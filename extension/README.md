# Job Finder Companion (Chrome extension)

A companion extension for the [job-finder](https://github.com/kushallj/job-finder)
backend. It does **not** run the pipeline, scraping, or email sending itself —
it's a client that talks to your existing `main.py` FastAPI server. Two things it does:

1. **Capture** — on LinkedIn/Indeed job pages, shows a small widget so you can
   save the job you're viewing straight into your database, with an optional
   AI match score.
2. **Remote control** — the toolbar popup shows your stats, saved jobs, and
   jobs pending outreach, lets you run a search/scoring pass, and lets you
   look up contacts and send outreach **one email at a time, with an explicit
   confirm step**. It never bulk-sends or sends anything automatically.

## 1. Apply the backend patch (required for job capture)

The "save the job I'm looking at" feature needs one new endpoint that doesn't
exist in the current backend: `POST /api/jobs/capture`. Two patch files are
included:

- `main.patch`
- `api_models.patch`

From the root of your `job-finder` checkout:

```bash
patch -p1 < main.patch
patch -p1 < api_models.patch
```

(Or open the patches and copy the added blocks by hand — each is a single
new endpoint/model, nothing existing is modified.)

Everything else — stats, jobs list, pending-outreach, contact search,
outreach send, run-query — uses endpoints that already exist in `main.py`,
so no other backend changes are required. Restart your server after patching.

## 2. Load the extension

1. Go to `chrome://extensions`.
2. Enable **Developer mode** (top right).
3. Click **Load unpacked** and select this folder.
4. Click the extension icon → ⚙️ → set the **Backend URL** (defaults to
   `http://localhost:8000`). If your backend is hosted remotely, use its
   https URL — Chrome will prompt you to grant permission for that host.

## 3. Use it

- Open a LinkedIn or Indeed job posting → a small "💾 Job Finder" card
  appears bottom-right. Check the fields it pulled in (site selectors change
  often, so double-check title/company), optionally tick "Score against my
  resume," and click **Save job**.
- Click the toolbar icon for the dashboard:
  - **Overview** — job/contact/application counts and outreach success rate.
  - **Jobs** — everything saved so far, paginated.
  - **Outreach** — jobs that are scored but haven't had outreach sent. Click
    **Find contacts** to discover people at that company, then **Send
    outreach** on a specific person — you'll get a confirm dialog before
    anything is sent.
  - **Search** — kicks off your backend's full fetch → score pipeline for a
    query (e.g. "senior backend engineer").

## Why it's built this way

The backend has no auth and CORS is wide open (`allow_origins=["*"]`), so all
requests go straight from the extension's background service worker to your
server — nothing is proxied through a third party.

The outreach-sending flow is intentionally one-contact-at-a-time with a
confirmation dialog, and there's no "send to everyone" button. If you ever
want to publish this to the Chrome Web Store rather than just loading it
unpacked for yourself, keep that constraint — a public extension whose main
feature is bulk cold-emailing from scraped contacts is likely to run into the
Web Store's spam/abuse policies, and most job boards' and Gmail's ToS
restrict this kind of automation regardless. Loading it unpacked for your own
use, or keeping it unlisted, sidesteps that entirely.

## Files

- `manifest.json` — MV3 manifest
- `background.js` / `common.js` — service worker, all API calls
- `content.js` / `content.css` — job-page detection + capture widget
- `popup.html` / `popup.js` / `popup.css` — dashboard
- `options.html` / `options.js` — backend URL setting
- `main.patch`, `api_models.patch` — backend changes (see step 1)
