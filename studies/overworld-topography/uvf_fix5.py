"""RUNG F -- THE ROOTS RELIEF RELAX (geometry-fix round 5, 2026-07-24).

Playtest 3 on FIXED4: the family re-clothe WORKED ("they almost look gone") but the GEOMETRY still
carries the dropped Cleyra roots -- elongated channel/cleft depressions radiating out of the crater
rim, a raised face/nub at each channel's crater end, and local "dig spot" pits.

``uvf_relief_probe.py`` MEASURED the mechanism and it is simpler than the hypothesis: NO movable fill
vertex carries a donor Y. 936 of 937 sit at EXACTLY ``rung_f_layout.LAND_HEIGHT`` = 3.000000 (the
``carry()`` flatten branch); one is an interpolated stitch vertex. What is stamped into the terrain is
a DEAD-FLAT 3.000u sheet welded into an undulating carried surface (kept ground Y 1.693..7.201, p50
3.000, p95 3.896). The channels are where the sheet lies 1-3.7u BELOW the carried rim; the "raised
face/nub" is the synthesized triangle that BRIDGES the two (126 synth tris span >=1u internally, 33
span >=3u, max dip 73.75 deg, every one of them with y_lo exactly 3.000).

THE WORK ORDER (owner-ratified): the roots are ABSENT, so the ground should continue smoothly --
relax the anomalous fill relief into the surrounding sand. THE CRATER MUST SURVIVE.

WHAT THIS SCRIPT DOES -- and what it deliberately does NOT
  * MOVABLE = the 937 positions every one of whose vertex entries (across Terrain/Object/Beach1/
    Sea1..Sea5 of all 20 touched blocks) belongs to one of the 2305 SYNTHESIZED tris. A single kept
    entry PINS the position (Dirichlet). 433 of the 1370 synth-touched positions are pinned that way.
  * THE CRATER is EXCLUDED, not trusted to the solve. The basin at (127.14,-1161.42) has a
    SYNTHESIZED floor (14 movable positions, all at Y=3.000, 3.265u below its CARRIED rim) -- a
    blanket relax would fill the crater in. It is separated from all 21 wedge clusters by three
    unanimous, non-overlapping discriminators (dropped-donor topo 59-decal vs 49-mural; enclosure
    0.951 vs 0.000-0.604; plan elongation 1.29 vs 1.36-16.1) and its 14 positions are pinned at dY=0.
  * THE SOLVE is HARMONIC least squares on the synthesized patch's OWN edge graph -- data term
    dY = -residual (weight 4.0 on the anomalous core, 1.0 "hold your ground" elsewhere), smoothness
    (dY_i - dY_j) on every patch edge, Dirichlet dY=0 on every edge to a pinned position. The blend is
    therefore a MESH function, not a distance falloff, so it reaches exactly zero at the pins and
    cannot mint a new ledge at the scope boundary (the failure mode a cosine-distance falloff has by
    construction: it pulls a ring vertex without knowing the pin behind it and merely RELOCATES the
    step one vertex over -- i.e. re-mints the reported terminal face).

SCOPE + SOLVE ARE IMPORTED FROM THE PROBE, NOT RE-IMPLEMENTED. ``uvf_relief_probe``'s own stage
functions are called verbatim (stage1 movable set -> stage2 reference surface -> stage3 residuals ->
stage4 mechanism/clusters -> stage5b basin exclusion -> stage6 solve), so the dY applied here IS the
dry run the probe reported, bit for bit. Divergence is impossible by construction.

INVARIANTS (all asserted in stage 6 against the bytes on disk)
  Y-ONLY: X/Z frozen. UVs, tangents (hence the IDALL topograph) and indices byte-identical to FIXED4
  everywhere -- so the ONE-WINDOW-PER-TRI UV invariant of FIXED3A/FIXED4 is untouched by definition.
  Normals: per-tri GEOMETRIC up-facing, recomputed for every synthesized tri with a moved vert AND
  ONLY those. Weld: dY is keyed on the ROUNDED 3D WORLD POSITION, so all 3-17 vertex entries at a
  moved position (166 of them span more than one block) receive the identical delta; a post-move
  coincident-position audit over all 8 parts of all 20 blocks proves no group split. verts==idx
  preserved. No new down-facing tri (a Y-only move cannot change the geometric normal's Y sign at
  all: that component is a pure X/Z cross product -- proven, then verified). Land stays above Sea
  Y=0. Only the dirty Terrain files change.

READ-ONLY vs the game install. Emits out/rung_f/FF9CustomMap-world-FIXED5 + uvf_fix5_report.json.
Renders nothing -- the eye lane owns judgment.

    py -X utf8 uvf_fix5.py            # probe-only (scope + solve dry run, writes nothing)
    py -X utf8 uvf_fix5.py --build    # emit FIXED5 + the full self-check
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

import uvf_fix2 as F2                                           # noqa: E402
import uvf_fix3 as F3                                           # noqa: E402
import uvf_relief_probe as P                                    # noqa: E402

CH_POS, CH_NRM, CH_UV, CH_TAN = X.CH_POS, X.CH_NRM, X.CH_UV, X.CH_TAN

RUNG_F = HERE / "out" / "rung_f"
FIXED4 = RUNG_F / "FF9CustomMap-world-FIXED4"
FIXED5 = RUNG_F / "FF9CustomMap-world-FIXED5"
FIX4_REPORT = RUNG_F / "uvf_fix4_report.json"
REPORT = RUNG_F / "uvf_fix5_report.json"

PARTS = P.PARTS
N_FILES = 180
N_SYNTH = 2305
SEA_Y = 0.0
MIN_LAND_Y = 0.5           # the clearance floor a moved vertex must stay above
AREA_EPS = 1e-9            # world-space triangle area under which a tri counts as 3D-degenerate
NRM_EPS = 1e-12


def log(m):
    print(m, flush=True)


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tri_geo(a, b, c):
    """Raw (unnormalized) geometric normal of a triangle, in the mesh's own winding."""
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    wx, wy, wz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    return (uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx)


