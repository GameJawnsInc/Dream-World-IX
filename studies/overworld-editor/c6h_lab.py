"""Rung 6 in game, the hill: a grass hill the World tab's hill tool raised in a draft, promoted, climbed.

    py studies/overworld-editor/c6h_lab.py build   # find a lawful spot; the tool raises the hill; identity; predictions
    py studies/overworld-editor/c6h_lab.py run     # reach the world; before / promote / reload / after; quit

THE EDITOR'S PATH (as the others): the real HillTool (workspace/worldhill.py) with its real runner against the real
install. The spot is the first a grid of the card's own preview passes on FF9CustomMap-world's deployed islands
(level mains lawn, clear of forest, stamps and rock), then Check runs `world-hill --dry-run`, Accept raises it in a
fresh draft. Then the command typed by hand into a second draft (I1) and the [[hill]] row composed into a third (I2),
every world file compared.

REGISTERED PREDICTIONS (c6h_prep.json, written by `build` before the game opens; tolerance 0.15):
  N0 before the promote, at the hill's centre T the party stands on the lawn, at its live height;
  N1 after the promote and the reload, at the Landing Site K (the control) it stands where it stood;
  N2 at T it stands on the hill's top, at the height point_info predicts with the draft in place (the lawn plus the
     height);
  N3 Memoria.log: the reload loaded T's block from FF9CustomMap-world.
The party is put back on K, and the game is closed at the end (the harness quit).
"""
from __future__ import annotations

import hashlib
import json
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
HEIGHT, RADIUS = 4.2, 18.0                                             # the verb's own defaults: the proven hill
OUT = HERE / "out" / "c6h_lab"
PREP = HERE / "out" / "c6h_prep.json"
RESULT = HERE / "out" / "c6h_result.json"
TOL = 0.15


def _world(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "FF9_Data" / "WorldMap").rglob("Block*")
            if ".bak-" not in p.name and p.suffix in (".ff9mesh", ".txt")}


def _spot(ix):
    """The first lawful centre on an 8u grid over the deployed lawn, nearest the Landing Site (a short walk)."""
    import numpy as np
    from ff9mapkit.world import hilledit as HE
    fam = HE._fam(ix)
    mains = ix.cent[fam == "main"]
    k = C1.CONTROL[1:]
    cands = sorted({(round(x / 8) * 8.0, round(z / 8) * 8.0) for x, z in mains[::7]},
                   key=lambda c: (c[0] - k[0]) ** 2 + (c[1] - k[1]) ** 2)
    for c in cands:
        if HE.preview(ix, c, HEIGHT, RADIUS)["ok"]:
            return c
    raise AssertionError("no lawful hill spot on the deployed islands")


def _drive_tool(drafts: Path) -> dict:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldforest import QProcessRunner
    from ff9mapkit.workspace.worldhill import HillTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    pal = pick_palette("dark")
    runner = QProcessRunner()
    argvs = []
    real_start = runner.start

    def start(argv, cwd, done):
        argvs.append([str(a) for a in argv])
        real_start(argv, cwd, done)
    runner.start = start
    tool = HillTool(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE,
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
    assert pump(lambda: tool._ix is not None, 300), tool.verdict_lbl.text()
    t0 = time.time()
    center = _spot(tool._ix)
    t_spot = time.time() - t0
    tool.height_spin.setValue(HEIGHT)
    tool.radius_spin.setValue(RADIUS)
    tool.place(*center, 0.0)
    preview = dict(tool._preview or {})
    t0 = time.time()
    assert pump(lambda: tool._current_verdict() is not None, 300), tool.verdict_lbl.text()
    t_check = time.time() - t0
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    check_text = tool.verdict_lbl.text()
    t0 = time.time()
    tool.accept_btn.click()
    assert pump(lambda: tool._job is None and tool.center is None, 600), tool.verdict_lbl.text()
    return {"argvs": argvs, "center": center, "preview": {k: preview.get(k) for k in ("ok", "why", "report")},
            "check": check_text, "accepted": tool.verdict_lbl.text(), "draft": str(tool.draft()),
            "spot_s": round(t_spot, 1), "check_s": round(t_check, 1), "accept_s": round(time.time() - t0, 1)}


def _kit(argv, timeout=900):
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "--game", str(GAME)] + argv, cwd=KIT, capture_output=True,
                       text=True, timeout=timeout)
    assert r.returncode == 0, (argv, r.stdout[-1500:], r.stderr[-1500:])
    return r


