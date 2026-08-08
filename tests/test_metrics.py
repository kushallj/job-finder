"""
Unit tests for the metrics collection system.

Tests verify all metrics are correctly tracked including:
- Job processing counts (total, success, failure)
- Processing times (min, avg, max, percentiles)
- Queue metrics
- Worker metrics  
- API latency tracking per service
- Retry tracking per error type
"""

import asyncio
import pytest
import time
from src.async_pipeline.metrics import (
    MetricsCollector,
    ServiceType,
    MetricsTimer,
    LatencyMetrics,
    RetryMetrics,
)


class TestLatencyMetrics:
    """Test LatencyMetrics dataclass."""
    
    def test_initial_state(self):
        """Test initial state of LatencyMetrics."""
        metrics = LatencyMetrics()
        
        assert metrics.count == 0
        assert metrics.total_ms == 0.0
        assert metrics.min_ms == float('inf')
        assert metrics.max_ms == 0.0
        assert metrics.avg_ms == 0.0
    
    def test_record_single_latency(self):
        """Test recording a single latency measurement."""
        metrics = LatencyMetrics()
        
        metrics.record(100.5)
        
        assert metrics.count == 1
        assert metrics.total_ms == 100.5
        assert metrics.min_ms == 100.5
        assert metrics.max_ms == 100.5
        assert metrics.avg_ms == 100.5
    
    def test_record_multiple_latencies(self):
        """Test recording multiple latency measurements."""
        metrics = LatencyMetrics()
        
        metrics.record(50.0)
        metrics.record(100.0)
        metrics.record(150.0)
        
        assert metrics.count == 3
        assert metrics.total_ms == 300.0
        assert metrics.min_ms == 50.0
        assert metrics.max_ms == 150.0
        assert metrics.avg_ms == 100.0
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = LatencyMetrics()
        metrics.record(50.0)
        metrics.record(100.0)
        
        result = metrics.to_dict()
        
        assert result["count"] == 2
        assert result["total_ms"] == 150.0
        assert result["min_ms"] == 50.0
        assert result["max_ms"] == 100.0
        assert result["avg_ms"] == 75.0


class TestRetryMetrics:
    """Test RetryMetrics dataclass."""
    
    def test_initial_state(self):
        """Test initial state of RetryMetrics."""
        metrics = RetryMetrics()
        
        assert metrics.retry_count == 0
        assert metrics.success_after_retry == 0
        assert metrics.failed_after_retry == 0
    
    def test_to_dict_with_zero_retries(self):
        """Test conversion to dict with no retries."""
        metrics = RetryMetrics()
        
        result = metrics.to_dict()
        
        assert result["retry_count"] == 0
        assert result["success_after_retry"] == 0
        assert result["failed_after_retry"] == 0
        assert result["success_rate"] == 0.0
    
    def test_to_dict_with_retries(self):
        """Test conversion to dict with retries."""
        metrics = RetryMetrics()
        metrics.retry_count = 10
        metrics.success_after_retry = 7
        metrics.failed_after_retry = 3
        
        result = metrics.to_dict()
        
        assert result["retry_count"] == 10
        assert result["success_after_retry"] == 7
        assert result["failed_after_retry"] == 3
        assert result["success_rate"] == 0.7


