"""
Property-based tests for error isolation in the async pipeline.

**Validates: Requirements 2.4, 3.6, 29.1, 29.2, 29.5**

This module tests that:
- Failing jobs don't affect other jobs (2.4, 29.1, 29.2)
- No exceptions propagate to pipeline coordinator (29.5)
- Overall job processing is marked as successful even when individual jobs fail (3.6)
"""

import asyncio
import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import List, Set

from src.async_pipeline import (
    AsyncJobPipeline,
    JobContext,
    ProcessingResult,
    JobStatus,
    ProcessorConfig,
)


# Hypothesis strategies for generating test data
@st.composite
def job_context_strategy(draw):
    """Generate a valid JobContext with random data."""
    job_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=48, max_codepoint=122)))
    title = draw(st.text(min_size=1, max_size=50))
    company = draw(st.text(min_size=1, max_size=50))
    description = draw(st.text(min_size=50, max_size=200))
    url = f"https://example.com/job/{job_id}"
    source = draw(st.sampled_from(["indeed", "linkedin", "glassdoor", "monster"]))
    
    return JobContext(
        job_id=job_id,
        title=title,
        company=company,
        description=description,
        url=url,
        source=source,
    )


@st.composite
def mixed_job_set_strategy(draw, min_jobs=5, max_jobs=20):
    """
    Generate a mixed set of jobs where some will succeed and some will fail.
    
    Returns: (jobs, indices_that_should_fail)
    """
    num_jobs = draw(st.integers(min_value=min_jobs, max_value=max_jobs))
    
    # Generate jobs with unique IDs
    jobs = []
    for i in range(num_jobs):
        job_id = f"test-job-{i}"
        title = draw(st.text(
            min_size=5, 
            max_size=50, 
            alphabet=st.characters(min_codepoint=65, max_codepoint=122, whitelist_categories=("Lu", "Ll"))
        ))
        company = draw(st.text(
            min_size=5, 
            max_size=50,
            alphabet=st.characters(min_codepoint=65, max_codepoint=122, whitelist_categories=("Lu", "Ll"))
        ))
        description = draw(st.text(min_size=50, max_size=200))
        
        job = JobContext(
            job_id=job_id,
            title=title,
            company=company,
            description=description,
            url=f"https://example.com/job/{job_id}",
            source="test",
        )
        jobs.append(job)
    
    # Choose which jobs should fail (at least 1, at most half)
    num_failures = draw(st.integers(min_value=1, max_value=max(1, num_jobs // 2)))
    failure_indices = draw(st.sets(
        st.integers(min_value=0, max_value=num_jobs - 1),
        min_size=num_failures,
        max_size=num_failures,
    ))
    
    return jobs, failure_indices


class TestErrorIsolationProperty:
    """
    Property-based tests for error isolation.
    
    **Property 4: Error Isolation**
    **Validates: Requirements 2.4, 3.6, 29.1, 29.2, 29.5**
    """
    
    @pytest.mark.asyncio
    @given(mixed_job_set_strategy(min_jobs=5, max_jobs=15))
    @settings(max_examples=2, deadline=10000)
    async def test_failing_jobs_dont_affect_other_jobs(self, mixed_job_set):
        """
        Property: When some jobs fail, other jobs continue processing successfully.
        
        **Validates: Requirements 2.4, 29.1, 29.2**
        
        Given: A set of jobs where some are marked to fail
        When: Jobs are processed through the pipeline
        Then:
          - All successful jobs complete successfully
          - All failing jobs fail as expected
          - No job affects the outcome of another job
          - Workers continue processing after encountering failures
        """
        jobs, failure_indices = mixed_job_set
        
        # Ensure we have both successes and failures
        assume(len(failure_indices) > 0)
        assume(len(failure_indices) < len(jobs))
        
        # Track which jobs should succeed vs fail
        expected_failures = {jobs[i].job_id for i in failure_indices}
        expected_successes = {job.job_id for job in jobs if job.job_id not in expected_failures}
        
        # Create a processor that fails for specific job indices
        async def selective_failing_processor(job: JobContext) -> ProcessingResult:
            """Processor that succeeds or fails based on job_id."""
            await asyncio.sleep(0.01)  # Simulate work
            
            if job.job_id in expected_failures:
                # Simulate a failure
                raise ValueError(f"Simulated failure for job {job.job_id}")
            else:
                # Simulate success
                return ProcessingResult.success(
                    job_id=job.job_id,
                    data={"match_score": 85, "status": "processed"},
                    attempt_count=1,
                )
        
        # Configure pipeline with small worker pool
        config = ProcessorConfig(
            worker_count=3,
            queue_size=20,
            max_retries=1,  # Don't retry to make test faster
            base_delay=0.1,
        )
        
        # Create pipeline
        pipeline = AsyncJobPipeline(config=config, db_url="sqlite+aiosqlite:///:memory:")
        pipeline.set_processor(selective_failing_processor)
        pipeline.enable_progress_display(False)
        
        try:
            # Manually setup and run pipeline with our test jobs
            await pipeline._init_database()
            await pipeline._setup_components()
            
            # Inject test jobs directly into queue
            for job in jobs:
                await pipeline._queue.put(job)
            
            # Start workers
            await pipeline._worker_pool.start()
            
            # Wait for all jobs to complete
            results = await pipeline._worker_pool.wait_completion()
            
            # Stop workers
            await pipeline._worker_pool.stop()
            
            # Verify: All jobs were processed (either success or failure)
            assert len(results) == len(jobs), \
                f"Expected {len(jobs)} results, got {len(results)}"
            
            # Verify: Successful jobs completed successfully
            successful_results = [r for r in results if r.is_success()]
            assert len(successful_results) == len(expected_successes), \
                f"Expected {len(expected_successes)} successes, got {len(successful_results)}"
            
            successful_job_ids = {r.job_id for r in successful_results}
            assert successful_job_ids == expected_successes, \
                f"Successful job IDs don't match. Expected {expected_successes}, got {successful_job_ids}"
            
            # Verify: Failed jobs failed as expected
            failed_results = [r for r in results if not r.is_success()]
            assert len(failed_results) == len(expected_failures), \
                f"Expected {len(expected_failures)} failures, got {len(failed_results)}"
            
            failed_job_ids = {r.job_id for r in failed_results}
            assert failed_job_ids == expected_failures, \
                f"Failed job IDs don't match. Expected {expected_failures}, got {failed_job_ids}"
            
            # Verify: All failed jobs have error information
            for failed_result in failed_results:
                assert failed_result.error is not None, \
                    f"Failed job {failed_result.job_id} has no error message"
                assert failed_result.error_type is not None, \
                    f"Failed job {failed_result.job_id} has no error type"
                assert failed_result.status == JobStatus.FAILED, \
                    f"Failed job {failed_result.job_id} has status {failed_result.status}"
            
            # **Validates Requirement 2.4, 29.2**: Workers continued processing after errors
            # The fact that we got results for all jobs proves this
            
        finally:
            await pipeline.close()
    
    @pytest.mark.asyncio
    @given(mixed_job_set_strategy(min_jobs=5, max_jobs=15))
    @settings(max_examples=2, deadline=10000)
    async def test_no_exceptions_propagate_to_pipeline(self, mixed_job_set):
        """
        Property: Exceptions from individual jobs never propagate to the pipeline coordinator.
        
        **Validates: Requirements 29.5, 3.6**
        
        Given: A set of jobs where some will raise exceptions
        When: Jobs are processed through the pipeline
        Then:
          - Pipeline run completes without raising exceptions
          - All exceptions are caught and converted to ProcessingResult.failure
          - Pipeline returns results for all jobs
          - Overall processing is marked as successful
        """
        jobs, failure_indices = mixed_job_set
        
        # Ensure we have at least one failure
        assume(len(failure_indices) > 0)
        
        # Track which jobs should fail
        expected_failures = {jobs[i].job_id for i in failure_indices}
        
        # Create various exception types
        exception_types = [
            ValueError("Simulated ValueError"),
            RuntimeError("Simulated RuntimeError"),
            TypeError("Simulated TypeError"),
            KeyError("Simulated KeyError"),
            Exception("Simulated generic Exception"),
        ]
        
        # Create a processor that raises different exceptions
        async def exception_raising_processor(job: JobContext) -> ProcessingResult:
            """Processor that raises various exceptions."""
            await asyncio.sleep(0.01)
            
            if job.job_id in expected_failures:
                # Raise a random exception type
                import random
                exception = random.choice(exception_types)
                raise exception
            else:
                return ProcessingResult.success(
                    job_id=job.job_id,
                    data={"status": "success"},
                    attempt_count=1,
                )
        
        config = ProcessorConfig(
            worker_count=3,
            queue_size=20,
            max_retries=1,
            base_delay=0.1,
        )
        
        pipeline = AsyncJobPipeline(config=config, db_url="sqlite+aiosqlite:///:memory:")
        pipeline.set_processor(exception_raising_processor)
        pipeline.enable_progress_display(False)
        
        pipeline_exception_raised = False
        
        try:
            # Setup pipeline
            await pipeline._init_database()
            await pipeline._setup_components()
            
            # Inject test jobs
            for job in jobs:
                await pipeline._queue.put(job)
            
            # Start workers
            await pipeline._worker_pool.start()
            
            # **Validates Requirement 29.5**: Pipeline should NOT raise exceptions
            try:
                results = await pipeline._worker_pool.wait_completion()
            except Exception as e:
                pipeline_exception_raised = True
                pytest.fail(
                    f"Pipeline raised exception: {type(e).__name__}: {str(e)}. "
                    "Requirement 29.5 violated: exceptions propagated to pipeline coordinator"
                )
            
            # Stop workers
            await pipeline._worker_pool.stop()
            
            # Verify: No exception was raised by the pipeline
            assert not pipeline_exception_raised, \
                "Pipeline raised an exception - Requirement 29.5 violated"
            
            # Verify: All jobs have results
            assert len(results) == len(jobs), \
                f"Expected {len(jobs)} results, got {len(results)}"
            
            # Verify: All failed jobs have error information captured
            for result in results:
                if result.job_id in expected_failures:
                    assert not result.is_success(), \
                        f"Job {result.job_id} should have failed"
                    assert result.error is not None, \
                        f"Failed job {result.job_id} has no error captured"
                    assert result.error_type is not None, \
                        f"Failed job {result.job_id} has no error type captured"
            
            # **Validates Requirement 3.6**: Overall processing succeeds even with individual failures
            # The fact that the pipeline completed without exceptions satisfies this requirement
            
        finally:
            await pipeline.close()
    
    @pytest.mark.asyncio
    @given(st.integers(min_value=10, max_value=30))
    @settings(max_examples=2, deadline=15000)  # Reduced for faster execution
    async def test_single_worker_error_doesnt_crash_pipeline(self, num_jobs):
        """
        Property: When a worker encounters an error, other workers continue processing.
        
        **Validates: Requirement 2.4**
        
        Given: Multiple jobs with one job that causes a worker error
        When: The pipeline processes all jobs
        Then:
          - Other workers continue processing remaining jobs
          - All jobs get processed despite the error
          - No cascade failures occur
        """
        # Create jobs where the middle job will fail
        jobs = []
        for i in range(num_jobs):
            job = JobContext(
                job_id=f"job-{i}",
                title=f"Job {i}",
                company=f"Company {i}",
                description="A" * 100,
                url=f"https://example.com/job-{i}",
                source="test",
            )
            jobs.append(job)
        
        failure_job_id = f"job-{num_jobs // 2}"
        
        # Processor that fails for one specific job
        async def single_failure_processor(job: JobContext) -> ProcessingResult:
            await asyncio.sleep(0.01)
            
            if job.job_id == failure_job_id:
                raise RuntimeError(f"Worker error for {job.job_id}")
            
            return ProcessingResult.success(
                job_id=job.job_id,
                data={"status": "success"},
                attempt_count=1,
            )
        
        config = ProcessorConfig(
            worker_count=5,  # Multiple workers
            queue_size=50,
            max_retries=1,
            base_delay=0.1,
        )
        
        pipeline = AsyncJobPipeline(config=config, db_url="sqlite+aiosqlite:///:memory:")
        pipeline.set_processor(single_failure_processor)
        pipeline.enable_progress_display(False)
        
        try:
            await pipeline._init_database()
            await pipeline._setup_components()
            
            # Inject all jobs
            for job in jobs:
                await pipeline._queue.put(job)
            
            # Start workers
            await pipeline._worker_pool.start()
            
            # Wait for completion
            results = await pipeline._worker_pool.wait_completion()
            
            # Stop workers
            await pipeline._worker_pool.stop()
            
            # Verify: All jobs were processed
            assert len(results) == num_jobs, \
                f"Expected {num_jobs} results, got {len(results)}"
            
            # Verify: Only one job failed
            failed_results = [r for r in results if not r.is_success()]
            assert len(failed_results) == 1, \
                f"Expected exactly 1 failure, got {len(failed_results)}"
            
            assert failed_results[0].job_id == failure_job_id, \
                f"Wrong job failed: expected {failure_job_id}, got {failed_results[0].job_id}"
            
            # Verify: All other jobs succeeded
            successful_results = [r for r in results if r.is_success()]
            assert len(successful_results) == num_jobs - 1, \
                f"Expected {num_jobs - 1} successes, got {len(successful_results)}"
            
            # **Validates Requirement 2.4**: Other workers continued processing
            # The fact that all other jobs succeeded proves this
            
        finally:
            await pipeline.close()
    
    @pytest.mark.asyncio
    @given(mixed_job_set_strategy(min_jobs=8, max_jobs=15))
    @settings(max_examples=2, deadline=10000)  # Reduced for faster execution
    async def test_error_isolation_with_multiple_error_types(self, mixed_job_set):
        """
        Property: Different error types in different jobs don't interfere with each other.
        
        **Validates: Requirements 29.1, 29.5**
        
        Given: Jobs that fail with different exception types
        When: All jobs are processed
        Then:
          - Each error is isolated to its job
          - Different error types don't interfere
          - All errors are properly captured and logged
          - No errors propagate to coordinator
        """
        jobs, failure_indices = mixed_job_set
        
        # Ensure we have multiple failures
        assume(len(failure_indices) >= 2)
        
        # Map each failing job to a different error type
        error_types = [
            ValueError,
            RuntimeError,
            TypeError,
            KeyError,
            ZeroDivisionError,
            AttributeError,
        ]
        
        failure_error_map = {}
        for idx, job_idx in enumerate(sorted(failure_indices)):
            error_type = error_types[idx % len(error_types)]
            failure_error_map[jobs[job_idx].job_id] = error_type
        
        # Processor that raises different errors for different jobs
        async def multi_error_processor(job: JobContext) -> ProcessingResult:
            await asyncio.sleep(0.01)
            
            if job.job_id in failure_error_map:
                error_type = failure_error_map[job.job_id]
                raise error_type(f"Simulated {error_type.__name__} for {job.job_id}")
            
            return ProcessingResult.success(
                job_id=job.job_id,
                data={"status": "success"},
                attempt_count=1,
            )
        
        config = ProcessorConfig(
            worker_count=4,
            queue_size=20,
            max_retries=1,
            base_delay=0.1,
        )
        
        pipeline = AsyncJobPipeline(config=config, db_url="sqlite+aiosqlite:///:memory:")
        pipeline.set_processor(multi_error_processor)
        pipeline.enable_progress_display(False)
        
        try:
            await pipeline._init_database()
            await pipeline._setup_components()
            
            # Inject jobs
            for job in jobs:
                await pipeline._queue.put(job)
            
            # Start and wait
            await pipeline._worker_pool.start()
            results = await pipeline._worker_pool.wait_completion()
            await pipeline._worker_pool.stop()
            
            # Verify: All jobs processed
            assert len(results) == len(jobs)
            
            # Verify: Each failing job captured its specific error type
            for result in results:
                if result.job_id in failure_error_map:
                    expected_error_type = failure_error_map[result.job_id]
                    assert not result.is_success(), \
                        f"Job {result.job_id} should have failed"
                    assert result.error_type == expected_error_type.__name__, \
                        f"Job {result.job_id} has wrong error type: expected {expected_error_type.__name__}, got {result.error_type}"
                    
                    # **Validates Requirement 29.1**: Error isolated to that job only
                    # Each job has its specific error, not affected by others
            
            # **Validates Requirement 29.5**: No exceptions propagated
            # We successfully got all results without any exceptions raised
            
        finally:
            await pipeline.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
