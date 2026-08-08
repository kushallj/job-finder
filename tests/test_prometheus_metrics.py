"""
Unit tests for Prometheus metrics export functionality.

Tests:
1. MetricsSnapshot.to_prometheus_format() generates valid Prometheus text
2. All required metrics are present in the output
3. Metric values are correctly formatted
4. Edge cases (empty metrics, no data)

Requirements tested: 6.1, 6.2, 6.3, 6.4, 6.5, 9.1
"""

import pytest
from src.async_pipeline.metrics import MetricsCollector, MetricsSnapshot, ServiceType


class TestPrometheusMetricsExport:
    """Test suite for Prometheus metrics export functionality."""
    
    def test_prometheus_format_basic(self):
        """Test basic Prometheus format generation."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        # Simulate some job processing
        collector.record_job_start("job-1")
        collector.record_job_success("job-1", duration_ms=250.5)
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # Verify Prometheus format markers
        assert "# HELP" in prometheus_text
        assert "# TYPE" in prometheus_text
        
        # Verify basic structure
        assert "pipeline_jobs_total" in prometheus_text
        assert "pipeline_jobs_success" in prometheus_text
    
    def test_all_required_metrics_present(self):
        """Test that all required metrics are present in output."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        # Simulate comprehensive data
        collector.record_job_start("job-1")
        collector.record_job_success("job-1", duration_ms=250.5)
        collector.record_job_start("job-2")
        collector.record_job_failure("job-2", duration_ms=100.0)
        
        collector.record_api_latency(ServiceType.LLM, 180.5)
        collector.record_api_latency(ServiceType.EMAIL, 50.2)
        
        collector.record_retry_attempt("TimeoutError")
        collector.record_retry_success("TimeoutError")
        
        collector.record_queue_state(size=42, active_workers=3, semaphore_available=7)
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # Job processing metrics (Req 6.1)
        required_metrics = [
            "pipeline_jobs_total",
            "pipeline_jobs_success",
            "pipeline_jobs_failed",
            "pipeline_job_success_rate",
            "pipeline_processing_time_min_ms",
            "pipeline_processing_time_avg_ms",
            "pipeline_processing_time_max_ms",
            "pipeline_processing_time_p50_ms",
            "pipeline_processing_time_p95_ms",
            "pipeline_processing_time_p99_ms",
            "pipeline_throughput_jobs_per_sec",
        ]
        
        for metric in required_metrics:
            assert metric in prometheus_text, f"Missing metric: {metric}"
        
        # Queue metrics (Req 6.2)
        queue_metrics = [
            "pipeline_queue_size_current",
            "pipeline_queue_size_max",
            "pipeline_queue_size_avg",
        ]
        
        for metric in queue_metrics:
            assert metric in prometheus_text, f"Missing queue metric: {metric}"
        
        # Worker metrics (Req 6.3)
        worker_metrics = [
            "pipeline_workers_active",
            "pipeline_workers_total",
            "pipeline_worker_utilization",
            "pipeline_worker_idle_rate",
        ]
        
        for metric in worker_metrics:
            assert metric in prometheus_text, f"Missing worker metric: {metric}"
        
        # API metrics (Req 6.4)
        api_metrics = [
            "pipeline_semaphore_available",
            "pipeline_semaphore_total",
            "pipeline_semaphore_contention",
            "pipeline_api_latency_count_llm",
            "pipeline_api_latency_avg_ms_llm",
            "pipeline_api_latency_count_email",
        ]
        
        for metric in api_metrics:
            assert metric in prometheus_text, f"Missing API metric: {metric}"
        
        # Error metrics (Req 6.5)
        error_metrics = [
            "pipeline_retry_count_timeouterror",
            "pipeline_retry_success_timeouterror",
            "pipeline_retry_success_rate_timeouterror",
        ]
        
        for metric in error_metrics:
            assert metric in prometheus_text, f"Missing error metric: {metric}"
    
    def test_metric_values_formatted_correctly(self):
        """Test that metric values are formatted correctly for Prometheus."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        collector.record_job_start("job-1")
        collector.record_job_success("job-1", duration_ms=250.5)
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # Check that values are numeric (not quoted)
        assert "pipeline_jobs_total 1" in prometheus_text
        assert "pipeline_jobs_success 1" in prometheus_text
        
        # Check that floats are formatted correctly
        lines = prometheus_text.split('\n')
        for line in lines:
            if line.startswith('pipeline_') and not line.startswith('# '):
                parts = line.split(' ')
                if len(parts) == 2:
                    # Verify value is numeric
                    try:
                        float(parts[1])
                    except ValueError:
                        pytest.fail(f"Invalid metric value in line: {line}")
    
    def test_empty_metrics(self):
        """Test Prometheus format generation with no data."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # Should still have headers and zero values
        assert "# HELP pipeline_jobs_total" in prometheus_text
        assert "pipeline_jobs_total 0" in prometheus_text
        assert "pipeline_jobs_success 0" in prometheus_text
    
    def test_percentile_calculation(self):
        """Test that latency percentiles are calculated correctly."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        # Record jobs with known latencies
        latencies = [100, 200, 300, 400, 500]
        for i, latency in enumerate(latencies):
            collector.record_job_start(f"job-{i}")
            collector.record_job_success(f"job-{i}", duration_ms=latency)
        
        snapshot = collector.get_snapshot()
        
        # Check percentiles
        assert snapshot.processing_time_p50_ms == 300  # Median
        assert snapshot.processing_time_min_ms == 100
        assert snapshot.processing_time_max_ms == 500
        
        prometheus_text = snapshot.to_prometheus_format()
        assert "pipeline_processing_time_p50_ms 300" in prometheus_text
    
    def test_worker_utilization_calculation(self):
        """Test worker utilization and idle rate calculations."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        # 3 out of 5 workers active
        collector.record_queue_state(size=10, active_workers=3, semaphore_available=7)
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # Utilization = 3/5 = 0.6
        assert "pipeline_worker_utilization 0.6000" in prometheus_text
        # Idle rate = 1 - 0.6 = 0.4
        assert "pipeline_worker_idle_rate 0.4000" in prometheus_text
    
    def test_semaphore_contention_calculation(self):
        """Test semaphore contention rate calculation."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        # 7 out of 10 slots available = 3 in use
        collector.record_queue_state(size=10, active_workers=3, semaphore_available=7)
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # Contention = 1 - (7/10) = 0.3
        assert "pipeline_semaphore_contention 0.3000" in prometheus_text
    
    def test_error_type_sanitization(self):
        """Test that error types are sanitized for Prometheus labels."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        # Record retries with various error types
        collector.record_retry_attempt("TimeoutError")
        collector.record_retry_attempt("Connection.Error")
        collector.record_retry_attempt("HTTP 500 Error")
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # Should be lowercased and sanitized
        assert "pipeline_retry_count_timeouterror" in prometheus_text
        assert "pipeline_retry_count_connection_error" in prometheus_text
        assert "pipeline_retry_count_http_500_error" in prometheus_text
    
    def test_success_rate_calculation(self):
        """Test job success rate calculation."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        # 8 successes, 2 failures = 80% success rate
        for i in range(8):
            collector.record_job_start(f"job-{i}")
            collector.record_job_success(f"job-{i}", duration_ms=100.0)
        
        for i in range(8, 10):
            collector.record_job_start(f"job-{i}")
            collector.record_job_failure(f"job-{i}", duration_ms=100.0)
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # Success rate = 8/10 = 0.8
        assert "pipeline_job_success_rate 0.8000" in prometheus_text
    
    def test_api_latency_per_service(self):
        """Test that API latencies are tracked separately per service."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        # Record different latencies for different services
        collector.record_api_latency(ServiceType.LLM, 180.5)
        collector.record_api_latency(ServiceType.LLM, 220.3)
        collector.record_api_latency(ServiceType.EMAIL, 50.2)
        collector.record_api_latency(ServiceType.DATABASE, 15.8)
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # LLM should have 2 calls, avg ~200ms
        assert "pipeline_api_latency_count_llm 2" in prometheus_text
        assert "pipeline_api_latency_avg_ms_llm" in prometheus_text
        
        # Email should have 1 call
        assert "pipeline_api_latency_count_email 1" in prometheus_text
        assert "pipeline_api_latency_avg_ms_email 50.2" in prometheus_text
        
        # Database should have 1 call
        assert "pipeline_api_latency_count_database 1" in prometheus_text
        assert "pipeline_api_latency_avg_ms_database 15.8" in prometheus_text
    
    def test_retry_success_rate_calculation(self):
        """Test retry success rate calculation for different error types."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        # TimeoutError: 1 attempt, 1 success = 100% success rate
        collector.record_retry_attempt("TimeoutError")
        collector.record_retry_success("TimeoutError")
        
        # ConnectionError: 2 attempts, 0 successes, 1 failure = 0% success rate
        collector.record_retry_attempt("ConnectionError")
        collector.record_retry_attempt("ConnectionError")
        collector.record_retry_failure("ConnectionError")
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # TimeoutError should have 100% success rate
        assert "pipeline_retry_success_rate_timeouterror 1.0" in prometheus_text
        
        # ConnectionError should have 0% success rate
        assert "pipeline_retry_success_rate_connectionerror 0.0" in prometheus_text
    
    def test_prometheus_format_no_newline_at_end(self):
        """Test that Prometheus format doesn't have extra newlines at end."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        # Should not end with multiple newlines
        assert not prometheus_text.endswith("\n\n")
    
    def test_metric_help_and_type_present(self):
        """Test that all metrics have HELP and TYPE annotations."""
        collector = MetricsCollector(semaphore_total=10, workers_total=5)
        
        collector.record_job_start("job-1")
        collector.record_job_success("job-1", duration_ms=250.5)
        
        snapshot = collector.get_snapshot()
        prometheus_text = snapshot.to_prometheus_format()
        
        lines = prometheus_text.split('\n')
        
        # Check that every metric has a HELP and TYPE before it
        metric_lines = [line for line in lines if line and not line.startswith('#')]
        
        for i, line in enumerate(metric_lines):
            metric_name = line.split(' ')[0]
            
            # Find the HELP and TYPE for this metric
            # They should appear before the metric value
            found_help = False
            found_type = False
            
            # Look backwards from current line
            for j in range(len(lines)):
                if lines[j].startswith(f"# HELP {metric_name}"):
                    found_help = True
                if lines[j].startswith(f"# TYPE {metric_name}"):
                    found_type = True
            
            assert found_help, f"Missing # HELP for metric: {metric_name}"
            assert found_type, f"Missing # TYPE for metric: {metric_name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
