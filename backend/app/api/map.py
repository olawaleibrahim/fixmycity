"""
/map endpoint — returns GeoJSON FeatureCollection for the frontend map.
"""

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import HazardEvent

router = APIRouter(prefix="/map", tags=["map"])

HAZARD_COLOURS = {
    "pothole": "#f97316",
    "flooding": "#3b82f6",
    "trash": "#84cc16",
    "broken_infrastructure": "#a855f7",
    "graffiti": "#ec4899",
    "housing_defect": "#ef4444",
}


@router.get("/events")
def map_events(
    time_range: Literal["24h", "7d", "30d", "all"] = Query("7d"),
    hazard_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """
    Return a GeoJSON FeatureCollection of all geo-located hazard events.
    Consumed directly by Leaflet / Mapbox on the frontend.
    """
    q = (
        db.query(HazardEvent)
        .filter(HazardEvent.lat.isnot(None), HazardEvent.lon.isnot(None))
        .filter(HazardEvent.hazard_type != "irrelevant")
    )

    if hazard_type:
        q = q.filter(HazardEvent.hazard_type == hazard_type)

    if time_range != "all":
        cutoff = {
            "24h": datetime.utcnow() - timedelta(hours=24),
            "7d": datetime.utcnow() - timedelta(days=7),
            "30d": datetime.utcnow() - timedelta(days=30),
        }[time_range]
        q = q.filter(HazardEvent.event_at >= cutoff)

    events = q.order_by(HazardEvent.severity_score.desc()).limit(2000).all()

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [event.lon, event.lat],
            },
            "properties": {
                "id": event.id,
                "hazard_type": event.hazard_type,
                "severity_score": event.severity_score,
                "confidence": event.confidence,
                "location_name": event.location_name,
                "summary": event.summary,
                "source": event.source,
                "source_url": event.source_url,
                "upvotes": event.upvotes,
                "event_at": event.event_at.isoformat() if event.event_at else None,
                "colour": HAZARD_COLOURS.get(event.hazard_type, "#6b7280"),
            },
        }
        for event in events
    ]

    return {
        "type": "FeatureCollection",
        "features": features,
        "meta": {
            "total": len(features),
            "time_range": time_range,
        },
    }


@router.get("/stats")
def map_stats(db: Session = Depends(get_db)):
    """Summary stats for the map overlay."""
    from sqlalchemy import func

    rows = (
        db.query(HazardEvent.hazard_type, func.count(HazardEvent.id).label("count"))
        .filter(HazardEvent.hazard_type != "irrelevant")
        .group_by(HazardEvent.hazard_type)
        .all()
    )

    return {
        "by_type": {row.hazard_type: row.count for row in rows},
        "total": sum(row.count for row in rows),
    }
