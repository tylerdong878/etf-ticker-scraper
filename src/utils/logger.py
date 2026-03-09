"""
Logging configuration for the ETF ticker scraper.
Sets up console and file logging with appropriate formats and levels.
"""
import logging
import sys
from pathlib import Path
from .config import LOGS_DIR


def get_logger(name: str) -> logging.Logger:
    """
    Create and configure a logger with console and file handlers.
    
    Args:
        name: Name of the logger (typically __name__ from calling module)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Format: "2026-03-08 06:00:00 | INFO | scraper | Scraped defiance: 62 funds"
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (INFO level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (DEBUG level)
    log_file = LOGS_DIR / "ticker_scraper.log"
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger