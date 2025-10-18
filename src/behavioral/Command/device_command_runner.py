from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "DeviceError",
    "CommandError",
    "CommandResult",
    "RetryPolicy",
    "Command",
    "AtomicCompositeCommand",
    "Device",
    "PLCDevice",
    "ConnectCommand",
    "DisconnectCommand",
    "SetParameterCommand",
    "StartProgramCommand",
    "StopProgramCommand",
]

# ==========================
# Module: device_command_runner
# Purpose: Command pattern for device/PLC operations with compensating undo
#          and transactional composite execution (atomic "all-or-nothing").
# ==========================


# ---------- Errors & Result ----------

class DeviceError(RuntimeError):
    """
    Raised when a device operation fails (e.g., connection/refused, invalid state).
    """


class CommandError(RuntimeError):
    """
    Raised when a command cannot complete successfully.
    """


@dataclass
class CommandResult:
    """
    Standard result wrapper for commands.

    :param success: Whether the command succeeded.
    :param value: Optional payload/result.
    :param error: Optional error if failed.
    """
    success: bool
    value: Any = None
    error: Optional[BaseException] = None


@dataclass
class RetryPolicy:
    """
    Retry configuration per command.

    :param max_retries: Maximum additional tries after the first attempt.
    :param backoff_seconds: Base backoff (informational; integration can implement waits).
    """
    max_retries: int = 0
    backoff_seconds: int = 0


# ---------- Base Command ----------

class Command(ABC):
    """
    Base interface for executable device commands with compensating undo.

    :param description: Human-readable description of the command.
    :param retry_policy: Optional per-command retry policy.
    """

    def __init__(self, description: str, retry_policy: Optional[RetryPolicy] = None) -> None:
        self._description = description
        self._executed = False
        self._retry_policy = retry_policy or RetryPolicy()

    @property
    def description(self) -> str:
        """
        :return: Command description string.
        """
        return self._description

    @property
    def executed(self) -> bool:
        """
        :return: True if the command has successfully executed once.
        """
        return self._executed

    def run(self) -> CommandResult:
        """
        Executes with simple retry loop and returns a CommandResult.

        :return: CommandResult(success/err).
        """
        attempts = 0
        last_exc: Optional[BaseException] = None
        total = 1 + max(0, self._retry_policy.max_retries)

        while attempts < total:
            try:
                self.execute()
                self._executed = True
                return CommandResult(success=True)
            except BaseException as exc:  # pylint: disable=broad-except
                last_exc = exc
                attempts += 1
                # Note: external integrator can implement backoff sleep if desired.
                logger.debug("Command '%s' attempt %d/%d failed: %r",
                             self._description, attempts, total, exc)

        return CommandResult(success=False, error=last_exc)

    @abstractmethod
    def execute(self) -> None:
        """
        Performs the primary action. On success must set internal state
        needed for a safe undo.
        """

    @abstractmethod
    def undo(self) -> None:
        """
        Compensates the effects of execute(). Must be idempotent and safe
        to call only if `self.executed` is True.
        """


class AtomicCompositeCommand(Command):
    """
    Executes a sequence of commands atomically: if any step fails, all
    prior steps are undone in reverse order.

    :param description: Short description for the composite.
    :param items: Ordered list of sub-commands to execute atomically.
    """

    def __init__(self, description: str, items: Optional[List[Command]] = None) -> None:
        super().__init__(description=description)
        self._items: List[Command] = list(items) if items else []
        self._executed_count = 0

    def add(self, cmd: Command) -> None:
        """
        Appends a sub-command to the composite.

        :param cmd: Command to add.
        """
        self._items.append(cmd)

    def execute(self) -> None:
        """
        Executes sub-commands in order. On failure, undoes all executed sub-commands
        and re-raises as CommandError.
        """
        self._executed_count = 0
        try:
            for cmd in self._items:
                res = cmd.run()
                if not res.success:
                    raise CommandError(f"Sub-command failed: {cmd.description}") from res.error
                self._executed_count += 1
            self._executed = True
        except BaseException as exc:  # rollback on any failure
            for cmd in reversed(self._items[: self._executed_count]):
                try:
                    if cmd.executed:
                        cmd.undo()
                except BaseException as undo_exc:  # best-effort; log only
                    logger.warning("Undo failed for '%s': %r", cmd.description, undo_exc)
            self._executed = False
            raise CommandError(f"Composite '{self.description}' rolled back due to failure.") from exc

    def undo(self) -> None:
        """
        Undoes all successfully executed sub-commands in reverse order.
        """
        if not self._executed:
            return
        for cmd in reversed(self._items[: self._executed_count]):
            cmd.undo()
        self._executed_count = 0
        self._executed = False


# ---------- Device Abstractions ----------

