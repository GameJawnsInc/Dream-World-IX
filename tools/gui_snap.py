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
import shutil
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
        self.campaign = getattr(args, "campaign", None)
        self.thumb_source = getattr(args, "thumb_source", None)
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


# --------------------------------------------------------------------------------------- world states
WORLD_STATES = ("guide", "nogame", "atlas")


def _fake_world_install() -> Path:
    """A fake install whose FF9CustomMap-world tree exercises every mark the atlas draws: two
    landmasses (one with buildings), a donor'd water-only carry, a STALE Disc4 mirror cell, and an
    --in-place .bak sibling. Stable path (the coop lesson: mkdtemp randomness breaks pixel-diffing);
    real write_ff9mesh header bytes, so the census reads it exactly like a shipped tree."""
    import struct

    def mesh(vcount=120, icount=210, salt=0):
        out = bytearray(b"F9WM") + struct.pack("<iiii", 1, vcount, icount, 0)
        for i in range(vcount):
            out += struct.pack("<3f", float(i + salt), 0.0, float(i))
        return bytes(out + struct.pack("<%di" % icount, *([0] * icount)))

    game = Path(tempfile.gettempdir()) / "ff9_gui_snap" / "game_world"
    mod = game / "FF9CustomMap-world"
    if mod.exists():
        shutil.rmtree(mod)

    def put(bx, by, name, data, disc=1):
        d = mod / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"Block[{bx}][{by}] {name}").write_bytes(data)

    west = ((4, 17), (5, 17), (4, 18), (5, 18), (6, 18))     # island-E-ish: an L of land
    east = tuple((bx, by) for bx in (18, 19, 20) for by in (17, 18, 19))   # the v4 3x3 massif bench
    for i, (bx, by) in enumerate(west + east):
        t = mesh(salt=i)
        put(bx, by, "Terrain.ff9mesh", t)
        put(bx, by, "Terrain.ff9mesh", t, disc=4)
    put(19, 18, "Object.ff9mesh", mesh(vcount=60, icount=90, salt=99))     # the ensemble's buildings
    put(19, 18, "Object.ff9mesh", mesh(vcount=60, icount=90, salt=99), disc=4)
    put(19, 18, "Donor.txt", b"5,15")                        # the horseshoe donor, as deployed
    stale = bytearray(mesh(salt=3))
    stale[-1] ^= 0xFF                                        # same size, different bytes -> STALE ring
    put(4, 18, "Terrain.ff9mesh", bytes(stale), disc=4)
    put(11, 19, "Terrain.ff9mesh", mesh(vcount=3, icount=3))               # the water-only arming stub
    put(11, 19, "Sea4.ff9mesh", mesh(vcount=8, icount=12, salt=7))
    put(11, 19, "Terrain.ff9mesh", mesh(vcount=3, icount=3), disc=4)
    put(11, 19, "Sea4.ff9mesh", mesh(vcount=8, icount=12, salt=7), disc=4)
    put(11, 19, "Donor.txt", b"0,0")
    put(6, 18, "Terrain.ff9mesh.bak-20260719-093929", mesh(salt=42))       # an --in-place backup
    (mod / "atlas-names.json").write_text(json.dumps(                      # landmass nameplates
        {"version": 1, "names": {"4,17": "Twin Isles", "18,17": "The Bench"}}), encoding="utf-8")
    return game


# The REAL install's stock land/sea grid, derived once via worldscan.derive_stock_grid (1.2s over
# p0data) and baked here so the atlas snap shows the true FF9 geography deterministically on any
# machine. Pure derived FACT (like the field manifest), zero SE bytes. L=land ~=coastal-water .=ocean;
# regenerate: py -c "from ff9mapkit.workspace import worldscan as w; from ff9mapkit import config;
# print(*w._rows_encode(w.derive_stock_grid(config.find_game_path(None))), sep='\n')"
_STOCK_ROWS = [
    "L......~LLL.~...........",
    "......LLLLL...LLLL~.....",
    ".....LLLLL...LLLLLL.....",
    "....LLLLL....LLLLLLLL~..",
    "....LLLL~..LLLLLLLLLL~..",
    ".....~LL..LLLLLLLLLLL...",
    "..LLLLLL.LL.LLLLLLLLL...",
    "..LLLLLLLLL.LLLLLLLLL...",
    "..LLLLLLL........~LLL...",
    "..LLLLLL~.....LLLLLLLL..",
    "..LLLLLLL...LLLLLLLLLL..",
    "..LLLLLLL..LLLLLLLLLLLL.",
    "...LLLLLL..LLLLLLLLLLLL.",
    "...LLLLLLL.LLLLLLLLLLLL.",
    "...LLLLLLL.~LLLLLLLLLLL.",
    "...~LLLLL~.~LLLLLLLLLLL.",
    ".....LLLL...LLLLLLLLLLL.",
    "......~LLLL.LLLLL.......",
    "........~LL..LLLL.......",
    "........................",
]


class _pin_world_state:
    """Point WorldDoc's scan at a fake install -- or at a raising resolver for `nogame` (production
    RAISES ConfigError; a pin returning None would fence an unreachable branch, the round-9 law).
    The atlas state also pins FF9MAPKIT_DATA at a scratch cache seeded with the baked stock grid, so
    the geography layer renders without touching the developer's cache or bundles."""

    def __init__(self, state: str):
        self.state = state

    def __enter__(self):
        from ff9mapkit import config as _cfg
        self._cfg, self._orig = _cfg, _cfg.find_game_path
        self._env = os.environ.get("FF9MAPKIT_DATA")
        if self.state == "nogame":
            def _raise(*_a, **_k):
                raise _cfg.ConfigError("FF9 install not found (pinned surface)")
            _cfg.find_game_path = _raise
        else:
            game = _fake_world_install()
            _cfg.find_game_path = lambda *_a, **_k: game
            cache = _SCRATCH / "world_cache"
            cache.mkdir(parents=True, exist_ok=True)
            (cache / "worldstock.json").write_text(json.dumps(
                {"version": 1, "game": str(game), "disc": 1, "rows": [r[:24] for r in _STOCK_ROWS]}),
                encoding="utf-8")
            os.environ["FF9MAPKIT_DATA"] = str(cache)
        return self

    def __exit__(self, *exc):
        self._cfg.find_game_path = self._orig
        if self._env is None:
            os.environ.pop("FF9MAPKIT_DATA", None)
        else:
            os.environ["FF9MAPKIT_DATA"] = self._env
        return False


def snap_world(ctx: _Ctx, state: str) -> None:
    if state not in WORLD_STATES:
        raise ValueError(f"unknown world state {state!r} (know: {', '.join(WORLD_STATES)})")
    if state == "guide":                           # the pre-scan front door: NO pin needed, because the
        win = _make_win(ctx)                       # doc does no I/O until the user's own Scan click --
        win.tabs.setCurrentWidget(win.world_doc)   # which is itself the contract this surface records
        _grab(ctx, "world-guide", win)
        _close(win)
        return
    with _pin_world_state(state):
        win = _make_win(ctx)
        win.tabs.setCurrentWidget(win.world_doc)
        win.world_doc.refresh(sync=True)           # the deterministic lane; production scans on a worker
        if state == "atlas":
            win.world_doc.canvas.select((19, 18))  # the showpiece cell: donor + buildings + details card
        _settle()
        _grab(ctx, f"world-{state}", win)
        if state == "atlas":                       # the siting enhancement: a clean ocean block's
            win.world_doc.canvas.select((14, 19))  # free-site strip + world-island command button
            _settle()
            _grab(ctx, "world-atlas-site", win)
        _close(win)


# ---------------------------------------------------------------------------------------- map states
MAP_STATES = ("empty", "plain", "art")


