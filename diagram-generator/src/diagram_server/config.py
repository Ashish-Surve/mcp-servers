"""Configuration and constants for diagram generator."""

from pathlib import Path

# Version
__version__ = "0.1.0"

# Directory exclusions for code analysis
SKIP_DIRS = {
    '.venv', 'venv', 'env', '.env',
    'node_modules',
    '__pycache__',
    '.git',
    '.pytest_cache', '.mypy_cache', '.tox',
    'build', 'dist', '.eggs',
    '.cache', '.ruff_cache',
    '.continue', '.claude', '.streamlit'
}

# Common base classes to skip in diagrams (reduce clutter)
SKIP_BASE_CLASSES = {'object', 'Enum'}

# Diagram output settings
DEFAULT_OUTPUT_DIR = Path("arch") / "diagrams"
DOT_FORMAT = "dot"
PNG_FORMAT = "png"

# Diagram layout options
LAYOUT_HORIZONTAL = "LR"  # Left to right
LAYOUT_VERTICAL = "TB"    # Top to bottom

# Diagram styling
DIAGRAM_STYLES = {
    'class': {
        'fillcolor': '#FEFECE',
        'shape': 'record',
        'style': 'filled',
    },
    'enum': {
        'fillcolor': '#DDFFDD',
        'shape': 'record',
        'style': 'filled',
    },
    'external': {
        'fillcolor': '#F0F0F0',
        'shape': 'record',
        'style': 'filled,dashed',
        'fontname': 'Helvetica-Oblique',
    },
    'module_cluster': {
        'style': 'rounded',
        'color': 'blue',
        'bgcolor': '#F8F8FF',
    },
    'enum_cluster': {
        'style': 'dashed',
        'color': 'green',
    },
    'component_cluster': {
        'style': 'filled',
        'fillcolor': '#E6F3FF',
    }
}

# Graph attributes
GRAPH_ATTRS = {
    'class_diagram': {
        'splines': 'ortho',
        'nodesep': '0.8',
        'ranksep': '1.5',
        'concentrate': 'true',
        'newrank': 'true',
    },
    'component_diagram': {
        'splines': 'spline',
        'nodesep': '0.8',
        'ranksep': '1.2',
    }
}

# Font settings
FONT_NAME = 'Helvetica'
FONT_SIZE_NODE = '10'
FONT_SIZE_EDGE = '9'
FONT_SIZE_TITLE = '16'
FONT_NAME_BOLD = 'Helvetica-Bold'

# Limits
MAX_METHODS_DISPLAY = 10  # Maximum methods to show per class

# Logging
LOG_FORMAT = "%(levelname)s: %(message)s"
LOG_LEVEL = "INFO"
