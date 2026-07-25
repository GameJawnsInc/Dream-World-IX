"""RUNG F -- THE ORPHAN-DECAL REDRESS (UV-fix round 8, 2026-07-25).

Playtest 6 on FIXED7 (close-up): the shaved knob area "still reads as a different texture than the
normal sand ... either it's a different texture or the way it's applied is causing a shrinkage."
BOTH halves of that report are measured truths, and they are the SAME object:

  * "a different texture" -- the five knobs' 10 decal tris wear the stock ROCK/LICHEN outcrop rect
    u[0.13867,0.19922] v[0.83594,0.86621].  That is genuinely not the dunes mains rect
    (u[0.39355,0.51659] v[0.63378,0.69531]); it is a separate atlas patch.
  * "shrinkage" -- those same tris carry sigma_max ~68..97 world-units per UV unit against the flat
    sand baseline ~132, i.e. the decal is laid ~1.4-1.9x DENSER than the surrounding sand.

In STOCK that pairing reads as a rock catching the light on a steep dune shoulder: every one of the
ten donor triangles dips 34.3-55.4 deg.  Rounds 6 and 7 shaved all five knobs flat (live dip now
4.2-23.9 deg), so the decals are ORPHANED -- dense mottled stains lying in smooth sand with no
feature under them.

THE LAW (owner-ratified lineage, the comp[1] round-10 precedent, and round 4's hole-fill analogue):
an orphaned decal -- one whose parent feature is absent at the deploy -- wears the PLAIN SURROUNDING
MAINS.  Our own shaves orphaned these decals, so the lawful dress is plain dunes mains.

THE CENSUS RULE (mechanical, no hand-picking).  A Terrain triangle is an ORPHANED DECAL iff all of:
  (1) CARRIED -- not in the 2305 synthesized (SPEC UV-degenerate) set;
  (2) GROUND -- its topograph has a ground family (grassland.TOPO_FAMILY / SNR.FAM_OF);
  (3) UNCATALOGUED RECT -- uvf_stock_census.classify_tri_plus == "other_uncatalogued": its 3 UVs sit
      in NO catalogued rect (any family's mains, either STRIPS decal column, any family's translated
      rock/wall band).  This is the sliver probe's classifier, imported, not re-implemented;
  (4) PARENT-GEOMETRY-ABSENT -- the relief the decal was drawn onto is gone.  Stated as a two-sided
      test against the tri's OWN DONOR triangle (Cleyra (13-15,11-12), stock disc 1, located by the
      recorded carry transform shift_world (-768,-384) / DY +0.1224):
          live dip < 25 deg   AND   donor dip >= 25 deg.
      A decal still on a steep face fails the first half; a decal stock itself laid on flat ground
      fails the second half.  Only a face WE flattened satisfies both.

Inside the 40u crater mound that rule selects exactly 10 tris = 5 edge-welded 2-tri knobs, the round-7
probe's set, re-derived here from the bytes rather than trusted.  Swept MAP-WIDE over all 20 blocks it
selects the same 10 and nothing else -- the class is closed knowingly (stage 2c).

THE RE-CLOTHE -- the standing one-window path (uvf_fix3/uvf_fix4 lineage), unmodified:
  centroid cell -> (quad,ori) -> UVs = grassland.ground_uv(vx, vz, cell, quad, ori, "dunes") per
  vertex, ONE window for the whole triangle.  The (quad,ori) field is REBUILT bit-identically to
  uvf_fix3's (method-(a) neighbour decode of the SPECIMEN's lawful grass + uvf_fix2.assign_mains_seeded
  seed 0xF92 on the dropped cells) and stage 3b PROVES the rebuild against FIXED7's own on-disk UVs
  before anything is written.  Method-(a) is additionally re-attempted per target cell in DUNES space
  (stage 3c); it fails on 10/10 own-cells -- exactly uvf_fix4 stage3c's documented finding that stock
  dunes slides free fractional windows and does not sit on the locked 2x2 lattice -- so the standing
  v2 seeded field's answer stands, which is the SAME window the tri's fill neighbours in that cell
  already wear.  The family is confirmed, not assumed: uvf_fix4's nearest-kept-ground-family vote
  (targets excluded from voting) resolves all 10 centroid cells to dunes at distance 0.

UV-ONLY: positions / normals / tangents (hence the IDALL topograph) / indices are byte-identical to
FIXED7 everywhere; Sea/Object/Beach parts untouched; the basin disc untouched by construction (no
target is inside it) and audited anyway.  Rock stamps (topo 58/31) are OUT OF SCOPE -- they keep their
rock geometry and their wall_rock UVs, and the classifier pulls them out before predicate (3).

READ-ONLY vs the game install.  Emits out/rung_f/FF9CustomMap-world-FIXED8 +
out/rung_f/uvf_fix8_report.json.  Renders nothing -- the eye lane owns judgment.  NEVER git commits.

    py -X utf8 uvf_fix8.py            # census + field proof + emission preview, no writes
    py -X utf8 uvf_fix8.py --build    # emit FIXED8 + the full self-check battery
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X                       # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import grassland as G                     # noqa: E402

import seam_null_recon as SNR                                   # noqa: E402  (FAM_OF / RECTS)
import uvf_stock_census as SC                                   # noqa: E402  (classify_tri_plus)
import uvf_fix2 as F2                                           # noqa: E402
import uvf_fix3 as F3                                           # noqa: E402
import uvf_relief_probe as P                                    # noqa: E402  (PARTS / pkey / stats)

CH_POS, CH_NRM, CH_UV, CH_TAN = X.CH_POS, X.CH_NRM, X.CH_UV, X.CH_TAN

RUNG_F = HERE / "out" / "rung_f"
SPEC = RUNG_F / "FF9CustomMap-world"                 # the round-0 staged specimen (classifier of record)
BASE = RUNG_F / "FF9CustomMap-world-FIXED7"          # round 8's INPUT
OUT = RUNG_F / "FF9CustomMap-world-FIXED8"           # round 8's OUTPUT
BUILD_JSON = RUNG_F / "rung_f_build.json"
FORENSICS = RUNG_F / "uvf_forensics.json"
FIX7_REPORT = RUNG_F / "uvf_fix7_report.json"        # the recorded carry transform (a transform, not a verdict)
SLIVER_PROBE = RUNG_F / "uvf_sliver_probe.json"      # round 7's diagnosis (cross-check only)
REPORT = RUNG_F / "uvf_fix8_report.json"

PARTS = P.PARTS
N_FILES = 180
N_SYNTH = 2305
CELL = 4.0
V2_SEED = F2.V2_SEED                                 # 0xF92
FAMILIES = ("grass", "desert", "dunes")
TARGET_FAMILY = "dunes"

BASIN_C = (127.14, -1161.42)
BASIN_R = 7.92
MOUND_R = 40.0                                       # the crater-mound region: the act set lives here

FLAT_DIP_T = 25.0                                    # predicate (4a): "no longer supports a feature"
DONOR_DIP_T = 25.0                                   # predicate (4b): the parent relief the decal was drawn for
N_EXPECTED_TRIS = 10
N_EXPECTED_KNOBS = 5

DONOR_BLOCKS = [(13, 11), (14, 11), (15, 11), (13, 12), (14, 12), (15, 12)]
POS_DP = P.POS_DP                                    # 3
XZ_DP = 2                                            # donor-match key resolution (the carry is exact in XZ)

REGION_TOL = 1e-6
AREA_EPS = 1e-9


def log(m):
    print(m, flush=True)


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def own_cell(vx, vz):
    return (math.floor(vx / CELL), math.floor(vz / CELL))


def centroid_xz(w3):
    return (sum(p[0] for p in w3) / 3.0, sum(p[2] for p in w3) / 3.0)


def rc(x, z):
    return math.hypot(x - BASIN_C[0], z - BASIN_C[1])


def area3d(w3):
    a, b, c = w3
    e1 = [b[k] - a[k] for k in range(3)]
    e2 = [c[k] - a[k] for k in range(3)]
    n = (e1[1] * e2[2] - e1[2] * e2[1],
         e1[2] * e2[0] - e1[0] * e2[2],
         e1[0] * e2[1] - e1[1] * e2[0])
    return 0.5 * math.sqrt(sum(v * v for v in n)), n


def dip_deg(w3):
    a, n = area3d(w3)
    if a < 1e-9:
        return None
    nl = math.sqrt(sum(v * v for v in n))
    return math.degrees(math.acos(min(1.0, abs(n[1]) / nl)))


def uv_area(uv3):
    (u0, v0), (u1, v1), (u2, v2) = uv3
    return abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) / 2.0


def sigma_max(w3, uv3):
    """largest singular value (world units per UV unit) of the affine uv->world map -- the texel
    smear / density scale.  Flat sand here measures ~132; the orphaned decals ~68-97."""
    a = uv3[1][0] - uv3[0][0]
    b = uv3[2][0] - uv3[0][0]
    c = uv3[1][1] - uv3[0][1]
    d = uv3[2][1] - uv3[0][1]
    det = a * d - b * c
    if abs(det) < 1e-12:
        return None
    inv = ((d / det, -b / det), (-c / det, a / det))
    e = [[w3[1][k] - w3[0][k], w3[2][k] - w3[0][k]] for k in range(3)]
    jm = [[e[k][0] * inv[0][0] + e[k][1] * inv[1][0],
           e[k][0] * inv[0][1] + e[k][1] * inv[1][1]] for k in range(3)]
    # singular values of the 3x2 J via the 2x2 Gram matrix
    g00 = sum(jm[k][0] * jm[k][0] for k in range(3))
    g01 = sum(jm[k][0] * jm[k][1] for k in range(3))
    g11 = sum(jm[k][1] * jm[k][1] for k in range(3))
    tr, dt = g00 + g11, g00 * g11 - g01 * g01
    disc = max(0.0, tr * tr / 4.0 - dt)
    return math.sqrt(max(0.0, tr / 2.0 + math.sqrt(disc)))


def xzk(p):
    return (round(float(p[0]), XZ_DP), round(float(p[2]), XZ_DP))


def trikey(w3):
    return tuple(sorted(xzk(p) for p in w3))


# =================================================================================================
#  STAGE 1 -- the mesh, the synthesized-tri classifier of record, and its carry-over into FIXED7
# =================================================================================================
def stage1(report):
    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    assert len(touched) == 20, len(touched)

    forensics = json.loads(FORENSICS.read_text(encoding="utf-8"))
    apron_keys = {(tuple(r["block"]), round(r["centroid"][0], 3), round(r["centroid"][2], 3))
                  for r in forensics["records"]
                  if r.get("uv_verdict") == "degenerate-zero-area" and r["provenance"] == "apron"}

    spec_meshes = F3.load_blocks(SPEC, touched)
    base_meshes = F3.load_blocks(BASE, touched)

    idx_diff = xz_diff = vcount_diff = y_diff = uv_diff = 0
    for b in touched:
        a = M.read_ff9mesh(F2.terr_path(BASE, *b))
        s = M.read_ff9mesh(F2.terr_path(SPEC, *b))
        idx_diff += (a["indices"] != s["indices"])
        vcount_diff += (a["vcount"] != s["vcount"])
        uv_diff += (a["uvs"] != s["uvs"])
        for j in range(min(a["vcount"], s["vcount"])):
            p, q = a["verts"][j], s["verts"][j]
            xz_diff += (p[0] != q[0] or p[2] != q[2])
            y_diff += (p[1] != q[1])

    defective, lawful_grass = F3.classify_defective(spec_meshes, apron_keys, touched)
    assert len(defective) == N_SYNTH, f"synthesized set {len(defective)} != {N_SYNTH}"
    synth_key = {(d["block"], d["tri"]) for d in defective}

    report["stage1_mesh"] = dict(
        base_tree=BASE.name, out_tree=OUT.name, touched_blocks=len(touched),
        n_synthesized_tris=len(defective), n_lawful_grass_tris=len(lawful_grass),
        spec_vs_base=dict(index_files_differing=idx_diff, vcount_files_differing=vcount_diff,
                          vertex_entries_with_XZ_differing=xz_diff,
                          vertex_entries_with_Y_differing=y_diff, uv_files_differing=uv_diff),
        classifier_carries_over=(idx_diff == 0 and xz_diff == 0 and vcount_diff == 0),
        note=("the synthesized-tri classifier of record runs on the SPECIMEN's degenerate UVs "
              "(uvf_fix2/3); rounds 1-4 cured those UVs and rounds 5-7 moved Y, so (block,tri) "
              "identity is proved instead by 0 index and 0 X/Z differences."))
    log(f"[s1] synth={len(defective)} lawful_grass={len(lawful_grass)}  carry-over ok="
        f"{idx_diff == 0 and xz_diff == 0 and vcount_diff == 0}  (Y entries differing {y_diff})")
    return dict(touched=touched, spec=spec_meshes, base=base_meshes,
                defective=defective, lawful_grass=lawful_grass, synth_key=synth_key)


# =================================================================================================
#  STAGE 2 -- THE ORPHANED-DECAL CENSUS (mechanical; mound-scoped act set + map-wide sweep)
# =================================================================================================
def load_donor(report):
    """the donor triangles the carry took, indexed by their SHIFTED plan key.  A transform, read from
    uvf_fix7_report's stage4_donor_overlay -- not re-derived, not a judgement."""
    ov = json.loads(FIX7_REPORT.read_text(encoding="utf-8"))["stage4_donor_overlay"]
    sh = (float(ov["shift_world"][0]), float(ov["shift_world"][1]))
    dy = float(ov["DY"])
    donor = {}
    for (bx, by) in DONOR_BLOCKS:
        bm = X.read_block(bx, by, disc=1, part="terrain")
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            w = [(bm.verts[j][0] + ox + sh[0], bm.verts[j][1] + dy, bm.verts[j][2] + oz + sh[1])
                 for j in tri]
            uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            donor[trikey(w)] = dict(w=w, uv=uv, topo=topo, block=(bx, by))
    report["donor_reference"] = dict(
        blocks=[list(b) for b in DONOR_BLOCKS], shift_world=list(sh), DY=dy,
        n_donor_tris_indexed=len(donor), source="uvf_fix7_report.json stage4_donor_overlay",
        note=("stock disc-1 Cleyra grass|desert|dunes junction, READ-ONLY.  Donor triangles are "
              "keyed by their SHIFTED plan (x,z) triple @2dp -- the carry is verbatim in X/Z, so a "
              "carried tri and its donor share that key exactly."))
    log(f"[s2] donor index: {len(donor)} tris from {len(DONOR_BLOCKS)} stock blocks "
        f"(shift {sh}, DY {dy})")
    return donor, sh, dy


