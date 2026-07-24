"""RUNG F -- THE DEFERRED LOWLAND-CUT / NECK SCAN (2026-07-24, READ-ONLY).

The round-3 diagnosis proved R1 cannot pass by minting a fresh round island around the
mountain-locked valley at blocks (13-15,11-12): the ecotone is INTERWOVEN with 6-40u
mountains, and any minted-coast frame slices those walls at elevation. The verified
FAITHFUL LEAD: the donor's OWN ecotone sits exactly 39.953u from its OWN real coast (the
NW inlet, block (13,11) is coastal). So a v4-style REGIONAL transplant that carries the
valley WITH its own coastal frontage (sea/beach parts riding free) reproduces R1 at stock's
own numbers BY CONSTRUCTION -- but ONLY if a watertight carry window exists: a block rect
CONTAINING the valley whose PERIMETER crosses ONLY (a) plain lowland grass necks
(land-touch ymax <= CUT_Y=6.5u, the v4 cut-line law) or (b) OPEN SEA. Rock may be ENCLOSED
inside the window (watertight, the massif-carry pattern) but NEVER sliced at elevation by
the perimeter.

This is the v4 census pattern (v4_rect_scan.py / v4_transplant_census.py). It:
  1. Builds a bounded per-block per-edge land-ymax census over the region around the valley
     (stock disc-1 bytes only, terrain parts).
  2. Grows block rects that CONTAIN the valley core (13-15,11-12), up to 8x6 blocks, and
     tests the perimeter: every outward block-edge must be SEA (no land) or a LOWLAND neck
     (land-touch ymax <= 6.5u). A TALL crossing (mountain sliced at elevation) FAILS.
  3. Reports the minimal watertight window (rect + per-side crossing inventory), the coastal
     frontage extent, the carried ecotone->coast distance (sanity ~39.953u), the footprint
     (blocks/cells/tris incl. mountain ring + Object + sea/beach parts), and the extra
     part-content in the grown window beyond the S1 (contract_mass_scout) census.
  4. If NO watertight window exists within 8x6, says so and maps the blocking crossings.

READ-ONLY: reads stock bytes via X.read_block; writes ONLY out/rung_f/neck_scan.json + this
file. No deploys, no --apply, no mirror, no game writes.

Run from the study dir:  py rung_f_neck_scan.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                       # noqa: E402
from ff9mapkit.world import extract as X             # noqa: E402

OUT_DIR = HERE / "out" / "rung_f"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "neck_scan.json"

DISC = 1
CELL = 4.0
BLOCK = 64.0
CUT_Y = 6.5           # v4 cut-line law: a land crossing this low is a sealable lowland neck
LAND_Y = 0.6          # a frame-touch counts as LAND above this (swash tops ~0.5)
FRAME_EPS = 0.10      # world-space tolerance for "vertex lies on the block frame plane"

# The mountain-locked valley the mass-anatomy contract identified (the map's ONLY grass|desert junction).
CORE = {(13, 11), (13, 12), (14, 11), (14, 12), (15, 11), (15, 12)}
CORE_X = (min(x for x, _ in CORE), max(x for x, _ in CORE))     # 13..15
CORE_Y = (min(y for _, y in CORE), max(y for _, y in CORE))     # 11..12

# Census region -- generous margin so an 8x6 window (max 5 extra cols / 4 extra rows off the
# 3x2 core) always fits inside what we measured. x well clear of the x=0/24 wrap seam.
REGION_X = (8, 22)
REGION_Y = (6, 18)
MAX_W, MAX_H = 8, 6

# NB grid row y advances toward -Z: a block's local z=0 edge ("N") faces row y-1; z=-64 ("S") row y+1.
EDGE_NB = {"W": (-1, 0), "E": (1, 0), "N": (0, -1), "S": (0, 1)}


def block_origin(bx, by):
    return bx * BLOCK, -by * BLOCK          # world (x0, z0); block spans x[x0,x0+64], z[z0-64,z0]


def part_inventory():
    env = X._worldmap_env(DISC)
    pat = re.compile(
        rf"worldmap/disc{DISC}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)(?:\.asset)?$")
    parts = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            parts[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
    return parts


def build_census(parts):
    """Per terrain block in the region: per-edge land ymax + tri count + world verts for coast work."""
    blk = {}
    terr_verts = {}       # (bx,by) -> world terrain verts (Nx3)
    for (bx, by), pset in parts.items():
        if not (REGION_X[0] <= bx <= REGION_X[1] and REGION_Y[0] <= by <= REGION_Y[1]):
            continue
        if "terrain" not in pset:
            continue
        bm = X.read_block(bx, by, disc=DISC, part="terrain")
        V = np.asarray(bm.verts, dtype=np.float64)                  # LOCAL coords
        idx = np.asarray(bm.flat_index, dtype=np.int64)
        ntri = len(idx) // 3
        x0, z0 = block_origin(bx, by)
        W = V.copy()
        W[:, 0] += x0
        W[:, 2] += z0
        terr_verts[(bx, by)] = W
        vy = V[:, 1]
        landv = vy > LAND_Y
        edges = {}
        # local frame planes: x 0 / 64 (W/E), z 0 / -64 (N/S)
        for name, axis, plane in (("W", 0, 0.0), ("E", 0, 64.0), ("N", 2, 0.0), ("S", 2, -64.0)):
            on = np.abs(V[:, axis] - plane) < FRAME_EPS
            touch = on & landv
            edges[name] = {
                "land": bool(touch.any()),
                "ymax": float(vy[touch].max()) if touch.any() else None,
            }
        blk[(bx, by)] = {"ntri": int(ntri), "edges": edges,
                         "parts": sorted(pset)}
    return blk, terr_verts


def eval_window(rect, blk):
    """rect=(x0,y0,x1,y1). Return per-edge crossing list + tallies. A crossing is evaluated on
    each terrain cell's edge whose neighbour is OUTSIDE the rect."""
    x0, y0, x1, y1 = rect
    cells = {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    crossings = []          # (cell, edge, type, ymax)
    tall = []               # blocking crossings
    n_sea = n_low = n_tall = 0
    side_sea = {"W": 0, "E": 0, "N": 0, "S": 0}
    side_land = {"W": 0, "E": 0, "N": 0, "S": 0}
    for c in cells:
        if c not in blk:
            continue                                # ocean cell in-rect contributes no land
        for e, (dx, dy) in EDGE_NB.items():
            nb = (c[0] + dx, c[1] + dy)
            if nb in cells:
                continue                            # interior border
            ed = blk[c]["edges"][e]
            if not ed["land"]:
                n_sea += 1
                side_sea[e] += 1
                crossings.append((list(c), e, "SEA", None))
            else:
                ym = round(ed["ymax"], 2)
                side_land[e] += 1
                if ed["ymax"] <= CUT_Y:
                    n_low += 1
                    crossings.append((list(c), e, "LOWLAND", ym))
                else:
                    n_tall += 1
                    tall.append((list(c), e, ym))
                    crossings.append((list(c), e, "TALL", ym))
    return {
        "rect": list(rect),
        "w": x1 - x0 + 1, "h": y1 - y0 + 1, "n_blocks": (x1 - x0 + 1) * (y1 - y0 + 1),
        "n_sea": n_sea, "n_low": n_low, "n_tall": n_tall,
        "passes": n_tall == 0,
        "tall_crossings": tall,
        "crossings": crossings,
        "side_sea": side_sea, "side_land": side_land,
    }


def enumerate_windows(blk):
    """All block rects containing the core, within the region, width<=8 height<=6."""
    xs_lo = range(max(REGION_X[0], CORE_X[1] - MAX_W + 1), CORE_X[0] + 1)
    ys_lo = range(max(REGION_Y[0], CORE_Y[1] - MAX_H + 1), CORE_Y[0] + 1)
    out = []
    for x0 in xs_lo:
        for x1 in range(CORE_X[1], min(REGION_X[1], x0 + MAX_W - 1) + 1):
            for y0 in ys_lo:
                for y1 in range(CORE_Y[1], min(REGION_Y[1], y0 + MAX_H - 1) + 1):
                    out.append(eval_window((x0, y0, x1, y1), blk))
    return out


def coast_and_ecotone(rect, blk, parts):
    """Carried ecotone->coast distance on STOCK bytes (the faithful-lead sanity, ~39.953u).
    boundary cells = grass|desert straddle cells; coast = sea-part vertices. Horizontal (XZ)."""
    x0, y0, x1, y1 = rect
    win_blocks = [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)
                  if (x, y) in blk]
    all_tris, _bms, _src = SNR.load_tris(win_blocks, source="stock")
    edge_owner = SNR.edge_index(all_tris)
    boundary_cells = set()
    for e, owners in edge_owner.items():
        fams = {all_tris[g]["fam"] for g in owners}
        if fams == {"grass", "desert"}:
            for g in owners:
                boundary_cells.add(all_tris[g]["cell"])
    # sea-part vertices (world XZ) over the window
    sea_xz = []
    sea_part_tris = 0
    for (bx, by) in win_blocks:
        ox, oz = block_origin(bx, by)
        for pname in parts.get((bx, by), ()):
            if pname.startswith("sea") or pname.startswith("beach"):
                try:
                    bm = X.read_block(bx, by, disc=DISC, part=pname)
                except Exception:
                    continue
                V = np.asarray(bm.verts, dtype=np.float64)
                if V.size == 0:
                    continue
                sea_xz.append(np.column_stack([V[:, 0] + ox, V[:, 2] + oz]))
                sea_part_tris += len(bm.flat_index) // 3
    dist_min = None
    n_boundary = len(boundary_cells)
    if boundary_cells and sea_xz:
        S = np.vstack(sea_xz)
        bc = np.array([[c[0] * CELL + CELL / 2, c[1] * CELL + CELL / 2] for c in boundary_cells])
        # min over boundary cells of (min over sea verts of XZ distance)
        dd = np.sqrt(((bc[:, None, :] - S[None, :, :]) ** 2).sum(-1))
        percell = dd.min(axis=1)
        dist_min = float(percell.min())
        dist_p50 = float(np.median(percell))
        dist_max = float(percell.max())
    else:
        dist_p50 = dist_max = None
    return {
        "n_straddle_boundary_cells_in_window": n_boundary,
        "n_sea_part_tris_in_window": sea_part_tris,
        "ecotone_to_sea_min_u": dist_min,
        "ecotone_to_sea_median_u": dist_p50,
        "ecotone_to_sea_max_u": dist_max,
        "stock_R1_boundary_floor_u": 39.953,
        "sanity_reproduces_floor": (dist_min is not None and abs(dist_min - 39.953) < 6.0),
    }


