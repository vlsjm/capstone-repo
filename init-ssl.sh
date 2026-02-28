#!/bin/bash
# ============================================================
#  init-ssl.sh — First-time SSL certificate setup
#
#  Usage (run on VPS):
#    chmod +x init-ssl.sh
#    ./init-ssl.sh yourdomain.com you@example.com
# ============================================================

set -e

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Usage: ./init-ssl.sh <domain> <email>"
    echo "  e.g. ./init-ssl.sh resourcehive.com admin@resourcehive.com"
    exit 1
fi

echo ""
echo "=== SSL Init for $DOMAIN ==="
echo ""

# Step 1: Create a temporary self-signed cert so Nginx can start
echo "[1/4] Creating temporary self-signed certificate..."
mkdir -p ./certbot/conf/live/$DOMAIN
docker compose run --rm --entrypoint "\
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
    -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
    -subj '/CN=$DOMAIN'" certbot

# Step 2: Start Nginx with the temp cert
echo "[2/4] Starting Nginx..."
docker compose up -d nginx

# Step 3: Delete the temp cert and request a real one from Let's Encrypt
echo "[3/4] Requesting real certificate from Let's Encrypt..."
docker compose run --rm --entrypoint "\
    rm -rf /etc/letsencrypt/live/$DOMAIN && \
    rm -rf /etc/letsencrypt/archive/$DOMAIN && \
    rm -rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot

docker compose run --rm --entrypoint "\
    certbot certonly --webroot -w /var/www/certbot \
    --email $EMAIL \
    -d $DOMAIN -d www.$DOMAIN \
    --rsa-key-size 4096 \
    --agree-tos \
    --no-eff-email \
    --force-renewal" certbot

# Step 4: Reload Nginx to pick up the real cert
echo "[4/4] Reloading Nginx..."
docker compose exec nginx nginx -s reload

echo ""
echo "=== Done! SSL is active for $DOMAIN ==="
echo "    Visit https://$DOMAIN"
echo ""
