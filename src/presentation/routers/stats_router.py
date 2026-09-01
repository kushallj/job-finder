"""
Presentation Router: StatsRouter
Clean, fast aggregated metrics and recent activity feed.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from src.database import SessionLocal
from src.models import Job as OrmJob, Contact as OrmContact, Application as OrmApp, OutreachRecord as OrmOutreach

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def get_system_stats():
    """
    Return comprehensive database metrics and recent outreach activity.

    Time Complexity: O(1) count aggregates with indexes.
    Space Complexity: O(1)
    """
    try:
        with SessionLocal() as db:
            tj = db.query(OrmJob).count()
            tc = db.query(OrmContact).count()
            ta = db.query(OrmApp).count()
            to = db.query(OrmOutreach).count()
            se = db.query(OrmOutreach).filter(OrmOutreach.email_sent == True).count()
            
            try:
                fu = db.query(OrmOutreach).filter(OrmOutreach.follow_up_count > 0).count()
            except Exception:
                fu = 0

            recent = [
                {
                    "id": r.id,
                    "contact_email": r.contact_email,
                    "status": r.status,
                    "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                }
                for r in db.query(OrmOutreach).order_by(OrmOutreach.sent_at.desc()).limit(5).all()
            ]

            success_rate = round(se / to * 100, 1) if to > 0 else 0.0

            return {
                "status": "success",
                "source": "db_live",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stats": {
                    "total_jobs": tj,
                    "total_contacts": tc,
                    "total_applications": ta,
                    "total_outreach_attempts": to,
                    "emails_sent": se,
                    "follow_ups_sent": fu,
                    "success_rate": success_rate,
                },
                "recent_outreach": recent,
                "error": None,
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
