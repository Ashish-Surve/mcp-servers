"""Obsidian MCP Server — daily notes, goals, calendar events."""

from datetime import datetime, date, timedelta
import re

from mcp.server.fastmcp import FastMCP
from config import validate_priority, validate_category, DAILY_NOTES_FOLDER, KNOWLEDGE_FOLDER, KNOWLEDGE_SUBFOLDERS, PRIORITY_EMOJI
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
    """Return today's date as YYYY-MM-DD. Use when unsure of today's date."""
    return notes.today()


@mcp.tool()
def get_daily_note(date: str = "") -> str:
    """Read (or auto-create) a daily note. date: YYYY-MM-DD, empty=today."""
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
    feeds: str = "",
    why: str = "",
    start_time: str = "",
    end_time: str = "",
    category: str = "",
) -> str:
    """
    Set a priority slot in the daily note. Pass start_time+end_time+category to also create a linked calendar event.

    slot: 1=highest, 2=high, 3=medium | tag: datascience/guitar/habits/health/investing/learning/personal/prep
    feeds: Obsidian link chain e.g. "[[2026-W08#DS-W1]] → [[2026-02#DS-M1]] → [[Long-Term-Goals#DS]]"
    why: one-line reason e.g. "Build gym habit 3x/week throughout March"
    category: TimeBlocks/DataScience/Investing/Guitar/Habits/Work | date: YYYY-MM-DD, empty=today
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
        notes.fill_priority(target, slot, task, resolved_tag, duration, why, time_block, feeds)
    except ValueError as exc:
        return f"❌ {exc}"

    if scheduling:
        event_result = cal.create_event(task, start_time, end_time, category, target)
        return f"✅ Priority {slot} set: {task} | {event_result}"

    return f"✅ Priority {slot} set: {task}"


@mcp.tool()
def update_priority(
    slot: int,
    date: str = "",
    task: str = "",
    feeds: str = "",
    why: str = "",
    time_estimate: str = "",
    time_block: str = "",
    completed: bool = False,
) -> str:
    """
    Patch fields in an existing priority slot without touching the rest. At least one field required.

    slot: 1–3 | date: YYYY-MM-DD, empty=today
    feeds: Obsidian link chain | why: one-line reason | time_estimate: e.g. "30 min"
    time_block: Obsidian link to event e.g. "[[2026-03-09 Deep Work]]"
    completed: true to mark the checkbox done and stamp ✅ YYYY-MM-DD
    """
    if not any([task, feeds, why, time_estimate, time_block, completed]):
        return "❌ Provide at least one field to update."

    target = date or notes.today()

    err = validate_priority(slot)
    if err:
        return f"❌ {err}"

    try:
        notes.patch_priority(target, slot, task, feeds, why, time_estimate, time_block, completed)
    except ValueError as exc:
        return f"❌ {exc}"

    updated = [f for f, v in [("task", task), ("feeds", feeds), ("why", why), ("time_estimate", time_estimate), ("time_block", time_block)] if v]
    if completed:
        updated.append("completed")
    return f"✅ Priority {slot} updated: {', '.join(updated)}"


@mcp.tool()
def clear_priority(slot: int, date: str = "") -> str:
    """Clear priority slot (1–3). date: YYYY-MM-DD, empty=today."""
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
def get_priorities(date: str = "") -> str:
    """Return all three priority slots for a day. date: YYYY-MM-DD, empty=today."""
    target = date or notes.today()
    slots = notes.get_priorities(target)

    lines = [f"Priorities for {target}:"]
    for n in (1, 2, 3):
        s = slots[n]
        if s is None:
            lines.append(f"  [{n}] {PRIORITY_EMOJI[n]} empty")
        else:
            done = "✅" if s["done"] else "⬜"
            lines.append(f"  [{n}] {PRIORITY_EMOJI[n]} {done} {s['task']} #{s['tag']}")
            if s["feeds"]:
                lines.append(f"       Feeds: {s['feeds']}")
            if s["why"]:
                lines.append(f"       Why: {s['why']}")
            if s["time_estimate"]:
                lines.append(f"       Est: {s['time_estimate']}")
            if s["time_block"]:
                lines.append(f"       Block: {s['time_block']}")
    return "\n".join(lines)


@mcp.tool()
def add_note(
    type: str,
    content: str,
    date: str = "",
) -> str:
    """Append to Ideas or Links section. type: "idea"|"link". date: YYYY-MM-DD, empty=today."""
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
    slot: int = 0,
    task: str = "",
    tag: str = "",
    date: str = "",
    carry_over: bool = False,
) -> str:
    """
    Set tomorrow priority slot in today's Tomorrow Prep section, or carry over incomplete priorities.

    slot: 1–3 (required when carry_over=False) | tag: datascience/guitar/habits/health/investing/learning/personal/prep
    carry_over: when True, reads today's incomplete priorities and pre-fills them into tomorrow slots (slot/task ignored)
    date: YYYY-MM-DD, empty=today
    """
    target = date or notes.today()

    if carry_over:
        slots = notes.get_priorities(target)
        carried = []
        for n in (1, 2, 3):
            s = slots[n]
            if s and not s["done"]:
                try:
                    notes.fill_tomorrow_priority(target, n, s["task"], s["tag"])
                    carried.append(f"slot {n}: {s['task']}")
                except ValueError:
                    pass  # slot already filled in tomorrow prep — skip silently
        if not carried:
            return "✅ No incomplete priorities to carry over."
        return "✅ Carried over:\n" + "\n".join(f"  {c}" for c in carried)

    if not slot or not task:
        return "❌ Provide slot + task, or set carry_over=True."

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
    """Read goals. level: "longterm"|"monthly"|"weekly"|"all" (default)."""
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
    Add a goal. level: "longterm"|"monthly"|"weekly".
    code: "DS" (longterm), "DS-M1" (monthly), "DS-W1" (weekly).
    feeds: parent code (empty for longterm). Auto-creates file if needed.
    """
    return goals_mgr.add_goal(level, code, goal, feeds, description)


