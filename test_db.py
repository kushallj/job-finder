from src.database import init_db, SessionLocal
from src.models import Job
from datetime import datetime

# Initialize database
init_db()

# Test insert
db = SessionLocal()
test_job = Job(
    job_id="test_001",
    title="Software Engineer",
    company="Test Company",
    location="Remote",
    description="Test description",
    url="https://example.com",
    source="test",
    posted_date=datetime.now()
)
db.add(test_job)
db.commit()

# Test query
jobs = db.query(Job).all()
print(f"✅ Found {len(jobs)} jobs in database")

db.close()