def up_normal(a, b, c):
    """Unit geometric normal forced UP-FACING (ny>=0) -- the convention uvf_fix round 1 used for the
    apron tris.  Returns None when the triangle has no area (never normalize a zero vector)."""
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


# =================================================================================================
#  STAGE A -- SCOPE + SOLVE (imported verbatim from the probe)
# =================================================================================================
def stage_scope(report):
    probe = {"meta": dict(reused_by="uvf_fix5.py")}
    touched, f4_meshes, defective, synth_key, prov_of, pos_entries, pinned, movable = P.stage1(probe)

    fix4 = json.loads(FIX4_REPORT.read_text(encoding="utf-8"))
    fill_fam_of_cell = {}
    for k, v in fix4["fill_cell_detail"].items():
        a, b = k.split(",")
        fill_fam_of_cell[(int(a), int(b))] = v["fam"]

    _ground_pos, ghash, samples = P.stage2(probe, touched, f4_meshes, synth_key)
    rows = P.stage3(probe, movable, pos_entries, prov_of, ghash, samples, fill_fam_of_cell)
    donor = P.load_donor(probe)
    anom, clusters = P.stage4(probe, rows, donor, ghash, samples)
    excl, inside = P.stage5b(probe, rows, clusters, ghash, samples)
    coreset, blend, moved = P.stage6(probe, rows, anom, movable, pinned, pos_entries,
                                     touched, f4_meshes, synth_key, excl)

    for c in probe["stage4_mechanism"]["clusters"]:
        c.pop("_keys", None)
    report["scope"] = dict(
        source="uvf_relief_probe.py stage1/2/3/4/5b/6 called VERBATIM -- the applied dY IS the dry run",
        movable_set=probe["stage1_movable_set"],
        reference_surface=probe["stage2_reference_surface"],
        residuals=probe["stage3_residuals"],
        basin_exclusion=probe["stage5b_basin_exclusion"],
        solve=probe["stage6_solve_dryrun"],
        face_collapse_check=probe["stage6_face_collapse_check"],
        proposal=probe["stage6_scope_proposal"],
        clusters=probe["stage4_mechanism"]["clusters"],
        basin_dem=probe.get("stage6_basin_dem"))
    return dict(touched=touched, f4_meshes=f4_meshes, defective=defective, synth_key=synth_key,
                pos_entries=pos_entries, pinned=pinned, movable=movable, rows=rows, anom=anom,
                excl=excl, inside=inside, coreset=coreset, blend=blend, moved=moved,
                ghash=ghash, samples=samples, probe=probe)


