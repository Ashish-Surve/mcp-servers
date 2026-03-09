"""
config.py — Constants, validation helpers, and logging for the Obsidian MCP server.

Single source of truth for all configuration values. No other file should
hardcode categories, tags, emoji mappings, or environment variables.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("obsidian-mcp")

# ── Environment ──────────────────────────────────────────────────────────────

OBSIDIAN_URL = os.getenv("OBSIDIAN_URL", "https://127.0.0.1:27124/")
API_KEY = os.getenv("OBSIDIAN_API_KEY")
# Path from vault root to the 05-Daily-Notes folder
DAILY_NOTES_FOLDER = os.getenv("DAILY_NOTES_FOLDER", "05-Daily-Notes")
CALENDAR_FOLDER = os.getenv("CALENDAR_FOLDER", "06-Calendar-Events")
# Parent folder containing all numbered subfolders (02–07).
# Leave empty if these folders are at the vault root.
PLANNING_ROOT = os.getenv("PLANNING_ROOT", "")

if not API_KEY:
    raise RuntimeError("OBSIDIAN_API_KEY is not set. Add it to your .env file.")

# ── Valid sets ───────────────────────────────────────────────────────────────

VALID_CATEGORIES: set[str] = {
    "TimeBlocks", "DataScience", "Investing", "Guitar", "Habits", "Work",
}

VALID_TAGS: set[str] = {
    "datascience", "investing", "guitar", "habits",
    "health", "prep", "learning", "personal",
}

VALID_SECTIONS: dict[str, str] = {
    "ideas": "### Ideas",
    "links": "### Links",
}

# ── Priority definitions ─────────────────────────────────────────────────────

PRIORITY_EMOJI: dict[int, str] = {1: "🔺", 2: "⏫", 3: "🔼"}
VALID_PRIORITIES: set[int] = {1, 2, 3}

# ── Validation helpers ───────────────────────────────────────────────────────


def validate_category(category: str) -> str | None:
    """Return error message if invalid, else None."""
    if category not in VALID_CATEGORIES:
        return f"Category must be one of: {', '.join(sorted(VALID_CATEGORIES))}"
    return None


def validate_priority(priority: int) -> str | None:
    """Return error message if invalid, else None."""
    if priority not in VALID_PRIORITIES:
        return "Priority must be 1, 2, or 3"
    return None
