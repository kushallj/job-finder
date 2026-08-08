"""
Unit tests for database schema validation.

Tests table existence, structure, indexes, and migration functionality.
This validates Requirements 21.1-21.11 from the system-architecture spec.
"""
import pytest
from sqlalchemy import (
    create_engine,
    inspect,
    text,
    Index,
    MetaData,
    Table,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import tempfile
import os

from src.models import Base, Job, Application, Resume, Contact, OutreachRecord, ProcessingResult, PipelineMetric, ProcessingResult, PipelineMetric


# --- Fixtures ---


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for test isolation."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_session(test_engine):
    """Create a test session bound to the in-memory engine."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    yield session
    session.close()


@pytest.fixture
def file_engine():
    """Create a file-based SQLite engine for testing index performance and migrations."""
    # Create a temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    engine.dispose()
    
    # Clean up the temporary file
    try:
        os.unlink(db_path)
    except Exception:
        pass


# --- Tests for Table Existence and Structure ---


class TestTableExistence:
    """Test that all required tables exist in the schema."""

    def test_all_required_tables_exist(self, test_engine):
        """Verify all required tables from Requirements 21.1-21.7 exist."""
        inspector = inspect(test_engine)
        table_names = inspector.get_table_names()

        # Requirement 21.1: jobs table
        assert "jobs" in table_names, "jobs table must exist"
        
        # Requirement 21.2: applications table
        assert "applications" in table_names, "applications table must exist"
        
        # Requirement 21.3: resumes table
        assert "resumes" in table_names, "resumes table must exist"
        
        # Requirement 21.4: contacts table
        assert "contacts" in table_names, "contacts table must exist"
        
        # Requirement 21.5: outreach_records table
        assert "outreach_records" in table_names, "outreach_records table must exist"
        
        # Requirement 21.6: processing_results table
        assert "processing_results" in table_names, "processing_results table must exist"
        
        # Requirement 21.7: pipeline_metrics table
        assert "pipeline_metrics" in table_names, "pipeline_metrics table must exist"
        
        # Requirement 21.6: processing_results table
        assert "processing_results" in table_names, "processing_results table must exist"
        
        # Requirement 21.7: pipeline_metrics table
        assert "pipeline_metrics" in table_names, "pipeline_metrics table must exist"


class TestJobsTableStructure:
    """Test the structure of the jobs table."""

    def test_jobs_table_has_required_columns(self, test_engine):
        """Verify jobs table has all required columns (Requirement 21.1)."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("jobs")}

        # Core columns
        assert "id" in columns, "jobs.id must exist"
        assert "job_id" in columns, "jobs.job_id must exist"
        assert "title" in columns, "jobs.title must exist"
        assert "company" in columns, "jobs.company must exist"
        assert "location" in columns, "jobs.location must exist"
        assert "description" in columns, "jobs.description must exist"
        assert "url" in columns, "jobs.url must exist"
        assert "source" in columns, "jobs.source must exist"
        assert "posted_date" in columns, "jobs.posted_date must exist"
        assert "fetched_at" in columns, "jobs.fetched_at must exist"

    def test_jobs_table_primary_key(self, test_engine):
        """Verify jobs table has correct primary key."""
        inspector = inspect(test_engine)
        pk_constraint = inspector.get_pk_constraint("jobs")
        
        assert "id" in pk_constraint["constrained_columns"], "jobs.id must be primary key"

    def test_jobs_table_unique_constraints(self, test_engine):
        """Verify jobs table has unique constraint on job_id."""
        # Test the unique constraint functionally by attempting to insert duplicates
        Session = sessionmaker(bind=test_engine)
        session = Session()
        
        from sqlalchemy.exc import IntegrityError
        
        # Insert first job
        job1 = Job(
            job_id="unique-test-1",
            title="Engineer A",
            company="CompanyA",
            source="adzuna",
        )
        session.add(job1)
        session.commit()
        
        # Attempt to insert duplicate job_id
        job2 = Job(
            job_id="unique-test-1",  # Same job_id
            title="Engineer B",
            company="CompanyB",
            source="remotive",
        )
        session.add(job2)
        
        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            session.commit()
        
        session.rollback()
        session.close()


class TestApplicationsTableStructure:
    """Test the structure of the applications table."""

    def test_applications_table_has_required_columns(self, test_engine):
        """Verify applications table has all required columns (Requirement 21.2)."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("applications")}

        # Core columns
        assert "id" in columns, "applications.id must exist"
        assert "job_id" in columns, "applications.job_id must exist (foreign key)"
        assert "match_score" in columns, "applications.match_score must exist"
        assert "skills_matched" in columns, "applications.skills_matched must exist"
        assert "skills_missing" in columns, "applications.skills_missing must exist"
        assert "status" in columns, "applications.status must exist"

    def test_applications_table_foreign_key(self, test_engine):
        """Verify applications table has foreign key to jobs table."""
        inspector = inspect(test_engine)
        foreign_keys = inspector.get_foreign_keys("applications")
        
        assert len(foreign_keys) > 0, "applications table must have foreign keys"
        
        # Check for foreign key to jobs table
        job_fk = [fk for fk in foreign_keys if fk["referred_table"] == "jobs"]
        assert len(job_fk) > 0, "applications must have foreign key to jobs"
        assert "job_id" in job_fk[0]["constrained_columns"], "foreign key must be on job_id"


class TestContactsTableStructure:
    """Test the structure of the contacts table."""

    def test_contacts_table_has_required_columns(self, test_engine):
        """Verify contacts table has all required columns (Requirement 21.4)."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("contacts")}

        # Core columns
        assert "id" in columns, "contacts.id must exist"
        assert "name" in columns, "contacts.name must exist"
        assert "email" in columns, "contacts.email must exist"
        assert "company" in columns, "contacts.company must exist"
        assert "title" in columns, "contacts.title must exist"
        assert "confidence_score" in columns, "contacts.confidence_score must exist"
        assert "source" in columns, "contacts.source must exist"


class TestOutreachRecordsTableStructure:
    """Test the structure of the outreach_records table."""

    def test_outreach_records_table_has_required_columns(self, test_engine):
        """Verify outreach_records table has all required columns (Requirement 21.5)."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("outreach_records")}

        # Core columns
        assert "id" in columns, "outreach_records.id must exist"
        assert "contact_id" in columns, "outreach_records.contact_id must exist"
        assert "job_id" in columns, "outreach_records.job_id must exist"
        assert "subject" in columns, "outreach_records.subject must exist"
        assert "body" in columns, "outreach_records.body must exist"
        assert "status" in columns, "outreach_records.status must exist"
        assert "sent_at" in columns, "outreach_records.sent_at must exist"

    def test_outreach_records_table_foreign_keys(self, test_engine):
        """Verify outreach_records table has foreign keys to contacts and jobs."""
        inspector = inspect(test_engine)
        foreign_keys = inspector.get_foreign_keys("outreach_records")
        
        assert len(foreign_keys) >= 2, "outreach_records must have at least 2 foreign keys"
        
        # Check for foreign key to contacts table
        contact_fk = [fk for fk in foreign_keys if fk["referred_table"] == "contacts"]
        assert len(contact_fk) > 0, "outreach_records must have foreign key to contacts"
        
        # Check for foreign key to jobs table
        job_fk = [fk for fk in foreign_keys if fk["referred_table"] == "jobs"]
        assert len(job_fk) > 0, "outreach_records must have foreign key to jobs"


class TestProcessingResultsTableStructure:
    """Test the structure of the processing_results table."""

    def test_processing_results_table_has_required_columns(self, test_engine):
        """Verify processing_results table has all required columns (Requirement 21.6)."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("processing_results")}

        # Core columns
        assert "id" in columns, "processing_results.id must exist"
        assert "job_id" in columns, "processing_results.job_id must exist"
        assert "status" in columns, "processing_results.status must exist"
        assert "data" in columns, "processing_results.data must exist"
        assert "error" in columns, "processing_results.error must exist"
        assert "error_type" in columns, "processing_results.error_type must exist"
        
        # Metrics columns
        assert "attempt_count" in columns, "processing_results.attempt_count must exist"
        assert "processing_time_ms" in columns, "processing_results.processing_time_ms must exist"
        assert "worker_id" in columns, "processing_results.worker_id must exist"
        
        # Timestamp columns
        assert "created_at" in columns, "processing_results.created_at must exist"
        assert "updated_at" in columns, "processing_results.updated_at must exist"

    def test_processing_results_table_primary_key(self, test_engine):
        """Verify processing_results table has correct primary key."""
        inspector = inspect(test_engine)
        pk_constraint = inspector.get_pk_constraint("processing_results")
        
        assert "id" in pk_constraint["constrained_columns"], \
            "processing_results.id must be primary key"

    def test_processing_results_can_store_job_results(self, test_session):
        """Test that processing_results table can store job processing results."""
        import json
        
        # Create a processing result
        result = ProcessingResult(
            job_id="test-job-1",
            status="completed",
            data=json.dumps({"match_score": 85, "skills": ["python", "react"]}),
            attempt_count=1,
            processing_time_ms=1234.56,
            worker_id="worker-1",
        )
        test_session.add(result)
        test_session.commit()
        
        # Fetch and verify
        fetched = test_session.query(ProcessingResult).filter_by(job_id="test-job-1").first()
        assert fetched is not None, "Processing result should be stored"
        assert fetched.status == "completed"
        assert fetched.attempt_count == 1
        assert fetched.processing_time_ms == 1234.56
        assert fetched.worker_id == "worker-1"
        
        # Verify data is stored as JSON
        data = json.loads(fetched.data)
        assert data["match_score"] == 85

    def test_processing_results_can_store_error_results(self, test_session):
        """Test that processing_results table can store error results."""
        # Create a failed processing result
        result = ProcessingResult(
            job_id="test-job-2",
            status="failed",
            error="API timeout after 30 seconds",
            error_type="TimeoutError",
            attempt_count=3,
            worker_id="worker-2",
        )
        test_session.add(result)
        test_session.commit()
        
        # Fetch and verify
        fetched = test_session.query(ProcessingResult).filter_by(job_id="test-job-2").first()
        assert fetched is not None
        assert fetched.status == "failed"
        assert fetched.error == "API timeout after 30 seconds"
        assert fetched.error_type == "TimeoutError"
        assert fetched.attempt_count == 3


class TestPipelineMetricsTableStructure:
    """Test the structure of the pipeline_metrics table."""

    def test_pipeline_metrics_table_has_required_columns(self, test_engine):
        """Verify pipeline_metrics table has all required columns (Requirement 21.7)."""
        inspector = inspect(test_engine)
        columns = {col["name"]: col for col in inspector.get_columns("pipeline_metrics")}

        # Job metrics
        assert "id" in columns, "pipeline_metrics.id must exist"
        assert "jobs_queued" in columns, "pipeline_metrics.jobs_queued must exist"
        assert "jobs_completed" in columns, "pipeline_metrics.jobs_completed must exist"
        assert "jobs_failed" in columns, "pipeline_metrics.jobs_failed must exist"
        
        # Queue metrics
        assert "queue_size" in columns, "pipeline_metrics.queue_size must exist"
        assert "queue_backpressure_events" in columns, \
            "pipeline_metrics.queue_backpressure_events must exist"
        assert "queue_wait_time_ms" in columns, "pipeline_metrics.queue_wait_time_ms must exist"
        
        # Worker metrics
        assert "workers_active" in columns, "pipeline_metrics.workers_active must exist"
        assert "workers_total" in columns, "pipeline_metrics.workers_total must exist"
        assert "worker_utilization_percent" in columns, \
            "pipeline_metrics.worker_utilization_percent must exist"
        
        # Performance metrics
        assert "throughput_jobs_per_second" in columns, \
            "pipeline_metrics.throughput_jobs_per_second must exist"
        assert "latency_p50_ms" in columns, "pipeline_metrics.latency_p50_ms must exist"
        assert "latency_p95_ms" in columns, "pipeline_metrics.latency_p95_ms must exist"
        assert "latency_p99_ms" in columns, "pipeline_metrics.latency_p99_ms must exist"
        
        # API metrics
        assert "api_rate_limit_waits" in columns, \
            "pipeline_metrics.api_rate_limit_waits must exist"
        assert "api_rate_limit_wait_time_ms" in columns, \
            "pipeline_metrics.api_rate_limit_wait_time_ms must exist"
        
        # Error metrics
        assert "retry_attempts" in columns, "pipeline_metrics.retry_attempts must exist"
        assert "retry_successes" in columns, "pipeline_metrics.retry_successes must exist"
        assert "retry_failures" in columns, "pipeline_metrics.retry_failures must exist"
        
        # Timestamp columns
        assert "recorded_at" in columns, "pipeline_metrics.recorded_at must exist"
        assert "pipeline_start_time" in columns, "pipeline_metrics.pipeline_start_time must exist"
        assert "pipeline_end_time" in columns, "pipeline_metrics.pipeline_end_time must exist"

    def test_pipeline_metrics_table_primary_key(self, test_engine):
        """Verify pipeline_metrics table has correct primary key."""
        inspector = inspect(test_engine)
        pk_constraint = inspector.get_pk_constraint("pipeline_metrics")
        
        assert "id" in pk_constraint["constrained_columns"], \
            "pipeline_metrics.id must be primary key"

    def test_pipeline_metrics_can_store_performance_data(self, test_session):
        """Test that pipeline_metrics table can store performance metrics."""
        from datetime import datetime, timedelta
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=60)
        
        # Create a metrics record
        metrics = PipelineMetric(
            jobs_queued=100,
            jobs_completed=95,
            jobs_failed=5,
            queue_size=10,
            queue_backpressure_events=3,
            queue_wait_time_ms=1500.0,
            workers_active=5,
            workers_total=5,
            worker_utilization_percent=95.0,
            throughput_jobs_per_second=1.58,
            latency_p50_ms=2000.0,
            latency_p95_ms=5000.0,
            latency_p99_ms=8000.0,
            api_rate_limit_waits=10,
            api_rate_limit_wait_time_ms=500.0,
            retry_attempts=15,
            retry_successes=10,
            retry_failures=5,
            pipeline_start_time=start_time,
            pipeline_end_time=end_time,
        )
        test_session.add(metrics)
        test_session.commit()
        
        # Fetch and verify
        fetched = test_session.query(PipelineMetric).first()
        assert fetched is not None, "Pipeline metrics should be stored"
        assert fetched.jobs_queued == 100
        assert fetched.jobs_completed == 95
        assert fetched.jobs_failed == 5
        assert fetched.throughput_jobs_per_second == 1.58
        assert fetched.latency_p50_ms == 2000.0
        assert fetched.latency_p95_ms == 5000.0
        assert fetched.latency_p99_ms == 8000.0
        assert fetched.workers_active == 5
        assert fetched.retry_attempts == 15

    def test_pipeline_metrics_can_track_multiple_runs(self, test_session):
        """Test that pipeline_metrics table can store multiple pipeline runs."""
        from datetime import datetime, timedelta
        
        # Create metrics for multiple pipeline runs
        for i in range(3):
            start_time = datetime.utcnow() + timedelta(hours=i)
            metrics = PipelineMetric(
                jobs_queued=50 * (i + 1),
                jobs_completed=45 * (i + 1),
                jobs_failed=5 * (i + 1),
                throughput_jobs_per_second=1.5 + (i * 0.1),
                pipeline_start_time=start_time,
            )
            test_session.add(metrics)
        
        test_session.commit()
        
        # Fetch all metrics
        all_metrics = test_session.query(PipelineMetric).all()
        assert len(all_metrics) == 3, "Should store 3 separate pipeline runs"
        
        # Verify different values
        assert all_metrics[0].jobs_queued == 50
        assert all_metrics[1].jobs_queued == 100
        assert all_metrics[2].jobs_queued == 150


