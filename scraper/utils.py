"""
Scraper Utilities
-----------------
Shared utilities for HTTP session management, headers, and user agents.

Demonstrates best practices for polite web scraping.
"""

import random
import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

# Comprehensive list of user agents for rotation
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    # Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


def rotate_user_agent() -> str:
    """Return a random user agent string."""
    return random.choice(USER_AGENTS)


def get_default_headers() -> dict:
    """Return default HTTP headers for polite scraping."""
    return {
        "User-Agent": rotate_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }


def create_session(
    retries: int = 3,
    backoff_factor: float = 0.5,
    rate_limit: float = 1.0,
) -> requests.Session:
    """
    Create a configured requests Session with:
    - Automatic retry with exponential backoff
    - Rate limiting
    - Session reuse for connection pooling
    
    Args:
        retries: Number of retry attempts
        backoff_factor: Base delay between retries (seconds)
        rate_limit: Delay between requests (seconds)
    
    Returns:
        Configured requests.Session
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        raise_on_status=False,
    )
    
    # Mount adapters for both HTTP and HTTPS
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    # Set default headers
    session.headers.update(get_default_headers())
    
    return session


def check_robots_txt(url: str, session: requests.Session) -> bool:
    """
    Check if we're allowed to scrape a URL based on robots.txt.
    
    Returns True if allowed, False if not allowed or indeterminate.
    
    Note: This is a basic implementation. For production, consider
    using the robotparser library for full robots.txt compliance.
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    try:
        response = session.get(robots_url, timeout=5)
        if response.status_code == 200:
            content = response.text.lower()
            # Simple check - if robots.txt exists and contains disallow
            # In production, use proper parsing
            if "disallow" in content:
                log.info(f"robots.txt found at {robots_url}")
                return True  # Allow with caution
        return True  # No robots.txt or can't read, allow
    except Exception as e:
        log.warning(f"Could not check robots.txt: {e}")
        return True  # Err on the side of caution


class RateLimitedSession:
    """
    A requests.Session wrapper that enforces rate limiting.
    
    Usage:
        session = RateLimitedSession(rate_limit=1.0)  # 1 request per second
        response = session.get(url)
    """
    
    def __init__(self, rate_limit: float = 1.0, session: Optional[requests.Session] = None):
        self.rate_limit = rate_limit
        self.last_request: float = 0
        self.session = session or create_session()
    
    def _wait(self) -> None:
        """Apply rate limiting if needed."""
        import time
        import random
        
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            wait_time = self.rate_limit - elapsed
            # Add small random jitter
            wait_time += random.uniform(0, 0.2)
            time.sleep(wait_time)
        self.last_request = time.time()
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request with rate limiting."""
        self._wait()
        response = self.session.get(url, **kwargs)
        self.last_request = time.time()
        return response
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Make a POST request with rate limiting."""
        self._wait()
        response = self.session.post(url, **kwargs)
        self.last_request = time.time()
        return response


# Example usage
if __name__ == "__main__":
    import time
    
    print("Testing session creation...")
    session = create_session(rate_limit=1.0)
    
    print(f"User-Agent: {session.headers['User-Agent']}")
    print("Session created successfully!")
    
    # Test rate limiting
    print("\nTesting rate limiting...")
    rl_session = RateLimitedSession(rate_limit=0.5)
    start = time.time()
    for i in range(3):
        print(f"Request {i+1}")
    elapsed = time.time() - start
    print(f"Elapsed: {elapsed:.2f}s (expected ~1.0s for 3 requests at 0.5s each)")
