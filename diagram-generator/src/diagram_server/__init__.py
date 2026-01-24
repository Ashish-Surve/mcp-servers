"""MCP Diagram Generator - Generate UML and component diagrams from Python codebases."""

from .config import __version__
from .core import CodeAnalyzer, DiagramBuilder
from .exceptions import (
    AnalysisError,
    DiagramBuildError,
    DiagramGeneratorError,
    InvalidPathError,
    NoClassesFoundError,
    NoPythonFilesFoundError,
    RenderError,
)
from .server import main

__all__ = [
    "__version__",
    "main",
    "CodeAnalyzer",
    "DiagramBuilder",
    "DiagramGeneratorError",
    "AnalysisError",
    "DiagramBuildError",
    "RenderError",
    "InvalidPathError",
    "NoClassesFoundError",
    "NoPythonFilesFoundError",
]
