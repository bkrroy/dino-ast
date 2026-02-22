"""
Service layer for wallet transactions.

All business logic is here — atomic transactions, select_for_update for
deadlock avoidance, idempotency checks, and double-entry ledger creation.
"""

from decimal import Decimal

from django.db import IntegrityError, transaction

from wallet.models import Account, LedgerEntry, Transaction


class InsufficientBalanceError(Exception):
    """Raised when a user tries to spend more than their balance."""
    pass


class AccountNotFoundError(Exception):
    """Raised when the specified account does not exist."""
    pass


def _get_system_account(asset_type_id: int) -> Account:
    """
    Fetch the system (treasury) account for the given asset type.
    Raises AccountNotFoundError if none exists.
    """
    try:
        return Account.objects.get(account_type=Account.AccountType.SYSTEM, asset_type_id=asset_type_id)
    except Account.DoesNotExist:
        raise AccountNotFoundError(f"No system account found for asset type {asset_type_id}")


def _create_double_entry(
    tx: Transaction,
    debit_account: Account,
    credit_account: Account,
    amount: Decimal,
):
    """
    Create the two ledger entries (debit + credit) for a transaction,
    and update the cached balances on both accounts.
    """
    LedgerEntry.objects.create(
        transaction=tx,
        account=debit_account,
        entry_type=LedgerEntry.EntryType.DEBIT,
        amount=amount,
    )
    LedgerEntry.objects.create(
        transaction=tx,
        account=credit_account,
        entry_type=LedgerEntry.EntryType.CREDIT,
        amount=amount,
    )

    # Update cached balances
    # DEBIT = money leaving the account, CREDIT = money entering the account
    debit_account.balance -= amount
    debit_account.save(update_fields=["balance", "updated_at"])

    credit_account.balance += amount
    credit_account.save(update_fields=["balance", "updated_at"])


def _lock_accounts_ordered(*accounts: Account):
    """
    Re-fetch and lock accounts using select_for_update, ordered by PK
    to avoid deadlocks. Returns accounts in the same order as input.
    """
    ordered = sorted(accounts, key=lambda a: str(a.pk))
    locked_map = {}
    for acc in ordered:
        locked_map[str(acc.pk)] = (
            Account.objects.select_for_update().get(pk=acc.pk)
        )
    return tuple(locked_map[str(a.pk)] for a in accounts)


def execute_topup(
    account_id: str,
    amount: Decimal,
    idempotency_key: str,
    description: str = "",
) -> Transaction:
    """
    Wallet Top-up: Credits the user wallet from the system treasury.
    Assumes payment has already been processed externally.
    """
    amount = Decimal(str(amount))

    # Idempotency check — return existing transaction if key already used
    existing = Transaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    with transaction.atomic():
        try:
            user_account = Account.objects.get(pk=account_id, account_type=Account.AccountType.USER)
        except Account.DoesNotExist:
            raise AccountNotFoundError(f"User account {account_id} not found")

        system_account = _get_system_account(user_account.asset_type_id)

        # Lock both accounts in a consistent order to prevent deadlocks
        system_account, user_account = _lock_accounts_ordered(system_account, user_account)

        tx = Transaction.objects.create(
            idempotency_key=idempotency_key,
            tx_type=Transaction.TxType.TOPUP,
            status=Transaction.TxStatus.SUCCESS,
            amount=amount,
            description=description or f"Top-up of {amount}",
            account=user_account,
        )

        # Debit treasury, credit user
        _create_double_entry(tx, debit_account=system_account, credit_account=user_account, amount=amount)

        return tx


def execute_bonus(
    account_id: str,
    amount: Decimal,
    idempotency_key: str,
    description: str = "",
) -> Transaction:
    """
    Bonus / Incentive: The system issues free credits to a user.
    """
    amount = Decimal(str(amount))

    existing = Transaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    with transaction.atomic():
        try:
            user_account = Account.objects.get(pk=account_id, account_type=Account.AccountType.USER)
        except Account.DoesNotExist:
            raise AccountNotFoundError(f"User account {account_id} not found")

        system_account = _get_system_account(user_account.asset_type_id)

        system_account, user_account = _lock_accounts_ordered(system_account, user_account)

        tx = Transaction.objects.create(
            idempotency_key=idempotency_key,
            tx_type=Transaction.TxType.BONUS,
            status=Transaction.TxStatus.SUCCESS,
            amount=amount,
            description=description or f"Bonus of {amount}",
            account=user_account,
        )

        _create_double_entry(tx, debit_account=system_account, credit_account=user_account, amount=amount)

        return tx


def execute_spend(
    account_id: str,
    amount: Decimal,
    idempotency_key: str,
    description: str = "",
) -> Transaction:
    """
    Spend / Purchase: A user spends credits to buy a service.
    Rejects the transaction if the user has insufficient balance.
    """
    amount = Decimal(str(amount))

    existing = Transaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    with transaction.atomic():
        try:
            user_account = Account.objects.get(pk=account_id, account_type=Account.AccountType.USER)
        except Account.DoesNotExist:
            raise AccountNotFoundError(f"User account {account_id} not found")

        system_account = _get_system_account(user_account.asset_type_id)

        system_account, user_account = _lock_accounts_ordered(system_account, user_account)

        # Check sufficient balance
        if user_account.balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance. Available: {user_account.balance}, requested: {amount}"
            )

        tx = Transaction.objects.create(
            idempotency_key=idempotency_key,
            tx_type=Transaction.TxType.SPEND,
            status=Transaction.TxStatus.SUCCESS,
            amount=amount,
            description=description or f"Spend of {amount}",
            account=user_account,
        )

        # Debit user, credit treasury
        _create_double_entry(tx, debit_account=user_account, credit_account=system_account, amount=amount)

        return tx
