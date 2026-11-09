// PM2 process file for a single GCP Compute Engine VM (see infra/gcp/README section in
// the root README.md and CLAUDE.md "Production on GCP").
//
//   pm2 start infra/gcp/ecosystem.config.js      # first start
//   pm2 reload infra/gcp/ecosystem.config.js     # zero-downtime API reload on deploy
//   pm2 logs | pm2 monit | pm2 status
//
// The Jobify frontend is static (vite build -> jobify/dist) and is served by nginx, so it is
// not a PM2 process. Secrets live in /opt/jobify/.env (read by src/config.py); PM2 only sets
// non-secret runtime switches. ENV=production makes the API refuse to start when a required
// setting is missing (src/production_checks.py) and log JSON to stdout, which PM2 captures.

const APP_DIR = process.env.JOBIFY_DIR || "/opt/jobify";
const VENV = `${APP_DIR}/.venv/bin`;
const LOG_DIR = process.env.JOBIFY_LOG_DIR || "/var/log/jobify";

const common = {
  cwd: APP_DIR,
  interpreter: "none",          // run the venv binaries directly
  autorestart: true,
  max_restarts: 10,
  min_uptime: "20s",
  restart_delay: 5000,
  kill_timeout: 30000,          // let in-flight requests / tasks finish on reload
  merge_logs: true,
  time: true,                   // timestamp lines in PM2 log files
  env: {
    ENV: "production",
    PYTHONUNBUFFERED: "1",
  },
};

module.exports = {
  apps: [
    {
      ...common,
      name: "jobify-api",
      script: `${VENV}/uvicorn`,
      // 127.0.0.1 only: nginx is the public entry point. --proxy-headers trusts
      // X-Forwarded-* from nginx on the same host for client IP and scheme.
      args: "main:app --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips=127.0.0.1 --no-server-header",
      max_memory_restart: "1500M",
      out_file: `${LOG_DIR}/api.out.log`,
      error_file: `${LOG_DIR}/api.err.log`,
    },
    {
      ...common,
      name: "jobify-worker",
      script: `${VENV}/celery`,
      args: "-A src.tasks worker --loglevel=info --concurrency=2 --queues=celery",
      max_memory_restart: "1200M",
      out_file: `${LOG_DIR}/worker.out.log`,
      error_file: `${LOG_DIR}/worker.err.log`,
    },
    {
      ...common,
      name: "jobify-beat",
      // Exactly ONE beat process, or every scheduled job runs twice (CLAUDE.md).
      instances: 1,
      exec_mode: "fork",
      script: `${VENV}/celery`,
      args: `-A src.tasks beat --loglevel=info --schedule ${APP_DIR}/data/celerybeat-schedule`,
      out_file: `${LOG_DIR}/beat.out.log`,
      error_file: `${LOG_DIR}/beat.err.log`,
    },
  ],
};
