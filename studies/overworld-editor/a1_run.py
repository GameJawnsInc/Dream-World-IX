"""Rung A1's in-game check, the driver: reach the world, teleport to each registered pick, judge, quit.

    py studies/overworld-editor/a1_prep.py        # first: the targets and predictions (out/a1_prep.json)
    py studies/overworld-editor/a1_run.py         # -> out/a1_result.json, the verdicts printed

1. ``tools/play.py a1_reach.py --keep-open``: the game on the disc-1 world map, the harness disarmed.
2. For each target, ``tools/world_teleport.py X Z --shot NAME`` -- the very argv the World tab's "Teleport game here"
   runs -- attached to that game; its JSON line is the read-back.
3. ``tools/play.py a1_quit.py --attach``: the game closed (it was launched for this check).
Verdicts P1-P3 against a1_prep.py's registered tolerances.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PREP = json.loads((HERE / "out" / "a1_prep.json").read_text(encoding="utf-8"))
OUT = HERE / "out" / "a1_result.json"


def _run(argv, timeout):
    print("$", " ".join(argv))
    r = subprocess.run(argv, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    print(r.stdout[-2500:])
    if r.returncode:
        print(r.stderr[-2500:])
    return r


def main():
    py = sys.executable
    tol = PREP["tolerances"]
    rec = {"prep_t": PREP["t"], "targets": []}
    r = _run([py, "tools/play.py", str(HERE / "a1_reach.py"), "--keep-open", "--label", "a1-reach"], 900)
    rec["reach_rc"] = r.returncode
    try:
        if r.returncode != 0:
            print("the world was not reached; no teleports sent")
            return
        for k, t in enumerate(PREP["targets"]):
            p = t["predict"]
            r = _run([py, "tools/world_teleport.py", f"{p['x']:.2f}", f"{p['z']:.2f}", "--shot", f"a1-{k}"], 300)
            back = json.loads(r.stdout.strip().splitlines()[-1])
            row = {"name": t["name"], "pick_dist": t["pick_dist"], "sent": (round(p["x"], 2), round(p["z"], 2)),
                   "stand_y": p["stand_y"], "back": back}
            if back["ok"]:
                row["dxz"] = math.dist((back["world_x"], back["world_z"]), row["sent"])
                row["dy"] = None if back["world_y"] is None else back["world_y"] - p["stand_y"]
            row["P1"] = t["pick_dist"] <= tol["pick"]
            row["P2"] = back["ok"] and row["dxz"] <= tol["xz"]
            row["P3"] = back["ok"] and row["dy"] is not None and abs(row["dy"]) <= tol["y"]
            rec["targets"].append(row)
    finally:
        rq = _run([py, "tools/play.py", str(HERE / "a1_quit.py"), "--attach", "--label", "a1-quit"], 300)
        rec["quit_rc"] = rq.returncode
        OUT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for row in rec["targets"]:
        b = row["back"]
        print(f"{row['name']:20s} P1 {row['P1']} (pick {row['pick_dist']:.3f}u)  "
              f"P2 {row['P2']} (dxz {row.get('dxz', float('nan')):.3f})  "
              f"P3 {row['P3']} (y {b.get('world_y')} vs {row['stand_y']:.3f}, dy {row.get('dy')})")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
