"""Rung C5 in game, the island: a new island the World tab's island tool minted into a draft, promoted, stood on.

    py studies/overworld-editor/c5i_lab.py build   # the tool places + accepts the island; identity; predictions
    py studies/overworld-editor/c5i_lab.py run     # reach the world; before / promote / reload / after; quit

THE EDITOR'S PATH (as the others): the real IslandTool (workspace/worldisland.py) with its real runner against the real
install: the ghost at CENTER with SEED, Check runs `world-island --dry-run`, Accept mints into a fresh draft. Then the
command typed by hand into a second draft, every world file compared (I1).

THE NEW BLOCK. Block (4,5) is open ocean in stock: no prefab of its own, and no folder of the stack overrides it.
The engine binds a block's overrides when the world loads, so the reload (C4's route) is what shows it.

REGISTERED PREDICTIONS (c5i_prep.json, written by `build` before the game opens; tolerance 0.15):
  N0 before the promote, at the island's centre C the party is in the open sea: at or below the surface (y <= 0.05;
     the engine seats a party in water below the sea mesh -- C5's sink measured 0.586 in Sea3);
  N1 after the promote and the reload, at the Landing Site K (the control) it stands where it stood;
  N2 at C it stands on the new island's land, at the height point_info predicts with the draft in place;
  N3 Memoria.log: the reload loaded block (4,5) from FF9CustomMap-world.
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
CENTER, SEED = (288.0, -352.0), 5                                      # block (4,5), north of the Landing Site
OUT = HERE / "out" / "c5i_lab"
PREP = HERE / "out" / "c5i_prep.json"
RESULT = HERE / "out" / "c5i_result.json"
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
    from ff9mapkit.workspace.worldisland import ISLAND, IslandTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    pal = pick_palette("dark")
    runner = QProcessRunner()
    argvs = []
    real_start = runner.start

    def start(argv, cwd, done):
        argvs.append([str(a) for a in argv])
        real_start(argv, cwd, done)
    runner.start = start
    tool = IslandTool(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE,
                      runner=runner, drafts_root=drafts)
    tool.seed.setValue(SEED)
    tool.open_tool()

    def pump(until, sec):
        t = time.time()
        while time.time() - t < sec:
            app.processEvents()
            if until():
                return True
            time.sleep(0.02)
        return False
    assert pump(lambda: tool._ix is not None and ISLAND in tool._outlines, 300), tool.verdict_lbl.text()
    tool.place(*CENTER, 0.0)
    preview = dict(tool._preview or {})
    t0 = time.time()
    assert pump(lambda: tool._current_verdict() is not None, 300), tool.verdict_lbl.text()
    t_check = time.time() - t0
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    check_text = tool.verdict_lbl.text()
    t0 = time.time()
    tool.accept_btn.click()
    assert pump(lambda: tool._job is None and tool.center is None, 600), tool.verdict_lbl.text()
    return {"argvs": argvs, "preview": {k: preview.get(k) for k in ("ok", "why", "blocks")}, "check": check_text,
            "accepted": tool.verdict_lbl.text(), "draft": str(tool.draft()), "check_s": round(t_check, 1),
            "accept_s": round(time.time() - t0, 1), "show": tool._last_center}


def build():
    from ff9mapkit.world import draft as D, render as R
    if OUT.exists():
        shutil.rmtree(OUT)
    drive = _drive_tool(OUT / "drafts")
    draft = Path(drive["draft"])
    print(f"tool: preview {drive['preview']}\n  check {drive['check_s']} s: {drive['check']}\n"
          f"  accept {drive['accept_s']} s: {drive['accepted']}")
    argv = drive["argvs"][-1][3:]
    hand = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "hand")
    hand_argv = [str(hand) if a == drive["draft"] else a for a in argv]
    hand_argv = [a for a in hand_argv]
    i = hand_argv.index("--report-json")
    hand_argv = hand_argv[:i] + hand_argv[i + 2:]
    r = subprocess.run([sys.executable, "-m", "ff9mapkit"] + hand_argv, cwd=KIT, capture_output=True, text=True,
                       timeout=900)
    assert r.returncode == 0, r.stderr[-2000:]
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
    C = (CENTER[0] + 0.37, CENTER[1] - 0.29)                           # off the 4u lattice
    targets = []
    for key, (x, z) in (("C", C), ("K", C1.CONTROL[1:])):
        g, w = C1._ground(with_draft, x, z, dnames), C1._ground(live, x, z, names)
        targets.append({"key": key, "x": round(x, 3), "z": round(z, 3), "predict_y": g["stand_y"],
                        "part": g.get("part"), "topograph": g.get("topograph"), "live_y": w["stand_y"],
                        "live_part": w.get("part"), "live_topograph": w.get("topograph")})
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "center": CENTER, "seed": SEED, "draft": str(draft),
           "edits": edits, "tool": drive, "hand_argv": hand_argv, "I1": {"identical": not diff, "differing": diff,
                                                                          "files": len(ed)},
           "stack": names, "tolerance": TOL, "targets": targets}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for t in targets:
        print(f"  {t['key']} at {t['x']}, {t['z']}: with the draft y {t['predict_y']:.3f} ({t['part']} topograph "
              f"{t['topograph']}); live y {t['live_y']:.3f} ({t['live_part']} topograph {t['live_topograph']})")
    print(f"-> {PREP}")


def run():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    tg = {t["key"]: t for t in prep["targets"]}
    Cp, K = (tg["C"]["x"], tg["C"]["z"]), (tg["K"]["x"], tg["K"]["z"])
    rec = {"prep_t": prep["t"], "steps": {}}

    def tele(key, at):
        r = C2._sh([py, "tools/world_teleport.py", f"{at[0]:.2f}", f"{at[1]:.2f}", "--shot", f"c5i-{key}"], 300)
        rec["steps"][key] = C2._last_json(r)

    r = C2._sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c5i-reach"], 900)
    rec["reach_rc"] = r.returncode
    try:
        if r.returncode == 0:
            tele("N0-before", Cp)
            tele("K0-before", K)                                       # off the water before anything else
            rec["promote"] = C2._promote(prep)
            if rec["promote"]["rc"] == 0:
                mark = log.stat().st_size if log.is_file() else 0
                r = C2._sh([py, "tools/world_reload.py", f"{K[0]:.2f}", f"{K[1]:.2f}", "--shot", "c5i-N1-reload"], 600)
                rec["steps"]["N1-reload"] = C2._last_json(r)
                text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
                rec["log"] = [ln.strip() for ln in text.splitlines() if "WorldMeshOverride" in ln
                              and "Block[4][5]" in ln]
                tele("N2-after", Cp)
                tele("K1-back", K)
    finally:
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c5i-quit"], 300)   # close the game
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")
    ran = (rec.get("promote") or {}).get("rc") == 0
    rec["N0"] = y("N0-before") is not None and y("N0-before") <= 0.05
    rec["N1"] = ran and y("N1-reload") is not None and abs(y("N1-reload") - tg["K"]["predict_y"]) <= TOL
    rec["N2"] = ran and y("N2-after") is not None and abs(y("N2-after") - tg["C"]["predict_y"]) <= TOL
    rec["N3"] = ran and len(rec.get("log") or []) >= 1 and all(SOURCE in ln and "loaded" in ln for ln in rec["log"])
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for k, key in (("N0-before", "C"), ("N1-reload", "K"), ("N2-after", "C"), ("K1-back", "K")):
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
