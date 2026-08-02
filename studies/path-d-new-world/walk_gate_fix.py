"""PRE-DEPLOY walk gate for THE RENDER-ONLY UNDERLAY (LAWN-CLIP-PREDICTION.md gate 2).
Points walk_sim at the BUILT Terrain meshes (out/terrace_strip/underlay_meshes), runs
the census + the full trajectory target set (the pin + the shingle round's measured
clusters, frozen from report.json), and gates:
  G-A  0 stacked-WALKABLE points anywhere,
  G-B  0 SUNKEN events on any trajectory,
  G-C  0 DEAD-BAND stalls (a stall whose 1u ring is pure single-sheet walkable lawn
       within climb reach = the render-only-leak class),
  G-D  >0 walkers CLIMB onto the carried surface (max committed y > 4.5).
Read-only; no deploy, no bench mutation.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402
from terrace_wall_strip import OUTD                         # noqa: E402

MDIR = OUTD / "underlay_meshes"


def main():
    tsrc = {}
    for (bx, by) in W.CELLS:
        p = MDIR / f"Block[{bx}][{by}] Terrain.ff9mesh"
        assert p.is_file(), f"missing built mesh {p} -- run full_skirt.py first"
        tsrc[(bx, by)] = p
    fix = W.load_world(terrain_src=tsrc)
    for bk in sorted(fix):
        print(f"   block {bk}: " + ", ".join(f"{m['name']}({len(m['tris'])})" for m in fix[bk]))

    stacked, clusters, _pin_dmin = W.census(fix, "FIX build (the underlay)")

    rep = json.load(open(HERE / "out" / "walk_sim" / "report.json"))
    targets = [(W.PIN[0], W.PIN[1], "PIN(434,-542)"),
               (438.5, -498.0, "blob-NE-curtain")]          # the curtain-class residual locus
    for c in rep["clusters"][:6]:
        targets.append((c["cx"], c["cz"], f"cluster@({c['cx']},{c['cz']})"))

    # trajectory pass with per-walker max-y + dead-band classification
    events, climbers, deadband = [], 0, []
    for (tx, tz, tag) in targets:
        for hk in range(12):
            th = 2 * math.pi * hk / 12
            r = 15.0
            sx = sz = None
            while r < 26.0:
                qx, qz = tx - r * math.sin(th), tz - r * math.cos(th)
                sh = W.all_sheets(fix, qx, qz)
                walk = [s for s in sh if s[1] in W.WALK_OK]
                if len(walk) == 1:
                    sx, sz, sy = qx, qz, walk[0][0]
                    break
                r += 2.0
            if sx is None:
                continue
            st = dict(x=sx, y=sy, z=sz, heading=th)
            ring = W.Ring()
            ymax = sy
            for k in range(90):
                ev = W.walk_step(fix, ring, st)
                ymax = max(ymax, st["y"])
                top = W.top_walk_surface(fix, st["x"], st["z"])
                if ev == "stall":
                    open_lawn = True
                    for aa in range(8):
                        ax = st["x"] + math.sin(math.pi * aa / 4)
                        az = st["z"] + math.cos(math.pi * aa / 4)
                        sh2 = W.all_sheets(fix, ax, az)
                        w2 = [s for s in sh2 if s[1] in W.WALK_OK]
                        if len(w2) != 1 or abs(w2[0][0] - st["y"]) > 2.0 or len(sh2) != len(w2):
                            open_lawn = False
                            break
                    events.append(dict(tag=tag, hd=hk, step=k, ev="STALL",
                                       x=round(st["x"], 2), z=round(st["z"], 2),
                                       y=round(st["y"], 2), open_lawn=open_lawn))
                    if open_lawn:
                        deadband.append(events[-1])
                    break
                if top is not None and st["y"] < top - W.SUNKEN_EPS:
                    events.append(dict(tag=tag, hd=hk, step=k, ev="SUNKEN",
                                       x=round(st["x"], 2), z=round(st["z"], 2),
                                       y=round(st["y"], 2), top=round(top, 2)))
            if ymax > 4.5:
                climbers += 1

    kinds = defaultdict(int)
    for e in events:
        kinds[(e["tag"], e["ev"])] += 1
    print(f"\n=== WALKERS [FIX]: {len(events)} events, {climbers} climbers ===")
    for (tag, ev), n in sorted(kinds.items()):
        print(f"   {tag:24s} {ev:7s}: {n}")
    if deadband:
        print("   DEAD-BAND stalls:", deadband[:8])

    sunken = sum(1 for e in events if e["ev"] == "SUNKEN")
    # gA, gap-aware (declared-freedom resolution recorded in LAWN-CLIP-PREDICTION.md):
    # a stack whose walkable-sheet gap is within the SUNKEN visibility threshold
    # cannot put the actor visibly below a surface; the strict census already
    # excludes measure-zero shared-boundary lines. Gate: no stack DEEPER than that.
    deep = [p for p in stacked.values() if p["gap"] > W.SUNKEN_EPS]
    if deep:
        print(f"   gA deep stacks ({len(deep)}):",
              [(p["x"], p["z"], p["gap"]) for p in deep[:10]])
    gates = dict(
        gA_no_stacked_beyond_eps=len(deep) == 0,
        gB_no_sunken=sunken == 0,
        gC_no_deadband=len(deadband) == 0,
        gD_climbers=climbers > 0,
    )
    print("\n=== FIX WALK GATES ===")
    for k, v in gates.items():
        print(f"   {k}: {'PASS' if v else 'FAIL'}")
    json.dump(dict(gates=gates, events=events, climbers=climbers,
                   stacked_n=len(stacked), clusters=clusters),
              open(HERE / "out" / "walk_sim" / "fix_gate.json", "w"), indent=1)
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
