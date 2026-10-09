#!/usr/bin/env bash
# Manual install / update from the release zip (cPanel Terminal, works from a phone).
#
#   bash ~/smarthome-release/install.sh
#
# Asks everything FIRST (subdomain, database password, owner email + password), checks it
# (domain format, https certificate, Python app, database login) and only then runs the
# SAME deploy.sh that GitHub Actions uses: backup -> code -> migrations -> restart ->
# health check -> automatic rollback on failure. Nothing on the server changes until every
# check has passed. If the database or its user is missing, it offers to create them with
# cPanel's own `uapi`. On the first run it creates the owner account.
#
# Answers (no secrets) are remembered in ~/sh-deploy/install.conf as defaults; a value given
# in the environment always wins. Secrets are generated on the server and stay only in the
# app's .env.
#
# Non-interactive (tests / scripted): SH_NONINTERACTIVE=1 plus the variables below.
# SH_DRY_RUN=1 stops after the checks (prints the plan, changes nothing).
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
STATE_DIR="${STATE_DIR:-$HOME/sh-deploy}"
CONF="$STATE_DIR/install.conf"
NI="${SH_NONINTERACTIVE:-0}"
CP_USER="${CP_USER:-$(id -un)}"
mkdir -p "$STATE_DIR" && chmod 700 "$STATE_DIR"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok() { printf '  ✓ %s\n' "$*"; }
stop() { printf '\n⏸ %s\n  Serverda hech narsa o'"'"'zgartirilmadi.\n' "$*"; exit 11; }
ask() {  # ask VAR "Question" "default"
  local var="$1" q="$2" def="${3:-}" cur="${!1:-}"
  [ -n "$cur" ] && def="$cur"
  if [ "$NI" = 1 ]; then printf -v "$var" '%s' "$def"; return; fi
  local ans
  read -r -p "$q${def:+ [$def]}: " ans
  printf -v "$var" '%s' "${ans:-$def}"
}
ask_secret() {  # ask_secret VAR "Question"   (not echoed, never saved)
  local var="$1" q="$2"
  [ "$NI" = 1 ] && return
  local ans
  read -r -s -p "$q: " ans; echo
  printf -v "$var" '%s' "$ans"
}
uapi_json() {  # uapi_json Module function args...  -> prints .result.data as JSON, fails on error
  command -v uapi >/dev/null 2>&1 || return 1
  uapi --output=json "$@" 2>/dev/null | python3 -c '
import json, sys
r = json.load(sys.stdin).get("result") or {}
if not r.get("status"):
    sys.stderr.write("; ".join(r.get("errors") or ["uapi failed"]) + "\n"); sys.exit(1)
print(json.dumps(r.get("data")))'
}

[ -f "$HERE/deploy.sh" ] && [ -f "$HERE/api/passenger_wsgi.py" ] && [ -f "$HERE/web/index.html" ] \
  || { echo "Bu papka to'liq reliz emas: $HERE (api/, web/, deploy.sh kerak)"; exit 1; }
BUILD="$(sed -n 's/^BUILD = "\(.*\)"$/\1/p' "$HERE/api/app/_build.py")"

# Remembered answers are defaults only: a value given in the environment wins.
if [ -f "$CONF" ]; then
  for _k in DOMAIN APP_DIR WEB_DIR VENV_ACTIVATE; do
    [ -n "${!_k:-}" ] || eval "$(grep -E "^$_k=" "$CONF" | head -1)"
  done
fi

say "SmartHome o'rnatish / yangilash (versiya ${BUILD:0:12})"

# ---- 1. subdomain ------------------------------------------------------------------------
while :; do
  ask DOMAIN "Subdomen (masalan smy.itcode.uz)" "${DOMAIN:-}"
  DOMAIN="$(printf '%s' "$DOMAIN" | tr 'A-Z' 'a-z' | sed -e 's#^[a-z]*://##' -e 's#^www\.##' -e 's#/.*$##' -e 's/[[:space:]]//g')"
  if printf '%s' "$DOMAIN" | grep -Eq '^[a-z0-9-]+(\.[a-z0-9-]+)+$'; then break; fi
  echo "  ✗ \"$DOMAIN\" — bu sayt manzili emas. Masalan: smy.itcode.uz"
  DOMAIN=""
  [ "$NI" = 1 ] && stop "Subdomen noto'g'ri."
