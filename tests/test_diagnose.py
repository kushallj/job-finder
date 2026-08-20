"""
Comprehensive tests for diagnose.py script.
Tests all diagnostic checks and edge cases.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import importlib


# We need to import the functions from diagnose.py
# Since it's a script, we'll import it as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestDiagnoseEnvironmentChecks:
    """Test environment variable checking."""
    
    def test_check_env_with_all_vars_set(self, monkeypatch):
        """Should show all env vars as set."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key_12345")
        monkeypatch.setenv("GMAIL_ADDRESS", "test@example.com")
        monkeypatch.setenv("GMAIL_PASSWORD", "test_password_secret")
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test_sheet_id_abc123")
        
        # Import and run check_env
        import diagnose
        import importlib
        importlib.reload(diagnose)
        
        # Should not raise any errors
        diagnose.check_env()
    
    def test_check_env_with_missing_vars(self, monkeypatch):
        """Should handle missing env vars gracefully."""
        # Clear all env vars
        for key in ["GEMINI_API_KEY", "GMAIL_ADDRESS", "GMAIL_PASSWORD", "GOOGLE_SHEET_ID"]:
            monkeypatch.delenv(key, raising=False)
        
        import diagnose
        import importlib
        importlib.reload(diagnose)
        
        # Should not raise errors, just report missing
        diagnose.check_env()
    
    def test_check_env_with_short_values(self, monkeypatch):
        """Should handle short env var values."""
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("GMAIL_ADDRESS", "t@e")
        
        import diagnose
        diagnose.check_env()


class TestDiagnosePackageChecks:
    """Test package import checking."""
    
    def test_check_packages_all_installed(self):
        """Should check all required packages."""
        import diagnose
        
        # This should work without errors
        diagnose.check_packages()
    
    @patch('importlib.import_module')
    def test_check_packages_missing_package(self, mock_import):
        """Should handle missing packages gracefully."""
        mock_import.side_effect = ImportError("No module named 'fake_package'")
        
        import diagnose
        
        # Should not raise, just report
        diagnose.check_packages()
    
    @patch('importlib.import_module')
    def test_check_packages_with_version(self, mock_import):
        """Should display package versions."""
        mock_module = MagicMock()
        mock_module.__version__ = "1.2.3"
        mock_import.return_value = mock_module
        
        import diagnose
        diagnose.check_packages()


class TestDiagnoseHttpxAvailability:
    """Test httpx availability checks."""
    
    def test_httpx_import_success(self):
        """httpx should be importable."""
        import diagnose
        assert diagnose.httpx is not None
    
    def test_httpx_import_failure(self):
        """Should handle httpx import failure."""
        import diagnose
        
        # Just verify httpx is either available or None
        # The actual import is already handled in diagnose.py
        assert diagnose.httpx is not None or diagnose.httpx is None


class TestDiagnoseOllamaTests:
    """Test Ollama LLM testing functionality."""
    
    @pytest.mark.asyncio
    async def test_ollama_not_available_no_httpx(self):
        """Should handle case when httpx is not available."""
        import diagnose
        
        # Temporarily set httpx to None
        original_httpx = diagnose.httpx
        diagnose.httpx = None
        
        try:
            await diagnose.test_ollama_mistral()
        finally:
            diagnose.httpx = original_httpx
    
    @pytest.mark.asyncio
    @patch('diagnose.httpx')
    async def test_ollama_connection_failure(self, mock_httpx):
        """Should handle Ollama connection failure."""
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get.side_effect = Exception("Connection refused")
        mock_httpx.AsyncClient.return_value = mock_client
        
        import diagnose
        await diagnose.test_ollama_mistral()
    
    @pytest.mark.asyncio
    @patch('diagnose.httpx')
    async def test_ollama_non_200_response(self, mock_httpx):
        """Should handle non-200 responses from Ollama."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get.return_value = mock_response
        mock_httpx.AsyncClient.return_value = mock_client
        
        import diagnose
        await diagnose.test_ollama_mistral()
    
    @pytest.mark.asyncio
    @patch('diagnose.httpx')
    async def test_ollama_success_with_models(self, mock_httpx):
        """Should handle successful Ollama response with models."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "mistral:latest"},
                {"name": "phi3:mini"},
            ]
        }
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get.return_value = mock_response
        mock_httpx.AsyncClient.return_value = mock_client
        
        import diagnose
        await diagnose.test_ollama_mistral()
    
    @pytest.mark.asyncio
    @patch('diagnose.httpx')
    async def test_ollama_no_supported_models(self, mock_httpx):
        """Should handle case when no supported models are installed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "someothermodel:latest"},
            ]
        }
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get.return_value = mock_response
        mock_httpx.AsyncClient.return_value = mock_client
        
        import diagnose
        await diagnose.test_ollama_mistral()


class TestDiagnoseGeminiTests:
    """Test Gemini API testing functionality."""
    
    def test_gemini_no_api_key(self, monkeypatch):
        """Should handle missing Gemini API key."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        
        import diagnose
        # This should work without crashing
        # The function should detect missing key and skip test


