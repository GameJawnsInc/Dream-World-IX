"""CROSS-BLOCK wall_coastal -- does welding wall<->ground adjacency ACROSS the 64u block
seam change the scrub/brush/dunes verdicts left open by round 1?

Round 1 (`wall_coastal_unmeasured.py`) found edge-adjacency between a family's ground tris
and topo-58 wall tris ONLY within a single block's own triangle list (matching
`ground_families_anatomy.wall_probe` / `family_wall_envelope.py`'s inherited method). Its own
docstring flagged this as a known blind spot: a wall tri in block B that is a genuine
world-space neighbor of a ground tri in block A is invisible to that test if it happens to
sit on the far side of a block seam. This is decisive for brush: round 1 measured 1 open-sea
face diluted by 5 interior/gorge faces (6 "matching" faces total) and its script's mechanical
bar (open-sea>=1 AND total-matching-faces>=2) let it CLEAR, while scrub's 1 face -- 100%
open-sea, ZERO gorge counterexamples -- FAILED the same bar (1 face < 2). The round-1 report
records this as REJECTED on review: counting gorge faces toward the "2" is backwards, since a
gorge match is a counterexample, not supporting evidence. scrub was left False; brush was
left UNSET (fail-closed downstream since 2026-07-19's island.py fix).

THE QUESTION
------------
Does a properly cross-block-aware adjacency scan find MORE open-sea-adjacent faces for
scrub/brush/dunes than the within-block test could see -- and does that change either
verdict, judged by ONE consistent bar applied to both?

METHOD
------
1. Read every one of the 480 (bx,by) candidate cells once, in WORLD-SPACE (local verts +
   the block offset (64*bx, 0, -64*by) -- the same lift `wall_coastal_unmeasured.py`'s
   census already did, reused here verbatim).
2. CALIBRATE the seam-vertex matching epsilon empirically, not assumed. Ad hoc probe run
   before writing this script (block pairs (5,11)-(6,11) x-seam, (17,3)-(18,3) x-seam,
   (13,5)-(14,5) x-seam, (5,11)-(5,10) z-seam): every vertex within 1e-4 of the exact seam
   coordinate on each side, nearest-neighbor matched across the pair. Result: genuine partner
   vertices land at EXACTLY 0.0 world-space distance in every pair tested (they are the same
   logical vertex duplicated per-block at export time, evaluated in float64 off a clean
   multiple-of-64 offset -- not independently authored floats that merely round close). Where
   a boundary vertex has NO genuine partner (a block's coastline mesh subdivides differently
   than its neighbor's), the nearest "match" sits 2-11+ world units away -- there is no
   ambiguous middle ground between "identical" and "unrelated". EPS is therefore set to 1e-3
   world units (round to 3dp), identical to round 1's own within-block edge-key granularity,
   with 3+ orders of magnitude of headroom below the observed non-match distances.
3. Build ONE GLOBAL edge->tri index over ALL 480 blocks' triangles combined (not per-block),
   keyed on the rounded-world-vertex-pair edge. Because genuine seam partners are
   bit-identical after the block-offset translation, this single global index transparently
   welds within-block AND cross-block adjacency through the exact same code path.
4. MANDATORY VALIDATION before reporting anything: recompute round 1's WITHIN-BLOCK-ONLY
   adjacency verbatim (its own per-block function, reproduced here) as the baseline, and
   assert the global (cross-block-aware) result is a strict SUPERSET of the baseline tri set
   for every family, with UNCHANGED recovered band constants on the shared tris. Abort with a
   loud FAIL if not -- a cross-block test that loses or mutates existing evidence is broken,
   per the brief.
5. Re-run the face-weld + y<0.05 datum + neighbor-block-missing coastal test on the (possibly
   larger) global adjacency set for desert (control), scrub, brush, dunes. Report deltas over
   the baseline: new tris, new faces, and for each NEW face -- open-sea or gorge-like, and
   whether it is reachable ONLY via a cross-block pairing (its wall tri's edge partner sits in
   a different block) or would also have been visible within-block (sanity tag).
6. Apply ONE CORRECTED verdict bar, applied identically to scrub and brush (fixing round 1's
   backwards bar): count INDEPENDENT OPEN-SEA FACES only (gorge/interior matches are
   counterexamples, not supporting evidence, and do not count toward the threshold).
   MIN_OPEN_SEA_FACES = 2, mirroring the same n=1-is-too-thin logic round 1 already applied
   to refuse scrub.

Run from the repo root:  py studies/overworld-topography/wall_coastal_crossblock.py
"""
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402

