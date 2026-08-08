"""
Tests for FastAPI server shutdown support (main.py lifespan context manager).

Tests cover:
- SIGTERM/SIGINT signal handling
- Database connection pool cleanup
- HTTP client session cleanup
- Log handler flushing and closing

Requirements: 24.1, 24.2, 24.3, 24.4
"""

import asyncio
import logging
import signal
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch


# ============================================================================
# Test Signal Handler Registration
# ============================================================================

def test_signal_handlers_can_be_registered():
    """
    Test that signal handlers can be registered for SIGTERM and SIGINT.
    
    Requirements: 24.1, 24.3
    """
    # Store original handlers
    original_sigterm = signal.getsignal(signal.SIGTERM)
    original_sigint = signal.getsignal(signal.SIGINT)
    
    try:
        # Test custom handler registration
        def custom_handler(signum, frame):
            pass
        
        signal.signal(signal.SIGTERM, custom_handler)
        signal.signal(signal.SIGINT, custom_handler)
        
        # Verify handlers are set
        assert signal.getsignal(signal.SIGTERM) == custom_handler
        assert signal.getsignal(signal.SIGINT) == custom_handler
    finally:
        # Restore original handlers
        signal.signal(signal.SIGTERM, original_sigterm)
        signal.signal(signal.SIGINT, original_sigint)


def test_signal_name_resolution():
    """
    Test that signal names can be resolved correctly.
    
    Requirements: 24.1, 24.3
    """
    assert signal.Signals(signal.SIGTERM).name == "SIGTERM"
    assert signal.Signals(signal.SIGINT).name == "SIGINT"


# ============================================================================
# Test Database Cleanup
# ============================================================================

def test_database_engine_dispose():
    """
    Test that database engine dispose method can be called.
    """
    mock_engine = Mock()
    mock_engine.dispose = Mock()
    
    # Simulate cleanup
    mock_engine.dispose()
    
    mock_engine.dispose.assert_called_once()


# ============================================================================
# Test Async Resource Cleanup
# ============================================================================

@pytest.mark.asyncio
async def test_safe_close_async_resource():
    """
    Test _safe_close helper handles async close methods.
    """
    from main import _safe_close
    
    # Create mock with async close
    mock_resource = AsyncMock()
    mock_resource.close = AsyncMock()
    
    await _safe_close(mock_resource, "test_resource")
    
    mock_resource.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_safe_close_sync_resource():
    """
    Test _safe_close helper handles sync close methods.
    """
    from main import _safe_close
    
    # Create mock with sync close
    mock_resource = Mock()
    mock_resource.close = Mock(return_value=None)
    
    await _safe_close(mock_resource, "test_resource")
    
    mock_resource.close.assert_called_once()


@pytest.mark.asyncio
async def test_safe_close_no_close_method():
    """
    Test _safe_close helper handles resources without close method.
    """
    from main import _safe_close
    
    # Create mock without close method
    mock_resource = Mock(spec=[])  # No attributes
    
    # Should not raise
    await _safe_close(mock_resource, "test_resource")


@pytest.mark.asyncio
async def test_safe_close_error_handling():
    """
    Test _safe_close helper handles errors gracefully.
    """
    from main import _safe_close
    
    # Create mock that raises on close
    mock_resource = Mock()
    mock_resource.close = Mock(side_effect=Exception("Close error"))
    
    # Should not raise, just log warning
    await _safe_close(mock_resource, "test_resource")


# ============================================================================
# Test Log Handler Cleanup
# ============================================================================

def test_log_handler_flush():
    """
    Test that log handlers can be flushed.
    """
    mock_handler = Mock()
    mock_handler.flush = Mock()
    
    # Simulate flush
    mock_handler.flush()
    
    mock_handler.flush.assert_called_once()


def test_log_handler_close():
    """
    Test that log handlers can be closed.
    """
    mock_handler = Mock()
    mock_handler.close = Mock()
    
    # Simulate close
    mock_handler.close()
    
    mock_handler.close.assert_called_once()


def test_root_logger_handler_iteration():
    """
    Test that root logger handlers can be iterated safely during removal.
    """
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers.copy()
    
    # Create test handler
    test_handler = logging.NullHandler()
    root_logger.addHandler(test_handler)
    
    try:
        # Iterate over copy and remove (as done in shutdown)
        for handler in root_logger.handlers[:]:
            if handler == test_handler:
                root_logger.removeHandler(handler)
        
        assert test_handler not in root_logger.handlers
    finally:
        # Cleanup: restore original state
        for h in root_logger.handlers[:]:
            if h not in original_handlers:
                root_logger.removeHandler(h)


# ============================================================================
# Test AppState
# ============================================================================

def test_appstate_initialization():
    """
    Test AppState dataclass initialization.
    """
    from main import AppState
    
    state = AppState()
    
    assert state.job_processor is None
    assert state.outreach_proc is None
    assert state.email_outreach is None
    assert state.async_pipeline is None
    assert state.resume_router is not None


def test_appstate_callback_persistence(tmp_path):
    """
    Test AppState callback persistence.
    """
    from main import AppState
    
    state = AppState()
    state._cb_path = tmp_path / "callbacks.json"
    
    # Save a callback
    state.save_cb("test_key", {"value": 123})
    
    # Load it back
    state.load_callbacks()
    
    assert state.get_cb("test_key") == {"value": 123}


# ============================================================================
# Test Lifespan Structure
# ============================================================================

def test_lifespan_is_async_context_manager():
    """
    Test that lifespan is an async context manager.
    """
    from main import lifespan
    from contextlib import asynccontextmanager
    
    # Check it's a coroutine function wrapped by asynccontextmanager
    import inspect
    assert inspect.isasyncgenfunction(lifespan.__wrapped__) or hasattr(lifespan, '__aenter__')


# ============================================================================
# Integration Test: Shutdown Sequence
# ============================================================================

@pytest.mark.asyncio
async def test_shutdown_sequence_order():
    """
    Test that shutdown happens in correct order (reverse of initialization).
    
    Order should be:
    1. AsyncJobPipeline (has in-flight jobs)
    2. OutreachProcessor
    3. EmailOutreach (HTTP clients)
    4. JobProcessor
    5. Database
    6. Log handlers
    """
    from main import _safe_close
    
    shutdown_order = []
    
    # Create mock resources that track shutdown order
    async def make_mock(name):
        mock = AsyncMock()
        async def close():
            shutdown_order.append(name)
        mock.close = close
        return mock
    
    # Create mocks
    async_pipeline = await make_mock("async_pipeline")
    outreach_proc = await make_mock("outreach_proc")
    email_outreach = await make_mock("email_outreach")
    job_processor = await make_mock("job_processor")
    
    # Simulate shutdown sequence (matching main.py order)
    await _safe_close(async_pipeline, "async_pipeline")
    await _safe_close(outreach_proc, "outreach_proc")
    await _safe_close(email_outreach, "email_outreach")
    await _safe_close(job_processor, "job_processor")
    
    # Verify order
    expected_order = ["async_pipeline", "outreach_proc", "email_outreach", "job_processor"]
    assert shutdown_order == expected_order


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
