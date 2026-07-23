"""RUNG D BUILD -- the full offline gate suite + the would-be-deployed dry-run file set for the
horseshoe-bench rebuild at the SW pocket site, on top of ``rung_d_layout.py``'s already-run staging
(site/anchor/termini/line/retile/dressing -- imported and re-executed here to capture the intermediate
in-memory blocks this script's own gates + file-set builder need; ``rung_d_layout.py`` itself is left
unmodified except for one corrected constant, see below).

READ-ONLY AGAINST THE GAME INSTALL. Dry-run (default) writes the complete would-be-deployed file set to
``out/rung_d/FF9CustomMap-world/...`` (never the game install). ``--apply`` (owner-gated, NEVER invoked
by this workflow) backs up any pre-existing target file first, writes, then auto-mirrors to Disc4,
mirroring ``mixed_biome_mint.py``'s / ``comp1_orphan_redress.py``'s own conventions. ``--revert`` undoes
a prior ``--apply`` via its manifest.

THIS SCRIPT FOLDS IN THE SKEPTIC REVIEW'S FINDINGS on the design report that preceded it (findings
verified against real bytes in this session, not taken on faith):

1. RATIO UNIT MISMATCH (confirmed, load-bearing) -- the design's headline ratio (1.358) paired Rung D's
   dressing PLAN-ENTRY count (``n_planned``=110, one record per assignment DECISION -- a straddle cell's
   decision can resolve to 1 OR 2 physical triangle writes) against Rung C's own TRI-WRITE count
   (``n_writes``=240, read from ``out/mixed_biome_mint.json`` this session). Re-derived in consistent
   units (tri-writes, the same granularity the desert-BODY count already uses, and the same granularity
   ``mixed_biome_eye_review.py``'s real-stock render classifies): Rung C = 240 writes : 96 body = 2.50;
   Rung D = 218 writes : 81 body = 2.69 -- Rung D is *worse* than Rung C by this measure, not "54% of
   its severity". Fixed below (``ratio_corrected``).
2. THE STOCK_CORE_DRESS_TRIS=110 "whole-map" FIGURE IS UNTRACEABLE -- grep-verified against every leaf
   value in ``out/contract_gd_composition.json`` this session: 110 appears exactly once, as
   ``topo_band.by_family.grass["29"]["0"]`` (a grass-depth-bin tri count, unrelated to any dressing/strip
   count). No whole-map stock dressing:body tri ratio exists anywhere in this study's own census output.
   The "0.26 whole-map band" is DROPPED as a judged clause (not silently kept); only the two traceable
   comparators survive: Rung C's own same-code result (240:96=2.50, re-verified against its JSON) and
   the real-stock render-window measurement (``mixed_eye_review.json``'s ``stock_ab_fam_counts``:
   desert=210, strip=392, both independently re-read this session, not re-typed from the design report).
3. STOCK_BODY_TRIS=422 IS RE-VERIFIED CORRECT -- ``sum(topo_band.by_family.desert[d]["16"] for d in
   0..3)`` = 237+152+29+4 = 422, independently re-summed this session directly from the contract JSON.
4. Clauses left as GAPS by the design (orphan gate, wang gate, byte-diff confinement, quartile density)
   are CLOSED here -- all four are cheap, already-proven machinery (``orphangate.py``, ``transplant.py``,
   ``contract_gd_composition.py``'s own quartile method) that were simply never invoked on Rung D's own
   composed output; they are now.

Run from the repo root:  py studies/overworld-topography/rung_d_build.py
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
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

import rung_d_layout as RDL                                  # noqa: E402  (the already-run staging)

M = RDL.MBM.M
X = RDL.X
IN = RDL.IN
ISL = RDL.ISL
OG = RDL.MBM.OG
TP = RDL.MBM.TP
DM = RDL.MBM.DM
GD = RDL.MBM.GD

MOD = "FF9CustomMap-world"
OUT_DIR = HERE / "out" / "rung_d"
OUT_ROOT = OUT_DIR / MOD
OUT_JSON = OUT_DIR / "rung_d_build.json"
BACKUP_ROOT = REPO_ROOT / "backups"

# ================================================================================================
# THE CORRECTED COMPARATORS (see module docstring items 1-3; every figure below is re-derived from
# a JSON this script re-reads live, not typed in from the design report's prose).
# ================================================================================================
RUNG_C_JSON = HERE / "out" / "mixed_biome_mint.json"
CONTRACT_JSON = HERE / "out" / "contract_gd_composition.json"


def gate(gates: list, name, ok, detail=""):
    gates.append({"name": name, "ok": bool(ok), "detail": str(detail)[:4000]})
    print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return bool(ok)


def log(msg):
    print(msg)


# ================================================================================================
# STAGE A -- re-run rung_d_layout's own staging in-process (in-memory; identical inputs/seeds to the
# already-recorded out/rung_d/rung_d_layout.json -- re-verified byte-identical below, not assumed).
# ================================================================================================
def run_layout_stages(game_root: Path) -> dict:
    log("#" * 100); log("STAGE A -- re-running rung_d_layout's staging in-process (site/anchor/"
                        "termini/line/retile/dressing) to capture in-memory blocks for the gate "
                        "suite + file-set builder below"); log("#" * 100)
    s0 = RDL.stage0_site(game_root)
    coast_edges = RDL.build_coastline(s0["built"])
    s1 = RDL.stage1_anchor(s0["built"], game_root)
    span_blocks = list(s1["res"]["changed"])
    s2 = RDL.stage2_rim_termini(s1["blocks_now"], span_blocks, s1["center"], coast_edges)
    s3 = RDL.stage3_line_and_retile(s1["blocks_now"], s2["term_a"], s2["term_b"], s1["center"])
    s4 = RDL.stage4_dressing_and_ratio(s3["blocks_retiled"], s0["footprint"], s3["retile_touched"],
                                       game_root)
    s5 = RDL.stage5_coast_standoff(coast_edges, s3["blocks_retiled"], s3["retile_stats"], s3["line"],
                                   s0["footprint"])
    return dict(s0=s0, s1=s1, s2=s2, s3=s3, s4=s4, s5=s5, coast_edges=coast_edges,
               span_blocks=span_blocks)


def check_reproduces_recorded_layout(built_stages: dict) -> dict:
    """Independently confirm this run's own numbers match the already-committed
    ``out/rung_d/rung_d_layout.json`` -- if this script's re-run of the SAME seeded pipeline ever
    drifts from the recorded artifact, that is itself a finding, not something to paper over."""
    recorded = json.loads((OUT_DIR / "rung_d_layout.json").read_text(encoding="utf-8"))
    s0, s1, s2, s3, s4, s5 = (built_stages[k] for k in ("s0", "s1", "s2", "s3", "s4", "s5"))
    n_body = s3["retile_stats"]["n_retiled"]
    n_planned = len(s4["dress"]["plan"])
    checks = {
        "stage0.gates": (s0["gates"], recorded["stage0_site"]["gates"]),
        "stage1.blob_tris": (s1["res"]["report"]["blob_tris"], recorded["stage1_anchor"]["report"]["blob_tris"]),
        "stage1.ensemble_tris": (s1["res"]["report"]["ensemble_tris"], recorded["stage1_anchor"]["report"]["ensemble_tris"]),
        "stage2.term_a": (list(s2["term_a"]), recorded["stage2_rim_termini"]["term_a"]),
        "stage2.term_b": (list(s2["term_b"]), recorded["stage2_rim_termini"]["term_b"]),
        "stage3.n_retiled": (n_body, recorded["stage3_line_and_retile"]["retile_stats"]["n_retiled"]),
        "stage4.n_planned": (n_planned, recorded["stage4_dressing"]["n_planned"]),
        "stage4.n_writes": (len(s4["dress"]["writes"]), recorded["stage4_dressing"]["n_writes"]),
        "stage5.line_min": (round(s5["line_min_dist_to_coast"], 2), recorded["stage5_coast_standoff"]["line_min_dist_to_coast"]),
    }
    mismatches = {k: v for k, v in checks.items() if v[0] != v[1]}
    ok = not mismatches
    log(f"  re-run vs recorded rung_d_layout.json: {'IDENTICAL' if ok else 'DIVERGED'}"
       + (f" -- {mismatches}" if mismatches else ""))
    return dict(ok=ok, mismatches=mismatches)


# ================================================================================================
# STAGE B -- THE CORRECTED RATIO (module docstring items 1-3)
# ================================================================================================
def stage_ratio_corrected(built_stages: dict) -> dict:
    log("\n" + "#" * 100); log("STAGE B -- THE CORRECTED DRESSING:BODY RATIO (consistent units, "
                              "re-verified comparators)"); log("#" * 100)
    s3, s4 = built_stages["s3"], built_stages["s4"]
    n_body = s3["retile_stats"]["n_retiled"]
    n_planned = len(s4["dress"]["plan"])
    n_writes = len(s4["dress"]["writes"])
    ratio_writes = n_writes / n_body if n_body else None
    ratio_planned = n_planned / n_body if n_body else None

    if not RUNG_C_JSON.is_file():
        raise FileNotFoundError(f"{RUNG_C_JSON} missing -- cannot re-verify the Rung-C comparator "
                                f"live; refusing to fall back to a typed-in number")
    rc = json.loads(RUNG_C_JSON.read_text(encoding="utf-8"))
    rc_n_body = rc["sector_retile"]["n_retiled"]
    rc_n_writes = rc["dressing"]["n_writes"]
    rc_n_planned = rc["dressing"]["n_planned"]
    rc_ratio_writes = rc_n_writes / rc_n_body
    rc_ratio_planned = rc_n_planned / rc_n_body
    log(f"  Rung C re-read live from {RUNG_C_JSON.name}: n_retiled(body)={rc_n_body} "
       f"n_planned={rc_n_planned} n_writes={rc_n_writes} -> writes:body={rc_ratio_writes:.4f}, "
       f"planned:body={rc_ratio_planned:.4f}")
    log(f"  Rung D (this build): n_retiled(body)={n_body} n_planned={n_planned} n_writes={n_writes} "
       f"-> writes:body={ratio_writes:.4f}, planned:body={ratio_planned:.4f}")

    if not CONTRACT_JSON.is_file():
        raise FileNotFoundError(f"{CONTRACT_JSON} missing")
    contract = json.loads(CONTRACT_JSON.read_text(encoding="utf-8"))
    desert_bins = contract["topo_band"]["by_family"]["desert"]
    stock_body_tris = sum(v.get("16", 0) for v in desert_bins.values())
    # the "STOCK_CORE_DRESS_TRIS=110 whole-map ratio" clause is DROPPED here: grep-verified this
    # session that 110 does not correspond to any dressing/strip tri count anywhere in the contract
    # JSON (it is topo_band.by_family.grass["29"]["0"], an unrelated grass depth-bin count) -- there
    # is no traceable whole-map stock dressing:body tri ratio in this study's own census output to
    # report against, so no whole-map verdict is rendered (rather than keep a fabricated one).
    stock_wholemap_ratio_traceable = False

    render_json_path = HERE / "out" / "mixed_biome_mint" / "renders" / "mixed_eye_review.json"
    render = json.loads(render_json_path.read_text(encoding="utf-8"))
    local_desert = render["stock_ab_fam_counts"]["desert"]
    local_strip = render["stock_ab_fam_counts"]["strip"]
    local_stock_ratio = local_strip / local_desert
    tol = 1.25
    local_band_max = local_stock_ratio * tol

    in_band_local_writes = ratio_writes is not None and ratio_writes <= local_band_max
    worse_than_rung_c_writes = ratio_writes is not None and ratio_writes > rc_ratio_writes

    log(f"  local real-stock comparator (re-read live from {render_json_path.name}, "
       f"stock_ab_fam_counts desert={local_desert} strip={local_strip}): {local_stock_ratio:.4f}, "
       f"+25% tol band max {local_band_max:.4f}")
    log(f"  Rung D writes:body ({ratio_writes:.4f}) vs local band max ({local_band_max:.4f}): "
       f"{'IN-BAND' if in_band_local_writes else 'OUT OF BAND'}")
    log(f"  Rung D writes:body ({ratio_writes:.4f}) vs Rung C's own writes:body ({rc_ratio_writes:.4f}): "
       f"{'WORSE (higher)' if worse_than_rung_c_writes else 'better-or-equal'}")
    log("  STOCK WHOLE-MAP RATIO CLAUSE: DROPPED -- the design's cited 110:422=0.26 comparator is "
       "untraceable to any real dressing/strip count in contract_gd_composition.json (verified this "
       "session); no whole-map dressing:body figure exists in this study's census to judge against.")

    return dict(
        n_body=n_body, n_planned=n_planned, n_writes=n_writes,
        ratio_writes=round(ratio_writes, 4) if ratio_writes else None,
        ratio_planned=round(ratio_planned, 4) if ratio_planned else None,
        rung_c=dict(n_body=rc_n_body, n_planned=rc_n_planned, n_writes=rc_n_writes,
                   ratio_writes=round(rc_ratio_writes, 4), ratio_planned=round(rc_ratio_planned, 4)),
        stock_body_tris_reverified=stock_body_tris,
        stock_wholemap_ratio_traceable=stock_wholemap_ratio_traceable,
        local_stock_ratio=round(local_stock_ratio, 4), local_stock_desert=local_desert,
        local_stock_strip=local_strip, local_band_tol=tol, local_band_max=round(local_band_max, 4),
        in_band_local_writes_units=in_band_local_writes,
        worse_than_rung_c_writes_units=worse_than_rung_c_writes,
        headline=(f"Rung D writes:body = {ratio_writes:.4f} is "
                 f"{'WORSE than' if worse_than_rung_c_writes else 'no worse than'} Rung C's own "
                 f"{rc_ratio_writes:.4f} (same code, consistent tri-write units) and "
                 f"{'OUT OF' if not in_band_local_writes else 'IN'} the local real-stock band "
                 f"(<= {local_band_max:.4f}). The design report's '54% of Rung C severity, in-band "
                 f"local' verdict does not survive a consistent-units re-derivation."))


# ================================================================================================
# STAGE C -- QUARTILE DRESSING DENSITY (a real gap the design left open; contract's own method:
# split the line's path into 4 quartiles, per-quartile fraction of CELLS carrying a dressing write)
# ================================================================================================
def stage_quartile_density(built_stages: dict) -> dict:
    log("\n" + "#" * 100); log("STAGE C -- DRESSING DENSITY BY LINE QUARTILE (informational -- "
                              "cell-membership method approximates, not replicates, the contract's "
                              "own connected-walkmesh-cell census)"); log("#" * 100)
    line_pts = built_stages["s3"]["line"]["points"]
    dress = built_stages["s4"]["dress"]
    core_cells = sorted(dress["eligible"]["core_cell_records"].keys())
    planned_cells = {tuple(p["cell"]) for p in dress["plan"]}
    if not core_cells:
        return dict(note="no dressing-core cells -- quartile density undefined", quartiles=[])

    def t_along_line(cx, cz):
        best_t, best_d = 0.0, None
        cum = 0.0
        seglens = [math.hypot(line_pts[k + 1][0] - line_pts[k][0], line_pts[k + 1][1] - line_pts[k][1])
                  for k in range(len(line_pts) - 1)]
        total = sum(seglens) or 1.0
        for k in range(len(line_pts) - 1):
            ax, az = line_pts[k]; bx, bz = line_pts[k + 1]
            ex, ez = bx - ax, bz - az
            L2 = ex * ex + ez * ez
            if L2 < 1e-9:
                cum += seglens[k]; continue
            tt = max(0.0, min(1.0, ((cx - ax) * ex + (cz - az) * ez) / L2))
            px, pz = ax + tt * ex, az + tt * ez
            d = math.hypot(cx - px, cz - pz)
            if best_d is None or d < best_d:
                best_d = d
                best_t = (cum + tt * seglens[k]) / total
            cum += seglens[k]
        return best_t

    cell_t = {}
    for c in core_cells:
        cx, cz = (c[0] + 0.5) * 4.0, (c[1] + 0.5) * 4.0
        cell_t[c] = t_along_line(cx, cz)
    ordered = sorted(core_cells, key=lambda c: cell_t[c])
    n = len(ordered)
    quartiles = []
    for qi in range(4):
        lo = (n * qi) // 4
        hi = (n * (qi + 1)) // 4 if qi < 3 else n
        seg = ordered[lo:hi] or ordered[lo:lo + 1]
        dressed = sum(1 for c in seg if c in planned_cells)
        quartiles.append(dict(quartile=qi, n_cells=len(seg), n_dressed=dressed,
                              rate=round(dressed / len(seg), 3) if seg else None))
    log(f"  Rung D dressing density by line quartile (n={n} core cells): {quartiles}")
    log(f"  contract's own stock main-arm quartile rates (cell-connectivity method, NOT directly "
       f"comparable -- different cell graph): {RDL.STOCK_DRESS_QUARTILES}")
    return dict(n_core_cells=n, quartiles=quartiles, stock_quartiles_informational=RDL.STOCK_DRESS_QUARTILES,
               method_note="Rung D bins ALL dressing-eligible cells (straddle+fringe) ordered by "
                           "projected position on the realized line; the contract bins the STOCK "
                           "line's own BFS-diameter walkmesh-cell path. Different cell graphs -- "
                           "reported side-by-side as informational, not gated pass/fail.")


# ================================================================================================
# STAGE D -- THE FULL GATE SUITE over the FINAL composed set (orphan/wang/mod-overwrite/flat-mesh/
# sea-layer/byte-diff-confinement) -- mirrors mixed_biome_mint.compose()'s own STEP 5 exactly,
# reusing its OG/TP/M imports + make_context_provider/_mint_sea4 helpers unchanged.
# ================================================================================================
def stage_full_gates(built_stages: dict, game_root: Path) -> dict:
    log("\n" + "#" * 100); log("STAGE D -- FULL GATE SUITE (final composed set)"); log("#" * 100)
    gates = []
    s0, s1, s3, s4 = built_stages["s0"], built_stages["s1"], built_stages["s3"], built_stages["s4"]
    footprint = s0["footprint"]
    final_blocks = dict(s4["dress"]["new_blocks"])          # 10 blocks: 5 retiled+dressed, 5 carve-only

    # -- byte-diff confinement: the retile+dress steps must ONLY move UV/idall, zero vertex/normal --
    geom_untouched = True
    bad = []
    pre_carve_blocks = s1["blocks_now"]                      # post-carve, pre-retile
    for blk in footprint:
        b0, b1 = pre_carve_blocks[blk], final_blocks[blk]
        if b0.verts != b1.verts or b0.normals != b1.normals:
            geom_untouched = False
            bad.append(blk)
    gate(gates, "byte-diff confinement: sector-retile + dressing move ZERO vertex/normal bytes on "
        "every footprint block (UV+idall only), vs the post-carve pre-retile baseline",
        geom_untouched, f"{bad}" if bad else "")

    # -- ORPHAN GATE (0/0 mandatory, ring-true) --
    final_cell_meshes = {blk: [("Terrain", bm)] for blk, bm in final_blocks.items()}
    provider = RDL.MBM.make_context_provider(final_blocks, game_root)
    orphan = OG.orphan_decal_gate(final_cell_meshes, footprint, enforce=True, redress=False,
                                  context_provider=provider)
    gate(gates, "THE ORPHAN GATE: 0 orphans / 0 ambiguous over the full final composed footprint "
        "(ring-true against the site's real neighbourhood -- all 10 footprint blocks are open ocean, "
        "so the ring is real stock sea/land, not another carry)",
        orphan["n_orphans"] == 0 and orphan["n_ambiguous"] == 0, f"{orphan}")

    # -- WANG-CARRY GATE (this mint's own sea-layer composition) --
    plane = ISL._sea_plane(1, game_root)
    sea_by_cell = {}
    for blk in footprint:
        bx, by = blk
        hidden = {p.lower(): M.hidden_block_mesh(name=f"Block[{bx}][{by}] {p}", disc=1, x=bx, y=by)
                 for p in ("Sea1", "Sea2", "Sea3", "Sea5")}
        hidden["sea4"] = RDL.MBM._mint_sea4(plane, bx, by)
        sea_by_cell[blk] = hidden
    wang = TP.wang_carry_gate(sea_by_cell, footprint, enforce=True)
    gate(gates, "wang-carry gate: 0 incoherent frame edges (a fresh open-ocean mint, not a Wang-"
        "region crop)", wang["ok"] and wang["incoherent"] == 0, f"{wang}")

    # -- MOD-OVERWRITE GATE (real disk read; Donor.txt = the horseshoe donor_ref for every span block,
    #    matching interior.deploy_mountain_parts' own per-block Donor.txt convention) --
    donor_ref = s1["res"]["donor_ref"]
    cell_donors = {blk: donor_ref for blk in footprint}
    mod_ow = TP._mod_overwrite_gate(MOD, cell_donors, disc=1, game=game_root)
    gate(gates, "MOD-OVERWRITE gate (transplant._mod_overwrite_gate, real disk read against the "
        "live install)", mod_ow["ok"], f"{mod_ow}")

    # -- GRID-BOUNDS (final) --
    gate(gates, "GRID-BOUNDS (final): every block in the composed set is inside the 24x20 grid",
        all(M.block_in_grid(*b) for b in final_blocks), "")

    # -- FLAT-MESH invariant + SEA-LAYER law --
    flat_bad = []
    for blk, bm in final_blocks.items():
        if bm.vcount != len(bm.flat_index) or len(bm.flat_index) != 3 * len(bm.tris):
            flat_bad.append((blk, bm.vcount, len(bm.flat_index), len(bm.tris)))
    for blk in footprint:
        s4m = sea_by_cell[blk]["sea4"]
        if s4m.vcount != len(s4m.flat_index) or len(s4m.flat_index) != 3 * len(s4m.tris):
            flat_bad.append((("Sea4", blk), s4m.vcount, len(s4m.flat_index), len(s4m.tris)))
    changed_parts = s1["res"].get("changed_parts") or {}
    for blk, parts in changed_parts.items():
        for pname, bm in parts.items():
            if bm.vcount != len(bm.flat_index) or len(bm.flat_index) != 3 * len(bm.tris):
                flat_bad.append(((pname, blk), bm.vcount, len(bm.flat_index), len(bm.tris)))
    gate(gates, "byte sanity: THE FLAT-MESH INVARIANT (vcount==len(flat_index)==3*len(tris)) on "
        "every produced Terrain + Sea4 + ensemble-aux mesh", not flat_bad, f"{flat_bad[:6]}")

    sea_y_bad = []
    for blk in footprint:
        s4m = sea_by_cell[blk]["sea4"]
        badv = [v[1] for v in s4m.verts if abs(v[1]) > 1e-6]
        if badv:
            sea_y_bad.append((blk, badv[:4]))
    gate(gates, "byte sanity: THE SEA-LAYER LAW (every Sea4 vertex Y==0)", not sea_y_bad, f"{sea_y_bad[:6]}")

    hidden_y_bad = []
    for blk in footprint:
        for pname, bm in sea_by_cell[blk].items():
            if pname == "sea4":
                continue
            if any(v[1] > OG.STUB_Y_FLOOR for v in bm.verts):
                hidden_y_bad.append((blk, pname))
    gate(gates, "byte sanity: every hidden/blanked sea part sits below the STUB_Y_FLOOR blanking "
        "convention", not hidden_y_bad, f"{hidden_y_bad[:6]}")

    # -- dressing stats vs null (re-verify the engine self-test, same as mixed_biome_mint.compose()) --
    null = RDL.SNR.part_b()
    engine_selftest = GD.engine_selftest(RDL.DRESS_SEED, null)
    gate(gates, "gd_seam_dress engine self-test: realized straddle/fringe rates converge on the "
        "null-cluster targets (N=4000/phase, synthetic cell-ids)", engine_selftest["ok"],
        f"{engine_selftest}")

    n_fail = sum(1 for g in gates if not g["ok"])
    log(f"\n=== STAGE D: {len(gates)} gates, {n_fail} FAILED ===")
    return dict(gates=gates, n_gates=len(gates), n_failed=n_fail, orphan=orphan, wang=wang,
               mod_overwrite=mod_ow, engine_selftest=engine_selftest,
               final_blocks=final_blocks, sea_by_cell=sea_by_cell, donor_ref=list(donor_ref),
               changed_parts=changed_parts)


# ================================================================================================
# STAGE E -- THE DRY-RUN FILE SET (Terrain final + Sea4 + hidden water parts + ensemble aux parts +
# Donor.txt on every span block). Never writes to the game install.
# ================================================================================================
def build_file_set(built_stages: dict, full_gates: dict, footprint) -> dict:
    final_blocks = full_gates["final_blocks"]
    sea_by_cell = full_gates["sea_by_cell"]
    changed_parts = full_gates["changed_parts"]
    donor_ref = tuple(full_gates["donor_ref"])
    files = {}
    for blk in footprint:
        bx, by = blk
        parts = {"Terrain": final_blocks[blk], "Sea4": sea_by_cell[blk]["sea4"]}
        for p in ("Sea1", "Sea2", "Sea3", "Sea5", "Beach1"):
            parts[p] = sea_by_cell[blk].get(p.lower()) or M.hidden_block_mesh(
                name=f"Block[{bx}][{by}] {p}", disc=1, x=bx, y=by)
        for p in IN.ENSEMBLE_PARTS:                          # Object, Falls, River, RiverJoint
            carried = changed_parts.get(blk, {}).get(p)
            parts[p] = carried if carried is not None else M.hidden_block_mesh(
                name=f"Block[{bx}][{by}] {p}", disc=1, x=bx, y=by)
        files[blk] = parts
    donors = {blk: donor_ref for blk in footprint}
    return {"files": files, "donors": donors}


def write_dry_run(fileset: dict, footprint) -> dict:
    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    written = []
    for blk in sorted(footprint):
        bx, by = blk
        parts = fileset["files"][blk]
        for part_name, bm in parts.items():
            rel = M.override_relpath(1, bx, by, "0_1", part_name)
            path = OUT_ROOT / rel
            M.write_ff9mesh(bm, path)
            written.append(str(path))
        donor = fileset["donors"][blk]
        rel_d = M.donor_sidecar_relpath(1, bx, by, "0_1")
        dpath = OUT_ROOT / rel_d
        dpath.parent.mkdir(parents=True, exist_ok=True)
        dpath.write_text(f"{donor[0]},{donor[1]}", encoding="utf-8")
        written.append(str(dpath))
    manifest = {"mod_folder": MOD, "written": written, "footprint": [list(b) for b in footprint],
               "note": "dry-run file set -- would-be-deployed bytes under out/rung_d/"
                       f"{MOD}/... , RELATIVE-equivalent to <game>/{MOD}/... under --apply "
                       "(never invoked this session)."}
    (OUT_DIR / "rung_d_build_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    log(f"\nDRY-RUN file set: {len(written)} file(s) -> {OUT_ROOT}")
    return manifest


# ================================================================================================
# --apply / --revert -- OWNER-GATED. Present for completeness (the redress-script convention the
# task specifies) but NEVER invoked by this session; the harness that runs this script is dry-run
# only by hard rule (CLAUDE.md Hard Constraints, the task's own HARD SAFETY RULES).
# ================================================================================================
def apply_deploy(fileset: dict, footprint, n_fail: int, game_root: Path) -> int:
    if n_fail:
        sys.exit(f"REFUSING --apply: {n_fail} gate(s) failed")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = BACKUP_ROOT / f"rung-d-build.{ts}"
    pre_existing = []
    for blk in footprint:
        for part_name in fileset["files"][blk]:
            p = game_root / MOD / M.override_relpath(1, blk[0], blk[1], "0_1", part_name)
            if p.exists():
                pre_existing.append(p)
        dp = game_root / MOD / M.donor_sidecar_relpath(1, blk[0], blk[1], "0_1")
        if dp.exists():
            pre_existing.append(dp)
    if pre_existing:
        backup_root.mkdir(parents=True, exist_ok=True)
        try:
            for p in pre_existing:
                rel = p.relative_to(game_root)
                dst = backup_root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
        except Exception as e:
            sys.exit(f"REFUSING to write: backup of {len(pre_existing)} pre-existing file(s) "
                     f"failed ({e}); nothing was touched.")
        print(f"backed up {len(pre_existing)} pre-existing file(s) -> {backup_root} "
             f"(unexpected -- MOD-OVERWRITE should have shown 0)")
    else:
        print("0 pre-existing target files (expected); no backup needed.")

    written = []
    for blk in sorted(footprint):
        for part_name, bm in fileset["files"][blk].items():
            written.append(M.deploy_override(bm, mod_folder=MOD, game=game_root, part=part_name))
        donor = fileset["donors"][blk]
        written.append(M.deploy_donor_sidecar(donor[0], donor[1], mod_folder=MOD, disc=1,
                                              x=blk[0], y=blk[1], game=game_root))
    mirror_summary = DM.auto_mirror(written, mod_folder=MOD)
    print(f"deployed {len(written)} file(s); disc-4 mirror: {mirror_summary}")
    manifest = {"mod_folder": MOD, "written": [str(p) for p in written],
               "pre_existing_backed_up": [str(p) for p in pre_existing], "backup_dir": str(backup_root),
               "mirror_summary": mirror_summary, "footprint": [list(b) for b in footprint]}
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    (BACKUP_ROOT / f"rung-d-build.{ts}.manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"revert manifest -> rung-d-build.{ts}.manifest.json (pass its stem to --revert)")
    return 0


def revert_deploy(name: str) -> int:
    manifest_path = BACKUP_ROOT / f"{name}.manifest.json"
    if not manifest_path.is_file():
        sys.exit(f"no such manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    game_root = Path(RDL._cfg.find_game_path(None))
    backup_root = Path(manifest["backup_dir"])
    backed_up = {str(Path(p)) for p in manifest.get("pre_existing_backed_up", [])}
    n_restored = n_deleted = 0
    for p_str in manifest["written"]:
        p = Path(p_str)
        if p_str in backed_up and backup_root.is_dir():
            rel = p.relative_to(game_root)
            src = backup_root / rel
            if src.is_file():
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, p)
                n_restored += 1
                continue
        if p.exists():
            p.unlink()
            n_deleted += 1
    print(f"reverted: {n_restored} file(s) restored from backup, {n_deleted} brand-new file(s) deleted")
    return 0


# ================================================================================================
# main
# ================================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write + backup + mirror (OWNER-GATED; never pass this in an agent session)")
    ap.add_argument("--revert", metavar="NAME", default=None,
                    help="revert a prior --apply via its manifest stem (rung-d-build.<ts>)")
    args = ap.parse_args()

    if args.revert:
        return revert_deploy(args.revert)

    game_root = Path(RDL._cfg.find_game_path(None))
    built_stages = run_layout_stages(game_root)
    repro = check_reproduces_recorded_layout(built_stages)
    ratio = stage_ratio_corrected(built_stages)
    quart = stage_quartile_density(built_stages)
    full_gates = stage_full_gates(built_stages, game_root)
    footprint = built_stages["s0"]["footprint"]
    fileset = build_file_set(built_stages, full_gates, footprint)
    manifest = write_dry_run(fileset, footprint)

    n_fail = full_gates["n_failed"] + (0 if repro["ok"] else 1)
    report = {
        "site": {"center": list(RDL.BENCH_CENTER), "radius": RDL.BENCH_RADIUS, "seed": RDL.BENCH_SEED,
                "donor": RDL.HORSESHOE_DONOR},
        "reproduces_recorded_layout": repro,
        "stage0_site_gates": built_stages["s0"]["gates"],
        "stage1_anchor_reproduction": built_stages["s1"]["reproduction"],
        "stage2_rim_termini": {"term_a": list(built_stages["s2"]["term_a"]),
                               "term_b": list(built_stages["s2"]["term_b"]),
                               "chord": round(built_stages["s2"]["chord"], 2)},
        "stage3_retile_stats": built_stages["s3"]["retile_stats"],
        "stage4_dressing": {"n_planned": len(built_stages["s4"]["dress"]["plan"]),
                            "n_writes": len(built_stages["s4"]["dress"]["writes"])},
        "stage5_coast_standoff": built_stages["s5"],
        "ratio_corrected": ratio,
        "quartile_density": quart,
        "full_gate_suite": {"gates": full_gates["gates"], "n_gates": full_gates["n_gates"],
                            "n_failed": full_gates["n_failed"]},
        "orphan_gate": full_gates["orphan"],
        "wang_gate": full_gates["wang"],
        "mod_overwrite_gate": full_gates["mod_overwrite"],
        "n_total_failed_gates": n_fail,
        "file_set_manifest": manifest,
        "apply_note": "NOT executed this session -- dry-run only, per HARD SAFETY RULES; --apply/"
                      "--revert exist in this script for the owner's hand.",
    }
    OUT_JSON.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log(f"\n-> {OUT_JSON}")
    log(f"\n=== TOTAL: {n_fail} failing check(s) across reproduction + full gate suite ===")
    log("READ-ONLY throughout -- zero writes to the game install; this run never deployed.")

    if args.apply:
        return apply_deploy(fileset, footprint, n_fail, game_root)

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
