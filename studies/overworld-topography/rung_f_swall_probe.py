"""RUNG F -- FRAME ATTEMPT 2: THE SOUTH-WALL TERMINATION PROBE (read-only).

Attempt-1 falsified BOTH full-basin mechanisms. The round's own guidance redefines the goal from
basin_envelope.json: the REAL stock pocket is walled STRONG-SOUTH (100% of rays hit rock) + THIN-WEST
and OPEN north/east. So the faithful F1 answer is a PARTIAL pocket: carry the stock SOUTH-WALL BAND
(+ thin west wall if it terminates cleanly) as a true-mesh strip, composed with the already-all-green
option (c) silhouette.

The DECISIVE question this probe answers (measured bytes, zero playtest cost): does the S-wall band
TERMINATE LAWFULLY on its far (south) side -- i.e. does its rock height drop back to a weldable
FOOT (~land_height, so the massif-carry apron conform is a small lift not a hanging cliff), or does
its far side stay mid-massif (high rock all the way to the site edge = un-terminable)?

Method: for the real junction (ecotone at blocks 13-15,11-12, bbox from basin_envelope), classify
every context cell as ocean / low-land (<8u) / high-rock (>=8u) with its family + p50 height. Then
march OUTWARD from the ecotone bbox in each of the 4 directions, column by column, recording the full
height sequence, and classify each ray's termination:
  FOOT_TO_LOWLAND  -- rock band then height drops to <8u land (weldable via apron) -> carriable
  FOOT_TO_OCEAN    -- rock band then ocean (no land)                                -> carriable
  MID_MASSIF       -- still >=8u rock at the carry horizon (HORIZON_U out)           -> NOT terminable
  NO_WALL          -- never hit >=8u rock (open side)
Then aggregate per side: what fraction of the wall rays terminate lawfully, and at what depth is the
foot -- so we know the narrowest carriable S-band, if any.

Run: cd studies/overworld-topography && py rung_f_swall_probe.py
Writes ONLY out/rung_f/swall_probe.json + this script. No deploy/apply/mirror/commit.
"""
from __future__ import annotations
import json, math, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                     # noqa: E402
from ff9mapkit.world import extract as X          # noqa: E402

CELL = 4.0
BLOCK = 64.0
OUT = HERE / "out" / "rung_f" / "swall_probe.json"

MASS_TOPOS = frozenset({16, 17, 19, 20, 41})
ROCK_TOPOS = frozenset(t for t, f in SNR.FAM_OF.items() if f == "rock") | {49}
HIGH_U = 8.0            # >=8u = "wall/highland" (the island generator's on-grain grass-edge ceiling)
HORIZON_U = 64.0       # the carry horizon: how far a true-mesh strip could reasonably reach south
LAND_FLOOR_U = 4.0     # a weldable foot: land tri p50 height at/below this ~ desert/grass floor (2.73)

CONTEXT_X = range(10, 19)
CONTEXT_Z = range(8, 16)
JUNCTION_BLOCKS = [(bx, by) for bx in range(13, 16) for by in range(11, 13)]


def log(m): print(m, flush=True)


def tri_topo(bm, tri):
    return X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]


def classify_cells(blocks):
    """cell -> dict(topo Counter, fam Counter, ys list)."""
    cells = {}
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError):
            continue
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            topo = tri_topo(bm, tri)
            fam = SNR.FAM_OF.get(topo)
            if topo == 49:
                fam = "rock"
            cx = sum(bm.verts[j][0] + ox for j in tri) / 3.0
            cz = sum(bm.verts[j][2] + oz for j in tri) / 3.0
            y = sum(bm.verts[j][1] for j in tri) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            d = cells.setdefault(cell, dict(topo=Counter(), fam=Counter(), ys=[]))
            d["topo"][topo] += 1
            d["fam"][str(fam)] += 1
            d["ys"].append(y)
    return cells


def dominant(counter):
    return counter.most_common(1)[0][0] if counter else None


