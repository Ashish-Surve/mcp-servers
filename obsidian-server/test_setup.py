"""
Tests for setup.py scaffold logic and notes.py Templater rendering.

Does not touch the real vault or .env — all I/O is done via tmp_path.
config.py raises RuntimeError if OBSIDIAN_API_KEY is unset, so we patch
the env before any server imports happen.
"""

import importlib
import os
import re
import sys
import types
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Ensure tests never read from the real .env or write to it."""
    monkeypatch.setenv("OBSIDIAN_API_KEY", "test-key")
    monkeypatch.setenv("OBSIDIAN_URL", "https://127.0.0.1:27124/")
    monkeypatch.setenv("VAULT_FOLDER", "05-Daily-Notes")
    monkeypatch.setenv("CALENDAR_FOLDER", "06-Calendar-Events")
    monkeypatch.setenv("PLANNING_ROOT", "")


@pytest.fixture()
def vault(tmp_path):
    """Return a fresh temp vault root."""
    return tmp_path / "vault"


# ---------------------------------------------------------------------------
# Helpers — import setup module with a fake .env path
# ---------------------------------------------------------------------------

def _load_setup(env_file: Path):
    """Import setup.py with load_dotenv pointed at env_file."""
    spec = importlib.util.spec_from_file_location(
        "setup",
        Path(__file__).parent / "setup.py",
    )
    mod = importlib.util.module_from_spec(spec)
    with patch("dotenv.load_dotenv"):
        spec.loader.exec_module(mod)
    mod._ENV_FILE_OVERRIDE = env_file
    return mod


# ---------------------------------------------------------------------------
# Import setup once for the whole module (dotenv is mocked out)
# ---------------------------------------------------------------------------

with patch("dotenv.load_dotenv"):
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("setup", Path(__file__).parent / "setup.py")
    setup = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(setup)


# ---------------------------------------------------------------------------
# setup.py — folder scaffolding
# ---------------------------------------------------------------------------

class TestFolderScaffolding:
    def test_all_folders_created(self, vault):
        for rel in setup.FOLDERS:
            setup.ensure_folder(vault, rel)
        for rel in setup.FOLDERS:
            assert (vault / rel).is_dir(), f"Missing folder: {rel}"

    def test_folder_count(self):
        assert len(setup.FOLDERS) == 23

    def test_idempotent_folder(self, vault, capsys):
        vault.mkdir()
        setup.ensure_folder(vault, "05-Daily-Notes")
        setup.ensure_folder(vault, "05-Daily-Notes")
        out = capsys.readouterr().out
        assert out.count("exists") == 1
        assert out.count("created") == 1

    def test_nested_folder_created(self, vault):
        setup.ensure_folder(vault, "06-Calendar-Events/DataScience")
        assert (vault / "06-Calendar-Events/DataScience").is_dir()


# ---------------------------------------------------------------------------
# setup.py — seed files
# ---------------------------------------------------------------------------

class TestSeedFiles:
    def test_priority_queue_created(self, vault):
        path = vault / "08-Queue/Priority-Queue.md"
        setup.ensure_file(path, setup.PRIORITY_QUEUE_CONTENT)
        assert path.exists()
        content = path.read_text()
        assert "## 🔺 P1 — Do Soon" in content
        assert "## ⏫ P2 — Do This Week/Next" in content
        assert "## 🔼 P3 — Someday" in content

    def test_priority_queue_kanban_metadata(self, vault):
        path = vault / "08-Queue/Priority-Queue.md"
        setup.ensure_file(path, setup.PRIORITY_QUEUE_CONTENT)
        assert 'kanban-plugin' in path.read_text()

    def test_long_term_goals_anchors(self, vault):
        path = vault / "02-Long-Term-Goals/Long-Term-Goals.md"
        setup.ensure_file(path, setup.LONG_TERM_GOALS_CONTENT)
        content = path.read_text()
        for anchor in ("^H", "^DS", "^INV", "^G", "^P"):
            assert anchor in content, f"Missing anchor: {anchor}"

    def test_daily_template_created(self, vault):
        path = vault / "01-Templates/Enhanced Daily Template.md"
        setup.ensure_file(path, setup.DAILY_TEMPLATE_CONTENT)
        assert path.exists()
        content = path.read_text()
        assert "tp.date.now" in content
        assert "### Priority 1" in content
        assert "### Priority 2" in content
        assert "### Priority 3" in content

    def test_claude_md_created(self, vault):
        path = vault / "CLAUDE.md"
        setup.ensure_file(path, setup.CLAUDE_MD_CONTENT)
        assert path.exists()

    def test_seed_file_not_overwritten(self, vault, capsys):
        path = vault / "08-Queue/Priority-Queue.md"
        path.parent.mkdir(parents=True)
        path.write_text("existing content")
        setup.ensure_file(path, setup.PRIORITY_QUEUE_CONTENT)
        assert path.read_text() == "existing content"
        assert "exists" in capsys.readouterr().out

    def test_seed_file_creates_parent_dirs(self, vault):
        path = vault / "deep/nested/file.md"
        setup.ensure_file(path, "content")
        assert path.exists()


# ---------------------------------------------------------------------------
# setup.py — .env append logic
# ---------------------------------------------------------------------------

class TestEnvAppend:
    def test_appends_vault_path_when_missing(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("OBSIDIAN_API_KEY=abc\n")
        setup.append_vault_path_to_env(Path("/my/vault"), env_file)
        assert "VAULT_PATH=/my/vault" in env_file.read_text()

    def test_does_not_append_if_already_present(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("VAULT_PATH=/existing\n")
        setup.append_vault_path_to_env(Path("/my/vault"), env_file)
        assert env_file.read_text().count("VAULT_PATH") == 1

    def test_warns_if_env_missing(self, tmp_path, capsys):
        setup.append_vault_path_to_env(Path("/my/vault"), tmp_path / ".env")
        assert "skipping" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# setup.py — MCP config JSON builder
# ---------------------------------------------------------------------------

class TestBuildMcpConfig:
    def test_contains_server_path(self):
        server_dir = Path("/some/path/obsidian-server")
        output = setup.build_mcp_config(server_dir)
        assert str(server_dir) in output
        assert "server.py" in output

    def test_valid_json_block(self):
        import json
        server_dir = Path("/some/path/obsidian-server")
        output = setup.build_mcp_config(server_dir)
        # Strip the comment header line before parsing
        json_part = "\n".join(
            line for line in output.splitlines() if not line.startswith("#")
        )
        parsed = json.loads(json_part)
        assert "mcpServers" in parsed
        assert "obsidian-daily-notes" in parsed["mcpServers"]

    def test_uv_command(self):
        output = setup.build_mcp_config(Path("/x"))
        assert '"uv"' in output
        assert '"--project"' in output


# ---------------------------------------------------------------------------
# notes.py — Templater expression rendering
# ---------------------------------------------------------------------------

@pytest.fixture()
def daily_note():
    """Return a DailyNote instance with fully stubbed config and vault modules."""
    fake_config = types.ModuleType("config")
    fake_config.PRIORITY_EMOJI = {1: "🔺", 2: "⏫", 3: "🔼"}
    fake_config.VALID_SECTIONS = {"ideas": "### Ideas", "links": "### Links"}
    fake_config.log = MagicMock()
    fake_config.PLANNING_ROOT = ""
    fake_config.OBSIDIAN_URL = "https://127.0.0.1:27124/"
    fake_config.API_KEY = "test-key"
    fake_config.DAILY_NOTES_FOLDER = "05-Daily-Notes"
    fake_config.CALENDAR_FOLDER = "06-Calendar-Events"
    fake_config.KNOWLEDGE_FOLDER = "10-Knowledge"

    fake_vault_mod = types.ModuleType("vault")
    fake_vault_mod.VaultClient = MagicMock

    with patch.dict(sys.modules, {"config": fake_config, "vault": fake_vault_mod}):
        import notes as _notes
        importlib.reload(_notes)
        mock_vault = MagicMock()
        mock_vault.get_file.return_value = ""  # no template file → fallback
        dn = _notes.DailyNote(mock_vault)
        return dn, _notes


class TestTemplaterRendering:
    def test_renders_date(self, daily_note):
        dn, mod = daily_note
        result = mod.DailyNote.__dict__["_render_templater"](
            dn,
            '<% tp.date.now("YYYY-MM-DD") %>',
            "2026-05-28",
        )
        assert result == "2026-05-28"

    def test_renders_date_with_positive_offset(self, daily_note):
        dn, mod = daily_note
        result = mod.DailyNote.__dict__["_render_templater"](
            dn,
            '<% tp.date.now("YYYY-MM-DD", 1) %>',
            "2026-05-28",
        )
        assert result == "2026-05-29"

    def test_renders_date_with_negative_offset(self, daily_note):
        dn, mod = daily_note
        result = mod.DailyNote.__dict__["_render_templater"](
            dn,
            '<% tp.date.now("YYYY-MM-DD", -1) %>',
            "2026-05-28",
        )
        assert result == "2026-05-27"

    def test_renders_week_id(self, daily_note):
        dn, mod = daily_note
        result = mod.DailyNote.__dict__["_render_templater"](
            dn,
            '<% tp.date.now("GGGG-[W]WW") %>',
            "2026-05-28",
        )
        assert re.match(r"\d{4}-W\d{2}", result)

    def test_renders_month_id(self, daily_note):
        dn, mod = daily_note
        result = mod.DailyNote.__dict__["_render_templater"](
            dn,
            '<% tp.date.now("YYYY-MM") %>',
            "2026-05-28",
        )
        assert result == "2026-05"

    def test_renders_long_date(self, daily_note):
        dn, mod = daily_note
        result = mod.DailyNote.__dict__["_render_templater"](
            dn,
            '<% tp.date.now("dddd, MMMM Do, YYYY") %>',
            "2026-05-28",
        )
        assert "Thursday" in result
        assert "May" in result
        assert "2026" in result
        assert "28th" in result

    def test_full_template_no_remaining_placeholders(self, daily_note):
        dn, mod = daily_note
        result = mod.DailyNote.__dict__["_render_templater"](
            dn,
            setup.DAILY_TEMPLATE_CONTENT,
            "2026-05-28",
        )
        assert "<%" not in result
        assert "%>" not in result

    def test_full_template_contains_correct_date(self, daily_note):
        dn, mod = daily_note
        result = mod.DailyNote.__dict__["_render_templater"](
            dn,
            setup.DAILY_TEMPLATE_CONTENT,
            "2026-05-28",
        )
        assert "2026-05-28" in result
        assert "2026-05-29" in result  # tomorrow
        assert "2026-05-27" in result  # yesterday


# ---------------------------------------------------------------------------
# notes.py — ordinal suffix helper
# ---------------------------------------------------------------------------

class TestOrdinalSuffix:
    @pytest.fixture()
    def dn(self, daily_note):
        return daily_note[0]

    @pytest.mark.parametrize("n,expected", [
        (1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"),
        (11, "11th"), (12, "12th"), (13, "13th"),
        (21, "21st"), (22, "22nd"), (23, "23rd"), (31, "31st"),
    ])
    def test_ordinal(self, dn, n, expected):
        assert dn.ordinal_suffix(n) == expected
