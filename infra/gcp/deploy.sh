#!/usr/bin/env bash
# Deploy one commit on the VM (run as the app user):
#
#   sudo -u jobify bash /opt/jobify/infra/gcp/deploy.sh [git-ref]     # default: origin/main
#
# CI calls this through the forced-command key (infra/gcp/ci_deploy.sh) with the exact commit
# SHA that passed CI. Order: code -> backend deps -> frontend build -> migrations -> settings
# check -> PM2 reload -> /readyz. Until the reload, the old processes keep serving.
#
# Rollback: the deployed SHAs are recorded in $APP_DIR/.deploy/{current,previous}. If any step
# fails (or /readyz never turns ready), the script redeploys the previous SHA automatically.
# Migrations are NOT reversed: keep them backward compatible (expand -> deploy -> contract),
# so the previous release can run against the newer schema.
set -euo pipefail

APP_DIR="${JOBIFY_DIR:-/opt/jobify}"
REF="${1:-origin/main}"
STATE="$APP_DIR/.deploy"
ROLLING_BACK="${JOBIFY_ROLLING_BACK:-0}"
cd "$APP_DIR"
mkdir -p "$STATE"

[ -f .env ] || { echo "missing $APP_DIR/.env (copy .env.production.example)"; exit 1; }

# One deploy at a time on this machine (CI also serialises, this covers manual runs).
exec 9>"$STATE/lock"
flock -n 9 || { echo "!! another deploy is running"; exit 1; }

PREV="$(cat "$STATE/current" 2>/dev/null || git rev-parse HEAD)"

rollback() {
  local code=$?
  trap - ERR
  if [ "$ROLLING_BACK" = "1" ] || [ -z "$PREV" ] || [ "$PREV" = "${TARGET:-}" ]; then
    echo "!! deploy failed (exit $code); no rollback target"; exit "$code"
  fi
  echo "!! deploy of ${TARGET:-$REF} failed (exit $code): rolling back to $PREV"
  flock -u 9
  JOBIFY_ROLLING_BACK=1 bash "$APP_DIR/infra/gcp/deploy.sh" "$PREV" || echo "!! ROLLBACK FAILED: fix by hand (pm2 logs jobify-api)"
  exit "$code"
}
trap rollback ERR

echo "== code: $REF"
git fetch --prune origin
TARGET="$(git rev-parse --verify "$REF^{commit}")"
git checkout --force --detach "$TARGET"
echo "   $PREV -> $TARGET"

echo "== backend dependencies"
[ -d .venv ] || python3.12 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

echo "== frontend build (VITE_* values are baked in at build time)"
set -a; [ -f jobify/.env.production ] && . jobify/.env.production; set +a
( cd jobify && npm ci --no-audit --no-fund && npm run build )

echo "== database migrations"
.venv/bin/alembic upgrade head

echo "== production settings check (API refuses to start if unsafe)"
ENV=production .venv/bin/python -c "import main" >/dev/null

echo "== processes"
if pm2 describe jobify-api >/dev/null 2>&1; then
  pm2 reload infra/gcp/ecosystem.config.js --update-env
else
  pm2 start infra/gcp/ecosystem.config.js
fi
pm2 save

echo "== health"
ready=0
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/readyz >/dev/null; then ready=1; break; fi
  sleep 2
done
[ "$ready" = 1 ] || { echo "!! /readyz did not turn ready (pm2 logs jobify-api --lines 100)"; false; }

if [ "$PREV" != "$TARGET" ]; then echo "$PREV" > "$STATE/previous"; fi
echo "$TARGET" > "$STATE/current"
echo "$(date -u +%FT%TZ) $TARGET$([ "$ROLLING_BACK" = 1 ] && echo " (rollback)")" >> "$STATE/history"
pm2 status
echo "deployed $TARGET"
