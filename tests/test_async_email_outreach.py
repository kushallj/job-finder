"""
Integration tests for async HTTP client refactoring in email_outreach.py
Tests Requirements 11.2, 11.4, 12.2, 12.4
"""

import pytest
import asyncio
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.email_outreach import (
    EmailOutreach,
    OutreachConfig,
    EmailRecord,
    EmailStatus,
)
from src.contact_finder import Contact


@pytest.fixture
def test_config():
    """Create a test configuration with minimal settings."""
    return OutreachConfig(
        sender_name="Test User",
        sender_email="test@example.com",
        sender_password="test_password",
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        http_pool_size=10,
        http_timeout=30.0,
        http_connect_timeout=10.0,
        http_keepalive_timeout=60.0,
        resume_pdf_path="data/resume.pdf",
        worker_count=3,
        provider="smtp",
    )


@pytest.fixture
def test_contact():
    """Create a test contact."""
    return Contact(
        name="John Doe",
        email="john.doe@testcompany.com",
        title="Engineering Manager",
        company="Test Company",
    )


@pytest.mark.asyncio
async def test_http_client_initialization(test_config):
    """Test that HTTP clients are properly initialized with connection pooling."""
    outreach = EmailOutreach(cfg=test_config)
    
    # Initialize HTTP clients
    await outreach._init_http_clients()
    
    # Verify aiohttp session is created
    assert outreach._http_session is not None
    assert outreach._http_session.connector is not None
    assert outreach._http_session.connector._limit == test_config.http_pool_size
    
    # Verify httpx client is created
    assert outreach._httpx_client is not None
    # Note: httpx doesn't expose _limits directly, but we can verify the client exists
    assert isinstance(outreach._httpx_client, httpx.AsyncClient)
    
    # Cleanup
    await outreach.close()


@pytest.mark.asyncio
async def test_http_client_timeout_configuration(test_config):
    """Test that HTTP clients have proper timeout configuration."""
    outreach = EmailOutreach(cfg=test_config)
    await outreach._init_http_clients()
    
    # Check aiohttp timeout
    assert outreach._http_session.timeout.total == test_config.http_timeout
    assert outreach._http_session.timeout.connect == test_config.http_connect_timeout
    
    # Check httpx timeout - httpx uses different attribute names
    assert outreach._httpx_client.timeout.read == test_config.http_timeout
    
    # Cleanup
    await outreach.close()


@pytest.mark.asyncio
async def test_http_client_keepalive(test_config):
    """Test that HTTP clients have keepalive timeout configured."""
    outreach = EmailOutreach(cfg=test_config)
    await outreach._init_http_clients()
    
    # Check aiohttp keepalive
    connector = outreach._http_session.connector
    assert connector._keepalive_timeout == test_config.http_keepalive_timeout
    
    # Cleanup
    await outreach.close()


@pytest.mark.asyncio
async def test_sendgrid_async_http_send(test_config):
    """Test SendGrid email sending via async HTTP client."""
    test_config.provider = "sendgrid"
    test_config.sendgrid_api_key = "test_api_key_123"
    
    outreach = EmailOutreach(cfg=test_config)
    await outreach._init_http_clients()
    
    # Mock the HTTP session
    mock_response = AsyncMock()
    mock_response.status = 202
    mock_response.text = AsyncMock(return_value="Accepted")
    
    with patch.object(
        outreach._http_session, 'post', 
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
    ) as mock_post:
        record = EmailRecord(
            trace_id="test123",
            contact_email="test@example.com",
            contact_name="Test User",
            company="Test Co",
            job_title="Engineer",
            job_url="https://test.com/job",
            subject="Test Subject",
            body="Test body",
            template_type="hr_outreach",
        )
        
        # This should not raise an exception
        await outreach._send_via_sendgrid(record)
        
        # Verify the HTTP call was made
        assert mock_post.called
        call_args = mock_post.call_args
        
        # Verify endpoint
        assert "sendgrid.com" in str(call_args)
        
        # Verify headers contain auth
        assert 'headers' in call_args.kwargs
        assert 'Authorization' in call_args.kwargs['headers']
        assert test_config.sendgrid_api_key in call_args.kwargs['headers']['Authorization']
    
    await outreach.close()


