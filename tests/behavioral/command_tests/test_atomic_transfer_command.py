import pytest
from behavioral.command.atomic_transfer_command import BankAccount, TransferCommand, TransactionError


def test_transfer_success():
    a = BankAccount("A", balance_cents=2_000)
    b = BankAccount("B", balance_cents=500)
    t = TransferCommand(a, b, 1_000)
    t.execute()
    assert a.balance_cents == 1_000
    assert b.balance_cents == 1_500


def test_transfer_rollback_on_overdraft():
    a = BankAccount("A", balance_cents=500)
    b = BankAccount("B", balance_cents=500)
    t = TransferCommand(a, b, 1_000)
    with pytest.raises(TransactionError):
        t.execute()
    # balances unchanged after rollback
    assert a.balance_cents == 500
    assert b.balance_cents == 500
