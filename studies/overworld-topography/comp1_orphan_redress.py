"""THE COMP[1] ORPHAN-DECAL REDRESS -- the fix pass for Round 10 of GROUND-FAMILY-DECODE-2026-07-19.md
(2026-07-22). Read Round 10 first ("THE DESERT|GRASS COMBINING LANGUAGE") -- it is this script's
contract.

THE CONTRACT (Round 10, verbatim summary)
  Round 10 decoded the desert|grass combining language as a CLOSED, 3-rect vocabulary:
  GROUNDS['grass'] mains / GROUNDS['desert'] mains / STRIPS[('grass','desert')]'s 4 fringe-decal
  rows -- grass's own FAM_REGION['B'] transition strip, translated by (du,dv)=(0.52442,-0.04687),
  confirmed byte-exact against grassland.py on both TRAIN and TEST blocks. Re-running the deployed
  comp[1] carry (the 9-block MINT_BLOCKS region (18-20,17-19), 1549 tris, ZERO grass tri anywhere)
  through the decoded vocabulary found exactly 7 ground tris score green_frac > 0, and ALL 7
  classify as STRIPS(grass,desert): 5 at row2 -- desert-side pure fringe -- (cells (307,-302),
  (304,-297), (312,-306), (313,-305), (320,-294)) and 2 at row1 -- a straddle-cell shared decal --
  (cells (317,-292), (320,-300)). Every one of the 7 is REAL, verbatim, byte-exact stock content:
  reverse-mapping each cell through the carry's own translation recovers a donor cell that
  genuinely borders grass in stock (Laws 2/3 hold at the donor). But at the DEPLOYED site there is
  no grass tri anywhere in the whole region -- the carry brought only the desert/dunes footprint --
  so per Laws 2/3/6 (which all require a genuine opposite-family neighbour for this decal to occur),
  a lawful isolated desert cell here renders plain GROUNDS['desert'] mains, not the fringe decal.
  RULING: all 7 = DEFECT (contextual/topological -- an orphaned decal relocated out of the context
  that explains it -- not a fabricated asset). The rock/mesa green (topo 49/58, a THIRD,
  uncatalogued texture axis, u~[0.716,0.776] v~[0.239,0.363]) is explicitly OUT OF SCOPE for this
  redress -- it stays exactly as-is (23 tris sample any green, unchanged by this pass).

THE REDRESS (this script) -- matches the arc's own FIX-G precedent (dunes_true_carry.redress_green_
  tri, the in-game-proven mechanism): UV + topo ONLY, zero geometry. Each of the 7 tris' 3 corners
  is re-pointed to lawful GROUNDS['desert'] mains via GL.assign_mains({cell}, seed=0xF93) ->
  GL.ground_uv(x, z, cell, quad, ori, 'desert') (the SAME per-cell call the shipped GroundRetile
  'recovered' path uses); topo re-encodes 16 -> GROUNDS['desert']['topo'] (17); event/area/flags are
  read off the tri's OWN existing idall and carried through UNCHANGED (all 7 tris share one idall,
  3136 = event0/area12/topo16/flags0, blanket-safe to re-encode to 3140). Vertex POSITIONS,
  NORMALS, and tangent[1:] (y/z/w) are never touched, and no other triangle in the mod is touched --
  the exact shape of fix as Round 7/8's FIX-G de-green pass.

Target tris are RE-DERIVED every run from the CURRENT deployed bytes + the Round-10 cell list read
straight from out/grass_desert_combine_decode.json -- never hardcoded tri indices (which could
drift under a re-deploy). For each of the (at most 3) blocks the 7 defect cells fall in, the script
loads the live Terrain.ff9mesh override, finds -- per cell -- the ONE tri (of the cell's 2, the
walkmesh's own diagonal split) whose topo is still 16 (its quad-partner is already topo 17, the
untouched legitimate plain-desert tile -- same_cell_straddle=false on all 7, re-verified here
against live bytes, not merely trusted from the dump), and reconciles its OLD uv against the dump's
stored uv byte-exact (float tol) before accepting it as the target.

SCOPE (recon finding, gated in-script): the prompt's 5 "carried blocks" ((18,18)/(19,17)/(19,18)/
(19,19)/(20,18)) is the carry's whole footprint, not the defect set. Only 3 of them actually hold a
target cell -- (19,18) x3, (19,19) x2, (20,18) x2. Blocks (18,18) and (19,17) hold NONE of the 7 and
are NEVER opened for writing; a gate refuses to run if the located block set is anything but exactly
those 3.

Files touched (Disc1, live bytes; Disc4 mirrored by discmirror.auto_mirror, --apply only):
  FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1/r18/Block[19][18] Terrain.ff9mesh
  FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1/r19/Block[19][19] Terrain.ff9mesh
  FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1/r18/Block[20][18] Terrain.ff9mesh

THE RE-CLASSIFY REGION (measured, not assumed): the doc's prose says "13 deployed blocks touching
comp[1]"; this script measured it directly -- MINT_BLOCKS, the 9-block (18-20,17-19) square, loads
EXACTLY 1549 tris with the EXACT topo census {58:232, 17:793, 16:144, 41:279, 59:39, 49:62} the dump
itself reports for its "13-block" region, byte-for-byte. That 9-block square IS the region the dump
censused (the "13" in the prose does not reconcile against any block set this script could find);
this script always re-classifies over MINT_BLOCKS and says so plainly in its report.

Run (DRY-RUN, default -- reads only, touches nothing):
  py studies/overworld-topography/comp1_orphan_redress.py
APPLY (backs up first, refuses on backup failure, writes + mirrors + post-checks):
  py studies/overworld-topography/comp1_orphan_redress.py --apply
REVERT a prior --apply from its backup dir (name under backups/, or a full path):
  py studies/overworld-topography/comp1_orphan_redress.py --revert comp1-redress.20260722-140501
Artifact -> out/comp1_orphan_redress.json

ROUND 2 (2026-07-22, same day) -- THE DESERT|DUNES PAIR'S OWN ORPHAN-DECAL CLASS
  The in-game playtest of the Round-1 apply reported a residual "mismatched transition tile" at
  world (1214,-1162) -- cell (303,-291), block (18,18). That block is OUTSIDE Round 1's own scope
  (Round 1's own gate refuses to open it -- it holds none of the 7 grass|desert defects). Round 10
  only ever decoded/scoped the grass|desert pair; this cell's defect is on the OTHER pair sharing
  comp[1]'s footprint, `STRIPS[('desert','dunes')]` (already in ``grassland.py``, unrelated to
  Round 10's own decode work). The class rule (never a hardcoded cell list -- re-derived from LIVE
  bytes every run via the same generative strip decoder ``dunes_grazing_eye._classify_tri`` uses):
  a desert|dunes STRIP decal whose row is one of the "straddle-cell shared decal" rows {1,3} is only
  legitimate on a cell that is ITSELF split between the two families (one tri desert, one dunes) --
  wearing it on a pure-family cell is a structural mismatch, independent of proximity. A decal in the
  single-family "pure fringe" rows {0,2} is legitimate only if a genuine dunes tile sits within the
  modal ~1-2 cell dressing band (Law 4); otherwise it is the Round-10-style orphaned-fringe defect,
  same rule, different pair. The census (9-block comp[1] core + a 1-block read-only ring) finds
  exactly ONE such cell: (303,-291), wearing STRIPS(desert,dunes) row1 ori0 on BOTH of its 2 tris
  (each sampling half the rect -- the same diagonal-blend signature a genuine straddle uses) despite
  both tris already being topo17/idall68 (byte-identical to an ordinary plain-desert-mains
  neighbour) -- i.e. topo/idall were NEVER mis-encoded here (unlike Round 1's topo16 cells); this is
  a PURE UV defect. The redress is UV-only, the same ``assign_mains(seed=0xF93)`` -> ``ground_uv(...,
  'desert')`` call Round 1 uses, applied to both of the cell's tris (so the cell renders as one
  ordinary plain-desert quad, split by its own walkmesh diagonal, exactly like its neighbours).
"""
from __future__ import annotations

