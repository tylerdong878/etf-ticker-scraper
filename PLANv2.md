# ETF Competitor Monitor - Revised Plan (v2)

## Key Change from v1
Instead of building 15 individual scrapers for each issuer's website, we scrape **stockanalysis.com** which already aggregates all ETF provider data in a consistent table format. BMO is the one exception (Canadian-focused) and gets its own scraper.

---

## Architecture

### Project Structure
```
etf-monitor/
├── src/
│   ├── scrapers/
│   │   ├── stockanalysis_scraper.py   # Main scraper (14 issuers)
│   │   └── bmo_scraper.py            # BMO-specific scraper
│   ├── enrichment/
│   │   └── yahoo_finance.py          # yfinance for supplemental data
│   ├── detection/
│   │   └── change_detector.py        # Launch/closure detection
│   ├── reporting/
│   │   ├── email_service.py          # Gmail SMTP delivery
│   │   └── templates/
│   │       └── report.html           # Jinja2 email template
│   ├── utils/
│   │   ├── config.py                 # Issuer URLs, settings
│   │   ├── logger.py                 # Logging setup
│   │   └── models.py                 # Data models
│   └── main.py                       # Orchestration
├── data/
│   ├── snapshots/                    # Daily JSON snapshots (git-tracked)
│   │   ├── 2026-03-03.json
│   │   ├── 2026-03-04.json
│   │   ├── 2026-03-08.json
│   │   └── latest.json               # Symlink to most recent
│   ├── changelog/                    # Weekly change logs
│   │   └── 2026-W10.json            # Week-by-week activity
│   └── logs/
├── tests/
├── .github/
│   └── workflows/
│       └── daily_monitor.yml         # GitHub Actions cron
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Issuer Configuration

```python
ISSUERS = {
    # 14 issuers via stockanalysis.com
    "proshares":          "https://stockanalysis.com/etf/provider/proshares/",
    "direxion":           "https://stockanalysis.com/etf/provider/direxion/",
    "graniteshares":      "https://stockanalysis.com/etf/provider/graniteshares/",
    "yieldmax":           "https://stockanalysis.com/etf/provider/yieldmax/",
    "neos":               "https://stockanalysis.com/etf/provider/neos/",
    "roundhill":          "https://stockanalysis.com/etf/provider/roundhill/",
    "rex-microsectors":   "https://stockanalysis.com/etf/provider/rex-microsectors/",
    "rex-shares":         "https://stockanalysis.com/etf/provider/rex-shares/",
    "tuttle-capital-management": "https://stockanalysis.com/etf/provider/tuttle-capital-management/",
    "defiance":           "https://stockanalysis.com/etf/provider/defiance/",
    "simplify":           "https://stockanalysis.com/etf/provider/simplify/",
    "volatility-shares":  "https://stockanalysis.com/etf/provider/volatility-shares/",
    "tradr":              "https://stockanalysis.com/etf/provider/tradr/",
    "leverage-shares":    "https://stockanalysis.com/etf/provider/leverage-shares/",
    "kurv":               "https://stockanalysis.com/etf/provider/kurv/",

    # BMO handled separately
    "bmo":                "CUSTOM_SCRAPER"
}
```

**Note on REX:** Stockanalysis splits REX into two providers — "REX Microsectors" (ETNs, ~$13B) and "REX Shares" (ETFs, ~$1.1B). We scrape both and merge under one "REX" umbrella in reports.

---

## Data Flow

```
1. SCRAPE (daily, weekdays)
   ├── stockanalysis.com/etf/provider/{issuer}/ × 14 issuers
   │   → Parse HTML table: ticker, name, AUM, div yield, expense ratio, 1Y return
   └── BMO custom scraper (etfdb.com or bmogam.com)
       → Parse BMO fund list

2. ENRICH (daily, after scrape)
   → For each ticker: NAV, volume, inception date, sector
   → Rate limited: ~2 req/sec, cached to avoid redundant calls

3. SAVE SNAPSHOT (daily)
   └── Write to data/snapshots/{date}.json
   └── Git commit + push (version-controlled history)

