#!/usr/bin/env pythonw
"""Dream World IX -- the front door. Opens the **Workspace**: ONE window for every tool.

Double-click this (windowless via pythonw) to launch the modern PySide6 Workspace -- a single dockable
window whose left rail is the journey > campaign > field > object hierarchy, with the field Editor, the
campaign Map, the Story State + Item & Equip save editors, Build & Deploy, and Import all as tabs, plus a
Ctrl-K command palette and a bottom Output/Problems console.

The legacy single-purpose tkinter windows (Logic Editor, Dialogue, Info Hub, Build, Import, Story State,
Item & Equip, Campaign Editor) were retired here -- everything they did now
lives inside this one Workspace, over the same tk-free backends. The Workspace needs PySide6
(`py -m pip install PySide6`, or `pip install ff9mapkit[gui]`).
"""
from __future__ import annotations

import sys
from pathlib import Path

# THIS worktree's kit package must shadow any editable install (another worktree may differ), so insert
# it BEFORE the first ff9mapkit import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ff9mapkit"))


def main():
    try:
        from ff9mapkit.workspace.shell import main as run
    except ImportError as e:                              # PySide6 missing -> a friendly tk dialog, not a crash
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Dream World IX — Workspace",
            "The Workspace needs PySide6, which isn't installed.\n\n"
            "Install it with:\n    py -m pip install PySide6\n\n"
            f"(import detail: {e})")
        return
    run()


if __name__ == "__main__":
    main()
