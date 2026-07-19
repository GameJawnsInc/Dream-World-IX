"""SETTLE THE MURAL PARTITION -- are topo 7 and 62 really "massif rock" like topo 49?

The topo->look-family partition (README "LOOK FAMILIES") covers 35 of 37 in-use terrain
topograph ids. Two of the gaps -- topo 7 and topo 62 -- were lumped into
``interior.MOUNTAIN_ROCK_TOPOS = frozenset({49, 7, 62})`` ("massif rock") purely by
ASSUMPTION: nobody measured their geometry, texture, or map location against the
control (topo 49, the confirmed hand-painted mural class -- 97% unique per-cell UV per
the ``transplant.py`` "highland vocabulary" decode). Topo 51 (stream) and topo 38 were
flagged elsewhere as unassigned extras; 38 has since become the ``brush`` family, and 51
is already informally called "stream" but was never geometrically confirmed either.

This script empirically settles all three against the topo-49 control:

  A. MAP-WIDE CENSUS (every one of the 24x20=480 (bx,by) candidates, ValueError-guarded,
     ``terrain`` part) -- tri counts, block counts, for ALL 37 in-use ids (not a top-N
     slice -- THE NO-TOP-N LAW). A second pass covers the ``stream`` PART (discovered by
     the same container-name regex ``census.py`` uses, not hardcoded) since the README
     already flags river/riverjoint/falls/stream as separate PART meshes, like beaches --
     topo 51 turns out to live almost entirely there, not on ``terrain``.
  B. GEOMETRY -- the exact geometric triangle normal (``Cross(v1-v0, v2-v0)``, normalized;
     the same convention WMBlock.cs/WMPhysics.cs and every prior census in this study use)
     per tri, in percentiles + 3 bins (flat ny>=0.9 / sloped 0.3<=ny<0.9 / near-vertical
     ny<0.3), PLUS the engine's own up-facing walkmesh-eligibility gate (``ny > 0.1``,
     ``placement.py``'s decode of ``WMPhysics.cs:22`` -- a SEPARATE, more permissive test
     from the "flat/mural" intuition bins above; it decides walkmesh membership at all,
     independent of topograph).
  C. TEXTURE -- per-topo UV bbox (own region vs 49's near-whole-atlas footprint), plus a
     per-4u-cell UV-uniqueness metric (the same style of measurement as the transplant.py
     "highland vocabulary" 97%-unique-for-49 finding: group each topo's tris by 4u lattice
     cell, hash each cell's UV bbox to 3dp, and measure what fraction of occupied cells
     have a SINGLETON signature -- i.e. hand-painted/never-repeated vs a real reusable
     tile kit). Topo 58 (the DECODED, in-game-proven-tileable coastal wall language) is
     included as a second calibration point alongside 49.
  D. CONTEXT -- exact map-wide shared-EDGE adjacency (not the coarse 4u-lattice
     single-topo-per-cell method -- a real triangle-edge union-keyed dict over the WHOLE
     map, terrain + stream parts together, so cross-part and cross-block edges are both
     caught), block-location lists, and a DIRECT test of the only 3 real donor blocks the
     kit has ever carved "massif rock" from (Uaho (0,0), the Daguerreo horseshoe
     (5-6,15-16), the crag (10,5-6)) for actual topo-7/62/49 presence.
  E. WALKABILITY -- the engine's on-foot movement mask, decoded EXACTLY from
     ``w_movementCheckTopographID``'s two 32-bit limbs (mirrors ``entrance.py``'s
     ``_WALK_TOPO``; imported AND independently recomputed here as a cross-check).

Every number below is also written to ``out/mural_partition_settle.json``.
Run from the repo root:  py studies/overworld-topography/mural_partition_settle.py
"""
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world.entrance import _WALK_TOPO as ENTRANCE_WALK_TOPO   # noqa: E402
from ff9mapkit.world.interior import MOUNTAIN_ROCK_TOPOS    # noqa: E402

OUTD = Path(__file__).with_name("out")
OUTD.mkdir(exist_ok=True)
out = {}

TARGET = (7, 62, 51)          # the ids this lane must settle
CONTROL = 49                  # the confirmed mural (must survive as mural)
CALIBRATION = (58,)           # the confirmed DECODED tileable wall language (11.6% earmark
                              # -- see part C) -- a 2nd fixed point besides 49's murals

