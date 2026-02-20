"""
goals.py — Goal hierarchy management for the Obsidian planning system.

Handles Long-Term, Monthly, and Weekly goal files:
  02-Long-Term-Goals/Long-Term-Goals.md
  03-Monthly/{YYYY-MM}.md
  04-Weekly/{YYYY-W##}.md
"""

import re
from datetime import date

from config import PLANNING_ROOT, log
from vault import VaultClient

# Status emoji mapping
STATUS_EMOJI = {
    "not_started": "🔴",
    "in_progress": "🟡",
    "done": "✅",
}


class GoalsManager:
    """Read and modify the goal hierarchy files in the Obsidian vault."""

    def __init__(self, vault: VaultClient) -> None:
        self._vault = vault

    # ── Path helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _prefixed(relative: str) -> str:
        """Prepend PLANNING_ROOT if set, otherwise use relative path as-is."""
        return f"{PLANNING_ROOT}/{relative}" if PLANNING_ROOT else relative

    def _longterm_path(self) -> str:
        return self._prefixed("02-Long-Term-Goals/Long-Term-Goals.md")

    def _monthly_path(self, month_id: str) -> str:
        return self._prefixed(f"03-Monthly/{month_id}.md")

    def _weekly_path(self, week_id: str) -> str:
        return self._prefixed(f"04-Weekly/{week_id}.md")

    # ── ISO date helpers ──────────────────────────────────────────────────

    @staticmethod
    def current_week_id() -> str:
        """Current ISO week, e.g. '2026-W08'."""
        iso = date.today().isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"

    @staticmethod
    def current_month_id() -> str:
        """Current month, e.g. '2026-02'."""
        return date.today().strftime("%Y-%m")

    @staticmethod
    def week_monday(week_id: str) -> date:
        """Parse 'YYYY-W##' and return the Monday date of that week."""
        parts = week_id.split("-W")
        year, week = int(parts[0]), int(parts[1])
        return date.fromisocalendar(year, week, 1)

    @staticmethod
    def month_id_from_week(week_id: str) -> str:
        """Return the month ID that contains the Monday of the given week."""
        monday = GoalsManager.week_monday(week_id)
        return monday.strftime("%Y-%m")

    # ── Tool: read_goals ──────────────────────────────────────────────────

    def read_goals(
        self,
        level: str = "all",
        month: str = "",
        week: str = "",
    ) -> str:
        """Read the goal hierarchy file(s) and return their content.

        level: "longterm", "monthly", "weekly", or "all"
        month: YYYY-MM (defaults to current month)
        week:  YYYY-W## (defaults to current week)
        """
        month_id = month or self.current_month_id()
        week_id = week or self.current_week_id()

        parts: list[str] = []

        if level in ("longterm", "all"):
            content = self._vault.get_file(self._longterm_path())
            if content:
                parts.append(f"## Long-Term Goals\n\n{content}")
            else:
                parts.append("## Long-Term Goals\n\n_(file not found)_")

        if level in ("monthly", "all"):
            content = self._vault.get_file(self._monthly_path(month_id))
            if content:
                parts.append(f"## Monthly Goals — {month_id}\n\n{content}")
            else:
                parts.append(
                    f"## Monthly Goals — {month_id}\n\n"
                    f"_(file not found — use create_monthly_goals to create it)_"
                )

        if level in ("weekly", "all"):
            content = self._vault.get_file(self._weekly_path(week_id))
            if content:
                parts.append(f"## Weekly Goals — {week_id}\n\n{content}")
            else:
                parts.append(
                    f"## Weekly Goals — {week_id}\n\n"
                    f"_(file not found — use create_weekly_goals to create it)_"
                )

        if not parts:
            return f"❌ Unknown level '{level}'. Use: longterm, monthly, weekly, or all."

        return "\n\n---\n\n".join(parts)

    # ── Tool: create_monthly_goals ────────────────────────────────────────

    def create_monthly_goals(self, month: str = "") -> str:
        """Create a new monthly goals file from template.

        Only creates if it doesn't already exist.
        month: YYYY-MM (defaults to current month)
        """
        month_id = month or self.current_month_id()
        path = self._monthly_path(month_id)

        if self._vault.get_file(path):
            return f"Monthly goals file for {month_id} already exists. Use read_goals to view it."

        dt = date.fromisoformat(f"{month_id}-01")
        month_name = dt.strftime("%B")
        year = dt.year

        content = f"""# 📅 {month_name} {year}

**Vision check:** [[Long-Term-Goals]]

> What are the 1-3 most important things I'm blessed to do this month?
> What is the one thing I can focus on such that by doing it everything else will be easier or unnecessary?

---

## Monthly Goals

---

## Life This Month
*What's happening that I need to plan around?*
-

---

## Supporting Goals
*Important but secondary — only if main goals are on track*
-

---

## Review

> *Fill this in at month end*

### What worked well?

### What didn't work?

### What did I learn about myself?

### Adjustments for next month:
"""
        self._vault.save_file(path, content)
        log.info("Created monthly goals: %s", month_id)
        return f"✅ Created monthly goals file for {month_id}"

    # ── Tool: add_monthly_goal ────────────────────────────────────────────

    def add_monthly_goal(
        self,
        goal_code: str,
        goal: str,
        feeds: str,
        why_it_matters: str = "",
        success_metric: str = "",
        time_needed: str = "",
        month: str = "",
    ) -> str:
        """Add a goal block under '## Monthly Goals' in the monthly file.

        goal_code: e.g. "DS-M1"
        feeds:     long-term goal category code, e.g. "DS"
        """
        month_id = month or self.current_month_id()
        path = self._monthly_path(month_id)

        content = self._vault.get_file(path)
        if not content:
            return (
                f"❌ Monthly goals file for {month_id} not found. "
                "Run create_monthly_goals first."
            )

        section_heading = "## Monthly Goals"
        if section_heading not in content:
            return f"❌ '## Monthly Goals' section not found in {month_id}.md."

        block = (
            f"\n### {goal_code}\n"
            f"**Goal:** {goal}\n"
            f"**Feeds:** [[Long-Term-Goals#{feeds}]]\n"
            f"**Why this matters:** {why_it_matters}\n"
            f"**Success metric:** {success_metric}\n"
            f"**Time needed:** {time_needed}\n"
        )

        # Insert block before the first '---' after the section heading
        after_section = content.split(section_heading, 1)[1]
        before_section = content.split(section_heading, 1)[0]

        if "---" in after_section:
            insert_pos = after_section.index("---")
            updated_after = after_section[:insert_pos] + block + after_section[insert_pos:]
        else:
            updated_after = after_section + block

        self._vault.save_file(path, before_section + section_heading + updated_after)
        log.info("Added monthly goal %s to %s", goal_code, month_id)
        return f"✅ Added monthly goal {goal_code} to {month_id}"

    # ── Tool: create_weekly_goals ─────────────────────────────────────────

    def create_weekly_goals(
        self,
        week: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> str:
        """Create a new weekly goals file from template.

        Only creates if it doesn't already exist.
        week:       YYYY-W## (defaults to current ISO week)
        start_date: YYYY-MM-DD (calculated from week if omitted)
        end_date:   YYYY-MM-DD (calculated from week if omitted)
        """
        week_id = week or self.current_week_id()
        path = self._weekly_path(week_id)

        if self._vault.get_file(path):
            return f"Weekly goals file for {week_id} already exists. Use read_goals to view it."

        monday = (
            date.fromisoformat(start_date) if start_date else self.week_monday(week_id)
        )
        sunday = (
            date.fromisoformat(end_date)
            if end_date
            else date.fromisocalendar(monday.isocalendar()[0], monday.isocalendar()[1], 7)
        )

        week_num = monday.isocalendar()[1]
        month_id = monday.strftime("%Y-%m")
        mon_str = monday.strftime("%b %-d")
        sun_str = sunday.strftime("%b %-d")
        year = monday.year

        content = f"""# 📆 Week {week_num} — {mon_str} to {sun_str}, {year}

**This month:** [[{month_id}]]

> What are the 1-3 most important things I'm blessed to do this week?
> What is the one thing I can focus on such that by doing it everything else will be easier or unnecessary?

---

## Weekly Goals

---

## Review

> *Fill this in on Sunday*

### Done?

### What went well?

### What got in the way?

### Lessons for next week:
"""
        self._vault.save_file(path, content)
        log.info("Created weekly goals: %s", week_id)
        return f"✅ Created weekly goals file for {week_id}"

    # ── Tool: add_weekly_goal ─────────────────────────────────────────────

    def add_weekly_goal(
        self,
        goal_code: str,
        goal: str,
        feeds: str,
        time_blocks: str = "",
        week: str = "",
    ) -> str:
        """Add a goal block under '## Weekly Goals' in the weekly file.

        goal_code:   e.g. "DS-W1"
        feeds:       monthly goal code to link to, e.g. "DS-M1"
        time_blocks: e.g. "3 hours"
        """
        week_id = week or self.current_week_id()
        path = self._weekly_path(week_id)
        month_id = self.month_id_from_week(week_id)

        content = self._vault.get_file(path)
        if not content:
            return (
                f"❌ Weekly goals file for {week_id} not found. "
                "Run create_weekly_goals first."
            )

        section_heading = "## Weekly Goals"
        if section_heading not in content:
            return f"❌ '## Weekly Goals' section not found in {week_id}.md."

        block = (
            f"\n### {goal_code}\n"
            f"**Goal:** {goal}\n"
            f"**Feeds:** [[{month_id}#{feeds}]]\n"
            f"**Time blocks:** {time_blocks}\n"
        )

        # Insert block before the first '---' after the section heading
        after_section = content.split(section_heading, 1)[1]
        before_section = content.split(section_heading, 1)[0]

        if "---" in after_section:
            insert_pos = after_section.index("---")
            updated_after = after_section[:insert_pos] + block + after_section[insert_pos:]
        else:
            updated_after = after_section + block

        updated_content = before_section + section_heading + updated_after

        # Also add to the Done? checklist in Review
        done_heading = "### Done?"
        if done_heading in updated_content:
            updated_content = updated_content.replace(
                done_heading,
                f"{done_heading}\n- [ ] {goal_code}",
                1,
            )

        self._vault.save_file(path, updated_content)
        log.info("Added weekly goal %s to %s", goal_code, week_id)
        return f"✅ Added weekly goal {goal_code} to {week_id}"

    # ── Tool: update_goal_status ──────────────────────────────────────────

    def update_goal_status(
        self,
        goal_code: str,
        status: str,
        level: str,
        progress_note: str = "",
        file_id: str = "",
    ) -> str:
        """Update the status emoji on a monthly or weekly goal.

        status: "not_started", "in_progress", or "done"
        level:  "monthly" or "weekly"
        file_id: YYYY-MM or YYYY-W## (defaults to current)
        """
        if status not in STATUS_EMOJI:
            return f"❌ Status must be one of: {', '.join(STATUS_EMOJI)}"

        emoji = STATUS_EMOJI[status]
        status_value = f"{emoji} {progress_note}".strip() if progress_note else emoji

        if level == "monthly":
            resolved_id = file_id or self.current_month_id()
            path = self._monthly_path(resolved_id)
        elif level == "weekly":
            resolved_id = file_id or self.current_week_id()
            path = self._weekly_path(resolved_id)
        else:
            return "❌ Level must be 'monthly' or 'weekly'."

        content = self._vault.get_file(path)
        if not content:
            return f"❌ File for {resolved_id} not found."

        heading = f"### {goal_code}"
        if heading not in content:
            return f"❌ Goal '{goal_code}' not found in {resolved_id}."

        # Find the goal block and update or insert **Status:**
        before_goal, after_goal = content.split(heading, 1)

        # Find the end of this goal block (next ### heading or end of file)
        next_heading_match = re.search(r"\n###? ", after_goal)
        if next_heading_match:
            goal_block = after_goal[: next_heading_match.start()]
            rest = after_goal[next_heading_match.start():]
        else:
            goal_block = after_goal
            rest = ""

        if "**Status:**" in goal_block:
            goal_block = re.sub(
                r"\*\*Status:\*\* .*",
                f"**Status:** {status_value}",
                goal_block,
                count=1,
            )
        else:
            # Append Status line at end of the goal block (before trailing newlines)
            goal_block = goal_block.rstrip("\n") + f"\n**Status:** {status_value}\n"

        updated_content = before_goal + heading + goal_block + rest

        # For weekly goals marked "done": check the Done? checkbox
        if level == "weekly" and status == "done":
            updated_content = re.sub(
                r"- \[ \] " + re.escape(goal_code),
                f"- [x] {goal_code}",
                updated_content,
                count=1,
            )
        elif level == "weekly" and status != "done":
            # Uncheck if previously done
            updated_content = re.sub(
                r"- \[x\] " + re.escape(goal_code),
                f"- [ ] {goal_code}",
                updated_content,
                count=1,
            )

        self._vault.save_file(path, updated_content)
        log.info("Updated status of %s to %s in %s", goal_code, status, resolved_id)
        return f"✅ Updated {goal_code} status to {emoji} in {resolved_id}"

    # ── Tool: add_longterm_goal ───────────────────────────────────────────

    def add_longterm_goal(
        self,
        code: str,
        goal: str,
        timeline: str,
        why_it_matters: str,
        success_looks_like: str,
    ) -> str:
        """Add a new goal to Long-Term-Goals.md.

        Appends the goal block before the '## Review Schedule' section
        and updates the *Last updated:* line.
        """
        path = self._longterm_path()
        content = self._vault.get_file(path)
        if not content:
            return "❌ Long-Term-Goals.md not found in the vault."

        block = (
            f"\n### {code}\n"
            f"**Goal:** {goal}\n"
            f"**Timeline:** {timeline}\n"
            f"**Why this matters:** {why_it_matters}\n"
            f"**Success looks like:** {success_looks_like}\n"
        )

        review_heading = "## Review Schedule"
        if review_heading in content:
            before_review, after_review = content.split(review_heading, 1)
            # Insert before the '---' that immediately precedes Review Schedule
            if before_review.rstrip().endswith("---"):
                # There's a separator before the heading — insert before it
                stripped = before_review.rstrip()
                trimmed = stripped[: -len("---")].rstrip()
                updated_content = trimmed + block + "\n\n---\n" + review_heading + after_review
            else:
                updated_content = before_review + block + review_heading + after_review
        else:
            # No review schedule section — append at end
            updated_content = content + block

        # Update *Last updated:* line
        today_str = date.today().isoformat()
        if "*Last updated:*" in updated_content:
            updated_content = re.sub(
                r"\*Last updated:\*.*",
                f"*Last updated:* {today_str}",
                updated_content,
                count=1,
            )

        self._vault.save_file(path, updated_content)
        log.info("Added long-term goal: %s", code)
        return f"✅ Added long-term goal '{code}' to Long-Term-Goals.md"
