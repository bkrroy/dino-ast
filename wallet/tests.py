from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from wallet.models import Account, AssetType, LedgerEntry, Transaction
from wallet.services import (
    AccountNotFoundError,
    InsufficientBalanceError,
    execute_bonus,
    execute_spend,
    execute_topup,
)


class BaseWalletTestCase(TestCase):

    def setUp(self):
        self.asset = AssetType.objects.create(name="Gold Coins", code="GOLD")
        self.alice_user = User.objects.create_user(
            username="alice", first_name="Alice", last_name="Smith", password="testpass123"
        )
        self.treasury = Account.objects.create(
            owner_name="Treasury",
            account_type=Account.AccountType.SYSTEM,
            asset_type=self.asset,
            balance=Decimal("0"),
        )
        self.user_account = Account.objects.create(
            user=self.alice_user,
            account_type=Account.AccountType.USER,
            asset_type=self.asset,
            balance=Decimal("0"),
        )
        self.client = APIClient()


class TopupServiceTests(BaseWalletTestCase):

    def test_topup_credits_user(self):
        tx = execute_topup(
            account_id=str(self.user_account.pk),
            amount=Decimal("100"),
            idempotency_key="topup-1",
        )
        self.user_account.refresh_from_db()
        self.assertEqual(self.user_account.balance, Decimal("100"))
        self.assertEqual(tx.tx_type, Transaction.TxType.TOPUP)
        self.assertEqual(tx.status, Transaction.TxStatus.SUCCESS)

    def test_topup_creates_double_entry(self):
        tx = execute_topup(
            account_id=str(self.user_account.pk),
            amount=Decimal("50"),
            idempotency_key="topup-2",
        )
        entries = LedgerEntry.objects.filter(transaction=tx)
        self.assertEqual(entries.count(), 2)
        debit = entries.get(entry_type=LedgerEntry.EntryType.DEBIT)
        credit = entries.get(entry_type=LedgerEntry.EntryType.CREDIT)
        self.assertEqual(debit.account, self.treasury)
        self.assertEqual(credit.account, self.user_account)
        self.assertEqual(debit.amount, Decimal("50"))
        self.assertEqual(credit.amount, Decimal("50"))

    def test_topup_debits_treasury(self):
        execute_topup(
            account_id=str(self.user_account.pk),
            amount=Decimal("100"),
            idempotency_key="topup-3",
        )
        self.treasury.refresh_from_db()
        self.assertEqual(self.treasury.balance, Decimal("-100"))

    def test_user_linked_to_account(self):
        self.assertEqual(self.user_account.user, self.alice_user)
        self.assertEqual(self.user_account.owner_name, "Alice Smith")


class IdempotencyTests(BaseWalletTestCase):

    def test_duplicate_topup_is_idempotent(self):
        tx1 = execute_topup(
            account_id=str(self.user_account.pk),
            amount=Decimal("100"),
            idempotency_key="idem-1",
        )
        tx2 = execute_topup(
            account_id=str(self.user_account.pk),
            amount=Decimal("100"),
            idempotency_key="idem-1",
        )
        self.assertEqual(tx1.pk, tx2.pk)
        self.user_account.refresh_from_db()
        self.assertEqual(self.user_account.balance, Decimal("100"))

    def test_duplicate_bonus_is_idempotent(self):
        tx1 = execute_bonus(
            account_id=str(self.user_account.pk),
            amount=Decimal("50"),
            idempotency_key="idem-bonus-1",
        )
        tx2 = execute_bonus(
            account_id=str(self.user_account.pk),
            amount=Decimal("50"),
            idempotency_key="idem-bonus-1",
        )
        self.assertEqual(tx1.pk, tx2.pk)


class BonusServiceTests(BaseWalletTestCase):

    def test_bonus_credits_user(self):
        tx = execute_bonus(
            account_id=str(self.user_account.pk),
            amount=Decimal("25"),
            idempotency_key="bonus-1",
        )
        self.user_account.refresh_from_db()
        self.assertEqual(self.user_account.balance, Decimal("25"))
        self.assertEqual(tx.tx_type, Transaction.TxType.BONUS)


