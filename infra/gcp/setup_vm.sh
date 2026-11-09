#!/usr/bin/env bash
# One-time bootstrap of a GCP Compute Engine VM (Ubuntu 24.04 LTS) for Jobify.
#
#   sudo bash infra/gcp/setup_vm.sh https://github.com/devnoid1/Jobify.git app.example.com
#
# Installs: Python 3.12 venv, Node 22 (to build the frontend), nginx, certbot, PM2 (+ log
# rotation), Redis (local; or point REDIS_URL at Memorystore and skip it). Postgres is NOT
# installed: use Cloud SQL (private IP) and put its URL in /opt/jobify/.env as DATABASE_URL.
# Re-running is safe. After this, fill /opt/jobify/.env and run infra/gcp/deploy.sh.
set -euo pipefail

REPO_URL="${1:?usage: setup_vm.sh <git repo url> <domain>}"
DOMAIN="${2:?usage: setup_vm.sh <git repo url> <domain>}"
APP_USER=jobify
APP_DIR=/opt/jobify
LOG_DIR=/var/log/jobify

echo "== system packages"
apt-get update -y
apt-get install -y --no-install-recommends \
  python3.12 python3.12-venv python3-pip build-essential libpq-dev \
  nginx certbot python3-certbot-nginx redis-server git curl ca-certificates ufw

echo "== Node 22 + PM2"
if ! command -v node >/dev/null || ! node -v | grep -q '^v22'; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi
npm install -g pm2@5

echo "== app user and directories"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash "$APP_USER"
mkdir -p "$APP_DIR" "$LOG_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$LOG_DIR"

echo "== code"
if [ ! -d "$APP_DIR/.git" ]; then
  sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR"
fi
if [ ! -f "$APP_DIR/.env" ]; then
  sudo -u "$APP_USER" cp "$APP_DIR/.env.production.example" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
  echo "!! Fill in $APP_DIR/.env (DATABASE_URL, CLERK_*, TOKEN_ENCRYPTION_KEY, ...) before deploying."
fi

echo "== redis (local, loopback only)"
sed -i 's/^#\?\s*bind .*/bind 127.0.0.1 ::1/' /etc/redis/redis.conf
systemctl enable --now redis-server

echo "== nginx + TLS certificate (webroot: works before the HTTPS site exists)"
mkdir -p /var/www/html
cat > /etc/nginx/sites-available/jobify-acme <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 503; }
}
NGINX
rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/jobify
ln -sf /etc/nginx/sites-available/jobify-acme /etc/nginx/sites-enabled/jobify-acme
nginx -t && systemctl reload nginx
if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
  certbot certonly --webroot -w /var/www/html -d "$DOMAIN" --non-interactive --agree-tos     --register-unsafely-without-email || { echo "!! certbot failed: point $DOMAIN's DNS A record at this VM and re-run"; exit 1; }
fi
# certbot ships these with the nginx plugin; create them if missing.
[ -f /etc/letsencrypt/options-ssl-nginx.conf ] || curl -fsSL -o /etc/letsencrypt/options-ssl-nginx.conf   https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf
[ -f /etc/letsencrypt/ssl-dhparams.pem ] || openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048

cp "$APP_DIR/infra/gcp/nginx/security-headers.conf" /etc/nginx/snippets/jobify-security-headers.conf
sed "s/app.example.com/$DOMAIN/g" "$APP_DIR/infra/gcp/nginx/jobify.conf" > /etc/nginx/sites-available/jobify
rm -f /etc/nginx/sites-enabled/jobify-acme
ln -sf /etc/nginx/sites-available/jobify /etc/nginx/sites-enabled/jobify
nginx -t && systemctl reload nginx
# Renewals: certbot's systemd timer renews via webroot; reload nginx afterwards.
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
printf '#!/bin/sh
systemctl reload nginx
' > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

echo "== firewall: only SSH + HTTP(S) reach the VM (API/Redis/Flower bind to loopback)"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "== PM2 boot service + log rotation for $APP_USER"
env PATH="$PATH" pm2 startup systemd -u "$APP_USER" --hp "/home/$APP_USER" >/dev/null
sudo -u "$APP_USER" pm2 install pm2-logrotate
sudo -u "$APP_USER" pm2 set pm2-logrotate:max_size 50M
sudo -u "$APP_USER" pm2 set pm2-logrotate:retain 14
sudo -u "$APP_USER" pm2 set pm2-logrotate:compress true

echo "Done. Next: edit $APP_DIR/.env, then: sudo -u $APP_USER bash $APP_DIR/infra/gcp/deploy.sh"
