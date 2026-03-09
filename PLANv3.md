# ETF Competitor Monitor - Plan v3

## Key Changes from v2

1. **stockanalysis.com only has 11 of 15 issuers** - not all providers are listed there
2. **4 issuers need custom scrapers** from their own websites:
   - Kurv → kurvinvest.com
   - Volatility Shares → volatilityshares.com
   - REX Shares → rexshares.com
   - Leverage Shares → leverageshares.com
3. **BMO dropped** - blocks headless browsers entirely (only 3 tiny US funds, not worth the effort)
4. **New launches page** added as auto-detection layer: stockanalysis.com/etf/list/new/

---

## Scraping Sources (Confirmed Working)

| # | Issuer | Source | URL |
|---|--------|--------|-----|
| 1 | ProShares | stockanalysis.com | https://stockanalysis.com/etf/provider/proshares/ |
| 2 | Direxion | stockanalysis.com | https://stockanalysis.com/etf/provider/direxion/ |
| 3 | GraniteShares | stockanalysis.com | https://stockanalysis.com/etf/provider/graniteshares/ |
| 4 | YieldMax | stockanalysis.com | https://stockanalysis.com/etf/provider/yieldmax/ |
| 5 | NEOS | stockanalysis.com | https://stockanalysis.com/etf/provider/neos/ |
| 6 | Roundhill | stockanalysis.com | https://stockanalysis.com/etf/provider/roundhill/ |
| 7 | REX Microsectors | stockanalysis.com | https://stockanalysis.com/etf/provider/rex-microsectors/ |
| 8 | Tuttle Capital Mgmt | stockanalysis.com | https://stockanalysis.com/etf/provider/tuttle-capital-management/ |
| 9 | Defiance | stockanalysis.com | https://stockanalysis.com/etf/provider/defiance/ |
| 10 | Simplify | stockanalysis.com | https://stockanalysis.com/etf/provider/simplify/ |
| 11 | Tradr | stockanalysis.com | https://stockanalysis.com/etf/provider/tradr/ |
| 12 | **Kurv** | **kurvinvest.com** | **https://www.kurvinvest.com/etfs** |
| 13 | **Volatility Shares** | **volatilityshares.com** | **https://www.volatilityshares.com/etf-product-list.php** |
| 14 | **REX Shares** | **rexshares.com** | **https://www.rexshares.com/home/all-funds/** |
| 15 | **Leverage Shares** | **leverageshares.com** | **https://leverageshares.com/us/all-etfs/** |
| **Bonus** | **New Launches** | **stockanalysis.com** | **https://stockanalysis.com/etf/list/new/** |

**Deferred:** BMO (blocks headless browsers — will figure out workaround later)

---

## Updated Architecture

