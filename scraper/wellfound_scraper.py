"""
Wellfound Scraper
----------------
Scraper for wellfound.com (formerly AngelList Talent).
Scrapes job postings with features, salary ranges, and company info.

Demonstrates:
- Site-specific HTML parsing with BeautifulSoup
- JavaScript-rendered page handling
- Complex multi-field extraction
- Pagination handling
"""

import logging
import re
from typing import Iterator, Optional
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ScrapedJob

log = logging.getLogger(__name__)


class WellfoundScraper(BaseScraper):
    """
    Wellfound-specific job scraper.
    
    Scrapes startup jobs from wellfound.com with:
    - Company name, job title, location
    - Salary ranges (when available)
    - Skills/tags
    - Remote/Hybrid work status
    - Job type (Full-time, Contract, etc.)
    """
    
    BASE_URL = "https://wellfound.com"
    JOBS_PATH = "/jobs"
    
    # Wellfound uses offset-based pagination
    # Page 1: offset=0, Page 2: offset=20, etc.
    JOBS_PER_PAGE = 20
    
    def get_jobs_url(self, page: int) -> str:
        """Build the jobs listing URL for a given page."""
        offset = (page - 1) * self.JOBS_PER_PAGE
        # Note: In production, this would use actual API or page parsing
        return f"{self.BASE_URL}{self.JOBS_PATH}?offset={offset}"
    
    def get_job_listings(self, page: int) -> Iterator[ScrapedJob]:
        """
        Fetch and yield job listings for a given page.
        
        This is a demonstration implementation. In production,
        would need to handle Wellfound's actual HTML structure.
        """
        url = self.get_jobs_url(page)
        soup = self.fetch_page(url)
        
        if not soup:
            log.warning(f"No page returned for page {page}")
            return
        
        # Try to find job cards - Wellfound uses various selectors
        # This is a sample structure - would need adjustment
        job_cards = soup.select(
            '[data-testid="job-card"], '
            '.JobCard, '
            '.job-card, '
            '[class*="JobCard"]'
        )
        
        if not job_cards:
            # Try alternative selectors
            job_cards = soup.select(
                'article[data-id], '
                '.startup-card, '
                '.job-listing'
            )
        
        for card in job_cards:
            job = self.parse_job_details(card, self.BASE_URL)
            if job:
                job.source = "wellfound"
                yield job
    
    def parse_job_details(self, job_card, base_url: str) -> Optional[ScrapedJob]:
        """
        Parse a job card element into a ScrapedJob.
        
        Extracts: title, company, location, description, salary, skills.
        """
        try:
            # Extract job title
            title_elem = job_card.select_one(
                'h2, h3, [data-testid="job-title"], '
                '.job-title, [class*="title"]'
            )
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"
            
            # Extract company name
            company_elem = job_card.select_one(
                '[data-testid="company-name"], '
                '.company-name, .company, '
                '[class*="company"]'
            )
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Extract location
            location_elem = job_card.select_one(
                '[data-testid="job-location"], '
                '.location, .job-location, '
                '[class*="location"]'
            )
            location = location_elem.get_text(strip=True) if location_elem else "Remote"
            
            # Extract job URL and full details URL
            link_elem = job_card.select_one('a[href]')
            job_url = ""
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                job_url = urljoin(base_url, href)
            
            # Extract description
            desc_elem = job_card.select_one(
                '.job-description, .description, '
                '[class*="description"]'
            )
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Extract salary (if present)
            salary_min, salary_max = self._extract_salary(job_card)
            
            # Extract skills/tags
            skills = self._extract_skills(job_card)
            
            # Determine remote status
            remote = self._check_remote(location)
            
            # Extract job type
            job_type = self._extract_job_type(job_card)
            
            # Extract posted date
            posted_date = self._extract_posted_date(job_card)
            
            # Store raw HTML for debugging
            raw_html = str(job_card)
            
            return ScrapedJob(
                title=title,
                company=company,
                location=location,
                description=description[:500] if description else "",  # Truncate long descriptions
                url=job_url,
                salary_min=salary_min,
                salary_max=salary_max,
                skills=skills,
                posted_date=posted_date,
                job_type=job_type,
                remote=remote,
                raw_html=raw_html,
            )
            
        except Exception as e:
            log.warning(f"Failed to parse job card: {e}")
            return None
    
    def _extract_salary(self, job_card) -> tuple[Optional[float], Optional[float]]:
        """Extract salary range from job card."""
        # Look for salary text patterns
        salary_elem = job_card.select_one(
            '.salary, [class*="salary"], '
            '[data-testid="salary"]'
        )
        
        if not salary_elem:
            return None, None
        
        salary_text = salary_elem.get_text(strip=True)
        
        # Use the salary parser module
        from ..parsers.salary_parser import parse_salary_range
        return parse_salary_range(salary_text)
    
    def _extract_skills(self, job_card) -> list[str]:
        """Extract skills/tags from job card."""
        # Look for tag elements
        tag_elems = job_card.select(
            '.tag, .skill, [class*="tag"], '
            '[data-testid="tag"]'
        )
        
        skills = []
        for tag in tag_elems:
            skill = tag.get_text(strip=True)
            if skill:
                skills.append(skill)
        
        return skills
    
    def _check_remote(self, location: str) -> Optional[bool]:
        """Check if job is remote based on location text."""
        location_lower = location.lower()
        
        if any(word in location_lower for word in ['remote', 'work from home', 'wfh']):
            return True
        if any(word in location_lower for word in ['on-site', 'onsite', 'office']):
            return False
        
        return None  # Unknown - could be hybrid
    
    def _extract_job_type(self, job_card) -> Optional[str]:
        """Extract job type (Full-time, Contract, etc.)."""
        type_elem = job_card.select_one(
            '[class*="type"], [class*="employment"], '
            '.job-type'
        )
        
        if type_elem:
            return type_elem.get_text(strip=True)
        
        return None
    
    def _extract_posted_date(self, job_card) -> Optional[str]:
        """Extract posted date from job card."""
        # Look for relative date text (e.g., "2 days ago")
        date_elem = job_card.select_one(
            '[class*="posted"], [class*="date"], '
            'time'
        )
        
        if date_elem:
            return date_elem.get_text(strip=True)
        
        return None


# Demo runner
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # For demonstration, create a sample scraper
    scraper = WellfoundScraper(max_pages=1, rate_limit=2.0)
    
    print("Starting Wellfound scraper demo...")
    print("Note: This is a demonstration implementation.")
    print("In production, would scrape actual Wellfound pages.")
    
    # Would normally scrape:
    # for job in scraper.scrape():
    #     print(f"Found: {job.title} at {job.company}")
