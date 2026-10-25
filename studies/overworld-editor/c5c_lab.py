"""Rung C5 in game, the coast: a cliff the World tab's coast tool pushed out in a draft, promoted, seen in the game.

    py studies/overworld-editor/c5c_lab.py build   # the tool picks the window + accepts the morph; identity; predictions
    py studies/overworld-editor/c5c_lab.py run     # reach the world; before / promote / reload / after; quit

THE EDITOR'S PATH (as C1-C3 and the sink): the real CoastTool (workspace/worldcoast.py) with its real runner against
the real install: a click near CLICK picks block (2,7)'s cliff window from its scanned windows, the verb is the
window's lawful cliff-bump at its own ceiling, Check runs `world-transplant --in-place --dry-run`, Accept runs the
morph into a fresh draft on disc 1 and then on disc 4. Then the two calls typed by hand into a second draft, every
world file compared (I1).

REGISTERED PREDICTIONS (c5c_prep.json, written by `build` before the game opens; tolerance 0.15):
  M0 before the promote, at the probe P (a point the morph moves the ground under by >= 0.5) the party stands at the
     live stack's height;
  M1 after the promote and the reload, at the Landing Site K (the control) it stands where it stood;
  M2 at P it stands where point_info predicts with the draft in place of FF9CustomMap-world;
  M3 Memoria.log: the reload loaded block (2,7) from FF9CustomMap-world.
The party is put back on K, and the game is closed at the end (the harness quit).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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
CLICK = (177.0, -480.0)                                                 # beside block (2,7)'s north-south cliff base
OUT = HERE / "out" / "c5c_lab"
PREP = HERE / "out" / "c5c_prep.json"
RESULT = HERE / "out" / "c5c_result.json"
TOL = 0.15


def _world(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh") if ".bak-" not in p.name}


def _drive_tool(drafts: Path) -> dict:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldcoast import CoastTool
    from ff9mapkit.workspace.worldforest import QProcessRunner
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    pal = pick_palette("dark")
    runner = QProcessRunner()
    argvs = []
    real_start = runner.start

    def start(argv, cwd, done):
        argvs.append([str(a) for a in argv])
        real_start(argv, cwd, done)
    runner.start = start
    tool = CoastTool(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE,
                     runner=runner, drafts_root=drafts)
    tool.open_tool()

    def pump(until, sec):
        t = time.time()
        while time.time() - t < sec:
            app.processEvents()
            if until():
                return True
            time.sleep(0.02)
        return False
    assert pump(lambda: tool._ix is not None, 120), tool.verdict_lbl.text()
    tool.place(*CLICK, 3.0)
    assert pump(lambda: tool._window is not None, 300), tool.window_lbl.text()
    verbs = [tool.verb_box.itemData(i) for i in range(tool.verb_box.count())]
    if "cliff-bump" in verbs:
        tool.verb_box.setCurrentIndex(tool.verb_box.findData("cliff-bump"))
    picked = {"window": tool.window_lbl.text(), "verbs": verbs, "verb": tool.verb(), "depth": tool.depth.value(),
              "range": [tool.depth.minimum(), tool.depth.maximum()]}
    tool._handles_changed(at_once=True)
    t0 = time.time()
    assert pump(lambda: tool._current_verdict() is not None, 300), tool.verdict_lbl.text()
    t_check = time.time() - t0
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    check_text = tool.verdict_lbl.text()
    t0 = time.time()
    tool.accept_btn.click()
    assert pump(lambda: tool._job is None and tool.center is None, 600), tool.verdict_lbl.text()
    return {"argvs": argvs, "picked": picked, "check": check_text, "accepted": tool.verdict_lbl.text(),
            "draft": str(tool.draft()), "check_s": round(t_check, 1), "accept_s": round(time.time() - t0, 1),
            "disc4": getattr(tool, "_disc4", None), "show": tool._last_center}


def build():
    import numpy as np
    from ff9mapkit.world import coastedit as CE, draft as D, render as R
    if OUT.exists():
        shutil.rmtree(OUT)
    drive = _drive_tool(OUT / "drafts")
    draft = Path(drive["draft"])
    print(f"tool: {drive['picked']}\n  check {drive['check_s']} s: {drive['check']}\n  accept {drive['accept_s']} s: "
          f"{drive['accepted']} (disc 4 {'done' if drive['disc4'] else 'refused'})")
    one = drive["argvs"][-2][3:]
    verb = next(a[2:] for a in one if a.startswith("--") and a[2:] in CE.VERBS)
    spec, cell = one[one.index(f"--{verb}") + 1], tuple(int(v) for v in one[one.index("--cell") + 1].split(","))
    hand = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "hand")
    for argv in CE.commands(hand, cell, verb, spec):
        r = subprocess.run([sys.executable, "-m", "ff9mapkit"] + argv, cwd=KIT, capture_output=True, text=True,
                           timeout=900)
        assert r.returncode == 0 or "--disc" in argv, r.stderr[-2000:]
    ed, hd = _world(draft), _world(hand)
    diff = sorted(k for k in set(ed) | set(hd) if ed.get(k) != hd.get(k))
    edits = D.edits(draft)
    print(f"I1 identity: {'IDENTICAL' if not diff else 'DIFFERS ' + str(diff)} over {len(ed)} world files; the draft "
          f"edited {len(edits)}: {edits}")
    assert not diff
    names = [p.name for p in R.game_stack(GAME)]
    live = R.RenderSite(cells=(), disc=1, game=GAME, stack=tuple(GAME / n for n in names))
    with_draft = R.RenderSite(cells=(), disc=1, game=GAME,
                              stack=tuple(draft if n == SOURCE else GAME / n for n in names))
    dnames = [draft.name if n == SOURCE else n for n in names]
    # THE PROBE: across the window, off the 4u lattice, the point the morph moves most that is walkable ground after it
    # (a bump turns sea into land: before, it may be the water)
    (x0, z0), (x1, z1) = [tuple(float(v) for v in p.split(",")) for p in spec.split(":")[:2]]
    mid, tang = np.array([(x0 + x1) / 2, (z0 + z1) / 2]), np.array([x1 - x0, z1 - z0])
    nrm = np.array([-tang[1], tang[0]]) / (np.linalg.norm(tang) or 1.0)
    best = None
    for s in np.arange(-6.0, 6.01, 0.5):
        for t in (-0.2, 0.0, 0.2):
            x, z = mid + nrm * s + tang * t / 2
            x, z = round(float(x) + 0.37, 2), round(float(z) - 0.29, 2)
            g, w = C1._ground(with_draft, x, z, dnames), C1._ground(live, x, z, names)
            sep = abs(g["stand_y"] - w["stand_y"])
            if g.get("walkable") and (best is None or sep > best[0]):
                best = (sep, x, z)
    assert best and best[0] >= 0.5, f"no probe the morph moves by 0.5 onto walkable ground (best {best})"
    targets = []
    for key, (x, z) in (("P", best[1:]), ("K", C1.CONTROL[1:])):
        g, w = C1._ground(with_draft, x, z, dnames), C1._ground(live, x, z, names)
        targets.append({"key": key, "x": x, "z": z, "predict_y": g["stand_y"], "topograph": g.get("topograph"),
                        "live_y": w["stand_y"], "live_topograph": w.get("topograph"),
                        "separation": abs(g["stand_y"] - w["stand_y"])})
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "cell": cell, "verb": verb, "spec": spec, "draft": str(draft),
           "edits": edits, "tool": drive, "I1": {"identical": not diff, "differing": diff, "files": len(ed)},
           "stack": names, "tolerance": TOL, "targets": targets}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for t in targets:
        print(f"  {t['key']} at {t['x']}, {t['z']}: with the draft y {t['predict_y']:.3f} (topograph {t['topograph']}); "
              f"live y {t['live_y']:.3f} (topograph {t['live_topograph']}), separation {t['separation']:.2f}")
    print(f"-> {PREP}")


def run():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    tg = {t["key"]: t for t in prep["targets"]}
    P, K = (tg["P"]["x"], tg["P"]["z"]), (tg["K"]["x"], tg["K"]["z"])
    rec = {"prep_t": prep["t"], "steps": {}}

    def tele(key, at):
        r = C2._sh([py, "tools/world_teleport.py", f"{at[0]:.2f}", f"{at[1]:.2f}", "--shot", f"c5c-{key}"], 300)
        rec["steps"][key] = C2._last_json(r)

    r = C2._sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c5c-reach"], 900)
    rec["reach_rc"] = r.returncode
    try:
        if r.returncode == 0:
            tele("M0-before", P)
            rec["promote"] = C2._promote(prep)
            if rec["promote"]["rc"] == 0:
                mark = log.stat().st_size if log.is_file() else 0
                r = C2._sh([py, "tools/world_reload.py", f"{K[0]:.2f}", f"{K[1]:.2f}", "--shot", "c5c-M1-reload"], 600)
                rec["steps"]["M1-reload"] = C2._last_json(r)
                text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
                bx, by = prep["cell"]
                rec["log"] = [ln.strip() for ln in text.splitlines() if "WorldMeshOverride" in ln
                              and f"Block[{bx}][{by}]" in ln]
                tele("M2-after", P)
                tele("K1-back", K)
    finally:
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c5c-quit"], 300)   # close the game
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")
    ran = (rec.get("promote") or {}).get("rc") == 0
    rec["M0"] = y("M0-before") is not None and abs(y("M0-before") - tg["P"]["live_y"]) <= TOL
    rec["M1"] = ran and y("M1-reload") is not None and abs(y("M1-reload") - tg["K"]["predict_y"]) <= TOL
    rec["M2"] = ran and y("M2-after") is not None and abs(y("M2-after") - tg["P"]["predict_y"]) <= TOL
    rec["M3"] = ran and len(rec.get("log") or []) >= 1 and all(SOURCE in ln and "loaded" in ln for ln in rec["log"])
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for k, key in (("M0-before", "P"), ("M1-reload", "K"), ("M2-after", "P"), ("K1-back", "K")):
        print(f"{k}: y {y(k)}  (live {tg[key]['live_y']:.3f}, with the draft {tg[key]['predict_y']:.3f})")
    print({k: rec[k] for k in ("M0", "M1", "M2", "M3")}, "promote", (rec.get("promote") or {}).get("seconds"), "s")
    print(f"-> {RESULT}")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        build()
    elif cmd == ["run"]:
        run()
    else:
        raise SystemExit(__doc__)
