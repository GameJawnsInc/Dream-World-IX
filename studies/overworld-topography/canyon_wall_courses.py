"""CANYON'S UN-CHASED 3rd V-LEVEL -- is the canyon coastal wall band a 2-course wall?

The ground-families decode (ground_families_anatomy.py) shipped ONE (wall_du, wall_dv)
pair per family, modelling every family's topo-58 coastal wall as a single flat quad-row
borrowed from the grass ROCK band (u[0.699,0.947] x v[0.893,0.923], a 0.24805-wide x
0.03028-tall rect -- ~4 TILE_U columns x ~1 TILE_V row of the 128px lattice
rock_wall_language.py decoded for the INTERIOR (topo-49) walls). canyon's own wall_probe
run (README.md line 505) noted "the red band shows a 3rd v-level (possible 2-row course
wall)" and never chased it. If real, a single delta pair describes at most ONE of two
courses and the shipped canyon wall constants (-0.69509, -0.49722) are structurally
incomplete -- any tall canyon wall face repeats one texture row instead of alternating
base/crest content.

METHOD -- two independent passes, both map-wide over ALL 480 (bx,by) candidates, NO
top-N slicing (THE METHOD LAW + THE NO-TOP-N LAW):

  PASS A -- reproduce family_wall_envelope.py's CANONICAL method exactly (topo-agnostic
  UV-band membership, +-0.006 EPS, union-find connected "faces" over shared verts) so its
  quoted canyon MAP-WIDE figure (655 tris / 48 faces) is independently re-derived here as
  a sanity gate, THEN go one level deeper than that script did: for every face, keep the
  full sorted list of distinct 5dp v-levels (not just the count), and for every face with
  >=3 levels ("the 3rd v-level"), dump per-level world-Y range + u-range + the level-to-
  level v spacing measured against TILE_V=0.03125 (the SAME 128px lattice
  rock_wall_language.py measured for the interior topo-49 course system) and against the
  row's OWN measured height (~0.030), to tell apart three concrete hypotheses:
    (i)   VERTICAL TILING of ONE course -- extra level ~= a whole multiple of the row's
          own span higher/lower, SAME u-range, taller-than-normal face (a general portrait-
          repeat law, not a 2nd distinct texture).
    (ii)  BOUNDARY NOISE -- an extra level with near-zero vertex support, no y-structure.
    (iii) A GENUINE 2nd COURSE -- extra level at an unrelated v, DIFFERENT u-range and/or
          a materially different (non-overlapping) world-Y band from the other levels.
  Run for canyon AND 3 controls (grass/desert/snow) so canyon's multi-level RATE and
  pattern can be judged against the general background rate for this metric (a single
  family showing SOME multi-level faces is not automatically a 2nd course -- the question
  is whether canyon's case is qualitatively different).

  PASS B -- an ADJACENCY-only re-derivation (no pre-supposed UV window at all: pick every
  topo-58 tri that shares an EDGE with a family-topo tri, map-wide) as a cross-check that
  the shipped single-band window is wide enough to contain everything reachable from the
  family ground -- and to flag BOUNDARY CONTAMINATION (a wall tri edge-adjacent to MORE
  than one family, which could manufacture a spurious "extra" v-level out of a neighbour's
  own wall band rather than canyon's own).

Run from the repo root:  py studies/overworld-topography/canyon_wall_courses.py
Artifacts -> studies/overworld-topography/out/canyon_wall_courses.json
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402

OUT = Path(__file__).with_name("out") / "canyon_wall_courses.json"
ROCK_U = (0.699, 0.947)
ROCK_V = (0.893, 0.923)
EPS = 0.006                                                  # family_wall_envelope.py's band tolerance
JITTER = 0.008                                                # its face_vlevels row-merge gap
TILE_U, TILE_V = 0.0625, 0.03125                              # rock_wall_language.py's 128px lattice
WALL_TOPO = 58
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

FAMS = {"grass": (0,), "desert": (17, 16, 19, 20), "snow": (27, 28), "canyon": (45, 46)}


def shipped_band(fam):
    g = G.GROUNDS[fam]
    return (ROCK_U[0] + g["wall_du"], ROCK_V[0] + g["wall_dv"],
            ROCK_U[1] + g["wall_du"], ROCK_V[1] + g["wall_dv"])


def in_band(uv, b):
    return b[0] - EPS <= uv[0] <= b[2] + EPS and b[1] - EPS <= uv[1] <= b[3] + EPS


# ---- 0. map-wide census (every candidate, no slicing) -------------------------------------------
census = {}
for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        tris = []
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            tris.append(dict(
                w=[(bm.verts[j][0] + 64.0 * bx, bm.verts[j][1], bm.verts[j][2] - 64.0 * by)
                   for j in tri],
                uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri],
                topo=X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]))
        census[(bx, by)] = tris
print(f"0. CENSUS: {len(census)}/480 candidate blocks host terrain (rest are open sea)")
canyon_blocks = sorted(blk for blk, tl in census.items() if any(t["topo"] in FAMS["canyon"] for t in tl))
print(f"   canyon-bearing blocks (topo 45/46), ALL {len(canyon_blocks)} of them: "
      f"{[f'{b[0]},{b[1]}' for b in canyon_blocks]}")


# ---- PASS A: canonical topo-agnostic UV-band method + per-face v-level detail -------------------
def connected_faces(wall_tris):
    """union-find over shared verts -> list of tri-index-lists (family_wall_envelope.wall_stats)."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for ti, t in enumerate(wall_tris):
        r0 = find(("t", ti))
        for p in t["w"]:
            parent[find(("v", kk(p)))] = r0
    comps = defaultdict(list)
    for ti in range(len(wall_tris)):
        comps[find(("t", ti))].append(ti)
    return list(comps.values())


