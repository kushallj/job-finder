"""
Tests for API request validation and error handling.

This module tests Pydantic request models, validation logic, and error responses.

Requirements: 23.2 (Validate request parameters, comprehensive error responses)
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.api_models import (
    QueryRequest,
    ContactSearchRequest,
    OutreachRequest,
    FollowUpRequest,
    CrawlRequest,
    ErrorResponse,
    PipelineStatistics,
    # Query parameter models
    PaginationParams,
    JobsQueryParams,
    ContactsQueryParams,
    PendingOutreachParams,
    # Response models
    StatsResponse,
    StatsData,
    RecentOutreach,
    PendingOutreachResponse,
    PendingOutreachJob,
    SignalHireCallbackResponse,
    SignalHireResultResponse,
    TimeoutErrorResponse,
    RateLimitErrorResponse,
)


class TestQueryRequest:
    """Test QueryRequest validation"""
    
    def test_valid_query_request(self):
        """Test valid query request with all fields"""
        request = QueryRequest(
            query="python developer",
            min_score=70,
            location="Remote",
        )
        assert request.query == "python developer"
        assert request.min_score == 70
        assert request.location == "Remote"
    
    def test_query_request_defaults(self):
        """Test query request with default values"""
        request = QueryRequest(query="software engineer")
        assert request.query == "software engineer"
        assert request.min_score == 50  # Default
        assert request.source is None
    
    def test_query_empty_string_validation(self):
        """Test that empty query strings are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(query="")
        
        errors = exc_info.value.errors()
        assert any("query" in str(err["loc"]) for err in errors)
    
    def test_query_whitespace_only_validation(self):
        """Test that whitespace-only queries are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(query="   ")
        
        errors = exc_info.value.errors()
        assert any("query" in str(err["loc"]) for err in errors)
    
    def test_min_score_range_validation(self):
        """Test min_score must be 0-100"""
        # Valid boundary values
        QueryRequest(query="test", min_score=0)
        QueryRequest(query="test", min_score=100)
        
        # Invalid values
        with pytest.raises(ValidationError):
            QueryRequest(query="test", min_score=-1)
        
        with pytest.raises(ValidationError):
            QueryRequest(query="test", min_score=101)
    
    def test_timeout_validation(self):
        """Test timeout_seconds validation"""
        # Valid timeout
        request = QueryRequest(query="test", timeout_seconds=120)
        assert request.timeout_seconds == 120
        
        # Too small
        with pytest.raises(ValidationError):
            QueryRequest(query="test", timeout_seconds=5)
        
        # Too large
        with pytest.raises(ValidationError):
            QueryRequest(query="test", timeout_seconds=4000)


class TestContactSearchRequest:
    """Test ContactSearchRequest validation"""
    
    def test_valid_contact_search(self):
        """Test valid contact search request"""
        request = ContactSearchRequest(
            company_name="Stripe",
            job_title="Engineering Manager",
            limit=20,
        )
        assert request.company_name == "Stripe"
        assert request.job_title == "Engineering Manager"
        assert request.limit == 20
    
    def test_contact_search_defaults(self):
        """Test contact search with default values"""
        request = ContactSearchRequest(company_name="OpenAI")
        assert request.company_name == "OpenAI"
        assert request.job_title is None
        assert request.limit == 10
        assert request.smtp_verify is False
    
    def test_company_name_empty_validation(self):
        """Test that empty company name is rejected"""
        with pytest.raises(ValidationError):
            ContactSearchRequest(company_name="")
    
    def test_limit_range_validation(self):
        """Test limit must be 1-50"""
        # Valid boundary values
        ContactSearchRequest(company_name="Test", limit=1)
        ContactSearchRequest(company_name="Test", limit=50)
        
        # Invalid values
        with pytest.raises(ValidationError):
            ContactSearchRequest(company_name="Test", limit=0)
        
        with pytest.raises(ValidationError):
            ContactSearchRequest(company_name="Test", limit=51)


class TestOutreachRequest:
    """Test OutreachRequest validation"""
    
    def test_valid_outreach_request(self):
        """Test valid outreach request"""
        request = OutreachRequest(
            job_id=123,
            contact_email="hiring@company.com",
            contact_name="Jane Smith",
            send_immediately=True,
        )
        assert request.job_id == 123
        assert request.contact_email == "hiring@company.com"
        assert request.contact_name == "Jane Smith"
        assert request.send_immediately is True
    
    def test_email_validation(self):
        """Test email format validation"""
        # Valid emails
        OutreachRequest(
            job_id=1,
            contact_email="test@example.com",
            contact_name="Test",
        )
        
        # Invalid emails
        with pytest.raises(ValidationError):
            OutreachRequest(
                job_id=1,
                contact_email="invalid-email",
                contact_name="Test",
            )
        
        with pytest.raises(ValidationError):
            OutreachRequest(
                job_id=1,
                contact_email="no-at-sign.com",
                contact_name="Test",
            )
    
    def test_email_normalization(self):
        """Test that emails are normalized to lowercase"""
        request = OutreachRequest(
            job_id=1,
            contact_email="Test@Example.COM",
            contact_name="Test",
        )
        assert request.contact_email == "test@example.com"
    
    def test_contact_name_validation(self):
        """Test contact name validation"""
        # Valid name
        OutreachRequest(
            job_id=1,
            contact_email="test@example.com",
            contact_name="John Doe",
        )
        
        # Empty name
        with pytest.raises(ValidationError):
            OutreachRequest(
                job_id=1,
                contact_email="test@example.com",
                contact_name="",
            )
    
    def test_job_id_validation(self):
        """Test job_id must be positive"""
        # Valid job_id
        OutreachRequest(
            job_id=1,
            contact_email="test@example.com",
            contact_name="Test",
        )
        
        # Invalid job_id
        with pytest.raises(ValidationError):
            OutreachRequest(
                job_id=0,
                contact_email="test@example.com",
                contact_name="Test",
            )


class TestFollowUpRequest:
    """Test FollowUpRequest validation"""
    
    def test_valid_follow_up_request(self):
        """Test valid follow-up request"""
        request = FollowUpRequest(
            outreach_id=456,
            follow_up_number=2,
        )
        assert request.outreach_id == 456
        assert request.follow_up_number == 2
    
    def test_follow_up_defaults(self):
        """Test follow-up request with defaults"""
        request = FollowUpRequest(outreach_id=123)
        assert request.outreach_id == 123
        assert request.follow_up_number == 1
    
    def test_follow_up_number_range(self):
        """Test follow_up_number must be 1-3"""
        # Valid values
        FollowUpRequest(outreach_id=1, follow_up_number=1)
        FollowUpRequest(outreach_id=1, follow_up_number=3)
        
        # Invalid values
        with pytest.raises(ValidationError):
            FollowUpRequest(outreach_id=1, follow_up_number=0)
        
        with pytest.raises(ValidationError):
            FollowUpRequest(outreach_id=1, follow_up_number=4)


class TestCrawlRequest:
    """Test CrawlRequest validation"""
    
    def test_valid_crawl_request(self):
        """Test valid crawl request"""
        request = CrawlRequest(
            url="https://stripe.com/jobs",
            company_name="Stripe",
            limit=100,
            depth=3,
        )
        assert request.url == "https://stripe.com/jobs"
        assert request.company_name == "Stripe"
        assert request.limit == 100
        assert request.depth == 3
    
    def test_url_https_validation(self):
        """Test that URL must be HTTPS"""
        # Valid HTTPS URL
        CrawlRequest(url="https://example.com/careers")
        
        # Invalid HTTP URL
        with pytest.raises(ValidationError):
            CrawlRequest(url="http://example.com/careers")
        
        # Invalid non-URL
        with pytest.raises(ValidationError):
            CrawlRequest(url="not-a-url")
    
    def test_limit_range_validation(self):
        """Test limit must be 1-500"""
        CrawlRequest(url="https://example.com", limit=1)
        CrawlRequest(url="https://example.com", limit=500)
        
        with pytest.raises(ValidationError):
            CrawlRequest(url="https://example.com", limit=0)
        
        with pytest.raises(ValidationError):
            CrawlRequest(url="https://example.com", limit=501)
    
    def test_depth_range_validation(self):
        """Test depth must be 1-5"""
        CrawlRequest(url="https://example.com", depth=1)
        CrawlRequest(url="https://example.com", depth=5)
        
        with pytest.raises(ValidationError):
            CrawlRequest(url="https://example.com", depth=0)
        
        with pytest.raises(ValidationError):
            CrawlRequest(url="https://example.com", depth=6)


class TestPipelineStatistics:
    """Test PipelineStatistics model"""
    
    def test_valid_statistics(self):
        """Test valid pipeline statistics"""
        stats = PipelineStatistics(
            jobs_fetched=100,
            jobs_processed=100,
            jobs_completed=95,
            jobs_failed=5,
            processing_time_seconds=45.2,
            throughput_jobs_per_second=2.21,
        )
        assert stats.jobs_fetched == 100
        assert stats.jobs_completed == 95
        assert stats.jobs_failed == 5
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        stats = PipelineStatistics(
            jobs_fetched=100,
            jobs_processed=100,
            jobs_completed=80,
            jobs_failed=20,
            processing_time_seconds=60.0,
            throughput_jobs_per_second=1.67,
        )
        assert stats.success_rate == 80.0
    
    def test_success_rate_with_zero_processed(self):
        """Test success rate when no jobs processed"""
        stats = PipelineStatistics(
            jobs_fetched=0,
            jobs_processed=0,
            jobs_completed=0,
            jobs_failed=0,
            processing_time_seconds=0.0,
            throughput_jobs_per_second=0.0,
        )
        assert stats.success_rate == 0.0


class TestErrorResponse:
    """Test ErrorResponse model"""
    
    def test_valid_error_response(self):
        """Test valid error response"""
        error = ErrorResponse(
            error="ValidationError",
            message="Request validation failed",
            trace_id="abc-123",
        )
        assert error.status == "error"
        assert error.error == "ValidationError"
        assert error.message == "Request validation failed"
        assert error.trace_id == "abc-123"
        assert error.details is None
    
    def test_error_response_with_details(self):
        """Test error response with detailed errors"""
        from src.api_models import ErrorDetail
        
        error = ErrorResponse(
            error="ValidationError",
            message="Validation failed",
            details=[
                ErrorDetail(
                    field="min_score",
                    message="Must be between 0 and 100",
                    type="value_error",
                ),
            ],
        )
        assert len(error.details) == 1
        assert error.details[0].field == "min_score"



class TestPaginationParams:
    """Test PaginationParams validation - Requirements: 23.2"""
    
    def test_valid_pagination_params(self):
        """Test valid pagination parameters"""
        params = PaginationParams(page=5, limit=100)
        assert params.page == 5
        assert params.limit == 100
    
    def test_pagination_defaults(self):
        """Test pagination with default values"""
        params = PaginationParams()
        assert params.page == 1
        assert params.limit == 50
    
    def test_page_range_validation(self):
        """Test page must be 1-10000"""
        # Valid boundary values
        PaginationParams(page=1)
        PaginationParams(page=10000)
        
        # Invalid values
        with pytest.raises(ValidationError):
            PaginationParams(page=0)
        
        with pytest.raises(ValidationError):
            PaginationParams(page=10001)
    
    def test_limit_range_validation(self):
        """Test limit must be 1-500"""
        # Valid boundary values
        PaginationParams(limit=1)
        PaginationParams(limit=500)
        
        # Invalid values
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)
        
        with pytest.raises(ValidationError):
            PaginationParams(limit=501)


class TestJobsQueryParams:
    """Test JobsQueryParams validation - Requirements: 23.2"""
    
    def test_valid_jobs_query_params(self):
        """Test valid jobs query parameters"""
        from src.api_models import JobSource
        params = JobsQueryParams(
            page=1,
            limit=25,
            source=JobSource.ADZUNA,
            company="Stripe",
            min_score=70,
        )
        assert params.source == JobSource.ADZUNA
        assert params.company == "Stripe"
        assert params.min_score == 70
    
    def test_jobs_query_params_optional_fields(self):
        """Test jobs query params with optional fields"""
        params = JobsQueryParams()
        assert params.source is None
        assert params.company is None
        assert params.min_score is None
    
    def test_min_score_range_validation(self):
        """Test min_score must be 0-100"""
        # Valid boundary values
        JobsQueryParams(min_score=0)
        JobsQueryParams(min_score=100)
        
        # Invalid values
        with pytest.raises(ValidationError):
            JobsQueryParams(min_score=-1)
        
        with pytest.raises(ValidationError):
            JobsQueryParams(min_score=101)


class TestContactsQueryParams:
    """Test ContactsQueryParams validation - Requirements: 23.2"""
    
    def test_valid_contacts_query_params(self):
        """Test valid contacts query parameters"""
        params = ContactsQueryParams(
            page=2,
            limit=20,
            company="OpenAI",
            min_confidence=80.0,
        )
        assert params.company == "OpenAI"
        assert params.min_confidence == 80.0
    
    def test_min_confidence_range_validation(self):
        """Test min_confidence must be 0-100"""
        # Valid boundary values
        ContactsQueryParams(min_confidence=0)
        ContactsQueryParams(min_confidence=100)
        
        # Invalid values
        with pytest.raises(ValidationError):
            ContactsQueryParams(min_confidence=-0.1)
        
        with pytest.raises(ValidationError):
            ContactsQueryParams(min_confidence=100.1)


class TestPendingOutreachParams:
    """Test PendingOutreachParams validation - Requirements: 23.2"""
    
    def test_valid_pending_outreach_params(self):
        """Test valid pending outreach parameters"""
        params = PendingOutreachParams(min_score=75, limit=100)
        assert params.min_score == 75
        assert params.limit == 100
    
    def test_pending_outreach_defaults(self):
        """Test pending outreach with default values"""
        params = PendingOutreachParams()
        assert params.min_score == 50
        assert params.limit == 50
    
    def test_min_score_validation(self):
        """Test min_score must be 0-100"""
        PendingOutreachParams(min_score=0)
        PendingOutreachParams(min_score=100)
        
        with pytest.raises(ValidationError):
            PendingOutreachParams(min_score=-1)
        
        with pytest.raises(ValidationError):
            PendingOutreachParams(min_score=101)
    
    def test_limit_validation(self):
        """Test limit must be 1-500"""
        PendingOutreachParams(limit=1)
        PendingOutreachParams(limit=500)
        
        with pytest.raises(ValidationError):
            PendingOutreachParams(limit=0)
        
        with pytest.raises(ValidationError):
            PendingOutreachParams(limit=501)


class TestStatsResponse:
    """Test StatsResponse validation - Requirements: 23.3"""
    
    def test_valid_stats_response(self):
        """Test valid stats response"""
        stats = StatsData(
            total_jobs=1000,
            total_contacts=150,
            total_applications=500,
            total_outreach_attempts=200,
            emails_sent=180,
            follow_ups_sent=50,
            success_rate=90.0,
        )
        response = StatsResponse(
            status="success",
            source="db_fallback",
            stats=stats,
            recent_outreach=[],
        )
        assert response.status == "success"
        assert response.stats.total_jobs == 1000
        assert response.stats.success_rate == 90.0
    
    def test_stats_with_recent_outreach(self):
        """Test stats response with recent outreach records"""
        recent = RecentOutreach(
            id=1,
            contact_email="test@example.com",
            status="sent",
            sent_at=datetime.utcnow(),
        )
        response = StatsResponse(
            status="success",
            source="live",
            stats=StatsData(
                total_jobs=0,
                total_contacts=0,
                total_applications=0,
                total_outreach_attempts=1,
                emails_sent=1,
                follow_ups_sent=0,
                success_rate=100.0,
            ),
            recent_outreach=[recent],
        )
        assert len(response.recent_outreach) == 1
        assert response.recent_outreach[0].contact_email == "test@example.com"
    
    def test_stats_with_error(self):
        """Test stats response with error"""
        response = StatsResponse(
            status="error",
            source="empty",
            error="Database connection failed",
            stats=StatsData(
                total_jobs=0,
                total_contacts=0,
                total_applications=0,
                total_outreach_attempts=0,
                emails_sent=0,
                follow_ups_sent=0,
                success_rate=0.0,
            ),
            recent_outreach=[],
        )
        assert response.error == "Database connection failed"


class TestPendingOutreachResponse:
    """Test PendingOutreachResponse validation - Requirements: 23.3"""
    
    def test_valid_pending_outreach_response(self):
        """Test valid pending outreach response"""
        job = PendingOutreachJob(
            id=123,
            title="Software Engineer",
            company="Stripe",
            location="Remote",
            url="https://stripe.com/jobs/123",
            source="adzuna",
            posted_date=datetime.utcnow(),
            fetched_at=datetime.utcnow(),
        )
        response = PendingOutreachResponse(
            status="success",
            total_jobs=1,
            jobs=[job],
        )
        assert response.total_jobs == 1
        assert response.jobs[0].company == "Stripe"
    
    def test_empty_pending_outreach_response(self):
        """Test pending outreach response with no jobs"""
        response = PendingOutreachResponse(
            status="success",
            total_jobs=0,
            jobs=[],
        )
        assert response.total_jobs == 0
        assert len(response.jobs) == 0


class TestSignalHireResponses:
    """Test SignalHire webhook response models - Requirements: 23.3"""
    
    def test_callback_response(self):
        """Test SignalHire callback response"""
        response = SignalHireCallbackResponse(
            status="received",
            saved=3,
            total=5,
        )
        assert response.status == "received"
        assert response.saved == 3
        assert response.total == 5
    
    def test_result_found_response(self):
        """Test SignalHire result found response"""
        response = SignalHireResultResponse(
            status="found",
            contact={"email": "test@example.com", "name": "John Doe"},
        )
        assert response.status == "found"
        assert response.contact["email"] == "test@example.com"
    
    def test_result_not_found_response(self):
        """Test SignalHire result not found response"""
        response = SignalHireResultResponse(
            status="not_found",
            message="No callback yet",
        )
        assert response.status == "not_found"
        assert response.message == "No callback yet"


class TestTimeoutErrorResponse:
    """Test TimeoutErrorResponse validation - Requirements: 23.4"""
    
    def test_valid_timeout_error_response(self):
        """Test valid timeout error response"""
        response = TimeoutErrorResponse(
            message="Operation timed out after 300 seconds",
            timeout_seconds=300,
            trace_id="abc-123",
        )
        assert response.status == "error"
        assert response.error == "TimeoutError"
        assert response.timeout_seconds == 300
        assert response.trace_id == "abc-123"
    
    def test_timeout_error_response_defaults(self):
        """Test timeout error response with minimal fields"""
        response = TimeoutErrorResponse(
            message="Request timed out",
            timeout_seconds=60,
        )
        assert response.trace_id is None
        assert response.timestamp is not None


class TestRateLimitErrorResponse:
    """Test RateLimitErrorResponse validation - Requirements: 23.2"""
    
    def test_valid_rate_limit_error_response(self):
        """Test valid rate limit error response"""
        response = RateLimitErrorResponse(
            message="Rate limit exceeded",
            retry_after_seconds=30,
            trace_id="xyz-456",
        )
        assert response.status == "error"
        assert response.error == "RateLimitError"
        assert response.retry_after_seconds == 30
    
    def test_rate_limit_response_without_retry_after(self):
        """Test rate limit response without retry_after"""
        response = RateLimitErrorResponse(
            message="Too many requests",
        )
        assert response.retry_after_seconds is None


class TestErrorHandlerIntegration:
    """Integration tests for error handlers - Requirements: 23.2"""
    
    def test_api_error_response_format(self):
        """Test that API errors produce consistent response format"""
        from src.api_error_handlers import (
            APIError,
            ResourceNotFoundError,
            ServiceUnavailableError,
            TimeoutError as APITimeoutError,
            RateLimitError,
            DatabaseError,
            ExternalAPIError,
        )
        
        # Test APIError
        error = APIError("Test error")
        assert error.status_code == 500
        assert error.error_type == "APIError"
        
        # Test ResourceNotFoundError
        error = ResourceNotFoundError("Job", 123)
        assert error.status_code == 404
        assert "Job" in error.message
        assert "123" in error.message
        
        # Test ServiceUnavailableError
        error = ServiceUnavailableError("EmailOutreach", "Check configuration")
        assert error.status_code == 503
        assert "EmailOutreach" in error.message
        
        # Test TimeoutError
        error = APITimeoutError("job processing", 300)
        assert error.status_code == 504
        assert error.timeout_seconds == 300
        
        # Test RateLimitError
        error = RateLimitError("Too many requests", retry_after_seconds=60)
        assert error.status_code == 429
        assert error.retry_after_seconds == 60
        
        # Test DatabaseError
        error = DatabaseError("Connection failed")
        assert error.status_code == 500
        assert "Database" in error.message
        
        # Test ExternalAPIError
        error = ExternalAPIError("GitHub", "API rate limited")
        assert error.status_code == 502
        assert "GitHub" in error.message
