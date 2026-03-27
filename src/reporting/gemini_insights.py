"""
Fetches weekly ETF industry insights and stock-specific updates using the Gemini API
with Google Search grounding.
"""
import json
from datetime import datetime, timedelta

from ..utils.config import GEMINI_API_KEY
from ..utils.logger import get_logger

logger = get_logger(__name__)


REQUIRED_FIELDS = {"point", "source_title", "source_url"}
OPTIONAL_FIELDS = {"source_date"}


def _parse_json_response(text: str) -> list | None:
    """Extract and parse a JSON array from a Gemini response, handling code fences and preamble."""
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        parts = text.split("```")
        # parts[1] is the content between first and second fence
        inner = parts[1] if len(parts) > 1 else text
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()

    # Try direct parse first
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return _validate_items(result)
        # If it's a dict, look for the first list value
        if isinstance(result, dict):
            for v in result.values():
                if isinstance(v, list):
                    return _validate_items(v)
    except json.JSONDecodeError:
        pass

    # Fall back: find the first '[' ... ']' substring and parse that
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, list):
                return _validate_items(result)
        except json.JSONDecodeError:
            pass

    return None


def _validate_items(items: list) -> list | None:
    """Filter items to only those that are dicts with all required fields populated."""
    valid = []
    for item in items:
        if not isinstance(item, dict):
            logger.debug("Skipping non-dict item: %s", item)
            continue
        missing = REQUIRED_FIELDS - item.keys()
        if missing:
            logger.debug("Skipping item missing fields %s: %s", missing, item)
            continue
        empty = [f for f in REQUIRED_FIELDS if not isinstance(item[f], str) or not item[f].strip()]
        if empty:
            logger.debug("Skipping item with empty/non-string fields %s: %s", empty, item)
            continue
        valid.append(item)
    return valid if valid else None


def _build_client():
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2
    )
    return client, config


def _date_context() -> str:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    return f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"


def get_etf_insights() -> list[dict] | None:
    """
    Returns up to 5 notable ETF industry news items from the past week.
    Each item has 'point', 'source_title', and 'source_url'.
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, skipping ETF insights")
        return None

    try:
        client, config = _build_client()
        date_context = _date_context()

        prompt = (
            f"RESPONSE FORMAT — CRITICAL: Your entire response must be ONLY a valid JSON array. "
            f"No markdown. No code fences. No ```json. No explanation. No preamble. No trailing text. "
            f"The very first character of your response must be '[' and the very last must be ']'. "
            f"Do NOT wrap the array in an object like {{\"results\": [...]}}. Return the array directly.\n\n"
            f"Each element of the array must be a JSON object with EXACTLY these 4 keys "
            f"(copy the key names exactly — lowercase, underscores, no variations):\n"
            f'  "point"       — string — one concise sentence summarizing the news\n'
            f'  "source_title" — string — the publication name or article headline\n'
            f'  "source_url"  — string — the full URL starting with https://\n'
            f'  "source_date" — string — publication date as YYYY-MM-DD, or "" if unknown\n\n'
            f"No other keys are allowed. All values must be strings (never null, never a number).\n\n"
            f"EXAMPLE of a perfectly formatted response (2 items shown, return 5):\n"
            f'[{{"point": "BlackRock launched a Bitcoin spot ETF with $1B in first-day inflows.", "source_title": "Reuters", "source_url": "https://reuters.com/markets/etf-launch", "source_date": "2026-03-20"}}, '
            f'{{"point": "SEC approved new leveraged ETF rules limiting daily reset products.", "source_title": "Wall Street Journal", "source_url": "https://wsj.com/articles/sec-etf-rules", "source_date": "2026-03-22"}}]\n\n"'
            f"TASK: Search for the 5 most notable ETF industry news stories from the past week "
            f"({date_context}). Focus on new ETF launches, large AUM movements, regulatory changes, "
            f"or major market themes. Return exactly 5 objects in the array."
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config
        )

        insights = _parse_json_response(response.text)
        if not insights:
            logger.warning("Gemini returned unexpected format for ETF insights. Raw response: %s", response.text[:1500])
            return None

        logger.info(f"Successfully fetched {len(insights)} ETF insights from Gemini")
        return insights[:5]

    except Exception as e:
        logger.warning(f"Gemini ETF insights call failed: {e}")
        return None


def get_stock_insights(ticker: str) -> list[dict] | None:
    """
    Returns up to 5 notable news items about a specific stock/company from the past week.
    Each item has 'point', 'source_title', and 'source_url'.
    """
    if not GEMINI_API_KEY:
        return None

    try:
        client, config = _build_client()
        date_context = _date_context()

        prompt = (
            f"RESPONSE FORMAT — CRITICAL: Your entire response must be ONLY a valid JSON array. "
            f"No markdown. No code fences. No ```json. No explanation. No preamble. No trailing text. "
            f"The very first character of your response must be '[' and the very last must be ']'. "
            f"Do NOT wrap the array in an object like {{\"results\": [...]}}. Return the array directly.\n\n"
            f"Each element of the array must be a JSON object with EXACTLY these 4 keys "
            f"(copy the key names exactly — lowercase, underscores, no variations):\n"
            f'  "point"       — string — one concise sentence summarizing the news\n'
            f'  "source_title" — string — the publication name or article headline\n'
            f'  "source_url"  — string — the full URL starting with https://\n'
            f'  "source_date" — string — publication date as YYYY-MM-DD, or "" if unknown\n\n'
            f"No other keys are allowed. All values must be strings (never null, never a number).\n\n"
            f"EXAMPLE of a perfectly formatted response (2 items shown, return up to 5):\n"
            f'[{{"point": "{ticker} reported record quarterly earnings beating analyst estimates.", "source_title": "Bloomberg", "source_url": "https://bloomberg.com/news/example", "source_date": "2026-03-20"}}, '
            f'{{"point": "{ticker} announced a major partnership with a cloud provider.", "source_title": "CNBC", "source_url": "https://cnbc.com/2026/03/22/example.html", "source_date": "2026-03-22"}}]\n\n"'
            f"TASK: Search for the most important news stories about {ticker} (the stock/company) "
            f"from the past week ({date_context}). "
            f"Focus on earnings, product launches, executive changes, regulatory news, "
            f"major partnerships, or anything significant that investors should know. "
            f"Return up to 5 objects (fewer if there are not 5 notable stories)."
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config
        )

        insights = _parse_json_response(response.text)
        if not insights:
            logger.warning("Gemini returned unexpected format for %s insights. Raw response: %s", ticker, response.text[:1500])
            return None

        logger.info(f"Successfully fetched {len(insights)} insights for {ticker}")
        return insights[:5]

    except Exception as e:
        logger.warning(f"Gemini stock insights call failed for {ticker}: {e}")
        return None


def get_all_stock_insights(tickers: list[str]) -> list[dict]:
    """
    Returns a list of {ticker, insights} dicts for each ticker in the watchlist.
    Tickers that fail are skipped silently.
    """
    results = []
    for ticker in tickers:
        insights = get_stock_insights(ticker)
        if insights:
            results.append({'ticker': ticker, 'insights': insights})
    return results
