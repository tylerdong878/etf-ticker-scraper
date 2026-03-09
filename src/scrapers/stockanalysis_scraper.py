"""
StockAnalysis.com scraper for ETF provider data.
Handles 14 of 15 issuers by scraping their provider pages.
"""
import re
import time
import random
from typing import Optional
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
from bs4 import BeautifulSoup

from ..utils.config import STOCKANALYSIS_ISSUERS, SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX, HEADLESS
from ..utils.models import ETFund, IssuerSnapshot
from ..utils.logger import get_logger

logger = get_logger(__name__)


class StockAnalysisScraper:
    """Scraper for stockanalysis.com ETF provider pages."""
    
    def __init__(self):
        """Initialize Playwright browser."""
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    def __enter__(self):
        """Context manager entry - start browser."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=HEADLESS)
        self.page = self.browser.new_page()
        logger.info("Browser initialized")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup browser."""
        self.close()
        
    def close(self):
        """Clean up Playwright browser resources."""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser closed")
    
    def _parse_aum(self, aum_str: str) -> Optional[int]:
        """
        Parse AUM string to integer dollars.
        Examples: "204.39M" → 204390000, "7.54B" → 7540000000, "-" → None
        """
        if not aum_str or aum_str.strip() in ["-", "N/A", ""]:
            return None
            
        aum_str = aum_str.strip().upper()
        
        # Extract number and multiplier
        match = re.match(r'([\d,.]+)([BMK])?', aum_str)
        if not match:
            return None
            
        number_str, multiplier = match.groups()
        number = float(number_str.replace(',', ''))
        
        # Apply multiplier
        if multiplier == 'B':
            return int(number * 1_000_000_000)
        elif multiplier == 'M':
            return int(number * 1_000_000)
        elif multiplier == 'K':
            return int(number * 1_000)
        else:
            return int(number)
    
    def _parse_percentage(self, pct_str: str) -> Optional[float]:
        """
        Parse percentage string to decimal.
        Examples: "44.95%" → 0.4495, "-25.57%" → -0.2557, "-" → None
        """
        if not pct_str or pct_str.strip() in ["-", "N/A", ""]:
            return None
            
        pct_str = pct_str.strip().replace('%', '')
        try:
            return float(pct_str) / 100.0
        except ValueError:
            return None
    
    def _ensure_all_rows_loaded(self):
        """
        Ensure all table rows are loaded by checking for pagination or lazy loading.
        Some issuers have 100+ funds that may require scrolling or clicking "show all".
        """
        if not self.page:
            return
            
        try:
            # Wait for table to be present
            self.page.wait_for_selector('table', timeout=15000)
            
            # Check for "show all" or pagination controls
            # Common patterns: "Show 100", "Show All", pagination buttons
            show_all_selectors = [
                'button:has-text("Show All")',
                'button:has-text("Show 100")',
                'button:has-text("Show 200")',
                'select option:has-text("All")',
                'select option:has-text("100")',
                'select option:has-text("200")'
            ]
            
            for selector in show_all_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        logger.debug(f"Found show-all control: {selector}")
                        element.click()
                        time.sleep(1)  # Wait for table to reload
                        break
                except Exception:
                    continue
            
            # Scroll to bottom to trigger any lazy loading
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)
            
            # Wait a bit for any dynamic content to load
            self.page.wait_for_timeout(1000)
            
        except Exception as e:
            logger.warning(f"Error ensuring all rows loaded: {e}")
    
    def scrape_issuer(self, issuer_slug: str, url: str) -> IssuerSnapshot:
        """
        Scrape a single issuer's ETF data from stockanalysis.com.
        
        Args:
            issuer_slug: Issuer identifier (e.g., "defiance")
            url: Full URL to the issuer's provider page
            
        Returns:
            IssuerSnapshot containing all funds for this issuer
        """
        logger.info(f"Scraping {issuer_slug}: {url}")
        
        if not self.page:
            logger.error(f"Browser page not initialized for {issuer_slug}")
            return IssuerSnapshot(
                issuer_slug=issuer_slug,
                total_funds=0,
                total_aum=0,
                funds=[]
            )
        
        try:
            # Load the page
            self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Ensure all rows are loaded
            self._ensure_all_rows_loaded()
            
            # Get page content and parse with BeautifulSoup
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find the table
            table = soup.find('table')
            if not table:
                logger.error(f"No table found for {issuer_slug}")
                return IssuerSnapshot(
                    issuer_slug=issuer_slug,
                    total_funds=0,
                    total_aum=0,
                    funds=[]
                )
            
            # Parse table rows
            funds = []
            tbody = table.find('tbody')
            if not tbody:
                logger.error(f"No tbody found for {issuer_slug}")
                return IssuerSnapshot(
                    issuer_slug=issuer_slug,
                    total_funds=0,
                    total_aum=0,
                    funds=[]
                )
            
            rows = tbody.find_all('tr')
            logger.debug(f"Found {len(rows)} rows for {issuer_slug}")
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 6:
                        continue
                    
                    # Extract data from cells based on the HTML structure
                    # Symbol | Fund Name | Assets | Div. Yield | Exp. Ratio | Change 1Y
                    ticker_cell = cells[0]
                    ticker_link = ticker_cell.find('a')
                    ticker = ticker_link.text.strip() if ticker_link else ticker_cell.text.strip()
                    
                    name = cells[1].text.strip()
                    aum_str = cells[2].text.strip()
                    div_yield_str = cells[3].text.strip()
                    expense_ratio_str = cells[4].text.strip()
                    return_1y_str = cells[5].text.strip()
                    
                    # Parse values
                    aum = self._parse_aum(aum_str)
                    div_yield = self._parse_percentage(div_yield_str)
                    expense_ratio = self._parse_percentage(expense_ratio_str)
                    return_1y = self._parse_percentage(return_1y_str)
                    
                    # Create ETFund object
                    fund = ETFund(
                        ticker=ticker,
                        name=name,
                        issuer=issuer_slug,
                        aum=aum,
                        div_yield=div_yield,
                        expense_ratio=expense_ratio,
                        return_1y=return_1y
                    )
                    funds.append(fund)
                    
                except Exception as e:
                    logger.warning(f"Error parsing row for {issuer_slug}: {e}")
                    continue
            
            # Calculate totals
            total_funds = len(funds)
            total_aum = sum(fund.aum for fund in funds if fund.aum is not None)
            
            logger.info(f"Scraped {issuer_slug}: {total_funds} funds, ${total_aum:,.0f} AUM")
            
            return IssuerSnapshot(
                issuer_slug=issuer_slug,
                total_funds=total_funds,
                total_aum=total_aum,
                funds=funds
            )
            
        except Exception as e:
            logger.error(f"Failed to scrape {issuer_slug}: {e}")
            return IssuerSnapshot(
                issuer_slug=issuer_slug,
                total_funds=0,
                total_aum=0,
                funds=[]
            )
    
    def scrape_all(self) -> dict[str, IssuerSnapshot]:
        """
        Scrape all stockanalysis.com issuers.
        
        Returns:
            Dictionary mapping issuer_slug to IssuerSnapshot
        """
        results = {}
        
        logger.info(f"Starting scrape of {len(STOCKANALYSIS_ISSUERS)} issuers")
        
        for i, (issuer_slug, url) in enumerate(STOCKANALYSIS_ISSUERS.items(), 1):
            try:
                # Scrape the issuer
                snapshot = self.scrape_issuer(issuer_slug, url)
                results[issuer_slug] = snapshot
                
                # Random delay between requests (except after last one)
                if i < len(STOCKANALYSIS_ISSUERS):
                    delay = random.uniform(SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX)
                    logger.debug(f"Waiting {delay:.1f}s before next issuer...")
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Failed to scrape {issuer_slug}: {e}")
                # Continue to next issuer even if this one fails
                results[issuer_slug] = IssuerSnapshot(
                    issuer_slug=issuer_slug,
                    total_funds=0,
                    total_aum=0,
                    funds=[]
                )
        
        logger.info(f"Scraping complete: {len(results)} issuers processed")
        return results