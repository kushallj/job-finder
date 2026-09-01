"""
Application Use Case: QueryJobsUseCase
Coordinates multi-facet search, pagination, and presentation mapping for jobs.
Adheres to Single Responsibility Principle (SRP).
"""
import math
from typing import Optional
from src.domain.interfaces.repositories.i_job_repository import IJobRepository
from src.application.dtos.job_dtos import (
    JobQueryParamsDTO,
    JobResponseDTO,
    PaginatedJobsResultDTO,
)


class QueryJobsUseCase:
    """
    Executes filtered job search with pagination and DTO mapping.

    Time Complexity:
        execute(): O(log N + limit)
    Space Complexity:
        O(limit)
    """

    def __init__(self, job_repository: IJobRepository):
        self.job_repository = job_repository

    async def execute(self, params: JobQueryParamsDTO) -> PaginatedJobsResultDTO:
        """Execute query across repository with parameters."""
        jobs_slice, total_count = await self.job_repository.query_filtered(
            page=params.page,
            limit=params.limit,
            search=params.search,
            region=params.region,
            experience_level=params.experience_level,
            years_of_experience=params.years_of_experience,
            date_posted=params.date_posted,
            tech_stack=params.tech_stack,
            source=params.source,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )

        total_pages = math.ceil(total_count / params.limit) if params.limit > 0 else 0

        dtos = [
            JobResponseDTO(
                id=j.id or 0,
                job_id=j.job_id or "",
                title=j.title,
                company=j.company,
                location=j.location,
                description=j.description,
                url=j.url,
                source=j.source,
                posted_date=j.posted_date.isoformat() if j.posted_date else None,
                fetched_at=j.fetched_at.isoformat() if j.fetched_at else "",
                salary_min=j.compensation.min_salary if j.compensation else None,
                salary_max=j.compensation.max_salary if j.compensation else None,
                salary_currency=j.compensation.currency if j.compensation else None,
                has_remote=j.has_remote,
                work_mode=j.work_mode,
                experience_level=j.experience_level.tier.value if j.experience_level else None,
                tags=j.tech_stack.to_list() if j.tech_stack else [],
                ghost_probability=j.ghost_probability,
                ghost_risk_level=j.ghost_risk_level,
                ghost_verified_active=j.ghost_verified_active,
            )
            for j in jobs_slice
        ]

        return PaginatedJobsResultDTO(
            status="success",
            jobs=dtos,
            page=params.page,
            limit=params.limit,
            total=total_count,
            pages=total_pages,
        )
