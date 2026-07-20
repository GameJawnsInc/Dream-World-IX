"""THE FIRST MINTED DUNES ECOTONE PATCH -- implements ``dunes_mint_design.md`` verbatim.

Not a carry (THE NO-ENCLOSED-DUNES LAW): a plain ``--ground desert`` `world-island` host, then an
IN-PLACE RETILE of a compact interior cell-set -- a 3x3 dunes-mains CORE, wrapped in a two-shell
strip RING (inner shell topo 41/dunes-side, outer shell topo 17/desert-side, both wearing the
``STRIPS[("desert","dunes")]`` seam UV), placed via round 3's BFS row emitter
(``dunes_strip_emitter.py``) with its measured constants FROZEN below (re-verified live every run
against the same script, LAW 5). Geometry (vertex positions/normals/triangle winding/block
partition) is byte-identical to the plain desert mint at every step -- only ``uv`` and
``tangent.x`` (topograph) change on the touched triangles.

SITE (design doc Sec.4, orchestrator-locked): island.build_landmass(center=(672,-1248),
base_radius=26, seed=2.0, ground="desert") -> single block (10,19), 494 tris. Dunes core = the
3x3 cell block x in {164,165,166} z in {-314,-313,-312} (world centre (662,-1250)). Ring = the
two 4-neighbour BFS shells around the core (inner touches the core -> topo 41; outer touches only
remaining plain desert -> topo 17); beyond the ring, everything stays untouched desert mains (the
verified 2-cell all-desert margin -- THE WALL-CONTEXT LAW never comes into play, ground="desert"
is wall_coastal=True and the patch never nears the rim).

Gate list = design doc Sec.5, in order. NO --deploy is ever invoked by the harness that runs this
(the --deploy CODE PATH is implemented per the brief but must not be executed).

Run from the repo root:  py studies/overworld-topography/dunes_patch_mint.py [--deploy]
Artifacts -> out/dunes_patch_mint.json, out/dunes_patch_mint_*.png
"""
from __future__ import annotations

import copy
import dataclasses
import json
import math
import random
import subprocess
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                          # noqa: E402
from ff9mapkit.world import discmirror as DM                  # noqa: E402
from ff9mapkit.world import extract as X                      # noqa: E402
from ff9mapkit.world import grassland as G                    # noqa: E402
from ff9mapkit.world import island as I                       # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import placement as P                    # noqa: E402

DEPLOY = "--deploy" in sys.argv
if DEPLOY:
    sys.exit("this harness run refuses --deploy per the lane's HARD RULES -- the code path exists "
             "(see deploy_patch() below) but must be invoked by a human, out of band")

HERE = Path(__file__).parent
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)

MOD = "FF9CustomMap-world"
CENTER = (672.0, -1248.0)
RADIUS = 26.0
SEED = 2.0
GROUND = "desert"
CORE_ORIGIN = (164, -314)                                     # cell coords (i, j); world = 4*i, 4*j
CORE_SIZE = 3                                                  # 3x3 -> world centre (662, -1250)
PAIR = ("desert", "dunes")
MAINS_SEED = 0xF91                                             # build_landmass's own default mains_seed
MINT_SEED = 0                                                  # the row emitter's seed (recorded)
BLOCK = 64.0
CELL_U = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
EPS = 0.006
TOL_V = 0.008
ROW_PITCH = 0.03125

GATES: list = []                                               # (name, ok, detail)


def gate(name: str, ok: bool, detail: str = ""):
    GATES.append((name, bool(ok), detail))
    print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return ok


# ============================================================================================
# THE FROZEN ROW-EMITTER CONSTANTS (dunes_strip_emitter.py round 3, re-derived this session --
# see _live_reverify() below, which re-runs the SAME script's Step 1+2 via the exec-and-cut
# technique already used by dunes_mint_design.md's own reproduction log, and asserts these
# literals still match it byte-for-byte. DELTA_P also matches out/dunes_strip_emitter.json's
# "delta_p" key exactly; TARGET_PMF is NOT persisted in that JSON (the emitter script only dumps
# it to stdout), so it is verified against the live re-derivation only.)
# ============================================================================================
FROZEN_TARGET_PMF = {
    "A-only": {0: 0.5303030303030303, 1: 0.25757575757575757, 2: 0.015151515151515152, 3: 0.19696969696969696},
    "both": {0: 0.17045454545454544, 1: 0.2916666666666667, 2: 0.23863636363636365, 3: 0.29924242424242425},
    "B-only": {0: 0.05172413793103448, 1: 0.29310344827586204, 2: 0.5689655172413793, 3: 0.08620689655172414},
    "neither": {0: 0.5, 1: 0.2777777777777778, 2: 0.16666666666666666, 3: 0.05555555555555555},
}
FROZEN_DELTA_P = {0: 0.09774436090225563, 1: 0.5263157894736842, 2: 0.2932330827067669, 3: 0.08270676691729323}


