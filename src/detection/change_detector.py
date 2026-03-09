"""
Change detector for comparing daily ETF snapshots.
Identifies launches, closures, and AUM changes between snapshots.
"""
import json
from datetime import datetime
from typing import Optional

from ..utils.models import DailySnapshot, ETFund
from ..utils.config import CHANGELOG_DIR
from ..utils.logger import get_logger
from .snapshot_manager import get_snapshot_history

logger = get_logger(__name__)


def detect_changes(current: DailySnapshot, previous: DailySnapshot) -> dict:
    """
    Compare two snapshots to detect launches, closures, and AUM changes.
    
    Args:
        current: Current day's snapshot
        previous: Previous day's snapshot
    
    Returns:
        Dictionary with keys: launches, closures, aum_changes
    """
    logger.info(f"Detecting changes between {previous.date} and {current.date}")
    
    launches = []
    closures = []
    aum_changes = []
    
    # Get all issuers from both snapshots
    all_issuers = set(current.issuers.keys()) | set(previous.issuers.keys())
    
    for issuer_slug in all_issuers:
        current_issuer = current.issuers.get(issuer_slug)
        previous_issuer = previous.issuers.get(issuer_slug)
        
        # Skip if issuer doesn't exist in one of the snapshots
        if not current_issuer or not previous_issuer:
            continue
        
        # Build ticker-to-fund mappings for easy lookup
        current_funds = {fund.ticker: fund for fund in current_issuer.funds}
        previous_funds = {fund.ticker: fund for fund in previous_issuer.funds}
        
        # Detect launches (in current but not in previous)
        for ticker, fund in current_funds.items():
            if ticker not in previous_funds:
                launches.append({
                    "ticker": ticker,
                    "name": fund.name,
                    "issuer": issuer_slug,
                    "date": current.date,
                    "aum": fund.aum
                })
                logger.info(f"Launch detected: {ticker} ({issuer_slug})")
        
        # Detect closures (in previous but not in current)
        for ticker, fund in previous_funds.items():
            if ticker not in current_funds:
                closures.append({
                    "ticker": ticker,
                    "name": fund.name,
                    "issuer": issuer_slug,
                    "date": current.date,
                    "last_aum": fund.aum
                })
                logger.info(f"Closure detected: {ticker} ({issuer_slug})")
        
        # Detect AUM changes (same ticker, different AUM)
        for ticker in current_funds.keys() & previous_funds.keys():
            current_fund = current_funds[ticker]
            previous_fund = previous_funds[ticker]
            
            # Only track if both have AUM values and they differ
            if (current_fund.aum is not None and 
                previous_fund.aum is not None and 
                current_fund.aum != previous_fund.aum):
                
                change = current_fund.aum - previous_fund.aum
                change_pct = change / previous_fund.aum if previous_fund.aum != 0 else 0
                
                aum_changes.append({
                    "ticker": ticker,
                    "issuer": issuer_slug,
                    "prev_aum": previous_fund.aum,
                    "current_aum": current_fund.aum,
                    "change": change,
                    "change_pct": change_pct
                })
    
    logger.info(f"Changes detected: {len(launches)} launches, {len(closures)} closures, {len(aum_changes)} AUM changes")
    
    return {
        "launches": launches,
        "closures": closures,
        "aum_changes": aum_changes
    }


def append_to_changelog(changes: dict, date: str) -> None:
    """
    Append daily changes to the weekly changelog file.
    
    Args:
        changes: Dictionary with launches, closures, aum_changes
        date: Date string in format "YYYY-MM-DD"
    """
    try:
        # Parse date and determine ISO week (e.g., "2026-W10")
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        iso_year, iso_week, _ = date_obj.isocalendar()
        week_str = f"{iso_year}-W{iso_week:02d}"
        
        filepath = CHANGELOG_DIR / f"{week_str}.json"
        
        # Load existing changelog if it exists
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                changelog = json.load(f)
        else:
            changelog = []
        
        # Create entry for this day
        entry = {
            "date": date,
            "changes": changes
        }
        
        # Append to changelog
        changelog.append(entry)
        
        # Save back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(changelog, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Appended changes to changelog: {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to append to changelog for {date}: {e}")
        raise


def load_weekly_changelog(week: str) -> list[dict]:
    """
    Load all daily entries for a given ISO week.
    
    Args:
        week: ISO week string in format "YYYY-WNN" (e.g., "2026-W10")
    
    Returns:
        List of daily change entries, or empty list if file doesn't exist
    """
    filepath = CHANGELOG_DIR / f"{week}.json"
    
    if not filepath.exists():
        logger.debug(f"No changelog found for week {week}")
        return []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            changelog = json.load(f)
        
        logger.info(f"Loaded changelog for week {week}: {len(changelog)} entries")
        return changelog
        
    except Exception as e:
        logger.error(f"Failed to load changelog for week {week}: {e}")
        return []


def is_confirmed_closure(ticker: str, issuer: str, days_missing: int = 2) -> bool:
    """
    Check if a ticker has been missing for multiple consecutive days.
    This prevents false positives from one-off scrape failures.
    
    Args:
        ticker: ETF ticker symbol
        issuer: Issuer slug
        days_missing: Number of consecutive days ticker must be missing (default: 2)
    
    Returns:
        True if ticker has been missing for days_missing consecutive snapshots
    """
    try:
        # Load recent snapshot history
        snapshots = get_snapshot_history(days=days_missing + 1)
        
        if len(snapshots) < days_missing:
            logger.debug(f"Not enough history to confirm closure for {ticker}")
            return False
        
        # Check the last N snapshots (excluding the most recent one we're analyzing)
        # We want to see if it was missing in the previous N days
        recent_snapshots = snapshots[-(days_missing + 1):-1]
        
        missing_count = 0
        for snapshot in recent_snapshots:
            issuer_snapshot = snapshot.issuers.get(issuer)
            if not issuer_snapshot:
                continue
            
            # Check if ticker exists in this snapshot
            ticker_found = any(fund.ticker == ticker for fund in issuer_snapshot.funds)
            
            if not ticker_found:
                missing_count += 1
            else:
                # If we find it in any snapshot, it's not a confirmed closure
                logger.debug(f"{ticker} found in snapshot {snapshot.date}, not a confirmed closure")
                return False
        
        # Confirmed closure if missing for all required days
        is_confirmed = missing_count >= days_missing
        
        if is_confirmed:
            logger.info(f"Confirmed closure: {ticker} ({issuer}) missing for {missing_count} consecutive days")
        
        return is_confirmed
        
    except Exception as e:
        logger.error(f"Failed to check closure confirmation for {ticker}: {e}")
        return False


def filter_confirmed_closures(closures: list[dict], days_missing: int = 2) -> list[dict]:
    """
    Filter closure list to only include confirmed closures.
    
    Args:
        closures: List of closure dictionaries from detect_changes
        days_missing: Number of consecutive days required for confirmation
    
    Returns:
        Filtered list of confirmed closures
    """
    confirmed = []
    
    for closure in closures:
        if is_confirmed_closure(closure["ticker"], closure["issuer"], days_missing):
            confirmed.append(closure)
    
    logger.info(f"Confirmed {len(confirmed)} of {len(closures)} potential closures")
    return confirmed