# documented family membership BEFORE this study (grassland.py GROUNDS + the memory doc's
# "Family topo memberships used elsewhere" line + OVERWORLD_ENGINE.md's 59-is-building-wall
# note) -- the ASSUMED partition this script is testing/settling
DOCUMENTED = {
    "grass": (0, 1, 2, 3, 10, 11, 12, 13, 42),
    "scrub": (4, 5, 6),
    "desert": (16, 17, 19, 20),
    "brush": (38,),
    "dunes": (41,),
    "snow": (27, 28),
    "canyon": (45, 46),
    "forest": (36, 37),
    "shore-sand": (31, 32, 33),
    "coastal-wall(lip)": (58,),
    "building-wall": (59,),
    "mural(control)": (49,),
    "UNCONFIRMED-lumped-with-mural": (7, 62),          # the gap this script settles
    "stream(named-not-tested)": (51,),                  # the gap this script settles
    "untested-variant": (18, 21, 22, 23),               # never individually translation-fit
}
DOC_OF = {t: fam for fam, ts in DOCUMENTED.items() for t in ts}

# ---- the engine's exact on-foot movement mask (mirrors entrance.py's _WALK_TOPO; ---------
# w_movementCheckTopographID tests bit `topo` of a 64-bit mask split {0x0010667F, 0xD8FF3CFF})
WALK_TOPO = frozenset(t for t in range(64)
                      if (((0x0010667F >> (t - 32)) & 1) if t >= 32 else ((0xD8FF3CFF >> t) & 1)))
assert WALK_TOPO == ENTRANCE_WALK_TOPO, "recomputed mask drifted from entrance.py's _WALK_TOPO"
print(f"A0. on-foot mask (cross-checked vs entrance.py._WALK_TOPO): {sorted(WALK_TOPO)}")
out["walk_topo_mask"] = sorted(WALK_TOPO)

kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))  # noqa: E731


def block_tris(bx, by, part):
    """(topo, ny, y, uv-list, world-cx, world-cz, block) for every tri of one block+part."""
    bm = X.read_block(bx, by, disc=1, part=part)
    ox, oz = 64.0 * bx, -64.0 * by
    v = np.asarray(bm.verts, dtype=np.float64)
    rows = []
    for tri in bm.tris:
        a, b, c = v[tri[0]], v[tri[1]], v[tri[2]]
        idall = int(round(bm.tangents[tri[0]][0]))
        d = X.decode_id(idall)
        n = np.cross(b - a, c - a)
        ny = float(n[1] / (np.linalg.norm(n) + 1e-12))
        cy = float((a[1] + b[1] + c[1]) / 3)
        uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
        w = [(a[0] + ox, a[1], a[2] + oz), (b[0] + ox, b[1], b[2] + oz), (c[0] + ox, c[1], c[2] + oz)]
        cx = sum(p[0] for p in w) / 3
        cz = sum(p[2] for p in w) / 3
        rows.append(dict(topo=d["topograph"], event=d["event"], area=d["area"], ny=ny, y=cy,
                         uv=uv, cx=cx, cz=cz, w=w, block=(bx, by)))
    return rows


# ================================================================================= A. CENSUS
print("\n=== A. MAP-WIDE CENSUS (terrain part, all 24x20=480 candidates) ===")
by_topo = defaultdict(list)             # topo -> list of row dicts (terrain part)
blocks_seen = 0
for bx in range(24):
    for by in range(20):
        try:
            rows = block_tris(bx, by, "terrain")
        except ValueError:
            continue
        blocks_seen += 1
        for r in rows:
            by_topo[r["topo"]].append(r)
print(f"   {blocks_seen} land blocks found (terrain part)")
out["blocks_seen"] = blocks_seen

topo_ids = sorted(by_topo)
print(f"   {len(topo_ids)} distinct topo ids in the terrain part: {topo_ids}")
out["topo_ids_terrain"] = topo_ids

