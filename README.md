# 🏦 Wallet Service

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- That's it! Everything else runs inside containers.

### 1. Clone & Start

```bash
git clone https://github.com/bkrroy/dino-ast.git
cd Dino-ast

# Build and start containers (PostgreSQL + Django)
chmod +x run.sh
./run.sh

```

The API will be available at **http://localhost:8000/api/**.

### 2. Seed Dummy Data

```bash
chmod +x seed_data.sh
./seed_data.sh
```

This creates asset types, system/user accounts, and random transactions. **Each run generates unique random data**.

### 3. Explore the API or just import the Postman collection json file

Open **http://localhost:8000/api/** in your browser for the DRF browsable API, or use `curl`:

```bash
# List all accounts
curl http://localhost:8000/api/accounts/

# Check a specific account balance
curl http://localhost:8000/api/accounts/<ACCOUNT_UUID>/balance/

# Top-up a user's wallet
curl -X POST http://localhost:8000/api/transactions/topup/ \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "<USER_ACCOUNT_UUID>",
    "amount": "100.00",
    "idempotency_key": "unique-key-123"
  }'

# Issue a bonus
curl -X POST http://localhost:8000/api/transactions/bonus/ \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "<USER_ACCOUNT_UUID>",
    "amount": "50.00",
    "idempotency_key": "bonus-key-456"
  }'

# Spend credits
curl -X POST http://localhost:8000/api/transactions/spend/ \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "<USER_ACCOUNT_UUID>",
    "amount": "30.00",
    "idempotency_key": "spend-key-789"
  }'
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/asset-types/` | List all asset types |
| GET | `/api/accounts/` | List all accounts |
| GET | `/api/accounts/<uuid>/` | Account detail |
| GET | `/api/accounts/<uuid>/balance/` | Quick balance check |
| GET | `/api/transactions/` | List transactions (filterable) |
| POST | `/api/transactions/topup/` | Wallet top-up |
| POST | `/api/transactions/bonus/` | Issue bonus credits |
| POST | `/api/transactions/spend/` | Spend credits |
| GET | `/api/ledger-entries/` | List ledger entries |

---


### Concurrency & Safety

| Feature | Implementation |
|---------|---------------|
| **Deadlock Avoidance** | Accounts locked via `SELECT FOR UPDATE` in consistent PK order |
| **Idempotency** | Unique `idempotency_key` per transaction — duplicate requests return the existing result |
| **Atomic Transactions** | All operations wrapped in `@transaction.atomic` |
| **Balance Integrity** | Cached balance updated inside the same atomic block as ledger entries |

### Transaction Flows

1. **Top-up** — User purchases credits (payment assumed complete). Treasury → User.
2. **Bonus** — System issues free credits. Treasury → User.
3. **Spend** — User spends credits. User → Treasury. Rejected if insufficient balance.

---

## 🧪 Running Tests

```bash
docker compose exec web python manage.py test wallet -v 2
```

---

## 🛠️ Useful Commands

```bash
# View logs
docker compose logs -f web

# Open a shell in the web container
docker compose exec web bash

# Run Django shell
docker compose exec web python manage.py shell

# Create a superuser for the admin panel
docker compose exec web python manage.py createsuperuser

# Stop all containers
docker compose down

# Stop and remove all data (including the database)
docker compose down -v
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `wallet_db` | Database name |
| `POSTGRES_USER` | `wallet_user` | Database user |
| `POSTGRES_PASSWORD` | `wallet_pass` | Database password |
| `POSTGRES_HOST` | `db` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `DJANGO_SECRET_KEY` | (dev default) | Django secret key |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `*` | Allowed hosts |
