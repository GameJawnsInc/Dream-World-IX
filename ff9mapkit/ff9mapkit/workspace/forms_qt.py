"""A generic Qt form renderer for :mod:`..editor.forms` specs (Phase 4 of the GUI makeover).

Builds a Qt form (a labelled widget per :class:`..editor.forms.Field`) + a dict of value getters from a
spec + flat values. Saving goes through ``forms.build_entity`` -- the SAME tk-free parser the tkinter
editor uses -- so a field edited in the Qt shell round-trips byte-identically to one edited in the old
editor. The renderer is thin; all parsing/validation stays in ``editor.forms`` (unit-tested headless).

Mapping: BOOL -> QCheckBox, PRESET -> an editable QComboBox seeded with the archetype names (a custom
string is still accepted), everything else -> a QLineEdit. Each field's ``help`` becomes a muted hint.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ..editor import forms


def build_form(spec, values: dict, palette: dict):
    """Return ``(widget, getters)`` for ``spec`` + flat ``values`` (from ``forms.entity_to_values``).

    ``getters`` maps each field key to a 0-arg callable returning the widget's current value (a ``str``
    for text/preset, a ``bool`` for checkboxes) -- exactly what ``forms.build_entity`` consumes."""
    w = QWidget()
    lay = QFormLayout(w)
    lay.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)
    lay.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    lay.setHorizontalSpacing(14)
    lay.setVerticalSpacing(10)
    getters = {}
    for f in spec:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        if f.kind == forms.BOOL:
            cb = QCheckBox()
            cb.setChecked(bool(values.get(f.key, f.default)))
            v.addWidget(cb)
            getters[f.key] = cb.isChecked
        elif f.kind == forms.PRESET:
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItems(list(forms.PRESETS))
            combo.setCurrentText(str(values.get(f.key, "") or ""))
            v.addWidget(combo)
            getters[f.key] = combo.currentText
        else:
            le = QLineEdit(str(values.get(f.key, "") or ""))
            if f.catalog:
                le.setPlaceholderText(f"a {f.catalog.split(',')[0]} name or id")
            v.addWidget(le)
            getters[f.key] = le.text
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
