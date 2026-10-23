"""Rung C2 in game: the mountain the World tab's mountain tool accepted into a draft, promoted, and walked.

    py studies/overworld-editor/c2_lab.py build    # the tool places + accepts the massif; identity; predictions
    py studies/overworld-editor/c2_lab.py run      # reach the world; before / promote / reload / summit; KEEPS the game
    py studies/overworld-editor/c2_lab.py revert   # after the owner's walk: world-promote --revert (byte-exact)

THE EDITOR'S PATH, NOT A REPLAY OF IT (as C1). `build` drives the real MountainTool (workspace/worldmountain.py)
against the real install with its real runner: the ghost goes to SPOT with Uaho turned ANGLE and stretched HEIGHT,
the tool's Check runs `world-mountain --dry-run` as a subprocess and its Accept runs `world-mountain` into a draft
under out/c2_lab/drafts. Then, on a second draft of the same folder, the hand-typed command runs, and every world
file of the two drafts is compared (I1: the C2 acceptance on the real island).

THE GAME FOLLOWS (C4's route, no DLL): `run` promotes the draft into FF9CustomMap-world (world-promote: backed up,
ledgered, disc 4 mirrored, snapshotted) and `tools/world_reload.py` makes the running game re-read the world. The
game is left open on the massif for the owner's walk; `revert` puts the folder back byte for byte afterwards.

REGISTERED PREDICTIONS (c2_prep.json, written by `build` before the game opens; tolerance 0.15):
  M0 before the promote, at the summit probe S the party stands on the island's grass (the live stack's height);
  M1 after the promote and the reload, at S it stands on the carried rock (topograph 49 has no walk sink) at the
     height point_info predicts with the draft drawn in place of FF9CustomMap-world, at least 0.5 above the grass;
  M2 at the carve's own teleport point T (beside the massif) it stands where the draft predicts (the apron);
  M3 Memoria.log: the reload loaded every edited disc-1 block from FF9CustomMap-world.
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

GAME, KIT, REPO = C1.GAME, C1.KIT, C1.REPO
SOURCE = "FF9CustomMap-world"
SPOT, DONOR, ANGLE, HEIGHT = (190.0, -1228.0), "0,0", 300, 1.5     # Uaho on the south-west island, turned + taller
OUT = HERE / "out" / "c2_lab"
PREP = HERE / "out" / "c2_prep.json"
RESULT = HERE / "out" / "c2_result.json"
TOL = 0.15


def _world_files(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "FF9_Data" / "WorldMap").rglob("*") if p.is_file() and ".bak-" not in p.name}


def _drive_tool(drafts: Path) -> dict:
    """The mountain tool, placed and accepted the way a click does, against the real install (offscreen: the tool
    needs no GL; its jobs are real world-mountain subprocesses)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldforest import QProcessRunner
    from ff9mapkit.workspace.worldmountain import MountainTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    pal = pick_palette("dark")
    runner = QProcessRunner()
    argvs = []
    real_start = runner.start

    def start(argv, cwd, done):
        argvs.append([str(a) for a in argv])
        real_start(argv, cwd, done)
    runner.start = start
    tool = MountainTool(pal, WorldView3DPanel(pal), game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE,
                        runner=runner, drafts_root=drafts)
    tool.donor_box.setCurrentIndex(tool.donor_box.findData(DONOR))
    tool.open_tool()

    def pump(until, sec):
        t = time.time()
        while time.time() - t < sec:
            app.processEvents()
            if until():
                return True
            time.sleep(0.02)
        return False
    assert pump(lambda: tool._ix is not None and DONOR in tool._outlines, 120), "the tool never read the island"
    tool.angle.setValue(ANGLE)
    tool.rock_height.setValue(HEIGHT)
    tool.place(*SPOT, 3.0)
    preview = dict(tool._preview or {})
    t0 = time.time()
    assert pump(lambda: tool._current_verdict() is not None, 180), tool.verdict_lbl.text()
    t_check = time.time() - t0
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    check_text, chip = tool.verdict_lbl.text(), tool.ground_chip.text()
    t0 = time.time()
    tool.accept_btn.click()
    assert pump(lambda: tool._job is None and tool.center is None, 180), tool.verdict_lbl.text()
    t_accept = time.time() - t0
    return {"argvs": argvs, "preview": {k: preview.get(k) for k in ("ok", "gate", "why")}, "chip": chip,
            "check": check_text, "accepted": tool.verdict_lbl.text(), "draft": str(tool.draft()),
            "show_point": tool._last_center, "check_s": round(t_check, 1), "accept_s": round(t_accept, 1)}