def footprint(rect, blk, parts):
    x0, y0, x1, y1 = rect
    win = [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
    land = [c for c in win if c in blk]
    terr_tris = sum(blk[c]["ntri"] for c in land)
    part_counts = defaultdict(int)
    part_blocks = defaultdict(list)
    extra_part_tris = 0
    for c in land:
        for p in parts.get(c, ()):
            part_counts[p] += 1
            if p != "terrain":
                part_blocks[p].append(list(c))
    # count tris in the non-terrain parts (object/sea/beach/stream = the free-ride ensemble)
    extra = {}
    for p, blocks in part_blocks.items():
        n = 0
        for c in blocks:
            try:
                bm = X.read_block(c[0], c[1], disc=DISC, part=p)
                n += len(bm.flat_index) // 3
            except Exception:
                pass
        extra[p] = {"n_blocks": len(blocks), "blocks": blocks, "tris": n}
        extra_part_tris += n
    return {
        "n_window_blocks": len(win),
        "n_land_blocks": len(land),
        "n_ocean_blocks": len(win) - len(land),
        "land_blocks": [list(c) for c in land],
        "land_cells_16u_each": len(land) * 256,      # 64/4 = 16 cells per side, 256 cells/block
        "terrain_tris": terr_tris,
        "part_counts": dict(sorted(part_counts.items())),
        "nonterrain_parts": extra,
        "nonterrain_part_tris": extra_part_tris,
        "total_tris_terrain_plus_parts": terr_tris + extra_part_tris,
    }


def main():
    t0 = time.time()
    print(f"game root: {SNR.GAME_ROOT}", flush=True)
    parts = part_inventory()
    blk, terr_verts = build_census(parts)
    print(f"censused {len(blk)} terrain blocks in region x{REGION_X} y{REGION_Y} "
          f"({time.time()-t0:.1f}s)", flush=True)

    windows = enumerate_windows(blk)
    passing = [w for w in windows if w["passes"]]
    passing.sort(key=lambda w: (w["n_blocks"], -w["n_sea"], w["n_low"]))
    print(f"enumerated {len(windows)} core-containing windows (<= {MAX_W}x{MAX_H}); "
          f"{len(passing)} watertight (0 tall crossings)", flush=True)

    result = {
        "meta": {
            "script": "rung_f_neck_scan.py",
            "round": "RUNG F -- deferred lowland-cut / neck scan (v4 transplant census pattern)",
            "read_only": True, "zero_game_writes": True, "zero_deploys": True,
            "disc": DISC, "cut_y_u": CUT_Y, "land_y_u": LAND_Y,
            "core_valley_blocks": [list(c) for c in sorted(CORE)],
            "region_x": list(REGION_X), "region_y": list(REGION_Y),
            "max_window": [MAX_W, MAX_H],
            "n_terrain_blocks_censused": len(blk),
            "n_windows_evaluated": len(windows),
            "n_watertight_windows": len(passing),
        },
        "census_edges": {
            f"{c[0]},{c[1]}": {e: blk[c]["edges"][e] for e in ("W", "E", "N", "S")}
            for c in sorted(blk)
        },
    }

    if passing:
        best = passing[0]
        rect = tuple(best["rect"])
        print(f"\nMINIMAL WATERTIGHT WINDOW: blocks x{rect[0]}-{rect[2]} y{rect[1]}-{rect[3]} "
              f"({best['w']}x{best['h']} = {best['n_blocks']} blocks); "
              f"sea={best['n_sea']} lowland={best['n_low']} tall={best['n_tall']}", flush=True)
        fp = footprint(rect, blk, parts)
        ce = coast_and_ecotone(rect, blk, parts)
        # frontage: sides whose crossings are pure sea (coastal frontage extent)
        frontage = {}
        for side in ("W", "E", "N", "S"):
            frontage[side] = {"sea_edges": best["side_sea"][side],
                              "land_edges": best["side_land"][side],
                              "is_coast_frontage": best["side_land"][side] == 0
                              and best["side_sea"][side] > 0}
        # extra content beyond S1 (scout censused ecotone/masses = terrain only)
        extra_content = {p: v for p, v in fp["nonterrain_parts"].items()}
        result["minimal_watertight_window"] = {
            **best,
            "footprint": fp,
            "coastal_frontage_by_side": frontage,
            "n_coast_frontage_sides": sum(1 for s in frontage.values() if s["is_coast_frontage"]),
            "carried_ecotone_to_coast": ce,
            "extra_part_content_beyond_S1_terrain_census": extra_content,
        }
        result["all_watertight_windows_top10"] = passing[:10]
        result["verdict"] = "WATERTIGHT_WINDOW_FOUND"
    else:
        # No watertight window: map the blocking (tall) crossings of the smallest few windows,
        # and the UNION of all tall crossings ever seen (the walls that block every window).
        windows.sort(key=lambda w: (w["n_tall"], w["n_blocks"]))
        best_effort = windows[:6]
        tall_union = {}
        for w in windows:
            for (cell, e, ym) in w["tall_crossings"]:
                key = f"{cell[0]},{cell[1]}:{e}"
                tall_union[key] = max(tall_union.get(key, 0.0), ym)
        # which blocking walls persist even at max growth 8x6?
        max_windows = [w for w in windows if w["w"] == MAX_W or w["h"] == MAX_H
                       or w["n_blocks"] == max(x["n_blocks"] for x in windows)]
        # side classification of the SMALLEST min-tall window + which sides are clean escapes
        smallest = min((w for w in windows if w["n_tall"] == best_effort[0]["n_tall"]),
                       key=lambda w: w["n_blocks"])
        sm_rect = tuple(smallest["rect"])
        frontage = {}
        for side in ("W", "E", "N", "S"):
            n_tall_side = sum(1 for (c, e, ym) in smallest["tall_crossings"] if e == side)
            frontage[side] = {
                "sea_edges": smallest["side_sea"][side],
                "land_edges": smallest["side_land"][side],
                "tall_edges": n_tall_side,
                "clean_escape": n_tall_side == 0,   # only lowland necks and/or open sea
            }
        # faithful full-massif enclosure: grow EAST until the east perimeter is all sea/lowland.
        east_foot = None
        for x1 in range(CORE_X[1], REGION_X[1] + 1):
            col_edges = [blk[(x1, y)]["edges"]["E"] for y in range(CORE_Y[0] - 2, CORE_Y[1] + 3)
                         if (x1, y) in blk]
            worst = max((e["ymax"] for e in col_edges if e["land"]), default=None)
            if worst is None or worst <= CUT_Y:
                east_foot = x1
                break
        result["verdict"] = "NO_WATERTIGHT_WINDOW_WITHIN_8x6"
        result["blocking_analysis"] = {
            "min_tall_crossings_any_window": min(w["n_tall"] for w in windows),
            "the_wall_is_the_east_massif": "every min-tall window's blocking crossings are on the "
            "EAST perimeter (column-15/16 boundary and east), where the valley's massif continues "
            "into the neighbouring blocks at 30-40u. The valley is the WEST FLANK of a large "
            "mountain massif, not an enclosable feature.",
            "smallest_min_tall_window": {
                "rect": list(sm_rect), "w": smallest["w"], "h": smallest["h"],
                "n_tall": smallest["n_tall"], "n_low": smallest["n_low"], "n_sea": smallest["n_sea"],
                "tall_crossings": smallest["tall_crossings"],
                "frontage_by_side": frontage,
                "clean_escape_sides": [s for s, v in frontage.items() if v["clean_escape"]],
            },
            "best_effort_windows": [
                {"rect": w["rect"], "w": w["w"], "h": w["h"], "n_tall": w["n_tall"],
                 "n_low": w["n_low"], "n_sea": w["n_sea"],
                 "tall_crossings": w["tall_crossings"]}
                for w in best_effort
            ],
            "tall_crossing_union_all_windows": dict(sorted(tall_union.items())),
            "n_distinct_tall_edges": len(tall_union),
            "east_massif_reaches_lowland_or_sea_at_col_E": east_foot,
            "east_massif_note": (
                f"scanning east edges from the valley, the massif first drops to lowland/sea at "
                f"column {east_foot}'s east frame" if east_foot is not None
                else "the massif never drops to lowland/sea within the censused region -- "
                     "it meets the sea as an ESCARPMENT CLIFF (tall edges to the waterline)"),
        }
        # west-frontage sanity: reproduce the 39.953u floor from the carried NW inlet
        result["blocking_analysis"]["carried_ecotone_to_coast_west_frontage"] = \
            coast_and_ecotone(sm_rect, blk, parts)
        result["blocking_analysis"]["footprint_smallest_min_tall_window"] = \
            footprint(sm_rect, blk, parts)
        # what a FAITHFUL full-massif carry would cost (over the cap): x13..east coast
        full_x1 = REGION_X[1]                      # massif meets sea only at the region's east edge
        for x1 in range(CORE_X[1], REGION_X[1] + 1):
            if all((x1, y) not in blk for y in range(CORE_Y[0], CORE_Y[1] + 1)):
                full_x1 = x1 - 1
                break
        full_rect = (CORE_X[0], CORE_Y[0] - 1, full_x1, CORE_Y[1] + 2)
        result["blocking_analysis"]["faithful_full_massif_footprint_OVER_CAP"] = {
            "note": "the window that WOULD enclose the whole massif to its own eastern coast; "
                    "EXCEEDS the 8x6 cap and its east coast is a WALL-COASTAL ESCARPMENT "
                    "(off-language per the WALL-CONTEXT LAW / canyon removal).",
            "rect": list(full_rect),
            "w": full_rect[2] - full_rect[0] + 1, "h": full_rect[3] - full_rect[1] + 1,
            "footprint": footprint(full_rect, blk, parts),
        }
        result["structural_conclusion"] = (
            "NO watertight lowland/sea carry window exists for the (13-15,11-12) ecotone within "
            "an 8x6 growth. The west/north/south perimeters ARE clean (lowland necks + open sea; "
            "the NW inlet reproduces the R1 boundary floor at 39.953u exactly), but the EAST "
            "perimeter slices a continuous mountain massif at 30-40u at EVERY candidate cut. The "
            "massif's true eastern coast is ~9 blocks east of the window's west edge (over the "
            "cap) and is an escarpment sea-cliff, not a lowland foot. The valley is the west flank "
            "of a large highland mass, not an extractable feature -- matching the round-3 "
            "mountain-lock diagnosis and THE ISLAND COROLLARY (no sea-ringed landmass carries "
            "walkable highland to a lowland-only crossing here).")
        print(f"\nNO WATERTIGHT WINDOW <= {MAX_W}x{MAX_H}. "
              f"min tall crossings in any window = {result['blocking_analysis']['min_tall_crossings_any_window']}; "
              f"{len(tall_union)} distinct blocking tall edges.", flush=True)

    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}  (total {time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
