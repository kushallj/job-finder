"""
Unit tests for comprehensive health check endpoints.

Tests verify that health checks correctly report status for:
- Ollama connectivity and model availability
- Database connectivity and table status
- Email service (SMTP) connectivity
- External API status (GitHub, Cloudflare, Google Sheets)
- Internal service availability
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path
import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the app and models
from main import app, AppState, get_state
from src.models import Base, Job, Application, Contact, OutreachRecord


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    
    # Add some test data
    job = Job(
        job_id="test-job-1",
        title="Software Engineer",
        company="Test Company",
        location="Remote",
        description="Test job description",
        url="https://example.com/job/1",
        source="test",
    )
    session.add(job)
    session.commit()
    
    yield session
    session.close()


@pytest.fixture
def mock_state():
    """Create a mock AppState for testing."""
    state = AppState()
    state.job_processor = Mock()
    state.email_outreach = Mock()
    state.email_outreach.health_check = AsyncMock()
    state.outreach_proc = Mock()
    state.async_pipeline = Mock()
    return state


@pytest.fixture
def client(mock_state):
    """Create a test client with mocked dependencies."""
    app.dependency_overrides[get_state] = lambda: mock_state
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestHealthCheckEndpoint:
    """Test suite for /api/health endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check_all_services_healthy(self, client, mock_state):
        """Test health check when all services are healthy."""
        # Mock Ollama health check
        with patch('src.ai.local_llm_service.LocalLLMService') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.health_check = AsyncMock(return_value=True)
            mock_llm.BASE_URL = "http://localhost:11434"
            mock_llm_class.return_value = mock_llm
            mock_llm_class._cached_model = "qwen2.5-coder:7b"  # Mock class variable
            
            # Mock database session
            with patch('main.db_session') as mock_db_session:
                mock_db = Mock()
                mock_db.execute = Mock()
                mock_db.query = Mock(return_value=Mock(count=Mock(return_value=10)))
                mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
                mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Mock email health check
                mock_email_report = Mock()
                mock_email_report.smtp_ok = True
                mock_email_report.sheets_ok = True
                mock_email_report.resume_ok = True
                mock_email_report.ai_ok = True
                mock_email_report.provider = "smtp"
                mock_email_report.details = {
                    "smtp": "Connected to smtp.gmail.com:587",
                    "sheets": "OK",
                    "resume": "Found",
                    "ai": "OK"
                }
                mock_state.email_outreach.health_check.return_value = mock_email_report
                
                # Mock GitHub API
                with patch('main.httpx.AsyncClient') as mock_http:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "rate": {"remaining": 5000}
                    }
                    mock_client = Mock()
                    mock_client.get = AsyncMock(return_value=mock_response)
                    mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    # Mock settings
                    with patch('main.settings') as mock_settings:
                        mock_settings.github_token = "test-token"
                        mock_settings.cloudflare_account_id = "test-account-id"
                        mock_settings.cloudflare_api_token = "test-api-token"
                        mock_settings.google_sheet_id = "test-sheet-id"
                        mock_settings.google_credentials_path = "/tmp/test-creds.json"
                        
                        # Mock Path.exists for Google credentials
                        with patch('main.Path.exists', return_value=True):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_file = Mock()
                                mock_file.read.return_value = '{"type": "service_account"}'
                                mock_file.__enter__ = Mock(return_value=mock_file)
                                mock_file.__exit__ = Mock(return_value=False)
                                mock_open.return_value = mock_file
                                
                                response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Status can be "healthy" or "healthy_with_warnings" depending on optional services
        assert data["status"] in ["healthy", "healthy_with_warnings"]
        assert "timestamp" in data
        assert "components" in data
        
        # Check Ollama component
        assert data["components"]["ollama"]["status"] == "healthy"
        assert data["components"]["ollama"]["model"] == "qwen2.5-coder:7b"
        
        # Check database component
        assert data["components"]["database"]["status"] == "healthy"
        assert "tables" in data["components"]["database"]
        
        # Check email component
        assert data["components"]["email"]["status"] == "healthy"
        
        # Check GitHub component
        assert data["components"]["github"]["status"] == "healthy"
        
        # Check internal services
        assert data["components"]["internal_services"]["job_processor"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_ollama_unavailable(self, client, mock_state):
        """Test health check when Ollama is not available."""
        with patch('src.ai.local_llm_service.LocalLLMService') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.health_check = AsyncMock(return_value=False)
            mock_llm._cached_model = None
            mock_llm.BASE_URL = "http://localhost:11434"
            mock_llm_class.return_value = mock_llm
            
            # Mock other dependencies to return healthy
            with patch('main.db_session') as mock_db_session:
                mock_db = Mock()
                mock_db.execute = Mock()
                mock_db.query = Mock(return_value=Mock(count=Mock(return_value=10)))
                mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
                mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
                
                mock_email_report = Mock()
                mock_email_report.smtp_ok = True
                mock_email_report.provider = "smtp"
                mock_email_report.details = {"smtp": "OK", "sheets": "OK"}
                mock_state.email_outreach.health_check.return_value = mock_email_report
                
                with patch('main.settings') as mock_settings:
                    mock_settings.github_token = None
                    mock_settings.cloudflare_account_id = None
                    mock_settings.google_sheet_id = None
                    
                    response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Overall status should be degraded
        assert data["status"] == "degraded"
        assert "issues" in data
        assert any("Ollama" in issue for issue in data["issues"])
        
        # Ollama component should show unavailable
        assert data["components"]["ollama"]["status"] == "unavailable"
    
    @pytest.mark.asyncio
    async def test_health_check_database_error(self, client, mock_state):
        """Test health check when database is not available."""
        with patch('src.ai.local_llm_service.LocalLLMService') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.health_check = AsyncMock(return_value=True)
            mock_llm.BASE_URL = "http://localhost:11434"
            mock_llm_class.return_value = mock_llm
            mock_llm_class._cached_model = "qwen2.5-coder:7b"  # Mock class variable
            
            # Mock database to raise an error - use a real exception
            async def mock_db_error():
                raise Exception("Database connection failed")
            
            with patch('main.db_session') as mock_db_session:
                mock_db_session.return_value.__aenter__ = mock_db_error
                mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
                
                mock_email_report = Mock()
                mock_email_report.smtp_ok = True
                mock_email_report.sheets_ok = True
                mock_email_report.resume_ok = True
                mock_email_report.ai_ok = True
                mock_email_report.provider = "smtp"
                mock_email_report.details = {"smtp": "OK", "sheets": "OK", "resume": "OK", "ai": "OK"}
                mock_state.email_outreach.health_check.return_value = mock_email_report
                
                with patch('main.settings') as mock_settings:
                    # Configure mock settings with explicit attributes to avoid circular references
                    mock_settings.github_token = None
                    mock_settings.cloudflare_account_id = None
                    mock_settings.cloudflare_api_token = None
                    mock_settings.google_sheet_id = None
                    mock_settings.google_credentials_path = "/nonexistent"
                    
                    response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert "issues" in data
        assert any("Database" in issue for issue in data["issues"])
        assert data["components"]["database"]["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_health_check_email_unavailable(self, client):
        """Test health check when email service is not initialized."""
        # Create state with no email_outreach
        state = AppState()
        state.job_processor = Mock()
        state.email_outreach = None
        state.outreach_proc = None
        state.async_pipeline = None
        
        app.dependency_overrides[get_state] = lambda: state
        
        try:
            with patch('src.ai.local_llm_service.LocalLLMService') as mock_llm_class:
                mock_llm = Mock()
                mock_llm.health_check = AsyncMock(return_value=True)
                mock_llm.BASE_URL = "http://localhost:11434"
                mock_llm_class.return_value = mock_llm
                mock_llm_class._cached_model = "qwen2.5-coder:7b"  # Mock class variable
                
                with patch('main.db_session') as mock_db_session:
                    mock_db = Mock()
                    mock_db.execute = Mock()
                    mock_db.query = Mock(return_value=Mock(count=Mock(return_value=10)))
                    mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
                    mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    with patch('main.settings') as mock_settings:
                        mock_settings.github_token = None
                        mock_settings.cloudflare_account_id = None
                        mock_settings.cloudflare_api_token = None
                        mock_settings.google_sheet_id = None
                        mock_settings.google_credentials_path = "/nonexistent"
                        
                        response = client.get("/api/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "degraded"
            assert "issues" in data
            assert any("Email" in issue for issue in data["issues"])
            assert data["components"]["email"]["status"] == "unavailable"
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_health_check_github_api_error(self, client, mock_state):
        """Test health check when GitHub API is unreachable."""
        with patch('src.ai.local_llm_service.LocalLLMService') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.health_check = AsyncMock(return_value=True)
            mock_llm.BASE_URL = "http://localhost:11434"
            mock_llm_class.return_value = mock_llm
            mock_llm_class._cached_model = "qwen2.5-coder:7b"  # Mock class variable
            
            with patch('main.db_session') as mock_db_session:
                mock_db = Mock()
                mock_db.execute = Mock()
                mock_db.query = Mock(return_value=Mock(count=Mock(return_value=10)))
                mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
                mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
                
                mock_email_report = Mock()
                mock_email_report.smtp_ok = True
                mock_email_report.sheets_ok = True
                mock_email_report.resume_ok = True
                mock_email_report.ai_ok = True
                mock_email_report.provider = "smtp"
                mock_email_report.details = {"smtp": "OK", "sheets": "OK", "resume": "OK", "ai": "OK"}
                mock_state.email_outreach.health_check.return_value = mock_email_report
                
                # Mock GitHub API to raise an error
                with patch('main.httpx.AsyncClient') as mock_http:
                    mock_client = Mock()
                    mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
                    mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    with patch('main.settings') as mock_settings:
                        mock_settings.github_token = "test-token"
                        mock_settings.cloudflare_account_id = None
                        mock_settings.cloudflare_api_token = None
                        mock_settings.google_sheet_id = None
                        mock_settings.google_credentials_path = "/nonexistent"
                        
                        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["components"]["github"]["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_health_check_services_not_configured(self, client, mock_state):
        """Test health check when external services are not configured."""
        with patch('src.ai.local_llm_service.LocalLLMService') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.health_check = AsyncMock(return_value=True)
            mock_llm.BASE_URL = "http://localhost:11434"
            mock_llm_class.return_value = mock_llm
            mock_llm_class._cached_model = "qwen2.5-coder:7b"  # Mock class variable
            
            with patch('main.db_session') as mock_db_session:
                mock_db = Mock()
                mock_db.execute = Mock()
                mock_db.query = Mock(return_value=Mock(count=Mock(return_value=10)))
                mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
                mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
                
                mock_email_report = Mock()
                mock_email_report.smtp_ok = True
                mock_email_report.sheets_ok = True
                mock_email_report.resume_ok = True
                mock_email_report.ai_ok = True
                mock_email_report.provider = "smtp"
                mock_email_report.details = {"smtp": "OK", "sheets": "OK", "resume": "OK", "ai": "OK"}
                mock_state.email_outreach.health_check.return_value = mock_email_report
                
                # No external services configured
                with patch('main.settings') as mock_settings:
                    mock_settings.github_token = None
                    mock_settings.cloudflare_account_id = None
                    mock_settings.cloudflare_api_token = None
                    mock_settings.google_sheet_id = None
                    mock_settings.google_credentials_path = "/nonexistent"
                    
                    response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have warnings - external services are not configured but are optional
        assert data["status"] in ["healthy", "healthy_with_warnings"]
        if "warnings" in data:
            assert len(data["warnings"]) > 0
        assert data["components"]["github"]["status"] == "not_configured"
        assert data["components"]["cloudflare"]["status"] == "not_configured"
        assert data["components"]["google_sheets"]["status"] == "not_configured"


class TestHealthCheckIntegration:
    """Integration tests for health check endpoint with real services."""
    
    @pytest.mark.integration
    def test_root_endpoint(self, client):
        """Test root health endpoint returns basic status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Job Search API"
        assert "version" in data
    
    @pytest.mark.integration
    async def test_health_check_response_structure(self, client, mock_state):
        """Test that health check response has correct structure."""
        with patch('src.ai.local_llm_service.LocalLLMService') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.health_check = AsyncMock(return_value=True)
            mock_llm._cached_model = "test-model"
            mock_llm.BASE_URL = "http://localhost:11434"
            mock_llm_class.return_value = mock_llm
            
            with patch('main.db_session') as mock_db_session:
                mock_db = Mock()
                mock_db.execute = Mock()
                mock_db.query = Mock(return_value=Mock(count=Mock(return_value=0)))
                mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
                mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
                
                mock_email_report = Mock()
                mock_email_report.smtp_ok = True
                mock_email_report.provider = "smtp"
                mock_email_report.details = {"smtp": "OK", "sheets": "OK"}
                mock_state.email_outreach.health_check.return_value = mock_email_report
                
                with patch('main.settings') as mock_settings:
                    mock_settings.github_token = None
                    mock_settings.cloudflare_account_id = None
                    mock_settings.google_sheet_id = None
                    
                    response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "status" in data
        assert data["status"] in ["healthy", "healthy_with_warnings", "degraded", "unhealthy"]
        assert "timestamp" in data
        assert "version" in data
        assert "components" in data
        
        # Verify component structure
        components = data["components"]
        assert "ollama" in components
        assert "database" in components
        assert "email" in components
        assert "github" in components
        assert "cloudflare" in components
        assert "google_sheets" in components
        assert "internal_services" in components
        
        # Each component should have a status
        for component_name, component in components.items():
            if isinstance(component, dict):
                assert "status" in component or component_name == "internal_services"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
