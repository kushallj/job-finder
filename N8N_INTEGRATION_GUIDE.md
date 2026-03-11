# 🔄 n8n Integration Guide

Complete guide to integrate your job outreach system with n8n for automated workflows.

## 🎯 What You Get

- **Automated Job Search** - Daily job discovery across 9+ platforms
- **Smart Contact Finding** - Automatic HR/Engineering manager discovery
- **Email Verification** - Integration with Hunter.io for email finding
- **Personalized Outreach** - AI-generated cold emails
- **Automated Follow-ups** - Smart follow-up system after 7 days
- **Slack Notifications** - Real-time campaign updates
- **Complete Tracking** - Full analytics and reporting

## 🚀 Quick Start

### Step 1: Start the API Server

```bash
# Install dependencies
pip install fastapi uvicorn

# Start the API server
python n8n_api.py

# Server runs on: http://localhost:8000
```

### Step 2: Install n8n

```bash
# Using npm
npm install -g n8n

# Or using Docker
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

### Step 3: Import Workflows

1. Open n8n: http://localhost:5678
2. Go to **Workflows** → **Import from File**
3. Import these workflows:
   - `n8n_workflows/job_outreach_workflow.json`
   - `n8n_workflows/follow_up_workflow.json`

### Step 4: Configure Credentials

In n8n, add these credentials:

**Hunter.io API** (for email finding):
- Get API key: https://hunter.io/api
- Add to n8n credentials

**Slack** (for notifications):
- Create Slack app: https://api.slack.com/apps
- Add to n8n credentials

## 📊 Available API Endpoints

### Job Search
```bash
POST http://localhost:8000/api/jobs/search
{
  "keywords": ["Python Developer", "Backend Developer"],
  "locations": ["Remote", "Bangalore"],
  "min_match_score": 60
}
```

### Get Jobs
```bash
GET http://localhost:8000/api/jobs?limit=20&company=Google
```

### Find Contacts
```bash
POST http://localhost:8000/api/contacts/search
{
  "company_name": "Google",
  "job_title": "Software Engineer"
}
```

### Send Outreach Email
```bash
POST http://localhost:8000/api/outreach/send
{
  "job_id": 123,
  "contact_email": "hr@company.com",
  "contact_name": "John Doe",
  "send_immediately": true
}
```

### Send Follow-ups
```bash
POST http://localhost:8000/api/outreach/follow-up
{
  "days_since_sent": 7
}
```

### Get Statistics
```bash
GET http://localhost:8000/api/stats
```

## 🔄 Workflow 1: Daily Job Outreach

**Trigger:** Daily at 9 AM

**Flow:**
1. Search jobs across all platforms
2. Split jobs into individual items
3. Find contacts for each company
4. Validate contact quality
5. Find/verify email with Hunter.io
6. Send personalized outreach email
7. Wait 30 seconds (rate limiting)
8. Log success
9. Send daily summary to Slack

**Configuration:**
- Edit schedule in "Schedule Daily Job Search" node
- Adjust keywords in "Search Jobs API" node
- Configure rate limiting in "Wait" node

## 🔄 Workflow 2: Automated Follow-ups

**Trigger:** Daily at 9 AM

**Flow:**
1. Check for pending follow-ups
2. If pending > 0:
   - Send follow-up emails
   - Notify via Slack
3. If pending = 0:
   - Send "no follow-ups" notification

**Configuration:**
- Edit `days_since_sent` (default: 7 days)
- Customize follow-up message template

## 🎨 Customization

### Change Email Templates

Edit `src/email_outreach.py`:
```python
async def create_personalized_email(self, contact, job_title, ...):
    # Customize email generation here
```

### Add More Job Sources

Edit `src/scrapers/multi_platform_scraper.py`:
```python
# Add new scraper class
class NewJobBoardScraper(BaseJobScraper):
    async def search(self, keyword, location):
        # Your scraping logic
```

### Modify Contact Finding

Edit `src/contact_finder.py`:
```python
async def find_company_contacts(self, company_name, job_title):
    # Customize contact discovery
