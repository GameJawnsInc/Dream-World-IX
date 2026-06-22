"""A modal editor for a journey's ``[journey.tuning]`` -- the mod-GLOBAL player/ability CSV deltas (BaseStats /
abilities / leveling / status / ...). It REUSES the battle "Party & abilities" specs verbatim
(:data:`ff9mapkit.editor.battle_forms.PLAYER_TABLES`) over the shared tk-free form machinery
(:mod:`ff9mapkit.editor.forms` + :mod:`forms_qt`), so the same tables a battle.toml carries are authored here at
the journey level -- the placement the user chose (mod-global tuning = journey).

The dialog is self-contained: a left row-list (one per tuning entry, ``<table> · <selector>``), a right form host,
Add / Remove, and OK/Cancel. ``result_tuning`` holds the edited ``{block: [rows]}`` dict on accept (else None); the
caller (:meth:`ff9mapkit.workspace.shell.Workspace.on_set_journey_tuning`) writes it back with
:func:`ff9mapkit.journey.set_journey_tuning`. The nested player tables (``[[learn]]`` / ``[[ability_feature]]`` /
``[[status_set]]`` / ``[[magic_sword_set]]``) stay hand-authored -- as everywhere else -- and are left untouched.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel, QListWidget, QPushButton, QScrollArea,
    QSplitter, QVBoxLayout, QWidget,
)

from ..editor import battle_forms as bf
from ..editor import forms
from .forms_qt import build_form, read


class TuningDialog(QDialog):
    """Edit a journey's ``[journey.tuning]`` player/ability CSV blocks. ``tuning`` is the current ``{block:
    [rows]}`` (only the KNOWN player-table blocks are editable; unknown/nested ones are preserved by the caller's
    text writer, untouched here). On accept, :attr:`result_tuning` is the edited dict (blocks with no rows
    dropped); on cancel it's None."""

    def __init__(self, parent, palette, jid, tuning, *, is_bare=False):
        super().__init__(parent)
        self.pal = palette
        self.jid = jid
        self.setWindowTitle(f"Tuning — {jid}")
        self.resize(660, 470)
        # a working COPY of just the FORM-editable blocks (the 7 PLAYER_SPECS); deep enough that Cancel discards.
        self.tuning = {k: [dict(r) for r in (tuning.get(k) or []) if isinstance(r, dict)]
                       for k in bf.PLAYER_SPECS if tuning.get(k)}
        # the nested blocks this dialog does NOT edit (learn / ability_feature / status_set / magic_sword_set, +
        # any unknown key) — carried through verbatim so an edit never DESTROYS hand-authored tuning.
        self._untouched = {k: v for k, v in (tuning or {}).items() if k not in bf.PLAYER_SPECS}
        self._rows: list = []          # [(block, idx)] parallel to the list widget
        self._ctx = None               # {block, idx, spec, getters} for the mounted form
        self.result_tuning = None
        self._build_ui(is_bare)
        self._rebuild()
        if self.rows.count():
            self.rows.setCurrentRow(0)

    # ------------------------------------------------------------------ UI
    def _build_ui(self, is_bare):
        outer = QVBoxLayout(self)
        intro = QLabel("Mod-GLOBAL player/ability tuning for this journey — the same BaseStats / abilities / "
                       "leveling deltas a field.toml carries, injected into the entry member at deploy. One CSV "
                       "per mod (shared across a multi-journey hub).")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color:{self.pal['muted']};")
        outer.addWidget(intro)
        if is_bare:
            warn = QLabel("⚠ This is a BARE single-field journey — tuning is injected into a MULTI-campaign entry "
                          "member, so it WON'T apply here. Put the deltas on the entry field's own field.toml.")
            warn.setWordWrap(True)
            warn.setStyleSheet(f"color:{self.pal['warn']};")
            outer.addWidget(warn)

        split = QSplitter()
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.rows = QListWidget()
        self.rows.currentRowChanged.connect(self._on_row)
        lv.addWidget(self.rows, 1)
        self.add_btn = QPushButton("Add tuning…")
        self.add_btn.clicked.connect(self._add)
        lv.addWidget(self.add_btn)
        self.del_btn = QPushButton("Remove selected")
        self.del_btn.clicked.connect(self._remove)
        self.del_btn.setEnabled(False)
        lv.addWidget(self.del_btn)
        split.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.host_scroll = QScrollArea()
        self.host_scroll.setWidgetResizable(True)
        self.host_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.host = QWidget()
        self.host_lay = QVBoxLayout(self.host)
        self.host_scroll.setWidget(self.host)
        rv.addWidget(self.host_scroll, 1)
        split.addWidget(right)
        split.setSizes([220, 430])
        outer.addWidget(split, 1)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        outer.addWidget(bb)
        self._placeholder("Add a tuning row, or pick one to edit.")

    def _clear(self):
        while self.host_lay.count():
            it = self.host_lay.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()

    def _placeholder(self, text):
        self._clear()
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{self.pal['muted']};")
        lbl.setWordWrap(True)
        self.host_lay.addWidget(lbl)
        self.host_lay.addStretch(1)

    # ------------------------------------------------------------------ row list
    def _all_rows(self):
        return [(block, i) for block in bf.PLAYER_SPECS for i in range(len(self.tuning.get(block) or []))]

    def _rebuild(self):
        self.rows.blockSignals(True)
        self.rows.clear()
        self._rows = []
        for block, i in self._all_rows():
            row = self.tuning[block][i]
            self.rows.addItem(f"{bf.PLAYER_LABEL[block]}  ·  {row.get(bf.PLAYER_SELECTOR[block], i)}")
            self._rows.append((block, i))
        self.rows.blockSignals(False)

    def _on_row(self, r):
        if not (0 <= r < len(self._rows)):
            self.del_btn.setEnabled(False)
            return
        self._commit()
        block, idx = self._rows[r]
        self.del_btn.setEnabled(True)
        if 0 <= idx < len(self.tuning.get(block) or []):
            self._mount(block, idx)

    def _mount(self, block, idx):
        self._clear()
        spec = bf.PLAYER_SPECS[block]
        form, getters = build_form(spec, forms.entity_to_values(spec, self.tuning[block][idx]), self.pal)
        self.host_lay.addWidget(form)
        self.host_lay.addStretch(1)
        self._ctx = {"block": block, "idx": idx, "spec": spec, "getters": getters}

    def _fold(self, ctx) -> bool:
        try:
            entity = forms.build_entity(ctx["spec"], read(ctx["getters"]))
        except ValueError:
            return False
        lst = self.tuning.get(ctx["block"]) or []
        if not (0 <= ctx["idx"] < len(lst)):
            return False                                   # a stale ctx (its row was removed)
        lst[ctx["idx"]] = entity
        return True

    def _commit(self) -> bool:
        return self._fold(self._ctx) if self._ctx else True

    def _select(self, block, idx):
        for r, node in enumerate(self._rows):
            if node == (block, idx):
                self.rows.setCurrentRow(r)
                return

    # ------------------------------------------------------------------ add / remove
    def _add(self):
        self._commit()
        block = self._pick_table()
        if not block:
            return
        self.tuning.setdefault(block, []).append(dict(bf.PLAYER_DEFAULT[block]))
        self._rebuild()
        self._select(block, len(self.tuning[block]) - 1)

    def _pick_table(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add tuning")
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("Tune which player-side table? It's mod-global — applied to the whole journey."))
        combo = QComboBox()
        for key, label, *_ in bf.PLAYER_TABLES:
            combo.addItem(label, key)
        lay.addWidget(combo)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        return combo.currentData()

    def _remove(self):
        r = self.rows.currentRow()
        if not (0 <= r < len(self._rows)):
            return
        block, idx = self._rows[r]
        lst = self.tuning.get(block) or []
        if not (0 <= idx < len(lst)):
            return
        self._ctx = None                                   # the mounted form's row is going away — don't commit it
        del lst[idx]
        if not lst:
            self.tuning.pop(block, None)
        self._rebuild()
        nxt = min(r, self.rows.count() - 1)
        if 0 <= nxt < self.rows.count():
            self.rows.setCurrentRow(nxt)
        else:
            self._placeholder("Add a tuning row, or pick one to edit.")
            self.del_btn.setEnabled(False)

    # ------------------------------------------------------------------ accept
    def _accept(self):
        if not self._commit():
            return                                         # an invalid field stays open (the form highlights it)
        # the edited form blocks OVER the carried-through nested blocks (disjoint keys -> a clean union)
        self.result_tuning = {**self._untouched, **{b: rows for b, rows in self.tuning.items() if rows}}
        self.accept()
