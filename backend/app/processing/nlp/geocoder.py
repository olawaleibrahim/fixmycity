"""
Geocoding: convert a location string to (lat, lon) using Nominatim (OpenStreetMap).
Free, no API key required — just needs a valid User-Agent email.
"""

import logging
import time
from functools import lru_cache

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from app.config import settings

logger = logging.getLogger(__name__)

_geocoder: Nominatim | None = None


def _get_geocoder() -> Nominatim:
    global _geocoder
    if _geocoder is None:
        _geocoder = Nominatim(
            user_agent=settings.nominatim_user_agent,
            timeout=5,
        )
    return _geocoder


@lru_cache(maxsize=512)
def geocode(location_text: str) -> tuple[float, float, str] | None:
    """
    Convert a location string to (lat, lon, resolved_name).
    Returns None if geocoding fails.

    Results are cached in-process to avoid hammering Nominatim.
    Nominatim rate limit: 1 request/second for free tier.
    """
    if not location_text or len(location_text) < 2:
        return None

    gc = _get_geocoder()

    # Try with UK country bias first
    queries = [
        f"{location_text}, United Kingdom",
        location_text,
    ]

    for query in queries:
        try:
            time.sleep(1.1)  # Nominatim rate limit
            result = gc.geocode(query, exactly_one=True, country_codes="gb")
            if result:
                return (result.latitude, result.longitude, result.address)
        except GeocoderTimedOut:
            logger.warning("Geocoding timed out for: %s", query)
        except GeocoderServiceError as exc:
            logger.warning("Geocoding error for '%s': %s", query, exc)

    return None


def geocode_locations(locations: list[str]) -> tuple[float, float, str] | None:
    """
    Try each location candidate in order until one geocodes successfully.
    Returns (lat, lon, resolved_name) or None.
    """
    for loc in locations:
        result = geocode(loc)
        if result:
            return result
    return None
