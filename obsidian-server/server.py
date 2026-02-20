"""
Obsidian Daily Note MCP Server
================================
Lets Claude read and update your Obsidian daily notes and goal hierarchy
via the Local REST API plugin.

This file defines the MCP tools as thin wrappers that validate inputs
and delegate to the domain classes in notes.py, events.py, goals.py, and vault.py.

Prerequisites:
  1. Install "Local REST API" plugin in Obsidian (Community Plugins)
  2. Enable it and note the API key from its settings
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
def read_daily_note(note_date: str = "") -> str:
    """
    Read the full content of a daily note.

    Args:
        note_date: Date as YYYY-MM-DD. Leave empty for today.

    Returns:
        The markdown content of the note, or a message if it doesn't exist.
    """
    target = note_date or notes.today()
    content = notes.read(target)
    if not content:
        return f"No daily note found for {target}. Use create_daily_note to make one."
    return content


@mcp.tool()
def create_daily_note(note_date: str = "") -> str:
    """
    Create a new daily note from the built-in template.
    Only creates if it doesn't already exist.

    Args:
        note_date: Date as YYYY-MM-DD. Leave empty for today.

    Returns:
        Success message or notice that note already exists.
    """
    target = note_date or notes.today()
    return notes.create(target)


@mcp.tool()
def add_priority_task(
    task_name: str,
    priority: int,
    tag: str,
    time_estimate: str,
    why_it_matters: str = "",
    goal_code: str = "",
    start_time: str = "",
    end_time: str = "",
    category: str = "",
    note_date: str = "",
) -> str:
    """
    Add a task to one of the 3 priority slots in the Priorities section.

    If goal_code is provided, the Feeds line will link to the weekly goal:
    [[YYYY-W###{goal_code}]].

    If start_time, end_time, and category are all provided, a Full Calendar
    event is automatically created and the Time block field will show a
    wikilink [[YYYY-MM-DD Task Name]] pointing to that event note.

    Args:
        task_name:      What the task is. E.g. "Prep for ML interview"
        priority:       1 (highest), 2 (high), or 3 (medium)
        tag:            One of: datascience, investing, guitar, habits, health,
                        prep, learning, personal
        time_estimate:  How long it will take. E.g. "2 hours"
        why_it_matters: Short reason this task is important (optional)
        goal_code:      Weekly goal code this task feeds. E.g. "DS-W1" (optional)
        start_time:     Start time HH:MM (24h) for the calendar event. E.g. "09:00"
        end_time:       End time HH:MM (24h) for the calendar event. E.g. "11:00"
        category:       Calendar category: TimeBlocks, DataScience, Investing,
                        Guitar, Habits, Work — required when scheduling
        note_date:      Date as YYYY-MM-DD. Leave empty for today.

    Returns:
        Success message.
    """
    target = note_date or notes.today()

    # Validate all inputs before any writes
    err = validate_priority(priority)
    if err:
        return f"❌ {err}"

    scheduling = bool(start_time and end_time and category)

    if scheduling:
        err = validate_category(category)
        if err:
            return f"❌ {err}"

    # Build time block value (wikilink if scheduling, else empty)
    time_block = ""
    if scheduling:
        note_name = CalendarManager.event_note_name(target, task_name)
        time_block = f"[[{note_name}]]"

    # Fill the priority slot in the daily note
    try:
        notes.fill_priority(
            target, priority, task_name, tag,
            time_estimate, why_it_matters, time_block,
            goal_code=goal_code,
        )
    except ValueError as exc:
        return f"❌ {exc}"

    # Create calendar event if scheduling info was provided
    if scheduling:
        event_result = cal.create_event(
            title=task_name,
            start=start_time,
            end=end_time,
            category=category,
            event_date=target,
        )
        return f"✅ Added Priority {priority} task: {task_name} | {event_result}"

    return f"✅ Added Priority {priority} task: {task_name}"


@mcp.tool()
def set_time_block(
    priority: int,
    time_block: str,
    note_date: str = "",
) -> str:
    """
    Set the time block for an already-added priority task.
    Use this when you know the task but want to schedule it separately.

    Args:
        priority:   1, 2, or 3
        time_block: E.g. "9:00 AM - 11:00 AM"
        note_date:  Date as YYYY-MM-DD. Leave empty for today.

    Returns:
        Success message.
    """
    target = note_date or notes.today()

    err = validate_priority(priority)
    if err:
        return f"❌ {err}"

    try:
        notes.set_time_block(target, priority, time_block)
    except ValueError as exc:
        return f"❌ {exc}"

    return f"✅ Set time block for Priority {priority}: {time_block}"


@mcp.tool()
def clear_priority_task(
    priority: int,
    note_date: str = "",
) -> str:
    """
    Clear a priority slot back to its empty template state.
    Useful for removing or replacing a task you've already added.

    Args:
        priority:  1, 2, or 3
        note_date: Date as YYYY-MM-DD. Leave empty for today.

    Returns:
        Success message.
    """
    target = note_date or notes.today()

    err = validate_priority(priority)
    if err:
        return f"❌ {err}"

    try:
        notes.clear_priority(target, priority)
    except ValueError as exc:
        return f"❌ {exc}"

    return f"✅ Cleared Priority {priority} slot — ready to be filled again."


@mcp.tool()
def add_quick_note(
    section: str,
    note_text: str,
    note_date: str = "",
) -> str:
    """
    Append a quick note to one of the capture sections at the bottom.

    Args:
        section:   One of: "ideas", "links"
        note_text: The content to add.
        note_date: Date as YYYY-MM-DD. Leave empty for today.
    """
    target = note_date or notes.today()

    try:
        notes.add_quick_note(target, section, note_text)
    except ValueError as exc:
        return f"❌ {exc}"

    return f"✅ Added note to {section}: {note_text}"


@mcp.tool()
def add_tomorrow_priority(
    task_name: str,
    priority: int,
    tag: str,
    note_date: str = "",
) -> str:
    """
    Add one of tomorrow's top 3 priorities (in the Tomorrow's Prep section).

    Args:
        task_name: Task description.
        priority:  1, 2, or 3
        tag:       Tag from standard list.
        note_date: Base date (today) as YYYY-MM-DD. Leave empty for today.
    """
    target = note_date or notes.today()

    err = validate_priority(priority)
    if err:
        return f"❌ {err}"

    try:
        notes.fill_tomorrow_priority(target, priority, task_name, tag)
    except ValueError as exc:
        return f"❌ {exc}"

    return f"✅ Added tomorrow's priority {priority}: {task_name}"


# ── Calendar Tools ────────────────────────────────────────────────────────────


@mcp.tool()
def create_calendar_event(
    title: str,
    start: str,
    end: str,
    category: str,
    date: str = "",
    priority: int = 0,
) -> str:
    """
    Create a Full Calendar event by writing a note into the correct
    06-Calendar-Events/<category>/ folder. The event will appear in
    Obsidian's Full Calendar view immediately.

    If priority (1–3) is given, also updates that priority's Time block
    in the daily note with a wikilink to the created event.

    Args:
        title:    Event title. E.g. "ML Interview Prep"
        start:    Start time in HH:MM (24h). E.g. "09:00"
        end:      End time in HH:MM (24h). E.g. "11:00"
        category: One of: TimeBlocks, DataScience, Investing, Guitar,
                  Habits, Work
        date:     Date as YYYY-MM-DD. Leave empty for today.
        priority: 1, 2, or 3 — if set, links this event in the daily note's
                  time block field for that priority. Leave 0 to skip.

    Returns:
        Success message.
    """
    target = date or notes.today()
    return cal.create_event(title, start, end, category, target, priority)


@mcp.tool()
def list_calendar_events(category: str, date: str = "") -> str:
    """
    List all calendar event notes in a given category folder for a date.
    Use this before deleting to confirm the exact event title.

    Args:
        category: One of: TimeBlocks, DataScience, Investing, Guitar, Habits, Work
        date:     Date as YYYY-MM-DD to filter by. Leave empty to list all.

    Returns:
        List of event filenames in that category.
    """
    return cal.list_events(category, date)


@mcp.tool()
def delete_calendar_event(title: str, category: str, date: str = "") -> str:
    """
    Delete a calendar event note from a category folder.
    Use list_calendar_events first to confirm the exact title.

    Args:
        title:    Exact event title used when creating. E.g. "Meet Amit"
        category: One of: TimeBlocks, DataScience, Investing, Guitar, Habits, Work
        date:     Date as YYYY-MM-DD. Leave empty for today.

    Returns:
        Success or error message.
    """
    target = date or notes.today()
    return cal.delete_event(title, category, target)


# ── Goal Tools ────────────────────────────────────────────────────────────────


@mcp.tool()
def read_goals(
    level: str = "all",
    month: str = "",
    week: str = "",
) -> str:
    """
    Read the goal hierarchy — long-term, monthly, and/or weekly goal files.

    Args:
        level: Which level(s) to read. One of: "longterm", "monthly", "weekly",
               or "all" (default).
        month: Month as YYYY-MM. Defaults to current month.
        week:  Week as YYYY-W##. Defaults to current ISO week.

    Returns:
        Concatenated content of the requested goal file(s).
    """
    return goals_mgr.read_goals(level, month, week)


@mcp.tool()
def create_monthly_goals(month: str = "") -> str:
    """
    Create a new monthly goals file from template.
    Only creates if it doesn't already exist.

    Args:
        month: Month as YYYY-MM. Defaults to current month.

    Returns:
        Success message or notice that file already exists.
    """
    return goals_mgr.create_monthly_goals(month)


@mcp.tool()
def add_monthly_goal(
    goal_code: str,
    goal: str,
    feeds: str,
    why_it_matters: str = "",
    success_metric: str = "",
    time_needed: str = "",
    month: str = "",
) -> str:
    """
    Add a goal under the '## Monthly Goals' section of a monthly file.

    Args:
        goal_code:      Goal identifier. Format: {CATEGORY}-M{N}. E.g. "DS-M1"
        goal:           Goal description. E.g. "Complete pandas + SQL modules"
        feeds:          Long-term goal category code. E.g. "DS", "GT", "H"
        why_it_matters: Motivation for the goal (optional)
        success_metric: How to measure completion (optional)
        time_needed:    Hours per week estimate (optional)
        month:          Month as YYYY-MM. Defaults to current month.

    Returns:
        Success message.
    """
    return goals_mgr.add_monthly_goal(
        goal_code, goal, feeds, why_it_matters, success_metric, time_needed, month
    )


@mcp.tool()
def create_weekly_goals(
    week: str = "",
    start_date: str = "",
    end_date: str = "",
) -> str:
    """
    Create a new weekly goals file from template.
    Only creates if it doesn't already exist.

    Args:
        week:       Week as YYYY-W##. Defaults to current ISO week.
        start_date: Week start date as YYYY-MM-DD (calculated if omitted).
        end_date:   Week end date as YYYY-MM-DD (calculated if omitted).

    Returns:
        Success message or notice that file already exists.
    """
    return goals_mgr.create_weekly_goals(week, start_date, end_date)


@mcp.tool()
def add_weekly_goal(
    goal_code: str,
    goal: str,
    feeds: str,
    time_blocks: str = "",
    week: str = "",
) -> str:
    """
    Add a goal under the '## Weekly Goals' section of a weekly file.
    Also adds a checkbox to the Done? review section.

    Args:
        goal_code:   Goal identifier. Format: {CATEGORY}-W{N}. E.g. "DS-W1"
        goal:        Goal description. E.g. "3 pandas lessons"
        feeds:       Monthly goal code to link to. E.g. "DS-M1"
        time_blocks: Time allocation. E.g. "3 hours" (optional)
        week:        Week as YYYY-W##. Defaults to current ISO week.

    Returns:
        Success message.
    """
    return goals_mgr.add_weekly_goal(goal_code, goal, feeds, time_blocks, week)


@mcp.tool()
def update_goal_status(
    goal_code: str,
    status: str,
    level: str,
    progress_note: str = "",
    file_id: str = "",
) -> str:
    """
    Update the status emoji on a monthly or weekly goal.

    Args:
        goal_code:     The goal code. E.g. "DS-M1" or "DS-W1"
        status:        One of: "not_started" (🔴), "in_progress" (🟡), "done" (✅)
        level:         "monthly" or "weekly"
        progress_note: Optional progress detail. E.g. "(2/3 lessons done)"
        file_id:       File ID: YYYY-MM or YYYY-W##. Defaults to current.

    Returns:
        Success message.
    """
    return goals_mgr.update_goal_status(goal_code, status, level, progress_note, file_id)


@mcp.tool()
def add_longterm_goal(
    code: str,
    goal: str,
    timeline: str,
    why_it_matters: str,
    success_looks_like: str,
) -> str:
    """
    Add a new goal to Long-Term-Goals.md.

    Args:
        code:               Short category code. E.g. "RD" for Reading
        goal:               Goal description. E.g. "Read 24 books per year"
        timeline:           E.g. "End of 2027", "Ongoing"
        why_it_matters:     Motivation for this goal
        success_looks_like: Concrete description of success

    Returns:
        Success message.
    """
    return goals_mgr.add_longterm_goal(code, goal, timeline, why_it_matters, success_looks_like)


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