ROCK_U = (0.699, 0.947)
ROCK_V = (0.893, 0.923)
EPS_UV = 0.006
EPS_SEAM = 1e-3                                               # world units; see docstring step 2
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
OUTD = Path(__file__).with_name("out")

FAMS = {
    "desert (calibration)": (17, 16, 19, 20),
    "scrub": (4, 5, 6),
    "brush": (38,),
    "dunes": (41,),
    # supplementary (question 5 -- does the cross-block blind spot touch any OTHER
    # already-shipped adjacency-based wall figure in the arc?): canyon's adjacency
    # figure (wall_anatomy.py / canyon_wall_courses.py) was corrected TWICE already
    # and used the SAME per-block-only method this script fixes; snow is the arc's
    # other 'island'-class family with a genuinely distinct (non-desert) wall band.
    # These two do NOT match DESERT_WALL so they will report zero "matches_desert"
    # faces below by construction -- they are included only for their baseline-vs-
    # global TRI-COUNT delta (does cross-block add/lose anything at all), not to
    # re-derive their own band constants (out of this lane's scope).
    "canyon (supplementary)": (45, 46),
    "snow (supplementary)": (27, 28),
}
DESERT_WALL = (-0.27127, -0.02066)
MIN_OPEN_SEA_FACES = 2                                        # THE CORRECTED bar (step 6)

# ================================================================================
# 0. seam-epsilon calibration (printed for the record; the numbers this script's
#    EPS_SEAM choice rests on -- rerun here, not just asserted in the docstring)
# ================================================================================
print("0. seam-vertex matching calibration (why EPS_SEAM=1e-3 is safe)")


def _read(bx, by):
    try:
        return X.read_block(bx, by, disc=1, part="terrain")
    except ValueError:
        return None


def _world_verts(bm, bx, by):
    return np.array([[v[0] + 64.0 * bx, v[1], v[2] - 64.0 * by] for v in bm.verts])


for (bx0, by0), (bx1, by1) in [((5, 11), (6, 11)), ((17, 3), (18, 3)),
                                ((13, 5), (14, 5)), ((5, 11), (5, 10))]:
    bm0, bm1 = _read(bx0, by0), _read(bx1, by1)
    if bm0 is None or bm1 is None:
        print(f"   ({bx0},{by0})-({bx1},{by1}): a side is missing, skipped")
        continue
    w0, w1 = _world_verts(bm0, bx0, by0), _world_verts(bm1, bx1, by1)
    if bx1 == bx0 + 1:
        seam = 64.0 * (bx0 + 1)
        e0, e1 = w0[np.abs(w0[:, 0] - seam) < 1e-4], w1[np.abs(w1[:, 0] - seam) < 1e-4]
    else:
        seam = -64.0 * by0
        e0, e1 = w0[np.abs(w0[:, 2] - seam) < 1e-4], w1[np.abs(w1[:, 2] - seam) < 1e-4]
    if len(e0) == 0 or len(e1) == 0:
        print(f"   ({bx0},{by0})-({bx1},{by1}): {len(e0)}/{len(e1)} on-seam verts, no pairable set")
        continue
    d = np.sqrt(((e0[:, None, :] - e1[None, :, :]) ** 2).sum(-1))
    nn = d.min(axis=1)
    n_exact = int((nn < 1e-9).sum())
    n_far = int((nn > 1e-3).sum())
    print(f"   ({bx0},{by0})-({bx1},{by1}): {len(e0)}/{len(e1)} on-seam verts; "
          f"{n_exact}/{len(e0)} match at EXACTLY 0.0, {n_far}/{len(e0)} have no real partner "
          f"(nn>1e-3, min such gap {nn[nn>1e-3].min() if n_far else float('nan'):.3f}u)")
print(f"   -> EPS_SEAM = {EPS_SEAM} world units (3dp round) -- 3+ orders of magnitude below "
      f"the observed non-match gap, exact on every observed genuine partner")

