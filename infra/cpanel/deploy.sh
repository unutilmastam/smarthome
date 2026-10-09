#!/usr/bin/env bash
# Runs ON THE cPANEL SERVER (GitHub Actions calls it over SSH; ADR 0011).
#
#   backup DB (pg_dump, keep last N) -> snapshot current code -> install new code
#   -> alembic upgrade head -> Passenger restart -> health check (build must match)
#   any failure after the backup -> automatic rollback: previous code + DB from backup
#
# Exit codes (the workflow turns them into a Telegram message):
#   0  deployed                         11 aborted before any change (nothing touched)
#   10 failed, rolled back OK           12 failed AND rollback failed (CRITICAL)
#
# Required env: APP_DIR WEB_DIR STAGE_DIR STATE_DIR VENV_ACTIVATE HEALTH_URL EXPECT_BUILD
# Optional env: KEEP_BACKUPS (10) HEALTH_TIMEOUT (120 s) RESTART_CMD
#               HEALTH_RESOLVE (host:443:ip for curl --resolve, when the server's DNS lags)
#               INIT_DATABASE_URL (only used to create APP_DIR/.env on the first deploy)
#               TELEGRAM_BOT_TOKEN PUBLIC_BASE_URL (ADR 0014: written into APP_DIR/.env)
set -uo pipefail

: "${APP_DIR:?}" "${WEB_DIR:?}" "${STAGE_DIR:?}" "${STATE_DIR:?}" "${VENV_ACTIVATE:?}"
: "${HEALTH_URL:?}" "${EXPECT_BUILD:?}"
PIP_INSTALL="${PIP_INSTALL:-python -m pip install -q -r}"
KEEP_BACKUPS="${KEEP_BACKUPS:-10}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"
RESTART_CMD="${RESTART_CMD:-mkdir -p \"$APP_DIR/tmp\" && touch \"$APP_DIR/tmp/restart.txt\"}"

# The web root also holds things cPanel owns: the Passenger config of the /api app
# (CloudLinux writes api/.htaccess or a block in .htaccess), AutoSSL challenges and cgi-bin.
# A deploy must never delete them.
WEB_KEEP=(--exclude '/api/' --exclude '/.well-known/' --exclude '/cgi-bin/')

# `rsync -a --delete [--exclude P]... SRC/ DST/`. Some shared hosts (hostmaster.uz) have no
# rsync: the same semantics in Python (patterns: '/x/' anchored dir, 'x/' dir anywhere,
# 'x' name anywhere; excluded paths in DST are neither copied over nor deleted).
sync_tree() {
  if command -v rsync >/dev/null 2>&1 && [ -z "${SH_NO_RSYNC:-}" ]; then
    rsync -a --delete "$@"; return
  fi
  python3 - "$@" <<'PY'
import os, shutil, sys

args, pats = sys.argv[1:], []
while args and args[0] == "--exclude":
    pats.append(args[1]); args = args[2:]
src, dst = (a.rstrip("/") for a in args)

def excluded(rel, is_dir):
    for p in pats:
        if p.endswith("/") and not is_dir:
            continue
        name = p.strip("/")
        if (rel == name) if p.startswith("/") else (os.path.basename(rel) == name):
            return True
    return False

def is_dir(path):
    return os.path.isdir(path) and not os.path.islink(path)

def remove(path):
    shutil.rmtree(path) if is_dir(path) else os.unlink(path)

def sync(rel):
    s, d = os.path.join(src, rel), os.path.join(dst, rel)
    if is_dir(d) is False and os.path.lexists(d):
        os.unlink(d)
    os.makedirs(d, exist_ok=True)
    names = set(os.listdir(s))
    for name in sorted(os.listdir(d)):        # --delete, but never touch excluded paths
        r = os.path.join(rel, name) if rel else name
        if name not in names and not excluded(r, is_dir(os.path.join(d, name))):
            remove(os.path.join(d, name))
    for name in sorted(names):
        r = os.path.join(rel, name) if rel else name
        sp, dp = os.path.join(s, name), os.path.join(d, name)
        if excluded(r, is_dir(sp)):
            continue
        if is_dir(sp):
            sync(r)
            continue
        if os.path.lexists(dp) and (is_dir(dp) or os.path.islink(dp) or os.path.islink(sp)):
            remove(dp)
        if os.path.islink(sp):
            os.symlink(os.readlink(sp), dp)
        else:
            shutil.copy2(sp, dp)
    shutil.copystat(s, d)

sync("")
PY
}

