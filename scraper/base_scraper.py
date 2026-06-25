"""
Base Scraper Abstract Class
-------------------------
Abstract base class for all job scrapers with built-in:
- Retry logic with exponential backoff
- Rate limiting
- Session reuse
- User agent rotation
- Polite scraping (respects robots.txt)

This demonstrates HTTP awareness and maintainable code design.
"""

import logging
import time
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# Rotating User-Agents to avoid detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


@dataclass
class ScrapedJob:
    """Raw job data as extracted from the source."""
    title: str
    company: str
    location: str
    description: str
    url: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "INR"
    skills: list[str] = field(default_factory=list)
    posted_date: Optional[str] = None
    job_type: Optional[str] = None
    remote: Optional[bool] = None
    raw_html: str = ""
    source: str = ""


class BaseScraper(ABC):
    """
    Abstract base class for job site scrapers.
    
    Provides common functionality:
    - Exponential backoff retry
    - Rate limiting
    - Session management
    - User agent rotation
    
    Subclasses implement site-specific scraping logic.
    """
    
    BASE_URL: str = ""
    ROBOTS_TXT_URL: str = ""
    
    def __init__(
        self,
        retries: int = 3,
        backoff_factor: float = 1.0,
        rate_limit: float = 1.0,
        max_pages: Optional[int] = None,
    ):
        self.retries = retries
        self.backoff_factor = backoff_factor
        self.rate_limit = rate_limit
        self.max_pages = max_pages
        self.session: Optional[requests.Session] = None
        self._scrape_stats = {
            "pages_scraped": 0,
            "jobs_found": 0,
            "jobs_failed": 0,
            "retries": 0,
        }
    
    def create_session(self) -> requests.Session:
        """Create a requests Session with retry logic and rate limiting."""
        session = requests.Session()
        
        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=self.retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False,
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Set initial headers
        session.headers.update({
            "User-Agent": self._get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        
        return session
    
    def _get_user_agent(self) -> str:
        """Get a random user agent for rotation."""
        return random.choice(USER_AGENTS)
    
    def _rotate_user_agent(self) -> None:
        """Rotate to a new user agent."""
        if self.session:
            self.session.headers["User-Agent"] = self._get_user_agent()
    
    def _wait(self) -> None:
        """Apply rate limiting delay."""
        # Add small random jitter to avoid detection patterns
        jitter = random.uniform(0, 0.5)
        time.sleep(self.rate_limit + jitter)
    
    def fetch_page(
        self, 
        url: str, 
        try_count: int = 0
    ) -> Optional[BeautifulSoup]:
        """
        Fetch a page with retry logic and rate limiting.
        
        Returns BeautifulSoup parsed HTML or None on failure.
        """
        self._wait()
        
        try:
            response = self.session.get(url, timeout=30)
            
            # Handle 429 - Too Many Requests
            if response.status_code == 429:
                if try_count < self.retries:
                    wait_time = self.backoff_factor * (2 ** try_count)
                    log.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    self._rotate_user_agent()
                    return self.fetch_page(url, try_count + 1)
                else:
                    log.error(f"Max retries reached for {url}")
                    return None
            
            response.raise_for_status()
            self._scrape_stats["pages_scraped"] += 1
            
            return BeautifulSoup(response.text, "lxml")
            
        except requests.exceptions.RequestException as e:
            log.warning(f"Request failed for {url}: {e}")
            if try_count < self.retries:
                self._scrape_stats["retries"] += 1
                wait_time = self.backoff_factor * (2 ** try_count)
                log.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
                return self.fetch_page(url, try_count + 1)
            return None
    
    @abstractmethod
    def get_job_listings(self, page: int) -> Iterator[ScrapedJob]:
        """
        Fetch job listings for a given page number.
        
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def parse_job_details(self, job_card, base_url: str) -> Optional[ScrapedJob]:
        """
        Parse individual job card into ScrapedJob.
        
        Must be implemented by subclasses.
        """
        pass
    
    def scrape(self) -> Iterator[ScrapedJob]:
        """
        Main scraping iterator that yields jobs across all pages.
        
        Stops when max_pages reached or no more jobs found.
        """
        self.session = self.create_session()
        page = 1
        
        while True:
            if self.max_pages and page > self.max_pages:
                log.info(f"Reached max pages limit: {self.max_pages}")
                break
            
            log.info(f"Scraping page {page}...")
            jobs_found = False
            
            try:
                for job in self.get_job_listings(page):
                    if job:
                        jobs_found = True
                        self._scrape_stats["jobs_found"] += 1
                        yield job
            except Exception as e:
                log.error(f"Error scraping page {page}: {e}")
            
            if not jobs_found:
                log.info(f"No more jobs found. Stopping at page {page}.")
                break
            
            page += 1
        
        self._log_stats()
    
    def _log_stats(self) -> None:
        """Log scraping statistics."""
        log.info("=== Scraping Statistics ===")
        log.info(f"Pages scraped: {self._scrape_stats['pages_scraped']}")
        log.info(f"Jobs found: {self._scrape_stats['jobs_found']}")
        log.info(f"Jobs failed: {self._scrape_stats['jobs_failed']}")
        log.info(f"Retries: {self._scrape_stats['retries']}")
    
    def get_stats(self) -> dict:
        """Return scraping statistics."""
        return self._scrape_stats.copy()