done
ok "Sayt: https://$DOMAIN"

# ---- 2. Python app (cPanel → Setup Python App) -----------------------------------------
APP_DIR="${APP_DIR:-$HOME/smarthome-api}"
case "$APP_DIR" in /*) ;; *) APP_DIR="$HOME/$APP_DIR" ;; esac
if [ -z "${VENV_ACTIVATE:-}" ] || [ ! -f "$VENV_ACTIVATE" ]; then
  VENV_ACTIVATE="$(ls -1d "$HOME/virtualenv/$(basename "$APP_DIR")"/*/bin/activate 2>/dev/null | sort -V | tail -1)"
fi
[ -n "$VENV_ACTIVATE" ] && [ -f "$VENV_ACTIVATE" ] || stop "Python ilova topilmadi.
  cPanel → Setup Python App → CREATE APPLICATION:
    Python version: 3.10 yoki yuqori;  Application root: $(basename "$APP_DIR")
    Application URL: $DOMAIN / api;  Startup file: passenger_wsgi.py;  Entry point: application
  So'ng shu buyruqni qayta ishga tushiring."
ok "Python ilova: $APP_DIR"

# ---- 3. web root = the subdomain's Document Root (asked from cPanel, not typed) ---------
if [ -z "${WEB_DIR:-}" ]; then
  WEB_DIR="$(uapi_json DomainInfo single_domain_data domain="$DOMAIN" \
    | python3 -c 'import json,sys; print((json.load(sys.stdin) or {}).get("documentroot") or "")' 2>/dev/null)"
  [ -n "$WEB_DIR" ] || WEB_DIR="$HOME/$DOMAIN"
