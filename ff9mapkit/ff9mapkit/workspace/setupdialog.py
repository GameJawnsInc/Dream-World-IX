"""The Setup & Health dialog -- the Workspace's onboarding front door.

Renders :mod:`..health`'s report as colored rows and wires the three setup actions: Locate game…
(pick + validate + persist the install path, in-process), Run setup (the full ``ff9mapkit setup``
pipeline -- detect, remember, extract templates, engine report -- streamed into the dialog's own
console via its own QProcess, so it works even while the shell's job runner is busy), and Install
engine patches… (confirm-first: ``setup --install-engine <zip>``, which backs up the live DLLs).

Everything degrades: on a machine with no game install the report says exactly what's wrong and the
buttons stay usable.
"""

from __future__ import annotations

import html as _html
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from .. import health

_GLYPH = {"ok": "✓", "warn": "⚠", "bad": "✕"}


class SetupHealthDialog(QDialog):
    """Health report + setup actions. ``kit_cwd`` = where ``py -m ff9mapkit`` resolves the local
    package (the shell's KIT); ``on_change`` (optional) fires after anything that may have changed
    the environment (config saved / setup ran), so the shell can refresh its Home banner."""

    def __init__(self, parent, pal, *, kit_cwd, on_change=None):
        super().__init__(parent)
        self.pal = pal
        self.kit_cwd = str(kit_cwd)
        self.on_change = on_change
        self.proc = None
        self.setWindowTitle("Setup & Health")
        self.setMinimumWidth(680)
        v = QVBoxLayout(self)
        intro = QLabel("Everything the kit needs, checked live. Fix the red rows first; amber rows "
                       "limit specific features (the advice says which).")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color:{pal['muted']};")
        v.addWidget(intro)

        self.grid_host = QWidget()
        v.addWidget(self.grid_host)
        self._grid = None

        row = QHBoxLayout()
        self.locate_btn = QPushButton("Locate game…")
        self.locate_btn.setToolTip("Point the kit at your FF9 install folder (saved to ~/.ff9mapkit.toml "
                                   "— every command resolves it from there).")
        self.locate_btn.clicked.connect(self.on_locate)
        self.setup_btn = QPushButton("Run setup")
        self.setup_btn.setObjectName("accent")
        self.setup_btn.setToolTip("The full first-run pipeline: detect the install, remember it, extract "
                                  "the base templates (~1–2 min, once), and report the Memoria engine. "
                                  "Non-destructive; safe to re-run.")
        self.setup_btn.clicked.connect(self.on_setup)
        self.engine_btn = QPushButton("Install engine patches…")
        self.engine_btn.setToolTip("Install the dwix-custom-memoria DLL bundle (needed by FORKED fields). "
                                   "Backs up the live DLLs first — reversible. Needs Memoria installed.")
        self.engine_btn.clicked.connect(self.on_engine)
        self.recheck_btn = QPushButton("Re-check")
        self.recheck_btn.clicked.connect(self.refresh)
        for b in (self.locate_btn, self.setup_btn, self.engine_btn, self.recheck_btn):
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Setup output streams here.")
        self.console.setFixedHeight(180)
        v.addWidget(self.console)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.close)              # via closeEvent -> the running-process guard applies
        close_row.addWidget(close)
        v.addLayout(close_row)
        self.refresh()

    # ---- the report ----
    def refresh(self):
        if self._grid is not None:
            # Detach NOW, then deleteLater. deleteLater alone is not enough: a deferred delete queued
            # OUTSIDE the dialog's exec() (e.g. the shell refreshing before exec) only processes when
            # that OUTER event-loop level resumes -- i.e. after the dialog closes -- so the stale grid
            # would render doubled under the new one for the dialog's whole lifetime.
            self._grid.setParent(None)
            self._grid.deleteLater()
        self._grid = QWidget(self.grid_host)
        g = QGridLayout(self._grid)
        g.setContentsMargins(0, 4, 0, 4)
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(6)
        col = {"ok": self.pal["success"], "warn": self.pal["warn"], "bad": self.pal["error"]}
        rows = health.health_report()
        for i, r in enumerate(rows):
            mark = QLabel(_GLYPH.get(r["level"], "·"))
            mark.setStyleSheet(f"color:{col.get(r['level'], self.pal['muted'])};font-weight:700;")
            lab = QLabel(r["label"])
            lab.setStyleSheet("font-weight:600;")
            val = QLabel(_html.escape(r["value"])                       # raw exception text / user paths --
                         + (f'   <span style="color:{self.pal["muted"]};">{_html.escape(r["advice"])}</span>'
                            if r["advice"] else ""))                    # never markup
            val.setTextFormat(Qt.TextFormat.RichText)
            val.setWordWrap(True)
            g.addWidget(mark, i, 0)
            g.addWidget(lab, i, 1)
            g.addWidget(val, i, 2)
        g.setColumnStretch(2, 1)
        lay = self.grid_host.layout()
        if lay is None:
            lay = QVBoxLayout(self.grid_host)
            lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._grid)
        self._worst = health.worst_level(rows)

    # ---- actions ----
    def on_locate(self):
        d = QFileDialog.getExistingDirectory(self, "Your FINAL FANTASY IX install folder")
        if not d:
            return
        from .. import config
        if not config._is_ff9_root(Path(d)):
            QMessageBox.warning(self, "Not an FF9 install",
                                f"{d}\n\ndoesn't look like the FF9 Steam/GOG folder (needs "
                                "FF9_Launcher.exe + StreamingAssets + FF9_Data/Managed). The Microsoft "
                                "Store build isn't supported.")
            return
        p = config.save_game_path(d)
        self.console.appendPlainText(f"Saved game path to {p}")
        self.refresh()
        if self.on_change:
            self.on_change()

    def _busy(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning

    def _run(self, argv, headline):
        if self._busy():
            QMessageBox.information(self, "Busy", "A setup step is already running.")
            return
        self.console.appendPlainText(f"$ {' '.join(argv[1:])}")
        for b in (self.locate_btn, self.setup_btn, self.engine_btn, self.recheck_btn):
            b.setEnabled(False)
        self._running = True
        self.proc = QProcess(self)
        self.proc.setProgram(argv[0])
        self.proc.setArguments([str(a) for a in argv[1:]])
        self.proc.setWorkingDirectory(self.kit_cwd)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(
            lambda: self.console.appendPlainText(
                bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace").rstrip()))
        self.proc.finished.connect(lambda code, _st: self._done(code, headline))
        # finished is NOT emitted on FailedToStart -- without this the buttons stay dead forever
        self.proc.errorOccurred.connect(
            lambda err: self._done(-1, f"{headline} (process error: {err.name})")
            if err == QProcess.ProcessError.FailedToStart else None)
        self.proc.start()

    def _done(self, code, headline):
        if not getattr(self, "_running", False):       # double-fire guard (errorOccurred + finished on crash)
            return
        self._running = False
        for b in (self.locate_btn, self.setup_btn, self.engine_btn, self.recheck_btn):
            b.setEnabled(True)
        self.console.appendPlainText(f"— {headline}: {'done' if code == 0 else f'exit {code} (see above)'}")
        self.refresh()
        if self.on_change:
            self.on_change()

    def closeEvent(self, event):                       # noqa: N802 (Qt override)
        """Closing mid-run must not silently orphan the process (it looks cancelled but keeps writing —
        and an app exit would then KILL it mid-write, worst case during an engine-DLL install)."""
        if self._busy():
            ans = QMessageBox.question(
                self, "Setup is still running",
                "A setup step is still running.\n\nStop it? (No keeps this dialog open until it finishes.)")
            if ans != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.proc.kill()
            self.proc.waitForFinished(3000)
        event.accept()

    def reject(self):                                  # Esc / the Close button route through closeEvent
        self.close()

    def on_setup(self):
        self._run([sys.executable, "-m", "ff9mapkit", "setup"], "Setup")

    def on_engine(self):
        f, _ = QFileDialog.getOpenFileName(self, "The engine bundle zip (dwix-custom-memoria-*.zip)",
                                           "", "Engine bundle (*.zip)")
        if not f:
            return
        if QMessageBox.question(
                self, "Install engine patches",
                "Install the patched Memoria DLLs into your game (x64 + x86 Managed)?\n\n"
                "The live DLLs are backed up first (dwix-engine-backups/<timestamp>/) — reversible. "
                "Needed only for FORKED fields; novel fields run on stock Memoria.",
        ) != QMessageBox.StandardButton.Yes:
            return
        self._run([sys.executable, "-m", "ff9mapkit", "setup", "--install-engine", f], "Engine install")
