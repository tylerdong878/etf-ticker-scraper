"""
Main entry point for the ETF ticker scraper.
Orchestrates scraping, change detection, enrichment, and reporting.
"""
import argparse
import sys
from datetime import datetime, date, timedelta
from typing import Optional

from .scrapers.stockanalysis_scraper import StockAnalysisScraper
from .scrapers.direct_scrapers import scrape_all_direct
from .scrapers.new_launches_scraper import NewLaunchesScraper
from .detection.snapshot_manager import (
    save_snapshot, load_snapshot, load_latest_snapshot, get_previous_date
)
from .detection.change_detector import detect_changes, append_to_changelog, load_weekly_changelog
from .enrichment.yahoo_finance import enrich_funds
from .reporting.email_service import generate_report, send_email, save_report_locally
from .utils.models import DailySnapshot, IssuerSnapshot
from .utils.config import (
    ENRICH_WITH_YFINANCE, SEND_EMAIL, DRY_RUN, REPORT_FREQUENCY
)
from .utils.logger import get_logger

logger = get_logger(__name__)


def merge_rex_issuers(results: dict[str, IssuerSnapshot]) -> dict[str, IssuerSnapshot]:
    """
    Merge rex-microsectors and rex-shares into a single 'rex' entry.
    
    Args:
        results: Dictionary of issuer snapshots
    
    Returns:
        Updated dictionary with merged REX entry
    """
    rex_micro = results.pop("rex-microsectors", None)
    rex_shares = results.pop("rex-shares", None)
    
    if rex_micro and rex_shares:
        # Combine both REX issuers
        merged_funds = rex_micro.funds + rex_shares.funds
        merged_snapshot = IssuerSnapshot(
            issuer_slug="rex",
            total_funds=rex_micro.total_funds + rex_shares.total_funds,
            total_aum=rex_micro.total_aum + rex_shares.total_aum,
            funds=merged_funds
        )
        results["rex"] = merged_snapshot
        logger.info(f"Merged REX issuers: {merged_snapshot.total_funds} funds, ${merged_snapshot.total_aum:,.0f} AUM")
    elif rex_micro:
        rex_micro.issuer_slug = "rex"
        results["rex"] = rex_micro
    elif rex_shares:
        rex_shares.issuer_slug = "rex"
        results["rex"] = rex_shares
    
    return results


def scrape_mode(specific_issuer: Optional[str] = None) -> None:
    """
    Run the scraping workflow.
    
    Args:
        specific_issuer: If provided, only scrape this issuer (for testing)
    """
    logger.info("=" * 80)
    logger.info("SCRAPE MODE STARTED")
    logger.info("=" * 80)
    
    results = {}
    total_launches = 0
    total_closures = 0
    
    try:
        # Step 1 & 2: Scrape StockAnalysis and Direct issuers
        if specific_issuer:
            logger.info(f"Scraping specific issuer: {specific_issuer}")
            # Try to scrape just this one issuer
            # This is a simplified version for testing
            with StockAnalysisScraper() as scraper:
                from .utils.config import STOCKANALYSIS_ISSUERS
                if specific_issuer in STOCKANALYSIS_ISSUERS:
                    url = STOCKANALYSIS_ISSUERS[specific_issuer]
                    snapshot = scraper.scrape_issuer(specific_issuer, url)
                    results[specific_issuer] = snapshot
                else:
                    logger.error(f"Issuer {specific_issuer} not found in STOCKANALYSIS_ISSUERS")
        else:
            # Scrape all issuers
            logger.info("Scraping StockAnalysis issuers...")
            with StockAnalysisScraper() as scraper:
                stockanalysis_results = scraper.scrape_all()
                results.update(stockanalysis_results)
            
            logger.info("Scraping direct issuer websites...")
            direct_results = scrape_all_direct()
            results.update(direct_results)
        
        # Step 3: Check for new launches
        logger.info("Checking for new launches...")
        try:
            with NewLaunchesScraper() as launch_scraper:
                # Get issuer names for filtering
                issuer_names = [
                    "ProShares", "Direxion", "GraniteShares", "YieldMax", "NEOS",
                    "Roundhill", "REX", "Tuttle", "Defiance", "Simplify", "TRADR",
                    "Kurv", "Volatility Shares", "Leverage Shares"
                ]
                new_launches = launch_scraper.check_for_issuer_launches(issuer_names)
                if new_launches:
                    logger.info(f"Found {len(new_launches)} new launches from tracked issuers")
                    total_launches = len(new_launches)
        except Exception as e:
            logger.warning(f"Failed to check new launches: {e}")
        
        # Step 4: Merge REX issuers
        results = merge_rex_issuers(results)
        
        # Step 5: Enrich with yfinance if enabled
        if ENRICH_WITH_YFINANCE and not specific_issuer:
            logger.info("Enriching funds with yfinance data...")
            try:
                all_funds = []
                for issuer_snapshot in results.values():
                    all_funds.extend(issuer_snapshot.funds)
                
                enriched_funds = enrich_funds(all_funds)
                
                # Update the funds in each issuer snapshot
                fund_map = {f.ticker: f for f in enriched_funds}
                for issuer_snapshot in results.values():
                    for i, fund in enumerate(issuer_snapshot.funds):
                        if fund.ticker in fund_map:
                            issuer_snapshot.funds[i] = fund_map[fund.ticker]
                
            except Exception as e:
                logger.error(f"Failed to enrich with yfinance: {e}")
        
        # Step 6: Build DailySnapshot
        today = date.today().isoformat()
        snapshot = DailySnapshot(date=today, issuers=results)
        
        # Step 7: Save snapshot
        save_snapshot(snapshot)
        
        # Step 8: Detect changes
        logger.info("Detecting changes from previous snapshot...")
        try:
            previous_date = get_previous_date(today)
            if previous_date:
                previous_snapshot = load_snapshot(previous_date)
                if previous_snapshot:
                    changes = detect_changes(snapshot, previous_snapshot)
                    total_launches = len(changes.get("launches", []))
                    total_closures = len(changes.get("closures", []))
                    
                    # Append to changelog
                    append_to_changelog(changes, today)
                    logger.info(f"Changes detected: {total_launches} launches, {total_closures} closures")
                else:
                    logger.info("No previous snapshot found for comparison")
            else:
                logger.info("This is the first snapshot")
        except Exception as e:
            logger.error(f"Failed to detect changes: {e}")
        
        # Step 9: Log summary
        total_issuers = len(results)
        total_funds = sum(issuer.total_funds for issuer in results.values())
        total_aum = sum(issuer.total_aum for issuer in results.values())
        
        logger.info("=" * 80)
        logger.info(f"SCRAPE COMPLETE: {total_issuers} issuers | {total_funds} funds | "
                   f"${total_aum:,.0f} AUM | {total_launches} launches | {total_closures} closures")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Scrape mode failed: {e}", exc_info=True)
        # Save whatever we collected
        if results:
            today = date.today().isoformat()
            snapshot = DailySnapshot(date=today, issuers=results)
            save_snapshot(snapshot)
            logger.info("Saved partial snapshot despite errors")
        raise


