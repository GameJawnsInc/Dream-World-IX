"""The FF9 Map Kit field-logic editor (Tkinter UI).

A friendly form-based front-end so authors edit a field's LOGIC (dialogue, events, story flags,
encounters, music, cutscenes) without hand-writing TOML. Spatial placement (camera / walkmesh /
positions / zones) stays in Blender; this edits the ``<field>.field.toml`` and never touches a sibling
``<field>.scene.toml``.

All the non-UI logic lives in the tk-free :mod:`.model` (load/save/serialize) and :mod:`.forms`
(specs/parsers), which are unit-tested; this file is the thin Tk wiring over them. Launch with
``ff9mapkit edit [field.toml]``.
"""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from . import forms
from .model import FieldDoc, protected_reason

# single-table logic sections and their specs; the rest are arrays-of-tables.
SINGLE_SPECS = {"field": forms.FIELD_SPEC, "encounter": forms.ENCOUNTER_SPEC,
                "music": forms.MUSIC_SPEC, "dialogue": forms.DIALOGUE_SPEC}
LIST_SPECS = {"npc": forms.NPC_SPEC, "gateway": forms.GATEWAY_SPEC, "event": forms.EVENT_SPEC,
              "marker": forms.MARKER_SPEC}
LIST_LABELS = {"npc": "NPCs", "gateway": "Gateways", "event": "Events", "marker": "Markers"}
OPTIONAL_SINGLES = ("encounter", "music", "cutscene", "dialogue")     # add/remove-able


def _find_tool(name):
    """Locate a dev tool script (deploy_field.py / revert_deploy.py) relative to the repo, or None.
    Only present in the dev checkout; a distributed kit just won't show the in-game test buttons."""
    here = Path(__file__).resolve()
    for base in here.parents:
        for cand in (base / "tools" / name, base / "tools" / "scroll_out" / name):
            if cand.is_file():
                return cand
    return None


