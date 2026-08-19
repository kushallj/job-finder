# Implementation Plan: Windows Installation Guide

## Overview

This plan breaks down the creation of `WINDOWS_INSTALLATION_GUIDE.md` into discrete documentation tasks. Each task involves writing specific sections of the guide following the design structure, using Windows-native command syntax, and ensuring all requirements are addressed. The guide will enable Windows users to successfully install and configure the job-finder automation system.

## Tasks

- [ ] 1. Create guide structure and metadata
  - Create `WINDOWS_INSTALLATION_GUIDE.md` in project root
  - Add document metadata (title, description, estimated time)
  - Create table of contents with section links
  - Add introduction explaining purpose and target audience
  - _Requirements: 12.6, 12.1_

- [ ] 2. Write prerequisites section
  - [ ] 2.1 Document system requirements
    - List Windows 10/11 requirement
    - Document minimum Python version (3.11+)
    - Document Git requirement with download link
    - Document Chrome browser requirement with download link
    - Add verification commands for each prerequisite
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ] 2.2 Add prerequisite verification instructions
    - Provide `python --version` command with expected output
    - Provide `git --version` command with expected output
    - Provide Chrome version check instructions (chrome://version)
    - Add troubleshooting notes for "command not found" errors
    - _Requirements: 1.5, 2.3, 2.4_

- [ ] 3. Write Python environment setup section
  - [ ] 3.1 Document Python installation
    - Provide Python 3.11+ download link for Windows
    - Explain "Add Python to PATH" checkbox importance
    - Provide installation wizard walkthrough
    - Add verification commands (`python --version`, `pip --version`)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [ ] 3.2 Add PATH troubleshooting
    - Provide step-by-step Windows Settings navigation for PATH editing
    - Explain how to add Python directories to PATH manually
    - Provide alternative using full Python path
    - Add note about restarting Command Prompt after PATH changes
    - _Requirements: 2.5, 11.1_

- [ ] 4. Write project setup section
  - [ ] 4.1 Document repository cloning
    - Provide Git clone command with Windows path syntax
    - Provide Command Prompt navigation commands (cd)
    - Add verification that clone succeeded (dir command)
    - _Requirements: 3.1, 3.2_
  
  - [ ] 4.2 Document virtual environment setup
    - Provide `python -m venv venv` command
    - Provide activation command for CMD (`venv\Scripts\activate.bat`)
    - Provide activation command for PowerShell (`venv\Scripts\Activate.ps1`)
    - Explain PowerShell execution policy issue and solution
    - Show visual indicator of activation (prompt shows `(venv)`)
    - Add deactivation command
    - _Requirements: 3.3, 3.4, 3.6, 11.2_
  
  - [ ] 4.3 Document dependency installation
    - Provide `pip install -r requirements.txt` command
    - Explain what happens during installation
    - Add expected completion time
    - Provide troubleshooting for common pip errors
    - _Requirements: 3.5_

- [ ] 5. Write Ollama installation and configuration section
  - [ ] 5.1 Document Ollama installation
    - Provide Ollama Windows installer download link
    - Provide installation wizard walkthrough
    - Explain that Ollama installs as Windows service
    - Add default installation path information
    - _Requirements: 4.1, 4.2_
  
  - [ ] 5.2 Document Ollama service management
    - Provide command to check service status (`sc query ollama`)
    - Provide command to start service (`sc start ollama`)
    - Provide command to configure auto-start (`sc config ollama start= auto`)
    - Explain how to use Windows Services app as alternative
    - _Requirements: 4.3, 4.6_
  
  - [ ] 5.3 Document model download and verification
    - Provide `ollama pull phi3:mini` command
    - Provide `ollama list` verification command
    - Explain model storage location
    - Add expected download time
    - _Requirements: 4.4, 4.5_
  
  - [ ] 5.4 Add Ollama testing instructions
    - Reference `python test_local_ai.py` test script
    - Provide API endpoint test command (curl or PowerShell)
    - Add expected test output
    - Provide troubleshooting for service issues
    - _Requirements: 4.7, 11.3_

- [ ] 6. Write ChromeDriver setup section
  - [ ] 6.1 Document automatic ChromeDriver setup
    - Explain that webdriver-manager handles ChromeDriver automatically
    - Explain that first run may download ChromeDriver
    - Add note about Windows Defender SmartScreen warnings
    - _Requirements: 5.1_
  
  - [ ] 6.2 Document manual ChromeDriver setup (fallback)
    - Provide ChromeDriver download link
    - Explain Chrome version matching requirement
    - Provide command to check Chrome version
    - Provide instructions to add ChromeDriver to PATH
    - Add troubleshooting for version mismatch errors
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 11.4_

- [ ] 7. Write database initialization section
  - [ ] 7.1 Document SQLite setup
    - Explain that SQLite requires no separate installation
    - Explain database file location (./job_automation.db)
    - Provide command to initialize database schema
    - Add verification command to check database exists
    - _Requirements: 6.1, 6.3, 6.4_
  
  - [ ] 7.2 Add database troubleshooting
    - Provide database reset instructions
    - Explain SQLite locking issues on Windows
    - Provide solution for "database is locked" errors
    - _Requirements: 6.5, 11.6_

- [ ] 8. Write Gmail configuration section
  - [ ] 8.1 Document Gmail setup process
    - Explain need for Gmail App Password (not regular password)
    - Provide step-by-step 2FA enablement instructions
    - Provide step-by-step App Password generation instructions
    - Add security best practices for credential handling
    - _Requirements: 7.1, 7.2, 7.4_
  
  - [ ] 8.2 Add Gmail testing instructions
    - Explain how to test email configuration without sending emails
    - Reference dry-run testing capability
    - Add expected test output
    - _Requirements: 7.5_

- [ ] 9. Write environment variables configuration section
  - [ ] 9.1 Document .env file creation
    - Provide command to copy `.env.example` to `.env` (copy command)
    - Provide commands to edit .env (notepad, VS Code)
    - Explain difference between mandatory and optional variables
    - _Requirements: 8.1, 8.3_
  
  - [ ] 9.2 Document required environment variables
    - Document DATABASE_URL with example
    - Document GMAIL_ADDRESS with example
    - Document GMAIL_PASSWORD with example and security warning
    - Document OLLAMA_MODEL with example
    - Document ADZUNA_APP_ID and ADZUNA_APP_KEY with example
    - Reference API_KEYS_CHECKLIST.md for obtaining keys
    - _Requirements: 8.2, 8.4, 8.6_
  
  - [ ] 9.3 Document optional environment variables
    - Document HUNTER_API_KEY with example
    - Document APOLLO_API_KEY with example
    - Document GOOGLE_CREDENTIALS_PATH with example
    - Document GOOGLE_SHEET_TITLE with example
    - Explain purpose of each optional variable
    - _Requirements: 8.2, 8.3, 8.4_
  
  - [ ] 9.4 Add system environment variable instructions
    - Explain when system-wide variables might be needed
    - Provide Windows Settings navigation for system variables
    - Add note that .env file is preferred method
    - _Requirements: 8.5_

- [ ] 10. Write installation verification section
  - [ ] 10.1 Document system check execution
    - Provide `python system_check.py` command
    - Explain what each check validates
    - Show expected output for successful checks
    - Show expected output for failed checks
    - _Requirements: 9.1, 9.2, 9.5_
  
  - [ ] 10.2 Document AI functionality testing
    - Provide `python test_local_ai.py` command
    - Explain what this test validates
    - Show expected successful output
    - Add troubleshooting for AI test failures
    - _Requirements: 9.3_
  
  - [ ] 10.3 Document dry-run outreach testing
    - Provide dry-run test command
    - Explain that no emails are sent during dry-run
    - Show expected output
    - Add next steps if verification fails
    - _Requirements: 9.4, 9.6_

- [ ] 11. Write running the automation section
  - [ ] 11.1 Document first run instructions
    - Provide `python comprehensive_job_search.py` command
    - Explain each phase of execution
    - Provide expected execution times for each phase
    - Add monitoring progress instructions
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [ ] 11.2 Document safe shutdown and control
    - Provide command to stop automation (Ctrl+C)
    - Explain graceful shutdown behavior
    - Add note about resuming interrupted runs
    - _Requirements: 10.5_
  
  - [ ] 11.3 Add reference to advanced usage
    - Link to QUICK_START.md for advanced features
    - Mention command-line options
    - Reference additional documentation
    - _Requirements: 10.6, 13.2_

- [ ] 12. Write Windows-specific troubleshooting section
  - [ ] 12.1 Add PATH troubleshooting
    - Provide detailed Windows Settings navigation
    - Show how to verify PATH contents
    - Provide alternative workarounds
    - _Requirements: 11.1_
  
  - [ ] 12.2 Add virtual environment troubleshooting
    - Address CMD vs PowerShell activation differences
    - Provide PowerShell execution policy solutions
    - Address "cannot be loaded" errors
    - Provide venv recreation instructions
    - _Requirements: 11.2_
  
  - [ ] 12.3 Add Ollama service troubleshooting
    - Provide Windows Services app navigation
    - Explain how to restart Ollama service
    - Provide Ollama log file location
    - Address port 11434 conflicts
    - _Requirements: 11.3_
  
  - [ ] 12.4 Add ChromeDriver troubleshooting
    - Address version mismatch errors
    - Provide Chrome update instructions
    - Address WebDriver installation failures
    - Explain Windows Defender exceptions
    - _Requirements: 11.4_
  
  - [ ] 12.5 Add file permission troubleshooting
    - Explain Windows file permissions
    - Provide "Run as Administrator" instructions
    - Address "Access Denied" errors
    - _Requirements: 11.5_
  
  - [ ] 12.6 Add database locking troubleshooting
    - Explain SQLite locking behavior on Windows
    - Provide instructions to close database connections
    - Address concurrent access issues
    - _Requirements: 11.6_
  
  - [ ] 12.7 Add antivirus troubleshooting
    - Explain common antivirus blocking scenarios
    - Provide instructions to add folder exceptions
    - List specific executables to whitelist
    - Address Windows Defender SmartScreen
    - _Requirements: 11.7_
  
  - [ ] 12.8 Add log file access instructions
    - Document log file locations (logs/ directory)
    - Provide commands to view logs (dir, type, notepad)
    - Provide PowerShell command to view last N lines
    - _Requirements: 11.8_

- [ ] 13. Write additional resources section
  - [ ] 13.1 Add project documentation references
    - Link to README.md for system overview
    - Link to QUICK_START.md for usage instructions
    - Link to API_KEYS_CHECKLIST.md for API setup
    - Link to EMAIL_DISCOVERY_API_GUIDE.md for email discovery
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  
  - [ ] 13.2 Add external documentation references
    - Link to Python Windows documentation
    - Link to Ollama Windows installation
    - Link to ChromeDriver documentation
    - Link to Windows environment variables documentation
    - _Requirements: 13.5_
  
  - [ ] 13.3 Add next steps section
    - Provide guidance for first job search
    - Link to usage guides
    - Mention community support resources
    - _Requirements: 13.6_

- [ ] 14. Apply formatting and accessibility improvements
  - [ ] 14.1 Add visual indicators
    - Add emoji/icons for warnings (⚠️)
    - Add emoji/icons for success indicators (✅)
    - Add emoji/icons for errors (❌)
    - Add emoji/icons for tips (💡)
    - _Requirements: 12.5_
  
  - [ ] 14.2 Format code blocks
    - Ensure all commands use proper code blocks
    - Add language hints (cmd, powershell, ini)
    - Verify Windows path syntax (backslashes)
    - Ensure copy-pasteable commands
    - _Requirements: 12.2_
  
  - [ ] 14.3 Apply consistent structure
    - Use numbered lists for sequential steps
    - Use bullet points for non-sequential info
    - Apply clear section headings
    - Ensure consistent heading hierarchy
    - _Requirements: 12.1, 12.3, 12.4_
  
  - [ ] 14.4 Review tone and accessibility
    - Ensure beginner-friendly language
    - Avoid unnecessary jargon
    - Explain technical terms when used
    - Maintain friendly, supportive tone
    - _Requirements: 12.8_

- [ ] 15. Final review and validation
  - Verify all requirements addressed
  - Check all links are valid
  - Verify all commands use Windows syntax
  - Ensure table of contents links work
  - Test guide rendering in GitHub and VS Code
  - Proofread for clarity and consistency

## Notes

- All tasks involve writing documentation in Markdown format
- Each task references specific requirements for traceability
- Commands must use Windows-native syntax (backslashes, .bat/.ps1 extensions)
- Guide should be self-contained and require no external help
- Target completion time for users following guide: 30-45 minutes
- Focus on preventing common Windows installation issues proactively
- Troubleshooting sections should address real user pain points

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1"]
    },
    {
      "id": 1,
      "tasks": ["2.1", "2.2"]
    },
    {
      "id": 2,
      "tasks": ["3.1", "3.2"]
    },
    {
      "id": 3,
      "tasks": ["4.1"]
    },
    {
      "id": 4,
      "tasks": ["4.2", "4.3"]
    },
    {
      "id": 5,
      "tasks": ["5.1", "6.1", "7.1"]
    },
    {
      "id": 6,
      "tasks": ["5.2", "5.3", "6.2", "7.2", "8.1"]
    },
    {
      "id": 7,
      "tasks": ["5.4", "8.2", "9.1"]
    },
    {
      "id": 8,
      "tasks": ["9.2", "9.3", "9.4"]
    },
    {
      "id": 9,
      "tasks": ["10.1", "10.2", "10.3"]
    },
    {
      "id": 10,
      "tasks": ["11.1", "11.2", "11.3"]
    },
    {
      "id": 11,
      "tasks": ["12.1", "12.2", "12.3", "12.4", "12.5", "12.6", "12.7", "12.8"]
    },
    {
      "id": 12,
      "tasks": ["13.1", "13.2", "13.3"]
    },
    {
      "id": 13,
      "tasks": ["14.1", "14.2", "14.3", "14.4"]
    },
    {
      "id": 14,
      "tasks": ["15"]
    }
  ]
}
```
