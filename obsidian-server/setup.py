"""Vault scaffold script for the Alfred MCP server."""

import os
import platform
import sys
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FOLDERS = [
    "01-Templates",
    "02-Long-Term-Goals",
    "03-Monthly",
    "04-Weekly",
    "05-Daily-Notes",
    "06-Calendar-Events/DataScience",
    "06-Calendar-Events/Guitar",
    "06-Calendar-Events/Habits",
    "06-Calendar-Events/Investing",
    "06-Calendar-Events/TimeBlocks",
    "06-Calendar-Events/Work",
    "07-Dashboard",
    "08-Queue",
    "09-Inbox",
    "10-Knowledge/MOCs",
    "10-Knowledge/AI-Engineering",
    "10-Knowledge/Data-Science",
    "10-Knowledge/Health",
    "10-Knowledge/Investing",
    "10-Knowledge/Guitar",
    "10-Knowledge/Personal",
    "10-Knowledge/References",
    "11-Chores",
]

PRIORITY_QUEUE_CONTENT = """\
# 🗂️ Priority Queue

## 🔺 P1 — Do Soon

## ⏫ P2 — Do This Week/Next

## 🔼 P3 — Someday

## ✅ Archive

**Complete**

%% kanban:settings
```
{"kanban-plugin":"board","list-collapse":[false]}
```
%%
"""

LONG_TERM_GOALS_CONTENT = """\
# Long-Term Goals

## Health ^H
-

## DataScience ^DS
-

## Investing ^INV
-

## Guitar ^G
-

## Personal ^P
-
"""

DAILY_TEMPLATE_CONTENT = """\
# 📝 <% tp.date.now("YYYY-MM-DD") %>

_<% tp.date.now("dddd, MMMM Do, YYYY") %>_

**This week:** [[<% tp.date.now("GGGG-[W]WW") %>]] | **This month:** [[<% tp.date.now("YYYY-MM") %>]] | **Vision:** [[Long-Term-Goals]]

> *What are the 1-3 most important things I'm blessed to do today?*

---

## 🔥 Priorities

### Priority 1

- [ ] #todo **Task:** 📅 <% tp.date.now("YYYY-MM-DD") %> 🔺 #{{tag}}
- **Feeds:**
- **Why it matters:**
- **Time estimate:**
- **Time block:**

### Priority 2

- [ ] #todo **Task:** 📅 <% tp.date.now("YYYY-MM-DD") %> ⏫ #{{tag}}
- **Feeds:**
- **Why it matters:**
- **Time estimate:**
- **Time block:**

### Priority 3

- [ ] #todo **Task:** 📅 <% tp.date.now("YYYY-MM-DD") %> 🔼 #{{tag}}
- **Feeds:**
- **Why it matters:**
- **Time estimate:**
- **Time block:**

---

## 🔄 Habits

> *Check off in the evening — honest log only.*

- [ ] #todo Morning routine 📅 <% tp.date.now("YYYY-MM-DD") %> 🔄 every day #habits
- [ ] #todo Proper nutrition & hydration 📅 <% tp.date.now("YYYY-MM-DD") %> 🔄 every day #habits
- [ ] #todo Evening reflection 📅 <% tp.date.now("YYYY-MM-DD") %> 🔄 every day #habits

---

## 📝 Notes

### Ideas

### Links

---

## 🔄 Tomorrow's Prep

1. [ ] #todo 📅 <% tp.date.now("YYYY-MM-DD", 1) %> 🔺 #{{tag}}
2. [ ] #todo 📅 <% tp.date.now("YYYY-MM-DD", 1) %> ⏫ #{{tag}}
3. [ ] #todo 📅 <% tp.date.now("YYYY-MM-DD", 1) %> 🔼 #{{tag}}

---

> *These are things I WANT to do, not things I NEED to do. Everything here is chosen.*

Yesterday: [[<% tp.date.now("YYYY-MM-DD", -1) %>]] | Tomorrow: [[<% tp.date.now("YYYY-MM-DD", 1) %>]]
"""

CLAUDE_MD_CONTENT = """\
# Vault Overview

This vault is managed by the Alfred MCP server.

Key paths:
- Daily notes:  05-Daily-Notes/YYYY/MM/YYYY-MM-DD.md
- Task queue:   08-Queue/Priority-Queue.md
- Inbox:        09-Inbox/
- Goals:        02-Long-Term-Goals/Long-Term-Goals.md
"""


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def print_header() -> None:
    print("╔══════════════════════════════════════════╗")
    print("║   Alfred Second Brain — Vault Setup      ║")
    print("╚══════════════════════════════════════════╝")
    print()