def emit_strip_rows(cells, touch_of_local, target_pmf, delta_p, seed=0):
    """VERBATIM copy of dunes_strip_emitter.py's emitter (round 3) -- pure deterministic code, not
    a measured number, so it is reused as code (not re-derived); its INPUT DATA (target_pmf/
    delta_p) is what gets frozen+reverified above."""
    rng = random.Random(seed)
    cellset = set(cells)

    def nbrs(c):
        i, j = c
        return [n for n in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)) if n in cellset]

    adj = {c: nbrs(c) for c in cellset}
    order = []
    remaining = set(cellset)
    while remaining:
        root = min(remaining)
        seen = {root}
        q = deque([root])
        while q:
            c = q.popleft(); order.append(c)
            for n in sorted(adj[c]):
                if n not in seen:
                    seen.add(n); q.append(n)
        remaining -= seen
    assigned = {}
    for c in order:
        cat = touch_of_local.get(c, "neither")
        pmf = target_pmf[cat]
        nbr_rows = [assigned[n] for n in adj[c] if n in assigned]
        weights = []
        for r in range(4):
            w_target = pmf[r]
            if nbr_rows:
                w_trans = 1.0
                for nr in nbr_rows:
                    w_trans *= max(delta_p.get(abs(r - nr), 1e-6), 1e-6)
                w_trans **= (1.0 / len(nbr_rows))
            else:
                w_trans = 1.0
            weights.append(w_target * w_trans)
        tot = sum(weights)
        probs = [w / tot for w in weights]
        assigned[c] = rng.choices(range(4), weights=probs, k=1)[0]
    return assigned


def _live_reverify():
    """Re-run dunes_strip_emitter.py's Step 1 (map-wide census) + Step 2 (emitter def) via the
    exec-and-cut technique the design doc's own reproduction log already used, and assert the
    FROZEN constants above still match byte-for-byte. Returns the live namespace (also reused
    below for the offline-eye's stock calibration windows -- no second 480-block scan)."""
    src_path = HERE / "dunes_strip_emitter.py"
    src = src_path.read_text(encoding="utf-8")
    marker = "# ============================================================================================\n# STEP 3"
    idx = src.index(marker)
    truncated = src[:idx]
    ns = {"__name__": "_dunes_strip_emitter_trunc_S1S2", "__file__": str(src_path)}
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(truncated, "dunes_strip_emitter.py(trunc@STEP3)", "exec"), ns)
    live_target = {cat: {int(k): float(v) for k, v in d.items()} for cat, d in ns["TARGET_PMF"].items()}
    live_delta = {int(k): float(v) for k, v in ns["DELTA_P"].items()}
    tp_ok = live_target == FROZEN_TARGET_PMF
    dp_ok = live_delta == FROZEN_DELTA_P
    max_tp_diff = max((abs(live_target[c][r] - FROZEN_TARGET_PMF[c][r]) for c in FROZEN_TARGET_PMF for r in range(4)), default=0.0)
    max_dp_diff = max((abs(live_delta[r] - FROZEN_DELTA_P[r]) for r in range(4)), default=0.0)
    gate("frozen TARGET_PMF matches live re-derivation (dunes_strip_emitter.py Step1+2, exec-and-cut)",
         tp_ok, f"max|diff|={max_tp_diff:.2e}")
    gate("frozen DELTA_P matches live re-derivation", dp_ok, f"max|diff|={max_dp_diff:.2e}")
    json_path = OUTD / "dunes_strip_emitter.json"
    if json_path.is_file():
        rec = json.loads(json_path.read_text(encoding="utf-8"))
        json_delta = {int(k): float(v) for k, v in rec["delta_p"].items()}
        gate("frozen DELTA_P matches out/dunes_strip_emitter.json byte-for-byte",
             json_delta == FROZEN_DELTA_P, f"json={json_delta}")
    else:
        gate("out/dunes_strip_emitter.json present for cross-check", False, "missing -- run dunes_strip_emitter.py first")
    return ns


# ============================================================================================
# strip_uv() -- design doc Sec.2, authored to mirror mains_uv() exactly (ori fixed at 0, the
# conservative/measured-safe choice -- round 2/3 never varied tile rotation within a strip cell)
# ============================================================================================

def strip_uv(x: float, z: float, cell, row: int, ori: int = 0, *, pair=PAIR):
    (i, j) = cell
    fx, fz = (x - CELL_U * i) / CELL_U, (z - CELL_U * j) / CELL_U
    a, b = G.rot_ab(fx, fz, ori)
    a, b = max(0.0, min(1.0, a)), max(0.0, min(1.0, b))
    S = G.STRIPS[pair]
    u0, u1 = G.STRIP_U
    v0, v1 = G.STRIPS_V[row]
    return [u0 + a * (u1 - u0) + S["du"], v0 + b * (v1 - v0) + S["dv"]]


# ---- the zero-residual classification oracle (reimplemented, not imported -- LAW 5) --------------

STRIP_U0, STRIP_U1 = G.STRIP_U
ROW0_V0 = G.STRIPS_V[0][0]
_S = G.STRIPS[PAIR]
_DU, _DV = _S["du"], _S["dv"]
TOPO_FAM = {17: "desert", 41: "dunes", 58: "rock"}


def _mains_rect(fam):
    m = G.FAM_REGION["main"]
    g = G.GROUNDS[fam]
    return (m[0] + g["mains_du"], m[1] + g["mains_dv"], m[2] + g["mains_du"], m[3] + g["mains_dv"])


RECTS = {"desert": _mains_rect("desert"), "dunes": _mains_rect("dunes")}


def _rect_contains(rect, uv3, eps=EPS):
    return all(rect[0] - eps <= u <= rect[2] + eps and rect[1] - eps <= v <= rect[3] + eps for (u, v) in uv3)


def classify_strip(uv3):
    u_lo, u_hi = STRIP_U0 + _DU - EPS, STRIP_U1 + _DU + EPS
    if not all(u_lo <= u <= u_hi for (u, _v) in uv3):
        return None
    v_min = min(v for (_u, v) in uv3)
    row0 = ROW0_V0 + _DV
    k = round((v_min - row0) / ROW_PITCH)
    if k < 0 or k > 3:
        return None
    if abs((v_min - row0) - k * ROW_PITCH) > TOL_V:
        return None
    return int(k)


