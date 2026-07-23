"""RUNG D SITE SCOUT -- read-only scan of the full 24x20 overworld block grid for open-ocean
pockets that can host an r70+-class world-island bench carrying the horseshoe massif ensemble
PLUS a designed-in grass|desert composition.

READ-ONLY: never writes to the game install. Only reads real block occupancy via
`world.island._real_block_parts` (the same function `landmass()`'s OPEN-OCEAN TARGET gate uses)
and cross-references the live FF9CustomMap-world override tree (also read-only, via a glob).

Run from ff9mapkit/ (the CLAUDE.md convention: run kit code with the local pkg on sys.path).
"""
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config as _cfg  # noqa: E402
from ff9mapkit.world.island import _real_block_parts, BLOCK  # noqa: E402
from ff9mapkit.world.mesh import GRID_COLS, GRID_ROWS  # noqa: E402

OUT = Path(__file__).resolve().parent / "out" / "rung_d"
OUT.mkdir(parents=True, exist_ok=True)


def scan_occupancy(game_root):
    """{(bx,by): {part: tri_count}} for every block with ANY real stock geometry (disc 1)."""
    occ = {}
    for bx in range(GRID_COLS):
        for by in range(GRID_ROWS):
            parts = _real_block_parts((bx, by), disc=1, lod="0_1", game=game_root)
            if parts:
                occ[(bx, by)] = parts
    return occ


def live_deployed_blocks(game_root):
    """The FF9CustomMap-world mod folder's currently-overridden (bx,by) set, ground-truth from
    the live install's own file tree (read-only glob, no interpretation of memory prose)."""
    mod_dir = Path(game_root) / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1"
    blocks = set()
    for p in mod_dir.rglob("Block*.ff9mesh"):
        name = p.name  # "Block[BX][BY] Part.ff9mesh"
        inner = name[len("Block["):]
        bx_s, rest = inner.split("]", 1)
        by_s = rest.split("[", 1)[1].split("]", 1)[0]
        blocks.add((int(bx_s), int(by_s)))
    return blocks


def find_open_rects(occupied, deployed, min_w, min_h, max_bx=GRID_COLS, max_by=GRID_ROWS):
    """Every MAXIMAL axis-aligned rect anchored at each free (bx0,by0) with running width
    >= min_w and total height >= min_h, fully inside the grid, with EVERY cell both
    real-open-ocean (not in `occupied`) AND not already mod-deployed. Reports the (w,h) pair
    actually achieved AT the tallest valid extent, not the width of a later failing row."""
    free = lambda bx, by: (0 <= bx < GRID_COLS and 0 <= by < GRID_ROWS
                            and (bx, by) not in occupied and (bx, by) not in deployed)
    rects = []
    for bx0 in range(GRID_COLS):
        for by0 in range(GRID_ROWS):
            if not free(bx0, by0):
                continue
            running_w = None
            best = None  # (w, h) of the largest-area valid rect seen growing down from by0
            by = by0
            while by < GRID_ROWS:
                row_w = 0
                bx = bx0
                while bx < GRID_COLS and free(bx, by):
                    row_w += 1
                    bx += 1
                running_w = row_w if running_w is None else min(running_w, row_w)
                if running_w < min_w:
                    break
                h = by - by0 + 1
                if running_w >= min_w and h >= min_h:
                    if best is None or running_w * h > best[0] * best[1]:
                        best = (running_w, h)
                by += 1
            if best is not None:
                rects.append({"anchor": [bx0, by0], "w": best[0], "h": best[1]})
    return rects


def main():
    game_root = _cfg.find_game_path(None)
    print(f"[scan] game root: {game_root}")
    occupied = scan_occupancy(game_root)
    deployed = live_deployed_blocks(game_root)
    print(f"[scan] real stock content in {len(occupied)}/480 blocks")
    print(f"[scan] live FF9CustomMap-world override blocks: {len(deployed)} -> {sorted(deployed)}")

    overlap = set(occupied) & deployed
    print(f"[scan] deployed blocks that ALSO carry real stock geometry underneath (expected -- "
          f"islands sit on a real prefab's coordinate slot only if THAT slot itself was empty; "
          f"a non-empty overlap here would mean a deployed override sits on real land) = {len(overlap)}")
    if overlap:
        print(f"       overlap set: {sorted(overlap)}")

    # candidate rect sizes: the horseshoe's 2026-07-15 bench was described as "10-block span"
    # inside an r72 mint's 4x3 footprint; comp[1]'s dunes carry used 3x3=9; comp20 used 2x2.
    # Scan a ladder of sizes so the picker can trade bench radius against site scarcity.
    results = {}
    for (w, h) in [(5, 4), (4, 4), (4, 3), (3, 3)]:
        rects = find_open_rects(occupied, deployed, w, h)
        results[f"{w}x{h}"] = rects
        print(f"[scan] open {w}x{h}+ pockets (both real-ocean AND un-deployed): {len(rects)}")

    payload = {
        "grid": [GRID_COLS, GRID_ROWS],
        "block_size_u": BLOCK,
        "n_occupied_real_blocks": len(occupied),
        "occupied_blocks": sorted([list(b) for b in occupied]),
        "deployed_blocks_live": sorted([list(b) for b in deployed]),
        "overlap_deployed_and_real": sorted([list(b) for b in overlap]),
        "open_rects_by_size": results,
    }
    out_path = OUT / "site_scan.json"
    out_path.write_text(json.dumps(payload, indent=1))
    print(f"[scan] wrote {out_path}")


if __name__ == "__main__":
    main()