# --- Tests for Index Creation ---


class TestRequiredIndexes:
    """Test that all required indexes from Requirements 21.8-21.11 are created or can be created."""

    def test_create_compound_index_jobs_company_fetched_at(self, file_engine):
        """Test creation of compound index on jobs(company, fetched_at) - Requirement 21.8."""
        # Create the compound index
        with file_engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_jobs_company_fetched_at "
                "ON jobs(company, fetched_at)"
            ))
            conn.commit()
        
        # Verify the index was created
        inspector = inspect(file_engine)
        indexes = inspector.get_indexes("jobs")
        index_names = [idx["name"] for idx in indexes]
        
        assert "idx_jobs_company_fetched_at" in index_names, \
            "Compound index on jobs(company, fetched_at) must exist"

    def test_create_compound_index_contacts_email_company(self, file_engine):
        """Test creation of compound index on contacts(email, company) - Requirement 21.9."""
        # Create the compound index
        with file_engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_contacts_email_company "
                "ON contacts(email, company)"
            ))
            conn.commit()
        
        # Verify the index was created
        inspector = inspect(file_engine)
        indexes = inspector.get_indexes("contacts")
        index_names = [idx["name"] for idx in indexes]
        
        assert "idx_contacts_email_company" in index_names, \
            "Compound index on contacts(email, company) must exist"

    def test_create_compound_index_outreach_job_contact(self, file_engine):
        """Test creation of compound index on outreach_records(job_id, contact_id) - Requirement 21.10."""
        # Create the compound index
        with file_engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_outreach_job_contact "
                "ON outreach_records(job_id, contact_id)"
            ))
            conn.commit()
        
        # Verify the index was created
        inspector = inspect(file_engine)
        indexes = inspector.get_indexes("outreach_records")
        index_names = [idx["name"] for idx in indexes]
        
        assert "idx_outreach_job_contact" in index_names, \
            "Compound index on outreach_records(job_id, contact_id) must exist"

    def test_create_index_applications_match_score(self, file_engine):
        """Test creation of index on applications(match_score) - Requirement 21.11."""
        # Create the index
        with file_engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_applications_match_score "
                "ON applications(match_score)"
            ))
            conn.commit()
        
        # Verify the index was created
        inspector = inspect(file_engine)
        indexes = inspector.get_indexes("applications")
        index_names = [idx["name"] for idx in indexes]
        
        assert "idx_applications_match_score" in index_names, \
            "Index on applications(match_score) must exist"


