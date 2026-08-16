"""Docs Studio -- a standalone desktop app for working on the Dream World IX Manual.

One window, three panes and a tools dock:

  * left   -- the Manual's sidebar as an editable tree: nav.toml sections, the glob-matched
              tutorial rows, and the auto "More" bucket. Reorder pages, move them between
              sections, pin glob/More pages as literal entries, add sections -- then Save nav.
  * center -- the markdown editor (Ctrl+S saves, Ctrl+F finds).
  * right  -- a live preview rendered by the REAL site pipeline (build.py's markdown config,
              GitHub-parity heading ids, tutorial-frontmatter chips), debounced as you type.
  * bottom -- the tooling: Build (all gates), the docsite test suite, shots --check / --all,
              the UI-inventory harvest, a local preview server, and Deploy (confirm-first).

Build errors land in a Problems list; double-click one to open the offending source.

Run:  py docsite/studio.py        (or double-click apps/ff9_docs_studio.pyw)
Needs PySide6 plus the docs build deps (markdown, pygments).
"""

from __future__ import annotations

import html as _html
import re
import socket
import sys
import time
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (QAction, QColor, QDesktopServices, QFont, QIcon, QKeySequence,
                           QSyntaxHighlighter, QTextCharFormat, QTextCursor)
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox, QDockWidget,
                               QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
                               QPlainTextEdit, QPushButton, QSplitter, QTextBrowser, QToolButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

HERE = Path(__file__).resolve().parent          # docsite/
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import studio_core as core  # noqa: E402

B = core.load_build()

MONO = "Consolas"
APP_TITLE = "Docs Studio"


# ---------------------------------------------------------------------------------- highlighter

def is_dark_palette() -> bool:
    from PySide6.QtGui import QPalette
    return QApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128


class MarkdownHighlighter(QSyntaxHighlighter):
    """Light-touch markdown coloring: headings, emphasis, inline code, links, fences.
    Two color sets -- ink is calibrated against the ACTUAL editor ground, light or dark."""

    IN_FENCE = 1

    def __init__(self, doc, dark: bool):
        super().__init__(doc)
        def fmt(color, bold=False, mono=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            if mono:
                f.setFontFamilies([MONO])
            return f
        if dark:
            self.f_head = fmt("#7fb4e8", bold=True)
            self.f_bold = fmt("#e0b070", bold=True)
            self.f_code = fmt("#e39ac0", mono=True)
            self.f_link = fmt("#6fc7b4", )
            self.f_fence = fmt("#9aa8b6", mono=True)
            self.f_quote = fmt("#98a4b0")
        else:
            self.f_head = fmt("#1a56a0", bold=True)
            self.f_bold = fmt("#7a4a00", bold=True)
            self.f_code = fmt("#8a2151", mono=True)
            self.f_link = fmt("#0f7060")
            self.f_fence = fmt("#5a6672", mono=True)
            self.f_quote = fmt("#5f6b76")
        self.rules = [
            (re.compile(r"`[^`\n]+`"), self.f_code),
            (re.compile(r"\*\*[^*\n]+\*\*"), self.f_bold),
            (re.compile(r"\[[^\]\n]*\]\([^)\n]+\)"), self.f_link),
        ]

    def highlightBlock(self, text: str) -> None:
        in_fence = self.previousBlockState() == self.IN_FENCE
        if text.lstrip().startswith("```"):
            self.setFormat(0, len(text), self.f_fence)
            self.setCurrentBlockState(0 if in_fence else self.IN_FENCE)
            return
        self.setCurrentBlockState(self.IN_FENCE if in_fence else 0)
        if in_fence:
            self.setFormat(0, len(text), self.f_fence)
            return
        if re.match(r"^#{1,6}\s", text):
            self.setFormat(0, len(text), self.f_head)
            return
        if text.lstrip().startswith(">"):
            self.setFormat(0, len(text), self.f_quote)
        for rx, f in self.rules:
            for m in rx.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), f)


# -------------------------------------------------------------------------------------- preview

PREVIEW_CSS_LIGHT = """
h1, h2, h3, h4 { color: #1b3a5c; }
code { font-family: Consolas; background-color: #eef1f5; color: #24313e; }
pre  { font-family: Consolas; background-color: #f2f4f7; color: #24313e; margin: 8px; }
a    { color: #0f62ae; }
a.hlink { color: #b8c2cc; }
th, td { border: 1px solid #c8cdd4; padding: 4px; }
p.tut-goal { font-style: italic; color: #35506b; }
p.tut-reqs span { background-color: #e4ecf4; color: #27415c; }
figcaption { color: #5f6b76; }
span.stamp { color: #8a94a0; }
blockquote { color: #4f5a64; border-left: 3px solid #c8cdd4; margin-left: 6px; }
"""

