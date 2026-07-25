"""RUNG F -- THE CARRIED-SPIKE SHAVE (geometry-fix round 6, 2026-07-25).

Playtest 4 on FIXED5: round 5's relief relax WORKED ("the crevices are sealed up ... seal looks good")
but the owner still reports "the bumpy top part" on the crater mound.

Round 5 could not touch it BY CONTRACT: the bumps are CARRIED donor geometry (kept topo-41 dunes tris),
which round 5 pinned as Dirichlet.  Round 5's own notes predicted exactly this ("if the owner still
reports a raised nub, it is carried geometry -- a different lever").  This is that lever, and it is the
THIRD application of the ratified direction: the roots/massif are ABSENT, the ground continues smoothly,
so an isolated carried remnant whose context was amputated relaxes into the local surface.

WHAT THE MEASUREMENT ACTUALLY FOUND (probe stage, all numbers re-derived on every run)
  * The bumps are NOT tents of fill.  Each site is ONE carried vertex -- the apex of a kept topo-41
    dunes TRI PAIR -- riding 0.52-0.78u above every one of its own mesh neighbours and 0.82-1.17u above
    the local rim surface, with round-5's lawfully-relaxed fill ramping UP to meet it.
  * THE BASIN IS A REFERENCE TRAP.  A local ground fit that samples the crater bowl (fill at Y=3.000,
    3.27u below its carried rim) is dragged DOWN, and then the crater's own RIM CREST -- a broad carried
    ring at exactly Y=6.208, r=8.9-11.5u -- scores residuals up to +1.958u, and 9 of its 14 vertices
    qualify as "spikes".  Shaving those would flatten the crater the owner likes.  The reference
    therefore EXCLUDES the sacred basin disc from its SAMPLE set; with that one change the crest ring
    falls to -0.131..+0.728u (0 of 14 qualifying) while the four real apexes stay at +0.82..+1.17u.
  * A THRESHOLD ALONE IS NOT ENOUGH.  Two carried positions clear +0.8u without being spikes at all --
    a rim-shoulder vertex at (116.00,-1164.00) (+0.863u) and a far grass vertex at (200.00,-1108.00)
    (+0.835u) -- both of which are FLUSH with a neighbour (prominence +0.133 / +0.000).  The load-
    bearing second predicate is MESH PROMINENCE: a spike is a STRICT LOCAL MAXIMUM, above every vertex
    it is welded to.  Residual AND prominence together select exactly 4 positions, all topo-41 dunes on
    the crater mound, with a clean margin on both axes (next-best prominence among residual-qualified
    carried positions is +0.133 vs the set's minimum +0.524).

THE CONTRACT CHANGE THIS ROUND (the only one)
  Carried positions MAY move -- but ONLY the census-defined SPIKE SET, plus fill positions welded/graph-
  adjacent to them.  Every other carried vertex stays byte-rigid; that is asserted, not asserted-in-prose:
  the unknown set contains NO carried position outside the spike set BY CONSTRUCTION, and a stop guard
  re-checks it against the solved dY before a byte is written.  ROCK STAMPS (topo 58 / 31) are exempt at
  three levels: they never vote as reference samples, they are never census candidates, and any position
  they touch is refused.  THE CRATER IS SACRED: the basin disc r<=7.92u at (127.14,-1161.42) is frozen,
  and the rim base's height distribution outside the 4 spike sites is proven bit-identical before/after.

THE SOLVE is round 5's, re-scoped: harmonic (Laplacian) least squares on the LOCAL patch graph --
unknowns = the 4 spikes + the fill within HOPS=2 of them; data term dY = -residual (weight W_SPIKE on the
spikes, "hold your ground" w=1 on the fill); smoothness on every edge inside the patch; Dirichlet dY=0 on
every edge leaving it.  C0 into the pins BY CONSTRUCTION -- a distance falloff would merely RELOCATE the
step onto the pinned rim (round 5's lesson, unchanged).  W_SPIKE is not hand-picked: it is the smallest
of a fixed sweep for which every spike lands within 0.15u of the rim surface and no fill vertex moves
more than 0.60u.

READ-ONLY vs the game install.  Emits out/rung_f/FF9CustomMap-world-FIXED6 + uvf_fix6_report.json.
Renders nothing -- uvf_eye_relief.py owns judgment.

    py -X utf8 uvf_fix6.py            # probe-only (census + solve dry run, writes nothing)
    py -X utf8 uvf_fix6.py --build    # emit FIXED6 + the full self-check battery
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
FIXED5 = RUNG_F / "FF9CustomMap-world-FIXED5"
FIXED6 = RUNG_F / "FF9CustomMap-world-FIXED6"
BUILD_JSON = RUNG_F / "rung_f_build.json"
FORENSICS = RUNG_F / "uvf_forensics.json"
FIX5_REPORT = RUNG_F / "uvf_fix5_report.json"
REPORT = RUNG_F / "uvf_fix6_report.json"

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
SPIKE_PROM_T = 0.40       # u above EVERY mesh neighbour (strict local maximum)
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
    # must hold for the (block, tri) identity to carry into FIXED5 is: identical INDICES, and identical
    # X/Z on every vertex entry (rounds 1-4 were UV-only, round 5 was Y-only).  Both are asserted.
    spec_meshes = F3.load_blocks(SPEC, touched)
    f5_meshes = F3.load_blocks(FIXED5, touched)
    uv_diff = idx_diff = xz_diff = y_diff = vcount_diff = 0
    for b in touched:
        a5 = M.read_ff9mesh(F2.terr_path(FIXED5, *b))
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

    # --- the position graph over EVERY part, on the FIXED5 bytes ----------------------------------
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
            p = Path(FIXED5) / M.override_relpath(1, b[0], b[1], part=part)
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
        spec_vs_fixed5=dict(
            uv_files_differing=uv_diff, index_files_differing=idx_diff, vcount_files_differing=vcount_diff,
            vertex_entries_with_XZ_differing=xz_diff, vertex_entries_with_Y_differing=y_diff,
            reading=("UV files DO differ -- that is FIXED3A's one-window cure plus round 4's family "
                     "re-clothe, and it is why the SPEC's degenerate UVs remain the classifier of "
                     "record.  The carry-over proof is instead: 0 index differences and 0 X/Z "
                     "differences, so (block, tri) means the same triangle in both trees; the Y "
                     "differences are exactly round 5's relief relax.")),
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
    rim_ring = sorted([k for k in S["kept_ground"] if abs(k[1] - 6.208) < 1e-3 and rc(k) <= 15.0],
                      key=lambda k: -res_contam[k])

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
                                                          if res[k] >= SPIKE_RES_T)),
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
                res_contam=res_contam, cand_a=cand_a)


# =================================================================================================
#  STAGE 3 -- THE SPIKE CENSUS
# =================================================================================================
def stage3(report, S, R):
    res, adj = R["res"], S["adj"]
    kept_ground, kept_rock, fill = S["kept_ground"], S["kept_rock"], S["fill"]
    parts_of = S["parts_of"]

    prom = {}
    for k in R["sample_keys"]:
        nb = adj.get(k, ())
        prom[k] = (k[1] - max((n[1] for n in nb), default=-1e9)) if nb else None

    donor = P.load_donor(report)          # dropped-topo-49 cells == the former root-wedge footprint
    cells49 = donor["cells49"]

    def cell_of(k):
        return (math.floor(k[0] / CELL), math.floor(k[2] / CELL))

    def row(k, kind):
        return dict(k=list(k), kind=kind, y=round(k[1], 4),
                    ref=round(k[1] - res[k], 4) if res.get(k) is not None else None,
                    res=round(res[k], 4) if res.get(k) is not None else None,
                    prom=round(prom[k], 4) if prom.get(k) is not None else None,
                    r_crater=round(rc(k), 2), deg=len(adj.get(k, ())),
                    topo=sorted(kept_ground.get(k, kept_rock.get(k, set()))),
                    parts=sorted(parts_of[k]),
                    in_wedge_donut=bool(cell_of(k) in cells49),
                    also_touched_by_fill=bool(k in S["synth_pos"]))

    # --- THE RULE (five predicates, no hand-picking) -----------------------------------------------
    def classify(k):
        if k in kept_rock:
            return "rock-stamp-EXEMPT"
        if k not in kept_ground:
            return "fill"
        if res.get(k) is None:
            return "unscored"
        if res[k] < SPIKE_RES_T:
            return "below-residual-threshold"
        if prom.get(k) is None or prom[k] < SPIKE_PROM_T:
            return "flush-with-a-neighbour(not-a-spike)"
        if rc(k) <= BASIN_R:
            return "inside-the-sacred-basin(refused)"
        if parts_of[k] != {"Terrain"}:
            return "shared-with-a-non-Terrain-part(refused)"
        if rc(k) > MOUND_R:
            return "outside-the-crater-mound(report-only)"
        return "SPIKE"

    verdicts = {k: classify(k) for k in set(kept_ground) | set(kept_rock)}
    spikes = sorted([k for k, v in verdicts.items() if v == "SPIKE"], key=lambda k: -res[k])

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

    report["stage3_spike_census"] = dict(
        rule=dict(
            residual_threshold_u=SPIKE_RES_T, prominence_threshold_u=SPIKE_PROM_T,
            mound_radius_u=MOUND_R, basin_radius_u=BASIN_R,
            statement=("a SPIKE is a CARRIED position that (1) has a ground family topograph -- rock "
                       f"stamps (58/31) are exempt outright; (2) sits >= {SPIKE_RES_T}u above the local "
                       f"rim reference; (3) is a STRICT LOCAL MAXIMUM, >= {SPIKE_PROM_T}u above EVERY "
                       "mesh vertex it is welded to; (4) lies outside the sacred basin disc and inside "
                       f"the {MOUND_R}u crater-mound region; (5) has all its vertex entries in the "
                       "Terrain part (a position shared with Object/Beach/Sea would demand a cross-part "
                       "move and is refused).  Predicate (3) is the load-bearing one: it is what "
                       "separates an apex from a rim-plateau vertex that merely scores high.")),
        verdict_hist=dict(sorted(Counter(verdicts.values()).items())),
        n_spikes=len(spikes), n_sites=len(sites), sites=sites,
        margin=dict(
            min_residual_in_set=round(min(res[k] for k in spikes), 3) if spikes else None,
            min_prominence_in_set=round(min(prom[k] for k in spikes), 3) if spikes else None,
            best_prominence_among_residual_qualified_rejects=round(
                max((prom[k] for k in kept_ground
                     if res.get(k) is not None and res[k] >= SPIKE_RES_T and k not in spikes),
                    default=float("nan")), 3),
            best_residual_among_prominence_qualified_rejects=round(
                max((res[k] for k in kept_ground
                     if prom.get(k) is not None and prom[k] >= SPIKE_PROM_T and k not in spikes),
                    default=float("nan")), 3),
            note=("both axes are separated: nothing rejected on prominence comes close to the set's "
                  "prominence floor, and nothing rejected on residual comes close to its residual "
                  "floor.  The two near-misses are named in near_misses below.")),
        near_misses=[row(k, "carried-ground") for k in carried_reported
                     if k not in spikes and res[k] >= SPIKE_RES_T],
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
        log(f"     site peak Y={s['peak_world'][1]:.3f} res={s['peak_residual_u']:+.3f} "
            f"prom={s['peak_prominence_u']:+.3f} r={s['r_crater']} topo={s['topo']} "
            f"ring={s['neighbour_ring_y']}")
    return dict(spikes=spikes, prom=prom, sites=sites, verdicts=verdicts, cells49=cells49,
                cell_of=cell_of)


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
                         and g["sea_clearance_ok"] and len(spikes) > 0)
    report["stop_guards"] = g
    log(f"[guards] {json.dumps({k: v for k, v in g.items() if k != 'all_pass'})}")
    log(f"[guards] ALL_PASS={g['all_pass']}")
    return g["all_pass"]


# =================================================================================================
#  STAGE 6 -- APPLY
# =================================================================================================
def stage_apply(report, S, Q):
    if FIXED6.exists():
        shutil.rmtree(FIXED6)
    shutil.copytree(FIXED5, FIXED6)
    n_copied = sum(1 for p in FIXED6.rglob("*") if p.is_file())
    assert n_copied == N_FILES, f"copy mismatch {n_copied} != {N_FILES}"
    log(f"[apply] copied {n_copied} files -> {FIXED6}")

    touched, synth_key, moved = S["touched"], S["synth_key"], Q["moved"]
    meshes = F3.load_blocks(FIXED6, touched)

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
        p = F2.terr_path(FIXED6, *b)
        M.write_ff9mesh(meshes[b], p)
        written[str(p.relative_to(FIXED6))] = sha256_file(p)

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

    f5 = {b: M.read_ff9mesh(F2.terr_path(FIXED5, *b)) for b in touched}
    f6 = {b: M.read_ff9mesh(F2.terr_path(FIXED6, *b)) for b in touched}

    # (1) FLAT-MESH INVARIANT ----------------------------------------------------------------------
    bad = [f"{b[0]},{b[1]}" for b in touched
           if not (f6[b]["vcount"] == len(f6[b]["indices"]) == len(f6[b]["verts"])
                   and len(f6[b]["indices"]) % 3 == 0)]
    v["flat_mesh"] = dict(bad_files=bad, ok=not bad)

    # (2) BYTE RIGIDITY vs FIXED5 ------------------------------------------------------------------
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
    v["byte_rigidity_vs_fixed5"] = rig
    v["uv_tangent_index_byte_identical"] = (rig["uv_bad"] == 0 and rig["tan_bad"] == 0
                                            and rig["idx_bad"] == 0)

    # (2b) the UV invariant re-measured from FIXED6's own bytes -------------------------------------
    uv_degen = 0
    for b in touched:
        uvs = f6[b]["uvs"]
        for t in range(len(f6[b]["indices"]) // 3):
            tri = f6[b]["indices"][3 * t:3 * t + 3]
            if F2.uv_degenerate([(uvs[j][0], uvs[j][1]) for j in tri]):
                uv_degen += 1
    v["one_window_uv_invariant"] = dict(
        uv_bytes_identical_to_fixed5=(rig["uv_bad"] == 0),
        degenerate_uv_tris_all_terrain=uv_degen, zero_uv_area_floor_held=(uv_degen == 0),
        note=("no UV byte is written this round, so FIXED3A's ONE-WINDOW-PER-TRI invariant, its "
              "zero-UV-area floor and round 4's family re-clothe carry over unchanged by definition; "
              "the floor is re-measured from FIXED6's own bytes anyway."))

    # (3) THE WELD AUDIT over ALL 8 PARTS of all 20 blocks ------------------------------------------
    pre_groups = defaultdict(list)
    post_pos = {}
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        for part in PARTS:
            rel = M.override_relpath(1, b[0], b[1], part=part)
            p5, p6 = FIXED5 / rel, FIXED6 / rel
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
    #     that did not move, so before/after are commensurable), plus a re-fit from FIXED6's bytes.
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

    # (8b) THE ROUND IS SELF-TERMINATING -- the whole census re-derived FROM FIXED6'S OWN BYTES ------
    v["recensus_from_disk"] = _recensus(FIXED6, S["touched"], synth_key)
    v["recensus_from_disk"]["fixed5_for_comparison"] = _recensus(FIXED5, S["touched"], synth_key)
    v["recensus_from_disk"]["census_now_empty"] = (v["recensus_from_disk"]["n_qualifying"] == 0)

    # (9) TREE DIFF ---------------------------------------------------------------------------------
    changed = [str(p.relative_to(FIXED5)) for p in sorted(FIXED5.rglob("*"))
               if p.is_file() and sha256_file(p) != sha256_file(FIXED6 / str(p.relative_to(FIXED5)))]
    expected = set(A["written"])
    v["tree_diff_vs_fixed5"] = dict(
        n_files=len(changed), files=changed,
        n_terrain=sum(1 for r in changed if "Terrain" in r),
        n_non_terrain=sum(1 for r in changed if "Terrain" not in r),
        unexpected=[r for r in changed if r not in expected],
        expected_not_changed=[r for r in expected if r not in changed],
        non_terrain_untouched=all("Terrain" in r for r in changed),
        file_count=sum(1 for p in FIXED6.rglob("*") if p.is_file()))

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
              and v["tree_diff_vs_fixed5"]["non_terrain_untouched"]
              and not v["tree_diff_vs_fixed5"]["unexpected"]
              and not v["tree_diff_vs_fixed5"]["expected_not_changed"]
              and v["tree_diff_vs_fixed5"]["file_count"] == N_FILES)
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
        f"{v['recensus_from_disk']['fixed5_for_comparison']['n_qualifying']} (FIXED5) -> "
        f"{v['recensus_from_disk']['n_qualifying']} (FIXED6); max mound prominence "
        f"{v['recensus_from_disk']['fixed5_for_comparison']['max_prominence_in_mound']} -> "
        f"{v['recensus_from_disk']['max_prominence_in_mound']}")
    log(f"[verify] tree diff: {len(changed)} files; OK={ok}")
    return ok


def _recensus(tree, touched, synth_key):
    """Re-derive the ENTIRE census (classification -> reference -> residual -> prominence -> the spike
    rule) from a tree's own bytes on disk.  Run on FIXED6 this is the round's self-termination proof:
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
    mound = [k for k in cg if BASIN_R < rc(k) <= MOUND_R and res[k] is not None]
    qual = [k for k in mound if res[k] >= SPIKE_RES_T and prom[k] >= SPIKE_PROM_T]
    return dict(
        tree=tree.name, n_carried_in_mound=len(mound),
        max_residual_in_mound=round(max(res[k] for k in mound), 4) if mound else None,
        max_prominence_in_mound=round(max(prom[k] for k in mound), 4) if mound else None,
        n_qualifying=len(qual),
        qualifying=[dict(world=[round(k[0], 3), round(k[1], 3), round(k[2], 3)],
                         res=round(res[k], 3), prom=round(prom[k], 3)) for k in qual],
        top_prominence=[dict(world=[round(k[0], 2), round(k[1], 3), round(k[2], 2)],
                             prom=round(prom[k], 3), res=round(res[k], 3), r_crater=round(rc(k), 1))
                        for k in sorted(mound, key=lambda k: -prom[k])[:5]],
        note=("the same five-predicate rule, re-run end to end on this tree's bytes.  On FIXED6 it must "
              "return an EMPTY set -- the round removed exactly what it was defined to find, and what "
              "residual is left in the mound belongs to the crater's own carried rim crest/shoulder "
              "(high residual, near-zero prominence: flush with a neighbour, therefore lawful)."))


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
        script="uvf_fix6.py", read_only_vs_game=True, build_requested=build,
        base_tree=str(FIXED5), out_tree=str(FIXED6),
        work_order=("shave the CARRIED remnant spikes on the crater mound into the local rim surface; "
                    "the crater bowl and the rim's overall height MUST survive"),
        contract_change=("carried positions MAY move -- but ONLY the census-defined SPIKE SET plus fill "
                         "positions welded/graph-adjacent to them; every other carried vertex stays "
                         "byte-rigid, rock stamps (topo 58/31) are exempt, the basin disc is frozen"),
        mechanism=("each site is ONE carried vertex -- the apex of a kept topo-41 dunes tri pair -- "
                   "riding above every vertex it is welded to, with round-5's relaxed fill ramping up "
                   "to meet it; the roots/massif that gave it context are ABSENT"),
        method=("two-predicate census (residual vs a leave-one-out, BASIN-EXCLUDED local rim reference "
                "AND strict mesh prominence) -> harmonic Laplacian least squares on the spike patch, "
                "Dirichlet dY=0 at every pinned position"))}

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
        log("[main] probe-only (pass --build to emit FIXED6).")

    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"\n{'=' * 80}\nwrote {REPORT}  ok={report.get('ok')}")
    return report


if __name__ == "__main__":
    main()
