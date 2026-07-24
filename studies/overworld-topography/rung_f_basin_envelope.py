"""RUNG F -- FRAME ROUND 2, the DECISIVE FIT MEASUREMENT.

READ-ONLY vs the game install. Writes ONLY out/rung_f/basin_envelope.json + this script.
No deploy, no --apply, no mirror, no git.

The eye + the restructure both point to OPTION (a): carry STOCK'S OWN enclosing rock (the
calib_context Daguerreo basin that literally rings THIS junction) as a TRUE-MESH carry, so
the mountain-ringed-basin FORM comes from stock bytes, not from bolting synthetic small massifs
(round-1, FALSIFIED: r_rim ~2x bigger than assumed, 394u > 320u E/W ceiling).

This script quantifies whether option (a) can FIT the (0-4,16-19) ocean site (320x256u):
  (1) STOCK ENCLOSING-ROCK ENVELOPE: for the real junction (ecotone at blocks 13-15,11-12),
      measure how thick the enclosing ROCK band is on each side (N/E/S/W) at the ecotone bbox.
  (2) CARRY-WINDOW FIT: for candidate block windows centred on the junction (3x3..5x4),
      measure captured rock cells + the ecotone's clearance to the window edge, and check the
      window fits the 320x256u ocean site with >= the R1-standoff grass+coast margin.
  (3) THE VERDICT: does a form-from-stock-bytes basin carry fit, and at what window?

Run:  cd studies/overworld-topography && py rung_f_basin_envelope.py
"""
from __future__ import annotations
import json, math, sys
from collections import Counter, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                         # noqa: E402  FAM_OF
from ff9mapkit.world import extract as X             # noqa: E402

CELL = 4.0
BLOCK = 64.0
OUT = HERE / "out" / "rung_f" / "basin_envelope.json"

MASS_TOPOS = frozenset({16, 17, 19, 20, 41})          # ecotone skin + desert/dirt + dunes = the carried core
ROCK_TOPOS = frozenset(t for t, f in SNR.FAM_OF.items() if f == "rock")

# the real junction (mass-anatomy contract: the map's ONE grass|desert cluster)
JUNCTION_BLOCKS = [(bx, by) for bx in range(13, 16) for by in range(11, 13)]   # (13-15,11-12)
# the context window the eye calibrated on (calib_context = 11-17,9-14)
CONTEXT_X = range(10, 19)
CONTEXT_Z = range(8, 16)

# the ocean site (the ONE open-ocean rect, restructure: Rmax=132 @ (144,-1144), rect = (0-4,16-19))
OCEAN_BLOCKS_X = range(0, 5)     # 5 blocks -> 320u E-W
OCEAN_BLOCKS_Z = range(16, 20)   # 4 blocks -> 256u N-S
OCEAN_W = 5 * BLOCK              # 320u
OCEAN_H = 4 * BLOCK             # 256u


def log(m): print(m, flush=True)


def tri_topo(bm, tri):
    return X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]


def classify_cells(blocks):
    """Return dicts cell->family-histogram (Counter of topo-family) over world cells for a stock block set."""
    cell_fam = {}     # cell -> Counter(fam)
    cell_topo = {}    # cell -> Counter(topo)
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError):
            continue
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            topo = tri_topo(bm, tri)
            fam = SNR.FAM_OF.get(topo)
            cx = sum(bm.verts[j][0] + ox for j in tri) / 3.0
            cz = sum(bm.verts[j][2] + oz for j in tri) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            cell_fam.setdefault(cell, Counter())[str(fam)] += 1
            cell_topo.setdefault(cell, Counter())[topo] += 1
    return cell_fam, cell_topo


def dominant(counter):
    return counter.most_common(1)[0][0] if counter else None