3b. DAILY CHANGE LOG (daily, after save)
   ├── Compare today's snapshot vs yesterday's
   ├── Append any changes to data/changelog/{week}.json:
   │   {
   │     "date": "2026-03-04",
   │     "launches": [{"ticker": "TRIL", "issuer": "defiance", "name": "..."}],
   │     "closures": [],
   │     "aum_changes": [{"ticker": "MSTX", "prev": 300M, "current": 280M}]
   │   }
   └── This changelog powers the weekly timeline in the email report

4. COMPARE (weekly, Mondays)
   ├── Load Monday snapshot + previous Monday snapshot
   ├── Diff per issuer:
   │   ├── NEW tickers     → flag as "Launch"
   │   ├── MISSING tickers → flag as "Closure/Delist"
   │   └── CHANGED AUM     → track growth/decline (week-over-week)
   └── Also check: any ticker missing for 2+ consecutive daily snapshots
        before confirming closure (avoids false positives from scrape errors)

5. REPORT (weekly, Mondays)
   ├── Generate HTML email via Jinja2 template
   │   │
   │   ├── Section 1: WEEKLY ACTIVITY LOG
   │   │   Timeline view of what happened each day:
   │   │   ├── "Tue 3/3: Defiance launched TRIL (Trillion Dollar Club Index ETF)"
   │   │   ├── "Wed 3/4: Tuttle launched UFOD (UFO Disclosure ETF)"
   │   │   ├── "Thu 3/5: REX closed RXYZ (delisted)"
   │   │   └── Shows exact day each change was detected, not just a weekly dump
   │   │
   │   ├── Section 2: NEW LAUNCHES (detail cards)
   │   │   For each new fund launched this week:
   │   │   ├── Ticker, full name, issuer
   │   │   ├── Expense ratio, category/strategy
   │   │   ├── AUM at end of first week (early traction signal)
   │   │   └── Link to stockanalysis.com page
   │   │
   │   ├── Section 3: CLOSURES & DELISTINGS
   │   │   For each fund removed this week:
   │   │   ├── Ticker, name, issuer
   │   │   ├── Last known AUM before closure
   │   │   └── How long it was active (inception → closure)
   │   │
   │   ├── Section 4: ISSUER SCOREBOARD
   │   │   Table comparing all 15 issuers:
   │   │   ├── Issuer | # Funds | Total AUM | WoW AUM Δ | WoW AUM Δ% | New | Closed
   │   │   ├── Sorted by total AUM descending
   │   │   └── Color-coded: green for growth, red for decline
   │   │
   │   ├── Section 5: AUM MOVERS
   │   │   ├── Top 10 funds by AUM gained this week ($)
   │   │   ├── Top 10 funds by AUM lost this week ($)
   │   │   └── Helps spot which products are gaining traction or bleeding out
   │   │
   │   ├── Section 6: FUND COUNT CHANGES
   │   │   ├── Which issuers added the most funds this week
   │   │   ├── Which issuers closed the most funds
   │   │   └── Running total trend (e.g. "Defiance: 60 → 62 funds, +2 this week")
   │   │
   │   └── Section 7: FULL FUND LIST (attachment or expandable)
   │       ├── Every fund across all 15 issuers
   │       ├── Grouped by issuer, sorted by AUM within each group
   │       └── Columns: Ticker | Name | AUM | Exp Ratio | Div Yield | 1Y Return
   │
   └── Send via Gmail SMTP
```

---

## Data Model

```python
# Per-fund data scraped from stockanalysis.com
{
    "ticker": "QQQY",
    "name": "Defiance Nasdaq 100 Weekly Distribution ETF",
    "issuer": "defiance",
    "aum": 204390000,           # from stockanalysis
    "expense_ratio": 0.0101,    # from stockanalysis
    "div_yield": 0.4495,        # from stockanalysis
    "return_1y": -0.2557,       # from stockanalysis
    # Optional enrichment from yfinance:
    "nav": 12.34,
    "volume": 1500000,
    "inception_date": "2023-09-13",
    "scraped_at": "2026-03-08T06:00:00Z"
}

