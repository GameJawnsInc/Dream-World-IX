"""The PySide6 workspace shell (Qt UI) -- Phase 3 of the GUI makeover.

One dockable window: a left project tree (journey > campaign > field > object), a clickable breadcrumb,
a central document area, a right inspector, and a bottom Output/Problems dock. It reuses the kit's
tk-free backends verbatim -- :mod:`..editor.feedback` (Verdict/Problem), :mod:`..editor.breadcrumb`
(Crumb/trail), :mod:`..campaign` (CampaignPlan/graph), :mod:`..editor.model` (FieldDoc) -- so only this
view layer is Qt. Long jobs stream via ``QProcess`` (the Qt analogue of the tkinter apps' thread+queue).

Launch:  ``py apps/ff9_workspace.pyw``  (or ``py -m ff9mapkit.workspace.shell``).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QAction, QBrush, QColor
from PySide6.QtWidgets import (
    QApplication, QDockWidget, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QPlainTextEdit, QPushButton, QSplitter, QTabWidget, QTextEdit,
    QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .. import campaign as C
from ..editor import breadcrumb as bc
from ..editor import feedback as fb
from ..editor.model import FieldDoc
from ..editor.theme import pick_palette
from .style import qss

KIT = Path(__file__).resolve().parents[2]          # the kit root (holds pyproject) -> `-m ff9mapkit` cwd

# object groups inside a field.toml, mirroring the tkinter editor's tree (editor/app.py).
_SINGLE = [("dialogue", "Dialogue"), ("encounter", "Encounter"), ("music", "Music"), ("cutscene", "Cutscene")]
_LISTS = [("npc", "NPCs"), ("gateway", "Gateways"), ("event", "Events"), ("marker", "Markers"),
          ("choice", "Choices")]
_ROLE = Qt.UserRole                                # per-item payload: (kind, label, key)


def _badge(node) -> str:
    """A leading health glyph for a campaign member (mirrors the tkinter navigator)."""
    if not node.reachable:
        return "✕"
    if node.needs_export:
        return "⚠"
    if node.is_entry:
        return "◆"
    if node.dead_end:
        return "○"
    return "•"


def _health(node, pal):
    """The member row's colour (problems loudest), or None for a healthy interior field."""
    if not node.reachable:
        return pal["error"]
    if node.needs_export:
        return pal["warn"]
    if node.is_entry:
        return pal["success"]
    return None


class BreadcrumbBar(QWidget):
    """A one-line clickable path built from :func:`..editor.breadcrumb.trail`. ``on_nav(crumb)`` fires
    when an ancestor segment is clicked (the leaf is inert)."""

    def __init__(self, pal):
        super().__init__()
        self.pal = pal
        self.on_nav = None
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(12, 6, 12, 6)
        self._lay.setSpacing(3)
        self.setStyleSheet(f"background:{pal['surface']};border-bottom:1px solid {pal['border']};")
        self.set([])

    def set(self, crumbs):
        while self._lay.count():
            w = self._lay.takeAt(0).widget()
            if w:
                w.deleteLater()
        if not crumbs:
            ph = QLabel("No campaign open  —  Open a campaign.toml to navigate it.")
            ph.setStyleSheet(f"color:{self.pal['muted']};")
            self._lay.addWidget(ph)
            self._lay.addStretch(1)
            return
        last = len(crumbs) - 1
        for i, c in enumerate(crumbs):
            if i:
                sep = QLabel("▸")
                sep.setStyleSheet(f"color:{self.pal['muted']};")
                self._lay.addWidget(sep)
            text = f"{bc.GLYPH.get(c.level, '')} {c.label}"
            if i == last:
                leaf = QLabel(text)
                leaf.setStyleSheet(f"color:{self.pal['text']};font-weight:600;")
                self._lay.addWidget(leaf)
            else:
                btn = QPushButton(text)
                btn.setFlat(True)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(
                    f"border:none;background:transparent;color:{self.pal['accent']};padding:2px 4px;")
                btn.clicked.connect(lambda _=False, cc=c: self.on_nav and self.on_nav(cc))
                self._lay.addWidget(btn)
        self._lay.addStretch(1)


