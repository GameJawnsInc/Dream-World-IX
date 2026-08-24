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

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QRadioButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from . import widgets
from .. import prefs
from ..editor import feedback as fb
from ..editor import jobs


class BuildDoc(QWidget):
    """Build / deploy a field, campaign, journey, or battle map, as a Workspace document. ``run`` =
    ``shell.run_job`` (streams a subprocess to Output + posts a verdict); ``problems`` =
    ``shell._show_problems`` (the in-process Check verdict + problems list)."""

    def __init__(self, pal, repo_root, *, run, problems, on_coop=None):
        super().__init__()
        self.pal = pal
        self._on_coop = on_coop        # shell nav: switch to the Co-op tab (a quiet header cross-link)
        # Resolve the DEV repo: a repo launch passes its own root; an INSTALLED launch passes the venv dir,
        # but can still light up dev mode if $FF9_REPO (or the cwd) points at a checkout -> resolve_dev_repo.
        self.repo = jobs.resolve_dev_repo(repo_root)
        self.kit = self.repo / "ff9mapkit"             # `-m ff9mapkit build` cwd (local pkg shadows)
        self.kit_cwd = self.kit if self.kit.is_dir() else None   # None -> run_job falls back to KIT (always valid)
        # A repo checkout has the deploy scripts at <repo>/tools/; an installed copy (pip/uv/.exe) does NOT,
        # so the test-slot DEPLOY + the debug-menu loop are unavailable there. `build` + campaign/journey/New-Game
        # deploy work either way (the latter via the package CLI).
        self.has_tools = jobs.has_deploy_tools(self.repo)
        self._suppress_dest_persist = False             # True while a PROGRAMMATIC dest pick runs (restore /
        #                                                 legality fallback) -- only a user click is a pref
        self._run = run
        self._problems = problems
        self.kind = "field"
        self.plan = None                               # the campaign plan when kind == "campaign"
        self.manifest = None                           # the journey manifest when kind == "journey"
        self.field_id = None
        self.field_name = None
        self.inplace_target = None                      # {donor,name,text_block,is_forest} for a verbatim fork of a real field
        self._inplace_available = False                 # in-place radio is live (a fork of a real field + dev tools)
        self._inplace_autoselected_for = None            # donor id we last auto-checked In-place FOR (see _sync_inplace)
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
        v = widgets.page_column(inner)                  # the centred 860 reading column + the page rung +
        #                                                 the card rhythm. Was a bare QVBoxLayout, so these
        #                                                 cards stretched to the window (1102px at 1920).
        # THE CROWN, and the answer to the study's OQ#2 ("what is under the lamp on Build & Deploy?").
        # Nothing was: this screen opened straight into "Project file:" with no title at all, six cards
        # deep, and its card titles are 11px overlines -- SMALLER than the 13px body they label. The
        # screen was not flat, it was typographically inverted. The lamp had been aimed at an empty room.
        crown, _ = widgets.nameplate("", "Build & Deploy",
                                     "Turn a project file into a playable mod folder — check it, build "
                                     "it, put it in the game.")
        v.addWidget(crown)
        if self._on_coop is not None:                   # quiet cross-link: Co-op deploys the same mod (wayfinding)
            xlink = QLabel('Playing with a friend? → <a href="coop">Co-op</a>')
            xlink.setObjectName("headerXlink")              # carries a :focus ring -- a keyboard Tab stop must show it
            xlink.setTextFormat(Qt.TextFormat.RichText)
            xlink.setProperty("role", "muted")
            xlink.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse
                                          | Qt.TextInteractionFlag.LinksAccessibleByKeyboard)  # a Tab stop, not mouse-only
            xlink.linkActivated.connect(lambda _=None: self._on_coop())
            v.addWidget(xlink)
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
        # Cross-tab beginner lever (ASK #12): the drawer's default open/shut tracks the mode -- Guided
        # collapses it (the routine deploy stays front-and-centre), Full opens every expert drawer inline.
        # A live flip re-defaults it via apply_guided() below. builddoc has no computed auto-expand
        # override, so the mode default always wins here. The mode is read from the workspace's live global
        # (forms_qt._GUIDED, which the shell keeps synced to prefs), NOT prefs.guided() -- so a standalone
        # BuildDoc in a test never inherits the developer's prefs file (THE DISEASE).
        from . import forms_qt
        adv = widgets.disclosure("Advanced — battle deploy · New Game entry (single-owner)",
                                 expanded=not forms_qt._GUIDED)
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
        self.pack_btn.setProperty("role", "quiet")     # the ladder's bottom rung -- see style.py
        self.pack_btn.setToolTip("Zip a BUILT mod folder into a shareable release — the last step of the "
                                 "funnel. Unzipping it next to FF9_Launcher.exe installs the mod.")
        self.pack_btn.clicked.connect(self.on_pack)
        btns.addWidget(self.chk)
        btns.addWidget(self.go)
        btns.addWidget(self.rev)
        # The stretch sits BETWEEN the build verbs and Package, not after all four -- it used to trail the
        # row, which packed four equally-filled buttons flush left with no entry point. Package is a
        # different job (ship a BUILT folder), so it belongs across the gap, quiet.
        btns.addStretch(1)
        btns.addWidget(self.pack_btn)
        v.addLayout(btns)
        v.addWidget(self._deployed_box())
        v.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self._refresh_deployed()               # populate the ledger on open (refresh() re-scans on tab-show)
        self._refresh_newgame_status()         # and the 'New Game currently points at ...' line

    def apply_guided(self, guided: bool):
        """Re-default the Advanced drawer when the cross-tab beginner mode flips (ASK #12): Full opens it,
        Guided collapses it. Called by the shell's ``_apply_guided`` on the live Preferences/Ctrl-K flip
        (and on the Cancel-revert path). The one computed auto-expand override -- a BATTLE target (whose
        Deploy-battle box lives inside this drawer, revealed in ``_update_dest``) -- keeps WINNING over the
        mode default (chair ruling), so a battle deploy's controls never vanish in Guided mode."""
        self._advanced.toggle_button.setChecked(getattr(self, "kind", None) == "battle" or not guided)

    def _field_box(self):
        box = widgets.section("Build to (field)")
        gv = box.content_layout
        self.tg = QButtonGroup(self)
        tid = self.worktree_id or 4003
        # In-place: only meaningful for a verbatim fork of a REAL field -> hidden until such a project loads
        # (set_field fills the label + shows it). Placed FIRST so it reads as the preferred route for a fork.
        self.rb_inplace = QRadioButton("In-place on the real field")
        self.rb_inplace.setVisible(False)
        self.tg.addButton(self.rb_inplace)
        self.rb_inplace.toggled.connect(self._update_dest)
        self.rb_test = QRadioButton(f"Test slot {tid}")
        self.rb_test.setChecked(self.has_tools)        # installed copy: no debug-menu dev engine -> default to Install to game
        # label = the folder NAME only; the full path lives in the tooltip. (An unwrappable radio label
        # carrying the whole install path forced the tab's minimum width past the pane -> h-scrolling.)
        # KEEP the ternary -- jobs.detect_game_mod() returns None and Path(None) raises TypeError.
        self.rb_game = QRadioButton(f"Install to game: {Path(self.game_mod).name}"
                                    if self.game_mod else "Install to game — (game install not found)")
        if self.game_mod:
            self.rb_game.setToolTip(str(self.game_mod))
        else:
            self.rb_game.setEnabled(False)
        # Own id, REVERSIBLE -- the combination the other three modes leave out (test slot = reversible but
        # overrides the id; install = the real id but a wholesale build with no revert script). Its caption
        # is filled by set_field, which knows the id. dev-repo only: it shells out to tools/deploy_field.py.
        self.rb_own = QRadioButton("Deploy at its own id")
        self.rb_own.setEnabled(self.has_tools)
        self.tg.addButton(self.rb_own)
        self.rb_own.toggled.connect(self._update_dest)
        self.rb_own.toggled.connect(lambda ch: self._persist_dest("own", ch))
        of = QHBoxLayout()
        self.rb_other = QRadioButton("Build only — to a folder:")
        self.other = QLineEdit()
        self.other.setAccessibleName("Build output folder")   # its label is the RADIO, not a QLabel
        self.other.setProperty("mono", True)                  # a path is a machine token, not prose
        ob = QPushButton("Browse…")
        ob.clicked.connect(self.browse_other)
        of.addWidget(self.rb_other)
        of.addWidget(self.other, 1)
        of.addWidget(ob)
        for rb in (self.rb_test, self.rb_game, self.rb_other):
            self.tg.addButton(rb)
            rb.toggled.connect(self._update_dest)
        # Persist a USER click on any of the four persistable modes (the squeeze law: a checked radio the
        # user toggled is a preference; a programmatic pick under _suppress_dest_persist is not).
        self.rb_test.toggled.connect(lambda ch: self._persist_dest("test", ch))
        self.rb_game.toggled.connect(lambda ch: self._persist_dest("game", ch))
        self.rb_other.toggled.connect(lambda ch: self._persist_dest("other", ch))
        self.other.textChanged.connect(self._update_dest)
        gv.addWidget(self.rb_inplace)                 # its caption is filled by set_field (donor-dependent)
        widgets.option(self.rb_test,
                       "Quick and reversible. Your field's own id is overridden — play it with ~ → Warp"
                       + (", or New Game → the hut door." if tid == 4003 else "."), gv)
        widgets.option(self.rb_own,
                       "Reversible, at the id your field declares. Other fields in the folder keep their "
                       "registrations, and this writes an undo you can run from Revert.", gv)
        widgets.option(self.rb_game,
                       "Installs at the field's OWN id, into your shipping mod folder. Overwrites whatever "
                       "is there — but the folder is backed up first, so Revert can undo it.", gv)
        # "Build only — to a folder:" keeps its sentence: it is a FIELD LABEL for the adjacent QLineEdit,
        # not prose. Cutting it orphans the input.
        gv.addLayout(of)
        # The consequence caption its three siblings get from option(); option() can't run here because
        # rb_other already lives in `of` (its radio is the line edit's field label), so mirror option's body.
        _other_cap = "Compiles the field into a plain folder — nothing is deployed to the game."
        oc = widgets.Prose(_other_cap, widgets.CAPTION_W, base="caption")
        oc.setProperty("role", "caption")
        oc.setContentsMargins(widgets.OPT_INDENT, 0, 0, 6)
        gv.addWidget(oc)
        self.rb_other.setAccessibleDescription(_other_cap)
        self.rb_other.description_label = oc
        # WAS role="accent" -- a ~140-char sentence in accent blue, the loudest thing on the card and the
        # least important. style.py documents that role as "an actionable VALUE (e.g. a deploy target)", and
        # measured, accent-as-text is sub-AA in 6 of 7 palettes (NORD 2.44:1 on surface_2). It is now a
        # short muted value line; the per-option captions above carry the explanation, and the rev tooltips
        # keep the detail. Every destination is reversible now (even Install-to-game snapshots first), so no
        # branch is a "danger" diagnostic -- the value line is uniformly muted.
        self.dest = QLabel("")
        self.dest.setWordWrap(True)
        self.dest.setProperty("role", "muted")
        self.dest.setProperty("mono", True)                   # it is all ids, folders and paths
        gv.addWidget(self.dest)
        if not self.has_tools:                         # installed: no test-slot/~ -> default to Install to game / Build only
            self.rb_test.setEnabled(False)
            self.rb_test.setText(self.rb_test.text() + "   (dev repo only)")
            self.rb_test.setToolTip("The test slot + ~ reload loop need a source checkout. Set the FF9_REPO "
                                    "environment variable to your Dream World IX repo (or launch it from there), "
                                    "then reopen — this lights up.")
            # installed default -- a forced fallback, not a user pick, so don't persist it as a preference
            self._set_dest_checked(self.rb_game if self.game_mod else self.rb_other)
        self.field_box = box
        return box

    def _campaign_box(self):
        box = widgets.section("Deploy campaign")
        cv = box.content_layout
        self.cg = QButtonGroup(self)
        self.rb_camp_deploy = QRadioButton("Deploy to game (reversible)")
        self.rb_camp_deploy.setChecked(True)
        self.rb_camp_build = QRadioButton("Build only — compile every member to the campaign's dist/")
        self.cg.addButton(self.rb_camp_deploy)
        self.cg.addButton(self.rb_camp_build)
        # THE THIRD LAW: a check/radio label is a NAME (widgets.option). This was a sentence, and a
        # QCheckBox does not word-wrap -- its minimumSizeHint IS the whole string, so it pins its card open.
        self.wire_newgame = QCheckBox("Wire New Game entry (experimental)")
        cv.addWidget(self.rb_camp_deploy)
        cv.addWidget(self.rb_camp_build)
        widgets.option(self.wire_newgame,
                       "Off = reach the chain via a gateway, or ~ → Warp on a dev build.", cv)
        self.campaign_box = box
        return box

    def _journey_box(self):
        box = widgets.section("Deploy journey")
        jv = box.content_layout
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
        # THE THIRD LAW: a check/radio label is a NAME (widgets.option) -- this was a sentence, and a
        # QCheckBox does not word-wrap, so its minimumSizeHint pinned the card open at the full string.
        self.cb_single_folder = QCheckBox("Single mod folder")
        self.cb_single_folder.setToolTip("Cleaner one-folder install. Trade-off: re-deploying re-merges the "
                                         "whole journey — you lose cheap per-campaign re-deploy.")
        widgets.option(self.cb_single_folder,
                       "Merge the whole journey into ONE FolderNames entry, instead of one folder "
                       "per campaign.", jv)
        # New-Game landing: meaningful only for the one-shot deploy (single-owner) -> disabled otherwise
        self.ng_group = widgets.section("New Game landing (one-shot deploy — single-owner)")
        ngv = self.ng_group.content_layout
        self.ngg = QButtonGroup(self)
        self.rb_ng_none = QRadioButton("Don't wire New Game — reach the hub via ~ → Warp")
        self.rb_ng_none.setChecked(True)
        self.rb_ng_hub = QRadioButton("Wire New Game → the hub menu (pick the journey at Mognet; seamless)")
        self.rb_ng_entry = QRadioButton("Wire New Game → straight into the opening (no menu; keeps the real FMV)")
        self.rb_ng_entry.setToolTip("Single-journey arc only — a multi-journey hub has no single opening to land in.")
        for rb in (self.rb_ng_none, self.rb_ng_hub, self.rb_ng_entry):
            self.ngg.addButton(rb)
            ngv.addWidget(rb)
        self.ng_group.setEnabled(False)
        jv.addWidget(self.ng_group)
        self.journey_hint = widgets.caption("")
        jv.addWidget(self.journey_hint)
        self.journey_box = box
        return box

    def _newgame_box(self):
        # always-visible: point New Game straight at a deployed field id (the hub-less single destination).
        box = widgets.section("New Game entry  (skip the hub — land straight on a field)")
        gv = box.content_layout
        row = QHBoxLayout()
        row.addWidget(QLabel("Field id:"))
        self.newgame_id = QLineEdit()
        self.newgame_id.setProperty("mono", True)   # a field id is a machine token
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
        hint = widgets.caption("Single-owner: CREATES the field-70 override from stock (opening FMV preserved) and "   # de-emphasise the jargon paragraph (smaller, quieter)
                               "replaces the current New-Game landing (skips any World Hub) — works even on a clean "
                               "install or a fresh region fork. The field must already be DEPLOYED/registered. Relaunch "
                               "to test.")
        gv.addWidget(hint)
        # A persistent read of where New Game currently lands -- so a wholesale campaign/journey deploy's
        # 'casualty' has a name here, not just in the deploy confirm. Refreshed on every tab-show + after a
        # set/revert (jobs.current_newgame_target reads the deployed field-70 override).
        self.newgame_status = QLabel("")
        self.newgame_status.setWordWrap(True)
        self.newgame_status.setProperty("role", "muted")
        gv.addWidget(self.newgame_status)
        self.newgame_box = box
        return box

    def _refresh_newgame_status(self):
        """Show where New Game currently points (the deployed FF9CustomMap field-70 override), or that it
        uses the stock opening. Silently blank when no install is found."""
        if not hasattr(self, "newgame_status"):
            return
        tgt = jobs.current_newgame_target(self.game_mod) if self.game_mod else None
        if tgt is not None:
            self.newgame_status.setText(f"New Game currently points at field {tgt}.")
        else:
            self.newgame_status.setText("New Game currently uses the stock opening (no custom entry deployed).")

    def _battle_box(self):
        box = widgets.section("Deploy battle map")
        bv = box.content_layout
        self.battle_dest = QLabel(f"Test mod folder: {self.mod_folder}")
        self.battle_dest.setProperty("role", "muted")
        if not self.has_tools:                         # installed: deploy_battle needs a source checkout -> mark it, like rb_test
            self.battle_dest.setText(self.battle_dest.text() + "   (dev repo only)")
            self.battle_dest.setToolTip("Battle deploy shells out to tools/deploy_battle.py, which needs a "
                                        "source checkout. Set the FF9_REPO environment variable to your Dream "
                                        "World IX repo (or launch it from there), then reopen.")
        bv.addWidget(self.battle_dest)
        tf = QHBoxLayout()
        tf.addWidget(QLabel("Trigger field (optional):"))
        self.trigger = QLineEdit()
        self.trigger.setProperty("mono", True)   # a field id is a machine token
        self.trigger.setFixedWidth(90)
        tf.addWidget(self.trigger)
        self.trigger_hint = widgets.caption("repoint a deployed field's encounter at the minted scene (only for a "
                                            "from-scratch new scene, not a reskin/fork).")
        tf.addWidget(self.trigger_hint, 1)
        bv.addLayout(tf)
        self.battle_box = box
        return box

    def _deployed_box(self):
        """The read side of the reversible test mod folder: every field registered there, paired with the
        per-id undo script deploy_field wrote for it, plus the folder-wide campaign / New-Game reverts.
        The single Revert button reaches only the LATEST deploy; these accumulate, so this lists them all
        with a confirm-first per-entry revert. Styled on modelsdoc._deployed_box (the proven read-inventory
        widget language)."""
        box = widgets.section("Deployed here")
        v = box.content_layout
        self.dep_list = QListWidget()
        self.dep_list.setAccessibleName("Fields deployed in this mod folder")   # no visible label to buddy
        self.dep_list.setMaximumHeight(170)
        v.addWidget(self.dep_list)
        row = QHBoxLayout()
        self.dep_refresh = QPushButton("Refresh")
        self.dep_refresh.clicked.connect(self._refresh_deployed)
        row.addWidget(self.dep_refresh)
        self.dep_revert = QPushButton("Revert selected…")
        self.dep_revert.setToolTip("Run this deploy's own undo script, restoring the field's previous "
                                   "contents in the mod folder.")
        self.dep_revert.clicked.connect(self.on_deployed_revert)
        row.addWidget(self.dep_revert)
        row.addStretch(1)
        v.addLayout(row)
        self.dep_hint = QLabel("")
        self.dep_hint.setWordWrap(True)
        self.dep_hint.setProperty("role", "muted")
        v.addWidget(self.dep_hint)
        self.deployed_box = box
        return box

    def _dep_row_label(self, r):
        base = f"field {r['id']} ({r['name']})" if r["kind"] == "field" else r["name"]
        return base if r["script"] else base + "   · no undo script"

    def _refresh_deployed(self):
        """Re-scan the reversible test mod folder's DictionaryPatch + tools/scroll_out and repaint the
        ledger. Read-only informational rows (a registration with no revert script) are non-selectable so
        Revert can only target an entry it can actually undo."""
        if not hasattr(self, "dep_list"):
            return
        dp = None
        try:
            from .. import config
            dp = config.find_game_path() / self.mod_folder / "DictionaryPatch.txt"
        except Exception:                                # noqa: BLE001 -- no install found -> no field rows
            dp = None
        scroll = jobs.scroll_out_dir(self.repo) if self.has_tools else None
        rows = jobs.scan_deployed_reverts(dp, scroll)
        self.dep_list.clear()
        for r in rows:
            it = QListWidgetItem(self._dep_row_label(r))
            it.setData(Qt.ItemDataRole.UserRole, r)
            if not r["script"]:                          # informational only -> not selectable / revertable
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.dep_list.addItem(it)
        n_undo = sum(1 for r in rows if r["script"])
        # THREE situations, three messages. The mixed case's "select one and Revert selected" is a DEAD
        # instruction when nothing is revertable -- it pointed at a button this same method disables, and
        # a worktree launch used to land every row in that state (empty scroll_out; caught by gui_snap
        # deployed:orphaned). Say what is true instead of repeating the happy path.
        if not rows:
            self.dep_hint.setText(f"Nothing registered in {self.mod_folder} yet.")
        elif n_undo == 0:
            self.dep_hint.setText(f"{len(rows)} deployed here · none has an undo script, so nothing here "
                                  "can be reverted from this tab.")
        else:
            self.dep_hint.setText(f"{len(rows)} deployed here · {n_undo} with an undo script — select one "
                                  "and Revert selected to undo it.")
        self.dep_revert.setEnabled(n_undo > 0)

    def on_deployed_revert(self):
        it = self.dep_list.currentItem()
        if it is None:
            return self._warn("Nothing selected", "Pick a deployed entry with an undo script first.")
        r = it.data(Qt.ItemDataRole.UserRole)
        if not r or not r.get("script"):
            return self._warn("No undo script", "This entry has no revert script on disk — it's "
                                                "informational only.")
        what = f"field {r['id']}" if r["kind"] == "field" else r["name"]
        if self._confirm(f"Revert {what}",
                         f"Run the undo script for {what}?\n\nThis restores the previous contents in "
                         f"{self.mod_folder} (reversible deploys only)."):
            self._busy(True)
            if not self._run([sys.executable, r["script"]], cwd=self.repo, subject=f"Revert {what}",
                             ok_headline=f"Reverted {what}",
                             ok_next="Relaunch the game (or ~ → Reload field) to load the restored state.",
                             on_finished=lambda _c: (self._busy(False), self._refresh_deployed())):
                self._busy(False)                        # a job was already running; nothing started

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

    def refresh(self):
        """Re-read the current target file from disk (field id/name, campaign plan, journey manifest, ...).
        ``self.path`` only re-detects on a TEXT change, so an edit-and-Save on the SAME path (e.g. bumping a
        field's own id in the Author form) left this tab showing stale bytes until the file was re-Browse'd.
        The shell calls this when the Build & Deploy tab becomes current -- same fix as story_state's
        `_refresh_flag_names` on tab-show, so the view is current no matter the open/edit order."""
        self._on_path()
        self._refresh_deployed()               # the 'Deployed here' ledger is a live inventory -> re-scan on show
        self._refresh_newgame_status()         # so is 'New Game currently points at ...'

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
            self._sync_own_id()
            self._sync_inplace()
            self._apply_saved_dest()
            self._update_dest()

    def _sync_own_id(self):
        """Label the own-id radio with the id the loaded field declares, and keep it selectable only when
        that id is actually known -- an unreadable/absent id would deploy nowhere meaningful. Never changes
        the selection: unlike In-place this is not a mode the kit should pick for you (installing at the
        real id is a deliberate act), so it only falls BACK when it is checked and becomes unusable."""
        known = self.field_id is not None and self.has_tools
        self.rb_own.setText(f"Deploy at its own id {self.field_id} — reversible" if known
                            else "Deploy at its own id" + ("" if self.has_tools else "   (dev repo only)"))
        self.rb_own.setEnabled(known)
        if not known and self.rb_own.isChecked():        # a forced fallback, not a user pick -> don't persist
            self._set_dest_checked(self.rb_test if self.has_tools
                                   else self.rb_game if self.game_mod else self.rb_other)

    def _sync_inplace(self):
        """Show/label the In-place radio for a verbatim fork of a real field, and DEFAULT to it the FIRST time
        a given donor is seen (the usual intent for such a fork -- and mandatory for a Chocobo forest, whose
        HUD is hardcoded on the donor id). Needs the dev test-slot tooling; on an installed copy it stays
        hidden (no reversible test folder).

        Only auto-CHECKS on a new donor (``_inplace_autoselected_for`` tracks the last one) -- this also runs
        from :meth:`refresh` on every Build & Deploy tab-show (so an id/name edit+Save is reflected live), and
        without the guard that re-render would silently stomp a deliberate "Install to game" pick back to
        In-place on every revisit, since the donor (and so `show`) doesn't change across such an edit."""
        t = self.inplace_target
        show = bool(t) and self.has_tools
        self._inplace_available = show                  # the logic gate (isVisible() is unreliable off-screen / off-tab)
        self.rb_inplace.setVisible(show)
        if not show:
            self._inplace_autoselected_for = None
            if self.rb_inplace.isChecked():            # a prior fork's default -> fall back to a live option
                self._set_dest_checked(self.rb_test if self.has_tools
                                       else self.rb_game if self.game_mod else self.rb_other)
            return
        forest = " (Chocobo forest — keeps the dig HUD)" if t["is_forest"] else ""
        self.rb_inplace.setText(f"In-place on field {t['donor']} — reversible; keeps the real field's "
                                f"id/name/HUD{forest}")
        self.rb_inplace.setToolTip(
            f"Deploys under the donor's own id {t['donor']} (text block {t['text_block']}) into "
            f"{self.mod_folder}, so the engine loads this in place of the real field. Reach it the normal "
            f"way, or ~ → Warp {t['donor']}. Reversible.")
        if self._inplace_autoselected_for != t["donor"]:      # the preferred route for a fork of a real field --
            self.rb_inplace.setChecked(True)                  # but only ONCE per donor, not on every re-render
            self._inplace_autoselected_for = t["donor"]

    def _update_dest(self, *_):
        if self.kind != "field":
            return
        tid = self.worktree_id or 4003
        own = self.field_id if self.field_id is not None else "?"
        # Each branch resolves to a short VALUE LINE (the option's caption above already explains the mode,
        # and the rev tooltip keeps the fine print) -- say each fact exactly once. There is no longer a
        # "danger" branch: Install-to-game became reversible this wave (it snapshots the whole mod folder
        # before the write), so every destination's value line is uniformly muted -- no state="warn".
        if self._inplace_available and self.rb_inplace.isChecked():
            t = self.inplace_target
            # KEEP "in place" + the donor id unsplit: test_builddoc_inplace.py:58 asserts on dest.text().
            msg = f"→ in place on field {t['donor']} in {self.mod_folder} · reversible"
            if t["is_forest"]:
                msg += " · keeps the Chocobo dig HUD"
            self.rev.setEnabled(True)              # the deploy writes a per-id revert script
            self.rev.setToolTip(f"Undo the last in-place deploy on field {t['donor']} (restores its previous "
                                "contents).")
        elif self.rb_test.isChecked():
            msg = f"→ field {tid} in {self.mod_folder} · reversible"
            self.rev.setEnabled(True)              # the test deploy writes a revert script
            self.rev.setToolTip("Undo the last test-slot deploy (restores the slot's previous contents).")
        elif self.rb_own.isChecked():
            msg = f"→ field {own} in {self.mod_folder} · reversible"
            self.rev.setEnabled(True)              # the deploy writes revert_deploy_<own id>.py
            self.rev.setToolTip(f"Undo the last deploy of field {own} (restores its previous contents).")
        elif self.rb_game.isChecked():
            where = self.game_mod or "(game install not found)"
            # Reversible now: Install-to-game snapshots the whole folder first (backup law, §2) and writes
            # revert_install.py. Still an overwrite in the shipping folder, so the value line names that.
            msg = f"→ field {own} in {where} · overwrites (backed up — Revert undoes it)"
            self.rev.setEnabled(True)
            self.rev.setToolTip(f"A direct game install overwrites field {own} in place. The whole mod "
                                "folder is backed up before the write, so Revert restores it.")
        else:
            folder = self.other.text().strip() or "(pick a folder)"
            msg = f"→ field {own} → {folder} · no game change"
            self.rev.setEnabled(False)             # building into a plain folder deploys nothing to revert
            self.rev.setToolTip("Builds into a plain folder — nothing was deployed to the game to revert.")
        self.dest.setText(msg)

    # ------------------------------------------------------------------ destination persistence
    # THE SQUEEZE LAW, applied to a radio: a value the user CLICKED is a real preference; a value COMPUTED
    # under duress (a legality fallback, the installed-copy default, the restore itself) is not. So the four
    # persistable modes persist only from a user toggle, and every programmatic pick runs through
    # _set_dest_checked (which suppresses the persist). In-place is excluded entirely -- it is donor-driven
    # and auto-selects, so remembering it would fight that auto-selection (prefs.set_deploy_dest drops it too).
    def _set_dest_checked(self, rb):
        """Select a destination radio WITHOUT persisting it -- for a programmatic pick (fallback / default /
        restore), which is not a user preference."""
        self._suppress_dest_persist = True
        try:
            rb.setChecked(True)
        finally:
            self._suppress_dest_persist = False

    def _persist_dest(self, mode, checked):
        """Remember the destination the user clicked (a checked radio, a real toggle -- not a suppressed
        programmatic pick)."""
        if checked and not self._suppress_dest_persist:
            prefs.set_deploy_dest(mode)

    def _apply_saved_dest(self):
        """Restore the remembered destination for a loaded field -- but only when its radio is legal and
        In-place is not auto-selecting (a verbatim fork's donor-driven route wins). Falls back legally by
        doing nothing (leaving the has_tools default / a fallback in place) when the saved mode is unusable,
        e.g. an installed copy where the test slot is disabled."""
        if self._inplace_available and self.rb_inplace.isChecked():
            return                                       # don't override the fork's auto-selected In-place
        mode = prefs.deploy_dest()
        if mode is None:
            return
        rb = {"test": self.rb_test, "own": self.rb_own,
              "game": self.rb_game, "other": self.rb_other}[mode]
        if rb.isEnabled() and not rb.isChecked():
            self._set_dest_checked(rb)                   # programmatic: restoring is not a fresh user choice

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

    def _confirm_reversible(self, title, text):
        """A REVERSIBLE deploy (the test slot / an in-place fork) skips the modal by default, so F9 is a
        true one-keystroke loop; ``prefs.confirm_reversible_deploys`` opts the confirm back IN. The no-undo
        Install-to-game and the wholesale campaign/journey deploys never route through here -- they keep
        their unconditional :meth:`_confirm`."""
        if not prefs.confirm_reversible_deploys():
            return True
        return self._confirm(title, text)

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
            f"'{what}' uses the development deploy loop (the repo's tools/ + the debug-menu dev engine), which an "
            "installed copy doesn't ship.\n\n"
            "Two options:\n"
            "  - Point this Workspace at your source checkout: set the FF9_REPO environment variable to your "
            "Dream World IX repo (or launch apps\\ff9_workspace.pyw from it), then reopen — the test slot + debug menu "
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
        for w in (self.chk, self.go, self.rev, self.pack_btn, self.set_ng, self.rev_ng,
                  self.dep_refresh, self.dep_revert):
            w.setEnabled(not b)

    def _revert_dirs(self):
        """(backups_dir, reverts_dir) for the Install-to-game snapshot -- the MAIN repo's ``backups/`` +
        ``tools/scroll_out/`` on a dev checkout, else the installed copy's per-user cache (Install-to-game
        works on both, so this can't assume repo tools).

        MAIN, not ``self.repo``: this snapshot IS the live install's only undo, and a Workspace launched
        from an agent worktree used to park it there, so cleaning the tree destroyed the backup while the
        game kept the install (project-ff9-worktree-parked-backups). Same rooting the deploy scripts use."""
        if self.has_tools:
            return jobs.install_backups_dir(self.repo), jobs.scroll_out_dir(self.repo)
        from .. import provision
        return provision.deploy_backups_dir(), provision.deploy_reverts_dir()

    def _snapshot_before_install(self) -> bool:
        """Back up the whole game mod folder before an Install-to-game write and wire its revert. Returns
        True when a revert script was written (Install-to-game becomes reversible), False when it could not
        be (so the caller states the honest truth instead of overclaiming)."""
        if not self.game_mod:                              # rb_game is disabled without an install; belt-and-braces
            return False
        backups_dir, reverts_dir = self._revert_dirs()
        return jobs.snapshot_mod_folder(self.game_mod, backups_dir, reverts_dir) is not None

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
        hint = widgets.caption("Zips a BUILT mod folder (DictionaryPatch.txt + StreamingAssets/…) so unzipping next "
                               "to FF9_Launcher.exe installs it. Build/Deploy first — pack takes the OUTPUT folder. "
                               "For a single-folder journey, pack the deployed <game>/<merged folder>.")
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
        widgets.fit_dialog(dlg, ch=84)                 # the mod-folder PATH is this form's whole subject
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

    def _stream(self, argv, *, cwd, subject, ok_headline, ok_next="", field_id=None, then=None):
        # field_id (a real/test/own field-deploy target) rides to run_job so the shell's post-deploy spine
        # can offer a one-click Copy-warp receipt; None on build/campaign/journey (no single warp id).
        # `then` (called on a code==0 finish) chains a follow-on job -- e.g. 'Deploy & re-wire' runs the
        # New-Game re-wire after a campaign deploy succeeds. run_job's proc is NotRunning by the time
        # on_finished fires, so starting the next job here is legal.
        self._busy(True)

        def _fin(code):
            self._busy(False)
            if then is not None and code == 0:
                then()
        if not self._run(argv, cwd=cwd, subject=subject, ok_headline=ok_headline, ok_next=ok_next,
                         field_id=field_id, on_finished=_fin):
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
            if self._confirm_reversible(f"Deploy in place on field {t['donor']}",
                             f"Build and deploy this fork IN PLACE on field {t['donor']} ({self.mod_folder})? "
                             f"The engine loads it instead of the real field (reversible).{hud}"):
                self._stream(jobs.deploy_field_inplace_argv(self.repo, field, t), cwd=self.repo,
                             subject=f"Deploy in place on field {t['donor']}",
                             ok_headline=f"Deployed in place on field {t['donor']} ({self.mod_folder})",
                             ok_next=f"In-game: reach it the normal way, or ~ → Warp {t['donor']}.",
                             field_id=t["donor"])
            return
        if self.rb_test.isChecked():
            if not self._require_tools("Deploy to test slot"):
                return
            tid = self.worktree_id or 4003
            reach = ("New Game → walk to the hut door (or ~ → Warp)" if tid == 4003
                     else f"~ → Warp to field {tid}")
            if self._confirm_reversible(f"Deploy to test field {tid}",
                             f"Build and deploy this field to the test slot {tid} ({self.mod_folder})? "
                             "It replaces whatever is there now (reversible)."):
                self._stream(jobs.deploy_field_argv(self.repo, field), cwd=self.repo,
                             subject=f"Deploy to test field {tid}",
                             ok_headline=f"Deployed to test field {tid} ({self.mod_folder})",
                             ok_next=f"In-game: {reach}.", field_id=tid)
        elif self.rb_own.isChecked():
            own = self.field_id
            nm = self.field_name or Path(field).stem
            self._stream(jobs.deploy_field_own_id_argv(self.repo, field, own, nm), cwd=self.repo,
                         subject=f"Deploy to field {own}",
                         ok_headline=f"Deployed field {own} ({self.mod_folder})",
                         ok_next=f"In-game: ~ → Warp to field {own}. Undo this deploy any time.", field_id=own)
        elif self.rb_game.isChecked():
            if self._confirm("Install to game",
                             f"Build this field into the game mod folder?\n\n{self.game_mod}\n\n"
                             "Writes the field at its real id, replacing any field already installed "
                             "there under that id. Other fields in the folder stay registered.\n\n"
                             "The folder is backed up first, so you can undo this with Revert."):
                # HONOR THE BACKUP LAW (§2). Install-to-game is the one GUI write into the real shipping
                # folder; snapshot the WHOLE folder BEFORE the build and wire the install revert. (The build
                # rewrites the folder's DictionaryPatch + patches wholesale, so a per-id write-set isn't
                # reliable here -> whole-folder, correctness over economy -- jobs.snapshot_mod_folder.)
                snap_ok = self._snapshot_before_install()
                # preserve_existing: a build writes the folder's WHOLE DictionaryPatch, so without it
                # every other field in a shipping folder is silently unregistered -- their files stay,
                # and the engine black-screens on them (observed 2026-07-18).
                self._stream(jobs.build_argv(field, str(self.game_mod), preserve_existing=True),
                             cwd=self.kit_cwd, subject="Install to game",
                             ok_headline=f"Built into {self.game_mod}",
                             ok_next=("Undo this deploy any time (the folder was backed up first)." if snap_ok else
                                      "Note: the pre-install backup could not be written — Revert is "
                                      "unavailable for this install. Restore from your own backup if needed."),
                             then=self._refresh_deployed)
        else:
            out = self.other.text().strip()
            if not out:
                return self._warn("No folder", "Pick an output folder.")
            self._stream(jobs.build_argv(field, out), cwd=self.kit_cwd, subject="Build",
                         ok_headline=f"Built into {out}")

    def _current_newgame_target_for(self, mod_folder_name):
        """The field id New Game currently lands on for a given mod-folder NAME, resolved against the
        detected game install -- or ``None`` when there is no install, no override, or it can't be parsed."""
        if not self.game_mod:
            return None
        try:
            return jobs.current_newgame_target(Path(self.game_mod).parent / mod_folder_name)
        except Exception:                              # noqa: BLE001 -- best-effort read; never blocks a deploy
            return None

    def _confirm_campaign_deploy(self, casualty, route):
        """The named 3-button confirm shown when a wholesale campaign deploy would WIPE a live New-Game
        entry: 'Deploy & re-wire' / 'Deploy anyway' / 'Cancel'. Returns ``"rewire"`` / ``"anyway"`` /
        ``"cancel"``. A QDialog (not a QMessageBox) so it wears the app's dialog grammar and is grab-testable
        by tools/gui_snap.py (dlg:campaign-newgame)."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Deploy campaign")
        v = QVBoxLayout(dlg)
        head = QLabel(f"Deploy campaign ‘{self.plan.name}’")
        head.setProperty("role", "head")
        v.addWidget(head)
        body = widgets.Prose(
            f"Reversibly installs {len(self.plan.members)} fields into {self.plan.mod_folder}. {route}\n\n"
            f"Heads up: a wholesale campaign deploy replaces that folder, which wipes the New Game entry — "
            f"it currently points at field {casualty}. Re-wire it back after the deploy, or deploy and "
            f"leave New Game unwired.", widgets.CAPTION_W)
        v.addWidget(body)
        result = {"choice": "cancel"}

        def _pick(choice):
            result["choice"] = choice
            dlg.accept()
        rewire = QPushButton("Deploy && re-wire")      # && -> a literal '&' (a single & is a Qt mnemonic)
        anyway = QPushButton("Deploy anyway")
        cancel = QPushButton("Cancel")
        rewire.clicked.connect(lambda: _pick("rewire"))
        anyway.clicked.connect(lambda: _pick("anyway"))
        cancel.clicked.connect(lambda: _pick("cancel"))
        rewire.setDefault(True)                         # the recommended path; quiet/default tier (no accent)
        row = QHBoxLayout()
        row.addWidget(cancel)
        row.addStretch(1)
        row.addWidget(anyway)
        row.addWidget(rewire)
        v.addLayout(row)
        widgets.fit_dialog(dlg, ch=74)
        dlg.exec()
        return result["choice"]

    def _rewire_newgame_after_deploy(self, target):
        """The 'Deploy & re-wire' follow-on: re-point New Game back at ``target`` (the id the wholesale
        deploy just wiped) via the from-stock wiring. Runs after the deploy job finishes cleanly.

        The re-wire MUST target the SAME folder the casualty was read from (``self.plan.mod_folder``, via
        :meth:`_current_newgame_target_for`) -- otherwise a campaign whose mod_folder is not FF9CustomMap
        gets its override wiped in that folder and restored in FF9CustomMap (both argv builders default the
        folder, so the fix is to pass it through)."""
        if target is None:
            return
        mod_folder = self.plan.mod_folder
        if self.has_tools:
            argv, cwd = jobs.newgame_from_stock_argv(self.repo, target, mod_folder=mod_folder), self.repo
        else:
            argv, cwd = jobs.newgame_from_stock_pkg_argv(target, mod_folder=mod_folder), self.kit_cwd
        self._stream(argv, cwd=cwd, subject="Re-wire New Game",
                     ok_headline=f"Re-wired New Game to field {target}",
                     ok_next="Relaunch the game, then New Game. Undo with 'Revert New Game'.",
                     then=self._refresh_newgame_status)

    def _go_campaign(self, path):
        if self.rb_camp_build.isChecked():
            self._stream(jobs.build_campaign_argv(path), cwd=self.kit_cwd, subject="Build campaign",
                         ok_headline=f"Built campaign {self.plan.name}")
            return
        wire = self.wire_newgame.isChecked()
        route = ("It also wires New Game to enter the chain (experimental)." if wire
                 else "Reach each screen in-game via ~ → Warp." if self.has_tools
                 else "Reach the chain via New Game (if wired) or a [[gateway]] from an early field.")
        # A wholesale campaign deploy REPLACES the mod folder, which WIPES the field-70 New-Game override.
        # When one is live, name the casualty in a 3-button dialog and offer to re-wire it after the deploy;
        # with none live there is nothing to warn about, so keep the plain reversible confirm.
        casualty = self._current_newgame_target_for(self.plan.mod_folder) if not wire else None
        rewire_after = False
        if casualty is not None:
            choice = self._confirm_campaign_deploy(casualty, route)
            if choice == "cancel":
                return
            rewire_after = (choice == "rewire")
        elif not self._confirm("Deploy campaign",
                               f"Reversibly install campaign '{self.plan.name}' ({len(self.plan.members)} "
                               f"fields) into:\n\n{self.plan.mod_folder}\n\n{route}"):
            return
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
        reach = (f"Relaunch once (new DictionaryPatch), then ~ → Warp → {entry} to walk the chain." if self.has_tools
                 else f"Add '{self.plan.mod_folder}' to Memoria.ini FolderNames AND Priorities, same order "
                      f"(Memoria auto-detects it; a FolderNames-only hand edit is reverted by the launcher), "
                      f"relaunch once, then reach the chain via New Game / a gateway.")
        # 'Deploy & re-wire' chains the New-Game re-wire after the deploy succeeds -- re-pointing New Game
        # back at the casualty id the wholesale replace wiped (the existing wire-from-stock path).
        then = (lambda: self._rewire_newgame_after_deploy(casualty)) if rewire_after else None
        self._stream(argv, cwd=cwd, subject="Deploy campaign",
                     ok_headline=f"Deployed campaign '{self.plan.name}' → {self.plan.mod_folder}",
                     ok_next=reach, then=then)

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
                 "none": "New Game is not wired to this journey — but a wholesale deploy replaces the mod "
                         "folder(s), so an existing custom New-Game entry living in one is wiped back to "
                         "stock. Reach the hub via ~ → Warp; re-wire New Game afterward if you had one."}[mode]
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
                     "none": "~ → Warp to the hub"}[mode]
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
                         ok_next="Relaunch the game, then New Game. Undo with 'Revert New Game'.",
                         then=self._refresh_newgame_status)

    def on_revert_newgame(self):
        argv = (jobs.revert_newgame_argv(self.repo) if self.has_tools else jobs.revert_newgame_pkg_argv())
        if argv is None or not Path(argv[-1]).exists():
            return self._info("Nothing to revert", "No New-Game change to undo yet.")
        cwd = self.repo if self.has_tools else self.kit_cwd
        if self._confirm("Revert New Game", "Restore the previous New-Game landing?"):
            self._stream(argv, cwd=cwd, subject="Revert New Game",
                         ok_headline="Reverted the New-Game retarget",
                         ok_next="Relaunch to load the restored New-Game landing.",
                         then=self._refresh_newgame_status)

    # ------------------------------------------------------------------ Revert
    def _revert_plan(self):
        """``(argv, what, needs_tools)`` for reverting the CURRENT destination -- PURE (no dialogs), so it
        is shared by :meth:`on_revert` (which prompts + streams) and :meth:`revert_available` (a silent
        predicate the shell reads to decide whether to offer an Undo). ``argv`` is ``None`` when no revert
        applies; ``needs_tools`` is True for the dev-repo-only reverts (battle + the test-slot/own-id field
        deploy), False for the ones that also run on an installed copy (campaign/journey/install, via the
        package-cache revert scripts)."""
        # campaign/journey/install reverts work for an installed copy too -- the package deploy writes them to
        # a per-user cache (jobs.revert_*_pkg_argv); battle + the test-slot/own-id field revert are dev-only.
        if self.kind == "campaign":
            argv = jobs.revert_campaign_argv(self.repo) if self.has_tools else jobs.revert_campaign_pkg_argv()
            return argv, "campaign", False
        if self.kind == "journey":
            argv = (jobs.revert_journey_argv(self.repo) if self.has_tools else jobs.revert_journey_pkg_argv())
            what = ("journey links" if argv and Path(argv[-1]).name == "revert_journey_links.py" else "journey")
            return argv, what, False
        if self.kind == "field" and self.rb_game.isChecked():
            argv = jobs.revert_install_argv(self.repo) if self.has_tools else jobs.revert_install_pkg_argv()
            return argv, "install", False
        if self.kind == "battle":
            return jobs.revert_battle_argv(self.repo), "battle", True
        # an own-id deploy has its OWN revert script; using the generic "latest" one there could undo a
        # different id's later deploy instead (jobs.revert_field_argv)
        fid = self.field_id if self.rb_own.isChecked() else None
        return jobs.revert_field_argv(self.repo, fid), (f"field {fid}" if fid is not None else "test field"), True

    def deploy_dest_key(self):
        """A hashable snapshot of the CURRENT deploy destination (kind + radio + id). The shell captures it
        at deploy time and compares it live, so moving the destination radio AFTER a deploy retires the
        spine's stale 'Undo this deploy' (which reverts the LIVE destination) instead of offering an undo for
        a destination the deploy never touched."""
        if self.kind != "field":
            return (self.kind,)
        if self._inplace_available and self.rb_inplace.isChecked():
            return ("inplace", self.inplace_target["donor"] if self.inplace_target else None)
        if self.rb_own.isChecked():
            return ("own", self.field_id)
        if self.rb_game.isChecked():
            return ("install",)
        return ("test",)

    def revert_available(self):
        """True when :meth:`on_revert` would find a revert script to run for the CURRENT destination (mirrors
        its argv-exists check, no dialogs). The shell reads this at deploy time so it never offers 'Undo this
        deploy' for a deploy that cannot be undone -- notably an install whose pre-install snapshot failed, so
        no revert script was written (its own receipt already says Revert is unavailable)."""
        try:
            argv, _what, needs_tools = self._revert_plan()
        except Exception:                              # noqa: BLE001 -- a bad radio state is not a crash here
            return False
        if needs_tools and not self.has_tools:
            return False
        return argv is not None and Path(argv[-1]).exists()

    def on_revert(self, *, then=None):
        argv, what, needs_tools = self._revert_plan()
        # Install-to-game is reversible via the pre-install whole-folder snapshot and, unlike the
        # test-slot/own-id/battle reverts, runs on an installed copy too -- so it skips the _require_tools gate.
        if needs_tools and not self._require_tools("Revert"):
            return
        if argv is None or not Path(argv[-1]).exists():
            return self._info("Nothing to revert", f"No {what} deploy to undo yet.")
        cwd = self.repo if self.has_tools else self.kit_cwd
        if self._confirm(f"Revert {what}", f"Restore the game to before the last {what} deploy?"):
            # `then` (fires on a code==0 finish) lets the shell's spine Undo self-dismiss the JUST-DEPLOYED
            # state once the deploy it advertised is actually gone (the Build tab's own Revert passes none).
            self._stream(argv, cwd=cwd, subject=f"Revert {what}",
                         ok_headline=f"Reverted the last {what} deploy",
                         ok_next="Relaunch the game to load the restored state.", then=then)
