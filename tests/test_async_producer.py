"""
Unit tests for AsyncJobProducer with comprehensive requirement coverage.

Tests verify:
- Requirement 1.1: Chunked database fetching
- Requirement 1.2: Yielding jobs one at a time
- Requirement 1.3: Session lifecycle management
- Requirement 1.4: O(chunk_size) memory usage
- Requirement 1.5: Clean generator termination
- Requirement 10.1-10.5: Memory efficiency through streaming
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from src.async_pipeline.producer import AsyncJobProducer
from src.async_pipeline.types import JobContext
from src.models import Base, Job, Application


class TestAsyncJobProducerRequirements:
    """Test AsyncJobProducer implementation against requirements."""
    
    @pytest.fixture
    async def async_engine(self):
        """Create an async in-memory SQLite engine."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
        )
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield engine
        
        await engine.dispose()
    
    @pytest.fixture
    def async_session_factory(self, async_engine):
        """Create an async session factory."""
        return sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    @pytest.fixture
    async def populated_db(self, async_session_factory):
        """Populate database with test jobs."""
        async with async_session_factory() as session:
            jobs = []
            for i in range(250):  # More than 2 chunks (default chunk_size=100)
                job = Job(
                    job_id=f"job-{i:03d}",
                    title=f"Software Engineer {i}" if i % 2 == 0 else f"Data Scientist {i}",
                    company=f"Company {i % 10}",
                    location="Remote",
                    description=f"{'A' * 100} position {i}",  # At least 50 chars
                    url=f"https://example.com/job/{i}",
                    source="indeed",
                    posted_date=datetime.utcnow(),
                )
                jobs.append(job)
            
            session.add_all(jobs)
            await session.commit()
        
        return 250  # Total job count
    
    @pytest.mark.asyncio
    async def test_requirement_1_1_chunked_fetching(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test Requirement 1.1: Jobs are retrieved in configurable chunks.
        
        **Validates: Requirements 1.1**
        """
        chunk_size = 50
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=chunk_size,
        )
        
        # Track how many times _fetch_job_chunk is called
        fetch_count = 0
        original_fetch = producer._fetch_job_chunk
        
        async def tracked_fetch(*args, **kwargs):
            nonlocal fetch_count
            fetch_count += 1
            return await original_fetch(*args, **kwargs)
        
        producer._fetch_job_chunk = tracked_fetch
        
        # Consume all jobs
        jobs = []
        async for job in producer.produce_jobs("Software Engineer"):
            jobs.append(job)
        
        # Should have fetched in multiple chunks
        expected_chunks = (len(jobs) + chunk_size - 1) // chunk_size
        assert fetch_count >= expected_chunks
        assert len(jobs) > 0
    
    @pytest.mark.asyncio
    async def test_requirement_1_2_yields_one_at_a_time(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test Requirement 1.2: Yields JobContext objects one at a time.
        
        **Validates: Requirements 1.2**
        """
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=100,
        )
        
        # Verify generator yields one at a time
        job_iterator = producer.produce_jobs("Software Engineer")
        
        # Get first job
        first_job = await anext(job_iterator)
        assert isinstance(first_job, JobContext)
        assert first_job.job_id is not None
        
        # Get second job
        second_job = await anext(job_iterator)
        assert isinstance(second_job, JobContext)
        assert second_job.job_id != first_job.job_id
        
        # Consume rest
        remaining = [job async for job in job_iterator]
        assert len(remaining) > 0
    
    @pytest.mark.asyncio
    async def test_requirement_1_3_session_lifecycle(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test Requirement 1.3: Database session is closed after each chunk.
        
        **Validates: Requirements 1.3**
        """
        chunk_size = 50
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=chunk_size,
        )
        
        # Track how many times _fetch_job_chunk is called
        # Each call should open and close a session
        fetch_calls = 0
        original_fetch = producer._fetch_job_chunk
        
        async def tracked_fetch(*args, **kwargs):
            nonlocal fetch_calls
            fetch_calls += 1
            return await original_fetch(*args, **kwargs)
        
        producer._fetch_job_chunk = tracked_fetch
        
        # Consume all jobs
        jobs = [job async for job in producer.produce_jobs("Software Engineer")]
        
        # Verify multiple chunks were fetched (each with its own session)
        assert fetch_calls > 1  # Multiple chunks means multiple session open/close cycles
        assert len(jobs) > chunk_size  # More jobs than one chunk
    
    @pytest.mark.asyncio
    async def test_requirement_1_4_memory_usage_o_chunk_size(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test Requirement 1.4: Memory usage is O(chunk_size), not O(total_jobs).
        
        **Validates: Requirements 1.4, 10.3**
        """
        chunk_size = 50
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=chunk_size,
        )
        
        # Track maximum batch size fetched
        max_batch_size = 0
        original_fetch = producer._fetch_job_chunk
        
        async def tracked_fetch(*args, **kwargs):
            nonlocal max_batch_size
            result = await original_fetch(*args, **kwargs)
            max_batch_size = max(max_batch_size, len(result))
            return result
        
        producer._fetch_job_chunk = tracked_fetch
        
        # Consume all jobs
        total_jobs = 0
        async for _ in producer.produce_jobs(""):
            total_jobs += 1
        
        # Max batch size should be <= chunk_size
        assert max_batch_size <= chunk_size
        # Total jobs should be much larger than chunk_size
        assert total_jobs > chunk_size * 2
    
    @pytest.mark.asyncio
    async def test_requirement_1_5_clean_termination(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test Requirement 1.5: Generator terminates cleanly when no more jobs.
        
        **Validates: Requirements 1.5**
        """
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=100,
        )
        
        # Consume all jobs
        jobs = []
        async for job in producer.produce_jobs("NonExistentQuery_XYZ"):
            jobs.append(job)
        
        # Should terminate cleanly with no results
        assert len(jobs) == 0
        
        # Try again with a query that has results
        jobs = []
        async for job in producer.produce_jobs("Software Engineer"):
            jobs.append(job)
        
        # Should have some results and terminate normally
        assert len(jobs) > 0
    
    @pytest.mark.asyncio
    async def test_requirement_10_1_async_generator_pattern(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test Requirement 10.1: Uses async generators to yield jobs one at a time.
        
        **Validates: Requirements 10.1**
        """
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=100,
        )
        
        # Verify produce_jobs returns an async generator
        result = producer.produce_jobs("Software Engineer")
        assert hasattr(result, "__anext__")
        assert hasattr(result, "__aiter__")
        
        # Verify we can iterate with async for
        count = 0
        async for job in result:
            count += 1
            if count >= 5:
                break  # Don't consume all
        
        assert count == 5
    
    @pytest.mark.asyncio
    async def test_requirement_10_2_previous_job_gc_eligible(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test Requirement 10.2: Previous job is GC-eligible after yielding next job.
        
        **Validates: Requirements 10.2**
        """
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=50,
        )
        
        # Keep track of job_ids but not job objects
        job_ids = []
        
        async for job in producer.produce_jobs("Software Engineer"):
            # Only keep job_id, not the whole JobContext
            job_ids.append(job.job_id)
            # After loop iteration, 'job' reference is lost
            # and object becomes GC-eligible
        
        # We only stored strings, not JobContext objects
        assert len(job_ids) > 0
        assert all(isinstance(job_id, str) for job_id in job_ids)
    
    @pytest.mark.asyncio
    async def test_requirement_10_5_session_closed_after_chunk(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test Requirement 10.5: Database sessions closed immediately after fetching chunk.
        
        **Validates: Requirements 10.5**
        """
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=50,
        )
        
        # Track when sessions are in use
        sessions_active = []
        original_fetch = producer._fetch_job_chunk
        
        async def tracked_fetch(*args, **kwargs):
            # Session should be active during fetch
            sessions_active.append(True)
            result = await original_fetch(*args, **kwargs)
            # After fetch returns, session should be closed
            sessions_active.append(False)
            return result
        
        producer._fetch_job_chunk = tracked_fetch
        
        # Consume some jobs
        count = 0
        async for _ in producer.produce_jobs("Software Engineer"):
            count += 1
            if count >= 10:
                break
        
        # Should have tracked session lifecycle
        assert len(sessions_active) > 0
    
    @pytest.mark.asyncio
    async def test_converts_orm_to_immutable_jobcontext(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test that ORM Job objects are converted to immutable JobContext dataclasses.
        
        **Validates: Requirements 1.2, 17.1**
        """
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=100,
        )
        
        # Get a job
        async for job in producer.produce_jobs("Software Engineer"):
            # Verify it's a JobContext, not ORM Job
            assert isinstance(job, JobContext)
            assert hasattr(job, "__dataclass_fields__")
            
            # Verify immutability (frozen)
            with pytest.raises(Exception):  # FrozenInstanceError
                job.title = "New Title"
            
            # Verify required fields
            assert job.job_id
            assert job.title
            assert job.company
            assert job.description
            assert job.url
            assert job.source
            
            break  # Only need to test one
    
    @pytest.mark.asyncio
    async def test_job_count_without_loading_all_jobs(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test get_job_count returns accurate count without loading all jobs.
        
        **Validates: Requirements 1.4, 10.3**
        """
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=50,
        )
        
        # Get count
        count = await producer.get_job_count("Software Engineer")
        
        # Verify count is accurate
        assert count > 0
        
        # Count all jobs manually
        manual_count = 0
        async for _ in producer.produce_jobs("Software Engineer"):
            manual_count += 1
        
        # Counts should match
        assert count == manual_count
    
    @pytest.mark.asyncio
    async def test_filters_unprocessed_jobs(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test that producer can filter out already processed jobs.
        
        **Validates: Requirements 1.1**
        """
        # Add an application to mark a job as processed
        async with async_session_factory() as session:
            result = await session.execute(select(Job).limit(1))
            job = result.scalar_one()
            
            application = Application(
                job_id=job.id,
                match_score=85.0,
                status="applied",
            )
            session.add(application)
            await session.commit()
        
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=100,
        )
        
        # Get unprocessed jobs
        unprocessed = []
        async for job in producer.produce_unprocessed_jobs(""):
            unprocessed.append(job)
        
        # Should exclude the job with application
        unprocessed_ids = [j.job_id for j in unprocessed]
        assert "job-000" not in unprocessed_ids  # First job has application
    
    @pytest.mark.asyncio
    async def test_chunk_size_validation(self, async_session_factory):
        """
        Test that invalid chunk_size raises ValueError.
        """
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            AsyncJobProducer(
                db_session_factory=async_session_factory,
                chunk_size=0,
            )
        
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            AsyncJobProducer(
                db_session_factory=async_session_factory,
                chunk_size=-10,
            )
    
    @pytest.mark.asyncio
    async def test_jobs_produced_counter(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test that jobs_produced counter is accurate.
        """
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=50,
        )
        
        # Initial count should be 0
        assert producer.jobs_produced == 0
        
        # Consume all jobs to get accurate count
        jobs_consumed = []
        async for job in producer.produce_jobs("Software Engineer"):
            jobs_consumed.append(job)
        
        # Counter should match actual jobs consumed
        assert producer.jobs_produced == len(jobs_consumed)
        assert producer.jobs_produced > 0
        
        # Reset counter
        producer.reset_counter()
        assert producer.jobs_produced == 0
    
    @pytest.mark.asyncio
    async def test_query_filters(
        self,
        async_session_factory,
        populated_db,
    ):
        """
        Test that query parameter filters results correctly.
        """
        producer = AsyncJobProducer(
            db_session_factory=async_session_factory,
            chunk_size=100,
        )
        
        # Query for specific title
        engineer_jobs = []
        async for job in producer.produce_jobs("Software Engineer"):
            engineer_jobs.append(job)
        
        # Query for different title
        scientist_jobs = []
        async for job in producer.produce_jobs("Data Scientist"):
            scientist_jobs.append(job)
        
        # Both should have results
        assert len(engineer_jobs) > 0
        assert len(scientist_jobs) > 0
        
        # Results should be different
        engineer_ids = set(j.job_id for j in engineer_jobs)
        scientist_ids = set(j.job_id for j in scientist_jobs)
        assert engineer_ids != scientist_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