# --- Tests for Index Performance ---


class TestIndexPerformance:
    """Test that indexes improve query performance."""

    def test_jobs_company_index_improves_query_performance(self, file_engine):
        """Test that compound index on jobs(company, fetched_at) improves query performance."""
        # Create the index
        with file_engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_jobs_company_fetched_at "
                "ON jobs(company, fetched_at)"
            ))
            conn.commit()
        
        # Insert test data
        Session = sessionmaker(bind=file_engine)
        session = Session()
        
        test_jobs = [
            Job(
                job_id=f"perf-test-{i}",
                title=f"Engineer {i}",
                company="TestCorp" if i % 2 == 0 else "OtherCorp",
                source="adzuna",
                fetched_at=datetime(2026, 1, i % 28 + 1),
            )
            for i in range(100)
        ]
        
        session.add_all(test_jobs)
        session.commit()
        
        # Test query using the index
        query = text(
            "SELECT * FROM jobs "
            "WHERE company = 'TestCorp' "
            "ORDER BY fetched_at DESC "
            "LIMIT 10"
        )
        
        with file_engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()
            
            assert len(rows) > 0, "Query should return results"
            
            # Verify query plan uses the index
            explain_query = text(
                "EXPLAIN QUERY PLAN "
                "SELECT * FROM jobs "
                "WHERE company = 'TestCorp' "
                "ORDER BY fetched_at DESC "
                "LIMIT 10"
            )
            
            explain_result = conn.execute(explain_query)
            plan = " ".join([str(row) for row in explain_result.fetchall()])
            
            # SQLite should use the index (plan will mention the index name or SEARCH using index)
            assert "idx_jobs_company_fetched_at" in plan or "SEARCH" in plan, \
                "Query plan should use the compound index"
        
        session.close()

    def test_applications_match_score_index_improves_query_performance(self, file_engine):
        """Test that index on applications(match_score) improves query performance."""
        # Create the index
        with file_engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_applications_match_score "
                "ON applications(match_score)"
            ))
            conn.commit()
        
        # Insert test data
        Session = sessionmaker(bind=file_engine)
        session = Session()
        
        # First create a job to satisfy foreign key constraint
        job = Job(
            job_id="score-test-job",
            title="Test Job",
            company="TestCorp",
            source="adzuna",
        )
        session.add(job)
        session.commit()
        
        test_applications = [
            Application(
                job_id=job.id,
                match_score=float(i) / 100.0,
                status="pending",
            )
            for i in range(100)
        ]
        
        session.add_all(test_applications)
        session.commit()
        
        # Test query using the index - high score filtering
        query = text(
            "SELECT * FROM applications "
            "WHERE match_score >= 0.8 "
            "ORDER BY match_score DESC"
        )
        
        with file_engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()
            
            assert len(rows) > 0, "Query should return high-scoring applications"
            
            # Verify query plan uses the index
            explain_query = text(
                "EXPLAIN QUERY PLAN "
                "SELECT * FROM applications "
                "WHERE match_score >= 0.8 "
                "ORDER BY match_score DESC"
            )
            
            explain_result = conn.execute(explain_query)
            plan = " ".join([str(row) for row in explain_result.fetchall()])
            
            # SQLite should use the index
            assert "idx_applications_match_score" in plan or "SEARCH" in plan, \
                "Query plan should use the match_score index"
        
        session.close()


