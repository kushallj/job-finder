"""
Presentation Router: JobsRouter
Clean, modular FastAPI endpoints for job querying and details.
Adheres to Single Responsibility Principle (SRP) and < 200 lines constraint.
"""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from src.application.dtos.job_dtos import JobQueryParamsDTO
from src.application.use_cases.query_jobs_use_case import QueryJobsUseCase
from src.infrastructure.repositories.sql_job_repository import SqlJobRepository

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def get_query_jobs_use_case() -> QueryJobsUseCase:
    """Dependency injection factory for QueryJobsUseCase."""
    repo = SqlJobRepository()
    return QueryJobsUseCase(job_repository=repo)


@router.get("")
async def get_all_jobs(
    page: int = Query(default=1, ge=1, le=10000),
    limit: int = Query(default=50, ge=1, le=500),
    search: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    experience_level: Optional[str] = Query(default=None),
    years_of_experience: Optional[int] = Query(default=None, ge=0, le=30),
    date_posted: Optional[str] = Query(default=None),
    tech_stack: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    has_remote: Optional[bool] = Query(default=None),
    sort_by: str = Query(default="fetched_at"),
    sort_order: str = Query(default="desc"),
    use_case: QueryJobsUseCase = Depends(get_query_jobs_use_case),
):
    """
    Get paginated jobs with multi-facet ORM filtering.

    Time Complexity: O(log N + limit)
    Space Complexity: O(limit)
    """
    try:
        dto = JobQueryParamsDTO(
            page=page,
            limit=limit,
            search=search,
            region=region,
            experience_level=experience_level,
            years_of_experience=years_of_experience,
            date_posted=date_posted,
            tech_stack=tech_stack,
            source=source,
            has_remote=has_remote,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        res = await use_case.execute(dto)
        return {
            "status": res.status,
            "jobs": [
                {
                    "id": j.id,
                    "job_id": j.job_id,
                    "title": j.title,
                    "company": j.company,
                    "location": j.location,
                    "description": j.description,
                    "url": j.url,
                    "source": j.source,
                    "posted_date": j.posted_date,
                    "fetched_at": j.fetched_at,
                    "match_score": j.match_score,
                    "application_status": j.application_status,
                    "salary_min": j.salary_min,
                    "salary_max": j.salary_max,
                    "salary_currency": j.salary_currency,
                    "has_remote": j.has_remote,
                    "work_mode": j.work_mode,
                    "experience_level": j.experience_level,
                    "tags": j.tags,
                    "ghost_probability": j.ghost_probability,
                    "ghost_risk_level": j.ghost_risk_level,
                    "ghost_verified_active": j.ghost_verified_active,
                }
                for j in res.jobs
            ],
            "pagination": {
                "page": res.page,
                "limit": res.limit,
                "total": res.total,
                "pages": res.pages,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{job_id}")
async def get_job_by_id(job_id: int):
    """Retrieve single job by primary key."""
    repo = SqlJobRepository()
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "status": "success",
        "job": {
            "id": job.id,
            "job_id": job.job_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
            "url": job.url,
            "source": job.source,
            "posted_date": job.posted_date.isoformat() if job.posted_date else None,
            "fetched_at": job.fetched_at.isoformat() if job.fetched_at else "",
            "salary_min": job.compensation.min_salary if job.compensation else None,
            "salary_max": job.compensation.max_salary if job.compensation else None,
            "salary_currency": job.compensation.currency if job.compensation else None,
            "has_remote": job.has_remote,
            "work_mode": job.work_mode,
            "experience_level": job.experience_level.tier.value if job.experience_level else None,
            "tags": job.tech_stack.to_list() if job.tech_stack else [],
        },
    }