class _pin_map_art:
    """The `map:art` surface's cache pin: FF9MAPKIT_DATA -> a scratch cache SEEDED with one thumb per
    member, thumbs ENABLED for this surface only (the module-top NO_THUMBS pin returns on exit).

    Seeding order per member: the project's own background.png (build_thumb scales it -- game-free);
    else a real_<id>.png copied from --thumb-source (a warm cache from a real session, e.g. the main
    repo's .ff9mapkit-cache/thumbs); else a generated flat-gradient placeholder. Every member lands
    WARM, so open_campaign answers entirely from the disk fast path and NO worker thread ever spawns --
    which is also the point: the grab proves the warm-cache -> art-band contract on a fresh session."""

    def __init__(self, campaign_toml: Path, thumb_source: Path | None):
        self.campaign_toml = Path(campaign_toml)
        self.thumb_source = Path(thumb_source) if thumb_source else None

    def __enter__(self):
        self._env = {k: os.environ.get(k) for k in ("FF9MAPKIT_DATA", "FF9MAPKIT_NO_THUMBS")}
        cache = _SCRATCH / "map_cache"
        os.environ["FF9MAPKIT_DATA"] = str(cache)
        os.environ["FF9MAPKIT_NO_THUMBS"] = "0"
        self._seed(cache / "thumbs")
        return self

    def __exit__(self, *exc):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return False

    def _seed(self, tdir: Path) -> None:
        import shutil

        from ff9mapkit import campaign as C
        from ff9mapkit.workspace import thumbs as T
        tdir.mkdir(parents=True, exist_ok=True)
        plan = C.load_campaign(self.campaign_toml)
        counts = {"project": 0, "copied": 0, "placeholder": 0}
        for i, m in enumerate(plan.members):
            toml = (self.campaign_toml.parent / m.toml_rel).resolve()
            if T._project_background(toml) is not None:
                T.build_thumb(toml, m.real_id)             # scales the project art into the pinned cache
                counts["project"] += 1
                continue
            src = (self.thumb_source / f"real_{int(m.real_id)}.png") if self.thumb_source else None
            if src is not None and src.is_file():
                shutil.copy2(src, tdir / src.name)
                counts["copied"] += 1
                continue
            self._placeholder(tdir / f"real_{int(m.real_id)}.png", i)
            counts["placeholder"] += 1
        print(f"  map:art seeded {len(plan.members)} thumb(s) -- "
              + ", ".join(f"{v} {k}" for k, v in counts.items() if v))

    @staticmethod
    def _placeholder(out: Path, i: int) -> None:
        """A deterministic flat two-tone gradient (no fonts -- font rasters differ per machine)."""
        from PIL import Image
        hues = ((66, 84, 122), (94, 74, 106), (64, 102, 96), (116, 96, 66))
        r0, g0, b0 = hues[i % len(hues)]
        im = Image.new("RGB", (360, 270))
        px = im.load()
        for y in range(270):
            t = y / 270
            row = (int(r0 * (1 - t) + 24 * t), int(g0 * (1 - t) + 28 * t), int(b0 * (1 - t) + 34 * t))
            for x in range(360):
                px[x, y] = row
        im.save(out, "PNG")


def _map_campaign(ctx: _Ctx) -> Path:
    p = Path(ctx.campaign) if ctx.campaign else REPO / "examples" / "stolen-ember" / "campaign.toml"
    if not p.is_file():
        raise FileNotFoundError(f"no campaign.toml at {p} (pass --campaign)")
    return p


def _grab_map_scene(ctx: _Ctx, name: str, mv) -> None:
    """The WHOLE scene at 1:1 (the viewport crops a large campaign) -- the full-map record."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QImage, QPainter
    r = mv._scene.sceneRect()
    img = QImage(int(r.width()), int(r.height()), QImage.Format.Format_ARGB32)
    img.fill(mv.backgroundBrush().color())
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    mv._scene.render(p, QRectF(0, 0, r.width(), r.height()), r)
    p.end()
    path = ctx.png(name)
    img.save(str(path))
    print(f"  {path}\n      scene {int(r.width())}x{int(r.height())}")
    ctx.saved.append(path)


def snap_map(ctx: _Ctx, state: str) -> None:
    if state not in MAP_STATES:
        raise ValueError(f"unknown map state {state!r} (know: {', '.join(MAP_STATES)})")
    if state == "empty":
        win = _make_win(ctx)
        win.tabs.setCurrentWidget(win.map)
        _grab(ctx, "map-empty", win)
        _close(win)
        return
    camp = _map_campaign(ctx)
    if state == "plain":                           # NO_THUMBS stays pinned -> the compact no-art boxes
        win = _make_win(ctx)                       # (what a game-less machine sees)
        win.open_campaign(camp)                    # lands on the Map tab itself
        _grab(ctx, "map-plain", win)
        _grab_map_scene(ctx, "map-plain-scene", win.map)
        _close(win)
        return
    with _pin_map_art(camp, Path(ctx.thumb_source) if ctx.thumb_source else None):
        win = _make_win(ctx)
        win.open_campaign(camp)
        # THE CACHING CONTRACT, asserted where it lives: the warm disk fast path answers request()
        # with NO ready() emit, and open_campaign renders the Map BEFORE the prefetch loop -- so a
        # warm open MUST have scheduled the coalesced rerender itself. Fire it now (the harness
        # cannot idle 250ms) and require the art bands to be up.
        assert win._thumb_rerender.isActive(), \
            "warm-cache open did not schedule the map rerender (the REOPEN HOLE class)"
        win._thumb_rerender.stop()
        win.map.rerender()
        _settle()
        assert win.map._use_thumbs, "cached thumbs on disk but the map drew the no-art boxes"
        _grab(ctx, "map-art", win)
        _grab_map_scene(ctx, "map-art-scene", win.map)
        _close(win)


# ------------------------------------------------------------------------------------- model states
MODEL_STATES = ("cliplist", "player")

_SNAP_MODEL = "GEO_MAIN_F0_VIV"                  # id 8 -- the catalog anchor, on every machine
_SNAP_FRAMES = 16                                # rendered frames the pin seeds for the clip


class _pin_anim_cache:
    """The `models:*` surfaces' cache pin: FF9MAPKIT_DATA -> a scratch cache seeded with everything
    the Models tab's preview column reads, thumbs ENABLED for this surface only (the module-top
    NO_THUMBS pin returns on exit -- and it is read at ModelsDoc CONSTRUCTION, so the pin has to be
    up before ``_make_win``).

    THREE things get seeded, because the player needs all three and a hole in any of them shows as an
    empty box rather than an error:
      * the STATIC model thumb + its counts sidecar -- what the detail pane paints before a clip is
        armed, and the target Reset restores;
      * one deterministic PNG per rendered frame (a flat gradient + a marker that MOVES with the frame
        index, so a still of the player provably shows a frame and not the thumb -- no fonts, whose
        rasters differ per machine);
      * the clip's meta json (frame_count / sample_rate / stride / fps / rendered_frames), which is
        what drives the transport and the counter.
    Everything lands WARM, so ``request_clip`` answers from disk with no worker and no signal -- which
    is also the point: the grab proves the warm-clip contract on a fresh session.
    """

    def __init__(self, geo: str = _SNAP_MODEL):
        self.geo = geo
        self.anim = None
        self.geo_id = None
        self.label = None                        # the pinned clip's ROW LABEL (what a picker field holds)

    def __enter__(self):
        self._env = {k: os.environ.get(k) for k in ("FF9MAPKIT_DATA", "FF9MAPKIT_NO_THUMBS")}
        os.environ["FF9MAPKIT_DATA"] = str(_SCRATCH / "anim_cache")
        os.environ["FF9MAPKIT_NO_THUMBS"] = "0"
        self._seed()
        return self

    def __exit__(self, *exc):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return False

    def _seed(self) -> None:
        from ff9mapkit import catalog
        from ff9mapkit.models import thumbcache
        m = catalog.model(self.geo)
        assert m is not None, f"no model {self.geo} in the catalog -- snap void"
        rows = catalog.clip_inventory(m.id)
        assert rows, f"{self.geo} has no catalogued clips -- snap void"
        self.geo_id, self.anim = m.id, rows[0]["anim_id"]        # the 'stand' movement slot
        self.label = rows[0]["label"]
        still, sidecar = thumbcache.model_thumb_paths(m.id)
        still.parent.mkdir(parents=True, exist_ok=True)
        self._figure(still, 0, _SNAP_FRAMES, still=True)
        sidecar.write_text(json.dumps({"geo": m.name, "id": m.id, "bones": 48, "meshes": 3,
                                       "verts": 1284, "textures": ["viv_body", "viv_face"]}),
                           encoding="utf-8")
        frames = list(range(_SNAP_FRAMES))
        thumbcache.anim_frame_path(m.id, self.anim, 0).parent.mkdir(parents=True, exist_ok=True)
        for f in frames:
            self._figure(thumbcache.anim_frame_path(m.id, self.anim, f), f, _SNAP_FRAMES)
        thumbcache.anim_meta_path(m.id, self.anim).write_text(json.dumps({
            "geo": m.name, "id": m.id, "anim": self.anim, "anim_key": "snap", "folder": m.id,
            "label": rows[0]["label"], "frame_count": _SNAP_FRAMES, "sample_rate": 30.0,
            "stride": 1, "fps": 30.0, "fit": [-1.0, 1.0, -1.0, 1.0], "rendered_frames": frames,
        }), encoding="utf-8")
        print(f"  models:* seeded {self.geo} (id {m.id}) clip {self.anim} -- "
              f"1 still + {len(frames)} frames + meta")

    @staticmethod
    def _figure(out: Path, i: int, n: int, *, still: bool = False) -> None:
        """A deterministic 256x256 'model': a vertical gradient plus a disc that swings with the frame
        index (the still's disc sits centred and grey). No fonts -- font rasters differ per machine."""
        import math

        from PIL import Image, ImageDraw

        from ff9mapkit.models import thumbcache
        size = thumbcache.MODEL_THUMB
        im = Image.new("RGB", (size, size))
        px = im.load()
        for y in range(size):
            t = y / size
            row = (int(46 * (1 - t) + 26 * t), int(52 * (1 - t) + 30 * t), int(66 * (1 - t) + 38 * t))
            for x in range(size):
                px[x, y] = row
        d = ImageDraw.Draw(im)
        if still:
            cx, cy, fill = size / 2, size / 2, (150, 156, 168)
        else:
            a = 2 * math.pi * i / max(1, n)
            cx, cy, fill = size / 2 + 52 * math.sin(a), size / 2 - 30 * math.cos(a), (232, 196, 96)
        d.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=fill)
        d.line([size / 2, cy + 20, size / 2, size - 34], fill=(120, 128, 146), width=9)
        im.save(out, "PNG")


