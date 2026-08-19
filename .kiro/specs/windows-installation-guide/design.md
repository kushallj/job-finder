# Design Document: Windows Installation Guide

## Overview

This design specifies the structure, content, and organization of the `WINDOWS_INSTALLATION_GUIDE.md` file - a comprehensive Windows-specific installation guide for the job-finder automation system. The guide will enable Windows users to successfully install and configure a complex Python-based application involving AI services (Ollama), web automation (Selenium/ChromeDriver), email automation (Gmail), and various APIs.

### Design Rationale

The existing documentation (`README.md`, `QUICK_START.md`) provides Unix-focused commands and assumes familiarity with terminal environments. Windows users face unique challenges:

- Different path separators (`\` vs `/`)
- Different shell environments (CMD vs PowerShell vs Bash)
- Different executable extensions (`.exe`, `.bat`)
- Virtual environment activation syntax differences
- PATH variable configuration complexity
- Service management differences (Ollama as Windows service)
- Antivirus and permission considerations

This guide addresses these Windows-specific challenges with native commands, proper path syntax, and Windows-focused troubleshooting.

### Target Audience

- Windows 10/11 users with basic computer skills
- Users new to Python development on Windows
- Users unfamiliar with command-line interfaces
- Users who may not have development tools pre-installed

### Success Criteria

A Windows user with zero prior setup should be able to:
1. Follow the guide sequentially without external resources
2. Complete installation within 30-45 minutes
3. Successfully run `python system_check.py` with all checks passing
4. Execute `python comprehensive_job_search.py` and see job results

## Architecture

### Document Structure

The guide follows a linear, step-by-step architecture:

```
Table of Contents
├── Prerequisites Section
│   ├── System Requirements
│   ├── Download Links
│   └── Verification Commands
├── Installation Sections (Sequential)
│   ├── Python Setup
│   ├── Git Installation
│   ├── Project Clone & Setup
│   ├── Virtual Environment
│   ├── Dependencies Installation
│   ├── Ollama Installation
│   ├── ChromeDriver Setup
│   ├── Database Initialization
│   ├── Gmail Configuration
│   └── Environment Variables
├── Verification Section
│   ├── System Check
│   ├── AI Test
│   └── Dry Run Test
├── Running the System
│   ├── First Run
│   ├── Monitoring Progress
│   └── Stopping Safely
├── Troubleshooting Section
│   ├── Python PATH Issues
│   ├── Virtual Environment Issues
│   ├── Ollama Service Issues
│   ├── ChromeDriver Issues
│   ├── Permission Issues
│   ├── Database Locking
│   └── Antivirus Blocking
├── Next Steps & Resources
└── Appendices
    ├── Command Reference
    └── File Locations
```

### Information Architecture Principles

1. **Progressive Disclosure**: Start with simple concepts, build to complex configurations
2. **Just-in-Time Information**: Explain concepts right before they're needed
3. **Error Prevention**: Warn about common mistakes before they happen
4. **Recovery Guidance**: Provide troubleshooting immediately after each major step
5. **Windows-First Design**: All commands use Windows-native syntax (no WSL/Git Bash assumptions)

### Command Syntax Strategy

All commands will use Windows Command Prompt (CMD) syntax by default, with PowerShell alternatives noted where significantly different:

```batch
REM Command Prompt (default)
python -m venv venv
venv\Scripts\activate.bat

# PowerShell (alternative)
python -m venv venv
venv\Scripts\Activate.ps1
```

## Components and Interfaces

### Document Components

#### 1. Prerequisites Section Component

**Purpose**: Ensure users have all required software before beginning installation

**Structure**:
```markdown
## Prerequisites

Before you begin, you'll need to install these tools:

### 1. Python 3.11 or Higher ✅
- **Download**: [Python for Windows](https://www.python.org/downloads/windows/)
- **Important**: Check "Add Python to PATH" during installation
- **Verify**: Open Command Prompt and run:
  ```cmd
  python --version
  ```
  You should see: `Python 3.11.x` or higher

### 2. Git for Windows ✅
- **Download**: [Git for Windows](https://git-scm.com/download/win)
- **Verify**: Open Command Prompt and run:
  ```cmd
  git --version
  ```
  You should see: `git version 2.x.x`

[... continues for each prerequisite]
```

**Key Features**:
- Download links to official sources
- Visual indicators (checkmarks, emojis)
- Verification commands with expected output
- "Important" callouts for critical installation options

#### 2. Installation Step Component (Template)

Each installation step follows a consistent pattern:

**Structure**:
```markdown
## Step X: [Component Name]

[Brief explanation of what this component does and why it's needed]

### Installation Instructions

1. [First step with command]
   ```cmd
   [command here]
   ```

2. [Second step with command]
   ```cmd
   [command here]
   ```

### Verification

Check that [component] is installed correctly:
```cmd
[verification command]
```

**Expected output**: [description of correct output]

### Troubleshooting

❌ **Problem**: [Common issue]
✅ **Solution**: [How to fix it]

[Repeat for 2-3 common issues]

---
```

**Key Features**:
- Clear purpose statement
- Numbered sequential steps
- Code blocks with proper syntax highlighting
- Verification commands
- Expected output descriptions
- Inline troubleshooting

#### 3. Python Installation Component

**Specific Content**:
- Download link to Python 3.11+ Windows installer
- Screenshot description of "Add Python to PATH" checkbox
- Detailed PATH troubleshooting if checkbox was missed
- Manual PATH editing instructions with step-by-step Windows UI navigation
- Verification commands for both Python and pip

**Windows-Specific Considerations**:
- Explain Microsoft Store Python vs Official Python
- Recommend official Python installer
- Explain why PATH is critical
- Provide fallback: using full path to python.exe

#### 4. Virtual Environment Component

**Specific Content**:
- Explanation of why virtual environments are needed
- Commands to create venv on Windows
- Activation commands for CMD and PowerShell
- Visual indicator of activation (prompt change)
- Deactivation command
- Troubleshooting execution policy errors (PowerShell)

**Windows-Specific Considerations**:
```cmd
REM Create virtual environment
python -m venv venv

REM Activate in CMD
venv\Scripts\activate.bat

REM Activate in PowerShell (may require execution policy change)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1

REM Verify activation - prompt should show (venv)
```

#### 5. Ollama Installation Component

**Specific Content**:
- Download link to Ollama Windows installer
- Installation wizard walkthrough
- Service startup commands
- Model download commands (`ollama pull phi3:mini`)
- Service management (start, stop, status)
- Auto-start configuration
- Testing Ollama API endpoint

**Windows-Specific Considerations**:
- Ollama installs as Windows service
- Service management via Services app or `sc` command
- Default installation path: `C:\Users\<username>\AppData\Local\Programs\Ollama`
- Models stored in: `C:\Users\<username>\.ollama\models`
- Firewall exceptions (if needed)

**Service Management**:
```cmd
REM Check if Ollama service is running
sc query ollama

REM Start Ollama service
sc start ollama

REM Configure auto-start
sc config ollama start= auto

REM Test Ollama API
curl http://localhost:11434/api/tags
```

#### 6. ChromeDriver Component

**Specific Content**:
- Explain that webdriver-manager auto-installs ChromeDriver
- Manual installation fallback instructions
- Chrome version checking
- ChromeDriver version matching
- PATH configuration for manual installation

**Windows-Specific Considerations**:
- Chrome typically installed in: `C:\Program Files\Google\Chrome\Application\`
- ChromeDriver should be in PATH or project directory
- Windows Defender SmartScreen warnings
- Explain that first run may trigger Chrome driver download

#### 7. Environment Variables Component

**Specific Content**:
- Copying `.env.example` to `.env` on Windows
- Editing `.env` with Notepad or VS Code
- Each variable explained with example values
- Mandatory vs optional variables clearly marked
- Gmail app password generation walkthrough
- API key acquisition links

**Windows-Specific Considerations**:
```cmd
REM Copy .env.example to .env
copy .env.example .env

REM Edit with Notepad
notepad .env

REM Or use VS Code if installed
code .env
```

**Variable Documentation Format**:
```markdown
### Required Variables ⚠️

#### GMAIL_ADDRESS
- **Purpose**: Your Gmail account for sending outreach emails
- **Example**: `your.email@gmail.com`
- **How to get**: Use your existing Gmail account

#### GMAIL_PASSWORD
- **Purpose**: Gmail App Password (NOT your regular password)
- **Example**: `abcd efgh ijkl mnop` (16 characters with spaces)
- **How to get**: See "Gmail Configuration" section below
- **Security**: Never commit this to Git

[... continues for each variable]
```

#### 8. Troubleshooting Component

**Structure**: Problem-solution pairs organized by category

**Categories**:
1. Python PATH Issues
2. Virtual Environment Activation
3. Ollama Service Issues
4. ChromeDriver/Selenium Issues
5. File Permissions
6. Database Locking
7. Antivirus Interference
8. Network/Firewall Issues

**Format**:
```markdown
### Python Not Recognized

❌ **Problem**: Running `python --version` shows:
```
'python' is not recognized as an internal or external command
```

✅ **Solution**: Python is not in your PATH. Follow these steps:

1. Open Windows Settings (Win + I)
2. Search for "Environment Variables"
3. Click "Environment Variables" button
4. Under "System variables", find "Path"
5. Click "Edit"
6. Click "New" and add: `C:\Users\YourUsername\AppData\Local\Programs\Python\Python311\`
7. Click "New" again and add: `C:\Users\YourUsername\AppData\Local\Programs\Python\Python311\Scripts\`
8. Click "OK" on all dialogs
9. **Close and reopen Command Prompt**
10. Try `python --version` again

**Alternative**: Use full path to Python:
```cmd
C:\Users\YourUsername\AppData\Local\Programs\Python\Python311\python.exe --version
```
```

#### 9. Verification Component

**Specific Content**:
- System check script execution
- Expected output for each check
- Interpreting success/failure messages
- AI functionality test
- Dry-run outreach test

**Commands**:
```cmd
REM Run comprehensive system check
python system_check.py

REM Test local AI
python test_local_ai.py

REM Test outreach without sending emails
python outreach_cli.py outreach --dry-run
```

**Expected Output Documentation**:
```markdown
### Expected System Check Output

✅ All checks should show green checkmarks:

```
✅ Database connection successful
✅ SQLite version: 3.x.x
✅ All required tables exist
✅ Ollama service is running
✅ Ollama model 'phi3:mini' is available
✅ Gmail configuration is valid
✅ Resume file found: data/resume.pdf
✅ Chrome browser detected
✅ ChromeDriver compatible
```

❌ If any check fails, see the Troubleshooting section for that component.
```

## Data Models

### Document Metadata

The guide itself contains structured information:

```markdown
---
Document: WINDOWS_INSTALLATION_GUIDE.md
Target OS: Windows 10/11
Python Version: 3.11+
Last Updated: 2024
Estimated Completion Time: 30-45 minutes
Difficulty Level: Beginner-Friendly
---
```

### Configuration File Template

The `.env` file structure (documented in guide):

```ini
# Database
DATABASE_URL=sqlite:///./job_automation.db

# Email Configuration (Required)
GMAIL_ADDRESS=your.email@gmail.com
GMAIL_PASSWORD=your_16_char_app_password

# Ollama Configuration (Required)
OLLAMA_MODEL=phi3:mini
OLLAMA_KEEP_ALIVE=5m

# Job Search API (Required)
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key

# Optional: Email Discovery APIs
HUNTER_API_KEY=optional_hunter_key
APOLLO_API_KEY=optional_apollo_key

# Optional: Google Sheets Integration
GOOGLE_CREDENTIALS_PATH=config/google-service-account.json
GOOGLE_SHEET_TITLE=Job Search Tracker
```

### Installation State Model

While not persisted, the guide implicitly tracks installation state:

```typescript
interface InstallationState {
  prerequisites: {
    python: {installed: boolean, version: string, inPath: boolean}
    git: {installed: boolean, version: string}
    chrome: {installed: boolean, version: string}
  }
  project: {
    cloned: boolean
    venvCreated: boolean
    venvActivated: boolean
    dependenciesInstalled: boolean
  }
  services: {
    ollama: {installed: boolean, running: boolean, modelDownloaded: boolean}
    chromedriver: {available: boolean, version: string}
  }
  configuration: {
    envFileCreated: boolean
    gmailConfigured: boolean
    apiKeysAdded: boolean
  }
  verification: {
    systemCheckPassed: boolean
    aiTestPassed: boolean
  }
}
```

Each section of the guide advances this state.

## Error Handling

### Error Prevention Strategy

The guide prevents errors through:

1. **Pre-flight Checks**: Verify each prerequisite before moving forward
2. **Clear Prerequisites**: List all requirements upfront
3. **Warning Callouts**: Highlight critical steps that users often miss
4. **Command Verification**: Every command has a verification step
5. **Expected Output**: Show what success looks like

### Error Recovery Strategy

When errors occur:

1. **Inline Troubleshooting**: Common issues addressed immediately after each step
2. **Dedicated Troubleshooting Section**: Comprehensive problem-solution index
3. **Rollback Instructions**: How to undo changes if needed
4. **Clean Reinstall**: Nuclear option for completely starting over

### Error Categories

#### 1. Installation Errors

**Symptom**: Software fails to install
**Recovery**: 
- Verify download integrity
- Check system requirements
- Disable antivirus temporarily
- Use administrator privileges

#### 2. PATH Errors

**Symptom**: Command not recognized
**Recovery**:
- Add to PATH manually (step-by-step GUI instructions)
- Use full paths as workaround
- Restart terminal
- Verify PATH variable spelling

#### 3. Permission Errors

**Symptom**: Access denied, file locked
**Recovery**:
- Run as administrator
- Close conflicting applications
- Check file permissions
- Disable antivirus temporarily

#### 4. Dependency Errors

**Symptom**: Package installation fails
**Recovery**:
- Update pip: `python -m pip install --upgrade pip`
- Use `--no-cache-dir` flag
- Install packages individually
- Check internet connection

#### 5. Service Errors

**Symptom**: Ollama service won't start
**Recovery**:
- Check Windows Services app
- Review Ollama logs
- Reinstall Ollama
- Check port 11434 availability

#### 6. Virtual Environment Errors

**Symptom**: Can't activate venv
**Recovery**:
- Use correct script (.bat for CMD, .ps1 for PowerShell)
- Change PowerShell execution policy
- Recreate virtual environment
- Use full path to activation script

### Logging and Diagnostics

The guide directs users to relevant log files:

```markdown
### Finding Log Files

The system creates logs in the `logs/` directory:

```cmd
dir logs
```

Key log files:
- `logs/main.log` - General application logs
- `logs/email_outreach.log` - Email sending logs
- `logs/contact_discovery.log` - Contact finding logs

To view recent logs:
```cmd
REM View last 50 lines
powershell Get-Content logs\main.log -Tail 50

REM Or open in Notepad
notepad logs\main.log
```
```

## Testing Strategy

Since this is documentation (not code), testing focuses on **validation** rather than automated tests.

### Documentation Testing Approach

#### 1. Technical Accuracy Review

**Method**: Expert review checklist
**Validates**: 
- Commands are correct for Windows
- Path syntax uses Windows conventions
- Software versions are current
- Download links are valid
- Configuration examples match actual `.env.example`

**Checklist**:
- [ ] All commands tested on fresh Windows 10 installation
- [ ] All commands tested on fresh Windows 11 installation
- [ ] All download links lead to official sources
- [ ] All verification commands produce documented output
- [ ] All troubleshooting solutions verified

#### 2. User Testing

**Method**: Observe real Windows users following the guide
**Validates**: 
- Instructions are clear and unambiguous
- Users don't get stuck
- Completion time matches estimate
- Users can successfully run the system

**Test Protocol**:
1. Recruit 3 Windows users (varying technical levels)
2. Provide only the installation guide (no other help)
3. Observe where they hesitate or make mistakes
4. Record completion time
5. Ask users to run `python system_check.py`
6. Collect feedback on clarity and completeness

**Success Criteria**:
- 3/3 users complete installation successfully
- Average completion time < 60 minutes
- Users rate clarity 4/5 or higher
- No critical errors encountered

#### 3. Link Validation

**Method**: Automated link checker
**Validates**: All external links are accessible

**Implementation**:
```python
# tests/test_installation_guide_links.py
import re
import requests
from pathlib import Path

def test_all_links_valid():
    """Verify all links in installation guide are accessible"""
    guide_path = Path("WINDOWS_INSTALLATION_GUIDE.md")
    content = guide_path.read_text()
    
    # Extract all markdown links
    links = re.findall(r'\[.*?\]\((https?://.*?)\)', content)
    
    for link in links:
        response = requests.head(link, allow_redirects=True, timeout=10)
        assert response.status_code == 200, f"Link broken: {link}"
```

#### 4. Command Validation

**Method**: Automated syntax checking
**Validates**: Commands use correct Windows syntax

**Implementation**:
```python
# tests/test_installation_guide_commands.py
import re
from pathlib import Path

def test_no_unix_paths():
    """Ensure no Unix-style paths in guide"""
    guide_path = Path("WINDOWS_INSTALLATION_GUIDE.md")
    content = guide_path.read_text()
    
    # Extract code blocks
    code_blocks = re.findall(r'```(?:cmd|batch|powershell)\n(.*?)\n```', content, re.DOTALL)
    
    for block in code_blocks:
        # Check for Unix path separators in non-URL contexts
        lines = block.split('\n')
        for line in lines:
            if '/' in line and 'http' not in line:
                # This might be a Unix path
                assert '\\' in line or line.strip().startswith('#'), \
                    f"Possible Unix path in Windows guide: {line}"

def test_venv_activation_syntax():
    """Verify virtual environment activation uses Windows syntax"""
    guide_path = Path("WINDOWS_INSTALLATION_GUIDE.md")
    content = guide_path.read_text()
    
    # Should use venv\Scripts\activate
    assert r'venv\Scripts\activate' in content, \
        "Missing Windows venv activation syntax"
    
    # Should not use source (Unix command)
    assert 'source venv' not in content, \
        "Unix 'source' command found in Windows guide"
```

#### 5. Completeness Check

**Method**: Requirements traceability matrix
**Validates**: All acceptance criteria addressed

**Matrix**:
| Requirement | Section | Verified |
|-------------|---------|----------|
| 1.1 Document Python version | Prerequisites | ✅ |
| 1.2 Document Git requirement | Prerequisites | ✅ |
| 1.3 Document Chrome requirement | Prerequisites | ✅ |
| 1.4 Provide download links | Prerequisites | ✅ |
| 1.5 Verification commands | Prerequisites | ✅ |
| ... | ... | ... |

#### 6. Example-Based Integration Tests

While the guide itself isn't code, we can test the commands it documents:

**Integration Test Suite**:
```python
# tests/test_windows_installation.py
import subprocess
import sys
from pathlib import Path

def test_python_version_check():
    """Test that Python version check command works"""
    result = subprocess.run(
        ["python", "--version"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Python 3." in result.stdout

def test_pip_version_check():
    """Test that pip version check command works"""
    result = subprocess.run(
        ["pip", "--version"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "pip" in result.stdout

def test_venv_creation():
    """Test virtual environment creation"""
    test_venv = Path("test_venv")
    
    # Create venv
    result = subprocess.run(
        [sys.executable, "-m", "venv", str(test_venv)],
        capture_output=True
    )
    assert result.returncode == 0
    assert test_venv.exists()
    assert (test_venv / "Scripts" / "activate.bat").exists()
    
    # Cleanup
    import shutil
    shutil.rmtree(test_venv)

def test_ollama_service_check():
    """Test Ollama service status command"""
    result = subprocess.run(
        ["sc", "query", "ollama"],
        capture_output=True,
        text=True
    )
    # May fail if Ollama not installed - that's okay
    # This just validates the command syntax
    assert result.returncode in [0, 1060]  # 0 = running, 1060 = not installed
```

### Manual Testing Checklist

Before releasing the guide, manually verify:

- [ ] Fresh Windows 10 VM: Complete installation successful
- [ ] Fresh Windows 11 VM: Complete installation successful
- [ ] All commands copy-pasteable without modification
- [ ] All code blocks have correct syntax highlighting
- [ ] All emoji/icons render correctly in common Markdown viewers
- [ ] Table of contents links work
- [ ] Guide renders correctly in GitHub
- [ ] Guide renders correctly in VS Code
- [ ] Guide prints correctly (if users want physical copy)

### Continuous Validation

As the project evolves:

1. **Dependency Changes**: When `requirements.txt` changes, review guide
2. **Version Bumps**: When minimum Python version changes, update guide
3. **New Features**: When new services added, update installation steps
4. **Bug Reports**: When users report installation issues, add to troubleshooting
5. **Quarterly Review**: Re-test guide on fresh Windows installations

### Documentation Quality Metrics

Track these metrics over time:

- **Completion Rate**: % of users who successfully complete installation
- **Average Completion Time**: Should be ≤ 45 minutes
- **Support Requests**: Number of installation help requests (should decrease)
- **First-Run Success**: % of users who successfully run system check on first try
- **User Satisfaction**: Survey score for guide clarity (target: 4.5/5)

## Next Steps

After the design is approved, implementation involves:

1. **Create WINDOWS_INSTALLATION_GUIDE.md** following this design
2. **Test on fresh Windows VMs** (Windows 10 and 11)
3. **User testing with 3 Windows users**
4. **Iterate based on feedback**
5. **Add to main README** with prominent link for Windows users
6. **Create validation tests** for commands and links
7. **Establish quarterly review schedule**

## References

- [Requirements Document](./requirements.md)
- [README.md](../../README.md) - Main project documentation
- [QUICK_START.md](../../QUICK_START.md) - Usage guide
- [API_KEYS_CHECKLIST.md](../../API_KEYS_CHECKLIST.md) - API configuration
- [Windows Environment Variables Documentation](https://docs.microsoft.com/en-us/windows/deployment/usmt/usmt-recognized-environment-variables)
- [Python on Windows](https://docs.python.org/3/using/windows.html)
- [Ollama Windows Installation](https://ollama.ai/download/windows)
- [ChromeDriver Documentation](https://chromedriver.chromium.org/getting-started)
