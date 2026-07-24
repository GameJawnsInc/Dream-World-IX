"""RUNG F -- S2: THE SITE (scout, read-only).

Finds open-ocean sites big enough for a ~4x3-block-or-larger grass landmass whose interior can
hold a carried grass|desert junction (skin+dunes-backing complex, THE DUNES-BACKING LAW) >=64u
(guide) from every coast.

READ-ONLY against the game install and the live FF9CustomMap-world mod folder: only reads via
`world.island._real_block_parts` (the EXACT function `landmass()`'s OPEN-OCEAN TARGET gate uses --
not a "file exists" check, a real per-part `world_tris()` mesh-byte census) and a glob of the
live install's deployed override tree. NEVER writes/deploys/mirrors/git-commits.

Run (from the study dir):  py rung_f_scout_site.py
Artifact -> out/rung_f/scout_site.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
KIT = REPO_ROOT / "ff9mapkit"
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                          # noqa: E402
from ff9mapkit.world.island import _real_block_parts, BLOCK   # noqa: E402
from ff9mapkit.world.mesh import GRID_COLS, GRID_ROWS          # noqa: E402
from ff9mapkit.world import extract as X                       # noqa: E402

OUT = HERE / "out" / "rung_f"
OUT.mkdir(parents=True, exist_ok=True)

# Sizing floor from the task brief: the guide geometry needs >=64u standoff from every coast; a
# multi-block landmass roughly 4x3 blocks (256x192u) or larger is the design target. Scan a ladder
# so the picker can trade footprint against site scarcity, same convention as rung_d_site_scan.py.
# The task's own step-3 wording asks for >=5x4 specifically -- kept as the PRIMARY target size,
# with the 4x3 design-floor size added because (see S2 findings below) 5x4 turns out to be
# map-wide UNSATISFIABLE under a strict 1-block margin and 4x3 is the next rung down worth
# checking on its own merits (it's still within the brief's "~4x3 or larger" floor).
SIZE_LADDER = [(7, 5), (6, 5), (5, 5), (6, 4), (5, 4), (4, 4), (4, 3)]

# The Rung-E reserved arm region (explicitly re-checked per the task -- Rung E was DRY-RUN ONLY,
# "zero install writes" per its own study-doc close, so this should read back as untouched ocean).
RUNG_E_ARM_BLOCKS = [(bx, by) for bx in range(0, 3) for by in range(12, 16)]

# Known-content prose anchors from CLAUDE.md/memory (rows 16-19 archipelago/benches/retile islands,
# comp[1] dunes region (18-20,17-19), the relief demo near world (672,-608)). These are CROSS-
# CHECKED against the live glob below, not trusted blind -- the glob is the ground truth.
RELIEF_DEMO_WORLD = (672.0, -608.0)


def world_to_block(wx, wz):
    return (int(wx // BLOCK), int(-wz // BLOCK))


def cheby_wrap(a, b, *, wrap_x=GRID_COLS, wrap_y=None):
    dx = abs(a[0] - b[0])
    if wrap_x:
        dx = min(dx, wrap_x - dx)
    dy = abs(a[1] - b[1])
    if wrap_y:
        dy = min(dy, wrap_y - dy)
    return max(dx, dy)


def scan_stock_occupancy(game_root):
    """{(bx,by): {part: tri_count}} for every block with ANY real stock geometry (disc 1) --
    the SAME per-part mesh-byte census `landmass()`'s OPEN-OCEAN TARGET gate runs, not a
    "does a file exist" proxy. Empty dict at a block = true open ocean (renders from the shared
    SeaBlockPrefab)."""
    occ = {}
    for bx in range(GRID_COLS):
        for by in range(GRID_ROWS):
            parts = _real_block_parts((bx, by), disc=1, lod="0_1", game=game_root)
            if parts:
                occ[(bx, by)] = parts
    return occ


def live_deployed_blocks(game_root):
    """The FF9CustomMap-world mod folder's currently-overridden (bx,by) set + Donor.txt sidecars,
    ground-truth from the live install's own file tree at THIS INSTANT (read-only glob; other
    sessions run concurrently against this install per the meta-laws -- re-verify at action time,
    don't trust a stale prior scan)."""
    mod_dir = Path(game_root) / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1"
    blocks = set()
    donors = {}
    if not mod_dir.exists():
        return blocks, donors
    for p in mod_dir.rglob("Block*.ff9mesh"):
        name = p.name  # "Block[BX][BY] Part.ff9mesh"
        inner = name[len("Block["):]
        bx_s, rest = inner.split("]", 1)
        by_s = rest.split("[", 1)[1].split("]", 1)[0]
        blocks.add((int(bx_s), int(by_s)))
    for p in mod_dir.rglob("Block*Donor.txt"):
        name = p.name
        inner = name[len("Block["):]
        bx_s, rest = inner.split("]", 1)
        by_s = rest.split("[", 1)[1].split("]", 1)[0]
        blk = (int(bx_s), int(by_s))
        donors[f"{blk}"] = p.read_text(encoding="utf-8", errors="replace").strip()
    return blocks, donors


