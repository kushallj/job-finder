# 🚀 100% Free Live Deployment & Setup Guide

This guide walks you through deploying the complete **Job Finder** platform live for free.

- **Frontend**: Hosted on **GitHub Pages** (Free HTTPS, zero-config via GitHub Actions).
- **Backend**: Hosted on **Render.com** (Free Web Service tier) or **Railway / Fly.io**.
- **Database**: Built-in SQLite or Free Managed PostgreSQL via **Supabase / Neon**.

---

## 🌐 Part 1: Deploy Frontend to GitHub Pages (2 Minutes)

The repository includes an automated GitHub Actions CI/CD workflow (`.github/workflows/deploy-frontend.yml`).

### Steps:
1. Go to your GitHub repository: `https://github.com/kushallj/job-finder`.
2. Click **Settings** (tab at the top) -> **Pages** (in the left sidebar).
3. Under **Build and deployment** -> **Source**, select **GitHub Actions**.
4. Push a commit or trigger the **Deploy Frontend to GitHub Pages** action under the **Actions** tab.
5. Your frontend is immediately live at:
   ```
   https://kushallj.github.io/job-finder/
   ```

---

## ⚡ Part 2: Deploy Backend to Render (Free Web Service)

Render provides free hosting for Python FastAPI web services.

### Option A: 1-Click Blueprint Deploy
1. Sign up / log in to [Render.com](https://render.com).
2. Click **New +** -> **Blueprint**.
3. Connect your `kushallj/job-finder` repository.
4. Render will detect `render.yaml` and configure the build automatically.

### Option B: Manual Web Service Deploy
1. Click **New +** -> **Web Service**.
2. Select your repository `job-finder`.
3. Fill in the deployment settings:
   - **Name**: `job-finder-api`
   - **Region**: Oregon or Frankfurt
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. Add Environment Variables in the **Environment** tab:
   - `GEMINI_API_KEY`: *(Your Google AI Studio API key)*
   - `SERPAPI_API_KEY`: *(Your SerpAPI key)*
   - `GMAIL_ADDRESS`: *(Your Gmail address)*
   - `GMAIL_PASSWORD`: *(Your Google App Password)*
   - `SENDER_NAME`: *(Your Full Name)*
   - `LINKEDIN_URL`: *(Your LinkedIn Profile URL)*
5. Click **Create Web Service**.
6. Once deployed, copy your backend URL: `https://job-finder-api.onrender.com`.

---

## 🗄️ Part 3: (Optional) Connect Free Supabase PostgreSQL

If you want persistent cloud storage across backend restarts instead of local SQLite:
1. Create a free project at [Supabase.com](https://supabase.com).
2. Go to **Project Settings** -> **Database** -> **Connection string** (URI).
3. Copy the `postgresql://...` URI.
4. Add it to your Render backend environment variables:
   ```
   DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres
   ```
5. The backend automatically initializes all tables on startup!

---

## 🔑 Part 4: Required API Keys Checklist

| API / Service | Free Tier Limits | How to Obtain |
| :--- | :--- | :--- |
| **Google Gemini AI** | **Free** (60 req/min) | [Google AI Studio](https://aistudio.google.com/app/apikey) -> Create API Key |
| **SerpAPI** | **100 searches/mo Free** | [SerpAPI.com](https://serpapi.com) -> Register -> Copy API Key |
| **Gmail App Password** | **Free** (500 emails/day) | [Google App Passwords](https://myaccount.google.com/apppasswords) -> Generate App Password |
| **Hunter.io** | **25 free searches/mo** | [Hunter.io](https://hunter.io) -> Free Account -> API Keys |
| **Tsenta Auto-Apply** | **25 free apps lifetime** | Local driver included or [Tsenta.com](https://tsenta.com) |
| **Telegram Alerts** | **Unlimited Free** | Message `@BotFather` on Telegram -> `/newbot` |

---

## 📲 Part 5: Connecting Frontend to Live Backend

1. Open your live frontend: `https://kushallj.github.io/job-finder/`.
2. Click **🚀 Setup Guide** in the navigation bar.
3. Paste your live backend URL (e.g. `https://job-finder-api.onrender.com`).
4. Click **Test & Connect**. The frontend will instantly save the connection and route all live queries, evaluations, and auto-applies to your cloud backend!
