"""Entry point for frozen (PyInstaller) builds and ``python -m privy_cli``."""

from __future__ import annotations

import sys


def main() -> None:
    import multiprocessing
    multiprocessing.freeze_support()

    # PyInstaller's bootloader may leak CPython flags (e.g. -B) into sys.argv.
    # Strip them so they don't confuse Typer / argument counting.
    if getattr(sys, "frozen", False):
        _PY_FLAGS = {"-B", "-b", "-bb", "-E", "-I", "-O", "-OO", "-q", "-R", "-s", "-S", "-u", "-v", "-x"}
        sys.argv = [a for a in sys.argv if a not in _PY_FLAGS]

    # When launched as a .app bundle (double-click), sys.argv has only the
    # binary path.  Detect this and launch the GUI directly.
    if getattr(sys, "frozen", False) and len(sys.argv) == 1:
        from privy_cli.gui import launch_gui

        launch_gui()
    else:
        from privy_cli.cli import app

        app()


if __name__ == "__main__":
    main()
