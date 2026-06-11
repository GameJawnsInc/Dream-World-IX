#!/usr/bin/env pythonw
"""FF9 Map Kit -- FFIX Import: bring content in from the real game.

Double-click to launch (windowless via pythonw), or:  py apps\\ff9_import.pyw

A discoverable front door to the kit's "import from game data" commands -- everything that reads your real
FF9 install (needs UnityPy). Two tabs:

  * Field          -- fork a REAL field into an editable project, with the fidelity options as PLAIN
                      checkboxes (Native art, carry NPCs/props, carry real dialogue, carry the save point)
                      instead of cryptic CLI flags. Then deploy what you made with Build & Deploy.
  * Read & Inspect -- view a real field's dialogue, inspect a save's story state, list the real fields,
                      or regenerate the kit's base templates from your install. (Read-only / maintenance.)

Each action shells out to `py -m ff9mapkit <cmd>` (run from the kit root) and STREAMS the output here, so
you see exactly what it read and wrote.
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]            # repo root (holds apps/, tools/, ff9mapkit/)
KIT = KIT_ROOT / "ff9mapkit"                              # the kit root (pyproject + the package) -- `-m` cwd
sys.path.insert(0, str(KIT_ROOT))
PYTHON = sys.executable
NOWIN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

import tkinter as tk                                       # noqa: E402
from tkinter import ttk, filedialog, messagebox, scrolledtext   # noqa: E402
from ff9mapkit.editor.theme import apply_theme             # noqa: E402  (shared modern theme/palette)


# --------------------------------------------------------------------------- pure arg builders (testable)
def import_args(field, *, out, field_id, name=None, art="native", carry_npcs=True, carry_text=True,
                dialogue_stubs=False, save_moogle=False) -> list:
    """The `ff9mapkit import ...` argv for a field fork (no `py -m ff9mapkit` prefix). ``art`` is
    'native' (--native) / 'borrow' (neither flag) / 'editable' (--editable). The carry flags map to the
    fidelity options; --carry-text and --save-moogle both imply --graft-player-funcs, which the kit also
    enforces, but we pass it explicitly when any carry is on so the command reads honestly."""
    args = ["import", str(field), "--out", str(out), "--id", str(field_id)]
    if name:
        args += ["--name", str(name)]
    if art == "native":
        args.append("--native")
    elif art == "editable":
        args.append("--editable")
    if carry_npcs or carry_text or save_moogle:
        args.append("--graft-player-funcs")
    if carry_text:
        args.append("--carry-text")
    if dialogue_stubs:
        args.append("--dialogue")
    if save_moogle:
        args.append("--save-moogle")
    return args


class App:
    def __init__(self, parent):
        self.root = parent.winfo_toplevel()               # real Tk root (after/dialogs); UI mounts on `parent`
        self.pal = apply_theme(self.root)                 # shared modern palette
        self.busy = False
        self.q: queue.Queue = queue.Queue()
        pad = dict(padx=10, pady=6)

        ttk.Label(parent, text="Bring content in from your real FF9 install (needs UnityPy).",
                  foreground=self.pal["muted"]).pack(fill="x", padx=10, pady=(8, 0))

        nb = ttk.Notebook(parent)
        nb.pack(fill="x", **pad)
        self.field_tab = ttk.Frame(nb)
        nb.add(self.field_tab, text="Field")
        self._build_field_tab(self.field_tab)
        self.read_tab = ttk.Frame(nb)
        nb.add(self.read_tab, text="Read & Inspect")
        self._build_read_tab(self.read_tab)

        self.log = scrolledtext.ScrolledText(parent, height=15, state="disabled", wrap="word",
                                             borderwidth=0, bg=self.pal["log_bg"], fg=self.pal["log_fg"])
        self.log.pack(fill="both", expand=True, **pad)
        self._write("Pick a field on the Field tab (or Find it), choose how faithfully to carry it, then "
                    "Import field. Deploy what you make with Build & Deploy.\n")
        self.root.after(120, self._drain)

    # ---------------------------------------------------------------- Field tab
    def _build_field_tab(self, parent):
        pad = dict(padx=8, pady=4)
        pick = ttk.Frame(parent)
        pick.pack(fill="x", **pad)
        ttk.Label(pick, text="Real field  —  an id, or an FBG-name substring (e.g. 100, grgr, alxt_map016).  "
                             "Use Find… to look up the exact names/ids.").grid(
            row=0, column=0, columnspan=2, sticky="w")
        self.field = tk.StringVar()
        ttk.Entry(pick, textvariable=self.field).grid(row=1, column=0, sticky="we")
        ttk.Button(pick, text="Find…", command=self.on_find).grid(row=1, column=1, padx=(6, 0))
        pick.columnconfigure(0, weight=1)

        art = ttk.LabelFrame(parent, text="Background art")
        art.pack(fill="x", **pad)
        self.art = tk.StringVar(value="native")
        for val, label in (
            ("native", "Native  —  seamless, faithful occlusion + lighting; works for ANY field (recommended)"),
            ("borrow", "BG-borrow  —  reuse the real art via DictionaryPatch (fast; area ≥ 10 only)"),
            ("editable", "Editable scene  —  repaintable per-depth layers (needs an in-game export first)"),
        ):
            ttk.Radiobutton(art, text=label, value=val, variable=self.art).pack(anchor="w", padx=6, pady=1)

        carry = ttk.LabelFrame(parent, text="Carry from the real field")
        carry.pack(fill="x", **pad)
        self.carry_npcs = tk.BooleanVar(value=True)
        self.carry_text = tk.BooleanVar(value=True)
        self.dialogue_stubs = tk.BooleanVar(value=False)
        self.save_moogle = tk.BooleanVar(value=False)
        ttk.Checkbutton(carry, variable=self.carry_npcs,
                        text="NPCs & props faithfully (their push/talk interactions fire)").pack(anchor="w", padx=6, pady=1)
        ttk.Checkbutton(carry, variable=self.carry_text,
                        text="Real dialogue, verbatim (per language) — carried NPCs speak the real words").pack(
            anchor="w", padx=6, pady=1)
        ttk.Checkbutton(carry, variable=self.dialogue_stubs,
                        text="Dialogue as editable [[npc]] stubs (to RE-AUTHOR, not carry)").pack(anchor="w", padx=6, pady=1)
        ttk.Checkbutton(carry, variable=self.save_moogle,
                        text="Save point — the hidden Moogle + the full save flourish (if the field has one)").pack(
            anchor="w", padx=6, pady=1)
        ttk.Label(carry, foreground=self.pal["muted"], wraplength=560, justify="left",
                  text="Carrying NPCs/props/dialogue/save grafts the donor's real bytes -- it needs no in-game export. "
                       "Without these, a fork is a faithful empty room you re-author.").pack(anchor="w", padx=6, pady=(0, 4))

        out = ttk.LabelFrame(parent, text="Write to")
        out.pack(fill="x", **pad)
        of = ttk.Frame(out)
        of.pack(fill="x", padx=6, pady=3)
        ttk.Label(of, text="Folder:").pack(side="left")
        self.out = tk.StringVar(value=str(KIT_ROOT / "imported"))
        ttk.Entry(of, textvariable=self.out).pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(of, text="Browse…", command=self.browse_out).pack(side="left")
        idf = ttk.Frame(out)
        idf.pack(fill="x", padx=6, pady=(0, 4))
        ttk.Label(idf, text="Field id:").pack(side="left")
        self.fid = tk.StringVar(value="4003")
        ttk.Entry(idf, textvariable=self.fid, width=8).pack(side="left", padx=(6, 14))
        ttk.Label(idf, text="Name (optional):").pack(side="left")
        self.name = tk.StringVar()
        ttk.Entry(idf, textvariable=self.name, width=18).pack(side="left", padx=(6, 0))

        run = ttk.Frame(parent)
        run.pack(fill="x", **pad)
        self.import_btn = ttk.Button(run, text="Import field", command=self.on_import)
        self.import_btn.pack(side="left")
        ttk.Label(run, text="→ then deploy it with Build & Deploy", foreground=self.pal["muted"]).pack(
            side="left", padx=10)

    # ---------------------------------------------------------------- Read & Inspect tab
    def _build_read_tab(self, parent):
        pad = dict(padx=8, pady=4)

        dlg = ttk.LabelFrame(parent, text="View a real field's dialogue  (dialogue-import)")
        dlg.pack(fill="x", **pad)
        df = ttk.Frame(dlg)
        df.pack(fill="x", padx=6, pady=4)
        ttk.Label(df, text="Field:").pack(side="left")
        self.dlg_field = tk.StringVar()
        ttk.Entry(df, textvariable=self.dlg_field, width=20).pack(side="left", padx=(6, 12))
        ttk.Label(df, text="Lang:").pack(side="left")
        self.dlg_lang = tk.StringVar(value="us")
        ttk.Combobox(df, textvariable=self.dlg_lang, width=5, state="readonly",
                     values=["us", "uk", "fr", "gr", "it", "es", "jp"]).pack(side="left", padx=(6, 12))
        self.dlg_btn = ttk.Button(df, text="View dialogue", command=self.on_view_dialogue)
        self.dlg_btn.pack(side="left")

        sav = ttk.LabelFrame(parent, text="Inspect a save's story state  (flags-inspect)")
        sav.pack(fill="x", **pad)
        sf = ttk.Frame(sav)
        sf.pack(fill="x", padx=6, pady=4)
        ttk.Label(sf, text="Save:").pack(side="left")
        self.save_path = tk.StringVar()
        ttk.Entry(sf, textvariable=self.save_path).pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(sf, text="Browse…", command=self.browse_save).pack(side="left", padx=(0, 6))
        self.save_btn = ttk.Button(sf, text="Inspect", command=self.on_inspect_save)
        self.save_btn.pack(side="left")

        lst = ttk.LabelFrame(parent, text="List real fields  (list-fields)")
        lst.pack(fill="x", **pad)
        lf = ttk.Frame(lst)
        lf.pack(fill="x", padx=6, pady=4)
        ttk.Label(lf, text="Filter:").pack(side="left")
        self.list_filter = tk.StringVar()
        ttk.Entry(lf, textvariable=self.list_filter, width=20).pack(side="left", padx=(6, 12))
        self.list_btn = ttk.Button(lf, text="List fields", command=self.on_list_fields)
        self.list_btn.pack(side="left")

        tpl = ttk.LabelFrame(parent, text="Maintenance")
        tpl.pack(fill="x", **pad)
        tf = ttk.Frame(tpl)
        tf.pack(fill="x", padx=6, pady=4)
        self.tpl_btn = ttk.Button(tf, text="Regenerate base templates", command=self.on_templates)
        self.tpl_btn.pack(side="left")
        ttk.Label(tf, text="rebuild the kit's base assets from YOUR install (ships no game data)",
                  foreground=self.pal["muted"], wraplength=380, justify="left").pack(side="left", padx=10)

    # ---------------------------------------------------------------- logging (post() is thread-safe)
    def _write(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", str(msg).rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def post(self, msg):
        self.q.put(msg)

    def _drain(self):
        try:
            while True:
                self._write(self.q.get_nowait())
        except queue.Empty:
            pass
        self.root.after(120, self._drain)

    # ---------------------------------------------------------------- run helpers
    def _buttons(self):
        return [getattr(self, b) for b in ("import_btn", "dlg_btn", "save_btn", "list_btn", "tpl_btn")
                if hasattr(self, b)]

    def _busy(self, b):
        self.busy = b
        st = ["disabled"] if b else ["!disabled"]
        for btn in self._buttons():
            btn.state(st)

    def _run_kit(self, args, *, intro=None, done_hint=None):
        """Shell out to `py -m ff9mapkit <args>` from the kit root and STREAM stdout/stderr into the log."""
        if self.busy:
            return
        self._busy(True)
        if intro:
            self.post("\n" + intro)
        self.post("$ ff9mapkit " + " ".join(args) + "\n")

        def work():
            try:
                proc = subprocess.Popen([PYTHON, "-m", "ff9mapkit", *args], cwd=str(KIT),
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                        bufsize=1, creationflags=NOWIN)
                for line in proc.stdout:
                    self.post(line.rstrip("\n"))
                code = proc.wait()
                if code == 0 and done_hint:
                    self.post(done_hint)
                elif code != 0:
                    self.post(f"[exit {code}] -- see the output above. (Importing needs UnityPy + your FF9 install.)")
            except Exception as e:                       # noqa: BLE001 -- surface any launch failure in the log
                self.post(f"ERROR launching ff9mapkit: {type(e).__name__}: {e}")
            finally:
                self.root.after(0, lambda: self._busy(False))

        threading.Thread(target=work, daemon=True).start()

    # ---------------------------------------------------------------- Field-tab actions
    def browse_out(self):
        d = filedialog.askdirectory(title="Folder to write the imported field into")
        if d:
            self.out.set(d)

    def on_find(self):
        self._run_kit(["list-fields", self.field.get().strip()] if self.field.get().strip()
                      else ["list-fields"], intro="Finding fields…")

    def on_import(self):
        field = self.field.get().strip()
        if not field:
            messagebox.showerror("No field", "Enter a real field id or name (use Find… to look it up).")
            return
        out = self.out.get().strip()
        if not out:
            messagebox.showerror("No output folder", "Pick a folder to write the imported field into.")
            return
        try:
            fid = int(self.fid.get().strip())
        except ValueError:
            messagebox.showerror("Bad field id", "Field id must be a number (e.g. 4003).")
            return
        Path(out).mkdir(parents=True, exist_ok=True)
        args = import_args(field, out=str(Path(out).resolve()), field_id=fid,
                           name=self.name.get().strip() or None, art=self.art.get(),
                           carry_npcs=self.carry_npcs.get(), carry_text=self.carry_text.get(),
                           dialogue_stubs=self.dialogue_stubs.get(), save_moogle=self.save_moogle.get())
        self._run_kit(args, intro=f"Importing {field}… (reads p0data via UnityPy; this can take a moment)",
                      done_hint=f"\nDone. The field.toml is in {out}. Next: open it in Build & Deploy to "
                                f"compile + deploy it (or add a [startup] block to assert its story beat).")

    # ---------------------------------------------------------------- Read-tab actions
    def browse_save(self):
        f = filedialog.askopenfilename(title="A save file (SavedData_ww.dat, a Memoria extra-save, or a save JSON)")
        if f:
            self.save_path.set(f)

    def on_view_dialogue(self):
        field = self.dlg_field.get().strip()
        if not field:
            messagebox.showerror("No field", "Enter a real field id or name to read its dialogue.")
            return
        self._run_kit(["dialogue-import", field, "--lang", self.dlg_lang.get()],
                      intro=f"Reading {field} dialogue ({self.dlg_lang.get()})…")

    def on_inspect_save(self):
        save = self.save_path.get().strip()
        if not save:
            messagebox.showerror("No save", "Pick a save file to inspect.")
            return
        self._run_kit(["flags-inspect", save], intro="Decoding the save's gEventGlobal…")

    def on_list_fields(self):
        flt = self.list_filter.get().strip()
        self._run_kit(["list-fields", flt] if flt else ["list-fields"], intro="Listing real fields…")

    def on_templates(self):
        if not messagebox.askyesno("Regenerate templates",
                                   "Rebuild the kit's base templates from your FF9 install? "
                                   "(Reads your install; writes only into the kit's data dir.)"):
            return
        self._run_kit(["extract-templates"], intro="Regenerating base templates from your install…",
                      done_hint="\nTemplates regenerated.")


def main():
    smoke = "--smoke" in sys.argv
    root = tk.Tk()
    root.title("FF9 Map Kit - FFIX Import")
    root.minsize(660, 560)
    if smoke:
        root.withdraw()
    app = App(root)
    if smoke:
        # the pure arg-builder is the behavioural core -- assert a representative mapping
        a = import_args("alexandria", out="/o", field_id=4003, art="native", carry_npcs=True,
                        carry_text=True, dialogue_stubs=False, save_moogle=False)
        want = ["import", "alexandria", "--out", "/o", "--id", "4003", "--native",
                "--graft-player-funcs", "--carry-text"]
        borrow = import_args("100", out="/o", field_id=4003, art="borrow", carry_npcs=False,
                             carry_text=False)
        controls = all(hasattr(app, c) for c in ("field", "art", "carry_npcs", "carry_text",
                                                 "save_moogle", "out", "fid", "import_btn",
                                                 "dlg_field", "save_path", "list_filter"))
        ok = a == want and borrow == ["import", "100", "--out", "/o", "--id", "4003"] and controls
        print(f"import gui smoke ok: tabs + controls built; import_args correct: {ok}")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