def classify_tri(topo, uv3):
    fam = TOPO_FAM.get(topo)
    if fam in PAIR:
        k = classify_strip(uv3)
        if k is not None:
            return ("strip", k)
    rect = RECTS.get(fam)
    if rect and _rect_contains(rect, uv3):
        return ("mains", fam)
    if fam == "rock":
        lo_u, lo_v = I.ROCK_U[0] + G.GROUNDS["desert"]["wall_du"], min(I.ROCK_V) + G.GROUNDS["desert"]["wall_dv"]
        hi_u, hi_v = I.ROCK_U[1] + G.GROUNDS["desert"]["wall_du"], max(I.ROCK_V) + G.GROUNDS["desert"]["wall_dv"]
        if _rect_contains((lo_u, lo_v, hi_u, hi_v), uv3, eps=1e-3):
            return ("rock",)
    return ("other",)


# ============================================================================================
# STEP 1 -- build the plain desert host in memory (no writes)
# ============================================================================================

def build_host():
    built = I.build_landmass(center=CENTER, base_radius=RADIUS, seed=SEED, ground=GROUND, stamps=None, disc=1)
    cells = sorted(built["blocks"])
    gate("host is a single block (design site pick)", cells == [(10, 19)], f"blocks={cells}")
    CELL = cells[0]
    occupied = {blk: occ for blk in cells if (occ := I._real_block_parts(blk, disc=1, game=None))}
    gate("OPEN-OCEAN TARGET (every touched block is true open ocean)", not occupied, f"occupied={occupied}")
    gate("THE WALL-CONTEXT LAW (ground=desert -> wall_coastal=True)", G.GROUNDS[GROUND]["wall_coastal"] is True,
         "enforced by build_landmass at call time; would have raised otherwise")
    plane = I._sea_plane(disc=1, game=None)
    report = I.verify_landmass(built, sea_plane=plane, land_height=3.2)
    gate("mint acceptance -- verify_landmass on the plain host (baseline, pre-retile)", report["clean"],
         f"{ {k: v for k, v in report.items() if k not in ('placement', 'shape')} }")
    n_tris = len(built["blocks"][CELL].tris)
    print(f"host: block {CELL}, {n_tris} tris, seed {built['seed']}, centre {built['center']}")
    return built, CELL, plane, report


# ============================================================================================
# STEP 2 -- the retile (in place; zero vertex motion by construction -- uv/tangent.x only)
# ============================================================================================

def to_world(bm, cell):
    bx, by = cell
    return [(v[0] + BLOCK * bx, v[1], v[2] - BLOCK * by) for v in bm.verts]


def dilate(seed_cells, exclude):
    nxt = set()
    for c in seed_cells:
        for (di, dj) in NEI4:
            n = (c[0] + di, c[1] + dj)
            if n not in exclude:
                nxt.add(n)
    return nxt


def _cell_is_regular(cell, tri_list, tris_idx, world_pos, *, tol=0.02):
    """A cell is a clean axis-aligned 4u-square (2 tris, every corner exactly on the cell's own
    4 corners) iff every vertex's cell-local (fx, fz) snaps to {0, 1} within ``tol``. The rim
    curve blends into the interior grid via irregular (non-grid) Delaunay triangles at the
    OUTERMOST 1-2 cells of the mains footprint (verts straddling into a neighbour cell, fz
    outside [0,1]) -- those triangles' UV do not fit the discrete-row classifier (built for
    stock geometry) and must not be forced into the strip vocabulary; the retile simply leaves
    them untouched plain desert."""
    (ci, cj) = cell
    for ti in tri_list:
        for j in tris_idx[ti]:
            fx = (world_pos[j][0] - CELL_U * ci) / CELL_U
            fz = (world_pos[j][2] - CELL_U * cj) / CELL_U
            if min(abs(fx - 0.0), abs(fx - 1.0)) > tol or min(abs(fz - 0.0), abs(fz - 1.0)) > tol:
                return False
    return True


def plan_cells(bm, cell):
    """CORE (3x3, dunes mains) + INNER/OUTER ring shells (BFS distance 1/2 from CORE, restricted
    to cells the built island actually fills with REGULAR desert-mains tri, per Sec.2/4)."""
    world_pos = to_world(bm, cell)
    tris_idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    mains_cells = defaultdict(list)
    for ti, tri in enumerate(tris_idx):
        topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        if topo != 17:
            continue
        cx = sum(world_pos[j][0] for j in tri) / 3.0
        cz = sum(world_pos[j][2] for j in tri) / 3.0
        mains_cells[(math.floor(cx / CELL_U), math.floor(cz / CELL_U))].append(ti)
    regular_cells = {c for c, tl in mains_cells.items() if _cell_is_regular(c, tl, tris_idx, world_pos)}
    irregular = set(mains_cells) - regular_cells
    print(f"mains cells: {len(mains_cells)} total, {len(irregular)} irregular (rim-blended, coast-adjacent) "
          f"excluded from ring eligibility: {sorted(irregular)}")
    (ci, cj) = CORE_ORIGIN
    CORE = {(ci + di, cj + dj) for di in range(CORE_SIZE) for dj in range(CORE_SIZE)}
    gate("dunes core is fully within the built island's desert-mains footprint", CORE <= set(mains_cells),
         f"missing={sorted(CORE - set(mains_cells))}")
    gate("dunes core cells are all geometrically regular (clean 4u grid squares)", CORE <= regular_cells,
         f"irregular core cells={sorted(CORE - regular_cells)}")
    inner_theory = dilate(CORE, CORE)
    INNER = inner_theory & regular_cells
    outer_theory = dilate(inner_theory, CORE | inner_theory)
    OUTER = (outer_theory & regular_cells) - INNER
    remaining_mains = set(mains_cells) - CORE - INNER - OUTER
    touch_of = {}
    for c in INNER:
        touch_of[c] = "B-only"
    for c in OUTER:
        touches_desert = any((c[0] + di, c[1] + dj) in remaining_mains for (di, dj) in NEI4)
        touch_of[c] = "A-only" if touches_desert else "neither"
    tally = Counter(touch_of.values())
    print(f"cells: core={len(CORE)} inner={len(INNER)} outer={len(OUTER)} "
          f"(theory inner={len(inner_theory)} outer={len(outer_theory)}); touch tally {dict(tally)}")
    return dict(world_pos=world_pos, tris_idx=tris_idx, mains_cells=mains_cells, CORE=CORE,
                INNER=INNER, OUTER=OUTER, touch_of=touch_of)


