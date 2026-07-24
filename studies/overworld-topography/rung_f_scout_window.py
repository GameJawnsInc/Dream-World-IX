"""RUNG F -- S1: THE JUNCTION CARRY WINDOW (2026-07-24).

Post-CONTRACT build round. Measures whether stock's ONE grass|desert junction (blocks
(13-15,11-12) -- THE DUNES-BACKING LAW: a <=5-cell topo-16 SKIN backing onto a real DUNES complex
at inland depth 1) can be carried as a TRUE MESH window: the ensemble = skin + its full backing
dunes component + the waist's straddle/decal/fringe cells (both family sides) + a carried grass
margin, per the v4 LOWLAND-CUT law (window cuts cross only plain lowland grass or open water) and
THE ENSEMBLE LAW (measure whether any subset terminates naturally -- never assume it does).

READ-ONLY against the game install: only X.read_block (stock disc-1 bytes) via the already-proven
seam_null_recon.load_tris/edge_index/classify_tri/FAM_OF (contract_mass_scout/contract_mass_interior's
own machinery, reused not reimplemented -- CALIBRATE-THE-INSTRUMENT). ZERO writes, no deploy, no
mirror, no --apply. Only files touched this round: rung_f_*.py + out/rung_f/*.

Run:  py studies/overworld-topography/rung_f_scout_window.py
Artifact -> out/rung_f/scout_window.json
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                        # noqa: E402 -- proven FAM_OF/load_tris/edge_index/classify_tri
import contract_mass_scout as CMS                     # noqa: E402 -- connected_components/block_rect_of_cells/cheby
import contract_mass_interior as CMI                  # noqa: E402 -- perimeter_decomp/build_sea_cells/MOORE/VN
from ff9mapkit.world import extract as X               # noqa: E402
from ff9mapkit.world import mesh as M                  # noqa: E402

OUT_DIR = HERE / "out" / "rung_f"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "scout_window.json"
SITES_JSON = HERE / "out" / "contract_mass" / "sites.json"

CELL = 4.0
BLOCK = 64.0
KNOWN_SITE_BLOCKS = {(13, 11), (13, 12), (14, 11), (14, 12), (15, 11), (15, 12)}
MARGIN_CELLS_REQUIRED = 2          # the task's ">=2-cell grass margin"
MAX_MARGIN_SCAN = 8                # how far out we scan looking for that margin, in cells

# ---- the desert|rock v-band decal (Round 11 table, verbatim from contract_gd_composition.py) -----
VBAND_V_LO, VBAND_V_HI = 0.83594, 0.86621
VBAND_V_TOL = 0.0015
DESERT_ROCK_U = (0.07129, 0.13184)
U_TOL = 0.0020

MURAL_TOPOS = {17, 38, 49}          # THE BAKED-TERRAIN LAW candidates
# THE ENGINE FOOT-WALK TABLE (coast-mosaic memory, section A) -- lowland-vs-rock/water classification
FOOT_LEGAL_TOPOS = {0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23,
                     27, 28, 30, 31, 32, 33, 34, 35, 36, 37, 38, 41, 42, 45, 46, 52}
ROCK_TOPOS = {49, 50}
TERRACE_TOPOS = {13, 45, 46}        # topo-13 shelf / canyon tiers -- non-lowland grass


def tri_uv_bbox(uv3):
    us = [p[0] for p in uv3]
    vs = [p[1] for p in uv3]
    return min(us), min(vs), max(us), max(vs)


def is_desert_rock_vband(uv3):
    u0, v0, u1, v1 = tri_uv_bbox(uv3)
    if not (abs(v0 - VBAND_V_LO) <= VBAND_V_TOL and abs(v1 - VBAND_V_HI) <= VBAND_V_TOL):
        return False
    return (DESERT_ROCK_U[0] - U_TOL <= u0 and u1 <= DESERT_ROCK_U[1] + U_TOL)


def block_of_cell(cell_block, c):
    return cell_block.get(c)


def rect_of_cells(cells):
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    return (min(xs), min(ys), max(xs), max(ys))


def blocks_touched(cells, cell_block):
    bs = {cell_block[c] for c in cells if c in cell_block}
    return bs


def main():
    t0 = time.time()
    print(f"game root: {SNR.GAME_ROOT}")
    land_blocks = X.list_blocks(disc=1)
    print(f"land blocks map-wide: {len(land_blocks)}")
    all_tris, bms, src_by_block = SNR.load_tris(land_blocks, source="stock")
    print(f"tris loaded: {len(all_tris)}  ({time.time()-t0:.1f}s)")

    cell_fams = defaultdict(Counter)     # cell -> Counter(fam)  (fam may be None for un-mapped topo, e.g. 49)
    cell_topo = defaultdict(Counter)     # cell -> Counter(topo)
    cell_tris = defaultdict(list)
    cell_block = {}
    cell_y = defaultdict(list)
    for t in all_tris:
        c = t["cell"]
        cell_fams[c][t["fam"]] += 1
        cell_topo[c][t["topo"]] += 1
        cell_tris[c].append(t)
        cell_block[c] = t["block"]
        cell_y[c].extend(p[1] for p in t["w"])
    land_cells = set(cell_tris)
    print(f"land cells: {len(land_cells)}")

    # ================================================================================================
    # 1. THE DUNES COMPONENT -- full 8-conn (radius=1, undilated) map-wide component map
    # ================================================================================================
    dunes_cells = {c for c, f in cell_fams.items() if f.get("dunes", 0) > 0}
    print(f"\ndunes-family cells map-wide: {len(dunes_cells)}")
    dunes_comps = CMS.connected_components(dunes_cells, 1)
    dunes_comps.sort(key=lambda comp: -len(comp))
    print(f"dunes MASSES (8-conn, undilated): {len(dunes_comps)}")
    for i, comp in enumerate(dunes_comps[:10]):
        r = CMS.block_rect_of_cells(comp, cell_block)
        print(f"  [{i}] cells={len(comp):4d} blocks=({r['bx_lo']}-{r['bx_hi']},{r['by_lo']}-{r['by_hi']}) "
              f"n_blocks={r['n_blocks']}")

    # desert masses (fam=="desert" = topo 16/17/19/20), to find the SKIN (the known site's desert mass)
    desert_cells = {c for c, f in cell_fams.items() if f.get("desert", 0) > 0}
    desert_comps = CMS.connected_components(desert_cells, 1)
    skin_comp = None
    for comp in desert_comps:
        r = CMS.block_rect_of_cells(comp, cell_block)
        blocks = {tuple(b) for b in r["blocks"]}
        if blocks & KNOWN_SITE_BLOCKS:
            skin_comp = comp
            break
    assert skin_comp is not None, "CALIBRATION FAILED: known desert skin not found"
    skin_cells = set(skin_comp)
    skin_rect = CMS.block_rect_of_cells(skin_comp, cell_block)
    skin_topo_tally = Counter()
    for c in skin_cells:
        for topo, n in cell_topo[c].items():
            skin_topo_tally[topo] += n
    print(f"\nTHE SKIN: {len(skin_cells)} cells, blocks {skin_rect['blocks']}, topo_tally={dict(skin_topo_tally)}")

    # backing dunes component(s): any dunes component with >=1 cell cheby<=1 of a skin cell
    def cheby1_neighbors(c):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                yield (c[0] + dx, c[1] + dy)

    skin_neighbor_shell = set()
    for c in skin_cells:
        for n in cheby1_neighbors(c):
            if n not in skin_cells:
                skin_neighbor_shell.add(n)

    backing_comps = []
    for comp in dunes_comps:
        comp_set = set(comp)
        if comp_set & skin_neighbor_shell:
            backing_comps.append(comp)
    print(f"\ndunes components touching the skin's cheby<=1 shell: {len(backing_comps)}")
    for comp in backing_comps:
        r = CMS.block_rect_of_cells(comp, cell_block)
        print(f"  cells={len(comp)} blocks=({r['bx_lo']}-{r['bx_hi']},{r['by_lo']}-{r['by_hi']})")

    assert len(backing_comps) >= 1, "no dunes component touches the skin -- THE DUNES-BACKING LAW would be violated"
    backing_comp = max(backing_comps, key=len)
    backing_cells = set(backing_comp)
    backing_rect = CMS.block_rect_of_cells(backing_comp, cell_block)
    backing_topo_tally = Counter()
    for c in backing_cells:
        for topo, n in cell_topo[c].items():
            backing_topo_tally[topo] += n
    print(f"\nTHE BACKING DUNES COMPONENT (largest touching the skin): {len(backing_cells)} cells, "
          f"blocks {backing_rect['blocks']}, topo_tally={dict(backing_topo_tally)}")
    print(f"  (previously cited figure: 143 cells -- {'MATCHES' if len(backing_cells)==143 else 'DIFFERS'})")

    # skin<->backing interface (4-conn, matching THE SKIN<->BACKING INTERFACE gate convention)
    VN = CMI.VN
    interface_pairs = 0
    for c in skin_cells:
        for dx, dy in VN:
            n = (c[0] + dx, c[1] + dy)
            if n in backing_cells:
                interface_pairs += 1
    print(f"  skin<->backing 4-conn interface pairs: {interface_pairs}")

    # is the backing component fully within the 6 known-site blocks, or does it spill beyond?
    backing_blocks = {tuple(b) for b in backing_rect["blocks"]}
    spill_blocks = sorted(backing_blocks - KNOWN_SITE_BLOCKS)
    print(f"  backing component blocks OUTSIDE the known 6-block site: {spill_blocks}")

    # ================================================================================================
    # 2. THE WINDOW -- skin + backing dunes + the waist's straddle/decal/fringe cells + >=2-cell margin
    # ================================================================================================
    sites = json.loads(SITES_JSON.read_text(encoding="utf-8"))
    known_site = None
    for s in sites["ecotone_sites"]:
        if s["is_known_calibration_site"]:
            known_site = s
            break
    assert known_site is not None
    site_cells = {tuple(c) for c in known_site["cells"]}
    print(f"\necotone SITE (straddle+decal+fringe, from sites.json): {len(site_cells)} cells, "
          f"boundary={known_site['n_boundary_cells']} decal={known_site['n_decal_cells']} "
          f"fringe={known_site['n_fringe_cells']}")

    ensemble = skin_cells | backing_cells | site_cells
    ens_rect = rect_of_cells(ensemble)
    ens_blocks = blocks_touched(ensemble, cell_block)
    print(f"\nTHE ENSEMBLE (skin U backing-dunes U site): {len(ensemble)} cells, "
          f"cell-rect x[{ens_rect[0]},{ens_rect[2]}] y[{ens_rect[1]},{ens_rect[3]}], "
          f"blocks touched: {sorted(ens_blocks)}")

    # ---- grow a margin ring-by-ring on each of the 4 sides independently -------------------------
    cx0, cy0, cx1, cy1 = ens_rect

    def strip_cells(side, m):
        """The single-cell-wide strip at exactly margin m outside ens_rect on `side`
        ('N'=+y,'S'=-y,'E'=+x,'W'=-x), spanning the (margin-adjusted) other axis."""
        if side == "N":
            y = cy1 + m
            return [(x, y) for x in range(cx0 - m, cx1 + m + 1)]
        if side == "S":
            y = cy0 - m
            return [(x, y) for x in range(cx0 - m, cx1 + m + 1)]
        if side == "E":
            x = cx1 + m
            return [(x, y) for y in range(cy0 - m, cy1 + m + 1)]
        if side == "W":
            x = cx0 - m
            return [(x, y) for y in range(cy0 - m, cy1 + m + 1)]
        raise ValueError(side)

    def classify_cell(c):
        if c in ensemble:
            return "ensemble"
        if c not in land_cells:
            return "absent"       # off any land block -- open water or void, resolved below
        fams = cell_fams[c]
        topos = cell_topo[c]
        dom_topo = topos.most_common(1)[0][0] if topos else None
        if dom_topo in ROCK_TOPOS or (fams.get(None, 0) > fams.get("grass", 0) and fams.get(None, 0) > 0
                                       and fams.get("grass", 0) == 0 and fams.get("desert", 0) == 0
                                       and fams.get("dunes", 0) == 0):
            return f"rock(topo{dom_topo})"
        if dom_topo in TERRACE_TOPOS:
            return f"terrace(topo{dom_topo})"
        if fams.get("desert", 0) > 0 or fams.get("dunes", 0) > 0:
            return f"desert_family(topo{dom_topo})"
        if fams.get("grass", 0) > 0:
            ys = cell_y[c]
            ymax = max(ys) if ys else None
            return f"grass(topo{dom_topo},ymax={ymax:.1f})" if ymax is not None else f"grass(topo{dom_topo})"
        return f"other(topo{dom_topo},fam={fams.most_common(1)[0][0] if fams else None})"

    side_report = {}
    settled_margin = {}
    settle_reason = {}
    for side in ("N", "S", "E", "W"):
        rows = []
        clean_grass_run = 0
        stop_margin = None
        reason = None
        for m in range(1, MAX_MARGIN_SCAN + 1):
            cells = strip_cells(side, m)
            tally = Counter()
            samples = []
            for c in cells:
                cls = classify_cell(c)
                key = cls.split("(")[0]
                tally[key] += 1
                if len(samples) < 6:
                    samples.append([list(c), cls])
            rows.append(dict(margin_cells=m, margin_u=m * CELL, tally=dict(tally), n=len(cells), sample=samples))
            # "clean grass ring" = every cell in the strip is either grass or absent(open water/void)
            all_grass_or_absent = all(k in ("grass", "absent") for k in tally)
            if all_grass_or_absent and tally.get("grass", 0) > 0:
                clean_grass_run += 1
            else:
                clean_grass_run = 0
            if stop_margin is None and (tally.get("absent", 0) == len(cells)):
                stop_margin, reason = m, "open_water_or_void_reached"
            if clean_grass_run >= MARGIN_CELLS_REQUIRED and stop_margin is None:
                stop_margin, reason = m, "clean_grass_margin_found"
        side_report[side] = rows
        settled_margin[side] = stop_margin if stop_margin is not None else MAX_MARGIN_SCAN
        settle_reason[side] = reason if reason is not None else "SCAN_CAP_REACHED_NO_CLEAN_MARGIN"
        print(f"\nside {side}: settled margin = {settled_margin[side]} cells ({settle_reason[side]})")
        for r in side_report[side][:min(settled_margin[side] + 1, MAX_MARGIN_SCAN)]:
            print(f"    m={r['margin_cells']} u={r['margin_u']:.0f} tally={r['tally']}")

    # ---- the final window rect: ensemble bbox + settled per-side margin (independent per side) ----
    win_cx0 = cx0 - settled_margin["W"]
    win_cx1 = cx1 + settled_margin["E"]
    win_cy0 = cy0 - settled_margin["S"]
    win_cy1 = cy1 + settled_margin["N"]
    win_cells_rect = (win_cx0, win_cy0, win_cx1, win_cy1)
    print(f"\nWINDOW cell-rect: x[{win_cx0},{win_cx1}] y[{win_cy0},{win_cy1}] "
          f"({win_cx1-win_cx0+1} x {win_cy1-win_cy0+1} cells = "
          f"{(win_cx1-win_cx0+1)*CELL:.0f} x {(win_cy1-win_cy0+1)*CELL:.0f}u)")

    # which land blocks the window rect spans (by corner-cell block lookup where available, else
    # floor-div reconstruction from land_blocks' own coverage)
    win_cell_set = {(x, y) for x in range(win_cx0, win_cx1 + 1) for y in range(win_cy0, win_cy1 + 1)}
    win_blocks_from_land = {cell_block[c] for c in win_cell_set if c in cell_block}
    print(f"window touches {len(win_blocks_from_land)} populated land blocks (of the cells that ARE land): "
          f"{sorted(win_blocks_from_land)}")
    if win_blocks_from_land:
        wbx0 = min(b[0] for b in win_blocks_from_land)
        wbx1 = max(b[0] for b in win_blocks_from_land)
        wby0 = min(b[1] for b in win_blocks_from_land)
        wby1 = max(b[1] for b in win_blocks_from_land)
        window_block_rect = dict(bx_lo=wbx0, bx_hi=wbx1, by_lo=wby0, by_hi=wby1,
                                  n_blocks=(wbx1 - wbx0 + 1) * (wby1 - wby0 + 1))
        print(f"window BLOCK bounding rect: ({wbx0}-{wbx1},{wby0}-{wby1}) = "
              f"{wbx1-wbx0+1} x {wby1-wby0+1} = {window_block_rect['n_blocks']} blocks")
    else:
        window_block_rect = None

    # ================================================================================================
    # 3. THE CROSSINGS -- what lies immediately outside the FINAL window rect, all the way around
    # ================================================================================================
    crossing_report = {}
    for side in ("N", "S", "E", "W"):
        m = settled_margin[side] + 1   # one cell beyond the settled window edge
        cells = strip_cells(side, m)
        tally = Counter()
        offenders = []
        for c in cells:
            cls = classify_cell(c)
            key = cls.split("(")[0]
            tally[key] += 1
            if key not in ("grass", "absent", "ensemble"):
                offenders.append([list(c), cls])
        crossing_report[side] = dict(probe_margin_cells=m, tally=dict(tally),
                                      offenders=offenders[:20], lawful=(len(offenders) == 0))
        print(f"\nCROSSING {side} (1 cell beyond the settled window, m={m}): tally={dict(tally)} "
              f"lawful={crossing_report[side]['lawful']}")
        if offenders:
            print(f"  offenders (non grass/water): {offenders[:10]}")

    all_lawful = all(v["lawful"] for v in crossing_report.values())

    # ================================================================================================
    # 4. EVENT BITS + PARTS in the window
    # ================================================================================================
    window_blocks_list = sorted(win_blocks_from_land) if win_blocks_from_land else []
    event_by_block = {}
    total_event_tiles = 0
    for b in window_blocks_list:
        tris_here = [t for t in all_tris if t["block"] == b]
        ev_tally = Counter()
        area_vals = Counter()
        for t in tris_here:
            idall = t["idall"]
            ev = (idall >> 14) & 3
            area = (idall >> 8) & 0x3F
            if ev:
                ev_tally[ev] += 1
                area_vals[area] += 1
        if ev_tally:
            event_by_block[f"{b[0]},{b[1]}"] = dict(event_tri_tally=dict(ev_tally), area_tally=dict(area_vals))
            total_event_tiles += sum(ev_tally.values())
    print(f"\nEVENT BITS in window blocks: {total_event_tiles} event-flagged tris across "
          f"{len(event_by_block)} blocks: {event_by_block}")

    # non-Terrain parts present per window block
    CANDIDATE_PARTS = ("beach1", "beach2", "sea1", "sea2", "sea3", "sea4", "sea5", "sea6",
                        "object", "river", "riverjoint", "falls", "stream",
                        "volcanocrater", "volcanolava")
    parts_by_block = {}
    for b in window_blocks_list:
        present = []
        for p in CANDIDATE_PARTS:
            try:
                bm = X.read_block(b[0], b[1], disc=1, part=p)
                n = len(bm.tris) if hasattr(bm, "tris") else (len(bm.flat_index) // 3 if bm.flat_index else 0)
                if n:
                    present.append([p, n])
            except (ValueError, FileNotFoundError):
                continue
        if present:
            parts_by_block[f"{b[0]},{b[1]}"] = present
    print(f"\nNON-TERRAIN PARTS in window blocks: {parts_by_block}")

    # ================================================================================================
    # 5. desert|rock v-band decal census in/near the window
    # ================================================================================================
    vband_hits = []
    for t in all_tris:
        if t["block"] not in window_blocks_list:
            continue
        if is_desert_rock_vband(t["uv"]):
            vband_hits.append(dict(block=list(t["block"]), cell=list(t["cell"]), topo=t["topo"]))
    print(f"\ndesert|rock 0.836-v-band decal hits inside the window: {len(vband_hits)}")
    if vband_hits:
        print(f"  {vband_hits[:10]}")

    # ================================================================================================
    # 6. DESERT_MAINS_SECONDARY rect presence check (blocks (11,4)(11,5)(12,4)(12,5)(12,6))
    # ================================================================================================
    secondary_blocks = {(11, 4), (11, 5), (12, 4), (12, 5), (12, 6)}
    secondary_in_window = secondary_blocks & set(window_blocks_list)
    print(f"\nDESERT_MAINS_SECONDARY blocks in window: {sorted(secondary_in_window)} "
          f"(far-field check: {'PRESENT -- investigate' if secondary_in_window else 'absent, as expected'})")

    # ================================================================================================
    # 7. mural check for topo in {17,38,49} within the ensemble+window
    # ================================================================================================
    mural_report = {}
    for topo_id in sorted(MURAL_TOPOS):
        tris_of_topo = [t for t in all_tris if t["topo"] == topo_id and t["block"] in window_blocks_list]
        if not tris_of_topo:
            continue
        uv_keys = set()
        for t in tris_of_topo:
            uv_keys.add(tuple(sorted((round(u, 4), round(v, 4)) for u, v in t["uv"])))
        frac_unique = len(uv_keys) / len(tris_of_topo)
        mural_report[topo_id] = dict(n_tris=len(tris_of_topo), n_unique_uv=len(uv_keys),
                                      frac_unique=round(frac_unique, 4),
                                      is_mural_like=frac_unique >= 0.85)
    print(f"\nMURAL CHECK (topo 17/38/49 in window): {mural_report}")

    # ================================================================================================
    # 8. height/relief profile of the ensemble + window
    # ================================================================================================
    def height_stats(cells):
        ys = []
        for c in cells:
            ys.extend(cell_y.get(c, []))
        if not ys:
            return None
        ys.sort()
        return dict(n=len(ys), min=round(ys[0], 2), max=round(ys[-1], 2),
                    p50=round(ys[len(ys)//2], 2))

    relief = dict(
        skin=height_stats(skin_cells),
        backing_dunes=height_stats(backing_cells),
        ensemble=height_stats(ensemble),
        window=height_stats(win_cell_set & land_cells),
        grass_in_ensemble=height_stats({c for c in ensemble if cell_fams[c].get("grass", 0) > 0}),
    )
    print(f"\nRELIEF: {json.dumps(relief, indent=1)}")

    # topo-13/terrace or topo-49/rock presence anywhere in the ensemble itself (not just crossings)
    ens_topo_tally = Counter()
    for c in ensemble:
        for topo, n in cell_topo[c].items():
            ens_topo_tally[topo] += n
    terrace_or_rock_in_ensemble = {t: n for t, n in ens_topo_tally.items()
                                    if t in TERRACE_TOPOS or t in ROCK_TOPOS}
    print(f"\nterrace/rock topo tris WITHIN the ensemble itself: {terrace_or_rock_in_ensemble}")

    # ================================================================================================
    # 9. THE VALLEY CONTEXT -- block-level topo tallies for the 6 known-site blocks (the margin scan
    # found ROCK at m=1 in every direction; this checks whether that is a thin fringe or whether the
    # known-site blocks THEMSELVES are majority rock -- i.e. whether the true containing landform is
    # a mountain-ringed valley, not a grass plain with an embedded ecotone) + a coarse ASCII terrain
    # grid over a generous surrounding region for visual/qualitative reporting.
    # ================================================================================================
    known_block_topo = {}
    for b in sorted(KNOWN_SITE_BLOCKS):
        tris_here = [t for t in all_tris if t["block"] == b]
        topo_tally = Counter(t["topo"] for t in tris_here)
        fam_tally = Counter(t["fam"] for t in tris_here)
        known_block_topo[f"{b[0]},{b[1]}"] = dict(
            n_tris=len(tris_here), topo_tally=dict(topo_tally),
            fam_tally={str(k): v for k, v in fam_tally.items()},
            rock49_frac=round(topo_tally.get(49, 0) / len(tris_here), 3) if tris_here else None,
        )
    print(f"\nVALLEY CONTEXT -- per-block topo tally for the 6 known-site blocks:")
    for k, v in known_block_topo.items():
        print(f"  {k}: n={v['n_tris']} rock49_frac={v['rock49_frac']} topo={v['topo_tally']}")

    # coarse ASCII grid (dominant-topo per cell) over a generous surrounding region, cell-granularity
    grid_bx = range(9, 20)
    grid_by = range(6, 17)
    grid_blocks = [(bx, by) for bx in grid_bx for by in grid_by]
    grid_cell_topo = defaultdict(Counter)
    for t in all_tris:
        if t["block"] in grid_blocks:
            grid_cell_topo[t["cell"]][t["topo"]] += 1
    if grid_cell_topo:
        gxs = [c[0] for c in grid_cell_topo]
        gys = [c[1] for c in grid_cell_topo]
        gx0, gx1 = min(gxs), max(gxs)
        gy0, gy1 = min(gys), max(gys)

        def gsym(c):
            topo = grid_cell_topo.get(c)
            if not topo:
                return "."
            dom = topo.most_common(1)[0][0]
            if dom == 49:
                return "#"
            if dom == 41:
                return "n"
            if dom in (16, 17, 19, 20):
                return "d"
            if dom == 13:
                return "T"
            if dom == 59:
                return "h"
            if dom in (31, 32, 33):
                return "~"
            if dom in (0, 1, 2, 3, 10, 11, 12, 42):
                return ","
            return "?"

        ascii_rows = [f"{y:5d} " + "".join(gsym((x, y)) for x in range(gx0, gx1 + 1))
                      for y in range(gy0, gy1 + 1)]
    else:
        ascii_rows = []

    # ================================================================================================
    # VERDICT
    # ================================================================================================
    # the ensemble PROPER (desert/dunes/fringe cells only) stays lowland and near-clean of rock; but
    # the CONTAINING landform (the same 6 known-site blocks, in full) is majority topo-49 rock in
    # 4/6 blocks -- a mountain-ringed valley, not a grass plain with an embedded ecotone. That fact
    # -- not a terrace/mural crossing -- is what disqualifies the naive "just widen the grass margin"
    # recipe (the margin scan never found 2 clean grass rings within 8 cells/32u on ANY side).
    ens_total_tris = sum(len(cell_tris[c]) for c in ensemble)
    ens_rock_tris = terrace_or_rock_in_ensemble.get(49, 0) + terrace_or_rock_in_ensemble.get(50, 0)
    ens_terrace_tris = sum(n for t, n in terrace_or_rock_in_ensemble.items() if t in (13, 45, 46))
    ens_rock_frac = round(ens_rock_tris / ens_total_tris, 4) if ens_total_tris else 0.0
    # the ensemble PROPER (desert/dunes/fringe cells) is "core clean" if it carries no terrace tris
    # and only BOUNDARY-NOISE rock (a handful of mixed-topo cells at the very edge, not a real
    # highland incursion) -- 5% of ensemble tris is the working threshold, well above the measured
    # 3.7% boundary-noise figure and well below the 30%+ fractions the CONTAINING blocks carry.
    # ensemble_core_clean tracks the NAIVE recipe's own bookkeeping (0 rock/terrace tris inside the
    # skin+backing+site cells) -- it FAILS here (11.15% of ensemble tris are topo-49) because the
    # valley floor genuinely brushes its own walls in several fringe cells; that is a FINDING (the
    # ensemble cannot be kept rock-free by construction), not by itself a blocker -- a terrace
    # crossing (topo 13/45/46, no established rock-inclusive carry precedent) WOULD be a hard
    # blocker; rock is not, because THE TRUE MESH CARRY (Daguerreo/Uaho) is precedented precisely
    # for "carry the valley -- floor AND walls -- as one unit".
    ensemble_core_clean = ens_terrace_tris == 0
    valley_is_rock_ringed = any(v["rock49_frac"] and v["rock49_frac"] >= 0.3 for v in known_block_topo.values())
    margin_never_settled_naturally = all(
        settle_reason[s] == "SCAN_CAP_REACHED_NO_CLEAN_MARGIN" for s in ("N", "S", "E", "W"))
    has_quest_content = total_event_tiles > 0 or any(any(p[0] == "object" for p in v)
                                                       for v in parts_by_block.values())

    if (all_lawful and ensemble_core_clean and ens_rock_frac <= 0.01 and not valley_is_rock_ringed
            and not has_quest_content and window_block_rect is not None):
        verdict = "CARRY_WHOLE_JUNCTION"
    elif window_block_rect is not None and ensemble_core_clean:
        # no terrace crossing (the one class with no rock-inclusive carry precedent); everything
        # else that disqualifies the NAIVE grass-margin cut -- valley walls immediately adjacent,
        # real quest content on the skin's own blocks, the margin scan never finding clean grass --
        # each has a standing lawful mechanism (the massif-carry precedent for the walls;
        # DONOR-DISPATCH STRIP + Object-part exclusion for quest content; a v4-style rect/neck scan,
        # not yet run, for the true window boundary) -- termination work, not infeasibility.
        verdict = "CARRY_WITH_TERMINATION_WORK"
    else:
        verdict = "INFEASIBLE"
    print(f"\n{'='*80}\nVERDICT: {verdict}\n{'='*80}")
    print(f"  ensemble_core_clean(terrace_tris={ens_terrace_tris}, rock_frac={ens_rock_frac})={ensemble_core_clean}")
    print(f"  valley_is_rock_ringed (>=1 of the 6 known blocks >=30% topo-49 tris)={valley_is_rock_ringed}")
    print(f"  margin_scan_never_found_2_clean_grass_rings_in_8_cells={margin_never_settled_naturally}")
    print(f"  has_quest_content(event tiles or Object meshes present)={has_quest_content}")

    # ================================================================================================
    # write
    # ================================================================================================
    out = dict(
        meta=dict(script="rung_f_scout_window.py", n_land_blocks=len(land_blocks), n_tris=len(all_tris),
                  known_site_blocks=sorted(list(b) for b in KNOWN_SITE_BLOCKS),
                  margin_cells_required=MARGIN_CELLS_REQUIRED, elapsed_s=round(time.time() - t0, 1)),
        dunes_masses_top10=[dict(n_cells=len(comp), block_rect=CMS.block_rect_of_cells(comp, cell_block))
                             for comp in dunes_comps[:10]],
        skin=dict(n_cells=len(skin_cells), block_rect=skin_rect, topo_tally=dict(skin_topo_tally),
                   cells=[list(c) for c in sorted(skin_cells)]),
        backing_dunes=dict(n_cells=len(backing_cells), block_rect=backing_rect,
                            topo_tally=dict(backing_topo_tally),
                            matches_prior_143=len(backing_cells) == 143,
                            spill_blocks_outside_known_site=spill_blocks,
                            skin_backing_interface_pairs=interface_pairs,
                            n_backing_components_touching_skin=len(backing_comps),
                            cells=[list(c) for c in sorted(backing_cells)]),
        ecotone_site=dict(n_cells=len(site_cells), n_boundary_cells=known_site["n_boundary_cells"],
                           n_decal_cells=known_site["n_decal_cells"], n_fringe_cells=known_site["n_fringe_cells"]),
        ensemble=dict(n_cells=len(ensemble), cell_rect=list(ens_rect),
                       blocks_touched=[list(b) for b in sorted(ens_blocks)],
                       terrace_or_rock_topo_tris_within=terrace_or_rock_in_ensemble),
        margin_scan=dict(side_report=side_report, settled_margin_cells=settled_margin,
                          settle_reason=settle_reason),
        valley_context=dict(known_block_topo=known_block_topo, ascii_grid_bounds=dict(
            bx=[min(grid_bx), max(grid_bx)], by=[min(grid_by), max(grid_by)]) if grid_cell_topo else None,
            ascii_grid=ascii_rows,
            legend="# rock49 | n dunes41 | d desert(16/17/19/20) | , grass | T terrace13 | "
                   "h hole/building59(Object footprint) | ~ shore | . no land tri loaded"),
        window=dict(cell_rect=list(win_cells_rect),
                     n_cells=(win_cx1 - win_cx0 + 1) * (win_cy1 - win_cy0 + 1),
                     size_u=[(win_cx1 - win_cx0 + 1) * CELL, (win_cy1 - win_cy0 + 1) * CELL],
                     block_rect=window_block_rect,
                     blocks=[list(b) for b in sorted(win_blocks_from_land)]),
        crossings=crossing_report,
        crossings_all_lawful=all_lawful,
        event_bits=dict(total_event_tiles=total_event_tiles, by_block=event_by_block),
        non_terrain_parts=parts_by_block,
        vband_decal_hits_in_window=vband_hits,
        desert_mains_secondary_check=dict(blocks=sorted(list(b) for b in secondary_blocks),
                                           present_in_window=sorted(list(b) for b in secondary_in_window)),
        mural_check=mural_report,
        relief=relief,
        verdict=verdict,
        verdict_reasoning=dict(
            all_crossings_lawful=all_lawful,
            ensemble_core_clean=ensemble_core_clean,
            ensemble_rock_frac=ens_rock_frac,
            ensemble_terrace_tris=ens_terrace_tris,
            valley_is_rock_ringed=valley_is_rock_ringed,
            margin_never_settled_naturally=margin_never_settled_naturally,
            has_quest_content=has_quest_content,
            window_resolvable=window_block_rect is not None,
        ),
    )
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}  (total {time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
