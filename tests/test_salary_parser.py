"""
Unit Tests for Salary Parser
---------------------------
Tests the salary parsing regex patterns.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from parsers.salary_parser import (
    parse_salary_range,
    parse_salary_value,
    normalize_salary,
    extract_currency,
    _convert_inr_lakhs,
    _convert_thousands,
    _convert_plain_number,
)


class TestParseSalaryValue:
    """Tests for parsing individual salary values."""
    
    def test_parse_inr_lakhs(self):
        assert _convert_inr_lakhs("7.2L") == 720000
        assert _convert_inr_lakhs("15L") == 1500000
        assert _convert_inr_lakhs("7.2LPA") == 720000
    
    def test_parse_thousands(self):
        assert _convert_thousands("80k") == 80000
        assert _convert_thousands("50K") == 50000
        assert _convert_thousands("120kpa") == 120000
    
    def test_parse_plain_number(self):
        assert _convert_plain_number("1500000") == 1500000
        assert _convert_plain_number("1500000.00") == 1500000.00
        assert _convert_plain_number("15,00,000") == 1500000


class TestParseSalaryRange:
    """Tests for parsing salary ranges."""
    
    def test_parse_inr_lakhs_range(self):
        min_val, max_val = parse_salary_range("₹7.2L–₹9L")
        assert min_val == 720000
        assert max_val == 900000
    
    def test_parse_inr_lakhs_range_with_spaces(self):
        min_val, max_val = parse_salary_range("₹7.2L - ₹9L")
        assert min_val == 720000
        assert max_val == 900000
    
    def test_parse_dollar_k_range(self):
        min_val, max_val = parse_salary_range("$80k - $120k")
        assert min_val == 80000
        assert max_val == 120000
    
    def test_parse_inr_comma_separated(self):
        min_val, max_val = parse_salary_range("₹15,00,000 - ₹25,00,000")
        assert min_val == 1500000
        assert max_val == 2500000
    
    def test_parse_plain_number_range(self):
        min_val, max_val = parse_salary_range("80000 - 120000")
        assert min_val == 80000
        assert max_val == 120000
    
    def test_parse_single_value(self):
        min_val, max_val = parse_salary_range("₹15L")
        assert min_val == 1500000
        assert max_val == 1500000
    
    def test_parse_rs_format(self):
        min_val, max_val = parse_salary_range("Rs. 7.2LPA")
        assert min_val == 720000
        assert max_val == 720000

    def test_parse_invalid_returns_none(self):
        min_val, max_val = parse_salary_range("")
        assert min_val is None
        assert max_val is None
    
    def test_parse_min_greater_than_max_swapped(self):
        min_val, max_val = parse_salary_range("₹9L - ₹7.2L")
        assert min_val == 720000
        assert max_val == 900000


class TestNormalizeSalary:
    """Tests for salary normalization."""
    
    def test_normalize_yearly(self):
        result = normalize_salary("₹15L - ₹25L")
        assert result["min"] == 1500000
        assert result["max"] == 2500000
        assert result["currency"] == "INR"
        assert result["period"] == "yearly"
    
    def test_normalize_monthly(self):
        result = normalize_salary("₹1.5L - ₹2L", period="monthly")
        assert result["min"] == 180000  # 15000 * 12
        assert result["period"] == "monthly"


class TestExtractCurrency:
    """Tests for currency extraction."""
    
    def test_extract_inr_rupee(self):
        currency, cleaned = extract_currency("₹7.2L")
        assert currency == "INR"
        assert "₹" not in cleaned
    
    def test_extract_usd(self):
        currency, cleaned = extract_currency("$80k")
        assert currency == "USD"
        assert "$" not in cleaned
    
    def test_extract_no_currency(self):
        currency, cleaned = extract_currency("80000")
        assert currency is None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
