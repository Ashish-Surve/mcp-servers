# Developer Guide

## Quick Reference for Working with the Refactored Codebase

### Project Structure

```
diagram_server/
├── config.py              # Edit constants and settings here
├── exceptions.py          # Add new exception types here
├── core/                  # Business logic
│   ├── models.py          # Add new data models here
│   ├── analyzer.py        # Code analysis logic
│   └── builder.py         # Diagram building logic
├── server/                # MCP interface
│   ├── app.py             # Add new MCP tools/prompts here
│   └── tools.py           # Tool implementation logic
└── utils/                 # Utilities
    ├── logging.py         # Logging configuration
    └── paths.py           # Path utilities
```

## Common Tasks

### Adding a New Configuration Setting

**File:** `config.py`

```python
# Add your constant at the top level
NEW_SETTING = "value"

# Or add to an existing dictionary
DIAGRAM_STYLES['new_type'] = {
    'fillcolor': '#ABCDEF',
}
```

### Adding a New Exception Type

**File:** `exceptions.py`

```python
class MyNewError(DiagramGeneratorError):
    """Raised when something specific happens."""
    pass
```

**Usage:**
```python
from diagram_server.exceptions import MyNewError

raise MyNewError("Something went wrong")
```

### Adding a New Data Model

**File:** `core/models.py`

```python
from dataclasses import dataclass, field

@dataclass
class MyNewModel:
    """Description of the model."""
    name: str
    items: list[str] = field(default_factory=list)
```

### Adding Analysis Functionality

**File:** `core/analyzer.py`

Add methods to the `CodeAnalyzer` class:

```python
class CodeAnalyzer:
    def my_new_analysis_method(self, source: str) -> Result:
        """Analyze something new."""
        # Implementation
        return result
```

### Adding Diagram Building Features

**File:** `core/builder.py`

Add methods to the `DiagramBuilder` class:

```python
class DiagramBuilder:
    def build_new_diagram_type(self, analysis: CodebaseAnalysis) -> Digraph:
        """Build a new type of diagram."""
        dot = Digraph("New_Diagram")
        # Build logic using DIAGRAM_STYLES from config
        return dot
```

### Adding a New MCP Tool

**Step 1:** Add implementation in `server/tools.py`

```python
class DiagramTools:
    def my_new_tool(self, param: str) -> str:
        """Implementation of new tool."""
        try:
            # Use self.analyzer and self.builder
            result = self.analyzer.analyze_directory(param)
            # Process result
            return "Success!"
        except Exception as e:
            logger.error(f"Error: {e}")
            return f"Failed: {e}"
```

**Step 2:** Add MCP decorator in `server/app.py`

```python
@mcp.tool()
def my_new_tool(param: str) -> str:
    """Tool description for MCP.

    Args:
        param: Parameter description

    Returns:
        Result description
    """
    return tools.my_new_tool(param)
```

### Adding a Utility Function

**File:** `utils/paths.py` or create new utility module

```python
def my_utility_function(arg: str) -> str:
    """Utility description."""
    # Implementation
    return result
```

Don't forget to export in `utils/__init__.py`:

```python
from .paths import my_utility_function

__all__ = [..., "my_utility_function"]
```

## Running and Testing

### Run the Server

```bash
# Via entry point
uv run diagram-generator

# Via module
uv run python -m diagram_server

# Direct
uv run python src/diagram_server/server/app.py
```

### Run Tests

```bash
# All tests
uv run pytest tests/

# Specific test file
uv run pytest tests/test_analyzer.py

# Specific test
uv run pytest tests/test_analyzer.py::TestCodeAnalyzer::test_analyze_file

# With coverage
uv run pytest --cov=diagram_server tests/

# Verbose
uv run pytest -v tests/
```

### Manual Testing

```python
# In a Python REPL
uv run python

>>> from diagram_server import CodeAnalyzer, DiagramBuilder
>>> analyzer = CodeAnalyzer()
>>> builder = DiagramBuilder()
>>>
>>> # Test analysis
>>> result = analyzer.analyze_directory("tests/fixtures", exclude_tests=False)
>>> print(f"Found {len(result.all_classes)} classes")
>>>
>>> # Test building
>>> diagram = builder.build_class_diagram(result)
>>> print(diagram.source)
```

## Import Guidelines

### Recommended Imports

```python
# Top-level package exports (preferred)
from diagram_server import CodeAnalyzer, DiagramBuilder, main
from diagram_server.exceptions import InvalidPathError

# Module-specific imports
from diagram_server.core.models import ClassInfo, FileAnalysis
from diagram_server.config import SKIP_DIRS, DIAGRAM_STYLES
from diagram_server.utils import get_logger, get_module_name
```

