"""
UK Police Street-Level Crime API ingestion.

Completely open — no API key required.
Source: https://data.police.uk

Data is typically 2–3 months behind the current date.
We fetch the last 2 available months for major UK cities.

Relevant crime categories mapped to our hazard types:
  anti-social-behaviour   → broken_infrastructure
  criminal-damage-arson   → graffiti
  public-order            → broken_infrastructure
  drugs                   → trash
"""

import logging
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.event import RawPost

logger = logging.getLogger(__name__)

POLICE_API = "https://data.police.uk/api"

# Only fetch categories relevant to urban hazards
RELEVANT_CATEGORIES = {
    "anti-social-behaviour": "broken_infrastructure",
    "criminal-damage-arson": "graffiti",
    "public-order": "broken_infrastructure",
    "drugs": "trash",
    "vehicle-crime": "broken_infrastructure",
}

UK_CITIES = [
    (51.5074, -0.1278, "London"),
    (53.4808, -2.2426, "Manchester"),
    (52.4862, -1.8904, "Birmingham"),
    (53.8008, -1.5491, "Leeds"),
    (55.8642, -4.2518, "Glasgow"),
    (51.4545, -2.5879, "Bristol"),
    (53.4084, -2.9916, "Liverpool"),
    (53.3811, -1.4701, "Sheffield"),
    (52.9548, -1.1581, "Nottingham"),
    (52.6369, -1.1398, "Leicester"),
    (50.8225, -0.1372, "Brighton"),
    (54.9783, -1.6178, "Newcastle"),
]


def _last_available_months(n: int = 2) -> list[str]:
    """
    Return the last n months in YYYY-MM format.
    Police data is ~2-3 months behind, so we offset by 3.
    """
    now = datetime.now(timezone.utc)
    months = []
    for i in range(3, 3 + n):
        d = now - timedelta(days=30 * i)
        months.append(d.strftime("%Y-%m"))
    return months


def fetch_city_crimes(
    client: httpx.Client,
    lat: float,
    lon: float,
    month: str,
) -> list[dict]:
    """Fetch street-level crimes for a location and month."""
    try:
        resp = client.get(
            f"{POLICE_API}/crimes-street/all-crime",
            params={"lat": lat, "lng": lon, "date": month},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Police API failed (%s, %s %s): %s", lat, lon, month, exc)
        return []


def ingest_police_crimes(db: Session) -> int:
    """
    Pull street crime data for major UK cities and store relevant incidents.
    Returns count of new records saved.
    """
    saved = 0
    months = _last_available_months(n=2)
    rows: list[dict] = []

    with httpx.Client(
        headers={"User-Agent": "fixmycity/0.1 (urban-insight-platform)"},
        follow_redirects=True,
    ) as client:
        for lat, lon, city_name in UK_CITIES:
            for month in months:
                crimes = fetch_city_crimes(client, lat, lon, month)
                logger.debug("%s %s: %d crimes fetched", city_name, month, len(crimes))

                for crime in crimes:
                    category = crime.get("category", "")
                    if category not in RELEVANT_CATEGORIES:
                        continue

                    crime_id = crime.get("persistent_id") or str(crime.get("id", ""))
                    if not crime_id:
                        continue

                    location = crime.get("location", {})
                    street_name = location.get("street", {}).get("name", "")
                    loc_lat = location.get("latitude")
                    loc_lon = location.get("longitude")

                    title = f"{category.replace('-', ' ').title()} near {street_name}"
                    text = (
                        f"{category.replace('-', ' ')} incident reported near {street_name}, "
                        f"{city_name}. Category: {category}. Month: {month}."
                    )

                    try:
                        posted_at = datetime.strptime(month, "%Y-%m").replace(day=1)
                    except ValueError:
                        posted_at = datetime.now(timezone.utc).replace(tzinfo=None)

                    rows.append({
                        "source": "police_uk",
                        "source_id": f"police_{crime_id}",
                        "text": text,
                        "title": title[:500],
                        "image_urls": [],
                        "author": "data.police.uk",
                        "url": f"https://data.police.uk/api/crimes-street/all-crime?lat={loc_lat}&lng={loc_lon}&date={month}",
                        "upvotes": 0,
                        "subreddit": city_name,
                        "posted_at": posted_at,
                        "processed": False,
                        "source_lat": float(loc_lat) if loc_lat else None,
                        "source_lon": float(loc_lon) if loc_lon else None,
                    })

    if rows:
        # Bulk upsert — skip duplicates via ON CONFLICT DO NOTHING
        stmt = pg_insert(RawPost.__table__).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["source_id"])
        result = db.execute(stmt)
        saved = result.rowcount
        db.commit()

    logger.info("Police crimes ingestion: saved %d new incidents.", saved)
    return saved
