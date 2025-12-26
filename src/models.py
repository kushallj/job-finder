from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(255), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    company = Column(String(500))
    location = Column(String(500))
    description = Column(Text)
    url = Column(Text)
    source = Column(String(100))
    posted_date = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    applications = relationship("Application", back_populates="job")

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    
    # Matching
    match_score = Column(Float)
    skills_matched = Column(Text)  # JSON string
    skills_missing = Column(Text)  # JSON string
    
    # Generated content
    resume_version = Column(Text)
    cover_letter = Column(Text)
    
    # Status
    status = Column(String(50), default="pending")  # pending, applied, rejected, interview
    applied_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="applications")

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True)
    original_content = Column(Text, nullable=False)
    skills = Column(Text)  # JSON string
    experience_years = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)