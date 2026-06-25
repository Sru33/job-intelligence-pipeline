# Job Intelligence Pipeline

A comprehensive data engineering project that scrapes job postings from Wellfound (and similar sources), extracts and normalizes structured data using regex patterns, stores in SQLite/PostgreSQL, and exposes via FastAPI with search capabilities.

This project demonstrates the core skills behind Teal's product - sourcing, cleaning, and structuring heterogeneous data from various sources.

## What It Does

### Layer 1 - Scraper
- Scrapes job postings from Wellfound.com
- Handles pagination, rate limiting, retry logic with exponential backoff
- Respects robots.txt, rotates user-agents
- Demonstrates HTTP awareness (429 handling, session reuse)

### Layer 2 - Parser
- Extracts fields: title, company, salary, location, skills, posted date
- Regex patterns to normalize salary ranges (e.g., ₹7.2L–₹9L → {min: 720000, max: 900000})
- Parses skills from unstructured description using keyword matching + regex
- Handles messy/inconsistent formats

### Layer 3 - Storage
- SQLite (development) or PostgreSQL (production) via SQLAlchemy
- Schema: raw_jobs, parsed_jobs, skills tables
- Deduplication logic (hash on URL or title+company+date)

### Layer 4 - API
- FastAPI with GET /jobs?skill=python&location=remote&min_salary=700000
- Full-text search capabilities
- RESTful endpoints for querying jobs

## Features

### Scraper Highlights
- **Exponential backoff** retry logic for handling rate limits (429s)
- **Session reuse** with connection pooling
- **User-agent rotation** to avoid detection
- **Polite scraping** with configurable rate limiting (default: 1 request/second)
- **Abstract base class** design for extensibility

### Parser Highlights
- **Complex regex patterns** for salary normalization:
  - Indian formats: ₹7.2L, ₹7.2LPA, ₹15L → numeric values
  - USD formats: $80k, $80K → thousands
  - Plain numbers: 1500000, 15,00,000
- **Skills extraction** using keyword matching + regex
- **Context-aware** detection of skills in various formats
- **Unit tested** - 20+ test cases

### Storage Highlights
- **SQLAlchemy ORM** for database abstraction
- **Proper indexing** for query performance
- **Batch operations** for efficiency
- **Many-to-many** job-skills relationships

### API Highlights
- **RESTful design** with proper HTTP verbs
- **Pydantic models** for request/response validation
- **CORS enabled** for frontend integration
- **Demo data seeder** for quick testing

## Project Structure

```
job-intelligence-pipeline/
├── scraper/
│   ├── base_scraper.py       # Abstract class, retry logic, rate limiting
│   ├── wellfound_scraper.py  # Site-specific implementation
│   └── utils.py              # Headers, session management
├── parsers/
│   ├── salary_parser.py      # Regex to normalize salary formats
│   ├── skills_extractor.py # Keyword + regex skills extraction
│   └── html_cleaner.py     # Clean HTML content
├── storage/
│   ├── models.py             # SQLAlchemy models
│   └── db.py                # Database connection + dedup logic
├── api/
│   └── main.py               # FastAPI app
├── tests/
│   ├── test_salary_parser.py
│   └── test_skills_extractor.py
├── requirements.txt
└── README.md
```

## Requirements

```
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
fastapi>=0.104.0
uvicorn>=0.24.0
sqlalchemy>=2.0.0
aiosqlite>=0.19.0
psycopg2-binary>=2.9.0
pandas>=2.0.0
pydantic>=2.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.25.0
```

## Installation

```bash
# Clone and navigate to project
cd job-intelligence-pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running

### Run the API Server

```bash
cd job-intelligence-pipeline
uvicorn api.main:app --reload --port 8000

# API will be available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Seed Demo Data

```bash
# After starting the server, seed demo data
curl -X POST http://localhost:8000/demo/seed
```

### Search Jobs via API

```bash
# Get all jobs
curl "http://localhost:8000/jobs"

# Filter by skill
curl "http://localhost:8000/jobs?skill=python"

# Filter by skill + location + salary
curl "http://localhost:8000/jobs?skill=python&location=remote&min_salary=700000"

# Filter by company
curl "http://localhost:8000/jobs?company=techcorp"

# Get stats
curl "http://localhost:8000/stats"
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_salary_parser.py -v
pytest tests/test_skills_extractor.py -v
```

## Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Unit Tests (All 32 tests pass)
```bash
pytest tests/ -v
```

Expected output:
```
============================= test session starts ==============================
tests/test_salary_parser.py::TestParseSalaryValue::test_parse_inr_lakhs PASSED     [  3%]
tests/test_salary_parser.py::TestParseSalaryValue::test_parse_thousands PASSED  [  6%]
...
tests/test_skills_extractor.py::TestExtractSkills::test_extract_python PASSED [100%]

=========================== 32 passed in 1.50s ===============================
```

### 3. Start the API Server
```bash
uvicorn api.main:app --reload --port 8000
```

### 4. Seed Demo Data
```bash
curl -X POST http://localhost:8000/demo/seed
```

