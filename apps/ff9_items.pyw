#!/usr/bin/env pythonw
"""FF9 Map Kit -- Item & Equipment save editor (inspect / EDIT a save's gil, inventory, equipment).

Double-click to launch (windowless via pythonw), or:  py apps\\ff9_items.pyw

The item/equip companion to the Story State console -- a SEPARATE surface (it touches only
:mod:`ff9mapkit.save_items`, never the story-state core; project-ff9-branch-lanes rule 3). It reads + writes
the Memoria EXTRA save file (``SavedData_ww_Memoria_*.dat``), the **load-authoritative** store that overrides
the encrypted main block on load (proven in-game), so an edit here changes what the game loads -- no relaunch,
just reload the save.

  * Inspect -- the decoded gil / inventory / equipment of each populated slot (``save_items.inspect``).
  * Edit    -- set gil, set/remove an item by name, or change a character's equipment -- each PREVIEWable
               (dry-run) and Apply backup-guarded (a timestamped .bak is written first; the write is atomic and
               re-read to confirm). Extra-only by design (the main-block mirror is a later step).

Pick a SavedData_ww.dat (enumerates its populated slots' extra files; the container read needs pycryptodome)
or a Memoria extra-save directly (no crypto). Provenance-clean: it touches only the user's own save, only on
Apply. Standalone, or embedded as a tab.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]               # repo root (apps/ is a direct child)
sys.path.insert(0, str(ROOT / "ff9mapkit"))              # the kit root holds the ff9mapkit package
from ff9mapkit import save as _save                       # noqa: E402  (the container codec + slot enumeration)
from ff9mapkit import save_items as _si                   # noqa: E402  (the item/equip read + write surface)
from ff9mapkit.editor.theme import apply_theme            # noqa: E402  (shared modern theme/palette)

import tkinter as tk                                      # noqa: E402
from tkinter import ttk, filedialog, messagebox           # noqa: E402


class ItemsApp:
    """App-on-parent (mirrors StoryStateApp): builds into ``parent``; ``parent.winfo_toplevel()`` is the real
    Tk root (for dialogs). Standalone via :func:`main`, or embedded as a Campaign-Editor tab."""

    def __init__(self, parent):
        self.root = parent.winfo_toplevel()
        self.pal = apply_theme(self.root)
        self.targets = []        # [(label, ItemReport|None, extra_path|None)] per populated slot
        self.path = ""

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
        self._build_edit()

        self.status = ttk.Label(parent, text="", anchor="w", padding=(6, 2), foreground=self.pal["muted"])
        self.status.pack(fill="x")
        self._render(self.inspect_txt,
                     "Pick a save (Browse…) to read / edit its gil, inventory and equipment.\n\n"
                     "A SavedData_ww.dat lists its populated slots (needs pycryptodome to read the container);\n"
                     "a Memoria extra-save ( *_Memoria_*.dat ) opens directly. Edits are written to the extra\n"
                     "file (the load-authoritative store) -- reload the save in-game to see them, no relaunch.")

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

    def _out(self, text):
        self._render(self.edit_txt, text)

    def _build_inspect(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Inspect")
        self.inspect_txt = self._text(f)
        self.inspect_txt.pack(fill="both", expand=True)

    def _build_edit(self):
        f = ttk.Frame(self.nb, padding=4)
        self.nb.add(f, text="Edit")
        self.edit_target = ttk.Label(f, text="(no save selected)", foreground=self.pal["muted"])
        self.edit_target.pack(anchor="w")

        # --- Gil ---
        gf = ttk.LabelFrame(f, text="Gil", padding=4)
        gf.pack(fill="x", pady=2)
        self.gil_var = tk.StringVar()
        ttk.Entry(gf, textvariable=self.gil_var, width=12).pack(side="left", padx=4)
        ttk.Label(gf, text=f"(0–{_si.GIL_CAP:,})", foreground=self.pal["muted"]).pack(side="left")
        ttk.Button(gf, text="Preview", command=lambda: self._edit("gil", False)).pack(side="left", padx=(8, 2))
        ttk.Button(gf, text="Apply", command=lambda: self._edit("gil", True)).pack(side="left")

        # --- Item ---
        itf = ttk.LabelFrame(f, text="Item  (count 0 removes; clamps to 99)", padding=4)
        itf.pack(fill="x", pady=2)
        ttk.Label(itf, text="name/id:").pack(side="left")
        self.item_var = tk.StringVar()
        ttk.Entry(itf, textvariable=self.item_var, width=16).pack(side="left", padx=4)
        ttk.Label(itf, text="count:").pack(side="left")
        self.count_var = tk.StringVar(value="1")
        ttk.Entry(itf, textvariable=self.count_var, width=5).pack(side="left", padx=4)
        ttk.Button(itf, text="Preview", command=lambda: self._edit("item", False)).pack(side="left", padx=(8, 2))
        ttk.Button(itf, text="Apply", command=lambda: self._edit("item", True)).pack(side="left")

        # --- Equipment ---
        ef = ttk.LabelFrame(f, text="Equipment  (item 'empty' unequips)", padding=4)
        ef.pack(fill="x", pady=2)
        ttk.Label(ef, text="who:").pack(side="left")
        self.char_var = tk.StringVar()
        self.char_menu = ttk.OptionMenu(ef, self.char_var, "")
        self.char_menu.pack(side="left", padx=4)
        ttk.Label(ef, text="slot:").pack(side="left")
        self.slot_var = tk.StringVar(value=_si.EQUIP_SLOTS[0])
        ttk.OptionMenu(ef, self.slot_var, _si.EQUIP_SLOTS[0], *_si.EQUIP_SLOTS).pack(side="left", padx=4)
        ttk.Label(ef, text="item:").pack(side="left")
        self.eqitem_var = tk.StringVar()
        ttk.Entry(ef, textvariable=self.eqitem_var, width=14).pack(side="left", padx=4)
        ttk.Button(ef, text="Preview", command=lambda: self._edit("equip", False)).pack(side="left", padx=(8, 2))
        ttk.Button(ef, text="Apply", command=lambda: self._edit("equip", True)).pack(side="left")

        self.edit_txt = self._text(f)
        self.edit_txt.pack(fill="both", expand=True, pady=(4, 0))

    # ----- loading -----
    def _browse(self):
        f = filedialog.askopenfilename(
            title="Pick a save (SavedData_ww.dat or a Memoria extra-save)",
            initialdir=_save.default_save_dir() or "",
            filetypes=[("FF9 save", "*.dat"), ("All files", "*.*")])
        if f:
            self.pathvar.set(f)
            self._load(f)

    def _load(self, path, keep=None):
        try:
            self.targets = self._resolve_targets(path)
        except Exception as e:                            # noqa: BLE001 -- any decode failure -> a clear note
            self.targets, self.path = [], ""
            self.lst.delete(0, "end")
            self._render(self.inspect_txt, f"Could not read items/equipment from:\n{path}\n\n{e}\n\n"
                         "(Reading a SavedData_ww.dat container needs pycryptodome: py -m pip install "
                         "pycryptodome. A Memoria extra-save opens without it.)")
            self.status.config(text="no items/equipment decoded")
            return
        self.path = path
        self.lst.delete(0, "end")
        for label, _rep, _extra in self.targets:
            self.lst.insert("end", label)
        editable = sum(1 for _, _, x in self.targets if x is not None)
        self.status.config(text=f"{len(self.targets)} populated save(s); {editable} editable (have an extra file)")
        if self.targets:
            i = keep if (keep is not None and keep < len(self.targets)) else 0
            self.lst.selection_set(i)
            self._on_select()

    @staticmethod
    def _resolve_targets(path):
        """[(label, ItemReport|None, extra_path|None)] for ``path``. A Memoria extra-save -> one editable
        target; a SavedData_ww.dat container -> one per populated slot, editable when its extra file exists."""
        common = _si.load_extra_common(path)[0]
        if common is not None:                            # a Memoria extra-save, opened directly
            return [("Memoria extra-save", _si.report_from_common(common), path)]
        sv = _save.FF9Save.load(path)                     # the encrypted container (needs pycryptodome)
        out = []
        for s in sv.populated():
            extra = _save.extra_file_path(path, s.block)
            c = _si.load_extra_common(extra)[0] if (extra and os.path.isfile(extra)) else None
            lbl = _save._slot_label(s) + (" · extra" if c is not None else " · (no extra file)")
            out.append((lbl, _si.report_from_common(c) if c is not None else None,
                        extra if c is not None else None))
        if not out:
            raise ValueError("no populated save slots found in this file")
        return out

    def _selected(self):
        sel = self.lst.curselection()
        return sel[0] if sel else None

    def _target_extra(self):
        i = self._selected()
        return self.targets[i][2] if (i is not None and i < len(self.targets)) else None

    def _on_select(self):
        i = self._selected()
        if i is None:
            return
        label, rep, extra = self.targets[i]
        self._render(self.inspect_txt, f"{label}\n\n" + _si.render_report(rep))
        # refresh the edit panel to this slot
        names = [pc["name"] or f"slot {pc['slot_no']}" for pc in (rep.equipment if rep else [])]
        menu = self.char_menu["menu"]
        menu.delete(0, "end")
        for nm in names:
            menu.add_command(label=nm, command=lambda v=nm: self.char_var.set(v))
        if names and self.char_var.get() not in names:
            self.char_var.set(names[0])
        if extra is None:
            self.edit_target.config(text="Editing disabled — this slot has no Memoria extra file (the "
                                         "load-authoritative store). The main-block edit is a later step.")
            self.gil_var.set("")
        else:
            self.edit_target.config(text=f"Editing: {label}.  Writes the extra file; a timestamped .bak is "
                                         "made first. Reload the save in-game (no relaunch).")
            self.gil_var.set(str(rep.gil) if (rep and rep.gil is not None) else "")

    # ----- edit (write the save) -----
    def _edit(self, kind, apply):
        extra = self._target_extra()
        if not extra:
            self._out("Select an editable slot (one with a Memoria extra file) on the left first.")
            return
        try:
            if kind == "gil":
                val = int(self.gil_var.get())
                render = _si.render_gil_write
                preview = _si.set_gil(extra, val, dry_run=True)
                do = lambda: _si.set_gil(extra, val, dry_run=False)        # noqa: E731
            elif kind == "item":
                item, cnt = self.item_var.get().strip(), int(self.count_var.get())
                render = _si.render_item_write
                preview = _si.set_item(extra, item, cnt, dry_run=True)
                do = lambda: _si.set_item(extra, item, cnt, dry_run=False)  # noqa: E731
            else:
                char, slot, item = self.char_var.get(), self.slot_var.get(), self.eqitem_var.get().strip()
                render = _si.render_equip_write
                preview = _si.set_equip(extra, char, slot, item, dry_run=True)
                do = lambda: _si.set_equip(extra, char, slot, item, dry_run=False)  # noqa: E731
        except ValueError as e:
            self._out(f"Cannot apply:\n  {e}")
            return
        if not apply:
            self._out("PREVIEW (nothing written yet):\n" + render(preview))
            return
        if not messagebox.askyesno("Apply save edit?",
                                   "This edits your REAL save (a timestamped .bak is written first):\n\n"
                                   + render(preview) + "\n\nProceed?"):
            return
        try:
            res = do()
        except Exception as e:                            # noqa: BLE001 -- surface any write failure in-pane
            self._out(f"Write failed:\n  {e}")
            return
        self._out(render(res) + "\n\nReload the save in-game to see it (no relaunch needed).")
        self.status.config(text="save edited (backup written) — reload it in-game")
        self._load(self.path, keep=self._selected())      # refresh inspect against the just-written save


def main():
    smoke = "--smoke" in sys.argv
    root = tk.Tk()
    root.title("FF9 Map Kit — Item & Equipment")
    root.geometry("900x600")
    if smoke:
        root.withdraw()
    app = ItemsApp(root)
    if smoke:
        import tempfile
        from ff9mapkit import sjbinary as SJ
        from ff9mapkit import items as I

        def _int(v):
            return SJ.SJData(SJ.INT, v)

        def _extra_save(gil=500):
            root_c = SJ.SJClass()
            root_c.add("95000_Setting", SJ.SJClass())
            common = SJ.SJClass()
            players = SJ.SJArray()
            for nm, sn, eq in (("Zidane", 0, [1, 112, 88, 149, 255]), ("Vivi", 1, [70, 255, 255, 255, 255])):
                p = SJ.SJClass(); p.add("name", SJ.SJData(SJ.VALUE, nm))
                info = SJ.SJClass(); info.add("slot_no", _int(sn)); p.add("info", info)
                p.add("equip", SJ.SJArray([_int(x) for x in eq]))
                players.items.append(p)
            common.add("players", players)
            common.add("gil", _int(gil))
            common.add("items", SJ.SJArray([_pair(236, 7), _pair(238, 2)]))
            root_c.add("40000_Common", common)
            path = Path(tempfile.mktemp(suffix="_Memoria_0_2.dat"))
            path.write_bytes(SJ.dumps(root_c))
            return str(path)

        def _pair(i, c):
            e = SJ.SJClass(); e.add("id", _int(i)); e.add("count", _int(c)); return e

        sp = _extra_save(gil=500)
        app._load(sp)
        assert app.targets and app.targets[0][2] == sp, "extra-save opened + editable"
        app._on_select()
        assert "Gil: 500" in app.inspect_txt.get("1.0", "end"), "inspect renders gil"
        # gil preview + apply
        app.gil_var.set("123456")
        app._edit("gil", False)
        assert "DRY RUN" in app.edit_txt.get("1.0", "end"), "gil preview is a dry-run"
        # apply paths confirm via messagebox -> stub it to 'yes' for the smoke run
        messagebox.askyesno = lambda *a, **k: True
        app._edit("gil", True)
        assert _si.inspect(sp)[0][1].gil == 123456, "gil applied to the extra file"
        # item: add Potion->99 + a new Elixir
        app.item_var.set("Potion"); app.count_var.set("99"); app._edit("item", True)
        app.item_var.set("Elixir"); app.count_var.set("5"); app._edit("item", True)
        inv = {i: c for i, _, c in _si.inspect(sp)[0][1].inventory}
        assert inv.get(236) == 99 and inv.get(I.resolve("Elixir")) == 5, "items applied"
        # equip: Zidane weapon -> Mage Masher
        app.char_var.set("Zidane"); app.slot_var.set("weapon"); app.eqitem_var.set("MageMasher")
        app._edit("equip", True)
        eq = _si.inspect(sp)[0][1].equipment[0]["equip"]["weapon"]
        assert eq and eq[1] == "MageMasher", "equip applied"
        # a backup was written for each apply
        baks = list(Path(sp).parent.glob(Path(sp).name + ".bak.*"))
        assert baks, "a .bak backup was written"
        print(f"smoke ok: loaded {len(app.targets)} slot(s); gil/item/equip applied; {len(baks)} backup(s)")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
