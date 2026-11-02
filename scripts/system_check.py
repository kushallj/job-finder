#!/usr/bin/env python3
"""
System Readiness Check
Verifies all components are ready for job search automation
"""

import os
import sys
import asyncio
import sqlite3

def check_files():
    """Check required files exist"""
    print("📁 Checking required files...")
    
    required = {
        "data/resume.txt": "Resume text file",
        "data/resume.pdf": "Resume PDF file",
        "job_automation.db": "Database file",
        ".env": "Environment configuration"
    }
    
    all_good = True
    for path, desc in required.items():
        if os.path.exists(path):
            print(f"   ✅ {desc}: {path}")
        else:
            print(f"   ❌ {desc} missing: {path}")
            all_good = False
    
    return all_good

def check_database():
    """Check database schema"""
    print("\n🗄️  Checking database schema...")
    
    try:
        conn = sqlite3.connect("job_automation.db")
        cursor = conn.cursor()
        
        # Check outreach_records table
        cursor.execute("PRAGMA table_info(outreach_records)")
        columns = {row[1] for row in cursor.fetchall()}
        
        required_columns = {
            'email_sent', 'contact_email', 'contact_name', 
            'follow_up_count', 'last_follow_up_at'
        }
        
        missing = required_columns - columns
        if missing:
            print(f"   ❌ Missing columns: {missing}")
            print("   💡 Run: python migrate_database.py")
            conn.close()
            return False
        
        print("   ✅ Database schema is up to date")
        
        # Check table counts
        cursor.execute("SELECT COUNT(*) FROM jobs")
        job_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM contacts")
        contact_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM outreach_records")
        outreach_count = cursor.fetchone()[0]
        
        print(f"   📊 Current data: {job_count} jobs, {contact_count} contacts, {outreach_count} outreach records")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return False

async def check_ollama():
    """Check Ollama service"""
    print("\n🤖 Checking Ollama AI service...")
    
    try:
        from src.ai.local_llm_service import LocalLLMService
        
        llm = LocalLLMService()
        is_healthy = await llm.health_check()
        
        if is_healthy:
            print(f"   ✅ Ollama is running with model: {llm._cached_model}")
            return True
        else:
            print("   ❌ Ollama not responding")
            print("   💡 Start Ollama: ollama serve")
            print("   💡 Or install: curl -fsSL https://ollama.com/install.sh | sh")
            return False
            
    except Exception as e:
        print(f"   ❌ Ollama check failed: {e}")
        return False

def check_env():
    """Check environment variables"""
    print("\n⚙️  Checking environment configuration...")
    
    try:
        from src.config import settings
        
        checks = {
            "Gmail address": settings.gmail_address,
            "Gmail password": settings.gmail_password,
            "Sender name": getattr(settings, 'sender_name', 'Kushall Jain'),
        }
        
        all_good = True
        for name, value in checks.items():
            if value and value != "Not set":
                # Mask sensitive values
                if "password" in name.lower():
                    display = "***" + value[-4:] if len(value) > 4 else "***"
                else:
                    display = value
                print(f"   ✅ {name}: {display}")
            else:
                print(f"   ⚠️  {name}: Not configured")
                if "password" in name.lower() or "address" in name.lower():
                    all_good = False
        
        return all_good
        
    except Exception as e:
        print(f"   ❌ Config error: {e}")
        return False

async def main():
    """Run all checks"""
    print("🔍 Job Search Automation System Check")
    print("=" * 60)
    
    results = {
        "Files": check_files(),
        "Database": check_database(),
        "Ollama": await check_ollama(),
        "Environment": check_env()
    }
    
    print("\n" + "=" * 60)
    print("📋 Summary:")
    
    all_passed = True
    for component, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {component}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 All systems ready!")
        print("\n💡 You can now run:")
        print("   python comprehensive_job_search.py")
        return 0
    else:
        print("⚠️  Some components need attention")
        print("\n💡 Fix the issues above and run this check again:")
        print("   python system_check.py")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
