"""
Job Intelligence API
--------------------
FastAPI application for exposing job postings via REST API.
"""

import logging
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from storage.db import get_db
from storage.models import ParsedJob, Skill, JobSkill

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(
    title="Job Intelligence API",
    description="API for searching job postings scraped from Wellfound and similar sources",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: Optional[str]
    description: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_currency: str
    job_type: Optional[str]
    is_remote: bool
    is_hybrid: bool
    is_onsite: bool
    application_url: Optional[str]
    skills: list[str]
    created_at: str
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    total: int
    jobs: list[JobResponse]
    page: int = 1
    page_size: int = 100


class SkillResponse(BaseModel):
    id: int
    name: str
    category: Optional[str]
    job_count: int = 0
    
    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_jobs: int
    total_skills: int
    remote_jobs: int
    latest_scrape: Optional[str]
    jobs_found_latest: int


def dict_to_job_response(job_dict: dict) -> JobResponse:
    """Convert dict from search_jobs to JobResponse."""
    return JobResponse(
        id=job_dict["id"],
        title=job_dict["title"],
        company=job_dict["company"],
        location=job_dict["location"],
        description=job_dict["description"],
        salary_min=job_dict["salary_min"],
        salary_max=job_dict["salary_max"],
        salary_currency=job_dict["salary_currency"],
        job_type=job_dict["job_type"],
        is_remote=job_dict["is_remote"],
        is_hybrid=job_dict["is_hybrid"],
        is_onsite=job_dict["is_onsite"],
        application_url=job_dict["application_url"],
        skills=job_dict["skills"],
        created_at=job_dict["created_at"].isoformat() if job_dict["created_at"] else "",
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Job Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/jobs", response_model=JobListResponse, tags=["Jobs"])
async def search_jobs(
    skill: Optional[str] = Query(None, description="Filter by skill name"),
    location: Optional[str] = Query(None, description="Filter by location"),
    min_salary: Optional[int] = Query(None, description="Minimum annual salary"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    remote: Optional[bool] = Query(None, description="Filter remote jobs only"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=500, description="Page size"),
):
    db = get_db()
    offset = (page - 1) * page_size
    
    jobs = db.search_jobs(
        skill=skill,
        location=location,
        min_salary=min_salary,
        company=company,
        remote=remote,
        job_type=job_type,
        limit=page_size,
        offset=offset,
    )
    
    total = db.get_jobs_count(skill=skill, location=location)
    
    job_responses = [dict_to_job_response(job) for job in jobs]
    
    return JobListResponse(
        total=total,
        jobs=job_responses,
        page=page,
        page_size=page_size,
    )


@app.get("/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def get_job(job_id: int):
    db = get_db()
    job = db.get_job_by_id(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build response dict manually for single job
    from storage.db import get_db as db_func
    db = db_func()
    session = db.get_session_direct()
    from storage.models import Skill, JobSkill
    skills = session.query(Skill).join(JobSkill).filter(
        JobSkill.job_id == job.id
    ).all()
    skill_names = [s.name for s in skills]
    session.close()
    
    return JobResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        description=job.description,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        job_type=job.job_type,
        is_remote=job.is_remote,
        is_hybrid=job.is_hybrid,
        is_onsite=job.is_onsite,
        application_url=job.application_url,
        skills=skill_names,
        created_at=job.created_at.isoformat() if job.created_at else "",
    )


@app.get("/skills", response_model=list[SkillResponse], tags=["Skills"])
async def list_skills(
    limit: int = Query(100, ge=1, le=500),
):
    db = get_db()
    skills = db.get_all_skills()
    
    from sqlalchemy import func
    
    response = []
    session = db.get_session_direct()
    for skill in skills[:limit]:
        count = session.query(func.count(JobSkill.id)).filter(
            JobSkill.skill_id == skill.id
        ).scalar()
        
        response.append(SkillResponse(
            id=skill.id,
            name=skill.name,
            category=skill.category,
            job_count=count or 0,
        ))
    session.close()
    
    return response


@app.get("/stats", response_model=StatsResponse, tags=["Stats"])
async def get_stats():
    db = get_db()
    stats = db.get_stats_summary()
    
    return StatsResponse(
        total_jobs=stats["total_jobs"],
        total_skills=stats["total_skills"],
        remote_jobs=stats["remote_jobs"],
        latest_scrape=stats["latest_scrape"].isoformat() if stats["latest_scrape"] else None,
        jobs_found_latest=stats["jobs_found_latest"],
    )


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


@app.post("/demo/seed", tags=["Demo"])
async def seed_demo_data():
    db = get_db()
    
    sample_jobs = [
        {
            "url": "https://wellfound.com/jobs/1",
            "title": "Senior Python Developer",
            "company": "TechCorp India",
            "location": "Bangalore, Karnataka",
            "description": "We are looking for a Senior Python Developer to join our team.",
            "salary": "₹15L - ₹25L",
            "skills": ["Python", "Django", "PostgreSQL", "AWS", "Docker"],
        },
        {
            "url": "https://wellfound.com/jobs/2",
            "title": "Frontend Engineer - React",
            "company": "StartupXYZ",
            "location": "Remote",
            "description": "Join our team as a Frontend Engineer working with React.",
            "salary": "₹12L - ₹18L",
            "skills": ["React", "TypeScript", "GraphQL", "JavaScript"],
        },
        {
            "url": "https://wellfound.com/jobs/3",
            "title": "Full Stack Developer",
            "company": "InnovateTech",
            "location": "Mumbai, Maharashtra",
            "description": "Full Stack Developer needed with Node.js, React, MongoDB.",
            "salary": "₹10L - ₹16L",
            "skills": ["Node.js", "React", "MongoDB", "TypeScript"],
        },
        {
            "url": "https://wellfound.com/jobs/4",
            "title": "Machine Learning Engineer",
            "company": "AIFirst",
            "location": "Remote",
            "description": "Machine Learning Engineer for our AI platform.",
            "salary": "₹20L - ₹35L",
            "skills": ["Python", "Machine Learning", "PyTorch", "TensorFlow", "AWS"],
        },
        {
            "url": "https://wellfound.com/jobs/5",
            "title": "DevOps Engineer",
            "company": "CloudScale",
            "location": "Hyderabad, Telangana",
            "description": "DevOps Engineer to manage cloud infrastructure.",
            "salary": "₹14L - ₹22L",
            "skills": ["Kubernetes", "Docker", "Terraform", "AWS", "Jenkins"],
        },
    ]
    
    from parsers.salary_parser import parse_salary_range
    from parsers.skills_extractor import normalize_skill_name
    
    jobs_saved = 0
    for job_data in sample_jobs:
        try:
            raw_job_id = db.save_raw_job(job_data, "demo")
            
            salary_min, salary_max = parse_salary_range(job_data["salary"])
            
            is_remote = "remote" in job_data["location"].lower()
            is_hybrid = "hybrid" in job_data["location"].lower()
            
            db.save_parsed_job(raw_job_id, {
                "title": job_data["title"],
                "company": job_data["company"],
                "location": job_data["location"],
                "description": job_data["description"],
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": "INR",
                "skills": [normalize_skill_name(s) for s in job_data["skills"]],
                "is_remote": is_remote,
                "is_hybrid": is_hybrid,
                "is_onsite": not is_remote and not is_hybrid,
                "application_url": job_data["url"],
            })
            
            jobs_saved += 1
            
        except Exception as e:
            log.warning(f"Failed to save job {job_data['title']}: {e}")
    
    return {
        "message": f"Seeded {jobs_saved} demo jobs",
        "jobs_saved": jobs_saved,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
