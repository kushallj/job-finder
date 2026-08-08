"""
Synchronous wrapper for the async job pipeline.

This module provides backward compatibility for code that expects synchronous interfaces.
It allows existing synchronous code to use the new async pipeline without modification.

Example:
    # Old synchronous code
    from src.job_processor import JobProcessor
    processor = JobProcessor()
    await processor.run("software engineer", resume_text)
    
    # New code with sync wrapper
    from src.async_pipeline.sync_wrapper import SyncJobPipelineWrapper
    pipeline = SyncJobPipelineWrapper()
    pipeline.run_sync("software engineer", resume_text)
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from src.async_pipeline.config import ProcessorConfig
from src.async_pipeline.pipeline import AsyncJobPipeline
from src.async_pipeline.types import JobContext, ProcessingResult

logger = logging.getLogger(__name__)


class SyncJobPipelineWrapper:
    """
    Synchronous wrapper around AsyncJobPipeline.
    
    Provides a synchronous interface to the async pipeline by running
    async operations in an event loop using asyncio.run().
    
    This is intended for backward compatibility with existing synchronous code.
    For new code, prefer using AsyncJobPipeline directly with async/await.
    
    Example:
        wrapper = SyncJobPipelineWrapper(config)
        wrapper.set_processor(my_processor)
        results = wrapper.run_sync(query="python developer", resume_text=resume)
        wrapper.close_sync()
    """
    
    def __init__(
        self,
        config: Optional[ProcessorConfig] = None,
        db_url: Optional[str] = None,
    ):
        """
        Initialize the sync wrapper.
        
        Args:
            config: Processor configuration. Uses defaults if not provided.
            db_url: Database URL. Reads from settings if not provided.
        """
        self._config = config or ProcessorConfig()
        self._db_url = db_url
        self._pipeline: Optional[AsyncJobPipeline] = None
        self._processor: Optional[Callable] = None
        
        logger.info("SyncJobPipelineWrapper initialized")
    
    def _ensure_pipeline(self) -> AsyncJobPipeline:
        """Ensure pipeline is initialized (lazy initialization)."""
        if self._pipeline is None:
            self._pipeline = AsyncJobPipeline(
                config=self._config,
                db_url=self._db_url,
            )
            if self._processor:
                self._pipeline.set_processor(self._processor)
        return self._pipeline
    
    def set_processor(self, processor: Callable[[JobContext], ProcessingResult]) -> None:
        """
        Set the job processor function.
        
        Args:
            processor: Async callable that processes JobContext and returns ProcessingResult.
        """
        self._processor = processor
        if self._pipeline:
            self._pipeline.set_processor(processor)
        logger.info("Job processor set")
    
    def set_progress_callback(self, callback: Callable[[Dict], None]) -> None:
        """
        Set a callback for progress updates.
        
        Args:
            callback: Function that receives progress dict.
        """
        pipeline = self._ensure_pipeline()
        pipeline.set_progress_callback(callback)
    
    def enable_progress_display(self, enable: bool = True) -> None:
        """
        Enable or disable rich progress display.
        
        Args:
            enable: True to enable progress display, False to disable.
        """
        pipeline = self._ensure_pipeline()
        pipeline.enable_progress_display(enable)
    
    def run_sync(
        self,
        query: str = "",
        resume_text: str = "",
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ProcessingResult]:
        """
        Run the pipeline synchronously.
        
        This method blocks until the pipeline completes and returns results.
        
        Args:
            query: Search query to filter jobs.
            resume_text: Resume text for job matching.
            filters: Additional filters for job selection.
            
        Returns:
            List of ProcessingResult for all processed jobs.
        """
        pipeline = self._ensure_pipeline()
        
        try:
            # Run the async pipeline in a new event loop
            return asyncio.run(pipeline.run(query, resume_text, filters))
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            raise
    
    def close_sync(self) -> None:
        """
        Close the pipeline synchronously.
        
        Cleans up all resources and closes connections.
        """
        if self._pipeline:
            try:
                asyncio.run(self._pipeline.close())
            except Exception as e:
                logger.error(f"Error closing pipeline: {e}")
            finally:
                self._pipeline = None
        
        logger.info("SyncJobPipelineWrapper closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.
        
        Returns:
            Dictionary with pipeline statistics.
        """
        if self._pipeline:
            return self._pipeline.stats.to_dict()
        return {}
    
    def get_metrics_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Get current metrics snapshot.
        
        Returns:
            Dictionary with current metrics, or None if not available.
        """
        if self._pipeline:
            snapshot = self._pipeline.get_metrics_snapshot()
            if snapshot:
                return snapshot.to_dict()
        return None


def run_pipeline_sync(
    query: str,
    processor: Callable[[JobContext], ProcessingResult],
    config: Optional[ProcessorConfig] = None,
    db_url: Optional[str] = None,
    resume_text: str = "",
    filters: Optional[Dict[str, Any]] = None,
) -> List[ProcessingResult]:
    """
    Convenience function to run a pipeline synchronously.
    
    Creates a pipeline, runs it, and returns results.
    All async operations are handled internally.
    
    Args:
        query: Search query for jobs.
        processor: Job processor function.
        config: Optional processor configuration.
        db_url: Optional database URL.
        resume_text: Optional resume text.
        filters: Optional job filters.
        
    Returns:
        List of ProcessingResult.
        
    Example:
        results = run_pipeline_sync(
            query="python developer",
            processor=my_processor,
            resume_text=open("resume.txt").read()
        )
    """
    wrapper = SyncJobPipelineWrapper(config=config, db_url=db_url)
    wrapper.set_processor(processor)
    
    try:
        return wrapper.run_sync(query=query, resume_text=resume_text, filters=filters)
    finally:
        wrapper.close_sync()


class JobProcessorCompatWrapper:
    """
    Compatibility wrapper that mimics the old JobProcessor interface.
    
    This allows existing code using JobProcessor to switch to the async
    pipeline with minimal changes.
    
    Example:
        # Old code
        from src.job_processor import JobProcessor
        processor = JobProcessor()
        await processor.run("software engineer", resume_text)
        
        # New code with compat wrapper
        from src.async_pipeline.sync_wrapper import JobProcessorCompatWrapper
        processor = JobProcessorCompatWrapper()
        await processor.run("software engineer", resume_text)
    """
    
    def __init__(self, config: Optional[ProcessorConfig] = None):
        """
        Initialize the compatibility wrapper.
        
        Args:
            config: Optional processor configuration.
        """
        self._wrapper = SyncJobPipelineWrapper(config=config)
        logger.info("JobProcessorCompatWrapper initialized")
    
    async def run(self, query: str = "software engineer", resume_text: str = "") -> Dict[str, Any]:
        """
        Run the pipeline (async interface).
        
        Args:
            query: Search query for jobs.
            resume_text: Resume text for matching.
            
        Returns:
            Dictionary with metrics similar to old JobProcessor.
        """
        results = self._wrapper.run_sync(query=query, resume_text=resume_text)
        stats = self._wrapper.get_stats()
        
        return {
            "jobs_processed": stats.get("jobs_completed", 0) + stats.get("jobs_failed", 0),
            "jobs_completed": stats.get("jobs_completed", 0),
            "jobs_failed": stats.get("jobs_failed", 0),
            "results": results,
        }
    
    def run_sync(self, query: str = "software engineer", resume_text: str = "") -> Dict[str, Any]:
        """
        Run the pipeline (synchronous interface).
        
        Args:
            query: Search query for jobs.
            resume_text: Resume text for matching.
            
        Returns:
            Dictionary with metrics similar to old JobProcessor.
        """
        results = self._wrapper.run_sync(query=query, resume_text=resume_text)
        stats = self._wrapper.get_stats()
        
        return {
            "jobs_processed": stats.get("jobs_completed", 0) + stats.get("jobs_failed", 0),
            "jobs_completed": stats.get("jobs_completed", 0),
            "jobs_failed": stats.get("jobs_failed", 0),
            "results": results,
        }
    
    async def close(self) -> None:
        """Close the wrapper (async interface)."""
        self._wrapper.close_sync()
    
    def close_sync(self) -> None:
        """Close the wrapper (synchronous interface)."""
        self._wrapper.close_sync()
