"""
Unit tests for S&P 500 Tech Job Scraper Engine.
"""
import pytest
from src.scrapers.sp500_job_scraper import (
    is_tech_job,
    extract_tech_stack,
    SP500_ATS_MAPPING,
    SP500JobScraper,
)


def test_is_tech_job_filter():
    assert is_tech_job("Senior Software Engineer, Backend") is True
    assert is_tech_job("Staff Machine Learning Engineer") is True
    assert is_tech_job("Full Stack Developer (React / Python)") is True
    assert is_tech_job("DevOps / Cloud Infrastructure Lead") is True
    assert is_tech_job("Branch Retail Store Associate") is False
    assert is_tech_job("Janitorial Services Specialist") is False


def test_extract_tech_stack_tokens():
    text = "Looking for a Python and FastAPI backend developer with React, PostgreSQL, Redis, and AWS experience."
    stack = extract_tech_stack(text)
    assert "Python" in stack
    assert "FastAPI" in stack
    assert "React" in stack
    assert "PostgreSQL" in stack
    assert "Redis" in stack
    assert "AWS" in stack


def test_sp500_ats_mapping():
    assert "UBER" in SP500_ATS_MAPPING
    assert SP500_ATS_MAPPING["UBER"]["platform"] == "greenhouse"
    assert "NFLX" in SP500_ATS_MAPPING
    assert SP500_ATS_MAPPING["NFLX"]["platform"] == "lever"
    assert "V" in SP500_ATS_MAPPING
    assert SP500_ATS_MAPPING["V"]["platform"] == "smartrecruiters"
