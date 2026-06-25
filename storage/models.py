"""
SQLAlchemy Models
----------------
Database models for storing job postings.

Schema:
- raw_jobs: Raw scraped data
- parsed_jobs: Cleaned/normalised data
- skills: Unique skills (normalized)
- job_skills: Many-to-many relationship

Demonstrates database schema design with SQLAlchemy.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Create base class for declarative models
Base = declarative_base()


class RawJob(Base):
    """
    Raw scraped job data.
    
    Stores the original scraped data before any transformations.
    Useful for debugging and reprocessing.
    """
    __tablename__ = "raw_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), unique=True, nullable=False)
    
    # Raw fields as scraped
    raw_title = Column(String(500))
    raw_company = Column(String(500))
    raw_location = Column(String(500))
    raw_description = Column(Text)
    raw_salary = Column(String(200))
    raw_skills = Column(Text)  # JSON string of raw skills
    raw_html = Column(Text)
    
    # Metadata
    source = Column(String(50))
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # Hash for deduplication
    url_hash = Column(String(64), index=True)
    
    # Relationships
    parsed_job = relationship("ParsedJob", back_populates="raw_job", uselist=False)
    
    def __repr__(self):
        return f"<RawJob(id={self.id}, title={self.raw_title}, company={self.raw_company})>"


class ParsedJob(Base):
    """
    Cleaned and normalised job data.
    
    The main table for querying jobs.
    """
    __tablename__ = "parsed_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_job_id = Column(Integer, ForeignKey("raw_jobs.id"), unique=True)
    
    # Cleaned fields
    title = Column(String(500), nullable=False, index=True)
    company = Column(String(500), nullable=False, index=True)
    location = Column(String(200), index=True)
    description = Column(Text)
    
    # Salary in paise/cents (store as integer for precision)
    salary_min = Column(Integer)  # Annual, in local currency
    salary_max = Column(Integer)
    salary_currency = Column(String(3), default="INR")
    
    # Job details
    job_type = Column(String(50))  # Full-time, Contract, etc.
    remote = Column(Boolean)
    posted_date = Column(DateTime)
    posted_date_raw = Column(String(50))
    
    # Work mode
    is_remote = Column(Boolean, default=False)
    is_hybrid = Column(Boolean, default=False)
    is_onsite = Column(Boolean, default=False)
    
    # URL for original posting
    application_url = Column(String(500))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_company", "company"),
        Index("idx_location", "location"),
        Index("idx_salary_range", "salary_min", "salary_max"),
        Index("idx_remote", "is_remote"),
        Index("idx_job_type", "job_type"),
        Index("idx_title_company", "title", "company"),
    )
    
    # Relationships
    raw_job = relationship("RawJob", back_populates="parsed_job")
    skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ParsedJob(id={self.id}, title={self.title}, company={self.company})>"
    
    @property
    def salary_range(self) -> str:
        """Get salary range as string."""
        if self.salary_min and self.salary_max:
            return f"{self.salary_min}-{self.salary_max} {self.salary_currency}"
        elif self.salary_min:
            return f"{self.salary_min} {self.salary_currency}"
        return None


class Skill(Base):
    """
    Normalized skill/tags table.
    
    Ensures consistent skill names across all jobs.
    """
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50))  # language, framework, tool, etc.
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    jobs = relationship("JobSkill", back_populates="skill")
    
    def __repr__(self):
        return f"<Skill(id={self.id}, name={self.name}, category={self.category})>"


class JobSkill(Base):
    """
    Many-to-many relationship between jobs and skills.
    
    Allows for efficient querying of jobs by skill.
    """
    __tablename__ = "job_skills"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("parsed_jobs.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    
    # Confidence score for skill extraction
    confidence = Column(Float, default=1.0)
    
    # Method used to extract this skill
    extraction_method = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint - one skill per job
    __table_args__ = (
        UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),
        Index("idx_job_id", "job_id"),
        Index("idx_skill_id", "skill_id"),
    )
    
    # Relationships
    job = relationship("ParsedJob", back_populates="skills")
    skill = relationship("Skill", back_populates="jobs")
    
    def __repr__(self):
        return f"<JobSkill(job_id={self.job_id}, skill_id={self.skill_id})>"


class ScrapeStats(Base):
    """
    Statistics about scraping runs.
    
    Useful for monitoring and observability.
    """
    __tablename__ = "scrape_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    
    # Stats
    pages_scraped = Column(Integer, default=0)
    jobs_found = Column(Integer, default=0)
    jobs_failed = Column(Integer, default=0)
    duplicates = Column(Integer, default=0)
    new_jobs = Column(Integer, default=0)
    updated_jobs = Column(Integer, default=0)
    
    # Duration
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # Errors
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<ScrapeStats(source={self.source}, jobs_found={self.jobs_found})>"


# Export for easy importing
__all__ = ["Base", "RawJob", "ParsedJob", "Skill", "JobSkill", "ScrapeStats"]
