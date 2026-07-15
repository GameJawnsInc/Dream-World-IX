"""THE HORSESHOE DONOR CHECK -- qualify the Daguerreo massif as a world-mountain donor.

The crag closed multi-block donors; the horseshoe (the v4 transplant's centerpiece,
anatomy = daguerreo_massif_anatomy.py) is the last unproven claim in the mountain arc:
"any studied massif, any size". It brings three unknowns the crag did not:

  A. THE FALLS APERTURES -- the anatomy proved literal holes in the Terrain behind the
     falls sheets. carve_mountain's plug path requires every extra blob ring to be the
     donor's OBJECT-part vertex set (THE FALLS-APERTURE LAW, proven on Uaho's alcove
     roof). Are the horseshoe's holes Object-backed -- or do their rings belong to the
     falls/river PARTS (which the terrain carve does not read)?
  B. THE HANGING BOWL -- the massif encloses the topo-13 river bowl at ~15.2; the blob's
     pocket fill would carry the WHOLE bowl (floor + river channel + any islet) as
     mountain-attached terrain. What topos ride along, and what stays behind (the river
     WATER + falls SHEETS are separate parts -- a terrain carve ships a dry bed)?
  C. SCALE -- the massif spans multiple blocks; what rim radius results after the fills,
     what target span does it demand, can world-island mint a bench that big, and does
     any all-free ocean window that size exist on the real map?

Stages: region component census -> the SHIPPED IN._mountain_blob (build or exact
refusal + ring forensics) -> the SHIPPED IN.carve_mountain dry-carve on an offline mint
sized to fit -> the map-wide free-window scan. Artifacts -> out/horseshoe_donor.json.
Run from the repo root:  py studies/overworld-topography/horseshoe_donor_check.py
"""
import json
import math
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                       # noqa: E402
from ff9mapkit.world import extract as X                   # noqa: E402
from ff9mapkit.world import interior as IN                 # noqa: E402
from ff9mapkit.world import mesh as M                      # noqa: E402
from ff9mapkit.world.island import build_landmass, _real_block_parts  # noqa: E402

REGION = [(5, 15), (6, 15), (7, 15), (5, 16), (6, 16), (7, 16)]
BLOCK = 64.0
ROCK = set(IN.MOUNTAIN_ROCK_TOPOS)
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
OUTD = Path(__file__).with_name("out")
out = {}

# ---- stage 1: which blocks hold the massif component --------------------------------------------
tris = []
for (bx, by) in REGION:
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except ValueError:
        continue
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        tris.append(dict(
            w=[(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1],
                bm.verts[j][2] - BLOCK * by) for j in tri],
            topo=X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"],
            blk=(bx, by)))
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
big = comps[0]
donor_blocks = sorted(Counter(tris[t]["blk"] for t in big))
print(f"stage 1: {len(comps)} rock comps, sizes {[len(c) for c in comps[:5]]}; "
      f"the massif = {len(big)} tris across {donor_blocks}")
out["component"] = dict(n=len(big), blocks=[list(b) for b in donor_blocks])

# ---- stage 2: the SHIPPED blob builder (build, or exact refusal + ring forensics) ----------------
blob_info = None
try:
    blob_info = IN._mountain_blob(donor_blocks, rock_topos=ROCK, alcove_box=None, disc=1)
except ValueError as e:
    print(f"stage 2: _mountain_blob REFUSED -- {e}")
    out["blob"] = dict(ok=False, refusal=str(e))
if blob_info:
    B = blob_info
    pockets = Counter(B["dtopo"][t] for t in B["blob"] if B["dtopo"][t] not in ROCK)
    ys = [p[1] for p in B["rim"]]
    print(f"stage 2: blob {len(B['blob'])} tris, rim {len(B['rim'])} pts "
          f"y[{min(ys):.1f},{max(ys):.1f}] radius {B['r_rim']:.1f}u; "
          f"apertures {[len(r) for r in B['apertures']]}; pocket topos {dict(pockets)}")
    out["blob"] = dict(ok=True, tris=len(B["blob"]), rim=len(B["rim"]),
                       rim_y=[round(min(ys), 1), round(max(ys), 1)],
                       radius=round(B["r_rim"], 1),
                       apertures=[len(r) for r in B["apertures"]],
                       pockets={str(k): v for k, v in pockets.items()})
