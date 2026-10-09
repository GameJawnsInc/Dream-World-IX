"""LAND -> SEA with shallows, the census (2026-10-09): which real islands can the re-banding sink take, and why not the
rest?

Every land COMPONENT of disc 1 within 9 blocks (`transplant.sink_candidates`: terrain and beach1 joined by shared
vertices), tried with `transplant.sink(..., dry_run=True)`: the plan (shore, region, bands, gates) and then every block's
in-place morph gates (frame, stitch, entrance). One verdict each; a sinkable island is tried on disc 4 too. Reads stock
only, writes nothing to the game. Writes out/sh_q5_census.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_q5_census.py
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


def verdict(at, disc):
    from ff9mapkit.world import transplant as TR
    try:
        s = TR.sink("FF9CustomMap_test_nonexistent", tuple(at), disc=disc, dry_run=True)
    except ValueError as e:
        return {"verdict": "refused", "why": str(e)[:300]}
    bad = [(b, g) for b, r in s["per_block"].items() for g in r["gates"] if not g.get("ok", True)]
    keep = ("blocks", "tiles", "land_tris", "land_u2", "shore_tris", "bands", "band_flips", "fill_tris",
            "sea_replaced", "edge_welds", "keel_to_open", "entrance_tris")
    return {"verdict": "SINKABLE" if not bad else f"gate:{bad[0][1]['gate']}",
            "plan": {k: s.get(k) for k in keep},
            "failed": [{"block": b, **{k: v for k, v in g.items() if k in ("gate", "welds", "torn", "applied",
                                                                         "expected", "exempt", "why")}}
                       for b, g in bad]}


def main():
    import ff9mapkit
    from ff9mapkit.world import transplant as TR
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    t0 = time.time()
    rows = TR.sink_candidates(disc=1)
    out = []
    for r in rows:
        v = verdict(r["at"], 1)
        row = {"at": r["at"], "land_u2": r["land_u2"], "blocks": r["blocks"], **v}
        if v["verdict"] == "SINKABLE":
            row["disc4"] = verdict(r["at"], 4)
        out.append(row)
        tag = v["verdict"] + (f" / disc 4 {row['disc4']['verdict']}" if "disc4" in row else "")
        info = (f"bands {v['plan']['bands']} shore {v['plan']['shore_tris']} flips {v['plan']['band_flips']}"
                if "plan" in v else v.get("why", "")[:150])
        print(f"{r['land_u2']:9.1f}u2 {len(r['blocks']):2d} blk at {r['at']} -> {tag}  {info}", flush=True)
    res = {"islands": len(out), "verdicts": dict(Counter(r["verdict"] for r in out)),
           "disc4": dict(Counter(r["disc4"]["verdict"] for r in out if "disc4" in r)),
           "seconds": round(time.time() - t0), "rows": out}
    (HERE / "out" / "sh_q5_census.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(res["verdicts"], "disc 4:", res["disc4"], f"{res['seconds']}s")


if __name__ == "__main__":
    main()
