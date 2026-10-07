"""CALIBRATION before any verdict (lane gap_inplace_stitch_composition).

C1  THE BERM LAW count -- memory project-ff9-overworld-coast-mosaic.md:146 "beach berms are topo-0 ONLY
    (664/702 map-wide L-chain welds)". The original census script was scratch, never committed
    (HANDOFF_BEACH_MINT_RUNG3.md 2a). Re-derive with the kit's own L-chain definition
    (coastmorph.beach_mint: L = sand-band verts welded to a NON-sand terrain tri and NOT welded to foam),
    under several counting units, and report which (if any) reproduces 664/702.
C2  The stock disc-1 border-gap count with the uncovered-stretch fix, reconciled row by row with
    disc4/out/weld_gap.json (D4-06: 17 gap>0 of 443; 37 open-but-gap-0, of which VERIFY says 26 uncovered and
    11 "covered T-junctions").
C3  Synthetic controls on REAL stock data:
    (a) the tear detector (pre/post distance of a stock weld pair > 0.05u) must flag a 0.06u move and pass
        a 0.01u move; the kit's mesh.weld_audit (near-miss census 0<d<0.05) is run on the SAME inputs to show
        what it can and cannot see;
    (b) the T-junction scan must flag a synthetic vertex inserted on a real border edge (and stock is 0);
    (c) the border-coverage instrument must report an uncovered stretch when one border tri is deleted.
Writes out/calibrate.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/calibrate.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
import stitch_census as C                              # noqa: E402
from ff9mapkit.world import mesh as KM                 # noqa: E402

SAND = {31, 32, 33}
res = {}


# ---------------------------------------------------------------- C1 the BERM LAW --------------------------
def berm(M, sand_topos, foam_parts=("beach1",), exclude_topos=frozenset(), scope="beach1", keep_foam=False):
    """scope 'beach1' = blocks carrying a Beach1 part; 'sand' = blocks whose Terrain carries a sand-topo tri.
    keep_foam=False is coastmorph.beach_mint's L (foam-welded end verts excluded)."""
    by_unit = Counter()
    if scope == "beach1":
        blocks = sorted({(x, y) for (x, y, p) in M if p in foam_parts})
    else:
        blocks = sorted({(x, y) for (x, y, p), m in M.items() if p == "terrain"
                         and any(S.topo(m.tri_idall(t)) in sand_topos for t in range(m.ntri))})
    rows = {}
    for (x, y) in blocks:
        ter = M.get((x, y, "terrain"))
        if ter is None:
            continue
        foam_k = set()
        for fp in foam_parts:
            if (x, y, fp) in M:
                foam_k |= {tuple(p) for p in M[(x, y, fp)].lv}
        sand_v, other_tris = set(), defaultdict(list)   # pos -> [topo of non-sand tris using it]
        for t in range(ter.ntri):
            tp = S.topo(ter.tri_idall(t))
            cs = [tuple(ter.lv[ter.fi[3 * t + k]]) for k in range(3)]
            if tp in sand_topos:
                sand_v |= set(cs)
            elif tp not in exclude_topos:
                for c in cs:
                    other_tris[c].append(tp)
        L = [p for p in sand_v if p in other_tris and (keep_foam or p not in foam_k)]
        r = Counter()
        for p in L:
            tps = other_tris[p]
            st = set(tps)
            r["L_verts"] += 1
            r["L_verts_all0"] += st == {0}
            r["L_verts_has0"] += 0 in st
            r["incid"] += len(tps)
            r["incid0"] += sum(1 for q in tps if q == 0)
        # edges between a sand tri and a non-sand tri (desert_beach_anatomy B's unit)
        eo = defaultdict(set)
        for t in range(ter.ntri):
            tp = S.topo(ter.tri_idall(t))
            cs = [tuple(ter.lv[ter.fi[3 * t + k]]) for k in range(3)]
            for i, j in ((0, 1), (1, 2), (2, 0)):
                eo[tuple(sorted((cs[i], cs[j])))].add(tp)
        for e, tps in eo.items():
            if tps & sand_topos:
                for q in tps - sand_topos - exclude_topos:
                    r["edges"] += 1
                    r["edges0"] += q == 0
        rows[f"{x},{y}"] = dict(r)
        by_unit.update(r)
    return dict(by_unit), rows