class SpendServiceTests(BaseWalletTestCase):

    def test_spend_debits_user(self):
        execute_topup(
            account_id=str(self.user_account.pk),
            amount=Decimal("100"),
            idempotency_key="setup-topup",
        )
        tx = execute_spend(
            account_id=str(self.user_account.pk),
            amount=Decimal("30"),
            idempotency_key="spend-1",
        )
        self.user_account.refresh_from_db()
        self.assertEqual(self.user_account.balance, Decimal("70"))
        self.assertEqual(tx.tx_type, Transaction.TxType.SPEND)

    def test_spend_insufficient_balance_raises(self):
        with self.assertRaises(InsufficientBalanceError):
            execute_spend(
                account_id=str(self.user_account.pk),
                amount=Decimal("999"),
                idempotency_key="spend-fail",
            )

    def test_spend_creates_double_entry(self):
        execute_topup(
            account_id=str(self.user_account.pk),
            amount=Decimal("100"),
            idempotency_key="setup-topup-2",
        )
        tx = execute_spend(
            account_id=str(self.user_account.pk),
            amount=Decimal("40"),
            idempotency_key="spend-2",
        )
        entries = LedgerEntry.objects.filter(transaction=tx)
        self.assertEqual(entries.count(), 2)
        debit = entries.get(entry_type=LedgerEntry.EntryType.DEBIT)
        credit = entries.get(entry_type=LedgerEntry.EntryType.CREDIT)
        self.assertEqual(debit.account, self.user_account)
        self.assertEqual(credit.account, self.treasury)


class AccountNotFoundTests(BaseWalletTestCase):

    def test_topup_invalid_account(self):
        with self.assertRaises(AccountNotFoundError):
            execute_topup(
                account_id="00000000-0000-0000-0000-000000000000",
                amount=Decimal("10"),
                idempotency_key="bad-account",
            )


class APIEndpointTests(BaseWalletTestCase):

    def test_list_asset_types(self):
        resp = self.client.get("/api/asset-types/")
        self.assertEqual(resp.status_code, 200)

    def test_list_accounts(self):
        resp = self.client.get("/api/accounts/")
        self.assertEqual(resp.status_code, 200)

    def test_account_detail(self):
        resp = self.client.get(f"/api/accounts/{self.user_account.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["owner_name"], "Alice Smith")

    def test_account_detail_has_user(self):
        resp = self.client.get(f"/api/accounts/{self.user_account.pk}/")
        self.assertEqual(resp.data["user"]["username"], "alice")

    def test_account_balance(self):
        resp = self.client.get(f"/api/accounts/{self.user_account.pk}/balance/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["balance"], "0.0000")

    def test_filter_accounts_by_user(self):
        resp = self.client.get(f"/api/accounts/?user={self.alice_user.pk}")
        self.assertEqual(resp.status_code, 200)

    def test_topup_api(self):
        resp = self.client.post("/api/transactions/topup/", {
            "account_id": str(self.user_account.pk),
            "amount": "100",
            "idempotency_key": "api-topup-1",
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.user_account.refresh_from_db()
        self.assertEqual(self.user_account.balance, Decimal("100"))

    def test_spend_api_insufficient_balance(self):
        resp = self.client.post("/api/transactions/spend/", {
            "account_id": str(self.user_account.pk),
            "amount": "9999",
            "idempotency_key": "api-spend-fail",
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_bonus_api(self):
        resp = self.client.post("/api/transactions/bonus/", {
            "account_id": str(self.user_account.pk),
            "amount": "50",
            "idempotency_key": "api-bonus-1",
        }, format="json")
        self.assertEqual(resp.status_code, 201)

    def test_list_transactions(self):
        execute_topup(
            account_id=str(self.user_account.pk),
            amount=Decimal("10"),
            idempotency_key="list-tx-1",
        )
        resp = self.client.get("/api/transactions/")
        self.assertEqual(resp.status_code, 200)

    def test_list_ledger_entries(self):
        execute_topup(
            account_id=str(self.user_account.pk),
            amount=Decimal("10"),
            idempotency_key="list-ledger-1",
        )
        resp = self.client.get("/api/ledger-entries/")
        self.assertEqual(resp.status_code, 200)
