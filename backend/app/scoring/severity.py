"""
Severity scoring for Week 1 MVP.

Formula (no CV yet — added in Week 2):
    severity = w1 * engagement_score
             + w2 * confidence_score
             + w3 * recency_score

All components normalised 0–1, output scaled 0–100.
"""

from datetime import datetime, timezone


# Weights — tune as needed
W_ENGAGEMENT = 0.4
W_CONFIDENCE = 0.35
W_RECENCY = 0.25

# Upvote thresholds for normalisation
MAX_UPVOTES = 500  # posts above this get full engagement score


def _engagement_score(upvotes: int) -> float:
    """Normalise upvotes to 0–1. Logarithmic scaling."""
    if upvotes <= 0:
        return 0.0
    import math
    return min(math.log1p(upvotes) / math.log1p(MAX_UPVOTES), 1.0)


def _recency_score(posted_at: datetime | None) -> float:
    """
    Recency decay: 1.0 if < 1 hour old, decays to 0 after 7 days.
    Uses exponential decay: score = e^(-hours / 72)
    """
    if posted_at is None:
        return 0.5  # unknown — assume middling recency

    import math
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)

    hours_old = (datetime.now(tz=timezone.utc) - posted_at).total_seconds() / 3600
    hours_old = max(hours_old, 0)
    return math.exp(-hours_old / 72)  # half-life ~50h


def compute_severity(
    upvotes: int,
    confidence: float,
    posted_at: datetime | None = None,
    cv_score: float = 0.0,  # placeholder for Week 2
) -> float:
    """
    Compute severity score (0–100).

    Args:
        upvotes: post engagement
        confidence: NLP classification confidence (0–1)
        posted_at: post timestamp for recency decay
        cv_score: computer vision severity (0–1), added in Week 2

    Returns:
        severity score in range [0, 100]
    """
    eng = _engagement_score(upvotes)
    rec = _recency_score(posted_at)
    conf = max(0.0, min(1.0, confidence))

    raw = W_ENGAGEMENT * eng + W_CONFIDENCE * conf + W_RECENCY * rec
    return round(raw * 100, 1)