def _summit(draft: Path):
    """The draft's highest carried-rock vertex near SPOT, and a probe beside it off the 4u lattice (a teleport on a
    lattice line lands on an edge)."""
    from ff9mapkit.world import interior as IN
    from ff9mapkit.world.extract import decode_id
    soup = IN.soup_from_blocks(IN.read_deployed_blocks(str(draft), near=SPOT, reach=48.0, game=GAME))
    best = None
    for tri, m in zip(soup["tris"], soup["meta"]):
        if decode_id(int(round(m[1])))["topograph"] in IN.MOUNTAIN_ROCK_TOPOS:
            for i in tri:
                p = soup["pos"][i]
                if best is None or p[1] > best[1]:
                    best = p
    return best, (round(best[0] + 0.37, 2), round(best[2] - 0.29, 2))


def build():
    from ff9mapkit.world import draft as D, render as R
    if OUT.exists():
        shutil.rmtree(OUT)
    drafts, hand_root = OUT / "drafts", OUT / "hand"
    drive = _drive_tool(drafts)
    draft = Path(drive["draft"])
    print(f"tool: check {drive['check_s']} s, accept {drive['accept_s']} s; chip {drive['chip']!r}\n"
          f"  {drive['check']}\n  {drive['accepted']}")
    hand = D.ensure_draft(GAME / SOURCE, game=GAME, root=hand_root)
    hand_argv = [sys.executable, "-m", "ff9mapkit", "world-mountain", "--mod-folder", str(hand),
                 "--center", "{:g},{:g}".format(*SPOT), "--donor", DONOR, "--rot", str(ANGLE),
                 "--rock-height", f"{HEIGHT:g}"]
    r = subprocess.run(hand_argv, cwd=KIT, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    ed, hd = _world_files(draft), _world_files(hand)
    diff = sorted(k for k in set(ed) | set(hd) if ed.get(k) != hd.get(k))
    edits = D.edits(draft)
    i1 = {"identical": not diff, "differing": diff, "files": len(ed), "edited": edits,
          "hand_argv": hand_argv[3:], "tool_argvs": [a[3:] for a in drive["argvs"]]}
    print(f"I1 identity: {'IDENTICAL' if not diff else 'DIFFERS ' + str(diff)} over {len(ed)} world files; "
          f"the draft edited {len(edits)}: {edits}")
    assert not diff
    names = [p.name for p in R.game_stack(GAME)]
    live = R.RenderSite(cells=(), disc=1, game=GAME, stack=tuple(GAME / n for n in names))
    with_draft = R.RenderSite(cells=(), disc=1, game=GAME,
                              stack=tuple(draft if n == SOURCE else GAME / n for n in names))
    dnames = [draft.name if n == SOURCE else n for n in names]
    peak, S = _summit(draft)
    T = tuple(round(float(c), 2) for c in drive["show_point"])
    targets = []
    for key, (x, z) in (("S", S), ("T", T), ("K", C1.CONTROL[1:])):
        g, w = C1._ground(with_draft, x, z, dnames), C1._ground(live, x, z, names)
        targets.append({"key": key, "x": x, "z": z, "predict_y": g["stand_y"], "topograph": g.get("topograph"),
                        "live_y": w["stand_y"], "live_topograph": w.get("topograph"),
                        "separation": abs(g["stand_y"] - w["stand_y"])})
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "spot": SPOT, "donor": DONOR, "angle": ANGLE, "height": HEIGHT,
           "draft": str(draft), "edits": edits, "tool": drive, "I1": i1, "stack": names, "tolerance": TOL,
           "peak": [round(float(c), 3) for c in peak], "targets": targets}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for t in targets:
        print(f"  {t['key']} at {t['x']}, {t['z']}: predict y {t['predict_y']:.3f} (topograph {t['topograph']}); "
              f"live {t['live_y']:.3f} (topograph {t['live_topograph']}), separation {t['separation']:.2f}")
    s = targets[0]
    assert s["topograph"] in (49,) and s["separation"] >= 0.5, "the summit probe cannot tell rock from grass"
    print(f"-> {PREP}")


