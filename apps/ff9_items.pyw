#!/usr/bin/env pythonw
"""FF9 Map Kit -- Item & Equipment save editor (inspect / EDIT a save's gil, inventory, equipment).

Double-click to launch (windowless via pythonw), or:  py apps\\ff9_items.pyw

The item/equip companion to the Story State console -- a SEPARATE surface (it touches only
:mod:`ff9mapkit.save_items`, never the story-state core; project-ff9-branch-lanes rule 3). It reads + edits both
the Memoria EXTRA save file (``SavedData_ww_Memoria_*.dat``, the **load-authoritative** store) and the encrypted
MAIN block, so an edit here changes what the game loads -- no relaunch, just reload the save.

  * Inspect -- the decoded gil / inventory / equipment of each populated slot (``save_items.inspect``).
  * Edit    -- set gil, set/remove an item by name, or change a character's equipment -- each PREVIEWable
               (dry-run) and Apply backup-guarded (a timestamped .bak is written first; the write is atomic and
               re-read to confirm). A Memoria slot DUAL-WRITES the main block + the extra mirror; a **vanilla
               (no-extra) save edits its encrypted main block directly** -- gil, items AND equipment (equipment
               by old-format slot; slots 5-7 are shared by Quina/Eiko/Amarant + their story stand-ins).

Pick a SavedData_ww.dat (enumerates its populated slots; the container read needs pycryptodome) or a Memoria
extra-save directly (no crypto). Provenance-clean: it touches only the user's own save, only on Apply.
Standalone, or embedded as a tab.
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
        self.targets = []        # [{label, report: ItemReport|None, extra, container, block}] per populated slot
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

        # --- Stats (permanent growth: writes basis + the equipment bonus accumulator) ---
        sf = ttk.LabelFrame(f, text="Stats  (permanent: writes basis + the equipment bonus)", padding=4)
        sf.pack(fill="x", pady=2)
        ttk.Label(sf, text="who:").pack(side="left")
        self.stat_char_var = tk.StringVar()
        self.stat_char_menu = ttk.OptionMenu(sf, self.stat_char_var, "")
        self.stat_char_menu.pack(side="left", padx=4)
        ttk.Label(sf, text="stat:").pack(side="left")
        self.stat_kind_var = tk.StringVar(value="Strength")
        ttk.OptionMenu(sf, self.stat_kind_var, "Strength", "Speed", "Strength", "Magic", "Spirit").pack(side="left", padx=4)
        ttk.Label(sf, text="value:").pack(side="left")
        self.stat_val_var = tk.StringVar(value="50")
        ttk.Entry(sf, textvariable=self.stat_val_var, width=5).pack(side="left", padx=4)
        ttk.Button(sf, text="Preview", command=lambda: self._edit_stat(False)).pack(side="left", padx=(8, 2))
        ttk.Button(sf, text="Apply", command=lambda: self._edit_stat(True)).pack(side="left")

        # --- Key items ---
        kf = ttk.LabelFrame(f, text="Key items  (give / remove an important item by name)", padding=4)
        kf.pack(fill="x", pady=2)
        ttk.Label(kf, text="name/id:").pack(side="left")
        self.ki_var = tk.StringVar()
        ttk.Entry(kf, textvariable=self.ki_var, width=18).pack(side="left", padx=4)
        ttk.Button(kf, text="Preview", command=lambda: self._edit_keyitem(False, True)).pack(side="left", padx=(8, 2))
        ttk.Button(kf, text="Give", command=lambda: self._edit_keyitem(True, True)).pack(side="left", padx=2)
        ttk.Button(kf, text="Remove", command=lambda: self._edit_keyitem(True, False)).pack(side="left")

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
        for t in self.targets:
            self.lst.insert("end", t["label"])
        editable = sum(1 for t in self.targets if t["report"] is not None)
        self.status.config(text=f"{len(self.targets)} populated save(s); {editable} editable "
                                "(gil, items, equipment)")
        if self.targets:
            i = keep if (keep is not None and keep < len(self.targets)) else 0
            self.lst.selection_set(i)
            self._on_select()

    @staticmethod
    def _resolve_targets(path):
        """A list of target dicts ``{label, report, extra, container, block}`` for ``path``. A Memoria extra-save
        opens as one extra-only target (no container). A SavedData_ww.dat container yields one per populated slot:
        a Memoria slot reads/edits its extra (dual-written with the main block); a VANILLA slot (no extra) reads
        + edits the encrypted MAIN block directly. Gil, items AND equipment are editable on every slot (vanilla
        equipment is by old-format slot)."""
        common = _si.load_extra_common(path)[0]
        if common is not None:                            # a Memoria extra-save, opened directly
            return [{"label": "Memoria extra-save", "report": _si.report_from_common(common),
                     "extra": path, "container": None, "block": None}]
        sv = _save.FF9Save.load(path)                     # the encrypted container (needs pycryptodome)
        out = []
        for s in sv.populated():
            extra = _save.extra_file_path(path, s.block)
            has_extra = bool(extra and os.path.isfile(extra))
            if has_extra:
                rep = _si.report_from_common(_si.load_extra_common(extra)[0])
                lbl = _save._slot_label(s) + " · extra"
            else:
                rep = _si.decode_main_block(path, s.block)
                lbl = _save._slot_label(s) + (" · main (vanilla)" if rep is not None else " · (unreadable)")
            out.append({"label": lbl, "report": rep, "extra": extra if has_extra else None,
                        "container": path, "block": s.block})
        if not out:
            raise ValueError("no populated save slots found in this file")
        return out

    def _selected(self):
        sel = self.lst.curselection()
        return sel[0] if sel else None

    def _target(self):
        i = self._selected()
        return self.targets[i] if (i is not None and i < len(self.targets)) else None

    def _on_select(self):
        t = self._target()
        if t is None:
            return
        rep, extra, container = t["report"], t["extra"], t["container"]
        self._render(self.inspect_txt, f"{t['label']}\n\n" + _si.render_report(rep))
        # refresh the character dropdowns (equip + stats) (extra slots = 12 PCs; vanilla = the 9 old-format slots)
        names = [pc["name"] or f"slot {pc['slot_no']}" for pc in (rep.equipment if rep else [])]
        for var, menuw in ((self.char_var, self.char_menu), (self.stat_char_var, self.stat_char_menu)):
            menu = menuw["menu"]
            menu.delete(0, "end")
            for nm in names:
                menu.add_command(label=nm, command=lambda v=nm, vr=var: vr.set(v))
            if names and var.get() not in names:
                var.set(names[0])
        editable = rep is not None and (container is not None or extra is not None)
        if not editable:
            self.edit_target.config(text="Editing disabled — this slot could not be decoded.")
            self.gil_var.set("")
        elif extra is None:                                # a vanilla save: gil + items + equip via the main block
            self.edit_target.config(text=f"Editing: {t['label']} (vanilla save — main block). Gil, items and "
                                         "equipment (by old-slot; slots 5-7 are shared). The whole save is backed "
                                         "up first.")
            self.gil_var.set(str(rep.gil) if rep.gil is not None else "")
        else:                                              # a Memoria save: gil/items dual-written, equip via extra
            where = "the extra file" if container is None else "the main block + the extra mirror"
            self.edit_target.config(text=f"Editing: {t['label']}. Writes {where}; a timestamped .bak is made "
                                         "first. Reload the save in-game (no relaunch).")
            self.gil_var.set(str(rep.gil) if rep.gil is not None else "")

    @staticmethod
    def _plan_gil(val, extra, container, block):
        """(render, preview, do) for a gil edit -- dual-write (main + extra mirror) on a container slot
        (handles a vanilla save), or extra-only on an extra-file-direct target."""
        if container is not None:
            return (_si.render_gil_dual, _si.set_gil_in_save(container, block, val, dry_run=True),
                    lambda: _si.set_gil_in_save(container, block, val, dry_run=False))
        return (_si.render_gil_write, _si.set_gil(extra, val, dry_run=True),
                lambda: _si.set_gil(extra, val, dry_run=False))

    @staticmethod
    def _plan_item(item, cnt, extra, container, block):
        if container is not None:
            return (_si.render_item_dual, _si.set_item_in_save(container, block, item, cnt, dry_run=True),
                    lambda: _si.set_item_in_save(container, block, item, cnt, dry_run=False))
        return (_si.render_item_write, _si.set_item(extra, item, cnt, dry_run=True),
                lambda: _si.set_item(extra, item, cnt, dry_run=False))

    @staticmethod
    def _plan_equip(char, slot, item, extra, container, block):
        if container is not None:                          # dual-write (main + extra mirror); main edits a vanilla slot
            return (_si.render_equip_dual, _si.set_equip_in_save(container, block, char, slot, item, dry_run=True),
                    lambda: _si.set_equip_in_save(container, block, char, slot, item, dry_run=False))
        return (_si.render_equip_write, _si.set_equip(extra, char, slot, item, dry_run=True),
                lambda: _si.set_equip(extra, char, slot, item, dry_run=False))

    # ----- edit (write the save) -----
    def _edit(self, kind, apply):
        t = self._target()
        if t is None or t["report"] is None:
            self._out("Select a decodable slot on the left first.")
            return
        extra, container, block = t["extra"], t["container"], t["block"]
        try:
            if kind == "gil":
                val = int(self.gil_var.get())
                render, preview, do = self._plan_gil(val, extra, container, block)
            elif kind == "item":
                item, cnt = self.item_var.get().strip(), int(self.count_var.get())
                render, preview, do = self._plan_item(item, cnt, extra, container, block)
            else:
                char, slot, item = self.char_var.get(), self.slot_var.get(), self.eqitem_var.get().strip()
                render, preview, do = self._plan_equip(char, slot, item, extra, container, block)
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

    def _edit_keyitem(self, apply, obtained):
        """Give (obtained=True) / remove (obtained=False) a key item -- dual-write on a container slot (handles
        a vanilla save's main-block rareItems), or extra-only on an extra-file-direct target."""
        t = self._target()
        if t is None or t["report"] is None:
            self._out("Select a decodable slot on the left first.")
            return
        extra, container, block = t["extra"], t["container"], t["block"]
        name = self.ki_var.get().strip()
        try:
            if container is not None:
                render = _si.render_keyitem_dual
                preview = _si.set_keyitem_in_save(container, block, name, obtained=obtained, dry_run=True)
                do = lambda: _si.set_keyitem_in_save(container, block, name, obtained=obtained, dry_run=False)  # noqa: E731
            elif extra is not None:
                render = _si.render_keyitem_write
                preview = _si.set_keyitem_extra(extra, name, obtained=obtained, dry_run=True)
                do = lambda: _si.set_keyitem_extra(extra, name, obtained=obtained, dry_run=False)  # noqa: E731
            else:
                self._out("Select an editable slot first.")
                return
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
        except Exception as e:                            # noqa: BLE001
            self._out(f"Write failed:\n  {e}")
            return
        self._out(render(res) + "\n\nReload the save in-game to see it (no relaunch needed).")
        self.status.config(text="save edited (backup written) — reload it in-game")
        self._load(self.path, keep=self._selected())

    def _edit_stat(self, apply):
        """Set a character's permanent growth stat (basis + the equipment bonus) -- dual-write on a container slot
        (handles a vanilla save's main block), extra-only on an extra-file-direct target."""
        t = self._target()
        if t is None or t["report"] is None:
            self._out("Select a decodable slot on the left first.")
            return
        extra, container, block = t["extra"], t["container"], t["block"]
        char, stat = self.stat_char_var.get(), self.stat_kind_var.get()
        try:
            val = int(self.stat_val_var.get())
            if container is not None:
                render = _si.render_stat_dual
                preview = _si.set_stat_in_save(container, block, char, stat, val, dry_run=True)
                do = lambda: _si.set_stat_in_save(container, block, char, stat, val, dry_run=False)  # noqa: E731
            elif extra is not None:
                render = _si.render_stat_write
                preview = _si.set_stat_extra(extra, char, stat, val, dry_run=True)
                do = lambda: _si.set_stat_extra(extra, char, stat, val, dry_run=False)  # noqa: E731
            else:
                self._out("Select an editable slot first.")
                return
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
        except Exception as e:                            # noqa: BLE001
            self._out(f"Write failed:\n  {e}")
            return
        self._out(render(res) + "\n\nReload the save in-game to see it (no relaunch needed).")
        self.status.config(text="save edited (backup written) — reload it in-game")
        self._load(self.path, keep=self._selected())


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
                basis = SJ.SJClass()
                for k, v in (("dex", 24), ("str", 27), ("mgc", 23), ("wpr", 25)):
                    basis.add(k, _int(v))
                p.add("basis", basis)
                bonus = SJ.SJClass()
                for k, v in (("dex", 5), ("str", 77), ("mgc", 45), ("wpr", 30)):
                    bonus.add(k, _int(v))
                p.add("bonus", bonus)
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
        assert app.targets and app.targets[0]["extra"] == sp, "extra-save opened + editable"
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
        # stat: set Zidane Strength -> 99 (writes basis + bonus)
        app.stat_char_var.set("Zidane"); app.stat_kind_var.set("Strength"); app.stat_val_var.set("99")
        app._edit_stat(True)
        st = {s["name"]: s["stats"] for s in _si.read_stats(_si.load_extra_common(sp)[0])}
        assert st["Zidane"]["Strength"] == 99, "stat (basis) applied via GUI"
        baks = list(Path(sp).parent.glob(Path(sp).name + ".bak.*"))
        assert baks, "a .bak backup was written"

        # --- a VANILLA (no-extra) container: gil + items + equip all edit the MAIN block ---
        vanilla_ok = "skipped (no pycryptodome)"
        try:
            import base64
            from Crypto.Cipher import AES  # noqa: PLC0415
            from ff9mapkit import save as SaveMod
            key, iv = SaveMod._key_iv()
            pt = bytearray(SaveMod.SAVE_BLOCK_SIZE); pt[0:4] = b"SAVE"
            geg = bytearray(2048); geg[0], geg[1] = 6000 & 0xFF, 6000 >> 8     # so populated() recognises the block
            b64 = base64.b64encode(bytes(geg)); pt[23:23 + len(b64)] = b64
            pt[_si.MAIN_GIL_OFF:_si.MAIN_GIL_OFF + 4] = (500).to_bytes(4, "little")
            pt[_si.MAIN_ITEMS_OFF], pt[_si.MAIN_ITEMS_OFF + 1] = 7, 236        # Potion x7; rest count-0 padding
            data = bytearray(SaveMod.BASE_SAVE_BLOCK_OFFSET + SaveMod.SAVE_BLOCK_SIZE * 2)
            lo = SaveMod.BASE_SAVE_BLOCK_OFFSET + SaveMod.SAVE_BLOCK_SIZE
            data[lo:lo + SaveMod.SAVE_BLOCK_SIZE] = AES.new(key, AES.MODE_CBC, iv).encrypt(bytes(pt))
            cdir = Path(tempfile.mkdtemp())
            cont = cdir / "SavedData_ww.dat"; cont.write_bytes(bytes(data))
            app._load(str(cont))
            t = app.targets[0]
            assert t["container"] and t["extra"] is None and "vanilla" in t["label"], "vanilla slot detected"
            app.lst.selection_set(0); app._on_select()
            app.gil_var.set("314159"); app._edit("gil", True)
            assert _si.decode_main_block(str(cont), 1).gil == 314159, "main-block gil edited via GUI"
            app.item_var.set("Ether"); app.count_var.set("4"); app._edit("item", True)
            assert any(i == I.resolve("Ether") for i, _, _ in _si.decode_main_block(str(cont), 1).inventory), \
                "main-block item added via GUI"
            app.char_var.set("Zidane"); app.slot_var.set("weapon"); app.eqitem_var.set("MageMasher")
            app._edit("equip", True)
            zeq = _si.decode_main_block(str(cont), 1).equipment[0]["equip"]["weapon"]
            assert zeq and zeq[1] == "MageMasher", "main-block equip edited via GUI (vanilla)"
            app.ki_var.set("7"); app._edit_keyitem(True, True)                 # give key item id 7 via the GUI
            assert any(i == 7 for i, _, ob, us in _si.decode_main_block(str(cont), 1).keyitems if ob), \
                "main-block key item given via GUI (vanilla)"
            app.stat_char_var.set("Zidane"); app.stat_kind_var.set("Strength"); app.stat_val_var.set("99")
            app._edit_stat(True)                                               # set a stat via the GUI (vanilla)
            zst = {s["name"]: s["stats"] for s in _si.decode_main_block(str(cont), 1).stats}
            assert zst["Zidane"]["Strength"] == 99, "main-block stat edited via GUI (vanilla)"
            vanilla_ok = "main-block gil+item+equip+keyitem+stat edited"
        except ImportError:
            pass
        print(f"smoke ok: extra slot gil/item/equip/stat applied ({len(baks)} bak); vanilla {vanilla_ok}")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