@mcp.tool()
def update_goal_status(
    code: str,
    level: str,
    status: str,
    progress_note: str = "",
) -> str:
    """Update goal status. level: "monthly"|"weekly". status: "not_started"|"in_progress"|"done"."""
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
    Create a calendar event. category: TimeBlocks/DataScience/Investing/Guitar/Habits/Work.
    priority 1–3: also links event to that daily-note slot. date: YYYY-MM-DD, empty=today.
    """
    target = date or notes.today()
    return cal.create_event(title, start_time, end_time, category, target, priority)


@mcp.tool()
def list_events(category: str, date: str = "", end_date: str = "") -> str:
    """
    List events by category. category: TimeBlocks/DataScience/Investing/Guitar/Habits/Work.
    date: YYYY-MM-DD start filter, empty=all. end_date: YYYY-MM-DD for range view (requires date).
    """
    return cal.list_events(category, date, end_date)


@mcp.tool()
def delete_event(title: str, category: str, date: str = "") -> str:
    """Delete a calendar event. Use list_events first to confirm exact title. date: YYYY-MM-DD, empty=today."""
    target = date or notes.today()
    return cal.delete_event(title, category, target)


# ── Queue Tools ───────────────────────────────────────────────────────────────

QUEUE_PATH = "08-Queue/Priority-Queue.md"
_STATUS_MARKER = {"promoted": "[>]", "done": "[x]", "cancelled": "[-]"}
_QUEUE_SECTIONS = {
    "p1": "## 🔺 P1 — Do Soon",
    "p2": "## ⏫ P2 — Do This Week/Next",
    "p3": "## 🔼 P3 — Someday",
}


@mcp.tool()
def queue_list() -> str:
    """List all pending tasks in the priority queue. Returns numbered list (IDs for queue_update)."""
    content = vault.get_file(QUEUE_PATH)
    if not content:
        return "✅ Queue is empty or file not found."

    pending = [(i, line) for i, line in enumerate(content.split("\n")) if line.startswith("- [ ]")]
    if not pending:
        return "✅ No pending tasks in queue."

    lines = [f"{n + 1}. {line[6:].strip()}" for n, (_, line) in enumerate(pending)]
    return f"{len(lines)} pending task(s):\n" + "\n".join(lines)


@mcp.tool()
def queue_add(task: str, priority: str, tag: str = "") -> str:
    """
    Add a task to the priority queue under the correct section.

    priority: p1 (Do Soon) | p2 (Do This Week/Next) | p3 (Someday)
    tag: optional tag appended to the task, e.g. 'work' → #work
    """
    priority = priority.lower().strip()
    if priority not in _QUEUE_SECTIONS:
        return f"❌ priority must be one of: {', '.join(_QUEUE_SECTIONS)}"

    content = vault.get_file(QUEUE_PATH)
    if not content:
        return f"❌ Queue file not found: {QUEUE_PATH}"

    heading = _QUEUE_SECTIONS[priority]
    if heading not in content:
        return f"❌ Section '{heading}' not found in queue file."

    item = f"- [ ] {task}"
    if tag:
        item += f" #{tag.lstrip('#')}"

    # Insert the new item right after the section heading (and any blank line)
    lines = content.split("\n")
    insert_at = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            insert_at = i + 1
            # Skip a single blank line after the heading if present
            if insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            break

    if insert_at is None:
        return f"❌ Could not locate section '{heading}'."

    lines.insert(insert_at, item)
    try:
        vault.save_file(QUEUE_PATH, "\n".join(lines))
    except Exception as exc:
        return f"❌ {exc}"

    return f"✅ Added to {heading}: {item}"


@mcp.tool()
def queue_update(task_id: int, status: str) -> str:
    """
    Update a queue task status by its ID from queue_list.

    task_id: 1-indexed position from queue_list
    status: promoted | done | cancelled
    """
    if status not in _STATUS_MARKER:
        return f"❌ status must be one of: {', '.join(_STATUS_MARKER)}"

    content = vault.get_file(QUEUE_PATH)
    if not content:
        return f"❌ Queue file not found: {QUEUE_PATH}"

    all_lines = content.split("\n")
    pending_indices = [i for i, line in enumerate(all_lines) if line.startswith("- [ ]")]

    if task_id < 1 or task_id > len(pending_indices):
        return f"❌ task_id {task_id} out of range (queue has {len(pending_indices)} pending tasks)."

    target_line_idx = pending_indices[task_id - 1]
    all_lines[target_line_idx] = all_lines[target_line_idx].replace("- [ ]", f"- {_STATUS_MARKER[status]}", 1)

    try:
        vault.save_file(QUEUE_PATH, "\n".join(all_lines))
    except Exception as exc:
        return f"❌ {exc}"

    task_text = all_lines[target_line_idx][6:].strip()
    return f"✅ Task {task_id} marked {status}: {task_text}"


# ── Vault Primitive Tools ─────────────────────────────────────────────────────


@mcp.tool()
def vault_read(path: str) -> str:
    """Read any file in the vault by relative path. E.g. '08-Queue/Priority-Queue.md'"""
    content = vault.get_file(path)
    return content if content else f"❌ File not found: {path}"


@mcp.tool()
def vault_write(path: str, content: str) -> str:
    """Create or overwrite a file in the vault. Path is relative to vault root."""
    try:
        vault.save_file(path, content)
        return f"✅ Written: {path}"
    except Exception as e:
        return f"❌ {e}"


@mcp.tool()
def vault_append(path: str, content: str) -> str:
    """Append content to a vault file. Creates the file if it doesn't exist."""
    try:
        existing = vault.get_file(path) or ""
        vault.save_file(path, existing + "\n" + content)
        return f"✅ Appended to: {path}"
    except Exception as e:
        return f"❌ {e}"