def cell_p50(d):
    ys = sorted(d["ys"])
    return ys[len(ys) // 2] if ys else None


def cell_class(cells, c):
    """Return (kind, fam, p50) for a world cell.
    kind in {ocean, low, high}. ocean = no land tri present."""
    d = cells.get(c)
    if d is None:
        return ("ocean", None, None)
    p50 = cell_p50(d)
    fam = dominant(d["fam"])
    topo = dominant(d["topo"])
    is_rock = topo in ROCK_TOPOS
    if p50 is not None and p50 >= HIGH_U:
        return ("high", fam, p50)
    # low land -- but a rock cell below 8u is a rock FOOT
    return ("low", fam, p50)


def march_side(cells, eco_bbox_cell, side):
    """March outward from the ecotone bbox edge. Return list of per-ray dicts."""
    exlo, ezlo, exhi, ezhi = eco_bbox_cell
    rays = []
    horizon_cells = int(HORIZON_U / CELL)
    if side in ("N", "S"):
        cols = range(exlo, exhi + 1)
        for cx in cols:
            if side == "N":
                seq_iter = ((cx, ezlo - 1 - k) for k in range(horizon_cells + 8)); edge = ezlo
            else:
                seq_iter = ((cx, ezhi + 1 + k) for k in range(horizon_cells + 8)); edge = ezhi
            rays.append(_walk(cells, seq_iter, edge, axis="z", side=side))
    else:
        rows = range(ezlo, ezhi + 1)
        for cz in rows:
            if side == "W":
                seq_iter = ((exlo - 1 - k, cz) for k in range(horizon_cells + 8)); edge = exlo
            else:
                seq_iter = ((exhi + 1 + k, cz) for k in range(horizon_cells + 8)); edge = exhi
            rays.append(_walk(cells, seq_iter, edge, axis="x", side=side))
    return rays


def _walk(cells, seq_iter, edge, axis, side):
    """Walk one ray outward; classify termination.
    Records: first_wall_u (first >=8u rock), foot_u (where rock drops to <8u land after a wall),
    ocean_u (first ocean after a wall), horizon_kind (class at HORIZON_U), seq (kinds)."""
    seq = []
    first_wall = None
    foot_u = None
    ocean_u = None
    in_wall = False
    horizon_kind = None
    for (cx, cz) in seq_iter:
        idx = cz if axis == "z" else cx
        d_u = abs(idx - edge) * CELL
        kind, fam, p50 = cell_class(cells, (cx, cz))
        is_rock = False
        dd = cells.get((cx, cz))
        if dd is not None:
            is_rock = dominant(dd["topo"]) in ROCK_TOPOS
        seq.append((round(d_u, 0), kind, fam, None if p50 is None else round(p50, 1)))
        if kind == "high" and is_rock:
            if first_wall is None:
                first_wall = d_u
            in_wall = True
        if in_wall:
            # a FOOT = land cell at <8u after the wall started (drops to weldable)
            if kind == "low" and foot_u is None:
                foot_u = d_u
            if kind == "ocean" and ocean_u is None:
                ocean_u = d_u
        if abs(d_u - HORIZON_U) < CELL / 2 and horizon_kind is None:
            horizon_kind = (kind, None if p50 is None else round(p50, 1))
        if kind == "ocean" and in_wall:
            break
        if d_u >= HORIZON_U + CELL and (foot_u is not None or ocean_u is not None):
            break
    # termination classification
    if first_wall is None:
        term = "NO_WALL"
    elif ocean_u is not None and (foot_u is None or ocean_u <= foot_u):
        term = "FOOT_TO_OCEAN"
    elif foot_u is not None:
        term = "FOOT_TO_LOWLAND"
    else:
        term = "MID_MASSIF"
    return dict(term=term, first_wall_u=None if first_wall is None else round(first_wall, 0),
                foot_u=None if foot_u is None else round(foot_u, 0),
                ocean_u=None if ocean_u is None else round(ocean_u, 0),
                horizon_kind=horizon_kind, seq=seq)


def summarize(rays):
    terms = Counter(r["term"] for r in rays)
    lawful = [r for r in rays if r["term"] in ("FOOT_TO_LOWLAND", "FOOT_TO_OCEAN")]
    foots = [r["foot_u"] for r in lawful if r["foot_u"] is not None]
    oceans = [r["ocean_u"] for r in lawful if r["ocean_u"] is not None]
    n = len(rays)
    walls = [r for r in rays if r["first_wall_u"] is not None]
    return dict(
        n_rays=n,
        terms=dict(terms),
        frac_lawful_termination=round(len(lawful) / max(1, n), 2),
        frac_mid_massif=round(terms.get("MID_MASSIF", 0) / max(1, n), 2),
        foot_depth_u_median=None if not foots else round(sorted(foots)[len(foots) // 2], 0),
        foot_depth_u_max=None if not foots else round(max(foots), 0),
        ocean_depth_u_median=None if not oceans else round(sorted(oceans)[len(oceans) // 2], 0),
        first_wall_u_median=None if not walls else round(
            sorted(r["first_wall_u"] for r in walls)[len(walls) // 2], 0),
    )


def main():
    log("=" * 92)
    log("RUNG F ATTEMPT 2 -- SOUTH-WALL (all-sides) TERMINATION PROBE (stock, read-only)")
    log("=" * 92)
    ctx_blocks = [(bx, by) for bx in CONTEXT_X for by in CONTEXT_Z]
    cells = classify_cells(ctx_blocks)
    log(f"context blocks: {len(ctx_blocks)}  land cells: {len(cells)}")

    # ecotone core bbox (same definition as basin_envelope)
    eco = set()
    for (bx, by) in JUNCTION_BLOCKS:
        ox, oz = X.block_world_origin(bx, by)
        cx0, cz0 = int(ox // CELL), int(oz // CELL)
        for dx in range(int(BLOCK // CELL)):
            for dz in range(int(BLOCK // CELL)):
                c = (cx0 + dx, cz0 + dz)
                d = cells.get(c)
                if d and dominant(d["topo"]) in MASS_TOPOS:
                    eco.add(c)
    exs = [c[0] for c in eco]; ezs = [c[1] for c in eco]
    eco_bbox_cell = (min(exs), min(ezs), max(exs), max(ezs))
    log(f"ecotone core: {len(eco)} cells bbox_cell={eco_bbox_cell} "
        f"bbox_u=({min(exs)*CELL:.0f},{min(ezs)*CELL:.0f})-({(max(exs)+1)*CELL:.0f},{(max(ezs)+1)*CELL:.0f})")
    log(f"HIGH_U={HIGH_U} HORIZON_U={HORIZON_U} (carry horizon)  LAND_FLOOR_U={LAND_FLOOR_U}")

    per_side = {}
    log("-" * 92)
    for side in ("N", "S", "E", "W"):
        rays = march_side(cells, eco_bbox_cell, side)
        s = summarize(rays)
        per_side[side] = dict(summary=s, rays=rays)
        log(f"{side}: rays={s['n_rays']:2d}  lawful_term={s['frac_lawful_termination']*100:.0f}%  "
            f"mid_massif={s['frac_mid_massif']*100:.0f}%  first_wall_med={s['first_wall_u_median']}u  "
            f"foot_med={s['foot_depth_u_median']}u foot_max={s['foot_depth_u_max']}u  "
            f"terms={s['terms']}")

    # THE VERDICT: a side is CARRIABLE as a true-mesh wall strip iff a large fraction of its rays
    # terminate lawfully (FOOT_TO_LOWLAND/OCEAN) at a foot depth within the HORIZON, so the strip's
    # south edge can weld to minted grass/ocean via the apron conform.
    verdict = {}
    for side, d in per_side.items():
        s = d["summary"]
        carriable = (s["frac_lawful_termination"] >= 0.6
                     and s["foot_depth_u_median"] is not None
                     and s["foot_depth_u_median"] <= HORIZON_U)
        verdict[side] = dict(
            carriable_true_mesh_strip=carriable,
            reason=("lawful termination >=60% within horizon" if carriable else
                    (f"only {s['frac_lawful_termination']*100:.0f}% lawful / "
                     f"{s['frac_mid_massif']*100:.0f}% mid-massif -- the wall stays high past the "
                     f"carry horizon (no weldable foot)")))
    log("-" * 92)
    log("VERDICT (per side, true-mesh WALL-STRIP carriability):")
    for side, v in verdict.items():
        log(f"  {side}: carriable={v['carriable_true_mesh_strip']}  ({v['reason']})")

    s_carriable = verdict["S"]["carriable_true_mesh_strip"]
    overall = ("A narrow S-wall strip CAN terminate lawfully -> attempt-2 carries it + option(c)."
               if s_carriable else
               "The S-wall does NOT terminate lawfully within the carry horizon (its far side stays "
               "mid-massif). No narrow S band welds to lowland/ocean at this site. => attempt-2 stages "
               "OPTION (c) ALONE as the candidate; the FRESH EYE judges it against the MEASURED stock "
               "context (partial pocket, open n/e).")
    log("-" * 92); log(overall)

    result = dict(
        rung="F", step="attempt 2 -- south-wall termination probe (read-only)", date="2026-07-24",
        params=dict(HIGH_U=HIGH_U, HORIZON_U=HORIZON_U, LAND_FLOOR_U=LAND_FLOOR_U),
        ecotone_bbox_cell=list(eco_bbox_cell),
        per_side={k: v["summary"] for k, v in per_side.items()},
        per_side_rays={k: v["rays"] for k, v in per_side.items()},
        verdict=verdict,
        s_wall_carriable=s_carriable,
        overall=overall,
    )
    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")
    log(f"\n-> {OUT}")
    return result


if __name__ == "__main__":
    main()