BACKUPS="$STATE_DIR/backups"
PREV="$STATE_DIR/previous"
LOCK="$STATE_DIR/lock"
mkdir -p "$BACKUPS" "$PREV" && chmod 700 "$STATE_DIR" "$BACKUPS"

log() { printf '%s deploy: %s\n' "$(date -u +%H:%M:%S)" "$*"; }
result() { printf 'RESULT=%s\n' "$1"; [ -n "${2:-}" ] && printf 'DETAIL=%s\n' "$2"; }

# ---- lock: never two deploys at once ------------------------------------------------
if ! mkdir "$LOCK" 2>/dev/null; then
  result aborted "another deploy is running ($LOCK exists)"; exit 11
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

# shellcheck disable=SC1090
. "$VENV_ACTIVATE" || { result aborted "cannot activate virtualenv"; exit 11; }

# ---- first deploy: create .env with secrets generated ON the server ------------------
if [ ! -f "$APP_DIR/.env" ]; then
  if [ -z "${INIT_DATABASE_URL:-}" ]; then
    result aborted "$APP_DIR/.env missing and INIT_DATABASE_URL not given"; exit 11
  fi
  mkdir -p "$APP_DIR"
  umask 077
  {
    echo "ENV=production"
    echo "DATABASE_URL=$INIT_DATABASE_URL"
    echo "JWT_SECRET=$(python -c 'import secrets;print(secrets.token_hex(32))')"
    echo "SIGNING_MASTER_KEY=$(python -c 'import secrets;print(secrets.token_hex(32))')"
    echo "COOKIE_SECURE=true"
    echo "REALTIME_PROVIDER=none"
  } > "$APP_DIR/.env"
  umask 022
  log "created $APP_DIR/.env (JWT/signing secrets generated here, never left the server)"
fi

DB_URL="$(grep -E '^DATABASE_URL=' "$APP_DIR/.env" | head -1 | cut -d= -f2- | tr -d '"'"'")"
DB_URL="${DB_URL/postgresql+psycopg:/postgresql:}"
[ -n "$DB_URL" ] || { result aborted "DATABASE_URL not found in .env"; exit 11; }

PREV_BUILD="$(sed -n 's/^BUILD = "\(.*\)"$/\1/p' "$APP_DIR/app/_build.py" 2>/dev/null || true)"
printf 'PREVIOUS_BUILD=%s\n' "${PREV_BUILD:-none}"

# ---- 1. backup BEFORE touching anything -----------------------------------------------
TS="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP="$BACKUPS/pre-deploy-$TS-${EXPECT_BUILD:0:12}.sql.gz"
log "pg_dump -> $DUMP"
if ! pg_dump --no-owner --no-privileges "$DB_URL" | gzip -9 > "$DUMP.tmp" \
    || ! gzip -t "$DUMP.tmp"; then
  rm -f "$DUMP.tmp"; result aborted "pg_dump failed: nothing was changed"; exit 11
fi
mv "$DUMP.tmp" "$DUMP" && chmod 600 "$DUMP"
# keep the newest KEEP_BACKUPS pre-deploy dumps
ls -1t "$BACKUPS"/pre-deploy-*.sql.gz 2>/dev/null | tail -n +"$((KEEP_BACKUPS + 1))" | xargs -r rm -f
printf 'BACKUP=%s\n' "$DUMP"

