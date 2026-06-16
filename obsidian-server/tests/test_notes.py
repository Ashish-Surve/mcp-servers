"""
Tests for notes.py — daily note priority slot manipulation.

Uses the real config.py (env vars stubbed via monkeypatch) and a MagicMock
VaultClient so no real Obsidian instance or filesystem is touched.

These tests pin down the exact markdown structure notes.py depends on
(fixed line offsets, exact substring markers, regex anchors) so that any
future change to config.py's structural constants or notes.py's parsing
logic is caught immediately rather than silently producing wrong output.
"""

import pytest
from unittest.mock import MagicMock


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


def _empty_note(for_date="2026-06-16"):
    """A minimal note with one unfilled priority slot, matching the real template shape."""
    return f"""# 📝 {for_date}

## 🔥 Priorities

### Priority 1

- [ ] #todo **Task:** 📅 {for_date} 🔺 #{{{{tag}}}}
- **Feeds:**
- **Why it matters:**
- **Time estimate:**
- **Time block:**

### Priority 2

- [ ] #todo **Task:** 📅 {for_date} ⏫ #{{{{tag}}}}
- **Feeds:**
- **Why it matters:**
- **Time estimate:**
- **Time block:**

### Priority 3

- [ ] #todo **Task:** 📅 {for_date} 🔼 #{{{{tag}}}}
- **Feeds:**
- **Why it matters:**
- **Time estimate:**
- **Time block:**

---

## 📝 Notes

### Ideas

### Links
"""


def _filled_note(for_date="2026-06-16"):
    return f"""# 📝 {for_date}

## 🔥 Priorities

### Priority 1

- [ ] #todo **Task:** Write report 📅 {for_date} 🔺 #work
- **Feeds:** [[Project]]
- **Why it matters:** Deadline tomorrow
- **Time estimate:** 2h
- **Time block:** 09:00-11:00

---
"""


