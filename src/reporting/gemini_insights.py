"""
Fetches weekly ETF industry insights using the Gemini API with Google Search grounding.
"""
import json
from datetime import datetime, timedelta

from ..utils.config import GEMINI_API_KEY
from ..utils.logger import get_logger

logger = get_logger(__name__)


def get_etf_insights() -> list[dict] | None:
    """
    Returns a list of 5 dicts, each with 'point', 'source_title', and 'source_url',
    covering notable ETF industry news from the past week.
    Returns None on failure so the report still generates without this section.
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, skipping ETF insights")
        return None

    try:
        from google import genai
        from google.genai import types

        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        date_context = f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"

        client = genai.Client(api_key=GEMINI_API_KEY)

        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.2
        )

        prompt = (
            f"Search for the 5 most notable ETF industry news stories from the past week "
            f"({date_context}). Focus on new ETF launches, large AUM movements, regulatory changes, "
            f"or major market themes. "
            f"Respond with ONLY a valid JSON array, no markdown, no code fences, no extra text. "
            f"The array must contain exactly 5 objects, each with these fields: "
            f"'point' (one concise sentence summarizing the news), "
            f"'source_title' (the publication or article title), "
            f"'source_url' (the direct URL to the article). "
            f"Example: "
            f'[{{"point": "...", "source_title": "...", "source_url": "https://..."}}]'
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config
        )

        # Strip markdown code fences if present
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        insights = json.loads(text)

        if not isinstance(insights, list):
            logger.warning("Gemini returned unexpected format for insights")
            return None

        logger.info(f"Successfully fetched {len(insights)} ETF insights from Gemini")
        return insights[:5]

    except Exception as e:
        logger.warning(f"Gemini API call failed, skipping insights section: {e}")
        return None
