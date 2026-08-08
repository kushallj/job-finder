"""
Metrics collection system for the async job pipeline.

This module provides comprehensive metrics tracking for monitoring:
- Job processing counts (total, success, failure)
- Processing times (min, avg, max)
- Queue metrics (size over time)
- Worker metrics (active workers, semaphore availability)
- API call latencies per service (LLM, email, scraping)
- Retry rates per error type

All metrics are collected in a structured format suitable for export to
monitoring tools like Prometheus, Datadog, or CloudWatch.

Requirements covered: 20.1, 20.2, 20.3, 20.4, 20.5
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from threading import Lock

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics tracked by the system."""
    COUNTER = "counter"  # Monotonically increasing value
    GAUGE = "gauge"      # Value that can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"      # Duration measurements


class ServiceType(Enum):
    """External services whose latencies are tracked."""
    LLM = "llm"
    EMAIL = "email"
    SCRAPING = "scraping"
    DATABASE = "database"


@dataclass
class LatencyMetrics:
    """Latency metrics for a specific service or operation."""
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float('inf')
    max_ms: float = 0.0
    
    def record(self, duration_ms: float) -> None:
        """Record a new latency measurement."""
        self.count += 1
        self.total_ms += duration_ms
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)
    
    @property
    def avg_ms(self) -> float:
        """Calculate average latency."""
        if self.count == 0:
            return 0.0
        return self.total_ms / self.count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "count": self.count,
            "total_ms": round(self.total_ms, 2),
            "min_ms": round(self.min_ms, 2) if self.min_ms != float('inf') else 0.0,
            "max_ms": round(self.max_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
        }


@dataclass
class RetryMetrics:
    """Retry metrics per error type."""
    retry_count: int = 0
    success_after_retry: int = 0
    failed_after_retry: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "retry_count": self.retry_count,
            "success_after_retry": self.success_after_retry,
            "failed_after_retry": self.failed_after_retry,
            "success_rate": (
                round(self.success_after_retry / self.retry_count, 3)
                if self.retry_count > 0 else 0.0
            ),
        }


@dataclass
class QueueSnapshot:
    """Snapshot of queue state at a point in time."""
    timestamp: float
    size: int
    active_workers: int
    semaphore_available: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "timestamp": self.timestamp,
            "size": self.size,
            "active_workers": self.active_workers,
            "semaphore_available": self.semaphore_available,
        }


