#!/usr/bin/env bash
# Manual install / update from the release zip (cPanel Terminal, works from an iPad).
#
#   cd ~ && unzip -o smarthome-*.zip && bash ~/smarthome-release/install.sh
#
# Asks a few questions (remembered in ~/sh-deploy/install.conf, no secrets there), then runs
# the SAME deploy.sh that GitHub Actions uses: backup -> code -> migrations -> restart ->
# health check -> automatic rollback on failure. On the first run it also creates the
# owner account. Secrets are generated on the server and stay only in the app's .env.
#
# Non-interactive (tests / scripted): set SH_NONINTERACTIVE=1 and the variables below.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
STATE_DIR="${STATE_DIR:-$HOME/sh-deploy}"
CONF="$STATE_DIR/install.conf"
mkdir -p "$STATE_DIR" && chmod 700 "$STATE_DIR"
[ -f "$CONF" ] && . "$CONF"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ask() {  # ask VAR "Question" "default"
  local var="$1" q="$2" def="${3:-}" cur="${!1:-}"
  [ -n "$cur" ] && def="$cur"
  if [ "${SH_NONINTERACTIVE:-0}" = 1 ]; then printf -v "$var" '%s' "$def"; return; fi
  local ans
  read -r -p "$q${def:+ [$def]}: " ans
  printf -v "$var" '%s' "${ans:-$def}"
}
ask_secret() {  # ask_secret VAR "Question"   (not echoed, not saved)
  local var="$1" q="$2"
  if [ "${SH_NONINTERACTIVE:-0}" = 1 ]; then return; fi
  local ans
  read -r -s -p "$q: " ans; echo
  printf -v "$var" '%s' "$ans"
}

[ -f "$HERE/deploy.sh" ] && [ -f "$HERE/api/passenger_wsgi.py" ] && [ -f "$HERE/web/index.html" ] \
  || { echo "Bu papka to'liq reliz emas: $HERE (api/, web/, deploy.sh kerak)"; exit 1; }
BUILD="$(sed -n 's/^BUILD = "\(.*\)"$/\1/p' "$HERE/api/app/_build.py")"

say "SmartHome o'rnatish / yangilash (versiya ${BUILD:0:12})"
ask DOMAIN   "Sayt manzili (subdomen, https:// siz)" "${DOMAIN:-home.example.uz}"
ask APP_DIR  "Python ilova papkasi (Setup Python App → Application root)" "${APP_DIR:-$HOME/smarthome-api}"
ask WEB_DIR  "Sayt papkasi (subdomen Document Root)" "${WEB_DIR:-$HOME/$DOMAIN}"
case "$APP_DIR" in /*) ;; *) APP_DIR="$HOME/$APP_DIR" ;; esac
case "$WEB_DIR" in /*) ;; *) WEB_DIR="$HOME/$WEB_DIR" ;; esac

if [ -z "${VENV_ACTIVATE:-}" ]; then
  VENV_ACTIVATE="$(ls -1d "$HOME/virtualenv/$(basename "$APP_DIR")"/*/bin/activate 2>/dev/null | sort -V | tail -1)"
fi
ask VENV_ACTIVATE "Virtualenv activate yo'li (Setup Python App sahifasining tepasida)" "$VENV_ACTIVATE"
[ -f "$VENV_ACTIVATE" ] || { echo "Topilmadi: $VENV_ACTIVATE — avval cPanel → Setup Python App da ilova yarating."; exit 1; }

INIT_DATABASE_URL="${INIT_DATABASE_URL:-}"
if [ ! -f "$APP_DIR/.env" ] && [ -z "$INIT_DATABASE_URL" ]; then
  say "Birinchi o'rnatish: PostgreSQL ma'lumotlari (cPanel → PostgreSQL Databases)"
  ask DB_NAME "Baza nomi" "${DB_NAME:-}"
  ask DB_USER "Baza foydalanuvchisi" "${DB_USER:-}"
  DB_PASS=""; ask_secret DB_PASS "Foydalanuvchi paroli (ko'rinmaydi)"
  INIT_DATABASE_URL="$(DBU="$DB_USER" DBP="$DB_PASS" DBN="$DB_NAME" python3 -c '
