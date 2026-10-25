"""Rung C5 in game, the river: the carried river the World tab's river tool moved in a draft, promoted, walked.

    py studies/overworld-editor/c5r_lab.py build   # the tool reads the river, picks the placement, moves it; identity
    py studies/overworld-editor/c5r_lab.py run     # reach the world; before / promote / reload / after; quit

THE EDITOR'S PATH (as the others): the real RiverTool (workspace/worldriver.py) with its real runner against the real
install. It reads where the river stands in FF9CustomMap-world (the ledger), a click picks the placement one block
north (shift TO), Check runs `world-river --move-from --dry-run`, Accept moves it in a fresh draft. Then the command
typed by hand into a second draft (I1) and the recipe's [[river]] row composed into a third (I2), every world file
compared.

REGISTERED PREDICTIONS (c5r_prep.json, written by `build` before the game opens; tolerance 0.15):
  N0 before the promote, at the probe O (the river's land on a cell the move empties) the party stands on that land,
     and at the probe N (the river's land after the move, on a cell it was not on) it is in the open sea (y <= 0.05);
  N1 after the promote and the reload, at the Landing Site K (the control) it stands where it stood;
  N2 at N it stands on the moved river's land, at the height point_info predicts with the draft in place;
  N3 at O it is in the open sea now (y <= 0.05);
  N4 Memoria.log: the reload loaded N's block from FF9CustomMap-world.
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
FROM, TO = (8, -2), (8, -3)                                            # 512,128 -> 512,192: one block north
OUT = HERE / "out" / "c5r_lab"
PREP = HERE / "out" / "c5r_prep.json"
RESULT = HERE / "out" / "c5r_result.json"
TOL = 0.15


def _world(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "FF9_Data" / "WorldMap").rglob("Block*")
            if ".bak-" not in p.name and p.suffix in (".ff9mesh", ".txt")}


def _drive_tool(drafts: Path) -> dict:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldforest import QProcessRunner
    from ff9mapkit.workspace.worldriver import RiverTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from ff9mapkit.world import riveredit as RE
    pal = pick_palette("dark")
    runner = QProcessRunner()
    argvs = []
    real_start = runner.start

    def start(argv, cwd, done):
        argvs.append([str(a) for a in argv])
        real_start(argv, cwd, done)
    runner.start = start
    tool = RiverTool(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE,
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
    t0 = time.time()
    assert pump(lambda: tool._ix is not None and tool._rs() is not None and tool._river is not None, 600), \
        tool.verdict_lbl.text()
    t_read = time.time() - t0
    rs = tool._rs()
    at_now = tool.river_at()
    assert RE.same_shift(at_now, FROM), f"the river stands at {at_now}, not {FROM}"
    free = RE.free_shifts(rs, river_at=at_now, occupied=lambda cells: {c: sorted(tool._river[2][c]) for c in cells
                                                                      if c in tool._river[2]})
    tool.place(*RE.centre(rs, TO), 0.0)
    assert tool._shift == TO, tool._shift
    preview = dict(tool._preview or {})
    t0 = time.time()
    assert pump(lambda: tool._current_verdict() is not None, 600), tool.verdict_lbl.text()
    t_check = time.time() - t0
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    check_text = tool.verdict_lbl.text()
    t0 = time.time()
    tool.accept_btn.click()
    assert pump(lambda: tool._job is None and tool.center is None, 900), tool.verdict_lbl.text()
    return {"argvs": argvs, "preview": {k: preview.get(k) for k in ("ok", "why", "blocks")}, "check": check_text,
            "accepted": tool.verdict_lbl.text(), "draft": str(tool.draft()), "read_s": round(t_read, 1),
            "check_s": round(t_check, 1), "accept_s": round(time.time() - t0, 1), "show": tool._last_center,
            "from_text": tool.from_lbl.text(), "free": free, "shifts": len(rs.shifts),
            "cells_from": rs.cells_at(FROM), "cells_to": rs.cells_at(TO)}


def _kit(argv, timeout=900):
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "--game", str(GAME)] + argv, cwd=KIT, capture_output=True,
                       text=True, timeout=timeout)
    assert r.returncode == 0, (argv, r.stdout[-1500:], r.stderr[-1500:])
    return r


def build():
    from ff9mapkit.world import draft as D, recipe as RC, render as R, riveredit as RE
    if OUT.exists():
        shutil.rmtree(OUT)
    drive = _drive_tool(OUT / "drafts")
    draft = Path(drive["draft"])
    print(f"tool: read {drive['read_s']} s ({drive['from_text']}); {drive['shifts']} placements, free "
          f"{drive['free']}\n  preview {drive['preview']}\n  check {drive['check_s']} s: {drive['check']}\n"
          f"  accept {drive['accept_s']} s: {drive['accepted']}")
    argv = drive["argvs"][-1][5:]                                     # after python -m ff9mapkit --game GAME
    i = argv.index("--report-json")
    argv = argv[:i] + argv[i + 2:]
    hand = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "hand")
    _kit([str(hand) if a == drive["draft"] else a for a in argv])
    recipe = OUT / "move.toml"
    recipe.write_text(RC.dumps([RC.row_for([a if a != drive["draft"] else "-" for a in argv])]), encoding="utf-8")
    composed = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "composed")
    _kit(["world-fuse", str(recipe), "--mod-folder", str(composed)])
    ed, hd, cd = _world(draft), _world(hand), _world(composed)
    d1 = sorted(k for k in set(ed) | set(hd) if ed.get(k) != hd.get(k))
    d2 = sorted(k for k in set(ed) | set(cd) if ed.get(k) != cd.get(k))
    edits, gone = D.edits(draft), D.removals(draft)
    print(f"I1 hand: {'IDENTICAL' if not d1 else 'DIFFERS ' + str(d1[:6])}; I2 recipe: "
          f"{'IDENTICAL' if not d2 else 'DIFFERS ' + str(d2[:6])}; over {len(ed)} world files. The draft edited "
          f"{len(edits)} and removed {len(gone)}")
    assert not d1 and not d2
    names = [p.name for p in R.game_stack(GAME)]
    live = R.RenderSite(cells=(), disc=1, game=GAME, stack=tuple(GAME / n for n in names))
    with_draft = R.RenderSite(cells=(), disc=1, game=GAME,
                              stack=tuple(draft if n == SOURCE else GAME / n for n in names))
    dnames = [draft.name if n == SOURCE else n for n in names]
    rs = RE.shape(game=GAME)
    only_from = set(drive["cells_from"]) - set(drive["cells_to"])
    only_to = set(drive["cells_to"]) - set(drive["cells_from"])

    def probe(cells, land, lsn, sea, ssn):
        """A point on ``cells`` (a 4u grid, off the lattice) that is walkable Terrain in the stack ``land`` and open
        sea in ``sea``: the river's island (its carried land or its minted lawn) on one side of the move only. The
        highest such point, so a party standing there is plainly on the land."""
        best = None
        for bx, by in sorted(cells):
            for i in range(2, 64, 4):
                for j in range(2, 64, 4):
                    x, z = round(64.0 * bx + i + 0.37, 2), round(-(64.0 * by + j) - 0.29, 2)
                    g = C1._ground(land, x, z, lsn)
                    if not (g.get("walkable") and g.get("part") == "Terrain"):
                        continue
                    w = C1._ground(sea, x, z, ssn)
                    if w.get("stand_y") is not None and w["stand_y"] <= 0.05 and (best is None or g["stand_y"] >
                                                                                   best[0]):
                        best = (g["stand_y"], (x, z))
        assert best is not None, f"no probe on {sorted(cells)}"
        return best[1]
    O = probe(only_from, live, names, with_draft, dnames)
    N = probe(only_to, with_draft, dnames, live, names)
    targets = []
    for key, (x, z) in (("O", O), ("N", N), ("K", C1.CONTROL[1:])):
        g, w = C1._ground(with_draft, x, z, dnames), C1._ground(live, x, z, names)
        targets.append({"key": key, "x": round(x, 3), "z": round(z, 3), "predict_y": g["stand_y"],
                        "part": g.get("part"), "topograph": g.get("topograph"), "live_y": w["stand_y"],
                        "live_part": w.get("part"), "live_topograph": w.get("topograph"),
                        "block": [int(x // 64) % 24, int(-z // 64)]})
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "from": FROM, "to": TO, "draft": str(draft), "edits": edits,
           "removals": gone, "tool": drive, "hand_argv": argv,
           "I1": {"identical": not d1, "differing": d1, "files": len(ed)}, "I2": {"identical": not d2, "differing": d2},
           "stack": names, "tolerance": TOL, "targets": targets}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for t in targets:
        print(f"  {t['key']} at {t['x']}, {t['z']} (block {t['block']}): with the draft y {t['predict_y']:.3f} "
              f"({t['part']} topograph {t['topograph']}); live y {t['live_y']:.3f} ({t['live_part']} topograph "
              f"{t['live_topograph']})")
    print(f"-> {PREP}")


def run():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    tg = {t["key"]: t for t in prep["targets"]}
    O, N, K = ((tg[k]["x"], tg[k]["z"]) for k in ("O", "N", "K"))
    rec = {"prep_t": prep["t"], "steps": {}}

    def tele(key, at):
        r = C2._sh([py, "tools/world_teleport.py", f"{at[0]:.2f}", f"{at[1]:.2f}", "--shot", f"c5r-{key}"], 300)
        rec["steps"][key] = C2._last_json(r)

    r = C2._sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c5r-reach"], 900)
    rec["reach_rc"] = r.returncode
    try:
        if r.returncode == 0:
            tele("N0-O-before", O)
            tele("N0-N-before", N)
            tele("K0-before", K)                                       # off the water before anything else
            rec["promote"] = C2._promote(prep)
            if rec["promote"]["rc"] == 0:
                mark = log.stat().st_size if log.is_file() else 0
                r = C2._sh([py, "tools/world_reload.py", f"{K[0]:.2f}", f"{K[1]:.2f}", "--shot", "c5r-N1-reload"], 600)
                rec["steps"]["N1-reload"] = C2._last_json(r)
                text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
                rec["log"] = [ln.strip() for ln in text.splitlines() if "WorldMeshOverride" in ln
                              and "Block[{}][{}]".format(*tg["N"]["block"]) in ln]
                tele("N2-after", N)
                tele("K1-mid", K)
                tele("N3-O-after", O)
                tele("K2-back", K)
    finally:
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c5r-quit"], 300)   # close the game
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")
    ran = (rec.get("promote") or {}).get("rc") == 0
    rec["N0"] = (y("N0-O-before") is not None and abs(y("N0-O-before") - tg["O"]["live_y"]) <= TOL
                 and y("N0-N-before") is not None and y("N0-N-before") <= 0.05)
    rec["N1"] = ran and y("N1-reload") is not None and abs(y("N1-reload") - tg["K"]["predict_y"]) <= TOL
    rec["N2"] = ran and y("N2-after") is not None and abs(y("N2-after") - tg["N"]["predict_y"]) <= TOL
    rec["N3"] = ran and y("N3-O-after") is not None and y("N3-O-after") <= 0.05
    rec["N4"] = ran and len(rec.get("log") or []) >= 1 and all(SOURCE in ln and "loaded" in ln for ln in rec["log"])
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for k, key in (("N0-O-before", "O"), ("N0-N-before", "N"), ("N1-reload", "K"), ("N2-after", "N"),
                   ("N3-O-after", "O"), ("K2-back", "K")):
        print(f"{k}: y {y(k)}  (live {tg[key]['live_y']:.3f}, with the draft {tg[key]['predict_y']:.3f})")
    print({k: rec[k] for k in ("N0", "N1", "N2", "N3", "N4")}, "promote", (rec.get("promote") or {}).get("seconds"),
          "s")
    print(f"-> {RESULT}")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        build()
    elif cmd == ["run"]:
        run()
    else:
        raise SystemExit(__doc__)
