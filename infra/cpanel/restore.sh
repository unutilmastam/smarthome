#!/usr/bin/env bash
# Restore the cloud database from a dump (Faza 14). Runs ON THE cPANEL SERVER, from the
# app directory (deploy puts it next to backup.sh). From iPad: cPanel → Terminal.
#
#   bash ~/smarthome-api/restore.sh                 # list available dumps
#   bash ~/smarthome-api/restore.sh <dump.sql.gz>   # dry check: is the dump usable?
#   bash ~/smarthome-api/restore.sh <dump.sql.gz> --yes
#
# What --yes does, in this order:
#   1. checks the dump (gzip OK + "dump complete" footer)  -> otherwise nothing is touched
#   2. takes a SAFETY dump of the current database (~/sh-deploy/backups/pre-restore-*.sql.gz)
#   3. drops this role's tables and loads the dump in ONE transaction: any error -> the
#      database stays exactly as it was
#   4. alembic upgrade head (an older dump gets the current schema; migrations are expand-only)
#   5. restarts the app (Passenger)
# Exit: 0 restored / checked, 1 refused or failed (database unchanged unless step 4 failed).
set -uo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")" && pwd)}"
STATE_DIR="${STATE_DIR:-$HOME/sh-deploy}"
RESTART_CMD="${RESTART_CMD:-mkdir -p \"$APP_DIR/tmp\" && touch \"$APP_DIR/tmp/restart.txt\"}"

log() { printf '%s restore: %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die() { log "REFUSED/FAILED: $*"; exit 1; }

URL="$(grep -E '^DATABASE_URL=' "$APP_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d "\"'")"
URL="${URL/postgresql+psycopg:/postgresql:}"
[ -n "$URL" ] || die "DATABASE_URL not found in $APP_DIR/.env"

if [ $# -eq 0 ]; then
  echo "Available dumps (newest first):"
  ls -1t "$STATE_DIR"/daily/*.sql.gz "$STATE_DIR"/backups/*.sql.gz 2>/dev/null | head -30
  exit 0
fi

DUMP="$1"
[ -f "$DUMP" ] || die "no such file: $DUMP"
gzip -t "$DUMP" 2>/dev/null || die "$DUMP is not a valid gzip file"
gunzip -c "$DUMP" | tail -n 5 | grep -q "PostgreSQL database dump complete" \
  || die "$DUMP is incomplete (no 'dump complete' footer)"
TABLES="$(gunzip -c "$DUMP" | grep -c '^CREATE TABLE ' || true)"
log "dump OK: $DUMP ($TABLES tables)"
if [ "${2:-}" != "--yes" ]; then
  log "dry check only. Add --yes to replace the current database with this dump."
  exit 0
fi

# ---- 2. safety dump of what is there now ------------------------------------------------
mkdir -p "$STATE_DIR/backups" && chmod 700 "$STATE_DIR/backups"
SAFE="$STATE_DIR/backups/pre-restore-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
( umask 077; pg_dump --no-owner --no-privileges "$URL" | gzip -9 > "$SAFE.tmp" ) \
  && gzip -t "$SAFE.tmp" && mv "$SAFE.tmp" "$SAFE" \
  || { rm -f "$SAFE.tmp"; die "safety dump failed: nothing was changed"; }
log "safety dump of the current database: $SAFE"

# ---- 3. drop + load in one transaction -------------------------------------------------------
log "loading $DUMP (single transaction)"
{
  cat <<'SQL'
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner = current_user LOOP
    EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
  END LOOP;
  FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' AND sequenceowner = current_user LOOP
    EXECUTE 'DROP SEQUENCE IF EXISTS public.' || quote_ident(r.sequencename) || ' CASCADE';
  END LOOP;
END $$;
SQL
  gunzip -c "$DUMP" | grep -v -E '^(COMMENT ON SCHEMA|CREATE SCHEMA|ALTER SCHEMA)'
} | psql -q -X --single-transaction -v ON_ERROR_STOP=1 "$URL" > /dev/null \
  || die "load failed and was rolled back: the database is unchanged (safety dump: $SAFE)"
log "database restored from $DUMP"

# ---- 4. schema up to the running code ----------------------------------------------------------
( cd "$APP_DIR" && python -m alembic upgrade head ) \
  || die "alembic upgrade head failed after restore (data is restored; safety dump: $SAFE)"

# ---- 5. restart ---------------------------------------------------------------------------------
eval "$RESTART_CMD" || log "WARNING: restart command failed — restart from cPanel → Setup Python App"
log "done. Check the app; to undo: bash $0 $SAFE --yes"
exit 0