### Internal Imports (within package)

```python
# In core/analyzer.py
from ..config import SKIP_DIRS
from ..exceptions import AnalysisError
from ..utils.logging import get_logger
from .models import ClassInfo, FileAnalysis

# In server/tools.py
from ..core import CodeAnalyzer, DiagramBuilder
from ..exceptions import NoClassesFoundError
from ..utils.paths import resolve_project_path
```

## Code Style Guidelines

### Type Hints

Always use type hints:

```python
def my_function(path: str, count: int = 10) -> list[str]:
    """Function with type hints."""
    results: list[str] = []
    return results
```

### Docstrings

Use Google-style docstrings:

```python
def my_function(param1: str, param2: int) -> bool:
    """Brief description.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When something is invalid
    """
    pass
```

### Error Handling

Use specific exceptions:

```python
from diagram_server.exceptions import InvalidPathError

try:
    result = process(path)
except FileNotFoundError as e:
    raise InvalidPathError(f"Path not found: {path}") from e
```

### Logging

Use the centralized logger:

```python
from diagram_server.utils import get_logger

logger = get_logger(__name__)

logger.info("Starting process")
logger.warning("This might be an issue")
logger.error("Something failed", exc_info=True)
```

## Configuration Access

Access configuration values from `config.py`:

```python
from diagram_server.config import (
    SKIP_DIRS,
    DIAGRAM_STYLES,
    DEFAULT_OUTPUT_DIR,
    MAX_METHODS_DISPLAY,
)

# Use them
if dir_name in SKIP_DIRS:
    continue

node_style = DIAGRAM_STYLES['class']
output_path = project_root / DEFAULT_OUTPUT_DIR
```

## Testing Guidelines

### Test File Organization

- `test_analyzer.py` - Tests for analyzer module
- `test_builder.py` - Tests for builder module
- `test_integration.py` - End-to-end tests
- `conftest.py` - Shared fixtures

### Writing Tests

```python
import pytest
from diagram_server.core import CodeAnalyzer

class TestMyFeature:
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for tests."""
        return CodeAnalyzer()

    def test_specific_behavior(self, analyzer, test_example_file):
        """Test description."""
        # Arrange
        expected = 5

        # Act
        result = analyzer.analyze_python_file(str(test_example_file))

        # Assert
        assert len(result.classes) == expected
```

## Debugging Tips

### Enable Debug Logging

```python
# In your code
from diagram_server.utils import setup_logging

setup_logging(level="DEBUG")
```

### Inspect Data Models

```python
from dataclasses import asdict
from diagram_server.core.models import ClassInfo

class_info = ClassInfo(name="MyClass")
print(asdict(class_info))  # See all fields
```

### Check Generated Diagrams

```python
# Save DOT source for inspection
diagram = builder.build_class_diagram(analysis)
print(diagram.source)  # See generated DOT code

# Manually render
diagram.render('/tmp/debug', format='png')
```

## Common Patterns

### Working with Paths

```python
from pathlib import Path
from diagram_server.utils.paths import resolve_project_path, get_project_root

# Resolve and validate path
path = resolve_project_path(user_input)  # Raises InvalidPathError if bad

# Get project root
root = get_project_root(path)

# Build output path
output_dir = root / "arch" / "diagrams"
output_dir.mkdir(parents=True, exist_ok=True)
```

### Analyzing Code

```python
from diagram_server.core import CodeAnalyzer

analyzer = CodeAnalyzer()

# Analyze directory (excludes tests by default)
analysis = analyzer.analyze_directory("/path/to/project")

# Include everything
analysis = analyzer.analyze_directory("/path/to/project", exclude_tests=False)

# Analyze single file
file_analysis = analyzer.analyze_python_file("/path/to/file.py")

# Access results
for class_name, class_info in analysis.all_classes.items():
    print(f"{class_name}: {len(class_info.methods)} methods")
```

### Building Diagrams

```python
from pathlib import Path
from diagram_server.core import DiagramBuilder

builder = DiagramBuilder()

# Build class diagram
diagram = builder.build_class_diagram(analysis, layout="LR")

# Build component diagram
diagram = builder.build_component_diagram(analysis)

# Render and save
output_dir = Path("/tmp/diagrams")
dot_path, png_path = builder.render_and_save(diagram, output_dir, "my_diagram")
```

## Package Distribution

### Building

```bash
uv build
```

### Installing Locally

```bash
uv pip install -e .
```

### Running Installed Package

```bash
diagram-generator  # Entry point script
python -m diagram_server  # Module execution
```

---

**Note:** Always run tests after making changes: `uv run pytest tests/`
