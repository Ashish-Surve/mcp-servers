"""
notes.py — Daily note structure, template building, and section editing.

All knowledge about the daily note markdown format lives here:
template placeholders, priority sections, quick-note sections, etc.
"""

import re
from datetime import date, timedelta

from config import (
    PRIORITY_EMOJI,
    VALID_SECTIONS,
    PRIORITY_HEADING_FMT,
    FIELD_TASK,
    FIELD_FEEDS,
    FIELD_WHY_IT_MATTERS,
    FIELD_TIME_ESTIMATE,
    FIELD_TIME_BLOCK,
    DATE_MARKER,
    TAG_PLACEHOLDER,
    TAG_PLACEHOLDER_RENDERED,
    TASKS_PLUGIN_METADATA_PATTERN,
    log,
)
from vault import VaultClient

TEMPLATE_PATH = "01-Templates/Enhanced Daily Template.md"


class DailyNote:
    """Read, create, and modify Obsidian daily notes."""

    def __init__(self, vault: VaultClient) -> None:
        self._vault = vault

    # ── Date helpers ─────────────────────────────────────────────────────

    @staticmethod
    def today() -> str:
        """Today as YYYY-MM-DD."""
        return date.today().isoformat()

    @staticmethod
    def tomorrow_from(base_date: str) -> str:
        """Next day from a YYYY-MM-DD string."""
        return (date.fromisoformat(base_date) + timedelta(days=1)).isoformat()

    @staticmethod
    def ordinal_suffix(n: int) -> str:
        """Return n with ordinal suffix: 1st, 2nd, 3rd, 4th, …, 20th, 21st."""
        if 11 <= (n % 100) <= 13:
            return f"{n}th"
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    @staticmethod
    def get_week_id(dt: date) -> str:
        """Return ISO week ID, e.g. '2026-W08'."""
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"

    @staticmethod
    def get_month_id(dt: date) -> str:
        """Return month ID, e.g. '2026-02'."""
        return dt.strftime("%Y-%m")

    # ── Read / create ────────────────────────────────────────────────────

    def read(self, note_date: str) -> str:
        """Return note content, or empty string if it doesn't exist."""
        return self._vault.get_note(note_date)

    def exists(self, note_date: str) -> bool:
        return bool(self._vault.get_note(note_date))

    def create(self, note_date: str) -> str:
        """Create a daily note from template. Returns a status message."""
        if self.exists(note_date):
            return f"Daily note for {note_date} already exists. Use read_daily_note to view it."
        content = self._build_template(note_date)
        self._vault.save_note(note_date, content)
        return f"Created daily note for {note_date}"

    # ── Priority manipulation ────────────────────────────────────────────

    def fill_priority(
        self,
        note_date: str,
        priority: int,
        task_name: str,
        tag: str,
        time_estimate: str,
        why_it_matters: str = "",
        time_block: str = "",
        feeds: str = "",
    ) -> None:
        """Replace a priority placeholder with filled values.

        feeds: raw Obsidian link chain string. If empty, left blank.

        Raises ValueError if the note is missing or the slot is already filled.
        """
        emoji = PRIORITY_EMOJI[priority]

        placeholder = (
            f"- [ ] #todo {FIELD_TASK} {DATE_MARKER} {note_date} {emoji} #{TAG_PLACEHOLDER}\n"
            f"- {FIELD_FEEDS}\n"
            f"- {FIELD_WHY_IT_MATTERS}\n"
            f"- {FIELD_TIME_ESTIMATE}\n"
            f"- {FIELD_TIME_BLOCK}"
        )

        filled = (
            f"- [ ] #todo {FIELD_TASK} {task_name} {DATE_MARKER} {note_date} {emoji} #{tag}\n"
            f"- {FIELD_FEEDS} {feeds}\n"
            f"- {FIELD_WHY_IT_MATTERS} {why_it_matters}\n"
            f"- {FIELD_TIME_ESTIMATE} {time_estimate}\n"
            f"- {FIELD_TIME_BLOCK} {time_block}"
        )

        content = self._vault.get_note(note_date)
        if not content:
            raise ValueError(f"No daily note for {note_date}. Run create_daily_note first.")

        if placeholder not in content:
            raise ValueError(
                f"Priority {priority} placeholder not found — slot may already be filled."
            )

        updated = content.replace(placeholder, filled, 1)
        self._vault.save_note(note_date, updated)
        log.info("Filled priority %d: %s", priority, task_name)

    # ── Anchored block/line lookup ───────────────────────────────────────
    #
    # The functions below locate fields by searching for their label within
    # the priority's section (bounded by the next heading or end of file)
    # instead of assuming a fixed line offset from the header. This makes
    # them tolerant of blank-line changes, reordered fields, or extra lines
    # a user/plugin (e.g. the Tasks community plugin) may have inserted —
    # the same anchoring style clear_priority/set_time_block already use.

    @staticmethod
    def _section_bounds(lines: list[str], start_idx: int) -> int:
        """Return the line index where the section starting at start_idx ends
        (the next '#'-heading line, or len(lines) if none)."""
        for i in range(start_idx + 1, len(lines)):
            if lines[i].startswith("#"):
                return i
        return len(lines)

    def _find_priority_section(self, lines: list[str], priority: int) -> tuple[int, int]:
        """Return (start_idx, end_idx) of the priority section's line range.

        start_idx is the header line itself; end_idx is exclusive.
        Raises ValueError if the header is not found.
        """
        header = PRIORITY_HEADING_FMT.format(n=priority)
        try:
            idx = lines.index(header)
        except ValueError:
            raise ValueError(f"Priority {priority} section not found in the note.")
        return idx, self._section_bounds(lines, idx)

    @staticmethod
    def _find_field_line(lines: list[str], start: int, end: int, label: str) -> int:
        """Return the index of the first line in [start, end) containing label.

        Raises ValueError with a scoped message if not found.
        """
        for i in range(start, end):
            if label in lines[i]:
                return i
        raise ValueError(
            f"'{label}' line not found in this priority section — "
            "it may have been removed or reworded."
        )

    @staticmethod
    def _find_task_line(lines: list[str], start: int, end: int) -> int:
        """Return the index of the task checkbox line in [start, end).

        Matches any markdown checkbox ("- [ ]", "- [x]", "- [X]", etc.)
        rather than assuming a fixed offset, so reordered/edited sections
        are still found.
        """
        for i in range(start, end):
            if re.match(r"^\s*- \[.\]", lines[i]):
                return i
        raise ValueError(
            "Task checkbox line not found in this priority section — "
            "it may have been deleted or its checkbox syntax altered."
        )

    @staticmethod
    def _split_task_line(line: str) -> dict:
        """Parse a task checkbox line into its structural parts.

        Tolerant of metadata the Tasks community plugin inserts (its own
        priority emoji, recurrence, scheduled/start/due dates, done-date),
        which may appear interleaved with this app's own **Task:**/📅/#tag
        fields. Anything recognized as Tasks-plugin metadata is treated as
        an opaque suffix to preserve, never as part of the task description.

        Returns {"done": bool, "prefix": str, "task_text": str, "tag": str,
        "metadata_suffix": str} — prefix is the literal "- [ ] #todo " (or
        whatever checkbox/marker text precedes **Task:**).

        Raises ValueError if the line doesn't contain the **Task:** marker.
        """
        checkbox_match = re.match(r"^(\s*- \[(.)\]\s*)", line)
        done = bool(checkbox_match) and checkbox_match.group(2).lower() == "x"

        task_marker = f"{FIELD_TASK} "
        if task_marker not in line:
            raise ValueError(
                f"'{FIELD_TASK}' marker not found in task line — "
                "the line may have been edited in a way that's no longer recognized."
            )
        marker_end = line.index(task_marker) + len(task_marker)
        prefix = line[:marker_end]
        rest = line[marker_end:]

        # Find where the task description ends: the first Tasks-plugin
        # metadata emoji (our own 📅 date marker is one of them) marks the
        # start of the metadata tail. Everything before it is description
        # text (the #tag, if present right before the date, is pulled out
        # separately below).
        meta_match = re.search(TASKS_PLUGIN_METADATA_PATTERN, rest)
        if meta_match:
            task_text = rest[: meta_match.start()].rstrip()
            metadata_suffix = rest[meta_match.start():]
        else:
            # No recognized metadata at all — whole remainder is task text.
            task_text = rest.rstrip()
            metadata_suffix = ""

        # Extract our #tag: last "#word" token in the metadata suffix that
        # isn't part of a recurrence phrase, scanned from the end so any
        # Tasks-plugin tags elsewhere on the line don't get picked instead.
        tag = ""
        for token in reversed(metadata_suffix.split()):
            if token.startswith("#") and not token.startswith("#todo"):
                tag = token[1:]
                break

        return {
            "done": done,
            "prefix": prefix,
            "task_text": task_text,
            "tag": tag,
            "metadata_suffix": metadata_suffix,
        }

    def clear_priority(self, note_date: str, priority: int) -> None:
        """Reset a priority slot back to its empty template placeholder.

        Locates the task/feeds/why/estimate/time-block lines by anchored
        label search within this priority's section (tolerant of Tasks
        community plugin metadata on the task line) and rewrites each of
        them to its unfilled form, rather than matching one fragile 5-line
        regex that breaks if any extra metadata is present.

        Raises ValueError if the note, section, or task line is not found,
        or if the slot is already empty (still shows the tag placeholder).
        """
        emoji = PRIORITY_EMOJI[priority]

        content = self._vault.get_note(note_date)
        if not content:
            raise ValueError(f"No daily note for {note_date}.")

        lines = content.split("\n")
        start, end = self._find_priority_section(lines, priority)
        task_idx = self._find_task_line(lines, start, end)
        task_line = lines[task_idx]

        if f"#{TAG_PLACEHOLDER_RENDERED}" in task_line or f"#{TAG_PLACEHOLDER}" in task_line:
            raise ValueError(
                f"Priority {priority} slot appears to be empty already "
                "or has an unexpected format."
            )

        lines[task_idx] = f"- [ ] #todo {FIELD_TASK} {DATE_MARKER} {note_date} {emoji} #{TAG_PLACEHOLDER}"

        for label in (FIELD_FEEDS, FIELD_WHY_IT_MATTERS, FIELD_TIME_ESTIMATE, FIELD_TIME_BLOCK):
            try:
                idx = self._find_field_line(lines, start, end, label)
            except ValueError:
                continue  # field line missing — nothing to clear, leave section as-is
            lines[idx] = f"- {label}"

        self._vault.save_note(note_date, "\n".join(lines))
        log.info("Cleared priority %d for %s", priority, note_date)

    def patch_priority(
        self,
        note_date: str,
        priority: int,
        task: str = "",
        feeds: str = "",
        why: str = "",
        time_estimate: str = "",
        time_block: str = "",
        completed: bool = False,
    ) -> None:
        """Patch individual fields in an already-filled priority slot.

        Only fields passed as non-empty strings are updated; others are left untouched.
        Pass completed=True to mark the checkbox done and stamp ✅ YYYY-MM-DD.

        Fields are located by searching for their label within the priority's
        section (bounded by the next heading) rather than assuming a fixed
        line offset, so the section tolerates blank-line changes, reordering,
        or extra lines a user/Tasks-plugin may have inserted.

        Raises ValueError if the note, the priority section, the task line,
        or a requested field's line cannot be found.
        """
        content = self._vault.get_note(note_date)
        if not content:
            raise ValueError(f"No daily note for {note_date}.")

        lines = content.split("\n")
        start, end = self._find_priority_section(lines, priority)

        if task:
            task_idx = self._find_task_line(lines, start, end)
            parts = self._split_task_line(lines[task_idx])

            # If the new task text ends with an embedded #tag, swap it into
            # the metadata suffix so the old tag isn't kept; otherwise the
            # existing tag (and all other Tasks-plugin metadata) is preserved
            # untouched.
            task_clean = task
            metadata_suffix = parts["metadata_suffix"]
            tag_match = re.search(r'\s(#\w+)$', task)
            if tag_match:
                task_clean = task[:tag_match.start()]
                new_tag = tag_match.group(1)
                if parts["tag"]:
                    metadata_suffix = re.sub(
                        r'#' + re.escape(parts["tag"]) + r'\b', new_tag, metadata_suffix, count=1
                    )
                else:
                    metadata_suffix = (metadata_suffix + f" {new_tag}").strip()

            separator = " " if metadata_suffix and not metadata_suffix.startswith(" ") else ""
            lines[task_idx] = parts["prefix"] + task_clean + separator + metadata_suffix

        if feeds is not None and feeds != "":
            idx = self._find_field_line(lines, start, end, FIELD_FEEDS)
            lines[idx] = f"- {FIELD_FEEDS} {feeds}"

        if why is not None and why != "":
            idx = self._find_field_line(lines, start, end, FIELD_WHY_IT_MATTERS)
            lines[idx] = f"- {FIELD_WHY_IT_MATTERS} {why}"

        if time_estimate:
            idx = self._find_field_line(lines, start, end, FIELD_TIME_ESTIMATE)
            lines[idx] = f"- {FIELD_TIME_ESTIMATE} {time_estimate}"

        if time_block:
            idx = self._find_field_line(lines, start, end, FIELD_TIME_BLOCK)
            lines[idx] = f"- {FIELD_TIME_BLOCK} {time_block}"

        if completed:
            completed_idx = self._find_task_line(lines, start, end)
            task_line = lines[completed_idx]
            if re.match(r"^\s*- \[ \]", task_line):
                lines[completed_idx] = re.sub(r"- \[ \]", "- [x]", task_line, count=1) + f" ✅ {note_date}"

        self._vault.save_note(note_date, "\n".join(lines))
        log.info("Patched priority %d for %s", priority, note_date)

    def set_time_block(self, note_date: str, priority: int, time_block: str) -> None:
        """Update the Time block line for a given priority.

        The Time block line is located by label search bounded to this
        priority's own section, so a missing/malformed line raises rather
        than silently matching a Time block line in a different section.

        Raises ValueError if the note, the priority section, or the Time
        block line is missing.
        """
        content = self._vault.get_note(note_date)
        if not content:
            raise ValueError(f"No daily note for {note_date}.")

        lines = content.split("\n")
        start, end = self._find_priority_section(lines, priority)
        idx = self._find_field_line(lines, start, end, FIELD_TIME_BLOCK)
        lines[idx] = f"- {FIELD_TIME_BLOCK} {time_block}"

        self._vault.save_note(note_date, "\n".join(lines))
        log.info("Set time block for priority %d: %s", priority, time_block)

    def link_event_to_priority(
        self, note_date: str, priority: int, note_name: str
    ) -> bool:
        """Set a priority's time block to [[note_name]].

        Returns True if linked, False if the note or section wasn't found.
        """
        try:
            self.set_time_block(note_date, priority, f"[[{note_name}]]")
            return True
        except ValueError as exc:
            log.warning("Could not link event to priority %d: %s", priority, exc)
            return False

    @staticmethod
    def _val(line: str, label: str) -> str:
        """Extract the value following a field label, e.g. '- **Feeds:** x' -> 'x'."""
        pos = line.find(label)
        return line[pos + len(label):].strip() if pos != -1 else ""

    def get_priorities(self, note_date: str) -> dict:
        """Return all three priority slots as structured dicts.

        Fields are located by searching for their label within each
        priority's section (bounded by the next heading) rather than
        assuming a fixed line offset, so reordered fields, extra blank
        lines, or lines a user/Tasks-plugin inserted don't shift reads
        onto the wrong line.

        Returns {1: {...}, 2: {...}, 3: {...}} where empty/unfilled slots
        have value None. A section whose task line is missing/unparsable
        is also treated as unfilled (None) rather than raising, since this
        is a read-only listing call.
        """
        content = self._vault.get_note(note_date)
        if not content:
            return {1: None, 2: None, 3: None}

        lines = content.split("\n")
        result = {}

        for priority in (1, 2, 3):
            try:
                start, end = self._find_priority_section(lines, priority)
            except ValueError:
                result[priority] = None
                continue

            try:
                task_idx = self._find_task_line(lines, start, end)
            except ValueError:
                result[priority] = None
                continue

            task_line = lines[task_idx]

            # Unfilled placeholder contains literal "#{tag}" (double-braced in template → single brace in file)
            if f"#{TAG_PLACEHOLDER_RENDERED}" in task_line or f"#{TAG_PLACEHOLDER}" in task_line:
                result[priority] = None
                continue

            try:
                task_parts = self._split_task_line(task_line)
            except ValueError:
                result[priority] = None
                continue

            def _field(label: str) -> str:
                try:
                    idx = self._find_field_line(lines, start, end, label)
                except ValueError:
                    return ""
                return self._val(lines[idx], label)

            result[priority] = {
                "task": task_parts["task_text"],
                "tag": task_parts["tag"],
                "feeds": _field(FIELD_FEEDS),
                "why": _field(FIELD_WHY_IT_MATTERS),
                "time_estimate": _field(FIELD_TIME_ESTIMATE),
                "time_block": _field(FIELD_TIME_BLOCK),
                "done": task_parts["done"],
            }

        return result

    # ── Quick notes ──────────────────────────────────────────────────────

    def add_quick_note(self, note_date: str, section: str, text: str) -> None:
        """Append a line under the Ideas or Links heading.

        Raises ValueError if the section is unknown or the note is missing.
        """
        heading = VALID_SECTIONS.get(section)
        if not heading:
            raise ValueError(f"Section must be one of: {', '.join(VALID_SECTIONS)}")

        content = self._vault.get_note(note_date)
        if not content:
            raise ValueError(f"No daily note for {note_date}.")

        updated = content.replace(heading, f"{heading}\n- {text}", 1)
        self._vault.save_note(note_date, updated)

    # ── Tomorrow's prep ──────────────────────────────────────────────────

    def fill_tomorrow_priority(
        self, note_date: str, priority: int, task_name: str, tag: str
    ) -> None:
        """Fill a Tomorrow's Prep slot.

        Raises ValueError if the placeholder is missing.
        """
        next_date = self.tomorrow_from(note_date)
        emoji = PRIORITY_EMOJI[priority]

        placeholder = f"{priority}. [ ] #todo {DATE_MARKER} {next_date} {emoji} #{TAG_PLACEHOLDER}"
        filled = f"{priority}. [ ] #todo {task_name} {DATE_MARKER} {next_date} {emoji} #{tag}"

        content = self._vault.get_note(note_date)
        if not content:
            raise ValueError(f"No daily note for {note_date}.")

        if placeholder not in content:
            raise ValueError(f"Tomorrow priority {priority} placeholder not found.")

        updated = content.replace(placeholder, filled, 1)
        self._vault.save_note(note_date, updated)
        log.info("Filled tomorrow priority %d: %s", priority, task_name)

    # ── Template ─────────────────────────────────────────────────────────

    def _build_template(self, for_date: str) -> str:
        """Render the daily note for for_date.

        Reads 01-Templates/Enhanced Daily Template.md from the vault and
        resolves all tp.date.now() expressions. Falls back to the hardcoded
        template if the file is missing so the server stays functional.
        """
        raw = self._vault.get_file(TEMPLATE_PATH)
        if raw:
            return self._render_templater(raw, for_date)
        log.warning("Template file %s not found — using built-in fallback", TEMPLATE_PATH)
        return self._builtin_template(for_date)

    def _resolve_tp_date(self, fmt: str, offset: int, base: date) -> str:
        """Resolve a single tp.date.now(fmt, offset) call to a string."""
        dt = base + timedelta(days=offset)
        if fmt == "YYYY-MM-DD":
            return dt.isoformat()
        if fmt == "YYYY-MM":
            return dt.strftime("%Y-%m")
        if fmt == "GGGG-[W]WW":
            iso = dt.isocalendar()
            return f"{iso[0]}-W{iso[1]:02d}"
        if fmt == "dddd, MMMM Do, YYYY":
            return f"{dt.strftime('%A')}, {dt.strftime('%B')} {self.ordinal_suffix(dt.day)}, {dt.year}"
        # Unknown format — return the raw moment string so it's visible
        return f"<unsupported:{fmt}>"

    def _render_templater(self, template: str, for_date: str) -> str:
        """Replace all tp.date.now() expressions in template with real values."""
        base = date.fromisoformat(for_date)

        def replacer(m: re.Match) -> str:
            fmt = m.group(1)
            offset = int(m.group(2)) if m.group(2) else 0
            return self._resolve_tp_date(fmt, offset, base)

        # Matches: <% tp.date.now("FMT") %> and <% tp.date.now("FMT", N) %>
        pattern = r"<%[ \t]*tp\.date\.now\(\"([^\"]+)\"(?:,[ \t]*(-?\d+))?[ \t]*\)[ \t]*%>"
        return re.sub(pattern, replacer, template)

    def _builtin_template(self, for_date: str) -> str:
        """Hardcoded fallback template — used only when vault template is missing."""
        dt = date.fromisoformat(for_date)
        next_date = (dt + timedelta(days=1)).isoformat()
        prev_date = (dt - timedelta(days=1)).isoformat()
        day_name = dt.strftime("%A")
        month_name = dt.strftime("%B")
        day_ordinal = self.ordinal_suffix(dt.day)
        week_id = self.get_week_id(dt)
        month_id = self.get_month_id(dt)
        e1, e2, e3 = PRIORITY_EMOJI[1], PRIORITY_EMOJI[2], PRIORITY_EMOJI[3]

        def _priority_block(n: int, emoji: str, for_date: str) -> str:
            return (
                f"{PRIORITY_HEADING_FMT.format(n=n)}\n\n"
                f"- [ ] #todo {FIELD_TASK} {DATE_MARKER} {for_date} {emoji} #{TAG_PLACEHOLDER}\n"
                f"- {FIELD_FEEDS}\n"
                f"- {FIELD_WHY_IT_MATTERS}\n"
                f"- {FIELD_TIME_ESTIMATE}\n"
                f"- {FIELD_TIME_BLOCK}\n"
            )

        priority_blocks = "\n".join(_priority_block(n, e, for_date) for n, e in ((1, e1), (2, e2), (3, e3)))

        return f"""# 📝 {for_date}

_{day_name}, {month_name} {day_ordinal}, {dt.year}_

**This week:** [[{week_id}]] | **This month:** [[{month_id}]] | **Vision:** [[Long-Term-Goals]]

> *What are the 1-3 most important things I'm blessed to do today?*

---

## 🔥 Priorities

{priority_blocks}
---

## 🔄 Habits

- [ ] #todo Morning routine 📅 {for_date} 🔄 every day #habits
- [ ] #todo Proper nutrition & hydration 📅 {for_date} 🔄 every day #health
- [ ] #todo Evening reflection 📅 {for_date} 🔄 every day #habits

---

## 📝 Notes

### Ideas

### Links

---

## 🔄 Tomorrow's Prep

1. [ ] #todo {DATE_MARKER} {next_date} {e1} #{TAG_PLACEHOLDER}
2. [ ] #todo {DATE_MARKER} {next_date} {e2} #{TAG_PLACEHOLDER}
3. [ ] #todo {DATE_MARKER} {next_date} {e3} #{TAG_PLACEHOLDER}

---

> *These are things I WANT to do, not things I NEED to do. Everything here is chosen.*

Yesterday: [[{prev_date}]] | Tomorrow: [[{next_date}]]
"""
