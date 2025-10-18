from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


__all__ = [
    "Command",
    "AtomicCompositeCommand",
    "TransferCommand",
    "BankAccount",
    "AccountError",
    "TransactionError",
]


# ==========================
# Module: atomic_transfer_command
# Purpose: Demonstrate transactional (atomic) Commands with compensating undo.
# Monetary values are integers representing cents to avoid floating point issues.
# ==========================


class AccountError(RuntimeError):
    """
    Raised when a bank account operation is invalid (e.g., overdraft limit exceeded).
    """


class TransactionError(RuntimeError):
    """
    Raised when an atomic composite cannot complete and has been rolled back.

    :param message: Human-readable description of the failure.
    :param cause: Original exception that triggered the rollback.
    """

    def __init__(self, message: str, cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.cause = cause


class Command(ABC):
    """
    Base interface for executable actions with compensating undo.

    :param description: Short, human-readable description of the command.
    """

    def __init__(self, description: str) -> None:
        self._description = description
        self._executed = False

    @property
    def description(self) -> str:
        """
        :return: Command description string.
        """
        return self._description

    @property
    def executed(self) -> bool:
        """
        :return: True if the command has successfully executed; False otherwise.
        """
        return self._executed

    @abstractmethod
    def execute(self) -> None:
        """
        Performs the primary action. Should set internal state required for a safe undo.
        Must set `self._executed = True` on success or raise an exception on failure.
        """

    @abstractmethod
    def undo(self) -> None:
        """
        Compensates the effects of `execute()`. Must be idempotent and safe to call
        only if `self.executed` is True.
        """


@dataclass(slots=True)
class BankAccount:
    """
    Simple bank account domain object.

    :param name: Account holder identifier.
    :param balance_cents: Current balance in cents.
    :param overdraft_limit_cents: Allowed negative balance in cents (e.g., 50_00 = -€50.00).
    """
    name: str
    balance_cents: int = 0
    overdraft_limit_cents: int = 0

    def deposit(self, amount_cents: int) -> None:
        """
        Adds money to the account.

        :param amount_cents: Amount in cents; must be >= 0.
        """
        if amount_cents < 0:
            raise AccountError("Deposit amount must be non-negative.")
        self.balance_cents += amount_cents

    def withdraw(self, amount_cents: int) -> None:
        """
        Removes money if within overdraft policy.

        :param amount_cents: Amount in cents; must be >= 0.
        :raises AccountError: If overdraft would be exceeded.
        """
        if amount_cents < 0:
            raise AccountError("Withdraw amount must be non-negative.")
        next_balance = self.balance_cents - amount_cents
        if next_balance < -self.overdraft_limit_cents:
            raise AccountError("Insufficient funds (overdraft limit exceeded).")
        self.balance_cents = next_balance


class DepositCommand(Command):
    """
    Deposits a given amount into a specific account. Undo withdraws the same amount.

    :param account: Target bank account (receiver).
    :param amount_cents: Amount to deposit in cents.
    """

    def __init__(self, account: BankAccount, amount_cents: int) -> None:
        super().__init__(description=f"Deposit {amount_cents}c to {account.name}")
        self._account = account
        self._amount = amount_cents

    def execute(self) -> None:
        """Perform the deposit."""
        self._account.deposit(self._amount)
        self._executed = True

    def undo(self) -> None:
        """Withdraw exactly what was deposited (compensation)."""
        if not self._executed:
            return
        # This should not fail if external mutations are avoided.
        self._account.withdraw(self._amount)
        self._executed = False


class WithdrawCommand(Command):
    """
    Withdraws a given amount from a specific account. Undo redeposits the same amount.

    :param account: Source bank account (receiver).
    :param amount_cents: Amount to withdraw in cents.
    """

    def __init__(self, account: BankAccount, amount_cents: int) -> None:
        super().__init__(description=f"Withdraw {amount_cents}c from {account.name}")
        self._account = account
        self._amount = amount_cents

    def execute(self) -> None:
        """Perform the withdrawal (may raise AccountError)."""
        self._account.withdraw(self._amount)
        self._executed = True

    def undo(self) -> None:
        """Re-deposit exactly what was withdrawn (compensation)."""
        if not self._executed:
            return
        self._account.deposit(self._amount)
        self._executed = False


class AtomicCompositeCommand(Command):
    """
    Executes a sequence of commands atomically: if any step fails, all prior steps are undone.

    :param description: Short description for the composite.
    :param items: Ordered list of sub-commands to execute.
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
        in reverse order and raises TransactionError.
        """
        self._executed_count = 0
        try:
            for cmd in self._items:
                cmd.execute()
                self._executed_count += 1
            self._executed = True
        except BaseException as exc:  # rollback on any failure
            for cmd in reversed(self._items[: self._executed_count]):
                try:
                    cmd.undo()
                except BaseException:
                    # Intentionally swallow to keep rollback best-effort and deterministic.
                    # In production, log this incident.
                    pass
            self._executed = False
            raise TransactionError("Atomic composite failed and was rolled back.", cause=exc) from exc

    def undo(self) -> None:
        """
        Undoes all successfully executed sub-commands in reverse order.
        Safe to call only after a successful `execute()`.
        """
        if not self._executed:
            return
        for cmd in reversed(self._items[: self._executed_count]):
            cmd.undo()
        self._executed_count = 0
        self._executed = False


class TransferCommand(AtomicCompositeCommand):
    """
    Atomic money transfer: withdraw from source, then deposit to destination.
    If deposit fails, withdrawal is automatically rolled back.

    :param source: Account to withdraw from.
    :param destination: Account to deposit into.
    :param amount_cents: Transfer amount in cents.
    """

    def __init__(self, source: BankAccount, destination: BankAccount, amount_cents: int) -> None:
        description = f"Transfer {amount_cents}c {source.name} -> {destination.name}"
        super().__init__(description=description)
        self.add(WithdrawCommand(source, amount_cents))
        self.add(DepositCommand(destination, amount_cents))
