"""
Infrastructure Mapper: JobMapper
Translates between pure domain Job entity and SQLAlchemy ORM Job model.
Adheres to Clean Architecture data transformation boundaries.
"""
import json
from typing import Optional
from src.domain.entities.job import Job as DomainJob
from src.domain.value_objects.compensation import Compensation
from src.domain.value_objects.tech_stack import TechStack
from src.domain.value_objects.experience_level import ExperienceLevel
from src.models import Job as OrmJob


class JobMapper:
    """
    Bi-directional mapper for Job domain entity <-> SQLAlchemy model.

    Time Complexity:
        to_domain() & to_orm(): O(1)
    Space Complexity:
        O(1)
    """

    @staticmethod
    def to_domain(orm: OrmJob) -> DomainJob:
        """Convert SQLAlchemy ORM row to Domain Entity."""
        # Parse tags
        tags = []
        if orm.tags:
            try:
                tags = json.loads(orm.tags) if isinstance(orm.tags, str) else list(orm.tags)
            except Exception:
                tags = [t.strip() for t in str(orm.tags).split(",") if t.strip()]

        comp = None
        if orm.salary_min or orm.salary_max:
            comp = Compensation(
                min_salary=orm.salary_min,
                max_salary=orm.salary_max,
                currency=orm.salary_currency or "INR",
            )

        exp = ExperienceLevel.from_text(orm.experience_level or orm.title)

        return DomainJob(
            id=orm.id,
            job_id=orm.job_id,
            title=orm.title,
            company=orm.company,
            location=orm.location or "Remote",
            description=orm.description or "",
            url=orm.url or "",
            source=orm.source or "unknown",
            posted_date=orm.posted_date,
            fetched_at=orm.fetched_at,
            compensation=comp,
            tech_stack=TechStack.from_iterable(tags),
            experience_level=exp,
            has_remote=bool(orm.has_remote),
            work_mode=orm.work_mode or "onsite",
            ghost_probability=getattr(orm, "ghost_probability", 0.0) or 0.0,
            ghost_risk_level=getattr(orm, "ghost_risk_level", "low") or "low",
            ghost_verified_active=getattr(orm, "ghost_verified_active", True),
        )

    @staticmethod
    def to_orm(domain: DomainJob) -> OrmJob:
        """Convert Domain Entity to SQLAlchemy ORM model."""
        tags_json = json.dumps(domain.tech_stack.to_list()) if domain.tech_stack else None

        return OrmJob(
            id=domain.id,
            job_id=domain.job_id,
            title=domain.title,
            company=domain.company,
            location=domain.location,
            description=domain.description,
            url=domain.url,
            source=domain.source,
            posted_date=domain.posted_date,
            fetched_at=domain.fetched_at,
            salary_min=domain.compensation.min_salary if domain.compensation else None,
            salary_max=domain.compensation.max_salary if domain.compensation else None,
            salary_currency=domain.compensation.currency if domain.compensation else None,
            has_remote=domain.has_remote,
            work_mode=domain.work_mode,
            experience_level=domain.experience_level.tier.value if domain.experience_level else None,
            tags=tags_json,
        )