# ---- 2. snapshot the running release ---------------------------------------------------
HAVE_PREV=0
if [ -f "$APP_DIR/passenger_wsgi.py" ] && [ -d "$APP_DIR/app" ]; then
  sync_tree --exclude '.env' --exclude 'tmp/' --exclude 'logs/' "$APP_DIR/" "$PREV/api/"
  mkdir -p "$WEB_DIR" && sync_tree "${WEB_KEEP[@]}" "$WEB_DIR/" "$PREV/web/"
  HAVE_PREV=1
fi

health_ok() {  # $1 = expected build
  local deadline=$((SECONDS + HEALTH_TIMEOUT)) body
  while [ "$SECONDS" -lt "$deadline" ]; do
    body="$(curl -fsS --max-time 10 ${HEALTH_RESOLVE:+--resolve "$HEALTH_RESOLVE"} "$HEALTH_URL" 2>/dev/null || true)"
    case "$body" in
      *'"status":"ok"'*'"build":"'"$1"'"'*) return 0 ;;
    esac
    sleep 3
  done
  return 1
}

restore_db() {
  log "restoring database from $DUMP"
  # Drop everything this role owns in public (also tables the failed migration added),
  # then load the pre-deploy dump.
  psql -q -v ON_ERROR_STOP=1 "$DB_URL" <<'SQL' || return 1
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner = current_user LOOP
    EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
  END LOOP;
  FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' AND sequenceowner = current_user LOOP
    EXECUTE 'DROP SEQUENCE IF EXISTS public.' || quote_ident(r.sequencename) || ' CASCADE';
  END LOOP;
END $$;
SQL
  gunzip -c "$DUMP" | grep -v -E '^(COMMENT ON SCHEMA|CREATE SCHEMA|ALTER SCHEMA)' \
    | psql -q -v ON_ERROR_STOP=1 "$DB_URL" > /dev/null
}

rollback() {
  local why="$1"
  log "FAILED: $why -> rolling back"
  if [ "$HAVE_PREV" = 1 ]; then
    sync_tree --exclude '.env' --exclude 'tmp/' --exclude 'logs/' "$PREV/api/" "$APP_DIR/"
    sync_tree "${WEB_KEEP[@]}" "$PREV/web/" "$WEB_DIR/"
    $PIP_INSTALL "$APP_DIR/requirements.txt" || log "pip install of previous release failed"
  fi
  if ! restore_db; then
    result rollback_failed "$why; DB restore failed (backup: $DUMP)"; exit 12
  fi
  eval "$RESTART_CMD"
  if [ "$HAVE_PREV" = 1 ]; then
    if health_ok "$PREV_BUILD"; then
      result rolled_back "$why"; exit 10
    fi
    result rollback_failed "$why; previous release ($PREV_BUILD) not healthy after rollback"; exit 12
  fi
  result rollback_failed "$why; first deploy, no previous release to return to (DB restored)"
  exit 12
}

# ---- 3. new code, migration, restart ----------------------------------------------------
log "installing build $EXPECT_BUILD"
$PIP_INSTALL "$STAGE_DIR/api/requirements.txt" || rollback "pip install failed"

# ---- notification settings (ADR 0014): kept ONLY in .env; generated secrets never leave here --
env_get() { grep -E "^$1=" "$APP_DIR/.env" | head -1 | cut -d= -f2-; }
env_set() {  # replace or append KEY=VALUE; the value is never printed
  ( umask 077
    { grep -v -E "^$1=" "$APP_DIR/.env"; printf '%s=%s\n' "$1" "$2"; } > "$APP_DIR/.env.tmp" \
      && mv "$APP_DIR/.env.tmp" "$APP_DIR/.env" )
}
for key in TELEGRAM_BOT_TOKEN PUBLIC_BASE_URL; do
  val="${!key:-}"
  if [ -n "$val" ] && [ "$(env_get "$key")" != "$val" ]; then
    env_set "$key" "$val" && log "$key set in .env"
  fi
done
if [ -z "$(env_get TELEGRAM_WEBHOOK_SECRET)" ]; then
  env_set TELEGRAM_WEBHOOK_SECRET "$(python -c 'import secrets;print(secrets.token_hex(32))')" \
    && log "TELEGRAM_WEBHOOK_SECRET generated"
