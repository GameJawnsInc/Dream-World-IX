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

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QRadioButton, QScrollArea, QVBoxLayout, QWidget,
)


def _pad(btn: QPushButton) -> QPushButton:
    """Reserve room for the label + the QSS padding: a starved layout compresses a button to its
    minimumSizeHint, which under a stylesheet undercounts the padding and clips the text."""
    btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(btn.text()) + 34)
    return btn

from ..editor import jobs


class CoopDoc(QWidget):
    """Host / join a co-op ghost-sync session as a Workspace document. ``run`` = ``shell.run_job``
    (streams the setup subprocess to Output); the bridge runs in-process and logs into a small
    in-tab console (its lines arrive on worker threads -> marshalled via a Signal)."""

    _bridge_line = Signal(str)

    def __init__(self, pal, kit_root, *, run, output=None):
        super().__init__()
        self.pal = pal
        self.kit = Path(kit_root)
        self._run = run
        self._output = output
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
        v = QVBoxLayout(inner)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(10)

        intro = QLabel("Two-player exploration co-op: you and a friend each see the other's ghost walk "
                       "a shared field. No battle or story coupling — every save stays your own.")
        intro.setWordWrap(True)
        v.addWidget(intro)

        st = QGroupBox("Status")
        sv = QVBoxLayout(st)
        self.lbl_game = QLabel("game: …")
        self.lbl_engine = QLabel("engine: …")
        self.lbl_room = QLabel("room: …")
        self.lbl_config = QLabel("config: …")
        for w in (self.lbl_game, self.lbl_engine, self.lbl_room, self.lbl_config):
            w.setWordWrap(True)
            sv.addWidget(w)
        ref = _pad(QPushButton("Refresh"))
        ref.clicked.connect(self.refresh_status)
        row = QHBoxLayout()
        row.addWidget(ref)
        row.addStretch(1)
        sv.addLayout(row)
        v.addWidget(st)

        sess = QGroupBox("Session")
        gv = QVBoxLayout(sess)
        self.rb_host = QRadioButton("Host — start a new session (your code is shared with the other player)")
        self.rb_join = QRadioButton("Join — enter the host's session code")
        self.rb_host.setChecked(True)
        self.rb_host.toggled.connect(self._render_role)
        gv.addWidget(self.rb_host)
        gv.addWidget(self.rb_join)

        code_row = QHBoxLayout()
        self.code_label = QLabel("Session code:")
        self.code = QLineEdit()
        self.code.setPlaceholderText("generated on Start (host) / paste the host's ff9-XXXXXXXX (join)")
        self.btn_copy = _pad(QPushButton("Copy"))
        self.btn_copy.clicked.connect(self._copy_code)
        code_row.addWidget(self.code_label)
        code_row.addWidget(self.code, 1)
        code_row.addWidget(self.btn_copy)
        gv.addLayout(code_row)

        lan_row = QHBoxLayout()
        self.rb_relay = QRadioButton("Internet (relay) — works from anywhere")
        self.rb_lan = QRadioButton("Direct LAN — same WiFi, no relay")
        self.rb_relay.setChecked(True)
        self.rb_relay.toggled.connect(self._render_role)
        self.lan_ip = QLineEdit()
        self.lan_ip.setPlaceholderText("host's LAN IP (join only)")
        lan_row.addWidget(self.rb_relay)
        lan_row.addWidget(self.rb_lan)
        lan_row.addWidget(self.lan_ip, 1)
        gv.addLayout(lan_row)
        v.addWidget(sess)

        btns = QHBoxLayout()
        self.btn_start = _pad(QPushButton("Start co-op"))
        self.btn_start.setDefault(True)
        self.btn_start.clicked.connect(self.start_coop)
        self.btn_stop = _pad(QPushButton("Stop bridge"))
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_bridge)
        self.btn_off = _pad(QPushButton("Disable co-op"))
        self.btn_off.clicked.connect(self.disable_coop)
        btns.addWidget(self.btn_start)
        btns.addWidget(self.btn_stop)
        btns.addWidget(self.btn_off)
        btns.addStretch(1)
        v.addLayout(btns)

        self.lbl_bridge = QLabel("bridge: not running")
        v.addWidget(self.lbl_bridge)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(96)
        self.log.setPlaceholderText("bridge log")
        v.addWidget(self.log)

        hint = QLabel("Start co-op, keep this app open, then launch FF9 → F6 → Warp to field → 30003 "
                      "(both players). The in-game overlay shows the code + pairing state and disappears "
                      "when your friend's ghost is up. Memoria.ini is read at launch — restart FF9 after "
                      "changing the session.")
        hint.setWordWrap(True)
        v.addWidget(hint)
        v.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self._render_role()

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
            self.lbl_game.setText("game: NOT FOUND — run Setup & health… first")
            self.lbl_engine.setText("engine: —")
            self.lbl_room.setText("room: —")
            self.lbl_config.setText("config: —")
            self.btn_start.setEnabled(False)
            return
        self.btn_start.setEnabled(True)
        self.lbl_game.setText(f"game: {self._game}")
        dll = self._game / "x64" / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"
        try:
            has_netsync = dll.is_file() and b"NetSyncClient" in dll.read_bytes()
        except OSError:
            has_netsync = False
        self.lbl_engine.setText("engine: netsync (s36) present"
                                if has_netsync else
                                "engine: netsync MISSING — install the Dream World IX custom engine first")
        folder = coop.find_registered_field(self._game, coop.COOP_FIELD)
        self.lbl_room.setText(f"room: field {coop.COOP_FIELD} registered ({folder})"
                              if folder else
                              f"room: not built yet — Start co-op builds it (field {coop.COOP_FIELD}, "
                              "takes a minute the first time)")
        try:
            ini = (self._game / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
        except OSError:
            ini = ""
        enabled = coop.read_ini_key(ini, "Netsync", "Enabled") == "1"
        role = coop.read_ini_key(ini, "Netsync", "Role") or "host"
        saved_code = coop.read_ini_key(ini, "Netsync", "SessionCode") or ""
        relay = coop.read_ini_key(ini, "Netsync", "RelayUrl") or ""
        self.lbl_config.setText("config: co-op ON — " + role + (", relay" if relay else ", direct LAN")
                                if enabled else "config: co-op off")
        if self.rb_host.isChecked() and saved_code and not self.code.text():
            self.code.setText(saved_code)       # surface the persisted code without a Start
        self._refresh_bridge_row()

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
            self.lbl_config.setText("config: enter the HOST's session code first (ask your friend)")
            return
        if lan and not hosting and not self.lan_ip.text().strip():
            self.lbl_config.setText("config: direct LAN join needs the host's IP")
            return
        argv = jobs.coop_setup_argv("host" if hosting else "join", code or None,
                                    lan=("" if hosting else self.lan_ip.text().strip()) if lan else None)

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
            self.lbl_config.setText("config: another job is running — wait for it to finish")

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
