"""
DABN23 Project — Google Places Provider (New API)

Purpose:
    Handle all Google Places API calls and normalization into the unified item schema.

Role in architecture:
    Provider layer — fetches + normalizes attractions data from Google.

Key responsibilities:
    - Text search for candidate places
    - Fetch detailed place metadata
    - Normalize into a unified dict used by item_summary cache

Dependencies:
    - requests
    - GOOGLE_API_KEY from config.py

Notes:
    We request only the fields we need using FieldMask to reduce payload size.
"""

from __future__ import annotations
import requests
from typing import Any, Dict, List
from .config import GOOGLE_API_KEY

PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAILS_URL_TMPL = "https://places.googleapis.com/v1/places/{place_id}"


def text_search_many(query: str, language_code: str = "en", max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Google Places Text Search: return a list of candidate places.

    Parameters
    ----------
    query : str
        Free-text query (e.g., "tourist attractions in Paris").

    language_code : str
        BCP-47 language code.

    max_results : int
        Max number of candidates to return.

    Returns
    -------
    list[dict]
        List of candidate place objects.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": ",".join([
            "places.id",
            "places.displayName",
            "places.formattedAddress",
            "places.rating",
            "places.userRatingCount",
            "places.primaryType",
            "places.types",
        ]),
    }

    payload = {"textQuery": query, "languageCode": language_code, "maxResultCount": max_results}
    r = requests.post(PLACES_TEXT_SEARCH_URL, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json().get("places", [])


def place_details(place_id: str, language_code: str = "en") -> Dict[str, Any]:
    """
    Google Places Details: fetch richer fields for one place_id.

    Notes:
        We request 'location' so we can store lat/lng for routing.
    """
    url = PLACES_DETAILS_URL_TMPL.format(place_id=place_id)
    headers = {
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": ",".join([
            "id",
            "displayName",
            "formattedAddress",
            "rating",
            "userRatingCount",
            "primaryType",
            "types",
            "accessibilityOptions",
            "regularOpeningHours",
            "websiteUri",
            "nationalPhoneNumber",
            "location",
        ]),
    }
    r = requests.get(url, headers=headers, params={"languageCode": language_code}, timeout=30)
    r.raise_for_status()
    return r.json()


def summarize(place: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Google Place Details into the unified schema.

    Returns
    -------
    dict
        A unified item summary with keys compatible with cache.upsert_item_summary().
    """
    name = (place.get("displayName") or {}).get("text")
    acc = place.get("accessibilityOptions") or {}
    hours = place.get("regularOpeningHours") or {}
    weekday_desc = hours.get("weekdayDescriptions") or []
    loc = place.get("location") or {}

    return {
        # Unified identity
        "source": "google",
        "item_id": place.get("id"),

        # Shared fields
        "name": name,
        "address": place.get("formattedAddress"),
        "rating": place.get("rating"),
        "review_count": place.get("userRatingCount"),
        "category_primary": place.get("primaryType"),
        "types": place.get("types", []),

        # Google-specific fields
        "wheelchair_accessible_entrance": acc.get("wheelchairAccessibleEntrance"),
        "opening_hours_weekday_descriptions": weekday_desc,
        "website": place.get("websiteUri"),
        "phone": place.get("nationalPhoneNumber"),

        # Coordinates for routing
        "lat": loc.get("latitude"),
        "lng": loc.get("longitude"),
    }