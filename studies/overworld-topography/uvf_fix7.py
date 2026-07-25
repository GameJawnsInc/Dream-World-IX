"""RUNG F -- THE SLIVER STEP SHAVE (geometry-fix round 7, 2026-07-25).

Playtest 5 on FIXED6: round 6's four-apex shave WORKED ("they're mostly flattened") but ONE feature
survives -- "ONE sticks out in particular and has a noticeably different texture than the sand", a small
raised patch just south of an owner standing WNW of the crater.

uvf_sliver_probe.py located it and named the lever.  THIS SCRIPT IMPLEMENTS THE PROBE'S PRIMARY SPEC
VERBATIM: round 6's census with ONE new arm on predicate (3), and nothing else changed.

WHAT THE PROBE FOUND (re-derived here on FIXED6's own bytes -- no number below is copied in)
  * THE ONE is the carried topo-41 dunes TRI PAIR (1,18)#1 + (1,18)#8, apex (116.000, 6.341, -1164.000),
    r_crater 11.43u, bearing WSW.  It is the FIFTH knob of the exact family round 6 shaved four of: the
    same 2-tri form, the same uncatalogued atlas rect u[0.13867,0.19922] v[0.83594,0.86621] (sand at low
    v, a mottled rock/lichen outcrop at high v, high-v end at the knob's TOP) -- literally "a noticeably
    different texture than the sand".  Its two tris sit at dip 46.0/35.6 while its four already-shaved
    siblings now sit at 4.2..23.9.  "Mostly flattened but ONE sticks out" is byte-literal.
  * IT IS ROUND 6'S OWN NAMED NEAR-MISS.  Residual +0.863u PASSES round 6's >=0.8 gate; mesh-prominence
    +0.133u FAILS its >=0.4 gate, because the apex is only 0.133u above neighbour B -- a two-vertex
    SHOULDER/RIDGE, not a cone.  Round 6's verdict string for it was literally
    "flush-with-a-neighbour(not-a-spike)".  A STEP EDGE IS NOT A LOCAL MAXIMUM: that is the whole class.
  * THE STEP IS REAL AND IT IS BIG.  Max welded drop 2.259u over 2.09u of plan distance = 47.2 deg, into
    a fill vertex at (114.000, 4.082, -1164.609) which round 5's relax pushed 1.040u BELOW its donor
    height.  The knob did not grow; its pedestal deepened.
  * IT IS INSIDE STOCK'S SAND ENVELOPE BUT IT IS A STEP.  Stock sand (topo-41) tops out at 55.4 deg /
    2.461u span, so the geometry is not off-language; what the owner sees is a lone raised nub wearing
    a rock decal on a plan-projected mound where every sibling has been flattened.

THE CONTRACT CHANGE THIS ROUND (the only one) -- PREDICATE (3) GAINS A STEP ARM
  Round 6:  prominence >= 0.40u                                        (a strict local maximum)
  Round 7:  prominence >= 0.40u   OR   (prominence >= 0.0u AND max welded drop >= 1.50u)
  Everything else is round 6's, byte for byte: the residual gate (0.80u), the ground-family predicate
  with ROCK STAMPS (topo 58/31) EXEMPT at three levels, the sacred basin disc, the 40u mound radius, the
  Terrain-only predicate, the harmonic solve, the guards, the weld law, Y-only.  The census SELECTS
  EXACTLY ONE POSITION tree-wide and that is asserted, not hoped for.

THE TWO MARGINS THAT KEEP THE ARM HONEST (both asserted before a byte is written)
  * THE BASIN REFERENCE TRAP stays shut.  The sacred RIM CREST (14 carried vertices at Y=6.208, r<=15u)
    tops out at residual +0.657u -- 0.143u of clearance under the 0.80 gate -- PROVIDED the basin disc is
    excluded from the reference SAMPLES, not merely from the target set.  Round 6 minted that law; this
    round re-proves it and additionally asserts that no rim-crest vertex enters the spike set.
  * THE STEP ARM CANNOT REACH ANYTHING ELSE.  The only other carried position tree-wide clearing +0.80u
    is (200.000, 4.115, -1108.000): max welded drop 1.258u (< 1.50, fails the arm) AND r_crater 90.35u
    (> 40, fails predicate 4).  Double-guarded.  The next-highest carried residuals inside the mound
    (+0.789, +0.714, +0.657, +0.630, +0.603) all have NEGATIVE prominence, so the arm's prominence>=0
    floor excludes them too.

TEXTURE WAS REFUTED, NOT SKIPPED.  The probe measured stock: across the real dunes mass (18,3)-(20,3)
and the Cleyra junction (13-15,11-12), stock leaves plain family mains on 0 of 57 ground tris at
dip >= 45 deg, and its ground UV-stretch ceiling is 1.414x.  THE ONE's own UV is byte-verbatim stock
(sigma_max 73.2/72.3 = 0.55x flat, i.e. COMPRESSED, exactly like stock's own knob population at p50
80.68).  Re-clothing it in plan-projected mains would destroy correct carried vocabulary AND create the
one thing stock never does.  Refused.  (The real smear defect -- 36 near-crater tris over 1.5x, peaking
2.769x -- is 100% SYNTHESIZED FILL, lives E/NE and inside the bowl, and is a separate texture-lane job.
ONE CHANGE PER IN-GAME TEST.)

THE SOLVE is round 6's, unchanged: harmonic (Laplacian) least squares on the LOCAL patch graph --
unknowns = the spike set + the fill within HOPS=2 of it; data term dY = -residual (weight W_SPIKE on the
spikes, "hold your ground" w=1 on the fill); smoothness on every edge inside the patch; Dirichlet dY=0 on
every edge leaving it.  C0 into the pins BY CONSTRUCTION -- a distance falloff would merely RELOCATE the
step onto the pinned rim.  W_SPIKE is not hand-picked: it is the smallest of a fixed sweep for which
every spike lands within 0.15u of the rim surface and no fill vertex moves more than 0.60u.

READ-ONLY vs the game install.  Emits out/rung_f/FF9CustomMap-world-FIXED7 + uvf_fix7_report.json.
Renders nothing -- uvf_eye_relief6.py owns judgment.

    py -X utf8 uvf_fix7.py            # probe-only (census + solve dry run, writes nothing)
    py -X utf8 uvf_fix7.py --build    # emit FIXED7 + the full self-check battery
"""
from __future__ import annotations
import hashlib
import json
import math
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X                       # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import grassland as G                     # noqa: E402

import uvf_fix2 as F2                                           # noqa: E402
import uvf_fix3 as F3                                           # noqa: E402
import uvf_relief_probe as P                                    # noqa: E402

CH_POS, CH_NRM, CH_UV, CH_TAN = X.CH_POS, X.CH_NRM, X.CH_UV, X.CH_TAN

RUNG_F = HERE / "out" / "rung_f"
SPEC = RUNG_F / "FF9CustomMap-world"
BASE = RUNG_F / "FF9CustomMap-world-FIXED6"          # round 7's INPUT (round 6's output)
OUT = RUNG_F / "FF9CustomMap-world-FIXED7"           # round 7's OUTPUT
BUILD_JSON = RUNG_F / "rung_f_build.json"
FORENSICS = RUNG_F / "uvf_forensics.json"
FIX5_REPORT = RUNG_F / "uvf_fix5_report.json"        # the sacred-disc definition of record
FIX6_REPORT = RUNG_F / "uvf_fix6_report.json"        # round 6's four shaved apexes (intactness proof)
SLIVER_PROBE = RUNG_F / "uvf_sliver_probe.json"      # round 7's diagnosis (cross-check only)
REPORT = RUNG_F / "uvf_fix7_report.json"

PARTS = P.PARTS
N_FILES = 180
N_SYNTH = 2305
CELL = 4.0
SEA_Y = 0.0
MIN_LAND_Y = 0.5
AREA_EPS = 1e-9
NRM_EPS = 1e-12

# ---- THE SACRED CRATER (round 5's own basin exclusion, re-read from its report and re-asserted) ------
BASIN_C = (127.14, -1161.42)
BASIN_R = 7.92
BASIN_GUARD_R = BASIN_R + 2.0        # the frozen-annulus guard radius (nothing inside it may move)

# ---- THE CENSUS RULE (stated once, applied mechanically) --------------------------------------------
SPIKE_RES_T = 0.80        # u above the local rim reference
SPIKE_PROM_T = 0.40       # u above EVERY mesh neighbour (strict local maximum) -- round 6's CONE arm
# ---- ROUND 7's ONE CONTRACT CHANGE: the STEP arm on predicate (3) -----------------------------------
STEP_PROM_T = 0.00        # a step crest need only be no LOWER than its highest neighbour ...
STEP_DROP_T = 1.50        # ... but it must fall at least this far to its LOWEST welded neighbour
N_EXPECTED_SPIKES = 1     # the probe's spec selects EXACTLY one position tree-wide; asserted, not hoped
RIM_CREST_Y = 6.208       # the sacred crater rim crest ring
RIM_CREST_R = 15.0        # ... measured out to this radius (round 6's own instrument)
RIM_CREST_MAX_RES_T = SPIKE_RES_T   # no crest vertex may reach the residual gate -- the BASIN TRAP guard
MOUND_R = 40.0            # the crater-mound region -- the shave set lives here; beyond = report only
REPORT_RES_T = 0.60       # the looser threshold the donut/whole-tree census reports at
CLUSTER_R = P.CLUSTER_R   # 4.5u -- site grouping, same instrument as round 5
HOPS = 2                  # fill graph-hops around a spike that join the unknown set
W_SWEEP = (4.0, 8.0, 12.0, 16.0, 24.0)
W_ACCEPT_POST = 0.15      # every spike must land within this of the rim surface
W_ACCEPT_FILL = 0.60      # no fill unknown may move more than this
W_EDGE, W_HOLD, EPS = 1.0, 1.0, 1e-3

GROUND_FAM = G.TOPO_FAMILY


