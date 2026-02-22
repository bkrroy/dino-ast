#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# run.sh — Build and start the Wallet Service Docker containers
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

echo "🐳  Building and starting Wallet Service containers..."
echo ""

docker compose up --build -d

echo ""
echo "✅  Containers are running!"
echo ""
echo "  Web:      http://localhost:8000/api/"
echo "  Postgres: localhost:5432"
echo ""
echo "  Useful commands:"
echo "    docker-compose logs -f web     # Follow Django logs"
echo "    docker-compose exec web bash   # Shell into the web container"
echo "    docker-compose down            # Stop all containers"
echo ""
