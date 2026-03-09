# ETF Competitor Monitoring Tool - Implementation Plan

## Project Overview
Automated Python tool to monitor 15 ETF issuers, track fund launches/closures, pull financial data, and send scheduled email reports.

## Architecture & Components

### 1. **Project Structure**
```
ticker-scraper/
├── src/
│   ├── scrapers/
│   │   ├── base_scraper.py          # Abstract base class
│   │   ├── proshares.py             # ProShares scraper
│   │   ├── direxion.py              # Direxion scraper
│   │   ├── bmo.py                   # BMO scraper
│   │   ├── graniteshares.py         # GraniteShares scraper
│   │   ├── yieldmax.py              # YieldMax scraper
│   │   ├── neos.py                  # NEOS scraper
│   │   ├── roundhill.py             # Roundhill scraper
│   │   ├── rex.py                   # REX scraper
│   │   ├── tuttle.py                # Tuttle scraper
│   │   ├── defiance.py              # Defiance scraper
│   │   ├── simplify.py              # Simplify scraper
│   │   ├── volatilityshares.py      # VolatilityShares scraper
│   │   ├── tradr.py                 # Tradr scraper
│   │   ├── leverageshares.py        # LeverageShares scraper
│   │   └── kurv.py                  # Kurv scraper
│   ├── models/
│   │   ├── etf.py                   # ETF data model
│   │   └── issuer.py                # Issuer data model
│   ├── services/
│   │   ├── yahoo_finance.py         # Yahoo Finance API integration
│   │   ├── change_detector.py       # Launch/closure detection
│   │   └── email_service.py         # Email report generation
│   ├── utils/
│   │   ├── logger.py                # Logging configuration
│   │   └── config.py                # Configuration management
│   └── main.py                      # Main orchestration script
├── data/
│   ├── snapshots/                   # Historical ETF data
│   └── logs/                        # Application logs
├── tests/                           # Unit and integration tests
├── .github/
│   └── workflows/
│       └── daily_scrape.yml         # GitHub Actions workflow
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
├── .gitignore
└── README.md
```

### 2. **Core Components**

#### **Scraper Framework**
- **Base Scraper Class**: Abstract class with common methods (fetch HTML, parse, error handling)
- **15 Custom Scrapers**: One per issuer, each implementing issuer-specific parsing logic
- **Key Methods**: `get_etf_list()`, `extract_ticker()`, `extract_fund_name()`
- **Technologies**: requests, BeautifulSoup4, selenium (for JavaScript-heavy sites)

#### **Data Models**
- **ETF Model**: ticker, name, issuer, inception_date, aum, nav, expense_ratio, volume, last_updated
- **Issuer Model**: name, website_url, scraper_class, last_scraped
- **Storage**: JSON files for snapshots (simple, version-controllable, no database needed)

#### **Change Detection System**
- Compare current scrape vs. previous snapshot
- Detect new tickers (launches) and missing tickers (closures)
- Track changes in AUM, NAV for existing funds
- Generate change summary for email report

#### **Yahoo Finance Integration**
- Use `yfinance` library (free, no API key needed)
- Pull: AUM, NAV, expense ratio, volume, inception date
- Batch requests with rate limiting to avoid blocks
- Cache results to minimize API calls

#### **Email Report Generator**
- **Section 1**: Changes (launches/closures) - highlighted at top
- **Section 2**: Competitor summary table (issuer, total funds, total AUM)
- **Section 3**: Full fund breakdown by issuer (sortable by AUM)
- **Format**: HTML email with CSS styling for readability
- **Delivery**: Gmail SMTP (free tier: 500 emails/day)

#### **Automation & Scheduling**
- **GitHub Actions**: Free tier (2,000 minutes/month)
- **Cron Schedule**: Daily at 6 AM PT or weekly on Mondays
- **Workflow**: Checkout code → Install dependencies → Run scraper → Send email
- **Secrets**: Store Gmail credentials in GitHub Secrets