def levels_of(vs, gap=JITTER):
    vs = sorted(set(round(v, 5) for v in vs))
    if not vs:
        return []
    out = [[vs[0]]]
    for v in vs[1:]:
        if v - out[-1][-1] > gap:
            out.append([v])
        else:
            out[-1].append(v)
    return [round(float(np.mean(g)), 5) for g in out]


results = {"passA": {}, "passA58": {}, "passB": {}}
for fam in FAMS:
    b = shipped_band(fam)
    wall_any = [t for tl in census.values() for t in tl if all(in_band(uv, b) for uv in t["uv"])]
    topo_hist = Counter(t["topo"] for t in wall_any)
    print(f"\n-- {fam} shipped-band topo composition (topo-AGNOSTIC, matching "
          f"family_wall_envelope.py's own method exactly): {dict(topo_hist)}")
    # THE CONTAMINATION CHECK: family_wall_envelope.py's in_band() test never filters by
    # topo -- if a DIFFERENT tile system (topo-49's interior escarpment courses,
    # rock_wall_language.py) happens to paint tris inside this family's shifted UV window,
    # its own (already-understood, ALREADY multi-course) content gets counted as if it were
    # this family's dedicated coastal wall. Report the STRICT topo-58-only subset alongside.
    wall = [t for t in wall_any if t["topo"] == WALL_TOPO]
    if len(wall) != len(wall_any):
        print(f"   ** {len(wall_any) - len(wall)}/{len(wall_any)} shipped-band tris are NOT "
              f"topo-58 ({dict(Counter(t['topo'] for t in wall_any if t['topo'] != WALL_TOPO))}) "
              f"-- restricting PASS A to topo-58 ONLY: {len(wall)} tris")
    faces = connected_faces(wall)
    per_face = []
    for tl in faces:
        ys_all = [p[1] for ti in tl for p in wall[ti]["w"]]
        vs_all = [uv[1] for ti in tl for uv in wall[ti]["uv"]]
        us_all = [uv[0] for ti in tl for uv in wall[ti]["uv"]]
        lv = levels_of(vs_all)
        per_level = []
        for lvv in lv:
            ys = [p[1] for ti in tl for uv, p in zip(wall[ti]["uv"], wall[ti]["w"])
                  if abs(round(uv[1], 5) - lvv) <= JITTER]
            us = [uv[0] for ti in tl for uv in wall[ti]["uv"] if abs(round(uv[1], 5) - lvv) <= JITTER]
            per_level.append(dict(v=lvv, n=len(ys),
                                   y_min=round(min(ys), 3) if ys else None,
                                   y_max=round(max(ys), 3) if ys else None,
                                   u_min=round(min(us), 5) if us else None,
                                   u_max=round(max(us), 5) if us else None))
        per_face.append(dict(n_tris=len(tl), n_levels=len(lv), levels=lv,
                              face_y=[round(min(ys_all), 3), round(max(ys_all), 3)],
                              per_level=per_level))
    n_by_levelcount = Counter(f["n_levels"] for f in per_face)
    print(f"\n== PASS A / {fam}: shipped band u[{b[0]:.5f},{b[2]:.5f}] v[{b[1]:.5f},{b[3]:.5f}] "
          f"+-{EPS} =====")
    print(f"   {len(wall)} tris in {len(faces)} faces (topo histogram: {dict(topo_hist)})")
    print(f"   faces-by-level-count: {dict(sorted(n_by_levelcount.items()))}")
    results["passA"][fam] = dict(n_tris=len(wall), n_faces=len(faces), topo_hist=dict(topo_hist),
                                  faces_by_levelcount=dict(n_by_levelcount), faces=per_face)
    multi = [f for f in per_face if f["n_levels"] >= 3]
    if multi:
        print(f"   {len(multi)}/{len(faces)} faces ({len(multi)/len(faces):.0%}) show >=3 v-levels "
              f"-- deep dive:")
        for f in multi:
            lv = f["levels"]
            gaps = [round(lv[i + 1] - lv[i], 5) for i in range(len(lv) - 1)]
            gap_tiles = [round(g / TILE_V, 3) for g in gaps]
            print(f"      face n_tris={f['n_tris']} face_y={f['face_y']} levels={lv} "
                  f"gaps={gaps} (x TILE_V: {gap_tiles})")
            for pl in f["per_level"]:
                print(f"         level v={pl['v']}: n={pl['n']} y=[{pl['y_min']},{pl['y_max']}] "
                      f"u=[{pl['u_min']},{pl['u_max']}]")
    else:
        print("   0 faces with >=3 v-levels.")