class TestMetricsCollector:
    """Test MetricsCollector functionality."""
    
    def test_initialization(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        assert collector._semaphore_total == 10
        assert collector._workers_total == 5
        assert collector._jobs_total == 0
        assert collector._jobs_success == 0
        assert collector._jobs_failed == 0
    
    def test_record_job_lifecycle(self):
        """Test recording complete job lifecycle."""
        collector = MetricsCollector()
        
        # Start job
        collector.record_job_start("job-1")
        assert collector._jobs_total == 1
        assert "job-1" in collector._jobs_in_progress
        
        # Complete job
        collector.record_job_success("job-1", duration_ms=250.5)
        assert collector._jobs_success == 1
        assert "job-1" not in collector._jobs_in_progress
        assert len(collector._processing_times) == 1
        assert collector._processing_times[0] == 250.5
    
    def test_record_job_failure(self):
        """Test recording job failure."""
        collector = MetricsCollector()
        
        collector.record_job_start("job-1")
        collector.record_job_failure("job-1", duration_ms=150.0)
        
        assert collector._jobs_failed == 1
        assert "job-1" not in collector._jobs_in_progress
    
    def test_processing_time_stats(self):
        """Test processing time statistics calculation."""
        collector = MetricsCollector()
        
        # Record multiple jobs with different processing times
        collector.record_job_start("job-1")
        collector.record_job_success("job-1", duration_ms=50.0)
        
        collector.record_job_start("job-2")
        collector.record_job_success("job-2", duration_ms=100.0)
        
        collector.record_job_start("job-3")
        collector.record_job_success("job-3", duration_ms=150.0)
        
        assert collector._processing_time_min == 50.0
        assert collector._processing_time_max == 150.0
        assert collector._processing_time_sum == 300.0
    
    def test_record_queue_state(self):
        """Test recording queue state."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        collector.record_queue_state(
            size=15,
            active_workers=3,
            semaphore_available=7,
        )
        
        assert collector._queue_size_current == 15
        assert collector._queue_size_max == 15
        assert collector._workers_active == 3
        assert collector._semaphore_available == 7
        assert len(collector._queue_snapshots) == 1
    
    def test_queue_max_tracking(self):
        """Test that queue max is tracked correctly."""
        collector = MetricsCollector()
        
        collector.record_queue_state(size=10, active_workers=2, semaphore_available=8)
        collector.record_queue_state(size=25, active_workers=3, semaphore_available=7)
        collector.record_queue_state(size=15, active_workers=2, semaphore_available=8)
        
        assert collector._queue_size_max == 25
        assert collector._queue_size_current == 15
    
    def test_record_api_latency(self):
        """Test recording API latencies per service."""
        collector = MetricsCollector()
        
        # Record LLM latencies
        collector.record_api_latency(ServiceType.LLM, 180.5)
        collector.record_api_latency(ServiceType.LLM, 220.3)
        
        # Record email latencies
        collector.record_api_latency(ServiceType.EMAIL, 50.0)
        
        llm_metrics = collector._api_latencies[ServiceType.LLM]
        assert llm_metrics.count == 2
        assert llm_metrics.avg_ms == (180.5 + 220.3) / 2
        
        email_metrics = collector._api_latencies[ServiceType.EMAIL]
        assert email_metrics.count == 1
        assert email_metrics.avg_ms == 50.0
    
    def test_record_retry_metrics(self):
        """Test recording retry metrics per error type."""
        collector = MetricsCollector()
        
        # Record retries for TimeoutError
        collector.record_retry_attempt("TimeoutError")
        collector.record_retry_attempt("TimeoutError")
        collector.record_retry_success("TimeoutError")
        
        # Record retries for ClientError
        collector.record_retry_attempt("ClientError")
        collector.record_retry_failure("ClientError")
        
        timeout_metrics = collector._retry_metrics["TimeoutError"]
        assert timeout_metrics.retry_count == 2
        assert timeout_metrics.success_after_retry == 1
        
        client_metrics = collector._retry_metrics["ClientError"]
        assert client_metrics.retry_count == 1
        assert client_metrics.failed_after_retry == 1
    
    def test_get_snapshot(self):
        """Test getting complete metrics snapshot."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        # Simulate some activity
        collector.record_job_start("job-1")
        collector.record_job_success("job-1", duration_ms=100.0)
        
        collector.record_job_start("job-2")
        collector.record_job_success("job-2", duration_ms=200.0)
        
        collector.record_job_start("job-3")
        collector.record_job_failure("job-3", duration_ms=150.0)
        
        collector.record_queue_state(size=5, active_workers=2, semaphore_available=8)
        
        collector.record_api_latency(ServiceType.LLM, 180.0)
        collector.record_retry_attempt("TimeoutError")
        
        snapshot = collector.get_snapshot()
        
        # Verify job metrics
        assert snapshot.jobs_total == 3
        assert snapshot.jobs_success == 2
        assert snapshot.jobs_failed == 1
        
        # Verify processing time metrics
        assert snapshot.processing_time_min_ms == 100.0
        assert snapshot.processing_time_max_ms == 200.0
        assert snapshot.processing_time_avg_ms == 150.0  # (100 + 200 + 150) / 3
        
        # Verify queue metrics
        assert snapshot.queue_size_current == 5
        assert snapshot.queue_size_max == 5
        
        # Verify worker metrics
        assert snapshot.workers_active == 2
        assert snapshot.workers_total == 5
        assert snapshot.semaphore_available == 8
        assert snapshot.semaphore_total == 10
        
        # Verify API latencies are included
        assert "count" in snapshot.llm_latency
        assert snapshot.llm_latency["count"] == 1
        
        # Verify retry metrics are included
        assert "TimeoutError" in snapshot.retry_metrics
    
    def test_get_snapshot_percentiles(self):
        """Test percentile calculation in snapshot."""
        collector = MetricsCollector()
        
        # Record 100 jobs with varying processing times
        for i in range(100):
            collector.record_job_start(f"job-{i}")
            collector.record_job_success(f"job-{i}", duration_ms=float(i + 1))
        
        snapshot = collector.get_snapshot()
        
        # Verify percentiles are calculated
        assert snapshot.processing_time_p50_ms > 0
        assert snapshot.processing_time_p95_ms > 0
        assert snapshot.processing_time_p99_ms > 0
        
        # Percentiles should be in ascending order
        assert snapshot.processing_time_p50_ms <= snapshot.processing_time_p95_ms
        assert snapshot.processing_time_p95_ms <= snapshot.processing_time_p99_ms
    
    def test_get_queue_history(self):
        """Test retrieving queue history."""
        collector = MetricsCollector()
        
        # Record queue states
        for i in range(10):
            collector.record_queue_state(
                size=i,
                active_workers=min(i, 5),
                semaphore_available=10 - min(i, 5),
            )
        
        history = collector.get_queue_history(limit=5)
        
        assert len(history) == 5
        assert all(isinstance(item, dict) for item in history)
        assert all("timestamp" in item for item in history)
        assert all("size" in item for item in history)
    
    def test_reset(self):
        """Test resetting all metrics."""
        collector = MetricsCollector()
        
        # Record some data
        collector.record_job_start("job-1")
        collector.record_job_success("job-1", duration_ms=100.0)
        collector.record_queue_state(size=5, active_workers=2, semaphore_available=8)
        collector.record_api_latency(ServiceType.LLM, 180.0)
        
        # Reset
        collector.reset()
        
        # Verify everything is reset
        assert collector._jobs_total == 0
        assert collector._jobs_success == 0
        assert collector._jobs_failed == 0
        assert len(collector._processing_times) == 0
        assert len(collector._queue_snapshots) == 0
        assert collector._api_latencies[ServiceType.LLM].count == 0
    
    def test_prometheus_format(self):
        """Test Prometheus format export."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        collector.record_job_start("job-1")
        collector.record_job_success("job-1", duration_ms=100.0)
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # Verify Prometheus format
        assert "# HELP" in prometheus_text
        assert "# TYPE" in prometheus_text
        assert "pipeline_jobs_total" in prometheus_text
        assert "pipeline_jobs_success" in prometheus_text
        assert "pipeline_jobs_failed" in prometheus_text
        assert "pipeline_throughput_jobs_per_sec" in prometheus_text


@pytest.mark.asyncio
async def test_metrics_timer_async():
    """Test MetricsTimer context manager with async."""
    collector = MetricsCollector()
    
    async with MetricsTimer(collector, ServiceType.LLM):
        await asyncio.sleep(0.01)  # Simulate async work
    
    llm_metrics = collector._api_latencies[ServiceType.LLM]
    assert llm_metrics.count == 1
    assert llm_metrics.avg_ms >= 10.0  # At least 10ms


def test_metrics_timer_sync():
    """Test MetricsTimer context manager with sync."""
    collector = MetricsCollector()
    
    with MetricsTimer(collector, ServiceType.DATABASE):
        time.sleep(0.01)  # Simulate sync work
    
    db_metrics = collector._api_latencies[ServiceType.DATABASE]
    assert db_metrics.count == 1
    assert db_metrics.avg_ms >= 10.0  # At least 10ms


def test_snapshot_to_dict():
    """Test snapshot conversion to dictionary."""
    collector = MetricsCollector()
    
    collector.record_job_start("job-1")
    collector.record_job_success("job-1", duration_ms=100.0)
    
    snapshot = collector.get_snapshot()
    snapshot_dict = snapshot.to_dict()
    
    # Verify all expected fields are present
    assert "jobs_total" in snapshot_dict
    assert "jobs_success" in snapshot_dict
    assert "jobs_failed" in snapshot_dict
    assert "processing_time_min_ms" in snapshot_dict
    assert "processing_time_avg_ms" in snapshot_dict
    assert "processing_time_max_ms" in snapshot_dict
    assert "processing_time_p50_ms" in snapshot_dict
    assert "processing_time_p95_ms" in snapshot_dict
    assert "processing_time_p99_ms" in snapshot_dict
    assert "queue_size_current" in snapshot_dict
    assert "workers_active" in snapshot_dict
    assert "semaphore_available" in snapshot_dict
    assert "llm_latency" in snapshot_dict
    assert "email_latency" in snapshot_dict
    assert "scraping_latency" in snapshot_dict
    assert "database_latency" in snapshot_dict
    assert "retry_metrics" in snapshot_dict
    assert "elapsed_seconds" in snapshot_dict
    assert "throughput_jobs_per_sec" in snapshot_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
