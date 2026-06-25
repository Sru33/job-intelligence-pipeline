"""
Skills Extractor
-----------------
Extracts skills and technologies from job descriptions using:
- Keyword matching
- Regex patterns
- Context-aware detection

Supports common programming languages, frameworks, and tools.
This demonstrates text processing and pattern matching skills.
"""

import logging
import re
from typing import Optional

log = logging.getLogger(__name__)

# Comprehensive skill keywords organized by category
SKILL_KEYWORDS = {
    # Programming Languages
    "python": ["python", "py"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "java": [" java ", "java ", " java"],
    "kotlin": ["kotlin"],
    "swift": ["swift"],
    "go": [" golang ", "go ", " go "],
    "rust": ["rust"],
    "c": [" c ", "c ", " c "],
    "cpp": ["c++", "c plus plus"],
    "csharp": ["c#", "c sharp"],
    "ruby": ["ruby", "rails"],
    "php": ["php"],
    "scala": ["scala"],
    "r": [" r ", "r ", " r "],
    
    # Web Frameworks
    "react": ["react", "reactjs", "react.js"],
    "vue": ["vue", "vuejs", "vue.js"],
    "angular": ["angular", "angularjs"],
    "nextjs": ["next.js", "nextjs"],
    "svelte": ["svelte"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "express": ["express", "expressjs"],
    "spring": ["spring", "spring boot"],
    "rails": ["rails", "ruby on rails"],
    "laravel": ["laravel"],
    "aspnet": ["asp.net", "aspnet"],
    
    # Data Science & ML
    "machine learning": [
        "machine learning", "ml", " ml ", 
        "machine-learning", "mlops"
    ],
    "deep learning": [
        "deep learning", "dl", "neural network",
        "pytorch", "tensorflow", "keras"
    ],
    "nlp": ["nlp", "natural language processing", "text analytics"],
    "data science": ["data science", "data analyst", "scientist"],
    "tensorflow": ["tensorflow", "tf"],
    "pytorch": ["pytorch"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "jupyter": ["jupyter", "jupyter notebook"],
    
# Databases - separate specific databases first to avoid substring issues
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic"],
    "dynamodb": ["dynamodb", "dynamo"],
    "firebase": ["firebase"],
    "sqlite": ["sqlite"],
    "oracle": ["oracle db"],
    # SQL must come after specific databases to avoid matching "postgresql" as "sql"
    "sql": ["sql"],
    
    # Cloud & DevOps
    "aws": ["aws", "amazon web services", "amazon s3", "ec2", "lambda"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "azure": ["azure", "microsoft azure"],
    "kubernetes": ["kubernetes", "k8s", "kubectl"],
    "docker": ["docker", "dockerfile", "container"],
    "terraform": ["terraform", "tf"],
    "ansible": ["ansible"],
    "jenkins": ["jenkins"],
    "ci/cd": ["ci/cd", "cicd", "continuous integration", "devops"],
    
    # Tools & Other
    "git": ["git", "github", "gitlab", "bitbucket"],
    "graphql": ["graphql", "apollo"],
    "rest": ["rest", "rest api", "restful"],
    "api": ["api", "apis"],
    "microservices": ["microservice", "microservices"],
    "agile": ["agile", "scrum", "kanban"],
    "jira": ["jira"],
    "linux": ["linux", "unix", "ubuntu", "centos"],
    
    # Soft Skills (often mentioned)
    "communication": ["communication", "communication skills"],
    "leadership": ["leadership", "lead"],
    "teamwork": ["teamwork", "team player"],
}


# Additional regex patterns for specific skill formats
SKILL_PATTERNS = [
    # Programming languages in bullet points
    (r"(?:^|\n)\s*[-*•]\s*([A-Z][a-zA-Z+#]+)", 1),  # e.g., "- Python"
    
    # Language/framework with version
    (r"(?:React|Angular|Vue|Django|Flask|Python|Java|Go|Rust)\s*\.?\s*(\d+(?:\.\d+)*)", 0),
    
    # "Proficient in X" or "Experience with X"
    (r"(?:proficient|experience|skilled|knowledgeable)\s+(?:in|with)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", 1),
    
    # Tools section
    (r"(?:tools|technologies|tech stack)[\s:]+([A-Z][a-zA-Z]+(?:\s*,\s*[A-Z][a-zA-Z]+)*)", 1),
]


def normalize_skill_name(skill: str) -> str:
    """
    Normalize skill name for consistent matching.
    
    - Convert to lowercase
    - Strip whitespace
    - Map aliases
    """
    skill = skill.lower().strip()
    
    # Map common aliases
    ALIAS_MAP = {
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
        "c++": "cpp",
        "c#": "csharp",
        "go": "go",
        "rb": "ruby",
        "py": "python",
        "mongo": "mongodb",
        "postgres": "postgresql",
        "tf": "tensorflow",
    }
    
    return ALIAS_MAP.get(skill, skill)


def extract_skills_v1(text: str) -> list[str]:
    """
    Method 1: Simple keyword matching.
    
    Fast, works well for exact matches.
    """
    text_lower = text.lower()
    skills = []
    
    # Check for each skill keyword
    for skill, keywords in SKILL_KEYWORDS.items():
        for keyword in keywords:
            # Match whole word case-insensitively
            pattern = re.escape(keyword)
            if re.search(pattern, text_lower):
                skills.append(skill)
                break
    
    return list(set(skills))  # Remove duplicates


def extract_skills_v2(text: str) -> list[str]:
    """
    Method 2: Regex pattern matching.
    
    More sophisticated, can catch variations.
    """
    text_lower = text.lower()
    skills = []
    
# Check each skill category - longer keywords first to avoid substring matching issues
    # Sort keywords by length (longest first) to prefer "postgresql" over "sql"
    for skill, keywords in SKILL_KEYWORDS.items():
        # Sort keywords by length (descending) so longer matches are tried first
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        keywords_pattern = "|".join(re.escape(kw) for kw in sorted_keywords)
        pattern = f"(?:{keywords_pattern})(?![a-zA-Z])"  # Negative lookahead
        
        if re.search(pattern, text_lower, re.IGNORECASE):
            skills.append(skill)
    
    return list(set(skills))


def extract_skills_regex(text: str) -> list[str]:
    """
    Method 3: Regex patterns for structured formats.
    
    Catches skills in lists, bullet points, etc.
    """
    skills = []
    
    # Look for skill patterns in the text
    for pattern, group_idx in SKILL_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if group_idx > 0 and match.lastindex and group_idx <= match.lastindex:
                skill = match.group(group_idx)
                if skill:
                    skills.append(normalize_skill_name(skill.strip()))
            elif match.lastindex:
                skill = match.group(1)
                if skill:
                    skills.append(normalize_skill_name(skill.strip()))
    
    return list(set(skills))


def extract_skills(
    text: str,
    method: str = "hybrid",
    min_confidence: float = 0.0,
) -> list[dict]:
    """
    Extract skills from job description text.
    
    Args:
        text: Job description text
        method: Extraction method - "keyword", "regex", "hybrid"
        min_confidence: Minimum confidence threshold (0-1)
    
    Returns:
        List of dicts with skill name and confidence:
        [{"skill": "python", "confidence": 0.95, "method": "keyword"}, ...]
    """
    if not text:
        return []
    
    # Clean the text
    text = text.strip()
    
    if len(text) < 5:
        log.debug("Text too short for skill extraction")
        return []
    
    skill_scores = {}
    
    # Method 1: Keyword matching
    if method in ["keyword", "hybrid"]:
        skills_v1 = extract_skills_v1(text)
        for skill in skills_v1:
            skill_scores[skill] = skill_scores.get(skill, 0) + 0.9
    
    # Method 2: Regex with context
    if method in ["regex", "hybrid"]:
        skills_v2 = extract_skills_v2(text)
        for skill in skills_v2:
            skill_scores[skill] = skill_scores.get(skill, 0) + 0.85
    
    # Method 3: Regex patterns
    if method in ["regex", "hybrid"]:
        # Already captured in v2
        pass
    
    # Convert to list with confidence scores
    results = []
    for skill, score in skill_scores.items():
        # Normalize score to 0-1
        confidence = min(1.0, score)
        
        if confidence >= min_confidence:
            results.append({
                "skill": skill,
                "confidence": confidence,
                "method": method,
            })
    
    # Sort by confidence
    results.sort(key=lambda x: x["confidence"], reverse=True)
    
    return results


def extract_top_skills(
    text: str,
    top_n: int = 10,
) -> list[str]:
    """
    Extract top N skills from text.
    
    Convenience function returning just skill names.
    """
    results = extract_skills(text, method="hybrid")
    return [r["skill"] for r in results[:top_n]]


def get_skill_category(skill: str) -> str:
    """Get the category for a skill."""
    skill = normalize_skill_name(skill)
    
    # Map skill to category
    skill_lower = skill.lower()
    
    if skill_lower in ["python", "java", "javascript", "typescript", "go", "rust", "ruby", "kotlin", "swift", "scala", "r", "php", "c", "cpp", "csharp"]:
        return "language"
    elif skill_lower in ["react", "angular", "vue", "django", "flask", "spring", "rails", "express", "nextjs", "svelte"]:
        return "framework"
    elif skill_lower in ["machine learning", "deep learning", "nlp", "tensorflow", "pytorch", "scikit-learn"]:
        return "ml_ai"
    elif skill_lower in ["sql", "mongodb", "redis", "elasticsearch", "dynamodb", "firebase", "postgresql", "mysql"]:
        return "database"
    elif skill_lower in ["aws", "gcp", "azure", "kubernetes", "docker", "terraform", "jenkins"]:
        return "cloud_devops"
    elif skill_lower in ["git", "graphql", "rest", "jira", "linux"]:
        return "tools"
    else:
        return "other"


# Test examples
if __name__ == "__main__":
    job_description = """
    We are looking for a Senior Software Engineer to join our team.
    
    Requirements:
    - 5+ years of experience with Python and JavaScript
    - Experience with React, Django or Flask
    - Knowledge of PostgreSQL and Redis
    - Familiar with AWS or GCP
    - Experience with Docker and Kubernetes
    - Strong communication skills
    
    Nice to have:
    - Experience with machine learning or deep learning
    - Knowledge of TensorFlow or PyTorch
    - Experience with GraphQL
    """
    
    print("Skills Extraction Test:")
    print("=" * 60)
    print(f"\nInput: {job_description[:200]}...")
    
    print("\n--- Extracted Skills (hybrid method) ---")
    skills = extract_skills(job_description)
    for s in skills:
        print(f"  {s['skill']}: {s['confidence']:.2f}")
    
    print("\n--- Top 10 Skills ---")
    top_skills = extract_top_skills(job_description, top_n=10)
    for i, skill in enumerate(top_skills, 1):
        print(f"  {i}. {skill}")
    
    print("\n--- Skills by Category ---")
    from collections import defaultdict
    by_category = defaultdict(list)
    for s in skills:
        category = get_skill_category(s["skill"])
        by_category[category].append(s["skill"])
    
    for category, cat_skills in sorted(by_category.items()):
        print(f"  {category}: {', '.join(cat_skills)}")