# Snapshot structure
{
    "date": "2026-03-08",
    "issuers": {
        "defiance": {
            "total_funds": 62,
            "total_aum": 7540000000,
            "funds": [ ... ]
        },
        ...
    }
}
```

---

## Scraping Strategy

### stockanalysis.com (14 issuers)
- **Method**: Playwright (the tables are JS-rendered, won't load with plain requests/BS4)
- **Parse**: Each provider page has a single table with columns:
  Symbol | Fund Name | Assets | Div. Yield | Exp. Ratio | Change 1Y
- **Rate limiting**: 2-3 second delay between page loads, randomized
- **User-Agent rotation**: Rotate between 3-4 common browser UAs
- **Fallback**: If stockanalysis blocks, fall back to etfdb.com provider pages

### BMO (1 issuer)
- **Primary source**: etfdb.com/etfs/issuers/bmo/
- **Alternative**: bmogam.com Canadian ETF page
- **Method**: Playwright or requests + BS4 depending on JS rendering

### Anti-blocking
- Randomized delays (2-5 sec between requests)
- Rotate User-Agent strings
- Run during off-peak hours (6 AM ET via cron)
- Cache aggressively — only scrape once per run
- If blocked: exponential backoff, then skip issuer and use cached data

---

## Implementation Phases

### Phase 1: Core Scraper (Days 1-3)
- [ ] Set up project structure and dependencies
- [ ] Build `stockanalysis_scraper.py` — single scraper that:
  - Takes a provider URL
  - Loads page with Playwright
  - Parses the ETF table
  - Returns list of fund dicts
- [ ] Test against 2-3 issuers to validate parsing
- [ ] Handle pagination if needed (some issuers have 100+ funds)

### Phase 2: All Issuers + BMO (Days 4-5)
- [ ] Run scraper against all 14 stockanalysis issuers
- [ ] Build BMO-specific scraper
- [ ] Merge REX Microsectors + REX Shares into unified "REX"
- [ ] Handle Tuttle split (Tuttle Capital Management vs Tuttle Capital)
- [ ] Validate data quality across all 15+

### Phase 3: Change Detection (Days 6-7)
- [ ] Build snapshot save/load system (JSON)
- [ ] Implement diff logic: new tickers, removed tickers, AUM changes
- [ ] Handle edge cases:
  - Ticker symbol changes (not a launch/closure)
  - Fund name changes
  - Temporary scrape failures (don't flag as closure)
- [ ] Test with synthetic "before/after" snapshots

### Phase 4: yfinance Enrichment (Day 8)
- [ ] Pull supplemental data: NAV, volume, inception date
- [ ] Batch requests with rate limiting
- [ ] Cache results (don't re-fetch if already enriched today)
- [ ] Handle missing tickers gracefully (new/tiny funds may not be on yfinance yet)

### Phase 5: Email Reports (Days 9-10)
- [ ] Design HTML email template (Jinja2)
- [ ] Implement Gmail SMTP sender
- [ ] Three report sections:
  1. Launches & Closures (bold, color-coded)
  2. Issuer Summary (table: name, # funds, total AUM, Δ from last)
  3. Full Fund Breakdown (grouped by issuer)
- [ ] Test email rendering in Gmail, Outlook, Apple Mail

### Phase 6: Automation (Days 11-12)
- [ ] Create TWO GitHub Actions workflows:
  1. **Daily scrape** (`daily_scrape.yml`)
     - Cron: `0 10 * * 1-5` (6 AM ET, weekdays)
     - Scrape all issuers → enrich with yfinance → save snapshot
     - Compare with yesterday's snapshot → append to weekly changelog
     - Commit snapshot to repo (data/snapshots/{date}.json)
     - No email sent
  2. **Weekly report** (`weekly_report.yml`)
     - Cron: `0 11 * * 1` (7 AM ET, Mondays only)
     - Triggered AFTER daily scrape completes
     - Loads current snapshot + snapshot from 7 days ago
     - Reads weekly changelog for day-by-day timeline
     - Generates weekly diff (all launches/closures from the past week)
     - Sends email report
- [ ] Install Playwright browsers in CI
- [ ] Store secrets: GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL
- [ ] Test dry runs for both workflows
- [ ] Add error notification (email on scrape failure)
- [ ] Monitor first few live runs

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Scraping | Playwright (JS-rendered pages) |
| HTML Parsing | BeautifulSoup4 (backup) |
| Financial Data | yfinance |
| Data Storage | JSON snapshots (git-tracked) |
| Email Template | Jinja2 |
| Email Delivery | Gmail SMTP (smtplib) |
| Scheduling | GitHub Actions (cron) |
| Data Processing | pandas |
| Config | python-dotenv |
| Logging | Python logging module |

### requirements.txt
```
playwright==1.49.0
beautifulsoup4==4.12.3
yfinance==0.2.48
pandas==2.2.3
jinja2==3.1.4
python-dotenv==1.0.1
```

---

## Environment Variables

```env
# Email
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
RECIPIENT_EMAIL=recipient@example.com

