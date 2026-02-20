"""
Obsidian MCP Server
===================
MCP interface for Obsidian daily notes, goals, and calendar events.

Designed for reliability with smaller LLMs: 11 focused tools with
minimal required parameters and sensible defaults.

Tool surface:
  Daily note  — get_daily_note, set_priority, clear_priority, add_note, plan_tomorrow
  Goals       — get_goals, add_goal, update_goal_status
  Calendar    — create_event, list_events, delete_event

Prerequisites:
  1. Install "Local REST API" plugin in Obsidian (Community Plugins)
  2. Enable it and copy the API key from its settings
  3. pip install mcp httpx python-dotenv
"""

from mcp.server.fastmcp import FastMCP
from config import validate_priority, validate_category
from vault import VaultClient
from notes import DailyNote
from events import CalendarManager
from goals import GoalsManager

# ── Bootstrap ────────────────────────────────────────────────────────────────

mcp = FastMCP("obsidian-daily-notes")
vault = VaultClient()
notes = DailyNote(vault)
cal = CalendarManager(vault, notes)
goals_mgr = GoalsManager(vault)


# ── Daily Note Tools ──────────────────────────────────────────────────────────


@mcp.tool()
def get_today() -> str:
    """
    Return today's date in YYYY-MM-DD format.
    Use this whenever a tool requires a date and you are not sure what today is.

    Returns:
        Today's date as YYYY-MM-DD. E.g. "2026-02-20"
    """
    return notes.today()


@mcp.tool()
def get_daily_note(date: str = "") -> str:
    """
    Read today's daily note. Creates it automatically if it doesn't exist yet.

    Args:
        date: Date as YYYY-MM-DD. Leave empty for today.

    Returns:
        The full markdown content of the daily note.
    """
    target = date or notes.today()
    content = notes.read(target)
    if not content:
        notes.create(target)
        content = notes.read(target)
    return content or f"❌ Failed to read or create daily note for {target}."


@mcp.tool()
def set_priority(
    slot: int,
    task: str,
    date: str = "",
    tag: str = "",
    duration: str = "",
    start_time: str = "",
    end_time: str = "",
    category: str = "",
) -> str:
    """
    Add a task to a priority slot in the daily note.

    Provide start_time + end_time + category to also create a calendar event
    and link it to the priority slot's time block in one step.

    Args:
        slot:       Priority slot: 1 (highest 🔺), 2 (high ⏫), or 3 (medium 🔼)
        task:       Task description. E.g. "Review ML flashcards"
        date:       Date as YYYY-MM-DD. Leave empty for today.
        tag:        Category tag. One of: datascience, guitar, habits, health,
                    investing, learning, personal, prep.
                    Defaults to "personal" if not provided.
        duration:   Time estimate. E.g. "90 min", "2 hours"
        start_time: Start time HH:MM (24h) — required for calendar scheduling. E.g. "09:00"
        end_time:   End time HH:MM (24h) — required for calendar scheduling. E.g. "11:00"
        category:   Calendar category — required for scheduling.
                    One of: TimeBlocks, DataScience, Investing, Guitar, Habits, Work

    Returns:
        Success message.
    """
    target = date or notes.today()

    err = validate_priority(slot)
    if err:
        return f"❌ {err}"

    scheduling = bool(start_time and end_time and category)
    if scheduling:
        err = validate_category(category)
        if err:
            return f"❌ {err}"

    resolved_tag = tag or "personal"

    time_block = ""
    if scheduling:
        note_name = CalendarManager.event_note_name(target, task)
        time_block = f"[[{note_name}]]"

    try:
        notes.fill_priority(target, slot, task, resolved_tag, duration, "", time_block)
    except ValueError as exc:
        return f"❌ {exc}"

    if scheduling:
        event_result = cal.create_event(task, start_time, end_time, category, target)
        return f"✅ Priority {slot} set: {task} | {event_result}"

    return f"✅ Priority {slot} set: {task}"


@mcp.tool()
def clear_priority(slot: int, date: str = "") -> str:
    """
    Clear a priority slot back to its empty state so it can be filled again.

    Args:
        slot: Priority slot to clear: 1, 2, or 3
        date: Date as YYYY-MM-DD. Leave empty for today.

    Returns:
        Success message.
    """
    target = date or notes.today()

    err = validate_priority(slot)
    if err:
        return f"❌ {err}"

    try:
        notes.clear_priority(target, slot)
    except ValueError as exc:
        return f"❌ {exc}"

    return f"✅ Cleared priority slot {slot}."


@mcp.tool()
def add_note(
    type: str,
    content: str,
    date: str = "",
) -> str:
    """
    Capture a quick note in today's daily note under Ideas or Links.

    Args:
        type:    Where to add it: "idea" or "link"
        content: The text or URL to capture.
        date:    Date as YYYY-MM-DD. Leave empty for today.

    Returns:
        Success message.
    """
    target = date or notes.today()

    section_map = {"idea": "ideas", "link": "links"}
    section = section_map.get(type)
    if not section:
        return "❌ type must be 'idea' or 'link'."

    try:
        notes.add_quick_note(target, section, content)
    except ValueError as exc:
        return f"❌ {exc}"

    return f"✅ Added {type}: {content}"


