"""
Tests for the ProgressTracker class with rich library integration.

This test suite verifies:
- Progress tracker initialization and lifecycle
- Job completion tracking with success/failure counts
- Throughput calculation
- ETA estimation
- Queue size and active worker tracking
- Statistics collection
- Context manager usage
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.async_pipeline.progress_tracker import ProgressTracker, track_progress
from src.async_pipeline.types import JobStatus, ProcessingResult


class TestProgressTrackerInitialization:
    """Test progress tracker initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        tracker = ProgressTracker()
        
        assert tracker._total_jobs == 0
        assert tracker._worker_count == 1
        assert tracker._enable_logging is True
        assert tracker._refresh_rate == 4
        assert tracker.is_started is False
    
    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        tracker = ProgressTracker(
            total_jobs=1000,
            worker_count=5,
            enable_logging=False,
            refresh_per_second=10,
        )
        
        assert tracker._total_jobs == 1000
        assert tracker._worker_count == 5
        assert tracker._enable_logging is False
        assert tracker._refresh_rate == 10


class TestProgressTrackerLifecycle:
    """Test progress tracker start/stop lifecycle."""
    
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    def test_start_tracker(self, mock_progress, mock_live):
        """Test starting the progress tracker."""
        tracker = ProgressTracker(total_jobs=100, worker_count=5)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        assert tracker.is_started is True
        assert tracker._start_time is not None
        mock_progress_instance.add_task.assert_called_once()
        mock_live_instance.start.assert_called_once()
    
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    def test_stop_tracker(self, mock_progress, mock_live):
        """Test stopping the progress tracker."""
        tracker = ProgressTracker(total_jobs=100, worker_count=5)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        tracker.stop()
        
        assert tracker.is_started is False
        mock_live_instance.stop.assert_called_once()
    
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    def test_double_start_warning(self, mock_progress, mock_live):
        """Test that starting twice logs a warning."""
        tracker = ProgressTracker(total_jobs=100)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        with patch('src.async_pipeline.progress_tracker.logger') as mock_logger:
            tracker.start()
            tracker.start()  # Second start
            
            mock_logger.warning.assert_called_once_with("Progress tracker already started")


class TestJobCompletionTracking:
    """Test job completion tracking and metrics."""
    
    @pytest.mark.asyncio
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    async def test_update_successful_job(self, mock_progress, mock_live):
        """Test updating progress with successful job."""
        tracker = ProgressTracker(total_jobs=100, worker_count=5)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress_instance.update = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        # Create successful result
        result = ProcessingResult.success(
            job_id="job-1",
            data={"status": "completed"},
            attempt_count=1,
            processing_time_ms=150.5,
        )
        
        await tracker.update_job_completed(result)
        
        assert tracker._jobs_completed == 1
        assert tracker._jobs_successful == 1
        assert tracker._jobs_failed == 0
        assert tracker._total_processing_time_ms == 150.5
        
        tracker.stop()
    
    @pytest.mark.asyncio
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    async def test_update_failed_job(self, mock_progress, mock_live):
        """Test updating progress with failed job."""
        tracker = ProgressTracker(total_jobs=100, worker_count=5)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        # Create failed result
        result = ProcessingResult.failure(
            job_id="job-1",
            error="API timeout",
            error_type="TimeoutError",
            attempt_count=3,
        )
        
        await tracker.update_job_completed(result)
        
        assert tracker._jobs_completed == 1
        assert tracker._jobs_successful == 0
        assert tracker._jobs_failed == 1
        
        tracker.stop()
    
    @pytest.mark.asyncio
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    async def test_multiple_job_updates(self, mock_progress, mock_live):
        """Test updating progress with multiple jobs."""
        tracker = ProgressTracker(total_jobs=10, worker_count=3)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        # Complete 5 successful and 2 failed jobs
        for i in range(5):
            result = ProcessingResult.success(
                job_id=f"job-{i}",
                data={"status": "completed"},
                processing_time_ms=100.0,
            )
            await tracker.update_job_completed(result)
        
        for i in range(2):
            result = ProcessingResult.failure(
                job_id=f"job-{i+5}",
                error="Error",
            )
            await tracker.update_job_completed(result)
        
        assert tracker._jobs_completed == 7
        assert tracker._jobs_successful == 5
        assert tracker._jobs_failed == 2
        
        tracker.stop()


class TestThroughputCalculation:
    """Test throughput and timing calculations."""
    
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    def test_throughput_calculation(self, mock_progress, mock_live):
        """Test throughput calculation in jobs per second."""
        tracker = ProgressTracker(total_jobs=100)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        # Simulate 10 jobs completed over 2 seconds
        tracker._jobs_completed = 10
        tracker._start_time = time.time() - 2.0
        
        throughput = tracker.throughput
        assert 4.5 < throughput < 5.5  # Should be ~5 jobs/sec
        
        tracker.stop()
    
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    def test_eta_calculation(self, mock_progress, mock_live):
        """Test ETA (estimated time remaining) calculation."""
        tracker = ProgressTracker(total_jobs=100)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        # Simulate 20 jobs completed over 4 seconds (5 jobs/sec)
        tracker._jobs_completed = 20
        tracker._start_time = time.time() - 4.0
        
        eta = tracker.eta_seconds
        # Remaining: 80 jobs at 5 jobs/sec = 16 seconds
        assert 15 < eta < 17
        
        tracker.stop()
    
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    def test_zero_throughput(self, mock_progress, mock_live):
        """Test throughput is zero when no jobs completed."""
        tracker = ProgressTracker(total_jobs=100)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        assert tracker.throughput == 0.0
        assert tracker.eta_seconds == 0.0
        
        tracker.stop()


