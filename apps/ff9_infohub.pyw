#!/usr/bin/env pythonw
"""FF9 Map Kit -- Info Hub viewer (browse the catalogs; copy the field.toml snippet).

Double-click to launch (windowless via pythonw), or:  py apps\\ff9_infohub.pyw

A standalone window over the Info Hub spine (``ff9mapkit.infohub``): type to search every catalog at once
(archetypes, creatures, props, set pieces, raw models, items, battle scenes), pick a result to see its
model + animations + composite parts + aliases, and Copy snippet drops the ready-to-place
``[[npc]]`` / ``[[prop]]`` block on the clipboard. This is the FIRST frontend on the spine -- the same
core the planned Campaign Editor will embed (and a Blender panel could reuse).

Preview in-game deploys a gallery of the selection to the test slot (then F6 -> Reload to see it live);
Where in FF9? lists the real fields whose scripts place the selected model (the `detail(usage_fn=...)` hook).
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]               # repo root (apps/ is a direct child)
sys.path.insert(0, str(ROOT / "ff9mapkit"))              # the kit root holds the ff9mapkit package
sys.path.insert(0, str(ROOT / "tools"))                  # tools/ holds the field-usage index helper
from ff9mapkit import infohub                             # noqa: E402
from ff9mapkit.editor.theme import apply_theme            # noqa: E402  (shared modern theme/palette)
try:                                                     # the "Where in FF9?" lookup is optional
    import model_field_usage as _mfu                      # noqa: E402
except Exception:
    _mfu = None

import tkinter as tk                                      # noqa: E402
from tkinter import ttk, filedialog                       # noqa: E402

DEPLOY = ROOT / "tools" / "deploy_field.py"               # builds + deploys a field.toml into the test slot
PREVIEW = Path(os.environ.get("IHTEST", r"C:\Users\skaki\AppData\Local\Temp\ihtest"))
NOWIN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
KIND_CHOICES = ("all",) + infohub.KINDS


class InfoHubApp:
    def __init__(self, parent):
        self.root = parent.winfo_toplevel()      # real Tk root (clipboard/update); the UI mounts on `parent`
        self.pal = apply_theme(self.root)        # shared modern palette (styles ttk globally too)
        self._entries = []
        self._current = None
        self._det = None

        top = ttk.Frame(parent, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Search:").pack(side="left")
        self.q = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.q)
        ent.pack(side="left", fill="x", expand=True, padx=4)
        ent.bind("<KeyRelease>", lambda e: self.refresh())
        self.kind = tk.StringVar(value="all")
        ttk.OptionMenu(top, self.kind, "all", *KIND_CHOICES, command=lambda v: self.refresh()).pack(side="left")

        body = ttk.Panedwindow(parent, orient="horizontal")
        body.pack(fill="both", expand=True, padx=6, pady=4)
        left = ttk.Frame(body)
        body.add(left, weight=1)
        self.lst = tk.Listbox(left, activestyle="none", exportselection=False, borderwidth=0,
                              highlightthickness=0, bg=self.pal["field"], fg=self.pal["text"],
                              selectbackground=self.pal["accent"], selectforeground=self.pal["accent_fg"])
        self.lst.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(left, command=self.lst.yview)
        sb.pack(side="right", fill="y")
        self.lst.config(yscrollcommand=sb.set)
        self.lst.bind("<<ListboxSelect>>", lambda e: self.show())

        right = ttk.Frame(body)
        body.add(right, weight=2)
        self.detail = tk.Text(right, wrap="word", state="disabled", font=("Consolas", 10), borderwidth=0,
                              highlightthickness=0, padx=8, pady=6, bg=self.pal["surface"], fg=self.pal["text"])
        self.detail.pack(fill="both", expand=True)
        bar = ttk.Frame(right)
        bar.pack(fill="x")
        ttk.Button(bar, text="Copy snippet", command=self.copy).pack(side="left", pady=4)
        ttk.Button(bar, text="Preview in-game", command=self.preview).pack(side="left", padx=6, pady=4)
        ttk.Button(bar, text="Where in FF9?", command=self.where).pack(side="left", pady=4)
        ttk.Button(bar, text="Inspect save…", command=self.inspect_save).pack(side="left", padx=6, pady=4)

        self.status = ttk.Label(parent, text="", anchor="w", padding=(6, 2))
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
        self._det = infohub.detail(self._current)
        self._render(self._format(self._det))

    def copy(self):
        if not self._current:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(infohub.snippet(self._current))
        self.status.config(text=f'copied the {self._current.kind} "{self._current.name}" snippet to the clipboard')

    def preview(self):
        """Deploy a gallery of the selection to the test slot so you can F6 -> Reload and see it live."""
        if not self._current:
            return
        toml = infohub.preview_field_toml([self._current], PREVIEW / "art")
        if not toml:
            self.status.config(text=f'"{self._current.name}" ({self._current.kind}) is not placeable in a field')
            return
        out = PREVIEW / "preview.field.toml"
        out.write_text(toml, encoding="utf-8")
        self.status.config(text=f'building + deploying "{self._current.name}" ...')
        self.root.update()
        try:
            r = subprocess.run([sys.executable, str(DEPLOY), str(out)],
                               capture_output=True, text=True, timeout=180, creationflags=NOWIN)
            blob = (r.stdout or "") + (r.stderr or "")
            if "deployed" in blob.lower():
                self.status.config(text=f'deployed "{self._current.name}" -- in-game press F6 -> Reload field')
            else:
                tail = (blob.strip().splitlines() or ["(no output)"])[-1][:100]
                self.status.config(text=f"deploy failed: {tail}")
        except Exception as ex:
            self.status.config(text=f"deploy error: {ex}")

    def inspect_save(self):
        """Open the save inspector -- decode a real save's story state (ScenarioCounter, beat, chests, bits)."""
        _SaveInspector(self.root, self.pal)

    def where(self):
        """On-demand: which real FF9 fields place the selection's model? (the field-usage hook)."""
        if not self._current or self._det is None:
            return
        d = self._det
        if _mfu is None:
            self.status.config(text="field-usage tool unavailable (tools/model_field_usage.py)")
            return
        if d.model_id is None or not (d.model or "").startswith("GEO"):
            self.status.config(text=f'"{d.name}" ({d.kind}) has no field model to locate')
            return
        self.status.config(text=f'looking up where "{d.name}" appears in FF9 ...')
        self.root.update()
        try:
            locs, total = _mfu.usage(d.model_id, limit=20)
        except Exception as ex:
            self.status.config(text=f"field-usage lookup failed (build it: py tools/model_field_usage.py --build): {ex}")
            return
        d.locations = locs
        self._render(self._format(d))
        self.status.config(text=(f'"{d.name}" is placed by {total} real FF9 field script(s)' if total else
                                 f'"{d.name}" not in any field script (battle-only / prop-only / unique)'))

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


