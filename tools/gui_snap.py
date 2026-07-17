"""gui_snap -- render any Workspace surface to a PNG, from the harness, no human in the loop.

The iteration engine for GUI rounds: an agent (or a human) runs this, Reads the PNGs, and judges the
real pixels instead of guessing from source. Built on the laws the aesthetics study paid for
(studies/gui-aesthetics/STATE.md + the project-ff9-gui-makeover memory):

  * NATIVE platform only. offscreen stubs the font DB -- every WIDTH it reports is fiction, and it has
    manufactured whole defects. This tool refuses to run offscreen.
  * The app runs Fusion deliberately (shell._apply_app_theme). Every snap goes through the same call.
  * PIN the prefs. An empty tempdir is NOT a clean room -- prefs.text_scale() falls through to the
    developer's Windows slider. LOCALAPPDATA is repointed at a scratch dir AND an explicit prefs.json is
    written with every value pinned (text_scale from --scale, guided from --guided, motion off, ...).
  * WA_DontShowOnScreen: widgets render fully but never flash a window on the user's desktop.
  * Modal dialogs are driven by patching QDialog.exec to show+grab+reject, so any on_* opener runs
    unmodified. The app's _warn helpers use the STATIC QMessageBox.warning/information/question, whose
    exec runs in C++ and never consults a Python-monkeypatched QDialog.exec -- unstubbed they would
    open a REAL modal and hang a headless run forever, so the statics are stubbed to their default
    button (and the stub prints the message, which is itself diagnostic).

Usage:
  py tools/gui_snap.py --list
  py tools/gui_snap.py home:fresh dlg:fork-regions --theme mist --scale 100
  py tools/gui_snap.py all --theme dark --scale 150 --width 1280
PNGs land in tools/scroll_out/gui_snaps/ (override with --out). Each snap prints its path plus the
geometry facts that matter for sizing bugs: shown size, sizeHint, minimumSizeHint.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "ff9mapkit"))

os.environ["FF9MAPKIT_NO_THUMBS"] = "1"          # deterministic: no thumbnail worker threads
# offscreen is banned (see the module docstring); make sure an inherited env can't sneak it in.
if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    del os.environ["QT_QPA_PLATFORM"]

assert os.name == "nt", "the prefs pin repoints LOCALAPPDATA, which provision._user_dir honours ONLY on Windows"
_SCRATCH = Path(tempfile.mkdtemp(prefix="gui_snap_prefs_"))
os.environ["LOCALAPPDATA"] = str(_SCRATCH)       # BEFORE any ff9mapkit import resolves the config dir


def _pin_prefs(theme: str, scale: int, guided: bool, recent: list | None = None) -> None:
    """Write an explicit prefs.json -- every value pinned, none left to fall through to the OS."""
    cfg = _SCRATCH / "ff9mapkit" / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "prefs.json").write_text(json.dumps({
        "theme": theme, "text_scale": scale, "guided": guided, "density": "comfortable",
        "motion": "off", "restore_session": False, "recent": recent or [],
    }, indent=2), encoding="utf-8")
    # update_check must never prompt or hit the network during a snap.
    (cfg / "update_check.json").write_text(json.dumps({"prompted": True, "enabled": False}),
                                           encoding="utf-8")


# ---------------------------------------------------------------------------------------------- Qt setup
from PySide6.QtCore import QCoreApplication, QEvent, Qt                   # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox   # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB and lies about width"

from ff9mapkit.workspace import shell as S                                # noqa: E402
from ff9mapkit.workspace.shell import pick_palette                        # noqa: E402


def _settle(n: int = 6) -> None:
    """Drive the UI the way the real event loop would -- INCLUDING deferred deletes.

    processEvents() does NOT deliver QEvent.DeferredDelete (only a running event loop does), so a
    probe that rebuilds rows (deleteLater + re-add) and then grabs will photograph ZOMBIE widgets --
    live-parented, visible, painting under their replacements -- that the real app buries before its
    next paint. Measured: the Home checklist rebuild showed a sliver of the OLD step-3 row between
    the new cards, and 12 extra processEvents rounds changed nothing. The instrument, not the app.
    """
    for _ in range(n):
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()


def _hide_flag(w) -> None:
    """Render fully, never appear on the desktop. Set BEFORE show()."""
    w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)


class _Ctx:
    """One snap run's knobs + bookkeeping."""

    def __init__(self, args):
        self.theme = args.theme
        self.scale = args.scale
        self.guided = args.guided != "full"
        self.width = args.width
        self.height = args.height
        self.out = Path(args.out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.saved: list[Path] = []

    def png(self, name: str) -> Path:
        return self.out / f"{name}_{self.theme}_{self.scale}.png"

    def report(self, name: str, w, path: Path) -> None:
        s, sh, msh = w.size(), w.sizeHint(), w.minimumSizeHint()
        print(f"  {path}")
        print(f"      shown {s.width()}x{s.height()}  sizeHint {sh.width()}x{sh.height()}"
              f"  minimumSizeHint {msh.width()}x{msh.height()}")
        self.saved.append(path)


def _make_win(ctx: _Ctx, *, recent: list | None = None):
    """A fresh Workspace, prefs pinned, native+Fusion, hidden-rendered at the asked width."""
    _pin_prefs(ctx.theme, ctx.scale, ctx.guided, recent)
    pal = pick_palette(ctx.theme)
    S._apply_app_theme(app, pal)
    win = S.Workspace(pal)
    _hide_flag(win)
    win.setFixedSize(ctx.width, ctx.height)
    win.show()
    _settle()
    assert win.width() == ctx.width, f"asked {ctx.width}, got {win.width()} -- snap void"
    return win


def _grab(ctx: _Ctx, name: str, w) -> None:
    _settle()
    img = w.grab().toImage()
    assert img.width() > 50 and img.height() > 50, f"{name}: grabbed nothing"
    path = ctx.png(name)
    img.save(str(path))
    ctx.report(name, w, path)


def _close(win) -> None:
    win.close()
    win.deleteLater()
    _settle(3)


# ------------------------------------------------------------------------------------- setup-state pins
class _pin_setup_state:
    """Force the machine-independent setup states Home branches on (game found / templates present)."""

    def __init__(self, *, game: bool, templates: bool):
        self.game, self.templates = game, templates

    def __enter__(self):
        from ff9mapkit import health, provision
        self._h, self._p = health, provision
        self._orig = (health.find_game, provision.templates_present, health.quick_issues)
        if self.game:
            health.find_game = lambda: (Path("C:/FF9"), None)
            health.quick_issues = lambda: []
        else:
            health.find_game = lambda: (None, "FF9 install not located")
            health.quick_issues = lambda: ["FF9 install not located"]
        self._p.templates_present = lambda: self.templates
        return self

    def __exit__(self, *exc):
        self._h.find_game, self._p.templates_present, self._h.quick_issues = self._orig
        return False


def _example_recent() -> list:
    """Recent rows pointing at real bundled examples (Home prunes rows whose file vanished)."""
    rows = []
    for kind, rel in (("campaign", "examples/stolen-ember/campaign.toml"),
                      ("field", "ff9mapkit/examples/SHOWCASE/showcase.field.toml"),
                      ("field", "ff9mapkit/examples/vivi-hut/hut_int.field.toml")):
        p = REPO / rel
        if p.exists():
            rows.append({"kind": kind, "path": str(p)})
    return rows


# ---------------------------------------------------------------------------------------- co-op states
def _fake_install(state: str) -> Path:
    """A minimal fake FF9 install expressing one co-op machine state. CoopDoc detects the engine by
    scanning Assembly-CSharp.dll for marker strings and reads [Netsync] from Memoria.ini -- both are
    just bytes on disk, so a scratch tree pins every state on any machine, game or no game.

    A STABLE path, not mkdtemp: the game path is painted VERBATIM into the status row (mono, full
    weight), so a random suffix made every snap differ in its most prominent line and broke
    pixel-diffing across runs. One fixed dir per state, rewritten each run."""
    game = Path(tempfile.gettempdir()) / "ff9_gui_snap" / f"game_{state}"
    managed = game / "x64" / "FF9_Data" / "Managed"
    managed.mkdir(parents=True, exist_ok=True)
    marker = {"stock": b"", "s36": b"NetSyncClient", "s37": b"NetSyncClient NetSyncBattle",
              "ready": b"NetSyncClient NetSyncBattle NetSyncDiorama",
              "live": b"NetSyncClient NetSyncBattle NetSyncDiorama"}
    (managed / "Assembly-CSharp.dll").write_bytes(b"MZfake" + marker[state])   # KeyError on an unknown
    #                                              state -- fabricating a fake machine silently is worse
    ini = ("[Netsync]\nEnabled = 1\nRole = host\nSessionCode = ff9-a1b2c3d4\n"
           "RelayUrl = wss://relay.example/ws\nGuestSlots = 3\nGuestWaitMs = 30000\n"
           "GhostAs = vivi\nFollowHost = 1\n") if state == "live" else "[Netsync]\nEnabled = 0\n"
    (game / "Memoria.ini").write_text(ini, encoding="utf-8")
    return game


class _pin_coop_state:
    """Point CoopDoc at a fake install: nogame | stock | s36 | s37 | ready | live."""

    def __init__(self, state: str):
        self.state = state

    def __enter__(self):
        from ff9mapkit import config as _cfg, coop as _coop
        self._cfg, self._coop = _cfg, _coop
        self._orig = (_cfg.find_game_path, _coop.find_registered_field)
        if self.state == "nogame":
            _cfg.find_game_path = lambda *_a, **_k: None
        else:
            game = _fake_install(self.state)
            _cfg.find_game_path = lambda *_a, **_k: game
            if self.state in ("ready", "live"):    # the co-op room is registered on this "machine"
                _coop.find_registered_field = lambda *_a, **_k: "FF9CustomMap"
        return self

    def __exit__(self, *exc):
        self._cfg.find_game_path, self._coop.find_registered_field = self._orig
        return False


COOP_STATES = ("nogame", "stock", "s36", "s37", "ready", "live")


def snap_coop(ctx: _Ctx, state: str) -> None:
    if state not in COOP_STATES:
        raise ValueError(f"unknown coop state {state!r} (know: {', '.join(COOP_STATES)})")
    with _pin_setup_state(game=(state != "nogame"), templates=True), _pin_coop_state(state):
        win = _make_win(ctx)
        doc = getattr(win, "coop", None) or getattr(win, "coop_doc")
        doc.refresh_status()                       # re-read through the pinned fake install
        if state == "live":
            # The live HALF of the page: a real bound socket + an alive dummy thread stand in for the
            # bridge, so the RUNNING row (the page's longest single-line label) and the enabled Stop
            # button render. Render-only; torn down before close.
            import socket
            import threading
            srv = socket.socket()
            srv.bind(("127.0.0.1", 0))
            gate = threading.Event()
            th = threading.Thread(target=gate.wait, daemon=True)
            th.start()
            doc._server, doc._thread = srv, th
            doc._append_log(f"bridge listening on ws://127.0.0.1:{srv.getsockname()[1]}")
            doc._refresh_bridge_row()
        win.tabs.setCurrentWidget(doc)
        _grab(ctx, f"coop-{state}", win)
        # ...and the WHOLE page (the scroll's inner widget renders at full content height), so the
        # below-the-fold half -- play style, verbs, bridge, log, the hint -- is in the record too.
        from PySide6.QtWidgets import QScrollArea
        inner = doc.findChild(QScrollArea).widget()
        _grab(ctx, f"coop-{state}-full", inner)
        if state == "live":
            gate.set()
            doc._stop_server()
        _close(win)


# ------------------------------------------------------------------------------------------- surfaces
def snap_home(ctx: _Ctx, state: str) -> None:
    pins = {"fresh":   dict(game=False, templates=False),
            "midway":  dict(game=True,  templates=False),
            "ready":   dict(game=True,  templates=True),
            "veteran": dict(game=True,  templates=True),
            "open":    dict(game=True,  templates=True)}[state]
    recent = _example_recent() if state in ("veteran", "open") else None
    with _pin_setup_state(**pins):
        win = _make_win(ctx, recent=recent)
        if state == "open":
            f = REPO / "ff9mapkit/examples/SHOWCASE/showcase.field.toml"
            if f.exists():
                win.open_field(f)
            win.tabs.setCurrentWidget(win._welcome_tab)
        win._refresh_home_status()
        _settle(12)          # deleteLater'd checklist rows from the rebuild must finish dying before the grab
        _grab(ctx, f"home-{state}", win)
        _close(win)


def snap_tab(ctx: _Ctx, tab: str) -> None:
    if tab == "coop":
        # tab:coop unpinned rendered THIS machine's real [Netsync] state -- including the developer's
        # real SessionCode painted into the code field and saved into the PNG record. The coop:<state>
        # surfaces own this tab with every input pinned.
        print("  tab:coop is pinned-only -- use coop:<state> (see --list)")
        return
    attr = {"build": "build_deploy", "import": "import_field",
            "models": "models_doc", "battle": "battle", "story": "story_state",
            "items": "item_equip"}[tab]
    win = _make_win(ctx)
    win.tabs.setCurrentWidget(getattr(win, attr))
    _grab(ctx, f"tab-{tab}", win)
    _close(win)


class _grab_next_dialog:
    """Patch QDialog.exec: show hidden-rendered, grab EVERY dialog the flow opens, reject.

    QFileDialog statics are stubbed to '' so no native picker can hang the run.
    """

    def __init__(self, ctx: _Ctx, name: str):
        self.ctx, self.name, self.count = ctx, name, 0

    def __enter__(self):
        self._exec = QDialog.exec
        self._file = (QFileDialog.getOpenFileName, QFileDialog.getSaveFileName,
                      QFileDialog.getExistingDirectory)
        QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
        QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: "")
        # The static message boxes exec in C++ (they never consult the Python QDialog.exec patch below)
        # and would hang the run as a REAL modal. Stub them to their default answer, loudly.
        self._msg = (QMessageBox.warning, QMessageBox.information, QMessageBox.question, QMessageBox.critical)

        def _msg_stub(name, ret):
            def stub(_parent, title, text, *a, **k):
                print(f"      [{name}] {title}: {text}".splitlines()[0])
                return ret
            return staticmethod(stub)

        QMessageBox.warning = _msg_stub("warning", QMessageBox.StandardButton.Ok)
        QMessageBox.information = _msg_stub("information", QMessageBox.StandardButton.Ok)
        QMessageBox.question = _msg_stub("question", QMessageBox.StandardButton.No)
        QMessageBox.critical = _msg_stub("critical", QMessageBox.StandardButton.Ok)
        me = self

        def exec_(dlg):
            me.count += 1
            suffix = "" if me.count == 1 else f"-{me.count}"
            _hide_flag(dlg)
            dlg.show()
            _settle()
            img = dlg.grab().toImage()
            path = me.ctx.png(f"{me.name}{suffix}")
            img.save(str(path))
            me.ctx.report(f"{me.name}{suffix}", dlg, path)
            dlg.close()
            return int(QDialog.DialogCode.Rejected)

        QDialog.exec = exec_
        return self

    def __exit__(self, *exc):
        QDialog.exec = self._exec
        (QFileDialog.getOpenFileName, QFileDialog.getSaveFileName,
         QFileDialog.getExistingDirectory) = self._file
        (QMessageBox.warning, QMessageBox.information,
         QMessageBox.question, QMessageBox.critical) = self._msg
        return False


