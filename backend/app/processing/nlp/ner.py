"""
Location extraction using spaCy NER.

Extracts GPE (geopolitical entities) and LOC (locations) from post text,
prioritising UK place names.
"""

import logging
import re
from functools import lru_cache

logger = logging.getLogger(__name__)

# Common UK place name patterns to boost extraction
UK_PLACE_PATTERNS = re.compile(
    r"\b("
    r"London|Manchester|Birmingham|Leeds|Glasgow|Bristol|Liverpool|Sheffield|"
    r"Edinburgh|Cardiff|Belfast|Nottingham|Leicester|Coventry|Bradford|"
    r"Kingston upon Hull|Stoke-on-Trent|Wolverhampton|Plymouth|Derby|"
    r"Southampton|Portsmouth|Norwich|Oxford|Cambridge|Reading|Luton|"
    r"Sunderland|Middlesbrough|Newcastle|Gateshead|Brighton|Bournemouth|"
    r"Northampton|Milton Keynes|Swansea|Aberdeen|Dundee|Inverness|"
    r"[A-Z][a-z]+-on-[A-Z][a-z]+|[A-Z][a-z]+ upon [A-Z][a-z]+"
    r")\b",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def _load_nlp():
    try:
        import spacy
        return spacy.load("en_core_web_sm")
    except Exception as exc:
        logger.error("spaCy model not available: %s", exc)
        return None


def extract_locations(text: str) -> list[str]:
    """
    Return a deduplicated list of location strings found in text.
    Combines spaCy NER + regex for UK place names.
    """
    locations: list[str] = []

    # Regex pass — fast and reliable for known UK cities
    regex_matches = UK_PLACE_PATTERNS.findall(text)
    locations.extend(regex_matches)

    # spaCy NER pass
    nlp = _load_nlp()
    if nlp is not None:
        doc = nlp(text[:1000])  # cap for speed
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC", "FAC"):
                locations.append(ent.text)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for loc in locations:
        normalised = loc.strip().lower()
        if normalised and normalised not in seen:
            seen.add(normalised)
            unique.append(loc.strip())

    return unique


def best_location(text: str) -> str | None:
    """Return the single most likely location mention from text."""
    locations = extract_locations(text)
    return locations[0] if locations else None