fi
case "$WEB_DIR" in /*) ;; *) WEB_DIR="$HOME/$WEB_DIR" ;; esac
ok "Sayt papkasi: $WEB_DIR"

# ---- 4. https must already work (otherwise the final health check fails) ---------------
if [ "${SH_SKIP_HTTPS_CHECK:-0}" != 1 ]; then
  curl -sS -o /dev/null --max-time 20 "https://$DOMAIN/" 2>"$STATE_DIR/https-check.err"
  case $? in
    0) ok "https ishlayapti" ;;
    6) stop "\"$DOMAIN\" internetda topilmadi. cPanel → Domains da shu subdomen yaratilganini tekshiring (yangi subdomen 5–15 daqiqada ishlay boshlaydi)." ;;
    35|51|53|58|59|60|77|80|82|83|90|91)
       uapi_json SSL start_autossl_check >/dev/null 2>&1 && echo "  AutoSSL ishga tushirildi."
       stop "\"$DOMAIN\" uchun SSL sertifikat hali yo'q. cPanel → SSL/TLS Status → $DOMAIN → Run AutoSSL, 5–10 daqiqa kutib qayta urining." ;;
    *) stop "https://$DOMAIN ochilmadi: $(tail -1 "$STATE_DIR/https-check.err")" ;;
  esac
fi

# ---- 5. database (first install only: afterwards it lives in the app's .env) -----------
INIT_DATABASE_URL="${INIT_DATABASE_URL:-}"
FIRST=0; [ -f "$APP_DIR/.env" ] || FIRST=1
db_try() {  # db_try HOST -> 0 if the login works; error text in $DB_ERR
  DB_ERR="$(PGPASSWORD="$DB_PASS" PGCONNECT_TIMEOUT=10 psql ${1:+-h "$1"} -U "$DB_USER" -d "$DB_NAME" \
    -tAc 'select 1' 2>&1 >/dev/null)"
}
db_login() {  # sets DB_HOST (127.0.0.1 or "" = local socket); 'localhost' may be ::1, rejected by cPanel
  DB_HOST=127.0.0.1; db_try "$DB_HOST" && return 0
  local first="$DB_ERR"; DB_HOST=""; db_try "" && return 0
  DB_ERR="$first"; return 1
}
db_create() {  # with cPanel's own API; each step skipped when it already exists
  command -v uapi >/dev/null 2>&1 || return 1
  local have
  have="$(uapi_json Postgresql list_databases)" || return 1
  printf '%s' "$have" | grep -q "\"$DB_NAME\"" \
    || { uapi_json Postgresql create_database name="$DB_NAME" >/dev/null && ok "Baza yaratildi: $DB_NAME"; } || return 1
  have="$(uapi_json Postgresql list_users)" || return 1
  printf '%s' "$have" | grep -q "\"$DB_USER\"" \
    || { uapi_json Postgresql create_user name="$DB_USER" password="$DB_PASS" >/dev/null && ok "Foydalanuvchi yaratildi: $DB_USER"; } || return 1
  uapi_json Postgresql grant_all_privileges user="$DB_USER" database="$DB_NAME" >/dev/null \
    && ok "$DB_USER → $DB_NAME ulandi"
}
if [ "$FIRST" = 1 ] && [ -z "$INIT_DATABASE_URL" ]; then
  say "PostgreSQL baza"
  base="$(printf '%s' "${DOMAIN%%.*}" | tr -c 'a-z0-9_\n' '_')"
  ask DB_NAME "Baza nomi" "${DB_NAME:-${CP_USER}_${base}}"
  ask DB_USER "Baza foydalanuvchisi" "${DB_USER:-${CP_USER}_${base}}"
  DB_PASS="${DB_PASS:-}"
  while [ -z "$DB_PASS" ]; do
    ask_secret DB_PASS "Baza foydalanuvchisi paroli (ko'rinmaydi; yangi bo'lsa — o'ylab toping)"
    [ "$NI" = 1 ] && [ -z "$DB_PASS" ] && stop "Baza paroli berilmadi."
  done
  command -v psql >/dev/null 2>&1 || stop "Serverda psql yo'q: hosting yordamiga yozing."
  DB_OK=0; db_login && DB_OK=1
  if [ "$DB_OK" = 0 ] && command -v uapi >/dev/null 2>&1; then
    echo "  Bazaga kirib bo'lmadi: ${DB_ERR##*FATAL:  }"
    yn="y"
    [ "$NI" = 1 ] || read -r -p "  Baza va foydalanuvchini cPanel orqali o'zim yaratib/ulab qo'yaymi? [Y/n]: " yn
    case "$yn" in [nN]*) ;; *) db_create && db_login && DB_OK=1 ;; esac
  fi
  if [ "$DB_OK" = 0 ]; then
    case "$DB_ERR" in
      *"password authentication failed"*) stop "Baza paroli noto'g'ri. cPanel → PostgreSQL Databases → $DB_USER → Change Password, keyin qayta urining." ;;
      *"does not exist"*) stop "\"$DB_NAME\" bazasi yoki \"$DB_USER\" foydalanuvchisi yo'q. cPanel → PostgreSQL Databases da yarating." ;;
      *"pg_hba.conf"*) stop "\"$DB_USER\" foydalanuvchisi \"$DB_NAME\" bazasiga ulanmagan. cPanel → PostgreSQL Databases → Add User To Database." ;;
      *) stop "Bazaga ulanib bo'lmadi: $DB_ERR" ;;
    esac
  fi
  ok "Baza ishlayapti ($DB_USER@${DB_HOST:-socket}/$DB_NAME)"
  INIT_DATABASE_URL="$(DBU="$DB_USER" DBP="$DB_PASS" DBN="$DB_NAME" DBH="${DB_HOST:+$DB_HOST:5432}" python3 -c '
import os, urllib.parse as u
print("postgresql+psycopg://%s:%s@%s/%s" % (u.quote(os.environ["DBU"], safe=""),
      u.quote(os.environ["DBP"], safe=""), os.environ["DBH"], u.quote(os.environ["DBN"], safe="")))')"
fi

# ---- 6. owner account (asked now, created after the deploy; nobody can log in without it)
OWNER_EMAIL="${OWNER_EMAIL:-}"; OWNER_PASSWORD="${OWNER_PASSWORD:-}"
if [ "$FIRST" = 1 ]; then
  say "Uy egasi (ilovaga shu email va parol bilan kirasiz)"
  while :; do
    ask OWNER_EMAIL "Email" "$OWNER_EMAIL"
    printf '%s' "$OWNER_EMAIL" | grep -Eq '^[^@ ]+@[^@ ]+\.[^@ ]+$' && break
    echo "  ✗ Email noto'g'ri."; OWNER_EMAIL=""
    [ "$NI" = 1 ] && stop "Email noto'g'ri."
  done
  while [ "$NI" != 1 ]; do
    ask_secret OWNER_PASSWORD "Ilovaga kirish paroli (kamida 10 belgi, ko'rinmaydi)"
    if [ "${#OWNER_PASSWORD}" -lt 10 ]; then echo "  ✗ Kamida 10 belgi kerak."; continue; fi
    ask_secret P2 "Parolni yana bir marta"
    [ "$OWNER_PASSWORD" = "$P2" ] && break
    echo "  ✗ Parollar bir xil emas."
  done
  [ "${#OWNER_PASSWORD}" -ge 10 ] || stop "Ilova paroli kamida 10 belgi bo'lishi kerak."
fi

# Remember the answers (no passwords, no tokens).
( umask 077; printf 'DOMAIN=%q\nAPP_DIR=%q\nWEB_DIR=%q\nVENV_ACTIVATE=%q\n' \
    "$DOMAIN" "$APP_DIR" "$WEB_DIR" "$VENV_ACTIVATE" > "$CONF" )

if [ "${SH_DRY_RUN:-0}" = 1 ]; then
  printf 'PLAN domain=%s app=%s web=%s venv=%s first=%s db=%s\n' "$DOMAIN" "$APP_DIR" "$WEB_DIR" \
    "$VENV_ACTIVATE" "$FIRST" "$(printf '%s' "$INIT_DATABASE_URL" | sed 's#://[^:]*:[^@]*@#://***@#')"
  exit 0
fi

# ---- 7. deploy (the same script as the automatic GitHub deploy) ------------------------
say "O'rnatilmoqda: zaxira → kod → migratsiya → qayta ishga tushirish → tekshiruv (2–5 daqiqa)"
echo "  Telefon ekrani o'chmasin va bu sahifani yopmang."
rmdir "$STATE_DIR/lock" 2>/dev/null
APP_DIR="$APP_DIR" WEB_DIR="$WEB_DIR" STAGE_DIR="$HERE" STATE_DIR="$STATE_DIR" \
VENV_ACTIVATE="$VENV_ACTIVATE" EXPECT_BUILD="$BUILD" \
HEALTH_URL="${HEALTH_URL:-https://$DOMAIN/api/v1/health}" \
INIT_DATABASE_URL="$INIT_DATABASE_URL" PUBLIC_BASE_URL="https://$DOMAIN" \
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}" \
  bash "$HERE/deploy.sh" | tee "$STATE_DIR/last-install.log"
code=${PIPESTATUS[0]}
case "$code" in
  0)  ;;
  10) say "⚠️ Yangi versiya ishlamadi va AVTOMATIK QAYTARILDI. Log: $STATE_DIR/last-install.log"; exit 10 ;;
  11) say "⏸ Hech narsa o'zgartirilmadi (sababi yuqorida). Log: $STATE_DIR/last-install.log"; exit 11 ;;
  *)  say "🆘 Xato. Log: $STATE_DIR/last-install.log — shu faylni yuboring."; exit "$code" ;;
esac

# ---- 8. owner: created, or (same email already there) its password set ----------------
if [ "$FIRST" = 1 ] && [ -n "$OWNER_EMAIL" ] && [ -n "$OWNER_PASSWORD" ]; then
  . "$VENV_ACTIVATE"
  printf '%s\n' "$OWNER_PASSWORD" | (cd "$APP_DIR" && python -m app.cli create-owner \
      --email "$OWNER_EMAIL" --name "${OWNER_NAME:-Uy egasi}" --home-name "${HOME_NAME:-Uy}" \
      --password-stdin) || { say "🆘 Uy egasini yaratib bo'lmadi (yuqoridagi xato)."; exit 13; }
fi
say "✅ O'rnatildi: https://$DOMAIN"
[ "$FIRST" = 1 ] && echo "  Kirish: $OWNER_EMAIL va siz kiritgan parol."
echo "  Keyin: Sozlamalar → PIN kod o'rnating."
