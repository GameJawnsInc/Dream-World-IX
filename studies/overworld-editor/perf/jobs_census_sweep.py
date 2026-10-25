"""Lane jobs: the census prototype (jobs_census_proto P1) against the unpatched placement.census on EVERY deployed
block of the lane's draft, both meshlist shapes census_gate builds (the deployed stack with the real parts, and the
hidden-blank + cut-sea stack the island lane uses), asserted == block by block, and timed kernel to kernel
(perf_counter, unprofiled, same process, alternating order per block).

    py studies/overworld-editor/perf/jobs_census_sweep.py      -> out/perf/jobs/census_sweep.json
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402
import jobs_census_proto as CP  # noqa: E402


def main():
    from ff9mapkit.world import interior as IN
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import placement as P
    from ff9mapkit.world.island import _cut_plane, _sea_plane
    d = J.draft()
    orig = P.census
    CP.install_p1()
    patched = P.census
    P.census = orig
    blocks = IN.read_deployed_blocks(str(d), near=(768.0, -640.0), reach=735.0, game=J.GAME)
    stack = IN.read_deployed_stack(str(d), blocks, game=J.GAME)
    plane = _sea_plane(1, game=J.GAME)
    t_o = t_p = 0.0
    n = same = 0
    for k, (blk, bm) in enumerate(sorted(blocks.items())):
        bx, by = blk
        wbx = M.wrap_block_col(bx)
        aux = {P.canonical_part(p_): IN._wrap_label(m_, P.canonical_part(p_))
               for p_, m_ in (stack.get(blk) or {}).items() if P.canonical_part(p_) != "Terrain"}
        ml_stack = P.build_meshlist({**aux, "Terrain": IN._wrap_label(bm, "Terrain")})
        hid = lambda nm_: M.hidden_block_mesh(name=nm_, disc=1, x=wbx, y=by)  # noqa: E731
        ml_blank = P.build_meshlist({"Object": hid("Object"), "Terrain": IN._wrap_label(bm, "Terrain"),
                                     "Sea1": hid("Sea1"), "Sea2": hid("Sea2"), "Sea3": hid("Sea3"),
                                     "Sea4": _cut_plane(plane, bx, by, frozenset(), bm, label_x=wbx,
                                                        rule="corners"),
                                     "Sea5": hid("Sea5")})
        for ml in (ml_stack, ml_blank):
            arms = [("o", orig), ("p", patched)] if k % 2 == 0 else [("p", patched), ("o", orig)]
            out = {}
            for tag, fn in arms:
                t = time.perf_counter()
                out[tag] = fn(ml, frame="block_local")
                dt = time.perf_counter() - t
                if tag == "o":
                    t_o += dt
                else:
                    t_p += dt
            n += 1
            same += out["o"] == out["p"]
            assert out["o"] == out["p"], blk
    rec = {"blocks": len(blocks), "censuses_each_way": n, "identical": same, "orig_s": t_o, "patched_s": t_p,
           "speedup": t_o / t_p if t_p else None}
    print(json.dumps(rec))
    (J.OUT / "census_sweep.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
