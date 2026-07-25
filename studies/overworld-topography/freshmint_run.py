"""THE FRESH-SITE PROOF driver -- runs ``junction_compose.compose`` at a FRESH site (2026-07-25).

Everything site-specific is a parameter of the site dict; no constant from the rung-F build survives
here.  ``--radius`` lets the caller probe the site-capacity boundary; ``--site`` picks the centre.

    py -X utf8 freshmint_run.py --cx 160 --cz -128 --radius 125
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import junction_compose as JC        # noqa: E402
import rung_f_layout as RFL          # noqa: E402

CELL = 4.0
BLOCK = 64.0
# the donor blob's own pre-shift centre: the 3x2-block ecotone core 13-15,11-12 = cell rect
# x[208,255] y[-208,-177] = world [832,1024]x[-832,-704] -> centre (928,-768).
BLOB_CENTER = (928.0, -768.0)


def fresh_site(cx, cz, radius, stage_dir, *, name, seed=40.0, land_height=3.0,
               undulation=0.02, n_corners=0, corner_strength=0.0, site_pad=1):
    """A site dict for ``junction_compose.compose``.  THE WHOLE-BLOCK SHIFT LAW
    (rung_f_layout:113) is asserted here, at the only place a fresh site is minted."""
    shift_world = (cx - BLOB_CENTER[0], cz - BLOB_CENTER[1])
    shift_cells = (int(round(shift_world[0] / CELL)), int(round(shift_world[1] / CELL)))
    assert abs(shift_cells[0] * CELL - shift_world[0]) < 1e-6
    assert abs(shift_cells[1] * CELL - shift_world[1]) < 1e-6
    assert shift_cells[0] % 16 == 0 and shift_cells[1] % 16 == 0, (
        f"THE WHOLE-BLOCK SHIFT LAW: shift_cells={shift_cells} is a PHASE shift; it would "
        f"re-partition every donor border tri into un-weldable T-junctions (rung_f_layout:113)")
    r = radius
    bx0 = max(0, int((cx - r) // BLOCK) - site_pad)
    bx1 = int((cx + r) // BLOCK) + site_pad
    by0 = max(0, int((-cz - r) // BLOCK) - site_pad)
    by1 = int((-cz + r) // BLOCK) + site_pad
    site_blocks = {(bx, by) for bx in range(bx0, bx1 + 1) for by in range(by0, by1 + 1)}
    return dict(
        name=name,
        island_center=(float(cx), float(cz)), island_radius=float(radius),
        land_height=land_height, island_seed=seed, island_undulation=undulation,
        island_n_corners=n_corners, island_corner_strength=corner_strength,
        site_blocks=site_blocks,
        donor_cell_x=RFL.DONOR_CELL_X, donor_cell_y=RFL.DONOR_CELL_Y,
        donor_blocks=list(RFL.DONOR_BLOCKS), shift_cells=shift_cells,
        drop_set=set(RFL.DROP_SET), qo_seed=JC.QO_SEED,
        stage_dir=Path(stage_dir))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cx", type=float, required=True)
    ap.add_argument("--cz", type=float, required=True)
    ap.add_argument("--radius", type=float, default=125.0)
    ap.add_argument("--seed", type=float, default=40.0)
    ap.add_argument("--name", default=None)
    ap.add_argument("--stage", default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--no-contract", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args(argv)
    name = a.name or f"freshmint_{int(a.cx)}_{int(a.cz)}_r{int(a.radius)}"
    out = HERE / "out" / "foldback"
    out.mkdir(parents=True, exist_ok=True)
    stage = Path(a.stage) if a.stage else out / "freshmint-tree"
    logs = []
    log = JC.log_maker(logs)
    try:
        R = JC.compose(fresh_site(a.cx, a.cz, a.radius, stage, name=name, seed=a.seed),
                       log=log, run_contract=not a.no_contract, render=not a.no_render)
    except Exception as e:                                   # noqa: BLE001
        import traceback
        tb = traceback.format_exc()
        log(f"COMPOSE RAISED: {type(e).__name__}: {e}")
        R = dict(meta=dict(site=name), all_green=False, raised=f"{type(e).__name__}: {e}",
                 traceback=tb, gates=[], failed=["<exception before the battery completed>"])
    R["site_params"] = dict(cx=a.cx, cz=a.cz, radius=a.radius, seed=a.seed,
                            shift_cells=list(fresh_site(a.cx, a.cz, a.radius, stage,
                                                        name=name)["shift_cells"]))
    R["log"] = logs
    rp = Path(a.report) if a.report else out / f"{name}.json"
    rp.write_text(json.dumps(R, indent=1, default=str))
    print(f"\nwrote {rp}")
    return 0 if R.get("all_green") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
