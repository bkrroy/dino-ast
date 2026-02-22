from rest_framework import generics, status, views
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from wallet.models import Account, AssetType, LedgerEntry, Transaction
from wallet.serializers import (
    AccountSerializer,
    AssetTypeSerializer,
    BonusInputSerializer,
    LedgerEntrySerializer,
    SpendInputSerializer,
    TopupInputSerializer,
    TransactionSerializer,
)
from wallet.services import (
    AccountNotFoundError,
    InsufficientBalanceError,
    execute_bonus,
    execute_spend,
    execute_topup,
)


# ── Asset Types ───────────────────────────────────────────────────────

class AssetTypeListView(generics.ListAPIView):
    queryset = AssetType.objects.all()
    serializer_class = AssetTypeSerializer


# ── Accounts ──────────────────────────────────────────────────────────

class AccountListView(generics.ListAPIView):
    queryset = Account.objects.select_related("asset_type", "user").all()
    serializer_class = AccountSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["account_type", "asset_type", "user"]


class AccountDetailView(generics.RetrieveAPIView):
    queryset = Account.objects.select_related("asset_type", "user").all()
    serializer_class = AccountSerializer


class AccountBalanceView(views.APIView):

    def get(self, request, pk):
        try:
            account = Account.objects.select_related("asset_type", "user").get(pk=pk)
        except Account.DoesNotExist:
            return Response(
                {"error": "Account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            "account_id": str(account.pk),
            "owner_name": account.owner_name,
            "user_id": account.user_id,
            "asset_type": account.asset_type.code,
            "balance": str(account.balance),
        })


# ── Transactions ──────────────────────────────────────────────────────

class TransactionListView(generics.ListAPIView):
    queryset = (
        Transaction.objects
        .select_related("account", "account__user")
        .prefetch_related("ledger_entries__account")
        .all()
    )
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["tx_type", "status", "account"]


class TopupView(views.APIView):

    def post(self, request):
        serializer = TopupInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            tx = execute_topup(
                account_id=str(data["account_id"]),
                amount=data["amount"],
                idempotency_key=data["idempotency_key"],
                description=data.get("description", ""),
            )
        except AccountNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        tx_data = TransactionSerializer(tx).data
        return Response(tx_data, status=status.HTTP_201_CREATED)


class BonusView(views.APIView):

    def post(self, request):
        serializer = BonusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            tx = execute_bonus(
                account_id=str(data["account_id"]),
                amount=data["amount"],
                idempotency_key=data["idempotency_key"],
                description=data.get("description", ""),
            )
        except AccountNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        tx_data = TransactionSerializer(tx).data
        return Response(tx_data, status=status.HTTP_201_CREATED)


class SpendView(views.APIView):

    def post(self, request):
        serializer = SpendInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            tx = execute_spend(
                account_id=str(data["account_id"]),
                amount=data["amount"],
                idempotency_key=data["idempotency_key"],
                description=data.get("description", ""),
            )
        except AccountNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except InsufficientBalanceError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        tx_data = TransactionSerializer(tx).data
        return Response(tx_data, status=status.HTTP_201_CREATED)


# ── Ledger Entries ────────────────────────────────────────────────────

class LedgerEntryListView(generics.ListAPIView):
    queryset = (
        LedgerEntry.objects
        .select_related("account", "transaction")
        .all()
    )
    serializer_class = LedgerEntrySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["account", "entry_type", "transaction"]
