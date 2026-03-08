from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://stockanalysis.com/etf/provider/defiance/")
    page.wait_for_selector("table", timeout=15000)

    # Grab the raw HTML of the table
    table = page.query_selector("table")
    print(table.inner_html()[:3000])  # Print first 3000 chars to inspect structure

    browser.close()
