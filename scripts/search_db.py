from src.database import SessionLocal
from src.models import Job, Application

def main():
    db = SessionLocal()

    # Example 1: all jobs
    jobs = db.query(Job).all()
    print(f"Total jobs: {len(jobs)}")

    # Example 2: search jobs by title keyword
    keyword = "python"
    jobs = db.query(Job).filter(Job.title.ilike(f"%{keyword}%")).all()
    print(f"\nJobs with '{keyword}' in title:")
    for j in jobs[:10]:  # show first 10
        print(f"- {j.title} @ {j.company} ({j.location})")

    # Example 3: high‑match applications
    apps = db.query(Application).filter(Application.match_score >= 70).all()
    print(f"\nApplications with score >= 70: {len(apps)}")

    db.close()

if __name__ == "__main__":
    main()