def apply_retile(bm, plan):
    world_pos, tris_idx, mains_cells = plan["world_pos"], plan["tris_idx"], plan["mains_cells"]
    CORE, INNER, OUTER, touch_of = plan["CORE"], plan["INNER"], plan["OUTER"], plan["touch_of"]
    RING = INNER | OUTER
    rows = emit_strip_rows(sorted(RING), touch_of, FROZEN_TARGET_PMF, FROZEN_DELTA_P, seed=MINT_SEED)
    core_quad, core_ori = G.assign_mains(CORE, seed=MAINS_SEED)
    idall_dunes = float(X.encode_id(topograph=41))
    idall_desert = float(X.encode_id(topograph=17))
    n_core = n_inner = n_outer = 0
    for cell, tri_list in mains_cells.items():
        if cell in CORE:
            quad, ori = core_quad[cell], core_ori[cell]
            for ti in tri_list:
                for j in tris_idx[ti]:
                    wx, wz = world_pos[j][0], world_pos[j][2]
                    u, v = G.ground_uv(wx, wz, cell, quad, ori, "dunes")
                    bm.uvs[j][0], bm.uvs[j][1] = u, v
                    bm.tangents[j][0] = idall_dunes
                n_core += 1
        elif cell in INNER:
            row = rows[cell]
            for ti in tri_list:
                for j in tris_idx[ti]:
                    wx, wz = world_pos[j][0], world_pos[j][2]
                    u, v = strip_uv(wx, wz, cell, row)
                    bm.uvs[j][0], bm.uvs[j][1] = u, v
                    bm.tangents[j][0] = idall_dunes
                n_inner += 1
        elif cell in OUTER:
            row = rows[cell]
            for ti in tri_list:
                for j in tris_idx[ti]:
                    wx, wz = world_pos[j][0], world_pos[j][2]
                    u, v = strip_uv(wx, wz, cell, row)
                    bm.uvs[j][0], bm.uvs[j][1] = u, v
                    bm.tangents[j][0] = idall_desert
                n_outer += 1
    print(f"retiled: {n_core} core tris (dunes mains), {n_inner} inner-ring tris (topo41+strip), "
          f"{n_outer} outer-ring tris (topo17+strip)")
    return rows


# ============================================================================================
# once_edges / weld / frame / census gates (reused technique, dunes_patch_carry.py)
# ============================================================================================

def _kk(p):
    return (round(p[0], 3), round(p[1], 3), round(p[2], 3))


def once_edges_from_bm(bm, cell):
    world_pos = to_world(bm, cell)
    tris_idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    c = Counter()
    for tri in tris_idx:
        ks = [_kk(world_pos[j]) for j in tri]
        for i in range(3):
            e = frozenset((ks[i], ks[(i + 1) % 3]))
            if len(e) == 2:
                c[e] += 1
    return {e for e, n in c.items() if n == 1}


