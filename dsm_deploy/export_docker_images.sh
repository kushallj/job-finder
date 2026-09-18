#!/usr/bin/env bash
set -euo pipefail

# Determine Docker binary
DOCKER_BIN="$(command -v docker || echo "/Applications/Docker.app/Contents/Resources/bin/docker")"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/docker_images"
mkdir -p "${OUTPUT_DIR}"

# 1. Remove existing tar files if any exist
echo "🧹 Removing existing .tar files from ${OUTPUT_DIR}..."
find "${OUTPUT_DIR}" -maxdepth 1 -name "*.tar" -delete
echo "✅ Existing .tar files cleared."

# 2. Load VITE_API_BASE_URL from .env.synology (override via env var if set externally)
ENV_FILE="${SCRIPT_DIR}/.env.synology"
if [[ -z "${VITE_API_BASE_URL:-}" && -f "${ENV_FILE}" ]]; then
  VITE_API_BASE_URL="$(grep -E '^VITE_API_BASE_URL=' "${ENV_FILE}" | cut -d'=' -f2- | tr -d '[:space:]')"
fi
VITE_API_BASE_URL="${VITE_API_BASE_URL:-https://testarea.ddns.net}"
echo "🌐 Using VITE_API_BASE_URL=${VITE_API_BASE_URL}"

# 3. Build Docker images (ensuring linux/amd64 platform for Synology NAS)
echo ""
echo "🔨 Building Docker images (linux/amd64)..."
DOCKER_DEFAULT_PLATFORM=linux/amd64 "${DOCKER_BIN}" compose -f "${ROOT_DIR}/docker-compose.yml" build \
  --build-arg VITE_API_BASE_URL="${VITE_API_BASE_URL}"

# 4. Export Docker images to .tar archives
echo ""
echo "🚀 Saving Docker images to ${OUTPUT_DIR}/*.tar..."

IMAGES=(
  "jf_api:latest" 
  "jf_celery_beat:latest"
  "jf_celery_flower:latest"
  "jf_celery_worker:latest"
  "jf_frontend:latest"
   "jf_postgres:latest"
  "jf_redis:latest"
  "jf_telegram_daemon:latest"
)

for IMAGE in "${IMAGES[@]}"; do
  SERVICE_NAME="$(echo "${IMAGE}" | cut -d':' -f1)"
  TAR_FILE="${OUTPUT_DIR}/${SERVICE_NAME}.tar"
  echo "📦 Exporting ${IMAGE} -> ${TAR_FILE}..."
  "${DOCKER_BIN}" save -o "${TAR_FILE}" "${IMAGE}"
  echo "✅ Saved ${TAR_FILE} ($(du -h "${TAR_FILE}" | cut -f1))"
done

echo ""
echo "🎉 All Docker images have been built and exported into '${OUTPUT_DIR}/':"
ls -lh "${OUTPUT_DIR}"/*.tar
