#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# seed_data.sh — Populate the database with random dummy data
# Each run generates unique random data for testing.
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

echo "🌱  Seeding Wallet Service database with random data..."
echo ""

docker compose exec web python manage.py seed_data

echo ""
echo "Done! You can now test the API at http://localhost:8000/api/"
echo ""
