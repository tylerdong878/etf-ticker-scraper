"""
Snapshot manager for saving and loading daily ETF snapshots.
Handles serialization, file I/O, and snapshot history management.
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from ..utils.models import DailySnapshot
from ..utils.config import SNAPSHOTS_DIR
from ..utils.logger import get_logger

logger = get_logger(__name__)


def save_snapshot(snapshot: DailySnapshot) -> None:
    """
    Save a daily snapshot to JSON file.
    
    Args:
        snapshot: DailySnapshot to save
    """
    filepath = SNAPSHOTS_DIR / f"{snapshot.date}.json"
    
    try:
        # Serialize to dict using the model's to_dict method
        data = snapshot.to_dict()
        
        # Save with pretty-printing for readability
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved snapshot to {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save snapshot for {snapshot.date}: {e}")
        raise


def load_snapshot(date: str) -> Optional[DailySnapshot]:
    """
    Load a daily snapshot from JSON file.
    
    Args:
        date: Date string in format "YYYY-MM-DD"
    
    Returns:
        DailySnapshot if file exists, None otherwise
    """
    filepath = SNAPSHOTS_DIR / f"{date}.json"
    
    if not filepath.exists():
        logger.debug(f"No snapshot found for {date}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Deserialize using the model's from_dict method
        snapshot = DailySnapshot.from_dict(data)
        logger.info(f"Loaded snapshot from {filepath}")
        return snapshot
        
    except Exception as e:
        logger.error(f"Failed to load snapshot for {date}: {e}")
        return None


def load_latest_snapshot() -> Optional[DailySnapshot]:
    """
    Load the most recent snapshot by finding the latest .json file.
    
    Returns:
        DailySnapshot if any snapshots exist, None if this is the first run
    """
    try:
        # Get all .json files in snapshots directory
        snapshot_files = list(SNAPSHOTS_DIR.glob("*.json"))
        
        if not snapshot_files:
            logger.info("No previous snapshots found (first run)")
            return None
        
        # Sort by filename (which is the date in YYYY-MM-DD format)
        # This naturally sorts chronologically
        latest_file = sorted(snapshot_files)[-1]
        
        # Extract date from filename
        date = latest_file.stem  # Gets filename without .json extension
        
        logger.info(f"Found latest snapshot: {date}")
        return load_snapshot(date)
        
    except Exception as e:
        logger.error(f"Failed to find latest snapshot: {e}")
        return None


def get_previous_date(current_date: str) -> Optional[str]:
    """
    Find the most recent snapshot date before the current date.
    Skips weekends, holidays, and missed days.
    
    Args:
        current_date: Date string in format "YYYY-MM-DD"
    
    Returns:
        Date string of previous snapshot, or None if no previous snapshot exists
    """
    try:
        # Parse current date
        current = datetime.strptime(current_date, "%Y-%m-%d")
        
        # Get all snapshot files
        snapshot_files = list(SNAPSHOTS_DIR.glob("*.json"))
        
        if not snapshot_files:
            logger.debug("No previous snapshots exist")
            return None
        
        # Extract dates from filenames and filter for dates before current
        previous_dates = []
        for filepath in snapshot_files:
            date_str = filepath.stem
            try:
                snapshot_date = datetime.strptime(date_str, "%Y-%m-%d")
                if snapshot_date < current:
                    previous_dates.append(date_str)
            except ValueError:
                logger.warning(f"Invalid snapshot filename: {filepath.name}")
                continue
        
        if not previous_dates:
            logger.debug(f"No snapshots found before {current_date}")
            return None
        
        # Return the most recent date before current
        most_recent = sorted(previous_dates)[-1]
        logger.info(f"Previous snapshot date: {most_recent}")
        return most_recent
        
    except Exception as e:
        logger.error(f"Failed to get previous date for {current_date}: {e}")
        return None


def get_snapshot_history(days: int = 7) -> list[DailySnapshot]:
    """
    Load the last N days of snapshots.
    
    Args:
        days: Number of most recent snapshots to load
    
    Returns:
        List of DailySnapshot objects, sorted by date (oldest first)
    """
    try:
        # Get all snapshot files
        snapshot_files = list(SNAPSHOTS_DIR.glob("*.json"))
        
        if not snapshot_files:
            return []
        
        # Sort by filename (date) and take the last N
        sorted_files = sorted(snapshot_files)[-days:]
        
        # Load each snapshot
        snapshots = []
        for filepath in sorted_files:
            date = filepath.stem
            snapshot = load_snapshot(date)
            if snapshot:
                snapshots.append(snapshot)
        
        logger.info(f"Loaded {len(snapshots)} snapshots from history")
        return snapshots
        
    except Exception as e:
        logger.error(f"Failed to load snapshot history: {e}")
        return []