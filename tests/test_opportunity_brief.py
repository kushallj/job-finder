from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from main import app
from src.database import SessionLocal, init_db
from src.models import Job, Application, Contact, OutreachRecord

@pytest.fixture
def seeded_job():
    init_db()
    db = SessionLocal()
    import uuid
    test_job_id = f'brief-test-{uuid.uuid4().hex}'
    job = Job(job_id=test_job_id, title='Senior Backend Engineer', company='Acme Labs', location='Remote', description='Python FastAPI PostgreSQL AWS distributed systems', url='https://example.com/job', source='test', posted_date=datetime.utcnow()-timedelta(days=2))
    db.add(job); db.commit(); db.refresh(job)
    db.add(Contact(name='Jane Manager', title='Engineering Manager', email='jane@acme.test', company='Acme Labs', confidence_score=92, source='website'))
    db.add(Application(job_id=job.id, match_score=88, skills_matched='["Python", "FastAPI"]', skills_missing='["Kafka"]', status='applied'))
    db.commit(); job_id = job.id; db.close()
    yield job_id
    db = SessionLocal()
    db.query(OutreachRecord).filter(OutreachRecord.job_id == job_id).delete(synchronize_session=False)
    db.query(Application).filter(Application.job_id == job_id).delete(synchronize_session=False)
    db.query(Job).filter(Job.id == job_id).delete(synchronize_session=False)
    db.commit(); db.close()

def test_opportunity_brief_contract(seeded_job):
    client = TestClient(app)
    r = client.get(f'/api/opportunities/{seeded_job}/brief')
    assert r.status_code == 200
    data = r.json()
    assert data['fit_score'] == 88
    assert data['fit_label'] == 'Excellent fit'
    assert data['people'][0]['name'] == 'Jane Manager'
    assert data['next_action']['key'] == 'outreach'
    assert 'Kafka' in data['resume']['missing_keywords']
