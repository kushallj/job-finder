# Job Outreach Automation System

An intelligent job search and outreach automation system that finds relevant job opportunities and conducts personalized cold email campaigns to HR managers and engineering leaders.

## 🎯 What This System Does

1. **Finds Relevant Jobs**: Searches multiple job boards and APIs for positions matching your skills
2. **Analyzes Job Fit**: Uses AI to match your resume against job requirements and score compatibility  
3. **Discovers Key Contacts**: Finds HR managers and engineering leaders at target companies
4. **Sends Personalized Outreach**: Creates and sends tailored cold emails to boost your job prospects
5. **Tracks Everything**: Maintains records of all outreach attempts and responses

## 🚀 Quick Start

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python outreach_cli.py setup

# Configure email (see OUTREACH_SETUP.md for details)
# Add your Gmail app password to .env file
```

### Run Your First Campaign
```bash
# Fetch jobs and run outreach (dry run first)
python outreach_cli.py fetch
python outreach_cli.py outreach --dry-run

# If everything looks good, run for real
python outreach_cli.py outreach
```

## 📋 Available Scripts

- `outreach_main.py` - Complete automated workflow
- `outreach_cli.py` - Command-line interface for granular control
- `main.py` - Original job analysis pipeline

## 📊 Key Features

- **Multi-source job fetching** (Adzuna, Remotive, more)
- **AI-powered resume matching** using Claude
- **Contact discovery** from company websites and patterns
- **Personalized email generation** for different contact types
- **Outreach tracking** and duplicate prevention
- **Google Sheets integration** for campaign monitoring

## 📖 Documentation

See `OUTREACH_SETUP.md` for detailed setup instructions and best practices.

## 🎯 Success Strategy

This system helps you move beyond just applying through job boards to building direct relationships with hiring managers and technical leaders. The key is quality over quantity - focus on companies and roles that genuinely interest you, and let the AI help you craft compelling, personalized outreach.