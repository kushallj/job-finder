"""
Unit tests verifying Clean Architecture domain entities, value objects,
services, and use cases.
"""
import pytest
from src.domain.value_objects.compensation import Compensation
from src.domain.value_objects.tech_stack import TechStack
from src.domain.value_objects.experience_level import ExperienceLevel, SeniorityTier
from src.domain.value_objects.email_address import EmailAddress
from src.domain.entities.job import Job
from src.domain.entities.contact import Contact
from src.domain.entities.application import Application, ApplicationStatus
from src.domain.entities.outreach_record import OutreachRecord, OutreachStatus
from src.application.services.job_deduplicator import JobDeduplicator
from src.application.services.taxonomy_classifier import TaxonomyClassifier
from src.application.dtos.job_dtos import JobQueryParamsDTO
from src.application.use_cases.query_jobs_use_case import QueryJobsUseCase
from src.infrastructure.repositories.sql_job_repository import SqlJobRepository


def test_compensation_value_object():
    comp = Compensation(min_salary=5000000, max_salary=7000000, currency="INR")
    assert comp.has_range is True
    assert comp.midpoint == 6000000.0
    assert "5,000,000" in comp.format_display()

    with pytest.raises(ValueError):
        Compensation(min_salary=8000000, max_salary=5000000)


def test_tech_stack_value_object():
    stack1 = TechStack.from_iterable(["Python", "FastAPI", "AWS"])
    stack2 = TechStack.from_iterable(["python", "aws", "docker"])
    assert stack1.contains("python") is True
    assert stack1.contains("Rust") is False
    score = stack1.overlap_score(stack2)
    assert score > 0.5


def test_experience_level_value_object():
    entry = ExperienceLevel.from_years(1)
    assert entry.tier == SeniorityTier.ENTRY

    sr = ExperienceLevel.from_text("Senior Backend Engineer")
    assert sr.tier == SeniorityTier.SENIOR

    staff = ExperienceLevel.from_text("Principal Architect")
    assert staff.tier == SeniorityTier.STAFF


def test_email_address_value_object():
    email = EmailAddress("careers@stripe.com")
    assert email.domain == "stripe.com"
    assert email.local_part == "careers"

    with pytest.raises(ValueError):
        EmailAddress("invalid-email-address")


def test_job_entity_fingerprint_and_freshness():
    job = Job(title="Senior SWE", company="Databricks", location="Bengaluru")
    assert len(job.job_id) == 16
    assert job.is_fresh() is True


def test_job_deduplicator():
    j1 = Job(title="Backend Dev", company="Groww", location="Bangalore")
    j2 = Job(title="Backend Dev", company="Groww", location="Bangalore")
    j3 = Job(title="Frontend Dev", company="Groww", location="Bangalore")

    unique, dupes = JobDeduplicator.deduplicate_batch([j1, j2, j3])
    assert len(unique) == 2
    assert len(dupes) == 1


def test_taxonomy_classifier():
    stack, exp, is_remote, mode = TaxonomyClassifier.classify(
        title="Senior Python & FastAPI Cloud Engineer",
        description="Build distributed Kafka data pipelines with AWS and Kubernetes. Fully remote role.",
    )
    assert stack.contains("Python") is True
    assert stack.contains("AWS / Cloud") is True
    assert exp.tier == SeniorityTier.SENIOR
    assert is_remote is True
    assert mode == "remote"


@pytest.mark.asyncio
async def test_query_jobs_use_case():
    repo = SqlJobRepository()
    use_case = QueryJobsUseCase(job_repository=repo)
    params = JobQueryParamsDTO(page=1, limit=5)
    result = await use_case.execute(params)

    assert result.status == "success"
    assert len(result.jobs) <= 5
    assert result.total >= 0
