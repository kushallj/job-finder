"""
Progress tracking with rich library for real-time visual feedback.

This module provides the ProgressTracker class that integrates with rich.progress
to display real-time progress updates including:
- Jobs processed (with progress bar)
- Success/failure counts
- Throughput (jobs/sec)
- Estimated completion time
- Queue size
- Active workers

The tracker is thread-safe and can be updated from multiple async workers.
"""

import asyncio
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

from src.async_pipeline.types import ProcessingResult, JobStatus

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Real-time progress tracking with rich library.
    
    Displays a progress bar with detailed metrics:
    - Jobs processed/total
    - Success/failure counts
    - Throughput (jobs/sec)
    - ETA (estimated time to completion)
    - Queue size
    - Active workers
    
    Example:
        tracker = ProgressTracker(total_jobs=1000, worker_count=5)
        tracker.start()
        
        # Update progress as jobs complete
        tracker.update_job_completed(result)
        tracker.update_queue_size(42)
        
        tracker.stop()
    """
    
    def __init__(
        self,
        total_jobs: int = 0,
        worker_count: int = 1,
        enable_logging: bool = True,
        refresh_per_second: int = 4,
    ):
        """
        Initialize progress tracker.
        
        Args:
            total_jobs: Total number of jobs to process.
            worker_count: Number of concurrent workers.
            enable_logging: Enable structured logging alongside progress display.
            refresh_per_second: Progress display refresh rate.
        """
        self._total_jobs = total_jobs
        self._worker_count = worker_count
        self._enable_logging = enable_logging
        self._refresh_rate = refresh_per_second
        
        # Progress metrics
        self._jobs_completed = 0
        self._jobs_successful = 0
        self._jobs_failed = 0
        self._jobs_retried = 0
        self._queue_size = 0
        self._active_workers = 0
        
        # Timing
        self._start_time: Optional[float] = None
        self._last_update_time: Optional[float] = None
        self._total_processing_time_ms = 0.0
        
        # Rich components
        self._console = Console()
        self._progress: Optional[Progress] = None
        self._progress_task: Optional[TaskID] = None
        self._live: Optional[Live] = None
        self._is_started = False
        
        # Lock for thread-safety
        self._lock = asyncio.Lock()
    
    def start(self) -> None:
        """Start the progress tracker display."""
        if self._is_started:
            logger.warning("Progress tracker already started")
            return
        
        self._start_time = time.time()
        self._last_update_time = self._start_time
        
        # Create progress bar
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=self._console,
            refresh_per_second=self._refresh_rate,
        )
        
        # Add main progress task
        self._progress_task = self._progress.add_task(
            "[cyan]Processing jobs...",
            total=self._total_jobs,
        )
        
        # Create live display with progress and stats
        self._live = Live(
            self._generate_display(),
            console=self._console,
            refresh_per_second=self._refresh_rate,
        )
        self._live.start()
        
        self._is_started = True
        
        if self._enable_logging:
            logger.info(
                f"Progress tracking started: {self._total_jobs} jobs, "
                f"{self._worker_count} workers"
            )
    
    def stop(self) -> None:
        """Stop the progress tracker display."""
        if not self._is_started:
            return
        
        # Stop live display
        if self._live:
            self._live.stop()
            self._live = None
        
        self._is_started = False
        
        # Print final summary
        self._print_summary()
        
        if self._enable_logging:
            logger.info(
                f"Progress tracking stopped: {self._jobs_completed}/{self._total_jobs} jobs, "
                f"{self._jobs_successful} successful, {self._jobs_failed} failed"
            )
    
    async def update_job_completed(self, result: ProcessingResult) -> None:
        """
        Update progress with a completed job result.
        
        Args:
            result: The processing result for the completed job.
        """
        async with self._lock:
            self._jobs_completed += 1
            
            if result.is_success():
                self._jobs_successful += 1
            else:
                self._jobs_failed += 1
            
            if result.status == JobStatus.RETRYING:
                self._jobs_retried += 1
            
            self._total_processing_time_ms += result.processing_time_ms
            
            # Update progress bar
            if self._progress and self._progress_task is not None:
                self._progress.update(self._progress_task, advance=1)
            
            # Update display
            if self._live:
                self._live.update(self._generate_display())
            
            # Log periodically
            if self._enable_logging and self._jobs_completed % 10 == 0:
                logger.info(
                    f"Progress: {self._jobs_completed}/{self._total_jobs} jobs, "
                    f"throughput: {self.throughput:.2f} jobs/sec"
                )
    
    def update_queue_size(self, size: int) -> None:
        """
        Update the current queue size.
        
        Args:
            size: Current queue size.
        """
        self._queue_size = size
        
        # Update display
        if self._live:
            self._live.update(self._generate_display())
    
    def update_active_workers(self, count: int) -> None:
        """
        Update the count of active workers.
        
        Args:
            count: Number of currently active workers.
        """
        self._active_workers = count
        
        # Update display
        if self._live:
            self._live.update(self._generate_display())
    
    def set_total_jobs(self, total: int) -> None:
        """
        Update the total job count.
        
        Args:
            total: New total job count.
        """
        self._total_jobs = total
        
        if self._progress and self._progress_task is not None:
            self._progress.update(self._progress_task, total=total)
        
        if self._live:
            self._live.update(self._generate_display())
    
    def _generate_display(self) -> Panel:
        """Generate the complete display with progress and stats."""
        # Create stats table
        stats_table = Table.grid(padding=(0, 2))
        stats_table.add_column(justify="right", style="cyan")
        stats_table.add_column(justify="left", style="white")
        
        # Add statistics rows
        stats_table.add_row("✓ Successful:", f"{self._jobs_successful:,}")
        stats_table.add_row("✗ Failed:", f"[red]{self._jobs_failed:,}[/red]")
        stats_table.add_row("↻ Retried:", f"{self._jobs_retried:,}")
        stats_table.add_row("⚡ Throughput:", f"{self.throughput:.2f} jobs/sec")
        stats_table.add_row("📊 Queue Size:", f"{self._queue_size:,}")
        stats_table.add_row("👷 Active Workers:", f"{self._active_workers}/{self._worker_count}")
        
        if self._jobs_completed > 0:
            avg_time = self._total_processing_time_ms / self._jobs_completed
            stats_table.add_row("⏱️  Avg Time:", f"{avg_time:.0f}ms")
        
        # Combine progress bar and stats
        if self._progress:
            display = Table.grid(padding=(0, 0))
            if hasattr(self._progress, "__rich__") or hasattr(self._progress, "__rich_console__"):
                display.add_row(self._progress)
            else:
                display.add_row(str(self._progress))
            display.add_row("")
            display.add_row(stats_table)
        else:
            display = stats_table

        
        # Wrap in panel
        return Panel(
            display,
            title="[bold cyan]Async Job Pipeline Progress",
            border_style="cyan",
            padding=(1, 2),
        )
    
    def _print_summary(self) -> None:
        """Print final summary after processing completes."""
        elapsed = self.elapsed_seconds
        
        # Create summary table
        summary = Table(title="Processing Summary", show_header=False, box=None)
        summary.add_column(justify="right", style="cyan")
        summary.add_column(justify="left", style="white")
        
        summary.add_row("Total Jobs:", f"{self._total_jobs:,}")
        summary.add_row("Completed:", f"{self._jobs_completed:,}")
        summary.add_row("Successful:", f"[green]{self._jobs_successful:,}[/green]")
        summary.add_row("Failed:", f"[red]{self._jobs_failed:,}[/red]")
        summary.add_row("Retried:", f"{self._jobs_retried:,}")
        summary.add_row("Elapsed Time:", self._format_duration(elapsed))
        summary.add_row("Throughput:", f"{self.throughput:.2f} jobs/sec")
        
        if self._jobs_completed > 0:
            avg_time = self._total_processing_time_ms / self._jobs_completed
            summary.add_row("Avg Processing Time:", f"{avg_time:.0f}ms")
            
            success_rate = (self._jobs_successful / self._jobs_completed) * 100
            summary.add_row("Success Rate:", f"{success_rate:.1f}%")
        
        self._console.print()
        self._console.print(summary)
        self._console.print()
    
    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds since start."""
        if not self._start_time:
            return 0.0
        return time.time() - self._start_time
    
    @property
    def throughput(self) -> float:
        """Calculate current throughput in jobs per second."""
        elapsed = self.elapsed_seconds
        if elapsed == 0:
            return 0.0
        return self._jobs_completed / elapsed
    
    @property
    def eta_seconds(self) -> float:
        """Estimate time remaining in seconds."""
        if self._jobs_completed == 0 or self.throughput == 0:
            return 0.0
        
        remaining_jobs = self._total_jobs - self._jobs_completed
        return remaining_jobs / self.throughput
    
    @property
    def stats(self) -> Dict:
        """Get current statistics as a dictionary."""
        return {
            "total_jobs": self._total_jobs,
            "jobs_completed": self._jobs_completed,
            "jobs_successful": self._jobs_successful,
            "jobs_failed": self._jobs_failed,
            "jobs_retried": self._jobs_retried,
            "queue_size": self._queue_size,
            "active_workers": self._active_workers,
            "elapsed_seconds": self.elapsed_seconds,
            "throughput": self.throughput,
            "eta_seconds": self.eta_seconds,
        }
    
    @property
    def is_started(self) -> bool:
        """Check if tracker is started."""
        return self._is_started
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to human-readable string."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


@contextmanager
def track_progress(
    total_jobs: int,
    worker_count: int = 1,
    enable_logging: bool = True,
):
    """
    Context manager for progress tracking.
    
    Example:
        with track_progress(total_jobs=1000, worker_count=5) as tracker:
            for result in process_jobs():
                await tracker.update_job_completed(result)
    
    Args:
        total_jobs: Total number of jobs to process.
        worker_count: Number of concurrent workers.
        enable_logging: Enable structured logging.
        
    Yields:
        ProgressTracker instance.
    """
    tracker = ProgressTracker(
        total_jobs=total_jobs,
        worker_count=worker_count,
        enable_logging=enable_logging,
    )
    
    try:
        tracker.start()
        yield tracker
    finally:
        tracker.stop()