def census(report, S, donor):
    """Every Terrain tri of all 20 blocks -> the 4-predicate orphan test.  Returns the act set."""
    touched, synth_key = S["touched"], S["synth_key"]
    cls_hist = Counter()
    cands = []                       # predicates (1)(2)(3) satisfied
    for b in touched:
        bm = S["base"][b]
        ox, oz = X.block_world_origin(*b)
        Pv, U, T = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_UV], bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            w = [(float(Pv[j][0]) + ox, float(Pv[j][1]), float(Pv[j][2]) + oz) for j in tri]
            uv = [(float(U[j][0]), float(U[j][1])) for j in tri]
            topo = X.decode_id(int(round(T[tri[0]][0])))["topograph"]
            fam = SNR.FAM_OF.get(topo)
            cls, det = SC.classify_tri_plus(fam, uv) if fam else ("no_family", None)
            cls_hist[cls] += 1
            if cls != "other_uncatalogued":                       # predicate (3)
                continue
            if (b, t) in synth_key:                               # predicate (1)
                cands.append(dict(block=b, tri=t, carried=False, topo=topo, fam=fam))
                continue
            if G.TOPO_FAMILY.get(topo) is None:                   # predicate (2)
                continue
            cx, cz = centroid_xz(w)
            live_dip = dip_deg(w)
            d = donor.get(trikey(w))
            rec = dict(
                block=b, tri=t, carried=True, topo=topo, fam=fam,
                centroid=[round(cx, 3), round(cz, 3)],
                r_crater=round(rc(cx, cz), 2),
                in_mound=(rc(cx, cz) <= MOUND_R),
                live_dip=None if live_dip is None else round(live_dip, 2),
                donor_matched=d is not None,
                donor_block=list(d["block"]) if d else None,
                donor_dip=None if d is None or dip_deg(d["w"]) is None else round(dip_deg(d["w"]), 2),
                max_abs_dY_vs_donor=(None if d is None else round(max(
                    abs(p[1] - dm) for p, dm in zip(
                        sorted(w, key=xzk),
                        [q[1] for q in sorted(d["w"], key=xzk)])), 4)),
                uv_rect=[round(min(u for u, _v in uv), 5), round(min(v for _u, v in uv), 5),
                         round(max(u for u, _v in uv), 5), round(max(v for _u, v in uv), 5)],
                sigma_max=None if sigma_max(w, uv) is None else round(sigma_max(w, uv), 2),
                verts=[[round(x, 3) for x in p] for p in w])
            rec["flat_now"] = (rec["live_dip"] is not None and rec["live_dip"] < FLAT_DIP_T)
            rec["donor_had_relief"] = (rec["donor_dip"] is not None and rec["donor_dip"] >= DONOR_DIP_T)
            rec["parent_geometry_absent"] = bool(rec["flat_now"] and rec["donor_had_relief"])
            cands.append(rec)

    carried = [c for c in cands if c["carried"]]
    orphan = [c for c in carried if c["parent_geometry_absent"]]
    orphan.sort(key=lambda r: (r["r_crater"], r["block"], r["tri"]))
    in_mound = [c for c in orphan if c["in_mound"]]
    outside = [c for c in orphan if not c["in_mound"]]
    rejected = [c for c in carried if not c["parent_geometry_absent"]]

    # --- knob clustering: shared plan EDGE over the act set ---------------------------------------
    edge_owner = defaultdict(list)
    for i, r in enumerate(in_mound):
        ks = [xzk(p) for p in r["verts"]]
        for a in range(3):
            edge_owner[tuple(sorted((ks[a], ks[(a + 1) % 3])))].append(i)
    parent = list(range(len(in_mound)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for owners in edge_owner.values():
        for j in owners[1:]:
            ra, rb = find(owners[0]), find(j)
            if ra != rb:
                parent[rb] = ra
    knobs = defaultdict(list)
    for i in range(len(in_mound)):
        knobs[find(i)].append(i)
    knob_list = []
    for members in knobs.values():
        rs = [in_mound[i] for i in members]
        knob_list.append(dict(
            tris=[f"({r['block'][0]}, {r['block'][1]})#{r['tri']}" for r in rs],
            n_tris=len(rs),
            centroid=[round(sum(r["centroid"][0] for r in rs) / len(rs), 2),
                      round(sum(r["centroid"][1] for r in rs) / len(rs), 2)],
            r_crater=round(sum(r["r_crater"] for r in rs) / len(rs), 2),
            live_dip=[r["live_dip"] for r in rs], donor_dip=[r["donor_dip"] for r in rs]))
    knob_list.sort(key=lambda k: k["r_crater"])

    report["stage2_census"] = dict(
        rule=("ORPHANED DECAL := (1) CARRIED (not one of the 2305 SPEC-UV-degenerate synthesized "
              "tris) AND (2) GROUND topograph (grassland.TOPO_FAMILY) AND (3) UNCATALOGUED RECT "
              "(uvf_stock_census.classify_tri_plus == 'other_uncatalogued': UVs in no family mains, "
              "no STRIPS decal column, no translated rock/wall band) AND (4) PARENT-GEOMETRY-ABSENT "
              f"(live dip < {FLAT_DIP_T} deg AND its OWN donor triangle's dip >= {DONOR_DIP_T} deg). "
              "No position, index or name is hand-listed anywhere in this rule."),
        uv_class_hist_all_terrain=dict(cls_hist),
        n_uncatalogued_total=sum(1 for c in cands),
        n_uncatalogued_synthesized=sum(1 for c in cands if not c["carried"]),
        n_uncatalogued_carried=len(carried),
        n_orphaned=len(orphan), n_orphaned_in_mound=len(in_mound),
        n_orphaned_outside_mound=len(outside),
        mound_radius_u=MOUND_R, crater_center=list(BASIN_C),
        act_set=in_mound, knobs=knob_list, n_knobs=len(knob_list),
        expected_tris=N_EXPECTED_TRIS, expected_knobs=N_EXPECTED_KNOBS,
        matches_round7_probe=(len(in_mound) == N_EXPECTED_TRIS and len(knob_list) == N_EXPECTED_KNOBS),
        surprises=([] if (len(in_mound) == N_EXPECTED_TRIS and len(knob_list) == N_EXPECTED_KNOBS
                          and not outside)
                   else dict(orphans_outside_the_mound=outside,
                             n_in_mound=len(in_mound), n_knobs=len(knob_list))))
    log(f"[s2] uncatalogued carried={len(carried)}  orphaned={len(orphan)} "
        f"(in-mound {len(in_mound)} / outside {len(outside)})  knobs={len(knob_list)}")
    for k in knob_list:
        log(f"      knob r={k['r_crater']:5.2f} {k['tris']} live_dip={k['live_dip']} "
            f"donor_dip={k['donor_dip']}")
    assert len(in_mound) == N_EXPECTED_TRIS, (
        f"act set {len(in_mound)} != {N_EXPECTED_TRIS} -- census disagreement, refusing to build")
    assert len(knob_list) == N_EXPECTED_KNOBS, (
        f"{len(knob_list)} knobs != {N_EXPECTED_KNOBS} -- census disagreement, refusing to build")
    assert all(k["n_tris"] == 2 for k in knob_list), "a knob is not a 2-tri pair"
    return in_mound, rejected, orphan


def census_mapwide(report, rejected, orphan):
    """STAGE 2c -- REPORT-ONLY.  Everything the census looked at outside the act set, so the class is
    closed knowingly.  Each rejected carried uncatalogued tri is shown WITH the predicate that
    rejected it and its donor evidence."""
    rows = []
    for r in sorted(rejected, key=lambda z: (z["r_crater"], z["block"], z["tri"])):
        why = []
        if not r["donor_matched"]:
            why.append("donor-unmatched (parent relief UNKNOWN -- flagged, not acted on)")
        else:
            if not r["flat_now"]:
                why.append(f"still steep (live dip {r['live_dip']} >= {FLAT_DIP_T})")
            if not r["donor_had_relief"]:
                why.append(f"donor was already flat (donor dip {r['donor_dip']} < {DONOR_DIP_T}) "
                           "-- a lawful stock decal on stock's own ground, never orphaned by us")
        rows.append(dict(tri=f"({r['block'][0]}, {r['block'][1]})#{r['tri']}", topo=r["topo"],
                         fam=r["fam"], centroid=r["centroid"], r_crater=r["r_crater"],
                         in_mound=r["in_mound"], live_dip=r["live_dip"], donor_dip=r["donor_dip"],
                         max_abs_dY_vs_donor=r["max_abs_dY_vs_donor"], uv_rect=r["uv_rect"],
                         sigma_max=r["sigma_max"], rejected_by=why))
    by_rect = Counter(tuple(r["uv_rect"]) for r in rows)
    report["stage2c_mapwide_orphan_census"] = dict(
        scope="all 20 touched blocks, every Terrain triangle, both inside and outside the 40u mound",
        n_carried_uncatalogued_total=len(rows) + len(orphan),
        n_orphaned_acted_on=len(orphan),
        n_carried_uncatalogued_not_orphaned=len(rows),
        not_orphaned_rows=rows,
        not_orphaned_rects={str(list(k)): v for k, v in sorted(by_rect.items())},
        n_donor_unmatched=sum(1 for r in rows if r["donor_dip"] is None),
        class_closed=(sum(1 for r in rows if r["donor_dip"] is None) == 0),
        finding=("every carried uncatalogued-rect triangle in the tree is accounted for: the acted-on "
                 "orphans, plus a remainder whose donor dip EQUALS its live dip -- stock laid those "
                 "decals on that geometry and nothing of ours moved it, so they are lawful carried "
                 "vocabulary, not orphans.  No member of the class is left unreported."))
    log(f"[s2c] map-wide: {len(orphan)} orphaned (acted) + {len(rows)} carried-uncatalogued "
        f"NOT orphaned; donor-unmatched={sum(1 for r in rows if r['donor_dip'] is None)}")
    return rows


# =================================================================================================
#  STAGE 3 -- the standing (quad,ori) field, REUSED (rebuilt bit-identically and proved)
# =================================================================================================
def stage3_cellfield(report, S):
    defective, lawful_grass = S["defective"], S["lawful_grass"]
    by_cell = defaultdict(list)
    for (cell, vw, uv3) in lawful_grass:
        by_cell[cell].append((vw, uv3))
    decoded_a = {}
    for cell in sorted(by_cell):
        for (vw, uv3) in by_cell[cell]:
            qo = F2.decode_quad_ori(cell, vw, uv3)
            if qo is not None:
                decoded_a[cell] = qo
                break

    target_cells, centroid_cells = set(), set()
    for d in defective:
        for (vx, _vy, vz) in d["vw"]:
            target_cells.add(own_cell(vx, vz))
        centroid_cells.add(own_cell(*centroid_xz(d["vw"])))
    resolve = target_cells | centroid_cells
    dropped = sorted(c for c in resolve if c not in decoded_a)
    vq, vo = F2.assign_mains_seeded(dropped, dict(decoded_a),
                                    {c: o for c, (q, o) in decoded_a.items()}, seed=V2_SEED)
    field = {c: (q, o, "a") for c, (q, o) in decoded_a.items()}
    for c in dropped:
        field[c] = (vq[c], vo[c], "v2")

    report["stage3_cell_field"] = dict(
        method_a_cells=len(decoded_a), dropped_cells=len(dropped),
        resolve_cells=len(resolve), total_field_cells=len(field), seed=V2_SEED,
        note=("construction IDENTICAL to uvf_fix3/uvf_fix4 (method-(a) decode of the SPECIMEN's "
              "lawful grass + assign_mains_seeded on the dropped cells) -- the field is REUSED, "
              "never re-drawn; stage 3b proves it against FIXED7's own bytes."))
    log(f"[s3] cell field: method-a={len(decoded_a)} dropped={len(dropped)} total={len(field)}")
    return field


def stage3b_prove_reuse(report, S, field):
    """PROOF the rebuilt field is the one already on disk: for every one of the 2305 synthesized
    tris, ONE (cell,quad,ori) from this field, in ONE family, must reproduce its FIXED7 UVs
    bit-for-bit under float32.  uvf_fix4's own verify recorded single=2304 / multi=1 (the single
    documented per-vertex last-resort sliver), so 2304 is the floor here."""
    touched = S["touched"]
    disk = {b: M.read_ff9mesh(F2.terr_path(BASE, *b)) for b in touched}
    single = 0
    misses = []
    fam_hist = Counter()
    kind_hist = Counter()
    for d in S["defective"]:
        uv3 = [disk[d["block"]]["uvs"][j] for j in d["vids"]]
        cand = [own_cell(*centroid_xz(d["vw"]))] + [own_cell(vx, vz) for (vx, _vy, vz) in d["vw"]]
        hit = None
        seen = set()
        for k, cell in enumerate(cand):
            if cell in seen or cell not in field:
                continue
            seen.add(cell)
            q, o, _m = field[cell]
            for fam in FAMILIES:
                pred = [G.ground_uv(vx, vz, cell, q, o, fam) for (vx, _vy, vz) in d["vw"]]
                if all(f32(pred[a][c]) == f32(uv3[a][c]) for a in range(3) for c in range(2)):
                    hit = (fam, "centroid" if k == 0 else "owncell-fallback")
                    break
            if hit:
                break
        if hit:
            single += 1
            fam_hist[hit[0]] += 1
            kind_hist[hit[1]] += 1
        else:
            misses.append(f"({d['block'][0]}, {d['block'][1]})#{d['tri']}")
    report["stage3b_reuse_proof"] = dict(
        n_synthesized_tris=len(S["defective"]), reconstructed_from_this_field=single,
        not_reconstructed=len(misses), examples_not_reconstructed=misses[:5],
        family_of_reconstruction=dict(fam_hist), window_source=dict(kind_hist),
        uvf_fix4_reference=dict(single=2304, multi=1),
        verdict=("PROVEN: the rebuilt (quad,ori) field is the field FIXED7's own UVs were emitted "
                 "through, so the round-8 re-clothe reuses the standing window, it does not mint one"
                 if len(misses) <= 1 else "FAILED -- field reconstruction diverges from FIXED7"))
    log(f"[s3b] field reuse proof: {single}/{len(S['defective'])} synthesized tris reconstruct "
        f"bit-exactly (misses {len(misses)}); families={dict(fam_hist)}")
    assert len(misses) <= 1, "the (quad,ori) field does not reproduce FIXED7 -- refusing to build"
    return single, misses


def stage3c_method_a_dunes(report, S, act, field):
    """Per the work order the target cell's window is sought FIRST by method-(a) -- an exact decode
    from a lawful same-cell / neighbour MAINS triangle -- and only then from the standing v2 field.
    Attempted here in DUNES space (uv minus GROUNDS['dunes'] translation, then the grass-lattice
    decode) and in GRASS space, and reported per cell."""
    touched = S["touched"]
    du, dv = G.GROUNDS[TARGET_FAMILY]["mains_du"], G.GROUNDS[TARGET_FAMILY]["mains_dv"]
    mains_by_cell = defaultdict(list)                   # (cell, fam) -> [(w, uv)]
    for b in touched:
        bm = S["base"][b]
        ox, oz = X.block_world_origin(*b)
        Pv, U, T = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_UV], bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            topo = X.decode_id(int(round(T[tri[0]][0])))["topograph"]
            fam = SNR.FAM_OF.get(topo)
            if fam is None:
                continue
            uv = [(float(U[j][0]), float(U[j][1])) for j in tri]
            if SC.classify_tri_plus(fam, uv)[0] != "mains_own":
                continue
            w = [(float(Pv[j][0]) + ox, float(Pv[j][1]), float(Pv[j][2]) + oz) for j in tri]
            mains_by_cell[(own_cell(*centroid_xz(w)), fam)].append((w, uv))

    rows = []
    resolved = {}
    for r in act:
        cell = tuple(r["cell"])
        got = None
        for fam, (fu, fv) in (("dunes", (du, dv)), ("grass", (0.0, 0.0))):
            for (w, uv) in mains_by_cell.get((cell, fam), []):
                qo = F2.decode_quad_ori(cell, w, [(u - fu, v - fv) for (u, v) in uv])
                if qo is not None:
                    got = dict(source="method_a", family_space=fam, quad=list(qo[0]), ori=qo[1])
                    break
            if got:
                break
        fq, fo, fm = field[cell]
        if got is None:
            resolved[cell] = (fq, fo, f"standing-field:{fm}")
        else:
            resolved[cell] = (tuple(got["quad"]), got["ori"], f"method_a:{got['family_space']}")
        rows.append(dict(
            cell=list(cell),
            n_same_cell_mains_dunes=len(mains_by_cell.get((cell, "dunes"), [])),
            n_same_cell_mains_grass=len(mains_by_cell.get((cell, "grass"), [])),
            method_a=got,
            standing_field=dict(quad=list(fq), ori=fo, provenance=fm),
            used=dict(quad=list(resolved[cell][0]), ori=resolved[cell][1],
                      source=resolved[cell][2])))
    seen = {}
    uniq = []
    for row in rows:
        k = tuple(row["cell"])
        if k not in seen:
            seen[k] = 1
            uniq.append(row)
    report["stage3c_window_resolution"] = dict(
        per_cell=uniq, n_distinct_cells=len(uniq),
        n_method_a=sum(1 for r in uniq if r["method_a"] is not None),
        n_standing_field=sum(1 for r in uniq if r["method_a"] is None),
        finding=("method-(a) fails on every target cell: those cells hold carried STOCK dunes mains, "
                 "and uvf_fix4 stage3c already measured that stock dunes does NOT sit on the locked "
                 "per-cell 2x2 (quad,ori) lattice -- it slides free fractional windows, so no exact "
                 "decode exists.  The standing v2 seeded field's answer therefore stands, which is "
                 "exactly the window the tri's own fill neighbours in that cell already wear -- the "
                 "seamless choice, not a mint."))
    log(f"[s3c] window resolution: method-a {sum(1 for r in uniq if r['method_a'])}/"
        f"{len(uniq)} cells; standing field {sum(1 for r in uniq if not r['method_a'])}")
    return resolved


# =================================================================================================
#  STAGE 4 -- the FAMILY of each target cell (uvf_fix4's nearest-kept-ground-family vote)
# =================================================================================================
def stage4_family(report, S, act):
    touched, synth_key = S["touched"], S["synth_key"]
    act_key = {(tuple(r["block"]), r["tri"]) for r in act}
    votes = defaultdict(Counter)
    for b in touched:
        bm = S["base"][b]
        ox, oz = X.block_world_origin(*b)
        Pv, T = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            if (b, t) in synth_key or (b, t) in act_key:      # the targets never vote on themselves
                continue
            fam = G.TOPO_FAMILY.get(X.decode_id(int(round(T[tri[0]][0])))["topograph"])
            if fam is None:
                continue
            cx = sum(Pv[j][0] + ox for j in tri) / 3.0
            cz = sum(Pv[j][2] + oz for j in tri) / 3.0
            votes[own_cell(cx, cz)][fam] += 1
    src = [(c[0], c[1], votes[c]) for c in sorted(votes)]

    def nearest_family(fc):
        groups = defaultdict(Counter)
        for (sx, sy, cnt) in src:
            groups[(sx - fc[0]) ** 2 + (sy - fc[1]) ** 2] += cnt
        ds = sorted(groups)
        acc = Counter()
        for d2 in ds:
            acc += groups[d2]
            rank = acc.most_common()
            if len(rank) == 1 or rank[0][1] > rank[1][1]:
                return rank[0][0], math.sqrt(ds[0]), dict(groups[ds[0]])
        best = max(acc.values())
        return sorted(f for f, n in acc.items() if n == best)[0], math.sqrt(ds[0]), dict(groups[ds[0]])

    rows = []
    non_dunes = []
    for r in act:
        cell = tuple(r["cell"])
        fam, d0, ring0 = nearest_family(cell)
        r["surround_family"] = fam
        r["surround_d0"] = round(d0, 3)
        rows.append(dict(tri=r["name"], cell=list(cell), surround_family=fam,
                         nearest_source_distance_cells=round(d0, 3), nearest_ring_votes=ring0,
                         own_topo=r["topo"], own_topo_family=G.TOPO_FAMILY.get(r["topo"])))
        if fam != TARGET_FAMILY:
            non_dunes.append(rows[-1])
    report["stage4_family"] = dict(
        method=("uvf_fix4's family field, verbatim: every KEPT ground Terrain tri (targets and "
                "synthesized tris excluded) votes grassland.TOPO_FAMILY[topo] into its centroid 4u "
                "cell; a cell takes the family of its exact-nearest source cell, ties by kept-tri "
                "majority in the nearest ring, then by absorbing the next ring, then lexically."),
        per_target=rows, n_dunes=sum(1 for r in rows if r["surround_family"] == TARGET_FAMILY),
        n_not_dunes=len(non_dunes), not_dunes=non_dunes,
        all_in_dunes_donut=(not non_dunes),
        note=("every target's OWN topograph is 41 = dunes AND its surrounding family field resolves "
              "to dunes at distance 0 (its own cell already holds carried dunes ground) -- the two "
              "independent readings agree, so 'plain dunes mains' is the dress on both."))
    log(f"[s4] surrounding family: dunes {sum(1 for r in rows if r['surround_family'] == 'dunes')}"
        f"/{len(rows)}  not-dunes={len(non_dunes)}")
    return non_dunes


# =================================================================================================
#  STAGE 5 -- EMIT (preview or build)
# =================================================================================================
def emit_uvs(r, resolved):
    cell = tuple(r["cell"])
    q, o, _src = resolved[cell]
    return [list(G.ground_uv(p[0], p[2], cell, q, o, r["emit_family"])) for p in r["verts_f"]]


def stage5_preview(report, act, resolved):
    lo_u, lo_v, hi_u, hi_v = G.ground_main_region(TARGET_FAMILY)
    rows = []
    ok = True
    for r in act:
        new = emit_uvs(r, resolved)
        sp = F3.max_pairwise_uv(new)
        inreg = all(lo_u - REGION_TOL <= u <= hi_u + REGION_TOL
                    and lo_v - REGION_TOL <= v <= hi_v + REGION_TOL for (u, v) in new)
        degen = F2.uv_tri_degen(new)
        sm_old = sigma_max(r["verts_f"], r["uv_old"])
        sm_new = sigma_max(r["verts_f"], new)
        r["uv_new"] = new
        rows.append(dict(
            tri=r["name"], centroid_cell=list(r["cell"]),
            quad=list(resolved[tuple(r["cell"])][0]), ori=resolved[tuple(r["cell"])][1],
            window_source=resolved[tuple(r["cell"])][2], family=r["emit_family"],
            uv_old=[[round(x, 5) for x in p] for p in r["uv_old"]],
            uv_new=[[round(x, 5) for x in p] for p in new],
            uv_spread=round(sp, 6), one_window_scale=round(F3.QUAD_DIAG, 6),
            spread_within_one_window=bool(sp <= F3.QUAD_DIAG + 1e-9),
            uv_area_old=round(uv_area(r["uv_old"]), 8), uv_area_new=round(uv_area(new), 8),
            sigma_max_old=None if sm_old is None else round(sm_old, 2),
            sigma_max_new=None if sm_new is None else round(sm_new, 2),
            in_dunes_mains_region=inreg, degenerate=degen))
        ok = ok and inreg and not degen and sp <= F3.QUAD_DIAG + 1e-9
    report["stage5_reclothe"] = dict(
        emission_path="grassland.ground_uv(vx, vz, centroid_cell, quad, ori, 'dunes')  [the kit's own family path]",
        one_window_per_tri=True,
        dunes_mains_region=[round(x, 5) for x in G.ground_main_region(TARGET_FAMILY)],
        dunes_translation=[G.GROUNDS[TARGET_FAMILY]["mains_du"], G.GROUNDS[TARGET_FAMILY]["mains_dv"]],
        per_tri=rows, all_in_region_nondegenerate_one_window=ok)
    log(f"[s5] preview: {len(rows)} tris re-clothed; all in-region + non-degenerate + one-window={ok}")
    assert ok, "an emitted tri is degenerate / out of region / wider than one window"
    return rows


def stage6_build(report, S, act):
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(BASE, OUT)
    n_copied = sum(1 for p in OUT.rglob("*") if p.is_file())
    assert n_copied == N_FILES, f"copy mismatch {n_copied} != {N_FILES}"
    log(f"[s6] copied {n_copied} files -> {OUT}")

    meshes = F3.load_blocks(OUT, S["touched"])
    changed_vids = defaultdict(set)
    dirty = set()
    for r in act:
        bm = meshes[tuple(r["block"])]
        tri = bm.tris[r["tri"]]
        uvs = bm.chan_arrays[CH_UV]
        for j, uv in zip(tri, r["uv_new"]):
            uvs[j] = list(uv)
            changed_vids[tuple(r["block"])].add(j)
        dirty.add(tuple(r["block"]))
    written = {}
    for b in sorted(dirty):
        p = F2.terr_path(OUT, *b)
        M.write_ff9mesh(meshes[b], p)
        written[str(p.relative_to(OUT))] = sha256_file(p)
    report["stage6_apply"] = dict(
        tris_rewritten=len(act), uv_vertex_entries_rewritten=sum(len(s) for s in changed_vids.values()),
        blocks_written=[list(b) for b in sorted(dirty)], files_written=written,
        move_axis="UV only -- no position, normal, tangent or index byte is written")
    log(f"[s6] rewrote {len(act)} tris / {sum(len(s) for s in changed_vids.values())} UV entries "
        f"across {len(dirty)} Terrain files")
    return dict(changed_vids=changed_vids, dirty=sorted(dirty), written=written)


# =================================================================================================
#  STAGE 7 -- THE SELF-CHECK BATTERY (uvf_fix lineage, everything against the BYTES ON DISK)
# =================================================================================================
def stage7_verify(report, S, act, resolved, A, donor):
    v = {}
    touched = S["touched"]
    a7 = {b: M.read_ff9mesh(F2.terr_path(BASE, *b)) for b in touched}       # FIXED7
    a8 = {b: M.read_ff9mesh(F2.terr_path(OUT, *b)) for b in touched}        # FIXED8

    # (1) FLAT MESH ---------------------------------------------------------------------------------
    bad = [f"{b[0]},{b[1]}" for b in touched
           if not (a8[b]["vcount"] == len(a8[b]["indices"]) == len(a8[b]["verts"])
                   and len(a8[b]["indices"]) % 3 == 0)]
    v["flat_mesh"] = dict(bad_files=bad, ok=not bad)

    # (2) BYTE RIGIDITY vs FIXED7 -------------------------------------------------------------------
    rig = dict(pos_bad=0, nrm_bad=0, tan_bad=0, idx_bad=0, vcount_bad=0,
               uv_expected=0, uv_unexpected=0)
    for b in touched:
        a, f = a7[b], a8[b]
        rig["pos_bad"] += (a["verts"] != f["verts"])
        rig["nrm_bad"] += (a["normals"] != f["normals"])
        rig["tan_bad"] += (a["tangents"] != f["tangents"])
        rig["idx_bad"] += (a["indices"] != f["indices"])
        rig["vcount_bad"] += (a["vcount"] != f["vcount"])
        chg = A["changed_vids"].get(b, set())
        for j in range(a["vcount"]):
            if a["uvs"][j] != f["uvs"][j]:
                rig["uv_expected" if j in chg else "uv_unexpected"] += 1
    v["byte_rigidity_vs_fixed7"] = rig
    v["uv_only"] = (rig["pos_bad"] == 0 and rig["nrm_bad"] == 0 and rig["tan_bad"] == 0
                    and rig["idx_bad"] == 0 and rig["vcount_bad"] == 0
                    and rig["uv_unexpected"] == 0)

    # (2b) whole-tree file diff ---------------------------------------------------------------------
    changed = []
    for p in sorted(BASE.rglob("*")):
        if p.is_file() and sha256_file(p) != sha256_file(OUT / str(p.relative_to(BASE))):
            changed.append(str(p.relative_to(BASE)))
    expected = sorted(A["written"])
    v["tree_diff_vs_fixed7"] = dict(
        n_files_changed=len(changed), files=changed, expected_files=expected,
        exactly_the_expected_terrain_set=(sorted(changed) == expected),
        n_non_terrain_changed=sum(1 for r in changed if "Terrain" not in r),
        sea_and_object_untouched=all("Terrain" in r for r in changed))

    # (3) ZERO DEGENERATE UVs tree-wide -------------------------------------------------------------
    degen = 0
    for b in touched:
        uvs = a8[b]["uvs"]
        for t in range(len(a8[b]["indices"]) // 3):
            tri = a8[b]["indices"][3 * t:3 * t + 3]
            if F2.uv_degenerate([(uvs[j][0], uvs[j][1]) for j in tri]):
                degen += 1
    v["degenerate_uv_tris_all_terrain"] = dict(n=degen, ok=(degen == 0))

    # (4) ONE-WINDOW COHERENCE of the 10 new tris, re-derived FROM DISK -----------------------------
    single = 0
    detail = []
    lo_u, lo_v, hi_u, hi_v = G.ground_main_region(TARGET_FAMILY)
    out_of_region = 0
    for r in act:
        b = tuple(r["block"])
        tri = [a8[b]["indices"][3 * r["tri"] + k] for k in range(3)]
        uv3 = [(a8[b]["uvs"][j][0], a8[b]["uvs"][j][1]) for j in tri]
        cell = tuple(r["cell"])
        q, o, _src = resolved[cell]
        pred = [G.ground_uv(p[0], p[2], cell, q, o, r["emit_family"]) for p in r["verts_f"]]
        ok = all(f32(pred[a][c]) == f32(uv3[a][c]) for a in range(3) for c in range(2))
        single += ok
        for (u, vv) in uv3:
            if not (lo_u - REGION_TOL <= u <= hi_u + REGION_TOL
                    and lo_v - REGION_TOL <= vv <= hi_v + REGION_TOL):
                out_of_region += 1
        detail.append(dict(tri=r["name"], cell=list(cell), quad=list(q), ori=o,
                           single_window_bit_exact=bool(ok),
                           uv_spread=round(F3.max_pairwise_uv(uv3), 6)))
    v["window_coherence_new_tris"] = dict(
        n_tris=len(act), single_window_reconstructed=single, multi_window=len(act) - single,
        per_tri=detail, uv_verts_out_of_dunes_mains_region=out_of_region,
        ok=(single == len(act) and out_of_region == 0))

    # (5) THE RE-CENSUS on FIXED8 -- the orphan class must be empty inside the mound ----------------
    post_carried_unc = []
    for b in touched:
        bm = M.blockmesh_from_ff9mesh(F2.terr_path(OUT, *b), disc=1, x=b[0], y=b[1], part="terrain")
        ox, oz = X.block_world_origin(*b)
        Pv, U, T = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_UV], bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            if (b, t) in S["synth_key"]:
                continue
            topo = X.decode_id(int(round(T[tri[0]][0])))["topograph"]
            fam = SNR.FAM_OF.get(topo)
            if fam is None or G.TOPO_FAMILY.get(topo) is None:
                continue
            uv = [(float(U[j][0]), float(U[j][1])) for j in tri]
            if SC.classify_tri_plus(fam, uv)[0] != "other_uncatalogued":
                continue
            w = [(float(Pv[j][0]) + ox, float(Pv[j][1]), float(Pv[j][2]) + oz) for j in tri]
            cx, cz = centroid_xz(w)
            d = donor.get(trikey(w))
            ld = dip_deg(w)
            dd = None if d is None else dip_deg(d["w"])
            post_carried_unc.append(dict(
                tri=f"({b[0]}, {b[1]})#{t}", r_crater=round(rc(cx, cz), 2),
                in_mound=(rc(cx, cz) <= MOUND_R),
                live_dip=None if ld is None else round(ld, 2),
                donor_dip=None if dd is None else round(dd, 2),
                orphaned=bool(ld is not None and ld < FLAT_DIP_T and dd is not None
                              and dd >= DONOR_DIP_T)))
    v["recensus_on_fixed8"] = dict(
        n_carried_uncatalogued=len(post_carried_unc),
        n_orphaned_remaining=sum(1 for r in post_carried_unc if r["orphaned"]),
        n_in_mound=sum(1 for r in post_carried_unc if r["in_mound"]),
        rows=post_carried_unc,
        ok=(sum(1 for r in post_carried_unc if r["orphaned"]) == 0
            and sum(1 for r in post_carried_unc if r["in_mound"]) == 0),
        note=("after the redress no orphaned decal survives anywhere in the tree, and no carried "
              "uncatalogued rect is left inside the 40u mound at all; the remainder are the lawful "
              "stock decals of stage 2c, still wearing the relief stock gave them."))

    # (6) THE SIGMA LEDGER -- the "shrinkage" the owner saw, before vs after --------------------------
    flat_sigma = []
    mound_mains_sigma = []
    mound_any_sigma = []                      # every mains-own ground tri in the mound, any family
    act_names = {r["name"] for r in act}
    for b in touched:
        bm = M.blockmesh_from_ff9mesh(F2.terr_path(OUT, *b), disc=1, x=b[0], y=b[1], part="terrain")
        ox, oz = X.block_world_origin(*b)
        Pv, U, T = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_UV], bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            topo = X.decode_id(int(round(T[tri[0]][0])))["topograph"]
            fam = G.TOPO_FAMILY.get(topo)
            if fam is None:
                continue
            w = [(float(Pv[j][0]) + ox, float(Pv[j][1]), float(Pv[j][2]) + oz) for j in tri]
            cx, cz = centroid_xz(w)
            if rc(cx, cz) > MOUND_R:
                continue
            uv = [(float(U[j][0]), float(U[j][1])) for j in tri]
            sm = sigma_max(w, uv)
            if sm is None:
                continue
            name = f"({b[0]}, {b[1]})#{t}"
            mains_own = (SC.classify_tri_plus(fam, uv)[0] == "mains_own")
            if mains_own and name not in act_names:
                mound_any_sigma.append((sm, fam, (b, t) in S["synth_key"], name))
            if fam != TARGET_FAMILY or not mains_own:
                continue
            d = dip_deg(w)
            if name not in act_names:
                mound_mains_sigma.append(sm)
            if d is not None and d < 5.0:
                flat_sigma.append(sm)
    flat_sigma.sort()
    mound_mains_sigma.sort()
    mound_any_sigma.sort()
    med = flat_sigma[len(flat_sigma) // 2] if flat_sigma else None
    before = [r["sigma_max_before"] for r in act if r["sigma_max_before"] is not None]
    after = []
    for r in act:
        b = tuple(r["block"])
        tri = [a8[b]["indices"][3 * r["tri"] + k] for k in range(3)]
        uv3 = [(a8[b]["uvs"][j][0], a8[b]["uvs"][j][1]) for j in tri]
        sm = sigma_max(r["verts_f"], uv3)
        if sm is not None:
            after.append(sm)
    ratio_after = sorted(round(s / med, 3) for s in after) if med else []
    peer_ratio = sorted(round(s / med, 3) for s in mound_mains_sigma) if med else []
    v["sigma_ledger"] = dict(
        flat_dunes_mains_baseline_median=None if med is None else round(med, 2),
        n_baseline_tris=len(flat_sigma),
        target_sigma_before=P.stats(before), target_sigma_after=P.stats(after),
        density_ratio_before=None if not med else round(med / (sum(before) / len(before)), 3),
        density_ratio_after=None if not med else round(med / (sum(after) / len(after)), 3),
        target_stretch_vs_flat_baseline_after=ratio_after,
        peer_population=dict(
            scope=f"every OTHER dunes mains-own Terrain tri inside the {MOUND_R}u mound",
            n=len(mound_mains_sigma), stretch_vs_flat_baseline=P.stats(peer_ratio),
            max_stretch=peer_ratio[-1] if peer_ratio else None,
            n_peers_above_stock_ceiling_1p41=sum(1 for x in peer_ratio if x > 1.41)),
        whole_mound_population=dict(
            scope=f"every mains-own GROUND tri of any family inside the {MOUND_R}u mound, targets excluded",
            n=len(mound_any_sigma),
            stretch_vs_flat_baseline=P.stats([round(s / med, 3) for (s, _f, _y, _n) in mound_any_sigma])
            if med else {},
            n_above_stock_ceiling_1p41=sum(1 for (s, _f, _y, _n) in mound_any_sigma
                                           if med and s / med > 1.41),
            worst_five=[dict(tri=n, family=f, synthesized=y, stretch=round(s / med, 3))
                        for (s, f, y, n) in mound_any_sigma[-5:][::-1]] if med else []),
        n_targets_above_stock_ceiling_1p41=sum(1 for x in ratio_after if x > 1.41),
        honest_edge=("THE ONE-WINDOW BLEED CLAMP -- reported, not traded away.  grassland.mains_uv "
                     "clamps a vertex that reaches outside its window's quadrant, so a triangle wider "
                     "than its own centroid cell gets its UV extent compressed and its world-per-UV "
                     "scale pushed UP.  Eight of the ten land at 1.00-1.32x the flat-sand scale -- "
                     "inside the mound's own dunes-mains population.  Two do not: (2,18)#17 at 2.10x "
                     "and (2,18)#11 at 1.97x, the widest pair (their vertices reach two cells out), "
                     "which is above stock's measured 1.41x ground ceiling AND above every other "
                     "dunes-mains tri in this mound.  This is the standing clamp behaviour every "
                     "shipped emitter has, and the same class round 7 recorded on 36 synthesized fill "
                     "tris up to 2.769x -- see whole_mound_population for this tree's own measured "
                     "spread rather than a quoted number.  Relieving it needs a per-vertex emission, "
                     "which would break THE ONE-WINDOW-PER-TRI LAW, so it is NOT done here.  Both "
                     "tris nonetheless now wear the SAME dunes sand rect as their neighbours, which "
                     "is the half of playtest 6 that named a different TEXTURE."),
        note=("sigma_max = world units per UV unit.  A ratio > 1 means the tri's texture is packed "
              "DENSER than the surrounding flat sand -- the owner's 'shrinkage'.  The redress puts "
              "the targets on the same atlas rect and the same window scale as their neighbours."))

    # (7) THE WELD -- every position, every part, byte-identical (a UV-only round must not move one)
    pre_groups = defaultdict(list)
    moved = 0
    parts_seen = Counter()
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        for part in PARTS:
            rel = M.override_relpath(1, b[0], b[1], part=part)
            p7, p8 = BASE / rel, OUT / rel
            if not p7.exists():
                continue
            parts_seen[part] += 1
            d7, d8 = M.read_ff9mesh(p7), M.read_ff9mesh(p8)
            assert d7["vcount"] == d8["vcount"], f"vcount drift in {rel}"
            for j in range(d7["vcount"]):
                a, c = d7["verts"][j], d8["verts"][j]
                pre_groups[P.pkey((a[0] + ox, a[1], a[2] + oz))].append((b, part, j))
                moved += (a != c)
    v["weld_audit"] = dict(
        n_distinct_positions_all_parts=len(pre_groups), parts_present=dict(parts_seen),
        vertex_entries_moved=moved, ok=(moved == 0),
        note=("this round writes UVs only, so not a single vertex entry may move; the weld graph is "
              "therefore trivially preserved -- audited across Terrain/Object/Beach1/Sea1..Sea5 of "
              "all 20 blocks rather than assumed."))

    # (8) THE BASIN, byte-frozen --------------------------------------------------------------------
    basin_changed = 0
    basin_entries = 0
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        d7, d8 = a7[b], a8[b]
        for t in range(len(d8["indices"]) // 3):
            tri = d8["indices"][3 * t:3 * t + 3]
            w = [(d8["verts"][j][0] + ox, d8["verts"][j][1], d8["verts"][j][2] + oz) for j in tri]
            if rc(*centroid_xz(w)) > BASIN_R:
                continue
            for j in tri:
                basin_entries += 1
                if d7["verts"][j] != d8["verts"][j] or d7["uvs"][j] != d8["uvs"][j]:
                    basin_changed += 1
    v["basin_sacred"] = dict(center=list(BASIN_C), radius_u=BASIN_R,
                             vertex_entries_inside=basin_entries,
                             pos_or_uv_bytes_changed=basin_changed, byte_frozen=(basin_changed == 0))

    report["stage7_verify"] = v
    ok = (v["flat_mesh"]["ok"] and v["uv_only"] and v["degenerate_uv_tris_all_terrain"]["ok"]
          and v["window_coherence_new_tris"]["ok"] and v["recensus_on_fixed8"]["ok"]
          and v["weld_audit"]["ok"] and v["basin_sacred"]["byte_frozen"]
          and v["tree_diff_vs_fixed7"]["exactly_the_expected_terrain_set"])
    report["ok"] = ok
    log(f"[s7] rigidity={rig}")
    log(f"[s7] tree diff={len(changed)} files (expected {len(expected)}); degenerate UV={degen}; "
        f"window coherence={single}/{len(act)}")
    log(f"[s7] re-census: orphans remaining="
        f"{v['recensus_on_fixed8']['n_orphaned_remaining']}, in-mound uncatalogued="
        f"{v['recensus_on_fixed8']['n_in_mound']}")
    log(f"[s7] sigma: flat-sand baseline={v['sigma_ledger']['flat_dunes_mains_baseline_median']} "
        f"targets before~{v['sigma_ledger']['target_sigma_before'].get('p50')} "
        f"after~{v['sigma_ledger']['target_sigma_after'].get('p50')}")
    log(f"[s7] weld moved={moved}  basin frozen={v['basin_sacred']['byte_frozen']}  OK={ok}")
    return ok


# =================================================================================================
def main():
    build_flag = "--build" in sys.argv
    report = {"meta": dict(
        script="uvf_fix8.py", round=8, read_only_vs_game=True, build_requested=build_flag,
        base_tree=str(BASE), out_tree=str(OUT), spec_tree=str(SPEC),
        playtest6=("the shaved knob area still reads as a different texture than the normal sand -- "
                   "either it's a different texture or the way it's applied is causing a shrinkage"),
        diagnosis=("both halves are one object: the five shaved knobs' 10 carried topo-41 tris wear "
                   "the stock ROCK/LICHEN outcrop rect u[0.13867,0.19922] v[0.83594,0.86621] at "
                   "sigma_max ~68-97 vs the flat-sand ~132, i.e. a different texture applied ~1.4-1.9x "
                   "denser.  In stock that pairing dresses a STEEP dune shoulder (donor dip 34.3-55.4 "
                   "deg); rounds 6-7 shaved all five flat, orphaning the decals."),
        law=("an ORPHANED DECAL -- one whose parent feature is absent at the deploy -- wears the PLAIN "
             "SURROUNDING MAINS (owner-ratified, the comp[1] round-10 precedent; round 4's hole-fill "
             "analogue).  Our shaves orphaned these, so the lawful dress is plain dunes mains."),
        lever="TEXTURE (UV-only).  No geometry byte is written this round.",
        scope_exclusions=("rock stamps (topo 58 / 31) are OUT OF SCOPE -- they keep their rock "
                          "geometry and their catalogued wall_rock UVs and never reach predicate (3); "
                          "the basin disc is byte-sacred; Sea/Object/Beach parts are untouched."),
        one_change_per_test="the only change vs FIXED7 is the 10 tris' 30 UV pairs")}

    S = stage1(report)
    donor, _sh, _dy = load_donor(report)
    act_raw, rejected, orphan = census(report, S, donor)
    census_mapwide(report, rejected, orphan)

    # normalise the act records into what the emitter needs (verts in FIXED7 order, old UVs, cell)
    act = []
    for r in act_raw:
        b = tuple(r["block"])
        bm = S["base"][b]
        ox, oz = X.block_world_origin(*b)
        tri = bm.tris[r["tri"]]
        Pv, U = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_UV]
        w = [(float(Pv[j][0]) + ox, float(Pv[j][1]), float(Pv[j][2]) + oz) for j in tri]
        uv = [(float(U[j][0]), float(U[j][1])) for j in tri]
        act.append(dict(block=b, tri=r["tri"], name=f"({b[0]}, {b[1]})#{r['tri']}",
                        verts_f=w, uv_old=uv, cell=list(own_cell(*centroid_xz(w))),
                        topo=r["topo"], r_crater=r["r_crater"],
                        sigma_max_before=sigma_max(w, uv),
                        emit_family=TARGET_FAMILY))

    field = stage3_cellfield(report, S)
    stage3b_prove_reuse(report, S, field)
    resolved = stage3c_method_a_dunes(report, S, act, field)
    non_dunes = stage4_family(report, S, act)
    for r in act:
        if non_dunes:
            # a target whose surrounding family is NOT dunes wears the family field's answer instead
            r["emit_family"] = r.get("surround_family", TARGET_FAMILY)
    stage5_preview(report, act, resolved)

    if build_flag:
        A = stage6_build(report, S, act)
        stage7_verify(report, S, act, resolved, A, donor)
    else:
        report["ok"] = None
        log("[main] probe-only (pass --build to emit FIXED8).")

    REPORT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log(f"\n{'=' * 80}\nwrote {REPORT}  ok={report.get('ok')}")
    return report


if __name__ == "__main__":
    main()
