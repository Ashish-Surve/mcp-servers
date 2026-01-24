"""Entry point for running diagram-generator as a module.

Usage:
    python -m diagram_server
"""

from .server.app import main

if __name__ == "__main__":
    main()
