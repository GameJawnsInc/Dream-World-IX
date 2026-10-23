"""Rung C4 in game: Promote writes an editor draft into the live folder, and the RUNNING game follows with no DLL.

    py studies/overworld-editor/c4_lab.py build   # the tool places + accepts a forest into a fresh draft; predictions
    py studies/overworld-editor/c4_lab.py run     # reach the world; before / promote / no reload / reload / revert

THE CLAIM: `world-promote <draft>` puts the editor's edit into FF9CustomMap-world (backed up, ledgered, disc 4
mirrored), the game keeps drawing the world it loaded until it loads the world again, and `tools/world_reload.py`
(the World tab's "Show in game": into bench field 6603 and back out) makes it re-read every override; `--revert`
then puts the live folder back byte for byte and the next reload shows the old ground again. The live folder ends as
it began, apart from the promote's backups and ledger rows.

REGISTERED PREDICTIONS (c4_prep.json, written by `build` before the game opens; tolerance 0.15), at SPOT:
  P0 before the promote the party stands on the grass (the live stack's height);
  P1 after the promote, teleported there WITHOUT a reload, it still stands on the grass (the game caches the world);
  P2 after world_reload.py it stands on the carried canopy, the height point_info predicts with the draft drawn in
     place of FF9CustomMap-world, at least 0.5 from the grass (the read-back tells them apart);
  P3 after `--revert` and another reload it stands on the grass again;
  P4 the live folder's world files after the revert are byte-identical to before the promote (backups aside);
  P5 Memoria.log: the reload loaded the edited blocks from FF9CustomMap-world.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lab as C1                                                    # noqa: E402  (the tool driver, the paths)

GAME, KIT, REPO = C1.GAME, C1.KIT, C1.REPO
SOURCE = "FF9CustomMap-world"
SPOT, DONOR = (188.0, -1220.0), (13, 15)                             # the south-west island, clear of the C1 lab
OUT = HERE / "out" / "c4_lab"
PREP = HERE / "out" / "c4_prep.json"
RESULT = HERE / "out" / "c4_result.json"
TOL = 0.15


def _world_tree(folder: Path) -> dict:
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (folder / "FF9_Data" / "WorldMap").rglob("*") if p.is_file() and ".bak-" not in p.name}


def build():
    from ff9mapkit.world import draft as D, render as R
    if OUT.exists():
        shutil.rmtree(OUT)
    drive = C1._drive_tool(OUT / "drafts", spot=SPOT, donor=DONOR)
    draft = Path(drive["draft"])
    print(f"tool: check {drive['check_s']} s, accept {drive['accept_s']} s\n  {drive['accepted']}")
    edits = D.edits(draft)
    names = [p.name for p in R.game_stack(GAME)]
    live = R.RenderSite(cells=(), disc=1, game=GAME, stack=tuple(GAME / n for n in names))
    with_draft = R.RenderSite(cells=(), disc=1, game=GAME,
                              stack=tuple(draft if n == SOURCE else GAME / n for n in names))
    g_live = C1._ground(live, *SPOT, names)
    g_draft = C1._ground(with_draft, *SPOT, [draft.name if n == SOURCE else n for n in names])
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "spot": SPOT, "donor": DONOR, "draft": str(draft),
           "edits": edits, "tool": drive, "stack": names, "tolerance": TOL,
           "grass_y": g_live["stand_y"], "canopy_y": g_draft["stand_y"], "canopy": bool(g_draft.get("canopy")),
           "separation": abs(g_draft["stand_y"] - g_live["stand_y"])}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(f"  at {SPOT}: grass {rec['grass_y']:.3f}, canopy {rec['canopy_y']:.3f} "
          f"(separation {rec['separation']:.2f}); the draft edited {edits}")
    assert rec["canopy"] and rec["separation"] >= 0.5, "the prediction cannot tell the canopy from the grass"
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


def run():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    x, z = prep["spot"]
    rec = {"prep_t": prep["t"], "steps": {}}
    src = GAME / SOURCE
    tree0 = _world_tree(src)
    promoted = False

    def tele(key):
        r = _sh([py, "tools/world_teleport.py", f"{x:.2f}", f"{z:.2f}", "--shot", f"c4-{key}"], 300)
        rec["steps"][key] = _last_json(r)

    def reload(key):
        r = _sh([py, "tools/world_reload.py", f"{x:.2f}", f"{z:.2f}", "--shot", f"c4-{key}"], 600)
        rec["steps"][key] = _last_json(r)

    def promote(*extra):
        # from the kit folder, as the World tab's job runs it (worldforest.kit_cwd): at the repo root `-m ff9mapkit`
        # finds the distribution folder, not the package (the first run's promote never ran)
        r = _sh([py, "-m", "ff9mapkit", "world-promote", prep["draft"], *extra], 600, cwd=KIT)
        return {"rc": r.returncode, "seconds": r.seconds, "out": r.stdout[-800:], "err": r.stderr[-800:]}

    try:
        r = _sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "c4-reach"], 900)
        rec["reach_rc"] = r.returncode
        if r.returncode == 0:
            tele("P0-before")
            rec["promote"] = promote()
            promoted = rec["promote"]["rc"] == 0
            tele("P1-no-reload")
            mark = log.stat().st_size if log.is_file() else 0
            reload("P2-reload")
            text = log.read_bytes()[mark:].decode("utf-8", "replace") if log.is_file() else ""
            rec["log"] = [ln.strip() for ln in text.splitlines()
                          if "WorldMeshOverride" in ln and any(f"Block[{a}][{b}] Terrain" in ln for a, b in
                                                               [tuple(map(int, re.findall(r"\[(\d+)\]", e)[:2]))
                                                                for e in prep["edits"] if "/Disc1/" in e])]
            rec["revert"] = promote("--revert")
            promoted = rec["revert"]["rc"] != 0
            reload("P3-reverted")
        _sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c4-quit"], 300)
    finally:
        if promoted:                                                  # never leave the edit live on a failed run
            rec["cleanup_revert"] = promote("--revert")
        tree1 = _world_tree(src)
        rec["P4"] = {"identical": tree0 == tree1,
                     "differing": sorted(k for k in set(tree0) | set(tree1) if tree0.get(k) != tree1.get(k))}
        RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    def y(key):
        return (rec["steps"].get(key) or {}).get("world_y")
    g, c = prep["grass_y"], prep["canopy_y"]
    ran = (rec.get("promote") or {}).get("rc") == 0 and (rec.get("revert") or {}).get("rc") == 0
    rec["promote_and_revert_ran"] = ran                               # P1-P5 mean nothing without both
    rec["P0"] = y("P0-before") is not None and abs(y("P0-before") - g) <= TOL
    rec["P1"] = ran and y("P1-no-reload") is not None and abs(y("P1-no-reload") - g) <= TOL
    rec["P2"] = ran and y("P2-reload") is not None and abs(y("P2-reload") - c) <= TOL
    rec["P3"] = ran and y("P3-reverted") is not None and abs(y("P3-reverted") - g) <= TOL
    rec["P5"] = ran and len(rec.get("log") or []) == len([e for e in prep["edits"] if "/Disc1/" in e]) and         all(SOURCE in ln and "loaded" in ln for ln in rec["log"])
    rec["P4"]["judged"] = ran
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for k in ("P0-before", "P1-no-reload", "P2-reload", "P3-reverted"):
        print(f"{k}: y {y(k)}  (grass {g:.3f}, canopy {c:.3f})  seconds {(rec['steps'].get(k) or {}).get('seconds')}")
    print({k: rec[k] for k in ("P0", "P1", "P2", "P3", "P5")}, "P4", rec["P4"]["identical"])
    print("promote", rec.get("promote", {}).get("seconds"), "s; revert", rec.get("revert", {}).get("seconds"), "s")
    print(f"-> {RESULT}")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        build()
    elif cmd == ["run"]:
        run()
    else:
        raise SystemExit(__doc__)
