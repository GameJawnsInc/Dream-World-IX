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
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from .. import dialogue as _dlg
from .. import infohub
from ..content.text import DEFAULT_WRAP_WIDTH
from ..editor import forms

# Fields whose value is a line shown in an FF9 text window -> they get a live wrap-preview (FF9 never
# auto-wraps, so the kit pre-breaks long lines; this shows exactly where). Keys match editor.forms specs.
DIALOGUE_KEYS = {"dialogue", "message", "prompt", "reply"}


def _wrap_preview_panel(line_edit, get_text, palette, wrap_width):
    """A read-only pane under a dialogue field: how the line breaks on the FF9 screen, live as you type.
    Reuses the exact build-time wrapper (:func:`..dialogue.wrap_preview`). ``wrap_width`` None = the field
    set ``[dialogue] wrap = false`` (author wraps by hand) -> show the text raw, no preview break."""
    panel = QWidget()
    pv = QVBoxLayout(panel)
    pv.setContentsMargins(0, 3, 0, 0)
    pv.setSpacing(2)
    cap = QLabel("On-screen preview — how it wraps in the FF9 window:")
    cap.setStyleSheet(f"color:{palette['muted']};font-size:11px;")
    pv.addWidget(cap)
    box = QPlainTextEdit()
    box.setReadOnly(True)
    box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)     # show the kit's OWN break points, not Qt's
    box.setFixedHeight(74)
    pv.addWidget(box)
    # The note is ALWAYS in the layout at a fixed height (it carries the warning OR a quiet "fits" line):
    # toggling visibility would change the panel height and, inside the nested form/scroll, clip the
    # fixed-height box on the way back. A constant-height panel can't reflow.
    note = QLabel("")
    note.setFixedHeight(16)
    pv.addWidget(note)

    def refresh(*_):
        txt = get_text() or ""
        box.setPlainText((_dlg.wrap_preview(txt, wrap_width) if wrap_width is not None else txt) or "(empty)")
        over = _dlg.overflow(txt, wrap_width) if (txt and wrap_width is not None) else []
        if over:
            note.setText(f"⚠ {len(over)} line(s) may overflow the window — verify in-game.")
            note.setStyleSheet(f"color:{palette['warn']};font-size:11px;")
        elif txt:
            note.setText("✓ fits the window")
            note.setStyleSheet(f"color:{palette['muted']};font-size:11px;")
        else:
            note.setText("")

    line_edit.textChanged.connect(refresh)
    refresh()
    return panel


def build_form(spec, values: dict, palette: dict, pick=None, wrap_width=DEFAULT_WRAP_WIDTH):
    """Return ``(widget, getters)`` for ``spec`` + flat ``values`` (from ``forms.entity_to_values``).

    ``getters`` maps each field key to a 0-arg callable returning the widget's current value. ``pick``
    (optional) is ``pick(catalog: str, current: str) -> str | None``; when given, catalog-backed fields
    get a "Browse…" button that calls it and writes the chosen name back into the widget. Dialogue-bearing
    fields (:data:`DIALOGUE_KEYS`) get a live FF9-window wrap preview at ``wrap_width`` (None = wrapping off
    for this field -> show the line raw)."""
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
        elif f.key in DIALOGUE_KEYS:
            # MULTI-LINE: dialogue carries explicit line breaks (Enter = a real \n, which is FF9's native
            # in-window line break; type [PAGE] for a new window). QLineEdit collapses newlines -> use a
            # plain text box. toPlainText returns real \n, preserved through build_entity/TOML/.mes.
            te = QPlainTextEdit(str(values.get(f.key, "") or ""))
            te.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
            te.setTabChangesFocus(True)            # Tab -> next field (Enter is the line break, not Tab)
            te.setFixedHeight(72)                   # ~4 lines, like the old Dialogue Editor
            te.setToolTip("Enter = a line break in the same window. Type [PAGE] for a new window.")
            widget, getters[f.key], setter = te, te.toPlainText, te.setPlainText
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
        if f.key in DIALOGUE_KEYS and hasattr(widget, "textChanged"):
            v.addWidget(_wrap_preview_panel(widget, getters[f.key], palette, wrap_width))
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
