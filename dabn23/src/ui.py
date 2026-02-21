"""
DABN23 Project — UI (ipywidgets)

Purpose:
    Provide reusable ipywidgets UI components to run the project interactively.

Role in architecture:
    Presentation layer — calls pipeline functions, displays tables.

Key responsibilities:
    - Build widgets (city input, source/type dropdowns, search button)
    - Display results as a pandas DataFrame
    - Provide small formatting helpers (opening hours printing)

Dependencies:
    - pandas
    - ipywidgets
    - IPython.display
    - A "search_fn" callable injected from the notebook/app layer

Notes:
    This module should NOT contain API/DB logic. It should only orchestrate
    user inputs and display outputs.
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List

import pandas as pd
import ipywidgets as widgets
from IPython.display import display


def results_to_dataframe(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert a list of unified item summaries into a display-friendly DataFrame.

    Notes:
        We choose columns that are broadly applicable across sources.
        If a column does not exist, we skip it.
    """
    df = pd.DataFrame(results)

    preferred_cols = [
        "source",
        "name",
        "rating",
        "review_count",
        "category_primary",
        "address",
        "website",
        "phone",
        "lat",
        "lng",
        "item_id",
        "_city_source",
        "_source",
    ]
    cols = [c for c in preferred_cols if c in df.columns]
    return df[cols]


def print_opening_hours(summary: Dict[str, Any]) -> None:
    """
    Print opening hours if present (Google typically has this; TripAdvisor often doesn't).
    """
    hours = summary.get("opening_hours_weekday_descriptions") or []
    if not hours:
        print("No opening hours available.")
        return
    for line in hours:
        print(line)


def build_search_widget(
    search_fn: Callable[[str, str, str], List[Dict[str, Any]]]
) -> None:
    """
    Build and display the main search widget UI.

    Parameters
    ----------
    search_fn : callable
        Function signature: search_fn(city, source, item_type) -> results list

        - city: user input city name
        - source: 'google' or 'tripadvisor'
        - item_type: 'attraction' or 'activity'
    """
    # --- Input fields ---
    city_input = widgets.Text(
        value="Paris",
        description="City:",
        placeholder="e.g., Paris, Rome, Stockholm",
        layout=widgets.Layout(width="420px"),
    )

    source_dropdown = widgets.Dropdown(
        options=[("Google Places", "google"), ("TripAdvisor", "tripadvisor")],
        value="google",
        description="Source:",
        layout=widgets.Layout(width="280px"),
    )

    item_type_dropdown = widgets.Dropdown(
        options=[("Attractions", "attraction"), ("Activities", "activity")],
        value="attraction",
        description="Type:",
        layout=widgets.Layout(width="280px"),
    )

    # --- Action button + output area ---
    button = widgets.Button(description="Search Top 10", button_style="primary")
    output = widgets.Output()

    def on_click(_):
        with output:
            output.clear_output()

            city = city_input.value.strip()
            if not city:
                print("Please enter a city name.")
                return

            source = source_dropdown.value
            item_type = item_type_dropdown.value

            print(f"Searching Top 10 | city='{city}' | source={source} | type={item_type}\n")

            try:
                results = search_fn(city, source, item_type)
                if not results:
                    print("No results found.")
                    return

                display(results_to_dataframe(results))

                # Show a small example section
                top = results[0]
                print("\nTop result:")
                print(" - Name:", top.get("name"))
                print(" - Source:", top.get("source"), "| Cache:", top.get("_source"))
                print("\nOpening hours (if available):")
                print_opening_hours(top)

            except Exception as e:
                print("Error:", str(e))

    button.on_click(on_click)

    display(widgets.VBox([
        widgets.HBox([city_input]),
        widgets.HBox([source_dropdown, item_type_dropdown]),
        button,
        output
    ]))