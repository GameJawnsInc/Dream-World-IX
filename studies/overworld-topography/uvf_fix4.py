"""RUNG F -- THE ROOTS RE-CLOTHE (UV-fix round 4, 2026-07-24).

Playtest 2 PASSED on FIXED3A ("solid work"). The owner's one note: the radiating wedges around the
crater are the DROPPED-topo-49 CLEYRA ROOT footprints, hole-filled as blanket GRASS straight through
the dunes/desert donut. Probe (donor frame): dropped topo within 14 cells of the crater center =
{49: 896, 59: 39, 10: 9}; the KEPT tris ringing those dropped cells = {grass 891, dunes 542,
desert 72}. So a desert/dunes-ringed footprint is wearing grass mains.

THE LAW (the orphan-decal law's HOLE-FILL analogue, owner-ratified): an absent feature's footprint
wears the SURROUNDING family. Fill ringed by dunes wears dunes mains; ringed by desert wears desert
mains; ringed by grass stays grass (byte-identical -- that is how the crater's carried bowl and the
grass lobe survive untouched).

WHAT IS REWRITABLE: exactly the 2305 SYNTHESIZED tris (hole-fill 1765 + apron 321 + stitch 218 + 1
stray) -- the tris FIXED3A rewrote, identified here as the SPECIMEN's UV-degenerate set AND
cross-checked as the FIXED3A-vs-SPEC UV diff (must agree exactly). Everything else (carried-core
1454, lawful frame-mint 3237, Sea4, every other part) is BYTE-RIGID.

THE MECHANISM
  1. FAMILY FIELD (stage 2). Every KEPT (non-synthesized) Terrain tri of the DEPLOYED FIXED3A tree
     votes its ground family into its centroid 4u cell, family = ``grassland.TOPO_FAMILY[topo]``
     (0/1/2/3/10/11/12/13/42 -> grass, 16/17/19/20 -> desert, 41 -> dunes). Non-ground topos
     (murals 49, decals 59, rock, water) ABSTAIN. Each FILL cell (a cell holding a synthesized tri
     centroid) then takes the family of its NEAREST source cell -- exact squared-Euclidean over the
     cell lattice, so there is no diagonal/BFS bias; ties inside the nearest ring break by kept-tri
     majority, then by absorbing the next ring, then lexically (each path counted). A fill cell that
     also holds kept ground content is its own source at distance 0.
  2. WINDOW REUSE (stage 3). The (quad,ori) field is REBUILT BIT-IDENTICALLY to uvf_fix3's (method-a
     neighbour-decode of the specimen's lawful grass + ``uvf_fix2.assign_mains_seeded`` seed 0xF92 for
     the dropped cells) and the ONE-WINDOW-PER-TRI choice is re-derived by the SAME rule (centroid
     cell first; a distinct vertex own-cell only where the centroid window's bleed clamp collapses the
     tri; the single documented per-vertex last-resort sliver). Stage 3b PROVES the reuse rather than
     asserting it: re-emitting all 2305 in GRASS through this field must reproduce FIXED3A's on-disk
     UVs bit-for-bit under float32 (2305/2305 required, else the build refuses).
  3. RE-EMIT (stage 4). For each synthesized tri whose centroid cell resolved to desert or dunes, all
     3 UVs are re-emitted through the KIT's OWN family path -- ``grassland.ground_uv(x, z, cell, quad,
     ori, family)`` = ``mains_uv`` + the byte-measured ``GROUNDS[family]`` translation (desert
     +0.65332/-0.09863, dunes +0.38964/-0.13477) -- against the SAME single window. Because the
     translation is a pure additive offset it preserves UV area exactly, so the degeneracy branch
     evaluated in grass space is the branch FIXED3A took. Grass-family tris are NOT touched.

UV-ONLY: positions / normals / tangents (hence the IDALL topograph) / indices are byte-identical to
FIXED3A everywhere; Sea4 and every non-Terrain part untouched. DELIBERATE DEVIATION from
``transplant.GroundRetile``, which also retags topo to the family topo: here topo stays grass-0 per the
work order, so walk/encounter semantics are unchanged and only the look moves.

HONESTY ON DUNES (stage 3c measures it, the report carries it): ``GROUNDS["dunes"]`` is a real
byte-measured mains TRANSLATION (the rect is confirmed against this tree's own carried stock dunes to
5dp), but stock dunes does NOT lay that rect on the locked per-cell 2x2 (quad,ori) lattice -- it slides
free fractional windows. The kit has no per-cell dunes placement model; ``grassland``'s own docstring
states the shipped policy ("the locked grass-form window is a common real form and the safe generative
choice, so minting reuses mains_uv"), and every shipped family emitter (world-island/world-mountain
``--ground``, ``GroundRetile``'s recover + degenerate-sand branches) emits exactly
``ground_uv(x, z, cell, quad, ori, family)``. That is the path used here, unmodified.

READ-ONLY vs the game install. Emits out/rung_f/FF9CustomMap-world-FIXED4 + uvf_fix4_report.json.
Render nothing -- the eye lane owns judgment.

    py -X utf8 uvf_fix4.py            # probe only (family field + reuse proof + dunes census)
    py -X utf8 uvf_fix4.py --build    # emit FIXED4 + self-check
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

import uvf_fix2 as F2                                           # noqa: E402
import uvf_fix3 as F3                                           # noqa: E402

CH_POS, CH_NRM, CH_UV, CH_TAN = X.CH_POS, X.CH_NRM, X.CH_UV, X.CH_TAN
CELL = 4.0
V2_SEED = F2.V2_SEED                                            # 0xF92

RUNG_F = HERE / "out" / "rung_f"
SPEC = RUNG_F / "FF9CustomMap-world"
FIXED3A = RUNG_F / "FF9CustomMap-world-FIXED3A"
FIXED4 = RUNG_F / "FF9CustomMap-world-FIXED4"
BUILD_JSON = RUNG_F / "rung_f_build.json"
FORENSICS = RUNG_F / "uvf_forensics.json"
REPORT = RUNG_F / "uvf_fix4_report.json"

FAMILIES = ("grass", "desert", "dunes")
#: the crater / root-wedge probe zone in the DEPLOY frame = donor cell (225,-196) + SHIFT_CELLS
#: (-192,-96) = (33,-292). (The work order quoted "(225-192, -196+96)" = (33,-100); that z is a
#: sign slip -- the shift is applied, not reflected. MEASURED CONFIRMATION, not a preference: the
#: deployed carried dunes ring occupies cells x[26,43] z[-301,-283] centred (33.6,-291.9), and every
#: non-grass fill cell this round resolves inside x[27,37] z[-296,-283]; cell (33,-100) holds no
#: island content at all.)
CRATER_CELL = (33, -292)
CRATER_R = 14
REGION_EPS = 0.006                                              # GroundRetile._EPS (uv membership slack)


def log(m):
    print(m, flush=True)


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def own_cell(vx, vz):
    return (math.floor(vx / CELL), math.floor(vz / CELL))


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def centroid_of(vw):
    return (sum(p[0] for p in vw) / 3.0, sum(p[2] for p in vw) / 3.0)


# ================================================================================================
#   STAGE 1 -- identify the 2305 synthesized tris (+ cross-check against the FIXED3A UV diff)
# ================================================================================================
def stage1(report, touched, apron_keys):
    spec_meshes = F3.load_blocks(SPEC, touched)
    a3_meshes = F3.load_blocks(FIXED3A, touched)

    # the classifier of record (uvf_fix2/3): the SPECIMEN's UV-degenerate tris
    defective, lawful_grass = F3.classify_defective(spec_meshes, apron_keys, touched)
    assert len(defective) == 2305, f"defective {len(defective)} != 2305"
    assert sum(1 for d in defective if d["is_apron"]) == 321

    # CROSS-CHECK: the FIXED3A-vs-SPEC UV diff must live entirely inside these tris' vertices
    def_vids = defaultdict(set)
    for d in defective:
        for j in d["vids"]:
            def_vids[d["block"]].add(j)
    diff_in = diff_out = 0
    for b in touched:
        s = M.read_ff9mesh(F2.terr_path(SPEC, *b))
        f = M.read_ff9mesh(F2.terr_path(FIXED3A, *b))
        for j in range(s["vcount"]):
            if s["uvs"][j] != f["uvs"][j]:
                if j in def_vids[b]:
                    diff_in += 1
                else:
                    diff_out += 1
    n_def_vids = sum(len(v) for v in def_vids.values())
    report["stage1_synthesized_set"] = dict(
        n_synthesized_tris=len(defective),
        n_apron=sum(1 for d in defective if d["is_apron"]),
        n_other=sum(1 for d in defective if not d["is_apron"]),
        uvdiff_fixed3a_vs_spec=dict(verts_changed_inside_2305=diff_in,
                                    verts_changed_outside_2305=diff_out,
                                    distinct_verts_of_2305=n_def_vids),
        crosscheck_ok=(diff_out == 0),
        note=("classifier of record = the SPECIMEN's UV-degenerate tris (uvf_fix2/3); the FIXED3A "
              "UV diff is a strict subset of their vertices -> the two identifications agree."))
    log(f"[s1] synthesized tris={len(defective)} (apron 321)  FIXED3A-vs-SPEC uv diff: "
        f"in={diff_in} out={diff_out} of {n_def_vids} distinct verts")
    assert diff_out == 0, "FIXED3A changed UVs outside the 2305 -- classifier disagreement"
    return spec_meshes, a3_meshes, defective, lawful_grass


# ================================================================================================
#   STAGE 2 -- THE FAMILY FIELD (nearest kept ground family per fill cell)
# ================================================================================================
def stage2(report, touched, a3_meshes, defective):
    synth_key = {(d["block"], d["tri"]) for d in defective}

    # --- sources: every KEPT Terrain tri with a GROUND topo votes into its centroid cell ---
    votes = defaultdict(Counter)              # cell -> family -> kept-tri count
    kept_topo = Counter()
    abstain_topo = Counter()
    for b in touched:
        bm = a3_meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[CH_POS]
        tans = bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            if (b, t) in synth_key:
                continue
            topo = X.decode_id(int(round(tans[tri[0]][0])))["topograph"]
            kept_topo[topo] += 1
            fam = G.TOPO_FAMILY.get(topo)
            if fam is None:
                abstain_topo[topo] += 1
                continue
            cx = sum(verts[j][0] + ox for j in tri) / 3.0
            cz = sum(verts[j][2] + oz for j in tri) / 3.0
            votes[own_cell(cx, cz)][fam] += 1

    # --- fill cells: the centroid cells of the synthesized tris ---
    fill_tri_cell = {}
    fill_cells = set()
    for d in defective:
        cx, cz = centroid_of(d["vw"])
        c = own_cell(cx, cz)
        fill_tri_cell[(d["block"], d["tri"])] = c
        fill_cells.add(c)

    src_list = [(c[0], c[1], votes[c]) for c in sorted(votes)]
    log(f"[s2] kept ground tris={sum(sum(v.values()) for v in votes.values())} in "
        f"{len(src_list)} source cells; fill cells={len(fill_cells)}")
    log(f"[s2] kept topo hist: {dict(kept_topo.most_common(14))}")

    # --- NEAREST source per fill cell (exact squared Euclidean; ring-majority tie-break) ---
    fam_of_cell = {}
    detail = {}
    d0_hist = Counter()
    near_fam = {}                                  # fill cell -> family -> nearest source distance
    ring_expanded = lexical = own_source = 0
    for fc in sorted(fill_cells):
        groups = defaultdict(Counter)
        best = {}
        for (sx, sy, cnt) in src_list:
            d2 = (sx - fc[0]) ** 2 + (sy - fc[1]) ** 2
            groups[d2] += cnt
            for f in cnt:
                if f not in best or d2 < best[f]:
                    best[f] = d2
        near_fam[fc] = {f: round(math.sqrt(d2), 3) for f, d2 in best.items()}
        ds = sorted(groups)
        if not ds:
            raise AssertionError("no kept ground content anywhere -- family field undefined")
        if ds[0] == 0:
            own_source += 1
        acc = Counter()
        chosen = None
        for k, d2 in enumerate(ds):
            acc += groups[d2]
            rank = acc.most_common()
            if len(rank) == 1 or rank[0][1] > rank[1][1]:
                chosen = rank[0][0]
                if k > 0:
                    ring_expanded += 1
                break
        if chosen is None:                        # every ring ties all the way out
            best = max(acc.values())
            chosen = sorted(f for f, n in acc.items() if n == best)[0]
            lexical += 1
        fam_of_cell[fc] = chosen
        d0 = math.sqrt(ds[0])
        d0_hist[round(d0, 3)] += 1
        detail[f"{fc[0]},{fc[1]}"] = dict(fam=chosen, d=round(d0, 3),
                                          ring0=dict(groups[ds[0]]), near=near_fam[fc])

    fam_cells = Counter(fam_of_cell.values())

    # --- BOUNDARY AUDIT: grass-resolved fill that has non-grass kept content close by. These are
    #     NOT under-clothed -- the law is nearest-wins and kept GRASS is strictly nearer (typically
    #     in the very same cell) -- but the count is the honest edge of the decision, so it ships.
    tri_per_cell = Counter(fill_tri_cell.values())
    audit = {}
    for r in (1.0, 1.5, 2.0, 3.0):
        cells = [c for c, f in fam_of_cell.items()
                 if f == "grass" and min(near_fam[c].get("dunes", 9e9),
                                         near_fam[c].get("desert", 9e9)) <= r]
        audit[f"within_{r}"] = dict(cells=len(cells), tris=sum(tri_per_cell[c] for c in cells),
                                    nearest_grass_is_same_cell=sum(1 for c in cells
                                                                   if near_fam[c].get("grass") == 0.0))

    # --- zone readouts: the crater/root-wedge zone vs the rest ---
    def in_crater(c):
        return math.hypot(c[0] - CRATER_CELL[0], c[1] - CRATER_CELL[1]) <= CRATER_R

    crater_cells = Counter(f for c, f in fam_of_cell.items() if in_crater(c))
    outer_cells = Counter(f for c, f in fam_of_cell.items() if not in_crater(c))
    crater_tris = Counter()
    outer_tris = Counter()
    for c, f in fam_of_cell.items():
        (crater_tris if in_crater(c) else outer_tris)[f] += tri_per_cell[c]
    nz = [c for c, f in fam_of_cell.items() if f != "grass"]
    bbox = (min(c[0] for c in nz), min(c[1] for c in nz),
            max(c[0] for c in nz), max(c[1] for c in nz)) if nz else None

    report["stage2_family_field"] = dict(
        n_source_cells=len(src_list),
        n_kept_ground_tris=sum(sum(v.values()) for v in votes.values()),
        source_cells_by_majority_family={f: sum(1 for (_x, _y, cnt) in src_list
                                                if cnt.most_common(1)[0][0] == f) for f in FAMILIES},
        kept_ground_tris_by_family={f: sum(cnt[f] for (_x, _y, cnt) in src_list) for f in FAMILIES},
        kept_topo_hist={str(k): v for k, v in sorted(kept_topo.items())},
        abstaining_nonground_topo_hist={str(k): v for k, v in sorted(abstain_topo.items())},
        n_fill_cells=len(fill_cells),
        fill_cells_by_family={f: fam_cells.get(f, 0) for f in FAMILIES},
        fill_cells_with_own_kept_ground=own_source,
        nearest_source_distance_hist={str(k): v for k, v in sorted(d0_hist.items())},
        ties_resolved_by_next_ring=ring_expanded,
        ties_resolved_lexically=lexical,
        crater_zone=dict(center_cell=list(CRATER_CELL), radius_cells=CRATER_R,
                         fill_cells_by_family={f: crater_cells.get(f, 0) for f in FAMILIES},
                         fill_tris_by_family={f: crater_tris.get(f, 0) for f in FAMILIES}),
        outside_crater_zone=dict(
            fill_cells_by_family={f: outer_cells.get(f, 0) for f in FAMILIES},
            fill_tris_by_family={f: outer_tris.get(f, 0) for f in FAMILIES}),
        non_grass_fill_cell_bbox=list(bbox) if bbox else None,
        boundary_audit_grass_resolved_near_nongrass=audit,
        boundary_audit_note=("the law is NEAREST-wins: these grass-resolved fill cells sit within "
                             "r cells of dunes/desert kept content but have kept GRASS strictly "
                             "nearer (usually in the same cell), so they are grass-adjacent fill and "
                             "stay byte-identical -- the crater-look guarantee, not under-clothing."),
        method=("kept Terrain tris of the DEPLOYED FIXED3A tree vote grassland.TOPO_FAMILY[topo] into "
                "their centroid 4u cell (non-ground topos abstain); each fill cell takes the family of "
                "its exact-nearest source cell, ties by kept-tri majority in the nearest ring, then by "
                "absorbing the next ring, then lexically."))
    log(f"[s2] fill cells by family={dict(fam_cells)}  own-source={own_source} "
        f"ties(ring)={ring_expanded} ties(lex)={lexical}")
    log(f"[s2] crater zone (<={CRATER_R} cells of {CRATER_CELL}): {dict(crater_cells)}   "
        f"outside: {dict(outer_cells)}")
    return fam_of_cell, fill_tri_cell, detail


# ================================================================================================
#   STAGE 3 -- rebuild the v2 (quad,ori) field EXACTLY as uvf_fix3 did (REUSE, never re-draw)
# ================================================================================================
def stage3_cellfield(report, defective, lawful_grass):
    target_cells = set()
    for d in defective:
        for (vx, _vy, vz) in d["vw"]:
            target_cells.add(own_cell(vx, vz))
    centroid_cells = {own_cell(*centroid_of(d["vw"])) for d in defective}
    resolve_cells = target_cells | centroid_cells

    # method (a): neighbour-decode ground truth -- VERBATIM uvf_fix3 semantics (first cell candidate
    # that decodes wins; a cell whose candidates all fail stays undecoded -> "dropped")
    by_cell = defaultdict(list)
    for (cell, vw, uv3) in lawful_grass:
        by_cell[cell].append((vw, uv3))
    decoded_a = {}
    for cell in sorted(by_cell):
        got = None
        for (vw, uv3) in by_cell[cell]:
            qo = F2.decode_quad_ori(cell, vw, uv3)
            if qo is not None:
                got = qo
                break
        if got is not None:
            decoded_a[cell] = got

    dropped = sorted(c for c in resolve_cells if c not in decoded_a)
    pre_quad = dict(decoded_a)
    pre_ori = {c: o for c, (q, o) in decoded_a.items()}
    v2_quad, v2_ori = F2.assign_mains_seeded(dropped, pre_quad, pre_ori, seed=V2_SEED)
    decoded = {c: (q, o, "a") for c, (q, o) in decoded_a.items()}
    for c in dropped:
        decoded[c] = (v2_quad[c], v2_ori[c], "v2")

    report["stage3_cell_field"] = dict(
        method_a_cells=len(decoded_a), dropped_cells=len(dropped),
        resolve_cells=len(resolve_cells), seed=V2_SEED,
        note=("construction IDENTICAL to uvf_fix3 (method-a decode of the specimen's lawful grass + "
              "assign_mains_seeded on the dropped cells) -- the field is REUSED, not re-drawn; "
              "stage 3b proves it bit-for-bit against FIXED3A's own bytes."))
    log(f"[s3] cell field: method-a={len(decoded_a)} dropped={len(dropped)} "
        f"resolve={len(resolve_cells)}")
    return decoded


def pick_window(d, decoded):
    """FIXED3A's own ONE-WINDOW choice for a tri: the CENTROID cell first, then each distinct vertex
    own-cell, taking the first whose GRASS-space UV triangle is non-degenerate; last resort = the
    per-vertex path (1 tri in FIXED3A). Returns (kind, cell_or_None)."""
    ccell = own_cell(*centroid_of(d["vw"]))
    cand = [ccell] + [own_cell(vx, vz) for (vx, _vy, vz) in d["vw"]]
    seen = set()
    for k, cell in enumerate(cand):
        if cell in seen:
            continue
        seen.add(cell)
        quad, ori, _m = decoded[cell]
        uv = [list(G.ground_uv(vx, vz, cell, quad, ori, "grass")) for (vx, _vy, vz) in d["vw"]]
        if not F2.uv_tri_degen(uv):
            return ("centroid" if k == 0 else "owncell-fallback"), cell
    return "pervertex-lastresort", None


def emit_tri(d, decoded, wkind, wcell, fam):
    """The kit's family mains path against the tri's ONE window (or the documented per-vertex
    last resort). Pure ``grassland.ground_uv`` -- no invented offsets."""
    if wcell is not None:
        q, o, _m = decoded[wcell]
        return [list(G.ground_uv(vx, vz, wcell, q, o, fam)) for (vx, _vy, vz) in d["vw"]]
    out = []
    for (vx, _vy, vz) in d["vw"]:
        c = own_cell(vx, vz)
        q, o, _m = decoded[c]
        out.append(list(G.ground_uv(vx, vz, c, q, o, fam)))
    return out


# ================================================================================================
#   STAGE 3b -- PROVE the reuse: grass re-emission must reproduce FIXED3A bit-for-bit
# ================================================================================================
def stage3b_prove_reuse(report, touched, defective, decoded):
    a3 = {b: M.read_ff9mesh(F2.terr_path(FIXED3A, *b)) for b in touched}
    exact = mismatch = 0
    worst = 0.0
    kinds = Counter()
    windows = {}
    for d in defective:
        kind, wcell = pick_window(d, decoded)
        kinds[kind] += 1
        windows[(d["block"], d["tri"])] = (kind, wcell)
        uv = emit_tri(d, decoded, kind, wcell, "grass")
        disk = [a3[d["block"]]["uvs"][j] for j in d["vids"]]
        ok = True
        for k in range(3):
            for a in range(2):
                if f32(uv[k][a]) != f32(disk[k][a]):
                    ok = False
                worst = max(worst, abs(f32(uv[k][a]) - f32(disk[k][a])))
        exact += ok
        mismatch += (not ok)
    report["stage3b_reuse_proof"] = dict(
        n_tris=len(defective), grass_reemission_bit_exact_vs_fixed3a=exact, mismatched=mismatch,
        max_abs_float32_delta=worst, window_source=dict(kinds),
        verdict=("PROVEN: the rebuilt (quad,ori) field + one-window choice reproduce FIXED3A's UVs "
                 "exactly, so the family re-emission differs from FIXED3A by the translation ALONE"
                 if mismatch == 0 else "FAILED -- field/window reconstruction diverges from FIXED3A"))
    log(f"[s3b] grass re-emission vs FIXED3A bytes: exact={exact}/{len(defective)} "
        f"mismatch={mismatch} maxdelta={worst}  window_source={dict(kinds)}")
    assert mismatch == 0, "field/window reuse NOT bit-true vs FIXED3A -- refusing to build"
    return windows


# ================================================================================================
#   STAGE 3c -- the DUNES/DESERT language census (honesty: what the kit's dunes path really is)
# ================================================================================================
def stage3c_family_language(report, touched, a3_meshes, defective):
    synth_key = {(d["block"], d["tri"]) for d in defective}
    per = defaultdict(Counter)
    bbox = defaultdict(lambda: [9.0, 9.0, -9.0, -9.0])
    for b in touched:
        bm = a3_meshes[b]
        ox, oz = X.block_world_origin(*b)
        P, U, T = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_UV], bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            if (b, t) in synth_key:
                continue
            topo = X.decode_id(int(round(T[tri[0]][0])))["topograph"]
            fam = G.TOPO_FAMILY.get(topo)
            if fam is None or fam == "grass":
                continue
            uv = [(U[j][0], U[j][1]) for j in tri]
            vw = [(P[j][0] + ox, P[j][1], P[j][2] + oz) for j in tri]
            lo_u, lo_v, hi_u, hi_v = G.ground_main_region(fam)
            inreg = all(lo_u - REGION_EPS <= u <= hi_u + REGION_EPS
                        and lo_v - REGION_EPS <= v <= hi_v + REGION_EPS for (u, v) in uv)
            key = f"{fam}/topo{topo}"
            per[key]["tris"] += 1
            bb = bbox[key + ("/mains" if inreg else "/off-mains")]
            for (u, v) in uv:
                bb[0] = min(bb[0], u); bb[1] = min(bb[1], v)
                bb[2] = max(bb[2], u); bb[3] = max(bb[3], v)
            if not inreg:
                per[key]["off-mains(decal/strip)"] += 1
                continue
            per[key]["in-mains-rect"] += 1
            du, dv = G.GROUNDS[fam]["mains_du"], G.GROUNDS[fam]["mains_dv"]
            cell = own_cell(*centroid_of(vw))
            qo = F2.decode_quad_ori(cell, vw, [(u - du, v - dv) for (u, v) in uv])
            per[key]["lattice-decodable" if qo else "free-fractional-window"] += 1
    report["stage3c_family_language"] = dict(
        carried_stock_tris={k: dict(v) for k, v in sorted(per.items())},
        uv_bbox={k: [round(x, 5) for x in v] for k, v in sorted(bbox.items())},
        kit_mains_regions={f: [round(x, 5) for x in G.ground_main_region(f)] for f in FAMILIES},
        kit_translations={f: [G.GROUNDS[f]["mains_du"], G.GROUNDS[f]["mains_dv"]] for f in FAMILIES},
        finding=("the family mains RECT is byte-confirmed (this tree's carried stock dunes/desert tris "
                 "land inside grassland.ground_main_region to 5dp), but stock does NOT lay it on the "
                 "locked per-cell 2x2 (quad,ori) lattice -- most in-rect stock tris are free fractional "
                 "windows. The kit ships NO per-cell dunes placement model; grassland's documented "
                 "policy is that the locked grass-form window is a common real form and the safe "
                 "generative choice, and every shipped emitter (world-island/world-mountain --ground, "
                 "GroundRetile recover + degenerate-sand) calls ground_uv(x,z,cell,quad,ori,family). "
                 "That path is used here unmodified."))
    log(f"[s3c] carried stock non-grass ground: "
        f"{ {k: dict(v) for k, v in sorted(per.items())} }")
    return per


# ================================================================================================
#   STAGE 4 -- BUILD FIXED4
# ================================================================================================
def stage4_build(report, touched, defective, fam_of_cell, fill_tri_cell, decoded, windows):
    if FIXED4.exists():
        shutil.rmtree(FIXED4)
    shutil.copytree(FIXED3A, FIXED4)
    n_copied = sum(1 for p in FIXED4.rglob("*") if p.is_file())
    assert n_copied == 180, f"copy mismatch {n_copied}"
    log(f"[s4] copied {n_copied} files -> {FIXED4}")

    meshes = F3.load_blocks(FIXED4, touched)
    uv_changed_vids = defaultdict(set)
    per_family = Counter()
    window_source = Counter()
    prov = Counter()
    max_spread = 0.0
    spread_over_window = 0
    dirty = set()
    for d in defective:
        cell = fill_tri_cell[(d["block"], d["tri"])]
        fam = fam_of_cell[cell]
        per_family[fam] += 1
        prov[(fam, "apron" if d["is_apron"] else "fill/stitch")] += 1
        if fam == "grass":
            continue                                    # untouched -> byte-identical to FIXED3A
        kind, wcell = windows[(d["block"], d["tri"])]
        window_source[f"{fam}:{kind}"] += 1
        new_uv = emit_tri(d, decoded, kind, wcell, fam)
        sp = F3.max_pairwise_uv(new_uv)
        max_spread = max(max_spread, sp)
        if sp > F3.QUAD_DIAG + 1e-9:
            spread_over_window += 1
        uvs = meshes[d["block"]].chan_arrays[CH_UV]
        for j, uv in zip(d["vids"], new_uv):
            uvs[j] = uv
            uv_changed_vids[d["block"]].add(j)
        dirty.add(d["block"])

    written = {}
    for b in sorted(dirty):
        p = F2.terr_path(FIXED4, *b)
        M.write_ff9mesh(meshes[b], p)
        written[str(p.relative_to(FIXED4))] = sha256_file(p)

    report["stage4_apply"] = dict(
        tris_by_family={f: per_family.get(f, 0) for f in FAMILIES},
        tris_rewritten=per_family.get("desert", 0) + per_family.get("dunes", 0),
        tris_left_grass_byte_identical=per_family.get("grass", 0),
        tris_by_family_and_provenance={f"{f}:{p}": n for (f, p), n in sorted(prov.items())},
        uv_changed_verts=sum(len(s) for s in uv_changed_vids.values()),
        window_source=dict(window_source),
        blocks_written=[list(b) for b in sorted(dirty)],
        tris_spread_over_one_window=spread_over_window,
        max_uv_spread=round(max_spread, 6),
        one_window_scale=round(F3.QUAD_DIAG, 6),
        emission_path="grassland.ground_uv(x, z, cell, quad, ori, family)  [the kit's own family path]",
        family_translations={f: [G.GROUNDS[f]["mains_du"], G.GROUNDS[f]["mains_dv"]] for f in FAMILIES})
    log(f"[s4] tris by family={dict(per_family)}  rewritten="
        f"{per_family.get('desert', 0) + per_family.get('dunes', 0)}  blocks written={len(dirty)}")
    log(f"[s4] window_source={dict(window_source)}  max_spread={round(max_spread, 5)}")
    return dict(uv_changed_vids=uv_changed_vids, written=written, dirty=dirty, per_family=per_family)


# ================================================================================================
#   STAGE 5 -- SELF-CHECK
# ================================================================================================
def stage5_verify(report, touched, defective, fam_of_cell, fill_tri_cell, decoded, windows, state):
    v = {}
    uv_changed_vids = state["uv_changed_vids"]
    meshes = F3.load_blocks(FIXED4, touched)

    # (1) zero degenerate UVs anywhere in the tree's Terrain
    post_def = 0
    for b in touched:
        uvs = meshes[b].chan_arrays[CH_UV]
        for tri in meshes[b].tris:
            if F2.uv_degenerate([(uvs[j][0], uvs[j][1]) for j in tri]):
                post_def += 1
    v["degenerate_uv_tris_all_terrain"] = post_def

    # (2) every rewritten UV inside ITS family's mains region (and untouched grass still in grass)
    regions = {f: G.ground_main_region(f) for f in FAMILIES}
    tol = 1e-6
    out_of_region = Counter()
    zero_area = Counter()
    for d in defective:
        fam = fam_of_cell[fill_tri_cell[(d["block"], d["tri"])]]
        lo_u, lo_v, hi_u, hi_v = regions[fam]
        uvs = meshes[d["block"]].chan_arrays[CH_UV]
        uv3 = [(uvs[j][0], uvs[j][1]) for j in d["vids"]]
        for (u, vv) in uv3:
            if not (lo_u - tol <= u <= hi_u + tol and lo_v - tol <= vv <= hi_v + tol):
                out_of_region[fam] += 1
        if F2.uv_tri_degen(uv3):
            zero_area[fam] += 1
    v["uv_out_of_own_family_region"] = dict(out_of_region)
    v["zero_uv_area_tris_by_family"] = dict(zero_area)
    v["family_mains_regions"] = {f: [round(x, 6) for x in regions[f]] for f in FAMILIES}

    # (3) RIGIDITY vs FIXED3A: pos/nrm/tan/idx identical everywhere; uv only at rewritten verts
    rig = dict(pos_bad=0, nrm_bad=0, tan_bad=0, idx_bad=0, uv_unexpected=0, uv_expected=0)
    for b in touched:
        a = M.read_ff9mesh(F2.terr_path(FIXED3A, *b))
        f = M.read_ff9mesh(F2.terr_path(FIXED4, *b))
        rig["pos_bad"] += (a["verts"] != f["verts"])
        rig["nrm_bad"] += (a["normals"] != f["normals"])
        rig["tan_bad"] += (a["tangents"] != f["tangents"])
        rig["idx_bad"] += (a["indices"] != f["indices"])
        chg = uv_changed_vids.get(b, set())
        for j in range(a["vcount"]):
            if a["uvs"][j] != f["uvs"][j]:
                rig["uv_expected" if j in chg else "uv_unexpected"] += 1
    v["byte_rigidity_vs_fixed3a"] = rig

    # (3b) whole-tree diff: only the dirty blocks' Terrain files may differ
    changed = []
    for p in sorted(FIXED3A.rglob("*")):
        if p.is_file() and sha256_file(p) != sha256_file(FIXED4 / str(p.relative_to(FIXED3A))):
            changed.append(str(p.relative_to(FIXED3A)))
    v["tree_diff_vs_fixed3a"] = dict(n_files_changed=len(changed),
                                     n_terrain=sum(1 for r in changed if "Terrain" in r),
                                     n_non_terrain=sum(1 for r in changed if "Terrain" not in r),
                                     files=changed)
    v["sea4_untouched"] = all("Sea4" not in r for r in changed)
    v["non_terrain_untouched"] = all("Terrain" in r for r in changed)

    # (4) ONE-WINDOW COHERENCE, family-aware -- re-derived FROM DISK: does ONE (cell,quad,ori) in the
    #     tri's own family space reproduce all 3 on-disk UVs bit-for-bit (float32)?
    single = multi = 0
    per_fam = defaultdict(Counter)
    exc = []
    for d in defective:
        fam = fam_of_cell[fill_tri_cell[(d["block"], d["tri"])]]
        uvs = meshes[d["block"]].chan_arrays[CH_UV]
        uv3 = [(uvs[j][0], uvs[j][1]) for j in d["vids"]]
        cand = [own_cell(*centroid_of(d["vw"]))] + [own_cell(vx, vz) for (vx, _vy, vz) in d["vw"]]
        ok = False
        for cell in cand:
            if cell not in decoded:
                continue
            q, o, _m = decoded[cell]
            pred = [G.ground_uv(vx, vz, cell, q, o, fam) for (vx, _vy, vz) in d["vw"]]
            if all(f32(pred[k][a]) == f32(uv3[k][a]) for k in range(3) for a in range(2)):
                ok = True
                break
        single += ok
        multi += (not ok)
        per_fam[fam]["single" if ok else "multi"] += 1
        exc.append(F3.max_pairwise_uv(uv3))
    exc.sort()
    n = len(exc)
    n_lastresort = sum(1 for k in windows.values() if k[1] is None)
    v["window_coherence"] = dict(
        n_tris=n, single_window_reconstructed=single, multi_window=multi,
        pct_single=round(100.0 * single / n, 3),
        per_family={f: dict(per_fam[f]) for f in FAMILIES},
        documented_pervertex_lastresort=n_lastresort,
        excursion_p50=round(exc[n // 2], 5), excursion_p90=round(exc[int(0.9 * (n - 1))], 5),
        excursion_max=round(exc[-1], 5), one_window_scale=round(F3.QUAD_DIAG, 5),
        fixed3a_reference=dict(single=2304, multi=1, exc_p50=0.06078, exc_p90=0.06962,
                               exc_max=0.07784),
        note=("the ONLY non-one-window tri is the same per-vertex last-resort sliver FIXED3A "
              "documents; every other tri reconstructs from ONE (cell,quad,ori) in its family space."))

    # (5) THE CRATER: carried content + grass-family fill byte-identical to FIXED3A (proved from disk)
    synth_vids = defaultdict(set)
    for d in defective:
        for j in d["vids"]:
            synth_vids[d["block"]].add(j)
    grass_tris = [d for d in defective
                  if fam_of_cell[fill_tri_cell[(d["block"], d["tri"])]] == "grass"]
    grass_bad = kept_bad = 0
    a3_cache = {b: M.read_ff9mesh(F2.terr_path(FIXED3A, *b)) for b in touched}
    f4_cache = {b: M.read_ff9mesh(F2.terr_path(FIXED4, *b)) for b in touched}
    for d in grass_tris:
        a, f = a3_cache[d["block"]], f4_cache[d["block"]]
        for j in d["vids"]:
            grass_bad += (a["uvs"][j] != f["uvs"][j])
    for b in touched:
        a, f = a3_cache[b], f4_cache[b]
        for j in range(a["vcount"]):
            if j not in synth_vids[b] and a["uvs"][j] != f["uvs"][j]:
                kept_bad += 1
    # the crater bowl itself: kept (carried) tris whose centroid cell is inside the crater radius
    bowl_tris = 0
    for b in touched:
        bm = meshes[b]
        ox, oz = X.block_world_origin(*b)
        P = bm.chan_arrays[CH_POS]
        synth = {d["tri"] for d in defective if d["block"] == b}
        for t, tri in enumerate(bm.tris):
            if t in synth:
                continue
            c = own_cell(sum(P[j][0] + ox for j in tri) / 3.0, sum(P[j][2] + oz for j in tri) / 3.0)
            if math.hypot(c[0] - CRATER_CELL[0], c[1] - CRATER_CELL[1]) <= CRATER_R:
                bowl_tris += 1
    v["crater_preserved"] = dict(
        grass_family_fill_tris=len(grass_tris), grass_family_fill_uv_diff_verts=grass_bad,
        kept_content_uv_diff_verts=kept_bad,
        kept_carried_tris_inside_crater_radius=bowl_tris,
        note=("the crater bowl is CARRIED content -- outside the 2305 rewritable set entirely -- and "
              "grass-family fill is skipped by construction; both verified byte-identical from disk."))

    # (5b) TRANSLATION-ONLY: every rewritten vertex's UV differs from FIXED3A's by exactly the
    #      family's GROUNDS translation (float32 rounding only). Together with stage 3b (grass
    #      re-emission == FIXED3A bit-for-bit) this pins the change to the translation alone.
    worst_du = 0.0
    n_checked = 0
    for d in defective:
        fam = fam_of_cell[fill_tri_cell[(d["block"], d["tri"])]]
        if fam == "grass":
            continue
        du, dv = G.GROUNDS[fam]["mains_du"], G.GROUNDS[fam]["mains_dv"]
        a, f = a3_cache[d["block"]], f4_cache[d["block"]]
        for j in d["vids"]:
            worst_du = max(worst_du, abs((f["uvs"][j][0] - a["uvs"][j][0]) - du),
                           abs((f["uvs"][j][1] - a["uvs"][j][1]) - dv))
            n_checked += 1
    v["translation_only"] = dict(rewritten_verts_checked=n_checked,
                                 max_abs_deviation_from_family_translation=worst_du,
                                 note=("each rewritten vertex moved by exactly GROUNDS[family] "
                                       "(mains_du, mains_dv); residual is float32 rounding only."))

    # (6) flat-mesh invariant on every written file
    flat_bad = []
    for rel in state["written"]:
        dd = M.read_ff9mesh(FIXED4 / rel)
        if not (dd["vcount"] == len(dd["indices"]) == len(dd["verts"]) and len(dd["indices"]) % 3 == 0):
            flat_bad.append(rel)
    v["flat_mesh_bad"] = flat_bad

    report["stage5_verify"] = v
    ok = (post_def == 0 and not out_of_region and not zero_area and not flat_bad
          and rig["pos_bad"] == 0 and rig["nrm_bad"] == 0 and rig["tan_bad"] == 0
          and rig["idx_bad"] == 0 and rig["uv_unexpected"] == 0
          and v["sea4_untouched"] and v["non_terrain_untouched"]
          and grass_bad == 0 and kept_bad == 0
          and multi <= n_lastresort)
    report["ok"] = ok
    log(f"[s5] degenerate={post_def} out_of_region={dict(out_of_region)} zero_area={dict(zero_area)}")
    log(f"[s5] rigidity vs FIXED3A: {rig}")
    log(f"[s5] tree diff: {v['tree_diff_vs_fixed3a']['n_files_changed']} files "
        f"({v['tree_diff_vs_fixed3a']['n_terrain']} Terrain / "
        f"{v['tree_diff_vs_fixed3a']['n_non_terrain']} other)")
    log(f"[s5] window coherence: single={single}/{n} multi={multi} "
        f"per_family={ {f: dict(per_fam[f]) for f in FAMILIES} }")
    log(f"[s5] crater: grass-fill uv diff={grass_bad}  kept-content uv diff={kept_bad}  "
        f"carried tris in crater radius={bowl_tris}")
    log(f"[s5] OK={ok}")
    return ok


def main():
    build_flag = "--build" in sys.argv
    report = {"meta": dict(
        script="uvf_fix4.py", read_only_vs_game=True, v2_seed=V2_SEED,
        spec_tree=str(SPEC), base_tree=str(FIXED3A), out_tree=str(FIXED4),
        build_requested=build_flag,
        law=("an absent feature's footprint wears the SURROUNDING family (the orphan-decal law's "
             "hole-fill analogue)"),
        uv_only=("positions/normals/tangents(IDALL topo)/indices byte-identical to FIXED3A; "
                 "deliberate deviation from GroundRetile, which also retags topo to the family "
                 "topo -- here topo stays grass-0 per the work order"))}

    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    assert len(touched) == 20

    forensics = json.loads(FORENSICS.read_text(encoding="utf-8"))
    apron_keys = set()
    for rec in forensics["records"]:
        if rec.get("uv_verdict") == "degenerate-zero-area" and rec["provenance"] == "apron":
            cx, _cy, cz = rec["centroid"]
            apron_keys.add((tuple(rec["block"]), round(cx, 3), round(cz, 3)))

    _spec, a3_meshes, defective, lawful_grass = stage1(report, touched, apron_keys)
    fam_of_cell, fill_tri_cell, cell_detail = stage2(report, touched, a3_meshes, defective)
    decoded = stage3_cellfield(report, defective, lawful_grass)
    windows = stage3b_prove_reuse(report, touched, defective, decoded)
    stage3c_family_language(report, touched, a3_meshes, defective)

    prev = Counter(fam_of_cell[fill_tri_cell[(d["block"], d["tri"])]] for d in defective)
    report["preview_tris_by_family"] = {f: prev.get(f, 0) for f in FAMILIES}
    log(f"[main] PREVIEW tris by family: {dict(prev)}")

    if build_flag:
        state = stage4_build(report, touched, defective, fam_of_cell, fill_tri_cell, decoded, windows)
        stage5_verify(report, touched, defective, fam_of_cell, fill_tri_cell, decoded, windows, state)
    else:
        report["ok"] = None
        log("[main] probe-only (pass --build to emit FIXED4).")

    report["fill_cell_detail"] = cell_detail
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"\n{'=' * 80}\nwrote {REPORT}  ok={report.get('ok')}")
    return report


if __name__ == "__main__":
    main()