def build():
    from ff9mapkit.world import draft as D, recipe as RC, render as R
    if OUT.exists():
        shutil.rmtree(OUT)
    drive = _drive_tool(OUT / "drafts")
    draft = Path(drive["draft"])
    print(f"tool: spot {drive['center']} ({drive['spot_s']} s); preview {drive['preview']}\n"
          f"  check {drive['check_s']} s: {drive['check']}\n  accept {drive['accept_s']} s: {drive['accepted']}")
    argv = drive["argvs"][-1][5:]
    i = argv.index("--report-json")
    argv = argv[:i] + argv[i + 2:]
    hand = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "hand")
    _kit([str(hand) if a == drive["draft"] else a for a in argv])
    recipe = OUT / "hill.toml"
    recipe.write_text(RC.dumps([RC.row_for([a if a != drive["draft"] else "-" for a in argv])]), encoding="utf-8")
    composed = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "composed")
    _kit(["world-fuse", str(recipe), "--mod-folder", str(composed)])
    ed, hd, cd = _world(draft), _world(hand), _world(composed)
    d1 = sorted(k for k in set(ed) | set(hd) if ed.get(k) != hd.get(k))
    d2 = sorted(k for k in set(ed) | set(cd) if ed.get(k) != cd.get(k))
    edits = D.edits(draft)
    print(f"I1 hand: {'IDENTICAL' if not d1 else 'DIFFERS ' + str(d1[:6])}; I2 recipe: "
          f"{'IDENTICAL' if not d2 else 'DIFFERS ' + str(d2[:6])}; over {len(ed)} world files. The draft edited "
          f"{len(edits)}: {edits}")
    assert not d1 and not d2
    names = [p.name for p in R.game_stack(GAME)]
    live = R.RenderSite(cells=(), disc=1, game=GAME, stack=tuple(GAME / n for n in names))
    with_draft = R.RenderSite(cells=(), disc=1, game=GAME,
                              stack=tuple(draft if n == SOURCE else GAME / n for n in names))
    dnames = [draft.name if n == SOURCE else n for n in names]
    cx, cz = drive["center"]
    T = (round(cx + 0.37, 2), round(cz - 0.29, 2))                   # off the 4u lattice, at the top
    targets = []
    for key, (x, z) in (("T", T), ("K", C1.CONTROL[1:])):
        g, w = C1._ground(with_draft, x, z, dnames), C1._ground(live, x, z, names)
        targets.append({"key": key, "x": round(x, 3), "z": round(z, 3), "predict_y": g["stand_y"],
                        "part": g.get("part"), "topograph": g.get("topograph"), "live_y": w["stand_y"],
                        "live_part": w.get("part"), "live_topograph": w.get("topograph"),
                        "block": [int(x // 64) % 24, int(-z // 64)]})
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "height": HEIGHT, "radius": RADIUS, "draft": str(draft),
           "edits": edits, "tool": drive, "hand_argv": argv,
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
    T, K = ((tg[k]["x"], tg[k]["z"]) for k in ("T", "K"))
    rec = {"prep_t": prep["t"], "steps": {}}

    def tele(key, at):
        r = C2._sh([py, "tools/world_teleport.py", f"{at[0]:.2f}", f"{at[1]:.2f}", "--shot", f"c6h-{key}"], 300)
        rec["steps"][key] = C2._last_json(r)

    r = C2._sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c6h-reach"], 900)
    rec["reach_rc"] = r.returncode
    try:
        if r.returncode == 0:
            tele("N0-before", T)
            tele("K0-before", K)
            rec["promote"] = C2._promote(prep)
            if rec["promote"]["rc"] == 0:
                mark = log.stat().st_size if log.is_file() else 0
                r = C2._sh([py, "tools/world_reload.py", f"{K[0]:.2f}", f"{K[1]:.2f}", "--shot", "c6h-N1-reload"], 600)
                rec["steps"]["N1-reload"] = C2._last_json(r)
                text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
                rec["log"] = [ln.strip() for ln in text.splitlines() if "WorldMeshOverride" in ln
                              and "Block[{}][{}]".format(*tg["T"]["block"]) in ln]
                tele("N2-after", T)
                tele("K1-back", K)
    finally:
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c6h-quit"], 300)   # close the game
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")
    ran = (rec.get("promote") or {}).get("rc") == 0
    rec["N0"] = y("N0-before") is not None and abs(y("N0-before") - tg["T"]["live_y"]) <= TOL
    rec["N1"] = ran and y("N1-reload") is not None and abs(y("N1-reload") - tg["K"]["predict_y"]) <= TOL
    rec["N2"] = ran and y("N2-after") is not None and abs(y("N2-after") - tg["T"]["predict_y"]) <= TOL
    rec["N3"] = ran and len(rec.get("log") or []) >= 1 and all(SOURCE in ln and "loaded" in ln for ln in rec["log"])
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for k, key in (("N0-before", "T"), ("N1-reload", "K"), ("N2-after", "T"), ("K1-back", "K")):
        print(f"{k}: y {y(k)}  (live {tg[key]['live_y']:.3f}, with the draft {tg[key]['predict_y']:.3f})")
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