def snap_dialog(ctx: _Ctx, key: str) -> None:
    openers = {
        "new-field":     lambda w: w.on_new_field(),
        "new-campaign":  lambda w: w.on_new_campaign(),
        "new-journey":   lambda w: w.on_new_journey(),
        "fork-regions":  lambda w: w.import_field.open_region_catalog(),
        "setup":         lambda w: w._open_setup(),
        "prefs":         lambda w: w._open_preferences(),
        "about":         lambda w: w._open_about(),
        "concept-map":   lambda w: w._show_concept_map(),
        "infohub":       lambda w: w._open_catalog(),
        "updates":       lambda w: w._open_update_dialog(),
        # the real opener is _fork_dialog (the first cut guessed `on_fork_battle` behind a hasattr guard,
        # which made this surface permanently, silently dead -- caught by the round's adversarial review)
        "fork-battle":   lambda w: w.battle._fork_dialog(),
    }
    with _pin_setup_state(game=True, templates=True):
        win = _make_win(ctx)
        with _grab_next_dialog(ctx, f"dlg-{key}") as g:
            openers[key](win)
        if g.count == 0:
            print(f"  dlg-{key}: NO dialog opened (flow bailed before exec)")
        _close(win)


HOME_STATES = ("fresh", "midway", "ready", "veteran", "open")
TABS = ("build", "import", "coop", "models", "battle", "story", "items")
DIALOGS = ("new-field", "new-campaign", "new-journey", "fork-regions", "setup", "prefs",
           "about", "concept-map", "infohub", "updates", "fork-battle")


