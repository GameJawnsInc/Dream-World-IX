"""Where did the shingle cut FIRE vs where did it MISS? Live-vs-pristine sheet diff.
DROPPED = pristine lawn absent live, carried surface above (the cut fired).
LAWN-UNDER = pristine lawn still present live, carried surface above (the cut missed).
The radial-guard hypothesis (full_skirt.py:871-873 skips tris with centroid beyond
rim_r_max+8) predicts a single radius R* from CENTER separating the two classes.
"""
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402

CENTER = (416.0, -512.0)


def main():
    live = W.load_world()
    tsrc = {}
    for (bx, by) in W.CELLS:
        p = W.PRISTINE_BK / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if p.is_file():
            tsrc[(bx, by)] = p
    pristine = W.load_world(terrain_src=tsrc)

    x0, x1, z0, z1 = W.REGION
    dropped, lawn_under = [], []
    i = 0
    x = x0
    while x <= x1:
        z = z0
        while z <= z1:
            psh = [s for s in W.all_sheets(pristine, x, z) if s[1] in W.WALK_OK]
            plawn = [s for s in psh if 3.0 <= s[0] <= 3.4]
            if plawn:
                py = plawn[0][0]
                lsh = [s for s in W.all_sheets(live, x, z) if s[1] in W.WALK_OK]
                has_lawn = any(abs(s[0] - py) < 0.05 for s in lsh)
                carried_above = any(s[0] > py + 0.25 for s in lsh)
                if carried_above:
                    r = math.hypot(x - CENTER[0], z - CENTER[1])
                    th = math.degrees(math.atan2(z - CENTER[1], x - CENTER[0]))
                    (lawn_under if has_lawn else dropped).append((r, th, x, z))
            z += W.GRID
        x += W.GRID
        i += 1

    for name, pts in (("DROPPED (cut fired)", dropped), ("LAWN-UNDER (cut missed)", lawn_under)):
        if not pts:
            print(f"{name}: none")
            continue
        rs = sorted(p[0] for p in pts)
        print(f"{name}: {len(pts)} pts, radius min {rs[0]:.1f} p25 {rs[len(rs)//4]:.1f} "
              f"med {rs[len(rs)//2]:.1f} p75 {rs[3*len(rs)//4]:.1f} max {rs[-1]:.1f}")

    print("\nper 22.5deg angle bin: [max DROPPED r | min LAWN-UNDER r]  (guard predicts a shared cut radius)")
    bins_d, bins_l = defaultdict(list), defaultdict(list)
    for (r, th, _, _) in dropped:
        bins_d[int((th + 180) // 22.5)].append(r)
    for (r, th, _, _) in lawn_under:
        bins_l[int((th + 180) // 22.5)].append(r)
    for b in range(16):
        d = max(bins_d[b]) if bins_d[b] else None
        l = min(bins_l[b]) if bins_l[b] else None
        ang = -180 + b * 22.5
        print(f"   {ang:+7.1f}..{ang+22.5:+7.1f}: dropped_max="
              f"{d and round(d,1)!s:>6} lawn_under_min={l and round(l,1)!s:>6} n_lu={len(bins_l[b])}")


if __name__ == "__main__":
    main()
