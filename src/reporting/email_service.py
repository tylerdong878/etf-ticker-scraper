"""
Email reporting service for ETF ticker scraper.
Generates HTML reports and sends them via Gmail SMTP.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from ..utils.models import DailySnapshot
from ..utils.config import (
    GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL,
    REPORTS_DIR, BASE_DIR
)
from ..utils.logger import get_logger

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
    changelog: list[dict]
) -> str:
    """
    Generate HTML report from snapshots and changelog data.
    
    Args:
        current_snapshot: Current day's snapshot
        previous_snapshot: Previous snapshot for comparison (can be None for first run)
        changelog: List of daily change entries for the week
    
    Returns:
        HTML string of the generated report
    """
    logger.info(f"Generating report for {current_snapshot.date}")
    
    # Set up Jinja2 environment
    template_dir = BASE_DIR / "src" / "reporting" / "templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report.html")
    
    # Parse date and get week number
    date_obj = datetime.strptime(current_snapshot.date, "%Y-%m-%d")
    week_number = date_obj.isocalendar()[1]
    
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
            
            scoreboard.append({
                'name': issuer_slug,
                'fund_count': current_issuer.total_funds,
                'total_aum': current_issuer.total_aum,
                'aum_change': aum_change,
                'aum_change_pct': aum_change_pct
            })
        
        # Merge REX issuers
        scoreboard = _merge_rex_issuers(scoreboard)
        
        # Sort by total AUM descending
        scoreboard.sort(key=lambda x: x['total_aum'], reverse=True)
    
    # Top AUM movers
    top_gainers = sorted(
        [m for m in all_aum_changes if m['change'] > 0],
        key=lambda x: x['change'],
        reverse=True
    )[:10]
    
    top_losers = sorted(
        [m for m in all_aum_changes if m['change'] < 0],
        key=lambda x: x['change']
    )[:10]
    
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
    
    # Render template
    html_content = template.render(
        report_date=current_snapshot.date,
        week_number=week_number,
        weekly_timeline=weekly_timeline,
        launches=all_launches,
        closures=all_closures,
        scoreboard=scoreboard,
        top_gainers=top_gainers,
        top_losers=top_losers,
        fund_count_changes=fund_count_changes,
        fund_list=fund_list,
        generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    
    logger.info("Report generated successfully")
    return html_content


def send_email(html_content: str, subject: str) -> bool:
    """
    Send HTML email via Gmail SMTP.
    
    Args:
        html_content: HTML content of the email
        subject: Email subject line
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not RECIPIENT_EMAIL:
        logger.error("Email credentials not configured in environment variables")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = GMAIL_USER
        msg['To'] = RECIPIENT_EMAIL
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Connect to Gmail SMTP server
        logger.info(f"Connecting to Gmail SMTP server...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {RECIPIENT_EMAIL}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def save_report_locally(html_content: str, date: str) -> None:
    """
    Save HTML report to local file system.
    
    Args:
        html_content: HTML content to save
        date: Date string in format "YYYY-MM-DD"
    """
    try:
        filepath = REPORTS_DIR / f"report_{date}.html"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Report saved locally to {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save report locally: {e}")
        raise