"""
Integration tests for trace ID functionality across the API.

This module demonstrates end-to-end trace ID functionality by testing
actual API endpoints and verifying trace ID propagation.

Requirements: 23.5, 25.2, 33.1
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_app_state():
    """Mock AppState for testing."""
    from main import AppState
    state = AppState()
    state.job_processor = MagicMock()
    state.resume_router = MagicMock()
    state.resume_router.route.return_value = "data/resume.txt"
    return state


@pytest.fixture
def client(mock_app_state, tmp_path):
    """Create a test client with mocked dependencies."""
    # Create a temporary resume file
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Sample resume content")
    
    # Patch the resume path
    with patch('main.ResumeTrie.DEFAULT', str(resume_path)):
        with patch('main._state', mock_app_state):
            with patch('main.init_db'):
                # Import app after patching
                from main import app
                with TestClient(app) as test_client:
                    yield test_client


class TestTraceIDHeaderPropagation:
    """Test X-Trace-ID header propagation across different endpoints."""
    
    def test_root_endpoint_has_trace_id(self, client):
        """Test that root endpoint returns trace ID in headers."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "X-Trace-ID" in response.headers
        
        # Verify it's a valid UUID
        trace_id = response.headers["X-Trace-ID"]
        uuid.UUID(trace_id)  # Will raise ValueError if invalid
    
    def test_health_endpoint_has_trace_id(self, client):
        """Test that health check endpoint returns trace ID in headers."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        assert "X-Trace-ID" in response.headers
        
        # Verify it's a valid UUID
        trace_id = response.headers["X-Trace-ID"]
        uuid.UUID(trace_id)  # Will raise ValueError if invalid
    
    def test_client_provided_trace_id_preserved(self, client):
        """Test that client-provided trace IDs are preserved."""
        # Generate a custom trace ID
        custom_trace_id = str(uuid.uuid4())
        
        # Send request with custom trace ID
        response = client.get("/", headers={"X-Trace-ID": custom_trace_id})
        
        assert response.status_code == 200
        assert response.headers["X-Trace-ID"] == custom_trace_id
    
    def test_different_requests_get_different_trace_ids(self, client):
        """Test that concurrent requests get different trace IDs."""
        trace_ids = []
        
        # Make multiple requests
        for _ in range(5):
            response = client.get("/")
            assert response.status_code == 200
            trace_ids.append(response.headers["X-Trace-ID"])
        
        # Verify all trace IDs are unique
        assert len(set(trace_ids)) == 5
    
    def test_trace_id_in_404_response(self, client):
        """Test that 404 responses include trace ID."""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        assert "X-Trace-ID" in response.headers


class TestTraceIDLogging:
    """Test that trace IDs appear in log entries."""
    
    @patch('main.log')
    def test_trace_id_logged_on_request_start(self, mock_logger, client):
        """Test that trace ID is logged when request starts."""
        response = client.get("/")
        trace_id = response.headers["X-Trace-ID"]
        
        # Verify log.info was called
        assert mock_logger.info.called
        
        # Check that trace ID appears in at least one log call
        trace_id_in_logs = False
        for call in mock_logger.info.call_args_list:
            log_message = str(call[0])
            if trace_id in log_message and "Request started" in log_message:
                trace_id_in_logs = True
                break
        
        assert trace_id_in_logs, f"Trace ID {trace_id} not found in request start logs"
    
    @patch('main.log')
    def test_trace_id_logged_on_request_completion(self, mock_logger, client):
        """Test that trace ID is logged when request completes."""
        response = client.get("/")
        trace_id = response.headers["X-Trace-ID"]
        
        # Verify log.info was called
        assert mock_logger.info.called
        
        # Check that trace ID appears in completion log
        trace_id_in_logs = False
        for call in mock_logger.info.call_args_list:
            log_message = str(call[0])
            if trace_id in log_message and "Request completed" in log_message:
                trace_id_in_logs = True
                # Also verify duration is logged
                assert "duration" in log_message.lower()
                break
        
        assert trace_id_in_logs, f"Trace ID {trace_id} not found in request completion logs"


class TestRequestMetricsLogging:
    """Test that request metrics are logged with trace IDs."""
    
    @patch('main.log')
    def test_request_duration_logged_with_trace_id(self, mock_logger, client):
        """Test that request duration is logged with trace ID."""
        response = client.get("/")
        trace_id = response.headers["X-Trace-ID"]
        
        # Find the completion log
        duration_logged = False
        for call in mock_logger.info.call_args_list:
            log_message = str(call[0])
            if trace_id in log_message and "duration" in log_message.lower():
                duration_logged = True
                # Verify duration is in milliseconds
                assert "ms" in log_message.lower()
                break
        
        assert duration_logged, "Request duration not logged with trace ID"
    
    @patch('main.log')
    def test_http_status_logged_with_trace_id(self, mock_logger, client):
        """Test that HTTP status code is logged with trace ID."""
        response = client.get("/")
        trace_id = response.headers["X-Trace-ID"]
        
        # Find the completion log with status code
        status_logged = False
        for call in mock_logger.info.call_args_list:
            log_message = str(call[0])
            # Check for status in the log message (may be in different formats)
            if trace_id in log_message and ("status" in log_message.lower() or str(response.status_code) in log_message):
                status_logged = True
                break
        
        assert status_logged, "HTTP status not logged with trace ID"
    
    @patch('main.log')
    def test_request_method_and_path_logged(self, mock_logger, client):
        """Test that request method and path are logged with trace ID."""
        response = client.get("/api/health")
        trace_id = response.headers["X-Trace-ID"]
        
        # Find the log with method and path
        method_path_logged = False
        for call in mock_logger.info.call_args_list:
            log_message = str(call[0])
            if trace_id in log_message and "GET" in log_message and "/api/health" in log_message:
                method_path_logged = True
                break
        
        assert method_path_logged, "Request method and path not logged with trace ID"


class TestDistributedTracing:
    """Test distributed tracing support."""
    
    def test_trace_id_propagation_across_requests(self, client):
        """Test that the same trace ID can be used across multiple requests."""
        # Generate a trace ID for a "transaction"
        transaction_trace_id = str(uuid.uuid4())
        
        # Make multiple requests with the same trace ID
        response1 = client.get("/", headers={"X-Trace-ID": transaction_trace_id})
        response2 = client.get("/api/health", headers={"X-Trace-ID": transaction_trace_id})
        
        # Verify both requests used the same trace ID
        assert response1.headers["X-Trace-ID"] == transaction_trace_id
        assert response2.headers["X-Trace-ID"] == transaction_trace_id
    
    def test_trace_id_format_suitable_for_distributed_tracing(self, client):
        """Test that trace IDs use UUID format suitable for distributed systems."""
        response = client.get("/")
        trace_id = response.headers["X-Trace-ID"]
        
        # Verify it's a valid UUID (standard format for distributed tracing)
        uuid_obj = uuid.UUID(trace_id)
        
        # Verify it's UUID4 (random, suitable for distributed systems)
        assert uuid_obj.version == 4


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
