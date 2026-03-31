from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.event import HazardEvent

router = APIRouter(prefix="/events", tags=["events"])

HazardType = Literal[
    "pothole", "flooding", "trash", "broken_infrastructure",
    "graffiti", "housing_defect", "irrelevant"
]


class EventResponse(BaseModel):
    id: int
    hazard_type: str
    confidence: float
    lat: float | None
    lon: float | None
    location_name: str | None
    severity_score: float
    summary: str | None
    source: str | None
    source_url: str | None
    upvotes: int
    event_at: datetime | None

    class Config:
        from_attributes = True


@router.get("/", response_model=list[EventResponse])
def list_events(
    hazard_type: str | None = Query(None),
    time_range: Literal["24h", "7d", "30d", "all"] = Query("7d"),
    min_severity: float = Query(0.0, ge=0, le=100),
    has_location: bool = Query(False),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """List hazard events with optional filters."""
    q = db.query(HazardEvent).filter(HazardEvent.hazard_type != "irrelevant")

    if hazard_type:
        q = q.filter(HazardEvent.hazard_type == hazard_type)

    if time_range != "all":
        cutoff = {
            "24h": datetime.utcnow() - timedelta(hours=24),
            "7d": datetime.utcnow() - timedelta(days=7),
            "30d": datetime.utcnow() - timedelta(days=30),
        }[time_range]
        q = q.filter(HazardEvent.event_at >= cutoff)

    if min_severity > 0:
        q = q.filter(HazardEvent.severity_score >= min_severity)

    if has_location:
        q = q.filter(HazardEvent.lat.isnot(None), HazardEvent.lon.isnot(None))

    q = q.order_by(HazardEvent.severity_score.desc())

    return q.offset(offset).limit(limit).all()


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(HazardEvent).filter_by(id=event_id).first()
    if not event:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Event not found")
    return event