@mcp.tool()
def plan_tomorrow(
    slot: int,
    task: str,
    tag: str = "",
    date: str = "",
) -> str:
    """
    Set one of tomorrow's top 3 priorities in today's Tomorrow Prep section.

    Args:
        slot: Priority slot: 1, 2, or 3
        task: Task description. E.g. "Morning workout"
        tag:  Category tag. One of: datascience, guitar, habits, health,
              investing, learning, personal, prep.
              Defaults to "personal" if not provided.
        date: Today's date as YYYY-MM-DD. Leave empty for today.

    Returns:
        Success message.
    """
    target = date or notes.today()

    err = validate_priority(slot)
    if err:
        return f"❌ {err}"

    resolved_tag = tag or "personal"

    try:
        notes.fill_tomorrow_priority(target, slot, task, resolved_tag)
    except ValueError as exc:
        return f"❌ {exc}"

    return f"✅ Tomorrow priority {slot}: {task}"


# ── Goal Tools ────────────────────────────────────────────────────────────────


@mcp.tool()
def get_goals(level: str = "all") -> str:
    """
    Read your goal hierarchy.

    Args:
        level: Which goals to read: "longterm", "monthly", "weekly", or "all" (default)

    Returns:
        Content of the requested goal file(s).
    """
    return goals_mgr.read_goals(level)


@mcp.tool()
def add_goal(
    level: str,
    code: str,
    goal: str,
    feeds: str = "",
    description: str = "",
) -> str:
    """
    Add a goal to the goal hierarchy. Creates the file automatically if needed.

    Args:
        level:       Goal level: "longterm", "monthly", or "weekly"
        code:        Goal identifier.
                       Long-term → category code, e.g. "DS" or "GT"
                       Monthly   → CATEGORY-M#, e.g. "DS-M1"
                       Weekly    → CATEGORY-W#, e.g. "DS-W1"
        goal:        Goal description. E.g. "Complete pandas + SQL modules"
        feeds:       What this goal feeds into (leave empty for longterm goals).
                       Monthly goals  → long-term code, e.g. "DS"
                       Weekly goals   → monthly code,    e.g. "DS-M1"
        description: Why this matters or any context.
                     E.g. "Core skill for the ML role I'm targeting"

    Returns:
        Success message.
    """
    return goals_mgr.add_goal(level, code, goal, feeds, description)


@mcp.tool()
def update_goal_status(
    code: str,
    level: str,
    status: str,
    progress_note: str = "",
) -> str:
    """
    Update the status of a monthly or weekly goal.

    Args:
        code:          Goal code. E.g. "DS-M1" or "DS-W1"
        level:         "monthly" or "weekly"
        status:        "not_started" 🔴, "in_progress" 🟡, or "done" ✅
        progress_note: Optional progress detail. E.g. "(2 of 3 lessons done)"

    Returns:
        Success message.
    """
    return goals_mgr.update_goal_status(code, status, level, progress_note)


# ── Calendar Tools ────────────────────────────────────────────────────────────


@mcp.tool()
def create_event(
    title: str,
    start_time: str,
    end_time: str,
    category: str,
    date: str = "",
    priority: int = 0,
) -> str:
    """
    Create a time-block event in Obsidian Full Calendar.

    If priority (1–3) is given, also links the event to that slot's
    time block field in the daily note.

    Args:
        title:      Event title. E.g. "Guitar practice"
        start_time: Start time HH:MM (24h). E.g. "18:00"
        end_time:   End time HH:MM (24h). E.g. "19:00"
        category:   One of: TimeBlocks, DataScience, Investing, Guitar, Habits, Work
        date:       Date as YYYY-MM-DD. Leave empty for today.
        priority:   1, 2, or 3 — links this event to that priority's time block.
                    Leave 0 (default) to skip linking.

    Returns:
        Success message.
    """
    target = date or notes.today()
    return cal.create_event(title, start_time, end_time, category, target, priority)


@mcp.tool()
def list_events(category: str, date: str = "") -> str:
    """
    List calendar events in a category, optionally filtered to a specific date.

    Args:
        category: One of: TimeBlocks, DataScience, Investing, Guitar, Habits, Work
        date:     Date as YYYY-MM-DD to filter by. Leave empty to list all.

    Returns:
        List of events in that category.
    """
    return cal.list_events(category, date)


@mcp.tool()
def delete_event(title: str, category: str, date: str = "") -> str:
    """
    Delete a calendar event. Use list_events first to confirm the exact title.

    Args:
        title:    Exact event title used when creating. E.g. "Guitar practice"
        category: One of: TimeBlocks, DataScience, Investing, Guitar, Habits, Work
        date:     Date as YYYY-MM-DD. Leave empty for today.

    Returns:
        Success or error message.
    """
    target = date or notes.today()
    return cal.delete_event(title, category, target)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