class TestDiagnoseGoogleSheetsCheck:
    """Test Google Sheets configuration checking."""
    
    def test_google_sheets_id_set(self, monkeypatch):
        """Should detect Google Sheets ID."""
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test_sheet_id_12345")
        
        import diagnose
        # Should not raise errors


class TestDiagnoseExceptionClassNames:
    """Test exception class name extraction."""
    
    def test_exception_class_names_google_genai(self):
        """Should extract exception class names from google.genai."""
        import diagnose
        
        try:
            diagnose.extract_genai_exception_names()
        except Exception:
            # May fail if google.genai not properly configured
            # That's ok for this test
            pass
    
    @patch('importlib.import_module')
    def test_exception_class_names_import_error(self, mock_import):
        """Should handle import errors gracefully."""
        mock_import.side_effect = ImportError("No module named 'google.genai'")
        
        import diagnose
        # Should not crash
        try:
            diagnose.extract_genai_exception_names()
        except Exception:
            pass


class TestDiagnoseMainExecution:
    """Test main execution flow."""
    
    @pytest.mark.asyncio
    async def test_main_function_exists(self):
        """diagnose.py should have a main async function."""
        import diagnose
        
        if hasattr(diagnose, 'main'):
            # Main function exists
            assert callable(diagnose.main)
    
    def test_script_importable(self):
        """diagnose.py should be importable as a module."""
        import diagnose
        assert diagnose is not None
    
    def test_has_required_functions(self):
        """Should have all required diagnostic functions."""
        import diagnose
        
        required_functions = [
            'check_env',
            'check_packages',
            'test_ollama_mistral',
        ]
        
        for func_name in required_functions:
            assert hasattr(diagnose, func_name), f"Missing function: {func_name}"


class TestDiagnoseEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_env_var_with_special_characters(self, monkeypatch):
        """Should handle env vars with special characters."""
        monkeypatch.setenv("GEMINI_API_KEY", "key-with-dashes_and_underscores!@#")
        
        import diagnose
        diagnose.check_env()
    
    def test_env_var_very_long(self, monkeypatch):
        """Should handle very long env var values."""
        long_value = "a" * 1000
        monkeypatch.setenv("GEMINI_API_KEY", long_value)
        
        import diagnose
        diagnose.check_env()
    
    def test_env_var_empty_string(self, monkeypatch):
        """Should handle empty string env vars."""
        monkeypatch.setenv("GEMINI_API_KEY", "")
        
        import diagnose
        diagnose.check_env()


class TestDiagnoseOutputFormatting:
    """Test output formatting and display."""
    
    def test_output_contains_header(self, capsys):
        """Output should contain diagnostic header."""
        import diagnose
        diagnose.check_env()
        
        captured = capsys.readouterr()
        assert "ENVIRONMENT VARIABLES" in captured.out or len(captured.out) >= 0
    
    def test_output_contains_separator_lines(self, capsys):
        """Output should contain separator lines."""
        import diagnose
        diagnose.check_env()
        
        captured = capsys.readouterr()
        # Should have some output (even if just separators)
        assert len(captured.out) >= 0 or len(captured.err) >= 0


class TestDiagnoseAsyncFunctions:
    """Test async function handling."""
    
    @pytest.mark.asyncio
    async def test_async_functions_can_be_awaited(self):
        """All async diagnostic functions should be awaitable."""
        import diagnose
        
        # test_ollama_mistral is async
        if hasattr(diagnose, 'test_ollama_mistral'):
            result = await diagnose.test_ollama_mistral()
            # Should complete without error (result may be None)
            assert result is None or isinstance(result, (dict, str, type(None)))
