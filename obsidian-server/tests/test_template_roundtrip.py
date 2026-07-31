"""
Phase 3 — round-trip self-check (obsidian-server issue #13).

Two things this guards against, neither covered by test_notes.py alone:

1. Structure drift between the *real* vault template seed
   (setup.py: DAILY_TEMPLATE_CONTENT — what actually gets written to
   01-Templates/Enhanced Daily Template.md) and notes.py's parsing logic.
   test_notes.py only exercises notes.py's own hardcoded fallback
   template, which is maintained by the same hand that maintains the
   parser — it can't catch the two vault-facing copies (this seed content
   and the parser) drifting apart from each other.

2. A full fill -> read -> clear round trip ending back at the original
   unfilled state, not just fill -> read (which test_notes.py already
   covers in TestBuiltinTemplate.test_round_trips_through_fill_and_get).

Does not touch a real Obsidian instance — DAILY_TEMPLATE_CONTENT is the
literal seed string setup.py writes; VaultClient is a MagicMock standing
in for the file store.
"""

import importlib.util as _ilu
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Load setup.py the same way tests/test_setup.py does, to get the real
# DAILY_TEMPLATE_CONTENT seed string without re-typing it here (re-typing it
# would itself be a third copy to drift).
# ---------------------------------------------------------------------------

with patch("dotenv.load_dotenv"):
    _spec = _ilu.spec_from_file_location("setup", Path(__file__).parent.parent / "setup.py")
    setup = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(setup)


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    monkeypatch.setenv("OBSIDIAN_API_KEY", "test-key")
    monkeypatch.setenv("OBSIDIAN_URL", "https://127.0.0.1:27124/")
    monkeypatch.setenv("DAILY_NOTES_FOLDER", "05-Daily-Notes")
    monkeypatch.setenv("CALENDAR_FOLDER", "06-Calendar-Events")
    monkeypatch.setenv("PLANNING_ROOT", "")


@pytest.fixture()
def mock_vault():
    return MagicMock()


@pytest.fixture()
def daily_note(mock_vault):
    from notes import DailyNote
    return DailyNote(mock_vault)


@pytest.fixture()
def rendered_vault_template(daily_note):
    """The real vault template seed, with Templater expressions resolved —
    i.e. what a fresh daily note actually looks like in production."""
    return daily_note._render_templater(setup.DAILY_TEMPLATE_CONTENT, "2026-06-16")


# ---------------------------------------------------------------------------
# 1. Structural assumptions in notes.py / config.py must match the real
#    vault template seed, not just notes.py's own fallback copy.
# ---------------------------------------------------------------------------

class TestVaultTemplateStructuralAssumptions:
    def test_contains_three_priority_headings(self, rendered_vault_template):
        from config import PRIORITY_HEADING_FMT
        for n in (1, 2, 3):
            assert PRIORITY_HEADING_FMT.format(n=n) in rendered_vault_template

    def test_contains_expected_field_labels(self, rendered_vault_template):
        from config import (
            FIELD_TASK, FIELD_FEEDS, FIELD_WHY_IT_MATTERS,
            FIELD_TIME_ESTIMATE, FIELD_TIME_BLOCK,
        )
        for label in (FIELD_TASK, FIELD_FEEDS, FIELD_WHY_IT_MATTERS, FIELD_TIME_ESTIMATE, FIELD_TIME_BLOCK):
            assert rendered_vault_template.count(label) == 3, (
                f"Expected '{label}' once per priority (3 total) in the vault "
                "template seed — config.py and setup.py have drifted."
            )

    def test_unfilled_slots_use_tag_placeholder_constant(self, rendered_vault_template):
        from config import TAG_PLACEHOLDER
        assert rendered_vault_template.count(f"#{TAG_PLACEHOLDER}") == 6  # 3 priorities + 3 tomorrow prep

    def test_quick_note_sections_match_valid_sections_constant(self, rendered_vault_template):
        from config import VALID_SECTIONS
        for heading in VALID_SECTIONS.values():
            assert heading in rendered_vault_template

    def test_no_unresolved_templater_expressions_remain(self, rendered_vault_template):
        assert "<%" not in rendered_vault_template
        assert "%>" not in rendered_vault_template

    def test_get_priorities_recognizes_all_slots_as_unfilled(self, daily_note, mock_vault, rendered_vault_template):
        """The real vault template's unfilled slots must parse as empty —
        this is the core drift check: if setup.py's seed and notes.py's
        parser disagree on structure, this is where it would show up."""
        mock_vault.get_note.return_value = rendered_vault_template
        result = daily_note.get_priorities("2026-06-16")
        assert result == {1: None, 2: None, 3: None}