def all_surfaces() -> list[str]:
    return ([f"home:{s}" for s in HOME_STATES] + [f"tab:{t}" for t in TABS]
            + [f"dlg:{d}" for d in DIALOGS] + [f"coop:{s}" for s in COOP_STATES])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("surfaces", nargs="*", help="home:<state> | tab:<name> | dlg:<name> | all")
    ap.add_argument("--theme", default="mist", help="palette key (dark/light/mist/nord/...)")
    ap.add_argument("--scale", type=int, default=100, choices=(100, 110, 125, 150))
    ap.add_argument("--guided", default="guided", choices=("guided", "full"))
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=850)
    ap.add_argument("--out", default=str(HERE / "scroll_out" / "gui_snaps"))
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list or not args.surfaces:
        print("surfaces:")
        for s in all_surfaces():
            print(f"  {s}")
        return
    ctx = _Ctx(args)
    names = all_surfaces() if args.surfaces == ["all"] else args.surfaces
    for s in names:
        kind, _, rest = s.partition(":")
        try:
            if kind == "home":
                snap_home(ctx, rest)
            elif kind == "tab":
                snap_tab(ctx, rest)
            elif kind == "dlg":
                snap_dialog(ctx, rest)
            elif kind == "coop":
                snap_coop(ctx, rest)
            else:
                print(f"  unknown surface {s!r} (try --list)")
        except Exception as e:                                        # noqa: BLE001 -- one bad surface
            print(f"  {s}: FAILED -- {type(e).__name__}: {e}")        # must not kill the whole sweep
    print(f"\n{len(ctx.saved)} snap(s) in {ctx.out}")


if __name__ == "__main__":
    main()
