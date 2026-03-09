"""
Data models for ETF scraper using Python dataclasses.
Defines structures for ETF funds, issuer snapshots, and daily snapshots.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class ETFund:
    """Represents a single ETF with its key metrics."""
    ticker: str
    name: str
    issuer: str
    aum: Optional[int] = None  # Assets under management in dollars
    expense_ratio: Optional[float] = None  # As decimal (e.g., 0.0101 for 1.01%)
    div_yield: Optional[float] = None  # Dividend yield as decimal
    return_1y: Optional[float] = None  # 1-year return as decimal
    nav: Optional[float] = None  # Net asset value
    volume: Optional[int] = None  # Trading volume
    inception_date: Optional[str] = None  # Format: "YYYY-MM-DD"
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_dict(self) -> dict:
        """Convert ETFund to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ETFund':
        """Create ETFund instance from dictionary."""
        return cls(**data)


@dataclass
class IssuerSnapshot:
    """Represents all ETFs for a single issuer at a point in time."""
    issuer_slug: str
    total_funds: int
    total_aum: int  # Sum of all fund AUMs
    funds: list[ETFund] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert IssuerSnapshot to dictionary for JSON serialization."""
        return {
            "issuer_slug": self.issuer_slug,
            "total_funds": self.total_funds,
            "total_aum": self.total_aum,
            "funds": [fund.to_dict() for fund in self.funds]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'IssuerSnapshot':
        """Create IssuerSnapshot instance from dictionary."""
        funds = [ETFund.from_dict(fund_data) for fund_data in data.get("funds", [])]
        return cls(
            issuer_slug=data["issuer_slug"],
            total_funds=data["total_funds"],
            total_aum=data["total_aum"],
            funds=funds
        )


@dataclass
class DailySnapshot:
    """Represents a complete snapshot of all issuers for a single day."""
    date: str  # Format: "YYYY-MM-DD"
    issuers: dict[str, IssuerSnapshot] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert DailySnapshot to dictionary for JSON serialization."""
        return {
            "date": self.date,
            "issuers": {
                slug: issuer.to_dict() 
                for slug, issuer in self.issuers.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DailySnapshot':
        """Create DailySnapshot instance from dictionary."""
        issuers = {
            slug: IssuerSnapshot.from_dict(issuer_data)
            for slug, issuer_data in data.get("issuers", {}).items()
        }
        return cls(
            date=data["date"],
            issuers=issuers
        )