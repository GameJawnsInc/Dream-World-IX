"""THE RAISED STEP: what comp26's and comp10's rims step onto at home (NOTES.md section 2, "a vertical step in the rim").

Both refuse 0/6 on a flat bench of their own ground: a rim edge of ~zero plan length rises 1.95u, so the zip can only
close it with a vertical tri (zipNyMin 0.00). comp9's inlet was the same class (the rim closing on home ground the
carry does not take) and the alcove floor carry fixed it. Before designing the carry this reads, per donor:
  - every STEP edge of the bare blob's rim (plan length < STEP_PLAN, rise > STEP_RISE);
  - the non-rock tris round each step's TOP vertex: topograph, height, event bits;
  - the RAISED GROUND: from those tris, a flood through non-rock tris whose lowest vertex stands above the step's
    foot + FLOOD_ABOVE (the shelf the rock meets one step up), with its size, plan box, topographs and height range,
    and whether it reaches the donor blocks' edge (a shelf that runs off the read window is not a carriable unit);
  - the plan box of each raised shelf in the FIRST donor block's local frame, the alcove spec's frame.
Writes out/step_anatomy.json.  RUN:  py studies/terrain-malleability/mountaindonors/step_anatomy.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sweep as S  # noqa: E402  (the worktree-pinned kit import)

DONORS = {"comp26": [(14, 3), (15, 3)], "comp10": [(14, 14), (15, 14)]}
STEP_PLAN = 0.1           # a rim edge this short in plan is a vertical step
STEP_RISE = 1.0
FLOOD_ABOVE = 0.5         # a raised-shelf tri's lowest vertex stands this far above the step's foot


def anatomy(name, blocks):
    IN, _, _ = S._kit()
    from ff9mapkit.world import extract as X
    rock = frozenset(IN.MOUNTAIN_ROCK_TOPOS)
    lines = []
    B = IN._mountain_blob(blocks, rock_topos=rock, alcove_box=None, log=lines.append)
    dV, dtri, dtopo, d_edge, dT = B["dV"], B["dtri"], B["dtopo"], B["d_edge"], B["dT"]
    kk3 = IN.kk3
    blob = B["blob"]
    rim = B["rim"]
    n = len(rim)
    doff = np.array([64.0 * blocks[0][0], 0.0, -64.0 * blocks[0][1]])
    xs = [64.0 * bx for bx, _ in blocks]
    win = (min(xs), max(xs) + 64.0, -64.0 * (max(by for _, by in blocks) + 1), -64.0 * min(by for _, by in blocks))
    by_key = {}
    for t, idx in enumerate(dtri):
        for i in idx:
            by_key.setdefault(kk3(dV[i]), set()).add(t)
    steps = []
    for k in range(n):
        a, b = rim[k], rim[(k + 1) % n]
        plan = math.hypot(a[0] - b[0], a[2] - b[2])
        rise = abs(a[1] - b[1])
        if plan < STEP_PLAN and rise > STEP_RISE:
            top, foot = (a, b) if a[1] > b[1] else (b, a)
            round_top = sorted(by_key.get(kk3(top), ()), key=lambda t: dtopo[t])
            ring = [{"tri": t, "topo": dtopo[t], "in_blob": t in blob,
                     "y": [round(float(dV[i][1]), 2) for i in dtri[t]],
                     "event": X.decode_id(int(round(dT[dtri[t][0]][0])))["event"]} for t in round_top]
            # the raised shelf: non-rock, non-blob tris touching the top, flooded through tris standing above the foot
            seeds = [t for t in round_top if t not in blob and dtopo[t] not in rock]
            shelf, st = set(), list(seeds)
            while st:
                t = st.pop()
                if t in shelf or t in blob or dtopo[t] in rock:
                    continue
                if min(dV[i][1] for i in dtri[t]) <= foot[1] + FLOOD_ABOVE:
                    continue
                shelf.add(t)
                for x, y in ((0, 1), (1, 2), (2, 0)):
                    for t2 in d_edge[tuple(sorted((kk3(dV[dtri[t][x]]), kk3(dV[dtri[t][y]]))))]:
                        if t2 not in shelf:
                            st.append(t2)
            rec = {"rim_k": k, "top": [round(float(v), 3) for v in top], "foot": [round(float(v), 3) for v in foot],
                   "plan": round(plan, 4), "rise": round(rise, 3), "round_top": ring, "shelf_tris": len(shelf)}
            if shelf:
                P = np.array([dV[i] for t in shelf for i in dtri[t]])
                L = P - doff
                rec.update(shelf_topos=dict(Counter(dtopo[t] for t in shelf)),
                           shelf_y=[round(float(P[:, 1].min()), 2), round(float(P[:, 1].max()), 2)],
                           shelf_world_box=[round(float(P[:, 0].min()), 2), round(float(P[:, 0].max()), 2),
                                            round(float(P[:, 2].min()), 2), round(float(P[:, 2].max()), 2)],
                           shelf_local_box=[round(float(L[:, 0].min()), 2), round(float(L[:, 0].max()), 2),
                                            round(float(L[:, 2].min()), 2), round(float(L[:, 2].max()), 2)],
                           shelf_touches_window_edge=bool(
                               (P[:, 0].min() <= win[0] + 0.01) or (P[:, 0].max() >= win[1] - 0.01)
                               or (P[:, 2].min() <= win[2] + 0.01) or (P[:, 2].max() >= win[3] - 0.01)),
                           shelf_events=dict(Counter(X.decode_id(int(round(dT[dtri[t][0]][0])))["event"]
                                                     for t in shelf)))
            steps.append(rec)
    feet = Counter()
    for k in range(n):
        a, b = rim[k], rim[(k + 1) % n]
        for t in d_edge.get(tuple(sorted((kk3(a), kk3(b)))), ()):
            if t not in blob:
                feet[dtopo[t]] += 1
    return {"blocks": blocks, "blob_tris": len(blob), "rim_pts": n,
            "rim_y": [round(min(p[1] for p in rim), 2), round(max(p[1] for p in rim), 2)],
            "feet_topos": dict(feet), "steps": steps, "log": [str(x) for x in lines]}


def main():
    out = {name: anatomy(name, blocks) for name, blocks in DONORS.items()}
    for name, r in out.items():
        print(f"== {name} {r['blocks']}: blob {r['blob_tris']} tris, rim {r['rim_pts']} pts y {r['rim_y']}, "
              f"feet {r['feet_topos']}")
        for s in r["steps"]:
            print(f"   step at rim {s['rim_k']}: top {s['top']} foot y {s['foot'][1]} rise {s['rise']} plan "
                  f"{s['plan']}; round the top: {[(x['topo'], x['in_blob'], x['y']) for x in s['round_top']]}")
            if s["shelf_tris"]:
                print(f"      SHELF {s['shelf_tris']} tris topos {s['shelf_topos']} y {s['shelf_y']} world box "
                      f"{s['shelf_world_box']} local box {s['shelf_local_box']} reaches window edge "
                      f"{s['shelf_touches_window_edge']} events {s['shelf_events']}")
            else:
                print("      no shelf: nothing non-rock above the foot touches the step's top")
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "step_anatomy.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