# =================================================================================================
#  STAGE B -- THE STOP GUARDS (every way the scope could be wrong, checked BEFORE a byte is written)
# =================================================================================================
def stage_guards(report, S):
    g = {}
    moved, movable, pinned = S["moved"], S["movable"], S["pinned"]
    rows = S["rows"]
    by_key = {r["k"]: r for r in rows}
    excluded = {r["k"] for r in rows if r.get("crater_excluded")}

    g["n_synthesized_tris"] = len(S["defective"])
    g["synth_tris_is_2305"] = (len(S["defective"]) == N_SYNTH)
    g["n_movable"] = len(movable)
    g["n_moved"] = len(moved)
    g["moved_subset_of_movable"] = not (set(moved) - set(movable))
    g["moved_disjoint_from_pinned"] = not (set(moved) & pinned)
    g["n_basin_clusters"] = len(S["excl"])
    g["basin_exclusion_nonempty"] = len(S["excl"]) >= 1 and len(excluded) > 0
    g["n_crater_excluded_positions"] = len(excluded)
    g["max_abs_dY_on_crater_excluded"] = round(max((abs(moved.get(k, 0.0)) for k in excluded),
                                                   default=0.0), 6)
    g["crater_excluded_frozen"] = (g["max_abs_dY_on_crater_excluded"] == 0.0)

    # the CRATER-RIM guard, stated the owner's way: no position that any KEPT (carried) triangle
    # touches may receive a delta.  This is the literal "if the crater rim would move, STOP".
    kept_touched = 0
    for b in S["touched"]:
        bm = S["f4_meshes"][b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[CH_POS]
        for t, tri in enumerate(bm.tris):
            if (b, t) in S["synth_key"]:
                continue
            for j in tri:
                v = verts[j]
                if P.pkey((v[0] + ox, v[1], v[2] + oz)) in moved:
                    kept_touched += 1
    g["kept_terrain_vertices_that_would_move"] = kept_touched
    g["kept_content_frozen"] = (kept_touched == 0)

    newY = [by_key[k]["y"] + v for k, v in moved.items()]
    g["predicted_min_Y_after"] = round(min(newY), 4) if newY else None
    g["predicted_max_abs_dY"] = round(max(abs(v) for v in moved.values()), 4) if moved else 0.0
    g["sea_clearance_ok"] = bool(not newY or min(newY) > MIN_LAND_Y)

    g["all_pass"] = bool(g["synth_tris_is_2305"] and g["moved_subset_of_movable"]
                         and g["moved_disjoint_from_pinned"] and g["basin_exclusion_nonempty"]
                         and g["crater_excluded_frozen"] and g["kept_content_frozen"]
                         and g["sea_clearance_ok"])
    report["stop_guards"] = g
    log(f"[guards] {json.dumps({k: v for k, v in g.items() if k != 'all_pass'})}")
    log(f"[guards] ALL_PASS={g['all_pass']}")
    return g["all_pass"]


# =================================================================================================
#  STAGE C -- APPLY
# =================================================================================================
def stage_apply(report, S):
    if FIXED5.exists():
        shutil.rmtree(FIXED5)
    shutil.copytree(FIXED4, FIXED5)
    n_copied = sum(1 for p in FIXED5.rglob("*") if p.is_file())
    assert n_copied == N_FILES, f"copy mismatch {n_copied} != {N_FILES}"
    log(f"[apply] copied {n_copied} files -> {FIXED5}")

    touched, synth_key, moved = S["touched"], S["synth_key"], S["moved"]
    meshes = F3.load_blocks(FIXED5, touched)

    # ---- PASS 1: resolve every synthesized vertex entry against the PRE-move position key --------
    plan = {b: {} for b in touched}                 # block -> vid -> dY
    moved_tris = {b: set() for b in touched}
    per_block_pos = defaultdict(set)
    entries_per_pos = Counter()
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[CH_POS]
        for t, tri in enumerate(bm.tris):
            if (b, t) not in synth_key:
                continue
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

    # every moved POSITION must have been found (else a key/rounding mismatch silently dropped it)
    found = set()
    for k in per_block_pos:
        found.add(k)
    missing = set(moved) - found
    assert not missing, f"{len(missing)} solved positions not located in the mesh -- key mismatch"

    # ---- PASS 2: the Y-only move (X/Z untouched, per POSITION so every coincident copy agrees) ---
    n_vert_entries = 0
    for b in touched:
        verts = meshes[b].chan_arrays[CH_POS]
        for j, dy in plan[b].items():
            verts[j][1] = verts[j][1] + dy
            n_vert_entries += 1

    # ---- PASS 3: per-tri GEOMETRIC up-facing normals, on the moved tris ONLY ---------------------
    nrm_changed_vids = defaultdict(set)
    n_nrm_tris = 0
    n_nrm_skipped_zero_area = 0
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts, nrm = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_NRM]
        for t in sorted(moved_tris[b]):
            tri = bm.tris[t]
            P3 = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in tri]
            nv = up_normal(*P3)
            if nv is None:
                n_nrm_skipped_zero_area += 1
                continue
            for j in tri:
                nrm[j] = list(nv)
                nrm_changed_vids[b].add(j)
            n_nrm_tris += 1

    dirty = sorted(b for b in touched if plan[b])
    written = {}
    for b in dirty:
        p = F2.terr_path(FIXED5, *b)
        M.write_ff9mesh(meshes[b], p)
        written[str(p.relative_to(FIXED5))] = sha256_file(p)

    dys = np.array(list(moved.values()))
    report["stage_apply"] = dict(
        positions_moved=len(moved),
        vertex_entries_moved=n_vert_entries,
        entries_per_moved_position=dict(sorted(Counter(entries_per_pos.values()).items())),
        synth_tris_with_a_moved_vert=sum(len(v) for v in moved_tris.values()),
        normal_tris_recomputed=n_nrm_tris,
        normal_tris_skipped_zero_area=n_nrm_skipped_zero_area,
        normal_verts_rewritten=sum(len(s) for s in nrm_changed_vids.values()),
        blocks_written=[list(b) for b in dirty],
        positions_spanning_multiple_blocks=sum(1 for k in moved if len(per_block_pos[k]) > 1),
        dY=P.stats(dys),
        max_abs_dY=round(float(np.abs(dys).max()), 4),
        move_axis="Y only -- X and Z are never written",
        normal_convention="per-tri geometric normal, forced ny>=0 (the uvf_fix round-1 apron rule)")
    log(f"[apply] moved {len(moved)} positions / {n_vert_entries} vertex entries; "
        f"normals on {n_nrm_tris} tris ({sum(len(s) for s in nrm_changed_vids.values())} verts); "
        f"wrote {len(dirty)} Terrain files; max|dY|={float(np.abs(dys).max()):.4f}")
    return dict(plan=plan, moved_tris=moved_tris, nrm_changed_vids=nrm_changed_vids,
                dirty=dirty, written=written, n_vert_entries=n_vert_entries)