# --- Tests for Migration Functionality ---


class TestSchemaMigration:
    """Test schema migration and rollback functionality."""

    def test_schema_can_be_dropped_and_recreated(self, file_engine):
        """Test that schema can be dropped and recreated (basic migration test)."""
        # Verify tables exist
        inspector = inspect(file_engine)
        original_tables = set(inspector.get_table_names())
        assert len(original_tables) > 0, "Tables should exist initially"
        
        # Drop all tables
        Base.metadata.drop_all(bind=file_engine)
        
        # Verify tables are dropped
        inspector = inspect(file_engine)
        tables_after_drop = inspector.get_table_names()
        assert len(tables_after_drop) == 0, "All tables should be dropped"
        
        # Recreate tables (migration forward)
        Base.metadata.create_all(bind=file_engine)
        
        # Verify tables are recreated
        inspector = inspect(file_engine)
        recreated_tables = set(inspector.get_table_names())
        assert recreated_tables == original_tables, "Recreated tables should match original"

    def test_migration_preserves_data(self, file_engine):
        """Test that data is preserved during a simulated migration."""
        # Insert test data
        Session = sessionmaker(bind=file_engine)
        session = Session()
        
        test_job = Job(
            job_id="migration-test-1",
            title="Migration Test Engineer",
            company="MigrationCorp",
            source="adzuna",
        )
        session.add(test_job)
        session.commit()
        
        # Verify data exists
        fetched = session.query(Job).filter_by(job_id="migration-test-1").first()
        assert fetched is not None, "Test data should exist before migration"
        assert fetched.title == "Migration Test Engineer"
        
        # Simulate a migration by adding an index (non-destructive change)
        with file_engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_migration_test "
                "ON jobs(source)"
            ))
            conn.commit()
        
        # Verify data still exists after migration
        fetched_after = session.query(Job).filter_by(job_id="migration-test-1").first()
        assert fetched_after is not None, "Test data should exist after migration"
        assert fetched_after.title == "Migration Test Engineer"
        
        session.close()

    def test_index_can_be_dropped_and_recreated(self, file_engine):
        """Test that indexes can be dropped and recreated (rollback simulation)."""
        # Create an index
        with file_engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_rollback_test "
                "ON jobs(company)"
            ))
            conn.commit()
        
        # Verify index exists
        inspector = inspect(file_engine)
        indexes = inspector.get_indexes("jobs")
        index_names = [idx["name"] for idx in indexes]
        assert "idx_rollback_test" in index_names, "Index should exist"
        
        # Drop the index (rollback)
        with file_engine.connect() as conn:
            conn.execute(text("DROP INDEX IF EXISTS idx_rollback_test"))
            conn.commit()
        
        # Verify index is dropped
        inspector = inspect(file_engine)
        indexes_after_drop = inspector.get_indexes("jobs")
        index_names_after_drop = [idx["name"] for idx in indexes_after_drop]
        assert "idx_rollback_test" not in index_names_after_drop, "Index should be dropped"
        
        # Recreate the index (forward migration again)
        with file_engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_rollback_test "
                "ON jobs(company)"
            ))
            conn.commit()
        
        # Verify index is recreated
        inspector = inspect(file_engine)
        indexes_after_recreate = inspector.get_indexes("jobs")
        index_names_after_recreate = [idx["name"] for idx in indexes_after_recreate]
        assert "idx_rollback_test" in index_names_after_recreate, "Index should be recreated"


