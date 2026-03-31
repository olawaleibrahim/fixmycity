"""
/dashboard endpoints — neighborhood rankings and area stats.
"""

import math
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.event import HazardEvent

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# ── location normalisation ─────────────────────────────────────────────────

_UK_NOISE = re.compile(
    r"\b(England|Wales|Scotland|Northern Ireland|United Kingdom|UK|GB)\b",
    re.I,
)
_POSTCODE = re.compile(r"\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b", re.I)
_COUNTY_SUFFIX = re.compile(r"\b(County|Borough|District|Council|City of)\b", re.I)


def _normalise_area(location_name: str | None, location_text: str | None) -> str | None:
    """Extract a short, readable neighbourhood/city name."""
    # NER-extracted text is already short and clean
    if location_text and 2 < len(location_text) < 50:
        return location_text.strip().title()

    if not location_name:
        return None

    clean = _POSTCODE.sub("", location_name)
    clean = _UK_NOISE.sub("", clean)
    clean = _COUNTY_SUFFIX.sub("", clean)
    clean = re.sub(r"\s+", " ", clean).strip().strip(",").strip()

    parts = [p.strip() for p in clean.split(",") if p.strip() and len(p.strip()) > 2]
    return parts[0].title() if parts else None


# ── scoring ────────────────────────────────────────────────────────────────

HAZARD_EMOJI = {
    "pothole": "🕳️",
    "flooding": "🌊",
    "trash": "🗑️",
    "broken_infrastructure": "🚧",
    "graffiti": "🎨",
    "housing_defect": "🏚️",
}

HAZARD_WEIGHT = {
    "flooding": 1.4,
    "pothole": 1.1,
    "housing_defect": 1.2,
    "broken_infrastructure": 1.0,
    "trash": 0.9,
    "graffiti": 0.8,
}

DESCRIPTORS = [
    (85, "💀 Absolute Carnage"),
    (70, "🔥 Pretty Grim"),
    (55, "⚠️ Rough Around the Edges"),
    (40, "😬 Has Some Issues"),
    (25, "🤔 Manageable"),
    (0,  "😌 Not Bad"),
]

TREND_LABELS = [
    (20,  "📈 Worsening Fast", "up"),
    (5,   "↗️ Getting Worse",  "up"),
    (-5,  "→ Stable",          "flat"),
    (-20, "↘️ Improving",      "down"),
    (-99, "📉 Turning Around", "down"),
]


def _descriptor(score: float) -> str:
    for threshold, label in DESCRIPTORS:
        if score >= threshold:
            return label
    return DESCRIPTORS[-1][1]


def _trend_label(pct_change: float | None) -> tuple[str, str]:
    if pct_change is None:
        return ("🆕 New Entry", "new")
    for threshold, label, direction in TREND_LABELS:
        if pct_change >= threshold:
            return (label, direction)
    return TREND_LABELS[-1][1], TREND_LABELS[-1][2]


def _shame_score(events: list) -> float:
    """
    Composite shame score 0–100.

    Combines:
      - Average weighted severity (accounts for hazard type danger level)
      - Volume bonus (log scale so one massive area doesn't dominate)
      - Hazard diversity (areas with multiple problem types score higher)
    """
    if not events:
        return 0.0

    weighted_severities = [
        e.severity_score * HAZARD_WEIGHT.get(e.hazard_type, 1.0)
        for e in events
    ]
    avg_severity = sum(weighted_severities) / len(weighted_severities)
    volume_bonus = math.log1p(len(events)) * 8
    unique_types = len({e.hazard_type for e in events})
    diversity_bonus = unique_types * 4

    raw = avg_severity * 0.65 + volume_bonus + diversity_bonus
    return round(min(raw, 100), 1)


# ── response models ─────────────────────────────────────────────────────────

class AreaRanking(BaseModel):
    rank: int
    area: str
    shame_score: float
    prev_score: float | None
    trend_pct: float | None
    trend_label: str
    trend_direction: str          # "up" | "down" | "flat" | "new"
    descriptor: str
    event_count: int
    primary_hazard: str
    primary_hazard_emoji: str
    hazard_breakdown: dict[str, int]
    lat: float | None
    lon: float | None


class RankingsResponse(BaseModel):
    generated_at: str
    period: str
    total_areas: int
    rankings: list[AreaRanking]
    most_improved: list[AreaRanking]


