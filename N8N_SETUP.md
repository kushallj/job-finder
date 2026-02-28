# n8n Local Setup with ngrok

This guide explains how to run the Job Outreach Automation workflow locally using n8n and ngrok.

## Prerequisites

1. **n8n** - Workflow automation tool
2. **ngrok** - Expose local server to internet
3. **API Keys** (optional but recommended):
   - Hunter.io API key
   - Apollo.io API key
   - SignalHire API key

## Step 1: Add API Keys to .env

Add these to your `.env` file:

```bash
# Email Discovery APIs (at least one recommended)
HUNTER_API_KEY=your_hunter_api_key
APOLLO_API_KEY=your_apollo_api_key
SIGNALHIRE_API_KEY=your_signalhire_api_key
SIGNALHIRE_CALLBACK_URL=https://your-ngrok-url.ngrok-free.app/api/signalhire/callback

# Gmail for sending emails
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_PASSWORD=your_app_password

# Google Sheets
GOOGLE_SHEET_WORKSHEET=Applications
```

### Getting API Keys:

- **Hunter.io**: https://hunter.io/api_keys (50 free requests/month)
- **Apollo.io**: https://app.apollo.io/#/settings/integrations/api 
  - Requires **Master API Key** for People Search
  - People Search doesn't return emails directly - uses enrichment
  - Docs: https://docs.apollo.io/reference/people-api-search
- **SignalHire**: https://www.signalhire.com/api (paid)
  - **Search API** (`searchByQuery`): Returns profiles WITHOUT contacts
  - **Person API** (`candidate/search`): Returns contacts via async callback
  - Search API access requires contacting support@signalhire.com
  - Docs: https://www.signalhire.com/api

## Step 2: Start the FastAPI Server

```bash
cd /Users/kushalljain/Desktop/job-finder
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Step 3: Expose with ngrok

In a new terminal:

```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

## Step 4: Install and Start n8n

### Option A: Docker (Recommended)
```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  -e N8N_SECURE_COOKIE=false \
  n8nio/n8n
```

### Option B: npm
```bash
npm install -g n8n
n8n start
```

Access n8n at: http://localhost:5678

## Step 5: Import the Workflow

1. Open n8n at http://localhost:5678
2. Click **Workflows** → **Import from File**
3. Select `n8n_workflows/job_outreach_workflow_enhanced.json`
4. Click **Import**

## Step 6: Configure Environment Variable

1. In n8n, go to **Settings** → **Variables**
2. Add a new variable:
   - **Name**: `API_BASE_URL`
   - **Value**: Your ngrok URL (e.g., `https://abc123.ngrok-free.app`)

## Step 7: Test the Workflow

1. Open the imported workflow
2. Click **Execute Workflow** to run manually
3. Check the execution logs for any errors

## API Endpoints Available

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/run-query` | POST | Search and process jobs |
| `/api/contacts/search` | POST | Find contacts using Hunter/Apollo/SignalHire |
| `/api/outreach/send` | POST | Send outreach email |
| `/api/outreach/followup` | POST | Send follow-up email |
| `/api/jobs/pending-outreach` | GET | Get jobs needing outreach |
| `/api/stats` | GET | Get campaign statistics |
| `/api/health` | GET | Health check |

## Workflow Features

### Daily Job Search (Main Flow)
1. **Schedule Daily** - Runs every 24 hours
2. **Search Python Jobs** - Searches for Python developer jobs
3. **Search React Jobs** - Searches for React developer jobs
4. **Get Pending Jobs** - Fetches jobs with high match scores
5. **Find Contacts** - Uses Hunter.io, Apollo.io, SignalHire to find emails
6. **Send Outreach Email** - Sends personalized email with resume
7. **Rate Limit Delay** - 45 second delay between emails

### Follow-up Flow (Every 3 Days)
1. **Schedule Follow-ups** - Runs every 3 days
2. **Get Outreach Records** - Fetches sent emails
3. **Needs Follow-up?** - Checks if status is "sent" (no reply)
4. **Send Follow-up Email** - Sends follow-up #1, #2, or #3

## Troubleshooting

### "Connection refused" errors
- Make sure FastAPI server is running on port 8000
- Check ngrok is running and URL is correct
- Verify `API_BASE_URL` variable in n8n

### "No contacts found"
- Check if API keys are configured in `.env`
- Hunter.io free tier has 50 requests/month limit
- Try with a well-known company name first

### Emails not sending
- Verify `GMAIL_ADDRESS` and `GMAIL_PASSWORD` in `.env`
- Use Gmail App Password, not regular password
- Check Gmail "Less secure apps" or use OAuth

### Google Sheets not updating
- Ensure `GOOGLE_SHEET_WORKSHEET=Applications` in `.env`
- Verify service account has edit access to the sheet

## Rate Limits

To avoid being flagged as spam:
- 45 second delay between outreach emails
- 60 second delay between follow-ups
- Maximum 3 follow-ups per contact
- Daily job search runs once per day

## Customization

### Change Search Keywords
Edit the "Search Python Jobs" and "Search React Jobs" nodes to change the query:
```json
{
  "query": "your custom search term"
}
```

### Change Follow-up Schedule
Edit "Schedule Follow-ups (Every 3 Days)" node to change interval.

### Adjust Confidence Threshold
Edit "High Confidence?" node to change minimum confidence score (default: 30).
