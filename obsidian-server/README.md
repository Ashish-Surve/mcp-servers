# Obsidian Daily Note MCP Server

Connect Claude to your Obsidian daily notes.  
Claude can create notes, add tasks, set time blocks, and capture quick notes.

---

## 1. Install Dependencies

```bash
uv init obsidian-mcp
cd obsidian-mcp
uv add mcp httpx
```

---

## 2. Enable Obsidian Local REST API Plugin

1. Open Obsidian → Settings → Community Plugins → Browse
2. Search **"Local REST API"** → Install → Enable
3. Go to its settings → copy the **API Key**
4. Note the port (default: **27124**)

---

## 3. Configure the Server

Open `server.py` and update the top section:

```python
OBSIDIAN_URL = "https://localhost:27124"   # Change port if needed
API_KEY      = "paste-your-key-here"       # From Local REST API settings
VAULT_FOLDER = "Daily Notes"               # Your actual folder name in the vault
```

---

## 4. Add to Claude Code Config

Find your Claude Code config file:
- **Mac/Linux:** `~/.claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add this block inside `"mcpServers"`:

```json
{
  "mcpServers": {
    "obsidian-daily-notes": {
      "command": "uv",
      "args": ["run", "/full/path/to/server.py"]
    }
  }
}
```

Restart Claude Code. You should see the tools available.

---

## 5. What Claude Can Do

| Say to Claude | What happens |
|---|---|
| "Create today's daily note" | Creates note from template |
| "Add ML interview prep as priority 1, 2 hours, morning" | Fills Priority 1 slot |
| "Set time block for priority 2 as 2-3pm" | Updates that field |
| "Add guitar practice as a bonus task" | Adds to Part 2 |
| "Set my focus word to Deep" | Updates intentions section |
| "Add quick note to ideas: look into RAG eval frameworks" | Appends to Ideas section |
| "Add tomorrow's priority: review investments" | Fills tomorrow's prep section |
| "Read today's note" | Returns full note content |

---

## 6. Available Tags

Claude knows these tags from your template:

| Tag | Use for |
|---|---|
| `#datascience` | ML/DS projects |
| `#investing` | Investment research |
| `#guitar` | Music practice |
| `#habits` | Daily routines |
| `#health` | Exercise, nutrition |
| `#prep` | Preparation tasks |
| `#learning` | Skill development |
| `#personal` | Personal tasks |

---

## File Structure

```
obsidian-mcp/
├── server.py    ← The MCP server (only file you need)
└── README.md    ← This file
```

---

## Troubleshooting

**"Connection refused"**  
→ Make sure Obsidian is open and Local REST API plugin is enabled

**"SSL error"**  
→ The `verify=False` in server.py handles this. If still failing, check the port number.

**"Could not find this text in the note"**  
→ Your template in Obsidian may differ slightly from the one in `build_template()`.  
→ Run `read_daily_note` first to see what's in your note, then adjust placeholders in server.py.

**Note not in right folder**  
→ Update `VAULT_FOLDER` in server.py to match your actual folder name exactly.