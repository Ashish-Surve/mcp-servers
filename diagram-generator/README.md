# Diagram Generator MCP Server

A Model Context Protocol (MCP) server that automatically generates UML class diagrams and component architecture diagrams from Python codebases using tree-sitter and Graphviz.

## Features

- **UML Class Diagrams**: Automatically extract classes, methods, attributes, inheritance relationships, and enums
- **Component Diagrams**: Visualize module structure and dependencies
- **Tree-sitter Parsing**: Fast, reliable code analysis without executing code
- **Auto-organized Output**: Creates `arch/diagrams/` directory with both `.dot` and `.png` files
- **MCP Integration**: Works seamlessly with Claude Desktop and other MCP clients

## Installation

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Graphviz system library (for rendering diagrams)

Install Graphviz:

```bash
# macOS
brew install graphviz

# Ubuntu/Debian
sudo apt-get install graphviz

# Windows (via chocolatey)
choco install graphviz
```

### Install the MCP Server

```bash
cd /Users/devwork/Developer/Project/mcp-servers/diagram-generator
uv pip install -e .
```

## Configuration

### Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "diagram-generator": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/devwork/Developer/Project/mcp-servers/diagram-generator",
        "run",
        "diagram-generator"
      ]
    }
  }
}
```

Restart Claude Desktop after adding the configuration.

## Usage

### Available Tools

#### 1. `generate_uml_diagram`

Generates a UML class diagram from your Python codebase.

**Parameters**:
- `path` (string): Absolute path to the directory or file to analyze

**Example**:
```
Generate a UML diagram for /path/to/my/project
```

**Output**:
- `arch/diagrams/class_diagram.dot` - Graphviz source
- `arch/diagrams/class_diagram.png` - Rendered image

**Extracts**:
- Class names and structure
- Attributes (from `__init__` and class-level)
- Methods (with signatures)
- Inheritance relationships
- Enum types and values
- Relationships between classes

#### 2. `generate_component_diagram`

Generates a high-level component/architecture diagram.

**Parameters**:
- `path` (string): Absolute path to the directory to analyze

**Example**:
```
Generate a component diagram for /path/to/my/project
```

**Output**:
- `arch/diagrams/component_diagram.dot` - Graphviz source
- `arch/diagrams/component_diagram.png` - Rendered image

**Shows**:
- Module organization
- Component grouping by package
- Import dependencies
- Architecture layers

## Example Workflow

1. Open Claude Desktop
2. Ensure the diagram-generator server is configured
3. Ask Claude:
   ```
   Generate UML and component diagrams for my project at /Users/me/myproject/src
   ```
4. Claude will use the MCP tools to analyze your code
5. Find the generated diagrams in `arch/diagrams/`

## Output Structure

After running the tools, you'll have:

```
your-project/
├── arch/
│   └── diagrams/
│       ├── class_diagram.dot          # UML class diagram source
│       ├── class_diagram.png          # UML class diagram image
│       ├── component_diagram.dot      # Component diagram source
│       └── component_diagram.png      # Component diagram image
└── (your source code)
```

## Technical Details

### Architecture

- **Tree-sitter**: Parses Python code into AST for accurate extraction
- **Graphviz**: Generates professional diagrams with automatic layout
- **FastMCP**: Minimal boilerplate for MCP server implementation

### Components

- `analyzer.py`: Code analysis using tree-sitter
- `diagram_builder.py`: Graphviz diagram generation
- `server.py`: MCP server tools

### Supported Python Features

- Classes and inheritance
- Methods (including `__init__`)
- Attributes (instance and class-level)
- Enums (from `enum.Enum`)
- Type annotations (partial)
- Module imports

### Limitations

- Python-only (JavaScript, TypeScript, Java support can be added later)
- Type annotations are partially extracted
- Complex generics may not be fully represented
- Only analyzes `.py` files

## Development

### Running Tests

Create a test Python file:

```python
# test_example.py
from enum import Enum

class Priority(Enum):
    HIGH = 1
    LOW = 2

class Task:
    def __init__(self, title: str, priority: Priority):
        self.title = title
        self.priority = priority

    def complete(self):
        pass
```

Generate diagrams:

```bash
cd /path/to/test/directory
uv run diagram-generator
# Then call the tools via MCP
```

### Project Structure

```
diagram-generator/
├── pyproject.toml
├── README.md
├── .gitignore
└── src/
    └── diagram_server/
        ├── __init__.py
        ├── server.py           # MCP server entry point
        ├── analyzer.py         # Tree-sitter code analysis
        └── diagram_builder.py  # Graphviz diagram generation
```

## Troubleshooting

### "Graphviz executable not found"

Install Graphviz system package (see Prerequisites).

### "No classes found"

Ensure the path contains `.py` files with class definitions. Check that the path is absolute.

### "Permission denied"

Ensure you have read permissions for the target directory and write permissions for the current working directory.

### Diagrams not appearing in Claude Desktop

1. Check that the MCP server is configured correctly
2. Restart Claude Desktop
3. Verify the path is absolute (not relative)

## Future Enhancements

- Support for JavaScript/TypeScript
- ER diagram generation for database schemas
- Sequence diagrams
- Customizable styling and colors
- Filtering options (e.g., only public methods)
- Interactive HTML output

## License

MIT

## Contributing

Contributions welcome! Please submit issues or pull requests.

## Credits

Built with:
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/)
- [tree-sitter](https://tree-sitter.github.io/tree-sitter/)
- [Graphviz](https://graphviz.org/)
- [FastMCP](https://github.com/jlowin/fastmcp)
