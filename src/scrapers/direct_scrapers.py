"""
Direct website scrapers for issuers not available on stockanalysis.com.
Each issuer has its own scraper class with context manager support.
"""
import time
import random
from typing import Optional
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
from bs4 import BeautifulSoup

from ..utils.config import DIRECT_ISSUERS, SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX, HEADLESS
from ..utils.models import ETFund, IssuerSnapshot
from ..utils.logger import get_logger

logger = get_logger(__name__)


class KurvScraper:
    """Scraper for Kurv ETFs from https://www.kurvinvest.com/etfs"""
    
    def __init__(self):
        """Initialize Playwright browser."""
        self.url = DIRECT_ISSUERS["kurv"]
        self.issuer_slug = "kurv"
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    def __enter__(self):
        """Context manager entry - start browser."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=HEADLESS)
        self.page = self.browser.new_page()
        logger.info(f"Browser initialized for {self.issuer_slug}")
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
        logger.info(f"Browser closed for {self.issuer_slug}")
    
    def scrape(self) -> IssuerSnapshot:
        """
        Scrape Kurv ETFs.
        
        Table structure: Ticker | Name | Distribution Frequency | Gross Expense Ratio | 
                        Net Expense Ratio | Distribution Rate | 30-Day SEC Yield | Net Assets
        
        Returns:
            IssuerSnapshot with all Kurv funds
        """
        logger.info(f"Scraping {self.issuer_slug}: {self.url}")
        
        if not self.page:
            logger.error("Browser page not initialized")
            return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])
        
        try:
            self.page.goto(self.url, wait_until='domcontentloaded', timeout=60000)
            self.page.wait_for_selector('table', timeout=15000)
            self.page.wait_for_timeout(2000)  # Extra wait for dynamic content
            
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            table = soup.find('table')
            if not table:
                logger.error(f"No table found for {self.issuer_slug}")
                return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])
            
            funds = []
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                
                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 7:
                            continue
                        
                        # Name is in the text of first cell
                        name = cells[0].text.strip()
                        
                        # Ticker is extracted from href of <a> tag in first cell
                        ticker_cell = cells[0]
                        ticker_link = ticker_cell.find('a')
                        ticker = None
                        if ticker_link:
                            href = ticker_link.get('href')
                            # Extract from href like "/etf/kyld" -> "KYLD"
                            if href and isinstance(href, str):
                                ticker = href.split('/')[-1].upper()
                        
                        if not ticker:
                            continue
                        
                        # Expense Ratio is in column 2 (index 2)
                        expense_ratio_str = cells[2].text.strip().replace('%', '')
                        
                        # Net Assets (AUM) is in column 6 (index 6)
                        net_assets_str = cells[6].text.strip()
                        
                        # Parse expense ratio (e.g., "1.16%" -> 0.0116)
                        expense_ratio = None
                        try:
                            if expense_ratio_str:
                                expense_ratio = float(expense_ratio_str) / 100.0
                        except (ValueError, AttributeError):
                            pass
                        
                        # Parse AUM (e.g., "$37,444,045" -> 37444045)
                        aum = None
                        if net_assets_str and net_assets_str not in ["-", "N/A", ""]:
                            try:
                                # Remove $ and commas, then parse
                                clean_str = net_assets_str.replace('$', '').replace(',', '').strip()
                                aum = int(float(clean_str))
                            except (ValueError, AttributeError):
                                pass
                        
                        fund = ETFund(
                            ticker=ticker,
                            name=name,
                            issuer=self.issuer_slug,
                            aum=aum,
                            expense_ratio=expense_ratio
                        )
                        funds.append(fund)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing {self.issuer_slug} row: {e}")
                        continue
            
            total_aum = sum(f.aum for f in funds if f.aum)
            logger.info(f"Scraped {self.issuer_slug}: {len(funds)} funds, ${total_aum:,.0f} AUM")
            
            return IssuerSnapshot(
                issuer_slug=self.issuer_slug,
                total_funds=len(funds),
                total_aum=total_aum,
                funds=funds
            )
            
        except Exception as e:
            logger.error(f"Failed to scrape {self.issuer_slug}: {e}")
            return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])


class VolatilitySharesScraper:
    """Scraper for Volatility Shares ETFs from https://www.volatilityshares.com/etf-product-list.php"""
    
    def __init__(self):
        """Initialize Playwright browser."""
        self.url = DIRECT_ISSUERS["volatility-shares"]
        self.issuer_slug = "volatility-shares"
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    def __enter__(self):
        """Context manager entry - start browser."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=HEADLESS)
        self.page = self.browser.new_page()
        logger.info(f"Browser initialized for {self.issuer_slug}")
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
        logger.info(f"Browser closed for {self.issuer_slug}")
    
    def scrape(self) -> IssuerSnapshot:
        """
        Scrape Volatility Shares ETFs.
        
        Table structure: Ticker | Fund Name | Category | NAV | Net Assets | ...
        
        Returns:
            IssuerSnapshot with all Volatility Shares funds
        """
        logger.info(f"Scraping {self.issuer_slug}: {self.url}")
        
        if not self.page:
            logger.error("Browser page not initialized")
            return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])
        
        try:
            self.page.goto(self.url, wait_until='domcontentloaded', timeout=60000)
            self.page.wait_for_selector('table', timeout=15000)
            self.page.wait_for_timeout(2000)
            
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            table = soup.find('table')
            if not table:
                logger.error(f"No table found for {self.issuer_slug}")
                return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])
            
            funds = []
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                
                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 5:
                            continue
                        
                        ticker = cells[0].text.strip()
                        name = cells[1].text.strip()
                        nav_str = cells[3].text.strip()
                        net_assets_str = cells[4].text.strip()
                        
                        # Parse NAV
                        nav = None
                        try:
                            nav = float(nav_str.replace('$', '').replace(',', ''))
                        except (ValueError, AttributeError):
                            pass
                        
                        # Parse AUM (Net Assets)
                        aum = None
                        if net_assets_str and net_assets_str not in ["-", "N/A"]:
                            try:
                                net_assets_str = net_assets_str.replace('$', '').replace(',', '').upper()
                                if 'M' in net_assets_str:
                                    aum = int(float(net_assets_str.replace('M', '')) * 1_000_000)
                                elif 'K' in net_assets_str:
                                    aum = int(float(net_assets_str.replace('K', '')) * 1_000)
                                elif 'B' in net_assets_str:
                                    aum = int(float(net_assets_str.replace('B', '')) * 1_000_000_000)
                                else:
                                    aum = int(float(net_assets_str))
                            except (ValueError, AttributeError):
                                pass
                        
                        fund = ETFund(
                            ticker=ticker,
                            name=name,
                            issuer=self.issuer_slug,
                            aum=aum,
                            nav=nav
                        )
                        funds.append(fund)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing {self.issuer_slug} row: {e}")
                        continue
            
            total_aum = sum(f.aum for f in funds if f.aum)
            logger.info(f"Scraped {self.issuer_slug}: {len(funds)} funds, ${total_aum:,.0f} AUM")
            
            return IssuerSnapshot(
                issuer_slug=self.issuer_slug,
                total_funds=len(funds),
                total_aum=total_aum,
                funds=funds
            )
            
        except Exception as e:
            logger.error(f"Failed to scrape {self.issuer_slug}: {e}")
            return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])


class RexSharesScraper:
    """Scraper for REX Shares ETFs from https://www.rexshares.com/home/all-funds/"""
    
    def __init__(self):
        """Initialize Playwright browser."""
        self.url = DIRECT_ISSUERS["rex-shares"]
        self.issuer_slug = "rex-shares"
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    def __enter__(self):
        """Context manager entry - start browser."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=HEADLESS)
        self.page = self.browser.new_page()
        logger.info(f"Browser initialized for {self.issuer_slug}")
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
        logger.info(f"Browser closed for {self.issuer_slug}")
    
    def scrape(self) -> IssuerSnapshot:
        """
        Scrape REX Shares ETFs.
        
        Table structure: Ticker | Fund Name | Fund Page
        Note: This table only has ticker and name, no AUM data
        
        Returns:
            IssuerSnapshot with all REX Shares funds
        """
        logger.info(f"Scraping {self.issuer_slug}: {self.url}")
        
        if not self.page:
            logger.error("Browser page not initialized")
            return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])
        
        try:
            self.page.goto(self.url, wait_until='domcontentloaded', timeout=60000)
            self.page.wait_for_selector('table', timeout=15000)
            self.page.wait_for_timeout(2000)
            
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            table = soup.find('table')
            if not table:
                logger.error(f"No table found for {self.issuer_slug}")
                return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])
            
            funds = []
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                
                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 2:
                            continue
                        
                        # Ticker is in first cell, often as a link
                        ticker_cell = cells[0]
                        ticker_link = ticker_cell.find('a')
                        ticker = ticker_link.text.strip() if ticker_link else ticker_cell.text.strip()
                        
                        # Fund name is in second cell
                        name = cells[1].text.strip()
                        
                        fund = ETFund(
                            ticker=ticker,
                            name=name,
                            issuer=self.issuer_slug,
                            aum=None  # No AUM data in this table
                        )
                        funds.append(fund)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing {self.issuer_slug} row: {e}")
                        continue
            
            logger.info(f"Scraped {self.issuer_slug}: {len(funds)} funds (no AUM data)")
            
            return IssuerSnapshot(
                issuer_slug=self.issuer_slug,
                total_funds=len(funds),
                total_aum=0,
                funds=funds
            )
            
        except Exception as e:
            logger.error(f"Failed to scrape {self.issuer_slug}: {e}")
            return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])


class LeverageSharesScraper:
    """Scraper for Leverage Shares ETFs from https://leverageshares.com/us/all-etfs/"""
    
    def __init__(self):
        """Initialize Playwright browser."""
        self.url = DIRECT_ISSUERS["leverage-shares"]
        self.issuer_slug = "leverage-shares"
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    def __enter__(self):
        """Context manager entry - start browser."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=HEADLESS)
        self.page = self.browser.new_page()
        logger.info(f"Browser initialized for {self.issuer_slug}")
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
        logger.info(f"Browser closed for {self.issuer_slug}")
    
    def scrape(self) -> IssuerSnapshot:
        """
        Scrape Leverage Shares ETFs.
        
        Table structure: Ticker | Name | ... (various columns)
        
        Returns:
            IssuerSnapshot with all Leverage Shares funds
        """
        logger.info(f"Scraping {self.issuer_slug}: {self.url}")
        
        if not self.page:
            logger.error("Browser page not initialized")
            return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])
        
        try:
            self.page.goto(self.url, wait_until='domcontentloaded', timeout=60000)
            self.page.wait_for_selector('table', timeout=15000)
            self.page.wait_for_timeout(2000)
            
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            table = soup.find('table')
            if not table:
                logger.error(f"No table found for {self.issuer_slug}")
                return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])
            
            funds = []
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                
                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 2:
                            continue
                        
                        # First cell typically has ticker
                        ticker = cells[0].text.strip()
                        
                        # Second cell typically has name
                        name = cells[1].text.strip()
                        
                        # Skip empty rows
                        if not ticker or not name:
                            continue
                        
                        fund = ETFund(
                            ticker=ticker,
                            name=name,
                            issuer=self.issuer_slug,
                            aum=None  # May not have AUM in table
                        )
                        funds.append(fund)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing {self.issuer_slug} row: {e}")
                        continue
            
            logger.info(f"Scraped {self.issuer_slug}: {len(funds)} funds")
            
            return IssuerSnapshot(
                issuer_slug=self.issuer_slug,
                total_funds=len(funds),
                total_aum=0,
                funds=funds
            )
            
        except Exception as e:
            logger.error(f"Failed to scrape {self.issuer_slug}: {e}")
            return IssuerSnapshot(issuer_slug=self.issuer_slug, total_funds=0, total_aum=0, funds=[])


def scrape_all_direct() -> dict[str, IssuerSnapshot]:
    """
    Scrape all direct issuer websites using their individual scrapers.
    
    Returns:
        Dictionary mapping issuer_slug to IssuerSnapshot
    """
    results = {}
    scrapers = [
        KurvScraper(),
        VolatilitySharesScraper(),
        RexSharesScraper(),
        LeverageSharesScraper()
    ]
    
    logger.info(f"Starting scrape of {len(scrapers)} direct issuers")
    
    for i, scraper_class in enumerate(scrapers, 1):
        try:
            with scraper_class as scraper:
                snapshot = scraper.scrape()
                results[snapshot.issuer_slug] = snapshot
                
                # Random delay between requests (except after last one)
                if i < len(scrapers):
                    delay = random.uniform(SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX)
                    logger.debug(f"Waiting {delay:.1f}s before next issuer...")
                    time.sleep(delay)
                    
        except Exception as e:
            logger.error(f"Failed to scrape with {scraper_class.__class__.__name__}: {e}")
            # Add empty snapshot for failed scraper
            issuer_slug = getattr(scraper_class, 'issuer_slug', 'unknown')
            results[issuer_slug] = IssuerSnapshot(
                issuer_slug=issuer_slug,
                total_funds=0,
                total_aum=0,
                funds=[]
            )
    
    logger.info(f"Direct scraping complete: {len(results)} issuers processed")
    return results