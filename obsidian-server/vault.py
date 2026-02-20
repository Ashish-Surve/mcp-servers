"""
vault.py — HTTP transport layer for the Obsidian Local REST API.

All httpx usage is encapsulated here. No other file should import httpx
or know about URLs, headers, or SSL configuration.
"""

import httpx
from datetime import date
from config import OBSIDIAN_URL, API_KEY, VAULT_FOLDER, CALENDAR_FOLDER, log


class VaultClient:
    """Thin wrapper around the Obsidian Local REST API."""

    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=OBSIDIAN_URL,
            headers={"Authorization": f"Bearer {API_KEY}"},
            verify=False,  # Obsidian local REST API uses a self-signed cert
            timeout=10,
        )

    # ── Generic file I/O ─────────────────────────────────────────────────

    def get_file(self, path: str) -> str:
        """Fetch any vault file by full relative path. Returns '' if not found."""
        resp = self._client.get(f"/vault/{path}")
        if resp.status_code == 404:
            return ""
        resp.raise_for_status()
        log.debug("Read file: %s (%d bytes)", path, len(resp.text))
        return resp.text

    def save_file(self, path: str, content: str) -> None:
        """Write any vault file by full relative path."""
        self._client.put(
            f"/vault/{path}",
            content=content.encode(),
            headers={"Content-Type": "text/markdown"},
        ).raise_for_status()
        log.info("Saved file: %s", path)

    # ── Daily note I/O ───────────────────────────────────────────────────

    def get_note(self, note_date: str) -> str:
        """Fetch raw markdown for a daily note. Returns '' if not found.

        Path: {VAULT_FOLDER}/{YYYY}/{MM}/{YYYY-MM-DD}.md
        VAULT_FOLDER points directly to the 05-Daily-Notes folder.
        """
        dt = date.fromisoformat(note_date)
        path = f"{VAULT_FOLDER}/{dt.year}/{dt.month:02d}/{note_date}.md"
        return self.get_file(path)

    def save_note(self, note_date: str, content: str) -> None:
        """Overwrite a daily note with new content.

        Path: {VAULT_FOLDER}/{YYYY}/{MM}/{YYYY-MM-DD}.md
        VAULT_FOLDER points directly to the 05-Daily-Notes folder.
        """
        dt = date.fromisoformat(note_date)
        path = f"{VAULT_FOLDER}/{dt.year}/{dt.month:02d}/{note_date}.md"
        self.save_file(path, content)

    # ── Calendar event I/O ───────────────────────────────────────────────

    def save_event(self, category: str, filename: str, content: str) -> None:
        """Write a calendar event note to the category folder."""
        path = f"{CALENDAR_FOLDER}/{category}/{filename}"
        self._client.put(
            f"/vault/{path}",
            content=content.encode(),
            headers={"Content-Type": "text/markdown"},
        ).raise_for_status()
        log.info("Saved event: %s", path)

    def delete_event(self, category: str, filename: str) -> bool:
        """Delete a calendar event. Returns False if not found."""
        path = f"{CALENDAR_FOLDER}/{category}/{filename}"
        resp = self._client.delete(f"/vault/{path}")
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        log.info("Deleted event: %s", path)
        return True

    def list_event_files(self, category: str) -> list[str]:
        """List .md filenames in a category folder. Returns [] if folder missing."""
        resp = self._client.get(f"/vault/{CALENDAR_FOLDER}/{category}/")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return [f for f in resp.json().get("files", []) if f.endswith(".md")]