else:
    # ring forensics ON THE FLOODED BLOB (the module's own state at refusal): whose
    # verts own the surviving interior ring(s)?
    part_keys = {}
    for part in ("object", "falls", "river", "riverjoint", "beach1"):
        keys = set()
        for (bx, by) in donor_blocks:
            try:
                pm = X.read_block(bx, by, disc=1, part=part)
            except Exception:
                continue
            off = np.array([BLOCK * bx, 0.0, -BLOCK * by])
            for p in (np.asarray(pm.verts, dtype=np.float64) + off):
                keys.add(kk(p))
        if keys:
            part_keys[part] = keys
    blob2 = set(big)

    def once_edges(tset):
        eu = Counter()
        for t in tset:
            ps = [kk(v) for v in tris[t]["w"]]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                eu[tuple(sorted((ps[a], ps[b])))] += 1
        return [e for e, n in eu.items() if n == 1]

    rings0 = IN.chain_rings(once_edges(blob2), "f0")
    rings0.sort(key=lambda g: -abs(IN.signed_area(g)))
    inner_pts = {p for g in rings0[1:] for p in g}
    st = [t for e in once_edges(blob2) if e[0] in inner_pts and e[1] in inner_pts
          for t in edge_tris[e] if t not in blob2]
    while st:
        t = st.pop()
        if t in blob2:
            continue
        blob2.add(t)
        ps = [kk(v) for v in tris[t]["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            for t2 in edge_tris[tuple(sorted((ps[a], ps[b])))]:
                if t2 not in blob2 and tris[t2]["topo"] not in ROCK:
                    st.append(t2)
    rings = IN.chain_rings(once_edges(blob2), "forensics")
    rings.sort(key=lambda g: -abs(IN.signed_area(g)))
    pock = Counter(tris[t]["topo"] for t in blob2 if tris[t]["topo"] not in ROCK)
    bpts = [v for t in blob2 for v in tris[t]["w"]]
    cxb = (min(p[0] for p in bpts) + max(p[0] for p in bpts)) / 2
    czb = (min(p[2] for p in bpts) + max(p[2] for p in bpts)) / 2
    rim0 = rings[0]
    r_rim = max(math.hypot(p[0] - cxb, p[2] - czb) for p in rim0)
    print(f"   forensics (flooded blob {len(blob2)} tris, pockets {dict(pock)}): "
          f"rings {[len(r) for r in rings]}; outer rim radius {r_rim:.1f}u "
          f"y[{min(p[1] for p in rim0):.1f},{max(p[1] for p in rim0):.1f}]")
    out["forensics"] = dict(blob=len(blob2), pockets={str(k): v for k, v in pock.items()},
                            rings=[len(r) for r in rings], radius=round(r_rim, 1))
    for ri, r in enumerate(rings[1:9], 1):
        owned = set()
        hits = {}
        for part, keys in part_keys.items():
            h = [p for p in r if p in keys]
            if h:
                hits[part] = len(h)
                owned |= set(h)
        print(f"   interior ring {ri} ({len(r)} pts, "
              f"y[{min(p[1] for p in r):.1f},{max(p[1] for p in r):.1f}]): part hits "
              f"{hits}; owned by ANY part {len(owned)}/{len(r)}")
        out["forensics"][f"ring{ri}"] = dict(pts=len(r), hits=hits,
                                             owned=len(owned))

# ---- stage 3b (refusal path): can world-island even mint a horseshoe-scale bench? ----------------
if not blob_info:
    print("stage 3b: horseshoe-scale bench feasibility (offline r69 mint)...")
    try:
        built = build_landmass(center=(512.0, -1216.0), base_radius=69.0, seed=11.0,
                               lobes=1, n_patches=0)
        from ff9mapkit.world.island import verify_landmass
        rep = verify_landmass(built)
        print(f"   r69 mint: {len(built['blocks'])} blocks, verify clean = {rep['clean']}")
        out["bench_r69"] = dict(blocks=len(built["blocks"]), clean=bool(rep["clean"]))
    except ValueError as e:
        print(f"   r69 mint REFUSED -- {e}")
        out["bench_r69"] = dict(clean=False, refusal=str(e))

# ---- stage 3: the dry carve on an offline mint sized to fit --------------------------------------
if blob_info:
    need = blob_info["r_rim"] + 6.5 + 2.0
    radius = math.ceil(need + 8.0)
    print(f"stage 3: minting an offline r{radius} bench (need {need:.1f}u clear)...")
    # centre on a 4-corner so the span tiles evenly
    CX, CZ = 512.0, -1216.0
    built = build_landmass(center=(CX, CZ), base_radius=float(radius), seed=11.0,
                           lobes=1, n_patches=0)
    print(f"   mint blocks: {sorted(built['blocks'])}")
    tmp = Path(tempfile.mkdtemp(prefix="ff9_horse_"))
    blocks = {}
    for blk, bm in built["blocks"].items():
        p = M.write_ff9mesh(bm, tmp / f"m_{blk[0]}_{blk[1]}.ff9mesh")
        blocks[blk] = M.blockmesh_from_ff9mesh(p, disc=1, x=blk[0], y=blk[1],
                                               part="terrain")
    soup = IN.soup_from_blocks(blocks)
    try:
        res = IN.carve_mountain(soup, near=(CX, CZ), donor=donor_blocks, alcove=None)
        rep = res["report"]
        print(f"   DRY CARVE: ALL GATES PASS -- placed {res['center']} rot "
              f"{rep['rot_deg']}deg over {len(rep['blocks'])} blocks; "
              f"{rep['blob_tris']} tris (+{rep['plugs']} plugs), peak y {rep['peak_y']}, "
              f"zip rise {rep['zip_rise']}, rigidity {rep['rock_rigid'] * 100:.1f}%, "
              f"apron {rep['apron_slope']}deg")
        out["dry_carve"] = {"ok": True, "bench_radius": radius,
                            **{k: rep[k] for k in ("blob_tris", "plugs", "peak_y",
                                                   "zip_rise", "rock_rigid",
                                                   "apron_slope", "blocks")}}
    except ValueError as e:
        print(f"   DRY CARVE REFUSED -- {e}")
        out["dry_carve"] = {"ok": False, "bench_radius": radius, "gate": str(e)}

# ---- stage 4: map-wide free ocean windows (deployability) -----------------------------------------
GP = Path(_cfg.find_game_path(None))
MODW = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
free = {}
for bx in range(24):
    for by in range(20):
        occ = _real_block_parts((bx, by), disc=1)
        dep = (MODW / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh").exists()
        free[(bx, by)] = (not occ) and not dep
for k in (2, 3):
    wins = [(bx, by) for bx in range(24 - k + 1) for by in range(20 - k + 1)
            if all(free[(bx + dx, by + dy)] for dx in range(k) for dy in range(k))]
    print(f"stage 4: free {k}x{k} ocean windows (top-left): {wins}")
    out[f"free_{k}x{k}"] = [list(w) for w in wins]

OUTD.mkdir(exist_ok=True)
(OUTD / "horseshoe_donor.json").write_text(json.dumps(out, indent=1, default=str))
print(f"-> {OUTD / 'horseshoe_donor.json'}")