# ---- PASS B: adjacency-only re-derivation + boundary-contamination flag -------------------------
def wall_adjacent(fam_topos):
    out = []
    for (bx, by), tris in census.items():
        edge_tris = defaultdict(list)
        for ti, t in enumerate(tris):
            ps = [kk(p) for p in t["w"]]
            for a, b2 in ((0, 1), (1, 2), (2, 0)):
                edge_tris[tuple(sorted((ps[a], ps[b2])))].append(ti)
        picked = set()
        for e, ts in edge_tris.items():
            tps = [tris[t]["topo"] for t in ts]
            if WALL_TOPO in tps and any(tp in fam_topos for tp in tps):
                for t in ts:
                    if tris[t]["topo"] == WALL_TOPO:
                        picked.add(t)
        for ti in picked:
            neigh = set()
            for a, b2 in ((0, 1), (1, 2), (2, 0)):
                ps = [kk(p) for p in tris[ti]["w"]]
                e = tuple(sorted((ps[a], ps[b2])))
                for t2 in edge_tris[e]:
                    if t2 != ti and tris[t2]["topo"] != WALL_TOPO:
                        neigh.add(tris[t2]["topo"])
            out.append(dict(blk=(bx, by), w=tris[ti]["w"], uv=tris[ti]["uv"], neigh=neigh))
    return out