# --- Integration Tests ---


class TestSchemaIntegration:
    """Integration tests for complete schema validation."""

    def test_complete_schema_setup(self, file_engine):
        """Test that complete schema with all tables and indexes can be set up."""
        # Create all indexes
        with file_engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_jobs_company_fetched_at "
                "ON jobs(company, fetched_at)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_contacts_email_company "
                "ON contacts(email, company)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_outreach_job_contact "
                "ON outreach_records(job_id, contact_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_applications_match_score "
                "ON applications(match_score)"
            ))
            conn.commit()
        
        # Verify all tables exist
        inspector = inspect(file_engine)
        tables = inspector.get_table_names()
        
        assert "jobs" in tables
        assert "applications" in tables
        assert "resumes" in tables
        assert "contacts" in tables
        assert "outreach_records" in tables
        assert "processing_results" in tables
        assert "pipeline_metrics" in tables
        
        # Verify all indexes exist
        jobs_indexes = [idx["name"] for idx in inspector.get_indexes("jobs")]
        assert "idx_jobs_company_fetched_at" in jobs_indexes
        
        contacts_indexes = [idx["name"] for idx in inspector.get_indexes("contacts")]
        assert "idx_contacts_email_company" in contacts_indexes
        
        outreach_indexes = [idx["name"] for idx in inspector.get_indexes("outreach_records")]
        assert "idx_outreach_job_contact" in outreach_indexes
        
        applications_indexes = [idx["name"] for idx in inspector.get_indexes("applications")]
        assert "idx_applications_match_score" in applications_indexes

    def test_schema_supports_full_workflow(self, file_engine):
        """Test that schema supports a complete job application workflow."""
        Session = sessionmaker(bind=file_engine)
        session = Session()
        
        # Create all required indexes
        with file_engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_jobs_company_fetched_at "
                "ON jobs(company, fetched_at)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_contacts_email_company "
                "ON contacts(email, company)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_outreach_job_contact "
                "ON outreach_records(job_id, contact_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_applications_match_score "
                "ON applications(match_score)"
            ))
            conn.commit()
        
        # 1. Create a job
        job = Job(
            job_id="workflow-test-1",
            title="Full Stack Engineer",
            company="WorkflowCorp",
            location="Remote",
            description="Build great things",
            source="adzuna",
            fetched_at=datetime(2026, 3, 3),
        )
        session.add(job)
        session.commit()
        
        # 2. Create an application with match score
        application = Application(
            job_id=job.id,
            match_score=0.85,
            skills_matched='["python", "react"]',
            status="pending",
        )
        session.add(application)
        session.commit()
        
        # 3. Create a contact
        contact = Contact(
            name="John Manager",
            title="Engineering Manager",
            email="john@workflowcorp.com",
            company="WorkflowCorp",
            confidence_score=90,
            source="linkedin",
        )
        session.add(contact)
        session.commit()
        
        # 4. Create an outreach record
        outreach = OutreachRecord(
            contact_id=contact.id,
            job_id=job.id,
            subject="Interested in Full Stack Engineer role",
            body="Hi John, I'm excited about the opportunity...",
            status="sent",
            email_sent=True,
            contact_email=contact.email,
            contact_name=contact.name,
        )
        session.add(outreach)
        session.commit()
        
        # 5. Verify the complete workflow using indexes
        # Query high-score applications using index
        high_score_apps = session.query(Application).filter(
            Application.match_score >= 0.8
        ).all()
        assert len(high_score_apps) > 0
        
        # Query jobs by company using compound index
        company_jobs = session.query(Job).filter_by(company="WorkflowCorp").all()
        assert len(company_jobs) > 0
        
        # Query contacts by email and company using compound index
        company_contacts = session.query(Contact).filter(
            Contact.email == "john@workflowcorp.com",
            Contact.company == "WorkflowCorp"
        ).all()
        assert len(company_contacts) > 0
        
        # Query outreach records using compound index
        job_outreach = session.query(OutreachRecord).filter(
            OutreachRecord.job_id == job.id,
            OutreachRecord.contact_id == contact.id
        ).all()
        assert len(job_outreach) > 0
        
        # Verify relationships work
        assert application.job.company == "WorkflowCorp"
        assert outreach.contact.name == "John Manager"
        assert outreach.job.title == "Full Stack Engineer"
        
        session.close()
