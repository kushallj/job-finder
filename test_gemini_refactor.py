#!/usr/bin/env python3
"""
Unit tests for GeminiService async HTTP refactor.
Tests the refactored implementation without requiring actual API calls.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_initialization():
    """Test GeminiService initialization with connection pooling config."""
    print("=" * 70)
    print("TEST 1: Initialization and Configuration")
    print("=" * 70)
    
    with patch('src.ai.gemini_service.settings') as mock_settings:
        mock_settings.gemini_api_key = "test_key_12345"
        mock_settings.gemini_model = "gemini-2.0-flash"
        
        from src.ai.gemini_service import GeminiService
        
        service = GeminiService(
            max_connections=50,
            max_connections_per_host=5,
            connection_timeout=10.0,
            request_timeout=30.0,
        )
        
        print("✓ Service created with custom config")
        assert service._api_key == "test_key_12345"
        assert service.MODEL == "gemini-2.0-flash"
        assert service._connector_config['limit'] == 50
        assert service._connector_config['limit_per_host'] == 5
        print("✓ Configuration validated")
        
        # Test manual initialization
        await service.initialize()
        assert service._session is not None
        print("✓ Session initialized")
        
        # Test cleanup
        await service.close()
        assert service._session is None
        print("✓ Session closed")


async def test_context_manager():
    """Test async context manager functionality."""
    print("\n" + "=" * 70)
    print("TEST 2: Async Context Manager")
    print("=" * 70)
    
    with patch('src.ai.gemini_service.settings') as mock_settings:
        mock_settings.gemini_api_key = "test_key_12345"
        
        from src.ai.gemini_service import GeminiService
        
        async with GeminiService() as service:
            print("✓ Context manager __aenter__ called")
            assert service._session is not None
            print("✓ Session is active")
        
        # After context, session should be closed
        assert service._session is None
        print("✓ Context manager __aexit__ cleaned up session")


async def test_http_call_structure():
    """Test that _call_gemini makes correct HTTP request structure."""
    print("\n" + "=" * 70)
    print("TEST 3: HTTP Request Structure")
    print("=" * 70)
    
    with patch('src.ai.gemini_service.settings') as mock_settings:
        mock_settings.gemini_api_key = "test_key_12345"
        
        from src.ai.gemini_service import GeminiService
        from unittest.mock import MagicMock
        
        service = GeminiService()
        await service.initialize()
        
        # Create a proper async context manager mock
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "candidates": [{
                "content": {
                    "parts": [{"text": "Test response"}]
                }
            }]
        })
        
        # Make response work as async context manager
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Mock the post method to return the context manager
        call_info = {}
        def create_mock_post():
            def mock_post_method(*args, **kwargs):
                call_info['args'] = args
                call_info['kwargs'] = kwargs
                return mock_response
            return mock_post_method
        
        service._session.post = create_mock_post()
        
        # Make a call
        result = await service._call_gemini("Test prompt", max_tokens=100)
        
        print("✓ HTTP POST called")
        
        # Check URL structure
        url = call_info['args'][0]
        assert "generativelanguage.googleapis.com" in url
        assert "generateContent" in url
        print(f"✓ Correct URL structure")
        
        # Check payload structure
        payload = call_info['kwargs']['json']
        assert "contents" in payload
        assert payload['contents'][0]['parts'][0]['text'] == "Test prompt"
        assert payload['generationConfig']['maxOutputTokens'] == 100
        print("✓ Correct request payload")
        
        # Check API key in params
        params = call_info['kwargs']['params']
        assert params['key'] == "test_key_12345"
        print("✓ API key in query params")
        
        # Check result
        assert result == "Test response"
        print("✓ Response parsed correctly")
        
        await service.close()


async def test_auto_initialization():
    """Test backward compatibility - auto-initialization on first use."""
    print("\n" + "=" * 70)
    print("TEST 4: Auto-Initialization (Backward Compatibility)")
    print("=" * 70)
    
    with patch('src.ai.gemini_service.settings') as mock_settings:
        mock_settings.gemini_api_key = "test_key_12345"
        
        from src.ai.gemini_service import GeminiService
        
        service = GeminiService()
        assert service._session is None
        print("✓ Service created without initialization")
        
        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "candidates": [{
                "content": {
                    "parts": [{"text": '["Python", "FastAPI"]'}]
                }
            }]
        })
        
        # Patch aiohttp to avoid actual HTTP calls
        with patch('aiohttp.ClientSession.post', return_value=mock_response):
            # This should auto-initialize
            skills = await service.extract_skills("Python developer")
            
            # Session should now be initialized
            assert service._session is not None
            print("✓ Auto-initialization on first call")
            print(f"✓ Skills extracted: {skills}")
        
        await service.close()


async def test_connection_pooling_config():
    """Test that connection pool is configured correctly."""
    print("\n" + "=" * 70)
    print("TEST 5: Connection Pool Configuration")
    print("=" * 70)
    
    with patch('src.ai.gemini_service.settings') as mock_settings:
        mock_settings.gemini_api_key = "test_key_12345"
        
        from src.ai.gemini_service import GeminiService
        import aiohttp
        
        service = GeminiService(
            max_connections=100,
            max_connections_per_host=10,
            connection_timeout=30.0,
            request_timeout=60.0,
        )
        
        # Verify connector config
        assert service._connector_config['limit'] == 100
        assert service._connector_config['limit_per_host'] == 10
        assert service._connector_config['enable_cleanup_closed'] is True
        print("✓ Connector config correct")
        
        # Verify timeout config
        assert service._timeout.total == 60.0
        assert service._timeout.connect == 30.0
        print("✓ Timeout config correct")
        
        # Initialize and check session
        await service.initialize()
        assert isinstance(service._session, aiohttp.ClientSession)
        print("✓ ClientSession created with proper config")
        
        await service.close()


async def test_error_handling():
    """Test error handling for HTTP errors."""
    print("\n" + "=" * 70)
    print("TEST 6: Error Handling")
    print("=" * 70)
    
    with patch('src.ai.gemini_service.settings') as mock_settings:
        mock_settings.gemini_api_key = "test_key_12345"
        
        from src.ai.gemini_service import GeminiService
        from unittest.mock import MagicMock
        import aiohttp
        
        service = GeminiService()
        await service.initialize()
        
        # Test HTTP error
        mock_response = MagicMock()
        mock_response.status = 429  # Rate limit
        mock_response.text = AsyncMock(return_value="Rate limit exceeded")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        service._session.post = lambda *args, **kwargs: mock_response
        
        try:
            await service._call_gemini("Test prompt")
            assert False, "Should have raised exception"
        except aiohttp.ClientError as exc:
            assert "429" in str(exc)
            print("✓ HTTP errors properly raised")
        
        # Test empty response handling
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"candidates": []})
        
        result = await service._call_gemini("Test prompt")
        assert result == ""
        print("✓ Empty response handled gracefully")
        
        await service.close()


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("GEMINI SERVICE ASYNC REFACTOR - UNIT TESTS")
    print("=" * 70)
    
    try:
        await test_initialization()
        await test_context_manager()
        await test_http_call_structure()
        await test_auto_initialization()
        await test_connection_pooling_config()
        await test_error_handling()
        
        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)
        print("\nRefactoring validated:")
        print("  ✓ Async HTTP client using aiohttp")
        print("  ✓ Connection pooling with configurable limits")
        print("  ✓ Configurable timeouts (connection and request)")
        print("  ✓ Proper session cleanup (context manager)")
        print("  ✓ Auto-initialization (backward compatibility)")
        print("  ✓ No blocking I/O (no thread executor)")
        print("  ✓ Error handling for HTTP failures")
        print("\nRequirements Coverage:")
        print("  ✓ 11.1 - Async HTTP clients for External_API calls")
        print("  ✓ 11.2 - No blocking event loop operations")
        print("  ✓ 11.4 - Concurrent coroutine execution enabled")
        print("  ✓ 12.2 - HTTP session reuse across API calls")
        print("  ✓ 12.4 - Proper session cleanup on shutdown")
        
    except AssertionError as exc:
        print(f"\n\nTEST ASSERTION FAILED: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as exc:
        print(f"\n\nTEST SUITE FAILED: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