class TestQueueAndWorkerTracking:
    """Test queue size and active worker tracking."""
    
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    def test_update_queue_size(self, mock_progress, mock_live):
        """Test updating queue size."""
        tracker = ProgressTracker(total_jobs=100)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        tracker.update_queue_size(42)
        assert tracker._queue_size == 42
        
        tracker.update_queue_size(10)
        assert tracker._queue_size == 10
        
        tracker.stop()
    
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    def test_update_active_workers(self, mock_progress, mock_live):
        """Test updating active worker count."""
        tracker = ProgressTracker(total_jobs=100, worker_count=5)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        tracker.update_active_workers(3)
        assert tracker._active_workers == 3
        
        tracker.update_active_workers(5)
        assert tracker._active_workers == 5
        
        tracker.stop()


class TestStatistics:
    """Test statistics collection."""
    
    @pytest.mark.asyncio
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    async def test_stats_dict(self, mock_progress, mock_live):
        """Test statistics dictionary."""
        tracker = ProgressTracker(total_jobs=100, worker_count=5)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        # Update with some jobs
        for i in range(3):
            result = ProcessingResult.success(
                job_id=f"job-{i}",
                data={"status": "completed"},
                processing_time_ms=100.0,
            )
            await tracker.update_job_completed(result)
        
        tracker.update_queue_size(25)
        tracker.update_active_workers(4)
        
        stats = tracker.stats
        
        assert stats["total_jobs"] == 100
        assert stats["jobs_completed"] == 3
        assert stats["jobs_successful"] == 3
        assert stats["jobs_failed"] == 0
        assert stats["queue_size"] == 25
        assert stats["active_workers"] == 4
        assert "elapsed_seconds" in stats
        assert "throughput" in stats
        assert "eta_seconds" in stats
        
        tracker.stop()


class TestContextManager:
    """Test context manager usage."""
    
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    def test_context_manager(self, mock_progress, mock_live):
        """Test using progress tracker as context manager."""
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        with track_progress(total_jobs=50, worker_count=3) as tracker:
            assert tracker.is_started is True
            assert tracker._total_jobs == 50
            assert tracker._worker_count == 3
        
        # Tracker should be stopped after context
        assert tracker.is_started is False


class TestDurationFormatting:
    """Test duration formatting utility."""
    
    def test_format_seconds(self):
        """Test formatting seconds."""
        assert ProgressTracker._format_duration(30.5) == "30.5s"
        assert ProgressTracker._format_duration(45) == "45.0s"
    
    def test_format_minutes(self):
        """Test formatting minutes and seconds."""
        assert ProgressTracker._format_duration(90) == "1m 30s"
        assert ProgressTracker._format_duration(125) == "2m 5s"
    
    def test_format_hours(self):
        """Test formatting hours and minutes."""
        assert ProgressTracker._format_duration(3661) == "1h 1m"
        assert ProgressTracker._format_duration(7320) == "2h 2m"


class TestLogging:
    """Test structured logging integration."""
    
    @pytest.mark.asyncio
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    @patch('src.async_pipeline.progress_tracker.logger')
    async def test_logging_enabled(self, mock_logger, mock_progress, mock_live):
        """Test logging when enabled."""
        tracker = ProgressTracker(total_jobs=100, enable_logging=True)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        # Verify start logging
        mock_logger.info.assert_called()
        
        # Complete 10 jobs to trigger periodic logging
        for i in range(10):
            result = ProcessingResult.success(
                job_id=f"job-{i}",
                data={"status": "completed"},
            )
            await tracker.update_job_completed(result)
        
        # Verify periodic logging occurred
        assert mock_logger.info.call_count >= 2
        
        tracker.stop()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    def test_set_total_jobs_after_start(self, mock_progress, mock_live):
        """Test updating total jobs after starting."""
        tracker = ProgressTracker(total_jobs=100)
        
        # Mock rich components
        mock_progress_instance = MagicMock()
        mock_progress.return_value = mock_progress_instance
        mock_live_instance = MagicMock()
        mock_live.return_value = mock_live_instance
        
        tracker.start()
        
        tracker.set_total_jobs(200)
        assert tracker._total_jobs == 200
        
        tracker.stop()
    
    def test_elapsed_time_before_start(self):
        """Test elapsed time before starting tracker."""
        tracker = ProgressTracker(total_jobs=100)
        
        assert tracker.elapsed_seconds == 0.0
    
    @patch('src.async_pipeline.progress_tracker.Live')
    @patch('src.async_pipeline.progress_tracker.Progress')
    def test_stop_before_start(self, mock_progress, mock_live):
        """Test stopping tracker before starting."""
        tracker = ProgressTracker(total_jobs=100)
        
        # Should not raise any exceptions
        tracker.stop()
        
        assert tracker.is_started is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