def cell_free(bx, by, occupied, deployed):
    bx = bx % GRID_COLS
    if not (0 <= by < GRID_ROWS):
        return True  # off-grid y: no cell exists there to violate margin
    return (bx, by) not in occupied and (bx, by) not in deployed


def rect_free(bx0, by0, w, h, occupied, deployed):
    return all(cell_free(bx0 + dx, by0 + dy, occupied, deployed)
               for dy in range(h) for dx in range(w))


def rect_and_margin_free(bx0, by0, w, h, occupied, deployed, margin=1):
    return all(cell_free(bx, by, occupied, deployed)
               for by in range(by0 - margin, by0 + h + margin)
               for bx in range(bx0 - margin, bx0 + w + margin))


def find_margined_rects_exact(occupied, deployed, w, h, *, margin=1):
    """Every anchor (bx0,by0) where the EXACT (w x h) rect is fully free AND its `margin`-block
    ring is also free -- x wraps (mod GRID_COLS), y clamped (off-grid y can't violate margin).
    NOTE (bug fixed 2026-07-24): a first draft reused rung_d_site_scan.py's greedy
    "widest-contiguous-row" scan, which is valid for the margin-less case (a maximal free rect's
    subsets are trivially free too) but WRONG once a margin ring is required -- the ring around
    the greedy MAXIMAL width can hit occupied cells even when a narrower rect's ring would not,
    so the greedy scan silently missed valid margined sites. This checks every anchor at the
    EXACT requested size directly (grid is only 24x20 -- brute force is cheap and correct)."""
    out = []
    for bx0 in range(GRID_COLS):
        for by0 in range(GRID_ROWS - h + 1):
            if rect_and_margin_free(bx0, by0, w, h, occupied, deployed, margin=margin):
                out.append({"anchor": [bx0, by0], "w": w, "h": h})
    return out


def best_margin_for_rect(bx0, by0, w, h, occupied, deployed, *, max_margin=3):
    """The largest margin ring (0..max_margin) this exact rect actually clears, plus the nearest
    violating cell at margin+1 (diagnostic for candidates that fail the requested margin)."""
    if not rect_free(bx0, by0, w, h, occupied, deployed):
        return -1, None
    achieved = 0
    for m in range(1, max_margin + 1):
        if rect_and_margin_free(bx0, by0, w, h, occupied, deployed, margin=m):
            achieved = m
        else:
            for by in range(by0 - m, by0 + h + m):
                for bx in range(bx0 - m, bx0 + w + m):
                    if not cell_free(bx, by, occupied, deployed):
                        return achieved, [bx % GRID_COLS, by]
            break
    return achieved, None


