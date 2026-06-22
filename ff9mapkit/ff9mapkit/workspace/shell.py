"""The PySide6 workspace shell (Qt UI) -- Phase 3 of the GUI makeover.

One dockable window: a left project tree (journey > campaign > field > object), a clickable breadcrumb,
a central document area, a right inspector, and a bottom Output/Problems dock. It reuses the kit's
tk-free backends verbatim -- :mod:`..editor.feedback` (Verdict/Problem), :mod:`..editor.breadcrumb`
(Crumb/trail), :mod:`..campaign` (CampaignPlan/graph), :mod:`..editor.model` (FieldDoc) -- so only this
view layer is Qt. Long jobs stream via ``QProcess`` (the Qt analogue of the tkinter apps' thread+queue).

Launch:  ``py apps/ff9_workspace.pyw``  (or ``py -m ff9mapkit.workspace.shell``).
"""

from __future__ import annotations

import collections
import copy
import html
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QProcess, QSize
from PySide6.QtGui import QAction, QBrush, QColor, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFileDialog, QFormLayout,
    QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QPlainTextEdit, QPushButton, QRadioButton, QScrollArea, QSplitter, QStackedWidget, QTabWidget, QTextEdit,
    QToolBar, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .. import campaign as C
from .. import save as _save
from ..editor import breadcrumb as bc
from ..editor import feedback as fb
from ..editor import forms
from ..editor import jobs
from ..editor.model import FieldDoc, protected_reason
from ..editor.theme import pick_palette
from .battledoc import BattleDoc
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
                 "event": forms.EVENT_SPEC, "flag": forms.FLAG_SPEC, "marker": forms.MARKER_SPEC,
                 "party": forms.PARTY_SPEC, "startup": forms.STARTUP_SPEC}
_SINGLES = ("field", "encounter", "music", "dialogue", "party", "startup")

# object groups inside a field.toml, mirroring the tkinter editor's tree (editor/app.py).
_SINGLE = [("dialogue", "Dialogue"), ("encounter", "Encounter"), ("music", "Music"), ("cutscene", "Cutscene"),
           ("party", "Party"), ("startup", "Startup beat")]
_LISTS = [("npc", "NPCs"), ("gateway", "Gateways"), ("event", "Events"), ("flag", "Flags"),
          ("marker", "Markers"), ("choice", "Choices")]
_LIST_SINGULAR = {"npc": "NPC", "gateway": "Gateway", "event": "Event", "flag": "Flag",
                  "marker": "Marker", "choice": "Choice"}
# the default new entity per list kind -- mirrors the tkinter editor's _add_entity (editor/app.py).
_LIST_DEFAULTS = {
    "npc": {"name": "NPC", "preset": "vivi", "dialogue": "..."},
    "gateway": {"name": "door", "to": 100, "entrance": 0},
    "event": {"name": "event", "message": "..."},
    "flag": {"name": "flag", "index": 8512},          # a save-persistent story flag (name -> gEventGlobal bit)
    "marker": {"name": "spot", "pos": [0, 0]},
    "choice": {"npc": "", "prompt": "What'll it be?", "options": [{"text": "Yes"}, {"text": "No"}]},
}
_ROLE = Qt.UserRole                                # per-item payload: (kind, label, key)
_DETAIL = Qt.UserRole + 1                           # read-only decoded detail (logic-map nodes): list[str]
_LOGIC_KINDS = ("logic_root", "logic_entry", "logic_node")   # read-only logic-map nodes (not editable)

# Hover help per tree-node KIND -- so a glyph is never the ONLY cue to what a row is (the icons read alike).
_KIND_HELP = {
    "jset": "Hub — the journeys.toml front door (the menu of playable journeys)",
    "journey": "Journey — one playable arc (a hub menu row)",
    "jcampaign": "Campaign — a member arc of this journey (double-click to open it)",
    "jbare": "Field — a bare single-field journey (warps straight to this field)",
    "campaign": "Campaign — a chain of fields",
    "field": "Field — one explorable screen",
    "group": "A list of objects in this field",
    "object": "An object in this field (NPC / gateway / event / …)",
}


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


def _field_token(name) -> str:
    """A field/member NAME -> a clean on-disk token (it becomes a subdir + ``EVT_<name>``/``FBG`` ids), or
    raise ValueError. Mirrors :func:`..campaign._validate_member_name` but raises the GUI's ValueError."""
    name = str(name).strip()
    if not name or name in (".", "..") or any(c in name for c in "/\\"):
        raise ValueError(f"invalid name {name!r} — use letters/digits/underscores, no path separators")
    return name


# One undo step = a member's whole doc.data BEFORE and AFTER an edit, plus the tree node to re-show.
# (Snapshot-of-the-document, not a per-op delta -- simple + always-correct for a small TOML tree.)
_UndoRec = collections.namedtuple("_UndoRec", "member before after label focus")
UNDO_LIMIT = 100                                   # cap the history so a long session can't grow unbounded


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _snip(s, n=44) -> str:
    """A one-line, length-capped preview of a value (Inspector dialogue/message snippets)."""
    s = str(s).replace("\n", " ").strip()
    return s if len(s) <= n else s[:n - 1] + "…"


def _toml_str(s) -> str:
    """Escape a value for a double-quoted TOML string (the New-Journey template's hub name)."""
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def _render_journey_toml(*, hub_name, hub_id, borrow_bg, jid, jname, kind="bare", entry=4100,
                         scenario=None, campaigns=None) -> str:
    """Render a New-Journey journeys.toml from the dialog's choices. ``kind='bare'`` -> a COMPLETE,
    ready-to-build file (the hub warps to one field). ``kind='multi'`` -> the hub + first journey filled in,
    with a placeholder entry + a commented links/seed block (those need member names from forked campaigns).
    Always loads (the schema is valid); a multi template's missing campaign folders surface as a helpful
    'fork the campaigns first' note in the overview/lint -- onboarding, not a crash."""
    from .. import hub as _hub
    L = ["# A JOURNEY = one playable arc the World Hub selects + warps into. The hub is a small BG-borrow",
         "# field that shows a menu; each journey seeds its story state and warps in. docs/JOURNEYS.md.",
         "",
         "[hub]",
         f'name = "{_hub.name_token(hub_name)}"      # an EVT_/FBG_ token (no spaces -- becomes the field name)',
         f"id = {int(hub_id)}                  # the hub field id (custom band, >= 4000)",
         f'borrow_bg = "{_toml_str(borrow_bg)}"   # a real field whose art the hub reuses (`ff9mapkit list-fields`)',
         "",
         "[[journey]]",
         f'id = "{_toml_str(jid)}"           # a stable slug -- the hub-choice key (A-Z, 0-9, _)',
         f'name = "{_toml_str(jname)}"       # the label shown on the hub menu']
    if kind == "bare":
        L.append(f"entry = {int(entry)}              # the field id the hub warps straight into")
        if scenario is not None:
            L.append(f"set_scenario = {int(scenario)}        # seed this story beat before warping in")
    else:
        folders = [f for f in (campaigns or []) if f] or ["campaign_folder"]
        clist = ", ".join(f'"{_toml_str(f)}"' for f in folders)
        L += [f"campaigns = [{clist}]   # campaign FOLDERS beside this file (fork them first: import-chain)",
              f'entry = {{ campaign = "{_toml_str(folders[0])}", field = "ENTRY_MEMBER" }}   '
              "# CHANGE: the member you start in",
              "",
              "# Cross-campaign warps AUTO-WIRE at deploy from the real .eb seams -- no [[journey.link]] needed.",
              "# Add a row ONLY to OVERRIDE one (a custom connection the game lacks); else leave this out:",
              "# [[journey.link]]",
              f'# from = {{ campaign = "{_toml_str(folders[0])}", field = "BOUNDARY_MEMBER" }}',
              '# to = { campaign = "NEXT_FOLDER", field = "ARRIVAL_MEMBER", entrance = 0 }',
              "",
              "# The New-Game starting state (the story_flags capstone). Uncomment + edit:",
              "# [journey.seed]",
              "# scenario = 2600",
              '# party = ["Zidane", "Vivi"]']
    return "\n".join(L) + "\n"


def _coord_like(s) -> bool:
    """True if a string looks like ``"x, z"`` coordinates rather than an entity NAME -- so a cutscene
    ``walk = "100, -800"`` isn't mistaken for a (missing) marker reference."""
    parts = [p.strip() for p in str(s).split(",")]
    if len(parts) != 2:
        return False
    try:
        float(parts[0]); float(parts[1])
        return True
    except ValueError:
        return False