class Device(ABC):
    """
    Abstract device interface (PLC or similar).

    Concrete implementations must manage connection state and operations.
    """

    @abstractmethod
    def connect(self, timeout_s: int = 10) -> None:
        """
        Establishes a connection.

        :param timeout_s: Connection timeout in seconds.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """
        Closes the connection gracefully.
        """

    @abstractmethod
    def set_param(self, key: str, value: Any) -> Any:
        """
        Sets a device parameter and returns the previous value (for undo).

        :param key: Parameter key.
        :param value: New value.
        :return: Previous value.
        """

    @abstractmethod
    def start_program(self, name: str) -> None:
        """
        Starts a device/PLC program by name.

        :param name: Program identifier.
        """

    @abstractmethod
    def stop_program(self) -> None:
        """
        Stops the current program if running.
        """


class PLCDevice(Device):
    """
    Minimal in-memory PLC stub to demonstrate the pattern.

    :param name: Device identifier.
    :param fail_on_subjects: Optional flags to simulate failures (testing/demo).
    """

    def __init__(self, name: str, fail_on_subjects: Optional[Dict[str, bool]] = None) -> None:
        self.name = name
        self.connected = False
        self.params: Dict[str, Any] = {}
        self.running_program: Optional[str] = None
        self._fail: Dict[str, bool] = fail_on_subjects or {}

    def connect(self, timeout_s: int = 10) -> None:
        if self._fail.get("connect"):
            raise DeviceError(f"[{self.name}] Simulated connect failure.")
        self.connected = True

    def disconnect(self) -> None:
        if not self.connected:
            return
        if self._fail.get("disconnect"):
            raise DeviceError(f"[{self.name}] Simulated disconnect failure.")
        self.connected = False

    def set_param(self, key: str, value: Any) -> Any:
        if not self.connected:
            raise DeviceError(f"[{self.name}] Not connected.")
        if self._fail.get("set_param"):
            raise DeviceError(f"[{self.name}] Simulated set_param failure.")
        prev = self.params.get(key)
        self.params[key] = value
        return prev

    def start_program(self, name: str) -> None:
        if not self.connected:
            raise DeviceError(f"[{self.name}] Not connected.")
        if self._fail.get("start_program"):
            raise DeviceError(f"[{self.name}] Simulated start_program failure.")
        if self.running_program:
            raise DeviceError(f"[{self.name}] Program already running: {self.running_program}")
        self.running_program = name

    def stop_program(self) -> None:
        if not self.connected:
            raise DeviceError(f"[{self.name}] Not connected.")
        if self._fail.get("stop_program"):
            raise DeviceError(f"[{self.name}] Simulated stop_program failure.")
        self.running_program = None


# ---------- Concrete Commands ----------

class ConnectCommand(Command):
    """
    Connects to a device.

    :param device: Target device.
    :param timeout_s: Connection timeout in seconds.
    :param retry_policy: Optional retry policy.
    """

    def __init__(self, device: Device, timeout_s: int = 10, retry_policy: Optional[RetryPolicy] = None) -> None:
        super().__init__(description=f"Connect({getattr(device, 'name', device)})", retry_policy=retry_policy)
        self._device = device
        self._timeout = timeout_s

    def execute(self) -> None:
        self._device.connect(timeout_s=self._timeout)

    def undo(self) -> None:
        self._device.disconnect()


class DisconnectCommand(Command):
    """
    Disconnects from a device (idempotent).

    :param device: Target device.
    """

    def __init__(self, device: Device) -> None:
        super().__init__(description=f"Disconnect({getattr(device, 'name', device)})")
        self._device = device

    def execute(self) -> None:
        self._device.disconnect()

    def undo(self) -> None:
        # Often a no-op; if needed, could reconnect, but not generally safe.
        pass


class SetParameterCommand(Command):
    """
    Sets a device parameter with compensation by restoring the previous value.

    :param device: Target device.
    :param key: Parameter key.
    :param value: New value to set.
    :param retry_policy: Optional retry policy.
    """

    def __init__(self, device: Device, key: str, value: Any, retry_policy: Optional[RetryPolicy] = None) -> None:
        super().__init__(description=f"SetParam({getattr(device, 'name', device)}.{key}={value})",
                         retry_policy=retry_policy)
        self._device = device
        self._key = key
        self._value = value
        self._prev: Any = None
        self._had_prev = False

    def execute(self) -> None:
        prev = self._device.set_param(self._key, self._value)
        self._prev = prev
        self._had_prev = self._key in getattr(self._device, "params", {})
        # If execute() succeeds, the command is considered executed.

    def undo(self) -> None:
        if not self.executed:
            return
        if self._had_prev:
            self._device.set_param(self._key, self._prev)
        else:
            # Remove the parameter if it did not exist before.
            # If the device API doesn't support deletion, set to None or a default.
            getattr(self._device, "params", {}).pop(self._key, None)


class StartProgramCommand(Command):
    """
    Starts a program on the device and compensates by stopping it.

    :param device: Target device.
    :param program: Program name to start.
    :param retry_policy: Optional retry policy.
    """

    def __init__(self, device: Device, program: str, retry_policy: Optional[RetryPolicy] = None) -> None:
        super().__init__(description=f"StartProgram({getattr(device, 'name', device)}:{program})",
                         retry_policy=retry_policy)
        self._device = device
        self._program = program

    def execute(self) -> None:
        self._device.start_program(self._program)

    def undo(self) -> None:
        if not self.executed:
            return
        # Stop only if we started it in this command.
        if getattr(self._device, "running_program", None) == self._program:
            self._device.stop_program()


class StopProgramCommand(Command):
    """
    Stops the currently running program. Undo will re-start the previously running program (best effort).

    :param device: Target device.
    :param retry_policy: Optional retry policy.
    """

    def __init__(self, device: Device, retry_policy: Optional[RetryPolicy] = None) -> None:
        super().__init__(description=f"StopProgram({getattr(device, 'name', device)})",
                         retry_policy=retry_policy)
        self._device = device
        self._prev: Optional[str] = None

    def execute(self) -> None:
        self._prev = getattr(self._device, "running_program", None)
        self._device.stop_program()

    def undo(self) -> None:
        if not self.executed:
            return
        if self._prev:
            # Best-effort restore of the previous program.
            self._device.start_program(self._prev)
