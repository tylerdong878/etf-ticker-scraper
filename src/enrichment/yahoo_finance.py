"""
Yahoo Finance enrichment for ETF data.
Uses yfinance to fetch NAV, volume, and inception date for ETFs.
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yfinance as yf

from ..utils.models import ETFund
from ..utils.config import CACHE_DIR
from ..utils.logger import get_logger

logger = get_logger(__name__)


def _get_cache_filepath() -> Path:
    """Get the cache filepath for today's date."""
    today = datetime.now().strftime("%Y-%m-%d")
    return CACHE_DIR / f"yfinance_{today}.json"


def _load_cache() -> dict:
    """Load today's yfinance cache if it exists."""
    cache_file = _get_cache_filepath()
    
    if not cache_file.exists():
        return {}
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        logger.debug(f"Loaded yfinance cache with {len(cache)} entries")
        return cache
    except Exception as e:
        logger.warning(f"Failed to load yfinance cache: {e}")
        return {}


def _save_cache(cache: dict) -> None:
    """Save the yfinance cache to disk."""
    cache_file = _get_cache_filepath()
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved yfinance cache with {len(cache)} entries")
    except Exception as e:
        logger.warning(f"Failed to save yfinance cache: {e}")


def _parse_inception_date(date_value) -> Optional[str]:
    """
    Parse inception date from yfinance to YYYY-MM-DD format.
    
    Args:
        date_value: Can be timestamp, string, or None
    
    Returns:
        Date string in YYYY-MM-DD format, or None
    """
    if date_value is None:
        return None
    
    try:
        # If it's a timestamp (int), convert to datetime
        if isinstance(date_value, (int, float)):
            date_obj = datetime.fromtimestamp(date_value)
            return date_obj.strftime("%Y-%m-%d")
        
        # If it's already a string, try to parse it
        if isinstance(date_value, str):
            # Try common formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"]:
                try:
                    date_obj = datetime.strptime(date_value, fmt)
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        
        # If it's a datetime object (check type to satisfy type checker)
        from datetime import datetime as dt_type
        if isinstance(date_value, dt_type):
            return date_value.strftime("%Y-%m-%d")
        
        return None
        
    except Exception as e:
        logger.debug(f"Could not parse inception date {date_value}: {e}")
        return None


def _fetch_ticker_data(ticker: str) -> dict:
    """
    Fetch data for a single ticker from yfinance.
    
    Args:
        ticker: ETF ticker symbol
    
    Returns:
        Dictionary with nav, volume, inception_date (or None values if not available)
    """
    try:
        # Create yfinance Ticker object
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
        
        # Extract NAV (net asset value / price)
        nav = info.get('regularMarketPrice') or info.get('navPrice')
        
        # Extract volume
        volume = info.get('averageVolume') or info.get('volume')
        
        # Extract inception date
        inception_raw = info.get('fundInceptionDate')
        inception_date = _parse_inception_date(inception_raw)
        
        # Extract total assets (AUM)
        total_assets = info.get('totalAssets')

        # Extract expense ratio (returned as decimal, e.g. 0.0095 for 0.95%)
        expense_ratio = info.get('annualReportExpenseRatio') or info.get('expenseRatio')

        return {
            "nav": nav,
            "volume": volume,
            "inception_date": inception_date,
            "total_assets": total_assets,
            "expense_ratio": expense_ratio
        }

    except Exception as e:
        logger.debug(f"Failed to fetch data for {ticker}: {e}")
        return {
            "nav": None,
            "volume": None,
            "inception_date": None,
            "total_assets": None
        }


def enrich_funds(funds: list[ETFund]) -> list[ETFund]:
    """
    Enrich a list of ETFund objects with data from Yahoo Finance.
    
    Fetches NAV, volume, and inception date for each fund.
    Uses daily caching to avoid redundant API calls.
    
    Args:
        funds: List of ETFund objects to enrich
    
    Returns:
        The same list of ETFund objects, enriched with yfinance data
    """
    logger.info(f"Starting yfinance enrichment for {len(funds)} funds")
    
    # Load cache
    cache = _load_cache()
    
    # Track statistics
    success_count = 0
    cached_count = 0
    failed_count = 0
    
    for i, fund in enumerate(funds, 1):
        ticker = fund.ticker
        
        # Check cache first
        if ticker in cache:
            cached_data = cache[ticker]
            fund.nav = cached_data.get("nav")
            fund.volume = cached_data.get("volume")
            fund.inception_date = cached_data.get("inception_date")
            fund.expense_ratio = cached_data.get("expense_ratio")
            if not fund.aum:
                total_assets = cached_data.get("total_assets")
                if total_assets:
                    fund.aum = total_assets
                    logger.debug(f"Filled AUM for {ticker} from cache: {total_assets}")
            cached_count += 1
            logger.debug(f"[{i}/{len(funds)}] Using cached data for {ticker}")
            continue
        
        # Fetch from yfinance
        logger.debug(f"[{i}/{len(funds)}] Fetching data for {ticker}")
        data = _fetch_ticker_data(ticker)
        
        # Update fund object
        fund.nav = data["nav"]
        fund.volume = data["volume"]
        fund.inception_date = data["inception_date"]
        fund.expense_ratio = data.get("expense_ratio")
        if not fund.aum:
            total_assets = data.get("total_assets")
            if total_assets:
                fund.aum = total_assets
                logger.debug(f"Filled AUM for {ticker} from yfinance: {total_assets}")
        
        # Cache the result
        cache[ticker] = data
        
        # Track success/failure
        if data["nav"] is not None or data["volume"] is not None:
            success_count += 1
        else:
            failed_count += 1
            logger.warning(f"No yfinance data available for {ticker}")
        
        # Rate limiting: sleep between requests (except for last one)
        if i < len(funds):
            time.sleep(0.5)
    
    # Save updated cache
    _save_cache(cache)
    
    # Log summary
    logger.info(
        f"Enriched {len(funds)} funds: "
        f"{success_count} success, {cached_count} cached, {failed_count} failed"
    )
    
    return funds