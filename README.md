# ETF Ticker Scraper

Automated system for tracking ETF launches, closures, and market changes across 16 major issuers. Generates weekly reports with executive summaries, Gemini-powered market insights, and detailed PDF attachments.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Multi-Source Scraping**: Collects data from 16 ETF issuers (11 via StockAnalysis.com, 5 direct websites)
- **Change Detection**: Automatically identifies launches, closures, and AUM changes
- **Market Enrichment**: Enhances data with yfinance (NAV, volume, inception dates)
- **Gemini Insights**: Weekly ETF industry news and watchlist stock updates via Gemini API with Google Search grounding
- **Smart Reporting**: Generates HTML reports with PDF attachments
- **GitHub Actions**: Automated daily scraping and weekly reports

## Project Structure

```
ticker-scraper/
├── src/
│   ├── scrapers/          # Data collection from multiple sources
│   ├── detection/         # Change detection and snapshot management
│   ├── enrichment/        # Market data enrichment via yfinance
│   ├── reporting/         # HTML/PDF report generation
│   └── utils/             # Models, config, logging
├── tests/                 # Pytest test suite
├── data/                  # Snapshots, changelogs, reports, cache
├── docs/                  # Design iterations (v1-v4)
└── .github/workflows/     # Automated scraping & reporting
```

## Quick Start

### Prerequisites

- Python 3.11+
- Gmail account with app password (for email reports)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ticker-scraper.git
cd ticker-scraper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium --with-deps

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

Create a `.env` file with:

```env
# Scraping
SCRAPE_DELAY_MIN=2
SCRAPE_DELAY_MAX=5
HEADLESS=true

# Features
ENRICH_WITH_YFINANCE=true
SEND_EMAIL=true
DRY_RUN=false
REPORT_FREQUENCY=weekly  # daily, weekly, or both

# Email (Gmail)
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient@example.com

# Gemini (optional — insights are skipped if not set)
GEMINI_API_KEY=your-gemini-api-key
WATCHLIST_TICKERS=  # comma-separated tickers for stock insights
```

## Usage

### CLI Commands

```bash
# Scrape all issuers
python3 -m src.main --mode scrape

# Generate and send report
python3 -m src.main --mode report

# Both (scrape + report)
python3 -m src.main --mode both

# Test single issuer
python3 -m src.main --mode scrape --issuer defiance

# Dry run (no email)
python3 -m src.main --mode both --dry-run
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_models.py

# Verbose output
pytest -v

# Run with coverage
pytest --cov=src
```

## Data Sources

### StockAnalysis.com (11 Issuers)
- ProShares, Direxion, GraniteShares, YieldMax, NEOS
- Roundhill, REX Microsectors, Tuttle Capital Management
- Defiance, Simplify, TRADR

### Direct Websites (5 Issuers)
- **Kurv**: https://www.kurvinvest.com/etfs
- **Volatility Shares**: https://www.volatilityshares.com/etf-product-list.php
- **REX Shares**: https://www.rexshares.com/home/all-funds/
- **Leverage Shares**: https://leverageshares.com/us/all-etfs/
- **BMO MAX**: https://www.maxetns.com/

### New Launches
- Monitors StockAnalysis.com's new ETF list for launches from tracked issuers

## Report Structure

### Email Body (Executive Summary)
1. Weekly Activity Log (timeline)
2. New Launches (detail cards)
3. Closures & Delistings
4. Issuer Scoreboard (WoW changes)
5. Top AUM Movers (gainers/losers)
6. Fund Count Changes
7. ETF Industry Insights (Gemini-powered, sourced from the past week)
8. Watchlist Stock Insights (per-ticker news for configured tickers)

### PDF Attachment (Full Report)
- All sections above PLUS
- Complete fund list grouped by issuer

## Automation

GitHub Actions runs automatically:
- **Schedule**: Weekdays at 10:00 UTC (6 AM ET)
- **Monday**: Full scrape + report
- **Tuesday-Friday**: Scrape only
- **Manual**: Trigger with custom mode

### Required Secrets
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`
- `RECIPIENT_EMAIL`

## Testing

Comprehensive test suite covering:
- Number parsing (AUM, percentages)
- Change detection logic
- Model serialization (round-trips)
- Report generation

```bash
pytest                    # Run all tests
pytest -v                 # Verbose
pytest -k "parsing"       # Specific tests
```

## Data Storage

```
data/
├── snapshots/           # Daily snapshots (YYYY-MM-DD.json)
├── changelog/           # Weekly changelogs (YYYY-WNN.json)
├── cache/              # yfinance cache (daily)
├── reports/            # HTML & PDF reports
└── logs/               # Application logs
```

## Development

### Architecture

The system follows a modular pipeline:

1. **Scraping**: Collect data from 15 sources
2. **Detection**: Compare snapshots, identify changes
3. **Enrichment**: Add market data via yfinance
4. **Reporting**: Generate HTML/PDF reports
5. **Delivery**: Email with summary + attachment

See [`docs/PLANv4.md`](docs/PLANv4.md) for detailed architecture.

### Design Iterations

The project evolved through multiple design iterations:
- [`docs/PLAN.md`](docs/PLAN.md) - Initial design
- [`docs/PLANv2.md`](docs/PLANv2.md) - Enhanced scraping
- [`docs/PLANv3.md`](docs/PLANv3.md) - Change detection
- [`docs/PLANv4.md`](docs/PLANv4.md) - PDF reports (current)

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Data sources: StockAnalysis.com and individual ETF issuers
- Market data: Yahoo Finance (yfinance)
- PDF generation: WeasyPrint
- Browser automation: Playwright

## Support

For issues or questions:
- Open an issue on GitHub
- Check [`docs/`](docs/) for design documentation
- Review test files for usage examples

---

**Note**: This project is for educational and personal use. Always verify ETF data with official sources before making investment decisions.