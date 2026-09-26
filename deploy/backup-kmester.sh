#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/kmester}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/kmester}"
mkdir -p "$BACKUP_DIR"
cd "$APP_DIR"
set -a; source .env; set +a
umask 077
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_DIR/kmester-$(date +%F-%H%M).sql.gz"
find "$BACKUP_DIR" -type f -name 'kmester-*.sql.gz' -mtime +14 -delete
