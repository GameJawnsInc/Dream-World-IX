#!/usr/bin/env pythonw
"""FF9 Map Kit -- Info Hub viewer (browse the catalogs; copy the field.toml snippet).

Double-click to launch (windowless via pythonw), or:  py tools\\ff9_infohub.pyw

A standalone window over the Info Hub spine (``ff9mapkit.infohub``): type to search every catalog at once
(archetypes, creatures, props, set pieces, raw models, items, battle scenes), pick a result to see its
model + animations + composite parts + aliases, and Copy snippet drops the ready-to-place
``[[npc]]`` / ``[[prop]]`` block on the clipboard. This is the FIRST frontend on the spine -- the same
core the planned Campaign Editor will embed (and a Blender panel could reuse).

Deferred (the spine already supports the hooks): a "Where in FF9?" button (the `detail(usage_fn=...)`
field-usage hook) and a "Preview in-game" button (deploy a gallery of the selection).
"""
import os
import sys

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)                                   # the kit root holds the ff9mapkit package
from ff9mapkit import infohub                             # noqa: E402

import tkinter as tk                                      # noqa: E402
from tkinter import ttk                                   # noqa: E402

KIND_CHOICES = ("all",) + infohub.KINDS


class InfoHubApp:
    def __init__(self, root):
        self.root = root
        root.title("FF9 Map Kit — Info Hub")
        root.geometry("920x580")
        self._entries = []
        self._current = None

        top = ttk.Frame(root, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Search:").pack(side="left")
        self.q = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.q)
        ent.pack(side="left", fill="x", expand=True, padx=4)
        ent.bind("<KeyRelease>", lambda e: self.refresh())
        self.kind = tk.StringVar(value="all")
        ttk.OptionMenu(top, self.kind, "all", *KIND_CHOICES, command=lambda v: self.refresh()).pack(side="left")

        body = ttk.Panedwindow(root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=6, pady=4)
        left = ttk.Frame(body)
        body.add(left, weight=1)
        self.lst = tk.Listbox(left, activestyle="none", exportselection=False)
        self.lst.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(left, command=self.lst.yview)
        sb.pack(side="right", fill="y")
        self.lst.config(yscrollcommand=sb.set)
        self.lst.bind("<<ListboxSelect>>", lambda e: self.show())

        right = ttk.Frame(body)
        body.add(right, weight=2)
        self.detail = tk.Text(right, wrap="word", state="disabled", font=("Consolas", 10))
        self.detail.pack(fill="both", expand=True)
        bar = ttk.Frame(right)
        bar.pack(fill="x")
        ttk.Button(bar, text="Copy snippet", command=self.copy).pack(side="left", pady=4)

        self.status = ttk.Label(root, text="", anchor="w", padding=(6, 2))
        self.status.pack(fill="x")
        self.refresh()

    # ----- data -----
    def refresh(self):
        kind = self.kind.get()
        kinds = None if kind == "all" else [kind]
        self._entries = infohub.browse(self.q.get(), kinds=kinds, limit=None)
        self.lst.delete(0, "end")
        for e in self._entries:
            self.lst.insert("end", f"{e.name}    [{e.kind}]")
        self.status.config(text=f"{len(self._entries)} result(s)")
        self._current = None
        self._render("")

    def show(self):
        sel = self.lst.curselection()
        if not sel:
            return
        self._current = self._entries[sel[0]]
        self._render(self._format(infohub.detail(self._current)))

    def copy(self):
        if not self._current:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(infohub.snippet(self._current))
        self.status.config(text=f'copied the {self._current.kind} "{self._current.name}" snippet to the clipboard')

    # ----- view -----
    @staticmethod
    def _format(d):
        L = [f"{d.name}   [{d.kind}]"]
        L += [f"  {label}: {val}" for label, val in d.facts]
        if d.aliases:
            L.append(f"  aliases: {', '.join(d.aliases)}")
        if d.movement:
            L.append("  movement: " + "  ".join(f"{k}={v}" for k, v in d.movement.items()))
        if d.anims:
            shown = ", ".join(f"{a}={i}" for a, i in d.anims[:24])
            more = "" if len(d.anims) <= 24 else f"  (+{len(d.anims) - 24} more)"
            L.append(f"  animations ({len(d.anims)}): {shown}{more}")
        if d.parts:
            L.append("  parts:")
            for name, pose, dx, dz in d.parts:
                off = "" if (dx == 0 and dz == 0) else f"   offset ({dx}, {dz})"
                L.append(f"     - {name}   pose {pose}{off}")
        if d.locations:
            L.append("  appears in: " + "; ".join(f"{fid}={nm}" for fid, nm in d.locations[:12]))
        L += ["", "--- field.toml ---", d.snippet]
        return "\n".join(L)

    def _render(self, text):
        self.detail.config(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.config(state="disabled")


def main():
    smoke = "--smoke" in sys.argv
    root = tk.Tk()
    if smoke:
        root.withdraw()
    app = InfoHubApp(root)
    if smoke:                                            # headless self-test: populate + render one detail
        app.lst.selection_set(0)
        app.show()
        body = app.detail.get("1.0", "end")
        print(f"smoke ok: {len(app._entries)} entries; first = {app._entries[0].name!r}; "
              f"detail {len(body)} chars; snippet line 1 = {infohub.snippet(app._entries[0]).splitlines()[0]!r}")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
