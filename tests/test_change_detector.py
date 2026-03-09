"""
Tests for change detection logic.
Tests detection of launches, closures, and AUM changes between snapshots.
"""
import pytest
from src.utils.models import ETFund, IssuerSnapshot, DailySnapshot
from src.detection.change_detector import detect_changes


class TestChangeDetection:
    """Test change detection between snapshots."""
    
    def test_detect_launches(self):
        """Test detection of new fund launches."""
        # Previous snapshot with 2 funds
        prev_funds = [
            ETFund(ticker="FUND1", name="Fund One", issuer="test", aum=1000000),
            ETFund(ticker="FUND2", name="Fund Two", issuer="test", aum=2000000),
        ]
        prev_issuer = IssuerSnapshot(
            issuer_slug="test",
            total_funds=2,
            total_aum=3000000,
            funds=prev_funds
        )
        prev_snapshot = DailySnapshot(
            date="2026-03-01",
            issuers={"test": prev_issuer}
        )
        
        # Current snapshot with 3 funds (FUND3 is new)
        curr_funds = [
            ETFund(ticker="FUND1", name="Fund One", issuer="test", aum=1000000),
            ETFund(ticker="FUND2", name="Fund Two", issuer="test", aum=2000000),
            ETFund(ticker="FUND3", name="Fund Three", issuer="test", aum=500000),
        ]
        curr_issuer = IssuerSnapshot(
            issuer_slug="test",
            total_funds=3,
            total_aum=3500000,
            funds=curr_funds
        )
        curr_snapshot = DailySnapshot(
            date="2026-03-02",
            issuers={"test": curr_issuer}
        )
        
        # Detect changes
        changes = detect_changes(curr_snapshot, prev_snapshot)
        
        # Verify launch detected
        assert len(changes["launches"]) == 1
        assert changes["launches"][0]["ticker"] == "FUND3"
        assert changes["launches"][0]["issuer"] == "test"
        assert changes["launches"][0]["aum"] == 500000
    
    def test_detect_closures(self):
        """Test detection of fund closures."""
        # Previous snapshot with 3 funds
        prev_funds = [
            ETFund(ticker="FUND1", name="Fund One", issuer="test", aum=1000000),
            ETFund(ticker="FUND2", name="Fund Two", issuer="test", aum=2000000),
            ETFund(ticker="FUND3", name="Fund Three", issuer="test", aum=500000),
        ]
        prev_issuer = IssuerSnapshot(
            issuer_slug="test",
            total_funds=3,
            total_aum=3500000,
            funds=prev_funds
        )
        prev_snapshot = DailySnapshot(
            date="2026-03-01",
            issuers={"test": prev_issuer}
        )
        
        # Current snapshot with 2 funds (FUND3 closed)
        curr_funds = [
            ETFund(ticker="FUND1", name="Fund One", issuer="test", aum=1000000),
            ETFund(ticker="FUND2", name="Fund Two", issuer="test", aum=2000000),
        ]
        curr_issuer = IssuerSnapshot(
            issuer_slug="test",
            total_funds=2,
            total_aum=3000000,
            funds=curr_funds
        )
        curr_snapshot = DailySnapshot(
            date="2026-03-02",
            issuers={"test": curr_issuer}
        )
        
        # Detect changes
        changes = detect_changes(curr_snapshot, prev_snapshot)
        
        # Verify closure detected
        assert len(changes["closures"]) == 1
        assert changes["closures"][0]["ticker"] == "FUND3"
        assert changes["closures"][0]["issuer"] == "test"
        assert changes["closures"][0]["last_aum"] == 500000
    
    def test_detect_aum_changes(self):
        """Test detection of AUM changes."""
        # Previous snapshot
        prev_funds = [
            ETFund(ticker="FUND1", name="Fund One", issuer="test", aum=1000000),
            ETFund(ticker="FUND2", name="Fund Two", issuer="test", aum=2000000),
        ]
        prev_issuer = IssuerSnapshot(
            issuer_slug="test",
            total_funds=2,
            total_aum=3000000,
            funds=prev_funds
        )
        prev_snapshot = DailySnapshot(
            date="2026-03-01",
            issuers={"test": prev_issuer}
        )
        
        # Current snapshot with AUM changes
        curr_funds = [
            ETFund(ticker="FUND1", name="Fund One", issuer="test", aum=1500000),  # +500k
            ETFund(ticker="FUND2", name="Fund Two", issuer="test", aum=1800000),  # -200k
        ]
        curr_issuer = IssuerSnapshot(
            issuer_slug="test",
            total_funds=2,
            total_aum=3300000,
            funds=curr_funds
        )
        curr_snapshot = DailySnapshot(
            date="2026-03-02",
            issuers={"test": curr_issuer}
        )
        
        # Detect changes
        changes = detect_changes(curr_snapshot, prev_snapshot)
        
        # Verify AUM changes detected
        assert len(changes["aum_changes"]) == 2
        
        # Check FUND1 increase
        fund1_change = next(c for c in changes["aum_changes"] if c["ticker"] == "FUND1")
        assert fund1_change["prev_aum"] == 1000000
        assert fund1_change["current_aum"] == 1500000
        assert fund1_change["change"] == 500000
        assert fund1_change["change_pct"] == 0.5
        
        # Check FUND2 decrease
        fund2_change = next(c for c in changes["aum_changes"] if c["ticker"] == "FUND2")
        assert fund2_change["prev_aum"] == 2000000
        assert fund2_change["current_aum"] == 1800000
        assert fund2_change["change"] == -200000
        assert fund2_change["change_pct"] == -0.1
    
    def test_no_changes(self):
        """Test when there are no changes between snapshots."""
        # Identical snapshots
        funds = [
            ETFund(ticker="FUND1", name="Fund One", issuer="test", aum=1000000),
            ETFund(ticker="FUND2", name="Fund Two", issuer="test", aum=2000000),
        ]
        issuer = IssuerSnapshot(
            issuer_slug="test",
            total_funds=2,
            total_aum=3000000,
            funds=funds
        )
        
        prev_snapshot = DailySnapshot(date="2026-03-01", issuers={"test": issuer})
        curr_snapshot = DailySnapshot(date="2026-03-02", issuers={"test": issuer})
        
        # Detect changes
        changes = detect_changes(curr_snapshot, prev_snapshot)
        
        # Verify no changes
        assert len(changes["launches"]) == 0
        assert len(changes["closures"]) == 0
        assert len(changes["aum_changes"]) == 0
    
    def test_multiple_issuers(self):
        """Test change detection across multiple issuers."""
        # Previous snapshot with 2 issuers
        prev_issuer1 = IssuerSnapshot(
            issuer_slug="issuer1",
            total_funds=1,
            total_aum=1000000,
            funds=[ETFund(ticker="FUND1", name="Fund One", issuer="issuer1", aum=1000000)]
        )
        prev_issuer2 = IssuerSnapshot(
            issuer_slug="issuer2",
            total_funds=1,
            total_aum=2000000,
            funds=[ETFund(ticker="FUND2", name="Fund Two", issuer="issuer2", aum=2000000)]
        )
        prev_snapshot = DailySnapshot(
            date="2026-03-01",
            issuers={"issuer1": prev_issuer1, "issuer2": prev_issuer2}
        )
        
        # Current snapshot with changes in both issuers
        curr_issuer1 = IssuerSnapshot(
            issuer_slug="issuer1",
            total_funds=2,
            total_aum=1500000,
            funds=[
                ETFund(ticker="FUND1", name="Fund One", issuer="issuer1", aum=1000000),
                ETFund(ticker="FUND3", name="Fund Three", issuer="issuer1", aum=500000),  # New
            ]
        )
        curr_issuer2 = IssuerSnapshot(
            issuer_slug="issuer2",
            total_funds=1,
            total_aum=2500000,
            funds=[ETFund(ticker="FUND2", name="Fund Two", issuer="issuer2", aum=2500000)]  # AUM change
        )
        curr_snapshot = DailySnapshot(
            date="2026-03-02",
            issuers={"issuer1": curr_issuer1, "issuer2": curr_issuer2}
        )
        
        # Detect changes
        changes = detect_changes(curr_snapshot, prev_snapshot)
        
        # Verify changes across issuers
        assert len(changes["launches"]) == 1
        assert changes["launches"][0]["issuer"] == "issuer1"
        
        assert len(changes["aum_changes"]) == 1
        assert changes["aum_changes"][0]["issuer"] == "issuer2"
        assert changes["aum_changes"][0]["change"] == 500000
    
    def test_ignore_none_aum_values(self):
        """Test that None AUM values are ignored in change detection."""
        # Previous snapshot
        prev_funds = [
            ETFund(ticker="FUND1", name="Fund One", issuer="test", aum=1000000),
        ]
        prev_issuer = IssuerSnapshot(
            issuer_slug="test",
            total_funds=1,
            total_aum=1000000,
            funds=prev_funds
        )
        prev_snapshot = DailySnapshot(
            date="2026-03-01",
            issuers={"test": prev_issuer}
        )
        
        # Current snapshot with None AUM
        curr_funds = [
            ETFund(ticker="FUND1", name="Fund One", issuer="test", aum=None),
        ]
        curr_issuer = IssuerSnapshot(
            issuer_slug="test",
            total_funds=1,
            total_aum=0,
            funds=curr_funds
        )
        curr_snapshot = DailySnapshot(
            date="2026-03-02",
            issuers={"test": curr_issuer}
        )
        
        # Detect changes
        changes = detect_changes(curr_snapshot, prev_snapshot)
        
        # Verify no AUM change detected (None values ignored)
        assert len(changes["aum_changes"]) == 0