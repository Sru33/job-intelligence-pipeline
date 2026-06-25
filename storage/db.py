"""
Database Connection & Operations
"""

import hashlib
import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base, RawJob, ParsedJob, Skill, JobSkill, ScrapeStats

log = logging.getLogger(__name__)


class Database:
    def __init__(self, database_url: str = "sqlite:///jobs.db"):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._init_engine()
    
    def _init_engine(self):
        if self.database_url.startswith("sqlite"):
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,
            )
        else:
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False,
            )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        
        log.info(f"Database engine initialized: {self.database_url}")
    
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        log.info("Database tables created")
    
    def drop_tables(self):
        Base.metadata.drop_all(bind=self.engine)
        log.info("Database tables dropped")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        return self.SessionLocal()
    
    def save_raw_job(self, job_data: dict, source: str = "wellfound") -> int:
        url_hash = self._hash_url(job_data.get("url", ""))
        
        with self.get_session() as session:
            existing = session.query(RawJob).filter(
                RawJob.url_hash == url_hash
            ).first()
            
            if existing:
                log.debug(f"Duplicate raw job: {job_data.get('title')}")
                return existing.id
            
            raw_job = RawJob(
                url=job_data.get("url", ""),
                raw_title=job_data.get("title"),
                raw_company=job_data.get("company"),
                raw_location=job_data.get("location"),
                raw_description=job_data.get("description"),
                raw_salary=job_data.get("salary"),
                raw_skills=json.dumps(job_data.get("skills", [])),
                raw_html=job_data.get("raw_html"),
                source=source,
                url_hash=url_hash,
            )
            
            session.add(raw_job)
            session.flush()
            raw_job_id = raw_job.id
            
            log.debug(f"Saved raw job: {job_data.get('title')}")
            return raw_job_id
    
    def get_raw_job_by_id(self, raw_job_id: int) -> Optional[RawJob]:
        with self.get_session() as session:
            return session.query(RawJob).filter(RawJob.id == raw_job_id).first()
    
    def save_parsed_job(
        self,
        raw_job_id: int,
        parsed_data: dict,
    ) -> ParsedJob:
        with self.get_session() as session:
            existing = session.query(ParsedJob).filter(
                ParsedJob.raw_job_id == raw_job_id
            ).first()
            
            if existing:
                self._update_parsed_job(existing, parsed_data)
                log.debug(f"Updated parsed job: {parsed_data.get('title')}")
                session.flush()
                return existing
            
            parsed_job = ParsedJob(
                raw_job_id=raw_job_id,
                title=parsed_data.get("title"),
                company=parsed_data.get("company"),
                location=parsed_data.get("location"),
                description=parsed_data.get("description"),
                salary_min=parsed_data.get("salary_min"),
                salary_max=parsed_data.get("salary_max"),
                salary_currency=parsed_data.get("salary_currency", "INR"),
                job_type=parsed_data.get("job_type"),
                remote=parsed_data.get("remote"),
                posted_date_raw=parsed_data.get("posted_date"),
                application_url=parsed_data.get("application_url", ""),
                is_remote=parsed_data.get("is_remote", False),
                is_hybrid=parsed_data.get("is_hybrid", False),
                is_onsite=parsed_data.get("is_onsite", False),
            )
            
            session.add(parsed_job)
            session.flush()
            
            skills = parsed_data.get("skills", [])
            self._add_job_skills(session, parsed_job.id, skills)
            
            log.debug(f"Saved parsed job: {parsed_data.get('title')}")
            return parsed_job
    
    def _update_parsed_job(self, job: ParsedJob, data: dict):
        job.title = data.get("title", job.title)
        job.company = data.get("company", job.company)
        job.location = data.get("location", job.location)
        job.description = data.get("description", job.description)
        job.salary_min = data.get("salary_min", job.salary_min)
        job.salary_max = data.get("salary_max", job.salary_max)
        job.job_type = data.get("job_type", job.job_type)
        job.remote = data.get("remote", job.remote)
        job.updated_at = datetime.utcnow()
    
    def _add_job_skills(self, session: Session, job_id: int, skills: list):
        for skill_name in skills:
            skill_name = skill_name.lower().strip()
            
            skill = session.query(Skill).filter(Skill.name == skill_name).first()
            if not skill:
                skill = Skill(name=skill_name)
                session.add(skill)
                session.flush()
            
            existing = session.query(JobSkill).filter(
                JobSkill.job_id == job_id,
                JobSkill.skill_id == skill.id,
            ).first()
            
            if not existing:
                job_skill = JobSkill(
                    job_id=job_id,
                    skill_id=skill.id,
                    confidence=1.0,
                    extraction_method="keyword",
                )
                session.add(job_skill)
    
    def search_jobs(
        self,
        skill: Optional[str] = None,
        location: Optional[str] = None,
        min_salary: Optional[int] = None,
        company: Optional[str] = None,
        remote: Optional[bool] = None,
        job_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Search jobs and return dicts with skills included."""
        with self.get_session() as session:
            query = session.query(ParsedJob)
            
            if skill:
                query = query.join(ParsedJob.skills).join(JobSkill.skill).filter(
                    Skill.name.ilike(f"%{skill}%")
                )
            
            if location:
                query = query.filter(
                    ParsedJob.location.ilike(f"%{location}%")
                )
            
            if min_salary is not None:
                query = query.filter(
                    ParsedJob.salary_max >= min_salary
                )
            
            if company:
                query = query.filter(
                    ParsedJob.company.ilike(f"%{company}%")
                )
            
            if remote is not None:
                query = query.filter(ParsedJob.is_remote == remote)
            
            if job_type:
                query = query.filter(ParsedJob.job_type == job_type)
            
            jobs = query.order_by(ParsedJob.created_at.desc()).offset(offset).limit(limit).all()
            
            results = []
            for job in jobs:
                skill_names = [s.name for s in session.query(Skill).join(
                    JobSkill, JobSkill.skill_id == Skill.id
                ).filter(JobSkill.job_id == job.id).all()]
                
                results.append({
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "description": job.description,
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                    "salary_currency": job.salary_currency,
                    "job_type": job.job_type,
                    "is_remote": job.is_remote,
                    "is_hybrid": job.is_hybrid,
                    "is_onsite": job.is_onsite,
                    "application_url": job.application_url,
                    "created_at": job.created_at,
                    "skills": skill_names,
                })
            
            return results
    
    def get_job_by_id(self, job_id: int) -> Optional[ParsedJob]:
        with self.get_session() as session:
            return session.query(ParsedJob).filter(ParsedJob.id == job_id).first()
    
    def get_jobs_count(
        self,
        skill: Optional[str] = None,
        location: Optional[str] = None,
    ) -> int:
        with self.get_session() as session:
            query = session.query(ParsedJob)
            
            if skill:
                query = query.join(ParsedJob.skills).join(JobSkill.skill).filter(
                    Skill.name.ilike(f"%{skill}%")
                )
            
            if location:
                query = query.filter(
                    ParsedJob.location.ilike(f"%{location}%")
                )
            
            return query.count()
    
    def get_all_skills(self) -> list[Skill]:
        with self.get_session() as session:
            return session.query(Skill).all()
    
    @staticmethod
    def _hash_url(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()
    
    def get_stats_summary(self) -> dict:
        with self.get_session() as session:
            total_jobs = session.query(ParsedJob).count()
            total_skills = session.query(Skill).count()
            remote_jobs = session.query(ParsedJob).filter(
                ParsedJob.is_remote == True
            ).count()
            latest_scrape = session.query(ScrapeStats).order_by(
                ScrapeStats.started_at.desc()
            ).first()
            
            return {
                "total_jobs": total_jobs,
                "total_skills": total_skills,
                "remote_jobs": remote_jobs,
                "latest_scrape": latest_scrape.started_at if latest_scrape else None,
                "jobs_found_latest": latest_scrape.jobs_found if latest_scrape else 0,
            }
    
    def close(self):
        if self.engine:
            self.engine.dispose()


DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "jobs.db"
)
_DEFAULT_URL = f"sqlite:///{DEFAULT_DB_PATH}"

_db: Optional[Database] = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database(_DEFAULT_URL)
        _db.create_tables()
    return _db


def init_db(database_url: str) -> Database:
    global _db
    _db = Database(database_url)
    _db.create_tables()
    return _db
