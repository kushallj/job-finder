# 🚀 Complete Job Outreach Automation Setup

Your all-in-one guide to set up the complete job search and outreach automation system.

## 📋 What You're Building

A fully automated system that:
1. **Searches 9+ job platforms** daily (Naukri, Indeed, Hirist, Foorilla, Remote.co, etc.)
2. **Finds HR/Engineering contacts** at target companies
3. **Sends personalized cold emails** with your resume
4. **Automates follow-ups** after 7 days
5. **Tracks everything** in database and Google Sheets
6. **Uses FREE local AI** (no API costs!)
7. **Integrates with n8n** for visual workflow automation

## 🎯 Quick Start (30 minutes)

### Step 1: Install Dependencies (5 min)

```bash
# Install Python packages
pip install -r requirements.txt

# Install Ollama for free local AI
# macOS:
brew install ollama

# Linux:
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: Download from https://ollama.ai/download
```

### Step 2: Setup Local AI (5 min)

```bash
# Pull a model (recommended: llama3.2:3b)
ollama pull llama3.2:3b

# Verify setup
python setup_local_ai.py
```

### Step 3: Configure Environment (5 min)

Edit `.env` file:
```bash
# Gmail for sending emails
GMAIL_ADDRESS=your.email@gmail.com
GMAIL_PASSWORD=your_app_password_here  # Get from https://myaccount.google.com/apppasswords

# Optional: Gemini API (if not using local AI)
GEMINI_API_KEY=your_key_here

# Job search APIs
ADZUNA_APP_ID=your_id
ADZUNA_APP_KEY=your_key

# Database
DATABASE_URL=sqlite:///./job_automation.db
```

### Step 4: Create Resume PDF (2 min)

```bash
# Add your resume to data/resume.txt
# Then convert to PDF
python create_resume_pdf.py
```

### Step 5: Initialize Database (1 min)

```bash
python outreach_cli.py setup
```

### Step 6: Test the System (5 min)

```bash
# Test AI service
python fix_api_key.py

# Test job search (dry run)
python outreach_cli.py fetch --comprehensive

# Test outreach (dry run - no emails sent)
python outreach_cli.py outreach --dry-run
```

### Step 7: Run Your First Campaign (5 min)

```bash
# Full automated campaign
python comprehensive_job_search.py
```

## 🎨 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Job Search Layer                       │
│  Naukri │ Indeed │ Hirist │ Foorilla │ Remote.co │ ...  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  AI Processing Layer                     │
│  Local LLM (Ollama) → Gemini API → Fallback Matching   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                 Contact Discovery Layer                  │
│  Company Websites │ Email Patterns │ Hunter.io (n8n)   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Outreach Layer                          │
│  Personalized Emails │ Resume Attachment │ Follow-ups   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Tracking Layer                          │
│  SQLite Database │ Google Sheets │ n8n Workflows       │
└─────────────────────────────────────────────────────────┘
```

## 🔧 Configuration Options

### AI Backend Selection

The system automatically chooses the best AI:

1. **Local LLM (Ollama)** - FREE, unlimited, private ✅
2. **Gemini API** - Free tier with quotas
3. **Fallback** - Keyword matching (no AI)

To force a specific backend, edit `src/ai/unified_ai_service.py`

### Job Search Customization

Edit `src/scrapers/multi_platform_scraper.py`:

```python
PROFILE = {
    "keywords": [
        "Your Job Title 1",
        "Your Job Title 2",
        # Add more...
    ],
    "locations": [
        "Your City 1",
        "Your City 2",
        "Remote"
    ],
    "skills": [
        "Skill 1",
        "Skill 2",
        # Add more...
    ]
}
```

### Email Templates

Edit `src/email_outreach.py` to customize:
- Email subject lines
- Email body templates
- Follow-up messages
- Signature

## 📊 Usage Modes

### Mode 1: Manual CLI

```bash
# Fetch jobs
python outreach_cli.py fetch --comprehensive

# View jobs
python outreach_cli.py jobs --limit 20

# View contacts
python outreach_cli.py contacts --company "Google"

# Send outreach
python outreach_cli.py outreach --max-contacts 2

# View stats
python outreach_cli.py stats
```

### Mode 2: Automated Script

```bash
# Run complete workflow
python comprehensive_job_search.py

# Runs:
# 1. Job search across all platforms
# 2. AI-powered matching
# 3. Contact discovery
# 4. Email outreach
# 5. Reporting
```

### Mode 3: n8n Workflows

```bash
# Start API server
python n8n_api.py

# Start n8n
n8n start