class TestFillPriority:
    def test_fills_placeholder(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = _empty_note()
        daily_note.fill_priority(
            "2026-06-16", 1, "Write report", "work", "2h",
            why_it_matters="Deadline tomorrow", time_block="09:00-11:00", feeds="[[Project]]",
        )
        saved = mock_vault.save_note.call_args[0][1]
        assert "**Task:** Write report 📅 2026-06-16 🔺 #work" in saved
        assert "**Feeds:** [[Project]]" in saved
        assert "**Why it matters:** Deadline tomorrow" in saved
        assert "**Time estimate:** 2h" in saved
        assert "**Time block:** 09:00-11:00" in saved

    def test_raises_if_note_missing(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = ""
        with pytest.raises(ValueError, match="No daily note"):
            daily_note.fill_priority("2026-06-16", 1, "x", "work", "1h")

    def test_raises_if_already_filled(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = _filled_note()
        with pytest.raises(ValueError, match="already be filled"):
            daily_note.fill_priority("2026-06-16", 1, "x", "work", "1h")


class TestClearPriority:
    def test_clears_filled_slot_back_to_placeholder(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = _filled_note()
        daily_note.clear_priority("2026-06-16", 1)
        saved = mock_vault.save_note.call_args[0][1]
        assert "- [ ] #todo **Task:** 📅 2026-06-16 🔺 #{{tag}}" in saved
        assert "Write report" not in saved

    def test_raises_if_section_missing(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = "# Empty note\n"
        with pytest.raises(ValueError, match="section not found"):
            daily_note.clear_priority("2026-06-16", 1)

    def test_raises_if_slot_already_empty(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = _empty_note()
        with pytest.raises(ValueError, match="empty already"):
            daily_note.clear_priority("2026-06-16", 1)


class TestPatchPriority:
    def test_patches_individual_fields(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = _filled_note()
        daily_note.patch_priority("2026-06-16", 1, time_block="14:00-15:00")
        saved = mock_vault.save_note.call_args[0][1]
        assert "**Time block:** 14:00-15:00" in saved
        # Untouched fields remain
        assert "**Task:** Write report 📅 2026-06-16 🔺 #work" in saved

    def test_patch_task_preserves_date_and_tag(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = _filled_note()
        daily_note.patch_priority("2026-06-16", 1, task="Write final report")
        saved = mock_vault.save_note.call_args[0][1]
        assert "**Task:** Write final report 📅 2026-06-16 🔺 #work" in saved

    def test_patch_task_replaces_embedded_tag(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = _filled_note()
        daily_note.patch_priority("2026-06-16", 1, task="Write final report #urgent")
        saved = mock_vault.save_note.call_args[0][1]
        assert "**Task:** Write final report 📅 2026-06-16 🔺 #urgent" in saved

    def test_completed_marks_checkbox_and_stamps_date(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = _filled_note()
        daily_note.patch_priority("2026-06-16", 1, completed=True)
        saved = mock_vault.save_note.call_args[0][1]
        assert "- [x] #todo **Task:** Write report 📅 2026-06-16 🔺 #work ✅ 2026-06-16" in saved

    def test_raises_if_section_missing(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = "# Empty note\n"
        with pytest.raises(ValueError, match="section not found"):
            daily_note.patch_priority("2026-06-16", 1, time_block="x")


class TestSetTimeBlock:
    def test_updates_time_block_line(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = _filled_note()
        daily_note.set_time_block("2026-06-16", 1, "[[SomeEvent]]")
        saved = mock_vault.save_note.call_args[0][1]
        assert "**Time block:** [[SomeEvent]]" in saved

    def test_raises_if_section_missing(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = "# Empty note\n"
        with pytest.raises(ValueError, match="section not found"):
            daily_note.set_time_block("2026-06-16", 1, "x")


class TestGetPriorities:
    def test_unfilled_slot_returns_none(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = _empty_note()
        result = daily_note.get_priorities("2026-06-16")
        assert result[1] is None
        assert result[2] is None
        assert result[3] is None

    def test_filled_slot_returns_structured_dict(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = _filled_note()
        result = daily_note.get_priorities("2026-06-16")
        assert result[1] == {
            "task": "Write report",
            "tag": "work",
            "feeds": "[[Project]]",
            "why": "Deadline tomorrow",
            "time_estimate": "2h",
            "time_block": "09:00-11:00",
            "done": False,
        }

    def test_missing_note_returns_all_none(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = ""
        result = daily_note.get_priorities("2026-06-16")
        assert result == {1: None, 2: None, 3: None}

    def test_done_task_detected(self, daily_note, mock_vault):
        content = _filled_note().replace("- [ ] #todo", "- [x] #todo", 1)
        mock_vault.get_note.return_value = content
        result = daily_note.get_priorities("2026-06-16")
        assert result[1]["done"] is True


class TestFillTomorrowPriority:
    def test_fills_placeholder(self, daily_note, mock_vault):
        content = "1. [ ] #todo 📅 2026-06-17 🔺 #{{tag}}\n"
        mock_vault.get_note.return_value = content
        daily_note.fill_tomorrow_priority("2026-06-16", 1, "Plan day", "work")
        saved = mock_vault.save_note.call_args[0][1]
        assert "1. [ ] #todo Plan day 📅 2026-06-17 🔺 #work" in saved

    def test_raises_if_placeholder_missing(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = "no placeholder here"
        with pytest.raises(ValueError, match="placeholder not found"):
            daily_note.fill_tomorrow_priority("2026-06-16", 1, "x", "work")


class TestAddQuickNote:
    def test_appends_under_heading(self, daily_note, mock_vault):
        mock_vault.get_note.return_value = "### Ideas\n\n### Links\n"
        daily_note.add_quick_note("2026-06-16", "ideas", "New idea")
        saved = mock_vault.save_note.call_args[0][1]
        assert "### Ideas\n- New idea" in saved

    def test_raises_on_unknown_section(self, daily_note, mock_vault):
        with pytest.raises(ValueError, match="Section must be one of"):
            daily_note.add_quick_note("2026-06-16", "bogus", "text")


class TestBuiltinTemplate:
    def test_contains_three_priority_headings(self, daily_note):
        rendered = daily_note._builtin_template("2026-06-16")
        for n in (1, 2, 3):
            assert f"### Priority {n}" in rendered

    def test_unfilled_slots_use_tag_placeholder(self, daily_note):
        rendered = daily_note._builtin_template("2026-06-16")
        assert rendered.count("#{{tag}}") == 6  # 3 priorities + 3 tomorrow prep

    def test_round_trips_through_get_priorities(self, daily_note, mock_vault):
        """The built-in template's unfilled slots must be recognized as empty
        by get_priorities — guards against the fallback template and the
        parsing logic drifting apart."""
        rendered = daily_note._builtin_template("2026-06-16")
        mock_vault.get_note.return_value = rendered
        result = daily_note.get_priorities("2026-06-16")
        assert result == {1: None, 2: None, 3: None}

    def test_round_trips_through_fill_and_get(self, daily_note, mock_vault):
        """Fill a priority in the built-in template, then read it back —
        exercises fill_priority + get_priorities against the same template
        source to catch structural drift between them."""
        rendered = daily_note._builtin_template("2026-06-16")
        mock_vault.get_note.return_value = rendered

        daily_note.fill_priority(
            "2026-06-16", 2, "Practice guitar", "guitar", "30m",
            why_it_matters="Daily habit", time_block="18:00-18:30",
        )
        saved = mock_vault.save_note.call_args[0][1]

        mock_vault.get_note.return_value = saved
        result = daily_note.get_priorities("2026-06-16")
        assert result[2]["task"] == "Practice guitar"
        assert result[2]["tag"] == "guitar"
        assert result[2]["time_block"] == "18:00-18:30"
        assert result[1] is None
        assert result[3] is None


# ---------------------------------------------------------------------------
# Phase 2 — anchored parsing hardening (manual edits / Tasks plugin metadata)
# ---------------------------------------------------------------------------
#
# These tests pin down behavior that fixed line-offset parsing would get
# wrong: reordered/extra-blank-line sections, and metadata the Tasks
# community plugin (https://publish.obsidian.md/tasks) inserts into a task
# line — its own priority emoji, recurrence, scheduled/start/due dates, and
# done-date — which can appear interleaved with this app's own fields.

def _note_with_section(body: str, for_date="2026-06-16") -> str:
    """Wrap a raw '### Priority N ...' block in minimal note scaffolding."""
    return f"# 📝 {for_date}\n\n## 🔥 Priorities\n\n{body}\n"


class TestReorderedAndExtraLines:
    """A user manually edits a filled slot in Obsidian: adds a blank line,
    reorders fields. Fixed offsets (idx+2..idx+6) would silently read/write
    the wrong line; anchored label search must still find the right one."""

    def test_get_priorities_survives_extra_blank_line(self, daily_note, mock_vault):
        content = _note_with_section(
            "### Priority 1\n\n"
            "\n"  # extra blank line a user added
            "- [ ] #todo **Task:** Write report 📅 2026-06-16 🔺 #work\n"
            "- **Feeds:** [[Project]]\n"
            "- **Why it matters:** Deadline tomorrow\n"
            "- **Time estimate:** 2h\n"
            "- **Time block:** 09:00-11:00\n"
        )
        mock_vault.get_note.return_value = content
        result = daily_note.get_priorities("2026-06-16")
        assert result[1]["task"] == "Write report"
        assert result[1]["time_block"] == "09:00-11:00"

    def test_get_priorities_survives_reordered_fields(self, daily_note, mock_vault):
        content = _note_with_section(
            "### Priority 1\n\n"
            "- [ ] #todo **Task:** Write report 📅 2026-06-16 🔺 #work\n"
            "- **Time block:** 09:00-11:00\n"  # moved up
            "- **Feeds:** [[Project]]\n"
            "- **Why it matters:** Deadline tomorrow\n"
            "- **Time estimate:** 2h\n"
        )
        mock_vault.get_note.return_value = content
        result = daily_note.get_priorities("2026-06-16")
        assert result[1]["time_block"] == "09:00-11:00"
        assert result[1]["feeds"] == "[[Project]]"
        assert result[1]["time_estimate"] == "2h"

    def test_patch_priority_survives_reordered_fields(self, daily_note, mock_vault):
        content = _note_with_section(
            "### Priority 1\n\n"
            "- [ ] #todo **Task:** Write report 📅 2026-06-16 🔺 #work\n"
            "- **Time block:** 09:00-11:00\n"
            "- **Feeds:** [[Project]]\n"
            "- **Why it matters:** Deadline tomorrow\n"
            "- **Time estimate:** 2h\n"
        )
        mock_vault.get_note.return_value = content
        daily_note.patch_priority("2026-06-16", 1, time_estimate="3h")
        saved = mock_vault.save_note.call_args[0][1]
        assert "**Time estimate:** 3h" in saved
        # Untouched fields/lines remain, in their (reordered) place
        assert "**Time block:** 09:00-11:00" in saved
        assert "**Feeds:** [[Project]]" in saved

    def test_set_time_block_does_not_bleed_into_next_section(self, daily_note, mock_vault):
        """If Priority 1's Time block line is missing, set_time_block must
        raise rather than silently editing Priority 2's Time block line."""
        content = _note_with_section(
            "### Priority 1\n\n"
            "- [ ] #todo **Task:** A 📅 2026-06-16 🔺 #work\n"
            "- **Feeds:**\n"
            "- **Why it matters:**\n"
            "- **Time estimate:**\n"
            "\n"
            "### Priority 2\n\n"
            "- [ ] #todo **Task:** B 📅 2026-06-16 ⏫ #work\n"
            "- **Feeds:**\n"
            "- **Why it matters:**\n"
            "- **Time estimate:**\n"
            "- **Time block:** 14:00-15:00\n"
        )
        mock_vault.get_note.return_value = content
        with pytest.raises(ValueError, match="Time block.*not found"):
            daily_note.set_time_block("2026-06-16", 1, "x")
        mock_vault.save_note.assert_not_called()


class TestTasksPluginMetadataTolerance:
    """The Tasks community plugin can append/insert its own metadata emoji
    (priority, recurrence, scheduled/due/done dates) on a task line. These
    must be preserved verbatim, never swallowed into the parsed task text
    or dropped on rewrite."""

    def test_get_priorities_ignores_trailing_recurrence_and_done_date(self, daily_note, mock_vault):
        content = _note_with_section(
            "### Priority 1\n\n"
            "- [x] #todo **Task:** Write report 📅 2026-06-16 🔺 #work 🔁 every week ✅ 2026-06-17\n"
            "- **Feeds:** [[Project]]\n"
            "- **Why it matters:** Deadline\n"
            "- **Time estimate:** 2h\n"
            "- **Time block:** 09:00-11:00\n"
        )
        mock_vault.get_note.return_value = content
        result = daily_note.get_priorities("2026-06-16")
        assert result[1]["task"] == "Write report"
        assert result[1]["tag"] == "work"
        assert result[1]["done"] is True

    def test_get_priorities_does_not_swallow_tasks_priority_emoji_into_task_text(self, daily_note, mock_vault):
        """A Tasks-plugin priority emoji inserted before our own 📅 marker
        must not end up appended to the parsed task description."""
        content = _note_with_section(
            "### Priority 1\n\n"
            "- [ ] #todo **Task:** Write report ⏫ 📅 2026-06-16 🔺 #work\n"
            "- **Feeds:**\n"
            "- **Why it matters:**\n"
            "- **Time estimate:**\n"
            "- **Time block:**\n"
        )
        mock_vault.get_note.return_value = content
        result = daily_note.get_priorities("2026-06-16")
        assert result[1]["task"] == "Write report"
        assert "⏫" not in result[1]["task"]

    def test_patch_priority_preserves_tasks_plugin_metadata_on_task_rewrite(self, daily_note, mock_vault):
        """Patching the task text must not drop a Tasks-plugin recurrence
        rule or done-date appended after our own #tag."""
        content = _note_with_section(
            "### Priority 1\n\n"
            "- [ ] #todo **Task:** Write report 📅 2026-06-16 🔺 #work 🔁 every week\n"
            "- **Feeds:**\n"
            "- **Why it matters:**\n"
            "- **Time estimate:**\n"
            "- **Time block:**\n"
        )
        mock_vault.get_note.return_value = content
        daily_note.patch_priority("2026-06-16", 1, task="Write final report")
        saved = mock_vault.save_note.call_args[0][1]
        assert "**Task:** Write final report 📅 2026-06-16 🔺 #work 🔁 every week" in saved

    def test_patch_priority_replaces_tag_while_preserving_recurrence(self, daily_note, mock_vault):
        content = _note_with_section(
            "### Priority 1\n\n"
            "- [ ] #todo **Task:** Write report 📅 2026-06-16 🔺 #work 🔁 every week\n"
            "- **Feeds:**\n"
            "- **Why it matters:**\n"
            "- **Time estimate:**\n"
            "- **Time block:**\n"
        )
        mock_vault.get_note.return_value = content
        daily_note.patch_priority("2026-06-16", 1, task="Write final report #urgent")
        saved = mock_vault.save_note.call_args[0][1]
        assert "#urgent" in saved
        assert "#work" not in saved
        assert "🔁 every week" in saved

    def test_completed_detects_capital_x_checkbox(self, daily_note, mock_vault):
        """Obsidian/Tasks-plugin sometimes write '[X]' (capital) for done."""
        content = _note_with_section(
            "### Priority 1\n\n"
            "- [X] #todo **Task:** Write report 📅 2026-06-16 🔺 #work\n"
            "- **Feeds:**\n"
            "- **Why it matters:**\n"
            "- **Time estimate:**\n"
            "- **Time block:**\n"
        )
        mock_vault.get_note.return_value = content
        result = daily_note.get_priorities("2026-06-16")
        assert result[1]["done"] is True

    def test_clear_priority_handles_task_with_trailing_metadata(self, daily_note, mock_vault):
        """clear_priority must still match/clear a filled slot even when
        the task line carries extra Tasks-plugin metadata at the end —
        the old single-regex implementation required an exact line shape
        and would have raised 'already empty' here."""
        content = _note_with_section(
            "### Priority 1\n\n"
            "- [x] #todo **Task:** Write report 📅 2026-06-16 🔺 #work 🔁 every week ✅ 2026-06-17\n"
            "- **Feeds:** [[Project]]\n"
            "- **Why it matters:** Deadline\n"
            "- **Time estimate:** 2h\n"
            "- **Time block:** 09:00-11:00\n"
        )
        mock_vault.get_note.return_value = content
        daily_note.clear_priority("2026-06-16", 1)
        saved = mock_vault.save_note.call_args[0][1]
        assert "- [ ] #todo **Task:** 📅 2026-06-16 🔺 #{{tag}}" in saved
        assert "Write report" not in saved


class TestScopedErrorMessages:
    """A missing/renamed field should raise a clear, scoped error rather
    than an unhandled ValueError or a silent wrong-line edit."""

    def test_patch_priority_field_not_found_raises_clear_error(self, daily_note, mock_vault):
        content = _note_with_section(
            "### Priority 1\n\n"
            "- [ ] #todo **Task:** A 📅 2026-06-16 🔺 #work\n"
            "- **Feeds:**\n"
            "- **Why it matters:**\n"
            "- **Time estimate:**\n"
            # Time block line missing entirely (user deleted it)
        )
        mock_vault.get_note.return_value = content
        with pytest.raises(ValueError, match=r"Time block.*not found"):
            daily_note.patch_priority("2026-06-16", 1, time_block="09:00")

    def test_patch_priority_task_line_missing_raises_clear_error(self, daily_note, mock_vault):
        content = _note_with_section(
            "### Priority 1\n\n"
            "- **Feeds:**\n"  # task checkbox line deleted entirely
        )
        mock_vault.get_note.return_value = content
        with pytest.raises(ValueError, match="Task checkbox line not found"):
            daily_note.patch_priority("2026-06-16", 1, task="x")