# =================================================================================================
#  STAGE D -- SELF-CHECK (everything against the BYTES ON DISK)
# =================================================================================================
def stage_verify(report, S, A):
    v = {}
    touched, synth_key, moved = S["touched"], S["synth_key"], S["moved"]
    rows = S["rows"]
    by_key = {r["k"]: r for r in rows}

    f4 = {b: M.read_ff9mesh(F2.terr_path(FIXED4, *b)) for b in touched}
    f5 = {b: M.read_ff9mesh(F2.terr_path(FIXED5, *b)) for b in touched}

    # (1) FLAT-MESH INVARIANT (verts == idx) on every Terrain file ---------------------------------
    flat_bad = []
    for b in touched:
        d = f5[b]
        if not (d["vcount"] == len(d["indices"]) == len(d["verts"]) and len(d["indices"]) % 3 == 0):
            flat_bad.append(f"{b[0]},{b[1]}")
    v["flat_mesh"] = dict(bad_files=flat_bad, ok=not flat_bad,
                          vcount_equals_idx_all_20=all(f5[b]["vcount"] == len(f5[b]["indices"])
                                                       for b in touched))

    # (2) BYTE RIGIDITY vs FIXED4: uv / tangents / indices identical, positions ONLY at planned vids,
    #     normals ONLY on the moved tris' vids -----------------------------------------------------
    rig = dict(uv_bad=0, tan_bad=0, idx_bad=0, vcount_bad=0,
               pos_expected=0, pos_unexpected=0, pos_xz_moved=0,
               nrm_expected=0, nrm_unexpected=0)
    for b in touched:
        a, f = f4[b], f5[b]
        rig["uv_bad"] += (a["uvs"] != f["uvs"])
        rig["tan_bad"] += (a["tangents"] != f["tangents"])
        rig["idx_bad"] += (a["indices"] != f["indices"])
        rig["vcount_bad"] += (a["vcount"] != f["vcount"])
        planned = A["plan"][b]
        nchg = A["nrm_changed_vids"].get(b, set())
        for j in range(a["vcount"]):
            if a["verts"][j] != f["verts"][j]:
                if j in planned:
                    rig["pos_expected"] += 1
                else:
                    rig["pos_unexpected"] += 1
                if a["verts"][j][0] != f["verts"][j][0] or a["verts"][j][2] != f["verts"][j][2]:
                    rig["pos_xz_moved"] += 1
            if a["normals"][j] != f["normals"][j]:
                if j in nchg:
                    rig["nrm_expected"] += 1
                else:
                    rig["nrm_unexpected"] += 1
    v["byte_rigidity_vs_fixed4"] = rig
    v["uv_tangent_index_byte_identical"] = (rig["uv_bad"] == 0 and rig["tan_bad"] == 0
                                            and rig["idx_bad"] == 0)
    v["one_window_uv_invariant"] = dict(
        uv_bytes_identical_to_fixed4=(rig["uv_bad"] == 0),
        note=("no UV byte is written this round, so FIXED3A/FIXED4's ONE-WINDOW-PER-TRI invariant and "
              "its zero-UV-area floor carry over unchanged by definition; re-measured below anyway."))

    # (2b) the UV invariant re-MEASURED from FIXED5's own bytes (not merely inferred) ---------------
    uv_degen = 0
    for b in touched:
        uvs = f5[b]["uvs"]
        for t in range(len(f5[b]["indices"]) // 3):
            tri = f5[b]["indices"][3 * t:3 * t + 3]
            if F2.uv_degenerate([(uvs[j][0], uvs[j][1]) for j in tri]):
                uv_degen += 1
    v["one_window_uv_invariant"]["degenerate_uv_tris_all_terrain"] = uv_degen

    # (3) THE WELD AUDIT -- coincident-position groups over ALL 8 PARTS of all 20 blocks, rebuilt
    #     from disk BEFORE and AFTER; a group that splits is a crack ------------------------------
    pre_groups = defaultdict(list)      # pre poskey -> [(block, part, vid)]
    post_pos = {}                       # (block, part, vid) -> post poskey
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        for part in PARTS:
            rel = M.override_relpath(1, b[0], b[1], part=part)
            p4, p5 = FIXED4 / rel, FIXED5 / rel
            if not p4.exists():
                continue
            d4 = M.read_ff9mesh(p4)
            d5 = M.read_ff9mesh(p5)
            assert d4["vcount"] == d5["vcount"], f"vcount drift in {rel}"
            for j in range(d4["vcount"]):
                a, c = d4["verts"][j], d5["verts"][j]
                pre_groups[P.pkey((a[0] + ox, a[1], a[2] + oz))].append((b, part, j))
                post_pos[(b, part, j)] = P.pkey((c[0] + ox, c[1], c[2] + oz))
    split = []
    nonuniform = []
    groups_moved = 0
    for k, ents in pre_groups.items():
        outs = {post_pos[e] for e in ents}
        if len(outs) != 1:
            split.append(dict(pre=list(k), n_entries=len(ents), post=[list(o) for o in sorted(outs)]))
        elif next(iter(outs)) != k:
            groups_moved += 1
        # the LOAD-BEARING property: did every entry of this group receive the SAME delta?
        deltas = {A["plan"][e[0]].get(e[2], 0.0) if e[1] == "Terrain" else 0.0 for e in ents}
        if len(deltas) != 1:
            nonuniform.append(dict(pre=list(k), n_entries=len(ents), deltas=sorted(deltas)))
    # a group whose |dY| is under the 3dp position-key resolution cannot register as "moved" in the
    # key space even though its bytes did change -- account for those instead of ignoring them.
    sub_key = [k for k, dv in moved.items() if abs(dv) < 0.5 * 10 ** (-P.POS_DP)]
    v["weld_audit"] = dict(
        n_distinct_positions_all_parts=len(pre_groups),
        groups_that_split=len(split), split_examples=split[:10],
        groups_with_nonuniform_delta=len(nonuniform), nonuniform_examples=nonuniform[:10],
        groups_that_moved=groups_moved, solver_moved_positions=len(moved),
        moved_below_position_key_resolution=len(sub_key),
        max_abs_dY_below_key_resolution=round(max((abs(moved[k]) for k in sub_key), default=0.0), 6),
        moved_groups_reconcile=(groups_moved + len(sub_key) == len(moved)),
        multi_entry_groups_moved=sum(1 for k in moved if len(pre_groups[k]) > 1),
        cross_block_groups_moved=sum(1 for k in moved
                                     if len({e[0] for e in pre_groups[k]}) > 1),
        cross_part_groups_moved=sum(1 for k in moved
                                    if len({e[1] for e in pre_groups[k]}) > 1),
        ok=(not split and not nonuniform and groups_moved + len(sub_key) == len(moved)),
        note=("every vertex entry sharing a rounded 3D world position received the identical dY "
              "(groups_with_nonuniform_delta must be 0) and no coincident group split -- audited "
              "across Terrain/Object/Beach1/Sea1..Sea5 of all 20 touched blocks, i.e. across parts "
              "AND block borders. groups_that_moved counts groups whose 3dp KEY changed, so it is "
              "short by exactly the positions whose |dY| < 0.0005 -- reconciled explicitly."))

    # (3b) PINNED positions provably frozen -------------------------------------------------------
    pin_moved = sum(1 for k in S["pinned"] if k in pre_groups
                    and post_pos[pre_groups[k][0]] != k)
    v["pinned_positions_moved"] = pin_moved

    # (4) NO NEW DOWN-FACING TRI.  A Y-only move cannot change the geometric normal's Y component at
    #     all: ny = (bx-ax)(cz-az) - (bz-az)(cx-ax) is a pure X/Z expression.  Proven, then verified
    #     tri by tri over EVERY Terrain triangle of all 20 blocks. -------------------------------
    ny_sign_before = Counter()
    ny_sign_after = Counter()
    ny_changed = 0
    newly_down = 0
    dip_before, dip_after = [], []
    degen3d_before = degen3d_after = 0
    for b in touched:
        ox, oz = X.block_world_origin(*b)
        d4, d5 = f4[b], f5[b]
        for t in range(len(d5["indices"]) // 3):
            tri = d5["indices"][3 * t:3 * t + 3]
            A3 = [(d4["verts"][j][0] + ox, d4["verts"][j][1], d4["verts"][j][2] + oz) for j in tri]
            B3 = [(d5["verts"][j][0] + ox, d5["verts"][j][1], d5["verts"][j][2] + oz) for j in tri]
            na = tri_geo(*A3)[1]
            nb = tri_geo(*B3)[1]
            sa = (0 if abs(na) < NRM_EPS else (1 if na > 0 else -1))
            sb = (0 if abs(nb) < NRM_EPS else (1 if nb > 0 else -1))
            ny_sign_before[sa] += 1
            ny_sign_after[sb] += 1
            if sa != sb:
                ny_changed += 1
            if sa >= 0 and sb < 0:
                newly_down += 1
            aa, ab = tri_area(*A3), tri_area(*B3)
            degen3d_before += (aa < AREA_EPS)
            degen3d_after += (ab < AREA_EPS)
            if (b, t) in synth_key:
                for (pts, out) in ((A3, dip_before), (B3, dip_after)):
                    nx, ny, nz = tri_geo(*pts)
                    ln = math.sqrt(nx * nx + ny * ny + nz * nz)
                    out.append(90.0 if ln < NRM_EPS
                               else math.degrees(math.acos(min(1.0, abs(ny) / ln))))
    v["down_facing"] = dict(
        geometric_ny_sign_before={str(k): x for k, x in sorted(ny_sign_before.items())},
        geometric_ny_sign_after={str(k): x for k, x in sorted(ny_sign_after.items())},
        tris_whose_ny_sign_changed=ny_changed, newly_down_facing_tris=newly_down,
        ok=(newly_down == 0 and ny_changed == 0),
        proof=("ny of the face cross product = (bx-ax)(cz-az) - (bz-az)(cx-ax) -- a pure X/Z "
               "expression, so a Y-only move leaves the winding/facing exactly invariant; verified "
               "tri by tri over every Terrain triangle of all 20 blocks."))
    v["stored_normals_all_up_facing"] = dict(
        min_ny_on_rewritten=round(min((f5[b]["normals"][j][1]
                                       for b in touched for j in A["nrm_changed_vids"].get(b, ())),
                                      default=1.0), 6))
    v["synth_tri_dip_deg"] = dict(before=P.stats(dip_before), after=P.stats(dip_after))
    v["degenerate_3d_area"] = dict(
        tris_before=degen3d_before, tris_after=degen3d_after,
        new_degenerate=max(0, degen3d_after - degen3d_before),
        area_eps=AREA_EPS,
        ok=(degen3d_after <= degen3d_before),
        note=("a Y-only move can only ever GROW a triangle's 3D area (the XZ-plan component is "
              "frozen and is a lower bound on it), so no fill tri can collapse; measured anyway."))

    # (5) LAND ABOVE SEA --------------------------------------------------------------------------
    all_y = [d["verts"][j][1] for b in touched for d in (f5[b],) for j in range(d["vcount"])]
    moved_y = [by_key[k]["y"] + dv for k, dv in moved.items()]
    v["land_above_sea"] = dict(
        sea_y=SEA_Y, min_Y_over_moved_positions=round(min(moved_y), 4) if moved_y else None,
        min_Y_all_terrain_verts=round(min(all_y), 4),
        min_Y_all_terrain_verts_before=round(min(f4[b]["verts"][j][1] for b in touched
                                                 for j in range(f4[b]["vcount"])), 4),
        moved_positions_below_floor=sum(1 for y in moved_y if y <= MIN_LAND_Y),
        ok=bool(not moved_y or min(moved_y) > MIN_LAND_Y))

    # (6) THE CRATER, re-measured FROM DISK --------------------------------------------------------
    excluded = [r for r in rows if r.get("crater_excluded")]
    exc_moved = [abs(moved.get(r["k"], 0.0)) for r in excluded]
    # the basin's own floor + the carried rim, read back out of FIXED5
    ex = S["excl"][0] if S["excl"] else None
    floor_after, rim_after = [], []
    if ex:
        cx, cz = ex["center"]
        for b in touched:
            ox, oz = X.block_world_origin(*b)
            d5 = f5[b]
            for t in range(len(d5["indices"]) // 3):
                tri = d5["indices"][3 * t:3 * t + 3]
                for j in tri:
                    x, y, z = d5["verts"][j][0] + ox, d5["verts"][j][1], d5["verts"][j][2] + oz
                    d = math.hypot(x - cx, z - cz)
                    if d <= ex["radius_u"]:
                        (floor_after if (b, t) in synth_key else rim_after).append(y)
    v["crater_untouched"] = dict(
        basin_center=ex["center"] if ex else None, basin_radius_u=ex["radius_u"] if ex else None,
        n_excluded_fill_positions=len(excluded),
        max_abs_dY_on_excluded=round(max(exc_moved), 6) if exc_moved else 0.0,
        basin_depth_before_u=round(float(np.mean([-r["res"] for r in excluded])), 3) if excluded else None,
        basin_depth_after_u=round(float(np.mean([-(r["res"] + moved.get(r["k"], 0.0))
                                                 for r in excluded])), 3) if excluded else None,
        basin_floor_y_after=P.stats(floor_after) if floor_after else dict(n=0),
        carried_rim_y_after=P.stats(rim_after) if rim_after else dict(n=0),
        carried_rim_position_diffs_vs_fixed4=sum(
            1 for b in touched for j in range(f4[b]["vcount"])
            if f4[b]["verts"][j] != f5[b]["verts"][j] and j not in A["plan"][b]),
        crater_wall_faces_within_12u=S["probe"]["stage6_face_collapse_check"][
            "crater_wall_faces_within_12u_of_basin"],
        ok=bool(not exc_moved or max(exc_moved) == 0.0))

    # (7) THE OUTCOME -- residuals re-measured against the SAME (kept, hence unmoved) reference ----
    after_res = []
    for r in rows:
        after_res.append(r["res"] + moved.get(r["k"], 0.0))
    core = [r for r in rows if abs(r["res"]) >= P.ANOM_T and not r.get("crater_excluded")]
    v["relief_outcome"] = dict(
        residual_all_movable_before=P.stats([r["res"] for r in rows]),
        residual_all_movable_after=P.stats(after_res),
        core_residual_before=P.stats([r["res"] for r in core]),
        core_residual_after=P.stats([r["res"] + moved.get(r["k"], 0.0) for r in core]),
        anomalies_before=int(sum(1 for r in rows if abs(r["res"]) >= P.ANOM_T)),
        anomalies_after=int(sum(1 for a in after_res if abs(a) >= P.ANOM_T)),
        anomalies_after_excluding_basin=int(sum(
            1 for r in rows if not r.get("crater_excluded")
            and abs(r["res"] + moved.get(r["k"], 0.0)) >= P.ANOM_T)),
        steep_face_span=dict(before=S["probe"]["stage6_face_collapse_check"]["all_faces_before"],
                             after=S["probe"]["stage6_face_collapse_check"]["all_faces_after"]),
        note=("the reference surface is fit from KEPT ground only and kept ground never moves, so the "
              "before/after residuals are measured against one and the same surface."))

    # (8) TREE DIFF -- only the dirty Terrain files may differ ------------------------------------
    changed = []
    for p in sorted(FIXED4.rglob("*")):
        if p.is_file() and sha256_file(p) != sha256_file(FIXED5 / str(p.relative_to(FIXED4))):
            changed.append(str(p.relative_to(FIXED4)))
    expected = set(A["written"])
    v["tree_diff_vs_fixed4"] = dict(
        n_files=len(changed), files=changed,
        n_terrain=sum(1 for r in changed if "Terrain" in r),
        n_non_terrain=sum(1 for r in changed if "Terrain" not in r),
        unexpected=[r for r in changed if r not in expected],
        expected_not_changed=[r for r in expected if r not in changed],
        non_terrain_untouched=all("Terrain" in r for r in changed),
        sea_parts_untouched=all(not any(s in r for s in ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5"))
                                for r in changed),
        object_beach_untouched=all("Object" not in r and "Beach" not in r for r in changed),
        file_count=sum(1 for p in FIXED5.rglob("*") if p.is_file()))

    ok = bool(v["flat_mesh"]["ok"] and v["weld_audit"]["ok"] and v["down_facing"]["ok"]
              and v["degenerate_3d_area"]["ok"] and v["land_above_sea"]["ok"]
              and v["crater_untouched"]["ok"] and v["uv_tangent_index_byte_identical"]
              and rig["pos_unexpected"] == 0 and rig["pos_xz_moved"] == 0
              and rig["nrm_unexpected"] == 0 and rig["vcount_bad"] == 0
              and pin_moved == 0
              and v["tree_diff_vs_fixed4"]["non_terrain_untouched"]
              and not v["tree_diff_vs_fixed4"]["unexpected"]
              and not v["tree_diff_vs_fixed4"]["expected_not_changed"]
              and v["tree_diff_vs_fixed4"]["file_count"] == N_FILES
              and v["one_window_uv_invariant"]["degenerate_uv_tris_all_terrain"] == 0)
    report["stage_verify"] = v
    report["ok"] = ok
    log(f"[verify] flat={v['flat_mesh']['ok']} weld={v['weld_audit']['ok']} "
        f"(split={v['weld_audit']['groups_that_split']}, moved-groups="
        f"{v['weld_audit']['groups_that_moved']}) down_facing_new={v['down_facing']['newly_down_facing_tris']} "
        f"degen3d={v['degenerate_3d_area']['tris_after']} minY={v['land_above_sea']['min_Y_all_terrain_verts']}")
    log(f"[verify] rigidity {rig}  pinned_moved={pin_moved}  uv_degen={uv_degen}")
    log(f"[verify] crater max|dY| on excluded={v['crater_untouched']['max_abs_dY_on_excluded']} "
        f"depth {v['crater_untouched']['basin_depth_before_u']} -> "
        f"{v['crater_untouched']['basin_depth_after_u']}")
    log(f"[verify] tree diff: {len(changed)} files ({v['tree_diff_vs_fixed4']['n_terrain']} Terrain / "
        f"{v['tree_diff_vs_fixed4']['n_non_terrain']} other)")
    log(f"[verify] anomalies |res|>={P.ANOM_T}: {v['relief_outcome']['anomalies_before']} -> "
        f"{v['relief_outcome']['anomalies_after']} "
        f"({v['relief_outcome']['anomalies_after_excluding_basin']} outside the basin)")
    log(f"[verify] OK={ok}")
    return ok


# =================================================================================================
def main():
    build = "--build" in sys.argv
    report = {"meta": dict(
        script="uvf_fix5.py", read_only_vs_game=True, build_requested=build,
        base_tree=str(FIXED4), out_tree=str(FIXED5),
        work_order=("relax the anomalous synthesized-fill RELIEF into the surrounding sand; the "
                    "crater rim/bowl MUST survive"),
        mechanism=("the movable fill is a DEAD-FLAT land_height=3.000 sheet welded into an "
                   "undulating carried surface -- 936/937 movable positions sit exactly at 3.000000 "
                   "and ZERO carry a donor Y; the channels are where the sheet lies below the "
                   "carried rim and the 'face/nub' is the synthesized tri that bridges the two"),
        method=("harmonic (Laplacian) least squares on the synthesized patch's own edge graph: data "
                "term dY=-residual (w=4 on the anomalous core, w=1 hold-your-ground elsewhere), "
                "smoothness on every patch edge, Dirichlet dY=0 at every pinned position -- C0 into "
                "the pins BY CONSTRUCTION, so no new ledge can appear at the scope boundary"),
        scope_source="uvf_relief_probe.py stage1/2/3/4/5b/6 called verbatim (dry run == applied dY)")}

    S = stage_scope(report)
    passed = stage_guards(report, S)
    if not passed:
        report["ok"] = False
        report["refused"] = ("a STOP guard failed -- the probe's scope does not hold on this tree; "
                             "nothing was written")
        REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
        log(f"REFUSED TO BUILD -- wrote {REPORT}")
        return report

    if build:
        A = stage_apply(report, S)
        stage_verify(report, S, A)
    else:
        report["ok"] = None
        log("[main] probe-only (pass --build to emit FIXED5).")

    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"\n{'=' * 80}\nwrote {REPORT}  ok={report.get('ok')}")
    return report


if __name__ == "__main__":
    main()
