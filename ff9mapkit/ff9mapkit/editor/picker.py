"""A modal Info Hub CATALOG PICKER for the editor (Tk).

Browse the same catalogs as the standalone viewer (via the UI-agnostic :mod:`..infohub` spine) and return
the chosen entry's NAME, so a form's name field (an NPC's preset, a give_item, ...) can be filled by
browse-and-pick instead of typing a model/archetype/item name blind. :func:`pick` is modal and returns the
chosen name (or ``None`` if cancelled); the editor wires a "Browse..." button next to each catalog-backed
field. It reuses the spine, so the editor and the standalone viewer stay in lockstep with one search core.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import infohub


def pick(parent, *, kinds=None, title="Pick from the catalog", initial="", campaign_context=None):
    """Open a modal catalog picker over the spine; return the chosen entry name (str) or None if cancelled.

    ``kinds`` restricts the search to those catalog kinds (e.g. ``["archetype", "creature"]``); None = all.
    ``initial`` pre-fills the search box (e.g. the field's current value). ``campaign_context`` (a
    CampaignPlan) lets the picker also surface the open campaign's members/shared flags (kind 'field'/'flag')."""
    dlg = _PickerDialog(parent, kinds=kinds, title=title, initial=initial, campaign_context=campaign_context)
    parent.wait_window(dlg.win)
    return dlg.result


class _PickerDialog:
    def __init__(self, parent, *, kinds=None, title="Pick", initial="", campaign_context=None):
        self.kinds = list(kinds) if kinds else None
        self.campaign_context = campaign_context
        self.result = None
        self._entries = []

        win = self.win = tk.Toplevel(parent)
        win.title(title)
        win.transient(parent)
        win.geometry("560x440")
        win.configure(background=parent.winfo_toplevel()["background"])   # inherit the themed window bg

        top = ttk.Frame(win, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Search:").pack(side="left")
        self.q = tk.StringVar(value=initial or "")
        ent = ttk.Entry(top, textvariable=self.q)
        ent.pack(side="left", fill="x", expand=True, padx=4)
        ent.bind("<KeyRelease>", lambda e: self._refresh())
        ent.bind("<Return>", lambda e: self._ok())
        ent.bind("<Escape>", lambda e: self._cancel())

        mid = ttk.Frame(win, padding=(6, 0))
        mid.pack(fill="both", expand=True)
        self.lst = tk.Listbox(mid, activestyle="none", exportselection=False)
        self.lst.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, command=self.lst.yview)
        sb.pack(side="right", fill="y")
        self.lst.config(yscrollcommand=sb.set)
        self.lst.bind("<Double-Button-1>", lambda e: self._ok())
        self.lst.bind("<<ListboxSelect>>", lambda e: self._describe())

        self.info = ttk.Label(win, text="", anchor="w", padding=(8, 2), wraplength=540, justify="left")
        self.info.pack(fill="x")

        bar = ttk.Frame(win, padding=6)
        bar.pack(fill="x")
        ttk.Button(bar, text="Use this", command=self._ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=self._cancel).pack(side="left", padx=6)

        self._refresh()
        ent.focus_set()
        win.grab_set()

    def _refresh(self):
        self._entries = infohub.browse(self.q.get(), kinds=self.kinds, limit=300,
                                       campaign_context=self.campaign_context)
        self.lst.delete(0, "end")
        for e in self._entries:
            self.lst.insert("end", f"{e.name}    [{e.kind}]")
        where = f" in {', '.join(self.kinds)}" if self.kinds else ""
        self.info.config(text=f"{len(self._entries)} match(es){where}")

    def _describe(self):
        sel = self.lst.curselection()
        if sel:
            e = self._entries[sel[0]]
            self.info.config(text=f"{e.name}  [{e.kind}]  --  {e.summary}")

    def _ok(self):
        sel = self.lst.curselection()
        if not sel and len(self._entries) == 1:        # a single match + Enter -> take it
            sel = (0,)
        if sel:
            self.result = self._entries[sel[0]].name
            self.win.destroy()

    def _cancel(self):
        self.result = None
        self.win.destroy()


def _smoke():
    """Headless self-test: build the picker, filter, simulate a pick."""
    root = tk.Tk()
    root.withdraw()
    dlg = _PickerDialog(root, kinds=["archetype", "creature"], title="smoke")
    dlg.q.set("vivi")
    dlg._refresh()
    names = [e.name for e in dlg._entries]
    assert "vivi" in names, names                      # the search finds the vivi archetype
    assert all(e.kind in ("archetype", "creature") for e in dlg._entries), names   # kinds filter holds
    dlg.lst.selection_set(names.index("vivi"))
    dlg._ok()
    print(f"picker smoke ok: {len(names)} archetype/creature match(es) for 'vivi' {names}; picked = {dlg.result!r}")
    root.destroy()


if __name__ == "__main__":
    import sys
    if "--smoke" in sys.argv:
        _smoke()
