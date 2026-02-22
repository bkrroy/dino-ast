"""
Django management command to populate the database with random dummy data.

Each run produces unique random data (names, amounts, etc.).
Usage: python manage.py seed_data
"""

import random
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from wallet.models import Account, AssetType, LedgerEntry, Transaction
from wallet.services import execute_bonus, execute_spend, execute_topup


def random_name():
    first_names = [
        "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace",
        "Hank", "Ivy", "Jack", "Karen", "Leo", "Mona", "Nick", "Olivia",
        "Paul", "Quinn", "Rosa", "Sam", "Tina", "Uma", "Vince", "Wendy",
        "Xander", "Yara", "Zane",
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
        "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez",
        "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson",
    ]
    return random.choice(first_names), random.choice(last_names)


def random_amount(low=10, high=500):
    return Decimal(str(round(random.uniform(low, high), 2)))


def random_key():
    return f"seed-{uuid.uuid4().hex[:12]}"


class Command(BaseCommand):
    help = "Populate the database with random dummy data for testing."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🌱 Seeding database with random data...\n"))

        # ── 1. Create Asset Types ─────────────────────────────────────
        asset_definitions = [
            ("Gold Coins", "GOLD", "In-game gold currency"),
            ("Diamonds", "DIAMOND", "Premium currency"),
            ("Loyalty Points", "LOYALTY", "Reward points for engagement"),
        ]

        assets = []
        for name, code, desc in asset_definitions:
            asset, created = AssetType.objects.get_or_create(
                code=code,
                defaults={"name": name, "description": desc},
            )
            assets.append(asset)
            status_msg = "Created" if created else "Already exists"
            self.stdout.write(f"  Asset Type: {asset.name} ({asset.code}) — {status_msg}")

        # ── 2. Create System Accounts (Treasury) ──────────────────────
        for asset in assets:
            _, created = Account.objects.get_or_create(
                account_type=Account.AccountType.SYSTEM,
                asset_type=asset,
                defaults={"owner_name": f"Treasury ({asset.code})"},
            )
            status_msg = "Created" if created else "Already exists"
            self.stdout.write(f"  System Account: Treasury ({asset.code}) — {status_msg}")

        # ── 3. Create Django Users + User Accounts ────────────────────
        num_users = random.randint(3, 6)
        user_accounts = []
        for _ in range(num_users):
            first_name, last_name = random_name()
            username = f"{first_name.lower()}_{last_name.lower()}_{random.randint(100, 999)}"

            django_user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=f"{username}@example.com",
                password="testpass123",
            )

            # Create one account per asset type for each user
            asset = random.choice(assets)
            account = Account.objects.create(
                user=django_user,
                account_type=Account.AccountType.USER,
                asset_type=asset,
            )
            user_accounts.append(account)
            self.stdout.write(f"  User: {first_name} {last_name} (@{username}) — {asset.code}")

        self.stdout.write("")

        # ── 4. Generate Random Transactions ───────────────────────────
        self.stdout.write(self.style.NOTICE("💸 Generating random transactions...\n"))

        for account in user_accounts:
            display_name = account.owner_name

            # Top-up the account first
            topup_amount = random_amount(100, 1000)
            execute_topup(
                account_id=str(account.pk),
                amount=topup_amount,
                idempotency_key=random_key(),
                description=f"Initial top-up for {display_name}",
            )
            self.stdout.write(f"  TOPUP  {display_name}: +{topup_amount} {account.asset_type.code}")

            # Maybe give a bonus
            if random.random() > 0.3:
                bonus_amount = random_amount(10, 200)
                execute_bonus(
                    account_id=str(account.pk),
                    amount=bonus_amount,
                    idempotency_key=random_key(),
                    description=f"Welcome bonus for {display_name}",
                )
                self.stdout.write(f"  BONUS  {display_name}: +{bonus_amount} {account.asset_type.code}")

            # Random number of spends
            num_spends = random.randint(1, 4)
            for i in range(num_spends):
                account.refresh_from_db()
                if account.balance <= 0:
                    break
                max_spend = min(float(account.balance), 200.0)
                spend_amount = random_amount(1, max(2, max_spend))
                if spend_amount > account.balance:
                    spend_amount = account.balance - Decimal("1")
                if spend_amount <= 0:
                    break
                try:
                    execute_spend(
                        account_id=str(account.pk),
                        amount=spend_amount,
                        idempotency_key=random_key(),
                        description=f"Purchase #{i + 1} by {display_name}",
                    )
                    self.stdout.write(f"  SPEND  {display_name}: -{spend_amount} {account.asset_type.code}")
                except Exception:
                    pass

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✅ Seed data created successfully!"))

        # Print summary
        self.stdout.write(f"\n  Users:          {User.objects.count()}")
        self.stdout.write(f"  Asset Types:    {AssetType.objects.count()}")
        self.stdout.write(f"  Accounts:       {Account.objects.count()}")
        self.stdout.write(f"  Transactions:   {Transaction.objects.count()}")
        self.stdout.write(f"  Ledger entries: {LedgerEntry.objects.count()}")
        self.stdout.write("")
