"""SAVE AS PREFAB from the World tab (overworld editor rung P6, studies/overworld-editor/PREFABS.md).

The Edit-the-map menu's last entry. A dialog lists the draft's applied steps (the recipe), each a checkbox: the ones
a prefab can hold (a base island or carried coast, then the forest, mountain and hill steps on it) are offered, the
rest greyed. The default ticks the LAST base step and the relief steps after it. A name and an optional note, then
``world-prefab NAME --save --from <draft> --steps ...`` runs as a job (THE CLI STAYS THE ORACLE: it composes the
steps with the prefab frame outside the install, fingerprints them at a clean site, proves them at a second, measures
the turns and appends the entry to your own catalog). The draft is only read. On success the Add-a-prefab card's
picker re-reads the catalog, and the new prefab is there, marked new until you walk it.
"""
from __future__ import annotations

import re
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QLineEdit, QListWidget,
                               QListWidgetItem, QVBoxLayout)

from . import widgets

BASES = ("island", "transplant")
RELIEF = ("mountain", "forest", "hill")
#: How long a save takes, measured on a real composition (stage x3 + three turned stagings): the dialog says so.
SAVE_TIME = "about a minute or two"


def offered(row) -> bool:
    return (row or {}).get("table") in BASES + RELIEF


def default_selection(steps) -> list:
    """The 0-based steps ticked by default: the last base step and the relief steps after it (to the next base)."""
    bases = [i for i, s in enumerate(steps) if s["row"].get("table") in BASES]
    if not bases:
        return []
    b = bases[-1]
    return [b] + [i for i in range(b + 1, len(steps)) if steps[i]["row"].get("table") in RELIEF]


def why_not(steps, picked) -> str:
    """'' when ``picked`` (0-based, in order) is a composition a prefab can hold, else why not (in the user's words)."""
    if not picked:
        return "Tick the steps the prefab holds: an island or a carried coast, then the relief on it."
    rows = [steps[i]["row"] for i in sorted(picked)]
    if rows[0].get("table") not in BASES:
        return "The first ticked step must be the island or carried coast the relief stands on."
    if sum(1 for r in rows if r.get("table") in BASES) != 1:
        return "A prefab holds one island or carried coast."
    if any(r.get("table") not in RELIEF for r in rows[1:]):
        return "After the base, only forest, mountain and hill steps can ride along."
    return ""


def suggest_name(steps, picked, taken) -> str:
    """A free default name from the base's ground: ``desert-isle``, ``desert-isle-2`` ..."""
    base = steps[sorted(picked)[0]]["row"] if picked else {}
    stem = (str(base.get("ground") or "grass") + ("-isle" if base.get("table") == "island" else "-coast")).lower()
    stem = re.sub(r"[^a-z0-9-]", "-", stem)
    name, n = stem, 2
    while name in taken:
        name, n = f"{stem}-{n}", n + 1
    return name


def save_argv(game, draft, name, picked, *, note="", turns=True, report=None) -> list:
    """The ``world-prefab --save`` job (1-based ``--steps``)."""
    argv = [sys.executable, "-m", "ff9mapkit", "--game", str(game), "world-prefab", str(name), "--save",
            "--from", str(draft), "--steps", ",".join(str(i + 1) for i in sorted(picked))]
    if note:
        argv.append("--note=" + " ".join(str(note).split()))      # (=: a note may start with '-')
    if not turns:
        argv.append("--no-turns")
    if report is not None:
        argv += ["--report-json", str(report)]
    return argv


class SavePrefabDialog(QDialog):
    """The steps to save, the name, a note, and whether to measure the turns. :meth:`result_value` after exec."""

    def __init__(self, steps, *, taken=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save as prefab")
        self._steps, self._taken = list(steps), set(taken)
        v = QVBoxLayout(self)
        intro = widgets.role_label("Freeze these steps as a prefab you can place anywhere it is lawful. It is built "
                                   "outside the install, held to itself at two sites and its turns measured: "
                                   f"{SAVE_TIME}. The draft is not changed.", "caption")
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.list = QListWidget()
        self.list.setAccessibleName("Steps")
        pick = set(default_selection(self._steps))
        for i, s in enumerate(self._steps):
            it = QListWidgetItem(f"{i + 1}. {s.get('label') or s['row'].get('table')}"
                                 + ("" if offered(s["row"]) else " (not part of a prefab)"))
            if offered(s["row"]):
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Checked if i in pick else Qt.CheckState.Unchecked)
            else:
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                it.setToolTip("A prefab holds an island or carried coast and the forest, mountain and hill on it.")
            self.list.addItem(it)
        self.list.itemChanged.connect(lambda _it: self._sync())
        v.addWidget(self.list, 1)
        v.addWidget(widgets.role_label("Name", "caption"))
        self.name_edit = QLineEdit(suggest_name(self._steps, sorted(pick), self._taken))
        self.name_edit.setAccessibleName("Prefab name")
        self.name_edit.setToolTip("Lower-case letters, digits and hyphens: the name the catalog and recipes use.")
        self.name_edit.textChanged.connect(lambda _t: self._sync())
        v.addWidget(self.name_edit)
        v.addWidget(widgets.role_label("Note (optional)", "caption"))
        self.note_edit = QLineEdit()
        self.note_edit.setAccessibleName("Note")
        v.addWidget(self.note_edit)
        self.turns_box = QCheckBox("Measure the quarter turns too")
        self.turns_box.setChecked(True)
        self.turns_box.setToolTip("Place each turn at a clean site and hold it to the land turned; the turns that pass "
                                  "are offered in the Add a prefab card.")
        v.addWidget(self.turns_box)
        self.why_lbl = widgets.role_label("", "caption")
        self.why_lbl.setWordWrap(True)
        self.why_lbl.setProperty("state", "warn")
        v.addWidget(self.why_lbl)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        v.addWidget(self.buttons)
        widgets.fit_dialog(self, ch=64, list_rows=min(10, max(4, len(self._steps))), lines=8)
        self._sync()

    def picked(self) -> list:
        return [i for i in range(self.list.count())
                if self.list.item(i).flags() & Qt.ItemFlag.ItemIsUserCheckable
                and self.list.item(i).checkState() == Qt.CheckState.Checked]

    def problem(self) -> str:
        why = why_not(self._steps, self.picked())
        name = self.name_edit.text().strip()
        if not why and not re.match(r"^[a-z0-9][a-z0-9-]{1,47}$", name):
            why = "The name is lower-case letters, digits and hyphens, 2 to 48 of them."
        if not why and name in self._taken:
            why = f"A prefab named {name} is in the catalog already."
        return why

    def _sync(self):
        why = self.problem()
        self.why_lbl.setText(why)
        self.why_lbl.setVisible(bool(why))
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(not why)

    def result_value(self):
        """``{"name", "picked" (0-based), "note", "turns"}``."""
        return {"name": self.name_edit.text().strip(), "picked": self.picked(), "note": self.note_edit.text().strip(),
                "turns": self.turns_box.isChecked()}


def ask_save(parent, steps, taken):
    """The dialog, modal; its :meth:`SavePrefabDialog.result_value` or None (cancelled)."""
    dlg = SavePrefabDialog(steps, taken=taken, parent=parent)
    return dlg.result_value() if dlg.exec() == QDialog.DialogCode.Accepted else None
