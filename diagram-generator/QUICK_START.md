# Quick Start Guide - Diagram Generator MCP

## TL;DR

**Fast Mode**: `"Generate a UML diagram for /path/to/project"`
**LLM Mode**: `"Analyze /path/to/project and create a diagram showing [specific aspect]"`

---

## Installation Complete ✅

Your MCP server is configured in:
- Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Claude Code CLI: `~/.claude/settings.json`
- VS Code: `~/Library/Application Support/Code/User/settings.json` (limited - use CLI instead)

---

## Quick Examples

### Fast Mode Examples

```
Generate a UML diagram for /Users/devwork/Developer/Project/resume-builder
```

```
Generate a component diagram for /Users/devwork/Developer/Project/resume-builder
```

```
Generate a UML diagram with TB layout for /Users/devwork/Developer/Project/resume-builder
```

### LLM Mode Examples

```
I want to create an intelligent diagram of my codebase
```
(Then provide path when asked)

```
Analyze the structure of /Users/devwork/Developer/Project/resume-builder
and create a diagram showing only the core business logic components
```

```
Use analyze_codebase_structure to understand /Users/devwork/Developer/Project/resume-builder,
then create a high-level architecture diagram showing the main layers
```

```
Create separate diagrams for the authentication system and data models
in /Users/devwork/Developer/Project/resume-builder
```

---

## Output Location

All diagrams are saved to:
```
<project-path>/arch/diagrams/
```

Files generated:
- `*.dot` - Graphviz source (editable)
- `*.png` - Rendered diagram (viewable)

---

## Tool Reference

| Tool | Mode | Purpose | Speed |
|------|------|---------|-------|
| `generate_uml_diagram` | Fast | Complete class diagram | 2-5s |
| `generate_component_diagram` | Fast | Module dependencies | 2-5s |
| `analyze_codebase_structure` | LLM | Extract for analysis | 2-5s |
| `render_diagram_from_dot` | LLM | Render custom diagram | 1-2s |

---

## Features Summary

### Smart Package Detection
- Reads `pyproject.toml` automatically
- Focuses on main package code
- Excludes test files
- Works with hatchling & setuptools

### Layout Options
- **LR** (default): Horizontal, left-to-right
- **TB**: Vertical, top-to-bottom

### Class Relationships
- ✅ Internal inheritance (solid lines)
- ✅ External inheritance (dashed lines to gray boxes)
- ✅ Base classes shown even if external (Exception, BaseModel, ABC, etc.)
- ✅ Module-based grouping

### Code Organization
The codebase follows professional Python structure:
- **`core/`**: Business logic (analyzer, builder, models)
- **`server/`**: MCP interface (app, tools)
- **`utils/`**: Reusable utilities (logging, paths)
- **`config.py`**: Centralized configuration
- **`exceptions.py`**: Custom error types

---

## Troubleshooting

### MCP Server Not Found
1. Restart Claude Desktop / reload Claude Code
2. Check configuration files have correct paths
3. Verify: `uv run diagram-generator` works

### VS Code Extension Hanging
- Known issue with MCP in VS Code extension
- **Solution**: Use Claude Code CLI instead
  ```bash
  cd /path/to/project
  claude
  # Then ask for diagram
  ```

### Diagram Too Large/Complex
- Use LLM mode to create focused views
- Ask for specific components only
- Request high-level architecture instead of detailed UML

---

## Next Steps

1. **Try Fast Mode**: Generate a quick UML diagram of your project
2. **Try LLM Mode**: Ask for a custom view of a specific component
3. **Explore Layouts**: Try both LR and TB layouts
4. **Custom Diagrams**: Use LLM to create sequence diagrams, flow charts, etc.

---

## Development

### Running the Server

```bash
# Entry point script
uv run diagram-generator

# Module execution
uv run python -m diagram_server
```

### Running Tests

```bash
# All tests
uv run pytest tests/

# Specific test
uv run pytest tests/test_analyzer.py

# With coverage
uv run pytest --cov=diagram_server tests/
```

### Importing in Python

```python
from diagram_server import CodeAnalyzer, DiagramBuilder
from diagram_server.exceptions import InvalidPathError
from diagram_server.core.models import ClassInfo
```

---

## Need Help?

- **Full Documentation**: [README.md](README.md)
- **Developer Guide**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- **Refactoring Details**: [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)
- Report issues: Create a GitHub issue or ask Claude!
