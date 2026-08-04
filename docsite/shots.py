"""shots -- the Manual's "gather screenshots" job: every GUI figure in the docs, regenerated on
demand by the toolkit's own headless harness. After a Workspace reskin or relayout, run this once
and every tutorial figure updates itself.

Built ON tools/gui_snap.py, never beside it: gui_snap owns the harness laws (native Qt only,
pinned prefs, modal stubs, deterministic fixtures) and every surface-state pin; this file only
declares WHICH surfaces the docs show (shots.toml) and adds the two docs-specific mechanisms:

  * WIDGET-ANCHORED ANNOTATIONS -- a callout names a widget by attribute path, resolved to a rect
    AT GRAB TIME and written to a JSON sidecar; the site draws the rings as SVG over the clean
    PNG. A reskin re-anchors every callout on re-run; a widget that VANISHED fails the run loudly
    (that failure is documentation-drift detection working, not an inconvenience).
  * PIN EVERY PAINTED PATH -- a surface that paints a machine path (the Import tab's "Write to:")
    gets that box pinned to a neutral value, or every machine's run diffs in its most prominent
    line.

THE PROVENANCE LAW: committed shot PNGs contain ZERO Square-Enix pixels. Only surfaces on the
allowlist below may appear in shots.toml -- all of them render from kit-authored fixtures, and
this job has no way to pass a real-art thumb source.

Usage (Windows + native Qt -- gui_snap's own law; no game install is read):
  py docsite/shots.py --all              # regenerate every figure into docsite/assets/shots/
  py docsite/shots.py import-fork        # one figure
  py docsite/shots.py --check            # re-render to scratch, report drift vs committed
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ASSETS = HERE / "assets" / "shots"

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# Surfaces the manifest may use. Every gui_snap surface is fixture-pinned, but the docs grow this
# list DELIBERATELY, one review at a time -- an allowlist cannot rot open.
# "cutscene" joined with the doc-tab redesign: its surfaces render the GLEN fixture owned by
# tests/test_cutscenedoc.py -- kit-authored, zero Square-Enix pixels.
ALLOWED_FAMILIES = {"tab", "home", "form", "dlg", "script", "console", "drift", "cutscene"}
# Families the in-process adapter can open (window in hand -> annotations + pins work). The rest
# run black-box through their gui_snap function and cannot carry annotations. Dialog widgets are
# addressed by LABEL (a11y name or rendered text -- dialogs hold no attr paths), the same handle
# gui_snap's _child_named drives them by.
ADAPTER_FAMILIES = {"tab", "home", "dlg"}

THEME_PAIR = {"light": "light", "dark": "mist"}   # the committed pair; the site swaps by theme


def load_manifest(path: Path | None = None) -> dict:
    data = tomllib.loads((path or HERE / "shots.toml").read_text(encoding="utf-8"))
    shots = data.get("shot", {})
    errors = []
    for name, s in shots.items():
        fam = s.get("surface", "").partition(":")[0]
        if fam not in ALLOWED_FAMILIES:
            errors.append(f"{name}: surface family {fam!r} is not on the provenance allowlist")
        if s.get("annotate") and fam not in ADAPTER_FAMILIES:
            errors.append(f"{name}: annotations need an adapter family ({sorted(ADAPTER_FAMILIES)})")
        if s.get("pin") and fam not in ADAPTER_FAMILIES:
            errors.append(f"{name}: pins need an adapter family")
        for a in s.get("annotate", []):
            if "widget" not in a:
                errors.append(f"{name}: an annotation without a widget path")
    if errors:
        raise SystemExit("shots.toml errors:\n  " + "\n  ".join(errors))
    return shots


def kit_version() -> str:
    with open(REPO / "ff9mapkit" / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


# ------------------------------------------------------------------- the harness (import = setup)

def _load_gui_snap():
    """Import tools/gui_snap.py by path. Its module-level side effects ARE the wanted setup:
    scratch-pinned LOCALAPPDATA, native QApplication, thumbs off, offscreen refused."""
    spec = importlib.util.spec_from_file_location("gui_snap", REPO / "tools" / "gui_snap.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gui_snap"] = mod
    spec.loader.exec_module(mod)
    return mod


def _resolve_widget(win, path: str):
    w = win
    for part in path.split("."):
        w = getattr(w, part, None)
        if w is None:
            raise AssertionError(
                f"widget path {path!r} no longer resolves on this surface -- the UI moved; "
                f"update shots.toml (this failure IS the drift alarm)")
    return w


def _ctx(gs, theme: str, shot: dict, out_dir: Path):
    return gs._Ctx(SimpleNamespace(
        theme=theme, scale=int(shot.get("scale", 100)), guided="guided",
        width=int(shot.get("width", 1280)), height=int(shot.get("height", 850)),
        campaign=None, thumb_source=None, out=str(out_dir)))


def render_shot(gs, name: str, shot: dict, theme: str, out_dir: Path) -> dict:
    """One figure, one theme -> PNG + sidecar dict. Adapter families open the window here so
    pins apply and annotation rects resolve; black-box families run their gui_snap function and
    the named take is renamed into place."""
    from PySide6.QtCore import QPoint

    surface = shot["surface"]
    fam, _, state = surface.partition(":")
    png = out_dir / f"{name}_{theme}.png"
    meta = {"shot": name, "surface": surface, "theme": theme,
            "scale": int(shot.get("scale", 100)), "kit_version": kit_version(),
            "theme_pair": THEME_PAIR, "annotations": []}

    if fam in ADAPTER_FAMILIES:
        ctx = _ctx(gs, theme, shot, out_dir)
        if fam == "dlg":
            sys.path.insert(0, str(HERE))
            from uiharvest import capture_next_dialog
            with gs._pin_setup_state(game=True, templates=True):
                win = gs._make_win(ctx)
                got: list[dict] = []
                with capture_next_dialog(gs, lambda d: got.append(
                        _pin_grab_dialog(gs, d, shot, png, QPoint))):
                    gs.DIALOG_OPENERS[state](win)
                assert got, f"{name}: {surface} opened no dialog"
                meta.update(got[0])
                gs._close(win)
        elif fam == "home":
            with gs._pin_setup_state(**gs.HOME_PINS[state]):
                win = gs._make_win(ctx, recent=gs._example_recent()
                                   if state in ("veteran", "open") else None)
                win._refresh_home_status()
                gs._settle(12)
                meta.update(_pin_grab(gs, win, shot, png, QPoint))
        else:                                     # tab:<name>
            win = gs._make_win(ctx)
            if shot.get("open"):
                # A read-only project open so state-dependent controls exist (e.g. the Build
                # tab's In-place radio needs a verbatim fork of a REAL field open -- and no such
                # example can ever be bundled, because a real verbatim fork carries Square-Enix
                # bytes; hence the kit-authored fixture). A grab never saves.
                if shot["open"] == "fixture:verbatim-fork":
                    proj = _fixture_verbatim_fork(gs)
                else:
                    proj = REPO / shot["open"]
                assert win.open_field(proj), f"{name}: open_field refused {proj}"
                win.build_deploy.set_target(str(proj))
                gs._settle(6)
            win.tabs.setCurrentWidget(getattr(win, gs.TAB_ATTRS[state]))
            meta.update(_pin_grab(gs, win, shot, png, QPoint))
    else:
        scratch = Path(tempfile.mkdtemp(prefix="docshot_"))
        ctx = _ctx(gs, theme, shot, scratch)
        fn = {"dlg": "snap_dialog"}.get(fam, f"snap_{fam}")   # gui_snap's one irregular name
        getattr(gs, fn)(ctx, state)
        take = shot.get("take") or f"{fam}-{state}"
        src = scratch / f"{take}_{theme}_{ctx.scale}.png"
        assert src.is_file(), (f"{name}: surface {surface} produced no take {take!r} "
                               f"(have: {[p.name for p in scratch.glob('*.png')]})")
        shutil.copy2(src, png)
        from PySide6.QtGui import QImage
        img = QImage(str(png))
        meta["size"] = [img.width(), img.height()]
    (png.with_suffix(".json")).write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"  {png.name}  {meta['size'][0]}x{meta['size'][1]}"
          + (f"  +{len(meta['annotations'])} note(s)" if meta["annotations"] else ""))
    return meta


def _fixture_verbatim_fork(gs) -> Path:
    """A verbatim fork of a 'real' field, kit-authored: the script-demo fixture's bytes (ONE owner:
    tests/test_workspace_script_tree.py) plus a real-band `donor`, which is all
    `jobs.field_inplace_target` reads. Stable path -- mkdtemp breaks pixel-diffing."""
    demo = gs._load_script_demo()
    root = gs._SCRATCH / "docshot_fork"
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    (root / "GLADE.verbatim_eb.bin").write_bytes(demo.demo_verbatim_eb())
    (root / "GLADE.text.json").write_text(json.dumps({"us": demo.demo_mes_body()}),
                                          encoding="utf-8")
    proj = root / "GLADE.field.toml"
    proj.write_text('[field]\nid = 30100\nname = "GLADE"\narea = 11\n\n'
                    '[verbatim_eb]\ndonor = 351\nbin = "GLADE.verbatim_eb.bin"\n'
                    'text = "GLADE.text.json"\n', encoding="utf-8")
    return proj


def _viewport_clip(w, win, QPoint) -> str | None:
    """The name of the first ancestor scroll viewport that clips any part of `w`, else None.
    Pure geometry (mapTo against each viewport), deliberately not visibleRegion(): paint-derived
    answers are unreliable under WA_DontShowOnScreen (the builddoc _inplace_available lesson)."""
    from PySide6.QtWidgets import QAbstractScrollArea
    p = w.parentWidget()
    while p is not None and p is not win:
        if isinstance(p, QAbstractScrollArea):
            vp = p.viewport()
            t = w.mapTo(vp, QPoint(0, 0))
            if not (0 <= t.x() and 0 <= t.y()
                    and t.x() + w.width() <= vp.width()
                    and t.y() + w.height() <= vp.height()):
                return type(p).__name__ + " viewport"
        p = p.parentWidget()
    return None


def _child_by_label(dlg, label: str, kind: str | None = None):
    """The unique child whose a11y name, text, or placeholder equals `label` -- the dialog
    counterpart of an attr path. `kind` (a class name, e.g. "QLineEdit") disambiguates when one
    label honestly names a pair (a dir row's edit + its Browse button share a caption). Zero
    matches = the drift alarm; still-plural = fix the app's a11y names, not the manifest."""
    from PySide6.QtWidgets import QWidget
    hits = []
    for w in dlg.findChildren(QWidget):
        if kind and type(w).__name__ != kind:
            continue
        names = {getattr(w, "accessibleName", lambda: "")(),
                 getattr(w, "text", lambda: "")() if hasattr(w, "text") else "",
                 getattr(w, "placeholderText", lambda: "")() if hasattr(w, "placeholderText") else ""}
        if label in {n.replace("&", "") for n in names if n}:
            hits.append(w)
    assert hits, f"no dialog control labeled {label!r} -- the UI moved (the drift alarm)"
    assert len(hits) == 1, (f"{len(hits)} controls answer to {label!r} -- add kind= to the "
                            f"manifest entry, or give one an accessibleName in the app")
    return hits[0]


def _pin_grab_dialog(gs, dlg, shot: dict, png: Path, QPoint) -> dict:
    """Pins + annotations + grab for a LIVE dialog (called inside the patched exec)."""
    for pin in shot.get("pin", []):
        w = _child_by_label(dlg, pin["widget"], pin.get("kind"))
        w.blockSignals(True)
        w.setText(pin["text"])
        w.blockSignals(False)
    gs._settle()
    notes = []
    for a in shot.get("annotate", []):
        w = _child_by_label(dlg, a["widget"], a.get("kind"))
        top = w.mapTo(dlg, QPoint(0, 0))
        rect = [top.x(), top.y(), w.width(), w.height()]
        assert 0 <= rect[0] and 0 <= rect[1] \
            and rect[0] + rect[2] <= dlg.width() and rect[1] + rect[3] <= dlg.height(), \
            f"annotation {a['widget']!r} is clipped at {rect} in the dialog"
        clip = _viewport_clip(w, dlg, QPoint)
        assert clip is None, f"annotation {a['widget']!r} is scrolled out of its {clip}"
        notes.append({"widget": a["widget"], "label": a.get("label", ""),
                      "kind": a.get("kind", "ring"), "rect": rect})
    img = dlg.grab().toImage()
    assert img.width() > 50, "grabbed nothing"
    sx = img.width() / dlg.width()
    for n in notes:
        n["rect"] = [round(v * sx) for v in n["rect"]]
    img.save(str(png))
    return {"size": [img.width(), img.height()], "annotations": notes}


def _pin_grab(gs, win, shot: dict, png: Path, QPoint) -> dict:
    """Apply painted-path pins, resolve annotation rects, grab the window, close it."""
    try:
        for pin in shot.get("pin", []):
            if "statusbar" in pin:               # the status bar paints the project path verbatim
                win.statusBar().showMessage(pin["statusbar"])
                continue
            w = _resolve_widget(win, pin["widget"])
            # COSMETIC only: block signals so a pinned text can never re-drive the surface's state
            # (build_deploy.path's textChanged would re-aim the whole tab at the fake path).
            w.blockSignals(True)
            w.setText(pin["text"])
            w.blockSignals(False)
        gs._settle()
        notes = []
        for a in shot.get("annotate", []):
            w = _resolve_widget(win, a["widget"])
            # isVisibleTo, not isVisible: the window renders under WA_DontShowOnScreen, where
            # absolute visibility is unreliable (builddoc's own _inplace_available comment).
            assert w.isVisibleTo(win), \
                f"annotation target {a['widget']} is not visible in this state"
            top = w.mapTo(win, QPoint(0, 0))
            rect = [top.x(), top.y(), w.width(), w.height()]
            # FULL containment, or fail -- in the WINDOW and in EVERY ancestor scroll viewport.
            # Window bounds alone are not enough: a widget below a scroll area's fold still maps
            # to in-window coordinates while the viewport clips its pixels, so the ring points at
            # nothing (the owner caught exactly this on the Build tab's fourth radio).
            assert 0 <= rect[0] and 0 <= rect[1] \
                and rect[0] + rect[2] <= win.width() and rect[1] + rect[3] <= win.height(), \
                (f"annotation target {a['widget']} is clipped at {rect} in a "
                 f"{win.width()}x{win.height()} window -- raise the shot height or drop the note")
            clip = _viewport_clip(w, win, QPoint)
            assert clip is None, \
                (f"annotation target {a['widget']} is scrolled out of its {clip} -- "
                 f"raise the shot height or drop the note")
            notes.append({"widget": a["widget"], "label": a.get("label", ""),
                          "kind": a.get("kind", "ring"), "rect": rect})
        img = win.grab().toImage()
        assert img.width() > 50, "grabbed nothing"
        sx = img.width() / win.width()            # devicePixelRatio: rects live in image coords
        for n in notes:
            n["rect"] = [round(v * sx) for v in n["rect"]]
        img.save(str(png))
        return {"size": [img.width(), img.height()], "annotations": notes}
    finally:
        gs._close(win)


# ------------------------------------------------------------------------------------------ jobs

def run(names: list[str], out_dir: Path) -> None:
    shots = load_manifest()
    unknown = [n for n in names if n not in shots]
    if unknown:
        raise SystemExit(f"unknown shot(s): {', '.join(unknown)} (have: {', '.join(sorted(shots))})")
    out_dir.mkdir(parents=True, exist_ok=True)
    gs = _load_gui_snap()
    for name in names:
        shot = shots[name]
        for theme in shot.get("themes", list(THEME_PAIR.values())):
            render_shot(gs, name, shot, theme, out_dir)
    print(f"{len(names)} shot(s) x themes -> {out_dir}")


def check() -> int:
    """Re-render everything to scratch IN A FRESH PROCESS (a warm process is not a clean room)
    and byte-compare against the committed assets."""
    scratch = Path(tempfile.mkdtemp(prefix="docshot_check_"))
    r = subprocess.run([sys.executable, str(HERE / "shots.py"), "--all", "--out", str(scratch)],
                       cwd=str(REPO))
    if r.returncode:
        return r.returncode
    drift = []
    for f in sorted(scratch.glob("*.png")):
        committed = ASSETS / f.name
        if not committed.is_file():
            drift.append(f"{f.name}: not committed")
        elif committed.read_bytes() != f.read_bytes():
            drift.append(f"{f.name}: pixels drifted")
    for f in sorted(ASSETS.glob("*.png")):
        if not (scratch / f.name).is_file():
            drift.append(f"{f.name}: committed but no longer produced")
    if drift:
        print("DRIFT:\n  " + "\n  ".join(drift))
        print("(a deliberate UI change? re-run `py docsite/shots.py --all` and commit the diff)")
        return 1
    print(f"check clean: {len(list(ASSETS.glob('*.png')))} committed PNG(s) reproduce exactly")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("names", nargs="*", help="shot names from shots.toml")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=str(ASSETS))
    args = ap.parse_args()
    if args.check:
        raise SystemExit(check())
    names = sorted(load_manifest()) if args.all or not args.names else args.names
    run(names, Path(args.out))


if __name__ == "__main__":
    main()
