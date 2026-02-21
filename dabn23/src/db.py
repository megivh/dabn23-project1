"""
DABN23 Project — Database (SQLite)

Purpose:
    Create and maintain the SQLite schema used for caching and snapshots.

Role in architecture:
    Persistence layer — shared cache for Google Places + TripAdvisor.

Key responsibilities:
    - Open SQLite connection (WAL mode)
    - Create tables and indexes (unified schema)
    - Perform minimal one-time migrations from earlier schemas

Dependencies:
    - sqlite3
    - city_top10 table (snapshot)
    - item_summary table (item cache)

Notes:
    The most common issue in evolving notebooks is "table already exists"
    with an old schema. SQLite will NOT add columns on CREATE TABLE IF NOT EXISTS.
    This module includes a small migration to handle that safely.
"""

from __future__ import annotations
import sqlite3
from typing import List


def connect(db_path: str) -> sqlite3.Connection:
    """
    Open a SQLite connection and set WAL mode for better concurrent access.

    Parameters
    ----------
    db_path : str
        Path to the shared SQLite database file.

    Returns
    -------
    sqlite3.Connection
        Active DB connection.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Return True if a table exists in the database."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> List[str]:
    """Return column names for a table."""
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def migrate_if_needed(conn: sqlite3.Connection) -> None:
    """
    Migrate legacy schemas to the unified schema.

    What this migration handles:
    - Old city_top10 schema:
        city_top10(city_key PK, city_display, place_ids_json, created_at_utc)

      New city_top10 schema:
        city_top10(city_key, source, item_type, item_ids_json, ...) as composite PK

    Why:
    - If the old table exists, new code that expects item_ids_json will crash.

    Strategy:
    - Create city_top10_new with the new schema
    - Copy old rows into it (default source='google', item_type='attraction')
    - Drop old table and rename new table

    Notes:
    - This is a one-time migration.
    - We intentionally keep it simple for project scope.
    """
    if not _table_exists(conn, "city_top10"):
        return

    cols = _columns(conn, "city_top10")

    # If already in unified shape, do nothing.
    already_unified = all(c in cols for c in ["source", "item_type", "item_ids_json"])
    if already_unified:
        return

    # Create new table (unified schema)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS city_top10_new (
        city_key       TEXT NOT NULL,   -- normalized city name
        city_display   TEXT,            -- original user input city
        source         TEXT NOT NULL,   -- 'google' or 'tripadvisor'
        item_type      TEXT NOT NULL,   -- 'attraction' or 'activity'
        item_ids_json  TEXT NOT NULL,   -- JSON list of item IDs
        created_at_utc TEXT NOT NULL,
        PRIMARY KEY (city_key, source, item_type)
    );
    """)

    # Copy from old schema if it has place_ids_json
    if "place_ids_json" in cols:
        conn.execute("""
        INSERT OR REPLACE INTO city_top10_new
            (city_key, city_display, source, item_type, item_ids_json, created_at_utc)
        SELECT
            city_key,
            city_display,
            'google' AS source,
            'attraction' AS item_type,
            place_ids_json AS item_ids_json,
            created_at_utc
        FROM city_top10;
        """)
    else:
        # Worst-case fallback: preserve city rows but empty lists
        conn.execute("""
        INSERT OR REPLACE INTO city_top10_new
            (city_key, city_display, source, item_type, item_ids_json, created_at_utc)
        SELECT
            city_key,
            city_display,
            'google',
            'attraction',
            '[]',
            created_at_utc
        FROM city_top10;
        """)

    # Swap tables
    conn.execute("DROP TABLE city_top10;")
    conn.execute("ALTER TABLE city_top10_new RENAME TO city_top10;")
    conn.commit()


def create_tables(conn: sqlite3.Connection) -> None:
    """
    Create the unified schema (if not already present).

    Tables
    ------
    city_top10:
        One row per (city, source, item_type), storing a JSON list of top 10 IDs.

    item_summary:
        Cache of normalized details per (source, item_id), plus summary_json blob.

    Notes
    -----
    We store a compact, normalized set of columns for easy display,
    AND a summary_json blob to preserve flexibility and raw-ish detail.
    """
    conn.execute("""
    CREATE TABLE IF NOT EXISTS city_top10 (
        city_key       TEXT NOT NULL,   -- normalized city identifier
        city_display   TEXT,            -- original city string
        source         TEXT NOT NULL,   -- 'google' | 'tripadvisor'
        item_type      TEXT NOT NULL,   -- 'attraction' | 'activity'
        item_ids_json  TEXT NOT NULL,   -- JSON list of item IDs
        created_at_utc TEXT NOT NULL,
        PRIMARY KEY (city_key, source, item_type)
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS item_summary (
        source         TEXT NOT NULL,   -- 'google' | 'tripadvisor'
        item_id        TEXT NOT NULL,   -- Google: place_id, TA: location_id
        name           TEXT,
        address        TEXT,
        rating         REAL,
        review_count   INTEGER,
        category_primary TEXT,

        -- We keep this generic: Google uses "types", TA uses "groups/tags"
        types_json     TEXT,

        -- Google provides these; TripAdvisor typically does not
        wheelchair_accessible_entrance INTEGER,
        opening_hours_json TEXT,

        website        TEXT,
        phone          TEXT,

        -- Coordinates: needed for routing
        lat            REAL,
        lng            REAL,

        -- Full compacted summary stored for flexibility
        summary_json   TEXT NOT NULL,
        fetched_at_utc TEXT NOT NULL,

        PRIMARY KEY (source, item_id)
    );
    """)

    # Helpful indexes for sorting/searching
    conn.execute("CREATE INDEX IF NOT EXISTS idx_item_review_count ON item_summary(source, review_count);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_item_name ON item_summary(source, name);")

    conn.commit()