M1 = S.load_disc(1)
variants = {}
for name, st, ex, sc, kf in (
        ("beach1blocks_sand31_Lmint", {31}, frozenset(), "beach1", False),
        ("beach1blocks_sand31+32+33_Lmint", SAND, frozenset(), "beach1", False),
        ("beach1blocks_sand31_foamkept", {31}, frozenset(), "beach1", True),
        ("sandblocks_sand31_Lmint", {31}, frozenset(), "sand", False),
        ("sandblocks_sand31_foamkept", {31}, frozenset(), "sand", True),
        ("sandblocks_sand31+32+33_foamkept", SAND, frozenset(), "sand", True)):
    tot, rows = berm(M1, st, exclude_topos=ex, scope=sc, keep_foam=kf)
    variants[name] = tot
    print(f"C1 {name:26s} L verts {tot.get('L_verts', 0)} (all-topo0 {tot.get('L_verts_all0', 0)}, "
          f"has-topo0 {tot.get('L_verts_has0', 0)}); incidences {tot.get('incid0', 0)}/{tot.get('incid', 0)}; "
          f"sand|other edges {tot.get('edges0', 0)}/{tot.get('edges', 0)}")
hit = [(n, u) for n, t in variants.items() for u, (a, b) in
       {"verts_all0": ("L_verts_all0", "L_verts"), "verts_has0": ("L_verts_has0", "L_verts"),
        "incid": ("incid0", "incid"), "edges": ("edges0", "edges")}.items()
       if t.get(a) == 664 and t.get(b) == 702]
print("C1 reproduces 664/702 under:", hit or "NONE")
res["C1_berm"] = {"variants": variants, "reproduces_664_702": hit,
                  "beach1_blocks": len({(x, y) for (x, y, p) in M1 if p == "beach1"}),
                  "beach_any_blocks": len({(x, y) for (x, y, p) in M1 if p in ("beach1", "beach2")})}

# ---------------------------------------------------------------- C2 border reconciliation ----------------
wg = json.loads((S.LANE.parent / "disc4" / "out" / "weld_gap.json").read_text(encoding="utf-8"))
mine = {}
for disc in (1,):
    for (x, y) in sorted(S.land_blocks(M1)):
        for (nx, ny, side) in S.neighbours(x, y)[::2]:
            if (nx, ny, "terrain") not in M1:
                continue
            opp = {"E": "W", "S": "N"}[side]
            A = C.border_profile(M1, (x, y), side)
            Bp = C.border_profile(M1, (nx, ny), opp)
            mine[(x, y, side)] = (C.compare_border(A, Bp), A, Bp)
rec = Counter()
recon = []
for r in wg:
    ax, ay, sa = r["a"]
    m, A, Bp = mine[(ax, ay, sa)]
    theirs_gap = r["d1_gap"]
    cls = []
    if r["d1_exact"]:
        cls.append("exact")
    else:
        if theirs_gap > 0:
            cls.append("theirs_gap>0")
        else:
            cls.append("theirs_gap0")
        cls.append("mine_gap>0.01" if m["gap_mutual"] > 0.01 else ("mine_gap(0,0.01]" if m["gap_mutual"] > 0 else "mine_gap0"))
        cls.append("uncovered" if m["uncovered_len"] > 1e-6 else "covered")
        # the unmatched verts inside the mutual stretch: XZ-stack (same along, other y on the partner) vs other
        pa, pb = A["pts"], Bp["pts"]
        extra = [p for p in (pa ^ pb)]
        stack_like = [p for p in extra if any(abs(q[0] - p[0]) < 1e-6 and q != p for q in (pa | pb))]
        cls.append(f"extra{len(extra)}_stack{len(stack_like)}")
    rec[" / ".join(cls[:4])] += 1
    recon.append({"a": r["a"], "b": r["b"], "theirs": {"exact": r["d1_exact"], "gap": theirs_gap,
                  "uncovered": r["d1_uncovered"]}, "mine": {k: m[k] for k in ("exact", "gap_mutual", "uncovered_len",
                                                                                 "unmatched_A", "unmatched_B")},
                  "class": cls})
print(f"C2 rows in disc4 weld_gap.json: {len(wg)}; my border rows on disc 1 (all torus-adjacent land pairs): {len(mine)}")
for k, v in sorted(rec.items()):
    print(f"   {k:70s} {v}")
res["C2_border_reconcile"] = {"classes": dict(rec), "rows": recon, "n_theirs": len(wg), "n_mine": len(mine)}


# ---------------------------------------------------------------- C3 synthetic controls ---------------------
def stock_weld_pairs(Mx, blk):
    """(owner_a, ia, owner_b, ib) for every exact cross-part coincidence inside one block (unique per pos pair)."""
    pos = defaultdict(list)
    for k, m in Mx.items():
        if (k[0], k[1]) != blk:
            continue
        for i, p in enumerate(m.lv):
            pos[p].append((k, i))
    out = []
    for p, insts in pos.items():
        parts = {k for k, _ in insts}
        if len(parts) >= 2:
            out.append(insts)
    return out


