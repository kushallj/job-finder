"""
AsyncJobProcessor - Core processing logic for individual jobs.

This module implements the async job processor that handles skill extraction,
resume matching, and result storage with retry logic, rate limiting, and
structured logging.

Responsibilities:
- Process individual jobs through the complete pipeline
- Call LLM API for skill extraction and matching
- Store results in database with per-task sessions
- Implement retry logic with exponential backoff
- Respect semaphore limits for rate control
- Log all operations with structured logging
- Handle errors gracefully and return ProcessingResult
"""

import asyncio
import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.async_pipeline import set_correlation_id, generate_correlation_id, get_correlation_id, get_logger
from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.retry import retry_on_api_error, retry_on_db_error
from src.async_pipeline.types import JobContext, JobStatus, ProcessingResult
from src.models import Job, Application

# Use structured logger
logger = get_logger(__name__)


class AsyncJobProcessor:
    """
    Core processing logic for a single job with retry, rate limiting, and error handling.
    
    This processor implements the full job processing pipeline:
    1. Extract skills from job description using LLM
    2. Match resume against job requirements
    3. Store results in database
    
    All external API calls are protected by semaphores for rate limiting,
    and use retry logic with exponential backoff for transient failures.
    
    Example:
        processor = AsyncJobProcessor(
            llm_service=llm,
            email_service=email,
            scraper_service=scraper,
            db_session_factory=session_factory,
            config=config
        )
        
        result = await processor.process_job(job, semaphore)
    """
    
    def __init__(
        self,
        config: Optional[ProcessorConfig] = None,
        resume_text: Optional[str] = None,
        llm_service: Optional[Any] = None,
        email_service: Optional[Any] = None,
        scraper_service: Optional[Any] = None,
        db_session_factory: Optional[Callable] = None,
    ):
        """
        Initialize the async job processor.
        
        Args:
            config: Processor configuration (uses defaults if not provided)
            resume_text: Resume text for matching. If None, loads from config path.
            llm_service: LLM service instance (optional, will be lazy-loaded)
            email_service: Email service instance (optional, will be lazy-loaded)
            scraper_service: Scraper service instance (optional, will be lazy-loaded)
            db_session_factory: Factory for async database sessions (optional)
        """
        self.config = config or ProcessorConfig()
        self.llm_service = llm_service
        self.email_service = email_service
        self.scraper_service = scraper_service
        self.db_session_factory = db_session_factory
        
        # Load resume content for matching
        if resume_text:
            self._resume_text = resume_text
        else:
            self._resume_text = self._load_resume()
    
    def _load_resume(self) -> str:
        """Load resume text from file for matching operations."""
        try:
            from pathlib import Path
            resume_path = Path(self.config.resume_pdf_path)
            
            # Try to load the text version first
            resume_txt_path = resume_path.with_suffix('.txt')
            if resume_txt_path.exists():
                return resume_txt_path.read_text(encoding='utf-8')
            
            # Fallback: try to extract text from PDF if available
            if resume_path.exists() and resume_path.suffix == '.pdf':
                try:
                    import PyPDF2
                    with open(resume_path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        text = []
                        for page in pdf_reader.pages:
                            text.append(page.extract_text())
                        return '\n'.join(text)
                except ImportError:
                    logger.warning("resume_load_warning", message="PyPDF2 not available, cannot extract resume text from PDF")
                except Exception as e:
                    logger.warning("resume_extraction_failed", error_message=str(e))
            
            # Last resort: return placeholder
            logger.warning("resume_not_found", path=str(resume_path), message="Using placeholder")
            return "Resume content not available. Please add resume.txt or resume.pdf to data/ directory."
            
        except Exception as e:
            logger.error("resume_load_error", error_type=type(e).__name__, error_message=str(e))
            return "Resume loading failed."
    
    @retry_on_api_error(max_attempts=3, base_delay=1.0, max_delay=60.0)
    async def process_job(
        self,
        job: JobContext,
        semaphore: asyncio.Semaphore,
    ) -> ProcessingResult:
        """
        Process a single job through the complete pipeline.
        
        This method is decorated with retry logic that will automatically
        retry on transient API errors with exponential backoff.
        
        Pipeline steps:
        1. Extract skills from job description
        2. Match resume against job requirements
        3. Store results in database
        
        Args:
            job: Job context to process
            semaphore: Concurrency limiter for external API calls
            
        Returns:
            ProcessingResult with status and data
            
        Note:
            This method never raises exceptions - all errors are caught
            and returned in the ProcessingResult with status=FAILED.
        """
        # Set correlation ID for tracing this job through the pipeline
        correlation_id = f"job-{job.job_id}-{generate_correlation_id()[:8]}"
        set_correlation_id(correlation_id)
        
        start_time = time.time()
        attempt_count = 1  # Will be updated by retry decorator
        
        # Extract attempt count from retry context if available
        try:
            import sys
            frame = sys._getframe()
            # Look for tenacity retry state in the call stack
            while frame:
                if 'retry_state' in frame.f_locals:
                    retry_state = frame.f_locals['retry_state']
                    attempt_count = getattr(retry_state, 'attempt_number', 1)
                    break
                frame = frame.f_back
        except:
            pass  # If we can't get attempt count, use default of 1
        
        logger.info(
            "job_processing_started",
            job_id=job.job_id,
            company=job.company,
            title=job.title,
            status=JobStatus.PROCESSING.value,
            attempt_count=attempt_count,
            correlation_id=correlation_id,
        )
        
        try:
            # Step 1: Extract skills from job description
            skills = await self.extract_skills(job.description, semaphore)
            
            logger.debug(
                "skills_extracted",
                job_id=job.job_id,
                skills_count=len(skills),
                correlation_id=correlation_id,
            )
            
            # Step 2: Match resume to job
            match_result = await self.match_resume(skills, job, semaphore)
            
            logger.debug(
                "resume_matched",
                job_id=job.job_id,
                match_score=match_result.get("match_score", 0),
                correlation_id=correlation_id,
            )
            
            # Step 3: Store result in database
            await self.store_result(job, match_result, semaphore)
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                "job_completed",
                job_id=job.job_id,
                status=JobStatus.COMPLETED.value,
                processing_time_ms=round(processing_time_ms, 2),
                attempt_count=attempt_count,
                correlation_id=correlation_id,
            )
            
            return ProcessingResult.success(
                job_id=job.job_id,
                data=match_result,
                attempt_count=attempt_count,
                processing_time_ms=processing_time_ms,
                worker_id="",  # Will be set by worker
            )
            
        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            error_type = type(e).__name__
            error_message = str(e)
            error_traceback = traceback.format_exc()
            
            logger.error(
                "job_failed",
                job_id=job.job_id,
                status=JobStatus.FAILED.value,
                error_type=error_type,
                error_message=error_message,
                traceback=error_traceback,
                processing_time_ms=round(processing_time_ms, 2),
                attempt_count=attempt_count,
                correlation_id=correlation_id,
            )
            
            return ProcessingResult.failure(
                job_id=job.job_id,
                error=error_message,
                error_type=error_type,
                attempt_count=attempt_count,
                worker_id="",  # Will be set by worker
            )
    
    async def extract_skills(
        self,
        description: str,
        semaphore: Optional[asyncio.Semaphore] = None,
    ) -> List[str]:
        """
        Extract skills from job description using LLM API.
        
        This method calls the LLM service to analyze the job description
        and extract required technical skills and qualifications.
        
        Args:
            description: Job description text
            semaphore: Optional semaphore for rate limiting
            
        Returns:
            List of extracted skill strings
            
        Raises:
            Exception: If LLM API call fails after retries
        """
        operation_start = time.time()
        correlation_id = get_correlation_id()
        
        # Acquire semaphore before external API call
        if semaphore:
            await semaphore.acquire()
        
        try:
            logger.debug(
                "llm_extract_skills_start",
                description_length=len(description),
                correlation_id=correlation_id,
            )
            
            # Call LLM service with timeout
            try:
                skills = await asyncio.wait_for(
                    self.llm_service.extract_skills(description),
                    timeout=self.config.llm_timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "llm_extract_skills_timeout",
                    timeout_seconds=self.config.llm_timeout_seconds,
                    correlation_id=correlation_id,
                )
                raise
            
            duration_ms = (time.time() - operation_start) * 1000
            
            logger.debug(
                "llm_extract_skills_complete",
                skills_count=len(skills),
                processing_time_ms=round(duration_ms, 2),
                correlation_id=correlation_id,
            )
            
            return skills
            
        finally:
            # Always release semaphore, even on exception
            if semaphore:
                semaphore.release()
    
    async def match_resume(
        self,
        skills: List[str],
        job: JobContext,
        semaphore: Optional[asyncio.Semaphore] = None,
    ) -> Dict[str, Any]:
        """
        Match resume against job requirements using LLM.
        
        This method uses the LLM service to analyze how well the resume
        matches the extracted job skills and requirements.
        
        Args:
            skills: List of required skills extracted from job
            job: Job context with full job information
            semaphore: Optional semaphore for rate limiting
            
        Returns:
            Dictionary with match results:
            {
                "match_score": int (0-100),
                "matched_skills": List[str],
                "missing_skills": List[str],
                "recommendations": str,
            }
            
        Raises:
            Exception: If LLM API call fails after retries
        """
        operation_start = time.time()
        correlation_id = get_correlation_id()
        
        # Acquire semaphore before external API call
        if semaphore:
            await semaphore.acquire()
        
        try:
            logger.debug(
                "llm_match_resume_start",
                job_id=job.job_id,
                skills_count=len(skills),
                correlation_id=correlation_id,
            )
            
            # Call LLM service with timeout
            try:
                match_result = await asyncio.wait_for(
                    self.llm_service.match_resume_to_job(self._resume_text, skills),
                    timeout=self.config.llm_timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "llm_match_resume_timeout",
                    job_id=job.job_id,
                    timeout_seconds=self.config.llm_timeout_seconds,
                    correlation_id=correlation_id,
                )
                raise
            
            duration_ms = (time.time() - operation_start) * 1000
            
            logger.debug(
                "llm_match_resume_complete",
                job_id=job.job_id,
                match_score=match_result.get("match_score", 0),
                processing_time_ms=round(duration_ms, 2),
                correlation_id=correlation_id,
            )
            
            # Ensure the result has all required fields
            return {
                "match_score": match_result.get("match_score", 0),
                "matched_skills": match_result.get("matched_skills", []),
                "missing_skills": match_result.get("missing_skills", skills),
                "recommendations": match_result.get("recommendations", ""),
                "job_id": job.job_id,
                "job_title": job.title,
                "company": job.company,
            }
            
        finally:
            # Always release semaphore, even on exception
            if semaphore:
                semaphore.release()
    
    @retry_on_db_error(max_attempts=3, base_delay=0.5, max_delay=10.0)
    async def store_result(
        self,
        job: JobContext,
        result: Dict[str, Any],
        semaphore: Optional[asyncio.Semaphore] = None,
    ) -> None:
        """
        Store processing result in database using per-task session with transaction.
        
        This method creates a new database session for this specific task,
        wraps all operations in a transaction, and ensures proper rollback
        on errors. All database operations are protected by a timeout wrapper.
        
        Args:
            job: Job context
            result: Processing result data to store
            semaphore: Optional semaphore for rate limiting
            
        Raises:
            Exception: If database operation fails after retries
            asyncio.TimeoutError: If database operation exceeds timeout
        """
        operation_start = time.time()
        correlation_id = get_correlation_id()
        
        # Acquire semaphore if provided (though database operations typically
        # don't need rate limiting, we respect the semaphore if passed)
        if semaphore:
            await semaphore.acquire()
        
        try:
            logger.debug(
                "db_store_result_start",
                job_id=job.job_id,
                correlation_id=correlation_id,
            )
            
            # Wrap entire database operation in timeout
            try:
                await asyncio.wait_for(
                    self._store_result_transaction(job, result, operation_start),
                    timeout=self.config.db_timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "db_store_result_timeout",
                    job_id=job.job_id,
                    timeout_seconds=self.config.db_timeout_seconds,
                    correlation_id=correlation_id,
                )
                raise
                    
        finally:
            # Always release semaphore, even on exception
            if semaphore:
                semaphore.release()
    
    async def send_outreach_email(
        self,
        job: JobContext,
        contact_email: str,
        email_content: str,
        semaphore: Optional[asyncio.Semaphore] = None,
    ) -> Dict[str, Any]:
        """
        Send outreach email with timeout protection.
        
        Args:
            job: Job context
            contact_email: Recipient email address
            email_content: Email body content
            semaphore: Optional semaphore for rate limiting
            
        Returns:
            Dictionary with email send result
            
        Raises:
            Exception: If email sending fails after retries
            asyncio.TimeoutError: If email operation exceeds timeout
        """
        operation_start = time.time()
        correlation_id = get_correlation_id()
        
        # Acquire semaphore before external API call
        if semaphore:
            await semaphore.acquire()
        
        try:
            logger.debug(
                "email_send_start",
                job_id=job.job_id,
                recipient=contact_email,
                correlation_id=correlation_id,
            )
            
            # Call email service with timeout
            try:
                result = await asyncio.wait_for(
                    self.email_service.send_email(
                        to_email=contact_email,
                        subject=f"Application for {job.title} at {job.company}",
                        body=email_content,
                    ),
                    timeout=self.config.email_timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "email_send_timeout",
                    job_id=job.job_id,
                    timeout_seconds=self.config.email_timeout_seconds,
                    correlation_id=correlation_id,
                )
                raise
            
            duration_ms = (time.time() - operation_start) * 1000
            
            logger.info(
                "email_send_complete",
                job_id=job.job_id,
                processing_time_ms=round(duration_ms, 2),
                correlation_id=correlation_id,
            )
            
            return result
            
        finally:
            # Always release semaphore, even on exception
            if semaphore:
                semaphore.release()
    
    async def scrape_job_details(
        self,
        job_url: str,
        semaphore: Optional[asyncio.Semaphore] = None,
    ) -> Dict[str, Any]:
        """
        Scrape additional job details with timeout protection.
        
        Args:
            job_url: URL to scrape
            semaphore: Optional semaphore for rate limiting
            
        Returns:
            Dictionary with scraped job data
            
        Raises:
            Exception: If scraping fails after retries
            asyncio.TimeoutError: If scraping operation exceeds timeout
        """
        operation_start = time.time()
        correlation_id = get_correlation_id()
        
        # Acquire semaphore before external operation
        if semaphore:
            await semaphore.acquire()
        
        try:
            logger.debug(
                "scrape_job_start",
                url=job_url,
                correlation_id=correlation_id,
            )
            
            # Call scraper service with timeout
            try:
                result = await asyncio.wait_for(
                    self.scraper_service.scrape_job(job_url),
                    timeout=self.config.scraper_timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "scrape_job_timeout",
                    url=job_url,
                    timeout_seconds=self.config.scraper_timeout_seconds,
                    correlation_id=correlation_id,
                )
                raise
            
            duration_ms = (time.time() - operation_start) * 1000
            
            logger.debug(
                "scrape_job_complete",
                url=job_url,
                processing_time_ms=round(duration_ms, 2),
                correlation_id=correlation_id,
            )
            
            return result
            
        finally:
            # Always release semaphore, even on exception
            if semaphore:
                semaphore.release()
    
    async def _store_result_transaction(
        self,
        job: JobContext,
        result: Dict[str, Any],
        operation_start: float,
    ) -> None:
        """
        Internal method to perform the database transaction.
        Separated for timeout wrapping.
        
        This method implements per-task database session management with explicit
        transaction control. Each call creates a new session to ensure complete
        isolation between workers. The transaction is automatically committed when
        exiting the context manager on success, or rolled back on any exception.
        
        Args:
            job: Job context
            result: Processing result data to store
            operation_start: Timestamp when operation started
            
        Raises:
            Exception: Database errors are propagated after logging and rollback
        """
        correlation_id = get_correlation_id()
        
        # Create NEW per-task database session for complete isolation
        # Each worker gets its own session, preventing shared state
        async with self.db_session_factory() as session:
            try:
                # Begin explicit transaction - commit/rollback handled automatically
                # by context manager on exit
                async with session.begin():
                    # Find existing job or create new one
                    stmt = select(Job).where(Job.job_id == job.job_id)
                    db_result = await session.execute(stmt)
                    db_job = db_result.scalar_one_or_none()
                    
                    if not db_job:
                        # Create new job record
                        db_job = Job(
                            job_id=job.job_id,
                            title=job.title,
                            company=job.company,
                            location=job.location,
                            description=job.description,
                            url=job.url,
                            source=job.source,
                            posted_date=job.posted_date,
                        )
                        session.add(db_job)
                        await session.flush()  # Get the job ID
                    
                    # Create or update application record
                    import json
                    application = Application(
                        job_id=db_job.id,
                        match_score=result.get("match_score", 0),
                        skills_matched=json.dumps(result.get("matched_skills", [])),
                        skills_missing=json.dumps(result.get("missing_skills", [])),
                        status="pending",
                    )
                    session.add(application)
                    
                    # Transaction commits automatically when exiting context manager
                    # No explicit commit() needed - this ensures proper transaction handling
                
                # Transaction committed successfully - log outside transaction block
                duration_ms = (time.time() - operation_start) * 1000
                
                logger.info(
                    "db_store_result_complete",
                    job_id=job.job_id,
                    match_score=result.get("match_score", 0),
                    processing_time_ms=round(duration_ms, 2),
                    correlation_id=correlation_id,
                )
                    
            except Exception as e:
                # Rollback is automatic with async context manager when exception occurs
                # Session is also automatically closed via outer context manager
                error_traceback = traceback.format_exc()
                logger.error(
                    "db_transaction_failed",
                    job_id=job.job_id,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    traceback=error_traceback,
                    correlation_id=correlation_id,
                )
                raise
            # Session cleanup happens automatically in finally block of context manager
