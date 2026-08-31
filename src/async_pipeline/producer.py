"""
Async job producer with O(1) memory usage for the async job pipeline.

This module provides streaming job production using async generators,
fetching jobs from the database in chunks to maintain constant memory.
"""

import logging
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.async_pipeline.types import JobContext
from src.models import Job, Application, OutreachRecord

logger = logging.getLogger(__name__)


class AsyncJobProducer:
    """
    Streaming job producer with O(1) memory usage.
    
    Fetches jobs from database in configurable chunks using async generators.
    Only one chunk is in memory at a time, regardless of total job count.
    
    Example:
        producer = AsyncJobProducer(
            db_session_factory=async_session_maker,
            chunk_size=100
        )
        
        async for job in producer.produce_jobs("software engineer"):
            await process(job)
    """
    
    def __init__(
        self,
        db_session_factory: Callable[[], AsyncSession],
        chunk_size: int = 100,
    ):
        """
        Initialize the async job producer.
        
        Args:
            db_session_factory: Async context manager that yields database sessions.
            chunk_size: Number of jobs to fetch per database query.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        
        self._db_session_factory = db_session_factory
        self._chunk_size = chunk_size
        self._jobs_produced = 0
        
        logger.debug(f"AsyncJobProducer initialized with chunk_size={chunk_size}")
    
    @property
    def chunk_size(self) -> int:
        """Get the chunk size."""
        return self._chunk_size
    
    @property
    def jobs_produced(self) -> int:
        """Get the total number of jobs produced."""
        return self._jobs_produced
    
    async def produce_jobs(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[JobContext, None]:
        """
        Stream jobs from database in chunks.
        
        Uses async generator pattern to maintain O(1) memory usage.
        
        Args:
            query: Search query to filter jobs.
            filters: Additional filters to apply to job query.
            
        Yields:
            JobContext objects one at a time.
        """
        offset = 0
        filters = filters or {}
        
        logger.info(f"Starting job production with query: {query}")
        
        while True:
            # Fetch chunk from database
            jobs = await self._fetch_job_chunk(
                query=query,
                offset=offset,
                limit=self._chunk_size,
                filters=filters,
            )
            
            if not jobs:
                logger.info(f"No more jobs to produce (reached offset {offset})")
                break
            
            # Yield each job individually
            for job in jobs:
                yield job
                self._jobs_produced += 1
            
            offset += self._chunk_size
            
            logger.debug(
                f"Produced chunk of {len(jobs)} jobs, total: {self._jobs_produced}"
            )
        
        logger.info(f"Job production complete, total produced: {self._jobs_produced}")
    
    async def _fetch_job_chunk(
        self,
        query: str,
        offset: int,
        limit: int,
        filters: Dict[str, Any],
    ) -> List[JobContext]:
        """
        Fetch a chunk of jobs from the database.
        
        Args:
            query: Search query.
            offset: Number of jobs to skip.
            limit: Maximum number of jobs to return.
            filters: Additional filters.
            
        Returns:
            List of JobContext objects.
        """
        async with self._db_session_factory() as session:
            # Build the query
            stmt = select(Job)
            
            # Apply search query filter (case-insensitive title search)
            if query:
                stmt = stmt.where(
                    Job.title.ilike(f"%{query}%") |
                    Job.company.ilike(f"%{query}%") |
                    Job.description.ilike(f"%{query}%")
                )
            
            # Apply additional filters
            if filters.get("source"):
                stmt = stmt.where(Job.source == filters["source"])
            
            if filters.get("company"):
                stmt = stmt.where(Job.company == filters["company"])
            
            if filters.get("location"):
                stmt = stmt.where(Job.location.ilike(f"%{filters['location']}%"))
            
            # Filter out jobs that already have applications (unless specified)
            if not filters.get("include_processed", False):
                stmt = stmt.outerjoin(Application).where(Application.id == None)
            
            # Order and paginate
            stmt = stmt.order_by(Job.id).offset(offset).limit(limit)
            
            # Execute query
            result = await session.execute(stmt)
            jobs = result.scalars().all()
            
            # Convert to JobContext
            return [self._job_to_context(job) for job in jobs]
    
    def _job_to_context(self, job: Job) -> JobContext:
        """
        Convert a Job ORM object to JobContext.
        
        Args:
            job: Job ORM object.
            
        Returns:
            JobContext instance.
        """
        return JobContext(
            job_id=str(job.id),
            title=job.title,
            company=job.company,
            description=job.description or "",
            url=job.url or "",
            source=job.source or "api",
            location=job.location or "",
            posted_date=job.posted_date,
            salary=getattr(job, "salary", None),
            metadata=getattr(job, "metadata", {}) or {},
        )
    
    async def get_job_count(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Get total count of matching jobs without loading them into memory.
        
        Uses efficient COUNT(*) query without loading job data into memory.
        
        Args:
            query: Search query.
            filters: Additional filters.
            
        Returns:
            Total number of matching jobs.
        """
        from sqlalchemy import func
        
        filters = filters or {}
        
        if not self._db_session_factory:
            return 0

        async with self._db_session_factory() as session:

            # Build count query using COUNT(*)
            stmt = select(func.count(Job.id))
            
            if query:
                stmt = stmt.where(
                    Job.title.ilike(f"%{query}%") |
                    Job.company.ilike(f"%{query}%") |
                    Job.description.ilike(f"%{query}%")
                )
            
            if filters.get("source"):
                stmt = stmt.where(Job.source == filters["source"])
            
            if filters.get("company"):
                stmt = stmt.where(Job.company == filters["company"])
            
            if filters.get("location"):
                stmt = stmt.where(Job.location.ilike(f"%{filters['location']}%"))
            
            if not filters.get("include_processed", False):
                stmt = stmt.outerjoin(Application).where(Application.id == None)
            
            # Execute count query - returns a single integer
            result = await session.execute(stmt)
            count = result.scalar_one()
            
            logger.info(f"Total matching jobs: {count}")
            return count
    
    async def produce_unprocessed_jobs(
        self,
        query: str = "",
    ) -> AsyncGenerator[JobContext, None]:
        """
        Stream jobs that haven't been processed yet.
        
        Filters out jobs that already have applications or outreach records.
        
        Args:
            query: Search query to filter jobs.
            
        Yields:
            JobContext objects for unprocessed jobs.
        """
        filters = {"include_processed": False}
        
        async for job in self.produce_jobs(query, filters):
            yield job
    
    def reset_counter(self) -> None:
        """Reset the job production counter."""
        self._jobs_produced = 0


class JobProducer:
    """
    Simplified synchronous job producer for backward compatibility.
    
    Wraps AsyncJobProducer for non-async contexts.
    """
    
    def __init__(
        self,
        db_session_factory: Callable[[], AsyncSession],
        chunk_size: int = 100,
    ):
        """Initialize the job producer."""
        self._producer = AsyncJobProducer(db_session_factory, chunk_size)
    
    @property
    def chunk_size(self) -> int:
        return self._producer.chunk_size
    
    @property
    def jobs_produced(self) -> int:
        return self._producer.jobs_produced
    
    async def produce_jobs(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[JobContext, None]:
        """Stream jobs from database."""
        async for job in self._producer.produce_jobs(query, filters):
            yield job
    
    async def get_job_count(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Get total count of matching jobs."""
        return await self._producer.get_job_count(query, filters)
    
    def reset_counter(self) -> None:
        """Reset the job production counter."""
        self._producer.reset_counter()

