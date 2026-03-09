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

# Issuer configuration - maps issuer slug to stockanalysis.com URL
ISSUERS = {
    # 14 issuers via stockanalysis.com
    "proshares": "https://stockanalysis.com/etf/provider/proshares/",
    "direxion": "https://stockanalysis.com/etf/provider/direxion/",
    "graniteshares": "https://stockanalysis.com/etf/provider/graniteshares/",
    "yieldmax": "https://stockanalysis.com/etf/provider/yieldmax/",
    "neos": "https://stockanalysis.com/etf/provider/neos/",
    "roundhill": "https://stockanalysis.com/etf/provider/roundhill/",
    "rex-microsectors": "https://stockanalysis.com/etf/provider/rex-microsectors/",
    "rex-shares": "https://stockanalysis.com/etf/provider/rex-shares/",
    "tuttle-capital-management": "https://stockanalysis.com/etf/provider/tuttle-capital-management/",
    "defiance": "https://stockanalysis.com/etf/provider/defiance/",
    "simplify": "https://stockanalysis.com/etf/provider/simplify/",
    "volatility-shares": "https://stockanalysis.com/etf/provider/volatility-shares/",
    "tradr": "https://stockanalysis.com/etf/provider/tradr/",
    "leverage-shares": "https://stockanalysis.com/etf/provider/leverage-shares/",
    "kurv": "https://stockanalysis.com/etf/provider/kurv/",
    
    # BMO handled separately with custom scraper
    "bmo": "CUSTOM_SCRAPER"
}

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