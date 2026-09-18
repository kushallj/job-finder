# DSM Upload & Deployment Service (`jf_dsm_upload_service`)

A file receiver service running on Synology NAS that accepts Docker image tarballs from your local workstation and automatically loads them into Container Manager — enabling a full redeploy of any `kj_job_finder` service with a single command.

---

## 📁 Directory Structure

```
jf_dsm_upload_service/
├── client-deploy.mjs   # Local client: uploads .tar files to the NAS receiver
├── .env                # Local credentials (DEPLOY_SECRET_TOKEN, DEPLOY_API_URL)
├── .env.example        # Template for the above
└── README.md           # This guide
```

---

## 🚀 How It Works

When a `.tar` file is uploaded via `POST /upload` with `subfolder=kj_job_finder`:

1. Verifies the archive is a valid POSIX `ustar` tar
2. Copies the archive to `/volume1/docker/kj_job_finder/x_deployment/<image>.tar`
3. Stops and removes the existing container + image
4. Runs `docker load -i <image>.tar` to load the new image
5. Brings the service back up: `docker compose up -d <service>`

All 8 services can be redeployed individually or all at once.

---

## ⚙️ Synology DSM Container Manager Configuration

The receiver runs on the NAS as defined in [`dsm_files/docker-compose.yml`](dsm_files/docker-compose.yml):

```yaml
services:
  dsm_file_receiver:
    image: dsm_file_receiver:latest
    container_name: dsm_file_receiver
    restart: always
    ports:
      - "9090:9090"
    volumes:
      - /volume1/api_files_receiver:/volume1/api_files_receiver
      - /volume1/docker/kj_job_finder:/volume1/docker/kj_job_finder
      - /var/run/docker.sock:/var/run/docker.sock
```

---

## 💻 Client Upload Usage (Run Locally)

Make sure `.env` in this directory contains:

```env
DEPLOY_SECRET_TOKEN=your-token-here
DEPLOY_API_URL=https://testarea.ddns.net/upload
```

### Upload all 8 images in batch

```bash
npm run dsm:upload
```

This runs `client-deploy.mjs` for every `.tar` in `dsm_deploy/docker_images/`.

### Upload a single image

```bash
node dsm_deploy/jf_dsm_upload_service/client-deploy.mjs \
  --file=dsm_deploy/docker_images/jf_api.tar \
  --subfolder=kj_job_finder
```

### Available image tarballs

| Tar file                   | Service redeployed  |
| :------------------------- | :------------------ |
| `jf_api.tar`               | `api`               |
| `jf_frontend.tar`          | `frontend`          |
| `jf_celery_worker.tar`     | `celery_worker`     |
| `jf_celery_beat.tar`       | `celery_beat`       |
| `jf_celery_flower.tar`     | `celery_flower`     |
| `jf_telegram_daemon.tar`   | `telegram_daemon`   |
| `jf_postgres.tar`          | `postgres`          |
| `jf_redis.tar`             | `redis`             |
