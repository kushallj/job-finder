#!/usr/bin/env bash
# Forced command for the GitHub Actions deploy key. setup_vm.sh installs this root-owned at
# /usr/local/bin/jobify-ci-deploy and pins the CI key to it in ~jobify/.ssh/authorized_keys:
#
#   command="/usr/local/bin/jobify-ci-deploy",restrict ssh-ed25519 AAAA... github-actions
#
# so a leaked CI key can only run these three actions, never a shell:
#   deploy <40-char commit sha>   deploy exactly that commit (it must be on origin/main)
#   rollback                      redeploy the previously deployed commit
#   status                        print the deployed commit and process status
set -euo pipefail

APP_DIR="${JOBIFY_DIR:-/opt/jobify}"
DEPLOY="$APP_DIR/infra/gcp/deploy.sh"
read -r action arg extra <<<"${SSH_ORIGINAL_COMMAND:-}"
[ -z "${extra:-}" ] || { echo "too many arguments"; exit 2; }

case "${action:-}" in
  deploy)
    [[ "${arg:-}" =~ ^[0-9a-f]{40}$ ]] || { echo "usage: deploy <40-char commit sha>"; exit 2; }
    cd "$APP_DIR" && git fetch --quiet origin main
    git merge-base --is-ancestor "$arg" origin/main || { echo "refusing: $arg is not on origin/main"; exit 2; }
    exec bash "$DEPLOY" "$arg"
    ;;
  rollback)
    [ -z "${arg:-}" ] || { echo "rollback takes no arguments"; exit 2; }
    prev="$(cat "$APP_DIR/.deploy/previous" 2>/dev/null || true)"
    [ -n "$prev" ] || { echo "no previous deploy recorded"; exit 2; }
    exec bash "$DEPLOY" "$prev"
    ;;
  status)
    [ -z "${arg:-}" ] || { echo "status takes no arguments"; exit 2; }
    echo "current:  $(cat "$APP_DIR/.deploy/current" 2>/dev/null || echo none)"
    echo "previous: $(cat "$APP_DIR/.deploy/previous" 2>/dev/null || echo none)"
    tail -n 5 "$APP_DIR/.deploy/history" 2>/dev/null || true
    pm2 status
    ;;
  *)
    echo "allowed: deploy <sha> | rollback | status"; exit 2
    ;;
esac
