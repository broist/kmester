#!/usr/bin/env bash
# Ubuntu 22.04+/Debian 12+ initial production setup. Run once as root.
set -euo pipefail
REPO_URL="${REPO_URL:-https://github.com/broist/kmester.git}"
APP_DIR="${APP_DIR:-/opt/kmester}"
DOMAIN="${DEPLOY_DOMAIN:?Set DEPLOY_DOMAIN, e.g. kaloria.example.com}"

apt-get update
apt-get install -y ca-certificates curl git nginx certbot python3-certbot-nginx ufw
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
mkdir -p /opt
if [ ! -d "$APP_DIR/.git" ]; then git clone "$REPO_URL" "$APP_DIR"; else git -C "$APP_DIR" pull --ff-only; fi
cd "$APP_DIR"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Edit $APP_DIR/.env now, then run this script again."
  exit 1
fi
sed -i "s|^APP_URL=.*|APP_URL=https://$DOMAIN|" .env
sed "s/kaloria.example.com/$DOMAIN/g" deploy/nginx-kmester.conf > /etc/nginx/sites-available/kmester
ln -sf /etc/nginx/sites-available/kmester /etc/nginx/sites-enabled/kmester
rm -f /etc/nginx/sites-enabled/default
chmod 600 .env deploy/backup-kmester.sh
docker compose up -d --build
install -m 700 deploy/backup-kmester.sh /usr/local/sbin/backup-kmester
echo '17 3 * * * root /usr/local/sbin/backup-kmester' > /etc/cron.d/kmester-backup
nginx -t
systemctl enable --now nginx
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
certbot --nginx --non-interactive --agree-tos --redirect -m "${CERTBOT_EMAIL:?Set CERTBOT_EMAIL}" -d "$DOMAIN"
echo "Ready: https://$DOMAIN"