def log(m):
    print(m, flush=True)


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tri_geo(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    wx, wy, wz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    return (uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx)


def up_normal(a, b, c):
    nx, ny, nz = tri_geo(a, b, c)
    if ny < 0.0:
        nx, ny, nz = -nx, -ny, -nz
    ln = math.sqrt(nx * nx + ny * ny + nz * nz)
    if ln < NRM_EPS:
        return None
    return [nx / ln, ny / ln, nz / ln]


def tri_area(a, b, c):
    nx, ny, nz = tri_geo(a, b, c)
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def rc(k):
    """Plan distance from the crater centre."""
    return math.hypot(k[0] - BASIN_C[0], k[2] - BASIN_C[1])


_R6_CACHE = {}


def _round6_apexes(S):
    """The four apexes round 6 shaved, RESOLVED against FIXED6's actual position keys.

    Round 6's report records each apex's pre-move world position and its y_after.  Rather than trust a
    3-dp string to reproduce a float that has since been through a mesh write/read cycle, each apex is
    LOCATED: the carried position whose X/Z match and whose Y is nearest the recorded y_after.  A 0.01u
    tolerance is asserted, so a mislocation fails loudly instead of silently proving nothing."""
    if "keys" not in _R6_CACHE:
        r6 = json.loads(FIX6_REPORT.read_text(encoding="utf-8"))
        mv = r6["stage4_solve"]["result"]["spike_moves"]
        keys = []
        for m in mv:
            x, z, ya = m["world"][0], m["world"][2], m["y_after"]
            cand = [k for k in S["kept_ground"]
                    if abs(k[0] - x) < 1e-3 and abs(k[2] - z) < 1e-3]
            assert cand, f"round-6 apex {m['world']} has no carried position at its X/Z in FIXED6"
            best = min(cand, key=lambda k: abs(k[1] - ya))
            assert abs(best[1] - ya) < 0.01, (
                f"round-6 apex {m['world']}: FIXED6 stores Y={best[1]} but round 6 reported "
                f"y_after={ya} -- the tree is not round 6's output")
            keys.append(best)
        _R6_CACHE["keys"] = keys
        _R6_CACHE["rows"] = mv
    return _R6_CACHE["keys"]


class ExcludeHash:
    """uvf_relief_probe.Hash2D with an index blacklist -- lets P.ref_at() run its EXACT IRLS fit on a
    sample set minus the query vertex (leave-one-out) and minus the basin / the spike candidates.
    Reuses the probe's fitting machinery verbatim; only the sample membership changes."""

    def __init__(self, base, drop):
        self.base = base
        self.drop = drop
        self.cell = base.cell
        self.pts = base.pts

    def query(self, x, z, r):
        return [(i, d2) for i, d2 in self.base.query(x, z, r) if i not in self.drop]


# =================================================================================================
#  STAGE 1 -- the mesh, the position graph, the families
# =================================================================================================
def stage1(report):
    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    assert len(touched) == 20, len(touched)

    forensics = json.loads(FORENSICS.read_text(encoding="utf-8"))
    apron_keys = {(tuple(r["block"]), round(r["centroid"][0], 3), round(r["centroid"][2], 3))
                  for r in forensics["records"]
                  if r.get("uv_verdict") == "degenerate-zero-area" and r["provenance"] == "apron"}

    # The synthesized-tri classifier of record runs on the SPECIMEN's UVs (uvf_fix2/3) -- FIXED3A/4
    # CURED those UVs, so they legitimately differ downstream and cannot be the carry-over proof.  What
    # must hold for the (block, tri) identity to carry into FIXED6 is: identical INDICES, and identical
    # X/Z on every vertex entry (rounds 1-4 were UV-only, rounds 5-6 were Y-only).  Both are asserted.
    spec_meshes = F3.load_blocks(SPEC, touched)
    f5_meshes = F3.load_blocks(BASE, touched)
    uv_diff = idx_diff = xz_diff = y_diff = vcount_diff = 0
    for b in touched:
        a5 = M.read_ff9mesh(F2.terr_path(BASE, *b))
        asp = M.read_ff9mesh(F2.terr_path(SPEC, *b))
        uv_diff += (a5["uvs"] != asp["uvs"])
        idx_diff += (a5["indices"] != asp["indices"])
        vcount_diff += (a5["vcount"] != asp["vcount"])
        for j in range(min(a5["vcount"], asp["vcount"])):
            p, q = a5["verts"][j], asp["verts"][j]
            xz_diff += (p[0] != q[0] or p[2] != q[2])
            y_diff += (p[1] != q[1])
    defective, _lawful = F3.classify_defective(spec_meshes, apron_keys, touched)
    assert len(defective) == N_SYNTH, len(defective)
    synth_key = {(d["block"], d["tri"]) for d in defective}

    # --- the position graph over EVERY part, on the FIXED6 bytes ----------------------------------
    kept_ground = defaultdict(set)     # poskey -> {ground topo}
    kept_rock = defaultdict(set)       # poskey -> {non-ground topo}  (58 wall_rock, 31)
    synth_pos = set()
    parts_of = defaultdict(set)
    adj = defaultdict(set)             # poskey -> {poskey} (Terrain mesh 1-ring, kept AND synth edges)
    tri_index = defaultdict(list)      # poskey -> [(block, tri, is_synth)]
    kept_topo_hist, synth_topo_hist = Counter(), Counter()
    for b in touched:
        bm = f5_meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts, tans = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            topo = X.decode_id(int(round(tans[tri[0]][0])))["topograph"]
            is_synth = (b, t) in synth_key
            ks = [P.pkey((verts[j][0] + ox, verts[j][1], verts[j][2] + oz)) for j in tri]
            (synth_topo_hist if is_synth else kept_topo_hist)[topo] += 1
            for a in range(3):
                for c in range(3):
                    if a != c and ks[a] != ks[c]:
                        adj[ks[a]].add(ks[c])
            for k in ks:
                parts_of[k].add("Terrain")
                tri_index[k].append((b, t, is_synth))
                if is_synth:
                    synth_pos.add(k)
                elif GROUND_FAM.get(topo) is not None:
                    kept_ground[k].add(topo)
                else:
                    kept_rock[k].add(topo)
    for b in touched:
        for part in PARTS:
            if part == "Terrain":
                continue
            p = Path(BASE) / M.override_relpath(1, b[0], b[1], part=part)
            if not p.exists():
                continue
            bm = M.blockmesh_from_ff9mesh(p, disc=1, x=b[0], y=b[1], part=part.lower())
            ox, oz = X.block_world_origin(*b)
            for tri in bm.tris:
                for j in tri:
                    v = bm.chan_arrays[CH_POS][j]
                    parts_of[P.pkey((v[0] + ox, v[1], v[2] + oz))].add(part)

    fill = {k for k in synth_pos if k not in kept_ground and k not in kept_rock}
    fill_terrain_only = {k for k in fill if parts_of[k] == {"Terrain"}}

    report["stage1_mesh"] = dict(
        touched_blocks=len(touched), n_synthesized_tris=len(defective),
        base_tree=BASE.name,
        spec_vs_base=dict(
            uv_files_differing=uv_diff, index_files_differing=idx_diff, vcount_files_differing=vcount_diff,
            vertex_entries_with_XZ_differing=xz_diff, vertex_entries_with_Y_differing=y_diff,
            reading=("UV files DO differ -- that is FIXED3A's one-window cure plus round 4's family "
                     "re-clothe, and it is why the SPEC's degenerate UVs remain the classifier of "
                     "record.  The carry-over proof is instead: 0 index differences and 0 X/Z "
                     "differences, so (block, tri) means the same triangle in both trees; the Y "
                     "differences are exactly round 5's relief relax plus round 6's four-apex shave.")),
        classifier_carries_over=(idx_diff == 0 and xz_diff == 0 and vcount_diff == 0),
        kept_tri_topo_hist=dict(sorted(kept_topo_hist.items())),
        synth_tri_topo_hist=dict(sorted(synth_topo_hist.items())),
        n_distinct_positions_all_parts=len(parts_of),
        n_carried_ground_positions=len(kept_ground),
        n_carried_rock_positions=len(kept_rock),
        n_fill_positions=len(fill),
        n_fill_positions_terrain_only=len(fill_terrain_only),
        carried_ground_topo_hist=dict(sorted(Counter(t for s in kept_ground.values()
                                                     for t in s).items())),
        carried_rock_topo_hist=dict(sorted(Counter(t for s in kept_rock.values() for t in s).items())),
        note=("CARRIED GROUND = a position touched by a kept Terrain tri whose topograph has a ground "
              "family (grassland.TOPO_FAMILY: grass/desert/dunes).  CARRIED ROCK = touched by a kept "
              "tri with NO ground family (58 wall_rock, 31) and by no ground tri -- the topo-58 "
              "frame-mint rock outcrops, lawful stock island decoration, EXEMPT from every stage.  "
              "FILL = touched only by synthesized tris.  Key = 3D position @3dp (same XZ + different Y "
              "is a wall, not a weld)."))
    log(f"[s1] synth {len(defective)} tris; positions: carried-ground {len(kept_ground)} "
        f"carried-rock {len(kept_rock)} fill {len(fill)} (Terrain-only {len(fill_terrain_only)})")
    return dict(touched=touched, f5=f5_meshes, synth_key=synth_key, defective=defective,
                kept_ground=kept_ground, kept_rock=kept_rock, fill=fill,
                fill_terrain_only=fill_terrain_only, parts_of=parts_of, adj=adj,
                tri_index=tri_index, synth_pos=synth_pos)


# =================================================================================================
#  STAGE 2 -- the local rim reference (leave-one-out, basin-excluded, candidate-excluded)
# =================================================================================================
def stage2(report, S):
    fix5 = json.loads(FIX5_REPORT.read_text(encoding="utf-8"))
    disc = fix5["scope"]["basin_exclusion"]["exclusion_discs"][0]
    assert abs(disc["center"][0] - BASIN_C[0]) < 1e-6 and abs(disc["center"][1] - BASIN_C[1]) < 1e-6, disc
    assert abs(disc["radius_u"] - BASIN_R) < 1e-6, disc

    sample_keys = sorted(set(S["kept_ground"]) | S["fill"])
    samples = np.array([[k[0], k[1], k[2]] for k in sample_keys], dtype=float)
    idx_of = {k: i for i, k in enumerate(sample_keys)}
    base = P.Hash2D(samples, cell=8.0)
    basin_keys = {k for k in sample_keys if rc(k) <= BASIN_R}
    basin_idx = frozenset(idx_of[k] for k in basin_keys)

    def census(drop_extra):
        out, diag = {}, {}
        for k in sample_keys:
            y, d = P.ref_at(ExcludeHash(base, basin_idx | {idx_of[k]} | drop_extra), samples,
                            k[0], k[2])
            out[k] = None if y is None else k[1] - y
            diag[k] = (y, d)
        return out, diag

    res_a, _ = census(frozenset())
    cand_a = {k for k, v in res_a.items() if v is not None and v >= SPIKE_RES_T}
    res, diag = census(frozenset(idx_of[k] for k in cand_a))

    # --- the trap this round exists to avoid, MEASURED both ways ----------------------------------
    def census_contaminated():
        out = {}
        for k in sample_keys:
            y, _ = P.ref_at(ExcludeHash(base, {idx_of[k]}), samples, k[0], k[2])
            out[k] = None if y is None else k[1] - y
        return out
    res_contam = census_contaminated()
    rim_ring = sorted([k for k in S["kept_ground"]
                       if abs(k[1] - RIM_CREST_Y) < 1e-3 and rc(k) <= RIM_CREST_R],
                      key=lambda k: -res_contam[k])
    rim_max_res = max((res[k] for k in rim_ring if res[k] is not None), default=None)

    report["stage2_reference"] = dict(
        n_sample_positions=len(sample_keys),
        n_carried_ground_samples=len(S["kept_ground"]), n_fill_samples=len(S["fill"]),
        basin_disc=dict(center=list(BASIN_C), radius_u=BASIN_R),
        n_samples_excluded_as_basin=len(basin_keys),
        basin_excluded_split=dict(carried=sum(1 for k in basin_keys if k in S["kept_ground"]),
                                  fill=sum(1 for k in basin_keys if k in S["fill"])),
        n_pass_a_candidates=len(cand_a),
        rock_positions_never_sampled=len(S["kept_rock"]),
        residual_all=P.stats([v for v in res.values() if v is not None]),
        THE_BASIN_REFERENCE_TRAP=dict(
            finding=("with the basin bowl IN the sample set, the crater's own carried RIM CREST -- a "
                     "broad ring at exactly Y=6.208, r=8.9-11.5u -- reads as spikes; shaving them "
                     "would destroy the feature the owner likes.  Excluding the sacred disc from the "
                     "SAMPLES (not merely from the shave set) is what makes the census safe.  The two "
                     "stat blocks below are the same 14 crest vertices measured both ways."),
            rim_ring_n=len(rim_ring),
            rim_ring_residual_with_basin_sampled=P.stats([res_contam[k] for k in rim_ring]),
            rim_ring_residual_basin_excluded=P.stats([res[k] for k in rim_ring]),
            rim_ring_qualifying_at_0p8_with_basin_sampled=sum(1 for k in rim_ring
                                                              if res_contam[k] >= SPIKE_RES_T),
            rim_ring_qualifying_at_0p8_basin_excluded=sum(1 for k in rim_ring
                                                          if res[k] >= SPIKE_RES_T),
            rim_ring_max_residual_basin_excluded=(None if rim_max_res is None
                                                  else round(rim_max_res, 4)),
            rim_ring_clearance_under_the_gate=(None if rim_max_res is None
                                               else round(SPIKE_RES_T - rim_max_res, 4)),
            round7_note=("round 7 WIDENS predicate (3), which is exactly the predicate that used to "
                         "protect the crest ring by shape.  The residual gate is therefore now the "
                         "ONLY thing standing between the census and the crater the owner likes, so "
                         "this clearance is promoted to a hard STOP GUARD: if any crest vertex reaches "
                         f"{RIM_CREST_MAX_RES_T}u the round refuses to build.")),
        method=("uvf_relief_probe.ref_at VERBATIM (IDW least-squares plane over a growing 8/12/18/26u "
                "radius + two Tukey-biweight IRLS passes) on a sample set of CARRIED GROUND + FILL "
                "positions, minus (a) the sacred basin disc, (b) the query position itself "
                "(leave-one-out -- without it a lone apex fits its own plane and hides), and (c) on the "
                "second pass every pass-A candidate.  Rock abstains at the source."),
        sign_convention="residual = Y minus the local rim reference (positive = sits ABOVE)")
    log(f"[s2] reference: {len(sample_keys)} samples ({len(basin_keys)} basin-excluded); pass-A "
        f"candidates {len(cand_a)}; rim-ring qualifying {sum(1 for k in rim_ring if res_contam[k]>=0.8)}"
        f" -> {sum(1 for k in rim_ring if res[k]>=0.8)} once the basin is out of the samples")
    return dict(sample_keys=sample_keys, samples=samples, idx_of=idx_of, base=base,
                basin_keys=basin_keys, basin_idx=basin_idx, res=res, diag=diag,
                res_contam=res_contam, cand_a=cand_a, rim_ring=rim_ring, rim_max_res=rim_max_res)


# =================================================================================================
#  STAGE 3 -- THE SPIKE CENSUS
# =================================================================================================
def stage3(report, S, R):
    res, adj = R["res"], S["adj"]
    kept_ground, kept_rock, fill = S["kept_ground"], S["kept_rock"], S["fill"]
    parts_of = S["parts_of"]

    prom, drop, slope = {}, {}, {}
    for k in R["sample_keys"]:
        nb = adj.get(k, ())
        prom[k] = (k[1] - max((n[1] for n in nb), default=-1e9)) if nb else None
        # THE STEP ARM's second number: how far this position falls to its LOWEST welded neighbour,
        # and the steepest welded slope that fall implies.  A cone has a big prominence; a STEP CREST
        # has ~zero prominence and a big drop -- which is precisely why round 6's predicate missed it.
        drop[k] = (k[1] - min((n[1] for n in nb), default=1e9)) if nb else None
        best = 0.0
        for n in nb:
            run = math.hypot(k[0] - n[0], k[2] - n[2])
            if run > 1e-6:
                best = max(best, math.degrees(math.atan2(abs(k[1] - n[1]), run)))
        slope[k] = best if nb else None

    donor = P.load_donor(report)          # dropped-topo-49 cells == the former root-wedge footprint
    cells49 = donor["cells49"]

    def cell_of(k):
        return (math.floor(k[0] / CELL), math.floor(k[2] / CELL))

    def arm_of(k):
        """Which arm of predicate (3), if any, this position satisfies.  CONE = round 6's rule; STEP =
        round 7's one new arm.  Reported on EVERY row so the widening is auditable, not just on hits."""
        p, d = prom.get(k), drop.get(k)
        if p is None or d is None:
            return None
        if p >= SPIKE_PROM_T:
            return "CONE"
        if p >= STEP_PROM_T and d >= STEP_DROP_T:
            return "STEP"
        return None

    def row(k, kind):
        return dict(k=list(k), kind=kind, y=round(k[1], 4),
                    ref=round(k[1] - res[k], 4) if res.get(k) is not None else None,
                    res=round(res[k], 4) if res.get(k) is not None else None,
                    prom=round(prom[k], 4) if prom.get(k) is not None else None,
                    drop=round(drop[k], 4) if drop.get(k) is not None else None,
                    slope_deg=round(slope[k], 2) if slope.get(k) is not None else None,
                    arm=arm_of(k),
                    r_crater=round(rc(k), 2), deg=len(adj.get(k, ())),
                    neighbour_y=sorted((round(n[1], 3) for n in adj.get(k, ())), reverse=True),
                    topo=sorted(kept_ground.get(k, kept_rock.get(k, set()))),
                    parts=sorted(parts_of[k]),
                    in_wedge_donut=bool(cell_of(k) in cells49),
                    also_touched_by_fill=bool(k in S["synth_pos"]))

    # --- THE RULE (five predicates, no hand-picking; predicate 3 is the round's ONE change) ---------
    def classify(k):
        if k in kept_rock:
            return "rock-stamp-EXEMPT"
        if k not in kept_ground:
            return "fill"
        if res.get(k) is None:
            return "unscored"
        if res[k] < SPIKE_RES_T:
            return "below-residual-threshold"
        if arm_of(k) is None:
            return ("flush-with-a-neighbour-and-no-step(not-a-spike)"
                    if (prom.get(k) is not None and prom[k] >= STEP_PROM_T)
                    else "below-a-neighbour(not-a-spike)")
        if rc(k) <= BASIN_R:
            return "inside-the-sacred-basin(refused)"
        if parts_of[k] != {"Terrain"}:
            return "shared-with-a-non-Terrain-part(refused)"
        if rc(k) > MOUND_R:
            return "outside-the-crater-mound(report-only)"
        return f"SPIKE-{arm_of(k)}"

    verdicts = {k: classify(k) for k in set(kept_ground) | set(kept_rock)}
    spikes = sorted([k for k, v in verdicts.items() if v.startswith("SPIKE")], key=lambda k: -res[k])

    # --- the honest census: everything the looser reporting threshold sees, everywhere -------------
    carried_reported = sorted([k for k in kept_ground
                               if res.get(k) is not None and res[k] >= REPORT_RES_T],
                              key=lambda k: -res[k])
    fill_reported = sorted([k for k in fill if res.get(k) is not None and res[k] >= REPORT_RES_T],
                           key=lambda k: -res[k])
    rock_reported = []
    for k in kept_rock:
        y, _ = P.ref_at(ExcludeHash(R["base"], R["basin_idx"]), R["samples"], k[0], k[2])
        if y is not None and k[1] - y >= REPORT_RES_T:
            rock_reported.append((k, k[1] - y))
    rock_reported.sort(key=lambda t: -t[1])

    # --- sites (proximity grouping, same instrument as round 5) ------------------------------------
    sites = []
    unassigned = list(spikes)
    while unassigned:
        seed = unassigned.pop(0)
        grp = [seed]
        for k in list(unassigned):
            if math.hypot(k[0] - seed[0], k[2] - seed[2]) <= CLUSTER_R:
                grp.append(k)
                unassigned.remove(k)
        peak = max(grp, key=lambda k: res[k])
        ring = sorted({n for k in grp for n in adj[k]} - set(grp), key=lambda n: -n[1])
        sites.append(dict(
            n_positions=len(grp),
            peak_world=[round(peak[0], 3), round(peak[1], 3), round(peak[2], 3)],
            peak_residual_u=round(res[peak], 3), peak_prominence_u=round(prom[peak], 3),
            peak_drop_u=round(drop[peak], 3), peak_slope_deg=round(slope[peak], 2),
            peak_arm=arm_of(peak),
            local_reference_y=round(peak[1] - res[peak], 3),
            r_crater=round(rc(peak), 2),
            topo=sorted(kept_ground[peak]),
            neighbour_ring_y=[round(n[1], 3) for n in ring],
            neighbour_ring_kind=["carried" if n in kept_ground else
                                 ("rock" if n in kept_rock else "fill") for n in ring],
            kept_tris=[f"{b}#{t}" for k in grp for (b, t, sy) in S["tri_index"][k] if not sy],
            synth_tris=sum(1 for k in grp for (b, t, sy) in S["tri_index"][k] if sy),
            in_wedge_donut=bool(cell_of(peak) in cells49),
            positions=[row(k, "carried-ground") for k in grp]))
    sites.sort(key=lambda s: -s["peak_residual_u"])

    res_qualified = [k for k in kept_ground if res.get(k) is not None and res[k] >= SPIKE_RES_T]
    rim_ring = R["rim_ring"]
    report["stage3_spike_census"] = dict(
        rule=dict(
            residual_threshold_u=SPIKE_RES_T,
            cone_arm_prominence_threshold_u=SPIKE_PROM_T,
            step_arm_prominence_threshold_u=STEP_PROM_T,
            step_arm_drop_threshold_u=STEP_DROP_T,
            mound_radius_u=MOUND_R, basin_radius_u=BASIN_R,
            statement=("a SPIKE is a CARRIED position that (1) has a ground family topograph -- rock "
                       f"stamps (58/31) are exempt outright; (2) sits >= {SPIKE_RES_T}u above the local "
                       "rim reference; (3) satisfies EITHER arm -- CONE: it is a strict local maximum, "
                       f">= {SPIKE_PROM_T}u above EVERY mesh vertex it is welded to (round 6's rule); "
                       f"or STEP: it is no lower than its highest welded neighbour (>= {STEP_PROM_T}u) "
                       f"AND falls >= {STEP_DROP_T}u to its lowest welded neighbour (round 7's one new "
                       "arm); (4) lies outside the sacred basin disc and inside the "
                       f"{MOUND_R}u crater-mound region; (5) has all its vertex entries in the Terrain "
                       "part (a position shared with Object/Beach/Sea would demand a cross-part move "
                       "and is refused)."),
            round7_change=("predicate (3) ONLY.  Round 6 required a strict local maximum, which by "
                           "construction cannot see a STEP EDGE -- a shoulder/ridge crest whose "
                           "prominence is ~0 because one neighbour is level with it, while the other "
                           "side falls away 2m+.  That is the class the sliver probe found, and it is "
                           "the class the render's bright lens/leaf faces belong to.  Nothing else in "
                           "the rule, the solve, the guards or the weld law changed.")),
        verdict_hist=dict(sorted(Counter(verdicts.values()).items())),
        n_spikes=len(spikes), n_sites=len(sites), sites=sites,
        arm_hist=dict(sorted(Counter(arm_of(k) or "none" for k in spikes).items())),
        margin=dict(
            min_residual_in_set=round(min(res[k] for k in spikes), 3) if spikes else None,
            min_prominence_in_set=round(min(prom[k] for k in spikes), 3) if spikes else None,
            min_drop_in_set=round(min(drop[k] for k in spikes), 3) if spikes else None,
            n_carried_positions_clearing_the_residual_gate=len(res_qualified),
            residual_qualified_rejects=[row(k, "carried-ground") for k in
                                        sorted((k for k in res_qualified if k not in spikes),
                                               key=lambda k: -res[k])],
            best_drop_among_residual_qualified_rejects=round(
                max((drop[k] for k in res_qualified if k not in spikes), default=float("nan")), 3),
            best_residual_among_step_qualified_rejects=round(
                max((res[k] for k in kept_ground
                     if arm_of(k) == "STEP" and k not in spikes), default=float("nan")), 3),
            THE_BASIN_TRAP_MARGIN=dict(
                rim_crest_n=len(rim_ring),
                rim_crest_max_residual=(None if R["rim_max_res"] is None
                                        else round(R["rim_max_res"], 4)),
                residual_gate=SPIKE_RES_T,
                clearance=(None if R["rim_max_res"] is None
                           else round(SPIKE_RES_T - R["rim_max_res"], 4)),
                n_rim_crest_vertices_in_spike_set=sum(1 for k in rim_ring if k in set(spikes)),
                n_rim_crest_vertices_passing_an_arm=sum(1 for k in rim_ring
                                                        if arm_of(k) is not None),
                why=("round 7 widened predicate (3), so a rim-crest vertex that used to be excluded "
                     "BY SHAPE could now pass an arm.  The residual gate is what still excludes it, "
                     "and that gate only holds because the sacred disc is out of the reference "
                     "SAMPLES.  Both facts are re-measured every run and both are STOP GUARDS.")),
            note=("the arm is narrow by measurement, not by hope: every carried position tree-wide "
                  "that clears the residual gate is listed in residual_qualified_rejects with its own "
                  "prominence/drop/arm, so the reader can see exactly what the widening did and did "
                  "not admit.")),
        near_misses=[row(k, "carried-ground") for k in carried_reported
                     if k not in spikes and res[k] >= SPIKE_RES_T],
        round6_carryover=dict(
            n_moved_by_round6=len(_round6_apexes(S)),
            still_qualifying_now=[row(k, "carried-ground") for k in _round6_apexes(S)
                                  if k in set(spikes)],
            note=("the four apexes round 6 shaved, re-classified under round 7's WIDER rule on "
                  "FIXED6's own bytes.  None may qualify again -- if one did, round 6 under-shaved "
                  "and this round would be re-cutting approved geometry.")),
        whole_tree_carried_census=dict(
            threshold_u=REPORT_RES_T, n=len(carried_reported),
            in_wedge_donut=sum(1 for k in carried_reported if cell_of(k) in cells49),
            within_mound=sum(1 for k in carried_reported if rc(k) <= MOUND_R),
            rows=[row(k, "carried-ground") for k in carried_reported]),
        whole_tree_fill_census=dict(
            threshold_u=REPORT_RES_T, n=len(fill_reported),
            rows=[row(k, "fill") for k in fill_reported][:40]),
        rock_stamp_census=dict(
            n_rock_positions=len(kept_rock),
            topo_hist=dict(sorted(Counter(t for s in kept_rock.values() for t in s).items())),
            n_within_mound=sum(1 for k in kept_rock if rc(k) <= MOUND_R),
            n_above_reporting_threshold=len(rock_reported),
            rows=[dict(world=[round(k[0], 2), round(k[1], 3), round(k[2], 2)], res=round(v, 3),
                       topo=sorted(kept_rock[k]), r_crater=round(rc(k), 1))
                  for k, v in rock_reported[:20]],
            handling=("EXEMPT at three levels: never a reference sample (their near-vertical faces "
                      "would tilt the local plane), never a census candidate, and any position they "
                      "touch is refused as a spike.  They are lawful stock island decoration.")),
        wedge_donut=dict(
            definition="cells whose donor window DROPPED topo-49 (the Cleyra mural/root strips)",
            n_cells=len(cells49),
            n_carried_ground_positions_in_donut=sum(1 for k in kept_ground if cell_of(k) in cells49),
            n_spikes_in_donut=sum(1 for k in spikes if cell_of(k) in cells49)))
    log(f"[s3] SPIKE SET = {len(spikes)} positions in {len(sites)} sites; verdicts "
        f"{dict(sorted(Counter(verdicts.values()).items()))}")
    for s in sites:
        log(f"     site [{s['peak_arm']}] peak Y={s['peak_world'][1]:.3f} res={s['peak_residual_u']:+.3f} "
            f"prom={s['peak_prominence_u']:+.3f} drop={s['peak_drop_u']:.3f} "
            f"slope={s['peak_slope_deg']} r={s['r_crater']} topo={s['topo']} "
            f"ring={s['neighbour_ring_y']}")
    log(f"[s3] rim-crest margin: max residual {R['rim_max_res']:.4f} vs gate {SPIKE_RES_T} "
        f"(clearance {SPIKE_RES_T - R['rim_max_res']:.4f}); crest vertices in the spike set "
        f"{sum(1 for k in rim_ring if k in set(spikes))}")
    return dict(spikes=spikes, prom=prom, drop=drop, slope=slope, arm_of=arm_of, sites=sites,
                verdicts=verdicts, cells49=cells49, cell_of=cell_of, rim_ring=rim_ring)


# =================================================================================================
#  STAGE 4 -- the harmonic solve on the spike patch
# =================================================================================================
def stage4(report, S, R, C):
    res, adj, fill = R["res"], S["adj"], S["fill_terrain_only"]
    spikes = C["spikes"]

    # --- unknowns: the spikes + the fill within HOPS of them (never a carried non-spike, never the
    #     basin, never a position shared with a non-Terrain part) -----------------------------------
    U = set(spikes)
    frontier = set(spikes)
    hop_of = {k: 0 for k in spikes}
    for h in range(1, HOPS + 1):
        nxt = set()
        for k in frontier:
            for n in adj[k]:
                if n in fill and n not in U and rc(n) > BASIN_GUARD_R:
                    nxt.add(n)
                    hop_of[n] = h
        U |= nxt
        frontier = nxt
    Ul = sorted(U)
    uidx = {k: i for i, k in enumerate(Ul)}
    n = len(Ul)

    edges = set()
    for k in Ul:
        for nb in adj[k]:
            edges.add((min(k, nb), max(k, nb)))
    e_uu = [(uidx[a], uidx[b]) for a, b in edges if a in uidx and b in uidx]
    e_ub = ([uidx[a] for a, b in edges if a in uidx and b not in uidx]
            + [uidx[b] for a, b in edges if b in uidx and a not in uidx])

    def solve(w_spike):
        A = np.zeros((n + len(e_uu) + len(e_ub) + n, n))
        rhs = np.zeros(A.shape[0])
        r0 = 0
        for k in Ul:                                   # data term
            w = w_spike if k in set(spikes) else W_HOLD
            A[r0, uidx[k]] = w
            rhs[r0] = -w * res[k]
            r0 += 1
        for i, j in e_uu:                              # smoothness inside the patch
            A[r0, i], A[r0, j] = W_EDGE, -W_EDGE
            r0 += 1
        for i in e_ub:                                 # Dirichlet dY=0 on every edge leaving it
            A[r0, i] = W_EDGE
            r0 += 1
        for i in range(n):                             # keeps isolated unknowns at 0
            A[r0, i] = EPS
            r0 += 1
        dY, *_ = np.linalg.lstsq(A, rhs, rcond=None)
        return {Ul[i]: float(dY[i]) for i in range(n) if abs(dY[i]) > 1e-4}

    sweep = []
    chosen = None
    for w in W_SWEEP:
        mv = solve(w)
        post = [abs(res[k] + mv.get(k, 0.0)) for k in spikes]
        fdy = [abs(v) for k, v in mv.items() if k not in set(spikes)]
        ok = (max(post, default=0.0) <= W_ACCEPT_POST and max(fdy, default=0.0) <= W_ACCEPT_FILL)
        sweep.append(dict(w_spike=w, max_post_abs_residual=round(max(post, default=0.0), 4),
                          max_fill_abs_dY=round(max(fdy, default=0.0), 4),
                          spike_dY=[round(mv.get(k, 0.0), 4) for k in spikes], accepted=ok))
        if ok and chosen is None:
            chosen = (w, mv)
    assert chosen is not None, "no sweep weight satisfied the acceptance rule"
    w_spike, moved = chosen

    report["stage4_solve"] = dict(
        unknowns=dict(n=n, spikes=len(spikes), fill=n - len(spikes), hops=HOPS,
                      fill_hop_hist=dict(sorted(Counter(hop_of[k] for k in Ul if k not in
                                                        set(spikes)).items())),
                      min_r_crater_of_a_fill_unknown=round(min((rc(k) for k in Ul
                                                                if k not in set(spikes)),
                                                               default=float("nan")), 2),
                      carried_non_spike_unknowns=0,
                      construction=("unknowns = the spike set + fill positions within "
                                    f"{HOPS} mesh hops of a spike, minus anything inside "
                                    f"{BASIN_GUARD_R}u of the basin centre and minus any fill position "
                                    "with a vertex entry outside Terrain.  A carried non-spike position "
                                    "can never enter the set BY CONSTRUCTION -- only fill is expanded "
                                    "into.")),
        graph=dict(patch_edges=len(e_uu), edges_to_pinned=len(e_ub)),
        weights=dict(sweep_grid=list(W_SWEEP), chosen_w_spike=w_spike, w_hold=W_HOLD,
                     w_edge=W_EDGE, eps=EPS,
                     selection_rule=(f"the SMALLEST sweep weight for which every spike lands within "
                                     f"{W_ACCEPT_POST}u of the rim surface AND no fill unknown moves "
                                     f"more than {W_ACCEPT_FILL}u"),
                     sweep=sweep),
        result=dict(
            n_moved=len(moved),
            spike_moves=[dict(world=[round(k[0], 3), round(k[1], 3), round(k[2], 3)],
                              res_before=round(res[k], 3), dY=round(moved.get(k, 0.0), 3),
                              y_after=round(k[1] + moved.get(k, 0.0), 3),
                              res_after=round(res[k] + moved.get(k, 0.0), 3),
                              reference_y=round(k[1] - res[k], 3),
                              r_crater=round(rc(k), 2)) for k in spikes],
            fill_moves=[dict(world=[round(k[0], 3), round(k[1], 3), round(k[2], 3)],
                             hop=hop_of[k], dY=round(v, 4), res_before=round(res[k], 3),
                             res_after=round(res[k] + v, 3), r_crater=round(rc(k), 2))
                        for k, v in sorted(moved.items(), key=lambda kv: -abs(kv[1]))
                        if k not in set(spikes)],
            dY=P.stats(list(moved.values())),
            max_abs_dY=round(max(abs(v) for v in moved.values()), 4) if moved else 0.0,
            all_spike_moves_are_downward=all(moved.get(k, 0.0) < 0 for k in spikes)),
        method=("harmonic (Laplacian) least squares on the local patch graph -- data term dY=-residual "
                "(w=w_spike on the spikes, w=1 'hold your ground' on the fill), smoothness on every "
                "patch edge, Dirichlet dY=0 on every edge to a pinned position.  THE MESH-FUNCTION "
                "BLEND: C0 into the pinned rim by construction.  A distance falloff would pull a ring "
                "vertex without knowing the pin behind it and merely RELOCATE the step -- round 5's "
                "lesson, unchanged."))
    log(f"[s4] unknowns {n} ({len(spikes)} spike + {n - len(spikes)} fill), {len(e_uu)} patch edges, "
        f"{len(e_ub)} pin edges; w_spike={w_spike} -> moved {len(moved)}, max|dY|="
        f"{max(abs(v) for v in moved.values()):.4f}")
    return dict(moved=moved, Ul=Ul, w_spike=w_spike, hop_of=hop_of, e_uu=e_uu, e_ub=e_ub)


# =================================================================================================
#  STAGE 5 -- THE STOP GUARDS (checked BEFORE a byte is written)
# =================================================================================================
def stage_guards(report, S, R, C, Q):
    g = {}
    moved, spikes = Q["moved"], set(C["spikes"])
    res = R["res"]

    g["n_synthesized_tris"] = len(S["defective"])
    g["synth_tris_is_2305"] = (len(S["defective"]) == N_SYNTH)
    g["classifier_carries_over"] = report["stage1_mesh"]["classifier_carries_over"]

    g["n_spikes"] = len(spikes)
    g["n_moved"] = len(moved)
    g["moved_subset_of_unknowns"] = not (set(moved) - set(Q["Ul"]))

    # (0) ROUND 7's OWN GUARDS -- the widening must select the probe's ONE position and nothing else.
    g["n_expected_spikes"] = N_EXPECTED_SPIKES
    g["census_selects_expected_count"] = (len(spikes) == N_EXPECTED_SPIKES)
    g["spike_arms"] = dict(sorted(Counter(C["arm_of"](k) or "none" for k in spikes).items()))
    g["every_spike_passes_an_arm"] = all(C["arm_of"](k) is not None for k in spikes)
    # THE BASIN REFERENCE TRAP, promoted to a guard now that predicate (3) no longer protects the crest
    g["rim_crest_n"] = len(C["rim_ring"])
    g["rim_crest_max_residual"] = (None if R["rim_max_res"] is None else round(R["rim_max_res"], 4))
    g["rim_crest_clear_of_the_residual_gate"] = bool(
        R["rim_max_res"] is not None and R["rim_max_res"] < RIM_CREST_MAX_RES_T)
    g["rim_crest_vertices_in_spike_set"] = sum(1 for k in C["rim_ring"] if k in spikes)
    g["rim_crest_excluded"] = (g["rim_crest_vertices_in_spike_set"] == 0)
    # round 6's approved work may not be re-cut by the wider rule
    r6 = set(_round6_apexes(S))
    g["round6_apexes_reselected"] = len(r6 & spikes)
    g["round6_apexes_not_reselected"] = (len(r6 & spikes) == 0)

    # (1) EVERY carried position outside the spike set must be frozen -- the round's whole contract.
    carried_moved = {k: v for k, v in moved.items()
                     if (k in S["kept_ground"] or k in S["kept_rock"]) and k not in spikes}
    g["carried_non_spike_positions_moved"] = len(carried_moved)
    g["carried_non_spike_frozen"] = (len(carried_moved) == 0)
    g["rock_positions_moved"] = sum(1 for k in moved if k in S["kept_rock"])
    g["rock_stamps_frozen"] = (g["rock_positions_moved"] == 0)

    # (2) THE BASIN.  Nothing inside the sacred disc (nor its guard annulus) may move.
    basin_moved = [k for k in moved if rc(k) <= BASIN_R]
    guard_moved = [k for k in moved if rc(k) <= BASIN_GUARD_R]
    g["basin_disc_positions_total"] = len(R["basin_keys"])
    g["basin_disc_positions_moved"] = len(basin_moved)
    g["basin_guard_annulus_radius_u"] = BASIN_GUARD_R
    g["basin_guard_positions_moved"] = len(guard_moved)
    g["basin_frozen"] = (not basin_moved and not guard_moved)
    g["min_r_crater_of_a_moved_position"] = round(min((rc(k) for k in moved), default=float("nan")), 3)

    # (3) THE SHAVE MUST BE A SHAVE.  Down only, and never past the rim surface.
    g["all_spike_moves_downward"] = all(moved.get(k, 0.0) < 0 for k in spikes)
    post = [res[k] + moved.get(k, 0.0) for k in spikes]
    g["spike_post_residual_max"] = round(max(post), 4) if post else None
    g["spike_post_residual_min"] = round(min(post), 4) if post else None
    g["no_overshave"] = all(p >= -W_ACCEPT_POST for p in post)
    g["shave_reaches_surface"] = all(abs(p) <= W_ACCEPT_POST for p in post)

    # (4) welds + parts: every moved position must be Terrain-only (no cross-part move is planned).
    g["moved_positions_outside_terrain"] = sum(1 for k in moved if S["parts_of"][k] != {"Terrain"})
    g["moved_terrain_only"] = (g["moved_positions_outside_terrain"] == 0)

    # (5) land clearance
    newY = [k[1] + v for k, v in moved.items()]
    g["predicted_min_Y_after"] = round(min(newY), 4) if newY else None
    g["sea_clearance_ok"] = bool(not newY or min(newY) > MIN_LAND_Y)
    g["predicted_max_abs_dY"] = round(max(abs(v) for v in moved.values()), 4) if moved else 0.0

    g["all_pass"] = bool(g["synth_tris_is_2305"] and g["classifier_carries_over"]
                         and g["moved_subset_of_unknowns"] and g["carried_non_spike_frozen"]
                         and g["rock_stamps_frozen"] and g["basin_frozen"]
                         and g["all_spike_moves_downward"] and g["no_overshave"]
                         and g["shave_reaches_surface"] and g["moved_terrain_only"]
                         and g["sea_clearance_ok"] and len(spikes) > 0
                         and g["census_selects_expected_count"] and g["every_spike_passes_an_arm"]
                         and g["rim_crest_clear_of_the_residual_gate"] and g["rim_crest_excluded"]
                         and g["round6_apexes_not_reselected"])
    report["stop_guards"] = g
    log(f"[guards] {json.dumps({k: v for k, v in g.items() if k != 'all_pass'})}")
    log(f"[guards] ALL_PASS={g['all_pass']}")
    return g["all_pass"]


# =================================================================================================
#  STAGE 6 -- APPLY
# =================================================================================================
def stage_apply(report, S, Q):
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(BASE, OUT)
    n_copied = sum(1 for p in OUT.rglob("*") if p.is_file())
    assert n_copied == N_FILES, f"copy mismatch {n_copied} != {N_FILES}"
    log(f"[apply] copied {n_copied} files -> {OUT}")

    touched, synth_key, moved = S["touched"], S["synth_key"], Q["moved"]
    meshes = F3.load_blocks(OUT, touched)

    # PASS 1 -- resolve every Terrain vertex entry (KEPT AND SYNTHESIZED: this round moves carried
    # geometry, so the scan can no longer be restricted to the synthesized tris) against the PRE-move
    # position key.
    plan = {b: {} for b in touched}
    moved_tris = {b: set() for b in touched}
    moved_tris_kept = {b: set() for b in touched}
    per_block_pos = defaultdict(set)
    entries_per_pos = Counter()
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[CH_POS]
        for t, tri in enumerate(bm.tris):
            hit = False
            for j in tri:
                v = verts[j]
                k = P.pkey((v[0] + ox, v[1], v[2] + oz))
                dy = moved.get(k)
                if dy is not None:
                    plan[b][j] = dy
                    per_block_pos[k].add(b)
                    entries_per_pos[k] += 1
                    hit = True
            if hit:
                moved_tris[b].add(t)
                if (b, t) not in synth_key:
                    moved_tris_kept[b].add(t)
    missing = set(moved) - set(per_block_pos)
    assert not missing, f"{len(missing)} solved positions not located in the mesh -- key mismatch"

    # PASS 2 -- the Y-only move, per POSITION so every coincident copy agrees
    n_vert_entries = 0
    for b in touched:
        verts = meshes[b].chan_arrays[CH_POS]
        for j, dy in plan[b].items():
            verts[j][1] = verts[j][1] + dy
            n_vert_entries += 1

    # PASS 3 -- per-tri GEOMETRIC up-facing normals on the moved tris ONLY
    nrm_changed_vids = defaultdict(set)
    n_nrm_tris = n_nrm_skipped = 0
    turn_deg = []
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts, nrm = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_NRM]
        for t in sorted(moved_tris[b]):
            tri = bm.tris[t]
            P3 = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in tri]
            nv = up_normal(*P3)
            if nv is None:
                n_nrm_skipped += 1
                continue
            old = nrm[tri[0]]
            dot = max(-1.0, min(1.0, sum(a * b2 for a, b2 in zip(old, nv))))
            turn_deg.append(math.degrees(math.acos(dot)))
            for j in tri:
                nrm[j] = list(nv)
                nrm_changed_vids[b].add(j)
            n_nrm_tris += 1

    dirty = sorted(b for b in touched if plan[b])
    written = {}
    for b in dirty:
        p = F2.terr_path(OUT, *b)
        M.write_ff9mesh(meshes[b], p)
        written[str(p.relative_to(OUT))] = sha256_file(p)

    dys = np.array(list(moved.values()))
    report["stage_apply"] = dict(
        positions_moved=len(moved), vertex_entries_moved=n_vert_entries,
        entries_per_moved_position=dict(sorted(Counter(entries_per_pos.values()).items())),
        tris_with_a_moved_vert=sum(len(v) for v in moved_tris.values()),
        of_which_carried_kept_tris=sum(len(v) for v in moved_tris_kept.values()),
        normal_tris_recomputed=n_nrm_tris, normal_tris_skipped_zero_area=n_nrm_skipped,
        normal_verts_rewritten=sum(len(s) for s in nrm_changed_vids.values()),
        normal_turn_deg=P.stats(turn_deg),
        blocks_written=[list(b) for b in dirty],
        positions_spanning_multiple_blocks=sum(1 for k in moved if len(per_block_pos[k]) > 1),
        dY=P.stats(dys), max_abs_dY=round(float(np.abs(dys).max()), 4),
        move_axis="Y only -- X and Z are never written",
        normal_convention=("per-tri geometric normal forced ny>=0, on every tri (kept OR synthesized) "
                           "with a moved vertex and only those; normal_turn_deg is how far each "
                           "rewritten normal actually swung from the value it replaced"))
    log(f"[apply] moved {len(moved)} positions / {n_vert_entries} entries; tris touched "
        f"{sum(len(v) for v in moved_tris.values())} ({sum(len(v) for v in moved_tris_kept.values())} "
        f"carried); wrote {len(dirty)} Terrain files; max|dY|={float(np.abs(dys).max()):.4f}")
    return dict(plan=plan, moved_tris=moved_tris, moved_tris_kept=moved_tris_kept,
                nrm_changed_vids=nrm_changed_vids, dirty=dirty, written=written)