class EditorApp:
    def __init__(self, root, path=None):
        self.root = root
        self.doc: FieldDoc | None = None
        self.active = None                 # {"type":..., "index":...} currently-edited node
        self.getters = {}                  # key -> widget reader for the active form
        self.step_widgets = None           # cutscene step editor state
        self.busy = False
        self.deploy = _find_tool("deploy_field.py")
        self.revert = _find_tool("revert_deploy.py")
        self.q: queue.Queue = queue.Queue()

        root.title("FF9 Map Kit - Field Editor")
        root.minsize(900, 560)
        self._build_toolbar()
        panes = ttk.PanedWindow(root, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(panes)
        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.tree.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        sb.pack(fill="y", side="right")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        panes.add(left, weight=1)
        self.form = ttk.Frame(panes)
        panes.add(self.form, weight=3)

        self.status = scrolledtext.ScrolledText(root, height=7, state="disabled", wrap="word")
        self.status.pack(fill="x", padx=6, pady=(0, 6))
        self._log("Open a .field.toml, or New. Edit logic on the right; placement stays in Blender. "
                  "New here? Click Help for a 30-second tour.")
        root.after(120, self._drain)
        if path:
            self._load(Path(path))
        else:
            self._show_welcome()

    # --------------------------------------------------------------- toolbar
    def _build_toolbar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(bar, text="Open", command=self.on_open).pack(side="left")
        ttk.Button(bar, text="New", command=self.on_new).pack(side="left", padx=(6, 0))
        self.btn_save = ttk.Button(bar, text="Save", command=self.on_save)
        self.btn_save.pack(side="left", padx=(6, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        self.btn_check = ttk.Button(bar, text="Check logic", command=self.on_check)
        self.btn_check.pack(side="left")
        self.btn_build = ttk.Button(bar, text="Build to game", command=self.on_build_game)
        self.btn_build.pack(side="left", padx=(6, 0))
        if self.deploy:
            self.btn_test = ttk.Button(bar, text="Build & Test (4003)", command=self.on_test)
            self.btn_test.pack(side="left", padx=(6, 0))
        if self.revert:
            ttk.Button(bar, text="Revert test", command=self.on_revert).pack(side="left", padx=(6, 0))
        self.title_lbl = ttk.Label(bar, text="(no file)")
        self.title_lbl.pack(side="right")
        ttk.Button(bar, text="Help", command=self.on_help).pack(side="right", padx=(0, 8))

    def on_help(self):
        messagebox.showinfo(
            "FF9 Map Kit - Field Editor",
            "WHAT THIS IS\n"
            "A form-based editor for a field's LOGIC: dialogue, NPCs, events, story flags, "
            "encounters, music, and cutscenes. No hand-writing TOML.\n\n"
            "WHERE PLACEMENT LIVES\n"
            "The camera, the walkmesh, and where things stand are SPATIAL -- you set those in "
            "Blender (the FF9 Map Kit add-on). This editor only touches the logic file "
            "(<name>.field.toml) and never your Blender scene (<name>.scene.toml).\n\n"
            "GETTING A FILE TO OPEN\n"
            "  - ff9mapkit new MY_ROOM      scaffold a blank room\n"
            "  - ff9mapkit import <field>   fork a real FF9 field (add --editable to repaint it)\n"
            "  - the Blender add-on's Export\n\n"
            "WORKFLOW\n"
            "Open -> pick a section on the left -> fill the form -> Save -> Check logic -> Build.\n"
            "A section marked (+) can be added; NPCs / Gateways / Events / Markers each hold a list.\n\n"
            "SECTIONS\n"
            "  - NPCs / Gateways / Events: people, exits, and walk-in triggers.\n"
            "  - Markers: named floor points a cutscene can walk to by name.\n"
            "  - Cutscene: ordered steps (control locks). An 'actor' NPC can walk / emote.\n"
            "  - Dialogue: auto-wrap width for long lines. Encounter / Music: battles + BGM.\n\n"
            "CUTSCENE STEPS\n"
            "  - walk/teleport: a marker name, @player, or \"x, z\" (walk auto-routes around things).\n"
            "  - path: a route, \"a; b; c\".   animation: a gesture name (glad) or id.   say: a line.\n\n"
            "A FEW FIELDS\n"
            "  - Field ID: any unique number >= 4000.\n"
            "  - Area: must be >= 10 (lower areas don't render).\n"
            "  - Text block: leave at 1073 unless you know otherwise.\n"
            "  - NPC preset: vivi or zidane is the easy path (a custom model also needs anims set "
            "in the .toml).")

    # --------------------------------------------------------------- logging
    def _log(self, msg):
        self.status.configure(state="normal")
        self.status.insert("end", str(msg).rstrip() + "\n")
        self.status.see("end")
        self.status.configure(state="disabled")

    def post(self, msg):
        self.q.put(msg)

    def _drain(self):
        try:
            while True:
                self._log(self.q.get_nowait())
        except queue.Empty:
            pass
        self.root.after(120, self._drain)

    # --------------------------------------------------------------- file io
    def on_open(self):
        f = filedialog.askopenfilename(title="Open field.toml",
                                       filetypes=[("Field project", "*.field.toml"),
                                                  ("TOML", "*.toml"), ("All files", "*.*")])
        if f:
            self._load(Path(f))

    def _load(self, path):
        try:
            self.doc = FieldDoc.load(path)
        except Exception as e:               # noqa: BLE001
            messagebox.showerror("Open failed", f"{path}\n\n{e}")
            return
        self.active = None
        split = " (+ scene.toml)" if self.doc.scene_data is not None else ""
        self.title_lbl.configure(text=path.name + split)
        self._log(f"opened {path.name}{split}")
        self._refresh_tree(reselect="field")     # land on the Field form (clears the welcome)

    def on_new(self):
        f = filedialog.asksaveasfilename(title="New field.toml", defaultextension=".field.toml",
                                         filetypes=[("Field project", "*.field.toml")])
        if not f:
            return
        p = Path(f)
        reason = protected_reason(p)
        if reason:
            messagebox.showerror("Can't create here", f"{p}\n\n{reason}.\n\nPick a folder of your own.")
            return
        name = p.name[:-len(".field.toml")] if p.name.endswith(".field.toml") else p.stem
        self.doc = FieldDoc.new(p, name=name.upper())
        self.active = None
        self.title_lbl.configure(text=p.name + " (new, unsaved)")
        self._refresh_tree(reselect="field")     # land on the Field form (clears the welcome)
        self._log(f"new field {name.upper()} -- fill in [field], add content, then Save.")

    def on_save(self):
        if not self._commit_active():
            return False
        if self.doc is None:
            return False
        reason = protected_reason(self.doc.path)
        if reason:
            messagebox.showerror("Can't save here", f"{self.doc.path}\n\n{reason}.\n\n"
                                 "Save a copy in a folder of your own first.")
            return False
        try:
            self._cleanup_empty()
            self.doc.save()
            self._log(f"saved {self.doc.path.name}")
        except Exception as e:               # noqa: BLE001
            messagebox.showerror("Save failed", str(e))
            return False
        return True

    def _cleanup_empty(self):
        """Drop empty array sections so we don't write ``npc = []`` etc."""
        for key in list(self.doc.data.keys()):
            v = self.doc.data[key]
            if isinstance(v, list) and not v:
                self.doc.data.pop(key)

    # --------------------------------------------------------------- tree
    def _refresh_tree(self, reselect=None):
        self.tree.delete(*self.tree.get_children())
        if self.doc is None:
            return
        self.tree.insert("", "end", iid="field", text="Field")
        self.tree.insert("", "end", iid="camera", text="Camera (Blender)")
        for key in ("dialogue", "encounter", "music", "cutscene"):
            present = key in self.doc.data
            label = {"dialogue": "Dialogue", "encounter": "Encounter",
                     "music": "Music", "cutscene": "Cutscene"}[key]
            self.tree.insert("", "end", iid=key, text=label + ("" if present else "  (+)"))
        for key in ("npc", "gateway", "event", "marker"):
            parent = self.tree.insert("", "end", iid=key, text=f"{LIST_LABELS[key]}  (+)", open=True)
            for i, e in enumerate(self.doc.data.get(key, [])):
                nm = e.get("name") or f"#{i}"
                self.tree.insert(parent, "end", iid=f"{key}:{i}", text=nm)
        if reselect and self.tree.exists(reselect):
            self.tree.selection_set(reselect)
            self.tree.see(reselect)

    def _on_select(self, _evt):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        if self.active and not self._commit_active():
            return                              # a parse error -- stay put
        self._show(iid)

    # --------------------------------------------------------------- forms
    def _clear_form(self):
        for w in self.form.winfo_children():
            w.destroy()
        self.getters = {}
        self.step_widgets = None
        self.active = None

    def _show_welcome(self):
        """Empty-state guidance shown before any file is open (newcomer's first screen)."""
        self._clear_form()
        msg = (
            "FF9 Map Kit - Field Editor\n\n"
            "This edits a field's LOGIC: dialogue, NPCs, events, story flags, encounters, music, and "
            "cutscenes. The SPATIAL side -- the camera, the walkmesh, and where things stand -- is "
            "authored in Blender; this editor never changes it.\n\n"
            "Open a .field.toml to start. You can get one from:\n"
            "    - ff9mapkit new MY_ROOM       a blank room\n"
            "    - ff9mapkit import <field>    fork a real FF9 field\n"
            "    - the Blender add-on's Export\n\n"
            "Then: pick a section on the left, fill in the form, Save, Check logic, Build.\n\n"
            "On the left, a section marked (+) is one you can add (Encounter, Music, Cutscene) or add "
            "items to (NPCs, Gateways, Events). Click Help in the toolbar any time."
        )
        ttk.Label(self.form, text=msg, justify="left", wraplength=560).pack(anchor="nw", padx=14, pady=14)

    def _show(self, iid):
        self._clear_form()
        if iid == "field":
            self._show_single("field", forms.FIELD_SPEC, "Field")
        elif iid == "camera":
            self._show_camera()
        elif iid in ("encounter", "music", "dialogue"):
            self._show_optional_single(iid, SINGLE_SPECS[iid], iid.capitalize())
        elif iid == "cutscene":
            self._show_cutscene()
        elif iid in LIST_SPECS:
            self._show_list_parent(iid)
        elif ":" in iid:
            kind, idx = iid.split(":")
            self._show_entity(kind, int(idx))

    def _header(self, text, key=None):
        ttk.Label(self.form, text=text, font=("", 11, "bold")).pack(anchor="w", padx=8, pady=(8, 2))
        note = forms.SECTION_HELP.get(key) if key else None
        if note:
            ttk.Label(self.form, text=note, foreground="#567", wraplength=580, justify="left").pack(
                anchor="w", padx=10, pady=(0, 4))

    def _form_grid(self):
        g = ttk.Frame(self.form)
        g.pack(fill="x", padx=8, pady=4)
        return g

    def _render_spec(self, parent, spec, values):
        getters = {}
        for r, f in enumerate(spec):
            ttk.Label(parent, text=f.label + ":").grid(row=r, column=0, sticky="ne", padx=4, pady=2)
            if f.kind == forms.BOOL:
                var = tk.BooleanVar(value=bool(values.get(f.key, f.default)))
                ttk.Checkbutton(parent, variable=var).grid(row=r, column=1, sticky="w")
            elif f.kind == forms.PRESET:
                var = tk.StringVar(value=str(values.get(f.key, "") or ""))
                ttk.Combobox(parent, textvariable=var, values=forms.PRESETS).grid(
                    row=r, column=1, sticky="we")
            else:
                var = tk.StringVar(value=str(values.get(f.key, "") or ""))
                ttk.Entry(parent, textvariable=var).grid(row=r, column=1, sticky="we")
            getters[f.key] = var.get
            if f.help:
                ttk.Label(parent, text=f.help, foreground="#777").grid(row=r, column=2,
                                                                       sticky="w", padx=6)
        parent.columnconfigure(1, weight=1)
        return getters

    def _show_single(self, key, spec, title):
        self._header(title, key)
        values = forms.entity_to_values(spec, self.doc.data.get(key, {}))
        self.getters = self._render_spec(self._form_grid(), spec, values)
        self.active = {"type": key, "section": key}

    def _show_optional_single(self, key, spec, title):
        if key not in self.doc.data:
            self._header(title + " (not set)", key)
            ttk.Label(self.form, text=f"No {title.lower()} on this field.").pack(anchor="w", padx=10)
            ttk.Button(self.form, text=f"Add {title}",
                       command=lambda: self._add_single(key)).pack(anchor="w", padx=10, pady=6)
            self.active = None
            return
        self._header(title, key)
        values = forms.entity_to_values(spec, self.doc.data.get(key, {}))
        self.getters = self._render_spec(self._form_grid(), spec, values)
        self.active = {"type": key, "section": key}
        ttk.Button(self.form, text=f"Remove {title}",
                   command=lambda: self._remove_single(key)).pack(anchor="w", padx=10, pady=8)

    def _add_single(self, key):
        self.doc.data.setdefault(key, {} if key != "cutscene" else {"steps": []})
        self._refresh_tree(reselect=key)
        self._show(key)

    def _remove_single(self, key):
        self.active = None
        self.doc.remove_section(key)
        self._refresh_tree(reselect=key)
        self._show(key)

    def _show_list_parent(self, kind):
        self._header(LIST_LABELS[kind], kind)
        ttk.Button(self.form, text=f"Add {kind}", command=lambda: self._add_entity(kind)).pack(
            anchor="w", padx=10, pady=6)
        n = len(self.doc.data.get(kind, []))
        ttk.Label(self.form, text=f"{n} {kind}(s). Select one on the left to edit, or Add.").pack(
            anchor="w", padx=10)
        self.active = None

    def _add_entity(self, kind):
        defaults = {"npc": {"name": "NPC", "preset": "vivi", "dialogue": "..."},
                    "gateway": {"name": "door", "to": 100, "entrance": 0},
                    "event": {"name": "event", "message": "..."},
                    "marker": {"name": "spot", "pos": [0, 0]}}[kind]
        lst = self.doc.list_section(kind)
        lst.append(dict(defaults))
        self._refresh_tree(reselect=f"{kind}:{len(lst) - 1}")
        self._show_entity(kind, len(lst) - 1)

    def _show_entity(self, kind, idx):
        spec = LIST_SPECS[kind]
        lst = self.doc.data.get(kind, [])
        if idx >= len(lst):
            return
        entity = lst[idx]
        self._header(f"{LIST_LABELS[kind][:-1]}: {entity.get('name') or '#' + str(idx)}", kind)
        self.getters = self._render_spec(self._form_grid(), spec, forms.entity_to_values(spec, entity))
        self.active = {"type": kind, "section": kind, "index": idx}
        # show the Blender-placed spatial value (read-only hint) if it's in the scene file
        scene_e = self.doc.scene_entities(kind).get(entity.get("name", ""))
        if scene_e:
            spatial = scene_e.get("pos") or scene_e.get("zone")
            ttk.Label(self.form, text=f"placed in Blender: {spatial}", foreground="#3a7").pack(
                anchor="w", padx=10, pady=(2, 0))
        ttk.Button(self.form, text=f"Delete this {kind}",
                   command=lambda: self._delete_entity(kind, idx)).pack(anchor="w", padx=10, pady=8)

    def _delete_entity(self, kind, idx):
        self.active = None
        lst = self.doc.data.get(kind, [])
        if idx < len(lst):
            lst.pop(idx)
        self._refresh_tree(reselect=kind)
        self._show(kind)

    def _show_camera(self):
        self._header("Camera & placement", "camera")
        msg = ("Camera, walkmesh, layers, and entity positions/zones are SPATIAL — author them in "
               "Blender (FF9 Map Kit add-on), which writes the sibling scene.toml. This editor owns "
               "the logic only.")
        ttk.Label(self.form, text=msg, wraplength=520, justify="left").pack(anchor="w", padx=10, pady=8)
        cam = (self.doc.merged() if self.doc else {}).get("camera", {})
        if cam:
            ttk.Label(self.form, text=f"current: {cam}", foreground="#777", wraplength=520,
                      justify="left").pack(anchor="w", padx=10)
        self.active = None

    # --------------------------------------------------------------- cutscene (steps)
    def _show_cutscene(self):
        if "cutscene" not in self.doc.data:
            self._show_optional_single("cutscene", forms.CUTSCENE_SPEC, "Cutscene")
            return
        self._header("Cutscene", "cutscene")
        cs = self.doc.data["cutscene"]
        self.getters = self._render_spec(self._form_grid(), forms.CUTSCENE_SPEC,
                                         forms.entity_to_values(forms.CUTSCENE_SPEC, cs))
        # --- the step list ---
        ttk.Label(self.form, text="Steps (run in order; control is locked):",
                  font=("", 10, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        body = ttk.Frame(self.form)
        body.pack(fill="both", expand=True, padx=10)
        lb = tk.Listbox(body, height=8, exportselection=False)
        lb.pack(side="left", fill="both", expand=True)
        for st in cs.get("steps", []):
            lb.insert("end", forms.step_summary(st))
        side = ttk.Frame(body)
        side.pack(side="left", fill="y", padx=(8, 0))
        kind = tk.StringVar(value="say")
        ttk.Label(side, text="Type:").pack(anchor="w")
        ttk.Combobox(side, textvariable=kind, values=list(forms.STEP_KIND),
                     state="readonly", width=14).pack(anchor="w")
        val = tk.StringVar()
        ttk.Label(side, text="Value:").pack(anchor="w", pady=(6, 0))
        ttk.Entry(side, textvariable=val, width=16).pack(anchor="w")
        hint = ttk.Label(side, text=forms.STEP_HELP.get(kind.get(), ""), foreground="#567",
                         wraplength=150, justify="left")
        hint.pack(anchor="w", pady=(3, 0))
        kind.trace_add("write", lambda *_: hint.configure(text=forms.STEP_HELP.get(kind.get(), "")))
        ttk.Label(side, text="(walk/path/teleport/animation/\nturn/face need an actor)",
                  foreground="#999", justify="left").pack(anchor="w", pady=(4, 0))
        self.step_widgets = {"listbox": lb, "kind": kind, "val": val}
        ttk.Button(side, text="Add / Update", command=self._step_add).pack(fill="x", pady=(8, 2))
        ttk.Button(side, text="Remove", command=self._step_remove).pack(fill="x", pady=2)
        ttk.Button(side, text="Up", command=lambda: self._step_move(-1)).pack(fill="x", pady=2)
        ttk.Button(side, text="Down", command=lambda: self._step_move(1)).pack(fill="x", pady=2)
        lb.bind("<<ListboxSelect>>", self._step_selected)
        ttk.Button(self.form, text="Remove Cutscene",
                   command=lambda: self._remove_single("cutscene")).pack(anchor="w", padx=10, pady=8)
        self.active = {"type": "cutscene", "section": "cutscene"}

    def _steps(self):
        return self.doc.data.setdefault("cutscene", {}).setdefault("steps", [])

    def _step_selected(self, _evt):
        w = self.step_widgets
        sel = w["listbox"].curselection()
        if not sel:
            return
        st = self._steps()[sel[0]]
        w["kind"].set(forms.step_key(st))
        w["val"].set(forms.step_value_text(st))

    def _step_add(self):
        w = self.step_widgets
        try:
            step = forms.make_step(w["kind"].get(), w["val"].get())
        except ValueError as e:
            messagebox.showerror("Bad step", str(e))
            return
        steps = self._steps()
        sel = w["listbox"].curselection()
        if sel and forms.step_key(steps[sel[0]]) == forms.step_key(step):
            steps[sel[0]] = step                          # update the selected same-type step
        else:
            steps.append(step)
        self._reload_steps()

    def _step_remove(self):
        w = self.step_widgets
        sel = w["listbox"].curselection()
        if sel:
            self._steps().pop(sel[0])
            self._reload_steps()

    def _step_move(self, d):
        w = self.step_widgets
        sel = w["listbox"].curselection()
        if not sel:
            return
        i = sel[0]
        steps = self._steps()
        j = i + d
        if 0 <= j < len(steps):
            steps[i], steps[j] = steps[j], steps[i]
            self._reload_steps(select=j)

    def _reload_steps(self, select=None):
        w = self.step_widgets
        lb = w["listbox"]
        lb.delete(0, "end")
        for st in self._steps():
            lb.insert("end", forms.step_summary(st))
        if select is not None and 0 <= select < lb.size():
            lb.selection_set(select)

    # --------------------------------------------------------------- commit
    def _commit_active(self) -> bool:
        """Write the active form back into the doc. Returns False (and reports) on a parse error."""
        if not self.active or not self.getters:
            return True
        a = self.active
        spec = SINGLE_SPECS.get(a["type"]) or LIST_SPECS.get(a["type"]) or (
            forms.FIELD_SPEC if a["type"] == "field" else forms.CUTSCENE_SPEC)
        values = {k: g() for k, g in self.getters.items()}
        try:
            entity = forms.build_entity(spec, values)
        except ValueError as e:
            messagebox.showerror("Invalid value", str(e))
            return False
        if "index" in a:                                  # an array-of-tables entity
            lst = self.doc.data.get(a["section"], [])
            if a["index"] < len(lst):
                _apply(lst[a["index"]], spec, entity)
        elif a["type"] == "cutscene":
            cs = self.doc.data.setdefault("cutscene", {})
            steps = cs.get("steps", [])
            _apply(cs, spec, entity)
            cs["steps"] = steps                           # keep the steps the list editor manages
        else:                                             # a single table (field/encounter/music)
            _apply(self.doc.data.setdefault(a["section"], {}), spec, entity)
        return True

    # --------------------------------------------------------------- build / check / deploy
    def _ensure_saved(self):
        if self.doc is None:
            messagebox.showinfo("No field", "Open or create a field first.")
            return False
        return self.on_save() is not False and self.doc is not None

    def on_check(self):
        if self.busy or not self._ensure_saved():
            return
        self._run(self._check)

    def _check(self):
        from ..build import FieldProject, lint_logic, validate
        self.post(f"\n--- check {self.doc.path.name} ---")
        p = FieldProject.load(self.doc.path)
        probs, lints = validate(p), lint_logic(p)
        for m in probs:
            self.post("  ERROR  " + m)
        for m in lints:
            self.post("  warn   " + m)
        self.post("  OK — no problems." if not (probs or lints)
                  else f"  {len(probs)} error(s), {len(lints)} warning(s)")

    def on_build_game(self):
        if self.busy or not self._ensure_saved():
            return
        try:
            from .. import config
            out = config.find_game_path() / "FF9CustomMap"
        except Exception:                                  # noqa: BLE001
            d = filedialog.askdirectory(title="Build output folder")
            if not d:
                return
            out = Path(d)
        if messagebox.askyesno("Build", f"Build this field into:\n{out}\n\n(installs at its real id)"):
            self._run(self._build, str(out))

    def _build(self, out):
        from ..build import FieldProject, build_mod, validate
        self.post(f"\n--- build {self.doc.path.name} -> {out} ---")
        p = FieldProject.load(self.doc.path)
        probs = validate(p)
        if probs:
            self.post("INVALID:\n  - " + "\n  - ".join(probs))
            return
        info = build_mod([p], out, mod_name="FF9CustomMap")
        self.post("OK:  " + info["dictionary"][0])
        for w in info.get("warnings", []):
            self.post("  warning: " + w)

    def on_test(self):
        if self.busy or not self._ensure_saved():
            return
        if messagebox.askyesno("Build & Test", "Build + deploy to the in-game test field (4003)?"):
            self._run(self._deploy)

    def _deploy(self):
        self.post(f"\n--- deploy {self.doc.path.name} -> test field 4003 ---")
        r = subprocess.run([sys.executable, str(self.deploy), str(self.doc.path)],
                           cwd=str(self.deploy.parents[1]), capture_output=True, text=True)
        if r.stdout:
            self.post(r.stdout)
        if r.returncode:
            self.post("ERROR:\n" + (r.stderr or "(no detail)"))
        else:
            self.post(">>> In-game: New Game -> walk to the hut door -> your field.")

    def on_revert(self):
        if self.busy:
            return
        if messagebox.askyesno("Revert", "Restore the game to before the last test deploy?"):
            self._run(self._do_revert)

    def _do_revert(self):
        self.post("\n--- revert test field ---")
        r = subprocess.run([sys.executable, str(self.revert)], cwd=str(self.revert.parents[1]),
                           capture_output=True, text=True)
        self.post(r.stdout or "")
        if r.returncode:
            self.post("ERROR:\n" + (r.stderr or "(no detail)"))

    def _run(self, fn, *args):
        self.busy = True

        def work():
            try:
                fn(*args)
            except Exception:                              # noqa: BLE001
                self.post("ERROR:\n" + traceback.format_exc())
            finally:
                self.busy = False
        threading.Thread(target=work, daemon=True).start()


def _apply(target: dict, spec, entity: dict):
    """Update ``target`` in place: clear this spec's keys, set the present ones, keep any others
    (so a single-file project's spatial keys and unknown future keys survive an edit)."""
    for f in spec:
        target.pop(f.key, None)
    target.update(entity)


def main(path=None):
    root = tk.Tk()
    try:
        EditorApp(root, path)
    except Exception:                                      # noqa: BLE001
        messagebox.showerror("FF9 Map Kit", traceback.format_exc())
        raise
    root.mainloop()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
