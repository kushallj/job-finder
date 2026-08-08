"""
Unit tests for AsyncJobProcessor database session management and worker isolation.

Tests cover:
- Per-task database session creation (new session for each job)
- Explicit transaction management (begin/commit/rollback)
- Automatic rollback on database errors
- Session cleanup in finally block
- Worker isolation: one worker's database failure doesn't affect others
- Separate sessions between workers (no shared session state)

Requirements Coverage: 13.3, 13.4, 13.5, 19.1, 19.2, 19.3, 19.4, 19.5
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, call
from datetime import datetime
from sqlalchemy.exc import OperationalError, IntegrityError

from src.async_pipeline.processor import AsyncJobProcessor
from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.types import JobContext, JobStatus


@pytest.fixture
def processor_config():
    """Create test configuration."""
    return ProcessorConfig(
        db_timeout_seconds=5.0,
        max_retries=1,
    )


@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    llm_service = AsyncMock()
    email_service = AsyncMock()
    scraper_service = AsyncMock()
    return llm_service, email_service, scraper_service


@pytest.fixture
def sample_jobs():
    """Create multiple sample job contexts for testing."""
    jobs = []
    for i in range(3):
        jobs.append(
            JobContext(
                job_id=f"test-job-{i}",
                title=f"Software Engineer {i}",
                company=f"Tech Corp {i}",
                description="A" * 100,
                url=f"https://example.com/job{i}",
                source="indeed",
            )
        )
    return jobs


class TestPerTaskSessions:
    """Test that each job gets its own database session."""
    
    @pytest.mark.asyncio
    async def test_new_session_created_per_job(self, processor_config, mock_services):
        """Test that store_result creates a new session for each job.
        
        Requirements Coverage: 13.3, 19.4
        """
        llm_service, email_service, scraper_service = mock_services
        
        # Track session creation
        sessions_created = []
        
        def create_mock_session():
            """Factory that creates a unique session for each call."""
            session = AsyncMock()
            
            # Mock the query result
            mock_db_result = AsyncMock()
            mock_db_result.scalar_one_or_none = MagicMock(return_value=None)  # NOT async
            session.execute = AsyncMock(return_value=mock_db_result)
            
            session.commit = AsyncMock()
            session.flush = AsyncMock()
            session.add = MagicMock()
            session.rollback = AsyncMock()
            session.close = AsyncMock()
            
            # Create proper async context manager for begin()
            class BeginContextManager:
                async def __aenter__(self_inner):
                    return self_inner
                
                async def __aexit__(self_inner, *args):
                    # Auto-commit on successful exit
                    if args[0] is None:  # No exception
                        await session.commit()
            
            session.begin = MagicMock(return_value=BeginContextManager())
            
            # Make session work as async context manager
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock()
            
            # Track this session
            sessions_created.append(session)
            
            return session
        
        # Create session factory that returns context manager
        class AsyncSessionFactory:
            def __call__(self):
                session = create_mock_session()
                return session
        
        session_factory = AsyncSessionFactory()
        
        processor = AsyncJobProcessor(
            llm_service=llm_service,
            email_service=email_service,
            scraper_service=scraper_service,
            db_session_factory=session_factory,
            config=processor_config,
        )
        
        # Create multiple jobs
        jobs = [
            JobContext(
                job_id=f"job-{i}",
                title=f"Job {i}",
                company="Company",
                description="Description" * 20,  # Make description longer
                url="https://example.com",
                source="test",
            )
            for i in range(3)
        ]
        
        # Process each job
        for job in jobs:
            result_data = {
                "match_score": 85,
                "matched_skills": ["Python"],
                "missing_skills": [],
            }
            
            await processor.store_result(job, result_data)
        
        # Verify that 3 separate sessions were created (one per job)
        assert len(sessions_created) == 3
        
        # Verify each session is unique
        session_ids = [id(session) for session in sessions_created]
        assert len(set(session_ids)) == 3, "Each job should get a unique session"
    
    @pytest.mark.asyncio
    async def test_session_cleanup_after_success(self, processor_config, mock_services):
        """Test that session is properly cleaned up after successful operation.
        
        Requirements Coverage: 13.3, 19.4, 19.5
        """
        llm_service, email_service, scraper_service = mock_services
        
        session = AsyncMock()
        
        # Mock the query result
        mock_db_result = AsyncMock()
        mock_db_result.scalar_one_or_none = MagicMock(return_value=None)  # NOT async
        session.execute = AsyncMock(return_value=mock_db_result)
        
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        session.close = AsyncMock()
        
        # Track context manager calls
        enter_count = [0]
        exit_count = [0]
        
        class BeginContextManager:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                if args[0] is None:
                    await session.commit()
        
        session.begin = MagicMock(return_value=BeginContextManager())
        
        async def track_enter(*args):
            enter_count[0] += 1
            return session
        
        async def track_exit(*args):
            exit_count[0] += 1
        
        session.__aenter__ = track_enter
        session.__aexit__ = track_exit
        
        class AsyncSessionFactory:
            def __call__(self):
                return session
        
        processor = AsyncJobProcessor(
            llm_service=llm_service,
            email_service=email_service,
            scraper_service=scraper_service,
            db_session_factory=AsyncSessionFactory(),
            config=processor_config,
        )
        
        job = JobContext(
            job_id="test-job",
            title="Job",
            company="Company",
            description="Description" * 20,
            url="https://example.com",
            source="test",
        )
        
        result_data = {
            "match_score": 85,
            "matched_skills": ["Python"],
            "missing_skills": [],
        }
        
        await processor.store_result(job, result_data)
        
        # Verify session was entered and exited (cleanup)
        assert enter_count[0] == 1, "Session context manager should be entered"
        assert exit_count[0] == 1, "Session context manager should be exited (cleanup)"


class TestExplicitTransactions:
    """Test explicit transaction management with begin/commit/rollback."""
    
    @pytest.mark.asyncio
    async def test_explicit_transaction_begin_commit(self, processor_config, mock_services):
        """Test that transactions use explicit begin() and auto-commit.
        
        Requirements Coverage: 19.1, 19.2
        """
        llm_service, email_service, scraper_service = mock_services
        
        session = AsyncMock()
        
        # Mock the query result
        mock_db_result = AsyncMock()
        mock_db_result.scalar_one_or_none = MagicMock(return_value=None)  # NOT async
        session.execute = AsyncMock(return_value=mock_db_result)
        
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        
        begin_called = [False]
        commit_called = [False]
        
        class BeginContextManager:
            async def __aenter__(self):
                begin_called[0] = True
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    commit_called[0] = True
                    await session.commit()
        
        session.begin = MagicMock(return_value=BeginContextManager())
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock()
        
        class AsyncSessionFactory:
            def __call__(self):
                return session
        
        processor = AsyncJobProcessor(
            llm_service=llm_service,
            email_service=email_service,
            scraper_service=scraper_service,
            db_session_factory=AsyncSessionFactory(),
            config=processor_config,
        )
        
        job = JobContext(
            job_id="test-job",
            title="Job",
            company="Company",
            description="Description" * 20,
            url="https://example.com",
            source="test",
        )
        
        result_data = {
            "match_score": 85,
            "matched_skills": ["Python"],
            "missing_skills": [],
        }
        
        await processor.store_result(job, result_data)
        
        # Verify transaction was explicitly started and committed
        assert begin_called[0], "Transaction should be explicitly started with begin()"
        assert commit_called[0], "Transaction should be committed on success"
    
    @pytest.mark.asyncio
    async def test_automatic_rollback_on_error(self, processor_config, mock_services):
        """Test that transaction is automatically rolled back on database error.
        
        Requirements Coverage: 19.1, 19.3, 13.4
        """
        llm_service, email_service, scraper_service = mock_services
        
        session = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        
        rollback_called = [False]
        
        class BeginContextManager:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    rollback_called[0] = True
                    await session.rollback()
                return False  # Don't suppress exception
        
        session.begin = MagicMock(return_value=BeginContextManager())
        
        # Simulate database error during execute
        session.execute = AsyncMock(side_effect=OperationalError("Database error", None, None))
        
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock()
        
        class AsyncSessionFactory:
            def __call__(self):
                return session
        
        processor = AsyncJobProcessor(
            llm_service=llm_service,
            email_service=email_service,
            scraper_service=scraper_service,
            db_session_factory=AsyncSessionFactory(),
            config=processor_config,
        )
        
        job = JobContext(
            job_id="test-job",
            title="Job",
            company="Company",
            description="Description" * 20,
            url="https://example.com",
            source="test",
        )
        
        result_data = {
            "match_score": 85,
            "matched_skills": ["Python"],
            "missing_skills": [],
        }
        
        # Should raise the database error (caught by retry decorator, but will fail after retries)
        try:
            await processor.store_result(job, result_data)
        except OperationalError:
            pass  # Expected
        
        # Verify rollback was called automatically
        assert rollback_called[0], "Transaction should be rolled back on error"


class TestWorkerIsolation:
    """Test that one worker's database failure doesn't affect other workers."""
    
    @pytest.mark.asyncio
    async def test_worker_isolation_database_failures(self, processor_config, mock_services):
        """Test that database failure in one worker doesn't affect other workers.
        
        This test verifies that when one database operation fails, it doesn't
        affect other concurrent operations. Each operation has its own session.
        
        Requirements Coverage: 13.3, 13.4, 13.5
        """
        llm_service, email_service, scraper_service = mock_services
        
        # Track which calls succeeded or failed
        call_results = []
        call_counter = [0]
        
        def create_session():
            """Create a session that alternates between success and failure."""
            call_num = call_counter[0]
            call_counter[0] += 1
            
            session = AsyncMock()
            session.commit = AsyncMock()
            session.flush = AsyncMock()
            session.add = MagicMock()
            session.rollback = AsyncMock()
            session.close = AsyncMock()
            
            class BeginContextManager:
                async def __aenter__(self):
                    return self
                
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    if exc_type is None:
                        await session.commit()
                    else:
                        await session.rollback()
                    return False
            
            session.begin = MagicMock(return_value=BeginContextManager())
            
            # Make the second call (call_num == 1) fail
            if call_num == 1:
                session.execute = AsyncMock(
                    side_effect=IntegrityError("Constraint violation", None, None)
                )
            else:
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none = MagicMock(return_value=None)  # NOT async
                session.execute = AsyncMock(return_value=mock_result)
            
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock()
            
            return session
        
        class AsyncSessionFactory:
            def __call__(self):
                return create_session()
        
        processor = AsyncJobProcessor(
            llm_service=llm_service,
            email_service=email_service,
            scraper_service=scraper_service,
            db_session_factory=AsyncSessionFactory(),
            config=processor_config,
        )
        
        # Create multiple jobs
        jobs = [
            JobContext(
                job_id=f"job-{i}",
                title=f"Job {i}",
                company="Company",
                description="Description" * 20,
                url="https://example.com",
                source="test",
            )
            for i in range(3)
        ]
        
        result_data = {
            "match_score": 85,
            "matched_skills": ["Python"],
            "missing_skills": [],
        }
        
        # Simulate concurrent workers processing jobs
        async def worker_process_job(job, index):
            """Simulate a worker processing a job."""
            try:
                await processor.store_result(job, result_data)
                call_results.append(("success", index))
                return "success"
            except Exception as e:
                call_results.append(("failed", index, type(e).__name__))
                return "failed"
        
        # Process all jobs concurrently (simulating multiple workers)
        results = await asyncio.gather(
            *[worker_process_job(job, i) for i, job in enumerate(jobs)],
            return_exceptions=False  # Let exceptions propagate to gather
        )
        
        # Verify results - we expect index 1 to fail (second call), others succeed
        # Due to retry logic, the failure might be caught, so we check the overall pattern
        successes = sum(1 for r in results if r == "success")
        failures = sum(1 for r in results if r == "failed")
        
        # At least 2 should succeed (demonstrating isolation)
        assert successes >= 2, f"At least 2 workers should succeed despite failures, got {successes} successes"
        
        # Verify all jobs were processed (no job left unprocessed)
        assert len(results) == 3, "All 3 jobs should be processed"
    
    @pytest.mark.asyncio
    async def test_separate_sessions_no_shared_state(self, processor_config, mock_services):
        """Test that workers use completely separate sessions with no shared state.
        
        Requirements Coverage: 13.3, 13.5, 19.4
        """
        llm_service, email_service, scraper_service = mock_services
        
        # Track all sessions created
        sessions_created = []
        session_operations = {}
        
        def create_unique_session():
            """Create a unique session for tracking."""
            session_id = f"session-{len(sessions_created)}"
            session = AsyncMock()
            session.id = session_id
            
            # Mock the query result
            mock_db_result = AsyncMock()
            mock_db_result.scalar_one_or_none = MagicMock(return_value=None)  # NOT async
            session.execute = AsyncMock(return_value=mock_db_result)
            
            session.commit = AsyncMock()
            session.flush = AsyncMock()
            session.add = MagicMock()
            session.rollback = AsyncMock()
            session.close = AsyncMock()
            
            # Track operations on this session
            session_operations[session_id] = []
            
            class BeginContextManager:
                async def __aenter__(self):
                    session_operations[session_id].append("begin")
                    return self
                
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    if exc_type is None:
                        session_operations[session_id].append("commit")
                        await session.commit()
            
            session.begin = MagicMock(return_value=BeginContextManager())
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock()
            
            sessions_created.append(session)
            return session
        
        class AsyncSessionFactory:
            def __call__(self):
                return create_unique_session()
        
        processor = AsyncJobProcessor(
            llm_service=llm_service,
            email_service=email_service,
            scraper_service=scraper_service,
            db_session_factory=AsyncSessionFactory(),
            config=processor_config,
        )
        
        # Create multiple jobs
        jobs = [
            JobContext(
                job_id=f"job-{i}",
                title=f"Job {i}",
                company="Company",
                description="Description" * 20,
                url="https://example.com",
                source="test",
            )
            for i in range(3)
        ]
        
        result_data = {
            "match_score": 85,
            "matched_skills": ["Python"],
            "missing_skills": [],
        }
        
        # Process all jobs concurrently
        await asyncio.gather(
            *[processor.store_result(job, result_data) for job in jobs]
        )
        
        # Verify that each job got its own session
        assert len(sessions_created) == 3, "Each job should create its own session"
        
        # Verify all sessions are unique
        session_ids = [session.id for session in sessions_created]
        assert len(set(session_ids)) == 3, "All sessions should be unique"
        
        # Verify each session had its own operations
        for session_id in session_ids:
            ops = session_operations[session_id]
            assert "begin" in ops, f"{session_id} should have begun a transaction"
            assert "commit" in ops, f"{session_id} should have committed"


class TestSessionCleanup:
    """Test that sessions are properly cleaned up in all scenarios."""
    
    @pytest.mark.asyncio
    async def test_session_cleanup_on_timeout(self, processor_config, mock_services):
        """Test that session is cleaned up even when operation times out.
        
        Requirements Coverage: 13.3, 19.4, 19.5
        """
        llm_service, email_service, scraper_service = mock_services
        
        # Use very short timeout to force timeout
        config = ProcessorConfig(db_timeout_seconds=0.1)
        
        session = AsyncMock()
        session.close = AsyncMock()
        
        cleanup_called = [False]
        
        async def track_exit(*args):
            cleanup_called[0] = True
        
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = track_exit
        
        class BeginContextManager:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, *args):
                pass
        
        session.begin = MagicMock(return_value=BeginContextManager())
        
        # Simulate slow database operation
        async def slow_execute(*args):
            await asyncio.sleep(1.0)  # Longer than timeout
            return AsyncMock()
        
        session.execute = slow_execute
        
        class AsyncSessionFactory:
            def __call__(self):
                return session
        
        processor = AsyncJobProcessor(
            llm_service=llm_service,
            email_service=email_service,
            scraper_service=scraper_service,
            db_session_factory=AsyncSessionFactory(),
            config=config,
        )
        
        job = JobContext(
            job_id="test-job",
            title="Job",
            company="Company",
            description="Description" * 20,
            url="https://example.com",
            source="test",
        )
        
        result_data = {
            "match_score": 85,
            "matched_skills": ["Python"],
            "missing_skills": [],
        }
        
        # Should timeout (caught by retry decorator, but will fail after retries)
        try:
            await processor.store_result(job, result_data)
        except asyncio.TimeoutError:
            pass  # Expected
        
        # Verify session cleanup was called despite timeout
        assert cleanup_called[0], "Session should be cleaned up even on timeout"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
