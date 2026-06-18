"""The FFIX Import document for the Workspace (Phase 6b) -- the tkinter ff9_import, folded in.

Bring content in from the real FF9 install: fork a field (Verbatim = the truest fork, the default — ships the
real script + dialogue, runs the real logic; or Re-authorable, the fidelity options as plain checkboxes),
preview fork fidelity, or read a field's dialogue / inspect a save / list fields. Every action
shells out to ``py -m ff9mapkit <cmd>`` and STREAMS into the shell's Output panel via ``run`` (the shell's
run_job). Only this view is Qt -- the argv is :func:`..editor.jobs.import_args`, the streaming + verdict
are the shell's, and the commands are the same CLI the terminal loop uses.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QRadioButton, QVBoxLayout, QWidget,
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
        intro = QLabel("Bring content in from your real FF9 install (needs UnityPy). Fork a single real field, "
                       "fork a whole connected REGION as one campaign, preview how faithfully it forks, or read "
                       "its dialogue / inspect a save.")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color:{pal['muted']};")
        root.addWidget(intro)
        root.addWidget(self._fork_box())
        root.addWidget(self._region_box())
        root.addWidget(self._read_box())
        root.addStretch(1)
        self._buttons = [self.find_btn, self.preview_btn, self.import_btn, self.dryrun_btn,
                         self.fork_region_btn, self.catalog_btn, self.dlg_btn, self.save_btn,
                         self.list_btn, self.tpl_btn]

    # ------------------------------------------------------------------ fork-a-field
    def _fork_box(self):
        box = QGroupBox("Fork a real field")
        v = QVBoxLayout(box)
        lbl = QLabel("ONE screen — an id, or an FBG-name substring (e.g. 100, grgr, alxt_map016). For a whole "
                     "connected AREA (many screens wired together), use Fork a region below. "
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

        mode = QGroupBox("Fork mode")
        mv = QVBoxLayout(mode)
        self.mode_verbatim = QRadioButton("Verbatim — the truest fork (recommended)")
        self.mode_authorable = QRadioButton("Re-authorable — editable [[npc]]/content, but you rebuild the "
                                            "field's logic & story gating yourself (advanced)")
        self.mode_verbatim.setChecked(True)
        mv.addWidget(self.mode_verbatim)
        mv.addWidget(self.mode_authorable)
        mhint = QLabel("Verbatim ships the field's real event script + dialogue WHOLE — it runs the original "
                       "logic, story gating, real doors and rotating cast (the proven faithful path), carrying "
                       "every NPC/prop/line itself. A verbatim fork boots at scenario zero — use Preview fidelity "
                       "for the suggested starting beat, then add a [startup] block in the editor. The scene + "
                       "carry options appear only in Re-authorable mode (which drops the real logic for editable "
                       "[[npc]]/content you re-author).")
        mhint.setWordWrap(True)
        mhint.setStyleSheet(f"color:{self.pal['muted']};")
        mv.addWidget(mhint)
        self.mode_verbatim.toggled.connect(self._sync_mode)
        v.addWidget(mode)

        self.art_box = QGroupBox("Background art")
        av = QVBoxLayout(self.art_box)
        self.art_native = QRadioButton("Native — seamless, faithful occlusion + lighting; ANY field (recommended)")
        self.art_borrow = QRadioButton("BG-borrow — reuse the real art via DictionaryPatch (fast; area ≥ 10)")
        self.art_editable = QRadioButton("Editable scene — repaintable per-depth layers (needs an in-game export)")
        self.art_native.setChecked(True)
        for r in (self.art_native, self.art_borrow, self.art_editable):
            av.addWidget(r)
        v.addWidget(self.art_box)

        self.carry_box = QGroupBox("Carry from the real field")
        cv = QVBoxLayout(self.carry_box)
        self.carry_npcs = QCheckBox("NPCs & props faithfully (their push/talk interactions fire)")
        self.carry_text = QCheckBox("Real dialogue, verbatim (per language) — carried NPCs speak the real words")
        self.dialogue_stubs = QCheckBox("Dialogue as editable [[npc]] stubs (to RE-AUTHOR, not carry)")
        self.save_moogle = QCheckBox("Save point — the hidden Moogle + the save flourish (if the field has one)")
        self.carry_npcs.setChecked(True)
        self.carry_text.setChecked(True)
        for c in (self.carry_npcs, self.carry_text, self.dialogue_stubs, self.save_moogle):
            cv.addWidget(c)
        v.addWidget(self.carry_box)
        self._sync_mode()       # verbatim is default -> dim the art/carry boxes (verbatim carries them itself)

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

    def _sync_mode(self, *_):
        """Verbatim carries every NPC/prop/line + implies --native, so the art + carry boxes are IRRELEVANT --
        HIDE them (a greyed box reads as 'blocked', a hidden one as 'not part of this choice') + pin art to
        Native so a later switch back to Re-authorable starts from the recommended scene mode."""
        verbatim = self.mode_verbatim.isChecked()
        self.art_box.setVisible(not verbatim)
        self.carry_box.setVisible(not verbatim)
        if verbatim:
            self.art_native.setChecked(True)

    # ------------------------------------------------------------------ fork-a-region (import-chain)
    def _region_box(self):
        muted = f"color:{self.pal['muted']};"
        box = QGroupBox("Fork a region  (a connected multi-field chain → one campaign)")
        v = QVBoxLayout(box)
        lbl = QLabel("Fork a whole connected AREA at once — the workflow behind the disc-1 opening. Enter one "
                     "or more seed fields (or click Browse FF9 regions… for a catalog of FF9's areas — pick one, "
                     "or several to compose into one campaign); the chain forks everything they reach into a "
                     "single campaign, doors rewired in-fork. Dry-run first to see the blast radius.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(muted)
        v.addWidget(lbl)
        row = QHBoxLayout()
        row.addWidget(QLabel("Seeds:"))
        self.seeds = QLineEdit()
        self.seeds.setPlaceholderText("field ids/names, comma-separated — e.g. 300  or  50,100,64")
        self.catalog_btn = QPushButton("Browse FF9 regions…")
        self.catalog_btn.clicked.connect(self.open_region_catalog)
        row.addWidget(self.seeds, 1)
        row.addWidget(self.catalog_btn)
        v.addLayout(row)
        self.rg_whole = QCheckBox("Whole zone — fork every field in each seed's zone, not just door-reachable "
                                  "(catches cutscene-only screens; more fields/ids — Dry-run to preview)")
        self.rg_verbatim = QCheckBox("Verbatim — each member ships its real script + dialogue, runs the real "
                                     "logic (recommended; uncheck to fork re-authorable members you rebuild yourself)")
        self.rg_whole.setChecked(True)
        self.rg_verbatim.setChecked(True)
        v.addWidget(self.rg_whole)
        v.addWidget(self.rg_verbatim)
        out = QHBoxLayout()
        out.addWidget(QLabel("Write campaign to:"))
        self.rg_out = QLineEdit(str(self.kit.parent / "campaign"))
        rbrowse = QPushButton("Browse…")
        rbrowse.clicked.connect(self.browse_region_out)
        out.addWidget(self.rg_out, 1)
        out.addWidget(rbrowse)
        v.addLayout(out)
        ids = QHBoxLayout()
        ids.addWidget(QLabel("id base:"))
        self.rg_idbase = QLineEdit()
        self.rg_idbase.setFixedWidth(70)
        self.rg_idbase.setPlaceholderText("6000")     # blank -> the CLI/.ff9deploy.toml default applies
        ids.addWidget(self.rg_idbase)
        ids.addWidget(QLabel("Name prefix:"))
        self.rg_prefix = QLineEdit()
        self.rg_prefix.setFixedWidth(110)
        self.rg_prefix.setPlaceholderText("e.g. dali_  (stacking)")
        ids.addWidget(self.rg_prefix)
        self.rg_fresh = QCheckBox("Re-allocate ids (--fresh-ids)")
        ids.addWidget(self.rg_fresh)
        ids.addStretch(1)
        v.addLayout(ids)
        collide_hint = QLabel("Field ids are GLOBAL across every stacked mod folder — to keep TWO regions side by "
                              "side, give each a DISTINCT id base AND a unique Name prefix, or the second black-"
                              "screens. The shipped disc-1 opening occupies ~6000–6371.")
        collide_hint.setWordWrap(True)
        collide_hint.setStyleSheet(muted)
        v.addWidget(collide_hint)
        fresh_hint = QLabel("Re-forking into the SAME folder reuses the prior fork's ids by default, so in-fork "
                            "saves survive. Tick --fresh-ids only to re-number from scratch.")
        fresh_hint.setWordWrap(True)
        fresh_hint.setStyleSheet(muted)
        v.addWidget(fresh_hint)
        btns = QHBoxLayout()
        self.dryrun_btn = QPushButton("Dry-run (preview blast radius)")
        self.dryrun_btn.clicked.connect(self.on_region_dryrun)
        self.fork_region_btn = QPushButton("Fork region")
        self.fork_region_btn.setObjectName("accent")
        self.fork_region_btn.clicked.connect(self.on_fork_region)
        btns.addWidget(self.dryrun_btn)
        btns.addStretch(1)
        btns.addWidget(self.fork_region_btn)
        v.addLayout(btns)
        hint = QLabel("→ then open the campaign on the Build & Deploy tab to compile + deploy the whole chain.")
        hint.setStyleSheet(muted)
        v.addWidget(hint)
        return box

    def _region_args(self, *, out):
        from ..editor import jobs
        idb = self.rg_idbase.text().strip()
        return jobs.import_chain_args(
            self.seeds.text().strip(), out=out,
            whole_zone=self.rg_whole.isChecked(), verbatim=self.rg_verbatim.isChecked(),
            id_base=int(idb) if idb.isdigit() else None,
            name_prefix=self.rg_prefix.text().strip() or None, fresh_ids=self.rg_fresh.isChecked())

    # ------------------------------------------------------------------ FF9 region catalog
    def _apply_region_selection(self, arcset, keys):
        """Compose the chosen catalog regions (``refarc.compose_region_fork``) into the Fork-a-region box:
        seeds (one region, or several composed into one campaign) + a suggested name prefix. Returns the seeds
        string. Dialog-free so it's headlessly testable."""
        from .. import refarc as RA
        seeds, prefix, _n = RA.compose_region_fork(arcset, keys)
        self.seeds.setText(seeds)
        self.rg_prefix.setText(prefix)      # ALWAYS (a composed multi-region pick clears a stale single-region tag)
        self.seeds.setFocus()
        return seeds

    def open_region_catalog(self):
        """A pickable catalog of FF9's forkable regions (refarc's ``reference_arcs.toml``). Check ONE region to
        fork it alone, or SEVERAL to compose their seeds into ONE campaign; 'Use selected' fills the Fork-a-
        region box. Replaces the old New-Journey 'FF9 reference arc' (which scaffolded an incomplete multi-
        campaign disc-1 journey) with a region-fork scaffold."""
        from .. import refarc as RA
        try:
            arcset = RA.load_reference_arcs()
        except Exception as e:                          # noqa: BLE001
            return self._warn("Region catalog", f"Couldn't load the FF9 region catalog: {e}")
        dlg = QDialog(self)
        dlg.setWindowTitle("Fork FF9 regions")
        lay = QVBoxLayout(dlg)
        intro = QLabel(f"<b>{arcset.title}</b> — pick FF9 regions to fork. Check ONE to fork it alone, or "
                       "SEVERAL to compose their seeds into ONE campaign. 'Use selected' fills the Fork-a-region "
                       "box (review id base / name prefix, then Dry-run or Fork).")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color:{self.pal['muted']};")
        lay.addWidget(intro)
        lst = QListWidget()
        for a in arcset.arcs:
            it = QListWidgetItem(f"{a.name}   (seed {a.seed})")
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            it.setData(Qt.ItemDataRole.UserRole, a.key)
            if a.note:
                it.setToolTip(a.note)
            lst.addItem(it)
        lay.addWidget(lst)
        foot = QLabel("Forking uses each region's seed + whole-zone. A region's curated zone / starting beat is "
                      "NOT applied here — add a [startup] beat in the editor after forking (or use the CLI "
                      "reference-arcs for a custom --zones).")
        foot.setWordWrap(True)
        foot.setStyleSheet(f"color:{self.pal['muted']};")
        lay.addWidget(foot)
        bb = QDialogButtonBox()
        bb.addButton("Use selected", QDialogButtonBox.ButtonRole.AcceptRole)
        bb.addButton(QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        keys = [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())
                if lst.item(i).checkState() == Qt.CheckState.Checked]
        if not keys:
            return self._warn("No region", "Check at least one region to fork (or Cancel).")
        self._apply_region_selection(arcset, keys)

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

    def browse_region_out(self):
        d = QFileDialog.getExistingDirectory(self, "Folder to write the campaign into")
        if d:
            self.rg_out.setText(d)

    def on_region_dryrun(self):
        if not self.seeds.text().strip():
            return self._warn("No seeds", "Enter one or more seed field ids/names to preview the region fork.")
        self._kit(self._region_args(out=None), subject="Region dry-run",
                  ok_next="Review the BLAST RADIUS + any under-forked zones, then Fork region.")

    def on_fork_region(self):
        seeds = self.seeds.text().strip()
        if not seeds:
            return self._warn("No seeds", "Enter one or more seed field ids/names (an id, or an FBG substring).")
        out = self.rg_out.text().strip()
        if not out:
            return self._warn("No output folder", "Pick a folder to write the campaign into.")
        idb = self.rg_idbase.text().strip()
        if idb and not idb.isdigit():
            return self._warn("Bad id base", "id base must be a number (e.g. 6000) — or blank for the default.")
        Path(out).mkdir(parents=True, exist_ok=True)
        self._kit(self._region_args(out=str(Path(out).resolve())), subject=f"Fork region {seeds}",
                  ok_next=f"Forked the chain to {out}. Open its campaign.toml on Build & Deploy → Deploy; then to "
                          f"make New Game start here, use Build & Deploy → New Game entry (point it at the entry "
                          f"id) and relaunch.")

    def on_find(self):
        flt = self.field.text().strip()
        self._kit(["list-fields", flt] if flt else ["list-fields"], subject="Find fields")

    def on_preview(self):
        field = self.field.text().strip()
        if not field:
            return self._warn("No field", "Enter a real field id or name to preview its fork fidelity.")
        self._kit(["fork-report", field], subject="Fork preview",
                  ok_next="Read the fidelity report (it recommends a fork mode). Verbatim is the faithful "
                          "default — note its suggested [startup] scenario, Import, then add that beat in the "
                          "editor; or switch to Re-authorable to carry NPCs/dialogue as editable content.")

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
        verbatim = self.mode_verbatim.isChecked()
        args = jobs.import_args(field, out=str(Path(out).resolve()), field_id=fid,
                                name=self.name.text().strip() or None, art=self._art(),
                                carry_npcs=self.carry_npcs.isChecked(), carry_text=self.carry_text.isChecked(),
                                dialogue_stubs=self.dialogue_stubs.isChecked(),
                                save_moogle=self.save_moogle.isChecked(), verbatim=verbatim)
        mode = "verbatim — real script + dialogue, real logic" if verbatim else "re-authorable carry"
        self._kit(args, subject=f"Import {field}",
                  ok_next=f"Forked ({mode}) to {out}. Open it on the Build & Deploy tab to compile + deploy"
                          + ("; then add a [startup] beat (Editor tab → the field's Field form) so it boots the "
                             "right story state instead of scenario zero." if verbatim else "."))

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
