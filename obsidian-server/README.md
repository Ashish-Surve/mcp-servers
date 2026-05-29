# Obsidian MCP Server

Connect Claude to your Obsidian vault. Claude can manage daily notes, priorities,
goals, calendar events, a task queue, inbox captures, and a knowledge base — all
through natural language.

---

## Prerequisites

- [Obsidian](https://obsidian.md) desktop app (must be running when using Claude)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- A Claude.ai account or Claude Desktop

---

## Obsidian plugins

### Required

| Plugin | Why |
|---|---|
| [Local REST API](https://obsidian.md/plugins?id=obsidian-local-rest-api) | How Claude talks to your vault — without this nothing works |

### Recommended

| Plugin | Why |
|---|---|
| [Templater](https://obsidian.md/plugins?id=templater-obsidian) | Auto-generates daily notes when you open a new day — point it at `01-Templates/Enhanced Daily Template.md` (seeded by `setup.py`). Do not modify this file; the MCP depends on its structure |
| [Dataview](https://obsidian.md/plugins?id=dataview) | Powers dashboard queries across your vault |
| [Full Calendar](https://obsidian.md/plugins?id=obsidian-full-calendar) | Visual calendar view of your `06-Calendar-Events/` time blocks |
| [Kanban](https://obsidian.md/plugins?id=obsidian-kanban) | Renders `Priority-Queue.md` as a drag-and-drop board |
| [Tasks](https://obsidian.md/plugins?id=obsidian-tasks-plugin) | Track due dates and recurring tasks across all notes |

Install via **Settings → Community Plugins → Browse**, search by name, install and enable.

---

## Setup (10 minutes)

### 1. Clone the repo

```bash
git clone https://github.com/Ashish-Surve/mcp-servers.git
cd mcp-servers/obsidian-server
```

---

### 2. Enable the Obsidian Local REST API plugin

1. Open Obsidian → **Settings → Community Plugins → Browse**
2. Search **"Local REST API"** → Install → Enable
3. Open the plugin settings → copy your **API Key**
4. Leave the port as default (**27124**) unless you have a conflict

---

### 3. Add your API key to `.env`

```bash
cp .env.example .env
```

Open `.env` and set your API key — that's the only value you need to fill in manually:

```env
OBSIDIAN_API_KEY=paste-your-api-key-here
```

The rest of the values have sensible defaults. Only change them if you have a reason to:

- `OBSIDIAN_URL` — change the port if you modified it in the plugin settings
- `VAULT_FOLDER`, `CALENDAR_FOLDER` — leave as-is unless you renamed those folders
- `PLANNING_ROOT` — leave empty if your numbered folders are at the vault root; set it if they live inside a subfolder, e.g. `PLANNING_ROOT=Planning System`

---

### 4. Run the setup script

```bash
uv run setup.py
```

The script will:
- Ask for your vault path and save it to `.env`
- Create all required folders in your vault
- Write `Priority-Queue.md` and `Long-Term-Goals.md` with the correct structure
- Print the exact JSON block to paste into your Claude config

> Safe to re-run — never overwrites existing files.

---

### 5. Add the printed JSON to your Claude config

The setup script prints the exact block to paste — copy it and add it to your Claude config file:

- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Claude Code:** `~/.claude/claude_desktop_config.json`

Then restart Claude. You should see the tools icon (🔨) appear.

---

### 6. Add the Alfred system prompt (optional but recommended)

For the full Alfred personal assistant experience, create a **Claude Project** and
paste the contents of `alfred-prompt.md` into the Project Instructions field.

Without this, Claude will still have access to all the tools but won't know how
to use them intelligently as a personal assistant.

---

## Test it works

Ask Claude:
> "What are my priorities today?"

If Obsidian is open and the plugin is running, Claude will read (or create) today's
daily note and respond.

---

## What Claude can do

| Say to Claude | What happens |
|---|---|
| "What are my priorities today?" | Reads today's daily note |
| "Add review NL2SQL as priority 1" | Sets priority slot 1 |
| "Mark priority 2 done" | Checks it off with a timestamp |
| "Add to queue: research ELSS funds" | Appends to P3 backlog |
| "Show my queue" | Lists all pending tasks |
| "Capture this idea: [text]" | Saves to 09-Inbox/ |
| "Show my goals" | Reads goal hierarchy |
| "Plan tomorrow" | Fills tomorrow prep section |
| "Create an event: Gym 7-8am Habits" | Creates calendar event |
| "Weekly review" | Summarises this week's notes |

---

## Token footprint

This server exposes **28 tools**. The total schema injected into every Claude conversation is approximately **~1,350 tokens** — well under 1% of Claude's 200K context window. Tool schemas are kept deliberately lean; docstrings carry only what Claude needs to call each tool correctly.

---

## Vault folder reference

| Folder | Purpose |
|---|---|
| `02-Long-Term-Goals/` | Single goals file with goal codes |
| `03-Monthly/` | Monthly planning notes (`YYYY-MM.md`) |
| `04-Weekly/` | Weekly planning notes (`YYYY-WNN.md`) |
| `05-Daily-Notes/` | Daily notes (`YYYY/MM/YYYY-MM-DD.md`) |
| `06-Calendar-Events/` | Time-blocked events by category |
| `08-Queue/` | Task backlog (`Priority-Queue.md`) |
| `09-Inbox/` | Raw captures pending processing |
| `10-Knowledge/` | Processed notes + Maps of Content |

---

## Working with MOCs (Maps of Content)

MOCs are theme hubs that group related knowledge notes together. You create them as you go — there are no presets.

**Create a new MOC:**
> "Create a MOC for cooking"

**Save a note to an existing MOC:**
> "Save this as a knowledge note about sourdough, link it to my Cooking MOC"

Before linking a note to a MOC, Claude calls `moc_list` to see what MOCs actually exist in your vault — this prevents hallucinated or duplicate MOC names. If the MOC you want doesn't exist yet, Claude will create it first then link the note.

Your MOCs live in `10-Knowledge/MOCs/` and grow organically as your knowledge base does.

---

## Available tags

`datascience` · `investing` · `guitar` · `habits` · `health` · `prep` · `learning` · `personal`

## Calendar categories

`TimeBlocks` · `DataScience` · `Investing` · `Guitar` · `Habits` · `Work`

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `OBSIDIAN_API_KEY is not set` | Check your `.env` file exists and has the key |
| `Connection refused` | Obsidian is not running, or Local REST API plugin is disabled |
| `SSL error` | Already handled in server — check your port matches the plugin settings |
| Tools icon not showing in Claude | Restart Claude after editing the config file |
| `uv: command not found` | Install uv: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Priority slot error | Daily note template placeholders may not match — run `vault_read` on today's note to inspect |
| Wrong folder structure | Check `PLANNING_ROOT` in `.env` — set it if your folders aren't at vault root |

---

## Environment variables reference

| Variable | Default | Description |
|---|---|---|
| `OBSIDIAN_API_KEY` | *(required)* | From Local REST API plugin settings |
| `OBSIDIAN_URL` | `https://127.0.0.1:27124/` | Change port if you modified it in plugin settings |
| `VAULT_PATH` | *(prompted)* | Absolute path to your Obsidian vault root |
| `VAULT_FOLDER` | `05-Daily-Notes` | Path to daily notes folder from vault root |
| `CALENDAR_FOLDER` | `06-Calendar-Events` | Path to calendar events folder |
| `PLANNING_ROOT` | *(empty)* | Parent folder for numbered subfolders, if any |
| `LOG_LEVEL` | `INFO` | Set to `DEBUG` for verbose output |
