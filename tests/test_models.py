"""
Tests for data models.
Tests serialization/deserialization (to_dict/from_dict) round-trips.
"""
import pytest
from datetime import datetime
from src.utils.models import ETFund, IssuerSnapshot, DailySnapshot


class TestETFundModel:
    """Test ETFund model serialization."""
    
    def test_etfund_to_dict(self):
        """Test ETFund to_dict conversion."""
        fund = ETFund(
            ticker="TEST",
            name="Test Fund",
            issuer="test-issuer",
            aum=1000000,
            expense_ratio=0.0095,
            div_yield=0.025,
            return_1y=0.15,
            nav=25.50,
            volume=100000,
            inception_date="2025-01-01"
        )
        
        fund_dict = fund.to_dict()
        
        assert fund_dict["ticker"] == "TEST"
        assert fund_dict["name"] == "Test Fund"
        assert fund_dict["issuer"] == "test-issuer"
        assert fund_dict["aum"] == 1000000
        assert fund_dict["expense_ratio"] == 0.0095
        assert fund_dict["div_yield"] == 0.025
        assert fund_dict["return_1y"] == 0.15
        assert fund_dict["nav"] == 25.50
        assert fund_dict["volume"] == 100000
        assert fund_dict["inception_date"] == "2025-01-01"
        assert "scraped_at" in fund_dict
    
    def test_etfund_from_dict(self):
        """Test ETFund from_dict conversion."""
        fund_dict = {
            "ticker": "TEST",
            "name": "Test Fund",
            "issuer": "test-issuer",
            "aum": 1000000,
            "expense_ratio": 0.0095,
            "div_yield": 0.025,
            "return_1y": 0.15,
            "nav": 25.50,
            "volume": 100000,
            "inception_date": "2025-01-01",
            "scraped_at": "2026-03-09T12:00:00Z"
        }
        
        fund = ETFund.from_dict(fund_dict)
        
        assert fund.ticker == "TEST"
        assert fund.name == "Test Fund"
        assert fund.issuer == "test-issuer"
        assert fund.aum == 1000000
        assert fund.expense_ratio == 0.0095
        assert fund.div_yield == 0.025
        assert fund.return_1y == 0.15
        assert fund.nav == 25.50
        assert fund.volume == 100000
        assert fund.inception_date == "2025-01-01"
        assert fund.scraped_at == "2026-03-09T12:00:00Z"
    
    def test_etfund_roundtrip(self):
        """Test ETFund to_dict -> from_dict round-trip."""
        original = ETFund(
            ticker="ROUND",
            name="Round Trip Fund",
            issuer="test",
            aum=5000000,
            expense_ratio=0.01,
            div_yield=0.03,
            return_1y=0.20,
            nav=50.00,
            volume=250000,
            inception_date="2024-06-15"
        )
        
        # Convert to dict and back
        fund_dict = original.to_dict()
        restored = ETFund.from_dict(fund_dict)
        
        # Verify all fields match
        assert restored.ticker == original.ticker
        assert restored.name == original.name
        assert restored.issuer == original.issuer
        assert restored.aum == original.aum
        assert restored.expense_ratio == original.expense_ratio
        assert restored.div_yield == original.div_yield
        assert restored.return_1y == original.return_1y
        assert restored.nav == original.nav
        assert restored.volume == original.volume
        assert restored.inception_date == original.inception_date
        assert restored.scraped_at == original.scraped_at
    
    def test_etfund_with_none_values(self):
        """Test ETFund with None values (common for missing data)."""
        fund = ETFund(
            ticker="NONE",
            name="Fund with Missing Data",
            issuer="test",
            aum=None,
            expense_ratio=None,
            div_yield=None,
            return_1y=None,
            nav=None,
            volume=None,
            inception_date=None
        )
        
        # Round-trip
        fund_dict = fund.to_dict()
        restored = ETFund.from_dict(fund_dict)
        
        assert restored.ticker == "NONE"
        assert restored.aum is None
        assert restored.expense_ratio is None
        assert restored.div_yield is None


