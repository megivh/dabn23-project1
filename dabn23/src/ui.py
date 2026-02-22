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


def build_city_widget(
    search_fn: Callable[[str], List[Dict[str, Any]]],
    *,
    default_city: str = "Paris",
    title: Optional[str] = None,
) -> None:
    """
    Build and display a simplified city-only search widget.

    Parameters
    ----------
    search_fn : callable
        Function signature: search_fn(city) -> results list
    default_city : str
        Prefilled city value.
    title : str | None
        Optional header text above the widget.
    """
    if title:
        display(widgets.HTML(f"<b>{title}</b>"))

    city_input = widgets.Text(
        value=default_city,
        description="City:",
        placeholder="e.g., Paris, Rome, Stockholm",
        layout=widgets.Layout(width="420px"),
    )

    button = widgets.Button(description="Search Top 10", button_style="primary")
    output = widgets.Output()

    def on_click(_):
        with output:
            output.clear_output()

            city = city_input.value.strip()
            if not city:
                print("Please enter a city name.")
                return

            print(f"Searching Top 10 | city='{city}'\n")

            try:
                results = search_fn(city)
                if not results:
                    print("No results found.")
                    return

                display(results_to_dataframe(results))

            except Exception as e:
                print("Error:", str(e))

    button.on_click(on_click)

    display(
        widgets.VBox([
            widgets.HBox([city_input, button]),
            output,
        ])
    )



def build_city_widget(
    search_fn: Callable[[str], List[Dict[str, Any]]],
    default_city: str = "Stockholm",
) -> None:
    """
    City-only UI widget.

    Expects:
        search_fn(city: str) -> List[dict]
    """
    city_input = widgets.Text(
        value=default_city,
        description="City:",
        placeholder="e.g., Paris, Rome, Stockholm",
        layout=widgets.Layout(width="420px"),
    )

    button = widgets.Button(description="Search Top 10", button_style="primary")
    output = widgets.Output()

    def on_click(_):
        with output:
            clear_output()
            city = city_input.value.strip()
            if not city:
                print("Please enter a city name.")
                return

            print(f"Searching Top 10 | city='{city}'\n")

            try:
                results = search_fn(city)
                if not results:
                    print("No results found.")
                    return

                display(results_to_dataframe(results))

            except Exception as e:
                print("Error:", str(e))

    button.on_click(on_click)

    display(widgets.VBox([
        widgets.HBox([city_input, button]),
        output
    ]))