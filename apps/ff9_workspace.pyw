#!/usr/bin/env pythonw
"""Double-click launcher for the Dream World IX **Workspace** -- the modern PySide6 shell.

A single dockable window whose left rail is the journey > campaign > field > object hierarchy, with a
clickable breadcrumb, a central document area, a right inspector, and a bottom Output/Problems dock. It
reuses the same backend as the tkinter apps; this is the genuinely-modern replacement, shipped alongside
them. Needs PySide6 (`py -m pip install PySide6`).

Or run:  py -m ff9mapkit.workspace.shell
"""
from __future__ import annotations

import sys
from pathlib import Path

# THIS worktree's kit package must shadow any editable install (another worktree may lack `workspace`),
# so insert it BEFORE the first ff9mapkit import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ff9mapkit"))

from ff9mapkit.workspace.shell import main  # noqa: E402

if __name__ == "__main__":
    main()