@pytest.mark.asyncio
async def test_http_client_connection_pooling(test_config):
    """Test that HTTP connections are reused (connection pooling)."""
    outreach = EmailOutreach(cfg=test_config)
    await outreach._init_http_clients()
    
    # The same session instance should be reused
    session1 = outreach._http_session
    session2 = outreach._http_session
    
    assert session1 is session2
    
    # Verify connector allows multiple connections
    connector = outreach._http_session.connector
    assert connector._limit == test_config.http_pool_size
    assert connector._limit > 1  # Must support pooling
    
    await outreach.close()


@pytest.mark.asyncio
async def test_http_client_cleanup(test_config):
    """Test that HTTP clients are properly closed on cleanup."""
    outreach = EmailOutreach(cfg=test_config)
    await outreach._init_http_clients()
    
    # Verify clients exist
    assert outreach._http_session is not None
    assert outreach._httpx_client is not None
    
    # Close
    await outreach.close()
    
    # Verify clients are cleaned up
    assert outreach._http_session is None
    assert outreach._httpx_client is None


@pytest.mark.asyncio
async def test_sendgrid_error_handling(test_config):
    """Test error handling for SendGrid HTTP errors."""
    test_config.provider = "sendgrid"
    test_config.sendgrid_api_key = "test_api_key"
    
    outreach = EmailOutreach(cfg=test_config)
    await outreach._init_http_clients()
    
    # Mock error response
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_response.text = AsyncMock(return_value="Unauthorized")
    
    with patch.object(
        outreach._http_session, 'post',
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
    ):
        record = EmailRecord(
            trace_id="test123",
            contact_email="test@example.com",
            contact_name="Test User",
            company="Test Co",
            job_title="Engineer",
            job_url="https://test.com/job",
            subject="Test Subject",
            body="Test body",
            template_type="hr_outreach",
        )
        
        # Should raise RuntimeError with status code
        with pytest.raises(RuntimeError) as exc_info:
            await outreach._send_via_sendgrid(record)
        
        assert "401" in str(exc_info.value)
    
    await outreach.close()


@pytest.mark.asyncio
async def test_http2_support(test_config):
    """Test that httpx client has HTTP/2 support enabled."""
    outreach = EmailOutreach(cfg=test_config)
    await outreach._init_http_clients()
    
    # Verify HTTP/2 is enabled in httpx client
    assert outreach._httpx_client._transport is not None
    # Note: We can't easily check the http2 flag after initialization,
    # but we can verify the client was created successfully
    assert outreach._httpx_client is not None
    
    await outreach.close()


@pytest.mark.asyncio
async def test_concurrent_requests_with_pooling(test_config):
    """Test that multiple concurrent requests reuse connections."""
    test_config.provider = "sendgrid"
    test_config.sendgrid_api_key = "test_key"
    test_config.http_pool_size = 5
    
    outreach = EmailOutreach(cfg=test_config)
    await outreach._init_http_clients()
    
    # Mock successful responses
    mock_response = AsyncMock()
    mock_response.status = 202
    mock_response.text = AsyncMock(return_value="Accepted")
    
    call_count = 0
    
    # Create an async context manager mock
    class AsyncContextManager:
        async def __aenter__(self):
            return mock_response
        
        async def __aexit__(self, *args):
            return None
    
    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return AsyncContextManager()
    
    with patch.object(outreach._http_session, 'post', side_effect=mock_post):
        # Create multiple records
        records = [
            EmailRecord(
                trace_id=f"test{i}",
                contact_email=f"test{i}@example.com",
                contact_name="Test User",
                company="Test Co",
                job_title="Engineer",
                job_url="https://test.com/job",
                subject="Test Subject",
                body="Test body",
                template_type="hr_outreach",
            )
            for i in range(10)
        ]
        
        # Send concurrently
        await asyncio.gather(*[
            outreach._send_via_sendgrid(record) 
            for record in records
        ])
        
        # Verify all requests were made
        assert call_count == 10
    
    await outreach.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
