# ETF Ticker Scraper - Implementation Plan v4

## Project Overview
Automated system to scrape ETF data from multiple sources, detect changes (launches/closures), enrich with market data, and generate weekly reports with executive summary emails and full PDF attachments.

## Architecture

### 1. Data Sources (15 Issuers)
**StockAnalysis.com (11 issuers):**
- ProShares, Direxion, GraniteShares, YieldMax, NEOS, Roundhill, REX Microsectors, Tuttle Capital Management, Defiance, Simplify, TRADR

**Direct Websites (4 issuers):**
- Kurv: https://www.kurvinvest.com/etfs
- Volatility Shares: https://www.volatilityshares.com/etf-product-list.php
- REX Shares: https://www.rexshares.com/home/all-funds/
- Leverage Shares: https://leverageshares.com/us/all-etfs/

**New Launches:**
- StockAnalysis.com new ETF list: https://stockanalysis.com/etf/list/new/

**Deferred:**
- BMO (blocks headless browsers - requires workaround)

### 2. Core Components

#### A. Scrapers (`src/scrapers/`)
- **`stockanalysis_scraper.py`**: Scrapes 11 issuers from stockanalysis.com
  - `StockAnalysisScraper` class with context manager
  - `scrape_all()` iterates through STOCKANALYSIS_ISSUERS
  - Parses table: Symbol | Fund Name | Assets | Div. Yield | Exp. Ratio | Change 1Y

- **`direct_scrapers.py`**: Individual scraper classes for 4 direct issuers
  - `KurvScraper`: Extracts ticker from href, parses AUM from column 6
  - `VolatilitySharesScraper`: Parses NAV and Net Assets
  - `RexSharesScraper`: Simple ticker/name table (no AUM)
  - `LeverageSharesScraper`: Basic ticker/name extraction
  - `scrape_all_direct()`: Runs all 4 with rate limiting

- **`new_launches_scraper.py`**: Scrapes new ETF launches
  - `NewLaunchesScraper` class
  - `scrape()`: Gets all 100 most recent launches
  - `check_for_issuer_launches()`: Filters by issuer names

#### B. Data Models (`src/utils/models.py`)
```python
@dataclass
class ETFund:
    ticker: str
    name: str
    issuer: str
    aum: Optional[int]
    expense_ratio: Optional[float]
    div_yield: Optional[float]
    return_1y: Optional[float]
    nav: Optional[float]
    volume: Optional[int]
    inception_date: Optional[str]
    scraped_at: str

@dataclass
class IssuerSnapshot:
    issuer_slug: str
    total_funds: int
    total_aum: int
    funds: list[ETFund]

@dataclass
class DailySnapshot:
    date: str  # YYYY-MM-DD
    issuers: dict[str, IssuerSnapshot]
```

#### C. Detection (`src/detection/`)
- **`snapshot_manager.py`**: Snapshot persistence
  - `save_snapshot()`: Serialize to JSON in data/snapshots/
  - `load_snapshot()`: Deserialize from JSON
  - `load_latest_snapshot()`: Find most recent snapshot
  - `get_previous_date()`: Find previous snapshot (skips gaps)

- **`change_detector.py`**: Change detection logic
  - `detect_changes()`: Compare two snapshots
    - Launches: ticker in current but not previous
    - Closures: ticker in previous but not current
    - AUM changes: same ticker, different AUM
  - `append_to_changelog()`: Save to weekly changelog (ISO week format)
  - `is_confirmed_closure()`: Verify closure over N consecutive days
  - `filter_confirmed_closures()`: Remove false positives

#### D. Enrichment (`src/enrichment/`)
- **`yahoo_finance.py`**: yfinance data enrichment
  - `enrich_funds()`: Adds NAV, volume, inception_date
  - Daily caching in data/cache/yfinance_{date}.json
  - Rate limiting: 0.5s between requests
  - Error handling for missing data

#### E. Reporting (`src/reporting/`)
- **`templates/report.html`**: Jinja2 HTML template
  - 7 sections: Weekly Activity, Launches, Closures, Scoreboard, AUM Movers, Fund Count Changes, Full Fund List
  - Print CSS for PDF generation (page breaks, formatting)
  - Conditional rendering: `{% if not is_email_body %}` hides Full Fund List in email
  - Dark navy header, clean white body, mobile-responsive

- **`email_service.py`**: Report generation and email delivery
  - `generate_report()`: Renders Jinja2 template
    - `is_email_body=True`: Executive summary (no full fund list)
    - `is_email_body=False`: Full report for PDF
  - `generate_pdf()`: Converts HTML to PDF using WeasyPrint
  - `send_email()`: Sends email with:
    - HTML body: Executive summary (sections 1-6)
    - PDF attachment: Full report (all 7 sections)
  - `save_report_locally()`: Saves HTML to data/reports/
  - `_merge_rex_issuers()`: Combines REX Microsectors + REX Shares