@mcp.tool()
def vault_list(folder: str = "", recursive: bool = False) -> str:
    """List files in a vault folder. folder: relative path, empty=root. recursive: true to include all subfolders."""
    try:
        files = vault.list_folder_recursive(folder) if recursive else vault.list_folder(folder)
        if not files:
            return f"No files found in '{folder}'"
        return "\n".join(files)
    except Exception as e:
        return f"❌ {e}"


# ── Inbox Tools ───────────────────────────────────────────────────────────────


@mcp.tool()
def inbox_capture(
    content: str,
    source_type: str = "dump",
    title: str = "",
) -> str:
    """
    Save a raw dump to 09-Inbox/ for later processing.

    source_type: dump|meeting|idea|link|learning|reference
    title: optional short title; auto-generated from timestamp if empty.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H%M")
    note_title = title or f"{timestamp} {source_type}"
    path = f"09-Inbox/{note_title}.md"

    frontmatter = f"""---
date: {datetime.now().strftime("%Y-%m-%d")}
type: {source_type}
status: unprocessed
---

"""
    vault.save_file(path, frontmatter + content)
    return f"✅ Captured to inbox: {path}"


@mcp.tool()
def inbox_list() -> str:
    """List all unprocessed items in 09-Inbox/."""
    try:
        files = vault.list_folder("09-Inbox")
        unprocessed = [f for f in files if f.endswith(".md")]
        if not unprocessed:
            return "✅ Inbox is empty."
        return f"{len(unprocessed)} item(s) in inbox:\n" + "\n".join(unprocessed)
    except Exception as e:
        return f"❌ {e}"


# ── Knowledge Base Tools ──────────────────────────────────────────────────────


@mcp.tool()
def knowledge_create(
    title: str,
    content: str,
    tags: str = "",
    moc: str = "",
    subfolder: str = "",
) -> str:
    """
    Create an atomic knowledge note in 10-Knowledge/.

    tags: comma-separated. E.g. "datascience,ml,python"
    moc: MOC(s) this note belongs to — auto-adds backlink. Comma-separated for multiple.
      E.g. "DataScience" or "Projects, AI Engineering"
    subfolder: domain folder under 10-Knowledge/ — auto-created on first write.
      Canonical: AI-Engineering | Data-Science | Guitar | Health | Investing | MOCs | Personal | References
      Empty = root of 10-Knowledge/.
    """
    folder = f"{KNOWLEDGE_FOLDER}/{subfolder}" if subfolder else KNOWLEDGE_FOLDER
    path = f"{folder}/{title}.md"

    tag_list = "\n".join([f"  - {t.strip()}" for t in tags.split(",")]) if tags else ""

    # Parse moc: comma-separated string → deduplicated list
    moc_list = [m.strip() for m in moc.split(",") if m.strip()] if moc else []
    seen: set = set()
    moc_list = [m for m in moc_list if not (m in seen or seen.add(m))]

    if moc_list:
        moc_links = " | ".join([f"[[{m}]]" for m in moc_list])
        moc_link = f"\n\n---\n🗺️ MOC: {moc_links}"
    else:
        moc_link = ""

    frontmatter = f"""---
