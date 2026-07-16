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
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
    QRadioButton, QScrollArea, QVBoxLayout, QWidget,
)

from . import widgets


class ImportDoc(QWidget):
    """Fork-from-game + read/inspect, as a Workspace document. ``run`` = ``shell.run_job`` (streams a CLI
    job to the Output panel + posts a verdict); ``problems`` = ``shell._show_problems`` (unused here -- the
    shell-outs have only a stream + a return code, so the verdict comes from run_job)."""

    def __init__(self, pal, kit_root, *, run, problems=None, on_forked=None, thumbs=None,
                 on_open_models=None):
        super().__init__()
        self.pal = pal
        self.thumbs = thumbs                           # the shell's ThumbService (field art previews); optional
        self._preview_key = None                       # the thumb key we're waiting on for the fork preview
        self._on_open_models = on_open_models          # shell callback: switch to the Models tab
        if thumbs is not None:
            thumbs.ready.connect(self._on_thumb_ready)
        self.kit = Path(kit_root)                      # `-m ff9mapkit` cwd (this worktree's package)
        # Default output base: the repo parent for a checkout; an installed copy's package dir is inside a
        # venv, so write forked projects to a discoverable user folder instead (not buried in site-packages).
        self.proj_base = (self.kit.parent if (self.kit / "pyproject.toml").is_file()
                          else Path.home() / "Dream World IX")
        self._run = run
        self._on_forked = on_forked                    # called with the output DIR on a clean fork -> shell opens it
        # The tab body SCROLLS: this view stacks five tall group boxes, so a short window would otherwise
        # cram/overlap them (and the inflated minimum height blocks the bottom Output dock from growing). The
        # scroll area keeps THIS widget's min height small so the dock is resizable + the boxes never collide.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        root = QVBoxLayout(inner)
        widgets.page_margins(root)                      # the page rung (was a hand-typed 16)
        root.setSpacing(widgets.SECTION_GAP)            # the rhythm between the raised panels (was 12)
        # The crown. The intro was already here and already correct -- it just had nothing above it, so
        # the screen's most prominent object was whatever card happened to be first.
        crown, _ = widgets.nameplate(
            "", "Import",
            "Bring content in from your real FF9 install (needs UnityPy). The usual start is to fork a "
            "single real field — everything else lives under “More ways to import”.")
        root.addWidget(crown)
        # Phase 6: FOREGROUND the simple-fork path; tuck the four other jobs (region / catalog+archive /
        # repaint / models / read) behind a disclosure, so the default Import view is one clear task.
        root.addWidget(self._fork_box())
        more = widgets.disclosure("More ways to import — region · catalog · repaint · models · read")
        for _boxfn in (self._region_box, self._archive_box, self._repaint_box, self._models_box, self._read_box):
            more.content_layout.addWidget(_boxfn())
        self._more_import = more                        # kept so the smoke can assert it's collapsed by default
        root.addWidget(more)
        root.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self._buttons = [self.find_btn, self.preview_btn, self.study_btn, self.rooms_btn, self.import_btn,
                         self.dryrun_btn, self.fork_region_btn, self.catalog_btn, self.arc_btn,
                         self.rp_unpack_btn, self.rp_pack_btn,
                         self.dlg_btn, self.save_btn, self.list_btn, self.songs_btn, self.sfx_btn,
                         self.tpl_btn]

    # ------------------------------------------------------------------ fork-a-field
    def _fork_box(self):
        box = widgets.section("Fork a real field")
        v = box.content_layout
        lbl = widgets.caption("ONE screen — an id, or an FBG-name substring (e.g. 100, grgr, alxt_map016). For a whole "
                              "connected AREA (many screens wired together), use Fork a region below. "
                              "Find… looks up exact names/ids; Preview shows what a fork will/won't reproduce.")
        v.addWidget(lbl)
        row = QHBoxLayout()
        self.field = QLineEdit()
        self.field.setPlaceholderText("field id or name")
        self.field.setAccessibleName("Field id or name")        # no visible label to buddy
        self.find_btn = QPushButton("Find…")
        self.find_btn.setToolTip("List the real FF9 fields matching the box above (id + name) — the same lookup "
                                 "as 'List fields' under Read & inspect.")
        self.find_btn.clicked.connect(self.on_find)
        row.addWidget(self.field, 1)
        row.addWidget(self.find_btn)
        v.addLayout(row)
        # the pre-fork STUDY row -- 'fork/learn from a real field's bytes BEFORE authoring' as buttons
        study = QHBoxLayout()
        self.preview_btn = QPushButton("Preview fidelity")
        self.preview_btn.clicked.connect(self.on_preview)
        study.addWidget(self.preview_btn)
        self.explain_chk = QCheckBox("+ explain NPC logic")
        self.explain_chk.setToolTip("fork-report --explain: decode each NPC's talk routine into readable "
                                    "English (dialogue + items + the funcs it runs) — shows WHY a "
                                    "render-only NPC needs --verbatim.")
        study.addWidget(self.explain_chk)
        self.study_btn = QPushButton("Study logic…")
        self.study_btn.setToolTip("The field's whole .eb as a read-only, legible logic map (every entry + "
                                  "routine: dialogue, rewards, flags, warps) — study the real bytes before "
                                  "you fork. Needs the install; ~2–5 s.")
        self.study_btn.clicked.connect(self.on_study_logic)
        study.addWidget(self.study_btn)
        study.addStretch(1)
        v.addLayout(study)
        self.preview_img = QLabel()                    # the room's actual background, shown by Preview fidelity
        self.preview_img.setVisible(False)
        v.addWidget(self.preview_img)

        mode = widgets.section("Fork mode")
        mv = mode.content_layout
        # NB: radio/checkbox labels can't word-wrap, so a long label forces the whole tab's minimum width
        # (horizontal scrolling at normal window sizes). Keep them SHORT; detail goes in the wrapped hints.
        self.mode_verbatim = QRadioButton("Verbatim — the truest fork (recommended)")
        self.mode_authorable = QRadioButton("Re-authorable — editable content; you rebuild the logic (advanced)")
        self.mode_verbatim.setChecked(True)
        mv.addWidget(self.mode_verbatim)
        mv.addWidget(self.mode_authorable)
        mhint = widgets.caption("Verbatim ships the field's real event script + dialogue WHOLE — it runs the original "
                                "logic, story gating, real doors and rotating cast (the proven faithful path), carrying "
                                "every NPC/prop/line itself. A verbatim fork boots at scenario zero — use Preview fidelity "
                                "for the suggested starting beat, then add a [startup] block in the editor. The scene + "
                                "carry options appear only in Re-authorable mode (which drops the real logic for editable "
                                "[[npc]]/content you re-author).")
        mv.addWidget(mhint)
        self.mode_verbatim.toggled.connect(self._sync_mode)
        v.addWidget(mode)

        self.art_box = widgets.section("Background art")
        av = self.art_box.content_layout
        self.art_native = QRadioButton("Native — seamless + faithful; ANY field (recommended)")
        self.art_borrow = QRadioButton("BG-borrow — reuse the real art (fast; area ≥ 10)")
        self.art_editable = QRadioButton("Editable scene — repaintable layers (seam-prone)")
        self.art_native.setChecked(True)
        for r in (self.art_native, self.art_borrow, self.art_editable):
            av.addWidget(r)
        art_hint = widgets.caption("Editable scenes show grid seams — to repaint seamlessly, fork Native and use "
                                   "‘Repaint a native fork’ below. BG-borrow points DictionaryPatch at the real art.")
        av.addWidget(art_hint)
        v.addWidget(self.art_box)

        self.carry_box = widgets.section("Carry from the real field")
        cv = self.carry_box.content_layout
        self.carry_npcs = QCheckBox("NPCs & props faithfully (push/talk interactions fire)")
        self.carry_text = QCheckBox("Real dialogue, verbatim (per language)")
        self.dialogue_stubs = QCheckBox("Dialogue as editable [[npc]] stubs (to RE-AUTHOR, not carry)")
        self.save_moogle = QCheckBox("Save point — hidden Moogle + flourish (if the field has one)")
        self.carry_npcs.setChecked(True)
        self.carry_text.setChecked(True)
        for c in (self.carry_npcs, self.carry_text, self.dialogue_stubs, self.save_moogle):
            cv.addWidget(c)
        v.addWidget(self.carry_box)
        # NB: the initial _sync_mode() is deferred to the END of this method -- it now reads swap_player +
        # writes mode_chip, neither of which exists yet here.

        # Walk as (player swap): who you CONTROL in the fork, decoupled from [party] MEMBERSHIP. Applies to
        # EITHER fork mode (the CLI forces --verbatim when set), so it lives OUTSIDE the verbatim-only carry box.
        swap = QHBoxLayout()
        _l_swap = QLabel("Walk as:")
        swap.addWidget(_l_swap)
        self.swap_player = QComboBox()
        _l_swap.setBuddy(self.swap_player)     # see the buddy note in coopdoc
        self.swap_player.setEditable(True)
        self.swap_player.addItems(["", "zidane", "vivi", "steiner", "garnet", "freya", "quina", "eiko",
                                   "amarant"])
        self.swap_player.setCurrentText("")
        self.swap_player.currentTextChanged.connect(self._sync_mode)   # a Walk-as FORCES verbatim -> reflect it live
        self.swap_player.setMaximumWidth(180)     # a short char-name/GEO id -- don't fill the row (a full-width
        swap.addWidget(self.swap_player)          # combo is a big wheel-scroll target in the scrolling panel)
        self.neutralize = QCheckBox("Neutralize scripted gestures")
        swap.addWidget(self.neutralize)
        self.rooms_btn = QPushButton("Suggest a test room…")
        self.rooms_btn.setToolTip("Sweep ALL fields for the best swap/demo rooms (single-PC, swap-clean, "
                                  "close camera) — answers 'which field should I try this in'. ~45 s; the "
                                  "table streams to Output.")
        self.rooms_btn.clicked.connect(
            lambda: self._kit(["find-rooms"], subject="Find test rooms",
                              ok_next="Pick a room from the table above, put its id in the field box, and "
                                      "Preview fidelity / Import."))
        swap.addWidget(self.rooms_btn)
        swap.addStretch(1)                        # left-align the compact combo + checkbox
        v.addLayout(swap)
        swap_hint = widgets.caption("Optional: control a different character (a playable name) or any model (a GEO id, "
                                    "e.g. a moogle 199) instead of the field's real player. Implies a verbatim fork. On "
                                    "a story field the swapped rig's scripted GESTURES glitch — tick Neutralize to stand "
                                    "cleanly (it won't emote), or fork a free-roam field.")
        v.addWidget(swap_hint)

        out = QHBoxLayout()
        _l_out = QLabel("Write to:")
        out.addWidget(_l_out)
        self.out = QLineEdit(str(self.proj_base / "imported"))
        _l_out.setBuddy(self.out)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.browse_out)
        out.addWidget(self.out, 1)
        out.addWidget(browse)
        v.addLayout(out)
        self.mode_chip = QLabel("")             # live 'what will ACTUALLY run' -- the mode can be forced by Walk-as
        self.mode_chip.setWordWrap(True)
        v.addWidget(self.mode_chip)
        ids = QHBoxLayout()
        _l_fid = QLabel("Field id:")
        ids.addWidget(_l_fid)
        self.fid = QLineEdit("4003")
        _l_fid.setBuddy(self.fid)
        self.fid.setFixedWidth(80)
        ids.addWidget(self.fid)
        _l_nm = QLabel("Name (optional):")
        ids.addWidget(_l_nm)
        self.name = QLineEdit()
        _l_nm.setBuddy(self.name)
        self.name.setFixedWidth(160)
        ids.addWidget(self.name)
        ids.addStretch(1)
        self.import_btn = QPushButton("Import field")
        self.import_btn.clicked.connect(self.on_import)
        ids.addWidget(self.import_btn)
        v.addLayout(ids)
        hint = widgets.caption("→ then deploy what you made on the Build & Deploy tab.")
        v.addWidget(hint)
        self._sync_mode()       # now swap_player + mode_chip exist: set art/carry visibility + the resolved-mode chip
        return box

    def _art(self):
        return "borrow" if self.art_borrow.isChecked() else "editable" if self.art_editable.isChecked() else "native"

    def _effective_verbatim(self):
        """What the fork will ACTUALLY be. A non-empty 'Walk as' FORCES verbatim regardless of the mode radio
        (the CLI requires --verbatim for --swap-player), so the true mode is mode_verbatim OR a swap."""
        swap = self.swap_player.currentText().strip() if hasattr(self, "swap_player") else ""
        return self.mode_verbatim.isChecked() or bool(swap)

    def _sync_mode(self, *_):
        """Keep the UI honest about what will run. Verbatim carries every NPC/prop/line + implies --native, so
        the art + carry boxes are IRRELEVANT -- HIDE them (a greyed box reads as 'blocked', a hidden one as
        'not part of this choice') + pin art to Native. Crucially this keys off EFFECTIVE verbatim (mode OR a
        Walk-as), so setting 'Walk as' visibly hides the editable scene/carry options (they won't apply) -- you
        can never pick 'Editable scene' and silently get verbatim."""
        verbatim = self._effective_verbatim()
        self.art_box.setVisible(not verbatim)
        self.carry_box.setVisible(not verbatim)
        if verbatim:
            self.art_native.setChecked(True)
        if hasattr(self, "mode_chip"):
            self._refresh_mode_chip()

    def _refresh_mode_chip(self):
        """The live 'Will fork: …' label by the Import button -- so you SEE the resolved mode before clicking,
        and the Walk-as override is never silent."""
        swap = self.swap_player.currentText().strip()
        forced = bool(swap) and not self.mode_verbatim.isChecked()
        if self._effective_verbatim():
            txt = "Will fork: VERBATIM" + (" — forced by ‘Walk as’ (editable-scene / carry options ignored)"
                                           if forced else " (real script + dialogue, not editable content)")
        else:
            txt = "Will fork: RE-AUTHORABLE (editable [[npc]]/content)"
        self.mode_chip.setText(txt)
        # WAS an inline `color:{accent}` -- two bugs in one line. (a) accent-as-text measures 2.44:1 on
        # nord and 3.06 on solarized-dark: sub-AA in 6 of 8 palettes, and this is a whole sentence of
        # prose, which is exactly what accent must never be. (b) an inline hex baked from self.pal at
        # build time goes STALE on a live theme switch (the same bug the Home status had).
        # Now: muted by default; `warn` ONLY when the mode was FORCED, because that is the one branch
        # that is a real diagnostic -- the user asked for one thing and is getting another.
        self.mode_chip.setProperty("role", "muted")
        widgets.set_state(self.mode_chip, "warn" if forced else "")

    # ------------------------------------------------------------------ fork-a-region (import-chain)
    def _region_box(self):
        box = widgets.section("Fork a region  (a connected multi-field chain → one campaign)")
        v = box.content_layout
        lbl = widgets.caption("Fork a whole connected AREA at once — the workflow behind the disc-1 opening. Enter one "
                              "or more seed fields (or click Browse FF9 regions… for a catalog of FF9's areas — pick one, "
                              "or several to compose into one campaign); the chain forks everything they reach into a "
                              "single campaign, doors rewired in-fork. Dry-run first to see the blast radius.")
        v.addWidget(lbl)
        row = QHBoxLayout()
        row.addWidget(QLabel("Seeds:"))
        self.seeds = QLineEdit()
        self.seeds.setPlaceholderText("field ids/names, comma-separated — e.g. 300  or  50,100,64")
        self._region_ids = None                  # cluster member ids from the last catalog pick (-> --ids); a
        self.seeds.textEdited.connect(self._clear_region_ids)   # hand-edit clears it (the cluster no longer applies)
        self.catalog_btn = QPushButton("Browse FF9 regions…")
        self.catalog_btn.clicked.connect(self.open_region_catalog)
        row.addWidget(self.seeds, 1)
        row.addWidget(self.catalog_btn)
        v.addLayout(row)
        self.rg_whole = QCheckBox("Whole zone — fork ALL story-state visits of each seed's zone")
        self.rg_verbatim = QCheckBox("Verbatim — real script + dialogue per member (recommended)")
        self.rg_whole.setChecked(False)          # default = the catalog region's own visit (--ids, lean + fast)
        self.rg_verbatim.setChecked(True)
        v.addWidget(self.rg_whole)
        v.addWidget(self.rg_verbatim)
        scope_hint = widgets.caption("Whole zone overrides the catalog's single-visit scope (more fields/ids — Dry-run to "
                                     "preview). Unchecking Verbatim forks re-authorable members whose logic you rebuild "
                                     "yourself.")
        v.addWidget(scope_hint)
        # Walk as (player swap) for the WHOLE chain -- the region analogue of the single-fork swap.
        rswap = QHBoxLayout()
        rswap.addWidget(QLabel("Walk as:"))
        self.rg_swap = QComboBox()
        self.rg_swap.setEditable(True)
        self.rg_swap.addItems(["", "zidane", "vivi", "steiner", "garnet", "freya", "quina", "eiko", "amarant"])
        self.rg_swap.setCurrentText("")
        self.rg_swap.setMaximumWidth(180)         # compact, like the single-fork Walk-as (don't capture wheel-scroll)
        rswap.addWidget(self.rg_swap)
        self.rg_neutralize = QCheckBox("Neutralize scripted gestures")
        rswap.addWidget(self.rg_neutralize)
        rswap.addStretch(1)
        v.addLayout(rswap)
        swap_hint = widgets.caption("Optional: play the WHOLE chain as a different character (a playable name) or any "
                                    "model (a GEO id). Implies verbatim; cutscene members' scripted gestures glitch — "
                                    "tick Neutralize to stand cleanly through them.")
        v.addWidget(swap_hint)
        out = QHBoxLayout()
        out.addWidget(QLabel("Write campaign to:"))
        self.rg_out = QLineEdit(str(self.proj_base / "campaign"))
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
        collide_hint = widgets.caption("Field ids are GLOBAL across every stacked mod folder — to keep TWO regions side by "
                                       "side, give each a DISTINCT id base AND a unique Name prefix, or the second black-"
                                       "screens. The shipped disc-1 opening occupies ~6000–6371.")
        v.addWidget(collide_hint)
        fresh_hint = widgets.caption("Re-forking into the SAME folder reuses the prior fork's ids by default, so in-fork "
                                     "saves survive. Tick --fresh-ids only to re-number from scratch.")
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
        hint = widgets.caption("→ then open the campaign on the Build & Deploy tab to compile + deploy the whole chain.")
        v.addWidget(hint)
        return box

    def _clear_region_ids(self, *_a):
        """A hand-edit of the Seeds box drops the catalog cluster (its member ids no longer describe the seeds),
        so the fork falls back to whole-zone for the typed seeds."""
        self._region_ids = None

    def _region_args(self, *, out):
        from ..editor import jobs
        idb = self.rg_idbase.text().strip()
        # Cluster scope (--ids) by default when a catalog region is picked; "Whole zone" overrides it, and a
        # raw typed seed (no cluster) always forks whole-zone (its safe default -- catches cutscene screens).
        whole = self.rg_whole.isChecked() or not self._region_ids
        ids = None if whole else self._region_ids
        swap = self.rg_swap.currentText().strip()
        return jobs.import_chain_args(
            self.seeds.text().strip(), out=out,
            whole_zone=whole, ids=ids, verbatim=self.rg_verbatim.isChecked() or bool(swap),
            id_base=int(idb) if idb.isdigit() else None,
            name_prefix=self.rg_prefix.text().strip() or None, fresh_ids=self.rg_fresh.isChecked(),
            swap_player=swap or None, neutralize_gestures=self.rg_neutralize.isChecked())

    def _region_swap_ok(self):
        """False (after a warning) if Neutralize is ticked with no 'Walk as' character -- the CLI rejects that."""
        if self.rg_neutralize.isChecked() and not self.rg_swap.currentText().strip():
            self._warn("Neutralize needs a character",
                       "Pick a 'Walk as' character first — Neutralize only applies with a swap.")
            return False
        return True

    # ------------------------------------------------------------------ FF9 region catalog
    def _apply_region_selection(self, arcset, keys):
        """Compose the chosen catalog regions (``refarc.compose_region_fork``) into the Fork-a-region box:
        seeds (one region, or several composed into one campaign) + a suggested name prefix. Returns the seeds
        string. Dialog-free so it's headlessly testable."""
        from .. import refarc as RA
        seeds, prefix, _n = RA.compose_region_fork(arcset, keys)
        self.seeds.setText(seeds)
        self._region_ids = RA.compose_region_ids(arcset, keys)   # the picked visit(s)' ids -> --ids (lean fork)
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
            arcset = RA.load_region_catalog()
        except Exception as e:                          # noqa: BLE001
            return self._warn("Region catalog", f"Couldn't load the FF9 region catalog: {e}")
        dlg = QDialog(self)
        dlg.setWindowTitle("Fork FF9 regions")
        lay = QVBoxLayout(dlg)
        intro = widgets.caption(f"<b>{arcset.title}</b> — pick FF9 regions to fork. Check ONE to fork it alone, or "
                                "SEVERAL to compose their seeds into ONE campaign. 'Use selected' fills the Fork-a-region "
                                "box (review id base / name prefix, then Dry-run or Fork).")
        lay.addWidget(intro)
        lst = QListWidget()
        for a in arcset.arcs:
            count = f"  ·  {len(a.members)} fields" if a.members else ""
            it = QListWidgetItem(f"{a.name}   (seed {a.seed}{count})")
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            it.setData(Qt.ItemDataRole.UserRole, a.key)
            if a.note:
                it.setToolTip(a.note)
            lst.addItem(it)
        lay.addWidget(lst)
        foot = widgets.caption("Each region forks just its OWN story-state visit (the revisits of a place are separate "
                               "regions). Check 'Whole zone' on the Fork box to fork all visits instead. A region's "
                               "starting beat isn't applied here — add a [startup] beat in the editor after forking.")
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
        box = widgets.section("Read & inspect  (read-only / maintenance)")
        v = box.content_layout
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
        self.save_path.setPlaceholderText("SavedData_ww.dat, a Memoria extra-save, or a save JSON")
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
        self.list_btn.setToolTip("List the real FF9 fields matching the filter (id + name).")
        self.list_btn.clicked.connect(self.on_list_fields)
        lst.addWidget(self.list_filter)
        lst.addWidget(self.list_btn)
        self.songs_btn = QPushButton("List songs")
        self.songs_btn.setToolTip("The game's music table (song id → resource) — the ids the [music] "
                                  "section and the Editor's song picker use. First run extracts it from "
                                  "your install (slow once, then cached).")
        self.songs_btn.clicked.connect(lambda: self._kit(["music-list"], subject="List songs"))
        self.sfx_btn = QPushButton("List SFX")
        self.sfx_btn.setToolTip("The game's sound-effect table (id → resource).")
        self.sfx_btn.clicked.connect(lambda: self._kit(["sfx-list"], subject="List SFX"))
        lst.addWidget(self.songs_btn)
        lst.addWidget(self.sfx_btn)
        lst.addStretch(1)
        v.addLayout(lst)

        tpl = QHBoxLayout()
        self.tpl_btn = QPushButton("Regenerate base templates")
        self.tpl_btn.clicked.connect(self.on_templates)
        tplhint = widgets.caption("rebuild the kit's base assets from YOUR install (ships no game data)")
        tpl.addWidget(self.tpl_btn)
        tpl.addWidget(tplhint, 1)
        v.addLayout(tpl)
        return box

    # ------------------------------------------------------------------ import-all archive
    def _archive_box(self):
        """`ff9mapkit import-all` — the whole-game (or one-zone) Blender-ready reference archive: the
        on-disk source of truth you copy field folders out of."""
        box = widgets.section("Reference archive  (import-all — every field, foldered)")
        v = box.content_layout
        lbl = widgets.caption("Bulk-import fields into <out>/<ZONE>/<FBG>/ — lightweight model-against projects "
                              "(camera + walkmesh + background.png) by default, or full repaintable scenes. The "
                              "browsable reference you copy field folders out of.")
        v.addWidget(lbl)
        row = QHBoxLayout()
        row.addWidget(QLabel("Archive root:"))
        self.arc_out = QLineEdit()
        self.arc_out.setPlaceholderText("a GITIGNORED folder — this is SE-derived art (e.g. reference/all-fields)")
        row.addWidget(self.arc_out, 1)
        ab = QPushButton("Browse…")
        ab.clicked.connect(lambda: self._pick_dir_into(self.arc_out, "Archive root (gitignored)"))
        row.addWidget(ab)
        v.addLayout(row)
        opts = QHBoxLayout()
        opts.addWidget(QLabel("Zone filter:"))
        self.arc_pattern = QLineEdit()
        self.arc_pattern.setFixedWidth(140)
        self.arc_pattern.setPlaceholderText("e.g. iccv — blank = ALL")
        self.arc_pattern.setToolTip("Only fields whose FBG folder contains this substring (a zone: iccv / "
                                    "dali / trno …). Blank imports the whole game.")
        opts.addWidget(self.arc_pattern)
        self.arc_editable = QCheckBox("Full editable scenes (bigger + slower)")
        self.arc_editable.setToolTip("Per-depth repaintable layers for art-modding a whole set at once "
                                     "(~2–3 GB whole-game) instead of the lightweight default (~500 MB).")
        opts.addWidget(self.arc_editable)
        self.arc_btn = QPushButton("Build archive")
        self.arc_btn.clicked.connect(self.on_archive)
        opts.addWidget(self.arc_btn)
        opts.addStretch(1)
        v.addLayout(opts)
        hint = widgets.caption("Whole game: ~15–20 s lightweight, minutes + ~2–3 GB editable. Failures (world/special "
                               "fields with no scene) are listed and skipped.")
        v.addWidget(hint)
        return box

    def _pick_dir_into(self, line_edit, caption):
        d = QFileDialog.getExistingDirectory(self, caption)
        if d:
            line_edit.setText(d)

    def on_archive(self):
        out = self.arc_out.text().strip().strip('"')
        if not out:
            return self._warn("No archive root", "Pick the folder to build the archive into (keep it "
                                                 "gitignored — the art is SE-derived).")
        pat = self.arc_pattern.text().strip()
        argv = ["import-all", "--out", out] + (["--pattern", pat] if pat else ["--all"]) \
            + (["--editable"] if self.arc_editable.isChecked() else [])
        self._kit(argv, subject="Build archive",
                  ok_next=f"Archive at {out} — <ZONE>/<FBG>/ folders, each openable here or importable "
                          "in Blender (Import FF9 Field).")

    # ------------------------------------------------------------------ custom 3D models (moved)
    def _models_box(self):
        """A pointer: the model round-trip GRADUATED to its own Models tab (browser with rendered
        previews + detail + the export/import/mint/clip actions). This stub keeps the workflow
        discoverable for anyone who learned it here."""
        box = widgets.section("Custom 3D models")
        v = box.content_layout
        lbl = widgets.caption("Model browsing + the whole edit round-trip (export .glb → Blender → import / mint / "
                              "clips) moved to the Models tab — every model, with rendered previews.")
        v.addWidget(lbl)
        row = QHBoxLayout()
        self.models_tab_btn = QPushButton("Open the Models tab")
        if self._on_open_models is not None:
            self.models_tab_btn.clicked.connect(self._on_open_models)
        else:
            self.models_tab_btn.setEnabled(False)
        row.addWidget(self.models_tab_btn)
        row.addStretch(1)
        v.addLayout(row)
        return box

    # ------------------------------------------------------------------ repaint a native fork
    def _repaint_box(self):
        box = widgets.section("Repaint a native fork's art  (seamless HD round-trip)")
        v = box.content_layout
        lbl = widgets.caption("A NATIVE fork ships its background as a tile-packed atlas.png — awkward to paint by hand. "
                              "Unpack it into spatial Overlay*.png layers (one per depth band, the same picture the engine "
                              "renders), repaint them in any editor, then Pack them back into atlas.png — SEAMLESS, no game "
                              "needed. The atlas stays byte-identical until you actually change a layer. THEN deploy the "
                              "NATIVE *.field.toml (not an editable .bgx fork — those are seam-prone).")
        v.addWidget(lbl)
        row = QHBoxLayout()
        row.addWidget(QLabel("Native project:"))
        self.rp_proj = QLineEdit()
        self.rp_proj.setPlaceholderText("the NATIVE fork folder or its .field.toml — needs scene.bgs.bytes + atlas.png")
        rb = QPushButton("Browse…")
        rb.clicked.connect(self.browse_repaint)
        row.addWidget(self.rp_proj, 1)
        row.addWidget(rb)
        v.addLayout(row)
        btns = QHBoxLayout()
        self.rp_unpack_btn = QPushButton("1. Unpack to layers")
        self.rp_unpack_btn.clicked.connect(self.on_repaint_unpack)
        self.rp_pack_btn = QPushButton("2. Pack into atlas")
        self.rp_pack_btn.setObjectName("accent")
        self.rp_pack_btn.clicked.connect(self.on_repaint_pack)
        btns.addWidget(self.rp_unpack_btn)
        btns.addStretch(1)
        btns.addWidget(self.rp_pack_btn)
        v.addLayout(btns)
        hint = widgets.caption("Native forks only — this is the seamless+repaintable path. (BG-borrow reuses the real "
                               "art; an editable .bgx fork is repaintable too but SEAM-PRONE.) → then deploy the NATIVE "
                               "field.toml on Build & Deploy to see the repaint in-game.")
        v.addWidget(hint)
        return box

    def browse_repaint(self):
        d = QFileDialog.getExistingDirectory(self, "The native fork project folder")
        if d:
            self.rp_proj.setText(d)

    def on_repaint_unpack(self):
        proj = self.rp_proj.text().strip()
        if not proj:
            return self._warn("No project", "Pick the native fork project folder (it has scene.bgs.bytes + "
                              "atlas.png). Forking a field above with Native art produces one.")
        self._kit(["repaint-native", str(Path(proj).resolve())], subject="Unpack repaint layers",
                  ok_next="Repaint the Overlay*.png files in the project's repaint/ folder, then Pack into atlas.")

    def on_repaint_pack(self):
        proj = self.rp_proj.text().strip()
        if not proj:
            return self._warn("No project", "Pick the native fork project folder first, then Unpack to layers.")
        self._kit(["repaint-native", str(Path(proj).resolve()), "--pack"], subject="Pack atlas",
                  ok_next="Repacked the layers into atlas.png (the old one is backed up) — deploy the project on "
                          "Build & Deploy to see the repaint in-game.")

    # ------------------------------------------------------------------ run helpers
    def _confirm(self, title, text):
        return QMessageBox.question(self, title, text) == QMessageBox.StandardButton.Yes

    def _warn(self, title, text):
        QMessageBox.warning(self, title, text)

    def _busy(self, b):
        for btn in self._buttons:
            btn.setEnabled(not b)

    def _kit(self, args, *, subject, ok_next="", forked=None):
        """Stream ``py -m ff9mapkit <args>`` from the kit root into the Output panel via run_job. When
        ``forked`` is the output DIR of a fork job, a clean exit fires ``on_forked`` so the shell opens the
        forked project (the Import->author handoff, instead of 'now go open it on Build & Deploy')."""
        self._busy(True)

        def _done(code):
            self._busy(False)
            if code == 0 and forked is not None and self._on_forked is not None:
                self._on_forked(forked)

        started = self._run([sys.executable, "-m", "ff9mapkit", *args], cwd=self.kit, subject=subject,
                            ok_headline=f"{subject} — done", ok_next=ok_next,
                            fail_hint="See the Output panel (importing needs UnityPy + your FF9 install).",
                            on_finished=_done)
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
        if not self._region_swap_ok():
            return
        self._kit(self._region_args(out=None), subject="Region dry-run",
                  ok_next="Review the BLAST RADIUS + any under-forked zones, then Fork region.")

    def on_fork_region(self):
        seeds = self.seeds.text().strip()
        if not seeds:
            return self._warn("No seeds", "Enter one or more seed field ids/names (an id, or an FBG substring).")
        out = self.rg_out.text().strip()
        if not out:
            return self._warn("No output folder", "Pick a folder to write the campaign into.")
        if not self._region_swap_ok():
            return
        idb = self.rg_idbase.text().strip()
        if idb and not idb.isdigit():
            return self._warn("Bad id base", "id base must be a number (e.g. 6000) — or blank for the default.")
        Path(out).mkdir(parents=True, exist_ok=True)
        self._kit(self._region_args(out=str(Path(out).resolve())), subject=f"Fork region {seeds}",
                  forked=str(Path(out).resolve()),
                  ok_next=f"Forked the chain to {out} — it opens automatically here. Then Build & Deploy → Deploy; "
                          f"to make New Game start here, use Build & Deploy → New Game entry (point it at the entry "
                          f"id) and relaunch.")

    def on_find(self):
        flt = self.field.text().strip()
        self._kit(["list-fields", flt] if flt else ["list-fields"], subject="Find fields")

    def on_preview(self):
        field = self.field.text().strip()
        if not field:
            return self._warn("No field", "Enter a real field id or name to preview its fork fidelity.")
        self._request_preview_art(field)
        argv = ["fork-report", field] + (["--explain"] if self.explain_chk.isChecked() else [])
        self._kit(argv, subject="Fork preview",
                  ok_next="Read the fidelity report (it recommends a fork mode). Verbatim is the faithful "
                          "default — note its suggested [startup] scenario, Import, then add that beat in the "
                          "editor; or switch to Re-authorable to carry NPCs/dialogue as editable content.")

    def on_study_logic(self):
        """'Study logic…' — the doctrine ('fork/learn from a real field's bytes before authoring') as a
        click: decode the field's whole .eb into the read-only logic map, IN-PROCESS (a few seconds behind
        a wait cursor), into a scrollable dialog. Same output as `ff9mapkit logic-map <field>`."""
        field = self.field.text().strip()
        if not field:
            return self._warn("No field", "Enter a real field id or name to study its logic.")
        from PySide6.QtGui import QCursor
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            from .. import forkreport as FR
            from .. import logic_map as LM
            fid = FR.resolve_field_id(field)
            text = LM.format_logic_map(LM.logic_map(fid))
            try:
                rep = FR.analyze(fid)                  # the beat/roster analysis (.eb-only, ~50 ms)
            except Exception:                          # noqa: BLE001  (the map alone is still worth showing)
                rep = None
        except Exception as e:                         # noqa: BLE001  (no install / unknown field / bad .eb)
            QApplication.restoreOverrideCursor()
            return self._warn("Couldn't decode", f"{e}\n\n(Studying a real field needs your FF9 install + "
                                                 "UnityPy — check Settings ▸ Setup & health.)")
        QApplication.restoreOverrideCursor()
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Field logic — {field} (read-only)")
        dlg.resize(860, 660)
        dv = QVBoxLayout(dlg)
        hint = widgets.caption("The field's real .eb, decoded: every entry + routine with its dialogue, rewards, "
                               "flags and warps. Fork it --verbatim to carry ALL of this faithfully.")
        dv.addWidget(hint)
        self._mount_beat_strip(dv, rep)
        body = QPlainTextEdit()
        body.setReadOnly(True)
        body.setPlainText(text)
        dv.addWidget(body, 1)
        close = QPushButton("Close")
        close.clicked.connect(dlg.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        dv.addLayout(row)
        dlg.exec()

    def _mount_beat_strip(self, dv, rep):
        """The BEAT SLIDER: on a rotating-cast field, scrub through the story beats the field gates on and
        watch the spawned roster change (fork-report's #13 director analysis, made visual). A static field
        gets a one-line note instead of a dead slider."""
        muted = f"color:{self.pal['muted']};"
        if rep is None:
            return
        if not rep.beat_roster:
            note = widgets.caption("Roster: static — the cast doesn't rotate with the story"
                          + (f" (gates on SC {', '.join(str(v) for v in rep.sc_gates)})" if rep.sc_gates
                             else " (no ScenarioCounter gating)")
                          + (f" · suggested [startup] scenario = {rep.suggested_scenario}"
                             if rep.suggested_scenario is not None else ""))
            dv.addWidget(note)
            return
        from PySide6.QtWidgets import QSlider
        rows = sorted(rep.beat_roster, key=lambda r: r[0])
        strip = widgets.section("Roster by story beat  (drag to scrub ScenarioCounter)")
        sv = strip.content_layout
        srow = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, len(rows) - 1)
        slider.setPageStep(1)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(1)
        srow.addWidget(slider, 1)
        sv.addLayout(srow)
        beat_lbl = QLabel("")
        beat_lbl.setTextFormat(Qt.TextFormat.RichText)
        beat_lbl.setWordWrap(True)
        sv.addWidget(beat_lbl)

        def show(ix):
            bv, nm, entries = rows[ix]
            where = nm[1] if nm else "?"
            names = ", ".join((n[4:] if n.startswith("GEO_") else n) + (" *" if d else "")
                              for _s, n, d in entries) or "(no carried cast)"
            tags = []
            if bv == 0:
                tags.append("scenario-zero baseline")
            if rep.suggested_scenario == bv:
                tags.append("suggested [startup] beat")
            tag = f' · <span style="{muted}">{" · ".join(tags)}</span>' if tags else ""
            beat_lbl.setText(f"<b>SC {bv}</b> — {where}{tag}<br>"
                             f'<span style="{muted}">{names}&nbsp;&nbsp;(* = a director; approximate — '
                             f"flag-gated content assumed present)</span>")

        slider.valueChanged.connect(show)
        show(0)
        dv.addWidget(strip)

    # ---- fork-preview art (SEE the room you're about to fork) ----
    def _request_preview_art(self, token):
        """Show the field's background beside the fidelity report. Numeric ids only (a name would need the
        install-side index resolved here); async + cached via the shell's ThumbService. ALWAYS resets the
        previous preview first -- stale art next to a different field's report is worse than none."""
        self._preview_key = None
        if hasattr(self, "preview_img"):
            self.preview_img.clear()
            self.preview_img.setVisible(False)
        if self.thumbs is None or not token.isdigit():
            return
        self._preview_key = f"import:{int(token)}"
        png = self.thumbs.request(self._preview_key, None, int(token))
        if png:
            self._show_preview_art(png)

    def _on_thumb_ready(self, member, png):
        if member == self._preview_key:
            self._show_preview_art(png)

    def _show_preview_art(self, png):
        from PySide6.QtGui import QPixmap
        pm = QPixmap(png)
        if pm.isNull():
            return
        self.preview_img.setPixmap(pm.scaledToWidth(300, Qt.TransformationMode.SmoothTransformation))
        self.preview_img.setVisible(True)

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
        swap = self.swap_player.currentText().strip()
        neutralize = self.neutralize.isChecked()
        if neutralize and not swap:
            return self._warn("Neutralize needs a character",
                              "Pick a 'Walk as' character first — Neutralize rewrites the swapped rig's "
                              "gestures, so it only applies with a swap.")
        verbatim = self.mode_verbatim.isChecked() or bool(swap)   # --swap-player forces verbatim in the CLI
        args = jobs.import_args(field, out=str(Path(out).resolve()), field_id=fid,
                                name=self.name.text().strip() or None, art=self._art(),
                                carry_npcs=self.carry_npcs.isChecked(), carry_text=self.carry_text.isChecked(),
                                dialogue_stubs=self.dialogue_stubs.isChecked(),
                                save_moogle=self.save_moogle.isChecked(), verbatim=verbatim,
                                swap_player=swap or None, neutralize_gestures=neutralize)
        swapped = f", walking as {swap}" if swap else ""
        mode = "verbatim — real script + dialogue, real logic" if verbatim else "re-authorable carry"
        if self._art() == "native":                  # a native fork is repaintable -> pre-aim the repaint box at it
            self.rp_proj.setText(str(Path(out).resolve()))
        self._kit(args, subject=f"Import {field}", forked=str(Path(out).resolve()),
                  ok_next=f"Forked ({mode}{swapped}) to {out} — it opens automatically here; Build & Deploy is "
                          "pre-aimed at it" + ("; then add a [startup] beat (Editor tab → the field's Field form) "
                             "so it boots the right story state instead of scenario zero." if verbatim else "."))

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
