"""
Tests for report generation.
Tests that the Jinja2 template renders without crashing.
"""
import pytest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from src.utils.models import ETFund, IssuerSnapshot, DailySnapshot
from src.reporting.email_service import generate_report


class TestReportGeneration:
    """Test report template rendering."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create sample data
        self.current_snapshot = self._create_sample_snapshot("2026-03-09")
        self.previous_snapshot = self._create_sample_snapshot("2026-03-02")
        self.changelog = self._create_sample_changelog()
    
    def _create_sample_snapshot(self, date: str) -> DailySnapshot:
        """Create a sample snapshot for testing."""
        funds = [
            ETFund(
                ticker="TEST1",
                name="Test Fund One",
                issuer="test-issuer",
                aum=10000000,
                expense_ratio=0.0095,
                div_yield=0.025,
                return_1y=0.15
            ),
            ETFund(
                ticker="TEST2",
                name="Test Fund Two",
                issuer="test-issuer",
                aum=20000000,
                expense_ratio=0.0105,
                div_yield=0.03,
                return_1y=0.20
            ),
        ]
        
        issuer = IssuerSnapshot(
            issuer_slug="test-issuer",
            total_funds=2,
            total_aum=30000000,
            funds=funds
        )
        
        return DailySnapshot(
            date=date,
            issuers={"test-issuer": issuer}
        )
    
    def _create_sample_changelog(self) -> list[dict]:
        """Create sample changelog data."""
        return [
            {
                "date": "2026-03-03",
                "changes": {
                    "launches": [
                        {
                            "ticker": "NEW1",
                            "name": "New Fund One",
                            "issuer": "test-issuer",
                            "date": "2026-03-03",
                            "aum": 5000000
                        }
                    ],
                    "closures": [],
                    "aum_changes": [
                        {
                            "ticker": "TEST1",
                            "issuer": "test-issuer",
                            "prev_aum": 9000000,
                            "current_aum": 10000000,
                            "change": 1000000,
                            "change_pct": 0.1111
                        }
                    ]
                }
            }
        ]
    
    def test_generate_full_report(self):
        """Test generating full report (with fund list)."""
        html = generate_report(
            self.current_snapshot,
            self.previous_snapshot,
            self.changelog,
            is_email_body=False
        )
        
        # Verify HTML was generated
        assert html is not None
        assert len(html) > 0
        
        # Verify key sections are present
        assert "ETF Ticker Scraper Report" in html
        assert "Weekly Activity Log" in html
        assert "New Launches" in html
        assert "Closures & Delistings" in html
        assert "Issuer Scoreboard" in html
        assert "Top AUM Movers" in html
        assert "Fund Count Changes" in html
        assert "Full Fund List" in html  # Should be present in full report
        
        # Verify data is rendered
        assert "TEST1" in html
        assert "TEST2" in html
        assert "test-issuer" in html
    
    def test_generate_email_body(self):
        """Test generating email body (without fund list)."""
        html = generate_report(
            self.current_snapshot,
            self.previous_snapshot,
            self.changelog,
            is_email_body=True
        )
        
        # Verify HTML was generated
        assert html is not None
        assert len(html) > 0
        
        # Verify key sections are present
        assert "ETF Ticker Scraper Report" in html
        assert "Weekly Activity Log" in html
        assert "New Launches" in html
        
        # Verify that the actual fund data rows are not present
        # These classes only appear in the Full Fund List section
        assert 'class="fund-item"' not in html
        assert 'class="fund-ticker"' not in html
    
    def test_report_with_empty_data(self):
        """Test report generation with empty/minimal data."""
        empty_snapshot = DailySnapshot(date="2026-03-09", issuers={})
        empty_changelog = []
        
        # Should not crash with empty data
        html = generate_report(
            empty_snapshot,
            None,  # No previous snapshot
            empty_changelog,
            is_email_body=False
        )
        
        assert html is not None
        assert "ETF Ticker Scraper Report" in html
        assert "No activity recorded this week" in html or "No previous" in html
    
    def test_report_with_launches(self):
        """Test report with launch data."""
        changelog_with_launches = [
            {
                "date": "2026-03-09",
                "changes": {
                    "launches": [
                        {
                            "ticker": "LAUNCH1",
                            "name": "Launch Fund One",
                            "issuer": "test-issuer",
                            "date": "2026-03-09",
                            "aum": 1000000
                        },
                        {
                            "ticker": "LAUNCH2",
                            "name": "Launch Fund Two",
                            "issuer": "test-issuer",
                            "date": "2026-03-09",
                            "aum": 2000000
                        }
                    ],
                    "closures": [],
                    "aum_changes": []
                }
            }
        ]
        
        html = generate_report(
            self.current_snapshot,
            self.previous_snapshot,
            changelog_with_launches,
            is_email_body=False
        )
        
        assert "LAUNCH1" in html
        assert "LAUNCH2" in html
        assert "Launch Fund One" in html
    
    def test_report_with_closures(self):
        """Test report with closure data."""
        changelog_with_closures = [
            {
                "date": "2026-03-09",
                "changes": {
                    "launches": [],
                    "closures": [
                        {
                            "ticker": "CLOSED1",
                            "name": "Closed Fund One",
                            "issuer": "test-issuer",
                            "date": "2026-03-09",
                            "last_aum": 5000000
                        }
                    ],
                    "aum_changes": []
                }
            }
        ]
        
        html = generate_report(
            self.current_snapshot,
            self.previous_snapshot,
            changelog_with_closures,
            is_email_body=False
        )
        
        assert "CLOSED1" in html
        assert "Closed Fund One" in html
    
    def test_report_with_aum_changes(self):
        """Test report with AUM change data."""
        changelog_with_aum = [
            {
                "date": "2026-03-09",
                "changes": {
                    "launches": [],
                    "closures": [],
                    "aum_changes": [
                        {
                            "ticker": "TEST1",
                            "issuer": "test-issuer",
                            "prev_aum": 9000000,
                            "current_aum": 10000000,
                            "change": 1000000,
                            "change_pct": 0.1111
                        }
                    ]
                }
            }
        ]
        
        html = generate_report(
            self.current_snapshot,
            self.previous_snapshot,
            changelog_with_aum,
            is_email_body=False
        )
        
        assert "TEST1" in html
        # Should show positive change
        assert "1,000,000" in html or "1000000" in html
    
    def test_report_html_structure(self):
        """Test that report has valid HTML structure."""
        html = generate_report(
            self.current_snapshot,
            self.previous_snapshot,
            self.changelog,
            is_email_body=False
        )
        
        # Check for basic HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "</head>" in html
        assert "<body>" in html
        assert "</body>" in html
        
        # Check for CSS
        assert "<style>" in html
        assert "</style>" in html
        
        # Check for print CSS
        assert "@media print" in html
    
    def test_report_date_formatting(self):
        """Test that dates are formatted correctly in report."""
        html = generate_report(
            self.current_snapshot,
            self.previous_snapshot,
            self.changelog,
            is_email_body=False
        )
        
        # Check that date appears in report
        assert "2026-03-09" in html
        
        # Check for week number
        assert "Week" in html
    
    def test_report_number_formatting(self):
        """Test that numbers are formatted correctly in report."""
        html = generate_report(
            self.current_snapshot,
            self.previous_snapshot,
            self.changelog,
            is_email_body=False
        )
        
        # AUM should be formatted with commas
        # 10,000,000 or 20,000,000 should appear
        assert "10,000,000" in html or "20,000,000" in html
        
        # Percentages should be formatted
        assert "%" in html


class TestTemplateExists:
    """Test that template file exists and is valid."""
    
    def test_template_file_exists(self):
        """Test that report.html template exists."""
        from src.utils.config import BASE_DIR
        template_path = BASE_DIR / "src" / "reporting" / "templates" / "report.html"
        assert template_path.exists(), f"Template not found at {template_path}"
    
    def test_template_loads(self):
        """Test that template can be loaded by Jinja2."""
        from src.utils.config import BASE_DIR
        template_dir = BASE_DIR / "src" / "reporting" / "templates"
        env = Environment(loader=FileSystemLoader(template_dir))
        
        # Should not raise an exception
        template = env.get_template("report.html")
        assert template is not None