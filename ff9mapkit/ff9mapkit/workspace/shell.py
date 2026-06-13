"""The PySide6 workspace shell (Qt UI) -- Phase 3 of the GUI makeover.

One dockable window: a left project tree (journey > campaign > field > object), a clickable breadcrumb,
a central document area, a right inspector, and a bottom Output/Problems dock. It reuses the kit's
tk-free backends verbatim -- :mod:`..editor.feedback` (Verdict/Problem), :mod:`..editor.breadcrumb`
(Crumb/trail), :mod:`..campaign` (CampaignPlan/graph), :mod:`..editor.model` (FieldDoc) -- so only this
view layer is Qt. Long jobs stream via ``QProcess`` (the Qt analogue of the tkinter apps' thread+queue).

Launch:  ``py apps/ff9_workspace.pyw``  (or ``py -m ff9mapkit.workspace.shell``).
"""

from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QAction, QBrush, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDockWidget, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSplitter,
    QTabWidget, QTextEdit, QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .. import campaign as C
from .. import save as _save
from ..editor import breadcrumb as bc
from ..editor import feedback as fb
from ..editor import forms
from ..editor.model import FieldDoc, protected_reason
from ..editor.theme import pick_palette
from .builddoc import BuildDoc
from .forms_qt import build_form, pick_catalog, read
from .importdoc import ImportDoc
from .mapview import CampaignMap
from .savedoc import ItemEquipDoc, StoryStateDoc
from .style import qss

KIT = Path(__file__).resolve().parents[2]          # the kit root (holds pyproject) -> `-m ff9mapkit` cwd
REPO = KIT.parent                                  # the repo root (holds tools/, apps/, .ff9deploy.toml)

# section key -> forms spec.  Single tables + the list-entity kinds the Qt editor can edit today.
# (cutscene steps + choice options are list-in-list sub-editors -- a Phase-4b follow-up.)
_SECTION_SPEC = {"field": forms.FIELD_SPEC, "encounter": forms.ENCOUNTER_SPEC, "music": forms.MUSIC_SPEC,
                 "dialogue": forms.DIALOGUE_SPEC, "npc": forms.NPC_SPEC, "gateway": forms.GATEWAY_SPEC,
                 "event": forms.EVENT_SPEC, "marker": forms.MARKER_SPEC}
_SINGLES = ("field", "encounter", "music", "dialogue")

# object groups inside a field.toml, mirroring the tkinter editor's tree (editor/app.py).
_SINGLE = [("dialogue", "Dialogue"), ("encounter", "Encounter"), ("music", "Music"), ("cutscene", "Cutscene")]
_LISTS = [("npc", "NPCs"), ("gateway", "Gateways"), ("event", "Events"), ("marker", "Markers"),
          ("choice", "Choices")]
