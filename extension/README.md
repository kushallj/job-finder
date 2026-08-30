# JobFinder & LinkedIn Referral Automator (Chrome Extension)

A Chrome Extension (Manifest V3) wired directly into the `job-finder` backend platform.

## Features

1. **1-Click Job Capture**:
   - Injected on LinkedIn and Indeed job detail pages.
   - Shows a sleek floating widget to 1-click save the job to your SQLite database.
   - Automatically calculates your AI resume match score and missing keywords.

2. **Autonomous Target Sync**:
   - 1-click syncs target companies and roles directly from `job-finder` (`GET /api/referrals/targets`).

3. **5-Stage LinkedIn Referral Automator**:
   - **Discover**: Searches employee contacts at target companies.
   - **Connect**: Sends connection requests with AI-generated notes ($\le 200/300$ chars).
   - **Follow-up**: Detects accepted connections and sends referral pitches.
   - **CRM Sync**: Ingests discovered contacts into `job-finder` Contacts CRM (`POST /api/referrals/sync`).
   - **Outreach Tracker**: Logs all invites and messages to `OutreachRecord` (`POST /api/referrals/log-action`).

## Loading the Extension in Chrome

1. Open `chrome://extensions` in Google Chrome.
2. Enable **Developer mode** (top-right toggle).
3. Click **Load unpacked** and select this `extension/` folder.
4. Open LinkedIn or Indeed, click the extension icon, or capture jobs with the floating card!