def created(path: Path) -> None:
    print(f"✓  created  {path}")


def exists(path: Path) -> None:
    print(f"↷  exists   {path}")


# ---------------------------------------------------------------------------
# Scaffold helpers
# ---------------------------------------------------------------------------

def ensure_folder(root: Path, rel: str) -> None:
    target = root / rel
    if target.exists():
        exists(target)
    else:
        target.mkdir(parents=True, exist_ok=True)
        created(target)


def ensure_file(path: Path, content: str) -> None:
    if path.exists():
        exists(path)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created(path)


# ---------------------------------------------------------------------------
# Config JSON builder
# ---------------------------------------------------------------------------

def build_mcp_config(server_dir: Path) -> str:
    system = platform.system()

    if system == "Windows":
        config_path = r"%APPDATA%\Claude\claude_desktop_config.json"
        def fmt(p: Path) -> str:
            return str(p).replace("\\", "\\\\")
    elif system == "Darwin":
        config_path = "~/Library/Application Support/Claude/claude_desktop_config.json"
        def fmt(p: Path) -> str:
            return str(p)
    else:
        config_path = "~/.claude/claude_desktop_config.json"
        def fmt(p: Path) -> str:
            return str(p)

    project_path = fmt(server_dir)
    server_py = fmt(server_dir / "server.py")

    return (
        f"# Add this to: {config_path}\n"
        "{\n"
        '  "mcpServers": {\n'
        '    "obsidian-daily-notes": {\n'
        '      "command": "uv",\n'
        '      "args": [\n'
        '        "run",\n'
        '        "--project",\n'
        f'        "{project_path}",\n'
        f'        "{server_py}"\n'
        "      ]\n"
        "    }\n"
        "  }\n"
        "}"
    )


# ---------------------------------------------------------------------------
# .env helpers
# ---------------------------------------------------------------------------

def append_vault_path_to_env(vault_path: Path, env_file: Path) -> None:
    if not env_file.exists():
        print(f"\n⚠  .env not found at {env_file} — skipping VAULT_PATH append.")
        return

    content = env_file.read_text(encoding="utf-8")
    if "VAULT_PATH" not in content:
        with env_file.open("a", encoding="utf-8") as f:
            f.write(f"\nVAULT_PATH={vault_path}\n")
        print(f"\n✓  Appended VAULT_PATH to {env_file}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print_header()

    env_file = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_file)

    vault_path_str = os.environ.get("VAULT_PATH", "").strip()
    prompted = False

    if not vault_path_str:
        prompted = True
        try:
            vault_path_str = input("Enter the absolute path to your Obsidian vault: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

    vault = Path(vault_path_str).expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)

    print(f"\nScaffolding vault at: {vault}\n")

    # Folders
    for folder in FOLDERS:
        ensure_folder(vault, folder)

    print()

    # Seed files
    ensure_file(vault / "08-Queue/Priority-Queue.md", PRIORITY_QUEUE_CONTENT)
    ensure_file(vault / "02-Long-Term-Goals/Long-Term-Goals.md", LONG_TERM_GOALS_CONTENT)
    ensure_file(vault / "01-Templates/Enhanced Daily Template.md", DAILY_TEMPLATE_CONTENT)
    ensure_file(vault / "CLAUDE.md", CLAUDE_MD_CONTENT)

    # Only append to .env if the user was prompted (not already set in env)
    if prompted:
        append_vault_path_to_env(vault, env_file)

    print("\n✅ Vault scaffolded successfully.\n")

    # MCP config JSON
    server_dir = Path(__file__).parent.resolve()
    print(build_mcp_config(server_dir))

    # Next steps
    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Next steps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Open .env and add your Obsidian API key:
       OBSIDIAN_API_KEY=paste-your-key-here

  2. Copy the JSON block above and paste it into
     your Claude config file — paths are already
     filled in, no edits needed.

  3. In Templater settings, set the template folder
     to 01-Templates/ in your vault.

  4. Restart Claude.

  5. Ask Claude: "what are my priorities today?"

  Optional: paste alfred-prompt.md into a Claude Project
  for the full Alfred personal assistant experience.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


if __name__ == "__main__":
    main()