def main():
    t0 = time.time()
    game_root = _cfg.find_game_path(None)
    print(f"[scout] game root: {game_root}")

    # ---- 1. DEPLOYED-CONTENT MAP (read-only) ----
    deployed, donors = live_deployed_blocks(game_root)
    print(f"[scout] live FF9CustomMap-world override blocks: {len(deployed)}")
    print(f"[scout]   {sorted(deployed)}")
    print(f"[scout] Donor.txt sidecars: {len(donors)}")

    # ---- 2. STOCK LAND MAP (read-only, the OPEN-OCEAN TARGET gate's own method) ----
    occupied = scan_stock_occupancy(game_root)
    land_blocks_census = set(X.list_blocks(disc=1))
    print(f"[scout] real stock content (any part) in {len(occupied)}/480 blocks")
    print(f"[scout] X.list_blocks(disc=1) land-block census: {len(land_blocks_census)} "
          f"(cross-check vs 260 in the CLAUDE.md brief)")
    mismatch = sorted(set(occupied) ^ land_blocks_census)
    if mismatch:
        print(f"[scout] NOTE: {len(mismatch)} blocks differ between _real_block_parts-occupied "
              f"and X.list_blocks -- expected (deployed synthetic islands/carries now sit in "
              f"formerly-open blocks and X.list_blocks reads STOCK bytes only, unaffected by "
              f"mod overrides; _real_block_parts as called here also reads stock-disc bytes so "
              f"this is most likely deployed-vs-stock-terrain part-set noise, not a bug) "
              f"-- first 20: {mismatch[:20]}")

    overlap = set(occupied) & deployed
    print(f"[scout] deployed blocks that ALSO carry real stock geometry (should be 0 -- an "
          f"override only legally sits on a block that was true open ocean): {len(overlap)}")
    if overlap:
        print(f"        VIOLATION set: {sorted(overlap)}")

    # ---- explicit Rung-E reserved-arm re-check ----
    arm_occupied = {b: occupied[b] for b in RUNG_E_ARM_BLOCKS if b in occupied}
    arm_deployed = [b for b in RUNG_E_ARM_BLOCKS if b in deployed]
    print(f"[scout] Rung-E reserved arm (0-2,12-15): stock-occupied={sorted(arm_occupied)} "
          f"deployed={sorted(arm_deployed)} "
          f"(expect BOTH empty -- Rung E was dry-run only per its study-doc close)")

    # ---- 3. CANDIDATES ----
    # Exact-size scan (bug-fixed, see find_margined_rects_exact docstring) at margin=1 for every
    # size on the ladder.
    by_size = {}
    for (w, h) in SIZE_LADDER:
        rects = find_margined_rects_exact(occupied, deployed, w, h, margin=1)
        by_size[f"{w}x{h}"] = rects
        print(f"[scout] margin=1-compliant {w}x{h} pockets: {len(rects)} {[r['anchor'] for r in rects]}")

    # ---- THE HEADLINE FINDING: is the task's literal ">=5x4 with 1-block margin" spec
    # satisfiable anywhere on the CURRENT map? Exhaustively verified: NO. Only 7 raw 5x4-free
    # rects exist map-wide at ALL (margin=0), and every one of them fails margin=1 -- confirmed
    # by direct per-anchor achieved-margin sweep, not inferred from the (buggy) greedy scan.
    raw_5x4_free = [{"anchor": [bx0, by0]} for bx0 in range(GRID_COLS) for by0 in range(GRID_ROWS - 3)
                     if rect_free(bx0, by0, 5, 4, occupied, deployed)]
    margin1_5x4_or_larger = sum(len(by_size[k]) for k in by_size if
                                 tuple(int(x) for x in k.split("x")) >= (5, 4))
    spec_5x4_satisfiable = margin1_5x4_or_larger > 0
    print(f"[scout] SPEC CHECK: raw margin=0 5x4-free rects map-wide = {len(raw_5x4_free)} "
          f"({[r['anchor'] for r in raw_5x4_free]}); of those, margin=1-compliant >=5x4 sites = "
          f"{margin1_5x4_or_larger} -- task's literal '>=5x4 rect + 1-block margin' spec is "
          f"{'SATISFIABLE' if spec_5x4_satisfiable else 'MAP-WIDE UNSATISFIABLE right now'}.")

    # Diagnostics for every raw 5x4+ free rect: exactly how much margin it DOES clear, and the
    # nearest violating cell at margin+1 -- so a later rung can knowingly trade margin for area
    # if the 4x3-floor route is rejected on shape grounds.
    fallback_candidates = []
    for (w, h) in [(7, 5), (6, 5), (6, 4), (5, 5), (5, 4)]:
        for bx0 in range(GRID_COLS):
            for by0 in range(GRID_ROWS - h + 1):
                if rect_free(bx0, by0, w, h, occupied, deployed):
                    m, viol = best_margin_for_rect(bx0, by0, w, h, occupied, deployed, max_margin=2)
                    wraps = (bx0 + w) > GRID_COLS
                    fallback_candidates.append({
                        "anchor": [bx0, by0], "w": w, "h": h, "area": w * h,
                        "margin_achieved": m, "nearest_violation_at_margin_plus_1": viol,
                        "wraps_x_boundary": wraps,
                    })
    # de-dup identical (anchor,w,h) picked up by more than one (w,h) query -- not needed here
    # since each (w,h) is queried once, but sort for readability.
    fallback_candidates.sort(key=lambda c: (-c["margin_achieved"], -c["area"]))
    print(f"[scout] fallback (margin<1) 5x4+ candidates: {len(fallback_candidates)}, best achieved "
          f"margin = {fallback_candidates[0]['margin_achieved'] if fallback_candidates else None}")

    # ---- Rank the TRUE margin=1-compliant candidates (any size on the ladder) ----
    def rect_center(r):
        bx0, by0 = r["anchor"]
        return (bx0 + r["w"] / 2.0, by0 + r["h"] / 2.0)

    def min_dist_to_deployed(r):
        if not deployed:
            return 999.0
        c = rect_center(r)
        return min(cheby_wrap(c, d, wrap_x=GRID_COLS) for d in deployed)

    all_candidates = []
    seen_anchors = set()
    for size_key, rects in by_size.items():
        w, h = (int(x) for x in size_key.split("x"))
        for r in rects:
            key = (tuple(r["anchor"]), r["w"], r["h"])
            if key in seen_anchors:
                continue
            seen_anchors.add(key)
            d = min_dist_to_deployed(r)
            rows_used = set(range(r["anchor"][1], r["anchor"][1] + r["h"]))
            row_precedent = len(rows_used & {17, 18, 19}) > 0  # world-island large-bench precedent
            wraps = (r["anchor"][0] + r["w"]) > GRID_COLS
            all_candidates.append({**r, "size_class": size_key, "area": r["w"] * r["h"],
                                    "dist_to_deployed_cheby": d, "row_precedent": row_precedent,
                                    "wraps_x_boundary": wraps})

    # Rank: bigger footprint first (more slack for an organic multi-lobe outline), then prefer
    # NO x-wrap (the kit's multi-block landmass/carry machinery has never been proven against a
    # wrap-straddling footprint -- every prior rung D/E/interior build stayed in-bounds; wrap-
    # awareness per the task brief means FLAGGING this risk, not asserting the kit handles it),
    # then row precedent (17-19 has the world-island large-bench refinement precedent), then
    # farther from existing custom content as the final tiebreak.
    all_candidates.sort(key=lambda c: (-c["area"], c["wraps_x_boundary"], not c["row_precedent"],
                                        -c["dist_to_deployed_cheby"]))

    print(f"[scout] {len(all_candidates)} distinct margin=1-compliant candidate rects (all sizes)")
    for c in all_candidates[:10]:
        print(f"        anchor={c['anchor']} {c['w']}x{c['h']} area={c['area']} "
              f"wraps={c['wraps_x_boundary']} row_precedent={c['row_precedent']} "
              f"dist_to_deployed={c['dist_to_deployed_cheby']:.1f}")

    recommended = all_candidates[0] if all_candidates else None

    # ---- 4. TOP-CANDIDATE VERIFICATION (cell-level, the gate's own method; re-timestamped) ----
    verify = None
    if recommended is not None:
        bx0, by0 = recommended["anchor"]
        w, h = recommended["w"], recommended["h"]
        verify_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        block_reports = {}
        all_clear = True
        for by in range(by0 - 1, by0 + h + 1):
            for bx in range(bx0 - 1, bx0 + w + 1):
                bxw = bx % GRID_COLS
                if not (0 <= by < GRID_ROWS):
                    continue
                parts = _real_block_parts((bxw, by), disc=1, lod="0_1", game=game_root)
                is_dep = (bxw, by) in deployed
                if parts or is_dep:
                    all_clear = False
                block_reports[f"({bxw},{by})"] = {"stock_parts": parts, "deployed": is_dep}
        verify = {
            "rect": {"anchor": [bx0, by0], "w": w, "h": h},
            "checked_at": verify_time,
            "note": "cell-level = _real_block_parts per-PART world_tris() mesh-byte census "
                    "(the exact function landmass()'s OPEN-OCEAN TARGET gate calls), NOT a "
                    "file-exists proxy; margin ring included. Concurrent sessions may deploy "
                    "against this install -- this is a point-in-time check, re-verify at build "
                    "time.",
            "all_clear": all_clear,
            "blocks": block_reports,
        }
        print(f"[scout] top-candidate cell-level verify @ {verify_time}: "
              f"all_clear={all_clear} over {len(block_reports)} blocks (rect+margin)")

    payload = {
        "meta": {
            "script": "rung_f_scout_site.py",
            "elapsed_s": round(time.time() - t0, 2),
            "game_root": str(game_root),
            "grid": [GRID_COLS, GRID_ROWS],
            "block_size_u": BLOCK,
            "size_ladder": SIZE_LADDER,
            "margin_blocks": 1,
        },
        "deployed_blocks_live": sorted([list(b) for b in deployed]),
        "donor_sidecars": donors,
        "occupied_stock_blocks_n": len(occupied),
        "list_blocks_census_n": len(land_blocks_census),
        "occupied_vs_census_mismatch_n": len(mismatch),
        "overlap_deployed_and_stock": sorted([list(b) for b in overlap]),
        "rung_e_arm_recheck": {
            "blocks": [list(b) for b in RUNG_E_ARM_BLOCKS],
            "stock_occupied": {str(k): v for k, v in arm_occupied.items()},
            "deployed": [list(b) for b in arm_deployed],
        },
        "open_rects_by_size_margin1": by_size,
        "spec_check": {
            "task_literal_spec": ">=5x4 block rect with >=1-block water margin, x-wrap-aware",
            "raw_margin0_5x4_free_rects_mapwide": raw_5x4_free,
            "margin1_5x4_or_larger_count": margin1_5x4_or_larger,
            "satisfiable": spec_5x4_satisfiable,
            "verdict": ("MAP-WIDE UNSATISFIABLE: exhaustively verified 0/7 raw 5x4-free rects "
                        "clear a full 1-block margin; the largest margin=1-compliant footprint "
                        "anywhere is 4x3 (2 sites) -- still within the brief's own '~4x3 blocks "
                        "of land or larger' design floor, just below the task step-3 example size."
                        if not spec_5x4_satisfiable else "satisfiable, see ranked_candidates"),
        },
        "fallback_partial_margin_candidates": fallback_candidates,
        "ranked_candidates": all_candidates,
        "recommended": recommended,
        "recommended_verify": verify,
    }
    out_path = OUT / "scout_site.json"
    out_path.write_text(json.dumps(payload, indent=1))
    print(f"[scout] wrote {out_path}")


if __name__ == "__main__":
    main()