import argparse
import copy
import glob as _glob_mod
import itertools
import json
import math
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                          # noqa: E402
from ff9mapkit.world import discmirror as DM                  # noqa: E402
from ff9mapkit.world import extract as X                       # noqa: E402
from ff9mapkit.world import grassland as GL                    # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402

import dunes_grazing_eye as GE                                 # noqa: E402  (tri_green_frac + _tris_of)

BLOCK = 64.0
CELL = 4.0
MOD = "FF9CustomMap-world"
DUMP_PATH = HERE / "out" / "grass_desert_combine_decode.json"
OUT = HERE / "out" / "comp1_orphan_redress.json"
BACKUP_ROOT = REPO_ROOT / "backups"

# the comp[1] re-classify region: MEASURED to reproduce the dump's n_total_tris=1549 + topo census
# byte-exact (see docstring) -- NOT the doc prose's "13 deployed blocks" figure, which this script
# could not reconcile against any real block set.
MINT_BLOCKS = [(bx, by) for bx in range(18, 21) for by in range(17, 20)]

GROUND_TOPOS = frozenset({0, 16, 17, 19, 20})    # grass + the desert family -- flat ground only
ROCK_TOPOS = frozenset({49, 58})                 # the separate, out-of-scope mesa/rock texture axis
REDRESS_SEED = 0xF93                             # the FIX-G precedent's own seed (dunes_true_carry.py)
UV_TOL = 2e-4                                    # float32-precision UV reconciliation tolerance
REGION_TOL = 0.005                               # slack allowed when gating "new UV inside desert mains"

GATES: list = []


def gate(name: str, ok: bool, detail: str = "") -> bool:
    GATES.append((name, bool(ok), detail))
    print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return bool(ok)


# ================================================================================================
# the Round-10 dump -> target cells
# ================================================================================================
def load_targets() -> dict:
    data = json.loads(DUMP_PATH.read_text())["comp1"]["results"]
    targets = {}
    for r in data:
        cell = tuple(r["cell"])
        targets[cell] = dict(topo=r["topo"], kind=r["kind"], detail=r["detail"],
                             green_frac=r["green_frac"], uv=[list(p) for p in r["uv"]],
                             reason=r.get("reason", ""))
    return targets


def cell_to_block(cell) -> tuple:
    """The block owning cell (ci,cj), by its world centre (extract's canonical frame: world =
    local + block_world_origin, i.e. bx=floor(wx/64), by=floor(-wz/64))."""
    wx = CELL * cell[0] + CELL / 2.0
    wz = CELL * cell[1] + CELL / 2.0
    return (int(math.floor(wx / BLOCK)), int(math.floor(-wz / BLOCK)))


def _uv_sets_match(a, b, tol=UV_TOL) -> bool:
    """Unordered corner match (the tri's vertex order in the live mesh need not match the dump's
    stored order) within float32 tolerance."""
    for perm in itertools.permutations(range(3)):
        if all(abs(a[i][0] - b[perm[i]][0]) < tol and abs(a[i][1] - b[perm[i]][1]) < tol
               for i in range(3)):
            return True
    return False


def _same_event_area_flags(old_idall: int, new_idall: int) -> bool:
    do, dn = X.decode_id(old_idall), X.decode_id(new_idall)
    return do["event"] == dn["event"] and do["area"] == dn["area"] and do["flags"] == dn["flags"]


# ================================================================================================
# locate the 7 target tris from LIVE deployed bytes (never hardcoded indices)
# ================================================================================================
def locate_tris(game_root: Path, targets: dict):
    """For every block a target cell falls in, load the live Terrain.ff9mesh override and find --
    per cell -- the ONE topo-16 tri (its quad-partner already topo 17). Returns
    (blocks, bms, plan, straddle_problems)."""
    blocks = sorted({cell_to_block(c) for c in targets})
    bms = {}
    cell_hits = defaultdict(list)
    for (bx, by) in blocks:
        rel = M.override_relpath(1, bx, by, part="Terrain")
        path = game_root / MOD / rel
        if not path.exists():
            raise FileNotFoundError(f"expected deployed override missing: {path}")
        bm = M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, part="terrain")
        bms[(bx, by)] = bm
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            wx = [bm.verts[j][0] + ox for j in tri]
            wz = [bm.verts[j][2] + oz for j in tri]
            cx, cz = sum(wx) / 3.0, sum(wz) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            if cell not in targets:
                continue
            topos = [X.decode_id(int(round(bm.tangents[j][0])))["topograph"] for j in tri]
            cell_hits[cell].append(dict(block=(bx, by), tri_idx=list(tri), topos=topos,
                                        uv=[list(bm.uvs[j]) for j in tri]))

    plan = []
    straddle_problems = []
    for cell, hits in cell_hits.items():
        n16 = [h for h in hits if all(t == 16 for t in h["topos"])]
        if len(hits) != 2 or len(n16) != 1:
            straddle_problems.append(dict(cell=list(cell), n_hits=len(hits), n_topo16=len(n16)))
            continue
        h = n16[0]
        rec = targets[cell]
        idalls = [int(round(bms[h["block"]].tangents[j][0])) for j in h["tri_idx"]]
        plan.append(dict(block=list(h["block"]), cell=list(cell), row=rec["detail"],
                         dump_green_frac=rec["green_frac"], dump_reason=rec["reason"],
                         tri_local_idx=h["tri_idx"], old_uv=h["uv"], old_idall=idalls,
                         dump_uv_match=_uv_sets_match(h["uv"], rec["uv"])))
    return blocks, bms, plan, straddle_problems


# ================================================================================================
# compute the redress (UV + topo only) for one located tri
# ================================================================================================
def compute_redress(bm, ox: float, oz: float, cell: tuple, tri_idx: list):
    cq, co = GL.assign_mains({cell}, seed=REDRESS_SEED)
    quad, ori = cq[cell], co[cell]
    new_uv, new_idall = [], []
    for j in tri_idx:
        wx = bm.verts[j][0] + ox
        wz = bm.verts[j][2] + oz
        new_uv.append(list(GL.ground_uv(wx, wz, cell, quad, ori, "desert")))
        d = X.decode_id(int(round(bm.tangents[j][0])))
        new_idall.append(X.encode_id(d["event"], d["area"], GL.GROUNDS["desert"]["topo"], d["flags"]))
    return quad, ori, new_uv, new_idall


