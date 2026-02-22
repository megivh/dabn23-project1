"""
DABN23 Project — Configuration (Environment Variables)

Purpose:
    Centralize reading configuration from environment variables.

Role in architecture:
    Configuration layer — used by all modules.

Key responsibilities:
    - Load API keys and the shared SQLite DB path
    - Fail fast with helpful error messages if missing

Dependencies:
    - os.environ

Notes:
    We intentionally avoid .env files and Colab secrets to keep the project
    environment-agnostic and collaboration-friendly.
"""

from __future__ import annotations
import os


def require_env(name: str) -> str:
    """
    Read an environment variable and throw a clear error if missing.

    Parameters
    ----------
    name : str
        Environment variable name.

    Returns
    -------
    str
        The environment variable value (non-empty).

    Raises
    ------
    RuntimeError
        If the environment variable is not set or empty.
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}\n\n"
            f"Set it like this:\n"
            f"Windows (PowerShell): setx {name} \"your_value_here\"\n"
            f"macOS/Linux: export {name}=your_value_here\n"
        )
    return value


# --- Required configuration ---
GOOGLE_API_KEY = require_env("GOOGLE_MAPS_API_KEY")
TA_API_KEY = require_env("TRIPADVISOR_API_KEY")
DB_PATH = require_env("DABN23_DB_PATH")