def run_gates(built, CELL, plane, plan, before_snapshot):
    bm = built["blocks"][CELL]
    bx, by = CELL

    # -- zero vertex motion: verts/normals byte-identical to the pre-retile snapshot -----------
    verts_ok = bm.verts == before_snapshot["verts"]
    norms_ok = bm.normals == before_snapshot["normals"]
    gate("zero vertex motion (verts byte-identical to the plain host)", verts_ok)
    gate("zero vertex motion (normals byte-identical to the plain host)", norms_ok)

    # -- retile strict zero-residual classification over the touched footprint -----------------
    touched = plan["CORE"] | plan["INNER"] | plan["OUTER"]
    tris_idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    world_pos = to_world(bm, CELL)
    tally = Counter()
    n_other = 0
    for cell, tri_list in plan["mains_cells"].items():
        if cell not in touched:
            continue
        for ti in tri_list:
            tri = tris_idx[ti]
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            uv3 = [tuple(bm.uvs[j]) for j in tri]
            tag = classify_tri(topo, uv3)
            tally[tag[0]] += 1
            if tag[0] == "other":
                n_other += 1
    gate("retile zero-residual classification (touched footprint: only mains-dunes/strip)", n_other == 0,
         f"tally={dict(tally)}")

    # -- boundary invariance + weld audit + frame bounds ----------------------------------------
    before_edges = before_snapshot["once_edges"]
    after_edges = once_edges_from_bm(bm, CELL)
    gate("boundary invariance (block once-edge set unchanged by the retile)", before_edges == after_edges,
         f"before={len(before_edges)} after={len(after_edges)}")
    pairs = M.weld_audit([bm])
    gate("weld audit (0 near-miss vertex pairs)", not pairs, f"{len(pairs)} pairs")
    lx = [v[0] for v in bm.verts]
    lz = [v[2] for v in bm.verts]
    frame_ok = -0.06 <= min(lx) and max(lx) <= 64.06 and -64.06 <= min(lz) and max(lz) <= 0.06
    gate("frame-bounds (local verts sit inside the block frame)", frame_ok,
         f"x[{min(lx):.2f},{max(lx):.2f}] z[{min(lz):.2f},{max(lz):.2f}]")

    # -- IDALL_SKIP: structurally unreachable (area always 0) -----------------------------------
    skip_hit = any(int(round(bm.tangents[j][0])) in P.IDALL_SKIP for j in range(bm.vcount))
    gate("IDALL_SKIP collision (structurally impossible, area always 0)", not skip_hit)

    # -- engine placement census: MISS regression + MISS==0 --------------------------------------
    hid = lambda nm: M.hidden_block_mesh(name=nm, disc=1, x=bx, y=by)  # noqa: E731
    meshlist_after = [("Object", hid("Object")), ("Terrain", bm), ("Sea1", hid("Sea1")), ("Sea2", hid("Sea2")),
                       ("Sea3", hid("Sea3")), ("Sea4", plane), ("Sea5", hid("Sea5"))]
    meshlist_before = [("Object", hid("Object")), ("Terrain", before_snapshot["bm_plain"]),
                        ("Sea1", hid("Sea1")), ("Sea2", hid("Sea2")), ("Sea3", hid("Sea3")),
                        ("Sea4", plane), ("Sea5", hid("Sea5"))]
    cen_before = P.census(meshlist_before, samples=24)
    cen_after = P.census(meshlist_after, samples=24)
    miss_regression = set(map(tuple, cen_after["miss"])) == set(map(tuple, cen_before["miss"]))
    gate("placement census MISS regression (identical to the plain host)", miss_regression,
         f"after={len(cen_after['miss'])} before={len(cen_before['miss'])}")
    gate("placement census MISS==0 (post-retile)", len(cen_after["miss"]) == 0, f"miss={cen_after['miss'][:5]}")

    # -- THE SAVE-BRICK PROBE: actually ground-query candidate spawn points, don't just assert --
    cx, cz = CENTER
    lx0, lz0 = cx - BLOCK * bx, cz + BLOCK * (by + 1) - BLOCK
    gy0, nm0, idall0, topo0 = P.place(meshlist_after, lx0, lz0, sky=True)
    block_centre_ok = nm0 == "Terrain" and topo0 in (17, 41)
    gate(f"save-brick probe: block centre ({cx:.0f},{cz:.0f}) grounds walkable", block_centre_ok,
         f"y={gy0:.2f} mesh={nm0} topo={topo0}")
    px, pz = 662.0, -1250.0                                        # the dunes core's own world centre
    plx, plz = px - BLOCK * bx, pz + BLOCK * (by + 1) - BLOCK
    gy1, nm1, idall1, topo1 = P.place(meshlist_after, plx, plz, sky=True)
    core_centre_ok = nm1 == "Terrain" and topo1 == 41
    gate("save-brick probe: dunes-core centre (662,-1250) grounds on walkable dunes (topo 41)", core_centre_ok,
         f"y={gy1:.2f} mesh={nm1} topo={topo1}")
    # a handful of ring-cell centres too (inner + outer), not just the two named points
    ring_ok = True
    ring_samples = []
    for cell in sorted(list(plan["INNER"])[:2] + list(plan["OUTER"])[:2]):
        rx, rz = CELL_U * cell[0] + CELL_U / 2, CELL_U * cell[1] + CELL_U / 2
        rlx, rlz = rx - BLOCK * bx, rz + BLOCK * (by + 1) - BLOCK
        gy, nm, idall, topo = P.place(meshlist_after, rlx, rlz, sky=True)
        ok = nm == "Terrain" and topo in (17, 41)
        ring_ok = ring_ok and ok
        ring_samples.append((cell, nm, topo, ok))
    gate("save-brick probe: sampled ring-cell centres ground walkable", ring_ok, f"{ring_samples}")

    return dict(tally=dict(tally), cen_after=len(cen_after["miss"]), cen_before=len(cen_before["miss"]))


# ============================================================================================
# THE OFFLINE EYE -- calibrated (stock-vs-stock controls in the same sheet, LAW: CALIBRATE THE
# INSTRUMENT BEFORE YOU JUDGE WITH IT)
# ============================================================================================

LDIR = (-0.45, 0.72, 0.45)
_l = math.sqrt(sum(q * q for q in LDIR))
LDIR = tuple(q / _l for q in LDIR)
ROW_COLOR = {0: (230, 60, 60), 1: (240, 170, 40), 2: (70, 190, 90), 3: (70, 130, 240)}


def _atlas():
    GP = Path(_cfg.find_game_path(None))
    MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / "textures" / "res(1_24)_terrain.png"
    atlas = Image.open(MOG).convert("RGBA")
    return atlas, atlas.size, atlas.load()


def synth_tris(bm, cell):
    bx, by = cell
    V, N, U, TAN = bm.verts, bm.normals, bm.uvs, bm.tangents
    out = []
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        p3 = [(V[j][0] + BLOCK * bx, V[j][1], V[j][2] - BLOCK * by) for j in tri]
        uv3 = [tuple(U[j][:2]) for j in tri]
        n3 = [tuple(N[j][:3]) for j in tri]
        topo = X.decode_id(int(round(TAN[tri[0]][0])))["topograph"]
        out.append((p3, uv3, n3, topo))
    return out


def stock_tris(bx, by):
    bm = X.read_block(bx, by, disc=1, part="terrain")
    return synth_tris(bm, (bx, by))


