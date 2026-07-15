"""THE ENSEMBLE INVENTORY -- what exactly rides with the horseshoe massif?

Stage A of THE ENSEMBLE CARRY: before any code, measure the donor blocks'
auxiliary parts so the subsetting + deployment rules come from bytes:

  A. PART UNIVERSE -- which parts exist on each donor block (the Donor.txt choice
     needs one block carrying every part transform we deploy).
  B. CHANNELS -- stride + channel layout per part; are tangent rows terrain-style
     [idall,0,0,1] or real tangents (split/write fidelity depends on it)?
  C. COMPONENTS vs THE RIM -- per part: weld-connected components, vert/tri counts,
     y ranges, and CONTAINMENT vs the massif's outer rim polygon (fully inside /
     straddling / outside) -- the subset rule.
  D. APERTURE COVERAGE -- which components' verts own the ensemble-aperture ring.

Run from the repo root:  py studies/overworld-topography/ensemble_inventory.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import interior as IN                  # noqa: E402
from ff9mapkit.world.island import _real_block_parts        # noqa: E402

BLOCK = 64.0
DONOR = [(5, 15), (5, 16), (6, 15), (6, 16)]
ROCK = set(IN.MOUNTAIN_ROCK_TOPOS)
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
OUTD = Path(__file__).with_name("out")
out = {}

# ---- A. the part universe per donor block --------------------------------------------------------
print("A. part universe:")
universe = {}
for blk in DONOR:
    occ = _real_block_parts(blk, disc=1)
    universe[blk] = sorted(occ)
    print(f"   {blk}: {dict(occ)}")
out["universe"] = {f"{b[0]},{b[1]}": universe[b] for b in DONOR}

# ---- the massif blob + rim polygon (for containment), via the shipped builder pieces -------------
tris = []
for (bx, by) in DONOR:
    bm = X.read_block(bx, by, disc=1, part="terrain")
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        tris.append(dict(
            w=[(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1],
                bm.verts[j][2] - BLOCK * by) for j in tri],
            topo=X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]))
edge_tris = defaultdict(list)
for ti, t in enumerate(tris):
    ps = [kk(v) for v in t["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_tris[tuple(sorted((ps[a], ps[b])))].append(ti)
adj = defaultdict(set)
for ts in edge_tris.values():
    r = [t for t in ts if tris[t]["topo"] in ROCK]
    for i in range(len(r)):
        for j in range(i + 1, len(r)):
            adj[r[i]].add(r[j]); adj[r[j]].add(r[i])
comps, seen = [], set()
for s in range(len(tris)):
    if tris[s]["topo"] not in ROCK or s in seen:
        continue
    comp = {s}; st = [s]
    while st:
        t = st.pop()
        for t2 in adj[t]:
            if t2 not in comp:
                comp.add(t2); st.append(t2)
    seen |= comp
    comps.append(comp)
comps.sort(key=len, reverse=True)
blob = set(comps[0])


def once_edges(tset):
    eu = Counter()
    for t in tset:
        ps = [kk(v) for v in tris[t]["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu[tuple(sorted((ps[a], ps[b])))] += 1
    return [e for e, n in eu.items() if n == 1]


rings0 = IN.chain_rings(once_edges(blob), "r0")
rings0.sort(key=lambda g: -abs(IN.signed_area(g)))
inner_pts = {p for g in rings0[1:] for p in g}
st = [t for e in once_edges(blob) if e[0] in inner_pts and e[1] in inner_pts
      for t in edge_tris[e] if t not in blob]
while st:
    t = st.pop()
    if t in blob:
        continue
    blob.add(t)
    ps = [kk(v) for v in tris[t]["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        for t2 in edge_tris[tuple(sorted((ps[a], ps[b])))]:
            if t2 not in blob and tris[t2]["topo"] not in ROCK:
                st.append(t2)
rings = IN.chain_rings(once_edges(blob), "post")
rings.sort(key=lambda g: -abs(IN.signed_area(g)))
rim_poly = [(p[0], p[2]) for p in rings[0]]
aperture = set(rings[1]) if len(rings) > 1 else set()
print(f"massif blob {len(blob)} tris; rim poly {len(rim_poly)} pts; "
      f"aperture ring {len(aperture)} pts")

# ---- B/C/D. per part: channels, components, containment, aperture coverage -----------------------
PARTS = ("object", "falls", "river", "riverjoint", "beach1")
for part in PARTS:
    total = dict(comps=[])
    for (bx, by) in DONOR:
        try:
            pm = X.read_block(bx, by, disc=1, part=part)
        except Exception:
            continue
        off = np.array([BLOCK * bx, 0.0, -BLOCK * by])
        V = np.asarray(pm.verts, dtype=np.float64) + off
        nt = len(pm.flat_index) // 3
        ptri = [pm.flat_index[3 * t:3 * t + 3] for t in range(nt)]
        # channels
        ts_ = pm.tangents
        tan_kind = "none"
        if ts_ is not None and len(ts_):
            rows = np.asarray(ts_, dtype=np.float64)
            if np.allclose(rows[:, 1:3], 0.0) and np.allclose(np.abs(rows[:, 3]), 1.0):
                ids = sorted({int(round(r[0])) for r in rows})
                tan_kind = f"idall-style ({len(ids)} ids, e.g. {ids[:4]})"
            else:
                tan_kind = "REAL tangents"
        if "chan" not in total:
            total["chan"] = dict(stride=pm.stride,
                                 channels={k: v for k, v in pm.channels.items()},
                                 uv=pm.uvs is not None, nrm=pm.normals is not None,
                                 tan=tan_kind)
        # weld components within this block's part
        padj = defaultdict(set)
        e2t = defaultdict(list)
        for t, tri in enumerate(ptri):
            for a, b in ((0, 1), (1, 2), (2, 0)):
                e2t[tuple(sorted((kk(V[tri[a]]), kk(V[tri[b]]))))].append(t)
        for ts2 in e2t.values():
            for i in range(len(ts2)):
                for j in range(i + 1, len(ts2)):
                    padj[ts2[i]].add(ts2[j]); padj[ts2[j]].add(ts2[i])
        seen2 = set()
        for s in range(nt):
            if s in seen2:
                continue
            comp = {s}; st2 = [s]
            while st2:
                t = st2.pop()
                for t2 in padj[t]:
                    if t2 not in comp:
                        comp.add(t2); st2.append(t2)
            seen2 |= comp
            pts = [V[i] for t in comp for i in ptri[t]]
            inside = sum(1 for p in pts if IN.pip(p[0], p[2], rim_poly))
            apt = sum(1 for p in pts if kk(p) in aperture)
            total["comps"].append(dict(
                blk=(bx, by), tris=len(comp), verts=len({kk(p) for p in pts}),
                y=[round(min(p[1] for p in pts), 1), round(max(p[1] for p in pts), 1)],
                inside=f"{inside}/{len(pts)}", ap_verts=apt))
    if "chan" not in total:
        continue
    print(f"\n{part}: stride {total['chan']['stride']}, tan {total['chan']['tan']}")
    for c in sorted(total["comps"], key=lambda c: -c["tris"]):
        print(f"   blk {c['blk']}: {c['tris']:3d} tris {c['verts']:3d} verts "
              f"y {c['y']}, inside-rim {c['inside']}, aperture-ring verts {c['ap_verts']}")
    out[part] = total

OUTD.mkdir(exist_ok=True)
(OUTD / "ensemble_inventory.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'ensemble_inventory.json'}")
