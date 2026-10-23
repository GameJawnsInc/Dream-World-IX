"""Rung C5 in game: the island the World tab's sink tool sank into a draft, promoted, and seen in the running game.

    py studies/overworld-editor/c5_lab.py build    # the tool picks + accepts the sink; identity; predictions
    py studies/overworld-editor/c5_lab.py run      # reach the world; before / promote / reload / after; quit

THE EDITOR'S PATH (as C1-C3): the real SinkTool (workspace/worldsink.py) with its real runner, against the real
install: the click at ISLAND picks the island from the cached island list, Check runs `world-sink --dry-run`, Accept
runs `world-sink` into a fresh draft on disc 1 and then on disc 4 (the draft's own disc-4 step). Then the two calls
typed by hand into a second draft, and every world file of the two drafts compared (I1).

THE GAME FOLLOWS (C4's route): `world-promote` puts the draft into FF9CustomMap-world (the live mirror copies disc 1
over disc 4 where they match, holds the draft's disc-4 sink where they differ) and `tools/world_reload.py` makes the
running game re-read the world, landing at the Landing Site K (land, the control). The party is put back on K last:
it never stays on the water where the island was.

REGISTERED PREDICTIONS (c5_prep.json, written by `build` before the game opens; tolerance 0.15):
  S0 before the promote, at the island's own point I the party stands on its land (the live stack's height);
  S1 after the promote and the reload, at K the party stands where it stood (the control: the sink touched only the
     island's block);
  S2 at I it stands where point_info predicts with the draft in place of FF9CustomMap-world (no land: the sea), at
     least 0.5 below the land;
  S3 Memoria.log: the reload loaded the edited disc-1 blocks from FF9CustomMap-world.
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
ISLAND = (249.556, -565.214)                                           # 115 u2, one block (3,8), west of the Landing Site
OUT = HERE / "out" / "c5_lab"
PREP = HERE / "out" / "c5_prep.json"
RESULT = HERE / "out" / "c5_result.json"
TOL = 0.15


def _world(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh") if ".bak-" not in p.name}


def _drive_tool(drafts: Path) -> dict:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldforest import QProcessRunner
    from ff9mapkit.workspace.worldsink import ISLANDS, SinkTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    pal = pick_palette("dark")
    runner = QProcessRunner()
    argvs = []
    real_start = runner.start

    def start(argv, cwd, done):
        argvs.append([str(a) for a in argv])
        real_start(argv, cwd, done)
    runner.start = start
    tool = SinkTool(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE,
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
    assert pump(lambda: tool._ix is not None and ISLANDS in tool._outlines, 600), tool.verdict_lbl.text()
    tool.place(ISLAND[0] + 1.0, ISLAND[1] + 1.0, 3.0)                 # a click on the island, not on its point
    picked = tool.island_lbl.text()
    t0 = time.time()
    assert pump(lambda: tool._current_verdict() is not None, 300), tool.verdict_lbl.text()
    t_check = time.time() - t0
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    check_text = tool.verdict_lbl.text()
    t0 = time.time()
    tool.accept_btn.click()
    assert pump(lambda: tool._job is None and tool.center is None, 600), tool.verdict_lbl.text()
    return {"argvs": argvs, "picked": picked, "at": list(tool._last_center or ISLAND), "check": check_text,
            "accepted": tool.verdict_lbl.text(), "draft": str(tool.draft()), "check_s": round(t_check, 1),
            "accept_s": round(time.time() - t0, 1), "disc4": getattr(tool, "_disc4", None)}


def build():
    from ff9mapkit.world import draft as D, render as R, sinkedit as SE
    if OUT.exists():
        shutil.rmtree(OUT)
    drive = _drive_tool(OUT / "drafts")
    draft = Path(drive["draft"])
    print(f"tool: {drive['picked']}\n  check {drive['check_s']} s: {drive['check']}\n  accept {drive['accept_s']} s: "
          f"{drive['accepted']} (disc 4 {'sunk' if drive['disc4'] else 'refused'})")
    at = tuple(float(v) for v in drive["argvs"][-1][drive["argvs"][-1].index("--at") + 1:][:2])
    hand = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "hand")
    for argv in SE.commands(hand, at):
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
    targets = []
    for key, (x, z) in (("I", at), ("K", C1.CONTROL[1:])):
        g, w = C1._ground(with_draft, x, z, dnames), C1._ground(live, x, z, names)
        targets.append({"key": key, "x": round(x, 3), "z": round(z, 3), "predict_y": g["stand_y"],
                        "part": g.get("part"), "topograph": g.get("topograph"), "live_y": w["stand_y"],
                        "live_part": w.get("part"), "live_topograph": w.get("topograph"),
                        "separation": abs(g["stand_y"] - w["stand_y"])})
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "island": ISLAND, "at": at, "draft": str(draft), "edits": edits,
           "tool": drive, "I1": {"identical": not diff, "differing": diff, "files": len(ed)}, "stack": names,
           "tolerance": TOL, "targets": targets}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for t in targets:
        print(f"  {t['key']} at {t['x']}, {t['z']}: with the draft y {t['predict_y']:.3f} ({t['part']} topograph "
              f"{t['topograph']}); live y {t['live_y']:.3f} ({t['live_part']} topograph {t['live_topograph']}), "
              f"separation {t['separation']:.2f}")
    assert targets[0]["separation"] >= 0.5, "the island's point cannot tell land from sea"
    print(f"-> {PREP}")


def run():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    tg = {t["key"]: t for t in prep["targets"]}
    island, K = (tg["I"]["x"], tg["I"]["z"]), (tg["K"]["x"], tg["K"]["z"])
    rec = {"prep_t": prep["t"], "steps": {}}

    def tele(key, at):
        r = C2._sh([py, "tools/world_teleport.py", f"{at[0]:.2f}", f"{at[1]:.2f}", "--shot", f"c5-{key}"], 300)
        rec["steps"][key] = C2._last_json(r)

    r = C2._sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c5-reach"], 900)
    rec["reach_rc"] = r.returncode
    if r.returncode == 0:
        tele("S0-island-before", island)
        tele("K0-before", K)
        rec["promote"] = C2._promote(prep)
        if rec["promote"]["rc"] == 0:
            mark = log.stat().st_size if log.is_file() else 0
            r = C2._sh([py, "tools/world_reload.py", f"{K[0]:.2f}", f"{K[1]:.2f}", "--shot", "c5-S1-reload"], 600)
            rec["steps"]["S1-reload"] = C2._last_json(r)
            text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
            cells = {tuple(map(int, re.findall(r"\[(\d+)\]", e)[:2])) for e in prep["edits"] if "/Disc1/" in e}
            rec["log"] = [ln.strip() for ln in text.splitlines() if "WorldMeshOverride" in ln
                          and any(f"Block[{a}][{b}]" in ln for a, b in cells)]
            tele("S2-island-after", island)
            tele("K1-back", K)                                        # never left standing on the water
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c5-quit"], 300)   # close the game
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")
    ran = (rec.get("promote") or {}).get("rc") == 0
    rec["S0"] = y("S0-island-before") is not None and abs(y("S0-island-before") - tg["I"]["live_y"]) <= TOL
    rec["S1"] = ran and y("S1-reload") is not None and abs(y("S1-reload") - tg["K"]["predict_y"]) <= TOL
    rec["S2"] = ran and y("S2-island-after") is not None and abs(y("S2-island-after") - tg["I"]["predict_y"]) <= TOL
    n_cells = len({e for e in prep["edits"] if "/Disc1/" in e})
    rec["S3"] = ran and len(rec.get("log") or []) >= 1 and all(SOURCE in ln and "loaded" in ln for ln in rec["log"])
    rec["edited_disc1_files"] = n_cells
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for k, key in (("S0-island-before", "I"), ("S1-reload", "K"), ("S2-island-after", "I"), ("K1-back", "K")):
        print(f"{k}: y {y(k)}  (live {tg[key]['live_y']:.3f}, with the draft {tg[key]['predict_y']:.3f})")
    print({k: rec[k] for k in ("S0", "S1", "S2", "S3")}, "promote", (rec.get("promote") or {}).get("seconds"), "s")
    print(f"-> {RESULT}")


def resume():
    """The first run's promote wrote the live folder and then failed to write its record (the record folder was never
    made: the live folder had no file at the island's cells -- fixed in world/draft.py, the record recovered by
    hand). The game is still open on the world: run the steps after the promote."""
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    rec = json.loads(RESULT.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    tg = {t["key"]: t for t in prep["targets"]}
    island, K = (tg["I"]["x"], tg["I"]["z"]), (tg["K"]["x"], tg["K"]["z"])
    rec["promote_recovered"] = "the live writes and the mirror pass ran; promote.json failed (no record folder); " \
                               "the record was rebuilt from the state it left and the draft rebased"

    def tele(key, at):
        r = C2._sh([py, "tools/world_teleport.py", f"{at[0]:.2f}", f"{at[1]:.2f}", "--shot", f"c5-{key}"], 300)
        rec["steps"][key] = C2._last_json(r)
    mark = log.stat().st_size if log.is_file() else 0
    r = C2._sh([py, "tools/world_reload.py", f"{K[0]:.2f}", f"{K[1]:.2f}", "--shot", "c5-S1-reload"], 600)
    rec["steps"]["S1-reload"] = C2._last_json(r)
    text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
    cells = {tuple(map(int, re.findall(r"\[(\d+)\]", e)[:2])) for e in prep["edits"] if "/Disc1/" in e}
    rec["log"] = [ln.strip() for ln in text.splitlines() if "WorldMeshOverride" in ln
                  and any(f"Block[{a}][{b}]" in ln for a, b in cells)]
    tele("S2-island-after", island)
    tele("K1-back", K)
    C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c5-quit"], 300)       # close the game

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")
    rec["S1"] = y("S1-reload") is not None and abs(y("S1-reload") - tg["K"]["predict_y"]) <= TOL
    rec["S2"] = y("S2-island-after") is not None and abs(y("S2-island-after") - tg["I"]["predict_y"]) <= TOL
    rec["S3"] = len(rec["log"]) >= 1 and all(SOURCE in ln and "loaded" in ln for ln in rec["log"])
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for k, key in (("S0-island-before", "I"), ("S1-reload", "K"), ("S2-island-after", "I"), ("K1-back", "K")):
        print(f"{k}: y {y(k)}  (live {tg[key]['live_y']:.3f}, with the draft {tg[key]['predict_y']:.3f})")
    print({k: rec.get(k) for k in ("S0", "S1", "S2", "S3")}, len(rec["log"]), "log lines")
    print(f"-> {RESULT}")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        build()
    elif cmd == ["run"]:
        run()
    elif cmd == ["resume"]:
        resume()
    else:
        raise SystemExit(__doc__)
