# Job Outreach Automation Setup Guide

This guide will help you set up the job outreach automation system to find relevant jobs and cold email HR/Engineering Managers.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Email Settings

You need to set up Gmail app passwords for sending emails:

1. Go to [Google Account Settings](https://myaccount.google.com/apppasswords)
2. Generate an app password for "Mail"
3. Update your `.env` file:
```
GMAIL_PASSWORD=your_16_character_app_password_here
```

### 3. Initialize Database
```bash
python outreach_cli.py setup
```

### 4. Add Your Resume
Create or update `data/resume.txt` with your background and experience, then convert it to PDF:

```bash
# Create PDF version for email attachments
python create_resume_pdf.py
```

This creates `data/resume.pdf` which will be automatically attached to outreach emails.

### 5. Run Your First Comprehensive Campaign
```bash
# Run comprehensive multi-platform search and outreach
python comprehensive_job_search.py

# Or use the CLI for more control
python outreach_cli.py comprehensive

# For testing, you can still do individual steps:
python outreach_cli.py fetch --comprehensive
python outreach_cli.py outreach --dry-run
```

## 📋 Available Commands

### Comprehensive Multi-Platform Search
```bash
# Full comprehensive search and outreach
python comprehensive_job_search.py

# CLI version with options
python outreach_cli.py comprehensive --dry-run
python outreach_cli.py comprehensive --max-contacts 3
```

### Fetch Jobs
```bash
# Fetch jobs with default queries
python outreach_cli.py fetch

# Comprehensive multi-platform fetch
python outreach_cli.py fetch --comprehensive

# Fetch with custom queries
python outreach_cli.py fetch --queries "python developer" "react developer"
```

### List Jobs
```bash
# List recent jobs
python outreach_cli.py jobs

# List jobs with high match scores
python outreach_cli.py jobs --min-score 70
```

### List Contacts
```bash
# List all contacts
python outreach_cli.py contacts

# Filter by company
python outreach_cli.py contacts --company "Google"
```

### Run Outreach Campaign
```bash
# Dry run (no emails sent)
python outreach_cli.py outreach --dry-run

# Real campaign
python outreach_cli.py outreach

# Target specific jobs
python outreach_cli.py outreach --job-ids 1 2 3

# Limit contacts per job
python outreach_cli.py outreach --max-contacts 1
```

### View Statistics
```bash
python outreach_cli.py stats
```

## 🎯 How It Works

### 1. Job Matching
- Fetches jobs from multiple sources (Adzuna, Remotive)
- Uses AI to analyze job descriptions and match with your resume
- Only processes jobs with match scores above your threshold

### 2. Contact Finding
- Searches for HR managers and Engineering managers at target companies
- Uses multiple methods:
  - Company website scraping
  - Email pattern generation
  - LinkedIn search (when available)
- Assigns confidence scores to contacts

### 3. Personalized Outreach
- Creates personalized emails using AI
- Different templates for HR vs Engineering contacts
- Includes relevant skills and experience from your resume
- Tracks all outreach attempts to avoid duplicates

### 4. Email Delivery
- Sends emails through Gmail SMTP
- Adds delays between emails to avoid spam detection
- Records all outreach attempts in database

## 📊 Monitoring Your Campaign

### Check Statistics
```bash
python outreach_cli.py stats
```

### View Recent Contacts
```bash
python outreach_cli.py contacts --limit 20
```

### Track Email Responses
- Monitor your Gmail for replies
- Update contact status manually (future feature will automate this)

## 🔧 Configuration Options

### Email Settings
- `GMAIL_ADDRESS`: Your Gmail address
- `GMAIL_PASSWORD`: Gmail app password (not regular password!)

### AI Settings
- `GEMINI_API_KEY`: Your Google Gemini API key for personalized emails
- `GEMINI_MODEL`: AI model to use (default: gemini-1.5-flash)

### Job Search Settings
- `ADZUNA_APP_ID` & `ADZUNA_APP_KEY`: For job fetching

## 🎯 Best Practices

### 1. Start Small
- Begin with a dry run to see what emails would be sent
- Start with 1-2 contacts per company
- Monitor response rates and adjust approach

### 2. Personalization
- Keep your resume updated in `data/resume.txt`
- Review generated emails before sending (dry run mode)
- Focus on companies and roles that genuinely interest you

### 3. Follow-up Strategy
- Wait 1 week before following up
- Track responses and update contact status
- Don't spam - quality over quantity

### 4. Compliance
- Respect company preferences about unsolicited emails
- Include unsubscribe information if sending bulk emails
- Follow local laws regarding cold outreach

## 🚨 Troubleshooting

### Email Not Sending
1. Check Gmail app password is correct
2. Ensure 2FA is enabled on your Google account
3. Verify SMTP settings in code

### No Contacts Found
1. Check if company websites are accessible
2. Try different search terms
3. Manually add contacts to database if needed

### Low Match Scores
1. Update your resume with more relevant keywords
2. Lower the minimum match score threshold
3. Expand job search queries

## 📈 Advanced Usage

### Custom Resume for Different Roles
Create specialized resumes:
- `data/resume_python.txt` for Python roles
- `data/resume_react.txt` for React roles
- The system will automatically use the most relevant one

### Batch Processing
```bash
# Process specific high-value jobs
python outreach_cli.py outreach --job-ids 15 23 42 --max-contacts 3
```

### Integration with Existing Workflow
The outreach system integrates with your existing job processing pipeline. You can:
1. Use the original `main.py` for job analysis
2. Use `outreach_main.py` for the complete outreach workflow
3. Use `outreach_cli.py` for granular control

## 🎉 Success Metrics

Track these metrics to measure success:
- Response rate (aim for 5-15%)
- Interview requests
- Quality of conversations
- Time to first response

Remember: This is about building genuine professional relationships, not just sending mass emails. Quality and personalization are key to success!