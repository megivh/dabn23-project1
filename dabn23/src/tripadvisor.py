"""
DABN23 Project — TripAdvisor Content API Provider

Purpose:
    Handle TripAdvisor Content API calls and normalize into the unified item schema.

Role in architecture:
    Provider layer — fetches + normalizes attraction/activity-like data from TripAdvisor.

Key responsibilities:
    - Resolve a city name to a geo location (to get coordinates)
    - Search for attractions near city coordinates
    - Fetch details for each location_id
    - Normalize into unified dict for item_summary cache

Dependencies:
    - requests
    - TA_API_KEY from config.py

Notes:
    TripAdvisor does not reliably provide:
    - wheelchair accessibility info
    - opening hours
    Coordinates may or may not be present; we store None if missing.
"""

from __future__ import annotations
import requests
from typing import Any, Dict, List
from .config import TA_API_KEY

TA_SEARCH_URL = "https://api.content.tripadvisor.com/api/v1/location/search"
TA_DETAILS_URL = "https://api.content.tripadvisor.com/api/v1/location/{location_id}/details"


def get_city_location(city: str, language: str = "en") -> Dict[str, Any]:
    """
    Resolve a city string into a TripAdvisor 'geo' entry.

    Returns
    -------
    dict
        Contains location_id, name, and lat_long string (if coords exist).
    """
    params = {
        "key": TA_API_KEY,
        "searchQuery": city,
        "category": "geos",   # important: geos only
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
        "lat_long": f"{lat},{lng}" if lat and lng else None,
    }


def search(city_geo: Dict[str, Any], item_type: str = "attraction", language: str = "en") -> List[Dict[str, Any]]:
    """
    Search TripAdvisor locations near a city's coordinates.

    Parameters
    ----------
    city_geo : dict
        Output of get_city_location().

    item_type : str
        'attraction' or 'activity'. (Project-level concept)
        NOTE: TripAdvisor Content API categories may not perfectly match this.
        We keep it as a parameter so the architecture can support both.

    Returns
    -------
    list[dict]
        Candidate locations, usually including num_reviews and location_id.
    """
    # Practical default: TripAdvisor Content API commonly supports "attractions".
    # If your API endpoint supports a separate "activities" category in practice,
    # you can change this mapping here.
    category = "attractions" if item_type in ("attraction", "activity") else "attractions"

    params = {
        "key": TA_API_KEY,
        "category": category,
        "language": language,
    }

    # Prefer latLong pinning for better relevance
    if city_geo.get("lat_long"):
        params["latLong"] = city_geo["lat_long"]
    else:
        params["searchQuery"] = city_geo.get("name")

    r = requests.get(TA_SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])


def details(location_id: str, language: str = "en") -> Dict[str, Any]:
    """
    Fetch detailed information for one TripAdvisor location_id.
    """
    url = TA_DETAILS_URL.format(location_id=location_id)
    params = {"key": TA_API_KEY, "language": language}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def summarize(place: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize TripAdvisor details response into unified schema.

    Notes:
        Many Google-specific fields are not available; we store None.
    """
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
        "types": groups,  # stored in types_json

        "wheelchair_accessible_entrance": None,
        "opening_hours_weekday_descriptions": None,
        "website": place.get("web_url"),
        "phone": None,

        "lat": float(lat) if lat else None,
        "lng": float(lng) if lng else None,
    }