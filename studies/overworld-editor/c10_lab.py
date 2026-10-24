"""Rung C10 on real bytes and in game: a hill and a forest placed across the world's x seam through the World tab's cards.

    py studies/overworld-editor/c10_lab.py build   # the cards place both across x = 0; identity; predictions
    py studies/overworld-editor/c10_lab.py run     # reach; before; promote; reload; after (both halves); quit

THE EDITOR'S PATH: the real HillTool and ForestTool (workspace/worldhill.py, worldforest.py) with their real runners
and their real soups against the real install, no soup injected: each card reads the island twice, in [0, 1536)
and across x = 0, and judges a centre near the seam in the second. On FF9CustomMap-world's lawn across x = 0 (the
landmass west of the Landing Site, columns 23 and 0): the hill H at the lawful centre nearest (0, -500) with x in [-8, -2]
(so its 18u slope runs over the seam both ways), then the forest F (forest-blob) at the lawful centre nearest
(0, -560) with x in [-6, -2], 44u+ from H. Clicks are fed as the view's WEST copy would give them (x < 0); the cards fold.
  I1: the cards' draft == the two commands typed by hand with the UNFOLDED centres (x < 0) onto a second draft;
  I2: == the saved recipe (`[[hill]]`, `[[forest]]`) composed by `world-fuse` onto a third.

REGISTERED PREDICTIONS (c10_prep.json, written by `build` before the game opens; tolerance 0.15):
  N0 before the promote, at H's top and on F's canopy the party stands on the lawn, at its live height;
  N1 after the promote and the reload, at the Landing Site K (the control) it stands where it stood;
  N2 at H's top, at a point on H's west slope (x >= 1520, column 23) and one on its east slope (x <= 16, column 0),
     and on F's canopy, it stands where point_info predicts with the draft in place;
  N3 Memoria.log: the reload loaded blocks of BOTH columns 23 and 0 from FF9CustomMap-world.
The party is put back on K, and the game is closed at the end (the harness quit).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lab as C1                                                    # noqa: E402  (the paths, the ground probe)
import c2_lab as C2                                                    # noqa: E402  (the shell steps, the promote)

GAME, KIT, REPO = C1.GAME, C1.KIT, C1.REPO
SOURCE = "FF9CustomMap-world"
HEIGHT, RADIUS = 4.2, 18.0
DONOR = (15, 15)                                                       # forest-blob, world-forest's default
OUT = HERE / "out" / "c10_lab"
PREP = HERE / "out" / "c10_prep.json"
RESULT = HERE / "out" / "c10_result.json"
TOL = 0.15


def _world(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "FF9_Data" / "WorldMap").rglob("Block*")
            if ".bak-" not in p.name and p.suffix in (".ff9mesh", ".txt")}


def _pump(app, until, sec):
    t = time.time()
    while time.time() - t < sec:
        app.processEvents()
        if until():
            return True
        time.sleep(0.02)
    return False


def _spot(lawful, near, xmax, *, away=(), step=2.0):
    """The lawful centre nearest ``near`` WEST of the seam, -xmax <= x <= -2 (a seam-frame x: its command spells it
    unfolded or folded, 1536u apart), 44u+ from every point of ``away``."""
    cands = sorted(((-x * step, near[1] + z * step) for x in range(1, int(xmax / step) + 1)
                    for z in range(-60, 61)), key=lambda c: math.dist(c, near))
    for c in cands:
        if all(math.dist(c, a) >= 44.0 for a in away) and lawful(c):
            return c
    raise AssertionError(f"no lawful centre near {near} with |x| <= {xmax}")


def _drive(drafts: Path) -> dict:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.world import forestedit as FE, hilledit as HE
    from ff9mapkit.workspace.worldforest import ForestTool, QProcessRunner
    from ff9mapkit.workspace.worldhill import HillTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    pal = pick_palette("dark")
    argvs = []

    def logged():
        r = QProcessRunner()
        real = r.start

        def start(argv, cwd, done):
            argvs.append([str(a) for a in argv])
            real(argv, cwd, done)
        r.start = start
        return r
    panel = WorldView3DPanel(pal)
    out = {}
    hill = HillTool(pal, panel, game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE, runner=logged(),
                    drafts_root=drafts)
    hill.open_tool()
    hill.place(-0.1, -500.0, 0.0)                        # a click on the west copy, by x = 0: the seam frame
    assert hill._seam, "the hill card did not take the seam frame"
    assert _pump(app, lambda: hill._ix is not None, 300), hill.verdict_lbl.text()
    t0 = time.time()
    H = _spot(lambda c: HE.preview(hill._ix, c, HEIGHT, RADIUS)["ok"], (0.0, -500.0), 8.0)
    t_spot = time.time() - t0
    for key, tool, at in (("H", hill, H), ("F", None, None)):
        if key == "F":
            hill.close_tool()
            tool = ForestTool(pal, panel, game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE, runner=logged(),
                              drafts_root=drafts)
            tool.open_tool()
            tool.donor_box.setCurrentIndex(tool.donor_box.findData("{},{}".format(*DONOR)))
            tool.place(-0.1, -560.0, 0.0)
            assert tool._seam
            assert _pump(app, lambda: tool._ix is not None and DONOR in tool._outlines, 300), tool.verdict_lbl.text()
            ol = tool._outlines[DONOR]

            def lawful(c, tool=tool, ol=ol):
                _t, rim = FE.placed(ol, c, ground_y=0.0)
                return FE.footprint_preview(tool._ix, rim[:, [0, 2]])["ok"]
            at = _spot(lawful, (0.0, -560.0), 6.0, away=(H,))
        tool.place(*at, 0.0)                             # x < 0: as the view's west copy gives it
        assert tool._seam and tool.fcenter() == (round(at[0], 1), round(at[1], 1)), (tool.center, tool.fcenter())
        poly = None if panel._ghost is None else panel._ghost["poly"]
        t0 = time.time()
        assert _pump(app, lambda: tool._current_verdict() is not None, 300), tool.verdict_lbl.text()
        check_s = round(time.time() - t0, 1)
        assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
        check_text = tool.verdict_lbl.text()
        t0 = time.time()
        tool.accept_btn.click()
        assert _pump(app, lambda: tool._job is None and tool.center is None, 900), tool.verdict_lbl.text()
        out[key] = {"at": at, "folded": [at[0] % 1536.0, at[1]], "check_s": check_s,
                    "accept_s": round(time.time() - t0, 1), "check": check_text, "accepted": tool.verdict_lbl.text(),
                    "ghost_x": None if poly is None else [round(float(min(p[0] for p in poly)), 2),
                                                          round(float(max(p[0] for p in poly)), 2)],
                    "argv": argvs[-1]}
        print(f"{key} at {at} (folded {out[key]['folded']}): ghost x {out[key]['ghost_x']}, check {check_s} s, "
              f"accept {out[key]['accept_s']} s\n  {check_text}")
    tool.close_tool()
    out["draft"], out["spot_s"] = str(tool.draft()), round(t_spot, 1)
    return out


def _kit(argv, timeout=900):
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "--game", str(GAME)] + argv, cwd=KIT, capture_output=True,
                       text=True, timeout=timeout)
    assert r.returncode == 0, (argv, r.stdout[-1500:], r.stderr[-1500:])
    return r


def build():
    from ff9mapkit.world import draft as D, recipe as RC, render as R
    if OUT.exists():
        shutil.rmtree(OUT)
    drive = _drive(OUT / "drafts")
    draft = Path(drive["draft"])
    hand = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "hand")
    hand_argvs = []
    for key in ("H", "F"):                               # the hand-typed commands, the centres UNFOLDED (x < 0)
        argv = drive[key]["argv"][5:]
        i = argv.index("--report-json")
        argv = argv[:i] + argv[i + 2:]
        argv[argv.index("--mod-folder") + 1] = str(hand)
        x, z = drive[key]["at"]
        argv[argv.index("--center") + 1] = f"{x:g},{z:g}"
        hand_argvs.append(argv)
        _kit(argv)
    recipe = OUT / "seam.toml"
    rows = D.recipe_rows(draft)
    recipe.write_text(RC.dumps(rows), encoding="utf-8")
    composed = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "composed")
    _kit(["world-fuse", str(recipe), "--mod-folder", str(composed)])
    ed, hd, cd = _world(draft), _world(hand), _world(composed)
    d1 = sorted(k for k in set(ed) | set(hd) if ed.get(k) != hd.get(k))
    d2 = sorted(k for k in set(ed) | set(cd) if ed.get(k) != cd.get(k))
    edits = D.edits(draft)
    cols = sorted({int(e.split("Block[")[1].split("]")[0]) for e in edits})
    print(f"I1 hand (unfolded centres): {'IDENTICAL' if not d1 else 'DIFFERS ' + str(d1[:6])}; I2 recipe: "
          f"{'IDENTICAL' if not d2 else 'DIFFERS ' + str(d2[:6])}; over {len(ed)} world files. The draft edited "
          f"{len(edits)} in columns {cols}: {edits}")
    assert not d1 and not d2 and 23 in cols and 0 in cols
    names = [p.name for p in R.game_stack(GAME)]
    live = R.RenderSite(cells=(), disc=1, game=GAME, stack=tuple(GAME / n for n in names))
    with_draft = R.RenderSite(cells=(), disc=1, game=GAME,
                              stack=tuple(draft if n == SOURCE else GAME / n for n in names))
    dnames = [draft.name if n == SOURCE else n for n in names]
    hx, hz = drive["H"]["folded"]
    fx, fz = drive["F"]["folded"]
    picks = (("H", ((hx + 0.37) % 1536.0, hz - 0.29)),          # the top, off the 4u lattice
             ("Hw", ((hx - 9.0) % 1536.0, hz + 0.3)),           # its west slope
             ("He", ((hx + 9.0) % 1536.0, hz - 0.3)),           # its east slope
             ("F", ((fx + 0.37) % 1536.0, fz - 0.29)),          # on the canopy
             ("K", C1.CONTROL[1:]))
    targets = []
    for key, (x, z) in picks:
        g, w = C1._ground(with_draft, x, z, dnames), C1._ground(live, x, z, names)
        targets.append({"key": key, "x": round(x, 3), "z": round(z, 3), "predict_y": g["stand_y"],
                        "part": g.get("part"), "topograph": g.get("topograph"), "live_y": w["stand_y"],
                        "block": [int(x // 64) % 24, int(-z // 64)]})
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "height": HEIGHT, "radius": RADIUS, "donor": DONOR,
           "draft": str(draft), "edits": edits, "columns": cols, "rows": rows, "tool": drive, "hand_argvs": hand_argvs,
           "I1": {"identical": not d1, "differing": d1, "files": len(ed)}, "I2": {"identical": not d2, "differing": d2},
           "stack": names, "tolerance": TOL, "targets": targets}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for t in targets:
        print(f"  {t['key']} at {t['x']}, {t['z']} (block {t['block']}): with the draft y {t['predict_y']:.3f} "
              f"({t['part']} topograph {t['topograph']}); live y {t['live_y']:.3f}")
    print(f"-> {PREP}")


def run():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    tg = {t["key"]: t for t in prep["targets"]}

    def at(key):
        return tg[key]["x"], tg[key]["z"]
    rec = {"prep_t": prep["t"], "steps": {}}

    def tele(key, where):
        r = C2._sh([py, "tools/world_teleport.py", f"{where[0]:.2f}", f"{where[1]:.2f}", "--shot", f"c10-{key}"], 300)
        rec["steps"][key] = C2._last_json(r)

    r = C2._sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c10-reach"], 900)
    rec["reach_rc"] = r.returncode
    try:
        if r.returncode == 0:
            tele("N0-H", at("H"))
            tele("N0-F", at("F"))
            rec["promote"] = C2._promote(prep)
            if rec["promote"]["rc"] == 0:
                mark = log.stat().st_size if log.is_file() else 0
                r = C2._sh([py, "tools/world_reload.py", f"{at('K')[0]:.2f}", f"{at('K')[1]:.2f}", "--shot",
                            "c10-N1-reload"], 600)
                rec["steps"]["N1-reload"] = C2._last_json(r)
                text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
                rec["log"] = [ln.strip() for ln in text.splitlines() if "WorldMeshOverride" in ln and SOURCE in ln
                              and any(f"Block[{c}][" in ln for c in (23, 0))]
                for key in ("H", "Hw", "He", "F"):
                    tele(f"N2-{key}", at(key))
                tele("K-back", at("K"))
    finally:
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c10-quit"], 300)   # close the game
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")

    def near(key, want):
        return y(key) is not None and abs(y(key) - want) <= TOL
    ran = (rec.get("promote") or {}).get("rc") == 0
    rec["N0"] = near("N0-H", tg["H"]["live_y"]) and near("N0-F", tg["F"]["live_y"])
    rec["N1"] = ran and near("N1-reload", tg["K"]["predict_y"])
    rec["N2"] = ran and all(near(f"N2-{k}", tg[k]["predict_y"]) for k in ("H", "Hw", "He", "F"))
    logged = rec.get("log") or []
    rec["N3"] = ran and any("Block[23][" in ln for ln in logged) and any("Block[0][" in ln for ln in logged) and \
        all("loaded" in ln for ln in logged)
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for step, key in (("N0-H", "H"), ("N0-F", "F"), ("N1-reload", "K"), ("N2-H", "H"), ("N2-Hw", "Hw"),
                      ("N2-He", "He"), ("N2-F", "F"), ("K-back", "K")):
        print(f"{step}: y {y(step)}  (live {tg[key]['live_y']:.3f}, with the draft {tg[key]['predict_y']:.3f})")
    print({k: rec[k] for k in ("N0", "N1", "N2", "N3")}, "promote", (rec.get("promote") or {}).get("seconds"), "s")
    print(f"-> {RESULT}")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        build()
    elif cmd == ["run"]:
        run()
    else:
        raise SystemExit(__doc__)