# Import workflows from n8n_workflows/
# Configure and activate
```

## 🎯 Daily Workflow

### Morning (9 AM)
- n8n triggers job search
- New jobs discovered and analyzed
- Contacts found for top matches

### Afternoon (2 PM)
- Personalized emails sent
- Rate-limited (30-60 sec between emails)
- All tracked in database

### Evening (6 PM)
- Daily summary sent to Slack
- Stats updated in Google Sheets
- Follow-ups scheduled for next week

## 📈 Expected Results

### Week 1
- **Jobs Found**: 200-500
- **Contacts Discovered**: 50-100
- **Emails Sent**: 20-30
- **Responses**: 1-3

### Month 1
- **Jobs Found**: 1000-2000
- **Contacts Discovered**: 200-400
- **Emails Sent**: 100-150
- **Responses**: 10-20
- **Interviews**: 2-5

### Success Rate
- **Response Rate**: 5-15%
- **Interview Rate**: 20-30% of responses
- **Offer Rate**: 10-20% of interviews

## 🔐 Privacy & Security

### Data Storage
- ✅ All data stored locally (SQLite)
- ✅ Resume never sent to external APIs (with local AI)
- ✅ Contacts encrypted in database
- ✅ Email credentials secured in .env

### Best Practices
- ✅ Use Gmail app passwords (not main password)
- ✅ Keep .env file private (in .gitignore)
- ✅ Regular database backups
- ✅ Monitor for suspicious activity

## 🆘 Troubleshooting

### Common Issues

**1. "Gemini quota exceeded"**
```bash
# Solution: Install local AI
ollama pull llama3.2:3b
python setup_local_ai.py
```

**2. "Cannot send emails"**
```bash
# Solution: Check Gmail settings
python fix_api_key.py
# Verify GMAIL_PASSWORD is app password
```

**3. "No jobs found"**
```bash
# Solution: Check job sources
python outreach_cli.py fetch --comprehensive
# Verify internet connection
```

**4. "No contacts found"**
```bash
# Solution: Check contact finder
# May need to add manual contacts
# Or integrate Hunter.io via n8n
```

**5. "n8n workflows not working"**
```bash
# Solution: Check API server
curl http://localhost:8000/
# Restart if needed
python n8n_api.py
```

## 📚 Documentation

- **Local AI Setup**: `LOCAL_AI_SETUP.md`
- **n8n Integration**: `N8N_INTEGRATION_GUIDE.md`
- **Outreach Guide**: `OUTREACH_SETUP.md`
- **API Reference**: `n8n_api.py` (FastAPI auto-docs at /docs)

## 🎓 Learning Resources

### Python & Async
- FastAPI: https://fastapi.tiangolo.com
- AsyncIO: https://docs.python.org/3/library/asyncio.html

### AI & LLMs
- Ollama: https://ollama.ai
- Llama Models: https://ai.meta.com/llama

### Automation
- n8n: https://docs.n8n.io
- Workflow Examples: https://n8n.io/workflows

### Job Search
- Hunter.io: https://hunter.io
- LinkedIn API: https://developer.linkedin.com

## 🚀 Advanced Features

### Multi-Account Setup

Run multiple campaigns with different accounts:

```bash
# Account 1
GMAIL_ADDRESS=account1@gmail.com python comprehensive_job_search.py

# Account 2
GMAIL_ADDRESS=account2@gmail.com python comprehensive_job_search.py
```

### Custom Job Sources

Add your own job board scrapers:

```python
# Create src/scrapers/custom_scraper.py
class CustomJobBoardScraper(BaseJobScraper):
    async def search(self, keyword, location):
        # Your scraping logic
        return jobs
```

### AI Model Switching

Switch between different local models:

```python
# Edit src/ai/local_llm_service.py
def __init__(self, model: str = "mistral:7b"):  # Change model here
```

## 🎉 Success Checklist

- [ ] Python dependencies installed
- [ ] Ollama installed and running
- [ ] Model downloaded (llama3.2:3b)
- [ ] .env file configured
- [ ] Gmail app password set
- [ ] Resume PDF created
- [ ] Database initialized
- [ ] Test run successful
- [ ] First campaign completed
- [ ] n8n workflows imported (optional)
- [ ] Tracking working (database + sheets)

## 💡 Pro Tips

1. **Start Small**: Begin with 5-10 emails/day, scale up gradually
2. **Personalize**: Always customize emails, never use pure templates
3. **Track Everything**: Monitor response rates and adjust strategy
4. **Follow Up**: Most responses come from follow-ups, not first email
5. **Be Patient**: Job search takes time, consistency is key
6. **Stay Organized**: Use Google Sheets to track all applications
7. **Network**: Combine cold emails with LinkedIn connections
8. **Quality > Quantity**: Better to send 10 great emails than 100 generic ones

## 🎯 Next Steps

1. **Run your first campaign**: `python comprehensive_job_search.py`
2. **Monitor results**: Check database and Google Sheets
3. **Adjust strategy**: Based on response rates
4. **Scale up**: Add more job sources and contacts
5. **Automate**: Set up n8n workflows for hands-off operation

**Good luck with your job search!** 🚀

---

**Questions?** Check the documentation or run:
```bash
python fix_api_key.py  # Diagnostic tool
python setup_local_ai.py  # AI setup checker
python outreach_cli.py --help  # CLI help
```