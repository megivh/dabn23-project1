"""
DABN23 Project — Selenium Driver

Purpose:
    Configure and initialize a Selenium Chrome WebDriver instance
    for automated Google Maps interaction.

Role in architecture:
    Infrastructure layer — provides a standardized browser instance
    used by the Selenium scraping pipeline.

Key responsibilities:
    - Configure Chrome options (language, user-agent, headless mode)
    - Apply geolocation override (for consistent Maps behavior)
    - Return a ready-to-use WebDriver instance

Dependencies:
    - selenium.webdriver
    - Chrome browser installed locally

Notes:
    Google Maps rendering depends heavily on region and language.
    For reliable execution, a VPN connected to an English-speaking
    country is recommended to ensure consistent DOM structure.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def make_driver(headless: bool = True):
    """
    Create and return a configured Chrome WebDriver instance.

    Parameters
    ----------
    headless : bool, default=True
        Whether to run Chrome in headless mode.

    Returns
    -------
    webdriver.Chrome
        Configured Selenium Chrome driver.
    """
    options = Options()
    options.add_argument("--lang=en-US")

    if headless:
        options.add_argument("--headless=new")

    options.add_experimental_option("prefs", {
        "intl.accept_languages": "en-US,en",
        "profile.default_content_setting_values.geolocation": 2,
    })

    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)

    # Geolocation override (stabilizes Maps rendering)
    driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy": 100,
    })

    return driver