"""
Email reporting service for ETF ticker scraper.
Generates HTML reports and sends them via Gmail SMTP with PDF attachment.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from ..utils.models import DailySnapshot
from ..utils.config import (
    GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL,
    REPORTS_DIR, BASE_DIR, WATCHLIST_TICKERS
)
from ..utils.logger import get_logger
from .gemini_insights import get_etf_insights, get_all_stock_insights

logger = get_logger(__name__)


def _merge_rex_issuers(scoreboard: list[dict]) -> list[dict]:
    """
    Merge REX Microsectors and REX Shares into a single "REX" row.
    
    Args:
        scoreboard: List of issuer scoreboard dictionaries
    
    Returns:
        Merged scoreboard with combined REX entry
    """
    rex_micro = None
    rex_shares = None
    other_issuers = []
    
    for issuer in scoreboard:
        if issuer['name'].lower() == 'rex-microsectors':
            rex_micro = issuer
        elif issuer['name'].lower() == 'rex-shares':
            rex_shares = issuer
        else:
            other_issuers.append(issuer)
    
    # If both REX issuers exist, merge them
    if rex_micro and rex_shares:
        merged_rex = {
            'name': 'REX',
            'fund_count': rex_micro['fund_count'] + rex_shares['fund_count'],
            'total_aum': rex_micro['total_aum'] + rex_shares['total_aum'],
            'aum_change': rex_micro['aum_change'] + rex_shares['aum_change'],
            'aum_change_pct': (
                (rex_micro['total_aum'] + rex_shares['total_aum'] - 
                 rex_micro['aum_change'] - rex_shares['aum_change']) /
                (rex_micro['total_aum'] + rex_shares['total_aum'] - 
                 rex_micro['aum_change'] - rex_shares['aum_change'])
                if (rex_micro['total_aum'] + rex_shares['total_aum'] - 
                    rex_micro['aum_change'] - rex_shares['aum_change']) != 0
                else 0
            )
        }
        other_issuers.append(merged_rex)
    elif rex_micro:
        rex_micro['name'] = 'REX'
        other_issuers.append(rex_micro)
    elif rex_shares:
        rex_shares['name'] = 'REX'
        other_issuers.append(rex_shares)
    
    return other_issuers


def generate_report(
    current_snapshot: DailySnapshot,
    previous_snapshot: Optional[DailySnapshot],
    changelog: list[dict],
    is_email_body: bool = False,
    etf_insights: Optional[list] = None,
    stock_insights: Optional[list] = None
) -> str:
    """
    Generate HTML report from snapshots and changelog data.

    Args:
        current_snapshot: Current day's snapshot
        previous_snapshot: Previous snapshot for comparison (can be None for first run)
        changelog: List of daily change entries for the week
        is_email_body: If True, excludes Full Fund List section for email body
        etf_insights: Pre-fetched ETF insights (fetched if None)
        stock_insights: Pre-fetched stock insights (fetched if None)
    
    Returns:
        HTML string of the generated report
    """
    logger.info(f"Generating report for {current_snapshot.date}")
    
    # Set up Jinja2 environment
    template_dir = BASE_DIR / "src" / "reporting" / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))

    def compact_aum(value):
        """Format AUM as compact string: $1.31B, $160M, $45K"""
        if value is None:
            return "N/A"
        abs_val = abs(value)
        sign = "-" if value < 0 else ""
        if abs_val >= 1_000_000_000:
            return f"{sign}${abs_val / 1_000_000_000:,.2f}B"
        elif abs_val >= 1_000_000:
            return f"{sign}${abs_val / 1_000_000:,.2f}M"
        elif abs_val >= 1_000:
            return f"{sign}${abs_val / 1_000:,.1f}K"
        else:
            return f"{sign}${abs_val:,.0f}"

    env.filters['compact_aum'] = compact_aum
    template = env.get_template("report.html")
    
    # Parse date and get week number with date range
    date_obj = datetime.strptime(current_snapshot.date, "%Y-%m-%d")
    # If snapshot is Monday, report covers the previous week
    ref_date = date_obj - timedelta(days=7) if date_obj.weekday() == 0 else date_obj
    week_number = ref_date.isocalendar()[1]
    week_start = ref_date - timedelta(days=ref_date.weekday())  # Monday
    week_end = week_start + timedelta(days=4)  # Friday
    if week_start.month == week_end.month:
        week_date_range = f"{week_start.strftime('%b %d')}–{week_end.strftime('%d')}"
    else:
        week_date_range = f"{week_start.strftime('%b %d')}–{week_end.strftime('%b %d')}"
    
    # Build weekly timeline from changelog
    weekly_timeline = []
    for entry in changelog:
        changes = entry.get('changes', {})
        weekly_timeline.append({
            'date': entry['date'],
            'launches': len(changes.get('launches', [])),
            'closures': len(changes.get('closures', [])),
            'aum_changes': len(changes.get('aum_changes', []))
        })
    
    # Aggregate all launches and closures from changelog
    all_launches = []
    all_closures = []
    all_aum_changes = []
    
    for entry in changelog:
        changes = entry.get('changes', {})
        all_launches.extend(changes.get('launches', []))
        all_closures.extend(changes.get('closures', []))
        all_aum_changes.extend(changes.get('aum_changes', []))
    
    # Build issuer scoreboard
    scoreboard = []
    if previous_snapshot:
        for issuer_slug, current_issuer in current_snapshot.issuers.items():
            previous_issuer = previous_snapshot.issuers.get(issuer_slug)
            
            if previous_issuer:
                aum_change = current_issuer.total_aum - previous_issuer.total_aum
                aum_change_pct = (
                    aum_change / previous_issuer.total_aum 
                    if previous_issuer.total_aum != 0 else 0
                )
            else:
                aum_change = 0
                aum_change_pct = 0
            
            # AUM-weighted average fee and total estimated annual revenue
            funds_with_fee = [f for f in current_issuer.funds if f.aum and f.expense_ratio]
            weighted_aum = sum(f.aum for f in funds_with_fee)
            avg_fee = (
                sum(f.aum * f.expense_ratio for f in funds_with_fee) / weighted_aum
                if weighted_aum else None
            )
            total_revenue = sum(f.aum * f.expense_ratio for f in funds_with_fee) if funds_with_fee else None

            scoreboard.append({
                'name': issuer_slug,
                'fund_count': current_issuer.total_funds,
                'total_aum': current_issuer.total_aum,
                'aum_change': aum_change,
                'aum_change_pct': aum_change_pct,
                'avg_fee': avg_fee,
                'total_revenue': total_revenue
            })
        
        # Merge REX issuers
        scoreboard = _merge_rex_issuers(scoreboard)
        
        # Sort by total AUM descending
        scoreboard.sort(key=lambda x: x['total_aum'], reverse=True)
    
    # Top AUM movers — net weekly change (current vs previous snapshot)
    aum_movers = []
    if previous_snapshot:
        for issuer_slug, current_issuer in current_snapshot.issuers.items():
            previous_issuer = previous_snapshot.issuers.get(issuer_slug)
            if not previous_issuer:
                continue
            prev_funds = {f.ticker: f for f in previous_issuer.funds}
            for fund in current_issuer.funds:
                prev_fund = prev_funds.get(fund.ticker)
                if prev_fund and fund.aum is not None and prev_fund.aum is not None:
                    change = fund.aum - prev_fund.aum
                    if change != 0:
                        aum_movers.append({
                            'ticker': fund.ticker,
                            'name': fund.name,
                            'issuer': issuer_slug,
                            'prev_aum': prev_fund.aum,
                            'current_aum': fund.aum,
                            'change': change,
                            'change_pct': change / prev_fund.aum,
                        })

    top_gainers = sorted(
        [m for m in aum_movers if m['change'] > 0],
        key=lambda x: x['change'],
        reverse=True
    )[:20]

    top_losers = sorted(
        [m for m in aum_movers if m['change'] < 0],
        key=lambda x: x['change']
    )[:20]
    
    # Fund count changes
    fund_count_changes = []
    if previous_snapshot:
        for issuer_slug, current_issuer in current_snapshot.issuers.items():
            previous_issuer = previous_snapshot.issuers.get(issuer_slug)
            
            if previous_issuer:
                count_change = current_issuer.total_funds - previous_issuer.total_funds
                if count_change != 0:
                    fund_count_changes.append({
                        'issuer': issuer_slug,
                        'prev_count': previous_issuer.total_funds,
                        'current_count': current_issuer.total_funds,
                        'change': count_change
                    })
    
    # Full fund list grouped by issuer
    fund_list = []
    for issuer_slug, issuer_snapshot in current_snapshot.issuers.items():
        # Sort funds by AUM descending
        sorted_funds = sorted(
            issuer_snapshot.funds,
            key=lambda f: f.aum if f.aum else 0,
            reverse=True
        )
        
        fund_list.append({
            'name': issuer_slug,
            'fund_count': len(sorted_funds),
            'funds': sorted_funds
        })
    
    # Sort issuers by total AUM descending
    fund_list.sort(
        key=lambda x: sum(f.aum for f in x['funds'] if f.aum),
        reverse=True
    )
    
    # Fetch Gemini insights if not provided (gracefully skipped if API key missing or call fails)
    if etf_insights is None:
        etf_insights = get_etf_insights()
    if stock_insights is None:
        stock_insights = get_all_stock_insights(WATCHLIST_TICKERS) if WATCHLIST_TICKERS else []

    # Render template
    html_content = template.render(
        report_date=current_snapshot.date,
        week_number=week_number,
        week_date_range=week_date_range,
        weekly_timeline=weekly_timeline,
        launches=all_launches,
        closures=all_closures,
        scoreboard=scoreboard,
        top_gainers=top_gainers,
        top_losers=top_losers,
        fund_count_changes=fund_count_changes,
        fund_list=fund_list,
        etf_insights=etf_insights,
        stock_insights=stock_insights,
        generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        is_email_body=is_email_body
    )
    
    logger.info("Report generated successfully")
    return html_content


def generate_pdf(html_content: str) -> bytes:
    """
    Convert HTML content to PDF bytes.
    
    Args:
        html_content: HTML string to convert
    
    Returns:
        PDF file as bytes
    """
    try:
        # Create PDF from HTML string
        pdf_file = BytesIO()
        HTML(string=html_content).write_pdf(pdf_file)
        pdf_bytes = pdf_file.getvalue()
        
        logger.info(f"Generated PDF: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        raise


def send_email(
    current_snapshot: DailySnapshot,
    previous_snapshot: Optional[DailySnapshot],
    changelog: list[dict],
    subject: str,
    etf_insights: Optional[list] = None,
    stock_insights: Optional[list] = None
) -> bool:
    """
    Send email with executive summary HTML body and full report PDF attachment.
    
    Args:
        current_snapshot: Current day's snapshot
        previous_snapshot: Previous snapshot for comparison
        changelog: List of daily change entries
        subject: Email subject line
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not RECIPIENT_EMAIL:
        logger.error("Email credentials not configured in environment variables")
        return False
    
    try:
        # Fetch Gemini insights if not provided
        if etf_insights is None or stock_insights is None:
            logger.info("Fetching Gemini insights...")
            if etf_insights is None:
                etf_insights = get_etf_insights()
            if stock_insights is None:
                stock_insights = get_all_stock_insights(WATCHLIST_TICKERS) if WATCHLIST_TICKERS else []

        # Generate email body (executive summary without full fund list)
        logger.info("Generating executive summary for email body...")
        email_body_html = generate_report(
            current_snapshot,
            previous_snapshot,
            changelog,
            is_email_body=True,
            etf_insights=etf_insights,
            stock_insights=stock_insights
        )

        # Generate full report HTML for PDF
        logger.info("Generating full report for PDF attachment...")
        full_report_html = generate_report(
            current_snapshot,
            previous_snapshot,
            changelog,
            is_email_body=False,
            etf_insights=etf_insights,
            stock_insights=stock_insights
        )
        
        # Convert full report to PDF
        logger.info("Converting full report to PDF...")
        pdf_bytes = generate_pdf(full_report_html)
        
        # Parse recipient emails (comma-separated)
        recipient_list = [email.strip() for email in RECIPIENT_EMAIL.split(',')]
        
        # Create multipart message
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = GMAIL_USER
        msg['To'] = RECIPIENT_EMAIL  # Display all recipients in email header
        
        # Attach email body HTML
        html_part = MIMEText(email_body_html, 'html')
        msg.attach(html_part)
        
        # Attach PDF
        pdf_filename = f"ETF_Report_{current_snapshot.date}.pdf"
        pdf_attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
        msg.attach(pdf_attachment)
        
        logger.info(f"Email prepared with PDF attachment: {pdf_filename}")
        
        # Connect to Gmail SMTP server
        logger.info(f"Connecting to Gmail SMTP server...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipient_list, msg.as_string())
        
        logger.info(f"Email sent successfully to {len(recipient_list)} recipient(s): {RECIPIENT_EMAIL}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def save_report_locally(html_content: str, date: str) -> None:
    """
    Save HTML and PDF reports to local file system.
    
    Args:
        html_content: HTML content to save
        date: Date string in format "YYYY-MM-DD"
    """
    try:
        # Save HTML file
        html_filepath = REPORTS_DIR / f"report_{date}.html"
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"HTML report saved to {html_filepath}")
        
        # Save PDF file
        pdf_filepath = REPORTS_DIR / f"report_{date}.pdf"
        pdf_bytes = generate_pdf(html_content)
        with open(pdf_filepath, 'wb') as f:
            f.write(pdf_bytes)
        logger.info(f"PDF report saved to {pdf_filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save report locally: {e}")
        raise