"""SKEPTIC re-run for lane jobs, candidate R1: does world-river's move probe composition (river.deploy's
compose(frag, offset=move_from, ...) with no folder check) yield exactly riveredit.RiverShape.cells_at(shift)? The lane
checked all 28 offered placements; this re-checks K of them picked at random (seeded), each composed exactly as
deploy's probe call does (area=None, apron=True defaults, the donor's disc), timed. Writes nothing in the kit.

    py studies/overworld-editor/perf/verify_jobs_river_cells.py K [seed]  -> out/perf/jobs/verify/river_cells.json
"""
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

VOUT = J.OUT / "verify"


def main():
    from ff9mapkit.world import river as R
    from ff9mapkit.world import riveredit as RE
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    rs = RE.shape(game=J.GAME)
    donor = R.CLUSTER_C
    win = R.read_window(donor, game=J.GAME)
    frag = R.build_fragment(win, donor)
    ol = R.outline(frag)
    picks = random.Random(seed).sample(list(rs.shifts), k)
    out = {"shifts_offered": len(rs.shifts), "checked": []}
    for s in picks:
        t = time.perf_counter()
        comp = R.compose(frag, offset=RE.offset_of(s), window=win, ol=ol, area=None, apron=True, disc=donor.disc,
                         game=J.GAME)
        dt = time.perf_counter() - t
        cells = sorted(tuple(int(v) for v in c.split(",")) for c in comp.plan["cells"])
        rec = {"shift": list(s), "compose_s": round(dt, 2), "same": cells == rs.cells_at(s), "n": len(cells)}
        print(json.dumps(rec), flush=True)
        out["checked"].append(rec)
    out["all_same"] = all(r["same"] for r in out["checked"])
    (VOUT / "river_cells.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
