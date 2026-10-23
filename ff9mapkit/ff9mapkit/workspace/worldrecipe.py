"""The World tab's recipe bar (overworld editor rung C3): the draft as a ``world-fuse`` recipe.

Every Accept of a carry tool is one row of the draft's recipe (``world.draft.history``). The bar says how many, walks
them with Undo and Redo (byte for byte, from each step's snapshots: no verb re-runs), saves them as a TOML that
``world-fuse`` composes (``world.recipe.dumps``), and opens one: a fresh draft, then each row composed by
``world-fuse`` itself, one job per row, so every row is its own undoable step.

THE CLI STAYS THE ORACLE here too: opening a recipe never carves in the Workspace's process.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMessageBox, QPushButton, QWidget

from . import widgets
from .worldforest import QProcessRunner, kit_cwd


class RecipeBar(QWidget):
    """``source_fn()`` the mod folder the tab shows; ``game_fn()`` the install; ``on_changed(draft)`` re-reads the
    view and the tools after the draft moved. ``runner``, ``ask``, ``save_path_fn(default)`` / ``open_path_fn()``
    (file dialogs) and ``drafts_root`` are the test and snap seams."""

    def __init__(self, pal, *, game_fn, source_fn, on_changed=None, runner=None, drafts_root=None, ask=None,
                 save_path_fn=None, open_path_fn=None):
        super().__init__()
        self.pal = pal
        self._game_fn, self._source_fn, self._on_changed = game_fn, source_fn, on_changed
        self._runner = runner or QProcessRunner()
        self._drafts_root = drafts_root
        self._ask = ask or (lambda title, text: QMessageBox.question(self, title, text)
                            == QMessageBox.StandardButton.Yes)
        self._save_path_fn = save_path_fn or self._save_dialog
        self._open_path_fn = open_path_fn or self._open_dialog
        self._queue = None                               # an opened recipe's rows still to compose
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 0, 2, 0)
        lay.setSpacing(8)
        lay.addWidget(widgets.role_label("Recipe", "cardtitle"))
        self.status_lbl = widgets.role_label("", "caption")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setAccessibleName("Recipe")
        lay.addWidget(self.status_lbl, 1)
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setProperty("role", "quiet")
        self.undo_btn.clicked.connect(self.undo)
        lay.addWidget(self.undo_btn)
        self.redo_btn = QPushButton("Redo")
        self.redo_btn.setProperty("role", "quiet")
        self.redo_btn.clicked.connect(self.redo)
        lay.addWidget(self.redo_btn)
        self.save_btn = QPushButton("Save recipe…")
        self.save_btn.setProperty("role", "quiet")
        self.save_btn.setToolTip("Write the draft's edits as a recipe world-fuse composes: ff9mapkit world-fuse "
                                 "<recipe> --mod-folder <folder> makes the same bytes.")
        self.save_btn.clicked.connect(self.save)
        lay.addWidget(self.save_btn)
        self.open_btn = QPushButton("Open recipe…")
        self.open_btn.setProperty("role", "quiet")
        self.open_btn.setToolTip("Compose a recipe into a fresh draft of this folder, one world-fuse job per row "
                                 "(each row undoable). The install is not touched.")
        self.open_btn.clicked.connect(self.open_recipe)
        lay.addWidget(self.open_btn)
        self.refresh()

    # -- the draft --
    def source(self) -> Path:
        return Path(self._source_fn())

    def draft(self):
        from ..world import draft as D
        p = D.draft_path(self.source(), root=self._drafts_root)
        return p if D.read_meta(p) is not None else None

    def refresh(self):
        """Say what the recipe holds and which way it can walk."""
        from ..world import draft as D
        d = self.draft()
        h = D.history(d) if d is not None else {"steps": [], "cursor": 0, "promoted": 0}
        steps, cur, prom = h["steps"], h["cursor"], h["promoted"]
        busy = self._queue is not None
        if not steps:
            text = "No edits yet: each Accept adds a row, and Save recipe writes them for world-fuse."
        else:
            text = f"{cur} step{'s' if cur != 1 else ''}"
            if cur:
                text += f", the last {steps[cur - 1]['label']}"
            if len(steps) > cur:
                text += f"; {len(steps) - cur} undone"
            if prom:
                text += f"; the first {prom} in the game (promoted)"
        if busy:
            left = len(self._queue["rows"])
            text = f"Composing {self._queue['name']}: {self._queue['done']} row(s) done, {left} to go…"
        self.status_lbl.setText(text)
        widgets.set_state(self.status_lbl, "")
        self.undo_btn.setEnabled(not busy and cur > prom)
        self.undo_btn.setToolTip(f"Undo: {steps[cur - 1]['label']}" if cur > prom else
                                 "The steps here are in the game: Revert promote first." if cur else "Nothing to undo.")
        self.redo_btn.setEnabled(not busy and len(steps) > cur)
        self.redo_btn.setToolTip(f"Redo: {steps[cur]['label']}" if len(steps) > cur else "Nothing to redo.")
        self.save_btn.setEnabled(not busy and cur > 0)
        self.open_btn.setEnabled(not busy)

    def _moved(self, note=None, state="ok"):
        self.refresh()
        if self._on_changed is not None:
            self._on_changed(self.draft())               # (the tab refreshes this bar too: the note goes last)
        if note:
            widgets.set_state(self.status_lbl, state)
            self.status_lbl.setText(note)

    # -- undo, redo --
    def undo(self):
        from ..world import draft as D
        d = self.draft()
        if d is None:
            return
        try:
            s = D.undo(d)
        except ValueError as e:
            self._moved(f"Not undone: {e}.", "error")
            return
        self._moved(f"Undone: {s['label']}.", "")

    def redo(self):
        from ..world import draft as D
        d = self.draft()
        if d is None:
            return
        try:
            s = D.redo(d)
        except ValueError as e:
            self._moved(f"Not redone: {e}.", "error")
            return
        self._moved(f"Redone: {s['label']}.", "")

    # -- save, open --
    def recipe_text(self) -> str:
        from ..world import draft as D
        from ..world import recipe as RC
        return RC.dumps(D.recipe_rows(self.draft()), base=self.source().name)

    def save(self):
        d = self.draft()
        if d is None:
            return
        path = self._save_path_fn(f"{self.source().name}-recipe.toml")
        if not path:
            return
        Path(path).write_text(self.recipe_text(), encoding="utf-8")
        self._moved(f"Saved the recipe to {path}.", "ok")

    def open_recipe(self):
        from ..world import draft as D
        from ..world import recipe as RC
        path = self._open_path_fn()
        if not path:
            return
        try:
            rows = RC.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            self._moved(f"Not opened: {e}.", "error")
            return
        d = self.draft()
        if d is not None and (D.history(d)["steps"] or D.edits(d)):
            if not self._ask("Replace the draft?", f"Compose {Path(path).name} into a fresh draft of "
                             f"{self.source().name}? The draft's current edits and their history are deleted (the "
                             "install is not touched)."):
                return
        if d is not None:
            D.discard(d, root=self._drafts_root)
        d = D.ensure_draft(self.source(), game=self._game_fn(), root=self._drafts_root)
        self._queue = {"name": Path(path).name, "rows": list(rows), "done": 0}
        self._next_row(d)

    def _next_row(self, d):
        from ..world import draft as D
        from ..world import recipe as RC
        q = self._queue
        if not q["rows"]:
            self._queue = None
            self._moved(f"Composed {q['name']}: {q['done']} row{'s' if q['done'] != 1 else ''} into the draft.", "ok")
            return
        row = q["rows"][0]
        D.begin_step(d, RC.row_cells(row))
        tmp = Path(tempfile.mkdtemp(prefix="ff9_recipe_")) / "row.toml"
        tmp.write_text(RC.dumps_one({k: v for k, v in row.items()}), encoding="utf-8")
        argv = [sys.executable, "-m", "ff9mapkit", "--game", str(self._game_fn()), "world-fuse", str(tmp),
                "--mod-folder", str(d)]
        self.refresh()
        self._runner.start(argv, kit_cwd(), lambda code, text: self._row_done(d, row, code, text))

    def _row_done(self, d, row, code, text):
        from ..world import draft as D
        from ..world import recipe as RC
        q = self._queue
        if q is None:
            return
        if code != 0:
            D.abort_step(d)
            self._queue = None
            last = [ln for ln in text.splitlines() if ln.strip()][-1:] or [f"exit code {code}"]
            self._moved(f"Stopped at {RC.label(row)} ({q['done']} row(s) composed): {last[0]}", "error")
            return
        D.commit_step(d, row, RC.label(row))
        q["rows"].pop(0)
        q["done"] += 1
        if self._on_changed is not None:
            self._on_changed(d)
        self._next_row(d)

    def _save_dialog(self, default):
        path, _f = QFileDialog.getSaveFileName(self, "Save recipe", default, "Recipe (*.toml)")
        return path

    def _open_dialog(self):
        path, _f = QFileDialog.getOpenFileName(self, "Open recipe", "", "Recipe (*.toml)")
        return path

    def retheme(self, pal):
        self.pal = pal