# Scraping
SCRAPE_DELAY_MIN=2
SCRAPE_DELAY_MAX=5
HEADLESS=true

# Feature flags
ENRICH_WITH_YFINANCE=true
SEND_EMAIL=true
DRY_RUN=false
```

---

## Error Handling

| Scenario | Response |
|----------|----------|
| stockanalysis.com blocks/down | Use cached snapshot, flag in report |
| Single issuer page fails | Skip issuer, continue others, note in report |
| yfinance rate limited | Exponential backoff, skip enrichment if persistent |
| Gmail SMTP fails | Log error, save report as local HTML file |
| No previous snapshot exists | First run — no change detection, just save baseline |
| Ticker appears to close but scraper failed | Require ticker missing for 2+ consecutive runs before flagging closure |

---

## Future Enhancements

- [ ] Bloomberg terminal integration for additional competitor intel
- [ ] Slack/Discord webhook notifications for launches
- [ ] Web dashboard (Streamlit) for historical AUM trends
- [ ] Track SEC N-1A filings for upcoming launches before they hit exchanges
- [ ] Add more competitors beyond the initial 15
- [ ] Weekly summary report in addition to daily alerts
- [ ] AUM trend charts embedded in email reports

---

## Competitors Being Tracked

| # | Issuer | Source | StockAnalysis Slug |
|---|--------|--------|--------------------|
| 1 | ProShares | stockanalysis.com | proshares |
| 2 | Direxion | stockanalysis.com | direxion |
| 3 | BMO | etfdb.com / bmogam.com | N/A (custom) |
| 4 | GraniteShares | stockanalysis.com | graniteshares |
| 5 | YieldMax | stockanalysis.com | yieldmax |
| 6 | NEOS | stockanalysis.com | neos |
| 7 | Roundhill | stockanalysis.com | roundhill |
| 8 | REX (Microsectors) | stockanalysis.com | rex-microsectors |
| 9 | REX (Shares) | stockanalysis.com | rex-shares |
| 10 | Tuttle Capital Mgmt | stockanalysis.com | tuttle-capital-management |
| 11 | Defiance | stockanalysis.com | defiance |
| 12 | Simplify | stockanalysis.com | simplify |
| 13 | VolatilityShares | stockanalysis.com | volatility-shares |
| 14 | Tradr | stockanalysis.com | tradr |
| 15 | LeverageShares | stockanalysis.com | leverage-shares |
| 16 | Kurv | stockanalysis.com | kurv |

---

## Original Issuer URLs (Reference)

- ProShares — https://www.proshares.com/
- Direxion — https://www.direxion.com/
- BMO (ETFs) — https://bmogam.com/ca-en/products/exchange-traded-funds/
- GraniteShares — https://www.graniteshares.com/
- YieldMax — https://yieldmaxetfs.com/
- NEOS — https://neosfunds.com/
- Roundhill — https://www.roundhillinvestments.com/
- REX — https://www.rexshares.com/
- Tuttle — https://www.tuttlecap.com/
- Defiance — https://www.defianceetfs.com/
- Simplify — https://www.simplify.us/
- VolatilityShares — https://www.volatilityshares.com/
- Tradr — https://www.tradretfs.com/
- LeverageShares (U.S.) — https://leverageshares.com/us/
- Kurv — https://www.kurvinvest.com/