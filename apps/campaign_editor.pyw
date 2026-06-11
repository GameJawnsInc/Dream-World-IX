#!/usr/bin/env pythonw
"""FF9 Map Kit -- Campaign Editor: the kit's GUIs in one tabbed window, with a campaign workspace.

The unified front-end: the Logic Editor, the Dialogue editor, the visual Map, the Info Hub catalog
browser, and Build & Deploy hosted as tabs over ONE Tk root (each app mounts on a parent frame, so they
also run standalone). The Logic + Dialogue tabs SHARE one FieldDoc, so words edited in either are the
same data. The campaign WORKSPACE is a left-hand pane that opens a `campaign.toml` as a project:

  * a member NAVIGATOR + GRAPH -- each member is a tree node; expand it to see its live doors (resolved
    to member NAMES) and onward seams; click a member (or a door) to open/jump to that field.toml in the
    Logic Editor. Per-member flags (entry / needs-art / unreachable / dead-end) come from
    `campaign.campaign_graph` (offline; no game install).
  * a CHECK button -- runs `campaign.lint_campaign` and reports errors/warnings in the workspace log.
  * gateway annotations -- in the Logic Editor a member's gateway shows the campaign member it leads to.

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
from tkinter import ttk, filedialog, messagebox  # noqa: E402

from ff9mapkit.editor import dialogs              # noqa: E402  (themed askstring/askinteger replacements)
from ff9mapkit.editor import graphview            # noqa: E402  (the visual campaign map)


def _load_app(filename, modname):
    """Import an apps/*.pyw module (.pyw isn't importable by name, so load it by path)."""
    spec = importlib.util.spec_from_file_location(modname, APPS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _member_tag(node) -> str:
    """A short ' -- flag' suffix describing a member's place in the campaign graph (entry / problems)."""
    bits = []
    if node.is_entry:
        bits.append("entry")
    if node.needs_export:
        bits.append("needs art")
    if not node.reachable:
        bits.append("unreachable")
    elif node.dead_end:
        bits.append("dead-end")
    return ("  -- " + ", ".join(bits)) if bits else ""


def _member_style(node) -> str:
    """The Treeview tag (colour) for a member row -- problems loudest."""
    if not node.reachable:
        return "problem"
    if node.needs_export:
        return "warn"
    if node.is_entry:
        return "entry"
    return "member"


class Workspace:
    """The campaign IDE shell: a member navigator + graph (left) wrapping the three app tabs (right).
    Opening a campaign.toml populates the navigator; selecting a member (or one of its doors) opens the
    field.toml in the Logic Editor; Check runs the campaign lint."""

    def __init__(self, root, palette):
        self.root = root
        self.palette = palette
        self.campaign_path = None
        self.plan = None
        self._member_paths = {}                   # member name -> resolved field.toml path
        self._nav = {}                            # door/seam child iid -> target member name

        panes = ttk.PanedWindow(root, orient="horizontal")
        panes.pack(fill="both", expand=True)

        side = ttk.Frame(panes)
        panes.add(side, weight=0)
        bar = ttk.Frame(side)
        bar.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Button(bar, text="Open Campaign...", command=self.on_open_campaign).pack(side="left")
        ttk.Button(bar, text="New...", command=self.on_new_campaign).pack(side="left", padx=(6, 0))
        self.btn_check = ttk.Button(bar, text="Check", command=self.on_check, state="disabled")
        self.btn_check.pack(side="left", padx=(6, 0))
        self.btn_flags = ttk.Button(bar, text="Flags...", command=self.on_flags, state="disabled")
        self.btn_flags.pack(side="left", padx=(6, 0))
        # member-authoring actions (Phase D) -- enabled once a campaign is open
        self.bar2 = ttk.Frame(side)
        self.bar2.pack(fill="x", padx=6, pady=(0, 4))
        self._edit_btns = []
        for txt, cmd in (("+ Field", self.on_add_field), ("Rename", self.on_rename_field),
                         ("Remove", self.on_remove_field), ("Set Entry", self.on_set_entry)):
            b = ttk.Button(self.bar2, text=txt, command=cmd, state="disabled")
            b.pack(side="left", padx=(0, 4))
            self._edit_btns.append(b)
        self.header = ttk.Label(side, text="No campaign open.\nOpen a campaign.toml to navigate its fields, "
                                "or New... to author one.", justify="left", anchor="nw")
        self.header.pack(fill="x", padx=8, pady=(0, 6))
        twrap = ttk.Frame(side)
        twrap.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.tree = ttk.Treeview(twrap, show="tree", selectmode="browse")
        self.tree.column("#0", width=260, stretch=True)
        self.tree.pack(side="left", fill="both", expand=True)
        tsb = ttk.Scrollbar(twrap, orient="vertical", command=self.tree.yview)
        tsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=tsb.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_member_select)
        for tag, col in (("entry", palette["success"]), ("problem", palette["error"]),
                         ("warn", palette["warn"]), ("door", palette["muted"])):
            self.tree.tag_configure(tag, foreground=col)
        self.log = self._build_log(side)

        self.nb = ttk.Notebook(panes)
        panes.add(self.nb, weight=1)
        from ff9mapkit.editor.app import EditorApp     # built first so it sets the shared theme
        self.ed_tab = ttk.Frame(self.nb)
        self.nb.add(self.ed_tab, text="Logic Editor")
        self.editor = EditorApp(self.ed_tab)
        dl = _load_app("ff9_dialogue.pyw", "ff9_dialogue")   # the focused dialogue editor / stock-text viewer
        self.dlg_tab = ttk.Frame(self.nb)
        self.nb.add(self.dlg_tab, text="Dialogue")
        self.dialogue = dl.DialogueApp(self.dlg_tab)
        # the Logic Editor's "Dialogue..." button flips to this tab; both tabs SHARE one FieldDoc (no divergence)
        self.editor.dialogue_opener = lambda: self.nb.select(self.dlg_tab)
        self.map_tab = ttk.Frame(self.nb)              # the visual node-link map of the open campaign
        self.nb.add(self.map_tab, text="Map")
        self.graph = graphview.GraphView(self.map_tab, palette, on_open=self._graph_open)
        ih = _load_app("ff9_infohub.pyw", "ff9_infohub")
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Info Hub")
        ih.InfoHubApp(f)
        bg = _load_app("ff9_build_gui.pyw", "ff9_build_gui")
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Build & Deploy")
        self.build_app = bg.App(f)
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)   # keep Logic+Dialogue tabs in sync

    def _on_tab_changed(self, _evt=None):
        """The Logic + Dialogue tabs share ONE FieldDoc, so a tab flip just commits the leaving tab's
        in-progress edit and refreshes the entering tab from the shared data (no save, no divergence)."""
        ed, dlg = getattr(self, "editor", None), getattr(self, "dialogue", None)
        if ed is None or dlg is None:
            return
        cur = self.nb.select()
        if cur == str(self.dlg_tab):
            ed._commit_active()
            if dlg.doc is not ed.doc:
                dlg.set_doc(ed.doc)
            else:
                dlg._refresh_tree()
        elif cur == str(self.ed_tab):
            dlg._commit_active()
            sel = ed.tree.selection()
            if sel:
                ed._show(sel[0])                       # re-render the Logic form from the shared doc

    # ---------------------------------------------------------------- logging
    def _build_log(self, parent):
        pal = self.palette
        wrap = ttk.Frame(parent)
        wrap.pack(fill="x", padx=6, pady=(0, 6))
        txt = tk.Text(wrap, height=7, state="disabled", wrap="word", relief="flat", borderwidth=0,
                      background=pal["log_bg"], foreground=pal["log_fg"], padx=8, pady=6,
                      highlightthickness=1, highlightbackground=pal["border"])
        txt.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.configure(yscrollcommand=sb.set)
        for tag, col in (("error", pal["error"]), ("warn", pal["warn"]),
                         ("ok", pal["success"]), ("muted", pal["muted"])):
            txt.tag_configure(tag, foreground=col)
        return txt

    def _log(self, msg, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", str(msg).rstrip() + "\n", (tag,) if tag else ())
        self.log.see("end")
        self.log.configure(state="disabled")

    # ---------------------------------------------------------------- campaign io
    def on_open_campaign(self):
        f = filedialog.askopenfilename(title="Open campaign.toml",
                                       filetypes=[("Campaign manifest", "campaign.toml"),
                                                  ("TOML", "*.toml"), ("All files", "*.*")])
        if f:
            self.open_campaign(Path(f))

    def open_campaign(self, path) -> bool:
        """Load a campaign.toml as the active project: resolve its graph + populate the navigator. Returns
        False (and reports) if the manifest can't be parsed."""
        from ff9mapkit import campaign
        path = Path(path)
        try:
            plan = campaign.load_campaign(path)
        except Exception as e:                        # noqa: BLE001
            messagebox.showerror("Open campaign failed", f"{path}\n\n{e}")
            return False
        self.campaign_path = path
        self.plan = plan
        self._member_paths = {m.name: (path.parent / m.toml_rel).resolve() for m in plan.members}
        self.editor.campaign_idmap = {m.new_id: m.name for m in plan.members}   # gateway annotations
        self.editor.campaign_plan = plan                                         # flag picker + name resolution
        self.dialogue.campaign_plan = plan                                       # same, for the Dialogue tab's picker
        self.btn_check.configure(state="normal")
        self.btn_flags.configure(state="normal")
        for b in self._edit_btns:
            b.configure(state="normal")
        self._populate(plan)
        self._log(f"opened campaign {plan.name} ({len(plan.members)} fields) -- click a field to edit it, "
                  "expand it to see its doors, or Check it.", "ok")
        # hand the campaign to the Build & Deploy tab so its picker defaults to this manifest
        setter = getattr(self.build_app, "set_project", None)
        if callable(setter):
            try:
                setter(path)
            except Exception:                         # noqa: BLE001 -- the navigator must not depend on it
                pass
        if plan.members:                              # land the editor on the entry member
            entry = campaign.campaign_graph(plan).entry or plan.members[0].name
            self.tree.see(entry)
            self.open_member(entry)
        return True

    def _populate(self, plan):
        from ff9mapkit.campaign import campaign_graph
        g = campaign_graph(plan)
        ids = [m.new_id for m in plan.members]
        rng = f"{min(ids)}–{max(ids)}" if ids else "-"
        problems = len(g.unreachable) + len(g.dangling_edges) + len(g.dangling_seams)
        warn = f"\n⚠ {problems} issue(s) -- click Check" if problems else ""
        self.header.configure(text=f"{plan.name}\n{len(plan.members)} fields · ids {rng}\n"
                                   f"entry: {g.entry or '(none)'}{warn}")
        self.tree.delete(*self.tree.get_children())
        self._nav = {}
        for node in g.nodes:
            if self.tree.exists(node.name):           # dup name in a hand-edited manifest -> lint flags it;
                continue                              # don't let a duplicate iid crash the navigator
            self.tree.insert("", "end", iid=node.name, text=f"{node.name}{_member_tag(node)}",
                             tags=(_member_style(node),))
            for i, oe in enumerate(node.out_edges):   # live doors -> a click jumps to the target member
                iid = f"@e:{node.name}:{i}"
                lbl = f"→ {oe['to']} (entrance {oe['entrance']})" + (" [gated]" if oe["gated"] else "")
                self.tree.insert(node.name, "end", iid=iid, text=lbl, tags=("door",))
                self._nav[iid] = oe["to"]
            for i, s in enumerate(node.seams):        # onward seams (scripted/overworld/portal/menu)
                iid = f"@s:{node.name}:{i}"
                tgt = s.get("to_member") or ("WORLDMAP" if s.get("to_real") == "WORLDMAP" else s.get("to_real"))
                self.tree.insert(node.name, "end", iid=iid, text=f"~ seam[{s.get('kind')}] → {tgt}",
                                 tags=("door",))
                if s.get("to_member"):
                    self._nav[iid] = s["to_member"]
        self.graph.render(g, current=self._current_member_name())     # the visual Map tab, same graph

    def _current_member_name(self):
        """The member whose field.toml is open in the editor (None if none / not a member)."""
        cur = getattr(self.editor.doc, "path", None) if self.editor.doc is not None else None
        if cur is None:
            return None
        curp = Path(cur).resolve()
        return next((nm for nm, p in self._member_paths.items() if Path(p).resolve() == curp), None)

    def _sync_graph(self, name):
        """Mark ``name`` as the open member on the Map tab (no-op before the graph exists)."""
        g = getattr(self, "graph", None)
        if g is not None:
            g.highlight(name)

    def _graph_open(self, name):
        """Double-click on a Map node -> open that member. Syncs the tree selection AND opens it directly,
        so it works with or without the Tk event loop (open_member is idempotent if <<TreeviewSelect>>
        re-fires it)."""
        if self.tree.exists(name):
            self.tree.see(name)
            self.tree.selection_set(name)
        self.open_member(name)

    # ---------------------------------------------------------------- member nav
    def _on_member_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid in self._member_paths:                 # a member row -> open it
            self.open_member(iid)
        elif iid in self._nav:                        # a door/seam row -> jump to its target member
            tgt = self._nav[iid]
            self.tree.see(tgt)
            self.open_member(tgt)

    def open_member(self, name) -> bool:
        """Open a member's field.toml in the Logic Editor tab. Returns False if the editor declined the
        switch (e.g. the user cancelled a save prompt) or the member has no resolvable toml."""
        path = self._member_paths.get(name)
        if not path:
            return False
        if getattr(self, "dialogue", None) is not None:
            self.dialogue._commit_active()            # fold any in-progress Dialogue-tab edit into the shared doc first
        cur = getattr(self.editor.doc, "path", None) if self.editor.doc is not None else None
        if cur is not None and Path(cur) == path:     # already open -> just focus the editor tab (no reload,
            self.dialogue.set_doc(self.editor.doc)    # and dodges the load-on-campaign-open double fire)
            self.nb.select(self.ed_tab)
            self._sync_graph(name)
            return True
        if not path.is_file():
            messagebox.showerror("Member not found",
                                 f"{name}: field.toml not found at\n{path}\n\n(stale campaign.toml?)")
            return False
        if self.editor.open_path(path):
            self.dialogue.set_doc(self.editor.doc)    # both tabs now share the one FieldDoc
            self.nb.select(self.ed_tab)
            self._sync_graph(name)
            return True
        return False

    # ---------------------------------------------------------------- check
    def on_check(self):
        """Run the campaign lint and report it in the workspace log; highlight a problem member. Returns
        (errors, warnings)."""
        if self.plan is None:
            return [], []
        from ff9mapkit import campaign
        try:
            errors, warnings = campaign.lint_campaign(self.plan, self.campaign_path.parent)
        except Exception as e:                        # noqa: BLE001
            self._log(f"check failed: {e}", "error")
            return [str(e)], []
        self._log(f"--- Check {self.plan.name}: {len(errors)} error(s), {len(warnings)} warning(s) ---",
                  "muted")
        for w in warnings:
            self._log("warning: " + w, "warn")
        for e in errors:
            self._log("error: " + e, "error")
        if not errors and not warnings:
            self._log("OK -- no campaign issues.", "ok")
        # scroll the first structurally-problematic member into view (see, NOT select -- selecting would
        # fire <<TreeviewSelect>> and open it, so merely checking could pop a save prompt). Colour + the
        # flag suffix already mark it in the tree.
        g = campaign.campaign_graph(self.plan)
        first = next((n.name for n in g.nodes if not n.reachable or n.needs_export), None)
        if first and self.tree.exists(first):
            self.tree.see(first)
        return errors, warnings

    # ---------------------------------------------------------------- authoring (Phase D)
    def _reload(self, land=None):
        """Re-read campaign.toml after a mutation (the API re-renders it) and repopulate the navigator;
        optionally open ``land`` in the editor. Keeps the manifest the single source of truth, and keeps
        the editor OFF a removed/renamed member (whose file just moved/vanished) so a later Save can't
        write to a dead path."""
        from ff9mapkit import campaign
        self.plan = campaign.load_campaign(self.campaign_path)
        self._member_paths = {m.name: (self.campaign_path.parent / m.toml_rel).resolve()
                              for m in self.plan.members}
        self.editor.campaign_idmap = {m.new_id: m.name for m in self.plan.members}
        self.editor.campaign_plan = self.plan
        self._populate(self.plan)
        cur = getattr(self.editor.doc, "path", None)
        live = {p.resolve() for p in self._member_paths.values()}
        stale = cur is not None and Path(cur).resolve() not in live
        target = land if (land and land in self._member_paths) else None
        if target is None and stale and self.plan.members:    # editor was on a removed/renamed member
            target = self.plan.entry_name if self.plan.entry_name in self._member_paths \
                else self.plan.members[0].name
        if target and target in self._member_paths:
            self.tree.see(target)
            self.open_member(target)

    def _selected_member(self):
        """The selected member name (a door/seam child resolves to its parent member); None if nothing
        member-like is selected (with a nudge)."""
        sel = self.tree.selection()
        if sel:
            iid = sel[0]
            if iid in self._member_paths:
                return iid
            parent = self.tree.parent(iid)
            if parent in self._member_paths:
                return parent
        messagebox.showinfo("No member selected", "Select a field in the list first.")
        return None

    def on_new_campaign(self):
        d = filedialog.askdirectory(title="New campaign: choose an empty folder for it")
        if not d:
            return
        name = dialogs.ask_string(self.root, "New campaign", "Campaign / mod name:")
        if not name:
            return
        id_base = dialogs.ask_integer(
            self.root, "New campaign", "First field id (id_base) for this campaign.\nEach member takes "
            "id_base, +1, +2 ...  Must be >= 4000 and NOT collide with other deployed fields.",
            initial=4000, minvalue=4000, maxvalue=32767)
        if id_base is None:
            return
        from ff9mapkit import campaign
        try:
            campaign.new_campaign(name, "FF9CustomMap", Path(d), id_base=id_base)
        except Exception as e:                        # noqa: BLE001
            messagebox.showerror("New campaign failed", str(e))
            return
        self.open_campaign(Path(d) / "campaign.toml")
        self._log("new campaign created -- add fields with '+ Field' (blank rooms, or fork a real field). "
                  "Tip: set mod_folder precisely by editing campaign.toml or via `ff9mapkit new-campaign`.",
                  "muted")

    def on_add_field(self):
        if self.plan is None:
            return
        name = dialogs.ask_string(self.root, "Add field", "New member name (unique, e.g. HUB):")
        if not name:
            return
        src = dialogs.ask_string(self.root, "Add field",
                                 "Fork which real FF9 field? (a field id or unique FBG name -- needs the "
                                 "game install)\n\nLeave BLANK for an empty room.")
        src = (src or "").strip() or None
        from ff9mapkit import campaign
        try:
            m = campaign.add_field(self.plan, self.campaign_path.parent, name=name, source=src)
        except Exception as e:                        # noqa: BLE001
            messagebox.showerror("Add field failed", str(e))
            return
        self._reload(land=m.name)
        self._log(f"added {m.name} (id {m.new_id}, {'fork ' + src if src else 'blank room'})", "ok")

    def on_remove_field(self):
        name = self._selected_member()
        if not name:
            return
        if not messagebox.askyesno("Remove member",
                                   f"Remove '{name}' from the campaign AND delete its folder on disk?\n\n"
                                   "Edges/seams referencing it are pruned. This can't be undone."):
            return
        from ff9mapkit import campaign
        try:
            campaign.remove_field(self.plan, self.campaign_path.parent, name)
        except Exception as e:                        # noqa: BLE001
            messagebox.showerror("Remove failed", str(e))
            return
        self._reload()
        self._log(f"removed {name}", "warn")

    def on_rename_field(self):
        name = self._selected_member()
        if not name:
            return
        new = dialogs.ask_string(self.root, "Rename member", f"New (structural) name for '{name}':",
                                 initial=name)
        if not new or new == name:
            return
        from ff9mapkit import campaign
        try:
            campaign.rename_field(self.plan, self.campaign_path.parent, name, new)
        except Exception as e:                        # noqa: BLE001
            messagebox.showerror("Rename failed", str(e))
            return
        self._reload(land=new)
        self._log(f"renamed {name} -> {new} (the field's in-game [field] name is separate -- edit it in the "
                  "Logic Editor)", "ok")

    def on_set_entry(self):
        name = self._selected_member()
        if not name:
            return
        from ff9mapkit import campaign
        try:
            campaign.set_entry(self.plan, self.campaign_path.parent, name)
        except Exception as e:                        # noqa: BLE001
            messagebox.showerror("Set entry failed", str(e))
            return
        self._reload()
        self._log(f"entry set to {name}", "ok")

    def on_flags(self):
        """A modal manager for the campaign's shared NAMED flags (cross-field story gates) -- the [[flag]]
        table members gate by name. Indices auto-allocate above the per-member blocks, in the safe band."""
        if self.plan is None:
            return
        from ff9mapkit import campaign
        win = tk.Toplevel(self.root)
        win.title(f"Shared named flags -- {self.plan.name}")
        win.transient(self.root)
        win.configure(background=self.palette["bg"])      # match the themed app (a bare Toplevel is OS-gray)
        ttk.Label(win, justify="left", text=(
            "Cross-field story gates. A member gates by NAME (requires_flag = \"<name>\").\n"
            "Indices auto-allocate ABOVE the per-member flag blocks, in the census-safe band.")
        ).pack(anchor="w", padx=10, pady=(10, 6))
        tv = ttk.Treeview(win, columns=("name", "index"), show="headings", height=10, selectmode="browse")
        tv.heading("name", text="Name")
        tv.heading("index", text="Index")
        tv.column("name", width=240)
        tv.column("index", width=80, anchor="e")
        tv.pack(fill="both", expand=True, padx=10)

        def refresh():
            tv.delete(*tv.get_children())
            for fdef in self.plan.flags:
                tv.insert("", "end", iid=str(fdef.get("name")), values=(fdef.get("name"), fdef.get("index")))

        def add():
            name = dialogs.ask_string(win, "Add flag", "New shared flag name (e.g. boss_dead):")
            if not name:
                return
            try:
                f = campaign.add_flag(self.plan, self.campaign_path.parent, name)
            except Exception as e:                    # noqa: BLE001
                messagebox.showerror("Add flag failed", str(e), parent=win)
                return
            refresh()
            self._log(f"added shared flag {f['name']} = {f['index']}", "ok")

        def remove():
            sel = tv.selection()
            if not sel:
                return
            try:
                campaign.remove_flag(self.plan, self.campaign_path.parent, sel[0])
            except Exception as e:                    # noqa: BLE001
                messagebox.showerror("Remove flag failed", str(e), parent=win)
                return
            refresh()
            self._log(f"removed shared flag {sel[0]}", "warn")

        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=10, pady=10)
        ttk.Button(btns, text="Add...", command=add).pack(side="left")
        ttk.Button(btns, text="Remove", command=remove).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="right")
        refresh()


def build(root):
    """Mount the campaign workspace (navigator + the three app tabs) on `root`; return the Workspace."""
    from ff9mapkit.editor.theme import apply_theme
    palette = apply_theme(root)                      # theme the root + notebook strip before the tabs
    return Workspace(root, palette)


def _smoke(ws):
    """Offline self-test: build a campaign with a door, a seam, a dangling edge and an unreachable member;
    open it; and verify the navigator wiring, the graph children, edge-navigation, Check, and the dirty gate."""
    import tempfile
    from ff9mapkit import campaign
    from ff9mapkit.editor import app as _appmod
    d = Path(tempfile.mkdtemp())
    M = campaign.Member
    members = [M(300, 30100, "IC_ENT", "borrow", 11, "", "IC_ENT/IC_ENT.field.toml", False),
               M(301, 30101, "IC_COR", "borrow", 11, "", "IC_COR/IC_COR.field.toml", False),
               M(302, 30102, "IC_LOST", "borrow", 11, "", "IC_LOST/IC_LOST.field.toml", False)]
    plan = campaign.CampaignPlan(name="ICE", mod_folder="M", id_base=30100,
                                 flag_base=campaign.FIRST_SAFE_FLAG, flags_per_field=64,
                                 entry_name="IC_ENT", entry_entrance=0, members=members,
                                 edges=[{"frm": "IC_ENT", "to": "IC_COR", "entrance": 2},
                                        {"frm": "IC_ENT", "to": "GHOST", "entrance": 0}],   # dangling
                                 seams=[{"frm": "IC_COR", "to_real": "WORLDMAP", "kind": "overworld",
                                         "note": "", "to_member": None}])
    (d / "campaign.toml").write_text(campaign.render_campaign_toml(plan), encoding="utf-8")
    for m in members:
        (d / m.name).mkdir(parents=True, exist_ok=True)
        (d / m.toml_rel).write_text(f'[field]\nid = {m.new_id}\nname = "{m.name}"\narea = 11\n',
                                    encoding="utf-8")

    calls = []                                        # capture the save-before-switch prompt (No -> discard)
    _appmod.messagebox.askyesnocancel = lambda *a, **k: (calls.append(1), False)[1]

    assert ws.open_campaign(d / "campaign.toml")
    assert list(ws.tree.get_children()) == ["IC_ENT", "IC_COR", "IC_LOST"]
    assert ws.editor.doc is not None and ws.editor.doc.path == members_path(d, "IC_ENT")   # auto-land entry
    # the Dialogue tab shares the SAME FieldDoc as the Logic Editor (no divergence on edit)
    assert ws.dialogue.doc is ws.editor.doc
    ws.nb.select(ws.dlg_tab)
    ws._on_tab_changed()
    assert ws.dialogue.doc is ws.editor.doc
    ws.nb.select(ws.ed_tab)
    ws._on_tab_changed()
    assert ws.editor.campaign_idmap == {30100: "IC_ENT", 30101: "IC_COR", 30102: "IC_LOST"}  # gateway hints
    # the visual Map tab renders the same graph and highlights the auto-landed entry
    assert ws.graph._layout is not None and len(ws.graph._layout.nodes) == 3
    assert ws.graph._current == "IC_ENT"
    ws._graph_open("IC_LOST")                         # double-click a Map node opens that member
    assert ws.editor.doc.path == members_path(d, "IC_LOST") and ws.graph._current == "IC_LOST"
    ws._graph_open("IC_ENT")                          # back to the entry for the rest of the flow
    assert ws.editor.doc.path == members_path(d, "IC_ENT")
    # graph children: IC_ENT shows its one live door (the dangling GHOST is NOT a child); IC_COR a seam
    ent_kids = ws.tree.get_children("IC_ENT")
    assert len(ent_kids) == 1 and ws._nav[ent_kids[0]] == "IC_COR"
    assert ws.tree.get_children("IC_COR")             # the overworld seam row
    # edge-navigation: selecting IC_ENT's door row jumps the editor to IC_COR (clean switch -> no prompt)
    ws.tree.selection_set(ent_kids[0])
    ws._on_member_select()
    assert ws.editor.doc.path == members_path(d, "IC_COR") and calls == []
    # Check surfaces the dangling edge as an error
    errors, warnings = ws.on_check()
    assert any("GHOST" in e for e in errors), errors
    # dirty gate: a real edit prompts before the next switch (and proceeds on 'No')
    ws.editor.doc.data["__dirty_probe__"] = True
    assert ws.open_member("IC_ENT") and ws.editor.doc.path == members_path(d, "IC_ENT")
    assert calls == [1], "a dirty switch should prompt exactly once"

    # --- Phase D authoring: add / rename / remove a member via the handlers (patched dialogs) ---
    import tkinter.messagebox as _mb
    answers = iter(["WEST", ""])                                   # on_add_field: name, then source (blank)
    dialogs.ask_string = lambda *a, **k: next(answers, "")
    ws.on_add_field()
    assert "WEST" in ws.tree.get_children() and (d / "WEST" / "west.field.toml").is_file()
    dialogs.ask_string = lambda *a, **k: "WESTWING"               # on_rename_field
    ws.tree.selection_set("WEST")
    ws.on_rename_field()
    assert "WESTWING" in ws.tree.get_children() and "WEST" not in ws.tree.get_children()
    assert (d / "WESTWING").is_dir() and not (d / "WEST").exists()
    _mb.askyesno = lambda *a, **k: True                            # on_remove_field (confirm)
    ws.tree.selection_set("WESTWING")
    ws.on_remove_field()
    assert "WESTWING" not in ws.tree.get_children() and not (d / "WESTWING").exists()
    # F1: shared named flags -- the button is live and add/remove round-trip through campaign.toml
    assert str(ws.btn_flags["state"]) == "normal"
    f = campaign.add_flag(ws.plan, ws.campaign_path.parent, "boss_dead")
    assert f["index"] >= campaign.FIRST_SAFE_FLAG + 3 * 64               # above the 3 member blocks
    assert campaign.load_campaign(ws.campaign_path).flags == [{"name": "boss_dead", "index": f["index"]}]
    campaign.remove_flag(ws.plan, ws.campaign_path.parent, "boss_dead")
    assert campaign.load_campaign(ws.campaign_path).flags == []
    print(f"campaign editor smoke ok: {ws.nb.index('end')} tabs (incl. Dialogue, shared doc), 3 members, "
          f"tree+Map graph + edge-nav + map-open + Check ({len(errors)} err) + dirty-gate + "
          f"Phase-D add/rename/remove + shared-flags")


def members_path(d, name):
    return (d / name / f"{name}.field.toml").resolve()


def main():
    smoke = "--smoke" in sys.argv
    root = tk.Tk()
    root.title("FF9 Map Kit - Campaign Editor")
    root.geometry("1320x820")
    root.minsize(1080, 680)
    if smoke:
        root.withdraw()
    try:
        ws = build(root)
    except Exception:
        if not smoke:
            messagebox.showerror("FF9 Map Kit - Campaign Editor", traceback.format_exc())
        raise
    if smoke:
        _smoke(ws)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
