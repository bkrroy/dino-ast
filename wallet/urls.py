from django.urls import path

from wallet import views

urlpatterns = [
    # Asset types
    path("asset-types/", views.AssetTypeListView.as_view(), name="asset-type-list"),

    # Accounts
    path("accounts/", views.AccountListView.as_view(), name="account-list"),
    path("accounts/<uuid:pk>/", views.AccountDetailView.as_view(), name="account-detail"),
    path("accounts/<uuid:pk>/balance/", views.AccountBalanceView.as_view(), name="account-balance"),

    # Transactions
    path("transactions/", views.TransactionListView.as_view(), name="transaction-list"),
    path("transactions/topup/", views.TopupView.as_view(), name="transaction-topup"),
    path("transactions/bonus/", views.BonusView.as_view(), name="transaction-bonus"),
    path("transactions/spend/", views.SpendView.as_view(), name="transaction-spend"),

    # Ledger
    path("ledger-entries/", views.LedgerEntryListView.as_view(), name="ledger-entry-list"),
]
