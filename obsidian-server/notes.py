"""
notes.py — Daily note structure, template building, and section editing.

All knowledge about the daily note markdown format lives here:
template placeholders, priority sections, quick-note sections, etc.
"""

import re
from datetime import date, timedelta

from config import PRIORITY_EMOJI, VALID_SECTIONS, log
from vault import VaultClient


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
        goal_code: str = "",
    ) -> None:
        """Replace a priority placeholder with filled values.

        If goal_code is provided, the Feeds line is set to a wikilink:
        [[{week_id}#{goal_code}]]. Otherwise it remains empty.

        Raises ValueError if the note is missing or the slot is already filled.
        """
        emoji = PRIORITY_EMOJI[priority]
        dt = date.fromisoformat(note_date)
        week_id = self.get_week_id(dt)

        feeds = f"[[{week_id}#{goal_code}]]" if goal_code else ""

        placeholder = (
            f"- [ ] #todo **Task:** 📅 {note_date} {emoji} #{{{{tag}}}}\n"
            f"- **Feeds:**\n"
            f"- **Why it matters:**\n"
            f"- **Time estimate:**\n"
            f"- **Time block:**"
        )

        filled = (
            f"- [ ] #todo **Task:** {task_name} 📅 {note_date} {emoji} #{tag}\n"
            f"- **Feeds:** {feeds}\n"
            f"- **Why it matters:** {why_it_matters}\n"
            f"- **Time estimate:** {time_estimate}\n"
            f"- **Time block:** {time_block}"
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

    def clear_priority(self, note_date: str, priority: int) -> None:
        """Reset a priority slot back to its empty template placeholder.

        Matches the filled 5-line block (Task/Feeds/Why/Estimate/Block) and
        replaces it with the unfilled template version.

        Raises ValueError if the note, section, or filled task is not found.
        """
        emoji = PRIORITY_EMOJI[priority]

        content = self._vault.get_note(note_date)
        if not content:
            raise ValueError(f"No daily note for {note_date}.")

        label = f"### Priority {priority}"
        if label not in content:
            raise ValueError(f"Priority {priority} section not found in the note.")

        # Match the 5-line filled task block within this priority section
        filled_pattern = (
            r"- \[.\] #todo \*\*Task:\*\* .+ 📅 " + re.escape(note_date)
            + r" " + re.escape(emoji) + r" #\w+\n"
            r"- \*\*Feeds:\*\* .*\n"
            r"- \*\*Why it matters:\*\* .*\n"
            r"- \*\*Time estimate:\*\* .*\n"
            r"- \*\*Time block:\*\* .*"
        )

        placeholder = (
            f"- [ ] #todo **Task:** 📅 {note_date} {emoji} #{{{{tag}}}}\n"
            f"- **Feeds:**\n"
            f"- **Why it matters:**\n"
            f"- **Time estimate:**\n"
            f"- **Time block:**"
        )

        before, after = content.split(label, 1)
        updated_after, count = re.subn(filled_pattern, placeholder, after, count=1)

        if count == 0:
            raise ValueError(
                f"Priority {priority} slot appears to be empty already "
                "or has an unexpected format."
            )

        self._vault.save_note(note_date, before + label + updated_after)
        log.info("Cleared priority %d for %s", priority, note_date)

    def set_time_block(self, note_date: str, priority: int, time_block: str) -> None:
        """Update the Time block line for a given priority.

        Raises ValueError if the note or priority section is missing.
        """
        content = self._vault.get_note(note_date)
        if not content:
            raise ValueError(f"No daily note for {note_date}.")

        label = f"### Priority {priority}"
        if label not in content:
            raise ValueError(f"Priority {priority} section not found in the note.")

        before, after = content.split(label, 1)
        updated_after = re.sub(
            r"- \*\*Time block:\*\* .*",
            f"- **Time block:** {time_block}",
            after,
            count=1,
        )
        self._vault.save_note(note_date, before + label + updated_after)
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

        placeholder = f"{priority}. [ ] #todo 📅 {next_date} {emoji} #{{{{tag}}}}"
        filled = f"{priority}. [ ] #todo {task_name} 📅 {next_date} {emoji} #{tag}"

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
        """Build the full daily note markdown for a given date."""
        dt = date.fromisoformat(for_date)
        next_date = (dt + timedelta(days=1)).isoformat()
        prev_date = (dt - timedelta(days=1)).isoformat()

        day_name = dt.strftime("%A")
        month_name = dt.strftime("%B")
        day_ordinal = self.ordinal_suffix(dt.day)
        week_id = self.get_week_id(dt)
        month_id = self.get_month_id(dt)

        e1, e2, e3 = PRIORITY_EMOJI[1], PRIORITY_EMOJI[2], PRIORITY_EMOJI[3]

        return f"""# 📝 {for_date}

_{day_name}, {month_name} {day_ordinal}, {dt.year}_

**This week:** [[{week_id}]] | **This month:** [[{month_id}]] | **Vision:** [[Long-Term-Goals]]

> *What are the 1-3 most important things I'm blessed to do today?*

---

## 🔥 Priorities

### Priority 1

- [ ] #todo **Task:** 📅 {for_date} {e1} #{{{{tag}}}}
- **Feeds:**
- **Why it matters:**
- **Time estimate:**
- **Time block:**

### Priority 2

- [ ] #todo **Task:** 📅 {for_date} {e2} #{{{{tag}}}}
- **Feeds:**
- **Why it matters:**
- **Time estimate:**
- **Time block:**

### Priority 3

- [ ] #todo **Task:** 📅 {for_date} {e3} #{{{{tag}}}}
- **Feeds:**
- **Why it matters:**
- **Time estimate:**
- **Time block:**

---

## 🔄 Habits

- [ ] #todo Morning routine 📅 {for_date} 🔄 every day #habits
- [ ] #todo Exercise/movement (30+ min) 📅 {for_date} 🔄 every day #health
- [ ] #todo Proper nutrition & hydration 📅 {for_date} 🔄 every day #health
- [ ] #todo Data science learning (15+ min) 📅 {for_date} 🔄 every day #datascience
- [ ] #todo Guitar practice (15+ min) 📅 {for_date} 🔄 every day #guitar
- [ ] #todo Investment research review 📅 {for_date} 🔄 every day #investing
- [ ] #todo Evening reflection 📅 {for_date} 🔄 every day #habits

---

## 📝 Notes

### Ideas

### Links

---

## 🔄 Tomorrow's Prep

1. [ ] #todo 📅 {next_date} {e1} #{{{{tag}}}}
2. [ ] #todo 📅 {next_date} {e2} #{{{{tag}}}}
3. [ ] #todo 📅 {next_date} {e3} #{{{{tag}}}}

---

> *These are things I WANT to do, not things I NEED to do. Everything here is chosen.*

Yesterday: [[{prev_date}]] | Tomorrow: [[{next_date}]]
"""