def paint(tris, cx, cz, win_x, win_z, sc, *, atlas_wh, atlas_px, rowmap=False):
    AW, AH = atlas_wh

    def at_b(u_, v_):
        fx = (u_ % 1.0) * AW - 0.5
        fy = (1.0 - v_ % 1.0) * AH - 0.5
        x0, y0 = int(math.floor(fx)), int(math.floor(fy))
        tx, ty = fx - x0, fy - y0
        acc = [0.0, 0.0, 0.0]
        aa = 0.0
        for (dx, dy, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                             (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
            px_, py_ = min(max(x0 + dx, 0), AW - 1), min(max(y0 + dy, 0), AH - 1)
            r, g, b, a = atlas_px[px_, py_]
            acc[0] += r * wg; acc[1] += g * wg; acc[2] += b * wg; aa += a * wg
        return aa, (acc[0], acc[1], acc[2])

    x0, x1 = cx - win_x / 2, cx + win_x / 2
    z0, z1 = cz - win_z / 2, cz + win_z / 2
    RW, RH = int(win_x * sc), int(win_z * sc)
    tex = Image.new("RGB", (RW, RH), (120, 150, 200))
    com = Image.new("RGB", (RW, RH), (120, 150, 200))
    tp, cp = tex.load(), com.load()
    plotted = []
    for (p3, uv3, n3, topo) in tris:
        if max(p[0] for p in p3) < x0 or min(p[0] for p in p3) > x1:
            continue
        if max(p[2] for p in p3) < z0 or min(p[2] for p in p3) > z1:
            continue
        srow = classify_strip(uv3) if topo in (17, 41) else None
        plotted.append((max(p[1] for p in p3), p3, uv3, n3, srow))
    for _, p3, q3, n3, srow in sorted(plotted, key=lambda t: t[0]):
        sx = [(p[0] - x0) * sc for p in p3]
        sy = [(z1 - p[2]) * sc for p in p3]
        bx0, bx1 = int(min(sx)), int(max(sx)) + 1
        by0, by1 = int(min(sy)), int(max(sy)) + 1
        d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(d) < 1e-9:
            continue
        flat_rgb = ROW_COLOR.get(srow, (70, 70, 70)) if rowmap else None
        for pxx in range(max(0, bx0), min(RW, bx1)):
            for pyy in range(max(0, by0), min(RH, by1)):
                w0 = ((sy[1] - sy[2]) * (pxx - sx[2]) + (sx[2] - sx[1]) * (pyy - sy[2])) / d
                w1 = ((sy[2] - sy[0]) * (pxx - sx[2]) + (sx[0] - sx[2]) * (pyy - sy[2])) / d
                w2 = 1 - w0 - w1
                if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                    continue
                if flat_rgb is not None:
                    rgb, aa = flat_rgb, 255
                else:
                    aa, rgb = at_b(w0 * q3[0][0] + w1 * q3[1][0] + w2 * q3[2][0],
                                   w0 * q3[0][1] + w1 * q3[1][1] + w2 * q3[2][1])
                    if aa < 24:
                        continue
                nx = sum(w * n3[k][0] for k, w in enumerate((w0, w1, w2)))
                ny = sum(w * n3[k][1] for k, w in enumerate((w0, w1, w2)))
                nz = sum(w * n3[k][2] for k, w in enumerate((w0, w1, w2)))
                nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                f = 0.45 + 0.55 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
                tp[pxx, pyy] = tuple(min(255, int(c)) for c in rgb)
                cp[pxx, pyy] = tuple(min(255, int(c * f)) for c in rgb)
    return tex, com


def sheet(panels, cols, cell_w, cell_h, label_h=22, path=None, title=""):
    rows = (len(panels) + cols - 1) // cols
    pad = 10
    W = cols * (cell_w + pad) + pad
    H = rows * (cell_h + label_h + pad) + pad + (24 if title else 0)
    im = Image.new("RGB", (W, H), (16, 16, 16))
    dr = ImageDraw.Draw(im)
    if title:
        dr.text((pad, 6), title, fill=(255, 230, 140))
    for i, (label, panel) in enumerate(panels):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = pad + (24 if title else 0) + r * (cell_h + label_h + pad)
        dr.text((x, y), label, fill=(230, 230, 230))
        pw, ph = panel.size
        scale = min(cell_w / pw, cell_h / ph)
        rp = panel.resize((max(1, int(pw * scale)), max(1, int(ph * scale))), Image.NEAREST)
        im.paste(rp, (x, y + label_h))
    if path:
        im.save(path)
        print(f"-> {path}")
    return im


def row_mean_luminance(atlas_wh, atlas_px):
    """A row's mean atlas luminance -- the jumpiness metric's per-row value, reused from the
    v2 calibration technique (mean |delta mean-luminance| between lattice-adjacent strip cells)."""
    AW, AH = atlas_wh
    out = {}
    for row in range(4):
        u0, u1 = G.STRIP_U[0] + _DU, G.STRIP_U[1] + _DU
        v0, v1 = G.STRIPS_V[row][0] + _DV, G.STRIPS_V[row][1] + _DV
        acc = n = 0.0
        for i in range(8):
            for j in range(8):
                u = u0 + (u1 - u0) * (i + 0.5) / 8
                v = v0 + (v1 - v0) * (j + 0.5) / 8
                px = min(max(int((u % 1.0) * AW), 0), AW - 1)
                py = min(max(int((1.0 - v % 1.0) * AH), 0), AH - 1)
                r, g, b, a = atlas_px[px, py]
                acc += 0.2126 * r + 0.7152 * g + 0.0722 * b
                n += 1
        out[row] = acc / n
    return out


def offline_eye(built, CELL, plan, rows, live_ns):
    atlas, atlas_wh, atlas_px = _atlas()
    bm = built["blocks"][CELL]
    synth = synth_tris(bm, CELL)

    # ---- jumpiness, calibrated against the transplant-null band (3.83-5.85) ------------------
    lum = row_mean_luminance(atlas_wh, atlas_px)
    RING = plan["INNER"] | plan["OUTER"]
    diffs = []
    for c in RING:
        for (di, dj) in ((1, 0), (0, 1)):
            nb = (c[0] + di, c[1] + dj)
            if nb in RING:
                diffs.append(abs(lum[rows[c]] - lum[rows[nb]]))
    jump = (sum(diffs) / len(diffs)) if diffs else 0.0
    band_ok = 3.83 <= jump <= 5.85
    gate("offline-eye jumpiness (informational -- inside the measured transplant-null band 3.83-5.85)",
         band_ok, f"jumpiness={jump:.3f} n_pairs={len(diffs)} row_luminance={ {k: round(v,1) for k,v in lum.items()} }")

    # ---- render: tight zoom on the minted seam + 2 real stock calibration windows ------------
    px, pz = 662.0, -1250.0
    STOCK_A, STOCK_B = (18, 3), (13, 12)
    cellinfo = live_ns["cellinfo"]
    strip_cells = live_ns["strip_cells"]

    def stock_centre(bxby):
        cs = [c for c in strip_cells if cellinfo[c]["block"] == bxby]
        if not cs:
            return (bxby[0] * 64 + 32, -(bxby[1] * 64 + 32))
        return ((sum(c[0] for c in cs) / len(cs) + 0.5) * 4.0, (sum(c[1] for c in cs) / len(cs) + 0.5) * 4.0)

    acx, acz = stock_centre(STOCK_A)
    bcx, bcz = stock_centre(STOCK_B)
    a_tris = stock_tris(*STOCK_A) + stock_tris(STOCK_A[0] - 1, STOCK_A[1]) + stock_tris(STOCK_A[0] + 1, STOCK_A[1]) \
        + stock_tris(STOCK_A[0], STOCK_A[1] - 1) + stock_tris(STOCK_A[0], STOCK_A[1] + 1)
    b_tris = stock_tris(*STOCK_B) + stock_tris(STOCK_B[0] - 1, STOCK_B[1]) + stock_tris(STOCK_B[0] + 1, STOCK_B[1]) \
        + stock_tris(STOCK_B[0], STOCK_B[1] - 1) + stock_tris(STOCK_B[0], STOCK_B[1] + 1)

    tight_panels = []
    for label, tris, cx, cz in (("SYNTH minted seam (10,19)", synth, px, pz),
                                 (f"STOCK {STOCK_A} (smooth-organic ref)", a_tris, acx, acz),
                                 (f"STOCK {STOCK_B} (boxy ref)", b_tris, bcx, bcz)):
        tex, com = paint(tris, cx, cz, 24, 24, 32, atlas_wh=atlas_wh, atlas_px=atlas_px)
        _, rowim = paint(tris, cx, cz, 24, 24, 32, atlas_wh=atlas_wh, atlas_px=atlas_px, rowmap=True)
        tight_panels.append((f"{label} -- UNSHADED", tex))
        tight_panels.append((f"{label} -- ROW MAP", rowim))
    sheet(tight_panels, cols=2, cell_w=640, cell_h=640, path=OUTD / "dunes_patch_mint_tight.png",
          title="TIGHT ZOOM (24x24u, sc=32) -- SYNTH minted seam vs 2 REAL stock desert|dunes windows (calibration)")

    medium_panels = []
    for label, tris, cx, cz, win in (("SYNTH whole patch", synth, px, pz, 48),
                                      (f"STOCK {STOCK_A}", a_tris, acx, acz, 48),
                                      (f"STOCK {STOCK_B}", b_tris, bcx, bcz, 48)):
        tex, com = paint(tris, cx, cz, win, win, 10, atlas_wh=atlas_wh, atlas_px=atlas_px)
        medium_panels.append((f"{label} -- TEXTURE", tex))
        medium_panels.append((f"{label} -- SHADED (gameplay-scale)", com))
    sheet(medium_panels, cols=2, cell_w=560, cell_h=560, path=OUTD / "dunes_patch_mint_medium.png",
          title="MEDIUM/GAMEPLAY-SCALE (48x48u, sc=10) -- SYNTH whole patch vs 2 REAL stock windows")

    return dict(jumpiness=jump, jumpiness_in_band=band_ok, row_luminance=lum)


# ============================================================================================
# THE --deploy PATH -- implemented per the brief, NEVER invoked by this harness run
# ============================================================================================

def would_write_list():
    """The exact Disc1 + auto-mirrored Disc4 file list a --deploy would write (design Sec.6.5-6.6),
    printed in dry mode without touching the filesystem (path construction only)."""
    game_root = _cfg.find_game_path(None)
    (bx, by) = 10, 19
    parts = ("Terrain", "Sea4", "Object", "Sea1", "Sea2", "Sea3", "Sea5", "Beach1")
    disc1 = [str(game_root / MOD / M.override_relpath(1, bx, by, part=p)) for p in parts]
    disc1.append(str(game_root / MOD / M.donor_sidecar_relpath(1, bx, by)))
    disc4 = [p.replace("Disc1", "Disc4") for p in disc1]
    return disc1, disc4


def deploy_patch(built, CELL, plane):                          # pragma: no cover -- never invoked this run
    """The real deploy: build_landmass's own per-block write loop (island.landmass, Sec 802-881),
    reused by hand since landmass() itself would deploy the UN-retiled mesh -- our retile happens
    on built["blocks"][CELL] BEFORE any write. Calls discmirror.auto_mirror itself on every path
    it wrote (closing the auto-mirror bypass gap the scrub carry script has)."""
    bx, by = CELL
    bm = built["blocks"][CELL]
    written = []
    written.append(M.deploy_override(bm, mod_folder=MOD, part="Terrain"))
    sea = dataclasses.replace(plane, x=bx, y=by, name=f"Block[{bx}][{by}] Sea4")
    written.append(M.deploy_override(sea, mod_folder=MOD, part="Sea4"))
    for part in I.HIDDEN_PARTS:
        written.append(M.deploy_override(M.hidden_block_mesh(name=f"Block[{bx}][{by}] {part}", disc=1, x=bx, y=by),
                                         mod_folder=MOD, part=part))
    written.append(M.deploy_donor_sidecar(I.DEFAULT_DONOR[0], I.DEFAULT_DONOR[1], mod_folder=MOD, disc=1, x=bx, y=by))
    DM.auto_mirror(written, mod_folder=MOD)
    return written


# ============================================================================================
# CLI smoke test -- the design doc's own recommended CLI line, --dry-run (writes nothing)
# ============================================================================================

def cli_smoke_test():
    kit_root = HERE.resolve().parents[1] / "ff9mapkit"
    cmd = [sys.executable, "-m", "ff9mapkit", "world-island", "--ground", "desert",
           "--mod-folder", MOD, "--center", "672,-1248", "--radius", "26", "--seed", "2", "--dry-run"]
    print(f"CLI smoke test (from {kit_root}): {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, cwd=str(kit_root), capture_output=True, text=True, timeout=180)
        ok = r.returncode == 0 and "all gates CLEAN" in r.stdout
        gate("CLI smoke test (world-island --dry-run, the design's recommended host command, writes nothing)",
             ok, f"returncode={r.returncode} stdout_tail={r.stdout[-300:]!r} stderr_tail={r.stderr[-300:]!r}")
        return dict(returncode=r.returncode, stdout=r.stdout, stderr=r.stderr)
    except Exception as e:                                     # noqa: BLE001
        gate("CLI smoke test (world-island --dry-run)", False, f"exception: {e}")
        return dict(error=str(e))


# ============================================================================================
# main
# ============================================================================================

def main():
    print(f"=== dunes_patch_mint.py -- MOD={MOD} CENTER={CENTER} RADIUS={RADIUS} SEED={SEED} "
          f"GROUND={GROUND} MINT_SEED(row emitter)={MINT_SEED} ===\n")

    print("--- frozen-constant live re-verification ---")
    live_ns = _live_reverify()

    print("\n--- STEP 1: build the plain desert host in memory (no writes) ---")
    built, CELL, plane, base_report = build_host()

    print("\n--- STEP 2: plan the core/ring cell-set ---")
    plan = plan_cells(built["blocks"][CELL], CELL)

    # snapshot BEFORE the retile (position-only + a plain copy for the census/edge regressions)
    bm = built["blocks"][CELL]
    before_snapshot = dict(
        verts=copy.deepcopy(bm.verts), normals=copy.deepcopy(bm.normals),
        once_edges=once_edges_from_bm(bm, CELL),
        bm_plain=dataclasses.replace(bm, chan_arrays={k: copy.deepcopy(v) for k, v in bm.chan_arrays.items()}),
    )

    print("\n--- STEP 3: apply the retile (uv + tangent.x only) ---")
    rows = apply_retile(bm, plan)

    print("\n--- STEP 4: the gate list ---")
    gate_summary = run_gates(built, CELL, plane, plan, before_snapshot)

    print("\n--- STEP 5: the offline eye (calibrated) ---")
    eye = offline_eye(built, CELL, plan, rows, live_ns)

    print("\n--- STEP 6: the --deploy path (dry mode only -- would-write list) ---")
    disc1, disc4 = would_write_list()
    print("would write (Disc1):")
    for p in disc1:
        print(f"   {p}")
    print("would write (Disc4, auto-mirrored):")
    for p in disc4:
        print(f"   {p}")

    print("\n--- STEP 7: CLI smoke test ---")
    cli_result = cli_smoke_test()

    n_fail = sum(1 for _, ok, _ in GATES if not ok)
    print(f"\n=== {len(GATES)} gates run, {n_fail} FAILED ===")

    out = dict(
        mod_folder=MOD, center=list(CENTER), radius=RADIUS, seed=SEED, ground=GROUND,
        core_origin=list(CORE_ORIGIN), core_size=CORE_SIZE, mint_seed=MINT_SEED, mains_seed=MAINS_SEED,
        cell=list(CELL),
        core_cells=[list(c) for c in sorted(plan["CORE"])],
        inner_ring_cells=[list(c) for c in sorted(plan["INNER"])],
        outer_ring_cells=[list(c) for c in sorted(plan["OUTER"])],
        touch_of={f"{c[0]},{c[1]}": v for c, v in plan["touch_of"].items()},
        row_assignment={f"{c[0]},{c[1]}": r for c, r in rows.items()},
        gates=[{"name": n, "ok": ok, "detail": d} for n, ok, d in GATES],
        n_gates=len(GATES), n_failed=n_fail,
        gate_summary=gate_summary, offline_eye=eye,
        would_write_disc1=disc1, would_write_disc4=disc4,
        cli_smoke=dict(returncode=cli_result.get("returncode"), ok="all gates CLEAN" in cli_result.get("stdout", "")),
        outputs=[str(p) for p in sorted(OUTD.glob("dunes_patch_mint_*.png"))],
    )
    (OUTD / "dunes_patch_mint.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n-> {OUTD / 'dunes_patch_mint.json'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
