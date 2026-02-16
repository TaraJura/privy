"""Entry point for frozen (PyInstaller) builds and ``python -m privy_cli``."""

from __future__ import annotations

from privy_cli.cli import app

if __name__ == "__main__":
    app()