# ================================================================================================
# the Round-10 classifier, re-run over MINT_BLOCKS (measured region -- see module docstring)
# ================================================================================================
def reclassify_region(game_root: Path, override_bms: dict | None = None):
    """override_bms: {(bx,by): BlockMesh} substituted in for blocks it covers (the in-memory,
    pre-write check); every other MINT_BLOCKS block reads its CURRENT bytes off disk. Returns
    (n_green_ground, green_ground_cells, n_rock_green) using the calibrated tri_green_frac(nsub=10)
    threshold (>0.0 -- the Round-10 dump's own threshold; the 0.05/0.20 bars older FIX-G passes used
    are too coarse for these ~0.015-0.030 fractions, which is exactly why they survived unfixed
    through rounds 7-9)."""
    override_bms = override_bms or {}
    all_tris = []
    for (bx, by) in MINT_BLOCKS:
        blk = (bx, by)
        if blk in override_bms:
            bm = override_bms[blk]
        else:
            path = game_root / MOD / M.override_relpath(1, bx, by, part="Terrain")
            if not path.exists():
                continue
            bm = M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, part="terrain")
        all_tris += GE._tris_of(bm, bx, by)
    n_green_ground = 0
    green_cells = []
    n_rock_green = 0
    for (p3, uv3, n3, topo, fam) in all_tris:
        if topo in GROUND_TOPOS:
            if GE.tri_green_frac(uv3, nsub=10) > 0.0:
                n_green_ground += 1
                cx = sum(p[0] for p in p3) / 3.0
                cz = sum(p[2] for p in p3) / 3.0
                green_cells.append([math.floor(cx / CELL), math.floor(cz / CELL)])
        elif topo in ROCK_TOPOS:
            if GE.tri_green_frac(uv3, nsub=10) > 0.0:
                n_rock_green += 1
    return n_green_ground, green_cells, n_rock_green


# ================================================================================================
# BUILD + GATE (dry-run always; --apply reuses this, then writes)
# ================================================================================================
def build_and_gate(game_root: Path):
    GATES.clear()
    print("=== comp1_orphan_redress.build_and_gate -- THE ORPHAN-DECAL REDRESS (Round 10) ===\n")

    targets = load_targets()
    gate("Round-10 dump has exactly 7 defect cells", len(targets) == 7, f"cells={sorted(targets)}")

    blocks, bms, plan, straddle_problems = locate_tris(game_root, targets)
    gate("every target cell holds exactly 2 tris (the walkmesh's own diagonal split) with exactly 1 "
         "at topo 16 (the other legitimately topo 17 already) -- re-verified against LIVE bytes, "
         "not merely trusted from the dump", not straddle_problems, f"{straddle_problems}")
    gate("touched-block set stays IN SCOPE: exactly 3 blocks, and neither (18,18) nor (19,17) -- "
         "named in the prompt's 5-block carry-footprint list but holding NONE of the 7 defect "
         "cells -- is among them", len(blocks) == 3 and (18, 18) not in blocks and (19, 17) not in blocks,
         f"blocks={sorted(blocks)}")
    gate("located exactly 7 target tris (1 per Round-10 defect cell)", len(plan) == 7,
         f"n={len(plan)} cells={[tuple(p['cell']) for p in plan]}")
    cellset = {tuple(p["cell"]) for p in plan}
    gate("located cell set == Round-10 dump cell set, EXACTLY (the reconciliation gate)",
         cellset == set(targets), f"missing={set(targets) - cellset} extra={cellset - set(targets)}")
    gate("every located tri's OLD topo == 16 (STRIPS grass|desert) -- never touching an "
         "already-plain tile", all(all(t == 16 for t in [X.decode_id(i)["topograph"] for i in p["old_idall"]])
                                   for p in plan))
    gate("every located tri's OLD uv reconciles with the Round-10 dump byte-exact (float32 tol)",
         all(p["dump_uv_match"] for p in plan),
         f"mismatched={[p['cell'] for p in plan if not p['dump_uv_match']]}")
    uniform_idalls = {p["old_idall"][0] for p in plan if len(set(p["old_idall"])) == 1}
    gate("all 7 tris carry ONE uniform idall across all 3 corners each, and it is the SAME idall "
         "for all 7 tris (clean, safe to blanket re-encode)",
         all(len(set(p["old_idall"])) == 1 for p in plan) and len(uniform_idalls) == 1,
         f"idall={sorted(uniform_idalls)}")

    # --- PRE-STATE reclassify (current deployed bytes, unmodified) --------------------------------
    pre_gg, pre_cells, pre_rg = reclassify_region(game_root)
    gate("PRE-STATE reclassify (current deployed bytes): exactly 7 green ground tiles -- matches "
         "the Round-10 dump baseline", pre_gg == 7, f"n={pre_gg} cells={pre_cells}")
    gate("PRE-STATE reclassify: rock-green (topo 49/58, the separate uncatalogued texture axis) is "
         "currently 23 -- matches the Round-10 dump baseline", pre_rg == 23, f"n={pre_rg}")

    # --- compute the redress on a COPY (bms itself is never mutated at build time) -----------------
    new_bms = {blk: copy.deepcopy(bm) for blk, bm in bms.items()}
    origins = {blk: X.block_world_origin(*blk) for blk in blocks}
    for p in plan:
        blk, cell, tri_idx = tuple(p["block"]), tuple(p["cell"]), p["tri_local_idx"]
        ox, oz = origins[blk]
        quad, ori, new_uv, new_idall = compute_redress(bms[blk], ox, oz, cell, tri_idx)
        p["quad"], p["ori"], p["new_uv"], p["new_idall"] = list(quad), ori, new_uv, new_idall
        nb = new_bms[blk]
        for k, j in enumerate(tri_idx):
            old_tan = nb.tangents[j]
            nb.uvs[j] = new_uv[k]
            nb.tangents[j] = [float(new_idall[k])] + list(old_tan[1:])

    gate("new topo == GROUNDS['desert']['topo'] (17) for every redressed corner",
         all(X.decode_id(v)["topograph"] == GL.GROUNDS["desert"]["topo"]
             for p in plan for v in p["new_idall"]))
    gate("event/area/flags preserved bit-for-bit (topo is the ONLY idall field that changes)",
         all(_same_event_area_flags(o, n) for p in plan for (o, n) in zip(p["old_idall"], p["new_idall"])))

    region = GL.ground_main_region("desert")
    out_of_region = [(p["cell"], uv) for p in plan for uv in p["new_uv"]
                     if not (region[0] - REGION_TOL <= uv[0] <= region[2] + REGION_TOL
                             and region[1] - REGION_TOL <= uv[1] <= region[3] + REGION_TOL)]
    gate(f"every new UV corner lands inside GROUNDS['desert'] mains region "
         f"{tuple(round(x, 5) for x in region)} (+/-{REGION_TOL})", not out_of_region,
         f"out_of_region={out_of_region}")

    # --- zero geometry moved: verts/normals identical everywhere; every OTHER vertex untouched ------
    geom_ok, other_ok = True, True
    other_detail = {}
    for blk in blocks:
        bm0, bm1 = bms[blk], new_bms[blk]
        if bm0.verts != bm1.verts or bm0.normals != bm1.normals:
            geom_ok = False
        changed = {j for p in plan if tuple(p["block"]) == blk for j in p["tri_local_idx"]}
        bad = [j for j in range(bm0.vcount) if j not in changed
               and (bm0.uvs[j] != bm1.uvs[j] or bm0.tangents[j] != bm1.tangents[j])]
        if bad:
            other_ok = False
            other_detail[str(blk)] = bad[:8]
    gate("zero vertex/normal motion anywhere (verts+normals byte-identical, every block)", geom_ok)
    gate("every OTHER vertex's uv+tangent (all 1542 untouched tri-corners) is byte-identical pre/post",
         other_ok, f"{other_detail}")

    post_green = [(p["cell"], GE.tri_green_frac(p["new_uv"], nsub=10)) for p in plan]
    gate("each redressed tri's NEW uv classifies as non-green (tri_green_frac == 0.0, matching the "
         "calibrated GROUNDS['desert'] mains signature of 0.000)", all(g == 0.0 for _, g in post_green),
         f"{post_green}")

    # --- POST-STATE reclassify (in-memory, pre-write) -----------------------------------------------
    post_gg, post_cells, post_rg = reclassify_region(game_root, override_bms=new_bms)
    gate("POST-STATE reclassify (in-memory, pre-write): 0 green ground tiles left in the comp[1] "
         "region", post_gg == 0, f"n={post_gg} cells={post_cells}")
    gate("POST-STATE reclassify (in-memory, pre-write): rock-green stays EXACTLY 23, unchanged "
         "(this redress never touches topo 49/58)", post_rg == 23, f"n={post_rg}")

    n_fail = sum(1 for _, ok, _ in GATES if not ok)
    print(f"\n=== {len(GATES)} gates, {n_fail} FAILED ===")

    print("\n--- per-tri plan (old row/uv -> target desert mains uv) ---")
    for p in plan:
        print(f"  cell{tuple(p['cell'])} block{tuple(p['block'])} row={p['row']} "
              f"idall {p['old_idall'][0]}->{p['new_idall'][0]}")
        print(f"      old uv={p['old_uv']}")
        print(f"      new uv={p['new_uv']}  (quad={p['quad']} ori={p['ori']})")

    out = dict(
        mod_folder=MOD, mint_blocks=[list(b) for b in MINT_BLOCKS],
        touched_blocks=[list(b) for b in blocks],
        plan=[{k: v for k, v in p.items()} for p in plan],
        pre_state=dict(n_green_ground=pre_gg, green_cells=pre_cells, n_rock_green=pre_rg),
        post_state=dict(n_green_ground=post_gg, green_cells=post_cells, n_rock_green=post_rg),
        n_gates=len(GATES), n_failed=n_fail,
        gates=[{"name": n, "ok": ok, "detail": str(d)} for n, ok, d in GATES],
        deployed=False,
    )
    return dict(bms=bms, new_bms=new_bms, plan=plan, blocks=blocks, targets=targets,
               n_fail=n_fail, out=out)


