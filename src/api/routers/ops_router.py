"""
ops_router.py: admin-only operational status for background jobs.

GET /api/admin/catalog-runs  recent job-catalog refreshes plus a `stale` flag
                             (src/services/catalog_runs.py explains the fields).

Superusers only (require_admin). Catalog runs are system records, not tenant data,
so there is no per-user filtering here.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.auth.dependencies import require_admin
from src.database import get_db
from src.models import User
from src.services import catalog_runs

router = APIRouter(prefix="/api/admin", tags=["Admin ops"])


@router.get("/catalog-runs")
def get_catalog_runs(
    limit: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return catalog_runs.catalog_status(db, limit=limit)
