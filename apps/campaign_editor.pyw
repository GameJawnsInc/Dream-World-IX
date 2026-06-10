#!/usr/bin/env pythonw
"""FF9 Map Kit -- Campaign Editor: the kit's GUIs in one tabbed window.

The unified front-end (Phase 3 of the Campaign Editor): the Logic Editor, the Info Hub catalog browser,
and Build & Deploy hosted as tabs over ONE Tk root. Each app was refactored to mount on a parent frame
(not own its own window), so they ALSO still run standalone via their individual launchers.

Double-click to launch (windowless via pythonw), or:  py apps\\campaign_editor.pyw
"""
import importlib.util
import sys
import traceback
from pathlib import Path

APPS = Path(__file__).resolve().parent
ROOT = APPS.parent
sys.path.insert(0, str(ROOT / "ff9mapkit"))     # the kit package
sys.path.insert(0, str(ROOT / "tools"))         # the field-usage helper (Info Hub's Where-in-FF9)

import tkinter as tk                              # noqa: E402
from tkinter import ttk, messagebox              # noqa: E402


def _load_app(filename, modname):
    """Import an apps/*.pyw module (.pyw isn't importable by name, so load it by path)."""
    spec = importlib.util.spec_from_file_location(modname, APPS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(root):
    """Mount the three app panels as tabs on `root`; return the notebook."""
    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)
    from ff9mapkit.editor.app import EditorApp        # in the package; built first so it sets the shared theme
    ed = ttk.Frame(nb); nb.add(ed, text="Logic Editor"); EditorApp(ed)
    ih = _load_app("ff9_infohub.pyw", "ff9_infohub")
    f = ttk.Frame(nb); nb.add(f, text="Info Hub"); ih.InfoHubApp(f)
    bg = _load_app("ff9_build_gui.pyw", "ff9_build_gui")
    f = ttk.Frame(nb); nb.add(f, text="Build & Deploy"); bg.App(f)
    return nb


def main():
    smoke = "--smoke" in sys.argv
    root = tk.Tk()
    root.title("FF9 Map Kit - Campaign Editor")
    root.geometry("1200x800")
    root.minsize(1000, 660)
    if smoke:
        root.withdraw()
    try:
        nb = build(root)
    except Exception:
        if not smoke:
            messagebox.showerror("FF9 Map Kit - Campaign Editor", traceback.format_exc())
        raise
    if smoke:
        print(f"campaign editor smoke ok: {nb.index('end')} tabs mounted on one root")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
