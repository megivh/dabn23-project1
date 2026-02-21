"""
DABN23 Project — Routing

Purpose:
    Compute "closest two" items given a start item and a list of other items.

Role in architecture:
    Routing layer — uses stored lat/lng and (optionally) Google Routes API.

Key responsibilities:
    - Validate coordinates exist
    - Compute distances (fallback) OR call Routes API (final)
    - Return the two closest candidates

Dependencies:
    - math (for fallback haversine)
    - In final version: Google Routes API

Notes:
    We provide a fallback (haversine distance) to keep the project runnable
    even before Routes API integration is fully wired.
"""

from __future__ import annotations
from typing import Any, Dict, List
import math


def _haversine_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    """
    Compute great-circle distance between two coordinates.

    Returns
    -------
    float
        Distance in kilometers.
    """
    R = 6371.0
    lat1, lon1 = math.radians(a_lat), math.radians(a_lng)
    lat2, lon2 = math.radians(b_lat), math.radians(b_lng)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def closest_two_fallback(start: Dict[str, Any], others: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Return the two closest items using straight-line distance (fallback).

    Parameters
    ----------
    start : dict
        Must contain lat/lng.

    others : list[dict]
        Each should contain lat/lng; items without coordinates are ignored.

    Returns
    -------
    list[dict]
        The two closest items by haversine distance (km).
    """
    if start.get("lat") is None or start.get("lng") is None:
        raise ValueError("Start item must have lat/lng for distance calculation.")

    valid = [o for o in others if o.get("lat") is not None and o.get("lng") is not None]

    ranked = sorted(
        valid,
        key=lambda o: _haversine_km(start["lat"], start["lng"], o["lat"], o["lng"]),
    )
    return ranked[:2]