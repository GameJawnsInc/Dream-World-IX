#!/usr/bin/env pythonw
"""FF9 Map Kit -- Story State console (inspect / diff / EDIT a save's gEventGlobal story state).

Double-click to launch (windowless via pythonw), or:  py apps\\ff9_storystate.pyw

The save-side companion to the Info Hub's story-flag REGISTRY: load a real FF9 save and work with its
narrative state, all anchored on the same registry the Info Hub browses (``flags.py``).

  * Inspect -- the decoded story state of each populated slot: ScenarioCounter -> beat, treasure points,
               chests, and set story bits grouped by named region (``save.inspect`` + ``flags.render_report``).
  * Diff    -- load a second save (or another slot) and see the A -> B delta: exactly what scenario / flags
               a story beat or play session wrote (``flags.diff_reports`` + ``render_diff``).
  * Edit    -- set the ScenarioCounter / set+clear story bits and write it back -- BACKUP-GUARDED (a .bak is
               made first) and reserved-region-REFUSED (``save.apply_story_edit`` shares the CLI's guards).

Editing needs the encrypted ``SavedData_ww.dat`` (pycryptodome); inspect/diff also read a Memoria
plaintext extra-save or an exported save JSON / Base64 gEventGlobal. Read-only + provenance-clean (it
touches only the user's own save, and only when they click Apply). Standalone, or embedded as a tab.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]               # repo root (apps/ is a direct child)
sys.path.insert(0, str(ROOT / "ff9mapkit"))              # the kit root holds the ff9mapkit package
from ff9mapkit import save as _save                       # noqa: E402  (the SavedData_ww.dat codec + inspect/edit)
from ff9mapkit import flags as _flags                     # noqa: E402  (the registry + render_report/render_diff)
from ff9mapkit.editor.theme import apply_theme            # noqa: E402  (shared modern theme/palette)

import tkinter as tk                                      # noqa: E402
from tkinter import ttk, filedialog, messagebox           # noqa: E402


class StoryStateApp:
    """App-on-parent (mirrors InfoHubApp): builds into ``parent``; ``parent.winfo_toplevel()`` is the real
    Tk root (for dialogs). Standalone via :func:`main`, or embedded as a Campaign-Editor tab."""

    def __init__(self, parent):
        self.root = parent.winfo_toplevel()
        self.pal = apply_theme(self.root)
        self.reports = []         # [(label, SaveReport)] for file A (the loaded save)
        self.blocks = []          # editable block per report (or None when not an encrypted .dat)
        self.path = ""
        self.reports_b = []       # file B (for diff)

        top = ttk.Frame(parent, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Save file:").pack(side="left")
        self.pathvar = tk.StringVar()
        ttk.Entry(top, textvariable=self.pathvar).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(top, text="Browse…", command=self._browse).pack(side="left")

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
        self.lst.bind("<<ListboxSelect>>", lambda e: self._on_select())

        right = ttk.Frame(body)
        body.add(right, weight=2)
        self.nb = ttk.Notebook(right)
        self.nb.pack(fill="both", expand=True)
        self._build_inspect()
        self._build_diff()
        self._build_edit()

        self.status = ttk.Label(parent, text="", anchor="w", padding=(6, 2), foreground=self.pal["muted"])
        self.status.pack(fill="x")
        self._render(self.inspect_txt,
                     "Pick a SavedData_ww.dat (Browse…) to read / diff / edit its story state.\n\n"
                     "Editing needs the encrypted SavedData_ww.dat (pycryptodome). Inspect/Diff also read a\n"
                     "Memoria extra-save ( *_Memoria_*.dat ) or an exported save JSON / Base64 gEventGlobal.")

    # ----- view scaffolding -----
    def _text(self, parent):
        return tk.Text(parent, wrap="word", state="disabled", font=("Consolas", 10), borderwidth=0,
                       highlightthickness=0, padx=8, pady=6, bg=self.pal["surface"], fg=self.pal["text"])

    @staticmethod
    def _render(widget, text):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")

    def _build_inspect(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Inspect")
        self.inspect_txt = self._text(f)
        self.inspect_txt.pack(fill="both", expand=True)

    def _build_diff(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Diff")
        bar = ttk.Frame(f, padding=4)
        bar.pack(fill="x")
        ttk.Label(bar, text="Compare selection (A) against:").pack(side="left")
        self.bvar = tk.StringVar()
        ttk.Entry(bar, textvariable=self.bvar).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(bar, text="Browse…", command=self._browse_b).pack(side="left")
        bar2 = ttk.Frame(f, padding=(4, 0))
        bar2.pack(fill="x")
        ttk.Label(bar2, text="B slot:").pack(side="left")
        self.bslot = tk.StringVar(value="0")
        self.bslot_menu = ttk.OptionMenu(bar2, self.bslot, "0")
        self.bslot_menu.pack(side="left", padx=4)
        ttk.Button(bar2, text="Compare  A → B", command=self._compare).pack(side="left", padx=6)
        ttk.Label(bar2, text="(no B file → compares two slots of the loaded save)",
                  foreground=self.pal["muted"]).pack(side="left")
        self.diff_txt = self._text(f)
        self.diff_txt.pack(fill="both", expand=True)

    def _build_edit(self):
        f = ttk.Frame(self.nb, padding=4)
        self.nb.add(f, text="Edit")
        self.edit_target = ttk.Label(f, text="(no save selected)", foreground=self.pal["muted"])
        self.edit_target.pack(anchor="w")
        form = ttk.Frame(f)
        form.pack(fill="x", pady=4)
        ttk.Label(form, text="Scenario:").grid(row=0, column=0, sticky="w")
        self.sc_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.sc_var, width=24).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(form, text='a value or area name (e.g. "Ice Cavern")',
                  foreground=self.pal["muted"]).grid(row=0, column=2, sticky="w")
        ttk.Label(form, text="Set flags:").grid(row=1, column=0, sticky="w")
        self.set_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.set_var, width=24).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(form, text="comma-separated bit indices (custom band ≥ 8512)",
                  foreground=self.pal["muted"]).grid(row=1, column=2, sticky="w")
        ttk.Label(form, text="Clear flags:").grid(row=2, column=0, sticky="w")
        self.clear_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.clear_var, width=24).grid(row=2, column=1, sticky="w", padx=4)
        btns = ttk.Frame(f)
        btns.pack(fill="x", pady=2)
        self.preview_btn = ttk.Button(btns, text="Preview", command=self._preview)
        self.preview_btn.pack(side="left")
        self.apply_btn = ttk.Button(btns, text="Apply  (backup + write)", command=self._apply)
        self.apply_btn.pack(side="left", padx=6)
        self.edit_txt = self._text(f)
        self.edit_txt.pack(fill="both", expand=True)

    # ----- loading (file A) -----
    def _browse(self):
        f = filedialog.askopenfilename(
            title="Pick a save (SavedData_ww.dat, a Memoria extra-save, or a save JSON)",
            initialdir=_save.default_save_dir() or "",
            filetypes=[("FF9 save", "*.dat"), ("Save JSON / Base64", "*.json *.txt"), ("All files", "*.*")])
        if f:
            self.pathvar.set(f)
            self._load(f)

    def _load(self, path):
        try:
            self.reports = _save.inspect(path)
        except Exception as e:                            # noqa: BLE001 -- any decode failure -> a clear note
            self.reports, self.blocks, self.path = [], [], ""
            self.lst.delete(0, "end")
            self._render(self.inspect_txt, f"Could not read story state from:\n{path}\n\n{e}\n\n"
                         "(An encrypted SavedData_ww.dat needs pycryptodome: py -m pip install pycryptodome)")
            self.status.config(text="no story state decoded")
            return
        self.path = path
        self.blocks = self._editable_blocks(path, len(self.reports))
        self.lst.delete(0, "end")
        for label, rep in self.reports:
            beat = rep.milestone[1] if rep.milestone else "(pre-story)"
            self.lst.insert("end", f"{label}  —  SC {rep.scenario_counter} · {beat}")
        ro = "" if any(b is not None for b in self.blocks) else \
            "  (read-only: editing needs the encrypted SavedData_ww.dat)"
        self.status.config(text=f"{len(self.reports)} populated save(s){ro}")
        if self.reports:
            self.lst.selection_set(0)
            self._on_select()

    @staticmethod
    def _editable_blocks(path, n):
        """The editable block per report (encrypted .dat only; ``save.inspect`` uses ``populated()`` order
        for an encrypted container, so index alignment holds). [None]*n when the file isn't an editable
        container (a Memoria extra-save / JSON / no pycryptodome)."""
        try:
            pops = _save.FF9Save.load(path).populated()
        except Exception:                                 # noqa: BLE001 -- not an encrypted .dat / no crypto
            return [None] * n
        return [p.block for p in pops] if len(pops) == n else [None] * n

    def _selected(self):
        sel = self.lst.curselection()
        return sel[0] if sel else None

    def _on_select(self):
        i = self._selected()
        if i is None:
            return
        label, rep = self.reports[i]
        self._render(self.inspect_txt, f"{label}\n\n" + _flags.render_report(rep))
        blk = self.blocks[i] if i < len(self.blocks) else None
        if blk is None:
            self.edit_target.config(text="Editing disabled — load the encrypted SavedData_ww.dat "
                                         "(this view is read-only).")
            self.preview_btn.config(state="disabled")
            self.apply_btn.config(state="disabled")
        else:
            self.edit_target.config(text=f"Editing: {label}  (block {blk}).  "
                                         f"Reserved-region flags are refused; a .bak is made before any write.")
            self.preview_btn.config(state="normal")
            self.apply_btn.config(state="normal")

    # ----- diff (file B) -----
    def _browse_b(self):
        f = filedialog.askopenfilename(
            title="Pick the second save (B) to compare against",
            initialdir=_save.default_save_dir() or "",
            filetypes=[("FF9 save", "*.dat"), ("Save JSON / Base64", "*.json *.txt"), ("All files", "*.*")])
        if f:
            self.bvar.set(f)
            self._load_b(f)

    def _load_b(self, path):
        try:
            self.reports_b = _save.inspect(path)
        except Exception as e:                            # noqa: BLE001
            self.reports_b = []
            self._render(self.diff_txt, f"Could not read save B:\n{path}\n\n{e}")
            return
        menu = self.bslot_menu["menu"]
        menu.delete(0, "end")
        for i, (label, rep) in enumerate(self.reports_b):
            menu.add_command(label=f"{i}: {label} (SC {rep.scenario_counter})",
                             command=lambda v=str(i): self.bslot.set(v))
        self.bslot.set("0")
        self.status.config(text=f"B: {len(self.reports_b)} populated save(s) — pick A (left) + a B slot, then Compare")

    def _compare(self):
        i = self._selected()
        if i is None:
            self._render(self.diff_txt, "Select a save on the left (A) first.")
            return
        reps_b = self.reports_b or self.reports          # no B file -> compare two slots of A
        try:
            j = int(self.bslot.get())
        except ValueError:
            j = 0
        if not 0 <= j < len(reps_b):
            self._render(self.diff_txt, f"B slot {j} out of range (B has {len(reps_b)} slot(s)).")
            return
        (la, ra), (lb, rb) = self.reports[i], reps_b[j]
        diff = _flags.diff_reports(ra, rb)
        self._render(self.diff_txt, f"A: {la}\nB: {lb}\n\n" + _flags.render_diff(diff))

    # ----- edit (write the save) -----
    def _parse_bits(self, s):
        out = []
        for tok in (s or "").replace(";", ",").split(","):
            tok = tok.strip()
            if tok:
                out.append(_flags.resolve(tok, {}))      # a bit index (or a [[flag]] name, were a names map given)
        return out

    def _edit_args(self):
        sc = self.sc_var.get().strip()
        scenario = _flags.resolve_scenario(sc) if sc else None
        return scenario, self._parse_bits(self.set_var.get()), self._parse_bits(self.clear_var.get())

    def _target_block(self):
        i = self._selected()
        return self.blocks[i] if (i is not None and i < len(self.blocks)) else None

    def _preview(self):
        blk = self._target_block()
        if blk is None:
            return
        try:
            scenario, setb, clrb = self._edit_args()
            res = _save.apply_story_edit(self.path, block=blk, scenario=scenario,
                                         set_flags=setb, clear_flags=clrb, dry_run=True)
        except (ValueError, IndexError) as e:
            self._render(self.edit_txt, f"Cannot apply:\n  {e}")
            return
        if not res["notes"]:
            self._render(self.edit_txt, "Nothing to change — set a Scenario / Set flags / Clear flags.")
            return
        body = "PREVIEW (nothing written yet):\n" + "\n".join(f"  - {n}" for n in res["notes"])
        if res["extra"]:
            body += "\n\n  (a Memoria extra-save is present and will be patched too)"
        self._render(self.edit_txt, body)

    def _apply(self):
        blk = self._target_block()
        if blk is None:
            return
        try:
            scenario, setb, clrb = self._edit_args()
            preview = _save.apply_story_edit(self.path, block=blk, scenario=scenario,
                                             set_flags=setb, clear_flags=clrb, dry_run=True)
        except (ValueError, IndexError) as e:
            self._render(self.edit_txt, f"Cannot apply:\n  {e}")
            return
        if not preview["notes"]:
            self._render(self.edit_txt, "Nothing to change.")
            return
        if not messagebox.askyesno("Apply story-state edit?",
                                   "This edits your REAL save (a .bak backup is written first):\n\n"
                                   + "\n".join(preview["notes"]) + "\n\nProceed?"):
            return
        try:
            res = _save.apply_story_edit(self.path, block=blk, scenario=scenario,
                                         set_flags=setb, clear_flags=clrb)
        except Exception as e:                            # noqa: BLE001 -- surface any write failure in-pane
            self._render(self.edit_txt, f"Write failed:\n  {e}")
            return
        msg = ["APPLIED — your save was edited:"] + [f"  - {n}" for n in res["notes"]]
        msg += [f"  backed up -> {os.path.basename(b)}" for b in res["backups"]]
        if res["extra"]:
            msg.append("  (Memoria extra-save patched too)")
        msg.append("\nReload the save in-game to see it.")
        self._render(self.edit_txt, "\n".join(msg))
        self.status.config(text="save edited (backup written) — reload it in-game")
        self._load(self.path)                            # refresh inspect against the just-written save


def main():
    smoke = "--smoke" in sys.argv
    root = tk.Tk()
    root.title("FF9 Map Kit — Story State")
    root.geometry("900x600")
    if smoke:
        root.withdraw()
    app = StoryStateApp(root)
    if smoke:
        import base64
        import json
        import tempfile

        def _json_save(sc, bits=()):
            g = bytearray(2048)
            g[0], g[1] = sc & 0xFF, sc >> 8
            for b in bits:
                g[b >> 3] |= 1 << (b & 7)
            p = Path(tempfile.mktemp(suffix=".json"))
            p.write_text(json.dumps({"profile": {"gEventGlobal": base64.b64encode(bytes(g)).decode()}}),
                         encoding="utf-8")
            return str(p)

        # inspect + diff with crypto-free JSON saves
        app._load(_json_save(2500, (8520,)))
        assert app.reports and app.reports[0][1].scenario_counter == 2500
        app._on_select()
        assert "Ice Cavern" in app.inspect_txt.get("1.0", "end"), "inspect renders the beat"
        app._load_b(_json_save(7200, (8520, 8530)))
        app.bslot.set("0")
        app._compare()
        diff = app.diff_txt.get("1.0", "end")
        assert "8530" in diff, "diff shows the newly-set bit"
        # edit-preview on an encrypted .dat (only if pycryptodome is present)
        edit_ok = "skipped (no pycryptodome)"
        try:
            from Crypto.Cipher import AES  # noqa: PLC0415
            key, iv = _save._key_iv()
            g = bytearray(2048)
            g[0], g[1] = 6000 & 0xFF, 6000 >> 8
            pt = bytearray(_save.SAVE_BLOCK_SIZE)
            pt[0:4] = b"SAVE"
            b64 = base64.b64encode(bytes(g))
            pt[23:23 + len(b64)] = b64
            data = bytearray(_save.BASE_SAVE_BLOCK_OFFSET + _save.SAVE_BLOCK_SIZE * 2)
            lo = _save.BASE_SAVE_BLOCK_OFFSET + _save.SAVE_BLOCK_SIZE
            data[lo:lo + _save.SAVE_BLOCK_SIZE] = AES.new(key, AES.MODE_CBC, iv).encrypt(bytes(pt))
            dp = Path(tempfile.mktemp(suffix=".dat"))
            dp.write_bytes(bytes(data))
            app._load(str(dp))
            assert any(b is not None for b in app.blocks), "encrypted .dat is editable"
            app.lst.selection_set(0)
            app._on_select()
            app.sc_var.set("Ice Cavern")
            app.set_var.set("8540")
            app._preview()
            pv = app.edit_txt.get("1.0", "end")
            assert "2500" in pv and "8540" in pv, "preview lists the scenario + flag change"
            # reserved-region flag is refused in preview (no write)
            app.set_var.set("8400")
            app._preview()
            assert "reserved" in app.edit_txt.get("1.0", "end").lower(), "reserved flag refused"
            edit_ok = "preview ok (scenario + flag; reserved refused)"
        except ImportError:
            pass
        print(f"smoke ok: inspect SC {app.reports[0][1].scenario_counter if app.reports else '-'}; "
              f"diff {len(diff)} chars; edit {edit_ok}")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