Expected output:
```json
{"message":"Seeded 5 demo jobs","jobs_saved":5}
```

### 5. Test the API
```bash
# Get all jobs
curl "http://localhost:8000/jobs"
```

```bash
# Filter by skill
curl "http://localhost:8000/jobs?skill=python"
```

```bash
# Get stats
curl "http://localhost:8000/stats"
```

Expected stats output:
```json
{
  "total_jobs":5,
  "total_skills":12,
  "remote_jobs":2,
  "latest_scrape":null,
  "jobs_found_latest":0
}
```

## Key Regex Patterns

### Salary Parser

The salary parser handles multiple formats:

```python
# Indian Lakh format
"₹7.2L–₹9L" → min=720000, max=900000
"₹15L" → min=1500000, max=1500000
"Rs. 7.2LPA" → min=720000, max=720000

# US thousand format  
"$80k - $120k" → min=80000, max=120000
"$80000" → min=80000, max=80000

# Plain numbers
"80000 - 120000" → min=80000, max=120000
"₹15,00,000 - ₹25,00,000" → min=1500000, max=2500000
```

### Skills Extraction

Supports 50+ skills across categories:
- **Languages**: Python, JavaScript, TypeScript, Java, Go, Rust, etc.
- **Frameworks**: React, Angular, Vue, Django, Flask, etc.
- **ML/AI**: Machine Learning, Deep Learning, TensorFlow, PyTorch
- **Databases**: PostgreSQL, MongoDB, Redis, Elasticsearch
- **Cloud/DevOps**: AWS, GCP, Azure, Kubernetes, Docker, Terraform

## API Endpoints

| Endpoint | Method | Description |
|---------|--------|-----------|
| `/` | GET | Root endpoint |
| `/jobs` | GET | Search jobs with filters |
| `/jobs/{id}` | GET | Get job by ID |
| `/skills` | GET | List all skills |
| `/stats` | GET | Get database statistics |
| `/demo/seed` | POST | Seed demo data |
| `/health` | GET | Health check |

## Query Parameters

- `skill` - Filter by skill name (e.g., python, react, aws)
- `location` - Filter by location (e.g., Bangalore, Remote)
- `min_salary` - Minimum annual salary (in local currency)
- `company` - Filter by company name
- `remote` - Filter remote jobs only (true/false)
- `job_type` - Filter by job type (full-time, contract, etc.)
- `page` - Page number (default: 1)
- `page_size` - Results per page (default: 100, max: 500)

## Example API Response

```json
{
  "total": 2,
  "jobs": [
    {
      "id": 1,
      "title": "Senior Python Developer",
      "company": "TechCorp India",
      "location": "Bangalore, Karnataka",
      "description": "We are looking for a Senior Python Developer...",
      "salary_min": 1500000,
      "salary_max": 2500000,
      "salary_currency": "INR",
      "job_type": "Full-time",
      "is_remote": false,
      "is_hybrid": true,
      "is_onsite": false,
      "skills": ["python", "django", "postgresql"],
      "created_at": "2024-01-15T10:30:00"
    }
  ],
  "page": 1,
  "page_size": 100
}
```

## Design Decisions

### Why This Structure?

| Requirement | How It's Handled |
|-------------|----------------|
| HTTP request/response handling | `requests.Session` with retry adapter; explicit 429 handling |
| Rate limiting | Fixed delay + random jitter in `_wait()` method |
| Regex parsing | Standalone parser modules, each unit-tested |
| Resilience | Per-record error catching instead of batch failure |
| Extensibility | Abstract base class - add new source via subclass |
| Structured API | FastAPI with Pydantic models |

## Extending to New Sources

Adding a new job site is straightforward:

```python
from scraper.base_scraper import BaseScraper, ScrapedJob

class NewSiteScraper(BaseScraper):
    BASE_URL = "https://newsite.com"
    
    def get_job_listings(self, page):
        # Implement page fetching
        pass
    
    def parse_job_details(self, job_card, base_url):
        # Implement parsing
        pass
```

## Timeline Estimate

| Phase | Time |
|-------|------|
| Scraper + HTTP layer | 2-3 days |
| Parser + regex | 1-2 days |
| Storage + dedup | 1 day |
| FastAPI | 1 day |
| Tests + README | 1 day |
| **Total** | ~1 week |

## Nice-to-Haves (Implemented)

- [x] SQLite/PostgreSQL with SQLAlchemy
- [x] FastAPI with full-text search
- [ ] Elasticsearch/OpenSearch indexing
- [ ] Grafana dashboard (metrics)
- [ ] PDF extraction with OCR

## Credits

This project was built to demonstrate:
- HTTP fundamentals (retries, backoff, rate limiting)
- Complex regex patterns (salary normalization)
- HTML parsing with BeautifulSoup
- Database design with SQLAlchemy
- REST API design with FastAPI
- Clean, maintainable, extensible code

The domain (job postings) was chosen as a subtle signal of understanding Teal's product - sourcing, structuring, and making job data usable through APIs.
