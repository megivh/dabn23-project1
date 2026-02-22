"""
DABN23 Project — TripAdvisor Content API Provider

Provider layer responsibilities:
- Resolve a city to geo coords
- Search candidates near city coords
- Fetch details for a location_id (with rate-limit backoff)
- Normalize into unified schema
- Provide optional group-based filtering helpers

IMPORTANT:
- TripAdvisor 'groups' are only reliably available in the details response.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests

from .config import TA_API_KEY

TA_SEARCH_URL = "https://api.content.tripadvisor.com/api/v1/location/search"
TA_DETAILS_URL = "https://api.content.tripadvisor.com/api/v1/location/{location_id}/details"


# -----------------------------
# City resolution (geo lookup)
# -----------------------------

def get_city_location(city: str, language: str = "en") -> Dict[str, Any]:
    """Resolve a city string into a TripAdvisor 'geo' entry."""
    params = {
        "key": TA_API_KEY,
        "searchQuery": city,
        "category": "geos",
        "language": language,
    }
    r = requests.get(TA_SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()

    results = r.json().get("data", [])
    if not results:
        raise ValueError(f"Could not resolve city: {city}")

    geo = results[0]
    lat = geo.get("latitude")
    lng = geo.get("longitude")

    return {
        "location_id": geo.get("location_id"),
        "name": geo.get("name"),
        "lat_long": f"{lat},{lng}" if lat is not None and lng is not None else None,
    }


# -----------------------------
# Search (candidate listing)
# -----------------------------

def search(
    city_geo: Dict[str, Any],
    item_type: str = "attraction",
    language: str = "en",
) -> List[Dict[str, Any]]:
    """
    Search TripAdvisor locations near a city's coordinates.

    Notes:
    - Search results generally do NOT contain groups reliably.
    - Use details() -> summarize() to access groups.
    """
    category = "attractions" if item_type in ("attraction", "activity") else "attractions"

    params = {
        "key": TA_API_KEY,
        "category": category,
        "language": language,
    }

    if city_geo.get("lat_long"):
        params["latLong"] = city_geo["lat_long"]
    else:
        params["searchQuery"] = city_geo.get("name")

    r = requests.get(TA_SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])


# -----------------------------
# Details (rate-limit resilient)
# -----------------------------

def details(location_id: str, language: str = "en", max_retries: int = 3) -> Dict[str, Any]:
    """
    Fetch detailed information for one TripAdvisor location_id.

    Retries on HTTP 429 with exponential backoff: 1s, 2s, 4s...
    """
    url = TA_DETAILS_URL.format(location_id=location_id)
    params = {"key": TA_API_KEY, "language": language}

    for attempt in range(max_retries + 1):
        r = requests.get(url, params=params, timeout=30)

        if r.status_code == 429 and attempt < max_retries:
            time.sleep(2 ** attempt)
            continue

        r.raise_for_status()
        return r.json()

    raise RuntimeError("TripAdvisor details retry loop ended unexpectedly.")


# -----------------------------
# Normalization (unified schema)
# -----------------------------

def summarize(place: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize TripAdvisor details response into unified schema."""
    addr = place.get("address_obj") or {}
    full_address = addr.get("address_string") or ", ".join(
        filter(None, [addr.get("street1"), addr.get("city"), addr.get("state"), addr.get("country")])
    )

    cat = place.get("category") or {}
    groups = [g.get("name") for g in (place.get("groups") or []) if g.get("name")]

    lat = place.get("latitude")
    lng = place.get("longitude")

    return {
        "source": "tripadvisor",
        "item_id": str(place.get("location_id", "")),
        "name": place.get("name"),
        "address": full_address,
        "rating": float(place["rating"]) if place.get("rating") else None,
        "review_count": int(place["num_reviews"]) if place.get("num_reviews") else None,
        "category_primary": cat.get("name"),
        # store TripAdvisor groups in unified schema types
        "types": groups,
        "wheelchair_accessible_entrance": None,
        "opening_hours_weekday_descriptions": None,
        "website": place.get("web_url"),
        "phone": None,
        "lat": float(lat) if lat is not None else None,
        "lng": float(lng) if lng is not None else None,
    }


# -----------------------------
# Group filtering helpers
# -----------------------------

def _norm_set(values: List[str]) -> set[str]:
    return {v.strip().lower() for v in values if isinstance(v, str) and v.strip()}


def summary_matches_groups(
    summary: Dict[str, Any],
    allow_groups: Optional[List[str]] = None,
    deny_groups: Optional[List[str]] = None,
) -> bool:
    """
    Keep/reject summarized place based on TripAdvisor groups (summary['types']).

    - deny_groups: if any match -> reject
    - allow_groups: if provided, require at least one match
    """
    place_groups = _norm_set(summary.get("types") or [])

    if deny_groups:
        deny = _norm_set(deny_groups)
        if place_groups.intersection(deny):
            return False

    if allow_groups:
        allow = _norm_set(allow_groups)
        return len(place_groups.intersection(allow)) > 0

    return True


def details_summarized_filtered(
    location_id: str,
    language: str = "en",
    allow_groups: Optional[List[str]] = None,
    deny_groups: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """details() -> summarize() -> filter by groups. Returns summary or None."""
    d = details(location_id, language=language)
    s = summarize(d)
    if not summary_matches_groups(s, allow_groups=allow_groups, deny_groups=deny_groups):
        return None
    return s