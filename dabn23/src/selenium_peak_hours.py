"""
DABN23 Project — Selenium Peak-Hours Scraper

Purpose:
    Retrieve real-time crowdedness ("Popular Times") data from
    Google Maps for stored attractions.

Role in architecture:
    Live data retrieval layer — complements the static API-based
    dataset with dynamic, real-time busyness information.

Key responsibilities:
    - Retrieve attraction names from the SQL database
    - Automate Google Maps search via Selenium
    - Extract full-day hourly busyness data
    - Store results in a structured dictionary format

Dependencies:
    - selenium (WebDriver, waits, selectors)
    - sqlite3 (database access)
    - re (aria-label parsing)
    - datetime (timestamping)
    - time (controlled pacing)

Notes:
    Execution requires consistent Google Maps language rendering.
    A VPN connected to an English-speaking country is recommended.
    Scraping is deliberately slowed to reduce blocking risk.
"""

from __future__ import annotations
from typing import Dict, List, Optional
import json
import sqlite3
import datetime
import time
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# ---------------------------------------------------------------------
# Database utilities
# ---------------------------------------------------------------------

def get_attraction_names(city: str, conn: sqlite3.Connection) -> Optional[List[str]]:
    """
    Retrieve stored Google attraction names for a given city.

    Returns
    -------
    list[str] or None
        Ordered list of attraction names,
        or None if the city is not stored.
    """
    citykey = city.strip().lower()
    cur = conn.cursor()

    row = cur.execute(
        "SELECT item_ids_json FROM city_top10 "
        "WHERE city_key = ? AND source = ? AND item_type = ?",
        (citykey, "google", "attraction")
    ).fetchone()

    if not row:
        return None

    place_ids = json.loads(row[0])
    if not place_ids:
        return []

    placeholders = ",".join("?" * len(place_ids))
    name_rows = cur.execute(
        f"SELECT item_id, name FROM item_summary "
        f"WHERE source = ? AND item_id IN ({placeholders})",
        ["google", *place_ids]
    ).fetchall()

    name_map = {pid: name for pid, name in name_rows}
    return [name_map[pid] for pid in place_ids if pid in name_map]


# ---------------------------------------------------------------------
# Peak-hours parsing
# ---------------------------------------------------------------------

def _parse_busy_bar(aria: str):
    """
    Parse one Google Maps peak-hours aria-label.

    Supports:
        - English format (e.g., "77% busy at 2 pm")
        - Nordic format (e.g., "37 aktivitet kl. 1300.")

    Returns
    -------
    tuple[int, int] or None
        (hour_24, percentage)
    """
    m = re.search(r"^(\d+)\D+?kl\.\s*(\d{2})\d{2}", aria.strip())
    if m:
        return int(m.group(2)), int(m.group(1))

    m = re.search(r"(\d+)%.*?(\d{1,2})\s*(am|pm)", aria, re.IGNORECASE)
    if m:
        pct, h, mer = int(m.group(1)), int(m.group(2)), m.group(3).lower()
        hour_24 = (h % 12) + (12 if mer == "pm" else 0)
        return hour_24, pct

    return None


def dismiss_google_consent(driver):
    """
    Attempt to dismiss Google Maps GDPR consent banner.
    """
    try:
        accept_btn = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//button[.//span[contains(text(),"Accept all") '
                'or contains(text(),"Reject all")]]'
            ))
        )
        accept_btn.click()
        time.sleep(1)
    except Exception:
        pass


# ---------------------------------------------------------------------
# Core scraping logic
# ---------------------------------------------------------------------

def get_current_busyness(driver, attraction_name: str) -> Optional[List[Optional[int]]]:
    """
    Scrape full-day hourly busyness for a single attraction.

    Returns
    -------
    list[int|None] or None
        24-length list indexed by hour (0–23),
        or None if no peak-hours section is available.
    """
    driver.get("https://www.google.com/maps")
    time.sleep(2)
    dismiss_google_consent(driver)

    search_bar = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, "searchboxinput"))
    )

    search_bar.clear()
    search_bar.send_keys(attraction_name)
    search_bar.submit()
    time.sleep(3)

    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.hfpxzc"))
        ).click()
        time.sleep(3)
    except TimeoutException:
        pass

    try:
        peak_section = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.UmE4Qe"))
        )
    except TimeoutException:
        return None

    hourly_data: List[Optional[int]] = [None] * 24
    bars = peak_section.find_elements(By.CSS_SELECTOR, "div.dpoVLd")

    for bar in bars:
        aria = bar.get_attribute("aria-label") or ""
        parsed = _parse_busy_bar(aria)
        if parsed:
            hour_24, pct = parsed
            if 0 <= hour_24 <= 23:
                hourly_data[hour_24] = pct

    return hourly_data


def scrape_peak_hours(
    city: str,
    conn: sqlite3.Connection,
    driver,
    busyness_data: Dict[str, Dict],
):
    """
    Scrape peak-hours data for all stored attractions of a city.

    Results are stored in the provided `busyness_data` dictionary.
    """
    scraped_at = datetime.datetime.now().strftime("%H:%M")
    city_key = city.strip()

    names = get_attraction_names(city_key, conn)
    if not names:
        return

    attractions = {}

    for name in names:
        hourly = get_current_busyness(driver, name)
        attractions[name] = hourly
        time.sleep(2)

    busyness_data[city_key] = {
        "scraped_at": scraped_at,
        "attractions": attractions,
    }