# src/pipelines.py
"""
Top-10 pipelines (snapshot + cache) for DABN23.

This module is meant to replace the notebook-defined pipeline functions so that:
- notebooks stay thin (just call functions)
- snapshot + caching logic lives in src/
- TripAdvisor group filtering is applied BEFORE snapshot is saved
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .cache import (
    get_city_snapshot_item_ids,
    save_city_snapshot_item_ids,
    get_cached_item_summary,
    upsert_item_summary,
)

from . import google_places as g
from . import tripadvisor as ta


def top10_google_attractions(
    conn,
    city: str,
    n: int = 10,
    language: str = "en",
    search_pool: int = 50,
) -> List[Dict[str, Any]]:
    """Top-N Google tourist attractions by review_count (static city snapshot)."""
    source, item_type = "google", "attraction"

    # 1) Snapshot lookup
    ids = get_city_snapshot_item_ids(conn, city, source, item_type)
    city_source = "city_snapshot" if ids else "computed"

    # 2) Compute snapshot once (if missing)
    if not ids:
        candidates = g.text_search_many(
            f"tourist attractions in {city}",
            language_code=language,
            max_results=search_pool,
        )

        # Strict filter: only tourist attractions
        filtered = [p for p in candidates if "tourist_attraction" in (p.get("types") or [])]

        # Rank by number of reviews
        ranked = sorted(filtered, key=lambda p: int(p.get("userRatingCount", 0) or 0), reverse=True)

        ids = [p["id"] for p in ranked[:n]]
        save_city_snapshot_item_ids(conn, city, source, item_type, ids)

    # 3) Resolve IDs -> cached details (or fetch once, then cache)
    results: List[Dict[str, Any]] = []
    for pid in ids[:n]:
        cached = get_cached_item_summary(conn, source, pid)
        if cached:
            s = cached
            s["_source"] = "cache"
        else:
            details = g.place_details(pid, language_code=language)
            s = g.summarize(details)
            upsert_item_summary(conn, s)
            s["_source"] = "api"

        s["_city_source"] = city_source
        results.append(s)

    return results


def top10_tripadvisor(
    conn,
    city: str,
    item_type: str = "attraction",
    n: int = 10,
    language: str = "en",
    allow_groups: Optional[List[str]] = None,
    deny_groups: Optional[List[str]] = None,
    search_pool: int = 50,
) -> List[Dict[str, Any]]:
    """
    Top-N TripAdvisor locations by review_count (static city snapshot).

    IMPORTANT:
    - groups are only reliable in details()
    - therefore we apply allow/deny filtering DURING snapshot construction
      and save ONLY accepted ids
    """
    source = "tripadvisor"

    # 1) Snapshot lookup
    ids = get_city_snapshot_item_ids(conn, city, source, item_type)
    city_source = "city_snapshot" if ids else "computed"

    # 2) Compute snapshot once (if missing)
    if not ids:
        city_geo = ta.get_city_location(city, language=language)
        candidates = ta.search(city_geo, item_type=item_type, language=language)

        ranked = sorted(candidates, key=lambda p: int(p.get("num_reviews", 0) or 0), reverse=True)

        accepted_ids: List[str] = []
        for p in ranked[:search_pool]:
            lid = str(p.get("location_id") or "")
            if not lid:
                continue

            # details -> summarize -> filter by groups
            s = ta.details_summarized_filtered(
                lid,
                language=language,
                allow_groups=allow_groups,
                deny_groups=deny_groups,
            )
            if not s:
                continue

            # Cache summary immediately so step 3 usually hits cache
            upsert_item_summary(conn, s)

            accepted_ids.append(lid)
            if len(accepted_ids) >= n:
                break

        ids = accepted_ids
        save_city_snapshot_item_ids(conn, city, source, item_type, ids)

    # 3) Resolve IDs -> cached details (or fetch once, then cache)
    results: List[Dict[str, Any]] = []
    for lid in ids[:n]:
        cached = get_cached_item_summary(conn, source, lid)
        if cached:
            s = cached
            s["_source"] = "cache"
        else:
            details = ta.details(lid, language=language)
            s = ta.summarize(details)
            upsert_item_summary(conn, s)
            s["_source"] = "api"

        s["_city_source"] = city_source
        results.append(s)

    return results


def unified_search(
    conn,
    city: str,
    source: str,
    item_type: str,
    *,
    language: str = "en",
    n: int = 10,
    # TripAdvisor knobs:
    allow_groups: Optional[List[str]] = None,
    deny_groups: Optional[List[str]] = None,
    search_pool: int = 50,
) -> List[Dict[str, Any]]:
    """One UI-facing entrypoint: (city, source, item_type) -> Top-N results."""
    if source == "google":
        if item_type != "attraction":
            return []
        return top10_google_attractions(conn, city, n=n, language=language, search_pool=search_pool)

    if source == "tripadvisor":
        return top10_tripadvisor(
            conn,
            city,
            item_type=item_type,
            n=n,
            language=language,
            allow_groups=allow_groups,
            deny_groups=deny_groups,
            search_pool=search_pool,
        )

    return []


def top10_city(conn, city: str, *, allow_groups=None, deny_groups=None, n: int = 10, language: str = "en", search_pool: int = 50):
    google = top10_google_attractions(conn, city, n=n, language=language, search_pool=search_pool)
    trip = top10_tripadvisor(conn, city, item_type="activity", n=n, language=language,
                             allow_groups=allow_groups, deny_groups=deny_groups, search_pool=search_pool)
    return google + trip