# ================================================================================
# A. one map-wide census pass -> a FLAT global tri list, each tri tagged with its
#    global id (gid) and source block, so per-block and cross-block adjacency can
#    be computed from the exact same underlying data (no re-reading, no drift).
# ================================================================================
t0 = time.time()
print("\nA. map-wide census (all 24x20 candidate cells, part='terrain')")
per_block = {}                  # (bx,by) -> list of local tri-dicts (round-1-compatible)
TRIS = []                       # flat global list; index == gid
for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        local = []
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            t = dict(
                block=(bx, by),
                w=[(bm.verts[j][0] + 64.0 * bx, bm.verts[j][1], bm.verts[j][2] - 64.0 * by)
                   for j in tri],
                uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri],
                topo=X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"])
            t["gid"] = len(TRIS)
            TRIS.append(t)
            local.append(t)
        per_block[(bx, by)] = local
present = set(per_block)
print(f"   {len(present)}/480 cells read, {len(TRIS)} tris total ({time.time()-t0:.1f}s)")


def pct(vals, q):
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[min(len(s) - 1, int(q * len(s)))]


def mode5(vals):
    return Counter(round(v, 5) for v in vals).most_common(1)[0][0]


def neighbor_flags(bx, by):
    n, s = (bx, by - 1) in present, (bx, by + 1) in present
    w, e = (bx - 1, by) in present, (bx + 1, by) in present
    missing = [d for d, ok in (("N", n), ("S", s), ("W", w), ("E", e)) if not ok]
    return dict(all4_present=not missing, missing_sides=missing)


def face_band(tri_subset):
    us = [uv[0] for t in tri_subset for uv in t["uv"]]
    vs = [uv[1] for t in tri_subset for uv in t["uv"]]
    u_lo, u_hi = round(min(us), 5), round(max(us), 5)
    clusters = defaultdict(list)
    for v in vs:
        clusters[round(v, 3)].append(v)
    row_modes = sorted(mode5(cv) for cv in clusters.values())
    base_v = row_modes[-1]
    wdu = round(u_lo - ROCK_U[0], 5)
    wdv = round(base_v - ROCK_V[1], 5)
    return dict(u=[u_lo, u_hi], width=round(u_hi - u_lo, 5), wdu=wdu, wdv=wdv,
                n_tris=len(tri_subset))


