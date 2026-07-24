"""RUNG F BUILD -- THE MIXED-BIOME BUILD (2026-07-24), the gate + stage + render half.

Runs the FULL gate stack over ``rung_f_layout.compose``'s in-memory build and stages the would-be-
deployed file set under ``out/rung_f/FF9CustomMap-world/`` (NEVER the game install). Records everything
in ``out/rung_f/rung_f_build.json``. NO --apply / deploy / mirror / commit from this phase.

THE GATE STACK (task-specified):
  1. PLUMBING
     - STAGE 0  site re-verify (open-ocean + margin, island._real_block_parts, at ACTION time)
     - STAGE 1  verify_landmass on the GRASS FRAME (0 cracks/holes/open-edges/down-facing on the frame
                -- verify_landmass is grass-UV-centric, so the composite's carried desert/dunes UVs are
                checked by STAGE 4's own composite crack/hole/open-edge/down-facing audit instead)
     - STAGE 2  BYTE-RIGIDITY of the carried window (donor bytes preserved exactly, translation only --
                ASSERTED per whole carried tri: pos == donor + T, uv/nrm verbatim, tangent[1:] verbatim,
                IDALL topo+flags kept event/area zeroed; clipped border pieces reported)
     - STAGE 3  EVENT/AREA STRIP verify (every carried IDALL decodes event==0 && area==0)
     - STAGE 4  composite plumbing: FLAT-MESH invariant, grid bounds, weld_audit (0 near-miss),
                frame bounds, cracks (position-welded height mismatch), down-facing, walk-filter, and
                the closed-surface once-edge audit (open edges above the y=0 skirt)
     - STAGE 5  ORPHAN-DECAL gate (deployed-else-stock ring), WANG-CARRY gate, MOD-OVERWRITE gate,
                effective-prefab-arm, SEA-LAYER law (Sea4 Y==0)
  2. THE CONTRACT SCREEN -- contract_mass_gates.py v4 over the staged tree (load_candidate on the staged
     mod dir), ALL THREE gates PASS + the R2/R3 calibration comparison vs stock.
  3. RENDERS -- planview + oblique of the junction area and the whole landmass (the dunes/massif eye
     convention: iterate offline, only finals playtest).

Run:  py studies/overworld-topography/rung_f_build.py   (cwd = studies/overworld-topography)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                        # noqa: E402
from ff9mapkit.world import island as ISL                   # noqa: E402
from ff9mapkit.world import mesh as M                        # noqa: E402
from ff9mapkit.world import transplant as TR                # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import orphangate as OG                # noqa: E402

import rung_f_layout as RFL                                  # noqa: E402
import contract_mass_gates as CMG                            # noqa: E402

BLOCK = RFL.BLOCK
CELL = RFL.CELL
MOD = RFL.MOD
LAND_HEIGHT = RFL.LAND_HEIGHT
OUT_DIR = HERE / "out" / "rung_f"
OUT_ROOT = OUT_DIR / MOD
OUT_JSON = OUT_DIR / "rung_f_build.json"
RENDER_DIR = OUT_DIR / "renders"

GATES: list = []


def gate(name, ok, detail=""):
    GATES.append(dict(name=name, ok=bool(ok), detail=str(detail)[:2000]))
    print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {str(detail)[:400]}" if detail else ""))
    return bool(ok)


def log(m):
    print(m, flush=True)


# ============================================================================================
# STAGE 0 -- site re-verify (ACTION TIME)
# ============================================================================================
def stage0_site(game_root):
    log("\n" + "#" * 96); log("STAGE 0 -- site re-verify (open-ocean + margin, at action time)"); log("#" * 96)
    site = sorted(RFL.SITE_BLOCKS)
    occ = {}
    for blk in site:
        p = ISL._real_block_parts(blk, disc=1, lod="0_1", game=game_root)
        if p:
            occ[f"{blk[0]},{blk[1]}"] = p
    ok_ocean = not occ
    gate("STAGE0 OPEN-OCEAN TARGET: every site block (0-3,16-19) is true stock open ocean", ok_ocean,
         f"occupied={occ}" if occ else "all 16 clear")
    # margin: the Moore ring around the site must be checked; (4,15) is a known diagonal land touch,
    # mitigated by the rounded coast (radius 118 never reaches it). Report the ring occupancy.
    ring = CMG.moore_ring(site, 1)
    ring_land = {}
    for blk in ring:
        if blk in RFL.SITE_BLOCKS:
            continue
        p = ISL._real_block_parts(blk, disc=1, lod="0_1", game=game_root)
        if p:
            ring_land[f"{blk[0]},{blk[1]}"] = sorted(p.keys())
    log(f"  margin ring land (context, not a gate): {ring_land}")
    return dict(ok_ocean=ok_ocean, occupied=occ, margin_ring_land=ring_land)


# ============================================================================================
# STAGE 1 -- verify_landmass on the grass frame
# ============================================================================================
def stage1_frame_verify(built, game_root):
    log("\n" + "#" * 96); log("STAGE 1 -- verify_landmass on the GRASS FRAME (grass-UV baseline)"); log("#" * 96)
    plane = ISL._sea_plane(disc=1, game=game_root)
    v = ISL.verify_landmass(built, sea_plane=plane, land_height=LAND_HEIGHT)
    frame_blocks_ok = RFL.SITE_BLOCKS.issuperset(set(built["blocks"]))
    gate("STAGE1 grass-frame stays within the site rect (blocks subset of 0-3,16-19)", frame_blocks_ok,
         f"frame blocks={sorted(built['blocks'])}")
    keys = ("cracks", "down_facing", "walk_filter_fails", "grass_over_8u", "uv_out_of_region",
            "holes", "open_edges", "missing_faces")
    clean = all(v.get(k, 0) == 0 for k in keys)
    detail = {k: v.get(k) for k in keys}
    gate("STAGE1 verify_landmass on the grass frame: 0 cracks/holes/open-edges/down-facing/steep/big/oob",
         clean, f"{detail}")
    gate("ADVISORY STAGE1 grass-frame coastline SHAPE (coast-realism; NOT in the task's verify_landmass "
         "criteria of cracks/holes/open-edges/down-facing -- a smooth minted coast reads med_turn low; "
         "cosmetic, closed by a higher-undulation / multi-lobe coast in a polish round)",
         bool(v["shape"]["ok"]), f"{v['shape']}")
    place = v.get("placement", {})
    miss = sum(pr.get("miss", 0) for pr in place.values()) if isinstance(place, dict) else None
    return dict(verify={k: v.get(k) for k in keys}, shape=v["shape"], frame_blocks_ok=frame_blocks_ok,
                frame_verify_clean=clean, placement_miss_total=miss)


# ============================================================================================
# STAGE 2 -- byte-rigidity of the carried window
# ============================================================================================
def stage2_rigidity(comp):
    log("\n" + "#" * 96); log("STAGE 2 -- BYTE-RIGIDITY of the carried window (translation only, ASSERTED)"); log("#" * 96)
    donor = comp["donor"]
    Twx, Twz = RFL.SHIFT_WORLD
    Tx, Tz = RFL.SHIFT_CELLS
    DY = comp["diag"]["DY"]
    # baseline: index donor tris by (cell, canonical vertex-position tuple) so we can match a carried
    # tri to its donor original. A carried WHOLE tri (unclipped) must equal donor + T exactly on pos,
    # verbatim uv/nrm/tangent[1:], and IDALL topo+flags kept / event+area zeroed.
    donor_by_key = {}
    for (c, tri) in donor["raw"]:
        key = tuple(sorted((round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4)) for v in tri))
        donor_by_key[key] = tri
    # FIX-H pre-quantizes carried verts within FIXH_TAU of a host block border ONTO it (the weld's
    # phase-shift fix) -- those tris are NOT asserted byte-rigid (that IS the tiny border-seam
    # deformation). Rigidity is asserted on carried tris clear of every block border, which carry the
    # whole ecotone.
    def near_border(tri):
        for v in tri:
            for w, ax in ((v[0][0], 0), (v[0][2], 2)):
                d = abs(w - round(w / BLOCK) * BLOCK)
                if d < RFL.FIXH_TAU + 0.1:
                    return True
        return False

    n_whole = n_clip = n_apron = 0
    pos_bad = uv_bad = nrm_bad = tan_bad = topo_bad = 0
    max_pos_err = 0.0
    for blk, soup in comp["out_soup"].items():
        # only carried tris are in placed_R; kept grass is not. classify by whether tri's cell is placed.
        for tri in soup:
            cx = sum(v[0][0] for v in tri) / 3.0
            cz = sum(v[0][2] for v in tri) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            if cell not in comp["placed_R"]:
                continue                                   # a kept-grass tri (frame), not carried
            if near_border(tri):
                n_apron += 1                               # a FIX-H border-seam tri (tiny weld deformation)
                continue
            # reconstruct the donor-frame key (undo T) and look for a WHOLE match
            key = tuple(sorted((round(v[0][0] - Twx, 4), round(v[0][1] - DY, 4), round(v[0][2] - Twz, 4))
                               for v in tri))
            dtri = donor_by_key.get(key)
            if dtri is None:
                n_clip += 1                                # a border-clipped piece (lerped verts)
                continue
            n_whole += 1
            # match verts by position within the donor tri (order-independent)
            dverts = {(round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4)): v for v in dtri}
            for (p, n, u, t) in tri:
                dk = (round(p[0] - Twx, 4), round(p[1] - DY, 4), round(p[2] - Twz, 4))
                dv = dverts.get(dk)
                if dv is None:
                    pos_bad += 1
                    continue
                perr = max(abs(p[0] - Twx - dv[0][0]), abs(p[1] - DY - dv[0][1]), abs(p[2] - Twz - dv[0][2]))
                max_pos_err = max(max_pos_err, perr)
                if u[0] != dv[2][0] or u[1] != dv[2][1]:
                    uv_bad += 1
                if tuple(n) != tuple(dv[1]):
                    nrm_bad += 1
                if tuple(t[1:]) != tuple(dv[3][1:]):
                    tan_bad += 1
                d_dec = X.decode_id(int(round(dv[3][0])))
                c_dec = X.decode_id(int(round(t[0])))
                if not (c_dec["topograph"] == d_dec["topograph"] and c_dec["flags"] == d_dec["flags"]):
                    topo_bad += 1
    rigid_ok = (pos_bad == 0 and uv_bad == 0 and nrm_bad == 0 and tan_bad == 0 and topo_bad == 0
                and max_pos_err < 1e-3)
    gate("STAGE2 BYTE-RIGIDITY: every pure-INTERIOR carried tri = donor + T exactly (pos), UV/normal/"
         "tangent[1:] VERBATIM, IDALL topo+flags KEPT (seam-collar apron ring excluded = the weld "
         "deformation)", rigid_ok,
         f"interior_whole={n_whole} clipped_pieces={n_clip} apron_ring={n_apron} pos_bad={pos_bad} "
         f"uv_bad={uv_bad} nrm_bad={nrm_bad} tan_bad={tan_bad} topo_flags_bad={topo_bad} "
         f"max_pos_err={max_pos_err:.2e}")
    return dict(n_interior_whole=n_whole, n_clipped_pieces=n_clip, n_apron_ring=n_apron, pos_bad=pos_bad,
                uv_bad=uv_bad, nrm_bad=nrm_bad, tan_bad=tan_bad, topo_flags_bad=topo_bad,
                max_pos_err=max_pos_err, rigid_ok=rigid_ok)


# ============================================================================================
# STAGE 3 -- event/area strip verify
# ============================================================================================
def stage3_event_strip(comp):
    log("\n" + "#" * 96); log("STAGE 3 -- EVENT/AREA STRIP verify (every carried IDALL event==0 && area==0)"); log("#" * 96)
    bad = 0
    n = 0
    for blk, soup in comp["out_soup"].items():
        for tri in soup:
            cx = sum(v[0][0] for v in tri) / 3.0
            cz = sum(v[0][2] for v in tri) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            if cell not in comp["placed_R"]:
                continue
            for (p, _nn, _u, t) in tri:
                d = X.decode_id(int(round(t[0])))
                n += 1
                if d["event"] != 0 or d["area"] != 0:
                    bad += 1
    ok = bad == 0
    gate("STAGE3 DONOR-DISPATCH STRIP: 0 carried tris carry a donor event/area bit", ok,
         f"carried_verts={n} event_or_area_nonzero={bad}")
    return dict(n_carried_verts=n, event_area_nonzero=bad, ok=ok)


# ============================================================================================
# STAGE 4 -- composite plumbing
# ============================================================================================
def stage4_composite_plumbing(comp):
    log("\n" + "#" * 96); log("STAGE 4 -- composite plumbing (flat-mesh, grid, weld_audit, frame, cracks, "
                              "down-facing, open-edge)"); log("#" * 96)
    final = comp["final_blocks"]
    # flat-mesh invariant + grid bounds
    flat_bad = []
    grid_ok = True
    for blk, bm in final.items():
        if bm.vcount != len(bm.flat_index) or len(bm.flat_index) != 3 * len(bm.tris):
            flat_bad.append((list(blk), bm.vcount, len(bm.flat_index), len(bm.tris)))
        grid_ok = grid_ok and M.block_in_grid(blk[0], blk[1])
    gate("STAGE4 FLAT-MESH invariant (vcount==indexCount==3*tris) on every composite block", not flat_bad,
         f"{flat_bad[:6]}")
    gate("STAGE4 grid bounds (every composite block on the 24x20 grid)", grid_ok)

    # weld audit per block (0 near-miss vertex pairs)
    weld_total = 0
    weld_detail = {}
    for blk, bm in final.items():
        w = len(M.weld_audit([bm]))
        if w:
            weld_detail[f"{blk[0]},{blk[1]}"] = w
        weld_total += w
    gate("STAGE4 weld audit (0 near-miss vertex pairs in every composite block frame)", weld_total == 0,
         f"total={weld_total} per_block={weld_detail}")

    # frame bounds
    fbad = {}
    for blk, bm in final.items():
        lx = [v[0] for v in bm.verts]; lz = [v[2] for v in bm.verts]
        if not (-0.06 <= min(lx) and max(lx) <= BLOCK + 0.06 and -BLOCK - 0.06 <= min(lz) and max(lz) <= 0.06):
            fbad[f"{blk[0]},{blk[1]}"] = (round(min(lx), 3), round(max(lx), 3), round(min(lz), 3), round(max(lz), 3))
    gate("STAGE4 frame bounds (local verts inside the block frame +/- slack)", not fbad, f"{fbad}")

    # ---- world-soup composite audit (CALIBRATED against the carried-stock baseline: stock's own
    #      6-block core has 60 down-facing + 124 vertical-face same-XZ pairs -- topo-59 building
    #      footprints + rock walls -- which are FAITHFUL carried features, not weld defects; per the
    #      calibrate-the-instrument meta-law the gate is on EXCESS beyond the carried subset). --------
    gpos = []       # (x,y,z)
    gtris = []      # (i,j,k, carried)
    placed = comp["placed_R"]
    for blk, bm in final.items():
        base = len(gpos)
        ox, oz = X.block_world_origin(blk[0], blk[1])
        for v in bm.verts:
            gpos.append((v[0] + ox, v[1], v[2] + oz))
        for tri in bm.tris:
            w = [(bm.verts[tri[q]][0] + ox, bm.verts[tri[q]][2] + oz) for q in range(3)]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[1] for p in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            gtris.append((base + tri[0], base + tri[1], base + tri[2], cell in placed))
    # down-facing, split carried (faithful stock) vs grass-frame/weld (must be 0 NEW)
    down_carried = down_grass = 0
    for (i, j, k, carried) in gtris:
        a, b, c = gpos[i], gpos[j], gpos[k]
        ny2 = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        if ny2 <= 0:
            if carried:
                down_carried += 1
            else:
                down_grass += 1
    gate("STAGE4 composite down-facing on the GRASS FRAME / weld apron (0 NEW downward-wound tris; "
         "carried stock down-facing is faithful and reported separately)", down_grass == 0,
         f"down_grass_or_apron={down_grass} down_carried_faithful={down_carried}")
    # vertical faces (same-XZ diff-Y) are legit terrain -- REPORTED, not gated
    seen = {}
    vfaces = 0
    for (x, y, z) in gpos:
        k = (round(x, 3), round(z, 3))
        if k in seen and abs(seen[k] - y) > 1e-3:
            vfaces += 1
        else:
            seen.setdefault(k, y)
    # open-edge once-audit = THE WELD-INTEGRITY GATE (a perfect carry+weld has 0 once-edges above the
    # y=0 skirt; stock's core interior is watertight, so any residual is a seam defect). Split by class.
    ecnt = Counter()
    for (i, j, k, _c) in gtris:
        pts = [(round(gpos[v][0], 3), round(gpos[v][1], 3), round(gpos[v][2], 3)) for v in (i, j, k)]
        for q in range(3):
            if pts[q] == pts[(q + 1) % 3]:
                continue
            ecnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1
    open_bad = [e for e, nn in ecnt.items() if nn == 1
                and not (e[0][1] <= 1e-3 and e[1][1] <= 1e-3)]

    def _cls(e):
        (a, b) = e
        onbord = any(abs(p - round(p / BLOCK) * BLOCK) < 1e-2 for p in (a[0], a[2], b[0], b[2]))
        offgrid = any(abs(p - round(p / CELL) * CELL) > 1e-2 for p in (a[0], a[2], b[0], b[2]))
        return ("border" if onbord else "interior") + ("_offgrid" if offgrid else "_grid")
    open_classes = Counter(_cls(e) for e in open_bad)
    gate("STAGE4 WELD-INTEGRITY (0 once-edges above the y=0 sea skirt = watertight composite; stock's "
         "carried core interior is watertight, so any residual is a seam defect)", len(open_bad) == 0,
         f"open_edges={len(open_bad)} classes={dict(open_classes)} sample={open_bad[:3]}")
    return dict(flat_mesh_ok=not flat_bad, grid_ok=grid_ok, weld_near_miss=weld_total,
                frame_bounds_ok=not fbad, frame_bad=fbad, vertical_faces_reported=vfaces,
                down_grass_or_apron=down_grass, down_carried_faithful=down_carried,
                open_edges_above_skirt=len(open_bad), open_edge_classes=dict(open_classes),
                open_edge_sample=[list(e) for e in open_bad[:6]])


# ============================================================================================
# STAGE 5 -- sea + Donor + orphan + wang + mod-overwrite + effective-prefab + sea-layer
# ============================================================================================
def stage5_sea_and_gates(comp, game_root):
    log("\n" + "#" * 96); log("STAGE 5 -- sea + Donor + ORPHAN + WANG + MOD-OVERWRITE + effective-prefab + "
                              "SEA-LAYER"); log("#" * 96)
    final = comp["final_blocks"]
    footprint = sorted(final.keys())
    plane = ISL._sea_plane(disc=1, game=game_root)
    import dataclasses
    # Sea4 = the shared deep-ocean plane, seated per block. Hidden/blank the coast-only water parts.
    # THE UNDERLAP LAW (contract R1): a full-block Sea4 under the ecotone would flag CONVENTION-INVALID.
    # The ecotone is INTERIOR land; we still emit a Sea4 per block (the island's ocean floor), but the
    # contract gate reads it -- if it flags underlap we drop the ecotone blocks' Sea4 to a blank (the
    # sea is disjoint from land per THE SEA-LAYER LAW). We first try the honest full plane and let the
    # gate measure; STAGE 7 reports the underlap verdict.
    sea_by_cell = {}
    for blk in footprint:
        bx, by = blk
        hidden = {p.lower(): M.hidden_block_mesh(name=f"Block[{bx}][{by}] {p}", disc=1, x=bx, y=by)
                  for p in ("Sea1", "Sea2", "Sea3", "Sea5")}
        hidden["sea4"] = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
        sea_by_cell[blk] = hidden

    # SEA-LAYER LAW: Sea4 Y==0
    sea_y_bad = []
    for blk in footprint:
        s4 = sea_by_cell[blk]["sea4"]
        if any(abs(v[1]) > 1e-6 for v in s4.verts):
            sea_y_bad.append(f"{blk[0]},{blk[1]}")
    gate("STAGE5 SEA-LAYER LAW (every staged Sea4 vertex Y==0)", not sea_y_bad, f"{sea_y_bad[:6]}")

    # Donor.txt: this is a MINT (grass frame) with a carried ensemble; every block gets the mountain
    # blanket donor (0,0) -- the value is inert (every emitted part is its own explicit override), but
    # a Donor.txt must exist alongside a Terrain override per THE MOD-OVERWRITE convention.
    donor_ref = (0, 0)
    cell_donors = {blk: donor_ref for blk in footprint}

    # ORPHAN-DECAL gate (deployed-else-stock ring). cell_meshes = final Terrain per block. The carry's
    # cut seam leaves 2 orphan gd-decals (a carried gd-decal whose grass partner is a NEW minted-grass
    # cell); the productized redress (FIX-G, UV+topo only, ZERO geometry moved, AMBIGUOUS never touched)
    # closes them IN MEMORY on final[blk] BEFORE staging + scoring -- the design's anticipated
    # gd_seam_dress path. First WARN-measure, then redress, then re-measure (never trust a fix blind).
    cell_meshes = {blk: [("Terrain", final[blk])] for blk in footprint}
    try:
        pre = OG.orphan_decal_gate(cell_meshes, set(footprint), enforce=True, redress=False,
                                   mod_folder=None, disc=1, game=game_root)
        orphan = OG.orphan_decal_gate(cell_meshes, set(footprint), enforce=True, redress=True,
                                      mod_folder=None, disc=1, game=game_root)
        orphan["n_orphans_pre_redress"] = pre.get("n_orphans")
        orphan_ok = orphan.get("n_orphans", 1) == 0 and orphan.get("n_ambiguous", 1) == 0
    except Exception as e:
        orphan = {"error": str(e)}
        orphan_ok = False
    gate("STAGE5 ORPHAN-DECAL gate: 0 orphans / 0 ambiguous over the staged footprint (ring-true; the "
         "cut-seam orphans are redressed FIX-G in-memory before staging)", orphan_ok,
         f"{ {k: orphan.get(k) for k in ('n_orphans', 'n_ambiguous', 'n_orphans_pre_redress', 'ok', 'error')} }")

    # WANG-CARRY gate over the sea frame
    try:
        wang = TR.wang_carry_gate(sea_by_cell, set(footprint), enforce=True)
        wang_ok = wang.get("ok", False) and wang.get("incoherent", 1) == 0
    except Exception as e:
        wang = {"error": str(e)}
        wang_ok = False
    gate("STAGE5 WANG-CARRY gate: 0 incoherent frame edges (fresh open-ocean mint)", wang_ok,
         f"{ {k: wang.get(k) for k in ('ok', 'incoherent', 'incoherent_deep', 'error')} }")

    # MOD-OVERWRITE gate (real disk read)
    try:
        mod_ow = TR._mod_overwrite_gate(MOD, cell_donors, disc=1, game=game_root)
        mod_ok = mod_ow.get("ok", False)
    except Exception as e:
        mod_ow = {"error": str(e)}
        mod_ok = False
    gate("STAGE5 MOD-OVERWRITE gate: no existing mod override collides on the site blocks", mod_ok,
         f"{ {k: mod_ow.get(k) for k in ('ok', 'collisions', 'error')} }")

    # effective-prefab-arm: every block ships real Terrain -> 0 need a stub arm
    armed = 0
    for blk in footprint:
        names = [("Terrain", None), ("Sea4", None)]
        try:
            arm_mesh, gd = TR.effective_prefab_arm(names, cell=blk, sidecar_parts={"terrain", "sea4"},
                                                   disc=1, lod="0_1")
            if arm_mesh is not None:
                armed += 1
        except Exception:
            pass
    gate("STAGE5 effective-prefab-arm: 0 blocks need a water-only arming stub (every block ships Terrain)",
         armed == 0, f"armed={armed}")

    return dict(sea_by_cell=sea_by_cell, cell_donors=cell_donors, donor_ref=list(donor_ref),
                sea_layer_ok=not sea_y_bad, orphan=orphan, orphan_ok=orphan_ok, wang=wang, wang_ok=wang_ok,
                mod_overwrite=mod_ow, mod_ok=mod_ok, n_armed=armed)


# ============================================================================================
# STAGE 6 -- stage the file set
# ============================================================================================
def stage6_write(comp, sea):
    log("\n" + "#" * 96); log(f"STAGE 6 -- stage the file set -> {OUT_ROOT}"); log("#" * 96)
    import shutil
    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    final = comp["final_blocks"]
    written = []
    for blk in sorted(final):
        bx, by = blk
        parts = {"Terrain": final[blk], "Sea4": sea["sea_by_cell"][blk]["sea4"]}
        for p in ("Sea1", "Sea2", "Sea3", "Sea5"):
            parts[p] = sea["sea_by_cell"][blk][p.lower()]
        parts["Object"] = M.hidden_block_mesh(name=f"Block[{bx}][{by}] Object", disc=1, x=bx, y=by)
        parts["Beach1"] = M.hidden_block_mesh(name=f"Block[{bx}][{by}] Beach1", disc=1, x=bx, y=by)
        for part_name, bm in parts.items():
            rel = M.override_relpath(1, bx, by, "0_1", part_name)
            path = OUT_ROOT / rel
            M.write_ff9mesh(bm, path)
            written.append(str(path))
        rel_d = M.donor_sidecar_relpath(1, bx, by, "0_1")
        dp = OUT_ROOT / rel_d
        dp.parent.mkdir(parents=True, exist_ok=True)
        d = sea["cell_donors"][blk]
        dp.write_text(f"{d[0]},{d[1]}", encoding="utf-8")
        written.append(str(dp))
    log(f"  staged {len(written)} files across {len(final)} blocks")
    return dict(n_files=len(written), n_blocks=len(final), root=str(OUT_ROOT))


# ============================================================================================
# STAGE 7 -- THE CONTRACT SCREEN
# ============================================================================================
def stage7_contract(game_root):
    log("\n" + "#" * 96); log("STAGE 7 -- THE CONTRACT SCREEN (contract_mass_gates v4 over the staged tree)"); log("#" * 96)
    # stock reference (calibrate the instrument)
    stock = CMG.load_candidate("stock_ecotone_13-15_11-12", None, core_blocks=CMG.ECOTONE_CORE)
    stock_row = CMG.run_matrix_on(stock)
    # staged Rung F candidate
    cand = CMG.load_candidate("rung_f_staged", str(OUT_ROOT))
    row = CMG.run_matrix_on(cand)
    r1, r2, r3 = row["R1"], row["R2"], row["R3"]
    log(f"  Rung F: R1={r1['verdict']} R2={r2['verdict']} R3={r3['verdict']}  overall={row['overall']}")
    log(f"    R1 measured: boundary={r1['checks']['boundary_cell']['measured_u']}u "
        f"straddle={r1['checks']['straddle_cell']['measured_u']}u body={r1['checks']['body_tri']['measured_u']}u "
        f"(floors 39.953/44.635/42.968); convention_invalid={r1['convention_invalid']}")
    log(f"    R2 sat grass={r2['saturation']['grass_decal']} any={r2['saturation']['any_decal']}; "
        f"fringe={r2['arrangement']['fringe_concentration']} pen={r2['arrangement']['penetration_ge2_fraction']} "
        f"float={r2['arrangement']['n_floating_components']}")
    log(f"    R3 reachable_backing={r3['largest_reachable_backing_cells']} interface="
        f"{r3['skin_backing_interface_pairs']} erosion={r3['erosion_survive_backing_cells']}")

    def r2n(rr):
        return dict(sat_grass=rr["saturation"]["grass_decal"], sat_any=rr["saturation"]["any_decal"],
                    fringe=rr["arrangement"]["fringe_concentration"],
                    penetration=rr["arrangement"]["penetration_ge2_fraction"],
                    floating=rr["arrangement"]["n_floating_components"],
                    body_total=rr["body"]["label_blind_total"])

    def r3n(rr):
        return dict(reachable_backing=rr["largest_reachable_backing_cells"],
                    interface=rr["skin_backing_interface_pairs"],
                    erosion=rr["erosion_survive_backing_cells"])

    calib = dict(
        stock_R2=r2n(stock_row["R2"]), rungf_R2=r2n(r2),
        stock_R3=r3n(stock_row["R3"]), rungf_R3=r3n(r3),
        R2_matches_stock=(r2n(r2) == r2n(stock_row["R2"])),
        R3_matches_stock=(r3n(r3) == r3n(stock_row["R3"])))
    log(f"  CALIBRATION vs stock: R2_matches={calib['R2_matches_stock']} R3_matches={calib['R3_matches_stock']}")
    log(f"    stock R2={calib['stock_R2']}\n    rungF R2={calib['rungf_R2']}")
    log(f"    stock R3={calib['stock_R3']}\n    rungF R3={calib['rungf_R3']}")

    gate("CONTRACT R1 realized-boundary standoff PASS", r1["verdict"] == "PASS",
         f"verdict={r1['verdict']} measured={ {k: r1['checks'][k]['measured_u'] for k in r1['checks']} }")
    gate("CONTRACT R2 saturation + arrangement PASS", r2["verdict"] == "PASS",
         f"verdict={r2['verdict']}")
    gate("CONTRACT R3 inland-backing extent PASS", r3["verdict"] == "PASS", f"verdict={r3['verdict']}")
    gate("CONTRACT stock reference still PASSES all three (instrument calibrated)",
         stock_row["overall"] == "PASS", f"stock={stock_row['overall']}")

    return dict(stock=stock_row, rung_f=row, calibration=calib,
                all_three_pass=(row["overall"] == "PASS"), stock_pass=(stock_row["overall"] == "PASS"))


# ============================================================================================
# STAGE 8 -- renders (offline eye)
# ============================================================================================
def stage8_renders(comp):
    log("\n" + "#" * 96); log(f"STAGE 8 -- renders (offline eye) -> {RENDER_DIR}"); log("#" * 96)
    try:
        from PIL import Image, ImageDraw
    except Exception as e:
        log(f"  PIL unavailable ({e}) -- skipping renders")
        return dict(rendered=[], error=str(e))
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    final = comp["final_blocks"]
    # world triangle soup with family colour
    FAM_COL = {"grass": (86, 140, 60), "desert": (200, 176, 110), "dunes": (222, 200, 140),
               "rock": (120, 112, 104), None: (150, 150, 150)}
    tris = []            # (p3, colour, mean_y)
    for blk, bm in final.items():
        ox, oz = X.block_world_origin(blk[0], blk[1])
        for tri in bm.tris:
            p3 = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            idall0 = int(round(bm.tangents[tri[0]][0]))
            topo = X.decode_id(idall0)["topograph"]
            from seam_null_recon import FAM_OF
            fam = FAM_OF.get(topo)
            if topo == 49:
                fam = "rock"
            tris.append((p3, FAM_COL.get(fam, FAM_COL[None]), sum(p[1] for p in p3) / 3.0))
    xs = [p[0] for (p3, _c, _y) in tris for p in p3]
    zs = [p[2] for (p3, _c, _y) in tris for p in p3]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    rendered = []

    def planview(fname, title, shade=False, light=(0.5, 0.8, 0.3)):
        W, H = 900, 900
        pad = 30
        sx = (W - 2 * pad) / (x1 - x0)
        sz = (H - 2 * pad) / (z1 - z0)
        s = min(sx, sz)
        img = Image.new("RGB", (W, H + 26), (20, 22, 26))
        dr = ImageDraw.Draw(img)
        dr.text((pad, 6), title, fill=(235, 225, 170))
        order = sorted(tris, key=lambda t: t[2])            # painter's, low first
        ll = math.sqrt(sum(c * c for c in light)) or 1.0
        lv = [c / ll for c in light]
        for (p3, col, _my) in order:
            pts = [(pad + (p[0] - x0) * s, 26 + H - pad - (p[2] - z0) * s) for p in p3]
            c = col
            if shade:
                e1 = [p3[1][k] - p3[0][k] for k in range(3)]
                e2 = [p3[2][k] - p3[0][k] for k in range(3)]
                gn = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
                gl = math.sqrt(sum(q * q for q in gn)) or 1.0
                sh = max(0.35, min(1.0, 0.45 + 0.55 * abs(sum(gn[k] * lv[k] for k in range(3)) / gl)))
                c = tuple(int(v * sh) for v in col)
            dr.polygon(pts, fill=c)
        img.save(RENDER_DIR / fname)
        rendered.append(str(RENDER_DIR / fname))
        log(f"  wrote {fname}")

    planview("rung_f_planview.png", "RUNG F -- planview by ground family (grass/desert/dunes/rock), "
             "whole 4x4 landmass + carried junction", shade=False)
    planview("rung_f_shaded.png", "RUNG F -- shaded relief (whole landmass; the carried valley reads "
             "as low relief in a flat grass island)", shade=True)

    # oblique of the junction area
    def oblique(fname, title, pitch=32.0):
        W, H = 1000, 620
        cxw = (x0 + x1) / 2.0
        czw = (z0 + z1) / 2.0
        az = math.radians(215.0)
        pr = math.radians(pitch)
        # simple camera: rotate about Y by az, tilt by pitch, orthographic
        pts_all = []
        order = sorted(tris, key=lambda t: -(math.cos(az) * (sum(p[0] for p in t[0]) / 3 - cxw)
                                             + math.sin(az) * (sum(p[2] for p in t[0]) / 3 - czw)))
        proj = []
        for (p3, col, _my) in order:
            sp = []
            for p in p3:
                dx = p[0] - cxw; dz = p[2] - czw; dy = p[1] - LAND_HEIGHT
                rx = math.cos(az) * dx - math.sin(az) * dz
                rz = math.sin(az) * dx + math.cos(az) * dz
                sy = rz * math.sin(pr) - dy * math.cos(pr)
                sp.append((rx, sy))
                pts_all.append((rx, sy))
            proj.append((sp, p3, col))
        pxs = [q[0] for q in pts_all]; pys = [q[1] for q in pts_all]
        s = min((W - 40) / (max(pxs) - min(pxs)), (H - 40) / (max(pys) - min(pys)))
        img = Image.new("RGB", (W, H + 26), (20, 22, 26))
        dr = ImageDraw.Draw(img)
        dr.text((20, 6), title, fill=(235, 225, 170))
        lv = (0.4, 0.82, 0.4); ll = math.sqrt(sum(c * c for c in lv))
        lv = [c / ll for c in lv]
        for (sp, p3, col) in proj:
            pts = [(20 + (q[0] - min(pxs)) * s, 26 + 20 + (q[1] - min(pys)) * s) for q in sp]
            e1 = [p3[1][k] - p3[0][k] for k in range(3)]
            e2 = [p3[2][k] - p3[0][k] for k in range(3)]
            gn = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
            gl = math.sqrt(sum(q * q for q in gn)) or 1.0
            sh = max(0.35, min(1.0, 0.45 + 0.55 * abs(sum(gn[k] * lv[k] for k in range(3)) / gl)))
            dr.polygon(pts, fill=tuple(int(v * sh) for v in col))
        img.save(RENDER_DIR / fname)
        rendered.append(str(RENDER_DIR / fname))
        log(f"  wrote {fname}")

    oblique("rung_f_oblique.png", "RUNG F -- oblique shaded (az215/pitch32): the mixed-biome junction "
            "carried into the flat grass island")
    return dict(rendered=rendered, world_bbox=[round(x0, 1), round(z0, 1), round(x1, 1), round(z1, 1)])


# ============================================================================================
# main
# ============================================================================================
def main():
    game_root = Path(_cfg.find_game_path(None))
    log(f"game root: {game_root}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    s0 = stage0_site(game_root)
    comp = RFL.compose(game_root)
    s1 = stage1_frame_verify(comp["built"], game_root)
    s2 = stage2_rigidity(comp)
    s3 = stage3_event_strip(comp)
    s4 = stage4_composite_plumbing(comp)
    s5 = stage5_sea_and_gates(comp, game_root)
    s6 = stage6_write(comp, s5)
    s7 = stage7_contract(game_root)
    s8 = stage8_renders(comp)

    plumbing_gates = [g for g in GATES if not g["name"].startswith("CONTRACT")
                      and not g["name"].startswith("ADVISORY")]
    contract_gates = [g for g in GATES if g["name"].startswith("CONTRACT")]
    advisory_gates = [g for g in GATES if g["name"].startswith("ADVISORY")]
    plumbing_green = all(g["ok"] for g in plumbing_gates)
    contract_green = s7["all_three_pass"] and s7["stock_pass"]
    all_green = plumbing_green and contract_green

    known_residuals = dict(
        R1_STRUCTURAL_BLOCKER=dict(
            status="STRUCTURAL -- R1 CANNOT PASS WITH THIS WINDOW (round-2 measurement FALSIFIES the "
            "round-1 'weldable seam artifact' hypothesis)",
            headline="R1 is capped at ~2.83u (the nearest carried MOUNTAIN WALL to the ecotone), not the "
            "~50u the round-1 design predicted. The 243 round-1 once-edges are NOT all weldable seam "
            "artifacts: 199 of the 251 carried-boundary once-edges are INTRINSIC TALL MOUNTAIN WALLS.",
            measured=dict(
                carried_boundary_once_edges=251, lowland_lt6u=52, tall_ge6u=199,
                tall_heights_u="6..39.5",
                nearest_tall_wall_to_ecotone_boundary_u=2.83,
                nearest_tall_wall_to_ecotone_straddle_u=6.32,
                nearest_lowland_seam_to_ecotone_u=2.00,
                window_cell_max_height_pctl="p10=2.7 p25=3.3 p50=7.0 p75=21.4 p90=29.5 max=39.5",
                height_cap_drop_does_not_separate="CAP=8 (drop to 802 cells) STILL leaves 173 tall "
                "once-edges at 2.0u; dropping fragments the mesh and exposes NEW tall edges (measured "
                "CAP in {0,8,10,12,15})"),
            why="R1 measures the ecotone -> nearest single-owner (coast) edge on the staged land-"
            "perimeter silhouette (single_owner_edges over ALL land tris, no coastal filter). The "
            "carried 6-block core is a MOUNTAIN-LOCKED VALLEY whose lowland grass|desert ecotone skin is "
            "INTERWOVEN with 6-40u mountains (cell max-height p50=7u, p75=21u -- not a separable ring). "
            "The window PERIMETER cuts THROUGH those mountains, so the carried boundary is a set of "
            "EXPOSED CLIFF-TOP once-edges 2.83u from the ecotone. A cliff top is genuinely open in the "
            "carried mesh (the donor terrain ended at the window edge) and CANNOT be closed by welding "
            "to a flat grass island (a foot-weld leaves the top rim open; a top-weld needs terrain we "
            "did not carry). No seam weld reduces the 199 tall once-edges -> R1 stays ~2.8u << 40u.",
            why_massif_carry_does_not_apply="the PROVEN massif-carry apron/zip (Uaho, horseshoe, in-game "
            "2026-07-13/15) welds a mountain into grass ONLY because its window PERIMETER sits at the "
            "mountain's LOWLAND grass FOOT (donor rim y 2.3..8.0) with the PEAK fully ENCLOSED watertight "
            "-- so its boundary is lowland (welds gently) and its summit is a two-owner interior. Rung "
            "F's window has NO such lowland perimeter: it slices a valley wall at elevation.",
            fix="NOT a seam weld -- a WINDOW RE-SELECTION. Carry a LARGER, block-aligned window whose "
            "PERIMETER lies entirely at LOWLAND (the mountains' outer feet), fully enclosing the ecotone "
            "AND its mountains watertight (the deferred S1 CARRY_WITH_TERMINATION / S2 neck-termination "
            "scan), OR find a grass|desert|dunes ecotone that is NOT mountain-locked. Only then does the "
            "massif-carry apron close the boundary and R1 measure ecotone -> true island coast (~50u). "
            "A >=6-block block-aligned site (removing the x half-block phase shift) is a necessary but "
            "NOT sufficient companion -- it fixes the fine/coarse seam density but not the exposed walls."),
        weld_integrity=dict(
            status="OPEN (dominated by the R1 structural blocker; the SEAM part is largely CLOSED)",
            open_edges=s4["open_edges_above_skirt"], classes=s4["open_edge_classes"],
            seam_progress="the rung_f_stitch seam weld (base corner-snap + lowland apron weld + seam-only "
            "T-junction elimination) reduced the LOWLAND once-edges from 243 (round 1) to ~53; the "
            "residual ~196 are the INTRINSIC TALL MOUNTAIN WALLS (see R1_STRUCTURAL_BLOCKER) + the border "
            "clips that frame-bounds compliance mints. The lowland seam weld MECHANISM is proven sound; "
            "it is simply not the bottleneck.",
            root_cause="the residual is the carried valley's exposed mountain-wall rims, not the "
            "fine-conform/coarse-lattice seam (that part welds)."),
        stitch_deliverable=dict(
            status="BUILT + WIRED (rung_f_stitch.py) -- the seam weld the task requested",
            what="corner_snap (round-1's full boundary-corner weld = the ~243 floor) + weld_grass_to_"
            "boundary (project LOWLAND grass hole-rim verts onto dC, apron law, deformation to the grass) "
            "+ eliminate_tjunctions (SEAM-ONLY fixed candidate set, single-pass multi-insert, bounded, "
            "no cascade -- edge-lerped inserts per the DEFORMED-TILE/clip law) + enforce_upface (apron "
            "ring only) + frame-clip re-block.",
            measured_improvements="down-facing 13 -> 0 (PASS), frame-bounds FAIL -> PASS, lowland "
            "once-edges 243 -> ~53, byte-rigidity PRESERVED (interior_whole tris untouched, only the "
            "boundary ring splits -> counted as clipped_pieces). max apron lift 39u -> 4u.",
            note="the FIRST-CUT surgical version welded lowland-only and TORE the grass (442 once-edges) "
            "and a whole-soup T-junction pass CASCADED (77865 splits); both are recorded dead ends -- the "
            "working recipe is corner-snap base + seam-only bounded T-junction."),
        weld_audit_near_miss=dict(
            status="OPEN (pre-existing; round-1 had 16, now 15)", near_miss=s4["weld_near_miss"],
            note="seam-precision residual (lerp-insert vs corner-snap verts <0.05u apart) in the "
            "seam blocks; unchanged in character from round 1, not introduced by the stitch."),
        coast_shape_advisory=dict(
            status="ADVISORY (cosmetic; not in the task's verify_landmass criteria)",
            detail="the minted coast is smoother than FF9's measured med-turn language (a large-radius "
            "circle reads med_turn ~4 deg/8u vs the 8-35 band); closed by a higher-undulation or "
            "multi-lobe coast in a polish round -- it does not affect watertightness or the contract."))

    report = dict(
        meta=dict(round="RUNG F -- THE MIXED-BIOME BUILD, BUILD-FIX ROUND 2 (staged dry-run)",
                  generated_by="rung_f_build.py", read_only=True, zero_game_writes=True, zero_deploys=True,
                  design="out/rung_f/design_round1.json",
                  round2_verdict="RED -- R1 is STRUCTURALLY blocked (mountain-locked valley), NOT a "
                  "weldable-seam defect; the seam weld is built + proven on the lowland seam but is not "
                  "the bottleneck. See known_residuals.R1_STRUCTURAL_BLOCKER for the falsifying "
                  "measurement and the WINDOW-RE-SELECTION fix."),
        stage0_site=s0,
        compose_diag=comp["diag"],
        stage1_frame_verify=s1,
        stage2_rigidity=s2,
        stage3_event_strip=s3,
        stage4_composite_plumbing=s4,
        stage5_sea_and_gates=dict(sea_layer_ok=s5["sea_layer_ok"], orphan_ok=s5["orphan_ok"],
                                  orphan={k: s5["orphan"].get(k) for k in ("n_orphans", "n_ambiguous", "ok", "error")},
                                  wang_ok=s5["wang_ok"],
                                  wang={k: s5["wang"].get(k) for k in ("ok", "incoherent", "incoherent_deep", "error")},
                                  mod_ok=s5["mod_ok"], n_armed=s5["n_armed"], donor_ref=s5["donor_ref"]),
        stage6_write=s6,
        stage7_contract=dict(all_three_pass=s7["all_three_pass"], stock_pass=s7["stock_pass"],
                             calibration=s7["calibration"],
                             rung_f=dict(overall=s7["rung_f"]["overall"],
                                         R1=s7["rung_f"]["R1"], R2=s7["rung_f"]["R2"], R3=s7["rung_f"]["R3"]),
                             stock=dict(overall=s7["stock"]["overall"])),
        stage8_renders=s8,
        gates=GATES,
        known_residuals=known_residuals,
        plumbing_green=plumbing_green,
        contract_green=contract_green,
        all_green=all_green,
        advisory_failed=[g["name"] for g in advisory_gates if not g["ok"]],
        headline=("ROUND 2: the seam weld (rung_f_stitch) is BUILT + WIRED and PROVEN on the lowland "
                  "seam (down-facing 13->0 PASS, frame-bounds FAIL->PASS, lowland once-edges 243->~53, "
                  "byte-rigidity preserved); but R1 is NOT a weldable-seam defect -- it is a STRUCTURAL "
                  "mountain-locked-valley blocker. Round-2 measurement FALSIFIES the round-1 hypothesis: "
                  "199 of 251 carried-boundary once-edges are INTRINSIC tall mountain walls (>=6u, up to "
                  "39.5u), the nearest 2.83u from the ecotone; the window perimeter slices a valley wall "
                  "at elevation, so R1 is capped at ~2.8u << the 40u floor and no seam weld can fix it. "
                  "R2+R3 still PASS at exact stock calibration. FIX = a WINDOW RE-SELECTION to a lowland-"
                  "perimeter window (see known_residuals.R1_STRUCTURAL_BLOCKER), NOT a weld. Remaining "
                  "plumbing FAILs are all downstream of this: weld-integrity (196 intrinsic walls) + "
                  "weld-audit (15, pre-existing)."),
        n_gates=len(GATES),
        n_failed=sum(1 for g in GATES if not g["ok"] and not g["name"].startswith("ADVISORY")),
        plumbing_failed=[g["name"] for g in plumbing_gates if not g["ok"]],
        contract_failed=[g["name"] for g in contract_gates if not g["ok"]],
    )
    OUT_JSON.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log("\n" + "=" * 96)
    log(f"PLUMBING {'GREEN' if plumbing_green else 'RED'} | CONTRACT {'GREEN' if contract_green else 'RED'} "
        f"| ALL {'GREEN' if all_green else 'RED'}")
    log(f"plumbing failed: {report['plumbing_failed']}")
    log(f"contract failed: {report['contract_failed']}")
    log(f"advisory failed: {report['advisory_failed']}")
    log(f"-> {OUT_JSON}")
    return 0 if all_green else 1


if __name__ == "__main__":
    sys.exit(main())
