"""
DABN23 Project — Cache & Snapshots

Purpose:
    Provide reusable database operations for:
    (1) City-level Top 10 snapshots
    (2) Item-level detail caching

Role in architecture:
    Persistence helper layer — shared by Google + TripAdvisor providers.

Key responsibilities:
    - Normalize city names
    - Read/write city snapshots from city_top10
    - Read/write item summaries from item_summary

Dependencies:
    - sqlite3 connection passed in from calling code
    - json for storing lists and full summary objects

Notes:
    We intentionally do NOT expire snapshots (static snapshots) due to the
    short project time window. This keeps behavior deterministic for grading/demo.
"""

from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def normalize_city(city: str) -> str:
    """
    Normalize a city name for consistent DB keys.

    Notes:
        This must match how you store and query city snapshots.
    """
    return city.strip().lower()


# -----------------------------
# City snapshot helpers (Top10)
# -----------------------------

def get_city_snapshot_item_ids(
    conn: sqlite3.Connection,
    city: str,
    source: str,
    item_type: str
) -> Optional[List[str]]:
    """
    Load a stored Top-10 snapshot for a given city/source/type.

    Returns
    -------
    list[str] or None
        The saved item IDs if snapshot exists, otherwise None.
    """
    city_key = normalize_city(city)
    row = conn.execute(
        "SELECT item_ids_json FROM city_top10 WHERE city_key=? AND source=? AND item_type=?",
        (city_key, source, item_type),
    ).fetchone()

    return json.loads(row[0]) if row else None


def save_city_snapshot_item_ids(
    conn: sqlite3.Connection,
    city: str,
    source: str,
    item_type: str,
    item_ids: List[str],
) -> None:
    """
    Save (UPSERT) a Top-10 snapshot.

    Notes:
        This is the "static snapshot" step: once saved, future runs reuse it.
    """
    city_key = normalize_city(city)
    conn.execute(
        """
        INSERT INTO city_top10 (city_key, city_display, source, item_type, item_ids_json, created_at_utc)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(city_key, source, item_type) DO UPDATE SET
            city_display   = excluded.city_display,
            item_ids_json  = excluded.item_ids_json,
            created_at_utc = excluded.created_at_utc
        """,
        (city_key, city.strip(), source, item_type, json.dumps(item_ids), utc_now_iso()),
    )
    conn.commit()


# -----------------------------
# Item detail cache (per item)
# -----------------------------

def get_cached_item_summary(
    conn: sqlite3.Connection,
    source: str,
    item_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached item summary JSON for (source, item_id).

    Returns
    -------
    dict or None
        Parsed JSON summary if present, else None.
    """
    row = conn.execute(
        "SELECT summary_json FROM item_summary WHERE source=? AND item_id=?",
        (source, item_id),
    ).fetchone()

    return json.loads(row[0]) if row else None


def upsert_item_summary(
    conn: sqlite3.Connection,
    summary: Dict[str, Any],
) -> None:
    """
    Insert/update an item summary in the cache.

    Required fields in `summary`:
        - source: 'google' or 'tripadvisor'
        - item_id: place_id or location_id

    Notes:
        We store both:
        - normalized columns (name, rating, lat/lng...)
        - full summary_json (the whole dict) for flexibility
    """
    source = summary.get("source")
    item_id = summary.get("item_id")
    if not source or not item_id:
        raise ValueError("summary must include 'source' and 'item_id'")

    # Convert booleans to SQLite-friendly integers
    w = summary.get("wheelchair_accessible_entrance")
    w_int = 1 if w is True else 0 if w is False else None

    # Lists stored as JSON strings
    types = summary.get("types")
    types_json = json.dumps(types, ensure_ascii=False) if types is not None else None

    hours = summary.get("opening_hours_weekday_descriptions")
    hours_json = json.dumps(hours, ensure_ascii=False) if hours is not None else None

    conn.execute(
        """
        INSERT INTO item_summary (
            source, item_id, name, address, rating, review_count, category_primary,
            types_json, wheelchair_accessible_entrance, opening_hours_json,
            website, phone, lat, lng, summary_json, fetched_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source, item_id) DO UPDATE SET
            name=excluded.name,
            address=excluded.address,
            rating=excluded.rating,
            review_count=excluded.review_count,
            category_primary=excluded.category_primary,
            types_json=excluded.types_json,
            wheelchair_accessible_entrance=excluded.wheelchair_accessible_entrance,
            opening_hours_json=excluded.opening_hours_json,
            website=excluded.website,
            phone=excluded.phone,
            lat=excluded.lat,
            lng=excluded.lng,
            summary_json=excluded.summary_json,
            fetched_at_utc=excluded.fetched_at_utc
        """,
        (
            source,
            item_id,
            summary.get("name"),
            summary.get("address"),
            summary.get("rating"),
            summary.get("review_count"),
            summary.get("category_primary"),
            types_json,
            w_int,
            hours_json,
            summary.get("website"),
            summary.get("phone"),
            summary.get("lat"),
            summary.get("lng"),
            json.dumps(summary, ensure_ascii=False),
            utc_now_iso(),
        ),
    )
    conn.commit()