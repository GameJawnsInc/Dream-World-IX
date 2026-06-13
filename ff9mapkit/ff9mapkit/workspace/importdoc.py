"""The FFIX Import document for the Workspace (Phase 6b) -- the tkinter ff9_import, folded in.

Bring content in from the real FF9 install: fork a field (the fidelity options as plain checkboxes, not
CLI flags), preview fork fidelity, or read a field's dialogue / inspect a save / list fields. Every action
shells out to ``py -m ff9mapkit <cmd>`` and STREAMS into the shell's Output panel via ``run`` (the shell's
run_job). Only this view is Qt -- the argv is :func:`..editor.jobs.import_args`, the streaming + verdict
are the shell's, and the commands are the same CLI the terminal loop uses.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QRadioButton, QVBoxLayout, QWidget,
)


class ImportDoc(QWidget):
    """Fork-from-game + read/inspect, as a Workspace document. ``run`` = ``shell.run_job`` (streams a CLI
    job to the Output panel + posts a verdict); ``problems`` = ``shell._show_problems`` (unused here -- the
    shell-outs have only a stream + a return code, so the verdict comes from run_job)."""

    def __init__(self, pal, kit_root, *, run, problems=None):
        super().__init__()
        self.pal = pal
        self.kit = Path(kit_root)                      # `-m ff9mapkit` cwd (this worktree's package)
        self._run = run
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)
        intro = QLabel("Bring content in from your real FF9 install (needs UnityPy). Fork a real field, "
                       "preview how faithfully it will fork, or read its dialogue / inspect a save.")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color:{pal['muted']};")
        root.addWidget(intro)
        root.addWidget(self._fork_box())
        root.addWidget(self._read_box())
        root.addStretch(1)
        self._buttons = [self.find_btn, self.preview_btn, self.import_btn, self.dlg_btn, self.save_btn,
                         self.list_btn, self.tpl_btn]

    # ------------------------------------------------------------------ fork-a-field
    def _fork_box(self):
        box = QGroupBox("Fork a real field")
        v = QVBoxLayout(box)
        lbl = QLabel("Real field — an id, or an FBG-name substring (e.g. 100, grgr, alxt_map016). "
                     "Find… looks up exact names/ids; Preview shows what a fork will/won't reproduce.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{self.pal['muted']};")
        v.addWidget(lbl)
        row = QHBoxLayout()
        self.field = QLineEdit()
        self.field.setPlaceholderText("field id or name")
        self.find_btn = QPushButton("Find…")
        self.find_btn.clicked.connect(self.on_find)
        self.preview_btn = QPushButton("Preview fidelity")
        self.preview_btn.clicked.connect(self.on_preview)
        row.addWidget(self.field, 1)
        row.addWidget(self.find_btn)
        row.addWidget(self.preview_btn)
        v.addLayout(row)

        art = QGroupBox("Background art")
        av = QVBoxLayout(art)
        self.art_native = QRadioButton("Native — seamless, faithful occlusion + lighting; ANY field (recommended)")
        self.art_borrow = QRadioButton("BG-borrow — reuse the real art via DictionaryPatch (fast; area ≥ 10)")
        self.art_editable = QRadioButton("Editable scene — repaintable per-depth layers (needs an in-game export)")
        self.art_native.setChecked(True)
        for r in (self.art_native, self.art_borrow, self.art_editable):
            av.addWidget(r)
        v.addWidget(art)

        carry = QGroupBox("Carry from the real field")
        cv = QVBoxLayout(carry)
        self.carry_npcs = QCheckBox("NPCs & props faithfully (their push/talk interactions fire)")
        self.carry_text = QCheckBox("Real dialogue, verbatim (per language) — carried NPCs speak the real words")
        self.dialogue_stubs = QCheckBox("Dialogue as editable [[npc]] stubs (to RE-AUTHOR, not carry)")
        self.save_moogle = QCheckBox("Save point — the hidden Moogle + the save flourish (if the field has one)")
        self.carry_npcs.setChecked(True)
        self.carry_text.setChecked(True)
        for c in (self.carry_npcs, self.carry_text, self.dialogue_stubs, self.save_moogle):
            cv.addWidget(c)
        v.addWidget(carry)

        out = QHBoxLayout()
        out.addWidget(QLabel("Write to:"))
        self.out = QLineEdit(str(self.kit.parent / "imported"))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.browse_out)
        out.addWidget(self.out, 1)
        out.addWidget(browse)
        v.addLayout(out)
        ids = QHBoxLayout()
        ids.addWidget(QLabel("Field id:"))
        self.fid = QLineEdit("4003")
        self.fid.setFixedWidth(80)
        ids.addWidget(self.fid)
        ids.addWidget(QLabel("Name (optional):"))
        self.name = QLineEdit()
        self.name.setFixedWidth(160)
        ids.addWidget(self.name)
        ids.addStretch(1)
        self.import_btn = QPushButton("Import field")
        self.import_btn.clicked.connect(self.on_import)
        ids.addWidget(self.import_btn)
        v.addLayout(ids)
        hint = QLabel("→ then deploy what you made on the Build & Deploy tab.")
        hint.setStyleSheet(f"color:{self.pal['muted']};")
        v.addWidget(hint)
        return box

    def _art(self):
        return "borrow" if self.art_borrow.isChecked() else "editable" if self.art_editable.isChecked() else "native"

    # ------------------------------------------------------------------ read & inspect
    def _read_box(self):
        box = QGroupBox("Read & inspect  (read-only / maintenance)")
        v = QVBoxLayout(box)
        dlg = QHBoxLayout()
        dlg.addWidget(QLabel("Dialogue of field:"))
        self.dlg_field = QLineEdit()
        self.dlg_field.setFixedWidth(150)
        dlg.addWidget(self.dlg_field)
        dlg.addWidget(QLabel("Lang:"))
        self.dlg_lang = QComboBox()
        self.dlg_lang.addItems(["us", "uk", "fr", "gr", "it", "es", "jp"])
        dlg.addWidget(self.dlg_lang)
        self.dlg_btn = QPushButton("View dialogue")
        self.dlg_btn.clicked.connect(self.on_view_dialogue)
        dlg.addWidget(self.dlg_btn)
        dlg.addStretch(1)
        v.addLayout(dlg)

        sav = QHBoxLayout()
        sav.addWidget(QLabel("Inspect save:"))
        self.save_path = QLineEdit()
        browse_s = QPushButton("Browse…")
        browse_s.clicked.connect(self.browse_save)
        self.save_btn = QPushButton("Inspect")
        self.save_btn.clicked.connect(self.on_inspect_save)
        sav.addWidget(self.save_path, 1)
        sav.addWidget(browse_s)
        sav.addWidget(self.save_btn)
        v.addLayout(sav)

        lst = QHBoxLayout()
        lst.addWidget(QLabel("List fields, filter:"))
        self.list_filter = QLineEdit()
        self.list_filter.setFixedWidth(150)
        self.list_btn = QPushButton("List fields")
        self.list_btn.clicked.connect(self.on_list_fields)
        lst.addWidget(self.list_filter)
        lst.addWidget(self.list_btn)
        lst.addStretch(1)
        v.addLayout(lst)

        tpl = QHBoxLayout()
        self.tpl_btn = QPushButton("Regenerate base templates")
        self.tpl_btn.clicked.connect(self.on_templates)
        tplhint = QLabel("rebuild the kit's base assets from YOUR install (ships no game data)")
        tplhint.setStyleSheet(f"color:{self.pal['muted']};")
        tpl.addWidget(self.tpl_btn)
        tpl.addWidget(tplhint, 1)
        v.addLayout(tpl)
        return box

    # ------------------------------------------------------------------ run helpers
    def _confirm(self, title, text):
        return QMessageBox.question(self, title, text) == QMessageBox.StandardButton.Yes

    def _warn(self, title, text):
        QMessageBox.warning(self, title, text)

    def _busy(self, b):
        for btn in self._buttons:
            btn.setEnabled(not b)

    def _kit(self, args, *, subject, ok_next=""):
        """Stream ``py -m ff9mapkit <args>`` from the kit root into the Output panel via run_job."""
        self._busy(True)
        started = self._run([sys.executable, "-m", "ff9mapkit", *args], cwd=self.kit, subject=subject,
                            ok_headline=f"{subject} — done", ok_next=ok_next,
                            fail_hint="See the Output tab (importing needs UnityPy + your FF9 install).",
                            on_finished=lambda _code: self._busy(False))
        if not started:
            self._busy(False)                          # a job was already running; nothing started

    # ------------------------------------------------------------------ actions
    def browse_out(self):
        d = QFileDialog.getExistingDirectory(self, "Folder to write the imported field into")
        if d:
            self.out.setText(d)

    def browse_save(self):
        f, _ = QFileDialog.getOpenFileName(self, "A save file (SavedData_ww.dat / extra-save / JSON)")
        if f:
            self.save_path.setText(f)

    def on_find(self):
        flt = self.field.text().strip()
        self._kit(["list-fields", flt] if flt else ["list-fields"], subject="Find fields")

    def on_preview(self):
        field = self.field.text().strip()
        if not field:
            return self._warn("No field", "Enter a real field id or name to preview its fork fidelity.")
        self._kit(["fork-report", field], subject="Fork preview",
                  ok_next="Read the fidelity report, then set the carry options and Import.")

    def on_import(self):
        from ..editor import jobs
        field = self.field.text().strip()
        if not field:
            return self._warn("No field", "Enter a real field id or name (use Find… to look it up).")
        out = self.out.text().strip()
        if not out:
            return self._warn("No output folder", "Pick a folder to write the imported field into.")
        try:
            fid = int(self.fid.text().strip())
        except ValueError:
            return self._warn("Bad field id", "Field id must be a number (e.g. 4003).")
        Path(out).mkdir(parents=True, exist_ok=True)
        args = jobs.import_args(field, out=str(Path(out).resolve()), field_id=fid,
                                name=self.name.text().strip() or None, art=self._art(),
                                carry_npcs=self.carry_npcs.isChecked(), carry_text=self.carry_text.isChecked(),
                                dialogue_stubs=self.dialogue_stubs.isChecked(),
                                save_moogle=self.save_moogle.isChecked())
        self._kit(args, subject=f"Import {field}",
                  ok_next=f"Written to {out}. Open it on the Build & Deploy tab to compile + deploy.")

    def on_view_dialogue(self):
        field = self.dlg_field.text().strip()
        if not field:
            return self._warn("No field", "Enter a real field id or name to read its dialogue.")
        self._kit(["dialogue-import", field, "--lang", self.dlg_lang.currentText()], subject="Read dialogue")

    def on_inspect_save(self):
        save = self.save_path.text().strip()
        if not save:
            return self._warn("No save", "Pick a save file to inspect.")
        self._kit(["flags-inspect", save], subject="Inspect save")

    def on_list_fields(self):
        flt = self.list_filter.text().strip()
        self._kit(["list-fields", flt] if flt else ["list-fields"], subject="List fields")

    def on_templates(self):
        if not self._confirm("Regenerate templates",
                             "Rebuild the kit's base templates from your FF9 install? "
                             "(Reads your install; writes only into the kit's data dir.)"):
            return
        self._kit(["extract-templates"], subject="Regenerate templates",
                  ok_next="Templates rebuilt from your install (ships no game data).")