# ── aggregation ─────────────────────────────────────────────────────────────

def _aggregate_by_area(events: list) -> dict[str, list]:
    """Group events by normalised area name."""
    buckets: dict[str, list] = defaultdict(list)
    for e in events:
        area = _normalise_area(e.location_name, e.location_text)
        if area:
            buckets[area].append(e)
    return dict(buckets)


def _area_centroid(events: list) -> tuple[float | None, float | None]:
    lats = [e.lat for e in events if e.lat]
    lons = [e.lon for e in events if e.lon]
    if lats and lons:
        return round(sum(lats) / len(lats), 4), round(sum(lons) / len(lons), 4)
    return None, None


def _build_ranking(rank: int, area: str, events: list,
                   prev_score: float | None) -> AreaRanking:
    score = _shame_score(events)
    trend_pct = (
        round((score - prev_score) / prev_score * 100, 1)
        if prev_score and prev_score > 0
        else None
    )
    trend_lbl, trend_dir = _trend_label(trend_pct)

    hazard_counts: dict[str, int] = defaultdict(int)
    for e in events:
        hazard_counts[e.hazard_type] += 1

    primary = max(hazard_counts, key=lambda k: hazard_counts[k])
    lat, lon = _area_centroid(events)

    return AreaRanking(
        rank=rank,
        area=area,
        shame_score=score,
        prev_score=prev_score,
        trend_pct=trend_pct,
        trend_label=trend_lbl,
        trend_direction=trend_dir,
        descriptor=_descriptor(score),
        event_count=len(events),
        primary_hazard=primary,
        primary_hazard_emoji=HAZARD_EMOJI.get(primary, "❓"),
        hazard_breakdown=dict(hazard_counts),
        lat=lat,
        lon=lon,
    )


# ── endpoint ────────────────────────────────────────────────────────────────

@router.get("/rankings", response_model=RankingsResponse)
def get_rankings(
    time_range: Literal["24h", "7d", "30d", "all"] = Query("all"),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
):
    """
    Rank neighbourhoods by composite shame score.
    Compares current period vs the equivalent previous period for trend arrows.
    """
    delta = {
        "24h": timedelta(hours=24),
        "7d":  timedelta(days=7),
        "30d": timedelta(days=30),
        "all": None,
    }[time_range]

    now = datetime.utcnow()

    base_q = (
        db.query(HazardEvent)
        .filter(HazardEvent.lat.isnot(None))
        .filter(HazardEvent.hazard_type != "irrelevant")
    )

    if delta:
        current_events = base_q.filter(HazardEvent.event_at >= now - delta).all()
        prev_events    = base_q.filter(
            HazardEvent.event_at >= now - delta * 2,
            HazardEvent.event_at <  now - delta,
        ).all()
    else:
        current_events = base_q.all()
        prev_events    = []

    current_by_area = _aggregate_by_area(current_events)
    prev_by_area    = _aggregate_by_area(prev_events)

    # Compute previous scores for trend
    prev_scores: dict[str, float] = {
        area: _shame_score(evs) for area, evs in prev_by_area.items()
    }

    # Rank current areas
    ranked = sorted(
        current_by_area.items(),
        key=lambda kv: _shame_score(kv[1]),
        reverse=True,
    )

    rankings = [
        _build_ranking(i + 1, area, evs, prev_scores.get(area))
        for i, (area, evs) in enumerate(ranked[:limit])
    ]

    # Most improved = areas that exist in both periods, sorted by biggest score DROP
    improved = [
        r for r in rankings
        if r.trend_pct is not None and r.trend_pct < -5
    ]
    improved.sort(key=lambda r: r.trend_pct or 0)

    return RankingsResponse(
        generated_at=now.strftime("%d %b %Y, %H:%M UTC"),
        period=time_range,
        total_areas=len(current_by_area),
        rankings=rankings,
        most_improved=improved[:5],
    )


@router.get("/area/{area_name}")
def get_area_detail(area_name: str, db: Session = Depends(get_db)):
    """All events for a specific area."""
    events = (
        db.query(HazardEvent)
        .filter(HazardEvent.lat.isnot(None))
        .filter(HazardEvent.hazard_type != "irrelevant")
        .all()
    )
    area_events = [
        e for e in events
        if _normalise_area(e.location_name, e.location_text) == area_name
    ]
    return {"area": area_name, "event_count": len(area_events), "shame_score": _shame_score(area_events)}
