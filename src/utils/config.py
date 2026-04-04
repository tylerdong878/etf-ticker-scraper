"""
Configuration settings for the ETF ticker scraper.
Defines issuer URLs, scraping parameters, and directory paths.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Issuer configuration - organized by scraping method

# Issuers available on stockanalysis.com (11 issuers)
STOCKANALYSIS_ISSUERS = {
    "proshares": "https://stockanalysis.com/etf/provider/proshares/",
    "direxion": "https://stockanalysis.com/etf/provider/direxion/",
    "graniteshares": "https://stockanalysis.com/etf/provider/graniteshares/",
    "yieldmax": "https://stockanalysis.com/etf/provider/yieldmax/",
    "neos": "https://stockanalysis.com/etf/provider/neos/",
    "roundhill": "https://stockanalysis.com/etf/provider/roundhill/",
    "rex-microsectors": "https://stockanalysis.com/etf/provider/rex-microsectors/",
    "tuttle-capital-management": "https://stockanalysis.com/etf/provider/tuttle-capital-management/",
    "defiance": "https://stockanalysis.com/etf/provider/defiance/",
    "simplify": "https://stockanalysis.com/etf/provider/simplify/",
    "tradr": "https://stockanalysis.com/etf/provider/tradr/",
    "global-x": "https://stockanalysis.com/etf/provider/global-x/",
    "kraneshares": "https://stockanalysis.com/etf/provider/kraneshares/",
    "bitwise": "https://stockanalysis.com/etf/provider/bitwise/",
    "grayscale": "https://stockanalysis.com/etf/provider/grayscale/",
    "ark": "https://stockanalysis.com/etf/provider/ark/",
}

# Issuers scraped from their own websites (4 issuers)
DIRECT_ISSUERS = {
    "kurv": "https://www.kurvinvest.com/etfs",
    "volatility-shares": "https://www.volatilityshares.com/etf-product-list.php",
    "rex-shares": "https://www.rexshares.com/home/all-funds/",
    "leverage-shares": "https://leverageshares.com/us/all-etfs/",
    "bmo-max": "https://www.maxetns.com/",
}

# New launches page on stockanalysis.com
NEW_LAUNCHES_URL = "https://stockanalysis.com/etf/list/new/"

# Combined issuers dictionary for backward compatibility
ISSUERS = {**STOCKANALYSIS_ISSUERS, **DIRECT_ISSUERS}

# Scraping settings
SCRAPE_DELAY_MIN = int(os.getenv("SCRAPE_DELAY_MIN", "2"))
SCRAPE_DELAY_MAX = int(os.getenv("SCRAPE_DELAY_MAX", "5"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

# Feature flags
ENRICH_WITH_YFINANCE = os.getenv("ENRICH_WITH_YFINANCE", "true").lower() == "true"
SEND_EMAIL = os.getenv("SEND_EMAIL", "true").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
REPORT_FREQUENCY = os.getenv("REPORT_FREQUENCY", "weekly")

# Email settings
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "")

# Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
WATCHLIST_TICKERS = [t.strip().upper() for t in os.getenv("WATCHLIST_TICKERS", "").split(",") if t.strip()]

# Directory paths
DATA_DIR = BASE_DIR / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
CHANGELOG_DIR = DATA_DIR / "changelog"
LOGS_DIR = DATA_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"
REPORTS_DIR = DATA_DIR / "reports"

# Ensure directories exist
for directory in [SNAPSHOTS_DIR, CHANGELOG_DIR, LOGS_DIR, CACHE_DIR, REPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)