def _sh(argv, timeout, cwd=REPO):
    print("$", " ".join(str(a) for a in argv), flush=True)
    t = time.time()
    r = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    r.seconds = round(time.time() - t, 2)
    print(r.stdout[-2500:], flush=True)
    if r.returncode:
        print(r.stderr[-2500:], flush=True)
    return r


def _last_json(r):
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"ok": False, "error": r.stderr[-500:]}


def _promote(prep, *extra):
    # from the kit folder, as the World tab's job runs it (worldforest.kit_cwd)
    r = _sh([sys.executable, "-m", "ff9mapkit", "world-promote", prep["draft"], *extra], 600, cwd=KIT)
    return {"rc": r.returncode, "seconds": r.seconds, "out": r.stdout[-800:], "err": r.stderr[-800:]}


def run():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    tg = {t["key"]: t for t in prep["targets"]}
    S, T = (tg["S"]["x"], tg["S"]["z"]), (tg["T"]["x"], tg["T"]["z"])
    rec = {"prep_t": prep["t"], "steps": {}}

    def tele(key, at):
        r = _sh([py, "tools/world_teleport.py", f"{at[0]:.2f}", f"{at[1]:.2f}", "--shot", f"c2-{key}"], 300)
        rec["steps"][key] = _last_json(r)

    r = _sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c2-reach"], 900)
    rec["reach_rc"] = r.returncode
    if r.returncode == 0:
        tele("M0-before", S)
        rec["promote"] = _promote(prep)
        if rec["promote"]["rc"] == 0:
            mark = log.stat().st_size if log.is_file() else 0
            r = _sh([py, "tools/world_reload.py", f"{T[0]:.2f}", f"{T[1]:.2f}", "--shot", "c2-M2-reload"], 600)
            rec["steps"]["M2-reload"] = _last_json(r)
            text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
            cells = [tuple(map(int, re.findall(r"\[(\d+)\]", e)[:2])) for e in prep["edits"] if "/Disc1/" in e]
            rec["log"] = [ln.strip() for ln in text.splitlines() if "WorldMeshOverride" in ln
                          and any(f"Block[{a}][{b}] Terrain" in ln for a, b in cells)]
            tele("M1-summit", S)
            tele("M2-beside", T)                         # left here, facing nothing in particular: the owner walks
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")
    ran = (rec.get("promote") or {}).get("rc") == 0
    rec["M0"] = y("M0-before") is not None and abs(y("M0-before") - tg["S"]["live_y"]) <= TOL
    rec["M1"] = ran and y("M1-summit") is not None and abs(y("M1-summit") - tg["S"]["predict_y"]) <= TOL
    rec["M2"] = ran and y("M2-beside") is not None and abs(y("M2-beside") - tg["T"]["predict_y"]) <= TOL
    n_cells = len([e for e in prep["edits"] if "/Disc1/" in e and "Terrain" in e])
    rec["M3"] = ran and len(rec.get("log") or []) >= n_cells and all(SOURCE in ln and "loaded" in ln
                                                                      for ln in rec["log"])
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for k, key in (("M0-before", "S"), ("M1-summit", "S"), ("M2-beside", "T")):
        print(f"{k}: y {y(k)}  (live {tg[key]['live_y']:.3f}, with the draft {tg[key]['predict_y']:.3f})")
    print({k: rec[k] for k in ("M0", "M1", "M2", "M3")}, "promote", (rec.get("promote") or {}).get("seconds"), "s")
    print(f"-> {RESULT}\nThe game is left open on the promoted massif. After the walk: c2_lab.py revert")


def revert():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    out = _promote(prep, "--revert")
    rec = json.loads(RESULT.read_text(encoding="utf-8")) if RESULT.is_file() else {}
    rec["revert"] = out
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print("reverted" if out["rc"] == 0 else "REVERT REFUSED", out["out"] or out["err"])


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        build()
    elif cmd == ["run"]:
        run()
    elif cmd == ["revert"]:
        revert()
    else:
        raise SystemExit(__doc__)
