"""
Environment Agency Real Time Flood Monitoring API.

Completely open — no API key required.
Covers England only (Scotland/Wales have separate agencies).

Docs: https://environment.data.gov.uk/flood-monitoring/doc/reference
"""

import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.models.event import RawPost

logger = logging.getLogger(__name__)

FLOOD_API = "https://environment.data.gov.uk/flood-monitoring"

SEVERITY_LABELS = {
    1: "Severe Flood Warning",
    2: "Flood Warning",
    3: "Flood Alert",
    4: "Warning no longer in force",
}


def _severity_to_text(level: int) -> str:
    return SEVERITY_LABELS.get(level, f"Severity {level}")


def fetch_active_floods(client: httpx.Client) -> list[dict]:
    """Fetch all currently active flood alerts in England."""
    try:
        resp = client.get(
            f"{FLOOD_API}/id/floods",
            params={"min-severity": 3},  # 1=Severe, 2=Warning, 3=Alert
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])
    except Exception as exc:
        logger.warning("EA Flood API error: %s", exc)
        return []


def fetch_flood_area_geometry(client: httpx.Client, area_url: str) -> tuple[float, float] | None:
    """Fetch the centroid lat/lon for a flood area polygon."""
    try:
        resp = client.get(f"{area_url}.json", timeout=10)
        resp.raise_for_status()
        item = resp.json().get("items", {})
        if isinstance(item, list):
            item = item[0]
        lat = item.get("lat")
        lon = item.get("long")
        if lat and lon:
            return float(lat), float(lon)
    except Exception:
        pass
    return None


def ingest_flood_monitor(db: Session) -> int:
    """
    Pull active flood alerts and store as raw posts.
    Each alert is one RawPost with pre-known lat/lon embedded in its metadata
    (the pipeline geocoder will also try to resolve from text).
    Returns count of new records saved.
    """
    saved = 0

    with httpx.Client(
        headers={"User-Agent": "fixmycity/0.1 (urban-insight-platform)"},
        follow_redirects=True,
    ) as client:
        alerts = fetch_active_floods(client)
        logger.debug("EA Flood API: %d active alerts", len(alerts))

        for alert in alerts:
            # Use the alert's @id as a stable source_id
            raw_id = alert.get("@id", "").split("/")[-1]
            if not raw_id:
                continue

            source_id = f"ea_flood_{raw_id}"
            existing = db.query(RawPost).filter_by(source_id=source_id).first()
            if existing:
                continue

            severity_level = alert.get("severityLevel", 3)
            severity_text = _severity_to_text(severity_level)
            area_name = alert.get("description") or alert.get("floodAreaID", "Unknown area")
            county = alert.get("floodArea", {}).get("county", "")
            river = alert.get("floodArea", {}).get("riverOrSea", "")

            title = f"{severity_text}: {area_name}"
            detail_parts = [f"Severity: {severity_text}"]
            if county:
                detail_parts.append(f"County: {county}")
            if river:
                detail_parts.append(f"River/Sea: {river}")
            detail_parts.append(f"Area: {area_name}")
            detail = ". ".join(detail_parts)

            # Parse time raised
            time_raised = alert.get("timeRaised") or alert.get("timeMessageChanged")
            posted_at = datetime.utcnow()
            if time_raised:
                try:
                    posted_at = datetime.fromisoformat(time_raised.replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    pass

            # Fetch centroid lat/lon from the flood area API
            area_id_url = alert.get("floodArea", {}).get("@id", "")
            geo = fetch_flood_area_geometry(client, area_id_url) if area_id_url else None
            src_lat, src_lon = geo if geo else (None, None)

            raw = RawPost(
                source="ea_flood",
                source_id=source_id,
                text=detail,
                title=title[:500],
                image_urls=[],
                author="Environment Agency",
                url=f"https://check-for-flooding.service.gov.uk/alerts-and-warnings?type=alert&location={raw_id}",
                upvotes=severity_level * -1 + 5,  # severity 1 (worst) → upvote proxy 4
                subreddit=county or "England",
                posted_at=posted_at,
                source_lat=src_lat,
                source_lon=src_lon,
            )
            db.add(raw)
            saved += 1

    db.commit()
    logger.info("EA Flood Monitor ingestion: saved %d new alerts.", saved)
    return saved