class TestIssuerSnapshotModel:
    """Test IssuerSnapshot model serialization."""
    
    def test_issuer_snapshot_to_dict(self):
        """Test IssuerSnapshot to_dict conversion."""
        funds = [
            ETFund(ticker="FUND1", name="Fund One", issuer="test", aum=1000000),
            ETFund(ticker="FUND2", name="Fund Two", issuer="test", aum=2000000),
        ]
        
        snapshot = IssuerSnapshot(
            issuer_slug="test",
            total_funds=2,
            total_aum=3000000,
            funds=funds
        )
        
        snapshot_dict = snapshot.to_dict()
        
        assert snapshot_dict["issuer_slug"] == "test"
        assert snapshot_dict["total_funds"] == 2
        assert snapshot_dict["total_aum"] == 3000000
        assert len(snapshot_dict["funds"]) == 2
        assert snapshot_dict["funds"][0]["ticker"] == "FUND1"
        assert snapshot_dict["funds"][1]["ticker"] == "FUND2"
    
    def test_issuer_snapshot_from_dict(self):
        """Test IssuerSnapshot from_dict conversion."""
        snapshot_dict = {
            "issuer_slug": "test",
            "total_funds": 2,
            "total_aum": 3000000,
            "funds": [
                {
                    "ticker": "FUND1",
                    "name": "Fund One",
                    "issuer": "test",
                    "aum": 1000000,
                    "expense_ratio": None,
                    "div_yield": None,
                    "return_1y": None,
                    "nav": None,
                    "volume": None,
                    "inception_date": None,
                    "scraped_at": "2026-03-09T12:00:00Z"
                },
                {
                    "ticker": "FUND2",
                    "name": "Fund Two",
                    "issuer": "test",
                    "aum": 2000000,
                    "expense_ratio": None,
                    "div_yield": None,
                    "return_1y": None,
                    "nav": None,
                    "volume": None,
                    "inception_date": None,
                    "scraped_at": "2026-03-09T12:00:00Z"
                }
            ]
        }
        
        snapshot = IssuerSnapshot.from_dict(snapshot_dict)
        
        assert snapshot.issuer_slug == "test"
        assert snapshot.total_funds == 2
        assert snapshot.total_aum == 3000000
        assert len(snapshot.funds) == 2
        assert snapshot.funds[0].ticker == "FUND1"
        assert snapshot.funds[1].ticker == "FUND2"
    
    def test_issuer_snapshot_roundtrip(self):
        """Test IssuerSnapshot to_dict -> from_dict round-trip."""
        original = IssuerSnapshot(
            issuer_slug="roundtrip",
            total_funds=3,
            total_aum=10000000,
            funds=[
                ETFund(ticker="A", name="Fund A", issuer="roundtrip", aum=3000000),
                ETFund(ticker="B", name="Fund B", issuer="roundtrip", aum=4000000),
                ETFund(ticker="C", name="Fund C", issuer="roundtrip", aum=3000000),
            ]
        )
        
        # Round-trip
        snapshot_dict = original.to_dict()
        restored = IssuerSnapshot.from_dict(snapshot_dict)
        
        assert restored.issuer_slug == original.issuer_slug
        assert restored.total_funds == original.total_funds
        assert restored.total_aum == original.total_aum
        assert len(restored.funds) == len(original.funds)
        
        for i, fund in enumerate(restored.funds):
            assert fund.ticker == original.funds[i].ticker
            assert fund.name == original.funds[i].name
            assert fund.aum == original.funds[i].aum


class TestDailySnapshotModel:
    """Test DailySnapshot model serialization."""
    
    def test_daily_snapshot_to_dict(self):
        """Test DailySnapshot to_dict conversion."""
        issuer1 = IssuerSnapshot(
            issuer_slug="issuer1",
            total_funds=1,
            total_aum=1000000,
            funds=[ETFund(ticker="FUND1", name="Fund One", issuer="issuer1", aum=1000000)]
        )
        issuer2 = IssuerSnapshot(
            issuer_slug="issuer2",
            total_funds=1,
            total_aum=2000000,
            funds=[ETFund(ticker="FUND2", name="Fund Two", issuer="issuer2", aum=2000000)]
        )
        
        snapshot = DailySnapshot(
            date="2026-03-09",
            issuers={"issuer1": issuer1, "issuer2": issuer2}
        )
        
        snapshot_dict = snapshot.to_dict()
        
        assert snapshot_dict["date"] == "2026-03-09"
        assert "issuer1" in snapshot_dict["issuers"]
        assert "issuer2" in snapshot_dict["issuers"]
        assert snapshot_dict["issuers"]["issuer1"]["total_funds"] == 1
        assert snapshot_dict["issuers"]["issuer2"]["total_funds"] == 1
    
    def test_daily_snapshot_from_dict(self):
        """Test DailySnapshot from_dict conversion."""
        snapshot_dict = {
            "date": "2026-03-09",
            "issuers": {
                "issuer1": {
                    "issuer_slug": "issuer1",
                    "total_funds": 1,
                    "total_aum": 1000000,
                    "funds": [
                        {
                            "ticker": "FUND1",
                            "name": "Fund One",
                            "issuer": "issuer1",
                            "aum": 1000000,
                            "expense_ratio": None,
                            "div_yield": None,
                            "return_1y": None,
                            "nav": None,
                            "volume": None,
                            "inception_date": None,
                            "scraped_at": "2026-03-09T12:00:00Z"
                        }
                    ]
                }
            }
        }
        
        snapshot = DailySnapshot.from_dict(snapshot_dict)
        
        assert snapshot.date == "2026-03-09"
        assert "issuer1" in snapshot.issuers
        assert snapshot.issuers["issuer1"].total_funds == 1
        assert snapshot.issuers["issuer1"].funds[0].ticker == "FUND1"
    
    def test_daily_snapshot_roundtrip(self):
        """Test DailySnapshot to_dict -> from_dict round-trip."""
        original = DailySnapshot(
            date="2026-03-09",
            issuers={
                "test": IssuerSnapshot(
                    issuer_slug="test",
                    total_funds=2,
                    total_aum=5000000,
                    funds=[
                        ETFund(ticker="X", name="Fund X", issuer="test", aum=2000000),
                        ETFund(ticker="Y", name="Fund Y", issuer="test", aum=3000000),
                    ]
                )
            }
        )
        
        # Round-trip
        snapshot_dict = original.to_dict()
        restored = DailySnapshot.from_dict(snapshot_dict)
        
        assert restored.date == original.date
        assert len(restored.issuers) == len(original.issuers)
        assert "test" in restored.issuers
        assert restored.issuers["test"].total_funds == original.issuers["test"].total_funds
        assert len(restored.issuers["test"].funds) == len(original.issuers["test"].funds)