"""The Co-op document for the Workspace -- play FF9's story together on two PCs, point-and-click.

Built around the two people at the table, not around the engine's knobs. The HOST plays their own save;
the GUEST's game follows the host's (screens, conversations, battles, the world map) while the guest's
own save is never touched. So the page asks one question first -- host or guest? -- and then shows only
what that person sets: the host decides how their friend joins their battles; the guest has nothing to
tune, just a plain account of what following means.

Role-scoped on purpose. The first version showed one shared "play style" card to both sides, including a
"follow the host" checkbox the host could tick; the engine's follow tick has no role check, so in the b20
smoke test a following host and its following guest bounced between two fields every few seconds. Now
Join always writes FollowHost = 1, Host always 0, and ``coop.playstyle_updates(role=...)`` refuses the
host combination for the CLI too.

Wraps the ``ff9mapkit coop`` lane (:mod:`..coop`): Start streams the setup (room build if needed +
Memoria.ini ``[Netsync]``) through the shell's ``run_job``, then runs the ws->wss TLS **bridge
in-process** (background threads; FF9's old Mono can't speak TLS itself). Direct-LAN mode skips the
bridge. Only this view is Qt -- the logic is ``ff9mapkit.coop``, shared with the CLI.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QEvent, QObject, QTimer, Signal
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

# What following means, told to the guest in the order they will meet it. Facts from the engine:
# s95 (no warp-pin), s84-s99 (dialogue in step), s133-s143 (battles), s144/s145 (world map), and the
# session end reloading the guest's own autosave.
GUEST_TERMS = (
    "When the host changes screens, you are pulled along. When they talk to someone, the scene plays on "
    "your screen and their presses turn the pages. In their battles you "
    "command the party members they hand you, from FF9's own battle menu, or watch if they hand you none. "
    "On the world map the host drives and you rejoin at their next stop. While you are paired there is "
    "no main menu and no saving; when the session ends your game reloads your own autosave, untouched."
)

START_LABEL = {True: "Start hosting", False: "Join game"}
#: [ff9mapkit s154] the Host field before this PC has an own code: Start hosting makes one (coop.own_host_code)
HOST_CODE_PLACEHOLDER = "not made yet"


class CoopDoc(QWidget):
    """Host / join a co-op session as a Workspace document. ``run`` = ``shell.run_job`` (streams the
    setup subprocess to Output); the bridge runs in-process and logs into a small in-tab console (its
    lines arrive on worker threads -> marshalled via a Signal)."""

    _bridge_line = Signal(str)

    def __init__(self, pal, kit_root, *, run, output=None, on_setup=None, on_build=None):
        super().__init__()
        self.pal = pal
        self.kit = Path(kit_root)
        self._run = run
        self._output = output
        self._on_setup = on_setup      # opens the shell's Setup & Health dialog (None = no shell around us)
        self._on_build = on_build      # shell nav: switch to Build & Deploy (a quiet header cross-link)
        self._server = None            # the in-process bridge's listening socket (None = not running)
        self._thread = None
        self._game = None              # resolved install path (None until refresh_status finds it)
        self._enabled = False          # [Netsync] Enabled, as of the last refresh_status
        # [ff9mapkit s154] THE OWN-CODE LAW (coop.own_host_code): the code field is per ROLE. Host shows THIS PC's own
        # code -- never SessionCode, which after a join is the FRIEND's -- except on a LIVE host, which shows the code its
        # game dials (see refresh_status); Join shows the guest's paste, kept here while the Host radio is up and put
        # back when Join is picked again.
        self._host_code = ""           # what the Host field shows, as of the last refresh_status ("" = none yet)
        self._paste = ""               # the Join field's text, stashed while Host shows the own code
        self._shown_hosting = True     # which role the field shows now (rb_host starts checked)
        self._bridge_line.connect(self._append_log)
        self._build_ui()
        self._poll = QTimer(self)      # notices the bridge dying (or its port) without user action
        self._poll.setInterval(2000)
        self._poll.timeout.connect(self._refresh_bridge_row)
        self._poll.start()
        self.refresh_status()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # scroll the body (like Build & Deploy): a short window must scroll, not crush the cards
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        v = widgets.page_column(inner)

        crown, _ = widgets.nameplate(
            "", "Co-op",
            "Play FF9's story together on two PCs. The host plays their own save, and the guest's game "
            "follows along: the same screens, the same conversations, the same battles. The guest's own "
            "save is never touched. Beta.")
        v.addWidget(crown)
        if self._on_build is not None:                  # quiet cross-link: both PCs need the same mods
            xlink = QLabel('Both PCs need the same mods → <a href="build">Build & Deploy</a>')
            xlink.setObjectName("headerXlink")              # carries a :focus ring -- a keyboard Tab stop must show it
            xlink.setTextFormat(Qt.TextFormat.RichText)
            xlink.setProperty("role", "muted")
            xlink.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse
                                          | Qt.TextInteractionFlag.LinksAccessibleByKeyboard)  # a Tab stop, not mouse-only
            xlink.linkActivated.connect(lambda _=None: self._on_build())
            v.addWidget(xlink)

        # ---- this machine: the two things that make co-op fail before it starts
        st = widgets.section("This PC")
        sv = st.content_layout
        # A definition list. The key column sizes itself off the widest key IN ITS OWN POLISHED FONT
        # (a construction-time px clipped every key at a 150% dial). Only `game` is mono -- it is a path.
        self.lbl_game = widgets.kv("game", sv, widest="engine", mono=True)
        self.lbl_engine = widgets.kv("engine", sv, widest="engine")
        sv.addWidget(widgets.caption("Both PCs need the same engine bundle: mismatched engines refuse to pair."))
        ref = _pad(QPushButton("Refresh"))
        ref.clicked.connect(self.refresh_status)
        # The rows above can say "run Setup & health first" / "install the engine bundle" -- this is the door
        # they point at. Shown only while the status needs it; a healthy machine never sees it.
        self.btn_setup = _pad(QPushButton("Open Setup && health…"))
        self.btn_setup.clicked.connect(self._open_setup_and_recheck)
        self.btn_setup.setVisible(False)
        row = QHBoxLayout()
        row.addWidget(ref)
        row.addWidget(self.btn_setup)
        row.addStretch(1)
        sv.addLayout(row)
        v.addWidget(st)

        # ---- 1. who is this PC?
        role = widgets.section("Who is playing on this PC?")
        rv = role.content_layout
        self.rb_host = QRadioButton("Host: I play my save")
        self.rb_join = QRadioButton("Guest: I join a friend's game")
        self.rb_host.setChecked(True)
        self.rb_host.toggled.connect(self._render_role)
        widgets.option(self.rb_host, "Your game runs the story. Your friend joins with your session code.", rv)
        widgets.option(self.rb_join, "Your game follows the host's. Nothing on your own save changes.", rv)
        v.addWidget(role)

        # ---- 2. how do the two PCs reach each other?
        conn = widgets.section("How do you connect?")
        cv = conn.content_layout
        self.rb_relay = QRadioButton("Over the internet")
        self.rb_lan = QRadioButton("On the same home network")
        self.rb_relay.setChecked(True)
        self.rb_relay.toggled.connect(self._render_role)
        widgets.option(self.rb_relay, "Works from anywhere. Keep this app open while you play: it carries "
                                      "the connection.", cv)
        widgets.option(self.rb_lan, "The games talk directly, no relay. When Windows asks, allow FF9 on "
                                    "Private networks only, on both PCs.", cv)

        code_row = QHBoxLayout()
        self.code_label = QLabel("Your session code:")
        self.code = QLineEdit()
        self.code.setPlaceholderText("ff9-XXXXXXXX")
        self.code.setProperty("mono", True)             # the most-copied string in the app
        self.code.setMaximumWidth(260)                  # a 12-char code, not a 970px trough
        self.btn_copy = _pad(QPushButton("Copy"))
        self.btn_copy.clicked.connect(self._copy_code)
        # Sections have no title for Qt to borrow a screen-reader name from, so the visible label is the
        # control's name (setBuddy) -- it tracks the role wording below, so it cannot drift.
        self.code_label.setBuddy(self.code)
        code_row.addWidget(self.code_label)
        code_row.addWidget(self.code)
        code_row.addWidget(self.btn_copy)
        code_row.addStretch(1)                          # controls size to CONTENT; the slack goes here
        self.code_row = QWidget()
        self.code_row.setLayout(code_row)
        code_row.setContentsMargins(0, 0, 0, 0)
        cv.addWidget(self.code_row)

        ip_row = QHBoxLayout()
        ip_row.setContentsMargins(0, 0, 0, 0)
        self.lan_label = QLabel("Host's LAN IP:")
        self.lan_ip = QLineEdit()
        self.lan_ip.setPlaceholderText("192.168.1.20")
        self.lan_ip.setMaximumWidth(200)
        self.lan_label.setBuddy(self.lan_ip)
        ip_row.addWidget(self.lan_label)
        ip_row.addWidget(self.lan_ip)
        ip_row.addStretch(1)
        self.ip_row = QWidget()
        self.ip_row.setLayout(ip_row)
        cv.addWidget(self.ip_row)
        v.addWidget(conn)

        # ---- 3a. HOST ONLY: how the friend takes part in the host's battles. Hot-reloads into a running game.
        self.host_box = widgets.section("Your friend in your battles")
        hv = self.host_box.content_layout

        slots_row = QHBoxLayout()
        slots_lbl = QLabel("They command party position:")
        slots_row.addWidget(slots_lbl)
        self.cb_slots = []
        for i in range(4):
            cb = QCheckBox(str(i + 1))
            cb.setAccessibleName(f"They command party position {i + 1}")
            self.cb_slots.append(cb)
            slots_row.addWidget(cb)
        slots_row.addStretch(1)
        hv.addLayout(slots_row)
        hv.addWidget(widgets.caption(
            "Positions as your party menu lists them. None ticked: they watch your battles. They never get "
            "the character you walk as; that position passes to the next member."))

        ghost_row = QHBoxLayout()
        ghost_lbl = QLabel("They appear as:")
        self.combo_ghost = QComboBox()
        # Item labels are capped at minimumContentsLength characters (fenced) -- the CLOSED box renders the
        # selected item at the box's width and Qt HARD-CLIPS it, no ellipsis.
        self.combo_ghost.addItem("Their own model", "")
        self.combo_ghost.addItem("Auto — the member they command", "auto")
        # Every name coop.GHOST_NAMES accepts (fenced): a missing one loads as index 0 and the next apply
        # would rewrite the user's GhostAs to "off".
        for label, data in (("Zidane", "zidane"), ("Vivi", "vivi"), ("Garnet / Dagger", "dagger"),
                            ("Steiner", "steiner"), ("Freya", "freya"), ("Quina", "quina"),
                            ("Eiko", "eiko"), ("Amarant", "amarant"), ("Moogle", "moogle"),
                            ("Cinna", "cinna"), ("Marcus", "marcus"), ("Blank", "blank"), ("Beatrix", "beatrix")):
            self.combo_ghost.addItem(label, data)
        ghost_lbl.setBuddy(self.combo_ghost)
        ghost_row.addWidget(ghost_lbl)
        # No px maximum (deaf to the text dial); a character-based minimum so the item list does not dictate
        # the floor, and 31 characters so every item fits the closed box (fenced).
        self.combo_ghost.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_ghost.setMinimumContentsLength(31)
        ghost_row.addWidget(self.combo_ghost)
        ghost_row.addStretch(1)
        hv.addLayout(ghost_row)
        hv.addWidget(widgets.caption("On both screens. Auto is a moogle while they only watch."))

        wait_row = QHBoxLayout()
        wait_lbl = QLabel("Their turn can pause the gauges for up to:")
        self.spin_wait = QSpinBox()
        self.spin_wait.setRange(0, 600)
        self.spin_wait.setValue(30)
        self.spin_wait.setSuffix(" s")
        self.spin_wait.setSpecialValueText("no limit")
        wait_lbl.setBuddy(self.spin_wait)
        wait_row.addWidget(wait_lbl)
        wait_row.addWidget(self.spin_wait)
        wait_row.addStretch(1)
        hv.addLayout(wait_row)
        hv.addWidget(widgets.caption(
            "In Wait mode a guest turn freezes the gauges like your own menu does. This is a fallback, not a "
            "timer: their command still lands after the gauges resume."))

        apply_row = QHBoxLayout()
        self.btn_style = _pad(QPushButton("Apply now"))
        self.btn_style.setToolTip("Start hosting already applies these. Apply updates a running session.")
        self.btn_style.clicked.connect(self.apply_playstyle)
        apply_row.addWidget(self.btn_style)
        apply_row.addStretch(1)
        hv.addLayout(apply_row)
        hv.addWidget(widgets.caption("A running game picks changes up within a couple of seconds."))
        v.addWidget(self.host_box)

        # ---- 3b. GUEST ONLY: nothing to tune; say what following means
        self.guest_box = widgets.section("What happens when you join")
        self.guest_box.content_layout.addWidget(widgets.caption(GUEST_TERMS))
        v.addWidget(self.guest_box)

        # ---- the verb, and what is true right now
        btns = QHBoxLayout()
        self.btn_start = _pad(QPushButton(START_LABEL[True]))
        self.btn_start.setObjectName("accent")         # this tab's verb, and the only accent on the page
        self.btn_start.clicked.connect(self.start_coop)
        self.btn_stop = _pad(QPushButton("Disconnect"))
        self.btn_stop.setToolTip("Stops this app's link to the relay. Co-op stays set up; press Start "
                                 "again to reconnect.")
        self.btn_stop.clicked.connect(self.stop_bridge)
        self.btn_off = _pad(QPushButton("Turn co-op off"))
        self.btn_off.setToolTip("Turns co-op off in Memoria.ini and disconnects. The game goes back to solo.")
        self.btn_off.setProperty("role", "quiet")      # the ladder's bottom rung -- see style.py
        self.btn_off.clicked.connect(self.disable_coop)
        btns.addWidget(self.btn_start)
        btns.addWidget(self.btn_stop)
        btns.addStretch(1)                             # Turn off sits across the gap from the verbs
        btns.addWidget(self.btn_off)
        v.addLayout(btns)

        now = QVBoxLayout()
        now.setSpacing(2)
        self.lbl_session = widgets.kv("co-op", now, widest="co-op")
        self.lbl_bridge = widgets.kv("link", now, widest="co-op")
        v.addLayout(now)
        self.lbl_next = widgets.caption("")
        v.addWidget(self.lbl_next)

        # The bridge's own lines: useful when pairing fails, noise otherwise -- so behind a fold.
        self.log_drawer = widgets.disclosure("Connection log")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setAccessibleName("Co-op connection log")
        self.log.setMaximumHeight(120)
        self.log.setPlaceholderText("nothing yet")
        self.log_drawer.content_layout.addWidget(self.log)
        v.addWidget(self.log_drawer)
        v.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self._render_role()

    def _open_setup_and_recheck(self):
        """Open Setup & health, then RE-MEASURE: the user may have just fixed the exact thing the door exists
        for, and the warning, the door and a disabled Start must not outlive it (the GOES-AWAY law)."""
        if self._on_setup is None:
            return
        self._on_setup()
        self.refresh_status()

    def _hosting(self) -> bool:
        return self.rb_host.isChecked()

    @staticmethod
    def _usable_code(text: str) -> str:
        """``text`` stripped when coop.validate_code accepts it, else "" -- a value Copy must never hand out."""
        from .. import coop
        try:
            return coop.validate_code(text.strip())
        except ValueError:
            return ""

    def _render_role(self):
        """Show this PC's side only: the host's battle settings or the guest's account of following, the
        code as this PC's own (read-only, Copy) or the host's (pasted; kept across a flip to Host and back), and the
        LAN IP only for a LAN guest."""
        hosting = self._hosting()
        lan = self.rb_lan.isChecked()
        self.host_box.setVisible(hosting)
        self.guest_box.setVisible(not hosting)
        if hosting != self._shown_hosting:      # [ff9mapkit s154] THE OWN-CODE LAW: the field's text is per role
            if hosting:
                self._paste = self.code.text()  # the guest's paste waits while Host shows this PC's own code
                self.code.setText(self._host_code)
            else:
                self.code.setText(self._paste)
            self._shown_hosting = hosting
        self.code.setReadOnly(hosting)          # the host's code is generated/kept; the guest pastes one
        # (a code-width field: the host's placeholder stays as short as a code, or it clips at the field's edge)
        self.code.setPlaceholderText(HOST_CODE_PLACEHOLDER if hosting else "ff9-XXXXXXXX")
        self.btn_copy.setVisible(hosting)
        self.code_label.setText("Your session code:" if hosting else "Host's session code:")
        self.code.setAccessibleName(self.code_label.text().rstrip(":"))
        self.code_row.setVisible(not lan)       # a LAN session pairs by address, not by code
        self.ip_row.setVisible(lan and not hosting)
        self.btn_start.setText(START_LABEL[hosting])
        self.btn_start.setMinimumWidth(self.btn_start.fontMetrics().horizontalAdvance(self.btn_start.text()) + 34)
        self._render_next()

    def _render_next(self):
        """The next step after Start, for THIS side and transport."""
        hosting, lan = self._hosting(), self.rb_lan.isChecked()
        if hosting:
            text = ("Then launch FF9 and load your save. " +
                    ("Your friend joins with your PC's LAN IP." if lan else "Send your friend the code."))
        else:
            text = ("Then launch FF9 and load any save. Once you pair, your game jumps to the host's screen.")
        self.lbl_next.setText(text)

    # ------------------------------------------------------------------ status
    def refresh_status(self):
        """Re-read install/engine/config state. Never raises -- a game-less machine shows what's missing
        instead (the smoke runs this headless)."""
        from .. import coop, health
        from ..config import find_game_path
        try:
            self._game = find_game_path(None)
        except Exception:                        # ConfigError or anything env-shaped: report, don't crash
            self._game = None
        if self._game is None:
            self.lbl_game.setText("NOT FOUND — run Setup & health first")
            widgets.set_state(self.lbl_game, "warn")      # the answer to "why is nothing working"
            self.lbl_engine.setText("—")
            self.lbl_session.setText("—")
            widgets.set_state(self.lbl_session, "")
            self._enabled = False
            self._host_code = ""                          # [ff9mapkit s154] no install, no own code to show
            if self._hosting():
                self.code.clear()
            self.btn_start.setEnabled(False)
            self.host_box.setEnabled(False)
            self.btn_setup.setVisible(self._on_setup is not None)
            self._refresh_bridge_row()
            return
        self.btn_start.setEnabled(True)
        self.lbl_game.setText(str(self._game))
        widgets.set_state(self.lbl_game, "")
        # The engine line is the SHARED derivation (health.netsync_generation) -- the same source Setup's
        # "Co-op engine" row reads, so the two can never disagree. Amber below the current generation.
        gen = health.netsync_generation(self._game)
        warn = gen["level"] != "ok"
        self.lbl_engine.setText(gen["summary"])
        widgets.set_state(self.lbl_engine, "warn" if warn else "")
        self.btn_setup.setVisible(self._on_setup is not None and warn)   # the door keys on the SAME predicate
        self.host_box.setEnabled(gen["s37"])
        try:
            ini = coop.read_ini_text(self._game / "Memoria.ini")
        except OSError:
            ini = ""
        enabled = self._enabled = coop.read_ini_key(ini, "Netsync", "Enabled") == "1"
        role = (coop.read_ini_key(ini, "Netsync", "Role") or "host").strip().lower()
        relay = coop.read_ini_key(ini, "Netsync", "RelayUrl") or ""
        saved_code = coop.read_ini_key(ini, "Netsync", "SessionCode") or ""
        # [ff9mapkit s154] BEFORE the radios move (a flip renders it): what the Host field shows. This PC's own code --
        # except on a LIVE host (Enabled=1 and the ini's own Role is host, as the engine reads it: an absent Role is
        # selftest, not hosting), which shows the code its game DIALS and the guest must join. The two part when the
        # engine mints a code into an emptied SessionCode (it never writes HostSessionCode) or after a CLI `coop host
        # <joined code>` (coop.joined_override); showing the own code there handed out a code nobody hosts on. An empty or
        # unusable dialled code shows nothing (the placeholder). Start hosting never forwards the field either way.
        live_host = enabled and (coop.read_ini_key(ini, "Netsync", "Role") or "").strip().lower() == "host"
        self._host_code = (self._usable_code(saved_code) if live_host else coop.own_host_code(ini)[0]) or ""
        if enabled:
            # A live session's role and transport are the truth: a guest PC opening this tab must not
            # find "Host" selected. A switched-off ini leaves the user's own picks alone.
            (self.rb_host if role == "host" else self.rb_join).setChecked(True)
            (self.rb_relay if relay else self.rb_lan).setChecked(True)
            self.lbl_session.setText(("ON, hosting" if role == "host" else "ON, joined as the guest")
                                     + (" over the internet" if relay else " on the home network"))
        else:
            self.lbl_session.setText("off")
        # The session row doubles as the validation channel (Start writes warnings into it), so a refresh
        # must CLEAR the state -- otherwise a stale amber outlives the problem it described.
        widgets.set_state(self.lbl_session, "")
        # [ff9mapkit s154] THE OWN-CODE LAW: the Host field shows THIS PC's own code (or a live host's dialled one), never
        # a joined SessionCode -- after a `coop join` that is the FRIEND's code, and s153 seeded it here (a switched-off
        # guest ini, or a live guest flipping to Host), so Start hosted on the friend's invite. The Join field of a live
        # guest shows the code it joined with.
        if self._hosting():
            self.code.setText(self._host_code)
        elif enabled and saved_code and not self.code.text():
            self.code.setText(saved_code)
        self._load_playstyle(ini)               # widgets mirror the ini (Refresh = re-read)
        self._refresh_bridge_row()

    def _load_playstyle(self, ini_text: str):
        """Point the host's battle settings at what Memoria.ini actually says right now."""
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

    def _playstyle_state(self):
        """The host's battle settings as (slot_spec, wait_seconds, ghost_as) -- the same human-level
        values the CLI flags take."""
        slots = [str(i + 1) for i, cb in enumerate(self.cb_slots) if cb.isChecked()]
        return (",".join(slots) or "none", self.spin_wait.value(), self.combo_ghost.currentData() or "off")

    def _role_style(self) -> dict:
        """The ``coop host|join`` play-style kwargs for THIS side. The host writes its battle settings and
        never follows; the guest always follows and wears the host's outfit pick (GhostAs off on its own
        side: a guest-side pick only re-dresses its view of the host, and the same pick on both PCs shows
        the guest two of that character)."""
        if self._hosting():
            if not self.host_box.isEnabled():
                return {}                       # an engine without the battle lanes: leave the ini alone
            slots, wait, ghost = self._playstyle_state()
            return {"guest_slots": slots, "guest_wait": wait, "ghost_as": ghost, "follow_host": False}
        return {"ghost_as": "off", "follow_host": True}

    def _refresh_bridge_row(self):
        running = self._thread is not None and self._thread.is_alive()
        if not running and self._server is not None:
            self._stop_server()                 # the accept loop died on its own -> reflect it
        if running:
            # The port lives in the log (its first line), not here: this label cannot wrap, and at 150% the
            # longer sentence was the widest unbreakable thing on the page.
            self.lbl_bridge.setText("connected through this app — keep it open")
        elif self._enabled and self.rb_lan.isChecked():
            self.lbl_bridge.setText("direct, on the home network (no relay needed)")
        else:
            self.lbl_bridge.setText("not connected")
        self.btn_stop.setVisible(running)

    # ------------------------------------------------------------------ actions
    def start_coop(self):
        """Stream the setup (`ff9mapkit coop … --no-bridge`) through run_job, then start the bridge."""
        from .. import coop
        hosting = self._hosting()
        lan = self.rb_lan.isChecked()
        # [ff9mapkit s154] THE OWN-CODE LAW: hosting NEVER forwards the field. `coop host` with no code picks THIS PC's
        # own code itself (coop.own_host_code) -- s153 forwarded the read-only field as an EXPLICIT `coop host <code>`,
        # and that field could hold the code this PC had joined a friend with. Joining forwards the guest's paste.
        code = "" if hosting or lan else self.code.text().strip()
        if not hosting and not lan and not code:
            widgets.set_state(self.lbl_session, "warn")
            self.lbl_session.setText("paste the host's session code first (ask your friend)")
            return
        if lan and not hosting and not self.lan_ip.text().strip():
            widgets.set_state(self.lbl_session, "warn")
            self.lbl_session.setText("type the host's LAN IP first")
            return
        if code:
            # Reject a bad paste HERE, before a subprocess spawns: .strip() only trims the ends, and argv
            # carries an embedded newline through intact, so the field is a live carrier for the ini-splice
            # -- see coop.validate_code. (Join only: a host never forwards the field, so a stored value the
            # user cannot edit can no longer dead-end Start -- `coop host` ignores an unusable one out loud.)
            try:
                coop.validate_code(code)
            except ValueError as e:
                widgets.set_state(self.lbl_session, "warn")
                self.lbl_session.setText(str(e))
                return
        argv = jobs.coop_setup_argv("host" if hosting else "join", code or None,
                                    lan=("" if hosting else self.lan_ip.text().strip()) if lan else None,
                                    **self._role_style())

        def done(rc):
            self.refresh_status()
            if rc != 0 or self._game is None:
                return
            if hosting and not lan:
                ini = coop.read_ini_text(self._game / "Memoria.ini")
                new_code = coop.own_host_code(ini)[0] or ""     # [ff9mapkit s154] the code `coop host` just kept
                if new_code:
                    self.code.setText(new_code)
                    QApplication.clipboard().setText(new_code)   # same auto-copy the CLI does
                    self._append_log(f"session code {new_code} copied to the clipboard -- send it to your friend")
            if not lan:
                self.start_bridge()

        started = self._run(argv, cwd=self.kit, subject="Co-op setup",
                            ok_headline="Co-op setup — done",
                            ok_next=self.lbl_next.text(),
                            fail_hint="See the Output panel (is the game path configured?).",
                            on_finished=done)
        if not started:
            widgets.set_state(self.lbl_session, "warn")
            self.lbl_session.setText("another job is running — wait for it to finish")

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
            self.log_drawer.toggle_button.setChecked(True)     # a failure is exactly when the log matters
            return
        self._append_log(f"bridge listening on ws://127.0.0.1:{port}")
        self._refresh_bridge_row()

    def stop_bridge(self):
        self._stop_server()
        self._append_log("bridge stopped")
        self._refresh_bridge_row()

    def apply_playstyle(self):
        """Write just the host's battle settings (no room build, no role change). The engine hot-reloads
        [Netsync], so a running game -- even mid-session -- picks this up in a couple of seconds."""
        from .. import coop
        if self._game is None or not self._hosting():
            return
        slots, wait, ghost = self._playstyle_state()
        try:
            updates = coop.playstyle_updates(slots, wait, ghost, False, role="host")
            coop.write_netsync(self._game, updates, out=self._append_log)
        except (ValueError, OSError, FileNotFoundError) as e:
            self._append_log(f"could not apply the battle settings: {e}")
            return
        self._append_log("battle settings applied -- a running game picks them up in a couple of seconds")

    def disable_coop(self):
        from .. import coop
        if self._game is None:
            return
        self.stop_bridge()
        try:
            coop.write_netsync(self._game, {"Enabled": "0"}, out=self._append_log)
        # ValueError = the writer refusing an unwritable key/value (coop._check_ini_pair). An unhandled raise
        # inside a Qt slot has no stderr under pythonw -- it would vanish, and the button would do nothing.
        except (ValueError, OSError, FileNotFoundError) as e:
            self._append_log(f"could not update Memoria.ini: {e}")
        self.refresh_status()

    # ------------------------------------------------------------------ helpers
    def _config_port(self) -> int:
        """The local bridge port from the ini's RelayUrl (so a custom port set via the CLI is honored)."""
        from .. import coop
        try:
            ini = coop.read_ini_text(self._game / "Memoria.ini")
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
