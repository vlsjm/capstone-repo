#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! python -c "
import socket, os
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect((os.environ.get('DB_HOST', 'db'), int(os.environ.get('DB_PORT', 5432))))
    s.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; do
    echo "  PostgreSQL is unavailable – sleeping 1s"
    sleep 1
done
echo "PostgreSQL is up!"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting Gunicorn..."
exec gunicorn ResourceHive.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
    
# Create superuser (only if needed)
echo "Creating superuser if it doesn't exist…"
python manage.py createsuperuser --noinput || true
