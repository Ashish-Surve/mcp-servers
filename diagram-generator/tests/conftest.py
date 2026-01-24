"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def test_example_file(fixtures_dir) -> Path:
    """Return the path to the test_example.py fixture."""
    return fixtures_dir / "test_example.py"