# ================================================================================================
# ROUND 2 -- the desert|dunes pair's OWN orphan-decal class (playtest report at world (1214,-1162),
# cell (303,-291), block (18,18) -- a DIFFERENT pair from Round 10's grass|desert scope, and a block
# Round-1's own scope-gate (above) explicitly REFUSES to open, since it holds none of the 7 grass|
# desert defects. This is a genuinely distinct defect on a genuinely distinct pair, so it earns its
# OWN census, its OWN rule-derived target set (never a hardcoded cell list), and its OWN scope gate
# -- Round-1's refusal of (18,18)/(19,17) a few hundred lines up is untouched by any of this.
# ================================================================================================

# the 9-block comp[1] core (== MINT_BLOCKS, the only region a write may land) unioned with its
# 1-block Moore ring (read-only -- neighbour lookups only), clipped to the engine's real 24x20
# block grid (mesh.block_in_grid -- THE GRID-BOUNDS GATE, minted by the 2026-07-21 dunes off-grid
# incident).
ROUND2_RING = sorted({(bx + dx, by + dy) for (bx, by) in MINT_BLOCKS
                      for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                      if M.block_in_grid(bx + dx, by + dy)})

STRADDLE_ROWS = frozenset({1, 3})    # STRIPS' "straddle-cell shared decal" rows (Law 2, grass|
                                      # desert vocabulary -- desert|dunes is the SAME translated-B-
                                      # strip 4-row family) -- legitimate ONLY on a cell that is
                                      # ITSELF split between the two families: the decal's two
                                      # halves exist to union into one rect across exactly two
                                      # different-family tris sharing one cell.
FRINGE_ROWS = frozenset({0, 2})      # single-family pure-fringe rows -- legitimate near (not
                                      # necessarily co-cell with) the partner family (Law 4's modal
                                      # 1-cell, occasionally 2-4-cell-at-reentrants, dressing band).
BAND_RING = 2                        # the FRINGE_ROWS neighbour-search radius -- deliberately more
                                      # generous than Law 4's *modal* 1, so a legitimately-dressed
                                      # fringe cell is never false-flagged by an under-sized search.
                                      # (Only reaches cells inside the loaded ROUND2_RING; a fringe
                                      # cell within BAND_RING of the OUTER edge of that ring could in
                                      # principle be undercounted -- noted, not load-bearing for the
                                      # one defect this round actually finds, which trips the
                                      # unconditional STRADDLE_ROWS rule, not this neighbour check.)

_S_DD = GL.STRIPS[("desert", "dunes")]
#: the expected row1 rect, computed from grassland.py's OWN constants (never the plan's copied
#: decimal literals) -- reconciled against live bytes below, not trusted blind.
EXPECTED_ROW1_RECT = (round(GL.STRIP_U[0] + _S_DD["du"], 5), round(GL.STRIPS_V[1][0] + _S_DD["dv"], 5),
                      round(GL.STRIP_U[1] + _S_DD["du"], 5), round(GL.STRIPS_V[1][1] + _S_DD["dv"], 5))
EXPECTED_ROUND2_DEFECTS = {(303, -291)}          # the plan's own asserted target set
EXPECTED_ROUND2_BLOCKS = {(18, 18)}              # -- both RE-DERIVED from live bytes below, never
EXPECTED_ROUND2_ROW = 1                          #    trusted blind; a mismatch is a hard AssertionError
EXPECTED_ROUND2_ORI = 0
EXPECTED_ROUND2_IDALL = X.encode_id(0, 0, GL.GROUNDS["desert"]["topo"], 0)   # event0/area0/topo17/flags0 = 68


def _region_blockmeshes(game_root: Path, blocks, override_bms: dict | None = None):
    """Load every block in `blocks`: an in-memory override (the pre-write, in-process POST-STATE
    check) if supplied, else the live MOD override if one is deployed there, else the real stock
    Disc-1 bytes -- the 1-block ring around the 9-block comp[1] core is mostly UN-MODDED stock, only
    the core carries an override. Returns {(bx,by): (BlockMesh, 'mem'|'mod'|'stock')}, silently
    skipping a block with none of the three (never fatal here -- it only narrows the neighbour-
    lookup evidence available for cells near that block)."""
    override_bms = override_bms or {}
    out = {}
    for (bx, by) in blocks:
        if (bx, by) in override_bms:
            out[(bx, by)] = (override_bms[(bx, by)], "mem")
            continue
        rel = M.override_relpath(1, bx, by, part="Terrain")
        path = game_root / MOD / rel
        if path.exists():
            out[(bx, by)] = (M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, part="terrain"), "mod")
            continue
        try:
            out[(bx, by)] = (X.read_block(bx, by, disc=1, part="terrain"), "stock")
        except (ValueError, FileNotFoundError):
            continue
    return out


