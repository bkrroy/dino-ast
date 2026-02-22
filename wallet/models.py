import uuid
from django.conf import settings
from django.db import models


class AssetType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=30, unique=True, help_text="Short code, e.g. GOLD, DIAMOND")
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Account(models.Model):

    class AccountType(models.TextChoices):
        USER = "USER", "User"
        SYSTEM = "SYSTEM", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts",
        null=True,
        blank=True,
        help_text="The Django user who owns this account. Null for system accounts.",
    )
    owner_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Display name. Auto-set from user if linked.",
    )
    account_type = models.CharField(max_length=10, choices=AccountType.choices)
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT, related_name="accounts")
    balance = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["owner_name"]
        indexes = [
            models.Index(fields=["account_type"]),
            models.Index(fields=["asset_type"]),
            models.Index(fields=["user"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "asset_type"],
                condition=models.Q(account_type="USER"),
                name="unique_user_asset_account",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.user and not self.owner_name:
            self.owner_name = self.user.get_full_name() or self.user.username
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.owner_name} ({self.account_type}) — {self.asset_type.code}"


class Transaction(models.Model):

    class TxType(models.TextChoices):
        TOPUP = "TOPUP", "Top-up (Purchase)"
        BONUS = "BONUS", "Bonus / Incentive"
        SPEND = "SPEND", "Spend / Purchase"

    class TxStatus(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.CharField(max_length=255, unique=True, db_index=True)
    tx_type = models.CharField(max_length=10, choices=TxType.choices)
    status = models.CharField(max_length=10, choices=TxStatus.choices, default=TxStatus.SUCCESS)
    amount = models.DecimalField(max_digits=20, decimal_places=4)
    description = models.TextField(blank=True, default="")
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="transactions",
        help_text="The user account involved in this transaction",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tx_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.tx_type} | {self.amount} | {self.idempotency_key}"


class LedgerEntry(models.Model):

    class EntryType(models.TextChoices):
        DEBIT = "DEBIT", "Debit"
        CREDIT = "CREDIT", "Credit"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name="ledger_entries")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="ledger_entries")
    entry_type = models.CharField(max_length=6, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=20, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Ledger entries"

    def __str__(self):
        return f"{self.entry_type} {self.amount} on {self.account.owner_name}"
