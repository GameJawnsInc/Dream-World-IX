"""The Build & Deploy document for the Workspace (Phase 6b) -- the tkinter ff9_build_gui, folded in.

Pick a project file; its kind is auto-detected (:func:`..editor.jobs.detect_kind`) and the matching target
panel shows: a single field (test slot / install to game / build to a folder), a whole campaign
(deploy / build-only), or a battle map (deploy + optional trigger field). **Check** validates in-process
(structured Problems); **Build / Deploy / Revert** stream through the shell's ``run_job`` into the Output
panel. Only this view is Qt -- detection + argv are jobs.py, verdicts are editor.feedback, and the deploys
are the same ``tools/deploy_*.py`` the CLI loop uses.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from ..editor import feedback as fb
from ..editor import jobs


class BuildDoc(QWidget):
    """Build / deploy a field, campaign, or battle map, as a Workspace document. ``run`` =
    ``shell.run_job`` (streams a subprocess to Output + posts a verdict); ``problems`` =
    ``shell._show_problems`` (the in-process Check verdict + problems list)."""

    def __init__(self, pal, repo_root, *, run, problems):
        super().__init__()
        self.pal = pal
        self.repo = Path(repo_root)
        self.kit = self.repo / "ff9mapkit"             # `-m ff9mapkit build` cwd (local pkg shadows)
        self._run = run
        self._problems = problems
        self.kind = "field"
        self.plan = None
        self.field_id = None
        self.field_name = None
        self.mod_folder, self.worktree_id = jobs.detect_deploy_target(self.repo)
        self.game_mod = jobs.detect_game_mod()
        self._build_ui()
        self._render_kind()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(QLabel("Project file:"))
        self.path = QLineEdit()
        self.path.setPlaceholderText("a .field.toml, campaign.toml, or battle.toml")
        self.path.textChanged.connect(self._on_path)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.browse)
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        v.addLayout(row)

        self.status = QLabel("Pick a field, campaign, or battle file.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(f"color:{self.pal['muted']};")
        v.addWidget(self.status)

        v.addWidget(self._field_box())
        v.addWidget(self._campaign_box())
        v.addWidget(self._battle_box())

        btns = QHBoxLayout()
        self.chk = QPushButton("Check logic")
        self.chk.clicked.connect(self.on_check)
        self.go = QPushButton("Build / Deploy")
        self.go.clicked.connect(self.on_go)
        self.rev = QPushButton("Revert test deploy")
        self.rev.clicked.connect(self.on_revert)
        btns.addWidget(self.chk)
        btns.addWidget(self.go)
        btns.addWidget(self.rev)
        btns.addStretch(1)
        v.addLayout(btns)
        v.addStretch(1)

    def _field_box(self):
        box = QGroupBox("Build to (field)")
        gv = QVBoxLayout(box)
        self.tg = QButtonGroup(self)
        tid = self.worktree_id or 4003
        self.rb_test = QRadioButton(f"Test slot {tid} — quick + reversible; play via F6 → Warp"
                                    + ("  (or New Game → hut door)" if tid == 4003 else ""))
        self.rb_test.setChecked(True)
        self.rb_game = QRadioButton(f"Install to game (shipping mod folder): {self.game_mod}"
                                    if self.game_mod else "Install to game — (game install not found)")
        if not self.game_mod:
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
        gv.addWidget(self.rb_test)
        gv.addWidget(self.rb_game)
        gv.addLayout(of)
        self.dest = QLabel("")
        self.dest.setWordWrap(True)
        self.dest.setStyleSheet(f"color:{self.pal['accent']};")
        gv.addWidget(self.dest)
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
        self.wire_newgame = QCheckBox("Wire New Game entry (experimental — off = reach the chain via F6 → Warp)")
        cv.addWidget(self.rb_camp_deploy)
        cv.addWidget(self.rb_camp_build)
        cv.addWidget(self.wire_newgame)
        self.campaign_box = box
        return box

    def _battle_box(self):
        box = QGroupBox("Deploy battle map")
        bv = QVBoxLayout(box)
        self.battle_dest = QLabel(f"This worktree's mod folder: {self.mod_folder}")
        self.battle_dest.setStyleSheet(f"color:{self.pal['muted']};")
        bv.addWidget(self.battle_dest)
        tf = QHBoxLayout()
        tf.addWidget(QLabel("Trigger field (optional):"))
        self.trigger = QLineEdit()
        self.trigger.setFixedWidth(90)
        tf.addWidget(self.trigger)
        self.trigger_hint = QLabel("repoint a deployed field's encounter at the minted scene (mint only).")
        self.trigger_hint.setWordWrap(True)
        self.trigger_hint.setStyleSheet(f"color:{self.pal['muted']};")
        tf.addWidget(self.trigger_hint, 1)
        bv.addLayout(tf)
        self.battle_box = box
        return box

    # ------------------------------------------------------------------ kind detection + rendering
    def set_target(self, path):
        """Point the doc at a project file (the shell calls this when a campaign/field opens, so Build &
        Deploy is pre-aimed at what you're working on)."""
        self.path.setText(str(path))

    def _on_path(self, _text=None):
        path = self.path.text().strip().strip('"')
        kind, plan = ("field", None)
        if path and Path(path).is_file():
            kind, plan = jobs.detect_kind(path)
        self.kind, self.plan = kind, plan
        if kind == "field":
            self.field_id, self.field_name = jobs.field_id_name(path) if path else (None, None)
        self._render_kind()

    def _render_kind(self):
        self.field_box.setVisible(self.kind == "field")
        self.campaign_box.setVisible(self.kind == "campaign")
        self.battle_box.setVisible(self.kind == "battle")
        if self.kind == "campaign" and self.plan is not None:
            ids = [m.new_id for m in self.plan.members]
            rng = f"{min(ids)}-{max(ids)}" if ids else "?"
            self.status.setText(f"Campaign '{self.plan.name}': {len(self.plan.members)} fields "
                                f"(ids {rng}) → {self.plan.mod_folder}")
            self.go.setText("Build / Deploy campaign")
            self.rev.setText("Revert campaign")
            self.rb_camp_deploy.setText(f"Deploy to game (reversible) → {self.plan.mod_folder}")
        elif self.kind == "battle":
            deployed = jobs.detect_deployed_fields(self.mod_folder)
            avail = ("deployed: " + ", ".join(f"{i} ({n})" for i, n in deployed) + " — ") if deployed \
                else "no fields deployed here yet — "
            self.trigger_hint.setText(avail + "repoint a deployed field's encounter at the minted scene "
                                              "so you can fight it now (mint only; blank otherwise).")
            self.status.setText(f"Battle map: {Path(self.path.text().strip()).name} → {self.mod_folder}")
            self.go.setText("Build / Deploy battle")
            self.rev.setText("Revert battle")
        else:
            self.go.setText("Build / Deploy")
            self.rev.setText("Revert test deploy")
            p = self.path.text().strip()
            if p and self.field_id is not None:
                self.status.setText(f"Field: {self.field_name or Path(p).stem} (its own id: {self.field_id})"
                                    f" — {Path(p).name}")
            elif p:
                self.status.setText(f"Field project: {Path(p).name}")
            else:
                self.status.setText("Pick a field, campaign, or battle file.")
            self._update_dest()

    def _update_dest(self, *_):
        if self.kind != "field":
            return
        tid = self.worktree_id or 4003
        own = self.field_id if self.field_id is not None else "?"
        if self.rb_test.isChecked():
            msg = (f"→ deploys to field {tid} in {self.mod_folder} (this worktree's test slot; reversible). "
                   f"Your field's own id ({own}) is overridden — reach it via F6 → Warp to {tid}.")
        elif self.rb_game.isChecked():
            where = self.game_mod or "(game install not found)"
            msg = f"→ installs at field {own} (the field's OWN id) in {where} — overwrites any field {own} there."
        else:
            folder = self.other.text().strip() or "(pick a folder)"
            msg = f"→ builds field {own} into {folder} — no game change."
        self.dest.setText(msg)

    # ------------------------------------------------------------------ pickers
    def browse(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Pick a field.toml, campaign.toml, or battle.toml", self.path.text().strip(),
            "Field / campaign / battle (*.toml);;All files (*)")
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

    def _picked(self):
        f = self.path.text().strip().strip('"')
        if not f or not Path(f).is_file():
            self._warn("No file", "Pick a .field.toml, campaign.toml, or battle.toml first.")
            return None
        return f

    def _busy(self, b):
        for w in (self.chk, self.go, self.rev):
            w.setEnabled(not b)

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
        elif self.kind == "battle":
            self._go_battle(f)
        else:
            self._go_field(f)

    def _go_field(self, field):
        if self.rb_test.isChecked():
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
                self._stream(jobs.build_argv(field, str(self.game_mod)), cwd=self.kit,
                             subject="Install to game", ok_headline=f"Built into {self.game_mod}")
        else:
            out = self.other.text().strip()
            if not out:
                return self._warn("No folder", "Pick an output folder.")
            self._stream(jobs.build_argv(field, out), cwd=self.kit, subject="Build",
                         ok_headline=f"Built into {out}")

    def _go_campaign(self, path):
        if self.rb_camp_build.isChecked():
            self._stream(jobs.build_campaign_argv(path), cwd=self.kit, subject="Build campaign",
                         ok_headline=f"Built campaign {self.plan.name}")
            return
        wire = self.wire_newgame.isChecked()
        route = ("It also wires New Game to enter the chain (experimental)." if wire
                 else "Reach each screen in-game via F6 → Warp.")
        if self._confirm("Deploy campaign",
                         f"Reversibly install campaign '{self.plan.name}' ({len(self.plan.members)} fields) "
                         f"into:\n\n{self.plan.mod_folder}\n\n{route}"):
            ids = [m.new_id for m in self.plan.members]
            entry = self.plan.members[0].new_id if self.plan.members else (min(ids) if ids else "?")
            self._stream(jobs.deploy_campaign_argv(self.repo, path, wire_newgame=wire), cwd=self.repo,
                         subject="Deploy campaign",
                         ok_headline=f"Deployed campaign '{self.plan.name}' → {self.plan.mod_folder}",
                         ok_next=f"Relaunch once (new DictionaryPatch), then F6 → Warp → {entry} to walk the chain.")

    def _go_battle(self, battle):
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

    # ------------------------------------------------------------------ Revert
    def on_revert(self):
        if self.kind == "battle":
            argv, what = jobs.revert_battle_argv(self.repo), "battle"
        elif self.kind == "campaign":
            argv, what = jobs.revert_campaign_argv(self.repo), "campaign"
        else:
            argv, what = jobs.revert_field_argv(self.repo), "test field"
        if argv is None or not Path(argv[-1]).exists():
            return self._info("Nothing to revert", f"No {what} deploy to undo yet.")
        if self._confirm(f"Revert {what}", f"Restore the game to before the last {what} deploy?"):
            self._stream(argv, cwd=self.repo, subject=f"Revert {what}",
                         ok_headline=f"Reverted the last {what} deploy",
                         ok_next="Relaunch the game to load the restored state.")