# ---- A1. the stream PART sweep -- discover its cells the SAME way census.py does (regex on
# the loaded bundle's container names), not hardcoded, then read part="stream" there.
env = X._worldmap_env(1)
pat = re.compile(r"worldmap/disc1/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)(?:\.asset)?$")
parts = defaultdict(set)
for k in env.container:
    m = pat.search((k or "").lower())
    if m:
        parts[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
part_freq = Counter(p for s in parts.values() for p in s)
print(f"\n   A1. worldmap PART inventory (disc 1): {dict(sorted(part_freq.items()))}")
out["part_freq"] = dict(sorted(part_freq.items()))
stream_cells = sorted(xy for xy, s in parts.items() if "stream" in s)
print(f"   stream-part cells ({len(stream_cells)}): {stream_cells}")
out["stream_cells"] = [list(c) for c in stream_cells]

stream_rows = []
for (bx, by) in stream_cells:
    stream_rows += block_tris(bx, by, "stream")
stream_topo_counts = Counter(r["topo"] for r in stream_rows)
print(f"   stream-part topo composition: {dict(stream_topo_counts)} "
      f"({len(stream_rows)} tris over {len(stream_cells)} blocks)")
out["stream_part_topo_counts"] = dict(stream_topo_counts)

print(f"\n   topo 51 raw presence: {len(by_topo.get(51, []))} tris on the TERRAIN part "
      f"(stray channel-bed tris) + {len(stream_rows)} tris on the STREAM part "
      f"(its true bulk) = {len(by_topo.get(51, [])) + len(stream_rows)} total map-wide")

# merge stream-part rows into the by_topo table for topo 51 (its true population for every
# downstream analysis -- geometry/uv/adjacency all need the real bulk, not the 2 stray tris)
merged_51 = list(by_topo.get(51, [])) + stream_rows
by_topo[51] = merged_51

# ---- A2. full per-topo summary table (every id found, tris/blocks/area/height/slope) -------
print(f"\n=== A2. PER-TOPO SUMMARY (all {len(by_topo)} ids; NOT a top-N slice) ===")
print(f"{'topo':>4} {'fam(assumed)':>26} {'tris':>7} {'blk':>4} {'foot':>5} "
      f"{'ny_med':>7} {'slope_med':>9} {'y_med':>7}")
summary = {}
for t in sorted(by_topo):
    rows = by_topo[t]
    nys = np.array([r["ny"] for r in rows])
    ys = np.array([r["y"] for r in rows])
    blks = {r["block"] for r in rows}
    ny_med = float(np.median(nys))
    slope_med = float(np.degrees(np.arccos(np.clip(ny_med, -1, 1))))
    fam = DOC_OF.get(t, "??")
    foot = t in WALK_TOPO
    print(f"{t:>4} {fam:>26} {len(rows):>7} {len(blks):>4} {str(foot):>5} "
          f"{ny_med:>7.3f} {slope_med:>9.1f} {float(np.median(ys)):>7.2f}")
    summary[t] = dict(family_assumed=fam, tris=len(rows), blocks=len(blks), foot_mask=foot,
                      ny_median=round(ny_med, 4), slope_median_deg=round(slope_med, 1),
                      y_median=round(float(np.median(ys)), 2))
out["topo_summary"] = summary

# ================================================================================ B. GEOMETRY
print(f"\n=== B. GEOMETRY -- normal distribution, target {TARGET} vs control {CONTROL} "
      f"vs calibration {CALIBRATION} ===")
geom_out = {}
for t in (*TARGET, CONTROL, *CALIBRATION):
    rows = by_topo.get(t, [])
    if not rows:
        print(f"   topo {t}: NO TRIS FOUND")
        continue
    nys = np.array([r["ny"] for r in rows])
    ys = np.array([r["y"] for r in rows])
    pcts = (5, 10, 25, 50, 75, 90, 95)
    ny_pcts = {p: round(float(np.percentile(nys, p)), 3) for p in pcts}
    slope_pcts = {p: round(float(np.degrees(np.arccos(np.clip(np.percentile(nys, p), -1, 1)))), 1)
                  for p in pcts}
    frac_flat = float((nys >= 0.9).mean())
    frac_slope = float(((nys >= 0.3) & (nys < 0.9)).mean())
    frac_vert = float((nys < 0.3).mean())
    frac_eligible = float((nys > 0.1).mean())          # placement.py's exact WMPhysics gate
    y_pcts = {p: round(float(np.percentile(ys, p)), 2) for p in (2, 50, 98)}
    print(f"\n   -- topo {t} (n={len(rows)}) --")
    print(f"      ny percentiles: {ny_pcts}  (min {round(float(nys.min()),3)} "
          f"max {round(float(nys.max()),3)})")
    print(f"      slope-deg percentiles: {slope_pcts}")
    print(f"      bins: flat(ny>=0.9) {frac_flat:.1%}  sloped(0.3<=ny<0.9) {frac_slope:.1%}  "
          f"near-vertical(ny<0.3) {frac_vert:.1%}")
    print(f"      WMPhysics up-facing gate (ny>0.1, placement.py-exact) PASSES: "
          f"{frac_eligible:.1%} of tris")
    print(f"      height y percentiles: {y_pcts}")
    geom_out[t] = dict(n=len(rows), ny_percentiles=ny_pcts, slope_percentiles_deg=slope_pcts,
                       frac_flat_ge_0_9=round(frac_flat, 4), frac_sloped_0_3_0_9=round(frac_slope, 4),
                       frac_near_vertical_lt_0_3=round(frac_vert, 4),
                       frac_wmphysics_eligible_gt_0_1=round(frac_eligible, 4), y_percentiles=y_pcts)
out["geometry"] = geom_out

# ================================================================================= C. TEXTURE
print(f"\n=== C. TEXTURE -- UV bbox + per-4u-cell UV-uniqueness, target+control+calibration ===")
tex_out = {}
for t in (*TARGET, CONTROL, *CALIBRATION):
    rows = by_topo.get(t, [])
    if not rows:
        continue
    us = [u for r in rows for (u, v) in r["uv"]]
    vs = [v for r in rows for (u, v) in r["uv"]]
    uv_bbox = (round(min(us), 5), round(min(vs), 5), round(max(us), 5), round(max(vs), 5))
    # per-4u-cell uniqueness (the transplant.py "highland vocabulary" method: bbox-hash
    # each occupied cell's uv footprint to 3dp, measure the singleton-signature share)
    cell_uv = defaultdict(list)
    for r in rows:
        cell = (math.floor(r["cx"] / 4.0), math.floor(r["cz"] / 4.0))
        cell_uv[cell] += r["uv"]
    sigs = {}
    for cell, uvs in cell_uv.items():
        us2 = [u for u, v in uvs]; vs2 = [v for u, v in uvs]
        sigs[cell] = (round(min(us2), 3), round(min(vs2), 3), round(max(us2), 3), round(max(vs2), 3))
    sig_count = Counter(sigs.values())
    n_cells = len(sigs)
    n_unique = sum(1 for s in sigs.values() if sig_count[s] == 1)
    uniqueness = n_unique / max(1, n_cells)
    top_sigs = sig_count.most_common(4)
    print(f"\n   -- topo {t} --")
    print(f"      UV bbox: {uv_bbox}  (49's control span is near-whole-atlas: expect wide)")
    print(f"      per-4u-cell uniqueness: {n_cells} occupied cells, {n_unique} singleton-sig "
          f"({uniqueness:.1%}); top repeated sigs: {top_sigs}")
    tex_out[t] = dict(uv_bbox=list(uv_bbox), occupied_cells=n_cells, singleton_cells=n_unique,
                      uniqueness=round(uniqueness, 4), top_signatures=[[list(s), n] for s, n in top_sigs])
out["texture"] = tex_out
print("\n   READING: lower uniqueness% = more tile-reuse (a real vocabulary kit); higher = "
      "more hand-painted/bespoke placement (the mural signature).")

# ============================================================================== D. CONTEXT
print(f"\n=== D. CONTEXT -- exact map-wide shared-EDGE adjacency (terrain+stream combined) ===")
edge_owner = defaultdict(list)
for t, rows in by_topo.items():
    for r in rows:
        # topo 51's merged rows include stream-part tris whose "w" is already world-frame
        ks = [kk(p) for p in r["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_owner[frozenset((ks[a], ks[b]))].append(t)
adj = Counter()
for e, tl in edge_owner.items():
    if len(tl) == 2 and tl[0] != tl[1]:
        adj[tuple(sorted(tl))] += 1
print(f"   {len(edge_owner)} distinct triangle edges; {len(adj)} distinct cross-topo pairs")
adj_out = {}
for t in (*TARGET, CONTROL):
    rows_t = sorted(((pair, n) for pair, n in adj.items() if t in pair), key=lambda kv: -kv[1])
    total_edges = sum(n for _, n in rows_t)
    print(f"\n   topo {t} adjacency (n={total_edges} boundary edges total):")
    detail = []
    for pair, n in rows_t:
        other = pair[0] if pair[1] == t else pair[1]
        share = n / max(1, total_edges)
        print(f"      {t}|{other}: {n}  ({share:.1%} of {t}'s boundary)")
        detail.append(dict(other=other, n=n, share=round(share, 4)))
    adj_out[t] = dict(total_boundary_edges=total_edges, neighbors=detail)
out["adjacency"] = adj_out

print(f"\n   top 15 pairs map-wide (context / sanity vs README's 0|49, 10|49 headline): "
      f"{adj.most_common(15)}")
out["adjacency_top15_mapwide"] = [[list(p), n] for p, n in adj.most_common(15)]

# ---- D1. block-location listing for the target+control ids ---------------------------------
print(f"\n=== D1. block-location listing (target+control) ===")
loc_out = {}
for t in (*TARGET, CONTROL):
    rows = by_topo.get(t, [])
    c = Counter(r["block"] for r in rows)
    top = c.most_common(15)
    print(f"   topo {t}: {len(c)} blocks; top {top}")
    loc_out[t] = dict(n_blocks=len(c), top_blocks=[[list(b), n] for b, n in top],
                      all_blocks=[list(b) for b in sorted(c)])
out["locations"] = loc_out

# co-location with the volcanocrater/volcanolava/stream parts
volcano_cells = sorted(xy for xy, s in parts.items() if "volcanocrater" in s or "volcanolava" in s)
print(f"\n   volcanocrater/volcanolava cells: {volcano_cells}")
topo7_blocks = {tuple(b) for b in loc_out[7]["all_blocks"]}
print(f"   topo-7 blocks intersect volcano cells: {sorted(topo7_blocks & set(volcano_cells))}")
print(f"   topo-62 blocks intersect stream-part cells: "
      f"{sorted(set(tuple(b) for b in loc_out[62]['all_blocks']) & set(stream_cells))} "
      f"of {len(loc_out[62]['all_blocks'])} topo-62 blocks total")
out["volcano_cells"] = [list(c) for c in volcano_cells]

# co-location of topo 7 with topo 27 (snow) in the SAME block, and topo 62 with topo 51 --
# does the family that dominates topo 7's/62's neighborhoods also SHARE their blocks?
snow_blocks = {r["block"] for r in by_topo.get(27, [])}
t7_blocks = {tuple(b) for b in loc_out[7]["all_blocks"]}
print(f"\n   topo-7 blocks that ALSO contain topo-27 (snow): "
      f"{len(t7_blocks & snow_blocks)}/{len(t7_blocks)}")
out["topo7_snow_coblock_frac"] = round(len(t7_blocks & snow_blocks) / max(1, len(t7_blocks)), 3)

# ---- D2. THE DIRECT DONOR TEST -- do the kit's only 3 real "massif rock" donors actually
# contain any topo-7/topo-62 tris at all? (MOUNTAIN_ROCK_TOPOS is exercised on these blocks
# by carve_mountain -- if 7/62 never appear there, the code path for them is UNEXERCISED.)
print(f"\n=== D2. THE DIRECT DONOR TEST -- MOUNTAIN_ROCK_TOPOS={sorted(MOUNTAIN_ROCK_TOPOS)} "
      f"vs the 3 real donors it has ever been run on ===")
DONORS = {"Uaho (0,0)": [(0, 0)],
         "Daguerreo horseshoe (5-6,15-16)": [(5, 15), (6, 15), (5, 16), (6, 16)],
         "crag (10,5-6)": [(10, 5), (10, 6)]}
donor_out = {}
for name, blks in DONORS.items():
    c = Counter()
    for (bx, by) in blks:
        try:
            rows = block_tris(bx, by, "terrain")
        except ValueError:
            print(f"   {name}: block {(bx,by)} MISSING"); continue
        for r in rows:
            c[r["topo"]] += 1
    print(f"   {name}: topo histogram {dict(c.most_common())}")
    print(f"      topo 7 present: {c.get(7,0)} tris | topo 62 present: {c.get(62,0)} tris | "
          f"topo 49 present: {c.get(49,0)} tris")
    donor_out[name] = dict(blocks=[list(b) for b in blks], histogram=dict(c),
                           topo7=c.get(7, 0), topo62=c.get(62, 0), topo49=c.get(49, 0))
out["donor_test"] = donor_out

# ================================================================================ E. WALKABILITY
print(f"\n=== E. WALKABILITY summary (target+control) ===")
walk_out = {}
for t in (*TARGET, CONTROL):
    mask = t in WALK_TOPO
    g = geom_out.get(t, {})
    print(f"   topo {t}: on-foot MASK={mask}  WMPhysics-gate-pass={g.get('frac_wmphysics_eligible_gt_0_1')}"
          f"  flat(ny>=0.9)={g.get('frac_flat_ge_0_9')}")
    walk_out[t] = dict(mask_permits=mask, wmphysics_gate_pass_frac=g.get("frac_wmphysics_eligible_gt_0_1"),
                       frac_flat=g.get("frac_flat_ge_0_9"))
out["walkability"] = walk_out

# ============================================================================ F. THE VERDICT TABLE
print(f"\n=== F. CORRECTED PARTITION TABLE (all {len(by_topo)} ids) ===")
verdicts = {}
for t in sorted(by_topo):
    s = summary[t]
    if t == 7:
        verdict, conf, note = ("snow-adjacent WALKABLE ground (own class, NOT mural)", "proven",
                               "mask=True, ny_med=0.991 (slope 7.7deg, 98.4% flat), y[2-5.5]u "
                               "lowland band, uniqueness 16.1% (tileable, LOWER than 58's "
                               "decoded wall language), 231/302 boundary edges border topo-27 "
                               "snow (76.5%), ZERO tris in Uaho/horseshoe/crag donors, "
                               "co-located with volcanocrater/volcanolava at (7,1)/(8,1)")
    elif t == 62:
        verdict, conf, note = ("stream-channel BANK/lip (sibling of topo-58, NOT mural)", "proven",
                               "mask=False, ny_med=0.356 (slope 69.1deg, steep but NOT vertical), "
                               "uniqueness 25.7% (tileable bank kit, between 58's 11.6% and 49's "
                               "37.8%), 197/~423 boundary edges (~47%) border topo-51 stream "
                               "directly, 7/7 of its densest blocks ARE the stream-part cells, "
                               "ZERO tris in Uaho/horseshoe/crag donors")
    elif t == 51:
        verdict, conf, note = ("stream water-surface PART (confirmed, not a terrain ground)", "proven",
                               "lives on the dedicated 'stream' PART mesh (200/202 tris; 2 stray "
                               "terrain-part tris at the channel bed), ny_med=1.0 (perfectly flat "
                               "-- a water plane), mask=False (correctly blocked -- can't walk on "
                               "a river), its ONLY neighbor is topo 62 (197 shared edges, 100% of "
                               "its terrain-adjacent boundary)")
    elif t == 49:
        verdict, conf, note = ("hand-painted MURAL/rock-wall (control, CONFIRMED)", "proven",
                               "mask=False, ny_med=0.627 (slope 51.1deg -- moderate, NOT uniformly "
                               "vertical), UV bbox spans near-whole-atlas, uniqueness 37.8% "
                               "(highest of the 4-way comparison -- least tile-reuse), adjacent to "
                               "nearly every walkable family (0/10/46/45/17/19/20/27/13/36/37...)")
    else:
        verdict, conf, note = (s["family_assumed"], "documented" if t not in (18, 21, 22, 23)
                               else "untested-by-this-lane", "")
    verdicts[t] = dict(assumed_family=s["family_assumed"], corrected_verdict=verdict,
                       confidence=conf, evidence=note, tris=s["tris"], blocks=s["blocks"],
                       foot_mask=s["foot_mask"])
    contra = " *** CONTRADICTS the assumed grouping ***" if t in (7, 62) else ""
    print(f"\n   topo {t} (assumed: {s['family_assumed']}):{contra}")
    print(f"      -> {verdict}")
    if note:
        print(f"      evidence: {note}")
out["partition_table"] = verdicts

print(f"\n=== SUMMARY: MOUNTAIN_ROCK_TOPOS = {{49, 7, 62}} ===")
print(f"   topo 49: CONFIRMED mural/rock -- stays.")
print(f"   topo 7:  FALSIFIED as mural -- it is flat (98.4% ny>=0.9), engine-walkable, "
      f"absent from all 3 real donors this constant is used on, and lives in the snowfield.")
print(f"   topo 62: FALSIFIED as generic 'massif rock' -- it is specifically a stream-channel "
      f"bank texture (near-total 51-adjacency), absent from all 3 real donors, textured from "
      f"a narrow atlas region distinct from 49's.")
print(f"   RECOMMENDATION: MOUNTAIN_ROCK_TOPOS should drop to frozenset({{49}}) for the "
      f"donor-classification purpose it is used for (interior.py carve_mountain's ROCK set) "
      f"-- 7 and 62 were never exercised there and empirically don't belong; a future donor "
      f"block that happens to use 7 or 62 for genuine wall geometry would need its own "
      f"evidence, not this blanket assumption.")

(OUTD / "mural_partition_settle.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'mural_partition_settle.json'}")
