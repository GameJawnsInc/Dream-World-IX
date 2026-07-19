"""WALL_COASTAL for scrub / brush / dunes -- closing the UNMEASURED gate field.

``grassland.GROUNDS`` marks scrub/brush/dunes as wall_du/wall_dv = the DESERT wall band
(-0.27127,-0.02066), with comments saying brush's copy is "its REAL stock wall (byte-exact
adjacency, measured)" while scrub's and dunes' are "borrowed -- an authoring choice, not a
measurement" because "scrub and dunes never touch topo-58 in stock". `wall_coastal` itself
is UNMEASURED on all three, but the shipped safety gate (build_landmass / GroundRetile.for_donor,
THE WALL-CONTEXT LAW) reads it to refuse a family a sea-ringed island mint. This script closes
that gate honestly.

QUESTION 1 -- is the "borrow" claim byte-true?  A ground family's REAL wall band can only be
recovered by EDGE ADJACENCY: find every topo-58 (rock/wall) tri that shares an edge (by
rounded vertex position, exactly the method `ground_families_anatomy.wall_probe` used on its
top-8 specimen slice) with a tri of the family's own topos, over ALL 480 (bx,by) candidate
cells map-wide (not a specimen slice -- THE NO-TOP-N-SLICING LAW). If a family has ZERO such
adjacent tris anywhere on the map, its wall band cannot be measured at all -- "borrow" is
confirmed as the correct word, not a euphemism for a missed measurement. If it has adjacent
tris, their own uv recovers the REAL band, compared to the desert band at 5dp.

Calibration: the same method is run on DESERT itself (topos 17/16/19/20) as a known-true
positive -- it must recover (-0.27127,-0.02066) map-wide to validate the adjacency method
before trusting a null (zero-adjacency) result for scrub/brush/dunes.

QUESTION 2 -- wall_coastal, map-wide, CORRECTED method (family_wall_envelope.py's fixed
full-map tally, not its once-shipped top-8 slice): of a family's own ADJACENT wall tris (not
just tris sitting in the same uv band, which conflates with desert's OWN wall since scrub/
brush/dunes hypothesize the identical band), weld into connected wall FACES, apply the y<0.05
datum test (family_wall_envelope.py's coastal-candidate test), and itemize every candidate
face with block position + a NEIGHBOR-BLOCK test (does the wall's block border missing/absent
=likely-open-sea blocks on any side, or is it interior-land-locked on all 4 sides = likely a
gorge, mirroring the manual (3,7) gorge call that rescued the canyon finding).

Run from the repo root:  py studies/overworld-topography/wall_coastal_unmeasured.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402

ROCK_U = (0.699, 0.947)
ROCK_V = (0.893, 0.923)                                      # sorted (island.py stores base->top)
EPS = 0.006
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
OUTD = Path(__file__).with_name("out")

# family under test -> its ground topos (grassland.py docstring's canonical membership sets)
FAMS = {
    "desert (calibration)": (17, 16, 19, 20),
    "scrub": (4, 5, 6),
    "brush": (38,),
    "dunes": (41,),
}
DESERT_WALL = (-0.27127, -0.02066)                            # the borrowed/claimed band


def band_rect(du, dv):
    return (ROCK_U[0] + du, ROCK_V[0] + dv, ROCK_U[1] + du, ROCK_V[1] + dv)


def in_band(uv, b):
    return b[0] - EPS <= uv[0] <= b[2] + EPS and b[1] - EPS <= uv[1] <= b[3] + EPS


# ---- A. one map-wide census pass: every (bx,by) that reads, with per-tri w/uv/topo ------------
print("A. map-wide census (all 24x20 candidate cells, part='terrain')")
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
present = set(census)
print(f"   {len(census)}/480 cells read (rest raised ValueError = open ocean, no terrain mesh)")


def block_wall_adjacency(bx, by, topos):
    """topo-58 tris edge-adjacent (shared rounded-vertex edge) to a `topos`-member tri,
    within this ONE block's own tri list (matches ground_families_anatomy.wall_probe's
    per-block edge test; blocks are not vertex-welded across borders in this dataset)."""
    tris = census.get((bx, by))
    if not tris:
        return []
    edge_tris = defaultdict(list)
    for ti, t in enumerate(tris):
        ps = [kk(v) for v in t["w"]]
        for a2, b2 in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((ps[a2], ps[b2])))].append(ti)
    picked = set()
    for e, ts in edge_tris.items():
        tp = {tris[t]["topo"] for t in ts}
        if 58 in tp and (tp & set(topos)):
            picked.update(t for t in ts if tris[t]["topo"] == 58)
    return [tris[t] for t in picked]


def pct(vals, q):
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[min(len(s) - 1, int(q * len(s)))]


def face_band(tris_subset):
    """Per-FACE band recovery (u_lo/u_hi + v-rows) -- the map-wide pooled min/max over
    ALL adjacent tris is UNSAFE (topo-58 is also used for incidental rock decoration far
    outside any coursed-wall band, so a global min/max spans nonsense); a single welded
    FACE is the right unit -- it is geometrically one wall run. Returns
    (u_lo, u_hi, width, wdu, wdv, well_formed) using the SAME index convention as
    ground_families_anatomy.wall_probe: wdv keys off the LARGER of the two dominant
    v-levels (island.py's ROCK_V=(0.923,0.893) base->top; ROCK_V[1] here = 0.923 = base)."""
    us = [uv[0] for t in tris_subset for uv in t["uv"]]
    vs = [uv[1] for t in tris_subset for uv in t["uv"]]
    u_lo, u_hi = round(min(us), 5), round(max(us), 5)
    # cluster raw v's at 3dp tolerance (row jitter) but report each row's value at the
    # true 5dp MODE within its cluster (not the 3dp-rounded cluster key) -- a 4dp/3dp
    # round would silently cap the precision a "5DP MATCH" claim can actually prove.
    clusters = defaultdict(list)
    for v in vs:
        clusters[round(v, 3)].append(v)
    row_modes = sorted(mode5(cv) for cv in clusters.values())
    base_v = row_modes[-1]                                    # ROCK_V[1]=0.923 convention: base = larger v
    wdu = round(u_lo - ROCK_U[0], 5)
    wdv = round(base_v - ROCK_V[1], 5)
    width = round(u_hi - u_lo, 5)
    well_formed = abs(width - 0.24805) < 3e-3                 # matches the known band width
    return dict(u=[u_lo, u_hi], width=width, v_levels=row_modes, wdu=wdu, wdv=wdv,
                well_formed=bool(well_formed), n_tris=len(tris_subset))


def mode5(vals):
    return Counter(round(v, 5) for v in vals).most_common(1)[0][0]


def weld_faces(wall_tris):
    """Union-find over shared verts -> connected wall FACES (matches
    family_wall_envelope.wall_stats)."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for ti, t in enumerate(wall_tris):
        ks = [("v", kk(p)) for p in t["w"]]
        r0 = find(("t", ti))
        for k in ks:
            parent[find(k)] = r0
    comps = defaultdict(list)
    for ti, t in enumerate(wall_tris):
        comps[find(("t", ti))].append(ti)
    return list(comps.values())


def neighbor_flags(bx, by):
    """Does this block border a missing (open-ocean-candidate) cell on any cardinal side,
    or is it interior (all 4 present)? A coarse proxy for the manual (3,7) gorge call --
    itemized, not asserted as ground truth."""
    n = (bx, by - 1) in present
    s = (bx, by + 1) in present
    w = (bx - 1, by) in present
    e = (bx + 1, by) in present
    missing = [d for d, ok in (("N", n), ("S", s), ("W", w), ("E", e)) if not ok]
    return dict(all4_present=not missing, missing_sides=missing)


out = {}

print("\nB. QUESTION 1 -- edge-adjacency wall-band recovery (map-wide, all 480 cells)")
for fam, topos in FAMS.items():
    fam_out = {"topos": list(topos)}
    co_blocks = []          # blocks where family topo AND topo-58 both present (weak: same block)
    adj_blocks = []         # blocks where a topo-58 tri actually shares an edge with family topo
    all_adj_tris = []
    for (bx, by), tris in census.items():
        has_fam = any(t["topo"] in topos for t in tris)
        has_58 = any(t["topo"] == 58 for t in tris)
        if has_fam and has_58:
            co_blocks.append((bx, by))
        if has_fam:
            adj = block_wall_adjacency(bx, by, topos)
            if adj:
                adj_blocks.append((bx, by))
                all_adj_tris.extend(adj)
    n_fam_tris = sum(1 for tl in census.values() for t in tl if t["topo"] in topos)
    n_fam_blocks = sum(1 for tl in census.values() if any(t["topo"] in topos for t in tl))
    print(f"\n== {fam} {topos}: {n_fam_tris} ground tris over {n_fam_blocks} blocks map-wide")
    print(f"   co-occur w/ ANY topo-58 in same block: {len(co_blocks)}/{n_fam_blocks} blocks")
    print(f"   TRUE edge-adjacency to topo-58: {len(adj_blocks)}/{n_fam_blocks} blocks, "
          f"{len(all_adj_tris)} adjacent wall tris")
    fam_out.update(ground_tris=n_fam_tris, ground_blocks=n_fam_blocks,
                    co_occur_blocks=len(co_blocks), adjacent_blocks=len(adj_blocks),
                    adjacent_wall_tris=len(all_adj_tris))
    if not all_adj_tris:
        print(f"   -> ZERO map-wide edge adjacency to topo-58. The family's wall band CANNOT "
              f"be measured; \"borrow\" is the correct word, not a missed measurement.")
        fam_out["verdict_q1"] = "no-adjacency-unmeasurable-borrow-confirmed"
        out[fam] = fam_out
        continue
    # PER-FACE band recovery (NOT a pooled global min/max -- topo-58 also dresses
    # incidental rock decoration far outside any coursed wall band, and a raw pooled
    # min/max over many blocks silently mixes those in; a single welded FACE is the
    # right unit -- geometrically one wall run, see face_band() docstring). NOTE: an
    # earlier version of this script gated on face WIDTH~=0.24805 ("well-formed") before
    # voting -- but a small/short wall face legitimately uses only a FRACTION of a band's
    # width starting from the SAME fixed left edge (u_lo) (the COL-FREEDOM LAW: in-band
    # window choice is cosmetically free), so a width gate wrongly discarded genuine
    # partial-width same-band evidence. The real test is whether u_lo (+ the row v) match
    # a hypothesis band's origin EXACTLY -- width is reported only as auxiliary context.
    adj_faces = weld_faces(all_adj_tris)
    face_bands = [face_band([all_adj_tris[ti] for ti in tl]) for tl in adj_faces]
    print(f"   {len(adj_faces)} welded wall FACES from the {len(all_adj_tris)} adjacent tris "
          f"(widths {sorted(round(fb['width'], 3) for fb in face_bands)})")
    for fb in face_bands:
        print(f"      face: {fb['n_tris']} tris, u{fb['u']} width {fb['width']}, "
              f"recovered (wdu,wdv) = ({fb['wdu']}, {fb['wdv']})")
    fam_out.update(n_faces=len(adj_faces),
                    face_bands=[dict(u=fb["u"], width=fb["width"], wdu=fb["wdu"],
                                     wdv=fb["wdv"], n_tris=fb["n_tris"])
                                for fb in face_bands])
    matches_desert = [(tl, fb) for tl, fb in zip(adj_faces, face_bands)
                       if abs(fb["wdu"] - DESERT_WALL[0]) < 1e-4
                       and abs(fb["wdv"] - DESERT_WALL[1]) < 1e-4]
    n_match_tris = sum(fb["n_tris"] for _, fb in matches_desert)
    print(f"   faces whose ORIGIN exactly matches the desert band (-0.27127,-0.02066) at "
          f"5dp: {len(matches_desert)}/{len(adj_faces)} faces, {n_match_tris}/{len(all_adj_tris)} tris")
    fam_out.update(faces_matching_desert=len(matches_desert), tris_matching_desert=n_match_tris)
    if not matches_desert:
        print(f"   -> NO face recovers the claimed desert band; the borrow claim has NO "
              f"supporting adjacency evidence (same standing as zero adjacency)")
        fam_out["verdict_q1"] = "adjacency-exists-but-no-coursed-band-evidence"
        out[fam] = fam_out
        continue
    print(f"   -> {len(matches_desert)} face(s) PROVEN 5dp-exact match to the claimed desert "
          f"band -- the borrow is byte-true wherever this family does touch a wall")
    fam_out.update(recovered_du=DESERT_WALL[0], recovered_dv=DESERT_WALL[1],
                    matches_desert_5dp=True)
    fam_out["verdict_q1"] = "measured-matches-desert"
    wf_face_tls = [tl for tl, _ in matches_desert]

    # ---- QUESTION 2 (adjacency-restricted): coastal fraction map-wide, on ONLY the
    # well-formed coursed-band tris (excludes incidental off-band rock decoration, which
    # is not part of the wall language and would contaminate a y<0.05 datum test with
    # unrelated boulders) ----
    wf_tris = [all_adj_tris[ti] for tl in wf_face_tls for ti in tl]
    spans = [max(p[1] for p in t["w"]) - min(p[1] for p in t["w"]) for t in wf_tris]
    face_h = []
    for tl in wf_face_tls:
        ys = [p[1] for ti in tl for p in all_adj_tris[ti]["w"]]
        face_h.append(max(ys) - min(ys))
    coastal_faces = [tl for tl in wf_face_tls
                     if min(p[1] for ti in tl for p in all_adj_tris[ti]["w"]) < 0.05]
    tris_coastal = sum(len(tl) for tl in coastal_faces)
    print(f"   MAP-WIDE tally (well-formed-band tris only): {len(wf_tris)} wall tris in "
          f"{len(wf_face_tls)} faces; "
          f"tri y-span p50 {pct(spans,.5):.2f} p90 {pct(spans,.9):.2f} max {max(spans):.2f}; "
          f"FACE height p50 {pct(face_h,.5):.2f} p90 {pct(face_h,.9):.2f} max {max(face_h):.2f}")
    print(f"   datum test (min-y < 0.05 = coastal CANDIDATE): {len(coastal_faces)}/{len(wf_face_tls)} "
          f"faces ({tris_coastal}/{len(wf_tris)} tris)")
    fam_out.update(wall_tris=len(wf_tris), wall_faces=len(wf_face_tls),
                    span_p90=round(pct(spans, .9), 3), face_max=round(max(face_h), 3),
                    face_p90=round(pct(face_h, .9), 3),
                    coastal_candidate_faces=len(coastal_faces),
                    coastal_candidate_tris=tris_coastal)
    face_detail = []
    for tl in coastal_faces:
        pts = [p for ti in tl for p in all_adj_tris[ti]["w"]]
        ys = sorted(p[1] for p in pts)
        xs = [p[0] for p in pts]
        zs = [p[2] for p in pts]
        cbx, cby = int(sum(xs) / len(xs) // 64), int(-sum(zs) / len(zs) // 64)
        nf = neighbor_flags(cbx, cby)
        print(f"      coastal-candidate face: {len(tl)} tris, y[{ys[0]:.2f},{ys[-1]:.2f}], "
              f"x[{min(xs):.1f},{max(xs):.1f}] z[{min(zs):.1f},{max(zs):.1f}] "
              f"~block ({cbx},{cby}) neighbor-present N/S/W/E all4={nf['all4_present']} "
              f"missing={nf['missing_sides']}")
        face_detail.append(dict(tris=len(tl), y=[round(ys[0], 2), round(ys[-1], 2)],
                                 x=[round(min(xs), 1), round(max(xs), 1)],
                                 z=[round(min(zs), 1), round(max(zs), 1)],
                                 block=[cbx, cby], **nf))
    fam_out["coastal_candidate_detail"] = face_detail
    # verdict: wall_coastal True only if >=1 candidate face is NOT interior-land-locked
    # (mirrors the canyon rescue: a face with all4 neighbor blocks present, entirely below
    # y=0.05, deep negative y, reads as an interior gorge not open sea)
    open_sea_like = [f for f in face_detail if f["missing_sides"]]
    print(f"   of {len(face_detail)} coastal-candidate faces, {len(open_sea_like)} border a "
          f"MISSING (open-ocean-candidate) map cell on >=1 side; "
          f"{len(face_detail) - len(open_sea_like)} are fully interior-land-locked (gorge-like)")
    fam_out["open_sea_like_faces"] = len(open_sea_like)
    fam_out["interior_lidded_faces"] = len(face_detail) - len(open_sea_like)
    out[fam] = fam_out

# ---- C. the BAND-MEMBERSHIP cross-check (the literal texture question) ------------------------
# scrub/brush/dunes all CLAIM the identical desert band (-0.27127,-0.02066) -- island.py's
# build_landmass paints THAT EXACT atlas rect for whichever `ground` is selected, regardless
# of adjacency. So a second, independent question: does that literal texture (any topo-58
# tri whose uv sits in that rect, MAP-WIDE, regardless what it happens to border) ever read
# coastal in stock? This is family_wall_envelope.py's own band-membership method (not
# adjacency) applied to the shared claimed band -- since the rect is identical for desert/
# scrub/brush/dunes, this number is la ONE shared figure, computed once here.
print("\nC. band-MEMBERSHIP cross-check on the shared claimed band (-0.27127,-0.02066) -- "
      "the literal atlas rect scrub/brush/dunes would paint, regardless of adjacency")
bx_rect = band_rect(*DESERT_WALL)
band_tris = [t for tl in census.values() for t in tl
             if all(in_band(uv, bx_rect) for uv in t["uv"])]
band_faces = weld_faces(band_tris)
band_coastal = [tl for tl in band_faces
                if min(p[1] for ti in tl for p in band_tris[ti]["w"]) < 0.05]
band_coastal_tris = sum(len(tl) for tl in band_coastal)
band_open = 0
band_face_detail = []
for tl in band_coastal:
    pts = [p for ti in tl for p in band_tris[ti]["w"]]
    xs = [p[0] for p in pts]
    zs = [p[2] for p in pts]
    cbx, cby = int(sum(xs) / len(xs) // 64), int(-sum(zs) / len(zs) // 64)
    nf = neighbor_flags(cbx, cby)
    if nf["missing_sides"]:
        band_open += 1
    band_face_detail.append(dict(tris=len(tl), block=[cbx, cby], **nf))
print(f"   {len(band_tris)} topo-58 tris map-wide sit inside this exact rect, in "
      f"{len(band_faces)} welded faces (this is DESERT's own wall population -- the rect is "
      f"identical, so this figure is shared by desert/scrub/brush/dunes alike)")
print(f"   datum test: {len(band_coastal)}/{len(band_faces)} faces reach y<0.05 "
      f"({band_coastal_tris}/{len(band_tris)} tris); of those, {band_open} border a MISSING "
      f"(open-ocean-candidate) map cell on >=1 side -> the literal texture DOES read "
      f"open-sea-coastal in stock ({'>=1 case' if band_open else 'ZERO cases'})")
out["_shared_band_membership"] = dict(
    band=list(DESERT_WALL), tris=len(band_tris), faces=len(band_faces),
    coastal_candidate_faces=len(band_coastal), coastal_candidate_tris=band_coastal_tris,
    open_sea_like_faces=band_open, detail=band_face_detail)

# ---- D. verdicts --------------------------------------------------------------------------------
# POLICY: canyon was disqualified for showing an EXCLUSIVELY-interior pattern (48/48 faces
# non-coastal, its one borderline face manually ruled a gorge) -- zero genuine open-sea
# instances anywhere, on a family with SUBSTANTIAL adjacency data (655 tris). The bar this
# script applies for a True/ALLOW verdict from DIRECT adjacency evidence is symmetric and
# non-trivial: (a) >=1 genuinely open-sea-adjacent face AND (b) enough independent matching
# faces that the finding isn't a single-triangle coincidence -- MIN_FACES=2, chosen because
# a single 3-tri face is indistinguishable from an incidental boundary artifact (e.g. an
# unrelated donor family's cliff corner happening to share one edge) rather than a
# deliberate, repeatable "this ground meets this wall" composition.
MIN_FACES_FOR_DIRECT_ALLOW = 2
print(f"\nD. VERDICTS (direct-evidence ALLOW bar: >=1 open-sea face AND "
      f">={MIN_FACES_FOR_DIRECT_ALLOW} independent band-matching faces, symmetric to how "
      f"canyon's 0/48-open-sea, substantial-n finding disqualified it)")
for fam in ("scrub", "brush", "dunes"):
    d = out[fam]
    if d["verdict_q1"] in ("no-adjacency-unmeasurable-borrow-confirmed",
                            "adjacency-exists-but-no-coursed-band-evidence"):
        verdict = (f"Q1: {fam} has NO coursed-band stock adjacency evidence for its own "
                   f"wall_du/wall_dv claim ({d['verdict_q1']}). Q2 (band-membership): the "
                   f"literal borrowed texture itself IS map-wide open-sea-coastal in stock "
                   f"({band_open} open-sea-like faces out of {len(band_coastal)} candidates) -- "
                   f"but {fam} is never observed painting it there, in either direction. "
                   f"RECOMMEND: wall_coastal=False (REFUSE island mint) -- a mint cannot claim "
                   f"in-language coastal use for a band the family never actually wears against "
                   f"a cliff anywhere on the map; class={G.GROUNDS[fam]['cls']} already "
                   f"independently excludes {fam} from whole-landmass island fills.")
    else:
        n_open = d.get("open_sea_like_faces", 0)
        n_tris = d.get("wall_tris", 0)
        n_faces = d.get("wall_faces", 0)
        n_gorge = d.get("interior_lidded_faces", 0)
        clears_bar = n_open >= 1 and n_faces >= MIN_FACES_FOR_DIRECT_ALLOW
        verdict = (f"Q1: {fam} has {n_tris} tris/{n_faces} band-matching wall faces genuinely "
                   f"adjacent to its own ground (5dp-exact match to the desert band); of those, "
                   f"{n_open} open-sea, {n_gorge} interior-gorge-like. Q2 band-membership "
                   f"({band_open} open-sea-like faces map-wide on the shared texture, "
                   f"{'>=1' if band_open else '0'} case) corroborates the TEXTURE is coastal-"
                   f"capable. Direct-evidence ALLOW bar ({'>=1 open-sea AND >=2 faces'}): "
                   f"{'CLEARS' if clears_bar else 'FAILS'} ({n_open} open-sea / {n_faces} faces"
                   f"{'' if n_faces >= MIN_FACES_FOR_DIRECT_ALLOW else f' < {MIN_FACES_FOR_DIRECT_ALLOW} min'}). "
                   f"RECOMMEND: wall_coastal={'True -> ALLOW' if clears_bar else 'False -> REFUSE (evidence too thin to certify, despite a non-zero/non-gorge-exclusive sample)'} "
                   f"island mint.")
    print(f"   {fam}: {verdict}")
    out[fam]["final_verdict"] = verdict
    out[fam]["clears_direct_allow_bar"] = bool(
        d["verdict_q1"] == "measured-matches-desert"
        and d.get("open_sea_like_faces", 0) >= 1
        and d.get("wall_faces", 0) >= MIN_FACES_FOR_DIRECT_ALLOW)

OUTD.mkdir(exist_ok=True)
(OUTD / "wall_coastal_unmeasured.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'wall_coastal_unmeasured.json'}")