# The dark set restates EVERY color pair -- a tinted fill keeps its own ink, never the ground's
# (the naive light boxes under dark body ink were unreadable in the first render).
PREVIEW_CSS_DARK = """
h1, h2, h3, h4 { color: #8fbce8; }
code { font-family: Consolas; background-color: #2c3440; color: #dbe4ee; }
pre  { font-family: Consolas; background-color: #262d38; color: #dbe4ee; margin: 8px; }
a    { color: #74b3e8; }
a.hlink { color: #4c5866; }
th, td { border: 1px solid #46505c; padding: 4px; }
p.tut-goal { font-style: italic; color: #a8bcd2; }
p.tut-reqs span { background-color: #31404f; color: #cfe0f0; }
figcaption { color: #98a4b0; }
span.stamp { color: #7c8894; }
blockquote { color: #a0acb8; border-left: 3px solid #46505c; margin-left: 6px; }
"""


def render_preview_html(text: str) -> str:
    """The page body exactly as the site pipeline renders it (frontmatter chips included);
    the shot-figure upgrade and link rewriting are build-time concerns the preview skips."""
    meta, body_md = B.parse_tutorial_front(text)
    body = B.render_markdown(body_md)
    body, _toc, _census = B.assign_heading_ids(body)
    if meta:
        try:
            strip = B._meta_strip_html(meta)
            # QTextBrowser renders span padding/margin as nothing -- space the chips by hand.
            strip = strip.replace('</span><span class="chip', '</span> &nbsp;<span class="chip')
            body = re.sub(r"(</h1>)", r"\1" + strip.replace("\\", "\\\\"), body, count=1)
        except Exception:  # noqa: BLE001 -- half-typed frontmatter must never kill the preview
            pass
    return body


# ------------------------------------------------------------------------------ new page dialog

