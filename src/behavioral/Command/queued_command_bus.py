from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Tuple, Optional

__all__ = [
    "Command",
    "RetryPolicy",
    "CommandEnvelope",
    "EmptyQueueError",
    "InMemoryQueue",
    "CommandBus",
    "CommandWorker",
    "EmailService",
    "SendEmailCommand",
]

logger = logging.getLogger(__name__)


# ==========================
# Module: queued_command_bus
# Purpose: Decouple command producers (invokers) from executors via a queue,
#          with retry policy and dead-letter handling.
# ==========================


class Command(ABC):
    """
    Base interface for executable commands.

    Commands are data + behavior targeting a specific receiver (service).

    :param description: Human-readable description of the command.
    """

    def __init__(self, description: str) -> None:
        self._description = description

    @property
    def description(self) -> str:
        """
        :return: Command description string.
        """
        return self._description

    @abstractmethod
    def execute(self) -> None:
        """
        Executes the command against its receiver.

        :raises Exception: On failure. The worker/queue decides how to retry/handle.
        """


@dataclass
class RetryPolicy:
    """
    Retry configuration per command.

    :param max_retries: Maximum retry attempts before sending to dead-letter.
    :param backoff_seconds: Base backoff in seconds (informational; bus can ignore or implement).
    """
    max_retries: int = 3
    backoff_seconds: int = 1


@dataclass
class CommandEnvelope:
    """
    Queue wrapper around a command with retry bookkeeping.

    :param command: The command instance to execute.
    :param retry_policy: Policy for retries.
    :param attempts: Attempts already made (incremented by worker).
    :param last_error: Optional last error message for diagnostics.
    """
    command: Command
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    attempts: int = 0
    last_error: Optional[str] = None


class EmptyQueueError(IndexError):
    """
    Raised when attempting to dequeue from an empty queue.
    """


class InMemoryQueue:
    """
    Minimal FIFO queue for CommandEnvelope objects.

    :param name: Logical queue name (useful for logs/metrics).
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._q: Deque[CommandEnvelope] = deque()

    def enqueue(self, env: CommandEnvelope) -> None:
        """
        Enqueues an envelope.

        :param env: CommandEnvelope to push.
        """
        self._q.append(env)

    def dequeue(self) -> CommandEnvelope:
        """
        Pops one envelope.

        :return: Next CommandEnvelope in FIFO order.
        :raises EmptyQueueError: If the queue is empty.
        """
        try:
            return self._q.popleft()
        except IndexError as exc:
            raise EmptyQueueError("Queue is empty.") from exc

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._q)

    @property
    def name(self) -> str:  # pragma: no cover - trivial
        return self._name


class CommandBus:
    """
    Producer-side bus that accepts commands and places them on a queue.

    :param queue: Target queue implementation.
    """

    def __init__(self, queue: InMemoryQueue) -> None:
        self._queue = queue

    def send(self, cmd: Command, retry_policy: Optional[RetryPolicy] = None) -> None:
        """
        Sends a command to the queue wrapped in an envelope.

        :param cmd: The command to send.
        :param retry_policy: Optional retry policy override.
        """
        env = CommandEnvelope(
            command=cmd,
            retry_policy=retry_policy or RetryPolicy(),
        )
        self._queue.enqueue(env)
        logger.debug("Enqueued command: %s to queue: %s", cmd.description, self._queue.name)


class CommandWorker:
    """
    Consumer-side worker that pulls commands from a queue and executes them.

    On failure, applies retry policy and re-enqueues or moves to dead-letter.

    :param queue: Source queue to consume from.
    """

    def __init__(self, queue: InMemoryQueue) -> None:
        self._queue = queue
        self._dead_letter: List[CommandEnvelope] = []

    def poll_once(self) -> bool:
        """
        Processes at most one message from the queue.

        :return: True if something was processed; False if queue was empty.
        """
        try:
            env = self._queue.dequeue()
        except EmptyQueueError:
            return False

        try:
            env.command.execute()
            logger.info("Executed: %s", env.command.description)
        except Exception as exc:  # pylint: disable=broad-except
            env.attempts += 1
            env.last_error = repr(exc)
            if env.attempts <= env.retry_policy.max_retries:
                # In a real system we would apply backoff. Here we just re-enqueue.
                self._queue.enqueue(env)
                logger.warning(
                    "Retry %d/%d for %s due to %s",
                    env.attempts, env.retry_policy.max_retries, env.command.description, env.last_error
                )
            else:
                self._dead_letter.append(env)
                logger.error(
                    "Dead-lettered %s after %d attempts: %s",
                    env.command.description,
                    env.attempts,
                    env.last_error,
                )
        return True

    def drain(self, max_steps: int = 1000) -> Tuple[int, int]:
        """
        Drains the queue up to `max_steps` messages.

        :param max_steps: Safety cap to avoid infinite loops.
        :return: Tuple of (processed_count, dead_letter_count).
        """
        processed = 0
        steps = 0
        while steps < max_steps and self.poll_once():
            processed += 1
            steps += 1
        return processed, len(self._dead_letter)

    @property
    def dead_letter(self) -> List[CommandEnvelope]:
        """
        :return: Read-only view of dead-lettered envelopes.
        """
        return list(self._dead_letter)


# ----------------------------
# Example receiver + command
# ----------------------------

class EmailService:
    """
    Simple receiver to demonstrate remote/queued execution.

    :param max_len: Max allowed subject length (for artificial failures).
    """

    def __init__(self, max_len: int = 120) -> None:
        self._max_len = max_len
        self.outbox: List[Tuple[str, str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        """
        Simulates send; raises on invalid inputs to trigger retries.

        :param to: Email recipient.
        :param subject: Email subject.
        :param body: Email body.
        :raises ValueError: If subject too long or recipient missing.
        """
        if not to:
            raise ValueError("Recipient is required.")
        if len(subject) > self._max_len:
            raise ValueError("Subject too long.")
        self.outbox.append((to, subject, body))


class SendEmailCommand(Command):
    """
    Command that sends an email via EmailService.

    :param service: Email service receiver.
    :param to: Recipient address.
    :param subject: Subject line.
    :param body: Email body.
    """

    def __init__(self, service: EmailService, to: str, subject: str, body: str) -> None:
        super().__init__(description=f"SendEmail(to={to})")
        self._service = service
        self._to = to
        self._subject = subject
        self._body = body

    def execute(self) -> None:
        """Delegates to EmailService; exceptions bubble to worker for retry."""
        self._service.send(self._to, self._subject, self._body)