_LIST_SINGULAR = {"npc": "NPC", "gateway": "Gateway", "event": "Event", "marker": "Marker", "choice": "Choice"}
# the default new entity per list kind -- mirrors the tkinter editor's _add_entity (editor/app.py).
_LIST_DEFAULTS = {
    "npc": {"name": "NPC", "preset": "vivi", "dialogue": "..."},
    "gateway": {"name": "door", "to": 100, "entrance": 0},
    "event": {"name": "event", "message": "..."},
    "marker": {"name": "spot", "pos": [0, 0]},
    "choice": {"npc": "", "prompt": "What'll it be?", "options": [{"text": "Yes"}, {"text": "No"}]},
}
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
        self._loose = None                         # the open standalone field's name (loose mode), else None
        self._docs = {}                            # member name -> loaded FieldDoc (cached, edited in place)
        self._clean = {}                           # member name -> deepcopy(doc.data) at load/last-save (dirty baseline)
        self._save_ctx = None                      # {member, key, spec, getters, single|kind, idx} for Save
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
        act_open_field = QAction("Open Field…", self)
        act_open_field.triggered.connect(self.on_open_field)
        tb.addAction(act_open_field)
        act_open_save = QAction("Open Save…", self)
        act_open_save.triggered.connect(self._open_save)
        tb.addAction(act_open_save)
        self.act_check = QAction("Check", self)
        self.act_check.triggered.connect(self.on_check)
        self.act_check.setEnabled(False)
        tb.addAction(self.act_check)
        self.act_lint_cli = QAction("Lint (CLI)", self)
        self.act_lint_cli.triggered.connect(self.run_cli_lint)
        self.act_lint_cli.setEnabled(False)
        tb.addAction(self.act_lint_cli)
        act_hub = QAction("Info Hub", self)
        act_hub.triggered.connect(self._open_catalog)
        tb.addAction(act_hub)
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred)
        tb.addWidget(spacer)
        search = QPushButton("⌕   Search content & commands   (Ctrl-K)")
        search.setObjectName("search")
        search.setFixedWidth(320)
        search.clicked.connect(self._open_palette)
        tb.addWidget(search)
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self._open_palette)

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
        self.tree.itemDoubleClicked.connect(self._on_tree_double)   # double-click = open (Editor / Map)
        split.addWidget(self.tree)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self._welcome()
        # the Editor tab: a scrollable host we refill with the selected node's form (Phase 4)
        self.doc_scroll = QScrollArea()
        self.doc_scroll.setWidgetResizable(True)
        self.doc_host = QWidget()
        self.doc_host_lay = QVBoxLayout(self.doc_host)
        self.doc_host_lay.setContentsMargins(14, 14, 14, 14)
        self.doc_host_lay.setSpacing(8)
        self.doc_scroll.setWidget(self.doc_host)
        self.tabs.addTab(self.doc_scroll, "Editor")
        self._doc_placeholder("Select a field or an object on the left to edit it.")
        self.map = CampaignMap(self.pal, on_open=self._select_member)   # the campaign graph as a document
        self.tabs.addTab(self.map, "Map")
        # the save docs route their console output to the bottom Output panel when docked (so the doc body
        # reclaims that height); standalone (output=None) they'd keep an in-pane console.
        self.story_state = StoryStateDoc(self.pal, output=self._save_output)       # save STATE layer (5b-i)
        self.tabs.addTab(self.story_state, "Story State")
        self.item_equip = ItemEquipDoc(self.pal, output=self._save_output)         # gil/inventory/equip (5b-ii)
        self.tabs.addTab(self.item_equip, "Item & Equip")
        # Phase 6b: Build & Deploy + Import folded in as documents (retiring the standalone tkinter apps).
        # They build argv via editor.jobs and stream through run_job -> the bottom Output panel.
        self.build_deploy = BuildDoc(self.pal, REPO, run=self.run_job, problems=self._show_problems)
        self.tabs.addTab(self.build_deploy, "Build & Deploy")
        self.import_field = ImportDoc(self.pal, KIT, run=self.run_job, problems=self._show_problems)
        self.tabs.addTab(self.import_field, "Import")
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
            "<p>The modern shell. <b>Open Campaign…</b> for a <code>campaign.toml</code>, or "
            "<b>Open Field…</b> for a standalone <code>field.toml</code>; the left tree shows "
            "<b>journey ▸ campaign ▸ field ▸ object</b>, the breadcrumb tracks where you are, and "
            "<b>Check</b> fills the Problems dock.</p>"
            "<p>One window, every tool: <b>Editor</b> (fields, NPCs, gateways, cutscenes, choices) · "
            "<b>Map</b> · <b>Story State</b> + <b>Item &amp; Equip</b> save editors · <b>Build &amp; "
            "Deploy</b> · <b>Import</b> (fork a real field). Press <b>Ctrl-K</b> to jump anywhere.</p>"
            "<p style='color:gray'>This shell wraps the same tk-free backends the kit's CLI uses.</p>")
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

    def on_open_field(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open a field.toml", "",
                                           "Field (*.field.toml);;TOML (*.toml);;All files (*)")
        if f:
            self.open_field(Path(f))

    def _save_output(self, text):
        """Sink for the docked save editors' Preview/Apply output -> the bottom Output panel (console's
        natural home), so a docked save doc doesn't spend its body height on its own console box."""
        self.output.setPlainText(text)
        self.dock_tabs.setCurrentWidget(self.output)

    def _open_save(self):
        """Open a save into BOTH save documents (story state + item/equip) -- a cross-cutting document,
        not a field. The two read different parts of the same file via different backends."""
        f, _ = QFileDialog.getOpenFileName(self, "Open a save (SavedData_ww.dat / extra-save / JSON)",
                                            _save.default_save_dir() or "",
                                            "FF9 save (*.dat);;Save JSON / Base64 (*.json *.txt);;All files (*)")
        if not f:
            return
        self.story_state.load(f)
        self.item_equip.load(f)
        self.tabs.setCurrentWidget(self.story_state)

    def open_field(self, path) -> bool:
        """Open a STANDALONE field.toml (no campaign) -- the 'Loose field' mode, so any authored field
        can be edited directly. Mirrors the tkinter editor opening a lone file."""
        if not self._maybe_prompt_unsaved():
            return False
        path = Path(path)
        try:
            doc = FieldDoc.load(path)
        except Exception as e:                     # noqa: BLE001
            self.statusBar().showMessage(f"Open failed: {e}")
            return False
        name = (doc.data.get("field", {}) or {}).get("name") or path.stem
        self.plan = None
        self.campaign_path = None
        self.journey_name = None
        self._loose = name
        self.member_paths = {name: path.resolve()}
        self._docs = {name: doc}
        self._clean = {name: copy.deepcopy(doc.data)}
        self.map.clear()                           # a standalone field has no campaign map
        self.build_deploy.set_target(path)         # pre-aim Build & Deploy at the open field
        self.act_check.setEnabled(True)
        self.act_lint_cli.setEnabled(False)       # lint-campaign is campaign-only
        self._populate_field(name)
        self.statusBar().showMessage(f"{name} — standalone field — {path}")
        self._select_member(name)
        self.tabs.setCurrentWidget(self.doc_scroll)   # a standalone field has no map -> show its Editor
        return True

    def _populate_field(self, name):
        self.tree.clear()
        self._member_items = {}
        mi = self._mk("field", name, name, "•")
        self.tree.addTopLevelItem(mi)
        self._member_items[name] = mi
        mi.addChild(self._mk("__lazy__", "loading…"))   # lazy object load on expand (same as a member)
        mi.setExpanded(True)

    def open_campaign(self, path) -> bool:
        if not self._maybe_prompt_unsaved():
            return False
        path = Path(path)
        try:
            plan = C.load_campaign(path)
        except Exception as e:                     # noqa: BLE001
            self.statusBar().showMessage(f"Open failed: {e}")
            return False
        self.plan = plan
        self._loose = None                         # leaving loose mode -> a real campaign is open
        self.campaign_path = path
        self.member_paths = {m.name: (path.parent / m.toml_rel).resolve() for m in plan.members}
        self.journey_name = self._journey_label()
        self._docs = {}
        self._clean = {}
        self.build_deploy.set_target(path)         # pre-aim Build & Deploy at the open campaign
        self.act_check.setEnabled(True)
        self.act_lint_cli.setEnabled(True)
        self._populate()
        self.statusBar().showMessage(
            f"{plan.name} — {len(plan.members)} fields — mod folder {plan.mod_folder}")
        g = C.campaign_graph(plan)
        entry = g.entry or (plan.members[0].name if plan.members else None)
        self.map.render(g, entry)
        if entry:
            self._select_member(entry)
        self.tabs.setCurrentWidget(self.map)       # open a campaign -> land on its Map (its overview)
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

    def _doc(self, member):
        """The member's FieldDoc, loaded once and cached (the form edits this instance + saves it)."""
        if member not in self._docs:
            self._docs[member] = FieldDoc.load(self.member_paths[member])
            self._clean[member] = copy.deepcopy(self._docs[member].data)   # dirty baseline
        return self._docs[member]

    def _mark_clean(self, member):
        """Snapshot a member's doc as the saved baseline (so _dirty_members no longer flags it)."""
        if member in self._docs:
            self._clean[member] = copy.deepcopy(self._docs[member].data)

    def _dirty_members(self):
        """Cached members whose in-memory doc differs from its load/last-save baseline."""
        return [m for m in self._docs if self._docs[m].data != self._clean.get(m)]

    def _load_objects(self, member_item):
        name = self._payload(member_item)[1]
        try:
            data = self._doc(name).data
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
                lbl = forms.choice_summary(e) if key == "choice" else (e.get("name") or f"#{i}")
                grp.addChild(self._mk("object", lbl, f"{key}:{i}"))
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
        if not self._commit_active():              # fold the leaving form into the doc; stay put on a bad value
            return
        p = self._payload(item)
        field_item = self._ancestor_field(item)
        field = self._payload(field_item)[1] if field_item is not None else None
        obj_label = obj_key = None
        if field_item is not None and item is not field_item and p:
            obj_label, obj_key = p[1], p[2]
        self.crumb.set(bc.trail(self.journey_name, self.plan.name if self.plan else None,
                                field, obj_label, obj_key or ""))
        self._inspect(item, p, field)
        if field and getattr(self, "map", None) is not None:
            self.map.highlight(field)              # keep the Map in sync, but DON'T steal the active tab
        if field_item is not None and p:
            member = self._payload(field_item)[1]
            if item is field_item:                 # the member row itself -> its Field form
                self._open_editor(member, "field", "field")
            else:                                  # an object/group under it -> edit by its key
                self._open_editor(member, p[0], p[2])

    def _on_tree_double(self, item, _col=0):
        """Double-click = explicit 'open': a field/object goes to the Editor, a campaign/journey root to
        the Map. (Single-click only selects + highlights, so browsing the tree doesn't steal your tab.)"""
        p = self._payload(item)
        if p:
            self.tabs.setCurrentWidget(self.map if p[0] in ("campaign", "journey") else self.doc_scroll)

    # ---- command palette (Ctrl-K) ----
    def _command_index(self):
        """The palette's entries: named commands + every navigable node currently in the tree (members
        always; a field's objects once it's been expanded)."""
        cmds = [
            ("Open Campaign…", "command", self.on_open_campaign),
            ("Open Field…", "command", self.on_open_field),
            ("Open Save…", "command", self._open_save),
            ("Check", "command", self.on_check),
            ("Lint (CLI)", "command", self.run_cli_lint),
            ("Browse catalog (Info Hub)", "command", self._open_catalog),
            ("Go to Editor", "view", lambda: self.tabs.setCurrentWidget(self.doc_scroll)),
            ("Go to Map", "view", lambda: self.tabs.setCurrentWidget(self.map)),
            ("Go to Story State", "view", lambda: self.tabs.setCurrentWidget(self.story_state)),
            ("Go to Item & Equip", "view", lambda: self.tabs.setCurrentWidget(self.item_equip)),
            ("Go to Build & Deploy", "view", lambda: self.tabs.setCurrentWidget(self.build_deploy)),
            ("Go to Import", "view", lambda: self.tabs.setCurrentWidget(self.import_field)),
        ]
        content = []

        def walk(item):
            p = self._payload(item)
            if p and p[0] in ("journey", "campaign", "field", "object", "group"):
                content.append((self._palette_label(item, p), p[0], lambda it=item: self._goto_tree(it)))
            for i in range(item.childCount()):
                walk(item.child(i))
        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))
        return cmds + content

    def _palette_label(self, item, p):
        fa = self._ancestor_field(item)
        if fa is not None and item is not fa:                # an object -> qualify it with its field
            return f"{self._payload(fa)[1]} ▸ {p[1]}"
        return p[1]

    def _goto_tree(self, item):
        self.tree.setCurrentItem(item)
        self.tree.scrollToItem(item)
        self._on_tree_double(item)                           # palette nav = explicit open -> switch tab

    def _open_palette(self):
        from .palette import CommandPalette
        CommandPalette(self, self._command_index(), self.pal).exec()

    def _open_catalog(self):
        """Browse the whole Info Hub catalog (models / archetypes / props / creatures / items / scenes /
        fields) in one searchable picker -- the standalone Info Hub browser, folded into the Workspace.
        browse=True: 'Copy name' copies the selected entry + keeps the window open; no result cap (the
        full ~2k-entry catalog, not the picker's 300)."""
        from .forms_qt import CatalogPicker
        CatalogPicker(self, None, "", self.plan, self.pal, browse=True, limit=None).exec()

    # ---- the document editor (Phase 4) ----
    def _clear_doc(self):
        self._save_ctx = None                      # the about-to-be-removed form is no longer the active one
        while self.doc_host_lay.count():
            it = self.doc_host_lay.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    def _doc_placeholder(self, text):
        self._clear_doc()
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{self.pal['muted']};")
        lbl.setWordWrap(True)
        self.doc_host_lay.addWidget(lbl)
        self.doc_host_lay.addStretch(1)
        self._save_ctx = None

    def _open_editor(self, member, kind, key):
        """Mount the form for the selected node into the Editor tab. ``kind`` is the item kind
        ('field'|'object'|'group'|...); ``key`` is the section/object key ('field', 'npc:2', ...)."""
        try:
            doc = self._doc(member)
        except Exception as e:                     # noqa: BLE001
            self._doc_placeholder(f"Could not load {member}: {e}")
            return
        if key == "camera":
            self._doc_placeholder("Camera / walkmesh / layers / positions are SPATIAL — author them in "
                                  "Blender (FF9 Map Kit add-on). This shell owns the logic only.")
            return
        if key in _SINGLES:                        # a single table (field/encounter/music/dialogue)
            spec = _SECTION_SPEC[key]
            self._mount_form(member, key, spec, doc.data.get(key, {}) or {}, single=True, section=key)
            return
        if key == "cutscene":                      # a single table + an ordered step list (sub-editor)
            self._mount_cutscene(member)
            return
        if ":" in key and key.split(":")[0] == "choice":        # a choice + its options (sub-editor)
            self._mount_choice(member, int(key.split(":")[1]))
            return
        if ":" in key and key.split(":")[0] in _SECTION_SPEC:   # a list entity (npc:2, gateway:0, ...)
            k, idx = key.split(":")
            idx = int(idx)
            lst = doc.data.get(k, []) or []
            if idx < len(lst):
                self._mount_form(member, key, _SECTION_SPEC[k], lst[idx], single=False, section=k, idx=idx)
            return
        if kind == "group" and key in _LIST_DEFAULTS:   # a list header (NPCs (n)) -> an Add button + count
            self._mount_group(member, key)
            return
        self._doc_placeholder(f"'{key}' isn't editable in the Workspace yet.")

    def _mount_group(self, member, kind):
        """The list-header view: an 'Add <kind>' button + the count. (Selecting an item under it edits it;
        this header is where you create a new one.)"""
        self._clear_doc()
        sing = _LIST_SINGULAR.get(kind, kind)
        n = len(self._doc(member).data.get(kind, []) or [])
        self._header(f"{member}  ·  {sing}s",
                     f"{n} {sing.lower()}(s) on this field. Add a new one below, or pick an existing item "
                     "in the tree to edit it.")
        btn = QPushButton(f"➕  Add {sing}")
        btn.setObjectName("accent")
        btn.clicked.connect(lambda _=False: self._add_list_item(member, kind))
        self.doc_host_lay.addWidget(btn, alignment=Qt.AlignLeft)
        self.doc_host_lay.addStretch(1)

    def _add_list_item(self, member, kind):
        """Append a default entity to ``member``'s ``kind`` list, refresh the tree, and open the new item's
        editor (so you land straight in the form to fill it in)."""
        doc = self._doc(member)
        lst = doc.data.setdefault(kind, [])
        lst.append(copy.deepcopy(_LIST_DEFAULTS[kind]))
        idx = len(lst) - 1
        self.tree.blockSignals(True)                 # rebuild the object subtree without spurious selections
        self._refresh_objects(member)
        self.tree.blockSignals(False)
        self._select_object(member, f"{kind}:{idx}")  # fires _on_select -> mounts the new item's form
        self.tabs.setCurrentWidget(self.doc_scroll)   # adding is an explicit edit -> show the Editor

    def _refresh_objects(self, member):
        """Rebuild a member's object subtree in place (after an add) so the new item + updated count show."""
        mi = getattr(self, "_member_items", {}).get(member)
        if mi is None:
            return
        mi.takeChildren()
        self._load_objects(mi)
        mi.setExpanded(True)

    def _object_item(self, member, key):
        """The QTreeWidgetItem for object ``key`` (e.g. 'npc:2') under ``member``, or None (walks the
        member's loaded object subtree). Used to locate a row by key -- never assume it's the selection."""
        mi = getattr(self, "_member_items", {}).get(member)
        if mi is None:
            return None
        stack = [mi.child(i) for i in range(mi.childCount())]
        while stack:
            it = stack.pop()
            p = self._payload(it)
            if p and p[0] == "object" and p[2] == key:
                return it
            stack += [it.child(i) for i in range(it.childCount())]
        return None

    def _select_object(self, member, key):
        """Select the object node ``key`` (e.g. 'npc:2') under ``member``."""
        it = self._object_item(member, key)
        if it is not None:
            self.tree.setCurrentItem(it)
            self.tree.scrollToItem(it)

    def _pick(self, catalog, current):
        """``build_form``'s picker: open the Qt catalog picker over the open campaign's context."""
        return pick_catalog(self, catalog, current, self.plan, self.pal)

    def _header(self, title, note=None):
        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight:600;font-size:15px;")
        self.doc_host_lay.addWidget(lbl)
        if note:
            h = QLabel(note)
            h.setWordWrap(True)
            h.setStyleSheet(f"color:{self.pal['muted']};")
            self.doc_host_lay.addWidget(h)

    def _wrap_width(self, member):
        """The FF9-window wrap width for this field's dialogue preview, from its ``[dialogue] wrap`` (a
        number, default 28), or None when ``wrap = false`` (author wraps by hand -> preview shows raw)."""
        from ..content.text import DEFAULT_WRAP_WIDTH
        doc = self._docs.get(member)
        w = (doc.data.get("dialogue", {}) or {}).get("wrap") if doc else None
        if w is False:
            return None
        if w is None:
            return DEFAULT_WRAP_WIDTH
        try:
            return float(w)
        except (TypeError, ValueError):
            return DEFAULT_WRAP_WIDTH

    def _mount_form(self, member, key, spec, entity, *, single, section, idx=None):
        self._clear_doc()
        self._header(f"{member}  ·  {key}", forms.SECTION_HELP.get(section))
        form, getters = build_form(spec, forms.entity_to_values(spec, entity), self.pal, pick=self._pick,
                                   wrap_width=self._wrap_width(member))
        self.doc_host_lay.addWidget(form)
        self._save_ctx = {"member": member, "key": key, "spec": spec, "getters": getters,
                          "single": single, "section": section, "idx": idx}
        self._add_save(self._save)

    def _add_save(self, handler):
        save = QPushButton("Save")
        save.setObjectName("accent")
        save.clicked.connect(lambda _=False: handler())
        self.doc_host_lay.addWidget(save, alignment=Qt.AlignLeft)
        self.doc_host_lay.addStretch(1)
        # NB: mounting a form no longer steals the active tab -- single-click selection stays put
        # (you reach the Editor via the tab or a double-click; see _on_tree_double).

    def _save(self):
        ctx = self._save_ctx
        if ctx:
            self._commit(ctx["member"], ctx["section"], ctx["spec"], ctx["getters"],
                         single=ctx["single"], idx=ctx["idx"], key=ctx["key"])

    def _commit(self, member, section, spec, getters, *, single, idx=None, key=None) -> bool:
        """Apply a form's values to the doc (clear the spec's keys, keep scene/unknown ones) + save.
        Shared by the simple forms and the cutscene/choice sub-editors. Returns True on success."""
        try:
            entity = forms.build_entity(spec, read(getters))
        except ValueError as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Invalid value — not saved"),
                                [fb.Problem(fb.ERROR, str(e))])
            return False
        reason = protected_reason(self.member_paths[member])      # don't overwrite a bundled/golden file
        if reason:
            self._show_problems(fb.Verdict(fb.ERROR, "Can't save here"),
                                [fb.Problem(fb.ERROR, f"{reason}. Save a copy in a folder of your own.")])
            return False
        doc = self._doc(member)
        target = doc.data.setdefault(section, {}) if single else doc.data.get(section, [])[idx]
        for f in spec:
            target.pop(f.key, None)
        target.update(entity)
        try:
            doc.save()
        except Exception as e:                     # noqa: BLE001
            self._show_problems(fb.Verdict(fb.ERROR, "Save failed"), [fb.Problem(fb.ERROR, str(e))])
            return False
        self._mark_clean(member)
        self._show_problems(fb.Verdict(fb.OK, f"Saved {member} · {key or section}",
                                       f"wrote {self.member_paths[member].name}"), [])
        if not single and "name" in entity:        # a renamed list entity -> refresh ITS tree row (located
            it = self._object_item(member, key)     # by key, NOT the selection -- a save needn't be selected)
            if it is not None:
                it.setText(0, entity["name"])
                it.setData(0, _ROLE, ("object", entity["name"], key))
        return True

    def _commit_active(self) -> bool:
        """Fold the currently-mounted form back into the IN-MEMORY doc (NO disk write), so navigating to
        another node doesn't silently lose edits (parity with the tkinter editor's _commit_active before
        _show). Returns False (+ surfaces the error) on an invalid value so the caller can keep the user
        on the form. Cutscene steps / choice options are already mutated live; this covers the header form."""
        ctx = self._save_ctx
        if not ctx:
            return True
        try:
            entity = forms.build_entity(ctx["spec"], read(ctx["getters"]))
        except ValueError as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Invalid value — fix it before leaving this form"),
                                [fb.Problem(fb.ERROR, str(e))])
            return False
        doc = self._docs.get(ctx["member"])
        if doc is None:
            return True
        if ctx["single"]:
            target = doc.data.setdefault(ctx["section"], {})
        else:
            lst = doc.data.get(ctx["section"], []) or []
            if ctx["idx"] is None or ctx["idx"] >= len(lst):
                return True
            target = lst[ctx["idx"]]
        for f in ctx["spec"]:
            target.pop(f.key, None)
        target.update(entity)
        return True

    def _ensure_saved(self) -> bool:
        """Commit the active form + write its doc to disk so Check validates the CURRENT edits, not stale
        bytes (parity with the tkinter editor's _ensure_saved). Skips a protected file."""
        if not self._commit_active():
            return False
        member = (self._save_ctx or {}).get("member") or self._loose
        if not member or member not in self._docs:
            return True
        path = self.member_paths.get(member)
        if path is None or protected_reason(path):
            return True
        try:
            self._docs[member].save()
        except Exception as e:                     # noqa: BLE001
            self._show_problems(fb.Verdict(fb.ERROR, "Couldn't save before Check"),
                                [fb.Problem(fb.ERROR, str(e))])
            return False
        self._mark_clean(member)
        return True

    def _maybe_prompt_unsaved(self) -> bool:
        """Before a file switch / window close: fold the active form in, and if any cached field has
        unsaved edits, offer Save / Discard / Cancel. Returns False ONLY on Cancel (caller aborts).
        Headless/offscreen never blocks (returns True)."""
        self._commit_active()                      # the in-progress form's edits count toward dirty
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return True
        dirty = self._dirty_members()
        if not dirty:
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved changes")
        box.setText(f"{len(dirty)} field(s) have unsaved changes: {', '.join(dirty)}.")
        box.setInformativeText("Save them before continuing?")
        box.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                               | QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        choice = box.exec()
        if choice == QMessageBox.StandardButton.Cancel:
            return False
        if choice == QMessageBox.StandardButton.Save:
            for m in dirty:
                path = self.member_paths.get(m)
                if path is None or protected_reason(path):
                    continue
                try:
                    self._docs[m].save()
                    self._mark_clean(m)
                except Exception:                  # noqa: BLE001 -- best-effort; a protected/locked file
                    pass
        return True

    def closeEvent(self, event):                   # noqa: N802 (Qt override)
        if self._maybe_prompt_unsaved():
            event.accept()
        else:
            event.ignore()

    # ---- cutscene + choice sub-editors (Phase 4b) ----
    def _list_buttons(self, pairs):
        """A horizontal row of buttons from (label, callback) pairs, returned as a QWidget."""
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        for label, cb in pairs:
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, c=cb: c())
            h.addWidget(b)
        h.addStretch(1)
        return w

    def _mount_cutscene(self, member):
        doc = self._doc(member)
        cs = doc.data.setdefault("cutscene", {})
        cs.setdefault("steps", [])
        self._clear_doc()
        self._header(f"{member}  ·  cutscene", forms.SECTION_HELP.get("cutscene"))
        form, getters = build_form(forms.CUTSCENE_SPEC, forms.entity_to_values(forms.CUTSCENE_SPEC, cs),
                                   self.pal, pick=self._pick, wrap_width=self._wrap_width(member))
        self.doc_host_lay.addWidget(form)
        self.doc_host_lay.addWidget(QLabel("Steps (run in order; control is locked):"))

        body = QWidget()
        row = QHBoxLayout(body)
        row.setContentsMargins(0, 0, 0, 0)
        steps_list = QListWidget()
        row.addWidget(steps_list, 1)
        side = QWidget()
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 0)
        type_combo = QComboBox()
        for k in forms.STEP_KIND:
            type_combo.addItem(forms.STEP_LABEL[k], k)
        value_edit = QLineEdit()
        hint = QLabel("")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{self.pal['muted']};font-size:11px;")
        sv.addWidget(QLabel("Type:"))
        sv.addWidget(type_combo)
        sv.addWidget(QLabel("Value:"))
        sv.addWidget(value_edit)
        sv.addWidget(hint)

        def reload_steps(select=None):
            steps_list.clear()
            for st in cs["steps"]:
                steps_list.addItem(forms.step_summary(st))
            if select is not None and 0 <= select < steps_list.count():
                steps_list.setCurrentRow(select)

        def on_type(_i=0):
            hint.setText(forms.STEP_HELP.get(type_combo.currentData(), ""))
        type_combo.currentIndexChanged.connect(on_type)

        def on_select(r):
            if 0 <= r < len(cs["steps"]):
                st = cs["steps"][r]
                k = forms.step_key(st)
                if k in forms.STEP_KIND:
                    type_combo.setCurrentIndex(list(forms.STEP_KIND).index(k))
                value_edit.setText(forms.step_value_text(st))
        steps_list.currentRowChanged.connect(on_select)

        def add_update():
            try:
                step = forms.make_step(type_combo.currentData(), value_edit.text())
            except ValueError as e:
                self._show_problems(fb.Verdict(fb.ERROR, "Bad step"), [fb.Problem(fb.ERROR, str(e))])
                return
            r = steps_list.currentRow()
            if 0 <= r < len(cs["steps"]) and forms.step_key(cs["steps"][r]) == forms.step_key(step):
                cs["steps"][r] = step
            else:
                cs["steps"].append(step)
                r = len(cs["steps"]) - 1
            reload_steps(r)

        def remove():
            r = steps_list.currentRow()
            if 0 <= r < len(cs["steps"]):
                cs["steps"].pop(r)
                reload_steps()

        def move(d):
            r = steps_list.currentRow()
            j = r + d
            if 0 <= r < len(cs["steps"]) and 0 <= j < len(cs["steps"]):
                cs["steps"][r], cs["steps"][j] = cs["steps"][j], cs["steps"][r]
                reload_steps(j)

        sv.addWidget(self._list_buttons([("Add / Update", add_update), ("Remove", remove),
                                         ("Up", lambda: move(-1)), ("Down", lambda: move(1))]))
        sv.addStretch(1)
        row.addWidget(side)
        self.doc_host_lay.addWidget(body)
        reload_steps()
        on_type()
        self._save_ctx = {"member": member, "key": "cutscene", "spec": forms.CUTSCENE_SPEC,
                          "getters": getters, "single": True, "section": "cutscene", "idx": None}
        self._add_save(lambda: self._commit(member, "cutscene", forms.CUTSCENE_SPEC, getters, single=True))

    def _mount_choice(self, member, idx):
        doc = self._doc(member)
        lst = doc.data.get("choice", [])
        if idx >= len(lst):
            self._doc_placeholder("choice not found")
            return
        ch = lst[idx]
        ch.setdefault("options", [])
        self._clear_doc()
        self._header(f"{member}  ·  choice[{idx}]", forms.SECTION_HELP.get("choice"))
        form, getters = build_form(forms.CHOICE_SPEC, forms.entity_to_values(forms.CHOICE_SPEC, ch),
                                   self.pal, pick=self._pick, wrap_width=self._wrap_width(member))
        self.doc_host_lay.addWidget(form)
        self.doc_host_lay.addWidget(QLabel("Options (top-to-bottom; Cancel/B picks the last):"))
        opts_list = QListWidget()
        self.doc_host_lay.addWidget(opts_list)
        opt_host = QWidget()
        opt_lay = QVBoxLayout(opt_host)
        opt_lay.setContentsMargins(0, 0, 0, 0)
        self.doc_host_lay.addWidget(opt_host)
        st = {"getters": None}

        def reload_opts(select=None):
            opts_list.blockSignals(True)
            opts_list.clear()
            for o in ch["options"]:
                opts_list.addItem(forms.option_summary(o))
            opts_list.blockSignals(False)
            if select is not None and 0 <= select < opts_list.count():
                opts_list.setCurrentRow(select)

        def show_opt(o):
            while opt_lay.count():
                w = opt_lay.takeAt(0).widget()
                if w:
                    w.deleteLater()
            f, g = build_form(forms.CHOICE_OPTION_SPEC, forms.entity_to_values(forms.CHOICE_OPTION_SPEC, o),
                              self.pal, pick=self._pick, wrap_width=self._wrap_width(member))
            opt_lay.addWidget(f)
            st["getters"] = g

        def on_select(r):
            if 0 <= r < len(ch["options"]):
                show_opt(ch["options"][r])
        opts_list.currentRowChanged.connect(on_select)

        def add_new():
            ch["options"].append({"text": "New"})
            reload_opts(len(ch["options"]) - 1)

        def update_sel():
            r = opts_list.currentRow()
            if not (0 <= r < len(ch["options"])) or not st["getters"]:
                return
            try:
                opt = forms.build_entity(forms.CHOICE_OPTION_SPEC, read(st["getters"]))
            except ValueError as e:
                self._show_problems(fb.Verdict(fb.ERROR, "Bad option"), [fb.Problem(fb.ERROR, str(e))])
                return
            if not opt.get("text"):
                self._show_problems(fb.Verdict(fb.ERROR, "Bad option"),
                                    [fb.Problem(fb.ERROR, "An option needs text (the menu row shown).")])
                return
            ch["options"][r] = opt
            reload_opts(r)

        def remove():
            r = opts_list.currentRow()
            if 0 <= r < len(ch["options"]):
                ch["options"].pop(r)
                reload_opts()

        def move(d):
            r = opts_list.currentRow()
            j = r + d
            if 0 <= r < len(ch["options"]) and 0 <= j < len(ch["options"]):
                ch["options"][r], ch["options"][j] = ch["options"][j], ch["options"][r]
                reload_opts(j)

        self.doc_host_lay.addWidget(self._list_buttons(
            [("Add new", add_new), ("Update", update_sel), ("Remove", remove),
             ("Up", lambda: move(-1)), ("Down", lambda: move(1))]))
        reload_opts(0 if ch["options"] else None)
        self._save_ctx = {"member": member, "key": f"choice:{idx}", "spec": forms.CHOICE_SPEC,
                          "getters": getters, "single": False, "section": "choice", "idx": idx}
        self._add_save(lambda: self._commit(member, "choice", forms.CHOICE_SPEC, getters,
                                            single=False, idx=idx, key=f"choice:{idx}"))

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
        if not self._ensure_saved():               # validate the CURRENT edits, not stale on-disk bytes
            return
        if self.plan is None:
            if self._loose:
                self._check_loose()
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

    def _check_loose(self):
        """Validate + lint the open standalone field (no campaign), via the same build-layer checks the
        tkinter editor uses."""
        from ..build import FieldProject, lint_logic, validate
        try:
            p = FieldProject.load(self.member_paths[self._loose])
            errs, warns = validate(p), lint_logic(p)
        except Exception as e:                     # noqa: BLE001
            errs, warns = [f"check failed: {e}"], []
        v = fb.classify(errs, warns, subject=f"Check {self._loose}",
                        clean_headline=f"{self._loose} — no problems")
        self._show_problems(v, fb.problems(errs, warns))

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

    def run_job(self, argv, *, cwd=None, subject="Job", ok_headline=None, ok_next="",
                fail_hint="See the Output tab.", on_finished=None):
        """Run ONE streaming subprocess job (lint / build / deploy / import): stream its stdout into the
        Output panel, then post a returncode verdict to Problems. ``argv[0]`` is the program. Returns
        ``False`` (and starts nothing) if a job is already running, else ``True``; ``on_finished(code)``
        fires after the verdict. The shell owns the single QProcess + the console plumbing -- the Build /
        Import docs only build the argv (the Qt analogue of the tkinter apps' thread+queue)."""
        if getattr(self, "proc", None) and self.proc.state() != QProcess.ProcessState.NotRunning:
            return False
        self._job = (subject, ok_headline, ok_next, fail_hint, on_finished)
        self.output.clear()
        self._show_problems(fb.Verdict(fb.RUNNING, f"{subject}…"), [])
        self.dock_tabs.setCurrentWidget(self.output)
        self.act_lint_cli.setEnabled(False)
        self.proc = QProcess(self)
        self.proc.setProgram(str(argv[0]))
        self.proc.setArguments([str(a) for a in argv[1:]])
        self.proc.setWorkingDirectory(str(cwd or KIT))
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._drain_proc)
        self.proc.finished.connect(self._proc_done)
        self.proc.start()
        return True

    def run_cli_lint(self):
        if self.campaign_path is None:
            return
        self.run_job([sys.executable, "-m", "ff9mapkit", "lint-campaign", str(self.campaign_path)],
                     cwd=KIT, subject="Lint (CLI)", ok_headline="Lint (CLI) — done")

    def _drain_proc(self):
        text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace").rstrip()
        if text:
            self.output.appendPlainText(text)

    def _proc_done(self, code, _status):
        self.act_lint_cli.setEnabled(self.campaign_path is not None)
        subject, ok_headline, ok_next, fail_hint, on_finished = getattr(
            self, "_job", ("Job", None, "", "See the Output tab.", None))
        v = fb.from_returncode(code, subject=subject, ok_headline=ok_headline, ok_next=ok_next,
                               fail_hint=fail_hint)
        self._show_problems(v, [])
        if on_finished:
            on_finished(code)


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
    # the campaign Map document renders the same graph (compute_layout core) -- 3 nodes, 1 edge
    assert win.map._layout is not None and len(win.map._layout.nodes) == 3
    assert len(win.map._layout.edges) == 1
    assert win.map._scene.items()                       # the scene actually drew something
    # 6a: the command palette indexes commands + content; fuzzy filter + run-to-navigate (campaign loaded)
    from .palette import CommandPalette, fuzzy
    assert fuzzy("opncmp", "open campaign…") and not fuzzy("zzz", "open campaign")
    entries = win._command_index()
    labels = [e[0] for e in entries]
    assert "Open Campaign…" in labels and "IC_ENT" in labels, labels[:8]
    pal = CommandPalette(win, entries, win.pal)
    pal.q.setText("iccor")                              # subsequence -> IC_COR
    assert any("IC_COR" in e[0] for e in pal._filtered), [e[0] for e in pal._filtered]
    pal.q.setText("opncmp")                             # subsequence -> Open Campaign ranks first
    assert pal._filtered and "Open Campaign" in pal._filtered[0][0], [e[0] for e in pal._filtered[:3]]
    next(e for e in entries if e[0] == "IC_COR")[2]()   # run the content entry -> selects IC_COR in the tree
    assert win._payload(win.tree.currentItem())[1] == "IC_COR"
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
    # Phase 4: the document editor -- open the NPC form, Save (round-trip), confirm it persisted to disk
    import tomllib
    win._open_editor("IC_ENT", "object", "npc:0")
    assert win._save_ctx and win._save_ctx["section"] == "npc"
    win._save()
    saved = tomllib.loads((d / "IC_ENT" / "IC_ENT.field.toml").read_text(encoding="utf-8"))
    assert saved["npc"][0]["name"] == "Guard", saved
    win._open_editor("IC_ENT", "field", "field")       # a single-table section
    assert win._save_ctx["single"] and win._save_ctx["section"] == "field"
    win._save()
    saved = tomllib.loads((d / "IC_ENT" / "IC_ENT.field.toml").read_text(encoding="utf-8"))
    assert saved["field"]["id"] == 30100 and saved["field"]["name"] == "IC_ENT", saved
    # H1: commit-on-switch keeps uncommitted form edits (no Save) -- simulate a widget edit, then switch
    win._open_editor("IC_ENT", "object", "npc:0")
    win._save_ctx["getters"]["dialogue"] = lambda: "EDITED ON SWITCH"   # as if the user typed it
    assert win._commit_active() is True                # what _on_select runs before mounting the next node
    assert win._doc("IC_ENT").data["npc"][0]["dialogue"] == "EDITED ON SWITCH"
    # H1: an INVALID value blocks the switch (returns False), mirroring tkinter's _commit_active
    win._open_editor("IC_ENT", "field", "field")
    win._save_ctx["getters"]["id"] = lambda: "not-a-number"
    assert win._commit_active() is False
    win._open_editor("IC_ENT", "field", "field")       # re-mount clears the simulated bad value
    # ADD list items: the group header's Add button appends a default entity, refreshes the tree, and opens
    # the new item's form (so authoring a brand-new NPC/gateway/choice works, not just editing existing ones)
    nbefore = len(win._doc("IC_ENT").data.get("npc", []))
    win._add_list_item("IC_ENT", "npc")
    npcs = win._doc("IC_ENT").data["npc"]
    assert len(npcs) == nbefore + 1 and npcs[-1]["name"] == "NPC", npcs
    assert win._save_ctx["section"] == "npc" and win._save_ctx["idx"] == nbefore   # new item's form is mounted
    assert win._payload(win.tree.currentItem()) == ("object", "NPC", f"npc:{nbefore}")   # tree refreshed+selected
    win._add_list_item("IC_ENT", "gateway")            # a different list kind
    assert win._doc("IC_ENT").data["gateway"][-1]["to"] == 100 and win._save_ctx["section"] == "gateway"
    win._add_list_item("IC_ENT", "choice")             # a choice routes to the choice sub-editor
    assert win._doc("IC_ENT").data["choice"][-1]["prompt"] == "What'll it be?"
    # the Qt form renderer round-trips through build_entity (the SAME parser as the tkinter editor)
    sample = {"name": "Vivi", "preset": "vivi", "dialogue": "hi"}
    _w, _g = build_form(forms.NPC_SPEC, forms.entity_to_values(forms.NPC_SPEC, sample), win.pal)
    assert forms.build_entity(forms.NPC_SPEC, read(_g)) == sample, read(_g)
    # the live dialogue wrap-preview: an NPC's dialogue field renders the kit's FF9-window break points
    from .. import dialogue as _dlg
    from PySide6.QtWidgets import QPlainTextEdit as _PTE
    longnpc = {"name": "Vivi", "dialogue": "this is a fairly long dialogue line that must wrap"}
    pw, _pg = build_form(forms.NPC_SPEC, forms.entity_to_values(forms.NPC_SPEC, longnpc), win.pal, wrap_width=12)
    prev_box = [pte for pte in pw.findChildren(_PTE) if pte.isReadOnly()]    # the PREVIEW (read-only) box
    assert prev_box and prev_box[0].toPlainText() == _dlg.wrap_preview(longnpc["dialogue"], 12), \
        (prev_box and prev_box[0].toPlainText())
    assert "\n" in prev_box[0].toPlainText(), "a long line pre-breaks in the preview"
    # the overflow note is FIXED-height (always in the layout, not visibility-toggled) so flipping
    # warn<->fits can't reflow/clip the preview box (the reported resize bug)
    note = [lb for lb in prev_box[0].parent().findChildren(QLabel) if lb.maximumHeight() == 16]
    assert note and note[0].minimumHeight() == 16, "the wrap-preview note is fixed-height (no reflow)"
    # MULTI-LINE dialogue: the EDITABLE dialogue widget is a QPlainTextEdit that holds real newlines, and
    # an interior \n survives build_entity (only edges are stripped) -> FF9's native in-window line break
    edit_box = [pte for pte in pw.findChildren(_PTE) if not pte.isReadOnly()]
    assert edit_box, "the dialogue field is a multi-line text box (not a single-line edit)"
    edit_box[0].setPlainText("Line one\nLine two")
    assert _pg["dialogue"]() == "Line one\nLine two"                         # getter returns the real newline
    assert forms.build_entity(forms.NPC_SPEC, read(_pg))["dialogue"] == "Line one\nLine two"  # \n kept by build
    assert prev_box[0].toPlainText() == _dlg.wrap_preview("Line one\nLine two", 12)  # preview honors the break

    # Phase 4b: the cutscene + choice sub-editors mount over a doc with steps/options
    edoc = win._doc("IC_ENT")
    edoc.data["cutscene"] = {"once": True, "steps": [{"say": "Hello"}, {"wait": 30}]}
    edoc.data["choice"] = [{"npc": "Guard", "prompt": "Well?", "options": [{"text": "Yes"}, {"text": "No"}]}]
    win._mount_cutscene("IC_ENT")
    step_lists = win.doc_host.findChildren(QListWidget)
    assert step_lists and step_lists[0].count() == 2, "cutscene steps list shows both steps"
    win._mount_choice("IC_ENT", 0)
    opt_lists = win.doc_host.findChildren(QListWidget)
    assert opt_lists and opt_lists[0].count() == 2, "choice options list shows both options"
    # the catalog picker reuses the infohub spine (archetype search finds 'vivi') -- no exec(), just _refresh
    from .forms_qt import CatalogPicker
    pk = CatalogPicker(win, ["archetype", "creature"], "vivi", win.plan, win.pal)
    assert "vivi" in [e.name for e in pk._entries], [e.name for e in pk._entries]
    # the Info Hub browser (folded in): browse=True, no cap -> the FULL catalog (>300, not the picker cap)
    brow = CatalogPicker(win, None, "", win.plan, win.pal, browse=True, limit=None)
    assert len(brow._entries) > 300, f"uncapped browse should exceed the 300 picker cap, got {len(brow._entries)}"
    brow.lst.setCurrentRow(0)
    brow._ok()                                          # browse mode: copies the name + stays open (no accept)
    assert brow.result is None and "Copied" in brow.info.text()
    assert "Browse catalog (Info Hub)" in [e[0] for e in win._command_index()]

    # Check surfaces the dangling GHOST edge as a problem
    win.on_check()
    assert win.problems.count() >= 1
    assert any("GHOST" in win.problems.item(i).text() for i in range(win.problems.count()))
    nprob = win.problems.count()

    # Open Field: a STANDALONE authored field (cutscene + choice) -- no campaign needed
    af = d / "AUTHORED.field.toml"
    af.write_text('[field]\nid = 4321\nname = "AUTHORED"\narea = 11\n\n'
                  '[cutscene]\nonce = true\n[[cutscene.steps]]\nsay = "Hi"\n\n'
                  '[[choice]]\nnpc = "Vivi"\nprompt = "Well?"\n'
                  '[[choice.options]]\ntext = "Yes"\n[[choice.options]]\ntext = "No"\n\n'
                  '[[npc]]\nname = "Vivi"\npreset = "vivi"\n', encoding="utf-8")
    assert win.open_field(af)
    assert win.plan is None and win._loose == "AUTHORED"
    assert win.map._layout is None                     # a loose field has no campaign map
    lf = win.tree.topLevelItem(0)
    assert win._payload(lf)[1] == "AUTHORED"
    win.tree.expandItem(lf)
    lgroups = [win._payload(lf.child(i))[1] for i in range(lf.childCount())]
    assert "Cutscene" in lgroups and any(g.startswith("Choices") for g in lgroups), lgroups
    # L1: dirty tracking -- a fresh open is clean; an in-memory edit is detected; baseline clears it
    assert win._dirty_members() == []
    win._doc("AUTHORED").data.setdefault("field", {})["title"] = "Dirty!"
    assert win._dirty_members() == ["AUTHORED"]
    win._mark_clean("AUTHORED")
    assert win._dirty_members() == []
    win._open_editor("AUTHORED", "object", "cutscene")     # cutscene sub-editor over a loose field
    win._open_editor("AUTHORED", "object", "choice:0")     # choice sub-editor over a loose field
    win.on_check()                                          # loose validate+lint runs (no campaign, no crash)

    # 5b-i: the Story State save document inspects a crypto-free JSON save (gEventGlobal)
    import base64 as _b64
    import json as _json
    g = bytearray(2048)
    g[0], g[1] = 2500 & 0xFF, 2500 >> 8
    g[8520 >> 3] |= 1 << (8520 & 7)
    sj = d / "save.json"
    sj.write_text(_json.dumps({"profile": {"gEventGlobal": _b64.b64encode(bytes(g)).decode()}}), encoding="utf-8")
    assert win.story_state.load(str(sj))
    assert win.story_state.reports and win.story_state.reports[0][1].scenario_counter == 2500
    win.story_state.slots.setCurrentRow(0)
    win.story_state._on_slot()
    assert "Ice Cavern" in win.story_state.inspect.toPlainText(), "Inspect renders the beat name"
    # 5b-ii: the Item & Equip save document inspects a Memoria extra-save (gil / items / equipment)
    from .. import sjbinary as _sj
    def _i(x):
        return _sj.SJData(_sj.INT, x)
    rootc = _sj.SJClass()
    rootc.add("95000_Setting", _sj.SJClass())
    common = _sj.SJClass()
    pc = _sj.SJClass()
    pc.add("name", _sj.SJData(_sj.VALUE, "Zidane"))
    pinfo = _sj.SJClass()
    pinfo.add("slot_no", _i(0))
    pinfo.add("menu_type", _i(0))
    pc.add("info", pinfo)
    pc.add("equip", _sj.SJArray([_i(x) for x in (1, 112, 88, 149, 255)]))
    common.add("players", _sj.SJArray([pc]))
    common.add("gil", _i(4321))
    item0 = _sj.SJClass()
    item0.add("id", _i(236))
    item0.add("count", _i(7))
    common.add("items", _sj.SJArray([item0]))
    rootc.add("40000_Common", common)
    esp = d / "x_Memoria_0_2.dat"
    esp.write_bytes(_sj.dumps(rootc))
    assert win.item_equip.load(str(esp))
    win.item_equip.slots.setCurrentRow(0)
    win.item_equip._on_slot()
    assert "4,321" in win.item_equip.inspect.toPlainText(), win.item_equip.inspect.toPlainText()[:120]
    assert win.item_equip.targets[0]["report"].gil == 4321
    # the write path: stub the confirm gate -> Yes, Apply a gil edit, verify it landed + the slot stays
    from .. import save_items as _si2
    win.item_equip._confirm = lambda _detail: True
    win.item_equip.gil_var.setText("99999")
    win.item_equip._edit("gil", True)
    assert _si2.inspect(str(esp))[0][1].gil == 99999, "gil Apply wrote the extra-save"
    assert win.item_equip.slots.currentRow() == 0, "the edited slot stays selected after Apply"
    win.item_equip._confirm = lambda _detail: False              # and a declined confirm does NOT write
    win.item_equip.gil_var.setText("1")
    win.item_equip._edit("gil", True)
    assert _si2.inspect(str(esp))[0][1].gil == 99999, "a declined Apply leaves the save untouched"

    # 6b: Build & Deploy + Import documents -- argv-building + in-process Check (no real subprocess launched)
    assert win.tabs.indexOf(win.build_deploy) >= 0 and win.tabs.indexOf(win.import_field) >= 0
    bd = win.build_deploy
    launched = []
    bd._run = lambda argv, **kw: (launched.append(list(map(str, argv))) or True)   # capture, don't launch
    bd._confirm = lambda *a: True
    bd.set_target(d / "campaign.toml")                           # auto-detect -> campaign kind
    assert bd.kind == "campaign" and bd.plan is not None
    bd._check_campaign(str(d / "campaign.toml"))                 # in-process Check -> Problems (dangling GHOST)
    assert any("GHOST" in win.problems.item(i).text() for i in range(win.problems.count()))
    bd.rb_camp_deploy.setChecked(True)
    bd.on_go()
    assert launched and any("deploy_campaign.py" in a for a in launched[-1]), launched[-1]
    bd.set_target(d / "IC_ENT" / "IC_ENT.field.toml")           # auto-detect -> field kind, id from [field]
    assert bd.kind == "field" and bd.field_id == 30100
    bd.rb_test.setChecked(True)
    bd.on_go()
    assert any("deploy_field.py" in a for a in launched[-1]), launched[-1]
    bd._check_field(str(d / "IC_ENT" / "IC_ENT.field.toml"))    # in-process field Check (no crash)

    imp = win.import_field
    icap = []
    imp._run = lambda argv, **kw: (icap.append(list(map(str, argv))) or True)
    imp.field.setText("100")
    imp.art_borrow.setChecked(True)
    imp.carry_npcs.setChecked(False)
    imp.carry_text.setChecked(False)
    imp.fid.setText("4003")
    imp.out.setText(str(d / "imp_out"))                          # a temp out folder (don't touch the repo)
    imp.on_import()
    assert icap[-1][:4] == [sys.executable, "-m", "ff9mapkit", "import"] and icap[-1][4] == "100", icap[-1]
    imp.on_find()
    assert "list-fields" in icap[-1], icap[-1]

    print(f"workspace shell smoke ok: campaign>field tree ({len(names)} members) + Map document, lazy "
          f"objects, breadcrumb, EDITOR forms (NPC+field round-trip) + cutscene/choice sub-editors + "
          f"catalog picker + Open Field (standalone authored) + Save docs (Story State SC "
          f"{win.story_state.reports[0][1].scenario_counter} + Item/Equip gil "
          f"{win.item_equip.targets[0]['report'].gil}) + ADD list items (NPC/gateway/choice) + Build/Deploy "
          f"+ Import docs (argv-built) + Ctrl-K palette, Problems dock ({nprob} rows); QProcess wired")


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
