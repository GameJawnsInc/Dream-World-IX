"""Where would THE FRINGE-SEAM UNIFY fire? -- the R5c rule's own predicate, read-only (R5b's tooth).

R5b snapped Uaho's SE rim vertex onto the lawn line. Its two contact tris still meet at a TOP vertex (V0) where the
donor's two uv charts disagree: v 10.062 (chart A, 4 tris) vs 9.375 (chart B, 5 tris), a 0.688-tile seam. The
fringe band (the blades, at the tile's bottom) therefore ends at a different height either side of their shared
edge: the tooth.

The candidate rule, evaluated here exactly as the kit would run it:
  - SCOPE: every corner of a CONTACT tri -- rock in the r10 c6-9 fringe tile with an edge on grass;
  - SEAM: at that position the fringe-tile corners' v spread > 0.25 tile (stock_fringe_continuity's cut: 6 such
    positions among 2,536 shared fringe positions on stock disc 1);
  - CANDIDATES: the v values already present there (no invented number);
  - VALID: moving every rock corner at the position to the candidate inverts no rock tri there (no tri whose v
    would rise with height where it fell before, or the reverse) -- the texture must not flip;
  - PICK: the valid candidate that moves the fewest corners; none valid = left and named.
Reports, per source: positions selected, the pick, the corners it moves, and the fringe density of every touched
tri before/after (tile-heights per unit; stock contact tris p50 0.25, p90 0.34, p97 0.43).

    py -X utf8 studies/overworld-topography/west-seam-continent/fringe_seam_screen.py [--stock]
"""
import math
import struct
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import uaho_contact_tiles as U                          # noqa: E402

SEAM_TOL = 0.25
SP = Path(r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\4defe9bc-0f55-44e7-952d-bd74e20446f5"
          r"\scratchpad")
BENCH = SP / "bench-uaho-r5c" / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"


def vt(uv):
    return (uv[1] - U.PV) / U.TV


def monotone_breaks(pts):
    """pts: [(y, v)] of one tri -> the corner pairs whose v order disagrees with the height order."""
    bad = set()
    for i in range(3):
        for j in range(3):
            if pts[i][0] < pts[j][0] - 0.05 and pts[i][1] < pts[j][1] - 1e-3:
                bad.add((i, j))
    return bad


def screen(mesh, label, origin=(0, 0)):
    verts, uvs, topos, tris = mesh
    bx, by = origin
    key = lambda i: tuple(round(x, 3) for x in verts[i])            # noqa: E731
    contact = {rt for rt, _vij, _gt in U.contact_edges(mesh) if U.is_fringe(U.tile([uvs[i] for i in tris[rt]]))}
    rock_at = defaultdict(list)                                     # position -> [(tri, corner)]
    for t, tr in enumerate(tris):
        if topos[tr[0]] == U.ROCK:
            for c, i in enumerate(tr):
                rock_at[key(i)].append((t, c))
    picked = []
    for pos in sorted({key(i) for t in contact for i in tris[t]}):
        fr = [(t, c) for t, c in rock_at[pos] if U.is_fringe(U.tile([uvs[i] for i in tris[t]]))]
        vs = [vt(uvs[tris[t][c]]) for t, c in fr]
        if len(fr) < 2 or max(vs) - min(vs) <= SEAM_TOL:
            continue
        cands = sorted({round(v, 4) for v in (vt(uvs[tris[t][c]]) for t, c in rock_at[pos])})
        best, rows = None, []
        for cand in cands:
            newly = 0
            moved = sum(1 for t, c in rock_at[pos] if abs(vt(uvs[tris[t][c]]) - cand) > 1e-4)
            for t, c in rock_at[pos]:
                before = [(verts[i][1], vt(uvs[i])) for i in tris[t]]
                after = [(y, cand) if k == c else (y, v) for k, (y, v) in enumerate(before)]
                if monotone_breaks(after) - monotone_breaks(before):
                    newly += 1
            rows.append((cand, moved, newly))
            if newly == 0 and (best is None or moved < best[1]):
                best = (cand, moved)
        w = (bx * 64 + pos[0], pos[1], pos[2] - by * 64)
        print(f"  {label} SEAM at ({w[0]:.2f},{w[2]:.2f}, y{w[1]:.2f}): fringe v {sorted(set(round(v, 3) for v in vs))} "
              f"spread {max(vs) - min(vs):.3f}; rock corners {len(rock_at[pos])}; candidates (v, moves, tris it would "
              f"invert) {rows} -> {'PICK v %.3f, %d corners' % best if best else 'NONE VALID: left'}")
        if best:
            for t, c in rock_at[pos]:
                tr = tris[t]
                ys = [verts[i][1] for i in tr]
                v0 = [vt(uvs[i]) for i in tr]
                v1 = [best[0] if k == c else v for k, v in enumerate(v0)]
                if abs(v0[c] - best[0]) > 1e-3:
                    d = lambda v: (max(v) - min(v)) / max(1e-6, max(ys) - min(ys))   # noqa: E731
                    print(f"      t{t} r{U.tile([uvs[i] for i in tr])[0]}: v {round(v0[c], 3)} -> {best[0]:.3f}; "
                          f"density {d(v0):.2f} -> {d(v1):.2f}")
        picked.append((w, best))
    return picked


def main():
    if "--stock" in sys.argv:
        n = 0
        for bx in range(24):
            for by in range(20):
                try:
                    mesh = U.read_stock(bx, by)
                except Exception:
                    continue
                n += len(screen(mesh, f"stock ({bx},{by})", (bx, by)))
        print(f"STOCK disc 1: {n} positions the predicate selects")
    U.LIVE = BENCH
    print("BENCH (R5b, Uaho snapped):")
    for b in ((22, 7), (22, 6), (23, 7), (23, 6)):
        m = U.read_live(*b)
        if m:
            screen(m, f"bench {b}", b)
    U.LIVE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap-world\FF9_Data"
                  r"\WorldMap\Disc1\0_1")
    print("LIVE comp20 blocks:")
    for b in ((22, 5), (22, 6), (23, 5), (23, 6)):
        m = U.read_live(*b)
        if m:
            screen(m, f"live {b}", b)


if __name__ == "__main__":
    main()
