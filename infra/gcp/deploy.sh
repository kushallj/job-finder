#!/usr/bin/env bash
# Deploy the current main branch on the VM (run as the app user):
#
#   sudo -u jobify bash /opt/jobify/infra/gcp/deploy.sh [git-ref]
#
# Order matters: dependencies -> frontend build -> migrations -> process reload. A failed
# step stops the deploy before traffic moves (set -e), and the old processes keep serving.
set -euo pipefail

APP_DIR="${JOBIFY_DIR:-/opt/jobify}"
REF="${1:-origin/main}"
cd "$APP_DIR"

[ -f .env ] || { echo "missing $APP_DIR/.env (copy .env.production.example)"; exit 1; }

echo "== code: $REF"
git fetch --prune origin
git checkout --force "$REF"

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
for i in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8000/readyz >/dev/null; then echo "ready"; pm2 status; exit 0; fi
  sleep 2
done
echo "!! /readyz did not turn ready; check: pm2 logs jobify-api --lines 100"
exit 1