class NewPageDialog(QDialog):
    def __init__(self, parent, nav: core.Nav):
        super().__init__(parent)
        self.setWindowTitle("New page")
        form = QFormLayout(self)
        self.location = QComboBox()
        self.location.addItems(list(core.LOCATIONS))
        self.title_edit = QLineEdit()
        self.file_edit = QLineEdit()
        self._file_touched = False
        self.template = QComboBox()
        self.template.addItems(["Blank page", "Tutorial scaffold"])
        self.section = QComboBox()
        self.section.addItem("(unlisted -- lands in the More bucket)")
        self.section.addItems([s.title for s in nav.sections])
        form.addRow("Location", self.location)
        form.addRow("Title", self.title_edit)
        form.addRow("File name", self.file_edit)
        form.addRow("Template", self.template)
        form.addRow("Nav section", self.section)
        hint = QLabel("The file name becomes the URL. The build's link gate will flag anything "
                      "that later links to a name that changed.")
        hint.setWordWrap(True)
        form.addRow(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.title_edit.textChanged.connect(self._sync_filename)
        self.file_edit.textEdited.connect(lambda _t: setattr(self, "_file_touched", True))
        self.resize(460, self.sizeHint().height())

    def _sync_filename(self, title: str) -> None:
        if not self._file_touched:
            self.file_edit.setText(core.slug_filename(title))


# ----------------------------------------------------------------------------------- the window

class StudioWindow(QMainWindow):
    ROLE = Qt.ItemDataRole.UserRole

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        icon = REPO / "ff9mapkit" / "ff9mapkit" / "workspace" / "dreamworldix.ico"
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))

        self.pages: list[core.DocPage] = []
        self.nav = core.load_nav()
        self.nav_dirty = False
        self.current: Path | None = None
        self._newline = "\n"
        self._problems: list[core.Problem] = []
        self._proc = None          # the one tool job at a time
        self._job_label = ""
        self._job_buf = ""
        self._server = None
        self._server_port = 0

        self._build_ui()
        self.refresh_corpus()
        self._restore_state()

    # ---------------------------------------------------------------------------------- layout

    def _build_ui(self) -> None:
        split = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(split)
        self.split = split

        # -- left: the nav tree + its controls
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(4, 4, 4, 4)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemSelectionChanged.connect(self._update_nav_buttons)
        self.tree.itemActivated.connect(self._tree_open)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        lv.addWidget(self.tree, 1)

        def btn(text, slot, tip=""):
            b = QPushButton(text)
            b.clicked.connect(slot)
            if tip:
                b.setToolTip(tip)
            return b

        row1 = QHBoxLayout()
        row1.addWidget(btn("New page…", self.new_page))
        self.section_btn = QToolButton()
        self.section_btn.setText("Sections")
        self.section_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        sec_menu = QMenu(self.section_btn)
        sec_menu.addAction("New section…", self.add_section)
        sec_menu.addAction("Rename section…", self.rename_section)
        sec_menu.addAction("Delete empty section", self.delete_section)
        self.section_btn.setMenu(sec_menu)
        row1.addWidget(self.section_btn)
        row1.addWidget(btn("Refresh", self.refresh_corpus, "Re-scan the docs folders"))
        row1.addStretch(1)
        lv.addLayout(row1)

        row2 = QHBoxLayout()
        self.up_btn = btn("Up", lambda: self.move_selected(-1))
        self.down_btn = btn("Down", lambda: self.move_selected(+1))
        self.moveto_btn = QToolButton()
        self.moveto_btn.setText("Move to")
        self.moveto_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.moveto_btn.setMenu(QMenu(self.moveto_btn))
        self.moveto_btn.menu().aboutToShow.connect(self._fill_moveto)
        self.pin_btn = btn("Pin", self.pin_selected,
                           "Turn a glob-matched or More-bucket page into a literal nav entry "
                           "so it can be reordered")
        self.unlist_btn = btn("Unlist", self.unlist_selected,
                              "Remove the literal entry (the page falls back to a matching "
                              "glob or the More bucket -- it never vanishes)")
        for b in (self.up_btn, self.down_btn, self.moveto_btn, self.pin_btn, self.unlist_btn):
            row2.addWidget(b)
        row2.addStretch(1)
        lv.addLayout(row2)

        row3 = QHBoxLayout()
        self.nav_state = QLabel("nav saved")
        self.save_nav_btn = btn("Save nav", self.save_nav)
        self.revert_nav_btn = btn("Revert nav", self.revert_nav)
        row3.addWidget(self.nav_state)
        row3.addStretch(1)
        row3.addWidget(self.revert_nav_btn)
        row3.addWidget(self.save_nav_btn)
        lv.addLayout(row3)
        split.addWidget(left)

        # -- center: find bar + editor
        mid = QWidget()
        mv = QVBoxLayout(mid)
        mv.setContentsMargins(0, 0, 0, 0)
        self.find_bar = QWidget()
        fb = QHBoxLayout(self.find_bar)
        fb.setContentsMargins(4, 2, 4, 2)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Find in page…")
        self.find_edit.returnPressed.connect(lambda: self.find_next(True))
        fb.addWidget(self.find_edit, 1)
        prev_b = QPushButton("Prev")
        prev_b.clicked.connect(lambda: self.find_next(False))
        next_b = QPushButton("Next")
        next_b.clicked.connect(lambda: self.find_next(True))
        close_b = QPushButton("Close")
        close_b.clicked.connect(self._hide_find)
        for w in (prev_b, next_b, close_b):
            fb.addWidget(w)
        self.find_bar.hide()
        mv.addWidget(self.find_bar)
        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont(MONO, 10))
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.editor.document().modificationChanged.connect(self._update_title)
        self.editor.textChanged.connect(self._schedule_preview)
        self.dark = is_dark_palette()
        self.highlighter = MarkdownHighlighter(self.editor.document(), self.dark)
        mv.addWidget(self.editor, 1)
        split.addWidget(mid)

        # -- right: preview
        self.preview = QTextBrowser()
        self.preview.setOpenLinks(False)
        self.preview.anchorClicked.connect(self._preview_link)
        self.preview.document().setDefaultStyleSheet(
            PREVIEW_CSS_DARK if self.dark else PREVIEW_CSS_LIGHT)
        split.addWidget(self.preview)
        split.setSizes([300, 560, 520])

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(350)
        self._preview_timer.timeout.connect(self.render_preview)

        # -- bottom dock: tools
        dock = QDockWidget("Tools", self)
        dock.setObjectName("tools")
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        tools = QWidget()
        tv = QVBoxLayout(tools)
        tv.setContentsMargins(4, 4, 4, 4)
        bar = QHBoxLayout()
        self.job_buttons = []

        def job_btn(text, slot, tip=""):
            b = btn(text, slot, tip)
            self.job_buttons.append(b)
            bar.addWidget(b)
            return b

        job_btn("Build site", self.run_build, "py docsite/build.py -- every gate, red on rot")
        job_btn("Run tests", self.run_tests, "py -m pytest docsite/tests -q")
        job_btn("Check shots", lambda: self.run_job(
            "Check shots", [sys.executable, str(HERE / "shots.py"), "--check"]),
            "Re-render figures to scratch and report drift (Windows + native Qt)")
        job_btn("Regenerate shots", lambda: self.run_job(
            "Regenerate shots", [sys.executable, str(HERE / "shots.py"), "--all"]),
            "Re-grab every figure after a Workspace reskin")
        job_btn("Harvest UI", lambda: self.run_job(
            "Harvest UI inventory", [sys.executable, str(HERE / "uiharvest.py")]),
            "Refresh assets/ui-inventory.json (the tutorial UI gate's truth)")
        self.stop_btn = btn("Stop job", self.stop_job)
        self.stop_btn.setEnabled(False)
        bar.addWidget(self.stop_btn)
        bar.addSpacing(16)
        self.serve_btn = btn("Serve preview", self.toggle_server,
                             "Local http.server over docsite/_site")
        bar.addWidget(self.serve_btn)
        self.browse_btn = btn("Open in browser", self.open_in_browser,
                              "The current page on the local preview server")
        bar.addWidget(self.browse_btn)
        bar.addStretch(1)
        self.deploy_btn = btn("Deploy…", self.deploy,
                              "Publish to jawnston.com/ff9docs -- asks first")
        self.job_buttons.append(self.deploy_btn)
        bar.addWidget(self.deploy_btn)
        tv.addLayout(bar)

        out_split = QSplitter(Qt.Orientation.Horizontal)
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont(MONO, 9))
        self.console.setMaximumBlockCount(5000)
        out_split.addWidget(self.console)
        pw = QWidget()
        pv = QVBoxLayout(pw)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.addWidget(QLabel("Problems (double-click to open)"))
        self.problems = QListWidget()
        self.problems.itemActivated.connect(self._open_problem)
        pv.addWidget(self.problems, 1)
        out_split.addWidget(pw)
        out_split.setSizes([640, 420])
        tv.addWidget(out_split, 1)
        tools.setMinimumHeight(170)
        dock.setWidget(tools)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

        # -- actions
        save = QAction("Save", self)
        save.setShortcut(QKeySequence.StandardKey.Save)
        save.triggered.connect(self.save_current)
        self.addAction(save)
        find = QAction("Find", self)
        find.setShortcut(QKeySequence.StandardKey.Find)
        find.triggered.connect(self._show_find)
        self.addAction(find)

        self.status_file = QLabel("")
        self.statusBar().addWidget(self.status_file, 1)
        self.status_job = QLabel("")
        self.statusBar().addPermanentWidget(self.status_job)

    # ---------------------------------------------------------------------------- corpus + tree

    def refresh_corpus(self) -> None:
        self.pages = core.corpus()
        self.rebuild_tree()

    def rebuild_tree(self, select_entry: tuple[int, int] | None = None) -> None:
        """Rebuild from the in-memory nav; select_entry=(sec_i, ent_i) restores selection."""
        sections, more = core.resolve_nav(self.nav, self.pages)
        self.tree.clear()
        want = None
        for si, sec in enumerate(sections):
            top = QTreeWidgetItem([f"{sec.title}"])
            top.setData(0, self.ROLE, {"kind": "section", "sec": si})
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            for row in sec.rows:
                label = row.page.title if row.page else row.entry
                suffix = {"auto": "  (auto)", "generated": "  (generated)",
                          "missing": "  (MISSING FILE)"}.get(row.kind, "")
                it = QTreeWidgetItem([label + suffix])
                it.setData(0, self.ROLE, {
                    "kind": row.kind, "sec": si, "ent": row.entry_index,
                    "entry": row.entry, "src": str(row.page.src) if row.page else None})
                it.setToolTip(0, row.page.repo_rel if row.page else row.entry)
                if row.kind == "missing":
                    it.setForeground(0, QColor("#e06c6c" if self.dark else "#b02a2a"))
                elif row.kind in ("auto", "generated"):
                    it.setForeground(0, QColor("#93a0ac" if self.dark else "#6a7580"))
                top.addChild(it)
                if select_entry is not None and row.kind != "auto" \
                        and (si, row.entry_index) == select_entry:
                    want = it
            self.tree.addTopLevelItem(top)
            top.setExpanded(True)
        if more:
            top = QTreeWidgetItem([f"More (unlisted, {len(more)})"])
            top.setData(0, self.ROLE, {"kind": "more-section"})
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            for p in more:
                it = QTreeWidgetItem([p.title])
                it.setData(0, self.ROLE, {"kind": "more", "src": str(p.src),
                                          "entry": core.nav_entry_for(p)})
                it.setToolTip(0, p.repo_rel)
                top.addChild(it)
            self.tree.addTopLevelItem(top)
            top.setExpanded(True)
        if want is not None:
            self.tree.setCurrentItem(want)
        self._mark_current_in_tree()
        self._update_nav_buttons()

    def _sel(self) -> dict | None:
        it = self.tree.currentItem()
        return it.data(0, self.ROLE) if it else None

    def _update_nav_buttons(self) -> None:
        d = self._sel() or {}
        kind = d.get("kind", "")
        literal = kind in ("literal", "generated", "missing")
        self.up_btn.setEnabled(literal)
        self.down_btn.setEnabled(literal)
        self.moveto_btn.setEnabled(literal or kind in ("auto", "more"))
        self.pin_btn.setEnabled(kind in ("auto", "more"))
        self.unlist_btn.setEnabled(literal)
        self.save_nav_btn.setEnabled(self.nav_dirty)
        self.revert_nav_btn.setEnabled(self.nav_dirty)
        self.nav_state.setText("nav MODIFIED" if self.nav_dirty else "nav saved")

    def _touch_nav(self, select_entry: tuple[int, int] | None = None) -> None:
        self.nav_dirty = True
        self.rebuild_tree(select_entry)

    # ------------------------------------------------------------------------------- nav ops

    def move_selected(self, delta: int) -> None:
        d = self._sel()
        if not d or d.get("ent") is None:
            return
        new_i = core.move_entry(self.nav, d["sec"], d["ent"], delta)
        self._touch_nav((d["sec"], new_i))

    def _fill_moveto(self) -> None:
        menu = self.moveto_btn.menu()
        menu.clear()
        d = self._sel()
        if not d:
            return
        for si, sec in enumerate(self.nav.sections):
            if d.get("kind") in ("literal", "generated", "missing") and si == d["sec"]:
                continue
            menu.addAction(sec.title, lambda si=si: self._move_to(si))

    def _move_to(self, dst: int) -> None:
        d = self._sel()
        if not d:
            return
        if d["kind"] in ("literal", "generated", "missing"):
            core.transfer_entry(self.nav, d["sec"], d["ent"], dst)
        else:                                    # auto / more: pin straight into the target
            core.add_entry(self.nav, dst, d["entry"])
        self._touch_nav((dst, len(self.nav.sections[dst].entries) - 1))

    def pin_selected(self) -> None:
        d = self._sel()
        if not d or d["kind"] not in ("auto", "more"):
            return
        if d["kind"] == "auto":                  # a literal entry above the glob keeps its spot
            core.add_entry(self.nav, d["sec"], d["entry"], at=d["ent"])
            self._touch_nav((d["sec"], d["ent"]))
        else:
            QMessageBox.information(self, "Pin", "Use Move to and pick a section -- a More-bucket "
                                                 "page pins by joining a section.")

    def unlist_selected(self) -> None:
        d = self._sel()
        if not d or d.get("ent") is None:
            return
        core.remove_entry(self.nav, d["sec"], d["ent"])
        self._touch_nav()

    def add_section(self) -> None:
        title, ok = QInputDialog.getText(self, "New section", "Section title:")
        if ok and title.strip():
            self.nav.sections.append(core.NavSection(title.strip()))
            self._touch_nav()

    def _current_section_index(self) -> int | None:
        d = self._sel()
        if not d:
            return None
        if d.get("kind") == "section":
            return d["sec"]
        return d.get("sec")

    def rename_section(self) -> None:
        si = self._current_section_index()
        if si is None:
            return
        title, ok = QInputDialog.getText(self, "Rename section", "Section title:",
                                         text=self.nav.sections[si].title)
        if ok and title.strip():
            self.nav.sections[si].title = title.strip()
            self._touch_nav()

    def delete_section(self) -> None:
        si = self._current_section_index()
        if si is None:
            return
        if self.nav.sections[si].entries:
            QMessageBox.warning(self, "Delete section",
                                "Only an empty section can be deleted -- move its pages out first.")
            return
        del self.nav.sections[si]
        self._touch_nav()

    def save_nav(self) -> None:
        core.save_nav(self.nav)
        self.nav_dirty = False
        self._update_nav_buttons()
        self._log("nav.toml saved")

    def revert_nav(self) -> None:
        self.nav = core.load_nav()
        self.nav_dirty = False
        self.rebuild_tree()

    # ------------------------------------------------------------------------------ page files

    def new_page(self) -> None:
        dlg = NewPageDialog(self, self.nav)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        dir_rel = core.LOCATIONS[dlg.location.currentText()]
        title = dlg.title_edit.text().strip() or "Untitled"
        filename = dlg.file_edit.text().strip() or core.slug_filename(title)
        template = "tutorial" if dlg.template.currentIndex() == 1 else "blank"
        try:
            dst = core.create_page(REPO / dir_rel, filename, title, template)
        except (ValueError, FileExistsError) as e:
            QMessageBox.warning(self, "New page", str(e))
            return
        self.pages = core.corpus()
        sec_i = dlg.section.currentIndex() - 1
        if sec_i >= 0:
            page = next(p for p in self.pages if p.src == dst)
            core.add_entry(self.nav, sec_i, core.nav_entry_for(page))
            self._touch_nav((sec_i, len(self.nav.sections[sec_i].entries) - 1))
        else:
            self.rebuild_tree()
        self.open_page(dst)

    def _tree_open(self, item: QTreeWidgetItem) -> None:
        d = item.data(0, self.ROLE) or {}
        if d.get("src"):
            self.open_page(Path(d["src"]))

    def _tree_menu(self, pos) -> None:
        it = self.tree.itemAt(pos)
        if it is None:
            return
        self.tree.setCurrentItem(it)
        d = it.data(0, self.ROLE) or {}
        if not d.get("src"):
            return
        src = Path(d["src"])
        menu = QMenu(self)
        menu.addAction("Open", lambda: self.open_page(src))
        menu.addAction("Show in Explorer",
                       lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(src.parent))))
        menu.addAction("Copy repo path", lambda: QApplication.clipboard().setText(
            src.relative_to(REPO).as_posix()))
        menu.addSeparator()
        menu.addAction("Rename file…", lambda: self.rename_file(src))
        menu.addAction("Delete file…", lambda: self.delete_file(src))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def rename_file(self, src: Path) -> None:
        new, ok = QInputDialog.getText(
            self, "Rename file",
            "New file name (other pages linking the old name will fail the build's link gate\n"
            "until re-pointed -- run Build site after):", text=src.name)
        if not ok or new.strip() == src.name:
            return
        old_page = next((p for p in self.pages if p.src == src), None)
        try:
            dst = core.rename_page(src, new.strip())
        except (ValueError, FileExistsError, OSError) as e:
            QMessageBox.warning(self, "Rename file", str(e))
            return
        if old_page is not None:
            new_page = core.DocPage(src=dst, repo_rel=dst.relative_to(REPO).as_posix(),
                                    out_rel="", title="")
            if core.rename_page_entries(self.nav, core.nav_entry_for(old_page),
                                        core.nav_entry_for(new_page)):
                self.nav_dirty = True
        if self.current == src:
            self.current = dst
        self.refresh_corpus()
        self._log(f"renamed {src.name} -> {dst.name} (run Build site to catch broken links)")

    def delete_file(self, src: Path) -> None:
        if QMessageBox.question(
                self, "Delete file",
                f"Delete {src.relative_to(REPO).as_posix()}?\n\nThe file is git-tracked, so "
                f"`git checkout` can restore it; pages linking it will fail the next build.",
        ) != QMessageBox.StandardButton.Yes:
            return
        page = next((p for p in self.pages if p.src == src), None)
        try:
            src.unlink()
        except OSError as e:
            QMessageBox.warning(self, "Delete file", str(e))
            return
        if page is not None and core.remove_page_everywhere(self.nav, core.nav_entry_for(page)):
            self.nav_dirty = True
        if self.current == src:
            self.current = None
            self.editor.blockSignals(True)
            self.editor.clear()
            self.editor.blockSignals(False)
            self.editor.document().setModified(False)
            self.preview.clear()
        self.refresh_corpus()
        self._log(f"deleted {src.name}")

    # --------------------------------------------------------------------------------- editing

    def maybe_save(self) -> bool:
        """True = safe to proceed (saved or discarded); False = user cancelled."""
        if self.current is None or not self.editor.document().isModified():
            return True
        r = QMessageBox.question(
            self, "Unsaved changes", f"Save changes to {self.current.name}?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            self.save_current()
            return True
        return r == QMessageBox.StandardButton.Discard

    def open_page(self, src: Path) -> None:
        if self.current == src:
            return
        if not self.maybe_save():
            return
        try:
            raw = src.read_bytes()
        except OSError as e:
            QMessageBox.warning(self, "Open", str(e))
            return
        self._newline = "\r\n" if b"\r\n" in raw else "\n"
        text = raw.decode("utf-8").replace("\r\n", "\n")
        self.current = src
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
        self.editor.document().setModified(False)
        self._update_title()
        self.render_preview()
        self._mark_current_in_tree()

    def save_current(self) -> None:
        if self.current is None:
            return
        text = self.editor.toPlainText()
        if not text.endswith("\n"):
            text += "\n"
        try:
            self.current.write_text(text, encoding="utf-8", newline=self._newline)
        except OSError as e:
            QMessageBox.warning(self, "Save", str(e))
            return
        self.editor.document().setModified(False)
        self._update_title()
        self._log(f"saved {self.current.relative_to(REPO).as_posix()}")
        # A retitled page renames its tree row; cheap enough to just re-census.
        sel = self.current
        self.pages = core.corpus()
        self.rebuild_tree()
        self.current = sel

    def _update_title(self) -> None:
        star = "*" if self.editor.document().isModified() else ""
        name = self.current.relative_to(REPO).as_posix() if self.current else "no page open"
        self.setWindowTitle(f"{APP_TITLE} -- {name}{star}")
        self.status_file.setText(f"{name}{star}")

    def _mark_current_in_tree(self) -> None:
        cur = str(self.current) if self.current else None
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                it = top.child(j)
                d = it.data(0, self.ROLE) or {}
                f = it.font(0)
                f.setUnderline(d.get("src") == cur)
                it.setFont(0, f)

    # ---------------------------------------------------------------------------------- find

    def _show_find(self) -> None:
        self.find_bar.show()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def _hide_find(self) -> None:
        self.find_bar.hide()
        self.editor.setFocus()

    def find_next(self, forward: bool) -> None:
        needle = self.find_edit.text()
        if not needle:
            return
        from PySide6.QtGui import QTextDocument
        flags = QTextDocument.FindFlag(0) if forward else QTextDocument.FindFlag.FindBackward
        if not self.editor.find(needle, flags):        # wrap once
            cur = self.editor.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.Start if forward
                             else QTextCursor.MoveOperation.End)
            self.editor.setTextCursor(cur)
            self.editor.find(needle, flags)

    def keyPressEvent(self, ev):  # Esc closes the find bar
        if ev.key() == Qt.Key.Key_Escape and self.find_bar.isVisible():
            self._hide_find()
            return
        super().keyPressEvent(ev)

    # --------------------------------------------------------------------------------- preview

    def _schedule_preview(self) -> None:
        self._preview_timer.start()

    def render_preview(self) -> None:
        if self.current is None:
            return
        try:
            body = render_preview_html(self.editor.toPlainText())
        except Exception as e:  # noqa: BLE001 -- a half-typed page must never crash the app
            body = f"<p><b>Preview error:</b> {_html.escape(str(e))}</p>"
        scroll = self.preview.verticalScrollBar().value()
        self.preview.document().setBaseUrl(QUrl.fromLocalFile(str(self.current.parent) + "/"))
        self.preview.setHtml(body)
        self.preview.verticalScrollBar().setValue(scroll)

    def _preview_link(self, url: QUrl) -> None:
        if url.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)
            return
        if not url.toString().startswith("#") and url.isLocalFile():
            path = Path(url.toLocalFile())
            if path.suffix.lower() == ".md" and path.exists():
                self.open_page(path)
                return
            if path.exists():
                QDesktopServices.openUrl(url)
                return
        frag = url.fragment()
        if frag:
            self.preview.scrollToAnchor(frag)

    # ------------------------------------------------------------------------------------ jobs

    def _log(self, line: str) -> None:
        self.console.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {line}")

    def run_job(self, label: str, args: list[str], cwd: Path = REPO) -> None:
        from PySide6.QtCore import QProcess
        if self._proc is not None:
            QMessageBox.information(self, label, "A job is already running -- stop it first.")
            return
        self._job_label = label
        self._job_buf = ""
        self._log(f"{label}: {' '.join(args)}")
        p = QProcess(self)
        p.setWorkingDirectory(str(cwd))
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.readyReadStandardOutput.connect(self._job_output)
        p.finished.connect(self._job_finished)
        p.errorOccurred.connect(lambda _e: self._job_finished(-1, None))
        self._proc = p
        for b in self.job_buttons:
            b.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_job.setText(f"running: {label}")
        p.start(args[0], args[1:])

    def _job_output(self) -> None:
        if self._proc is None:
            return
        text = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        self._job_buf += text
        for line in text.splitlines():
            self.console.appendPlainText(line)

    def _job_finished(self, code: int, _status) -> None:
        if self._proc is None:
            return
        self._proc.deleteLater()
        self._proc = None
        for b in self.job_buttons:
            b.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_job.setText("")
        verdict = "OK" if code == 0 else f"FAILED (exit {code})"
        self._log(f"{self._job_label}: {verdict}")
        if self._job_label in ("Build site", "Deploy"):
            self._fill_problems(core.parse_problems(self._job_buf))

    def stop_job(self) -> None:
        if self._proc is not None:
            self._proc.kill()

    def _fill_problems(self, problems: list[core.Problem]) -> None:
        self._problems = problems
        self.problems.clear()
        for pr in problems:
            it = QListWidgetItem(f"{pr.rel or '(general)'}: {pr.message}")
            src = core.problem_source(pr, self.pages)
            it.setData(Qt.ItemDataRole.UserRole, str(src) if src else None)
            self.problems.addItem(it)
        if problems:
            self._log(f"{len(problems)} problem(s) -- double-click to open")

    def _open_problem(self, item: QListWidgetItem) -> None:
        src = item.data(Qt.ItemDataRole.UserRole)
        if src:
            self.open_page(Path(src))

    def run_build(self) -> None:
        if not self.maybe_save():
            return
        if self.nav_dirty:
            self.save_nav()
        self.problems.clear()
        self.run_job("Build site", [sys.executable, str(HERE / "build.py")])

    def run_tests(self) -> None:
        self.run_job("Docsite tests",
                     [sys.executable, "-m", "pytest", str(HERE / "tests"), "-q"])

    # ---------------------------------------------------------------------------- serve + deploy

    def toggle_server(self) -> None:
        from PySide6.QtCore import QProcess
        if self._server is not None:
            self._server.kill()
            return
        site = HERE / "_site"
        if not site.is_dir():
            self._log("no _site/ yet -- run Build site first")
            return
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        p = QProcess(self)
        p.setWorkingDirectory(str(REPO))
        p.finished.connect(self._server_gone)
        p.errorOccurred.connect(lambda _e: self._server_gone())
        p.start(sys.executable, ["-m", "http.server", str(port),
                                 "--bind", "127.0.0.1", "-d", str(site)])
        self._server, self._server_port = p, port
        self.serve_btn.setText(f"Stop server :{port}")
        self._log(f"preview server: http://127.0.0.1:{port}/")

    def _server_gone(self) -> None:
        if self._server is not None:
            self._server.deleteLater()
            self._server = None
            self.serve_btn.setText("Serve preview")
            self._log("preview server stopped")

    def open_in_browser(self) -> None:
        if self._server is None:
            self.toggle_server()
            if self._server is None:
                return
        rel = "index.html"
        if self.current is not None:
            page = next((p for p in self.pages if p.src == self.current), None)
            if page:
                rel = page.out_rel
        QDesktopServices.openUrl(QUrl(f"http://127.0.0.1:{self._server_port}/{rel}"))

    def deploy(self) -> None:
        script = HERE / "deploy.ps1"
        if QMessageBox.question(
                self, "Deploy the Manual",
                "This publishes the site to https://jawnston.com/ff9docs/ -- an outward-facing "
                "action.\n\ndeploy.ps1 rebuilds fresh first (a red build never deploys) and keeps "
                "the prior deploy at ff9docs.old for rollback.\n\nDeploy now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Yes:
            return
        if not self.maybe_save():
            return
        if self.nav_dirty:
            self.save_nav()
        self.run_job("Deploy", ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                "-File", str(script)])

    # ----------------------------------------------------------------------------- persistence

    def _settings(self) -> QSettings:
        return QSettings("DreamWorldIX", "DocsStudio")

    def _restore_state(self) -> None:
        s = self._settings()
        geo = s.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        else:
            self.resize(1480, 900)
        sizes = s.value("split")
        if sizes:
            try:
                self.split.setSizes([int(x) for x in sizes])
            except (TypeError, ValueError):
                pass
        last = s.value("last_file")
        if last and Path(last).is_file():
            self.open_page(Path(last))
        self._update_title()

    def closeEvent(self, ev) -> None:
        if not self.maybe_save():
            ev.ignore()
            return
        if self.nav_dirty:
            r = QMessageBox.question(
                self, "Unsaved nav", "Save the reorganized nav.toml?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Cancel:
                ev.ignore()
                return
            if r == QMessageBox.StandardButton.Save:
                self.save_nav()
        s = self._settings()
        s.setValue("geometry", self.saveGeometry())
        s.setValue("split", self.split.sizes())
        s.setValue("last_file", str(self.current) if self.current else "")
        if self._server is not None:
            self._server.kill()
        if self._proc is not None:
            self._proc.kill()
        super().closeEvent(ev)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_TITLE)
    win = StudioWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
