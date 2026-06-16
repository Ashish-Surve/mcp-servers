"""
Root conftest.py — ensures the project root is on sys.path so tests under
tests/ can do `from notes import DailyNote`, `from config import ...`, etc.
without the project being installed as a package.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
