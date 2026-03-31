"""
Ingestion layer — all sources, no API keys required.

Sources:
  - UK Police Street Crime API : anti-social behaviour, criminal damage, public order incidents
  - EA Flood Monitoring API    : real-time flood alerts (England)
  - RSS feeds                  : BBC local news + Guardian environment/cities
"""

import logging

from sqlalchemy.orm import Session

from app.ingestion.police_crimes import ingest_police_crimes
from app.ingestion.flood_monitor import ingest_flood_monitor
from app.ingestion.rss_scraper import ingest_rss

logger = logging.getLogger(__name__)


def ingest_all(db: Session) -> dict[str, int]:
    """Run all ingestion sources and return counts per source."""
    results = {}

    results["police"] = ingest_police_crimes(db)
    results["flood_monitor"] = ingest_flood_monitor(db)
    results["rss"] = ingest_rss(db)

    total = sum(results.values())
    logger.info("Ingestion complete: %d new records total — %s", total, results)
    return results
