from django.contrib import admin

from wallet.models import Account, AssetType, LedgerEntry, Transaction


@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "created_at"]
    search_fields = ["name", "code"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["owner_name", "user", "account_type", "asset_type", "balance", "created_at"]
    list_filter = ["account_type", "asset_type"]
    search_fields = ["owner_name", "user__username", "user__first_name", "user__last_name"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "tx_type", "status", "amount", "account", "idempotency_key", "created_at"]
    list_filter = ["tx_type", "status"]
    search_fields = ["idempotency_key"]
    readonly_fields = ["id", "idempotency_key", "created_at"]


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "transaction", "account", "entry_type", "amount", "created_at"]
    list_filter = ["entry_type"]
