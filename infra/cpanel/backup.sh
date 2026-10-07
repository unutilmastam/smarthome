#!/bin/sh
# Daily pg_dump (cPanel cron). Credentials come from ~/.pgpass (chmod 600), never from
# this file. Dumps are stored outside public_html and contain NO video (ADR 0006).
set -eu
: "${PGDATABASE:?set PGDATABASE (e.g. in ~/.bashrc or the cron line)}"
DIR="${BACKUP_DIR:-$HOME/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
mkdir -p "$DIR" && chmod 700 "$DIR"
FILE="$DIR/smarthome-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
pg_dump --no-owner --no-privileges "$PGDATABASE" | gzip -9 > "$FILE.tmp"
mv "$FILE.tmp" "$FILE"
chmod 600 "$FILE"
find "$DIR" -name 'smarthome-*.sql.gz' -mtime +"$KEEP_DAYS" -delete
echo "backup ok: $FILE ($(wc -c < "$FILE") bytes)"
