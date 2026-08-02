"""THE V-CORNER FLOW PROBE — decode the residual CATCH + run-freeze (playtest 3).

Against the LIVE post-sea-cut bytes: (A) the wedge fan decoded per heading (reject
class miss-vs-mask + the answering surface, cold and approach-warmed); (B) coast-HUG
walkers — heading biased INTO the wall like a player hugging it — driven around the
corner and along a healthy control stretch, measuring THROUGH-FLOW (net progress),
stall ticks, and micro-jitter; (C) the walkable-strip pinch width along the corner
path. READ-ONLY.
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402
from probe_vcorner_trap import fan_test, reason_key         # noqa: E402

WEDGE = (376.86, -509.60)
HEADINGS = [math.radians(11.25 * k) for k in range(32)]


def wedge_decode(world):
    print("=== A) THE WEDGE FAN, decoded per heading ===")
    for (tag, ring) in (("cold", None),):
        ft = fan_test(world, WEDGE[0], WEDGE[1], ring=ring)
        if ft is None:
            print(f"   [{tag}] not standable?!")
            continue
        print(f"   [{tag}] standing y={ft['y']} n_ok={ft['n_ok']}/32; failing headings:")
        for k, d in enumerate(ft["det"]):
            if d.get("ok"):
                continue
            extra = ""
            if d["reason"].startswith("miss") and d.get("raw"):
                extra = "  raw:" + "; ".join(f"y={r[0]} topo={r[1]} {r[2]}#{r[3]} ny={r[5]}"
                                             for r in d["raw"][:2])
            if d["reason"] == "mask":
                s = d["surf"]
                extra = f"  {s['part']}#{s['ti']} topo={s['topo']} y={s['y']} ({s['src']})"
            print(f"      h{k:2d} ({11.25 * k:6.2f}deg) -> ({d['nx']},{d['nz']}): "
                  f"{d['reason']}{extra} [{d.get('stage', 'p1')}]")
    # the south-approach warmed ring, exactly the playtest approach
    st = dict(x=WEDGE[0], y=3.2, z=WEDGE[1] + 8.0, heading=math.pi)
    walk = [s for s in W.all_sheets(world, st["x"], st["z"]) if s[1] in W.WALK_OK]
    st["y"] = walk[0][0]
    ring = W.Ring()
    for k in range(200):
        if W.walk_step(world, ring, st) == "stall":
            break
    ft = fan_test(world, st["x"], st["z"], ring=ring, y=st["y"])
    per = Counter(reason_key(d) for d in ft["det"] if not d.get("ok"))
    print(f"   [warmed, stalled at ({st['x']:.2f},{st['z']:.2f})] n_ok={ft['n_ok']}/32; reasons:")
    for k, n in per.most_common(8):
        print(f"      {n:2d}/32 {k}")


def hug_drive(world, spawns, along, inward, pass_line, title, steps=400):
    """Coast-hug walkers: heading = along-coast rotated INTO the wall by `inward`.
    pass_line(x, z) -> True once the walker is past the corner/stretch."""
    print(f"\n=== B) COAST HUG [{title}] along={math.degrees(along):.0f}deg "
          f"inward bias {math.degrees(inward):.0f}deg ===")
    for (sx, sz) in spawns:
        walk = [s for s in W.all_sheets(world, sx, sz) if s[1] in W.WALK_OK]
        if len(walk) != 1:
            print(f"   spawn ({sx},{sz}): not clean lawn, skipped")
            continue
        st = dict(x=sx, y=walk[0][0], z=sz, heading=along + inward)
        ring = W.Ring()
        stalls = 0
        moves = 0
        deflects = 0
        passed = None
        first_stall = None
        for k in range(steps):
            ev = W.walk_step(world, ring, st)
            if ev == "stall":
                stalls += 1
                if first_stall is None:
                    first_stall = (round(st["x"], 2), round(st["z"], 2), k)
            elif ev == "move":
                moves += 1
            else:
                deflects += 1
            if pass_line(st["x"], st["z"]):
                passed = k
                break
        out = (f"PASSED at step {passed}" if passed is not None
               else f"CAUGHT at ({st['x']:.2f},{st['z']:.2f})")
        print(f"   spawn ({sx:6.1f},{sz:7.1f}): {out}; moves={moves} deflects={deflects} "
              f"stalls={stalls} first_stall={first_stall}")


def pinch_map(world):
    print("\n=== C) THE PINCH: standable-strip width across the corner path ===")
    # stations along the wall from NNW of the corner to ESE past it; width measured
    # perpendicular-ish (NE-SW) at 0.1u
    stations = [(375.6 + 0.25 * k, -507.6 - 0.4 * k) for k in range(14)]
    for (cx, cz) in stations:
        n = 0
        for t in range(-30, 31):
            x, z = cx + 0.1 * t * 0.707, cz + 0.1 * t * 0.707   # NE-SW cut
            if any(s[1] in W.WALK_OK for s in W.all_sheets(world, x, z)):
                n += 1
        print(f"   station ({cx:6.2f},{cz:8.2f}): strip ~{n * 0.1:.1f}u")


def main():
    print("loading LIVE (post-sea-cut) world ...")
    world = W.load_world()
    wedge_decode(world)
    # the corner: walk the west shore southbound, hug into the wall (west/SW), must
    # round the corner and continue southeast past z=-512
    hug_drive(world, [(377.5, -503.0), (377.2, -505.5), (377.0, -507.0)],
              along=math.pi, inward=math.radians(22.5),
              pass_line=lambda x, z: z < -512.5, title="THE CORNER, south + hug west")
    hug_drive(world, [(377.5, -503.0), (377.2, -505.5)],
              along=math.pi, inward=math.radians(45.0),
              pass_line=lambda x, z: z < -512.5, title="THE CORNER, south + hard hug")
    # the reverse direction: from the south shore heading north around the corner
    hug_drive(world, [(380.5, -513.5), (379.5, -512.5)],
              along=0.0, inward=math.radians(-22.5),
              pass_line=lambda x, z: z > -506.0, title="THE CORNER, north + hug west")
    # CONTROL: the east shore beside the pristine cliff (the wall runs N-S at x~448),
    # southbound hugging east; healthy coast per the owner
    hug_drive(world, [(446.5, -496.0), (446.5, -500.0)],
              along=math.pi, inward=math.radians(-22.5),
              pass_line=lambda x, z: z < -516.0, title="CONTROL east shore, south + hug east")
    pinch_map(world)


if __name__ == "__main__":
    main()
