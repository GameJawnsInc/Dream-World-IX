#!/usr/bin/env pythonw
"""FF9 Map Kit -- the launcher: one window, every tool.

Double-click this (windowless via pythonw) to pick which app to open. It's the front door to the kit's
GUI apps (all in this apps/ folder). The apps now ALSO combine into one tabbed window:

  * Campaign Editor -- campaign_editor.pyw (the all-in-one: the others below as tabs over one root)
  * FFIX Import     -- ff9_import.pyw      (bring content in from the real game: fork a field, read dialogue, inspect a save)
  * Build & Deploy  -- ff9_build_gui.pyw  (compile a field.toml + deploy it)
  * Logic Editor    -- ff9_editor.pyw     (form-based field.toml logic editor)
  * Dialogue Editor -- ff9_dialogue.pyw   (word-smith lines with a wrap preview; view/import stock dialogue)
  * Info Hub        -- ff9_infohub.pyw    (browse the catalogs; copy snippets)
"""
import os
import subprocess
import sys
from pathlib import Path

APPS = Path(__file__).resolve().parent
NOWIN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

import tkinter as tk                                   # noqa: E402
from tkinter import ttk                                # noqa: E402

TOOLS = [
    ("Campaign Editor", "campaign_editor.pyw", "All-in-one: Logic Editor + Info Hub + Build & Deploy in one tabbed window."),
    ("FFIX Import", "ff9_import.pyw", "Bring content in from the real game: fork a field (Native art, carry NPCs/dialogue/save), read dialogue, inspect a save."),
    ("Build & Deploy", "ff9_build_gui.pyw", "Compile a field.toml and deploy it to the test slot or the game."),
    ("Logic Editor",   "ff9_editor.pyw",    "Edit a field's logic (NPCs, events, gateways, cutscenes) in forms."),
    ("Dialogue Editor", "ff9_dialogue.pyw", "Word-smith every line with a live wrap preview; view/import stock dialogue."),
    ("Info Hub",       "ff9_infohub.pyw",   "Browse every catalog (models, archetypes, props, items); copy snippets."),
    ("Story State",    "ff9_storystate.pyw", "Inspect / diff / EDIT a save's story state (ScenarioCounter + flags); backup-guarded."),
]


def launch(filename):
    """Open one app as its own process + window (same interpreter; no console window on Windows)."""
    subprocess.Popen([sys.executable, str(APPS / filename)], creationflags=NOWIN)


class Launcher:
    def __init__(self, root):
        root.title("FF9 Map Kit")
        root.geometry("480x300")
        ttk.Label(root, text="FF9 Map Kit", font=("Segoe UI", 16, "bold")).pack(pady=(16, 0))
        ttk.Label(root, text="Pick a tool to open:", foreground="#555").pack(pady=(0, 10))
        for label, fname, desc in TOOLS:
            row = ttk.Frame(root, padding=(18, 3))
            row.pack(fill="x")
            ttk.Button(row, text=label, width=15, command=lambda fn=fname: launch(fn)).pack(side="left")
            ttk.Label(row, text=desc, wraplength=255, foreground="#555", justify="left").pack(side="left", padx=10)


def main():
    smoke = "--smoke" in sys.argv
    root = tk.Tk()
    if smoke:
        root.withdraw()
    Launcher(root)
    if smoke:
        ok = all((APPS / f).exists() for _, f, _ in TOOLS)
        print(f"smoke ok: launcher built; {len(TOOLS)} tools; all apps present in {APPS.name}/: {ok}")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
