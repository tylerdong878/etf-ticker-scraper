"""
Tests for number parsing utilities in the scrapers.
Tests AUM parsing (M, B, K suffixes) and percentage parsing.
"""
import pytest
from src.scrapers.stockanalysis_scraper import StockAnalysisScraper


class TestAUMParsing:
    """Test AUM (Assets Under Management) parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = StockAnalysisScraper()
    
    def test_parse_millions(self):
        """Test parsing millions format."""
        assert self.scraper._parse_aum("204.39M") == 204_390_000
        assert self.scraper._parse_aum("1.5M") == 1_500_000
        assert self.scraper._parse_aum("999.99M") == 999_990_000
    
    def test_parse_billions(self):
        """Test parsing billions format."""
        assert self.scraper._parse_aum("7.54B") == 7_540_000_000
        assert self.scraper._parse_aum("1.0B") == 1_000_000_000
        assert self.scraper._parse_aum("123.456B") == 123_456_000_000
    
    def test_parse_thousands(self):
        """Test parsing thousands format."""
        assert self.scraper._parse_aum("500K") == 500_000
        assert self.scraper._parse_aum("1.5K") == 1_500
        assert self.scraper._parse_aum("999K") == 999_000
    
    def test_parse_with_commas(self):
        """Test parsing numbers with commas."""
        assert self.scraper._parse_aum("1,234.56M") == 1_234_560_000
        assert self.scraper._parse_aum("10,000K") == 10_000_000
    
    def test_parse_plain_numbers(self):
        """Test parsing plain numbers without suffixes."""
        assert self.scraper._parse_aum("1000000") == 1_000_000
        assert self.scraper._parse_aum("500") == 500
    
    def test_parse_invalid_values(self):
        """Test parsing invalid or missing values."""
        assert self.scraper._parse_aum("-") is None
        assert self.scraper._parse_aum("N/A") is None
        assert self.scraper._parse_aum("") is None
        assert self.scraper._parse_aum("invalid") is None
    
    def test_parse_edge_cases(self):
        """Test edge cases."""
        assert self.scraper._parse_aum("0M") == 0
        assert self.scraper._parse_aum("0.01M") == 10_000
        assert self.scraper._parse_aum("   204.39M   ") == 204_390_000  # whitespace


class TestPercentageParsing:
    """Test percentage parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = StockAnalysisScraper()
    
    def test_parse_positive_percentages(self):
        """Test parsing positive percentages."""
        assert self.scraper._parse_percentage("44.95%") == 0.4495
        assert self.scraper._parse_percentage("1.5%") == 0.015
        assert self.scraper._parse_percentage("100%") == 1.0
        assert self.scraper._parse_percentage("0.5%") == 0.005
    
    def test_parse_negative_percentages(self):
        """Test parsing negative percentages."""
        assert self.scraper._parse_percentage("-25.57%") == -0.2557
        assert self.scraper._parse_percentage("-1.5%") == -0.015
        assert self.scraper._parse_percentage("-100%") == -1.0
    
    def test_parse_without_percent_sign(self):
        """Test parsing percentages without % sign."""
        assert self.scraper._parse_percentage("44.95") == 0.4495
        assert self.scraper._parse_percentage("-25.57") == -0.2557
    
    def test_parse_invalid_percentages(self):
        """Test parsing invalid percentage values."""
        assert self.scraper._parse_percentage("-") is None
        assert self.scraper._parse_percentage("N/A") is None
        assert self.scraper._parse_percentage("") is None
        assert self.scraper._parse_percentage("invalid") is None
    
    def test_parse_edge_cases(self):
        """Test edge cases."""
        assert self.scraper._parse_percentage("0%") == 0.0
        assert self.scraper._parse_percentage("0.01%") == 0.0001
        assert self.scraper._parse_percentage("   44.95%   ") == 0.4495  # whitespace


class TestDirectScraperParsing:
    """Test parsing in direct scrapers."""
    
    def test_kurv_aum_parsing(self):
        """Test Kurv AUM parsing (dollar amounts with commas)."""
        # Simulate the parsing logic from KurvScraper
        test_cases = [
            ("$37,444,045", 37_444_045),
            ("$1,234,567", 1_234_567),
            ("$500", 500),
            ("$1,000,000,000", 1_000_000_000),
        ]
        
        for input_str, expected in test_cases:
            clean_str = input_str.replace('$', '').replace(',', '').strip()
            result = int(float(clean_str))
            assert result == expected
    
    def test_expense_ratio_parsing(self):
        """Test expense ratio parsing."""
        test_cases = [
            ("1.16%", 0.0116),
            ("0.95%", 0.0095),
            ("2.5%", 0.025),
        ]
        
        for input_str, expected in test_cases:
            clean_str = input_str.replace('%', '')
            result = float(clean_str) / 100.0
            assert result == expected