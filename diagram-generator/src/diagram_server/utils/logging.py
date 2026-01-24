"""Logging utilities for diagram generator."""

import logging
import sys

from ..config import LOG_FORMAT, LOG_LEVEL


def setup_logging(level: str = LOG_LEVEL) -> None:
    """Configure logging to stderr (stdout is reserved for MCP JSON-RPC).

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=LOG_FORMAT,
        stream=sys.stderr,
        force=True,  # Override any existing configuration
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