fi
if [ -z "$(env_get VAPID_PRIVATE_KEY)" ]; then
  vapid="$(python -c 'import base64; from cryptography.hazmat.primitives.asymmetric import ec
k = ec.generate_private_key(ec.SECP256R1()).private_numbers().private_value.to_bytes(32, "big")
print(base64.urlsafe_b64encode(k).rstrip(b"=").decode())' 2>/dev/null)"
  if [ -n "$vapid" ]; then env_set VAPID_PRIVATE_KEY "$vapid" && log "VAPID_PRIVATE_KEY generated"
  else log "WARNING: could not generate VAPID key (Web Push stays off)"; fi
fi
mkdir -p "$APP_DIR" "$WEB_DIR"
sync_tree --exclude '.env' --exclude 'tmp/' --exclude 'logs/' "$STAGE_DIR/api/" "$APP_DIR/" \
  || rollback "code upload into $APP_DIR failed"
# Keep a CloudLinux Passenger block from the live .htaccess on top of ours.
PASSENGER_BLOCK="$(sed -n '/CLOUDLINUX PASSENGER CONFIGURATION BEGIN/,/CLOUDLINUX PASSENGER CONFIGURATION END/p' \
  "$WEB_DIR/.htaccess" 2>/dev/null || true)"
sync_tree "${WEB_KEEP[@]}" "$STAGE_DIR/web/" "$WEB_DIR/" || rollback "web upload failed"
if [ -n "$PASSENGER_BLOCK" ]; then
  { printf '%s\n\n' "$PASSENGER_BLOCK"; cat "$WEB_DIR/.htaccess"; } > "$WEB_DIR/.htaccess.new" \
    && mv "$WEB_DIR/.htaccess.new" "$WEB_DIR/.htaccess" || rollback "could not keep the Passenger block in .htaccess"
fi

log "alembic upgrade head"
( cd "$APP_DIR" && python -m alembic upgrade head ) || rollback "alembic upgrade head failed"

eval "$RESTART_CMD"

# ---- 4. health check: the NEW build must answer -------------------------------------------
log "health check $HEALTH_URL (expect build $EXPECT_BUILD, ${HEALTH_TIMEOUT}s)"
health_ok "$EXPECT_BUILD" || rollback "health check failed (build $EXPECT_BUILD did not answer ok)"

( cd "$APP_DIR" && python -m app.jobs.no_video_check "$APP_DIR" "$WEB_DIR" ) \
  || rollback "no-video check failed (ADR 0006)"

# Telegram webhook (ADR 0014). Never fails the deploy: notifications are not worth a rollback.
( cd "$APP_DIR" && python -m app.jobs.telegram_setup ) || log "WARNING: Telegram webhook setup failed"

# ---- 5. cron jobs (idempotent; never fails the deploy) ------------------------------------
install_cron() {
  local py marker="# smarthome-managed"
  py="$(command -v python)"
  { crontab -l 2>/dev/null | grep -v "$marker"
    echo "* * * * * cd $APP_DIR && $py -m app.jobs.expire_due >/dev/null 2>&1 $marker"
    echo "* * * * * cd $APP_DIR && $py -m app.jobs.notify >/dev/null 2>&1 $marker"
    echo "* * * * * cd $APP_DIR && $py -m app.jobs.yandex_sync >/dev/null 2>&1 $marker"
    echo "7 * * * * cd $APP_DIR && $py -m app.jobs.energy >/dev/null 2>&1 $marker"
    echo "17 3 * * * cd $APP_DIR && $py -m app.jobs.retention >/dev/null 2>&1 $marker"
    echo "41 3 * * * sh $APP_DIR/backup.sh >/dev/null 2>&1 $marker"
  } | crontab - 2>/dev/null && log "cron jobs installed" || log "WARNING: could not install cron jobs"
}
[ "${SKIP_CRON:-0}" = 1 ] || install_cron

result deployed "build $EXPECT_BUILD (previous ${PREV_BUILD:-none})"
exit 0