# =================================================================================================
#  STAGE 7 -- SELF-CHECK (everything against the BYTES ON DISK)
# =================================================================================================
def stage_verify(report, S, R, C, Q, A):
    v = {}
    touched, synth_key, moved = S["touched"], S["synth_key"], Q["moved"]
    spikes = set(C["spikes"])
    res = R["res"]

    f5 = {b: M.read_ff9mesh(F2.terr_path(BASE, *b)) for b in touched}     # FIXED6 (this round's input)
    f6 = {b: M.read_ff9mesh(F2.terr_path(OUT, *b)) for b in touched}      # FIXED7 (this round's output)

    # (1) FLAT-MESH INVARIANT ----------------------------------------------------------------------
    bad = [f"{b[0]},{b[1]}" for b in touched
           if not (f6[b]["vcount"] == len(f6[b]["indices"]) == len(f6[b]["verts"])
                   and len(f6[b]["indices"]) % 3 == 0)]
    v["flat_mesh"] = dict(bad_files=bad, ok=not bad)

    # (2) BYTE RIGIDITY vs FIXED6 ------------------------------------------------------------------
    rig = dict(uv_bad=0, tan_bad=0, idx_bad=0, vcount_bad=0, pos_expected=0, pos_unexpected=0,
               pos_xz_moved=0, nrm_expected=0, nrm_unexpected=0)
    for b in touched:
        a, f = f5[b], f6[b]
        rig["uv_bad"] += (a["uvs"] != f["uvs"])
        rig["tan_bad"] += (a["tangents"] != f["tangents"])
        rig["idx_bad"] += (a["indices"] != f["indices"])
        rig["vcount_bad"] += (a["vcount"] != f["vcount"])
        planned, nchg = A["plan"][b], A["nrm_changed_vids"].get(b, set())
        for j in range(a["vcount"]):
            if a["verts"][j] != f["verts"][j]:
                rig["pos_expected" if j in planned else "pos_unexpected"] += 1
                if a["verts"][j][0] != f["verts"][j][0] or a["verts"][j][2] != f["verts"][j][2]:
                    rig["pos_xz_moved"] += 1
            if a["normals"][j] != f["normals"][j]:
                rig["nrm_expected" if j in nchg else "nrm_unexpected"] += 1
    v["byte_rigidity_vs_fixed6"] = rig
    v["uv_tangent_index_byte_identical"] = (rig["uv_bad"] == 0 and rig["tan_bad"] == 0
                                            and rig["idx_bad"] == 0)

    # (2b) the UV invariant re-measured from FIXED7's own bytes -------------------------------------
    uv_degen = 0
    for b in touched:
        uvs = f6[b]["uvs"]
        for t in range(len(f6[b]["indices"]) // 3):
            tri = f6[b]["indices"][3 * t:3 * t + 3]
            if F2.uv_degenerate([(uvs[j][0], uvs[j][1]) for j in tri]):
                uv_degen += 1
    v["one_window_uv_invariant"] = dict(
        uv_bytes_identical_to_fixed6=(rig["uv_bad"] == 0),
        degenerate_uv_tris_all_terrain=uv_degen, zero_uv_area_floor_held=(uv_degen == 0),
        note=("no UV byte is written this round -- the texture lever was REFUTED on stock evidence, "
              "see the module docstring -- so FIXED3A's ONE-WINDOW-PER-TRI invariant, its "
              "zero-UV-area floor and round 4's family re-clothe carry over unchanged by definition; "
              "the floor is re-measured from FIXED7's own bytes anyway."))

    # (3) THE WELD AUDIT over ALL 8 PARTS of all 20 blocks ------------------------------------------
    pre_groups = defaultdict(list)
    post_pos = {}
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        for part in PARTS:
            rel = M.override_relpath(1, b[0], b[1], part=part)
            p5, p6 = BASE / rel, OUT / rel
            if not p5.exists():
                continue
            d5, d6 = M.read_ff9mesh(p5), M.read_ff9mesh(p6)
            assert d5["vcount"] == d6["vcount"], f"vcount drift in {rel}"
            for j in range(d5["vcount"]):
                a, c = d5["verts"][j], d6["verts"][j]
                pre_groups[P.pkey((a[0] + ox, a[1], a[2] + oz))].append((b, part, j))
                post_pos[(b, part, j)] = P.pkey((c[0] + ox, c[1], c[2] + oz))
    split, nonuniform, groups_moved = [], [], 0
    for k, ents in pre_groups.items():
        outs = {post_pos[e] for e in ents}
        if len(outs) != 1:
            split.append(dict(pre=list(k), n_entries=len(ents), post=[list(o) for o in sorted(outs)]))
        elif next(iter(outs)) != k:
            groups_moved += 1
        deltas = {A["plan"][e[0]].get(e[2], 0.0) if e[1] == "Terrain" else 0.0 for e in ents}
        if len(deltas) != 1:
            nonuniform.append(dict(pre=list(k), n_entries=len(ents), deltas=sorted(deltas)))
    sub_key = [k for k, dv in moved.items() if abs(dv) < 0.5 * 10 ** (-P.POS_DP)]
    v["weld_audit"] = dict(
        n_distinct_positions_all_parts=len(pre_groups),
        groups_that_split=len(split), split_examples=split[:10],
        groups_with_nonuniform_delta=len(nonuniform), nonuniform_examples=nonuniform[:10],
        groups_that_moved=groups_moved, solver_moved_positions=len(moved),
        moved_below_position_key_resolution=len(sub_key),
        moved_groups_reconcile=(groups_moved + len(sub_key) == len(moved)),
        multi_entry_groups_moved=sum(1 for k in moved if len(pre_groups[k]) > 1),
        cross_block_groups_moved=sum(1 for k in moved if len({e[0] for e in pre_groups[k]}) > 1),
        cross_part_groups_moved=sum(1 for k in moved if len({e[1] for e in pre_groups[k]}) > 1),
        entries_per_moved_group=dict(sorted(Counter(len(pre_groups[k]) for k in moved).items())),
        ok=(not split and not nonuniform and groups_moved + len(sub_key) == len(moved)),
        note=("every vertex entry sharing a rounded 3D world position received the identical dY and no "
              "coincident group split -- audited across Terrain/Object/Beach1/Sea1..Sea5 of all 20 "
              "touched blocks, i.e. across parts AND block borders."))

    # (4) NO NEW DOWN-FACING TRI + 3D DEGENERACY ----------------------------------------------------
    ny_before, ny_after = Counter(), Counter()
    ny_changed = newly_down = 0
    degen_before = degen_after = 0
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        d5, d6 = f5[b], f6[b]
        for t in range(len(d6["indices"]) // 3):
            tri = d6["indices"][3 * t:3 * t + 3]
            A3 = [(d5["verts"][j][0] + ox, d5["verts"][j][1], d5["verts"][j][2] + oz) for j in tri]
            B3 = [(d6["verts"][j][0] + ox, d6["verts"][j][1], d6["verts"][j][2] + oz) for j in tri]
            na, nb = tri_geo(*A3)[1], tri_geo(*B3)[1]
            sa = 0 if abs(na) < NRM_EPS else (1 if na > 0 else -1)
            sb = 0 if abs(nb) < NRM_EPS else (1 if nb > 0 else -1)
            ny_before[sa] += 1
            ny_after[sb] += 1
            ny_changed += (sa != sb)
            newly_down += (sa >= 0 and sb < 0)
            degen_before += (tri_area(*A3) < AREA_EPS)
            degen_after += (tri_area(*B3) < AREA_EPS)
    v["down_facing"] = dict(
        geometric_ny_sign_before={str(k): x for k, x in sorted(ny_before.items())},
        geometric_ny_sign_after={str(k): x for k, x in sorted(ny_after.items())},
        tris_whose_ny_sign_changed=ny_changed, newly_down_facing_tris=newly_down,
        ok=(newly_down == 0 and ny_changed == 0),
        proof=("ny of the face cross product = (bx-ax)(cz-az) - (bz-az)(cx-ax) -- a pure X/Z "
               "expression, so a Y-only move leaves winding/facing exactly invariant; verified tri by "
               "tri over every Terrain triangle of all 20 blocks."))
    v["stored_normals_all_up_facing"] = dict(
        min_ny_on_rewritten=round(min((f6[b]["normals"][j][1] for b in touched
                                       for j in A["nrm_changed_vids"].get(b, ())), default=1.0), 6))
    v["degenerate_3d_area"] = dict(tris_before=degen_before, tris_after=degen_after,
                                   new_degenerate=max(0, degen_after - degen_before),
                                   area_eps=AREA_EPS, ok=(degen_after <= degen_before))

    # (5) LAND ABOVE SEA ----------------------------------------------------------------------------
    all_y = [f6[b]["verts"][j][1] for b in touched for j in range(f6[b]["vcount"])]
    moved_y = [k[1] + dv for k, dv in moved.items()]
    v["land_above_sea"] = dict(
        sea_y=SEA_Y, min_Y_over_moved_positions=round(min(moved_y), 4) if moved_y else None,
        min_Y_all_terrain_verts=round(min(all_y), 4),
        min_Y_all_terrain_verts_before=round(min(f5[b]["verts"][j][1] for b in touched
                                                 for j in range(f5[b]["vcount"])), 4),
        ok=bool(not moved_y or min(moved_y) > MIN_LAND_Y))

    # (6) THE CRATER, RE-MEASURED FROM DISK ---------------------------------------------------------
    #     (a) the basin disc byte-frozen  (b) the rim base height DISTRIBUTION identical outside the
    #     spike sites -- the two claims the owner's "crater is sacred" reduces to.
    basin_bytes_changed = 0
    rim_before, rim_after = [], []
    basin_before, basin_after = [], []
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        d5, d6 = f5[b], f6[b]
        for j in range(d5["vcount"]):
            x5, y5, z5 = d5["verts"][j][0] + ox, d5["verts"][j][1], d5["verts"][j][2] + oz
            k = P.pkey((x5, y5, z5))
            r = rc(k)
            if r <= BASIN_R:
                basin_before.append(y5)
                basin_after.append(d6["verts"][j][1])
                if d5["verts"][j] != d6["verts"][j]:
                    basin_bytes_changed += 1
            if r <= MOUND_R and k not in spikes:
                is_kept = any(not sy for (_bb, _tt, sy) in S["tri_index"].get(k, ()))
                if is_kept:
                    rim_before.append(round(y5, 6))
                    rim_after.append(round(d6["verts"][j][1], 6))
    v["crater_sacred"] = dict(
        basin=dict(center=list(BASIN_C), radius_u=BASIN_R,
                   n_vertex_entries_inside=len(basin_before),
                   n_position_groups_inside=len(R["basin_keys"]),
                   vertex_bytes_changed=basin_bytes_changed,
                   y_before=P.stats(basin_before), y_after=P.stats(basin_after),
                   byte_frozen=(basin_bytes_changed == 0)),
        rim_base=dict(
            scope=f"every CARRIED vertex entry within {MOUND_R}u of the crater centre, spikes excluded",
            n_entries=len(rim_before),
            distribution_before=P.stats(rim_before), distribution_after=P.stats(rim_after),
            multiset_identical=(sorted(rim_before) == sorted(rim_after)),
            entries_differing=sum(1 for a, b2 in zip(rim_before, rim_after) if a != b2),
            crest_ring_y_6p208_count=sum(1 for y in rim_after if abs(y - 6.208) < 1e-3)),
        ok=(basin_bytes_changed == 0 and sorted(rim_before) == sorted(rim_after)))

    # (7) THE OUTCOME -- residuals re-measured against the SAME reference (it is fit from positions
    #     that did not move, so before/after are commensurable), plus a re-fit from FIXED7's bytes.
    post_same_ref = {k: res[k] + moved.get(k, 0.0) for k in spikes}
    sample_keys2 = sorted(set(S["kept_ground"]) | S["fill"])
    samples2 = np.array([[k[0], k[1] + moved.get(k, 0.0), k[2]] for k in sample_keys2], dtype=float)
    idx2 = {k: i for i, k in enumerate(sample_keys2)}
    base2 = P.Hash2D(samples2, cell=8.0)
    basin2 = frozenset(idx2[k] for k in sample_keys2 if rc(k) <= BASIN_R)
    refit = {}
    for k in spikes:
        y, _ = P.ref_at(ExcludeHash(base2, basin2 | {idx2[k]}), samples2, k[0], k[2])
        refit[k] = None if y is None else (k[1] + moved[k]) - y
    v["spike_outcome"] = dict(
        sites=[dict(world=[round(k[0], 3), round(k[1], 3), round(k[2], 3)],
                    y_before=round(k[1], 3), y_after=round(k[1] + moved[k], 3),
                    dY=round(moved[k], 3),
                    residual_before=round(res[k], 3),
                    residual_after_same_reference=round(post_same_ref[k], 3),
                    residual_after_refit_from_disk=(None if refit[k] is None else round(refit[k], 3)),
                    prominence_before=round(C["prom"][k], 3),
                    prominence_after=round((k[1] + moved[k])
                                           - max(n[1] + moved.get(n, 0.0) for n in S["adj"][k]), 3))
               for k in sorted(spikes, key=lambda k: -res[k])],
        max_abs_residual_after=round(max(abs(x) for x in post_same_ref.values()), 4),
        all_below_threshold=all(abs(x) < SPIKE_RES_T for x in post_same_ref.values()),
        note=("prominence_after <= 0 means the vertex is no longer a local maximum: it has been "
              "shaved into its own neighbour ring, which is the whole point of the round."))

    # (8) THE TENT FILL -- the synthesized tris that ramp up to each spike ---------------------------
    span_before, span_after, dip_before, dip_after = [], [], [], []
    tent_rows = []
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        d5, d6 = f5[b], f6[b]
        for t in sorted(A["moved_tris"][b]):
            tri = d6["indices"][3 * t:3 * t + 3]
            A3 = [(d5["verts"][j][0] + ox, d5["verts"][j][1], d5["verts"][j][2] + oz) for j in tri]
            B3 = [(d6["verts"][j][0] + ox, d6["verts"][j][1], d6["verts"][j][2] + oz) for j in tri]

            def dip(pts):
                nx, ny, nz = tri_geo(*pts)
                ln = math.sqrt(nx * nx + ny * ny + nz * nz)
                return 90.0 if ln < NRM_EPS else math.degrees(math.acos(min(1.0, abs(ny) / ln)))
            sb = max(p[1] for p in A3) - min(p[1] for p in A3)
            sa = max(p[1] for p in B3) - min(p[1] for p in B3)
            span_before.append(sb)
            span_after.append(sa)
            dip_before.append(dip(A3))
            dip_after.append(dip(B3))
            tent_rows.append(dict(block=f"{b[0]},{b[1]}", tri=t, synth=((b, t) in synth_key),
                                  y_span_before=round(sb, 3), y_span_after=round(sa, 3),
                                  dip_before=round(dip(A3), 1), dip_after=round(dip(B3), 1)))
    tent_rows.sort(key=lambda r: -(r["y_span_before"] - r["y_span_after"]))
    v["tent_fill_smoothed"] = dict(
        n_tris_touched=len(tent_rows),
        y_span=dict(before=P.stats(span_before), after=P.stats(span_after)),
        dip_deg=dict(before=P.stats(dip_before), after=P.stats(dip_after)),
        n_tris_span_ge_1u=dict(before=sum(1 for s in span_before if s >= 1.0),
                               after=sum(1 for s in span_after if s >= 1.0)),
        n_tris_dip_ge_45=dict(before=sum(1 for d in dip_before if d >= 45.0),
                              after=sum(1 for d in dip_after if d >= 45.0)),
        biggest_collapses=tent_rows[:15])

    # (8b) THE ROUND IS SELF-TERMINATING -- the whole census re-derived FROM FIXED7'S OWN BYTES ------
    v["recensus_from_disk"] = _recensus(OUT, S["touched"], synth_key)
    v["recensus_from_disk"]["base_for_comparison"] = _recensus(BASE, S["touched"], synth_key)
    v["recensus_from_disk"]["census_now_empty"] = (v["recensus_from_disk"]["n_qualifying"] == 0)

    # (8c) PRIOR FIXES INTACT -- rounds 5 and 6 re-verified on FIXED7's own bytes -------------------
    v["prior_fixes_intact"] = _prior_fixes_intact(S, R, C, Q, A, f5, f6, res)

    # (9) TREE DIFF ---------------------------------------------------------------------------------
    changed = [str(p.relative_to(BASE)) for p in sorted(BASE.rglob("*"))
               if p.is_file() and sha256_file(p) != sha256_file(OUT / str(p.relative_to(BASE)))]
    expected = set(A["written"])
    v["tree_diff_vs_fixed6"] = dict(
        n_files=len(changed), files=changed,
        n_terrain=sum(1 for r in changed if "Terrain" in r),
        n_non_terrain=sum(1 for r in changed if "Terrain" not in r),
        unexpected=[r for r in changed if r not in expected],
        expected_not_changed=[r for r in expected if r not in changed],
        non_terrain_untouched=all("Terrain" in r for r in changed),
        file_count=sum(1 for p in OUT.rglob("*") if p.is_file()))

    # (10) a compact DEM of the mound, before and after ---------------------------------------------
    v["mound_dem"] = _mound_dem(S, f5, f6)

    ok = bool(v["flat_mesh"]["ok"] and v["weld_audit"]["ok"] and v["down_facing"]["ok"]
              and v["degenerate_3d_area"]["ok"] and v["land_above_sea"]["ok"]
              and v["crater_sacred"]["ok"] and v["uv_tangent_index_byte_identical"]
              and v["one_window_uv_invariant"]["zero_uv_area_floor_held"]
              and rig["pos_unexpected"] == 0 and rig["pos_xz_moved"] == 0
              and rig["nrm_unexpected"] == 0 and rig["vcount_bad"] == 0
              and v["spike_outcome"]["all_below_threshold"]
              and v["recensus_from_disk"]["census_now_empty"]
              and v["prior_fixes_intact"]["ok"]
              and v["tree_diff_vs_fixed6"]["non_terrain_untouched"]
              and not v["tree_diff_vs_fixed6"]["unexpected"]
              and not v["tree_diff_vs_fixed6"]["expected_not_changed"]
              and v["tree_diff_vs_fixed6"]["file_count"] == N_FILES)
    report["stage_verify"] = v
    report["ok"] = ok
    log(f"[verify] flat={v['flat_mesh']['ok']} weld={v['weld_audit']['ok']} "
        f"(split={v['weld_audit']['groups_that_split']}) "
        f"down_new={v['down_facing']['newly_down_facing_tris']} "
        f"degen3d={v['degenerate_3d_area']['tris_after']} "
        f"minY={v['land_above_sea']['min_Y_all_terrain_verts']}")
    log(f"[verify] rigidity {rig}  uv_degen={uv_degen}")
    log(f"[verify] crater: basin bytes changed={basin_bytes_changed}; rim-base multiset identical="
        f"{v['crater_sacred']['rim_base']['multiset_identical']} over "
        f"{v['crater_sacred']['rim_base']['n_entries']} carried entries")
    log(f"[verify] spikes after: {[s['residual_after_same_reference'] for s in v['spike_outcome']['sites']]}"
        f"  prominence after: {[s['prominence_after'] for s in v['spike_outcome']['sites']]}")
    log(f"[verify] re-census from disk: qualifiers "
        f"{v['recensus_from_disk']['base_for_comparison']['n_qualifying']} (FIXED6) -> "
        f"{v['recensus_from_disk']['n_qualifying']} (FIXED7); max mound drop "
        f"{v['recensus_from_disk']['base_for_comparison']['max_drop_in_mound']} -> "
        f"{v['recensus_from_disk']['max_drop_in_mound']}")
    pf = v["prior_fixes_intact"]
    log(f"[verify] prior fixes: round6 apexes intact={pf['round6']['all_four_intact']} "
        f"round5 seal intact={pf['round5']['seal_intact']} "
        f"the-one dips {pf['the_one']['dip_before']} -> {pf['the_one']['dip_after']} "
        f"(4 shaved siblings now {pf['round6']['sibling_decal_dips']})")
    log(f"[verify] tree diff: {len(changed)} files; OK={ok}")
    return ok


def _tri_dip(pts):
    nx, ny, nz = tri_geo(*pts)
    ln = math.sqrt(nx * nx + ny * ny + nz * nz)
    return 90.0 if ln < NRM_EPS else math.degrees(math.acos(min(1.0, abs(ny) / ln)))


def _prior_fixes_intact(S, R, C, Q, A, f5, f6, res):
    """ROUNDS 5 AND 6 RE-VERIFIED ON FIXED7'S OWN BYTES.

    This round moves CARRIED geometry a few metres from work the owner has already approved, so "I did
    not touch it" is not good enough -- the previous rounds' OUTCOMES are re-measured, not just their
    inputs.  Three claims:
      round 6 -- the four shaved apexes still sit at exactly the Y round 6 left them at, and their
                 two-tri rock decals are still lying nearly flat;
      round 5 -- the seal holds: no fill position outside this round's patch moved, and neither the
                 fill's residual spread nor the mound's steep-face population grew;
      the one -- the round's actual objective, measured the way the owner sees it (the decal tri dips).
    """
    touched, moved = S["touched"], Q["moved"]
    spikes = set(C["spikes"])

    def dips_at(k, meshes):
        """Dips of the KEPT (carried) tris touching position k, evaluated in the given tree."""
        out = []
        for (b, t, sy) in S["tri_index"].get(k, ()):
            if sy:
                continue
            ox, oz = X.block_world_origin(*b)
            d = meshes[b]
            tri = d["indices"][3 * t:3 * t + 3]
            pts = [(d["verts"][j][0] + ox, d["verts"][j][1], d["verts"][j][2] + oz) for j in tri]
            out.append((f"{b}#{t}", round(_tri_dip(pts), 2)))
        return sorted(set(out))

    # --- ROUND 6 -----------------------------------------------------------------------------------
    r6_keys = _round6_apexes(S)
    r6_rows, r6_ok = [], True
    for k in r6_keys:
        yb = _y_at(f5, S, k)
        ya = _y_at(f6, S, k)
        intact = (yb is not None and ya is not None and yb == ya and k not in moved)
        r6_ok = r6_ok and intact
        r6_rows.append(dict(world=[round(k[0], 3), round(k[1], 3), round(k[2], 3)],
                            y_in_fixed6=yb, y_in_fixed7=ya, byte_identical=(yb == ya),
                            moved_this_round=(k in moved),
                            decal_tri_dips_after=dips_at(k, f6), intact=intact))
    sib_dips = sorted({d for r in r6_rows for (_t, d) in r["decal_tri_dips_after"]})

    # --- ROUND 5 -- the seal ------------------------------------------------------------------------
    fill = S["fill"]
    fill_changed_outside_patch = [k for k in fill if k not in moved and _y_at(f5, S, k) != _y_at(f6, S, k)]
    fill_res_before = [res[k] for k in fill if res.get(k) is not None]
    fill_res_after = [res[k] + moved.get(k, 0.0) for k in fill if res.get(k) is not None]
    steep_b = steep_a = span_b = span_a = 0
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        d5, d6 = f5[b], f6[b]
        for t in range(len(d6["indices"]) // 3):
            tri = d6["indices"][3 * t:3 * t + 3]
            A3 = [(d5["verts"][j][0] + ox, d5["verts"][j][1], d5["verts"][j][2] + oz) for j in tri]
            if math.hypot(sum(p[0] for p in A3) / 3 - BASIN_C[0],
                          sum(p[2] for p in A3) / 3 - BASIN_C[1]) > MOUND_R:
                continue
            B3 = [(d6["verts"][j][0] + ox, d6["verts"][j][1], d6["verts"][j][2] + oz) for j in tri]
            steep_b += (_tri_dip(A3) >= 45.0)
            steep_a += (_tri_dip(B3) >= 45.0)
            span_b += ((max(p[1] for p in A3) - min(p[1] for p in A3)) >= 1.0)
            span_a += ((max(p[1] for p in B3) - min(p[1] for p in B3)) >= 1.0)
    seal_ok = bool(not fill_changed_outside_patch and steep_a <= steep_b and span_a <= span_b
                   and max((abs(x) for x in fill_res_after), default=0.0)
                   <= max((abs(x) for x in fill_res_before), default=0.0) + 1e-6)

    # --- THE ONE -- the objective --------------------------------------------------------------------
    one_b = sorted({d for k in spikes for (_t, d) in dips_at(k, f5)})
    one_a = sorted({d for k in spikes for (_t, d) in dips_at(k, f6)})

    return dict(
        round6=dict(
            source=str(FIX6_REPORT.name), n_apexes=len(r6_keys), rows=r6_rows,
            all_four_intact=r6_ok, sibling_decal_dips=sib_dips,
            reselected_by_the_wider_rule=len(set(r6_keys) & spikes),
            claim=("round 6's four apexes are byte-frozen this round AND their carried rock-decal tris "
                   "are still lying flat -- the widened predicate did not re-cut approved geometry.")),
        round5=dict(
            n_fill_positions=len(fill),
            fill_positions_changed_outside_this_patch=len(fill_changed_outside_patch),
            fill_residual_before=P.stats(fill_res_before), fill_residual_after=P.stats(fill_res_after),
            mound_tris_dip_ge_45=dict(before=steep_b, after=steep_a),
            mound_tris_span_ge_1u=dict(before=span_b, after=span_a),
            seal_intact=seal_ok,
            claim=("round 5's seal is the fill sheet: no fill position outside this round's own patch "
                   "moved a byte, the fill's residual spread did not widen, and the mound's steep-face "
                   "and tall-tri populations did not grow.  A shave that re-opened a crevice would "
                   "show up as steep/span AFTER > BEFORE.")),
        the_one=dict(
            n_spikes=len(spikes),
            dip_before=one_b, dip_after=one_a,
            objective=("the owner sees a DIP, not a residual: the carried rock-decal tri pair stood at "
                       "46.0/35.6 deg while its four already-shaved siblings lie at 4.2-23.9.  After "
                       "this round it must join them.")),
        ok=bool(r6_ok and seal_ok))


def _y_at(meshes, S, k):
    """The Y this tree stores at position key k, located by X/Z (Y is what may have changed).  The weld
    audit separately proves every entry sharing a position agrees, so any one entry is the answer."""
    for (b, t, _sy) in S["tri_index"].get(k, ()):
        ox, oz = X.block_world_origin(*b)
        d = meshes[b]
        for j in d["indices"][3 * t:3 * t + 3]:
            if (round(d["verts"][j][0] + ox, P.POS_DP) == k[0]
                    and round(d["verts"][j][2] + oz, P.POS_DP) == k[2]):
                return d["verts"][j][1]
    return None


def _recensus(tree, touched, synth_key):
    """Re-derive the ENTIRE census (classification -> reference -> residual -> prominence -> the spike
    rule) from a tree's own bytes on disk.  Run on FIXED7 this is the round's self-termination proof:
    the rule that selected 4 positions must now select none."""
    meshes = F3.load_blocks(tree, touched)
    cg, rock, fillp = set(), set(), set()
    adj = defaultdict(set)
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts, tans = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            topo = X.decode_id(int(round(tans[tri[0]][0])))["topograph"]
            ks = [P.pkey((verts[j][0] + ox, verts[j][1], verts[j][2] + oz)) for j in tri]
            for a in range(3):
                for c in range(3):
                    if a != c and ks[a] != ks[c]:
                        adj[ks[a]].add(ks[c])
            for k in ks:
                if (b, t) in synth_key:
                    fillp.add(k)
                elif GROUND_FAM.get(topo) is not None:
                    cg.add(k)
                else:
                    rock.add(k)
    fillp -= cg
    fillp -= rock
    keys = sorted(cg | fillp)
    smp = np.array([[k[0], k[1], k[2]] for k in keys], dtype=float)
    io = {k: i for i, k in enumerate(keys)}
    h = P.Hash2D(smp, cell=8.0)
    basin = frozenset(io[k] for k in keys if rc(k) <= BASIN_R)

    def run(drop):
        out = {}
        for k in keys:
            y, _ = P.ref_at(ExcludeHash(h, basin | {io[k]} | drop), smp, k[0], k[2])
            out[k] = None if y is None else k[1] - y
        return out
    r1 = run(frozenset())
    res = run(frozenset(io[k] for k in keys if r1[k] is not None and r1[k] >= SPIKE_RES_T))
    prom = {k: k[1] - max((n[1] for n in adj[k]), default=-1e9) for k in keys}
    drop = {k: k[1] - min((n[1] for n in adj[k]), default=1e9) for k in keys}

    def arm(k):
        if prom[k] >= SPIKE_PROM_T:
            return "CONE"
        if prom[k] >= STEP_PROM_T and drop[k] >= STEP_DROP_T:
            return "STEP"
        return None
    mound = [k for k in cg if BASIN_R < rc(k) <= MOUND_R and res[k] is not None]
    qual = [k for k in mound if res[k] >= SPIKE_RES_T and arm(k) is not None]
    return dict(
        tree=tree.name, n_carried_in_mound=len(mound),
        rule="round 7 -- residual >= 0.8 AND (prominence >= 0.4 OR (prominence >= 0.0 AND drop >= 1.5))",
        max_residual_in_mound=round(max(res[k] for k in mound), 4) if mound else None,
        max_prominence_in_mound=round(max(prom[k] for k in mound), 4) if mound else None,
        max_drop_in_mound=round(max(drop[k] for k in mound), 4) if mound else None,
        n_qualifying=len(qual),
        qualifying=[dict(world=[round(k[0], 3), round(k[1], 3), round(k[2], 3)],
                         res=round(res[k], 3), prom=round(prom[k], 3), drop=round(drop[k], 3),
                         arm=arm(k)) for k in qual],
        top_drop=[dict(world=[round(k[0], 2), round(k[1], 3), round(k[2], 2)],
                       drop=round(drop[k], 3), prom=round(prom[k], 3), res=round(res[k], 3),
                       arm=arm(k), r_crater=round(rc(k), 1))
                  for k in sorted(mound, key=lambda k: -drop[k])[:5]],
        top_prominence=[dict(world=[round(k[0], 2), round(k[1], 3), round(k[2], 2)],
                             prom=round(prom[k], 3), res=round(res[k], 3), r_crater=round(rc(k), 1))
                        for k in sorted(mound, key=lambda k: -prom[k])[:5]],
        note=("the same five-predicate rule INCLUDING ROUND 7's STEP ARM, re-run end to end on this "
              "tree's bytes.  On FIXED7 it must return an EMPTY set -- the round removed exactly what "
              "it was defined to find and the widening opened no new door.  On FIXED6 it must return "
              "exactly the one position this round shaved: that pair of results is what makes the "
              "widening self-terminating rather than open-ended.  Whatever residual is left in the "
              "mound belongs to the crater's own carried rim crest/shoulder (high residual, small "
              "drop, near-zero prominence -- flush with a neighbour on a gentle ramp, therefore "
              "lawful)."))


def _mound_dem(S, f5, f6, R_=26.0, STEP=1.5, lo=2.5, hi=7.4):
    """Top-surface DEM of the crater mound from the bytes, BEFORE and AFTER, as glyph grids."""
    cx0, cz0 = BASIN_C
    n = int(2 * R_ / STEP) + 1

    def build(meshes):
        Yg = [[None] * n for _ in range(n)]
        for b in S["touched"]:
            ox, oz = X.block_world_origin(*b)
            d = meshes[b]
            for t in range(len(d["indices"]) // 3):
                tri = d["indices"][3 * t:3 * t + 3]
                pts = [(d["verts"][j][0] + ox, d["verts"][j][1], d["verts"][j][2] + oz) for j in tri]
                xs = [p[0] for p in pts]
                zs = [p[2] for p in pts]
                if min(xs) > cx0 + R_ or max(xs) < cx0 - R_ or min(zs) > cz0 + R_ or max(zs) < cz0 - R_:
                    continue
                (ax, ay, az), (bx, by, bz), (cx, cy, cz) = pts
                den = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
                if abs(den) < 1e-9:
                    continue
                i0 = max(0, int((min(xs) - (cx0 - R_)) / STEP))
                i1 = min(n - 1, int((max(xs) - (cx0 - R_)) / STEP) + 1)
                j0 = max(0, int((min(zs) - (cz0 - R_)) / STEP))
                j1 = min(n - 1, int((max(zs) - (cz0 - R_)) / STEP) + 1)
                for i in range(i0, i1 + 1):
                    px = cx0 - R_ + i * STEP
                    for j in range(j0, j1 + 1):
                        pz = cz0 - R_ + j * STEP
                        l1 = ((bz - cz) * (px - cx) + (cx - bx) * (pz - cz)) / den
                        l2 = ((cz - az) * (px - cx) + (ax - cx) * (pz - cz)) / den
                        if l1 < -1e-6 or l2 < -1e-6 or 1 - l1 - l2 < -1e-6:
                            continue
                        y = l1 * ay + l2 * by + (1 - l1 - l2) * cy
                        if Yg[j][i] is None or y > Yg[j][i]:
                            Yg[j][i] = y
        return ["".join(" " if val is None else
                        "0123456789"[max(0, min(9, int((val - lo) / (hi - lo) * 10)))]
                        for val in rowv) for rowv in Yg]

    return dict(centre=list(BASIN_C), half_width_u=R_, step_u=STEP,
                glyph_scale=f"'0'..'9' = Y {lo}..{hi}u, ' ' = no surface",
                row_z_from=round(cz0 - R_, 1), col_x_from=round(cx0 - R_, 1),
                before=build(f5), after=build(f6))


# =================================================================================================
def main():
    build = "--build" in sys.argv
    report = {"meta": dict(
        script="uvf_fix7.py", round=7, read_only_vs_game=True, build_requested=build,
        base_tree=str(BASE), out_tree=str(OUT),
        diagnosis_source=str(SLIVER_PROBE),
        playtest5=("they're mostly flattened but ONE sticks out in particular and has a noticeably "
                   "different texture than the sand"),
        work_order=("shave the ONE surviving carried STEP crest on the crater mound into the local rim "
                    "surface; the crater bowl, the rim's overall height and rounds 5-6's approved work "
                    "MUST survive"),
        lever="GEOMETRY-SOFTEN (Y-only).  TEXTURE-DRESS was refuted on stock evidence -- see docstring.",
        contract_change=("predicate (3) of round 6's census gains a STEP ARM: prominence >= 0.4u (CONE, "
                         "round 6) OR prominence >= 0.0u AND max welded drop >= 1.5u (STEP, new).  "
                         "Everything else -- the residual gate, the rock exemption, the sacred basin, "
                         "the mound radius, the Terrain-only predicate, the solve, the guards, the weld "
                         "law -- is round 6's, unchanged."),
        mechanism=("THE ONE is the fifth knob of the family round 6 shaved four of: a carried topo-41 "
                   "dunes tri pair wearing an uncatalogued rock/lichen atlas decal, apex "
                   "(116.000, 6.341, -1164.000), r 11.43u WSW.  It is NOT a cone -- one neighbour is "
                   "0.133u below it (so round 6's strict-local-maximum predicate skipped it) while the "
                   "other side falls 2.259u at 47.2 deg into fill that round 5's relax pushed 1.040u "
                   "below its donor height.  A STEP, not a spike."),
        method=("two-predicate census (residual vs a leave-one-out, BASIN-EXCLUDED local rim reference "
                "AND a two-armed shape test: strict mesh prominence OR step drop) -> harmonic Laplacian "
                "least squares on the spike patch, Dirichlet dY=0 at every pinned position"),
        not_done=("the fill-restore companion (raise the two over-relaxed fill vertices back to donor "
                  "height) is the fidelity-correct alternative and is deliberately NOT bundled here -- "
                  "it has no approved precedent and would confound the in-game read.  ONE CHANGE PER "
                  "IN-GAME TEST.  The 36 over-stretched synthesized-fill tris (up to 2.769x vs stock's "
                  "1.414x ground ceiling) are a separate texture-lane job."))}

    S = stage1(report)
    R = stage2(report, S)
    C = stage3(report, S, R)
    Q = stage4(report, S, R, C)
    passed = stage_guards(report, S, R, C, Q)
    if not passed:
        report["ok"] = False
        report["refused"] = "a STOP guard failed -- nothing was written"
        REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
        log(f"REFUSED TO BUILD -- wrote {REPORT}")
        return report

    if build:
        A = stage_apply(report, S, Q)
        stage_verify(report, S, R, C, Q, A)
    else:
        report["ok"] = None
        log("[main] probe-only (pass --build to emit FIXED7).")

    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"\n{'=' * 80}\nwrote {REPORT}  ok={report.get('ok')}")
    return report


if __name__ == "__main__":
    main()