def report_mode(dry_run: bool = False) -> None:
    """
    Run the reporting workflow.
    
    Args:
        dry_run: If True, skip sending email
    """
    logger.info("=" * 80)
    logger.info("REPORT MODE STARTED")
    logger.info("=" * 80)
    
    try:
        # Check if we should generate a report based on frequency
        today = datetime.now()
        is_monday = today.weekday() == 0
        
        should_report = False
        report_type = "full"
        
        if REPORT_FREQUENCY == "daily":
            should_report = True
            report_type = "daily"
        elif REPORT_FREQUENCY == "weekly":
            should_report = is_monday
            report_type = "weekly"
        elif REPORT_FREQUENCY == "both":
            should_report = True
            report_type = "weekly" if is_monday else "daily"
        else:
            logger.warning(f"Unknown REPORT_FREQUENCY: {REPORT_FREQUENCY}, defaulting to weekly")
            should_report = is_monday
            report_type = "weekly"
        
        if not should_report:
            logger.info(f"Skipping report (REPORT_FREQUENCY={REPORT_FREQUENCY}, today is not Monday)")
            return
        
        logger.info(f"Generating {report_type} report...")
        
        # Step 1: Load today's snapshot (or latest)
        current_snapshot = load_latest_snapshot()
        if not current_snapshot:
            logger.error("No snapshot found to generate report")
            return
        
        logger.info(f"Loaded snapshot for {current_snapshot.date}")
        
        # Step 2: Load snapshot from 7 days ago
        current_date = datetime.strptime(current_snapshot.date, "%Y-%m-%d")
        week_ago_date = (current_date - timedelta(days=7)).strftime("%Y-%m-%d")
        
        previous_snapshot = load_snapshot(week_ago_date)
        if not previous_snapshot:
            # Try to find nearest available snapshot
            logger.info(f"No snapshot found for {week_ago_date}, looking for nearest...")
            previous_date = get_previous_date(current_snapshot.date)
            if previous_date:
                previous_snapshot = load_snapshot(previous_date)
                logger.info(f"Using snapshot from {previous_date} for comparison")
        
        # Step 3: Load this week's changelog
        iso_year, iso_week, _ = current_date.isocalendar()
        week_str = f"{iso_year}-W{iso_week:02d}"
        changelog = load_weekly_changelog(week_str)
        
        logger.info(f"Loaded changelog for week {week_str}: {len(changelog)} entries")
        
        # Step 4: Generate HTML report
        html_content = generate_report(current_snapshot, previous_snapshot, changelog)
        
        # Step 5: Save report locally (always)
        save_report_locally(html_content, current_snapshot.date)
        
        # Step 6: Send email if enabled and not dry-run
        if SEND_EMAIL and not dry_run and not DRY_RUN:
            subject = f"ETF Ticker Scraper Report - {current_snapshot.date}"
            if report_type == "daily":
                subject = f"Daily ETF Update - {current_snapshot.date}"
            
            success = send_email(html_content, subject)
            if success:
                logger.info("Report email sent successfully")
            else:
                logger.error("Failed to send report email")
        else:
            if dry_run or DRY_RUN:
                logger.info("Dry run mode: skipping email send")
            else:
                logger.info("Email sending disabled in config")
        
        logger.info("=" * 80)
        logger.info("REPORT COMPLETE")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Report mode failed: {e}", exc_info=True)
        raise


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="ETF Ticker Scraper - Scrape, detect changes, and generate reports"
    )
    
    parser.add_argument(
        "--mode",
        choices=["scrape", "report", "both"],
        required=True,
        help="Operation mode: scrape data, generate report, or both"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without sending emails"
    )
    
    parser.add_argument(
        "--issuer",
        type=str,
        help="Scrape only a specific issuer (for testing)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "scrape":
            scrape_mode(specific_issuer=args.issuer)
        
        elif args.mode == "report":
            report_mode(dry_run=args.dry_run)
        
        elif args.mode == "both":
            scrape_mode(specific_issuer=args.issuer)
            report_mode(dry_run=args.dry_run)
        
        logger.info("All operations completed successfully")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()