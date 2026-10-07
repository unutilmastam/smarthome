#!/bin/sh
# Daily pg_dump (cron, installed automatically by deploy.sh). The connection comes from
# DATABASE_URL in the app's .env (next to this script) — no password in the crontab.
# Dumps stay outside public_html and contain NO video (ADR 0006).
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
URL="$(grep -E '^DATABASE_URL=' "$HERE/.env" | head -1 | cut -d= -f2- | tr -d "\"'")"
URL="$(printf '%s' "$URL" | sed 's#^postgresql+psycopg:#postgresql:#')"
[ -n "$URL" ] || { echo "DATABASE_URL not found in $HERE/.env" >&2; exit 1; }
DIR="${BACKUP_DIR:-$HOME/sh-deploy/daily}"
KEEP_DAYS="${KEEP_DAYS:-14}"
mkdir -p "$DIR" && chmod 700 "$DIR"
FILE="$DIR/smarthome-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
pg_dump --no-owner --no-privileges "$URL" | gzip -9 > "$FILE.tmp"
gzip -t "$FILE.tmp" && mv "$FILE.tmp" "$FILE"
chmod 600 "$FILE"
find "$DIR" -name 'smarthome-*.sql.gz' -mtime +"$KEEP_DAYS" -delete
echo "backup ok: $FILE ($(wc -c < "$FILE") bytes)"
