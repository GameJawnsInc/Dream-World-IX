"""A generic Qt form renderer for :mod:`..editor.forms` specs (Phase 4 of the GUI makeover).

Builds a Qt form (a labelled widget per :class:`..editor.forms.Field`) + a dict of value getters from a
spec + flat values. Saving goes through ``forms.build_entity`` -- the SAME tk-free parser the tkinter
editor uses -- so a field edited in the Qt shell round-trips byte-identically to one edited in the old
editor. The renderer is thin; all parsing/validation stays in ``editor.forms`` (unit-tested headless).

Mapping: BOOL -> QCheckBox, PRESET -> an editable QComboBox seeded with the archetype names (a custom
string is still accepted), everything else -> a QLineEdit. A catalog-backed field also gets a "Browse…"
button wired to :class:`CatalogPicker`, which reuses the UI-agnostic ``infohub.browse`` spine (exactly
like the tkinter editor's picker) so the two stay in lockstep.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QPushButton, QVBoxLayout, QWidget,
)

from .. import infohub
from ..editor import forms


def build_form(spec, values: dict, palette: dict, pick=None):
    """Return ``(widget, getters)`` for ``spec`` + flat ``values`` (from ``forms.entity_to_values``).

    ``getters`` maps each field key to a 0-arg callable returning the widget's current value. ``pick``
    (optional) is ``pick(catalog: str, current: str) -> str | None``; when given, catalog-backed fields
    get a "Browse…" button that calls it and writes the chosen name back into the widget."""
    w = QWidget()
    lay = QFormLayout(w)
    lay.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)
    lay.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    lay.setHorizontalSpacing(14)
    lay.setVerticalSpacing(10)
    getters = {}

    def browse(field, getter, setter):
        name = pick(field.catalog, getter())
        if name:
            setter(name)

    for f in spec:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        setter = None
        if f.kind == forms.BOOL:
            cb = QCheckBox()
            cb.setChecked(bool(values.get(f.key, f.default)))
            widget, getters[f.key] = cb, cb.isChecked
        elif f.kind == forms.PRESET:
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItems(list(forms.PRESETS))
            combo.setCurrentText(str(values.get(f.key, "") or ""))
            widget, getters[f.key], setter = combo, combo.currentText, combo.setCurrentText
        else:
            le = QLineEdit(str(values.get(f.key, "") or ""))
            if f.catalog:
                le.setPlaceholderText(f"a {f.catalog.split(',')[0]} name or id")
            widget, getters[f.key], setter = le, le.text, le.setText
        if f.catalog and pick is not None and setter is not None:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(widget, 1)
            b = QPushButton("Browse…")
            b.clicked.connect(lambda _=False, ff=f, g=getters[f.key], st=setter: browse(ff, g, st))
            row.addWidget(b)
            v.addLayout(row)
        else:
            v.addWidget(widget)
        if f.help:
            hint = QLabel(f.help)
            hint.setWordWrap(True)
            hint.setStyleSheet(f"color:{palette['muted']};font-size:11px;")
            v.addWidget(hint)
        label = QLabel(f.label + ":")
        label.setStyleSheet("font-weight:500;")
        lay.addRow(label, box)
    return w, getters


def read(getters: dict) -> dict:
    """Collect the current ``{key: value}`` from a getters dict (call each getter)."""
    return {k: g() for k, g in getters.items()}


class CatalogPicker(QDialog):
    """A modal Info-Hub catalog picker: search + a result list, returning the chosen entry NAME. Reuses
    the same ``infohub.browse`` spine as the tkinter editor's picker (archetype/creature/item/flag/...)."""

    def __init__(self, parent, kinds, initial, plan, palette, *, browse=False, limit=300):
        super().__init__(parent)
        self.setWindowTitle("Browse the catalog" if browse else "Pick from the catalog")
        self.resize(560, 460)
        self.kinds = kinds
        self.plan = plan
        self.browse = browse                           # browse mode: "Use this" copies the name + stays open
        self.limit = limit
        self.result = None
        self._entries = []
        lay = QVBoxLayout(self)
        self.q = QLineEdit(initial or "")
        self.q.setPlaceholderText("Search…")
        self.q.textChanged.connect(self._refresh)
        self.q.returnPressed.connect(self._ok)
        lay.addWidget(self.q)
        self.lst = QListWidget()
        self.lst.itemDoubleClicked.connect(lambda _i: self._ok())
        self.lst.currentRowChanged.connect(self._describe)
        lay.addWidget(self.lst, 1)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setStyleSheet(f"color:{palette['muted']};")
        lay.addWidget(self.info)
        bar = QHBoxLayout()
        use = QPushButton("Copy name" if browse else "Use this")
        use.setObjectName("accent")
        use.clicked.connect(self._ok)
        cancel = QPushButton("Close" if browse else "Cancel")
        cancel.clicked.connect(self.reject)
        bar.addWidget(use)
        bar.addWidget(cancel)
        bar.addStretch(1)
        lay.addLayout(bar)
        self._refresh()
        self.q.setFocus()

    def _refresh(self):
        try:
            self._entries = infohub.browse(self.q.text(), kinds=self.kinds, limit=self.limit,
                                           campaign_context=self.plan)
        except Exception:                              # noqa: BLE001 -- a catalog needing data we lack
            self._entries = []
        self.lst.clear()
        for e in self._entries:
            self.lst.addItem(f"{e.name}    [{e.kind}]")
        where = f" in {', '.join(self.kinds)}" if self.kinds else ""
        capped = self.limit is not None and len(self._entries) >= self.limit
        note = " (capped — type to narrow)" if capped else ""
        self.info.setText(f"{len(self._entries)} match(es){where}{note}")

    def _describe(self, row):
        if 0 <= row < len(self._entries):
            e = self._entries[row]
            self.info.setText(f"{e.name}  [{e.kind}]  —  {e.summary}")

    def _ok(self):
        row = self.lst.currentRow()
        if row < 0 and len(self._entries) == 1:
            row = 0
        if not (0 <= row < len(self._entries)):
            return
        e = self._entries[row]
        if self.browse:                                # Info Hub browse: copy the name, keep browsing
            QApplication.clipboard().setText(e.name)
            self.info.setText(f"Copied “{e.name}” [{e.kind}] to the clipboard.")
            return
        self.result = e.name
        self.accept()


def pick_catalog(parent, catalog, initial, plan, palette):
    """Open :class:`CatalogPicker` for a comma-separated ``catalog`` string; return the chosen name or
    None. The shell passes this (curried with its window/plan/palette) as ``build_form``'s ``pick``."""
    kinds = [k.strip() for k in catalog.split(",")] if catalog else None
    dlg = CatalogPicker(parent, kinds, initial, plan, palette)
    dlg.exec()
    return dlg.result