import os, urllib.parse as u
print("postgresql+psycopg://%s:%s@localhost:5432/%s" % (u.quote(os.environ["DBU"], safe=""),
      u.quote(os.environ["DBP"], safe=""), u.quote(os.environ["DBN"], safe="")))')"
fi

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
if [ -z "$TELEGRAM_BOT_TOKEN" ] && ! grep -q '^TELEGRAM_BOT_TOKEN=.' "$APP_DIR/.env" 2>/dev/null; then
  ask_secret TELEGRAM_BOT_TOKEN "Telegram bot tokeni (@BotFather; bo'sh qoldirsangiz keyin qo'shasiz)"
fi

# Remember the answers (no passwords, no tokens).
( umask 077; printf 'DOMAIN=%q\nAPP_DIR=%q\nWEB_DIR=%q\nVENV_ACTIVATE=%q\n' \
    "$DOMAIN" "$APP_DIR" "$WEB_DIR" "$VENV_ACTIVATE" > "$CONF" )

say "O'rnatilmoqda: zaxira → kod → migratsiya → qayta ishga tushirish → tekshiruv (1–3 daqiqa)"
APP_DIR="$APP_DIR" WEB_DIR="$WEB_DIR" STAGE_DIR="$HERE" STATE_DIR="$STATE_DIR" \
VENV_ACTIVATE="$VENV_ACTIVATE" EXPECT_BUILD="$BUILD" \
HEALTH_URL="${HEALTH_URL:-https://$DOMAIN/api/v1/health}" \
INIT_DATABASE_URL="$INIT_DATABASE_URL" PUBLIC_BASE_URL="https://$DOMAIN" \
TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
  bash "$HERE/deploy.sh" | tee "$STATE_DIR/last-install.log"
code=${PIPESTATUS[0]}
case "$code" in
  0)  say "✅ O'rnatildi: https://$DOMAIN" ;;
  10) say "⚠️ Yangi versiya ishlamadi va AVTOMATIK QAYTARILDI (eski versiya va baza joyida). Log: $STATE_DIR/last-install.log"; exit 10 ;;
  11) say "⏸ Hech narsa o'zgartirilmadi (sababi yuqorida). Log: $STATE_DIR/last-install.log"; exit 11 ;;
  *)  say "🆘 Xato va qaytarish ham muvaffaqiyatsiz. docs/runbooks/backup-restore.md ga qarang. Log: $STATE_DIR/last-install.log"; exit "$code" ;;
esac

# First run: the owner account (nobody can log in without it).
. "$VENV_ACTIVATE"
USERS="$(cd "$APP_DIR" && python -c '
from sqlalchemy import func, select
from app.core.config import get_settings
from app.db.session import Database
from app.models import User
db = next(Database(get_settings()).session())
print(db.scalar(select(func.count()).select_from(User)))' 2>/dev/null || echo "?")"
if [ "$USERS" = "0" ]; then
  say "Birinchi foydalanuvchi — uy egasi"
  ask OWNER_EMAIL "Email" "${OWNER_EMAIL:-}"
  ask OWNER_NAME "Ismingiz" "${OWNER_NAME:-}"
  ask HOME_NAME "Uy nomi" "${HOME_NAME:-Uy}"
  if [ "${SH_NONINTERACTIVE:-0}" = 1 ]; then
    printf '%s\n' "${OWNER_PASSWORD:?}" | (cd "$APP_DIR" && python -m app.cli create-owner --email "$OWNER_EMAIL" \
      --name "$OWNER_NAME" --home-name "$HOME_NAME" --password-stdin)
  else
    (cd "$APP_DIR" && python -m app.cli create-owner --email "$OWNER_EMAIL" --name "$OWNER_NAME" --home-name "$HOME_NAME")
  fi
fi
say "Telefonda oching: https://$DOMAIN → kiring → Sozlamalar → PIN kod o'rnating."
