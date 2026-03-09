"""
New Launches scraper for stockanalysis.com.
Scrapes the 100 most recently launched ETFs.
"""
from datetime import datetime
from typing import Optional
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
from bs4 import BeautifulSoup

from ..utils.config import NEW_LAUNCHES_URL, HEADLESS
from ..utils.logger import get_logger

logger = get_logger(__name__)


class NewLaunchesScraper:
    """Scraper for stockanalysis.com new ETF launches page."""
    
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
        logger.info("Browser initialized for new launches scraper")
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
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse date string to ISO format.
        Examples: "Mar 5, 2026" → "2026-03-05", "Jan 15, 2025" → "2025-01-15"
        """
        if not date_str or date_str.strip() in ["-", "N/A", ""]:
            return None
            
        try:
            # Parse date like "Mar 5, 2026"
            date_obj = datetime.strptime(date_str.strip(), "%b %d, %Y")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            logger.warning(f"Could not parse date: {date_str}")
            return None
    
    def _parse_price(self, price_str: str) -> Optional[float]:
        """
        Parse price string to float.
        Examples: "$24.76" → 24.76, "$1,234.56" → 1234.56
        """
        if not price_str or price_str.strip() in ["-", "N/A", ""]:
            return None
            
        try:
            # Remove $ and commas, then convert to float
            price_clean = price_str.strip().replace('$', '').replace(',', '')
            return float(price_clean)
        except ValueError:
            logger.warning(f"Could not parse price: {price_str}")
            return None
    
    def scrape(self) -> list[dict]:
        """
        Scrape all new ETF launches from stockanalysis.com.
        
        Returns:
            List of dictionaries with keys: date, ticker, name, price
        """
        logger.info(f"Scraping new launches: {NEW_LAUNCHES_URL}")
        
        if not self.page:
            logger.error("Browser page not initialized")
            return []
        
        try:
            # Load the page
            self.page.goto(NEW_LAUNCHES_URL, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for table to be present
            self.page.wait_for_selector('table', timeout=15000)
            
            # Get page content and parse with BeautifulSoup
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find the table
            table = soup.find('table')
            if not table:
                logger.error("No table found on new launches page")
                return []
            
            # Parse table rows
            launches = []
            tbody = table.find('tbody')
            if not tbody:
                logger.error("No tbody found in new launches table")
                return []
            
            rows = tbody.find_all('tr')
            logger.debug(f"Found {len(rows)} new launch rows")
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 4:
                        continue
                    
                    # Extract data from cells
                    # Columns: Inception (date) | Symbol | Fund Name | Stock Price | % Change
                    date_str = cells[0].text.strip()
                    
                    # Symbol cell has class 'sym' with ticker link
                    ticker_cell = cells[1]
                    ticker_link = ticker_cell.find('a')
                    ticker = ticker_link.text.strip() if ticker_link else ticker_cell.text.strip()
                    
                    # Fund name cell has class 'slw'
                    name = cells[2].text.strip()
                    
                    # Stock price
                    price_str = cells[3].text.strip()
                    
                    # Parse values
                    date = self._parse_date(date_str)
                    price = self._parse_price(price_str)
                    
                    # Create launch dict
                    launch = {
                        "date": date,
                        "ticker": ticker,
                        "name": name,
                        "price": price
                    }
                    launches.append(launch)
                    
                except Exception as e:
                    logger.warning(f"Error parsing new launch row: {e}")
                    continue
            
            logger.info(f"Scraped {len(launches)} new launches")
            return launches
            
        except Exception as e:
            logger.error(f"Failed to scrape new launches: {e}")
            return []
    
    def check_for_issuer_launches(self, issuer_names: list[str]) -> list[dict]:
        """
        Check for new launches from specific issuers.
        
        Args:
            issuer_names: List of issuer names to filter for (e.g., ["Defiance", "Kurv"])
        
        Returns:
            List of launch dictionaries matching any of the issuer names
        """
        logger.info(f"Checking for launches from issuers: {issuer_names}")
        
        # Scrape all launches
        all_launches = self.scrape()
        
        if not all_launches:
            return []
        
        # Filter for matching issuers (case-insensitive)
        issuer_names_lower = [name.lower() for name in issuer_names]
        matching_launches = []
        
        for launch in all_launches:
            fund_name_lower = launch["name"].lower()
            
            # Check if any issuer name appears in the fund name
            for issuer_name in issuer_names_lower:
                if issuer_name in fund_name_lower:
                    matching_launches.append(launch)
                    logger.debug(f"Found match: {launch['ticker']} - {launch['name']}")
                    break
        
        logger.info(f"Found {len(matching_launches)} launches from tracked issuers")
        return matching_launches