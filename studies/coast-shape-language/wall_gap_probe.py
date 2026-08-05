"""Capability 3 pre-design measurement: what ARE the wall gaps the CliffWindow decode
refuses? Dumps the byte-level tri structure at each refused gap -- roles, extra verts,
positions, uvs -- for the two refusal classes ("1 tris, 0 refined" and "2 tris,
1 refined"). Read-only. Run from the repo root.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import coastscan as CS                  # noqa: E402
from ff9mapkit.world import coastmorph as CM                 # noqa: E402
from ff9mapkit.world.extract import decode_id                # noqa: E402

#: (block, L, the refused gap index from the sweep)
SPECIMENS = [
    ((17, 1), 101.1, 10),      # crescent, "1 tris, 0 refined"
    ((14, 2), 60.0, 13),       # crescent, "1 tris, 0 refined"
    ((15, 2), 42.0, 0),        # crescent, "1 tris, 0 refined"
    ((14, 1), 24.5, 5),        # crescent, "2 tris, 1 refined"
    ((9, 18), 45.7, 0),        # chain,    "2 tris, 1 refined"
    ((9, 7), 66.0, 10),        # comma,    "2 tris, 1 refined"
]


class OpenWindow(CM.CliffWindow):
    """CliffWindow with the gap refusal DISARMED -- failed gaps recorded, not raised."""

    def __init__(self, *a, **kw):
        self.failed_gaps = []
        try:
            super().__init__(*a, **kw)
        except ValueError as e:
            print(f"   (window still refused: {str(e)[:90]})")
            raise


def probe(blk, want_l, gap):
    wins = [w for w in CS.scan_block(*blk, disc=1) if w["kind"] == "cliff"
            and abs(w["L"] - want_l) < 0.5]
    if not wins:
        print(f"== {blk} L~{want_l}: window not found")
        return
    w = wins[0]
    # rebuild just enough: run the real decode but catch at the failing gap by
    # monkey-walking -- easiest is to read the raw pieces the way __init__ does,
    # via a stripped-down copy of its edge logic
    import math
    from collections import defaultdict
    TR = CM.TR
    terr = TR.world_tris(*blk, "terrain", disc=1)
    topo = lambda t3: decode_id(int(round(t3[0][3][0])))["topograph"]
    cliff = [t for t in terr if topo(t) == 58]
    cnt = defaultdict(int)
    for t3 in cliff:
        ps = [v[0] for v in t3]
        for i in range(3):
            cnt[frozenset((CM._pk(ps[i]), CM._pk(ps[(i + 1) % 3])))] += 1
    land_edges = set()
    for t3 in terr:
        if topo(t3) == 58:
            continue
        ps = [v[0] for v in t3]
        for i in range(3):
            land_edges.add(frozenset((CM._pk(ps[i]), CM._pk(ps[(i + 1) % 3]))))
    x0, x1, z0, z1 = CM.CliffWindow.region_frame(blk, (1, 1))

    def on_frame(a, b, eps=0.02):
        for ax, lo, hi in ((0, x0, x1), (2, z0, z1)):
            for plane in (lo, hi):
                if abs(a[ax] - plane) < eps and abs(b[ax] - plane) < eps:
                    return True
        return False
    base_edges = [e for e, c in cnt.items()
                  if c == 1 and e not in land_edges and not on_frame(*tuple(e))
                  and max(a[1] for a in e) < CM.BASE_Y_MAX]
    adj = defaultdict(list)
    for e in base_edges:
        a, b = tuple(e)
        adj[a].append(b)
        adj[b].append(a)
    pos_of = {}
    for t3 in cliff:
        for v in t3:
            pos_of.setdefault(CM._pk(v[0]), v[0])

    def snap(p):
        best, bd = None, 0.6
        for k in adj:
            d = math.hypot(pos_of[k][0] - p[0], pos_of[k][2] - p[1])
            if d < bd:
                best, bd = k, d
        return best
    ks, ke = snap(w["start"]), snap(w["end"])
    chain = None
    for first in adj[ks]:
        trial, prev = [ks, first], ks
        while trial[-1] != ke and len(trial) <= 4096:
            nxts = [n for n in adj[trial[-1]] if n != prev]
            if not nxts:
                break
            prev = trial[-1]
            trial.append(nxts[0])
        if trial[-1] == ke:
            chain = trial
            break
    if chain is None:
        print(f"== {blk} L~{want_l}: no chain")
        return
    base = [pos_of[k] for k in chain]
    elevated = {}
    for e, c in cnt.items():
        a, b = tuple(e)
        for p, q in ((a, b), (b, a)):
            if p in set(chain) and q not in adj and pos_of.get(q, (0, 99, 0))[1] > CM.BASE_Y_MAX:
                elevated.setdefault(p, []).append(q)
    crease = []
    for k, bp in zip(chain, base):
        cands = elevated.get(k, [])
        if not cands:
            crease.append(None)
            continue
        crease.append(pos_of[min(
            cands, key=lambda q: (pos_of[q][0] - bp[0]) ** 2 + (pos_of[q][2] - bp[2]) ** 2)])
    i = gap
    bl, br = base[i], base[i + 1]
    cl, cr = crease[i], crease[i + 1]
    print(f"== {blk} L={w['L']:.1f} gap {gap}")
    print(f"   bl {tuple(round(c, 2) for c in bl)}  cl "
          f"{tuple(round(c, 2) for c in cl) if cl else None}")
    print(f"   br {tuple(round(c, 2) for c in br)}  cr "
          f"{tuple(round(c, 2) for c in cr) if cr else None}")
    if cl is not None and cr is not None:
        same = CM._pk(cl) == CM._pk(cr)
        print(f"   crease-shared: {same}  gap-width {math.dist(bl, br):.2f}u  "
              f"crease-dist {math.dist(cl, cr):.2f}u")
    roles = {CM._pk(p) for p in (bl, cl, br, cr) if p is not None}
    touching = [t3 for t3 in cliff
                if CM._key_set(t3) & {CM._pk(bl), CM._pk(br)}]
    for t3 in touching:
        ks_ = CM._key_set(t3)
        extra = [k for k in ks_ if k not in roles]
        tag = "inside-roles" if not extra else f"extra {[tuple(round(c,2) for c in k) for k in extra]}"
        ys = sorted(round(v[0][1], 2) for v in t3)
        print(f"     tri ys={ys} {tag}")


for blk, want_l, gap in SPECIMENS:
    probe(blk, want_l, gap)