### 3. Configuration (`src/utils/config.py`)
```python
STOCKANALYSIS_ISSUERS = {
    "proshares": "https://stockanalysis.com/etf/provider/proshares/",
    # ... 10 more
}

DIRECT_ISSUERS = {
    "kurv": "https://www.kurvinvest.com/etfs",
    "volatility-shares": "https://www.volatilityshares.com/etf-product-list.php",
    "rex-shares": "https://www.rexshares.com/home/all-funds/",
    "leverage-shares": "https://leverageshares.com/us/all-etfs/",
}

NEW_LAUNCHES_URL = "https://stockanalysis.com/etf/list/new/"
BMO_DEFERRED = "https://www.bmogam.com/ca-en/products/exchange-traded-funds/"

# Environment variables
SCRAPE_DELAY_MIN = 2
SCRAPE_DELAY_MAX = 5
HEADLESS = true
ENRICH_WITH_YFINANCE = true
SEND_EMAIL = true
DRY_RUN = false
REPORT_FREQUENCY = "weekly"  # daily, weekly, both
```

### 4. Main Orchestrator (`src/main.py`)

#### CLI Modes
```bash
# Scrape mode: Collect data, detect changes
python3 -m src.main --mode scrape [--issuer defiance] [--dry-run]

# Report mode: Generate and send report
python3 -m src.main --mode report [--dry-run]

# Both: Scrape then report (for Mondays)
python3 -m src.main --mode both [--dry-run]
```

#### Scrape Workflow
1. Run `StockAnalysisScraper.scrape_all()` (11 issuers)
2. Run `scrape_all_direct()` (4 issuers)
3. Check for new launches with `NewLaunchesScraper`
4. Merge rex-microsectors + rex-shares → "rex"
5. Enrich with yfinance if enabled
6. Build DailySnapshot (date = today)
7. Save snapshot to data/snapshots/{date}.json
8. Load previous snapshot, detect changes
9. Append changes to weekly changelog
10. Log summary: "Scraped X issuers | Y funds | Z launches | W closures"

#### Report Workflow
1. Load latest snapshot
2. Load snapshot from 7 days ago (or nearest)
3. Load weekly changelog
4. Generate full HTML report (all 7 sections)
5. Save full report locally (always)
6. If SEND_EMAIL and not dry-run:
   - Generate executive summary HTML (sections 1-6)
   - Convert full report to PDF
   - Send email with summary body + PDF attachment
7. Respect REPORT_FREQUENCY:
   - "weekly": Report only on Mondays
   - "daily": Report every run
   - "both": Daily alerts + full weekly on Mondays

### 5. Automation (`.github/workflows/daily_monitor.yml`)

**Schedule:**
- Cron: `0 10 * * 1-5` (10:00 UTC = 6 AM ET, weekdays)
- Manual trigger with mode selection

**Logic:**
- Monday: `mode=both` (scrape + report)
- Tuesday-Friday: `mode=scrape` (scrape only)

**Steps:**
1. Checkout repo
2. Setup Python 3.11
3. Install dependencies (including weasyprint)
4. Install Playwright Chromium
5. Set environment variables from secrets
6. Run `python3 -m src.main --mode $MODE`
7. Commit and push data/ changes
8. Send error email on failure

**Required Secrets:**
- GMAIL_USER
- GMAIL_APP_PASSWORD
- RECIPIENT_EMAIL

### 6. Data Storage Structure
```
data/
├── snapshots/
│   ├── 2026-03-03.json
│   ├── 2026-03-04.json
│   └── 2026-03-05.json
├── changelog/
│   ├── 2026-W09.json
│   └── 2026-W10.json
├── cache/
│   └── yfinance_2026-03-05.json
├── reports/
│   ├── report_2026-03-03.html
│   └── report_2026-03-04.html
└── logs/
    └── scraper.log
```

### 7. Email Report Structure

**Email Body (Executive Summary):**
- Section 1: Weekly Activity Log (timeline)
- Section 2: New Launches (detail cards)
- Section 3: Closures & Delistings
- Section 4: Issuer Scoreboard (WoW changes)
- Section 5: AUM Movers (top 10 gainers/losers)
- Section 6: Fund Count Changes

**PDF Attachment (Full Report):**
- All 6 sections above PLUS
- Section 7: Full Fund List (all funds grouped by issuer)

### 8. Error Handling
- Partial failures save whatever data was collected
- Individual issuer failures don't stop the entire scrape
- Missing yfinance data logged as warnings
- Email failures logged but don't crash the system
- GitHub Actions sends error notification email on workflow failure

### 9. Dependencies
```
playwright          # Browser automation
beautifulsoup4      # HTML parsing
yfinance           # Market data enrichment
pandas             # Data manipulation
jinja2             # HTML templating
python-dotenv      # Environment variables
weasyprint         # HTML to PDF conversion
```

### 10. Testing Strategy
- `--issuer defiance`: Test single issuer scraping
- `--dry-run`: Test without sending emails
- Manual workflow trigger: Test specific modes
- Local runs: `python3 -m src.main --mode scrape --dry-run`

## Implementation Status: ✅ COMPLETE

All components implemented and integrated:
- ✅ 15 issuer scrapers (11 StockAnalysis + 4 direct)
- ✅ New launches scraper
- ✅ Data models with serialization
- ✅ Snapshot management
- ✅ Change detection with confirmation
- ✅ yfinance enrichment with caching
- ✅ HTML report template with print CSS
- ✅ Email service with PDF attachment
- ✅ Main orchestrator with CLI
- ✅ GitHub Actions automation
- ✅ Error handling and notifications

## Next Steps
1. Set up GitHub secrets (GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL)
2. Test locally: `python3 -m src.main --mode scrape --dry-run`
3. Enable GitHub Actions workflow
4. Monitor first automated run
5. Adjust REPORT_FREQUENCY as needed