def snap_models(ctx: _Ctx, state: str) -> None:
    """The Models tab's animation preview: the clip list armed and idle, and the player mid-clip."""
    if state not in MODEL_STATES:
        raise ValueError(f"unknown model state {state!r} (know: {', '.join(MODEL_STATES)})")
    from PySide6.QtWidgets import QScrollArea
    with _pin_anim_cache() as pin:
        win = _make_win(ctx)
        # HOLD the still-render worker for the whole surface: the tab enqueues its top-of-list batch
        # (_THUMB_BATCH == 96) at construction, and on this cold scratch cache that fill would race
        # the grab -- rows repainting mid-photograph.
        win.model_thumbs.hold()
        try:
            win.tabs.setCurrentWidget(win.models_doc)
            md = win.models_doc
            md.search.setText(pin.geo)
            _settle()
            assert md.listw.count() == 1, f"the search did not narrow to {pin.geo} -- snap void"
            md.listw.setCurrentRow(0)
            _settle()
            assert md.clip_list.count() > 5, "the clip list is empty -- snap void"
            right = md.findChildren(QScrollArea)[0].widget()
            if state == "cliplist":
                _grab(ctx, "models-cliplist", win)
                _grab(ctx, "models-cliplist-detail", right)
            else:
                rows = [md.clip_list.item(i).data(Qt.ItemDataRole.UserRole)
                        for i in range(md.clip_list.count())]
                md.clip_list.setCurrentRow(rows.index(pin.anim))
                _settle()
                assert md._armed == (pin.geo, pin.anim), "the row did not arm the player -- snap void"
                assert len(md._seq) == _SNAP_FRAMES, \
                    f"the pinned clip painted {len(md._seq)}/{_SNAP_FRAMES} frames -- warm read broke"
                md.anim_slider.setValue(_SNAP_FRAMES // 2)   # a MID-clip frame: a still of frame 0
                _settle()                                    # is indistinguishable from the thumb
                _grab(ctx, "models-player", win)
                _grab(ctx, "models-player-detail", right)
                _grab_strip(ctx, "models-player-transport", md.anim_strip)
        finally:
            win.model_thumbs.release()
        _close(win)


# ------------------------------------------------------------------------------------------- surfaces
# Home's setup-state pins, module-level for the same reason as TAB_ATTRS.
HOME_PINS = {"fresh":   dict(game=False, templates=False),
             "midway":  dict(game=True,  templates=False),
             "ready":   dict(game=True,  templates=True),
             "veteran": dict(game=True,  templates=True),
             "open":    dict(game=True,  templates=True)}


def snap_home(ctx: _Ctx, state: str) -> None:
    pins = HOME_PINS[state]
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


DRIFT_STATES = ("none", "synced", "ahead", "campaign")


class _no_modals:
    """Make every message box non-blocking for a whole surface, loudly -- BOTH kinds.

    Needed OUTSIDE a dialog grab, which is why it is not part of :class:`_grab_next_dialog`. The case that
    found it: a surface that deliberately leaves UNSAVED edits (drift:ahead), where ``win.close()`` fires the
    unsaved-changes prompt long after the dialog grab has exited. The run hung with NO OUTPUT AT ALL and only
    ``faulthandler.dump_traceback_later`` said where -- worth remembering as the tool for a silent hang.

    TWO KINDS, and the first fix only covered one. The static helpers (``QMessageBox.warning`` etc.) exec in
    C++ and never consult a Python-patched ``QDialog.exec``; but ``_maybe_prompt_unsaved`` builds an INSTANCE
    (``QMessageBox(self).exec()``), which the static stubs cannot see. So the instance ``exec`` is stubbed too,
    to Discard -- a snap must not silently WRITE the user's project, and Save would.

    (`_maybe_prompt_unsaved` early-returns under ``QT_QPA_PLATFORM=offscreen``, which is exactly why every
    offscreen probe of this feature was clean and only the native snap hung.)
    """

    def __enter__(self):
        self._msg = (QMessageBox.warning, QMessageBox.information, QMessageBox.question, QMessageBox.critical)
        self._exec = QMessageBox.exec

        def _exec_stub(box):
            print(f"      [modal] {box.windowTitle()}: {box.text()}".splitlines()[0])
            return QMessageBox.StandardButton.Discard      # never Save: a snap must not write the project
        QMessageBox.exec = _exec_stub

        def _stub(name, ret):
            def stub(_parent, title, text, *a, **k):
                print(f"      [{name}] {title}: {text}".splitlines()[0])
                return ret
            return staticmethod(stub)

        QMessageBox.warning = _stub("warning", QMessageBox.StandardButton.Ok)
        QMessageBox.information = _stub("information", QMessageBox.StandardButton.Ok)
        QMessageBox.question = _stub("question", QMessageBox.StandardButton.No)
        QMessageBox.critical = _stub("critical", QMessageBox.StandardButton.Ok)
        return self

    def __exit__(self, *exc):
        (QMessageBox.warning, QMessageBox.information,
         QMessageBox.question, QMessageBox.critical) = self._msg
        QMessageBox.exec = self._exec
        return False


class _pin_snapshot_dir:
    """Redirect deploy SNAPSHOTS to this run's scratch, so a snap never writes into the checkout.

    Scoped to :mod:`deploysnap`, NOT done with ``FF9MAPKIT_DATA``. The first cut set that env var -- and it
    overrides ``provision.data_dir()`` (the TEMPLATES dir) as well as the cache, so it silently pointed every
    surface's template lookup at an empty directory and the whole harness hung on the first snap. One knob,
    two meanings: patch the narrow thing instead.
    """

    def __init__(self, sub: str):
        self.dir = _SCRATCH / "snapcache" / sub

    def __enter__(self):
        from ff9mapkit.editor import deploysnap
        self._mod, self._orig = deploysnap, deploysnap.snap_dir
        deploysnap.snap_dir = lambda: self.dir
        return self

    def __exit__(self, *exc):
        self._mod.snap_dir = self._orig
        return False


def _drift_project(ctx, kind="field"):
    """A WRITABLE copy of a bundled example + the shell aimed at it.

    Never the bundled example itself: the study's standing rule is that a form-editor Save rewrites the
    byte-exact golden oracle. A snap that edits a project has to edit a copy.
    """
    # stolen-ember lives at the REPO root's examples/, boletta under the package's -- resolve, never assume.
    rel = ("examples/stolen-ember" if kind == "campaign" else "ff9mapkit/examples/boletta")
    src = next((c for c in (REPO / rel, REPO / "ff9mapkit" / rel, REPO / rel.split("/", 1)[-1]) if c.is_dir()), None)
    assert src is not None, f"cannot find the {kind} example ({rel}) -- snap void"
    dst = _SCRATCH / f"drift_{kind}"
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    proj = (dst / "campaign.toml") if kind == "campaign" else (dst / "boletta.field.toml")
    win = _make_win(ctx)
    if kind == "campaign":
        win.open_campaign(proj)
    else:
        win.open_field(proj)
    win.build_deploy.set_target(str(proj))
    _settle(6)
    return win, proj


def _grab_strip(ctx: _Ctx, name: str, w, factor: int = 3) -> None:
    """Grab a SHORT widget (a status bar is ~25px) upscaled nearest-neighbour.

    Two reasons, both from round 11: `_grab` floors at 50px so a strip fails its "grabbed nothing" assert;
    and a chip judged inside an 850px window shot is the downscaled-review mistake -- the subject has to be
    big enough to read. Nearest-neighbour so no intermediate colour is invented.
    """
    _settle()
    img = w.grab().toImage()
    assert img.width() > 20 and img.height() > 4, f"{name}: grabbed nothing"
    big = img.scaled(img.width() * factor, img.height() * factor,
                     Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
    path = ctx.png(name)
    big.save(str(path))
    print(f"  {path}")
    print(f"      strip {img.width()}x{img.height()} at {factor}x")
    ctx.saved.append(path)


def snap_drift(ctx: _Ctx, state: str) -> None:
    """The drift chip + the change list: "am I looking at what the game is running?"

    The deploy is driven through the real hooks (_capture_deploy_snapshot / _commit_deploy_snapshot) rather
    than by hand-writing a snapshot file, so the snap exercises the shipped path. FF9MAPKIT_DATA already
    points at this run's scratch dir, so no real cache is touched.
    """
    if state not in DRIFT_STATES:
        raise ValueError(f"unknown drift state {state!r} (know: {', '.join(DRIFT_STATES)})")
    # _no_static_modals wraps the WHOLE surface: the 'ahead' states end with unsaved edits on purpose, and
    # win.close() then fires the unsaved-changes prompt -- a static QMessageBox, i.e. a hard hang.
    with _pin_snapshot_dir(state), _no_modals():
        _snap_drift_body(ctx, state)


def _snap_drift_body(ctx: _Ctx, state: str) -> None:
    win, _proj = _drift_project(ctx, "campaign" if state == "campaign" else "field")
    if state != "none":                                  # 'none' = never deployed -> the chip must be absent
        win._capture_deploy_snapshot()
        win._deployed_field_id = 4004
        win._commit_deploy_snapshot()
        _settle(4)
    if state in ("ahead", "campaign"):
        doc = win._docs[sorted(win._docs)[0]]
        doc.data.setdefault("camera", {})["pitch"] = 45.0
        doc.data.setdefault("field", {})["title"] = "A Colder Glade"
        npcs = doc.data.get("npc") or []
        if npcs:
            npcs[0]["dialogue"] = "It is colder now than it was."
        win._refresh_drift_chip()
        _settle(4)
    win._refresh_drift_chip()
    _settle(4)
    _grab(ctx, f"drift-{state}", win)
    _grab_strip(ctx, f"drift-{state}-statusbar", win.statusBar())
    with _grab_next_dialog(ctx, f"drift-{state}-dialog"):
        win._open_drift()
    _close(win)


SCRIPT_STATES = ("tree", "panel")


def _load_script_demo():
    """The synthetic verbatim demo field's builder lives in tests/test_workspace_script_tree.py -- ONE
    owner for the fixture bytes (kit-authored raw instructions, zero Square-Enix bytes), loaded by path
    because tests/ is not a package. Import side effects are benign here: the module's env setdefaults
    land after the native QApplication already exists."""
    import importlib.util
    p = REPO / "ff9mapkit" / "tests" / "test_workspace_script_tree.py"
    spec = importlib.util.spec_from_file_location("_script_demo_fixture", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def snap_script(ctx: _Ctx, state: str) -> None:
    """The verbatim 'Script (verbatim .eb)' presentation over the kit-authored demo field: the tree
    expanded to its routines with the NPC talk handler selected ('tree' -- the Inspector shows the
    friendly transcript), or that routine's in-place edit panel ('panel')."""
    if state not in SCRIPT_STATES:
        raise ValueError(f"unknown script state {state!r} (know: {', '.join(SCRIPT_STATES)})")
    demo = _load_script_demo()
    root = _SCRATCH / "script_demo"                    # stable path -- mkdtemp breaks pixel-diffing
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    proj = demo.make_demo_campaign(root)
    win = _make_win(ctx)
    assert win.open_campaign(proj), "the demo campaign must open"
    win.tree.expandItem(win.tree.topLevelItem(0))
    vitem = win.tree.topLevelItem(0).child(0)
    win.tree.expandItem(vitem)
    _settle(4)
    grp = next(vitem.child(i) for i in range(vitem.childCount())
               if win._payload(vitem.child(i))[0] == "logic_root")
    win.tree.expandItem(grp)
    _settle(4)
    for i in range(grp.childCount()):
        win.tree.expandItem(grp.child(i))
    _settle(4)
    tgt = None                                         # the NPC talk handler -> the Inspector transcript
    for i in range(grp.childCount()):
        for j in range(grp.child(i).childCount()):
            if win._payload(grp.child(i).child(j))[2] == "logic_n:2:3":
                tgt = grp.child(i).child(j)
    assert tgt is not None, "the demo field's talk handler row must exist"
    win.tree.setCurrentItem(tgt)
    _settle(6)
    if state == "panel":
        win._open_editor("GLADE", "logic_node", "logic_n:2:3")
        win.tabs.setCurrentWidget(win.doc_scroll)      # the Editor sub-tab (a campaign open lands on Map)
        _settle(6)
    _grab(ctx, f"script-{state}", win)
    _grab(ctx, f"script-{state}-tree", win.tree)
    _close(win)


BEHAVIOR_STATES = ("guide", "bare", "wizard", "branchwiz", "doc", "compiled", "edit",
                   "stage", "sweep", "siege", "sim")

TRACE_STATES = ("bare", "traced", "contacts", "regions")


def snap_trace(ctx: _Ctx, state: str) -> None:
    """The Trace tab (click-authoring Rungs 1+2+4): the empty on-ramp ('bare' — the teach caption
    + the bare canvas frame with its horizon), the synthetic proof room loaded with a traced
    floor polygon and its +48u outset ring ('traced'), that room with the PILLAR marked as a
    foreground cut-out at its in-game-proven contact (230,320) -> z 1073 ('contacts' — the strip
    + the anchored marker), or the Regions tool with a drawn gateway + a law-warned event zone
    ('regions'). The photo + polygon come from test_imagefield's _paint_room — ONE owner for the
    fixture art (kit-painted, zero Square-Enix bytes)."""
    if state not in TRACE_STATES:
        raise ValueError(f"unknown trace state {state!r} (know: {', '.join(TRACE_STATES)})")
    win = _make_win(ctx)
    win.tabs.setCurrentWidget(win.trace_doc)
    _settle(4)
    if state in ("traced", "contacts", "regions"):
        import importlib.util
        p = REPO / "ff9mapkit" / "ff9mapkit" / "tests" / "test_imagefield.py"
        spec = importlib.util.spec_from_file_location("_trace_fixture", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        root = _SCRATCH / "trace_demo"                 # stable path -- mkdtemp breaks pixel-diffing
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        photo, floor = mod._paint_room(root)
        win.trace_doc.load_image(photo)
        win.trace_doc.canvas._commit_floor([(float(x), float(y)) for x, y in floor])
        _settle(6)
    if state == "contacts":
        from PIL import Image
        cut = _SCRATCH / "trace_demo" / "pillar_snip.png"
        im = Image.new("RGBA", (40, 180), (68, 60, 82, 255))   # a kit-painted object SNIP: the
        im.save(cut)                                           # positionable-cut-out idiom
        td = win.trace_doc
        td._ask_cutout = lambda: str(cut)                    # the attach dialog, answered
        td.fg_btn.setChecked(True)
        td._on_contact(230.0, 320.0)                         # the proven pillar contact -> z 1073
        _settle(6)
    if state == "regions":
        from ff9mapkit import imagefield as _if
        td = win.trace_doc
        td.tools.set_current("regions")                      # the rung-4 tool, on the photo lane
        cam = td.canvas.camera()
        td.gw_to.setValue(4005)
        td._on_region_drawn([_if.click_to_world(cam, p) for p in
                             [(40.0, 400.0), (150.0, 400.0), (150.0, 430.0), (40.0, 430.0)]])
        td.rkind_btns["event"].setChecked(True)
        td.ev_msg.setText("It creaks underfoot.")
        td._on_region_drawn([_if.click_to_world(cam, p) for p in   # a bowtie: the spill wash
                             [(220.0, 380.0), (330.0, 380.0), (220.0, 430.0), (330.0, 430.0)]])
        _settle(6)
    _grab(ctx, f"trace-{state}", win)
    _grab(ctx, f"trace-{state}-canvas", win.trace_doc.canvas)   # the SUBJECT, not just the window
    _close(win)


PLACE_STATES = ("bare", "fork", "refused", "regions")


def snap_place(ctx: _Ctx, state: str) -> None:
    """The Place tab (click-authoring Rung 3c/4): the empty on-ramp ('bare'), a fork member with
    a loaded surface + placed content ('fork' — kit-painted stand-in art + a synthetic flat quad,
    so the snap needs no install; the REAL donor surface arrives through the user's own Load),
    a bundled example refusing placement outright ('refused'), or the Regions tool with all
    three zone-law renders on the art ('regions' — a gateway's walk-out edge, a TREADQUAD
    overlap warn, and a non-convex quad's over-trigger spill wash)."""
    if state not in PLACE_STATES:
        raise ValueError(f"unknown place state {state!r} (know: {', '.join(PLACE_STATES)})")
    # 'fork' deliberately ends with an UNSAVED placed prop, so win.close() would fire the
    # unsaved-changes QMessageBox -- the drift surfaces' silent native hang. Same cure.
    with _no_modals():
        _snap_place_body(ctx, state)


def _snap_place_body(ctx: _Ctx, state: str) -> None:
    win = _make_win(ctx)
    if state == "refused":
        ex = REPO / "ff9mapkit" / "examples" / "vivi-hut" / "hut_int.field.toml"
        win.tabs.setCurrentWidget(win.place_doc)
        win.place_doc.show_field("hut_int", {"verbatim_eb": {"donor": 351}}, ex)
        _settle(4)
    elif state in ("fork", "regions"):
        import importlib.util
        p = REPO / "ff9mapkit" / "ff9mapkit" / "tests" / "test_imagefield.py"
        spec = importlib.util.spec_from_file_location("_place_fixture", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        root = _SCRATCH / "place_demo"                 # stable path -- mkdtemp breaks pixel-diffing
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        photo, _floor = mod._paint_room(root)
        pf = root / "PLACEDEMO.field.toml"
        pf.write_text('[field]\nid = 4702\nname = "PLACEDEMO"\narea = 11\nsource_field = 351\n\n'
                      '[[npc]]\nname = "Mira"\npreset = "vivi"\ndialogue = "..."\npos = [-120, 1100]\n',
                      encoding="utf-8")
        assert win.open_field(pf), "the demo fork must open"
        win.tabs.setCurrentWidget(win.place_doc)
        pd = win.place_doc
        from ff9mapkit.scene import guide as _guide
        quad = [((-900.0, 0.0, 500.0), (900.0, 0.0, 500.0), (900.0, 0.0, 2600.0)),
                ((-900.0, 0.0, 500.0), (900.0, 0.0, 2600.0), (-900.0, 0.0, 2600.0))]
        pd._bundles[(351, 0)] = {"donor": 351, "cam_index": 0, "n_cams": 1,
                                 "cam": _guide.make_camera(26.0, 3000.0, fov_x_deg=42.0),
                                 "png": str(photo), "tris": quad, "floors": [0, 0]}
        pd._apply_bundle(pd._bundles[(351, 0)], refit=True)
        if state == "regions":
            pd.tools.set_current("regions")            # the rung-4 tool, through its own strip
            pd.gw_to.setValue(4005)
            pd._on_region_drawn([(-800.0, 1600.0), (-100.0, 1600.0),  # a CLEAN convex gateway:
                                 (-100.0, 2400.0), (-800.0, 2400.0)])  # accent, edge + chevron
            pd._on_region_drawn([(400.0, 1900.0), (900.0, 1900.0),   # overlaps the event below ->
                                 (900.0, 2600.0), (400.0, 2600.0)])   # the TREADQUAD warn pair
            pd.rkind_btns["event"].setChecked(True)
            pd._on_region_drawn([(100.0, 1600.0), (800.0, 1600.0),
                                 (800.0, 2200.0), (100.0, 2200.0)])
            pd._on_region_drawn([(-50.0, 1000.0), (300.0, 600.0),    # a notch-in-hull dart ->
                                 (300.0, 1200.0), (-400.0, 1200.0)])  # the over-trigger wash
        else:
            pd.mode_btns["prop"].setChecked(True)      # place a prop through the REAL op path so the
            pd._apply_hit({"xz": (300.0, 1700.0), "pos": (300.0, 0.0, 1700.0),   # status + marker are true
                           "floor": 0, "tri": 0, "s": 1.0})
        _settle(6)
    else:
        win.tabs.setCurrentWidget(win.place_doc)
        _settle(4)
    _grab(ctx, f"place-{state}", win)
    _grab(ctx, f"place-{state}-canvas", win.place_doc.canvas)   # the SUBJECT, not just the window
    _close(win)

FLOORPLAN_STATES = ("bare", "rooms", "door", "refused", "reclaimed")

# The snap's own plan, in PLAN-frame world units: an L of three abutting rooms. Deterministic and
# kit-authored (zero Square-Enix bytes, no install needed -- the composer is pure math).
_FP_A = [(-1200, -800), (0, -800), (0, 800), (-1200, 800)]
_FP_B = [(0, -800), (1200, -800), (1200, 800), (0, 800)]
_FP_C = [(0, 800), (1200, 800), (1200, 2000), (0, 2000)]


def _fp_draw(canvas, pts):
    """Draw one room through the canvas's own click seam and CLOSE it on the first corner."""
    for p in pts:
        canvas.click_world(*p)
    canvas.click_world(*pts[0])


def snap_floorplan(ctx: _Ctx, state: str) -> None:
    """The Floorplan tab (click-authoring Rung 6c): the empty on-ramp with its compass and the
    teach line ('bare'), three abutting rooms drawn in Rooms mode with their footprints and the
    entry mark ('rooms'), the Doors tool with one DECLARED door plus the shared wall still on
    offer ('door'), or the live gate REFUSING a door shallower than 2*R_WALK -- the door and both
    its rooms in the error colour, the reason listed verbatim, Compose off ('refused').

    'reclaimed' is 'refused' with the chart/findings rail dragged shut -- the author having read the
    refusal and asked for the drawing back. It is the reason the rail exists and the only state that
    shows what it buys (at CALIBRE 150 the chart goes 127 -> 245px), so it is pinned: a state that
    cannot be reproduced cannot be reviewed. The status line changes with it, because "see the list
    below" is a lie once the list is shut.

    'refused' shows the DOOR class deliberately. ``compose`` raises per STAGE, so a bad room
    OUTLINE never reaches the door gate at all and a plan carrying both would render only the room
    half; that half (a self-intersecting outline -> G1) is fenced in
    tests/test_workspace_floorplan.py, and this is the paint that needed an eye on it.

    The plan is kit-authored world geometry and the composer is pure math, so no install and no
    templates are needed; the gate verdict is computed on the SYNC lane (production judges on a
    worker thread behind a 140ms debounce, which a harness cannot idle through)."""
    if state not in FLOORPLAN_STATES:
        raise ValueError(f"unknown floorplan state {state!r} (know: {', '.join(FLOORPLAN_STATES)})")
    win = _make_win(ctx)
    doc = win.floorplan_doc
    doc.id_box.setText("30500")                        # the scratch run this lane's pin names --
    #                                                    BEFORE the show, so the doc's own
    #                                                    measure-after-polish pass re-homes the
    #                                                    caret (a caret-scrolled box reads "0500")
    win.tabs.setCurrentWidget(win.floorplan_doc)
    _settle(4)
    if state != "bare":
        doc.name_box.setText("SUNKEN")
        for poly in (_FP_A, _FP_B, _FP_C):
            _fp_draw(doc.canvas, poly)
    if state in ("door", "refused", "reclaimed"):
        doc.tools.set_current("doors")
        doc.judge_now(sync=True)
        doc.canvas.click_world(0, 0)                   # declare the ROOM1-ROOM2 wall
    if state in ("refused", "reclaimed"):
        doc.depth.setValue(100)                        # under DEPTH_MIN: refused, never clamped
    doc.judge_now(sync=True)
    _settle(6)
    if state == "reclaimed":
        # through moveSplitter, not setSizes: moveSplitter is what emits splitterMoved, and the
        # recorded CHOICE is the whole difference between a drag and the app's own arithmetic.
        doc.split.moveSplitter(sum(doc.split.sizes()), 1)
        _settle(6)
    _settle(6)                                     # the viewport must be SETTLED before the fit:
    doc.canvas.fit()                               # fit() measures the live viewport
    _settle(4)
    _grab(ctx, f"floorplan-{state}", win)
    _grab(ctx, f"floorplan-{state}-canvas", doc.canvas)   # the SUBJECT, not just the window
    _close(win)


_BARE_TOML = """\
[field]
name = "BARE"
id = 30990

[player]
spawn = [0, 0]

[[npc]]
name = "watch"
pos = [200, 100]

[[npc]]
name = "ward"
pos = [-200, 100]
"""


def _load_behavior_demo():
    """The synthetic [behavior] demo field's builder lives in tests/test_behaviordoc.py -- ONE
    owner for the fixture TOML (kit-authored, zero Square-Enix bytes; its dry-compile is pinned
    by that suite), loaded by path because tests/ is not a package."""
    import importlib.util
    p = REPO / "ff9mapkit" / "tests" / "test_behaviordoc.py"
    spec = importlib.util.spec_from_file_location("_behavior_demo_fixture", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def snap_behavior(ctx: _Ctx, state: str) -> None:
    """The Behavior tab: its no-field front door ('guide'), the ACTION guide on a bare
    field ('bare' -- the three-route teach), the archetype stamp wizard ('wizard'), the
    demo field's cast + ladder + stage ('doc'), the dry-compile instruments filled
    ('compiled'), the branch editor open ('edit'), stage-edit mode with its drag
    handles + guides ('stage'), the walkability sweep's painted verdicts over the
    demo's REAL synthetic walkmesh ('sweep'), the [siege] read-only face ('siege'),
    or the tick-stepper 3 s in ('sim')."""
    if state not in BEHAVIOR_STATES:
        raise ValueError(f"unknown behavior state {state!r} (know: {', '.join(BEHAVIOR_STATES)})")
    win = _make_win(ctx)
    if state == "guide":
        win.tabs.setCurrentWidget(win.behavior_doc)
        _settle(4)
        _grab(ctx, "behavior-guide", win)
        _close(win)
        return
    demo = _load_behavior_demo()
    root = _SCRATCH / "behavior_demo"                  # stable path -- mkdtemp breaks pixel-diffing
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    if state in ("bare", "wizard"):                    # a field with npcs but NO [behavior]:
        root.mkdir(parents=True, exist_ok=True)        # the action guide / the wizard's ground
        toml = root / "field.toml"
        toml.write_text(_BARE_TOML, encoding="utf-8")
    elif state == "siege":                             # the READ-ONLY generated view: test_siege's
        import copy as _copy                           # own RAW through editor.model.dumps
        import importlib.util as _ilu
        from ff9mapkit.editor import model as _model
        sp = _ilu.spec_from_file_location(
            "_siege_fixture", REPO / "ff9mapkit" / "ff9mapkit" / "tests" / "test_siege.py")
        sm = _ilu.module_from_spec(sp)
        sp.loader.exec_module(sm)
        root.mkdir(parents=True, exist_ok=True)
        toml = root / "field.toml"
        toml.write_text(_model.dumps(
            {"field": {"name": "REDOUBT", "id": 30991}, "player": {"spawn": [0, -600]},
             "siege": _copy.deepcopy(sm.RAW)}), encoding="utf-8")
    else:
        toml = demo.make_behavior_field(root)
    assert win.open_field(toml), "the behavior demo field must open"
    win.tabs.setCurrentWidget(win.behavior_doc)        # the shell feed runs on tab show
    _settle(6)
    if state in ("wizard", "branchwiz"):               # the stamp wizards, grabbed as their
        from ff9mapkit.workspace.behaviordoc import ArchetypeWizard, BranchWizard   # own
        if state == "wizard":                          # subjects (built directly -- exec()
            dlg = ArchetypeWizard(win.behavior_doc.pal, win.behavior_doc._raw, win)
        else:                                          # lives only in the modal seam)
            dlg = BranchWizard(win.behavior_doc.pal, win.behavior_doc._raw,
                               win.behavior_doc._selected_unit or "watchman", win)
            dlg.list.setCurrentRow(4)                  # chase-on-sight: target row + preview
        dlg.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        dlg.show()
        _settle(4)
        _grab(ctx, f"behavior-{state}", dlg)
        dlg.reject()
        _close(win)
        return
    if state == "compiled":
        win.behavior_doc.compile_now(sync=True)        # the deterministic lane; production compiles
        _settle(4)                                     # on a worker behind the user's own click
    elif state == "edit":
        win.behavior_doc._edit_branch(4)               # the chase row open in the branch editor
        _settle(4)
    elif state == "stage":
        win.behavior_doc.edit_btn.setChecked(True)     # handles + compass + ring grips
        _settle(4)
    elif state == "sweep":
        win.behavior_doc.edit_btn.setChecked(True)
        win.behavior_doc.sweep_now(sync=True)          # the REAL lane over the fixture's own
        _settle(4)                                     # walkmesh sidecar -- verdicts, not props
    elif state == "sim":
        win.behavior_doc.sim_btn.setChecked(True)      # rung E1: the tick-stepper's strip +
        win.behavior_doc._sim_show(90)                 # ghosts + ▶ sweep, 3 s into the timeline
        _settle(4)
    _grab(ctx, f"behavior-{state}", win)
    if state in ("stage", "sweep", "sim"):             # the canvas is the subject -- grab IT too
        _grab(ctx, f"behavior-{state}-canvas", win.behavior_doc.canvas)
    _close(win)


CUTSCENE_STATES = ("guide", "doc", "editor", "settings", "storyboard", "staged", "narration")


def _load_cutscene_demo():
    """The GLEN fixture's builder lives in tests/test_cutscenedoc.py -- ONE owner (kit-authored,
    zero Square-Enix bytes; a genuinely ROUTED walk), loaded by path because tests/ is not a
    package -- the behavior demo's own pattern."""
    import importlib.util
    p = REPO / "ff9mapkit" / "tests" / "test_cutscenedoc.py"
    spec = importlib.util.spec_from_file_location("_cutscene_demo_fixture", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def snap_cutscene(ctx: _Ctx, state: str) -> None:
    """The Cutscene tab (the redesign): the no-field front door ('guide'), the demo dispatch's
    rail + ladder + stage ('doc'), the step editor open on the attributed say with the pacing
    drawer expanded ('editor'), the scene-settings card ('settings'), the beat storyboard over
    the ROUTED walk ('storyboard'), a staging verdict painted on the failing leg ('staged'),
    and the narration scene's face ('narration')."""
    if state not in CUTSCENE_STATES:
        raise ValueError(f"unknown cutscene state {state!r} (know: {', '.join(CUTSCENE_STATES)})")
    win = _make_win(ctx)
    if state == "guide":
        win.tabs.setCurrentWidget(win.cutscene_doc)
        _settle(4)
        _grab(ctx, "cutscene-guide", win)
        _close(win)
        return
    demo = _load_cutscene_demo()
    root = _SCRATCH / "cutscene_demo"                  # stable path -- mkdtemp breaks pixel-diffing
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    toml = demo.make_cutscene_field(root)
    assert win.open_field(toml), "the cutscene demo field must open"
    win.tabs.setCurrentWidget(win.cutscene_doc)        # the shell feed runs on tab show
    _settle(6)
    doc = win.cutscene_doc
    if state == "editor":
        doc._edit_step(2)                              # the attributed say: text box + preview
        doc.editor.extras.toggle_button.click()        # the pacing drawer is the subject
        _settle(4)
    elif state == "settings":
        doc.settings_btn.setChecked(True)
        _settle(4)
    elif state == "storyboard":
        doc.stage_now(sync=True)                       # warm mesh: the walk shows ROUTED
        doc.board_btn.setChecked(True)
        doc._show_beat(0)
        _settle(4)
    elif state == "staged":
        doc._steps()[0]["walk"] = [2000, 2000]         # an in-memory stall; nothing is saved
        doc._render()
        doc.stage_now(sync=True)                       # the verdict paints on the failing leg
        _settle(4)
    elif state == "narration":
        doc.rail.setCurrentRow(1)
        _settle(4)
    _grab(ctx, f"cutscene-{state}", win)
    if state in ("doc", "storyboard", "staged"):       # the canvas is the subject -- grab IT too
        _grab(ctx, f"cutscene-{state}-canvas", doc.canvas)
    _close(win)


CONSOLE_STATES = ("log", "find", "miss", "jobs")


def _seed_console(win) -> list[dict]:
    """A realistic MULTI-JOB session log + its job index, pinned -- never this machine's real jobs.

    Written through ``win._log`` in the same four registers ``run_job`` uses (head / echo / body / trace) so
    the snap records the real ink, and the head strings are built the same way run_job builds them. Fixed
    timestamps: a random clock would break pixel-diffing the most prominent line in the panel (round 9's
    mkdtemp lesson).
    """
    session = [("09:41:02", "Build field 4003", 0,
                ["scene: camera k=14 ok", "wrote build/4003/scene.bgx", "wrote build/4003/field.eb"]),
               ("09:41:20", "Deploy field 4003", 0,
                ["copying to FF9CustomMap/StreamingAssets", "wrote revert_deploy_4003.py", "deploy ok"]),
               ("09:42:07", "Import field 354", 1,
                ["reading p0data7.bin", "Traceback (most recent call last):",
                 "  File \"ff9mapkit/import.py\", line 88, in scan", "KeyError: 'walkmesh'"])]
    idx = []
    for stamp, subject, code, lines in session:
        head = f"[{stamp}] {subject}"
        idx.append({"head": head, "time": stamp, "subject": subject, "code": code, "stopped": False})
        win._log(head, "head")
        win._log(f"$ -m ff9mapkit {subject.split()[0].lower()} examples/showcase", "echo")
        for ln in lines:
            win._log(ln, "trace" if win._TRACE_ANCHOR in ln else "body")
    win._job_index = idx
    return idx


def snap_console(ctx: _Ctx, state: str) -> None:
    """The console read as a DOCUMENT: the multi-job log, the find bar's two highlight tiers, the no-match
    state, and the Jobs menu."""
    if state not in CONSOLE_STATES:
        raise ValueError(f"unknown console state {state!r} (know: {', '.join(CONSOLE_STATES)})")
    win = _make_win(ctx)
    _seed_console(win)
    win._raise_console()
    if state == "find":
        win._open_find("wrote")
    elif state == "miss":
        win._open_find("walkmsh")            # a typo'd needle -> the 'no matches' tier
    _settle(8)
    if state == "jobs":
        win._fill_jobs_menu()
        _grab(ctx, "console-jobs-menu", win._jobs_menu)
    # The console body is the subject, so grab IT as well as the window: the panel is ~200px of a 850px
    # shot and a highlight tier judged from the downscaled whole is the 'sample the button, don't squint at
    # the screenshot' mistake this study already paid for.
    _grab(ctx, f"console-{state}", win)
    _grab(ctx, f"console-{state}-panel", win.console_panel)
    _close(win)


def snap_form(ctx: _Ctx, state: str) -> None:
    """The field editor's LOGIC FORMS -- the surface that had no pinned snap at all, which is how a field
    could ship a placeholder ("a encounter name or id") that its own parser refused.

    Each state opens a writable copy of the boletta example with the section under test appended, selects
    that section's tree row through the shipped jump (``_goto_tree_section``), and grabs the FORM, not the
    window: a hint judged inside an 850px screenshot is the downscaled-review mistake. Guided mode is forced
    OFF here so the 'advanced' fields (the NPC model) are inline instead of inside a collapsed drawer -- a
    field hidden behind a disclosure cannot be read in a still.
    """
    if state not in FORM_STATES:
        raise ValueError(f"unknown form state {state!r} (know: {', '.join(FORM_STATES)})")
    body = {
        # blank scene -> the PLACEHOLDER is the subject (it must not promise a name the parser refuses)
        "encounter": '[encounter]\nfreq = 64\n',
        # a battle-scene NAME: legal TOML since the build resolves it -- it must render with NO error notice
        "encounter-named": '[encounter]\nscene = "BSC_EF_R007"\nfreq = 64\n',
        # the id-only catalogs (song) must say "id", not "name or id" -- the honest half of the same rule
        "music": "[music]\nloop_start = 0\n",
        # [[npc]] model takes an exact GEO name too (build.resolve_npc_model), same defect, same spec file
        "npc": None,
        # the spine tutorials' teaching subjects (S3/S4): a filled gateway + a named-flag chest
        "gateway": ('[[gateway]]\nto = 30002\nentrance = 0\n'
                    'zone = [[300, -400], [700, -400], [700, -800], [300, -800]]\n'),
        "chest": ('[[chest]]\npos = [0, 80]\nitem = ["Potion", 1]\nflag = "chest_potion"\n\n'
                  '[[flag]]\nname = "chest_potion"\nindex = 8720\n'),
        # post-redesign: the tree node is a SUMMARY + the door to the Cutscene tab -- the subject
        # here is the summary card itself (per-scene lines + the accented "Open the Cutscene tab").
        # The step-editing surfaces are the cutscene:* snaps.
        "cutscene": ('[cutscene]\nonce = true\nsteps = [\n'
                     '  { say = "The hut is silent..." },\n  { wait = 30 },\n'
                     '  { say = "...for now." },\n]\n'),
        # THE DISPATCH through the summary: every scene named with its gate (the old form edited
        # scene #0 and hid the rest -- the summary must NOT repeat that lie by omission).
        "cutscene-dispatch": (
            '[[cutscene]]\nactors = ["Boletta"]\nrequires_scenario = 100\nset_scenario = 200\n'
            'steps = [\n  { say = "You came back." },\n  { walk = [0, 80], actor = "Boletta" },\n]\n\n'
            '[[cutscene]]\nactors = ["Boletta"]\nrequires_scenario = 300\n'
            'steps = [\n  { say = "It is finished." },\n]\n'),
    }[state]
    src = REPO / "ff9mapkit" / "examples" / "boletta"
    assert src.is_dir(), "cannot find the boletta example -- snap void"
    dst = _SCRATCH / f"form_{state}"
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)                     # NEVER the bundled example: a form Save rewrites the oracle
    proj = dst / "boletta.field.toml"
    if body:
        proj.write_text(proj.read_text(encoding="utf-8") + "\n" + body, encoding="utf-8")
    elif state == "npc":                          # the example's NPC by GEO NAME instead of its numeric id
        txt = proj.read_text(encoding="utf-8")
        assert "model = 6300" in txt, "boletta's npc no longer carries `model = 6300` -- snap void"
        proj.write_text(txt.replace("model = 6300", 'model = "GEO_NPC_F0_BAR"'), encoding="utf-8")
    guided = ctx.guided
    ctx.guided = False                            # advanced fields inline -- a collapsed drawer is unreadable
    try:
        win = _make_win(ctx)
        assert win.open_field(proj), f"form:{state}: open_field refused the copy -- snap void"
        sect = state.split("-")[0]
        if sect in ("npc", "gateway", "chest"):           # array tables: the group header has no
            win._goto_tree_section("GLADE", sect)         # form, select the ENTRY row
            win._select_object("GLADE", f"{sect}:0")
            assert win._payload(win.tree.currentItem())[2] == f"{sect}:0", \
                f"form:{state}: never reached the {sect} row"
        else:
            win._goto_tree_section("GLADE", sect)
        _settle(6)
        _grab(ctx, f"form-{state}", win.doc_host)   # the document BODY, not the window (read the hints, not a thumb)
        _close(win)
    finally:
        ctx.guided = guided


# The tab -> Workspace-attribute map, module-level so docsite/shots.py (the Manual's screenshot
# job) can open the same surfaces without re-owning the mapping.
TAB_ATTRS = {"build": "build_deploy", "import": "import_field",
             "models": "models_doc", "battle": "battle", "story": "story_state",
             "items": "item_equip"}


def snap_tab(ctx: _Ctx, tab: str) -> None:
    if tab == "coop":
        # tab:coop unpinned rendered THIS machine's real [Netsync] state -- including the developer's
        # real SessionCode painted into the code field and saved into the PNG record. The coop:<state>
        # surfaces own this tab with every input pinned.
        print("  tab:coop is pinned-only -- use coop:<state> (see --list)")
        return
    if tab == "world":
        print("  tab:world is owned by world:<state> (guide | nogame | atlas -- see --list)")
        return
    attr = TAB_ATTRS[tab]
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


def _open_campaign_newgame(win) -> None:
    """Open BuildDoc's named 'a campaign deploy will wipe your New Game entry' 3-button confirm with a
    fabricated plan + casualty id, so the harness can grab a surface that only appears when a live New-Game
    override exists on the machine."""
    from types import SimpleNamespace
    bd = win.build_deploy
    bd.plan = SimpleNamespace(name="Demo Campaign", members=[0, 1, 2], mod_folder="FF9CustomMap")
    bd._confirm_campaign_deploy(4100, "Reach each screen in-game via ~ -> Warp.")


def _child_named(root, cls, name):
    """One widget by its ACCESSIBLE NAME -- the handle a form's Browse buttons carry (they all read
    "Browse…"). Raises rather than returning None: a snap that silently found no opener is the
    dead-opener incident this file already paid for once (`on_fork_battle` behind a hasattr guard)."""
    for w in root.findChildren(cls):
        if w.accessibleName() == name:
            return w
    raise AssertionError(f"no {cls.__name__} named {name!r} on this surface -- snap void")


def _anim_field_project(pin) -> Path:
    """A writable boletta copy whose NPC wears the PINNED model and whose cutscene step is an
    ANIMATION on it -- so both animation Browse call sites open scoped to a rig whose frames the pin
    seeded (an unscoped picker would photograph an empty list and prove nothing)."""
    src = REPO / "ff9mapkit" / "examples" / "boletta"
    assert src.is_dir(), "cannot find the boletta example -- snap void"
    dst = _SCRATCH / "form_anim"
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)                     # NEVER the bundled example: a form Save rewrites the oracle
    proj = dst / "boletta.field.toml"
    txt = proj.read_text(encoding="utf-8")
    assert "model = 6300" in txt, "boletta's npc no longer carries `model = 6300` -- snap void"
    txt = txt.replace("model = 6300", f'model = "{pin.geo}"')
    txt += ('\n[cutscene]\nactors = ["Boletta"]\nsteps = [ { animation = "%s" } ]\n'
            % pin.label)
    proj.write_text(txt, encoding="utf-8")
    return proj


def _snap_anim_dialog(ctx: _Ctx, key: str) -> None:
    """The two animation pickers, opened through their REAL call sites (a bare _make_win has no open
    field, so a hand-called constructor would photograph a surface no user can reach):

      * ``anim-picker``    -- the CUTSCENE step editor's Browse (the DOC tab, post-redesign), on an
        `animation` step whose actor is the field's own NPC (CutsceneDoc -> shell._actor_model_hint);
      * ``animset-picker`` -- the [[npc]] form's `anims` Browse (forms_qt's browse closure ->
        shell._pick's early return).

    Wrapped in _pin_anim_cache so the gesture picker's preview pane paints a REAL frame from a warm
    cache instead of "rendering…".
    """
    from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton
    from ff9mapkit.editor import forms as _forms
    guided = ctx.guided
    ctx.guided = False                            # `anims` is an advanced field: a collapsed drawer has no button
    with _pin_anim_cache() as pin:
        proj = _anim_field_project(pin)
        win = _make_win(ctx)
        win.model_thumbs.hold()                   # the Models tab's cold refill must not race the grab
        try:
            assert win.open_field(proj), f"dlg-{key}: open_field refused the copy -- snap void"
            with _grab_next_dialog(ctx, f"dlg-{key}") as g:
                if key == "animset-picker":
                    win._goto_tree_section("GLADE", "npc")
                    win._select_object("GLADE", "npc:0")
                    _settle(6)
                    _child_named(win, QPushButton, "Browse Movement clips").click()
                else:
                    win.tabs.setCurrentWidget(win.cutscene_doc)   # the DOC owns the step editor now
                    _settle(6)
                    doc = win.cutscene_doc
                    if doc._stack.currentWidget() is doc._guide_page:
                        doc._add_scene()               # a scene to host the step (in-memory copy)
                    doc._add_step()
                    _settle(2)
                    combo = _child_named(win, QComboBox, "Cutscene step type")
                    combo.setCurrentIndex(list(_forms.STEP_KIND).index("animation"))
                    _child_named(win, QLineEdit, "Cutscene step value").setText(pin.label)
                    _child_named(win, QComboBox, "Cutscene step actor").setEditText("Boletta")
                    _settle()
                    _child_named(win, QPushButton,
                                 "Browse animations this actor's model can play").click()
            if g.count == 0:
                print(f"  dlg-{key}: NO dialog opened (flow bailed before exec)")
        finally:
            win.model_thumbs.release()
            ctx.guided = guided
        _close(win)


# The dialog -> opener map, module-level so docsite/shots.py + docsite/uiharvest.py open the
# same surfaces without re-owning the flows (the TAB_ATTRS pattern).
DIALOG_OPENERS = {
    "new-field":     lambda w: w.on_new_field(),
    "new-campaign":  lambda w: w.on_new_campaign(),
    "new-journey":   lambda w: w.on_new_journey(),
    "fork-regions":  lambda w: w.import_field.open_region_catalog(),
    "import-fields": lambda w: w.import_field.on_find(),
    "setup":         lambda w: w._open_setup(),
    "prefs":         lambda w: w._open_preferences(),
    "about":         lambda w: w._open_about(),
    "concept-map":   lambda w: w._show_concept_map(),
    "infohub":       lambda w: w._open_catalog(),
    "updates":       lambda w: w._open_update_dialog(),
    # the real opener is _fork_dialog (the first cut guessed `on_fork_battle` behind a hasattr guard,
    # which made this surface permanently, silently dead -- caught by the round's adversarial review)
    "fork-battle":   lambda w: w.battle._fork_dialog(),
    # the named 3-button 'a campaign deploy will wipe your New Game entry' confirm -- fabricate a plan
    # + a casualty so the modal has something to name (BuildDoc._confirm_campaign_deploy).
    "campaign-newgame": _open_campaign_newgame,
}


def snap_dialog(ctx: _Ctx, key: str) -> None:
    if key in ("anim-picker", "animset-picker"):
        return _snap_anim_dialog(ctx, key)
    with _pin_setup_state(game=True, templates=True):
        win = _make_win(ctx)
        with _grab_next_dialog(ctx, f"dlg-{key}") as g:
            DIALOG_OPENERS[key](win)
        if g.count == 0:
            print(f"  dlg-{key}: NO dialog opened (flow bailed before exec)")
        _close(win)


FORM_STATES = ("encounter", "encounter-named", "music", "npc", "gateway", "chest", "cutscene",
               "cutscene-dispatch")
HOME_STATES = ("fresh", "midway", "ready", "veteran", "open")
TABS = ("build", "import", "coop", "models", "battle", "story", "items")
DIALOGS = ("new-field", "new-campaign", "new-journey", "fork-regions", "import-fields", "setup", "prefs",
           "about", "concept-map", "infohub", "updates", "fork-battle", "campaign-newgame",
           "anim-picker", "animset-picker")


def all_surfaces() -> list[str]:
    return ([f"home:{s}" for s in HOME_STATES] + [f"tab:{t}" for t in TABS]
            + [f"dlg:{d}" for d in DIALOGS] + [f"coop:{s}" for s in COOP_STATES]
            + [f"map:{s}" for s in MAP_STATES] + [f"world:{s}" for s in WORLD_STATES]
            + [f"models:{s}" for s in MODEL_STATES]
            + [f"console:{s}" for s in CONSOLE_STATES]
            + [f"drift:{s}" for s in DRIFT_STATES]
            + [f"script:{s}" for s in SCRIPT_STATES]
            + [f"behavior:{s}" for s in BEHAVIOR_STATES]
            + [f"cutscene:{s}" for s in CUTSCENE_STATES]
            + [f"trace:{s}" for s in TRACE_STATES]
            + [f"place:{s}" for s in PLACE_STATES]
            + [f"floorplan:{s}" for s in FLOORPLAN_STATES]
            + [f"form:{s}" for s in FORM_STATES])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("surfaces", nargs="*", help="home:<state> | tab:<name> | dlg:<name> | all")
    ap.add_argument("--theme", default="mist", help="palette key (dark/light/mist/nord/...)")
    ap.add_argument("--scale", type=int, default=100, choices=(100, 110, 125, 150))
    ap.add_argument("--guided", default="guided", choices=("guided", "full"))
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=850)
    ap.add_argument("--out", default=str(HERE / "scroll_out" / "gui_snaps"))
    ap.add_argument("--campaign", default=None,
                    help="map:* surfaces: the campaign.toml to open (default: examples/stolen-ember)")
    ap.add_argument("--thumb-source", default=None,
                    help="map:art: a warm thumbs cache dir to copy real_<id>.png art from")
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
            elif kind == "map":
                snap_map(ctx, rest)
            elif kind == "world":
                snap_world(ctx, rest)
            elif kind == "models":
                snap_models(ctx, rest)
            elif kind == "console":
                snap_console(ctx, rest)
            elif kind == "drift":
                snap_drift(ctx, rest)
            elif kind == "script":
                snap_script(ctx, rest)
            elif kind == "behavior":
                snap_behavior(ctx, rest)
            elif kind == "cutscene":
                snap_cutscene(ctx, rest)
            elif kind == "trace":
                snap_trace(ctx, rest)
            elif kind == "place":
                snap_place(ctx, rest)
            elif kind == "floorplan":
                snap_floorplan(ctx, rest)
            elif kind == "form":
                snap_form(ctx, rest)
            else:
                print(f"  unknown surface {s!r} (try --list)")
        except Exception as e:                                        # noqa: BLE001 -- one bad surface
            print(f"  {s}: FAILED -- {type(e).__name__}: {e}")        # must not kill the whole sweep
    print(f"\n{len(ctx.saved)} snap(s) in {ctx.out}")


if __name__ == "__main__":
    main()
