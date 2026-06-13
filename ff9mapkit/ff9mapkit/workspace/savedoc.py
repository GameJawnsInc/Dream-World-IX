"""Qt save-editor documents for the Workspace (Phase 5b) -- the cross-cutting STATE layer.

A save isn't tied to a campaign/field; it's the player's story + inventory state. This module hosts the
Qt documents that read/EDIT it, reusing the kit's tk-free save backends verbatim (the same code the
tkinter ``ff9_storystate`` / ``ff9_items`` apps call):

  * :class:`StoryStateDoc` -- ScenarioCounter + story flags (``save.inspect`` / ``flags.render_report`` /
    ``flags.diff_reports`` / ``save.apply_story_edit``). Inspect / Diff / Edit, BACKUP-guarded +
    reserved-region-refused (the edit path shares the CLI's guards). (5b-i)

Editing the encrypted ``SavedData_ww.dat`` needs pycryptodome; inspect/diff also read a Memoria
plaintext extra-save or an exported save JSON. Provenance-clean: only the user's own save, only on Apply.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPlainTextEdit, QPushButton,
    QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from .. import flags as _flags
from .. import save as _save


class StoryStateDoc(QWidget):
    """Inspect / Diff / EDIT a save's gEventGlobal story state (ScenarioCounter + story bits)."""

    def __init__(self, palette):
        super().__init__()
        self.pal = palette
        self.reports = []          # [(label, SaveReport)] for the loaded save (A)
        self.blocks = []           # editable block per report (None unless an encrypted .dat)
        self.path = ""
        self.reports_b = []        # the compare-against save (B)

        v = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.open_btn = QPushButton("Open Save…")
        self.open_btn.clicked.connect(self.browse)
        self.path_lbl = QLabel("No save loaded.")
        self.path_lbl.setStyleSheet(f"color:{palette['muted']};")
        bar.addWidget(self.open_btn)
        bar.addWidget(self.path_lbl, 1)
        v.addLayout(bar)

        split = QSplitter(Qt.Horizontal)
        v.addWidget(split, 1)
        self.slots = QListWidget()
        self.slots.currentRowChanged.connect(lambda _r: self._on_slot())
        split.addWidget(self.slots)

        self.tabs = QTabWidget()
        self.inspect = QPlainTextEdit()
        self.inspect.setReadOnly(True)
        self.tabs.addTab(self.inspect, "Inspect")
        self.tabs.addTab(self._build_diff(), "Diff")
        self.tabs.addTab(self._build_edit(), "Edit")
        split.addWidget(self.tabs)
        split.setSizes([240, 620])

        self.status = QLabel("Open a SavedData_ww.dat (or a Memoria extra-save / save JSON) to inspect or edit.")
        self.status.setStyleSheet(f"color:{palette['muted']};")
        v.addWidget(self.status)

    # ---- view scaffolding ----
    def _build_diff(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        row = QHBoxLayout()
        row.addWidget(QLabel("Compare A against B:"))
        self.b_btn = QPushButton("Open B…")
        self.b_btn.clicked.connect(self.browse_b)
        row.addWidget(self.b_btn)
        row.addWidget(QLabel("B slot:"))
        self.b_slot = QComboBox()
        row.addWidget(self.b_slot)
        cmp_btn = QPushButton("Compare  A → B")
        cmp_btn.clicked.connect(self._compare)
        row.addWidget(cmp_btn)
        row.addStretch(1)
        lay.addLayout(row)
        self.diff_txt = QPlainTextEdit()
        self.diff_txt.setReadOnly(True)
        lay.addWidget(self.diff_txt, 1)
        return page

    def _build_edit(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        self.edit_target = QLabel("(no save selected)")
        self.edit_target.setStyleSheet(f"color:{self.pal['muted']};")
        self.edit_target.setWordWrap(True)
        lay.addWidget(self.edit_target)
        for label, attr, hint in (
                ("Scenario:", "sc_var", 'a value or area name (e.g. "Ice Cavern")'),
                ("Set flags:", "set_var", "comma-separated bit indices (custom band ≥ 8512)"),
                ("Clear flags:", "clear_var", "comma-separated bit indices")):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            le = QLineEdit()
            setattr(self, attr, le)
            row.addWidget(le, 1)
            h = QLabel(hint)
            h.setStyleSheet(f"color:{self.pal['muted']};font-size:11px;")
            row.addWidget(h)
            lay.addLayout(row)
        btns = QHBoxLayout()
        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self._preview)
        self.apply_btn = QPushButton("Apply  (backup + write)")
        self.apply_btn.setObjectName("accent")
        self.apply_btn.clicked.connect(self._apply)
        btns.addWidget(self.preview_btn)
        btns.addWidget(self.apply_btn)
        btns.addStretch(1)
        lay.addLayout(btns)
        self.edit_txt = QPlainTextEdit()
        self.edit_txt.setReadOnly(True)
        lay.addWidget(self.edit_txt, 1)
        return page

    # ---- loading (A) ----
    def browse(self):
        from PySide6.QtWidgets import QFileDialog
        f, _ = QFileDialog.getOpenFileName(self, "Pick a save (SavedData_ww.dat / extra-save / JSON)",
                                           _save.default_save_dir() or "",
                                           "FF9 save (*.dat);;Save JSON / Base64 (*.json *.txt);;All files (*)")
        if f:
            self.load(f)

    def load(self, path, select=0) -> bool:
        try:
            self.reports = _save.inspect(path)
        except Exception as e:                            # noqa: BLE001
            self.reports, self.blocks, self.path = [], [], ""
            self.slots.clear()
            self.inspect.setPlainText(f"Could not read story state from:\n{path}\n\n{e}\n\n"
                                      "(An encrypted SavedData_ww.dat needs pycryptodome.)")
            self.status.setText("no story state decoded")
            return False
        self.path = path
        self.blocks = self._editable_blocks(path, len(self.reports))
        self.path_lbl.setText(str(path))
        self.slots.clear()
        for label, rep in self.reports:
            beat = rep.milestone[1] if rep.milestone else "(pre-story)"
            self.slots.addItem(f"{label}  —  SC {rep.scenario_counter} · {beat}")
        ro = "" if any(b is not None for b in self.blocks) else \
            "  (read-only: editing needs the encrypted SavedData_ww.dat + pycryptodome)"
        self.status.setText(f"{len(self.reports)} populated save(s){ro}")
        self._refresh_b_slots()
        if self.reports:
            self.slots.setCurrentRow(select if 0 <= select < len(self.reports) else 0)
        return True

    @staticmethod
    def _editable_blocks(path, n):
        try:
            pops = _save.FF9Save.load(path).populated()
        except Exception:                                 # noqa: BLE001 -- not an encrypted .dat / no crypto
            return [None] * n
        return [p.block for p in pops] if len(pops) == n else [None] * n

    def _refresh_b_slots(self):
        reps = self.reports_b or self.reports
        self.b_slot.clear()
        for i, (label, rep) in enumerate(reps):
            self.b_slot.addItem(f"{i}: {label} (SC {rep.scenario_counter})", i)

    def _on_slot(self):
        i = self.slots.currentRow()
        if not (0 <= i < len(self.reports)):
            return
        label, rep = self.reports[i]
        self.inspect.setPlainText(f"{label}\n\n" + _flags.render_report(rep))
        blk = self.blocks[i] if i < len(self.blocks) else None
        if blk is None:
            self.edit_target.setText("Editing disabled — load the encrypted SavedData_ww.dat (read-only).")
            self.preview_btn.setEnabled(False)
            self.apply_btn.setEnabled(False)
        else:
            self.edit_target.setText(f"Editing: {label}  (block {blk}).  Reserved-region flags are refused; "
                                     "a .bak is written before any change.")
            self.preview_btn.setEnabled(True)
            self.apply_btn.setEnabled(True)

    # ---- diff (B) ----
    def browse_b(self):
        from PySide6.QtWidgets import QFileDialog
        f, _ = QFileDialog.getOpenFileName(self, "Pick the second save (B)", _save.default_save_dir() or "",
                                           "FF9 save (*.dat);;Save JSON / Base64 (*.json *.txt);;All files (*)")
        if not f:
            return
        try:
            self.reports_b = _save.inspect(f)
        except Exception as e:                            # noqa: BLE001
            self.reports_b = []
            self.diff_txt.setPlainText(f"Could not read save B:\n{f}\n\n{e}")
            return
        self._refresh_b_slots()
        self.status.setText(f"B: {len(self.reports_b)} populated save(s) — pick a B slot, then Compare")

    def _compare(self):
        i = self.slots.currentRow()
        if not (0 <= i < len(self.reports)):
            self.diff_txt.setPlainText("Select a save on the left (A) first.")
            return
        reps_b = self.reports_b or self.reports           # no B file -> compare two slots of A
        j = self.b_slot.currentData()
        j = j if isinstance(j, int) else 0
        if not 0 <= j < len(reps_b):
            self.diff_txt.setPlainText(f"B slot {j} out of range (B has {len(reps_b)}).")
            return
        (la, ra), (lb, rb) = self.reports[i], reps_b[j]
        self.diff_txt.setPlainText(f"A: {la}\nB: {lb}\n\n" + _flags.render_diff(_flags.diff_reports(ra, rb)))

    # ---- edit (write) ----
    def _parse_bits(self, s):
        return [_flags.resolve(t.strip(), {}) for t in (s or "").replace(";", ",").split(",") if t.strip()]

    def _edit_args(self):
        sc = self.sc_var.text().strip()
        return (_flags.resolve_scenario(sc) if sc else None,
                self._parse_bits(self.set_var.text()), self._parse_bits(self.clear_var.text()))

    def _target_block(self):
        i = self.slots.currentRow()
        return self.blocks[i] if (0 <= i < len(self.blocks)) else None

    def _preview(self):
        blk = self._target_block()
        if blk is None:
            return
        try:
            scenario, setb, clrb = self._edit_args()
            res = _save.apply_story_edit(self.path, block=blk, scenario=scenario,
                                         set_flags=setb, clear_flags=clrb, dry_run=True)
        except (ValueError, IndexError) as e:
            self.edit_txt.setPlainText(f"Cannot apply:\n  {e}")
            return
        if not res["notes"]:
            self.edit_txt.setPlainText("Nothing to change — set a Scenario / Set flags / Clear flags.")
            return
        body = "PREVIEW (nothing written yet):\n" + "\n".join(f"  - {n}" for n in res["notes"])
        if res["extra"]:
            body += "\n\n  (a Memoria extra-save is present and will be patched too)"
        self.edit_txt.setPlainText(body)

    def _apply(self):
        blk = self._target_block()
        if blk is None:
            return
        try:
            scenario, setb, clrb = self._edit_args()
            preview = _save.apply_story_edit(self.path, block=blk, scenario=scenario,
                                             set_flags=setb, clear_flags=clrb, dry_run=True)
        except (ValueError, IndexError) as e:
            self.edit_txt.setPlainText(f"Cannot apply:\n  {e}")
            return
        if not preview["notes"]:
            self.edit_txt.setPlainText("Nothing to change.")
            return
        ok = QMessageBox.question(
            self, "Apply story-state edit?",
            "This edits your REAL save (a .bak backup is written first):\n\n"
            + "\n".join(preview["notes"]) + "\n\nProceed?")
        if ok != QMessageBox.StandardButton.Yes:
            return
        try:
            res = _save.apply_story_edit(self.path, block=blk, scenario=scenario,
                                         set_flags=setb, clear_flags=clrb)
        except Exception as e:                            # noqa: BLE001
            self.edit_txt.setPlainText(f"Write failed:\n  {e}")
            return
        msg = ["APPLIED — your save was edited:"] + [f"  - {n}" for n in res["notes"]]
        msg += [f"  backed up -> {os.path.basename(b)}" for b in res["backups"]]
        if res["extra"]:
            msg.append("  [OK] Memoria extra-save patched + verified — this IS the gEventGlobal the game loads."
                       if res.get("extra_patched") else
                       "  [WARN] a Memoria extra-save is present but could NOT be verified-patched.")
        else:
            msg.append("  (no Memoria extra-save for this slot — the main save block governs)")
        msg.append("\nReload the save in-game to see it.")
        self.edit_txt.setPlainText("\n".join(msg))
        self.status.setText("save edited (backup written) — reload it in-game")
        self.load(self.path, select=self.slots.currentRow())   # refresh, KEEPING the edited slot selected
