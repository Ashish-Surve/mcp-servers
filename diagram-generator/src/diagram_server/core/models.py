"""Data models for code analysis and diagram generation."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ClassInfo:
    """Information about a Python class.

    Attributes:
        name: The class name
        base_classes: List of base class names
        attributes: List of class/instance attributes
        methods: List of method signatures
        is_enum: Whether this is an Enum class
        enum_values: List of enum values (if is_enum is True)
        docstring: The class docstring
        file_path: Absolute path to the file containing this class
    """
    name: str
    base_classes: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    is_enum: bool = False
    enum_values: list[str] = field(default_factory=list)
    docstring: Optional[str] = None
    file_path: str = ""


@dataclass
class ImportInfo:
    """Information about imports in a file.

    Attributes:
        module: The module being imported
        names: Specific names imported (for 'from' imports)
        is_from_import: Whether this is a 'from module import name' statement
    """
    module: str
    names: list[str] = field(default_factory=list)
    is_from_import: bool = False


@dataclass
class FileAnalysis:
    """Analysis results for a single Python file.

    Attributes:
        file_path: Absolute path to the analyzed file
        classes: List of classes found in this file
        imports: List of imports found in this file
        module_name: Python module name (e.g., 'package.submodule.file')
    """
    file_path: str
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    module_name: str = ""


@dataclass
class CodebaseAnalysis:
    """Analysis results for an entire codebase.

    Attributes:
        files: List of analyzed files
        all_classes: Dictionary mapping class names to ClassInfo objects
        module_dependencies: Dictionary mapping module names to their dependencies
    """
    files: list[FileAnalysis] = field(default_factory=list)
    all_classes: dict[str, ClassInfo] = field(default_factory=dict)
    module_dependencies: dict[str, set[str]] = field(default_factory=dict)
