"""The Co-op document for the Workspace -- two-player ghost sync, point-and-click.

Wraps the ``ff9mapkit coop`` lane (:mod:`..coop`): pick Host or Join, press **Start co-op**, and the doc
streams the setup (room build if needed + Memoria.ini ``[Netsync]``) through the shell's ``run_job``, then
runs the ws->wss TLS **bridge in-process** (background threads; FF9's old Mono can't speak TLS itself).
The session code is shown with a Copy button the moment the host's setup lands. Status at the top answers
the three "why doesn't it work" questions up front: is the game found, does the engine have the s36
netsync patch, and which mod folder carries the co-op room.

Only this view is Qt -- all the logic is ``ff9mapkit.coop`` (the CLI and this tab share one backend), and
the bridge is ``ff9mapkit.netsync_bridge`` exactly as the CLI runs it. Direct-LAN mode skips the bridge.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QRadioButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)


class _PadFilter(QObject):
    """Re-run _pad's measurement when the button's font actually lands/changes. The floor is computed
    from fontMetrics at construction -- on a PARENTLESS button that is the pre-QSS default font, and a
    CALIBRE dial change never re-measured it, so under a starved layout the floor was too small at
    150% (the same frozen-px class as the kv key column; review finding)."""

    def eventFilter(self, obj, ev):                    # noqa: N802 (Qt override)
        if ev.type() == QEvent.Type.FontChange and isinstance(obj, QPushButton):
            obj.setMinimumWidth(obj.fontMetrics().horizontalAdvance(obj.text()) + 34)
        return False


_PAD_FILTER = _PadFilter()


def _pad(btn: QPushButton) -> QPushButton:
    """Reserve room for the label + the QSS padding: a starved layout compresses a button to its
    minimumSizeHint, which under a stylesheet undercounts the padding and clips the text. The floor
    re-measures on FontChange (see _PadFilter)."""
    btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(btn.text()) + 34)
    btn.installEventFilter(_PAD_FILTER)
    return btn

from . import widgets
from ..editor import jobs


class CoopDoc(QWidget):
    """Host / join a co-op ghost-sync session as a Workspace document. ``run`` = ``shell.run_job``
    (streams the setup subprocess to Output); the bridge runs in-process and logs into a small
    in-tab console (its lines arrive on worker threads -> marshalled via a Signal)."""

    _bridge_line = Signal(str)

    def __init__(self, pal, kit_root, *, run, output=None, on_setup=None):
        super().__init__()
        self.pal = pal
        self.kit = Path(kit_root)
        self._run = run
        self._output = output
        self._on_setup = on_setup      # opens the shell's Setup & Health dialog (None = no shell around us)
        self._server = None            # the in-process bridge's listening socket (None = not running)
        self._thread = None
        self._game = None              # resolved install path (None until _refresh_status finds it)
        self._bridge_line.connect(self._append_log)
        self._build_ui()
        self._poll = QTimer(self)      # notices the bridge dying (or its port) without user action
        self._poll.setInterval(2000)
        self._poll.timeout.connect(self._refresh_bridge_row)
        self._poll.start()
        self.refresh_status()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # scroll the body (like Build & Deploy): a short window must scroll, not crush the group boxes
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        # The centred 860 reading column + the page rung + the card rhythm, in one call. (The gap between
        # cards lives in page_column now: the cards kept their borders through the card reversal, so that
        # gap separates bounded objects rather than carrying the grouping alone. The value is unchanged.)
        v = widgets.page_column(inner)

        crown, _ = widgets.nameplate(
            "", "Co-op",
            "Two-player co-op: you and a friend each see the other's ghost walk a shared field, and — if "
            "you grant it in Play style below — they command party members in your battles. Every save "
            "stays your own.")
        v.addWidget(crown)

        st = widgets.section("Status")
        sv = st.content_layout
        # A definition list, not four sentences: a muted key column, the answers at full weight on one
        # aligned left edge. The column sizes itself off the widest key IN ITS OWN POLISHED FONT (the
        # first cut measured self.fontMetrics() here, at construction -- the pre-QSS font -- and the
        # frozen px clipped every key at a 150% dial: "gameC:", "enginnetsync"). Only `game` is mono --
        # it is a path; the others are prose, and mono on a sentence reads as a bug.
        self.lbl_game = widgets.kv("game", sv, widest="engine", mono=True)
        self.lbl_engine = widgets.kv("engine", sv, widest="engine")
        self.lbl_room = widgets.kv("room", sv, widest="engine")
        self.lbl_config = widgets.kv("config", sv, widest="engine")
        ref = _pad(QPushButton("Refresh"))
        ref.clicked.connect(self.refresh_status)
        # The row above can SAY "run Setup & health… first" / "install the custom engine first" -- this
        # is the door it points at. Shown only while the status actually needs it (game missing, or the
        # engine has no netsync); a healthy machine never sees it.
        self.btn_setup = _pad(QPushButton("Open Setup && health…"))
        self.btn_setup.clicked.connect(self._open_setup_and_recheck)
        self.btn_setup.setVisible(False)
        row = QHBoxLayout()
        row.addWidget(ref)
        row.addWidget(self.btn_setup)
        row.addStretch(1)
        sv.addLayout(row)
        v.addWidget(st)

        sess = widgets.section("Session")
        gv = sess.content_layout
        self.rb_host = QRadioButton("Host")
        self.rb_join = QRadioButton("Join")
        self.rb_host.setChecked(True)
        self.rb_host.toggled.connect(self._render_role)
        widgets.option(self.rb_host, "Start a new session. Your code is shared with the other player.", gv)
        widgets.option(self.rb_join, "Enter the host's session code.", gv)

        code_row = QHBoxLayout()
        self.code_label = QLabel("Session code:")
        self.code = QLineEdit()
        self.code.setPlaceholderText("ff9-XXXXXXXX")
        self.code.setProperty("mono", True)             # the most-copied string in the app
        self.code.setMaximumWidth(260)                  # a 12-char code, not a 970px trough
        self.btn_copy = _pad(QPushButton("Copy"))
        self.btn_copy.clicked.connect(self._copy_code)
        # Qt derives an unnamed control's screen-reader name from its enclosing QGroupBox TITLE
        # (QAccessibleWidget -> buddyString). Sections have no title, so every control that was leaning on
        # the box for its name goes silent -- test_every_visible_actionable_control_has_a_screen_reader_name
        # caught exactly this. setBuddy restores it from the VISIBLE label, which is a better name than the
        # box title ever was ("Session code" beats "Session") and cannot drift out of sync.
        self.code_label.setBuddy(self.code)
        code_row.addWidget(self.code_label)
        code_row.addWidget(self.code)
        code_row.addWidget(self.btn_copy)
        code_row.addStretch(1)                          # controls size to CONTENT; the slack goes here
        gv.addLayout(code_row)

        lan_row = QHBoxLayout()
        self.rb_relay = QRadioButton("Internet (relay)")
        self.rb_relay.setToolTip("Works from anywhere; the session is bridged through a relay.")
        self.rb_lan = QRadioButton("Direct LAN")
        self.rb_lan.setToolTip("Same WiFi only, no relay.")
        self.rb_relay.setChecked(True)
        self.rb_relay.toggled.connect(self._render_role)
        self.lan_ip = QLineEdit()
        self.lan_ip.setPlaceholderText("host's LAN IP")
        self.lan_ip.setAccessibleName("Host's LAN IP")   # no visible label of its own to buddy to
        self.lan_ip.setMaximumWidth(200)
        lan_row.addWidget(self.rb_relay)
        lan_row.addSpacing(24)
        lan_row.addWidget(self.rb_lan)
        lan_row.addWidget(self.lan_ip)
        lan_row.addStretch(1)
        gv.addLayout(lan_row)
        v.addWidget(sess)

        # ---- play style (s37): battle co-op + visitor mode -- how co-op behaves on THIS machine.
        # Each side sets its own: battle slots/wait cap govern MY battles, the outfit is how THEIR
        # ghost looks on MY screen, follow-host is for the joining side. Hot-reloads into a running
        # game, so Apply works mid-session.
        self.style_box = widgets.section("Play style")
        pv = self.style_box.content_layout

        slots_row = QHBoxLayout()
        slots_lbl = QLabel("In my battles, my friend commands party slot(s):")
        slots_lbl.setToolTip("Party positions 1-4 as the in-game menu lists them. None checked = "
                             "they just spectate. Their assist panel appears in-battle; commands "
                             "are re-validated on this machine.")
        slots_row.addWidget(slots_lbl)
        self.cb_slots = []
        for i in range(4):
            cb = QCheckBox(str(i + 1))
            self.cb_slots.append(cb)
            slots_row.addWidget(cb)
        slots_row.addStretch(1)
        pv.addLayout(slots_row)

        wait_row = QHBoxLayout()
        wait_lbl = QLabel("Their turn may hold the ATB gauges for:")
        wait_lbl.setToolTip("In Wait-style ATB modes a guest turn freezes the gauges like a local "
                            "menu. This caps it — a fallback, not a rush timer: their command still "
                            "lands after the gauges resume. 0 = no cap.")
        self.spin_wait = QSpinBox()
        self.spin_wait.setRange(0, 600)
        self.spin_wait.setValue(30)
        self.spin_wait.setSuffix(" s")
        self.spin_wait.setSpecialValueText("no cap")
        wait_lbl.setBuddy(self.spin_wait)           # see the buddy note in the Session section
        wait_row.addWidget(wait_lbl)
        wait_row.addWidget(self.spin_wait)
        wait_row.addStretch(1)
        pv.addLayout(wait_row)

        ghost_row = QHBoxLayout()
        ghost_lbl = QLabel("Their ghost appears on my screen as:")
        ghost_lbl.setToolTip("Visitor mode: dress the other player's ghost as a real party member. "
                             "Auto picks whoever they command in battle (needs a battle slot above).")
        self.combo_ghost = QComboBox()
        # Item labels are capped at minimumContentsLength characters (fenced) -- the CLOSED box renders
        # the selected item at the box's width and Qt HARD-CLIPS it, no ellipsis: the round-9 snaps
        # caught "Their own model (classic gl" mid-word. The teaching lives in the tooltip above.
        self.combo_ghost.addItem("Their own model", "")
        self.combo_ghost.addItem("Auto — the member they command", "auto")
        for label, data in (("Zidane", "zidane"), ("Vivi", "vivi"), ("Garnet / Dagger", "dagger"),
                            ("Steiner", "steiner"), ("Freya", "freya"), ("Quina", "quina"),
                            ("Eiko", "eiko"), ("Amarant", "amarant")):
            self.combo_ghost.addItem(label, data)
        ghost_lbl.setBuddy(self.combo_ghost)        # see the buddy note in the Session section
        ghost_row.addWidget(ghost_lbl)
        # NO setMaximumWidth. It was 340 -- a px constant that cannot hear the text dial, and at 125/150%
        # it clamped the box BELOW its own 31-character sizeHint, hard-clipping the selected item again
        # (measured natively by the review: sizeHint 436 vs cap 340 at 150% = a 37px mid-word cut). The
        # size policy below already keeps the box at its hint; the row's stretch absorbs the slack.
        # ...and a MINIMUM, which is the half that was missing. A QComboBox's minimumSizeHint is its
        # LONGEST ITEM, so setMaximumWidth capped how wide it may get while the row stayed pinned at
        # label+longest. AdjustToMinimumContentsLengthWithIcon (Qt6 dropped the non-icon variant) makes
        # the item list stop dictating the floor; the popup still shows every option at full width.
        # 31, NOT 18: with this policy the box's sizeHint IS minimumContentsLength characters, and the
        # trailing stretch hands it nothing more -- so any item longer than the length HARD-CLIPS in the
        # closed box (measured: "…(classic gl"). 31 fits every item above (fenced: items <= this length).
        self.combo_ghost.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_ghost.setMinimumContentsLength(31)
        ghost_row.addWidget(self.combo_ghost)
        ghost_row.addStretch(1)
        pv.addLayout(ghost_row)

        # THE THIRD LAW: never put prose inside a widget (widgets.option). This shipped as one QCheckBox
        # whose LABEL was the whole sentence -- and a QCheckBox does not word-wrap, so its minimumSizeHint
        # was the full 763px string. That single control set a 797px floor under the Play-style CARD, which
        # is why Co-op forced a horizontal scrollbar at 1280 while every other doc fitted: one label the
        # layout could not compress, holding the whole page open.
        # option() splits it the way the rest of the app already does -- the NAME you tick, the consequence
        # in a capped caption beneath it -- and carries the consequence into the accessible description, so
        # a screen reader still reads what it used to say.
        self.cb_follow = QCheckBox("Follow the host between screens")
        widgets.option(self.cb_follow,
                       "Joining side: my game auto-warps to their field and my random encounters pause.",
                       pv)

        self.cb_diorama = QCheckBox("Boot into the host's battles (diorama)")
        self.cb_diorama.setChecked(True)                   # the engine default (s40): on
        widgets.option(self.cb_diorama,
                       "Joining side: when the host fights, my screen boots the same battle live "
                       "(render-only — my own save is never touched). Untick for the text spectate panel.",
                       pv)

        apply_row = QHBoxLayout()
        self.btn_style = _pad(QPushButton("Apply play style"))
        self.btn_style.clicked.connect(self.apply_playstyle)
        apply_row.addWidget(self.btn_style)
        apply_row.addStretch(1)
        pv.addLayout(apply_row)
        # The note is BELOW the button, not beside it. Inline it was a bare QLabel in an HBox: a 411px
        # minimum that could not wrap and could not compress, so button+note pinned this row at 530px --
        # the widest thing in the card once the checkbox was split. A hint gets a hint's treatment
        # (widgets.caption: capped, wrapped, on the ramp), and the row collapses to the button.
        pv.addWidget(widgets.caption("Applies to a running game within a couple of seconds — no restart."))
        v.addWidget(self.style_box)

        btns = QHBoxLayout()
        self.btn_start = _pad(QPushButton("Start co-op"))
        # This tab's verb, and the only accent on the page. setDefault(True) used to sit here and was
        # DOUBLY inert: CoopDoc is a QWidget, not a QDialog (so nothing arms a default button), and the
        # stylesheet carries no `QPushButton:default` rule to paint one. It rendered exactly zero pixels.
        self.btn_start.setObjectName("accent")
        self.btn_start.clicked.connect(self.start_coop)
        self.btn_stop = _pad(QPushButton("Stop bridge"))
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_bridge)
        self.btn_off = _pad(QPushButton("Disable co-op"))
        self.btn_off.setProperty("role", "quiet")      # the ladder's bottom rung -- see style.py
        self.btn_off.clicked.connect(self.disable_coop)
        btns.addWidget(self.btn_start)
        btns.addWidget(self.btn_stop)
        btns.addStretch(1)                             # Disable sits across the gap from the two verbs
        btns.addWidget(self.btn_off)
        v.addLayout(btns)

        self.lbl_bridge = QLabel("bridge: not running")
        v.addWidget(self.lbl_bridge)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setAccessibleName("Co-op bridge log")
        self.log.setMaximumHeight(96)
        self.log.setPlaceholderText("bridge log")
        v.addWidget(self.log)

        # A hint gets a hint's treatment (capped measure, the caption tier). As a bare QLabel it wrapped
        # at the full page column -- ~135 characters a line, the exact COLUMN defect the rest of the app
        # already fixed (widgets.caption caps at ~74ch).
        hint = widgets.caption(
            "Start co-op, keep this app open, then launch FF9 and stand on the same screen as "
            "your friend — ghosts appear anywhere you two share a field (guaranteed meeting "
            "spot: F6 → Warp to field → 30003). The in-game overlay shows the code + pairing "
            "state, tells you which field your friend is on, and disappears when their ghost "
            "is up. A running game picks up session changes within a few seconds — no restart "
            "needed.")
        v.addWidget(hint)
        v.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self._render_role()

    def _open_setup_and_recheck(self):
        """Open Setup & health, then RE-MEASURE. The dialog is modal, so when it returns the user may
        have just fixed the exact thing the door exists for -- without the recheck the amber row, the
        door, and the disabled Start all outlive the problem they describe (the GOES-AWAY law; review
        finding). refresh_status is cheap and idempotent."""
        if self._on_setup is None:
            return
        self._on_setup()
        self.refresh_status()

    def _render_role(self):
        hosting = self.rb_host.isChecked()
        self.code.setReadOnly(hosting)          # the host's code is generated/kept; the guest pastes one
        self.btn_copy.setVisible(hosting)
        self.lan_ip.setVisible(self.rb_lan.isChecked() and not hosting)

    # ------------------------------------------------------------------ status
    def refresh_status(self):
        """Re-read install/engine/room/config state. Never raises -- a game-less machine shows what's
        missing instead (the smoke runs this headless)."""
        from .. import coop
        from ..config import find_game_path
        try:
            self._game = find_game_path(None)
        except Exception:                        # ConfigError or anything env-shaped: report, don't crash
            self._game = None
        if self._game is None:
            self.lbl_game.setText("NOT FOUND — run Setup & health… first")
            widgets.set_state(self.lbl_game, "warn")      # the answer to "why is nothing working"
            self.lbl_engine.setText("—")
            self.lbl_room.setText("—")
            self.lbl_config.setText("—")
            self.btn_start.setEnabled(False)
            self.style_box.setEnabled(False)
            # ...and the DOOR the warning points at, not just its name (usability: a status that says
            # "run X first" without a way to run X is a scavenger hunt).
            self.btn_setup.setVisible(self._on_setup is not None)
            return
        self.btn_start.setEnabled(True)
        self.lbl_game.setText(str(self._game))
        widgets.set_state(self.lbl_game, "")
        dll = self._game / "x64" / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"
        try:
            blob = dll.read_bytes() if dll.is_file() else b""
        except OSError:
            blob = b""
        has_netsync = b"NetSyncClient" in blob
        has_s37 = b"NetSyncBattle" in blob          # the battle/visitor lanes shipped together (s37)
        has_s40 = b"NetSyncDiorama" in blob         # the battle diorama (s40)
        self.lbl_engine.setText("netsync + battle co-op + diorama (s40) present" if has_s40 else
                                "netsync + battle/visitor co-op (s37) — the battle diorama needs "
                                "the newer s40 engine" if has_s37 else
                                "netsync (s36) present — Play style needs the newer s37 engine"
                                if has_netsync else
                                "netsync MISSING — install the Dream World IX custom engine first")
        widgets.set_state(self.lbl_engine, "" if has_s37 else "warn")
        # The door keys on the SAME predicate as the amber state one line up (not has_s37). Its first
        # cut keyed on `not has_netsync`, so an s36 machine got a warning naming the newer engine with
        # the door to that exact remedy hidden -- the scavenger hunt back for one engine generation
        # (review finding). Setup & health owns the remedy either way ("Install engine patches…").
        self.btn_setup.setVisible(self._on_setup is not None and not has_s37)
        self.style_box.setEnabled(has_s37)
        # The diorama checkbox alone keys on s40: greyed on an s37-only engine so Apply/Start
        # never write a key the engine can't read (None -> the flag is simply not passed).
        self.cb_diorama.setEnabled(has_s40)
        folder = coop.find_registered_field(self._game, coop.COOP_FIELD)
        self.lbl_room.setText(f"field {coop.COOP_FIELD} registered ({folder})"
                              if folder else
                              f"not built yet — Start co-op builds it (field {coop.COOP_FIELD}, "
                              "takes a minute the first time)")
        try:
            ini = (self._game / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
        except OSError:
            ini = ""
        enabled = coop.read_ini_key(ini, "Netsync", "Enabled") == "1"
        role = coop.read_ini_key(ini, "Netsync", "Role") or "host"
        saved_code = coop.read_ini_key(ini, "Netsync", "SessionCode") or ""
        relay = coop.read_ini_key(ini, "Netsync", "RelayUrl") or ""
        target = (coop.read_ini_key(ini, "Netsync", "TargetField") or "0").strip()
        scope = "everywhere" if target in ("", "0") else f"field {target} only"
        self.lbl_config.setText("co-op ON — " + role + (", relay" if relay else ", direct LAN")
                                + ", " + scope if enabled else "co-op off")
        # The config row doubles as a validation channel (Start writes warnings into it), so a refresh must
        # CLEAR the state -- otherwise a stale amber outlives the problem it described.
        widgets.set_state(self.lbl_config, "")
        if self.rb_host.isChecked() and saved_code and not self.code.text():
            self.code.setText(saved_code)       # surface the persisted code without a Start
        self._load_playstyle(ini)               # widgets mirror the ini (Refresh = re-read)
        self._refresh_bridge_row()

    def _load_playstyle(self, ini_text: str):
        """Point the play-style widgets at what Memoria.ini actually says right now."""
        from .. import coop
        try:
            mask = int(coop.read_ini_key(ini_text, "Netsync", "GuestSlots") or "0") & 0x0F
        except ValueError:
            mask = 0
        for i, cb in enumerate(self.cb_slots):
            cb.setChecked(bool(mask & (1 << i)))
        try:
            wait_ms = int(coop.read_ini_key(ini_text, "Netsync", "GuestWaitMs") or "30000")
        except ValueError:
            wait_ms = 30000
        self.spin_wait.setValue(max(0, min(600, wait_ms // 1000)))
        ghost = (coop.read_ini_key(ini_text, "Netsync", "GhostAs") or "").strip().lower()
        ghost = {"garnet": "dagger", "salamander": "amarant", "off": "", "0": ""}.get(ghost, ghost)
        idx = self.combo_ghost.findData(ghost)
        self.combo_ghost.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_follow.setChecked((coop.read_ini_key(ini_text, "Netsync", "FollowHost") or "") == "1")
        # Diorama defaults ON in the engine (s40): an absent key reads as checked.
        self.cb_diorama.setChecked((coop.read_ini_key(ini_text, "Netsync", "Diorama") or "1") != "0")

    def _playstyle_state(self):
        """The widgets' current play style as (slot_spec, wait_seconds, ghost_as, follow, diorama) --
        the same human-level values the CLI flags take. ``diorama`` is None when the engine
        predates s40 (the checkbox is greyed) so nothing downstream writes the key."""
        slots = [str(i + 1) for i, cb in enumerate(self.cb_slots) if cb.isChecked()]
        return (",".join(slots) or "none", self.spin_wait.value(),
                self.combo_ghost.currentData() or "off", self.cb_follow.isChecked(),
                self.cb_diorama.isChecked() if self.cb_diorama.isEnabled() else None)

    def _refresh_bridge_row(self):
        running = self._thread is not None and self._thread.is_alive()
        if not running and self._server is not None:
            self._stop_server()                 # the accept loop died on its own -> reflect it
        if running:
            port = self._server.getsockname()[1]
            self.lbl_bridge.setText(f"bridge: RUNNING on ws://127.0.0.1:{port} — keep this app open while you play")
        else:
            self.lbl_bridge.setText("bridge: not running")
        self.btn_stop.setEnabled(running)

    # ------------------------------------------------------------------ actions
    def start_coop(self):
        """Stream the setup (`ff9mapkit coop … --no-bridge`) through run_job, then start the bridge."""
        from .. import coop
        hosting = self.rb_host.isChecked()
        lan = self.rb_lan.isChecked()
        code = self.code.text().strip()
        if not hosting and not lan and not code:
            widgets.set_state(self.lbl_config, "warn")
            self.lbl_config.setText("enter the HOST's session code first (ask your friend)")
            return
        if lan and not hosting and not self.lan_ip.text().strip():
            widgets.set_state(self.lbl_config, "warn")
            self.lbl_config.setText("direct LAN join needs the host's IP")
            return
        style = dict(zip(("guest_slots", "guest_wait", "ghost_as", "follow_host", "diorama"),
                         self._playstyle_state())) if self.style_box.isEnabled() else {}
        argv = jobs.coop_setup_argv("host" if hosting else "join", code or None,
                                    lan=("" if hosting else self.lan_ip.text().strip()) if lan else None,
                                    **style)

        def done(rc):
            self.refresh_status()
            if rc != 0 or self._game is None:
                return
            if hosting:
                ini = (self._game / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
                new_code = coop.read_ini_key(ini, "Netsync", "SessionCode") or ""
                if new_code:
                    self.code.setText(new_code)
                    QApplication.clipboard().setText(new_code)   # same auto-copy the CLI does
                    self._append_log(f"session code {new_code} copied to the clipboard -- send it to your friend")
            if not lan:
                self.start_bridge()

        started = self._run(argv, cwd=self.kit, subject="Co-op setup",
                            ok_headline="Co-op setup — done",
                            ok_next=("send your code, then launch FF9 -> F6 -> Warp -> 30003"
                                     if hosting else "launch FF9 -> F6 -> Warp -> 30003"),
                            fail_hint="See the Output panel (is the game path configured?).",
                            on_finished=done)
        if not started:
            widgets.set_state(self.lbl_config, "warn")
            self.lbl_config.setText("another job is running — wait for it to finish")

    def start_bridge(self):
        from .. import netsync_bridge as nb
        if self._thread is not None and self._thread.is_alive():
            return
        # Route the bridge's log lines into the in-tab console. They arrive on worker threads, so they
        # go through the queued Signal; the rebind also matters under pythonw, where print() has no stdout.
        nb.log = lambda msg: self._bridge_line.emit(str(msg))
        port = self._config_port()
        try:
            self._server, self._thread = nb.run_server("127.0.0.1", port, nb.default_relay(), False)
        except OSError as e:
            self._append_log(f"bridge failed to start on port {port}: {e}")
            return
        self._append_log(f"bridge listening on ws://127.0.0.1:{port}")
        self._refresh_bridge_row()

    def stop_bridge(self):
        self._stop_server()
        self._append_log("bridge stopped")
        self._refresh_bridge_row()

    def apply_playstyle(self):
        """Write just the play-style keys (no room build, no role change). The engine hot-reloads
        [Netsync], so a running game -- even mid-session -- picks this up in a couple of seconds."""
        from .. import coop
        if self._game is None:
            return
        slots, wait, ghost, follow, diorama = self._playstyle_state()
        try:
            updates = coop.playstyle_updates(slots, wait, ghost, follow, diorama)
            coop.write_netsync(self._game, updates, out=self._append_log)
        except (ValueError, OSError, FileNotFoundError) as e:
            self._append_log(f"could not apply the play style: {e}")
            return
        self._append_log("play style applied -- a running game picks it up in a couple of seconds")

    def disable_coop(self):
        from .. import coop
        if self._game is None:
            return
        self.stop_bridge()
        try:
            coop.write_netsync(self._game, {"Enabled": "0"}, out=self._append_log)
        except (OSError, FileNotFoundError) as e:
            self._append_log(f"could not update Memoria.ini: {e}")
        self.refresh_status()

    # ------------------------------------------------------------------ helpers
    def _config_port(self) -> int:
        """The local bridge port from the ini's RelayUrl (so a custom port set via the CLI is honored)."""
        from .. import coop
        try:
            ini = (self._game / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
            url = coop.read_ini_key(ini, "Netsync", "RelayUrl") or ""
            if url.startswith("ws://127.0.0.1:"):
                return int(url.rsplit(":", 1)[1].split("/")[0])
        except (OSError, ValueError):
            pass
        return coop.BRIDGE_PORT

    def _stop_server(self):
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
        self._server = None
        self._thread = None

    def _copy_code(self):
        code = self.code.text().strip()
        if code:
            QApplication.clipboard().setText(code)
            self._append_log(f"copied {code}")

    def _append_log(self, line: str):
        self.log.appendPlainText(line)

    def closeEvent(self, ev):                    # the shell owns app close; be tidy anyway
        self._stop_server()
        super().closeEvent(ev)
