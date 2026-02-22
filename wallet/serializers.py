from decimal import Decimal

from rest_framework import serializers
from django.contrib.auth.models import User

from wallet.models import Account, AssetType, LedgerEntry, Transaction


# ── Read Serializers ──────────────────────────────────────────────────

class AssetTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetType
        fields = ["id", "name", "code", "description", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


class AccountSerializer(serializers.ModelSerializer):
    asset_type = AssetTypeSerializer(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Account
        fields = [
            "id",
            "user",
            "owner_name",
            "account_type",
            "asset_type",
            "balance",
            "created_at",
            "updated_at",
        ]


class LedgerEntrySerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.owner_name", read_only=True)

    class Meta:
        model = LedgerEntry
        fields = ["id", "transaction", "account", "account_name", "entry_type", "amount", "created_at"]


class TransactionSerializer(serializers.ModelSerializer):
    ledger_entries = LedgerEntrySerializer(many=True, read_only=True)
    account_name = serializers.CharField(source="account.owner_name", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "idempotency_key",
            "tx_type",
            "status",
            "amount",
            "description",
            "account",
            "account_name",
            "ledger_entries",
            "created_at",
        ]


# ── Input Serializers (for POST endpoints) ───────────────────────────

class TopupInputSerializer(serializers.Serializer):
    account_id = serializers.UUIDField(help_text="UUID of the user account to top up")
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=4,
        min_value=Decimal("0.0001"),
        help_text="Amount to top up",
    )
    idempotency_key = serializers.CharField(
        max_length=255,
        help_text="Unique key to ensure this request is processed only once",
    )
    description = serializers.CharField(required=False, default="", allow_blank=True)


class BonusInputSerializer(serializers.Serializer):
    account_id = serializers.UUIDField(help_text="UUID of the user account to receive bonus")
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=4,
        min_value=Decimal("0.0001"),
        help_text="Bonus amount to issue",
    )
    idempotency_key = serializers.CharField(
        max_length=255,
        help_text="Unique key to ensure this request is processed only once",
    )
    description = serializers.CharField(required=False, default="", allow_blank=True)


class SpendInputSerializer(serializers.Serializer):
    account_id = serializers.UUIDField(help_text="UUID of the user account spending credits")
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=4,
        min_value=Decimal("0.0001"),
        help_text="Amount to spend",
    )
    idempotency_key = serializers.CharField(
        max_length=255,
        help_text="Unique key to ensure this request is processed only once",
    )
    description = serializers.CharField(required=False, default="", allow_blank=True)