for fam, topos in FAMS.items():
    picked = wall_adjacent(topos)
    fam_id = set(topos)
    mixed = [p for p in picked if p["neigh"] - fam_id - {WALL_TOPO}]
    b = shipped_band(fam)
    n_shipped_matching_adjacent = sum(1 for p in picked if all(in_band(uv, b) for uv in p["uv"]))
    print(f"\n== PASS B / {fam}: adjacency-only (no UV window presupposed): {len(picked)} tris "
          f"({len(mixed)} touch >1 family); {n_shipped_matching_adjacent}/{len(picked)} also land "
          f"inside the shipped band")
    if mixed:
        mixneigh = Counter(t for p in mixed for t in (p["neigh"] - fam_id - {WALL_TOPO}))
        print(f"   mixed-boundary neighbour topos: {dict(mixneigh.most_common(10))}")
    results["passB"][fam] = dict(n_adjacent=len(picked), n_mixed=len(mixed),
                                  n_inside_shipped_band=n_shipped_matching_adjacent)
    # ---- PASS C: row-band clustering on the CONTAMINATION-FREE adjacency population --------
    # (topo-58 strict by construction of wall_adjacent(); drop the boundary-mixed tris so a
    # neighbouring family's own wall band can't manufacture a spurious extra row here). This
    # is the population the shipped single (wall_du,wall_dv) window is TOO NARROW to fully
    # contain for canyon (PASS B showed only 19/43 land inside it) -- so PASS A undercounts
    # canyon's real wall geometry while PASS C sees all of it.
    clean = [p for p in picked if not (p["neigh"] - fam_id - {WALL_TOPO})]
    vs_all = [uv[1] for p in clean for uv in p["uv"]]
    rows = []
    for v in sorted(set(round(v, 5) for v in vs_all)):
        if rows and v - rows[-1][-1] <= JITTER:
            rows[-1].append(v)
        else:
            rows.append([v])
    row_bands = [(g[0], g[-1]) for g in rows]
    print(f"   PASS C / {fam}: {len(clean)} contamination-free topo-58 tris -> "
          f"{len(row_bands)} row band(s) {row_bands}")
    row_detail = []
    for lo, hi in row_bands:
        verts = [(uv[0], w[1]) for p in clean for uv, w in zip(p["uv"], p["w"])
                 if lo - 1e-6 <= round(uv[1], 5) <= hi + 1e-6]
        n_tris = sum(1 for p in clean if any(lo - 1e-6 <= round(uv[1], 5) <= hi + 1e-6 for uv in p["uv"]))
        ys = [y for (_, y) in verts]
        us = [u for (u, _) in verts]
        row_detail.append(dict(v_lo=lo, v_hi=hi, n_verts=len(verts), n_tris=n_tris,
                                y_min=round(min(ys), 3), y_max=round(max(ys), 3),
                                y_mean=round(float(np.mean(ys)), 3),
                                u_min=round(min(us), 5), u_max=round(max(us), 5)))
        print(f"      row v[{lo},{hi}]: {len(verts)} vertex-samples ({n_tris} tris touch it); "
              f"world Y [{row_detail[-1]['y_min']},{row_detail[-1]['y_max']}] "
              f"mean {row_detail[-1]['y_mean']}; u [{row_detail[-1]['u_min']},{row_detail[-1]['u_max']}]")
    if len(row_detail) >= 2:
        for i in range(len(row_detail) - 1):
            a, c = row_detail[i], row_detail[i + 1]
            center_gap = round(((a["v_lo"] + a["v_hi"]) / 2 - (c["v_lo"] + c["v_hi"]) / 2), 5)
            tile_mult = round(abs(center_gap) / TILE_V, 3)
            lo_ov = max(a["y_min"], c["y_min"])
            hi_ov = min(a["y_max"], c["y_max"])
            span = max(a["y_max"], c["y_max"]) - min(a["y_min"], c["y_min"])
            ov = max(0.0, hi_ov - lo_ov) / span if span > 0 else 1.0
            print(f"      row[{i}]<->row[{i+1}]: v-center gap {center_gap} = {tile_mult} x TILE_V; "
                  f"world-Y overlap {ov:.0%} {'(JITTER/SAME-course-like)' if ov > 0.4 else '(DISJOINT -- distinct physical bands)'}")
    results.setdefault("passC", {})[fam] = dict(n_clean=len(clean), row_bands=row_detail)

    # ---- PASS D: PER-PHYSICAL-FACE breakdown of the SAME `clean` population -----------------
    # PASS C pools tris map-wide before computing row-bands -- a "disjoint Y" read there could
    # just mean two SEPARATE wall segments (different blocks) happen to use different edges of
    # ONE row's range, not that any SINGLE contiguous wall face itself is 2-course. Re-run the
    # union-find connected-component split (the SAME method as PASS A) on `clean` and read each
    # PHYSICAL face's own v-levels + y-range -- the only test that can tell "2 courses stacked
    # on one wall" apart from "map-wide range pooled from unrelated single-course segments".
    dfaces = connected_faces(clean)
    d_multi = 0
    for tl in dfaces:
        vs_f = [uv[1] for ti in tl for uv in clean[ti]["uv"]]
        ys_f = [p[1] for ti in tl for p in clean[ti]["w"]]
        lv = levels_of(vs_f)
        if len(lv) >= 2:
            per_lv = []
            for lvv in lv:
                ys = [p[1] for ti in tl for uv, p in zip(clean[ti]["uv"], clean[ti]["w"])
                      if abs(round(uv[1], 5) - lvv) <= JITTER]
                per_lv.append((lvv, len(ys), round(min(ys), 3), round(max(ys), 3)))
            if fam == "canyon" or len(lv) >= 3:
                print(f"      PASS D face (n_tris={len(tl)}, blk={clean[tl[0]]['blk']}): "
                      f"levels={lv} face_y=[{round(min(ys_f),3)},{round(max(ys_f),3)}] "
                      f"per-level(v,n,ymin,ymax)={per_lv}")
            if len(lv) >= 2:
                d_multi += 1
    print(f"   PASS D / {fam}: {len(dfaces)} physical faces from the un-windowed adjacency set; "
          f"{d_multi} of them individually show >=2 v-levels")
    results["passC"][fam]["passD_n_faces"] = len(dfaces)
    results["passC"][fam]["passD_multilevel_faces"] = d_multi

