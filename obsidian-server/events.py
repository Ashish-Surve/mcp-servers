"""
events.py — Full Calendar event CRUD and priority linking.

Manages calendar event notes in the Obsidian vault's calendar folder.
Owns the YAML frontmatter format and the naming convention for event files.
"""

from config import validate_category, log
from vault import VaultClient
from notes import DailyNote


class CalendarManager:
    """Create, list, and delete Full Calendar event notes."""

    def __init__(self, vault: VaultClient, daily_note: DailyNote) -> None:
        self._vault = vault
        self._daily = daily_note

    # ── Naming conventions ───────────────────────────────────────────────

    @staticmethod
    def event_note_name(event_date: str, title: str) -> str:
        """Canonical note name: 'YYYY-MM-DD Title'."""
        return f"{event_date} {title}"

    @staticmethod
    def event_filename(event_date: str, title: str) -> str:
        """Canonical filename: 'YYYY-MM-DD Title.md'."""
        return f"{event_date} {title}.md"

    @staticmethod
    def build_frontmatter(title: str, event_date: str, start: str, end: str) -> str:
        """Build YAML frontmatter for a calendar event note."""
        return (
            f"---\n"
            f"title: {title}\n"
            f"date: {event_date}\n"
            f'startTime: "{start}"\n'
            f'endTime: "{end}"\n'
            f"allDay: false\n"
            f"completed:\n"
            f"---\n"
        )

    # ── CRUD ─────────────────────────────────────────────────────────────

    def create_event(
        self,
        title: str,
        start: str,
        end: str,
        category: str,
        event_date: str,
        priority: int = 0,
    ) -> str:
        """Create a calendar event and optionally link it to a priority.

        Returns a status message string.
        """
        err = validate_category(category)
        if err:
            return f"❌ {err}"

        filename = self.event_filename(event_date, title)
        content = self.build_frontmatter(title, event_date, start, end)
        self._vault.save_event(category, filename, content)

        result = f"Calendar event created: {title} ({start}–{end}) in {category}"

        if priority in (1, 2, 3):
            note_name = self.event_note_name(event_date, title)
            linked = self._daily.link_event_to_priority(event_date, priority, note_name)
            if linked:
                result += f" | Linked in Priority {priority} time block"
            else:
                result += (
                    f" | ⚠️ Could not link to Priority {priority}"
                    " (daily note or section not found)"
                )

        return result

    def list_events(self, category: str, event_date: str = "") -> str:
        """List events in a category, optionally filtered by date."""
        err = validate_category(category)
        if err:
            return f"❌ {err}"

        files = self._vault.list_event_files(category)
        if event_date:
            files = [f for f in files if f.startswith(event_date)]

        if not files:
            suffix = f" for {event_date}" if event_date else ""
            return f"No events found in {category}{suffix}."

        return "\n".join(files)

    def delete_event(self, title: str, category: str, event_date: str) -> str:
        """Delete a calendar event note."""
        err = validate_category(category)
        if err:
            return f"❌ {err}"

        filename = self.event_filename(event_date, title)
        if self._vault.delete_event(category, filename):
            return f"✅ Deleted: {filename}"
        return f"❌ Event not found: {filename}. Use list_calendar_events to see available events."
