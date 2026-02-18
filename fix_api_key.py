#!/usr/bin/env python3
"""
API Key Diagnostic and Fix Tool
"""

import asyncio
import os
from src.ai.claude_service import ClaudeService

async def test_anthropic_api():
    """Test Anthropic API key"""
    print("🔍 Testing Anthropic API Key...")
    
    try:
        claude = ClaudeService()
        
        # Test with a simple job description
        test_job = """
        We are looking for a Python Developer with experience in Django and FastAPI.
        The candidate should have 3+ years of experience in backend development.
        """
        
        print("📝 Testing skill extraction...")
        skills = await claude.extract_skills(test_job)
        
        if skills and skills.get('technical_skills'):
            print("✅ Anthropic API is working!")
            print(f"   Found skills: {skills['technical_skills'][:3]}")
            return True
        else:
            print("⚠️  API responded but with empty results")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if "authentication_error" in error_msg or "invalid x-api-key" in error_msg:
            print("❌ Anthropic API key is invalid or expired")
            print("   Please get a new API key from: https://console.anthropic.com/")
        else:
            print(f"❌ Anthropic API error: {e}")
        return False

def check_env_file():
    """Check .env file for API keys"""
    print("\n🔍 Checking .env file...")
    
    env_path = ".env"
    if not os.path.exists(env_path):
        print("❌ .env file not found!")
        return False
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Check for required keys
    required_keys = [
        'ANTHROPIC_API_KEY',
        'ADZUNA_APP_ID', 
        'ADZUNA_APP_KEY',
        'GMAIL_ADDRESS',
        'GMAIL_PASSWORD'
    ]
    
    missing_keys = []
    for key in required_keys:
        if key not in content or f"{key}=" not in content:
            missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ Missing keys in .env: {missing_keys}")
        return False
    else:
        print("✅ All required keys found in .env")
        return True

async def test_fallback_system():
    """Test the fallback AI system"""
    print("\n🔍 Testing Fallback AI System...")
    
    try:
        from src.ai.fallback_service import FallbackAIService
        fallback = FallbackAIService()
        
        test_job = """
        We are looking for a Python Developer with experience in Django and FastAPI.
        The candidate should have 3+ years of experience in backend development.
        """
        
        skills = await fallback.extract_skills(test_job)
        
        if skills and skills.get('technical_skills'):
            print("✅ Fallback AI system is working!")
            print(f"   Found skills: {skills['technical_skills'][:3]}")
            return True
        else:
            print("❌ Fallback AI system failed")
            return False
            
    except Exception as e:
        print(f"❌ Fallback AI error: {e}")
        return False

def show_solutions():
    """Show solutions for fixing API issues"""
    print("\n💡 Solutions:")
    print("=" * 50)
    
    print("\n1. 🔑 Fix Anthropic API Key:")
    print("   • Go to: https://console.anthropic.com/")
    print("   • Sign in or create account")
    print("   • Generate new API key")
    print("   • Replace ANTHROPIC_API_KEY in .env file")
    
    print("\n2. 📧 Fix Gmail Settings:")
    print("   • Go to: https://myaccount.google.com/apppasswords")
    print("   • Generate app password for Mail")
    print("   • Replace GMAIL_PASSWORD in .env file")
    
    print("\n3. 🔄 Use Fallback Mode (Temporary):")
    print("   • System will work with basic AI matching")
    print("   • No external API calls needed")
    print("   • Less accurate but functional")
    
    print("\n4. 🧪 Test Individual Components:")
    print("   • python fix_api_key.py")
    print("   • python outreach_cli.py stats")
    print("   • python test_foorilla.py")

async def main():
    """Main diagnostic function"""
    print("🔧 API Key Diagnostic Tool")
    print("=" * 40)
    
    # Check .env file
    env_ok = check_env_file()
    
    # Test Anthropic API
    anthropic_ok = await test_anthropic_api()
    
    # Test fallback system
    fallback_ok = await test_fallback_system()
    
    # Summary
    print("\n📊 Diagnostic Summary:")
    print("=" * 30)
    print(f"   .env file: {'✅' if env_ok else '❌'}")
    print(f"   Anthropic API: {'✅' if anthropic_ok else '❌'}")
    print(f"   Fallback AI: {'✅' if fallback_ok else '❌'}")
    
    if anthropic_ok:
        print("\n🎉 All systems working! You can run:")
        print("   python comprehensive_job_search.py")
    elif fallback_ok:
        print("\n⚠️  Running in fallback mode. Job matching will work but be less accurate.")
        print("   You can still run: python comprehensive_job_search.py")
    else:
        print("\n❌ System needs attention before running job search.")
    
    show_solutions()

if __name__ == "__main__":
    asyncio.run(main())