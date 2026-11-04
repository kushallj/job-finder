#!/bin/bash
# scripts/vc_cron.sh — 100 Global VC Firms Autonomous Founder Batch Cron Runner
#
# Periodically harvests batches of 50 verified founders across 100 global VC portfolios.
# Logs streamed to logs/vc_cron.log.
#
# Usage:
#   bash scripts/vc_cron.sh                      # Runs continuous daemon (50 founders every 60s)
#   bash scripts/vc_cron.sh --interval 300       # Harvests a batch of 50 every 5 minutes
#   bash scripts/vc_cron.sh --once               # Runs a single batch of 50 founders and exits
#   bash scripts/vc_cron.sh --max-batches 5      # Runs 5 batches and exits

set -euo pipefail

PROJECT_DIR="/Users/kushalljain/Desktop/job-finder"
cd "$PROJECT_DIR"

PYTHON="${PROJECT_DIR}/.venv/bin/python"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/vc_cron.log"

mkdir -p "$LOG_DIR"

echo "==================================================" >> "$LOG_FILE"
echo "VC Founder Batch Cron Runner started at $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "==================================================" >> "$LOG_FILE"

export PYTHONPATH="$PROJECT_DIR"

exec "$PYTHON" -m src.cli vc-cron "$@"