# ---------------------------------------------------------------------------
# 2. Full fill -> get -> clear round trip against the real vault template,
#    ending back at byte-identical original content.
# ---------------------------------------------------------------------------

class TestFullRoundTrip:
    def test_fill_then_clear_returns_to_original_content(self, daily_note, mock_vault, rendered_vault_template):
        mock_vault.get_note.return_value = rendered_vault_template

        daily_note.fill_priority(
            "2026-06-16", 1, "Write report", "work", "2h",
            why_it_matters="Deadline tomorrow", time_block="09:00-11:00", feeds="[[Project]]",
        )
        after_fill = mock_vault.save_note.call_args[0][1]
        assert after_fill != rendered_vault_template  # sanity: fill actually changed something

        mock_vault.get_note.return_value = after_fill
        daily_note.clear_priority("2026-06-16", 1)
        after_clear = mock_vault.save_note.call_args[0][1]

        assert after_clear == rendered_vault_template

    def test_fill_get_clear_round_trip_for_every_priority_slot(self, daily_note, mock_vault, rendered_vault_template):
        """Same round trip, run independently for each of the 3 slots,
        to catch a bug that only affects e.g. Priority 2 or 3."""
        for priority, tag, emoji_task in (
            (1, "work", "Write report"),
            (2, "guitar", "Practice scales"),
            (3, "health", "Go for a run"),
        ):
            mock_vault.reset_mock()
            mock_vault.get_note.return_value = rendered_vault_template

            daily_note.fill_priority(
                "2026-06-16", priority, emoji_task, tag, "1h",
                why_it_matters="testing", time_block="10:00-11:00",
            )
            filled = mock_vault.save_note.call_args[0][1]

            mock_vault.get_note.return_value = filled
            result = daily_note.get_priorities("2026-06-16")
            assert result[priority]["task"] == emoji_task
            assert result[priority]["tag"] == tag
            assert result[priority]["time_block"] == "10:00-11:00"
            other_slots = {1, 2, 3} - {priority}
            for other in other_slots:
                assert result[other] is None

            mock_vault.get_note.return_value = filled
            daily_note.clear_priority("2026-06-16", priority)
            cleared = mock_vault.save_note.call_args[0][1]
            assert cleared == rendered_vault_template

    def test_patch_after_fill_then_clear_round_trip(self, daily_note, mock_vault, rendered_vault_template):
        """fill -> patch (partial edit) -> clear must still return to the
        original unfilled content, exercising patch_priority's anchored
        field lookups against the real vault template structure."""
        mock_vault.get_note.return_value = rendered_vault_template
        daily_note.fill_priority(
            "2026-06-16", 2, "Practice guitar", "guitar", "30m", time_block="18:00",
        )
        filled = mock_vault.save_note.call_args[0][1]

        mock_vault.get_note.return_value = filled
        daily_note.patch_priority("2026-06-16", 2, time_block="18:00-18:30", why="Daily habit")
        patched = mock_vault.save_note.call_args[0][1]
        assert "**Time block:** 18:00-18:30" in patched
        assert "**Why it matters:** Daily habit" in patched

        mock_vault.get_note.return_value = patched
        daily_note.clear_priority("2026-06-16", 2)
        cleared = mock_vault.save_note.call_args[0][1]
        assert cleared == rendered_vault_template
