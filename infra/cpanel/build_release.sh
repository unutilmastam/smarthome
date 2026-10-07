#!/bin/sh
# Assembles what goes to the cPanel account. Run from the repo root (CI does this):
#   sh infra/cpanel/build_release.sh out/
# out/api  -> Python app root (Setup Python App), WITHOUT .env (it lives only on the server)
# out/web  -> document root of the subdomain (PWA + .htaccess)
set -eu
OUT="${1:?usage: build_release.sh <out-dir>}"
rm -rf "$OUT" && mkdir -p "$OUT/api" "$OUT/web"

# Backend: only runtime files. Tests, caches and secrets never ship.
cp -R services/backend/app services/backend/migrations "$OUT/api/"
cp services/backend/alembic.ini services/backend/passenger_wsgi.py \
   services/backend/requirements.txt "$OUT/api/"
mkdir -p "$OUT/api/contracts"
cp -R packages/contracts/capabilities.json packages/contracts/roles.json \
   packages/contracts/schemas "$OUT/api/contracts/"
cp infra/cpanel/backup.sh "$OUT/api/"
cp infra/cpanel/deploy.sh "$OUT/"
# Build id: the health check waits for exactly this commit after the restart.
BUILD="${BUILD_ID:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}"
printf 'BUILD = "%s"\n' "$BUILD" > "$OUT/api/app/_build.py"
find "$OUT/api" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "$OUT/api" -name "*.pyc" -delete

# PWA (built by `npx vite build` in apps/web beforehand).
[ -f apps/web/dist/index.html ] || { echo "apps/web/dist missing: build the PWA first" >&2; exit 1; }
cp -R apps/web/dist/. "$OUT/web/"
cp infra/cpanel/web.htaccess "$OUT/web/.htaccess"

# Safety net: refuse to ship anything that looks like a secret.
if find "$OUT" \( -name ".env" -o -name "*.env" -o -name "*.pem" -o -name "*.key" -o -name "passwd" \) | grep -q .; then
  echo "refusing: secret-like file in release" >&2; exit 1
fi
echo "release ready in $OUT"
