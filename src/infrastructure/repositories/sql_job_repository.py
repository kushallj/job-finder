"""
Infrastructure Repository: SqlJobRepository
Concrete implementation of IJobRepository using SQLAlchemy ORM queries and connection pooling.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy import or_, func
from src.database import SessionLocal
from src.models import Job as OrmJob
from src.domain.entities.job import Job as DomainJob
from src.domain.interfaces.repositories.i_job_repository import IJobRepository
from src.infrastructure.database.mappers.job_mapper import JobMapper


class SqlJobRepository(IJobRepository):
    """
    SQLAlchemy-backed repository executing optimized ORM filter queries.

    Time Complexity:
        get_by_id(): O(log N) primary key B-Tree lookup.
        query_filtered(): O(log N + limit) with index scan.
    Space Complexity:
        O(limit) for fetched batch.
    """

    async def get_by_id(self, job_id: int) -> Optional[DomainJob]:
        with SessionLocal() as db:
            orm = db.query(OrmJob).filter(OrmJob.id == job_id).first()
            return JobMapper.to_domain(orm) if orm else None

    async def get_by_fingerprint(self, fingerprint: str) -> Optional[DomainJob]:
        with SessionLocal() as db:
            orm = db.query(OrmJob).filter(OrmJob.job_id == fingerprint).first()
            return JobMapper.to_domain(orm) if orm else None

    async def save(self, job: DomainJob) -> DomainJob:
        with SessionLocal() as db:
            orm = db.query(OrmJob).filter(OrmJob.job_id == job.job_id).first()
            if orm:
                orm.title = job.title
                orm.company = job.company
                orm.location = job.location
                orm.fetched_at = job.fetched_at
            else:
                orm = JobMapper.to_orm(job)
                db.add(orm)
            db.commit()
            db.refresh(orm)
            return JobMapper.to_domain(orm)

    async def save_batch(self, jobs: List[DomainJob]) -> Tuple[int, int]:
        if not jobs:
            return 0, 0
        inserted, updated = 0, 0
        with SessionLocal() as db:
            fps = [j.job_id for j in jobs if j.job_id]
            existing = {r.job_id: r for r in db.query(OrmJob).filter(OrmJob.job_id.in_(fps)).all()}
            for j in jobs:
                if j.job_id in existing:
                    row = existing[j.job_id]
                    row.fetched_at = j.fetched_at
                    row.title = j.title
                    updated += 1
                else:
                    db.add(JobMapper.to_orm(j))
                    inserted += 1
            db.commit()
        return inserted, updated

    async def query_filtered(
        self,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        region: Optional[str] = None,
        experience_level: Optional[str] = None,
        years_of_experience: Optional[int] = None,
        date_posted: Optional[str] = None,
        tech_stack: Optional[str] = None,
        source: Optional[str] = None,
        sort_by: str = "fetched_at",
        sort_order: str = "desc",
    ) -> Tuple[List[DomainJob], int]:
        with SessionLocal() as db:
            q = db.query(OrmJob)

            if search and search.strip():
                t = f"%{search.strip().lower()}%"
                q = q.filter(or_(func.lower(OrmJob.title).like(t), func.lower(OrmJob.company).like(t), func.lower(OrmJob.location).like(t), func.lower(OrmJob.tags).like(t)))

            if region and region.strip().lower() != "all":
                reg = region.strip().lower()
                if reg == "remote":
                    q = q.filter(or_(OrmJob.has_remote == True, OrmJob.work_mode == "remote", func.lower(OrmJob.location).like("%remote%")))
                elif reg in ("india", "in", "bengaluru", "mumbai", "pune", "delhi"):
                    q = q.filter(or_(func.lower(OrmJob.location).like("%india%"), func.lower(OrmJob.location).like("%bengaluru%"), func.lower(OrmJob.location).like("%mumbai%"), func.lower(OrmJob.location).like("%pune%")))
                else:
                    q = q.filter(func.lower(OrmJob.location).like(f"%{reg}%"))

            if years_of_experience is not None:
                if years_of_experience <= 2:
                    q = q.filter(or_(OrmJob.experience_level.like("%Junior%"), OrmJob.experience_level.like("%Entry%")))
                elif years_of_experience <= 5:
                    q = q.filter(OrmJob.experience_level.like("%Mid%"))
                elif years_of_experience <= 8:
                    q = q.filter(OrmJob.experience_level.like("%Senior%"))
                else:
                    q = q.filter(or_(OrmJob.experience_level.like("%Lead%"), OrmJob.experience_level.like("%Staff%"), OrmJob.experience_level.like("%Principal%")))
            elif experience_level and experience_level.strip().lower() != "all":
                q = q.filter(func.lower(OrmJob.experience_level).like(f"%{experience_level.strip().lower()}%"))

            if date_posted and date_posted.strip().lower() not in ("all", "anytime"):
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                cutoff = now - timedelta(days=1 if "24h" in date_posted else (7 if "7d" in date_posted else 30))
                q = q.filter(or_(OrmJob.posted_date >= cutoff, OrmJob.fetched_at >= cutoff))

            if tech_stack and tech_stack.strip().lower() != "all":
                for s in tech_stack.split(","):
                    if s.strip():
                        q = q.filter(func.lower(OrmJob.tags).like(f"%{s.strip().lower()}%"))

            if source and source.strip().lower() != "all":
                q = q.filter(func.lower(OrmJob.source).like(f"%{source.strip().lower()}%"))

            sort_col = OrmJob.posted_date if sort_by == "posted_date" else OrmJob.fetched_at
            q = q.order_by(sort_col.asc() if sort_order == "asc" else sort_col.desc())

            total = q.count()
            rows = q.offset((page - 1) * limit).limit(limit).all()
            return [JobMapper.to_domain(r) for r in rows], total

    async def count_total(self) -> int:
        with SessionLocal() as db:
            return db.query(OrmJob).count()
