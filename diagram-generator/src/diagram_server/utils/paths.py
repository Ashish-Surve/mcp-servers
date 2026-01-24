"""Path utilities for diagram generator."""

from pathlib import Path
from typing import Optional


def get_module_name(filepath: str) -> str:
    """Extract module name from file path.

    Converts a file path to Python module notation.
    For example: /path/to/src/package/module.py -> package.module

    Args:
        filepath: Absolute or relative path to Python file

    Returns:
        Module name in dot notation
    """
    path = Path(filepath)
    # Remove .py extension and convert to module notation
    parts = path.with_suffix("").parts

    # Find index of 'src' or use all parts
    try:
        src_idx = parts.index("src") + 1
        return ".".join(parts[src_idx:])
    except ValueError:
        return path.stem


def get_module_from_path(file_path: str) -> str:
    """Extract a clean module name from file path.

    Tries to identify the main package name from common project structures.

    Args:
        file_path: Absolute or relative path to Python file

    Returns:
        Module/package name
    """
    path = Path(file_path)
    parts = path.parts

    # Look for common package indicators
    if "src" in parts:
        idx = parts.index("src") + 1
        if idx < len(parts):
            # Get first directory after src
            return parts[idx]

    # Look for other common patterns
    for base in ["lib", "pkg"]:
        if base in parts:
            idx = parts.index(base) + 1
            if idx < len(parts):
                return parts[idx]

    # Fallback: use parent directory name
    if len(parts) > 1:
        return parts[-2]

    return "main"


def ensure_output_dir(base_path: Path, relative_path: Optional[Path] = None) -> Path:
    """Ensure output directory exists and return the path.

    Args:
        base_path: Base directory for output
        relative_path: Optional relative path to append

    Returns:
        Absolute path to output directory
    """
    if relative_path:
        output_dir = base_path / relative_path
    else:
        output_dir = base_path

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def resolve_project_path(path_str: str) -> Path:
    """Resolve a path string to an absolute Path object.

    Handles both files and directories.

    Args:
        path_str: Path string to resolve

    Returns:
        Resolved absolute Path object

    Raises:
        FileNotFoundError: If path doesn't exist
    """
    path = Path(path_str).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path_str}")
    return path


def get_project_root(path: Path) -> Path:
    """Get the project root directory from a file or directory path.

    Args:
        path: File or directory path

    Returns:
        Project root directory (parent if path is a file)
    """
    if path.is_file():
        return path.parent
    return path
