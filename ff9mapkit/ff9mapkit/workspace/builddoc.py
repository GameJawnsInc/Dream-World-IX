"""The Build & Deploy document for the Workspace (Phase 6b) -- the tkinter ff9_build_gui, folded in.

Pick a project file; its kind is auto-detected (:func:`..editor.jobs.detect_kind`) and the matching target
panel shows: a single field (test slot / install to game / build to a folder), a whole campaign
(deploy / build-only), a multi-campaign journey (dry-run playbook / one-shot deploy / re-apply links), or a
battle map (deploy + optional trigger field). **Check** validates in-process (structured Problems); **Build /
Deploy / Revert** stream through the shell's ``run_job`` into the Output panel. Only this view is Qt --
detection + argv are jobs.py, verdicts are editor.feedback, and the deploys are the same ``tools/deploy_*.py``
the CLI loop uses (the journey path = ``tools/deploy_journey.py``, the orchestrator above deploy_campaign).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QRadioButton, QScrollArea, QVBoxLayout, QWidget,
)

from . import widgets
from ..editor import feedback as fb
from ..editor import jobs


class BuildDoc(QWidget):
    """Build / deploy a field, campaign, journey, or battle map, as a Workspace document. ``run`` =
    ``shell.run_job`` (streams a subprocess to Output + posts a verdict); ``problems`` =
    ``shell._show_problems`` (the in-process Check verdict + problems list)."""

    def __init__(self, pal, repo_root, *, run, problems):
        super().__init__()
        self.pal = pal
        # Resolve the DEV repo: a repo launch passes its own root; an INSTALLED launch passes the venv dir,
        # but can still light up dev mode if $FF9_REPO (or the cwd) points at a checkout -> resolve_dev_repo.
        self.repo = jobs.resolve_dev_repo(repo_root)
        self.kit = self.repo / "ff9mapkit"             # `-m ff9mapkit build` cwd (local pkg shadows)
        self.kit_cwd = self.kit if self.kit.is_dir() else None   # None -> run_job falls back to KIT (always valid)
        # A repo checkout has the deploy scripts at <repo>/tools/; an installed copy (pip/uv/.exe) does NOT,
        # so the test-slot DEPLOY + the F6 loop are unavailable there. `build` + campaign/journey/New-Game
        # deploy work either way (the latter via the package CLI).
        self.has_tools = jobs.has_deploy_tools(self.repo)
        self._run = run
        self._problems = problems
        self.kind = "field"
        self.plan = None                               # the campaign plan when kind == "campaign"
        self.manifest = None                           # the journey manifest when kind == "journey"
        self.field_id = None
        self.field_name = None
        self.inplace_target = None                      # {donor,name,text_block,is_forest} for a verbatim fork of a real field
        self._inplace_available = False                 # in-place radio is live (a fork of a real field + dev tools)
        self.mod_folder, self.worktree_id = jobs.detect_deploy_target(self.repo)
        self.game_mod = jobs.detect_game_mod()
        self._build_ui()
        self._render_kind()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # SCROLL the body: five target group boxes + the New-Game box stack tall, so a short window would
        # cram them and inflate the central minimum height (blocking the bottom Output dock from growing).
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(16, 16, 16, 16)           # 4pt-grid page padding
        v.setSpacing(12)                                # 4pt-grid rhythm between the raised panels
        row = QHBoxLayout()
        row.addWidget(QLabel("Project file:"))
        self.path = QLineEdit()
        self.path.setAccessibleName("Project file to build or deploy")
        self.path.setPlaceholderText("a .field.toml, campaign.toml, journeys.toml, or battle.toml")
        self.path.textChanged.connect(self._on_path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.browse)
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        v.addLayout(row)

        self.status = QLabel("Pick a field, campaign, journey, or battle file.")
        self.status.setWordWrap(True)
        self.status.setProperty("role", "muted")
        v.addWidget(self.status)

        v.addWidget(self._field_box())
        v.addWidget(self._campaign_box())
        v.addWidget(self._journey_box())
        # Phase 6: the routine deploy is field / campaign / journey (the F9 button drives these). The niche
        # battle target and the New-Game footgun (single-owner -- a wholesale campaign re-deploy WIPES it) are
        # fenced behind an Advanced drawer so they're not visually co-equal with routine deploy.
        adv = widgets.disclosure("Advanced — battle deploy · New Game entry (single-owner)")
        adv.content_layout.addWidget(self._battle_box())
        adv.content_layout.addWidget(self._newgame_box())
        self._advanced = adv
        v.addWidget(adv)

        btns = QHBoxLayout()
        self.chk = QPushButton("Check logic")
        self.chk.clicked.connect(self.on_check)
        self.go = QPushButton("Build / Deploy")
        self.go.clicked.connect(self.on_go)
        self.rev = QPushButton("Revert test deploy")
        self.rev.clicked.connect(self.on_revert)
        self.pack_btn = QPushButton("Package (zip)…")
        self.pack_btn.setToolTip("Zip a BUILT mod folder into a shareable release — the last step of the "
                                 "funnel. Unzipping it next to FF9_Launcher.exe installs the mod.")
        self.pack_btn.clicked.connect(self.on_pack)
        btns.addWidget(self.chk)
        btns.addWidget(self.go)
        btns.addWidget(self.rev)
        btns.addWidget(self.pack_btn)
        btns.addStretch(1)
        v.addLayout(btns)
        v.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def _field_box(self):
        box = QGroupBox("Build to (field)")
        gv = QVBoxLayout(box)
        self.tg = QButtonGroup(self)
        tid = self.worktree_id or 4003
        # In-place: only meaningful for a verbatim fork of a REAL field -> hidden until such a project loads
        # (set_field fills the label + shows it). Placed FIRST so it reads as the preferred route for a fork.
        self.rb_inplace = QRadioButton("In-place on the real field")
        self.rb_inplace.setVisible(False)
        self.tg.addButton(self.rb_inplace)
        self.rb_inplace.toggled.connect(self._update_dest)
        self.rb_test = QRadioButton(f"Test slot {tid} — quick + reversible; play via F6 → Warp"
                                    + ("  (or New Game → hut door)" if tid == 4003 else ""))
        self.rb_test.setChecked(self.has_tools)        # installed copy: no F6 dev engine -> default to Install to game
        # label = the folder NAME only; the full path lives in the tooltip. (An unwrappable radio label
        # carrying the whole install path forced the tab's minimum width past the pane -> h-scrolling.)
        self.rb_game = QRadioButton(f"Install to game (shipping mod folder): {Path(self.game_mod).name}"
                                    if self.game_mod else "Install to game — (game install not found)")
        if self.game_mod:
            self.rb_game.setToolTip(str(self.game_mod))
        else:
            self.rb_game.setEnabled(False)
        of = QHBoxLayout()
        self.rb_other = QRadioButton("Build only — to a folder:")
        self.other = QLineEdit()
        ob = QPushButton("Browse…")
        ob.clicked.connect(self.browse_other)
        of.addWidget(self.rb_other)
        of.addWidget(self.other, 1)
        of.addWidget(ob)
        for rb in (self.rb_test, self.rb_game, self.rb_other):
            self.tg.addButton(rb)
            rb.toggled.connect(self._update_dest)
        self.other.textChanged.connect(self._update_dest)
        gv.addWidget(self.rb_inplace)
        gv.addWidget(self.rb_test)
        gv.addWidget(self.rb_game)
        gv.addLayout(of)
        self.dest = QLabel("")
        self.dest.setWordWrap(True)
        self.dest.setProperty("role", "accent")
        gv.addWidget(self.dest)
        if not self.has_tools:                         # installed: no test-slot/F6 -> default to Install to game / Build only
            self.rb_test.setEnabled(False)
            self.rb_test.setText(self.rb_test.text() + "   (dev repo only)")
            self.rb_test.setToolTip("The test slot + F6 reload loop need a source checkout. Set the FF9_REPO "
                                    "environment variable to your Dream World IX repo (or launch it from there), "
                                    "then reopen — this lights up.")
            (self.rb_game if self.game_mod else self.rb_other).setChecked(True)  # safe now: self.dest exists
        self.field_box = box
        return box

    def _campaign_box(self):
        box = QGroupBox("Deploy campaign")
        cv = QVBoxLayout(box)
        self.cg = QButtonGroup(self)
        self.rb_camp_deploy = QRadioButton("Deploy to game (reversible)")
        self.rb_camp_deploy.setChecked(True)
        self.rb_camp_build = QRadioButton("Build only — compile every member to the campaign's dist/")
        self.cg.addButton(self.rb_camp_deploy)
        self.cg.addButton(self.rb_camp_build)
        self.wire_newgame = QCheckBox("Wire New Game entry (experimental — off = reach the chain via a gateway, "
                                      "or F6 → Warp on a dev build)")
        cv.addWidget(self.rb_camp_deploy)
        cv.addWidget(self.rb_camp_build)
        cv.addWidget(self.wire_newgame)
        self.campaign_box = box
        return box

    def _journey_box(self):
        box = QGroupBox("Deploy journey")
        jv = QVBoxLayout(box)
        self.jg = QButtonGroup(self)
        self.rb_jour_preview = QRadioButton("Preview deploy playbook (dry-run — no game files touched)")
        self.rb_jour_preview.setChecked(True)
        self.rb_jour_apply = QRadioButton("Deploy journey to game (one-shot: campaigns → links → hub, reversible)")
        self.rb_jour_links = QRadioButton("Re-apply cross-campaign links only (after a campaign re-deploy)")
        for rb in (self.rb_jour_preview, self.rb_jour_apply, self.rb_jour_links):
            self.jg.addButton(rb)
            rb.toggled.connect(self._update_journey_hint)
            jv.addWidget(rb)
        # Single mod folder: merge the whole journey into ONE FolderNames entry (one-shot deploy only)
        self.cb_single_folder = QCheckBox("Single mod folder — merge the whole journey into ONE FolderNames "
                                          "entry (instead of one folder per campaign)")
        self.cb_single_folder.setToolTip("Cleaner one-folder install. Trade-off: re-deploying re-merges the "
                                         "whole journey — you lose cheap per-campaign re-deploy.")
        jv.addWidget(self.cb_single_folder)
        # New-Game landing: meaningful only for the one-shot deploy (single-owner) -> disabled otherwise
        self.ng_group = QGroupBox("New Game landing (one-shot deploy — single-owner)")
        ngv = QVBoxLayout(self.ng_group)
        self.ngg = QButtonGroup(self)
        self.rb_ng_none = QRadioButton("Don't wire New Game — reach the hub via F6 → Warp")
        self.rb_ng_none.setChecked(True)
        self.rb_ng_hub = QRadioButton("Wire New Game → the hub menu (pick the journey at Mognet; seamless)")
        self.rb_ng_entry = QRadioButton("Wire New Game → straight into the opening (no menu; keeps the real FMV)")
        self.rb_ng_entry.setToolTip("Single-journey arc only — a multi-journey hub has no single opening to land in.")
        for rb in (self.rb_ng_none, self.rb_ng_hub, self.rb_ng_entry):
            self.ngg.addButton(rb)
            ngv.addWidget(rb)
        self.ng_group.setEnabled(False)
        jv.addWidget(self.ng_group)
        self.journey_hint = QLabel("")
        self.journey_hint.setWordWrap(True)
        self.journey_hint.setProperty("role", "caption")
        jv.addWidget(self.journey_hint)
        self.journey_box = box
        return box

    def _newgame_box(self):
        # always-visible: point New Game straight at a deployed field id (the hub-less single destination).
        box = QGroupBox("New Game entry  (skip the hub — land straight on a field)")
        gv = QVBoxLayout(box)
        row = QHBoxLayout()
        row.addWidget(QLabel("Field id:"))
        self.newgame_id = QLineEdit()
        self.newgame_id.setFixedWidth(90)
        self.newgame_id.setPlaceholderText("4100")
        self.set_ng = QPushButton("Point New Game here")
        self.set_ng.clicked.connect(self.on_set_newgame)
        self.rev_ng = QPushButton("Revert New Game")
        self.rev_ng.clicked.connect(self.on_revert_newgame)
        row.addWidget(self.newgame_id)
        row.addWidget(self.set_ng)
        row.addWidget(self.rev_ng)
        row.addStretch(1)
        gv.addLayout(row)
        hint = QLabel("Single-owner: CREATES the field-70 override from stock (opening FMV preserved) and "
                      "replaces the current New-Game landing (skips any World Hub) — works even on a clean "
                      "install or a fresh region fork. The field must already be DEPLOYED/registered. Relaunch "
                      "to test.")
        hint.setWordWrap(True)
        hint.setProperty("role", "caption")            # de-emphasise the jargon paragraph (smaller, quieter)
        gv.addWidget(hint)
        self.newgame_box = box
        return box

    def _battle_box(self):
        box = QGroupBox("Deploy battle map")
        bv = QVBoxLayout(box)
        self.battle_dest = QLabel(f"Test mod folder: {self.mod_folder}")
        self.battle_dest.setProperty("role", "muted")
        bv.addWidget(self.battle_dest)
        tf = QHBoxLayout()
        tf.addWidget(QLabel("Trigger field (optional):"))
        self.trigger = QLineEdit()
        self.trigger.setFixedWidth(90)
        tf.addWidget(self.trigger)
        self.trigger_hint = QLabel("repoint a deployed field's encounter at the minted scene (only for a "
                                   "from-scratch new scene, not a reskin/fork).")
        self.trigger_hint.setWordWrap(True)
        self.trigger_hint.setProperty("role", "caption")
        tf.addWidget(self.trigger_hint, 1)
        bv.addLayout(tf)
        self.battle_box = box
        return box

    # ------------------------------------------------------------------ kind detection + rendering
    def crumb_label(self):
        """A short 'you are deploying X' label for the breadcrumb when the Build & Deploy tab is active --
        the detected kind + the target file name (or a no-target hint)."""
        p = self.path.text().strip().strip('"')
        return f"{self.kind} · {Path(p).name}" if p else "no build target"

    def set_target(self, path):
        """Point the doc at a project file (the shell calls this when a campaign/field opens, so Build &
        Deploy is pre-aimed at what you're working on)."""
        self.path.setText(str(path))

    def _on_path(self, _text=None):
        path = self.path.text().strip().strip('"')
        kind, payload = ("field", None)
        if path and Path(path).is_file():
            kind, payload = jobs.detect_kind(path)
        self.kind = kind
        self.plan = payload if kind == "campaign" else None
        self.manifest = payload if kind == "journey" else None
        if kind == "field":
            self.field_id, self.field_name = jobs.field_id_name(path) if path else (None, None)
            self.inplace_target = jobs.field_inplace_target(path) if path else None
            if self.field_id is not None and not self.newgame_id.text().strip():
                self.newgame_id.setText(str(self.field_id))   # convenience: prefill the New-Game target once
        self._render_kind()

    def _render_kind(self):
        self.field_box.setVisible(self.kind == "field")
        self.campaign_box.setVisible(self.kind == "campaign")
        self.journey_box.setVisible(self.kind == "journey")
        self.battle_box.setVisible(self.kind == "battle")
        if self.kind == "battle" and hasattr(self, "_advanced"):
            self._advanced.toggle_button.setChecked(True)   # the battle box lives in the Advanced drawer -> reveal it
        self.rev.setEnabled(True)                  # default; _update_dest disables it for a field's no-undo destinations
        self.rev.setToolTip("Undo the last deploy and restore the previous state.")
        if self.kind == "campaign" and self.plan is not None:
            ids = [m.new_id for m in self.plan.members]
            rng = f"{min(ids)}-{max(ids)}" if ids else "?"
            self.status.setText(f"Campaign '{self.plan.name}': {len(self.plan.members)} fields "
                                f"(ids {rng}) → {self.plan.mod_folder}")
            self.go.setText("Build / Deploy campaign")
            self.rev.setText("Revert campaign")
            self.chk.setText("Check campaign")
            self.rb_camp_deploy.setText(f"Deploy to game (reversible) → {self.plan.mod_folder}")
        elif self.kind == "journey" and self.manifest is not None:
            m = self.manifest
            hub_id = m.hub.get("id") if m.hub else None
            name = (m.hub.get("name") if m.hub else None) or Path(self.path.text().strip()).stem
            self.status.setText(f"Journey '{name}': {len(m.journeys)} journey(s), hub field {hub_id} "
                                "→ each campaign stacks into its own mod folder.")
            self.go.setText("Build / Deploy journey")
            self.rev.setText("Revert journey")
            self.chk.setText("Check journey")
            self._update_journey_hint()
        elif self.kind == "battle":
            deployed = jobs.detect_deployed_fields(self.mod_folder)
            avail = ("deployed: " + ", ".join(f"{i} ({n})" for i, n in deployed) + " — ") if deployed \
                else "no fields deployed here yet — "
            self.trigger_hint.setText(avail + "repoint a deployed field's encounter at the minted scene "
                                              "so you can fight it now (only for a from-scratch new scene; "
                                              "blank otherwise).")
            self.status.setText(f"Battle map: {Path(self.path.text().strip()).name} → {self.mod_folder}")
            self.go.setText("Build / Deploy battle")
            self.rev.setText("Revert battle")
            self.chk.setText("Check battle")
        else:
            self.go.setText("Build / Deploy")
            self.rev.setText("Revert test deploy")
            self.chk.setText("Check logic")
            p = self.path.text().strip()
            if p and self.field_id is not None:
                self.status.setText(f"Field: {self.field_name or Path(p).stem} (its own id: {self.field_id})"
                                    f" — {Path(p).name}")
            elif p:
                self.status.setText(f"Field project: {Path(p).name}")
            else:
                self.status.setText("Pick a field, campaign, journey, or battle file.")
            self._sync_inplace()
            self._update_dest()

    def _sync_inplace(self):
        """Show/label the In-place radio for a verbatim fork of a real field, and DEFAULT to it (the usual
        intent for such a fork -- and mandatory for a Chocobo forest, whose HUD is hardcoded on the donor id).
        Needs the dev test-slot tooling; on an installed copy it stays hidden (no reversible test folder)."""
        t = self.inplace_target
        show = bool(t) and self.has_tools
        self._inplace_available = show                  # the logic gate (isVisible() is unreliable off-screen / off-tab)
        self.rb_inplace.setVisible(show)
        if not show:
            if self.rb_inplace.isChecked():            # a prior fork's default -> fall back to a live option
                (self.rb_test if self.has_tools else self.rb_game if self.game_mod else self.rb_other).setChecked(True)
            return
        forest = " (Chocobo forest — keeps the dig HUD)" if t["is_forest"] else ""
        self.rb_inplace.setText(f"In-place on field {t['donor']} — reversible; keeps the real field's "
                                f"id/name/HUD{forest}")
        self.rb_inplace.setToolTip(
            f"Deploys under the donor's own id {t['donor']} (text block {t['text_block']}) into "
            f"{self.mod_folder}, so the engine loads this in place of the real field. Reach it the normal "
            f"way, or F6 → Warp {t['donor']}. Reversible.")
        self.rb_inplace.setChecked(True)               # the preferred route for a fork of a real field

    def _update_dest(self, *_):
        if self.kind != "field":
            return
        tid = self.worktree_id or 4003
        own = self.field_id if self.field_id is not None else "?"
        if self._inplace_available and self.rb_inplace.isChecked():
            t = self.inplace_target
            msg = (f"→ deploys IN PLACE on field {t['donor']} in {self.mod_folder} (reversible). The engine "
                   f"loads this instead of the real field — reach it the normal way, or F6 → Warp {t['donor']}."
                   + ("  Keeps the Chocobo dig HUD." if t["is_forest"] else ""))
            self.rev.setEnabled(True)              # the deploy writes a per-id revert script
            self.rev.setToolTip(f"Undo the last in-place deploy on field {t['donor']} (restores its previous "
                                "contents).")
        elif self.rb_test.isChecked():
            msg = (f"→ deploys to field {tid} in {self.mod_folder} (your test slot; reversible). "
                   f"Your field's own id ({own}) is overridden — reach it via F6 → Warp to {tid}.")
            self.rev.setEnabled(True)              # the test deploy writes a revert script
            self.rev.setToolTip("Undo the last test-slot deploy (restores the slot's previous contents).")
        elif self.rb_game.isChecked():
            where = self.game_mod or "(game install not found)"
            msg = f"→ installs at field {own} (the field's OWN id) in {where} — overwrites any field {own} there."
            self.rev.setEnabled(False)             # a direct game install overwrites in place -- no revert script
            self.rev.setToolTip(f"A direct game install overwrites field {own} in place — there's no automatic "
                                "undo. Restore from your backup, or re-install the original field.")
        else:
            folder = self.other.text().strip() or "(pick a folder)"
            msg = f"→ builds field {own} into {folder} — no game change."
            self.rev.setEnabled(False)             # building into a plain folder deploys nothing to revert
            self.rev.setToolTip("Builds into a plain folder — nothing was deployed to the game to revert.")
        self.dest.setText(msg)

    def _journey_newgame_mode(self) -> str:
        """The selected New-Game landing for the one-shot deploy: ``"hub"`` / ``"entry"`` / ``"none"``."""
        if self.rb_ng_hub.isChecked():
            return "hub"
        if self.rb_ng_entry.isChecked():
            return "entry"
        return "none"

    def _update_journey_hint(self, *_):
        if self.kind != "journey":
            return
        apply_on = self.rb_jour_apply.isChecked()
        if self.rb_jour_preview.isChecked():
            msg = ("→ lints the manifest + prints the ordered deploy playbook. No game files are touched — "
                   "safe to run anytime; review the steps, then switch to 'Deploy journey to game'.")
        elif self.rb_jour_links.isChecked():
            msg = ("→ re-applies ONLY the cross-campaign link .eb remaps (run after a campaign re-deploy "
                   "wholesale-replaces its folder and wipes the links). The campaigns must already be deployed.")
        elif self.cb_single_folder.isChecked():
            msg = ("→ one-shot, SINGLE FOLDER: build every campaign + the hub, MERGE them into one stacked mod "
                   "folder (one Memoria.ini entry), apply the cross-campaign links, optional New Game — one "
                   "unified revert. Cleaner install; re-deploying re-merges the whole journey.")
        else:
            msg = ("→ one-shot: each campaign → its own stacked folder, the cross-campaign links, then the hub "
                   "field — one unified revert. You then stack the folders in Memoria.ini and relaunch once.")
        self.cb_single_folder.setEnabled(apply_on)
        self.ng_group.setEnabled(apply_on)
        # "straight into the opening" needs a single-journey manifest (a multi-journey hub has no single opening)
        single = self.manifest is not None and len(self.manifest.journeys) == 1
        self.rb_ng_entry.setEnabled(apply_on and single)
        if not single and self.rb_ng_entry.isChecked():
            self.rb_ng_none.setChecked(True)
        self.journey_hint.setText(msg)

    # ------------------------------------------------------------------ pickers
    def browse(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Pick a field.toml, campaign.toml, journeys.toml, or battle.toml", self.path.text().strip(),
            "Field / campaign / journey / battle (*.toml);;All files (*)")
        if f:
            self.path.setText(f)

    def browse_other(self):
        d = QFileDialog.getExistingDirectory(self, "Output folder")
        if d:
            self.other.setText(d)
            self.rb_other.setChecked(True)

    # ------------------------------------------------------------------ helpers
    def _confirm(self, title, text):
        return QMessageBox.question(self, title, text) == QMessageBox.StandardButton.Yes

    def _warn(self, title, text):
        QMessageBox.warning(self, title, text)

    def _info(self, title, text):
        QMessageBox.information(self, title, text)

    def _require_tools(self, what):
        """Installed (non-repo) copies don't ship the deploy SCRIPTS (tools/). Show a clear, actionable
        message instead of a cryptic 'no such file' and return False; True when the repo tools are present."""
        if self.has_tools:
            return True
        self._warn(
            f"{what} needs a dev checkout",
            f"'{what}' uses the development deploy loop (the repo's tools/ + the F6 dev engine), which an "
            "installed copy doesn't ship.\n\n"
            "Two options:\n"
            "  - Point this Workspace at your source checkout: set the FF9_REPO environment variable to your "
            "Dream World IX repo (or launch apps\\ff9_workspace.pyw from it), then reopen — the test slot + F6 "
            "light up.\n"
            "  - Or use  Build -> 'Install to game'  (campaign / journey deploy + 'Set New Game' already work "
            "on an installed copy).")
        return False

    def _picked(self):
        f = self.path.text().strip().strip('"')
        if not f or not Path(f).is_file():
            self._warn("No file", "Pick a .field.toml, campaign.toml, journeys.toml, or battle.toml first.")
            return None
        return f

    def _busy(self, b):
        for w in (self.chk, self.go, self.rev, self.pack_btn, self.set_ng, self.rev_ng):
            w.setEnabled(not b)

    # ------------------------------------------------------------------ Package for sharing
    def _pack_guess(self):
        """(mod_root, name) prefill for the pack dialog, per the open target kind: the staged dist/ beside
        the project file, and the REAL mod-folder name (Memoria identifies a mod by its folder name, so a
        zip must not unpack as 'dist')."""
        f = self.path.text().strip().strip('"')
        base = Path(f).parent if f else None
        if self.kind == "campaign" and self.plan is not None:
            return (base / "dist" if base else None), (self.plan.mod_folder or "FF9CustomMap")
        if self.kind == "journey":
            return None, ""                            # a single-folder journey stages only into the live
        if base is not None:                           # game folder -- pack THAT (the hint says so)
            return base / "dist", "FF9CustomMap"
        return None, ""

    def on_pack(self):
        """'Package (zip)…' — zip a built mod folder for sharing (`ff9mapkit pack`). A small dialog:
        the folder to zip (prefilled with the staged dist/ when one is knowable), the mod-folder name
        inside the zip, and the destination .zip."""
        guess_root, guess_name = self._pack_guess()
        dlg = QDialog(self)
        dlg.setWindowTitle("Package mod for sharing")
        v = QVBoxLayout(dlg)
        hint = QLabel("Zips a BUILT mod folder (DictionaryPatch.txt + StreamingAssets/…) so unzipping next "
                      "to FF9_Launcher.exe installs it. Build/Deploy first — pack takes the OUTPUT folder. "
                      "For a single-folder journey, pack the deployed <game>/<merged folder>.")
        hint.setWordWrap(True)
        hint.setProperty("role", "caption")
        v.addWidget(hint)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Mod folder:"))
        root_edit = QLineEdit(str(guess_root) if guess_root else "")
        row1.addWidget(root_edit, 1)
        b1 = QPushButton("Browse…")

        def _pick_root():
            d = QFileDialog.getExistingDirectory(dlg, "Built mod folder (a dist/ or a deployed mod folder)")
            if d:
                root_edit.setText(d)
        b1.clicked.connect(_pick_root)
        row1.addWidget(b1)
        v.addLayout(row1)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Folder name in the zip:"))
        name_edit = QLineEdit(guess_name)
        name_edit.setToolTip("What Memoria.ini FolderNames will call the mod — a staged dist/ must NOT "
                             "ship as a folder literally named 'dist'.")
        row2.addWidget(name_edit, 1)
        v.addLayout(row2)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Pack…")
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        root = root_edit.text().strip().strip('"')
        if not root or not Path(root).is_dir():
            self._warn("No mod folder", "Pick the BUILT mod folder to zip (run Build / Deploy first).")
            return
        name = name_edit.text().strip() or Path(root).name
        out, _ = QFileDialog.getSaveFileName(self, "Save the release zip as",
                                             str(Path(root).parent / f"{name}.zip"), "Zip (*.zip)")
        if not out:
            return
        self._stream(jobs.pack_argv(root, out, name=name), cwd=self.kit_cwd, subject="Package",
                     ok_headline="Packed — ready to share",
                     ok_next=f"Share {out} — unzipping it next to FF9_Launcher.exe installs the mod "
                             f"(folder '{name}', add it to Memoria.ini FolderNames).")

    def _stream(self, argv, *, cwd, subject, ok_headline, ok_next=""):
        self._busy(True)
        if not self._run(argv, cwd=cwd, subject=subject, ok_headline=ok_headline, ok_next=ok_next,
                         on_finished=lambda _c: self._busy(False)):
            self._busy(False)                          # a job was already running; nothing started

    # ------------------------------------------------------------------ Check (in-process, structured)
    def on_check(self):
        f = self._picked()
        if not f:
            return
        if self.kind == "campaign":
            self._check_campaign(f)
        elif self.kind == "journey":
            self._check_journey(f)
        elif self.kind == "battle":
            self._check_battle(f)
        else:
            self._check_field(f)

    def _verdict(self, errs, warns, *, subject, clean):
        self._problems(fb.classify(errs, warns, subject=subject, clean_headline=clean),
                       fb.problems(errs, warns))

    def _check_field(self, field):
        try:
            from ..build import FieldProject, lint_logic, validate
            p = FieldProject.load(field)
            self._verdict(validate(p), lint_logic(p), subject=f"Check {Path(field).name}",
                          clean=f"{Path(field).name} — no problems")
        except Exception as e:                         # noqa: BLE001
            self._verdict([f"{type(e).__name__}: {e}"], [], subject="Check", clean="")

    def _check_campaign(self, path):
        try:
            from ..campaign import lint_campaign, load_campaign
            plan = load_campaign(path)
            errs, warns = lint_campaign(plan, Path(path).parent)
            self._verdict(errs, warns, subject=f"Campaign lint ({plan.name})", clean=f"{plan.name} — no problems")
        except Exception as e:                         # noqa: BLE001
            self._verdict([f"{type(e).__name__}: {e}"], [], subject="Campaign lint", clean="")

    def _check_journey(self, path):
        try:
            from ..journey import lint_manifest, load_journeys
            m = load_journeys(path)                     # re-load from disk (the file may have changed)
            errs, warns = lint_manifest(m)
            name = (m.hub.get("name") if m.hub else None) or Path(path).stem
            self._verdict(errs, warns, subject=f"Journey lint ({name})", clean=f"{name} — no problems")
        except Exception as e:                         # noqa: BLE001
            self._verdict([f"{type(e).__name__}: {e}"], [], subject="Journey lint", clean="")

    def _check_battle(self, battle):
        try:
            from ..battle.build import BattleProject, validate_battle
            p = BattleProject.load(battle)
            self._verdict(validate_battle(p), [], subject=f"Check {Path(battle).name}",
                          clean=f"{Path(battle).name} — no problems")
        except Exception as e:                         # noqa: BLE001
            self._verdict([f"{type(e).__name__}: {e}"], [], subject="Battle check", clean="")

    # ------------------------------------------------------------------ Build / Deploy
    def on_go(self):
        f = self._picked()
        if not f:
            return
        if self.kind == "campaign":
            self._go_campaign(f)
        elif self.kind == "journey":
            self._go_journey(f)
        elif self.kind == "battle":
            self._go_battle(f)
        else:
            self._go_field(f)

    def _go_field(self, field):
        if self._inplace_available and self.rb_inplace.isChecked():
            if not self._require_tools("Deploy in place"):
                return
            t = self.inplace_target
            hud = "\n\nKeeps the Chocobo dig HUD (hardcoded on the real forest id)." if t["is_forest"] else ""
            if self._confirm(f"Deploy in place on field {t['donor']}",
                             f"Build and deploy this fork IN PLACE on field {t['donor']} ({self.mod_folder})? "
                             f"The engine loads it instead of the real field (reversible).{hud}"):
                self._stream(jobs.deploy_field_inplace_argv(self.repo, field, t), cwd=self.repo,
                             subject=f"Deploy in place on field {t['donor']}",
                             ok_headline=f"Deployed in place on field {t['donor']} ({self.mod_folder})",
                             ok_next=f"In-game: reach it the normal way, or F6 → Warp {t['donor']}.")
            return
        if self.rb_test.isChecked():
            if not self._require_tools("Deploy to test slot"):
                return
            tid = self.worktree_id or 4003
            reach = ("New Game → walk to the hut door (or F6 → Warp)" if tid == 4003
                     else f"F6 → Warp to field {tid}")
            if self._confirm(f"Deploy to test field {tid}",
                             f"Build and deploy this field to the test slot {tid} ({self.mod_folder})? "
                             "It replaces whatever is there now (reversible)."):
                self._stream(jobs.deploy_field_argv(self.repo, field), cwd=self.repo,
                             subject=f"Deploy to test field {tid}",
                             ok_headline=f"Deployed to test field {tid} ({self.mod_folder})",
                             ok_next=f"In-game: {reach}.")
        elif self.rb_game.isChecked():
            if self._confirm("Install to game",
                             f"Build this field into the game mod folder?\n\n{self.game_mod}\n\n"
                             "Writes the field at its real id (may overwrite a field with the same id)."):
                self._stream(jobs.build_argv(field, str(self.game_mod)), cwd=self.kit_cwd,
                             subject="Install to game", ok_headline=f"Built into {self.game_mod}")
        else:
            out = self.other.text().strip()
            if not out:
                return self._warn("No folder", "Pick an output folder.")
            self._stream(jobs.build_argv(field, out), cwd=self.kit_cwd, subject="Build",
                         ok_headline=f"Built into {out}")

    def _go_campaign(self, path):
        if self.rb_camp_build.isChecked():
            self._stream(jobs.build_campaign_argv(path), cwd=self.kit_cwd, subject="Build campaign",
                         ok_headline=f"Built campaign {self.plan.name}")
            return
        wire = self.wire_newgame.isChecked()
        route = ("It also wires New Game to enter the chain (experimental)." if wire
                 else "Reach each screen in-game via F6 → Warp." if self.has_tools
                 else "Reach the chain via New Game (if wired) or a [[gateway]] from an early field.")
        if self._confirm("Deploy campaign",
                         f"Reversibly install campaign '{self.plan.name}' ({len(self.plan.members)} fields) "
                         f"into:\n\n{self.plan.mod_folder}\n\n{route}"):
            ids = [m.new_id for m in self.plan.members]
            entry = self.plan.members[0].new_id if self.plan.members else (min(ids) if ids else "?")
            # Repo checkout -> the dev tool (reverts to tools/scroll_out); installed copy -> the package CLI
            # (ff9mapkit deploy-campaign; reverts to a per-user cache). Same in-game-proven orchestration.
            if self.has_tools:
                argv, cwd = jobs.deploy_campaign_argv(self.repo, path, wire_newgame=wire,
                                                      mod_folder=self.plan.mod_folder), self.repo
            else:
                argv, cwd = jobs.deploy_campaign_pkg_argv(path, wire_newgame=wire,
                                                          mod_folder=self.plan.mod_folder), self.kit_cwd
            reach = (f"Relaunch once (new DictionaryPatch), then F6 → Warp → {entry} to walk the chain." if self.has_tools
                     else f"Add '{self.plan.mod_folder}' to Memoria.ini FolderNames AND Priorities, same order "
                          f"(Memoria auto-detects it; a FolderNames-only hand edit is reverted by the launcher), "
                          f"relaunch once, then reach the chain via New Game / a gateway.")
            self._stream(argv, cwd=cwd, subject="Deploy campaign",
                         ok_headline=f"Deployed campaign '{self.plan.name}' → {self.plan.mod_folder}",
                         ok_next=reach)

    def _go_journey(self, path):
        # Repo checkout -> the dev tool (cwd=repo, reverts to tools/scroll_out); installed copy -> the package
        # CLI (ff9mapkit deploy-journey, reverts to a per-user cache). Same orchestration either way.
        def _jargv(**kw):
            return (jobs.deploy_journey_argv(self.repo, path, **kw) if self.has_tools
                    else jobs.deploy_journey_pkg_argv(path, **kw))
        jcwd = self.repo if self.has_tools else self.kit_cwd
        if self.rb_jour_preview.isChecked():           # dry-run: print the playbook, no game writes -> no confirm
            self._stream(_jargv(), cwd=jcwd,
                         subject="Journey deploy playbook (dry-run)",
                         ok_headline="Printed the journey deploy playbook (no game files touched)",
                         ok_next="Review the ordered steps above, then choose 'Deploy journey to game' to run them.")
            return
        if self.rb_jour_links.isChecked():
            if self._confirm("Re-apply cross-campaign links",
                             "Re-apply ONLY the cross-campaign link .eb rewrites?\n\nRun this after re-deploying "
                             "a campaign — deploy_campaign wholesale-replaces its folder, wiping the boundary "
                             "links. The campaigns must already be deployed."):
                self._stream(_jargv(apply_links=True), cwd=jcwd,
                             subject="Re-apply journey links",
                             ok_headline="Re-applied the cross-campaign links",
                             ok_next="Relaunch and playtest the campaign boundary.")
            return
        mode = self._journey_newgame_mode()
        single = self.cb_single_folder.isChecked()
        name = (self.manifest.hub.get("name") if self.manifest and self.manifest.hub else None) or Path(path).stem
        njourneys = len(self.manifest.journeys) if self.manifest else "?"
        route = {"hub": "New Game will land on the hub MENU (single-owner — replaces the current New-Game target).",
                 "entry": "New Game will land STRAIGHT in the opening field, no menu (single-owner — replaces the "
                          "current target; keeps the real opening FMV).",
                 "none": "New Game is left UNCHANGED — reach the hub via F6 → Warp."}[mode]
        layout = ("MERGED into ONE stacked mod folder (a single FolderNames entry)" if single
                  else "every campaign into its own stacked mod folder")
        folders_note = ("Reversible via one unified revert. You then add the ONE merged folder to Memoria.ini "
                        "(remove the journey's old per-campaign folders) and relaunch once." if single else
                        "Reversible via one unified revert. You must then STACK the folders in Memoria.ini and "
                        "relaunch once.")
        if self._confirm("Deploy journey",
                         f"Deploy journey '{name}' ({njourneys} journey(s)) in one shot — {layout}, the "
                         f"cross-campaign links, then the hub field?\n\n{route}\n\n{folders_note}"):
            reach = {"hub": "New Game → the hub menu", "entry": "New Game → straight into the opening",
                     "none": "F6 → Warp to the hub"}[mode]
            stackmsg = (f"Add the ONE merged folder to Memoria.ini [Mod] FolderNames AND Priorities, same order "
                        f"(drop the old per-campaign ones from BOTH), relaunch once, then {reach}. Playtest." if single else
                        f"Stack every campaign + hub folder in Memoria.ini [Mod] FolderNames AND Priorities, "
                        f"same order (the launcher rewrites FolderNames from Priorities), relaunch once, "
                        f"then {reach}. Playtest.")
            self._stream(_jargv(apply=True, newgame=mode, single_folder=single),
                         cwd=jcwd, subject="Deploy journey",
                         ok_headline=f"Deployed journey '{name}'" + (" (single folder)" if single else ""),
                         ok_next=stackmsg)

    def _go_battle(self, battle):
        if not self._require_tools("Deploy battle map"):
            return
        trig = self.trigger.text().strip()
        if trig and not trig.isdigit():
            return self._warn("Bad trigger field", "Trigger field must be a field id number (or blank).")
        tmsg = (f"\n\nAlso repoint field {trig}'s encounter at the minted scene." if trig else "")
        if self._confirm("Deploy battle map",
                         f"Build and deploy this battle map into:\n\n{self.mod_folder}\n\n"
                         "Replaces any prior deploy of the same map (reversible). A minted scene or a "
                         "BattlePatch line needs one relaunch." + tmsg):
            self._stream(jobs.deploy_battle_argv(self.repo, battle, trigger=trig or None), cwd=self.repo,
                         subject="Deploy battle map",
                         ok_headline=f"Deployed battle map → {self.mod_folder}",
                         ok_next="A minted scene / BattlePatch line needs one relaunch; a texture/FBX override "
                                 "loads on the next battle.")

    # ------------------------------------------------------------------ New Game entry (hub-less)
    def on_set_newgame(self):
        fid = self.newgame_id.text().strip()
        if not fid.isdigit():
            return self._warn("Bad field id", "Enter the numeric field id New Game should land on "
                                              "(e.g. a deployed slice's entry, 4100).")
        if self._confirm("Point New Game here",
                         f"Point New Game straight at field {fid}?\n\nThis CREATES the field-70 override from "
                         "stock (the opening FMV is preserved) and REPLACES the current New-Game landing "
                         "(single-owner), skipping any World Hub. Works even on a clean install / a fresh fork. "
                         "The field must already be deployed/registered; relaunch the game to test."):
            # repo -> the dev tool; installed -> ff9mapkit newgame (same from-stock override, revert to cache)
            if self.has_tools:
                argv, cwd = jobs.newgame_from_stock_argv(self.repo, fid), self.repo
            else:
                argv, cwd = jobs.newgame_from_stock_pkg_argv(fid), self.kit_cwd
            self._stream(argv, cwd=cwd, subject="Set New Game entry",
                         ok_headline=f"New Game now lands on field {fid}",
                         ok_next="Relaunch the game, then New Game. Undo with 'Revert New Game'.")

    def on_revert_newgame(self):
        argv = (jobs.revert_newgame_argv(self.repo) if self.has_tools else jobs.revert_newgame_pkg_argv())
        if argv is None or not Path(argv[-1]).exists():
            return self._info("Nothing to revert", "No New-Game change to undo yet.")
        cwd = self.repo if self.has_tools else self.kit_cwd
        if self._confirm("Revert New Game", "Restore the previous New-Game landing?"):
            self._stream(argv, cwd=cwd, subject="Revert New Game",
                         ok_headline="Reverted the New-Game retarget",
                         ok_next="Relaunch to load the restored New-Game landing.")

    # ------------------------------------------------------------------ Revert
    def on_revert(self):
        # campaign/journey reverts work for an installed copy too -- the package deploy writes them to a
        # per-user cache (jobs.revert_*_pkg_argv); battle + the test-slot field revert are dev-repo-only.
        if self.kind == "campaign":
            argv = jobs.revert_campaign_argv(self.repo) if self.has_tools else jobs.revert_campaign_pkg_argv()
            what = "campaign"
        elif self.kind == "journey":
            argv = (jobs.revert_journey_argv(self.repo) if self.has_tools else jobs.revert_journey_pkg_argv())
            what = ("journey links" if argv and Path(argv[-1]).name == "revert_journey_links.py" else "journey")
        else:
            if not self._require_tools("Revert"):
                return
            argv = jobs.revert_battle_argv(self.repo) if self.kind == "battle" else jobs.revert_field_argv(self.repo)
            what = "battle" if self.kind == "battle" else "test field"
        if argv is None or not Path(argv[-1]).exists():
            return self._info("Nothing to revert", f"No {what} deploy to undo yet.")
        cwd = self.repo if self.has_tools else self.kit_cwd
        if self._confirm(f"Revert {what}", f"Restore the game to before the last {what} deploy?"):
            self._stream(argv, cwd=cwd, subject=f"Revert {what}",
                         ok_headline=f"Reverted the last {what} deploy",
                         ok_next="Relaunch the game to load the restored state.")