### Project Structure
```
ticker-scraper/
├── src/
│   ├── scrapers/
│   │   ├── stockanalysis_scraper.py      # 11 issuers via stockanalysis.com
│   │   ├── kurv_scraper.py               # Kurv custom scraper
│   │   ├── volatilityshares_scraper.py   # Volatility Shares custom scraper
│   │   ├── rexshares_scraper.py          # REX Shares custom scraper
│   │   ├── leverageshares_scraper.py     # Leverage Shares custom scraper
│   │   └── new_launches_scraper.py       # Auto-detection from new launches page
│   ├── enrichment/
│   │   └── yahoo_finance.py              # yfinance for supplemental data
│   ├── detection/
│   │   └── change_detector.py            # Launch/closure detection
│   ├── reporting/
│   │   ├── email_service.py              # Gmail SMTP delivery
│   │   └── templates/
│   │       └── report.html               # Jinja2 email template
│   ├── utils/
│   │   ├── config.py                     # Issuer URLs, settings
│   │   ├── logger.py                     # Logging setup
│   │   └── models.py                     # Data models
│   └── main.py                           # Orchestration
├── data/
│   ├── snapshots/                        # Daily JSON snapshots
│   ├── changelog/                        # Weekly change logs
│   ├── logs/
│   ├── cache/
│   └── reports/
├── tests/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Updated Issuer Configuration

```python
ISSUERS = {
    # 11 issuers via stockanalysis.com
    "proshares": {
        "url": "https://stockanalysis.com/etf/provider/proshares/",
        "scraper": "stockanalysis"
    },
    "direxion": {
        "url": "https://stockanalysis.com/etf/provider/direxion/",
        "scraper": "stockanalysis"
    },
    "graniteshares": {
        "url": "https://stockanalysis.com/etf/provider/graniteshares/",
        "scraper": "stockanalysis"
    },
    "yieldmax": {
        "url": "https://stockanalysis.com/etf/provider/yieldmax/",
        "scraper": "stockanalysis"
    },
    "neos": {
        "url": "https://stockanalysis.com/etf/provider/neos/",
        "scraper": "stockanalysis"
    },
    "roundhill": {
        "url": "https://stockanalysis.com/etf/provider/roundhill/",
        "scraper": "stockanalysis"
    },
    "rex-microsectors": {
        "url": "https://stockanalysis.com/etf/provider/rex-microsectors/",
        "scraper": "stockanalysis"
    },
    "tuttle-capital-management": {
        "url": "https://stockanalysis.com/etf/provider/tuttle-capital-management/",
        "scraper": "stockanalysis"
    },
    "defiance": {
        "url": "https://stockanalysis.com/etf/provider/defiance/",
        "scraper": "stockanalysis"
    },
    "simplify": {
        "url": "https://stockanalysis.com/etf/provider/simplify/",
        "scraper": "stockanalysis"
    },
    "tradr": {
        "url": "https://stockanalysis.com/etf/provider/tradr/",
        "scraper": "stockanalysis"
    },
    
    # 4 custom scrapers
    "kurv": {
        "url": "https://www.kurvinvest.com/etfs",
        "scraper": "kurv"
    },
    "volatility-shares": {
        "url": "https://www.volatilityshares.com/etf-product-list.php",
        "scraper": "volatilityshares"
    },
    "rex-shares": {
        "url": "https://www.rexshares.com/home/all-funds/",
        "scraper": "rexshares"
    },
    "leverage-shares": {
        "url": "https://leverageshares.com/us/all-etfs/",
        "scraper": "leverageshares"
    }
}

# New launches detection
NEW_LAUNCHES_URL = "https://stockanalysis.com/etf/list/new/"
```

---

## Implementation Plan v3

### Phase 1: Core Scraper (Days 1-2) ✅
- [x] Set up project structure
- [x] Build `stockanalysis_scraper.py` for 11 issuers
- [x] Test against 2-3 issuers to validate

### Phase 2: Custom Scrapers (Days 3-5)
- [ ] Build `kurv_scraper.py`
- [ ] Build `volatilityshares_scraper.py`
- [ ] Build `rexshares_scraper.py`
- [ ] Build `leverageshares_scraper.py`
- [ ] Test all 15 issuers end-to-end

### Phase 3: New Launches Detection (Day 6)
- [ ] Build `new_launches_scraper.py`
- [ ] Parse stockanalysis.com/etf/list/new/ page
- [ ] Cross-reference with existing snapshots
- [ ] Flag truly new funds vs. existing ones

### Phase 4: Change Detection (Day 7)
- [ ] Build snapshot save/load system
- [ ] Implement diff logic
- [ ] Handle edge cases (ticker changes, scrape failures)

### Phase 5: yfinance Enrichment (Day 8)
- [ ] Pull supplemental data (NAV, volume, inception)
- [ ] Batch requests with rate limiting
- [ ] Cache results

### Phase 6: Email Reports (Days 9-10)
- [ ] Design HTML email template
- [ ] Implement Gmail SMTP sender
- [ ] Test email rendering

### Phase 7: Automation (Days 11-12)
- [ ] GitHub Actions workflows (daily scrape + weekly report)
- [ ] Install Playwright browsers in CI
- [ ] Store secrets
- [ ] Monitor first live runs

---

## Custom Scraper Requirements

Each custom scraper must implement the same interface as `StockAnalysisScraper`:

```python
class CustomScraper:
    def __init__(self):
        # Initialize browser
        pass
    
    def __enter__(self):
        # Context manager entry
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup
        pass
    
    def scrape_issuer(self, issuer_slug: str, url: str) -> IssuerSnapshot:
        # Scrape and return IssuerSnapshot
        pass
    
    def close(self):
        # Cleanup browser
        pass
```

---

## Next Steps

1. Update `config.py` to use new issuer structure
2. Build 4 custom scrapers
3. Build new launches scraper
4. Update main orchestration to handle multiple scraper types
5. Test full pipeline with all 15 issuers

---

## Notes

- BMO deferred indefinitely (headless browser blocking)
- New launches page provides early detection before daily scrapes
- REX is now split: REX Microsectors (stockanalysis) + REX Shares (custom)
- Total: 15 issuers tracked (down from 16 with BMO removed)