def round2_census(game_root: Path, override_bms: dict | None = None):
    """Rule-derived (never a hardcoded cell list) census of the desert|dunes pair over the 9-block
    comp[1] core + its 1-block ring -- see the module-level Round-2 docstring/comment block above for
    the class rule. Returns (stats, defects, bms); defects = {cell: dict(row, ori, hits=[hit, ...])}
    where a hit carries block/tri_idx/topo/uv/idall for one flagged triangle (a defect cell has 1 or
    2 hits, never more -- a cell is always exactly 2 tris, the walkmesh's own diagonal split)."""
    bms = _region_blockmeshes(game_root, ROUND2_RING, override_bms)
    cellmap = defaultdict(list)
    for (bx, by), (bm, src) in bms.items():
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            wpts = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            cx = sum(p[0] for p in wpts) / 3.0
            cz = sum(p[2] for p in wpts) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            idall_pv = [int(round(bm.tangents[j][0])) for j in tri]
            topo = X.decode_id(idall_pv[0])["topograph"]
            uv3 = [list(bm.uvs[j]) for j in tri]
            cellmap[cell].append(dict(block=(bx, by), src=src, tri_idx=list(tri), topo=topo,
                                      world_pts=wpts, uv=uv3, idall=idall_pv))

    strip_hits = defaultdict(list)   # cell -> [(hit, row, ori), ...] -- every tri that DECODES as a
                                      # desert|dunes strip, via the SAME generative decoder the arc's
                                      # own frozen grazing-eye instrument uses (never a colour band).
    cell_fams = defaultdict(set)     # cell -> {family present at any desert/dunes tri in the cell}
    for cell, hits in cellmap.items():
        for h in hits:
            fam = GE.TOPO_FAM.get(h["topo"])
            if fam not in ("desert", "dunes"):
                continue
            cell_fams[cell].add(fam)
            cls = GE._classify_tri(h["topo"], h["world_pts"], h["uv"], cell)
            if cls[0] == "strip":
                strip_hits[cell].append((h, cls[1], cls[2]))

    stats = dict(n_vocab_cells=len(strip_hits), n_straddle_cells=0, n_pure_cells_with_strip=0,
                n_fringe_ok=0, n_fringe_defect=0, n_straddle_row_defect=0)
    defects = {}
    for cell, hits in strip_hits.items():
        if cell_fams[cell] == {"desert", "dunes"}:
            # a GENUINE same-cell straddle -- always lawful, whatever row it reads.
            stats["n_straddle_cells"] += 1
            continue
        stats["n_pure_cells_with_strip"] += 1
        bad_hits, row_seen, ori_seen = [], None, None
        for (h, row, ori) in hits:
            if row in STRADDLE_ROWS:
                # a straddle-only decal on a cell that cannot supply the straddle -- a STRUCTURAL
                # mismatch, unconditional (no neighbour search can make this row legitimate here).
                bad_hits.append(h)
                row_seen, ori_seen = row, ori
            elif row in FRINGE_ROWS:
                has_neighbor = any(
                    (cell[0] + di, cell[1] + dj) in cellmap
                    and any(t["topo"] == 41 for t in cellmap[(cell[0] + di, cell[1] + dj)])
                    for di in range(-BAND_RING, BAND_RING + 1)
                    for dj in range(-BAND_RING, BAND_RING + 1)
                    if not (di == 0 and dj == 0))
                if has_neighbor:
                    stats["n_fringe_ok"] += 1
                else:
                    stats["n_fringe_defect"] += 1
                    bad_hits.append(h)
                    row_seen, ori_seen = row, ori
        if bad_hits:
            if row_seen in STRADDLE_ROWS:
                stats["n_straddle_row_defect"] += 1
            defects[cell] = dict(row=row_seen, ori=ori_seen, hits=bad_hits)
    stats["n_defect_cells"] = len(defects)
    return stats, defects, bms


def compute_redress_round2(bm, ox: float, oz: float, cell: tuple, tri_idx: list):
    """UV-ONLY redress for a Round-2 tri: idall is left UNTOUCHED -- unlike Round 1's topo16->17
    tris, this defect's topo/idall was never mis-encoded (already GROUNDS['desert']['topo']=17,
    idall 68); the ONLY wrong byte is the UV."""
    cq, co = GL.assign_mains({cell}, seed=REDRESS_SEED)
    quad, ori = cq[cell], co[cell]
    new_uv = []
    for j in tri_idx:
        wx = bm.verts[j][0] + ox
        wz = bm.verts[j][2] + oz
        new_uv.append(list(GL.ground_uv(wx, wz, cell, quad, ori, "desert")))
    return quad, ori, new_uv


