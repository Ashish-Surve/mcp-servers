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
KNOWLEDGE_FOLDER = os.getenv("KNOWLEDGE_FOLDER", "10-Knowledge")
# Parent folder containing all numbered subfolders (02–07).
# Leave empty if these folders are at the vault root.
PLANNING_ROOT = os.getenv("PLANNING_ROOT", "")

if not API_KEY:
    raise RuntimeError("OBSIDIAN_API_KEY is not set. Add it to your .env file.")

# ── Valid sets ───────────────────────────────────────────────────────────────

VALID_CATEGORIES: set[str] = {
    "TimeBlocks", "DataScience", "Investing", "Guitar", "Habits", "Work",
}

# Canonical domain subfolders under KNOWLEDGE_FOLDER.
# Any name is accepted (the Obsidian API creates folders on first write),
# but these are the standard ones — use them for consistency.
KNOWLEDGE_SUBFOLDERS: tuple[str, ...] = (
    "AI-Engineering",
    "Data-Science",
    "Guitar",
    "Health",
    "Investing",
    "MOCs",
    "Personal",
    "References",
)

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

# Tag placeholder token used in unfilled template slots.
# In the raw template file this appears as "#{{tag}}"; after Obsidian/Templater
# processing it may render as "#{tag}". Code that detects "unfilled" slots
# should check for both forms.
TAG_PLACEHOLDER: str = "{{tag}}"
TAG_PLACEHOLDER_RENDERED: str = "{tag}"

# ── Daily note structure ──────────────────────────────────────────────────────
# Headings and field labels used in 01-Templates/Enhanced Daily Template.md
# and replicated in the hardcoded fallback template. Centralized here so
# notes.py has one place to update if the template structure changes.

PRIORITY_HEADING_FMT: str = "### Priority {n}"

FIELD_TASK: str = "**Task:**"
FIELD_FEEDS: str = "**Feeds:**"
FIELD_WHY_IT_MATTERS: str = "**Why it matters:**"
FIELD_TIME_ESTIMATE: str = "**Time estimate:**"
FIELD_TIME_BLOCK: str = "**Time block:**"

# Order of fields below a "### Priority N" heading, used by code that walks
# fixed line offsets. Index 0 corresponds to the line immediately after the
# blank line following the heading (offset +2).
PRIORITY_FIELD_ORDER: tuple[str, ...] = (
    FIELD_TASK, FIELD_FEEDS, FIELD_WHY_IT_MATTERS, FIELD_TIME_ESTIMATE, FIELD_TIME_BLOCK,
)

DATE_MARKER: str = "📅"

# Emoji the Tasks community plugin (https://publish.obsidian.md/tasks) inserts
# into a task line as metadata. These can appear interleaved with our own
# fields (e.g. a Tasks-plugin priority set via right-click, or a recurrence
# rule) and must be tolerated by parsing rather than swallowed into task text
# or silently dropped on rewrite.
TASKS_PLUGIN_PRIORITY_EMOJI: tuple[str, ...] = ("🔺", "⏫", "🔼", "🔽", "⏬")
TASKS_PLUGIN_DATE_EMOJI: tuple[str, ...] = ("➕", "🛫", "⏳", "📅", "✅", "❌")
TASKS_PLUGIN_RECURRENCE_EMOJI: str = "🔁"
# Matches any Tasks-plugin metadata token so it can be detected/preserved
# instead of being treated as task description text.
TASKS_PLUGIN_METADATA_PATTERN: str = (
    r"(?:[🔺⏫🔼🔽⏬🔁➕🛫⏳📅✅❌]\S*(?:\s|$))"
)

# ── Goal hierarchy structure ────────────────────────────────────────────────
# Headings and field labels used in Long-Term-Goals.md, 03-Monthly/*.md,
# and 04-Weekly/*.md. Centralized here so goals.py has one place to update
# if the goal-file structure changes.

MONTHLY_GOALS_HEADING: str = "## Monthly Goals"
WEEKLY_GOALS_HEADING: str = "## Weekly Goals"
REVIEW_SCHEDULE_HEADING: str = "## Review Schedule"
DONE_CHECKLIST_HEADING: str = "### Done?"

FIELD_GOAL: str = "**Goal:**"
FIELD_TIMELINE: str = "**Timeline:**"
FIELD_WHY_MATTERS: str = "**Why this matters:**"
FIELD_SUCCESS_METRIC: str = "**Success metric:**"
FIELD_SUCCESS_LOOKS_LIKE: str = "**Success looks like:**"
FIELD_TIME_NEEDED: str = "**Time needed:**"
FIELD_TIME_BLOCKS: str = "**Time blocks:**"
FIELD_STATUS: str = "**Status:**"
FIELD_LAST_UPDATED: str = "*Last updated:*"

# Status emoji mapping for monthly/weekly goal status updates.
STATUS_EMOJI: dict[str, str] = {
    "not_started": "🔴",
    "in_progress": "🟡",
    "done": "✅",
}
VALID_STATUSES: set[str] = set(STATUS_EMOJI)

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
