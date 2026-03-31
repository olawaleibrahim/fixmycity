"""
Full NLP processing pipeline.

For each unprocessed RawPost:
  1. Classify → hazard_type + confidence
  2. Extract locations (NER)
  3. Geocode → lat/lon
  4. Score severity
  5. Save HazardEvent
"""

import logging

from sqlalchemy.orm import Session

from app.models.event import RawPost, HazardEvent
from app.processing.nlp.classifier import classify
from app.processing.nlp.ner import extract_locations
from app.processing.nlp.geocoder import geocode_locations
from app.scoring.severity import compute_severity

logger = logging.getLogger(__name__)


def process_post(raw: RawPost, db: Session) -> HazardEvent | None:
    """Process a single raw post through the NLP pipeline."""
    full_text = f"{raw.title or ''} {raw.text or ''}".strip()

    # 1. Classify
    result = classify(raw.title or "", raw.text or "")
    if result.hazard_type == "irrelevant":
        raw.processed = True
        db.add(raw)
        return None

    # 2. Use pre-known coordinates if available (e.g. police API, flood API)
    if raw.source_lat is not None and raw.source_lon is not None:
        lat, lon = raw.source_lat, raw.source_lon
        locations = extract_locations(full_text)
        resolved_name = locations[0] if locations else None
    else:
        # 3. Extract locations then geocode
        locations = extract_locations(full_text)
        geo = geocode_locations(locations)
        lat, lon, resolved_name = geo if geo else (None, None, None)

    # 4. Build summary (simple truncation for MVP; swap for LLM later)
    summary = _make_summary(raw.title, raw.text, result.hazard_type)

    # 5. Severity score
    severity = compute_severity(
        upvotes=raw.upvotes or 0,
        confidence=result.confidence,
        posted_at=raw.posted_at,
    )

    event = HazardEvent(
        raw_post_id=raw.id,
        hazard_type=result.hazard_type,
        confidence=result.confidence,
        location_text=locations[0] if locations else None,
        location_name=resolved_name,
        lat=lat,
        lon=lon,
        severity_score=severity,
        summary=summary,
        source=raw.source,
        source_url=raw.url,
        upvotes=raw.upvotes or 0,
        event_at=raw.posted_at,
    )

    raw.processed = True
    db.add(event)
    db.add(raw)
    return event


def _make_summary(title: str | None, body: str | None, hazard_type: str) -> str:
    """
    Simple extractive summary: first 200 chars of body, or title.
    Replace with LLM call in Week 2/3.
    """
    text = (title or "").strip()
    if body and len(body) > 20:
        snippet = body.strip()[:200].rsplit(" ", 1)[0]
        text = f"{text}. {snippet}" if text else snippet
    return text or f"Reported {hazard_type.replace('_', ' ')} issue."


def run_pipeline(db: Session, batch_size: int = 100) -> int:
    """
    Process all unprocessed raw posts.
    Prioritises sources with pre-known coordinates (ea_flood, police_uk) so
    geo-located events appear on the map immediately.
    Returns count of HazardEvents created.
    """
    from sqlalchemy import case

    priority = case(
        (RawPost.source == "ea_flood", 0),
        (RawPost.source == "police_uk", 1),
        else_=2,
    )
    posts = (
        db.query(RawPost)
        .filter_by(processed=False)
        .order_by(priority, RawPost.id)
        .limit(batch_size)
        .all()
    )

    created = 0
    for raw in posts:
        try:
            event = process_post(raw, db)
            if event:
                created += 1
        except Exception as exc:
            logger.error("Failed to process post %s: %s", raw.source_id, exc)
            raw.processed = True  # mark to avoid infinite retry
            db.add(raw)

    db.commit()
    logger.info("Pipeline: created %d events from %d posts.", created, len(posts))
    return created
