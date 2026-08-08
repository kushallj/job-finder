"""
Types and data models for the async job pipeline.

This module provides immutable job context and processing result types
following the design specification for the async pipeline.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Status of a job in the processing pipeline."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass(frozen=True)
class JobContext:
    """
    Immutable job context passed through the pipeline.
    
    Frozen dataclass ensures no accidental mutations during processing.
    All fields are required except metadata which defaults to empty dict.
    """
    job_id: str
    title: str
    company: str
    description: str
    url: str
    source: str
    location: str = ""
    posted_date: Optional[datetime] = None
    salary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate job context after initialization."""
        if not self.job_id or not self.job_id.strip():
            raise ValueError("job_id cannot be empty")
        if not self.title or not self.title.strip():
            raise ValueError("title cannot be empty")
        if not self.company or not self.company.strip():
            raise ValueError("company cannot be empty")
        if len(self.description) < 50:
            logger.warning(
                f"Job {self.job_id} description is shorter than 50 characters"
            )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobContext":
        """Create JobContext from a dictionary."""
        return cls(
            job_id=data.get("job_id", ""),
            title=data.get("title", ""),
            company=data.get("company", ""),
            description=data.get("description", ""),
            url=data.get("url", ""),
            source=data.get("source", "api"),
            location=data.get("location", ""),
            posted_date=data.get("posted_date"),
            salary=data.get("salary"),
            metadata=data.get("metadata", {}),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "title": self.title,
            "company": self.company,
            "description": self.description,
            "url": self.url,
            "source": self.source,
            "location": self.location,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "salary": self.salary,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "JobContext":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class ProcessingResult:
    """
    Result of job processing with status and metrics.
    
    This dataclass is mutable to allow setting results after processing.
    """
    job_id: str
    status: JobStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    attempt_count: int = 1
    processing_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    worker_id: str = ""
    
    def __post_init__(self):
        """Validate processing result after initialization."""
        if self.status == JobStatus.FAILED and not self.error:
            raise ValueError("Failed status requires an error message")
        if self.status == JobStatus.COMPLETED and not self.data:
            raise ValueError("Completed status requires data")
        if self.attempt_count < 1:
            raise ValueError("attempt_count must be positive")
        if self.processing_time_ms < 0:
            raise ValueError("processing_time_ms must be non-negative")
    
    def is_success(self) -> bool:
        """Check if processing was successful."""
        return self.status == JobStatus.COMPLETED
    
    def is_retryable(self) -> bool:
        """Check if error is retryable."""
        return self.status == JobStatus.RETRYING
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "error_type": self.error_type,
            "attempt_count": self.attempt_count,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "worker_id": self.worker_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingResult":
        """Create ProcessingResult from a dictionary."""
        return cls(
            job_id=data["job_id"],
            status=JobStatus(data.get("status", "pending")),
            data=data.get("data"),
            error=data.get("error"),
            error_type=data.get("error_type"),
            attempt_count=data.get("attempt_count", 1),
            processing_time_ms=data.get("processing_time_ms", 0.0),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            worker_id=data.get("worker_id", ""),
        )
    
    @classmethod
    def success(
        cls,
        job_id: str,
        data: Dict[str, Any],
        attempt_count: int = 1,
        processing_time_ms: float = 0.0,
        worker_id: str = "",
    ) -> "ProcessingResult":
        """Factory method for successful results."""
        return cls(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            data=data,
            attempt_count=attempt_count,
            processing_time_ms=processing_time_ms,
            worker_id=worker_id,
        )
    
    @classmethod
    def failure(
        cls,
        job_id: str,
        error: str,
        error_type: Optional[str] = None,
        attempt_count: int = 1,
        worker_id: str = "",
    ) -> "ProcessingResult":
        """Factory method for failed results."""
        return cls(
            job_id=job_id,
            status=JobStatus.FAILED,
            error=error,
            error_type=error_type,
            attempt_count=attempt_count,
            worker_id=worker_id,
        )


@dataclass
class QueueStats:
    """Statistics for the bounded queue."""
    items_put: int = 0
    items_get: int = 0
    items_failed: int = 0
    backpressure_events: int = 0
    total_wait_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkerPoolStats:
    """Statistics for the worker pool."""
    workers_active: int = 0
    workers_total: int = 0
    jobs_processed: int = 0
    jobs_failed: int = 0
    jobs_retried: int = 0
    total_processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RetryStats:
    """Statistics for retry operations."""
    total_attempts: int = 0
    successful_retries: int = 0
    failed_retries: int = 0
    total_delay_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RateLimiterStats:
    """Statistics for rate limiting."""
    tokens_consumed: int = 0  # Total tokens consumed (same as tokens_acquired)
    requests_blocked: int = 0  # Number of times requests had to wait
    total_wait_time_ms: float = 0.0  # Total time spent waiting
    tokens_acquired: int = 0  # Alias for tokens_consumed for backwards compatibility
    wait_events: int = 0  # Alias for requests_blocked for backwards compatibility
    
    @property
    def average_wait_time_ms(self) -> float:
        """Calculate average wait time per blocked request."""
        if self.requests_blocked == 0:
            return 0.0
        return self.total_wait_time_ms / self.requests_blocked
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["average_wait_time_ms"] = self.average_wait_time_ms
        return data


@dataclass
class PipelineStats:
    """Overall pipeline statistics."""
    jobs_queued: int = 0
    jobs_completed: int = 0
    jobs_failed: int = 0
    start_time: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    end_time: Optional[float] = None
    
    @property
    def elapsed_seconds(self) -> float:
        end = self.end_time or datetime.utcnow().timestamp()
        return end - self.start_time
    
    @property
    def throughput(self) -> float:
        elapsed = self.elapsed_seconds
        if elapsed == 0:
            return 0.0
        return self.jobs_completed / elapsed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "jobs_queued": self.jobs_queued,
            "jobs_completed": self.jobs_completed,
            "jobs_failed": self.jobs_failed,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "throughput_jobs_per_second": round(self.throughput, 2),
        }