def round2_build_and_gate(game_root: Path):
    gates2: list = []

    def g2(name, ok, detail=""):
        gates2.append((name, bool(ok), detail))
        print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
        return bool(ok)

    print("\n=== comp1_orphan_redress.round2_build_and_gate -- THE DESERT|DUNES ORPHAN-DECAL "
         "REDRESS (playtest report at world (1214,-1162)) ===\n")
    print(f"census region: 9-block comp[1] core {MINT_BLOCKS} + 1-block ring -> "
         f"{len(ROUND2_RING)} blocks total: {ROUND2_RING}\n")

    stats, defects, bms = round2_census(game_root)
    print(f"census: {stats}")
    for cell, d in sorted(defects.items()):
        blocks_here = sorted({h['block'] for h in d['hits']})
        print(f"  DEFECT cell{cell} row={d['row']} ori={d['ori']} n_tris={len(d['hits'])} "
             f"blocks={blocks_here}")

    derived_cells = set(defects)
    if not derived_cells:
        # Idempotent steady-state: the round-2 defect is already fixed on disk (applied
        # 2026-07-22 15:22, backup comp1-redress-round2.20260722-152213). A bare dry-run after
        # the apply must report that plainly, not crash on the pre-apply reconciliation assert.
        print("\nround 2: 0 rule-derived defects -- the desert|dunes orphan decal is already "
              "redressed on disk (idempotent no-op; nothing to do).")
        return dict(bms={}, new_bms={}, plan=[], blocks=[], defects={}, n_fail=0,
                    out=dict(idempotent_noop=True, gates=[], defects=[], plan=[]))
    g2("derived defect cell set == the plan's own asserted target set, EXACTLY",
       derived_cells == EXPECTED_ROUND2_DEFECTS,
       f"derived={sorted(derived_cells)} expected={sorted(EXPECTED_ROUND2_DEFECTS)}")
    assert derived_cells == EXPECTED_ROUND2_DEFECTS, (
        f"round-2 rule-derived defect set {sorted(derived_cells)} != the plan's asserted "
        f"{sorted(EXPECTED_ROUND2_DEFECTS)} -- REFUSING to proceed on an unreconciled derivation "
        f"(ambiguous diagnosis -- report, do not fix)")

    blocks2 = sorted({h["block"] for d in defects.values() for h in d["hits"]})
    g2("derived touched-block set == {(18,18)}, EXACTLY", set(blocks2) == EXPECTED_ROUND2_BLOCKS,
       f"blocks={blocks2}")
    g2("every derived block sits inside the writable 9-block comp[1] core (MINT_BLOCKS) -- never "
       "the read-only ring", all(b in set(MINT_BLOCKS) for b in blocks2), f"blocks={blocks2}")

    tgt = next(iter(EXPECTED_ROUND2_DEFECTS))
    only = defects.get(tgt)
    if only is not None:
        g2("the one defect cell reads row=1 ori=0 (the plan's own reading)",
           only["row"] == EXPECTED_ROUND2_ROW and only["ori"] == EXPECTED_ROUND2_ORI,
           f"row={only['row']} ori={only['ori']}")
        g2("the one defect cell flags BOTH of its 2 tris (the walkmesh's own diagonal split -- the "
           "whole cell wears the decal, not one corner of it, matching the plan's own reading)",
           len(only["hits"]) == 2, f"n={len(only['hits'])}")
        union_u = [u for h in only["hits"] for (u, v) in h["uv"]]
        union_v = [v for h in only["hits"] for (u, v) in h["uv"]]
        got_rect = (round(min(union_u), 5), round(min(union_v), 5),
                   round(max(union_u), 5), round(max(union_v), 5))
        g2("the 2 tris' UV corners union to the STRIPS(desert,dunes) row1 rect, byte-exact (5dp), "
           "computed from grassland.py's OWN constants -- never the plan's copied decimal literals",
           got_rect == EXPECTED_ROW1_RECT, f"got={got_rect} expected={EXPECTED_ROW1_RECT}")
        idalls = [v for h in only["hits"] for v in h["idall"]]
        g2("every corner's idall == 68 (event0/area0/topo17/flags0) -- byte-identical to the plan's "
           "own reading, and to an ordinary plain-desert-mains neighbour (topo/idall was NEVER "
           "mis-encoded here -- this is a pure UV defect, unlike Round 1)",
           all(v == EXPECTED_ROUND2_IDALL for v in idalls), f"idalls={sorted(set(idalls))}")
    else:
        for name in ("the one defect cell reads row=1 ori=0 (the plan's own reading)",
                     "the one defect cell flags BOTH of its 2 tris",
                     "the 2 tris' UV corners union to the STRIPS(desert,dunes) row1 rect",
                     "every corner's idall == 68"):
            g2(name, False, f"target cell {tgt} not found in the derived defect set")

    # --- compute the redress on a COPY (bms itself is never mutated at build time) -----------------
    origins = {blk: X.block_world_origin(*blk) for blk in blocks2}
    new_bms = {blk: copy.deepcopy(bms[blk][0]) for blk in blocks2}
    plan = []
    for cell, d in defects.items():
        blk = d["hits"][0]["block"]
        ox, oz = origins[blk]
        bm = bms[blk][0]
        quad = ori = None
        tri_reports = []
        for h in d["hits"]:
            quad, ori, new_uv = compute_redress_round2(bm, ox, oz, cell, h["tri_idx"])
            new_world_pts = [(bm.verts[j][0] + ox, 0.0, bm.verts[j][2] + oz) for j in h["tri_idx"]]
            tri_reports.append(dict(tri_idx=h["tri_idx"], old_uv=h["uv"], new_uv=new_uv,
                                    idall=h["idall"], new_world_pts=new_world_pts))
            nb = new_bms[blk]
            for k, j in enumerate(h["tri_idx"]):
                nb.uvs[j] = new_uv[k]
        plan.append(dict(block=list(blk), cell=list(cell), row=d["row"], ori=d["ori"],
                         quad=list(quad) if quad else None, new_ori=ori, tris=tri_reports))

    region = GL.ground_main_region("desert")
    out_of_region = [(p["cell"], t["new_uv"][k]) for p in plan for t in p["tris"] for k in range(3)
                     if not (region[0] - REGION_TOL <= t["new_uv"][k][0] <= region[2] + REGION_TOL
                             and region[1] - REGION_TOL <= t["new_uv"][k][1] <= region[3] + REGION_TOL)]
    g2(f"every new UV corner lands inside GROUNDS['desert'] mains region "
      f"{tuple(round(x, 5) for x in region)} (+/-{REGION_TOL})", not out_of_region,
      f"out_of_region={out_of_region}")

    new_row_check = [GE._classify_tri(GL.GROUNDS["desert"]["topo"], t["new_world_pts"], t["new_uv"],
                                      tuple(p["cell"]))
                    for p in plan for t in p["tris"]]
    g2("every redressed tri's NEW uv re-classifies as ('mains','desert',...) -- the STRIPS decal is "
      "genuinely GONE, not merely tolerance-adjacent to it",
      all(c[0] == "mains" and c[1] == "desert" for c in new_row_check),
      f"{[c[0] for c in new_row_check]}")

    # --- zero geometry moved, zero idall moved (Round 2 is UV-ONLY), every OTHER vertex untouched --
    geom_ok, idall_ok, other_ok = True, True, True
    other_detail = {}
    for blk in blocks2:
        bm0, bm1 = bms[blk][0], new_bms[blk]
        if bm0.verts != bm1.verts or bm0.normals != bm1.normals:
            geom_ok = False
        if bm0.tangents != bm1.tangents:
            idall_ok = False
        changed = {j for p in plan if tuple(p["block"]) == blk for t in p["tris"] for j in t["tri_idx"]}
        bad = [j for j in range(bm0.vcount) if j not in changed and bm0.uvs[j] != bm1.uvs[j]]
        if bad:
            other_ok = False
            other_detail[str(blk)] = bad[:8]
    g2("zero vertex/normal motion anywhere (verts+normals byte-identical, every touched block)",
      geom_ok)
    g2("zero idall/tangent motion anywhere -- Round 2 is UV-ONLY (unlike Round 1, topo/idall was "
      "already correct here)", idall_ok)
    g2("every OTHER vertex's uv is byte-identical pre/post (only the redressed corners move)",
      other_ok, f"{other_detail}")

    # --- POST-STATE reclassify (in-memory, pre-write): re-run the SAME census with the redressed
    #     block substituted in, confirm zero desert|dunes defects remain -------------------------
    post_stats, post_defects, _ = round2_census(game_root, override_bms={b: new_bms[b] for b in blocks2})
    g2("POST-STATE reclassify (in-memory, pre-write): 0 desert|dunes defect cells left in the region",
      post_stats["n_defect_cells"] == 0, f"n={post_stats['n_defect_cells']} cells={sorted(post_defects)}")
    g2("POST-STATE reclassify: straddle-cell count is UNCHANGED (this redress never touches a "
      "genuine straddle)", post_stats["n_straddle_cells"] == stats["n_straddle_cells"],
      f"pre={stats['n_straddle_cells']} post={post_stats['n_straddle_cells']}")

    n_fail = sum(1 for _, ok, _ in gates2 if not ok)
    print(f"\n=== round-2: {len(gates2)} gates, {n_fail} FAILED ===")

    print("\n--- round-2 per-tri plan (old row -> lawful plain-desert-mains uv) ---")
    for p in plan:
        print(f"  cell{tuple(p['cell'])} block{tuple(p['block'])} old_row={p['row']} "
             f"old_ori={p['ori']} -> quad={p['quad']} new_ori={p['new_ori']}")
        for t in p["tris"]:
            print(f"      tri{t['tri_idx']} idall {t['idall']} (unchanged)")
            print(f"        old uv={t['old_uv']}")
            print(f"        new uv={t['new_uv']}")

    out = dict(
        mod_folder=MOD, census_core=[list(b) for b in MINT_BLOCKS],
        census_ring=[list(b) for b in ROUND2_RING], stats=stats,
        defect_cells=[list(c) for c in sorted(defects)],
        touched_blocks=[list(b) for b in blocks2],
        plan=plan, post_stats=post_stats,
        n_gates=len(gates2), n_failed=n_fail,
        gates=[{"name": n, "ok": ok, "detail": str(d)} for n, ok, d in gates2],
        deployed=False,
    )
    return dict(bms={b: bms[b][0] for b in blocks2}, new_bms=new_bms, plan=plan, blocks=blocks2,
               defects=defects, n_fail=n_fail, out=out)


