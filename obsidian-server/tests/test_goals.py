"""
Tests for goals.py — Long-Term/Monthly/Weekly goal file manipulation.

Uses the real config.py (env vars stubbed via monkeypatch) and a MagicMock
VaultClient so no real Obsidian instance or filesystem is touched.

Pins down the exact markdown structure goals.py depends on (section
headings, field labels, the Done? checklist) so structural drift between
config.py's constants and goals.py's parsing logic is caught immediately.
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
def goals_mgr(mock_vault):
    from goals import GoalsManager
    return GoalsManager(mock_vault)


MONTHLY_FILE = """# 📅 June 2026

## Monthly Goals

---

## Review
"""

WEEKLY_FILE = """# 📆 Week 25

## Weekly Goals

---

## Review

### Done?

### What went well?
"""

LONGTERM_FILE = """# 🎯 Long-Term Goals

### DS
**Goal:** Become a data scientist
**Timeline:** 2 years
**Why this matters:** Career growth
**Success looks like:** Employed as DS

---

## Review Schedule

*Last updated:* 2026-01-01
"""


class TestAddMonthlyGoal:
    def test_adds_goal_block_with_correct_fields(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = MONTHLY_FILE
        goals_mgr.add_monthly_goal(
            "DS-M1", "Finish course", "DS",
            why_it_matters="Builds foundation", success_metric="Certificate",
            time_needed="10h",
        )
        saved = mock_vault.save_file.call_args[0][1]
        assert "### DS-M1" in saved
        assert "**Goal:** Finish course" in saved
        assert "**Feeds:** [[Long-Term-Goals#DS]]" in saved
        assert "**Why this matters:** Builds foundation" in saved
        assert "**Success metric:** Certificate" in saved
        assert "**Time needed:** 10h" in saved

    def test_inserts_before_first_separator(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = MONTHLY_FILE
        goals_mgr.add_monthly_goal("DS-M1", "Goal", "DS")
        saved = mock_vault.save_file.call_args[0][1]
        assert saved.index("### DS-M1") < saved.index("## Review")

    def test_returns_error_if_file_missing(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = ""
        result = goals_mgr.add_monthly_goal("DS-M1", "Goal", "DS")
        assert "not found" in result
        mock_vault.save_file.assert_not_called()

    def test_returns_error_if_section_missing(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = "# No monthly goals section here\n"
        result = goals_mgr.add_monthly_goal("DS-M1", "Goal", "DS")
        assert "Monthly Goals" in result
        mock_vault.save_file.assert_not_called()


class TestAddWeeklyGoal:
    def test_adds_goal_block_with_correct_fields(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = WEEKLY_FILE
        goals_mgr.add_weekly_goal("DS-W1", "Read chapter 3", "DS-M1", time_blocks="3 hours", week="2026-W25")
        saved = mock_vault.save_file.call_args[0][1]
        assert "### DS-W1" in saved
        assert "**Goal:** Read chapter 3" in saved
        assert "**Feeds:** [[2026-06#DS-M1]]" in saved
        assert "**Time blocks:** 3 hours" in saved

    def test_adds_to_done_checklist(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = WEEKLY_FILE
        goals_mgr.add_weekly_goal("DS-W1", "Read chapter 3", "DS-M1", week="2026-W25")
        saved = mock_vault.save_file.call_args[0][1]
        assert "### Done?\n- [ ] DS-W1" in saved

    def test_returns_error_if_section_missing(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = "# No weekly goals section\n"
        result = goals_mgr.add_weekly_goal("DS-W1", "Goal", "DS-M1", week="2026-W25")
        assert "Weekly Goals" in result


class TestUpdateGoalStatus:
    def test_inserts_status_line_when_absent(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = MONTHLY_FILE.replace(
            "## Monthly Goals\n", "## Monthly Goals\n\n### DS-M1\n**Goal:** x\n"
        )
        goals_mgr.update_goal_status("DS-M1", "in_progress", "monthly", file_id="2026-06")
        saved = mock_vault.save_file.call_args[0][1]
        assert "**Status:** 🟡" in saved

    def test_replaces_existing_status_line(self, goals_mgr, mock_vault):
        content = MONTHLY_FILE.replace(
            "## Monthly Goals\n",
            "## Monthly Goals\n\n### DS-M1\n**Goal:** x\n**Status:** 🔴\n",
        )
        mock_vault.get_file.return_value = content
        goals_mgr.update_goal_status("DS-M1", "done", "monthly", file_id="2026-06")
        saved = mock_vault.save_file.call_args[0][1]
        assert "**Status:** ✅" in saved
        assert "**Status:** 🔴" not in saved

    def test_done_checks_weekly_checklist_box(self, goals_mgr, mock_vault):
        content = WEEKLY_FILE.replace(
            "## Weekly Goals\n", "## Weekly Goals\n\n### DS-W1\n**Goal:** x\n"
        ).replace("### Done?\n", "### Done?\n- [ ] DS-W1\n")
        mock_vault.get_file.return_value = content
        goals_mgr.update_goal_status("DS-W1", "done", "weekly", file_id="2026-W25")
        saved = mock_vault.save_file.call_args[0][1]
        assert "- [x] DS-W1" in saved

    def test_uncheck_weekly_checklist_box_when_not_done(self, goals_mgr, mock_vault):
        content = WEEKLY_FILE.replace(
            "## Weekly Goals\n", "## Weekly Goals\n\n### DS-W1\n**Goal:** x\n"
        ).replace("### Done?\n", "### Done?\n- [x] DS-W1\n")
        mock_vault.get_file.return_value = content
        goals_mgr.update_goal_status("DS-W1", "in_progress", "weekly", file_id="2026-W25")
        saved = mock_vault.save_file.call_args[0][1]
        assert "- [ ] DS-W1" in saved

    def test_rejects_invalid_status(self, goals_mgr, mock_vault):
        result = goals_mgr.update_goal_status("DS-M1", "bogus", "monthly")
        assert "Status must be one of" in result

    def test_rejects_invalid_level(self, goals_mgr, mock_vault):
        result = goals_mgr.update_goal_status("DS-M1", "done", "bogus")
        assert "Level must be" in result

    def test_returns_error_if_goal_not_found(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = MONTHLY_FILE
        result = goals_mgr.update_goal_status("NOPE", "done", "monthly", file_id="2026-06")
        assert "not found" in result


class TestAddLongtermGoal:
    def test_adds_goal_block_with_correct_fields(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = LONGTERM_FILE
        goals_mgr.add_longterm_goal("GU", "Learn guitar", "1 year", "Creative outlet", "Can play songs")
        saved = mock_vault.save_file.call_args[0][1]
        assert "### GU" in saved
        assert "**Goal:** Learn guitar" in saved
        assert "**Timeline:** 1 year" in saved
        assert "**Why this matters:** Creative outlet" in saved
        assert "**Success looks like:** Can play songs" in saved

    def test_inserts_before_review_schedule(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = LONGTERM_FILE
        goals_mgr.add_longterm_goal("GU", "Learn guitar", "1 year", "x", "y")
        saved = mock_vault.save_file.call_args[0][1]
        assert saved.index("### GU") < saved.index("## Review Schedule")

    def test_updates_last_updated_line(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = LONGTERM_FILE
        goals_mgr.add_longterm_goal("GU", "Learn guitar", "1 year", "x", "y")
        saved = mock_vault.save_file.call_args[0][1]
        assert "*Last updated:* 2026-01-01" not in saved
        assert "*Last updated:*" in saved

    def test_returns_error_if_file_missing(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = ""
        result = goals_mgr.add_longterm_goal("GU", "x", "y", "z", "w")
        assert "not found" in result


class TestWhyMattersConsistency:
    """Regression test for the pre-fix inconsistency where add_monthly_goal
    used '**Why it matters:**' and add_longterm_goal used '**Why this
    matters:**' for conceptually the same field. Both must now agree."""

    def test_monthly_and_longterm_use_same_label(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = MONTHLY_FILE
        goals_mgr.add_monthly_goal("DS-M1", "Goal", "DS", why_it_matters="reason")
        monthly_saved = mock_vault.save_file.call_args[0][1]

        mock_vault.get_file.return_value = LONGTERM_FILE
        goals_mgr.add_longterm_goal("GU", "Goal", "1y", "reason", "outcome")
        longterm_saved = mock_vault.save_file.call_args[0][1]

        assert "**Why this matters:** reason" in monthly_saved
        assert "**Why this matters:** reason" in longterm_saved


class TestCreateMonthlyAndWeeklyGoals:
    def test_create_monthly_goals_contains_heading(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = ""
        goals_mgr.create_monthly_goals("2026-06")
        saved = mock_vault.save_file.call_args[0][1]
        assert "## Monthly Goals" in saved

    def test_create_weekly_goals_contains_heading_and_checklist(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = ""
        goals_mgr.create_weekly_goals("2026-W25")
        saved = mock_vault.save_file.call_args[0][1]
        assert "## Weekly Goals" in saved
        assert "### Done?" in saved

    def test_does_not_overwrite_existing_file(self, goals_mgr, mock_vault):
        mock_vault.get_file.return_value = MONTHLY_FILE
        result = goals_mgr.create_monthly_goals("2026-06")
        assert "already exists" in result
        mock_vault.save_file.assert_not_called()
