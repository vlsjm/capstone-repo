#!/bin/bash
# ============================================================
#  update.sh — Pull latest code and redeploy
#
#  Usage:
#    chmod +x update.sh    (first time only)
#    ./update.sh
# ============================================================

set -e

echo "=== Pulling latest code ==="
git pull

echo "=== Rebuilding and restarting containers ==="
docker compose up --build -d

echo "=== Running migrations ==="
docker compose exec web python manage.py migrate --noinput

echo "=== Done! ==="
docker compose ps