class BreadcrumbBar(QWidget):
    """A one-line clickable path built from :func:`..editor.breadcrumb.trail`. ``on_nav(crumb)`` fires
    when an ancestor segment is clicked (the leaf is inert)."""

    def __init__(self, pal):
        super().__init__()
        self.pal = pal
        self.on_nav = None
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(12, 6, 12, 6)
        self._lay.setSpacing(6)
        self.setStyleSheet(f"background:{pal['surface']};border-bottom:1px solid {pal['border']};")
        self._chip = QLabel("")                    # a PERSISTENT left-anchored doc-mode chip (never cleared by set)
        self._chip.setVisible(False)
        self._lay.addWidget(self._chip)
        self.set([])

    def set_chip(self, text, color=None):
        """The always-visible 'what am I editing' chip (JOURNEY / CAMPAIGN / FIELD / BATTLE / SAVE / BUILD).
        Empty text hides it. Persists across :meth:`set` so it stays truthful on every tab."""
        if not text:
            self._chip.setVisible(False)
            return
        col = color or self.pal["accent"]
        self._chip.setText(text)
        self._chip.setStyleSheet(
            f"background:{col};color:#ffffff;border-radius:3px;padding:1px 7px;font-weight:600;")
        self._chip.setVisible(True)

    def set(self, crumbs):
        while self._lay.count() > 1:               # keep index 0 (the persistent chip); clear the trail after it
            w = self._lay.takeAt(1).widget()
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
        self.manifest = None                       # the loaded JourneyManifest in JOURNEY mode (else None)
        self.journey_root = None                   # the open journeys.toml path (journey mode)
        self._journey_label_path = None            # a journeys.toml found NEAR an opened campaign (for "jump to journey")
        self._loose = None                         # the open standalone field's name (loose mode), else None
        self._docs = {}                            # member name -> loaded FieldDoc (cached, edited in place)
        self._clean = {}                           # member name -> deepcopy(doc.data) at load/last-save (dirty baseline)
        self._touched = set()                      # members with in-progress (typed-but-uncommitted) edits
        self._name_valid = {}                      # (catalog, value) -> bool, memoized (the catalogs are static)
        self._scene_names = {}                     # member -> (mtime, npc names, marker names) from the scene.toml
        self._active_save = None                   # the mounted form's Save handler (Ctrl-S target)
        self._save_btn = None                      # the mounted form's Save button (greys when clean)
        self._reset_btn = None                     # the mounted form's Reset button (revert to last save)
        self._save_ctx = None                      # {member, key, spec, getters, single|kind, idx} for Save
        self._undo_stack = []                      # [_UndoRec] -- applied edits (Ctrl-Z pops the last)
        self._redo_stack = []                      # [_UndoRec] -- undone edits (Ctrl-Shift-Z re-applies)
        self._undo_base = {}                       # member -> deepcopy(doc.data) at the last checkpoint
        self._last_new_dir = str(REPO)             # remembered folder for the New Field / New Campaign pickers
        self._content_crumbs = []                  # cached tree-driven trail -> restored when returning to a content tab
        self._content_chip = None                  # cached chip mode for the SELECTED node (hub/journey/campaign/field)
        self._loose_parent = (None, None, None)    # (campaign.toml, member, name) when a loose field is a campaign member
        self.setWindowTitle("Dream World IX — Workspace")
        self.resize(1280, 820)
        self.setStyleSheet(qss(pal))
        self._dot_icon = self._make_dot_icon(pal["warn"])     # the unsaved-changes dot (amber, not text)
        self._blank_icon = self._make_dot_icon(None)          # a transparent same-size icon for clean rows,
        self._root_items = []                                 # so toggling the dot never resizes/shifts a row
        self._build_toolbar()
        self._build_central()
        self._build_dock()
        self.statusBar().showMessage("Open a campaign.toml to begin.")

    # ---- chrome ----
    def _build_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)
        # Project-file ops consolidated into 3 hierarchy dropdowns (Field / Campaign / Journey), each New +
        # Open. The keyboard shortcuts (below) are independent of the menus, so the keys still work directly.
        self._field_btn = self._menu_button(tb, "Field", "Create or open a standalone field", [
            ("New Field…   (Ctrl-N)", self.on_new_field),
            ("Open Field…", self.on_open_field)])
        self._campaign_btn = self._menu_button(tb, "Campaign", "Create or open a campaign (a chain of fields)", [
            ("New Campaign…   (Ctrl-Shift-N)", self.on_new_campaign),
            ("Open Campaign…", self.on_open_campaign)])
        self._journey_btn = self._menu_button(tb, "Journey", "Create or open a journey (the whole arc — the "
                                              "project front door)", [
            ("New Journey…   (commented template)", self.on_new_journey),
            ("Open Journey…", self.on_open_journey)])
        tb.addSeparator()
        act_open_save = QAction("Open Save…", self)
        act_open_save.setToolTip("Open a game save to edit story state / items / equipment")
        act_open_save.triggered.connect(self._open_save)
        tb.addAction(act_open_save)
        self.act_close = QAction("Close", self)
        self.act_close.setToolTip("Close the open project and return to the empty Workspace — the way OUT of any "
                                  "journey / campaign / field, from any tab")
        self.act_close.triggered.connect(self._close_project)
        tb.addAction(self.act_close)
        tb.addSeparator()
        self.act_undo = QAction("Undo", self)
        self.act_undo.setToolTip("Undo (Ctrl+Z)")
        self.act_undo.setEnabled(False)
        self.act_undo.triggered.connect(self._undo)             # the toolbar button is always app-level undo
        tb.addAction(self.act_undo)
        self.act_redo = QAction("Redo", self)
        self.act_redo.setToolTip("Redo (Ctrl+Shift+Z)")
        self.act_redo.setEnabled(False)
        self.act_redo.triggered.connect(self._redo)
        tb.addAction(self.act_redo)
        self.act_save_all = QAction("Save All", self)
        self.act_save_all.setToolTip("Save every field with unsaved changes (Ctrl-Shift-S)")
        self.act_save_all.triggered.connect(self._save_all)
        tb.addAction(self.act_save_all)
        self.act_check = QAction("Check", self)
        self.act_check.triggered.connect(self.on_check)
        self.act_check.setEnabled(False)
        tb.addAction(self.act_check)
        self.act_lint_cli = QAction("Lint (CLI)", self)
        self.act_lint_cli.triggered.connect(self.run_cli_lint)
        self.act_lint_cli.setEnabled(False)
        tb.addAction(self.act_lint_cli)
        self.act_hub = QAction("Info Hub", self)
        self.act_hub.setToolTip("Open the Info Hub catalog library (browse models / NPCs / props / items / "
                                "flags by name)")
        self.act_hub.triggered.connect(self._open_catalog)
        tb.addAction(self.act_hub)
        self._hub_btn = tb.widgetForAction(self.act_hub)   # color it violet (= the 'info / reference' hue, like
        if self._hub_btn is not None:                       # the Info Hub's own ? badge) so the popup stands out
            self._hub_btn.setStyleSheet(
                f"QToolButton {{ background:{self.pal['help']}; color:{self.pal['accent_fg']}; "
                f"border:1px solid {self.pal['help']}; border-radius:6px; padding:6px 12px; font-weight:600; }}"
                f"QToolButton:hover {{ background:{self.pal['help_hover']}; border-color:{self.pal['help_hover']}; }}")
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred)
        tb.addWidget(spacer)
        search = QPushButton("⌕   Search content & commands   (Ctrl-K)")
        search.setObjectName("search")
        search.setFixedWidth(320)
        search.clicked.connect(self._open_palette)
        tb.addWidget(search)
        QShortcut(QKeySequence("Ctrl+K"), self, activated=self._open_palette)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._save_shortcut)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self._save_all)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.on_new_field)
        QShortcut(QKeySequence("Ctrl+Shift+N"), self, activated=self.on_new_campaign)
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self._undo_shortcut)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=self._redo_shortcut)

    def _menu_button(self, tb, text, tooltip, items):
        """A toolbar DROPDOWN button: ``text ▾`` opening a menu of (label, callback) items. Returns the
        QToolButton. Used to fold New/Open into one button per hierarchy level (Field/Campaign/Journey)."""
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(btn)
        for label, cb in items:
            menu.addAction(label, cb)
        btn.setMenu(menu)
        tb.addWidget(btn)
        return btn

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
        self.tree.setUniformRowHeights(True)        # the unsaved-dot icon must NOT change a row's height
        self.tree.setIconSize(QSize(12, 12))        # ...so the tree doesn't jump when a dot appears/clears
        self.tree.itemSelectionChanged.connect(self._on_select)
        self.tree.itemExpanded.connect(self._on_expand)
        self.tree.itemDoubleClicked.connect(self._on_tree_double)   # double-click = open (Editor / Map)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)        # right-click = Add / Delete / Remove
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        del_sc = QShortcut(QKeySequence(Qt.Key_Delete), self.tree, activated=self._delete_selected)
        del_sc.setContext(Qt.ShortcutContext.WidgetShortcut)        # Delete only when the tree has focus
        for _ekey in (Qt.Key_Return, Qt.Key_Enter):                 # Enter = open (parity with double-click)
            esc = QShortcut(QKeySequence(_ekey), self.tree, activated=self._open_current_tree_item)
            esc.setContext(Qt.ShortcutContext.WidgetShortcut)
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
        self.battle = BattleDoc(self.pal, output=self._save_output, problems=self._show_problems,
                                run=self.run_job, kit_root=KIT,            # encounter editor + Fork battle…
                                on_open=self._on_battle_open)              # opening/forking a battle.toml pre-aims Build & Deploy
        self.tabs.addTab(self.battle, "Battle")
        # Phase 6b: Build & Deploy + Import folded in as documents (retiring the standalone tkinter apps).
        # They build argv via editor.jobs and stream through run_job -> the bottom Output panel.
        self.build_deploy = BuildDoc(self.pal, REPO, run=self.run_job, problems=self._show_problems)
        self.tabs.addTab(self.build_deploy, "Build & Deploy")
        self.import_field = ImportDoc(self.pal, KIT, run=self.run_job, problems=self._show_problems,
                                      on_forked=self._import_forked)       # a clean fork auto-opens its project
        self.tabs.addTab(self.import_field, "Import")
        # do-now #1: keep the breadcrumb + doc-mode chip truthful on EVERY tab (the indicator used to update
        # ONLY on tree selection, so it lied on the 5 self-contained doc tabs). Wired AFTER all addTab calls
        # so it doesn't fire mid-construction (current index is the Home tab, which _on_tab_changed no-ops).
        self.tabs.currentChanged.connect(self._on_tab_changed)
        split.addWidget(self.tabs)

        insp = QWidget()
        insp.setMaximumWidth(420)                   # an info panel -- cap it so long content can't balloon it
        iv = QVBoxLayout(insp)
        iv.setContentsMargins(10, 10, 10, 10)
        self.insp_title = QLabel("Inspector")
        self.insp_title.setTextFormat(Qt.TextFormat.PlainText)   # a user-typed entity name is never markup
        self.insp_title.setStyleSheet("font-weight:600;")
        self.insp_body = QLabel("Select something on the left.")
        self.insp_body.setMinimumWidth(0)          # don't let a long line dictate the panel/splitter width
        self.insp_body.setWordWrap(True)
        self.insp_body.setTextFormat(Qt.TextFormat.RichText)        # the file line is a copy-to-clipboard link
        self.insp_body.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse
                                               | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.insp_body.linkActivated.connect(self._inspect_link)
        self._inspect_path = None
        self.insp_body.setStyleSheet(f"color:{self.pal['muted']};")
        self.insp_body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        iv.addWidget(self.insp_title)
        iv.addWidget(self.insp_body, 1)
        split.addWidget(insp)

        split.setSizes([300, 640, 240])
        split.setStretchFactor(1, 1)
        self.setCentralWidget(central)

    def _dock_header(self, text):
        """A small bold caption for a dock panel (replaces the old tab labels, since both panels now show
        at once)."""
        lab = QLabel(text)
        lab.setStyleSheet(f"color:{self.pal['text']};font-weight:600;")
        return lab

    def _build_dock(self):
        # Problems + Output were tabs (one visible at a time), but they're almost always wanted TOGETHER (a
        # job streams to Output while its verdict lands in Problems). So show both side-by-side in one dock,
        # split by a draggable divider.
        dock = QDockWidget("Problems  ·  Output")
        dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.dock = dock
        split = QSplitter(Qt.Horizontal)

        prob_page = QWidget()                       # left: the lint verdict banner + the Problems rows
        pv = QVBoxLayout(prob_page)
        pv.setContentsMargins(8, 8, 8, 8)
        pv.setSpacing(6)
        pv.addWidget(self._dock_header("Problems"))
        self.banner = QLabel("")
        self.banner.setVisible(False)
        self.banner.setWordWrap(True)
        self.problems = QListWidget()
        pv.addWidget(self.banner)
        pv.addWidget(self.problems, 1)
        self.problems_page = prob_page

        out_page = QWidget()                        # right: the streamed process/console output
        ov = QVBoxLayout(out_page)
        ov.setContentsMargins(8, 8, 8, 8)
        ov.setSpacing(6)
        ov.addWidget(self._dock_header("Output"))
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        ov.addWidget(self.output, 1)

        split.addWidget(prob_page)
        split.addWidget(out_page)
        split.setSizes([360, 720])                  # Output starts wider (build/deploy logs run long); draggable
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        self.dock_split = split

        dock.setWidget(split)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        dock.setMinimumHeight(150)

    def _raise_dock(self):
        """Both panels are always visible now (side-by-side splitter), so 'focus Problems/Output' just means
        make sure the dock itself is shown -- e.g. if the user floated or closed it."""
        if getattr(self, "dock", None) is not None:
            self.dock.setVisible(True)
            self.dock.raise_()

    def _welcome(self):
        """The 'Start here' HOME (do-now #4): a live front door that names every entry point in hierarchy
        order — the .toml spine top-down (journey ▸ campaign ▸ field) + the off-spine starts (battle / import /
        save) — each a real button on the existing open/new handlers, plus a 'Currently editing …' line. Answers
        'where do I start / do I need a journey?' at the moment of entry. Tab index 0, shown on cold start."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(30, 26, 30, 26)
        v.setSpacing(10)
        title = QLabel("Dream World IX — Workspace")
        title.setStyleSheet("font-size:18px;font-weight:700;")
        v.addWidget(title)
        self._home_status = QLabel("")
        self._home_status.setWordWrap(True)
        self._home_status.setTextFormat(Qt.TextFormat.RichText)
        v.addWidget(self._home_status)
        intro = QLabel("Start at <b>any</b> level — they nest (journey ▸ campaign ▸ field ▸ object), but none "
                       "<i>requires</i> the one above. A <b>journey</b> is the front door (the whole arc); you "
                       "can also open a single campaign or field directly.")
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.TextFormat.RichText)
        intro.setStyleSheet(f"color:{self.pal['muted']};")
        v.addWidget(intro)
        v.addWidget(self._home_section("The project spine — top-down"))
        v.addWidget(self._home_row("◆ Journey", "the whole arc: a hub + member campaigns + links (the front door)",
                                   [("Open…", self.on_open_journey), ("New…", self.on_new_journey)]))
        v.addWidget(self._home_row("▣ Campaign", "a connected chain of fields",
                                   [("Open…", self.on_open_campaign), ("New…", self.on_new_campaign)]))
        v.addWidget(self._home_row("● Field", "one explorable screen (edit it standalone)",
                                   [("Open…", self.on_open_field), ("New…", self.on_new_field)]))
        v.addWidget(self._home_section("Off to the side"))
        v.addWidget(self._home_row("⚔ Battle", "a battle background / encounter — a referenced sibling of a field",
                                   [("Go to Battle", lambda: self.tabs.setCurrentWidget(self.battle))]))
        v.addWidget(self._home_row("⤵ Import", "fork a real FF9 field into a new project",
                                   [("Go to Import", lambda: self.tabs.setCurrentWidget(self.import_field))]))
        v.addWidget(self._home_row("◈ Save", "edit a real save's story flags / items / equipment (orthogonal state)",
                                   [("Open Save…", self._open_save)]))
        v.addStretch(1)
        hint = QLabel("Press <b>Ctrl-K</b> to jump anywhere · <b>Close</b> (toolbar) returns here.")
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setStyleSheet(f"color:{self.pal['muted']};")
        v.addWidget(hint)
        scroll.setWidget(body)
        self._welcome_tab = scroll                 # kept so Close can return here
        self.tabs.addTab(scroll, "Home")
        self._refresh_home_status()

    def _home_section(self, text):
        lab = QLabel(text)
        lab.setStyleSheet(f"color:{self.pal['muted']};font-weight:600;margin-top:8px;")
        return lab

    def _home_row(self, title, desc, buttons):
        """One entry-point row: a glyph+name + one-line description on the left, its action button(s) on the
        right (the same glyphs as the tree/breadcrumb, so the visual language is consistent)."""
        box = QWidget()
        h = QHBoxLayout(box)
        h.setContentsMargins(0, 0, 0, 0)
        col = QWidget()
        cv = QVBoxLayout(col)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(1)
        t = QLabel(title)
        t.setStyleSheet("font-weight:600;")
        d = QLabel(desc)
        d.setWordWrap(True)
        d.setStyleSheet(f"color:{self.pal['muted']};")
        cv.addWidget(t)
        cv.addWidget(d)
        h.addWidget(col, 1)
        for label, cb in buttons:
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, c=cb: c())
            h.addWidget(b)
        return box

    def _current_target(self):
        """(name, level-label) of what's currently open — for the Home 'Currently editing' line. (None, None)
        when the Workspace is empty."""
        if self.manifest is not None and self.plan is None:
            return (self.journey_name, "Journey")
        if self.plan is not None:
            return (self.plan.name, "Campaign")
        if self._loose is not None:
            return (self._loose, "Field")
        return (None, None)

    def _refresh_home_status(self):
        """Update the Home 'Currently editing …' line (called when Home is shown, so it's always fresh)."""
        if not hasattr(self, "_home_status"):
            return
        name, level = self._current_target()
        if name is None:
            self._home_status.setText(self._muted("Nothing open yet — pick a starting point below."))
        else:
            self._home_status.setText(f"Currently editing a <b>{level}</b>: {_esc(str(name))}.")

    # ---- item helpers ----
    @staticmethod
    def _mk(kind, label, key="", glyph=""):
        it = QTreeWidgetItem([f"{glyph} {label}".strip()])
        it.setData(0, _ROLE, (kind, label, key))
        help_ = _KIND_HELP.get(kind)
        if help_:
            it.setToolTip(0, help_)                # hover names the TYPE -- the glyph isn't the only cue
        return it

    @staticmethod
    def _payload(item):
        return item.data(0, _ROLE) if item is not None else None

    # ---- campaign io ----
    def on_open_journey(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open a journeys.toml", "",
                                           "Journeys (journeys.toml);;TOML (*.toml);;All files (*)")
        if f:
            self.open_journey(Path(f))

    def open_journey(self, path) -> bool:
        """Open a journeys.toml as the project FRONT DOOR: the whole arc (hub + member campaigns + links) is
        the index -- no directory searching. Loads + lints the manifest, shows the resolved plan, and lets
        you drill into any campaign to edit it (the journey stays remembered)."""
        if not self._maybe_prompt_unsaved():
            return False
        self._clear_doc()
        path = Path(path)
        try:
            from .. import journey as J
            manifest = J.load_journeys(path)
        except Exception as e:                     # noqa: BLE001
            self.statusBar().showMessage(f"Open failed: {e}")
            return False
        self.manifest = manifest
        self.journey_root = path
        self.plan = None
        self.campaign_path = None
        self._loose = None
        self._journey_label_path = None            # journey mode uses self.manifest, not the reverse-search path
        self.journey_name = (manifest.hub.get("name") if manifest.hub else None) or path.parent.name
        self.member_paths = {}
        self._docs = {}
        self._clean = {}
        self._touched = set()
        self._fork_queue = []                      # a fresh journey -> no stale fork chain can re-drain
        self._reset_history()
        self.map.clear()                           # the journey overview lives in the doc area, not the Map
        self.build_deploy.set_target(self.journey_root)   # pre-aim Build & Deploy at the journey (deploy_journey)
        self.act_check.setEnabled(True)            # Check = lint the journey manifest
        self.act_lint_cli.setEnabled(False)
        self._populate_journey()
        self._lint_journey()                       # the namespace guarantee -> Problems dock, on open
        self._mount_journey_overview()
        self.tabs.setCurrentWidget(self.doc_scroll)
        self.statusBar().showMessage(f"Journey {self.journey_name} — {len(manifest.journeys)} journey(s) — {path}")
        self._refresh_flag_names()                 # re-annotate an already-open Story State save with this journey
        return True

    def _populate_journey(self):
        """The journey tree: the manifest -> each [[journey]] -> its member campaigns (open one to edit it).
        Journey mode = self.manifest set, self.plan None."""
        self.tree.clear()
        self._root_items = []
        self._member_items = {}
        jset = self._mk("jset", self.journey_name, "@journeys", "⌂")   # the HUB glyph -- distinct from a journey's ◆
        jset.setForeground(0, QBrush(QColor(self.pal["accent"])))
        jset.setIcon(0, self._blank_icon)
        self.tree.addTopLevelItem(jset)
        jset.setExpanded(True)
        self._root_items.append(jset)
        for j in self.manifest.journeys:
            jn = self._mk("journey", j.name or j.id, f"@journey:{j.id}", "◆")
            jn.setIcon(0, self._blank_icon)
            jset.addChild(jn)
            jn.setExpanded(True)
            if j.is_bare:                          # a single-field journey -> the hub warps straight to a field
                leaf = self._mk("jbare", f"→ field {j.entry.field}", f"@bare:{j.id}", "•")
                leaf.setIcon(0, self._blank_icon)
                jn.addChild(leaf)
            else:
                for folder in j.campaigns:
                    cn = self._mk("jcampaign", folder, folder, "▣")
                    cn.setIcon(0, self._blank_icon)
                    jn.addChild(cn)

    def _mount_journey_overview(self, selected_jid=None):
        """Show the resolved journey plan (campaigns, entry ids, flag windows, cross-campaign links) in the
        doc area -- read-only; render_journey_plan is the same view as `lint-journey --graph`. Below it, a
        'Fork the arcs' panel surfaces the Step-1 fork playbook (per-arc status + a Fork button) so a fresh
        reference-arc scaffold reads as 'next steps', not just a red lint error. When ``selected_jid`` names a
        specific [[journey]] row, a per-journey action row (seed / tuning / remove) is mounted -- the same
        authoring that used to live ONLY in the tree right-click menu, now a visible compartment."""
        self._clear_doc()
        self._set_editor_tab("Journey")
        self._header(self.journey_name, "The assembled journey plan. Open a campaign in the tree to edit it; "
                     "Check (or open) lints the global id/flag namespace into Problems.")
        addrow = QHBoxLayout()
        add_journey = QPushButton("Add journey…")
        add_journey.setToolTip("Add a menu row that warps New Game into an installed slice (the World-Hub selector)")
        add_journey.clicked.connect(self.on_add_journey_row)
        addrow.addWidget(add_journey)
        if any(j.campaigns for j in self.manifest.journeys):       # a multi-campaign journey -> grow it + STEP-2 fill
            addregion = QPushButton("Add region to arc…")
            addregion.setToolTip("Append an FF9 region (its own forked campaign) to this chain — the bottom-up "
                                 "fork-a-region-at-a-time loop. Allocates a disjoint id band; links auto-wire at deploy.")
            addregion.clicked.connect(self.on_add_region_to_arc)
            addrow.addWidget(addregion)
            fillb = QPushButton("Fill entry from forks")
            fillb.setToolTip("STEP 2: fill the ENTRY member from the forked entry campaign + clear the obsolete "
                             "link templates. Cross-campaign warps AUTO-WIRE at deploy from the real .eb seams -- "
                             "no link rows to fill. Run after Fork all. Idempotent.")
            if self._needs_reconcile():
                fillb.setObjectName("accent")          # highlight while the ENTRY_MEMBER placeholder remains
            fillb.clicked.connect(self.on_reconcile_journey)
            addrow.addWidget(fillb)
        addrow.addStretch(1)
        self.doc_host_lay.addLayout(addrow)
        if selected_jid is not None:
            self._mount_journey_row_actions(selected_jid)
        self._mount_fork_panel()                   # Step-1 fork helper (only if the manifest has campaigns)
        box = QPlainTextEdit()
        box.setReadOnly(True)
        try:
            from .. import journey as J
            box.setPlainText(J.render_journey_plan(self.manifest))
        except Exception as e:                     # noqa: BLE001
            box.setPlainText(f"Could not resolve the journey plan:\n{e}")
        self.doc_host_lay.addWidget(box, 1)

    def _mount_journey_row_actions(self, jid):
        """A visible per-journey action row (mounted when a specific [[journey]] row is selected): Set base
        party / seed, Set tuning, Remove -- the journey-tier authoring that was previously reachable ONLY
        from the tree right-click menu. Wired to the same callbacks the context menu binds."""
        j = next((x for x in self.manifest.journeys if x.id == jid), None)
        if j is None:
            return
        row = QHBoxLayout()
        lbl = QLabel(f"Journey ‘{j.name or j.id}’:")
        lbl.setStyleSheet(f"color:{self.pal['muted']};")
        row.addWidget(lbl)
        seed_b = QPushButton("Set base party / seed…")
        seed_b.setToolTip("Edit [journey.seed] — the base party + start beat seeded into the entry member at "
                          "deploy (the story-flags capstone)")
        seed_b.clicked.connect(lambda _=False, j=jid: self.on_set_journey_seed(j))
        row.addWidget(seed_b)
        tune_b = QPushButton("Set tuning…")
        tune_b.setToolTip("Edit [journey.tuning] — the mod-global player / ability CSV deltas (BaseStats / "
                          "abilities / leveling)")
        tune_b.clicked.connect(lambda _=False, j=jid: self.on_set_journey_tuning(j))
        row.addWidget(tune_b)
        rm_b = QPushButton("Remove journey")
        rm_b.setToolTip("Remove this [[journey]] menu row from the hub (the installed slice it points to is "
                        "NOT deleted)")
        rm_b.clicked.connect(lambda _=False, j=jid: self.on_remove_journey_row(j))
        row.addWidget(rm_b)
        row.addStretch(1)
        self.doc_host_lay.addLayout(row)

    # ---- Step-1 fork helper (run import-chain per arc, from the journey overview) ----
    def _campaign_forked(self, folder) -> bool:
        """True if a member campaign has actually been forked (its campaign.toml exists beside the manifest)."""
        try:
            return (self.manifest.root / folder / "campaign.toml").is_file()
        except Exception:                          # noqa: BLE001
            return False

    def _mount_fork_panel(self):
        """The 'Fork the arcs' card: every member campaign with its status (forked / not) + a Fork button that
        runs its `import-chain` command (parsed from the journeys.toml header playbook) right in the GUI. Shown
        only when the manifest has campaigns; Fork buttons appear only for arcs whose command is in the header
        (a reference-arc scaffold, or any journey whose comments carry the playbook)."""
        folders = []
        for j in self.manifest.journeys:
            for f in j.campaigns:
                if f not in folders:
                    folders.append(f)
        if not folders:
            return
        self._fork_cmds = {}
        try:
            from .. import refarc as RA
            text = Path(self.journey_root).read_text(encoding="utf-8")
            self._fork_cmds = {pf.key: pf for pf in RA.parse_fork_commands(text)}
        except Exception:                          # noqa: BLE001
            self._fork_cmds = {}
        self._fork_order = folders
        done = [f for f in folders if self._campaign_forked(f)]
        missing_cmds = [f for f in folders if f not in done and f in self._fork_cmds]

        box = QGroupBox(f"Fork the arcs   ({len(done)}/{len(folders)} forked)")
        gv = QVBoxLayout(box)
        if len(done) < len(folders):
            hint = QLabel("These campaigns don't exist yet — <b>Step 1</b> is to fork them from their real FF9 "
                          "fields. Click <b>Fork</b> (runs <code>import-chain</code> into a folder beside this "
                          "file; needs UnityPy + your install), or run the commands in a terminal. The lint "
                          "clears each one as it's forked.")
            hint.setTextFormat(Qt.TextFormat.RichText)
            hint.setWordWrap(True)
            hint.setStyleSheet(f"color:{self.pal['muted']};")
            gv.addWidget(hint)
        self._fork_buttons = {}
        self._fork_rows = {}                        # key -> the status QLabel (restyled while a fork runs)
        for f in folders:
            row = QHBoxLayout()
            forked = self._campaign_forked(f)
            pf = self._fork_cmds.get(f)
            tag = QLabel(("✓ " if forked else "○ ") + f + (f"  (real field {pf.seed})" if pf else ""))
            tag.setStyleSheet(f"color:{self.pal['accent'] if forked else self.pal['text']};")
            self._fork_rows[f] = tag
            row.addWidget(tag)
            row.addStretch(1)
            if forked:
                lbl = QLabel("forked")
                lbl.setStyleSheet(f"color:{self.pal['muted']};")
                row.addWidget(lbl)
            elif pf:
                b = QPushButton("Fork")
                b.clicked.connect(lambda _=False, key=f: self._fork_campaign(key))
                self._fork_buttons[f] = b
                row.addWidget(b)
            else:
                lbl = QLabel("fork manually")
                lbl.setStyleSheet(f"color:{self.pal['muted']};")
                row.addWidget(lbl)
            gv.addLayout(row)
        if missing_cmds:
            allb = QPushButton(f"Fork all missing ({len(missing_cmds)})")
            allb.setObjectName("accent")
            allb.clicked.connect(self._fork_all_missing)
            self._fork_all_btn = allb
            gv.addWidget(allb)
        self.doc_host_lay.addWidget(box)

    def _mark_fork_running(self, key):
        """Reflect an in-progress fork in the panel so it's obvious something's happening: the active arc's row
        flips to '⟳ … forking…' and its button to 'Forking…', and EVERY fork control disables (you can't
        double-launch). The panel re-mounts on completion (showing the arc's ✓ + re-enabling the rest)."""
        for f, b in getattr(self, "_fork_buttons", {}).items():
            b.setEnabled(False)
            b.setText("Forking…" if f == key else "Fork")
        tag = getattr(self, "_fork_rows", {}).get(key)
        if tag is not None:
            tag.setText(f"⟳ {key}  (forking…)")
            tag.setStyleSheet(f"color:{self.pal['accent']};")
        allb = getattr(self, "_fork_all_btn", None)
        if allb is not None:
            allb.setEnabled(False)
            allb.setText("Forking…")

    def _fork_argv(self, key):
        """The runnable import-chain argv for arc ``key`` (its --out rewritten to an absolute path beside the
        manifest, so the fork runs from the kit root yet lands the folder next to the journeys.toml)."""
        pf = self._fork_cmds[key]
        return jobs.fork_command_argv(pf.command, out_abs=self.manifest.root / key)

    def _fork_campaign(self, key):
        """Fork ONE arc via import-chain (streamed to Output); on success, refresh the overview + re-lint."""
        if key not in self._fork_cmds:
            return
        pf = self._fork_cmds[key]
        if self.run_job(self._fork_argv(key), cwd=KIT, subject=f"Fork {key} (import-chain {pf.seed})",
                        ok_headline=f"Forked {key} → {self.manifest.root / key}",
                        ok_next="The arc folder exists now; the journey lint clears it. Fill the entry (links auto-wire).",
                        fail_hint="import-chain needs UnityPy + your FF9 install. See the Output panel.",
                        on_finished=lambda code: self._after_fork()):
            self._mark_fork_running(key)           # immediate 'Forking…' feedback (the job streams to Output)
        else:
            self.statusBar().showMessage("a job is already running — wait for it to finish")

    def _on_journey_overview(self) -> bool:
        """True iff the journey overview is the active context (manifest open, not drilled into a campaign).
        The fork chain + its refresh both gate on this so navigating away stops the background forks."""
        return self.manifest is not None and self.plan is None and bool(self.journey_root)

    def _fork_all_missing(self):
        """Fork every not-yet-forked arc that has a command, one after another (stop on the first failure)."""
        self._fork_queue = [f for f in getattr(self, "_fork_order", [])
                            if f in self._fork_cmds and not self._campaign_forked(f)]
        self._fork_next_in_queue()

    def _fork_next_in_queue(self):
        # bail (clearing the queue) if we've left the journey overview -- don't keep launching forks in the
        # background after the user drills into a campaign or closes the journey.
        if not self._on_journey_overview():
            self._fork_queue = []
            return
        while getattr(self, "_fork_queue", None):
            key = self._fork_queue[0]              # PEEK -- only consume on a successful launch (no lost arc)
            pf = self._fork_cmds.get(key)
            if pf is None or self._campaign_forked(key):   # vanished from the header / already forked -> drop
                self._fork_queue.pop(0)
                continue
            if self.run_job(self._fork_argv(key), cwd=KIT, subject=f"Fork {key} (import-chain {pf.seed})",
                            ok_headline=f"Forked {key}", on_finished=lambda code: self._after_queued_fork(code)):
                self._fork_queue.pop(0)            # launched -> consume it; the rest run from on_finished
                self._mark_fork_running(key)       # show THIS arc as forking (the rest disable)
            else:                                  # a job is already running -> keep the queue, let the user retry
                self.statusBar().showMessage("a job is already running — click ‘Fork all missing’ again when it finishes")
            return                                 # one fork at a time (launched OR deferred)
        self._after_fork()                         # queue drained -> refresh once

    def _after_queued_fork(self, code):
        if code != 0:
            self._fork_queue = []                  # stop the chain on a failure; let the user see the Output
        self._after_fork()                         # re-mount: the just-forked arc shows ✓ (and re-enables the rest)
        if code == 0 and getattr(self, "_fork_queue", None):
            self._fork_next_in_queue()             # ...then launch the next arc (marks it running on the fresh panel)

    def _after_fork(self):
        """Refresh the journey overview + re-lint after a fork (only if still on the journey overview)."""
        if self._on_journey_overview():
            self._mount_journey_overview()
            self._lint_journey()
            # all arcs forked but the entry is still a placeholder -> nudge STEP 2 (the lint shows the
            # ENTRY_MEMBER error; the 'Fill entry from forks' button resolves it; links auto-wire at deploy).
            folders = getattr(self, "_fork_order", [])
            if folders and all(self._campaign_forked(f) for f in folders) and self._needs_reconcile():
                self.statusBar().showMessage("All arcs forked — click ‘Fill entry from forks’ to "
                                             "set the entry (STEP 2; cross-campaign links auto-wire at deploy).")

    def _lint_journey(self):
        """Lint the open journeys.toml -> the Problems dock (the GLOBAL id/flag-disjointness guarantee)."""
        try:
            from .. import journey as J
            errs, warns = J.lint_manifest(self.manifest)
        except Exception as e:                     # noqa: BLE001
            errs, warns = [f"journey lint failed: {e}"], []
        v = fb.classify(errs, warns, subject=f"Journey lint ({self.journey_name})",
                        clean_headline=f"{self.journey_name} — no problems")
        self._show_problems(v, fb.problems(errs, warns))

    def _open_member_campaign(self, folder):
        """Drill from the journey into one member campaign (the existing single-campaign editor); the journey
        stays remembered so the journey root row returns to the overview."""
        cpath = self.manifest.root / folder / "campaign.toml"
        if not cpath.is_file():
            self.statusBar().showMessage(f"no campaign.toml in {folder}")
            return
        self.open_campaign(cpath, keep_journey=True)

    def _back_to_journey(self):
        if self.journey_root:                      # open_journey runs its own unsaved-prompt -- don't double it
            self.open_journey(self.journey_root)

    def on_add_journey_row(self):
        """Add a ``[[journey]]`` menu row to the open hub: a row that warps New Game into an ALREADY-INSTALLED
        field. The World-Hub selector builder -- validates (slug + entry id, no dup), appends to the
        journeys.toml, and re-opens so the row lints + lists. (Reach an installed slice via Build & Deploy.)"""
        if self.manifest is None or not self.journey_root:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Add journey to hub")
        form = QFormLayout(dlg)
        jid = QLineEdit()
        jid.setPlaceholderText("dali   (a slug: A-Z, 0-9, _)")
        jname = QLineEdit()
        jname.setPlaceholderText("Dali")
        entry = QLineEdit()
        entry.setPlaceholderText("4100   (the installed field this row warps into)")
        scenario = QLineEdit()
        scenario.setPlaceholderText("optional story beat (set_scenario)")
        form.addRow("Journey id", jid)
        form.addRow("Menu label", jname)
        form.addRow("Entry field id", entry)
        form.addRow("Scenario", scenario)
        note = QLabel("Each row is a menu choice on the hub. Install the slice first (fork + deploy); this row "
                      "just points New Game at its field id.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{self.pal['muted']};")
        form.addRow(note)
        form.addRow(self._ok_cancel(dlg))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._append_journey_row(jid.text().strip(), jname.text().strip(), entry.text().strip(),
                                 scenario.text().strip())

    def _append_journey_row(self, sid, name, entry_text, scenario_text) -> bool:
        """Validate + append a ``[[journey]]`` row to the open hub, then re-open (re-lint + re-list). Returns
        True on success. The dialog-free core of :meth:`on_add_journey_row` (so it's headlessly testable)."""
        import tomllib
        from .. import journey as J
        try:
            sid = str(sid).strip()                 # strip BEFORE the empty/dup checks (render_journey_row strips too)
            if not sid:
                raise ValueError("a journey id is required")
            if sid in {j.id for j in self.manifest.journeys}:
                raise ValueError(f"a journey id {sid!r} is already in this hub — pick another")
            ent = int(entry_text)
            row = J.render_journey_row(sid, name or sid, ent,
                                       scenario=int(scenario_text) if str(scenario_text).strip() else None)
            text = Path(self.journey_root).read_text(encoding="utf-8").rstrip("\n") + "\n\n" + row
            tomllib.loads(text)                    # belt-and-suspenders: the result must still parse
            Path(self.journey_root).write_text(text, encoding="utf-8", newline="\n")
            self.open_journey(self.journey_root)   # re-lint + re-list (the new row appears in the tree)
            self.statusBar().showMessage(f"Added journey '{sid}' → field {ent}")
            return True
        except (ValueError, J.JourneyError, tomllib.TOMLDecodeError, OSError) as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Couldn't add the journey"),
                                [fb.Problem(fb.ERROR, str(e))])
            return False

    def on_set_journey_seed(self, jid):
        """Edit a journey's ``[journey.seed]`` -- its BASE PARTY + start beat (the destination-side story_flags
        capstone). A dialog prefilled from the current seed. For a BARE single-field journey the party seed
        won't apply (warned -> set it on the entry field's [party]); the start beat still applies hub-side."""
        if self.manifest is None or not self.journey_root:
            return
        j = next((x for x in self.manifest.journeys if x.id == jid), None)
        if j is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Base party / seed — {jid}")
        form = QFormLayout(dlg)
        party = QLineEdit(", ".join(j.seed.party))
        party.setPlaceholderText("Zidane, Vivi, Dagger   (character names, comma-separated)")
        scenario = QLineEdit("" if j.seed.scenario is None else str(j.seed.scenario))
        scenario.setPlaceholderText("optional story beat (the seed scenario)")
        form.addRow("Base party", party)
        form.addRow("Start beat", scenario)
        if j.is_bare:
            note = QLabel("⚠ This is a BARE single-field journey: the base PARTY won't apply (it's injected into "
                          "a MULTI-campaign entry's script at deploy). Set the party on the entry FIELD's [party] "
                          "in the Editor instead. The start beat still seeds hub-side.")
            note.setStyleSheet(f"color:{self.pal['warn']};")
        else:
            note = QLabel("The base party + start beat seed the journey's entry member at deploy (the story_flags "
                          "capstone). Zidane is implicit — New Game already seeds him in slot 0.")
            note.setStyleSheet(f"color:{self.pal['muted']};")
        note.setWordWrap(True)
        form.addRow(note)
        form.addRow(self._ok_cancel(dlg))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._apply_journey_seed(jid, scenario.text().strip(), party.text().strip())

    def _apply_journey_seed(self, jid, scenario_text, party_text) -> bool:
        """Validate + upsert journey ``jid``'s ``[journey.seed]`` in the open hub, then re-open (re-lint +
        re-list). Returns True on success. The dialog-free core of :meth:`on_set_journey_seed` (headlessly
        testable). ``party_text`` is a comma-separated name list; blank scenario clears the start beat."""
        import tomllib
        from .. import journey as J
        try:
            party = [p.strip() for p in str(party_text).split(",") if p.strip()]
            sc = int(scenario_text) if str(scenario_text).strip() else None
            text = J.set_journey_seed(Path(self.journey_root).read_text(encoding="utf-8"), jid,
                                      scenario=sc, party=party)
            tomllib.loads(text)                    # belt-and-suspenders: the result must still parse
            Path(self.journey_root).write_text(text, encoding="utf-8", newline="\n")
            self.open_journey(self.journey_root)   # re-lint (the bare-party warning surfaces here) + re-list
            self.statusBar().showMessage(f"Set base party / seed for '{jid}'")
            return True
        except (ValueError, TypeError, J.JourneyError, tomllib.TOMLDecodeError, OSError) as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Couldn't set the journey seed"),
                                [fb.Problem(fb.ERROR, str(e))])
            return False

    def on_set_journey_tuning(self, jid):
        """Edit a journey's ``[journey.tuning]`` -- the mod-GLOBAL player/ability CSV deltas (BaseStats /
        abilities / leveling) -- in a modal editor that reuses the battle Party & abilities forms. For a BARE
        journey it won't apply (warned in the dialog + the lint)."""
        if self.manifest is None or not self.journey_root:
            return
        j = next((x for x in self.manifest.journeys if x.id == jid), None)
        if j is None:
            return
        from .tuningdialog import TuningDialog
        dlg = TuningDialog(self, self.pal, jid, j.tuning, is_bare=j.is_bare)
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.result_tuning is None:
            return                                         # cancelled (accept-with-empty -> {} clears the tuning)
        self._apply_journey_tuning(jid, dlg.result_tuning)

    def _apply_journey_tuning(self, jid, tuning) -> bool:
        """Write journey ``jid``'s ``[journey.tuning]`` back to the open hub + re-open (re-lint surfaces the
        mod-global / bare warnings). Returns True on success. The dialog-free core (headlessly testable)."""
        import tomllib
        from .. import journey as J
        try:
            text = J.set_journey_tuning(Path(self.journey_root).read_text(encoding="utf-8"), jid, tuning)
            tomllib.loads(text)                            # belt-and-suspenders: the result must still parse
            Path(self.journey_root).write_text(text, encoding="utf-8", newline="\n")
            self.open_journey(self.journey_root)           # re-lint + re-list
            self.statusBar().showMessage(f"Set tuning for '{jid}'")
            return True
        except (ValueError, TypeError, J.JourneyError, tomllib.TOMLDecodeError, OSError) as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Couldn't set the journey tuning"),   # TypeError: an
                                [fb.Problem(fb.ERROR, str(e))])                             # unserializable value
            return False

    def on_remove_journey_row(self, jid):
        """Confirm + remove a hub menu row (the dialog/Delete-key entry to :meth:`_remove_journey_row`)."""
        if self._confirm(f"Remove journey '{jid}'",
                         f"Remove the menu row '{jid}' from this hub?\n\n(The installed slice it points to is "
                         "NOT deleted — only this menu choice.)"):
            self._remove_journey_row(jid)

    def _remove_journey_row(self, jid) -> bool:
        """Remove the ``[[journey]]`` row ``jid`` from the open hub, then re-open (re-lint + re-list). Returns
        True on success. The dialog-free core (so it's headlessly testable)."""
        if self.manifest is None or not self.journey_root:
            return False
        from .. import journey as J
        try:
            text = J.remove_journey_row(Path(self.journey_root).read_text(encoding="utf-8"), jid)
            Path(self.journey_root).write_text(text, encoding="utf-8", newline="\n")
            self.open_journey(self.journey_root)
            self.statusBar().showMessage(f"Removed journey '{jid}'")
            return True
        except (J.JourneyError, OSError) as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Couldn't remove the journey"),
                                [fb.Problem(fb.ERROR, str(e))])
            return False

    # ---- grow a multi-campaign arc: add an FF9 region (refarc.append_region_to_arc) ----
    def _has_multi_arc(self) -> bool:
        """True iff the open manifest has a multi-campaign journey (``campaigns = [...]``) -- the gate for
        'Add region to arc' + 'Fill entry from forks'."""
        return self.manifest is not None and any(j.campaigns for j in self.manifest.journeys)

    def _pick_regions(self, *, title="Add region to arc", exclude=None):
        """Show the FF9 region catalog (``refarc``'s ``reference_arcs.toml``) as a checkable list; return the
        selected region KEYS in catalog order (``[]`` on cancel / none checked). Regions in ``exclude`` are shown
        disabled (default = the open arc's members, so 'Add region to arc' can't re-add; pass ``set()`` from the
        New-Journey picker where there's no target arc). The dialog half (headless core = :meth:`_apply_add_region`)."""
        from .. import refarc as RA
        try:
            arcset = RA.load_region_catalog()
        except Exception as e:                          # noqa: BLE001
            self._show_problems(fb.Verdict(fb.ERROR, "Region catalog"),
                                [fb.Problem(fb.ERROR, f"Couldn't load the FF9 region catalog: {e}")])
            return []
        existing = exclude if exclude is not None else {
            c for j in (self.manifest.journeys if self.manifest else []) for c in (j.campaigns or [])}
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        lay = QVBoxLayout(dlg)
        intro = QLabel(f"<b>{html.escape(arcset.title)}</b> — check the FF9 region(s) to add to the arc, in story "
                       "order. Each becomes its own forked campaign with a disjoint id band + flag window; the "
                       "boundary link is wired by 'Fill entry &amp; links from forks' after you fork it.")
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.TextFormat.RichText)
        intro.setStyleSheet(f"color:{self.pal['muted']};")
        lay.addWidget(intro)
        lst = QListWidget()
        for a in arcset.arcs:
            tag = "   ✓ in arc" if a.key in existing else ""
            it = QListWidgetItem(f"{a.name}   (seed {a.seed}){tag}")
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            it.setData(Qt.ItemDataRole.UserRole, a.key)
            if a.note:                                  # the catalog note shows even on a disabled "✓ in arc" row
                it.setToolTip(a.note + ("  (already in this arc)" if a.key in existing else ""))
            if a.key in existing:                       # already chained -> not re-addable (append is idempotent)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            lst.addItem(it)
        lay.addWidget(lst)
        bb = QDialogButtonBox()
        bb.addButton("Add selected", QDialogButtonBox.ButtonRole.AcceptRole)
        bb.addButton(QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return []
        return [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())
                if lst.item(i).checkState() == Qt.CheckState.Checked]

    def on_add_region_to_arc(self):
        """Add FF9 region(s) to the open multi-campaign arc -- the bottom-up faithful-recreation loop
        (fork-a-region, playtest, add the next). Opens the catalog -> :meth:`_apply_add_region`."""
        if not self._has_multi_arc() or not self.journey_root:
            return
        keys = self._pick_regions()
        if keys:
            self._apply_add_region(keys)

    def _apply_add_region(self, keys) -> bool:
        """Append the chosen region keys (in order) to the open arc's chain
        (:func:`ff9mapkit.refarc.append_region_to_arc` each), then write + re-open (re-lint + re-list). Notes go
        to the Output console; the re-open's journey lint owns Problems. Dialog-free core (headlessly testable).
        Returns True iff it changed the file."""
        if self.manifest is None or not self.journey_root:
            return False
        import tomllib
        from .. import refarc as RA
        try:
            bykey = {a.key: a for a in RA.load_region_catalog().arcs}
            orig = Path(self.journey_root).read_text(encoding="utf-8")
            text, added, log = orig, [], []
            for k in keys:
                arc = bykey.get(k)
                if arc is None:
                    log.append(f"unknown region {k!r} — skipped")
                    continue
                text, notes = RA.append_region_to_arc(text, arc)
                log.extend(n.text for n in notes)
                if any(n.level == "filled" for n in notes):
                    added.append(k)
            if text == orig:
                self._show_problems(fb.Verdict(fb.WARN, "Add region — nothing added"),
                                    [fb.Problem(fb.WARN, t) for t in log] or [fb.Problem(fb.WARN, "nothing to add")])
                return False
            tomllib.loads(text)                          # belt-and-suspenders: the result must still parse
            Path(self.journey_root).write_text(text, encoding="utf-8", newline="\n")
            self.output.appendPlainText("Add region to arc:\n  " + "\n  ".join(log))
            self.open_journey(self.journey_root)         # re-lint + re-list (now owns Problems)
            self.statusBar().showMessage(f"Added {len(added)} region(s): {', '.join(added)} — fork them "
                                         "(Fork panel), then 'Fill entry from forks'")
            return True
        except (ValueError, tomllib.TOMLDecodeError, OSError) as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Couldn't add the region"),
                                [fb.Problem(fb.ERROR, str(e))])
            return False

    def _needs_reconcile(self) -> bool:
        """True iff the open manifest has a multi-campaign journey still carrying STEP-2 placeholders
        (``ENTRY_MEMBER`` / ``BOUNDARY_MEMBER`` / ``ARRIVAL_MEMBER``) -- the signal to offer 'Fill entry &
        links from forks'. Cheap text check (no resolution)."""
        if self.manifest is None or not self.journey_root:
            return False
        if not any(j.campaigns for j in self.manifest.journeys):
            return False
        try:
            text = Path(self.journey_root).read_text(encoding="utf-8")
        except OSError:
            return False
        return any(ph in text for ph in ("ENTRY_MEMBER", "BOUNDARY_MEMBER", "ARRIVAL_MEMBER"))

    def on_reconcile_journey(self):
        """Fill the multi-campaign journey's ``entry`` + ``[[journey.link]]`` rows from the forked campaigns
        beside the manifest (STEP 2, automated). The button/palette entry to :meth:`_reconcile_journey`."""
        self._reconcile_journey()

    def _reconcile_journey(self) -> bool:
        """STEP 2: replace the reference-arc scaffold's ``ENTRY_MEMBER`` + commented ``[[journey.link]]``
        templates with the REAL member names of the campaigns forked beside the manifest
        (:func:`ff9mapkit.refarc.reconcile_arc_journey`). Writes + re-opens (the journey lint then shows the
        now-resolved state -- clean, or a precise 'fill this boundary' error for any seam it couldn't auto-find).
        Dialog-free core (headlessly testable); returns True iff it wrote a change."""
        if self.manifest is None or not self.journey_root:
            return False
        import tomllib
        from .. import refarc as RA, journey as J
        try:
            text = Path(self.journey_root).read_text(encoding="utf-8")
            new_text, notes = RA.reconcile_arc_journey(text, self.manifest.root)
            filled = [n.text for n in notes if n.level == "filled"]
            verify = [n.text for n in notes if n.level == "verify"]
            if new_text == text:                       # nothing filled -> show why (no re-open, so Problems is ours)
                self._show_problems(
                    fb.Verdict(fb.WARN if (verify or not filled) else fb.OK, "Reconcile — nothing to fill"),
                    [fb.Problem(fb.WARN, n.text) for n in notes] or [fb.Problem(fb.WARN, "nothing to reconcile")])
                return False
            tomllib.loads(new_text)                    # belt-and-suspenders: the result must still parse
            Path(self.journey_root).write_text(new_text, encoding="utf-8", newline="\n")
            self.open_journey(self.journey_root)       # re-lint + re-list -- the lint now owns Problems (cleaner)
            tail = f" — {len(verify)} note(s) to review (see the Output console + any inline # VERIFY/# FILL)" if verify else ""
            self.statusBar().showMessage(f"Filled entry & links from the forked campaigns{tail}")
            return True
        except (ValueError, J.JourneyError, tomllib.TOMLDecodeError, OSError) as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Couldn't reconcile the journey"),
                                [fb.Problem(fb.ERROR, str(e))])
            return False

    def on_open_campaign(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open campaign.toml", "",
                                           "Campaign (campaign.toml);;TOML (*.toml);;All files (*)")
        if f:
            self.open_campaign(Path(f))

    def on_open_field(self):
        # default to ALL .toml (the old "*.field.toml" default HID a plainly-named field.toml -> "nothing happened")
        f, _ = QFileDialog.getOpenFileName(self, "Open a field.toml", "",
                                           "Field / TOML (*.toml);;Field only (*.field.toml);;All files (*)")
        if f:
            self.open_field(Path(f))

    def _close_project(self):
        """The escape hatch: close whatever is open (journey / campaign / loose field) and return to the empty
        Workspace, from ANY tab. Prompts for unsaved edits first. This is the visible 'way out' -- previously
        the only exit was Open Field (which silently no-ops if its file dialog is cancelled)."""
        if not self._maybe_prompt_unsaved():
            return
        self.plan = self.campaign_path = self.journey_name = None
        self.manifest = self.journey_root = self._journey_label_path = self._loose = None
        self._loose_parent = (None, None, None)
        self.member_paths = {}
        self._docs = {}
        self._clean = {}
        self._touched = set()
        self._reset_history()
        self.tree.clear()
        self._member_items = {}
        self._root_items = []
        self._clear_doc()
        self.map.clear()
        self._content_crumbs = []
        self._content_chip = None
        self.crumb.set([])
        self.crumb.set_chip("")
        self.act_check.setEnabled(False)
        self.story_state.set_flag_names({})        # no project -> drop the authored-flag labels
        self.tabs.setCurrentWidget(self._welcome_tab)
        self.statusBar().showMessage("Closed — open a journey, campaign, or field to begin.")

    # ---- create new (field / campaign / member) ----
    def _default_new_dest(self) -> str:
        """The folder the New pickers start in (the last one chosen, else the repo root)."""
        return getattr(self, "_last_new_dir", None) or str(REPO)

    def _pick_dir(self, line_edit, caption):
        d = QFileDialog.getExistingDirectory(self, caption, line_edit.text().strip() or self._default_new_dest())
        if d:
            line_edit.setText(d)
            self._last_new_dir = d

    def _dir_row(self, line_edit, caption):
        """A folder QLineEdit + a Browse… button, as one row widget (for the New dialogs)."""
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(line_edit, 1)
        b = QPushButton("Browse…")
        b.clicked.connect(lambda _=False: self._pick_dir(line_edit, caption))
        h.addWidget(b)
        return row

    @staticmethod
    def _ok_cancel(dlg):
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        return bb

    def _new_field(self, name, dest, *, field_id=None, area=11, pitch=48.0, title=None):
        """Scaffold a standalone field project (``pack.new_project`` -- placeholder art, walkable) and open
        it. Returns the new field.toml path. Raises ValueError on a bad name or an existing project."""
        from .. import pack
        name = _field_token(name)
        area = int(area)
        if area < 10:
            raise ValueError(f"area must be ≥ 10 (got {area}) — single-digit areas black-screen (CLAUDE.md §7)")
        if field_id is not None and not (4000 <= int(field_id) <= 32767):
            raise ValueError(f"field id {field_id} out of the custom band 4000–32767 (real ids are locked)")
        proj_dir = Path(dest) / name
        fpath = proj_dir / f"{name.lower()}.field.toml"
        if fpath.exists():
            raise ValueError(f"{fpath.name} already exists in {proj_dir} — pick a new name or folder")
        pack.new_project(name, dest, field_id=field_id, area=area, pitch=float(pitch),
                         title=(title or None))
        self._last_new_dir = str(dest)
        self.open_field(fpath)
        return fpath

    def on_new_field(self):
        """New Field… dialog -> scaffold + open a standalone field.toml."""
        dlg = QDialog(self)
        dlg.setWindowTitle("New field")
        form = QFormLayout(dlg)
        name = QLineEdit()
        name.setPlaceholderText("MY_ROOM")
        dest = QLineEdit(self._default_new_dest())
        fid = QLineEdit()
        fid.setPlaceholderText("auto (suggested)")
        area = QLineEdit("11")
        pitch = QLineEdit("48")
        form.addRow("Name", name)
        form.addRow("Destination", self._dir_row(dest, "Choose where to scaffold the field"))
        form.addRow("Field id", fid)
        form.addRow("Area (≥10)", area)
        form.addRow("Camera pitch", pitch)
        note = QLabel("A new walkable room with PLACEHOLDER art is created under "
                      "<dest>/<NAME>/ and opened. Repaint the layers + author it here.")
        note.setStyleSheet(f"color:{self.pal['muted']};")
        note.setWordWrap(True)
        form.addRow(note)
        form.addRow(self._ok_cancel(dlg))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._new_field(name.text(), dest.text().strip() or self._default_new_dest(),
                            field_id=(int(fid.text()) if fid.text().strip() else None),
                            area=int(area.text() or 11), pitch=float(pitch.text() or 48))
        except (ValueError, OSError) as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Couldn't create the field"),
                                [fb.Problem(fb.ERROR, str(e))])

    def _new_campaign(self, name, dest, *, mod_folder="FF9CustomMap", id_base=4000):
        """Create an EMPTY campaign (``campaign.new_campaign``) and open it. Add rooms afterward from the
        campaign root. Returns the campaign.toml path. Raises ValueError / CampaignError on bad input."""
        name = str(name).strip()
        if not name:
            raise ValueError("a campaign name is required")
        dest = Path(dest)
        cpath = dest / "campaign.toml"
        if cpath.exists():
            raise ValueError(f"a campaign.toml already exists in {dest} — choose an empty folder")
        C.new_campaign(name, mod_folder or "FF9CustomMap", dest, id_base=int(id_base))
        self._last_new_dir = str(dest)
        self.open_campaign(cpath)
        return cpath

    def on_new_campaign(self):
        """New Campaign… dialog -> create + open an empty campaign.toml."""
        mod_folder, _fid = jobs.detect_deploy_target(REPO)
        dlg = QDialog(self)
        dlg.setWindowTitle("New campaign")
        form = QFormLayout(dlg)
        name = QLineEdit()
        name.setPlaceholderText("My Campaign")
        dest = QLineEdit(self._default_new_dest())
        mod = QLineEdit(mod_folder or "FF9CustomMap")
        idb = QLineEdit("4000")
        form.addRow("Name", name)
        form.addRow("Folder", self._dir_row(dest, "Choose the campaign folder (campaign.toml goes here)"))
        form.addRow("Mod folder", mod)
        form.addRow("First field id", idb)
        note = QLabel("An empty campaign.toml is created here and opened. Right-click the campaign in the "
                      "tree (or its root) to <b>Add field…</b>.")
        note.setStyleSheet(f"color:{self.pal['muted']};")
        note.setWordWrap(True)
        form.addRow(note)
        form.addRow(self._ok_cancel(dlg))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._new_campaign(name.text(), dest.text().strip() or self._default_new_dest(),
                               mod_folder=mod.text().strip() or "FF9CustomMap",
                               id_base=int(idb.text() or 4000))
        except (ValueError, C.CampaignError, OSError) as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Couldn't create the campaign"),
                                [fb.Problem(fb.ERROR, str(e))])

    @staticmethod
    def _all_catalog_regions(campaigns) -> bool:
        """True iff every name in ``campaigns`` is a known FF9 region key (``refarc``'s ``reference_arcs.toml``)
        -- the signal that a Multi journey should render the FAITHFUL fork playbook, not the typed-folder
        placeholder template. False (caught) if the catalog can't load."""
        try:
            from .. import refarc as RA
            keys = {a.key for a in RA.load_region_catalog().arcs}
            return bool(campaigns) and all(c in keys for c in campaigns)
        except Exception:                               # noqa: BLE001 -- no catalog -> fall back to the template
            return False

    def _new_journey(self, name, dest, *, kind="bare", hub_id=4600, borrow_bg="N11_HUT", jid="intro",
                     jname="Intro", entry=4100, scenario=None, campaigns=None):
        """Write a journeys.toml from the New-Journey choices + open it. ``kind='bare'`` = a complete file;
        ``kind='multi'`` = hub + first journey filled in, links/seed left to fill; ``kind='refarc'`` = the FF9
        reference-arc scaffold (the disc-1 story spine as a chained journey + the per-arc import-chain fork
        playbook, via `refarc`). Returns the path. Raises ValueError on an empty name or an existing manifest."""
        name = str(name).strip()
        if not name:
            raise ValueError("a hub / journey name is required")
        dest = Path(dest)
        jpath = dest / "journeys.toml"
        if jpath.exists():
            raise ValueError(f"a journeys.toml already exists in {dest} — choose another folder")
        dest.mkdir(parents=True, exist_ok=True)
        if kind == "refarc":
            from .. import refarc as RA
            # the generic N11_HUT placeholder OR the Mognet bg -> use refarc's full Mognet-Central default
            # (borrow_bg + area + borrow_field, so `deploy_journey --apply` auto-extracts the camera); a truly
            # custom borrow_bg is passed through (just the bg + a commented borrow_field hint).
            bg = (borrow_bg or "").strip()
            use = None if bg in ("", "N11_HUT", RA.HUB_BORROW_BG) else bg
            text = RA.render_arc_journey_toml(RA.load_reference_arcs(), hub_name=name, hub_id=hub_id, borrow_bg=use)
        elif kind == "hub":
            from .. import journey as J, refarc as RA
            bg = (borrow_bg or "").strip()                 # same Mognet-Central default as the reference-arc hub
            use = None if bg in ("", "N11_HUT", RA.HUB_BORROW_BG) else bg
            text = J.render_selector_hub_toml(hub_name=name, hub_id=hub_id, borrow_bg=use)
        elif kind == "multi" and campaigns and self._all_catalog_regions(campaigns):
            # the campaign names are all FF9 catalog regions -> render the FAITHFUL multi-campaign arc (the fork
            # PLAYBOOK + entry/link templates), so the Fork panel can fork each and reconcile wires the seams.
            from .. import refarc as RA
            bykey = {a.key: a for a in RA.load_region_catalog().arcs}
            picked = RA.ReferenceArcSet(title=(jname or "FF9 region arc"), arcs=[bykey[c] for c in campaigns])
            bg = (borrow_bg or "").strip()
            use = None if bg in ("", "N11_HUT", RA.HUB_BORROW_BG) else bg
            text = RA.render_arc_journey_toml(picked, hub_name=name, hub_id=hub_id,
                                              journey_id=(jid or "ff9_arc"), journey_name=(jname or None), borrow_bg=use)
        else:
            text = _render_journey_toml(hub_name=name, hub_id=hub_id, borrow_bg=borrow_bg or "N11_HUT",
                                        jid=jid or "intro", jname=jname or "Intro", kind=kind,
                                        entry=entry, scenario=scenario, campaigns=campaigns)
        jpath.write_text(text, encoding="utf-8", newline="\n")
        self._last_new_dir = str(dest)
        self.open_journey(jpath)
        return jpath

    def _fork_ff9_regions(self):
        """Open the FF9 region catalog on the Import tab — pick real FF9 areas to fork as campaigns (one, or
        several composed into one). The region-fork home (the old New-Journey 'FF9 reference arc' moved here)."""
        self.tabs.setCurrentWidget(self.import_field)
        self.import_field.open_region_catalog()

    def on_new_journey(self):
        """New Journey… dialog: pick Bare / Multi-campaign / FF9-reference-arc + the hub / first-journey values,
        so the generated journeys.toml has REAL values (not placeholders) and the dialog itself shows what a
        journey IS."""
        dlg = QDialog(self)
        dlg.setWindowTitle("New journey")
        form = QFormLayout(dlg)
        bare_rb = QRadioButton("Bare — the hub warps straight to ONE field")
        multi_rb = QRadioButton("Multi-campaign arc — chain forked campaigns")
        hub_rb = QRadioButton("World Hub — a menu that lists installed journeys, pick one at New Game")
        bare_rb.setChecked(True)
        grp = QButtonGroup(dlg)
        grp.addButton(bare_rb)
        grp.addButton(multi_rb)
        grp.addButton(hub_rb)
        trow = QWidget()
        tl = QVBoxLayout(trow)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(bare_rb)
        tl.addWidget(multi_rb)
        tl.addWidget(hub_rb)
        regions_hint = QLabel("Forking FF9 areas as campaigns moved to <b>Import → Browse FF9 regions…</b> "
                              "(or Ctrl-K → “Fork FF9 regions”) — a region catalog, not a journey.")
        regions_hint.setTextFormat(Qt.TextFormat.RichText)
        regions_hint.setWordWrap(True)
        regions_hint.setStyleSheet(f"color:{self.pal['muted']};")
        tl.addWidget(regions_hint)
        form.addRow("Type", trow)
        name = QLineEdit()
        name.setPlaceholderText("My Hub")
        dest = QLineEdit(self._default_new_dest())
        hub_id = QLineEdit("4600")
        borrow = QLineEdit("N11_HUT")
        jid = QLineEdit("intro")
        jname = QLineEdit("Intro")
        form.addRow("Hub name", name)
        form.addRow("Folder", self._dir_row(dest, "Choose a folder for the journeys.toml"))
        form.addRow("Hub field id", hub_id)
        form.addRow("Hub art (borrow a real field)", borrow)
        form.addRow("First journey id", jid)
        form.addRow("First journey name", jname)
        entry = QLineEdit("4100")
        scenario = QLineEdit()
        scenario.setPlaceholderText("optional story beat")
        campaigns = QLineEdit()
        campaigns.setPlaceholderText("dali, dali_outside   (folders you've forked)")
        bare_panel, bl = QWidget(), None
        bl = QFormLayout(bare_panel)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addRow("Entry field id", entry)
        bl.addRow("Scenario", scenario)
        multi_panel = QWidget()
        ml = QFormLayout(multi_panel)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.addRow("Campaign folders", campaigns)
        pick_regions = QPushButton("Pick FF9 regions…")
        pick_regions.setToolTip("Choose real FF9 regions from the catalog — they fill the folders above AND make "
                                "this a faithful arc with a fork playbook (each region forks into its own band).")
        pick_regions.clicked.connect(
            lambda: campaigns.setText(", ".join(self._pick_regions(title="Pick FF9 regions", exclude=set()))
                                      or campaigns.text()))
        ml.addRow("", pick_regions)
        hub_panel = QWidget()
        hl = QVBoxLayout(hub_panel)
        hl.setContentsMargins(0, 0, 0, 0)
        hub_blurb = QLabel("Creates an empty World Hub (just the <code>[hub]</code> menu field). After it opens, "
                           "use <b>Add journey…</b> to add one menu row per installed slice — each row warps "
                           "into a field you've already forked &amp; deployed.")
        hub_blurb.setWordWrap(True)
        hub_blurb.setTextFormat(Qt.TextFormat.RichText)
        hl.addWidget(hub_blurb)
        stack = QStackedWidget()
        stack.addWidget(bare_panel)
        stack.addWidget(multi_panel)
        stack.addWidget(hub_panel)
        form.addRow(stack)
        note = QLabel()
        note.setStyleSheet(f"color:{self.pal['muted']};")
        note.setWordWrap(True)
        form.addRow(note)
        form.addRow(self._ok_cancel(dlg))

        from .. import refarc as _RA
        _NOTES = {
            0: "A <b>complete</b>, ready-to-build journeys.toml — the hub menu warps straight to your entry field.",
            1: "A faithful multi-campaign arc (New Game plays straight through). <b>Pick FF9 regions…</b> for the "
               "fork playbook (each region forks into its own id band; <b>Add region to arc…</b> grows it later), "
               "or type folders you forked yourself. Fork the campaigns, then 'Fill entry &amp; links from forks'.",
            2: "A journey SELECTOR: New Game lands on the hub and you pick which installed journey to play. "
               "Creates the empty hub; add a menu row per slice with <b>Add journey…</b> afterward. The hub "
               "defaults to <b>Mognet Central</b> (the journey nexus).",
        }
        def _toggle():
            rbs = [bare_rb, multi_rb, hub_rb]
            idx = next((i for i, rb in enumerate(rbs) if rb.isChecked()), 0)
            stack.setCurrentIndex(idx)
            # swap the borrow-art default to match the kind (the World-Hub field defaults to Mognet Central,
            # FF9's journey nexus) WITHOUT clobbering a value the user actually typed.
            cur = borrow.text().strip()
            if idx == 2 and cur in ("", "N11_HUT"):
                borrow.setText(_RA.HUB_BORROW_BG)
            elif idx != 2 and cur in ("", _RA.HUB_BORROW_BG):
                borrow.setText("N11_HUT")
            note.setText(_NOTES[idx])
        for rb in (bare_rb, multi_rb, hub_rb):
            rb.toggled.connect(_toggle)
        _toggle()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        kind = "bare" if bare_rb.isChecked() else "multi" if multi_rb.isChecked() else "hub"
        hub_name = name.text().strip() or {"hub": "World Hub"}.get(kind, "")
        try:
            self._new_journey(
                hub_name, dest.text().strip() or self._default_new_dest(), kind=kind,
                hub_id=int(hub_id.text() or 4600), borrow_bg=borrow.text().strip() or "N11_HUT",
                jid=jid.text().strip() or "intro", jname=jname.text().strip() or "Intro",
                entry=int(entry.text() or 4100),
                scenario=int(scenario.text()) if (kind == "bare" and scenario.text().strip()) else None,
                campaigns=[c.strip() for c in campaigns.text().split(",") if c.strip()] if kind == "multi" else None)
        except (ValueError, OSError) as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Couldn't create the journey"),
                                [fb.Problem(fb.ERROR, str(e))])

    def _add_field_to_campaign(self, name, *, source=None):
        """Append a member to the OPEN campaign (``campaign.add_field``): a blank walkable room (offline) or
        -- with ``source`` (a real field id/name) -- a fork (needs the game). Re-renders the tree + Map and
        selects the new member. Returns the new Member (or None if no campaign is open)."""
        if self.plan is None or self.campaign_path is None:
            return None
        member = C.add_field(self.plan, self.campaign_path.parent, name=name, source=source, game=None)
        self.member_paths = {m.name: (self.campaign_path.parent / m.toml_rel).resolve()
                             for m in self.plan.members}
        self._populate()
        g = C.campaign_graph(self.plan)
        self.map.render(g, g.entry or (self.plan.members[0].name if self.plan.members else None))
        self._select_member(member.name)
        self.statusBar().showMessage(f"Added {member.name} (id {member.new_id}) to {self.plan.name}")
        return member

    def on_add_field(self):
        """Add field… dialog (from the campaign root's right-click) -> scaffold a blank member + select it."""
        if self.plan is None or self.campaign_path is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Add field to campaign")
        form = QFormLayout(dlg)
        name = QLineEdit()
        name.setPlaceholderText("ROOM2")
        form.addRow("Name", name)
        note = QLabel("A new blank, walkable room is scaffolded and added to this campaign.<br>"
                      "To fork a REAL field into the campaign, use the <b>Import</b> tab or "
                      "<code>ff9mapkit add-field --source</code>.")
        note.setStyleSheet(f"color:{self.pal['muted']};")
        note.setWordWrap(True)
        form.addRow(note)
        form.addRow(self._ok_cancel(dlg))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._add_field_to_campaign(name.text().strip())
        except (ValueError, C.CampaignError, OSError, RuntimeError) as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Couldn't add the field"),
                                [fb.Problem(fb.ERROR, str(e))])

    def _save_output(self, text):
        """Sink for the docked save editors' Preview/Apply output -> the bottom Output panel (console's
        natural home), so a docked save doc doesn't spend its body height on its own console box."""
        self.output.setPlainText(text)
        self._raise_dock()

    def _project_flag_names(self) -> dict:
        """``{absolute gEventGlobal bit: authored [[flag]] name}`` for the OPEN project (loose field / campaign /
        journey), to annotate the Story State save view (audit #7). A named ``[[flag]] index`` is ABSOLUTE --
        never offset by a campaign/journey flag-window -- so this is a pure identity map (no offset math, the
        whole no-mislabel guarantee). Fail-safe: ANY error -> ``{}`` (no annotation rather than a wrong one).
        A cross-source index collision -> an ``<ambiguous>`` sentinel, never a silent pick."""
        import tomllib
        from .. import flags as _flags
        seen: dict = {}

        def _add(raw):
            for idx, name in _flags.project_flag_names(raw).items():
                prev = seen.get(idx)
                seen[idx] = name if prev in (None, name) else "<ambiguous>"

        def _read(p):
            with open(p, "rb") as fh:
                return tomllib.load(fh)

        try:
            if self.manifest is not None and self.plan is None:        # JOURNEY: every member of every campaign
                for j in self.manifest.journeys:
                    for folder in (j.campaigns or []):
                        ct = self.manifest.root / folder / "campaign.toml"
                        if ct.is_file():
                            plan = C.load_campaign(ct)
                            _add({"flag": getattr(plan, "flags", []) or []})
                            for m in plan.members:
                                mp = ct.parent / m.toml_rel
                                if mp.is_file():
                                    _add(_read(mp))
            elif self.plan is not None:                                # CAMPAIGN: shared flags + each member
                _add({"flag": getattr(self.plan, "flags", []) or []})
                for name, mp in self.member_paths.items():
                    doc = self._docs.get(name)                         # prefer the IN-MEMORY doc (picks up unsaved edits)
                    if doc is not None:
                        _add(doc.data)
                    elif Path(mp).is_file():
                        _add(_read(mp))
            elif self._loose is not None:                              # LOOSE single field
                doc = self._docs.get(self._loose)
                if doc is not None:
                    _add(doc.data)
        except Exception:                                              # noqa: BLE001 -- fail-safe to no annotation
            return {}
        return seen

    def _refresh_flag_names(self):
        """Re-push the open project's authored flag names to Story State, so an already-loaded save re-annotates
        when you open/close/switch a project (and clears to bare numbers when nothing is open)."""
        self.story_state.set_flag_names(self._project_flag_names())

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
        self.story_state.set_flag_names(self._project_flag_names())   # annotate with the open project's [[flag]] names
        self.tabs.setCurrentWidget(self.story_state)

    def open_field(self, path) -> bool:
        """Open a STANDALONE field.toml (no campaign) -- the 'Loose field' mode, so any authored field
        can be edited directly. Mirrors the tkinter editor opening a lone file."""
        if not self._maybe_prompt_unsaved():
            return False
        self._clear_doc()                          # drop the prior file's mounted form (stale _save_ctx)
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
        self.manifest = None                       # a standalone field leaves any journey context
        self.journey_root = None
        self._loose = name
        self._loose_parent = self._field_parent_campaign(path)   # is this loose field actually a campaign member?
        self.member_paths = {name: path.resolve()}
        self._docs = {name: doc}
        self._clean = {name: copy.deepcopy(doc.data)}
        self._touched = set()                      # fresh open -> nothing in-progress
        self._reset_history()                      # a different file -> drop the old undo history
        self._seed_undo_base(name)
        self.map.clear()                           # a standalone field has no campaign map
        self.build_deploy.set_target(path)         # pre-aim Build & Deploy at the open field
        self.act_check.setEnabled(True)
        self.act_lint_cli.setEnabled(False)       # lint-campaign is campaign-only
        self._populate_field(name)
        self.statusBar().showMessage(f"{name} — standalone field — {path}")
        self._select_member(name)
        self.tabs.setCurrentWidget(self.doc_scroll)   # a standalone field has no map -> show its Editor
        self._refresh_flag_names()                    # re-annotate an already-open Story State save with this field
        return True

    def _populate_field(self, name):
        self.tree.clear()
        self._member_items = {}
        self._root_items = []                      # loose mode: the member IS the top-level (it gets its own dot)
        mi = self._mk("field", name, name, "•")
        self.tree.addTopLevelItem(mi)
        self._member_items[name] = mi
        mi.addChild(self._mk("__lazy__", "loading…"))   # lazy object load on expand (same as a member)
        mi.setExpanded(True)
        self._refresh_dirty_marks()                     # reserve the icon slot from the first paint

    def _field_parent_campaign(self, field_path):
        """If a standalone field.toml is actually a MEMBER of a campaign, return (campaign.toml, member_name,
        campaign_name); else (None, None, None). Reverse-searches campaign.toml in the field's own dir + up to
        2 ancestors and matches by RESOLVED member path (mirrors open_campaign's member_paths resolution) -- so
        a loosely-opened member can jump UP into its full campaign context (the spine made two-way; do-now #5)."""
        try:
            field_path = Path(field_path).resolve()
        except Exception:                              # noqa: BLE001
            return (None, None, None)
        d = field_path.parent
        for _ in range(3):                             # the field's own dir, then up to 2 ancestors
            ct = d / "campaign.toml"
            if ct.is_file():
                try:
                    plan = C.load_campaign(ct)
                    for m in plan.members:
                        if (ct.parent / m.toml_rel).resolve() == field_path:
                            return (ct, m.name, plan.name)
                except Exception:                      # noqa: BLE001  -- a malformed campaign.toml just doesn't match
                    pass
            if d.parent == d:
                break
            d = d.parent
        return (None, None, None)

    def _open_parent_campaign(self):
        """The upward jump: promote the open loose field into its parent campaign -- open the campaign, then
        select THIS field within it, so you keep editing the same field but now WITH the Map / cross-refs /
        siblings (today journey->campaign is one-way; this makes field->campaign traversable too)."""
        ct, member, _name = self._loose_parent
        if ct is None:
            return
        if self.open_campaign(ct) and member in getattr(self, "_member_items", {}):
            self._select_member(member)
            self.tabs.setCurrentWidget(self.doc_scroll)   # you were editing the field -> its Editor, not the Map

    def _on_battle_open(self, path):
        """A battle.toml opened/forked on the Battle tab -> pre-aim Build & Deploy at it (do-now #6), so it's
        ready when you switch there. Mirrors how opening a field/campaign/journey pre-aims Build & Deploy."""
        self.build_deploy.set_target(path)
        self.statusBar().showMessage(f"Build & Deploy aimed at {Path(path).name}", 4000)

    def _import_forked(self, out_dir):
        """An Import fork finished cleanly -> open the project it wrote (a campaign.toml, else a single
        field.toml), so the Import→author handoff is ONE step instead of 'now go open it on Build & Deploy'
        (do-now #6). open_campaign/open_field also pre-aim Build & Deploy, so it's immediately buildable."""
        out = Path(out_dir)
        if (out / "campaign.toml").is_file():
            self.open_campaign(out / "campaign.toml")
            return
        for pat in ("*.field.toml", "field.toml", "*/*.field.toml"):
            hits = sorted(out.glob(pat))
            if hits:
                self.open_field(hits[0])
                return
        self.statusBar().showMessage(f"Imported to {out} — no campaign.toml / field.toml found to open.", 6000)

    def open_campaign(self, path, *, keep_journey=False) -> bool:
        if not self._maybe_prompt_unsaved():
            return False
        self._clear_doc()                          # drop the prior file's mounted form (stale _save_ctx)
        path = Path(path)
        try:
            plan = C.load_campaign(path)
        except Exception as e:                     # noqa: BLE001
            self.statusBar().showMessage(f"Open failed: {e}")
            return False
        if not keep_journey:                       # opening a campaign DIRECTLY leaves any journey context
            self.manifest = None
            self.journey_root = None
        self.plan = plan
        self._loose = None                         # leaving loose mode -> a real campaign is open
        self.campaign_path = path
        self.member_paths = {m.name: (path.parent / m.toml_rel).resolve() for m in plan.members}
        # drilling in from a journey KEEPS open_journey's label (stable + always present, so the back-row
        # never vanishes); a DIRECT campaign open reverse-searches for a nearby journeys.toml (display only).
        if not keep_journey:
            self.journey_name = self._journey_label()
        self._docs = {}
        self._clean = {}
        self._touched = set()
        self._reset_history()                      # a different campaign -> drop the old undo history
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
        self._refresh_flag_names()                 # re-annotate an already-open Story State save with this campaign
        return True

    def _journey_label(self):
        """A real journey from a journeys.toml beside the campaign or one level up (display only; mirrors
        the tkinter navigator -- see docs/JOURNEYS.md). None when none is defined."""
        self._journey_label_path = None
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
                        self._journey_label_path = jt      # so the journey row can open it (jump to journey)
                        return j["name"]
            except Exception:                      # noqa: BLE001
                continue
        return None

    def _populate(self):
        self.tree.clear()
        self._root_items = []
        g = C.campaign_graph(self.plan)
        parent = self.tree
        if self.journey_name:
            jr = self._mk("journey", self.journey_name, "@journey", "◆")
            jr.setForeground(0, QBrush(QColor(self.pal["accent"])))
            self.tree.addTopLevelItem(jr)
            jr.setExpanded(True)
            parent = jr
            self._root_items.append(jr)
        camp = self._mk("campaign", self.plan.name, "@campaign", "▣")
        camp.setForeground(0, QBrush(QColor(self.pal["accent"])))
        (parent.addChild(camp) if isinstance(parent, QTreeWidgetItem) else self.tree.addTopLevelItem(camp))
        camp.setExpanded(True)
        self._root_items.append(camp)
        self._member_items = {}
        for node in g.nodes:
            mi = self._mk("field", node.name, node.name, _badge(node))
            col = _health(node, self.pal)
            if col:
                mi.setForeground(0, QBrush(QColor(col)))
            camp.addChild(mi)
            self._member_items[node.name] = mi
            mi.addChild(self._mk("__lazy__", "loading…"))   # placeholder -> lazy object load on expand
        self._refresh_dirty_marks()                         # reserve the icon slot from the first paint

    # ---- lazy object load ----
    def _on_expand(self, item):
        kind = (self._payload(item) or (None,))[0]
        if kind == "field":
            if item.childCount() == 1 and (self._payload(item.child(0)) or (None,))[0] == "__lazy__":
                item.takeChild(0)
                self._load_objects(item)
        elif kind == "logic_root":
            if item.childCount() == 1 and (self._payload(item.child(0)) or (None,))[0] == "__lazy_logic__":
                item.takeChild(0)
                self._load_logic_map(item)

    def _load_logic_map(self, grp):
        """Populate a verbatim member's 'Script' group with a READ-ONLY logic map of its shipped ``.eb``:
        every entry/routine, the resolved call graph, and the dialogue/item/flag effects each routine
        performs (logic_map.build_logic_map). Built from the member's LOCAL ``verbatim_eb.bin`` -- no game
        install needed. The legible view of the entanglement the declarative editor can't express."""
        field_item = self._ancestor_field(grp)
        if field_item is None:
            return
        name = self._payload(field_item)[1]
        try:
            from .. import logic_map as LM
            eb, entries, _lang = self._member_logic_inputs(name)
            lm = LM.build_logic_map(eb, entries=entries)
            self._logic_maps = getattr(self, "_logic_maps", {})
            self._logic_maps[name] = lm                 # cache for the edit panel's per-routine summary
        except Exception as e:                          # noqa: BLE001
            grp.addChild(self._mk("note", f"(could not build logic map: {e})"))
            return
        grp.setData(0, _DETAIL, [
            f"{len([x for x in lm.entries if x.role != 'empty'])} entries, {len(lm.nodes)} routines",
            self._muted("a read-only view of the shipped .eb — edit it in place (Phase 2), not here"),
            self._muted("'?' marks a target chosen at runtime (computed / dynamic-caller) — unresolvable offline")])
        from .. import logic_map as LM
        by_entry = {}
        for n in lm.nodes:
            by_entry.setdefault(n.entry, []).append(n)
        shown = 0
        for e in lm.entries:
            if e.role == "empty":
                continue
            nodes = [n for n in by_entry.get(e.index, []) if not n.empty]
            if not nodes and e.role in ("logic",):       # a contentless region/seq entry -> skip the clutter
                continue
            model = f"  {e.model_name or ('model ' + str(e.model_id))}" if e.model_id is not None else ""
            ehdr = self._mk("logic_entry", f"entry {e.index}: {e.role}{model}", f"logic_e:{e.index}")
            ehdr.setData(0, _DETAIL, [_esc(s) for s in self._logic_entry_detail(e)])
            for n in nodes:
                rn = self._mk("logic_node", f"{n.kind} / tag {n.tag}{LM.node_hint(n)}", f"logic_n:{e.index}:{n.tag}")
                rn.setData(0, _DETAIL, [_esc(s) for s in LM.node_report(n)] or [self._muted("—")])
                ehdr.addChild(rn)
            grp.addChild(ehdr)
            shown += 1
        if not shown:
            grp.addChild(self._mk("note", "(no script content decoded)"))

    @staticmethod
    def _logic_entry_detail(e):
        out = [f"role: {e.role}"]
        if e.model_id is not None:
            out.append(f"model: {e.model_name or e.model_id}")
        if e.role not in ("main", "player"):
            out.append(f"spawned: {e.spawns}x" if e.spawns else "defined, not spawned")
        out.append(f"functions (tags): {', '.join(str(t) for t in e.tags) or '—'}")
        return out

    def _member_logic_inputs(self, member):
        """Load a verbatim member's ``.eb`` bytes AS THE BUILD EDITS THEM + parsed us ``.mes`` (line text) +
        ALL-language ``.mes`` bodies (for per-language text edits) from the LOCAL sidecars -- no game install.
        Shared by the read-only logic map and the in-place edit panel. Returns ``(eb_bytes, us_entries|None,
        {lang: body})``; raises on a missing/unreadable ``.bin``."""
        import json
        from .. import dialogue as _d
        spec = (self._doc(member).data.get("verbatim_eb") or {})
        base = Path(self.member_paths[member]).parent
        eb = self._composed_verbatim_eb(member, spec, base)
        entries, lang_bodies = None, {}
        tj = spec.get("text")
        if tj and (base / tj).exists():
            blocks = json.loads((base / tj).read_text(encoding="utf-8"))
            if isinstance(blocks, dict):
                lang_bodies = {k: v for k, v in blocks.items() if isinstance(v, str)}
                body = blocks.get("us") or next(iter(lang_bodies.values()), None)
                if body:
                    entries = _d.parse_mes(body)
        return eb, entries, lang_bodies

    def _composed_verbatim_eb(self, member, spec, base):
        """The member's verbatim ``.eb`` AS THE BUILD EDITS IT: the donor bytes with the ``retarget`` Field-remap
        + the ``[startup]``/``[party]``/``[[on_entry]]`` field-load inserts applied (``build.compose_verbatim_eb``,
        the SAME composition Check + the build run), so the panel's discovery + dry-run can't disagree with the
        build (a ``field`` warp's ``old`` and a flag/item ``nth`` are computed on the SAME stream). Built from the
        ON-DISK project -- the build also runs on saved files, and the GUI doesn't edit retarget/startup, only the
        ``[[logic_edit]]`` list (applied separately). Degrades to the retargeted donor, then the raw donor, if the
        project can't be composed, so the panel never breaks."""
        raw = (base / spec["bin"]).read_bytes()
        try:
            from .. import build as _build
            eb, _suffix = _build.compose_verbatim_eb(_build.FieldProject.load(self.member_paths[member]))
            if eb is not None:
                return eb
        except Exception:                              # noqa: BLE001 -- e.g. a jump-table donor -> degrade
            pass
        try:                                           # at least apply the Field() retarget (the common case)
            from ..content.verbatim import remap_fields
            rt = {int(k): int(v) for k, v in (spec.get("retarget") or {}).items()}
            if rt:
                return remap_fields(raw, rt)
        except Exception:                              # noqa: BLE001
            pass
        return raw

    def _doc(self, member):
        """The member's FieldDoc, loaded once and cached (the form edits this instance + saves it)."""
        if member not in self._docs:
            self._docs[member] = FieldDoc.load(self.member_paths[member])
            self._clean[member] = copy.deepcopy(self._docs[member].data)   # dirty baseline
            self._seed_undo_base(member)                                   # undo-history baseline (loaded state)
        return self._docs[member]

    def _mark_clean(self, member):
        """Snapshot a member's doc as the saved baseline (so _dirty_members no longer flags it)."""
        if member in self._docs:
            self._clean[member] = copy.deepcopy(self._docs[member].data)
        self._touched.discard(member)              # a save clears the in-progress flag too
        self._refresh_dirty_marks()

    def _dirty_members(self):
        """Cached members whose in-memory doc differs from its load/last-save baseline."""
        return [m for m in self._docs if self._docs[m].data != self._clean.get(m)]

    def _touch(self, member):
        """Mark a member as having in-progress edits (a list/step mutation) + refresh the tree dots."""
        self._touched.add(member)
        self._refresh_dirty_marks()

    def _on_form_change(self, member):
        """A form WIDGET changed: dot the member only if the active form now DIFFERS from the saved
        baseline -- so reverting a value back to its original un-dots the row -- else clear it."""
        ctx = self._save_ctx
        if ctx and ctx.get("member") == member and self._form_matches_baseline(ctx):
            self._touched.discard(member)
        else:
            self._touched.add(member)
        self._refresh_dirty_marks()

    def _form_matches_baseline(self, ctx) -> bool:
        """True if the mounted form's current values equal the saved baseline's section (normalized through
        build_entity both ways, so default-equal omissions don't count as a change). False on a bad value."""
        try:
            entity = forms.build_entity(ctx["spec"], read(ctx["getters"]))
        except ValueError:
            return False
        clean = self._clean.get(ctx["member"], {})
        if ctx["single"]:
            base = clean.get(ctx["section"], {}) or {}
        else:
            lst = clean.get(ctx["section"], []) or []
            idx = ctx.get("idx")
            base = lst[idx] if idx is not None and idx < len(lst) else {}
        return forms.build_entity(ctx["spec"], forms.entity_to_values(ctx["spec"], base)) == entity

    def _unsaved(self):
        """Members to flag with the unsaved-dot: committed-but-unsaved OR typed-but-uncommitted."""
        return set(self._dirty_members()) | self._touched

    @staticmethod
    def _make_dot_icon(color):
        """A 12px QIcon: a filled circle in ``color`` (the unsaved dot), or a TRANSPARENT same-size icon
        when ``color`` is None -- a non-null blank icon still reserves the row's icon slot, so swapping it
        for the dot never resizes or horizontally shifts the row."""
        pm = QPixmap(12, 12)                        # matches the tree iconSize so it isn't scaled/blurred
        pm.fill(QColor(0, 0, 0, 0))
        if color is not None:
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color))
            p.drawEllipse(2, 2, 8, 8)
            p.end()
        return QIcon(pm)

    def _refresh_dirty_marks(self):
        """Show the amber unsaved-dot icon on each member row with unsaved changes (committed or
        in-progress); roll it up to the campaign/journey root and the window title so unsaved work is
        visible even when the member rows are collapsed or scrolled away."""
        unsaved = self._unsaved()
        for name, mi in getattr(self, "_member_items", {}).items():
            mi.setIcon(0, self._dot_icon if name in unsaved else self._blank_icon)
        any_unsaved = bool(unsaved)
        for root in getattr(self, "_root_items", []):
            root.setIcon(0, self._dot_icon if any_unsaved else self._blank_icon)
        self.setWindowTitle("Dream World IX — Workspace" + ("  •" if any_unsaved else ""))
        self._refresh_save_button()

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
            it = self._mk("object", label, key)
            if key not in data:                        # absent -> dim it (click to author; created on save)
                it.setForeground(0, QBrush(QColor(self.pal["muted"])))
            member_item.addChild(it)
        for key, label in _LISTS:
            lst = data.get(key, []) or []
            grp = self._mk("group", f"{label} ({len(lst)})", key)
            for i, e in enumerate(lst):
                lbl = forms.choice_summary(e) if key == "choice" else (e.get("name") or f"#{i}")
                grp.addChild(self._mk("object", lbl, f"{key}:{i}"))
            member_item.addChild(grp)
        if data.get("verbatim_eb"):                    # a VERBATIM fork: the lists above are empty BY DESIGN --
            # the real content lives in the shipped .eb. Badge the row + add a read-only logic-map subtree.
            member_item.setText(0, member_item.text(0).split("  · ")[0] + "  · verbatim")
            member_item.setToolTip(0, "verbatim fork — ships the donor's whole .eb; the lists above are empty by "
                                      "design. Expand 'Script (verbatim .eb)' for its real content (read-only).")
            grp = self._mk("logic_root", "Script (verbatim .eb)", "logic")
            grp.addChild(self._mk("__lazy_logic__", "loading…"))
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
        if self.manifest is not None and self.plan is None:   # JOURNEY mode: no field forms, just overview/inspect
            self._on_select_journey(item, self._payload(item))
            return
        if not self._commit_active_ck():           # fold + checkpoint the leaving form; stay put on a bad value
            return
        self._touched &= set(self._dirty_members())   # reconcile: a touched-but-reverted member is clean now
        self._refresh_dirty_marks()
        p = self._payload(item)
        field_item = self._ancestor_field(item)
        field = self._payload(field_item)[1] if field_item is not None else None
        obj_label = obj_key = None
        if field_item is not None and item is not field_item and p:
            obj_label, obj_key = p[1], p[2]
        self._content_crumbs = bc.trail(self.journey_name, self.plan.name if self.plan else None,
                                        field, obj_label, obj_key or "")
        self.crumb.set(self._content_crumbs)
        self._content_chip = self._chip_for_kind(p[0]) if p else None
        self._set_chip(self._content_chip)
        self._inspect(item, p, field)
        if field and getattr(self, "map", None) is not None:
            self.map.highlight(field)              # keep the Map in sync, but DON'T steal the active tab
        if field_item is not None and p:
            member = self._payload(field_item)[1]
            if item is field_item:                 # the member row itself -> its Field form
                self._open_editor(member, "field", "field")
            elif p[0] == "logic_node":             # a verbatim routine -> the in-place [[logic_edit]] panel
                self._open_editor(member, "logic_node", p[2])
            elif p[0] not in _LOGIC_KINDS:         # an object/group under it -> edit by its key
                self._open_editor(member, p[0], p[2])
            #                                        (logic_root / logic_entry are containers -> inspector only)

    def _on_select_journey(self, item, p):
        """JOURNEY-mode selection: a journey/root row shows the plan overview; a campaign row prompts to open
        it. No field forms, no dirty tracking (nothing's editable until you drill into a campaign)."""
        if not p:
            return
        kind, label, _key = p
        self.insp_title.setText(label)
        self.insp_body.setToolTip("")
        self._inspect_path = None
        self._content_crumbs = self._journey_crumbs(item)     # full hub▸journey▸campaign trail to THIS node
        self.crumb.set(self._content_crumbs)
        self._content_chip = self._chip_for_kind(kind)        # the chip names the SELECTED row's type
        self._set_chip(self._content_chip)
        if kind == "jcampaign":
            self.insp_body.setText("<br>".join([
                self._muted("a member campaign of this journey"),
                self._muted("double-click (or Enter) to open it for editing")]))
        elif kind == "jbare":
            self.insp_body.setText(self._muted("a bare single-field journey — the hub warps straight to this field"))
        else:                                      # jset / journey -> the resolved plan overview
            jid = _key.split(":", 1)[1] if kind == "journey" and _key and ":" in _key else None
            self._mount_journey_overview(selected_jid=jid)
            self.insp_body.setText("<br>".join([
                f"{len(self.manifest.journeys)} journey(s)",
                self._muted("Check lints the global id/flag namespace → Problems")]))

    # ---- do-now #1: the persistent edit-target indicator (breadcrumb + doc-mode chip), truthful per tab ----
    @staticmethod
    def _chip_for_kind(kind):
        """The chip MODE for a selected tree node's payload kind -- so the chip names the SELECTED thing's
        TYPE (HUB / JOURNEY / CAMPAIGN / FIELD), not just the open document. Objects/groups/logic nodes read
        as FIELD (you're editing within a field)."""
        return {"jset": "hub", "journey": "journey", "jcampaign": "campaign", "campaign": "campaign",
                "jbare": "field", "field": "field"}.get(kind, "field")

    def _set_chip(self, mode):
        """Drive the breadcrumb's left chip from a mode name (battle = warn-coloured to read as off-spine)."""
        chips = {"hub": ("HUB", "accent"), "journey": ("JOURNEY", "accent"), "campaign": ("CAMPAIGN", "accent"),
                 "field": ("FIELD", "accent"), "battle": ("BATTLE", "warn"),
                 "save": ("SAVE", "accent"), "build": ("BUILD", "accent")}
        spec = chips.get(mode)
        if spec is None:
            self.crumb.set_chip("")
            return
        label, ckey = spec
        self.crumb.set_chip(label, self.pal.get(ckey, self.pal["accent"]))

    def _journey_crumbs(self, item):
        """The full hub▸journey▸campaign/field trail to a selected JOURNEY-mode tree node (each crumb keyed by
        its payload so :meth:`_on_crumb` can navigate to it). The leaf is where you are; its ancestors are the
        containment chain -- so the breadcrumb tells the whole 'which is which' story, not just the hub name."""
        level_for = {"jset": bc.HUB, "journey": bc.JOURNEY, "jcampaign": bc.CAMPAIGN, "jbare": bc.FIELD}
        chain = []
        node = item
        while node is not None:
            pp = self._payload(node)
            if pp:
                chain.append(bc.Crumb(level_for.get(pp[0], bc.OBJECT), pp[1], pp[2]))
            node = node.parent()
        chain.reverse()
        return chain

    def _on_tab_changed(self, _idx=None):
        """Keep the breadcrumb + chip truthful on EVERY tab. Content tabs (Editor/Map) restore the cached
        tree-driven journey▸campaign▸field▸object trail + the selected node's chip; each self-contained doc tab
        (Battle/Save/Build) names what IT edits via its own ``crumb_label()``; Import/Welcome show the project
        context with no edit chip (they don't edit the open doc)."""
        if not hasattr(self, "tabs"):
            return
        w = self.tabs.currentWidget()
        if w in (self.doc_scroll, self.map):
            self.crumb.set(self._content_crumbs)
            self._set_chip(self._content_chip)
        elif w is self.battle:
            self.crumb.set([bc.Crumb(bc.BATTLE, w.crumb_label())])
            self._set_chip("battle")
        elif w in (self.story_state, self.item_equip):
            self.crumb.set([bc.Crumb(bc.SAVE, w.crumb_label())])
            self._set_chip("save")
            if w is self.story_state:                  # re-read the open project's [[flag]] names on each view
                self._refresh_flag_names()             # so the annotation is current no matter the open/edit order
        elif w is self.build_deploy:
            self.crumb.set([bc.Crumb("build", w.crumb_label())])
            self._set_chip("build")
        else:                                      # Import / Home -> project context, but no edit-target chip
            self.crumb.set(self._content_crumbs)
            self._set_chip(None)
            if w is self._welcome_tab:              # Home: refresh the 'Currently editing …' line on show
                self._refresh_home_status()

    def _on_tree_double(self, item, _col=0):
        """Double-click = explicit 'open': a field/object -> the Editor; a campaign/journey root -> the Map;
        a journey member campaign -> open it; the journey root row (when a journey is loaded) -> the overview."""
        p = self._payload(item)
        if not p:
            return
        kind = p[0]
        if kind == "jcampaign":                    # drill from the journey into a member campaign (editable)
            self._open_member_campaign(p[2])
            return
        if kind == "journey" and self.plan is not None:   # the journey row above a drilled-in campaign -> back
            if self.manifest is not None:
                self._back_to_journey()
            elif self._journey_label_path is not None:    # opened the campaign directly -> jump UP to its journey
                self.open_journey(self._journey_label_path)
            return
        if kind in ("jset", "journey", "jbare"):   # journey-mode rows -> the overview doc
            self.tabs.setCurrentWidget(self.doc_scroll)
            return
        self.tabs.setCurrentWidget(self.map if kind == "campaign" else self.doc_scroll)

    def _open_current_tree_item(self):
        """Enter on the focused tree row = open it (the keyboard equivalent of a double-click)."""
        item = self.tree.currentItem()
        if item is not None:
            self._on_tree_double(item)

    # ---- command palette (Ctrl-K) ----
    def _command_index(self):
        """The palette's entries: named commands + every navigable node currently in the tree (members
        always; a field's objects once it's been expanded)."""
        cmds = [
            ("New Field…", "command", self.on_new_field),
            ("New Campaign…", "command", self.on_new_campaign),
            ("New Journey…", "command", self.on_new_journey),
            ("Open Journey…", "command", self.on_open_journey),
            ("Open Campaign…", "command", self.on_open_campaign),
            ("Open Field…", "command", self.on_open_field),
            ("Open Save…", "command", self._open_save),
            ("Check", "command", self.on_check),
            ("Lint (CLI)", "command", self.run_cli_lint),
            ("Browse catalog (Info Hub)", "command", self._open_catalog),
            ("Fork FF9 regions…", "command", self._fork_ff9_regions),
            ("Undo", "command", self._undo),
            ("Redo", "command", self._redo),
            ("Save All fields", "command", self._save_all),
            ("Go to Editor", "view", lambda: self.tabs.setCurrentWidget(self.doc_scroll)),
            ("Go to Map", "view", lambda: self.tabs.setCurrentWidget(self.map)),
            ("Go to Story State", "view", lambda: self.tabs.setCurrentWidget(self.story_state)),
            ("Go to Item & Equip", "view", lambda: self.tabs.setCurrentWidget(self.item_equip)),
            ("Go to Build & Deploy", "view", lambda: self.tabs.setCurrentWidget(self.build_deploy)),
            ("Go to Import", "view", lambda: self.tabs.setCurrentWidget(self.import_field)),
        ]
        if self.plan is not None and self.campaign_path is not None:
            cmds.insert(2, ("Add field to campaign…", "command", self.on_add_field))
        if self.manifest is not None:
            cmds.insert(2, ("Add journey to hub…", "command", self.on_add_journey_row))
            if any(j.campaigns for j in self.manifest.journeys):
                cmds.insert(3, ("Add region to arc…", "command", self.on_add_region_to_arc))
                cmds.insert(4, ("Fill entry from forks…", "command", self.on_reconcile_journey))
        content = []

        def walk(item):
            p = self._payload(item)
            if p and p[0] in ("jset", "jcampaign", "journey", "campaign", "field", "object", "group"):
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
        """Open the Info Hub as a SECTIONED LIBRARY (`CatalogLibrary`): a category sidebar with counts, a
        per-section searchable list, and a rich detail pane (facts/animations/movement/parts/aliases + a
        ready field.toml snippet). Replaces the old all-in-one flat browse list; the in-form picker stays
        `CatalogPicker`."""
        from .forms_qt import CatalogLibrary
        CatalogLibrary(self, self.plan, self.pal).exec()

    def _save_shortcut(self):
        """Ctrl-S: save the mounted form (the same as clicking its Save button)."""
        if self._active_save is not None:
            self._active_save()

    # ---- undo / redo (a per-field document history) ----
    # The model: each member's doc.data is the editing buffer; _undo_base[member] tracks its state as of the
    # last checkpoint. _checkpoint() diffs the buffer against that base and, on a real change, records one
    # _UndoRec (before/after whole-doc snapshots) + advances the base. Undo/redo rewrite the buffer IN MEMORY
    # only (never disk) -- the restored buffer is dirty-tracked vs _clean like any edit, so Save persists it.
    # In-field typing undo stays with the focused QLineEdit/QPlainTextEdit (see _undo_shortcut); this app-level
    # history covers COMMITTED edits (a folded form, an add/delete/reset, a cutscene/choice step).
    def _checkpoint(self, member, label, focus):
        """Record an undo step if ``member``'s doc changed since its last checkpoint; advance the baseline."""
        if member not in self._docs:
            return
        cur = self._docs[member].data
        base = self._undo_base.get(member)
        if base is None:                              # first sight of this member -> seed the baseline, no step
            self._undo_base[member] = copy.deepcopy(cur)
            return
        if base == cur:
            return                                    # no real change (a viewed-but-unedited form folds to a no-op)
        snap = copy.deepcopy(cur)
        self._undo_stack.append(_UndoRec(member, base, snap, label, focus))
        self._undo_base[member] = snap
        if len(self._undo_stack) > UNDO_LIMIT:
            self._undo_stack.pop(0)
        self._redo_stack.clear()                      # a fresh edit invalidates the redo branch
        self._refresh_undo_actions()

    def _seed_undo_base(self, member):
        """Seed a member's history baseline at its loaded state (so the FIRST edit is recordable)."""
        if member in self._docs:
            self._undo_base[member] = copy.deepcopy(self._docs[member].data)

    def _reset_history(self):
        """Drop all undo/redo history + baselines (on opening a different campaign/field)."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._undo_base.clear()
        self._refresh_undo_actions()

    def _commit_active_ck(self) -> bool:
        """``_commit_active`` + checkpoint the leaving form's edit (the nav / save / close boundary). Returns
        ``_commit_active``'s bool so callers still abort a switch on an invalid value."""
        prev = self._save_ctx
        if not self._commit_active():
            return False
        if prev:
            self._checkpoint(prev["member"], f"edit {prev['section']}", prev["key"])
        return True

    def _undo_shortcut(self):
        """Ctrl-Z: let a focused text widget undo its own typing first; otherwise undo a committed edit."""
        if not self._delegate_text_history(redo=False):
            self._undo()

    def _redo_shortcut(self):
        if not self._delegate_text_history(redo=True):
            self._redo()

    @staticmethod
    def _delegate_text_history(redo) -> bool:
        """If an EDITABLE text widget is focused AND has in-field history, route Ctrl-Z/Ctrl-Shift-Z to IT (so
        per-keystroke undo inside a field keeps working) and return True; else False (do app-level undo).
        A READ-ONLY box (the Output console / a wrap-preview / a save Inspect pane) is never an editing buffer
        -- setReadOnly doesn't disable its document's undo, so delegating there would wipe its shown text."""
        w = QApplication.focusWidget()
        if not isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit)) or w.isReadOnly():
            return False
        if isinstance(w, QLineEdit):
            avail = w.isRedoAvailable() if redo else w.isUndoAvailable()
        else:
            d = w.document()
            avail = d.isRedoAvailable() if redo else d.isUndoAvailable()
        if avail:
            (w.redo if redo else w.undo)()
            return True
        return False

    def _undo(self):
        if not self._commit_active_ck():           # fold+checkpoint any pending edit FIRST (its own step) so a
            return                                 # typed-but-uncommitted change isn't lost; abort on a bad value
        if not self._undo_stack:
            return
        rec = self._undo_stack.pop()
        self._redo_stack.append(rec)
        self._apply_history(rec.member, rec.before, rec.focus, f"Undo {rec.label}")

    def _redo(self):
        if not self._commit_active_ck():           # (a pending edit is a divergence -> it commits + clears redo)
            return
        if not self._redo_stack:
            return
        rec = self._redo_stack.pop()
        self._undo_stack.append(rec)
        self._apply_history(rec.member, rec.after, rec.focus, f"Redo {rec.label}")

    def _apply_history(self, member, data, focus, note):
        """Restore ``member``'s buffer to ``data`` (a whole-doc snapshot), refresh its tree + re-show the
        edited node. In-memory only -- the restored buffer is dirty-tracked vs the saved baseline."""
        if member not in self._docs:                  # the campaign/field was closed -> the snapshot is stale
            self.statusBar().showMessage(f"{note} — {member} is no longer open", 4000)
            self._refresh_undo_actions()
            return
        self._docs[member].data = copy.deepcopy(data)
        self._undo_base[member] = copy.deepcopy(data)   # the next edit diffs against the restored state
        self._touched.discard(member)
        self._clear_doc()                             # drop the stale form BEFORE refreshing (no spurious fold)
        if member in getattr(self, "_member_items", {}):
            self.tree.blockSignals(True)
            self._refresh_objects(member)             # rebuild object rows (an add/delete changed them)
            self.tree.blockSignals(False)
        self._refresh_dirty_marks()
        self._refresh_undo_actions()
        self._goto_focus(member, focus)               # select + mount the edited node from restored data
        self.statusBar().showMessage(note, 3000)

    def _select_logic_node(self, member, entry, tag):
        """Expand the member's Script subtree + select its ``(entry, tag)`` routine row so the edit panel and
        the tree highlight agree (after an undo/redo). Returns True if the row was found + selected."""
        mi = getattr(self, "_member_items", {}).get(member)
        if mi is None:
            return False
        grp = next((mi.child(i) for i in range(mi.childCount())
                    if (self._payload(mi.child(i)) or (None,))[0] == "logic_root"), None)
        if grp is None:
            return False
        self.tree.expandItem(grp)                      # triggers the lazy _load_logic_map if not yet built
        want = f"logic_n:{entry}:{tag}"
        for ei in range(grp.childCount()):
            en = grp.child(ei)
            for ri in range(en.childCount()):
                rn = en.child(ri)
                if (self._payload(rn) or (None, None, None))[2] == want:
                    self.tabs.setCurrentWidget(self.doc_scroll)
                    self.tree.setCurrentItem(rn)       # fires _on_select -> mounts the panel + breadcrumb
                    return True
        return False

    def _goto_focus(self, member, key):
        """Select + mount the node ``(member, key)`` after an undo/redo (falls back to the member row)."""
        if key and key.startswith("logic_n:"):       # a verbatim logic-node edit -> re-open its edit panel
            parts = key.split(":")
            if len(parts) == 3 and member in self._docs:
                e_, t_ = int(parts[1]), int(parts[2])
                if not self._select_logic_node(member, e_, t_):   # select the tree row (panel + highlight agree)
                    self.tabs.setCurrentWidget(self.doc_scroll)   # row gone (lazy/closed) -> mount directly
                    self._mount_logic_node(member, e_, t_)
                return
        node = None
        if key and ":" in key:                        # a list entity (npc:2) or a choice (choice:0)
            node = self._object_item(member, key, kind="object")
        elif key in dict(_SINGLE):                    # a single section node (dialogue/encounter/music/cutscene)
            node = self._object_item(member, key, kind="object")
        elif key in _LIST_DEFAULTS:                   # a list header (npc/gateway/...) -> its group row
            node = self._object_item(member, key, kind="group")
        if node is None:                              # field/camera/loose/deleted-entity -> the member row
            node = getattr(self, "_member_items", {}).get(member)
        if node is None:
            self._doc_placeholder("Change applied.")
            return
        self.tabs.setCurrentWidget(self.doc_scroll)
        if self.tree.currentItem() is node:
            self._on_select()                         # selection unchanged -> mount manually (no signal fires)
        else:
            self.tree.setCurrentItem(node)            # selection change -> _on_select mounts it

    def _refresh_undo_actions(self):
        """Enable/disable + label the toolbar Undo/Redo from the stacks (shows the next op's name)."""
        u = self._undo_stack[-1].label if self._undo_stack else None
        r = self._redo_stack[-1].label if self._redo_stack else None
        if getattr(self, "act_undo", None) is not None:
            self.act_undo.setEnabled(bool(u))
            self.act_undo.setToolTip(f"Undo {u} (Ctrl+Z)" if u else "Undo (Ctrl+Z)")
        if getattr(self, "act_redo", None) is not None:
            self.act_redo.setEnabled(bool(r))
            self.act_redo.setToolTip(f"Redo {r} (Ctrl+Shift+Z)" if r else "Redo (Ctrl+Shift+Z)")

    def _save_all(self):
        """Ctrl-Shift-S / Save All: fold the active form in, then write every field with unsaved changes."""
        self._commit_active_ck()                   # the in-progress form counts as unsaved (+ checkpoint it)
        saved = 0
        for m in list(self._dirty_members()):
            path = self.member_paths.get(m)
            if path is None or protected_reason(path):
                continue
            try:
                self._docs[m].save()
            except Exception:                      # noqa: BLE001 -- best-effort; skip a locked/protected file
                continue
            self._mark_clean(m)                    # clears the dot + the touch for m
            saved += 1
        self._refresh_dirty_marks()
        left = self._dirty_members()
        if saved or left:
            note = f"Saved {saved} field(s)" + (f"; {len(left)} could not be written" if left else "")
            self._show_problems(fb.Verdict(fb.WARN if left else fb.OK, note), [])

    # ---- the document editor (Phase 4) ----
    def _set_editor_tab(self, suffix=None):
        """Title the Editor tab with what's open (e.g. 'Editor — Vivi'), or plain 'Editor' when empty."""
        idx = self.tabs.indexOf(self.doc_scroll)
        if idx >= 0:
            self.tabs.setTabText(idx, "Editor" + (f" — {suffix}" if suffix else ""))

    def _refresh_save_button(self):
        """Enable the mounted form's Save + Reset only when its field has something to save (clean -> grey)."""
        if not self._save_ctx:
            return
        enabled = self._save_ctx.get("member") in self._unsaved()
        for btn in (getattr(self, "_save_btn", None), getattr(self, "_reset_btn", None)):
            if btn is not None:
                btn.setEnabled(enabled)

    def _reset_active(self):
        """Reset = the opposite of Save: discard this form's unsaved edits by restoring its section/entity
        from the saved baseline, then re-mount it. (Greyed when there's nothing to reset.)"""
        ctx = self._save_ctx
        if not ctx:
            return
        member, section, key = ctx["member"], ctx["section"], ctx["key"]
        clean = self._clean.get(member, {})
        doc = self._doc(member)
        if ctx["single"]:
            if section in clean:
                doc.data[section] = copy.deepcopy(clean[section])
            else:
                doc.data.pop(section, None)                    # it didn't exist at last save -> drop it
        else:
            idx = ctx["idx"]
            base = clean.get(section, [])
            cur = doc.data.get(section, [])
            if idx is not None and idx < len(base) and idx < len(cur):
                cur[idx] = copy.deepcopy(base[idx])
        self._touched.discard(member)
        self._checkpoint(member, f"reset {section}", key)     # a Reset is itself an undoable change
        self._open_editor(member, "object", key)              # re-mount from the restored data
        self._refresh_dirty_marks()

    def _clear_doc(self):
        self._save_ctx = None                      # the about-to-be-removed form is no longer the active one
        self._active_save = None                   # ...and Ctrl-S has nothing to save until a form mounts
        self._save_btn = None
        self._reset_btn = None
        self._clear_layout(self.doc_host_lay)

    def _clear_layout(self, lay):
        """Empty a layout, deleting its widgets AND recursing into nested sub-layouts. ``takeAt`` pops a nested
        layout (e.g. the journey overview's button row, added via ``addLayout``) off the parent, but its child
        widgets stay PARENTED to the host widget and keep painting -- the 'journey buttons leak into the Script /
        marker / gateway panels' bug -- unless we descend and delete them too. Spacer items (``addStretch``) are
        neither widget nor layout, so ``takeAt`` removing them is enough."""
        while lay.count():
            it = lay.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()
                continue
            sub = it.layout()
            if sub is not None:
                self._clear_layout(sub)
                sub.deleteLater()

    def _doc_placeholder(self, text):
        self._clear_doc()
        self._set_editor_tab(None)
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
        if kind == "logic_node":                   # a verbatim routine -> the in-place [[logic_edit]] panel
            parts = key.split(":")                  # key = "logic_n:<entry>:<tag>"
            if len(parts) == 3:
                self._mount_logic_node(member, int(parts[1]), int(parts[2]))
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
        self._set_editor_tab(f"{sing}s")            # so the tab reflects the group, not the prior leaf's name
        n = len(self._doc(member).data.get(kind, []) or [])
        self._header(f"{member}  ·  {sing}s",
                     f"{n} {sing.lower()}(s) on this field. Add a new one below, or pick an existing item "
                     "in the tree to edit it.")
        btn = QPushButton(f"➕  Add {sing}")
        btn.setObjectName("accent")
        btn.clicked.connect(lambda _=False: self._add_list_item(member, kind))
        self.doc_host_lay.addWidget(btn, alignment=Qt.AlignLeft)
        self.doc_host_lay.addStretch(1)

    # ---- in-place edits of a verbatim fork's .eb (the "Script" subtree -> [[logic_edit]] authoring) ----
    def _logic_node(self, member, entry, tag, eb, entries):
        """The logic_map :class:`Node` for (entry, tag) -- reused for the panel's one-line summary + the
        collapsible 'what this routine does' transcript. Cached from the tree build; rebuilt offline if the
        tree wasn't expanded first. ``None`` if unavailable (the summary/report is best-effort, never fatal)."""
        from .. import logic_map as LM
        lm = getattr(self, "_logic_maps", {}).get(member)
        if lm is None:
            try:
                lm = LM.build_logic_map(eb, entries=entries)
            except Exception:                              # noqa: BLE001 -- best-effort context, never fatal
                return None
        return next((x for x in lm.nodes if x.entry == entry and x.tag == tag), None)

    def _logic_node_summary(self, member, entry, tag, eb, entries):
        """The one-line 'what this routine does' (logic_map.node_summary), or '' -- used by the smoke + tests."""
        from .. import logic_map as LM
        n = self._logic_node(member, entry, tag, eb, entries)
        return LM.node_summary(n) if n is not None else ""

    def _mount_logic_node(self, member, entry, tag):
        """The in-place edit panel for one verbatim routine: each editable value (item reward, gil, warp,
        story flag, dialogue line) as a row with an 'Edit…' affordance that authors a ``[[logic_edit]]`` into
        the member's field.toml (the amber-dot/Save flow). Sidesteps dead-end #14 -- edit the shipped ``.eb``
        IN PLACE rather than extract a routine. Each commit is dry-run-validated (build's verbatim pass)."""
        from .. import logic_edit as LE
        self._clear_doc()
        self._set_editor_tab(f"Script · entry {entry}")
        try:
            eb, entries, lang_bodies = self._member_logic_inputs(member)
            sites = LE.editable_effects(eb, entry, tag, entries=entries, lang_bodies=lang_bodies)
        except Exception as e:                          # noqa: BLE001
            self._doc_placeholder(f"Could not load the script for {member}: {e}")
            return
        self._header(f"{member}  ·  entry {entry} / tag {tag}",
                     "In-place edits to the shipped .eb / .mes. Changing a value authors a [[logic_edit]] — "
                     "length-preserving + old-guarded; the read-only tree above still shows the donor's "
                     "original. Run Check, then Build & Deploy.")
        from .. import logic_map as LM                  # context: WHAT this routine does, not just editable values
        node = self._logic_node(member, entry, tag, eb, entries)
        if node is not None:
            report = LM.node_report(node)
            summary = LM.node_summary(node)
            if report:                                  # a collapsible friendly transcript (header = the one-liner)
                self.doc_host_lay.addWidget(self._collapsible(
                    f"This routine {summary}" if summary else "What this routine does", report))
            elif summary:
                self.doc_host_lay.addWidget(self._muted_label(f"This routine {summary}."))
        reason = protected_reason(self.member_paths[member])
        if reason:
            self.doc_host_lay.addWidget(self._warn_label(
                f"⚠ {reason}. Save a copy in a folder of your own to author edits."))
        existing = self._doc(member).data.get("logic_edit") or []
        if sites:
            nedit = sum(1 for s in sites if self._logic_pending(s, existing))
            self.doc_host_lay.addWidget(self._muted_label(
                f"{len(sites)} editable value(s)" + (f" · {nedit} edited" if nedit else "")))
            for site in sites:
                self.doc_host_lay.addWidget(self._logic_site_row(member, entry, tag, site, existing))
        else:
            self.doc_host_lay.addWidget(self._muted_label(
                "No editable values in this routine — its rewards/warps/flags aren't literal operands. "
                "You can still ADD an effect below."))
        self._mount_logic_add_section(member, entry, tag, eb)       # [[logic_add]] authoring (length-changing)
        self._active_save = lambda m=member, e=entry, t=tag: self._save_logic(m, e, t)
        row = QHBoxLayout()
        row.setContentsMargins(0, 8, 0, 0)
        save = QPushButton("Save")
        save.setObjectName("accent")
        save.clicked.connect(lambda _=False: self._save_logic(member, entry, tag))
        row.addWidget(save)
        rst = QPushButton("Reset")
        rst.setToolTip("Discard ALL unsaved logic edits + added effects on this field (revert to the last save)")
        rst.clicked.connect(lambda _=False: self._reset_logic(member, entry, tag))
        row.addWidget(rst)
        row.addStretch(1)
        holder = QWidget()
        holder.setLayout(row)
        self.doc_host_lay.addWidget(holder)
        self.doc_host_lay.addStretch(1)

    def _muted_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{self.pal['muted']};")
        lbl.setWordWrap(True)
        return lbl

    def _warn_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{self.pal['warn']};")
        lbl.setWordWrap(True)
        return lbl

    def _collapsible(self, title, lines, *, open_=False):
        """A disclosure section: a clickable header (``title``) that shows/hides a body of muted ``lines``.
        Used for the read-only 'What this routine does' transcript so a big routine doesn't flood the panel."""
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(2)
        btn = QToolButton()
        btn.setText(title)
        btn.setCheckable(True)
        btn.setChecked(open_)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        btn.setArrowType(Qt.ArrowType.DownArrow if open_ else Qt.ArrowType.RightArrow)
        btn.setStyleSheet("QToolButton { border:none; font-weight:600; text-align:left; }")
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(16, 0, 0, 0)
        bl.setSpacing(1)
        for ln in lines:
            bl.addWidget(self._muted_label(_esc(ln)))
        body.setVisible(open_)

        def _toggle(checked):
            body.setVisible(checked)
            btn.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        btn.toggled.connect(_toggle)
        lay.addWidget(btn)
        lay.addWidget(body)
        return box

    @staticmethod
    def _logic_pending(site, edits):
        """The authored edits on ``site`` (coords in its footprint) within ``edits``, or []."""
        from .. import logic_edit as LE
        foot = LE.site_footprint(site)
        return [e for e in (edits or []) if LE.edit_coord(e) in foot]

    def _logic_site_row(self, member, entry, tag, site, existing):
        """One editable-value row: 'gives Potion  →  Elixir (unsaved)'  [Edit…] [Revert]. '(unsaved)' vs
        '(saved)' is decided by comparing this site's edits against the saved baseline -- so a fork opened with
        edits already in its toml reads '(saved)', not a false '(unsaved)'."""
        pend = self._logic_pending(site, existing)
        saved = self._logic_pending(site, (self._clean.get(member) or {}).get("logic_edit") or [])
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 2, 0, 2)
        cur = self._logic_value_str(site, site.old)
        if pend:
            state = ("saved", self.pal["muted"]) if pend == saved else ("unsaved", self.pal["warn"])
            txt = f'{site.label}  →  <b>{_esc(self._logic_pending_str(site, pend))}</b>  ' \
                  f'<span style="color:{state[1]};">({state[0]})</span>'
        else:
            txt = f"{site.label}" + (f"  <span style='color:{self.pal['muted']};'>= {_esc(cur)}</span>"
                                     if site.value_kind in ("int", "field", "flag") else "")
        lbl = QLabel(txt)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        if site.note and not pend:
            lbl.setToolTip(site.note)
        h.addWidget(lbl, 1)
        edit = QPushButton("Edit…")
        edit.clicked.connect(lambda _=False, s=site: self._edit_logic_site(member, entry, tag, s))
        h.addWidget(edit)
        if pend:
            rv = QPushButton("Revert")
            rv.clicked.connect(lambda _=False, s=site: self._revert_logic_site(member, entry, tag, s))
            h.addWidget(rv)
        return w

    def _logic_value_str(self, site, v):
        """A friendly rendering of a site value: an item name, a truncated string, else the number."""
        if site.value_kind == "item":
            from .. import items
            return items.name_of(v) or f"item #{v}"
        if site.value_kind == "string":
            s = " ".join(str(v).split())
            return '"' + (s[:44] + "…" if len(s) > 44 else s) + '"'
        return str(v)

    def _logic_pending_str(self, site, pend):
        """The new value to show on a row with a pending edit. An item shows item + quantity (either of which
        may be unchanged), so a count-only or id-only edit reads correctly."""
        if site.group == "item":
            id_edit = next((e for e in pend if e.get("kind") in ("item", "item_display")), None)
            cnt_edit = next((e for e in pend if e.get("kind") == "item_count"), None)
            new_id = id_edit["new"] if id_edit else site.old
            new_cnt = cnt_edit["new"] if cnt_edit else site.count_old
            return self._logic_value_str(site, new_id) + (f" ×{new_cnt}" if new_cnt is not None else "")
        return self._logic_value_str(site, pend[0].get(site.new_key))

    def _resolve_logic_value(self, site, text):
        """Parse the dialog text into a NEW value for ``site`` (an item name/id, a number, or a string).
        Raises ValueError with a hint on a bad value."""
        if site.value_kind == "string":
            return text
        text = (text or "").strip()
        if not text:
            raise ValueError("enter a value")
        if site.value_kind == "item":
            from .. import items
            try:
                return items.resolve(text)             # a name, or a 0–255 regular item id
            except ValueError:
                if text.isdigit():                     # allow a raw pool-encoded id beyond the named 0–255 space
                    return int(text)
                raise
        if not text.lstrip("-").isdigit():
            raise ValueError("enter a whole number")
        return int(text)

    def _logic_value_dialog(self, site):
        """Modal editor for one site's value; returns the NEW value (int, or str for a dialogue line) or None."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit value")
        form = QFormLayout(dlg)
        form.addRow(QLabel(site.label))
        if site.value_kind == "string":
            ed = QPlainTextEdit(str(site.old))
            ed.setMinimumSize(QSize(380, 96))
            form.addRow("New line", ed)
            if site.note:
                form.addRow(self._muted_label(site.note + " — other languages are set to this line too."))
            form.addRow(self._ok_cancel(dlg))
            return ed.toPlainText() if dlg.exec() == QDialog.DialogCode.Accepted else None
        prefill = self._logic_value_str(site, site.old) if site.value_kind == "item" else str(site.old)
        ed = QLineEdit(prefill)
        ed.setMinimumWidth(260)
        form.addRow("New value", ed)
        hint = self._muted_label(site.note or "")
        form.addRow(hint)
        if site.value_kind == "item":
            def on_change(*_):
                try:
                    v = self._resolve_logic_value(site, ed.text())
                    hint.setText(f"→ {self._logic_value_str(site, v)}  (#{v})")
                except ValueError as e:
                    hint.setText(f"⚠ {e}")
            ed.textChanged.connect(on_change)
            ed.selectAll()
            on_change()
        form.addRow(self._ok_cancel(dlg))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        try:
            return self._resolve_logic_value(site, ed.text())
        except ValueError as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Bad value"), [fb.Problem(fb.ERROR, str(e))])
            return None

    def _edit_logic_site(self, member, entry, tag, site):
        if site.group == "item":                                # an item reward: edit BOTH the item + quantity
            picked = self._logic_item_dialog(site)
            if picked is None:
                return
            self._commit_item_edit(member, entry, tag, site, *picked)
            return
        new = self._logic_value_dialog(site)
        if new is None:
            return
        if site.group != "text" and new == site.old:            # back to the donor value -> just clear the edit
            self._revert_logic_site(member, entry, tag, site)
            return
        self._commit_logic_edit(member, entry, tag, site, new)

    def _logic_item_dialog(self, site):
        """Modal editor for an item reward: pick a new item (name or id, live-resolved) AND, when the quantity
        is uniform across the give-paths, a quantity. Returns ``(new_id, new_count)`` or None."""
        from .. import items
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit item reward")
        form = QFormLayout(dlg)
        form.addRow(QLabel(site.label))
        item_ed = QLineEdit(self._logic_value_str(site, site.old))
        item_ed.setMinimumWidth(260)
        form.addRow("New item", item_ed)
        hint = self._muted_label("")
        form.addRow(hint)

        def on_change(*_):
            try:
                v = self._resolve_logic_value(site, item_ed.text())
                hint.setText(f"→ {self._logic_value_str(site, v)}  (#{v})")
            except ValueError as e:
                hint.setText(f"⚠ {e}")
        item_ed.textChanged.connect(on_change)
        item_ed.selectAll()
        on_change()
        qty_ed = None
        if site.count_old is not None:
            qty_ed = QLineEdit(str(site.count_old))
            form.addRow("Quantity", qty_ed)
        elif site.note:
            form.addRow(self._muted_label(site.note))
        form.addRow(self._ok_cancel(dlg))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        try:
            new_id = self._resolve_logic_value(site, item_ed.text())
            new_count = site.count_old
            if qty_ed is not None:
                txt = qty_ed.text().strip()
                if not txt.isdigit():
                    raise ValueError("quantity must be a whole number")
                new_count = int(txt)
                if not (1 <= new_count <= 255):
                    raise ValueError("quantity must be 1–255 (the AddItem count is one byte)")
        except ValueError as e:
            self._show_problems(fb.Verdict(fb.ERROR, "Bad value"), [fb.Problem(fb.ERROR, str(e))])
            return None
        return new_id, new_count

    def _commit_item_edit(self, member, entry, tag, site, new_id, new_count):
        """Author an item reward edit (give + paired display + quantity), dry-run-validated, into the member's
        logic_edit list. No change (same id + count) clears the site's edits."""
        from .. import logic_edit as LE
        doc = self._doc(member)
        edits = LE.synth_item_edits(site, new_id, new_count)
        cand = LE.upsert_edits(doc.data.get("logic_edit"), edits, drop=LE.site_footprint(site))
        err = self._validate_logic_candidate(member, cand)
        if err:
            self._show_problems(fb.Verdict(fb.ERROR, "Edit not applied — it wouldn't build"),
                                [fb.Problem(fb.ERROR, err)])
            return
        self._set_logic_edits(member, cand)
        self._reconcile_logic_dirty(member)
        self._checkpoint(member, "edit item", f"logic_n:{entry}:{tag}")
        self._mount_logic_node(member, entry, tag)
        qty = f" ×{new_count}" if new_count is not None else ""
        self._show_problems(fb.Verdict(fb.OK,
                            f"{member}: {site.label} → {self._logic_value_str(site, new_id)}{qty}"), [])

    def _commit_logic_edit(self, member, entry, tag, site, new):
        """Author (or replace) ``site``'s edit -> the member's ``logic_edit`` list, AFTER a clean offline
        dry-run (build's verbatim pass). On a validation error nothing is written + the reason is shown."""
        from .. import logic_edit as LE
        doc = self._doc(member)
        cand = LE.upsert_edits(doc.data.get("logic_edit"), LE.synth_edits(site, new),
                               drop=LE.site_footprint(site))
        err = self._validate_logic_candidate(member, cand)
        if err:
            self._show_problems(fb.Verdict(fb.ERROR, "Edit not applied — it wouldn't build"),
                                [fb.Problem(fb.ERROR, err)])
            return
        self._set_logic_edits(member, cand)
        self._touch(member)
        self._checkpoint(member, f"edit {site.group}", f"logic_n:{entry}:{tag}")
        self._mount_logic_node(member, entry, tag)              # re-render with the pending state
        notes = []
        try:                                                   # best-effort text-shadow pre-flight (never blocks)
            from .. import build as _build
            tb = (doc.data.get("field") or {}).get("text_block")
            hint = _build.shared_text_block_hint_for(cand, tb)
            if hint:
                notes = [fb.Problem(fb.WARN, hint)]
        except Exception:                                      # noqa: BLE001
            notes = []
        self._show_problems(fb.Verdict(fb.OK,
                            f"{member}: {site.label} → {self._logic_value_str(site, new)} (unsaved)"), notes)

    def _revert_logic_site(self, member, entry, tag, site):
        from .. import logic_edit as LE
        doc = self._doc(member)
        self._set_logic_edits(member, LE.upsert_edits(doc.data.get("logic_edit"), [],
                                                      drop=LE.site_footprint(site)))
        self._reconcile_logic_dirty(member)
        self._checkpoint(member, f"revert {site.group}", f"logic_n:{entry}:{tag}")
        self._mount_logic_node(member, entry, tag)

    def _set_logic_edits(self, member, cand):
        """Write the member's ``logic_edit`` list (or drop the key entirely when empty, so a fully-reverted
        field stays byte-identical to the donor and the toml has no empty ``[[logic_edit]]`` noise)."""
        doc = self._doc(member)
        if cand:
            doc.data["logic_edit"] = cand
        else:
            doc.data.pop("logic_edit", None)

    def _validate_logic_candidate(self, member, cand):
        """Dry-run ``cand`` against the member's LOCAL .eb/.mes (mirrors build._validate_logic_edits). Returns
        an error string, or None if every edit applies cleanly + the composed .eb lints clean."""
        from .. import logic_edit as LE
        from .. import eblint
        try:
            eb, _entries, lang_bodies = self._member_logic_inputs(member)
            errs = eblint.errors(eblint.lint_eb(LE.apply_logic_edits(eb, cand)))
            if errs:
                return f"composed .eb: {errs[0]}"            # EbIssue.__str__ (str+EbIssue would TypeError)
            for lang, body in lang_bodies.items():
                LE.apply_logic_text_edits(body, cand, lang)
        except LE.LogicEditError as ex:
            return str(ex)
        except Exception as ex:                                  # noqa: BLE001
            return f"{type(ex).__name__}: {ex}"
        return None

    def _reconcile_logic_dirty(self, member):
        """After a revert, drop the touch flag iff the doc is back to its saved baseline."""
        if member in self._docs and self._docs[member].data == self._clean.get(member):
            self._touched.discard(member)
        else:
            self._touched.add(member)
        self._refresh_dirty_marks()

    def _save_logic(self, member, entry, tag):
        """Persist the member's doc (its authored logic_edit list) to disk + clear the dot."""
        reason = protected_reason(self.member_paths[member])
        if reason:
            self._show_problems(fb.Verdict(fb.ERROR, "Can't save here"),
                                [fb.Problem(fb.ERROR, f"{reason}. Save a copy in a folder of your own.")])
            return
        try:
            self._doc(member).save()
        except Exception as e:                                   # noqa: BLE001
            self._show_problems(fb.Verdict(fb.ERROR, "Save failed"), [fb.Problem(fb.ERROR, str(e))])
            return
        self._mark_clean(member)
        self._checkpoint(member, "save logic edits", f"logic_n:{entry}:{tag}")
        self._mount_logic_node(member, entry, tag)          # re-render so the rows flip "(unsaved)" -> "(saved)"
        self._show_problems(fb.Verdict(fb.OK, f"Saved {member} · logic edits",
                                       f"wrote {self.member_paths[member].name}"), [])

    def _reset_logic(self, member, entry, tag):
        """Reset = discard ALL unsaved logic edits AND added effects on this field (restore the saved baseline)."""
        clean = self._clean.get(member, {})
        doc = self._doc(member)
        for key in ("logic_edit", "logic_add"):
            if key in clean:
                doc.data[key] = copy.deepcopy(clean[key])
            else:
                doc.data.pop(key, None)
        self._reconcile_logic_dirty(member)
        self._checkpoint(member, "reset logic edits", f"logic_n:{entry}:{tag}")
        self._mount_logic_node(member, entry, tag)

    # ---- [[logic_add]] authoring: length-changing effects (give item/gil, set flag, show line) ----
    def _routine_adds(self, member, entry, tag):
        """``[(list_index, add)]`` for the doc's ``[[logic_add]]`` entries that target this (entry, tag)."""
        out = []
        for i, a in enumerate(self._doc(member).data.get("logic_add") or []):
            if isinstance(a, dict) and a.get("entry") == entry and a.get("tag") == tag:
                out.append((i, a))
        return out

    def _effect_phrase(self, kind, add):
        """The 'what it does' phrase for an effect kind (give item/gil, set flag, show line) -- shared by the
        ``[[logic_add]]`` row label and the ``menu_row`` label (whose ``effect`` names the same payload)."""
        if kind == "give_item":
            from .. import items
            it = add.get("item")
            nm = items.name_of(it) if isinstance(it, int) else str(it)
            return f"give {nm} ×{add.get('count', 1)}"
        if kind == "give_gil":
            return f"give {add.get('amount')} gil"
        if kind == "set_flag":
            return f"set flag {add.get('flag')} = {add.get('value', 1)}"
        if kind == "show_line":
            return f'show "{self._short(add.get("message", ""))}"'
        return str(kind)

    def _logic_add_label(self, add):
        """A friendly one-line rendering of a ``[[logic_add]]`` (what it does + where it's inserted)."""
        from ..eb import disasm
        kind = add.get("kind")
        if kind == "menu_row":                                     # a new choice-menu row (no prepend/after place)
            eff = add.get("effect")
            extra = (f' + “{self._short(add.get("message"))}”'
                     if (add.get("message") and eff != "show_line") else "")
            return (f'menu row “{self._short(add.get("label", ""))}” → {self._effect_phrase(eff, add)}{extra} '
                    f'(txid {add.get("menu_txid")})')
        where = add.get("where", "prepend")
        place = ("at start" if where != "after"
                 else f"after {disasm.op_name(add.get('after_op'))} #{add.get('after_nth', 0)}")
        body = self._effect_phrase(kind, add)
        msg = add.get("message")
        extra = f' + “{self._short(msg)}”' if (msg and kind != "show_line") else ""
        return f"{body}{extra} ({place})"

    @staticmethod
    def _short(s, n=40):
        s = " ".join(str(s or "").split())
        return s if len(s) <= n else s[:n] + "…"

    def _mount_logic_add_section(self, member, entry, tag, eb):
        """The ``[[logic_add]]`` block for this routine: a header + 'Add effect…' button, then each existing
        added effect (with Remove). Adds are length-CHANGING (give item/gil, set flag, show line), guarded so
        they fire once; the read-only tree above still shows the donor's original bytecode."""
        adds = self._routine_adds(member, entry, tag)
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 12, 0, 0)
        title = QLabel(f"Added effects{f' · {len(adds)}' if adds else ''}")
        title.setStyleSheet("font-weight:600;")
        hdr.addWidget(title)
        hdr.addStretch(1)
        addbtn = QPushButton("Add effect…")
        addbtn.setToolTip("Insert a give-item / give-gil / set-flag / show-line effect into this routine "
                          "(a length-changing [[logic_add]], guarded so it fires once)")
        addbtn.clicked.connect(lambda _=False: self._add_logic_effect(member, entry, tag, eb))
        hdr.addWidget(addbtn)
        if self._menu_txid_hint(eb, entry, tag) is not None:    # only where this routine HAS a choice menu
            rowbtn = QPushButton("Add menu row…")
            rowbtn.setToolTip("Add a NEW selectable row to the choice menu in this routine (a [[logic_add]] "
                              "menu_row: the row label + its dispatch arm + the availability mask, at once)")
            rowbtn.clicked.connect(lambda _=False: self._add_menu_row(member, entry, tag, eb))
            hdr.addWidget(rowbtn)
        hw = QWidget()
        hw.setLayout(hdr)
        self.doc_host_lay.addWidget(hw)
        for idx, add in adds:
            self.doc_host_lay.addWidget(self._logic_add_row(member, entry, tag, idx, add))

    def _logic_add_row(self, member, entry, tag, idx, add):
        """One added-effect row: 'give Phoenix Down ×1 (after AddItem #0)  (unsaved)'  [Remove]."""
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 2, 0, 2)
        # POSITION-aware: this exact add is "(saved)" iff the saved baseline holds an equal dict at the SAME
        # list index (a plain `in` would mislabel a value-identical NEW duplicate as already-saved).
        baseline = (self._clean.get(member) or {}).get("logic_add") or []
        saved = idx < len(baseline) and baseline[idx] == add
        state = ("saved", self.pal["muted"]) if saved else ("unsaved", self.pal["warn"])
        lbl = QLabel(f"{_esc(self._logic_add_label(add))}  "
                     f"<span style='color:{state[1]};'>({state[0]})</span>")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        h.addWidget(lbl, 1)
        rm = QPushButton("Remove")
        rm.clicked.connect(lambda _=False, i=idx: self._revert_logic_add(member, entry, tag, i))
        h.addWidget(rm)
        return w

    def _add_logic_effect(self, member, entry, tag, eb):
        reason = protected_reason(self.member_paths[member])
        if reason:
            self._show_problems(fb.Verdict(fb.ERROR, "Can't author here"),
                                [fb.Problem(fb.ERROR, f"{reason}. Save a copy in a folder of your own.")])
            return
        add = self._logic_add_dialog(member, entry, tag, eb)
        if add is not None:
            self._commit_logic_add(member, entry, tag, add)

    def _routine_anchors(self, eb, entry, tag):
        """``[(after_op, after_nth, label)]`` for each instruction in the routine -- the 'after' placement
        choices (anchor the insert after the after_nth-th occurrence of after_op)."""
        from ..eb.model import EbScript
        from ..eb import disasm
        try:
            s = EbScript.from_bytes(eb)
            e = s.entry(entry)
            f = None if e.empty else e.func_by_tag(tag)
        except Exception:                                          # noqa: BLE001
            return []
        if f is None:
            return []
        out, seen = [], {}
        for k, i in enumerate(s.instrs(f)):
            nth = seen.get(i.op, 0)
            seen[i.op] = nth + 1
            arg = ""
            try:
                if i.imm(0) is not None:
                    arg = f"({i.imm(0)})"
            except Exception:                                      # noqa: BLE001
                arg = ""
            out.append((i.op, nth, f"#{k}: {disasm.op_name(i.op)}{arg}"))
        return out

    def _logic_add_dialog(self, member, entry, tag, eb):
        """Author one ``[[logic_add]]`` for this routine: pick a kind (give item/gil, set flag, show line), a
        placement (at start, or after an instruction), and an optional/required message. Returns the add dict
        or None. The heavy validation happens at commit (build.dry_run_logic_adds)."""
        from .. import flags as _flags
        dlg = QDialog(self)
        dlg.setWindowTitle("Add effect")
        outer = QVBoxLayout(dlg)
        form = QFormLayout()
        outer.addLayout(form)

        kind = QComboBox()
        for label, data in (("Give item", "give_item"), ("Give gil", "give_gil"),
                            ("Set story flag", "set_flag"), ("Show line", "show_line")):
            kind.addItem(label, data)
        form.addRow("Effect", kind)

        stack = QStackedWidget()
        gi = QWidget(); gif = QFormLayout(gi); gif.setContentsMargins(0, 0, 0, 0)
        item_ed = QLineEdit("Potion"); gi_count = QLineEdit("1")
        gif.addRow("Item", item_ed); gif.addRow("Count", gi_count)
        gi_hint = self._muted_label(""); gif.addRow(gi_hint)
        gg = QWidget(); ggf = QFormLayout(gg); ggf.setContentsMargins(0, 0, 0, 0)
        gil_ed = QLineEdit("1000"); ggf.addRow("Amount", gil_ed)
        sf = QWidget(); sff = QFormLayout(sf); sff.setContentsMargins(0, 0, 0, 0)
        flag_ed = QLineEdit(str(_flags.FIRST_SAFE_FLAG)); val_ed = QLineEdit("1")
        sff.addRow("Flag index", flag_ed); sff.addRow("Value (0/1)", val_ed)
        sff.addRow(self._muted_label(f"An explicit safe-band index ≥ {_flags.FIRST_SAFE_FLAG}."))
        sl = QWidget(); slf = QFormLayout(sl); slf.setContentsMargins(0, 0, 0, 0)
        slf.addRow(self._muted_label("The message below IS the effect (a dialogue window)."))
        for w in (gi, gg, sf, sl):
            stack.addWidget(w)
        form.addRow(stack)

        msg_ed = QPlainTextEdit("")
        msg_ed.setMinimumSize(QSize(360, 60))
        msg_lbl = QLabel("Message")
        form.addRow(msg_lbl, msg_ed)
        msg_hint = self._muted_label("")
        form.addRow(msg_hint)

        place = QComboBox()
        place.addItem("At start of routine", "prepend")
        place.addItem("After an instruction…", "after")
        form.addRow("Where", place)
        anchors = self._routine_anchors(eb, entry, tag)
        anchor = QComboBox()
        for op, nth, label in anchors:
            anchor.addItem(label, (op, nth))
        anchor_lbl = QLabel("Anchor")
        form.addRow(anchor_lbl, anchor)

        def sync(*_):
            k = kind.currentData()
            stack.setCurrentIndex({"give_item": 0, "give_gil": 1, "set_flag": 2, "show_line": 3}[k])
            is_show = (k == "show_line")
            msg_lbl.setText("Message (required)" if is_show else "Message")
            after = (place.currentData() == "after")
            anchor.setVisible(after and bool(anchors))
            anchor_lbl.setVisible(after and bool(anchors))
            if after and not anchors:
                msg_hint.setText("⚠ this routine has no instructions to anchor after — use 'At start'.")
            elif is_show:
                msg_hint.setText("Shown in a dialogue window when this fires (once-guarded).")
            else:
                msg_hint.setText("Optional — pops a “Received…” style window when the effect fires.")

        def on_item(*_):
            from .. import items
            t = item_ed.text().strip()
            try:
                v = int(t) if t.isdigit() else items.resolve(t)
                gi_hint.setText(f"→ {items.name_of(v) or ('item #' + str(v))}  (#{v})")
            except ValueError as ex:
                gi_hint.setText(f"⚠ {ex}")

        kind.currentIndexChanged.connect(sync)
        place.currentIndexChanged.connect(sync)
        item_ed.textChanged.connect(on_item)
        on_item()
        sync()
        outer.addWidget(self._ok_cancel(dlg))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        try:
            return self._build_logic_add(kind.currentData(), entry, tag, place.currentData(),
                                         anchor.currentData() if anchors else None, anchors,
                                         item_ed.text(), gi_count.text(), gil_ed.text(),
                                         flag_ed.text(), val_ed.text(), msg_ed.toPlainText())
        except ValueError as ex:
            self._show_problems(fb.Verdict(fb.ERROR, "Bad value"), [fb.Problem(fb.ERROR, str(ex))])
            return None

    def _build_logic_add(self, kind, entry, tag, placement, anchor_data, anchors,
                         item_text, count_text, gil_text, flag_text, val_text, message):
        """Assemble + light-validate a ``[[logic_add]]`` dict from the dialog inputs (raises ValueError on a
        bad field; the full build dry-run runs at commit)."""
        from .. import items
        add = {"kind": kind, "entry": entry, "tag": tag}
        if placement == "after":
            if not anchors:
                raise ValueError("no instruction to anchor after — use 'At start of routine'")
            op, nth = anchor_data
            add["where"] = "after"
            add["after_op"] = int(op)
            add["after_nth"] = int(nth)
        if kind == "give_item":
            t = item_text.strip()
            (int(t) if t.isdigit() else items.resolve(t))          # validate it resolves
            add["item"] = int(t) if t.isdigit() else t
            cnt = self._pos_int(count_text, "count", 1, 255)
            if cnt != 1:
                add["count"] = cnt
        elif kind == "give_gil":
            add["amount"] = self._pos_int(gil_text, "amount", 1, 9_999_999)
        elif kind == "set_flag":
            add["flag"] = self._pos_int(flag_text, "flag index", 0, 65535)
            v = self._pos_int(val_text, "value", 0, 1) if (val_text or "").strip() else 1
            if v != 1:
                add["value"] = v
        msg = (message or "").strip()
        if kind == "show_line":
            if not msg:
                raise ValueError("a show-line needs a message")
            add["message"] = msg
        elif msg:
            add["message"] = msg
        return add

    @staticmethod
    def _pos_int(text, label, lo, hi):
        try:
            v = int((text or "").strip())                       # int() rejects "--5"/"5-3"/"" cleanly
        except (TypeError, ValueError):
            raise ValueError(f"{label} must be a whole number")
        if not (lo <= v <= hi):
            raise ValueError(f"{label} must be {lo}–{hi}")
        return v

    # ---- menu_row authoring: a NEW selectable+labelled choice-menu row ------------------------------
    def _menu_txid_hint(self, eb, entry, tag):
        """Best-effort: the ``.mes`` txid of a choice menu in this routine (the WindowSync just before a base-0
        contiguous GetChoose switch), to PRE-FILL the dialog. None if the routine has no such menu."""
        from ..eb import disasm
        from ..eb.model import EbScript
        window_ops = {0x1F: 2, 0x20: 2, 0x95: 3, 0x96: 3}
        try:
            s = EbScript.from_bytes(eb)
            e = s.entry(entry)
            f = None if e.empty else e.func_by_tag(tag)
            if f is None:
                return None
            ins = list(s.instrs(f))
        except Exception:                                          # noqa: BLE001
            return None
        for sw in ins:
            if sw.op not in (0x0B, 0x0D):
                continue
            si = disasm.decode_switch(sw)
            if si is None or si.base != 0:
                continue
            wins = [i for i in ins if i.op in window_ops and i.off < sw.off]
            if wins:
                t = wins[-1].imm(window_ops[wins[-1].op])
                if t is not None:
                    return t
        return None

    def _build_menu_row(self, entry, tag, menu_txid_text, label, effect_kind,
                        item_text, count_text, gil_text, flag_text, val_text, message):
        """Assemble a ``[[logic_add]] kind="menu_row"`` dict from the dialog inputs (raises ValueError on a bad
        field; the full build dry-run runs at commit). Reuses :meth:`_build_logic_add` for the row's effect
        payload, then drops the prepend/after placement keys a dispatch row doesn't use."""
        lbl = (label or "").strip()
        if not lbl:
            raise ValueError("a menu row needs a label (the option text shown in the menu)")
        if "\n" in lbl:
            raise ValueError("a menu row label can't contain a newline")
        txid = self._pos_int(menu_txid_text, "menu text id", 0, 65535)
        eff = self._build_logic_add(effect_kind, entry, tag, "prepend", None, [],
                                    item_text, count_text, gil_text, flag_text, val_text, message)
        payload = {k: v for k, v in eff.items() if k not in ("kind", "entry", "tag")}
        return {"kind": "menu_row", "entry": entry, "tag": tag, "menu_txid": txid,
                "label": lbl, "effect": effect_kind, **payload}

    def _add_menu_row(self, member, entry, tag, eb):
        reason = protected_reason(self.member_paths[member])
        if reason:
            self._show_problems(fb.Verdict(fb.ERROR, "Can't author here"),
                                [fb.Problem(fb.ERROR, f"{reason}. Save a copy in a folder of your own.")])
            return
        add = self._menu_row_dialog(member, entry, tag, eb)
        if add is not None:
            self._commit_logic_add(member, entry, tag, add)

    def _menu_row_dialog(self, member, entry, tag, eb):
        """Author a ``[[logic_add]] kind="menu_row"``: the menu's text id + the new row label, the row's effect
        (give item/gil, set flag, show line), and an optional announce. Returns the add dict or None. The heavy
        validation (1:1 menu, [PCHM] reject, row alignment) happens at commit (build.dry_run_logic_adds)."""
        from .. import flags as _flags
        dlg = QDialog(self)
        dlg.setWindowTitle("Add menu row")
        outer = QVBoxLayout(dlg)
        form = QFormLayout()
        outer.addLayout(form)
        form.addRow(self._muted_label(
            "Adds a NEW selectable row to an existing choice menu in this routine (a base-0 contiguous GetChoose "
            "switch + a [CHOO] row list). Picking the row runs the effect below; the row appears last."))

        hint = self._menu_txid_hint(eb, entry, tag)
        txid_ed = QLineEdit("" if hint is None else str(hint))
        form.addRow("Menu text id", txid_ed)
        form.addRow(self._muted_label("The .mes entry holding the menu's prompt + rows (the WindowSync txid)"
                                      + ("." if hint is None else " — pre-filled from this routine's menu.")))
        label_ed = QLineEdit("Get a free Potion!")
        form.addRow("Row label", label_ed)

        kind = QComboBox()
        for label, data in (("Give item", "give_item"), ("Give gil", "give_gil"),
                            ("Set story flag", "set_flag"), ("Show line", "show_line")):
            kind.addItem(label, data)
        form.addRow("When picked", kind)

        stack = QStackedWidget()
        gi = QWidget(); gif = QFormLayout(gi); gif.setContentsMargins(0, 0, 0, 0)
        item_ed = QLineEdit("Potion"); count_ed = QLineEdit("1")
        gif.addRow("Item", item_ed); gif.addRow("Count", count_ed)
        gi_hint = self._muted_label(""); gif.addRow(gi_hint)
        gg = QWidget(); ggf = QFormLayout(gg); ggf.setContentsMargins(0, 0, 0, 0)
        gil_ed = QLineEdit("1000"); ggf.addRow("Amount", gil_ed)
        sf = QWidget(); sff = QFormLayout(sf); sff.setContentsMargins(0, 0, 0, 0)
        flag_ed = QLineEdit(str(_flags.FIRST_SAFE_FLAG)); val_ed = QLineEdit("1")
        sff.addRow("Flag index", flag_ed); sff.addRow("Value (0/1)", val_ed)
        sff.addRow(self._muted_label(f"An explicit safe-band index ≥ {_flags.FIRST_SAFE_FLAG}."))
        sl = QWidget(); slf = QFormLayout(sl); slf.setContentsMargins(0, 0, 0, 0)
        slf.addRow(self._muted_label("The message below IS the effect (a dialogue window)."))
        for w in (gi, gg, sf, sl):
            stack.addWidget(w)
        form.addRow(stack)

        msg_ed = QPlainTextEdit("")
        msg_ed.setMinimumSize(QSize(360, 56))
        msg_lbl = QLabel("Message")
        form.addRow(msg_lbl, msg_ed)
        msg_hint = self._muted_label("")
        form.addRow(msg_hint)

        def sync(*_):
            k = kind.currentData()
            stack.setCurrentIndex({"give_item": 0, "give_gil": 1, "set_flag": 2, "show_line": 3}[k])
            msg_lbl.setText("Message (required)" if k == "show_line" else "Message")
            msg_hint.setText("Shown in a dialogue window when this row is picked (once-guarded)."
                             if k == "show_line"
                             else "Optional — pops a “Received…” style window when the row's effect fires.")

        def on_item(*_):
            from .. import items
            t = item_ed.text().strip()
            try:
                v = int(t) if t.isdigit() else items.resolve(t)
                gi_hint.setText(f"→ {items.name_of(v) or ('item #' + str(v))}  (#{v})")
            except ValueError as ex:
                gi_hint.setText(f"⚠ {ex}")

        kind.currentIndexChanged.connect(sync)
        item_ed.textChanged.connect(on_item)
        on_item()
        sync()
        outer.addWidget(self._ok_cancel(dlg))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        try:
            return self._build_menu_row(entry, tag, txid_ed.text(), label_ed.text(), kind.currentData(),
                                        item_ed.text(), count_ed.text(), gil_ed.text(),
                                        flag_ed.text(), val_ed.text(), msg_ed.toPlainText())
        except ValueError as ex:
            self._show_problems(fb.Verdict(fb.ERROR, "Bad value"), [fb.Problem(fb.ERROR, str(ex))])
            return None

    def _set_logic_adds(self, member, cand):
        """Write the member's ``logic_add`` list (or drop the key when empty, so a fully-reverted field stays
        byte-identical to the donor)."""
        doc = self._doc(member)
        if cand:
            doc.data["logic_add"] = cand
        else:
            doc.data.pop("logic_add", None)

    def _validate_logic_add_candidate(self, member, cand_adds):
        """Dry-run ``cand_adds`` (+ the member's CURRENT, possibly-unsaved logic_edit) against its LOCAL
        .eb/.mes via build.dry_run_logic_adds -- the EXACT build path. Returns an error string, or None."""
        from .. import build as _build
        try:
            proj = _build.FieldProject.load(self.member_paths[member])
        except Exception as ex:                                    # noqa: BLE001
            return f"{type(ex).__name__}: {ex}"
        proj.raw["logic_edit"] = self._doc(member).data.get("logic_edit") or []
        proj.raw["logic_add"] = cand_adds
        return _build.dry_run_logic_adds(proj)

    def _commit_logic_add(self, member, entry, tag, add):
        """Append a new ``[[logic_add]]`` after a clean offline dry-run (build's verbatim add pass). On a
        validation error nothing is written + the reason is shown."""
        doc = self._doc(member)
        cand = (doc.data.get("logic_add") or []) + [add]
        err = self._validate_logic_add_candidate(member, cand)
        if err:
            self._show_problems(fb.Verdict(fb.ERROR, "Effect not added — it wouldn't build"),
                                [fb.Problem(fb.ERROR, err)])
            return
        self._set_logic_adds(member, cand)
        self._touch(member)
        self._checkpoint(member, f"add {add.get('kind')}", f"logic_n:{entry}:{tag}")
        self._mount_logic_node(member, entry, tag)
        self._show_problems(fb.Verdict(fb.OK, f"{member}: + {self._logic_add_label(add)} (unsaved)"), [])

    def _revert_logic_add(self, member, entry, tag, idx):
        doc = self._doc(member)
        lst = list(doc.data.get("logic_add") or [])
        if 0 <= idx < len(lst):
            lst.pop(idx)
        self._set_logic_adds(member, lst)
        self._reconcile_logic_dirty(member)
        self._checkpoint(member, "remove effect", f"logic_n:{entry}:{tag}")
        self._mount_logic_node(member, entry, tag)

    # ---- tree right-click / Delete-key: Add to a group, Delete an entity, Remove a single section ----
    def _context_actions(self, item):
        """``[(label, callback), ...]`` for a right-click / Delete on a tree node: add to a list group,
        delete a list entity, or remove an existing single section. Empty for field / camera / an absent
        single (nothing to do there)."""
        p = self._payload(item)
        if p and p[0] in ("jset", "journey") and self.manifest is not None:
            acts = [("Add journey…", self.on_add_journey_row)]   # the hub root: add a menu row (selector builder)
            if self._has_multi_arc():                            # a multi-campaign arc -> grow it region-by-region
                acts.append(("Add region to arc…", self.on_add_region_to_arc))
            if p[0] == "journey" and ":" in (p[2] or ""):        # a journey row: seed it + offer Remove (Delete-key)
                jid = p[2].split(":", 1)[1]
                acts.append(("Set base party / seed…", lambda j=jid: self.on_set_journey_seed(j)))
                acts.append(("Set tuning (player stats)…", lambda j=jid: self.on_set_journey_tuning(j)))
                acts.append((f"Remove journey '{jid}'", lambda j=jid: self.on_remove_journey_row(j)))
            return acts
        if p and p[0] == "campaign" and self.plan is not None and self.campaign_path is not None:
            return [("Add field…", self.on_add_field)]      # the campaign root: scaffold a new member
        fa = self._ancestor_field(item)
        if not p or fa is None:
            return []
        kind, _label, key = p
        member = self._payload(fa)[1]
        if kind == "group" and key in _LIST_DEFAULTS:                        # NPCs (n) -> Add NPC
            sing = _LIST_SINGULAR.get(key, key)
            return [(f"Add {sing}", lambda: self._add_list_item(member, key))]
        if kind == "object" and ":" in key:                                  # npc:2 / choice:0 -> Delete
            section, idx = key.split(":")
            sing = _LIST_SINGULAR.get(section, section)
            return [(f"Delete {sing}",
                     lambda: self._delete_object(member, section, single=False, idx=int(idx), label=sing))]
        if kind == "object" and key in dict(_SINGLE) and key in self._doc(member).data:  # an existing single
            return [(f"Remove {key}", lambda: self._delete_object(member, key, single=True, label=key))]
        return []

    def _tree_menu(self, pos):
        item = self.tree.itemAt(pos)
        actions = self._context_actions(item) if item is not None else []
        if not actions:
            return
        menu = QMenu(self)
        for label, cb in actions:
            menu.addAction(label, cb)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _delete_selected(self):
        """Delete-key on the focused tree: run the selected node's Delete/Remove action (if any)."""
        item = self.tree.currentItem()
        if item is None:
            return
        for label, cb in self._context_actions(item):
            if label.startswith(("Delete", "Remove")):
                cb()
                return

    def _add_list_item(self, member, kind):
        """Append a default entity to ``member``'s ``kind`` list, refresh the tree, and open the new item's
        editor (so you land straight in the form to fill it in)."""
        if not self._commit_active_ck():             # fold+checkpoint any pending edit first (its own step);
            return                                   # an invalid open form blocks adding (fix it first)
        doc = self._doc(member)
        lst = doc.data.setdefault(kind, [])
        lst.append(copy.deepcopy(_LIST_DEFAULTS[kind]))
        idx = len(lst) - 1
        self._touch(member)                           # the new default entity is an unsaved change
        self._checkpoint(member, f"add {_LIST_SINGULAR.get(kind, kind)}", f"{kind}:{idx}")  # the add = one step
        self.tree.blockSignals(True)                 # rebuild the object subtree without spurious selections
        self._refresh_objects(member)
        self.tree.blockSignals(False)
        self._select_object(member, f"{kind}:{idx}")  # fires _on_select -> mounts the new item's form (no-op fold)
        self.tabs.setCurrentWidget(self.doc_scroll)   # adding is an explicit edit -> show the Editor

    def _refresh_objects(self, member):
        """Rebuild a member's object subtree in place (after an add) so the new item + updated count show."""
        mi = getattr(self, "_member_items", {}).get(member)
        if mi is None:
            return
        mi.takeChildren()
        self._load_objects(mi)
        mi.setExpanded(True)

    def _object_item(self, member, key, kind="object"):
        """The QTreeWidgetItem of ``kind`` ('object'|'group') with ``key`` under ``member``, or None (walks
        the member's loaded subtree). Locates a row by key -- never assume it's the selection."""
        mi = getattr(self, "_member_items", {}).get(member)
        if mi is None:
            return None
        stack = [mi.child(i) for i in range(mi.childCount())]
        while stack:
            it = stack.pop()
            p = self._payload(it)
            if p and p[0] == kind and p[2] == key:
                return it
            stack += [it.child(i) for i in range(it.childCount())]
        return None

    def _select_object(self, member, key):
        """Select the object node ``key`` (e.g. 'npc:2') under ``member``."""
        it = self._object_item(member, key)
        if it is not None:
            self.tree.setCurrentItem(it)
            self.tree.scrollToItem(it)

    def _refresh_single_dim(self, member, section):
        """Re-colour a single section's tree node after a save: dim while the section is ABSENT from the doc,
        normal once it's authored. Saving a single edits the doc in place WITHOUT rebuilding the subtree
        (unlike delete -> _refresh_objects), so its node would otherwise keep the stale 'absent' grey."""
        it = self._object_item(member, section)
        if it is None:
            return
        present = section in self._doc(member).data
        it.setForeground(0, QBrush(QColor(self.pal["text" if present else "muted"])))

    def _confirm(self, title, text):
        """A yes/no confirm (the smoke stubs this). Destructive actions gate on it."""
        return QMessageBox.question(self, title, text) == QMessageBox.StandardButton.Yes

    def _delete_object(self, member, section, *, single, idx=None, label="item"):
        """Remove a list entity (``single=False``, by ``idx``) or a whole single section (``single=True``)
        from ``member``, write the file, refresh the tree, and land on the parent group/section."""
        if not self._confirm(f"Delete {label}",
                             f"Delete this {label} from {member}? This writes {self.member_paths[member].name}."):
            return
        reason = protected_reason(self.member_paths[member])      # don't delete out of a bundled/golden file
        if reason:
            self._show_problems(fb.Verdict(fb.ERROR, "Can't delete here"),
                                [fb.Problem(fb.ERROR, f"{reason}. Edit a copy in a folder of your own.")])
            return
        doc = self._doc(member)
        if single:
            doc.data.pop(section, None)
        else:
            lst = doc.data.get(section, [])
            if idx is None or idx >= len(lst):
                return
            lst.pop(idx)
            if not lst:
                doc.data.pop(section, None)                        # drop an emptied list (no bare [[npc]])
        try:
            doc.save()
        except Exception as e:                                     # noqa: BLE001
            self._show_problems(fb.Verdict(fb.ERROR, "Delete failed"), [fb.Problem(fb.ERROR, str(e))])
            return
        self._mark_clean(member)
        self._checkpoint(member, f"delete {label}", section)      # the delete is one undo step
        self._save_ctx = None                                     # the deleted thing's form is gone
        self.tree.blockSignals(True)
        self._refresh_objects(member)
        self.tree.blockSignals(False)
        # land on the parent: the list's group (updated count) or the single's (now-dim) section node
        node = self._object_item(member, section, kind="group") if not single \
            else self._object_item(member, section)
        if node is not None:
            self.tree.setCurrentItem(node)                        # fires _on_select -> mounts that view
        else:
            self._doc_placeholder(f"Deleted {label}.")
        self._show_problems(fb.Verdict(fb.OK, f"Deleted {label} from {member}",
                                       f"wrote {self.member_paths[member].name}"), [])

    def _pick(self, catalog, current, want_id=False):
        """``build_form``'s picker: open the Qt catalog picker over the open campaign's context. ``want_id``
        returns the picked entry's numeric id (for an INT field like the encounter battle scene)."""
        return pick_catalog(self, catalog, current, self.plan, self.pal, want_id=want_id)

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
        tab = (entity.get("name") if not single else None) or _LIST_SINGULAR.get(section) or section.title()
        self._set_editor_tab(str(tab)[:24])
        form, getters = build_form(spec, forms.entity_to_values(spec, entity), self.pal, pick=self._pick,
                                   wrap_width=self._wrap_width(member), on_change=lambda m=member: self._on_form_change(m))
        self.doc_host_lay.addWidget(form)
        self._save_ctx = {"member": member, "key": key, "spec": spec, "getters": getters,
                          "single": single, "section": section, "idx": idx}
        delete = None
        if not single:                                         # a list entity (npc/gateway/event/marker)
            lbl = _LIST_SINGULAR.get(section, section)
            delete = (f"Delete {lbl}",
                      lambda: self._delete_object(member, section, single=False, idx=idx, label=lbl))
        elif section != "field" and section in self._doc(member).data:   # an OPTIONAL single that exists
            delete = (f"Remove {section}",
                      lambda: self._delete_object(member, section, single=True, label=section))
        self._add_save(self._save, delete)

    def _add_save(self, handler, delete=None):
        self._active_save = handler                            # Ctrl-S saves the mounted form
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        save = QPushButton("Save")
        save.setObjectName("accent")
        save.clicked.connect(lambda _=False: handler())
        row.addWidget(save)
        self._save_btn = save                                  # so it can grey out when there's nothing to save
        reset = QPushButton("Reset")
        reset.setToolTip("Discard this form's unsaved changes (revert to the last save)")
        reset.clicked.connect(lambda _=False: self._reset_active())
        row.addWidget(reset)
        self._reset_btn = reset
        if delete is not None:                                 # (label, callback) -> a Delete/Remove button
            db = QPushButton(delete[0])
            db.clicked.connect(lambda _=False, cb=delete[1]: cb())
            row.addWidget(db)
        row.addStretch(1)
        holder = QWidget()
        holder.setLayout(row)
        self.doc_host_lay.addWidget(holder)
        self.doc_host_lay.addStretch(1)
        self._refresh_save_button()                            # initial enabled/grey state
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
        if single and section not in doc.data and not entity:
            # Saving an EMPTY, not-yet-created single section (e.g. an untouched Cutscene/Music) -> nothing
            # to write; don't materialize an empty [section]. (Cutscene steps add via ensure_cs first.)
            self._show_problems(fb.Verdict(fb.OK, f"{member} · {key or section} — nothing to save (empty)"), [])
            return True
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
        self._checkpoint(member, f"edit {key or section}", key or section)   # the saved fold is one undo step
        self._show_problems(fb.Verdict(fb.OK, f"Saved {member} · {key or section}",
                                       f"wrote {self.member_paths[member].name}"), [])
        if single and section in dict(_SINGLE):     # un-dim a just-authored optional single's tree node
            self._refresh_single_dim(member, section)
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
            if ctx["section"] not in doc.data and not entity:
                return True                # untouched/empty new single section -> don't materialize it (dirty)
            target = doc.data.setdefault(ctx["section"], {})
        else:
            lst = doc.data.get(ctx["section"], []) or []
            if ctx["idx"] is None or ctx["idx"] >= len(lst):
                return True
            target = lst[ctx["idx"]]
        # No-op fold guard: if the form's entity matches the target's NORMALIZED content, writing would only
        # drop default-equal BOOLs (build_entity omits e.g. once=true) and falsely dirty a merely-VIEWED node.
        if forms.build_entity(ctx["spec"], forms.entity_to_values(ctx["spec"], target)) == entity:
            return True
        for f in ctx["spec"]:
            target.pop(f.key, None)
        target.update(entity)
        return True

    def _ensure_saved(self) -> bool:
        """Commit the active form + write its doc to disk so Check validates the CURRENT edits, not stale
        bytes (parity with the tkinter editor's _ensure_saved). Skips a protected file."""
        if not self._commit_active_ck():
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
        self._commit_active_ck()                   # the in-progress form's edits count toward dirty (+ checkpoint)
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
        # Don't materialize an empty [cutscene] just by BROWSING here -- that would mark the field dirty.
        # Create it lazily: on the first added step (ensure_cs) or an explicit Save (_commit's guard).
        def cs():
            return doc.data.get("cutscene") or {}

        def ensure_cs():
            c = doc.data.setdefault("cutscene", {})    # materialize on a real edit (add a step)
            c.setdefault("steps", [])
            return c

        def steps():
            return cs().get("steps", [])
        self._clear_doc()
        self._header(f"{member}  ·  cutscene", forms.SECTION_HELP.get("cutscene"))
        self._set_editor_tab("Cutscene")
        form, getters = build_form(forms.CUTSCENE_SPEC, forms.entity_to_values(forms.CUTSCENE_SPEC, cs()),
                                   self.pal, pick=self._pick, wrap_width=self._wrap_width(member),
                                   on_change=lambda m=member: self._on_form_change(m))
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
        # the 'say' step is dialogue -> a multi-line box (Enter / typed \n = an in-window line break);
        # every other step is a short single value -> a line edit. Only one shows at a time.
        value_line = QLineEdit()
        value_text = QPlainTextEdit()
        value_text.setTabChangesFocus(True)
        value_text.setFixedHeight(64)
        value_text.setToolTip("Line break: press Enter, or type \\n.   New window: type [PAGE].")
        value_text.setVisible(False)
        hint = QLabel("")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{self.pal['muted']};font-size:11px;")
        sv.addWidget(QLabel("Type:"))
        sv.addWidget(type_combo)
        sv.addWidget(QLabel("Value:"))
        sv.addWidget(value_line)
        sv.addWidget(value_text)
        sv.addWidget(hint)

        def is_say():
            return type_combo.currentData() == "say"

        def value_get():
            return value_text.toPlainText().replace("\\n", "\n") if is_say() else value_line.text()

        def value_set(s):
            (value_text.setPlainText if is_say() else value_line.setText)(s)

        def swap_value_widget():
            """Show the multi-line box for 'say', the line edit otherwise; carry the typed text across."""
            say = is_say()
            if say and not value_text.isVisible():
                value_text.setPlainText(value_line.text())
            elif not say and value_text.isVisible():
                value_line.setText(value_text.toPlainText().replace("\n", " "))
            value_text.setVisible(say)
            value_line.setVisible(not say)

        def reload_steps(select=None):
            steps_list.clear()
            for st in steps():
                steps_list.addItem(forms.step_summary(st))
            if select is not None and 0 <= select < steps_list.count():
                steps_list.setCurrentRow(select)

        def on_type(_i=0):
            hint.setText(forms.STEP_HELP.get(type_combo.currentData(), ""))
            swap_value_widget()
        type_combo.currentIndexChanged.connect(on_type)
        on_type()                                  # initialise hint + the right value widget (default = say)

        def on_select(r):
            s = steps()
            if 0 <= r < len(s):
                st = s[r]
                k = forms.step_key(st)
                if k in forms.STEP_KIND:
                    type_combo.setCurrentIndex(list(forms.STEP_KIND).index(k))   # fires on_type -> swaps widget
                value_set(forms.step_value_text(st))
        steps_list.currentRowChanged.connect(on_select)

        def add_update():
            try:
                step = forms.make_step(type_combo.currentData(), value_get())
            except ValueError as e:
                self._show_problems(fb.Verdict(fb.ERROR, "Bad step"), [fb.Problem(fb.ERROR, str(e))])
                return
            st = ensure_cs()["steps"]                  # materialize [cutscene] now that there's real content
            r = steps_list.currentRow()
            if 0 <= r < len(st) and forms.step_key(st[r]) == forms.step_key(step):
                st[r] = step
            else:
                st.append(step)
                r = len(st) - 1
            reload_steps(r)
            self._touch(member)
            self._checkpoint(member, "edit cutscene step", "cutscene")

        def remove():
            s = steps()
            r = steps_list.currentRow()
            if 0 <= r < len(s):
                s.pop(r)
                reload_steps()
                self._touch(member)
                self._checkpoint(member, "remove cutscene step", "cutscene")

        def move(d):
            s = steps()
            r = steps_list.currentRow()
            j = r + d
            if 0 <= r < len(s) and 0 <= j < len(s):
                s[r], s[j] = s[j], s[r]
                reload_steps(j)
                self._touch(member)
                self._checkpoint(member, "reorder cutscene steps", "cutscene")

        sv.addWidget(self._list_buttons([("Add / Update", add_update), ("Remove", remove),
                                         ("Up", lambda: move(-1)), ("Down", lambda: move(1))]))
        sv.addStretch(1)
        row.addWidget(side)
        self.doc_host_lay.addWidget(body)
        reload_steps()
        on_type()
        self._save_ctx = {"member": member, "key": "cutscene", "spec": forms.CUTSCENE_SPEC,
                          "getters": getters, "single": True, "section": "cutscene", "idx": None}
        delete = (("Remove cutscene", lambda: self._delete_object(member, "cutscene", single=True,
                                                                  label="cutscene"))
                  if "cutscene" in doc.data else None)         # only when it actually exists (lazy)
        self._add_save(
            lambda: self._commit(member, "cutscene", forms.CUTSCENE_SPEC, getters, single=True), delete)

    def _mount_choice(self, member, idx):
        doc = self._doc(member)
        lst = doc.data.get("choice", [])
        if idx >= len(lst):
            self._doc_placeholder("choice not found")
            return
        ch = lst[idx]
        # Don't materialize an empty `options` just by BROWSING -- that would dirty the field with no edit
        # (mirrors _mount_cutscene's ensure_cs). Read via opts(); the closures that mutate call ensure_opts().
        def opts():
            return ch.get("options") or []

        def ensure_opts():
            return ch.setdefault("options", [])
        self._clear_doc()
        self._header(f"{member}  ·  choice[{idx}]", forms.SECTION_HELP.get("choice"))
        self._set_editor_tab(f"Choice {idx + 1}")
        form, getters = build_form(forms.CHOICE_SPEC, forms.entity_to_values(forms.CHOICE_SPEC, ch),
                                   self.pal, pick=self._pick, wrap_width=self._wrap_width(member),
                                   on_change=lambda m=member: self._on_form_change(m))
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
            for o in opts():
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
                              self.pal, pick=self._pick, wrap_width=self._wrap_width(member),
                              on_change=lambda m=member: self._on_form_change(m))
            opt_lay.addWidget(f)
            st["getters"] = g

        def on_select(r):
            if 0 <= r < len(opts()):
                show_opt(opts()[r])
        opts_list.currentRowChanged.connect(on_select)

        def add_new():
            ensure_opts().append({"text": "New"})
            reload_opts(len(opts()) - 1)
            self._touch(member)
            self._checkpoint(member, "add choice option", f"choice:{idx}")

        def update_sel():
            r = opts_list.currentRow()
            if not (0 <= r < len(opts())) or not st["getters"]:
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
            ensure_opts()[r] = opt
            reload_opts(r)
            self._touch(member)
            self._checkpoint(member, "edit choice option", f"choice:{idx}")

        def remove():
            r = opts_list.currentRow()
            if 0 <= r < len(opts()):
                ensure_opts().pop(r)
                reload_opts()
                self._touch(member)
                self._checkpoint(member, "remove choice option", f"choice:{idx}")

        def move(d):
            r = opts_list.currentRow()
            j = r + d
            o = opts()
            if 0 <= r < len(o) and 0 <= j < len(o):
                o[r], o[j] = o[j], o[r]
                reload_opts(j)
                self._touch(member)
                self._checkpoint(member, "reorder choice options", f"choice:{idx}")

        self.doc_host_lay.addWidget(self._list_buttons(
            [("Add new", add_new), ("Update", update_sel), ("Remove", remove),
             ("Up", lambda: move(-1)), ("Down", lambda: move(1))]))
        reload_opts(0 if opts() else None)
        self._save_ctx = {"member": member, "key": f"choice:{idx}", "spec": forms.CHOICE_SPEC,
                          "getters": getters, "single": False, "section": "choice", "idx": idx}
        self._add_save(lambda: self._commit(member, "choice", forms.CHOICE_SPEC, getters,
                                            single=False, idx=idx, key=f"choice:{idx}"),
                       ("Delete choice", lambda: self._delete_object(member, "choice", single=False,
                                                                     idx=idx, label="choice")))

    def _copy_inspect_path(self, _href):
        """Click the inspector's file link -> copy the full path to the clipboard (with a status note)."""
        if self._inspect_path:
            QApplication.clipboard().setText(self._inspect_path)
            self.statusBar().showMessage(f"Copied path: {self._inspect_path}", 4000)

    def _inspect_link(self, href):
        """Inspector hyperlink dispatch: 'copy' -> copy the file path; 'goto:battle:<id>' -> jump to the
        Battle tab for an encounter's scene; 'goto:<member>' -> select that field; 'jseed:'/'jtuning:<id>' ->
        the journey seed / tuning editors (the same callbacks the journey button row + right-click bind)."""
        if href == "copy":
            self._copy_inspect_path("copy")
        elif href.startswith("goto:battle:"):
            self._goto_battle_scene(href[len("goto:battle:"):])
        elif href.startswith("goto:"):
            self._select_member(href[len("goto:"):])
        elif href.startswith("jseed:"):
            self.on_set_journey_seed(href[len("jseed:"):])
        elif href.startswith("jtuning:"):
            self.on_set_journey_tuning(href[len("jtuning:"):])
        elif href == "openparent":
            self._open_parent_campaign()

    def _goto_battle_scene(self, sid_text):
        """Cross-tab jump from a field's [[encounter]] to the Battle tab. battle.toml is a standalone SIBLING
        with no on-disk back-link from the field, so we can't reliably locate the authoring file -- switch to
        the Battle tab and, if it already has that scene open, confirm it; else nudge toward Fork battle…
        (fail-soft: never block, never guess a file)."""
        self.tabs.setCurrentWidget(self.battle)
        try:
            sid = int(sid_text)
        except (TypeError, ValueError):
            return
        open_sid = self.battle.open_scene_id() if hasattr(self.battle, "open_scene_id") else None
        if open_sid == sid:
            self.statusBar().showMessage(f"Battle tab — scene {sid} (this battle.toml authors it).", 5000)
        else:
            self.statusBar().showMessage(
                f"Battle tab — scene {sid} isn't open here. Open its battle.toml, or use Fork battle… to "
                f"author it.", 7000)

    def _goto_link(self, member):
        return self._link(f"goto:{member}", member)

    def _link(self, href, label):
        """An inspector hyperlink (accent-coloured, no underline) routed through :meth:`_inspect_link`."""
        return (f'<a href="{_esc(href)}" style="color:{self.pal["accent"]};'
                f'text-decoration:none;">{_esc(label)}</a>')

    def _muted(self, s):
        return f'<span style="color:{self.pal["muted"]};">{s}</span>'

    def _safe_doc(self, member):
        """The member's FieldDoc, loading+caching it if needed (the Inspector runs BEFORE the editor mounts,
        so a never-opened field would otherwise have no data to roll up). None on a load error."""
        if member in self._docs:
            return self._docs[member]
        try:
            return self._doc(member)
        except Exception:                              # noqa: BLE001
            return None

    def _inspect(self, item, payload, field):
        if payload is None:
            return
        kind, label, key = payload
        self.insp_title.setText(label)
        self.insp_body.setToolTip("")                       # full path (if any) goes on hover, not inline
        self._inspect_path = None
        if kind in _LOGIC_KINDS:                            # a read-only logic-map node -> show its decoded detail
            detail = item.data(0, _DETAIL) or []
            self.insp_body.setText("<br>".join(detail) if detail else self._muted("— (no decoded detail)"))
            return
        try:                                                # a single bad node must never blank/break the panel
            lines = self._inspect_build(kind, key, field)
        except Exception:                                   # noqa: BLE001
            lines = [self._muted("— (could not inspect this node)")]
        self.insp_body.setText("<br>".join(lines) if lines else "—")

    def _inspect_build(self, kind, key, field):
        if kind == "field":
            return self._inspect_field(field)
        if kind == "campaign" and self.plan is not None:
            g = C.campaign_graph(self.plan)
            return [f"{len(self.plan.members)} fields", f"entry: {g.entry or '(none)'}",
                    f"mod folder: {self.plan.mod_folder}",
                    f"unreachable: {len(g.unreachable)} · dead-ends: {len(g.dead_ends)}"]
        if kind == "journey":
            back = (self.manifest is not None) or (self._journey_label_path is not None)
            lines = ["a playable arc (see docs/JOURNEYS.md)"]
            j = None
            if self.manifest is not None and key and ":" in key:     # a specific [[journey]] row (not the hub root)
                j = next((x for x in self.manifest.journeys if x.id == key.split(":", 1)[1]), None)
            if j is not None:
                lines.append(self._muted("single-field journey" if j.is_bare
                                         else f"{len(j.campaigns)}-campaign arc"))
                if j.seed.party:
                    lines.append(f"base party: {', '.join(j.seed.party)}")
                if j.tuning:
                    nrows = sum(len(v) for v in j.tuning.values() if isinstance(v, list))
                    lines.append(self._muted(f"tuning: {nrows} player-CSV row(s)"))
                if j.hub_scenario is not None:
                    lines.append(self._muted(f"start beat: {j.hub_scenario}"))
                lines.append(self._link(f"jseed:{j.id}", "Set base party / seed…") + self._muted(" · ")
                             + self._link(f"jtuning:{j.id}", "Set tuning…"))
            else:
                lines.append(self._muted("double-click to open the whole journey" if back
                                         else "authoring is the overworld / World-Hub lane"))
            return lines
        if kind == "group" and field:
            return self._inspect_group(field, key)
        if kind == "object" and field:
            return self._inspect_object(field, key)
        return [self._muted(f"in field: {field}")] if field else []

    def _inspect_field(self, name):
        """A campaign member (or a loose field): id/source/mode, a CONTENT rollup, the live cross-references
        (exits to / reached from -- clickable member links + reachability flags), and the file-path link."""
        lines = []
        doc = self._safe_doc(name)
        if self.plan is not None:
            m = next((mm for mm in self.plan.members if mm.name == name), None)
            if m:
                lines += [f"field id: {m.new_id}",
                          self._muted(f"source: real field {m.real_id} · mode: {m.mode}")]
        elif doc is not None:
            lines.append(f"field id: {(doc.data.get('field') or {}).get('id')}")
        if self.plan is None and name == self._loose and self._loose_parent[0] is not None:
            cname = self._loose_parent[2] or self._loose_parent[0].parent.name   # the upward jump (do-now #5)
            lines.append(f'▣ part of campaign <b>{_esc(str(cname))}</b> — '
                         + self._link("openparent", "Open the campaign (full context)"))
        if doc is not None:
            lines.append(self._rollup(doc.data))
            lines += self._battle_party_lines(doc.data)     # encounter scene / [party] / [startup] read-only detail
            if doc.data.get("verbatim_eb"):             # explain the empty rollup BEFORE it confuses (the orig. Q)
                lines.append(self._muted("verbatim fork — content is in the shipped .eb, not these lists; "
                                         "see 'Script (verbatim .eb)'"))
            nbad = self._count_node_problems(name)      # field-level health badge (cheap per-node predicates)
            if nbad:
                lines.append(f'<span style="color:{self.pal["warn"]};">⚠ {nbad} object(s) with issues — '
                             f'select one to see</span>')
        if self.plan is not None:
            lines += self._field_xrefs(name)
        path = self.member_paths.get(name)
        if path:
            self._inspect_path = str(path)
            self.insp_body.setToolTip(str(path))            # a long absolute path mustn't force the panel wide
            lines.append(f'<a href="copy" style="color:{self.pal["accent"]};text-decoration:none;">'
                         f'file: {Path(path).name}  ⧉ copy</a>')
        return lines

    def _rollup(self, data):
        """A one-line 'what's in this field' tally -- the content the tree groups hide behind their counts."""
        bits = []
        for sect, sing in (("npc", "NPC"), ("gateway", "gateway"), ("event", "event"),
                           ("marker", "marker"), ("choice", "choice")):
            n = len(data.get(sect, []) or [])
            if n:
                bits.append(f"{n} {sing}{'' if n == 1 else 's'}")
        if data.get("cutscene"):
            steps = len((data.get("cutscene") or {}).get("steps", []) or [])
            bits.append(f"cutscene ({steps} step{'' if steps == 1 else 's'})")
        if data.get("encounter"):
            bits.append("encounters")
        if data.get("music"):
            bits.append("BGM")
        return self._muted("contents: " + (", ".join(bits) if bits else "empty"))

    def _battle_party_lines(self, data):
        """Read-only battle/party summary lines for a field's Inspector card: the encounter scene (id + its
        resolved BSC_ name, so a debug-bucket id like BSC_B3_* is visible at a glance), the [party] add/remove
        roster, and the [startup] beat. All offline -- no install, no battle-scene DATA read."""
        from .. import catalog as _cat
        from ..content import party as _party
        lines = []
        enc = data.get("encounter")
        if isinstance(enc, dict) and enc.get("scene") is not None:
            sid = enc.get("scene")
            nm = _cat.scene_name(sid) if isinstance(sid, int) else None
            scene_txt = f"scene {sid}" + (f" — {nm}" if nm else "")
            # the resolved scene is the field's one cross-edge to a battle.toml -> make it a Battle-tab jump
            scene_seg = self._link(f"goto:battle:{sid}", scene_txt) if isinstance(sid, int) else _esc(scene_txt)
            lines.append(self._muted("encounter: ") + scene_seg
                         + self._muted(f" · freq {enc.get('freq', 255)}"))
        pty = data.get("party")
        if isinstance(pty, dict) and (pty.get("add") or pty.get("remove")):
            def _who(m):
                return _party.CHAR_OLD_INDEX.get(m, str(m)) if isinstance(m, int) else str(m)
            roster = ([f"+{_who(m)}" for m in pty.get("add", []) or []]
                      + [f"−{_who(m)}" for m in pty.get("remove", []) or []])
            lines.append(self._muted("party: " + ", ".join(roster)))
        su = data.get("startup")
        if isinstance(su, dict) and (su.get("scenario") is not None or su.get("flags")):
            bits = []
            sc = su.get("scenario")
            if sc is not None:
                from .. import flags as _flags
                beat = getattr(_flags, "SCENARIO_MILESTONES", {}).get(sc) if isinstance(sc, int) else None
                bits.append(f"scenario {sc}" + (f" ({beat})" if beat else ""))
            nf = len(su.get("flags", []) or [])
            if nf:
                bits.append(f"{nf} flag{'' if nf == 1 else 's'}")
            lines.append(self._muted("startup: " + " · ".join(bits)))
        return lines

    def _field_xrefs(self, name):
        """The member's doors as clickable cross-references -- the SAME edges the Map draws, resolved from the
        campaign manifest as loaded (plan.edges). NOTE: these reflect the campaign AS OPENED -- a gateway edit
        isn't mirrored here until the campaign is reopened (the rollup/destination lines above DO read the live
        doc), so we flag it when the field has unsaved edits."""
        try:
            node = C.campaign_graph(self.plan).by_name.get(name)
        except Exception:                              # noqa: BLE001
            return []
        if node is None:
            return []
        lines = []
        if node.out_edges:
            lines.append("→ exits to: " + ", ".join(
                self._goto_link(oe["to"]) + (" (gated)" if oe["gated"] else "") for oe in node.out_edges))
        if node.in_edges:
            lines.append("← reached from: " + ", ".join(
                self._goto_link(ie["frm"]) + (" (gated)" if ie.get("gated") else "") for ie in node.in_edges))
        for s in node.seams:
            tgt = s.get("to_member") or s.get("to_real") or "?"
            lines.append(f"⇢ seam ({_esc(s.get('kind', ''))}): "
                         + (self._goto_link(tgt) if s.get("to_member") else _esc(tgt)))
        if not node.reachable and not node.is_entry:
            lines.append(f'<span style="color:{self.pal["error"]};">⚠ unreachable from the entry</span>')
        elif node.dead_end:
            lines.append(self._muted("○ dead end — no exits"))
        if name in self._unsaved():                    # the doors above are as-of-open; warn that edits aren't live
            lines.append(self._muted("↻ doors as of campaign open — reopen to refresh after gateway edits"))
        return lines

    def _inspect_group(self, member, key):
        doc = self._safe_doc(member)
        n = len(doc.data.get(key, []) or []) if doc else 0
        sing = _LIST_SINGULAR.get(key, key)
        return [f"in field: {self._goto_link(member)}",
                self._muted(f"{n} {sing.lower()}{'' if n == 1 else 's'} — pick one to edit, or add a new one")]

    def _inspect_object(self, member, key):
        if key == "field":                             # the 'Field' child node -> the SAME rich view as the row
            return self._inspect_field(member)
        doc = self._safe_doc(member)
        if doc is None:
            return [self._muted(f"in field: {member}")]
        head = [f"in field: {self._goto_link(member)}"]
        if key == "camera":                            # spatial -- Blender-only (mirror the editor's own note)
            return head + [self._muted("camera / walkmesh / layers are SPATIAL — authored in Blender, "
                                       "read-only here.")]
        if ":" in key:                                 # a list entity (npc:2, gateway:0, ...)
            section, idx = key.split(":")
            lst = doc.data.get(section, []) or []
            idx = int(idx)
            if idx >= len(lst):
                return head
            e = lst[idx]
            if not isinstance(e, dict):                 # a malformed inline entry (e.g. npc = ["foo"])
                return head + [f'<span style="color:{self.pal["warn"]};">⚠ malformed entry (not a table)</span>']
            return head + self._inspect_entity(section, e) + self._node_problems(section, e, member)
        data = doc.data.get(key)                        # a single section
        return head + self._inspect_single(key, data) + self._node_problems(key, data or {}, member)

    def _inspect_entity(self, section, e):
        m = self._muted
        if section == "npc":
            model = e.get("preset") or (f"model #{e['model']}" if e.get("model") is not None else "?")
            out = [f"NPC: {_esc(e.get('name', '?'))}", m(f"looks like: {_esc(model)}")]
            if e.get("pos") is not None:
                out.append(m(f"pos: {_esc(e['pos'])}"))
            if e.get("dialogue"):
                out.append(m(f"“{_esc(_snip(e['dialogue']))}”"))
            return out + self._gate_lines(e)
        if section == "gateway":
            dest, broken = self._resolve_dest(e.get("to"))
            out = ["gateway → " + dest]
            if e.get("entrance") is not None:
                out.append(m(f"entrance: {_esc(e['entrance'])}"))
            if e.get("zone"):
                out.append(m(f"zone: {len(e['zone'])} pts"))
            if broken:
                out.append(f'<span style="color:{self.pal["warn"]};">⚠ destination not in this campaign</span>')
            return out + self._gate_lines(e)
        if section == "event":
            eff = []                                   # an event can do several things -> show ALL, not just one
            if e.get("give_item"):
                eff.append("item")
            if e.get("gil") is not None:
                eff.append("gil")
            if e.get("set_flag"):
                eff.append("flag")
            if e.get("message"):
                eff.append("message")
            out = [f"event: {_esc(e.get('name', 'event'))} ({'+'.join(eff) if eff else 'trigger'})"]
            if e.get("message"):
                out.append(m(f"“{_esc(_snip(e['message']))}”"))
            if e.get("set_flag"):
                out.append(m(f"sets flag: {_esc(e['set_flag'])}"))
            out.append(m(f"once: {str(e.get('once', True)).lower()}"))
            return out + self._gate_lines(e)
        if section == "marker":
            out = [f"marker: {_esc(e.get('name', '?'))}"]
            if e.get("pos") is not None:
                out.append(m(f"pos: {_esc(e['pos'])}"))
            return out
        if section == "choice":
            out = [f"choice: “{_esc(_snip(e.get('prompt', '')))}”",
                   m(f"{len(e.get('options', []) or [])} option(s)")]
            if e.get("npc"):
                out.append(m(f"on NPC: {_esc(e['npc'])}"))
            elif e.get("zone"):
                out.append(m(f"zone trigger: {len(e['zone'])} pts"))
            return out
        return [m(f"kind: {section}")]

    def _gate_lines(self, e):
        out = []
        if e.get("requires_flag"):
            out.append(self._muted(f"shows when flag set: {_esc(e['requires_flag'])}"))
        if e.get("requires_flag_clear"):
            out.append(self._muted(f"shows when flag clear: {_esc(e['requires_flag_clear'])}"))
        return out

    def _inspect_single(self, key, data):
        if not data:
            return [self._muted(f"{key}: not set — select it to author")]
        if key == "cutscene":
            steps = (data or {}).get("steps", []) or []
            out = [f"cutscene: {len(steps)} step{'' if len(steps) == 1 else 's'}",
                   self._muted("actor: " + (_esc(data["actor"]) if data.get("actor") else "narration")),
                   self._muted(f"once: {str(data.get('once', True)).lower()}")]
            if steps:
                out.append(self._muted(f"first: {_esc(forms.step_summary(steps[0]))}"))
            return out
        return [self._muted(f"{_esc(k)}: {_esc(_snip(v))}") for k, v in (data or {}).items()]

    # ---- Tier-3: cheap, EXACT per-node validation (the inline lint signal) ----
    def _name_ok(self, cat, value):
        """Memoized 'is this catalog value valid?', MIRRORING the build's own resolvers so the Inspector and
        Check agree. The catalogs are STATIC, so (cat, value) -> bool never changes in-session and is cached
        forever -- this bounds the resolvers' near-miss difflib cost to once per distinct value (the field
        health badge re-scans every object on each tree click). On any predicate error -> True (don't cry wolf)."""
        key = (cat, value if isinstance(value, (str, int, float)) else repr(value))
        if key in self._name_valid:
            return self._name_valid[key]
        ok = True
        try:
            from .. import archetypes, catalog, items
            if cat == "archetype":                         # build: archetypes.resolve ONLY (a GEO name errors too)
                try:
                    archetypes.resolve(value)
                except ValueError:
                    ok = False
            elif cat == "model":                           # a GEO model NAME (a raw int id passes the build)
                ok = catalog.model(value) is not None
            elif cat == "item":
                try:
                    items.resolve(value)
                except (ValueError, TypeError):
                    ok = False
        except Exception:                                  # noqa: BLE001 -- predicate import/quirk: stay silent
            ok = True
        self._name_valid[key] = ok
        return ok

    def _scene_entity_names(self, member):
        """``(npc names, marker names)`` from the sibling ``<stem>.scene.toml`` (the Blender-owned spatial
        file -- entity lists are SPLIT field/scene by name, so an NPC/marker can be scene-ONLY). Cached by
        the file's mtime so a Blender re-export is picked up; a missing sibling -> empty (uncached)."""
        path = self.member_paths.get(member)
        if not path:
            return frozenset(), frozenset()
        name = Path(path).name                              # <x>.field.toml -> <x>.scene.toml (build's convention)
        stem = name[:-len(".field.toml")] if name.endswith(".field.toml") else Path(path).stem
        sib = Path(path).parent / f"{stem}.scene.toml"
        try:
            mtime = sib.stat().st_mtime
        except OSError:
            return frozenset(), frozenset()                 # no sibling -> don't cache (a later export is seen)
        cached = self._scene_names.get(member)
        if cached and cached[0] == mtime:
            return cached[1], cached[2]
        try:
            import tomllib
            sd = tomllib.loads(sib.read_text(encoding="utf-8"))
        except Exception:                                   # noqa: BLE001 -- a malformed scene -> no names
            sd = {}
        npc = frozenset(n.get("name") for n in (sd.get("npc", []) or [])
                        if isinstance(n, dict) and n.get("name"))
        mk = frozenset(n.get("name") for n in (sd.get("marker", []) or [])
                       if isinstance(n, dict) and n.get("name"))
        self._scene_names[member] = (mtime, npc, mk)
        return npc, mk

    def _field_entity_names(self, member):
        """``{'npc': set, 'marker': set}`` of entity NAMES for a field, MERGED from its live field.toml
        (doc.data) AND its sibling scene.toml -- so a choice/cutscene reference to a scene-placed NPC/marker
        isn't falsely flagged (the false positive that got these checks dropped in Tier-3)."""
        doc = self._safe_doc(member)
        data = doc.data if doc else {}
        s_npc, s_mk = self._scene_entity_names(member)

        def field(sec):
            return {n.get("name") for n in (data.get(sec, []) or []) if isinstance(n, dict) and n.get("name")}
        return {"npc": field("npc") | s_npc, "marker": field("marker") | s_mk}

    def _node_problems(self, kind, obj, member):
        """Per-node problems computed DIRECTLY from the kit's pure predicates, MIRRORING what the build
        actually accepts (so the Inspector never contradicts Check): an unknown archetype/preset (or, when
        no archetype, an unknown GEO model NAME -- a raw model id passes); an unknown give/remove item; a
        NON-NUMERIC battle scene (the build does int(scene)); a set_flag into a reserved gEventGlobal bit;
        and a choice/cutscene reference to an NPC/marker that exists in NEITHER the field.toml NOR the
        sibling scene.toml. The geometric/structural lint (off-walkmesh, seams, dialogue overflow) stays
        with Check. Never raises. Returns colored ⚠ lines."""
        if not isinstance(obj, dict):
            return []
        out = []
        warn = lambda msg: out.append(f'<span style="color:{self.pal["warn"]};">⚠ {_esc(msg)}</span>')  # noqa: E731
        try:
            if kind == "npc":
                arch = obj.get("archetype") or obj.get("preset")
                if arch is not None and not isinstance(arch, bool):
                    if not self._name_ok("archetype", arch):
                        warn(f"unknown archetype '{arch}'")
                else:                                      # model is used ONLY when there's no archetype/preset
                    mid = obj.get("model")
                    if isinstance(mid, str) and mid.strip() and not mid.strip().isdigit() \
                            and not self._name_ok("model", mid):    # a raw int id passes (the build accepts it)
                        warn(f"unknown model '{mid}'")
            elif kind == "event":
                for fld in ("give_item", "remove_item"):
                    v = obj.get(fld)
                    if v:
                        it = v[0] if isinstance(v, (list, tuple)) and v else v
                        if not self._name_ok("item", it):
                            warn(f"unknown item '{it}'")
                sf = obj.get("set_flag")
                if isinstance(sf, (list, tuple)) and sf:
                    f0 = sf[0]
                    if (isinstance(f0, int) and not isinstance(f0, bool)) or (isinstance(f0, str) and f0.isdigit()):
                        from .. import flags
                        if flags.is_reserved(int(f0)):
                            warn(f"set_flag writes a reserved bit ({f0})")
            elif kind == "flag":                           # mirror collect_flag_defs: the index must be in-band
                from .. import flags
                idx = obj.get("index")
                if isinstance(idx, (int, str)) and str(idx).lstrip("-").isdigit():
                    n = int(idx)
                    if not (flags.FIRST_SAFE_FLAG <= n < flags.CHOICE_SCRATCH_FLOOR):
                        warn(f"flag index {n} is outside the safe custom band "
                             f"[{flags.FIRST_SAFE_FLAG}, {flags.CHOICE_SCRATCH_FLOOR})")
            elif kind == "encounter":
                sc = obj.get("scene")
                if sc is not None and not ((isinstance(sc, int) and not isinstance(sc, bool))
                                           or (isinstance(sc, str) and sc.strip().lstrip("-").isdigit())):
                    warn(f"battle scene must be a numeric id (got '{sc}')")
            elif kind == "choice":
                ref = obj.get("npc")                       # talk-triggered: must name an existing NPC
                if isinstance(ref, str) and ref.strip() and ref not in self._field_entity_names(member)["npc"]:
                    warn(f"no NPC named '{ref}' in this field")
            elif kind == "cutscene":
                seen = self._field_entity_names(member)
                actor = obj.get("actor")               # build: an actor must be a defined [[npc]] (build.py:1112)
                if isinstance(actor, str) and actor.strip() and actor not in seen["npc"]:
                    warn(f"no NPC named '{actor}' for the actor")
                # a movement target resolves against markers + NPCs + player/spawn (build's _resolve_point
                # registry; a leading @ is optional, a [x, z] list / "x, z" coords pass). Applies to a single
                # walk/teleport target AND every string waypoint of a path route (build.py:1097-1111).
                targets = seen["marker"] | seen["npc"] | {"player", "spawn"}

                def bad_target(tgt):
                    if not (isinstance(tgt, str) and tgt.strip()) or _coord_like(tgt):
                        return False                   # a coord [x,z] / "x, z" or a non-string passes
                    nm = tgt.strip()
                    return (nm[1:] if nm.startswith("@") else nm) not in targets

                for st in (obj.get("steps", []) or []):
                    if not isinstance(st, dict):
                        continue
                    for skey in ("walk", "teleport"):   # a single movement target
                        if bad_target(st.get(skey)):
                            warn(f"{skey} target '{st[skey]}' isn't a marker/NPC in this field")
                    if isinstance(st.get("path"), list):    # a route: every string waypoint resolves too
                        for elem in st["path"]:
                            if bad_target(elem):
                                warn(f"path waypoint '{elem}' isn't a marker/NPC in this field")
        except Exception:                              # noqa: BLE001 -- a predicate quirk must never break inspect
            return out
        return out

    def _count_node_problems(self, member):
        """How many objects in a field have a per-node problem (the field-level health badge) -- cheap +
        memoized over npc/event/choice + the encounter/cutscene singles."""
        doc = self._safe_doc(member)
        data = doc.data if doc else {}
        n = 0
        for section in ("npc", "event", "choice"):
            for e in (data.get(section, []) or []):
                if isinstance(e, dict) and self._node_problems(section, e, member):
                    n += 1
        for single in ("encounter", "cutscene"):
            if data.get(single) and self._node_problems(single, data[single], member):
                n += 1
        return n

    def _resolve_dest(self, to):
        """A gateway's destination id -> (display html, broken?). A campaign member -> a clickable name; a
        real FF9 field -> its (shortened) FBG folder; otherwise it's dangling (⚠). Coerces ``to`` to an int
        once so the member / real-field / dangling branches agree (a hand-edited toml may hold a string)."""
        raw = to
        try:
            to = int(to)
        except (TypeError, ValueError):
            to = None
        if to is None:                                 # unset, or a non-numeric value -> dangling (escaped)
            return (self._muted("(unset)") if raw is None else f"field {_esc(raw)}", raw is not None)
        if self.plan is not None:
            m = next((mm for mm in self.plan.members if mm.new_id == to), None)
            if m:
                return (self._goto_link(m.name) + " " + self._muted(f"(field {to})"), False)
        folder = self._real_field_name(to)
        if folder:
            return (f"{_esc(_snip(folder, 28))} " + self._muted(f"(real field {to})"), False)
        return (f"field {to}", True)

    @staticmethod
    def _real_field_name(fid):
        try:
            from .. import extract
            return extract.ID_TO_FBG.get(int(fid))
        except Exception:                              # noqa: BLE001
            return None

    def _select_member(self, name):
        mi = getattr(self, "_member_items", {}).get(name)
        if mi is not None:
            self.tree.setCurrentItem(mi)
            self.tree.scrollToItem(mi)

    def _on_crumb(self, crumb):
        if crumb.level == bc.FIELD and self.manifest is None:    # a campaign-mode field crumb -> select the member
            self._select_member(crumb.key)
        elif crumb.level in (bc.JOURNEY, bc.CAMPAIGN, bc.HUB) or crumb.level == bc.FIELD:
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
        if self.manifest is not None and self.plan is None:   # journey mode -> lint the manifest
            self._lint_journey()
            return
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
        self._raise_dock()

    def run_job(self, argv, *, cwd=None, subject="Job", ok_headline=None, ok_next="",
                fail_hint="See the Output panel.", on_finished=None):
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
        self._raise_dock()
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
            self, "_job", ("Job", None, "", "See the Output panel.", None))
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
    # the single sections ALWAYS show (so an absent one is authorable) even though IC_ENT has none yet
    assert {"Dialogue", "Encounter", "Music", "Cutscene"} <= set(groups), groups
    # lazy: BROWSING an absent single must NOT materialize it (that would dirty the field). Only a real edit
    # (add a cutscene step / Save a filled form) creates the [section].
    assert "cutscene" not in win._doc("IC_ENT").data
    win._open_editor("IC_ENT", "object", "cutscene")        # mount the empty cutscene editor
    assert "cutscene" not in win._doc("IC_ENT").data, "mounting an absent Cutscene must not create it"
    assert win._commit_active() is True                     # navigate-away folds the empty header...
    assert "cutscene" not in win._doc("IC_ENT").data, "an empty Cutscene is not materialized on leave"
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
    # [party] mounts via the SAME single-table path (registered in _SINGLES); STRLIST add/remove -> a real list
    pnode = win._object_item("IC_ENT", "party")
    assert pnode is not None and pnode.foreground(0).color().name().lower() == \
        QColor(win.pal["muted"]).name().lower(), "an unauthored [party] node is dimmed"
    win._open_editor("IC_ENT", "object", "party")
    assert win._save_ctx["single"] and win._save_ctx["section"] == "party"
    win._save_ctx["getters"]["add"] = lambda: "Steiner, Beatrix"      # as if typed into the add field
    win._save()
    saved = tomllib.loads((d / "IC_ENT" / "IC_ENT.field.toml").read_text(encoding="utf-8"))
    assert saved["party"]["add"] == ["Steiner", "Beatrix"], saved
    assert pnode.foreground(0).color().name().lower() == QColor(win.pal["text"]).name().lower(), \
        "saving [party] un-dims its tree node (no full subtree rebuild on save)"
    # [startup] mounts the same single-table way; SCENARIOREF -> a beat int, FLAGDICTLIST -> a {flag,value} list
    win._open_editor("IC_ENT", "object", "startup")
    assert win._save_ctx["section"] == "startup"
    win._save_ctx["getters"]["scenario"] = lambda: "2600"
    win._save_ctx["getters"]["flags"] = lambda: "boss_dead, 1"
    win._save()
    saved = tomllib.loads((d / "IC_ENT" / "IC_ENT.field.toml").read_text(encoding="utf-8"))
    assert saved["startup"]["scenario"] == 2600 and \
        saved["startup"]["flags"] == [{"flag": "boss_dead", "value": 1}], saved
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
    win._add_list_item("IC_ENT", "flag")               # the [[flag]] section (audit #7 -> story flags are GUI-authorable)
    assert win._doc("IC_ENT").data["flag"][-1] == {"name": "flag", "index": 8512} and win._save_ctx["section"] == "flag"
    assert forms.build_entity(forms.FLAG_SPEC, {"name": "got_sword", "index": "8520"}) == {"name": "got_sword", "index": 8520}
    assert win._node_problems("flag", {"name": "x", "index": 8520}, "IC_ENT") == []   # in-band: clean
    assert win._node_problems("flag", {"name": "x", "index": 100}, "IC_ENT")          # out-of-band: warns
    win._confirm = lambda *a: True
    win._delete_object("IC_ENT", "flag", single=False, idx=len(win._doc("IC_ENT").data["flag"]) - 1, label="Flag")
    assert "flag" not in win._doc("IC_ENT").data                                       # cleaned up
    # DELETE a list entity: removes it, writes the file, refreshes the tree, lands on the group
    win._confirm = lambda *a: True                     # stub the destructive confirm (headless)
    n_after_add = len(win._doc("IC_ENT").data["npc"])
    win._delete_object("IC_ENT", "npc", single=False, idx=n_after_add - 1, label="NPC")
    assert len(win._doc("IC_ENT").data["npc"]) == n_after_add - 1, "the NPC was removed"
    assert win._payload(win.tree.currentItem())[0] == "group"            # landed on the NPCs group
    win._delete_object("IC_ENT", "gateway", single=False, idx=0, label="Gateway")
    assert "gateway" not in win._doc("IC_ENT").data, "an emptied list drops its key"
    win._confirm = lambda *a: False                    # a declined confirm deletes nothing
    keep = len(win._doc("IC_ENT").data["npc"])
    win._delete_object("IC_ENT", "npc", single=False, idx=0, label="NPC")
    assert len(win._doc("IC_ENT").data["npc"]) == keep, "a declined delete leaves the list intact"
    win._confirm = lambda *a: True
    # tree right-click / Delete-key context actions: Add on a group, Delete on an entity, Remove a single
    grp = win._object_item("IC_ENT", "npc", kind="group")
    assert [lb for lb, _ in win._context_actions(grp)] == ["Add NPC"], win._context_actions(grp)
    # the campaign ROOT offers 'Add field…' (scaffold a new member); the Delete key ignores it (not Delete/Remove)
    assert [lb for lb, _ in win._context_actions(win._root_items[0])] == ["Add field…"]
    ent_item = win._object_item("IC_ENT", "npc:0")
    assert ent_item and win._context_actions(ent_item)[0][0] == "Delete NPC"
    cs_item = win._object_item("IC_ENT", "cutscene")                     # the (always-shown) Cutscene node
    assert win._context_actions(cs_item) == []                           # absent single -> nothing to remove
    win._doc("IC_ENT").data["cutscene"] = {"steps": [{"say": "x"}]}      # ...but an EXISTING single is removable
    assert win._context_actions(cs_item)[0][0] == "Remove cutscene"
    win._doc("IC_ENT").data.pop("cutscene", None)                        # clean up (Phase 4b sets it fresh)
    before_del = len(win._doc("IC_ENT").data.get("npc", []))
    win.tree.setCurrentItem(ent_item)                                   # select the NPC, then press Delete
    win._delete_selected()
    assert len(win._doc("IC_ENT").data.get("npc", [])) == before_del - 1, "the Delete key removed the NPC"
    # EDITING POLISH -- (1) unsaved-dot icon: touching a member dots its tree row; saving clears it. Clean
    # rows carry a TRANSPARENT same-size icon (not a null one) so the dot never resizes/shifts the row.
    is_dot = lambda it: it.icon(0).cacheKey() == win._dot_icon.cacheKey()        # noqa: E731
    win._mark_clean("IC_ENT")                          # known-clean baseline
    mi_ic = win._member_items["IC_ENT"]
    assert not mi_ic.icon(0).isNull() and not is_dot(mi_ic), "a clean member reserves the slot (blank icon)"
    win._touch("IC_ENT")
    assert is_dot(mi_ic), "an edited member shows the unsaved-dot icon"
    # roll-up: the campaign root + the window title also reflect unsaved work (visible when collapsed)
    assert win._root_items and is_dot(win._root_items[0]), "the campaign root rolls up the dot"
    assert win.windowTitle().endswith("•"), "the window title marks unsaved work"
    win._mark_clean("IC_ENT")
    assert not is_dot(mi_ic), "saving clears the unsaved-dot (back to the blank icon)"
    assert not is_dot(win._root_items[0]) and not win.windowTitle().endswith("•"), "root + title clear"
    # (2) reverting a value to its original clears the in-progress dot (no save needed)
    win._open_editor("IC_ENT", "field", "field")
    id_w = win._save_ctx["getters"]["id"].__self__     # the id QLineEdit behind the field form
    orig = id_w.text()
    id_w.setText(orig + "9")                            # edit -> on_field_change -> _on_form_change -> touched
    assert "IC_ENT" in win._touched, "editing a field marks it touched"
    id_w.setText(orig)                                 # revert -> matches baseline -> un-touched
    assert "IC_ENT" not in win._touched, "reverting a value clears the in-progress dot"
    # (3) Ctrl-S runs the mounted form's Save handler
    saved_calls = []
    win._active_save = lambda: saved_calls.append(True)
    win._save_shortcut()
    assert saved_calls, "Ctrl-S runs the active form's Save handler"
    # (3b) Save All writes every dirty field + clears the dots
    import tomllib as _tl_sa
    win._save_ctx = None                               # no active form to fold over the direct edit
    win._doc("IC_ENT").data.setdefault("field", {})["area"] = 12
    assert "IC_ENT" in win._dirty_members()
    win._save_all()
    assert "IC_ENT" not in win._dirty_members() and not is_dot(win._member_items["IC_ENT"]), \
        "Save All wrote the field + cleared its dot"
    assert _tl_sa.loads((d / "IC_ENT" / "IC_ENT.field.toml").read_text(encoding="utf-8"))["field"]["area"] == 12
    assert "Save All fields" in [e[0] for e in win._command_index()]
    # small wins -- (a) Enter on a tree row opens it (Editor for a field, Map for the campaign root)
    win.tabs.setCurrentWidget(win.map)
    win.tree.setCurrentItem(win._member_items["IC_ENT"])
    win._open_current_tree_item()
    assert win.tabs.currentWidget() is win.doc_scroll, "Enter on a field opens the Editor"
    win.tree.setCurrentItem(win._root_items[0])
    win._open_current_tree_item()
    assert win.tabs.currentWidget() is win.map, "Enter on the campaign root opens the Map"
    # (a2) the inspector shows the FILE NAME inline as a copy-to-clipboard link; the full path is on the
    # tooltip + copied on click (so a long absolute path can't balloon the panel)
    win.tree.setCurrentItem(win._member_items["IC_ENT"])
    mp = str(win.member_paths["IC_ENT"])
    assert "file: IC_ENT.field.toml" in win.insp_body.text() and 'href="copy"' in win.insp_body.text()
    assert mp not in win.insp_body.text(), "the full path is not shown inline"
    assert win.insp_body.toolTip() == mp and win._inspect_path == mp
    win._copy_inspect_path("copy")
    assert QApplication.clipboard().text() == mp, "the file link copies the full path"
    # FULLER INSPECTOR -- a field node shows a content ROLLUP + clickable CROSS-REFERENCES (the live doors,
    # same edges the Map draws). IC_ENT -> IC_COR is a stable plan edge.
    win.tree.setCurrentItem(win._member_items["IC_ENT"])
    ib = win.insp_body.text()
    assert "contents:" in ib, ib
    assert "party:" in ib and "Steiner" in ib, ib                  # read-only [party] roster (saved earlier)
    assert "exits to:" in ib and 'href="goto:IC_COR"' in ib, ib    # clickable member link
    # the goto link navigates: feeding it to the link dispatch selects that member in the tree
    win._inspect_link("goto:IC_COR")
    assert win._payload(win.tree.currentItem())[1] == "IC_COR", "a cross-ref link selects the field"
    # IC_COR is reached-from IC_ENT (the reverse edge), also clickable
    assert "reached from:" in win.insp_body.text() and 'href="goto:IC_ENT"' in win.insp_body.text()
    # CROSS-TAB (do-now #2): a field's [[encounter]] scene is the field's ONE edge to a battle.toml -- the
    # resolved scene line is a clickable jump to the Battle tab (fail-soft: switches the tab, nudges if no
    # battle.toml authoring it is open).
    pdoc0 = win._doc("IC_ENT")
    pdoc0.data["encounter"] = {"scene": 67, "freq": 64}
    win.tree.setCurrentItem(win._member_items["IC_ENT"])
    eb = win.insp_body.text()
    assert 'href="goto:battle:67"' in eb and "BSC_EF_R007" in eb, eb
    win._inspect_link("goto:battle:67")
    assert win.tabs.currentWidget() is win.battle, "the encounter scene link jumps to the Battle tab"
    win.tabs.setCurrentWidget(win.doc_scroll)                 # restore for the rest of the inspector smoke
    del pdoc0.data["encounter"]
    win.tree.setCurrentItem(win._member_items["IC_ENT"])      # re-select with the probe encounter removed
    # do-now #1: the persistent doc-mode CHIP + breadcrumb stay truthful on EVERY tab (the indicator used to
    # update only on tree selection -> it lied on the 5 self-contained doc tabs). A campaign is open here.
    assert not win.crumb._chip.isHidden() and win.crumb._chip.text() == "FIELD", win.crumb._chip.text()
    _field_trail = list(win._content_crumbs)
    win.tabs.setCurrentWidget(win.battle)
    assert win.crumb._chip.text() == "BATTLE", "the Battle tab names itself as the edit target"
    win.tabs.setCurrentWidget(win.story_state)
    assert win.crumb._chip.text() == "SAVE", "the Save tab names itself"
    win.tabs.setCurrentWidget(win.build_deploy)
    assert win.crumb._chip.text() == "BUILD", "the Build & Deploy tab names itself"
    win.tabs.setCurrentWidget(win.import_field)
    assert win.crumb._chip.isHidden(), "Import shows project context but NO edit-target chip"
    win.tabs.setCurrentWidget(win.doc_scroll)                 # back to the Editor -> the field trail is RESTORED
    assert win.crumb._chip.text() == "FIELD" and win._content_crumbs == _field_trail, "content trail restored"
    # per-ENTITY summaries: probe an NPC (with an HTML-ish name for the escaping path) + a member gateway,
    # a real-FF9 gateway, and an out-of-campaign gateway, then clean up
    pdoc = win._doc("IC_ENT")
    pdoc.data.setdefault("npc", []).append({"name": "<b>Probe</b>", "preset": "vivi", "dialogue": "Hi, friend!"})
    pdoc.data.setdefault("gateway", []).extend([{"name": "door", "to": 30101, "entrance": 2},
                                                {"name": "real", "to": 100},      # a real FF9 field id
                                                {"name": "oob", "to": 99999}])
    win.tree.blockSignals(True)
    win._refresh_objects("IC_ENT")
    win.tree.blockSignals(False)
    win._select_object("IC_ENT", f"npc:{len(pdoc.data['npc']) - 1}")
    ni = win.insp_body.text()
    assert "vivi" in ni and "Hi, friend" in ni, ni
    assert "&lt;b&gt;Probe&lt;/b&gt;" in ni and "<b>Probe</b>" not in ni, "the body ESCAPES HTML in a name"
    assert win.insp_title.text() == "<b>Probe</b>", "the title is PLAIN text (literal name, not rendered)"
    assert win.insp_title.textFormat() == Qt.TextFormat.PlainText
    win._select_object("IC_ENT", "gateway:0")          # to=30101 == IC_COR's new_id -> resolves to the member
    assert 'href="goto:IC_COR"' in win.insp_body.text(), win.insp_body.text()
    win._select_object("IC_ENT", "gateway:1")          # to=100 -> a real FF9 field: named, NOT clickable, NOT broken
    gr = win.insp_body.text()
    assert "real field 100" in gr and "not in this campaign" not in gr, gr
    assert "goto:" not in gr.split("gateway")[-1], "a real-field destination is plain text, not a member link"
    win._select_object("IC_ENT", "gateway:2")          # to=99999 -> neither a member nor a real field
    assert "not in this campaign" in win.insp_body.text(), win.insp_body.text()
    # TIER-3: per-node validation from pure predicates, MIRRORING the build (so the Inspector never
    # contradicts Check). A VALID npc (vivi) is clean; an unknown archetype warns. (3rd arg = the member.)
    assert win._node_problems("npc", {"preset": "vivi"}, "IC_ENT") == [], "a known archetype is clean"
    assert win._node_problems("npc", {"preset": "vivvi"}, "IC_ENT"), "an unknown archetype warns"
    # a raw model id passes (resolve_npc_model accepts raw ints); model is IGNORED when a preset is set
    assert win._node_problems("npc", {"model": 999999}, "IC_ENT") == [], "a raw model id passes (build accepts it)"
    assert win._node_problems("npc", {"preset": "vivi", "model": 999999}, "IC_ENT") == [], "model ignored w/ preset"
    assert win._node_problems("event", {"give_item": ["NoSuchItem", 1]}, "IC_ENT"), "an unknown give_item warns"
    assert win._node_problems("event", {"remove_item": ["NoSuchItem", 1]}, "IC_ENT"), "an unknown remove_item warns"
    from ..flags import CHEST_FLAG_LO as _CFLO
    assert win._node_problems("event", {"set_flag": [_CFLO, 1]}, "IC_ENT"), "a reserved set_flag bit warns"
    assert win._node_problems("event", {"set_flag": [8520, 1]}, "IC_ENT") == [], "a safe-band flag is clean"
    # the build does int(scene): a non-numeric scene can't build -> warn; a numeric id passes
    assert win._node_problems("encounter", {"scene": "NoSuchScene"}, "IC_ENT"), "a non-numeric scene warns"
    assert win._node_problems("encounter", {"scene": 67}, "IC_ENT") == [], "a numeric scene id passes"
    # SCENE.TOML-AWARE reference checks: a choice/cutscene reference resolves against BOTH the field.toml
    # NPCs/markers AND the sibling scene.toml (Blender-owned) -- so a scene-placed entity isn't falsely flagged.
    pdoc.data["npc"].append({"name": "Ref", "preset": "vivi"})       # a field.toml NPC
    (d / "IC_ENT" / "IC_ENT.scene.toml").write_text(                 # a scene-ONLY NPC + marker
        '[[npc]]\nname = "SceneGuy"\n[[marker]]\nname = "spot1"\n', encoding="utf-8")
    assert win._node_problems("choice", {"npc": "Ref"}, "IC_ENT") == [], "a field.toml NPC reference is clean"
    assert win._node_problems("choice", {"npc": "SceneGuy"}, "IC_ENT") == [], "a scene.toml NPC reference is clean"
    assert win._node_problems("choice", {"npc": "Nope"}, "IC_ENT"), "a missing NPC reference warns"
    assert win._node_problems("cutscene", {"actor": "SceneGuy"}, "IC_ENT") == [], "a scene.toml actor is clean"
    assert win._node_problems("cutscene", {"actor": "Ghost"}, "IC_ENT"), "a missing actor warns"
    assert win._node_problems("cutscene", {"steps": [{"walk": "spot1"}]}, "IC_ENT") == [], "a scene marker walk is clean"
    # a walk/teleport target resolves against markers + NPCs + player/spawn (matching the build's _resolve_point)
    assert win._node_problems("cutscene", {"steps": [{"walk": "Ref"}]}, "IC_ENT") == [], "a walk to an NPC is clean"
    assert win._node_problems("cutscene", {"steps": [{"teleport": "@player"}]}, "IC_ENT") == [], "@player target clean"
    assert win._node_problems("cutscene", {"steps": [{"walk": "nomarker"}]}, "IC_ENT"), "an unknown walk target warns"
    assert win._node_problems("cutscene", {"steps": [{"walk": "10, -20"}]}, "IC_ENT") == [], "coords aren't a name ref"
    # a 'path' route validates EACH string waypoint the same way (mirrors build.py:1103); coord elems pass
    assert win._node_problems("cutscene", {"steps": [{"path": ["spot1", "Ref", [10, -20]]}]}, "IC_ENT") == [], \
        "a path of known waypoints + coords is clean"
    assert win._node_problems("cutscene", {"steps": [{"path": ["spot1", "sopt2"]}]}, "IC_ENT"), "a typo'd waypoint warns"
    (d / "IC_ENT" / "IC_ENT.scene.toml").unlink()                    # clean up the scene sibling
    pdoc.data["npc"].pop()                                           # drop the Ref NPC
    # a malformed inline entry (a bare string where a table is expected) inspects safely, no crash
    pdoc.data.setdefault("npc", []).append("not-a-table")
    ml = win._inspect_object("IC_ENT", f"npc:{len(pdoc.data['npc']) - 1}")
    assert any("malformed" in s for s in ml), ml
    pdoc.data["npc"].pop()
    # the per-node warning surfaces in the live Inspector body, and the field rolls up a health badge
    pdoc.data["npc"].append({"name": "Typo", "preset": "vivvi"})
    win.tree.blockSignals(True)
    win._refresh_objects("IC_ENT")
    win.tree.blockSignals(False)
    win._select_object("IC_ENT", f"npc:{len(pdoc.data['npc']) - 1}")
    assert "unknown archetype" in win.insp_body.text(), win.insp_body.text()
    assert win._count_node_problems("IC_ENT") >= 1
    win.tree.setCurrentItem(win._member_items["IC_ENT"])
    assert "object(s) with issues" in win.insp_body.text(), win.insp_body.text()
    pdoc.data["npc"].pop()                             # drop the Typo probe
    pdoc.data["npc"].pop()                             # clean up the probes (and re-baseline)
    pdoc.data.pop("gateway", None)
    win.tree.blockSignals(True)
    win._refresh_objects("IC_ENT")
    win.tree.blockSignals(False)
    win._mark_clean("IC_ENT")
    win.tree.setCurrentItem(win._member_items["IC_ENT"])
    # the unsaved-dot icon must not resize tree rows (uniform height + small icon -> no jump on save)
    assert win.tree.uniformRowHeights() and win.tree.iconSize() == QSize(12, 12)
    # (b) the Editor tab reflects what's open; placeholder resets it
    et = lambda: win.tabs.tabText(win.tabs.indexOf(win.doc_scroll))
    win._open_editor("IC_ENT", "field", "field")
    assert et() == "Editor — Field", et()
    win._open_editor("IC_ENT", "object", "cutscene")
    assert et() == "Editor — Cutscene", et()
    win._doc_placeholder("nothing")
    assert et() == "Editor", "placeholder resets the Editor tab title"
    # (c) the Save button greys out when there's nothing to save, enables on edit
    win._mark_clean("IC_ENT")
    win._open_editor("IC_ENT", "field", "field")
    assert win._save_btn is not None and not win._save_btn.isEnabled(), "Save is greyed on a clean form"
    win._touch("IC_ENT")
    assert win._save_btn.isEnabled(), "Save enables when there are unsaved changes"
    win._mark_clean("IC_ENT")
    assert not win._save_btn.isEnabled(), "Save greys again after saving"
    # (c2) Reset (opposite of Save): greyed when clean; reverts the form's unsaved edits to the last save
    win._mark_clean("IC_ENT")
    win._open_editor("IC_ENT", "field", "field")
    assert win._reset_btn is not None and not win._reset_btn.isEnabled(), "Reset is greyed on a clean form"
    saved_id = win._doc("IC_ENT").data["field"]["id"]
    win._save_ctx["getters"]["id"].__self__.setText("999777")   # a widget edit -> touched -> Reset enables
    assert win._reset_btn.isEnabled() and "IC_ENT" in win._touched
    win._reset_active()
    assert win._save_ctx["getters"]["id"]() == str(saved_id), "Reset re-mounted with the saved id"
    assert "IC_ENT" not in win._touched, "Reset cleared the in-progress flag"
    win._mark_clean("IC_ENT")                          # reset a COMMITTED-but-unsaved (in-doc) change too
    win._doc("IC_ENT").data["field"]["area"] = 99
    win._open_editor("IC_ENT", "field", "field")
    win._reset_active()
    assert win._doc("IC_ENT").data["field"]["area"] != 99, "Reset reverted the committed-unsaved change"
    # (4) live validation: a bad value flags its field (validate() returns the invalid count); also proves
    # the hint is parented before setVisible (no parentless top-level flash -- the build-time flicker fix)
    from PySide6.QtWidgets import QLineEdit as _QLE2
    fw2, fg2 = build_form(forms.FIELD_SPEC,
                          forms.entity_to_values(forms.FIELD_SPEC, {"id": 4003, "name": "R", "area": 11}), win.pal)
    assert fw2.validate() == 0, "loaded values are valid"
    id_edit = fg2["id"].__self__                       # the QLineEdit behind the id getter
    assert isinstance(id_edit, _QLE2)
    id_edit.setText("abc")                             # type a non-numeric id -> live validate flags it
    assert fw2.validate() == 1, "a non-numeric id is flagged invalid"
    # review fix 1: merely VIEWING a node whose BOOL equals its default (once=true) must NOT dirty the doc
    win._doc("IC_ENT").data["event"] = [{"name": "chest", "message": "hi", "once": True}]
    win._mark_clean("IC_ENT")
    win._open_editor("IC_ENT", "object", "event:0")    # view the event (no edit)
    assert win._commit_active() is True                # navigate-away folds it...
    assert win._doc("IC_ENT").data["event"][0].get("once") is True, "viewing kept the explicit once=true"
    assert "IC_ENT" not in win._dirty_members(), "viewing an event with once=true did not dirty the field"
    win._doc("IC_ENT").data.pop("event", None)
    win._mark_clean("IC_ENT")
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
    edit_box[0].setPlainText("a\\nb")                                        # a typed LITERAL backslash-n...
    assert _pg["dialogue"]() == "a\nb"                                       # ...is normalized to a real newline

    # Phase 4b: the cutscene + choice sub-editors mount over a doc with steps/options
    edoc = win._doc("IC_ENT")
    edoc.data["cutscene"] = {"once": True, "steps": [{"say": "Hello"}, {"wait": 30}]}
    edoc.data["choice"] = [{"npc": "Guard", "prompt": "Well?", "options": [{"text": "Yes"}, {"text": "No"}]}]
    win._mount_cutscene("IC_ENT")
    # (any(...==2), not [0]: deleteLater'd widgets from earlier mounts linger without a running event loop)
    step_lists = win.doc_host.findChildren(QListWidget)
    assert any(lst.count() == 2 for lst in step_lists), "cutscene steps list shows both steps"
    # the cutscene 'say' step is dialogue -> a multi-line value box (default type is 'say')
    say_box = [p for p in win.doc_host.findChildren(QPlainTextEdit) if not p.isReadOnly()]
    assert say_box, "cutscene 'say' step has a multi-line value box"
    win._mount_choice("IC_ENT", 0)
    opt_lists = win.doc_host.findChildren(QListWidget)
    assert any(lst.count() == 2 for lst in opt_lists), "choice options list shows both options"
    # the catalog picker reuses the infohub spine (archetype search finds 'vivi') -- no exec(), just _refresh
    from .forms_qt import CatalogPicker
    pk = CatalogPicker(win, ["archetype", "creature"], "vivi", win.plan, win.pal)
    assert "vivi" in [e.name for e in pk._entries], [e.name for e in pk._entries]
    # the encounter battle-scene picker: a 'scene' catalog over an INT field returns the entry's ID (want_id),
    # so a picked scene lands an INT-parseable scene id in the form (not its name)
    sk = CatalogPicker(win, ["scene"], "", win.plan, win.pal, want_id=True)
    assert sk._entries and all(e.kind == "scene" for e in sk._entries), "scene catalog lists battle scenes"
    sk.lst.setCurrentRow(0)
    sk._ok()
    assert sk.result == str(sk._entries[0].ident) and int(sk.result) == sk._entries[0].ident, sk.result
    # the Info Hub LIBRARY (sectioned, replacing the all-in-one flat browse): a category sidebar with
    # counts, a per-section searchable list, and a rich detail pane (infohub.detail, not just the summary)
    from .forms_qt import CatalogLibrary
    lib = CatalogLibrary(win, win.plan, win.pal)
    cat_labels = [lib.cats.item(i).text() for i in range(lib.cats.count())]
    assert cat_labels[0].startswith("All  ("), cat_labels
    assert any(l.startswith("Archetypes") for l in cat_labels) and any(l.startswith("Items") for l in cat_labels)
    assert any(l.startswith("Campaign fields") for l in cat_labels), "campaign sections show when one is open"
    # row 0 = 'All' -> the whole catalog (the old >300 floor; no cap)
    assert lib._kind is None and len(lib._entries) > 300, len(lib._entries)
    # selecting the Archetypes section filters to that ONE kind; the search box narrows WITHIN it
    arch = next(i for i in range(lib.cats.count()) if lib.cats.item(i).text().startswith("Archetypes"))
    lib.cats.setCurrentRow(arch)
    assert lib._entries and all(e.kind == "archetype" for e in lib._entries), "a section is one kind"
    nfull = len(lib._entries)
    lib.q.setText("vivi")
    assert lib._entries and len(lib._entries) < nfull and any(e.name == "vivi" for e in lib._entries)
    # the detail pane renders the RICH record (facts + animations), not just the one-line summary
    lib.lst.setCurrentRow(next(i for i, e in enumerate(lib._entries) if e.name == "vivi"))
    dt = lib.detail.toPlainText().lower()
    assert "vivi" in dt and "model" in dt and "anim" in dt, dt[:200]
    # Copy name + Copy snippet reach the clipboard (snippet = a ready [[npc]] block)
    lib._copy_name()
    assert QApplication.clipboard().text() == "vivi"
    lib._copy_snippet()
    snip = QApplication.clipboard().text()
    assert "[[npc]]" in snip and "vivi" in snip, snip
    # the detail pane renders EVERY kind without error (item stats / storyflag registry / a campaign field)
    for sect_label in ("Items", "Story flags", "Campaign fields"):
        srow = next((i for i in range(lib.cats.count()) if lib.cats.item(i).text().startswith(sect_label)), None)
        if srow is None:
            continue
        lib.cats.setCurrentRow(srow)
        if lib._entries:
            lib.lst.setCurrentRow(0)
            assert lib.detail.toPlainText().strip(), f"{sect_label} detail rendered empty"
    # the Help button's glossary explains every section (so 'archetype' etc. is self-explanatory in-app)
    from .forms_qt import _hub_help_html
    hh = _hub_help_html()
    assert "Archetypes" in hh and "[[npc]] archetype" in hh and "Props" in hh and "Copy snippet" in hh, hh[:120]
    assert hasattr(lib, "_show_help")
    # with NO campaign open: the campaign-own sections are absent, the static catalogs remain
    lib2 = CatalogLibrary(win, None, win.pal)
    nolabels = [lib2.cats.item(i).text() for i in range(lib2.cats.count())]
    assert not any(l.startswith("Campaign") for l in nolabels), nolabels
    assert any(l.startswith("Archetypes") for l in nolabels) and lib2.cats.count() >= 5, nolabels
    assert "Browse catalog (Info Hub)" in [e[0] for e in win._command_index()]
    # the toolbar Info Hub button is tinted the violet 'info' hue (so the catalog popup stands out)
    assert win._hub_btn is not None and win.pal["help"] in win._hub_btn.styleSheet()

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
    # review fix 2: reopening a DIFFERENT file that shares a [field] name must not carry the old form's values
    da = d / "DUP_A.field.toml"
    da.write_text('[field]\nid = 4400\nname = "DUP"\narea = 11\n\n[[npc]]\nname = "Alpha"\n', encoding="utf-8")
    db = d / "DUP_B.field.toml"
    db.write_text('[field]\nid = 4401\nname = "DUP"\narea = 11\n\n[[npc]]\nname = "Beta"\n', encoding="utf-8")
    assert win.open_field(da)
    win._open_editor("DUP", "object", "npc:0")             # mount A's NPC form (stale _save_ctx if not cleared)
    assert win.open_field(db)                              # open B (same field name 'DUP')
    assert win._doc("DUP").data["npc"][0]["name"] == "Beta", "B's NPC is intact (no stale write from A)"
    assert "DUP" not in win._dirty_members(), "a fresh open of B (same name) is clean"

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

    # BATTLE DOCUMENT (Phase 3): open a battle.toml, edit the encounter-first nodes, save round-trips
    import tomllib as _tl
    bdir = d / "fight"
    bdir.mkdir()
    (bdir / "BBG_B013.fbx").write_text("dummy", encoding="utf-8")          # so validate_battle's fbx check passes
    btoml = bdir / "battle.toml"
    btoml.write_text('[battlemap]\nbbg = "BBG_B013"\nfbx = "BBG_B013.fbx"\n\n'
                     '[scene]\nmonster_count = 2\n\n[[scene.enemy]]\nslot = 0\nhp = 500\n', encoding="utf-8")
    assert win.battle.load(str(btoml))
    # do-now #6: opening a battle.toml on the Battle tab PRE-AIMS Build & Deploy at it (cross-tab handoff)
    assert Path(win.build_deploy.path.text()) == btoml, win.build_deploy.path.text()
    assert win.battle._nodes[0][0] == "battlemap" and win.battle._nodes[1][0] == "scene"
    assert any(k == "enemy" for k, _ in win.battle._nodes), win.battle._nodes
    win.battle.nodes.setCurrentRow(0)                                      # the Map form mounts
    assert win.battle._ctx["kind"] == "battlemap"
    erow = next(i for i, (k, _) in enumerate(win.battle._nodes) if k == "enemy")
    win.battle.nodes.setCurrentRow(erow)                                  # drill into the enemy slot
    assert win.battle._ctx["kind"] == "enemy"
    win.battle._ctx["getters"]["hp"] = lambda: "777"                      # as if typed into HP
    win.battle._save()
    assert _tl.loads(btoml.read_text(encoding="utf-8"))["scene"]["enemy"][0]["hp"] == 777   # round-trips to disk
    assert win.battle.nodes.currentRow() == erow and win.battle.del_btn.isEnabled()   # Save keeps the row + Remove armed
    win.battle._add_enemy()                                               # a new [[scene.enemy]] at the next slot
    assert len(win.battle._enemies()) == 2 and win.battle._enemies()[1]["slot"] == 1
    # Formation form: the encounter-rules STRLIST + a FLOAT camera tweak round-trip (keeping the enemy list)
    srow = next(i for i, (k, _) in enumerate(win.battle._nodes) if k == "scene")
    win.battle.nodes.setCurrentRow(srow)
    assert win.battle._ctx["kind"] == "scene"
    win.battle._ctx["getters"]["flags"] = lambda: "no_escape"
    win.battle._ctx["getters"]["camera_zoom"] = lambda: "1.5"             # a FLOAT field
    win.battle._save()
    _bscene = _tl.loads(btoml.read_text(encoding="utf-8"))["scene"]
    assert _bscene["flags"] == ["no_escape"] and _bscene["camera_zoom"] == 1.5
    assert len(_bscene["enemy"]) == 2                                     # the enemy list survived the scene save
    # AI phase (boss enrage): add a [[scene.ai_phase]], edit an attack index, save round-trips (note the 'else' key)
    win.battle._add_ai_phase()
    assert any(k == "ai_phase" for k, _ in win.battle._nodes) and win.battle._ctx["kind"] == "ai_phase"
    win.battle._ctx["getters"]["then"] = lambda: "3"
    win.battle._save()
    _bap = _tl.loads(btoml.read_text(encoding="utf-8"))["scene"]["ai_phase"][0]
    assert _bap == {"entry": 1, "tag": 5, "stat": "hp", "below": 0.5, "then": 3, "else": 0}, _bap
    win.battle._check()                                                   # validate_battle -> Problems (no crash)
    # Same-length patches (cite-an-offset): add an [[scene.ai_patch]] + a [[scene.seq_patch]], round-trip to disk
    win.battle._pick_patch_kind = lambda: "ai_patch"                      # stub the AI/seq chooser dialog
    win.battle._add_patch()
    assert any(k == "ai_patch" for k, _ in win.battle._nodes) and win.battle._ctx["kind"] == "ai_patch"
    win.battle._ctx["getters"].update(at=lambda: "1234", old=lambda: "50", new=lambda: "80")
    win.battle._save()
    assert _tl.loads(btoml.read_text(encoding="utf-8"))["scene"]["ai_patch"][0] == {"at": 1234, "old": 50, "new": 80}
    win.battle._pick_patch_kind = lambda: "seq_patch"
    win.battle._add_patch()
    assert win.battle._ctx["kind"] == "seq_patch"
    win.battle._ctx["getters"].update(at=lambda: "88", old=lambda: "10", new=lambda: "20", seq=lambda: "3")
    win.battle._save()
    assert _tl.loads(btoml.read_text(encoding="utf-8"))["scene"]["seq_patch"][0] == \
        {"at": 88, "old": 10, "new": 20, "seq": 3}
    # this battle.toml is a bare-BBG OVERRIDE (no forked scene/), so the Browse-sites picker degrades to None
    assert win.battle._donor_patch_sites("ai_patch") is None and win.battle._donor_patch_sites("seq_patch") is None
    # Browse-sites glue: a picked donor site fills Offset (at) + the OLD guard, KEEPING the user's typed `new`
    # (the commit-before-remount path that must not let the stale form widgets clobber the filled offset)
    win.battle._donor_patch_sites = lambda kind: [(1000, 42, "entry1/tag5 Wait arg0", 0, 255)]   # stub the donor read
    win.battle._choose = lambda _title, rows: rows[0]                     # stub the picker dialog -> first site
    arow = next(i for i, (k, _) in enumerate(win.battle._nodes) if k == "ai_patch")
    win.battle.nodes.setCurrentRow(arow)                                  # mount the ai_patch form
    win.battle._ctx["getters"]["new"] = lambda: "80"                      # the user's typed value to preserve
    win.battle._browse_sites("ai_patch")
    assert win.battle.data["scene"]["ai_patch"][0] == {"at": 1000, "old": 42, "new": 80}
    assert win.battle._ctx["kind"] == "ai_patch"                          # remounted on the same patch form
    # Player/ability tuning branch (mod-global): add a [[character]] row, edit a stat, save round-trips
    win.battle._pick_player_table = lambda: "character"                   # stub the picker dialog
    win.battle._add_player()
    assert win.battle.data["character"][-1] == {"character": "Zidane"}
    assert any(k == "character" for k, _ in win.battle._nodes), win.battle._nodes
    assert win.battle._ctx["kind"] == "character"                         # landed on the new row's form
    win.battle._ctx["getters"]["strength"] = lambda: "99"                 # as if typed into Strength
    win.battle._save()
    _bsaved = _tl.loads(btoml.read_text(encoding="utf-8"))
    assert _bsaved["character"][0] == {"character": "Zidane", "strength": 99}, _bsaved.get("character")
    # the saved battle.toml uses REAL sections (not the field.toml inline `scene = {...}` collision) — readable + round-trips
    _btext = btoml.read_text(encoding="utf-8")
    assert "[scene]" in _btext and "[[scene.enemy]]" in _btext and "[[scene.ai_phase]]" in _btext
    assert "scene = {" not in _btext, _btext[:200]
    # Check must NOT persist: add an enemy in-memory, Check, the on-disk enemy count is unchanged (Save is the only writer)
    _disk_before = len(_tl.loads(_btext)["scene"]["enemy"])
    win.battle._add_enemy()
    win.battle._check()
    assert len(_tl.loads(btoml.read_text(encoding="utf-8"))["scene"]["enemy"]) == _disk_before, "Check wrote an unsaved Add"
    win.battle._enemies().pop()                                          # drop the unsaved scratch enemy before the delete tests
    win.battle._rebuild_nodes()
    # Remove selected: every list row (player / scene sub-table / enemy) is deletable; Map/Formation are not.
    win.battle._confirm_delete = lambda _label: True                     # stub the confirm dialog -> Yes
    win.battle.nodes.setCurrentRow(0)                                    # Map (a singleton) — not removable
    assert not win.battle.del_btn.isEnabled()
    crow = next(i for i, (k, _) in enumerate(win.battle._nodes) if k == "character")
    win.battle.nodes.setCurrentRow(crow)
    assert win.battle.del_btn.isEnabled()                               # a list row arms Remove
    win.battle._delete_selected()
    assert "character" not in win.battle.data                           # the emptied top-level [[character]] is popped
    assert not any(k == "character" for k, _ in win.battle._nodes)
    assert not win.battle.del_btn.isEnabled()                           # landed on Map (no sibling left) -> disabled
    prow = next(i for i, (k, _) in enumerate(win.battle._nodes) if k == "ai_patch")
    win.battle.nodes.setCurrentRow(prow)
    win.battle._delete_selected()
    assert "ai_patch" not in win.battle.data["scene"]                   # the emptied [scene] sub-table is popped
    e0 = next(i for i, (k, _) in enumerate(win.battle._nodes) if k == "enemy")
    win.battle.nodes.setCurrentRow(e0)
    win.battle._delete_selected()
    assert len(win.battle._enemies()) == 1                              # a non-empty list keeps its remaining rows
    win.battle._save()                                                  # the removals persist to disk
    _adel = _tl.loads(btoml.read_text(encoding="utf-8"))
    assert "character" not in _adel and "ai_patch" not in _adel.get("scene", {})
    assert len(_adel["scene"]["enemy"]) == 1
    # Fork battle: the battle-import argv + auto-open wiring (stub the runner -> no subprocess / install)
    forked = {}

    def _fake_battle_run(argv, *, cwd=None, on_finished=None, **_kw):
        forked["argv"] = list(argv)
        fout = Path(argv[argv.index("--out") + 1])
        fout.mkdir(parents=True, exist_ok=True)
        (fout / "battle.toml").write_text('[battlemap]\nbbg = "BBG_B042"\n', encoding="utf-8")
        if on_finished:
            on_finished(0)                                               # a clean battle-import -> auto-open
        return True

    win.battle._run, win.battle.kit = _fake_battle_run, d
    win.battle._run_fork("BBG_B042", str(d / "forked_fight"), fork_scene="EF_R007")
    assert forked["argv"][3:] == ["battle-import", "BBG_B042", "--out", str(d / "forked_fight"),
                                  "--fork-scene", "EF_R007"], forked["argv"]
    assert win.battle.path == (d / "forked_fight" / "battle.toml")        # auto-opened the forked result
    assert win.battle.data["battlemap"]["bbg"] == "BBG_B042"
    assert Path(win.build_deploy.path.text()) == d / "forked_fight" / "battle.toml", "fork pre-aims Build & Deploy"
    # Fork-dialog Browse: an install-gated list -> _choose -> fills the field; read once, then CACHED
    from PySide6.QtWidgets import QLineEdit as _QLE
    _calls = []

    def _bbg_loader():
        _calls.append(1)
        return ["BBG_B013", "BBG_B042"]

    win.battle._choose = lambda _title, rows: rows[0] if rows else None
    _bbg_edit = _QLE()
    win.battle._pick_install_list("Battle backgrounds", _bbg_loader, _bbg_edit, "bbg")
    win.battle._pick_install_list("Battle backgrounds", _bbg_loader, _bbg_edit, "bbg")   # cached: loader NOT re-run
    assert _bbg_edit.text() == "BBG_B013" and len(_calls) == 1, (_bbg_edit.text(), _calls)

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
    # journey kind: a bare journeys.toml auto-detects -> the deploy_journey.py orchestrator (slice 2). The
    # default is a SAFE dry-run (playbook only); --apply / --wire-newgame / --apply-links are opt-in radios.
    jbd = d / "bd_journey.toml"
    jbd.write_text('[hub]\nname = "BD Hub"\nid = 4600\n\n[[journey]]\nid = "solo"\nentry = 4100\n', encoding="utf-8")
    bd.set_target(jbd)
    assert bd.kind == "journey" and bd.manifest is not None
    # isHidden() reflects the explicit setVisible() state (the window isn't shown in headless smoke, so
    # isVisible() is False for every child) -> the journey panel is the one un-hidden by _render_kind.
    assert not bd.journey_box.isHidden() and bd.field_box.isHidden(), "the journey panel shows for a journeys.toml"
    bd.rb_jour_preview.setChecked(True)
    bd.on_go()
    assert any("deploy_journey.py" in a for a in launched[-1]) and "--apply" not in launched[-1], launched[-1]
    bd.rb_jour_apply.setChecked(True)
    bd._update_journey_hint()
    # New-Game landing = a 3-way radio (none / hub / opening entry), enabled only for the one-shot deploy
    assert bd.ng_group.isEnabled(), "New-Game radios enable only for the one-shot deploy"
    assert bd.rb_ng_entry.isEnabled(), "single-journey manifest -> 'straight into the opening' is available"
    bd.rb_ng_hub.setChecked(True)                              # wire -> hub menu
    bd.on_go()
    assert "--apply" in launched[-1] and launched[-1][-2:] == ["--newgame", "hub"], launched[-1]
    bd.rb_ng_entry.setChecked(True)                            # wire -> straight into the opening
    bd.on_go()
    assert launched[-1][-2:] == ["--newgame", "entry"], launched[-1]
    bd.rb_ng_none.setChecked(True)                             # no wiring
    bd.on_go()
    assert "--apply" in launched[-1] and "--newgame" not in launched[-1], launched[-1]
    bd.rb_jour_links.setChecked(True)
    bd._update_journey_hint()
    assert not bd.ng_group.isEnabled(), "New-Game radios grey out for links-only"
    bd.on_go()
    assert "--apply-links" in launched[-1] and "--apply" not in launched[-1], launched[-1]
    # a MULTI-journey manifest -> 'straight into the opening' is disabled (no single opening to land in)
    jbd2 = d / "bd_journey2.toml"
    jbd2.write_text('[hub]\nname = "H2"\nid = 4600\n\n[[journey]]\nid = "a"\nentry = 4100\n\n'
                    '[[journey]]\nid = "b"\nentry = 4200\n', encoding="utf-8")
    bd.set_target(jbd2)
    bd.rb_jour_apply.setChecked(True)
    bd._update_journey_hint()
    assert bd.ng_group.isEnabled() and not bd.rb_ng_entry.isEnabled(), "multi-journey -> entry-wiring disabled"
    bd.set_target(jbd)                                         # restore the single-journey target for later steps
    bd._check_journey(str(jbd))                                 # in-process journey lint (no crash)
    # the journey revert resolves the MOST RECENT of revert_journey.py / revert_journey_links.py (or None) --
    # robust to whatever real reverts the repo happens to have; exercise the on_revert journey branch headless.
    rj = jobs.revert_journey_argv(REPO)
    assert rj is None or rj[-1].replace("\\", "/").endswith(("scroll_out/revert_journey.py",
                                                             "scroll_out/revert_journey_links.py")), rj
    bd._info = lambda *a: None                                   # don't pop a modal box in headless
    bd.on_revert()                                              # journey revert branch: no-op or captured argv, no crash
    # NEW GAME ENTRY (hub-less): CREATE the field-70 override from stock (works on a clean install / fresh fork)
    bd.newgame_id.setText("4100")
    bd.on_set_newgame()
    assert any("wire_newgame_from_stock.py" in a for a in launched[-1]) and "4100" in launched[-1], launched[-1]
    bd.newgame_id.setText("not-a-number")                        # a bad id is refused (warn, no launch)
    _before = list(launched[-1])
    bd._warn = lambda *a: None
    bd.on_set_newgame()
    assert launched[-1] == _before, "a non-numeric New-Game id launches nothing"
    bd.on_revert_newgame()                                       # revert branch: no-op (no retarget) or captured

    imp = win.import_field
    icap = []
    imp._run = lambda argv, **kw: (icap.append(list(map(str, argv))) or True)
    imp.field.setText("100")
    imp.fid.setText("4003")
    imp.name.setText("MYFORK")                                   # the one field that flows to argv in both modes
    imp.out.setText(str(d / "imp_out"))                          # a temp out folder (don't touch the repo)
    # DEFAULT mode = verbatim (the recommended fork): the scene/carry boxes are HIDDEN (irrelevant), art pinned Native
    assert imp.art_box.isHidden() and imp.carry_box.isHidden() and imp.art_native.isChecked(), "verbatim default"
    imp.on_import()
    assert icap[-1][:5] == [sys.executable, "-m", "ff9mapkit", "import", "100"], icap[-1]
    assert "--verbatim" in icap[-1] and "--graft-player-funcs" not in icap[-1], icap[-1]
    assert "VERBATIM" in imp.mode_chip.text(), imp.mode_chip.text()  # the live resolved-mode chip names what runs
    _ni = icap[-1].index("--name")
    assert icap[-1][_ni:_ni + 2] == ["--name", "MYFORK"], icap[-1]   # Name field -> argv passthrough
    imp.mode_authorable.setChecked(True)                         # RE-AUTHORABLE: the boxes appear
    assert not imp.art_box.isHidden() and not imp.carry_box.isHidden(), "authorable shows scene/carry"
    assert "RE-AUTHORABLE" in imp.mode_chip.text(), imp.mode_chip.text()
    imp.art_editable.setChecked(True)
    imp.carry_text.setChecked(True)
    imp.on_import()
    assert "--verbatim" not in icap[-1] and "--editable" in icap[-1] and "--carry-text" in icap[-1], icap[-1]
    # import-verbatim-bug fix: a 'Walk as' swap FORCES verbatim even in Re-authorable mode -> the editable
    # scene / carry boxes HIDE (you can't pick 'Editable scene' and silently get verbatim) + the chip says so.
    imp.swap_player.setCurrentText("vivi")
    assert imp.art_box.isHidden() and imp.carry_box.isHidden(), "a Walk-as hides the editable/carry options"
    assert "VERBATIM" in imp.mode_chip.text() and "Walk as" in imp.mode_chip.text(), imp.mode_chip.text()
    imp.on_import()
    assert "--verbatim" in icap[-1] and "--swap-player" in icap[-1] and "--editable" not in icap[-1], icap[-1]
    imp.swap_player.setCurrentText("")                           # clearing Walk-as restores the editable options
    assert not imp.art_box.isHidden() and "RE-AUTHORABLE" in imp.mode_chip.text(), imp.mode_chip.text()
    imp.mode_verbatim.setChecked(True)                           # back to verbatim: re-hide + re-pin Native
    assert imp.art_box.isHidden() and imp.art_native.isChecked(), "verbatim re-pins Native"
    # REPAINT a native fork (the atlas<->layers round-trip): the native imports above pre-aimed the box
    assert imp.rp_unpack_btn in imp._buttons and imp.rp_pack_btn in imp._buttons   # _busy disables them
    assert imp.rp_proj.text() == str((d / "imp_out").resolve()), "a native import pre-aims the repaint box"
    _rp_warn, _rw0 = [], imp._warn
    imp._warn = lambda *a: _rp_warn.append(a)
    imp.rp_proj.setText("")
    _m = len(icap)
    imp.on_repaint_unpack()                                      # empty-project GUARD: warn, start no job
    assert _rp_warn and len(icap) == _m, "empty repaint project starts no job"
    imp._warn = _rw0
    imp.rp_proj.setText(str(d / "nat_proj"))
    imp.on_repaint_unpack()
    assert icap[-1][3:] == ["repaint-native", str((d / "nat_proj").resolve())], icap[-1]
    imp.on_repaint_pack()
    assert icap[-1][3:] == ["repaint-native", str((d / "nat_proj").resolve()), "--pack"], icap[-1]
    # FORK A REGION (import-chain, the disc-1 workflow)
    assert imp.dryrun_btn in imp._buttons and imp.fork_region_btn in imp._buttons   # _busy disables them
    imp.seeds.setText("")                                        # empty-seeds GUARD: no job may start
    _rw, _warned = imp._warn, []
    imp._warn = lambda *a: _warned.append(a)
    _n = len(icap)
    imp.on_region_dryrun()
    assert _warned and len(icap) == _n, "blank seeds must not launch a job"
    imp._warn = _rw
    imp.seeds.setText("300")                                     # dry-run (no --out)
    imp.on_region_dryrun()
    assert icap[-1][3] == "import-chain" and icap[-1][4] == "300", icap[-1]
    assert "--out" not in icap[-1] and "--whole-zone" in icap[-1] and "--verbatim" in icap[-1], icap[-1]
    imp.rg_out.setText(str(d / "rg_out"))                        # fork (with --out + explicit id-base/prefix)
    imp.rg_idbase.setText("6500")
    imp.rg_prefix.setText("RG")
    imp.on_fork_region()
    assert "--out" in icap[-1] and "--fresh-ids" not in icap[-1], icap[-1]
    assert icap[-1][icap[-1].index("--name-prefix") + 1] == "RG", icap[-1]
    assert icap[-1][icap[-1].index("--id-base") + 1] == "6500", icap[-1]
    # CLUSTER SCOPE: picking a catalog region forks just THAT story-state visit (--ids), not the whole zone;
    # a hand-edit of the Seeds box drops the cluster -> whole-zone fallback for the typed seeds.
    from .. import refarc as _RA
    _cat = _RA.load_region_catalog()
    _clk = next((a.key for a in _cat.arcs if a.members), None)
    if _clk:
        imp._apply_region_selection(_cat, [_clk])
        assert imp._region_ids, "catalog pick sets cluster ids"
        imp.on_region_dryrun()
        assert "--ids" in icap[-1] and "--whole-zone" not in icap[-1], icap[-1]
        imp.seeds.setText("999"); imp.seeds.textEdited.emit("999")   # a hand-edit fires textEdited -> clears cluster
        assert imp._region_ids is None, "textEdited wiring must drop the cluster"
        imp.on_region_dryrun()
        assert "--whole-zone" in icap[-1] and "--ids" not in icap[-1], icap[-1]
    imp.on_find()
    assert "list-fields" in icap[-1], icap[-1]

    # UNDO / REDO -- a fresh loose field gives a clean history to exercise the stacks
    uf = d / "UNDOTEST.field.toml"
    uf.write_text('[field]\nid = 4700\nname = "U1"\narea = 11\n\n'
                  '[[npc]]\nname = "Aaa"\npreset = "vivi"\n[[npc]]\nname = "Bbb"\npreset = "vivi"\n',
                  encoding="utf-8")
    assert win.open_field(uf)
    assert win._undo_stack == [] and win._redo_stack == [], "a fresh open clears the undo history"
    assert not win.act_undo.isEnabled() and not win.act_redo.isEnabled()
    ulabels = [e[0] for e in win._command_index()]
    assert "Undo" in ulabels and "Redo" in ulabels, ulabels
    # (1) edit a form value + cross the nav/save boundary -> one undo step; undo reverts, redo re-applies
    win._open_editor("U1", "field", "field")
    idw = win._save_ctx["getters"]["id"].__self__                  # the id QLineEdit behind the field form
    assert idw.text() == "4700"
    idw.setText("4999")
    assert win._commit_active_ck() is True                         # the nav/save boundary folds + checkpoints
    assert win._doc("U1").data["field"]["id"] == 4999 and len(win._undo_stack) == 1
    assert win.act_undo.isEnabled() and win.act_undo.toolTip().startswith("Undo edit field")
    win._undo()
    assert win._doc("U1").data["field"]["id"] == 4700, "undo reverted the field id"
    assert win._redo_stack and win.act_redo.isEnabled() and not win.act_undo.isEnabled()
    win._redo()
    assert win._doc("U1").data["field"]["id"] == 4999 and not win._redo_stack, "redo re-applied the id"
    # (1b) review fix: a PENDING (uncommitted) form edit is folded into history by Undo, not silently lost
    win._open_editor("U1", "field", "field")
    win._save_ctx["getters"]["id"].__self__.setText("4321")       # typed, NOT committed (no nav/save)
    win._undo()                                                   # Undo commits the pending edit, then undoes it
    assert win._doc("U1").data["field"]["id"] == 4999, "Undo reverted the just-typed (uncommitted) id"
    win._redo()
    assert win._doc("U1").data["field"]["id"] == 4321, "the folded pending edit is recoverable via Redo"
    win._undo()                                                   # leave the id back at 4999 for the next steps
    assert win._doc("U1").data["field"]["id"] == 4999
    # (2) add an entity -> undo removes it, redo re-adds (the structural ops are checkpointed)
    n0 = len(win._doc("U1").data["npc"])
    win._add_list_item("U1", "npc")
    assert len(win._doc("U1").data["npc"]) == n0 + 1
    win._undo()
    assert len(win._doc("U1").data.get("npc", [])) == n0, "undo removed the added NPC"
    win._redo()
    assert len(win._doc("U1").data["npc"]) == n0 + 1, "redo restored the added NPC"
    # (3) delete an entity -> undo restores it (a delete writes disk + marks clean; undo makes it dirty again)
    win._confirm = lambda *a: True
    nd = len(win._doc("U1").data["npc"])
    win._delete_object("U1", "npc", single=False, idx=nd - 1, label="NPC")
    assert len(win._doc("U1").data["npc"]) == nd - 1
    win._undo()
    assert len(win._doc("U1").data["npc"]) == nd, "undo restored the deleted NPC"
    assert "U1" in win._dirty_members(), "an undone delete is dirty vs the saved file (Save persists it)"
    # (4) redo INVALIDATION: a fresh edit after an undo clears the redo branch
    assert win._redo_stack, "the undone delete is redoable"
    win._add_list_item("U1", "marker")                            # a NEW edit...
    assert win._redo_stack == [], "a new edit invalidates the redo branch"
    # (5) a cutscene STEP add records an undo step (the live sub-editor closures are checkpointed too)
    win._mount_cutscene("U1")
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QComboBox as _QCB, QPushButton as _QPB
    QApplication.instance().sendPostedEvents(None, QEvent.Type.DeferredDelete)   # drop earlier mounts' stale widgets
    combo = next(c for c in win.doc_host.findChildren(_QCB)
                 if any(c.itemData(i) == "say" for i in range(c.count())))
    combo.setCurrentIndex(next(i for i in range(combo.count()) if combo.itemData(i) == "say"))
    vbox = next(p for p in win.doc_host.findChildren(QPlainTextEdit)
                if not p.isReadOnly() and "Line break" in p.toolTip())
    vbox.setPlainText("A cutscene line")
    nU = len(win._undo_stack)
    next(b for b in win.doc_host.findChildren(_QPB) if b.text() == "Add / Update").click()
    assert win._doc("U1").data.get("cutscene", {}).get("steps"), "the cutscene step was added"
    assert len(win._undo_stack) == nU + 1, "adding a cutscene step recorded an undo step"
    win._undo()
    assert not win._doc("U1").data.get("cutscene", {}).get("steps", []), "undo removed the cutscene step"
    # (6) closed-member guard: applying history for a no-longer-open member is a graceful no-op (no crash)
    win._apply_history("GONE", {"field": {}}, "field", "Undo x")
    # (7) focus-aware shortcut: with no text widget focused, Ctrl-Z routes to app-level undo; and the
    # read-only console/preview boxes that the delegate must REFUSE (else Ctrl-Z wipes their shown text)
    assert win._delegate_text_history(redo=False) is False
    assert win.output.isReadOnly(), "the Output console is read-only -> _delegate_text_history must skip it"
    # review fix: a list-group header retitles the Editor tab (no stale prior-leaf name)
    et = lambda: win.tabs.tabText(win.tabs.indexOf(win.doc_scroll))                       # noqa: E731
    win._open_editor("U1", "group", "npc")
    assert et() == "Editor — NPCs", et()
    # review fix: viewing a [[choice]] with NO `options` key must not materialize it (dirty-on-view)
    win._doc("U1").data["choice"] = [{"npc": "Z", "prompt": "Hm?"}]
    win._mark_clean("U1")
    win._mount_choice("U1", 0)
    assert "options" not in win._doc("U1").data["choice"][0], "viewing a choice must not inject options"
    assert "U1" not in win._dirty_members(), "viewing an options-less choice did not dirty the field"
    win._doc("U1").data.pop("choice", None)
    win._mark_clean("U1")

    # CREATE NEW (the pure actions; the dialogs are modal so the smoke drives the actions directly) --
    # New Field scaffolds a standalone project + opens it (loose mode)
    nf = win._new_field("NEWROOM", d, field_id=4555, area=12, pitch=40)
    assert nf.exists() and win._loose == "NEWROOM" and win.plan is None
    assert win._doc("NEWROOM").data["field"]["id"] == 4555, win._doc("NEWROOM").data["field"]
    assert (d / "NEWROOM" / "art").is_dir(), "placeholder art folder scaffolded"
    try:                                                # clobber guard: same name+folder is refused
        win._new_field("NEWROOM", d)
        assert False, "creating over an existing field.toml should raise"
    except ValueError:
        pass
    try:                                                # a bad name token is rejected
        win._new_field("bad/name", d)
        assert False, "a path-separator name should raise"
    except ValueError:
        pass
    for bad in (dict(area=9), dict(field_id=50)):       # area<10 + an out-of-band id are refused up front
        try:
            win._new_field("GUARDROOM", d, **bad)
            assert False, f"{bad} should raise"
        except ValueError:
            pass
    # New Campaign creates an EMPTY campaign + opens it; Add field scaffolds blank members into it
    cdir = d / "newcamp"
    nc = win._new_campaign("My Camp", cdir, mod_folder="FF9CustomMap", id_base=4600)
    assert nc.exists() and win.plan is not None and win.plan.name == "My Camp"
    assert win.plan.members == [] and win._loose is None, "a fresh campaign opens empty"
    m1 = win._add_field_to_campaign("ROOM1")
    assert m1 and m1.name == "ROOM1" and len(win.plan.members) == 1 and win.plan.entry_name == "ROOM1"
    assert (cdir / "ROOM1" / "room1.field.toml").exists()
    assert "ROOM1" in win.member_paths and win._member_items.get("ROOM1") is not None
    assert win._payload(win.tree.currentItem())[1] == "ROOM1", "the new member is selected"
    m2 = win._add_field_to_campaign("ROOM2")
    assert len(win.plan.members) == 2 and m2.new_id == m1.new_id + 1, (m1.new_id, m2.new_id)
    # the two new members are registered in the on-disk campaign.toml (add_field re-saved it)
    import tomllib as _tl_nc
    ondisk = _tl_nc.loads((cdir / "campaign.toml").read_text(encoding="utf-8"))
    assert {f["name"] for f in ondisk.get("field", [])} == {"ROOM1", "ROOM2"}, ondisk
    try:                                                # clobber guard: an existing campaign folder is refused
        win._new_campaign("Again", cdir)
        assert False, "creating over an existing campaign.toml should raise"
    except ValueError:
        pass
    # the new commands are in the palette (+ Add field appears only while a campaign is open)
    plabels = [e[0] for e in win._command_index()]
    assert {"New Field…", "New Campaign…", "Add field to campaign…"} <= set(plabels), plabels
    _newcamp_members = len(win.plan.members)               # captured for the summary (journey mode clears win.plan)
    # New Journey -- BARE = a COMPLETE ready file (hub warps to one field); MULTI = hub + journey with the
    # entry/links/seed left to fill in. Both open into journey mode; the dialog's choices become real values.
    jbare = win._new_journey("My Hub", d / "jnew", kind="bare", hub_id=4600, entry=4100)
    assert jbare.exists() and win.manifest is not None and win.journey_name == "My_Hub"  # hub name -> EVT/FBG token
    bt = jbare.read_text(encoding="utf-8")
    assert "[hub]" in bt and 'id = "intro"' in bt and "entry = 4100" in bt and "campaigns" not in bt, bt
    jmulti = win._new_journey("Arc Hub", d / "jmulti", kind="multi", campaigns=["dali", "outside"])
    assert jmulti.exists() and win.manifest is not None and win.journey_name == "Arc_Hub"  # hub name -> token
    mt = jmulti.read_text(encoding="utf-8")
    assert 'campaigns = ["dali", "outside"]' in mt and 'campaign = "dali"' in mt, mt
    assert "[[journey.link]]" in mt and "import-chain" in mt, "the multi file shows the links + the fork-first step"
    # FF9 REFERENCE ARC -- scaffolds the disc-1 story spine as a chained journey + the per-arc fork playbook
    jref = win._new_journey("FF9 Disc 1", d / "jref", kind="refarc")
    assert jref.exists() and win.manifest is not None, "the reference-arc journey opened in journey mode"
    rt = jref.read_text(encoding="utf-8")
    assert "import-chain 300" in rt and "ice_cavern" in rt and "--name-prefix" in rt, "the fork playbook is in the header"
    assert win.manifest.journeys[0].campaigns[:2] == ["alexandria", "evil_forest"], win.manifest.journeys[0].campaigns
    # FF9 REGION CATALOG: "Browse FF9 regions…" (Import) + Ctrl-K "Fork FF9 regions" compose catalog regions
    # into the Fork-a-region box -- one region alone (its seed + a suggested prefix), or several composed into ONE.
    from .. import refarc as _RAcat
    _aset = _RAcat.load_region_catalog()
    _imp = win.import_field
    s1 = _imp._apply_region_selection(_aset, [_aset.arcs[0].key])
    assert "," not in s1 and _imp.rg_prefix.text(), s1         # one region -> single seed + a suggested prefix
    s2 = _imp._apply_region_selection(_aset, [_aset.arcs[0].key, _aset.arcs[1].key])
    assert "," in s2 and _imp.seeds.text() == s2, s2           # several -> composed seeds fill the box
    assert _imp.rg_prefix.text() == "", "a composed multi-region fork CLEARS the stale single-region prefix"
    _imp.open_region_catalog = lambda: None                    # stub the modal so the route is headless-testable
    win._fork_ff9_regions()                                    # Ctrl-K "Fork FF9 regions" -> Import tab + catalog
    assert win.tabs.currentWidget() is _imp, "Fork FF9 regions switches to the Import tab"
    # the journey overview's Step-1 FORK panel: per-arc commands parsed from the header, none forked yet, and a
    # Fork button that runs import-chain (--out rewritten beside the manifest) right in the GUI (slice 3).
    assert "ice_cavern" in win._fork_cmds and win._fork_cmds["ice_cavern"].seed == 300, "fork commands parsed"
    assert not win._campaign_forked("ice_cavern"), "no arc is forked in a fresh scaffold"
    _real_run_job = win.run_job
    fcap = []
    win.run_job = lambda argv, **kw: (fcap.append(list(map(str, argv))) or True)  # capture, don't launch
    win._fork_campaign("ice_cavern")
    assert fcap and "import-chain" in fcap[-1] and "300" in fcap[-1], fcap[-1]
    iout = fcap[-1][fcap[-1].index("--out") + 1]
    assert iout.replace("\\", "/").endswith("jref/ice_cavern"), iout       # forked beside the journeys.toml
    # in-progress feedback: the active arc shows 'Forking…' + EVERY fork control disables (no silent run)
    assert win._fork_buttons["ice_cavern"].text() == "Forking…", win._fork_buttons["ice_cavern"].text()
    assert all(not b.isEnabled() for b in win._fork_buttons.values()), "all fork buttons disable during a fork"
    assert not win._fork_all_btn.isEnabled(), "Fork-all disables during a fork too"
    win._fork_all_missing()                                                 # the chain runs the first, queues the rest
    assert win._fork_queue and "import-chain" in fcap[-1], "Fork-all started the chain"
    # busy-rejection: a rejected launch (a job already running) must keep the WHOLE queue (no arc dropped)
    win.run_job = lambda argv, **kw: False
    win._fork_all_missing()
    assert win._fork_queue == [f for f in win._fork_order if not win._campaign_forked(f)], "rejected launch loses no arc"
    # navigation guard: once we've left the journey overview (a campaign drilled in), the chain bails + clears
    win.plan = object()
    win._fork_next_in_queue()
    assert win._fork_queue == [], "the fork chain stops when off the journey overview"
    win.plan = None
    win._fork_queue = []                                                    # stop the (stubbed) chain
    win.run_job = _real_run_job
    # CATALOG-DRIVEN MULTI ARC + 'Add region to arc' (the bottom-up fork-a-region loop): a Multi journey whose
    # campaigns are FF9 catalog regions renders the FAITHFUL fork playbook; _apply_add_region grows the chain.
    _k0, _k1, _k2 = _aset.arcs[0].key, _aset.arcs[1].key, _aset.arcs[2].key
    assert win._all_catalog_regions([_k0, _k1]) and not win._all_catalog_regions([_k0, "made_up_folder"])
    jarc = win._new_journey("Region Arc", d / "jarc", kind="multi", campaigns=[_k0, _k1])
    at = jarc.read_text(encoding="utf-8")
    assert "import-chain" in at and "--id-base" in at and "--name-prefix" in at, "catalog multi -> a fork playbook"
    assert win.manifest.journeys[0].campaigns == [_k0, _k1] and win._has_multi_arc()
    assert win._apply_add_region([_k2]) is True, "added a region to the arc"
    assert win.manifest.journeys[0].campaigns == [_k0, _k1, _k2], win.manifest.journeys[0].campaigns
    assert f"--out {_k2}" in jarc.read_text(encoding="utf-8"), "the added region got a fork command"
    assert win._apply_add_region([_k2]) is False, "re-adding the same region is a no-op (idempotent)"
    # the action is reachable: context menu on the journey root + the Ctrl-K palette
    assert any(lbl == "Add region to arc…" for lbl, _ in win._context_actions(win.tree.topLevelItem(0)))
    assert "Add region to arc…" in [e[0] for e in win._command_index()]
    # WORLD HUB (the journey selector): create an empty hub, then add menu rows pointing at installed slices.
    jhub = win._new_journey("My World Hub", d / "jhub", kind="hub")
    assert jhub.exists() and win.manifest is not None and len(win.manifest.journeys) == 0, "empty selector hub"
    ht = jhub.read_text(encoding="utf-8")
    assert win.manifest.hub.get("borrow_field") == 3100 and "[hub]" in ht, "hub defaults to Mognet Central"
    assert win.manifest.hub.get("name") == "My_World_Hub", "hub name coerced to an EVT/FBG token (no spaces)"
    # an empty selector hub is a WARNING (a fill-me-in scaffold), NOT a red error (the original UX complaint)
    from .. import journey as _Jh
    _he, _hw = _Jh.lint_manifest(win.manifest)
    assert _he == [] and any("add a journey" in w for w in _hw), (_he, _hw)
    assert win.on_add_journey_row.__self__ is win                          # the action exists
    assert win._append_journey_row("dali", "Dali", "4100", "2600") is True, "added a journey row"
    assert win._append_journey_row("treno", "Treno", "4501", "") is True
    assert [j.id for j in win.manifest.journeys] == ["dali", "treno"], [j.id for j in win.manifest.journeys]
    assert win.manifest.journeys[0].entry.field == 4100 and win.manifest.journeys[0].hub_scenario == 2600
    assert not win._append_journey_row("dali", "Dup", "4102", ""), "a duplicate journey id is refused"
    assert not win._append_journey_row(" dali ", "Dup", "4102", ""), "a whitespace-padded duplicate is refused too"
    assert not win._append_journey_row("bad slug!", "X", "4103", ""), "a bad slug is refused"
    assert not win._append_journey_row("ok", "X", "not-an-int", ""), "a non-numeric entry is refused"
    assert [j.id for j in win.manifest.journeys] == ["dali", "treno"], "rejected rows didn't land"
    # two rows -> the SAME field warn (the copy-paste mistake); removing one clears it
    assert win._append_journey_row("dup", "Dup", "4100", "") is True     # 4100 == dali's entry
    _de, _dw = _Jh.lint_manifest(win.manifest)
    assert any("both warp to field 4100" in w for w in _dw), _dw
    assert win._remove_journey_row("dup") is True and [j.id for j in win.manifest.journeys] == ["dali", "treno"]
    assert not any("both warp" in w for w in _Jh.lint_manifest(win.manifest)[1]), "dup-entry warning cleared"
    assert win._remove_journey_row("nope") is False, "removing a missing journey fails gracefully"
    # 'Add journey…' on the hub root + 'Remove journey' on a journey row (context menu) + the palette
    assert any(lbl == "Add journey…" for lbl, _ in win._context_actions(win.tree.topLevelItem(0)))
    _jrow = win.tree.topLevelItem(0).child(0)                            # the first [[journey]] node
    assert any(lbl.startswith("Remove journey") for lbl, _ in win._context_actions(_jrow)), win._payload(_jrow)
    assert any(lbl == "Set base party / seed…" for lbl, _ in win._context_actions(_jrow)), "seed action offered"
    # Set base party / seed: upsert [journey.seed], round-trips; bare-journey party warns; Inspector + clear work
    assert win._apply_journey_seed("dali", "2600", "Zidane, Vivi") is True
    _dj = next(j for j in win.manifest.journeys if j.id == "dali")
    assert _dj.seed.party == ["Zidane", "Vivi"] and _dj.seed.scenario == 2600
    assert any("BARE single-field journey" in w for w in _Jh.lint_manifest(win.manifest)[1]), "bare-party warns"
    assert any("base party: Zidane, Vivi" in s for s in win._inspect_build("journey", "@journey:dali", None))
    # do-now #3: the journey-tier authoring is now a VISIBLE compartment, not right-click-only -- the Inspector
    # card carries clickable seed/tuning links (routed through _inspect_link) + the overview mounts a per-journey
    # action button row when a [[journey]] row is selected.
    _jcard = "<br>".join(win._inspect_build("journey", "@journey:dali", None))
    assert 'href="jseed:dali"' in _jcard and 'href="jtuning:dali"' in _jcard, _jcard
    assert "right-click" not in _jcard, "seed/tuning are clickable now, not a right-click hint"
    win._mount_journey_overview(selected_jid="dali")                      # mounts _mount_journey_row_actions (no crash)
    assert win._apply_journey_seed("dali", "", "") is True                # clearing both removes the [journey.seed]
    assert next(j for j in win.manifest.journeys if j.id == "dali").seed.is_empty
    assert win._apply_journey_seed("nope", "", "Vivi") is False           # a missing journey fails gracefully
    # Set tuning (player stats): the TuningDialog add/fold/accept logic + the apply round-trip (reuses PLAYER_TABLES)
    from .tuningdialog import TuningDialog as _TD
    _td = _TD(win, win.pal, "dali", {}, is_bare=True)
    _td._pick_table = lambda: "character"                                # stub the table chooser
    _td._add()
    assert _td._ctx["block"] == "character"                              # landed on the new row's form
    _td._ctx["getters"]["character"] = lambda: "Vivi"
    _td._ctx["getters"]["magic"] = lambda: "55"
    _td._accept()
    assert _td.result_tuning == {"character": [{"character": "Vivi", "magic": 55}]}, _td.result_tuning
    # the dialog edits only the 7 form tables but must CARRY THROUGH the nested hand-authored blocks (learn / ...)
    _td3 = _TD(win, win.pal, "dali", {"learn": [{"character": "Vivi", "abilities": ["Fire"]}]}, is_bare=True)
    _td3._pick_table = lambda: "character"
    _td3._add()
    _td3._ctx["getters"]["character"] = lambda: "Dagger"
    _td3._accept()
    assert _td3.result_tuning["learn"] == [{"character": "Vivi", "abilities": ["Fire"]}], "nested block preserved"
    assert _td3.result_tuning["character"] == [{"character": "Dagger"}]
    _jrow2 = win.tree.topLevelItem(0).child(0)                           # re-fetch (re-opens rebuilt the tree)
    assert any(lbl == "Set tuning (player stats)…" for lbl, _ in win._context_actions(_jrow2)), "tuning action offered"
    assert win._apply_journey_tuning("dali", _td.result_tuning) is True
    assert next(j for j in win.manifest.journeys if j.id == "dali").tuning["character"] == [{"character": "Vivi", "magic": 55}]
    assert any("[journey.tuning] writes MOD-GLOBAL" in w for w in _Jh.lint_manifest(win.manifest)[1])
    assert any("tuning: 1 player-CSV row" in s for s in win._inspect_build("journey", "@journey:dali", None))
    assert win._apply_journey_tuning("dali", {}) is True                 # empty clears every [[journey.tuning.*]]
    assert next(j for j in win.manifest.journeys if j.id == "dali").tuning == {}
    assert "Add journey to hub…" in [e[0] for e in win._command_index()]
    try:                                                   # clobber guard: an existing manifest is refused
        win._new_journey("Again", d / "jnew")
        assert False, "an existing journeys.toml should be refused"
    except ValueError:
        pass
    assert "New Journey…" in [e[0] for e in win._command_index()]
    # the toolbar folds New/Open into 3 hierarchy DROPDOWNS (Field / Campaign / Journey), each with both actions
    for btn, want in ((win._field_btn, ("New Field", "Open Field")),
                      (win._campaign_btn, ("New Campaign", "Open Campaign")),
                      (win._journey_btn, ("New Journey", "Open Journey"))):
        acts = [a.text() for a in btn.menu().actions()]
        assert all(any(lbl in a for a in acts) for lbl in want), (btn.text(), acts)

    # JOURNEY MODE: open a journeys.toml as the FRONT DOOR (load + lint + tree + overview + drill into a campaign)
    jdir = d / "jtest"
    (jdir / "camp1").mkdir(parents=True, exist_ok=True)
    jcm = [C.Member(0, 5000, "ROOMA", "editable", 11, "", "ROOMA/ROOMA.field.toml", False)]
    jcplan = C.CampaignPlan(name="Camp1", mod_folder="M", id_base=5000, flag_base=C.FIRST_SAFE_FLAG,
                            flags_per_field=64, entry_name="ROOMA", entry_entrance=0, members=jcm, edges=[], seams=[])
    (jdir / "camp1" / "campaign.toml").write_text(C.render_campaign_toml(jcplan), encoding="utf-8")
    (jdir / "camp1" / "ROOMA").mkdir(parents=True, exist_ok=True)
    (jdir / "camp1" / "ROOMA" / "ROOMA.field.toml").write_text(
        '[field]\nid = 5000\nname = "ROOMA"\narea = 11\n\n[[npc]]\nname = "Host"\n', encoding="utf-8")
    # NB: named arc.toml (NOT journeys.toml) on purpose -- the reverse-search _journey_label only finds a file
    # literally named journeys.toml, so this exercises the drill-in regression (the journey label must be KEPT
    # from open_journey, not re-derived, or the back-to-journey row would vanish -- the HIGH review finding).
    (jdir / "arc.toml").write_text(
        '[hub]\nname = "Test Hub"\nid = 4600\n\n'
        '[[journey]]\nid = "alpha"\nname = "Alpha Arc"\ncampaigns = ["camp1"]\n'
        'entry = { campaign = "camp1", field = "ROOMA" }\n', encoding="utf-8")
    assert win.open_journey(jdir / "arc.toml")
    assert win.manifest is not None and win.plan is None and win.journey_name == "Test Hub"
    jroot = win.tree.topLevelItem(0)                       # journeys-manifest root -> journey -> member campaign
    assert win._payload(jroot)[0] == "jset"
    jnode = jroot.child(0)
    assert win._payload(jnode) == ("journey", "Alpha Arc", "@journey:alpha"), win._payload(jnode)
    cnode = jnode.child(0)
    assert win._payload(cnode) == ("jcampaign", "camp1", "camp1"), win._payload(cnode)
    # ITERATION 2 (playtest feedback): the hub/journey/campaign rows must read DISTINCTLY -- the hub glyph (⌂)
    # differs from a journey's (◆), and every row carries a TYPE tooltip (the glyph isn't the only cue).
    assert jroot.text(0).startswith("⌂") and jnode.text(0).startswith("◆"), (jroot.text(0), jnode.text(0))
    assert "Hub" in jroot.toolTip(0) and "Journey" in jnode.toolTip(0) and "Campaign" in cnode.toolTip(0)
    # the CHIP names the SELECTED row's type (not just the open document), and the breadcrumb deepens to it
    win.tree.setCurrentItem(jroot)
    assert win.crumb._chip.text() == "HUB", win.crumb._chip.text()
    win.tree.setCurrentItem(jnode)
    assert win.crumb._chip.text() == "JOURNEY"
    win.tree.setCurrentItem(cnode)
    assert win.crumb._chip.text() == "CAMPAIGN"
    assert [c.label for c in win._content_crumbs] == ["Test Hub", "Alpha Arc", "camp1"], \
        "the breadcrumb shows the full hub▸journey▸campaign trail to the selected row"
    # selecting the root mounts the resolved-plan overview in the doc area (read-only)
    win.tree.setCurrentItem(jroot)
    ov = [w for w in win.doc_host.findChildren(QPlainTextEdit) if w.isReadOnly()]
    assert any("Alpha Arc" in w.toPlainText() and "5000" in w.toPlainText() for w in ov), "overview renders the plan"
    # REGRESSION (nested-layout leak): the overview's action buttons live in a NESTED QHBoxLayout (addLayout),
    # so _clear_doc must delete THOSE widgets too -- else 'Add journey…' etc. leak into the next panel (the
    # Script / marker / gateway leak the user hit). Capture them while the overview is up...
    from PySide6.QtCore import QEvent
    _JLABELS = {"Add journey…", "Add region to arc…", "Fill entry from forks"}
    _jbuttons = [b for b in win.doc_host.findChildren(QPushButton) if b.text() in _JLABELS]
    assert _jbuttons, "overview shows its journey-action buttons"
    win.on_check()                                         # Check lints the manifest -> Problems (no crash)
    # DRILL IN: opening the campaign node loads it (single-campaign editor); the journey stays remembered
    win._on_tree_double(cnode)
    assert win.plan is not None and win.plan.name == "Camp1" and win.manifest is not None, "drilled into the campaign"
    assert "ROOMA" in win.member_paths
    # _clear_doc deleteLater()'d the journey buttons; flush EACH one's DeferredDelete (processEvents alone won't
    # run it) -- per-receiver so we don't disturb other pending deletions -- then assert none survive in doc_host.
    for _b in _jbuttons:
        QApplication.sendPostedEvents(_b, QEvent.Type.DeferredDelete)
    assert not ({b.text() for b in win.doc_host.findChildren(QPushButton)} & _JLABELS), \
        "journey buttons must NOT leak into the drilled-in campaign panel (nested-layout clear)"
    assert win.journey_name == "Test Hub", "drill-in KEEPS the journey label (no reverse-search rename/loss)"
    # the journey row (always present -- the label is kept) sits above the campaign; it returns to the overview
    jrow = win._root_items[0]
    assert win._payload(jrow)[0] == "journey", "the back-to-journey row exists after drilling in"
    win._on_tree_double(jrow)
    assert win.plan is None and win.manifest is not None, "back to the journey overview"
    # opening a plain field afterwards drops the journey context
    assert win.open_field(af) and win.manifest is None, "a standalone field leaves journey mode"
    assert "Open Journey…" in [e[0] for e in win._command_index()]
    # ITERATION 2 (playtest feedback): the user's exact stuck-state -- Open Field from a DRILLED-IN
    # (journey+campaign) state must escape, AND the toolbar Close returns to the empty Workspace from any mode.
    assert win.open_journey(jdir / "arc.toml") and win.manifest is not None
    win._on_tree_double(win.tree.topLevelItem(0).child(0).child(0))     # drill into camp1 (plan+manifest set)
    assert win.plan is not None and win.manifest is not None, "drilled into journey+campaign"
    assert win.open_field(af) and win.manifest is None and win.plan is None, "Open Field escapes a drilled-in journey"
    win._refresh_home_status()                                          # do-now #4: Home reflects what's open
    assert "Currently editing" in win._home_status.text() and "Field" in win._home_status.text()
    win._close_project()
    assert win.manifest is None and win.plan is None and win._loose is None and win.tree.topLevelItemCount() == 0, \
        "Close returns to the empty Workspace"
    assert win.crumb._chip.isHidden(), "Close clears the doc-mode chip"
    # do-now #4: the 'Start here' Home resets its status after Close + names every entry point as a real button
    assert "Nothing open" in win._home_status.text(), "Home resets its status after Close"
    _home_btns = {b.text() for b in win._welcome_tab.findChildren(QPushButton)}
    assert {"Open…", "New…", "Go to Battle", "Go to Import", "Open Save…"} <= _home_btns, _home_btns

    # RECONCILE (STEP 2): a reference-arc scaffold's ENTRY_MEMBER + link placeholders fill from the forked
    # campaigns beside it -- camp_a/A2 has a scripted Field() seam to 200 (== camp_b/B1's source) -> PRECISE.
    from .. import refarc as _RA
    rdir = Path(tempfile.mkdtemp())
    for key, ent, mem, sm in (("camp_a", "A1", [("A1", 100, 6000), ("A2", 101, 6001)], [("A2", 200, "scripted")]),
                              ("camp_b", "B1", [("B1", 200, 6100)], [])):
        rp = C.CampaignPlan(name=key, mod_folder=f"FF9CustomMap-{key}", id_base=mem[0][2],
                            flag_base=C.FIRST_SAFE_FLAG, flags_per_field=16, entry_name=ent, entry_entrance=0,
                            members=[C.Member(s, n, nm, "native", 11, "", f"{nm}/{nm}.field.toml", False)
                                     for (nm, s, n) in mem],
                            seams=[{"frm": f, "to_real": tr, "kind": k, "note": "", "to_member": None}
                                   for (f, tr, k) in sm], verbatim=True)
        (rdir / key).mkdir(parents=True, exist_ok=True)
        (rdir / key / "campaign.toml").write_text(C.render_campaign_toml(rp), encoding="utf-8", newline="\n")
        for (nm, *_rest) in mem:                                   # member field.tomls (so the campaign lints)
            (rdir / key / nm).mkdir(parents=True, exist_ok=True)
            (rdir / key / nm / f"{nm}.field.toml").write_text(
                f'[field]\nid = {dict((m[0], m[2]) for m in mem)[nm]}\nname = "{nm}"\narea = 11\n', encoding="utf-8")
    aset = _RA.ReferenceArcSet(title="Recon", arcs=[_RA.ReferenceArc(key="camp_a", name="A", seed=100, beat=0),
                                                    _RA.ReferenceArc(key="camp_b", name="B", seed=200)])
    (rdir / "journeys.toml").write_text(_RA.render_arc_journey_toml(aset), encoding="utf-8", newline="\n")
    assert win.open_journey(rdir / "journeys.toml")
    assert win._needs_reconcile(), "the scaffold still has ENTRY_MEMBER/link placeholders"
    assert win._reconcile_journey() is True, "reconcile filled the placeholders"
    assert not win._needs_reconcile(), "placeholders gone after reconcile"
    j0 = win.manifest.journeys[0]
    assert j0.entry.field == "A1", j0.entry.field
    assert j0.links == [], "(i): reconcile writes NO link rows -- cross-campaign warps auto-wire at deploy"
    from .. import journey as _J                                            # the wiring lives in resolve, not the toml
    rj = _J.resolve_journey(j0, _J.load_campaign_plans(win.manifest))
    assert ("camp_a", "A2", "camp_b", "B1") in {
        (l["src_campaign"], l["src_field"], l["dst_campaign"], l["dst_field"]) for l in rj.links}, rj.links
    assert win._reconcile_journey() is False, "reconcile is idempotent (entry set, nothing left to fill)"
    assert win.open_field(af) and win.manifest is None                    # leave journey mode for the rest

    # PHASE 0 -- VERBATIM logic-map surfacing: a [verbatim_eb] member badges its row, shows a read-only
    # "Script" subtree (built from the LOCAL .bin -- no install), and the field rollup explains the empty lists.
    vb_ok = False
    add_ok = False
    _fix = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "alex100-us.eb.bytes"
    if _fix.exists():                                       # needs the extracted fixture (skipped on a clean clone)
        vd = Path(tempfile.mkdtemp())
        vmem = [C.Member(100, 30100, "ALEXFORK", "borrow", 11, "", "ALEXFORK/ALEXFORK.field.toml", False)]
        vplan = C.CampaignPlan(name="VB", mod_folder="M", id_base=30100, flag_base=C.FIRST_SAFE_FLAG,
                               flags_per_field=64, entry_name="ALEXFORK", entry_entrance=0,
                               members=vmem, edges=[], seams=[])
        (vd / "campaign.toml").write_text(C.render_campaign_toml(vplan), encoding="utf-8")
        (vd / "ALEXFORK").mkdir(parents=True, exist_ok=True)
        (vd / "ALEXFORK" / "ALEXFORK.field.toml").write_text(
            '[field]\nid = 30100\nname = "ALEXFORK"\narea = 11\n\n'
            '[verbatim_eb]\nbin = "ALEXFORK.verbatim_eb.bin"\n', encoding="utf-8")
        (vd / "ALEXFORK" / "ALEXFORK.verbatim_eb.bin").write_bytes(_fix.read_bytes())
        assert win.open_campaign(vd / "campaign.toml")
        vitem = win.tree.topLevelItem(0).child(0)
        win.tree.expandItem(vitem)                          # lazy _load_objects -> badge + Script group
        assert "· verbatim" in vitem.text(0), vitem.text(0)
        sgrp = next(vitem.child(i) for i in range(vitem.childCount())
                    if win._payload(vitem.child(i))[0] == "logic_root")
        win.tree.expandItem(sgrp)                           # lazy _load_logic_map from the local .bin
        ekinds = [win._payload(sgrp.child(i))[0] for i in range(sgrp.childCount())]
        assert ekinds and all(k in ("logic_entry", "note") for k in ekinds), ekinds
        eitem = next(sgrp.child(i) for i in range(sgrp.childCount())
                     if win._payload(sgrp.child(i))[0] == "logic_entry")
        assert eitem.childCount() >= 1, "the entry has decoded routines"
        rnode = eitem.child(0)
        win.tree.setCurrentItem(rnode)                      # read-only inspect: detail shown in the inspector
        assert win._payload(rnode)[0] == "logic_node" and win.insp_body.text(), "routine detail in the inspector"
        win.tree.setCurrentItem(vitem)
        assert "verbatim fork" in win.insp_body.text(), win.insp_body.text()

        # PHASE 2b -- editable logic node: selecting a routine mounts the in-place edit panel; authoring a
        # value writes a [[logic_edit]] into the member field.toml (the amber-dot flow), a revert clears it.
        from .. import logic_edit as _LE
        win._open_editor("ALEXFORK", "logic_node", win._payload(rnode)[2])   # mount the panel (sites or empty)
        assert win.doc_host_lay.count() > 0, "logic-node edit panel mounted"
        eb_b, ents, langs = win._member_logic_inputs("ALEXFORK")
        _SAFE = {"text": "Smoke edit!", "item": 233, "gil": 7, "field": 6300}   # safe NEW per editable kind
        edit_ok = False
        for ei in range(sgrp.childCount()):
            en = sgrp.child(ei)
            if win._payload(en)[0] != "logic_entry":
                continue
            for ri in range(en.childCount()):
                rkey = win._payload(en.child(ri))[2]
                e_, t_ = int(rkey.split(":")[1]), int(rkey.split(":")[2])
                site = next((s for s in _LE.editable_effects(eb_b, e_, t_, entries=ents, lang_bodies=langs)
                             if s.group in _SAFE), None)
                if site is None:
                    continue
                win._open_editor("ALEXFORK", "logic_node", rkey)
                if site.group == "item":                        # the new item path: retarget id (+ display + qty)
                    win._commit_item_edit("ALEXFORK", e_, t_, site, _SAFE["item"], site.count_old)
                else:
                    win._commit_logic_edit("ALEXFORK", e_, t_, site, _SAFE[site.group])
                assert win._doc("ALEXFORK").data.get("logic_edit"), "authored a [[logic_edit]]"
                assert "ALEXFORK" in win._unsaved(), "authoring dirtied the member"
                win._undo()                                     # undo re-opens the panel + clears the edit
                assert not win._doc("ALEXFORK").data.get("logic_edit"), "undo removed the edit"
                assert win.doc_host_lay.count() > 0, "undo re-mounted the logic panel (not the field form)"
                win._redo()
                assert win._doc("ALEXFORK").data.get("logic_edit"), "redo restored the edit"
                win._save_logic("ALEXFORK", e_, t_)             # persist -> the row should now read "(saved)"
                assert "ALEXFORK" not in win._unsaved(), "save cleared the dot"
                assert (win._logic_pending(site, win._doc("ALEXFORK").data.get("logic_edit"))
                        == win._logic_pending(site, (win._clean.get("ALEXFORK") or {}).get("logic_edit"))), \
                    "a saved edit matches the baseline -> labeled (saved), not (unsaved)"
                win._revert_logic_site("ALEXFORK", e_, t_, site)
                win._save_logic("ALEXFORK", e_, t_)             # leave the fixture's toml clean again
                assert not win._doc("ALEXFORK").data.get("logic_edit"), "revert cleared the edit"
                edit_ok = True
                break
            if edit_ok:
                break
        vb_ok = "edited" if edit_ok else "shown"

        # PHASE 4 GUI -- author a [[logic_add]] from the Script panel: add a give_item + a show_line (both
        # dry-run-validated via build.dry_run_logic_adds), the anchor builder, revert/undo/redo, save clean.
        add_ok = False
        rkey0 = win._payload(rnode)[2]
        e0, t0 = int(rkey0.split(":")[1]), int(rkey0.split(":")[2])
        win._open_editor("ALEXFORK", "logic_node", rkey0)
        # the panel + tree now carry a per-routine 'what it does' summary / single-category hint (read-only)
        from ff9mapkit import logic_map as _LM2
        assert isinstance(win._logic_node_summary("ALEXFORK", e0, t0, eb_b, ents), str), "node summary builds"
        _lm0 = win._logic_maps.get("ALEXFORK")
        assert _lm0 and any(_LM2.node_summary(n) for n in _lm0.nodes), "a routine summarizes"
        assert any(_LM2.node_report(n) for n in _lm0.nodes), "a routine has a friendly transcript"
        assert win._collapsible("hdr", ["line one", "line two"]) is not None, "the disclosure widget builds"
        gi = win._build_logic_add("give_item", e0, t0, "prepend", None, [], "Potion", "1", "", "", "", "")
        assert gi == {"kind": "give_item", "entry": e0, "tag": t0, "item": "Potion"}, gi
        win._commit_logic_add("ALEXFORK", e0, t0, gi)
        assert (win._doc("ALEXFORK").data.get("logic_add") or [])[-1]["kind"] == "give_item", "authored a give_item"
        assert "ALEXFORK" in win._unsaved() and win._routine_adds("ALEXFORK", e0, t0), "dirtied + shows in rows"
        sl = win._build_logic_add("show_line", e0, t0, "prepend", None, [], "", "", "", "", "", "Bonus line!")
        assert sl["kind"] == "show_line" and sl["message"] == "Bonus line!", sl
        win._commit_logic_add("ALEXFORK", e0, t0, sl)
        assert sum(a["kind"] == "show_line" for a in win._doc("ALEXFORK").data["logic_add"]) == 1, "authored show_line"
        # the anchor builder resolves an 'after' placement to (after_op, after_nth)
        anchors = win._routine_anchors(eb_b, e0, t0)
        assert anchors, "the routine exposes anchorable instructions"
        aft = win._build_logic_add("give_gil", e0, t0, "after", anchors[0][:2], anchors, "", "", "500", "", "", "")
        assert aft["where"] == "after" and aft["after_op"] == anchors[0][0] and aft["amount"] == 500, aft
        # menu_row: the build helper assembles a dispatch-row dict (the effect payload reused, no placement keys)
        mr = win._build_menu_row(e0, t0, "118", "Get a free Potion!", "give_item", "Potion", "1", "", "", "", "")
        assert mr == {"kind": "menu_row", "entry": e0, "tag": t0, "menu_txid": 118,
                      "label": "Get a free Potion!", "effect": "give_item", "item": "Potion"}, mr
        mrm = win._build_menu_row(e0, t0, "118", "Lore", "show_line", "", "", "", "", "", "An old tale...")
        assert mrm["effect"] == "show_line" and mrm["message"] == "An old tale..." and "where" not in mrm, mrm
        assert "menu row" in win._logic_add_label(mr) and "txid 118" in win._logic_add_label(mr)
        win._undo(); win._redo()                                # checkpoint round-trips the add history
        while win._routine_adds("ALEXFORK", e0, t0):            # remove every added effect
            win._revert_logic_add("ALEXFORK", e0, t0, win._routine_adds("ALEXFORK", e0, t0)[0][0])
        assert not win._doc("ALEXFORK").data.get("logic_add"), "removed all added effects"
        win._save_logic("ALEXFORK", e0, t0)                     # leave the fixture clean
        assert "ALEXFORK" not in win._unsaved(), "save cleared the dot"
        add_ok = True

    # do-now #5: a loosely-opened campaign MEMBER detects its parent + can jump UP into the full campaign
    # (the spine made two-way). Re-open the early IC campaign (still on disk) to grab a real member path.
    assert win.open_campaign(d / "campaign.toml")
    _memberp = win.member_paths["IC_ENT"]
    assert win.open_field(_memberp) and win._loose, "opened a campaign member as a standalone field"
    assert win._loose_parent[0] is not None and win._loose_parent[1] == "IC_ENT", win._loose_parent
    win.tree.setCurrentItem(win._member_items[win._loose])             # select it -> the Inspector offers the jump
    assert 'href="openparent"' in win.insp_body.text(), win.insp_body.text()
    win._open_parent_campaign()
    assert win.plan is not None and win._loose is None, "the upward jump opened the parent campaign"
    assert win._payload(win.tree.currentItem())[1] == "IC_ENT", "and kept us on the same field"
    # a TRULY standalone field (no parent campaign) shows no jump
    assert win.open_field(af) and win._loose_parent[0] is None, "a standalone field has no parent campaign"
    # do-now #6: an Import fork auto-opens the project it wrote (here, the dir holding the IC campaign.toml) --
    # the Import->author handoff in one step instead of 'now go open it on Build & Deploy'.
    win._close_project()
    win._import_forked(d)
    assert win.plan is not None and win.campaign_path == d / "campaign.toml", "an Import fork auto-opens its campaign"
    # do-now #7: Story State annotates custom-band bits with the OPEN project's authored [[flag]] names. A
    # named [[flag]] index is an ABSOLUTE bit (no flag-window offset), so the resolver is a pure identity map.
    _fdir = Path(tempfile.mkdtemp())
    _ff = _fdir / "FLAGFIELD.field.toml"
    _ff.write_text('[field]\nid = 4055\nname = "FLAGFIELD"\narea = 12\n\n[[flag]]\nname = "got_sword"\nindex = 8520\n',
                   encoding="utf-8")
    assert win.open_field(_ff) and win._project_flag_names() == {8520: "got_sword"}, win._project_flag_names()
    from .. import flags as _flags
    _fb = bytearray(2048); _fb[8520 >> 3] |= 1 << (8520 & 7)
    _frep = _flags.decode_gEventGlobal(bytes(_fb))
    assert "8520=got_sword" in _flags.render_report(_frep, names=win._project_flag_names())
    # robustness: just VIEWING Story State re-reads the open project's flags (no open/edit-order dependence)
    win.tabs.setCurrentWidget(win.story_state)
    assert win.story_state.flag_names == {8520: "got_sword"}, win.story_state.flag_names
    win.tabs.setCurrentWidget(win.doc_scroll)
    win._close_project()
    assert win.story_state.flag_names == {}, "Close drops the authored-flag annotation"

    print(f"workspace shell smoke ok: campaign>field tree ({len(names)} members) + Map document, lazy "
          f"objects, breadcrumb, EDITOR forms (NPC+field+party+startup round-trip) + cutscene/choice sub-editors + "
          f"catalog picker (+ scene-id) + Open Field (standalone authored) + Save docs (Story State SC "
          f"{win.story_state.reports[0][1].scenario_counter} + Item/Equip gil "
          f"{win.item_equip.targets[0]['report'].gil}) + Battle doc (encounter/enemy + save round-trip + "
          f"ai_phase/ai_patch/seq_patch forms + Browse-sites fill + Remove-selected + fork-battle auto-open + "
          f"install-list browse) + ADD list items (NPC/gateway/choice/FLAG section + band-lint) + UNDO/REDO "
          f"(form/add/delete/cutscene + redo-invalidation) + New Field/Campaign + Add-field "
          f"({_newcamp_members} blank members) + Build/Deploy + Import docs (verbatim default + re-authorable + region-fork dry-run/fork + FF9-region catalog, argv-built) + Info Hub "
          f"LIBRARY (sectioned + detail pane) + INSPECTOR (rollup + clickable cross-refs + encounter->Battle jump) + "
          f"persistent CHIP names the SELECTED node's type (hub/journey/campaign/field) + breadcrumb truthful "
          f"per-tab (content/battle/save/build) + distinct hub⌂/journey◆ glyphs + type tooltips + Close-to-empty + "
          f"drilled-in Open-Field escape + 'Start here' HOME (entry points as buttons + 'currently editing') + "
          f"loose-field→parent-campaign upward jump + battle.toml/Import fork pre-aim+auto-open Build&Deploy + JOURNEY mode "
          f"(open/lint/overview/drill-in/RECONCILE entry+links from forks/ADD region to arc/base-party seed/player tuning + VISIBLE per-journey action row + clickable seed/tuning) + VERBATIM logic-map subtree + in-place edit panel "
          f"({vb_ok or 'fixture-skipped'}) + [[logic_add]] authoring "
          f"({'add/show_line/anchor/menu_row/revert' if (_fix.exists() and add_ok) else 'fixture-skipped'}) "
          f"+ Ctrl-K palette, Problems dock ({nprob} rows); QProcess wired")


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
