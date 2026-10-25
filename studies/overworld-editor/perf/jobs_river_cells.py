"""Lane jobs: can world-river's MOVE skip its probe composition? river.deploy(move_from=...) composes the river at the
OLD placement (~10 s, no folder check) only to read plan["cells"] -- the cells the old deploy wrote. The editor
already assumes those cells are the home composition's cells shifted by whole blocks (riveredit.RiverShape.cells_at:
"a whole-block shift moves every cell by the same block step, so the cells need composing once").

This probe tests that assumption against the verb's own composition at EVERY placement the editor offers
(riveredit.shape().shifts, nearest first): compose(frag, offset=offset_of(s), window, ol, disc) exactly as deploy's
probe call does, and compare sorted(plan cells) with rs.cells_at(s). It writes nothing.

    py studies/overworld-editor/perf/jobs_river_cells.py [limit]     -> out/perf/jobs/river_cells.json
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402


def main():
    from ff9mapkit.world import river as R
    from ff9mapkit.world import riveredit as RE
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 6
    t = time.perf_counter()
    rs = RE.shape(game=J.GAME)
    t_shape = time.perf_counter() - t
    donor = R.CLUSTER_C
    win = R.read_window(donor, game=J.GAME)
    frag = R.build_fragment(win, donor)
    ol = R.outline(frag)
    out = {"shape_s": t_shape, "shifts": len(rs.shifts), "checked": [], "mismatch": []}
    for s in rs.shifts[:limit]:
        t = time.perf_counter()
        try:
            comp = R.compose(frag, offset=RE.offset_of(s), window=win, ol=ol, disc=donor.disc, game=J.GAME)
            cells = sorted(tuple(int(v) for v in k.split(",")) for k in comp.plan["cells"])
            err = None
        except Exception as e:  # noqa: BLE001 -- a refusal is a result too (deploy's probe would raise the same)
            cells, err = None, f"{type(e).__name__}: {e}"[:300]
        dt = time.perf_counter() - t
        pred = rs.cells_at(s)
        same = cells == pred
        rec = {"shift": list(s), "s": round(dt, 2), "same": same, "err": err, "n_cells": len(cells or [])}
        out["checked"].append(rec)
        if not same:
            out["mismatch"].append({**rec, "composed": cells, "predicted": pred})
        print(f"shift {s}: {dt:5.1f}s cells {len(cells or [])} same={same} {err or ''}", flush=True)
        (J.OUT / "river_cells.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"== {len(out['checked'])} placements, {len(out['mismatch'])} mismatch")


if __name__ == "__main__":
    main()