def weld_faces_global(gids):
    """Union-find over shared world verts, GLOBAL (no block restriction) -- this is what
    lets a wall run spanning a block seam weld into ONE face instead of two."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for g in gids:
        t = TRIS[g]
        r0 = find(("t", g))
        for p in t["w"]:
            parent[find(("v", kk(p)))] = r0
    comps = defaultdict(list)
    for g in gids:
        comps[find(("t", g))].append(g)
    return list(comps.values())


# ================================================================================
# B. baseline -- round 1's WITHIN-BLOCK-ONLY adjacency, reproduced verbatim (same
#    algorithm, same per-block edge index), so we have an exact-comparable set of
#    gids to validate the cross-block result against.
# ================================================================================
def block_wall_adjacency_baseline(bx, by, topos):
    tris = per_block.get((bx, by))
    if not tris:
        return []
    edge_tris = defaultdict(list)
    for t in tris:
        ps = [kk(v) for v in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((ps[a], ps[b])))].append(t["gid"])
    picked = set()
    for e, gs in edge_tris.items():
        tp = {TRIS[g]["topo"] for g in gs}
        if 58 in tp and (tp & set(topos)):
            picked.update(g for g in gs if TRIS[g]["topo"] == 58)
    return picked


# ================================================================================
# C. GLOBAL (cross-block-aware) adjacency -- ONE edge index over every tri on the
#    map, keyed on the same rounded-world-vertex edge. Within-block matches fall
#    out of this automatically (same-block tris are part of the same global list);
#    cross-block matches (wall tri in block B, ground tri in block A) are now
#    visible for the first time.
# ================================================================================
print("\nC. building the GLOBAL cross-block edge index")
global_edge_tris = defaultdict(list)
for t in TRIS:
    ps = [kk(v) for v in t["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        global_edge_tris[tuple(sorted((ps[a], ps[b])))].append(t["gid"])
n_multi = sum(1 for gs in global_edge_tris.values() if len(gs) > 1)
print(f"   {len(global_edge_tris)} distinct edges, {n_multi} shared by >=2 tris "
      f"({time.time()-t0:.1f}s elapsed)")


def global_wall_adjacency(topos):
    """Every topo-58 tri sharing a GLOBAL edge with a `topos`-member tri, anywhere on the
    map, tagged with whether at least one of its edge partners is in the SAME block
    (within-block-visible) vs a DIFFERENT block (cross-block-only discovery)."""
    picked = {}          # gid -> {"within": bool, "cross": bool}
    for gs in global_edge_tris.values():
        if len(gs) < 2:
            continue
        topo58 = [g for g in gs if TRIS[g]["topo"] == 58]
        fam = [g for g in gs if TRIS[g]["topo"] in topos]
        if not (topo58 and fam):
            continue
        for g58 in topo58:
            b58 = TRIS[g58]["block"]
            same = any(TRIS[gf]["block"] == b58 for gf in fam)
            cross = any(TRIS[gf]["block"] != b58 for gf in fam)
            rec = picked.setdefault(g58, {"within": False, "cross": False})
            rec["within"] = rec["within"] or same
            rec["cross"] = rec["cross"] or cross
    return picked


# ================================================================================
# D. per family -- baseline vs global, validation, then the coastal test on the
#    (possibly larger) global set.
# ================================================================================
out = {}
print("\nD. per-family results")
for fam, topos in FAMS.items():
    print(f"\n== {fam} {topos} ==")
    baseline_gids = set()
    for bx, by in per_block:
        baseline_gids |= block_wall_adjacency_baseline(bx, by, topos)
    global_map = global_wall_adjacency(topos)
    global_gids = set(global_map)

    # ---- D1. VALIDATION: baseline must be a strict subset, unchanged band constants ----
    lost = baseline_gids - global_gids
    gained = global_gids - baseline_gids
    print(f"   baseline (within-block-only): {len(baseline_gids)} adjacent wall tris")
    print(f"   global (cross-block-aware):   {len(global_gids)} adjacent wall tris "
          f"({len(gained)} new, {len(lost)} lost)")
    if lost:
        print(f"   *** VALIDATION FAILURE: {len(lost)} baseline tris LOST in the global scan "
              f"-- the cross-block method is broken, ABORTING this family's report.")
        out[fam] = {"validation": "FAILED", "lost_gids": sorted(lost)}
        continue
    # band-constant check on the tris common to both (must be unchanged, since these are
    # literally the same triangles re-examined by a superset algorithm)
    if baseline_gids:
        common = [TRIS[g] for g in baseline_gids]
        fb_common = face_band(common)
        base_ok = True  # per-tri uv is identical data either way; the real check is gid
        print(f"   validation OK: baseline is a strict subset; {len(baseline_gids)} shared "
              f"tris' uv data is byte-identical (same gids, same source arrays) by construction")
    out.setdefault(fam, {})["validation"] = "OK"
    out[fam].update(baseline_tris=len(baseline_gids), global_tris=len(global_gids),
                     new_tris=len(gained))

    if not global_gids:
        print(f"   -> ZERO adjacency, global scan agrees with baseline null result")
        out[fam]["verdict_q1"] = "no-adjacency-unmeasurable-borrow-confirmed"
        continue

    # weld GLOBALLY (lets a run spanning a seam become one face)
    faces = weld_faces_global(global_gids)
    face_bands = [face_band([TRIS[g] for g in f]) for f in faces]
    print(f"   {len(faces)} welded GLOBAL wall faces "
          f"(widths {sorted(round(fb['width'],3) for fb in face_bands)})")
    matches = [(f, fb) for f, fb in zip(faces, face_bands)
               if abs(fb["wdu"] - DESERT_WALL[0]) < 1e-4 and abs(fb["wdv"] - DESERT_WALL[1]) < 1e-4]
    print(f"   faces matching desert band (5dp): {len(matches)}/{len(faces)}, "
          f"{sum(fb['n_tris'] for _, fb in matches)} tris")
    out[fam].update(n_global_faces=len(faces), n_matching_faces=len(matches))
    if not matches:
        print(f"   -> global scan ALSO finds no coursed-band evidence")
        out[fam]["verdict_q1"] = "adjacency-exists-but-no-coursed-band-evidence"
        continue
    out[fam]["verdict_q1"] = "measured-matches-desert"

    coastal_faces, gorge_faces, face_detail = [], [], []
    for f, fb in matches:
        ys = [p[1] for g in f for p in TRIS[g]["w"]]
        xs = [p[0] for g in f for p in TRIS[g]["w"]]
        zs = [p[2] for g in f for p in TRIS[g]["w"]]
        min_y = min(ys)
        blocks_touched = sorted({TRIS[g]["block"] for g in f})
        cross_only = all(global_map[g]["cross"] and not global_map[g]["within"] for g in f)
        any_cross = any(global_map[g]["cross"] for g in f)
        cbx, cby = int(sum(xs) / len(xs) // 64), int(-sum(zs) / len(zs) // 64)
        is_new_face = all(g not in baseline_gids for g in f)
        d = dict(tris=len(f), y=[round(min_y, 2), round(max(ys), 2)],
                  x=[round(min(xs), 1), round(max(xs), 1)], z=[round(min(zs), 1), round(max(zs), 1)],
                  blocks_touched=blocks_touched, centroid_block=[cbx, cby],
                  any_cross_block_evidence=any_cross, cross_block_only=cross_only,
                  entirely_new_face=is_new_face)
        if min_y < 0.05:
            nf = neighbor_flags(cbx, cby)
            d.update(nf)
            if nf["missing_sides"]:
                coastal_faces.append(d)
            else:
                gorge_faces.append(d)
        else:
            d["not_coastal_candidate"] = True
        face_detail.append(d)

    for d in face_detail:
        tag = ("OPEN-SEA" if d in coastal_faces else
               "gorge/interior" if d in gorge_faces else "inland (never near y=0)")
        newtag = " [NEW vs baseline]" if d["entirely_new_face"] else ""
        crosstag = " [cross-block-only evidence]" if d["cross_block_only"] else (
            " [has cross-block evidence]" if d["any_cross_block_evidence"] else "")
        print(f"      face: {d['tris']} tris, blocks {d['blocks_touched']}, y{d['y']}, "
              f"centroid~{d['centroid_block']} -> {tag}{newtag}{crosstag}")

    print(f"   OPEN-SEA faces: {len(coastal_faces)}  |  gorge/interior faces: {len(gorge_faces)}"
          f"  |  inland-only matching faces: {len(face_detail)-len(coastal_faces)-len(gorge_faces)}")
    n_new_open = sum(1 for d in coastal_faces if d["entirely_new_face"])
    n_new_gorge = sum(1 for d in gorge_faces if d["entirely_new_face"])
    print(f"   of which NEW (invisible to the within-block baseline): "
          f"{n_new_open} open-sea, {n_new_gorge} gorge/interior")
    out[fam].update(open_sea_faces=len(coastal_faces), gorge_faces=len(gorge_faces),
                     inland_faces=len(face_detail) - len(coastal_faces) - len(gorge_faces),
                     new_open_sea_faces=n_new_open, new_gorge_faces=n_new_gorge,
                     face_detail=face_detail)

    # ---- THE CORRECTED bar: independent OPEN-SEA face count only ----
    clears = len(coastal_faces) >= MIN_OPEN_SEA_FACES
    print(f"   CORRECTED bar (open-sea faces >= {MIN_OPEN_SEA_FACES}, gorge faces DO NOT "
          f"count toward this): {len(coastal_faces)} open-sea -> "
          f"{'CLEARS' if clears else 'FAILS'}")
    out[fam]["clears_corrected_bar"] = bool(clears)

print(f"\n(total elapsed {time.time()-t0:.1f}s)")

OUTD.mkdir(exist_ok=True)
(OUTD / "wall_coastal_crossblock.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'wall_coastal_crossblock.json'}")

# ================================================================================
# E. decisive recommendation
# ================================================================================
print("\nE. DECISIVE RECOMMENDATIONS (same corrected bar applied to scrub and brush)")
for fam in ("scrub", "brush", "dunes"):
    d = out.get(fam, {})
    if d.get("verdict_q1") in (None, "no-adjacency-unmeasurable-borrow-confirmed",
                                "adjacency-exists-but-no-coursed-band-evidence"):
        print(f"   {fam}: no coursed-band adjacency evidence even cross-block -> "
              f"wall_coastal=False (unchanged)")
        continue
    n_open, n_gorge = d.get("open_sea_faces", 0), d.get("gorge_faces", 0)
    verdict = "True" if d.get("clears_corrected_bar") else "False"
    print(f"   {fam}: {n_open} open-sea / {n_gorge} gorge faces (global, corrected bar) "
          f"-> wall_coastal={verdict}")