class Workspace(QMainWindow):
    """The shell: a project tree (left) + document tabs (center) + inspector (right) + Output/Problems
    dock (bottom), with a breadcrumb above. Open a campaign.toml to populate it."""

    def __init__(self, pal):
        super().__init__()
        self.pal = pal
        self.plan = None
        self.campaign_path = None
        self.member_paths = {}                     # member name -> field.toml path
        self.journey_name = None
        self.setWindowTitle("FF9 Map Kit — Workspace")
        self.resize(1280, 820)
        self.setStyleSheet(qss(pal))
        self._build_toolbar()
        self._build_central()
        self._build_dock()
        self.statusBar().showMessage("Open a campaign.toml to begin.")

    # ---- chrome ----
    def _build_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)
        act_open = QAction("Open Campaign…", self)
        act_open.triggered.connect(self.on_open_campaign)
        tb.addAction(act_open)
        self.act_check = QAction("Check", self)
        self.act_check.triggered.connect(self.on_check)
        self.act_check.setEnabled(False)
        tb.addAction(self.act_check)
        self.act_lint_cli = QAction("Lint (CLI)", self)
        self.act_lint_cli.triggered.connect(self.run_cli_lint)
        self.act_lint_cli.setEnabled(False)
        tb.addAction(self.act_lint_cli)
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred)
        tb.addWidget(spacer)
        search = QLineEdit()
        search.setObjectName("search")
        search.setPlaceholderText("⌕  Ctrl-K — search content & commands  (coming soon)")
        search.setFixedWidth(320)
        search.setEnabled(False)
        tb.addWidget(search)

    def _build_central(self):
        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.crumb = BreadcrumbBar(self.pal)
        self.crumb.on_nav = self._on_crumb
        v.addWidget(self.crumb)

        split = QSplitter(Qt.Horizontal)
        v.addWidget(split, 1)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemSelectionChanged.connect(self._on_select)
        self.tree.itemExpanded.connect(self._on_expand)
        split.addWidget(self.tree)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self._welcome()
        split.addWidget(self.tabs)

        insp = QWidget()
        iv = QVBoxLayout(insp)
        iv.setContentsMargins(10, 10, 10, 10)
        self.insp_title = QLabel("Inspector")
        self.insp_title.setStyleSheet("font-weight:600;")
        self.insp_body = QLabel("Select something on the left.")
        self.insp_body.setWordWrap(True)
        self.insp_body.setStyleSheet(f"color:{self.pal['muted']};")
        self.insp_body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        iv.addWidget(self.insp_title)
        iv.addWidget(self.insp_body, 1)
        split.addWidget(insp)

        split.setSizes([300, 640, 240])
        split.setStretchFactor(1, 1)
        self.setCentralWidget(central)

    def _build_dock(self):
        dock = QDockWidget("Output  /  Problems")
        dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.dock_tabs = QTabWidget()
        self.dock_tabs.setDocumentMode(True)

        prob_page = QWidget()
        pv = QVBoxLayout(prob_page)
        pv.setContentsMargins(8, 8, 8, 8)
        self.banner = QLabel("")
        self.banner.setVisible(False)
        self.banner.setWordWrap(True)
        self.problems = QListWidget()
        pv.addWidget(self.banner)
        pv.addWidget(self.problems, 1)
        self.problems_page = prob_page

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)

        self.dock_tabs.addTab(prob_page, "Problems")
        self.dock_tabs.addTab(self.output, "Output")
        dock.setWidget(self.dock_tabs)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        dock.setMinimumHeight(150)

    def _welcome(self):
        w = QTextEdit()
        w.setReadOnly(True)
        w.setHtml(
            "<h2>FF9 Map Kit — Workspace</h2>"
            "<p>The modern shell (Phase 3). <b>Open Campaign…</b> to load a <code>campaign.toml</code>; "
            "the left tree shows <b>journey ▸ campaign ▸ field ▸ object</b>, the breadcrumb tracks where "
            "you are, and <b>Check</b> fills the Problems dock.</p>"
            "<p style='color:gray'>The field editor forms mount here in Phase 4; this shell wraps the "
            "same backend as the tkinter apps.</p>")
        self.tabs.addTab(w, "Welcome")

    # ---- item helpers ----
    @staticmethod
    def _mk(kind, label, key="", glyph=""):
        it = QTreeWidgetItem([f"{glyph} {label}".strip()])
        it.setData(0, _ROLE, (kind, label, key))
        return it

    @staticmethod
    def _payload(item):
        return item.data(0, _ROLE) if item is not None else None

    # ---- campaign io ----
    def on_open_campaign(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open campaign.toml", "",
                                           "Campaign (campaign.toml);;TOML (*.toml);;All files (*)")
        if f:
            self.open_campaign(Path(f))

    def open_campaign(self, path) -> bool:
        path = Path(path)
        try:
            plan = C.load_campaign(path)
        except Exception as e:                     # noqa: BLE001
            self.statusBar().showMessage(f"Open failed: {e}")
            return False
        self.plan = plan
        self.campaign_path = path
        self.member_paths = {m.name: (path.parent / m.toml_rel).resolve() for m in plan.members}
        self.journey_name = self._journey_label()
        self.act_check.setEnabled(True)
        self.act_lint_cli.setEnabled(True)
        self._populate()
        self.statusBar().showMessage(
            f"{plan.name} — {len(plan.members)} fields — mod folder {plan.mod_folder}")
        g = C.campaign_graph(plan)
        entry = g.entry or (plan.members[0].name if plan.members else None)
        if entry:
            self._select_member(entry)
        return True

    def _journey_label(self):
        """A real journey from a journeys.toml beside the campaign or one level up (display only; mirrors
        the tkinter navigator -- see docs/JOURNEYS.md). None when none is defined."""
        if not self.campaign_path:
            return None
        folder = self.campaign_path.parent.name
        ids = {m.new_id for m in self.plan.members}
        for jt in (self.campaign_path.parent / "journeys.toml",
                   self.campaign_path.parent.parent / "journeys.toml"):
            try:
                if not jt.is_file():
                    continue
                import tomllib
                for j in tomllib.loads(jt.read_text(encoding="utf-8")).get("journey", []):
                    if j.get("name") and (folder in j.get("campaigns", []) or j.get("entry") in ids):
                        return j["name"]
            except Exception:                      # noqa: BLE001
                continue
        return None

    def _populate(self):
        self.tree.clear()
        g = C.campaign_graph(self.plan)
        parent = self.tree
        if self.journey_name:
            jr = self._mk("journey", self.journey_name, "@journey", "◆")
            jr.setForeground(0, QBrush(QColor(self.pal["accent"])))
            self.tree.addTopLevelItem(jr)
            jr.setExpanded(True)
            parent = jr
        camp = self._mk("campaign", self.plan.name, "@campaign", "▣")
        camp.setForeground(0, QBrush(QColor(self.pal["accent"])))
        (parent.addChild(camp) if isinstance(parent, QTreeWidgetItem) else self.tree.addTopLevelItem(camp))
        camp.setExpanded(True)
        self._member_items = {}
        for node in g.nodes:
            mi = self._mk("field", node.name, node.name, _badge(node))
            col = _health(node, self.pal)
            if col:
                mi.setForeground(0, QBrush(QColor(col)))
            camp.addChild(mi)
            self._member_items[node.name] = mi
            mi.addChild(self._mk("__lazy__", "loading…"))   # placeholder -> lazy object load on expand

    # ---- lazy object load ----
    def _on_expand(self, item):
        kind = (self._payload(item) or (None,))[0]
        if kind != "field":
            return
        if item.childCount() == 1 and (self._payload(item.child(0)) or (None,))[0] == "__lazy__":
            item.takeChild(0)
            self._load_objects(item)

    def _load_objects(self, member_item):
        name = self._payload(member_item)[1]
        path = self.member_paths.get(name)
        try:
            doc = FieldDoc.load(path)
            data = doc.data
        except Exception as e:                     # noqa: BLE001
            member_item.addChild(self._mk("note", f"(could not load: {e})"))
            return
        member_item.addChild(self._mk("object", "Field", "field"))
        member_item.addChild(self._mk("object", "Camera (Blender)", "camera"))
        for key, label in _SINGLE:
            if key in data:
                member_item.addChild(self._mk("object", label, key))
        for key, label in _LISTS:
            lst = data.get(key, []) or []
            grp = self._mk("group", f"{label} ({len(lst)})", key)
            for i, e in enumerate(lst):
                grp.addChild(self._mk("object", e.get("name") or f"#{i}", f"{key}:{i}"))
            member_item.addChild(grp)

    # ---- selection -> breadcrumb + inspector ----
    def _ancestor_field(self, item):
        node = item
        while node is not None:
            p = self._payload(node)
            if p and p[0] == "field":
                return node
            node = node.parent()
        return None

    def _on_select(self):
        items = self.tree.selectedItems()
        if not items:
            return
        item = items[0]
        p = self._payload(item)
        field_item = self._ancestor_field(item)
        field = self._payload(field_item)[1] if field_item is not None else None
        obj_label = obj_key = None
        if field_item is not None and item is not field_item and p:
            obj_label, obj_key = p[1], p[2]
        self.crumb.set(bc.trail(self.journey_name, self.plan.name if self.plan else None,
                                field, obj_label, obj_key or ""))
        self._inspect(item, p, field)

    def _inspect(self, item, payload, field):
        if payload is None:
            return
        kind, label, key = payload
        self.insp_title.setText(label)
        lines = []
        if kind == "field" and self.plan is not None:
            m = next((m for m in self.plan.members if m.name == label), None)
            if m:
                lines = [f"field id: {m.new_id}", f"source: real field {m.real_id}", f"mode: {m.mode}",
                         f"toml: {self.member_paths.get(label)}"]
        elif kind == "campaign" and self.plan is not None:
            g = C.campaign_graph(self.plan)
            lines = [f"{len(self.plan.members)} fields", f"entry: {g.entry or '(none)'}",
                     f"mod folder: {self.plan.mod_folder}",
                     f"unreachable: {len(g.unreachable)} · dead-ends: {len(g.dead_ends)}"]
        elif kind == "journey":
            lines = ["a playable arc (see docs/JOURNEYS.md)",
                     "authoring is the overworld / World-Hub lane"]
        elif field:
            lines = [f"in field: {field}", f"kind: {kind}"]
        self.insp_body.setText("\n".join(lines) if lines else "—")

    def _select_member(self, name):
        mi = getattr(self, "_member_items", {}).get(name)
        if mi is not None:
            self.tree.setCurrentItem(mi)
            self.tree.scrollToItem(mi)

    def _on_crumb(self, crumb):
        if crumb.level == bc.FIELD:
            self._select_member(crumb.key)
        elif crumb.level in (bc.JOURNEY, bc.CAMPAIGN):
            # select the matching root row
            root = self.tree.topLevelItem(0)
            target = crumb.key
            stack = [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
            while stack:
                it = stack.pop()
                p = self._payload(it)
                if p and p[2] == target:
                    self.tree.setCurrentItem(it)
                    return
                stack += [it.child(i) for i in range(it.childCount())]

    # ---- check (in-process) + lint (QProcess) ----
    def on_check(self):
        if self.plan is None:
            return
        try:
            errs, warns = C.lint_campaign(self.plan, self.campaign_path.parent)
        except Exception as e:                     # noqa: BLE001
            errs, warns = [f"lint failed: {e}"], []
        v = fb.classify(errs, warns, subject=f"Campaign lint ({self.plan.name})",
                        clean_headline=f"{self.plan.name} — no problems")
        self._show_problems(v, fb.problems(errs, warns))
        first = next((n.name for n in C.campaign_graph(self.plan).nodes
                      if not n.reachable or n.needs_export), None)
        if first:
            self._select_member(first)

    def _show_problems(self, verdict, problems):
        col = {fb.OK: self.pal["success"], fb.WARN: self.pal["warn"], fb.ERROR: self.pal["error"],
               fb.RUNNING: self.pal["muted"]}.get(verdict.level, self.pal["muted"])
        glyph = {fb.OK: "✓", fb.WARN: "⚠", fb.ERROR: "✕", fb.RUNNING: "…"}.get(verdict.level, "")
        tail = f"   —   {verdict.next_action}" if verdict.next_action else ""
        self.banner.setText(f"  {glyph}  {verdict.headline}{tail}")
        self.banner.setStyleSheet(
            f"background:{self.pal['surface']};color:{self.pal['text']};"
            f"border-left:4px solid {col};border-radius:6px;padding:9px;")
        self.banner.setVisible(True)
        self.problems.clear()
        for p in problems:
            it = QListWidgetItem(f"{'✕' if p.severity == fb.ERROR else '⚠'}  {p.message}")
            it.setForeground(QBrush(QColor(self.pal["error"] if p.severity == fb.ERROR else self.pal["warn"])))
            self.problems.addItem(it)
        self.dock_tabs.setCurrentWidget(self.problems_page)

    def run_cli_lint(self):
        if self.campaign_path is None:
            return
        self.output.clear()
        self._show_problems(fb.Verdict(fb.RUNNING, "Linting via CLI…"), [])
        self.dock_tabs.setCurrentWidget(self.output)
        self.proc = QProcess(self)
        self.proc.setProgram(sys.executable)
        self.proc.setArguments(["-m", "ff9mapkit", "lint-campaign", str(self.campaign_path)])
        self.proc.setWorkingDirectory(str(KIT))
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._drain_proc)
        self.proc.finished.connect(self._proc_done)
        self.proc.start()

    def _drain_proc(self):
        text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace").rstrip()
        if text:
            self.output.appendPlainText(text)

    def _proc_done(self, code, _status):
        v = fb.from_returncode(code, subject="Lint (CLI)", ok_headline="Lint (CLI) — done",
                               fail_hint="See the Output tab.")
        self._show_problems(v, [])