@dataclass
class MetricsSnapshot:
    """
    Complete snapshot of all pipeline metrics.
    
    This is the main export format for monitoring systems.
    """
    # Job processing metrics (Req 6.1, 20.1)
    jobs_total: int = 0
    jobs_success: int = 0
    jobs_failed: int = 0
    
    # Processing time metrics (Req 6.1, 20.2)
    processing_time_min_ms: float = float('inf')
    processing_time_avg_ms: float = 0.0
    processing_time_max_ms: float = 0.0
    processing_time_p50_ms: float = 0.0  # Median
    processing_time_p95_ms: float = 0.0  # 95th percentile
    processing_time_p99_ms: float = 0.0  # 99th percentile
    
    # Queue metrics (Req 6.2, 20.3)
    queue_size_current: int = 0
    queue_size_max: int = 0
    queue_size_avg: float = 0.0
    queue_backpressure_events: int = 0  # Req 6.2: backpressure events
    queue_wait_time_avg_ms: float = 0.0  # Req 6.2: wait times
    queue_wait_time_max_ms: float = 0.0  # Req 6.2: wait times
    
    # Worker metrics (Req 6.3, 20.3)
    workers_active: int = 0
    workers_total: int = 0
    worker_idle_time_total_ms: float = 0.0  # Req 6.3: idle time
    semaphore_available: int = 0
    semaphore_total: int = 0
    
    # API metrics - rate limiter waits and semaphore contention (Req 6.4, 20.4)
    rate_limiter_waits_total: int = 0  # Req 6.4: rate limiter waits
    rate_limiter_wait_time_total_ms: float = 0.0  # Req 6.4: rate limiter wait times
    llm_latency: Dict[str, Any] = field(default_factory=dict)
    email_latency: Dict[str, Any] = field(default_factory=dict)
    scraping_latency: Dict[str, Any] = field(default_factory=dict)
    database_latency: Dict[str, Any] = field(default_factory=dict)
    
    # Retry/Error metrics per error type (Req 6.5, 20.5)
    retry_metrics: Dict[str, Any] = field(default_factory=dict)
    total_retry_attempts: int = 0  # Req 6.5: total retry attempts
    total_errors: int = 0  # Req 6.5: total errors
    error_rate: float = 0.0  # Req 6.5: error rate
    
    # Metadata
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    elapsed_seconds: float = 0.0
    throughput_jobs_per_sec: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return asdict(self)
    
    def to_prometheus_format(self) -> str:
        """
        Export metrics in Prometheus text format.
        
        Includes:
        - Job processing metrics (throughput, latency, success rate) - Req 6.1
        - Queue metrics (size, backpressure events, wait times) - Req 6.2
        - Worker metrics (utilization, active count, idle time) - Req 6.3
        - API metrics (rate limiter waits, semaphore contention) - Req 6.4
        - Error metrics (retry attempts, failure types, error rates) - Req 6.5
        
        Returns:
            String in Prometheus exposition format.
        """
        lines = []
        
        # ═══════════════════════════════════════════════════════════════════════════
        # Job Processing Metrics (Req 6.1: throughput, latency, success rate)
        # ═══════════════════════════════════════════════════════════════════════════
        lines.append("# HELP pipeline_jobs_total Total number of jobs processed")
        lines.append("# TYPE pipeline_jobs_total counter")
        lines.append(f"pipeline_jobs_total {self.jobs_total}")
        
        lines.append("# HELP pipeline_jobs_success Number of successful jobs")
        lines.append("# TYPE pipeline_jobs_success counter")
        lines.append(f"pipeline_jobs_success {self.jobs_success}")
        
        lines.append("# HELP pipeline_jobs_failed Number of failed jobs")
        lines.append("# TYPE pipeline_jobs_failed counter")
        lines.append(f"pipeline_jobs_failed {self.jobs_failed}")
        
        # Success rate
        success_rate = (self.jobs_success / self.jobs_total) if self.jobs_total > 0 else 0.0
        lines.append("# HELP pipeline_job_success_rate Job success rate (0-1)")
        lines.append("# TYPE pipeline_job_success_rate gauge")
        lines.append(f"pipeline_job_success_rate {success_rate:.4f}")
        
        # Throughput (Req 6.1)
        lines.append("# HELP pipeline_throughput_jobs_per_sec Jobs processed per second")
        lines.append("# TYPE pipeline_throughput_jobs_per_sec gauge")
        lines.append(f"pipeline_throughput_jobs_per_sec {self.throughput_jobs_per_sec}")
        
        # Processing time metrics - latency (Req 6.1)
        lines.append("# HELP pipeline_processing_time_min_ms Minimum processing time in milliseconds")
        lines.append("# TYPE pipeline_processing_time_min_ms gauge")
        lines.append(f"pipeline_processing_time_min_ms {self.processing_time_min_ms}")
        
        lines.append("# HELP pipeline_processing_time_avg_ms Average processing time in milliseconds")
        lines.append("# TYPE pipeline_processing_time_avg_ms gauge")
        lines.append(f"pipeline_processing_time_avg_ms {self.processing_time_avg_ms}")
        
        lines.append("# HELP pipeline_processing_time_max_ms Maximum processing time in milliseconds")
        lines.append("# TYPE pipeline_processing_time_max_ms gauge")
        lines.append(f"pipeline_processing_time_max_ms {self.processing_time_max_ms}")
        
        lines.append("# HELP pipeline_processing_time_p50_ms Median (p50) processing time in milliseconds")
        lines.append("# TYPE pipeline_processing_time_p50_ms gauge")
        lines.append(f"pipeline_processing_time_p50_ms {self.processing_time_p50_ms}")
        
        lines.append("# HELP pipeline_processing_time_p95_ms 95th percentile processing time in milliseconds")
        lines.append("# TYPE pipeline_processing_time_p95_ms gauge")
        lines.append(f"pipeline_processing_time_p95_ms {self.processing_time_p95_ms}")
        
        lines.append("# HELP pipeline_processing_time_p99_ms 99th percentile processing time in milliseconds")
        lines.append("# TYPE pipeline_processing_time_p99_ms gauge")
        lines.append(f"pipeline_processing_time_p99_ms {self.processing_time_p99_ms}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # Queue Metrics (Req 6.2: size, backpressure events, wait times)
        # ═══════════════════════════════════════════════════════════════════════════
        lines.append("# HELP pipeline_queue_size_current Current queue size")
        lines.append("# TYPE pipeline_queue_size_current gauge")
        lines.append(f"pipeline_queue_size_current {self.queue_size_current}")
        
        lines.append("# HELP pipeline_queue_size_max Maximum queue size reached")
        lines.append("# TYPE pipeline_queue_size_max gauge")
        lines.append(f"pipeline_queue_size_max {self.queue_size_max}")
        
        lines.append("# HELP pipeline_queue_size_avg Average queue size")
        lines.append("# TYPE pipeline_queue_size_avg gauge")
        lines.append(f"pipeline_queue_size_avg {self.queue_size_avg}")
        
        # Backpressure events (Req 6.2)
        lines.append("# HELP pipeline_queue_backpressure_events_total Total backpressure events when queue was full")
        lines.append("# TYPE pipeline_queue_backpressure_events_total counter")
        lines.append(f"pipeline_queue_backpressure_events_total {self.queue_backpressure_events}")
        
        # Wait times (Req 6.2)
        lines.append("# HELP pipeline_queue_wait_time_avg_ms Average queue wait time in milliseconds")
        lines.append("# TYPE pipeline_queue_wait_time_avg_ms gauge")
        lines.append(f"pipeline_queue_wait_time_avg_ms {self.queue_wait_time_avg_ms}")
        
        lines.append("# HELP pipeline_queue_wait_time_max_ms Maximum queue wait time in milliseconds")
        lines.append("# TYPE pipeline_queue_wait_time_max_ms gauge")
        lines.append(f"pipeline_queue_wait_time_max_ms {self.queue_wait_time_max_ms}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # Worker Metrics (Req 6.3: utilization, active count, idle time)
        # ═══════════════════════════════════════════════════════════════════════════
        lines.append("# HELP pipeline_workers_active Currently active workers")
        lines.append("# TYPE pipeline_workers_active gauge")
        lines.append(f"pipeline_workers_active {self.workers_active}")
        
        lines.append("# HELP pipeline_workers_total Total number of workers")
        lines.append("# TYPE pipeline_workers_total gauge")
        lines.append(f"pipeline_workers_total {self.workers_total}")
        
        # Worker utilization (Req 6.3)
        utilization = (self.workers_active / self.workers_total) if self.workers_total > 0 else 0.0
        lines.append("# HELP pipeline_worker_utilization Worker utilization rate (0-1)")
        lines.append("# TYPE pipeline_worker_utilization gauge")
        lines.append(f"pipeline_worker_utilization {utilization:.4f}")
        
        # Idle time (Req 6.3)
        idle_rate = 1.0 - utilization
        lines.append("# HELP pipeline_worker_idle_rate Worker idle rate (0-1)")
        lines.append("# TYPE pipeline_worker_idle_rate gauge")
        lines.append(f"pipeline_worker_idle_rate {idle_rate:.4f}")
        
        lines.append("# HELP pipeline_worker_idle_time_total_ms Total worker idle time in milliseconds")
        lines.append("# TYPE pipeline_worker_idle_time_total_ms counter")
        lines.append(f"pipeline_worker_idle_time_total_ms {self.worker_idle_time_total_ms}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # API Metrics (Req 6.4: rate limiter waits, semaphore contention)
        # ═══════════════════════════════════════════════════════════════════════════
        lines.append("# HELP pipeline_semaphore_available Available semaphore slots")
        lines.append("# TYPE pipeline_semaphore_available gauge")
        lines.append(f"pipeline_semaphore_available {self.semaphore_available}")
        
        lines.append("# HELP pipeline_semaphore_total Total semaphore slots")
        lines.append("# TYPE pipeline_semaphore_total gauge")
        lines.append(f"pipeline_semaphore_total {self.semaphore_total}")
        
        # Semaphore contention (Req 6.4)
        contention = 1.0 - (self.semaphore_available / self.semaphore_total) if self.semaphore_total > 0 else 0.0
        lines.append("# HELP pipeline_semaphore_contention Semaphore contention rate (0-1)")
        lines.append("# TYPE pipeline_semaphore_contention gauge")
        lines.append(f"pipeline_semaphore_contention {contention:.4f}")
        
        # Rate limiter waits (Req 6.4)
        lines.append("# HELP pipeline_rate_limiter_waits_total Total number of rate limiter wait events")
        lines.append("# TYPE pipeline_rate_limiter_waits_total counter")
        lines.append(f"pipeline_rate_limiter_waits_total {self.rate_limiter_waits_total}")
        
        lines.append("# HELP pipeline_rate_limiter_wait_time_total_ms Total time spent waiting for rate limiter in milliseconds")
        lines.append("# TYPE pipeline_rate_limiter_wait_time_total_ms counter")
        lines.append(f"pipeline_rate_limiter_wait_time_total_ms {self.rate_limiter_wait_time_total_ms}")
        
        # API latency metrics per service (Req 6.4)
        for service_name, latency_dict in [
            ("llm", self.llm_latency),
            ("email", self.email_latency),
            ("scraping", self.scraping_latency),
            ("database", self.database_latency),
        ]:
            if latency_dict and latency_dict.get("count", 0) > 0:
                lines.append(f"# HELP pipeline_api_latency_count_{service_name} Number of API calls to {service_name}")
                lines.append(f"# TYPE pipeline_api_latency_count_{service_name} counter")
                lines.append(f"pipeline_api_latency_count_{service_name} {latency_dict['count']}")
                
                lines.append(f"# HELP pipeline_api_latency_total_ms_{service_name} Total API latency for {service_name} in milliseconds")
                lines.append(f"# TYPE pipeline_api_latency_total_ms_{service_name} counter")
                lines.append(f"pipeline_api_latency_total_ms_{service_name} {latency_dict['total_ms']}")
                
                lines.append(f"# HELP pipeline_api_latency_avg_ms_{service_name} Average API latency for {service_name} in milliseconds")
                lines.append(f"# TYPE pipeline_api_latency_avg_ms_{service_name} gauge")
                lines.append(f"pipeline_api_latency_avg_ms_{service_name} {latency_dict['avg_ms']}")
                
                lines.append(f"# HELP pipeline_api_latency_min_ms_{service_name} Minimum API latency for {service_name} in milliseconds")
                lines.append(f"# TYPE pipeline_api_latency_min_ms_{service_name} gauge")
                lines.append(f"pipeline_api_latency_min_ms_{service_name} {latency_dict['min_ms']}")
                
                lines.append(f"# HELP pipeline_api_latency_max_ms_{service_name} Maximum API latency for {service_name} in milliseconds")
                lines.append(f"# TYPE pipeline_api_latency_max_ms_{service_name} gauge")
                lines.append(f"pipeline_api_latency_max_ms_{service_name} {latency_dict['max_ms']}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # Error Metrics (Req 6.5: retry attempts, failure types, error rates)
        # ═══════════════════════════════════════════════════════════════════════════
        lines.append("# HELP pipeline_retry_attempts_total Total number of retry attempts across all jobs")
        lines.append("# TYPE pipeline_retry_attempts_total counter")
        lines.append(f"pipeline_retry_attempts_total {self.total_retry_attempts}")
        
        lines.append("# HELP pipeline_errors_total Total number of errors encountered")
        lines.append("# TYPE pipeline_errors_total counter")
        lines.append(f"pipeline_errors_total {self.total_errors}")
        
        lines.append("# HELP pipeline_error_rate Error rate (errors / total jobs)")
        lines.append("# TYPE pipeline_error_rate gauge")
        lines.append(f"pipeline_error_rate {self.error_rate:.4f}")
        
        # Per-error-type retry metrics (Req 6.5: failure types)
        if self.retry_metrics:
            for error_type, retry_dict in self.retry_metrics.items():
                # Sanitize error_type for Prometheus label
                sanitized_error = error_type.replace(" ", "_").replace(".", "_").lower()
                
                lines.append(f"# HELP pipeline_retry_count_{sanitized_error} Number of retry attempts for {error_type}")
                lines.append(f"# TYPE pipeline_retry_count_{sanitized_error} counter")
                lines.append(f"pipeline_retry_count_{sanitized_error} {retry_dict['retry_count']}")
                
                lines.append(f"# HELP pipeline_retry_success_{sanitized_error} Successful retries for {error_type}")
                lines.append(f"# TYPE pipeline_retry_success_{sanitized_error} counter")
                lines.append(f"pipeline_retry_success_{sanitized_error} {retry_dict['success_after_retry']}")
                
                lines.append(f"# HELP pipeline_retry_failure_{sanitized_error} Failed retries for {error_type}")
                lines.append(f"# TYPE pipeline_retry_failure_{sanitized_error} counter")
                lines.append(f"pipeline_retry_failure_{sanitized_error} {retry_dict['failed_after_retry']}")
                
                lines.append(f"# HELP pipeline_retry_success_rate_{sanitized_error} Retry success rate for {error_type} (0-1)")
                lines.append(f"# TYPE pipeline_retry_success_rate_{sanitized_error} gauge")
                lines.append(f"pipeline_retry_success_rate_{sanitized_error} {retry_dict['success_rate']}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # Metadata
        # ═══════════════════════════════════════════════════════════════════════════
        lines.append("# HELP pipeline_elapsed_seconds Elapsed time since pipeline started in seconds")
        lines.append("# TYPE pipeline_elapsed_seconds counter")
        lines.append(f"pipeline_elapsed_seconds {self.elapsed_seconds}")
        
        return "\n".join(lines)


class MetricsCollector:
    """
    Central metrics collection system for the async job pipeline.
    
    Thread-safe collector that tracks all pipeline metrics including:
    - Job counts (total, success, failure)
    - Processing times with percentile calculations
    - Queue size over time
    - Worker and semaphore utilization
    - API call latencies per service
    - Retry rates per error type
    
    Example:
        collector = MetricsCollector()
        
        # Record job processing
        collector.record_job_start("job-123")
        collector.record_job_success("job-123", duration_ms=250.5)
        
        # Record API latency
        collector.record_api_latency(ServiceType.LLM, duration_ms=180.2)
        
        # Record queue state
        collector.record_queue_state(size=15, active_workers=5, semaphore_available=3)
        
        # Export metrics
        snapshot = collector.get_snapshot()
        print(snapshot.to_dict())
    """
    
    def __init__(self, semaphore_total: int = 10, workers_total: int = 5):
        """
        Initialize metrics collector.
        
        Args:
            semaphore_total: Total semaphore slots for API rate limiting.
            workers_total: Total number of worker threads.
        """
        self._lock = Lock()
        
        # Job metrics (Req 6.1, 20.1)
        self._jobs_total = 0
        self._jobs_success = 0
        self._jobs_failed = 0
        self._jobs_in_progress: Set[str] = set()
        
        # Processing time tracking (Req 6.1, 20.2)
        self._processing_times: List[float] = []
        self._processing_time_sum = 0.0
        self._processing_time_min = float('inf')
        self._processing_time_max = 0.0
        
        # Queue metrics (Req 6.2, 20.3)
        self._queue_snapshots: List[QueueSnapshot] = []
        self._queue_size_current = 0
        self._queue_size_max = 0
        self._queue_size_sum = 0.0
        self._queue_size_samples = 0
        self._queue_backpressure_events = 0  # Req 6.2: backpressure events
        self._queue_wait_times: List[float] = []  # Req 6.2: wait times
        
        # Worker metrics (Req 6.3, 20.3)
        self._workers_active = 0
        self._workers_total = workers_total
        self._worker_idle_time_total_ms = 0.0  # Req 6.3: idle time
        self._semaphore_available = semaphore_total
        self._semaphore_total = semaphore_total
        
        # API latency tracking per service (Req 6.4, 20.4)
        self._api_latencies: Dict[ServiceType, LatencyMetrics] = {
            ServiceType.LLM: LatencyMetrics(),
            ServiceType.EMAIL: LatencyMetrics(),
            ServiceType.SCRAPING: LatencyMetrics(),
            ServiceType.DATABASE: LatencyMetrics(),
        }
        
        # Rate limiter metrics (Req 6.4)
        self._rate_limiter_waits_total = 0
        self._rate_limiter_wait_time_total_ms = 0.0
        
        # Retry tracking per error type (Req 6.5, 20.5)
        self._retry_metrics: Dict[str, RetryMetrics] = defaultdict(RetryMetrics)
        
        # Timing
        self._start_time = time.time()
        
        logger.info(
            f"MetricsCollector initialized (workers={workers_total}, semaphore={semaphore_total})"
        )
    
    # Job processing metrics (Req 20.1)
    
    def record_job_start(self, job_id: str) -> None:
        """
        Record that a job has started processing.
        
        Args:
            job_id: Unique job identifier.
        """
        with self._lock:
            self._jobs_total += 1
            self._jobs_in_progress.add(job_id)
    
    def record_job_success(self, job_id: str, duration_ms: float) -> None:
        """
        Record successful job completion.
        
        Args:
            job_id: Unique job identifier.
            duration_ms: Processing duration in milliseconds.
        """
        with self._lock:
            self._jobs_success += 1
            self._jobs_in_progress.discard(job_id)
            self._record_processing_time(duration_ms)
    
    def record_job_failure(self, job_id: str, duration_ms: float = 0.0) -> None:
        """
        Record job failure.
        
        Args:
            job_id: Unique job identifier.
            duration_ms: Processing duration in milliseconds.
        """
        with self._lock:
            self._jobs_failed += 1
            self._jobs_in_progress.discard(job_id)
            if duration_ms > 0:
                self._record_processing_time(duration_ms)
    
    # Processing time metrics (Req 20.2)
    
    def _record_processing_time(self, duration_ms: float) -> None:
        """
        Internal method to record processing time.
        Must be called with lock held.
        
        Args:
            duration_ms: Processing duration in milliseconds.
        """
        self._processing_times.append(duration_ms)
        self._processing_time_sum += duration_ms
        self._processing_time_min = min(self._processing_time_min, duration_ms)
        self._processing_time_max = max(self._processing_time_max, duration_ms)
    
    # Queue and worker metrics (Req 20.3)
    
    def record_queue_state(
        self,
        size: int,
        active_workers: int,
        semaphore_available: int,
    ) -> None:
        """
        Record current queue and worker state.
        
        This should be called periodically to track queue size over time.
        
        Args:
            size: Current queue size.
            active_workers: Number of currently active workers.
            semaphore_available: Available semaphore slots.
        """
        with self._lock:
            self._queue_size_current = size
            self._queue_size_max = max(self._queue_size_max, size)
            self._queue_size_sum += size
            self._queue_size_samples += 1
            
            self._workers_active = active_workers
            self._semaphore_available = semaphore_available
            
            # Store snapshot for time series
            snapshot = QueueSnapshot(
                timestamp=time.time(),
                size=size,
                active_workers=active_workers,
                semaphore_available=semaphore_available,
            )
            self._queue_snapshots.append(snapshot)
            
            # Limit snapshot history to last 1000 samples
            if len(self._queue_snapshots) > 1000:
                self._queue_snapshots = self._queue_snapshots[-1000:]
    
    # API latency metrics per service (Req 20.4)
    
    def record_api_latency(self, service: ServiceType, duration_ms: float) -> None:
        """
        Record API call latency for a specific service.
        
        Args:
            service: Type of service (LLM, EMAIL, SCRAPING, DATABASE).
            duration_ms: API call duration in milliseconds.
        """
        with self._lock:
            self._api_latencies[service].record(duration_ms)
    
    # Retry metrics per error type (Req 20.5)
    
    def record_retry_attempt(self, error_type: str) -> None:
        """
        Record a retry attempt for a specific error type.
        
        Args:
            error_type: Type of error that triggered the retry (e.g., "TimeoutError").
        """
        with self._lock:
            self._retry_metrics[error_type].retry_count += 1
    
    def record_retry_success(self, error_type: str) -> None:
        """
        Record successful completion after retry.
        
        Args:
            error_type: Type of error that was retried.
        """
        with self._lock:
            self._retry_metrics[error_type].success_after_retry += 1
    
    def record_retry_failure(self, error_type: str) -> None:
        """
        Record final failure after all retries exhausted.
        
        Args:
            error_type: Type of error that caused final failure.
        """
        with self._lock:
            self._retry_metrics[error_type].failed_after_retry += 1
    
    # Queue backpressure and wait time metrics (Req 6.2)
    
    def record_backpressure_event(self) -> None:
        """
        Record a backpressure event (queue was full when put() was attempted).
        
        Requirements: 6.2 (queue backpressure events)
        """
        with self._lock:
            self._queue_backpressure_events += 1
    
    def record_queue_wait_time(self, wait_time_ms: float) -> None:
        """
        Record queue wait time (time spent waiting to get/put from queue).
        
        Args:
            wait_time_ms: Wait time in milliseconds.
            
        Requirements: 6.2 (queue wait times)
        """
        with self._lock:
            self._queue_wait_times.append(wait_time_ms)
            # Limit history to prevent unbounded growth
            if len(self._queue_wait_times) > 10000:
                self._queue_wait_times = self._queue_wait_times[-10000:]
    
    # Worker idle time metrics (Req 6.3)
    
    def record_worker_idle_time(self, idle_time_ms: float) -> None:
        """
        Record worker idle time (time spent waiting for jobs).
        
        Args:
            idle_time_ms: Idle time in milliseconds.
            
        Requirements: 6.3 (worker idle time)
        """
        with self._lock:
            self._worker_idle_time_total_ms += idle_time_ms
    
    # Rate limiter metrics (Req 6.4)
    
    def record_rate_limiter_wait(self, wait_time_ms: float) -> None:
        """
        Record a rate limiter wait event.
        
        Args:
            wait_time_ms: Time spent waiting for rate limiter in milliseconds.
            
        Requirements: 6.4 (rate limiter waits)
        """
        with self._lock:
            self._rate_limiter_waits_total += 1
            self._rate_limiter_wait_time_total_ms += wait_time_ms
    
    # Metric export
    
    def get_snapshot(self) -> MetricsSnapshot:
        """
        Get a complete snapshot of all metrics.
        
        Returns:
            MetricsSnapshot with all current metrics.
        """
        with self._lock:
            # Calculate processing time percentiles
            processing_times = sorted(self._processing_times)
            n = len(processing_times)
            
            p50 = processing_times[int(n * 0.50)] if n > 0 else 0.0
            p95 = processing_times[int(n * 0.95)] if n > 0 else 0.0
            p99 = processing_times[int(n * 0.99)] if n > 0 else 0.0
            
            avg_processing_time = (
                self._processing_time_sum / n if n > 0 else 0.0
            )
            
            # Calculate queue size average
            avg_queue_size = (
                self._queue_size_sum / self._queue_size_samples
                if self._queue_size_samples > 0 else 0.0
            )
            
            # Calculate queue wait time statistics (Req 6.2)
            wait_times = self._queue_wait_times
            queue_wait_time_avg_ms = (
                sum(wait_times) / len(wait_times) if wait_times else 0.0
            )
            queue_wait_time_max_ms = max(wait_times) if wait_times else 0.0
            
            # Calculate total retry attempts and error metrics (Req 6.5)
            total_retry_attempts = sum(
                m.retry_count for m in self._retry_metrics.values()
            )
            total_errors = self._jobs_failed
            error_rate = (
                total_errors / self._jobs_total if self._jobs_total > 0 else 0.0
            )
            
            # Calculate elapsed time and throughput
            elapsed = time.time() - self._start_time
            throughput = self._jobs_success / elapsed if elapsed > 0 else 0.0
            
            return MetricsSnapshot(
                # Job metrics (Req 6.1)
                jobs_total=self._jobs_total,
                jobs_success=self._jobs_success,
                jobs_failed=self._jobs_failed,
                
                # Processing time metrics (Req 6.1)
                processing_time_min_ms=round(
                    self._processing_time_min if self._processing_time_min != float('inf') else 0.0,
                    2
                ),
                processing_time_avg_ms=round(avg_processing_time, 2),
                processing_time_max_ms=round(self._processing_time_max, 2),
                processing_time_p50_ms=round(p50, 2),
                processing_time_p95_ms=round(p95, 2),
                processing_time_p99_ms=round(p99, 2),
                
                # Queue metrics (Req 6.2)
                queue_size_current=self._queue_size_current,
                queue_size_max=self._queue_size_max,
                queue_size_avg=round(avg_queue_size, 2),
                queue_backpressure_events=self._queue_backpressure_events,
                queue_wait_time_avg_ms=round(queue_wait_time_avg_ms, 2),
                queue_wait_time_max_ms=round(queue_wait_time_max_ms, 2),
                
                # Worker metrics (Req 6.3)
                workers_active=self._workers_active,
                workers_total=self._workers_total,
                worker_idle_time_total_ms=round(self._worker_idle_time_total_ms, 2),
                semaphore_available=self._semaphore_available,
                semaphore_total=self._semaphore_total,
                
                # API metrics / Rate limiter (Req 6.4)
                rate_limiter_waits_total=self._rate_limiter_waits_total,
                rate_limiter_wait_time_total_ms=round(self._rate_limiter_wait_time_total_ms, 2),
                llm_latency=self._api_latencies[ServiceType.LLM].to_dict(),
                email_latency=self._api_latencies[ServiceType.EMAIL].to_dict(),
                scraping_latency=self._api_latencies[ServiceType.SCRAPING].to_dict(),
                database_latency=self._api_latencies[ServiceType.DATABASE].to_dict(),
                
                # Retry/Error metrics (Req 6.5)
                retry_metrics={
                    error_type: metrics.to_dict()
                    for error_type, metrics in self._retry_metrics.items()
                },
                total_retry_attempts=total_retry_attempts,
                total_errors=total_errors,
                error_rate=round(error_rate, 4),
                
                # Metadata
                elapsed_seconds=round(elapsed, 2),
                throughput_jobs_per_sec=round(throughput, 2),
            )
    
    def get_queue_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent queue state history.
        
        Args:
            limit: Maximum number of snapshots to return.
            
        Returns:
            List of queue snapshots.
        """
        with self._lock:
            snapshots = self._queue_snapshots[-limit:]
            return [s.to_dict() for s in snapshots]
    
    def reset(self) -> None:
        """Reset all metrics (useful for testing or restart)."""
        with self._lock:
            self._jobs_total = 0
            self._jobs_success = 0
            self._jobs_failed = 0
            self._jobs_in_progress.clear()
            
            self._processing_times.clear()
            self._processing_time_sum = 0.0
            self._processing_time_min = float('inf')
            self._processing_time_max = 0.0
            
            self._queue_snapshots.clear()
            self._queue_size_current = 0
            self._queue_size_max = 0
            self._queue_size_sum = 0.0
            self._queue_size_samples = 0
            self._queue_backpressure_events = 0  # Req 6.2
            self._queue_wait_times.clear()  # Req 6.2
            
            self._workers_active = 0
            self._worker_idle_time_total_ms = 0.0  # Req 6.3
            self._semaphore_available = self._semaphore_total
            
            # Reset rate limiter metrics (Req 6.4)
            self._rate_limiter_waits_total = 0
            self._rate_limiter_wait_time_total_ms = 0.0
            
            # Reset API latencies
            for service in ServiceType:
                self._api_latencies[service] = LatencyMetrics()
            
            # Reset retry metrics
            self._retry_metrics.clear()
            
            self._start_time = time.time()
            
            logger.info("Metrics reset")
    
    def log_summary(self) -> None:
        """Log a summary of current metrics."""
        snapshot = self.get_snapshot()
        
        logger.info(
            "Pipeline Metrics Summary",
            extra={
                "jobs_total": snapshot.jobs_total,
                "jobs_success": snapshot.jobs_success,
                "jobs_failed": snapshot.jobs_failed,
                "success_rate": round(
                    snapshot.jobs_success / snapshot.jobs_total * 100, 1
                ) if snapshot.jobs_total > 0 else 0.0,
                "processing_time_avg_ms": snapshot.processing_time_avg_ms,
                "processing_time_p95_ms": snapshot.processing_time_p95_ms,
                "throughput_jobs_per_sec": snapshot.throughput_jobs_per_sec,
                "queue_size_current": snapshot.queue_size_current,
                "workers_active": snapshot.workers_active,
            }
        )


# Context manager for timing operations
class MetricsTimer:
    """
    Context manager for timing operations and recording to metrics collector.
    
    Example:
        collector = MetricsCollector()
        
        async with MetricsTimer(collector, ServiceType.LLM):
            result = await llm_service.call_api()
    """
    
    def __init__(
        self,
        collector: MetricsCollector,
        service: ServiceType,
    ):
        """
        Initialize timer.
        
        Args:
            collector: Metrics collector to record to.
            service: Service type being timed.
        """
        self.collector = collector
        self.service = service
        self.start_time: Optional[float] = None
    
    async def __aenter__(self):
        """Start timer."""
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and record metric."""
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            self.collector.record_api_latency(self.service, duration_ms)
        return False
    
    def __enter__(self):
        """Start timer (sync version)."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and record metric (sync version)."""
        if self.start_time is not None:
            duration_ms = (time.time() - self.start_time) * 1000
            self.collector.record_api_latency(self.service, duration_ms)
        return False
