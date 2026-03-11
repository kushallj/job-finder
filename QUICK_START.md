# Quick Start Guide

## 🚀 Run Job Search Automation

### One Command to Rule Them All
```bash
python comprehensive_job_search.py
```

This single command will:
1. ✅ Search 9+ job platforms for relevant positions
2. ✅ Analyze each job with AI (match score, skills)
3. ✅ Find HR and Engineering Manager contacts
4. ✅ Send personalized emails with your resume attached
5. ✅ Generate detailed reports

---

## 📋 Quick Commands

### Check System Status
```bash
python system_check.py
```
Verifies all components are working (database, AI, email, files)

### Test Local AI
```bash
python test_local_ai.py
```
Tests Ollama AI service with sample job matching

### Export to Google Sheets
```bash
python export_to_sheets.py
```
Exports all jobs, contacts, and outreach records to Google Sheets

### Search Database
```bash
python search_db.py
```
Interactive database search and statistics

---

## ⚙️ Configuration

### Your Settings (.env file)
- **Email**: canaby007@gmail.com
- **Name**: Kushall Jain
- **Resume**: data/resume.pdf
- **AI**: Ollama (mistral:latest) - FREE & UNLIMITED

### Customize Search Queries
Edit `comprehensive_job_search.py` line 48-56:
```python
enhanced_queries = [
    "Python Developer",
    "Backend Developer",
    "Full Stack Developer",
    # Add your own search terms here
]
```

### Adjust Match Score Threshold
Edit `comprehensive_job_search.py` line 70:
```python
await job_processor.process_all_jobs(resume_text, min_score=65)
# Change 65 to higher (more selective) or lower (more opportunities)
```

---

## 🎯 What Happens When You Run

### Step 1: Job Search (2-5 minutes)
- Searches across Naukri, Indeed, Hirist, Foorilla, Remote.co, etc.
- Finds 50-200 new jobs per run
- Deduplicates and filters

### Step 2: AI Analysis (5-10 minutes)
- Extracts skills from each job description
- Calculates match score with your resume
- Identifies matched and missing skills
- Filters jobs above threshold (default: 65%)

### Step 3: Contact Discovery (10-20 minutes)
- Searches LinkedIn for HR and Engineering Managers
- Discovers email addresses
- Validates contact information
- Prioritizes decision-makers

### Step 4: Email Outreach (5-10 minutes)
- Generates personalized emails
- Attaches your resume PDF
- Sends to verified contacts only
- Logs all outreach attempts

### Step 5: Reporting (1 minute)
- Shows statistics and insights
- Lists top companies contacted
- Provides success metrics
- Suggests next steps

**Total Time**: 25-45 minutes per run

---

## 📊 Expected Results

### Per Run (Weekly)
- **Jobs Found**: 50-200 new positions
- **Jobs Analyzed**: All with AI matching
- **High Match Jobs**: 10-30 (score > 65%)
- **Contacts Found**: 5-15 decision-makers
- **Emails Sent**: 5-15 personalized outreach

### Success Rates
- **Contact Discovery**: 30-50% of jobs
- **Email Delivery**: 95%+ (valid emails)
- **Response Rate**: 5-15% (industry average)
- **Interview Rate**: 1-3% (of emails sent)

### Timeline
- **Week 1**: Send initial outreach
- **Week 2**: Follow up with non-responders
- **Week 3-4**: Interviews start coming in
- **Month 2-3**: Offers typically arrive

---

## 💡 Pro Tips

### Maximize Response Rates
1. **Run weekly** - Fresh jobs get more responses
2. **Personalize** - Edit templates for specific companies
3. **Follow up** - Send follow-ups after 7 days
4. **Track responses** - Use Google Sheets export
5. **Optimize timing** - Run Tuesday-Thursday mornings

### Best Practices
- ✅ Keep resume updated (data/resume.txt and .pdf)
- ✅ Monitor email daily for responses
- ✅ Respond quickly to interested companies
- ✅ Track conversations in database
- ✅ Adjust search queries based on results

### Avoid Common Mistakes
- ❌ Don't run multiple times per day (spam risk)
- ❌ Don't lower match threshold below 50% (poor fit)
- ❌ Don't ignore follow-ups (missed opportunities)
- ❌ Don't forget to check spam folder
- ❌ Don't send to same contact twice (check database)

---

## 🔧 Troubleshooting

### "Ollama not available"
```bash
ollama serve
```

### "Database error"
```bash
python migrate_database.py
```

### "Email sending failed"
- Check .env file has correct Gmail password
- Verify internet connection
- Check logs/email_outreach.log

### "No jobs found"
- Check internet connection
- Try different search queries
- Some platforms may be temporarily down

---

## 📈 Track Your Progress

### View Statistics
```bash
python search_db.py
```

### Export to Sheets
```bash
python export_to_sheets.py
```

### Check Logs
```bash
tail -f logs/main.log
tail -f logs/email_outreach.log
```

---

## 🎯 Your Goal

**Target**: 100+ applications per month
- **Week 1**: 25 applications
- **Week 2**: 25 applications + follow-ups
- **Week 3**: 25 applications + follow-ups
- **Week 4**: 25 applications + follow-ups

**Expected Outcome**:
- 5-15 responses per month
- 2-5 interviews per month
- 1-2 offers per quarter

---

## 🚀 Ready to Start?

```bash
# 1. Check everything is ready
python system_check.py

# 2. Run the automation
python comprehensive_job_search.py

# 3. Monitor your email
# Check: canaby007@gmail.com

# 4. Track progress
python export_to_sheets.py
```

---

**Good luck with your job search! 🎉**

*Remember: Consistency is key. Run weekly for best results.*