class _SaveInspector:
    """A window that decodes an FF9 save's story state. Pick a file (an encrypted SavedData_ww.dat, a
    Memoria plaintext extra-save, or an open save JSON / Base64 gEventGlobal); each populated slot is
    listed with its ScenarioCounter + beat, and selecting one shows the full report (treasure points,
    chests, set story bits by region) via the spine (``save.inspect`` + ``flags.render_report``)."""

    def __init__(self, parent, palette, path=None):
        self.pal = palette
        self.reports = []                                # [(label, SaveReport)]
        win = self.win = tk.Toplevel(parent)
        win.title("Inspect save — story state")
        win.transient(parent)
        win.geometry("780x540")
        win.configure(background=palette["bg"])

        top = ttk.Frame(win, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Save file:").pack(side="left")
        self.pathvar = tk.StringVar(value=path or "")
        ttk.Entry(top, textvariable=self.pathvar).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(top, text="Browse…", command=self._browse).pack(side="left")

        body = ttk.Panedwindow(win, orient="horizontal")
        body.pack(fill="both", expand=True, padx=6, pady=4)
        left = ttk.Frame(body)
        body.add(left, weight=1)
        self.lst = tk.Listbox(left, activestyle="none", exportselection=False, borderwidth=0,
                              highlightthickness=0, bg=palette["field"], fg=palette["text"],
                              selectbackground=palette["accent"], selectforeground=palette["accent_fg"])
        self.lst.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(left, command=self.lst.yview)
        sb.pack(side="right", fill="y")
        self.lst.config(yscrollcommand=sb.set)
        self.lst.bind("<<ListboxSelect>>", lambda e: self._show())
        right = ttk.Frame(body)
        body.add(right, weight=2)
        self.report = tk.Text(right, wrap="word", state="disabled", font=("Consolas", 10), borderwidth=0,
                              highlightthickness=0, padx=8, pady=6, bg=palette["surface"], fg=palette["text"])
        self.report.pack(fill="both", expand=True)

        self.status = ttk.Label(win, text="", anchor="w", padding=(6, 2), foreground=palette["muted"])
        self.status.pack(fill="x")
        if path:
            self._load(path)
        else:
            self._render("Pick a save file (Browse…) to decode its story state.\n\n"
                         "Works on:  EncryptedSavedData\\SavedData_ww.dat   (per slot; needs pycryptodome)\n"
                         "           a Memoria plaintext extra-save  ( *_Memoria_*.dat )\n"
                         "           an exported save JSON / a Base64 gEventGlobal blob")

    def _browse(self):
        from ff9mapkit import save as _save
        f = filedialog.askopenfilename(
            title="Pick a save (SavedData_ww.dat, a Memoria extra-save, or a save JSON)",
            initialdir=_save.default_save_dir() or "",   # open right where FF9's saves live (AppData/LocalLow)
            filetypes=[("FF9 save", "*.dat"), ("Save JSON / Base64", "*.json *.txt"), ("All files", "*.*")])
        if f:
            self.pathvar.set(f)
            self._load(f)

    def _load(self, path):
        from ff9mapkit import save as _save
        try:
            self.reports = _save.inspect(path)
        except Exception as e:                           # noqa: BLE001
            self.reports = []
            self.lst.delete(0, "end")
            self._render(f"Could not read story state from:\n{path}\n\n{e}\n\n"
                         "(An encrypted SavedData_ww.dat needs pycryptodome:  py -m pip install pycryptodome)")
            self.status.config(text="no story state decoded")
            return
        self.lst.delete(0, "end")
        for label, rep in self.reports:
            beat = rep.milestone[1] if rep.milestone else "(pre-story)"
            self.lst.insert("end", f"{label}  —  SC {rep.scenario_counter} · {beat}")
        self.status.config(text=f"{len(self.reports)} populated save(s) -- select one to read its story state")
        if self.reports:
            self.lst.selection_set(0)
            self._show()

    def _show(self):
        sel = self.lst.curselection()
        if not sel:
            return
        from ff9mapkit import flags as _flags
        label, rep = self.reports[sel[0]]
        self._render(f"{label}\n\n" + _flags.render_report(rep))

    def _render(self, text):
        self.report.config(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", text)
        self.report.config(state="disabled")


def main():
    smoke = "--smoke" in sys.argv
    root = tk.Tk()
    root.title("FF9 Map Kit — Info Hub")
    root.geometry("920x580")
    if smoke:
        root.withdraw()
    app = InfoHubApp(root)
    if smoke:                                            # headless self-test: populate + render one detail
        app.lst.selection_set(0)
        app.show()
        body = app.detail.get("1.0", "end")
        print(f"smoke ok: {len(app._entries)} entries; first = {app._entries[0].name!r}; "
              f"detail {len(body)} chars; snippet line 1 = {infohub.snippet(app._entries[0]).splitlines()[0]!r}")
        app.where()                                      # exercise the field-usage (Where in FF9?) hook
        print(f"where ok: {app._det.name!r} model {app._det.model_id} -> "
              f"{len(app._det.locations or [])} field location(s); status = {app.status.cget('text')!r}")
        # F3: the story-flag registry kind is browsable (a scenario milestone searchable by beat)
        sfs = infohub.browse("ice cavern", kinds=["storyflag"])
        assert any(e.ident == 2500 for e in sfs), "scenario milestone Ice Cavern (2500) searchable"
        # F3: the save inspector decodes a synthetic open save JSON (no crypto needed)
        import base64
        import json
        import tempfile
        geg = bytearray(2048)
        geg[0], geg[1] = 2500 & 0xFF, 2500 >> 8
        sp = Path(tempfile.gettempdir()) / "ih_smoke_save.json"
        sp.write_text(json.dumps({"profile": {"gEventGlobal": base64.b64encode(bytes(geg)).decode()}}),
                      encoding="utf-8")
        insp = _SaveInspector(root, app.pal, path=str(sp))
        assert len(insp.reports) == 1 and insp.reports[0][1].scenario_counter == 2500
        rpt = insp.report.get("1.0", "end")
        assert "Ice Cavern" in rpt, "the inspector renders the decoded report"
        print(f"F3 ok: {len(sfs)} storyflag hit(s); inspector decoded SC "
              f"{insp.reports[0][1].scenario_counter} ({len(rpt)} chars)")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