def tear_detect(Mpre, Mpost, blk, tol=S.TOL):
    """pre/post: for every stock weld position cluster, the max distance between member instances after the
    edit; a cluster whose instances separate by > tol is TORN."""
    torn = []
    for insts in stock_weld_pairs(Mpre, blk):
        ps = [Mpost[k].lv[i] for k, i in insts]
        d = max(math.dist(a, b) for a in ps for b in ps)
        if d > tol:
            torn.append((sorted({k[2] for k, _ in insts}), round(d, 4)))
    return torn


class _BM:                                             # minimal BlockMesh stand-in for KM.weld_audit
    def __init__(self, verts):
        self.verts = verts


blk = (7, 17)                                          # the proven beach donor
sel = None
for insts in stock_weld_pairs(M1, blk):
    if {k[2] for k, _ in insts} == {"terrain", "beach1"}:
        sel = insts
        break
ctl = {}
for delta in (0.06, 0.01):
    Mpost = {k: S.Mesh(*[m.disc, m.x, m.y, m.part, m.name, list(m.lv), m.idall, m.fi]) for k, m in M1.items()
             if (k[0], k[1]) == blk}
    for k, i in sel:
        if k[2] == "beach1":
            v = Mpost[k].lv[i]
            Mpost[k].lv[i] = (v[0], v[1] + delta, v[2])
    pre = {k: m for k, m in M1.items() if (k[0], k[1]) == blk}
    t = tear_detect(pre, Mpost, blk)
    wa_pre = KM.weld_audit([_BM(m.lv) for m in pre.values()])
    wa_post = KM.weld_audit([_BM(m.lv) for m in Mpost.values()])
    ctl[str(delta)] = {"tear_detector_flags": len(t), "weld_audit_pairs_stock": len(wa_pre),
                       "weld_audit_pairs_after": len(wa_post)}
    print(f"C3a move one Beach1 partner of a (7,17) Terrain|Beach1 weld by +{delta}u (all its instances): "
          f"tear detector flags {len(t)} cluster(s); mesh.weld_audit pairs stock {len(wa_pre)} -> after {len(wa_post)}")
res["C3a_tear_vs_weld_audit"] = ctl
# (b) T-junction positive control (a probe vertex at the midpoint of a real (7,11)|(7,12) border edge)
m = M1[(7, 11, "terrain")]
E = S.mesh_edges(m)
e = [k for k in E if abs(k[0][2] + 768) < 1e-6 and abs(k[1][2] + 768) < 1e-6 and abs(k[0][0] - k[1][0]) > 1][0]
mid = tuple((e[0][i] + e[1][i]) / 2 for i in range(3))
loc = (mid[0] - 7 * 64, mid[1], mid[2] + 12 * 64)
probe = S.Mesh(1, 7, 12, "probe", "probe", [loc, (loc[0] + 1, loc[1], loc[2] - 1), (loc[0] - 1, loc[1], loc[2] - 1)],
               [0, 0, 0], [0, 1, 2])
M2 = dict(M1)
M2[(7, 12, "probe")] = probe
tj_pos = C.tjunctions(M2, blocks={(7, 11)})[0]
tj_stock = C.tjunctions(M1, blocks={(7, 11)})[0]
print(f"C3b T-junction scan: synthetic midpoint vertex -> {dict(tj_pos)}; stock (7,11) -> {dict(tj_stock)}")
res["C3b_tjunction"] = {"positive": dict(tj_pos), "stock": dict(tj_stock)}
# (c) uncovered stretch control: delete the (7,11) terrain tri owning that border edge
owner_t = E[e][0]
fi = list(m.fi)
del fi[3 * owner_t:3 * owner_t + 3]
M3 = dict(M1)
M3[(7, 11, "terrain")] = S.Mesh(1, 7, 11, "terrain", m.name, m.lv, m.idall, fi)
r0 = C.compare_border(C.border_profile(M1, (7, 11), "S"), C.border_profile(M1, (7, 12), "N"))
r1 = C.compare_border(C.border_profile(M3, (7, 11), "S"), C.border_profile(M3, (7, 12), "N"))
print(f"C3c uncovered stretch: stock {r0['uncovered_len']}u -> one border tri deleted {r1['uncovered_len']}u "
      f"(B_only {r1['uncovered_B_only']})")
res["C3c_uncovered"] = {"stock": r0["uncovered_len"], "deleted": r1["uncovered_len"]}
p = S.save_json("calibrate.json", res)
print("->", p)
