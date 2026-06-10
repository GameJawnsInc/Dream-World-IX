"""Small THEMED modal input dialogs -- a drop-in for :mod:`tkinter.simpledialog`.

tkinter's ``simpledialog`` builds its Toplevel from CLASSIC tk widgets with OS-default colours, so it
ignores the app's ttk theme and renders light against the dark editor. These replacements use ttk
widgets on a Toplevel whose background matches the themed app, so an input prompt looks native to the
editor. :func:`ask_string` returns the entered text (or ``None`` if cancelled); :func:`ask_integer`
parses + range-checks an int, re-prompting inline on a bad value. The dialog is a small class
(mirroring :mod:`.picker`) so it's headless-testable -- ``ask_*`` just wrap it with ``wait_window``.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class _InputDialog:
    def __init__(self, parent, title, prompt, *, initial="", integer=False, minvalue=None, maxvalue=None):
        self.integer = integer
        self.minvalue, self.maxvalue = minvalue, maxvalue
        self.result = None

        win = self.win = tk.Toplevel(parent)
        win.title(title)
        win.transient(parent)
        win.resizable(False, False)
        try:                                              # match the themed app (a bare Toplevel is OS-gray)
            win.configure(background=parent.winfo_toplevel()["background"])
        except tk.TclError:
            pass

        ttk.Label(win, text=prompt, wraplength=380, justify="left").pack(anchor="w", padx=14, pady=(14, 6))
        self.var = tk.StringVar(value="" if initial is None else str(initial))
        ent = self.ent = ttk.Entry(win, textvariable=self.var, width=46)
        ent.pack(fill="x", padx=14)
        self.err = ttk.Label(win, text="", foreground="#ff6b6b", wraplength=380, justify="left")
        self.err.pack(anchor="w", padx=14, pady=(2, 0))

        bar = ttk.Frame(win, padding=12)
        bar.pack(fill="x")
        ttk.Button(bar, text="OK", style="Accent.TButton", command=self._ok).pack(side="right")
        ttk.Button(bar, text="Cancel", command=self._cancel).pack(side="right", padx=6)
        ent.bind("<Return>", lambda e: self._ok())
        ent.bind("<Escape>", lambda e: self._cancel())
        ent.focus_set()
        ent.select_range(0, "end")
        win.grab_set()

    def _ok(self):
        v = self.var.get().strip()
        if self.integer:
            try:
                n = int(v)
            except ValueError:
                self.err.config(text="Enter a whole number.")
                return
            if self.minvalue is not None and n < self.minvalue:
                self.err.config(text=f"Must be at least {self.minvalue}.")
                return
            if self.maxvalue is not None and n > self.maxvalue:
                self.err.config(text=f"Must be at most {self.maxvalue}.")
                return
            self.result = n
        else:
            self.result = v                               # the caller treats "" as cancel (if not name: ...)
        self.win.destroy()

    def _cancel(self):
        self.result = None
        self.win.destroy()


def ask_string(parent, title, prompt, *, initial=""):
    """Modal themed text prompt. Returns the entered string, or None if cancelled."""
    dlg = _InputDialog(parent, title, prompt, initial=initial)
    parent.wait_window(dlg.win)
    return dlg.result


def ask_integer(parent, title, prompt, *, initial=None, minvalue=None, maxvalue=None):
    """Modal themed integer prompt (re-prompts inline on a non-int / out-of-range). Returns int or None."""
    dlg = _InputDialog(parent, title, prompt, initial=initial, integer=True,
                       minvalue=minvalue, maxvalue=maxvalue)
    parent.wait_window(dlg.win)
    return dlg.result


def _smoke():
    """Headless self-test: build the dialog, drive _ok/_cancel, and check string + int parsing/ranging."""
    from .theme import apply_theme
    root = tk.Tk()
    root.withdraw()
    apply_theme(root)

    d = _InputDialog(root, "t", "name?", initial="seed")
    assert d.var.get() == "seed"
    d.var.set("boss_dead"); d._ok()
    assert d.result == "boss_dead", d.result

    bad = _InputDialog(root, "t", "n?", integer=True, minvalue=4000, maxvalue=32767)
    bad.var.set("nope"); bad._ok()
    assert bad.result is None and bad.err["text"], "a non-int stays open with an error"
    bad.var.set("10"); bad._ok()
    assert bad.result is None, "below minvalue stays open"
    bad.var.set("5000"); bad._ok()
    assert bad.result == 5000, bad.result

    cx = _InputDialog(root, "t", "x?"); cx._cancel()
    assert cx.result is None
    print("dialogs smoke ok: string + integer (parse/range) + cancel")
    root.destroy()


if __name__ == "__main__":
    import sys
    if "--smoke" in sys.argv:
        _smoke()
