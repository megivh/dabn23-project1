"""
DABN23 Project — UI (ipywidgets)

Purpose:
    Provide reusable ipywidgets UI components to run the project interactively.

Role in architecture:
    Presentation layer — calls pipeline functions, displays tables.

Key responsibilities:
    - Build widgets (city input, search button)
    - Display results as a pandas DataFrame
    - Provide small formatting helpers (opening hours printing)

Dependencies:
    - pandas
    - ipywidgets
    - IPython.display

Notes:
    This module should NOT contain API/DB logic. It should only orchestrate
    user inputs and display outputs.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import ipywidgets as widgets
from IPython.display import display, clear_output

def format_type_label(label: str) -> str:
    """
    Convert Google-style type strings into human-readable labels.

    Examples:
        museum -> Museum
        art_museum -> Art Museum
        tourist_attraction -> Tourist Attraction
    """
    if not isinstance(label, str):
        return label
    return label.replace("_", " ").title()

def results_to_dataframe(results: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(results)

    # --- TripAdvisor: move types (groups) into category_primary for display ---
    if "source" in df.columns:
        is_ta = df["source"] == "tripadvisor"

        if "types" in df.columns:
            # If category_primary is missing/boring (often "Attraction"), show groups instead
            def ta_primary_from_types(v):
                if not isinstance(v, list):
                    return None
                # choose ONE:
                # return v[0] if v else None              # first group only
                return ", ".join(v) if v else None       # all groups joined

            # Overwrite category_primary for TripAdvisor rows using types
            if "category_primary" in df.columns:
                df.loc[is_ta, "category_primary"] = df.loc[is_ta, "types"].apply(ta_primary_from_types)
            else:
                df["category_primary"] = None
                df.loc[is_ta, "category_primary"] = df.loc[is_ta, "types"].apply(ta_primary_from_types)

            # Make 'types' visually empty for TripAdvisor rows (presentation only)
            df.loc[is_ta, "types"] = ""

    preferred_cols = [
        "source",
        "name",
        "rating",
        "review_count",
        "category_primary",
        "address",
        "website",
        "phone"    
    ]
    cols = [c for c in preferred_cols if c in df.columns]
    return df[cols] if cols else df


def print_opening_hours(summary: Dict[str, Any]) -> None:
    """Print opening hours if present (Google typically has this; TripAdvisor often doesn't)."""
    hours = summary.get("opening_hours_weekday_descriptions") or []
    if not hours:
        print("No opening hours available.")
        return
    for line in hours:
        print(line)


from typing import Any, Callable, Dict, List, Optional
import ipywidgets as widgets
from IPython.display import display

def build_city_widget(
    search_fn: Callable[[str], List[Dict[str, Any]]],
    *,
    default_city: str = "Paris",
    title: Optional[str] = None,
    selenium_fn: Optional[Callable[[str], None]] = None,  # optional: run automatically after search
):
    """
    City-only widget with ONE button.

    - Click "Search Top 10" -> runs search_fn(city) and displays results
    - Stores last searched city in returned state dict and in build_city_widget.last_city
    - If selenium_fn is provided, runs it right after search using the same city
    """
    if title:
        display(widgets.HTML(f"<b>{title}</b>"))

    city_input = widgets.Text(
        value=default_city,
        description="City:",
        placeholder="e.g., Paris, Rome, Stockholm",
        layout=widgets.Layout(width="420px"),
    )

    btn_search = widgets.Button(description="Search Top 10", button_style="primary")
    output = widgets.Output()

    # Exposed state you can read later
    state: Dict[str, Any] = {"last_city": None, "last_results": None}

    def on_search(_):
        with output:
            output.clear_output()

            city = city_input.value.strip()
            if not city:
                print("Please enter a city name.")
                return

            # store for later access (robust in notebooks)
            global LAST_SEARCHED_CITY, LAST_SEARCH_RESULTS
            LAST_SEARCHED_CITY = city

            # (optional) keep state dict too if you still want it
            state["last_city"] = city

            print(f"Searching Top 10 | city='{city}'\n")

            try:
                results = search_fn(city)

                # store results for later access
                LAST_SEARCH_RESULTS = results
                state["last_results"] = results

                if not results:
                    print("No results found.")
                    return

                display(results_to_dataframe(results))

                # Optional: run selenium immediately after search (no extra button)
                if selenium_fn is not None:
                    print("\nRunning Selenium...\n")
                    selenium_fn(city)

            except Exception as e:
                print("Error:", str(e))
    btn_search.on_click(on_search)

    display(widgets.VBox([
        widgets.HBox([city_input, btn_search]),
        output,
    ]))

    return state