# ---- VERDICT --------------------------------------------------------------------------------------
print("\n== VERDICT (canyon vs controls, PASS A canonical method) "
      "===========================================================")
for fam in FAMS:
    fb = results["passA"][fam]["faces_by_levelcount"]
    nf = results["passA"][fam]["n_faces"]
    ge3 = sum(n for lv, n in fb.items() if int(lv) >= 3)
    print(f"   {fam}: {nf} faces, >=3-level faces: {ge3} ({ge3/nf:.0%}); by-count {fb}")

canyon_multi = [f for f in results["passA"]["canyon"]["faces"] if f["n_levels"] >= 3]
canyon_total = results["passA"]["canyon"]["n_faces"]
print(f"\ncanyon: {len(canyon_multi)}/{canyon_total} faces ({len(canyon_multi)/canyon_total:.0%}) show "
      f">=3 v-levels -- {'HIGHEST of the 4 families' if len(canyon_multi)/canyon_total == max((sum(n for lv,n in results['passA'][f]['faces_by_levelcount'].items() if int(lv)>=3)/results['passA'][f]['n_faces']) for f in FAMS) else 'NOT the highest'}")
# does the extra level look like vertical repeat-tiling of ONE row (same u-range, gap ~ own
# row height / a TILE_V multiple) or a genuinely distinct course (different u-range)?
retile_like, distinct_like, thin = 0, 0, 0
for f in canyon_multi:
    lv = f["levels"]
    us = [(pl["u_min"], pl["u_max"]) for pl in f["per_level"]]
    same_u = all(abs(us[i][0] - us[0][0]) < 0.01 and abs(us[i][1] - us[0][1]) < 0.01 for i in range(len(us)))
    gaps = [lv[i + 1] - lv[i] for i in range(len(lv) - 1)]
    tile_locked = any(abs(g / TILE_V - round(g / TILE_V)) < 0.1 for g in gaps)
    ns = [pl["n"] for pl in f["per_level"]]
    if min(ns) <= 2:
        thin += 1
    elif same_u and tile_locked:
        retile_like += 1
    else:
        distinct_like += 1
print(f"of canyon's {len(canyon_multi)} multi-level faces: {retile_like} look like SAME-u "
      f"tile-locked vertical repeats of one row, {distinct_like} show a DIFFERENT u-range / "
      f"non-tile-locked gap (a genuinely distinct atlas position), {thin} are thin "
      f"(<=2 vertex samples on the extra level -- noise-candidate)")
results["verdict"] = dict(canyon_multi_faces=len(canyon_multi), canyon_total_faces=canyon_total,
                           retile_like=retile_like, distinct_like=distinct_like, thin=thin)

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(results, indent=1, default=str))
print(f"\n-> {OUT}")
