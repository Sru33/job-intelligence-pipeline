"""
Unit Tests for Skills Extractor
-----------------------------
Tests the skills extraction functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from parsers.skills_extractor import (
    extract_skills,
    extract_top_skills,
    normalize_skill_name,
    get_skill_category,
)


class TestExtractSkills:
    """Tests for skill extraction."""
    
    def test_extract_python(self):
        text = "We are looking for a Python developer with Django experience."
        skills = extract_skills(text)
        skill_names = [s["skill"] for s in skills]
        assert "python" in skill_names
    
    def test_extract_multiple_skills(self):
        text = "Experience with Python, JavaScript, React, and PostgreSQL required."
        skills = extract_skills(text)
        skill_names = [s["skill"] for s in skills]
        assert "python" in skill_names
        assert "javascript" in skill_names
        assert "react" in skill_names
        assert "postgresql" in skill_names
    
    def test_extract_machine_learning(self):
        text = "Machine learning and deep learning experience preferred."
        skills = extract_skills(text)
        skill_names = [s["skill"] for s in skills]
        assert "machine learning" in skill_names
    
    def test_extract_cloud_skills(self):
        text = "AWS and GCP experience required. Docker and Kubernetes."
        skills = extract_skills(text)
        skill_names = [s["skill"] for s in skills]
        assert "aws" in skill_names or "gcp" in skill_names
    
    def test_empty_text(self):
        text = ""
        skills = extract_skills(text)
        assert len(skills) == 0
    
    def test_short_text(self):
        text = "Hi"
        skills = extract_skills(text)
        assert len(skills) == 0


class TestExtractTopSkills:
    """Tests for top skills extraction."""
    
    def test_top_skills_returns_list(self):
        text = "Python JavaScript React Django Node.js PostgreSQL MongoDB"
        skills = extract_top_skills(text)
        assert isinstance(skills, list)
    
    def test_top_skills_respects_limit(self):
        text = "Python JavaScript React Django Node.js PostgreSQL MongoDB"
        skills = extract_top_skills(text, top_n=3)
        assert len(skills) <= 3


class TestNormalizeSkillName:
    """Tests for skill name normalization."""
    
    def test_lowercase(self):
        assert normalize_skill_name("PYTHON") == "python"
    
    def test_alias_mapping(self):
        assert normalize_skill_name("js") == "javascript"
        assert normalize_skill_name("ts") == "typescript"
        assert normalize_skill_name("mongo") == "mongodb"


class TestGetSkillCategory:
    """Tests for skill categorization."""
    
    def test_language_category(self):
        assert get_skill_category("python") == "language"
        assert get_skill_category("java") == "language"
    
    def test_framework_category(self):
        assert get_skill_category("react") == "framework"
        assert get_skill_category("django") == "framework"
    
    def test_ml_ai_category(self):
        assert get_skill_category("machine learning") == "ml_ai"
        assert get_skill_category("tensorflow") == "ml_ai"
    
    def test_database_category(self):
        assert get_skill_category("postgresql") == "database"
        assert get_skill_category("mongodb") == "database"
    
    def test_cloud_devops_category(self):
        assert get_skill_category("aws") == "cloud_devops"
        assert get_skill_category("kubernetes") == "cloud_devops"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
