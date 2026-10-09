"""ISLAND CLUSTERS, the census (2026-10-09): which real islands can `world-sink` take now, and how?

Every land component of disc 1 within 9 blocks (`transplant.sink_candidates`), deployed dry with `transplant.sink`
(the plan and every block's in-place morph gates: frame, stitch, entrance): the whole-tile sink, or -- where the island's
water joins another coast's -- the island alone with its neighbours kept (the footprint sink); a refused island that
joins others is also tried with `--cluster`. One verdict each, the fill used, and disc 4 for every sinkable one.
Entrance tiles on an island are counted (a deploy needs --allow-entrances there) but do not refuse here.
Reads stock only, writes nothing to the game. Writes out/sh_c5_census.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_c5_census.py
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))


def verdict(at, disc, cluster=False):
    from ff9mapkit.world import transplant as TR
    try:
        s = TR.sink("FF9CustomMap_test_nonexistent", tuple(at), disc=disc, dry_run=True, cluster=cluster,
                    allow_entrances=True)
    except ValueError as e:
        return {"verdict": "refused", "why": str(e)[:300]}
    bad = [(b, g) for b, r in s["per_block"].items() for g in r["gates"] if not g.get("ok", True)]
    keep = ("fill", "blocks", "tiles", "land_tris", "land_u2", "shore_tris", "bands", "band_flips", "fill_tris",
            "cells_whole", "cells_partial", "split_tris", "keel_to_open", "entrance_tris", "members")
    return {"verdict": "SINKABLE" if not bad else f"gate:{bad[0][1]['gate']}",
            "plan": {k: s.get(k) for k in keep},
            "failed": [{"block": b, **{k: v for k, v in g.items() if k in ("gate", "welds", "torn", "applied",
                                                                         "expected", "exempt")}} for b, g in bad]}


def main():
    import ff9mapkit
    from ff9mapkit.world import transplant as TR
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    t0 = time.time()
    rows = TR.sink_candidates(disc=1)
    out = []
    for r in rows:
        v = verdict(r["at"], 1)
        row = {"at": r["at"], "land_u2": r["land_u2"], **v}
        if v["verdict"] == "SINKABLE":
            row["disc4"] = verdict(r["at"], 4)["verdict"]
        if r.get("cluster") and r["cluster"]["ok"]:
            c = verdict(r["at"], 1, cluster=True)
            row["cluster"] = {"verdict": c["verdict"], "members": (c.get("plan") or {}).get("members"),
                              "blocks": (c.get("plan") or {}).get("blocks"), "why": c.get("why")}
            if c["verdict"] == "SINKABLE":
                row["cluster"]["disc4"] = verdict(r["at"], 4, cluster=True)["verdict"]
        out.append(row)
        fill = (v.get("plan") or {}).get("fill", "-")
        print(f"{r['land_u2']:9.1f}u2 at {r['at']} -> {v['verdict']} ({fill})"
              + (f" disc4 {row['disc4']}" if "disc4" in row else "")
              + (f"  entrance tris {v['plan']['entrance_tris']}" if v.get("plan", {}).get("entrance_tris") else "")
              + (f"  | cluster of {len(row['cluster']['members'] or [])}: {row['cluster']['verdict']}"
                 f" disc4 {row['cluster'].get('disc4')}" if "cluster" in row else "")
              + (f"  [{v['why'][:110]}]" if "why" in v else ""), flush=True)
    res = {"islands": len(out), "verdicts": dict(Counter(f"{r['verdict']} ({(r.get('plan') or {}).get('fill', '-')})"
                                                         for r in out)),
           "disc4": dict(Counter(r["disc4"] for r in out if "disc4" in r)),
           "clusters": len({json.dumps(r["cluster"]["blocks"]) for r in out if "cluster" in r
                            and r["cluster"]["verdict"] == "SINKABLE"}),
           "seconds": round(time.time() - t0), "rows": out}
    (HERE / "out" / "sh_c5_census.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(res["verdicts"], "disc 4:", res["disc4"], "clusters:", res["clusters"], f"{res['seconds']}s")


if __name__ == "__main__":
    main()
