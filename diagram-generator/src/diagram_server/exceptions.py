"""Custom exceptions for diagram generator."""


class DiagramGeneratorError(Exception):
    """Base exception for diagram generator errors."""
    pass


class AnalysisError(DiagramGeneratorError):
    """Raised when code analysis fails."""
    pass


class DiagramBuildError(DiagramGeneratorError):
    """Raised when diagram building fails."""
    pass


class RenderError(DiagramGeneratorError):
    """Raised when diagram rendering fails."""
    pass


class InvalidPathError(DiagramGeneratorError):
    """Raised when provided path is invalid or inaccessible."""
    pass


class NoClassesFoundError(AnalysisError):
    """Raised when no classes are found in the analyzed code."""
    pass


class NoPythonFilesFoundError(AnalysisError):
    """Raised when no Python files are found in the directory."""
    pass
