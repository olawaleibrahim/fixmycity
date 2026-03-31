"""
RSS feed ingestion for urban hazard news.

No API keys required — all feeds are public.
Uses feedparser to parse Atom/RSS.

Sources:
  - BBC local news (per region)
  - The Guardian: environment, cities
  - GOV.UK news tagged with relevant topics
"""

import hashlib
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
from sqlalchemy.orm import Session

from app.models.event import RawPost

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    # BBC regional news
    {
        "url": "https://feeds.bbci.co.uk/news/england/rss.xml",
        "label": "BBC England",
    },
    {
        "url": "https://feeds.bbci.co.uk/news/england/london/rss.xml",
        "label": "BBC London",
    },
    {
        "url": "https://feeds.bbci.co.uk/news/england/manchester/rss.xml",
        "label": "BBC Manchester",
    },
    {
        "url": "https://feeds.bbci.co.uk/news/england/birmingham_and_black_country/rss.xml",
        "label": "BBC Birmingham",
    },
    {
        "url": "https://feeds.bbci.co.uk/news/england/leeds_and_west_yorkshire/rss.xml",
        "label": "BBC Leeds",
    },
    {
        "url": "https://feeds.bbci.co.uk/news/england/bristol/rss.xml",
        "label": "BBC Bristol",
    },
    # The Guardian
    {
        "url": "https://www.theguardian.com/environment/flooding/rss",
        "label": "Guardian Flooding",
    },
    {
        "url": "https://www.theguardian.com/cities/rss",
        "label": "Guardian Cities",
    },
    {
        "url": "https://www.theguardian.com/environment/pollution/rss",
        "label": "Guardian Pollution",
    },
    # GOV.UK topic feeds
    {
        "url": "https://www.gov.uk/search/news-and-communications.atom?keywords=flooding&topical_events=",
        "label": "GOV.UK Flooding",
    },
    {
        "url": "https://www.gov.uk/search/news-and-communications.atom?keywords=pothole+road+repair",
        "label": "GOV.UK Roads",
    },
]


def _parse_published(entry) -> datetime:
    """Extract published datetime from feed entry."""
    for field in ("published", "updated"):
        val = getattr(entry, field, None)
        if val:
            try:
                return parsedate_to_datetime(val).replace(tzinfo=None)
            except Exception:
                try:
                    return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass
    return datetime.utcnow()


def _stable_id(feed_label: str, entry_id: str, title: str) -> str:
    """Generate a stable deduplication key from entry metadata."""
    raw = f"{feed_label}|{entry_id or title}"
    return f"rss_{hashlib.sha1(raw.encode()).hexdigest()[:16]}"


def ingest_rss(db: Session) -> int:
    """
    Parse all configured RSS feeds and save new entries as raw posts.
    Returns count of new records saved.
    """
    saved = 0

    for feed_cfg in RSS_FEEDS:
        feed_url = feed_cfg["url"]
        label = feed_cfg["label"]

        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            logger.warning("Failed to parse feed %s: %s", feed_url, exc)
            continue

        if parsed.bozo and not parsed.entries:
            logger.warning("Feed parse error for %s: %s", label, parsed.bozo_exception)
            continue

        for entry in parsed.entries:
            title = entry.get("title", "").strip()
            if not title:
                continue

            source_id = _stable_id(label, entry.get("id", ""), title)

            existing = db.query(RawPost).filter_by(source_id=source_id).first()
            if existing:
                continue

            # Extract body: prefer summary over content
            body = ""
            if hasattr(entry, "summary"):
                body = entry.summary
            elif hasattr(entry, "content") and entry.content:
                body = entry.content[0].get("value", "")

            # Strip basic HTML tags
            import re
            body = re.sub(r"<[^>]+>", " ", body).strip()

            url = entry.get("link", "")

            raw = RawPost(
                source="rss",
                source_id=source_id,
                text=(body or title)[:5000],
                title=title[:500],
                image_urls=[],
                author=label,
                url=url,
                upvotes=0,
                subreddit=label,   # repurpose field as feed label
                posted_at=_parse_published(entry),
            )
            db.add(raw)
            saved += 1

    db.commit()
    logger.info("RSS ingestion: saved %d new entries.", saved)
    return saved
