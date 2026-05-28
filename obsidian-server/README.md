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

### 3. Configure your environment

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
OBSIDIAN_API_KEY=paste-your-api-key-here
OBSIDIAN_URL=https://127.0.0.1:27124/

# Paths are relative to your vault root
VAULT_FOLDER=05-Daily-Notes
CALENDAR_FOLDER=06-Calendar-Events
PLANNING_ROOT=
```

> **PLANNING_ROOT** — leave empty if your numbered folders (`02-Long-Term-Goals`,
> `03-Monthly`, `04-Weekly`, etc.) are at the vault root. Set it if they live
> inside a subfolder, e.g. `PLANNING_ROOT=Planning System`.

---

### 4. Set up the vault structure

Your vault needs these folders. Create them in Obsidian or via your file system:

```
your-vault/
├── 02-Long-Term-Goals/
│   └── Long-Term-Goals.md
├── 03-Monthly/
├── 04-Weekly/
├── 05-Daily-Notes/
├── 06-Calendar-Events/
│   ├── DataScience/
│   ├── Guitar/
│   ├── Habits/
│   ├── Investing/
│   ├── TimeBlocks/
│   └── Work/
├── 08-Queue/
│   └── Priority-Queue.md
├── 09-Inbox/
└── 10-Knowledge/
    ├── MOCs/
    ├── AI-Engineering/
    ├── Health/
    ├── Investing/
    └── Personal/
```

**Priority-Queue.md** must contain these exact section headings:

```markdown
## 🔺 P1 — Do Soon

## ⏫ P2 — Do This Week/Next

## 🔼 P3 — Someday
```

---

### 5. Add to Claude config

Find your config file:
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Claude Code:** `~/.claude/claude_desktop_config.json`

Add this inside `"mcpServers"` — replace the path with your actual clone location:

```json
{
  "mcpServers": {
    "obsidian-daily-notes": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/full/path/to/mcp-servers/obsidian-server",
        "/full/path/to/mcp-servers/obsidian-server/server.py"
      ]
    }
  }
}
```

> **Mac example:**
> `/Users/yourname/code/mcp-servers/obsidian-server`
>
> **Windows example:**
> `C:\\Users\\yourname\\code\\mcp-servers\\obsidian-server`
> (use double backslashes in JSON)

Restart Claude. You should see the tools icon (🔨) appear.

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
| `VAULT_FOLDER` | `05-Daily-Notes` | Path to daily notes folder from vault root |
| `CALENDAR_FOLDER` | `06-Calendar-Events` | Path to calendar events folder |
| `PLANNING_ROOT` | *(empty)* | Parent folder for numbered subfolders, if any |
| `LOG_LEVEL` | `INFO` | Set to `DEBUG` for verbose output |
