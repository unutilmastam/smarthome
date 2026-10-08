#!/bin/sh
# Daily pg_dump (cron, installed automatically by deploy.sh). The connection comes from
# DATABASE_URL in the app's .env (next to this script) — no password in the crontab.
# Dumps stay outside public_html and contain NO video (ADR 0006).
#
# POSIX sh has no pipefail: `pg_dump | gzip` would report success for a dump that died
# halfway (Faza 14 finding). So: dump to a file, check pg_dump's exit code AND the
# "dump complete" footer, only then compress.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
URL="$(grep -E '^DATABASE_URL=' "$HERE/.env" | head -1 | cut -d= -f2- | tr -d "\"'")"
URL="$(printf '%s' "$URL" | sed 's#^postgresql+psycopg:#postgresql:#')"
[ -n "$URL" ] || { echo "DATABASE_URL not found in $HERE/.env" >&2; exit 1; }
DIR="${BACKUP_DIR:-$HOME/sh-deploy/daily}"
KEEP_DAYS="${KEEP_DAYS:-14}"
mkdir -p "$DIR" && chmod 700 "$DIR"
FILE="$DIR/smarthome-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
umask 077
trap 'rm -f "$FILE.sql" "$FILE.tmp"' EXIT
if ! pg_dump --no-owner --no-privileges -f "$FILE.sql" "$URL"; then
  echo "backup FAILED: pg_dump exited non-zero (nothing kept)" >&2; exit 1
fi
if ! tail -n 5 "$FILE.sql" | grep -q "PostgreSQL database dump complete"; then
  echo "backup FAILED: dump is incomplete (nothing kept)" >&2; exit 1
fi
gzip -9 -c "$FILE.sql" > "$FILE.tmp" && gzip -t "$FILE.tmp" && mv "$FILE.tmp" "$FILE"
chmod 600 "$FILE"
find "$DIR" -name 'smarthome-*.sql.gz' -mtime +"$KEEP_DAYS" -delete
echo "backup ok: $FILE ($(wc -c < "$FILE") bytes)"