```

## 📈 Advanced n8n Workflows

### Workflow 3: Email Reply Monitoring

Monitor Gmail for replies and update status:

```json
{
  "trigger": "Gmail - New Email",
  "filter": "from:hr@company.com",
  "action": "Update Outreach Status",
  "endpoint": "PUT /api/outreach/{id}/status"
}
```

### Workflow 4: Multi-Channel Outreach

Combine email with LinkedIn messages:

```json
{
  "trigger": "New Job Found",
  "parallel": [
    "Send Email",
    "Send LinkedIn Message",
    "Add to CRM"
  ]
}
```

### Workflow 5: A/B Testing

Test different email templates:

```json
{
  "split": "50/50",
  "template_a": "Professional tone",
  "template_b": "Casual tone",
  "track": "Response rates"
}
```

## 🔧 Troubleshooting

### API Server Not Starting

```bash
# Check if port 8000 is in use
lsof -i :8000

# Use different port
uvicorn n8n_api:app --port 8001
```

### n8n Can't Connect to API

```bash
# Check API is running
curl http://localhost:8000/

# Check firewall settings
# Ensure localhost connections are allowed
```

### Emails Not Sending

```bash
# Verify Gmail settings
python fix_api_key.py

# Check GMAIL_PASSWORD in .env
# Must be App Password, not regular password
```

### Hunter.io Rate Limits

```bash
# Free tier: 50 searches/month
# Upgrade or use alternative:
# - Clearbit
# - RocketReach
# - Manual email patterns
```

## 📊 Monitoring & Analytics

### View Campaign Stats

```bash
# Via API
curl http://localhost:8000/api/stats

# Via n8n Dashboard
# Add "Get Stats" node to any workflow
```

### Track Success Metrics

Key metrics to monitor:
- **Total Outreach**: Total emails sent
- **Response Rate**: Replies / Sent
- **Interview Rate**: Interviews / Replies
- **Conversion Rate**: Offers / Interviews

### Export Data

```bash
# Export to CSV
python outreach_cli.py stats > stats.csv

# Export to Google Sheets
# Already integrated in job_processor.py
```

## 🎯 Best Practices

### Rate Limiting

- **30-60 seconds** between emails
- **Max 50 emails/day** to avoid spam flags
- **Personalize each email** - no templates

### Follow-up Strategy

- **Wait 7 days** before first follow-up
- **Max 2 follow-ups** per contact
- **Different message** each time

### Email Quality

- ✅ Always use contact's real name
- ✅ Reference specific job details
- ✅ Attach resume as PDF
- ✅ Professional signature
- ❌ No generic templates
- ❌ No mass CC/BCC

### Compliance

- ✅ Include unsubscribe option
- ✅ Respect opt-outs immediately
- ✅ Follow CAN-SPAM Act
- ✅ GDPR compliant (if EU)

## 🚀 Scaling Up

### Multiple Accounts

Run multiple instances with different Gmail accounts:

```bash
# Instance 1
PORT=8000 GMAIL_ADDRESS=account1@gmail.com python n8n_api.py

# Instance 2
PORT=8001 GMAIL_ADDRESS=account2@gmail.com python n8n_api.py
```

### Distributed Processing

Use Redis for job queue:

```python
# Add to n8n_api.py
from redis import Redis
redis = Redis()

# Queue jobs
redis.lpush('job_queue', job_id)

# Process in parallel workers
```

### Database Optimization

For high volume:

```bash
# Switch from SQLite to PostgreSQL
# Update DATABASE_URL in .env
DATABASE_URL=postgresql://user:pass@localhost/jobdb
```

## 📚 Resources

- **n8n Documentation**: https://docs.n8n.io
- **Hunter.io API**: https://hunter.io/api-documentation
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Ollama Models**: https://ollama.ai/library

## 🎉 Success Checklist

- [ ] API server running on port 8000
- [ ] n8n installed and accessible
- [ ] Workflows imported successfully
- [ ] Hunter.io credentials configured
- [ ] Slack notifications working
- [ ] Test email sent successfully
- [ ] Follow-up workflow scheduled
- [ ] Local AI (Ollama) installed
- [ ] Resume PDF created
- [ ] Gmail app password set

**You're ready to automate your job search!** 🚀