### 3. **Implementation Phases**

#### **Phase 1: Foundation** (Days 1-2)
- Set up project structure
- Create base scraper class
- Implement data models
- Set up logging and configuration

#### **Phase 2: Scrapers** (Days 3-7)
- Research each issuer's website structure
- Implement 15 custom scrapers (3 per day)
- Test each scraper individually
- Handle edge cases (JavaScript rendering, rate limiting)

#### **Phase 3: Data Pipeline** (Days 8-9)
- Integrate Yahoo Finance API
- Build change detection logic
- Create snapshot storage system
- Test with historical data

#### **Phase 4: Reporting** (Days 10-11)
- Design HTML email template
- Implement report generator
- Configure Gmail SMTP
- Test email delivery

#### **Phase 5: Automation** (Day 12)
- Create GitHub Actions workflow
- Set up environment variables and secrets
- Test scheduled execution
- Add error notifications

#### **Phase 6: Polish** (Days 13-14)
- Add comprehensive error handling
- Write documentation
- Create setup guide
- End-to-end testing

### 4. **Key Technologies**

**Python Libraries:**
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `selenium` - JavaScript-heavy sites
- `yfinance` - Yahoo Finance data
- `pandas` - Data manipulation
- `jinja2` - Email templating
- `python-dotenv` - Environment variables
- `schedule` - Local scheduling (optional)

**External Services:**
- GitHub Actions (free automation)
- Gmail SMTP (free email delivery)
- Yahoo Finance API (free financial data)

### 5. **Configuration Requirements**

**Environment Variables:**
- `GMAIL_USER` - Gmail address
- `GMAIL_APP_PASSWORD` - Gmail app-specific password
- `RECIPIENT_EMAIL` - Report recipient
- `SCHEDULE_CRON` - Cron expression for timing

**GitHub Secrets:**
- Same as environment variables above

### 6. **Data Flow**

1. **Scrape**: Run all 15 scrapers → collect current ETF lists
2. **Enrich**: Pull Yahoo Finance data for each ticker
3. **Compare**: Load previous snapshot → detect changes
4. **Report**: Generate HTML email with 3 sections
5. **Send**: Deliver via Gmail SMTP
6. **Save**: Store current data as new snapshot

### 7. **Error Handling Strategy**

- Retry logic for network failures (3 attempts with exponential backoff)
- Fallback to cached data if scraper fails
- Email notification on critical errors
- Detailed logging for debugging
- Graceful degradation (continue if one issuer fails)

### 8. **Testing Strategy**

- Unit tests for each scraper
- Integration tests for data pipeline
- Mock Yahoo Finance API for testing
- Test email generation with sample data
- Dry-run mode for GitHub Actions testing

### 9. **Deployment Checklist**

- [ ] Create GitHub repository
- [ ] Set up Gmail app password
- [ ] Configure GitHub Secrets
- [ ] Test scrapers for all 15 issuers
- [ ] Verify Yahoo Finance integration
- [ ] Test email delivery
- [ ] Enable GitHub Actions workflow
- [ ] Monitor first scheduled run
- [ ] Document any issuer-specific quirks

### 10. **Maintenance Considerations**

- Scrapers may break when issuers redesign websites
- Monitor GitHub Actions execution logs
- Update scraper logic as needed
- Consider adding Slack/Discord notifications
- Potential future: web dashboard for historical data

## 15 ETF Issuers to Monitor

1. ProShares
2. Direxion
3. BMO
4. GraniteShares
5. YieldMax
6. NEOS
7. Roundhill
8. REX
9. Tuttle
10. Defiance
11. Simplify
12. VolatilityShares
13. Tradr
14. LeverageShares
15. Kurv

## Next Steps

Ready to start implementation! The project is broken into 12 clear tasks that can be tackled sequentially. Each component is modular and testable independently.