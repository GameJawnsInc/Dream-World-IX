#!/usr/bin/env pythonw
"""FF9 Map Kit -- Campaign Editor: the kit's GUIs in one tabbed window, with a campaign workspace.

The unified front-end: the Logic Editor, the Info Hub catalog browser, and Build & Deploy hosted as
tabs over ONE Tk root (each app mounts on a parent frame, so they also run standalone). The campaign
WORKSPACE is a left-hand pane that opens a `campaign.toml` as a project:

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
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(bar, text="Open Campaign...", command=self.on_open_campaign).pack(side="left")
        self.btn_check = ttk.Button(bar, text="Check", command=self.on_check, state="disabled")
        self.btn_check.pack(side="left", padx=(6, 0))
        self.header = ttk.Label(side, text="No campaign open.\nOpen a campaign.toml to navigate its fields.",
                                justify="left", anchor="nw")
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
        ih = _load_app("ff9_infohub.pyw", "ff9_infohub")
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Info Hub")
        ih.InfoHubApp(f)
        bg = _load_app("ff9_build_gui.pyw", "ff9_build_gui")
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Build & Deploy")
        self.build_app = bg.App(f)

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
        self.btn_check.configure(state="normal")
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
        cur = getattr(self.editor.doc, "path", None) if self.editor.doc is not None else None
        if cur is not None and Path(cur) == path:     # already open -> just focus the editor tab (no reload,
            self.nb.select(self.ed_tab)               # and dodges the load-on-campaign-open double fire)
            return True
        if not path.is_file():
            messagebox.showerror("Member not found",
                                 f"{name}: field.toml not found at\n{path}\n\n(stale campaign.toml?)")
            return False
        if self.editor.open_path(path):
            self.nb.select(self.ed_tab)
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
    plan = campaign.CampaignPlan(name="ICE", mod_folder="M", id_base=30100, flag_base=8300,
                                 flags_per_field=64, entry_name="IC_ENT", entry_entrance=0, members=members,
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
    assert ws.editor.campaign_idmap == {30100: "IC_ENT", 30101: "IC_COR", 30102: "IC_LOST"}  # gateway hints
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
    print(f"campaign editor smoke ok: {ws.nb.index('end')} tabs, 3 members, graph children + edge-nav + "
          f"Check ({len(errors)} err) + dirty-gate verified")


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