def main():
    log("=" * 90); log("RUNG F FRAME ROUND 2 -- BASIN ENVELOPE FIT MEASUREMENT (stock, read-only)"); log("=" * 90)

    # ---- read the whole junction context (stock) ------------------------------------------------
    ctx_blocks = [(bx, by) for bx in CONTEXT_X for by in CONTEXT_Z]
    cell_fam, cell_topo = classify_cells(ctx_blocks)
    log(f"context blocks read: {len(ctx_blocks)}  land cells: {len(cell_fam)}")

    # ecotone core = cells whose dominant topo is a MASS_TOPO (16/17/19/20/41), restricted to the junction blocks
    ecotone_cells = set()
    for (bx, by) in JUNCTION_BLOCKS:
        ox, oz = X.block_world_origin(bx, by)
        cx0, cz0 = int(ox // CELL), int(oz // CELL)
        for dx in range(int(BLOCK // CELL)):
            for dz in range(int(BLOCK // CELL)):
                c = (cx0 + dx, cz0 + dz)
                tc = cell_topo.get(c)
                if tc and dominant(tc) in MASS_TOPOS:
                    ecotone_cells.add(c)
    exs = [c[0] for c in ecotone_cells]; ezs = [c[1] for c in ecotone_cells]
    eco_bbox_cell = (min(exs), min(ezs), max(exs), max(ezs))
    eco_bbox_u = (min(exs) * CELL, min(ezs) * CELL, (max(exs) + 1) * CELL, (max(ezs) + 1) * CELL)
    eco_w = eco_bbox_u[2] - eco_bbox_u[0]
    eco_h = eco_bbox_u[3] - eco_bbox_u[1]
    log(f"ecotone core: {len(ecotone_cells)} cells  bbox_u=({eco_bbox_u[0]:.0f},{eco_bbox_u[1]:.0f})-"
        f"({eco_bbox_u[2]:.0f},{eco_bbox_u[3]:.0f})  span={eco_w:.0f}x{eco_h:.0f}u")

    # rock cells in context
    rock_cells = {c for c, tc in cell_topo.items() if dominant(tc) in ROCK_TOPOS}
    grass_cells = {c for c, fc in cell_fam.items() if dominant(fc) == "grass"}
    log(f"context rock cells: {len(rock_cells)}   grass cells: {len(grass_cells)}")

    # ---- (1) enclosing-rock thickness per side --------------------------------------------------
    # For each side, march outward from the ecotone bbox edge cell-by-cell and record the first-rock
    # distance and the contiguous rock-band thickness on the centre ray of that side.
    def march(side):
        exlo, ezlo, exhi, ezhi = eco_bbox_cell
        results = []
        if side in ("N", "S"):
            # march in z, sample several x columns across the ecotone width
            cols = range(exlo, exhi + 1)
            for cx in cols:
                if side == "N":  # -z is "north" in this world? use decreasing z
                    zr = range(ezlo - 1, ezlo - 40, -1); start_edge = ezlo
                else:
                    zr = range(ezhi + 1, ezhi + 40); start_edge = ezhi
                first_rock = None; band = 0; in_band = False
                for cz in zr:
                    c = (cx, cz)
                    is_rock = c in rock_cells
                    is_land = c in cell_fam
                    d = abs(cz - start_edge) * CELL
                    if is_rock and first_rock is None:
                        first_rock = d
                    if is_rock:
                        in_band = True; band += 1
                    elif in_band and not is_land:
                        break  # left land (reached coast/edge) after a rock band
                    elif in_band and is_land and not is_rock:
                        # grass gap inside the band -- allow small gaps, but stop after 3
                        pass
                results.append((first_rock, band * CELL))
        else:
            rows = range(ezlo, ezhi + 1)
            for cz in rows:
                if side == "W":
                    xr = range(exlo - 1, exlo - 40, -1); start_edge = exlo
                else:
                    xr = range(exhi + 1, exhi + 40); start_edge = exhi
                first_rock = None; band = 0; in_band = False
                for cx in xr:
                    c = (cx, cz)
                    is_rock = c in rock_cells
                    is_land = c in cell_fam
                    d = abs(cx - start_edge) * CELL
                    if is_rock and first_rock is None:
                        first_rock = d
                    if is_rock:
                        in_band = True; band += 1
                    elif in_band and not is_land:
                        break
                results.append((first_rock, band * CELL))
        firsts = [r[0] for r in results if r[0] is not None]
        bands = [r[1] for r in results]
        frac_reach_rock = len(firsts) / max(1, len(results))
        return dict(
            n_rays=len(results),
            frac_rays_hitting_rock=round(frac_reach_rock, 2),
            first_rock_u_median=None if not firsts else round(sorted(firsts)[len(firsts) // 2], 1),
            first_rock_u_min=None if not firsts else round(min(firsts), 1),
            rock_band_u_median=round(sorted(bands)[len(bands) // 2], 1),
            rock_band_u_max=round(max(bands), 1) if bands else 0.0,
        )

    sides = {s: march(s) for s in ("N", "S", "E", "W")}
    log("-" * 90); log("(1) STOCK ENCLOSING-ROCK ENVELOPE (per side, marching out from the ecotone bbox):")
    for s, r in sides.items():
        log(f"  {s}: {r['frac_rays_hitting_rock']*100:.0f}% of rays hit rock; first rock median={r['first_rock_u_median']}u "
            f"min={r['first_rock_u_min']}u; rock band median={r['rock_band_u_median']}u max={r['rock_band_u_max']}u")

    # ---- (2) carry-window fit -------------------------------------------------------------------
    # the junction spans blocks 13-15 (x) / 11-12 (z). candidate windows centred on it:
    windows = {
        "3x2_core_only": (range(13, 16), range(11, 13)),
        "3x3": (range(13, 16), range(10, 13)),
        "4x3": (range(12, 16), range(10, 13)),
        "4x4": (range(12, 16), range(10, 14)),
        "5x3": (range(12, 17), range(10, 13)),
        "5x4": (range(12, 17), range(10, 14)),
    }
    win_out = {}
    log("-" * 90); log("(2) CARRY-WINDOW FIT into the 320x256u ocean site:")
    for name, (wx, wz) in windows.items():
        wblocks = [(bx, by) for bx in wx for by in wz]
        wcf, wct = classify_cells(wblocks)
        wrock = {c for c, tc in wct.items() if dominant(tc) in ROCK_TOPOS}
        nbx, nbz = len(list(wx)), len(list(wz))
        win_w, win_h = nbx * BLOCK, nbz * BLOCK
        # the ecotone's clearance to the window edges (how much carried material holds it inland):
        # window world bbox
        oxs = [X.block_world_origin(bx, by)[0] for (bx, by) in wblocks]
        ozs = [X.block_world_origin(bx, by)[1] for (bx, by) in wblocks]
        wx0, wz0 = min(oxs), min(ozs)
        wx1, wz1 = max(oxs) + BLOCK, max(ozs) + BLOCK
        clr_w = eco_bbox_u[0] - wx0     # west margin of carried content beyond ecotone
        clr_e = wx1 - eco_bbox_u[2]
        clr_n = eco_bbox_u[1] - wz0
        clr_s = wz1 - eco_bbox_u[3]
        fits_site = (win_w <= OCEAN_W and win_h <= OCEAN_H)
        # after the carry we still need a grass+coast margin so the ecotone clears the ISLAND coast.
        # island coast sits >= (site - window)/2 beyond the window on each axis (if window centred).
        grass_margin_ew = (OCEAN_W - win_w) / 2.0
        grass_margin_ns = (OCEAN_H - win_h) / 2.0
        # realized ecotone->island-coast standoff (approx) = min carried-clearance + grass margin on that side
        est_standoff = min(
            clr_w + grass_margin_ew, clr_e + grass_margin_ew,
            clr_n + grass_margin_ns, clr_s + grass_margin_ns,
        )
        win_out[name] = dict(
            blocks=f"{nbx}x{nbz}", span_u=[win_w, win_h], n_land_cells=len(wcf), n_rock_cells=len(wrock),
            ecotone_edge_clearance_u=dict(W=round(clr_w, 0), E=round(clr_e, 0), N=round(clr_n, 0), S=round(clr_s, 0)),
            fits_ocean_site=fits_site,
            grass_margin_if_centred_u=dict(EW=round(grass_margin_ew, 0), NS=round(grass_margin_ns, 0)),
            est_min_ecotone_to_coast_u=round(est_standoff, 0),
        )
        log(f"  {name:14s} {nbx}x{nbz} ({win_w:.0f}x{win_h:.0f}u) rock_cells={len(wrock):4d} "
            f"eco_edge_clr WENS={win_out[name]['ecotone_edge_clearance_u']} "
            f"fits={fits_site} grass_margin EW/NS={grass_margin_ew:.0f}/{grass_margin_ns:.0f}u "
            f"est_standoff={est_standoff:.0f}u")

    # ---- (3) verdict ---------------------------------------------------------------------------
    # A window is a viable option-(a) basin carry iff:
    #   fits_ocean_site AND captures substantial rock (enclosing walls) AND est_standoff >= 40u (R1 floor)
    #   with target >= 50u.
    viable = {n: w for n, w in win_out.items()
              if w["fits_ocean_site"] and w["n_rock_cells"] >= 60 and w["est_min_ecotone_to_coast_u"] >= 40}
    log("-" * 90); log("(3) VERDICT:")
    if viable:
        best = max(viable, key=lambda n: (viable[n]["n_rock_cells"], viable[n]["est_min_ecotone_to_coast_u"]))
        log(f"  VIABLE option-(a) windows: {list(viable)}; best rock+standoff = {best}")
    else:
        log("  NO window both fits the ocean site AND captures enclosing rock AND clears 40u -- "
            "option (a) whole-basin carry does NOT fit; the enclosing rock and the standoff margin "
            "compete for the same 320x256u.")

    result = dict(
        rung="F", step="frame round 2 -- basin envelope fit (read-only)", date="2026-07-24",
        ecotone=dict(n_cells=len(ecotone_cells), bbox_u=[round(v, 0) for v in eco_bbox_u],
                     span_u=[round(eco_w, 0), round(eco_h, 0)]),
        context=dict(n_blocks=len(ctx_blocks), n_rock_cells=len(rock_cells), n_grass_cells=len(grass_cells)),
        enclosing_rock_envelope=sides,
        carry_window_fit=win_out,
        ocean_site=dict(blocks="0-4,16-19", span_u=[OCEAN_W, OCEAN_H], rmax_u=132),
        viable_option_a_windows=list(viable.keys()),
    )
    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")
    log("\n" + "=" * 90); log(f"-> {OUT}")
    return result


if __name__ == "__main__":
    main()
