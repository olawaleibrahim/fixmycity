"""
Keyword-based hazard classifier for MVP.

Each post is scored against keyword sets for each hazard type.
The highest-scoring type wins if it exceeds a threshold, otherwise
the post is marked "irrelevant".

Easily replaceable with HuggingFace zero-shot later:
    from transformers import pipeline
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
"""

import re
from dataclasses import dataclass

HAZARD_KEYWORDS: dict[str, list[str]] = {
    "pothole": [
        "pothole", "pot hole", "road damage", "road crack", "road surface",
        "damaged road", "road repair", "tarmac", "road hole", "crumbling road",
    ],
    "flooding": [
        "flood", "flooding", "flooded", "waterlogged", "standing water",
        "blocked drain", "drain overflow", "sewage", "puddle", "puddles",
        "water on road", "overflowing", "burst pipe", "burst main",
        # EA Flood API terms
        "flood warning", "flood alert", "severe flood", "groundwater flooding",
        "river flooding", "surface water flooding", "coastal flooding",
    ],
    "trash": [
        "litter", "littering", "rubbish", "garbage", "trash", "fly tip",
        "fly-tip", "flytipping", "dumped waste", "illegal dumping",
        "bin overflow", "overflowing bin", "fly tipping", "waste dump",
        # Police API terms
        "drugs", "drug dealing", "drug incident",
    ],
    "broken_infrastructure": [
        "streetlight", "street light", "lamppost", "lamp post", "broken light",
        "traffic light", "traffic lights", "broken sign", "damaged sign",
        "pavement crack", "cracked pavement", "broken pavement", "dangerous pavement",
        "missing manhole", "manhole cover", "broken bench", "damaged fence",
        # Police API terms
        "anti social behaviour", "anti-social behaviour", "antisocial behaviour",
        "public order", "vehicle crime", "abandoned vehicle",
    ],
    "graffiti": [
        "graffiti", "vandalism", "vandal", "tagged", "tagging", "spray paint",
        "spray painted",
        # Police API terms
        "criminal damage", "arson", "criminal damage arson",
    ],
    "housing_defect": [
        "mold", "mould", "damp", "dampness", "leak", "leaking roof",
        "cracks in wall", "crumbling wall", "broken window", "no heating",
        "no hot water", "pest infestation", "rats", "mice", "cockroach",
        "unsafe building", "unsafe property", "housing disrepair",
    ],
}

# Irrelevance signals — strong negative indicators
IRRELEVANT_SIGNALS = [
    "minecraft", "gaming", "recipe", "movie", "series", "book",
    "stock", "crypto", "investment", "relationship", "dating",
]


@dataclass
class ClassificationResult:
    hazard_type: str   # e.g. "pothole" or "irrelevant"
    confidence: float  # 0.0 – 1.0
    matched_keywords: list[str]


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower())


def classify(title: str, body: str = "") -> ClassificationResult:
    """
    Classify a post into a hazard type using keyword matching.
    Returns ClassificationResult with hazard_type and confidence.
    """
    full_text = _normalise(f"{title} {body}")

    # Quick irrelevance check
    for signal in IRRELEVANT_SIGNALS:
        if signal in full_text:
            return ClassificationResult("irrelevant", 0.0, [])

    scores: dict[str, float] = {}
    all_matched: dict[str, list[str]] = {}

    for hazard_type, keywords in HAZARD_KEYWORDS.items():
        matched = []
        for kw in keywords:
            if kw in full_text:
                matched.append(kw)
        if matched:
            # Weight by number of unique keyword hits; title matches score higher
            title_norm = _normalise(title)
            title_hits = sum(1 for kw in matched if kw in title_norm)
            body_hits = len(matched) - title_hits
            scores[hazard_type] = title_hits * 2.0 + body_hits * 1.0
            all_matched[hazard_type] = matched

    if not scores:
        return ClassificationResult("irrelevant", 0.0, [])

    best_type = max(scores, key=lambda k: scores[k])
    raw_score = scores[best_type]

    # Normalise to 0–1 confidence (cap at 5 hits = full confidence)
    confidence = min(raw_score / 5.0, 1.0)

    if confidence < 0.2:
        return ClassificationResult("irrelevant", confidence, all_matched.get(best_type, []))

    return ClassificationResult(best_type, confidence, all_matched[best_type])