def round2_apply_redress(game_root: Path, res2: dict, out2: dict) -> int:
    """--apply for Round 2: same backup-first-refusal / write / mirror / post-check shape as
    ``apply_redress``, specialized for a UV-ONLY redress (no idall/tangent window)."""
    bms, new_bms, plan, blocks = res2["bms"], res2["new_bms"], res2["plan"], res2["blocks"]
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = BACKUP_ROOT / f"comp1-redress-round2.{ts}"
    try:
        n_bk = backup_files(game_root, blocks, backup_root)
    except Exception as e:
        sys.exit(f"REFUSING to write (round 2): backup failed ({e}); nothing was touched.")
    if n_bk == 0:
        sys.exit("REFUSING to write (round 2): backup copied 0 files (unexpected); aborting before any write.")
    print(f"\n[round 2] backed up {n_bk} file(s) -> {backup_root}")

    before_bytes = {}
    written = []
    for blk in blocks:
        rel = M.override_relpath(1, blk[0], blk[1], part="Terrain")
        path = game_root / MOD / rel
        before_bytes[blk] = path.read_bytes()
        p = M.deploy_override(new_bms[blk], mod_folder=MOD, part="Terrain")
        written.append(p)
        print(f"  wrote {p}")

    mirror_summary = DM.auto_mirror(written, mod_folder=MOD)
    print(f"  disc-4 mirror summary: {mirror_summary}")

    post_gates = []

    def pg(name, ok, detail=""):
        post_gates.append({"name": name, "ok": bool(ok), "detail": str(detail)})
        print(f"POST [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

    post_stats, post_defects, _ = round2_census(game_root)
    pg("POST re-classify (disk read-back): 0 desert|dunes defect cells in the region",
      post_stats["n_defect_cells"] == 0, f"n={post_stats['n_defect_cells']} cells={sorted(post_defects)}")

    diff_report = {}
    all_diffs_ok = True
    for blk in blocks:
        rel = M.override_relpath(1, blk[0], blk[1], part="Terrain")
        after = (game_root / MOD / rel).read_bytes()
        before = before_bytes[blk]
        diffs = _byte_diff_ranges(before, after)
        touched = {j for p in plan if tuple(p["block"]) == blk for t in p["tris"] for j in t["tri_idx"]}
        vcount = bms[blk].vcount
        uv_off = 20 + vcount * 12 + vcount * 12
        windows = [(uv_off + j * 8, uv_off + j * 8 + 8) for j in sorted(touched)]
        bad = _bytes_outside_windows(diffs, windows)
        diff_report[str(blk)] = dict(n_diff_ranges=len(diffs), n_expected_windows=len(windows),
                                     n_diff_bytes=sum(e - s for s, e in diffs),
                                     n_window_bytes=sum(w1 - w0 for w0, w1 in windows),
                                     out_of_expected_bytes=bad)
        if bad:
            all_diffs_ok = False
    pg("byte-diff vs backup touches ONLY the UV(8B) windows of the redressed corners (round 2 never "
      "touches the 4B idall window -- it was already correct)", all_diffs_ok, f"{diff_report}")

    n_post_fail = sum(1 for g in post_gates if not g["ok"])
    out2["deployed"] = True
    out2["backup_dir"] = str(backup_root)
    out2["written"] = [str(p) for p in written]
    out2["mirror_summary"] = mirror_summary
    out2["post_gates"] = post_gates
    out2["n_post_gates"] = len(post_gates)
    out2["n_post_failed"] = n_post_fail
    print(f"\n=== round-2 APPLY complete: {len(post_gates)} post-gates, {n_post_fail} FAILED ===")
    return n_post_fail


# ================================================================================================
# --apply: backup -> write -> mirror -> post-checks
# ================================================================================================
def backup_files(game_root: Path, blocks: list, backup_root: Path) -> int:
    """Back up EVERY per-cell override part present for the touched blocks (Terrain/Object/Beach1/
    Sea1-5/Donor.txt -- whatever exists), on BOTH Disc1 (about to be written) and Disc4 (about to be
    overwritten by the mirror step), even though only Terrain's bytes actually change -- honoring
    the hard 'backup before every game-folder write' rule rather than relying on content-identity
    for the untouched sibling files (recon risk #2). Preserves each file's path relative to the
    game root (mirrors FF9CustomMap-world/FF9_Data/WorldMap/Disc{d}/0_1/r{y}/Block[x][y] <Part>...).
    Returns the number of files backed up; raises on any copy failure (the caller must abort on
    exception -- NO write may proceed if the backup did not fully succeed)."""
    backup_root.mkdir(parents=True, exist_ok=True)
    n = 0
    for (bx, by) in blocks:
        for disc in (1, 4):
            folder = game_root / MOD / f"FF9_Data/WorldMap/Disc{disc}/0_1/r{by}"
            if not folder.is_dir():
                continue
            pattern = _glob_mod.escape(f"Block[{bx}][{by}]") + " *"
            for p in sorted(folder.glob(pattern)):
                rel = p.relative_to(game_root)
                dst = backup_root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
                n += 1
    return n


def _byte_diff_ranges(a: bytes, b: bytes):
    """Contiguous differing byte ranges [(start,end), ...] between two equal-length buffers."""
    assert len(a) == len(b)
    ranges = []
    i, n = 0, len(a)
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            ranges.append((i, j))
            i = j
        else:
            i += 1
    return ranges


def _expected_byte_windows(bm, touched_js: set):
    """The .ff9mesh SoA layout (mesh.write_ff9mesh): header(20) | verts(vcount*12) |
    normals(vcount*12) | uvs(vcount*8) | tangents(vcount*16) | indices. For each touched vertex j,
    the ONLY bytes a lawful redress may change are its 8-byte uv entry and the first 4 bytes
    (tangent.x, the idall float) of its 16-byte tangent entry -- y/z/w never move."""
    vcount = bm.vcount
    uv_off = 20 + vcount * 12 + vcount * 12
    tan_off = uv_off + vcount * 8
    windows = []
    for j in sorted(touched_js):
        windows.append((uv_off + j * 8, uv_off + j * 8 + 8))
        windows.append((tan_off + j * 16, tan_off + j * 16 + 4))
    return windows


def _bytes_outside_windows(ranges, windows):
    """Per-BYTE containment against the UNION of expected windows -- NOT per-contiguous-range
    containment against any SINGLE window. Two touched vertices that are adjacent in the file (e.g.
    a tri's 3 corners are consecutive vertex slots j,j+1,j+2 in this unwelded mesh) legitimately
    produce one contiguous differing byte-run that straddles the boundary between vertex j's window
    and vertex j+1's window -- that run is still fully lawful, but a naive 'does ONE window contain
    this whole range' test flags it as a false positive. Returns the list of individual byte offsets
    that differ AND are not covered by any expected window (a genuinely bad byte, if any)."""
    covered = set()
    for (w0, w1) in windows:
        covered.update(range(w0, w1))
    bad = []
    for (s, e) in ranges:
        bad.extend(i for i in range(s, e) if i not in covered)
    return bad


def apply_redress(game_root: Path, bms: dict, new_bms: dict, plan: list, blocks: list, out: dict):
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = BACKUP_ROOT / f"comp1-redress.{ts}"
    try:
        n_bk = backup_files(game_root, blocks, backup_root)
    except Exception as e:
        sys.exit(f"REFUSING to write: backup failed ({e}); nothing was touched.")
    if n_bk == 0:
        sys.exit("REFUSING to write: backup copied 0 files (unexpected); aborting before any write.")
    print(f"\nbacked up {n_bk} file(s) -> {backup_root}")

    before_bytes = {}
    written = []
    for blk in blocks:
        rel = M.override_relpath(1, blk[0], blk[1], part="Terrain")
        path = game_root / MOD / rel
        before_bytes[blk] = path.read_bytes()
        p = M.deploy_override(new_bms[blk], mod_folder=MOD, part="Terrain")
        written.append(p)
        print(f"  wrote {p}")

    mirror_summary = DM.auto_mirror(written, mod_folder=MOD)
    print(f"  disc-4 mirror summary: {mirror_summary}")

    print("\n--- per-tri report (before -> after) ---")
    for p in plan:
        print(f"  cell{tuple(p['cell'])} block{tuple(p['block'])} row={p['row']}")
        print(f"      idall {p['old_idall'][0]} -> {p['new_idall'][0]}")
        print(f"      uv {p['old_uv']} -> {p['new_uv']}")

    post_gates = []

    def pg(name, ok, detail=""):
        post_gates.append({"name": name, "ok": bool(ok), "detail": str(detail)})
        print(f"POST [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

    # (a) re-classify the region from the REAL bytes now on disk
    n_gg, gg_cells, n_rg = reclassify_region(game_root)
    pg("POST re-classify (disk read-back): 0 green ground tiles in the comp[1] region",
       n_gg == 0, f"n={n_gg} cells={gg_cells}")
    pg("POST re-classify (disk read-back): rock-green stays exactly 23, unchanged",
       n_rg == 23, f"n={n_rg}")

    # (b) byte-diff each modified Terrain file vs its own backup, confined to expected ranges
    diff_report = {}
    all_diffs_ok = True
    for blk in blocks:
        rel = M.override_relpath(1, blk[0], blk[1], part="Terrain")
        after = (game_root / MOD / rel).read_bytes()
        before = before_bytes[blk]
        diffs = _byte_diff_ranges(before, after)
        touched = {j for p in plan if tuple(p["block"]) == blk for j in p["tri_local_idx"]}
        windows = _expected_byte_windows(bms[blk], touched)
        # per-BYTE union containment (NOT "does one window contain the whole contiguous diff-range"
        # -- that naive test false-positives whenever two touched vertices are adjacent in the file,
        # e.g. a tri's 3 corners are consecutive vertex slots and their combined diff-run straddles
        # the boundary between two legitimately-expected, adjacent windows).
        bad = _bytes_outside_windows(diffs, windows)
        diff_report[str(blk)] = dict(n_diff_ranges=len(diffs), n_expected_windows=len(windows),
                                     n_diff_bytes=sum(e - s for s, e in diffs),
                                     n_window_bytes=sum(w1 - w0 for w0, w1 in windows),
                                     out_of_expected_bytes=bad)
        if bad:
            all_diffs_ok = False
    pg("byte-diff vs backup touches ONLY bytes covered by the expected UV/idall windows (per-byte "
       "union containment, every touched file)", all_diffs_ok, f"{diff_report}")

    n_post_fail = sum(1 for g in post_gates if not g["ok"])
    out["deployed"] = True
    out["backup_dir"] = str(backup_root)
    out["written"] = [str(p) for p in written]
    out["mirror_summary"] = mirror_summary
    out["post_gates"] = post_gates
    out["n_post_gates"] = len(post_gates)
    out["n_post_failed"] = n_post_fail
    print(f"\n=== APPLY complete: {len(post_gates)} post-gates, {n_post_fail} FAILED ===")
    return n_post_fail


# ================================================================================================
# --revert
# ================================================================================================
def revert_from_backup(name: str) -> int:
    backup_dir = Path(name)
    if not backup_dir.is_absolute():
        backup_dir = BACKUP_ROOT / name
    if not backup_dir.is_dir():
        sys.exit(f"no such backup dir: {backup_dir}")
    game_root = Path(_cfg.find_game_path(None))
    n = 0
    for p in sorted(backup_dir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(backup_dir)
            dst = game_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            n += 1
            print(f"  restored {dst}")
    print(f"\nreverted {n} file(s) from {backup_dir} -> {game_root}")
    return 0


# ================================================================================================
# main
# ================================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write + backup + mirror + post-check")
    ap.add_argument("--revert", metavar="BACKUP_DIR", default=None,
                    help="restore every file from a prior --apply's backup dir")
    args = ap.parse_args()

    if args.revert:
        return revert_from_backup(args.revert)

    game_root = Path(_cfg.find_game_path(None))

    print("#" * 96)
    print("# ROUND 1 -- grass|desert orphan decals (Round 10's own dump)")
    print("#" * 96)
    res = build_and_gate(game_root)

    print("\n" + "#" * 96)
    print("# ROUND 2 -- desert|dunes orphan decal (a straddle-only row on a non-straddle cell)")
    print("#" * 96)
    res2 = round2_build_and_gate(game_root)

    out = dict(res["out"])
    out["round2"] = res2["out"]

    if args.apply:
        # Round 1 was already applied earlier the same day (backups/comp1-redress.20260722-140044/)
        # -- a re-run of its own matcher correctly finds 0 targets (idempotent: an already-redressed
        # cell no longer decodes as topo16, so it never re-matches). An EMPTY plan is that expected
        # steady state, not a failure, so it is not treated as one; a NON-empty plan that still fails
        # its own gates is refused exactly as before.
        any_post_fail = 0
        if res["plan"]:
            if res["n_fail"]:
                sys.exit(f"REFUSING round-1 --apply: {res['n_fail']} dry-run gate(s) failed")
            any_post_fail += apply_redress(game_root, res["bms"], res["new_bms"], res["plan"],
                                           res["blocks"], out)
        else:
            print("\nROUND 1: nothing to apply (0 located targets -- idempotent no-op, consistent "
                 "with the redress already on disk)")
        if res2["plan"]:
            if res2["n_fail"]:
                sys.exit(f"REFUSING round-2 --apply: {res2['n_fail']} dry-run gate(s) failed")
            any_post_fail += round2_apply_redress(game_root, res2, out["round2"])
        else:
            print("\nROUND 2: nothing to apply (0 located targets)")
        OUT.write_text(json.dumps(out, indent=1, default=str))
        print(f"\n-> {OUT}")
        return 0 if any_post_fail == 0 else 1

    OUT.write_text(json.dumps(out, indent=1, default=str))
    print(f"\nDRY-RUN only -- nothing written to the game. Plan -> {OUT}")
    return 0 if (res["n_fail"] == 0 and res2["n_fail"] == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