date: {datetime.now().strftime("%Y-%m-%d")}
tags:
{tag_list}
---

"""
    vault.save_file(path, frontmatter + content + moc_link)

    for m in moc_list:
        moc_path = f"{KNOWLEDGE_FOLDER}/MOCs/{m}.md"
        vault_append(moc_path, f"\n- [[{title}]]")

    return f"✅ Knowledge note created: {path}"


@mcp.tool()
def moc_create(title: str, description: str = "", tags: str = "") -> str:
    """
    Create a Map of Content (theme hub) in 10-Knowledge/MOCs/.

    title: E.g. "DataScience", "Guitar", "Investing"
    tags: comma-separated.
    """
    path = f"{KNOWLEDGE_FOLDER}/MOCs/{title}.md"
    tag_list = "\n".join([f"  - {t.strip()}" for t in tags.split(",")]) if tags else ""

    content = f"""---
date: {datetime.now().strftime("%Y-%m-%d")}
type: moc
tags:
{tag_list}
---

# {title}

{description}

## Notes

"""
    vault.save_file(path, content)
    return f"✅ MOC created: {path}"


# ── Inbox Processor ───────────────────────────────────────────────────────────


@mcp.tool()
def inbox_process(
    inbox_filename: str,
    destination: str,
    title: str = "",
    tags: str = "",
    project: str = "",
    moc: str = "",
    subfolder: str = "",
) -> str:
    """
    Process an inbox item — route it to its permanent home and mark as processed.

    inbox_filename: from inbox_list(). E.g. "2026-02-20 1430 meeting.md"
    destination: knowledge|project|queue|daily|weekly|reference|moc|delete
    title: title for the new permanent note.
    tags: comma-separated. E.g. "datascience,ml"
    project: required when destination=project. E.g. "Intelligent Payroll"
    moc: MOC name(s) to link when destination=knowledge. Comma-separated for multiple.
      E.g. "DataScience" or "Projects, AI Engineering"
    subfolder: domain folder under 10-Knowledge/ when destination=knowledge — auto-created on first write.
      Canonical: AI-Engineering | Data-Science | Guitar | Health | Investing | MOCs | Personal | References
    """
    inbox_path = f"09-Inbox/{inbox_filename}"
    raw_content = vault.get_file(inbox_path)
    if not raw_content:
        return f"❌ Inbox item not found: {inbox_path}"

    # Strip frontmatter to get body
    lines = raw_content.split("\n")
    body_start = 0
    if lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                body_start = i + 1
                break
    body = "\n".join(lines[body_start:]).strip()

    final_path = ""

    if destination in ("knowledge", "reference"):
        resolved_subfolder = "References" if destination == "reference" else subfolder
        note_title = title or inbox_filename.replace(".md", "")
        final_path = f"{KNOWLEDGE_FOLDER}/{resolved_subfolder}/{note_title}.md" if resolved_subfolder else f"{KNOWLEDGE_FOLDER}/{note_title}.md"
        if vault.get_file(final_path):
            return f"❌ Duplicate: {final_path} already exists. Rename with title= or delete the existing note first."
        knowledge_create(note_title, body, tags, moc, resolved_subfolder)

    elif destination == "moc":
        note_title = title or inbox_filename.replace(".md", "")
        final_path = f"{KNOWLEDGE_FOLDER}/MOCs/{note_title}.md"
        if vault.get_file(final_path):
            return f"❌ Duplicate: {final_path} already exists. Rename with title= or delete the existing note first."
        moc_create(note_title, body, tags)

    elif destination == "project":
        if not project:
            return "❌ 'project' parameter required when destination=project"
        note_title = title or inbox_filename.replace(".md", "")
        final_path = f"Projects Information/{project}/{note_title}.md"
        if vault.get_file(final_path):
            return f"❌ Duplicate: {final_path} already exists. Rename with title= or delete the existing note first."
        vault.save_file(final_path, f"# {note_title}\n\n{body}")

    elif destination == "queue":
        final_path = "08-Queue/Priority-Queue.md"
        vault_append(final_path, f"\n- [ ] {title or body[:80]}")

    elif destination == "daily":
        today = notes.today()
        final_path = f"{DAILY_NOTES_FOLDER}/{today[:4]}/{today[5:7]}/{today}.md"
        vault_append(final_path, f"\n\n---\n{body}")

    elif destination == "weekly":
        iso = date.today().isocalendar()
        weekly_path = f"04-Weekly/{iso[0]}-W{iso[1]:02d}.md"
        final_path = weekly_path
        vault_append(weekly_path, f"\n\n---\n{body}")

    elif destination == "delete":
        vault.delete_inbox_item(inbox_filename)
        return f"✅ Deleted from inbox: {inbox_filename}"

    else:
        return f"❌ Unknown destination: {destination}"

    vault.delete_inbox_item(inbox_filename)
    return f"✅ Routed to {final_path} — inbox item deleted."


# ── Weekly Review Tool ────────────────────────────────────────────────────────


@mcp.tool()
def weekly_review_read(week: str = "") -> str:
    """
    Read all daily notes for the current (or given) week for review/synthesis.

    week: ISO week as YYYY-WNN. E.g. "2026-W08". Leave empty for current week.
    """
    if week:
        match = re.match(r"(\d{4})-W(\d{2})", week)
        if not match:
            return "❌ Format must be YYYY-WNN. E.g. 2026-W08"
        year, week_num = int(match.group(1)), int(match.group(2))
        jan4 = date(year, 1, 4)
        monday = jan4 + timedelta(weeks=week_num - 1, days=-jan4.weekday())
    else:
        today = date.today()
        monday = today - timedelta(days=today.weekday())

    combined = []
    for i in range(7):
        d = monday + timedelta(days=i)
        path = f"{DAILY_NOTES_FOLDER}/{d.year}/{d.month:02d}/{d}.md"
        content = vault.get_file(path)
        if content:
            combined.append(f"## {d.strftime('%A %Y-%m-%d')}\n\n{content}")

    if not combined:
        return "No daily notes found for this week."

    return "\n\n---\n\n".join(combined)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
