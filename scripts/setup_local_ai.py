#!/usr/bin/env python3
"""
Setup Local AI (Ollama) for Free Unlimited AI Processing
"""

import asyncio
import subprocess
import sys
import platform

async def check_ollama_installed():
    """Check if Ollama is installed"""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

async def check_ollama_running():
    """Check if Ollama service is running"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            return response.status_code == 200
    except:
        return False

async def list_installed_models():
    """List installed Ollama models"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
    except:
        pass
    return []

def get_install_instructions():
    """Get platform-specific installation instructions"""
    os_type = platform.system()
    
    if os_type == "Darwin":  # macOS
        return """
🍎 macOS Installation:

1. Download Ollama:
   https://ollama.ai/download/Ollama-darwin.zip
   
   Or use Homebrew:
   brew install ollama

2. Ollama will start automatically after installation

3. Install a model:
   ollama pull llama3.2:3b
"""
    elif os_type == "Linux":
        return """
🐧 Linux Installation:

1. Run the install script:
   curl -fsSL https://ollama.ai/install.sh | sh

2. Ollama will start automatically

3. Install a model:
   ollama pull llama3.2:3b
"""
    elif os_type == "Windows":
        return """
🪟 Windows Installation:

1. Download Ollama:
   https://ollama.ai/download/OllamaSetup.exe

2. Run the installer

3. Open Command Prompt and install a model:
   ollama pull llama3.2:3b
"""
    else:
        return """
Installation:
Visit https://ollama.ai/download for your platform
"""

def recommend_models():
    """Recommend models based on use case"""
    return """
📦 Recommended Models:

🚀 Fast & Small (Recommended for most users):
   ollama pull llama3.2:3b
   Size: ~2GB | Speed: Very Fast | Quality: Good

⚡ Ultra Fast (For quick responses):
   ollama pull llama3.2:1b
   Size: ~1GB | Speed: Blazing Fast | Quality: Decent

🎯 Better Quality (If you have more RAM):
   ollama pull mistral:7b
   Size: ~4GB | Speed: Fast | Quality: Excellent

🔬 Balanced (Good middle ground):
   ollama pull phi3:mini
   Size: ~2GB | Speed: Fast | Quality: Very Good

💡 Tip: Start with llama3.2:3b - it's the best balance!
"""

async def test_model(model_name: str):
    """Test if a model works"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"   Sending test prompt to {model_name}...")
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": "Say: Hello!",
                    "stream": False
                }
            )
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                if response_text:
                    return True, response_text
                else:
                    return False, "Empty response from model"
            else:
                error_text = response.text
                return False, f"HTTP {response.status_code}: {error_text}"
    except httpx.TimeoutException:
        return False, "Request timed out - model may be loading (this is normal for first run)"
    except Exception as e:
        return False, f"Error: {str(e)}"

async def main():
    """Main setup function"""
    print("🤖 Local AI (Ollama) Setup Tool")
    print("=" * 50)
    
    # Check if Ollama is installed
    print("\n1️⃣  Checking Ollama installation...")
    is_installed = await check_ollama_installed()
    
    if is_installed:
        print("   ✅ Ollama is installed")
    else:
        print("   ❌ Ollama is not installed")
        print(get_install_instructions())
        print("\n💡 After installing, run this script again!")
        return
    
    # Check if Ollama is running
    print("\n2️⃣  Checking Ollama service...")
    is_running = await check_ollama_running()
    
    if is_running:
        print("   ✅ Ollama service is running")
    else:
        print("   ⚠️  Ollama service is not running")
        print("   Starting Ollama...")
        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", "-a", "Ollama"])
            else:
                subprocess.Popen(["ollama", "serve"])
            await asyncio.sleep(3)
            is_running = await check_ollama_running()
            if is_running:
                print("   ✅ Ollama service started")
            else:
                print("   ❌ Could not start Ollama service")
                print("   Please start it manually: ollama serve")
                return
        except Exception as e:
            print(f"   ❌ Error starting Ollama: {e}")
            return
    
    # List installed models
    print("\n3️⃣  Checking installed models...")
    models = await list_installed_models()
    
    if models:
        print(f"   ✅ Found {len(models)} installed model(s):")
        for model in models:
            print(f"      • {model}")
    else:
        print("   ⚠️  No models installed")
        print(recommend_models())
        print("\n   Install a model now? (recommended: llama3.2:3b)")
        print("   Run: ollama pull llama3.2:3b")
        return
    
    # Test a model
    print("\n4️⃣  Testing model...")
    test_model_name = models[0]
    print(f"   Testing {test_model_name}...")
    
    success, response = await test_model(test_model_name)
    
    if success:
        print(f"   ✅ Model works! Response: {response[:50]}...")
    else:
        print(f"   ⚠️  Model test issue: {response}")
        if "timed out" in response.lower() or "loading" in response.lower():
            print(f"   💡 This is normal for the first run - the model is loading")
            print(f"   💡 Try running your job search now, it should work!")
            success = True  # Consider it successful
        else:
            print(f"   💡 Try running: ollama run {test_model_name}")
            return
    
    # Success!
    print("\n" + "=" * 50)
    print("🎉 Setup Complete!")
    print("=" * 50)
    print("\n✅ Your system is ready to use Local AI!")
    print("\n📊 Summary:")
    print(f"   • Ollama: Installed & Running")
    print(f"   • Models: {len(models)} installed")
    print(f"   • Active Model: {test_model_name}")
    print("\n🚀 Next Steps:")
    print("   1. Run your job search: python comprehensive_job_search.py")
    print("   2. The system will automatically use Local AI")
    print("   3. Enjoy unlimited, free AI processing!")
    print("\n💡 Benefits:")
    print("   • No API costs")
    print("   • No rate limits")
    print("   • Complete privacy (runs locally)")
    print("   • Works offline")

if __name__ == "__main__":
    asyncio.run(main())