# --------------------------------------------------------------------------- entry point + smoke
def _smoke(win):
    """Offline self-test: build a 3-member campaign (one unreachable + a dangling edge), open it, and
    check the tree, the breadcrumb, lazy object load, and the Problems dock -- the Qt analogue of the
    tkinter campaign-editor smoke. Runs under QT_QPA_PLATFORM=offscreen."""
    import tempfile
    d = Path(tempfile.mkdtemp())
    M = C.Member
    members = [M(300, 30100, "IC_ENT", "borrow", 11, "", "IC_ENT/IC_ENT.field.toml", False),
               M(301, 30101, "IC_COR", "borrow", 11, "", "IC_COR/IC_COR.field.toml", False),
               M(302, 30102, "IC_LOST", "borrow", 11, "", "IC_LOST/IC_LOST.field.toml", False)]
    plan = C.CampaignPlan(name="ICE", mod_folder="M", id_base=30100, flag_base=C.FIRST_SAFE_FLAG,
                          flags_per_field=64, entry_name="IC_ENT", entry_entrance=0, members=members,
                          edges=[{"frm": "IC_ENT", "to": "IC_COR", "entrance": 2},
                                 {"frm": "IC_ENT", "to": "GHOST", "entrance": 0}], seams=[])
    (d / "campaign.toml").write_text(C.render_campaign_toml(plan), encoding="utf-8")
    for m in members:
        (d / m.name).mkdir(parents=True, exist_ok=True)
        (d / m.toml_rel).write_text(
            f'[field]\nid = {m.new_id}\nname = "{m.name}"\narea = 11\n\n[[npc]]\nname = "Guard"\n',
            encoding="utf-8")

    assert win.open_campaign(d / "campaign.toml")
    camp = win.tree.topLevelItem(0)                       # no journeys.toml -> campaign is the root
    assert win._payload(camp)[0] == "campaign"
    names = [win._payload(camp.child(i))[1] for i in range(camp.childCount())]
    assert names == ["IC_ENT", "IC_COR", "IC_LOST"], names
    # lazy object load: expand IC_ENT -> it gains object groups (incl. the NPC we wrote)
    ent = camp.child(0)
    win.tree.expandItem(ent)
    groups = [win._payload(ent.child(i))[1] for i in range(ent.childCount())]
    assert any(g.startswith("NPCs") for g in groups), groups
    # breadcrumb resolved campaign > field (no journey, no object yet)
    win.tree.setCurrentItem(ent)
    trail = bc.trail(win.journey_name, win.plan.name,
                     win._payload(win._ancestor_field(ent))[1], None, "")
    assert [c.level for c in trail] == ["campaign", "field"], trail
    # Check surfaces the dangling GHOST edge as a problem
    win.on_check()
    assert win.problems.count() >= 1
    assert any("GHOST" in win.problems.item(i).text() for i in range(win.problems.count()))
    print(f"workspace shell smoke ok: campaign>field tree ({len(names)} members), lazy objects, "
          f"breadcrumb, Problems dock ({win.problems.count()} rows); QProcess lint wired")


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    smoke = "--smoke" in argv
    if smoke:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    win = Workspace(pick_palette("dark" if smoke else "auto"))
    if smoke:
        _smoke(win)
        return
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
