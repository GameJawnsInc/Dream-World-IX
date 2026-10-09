"""LAND -> SEA, census (2026-10-09): which real islands can `transplant.sink` turn into open sea, and why the rest
cannot.

Candidates: every land ASSEMBLY of island_pool.py (out/island_pool_d1.json; run it first), tried at a point on its own
land with `transplant.sink(..., dry_run=True)` -- the plan (unit, region, keel, T-junction and coverage gates) and then
every block's in-place morph gates (frame, stitch, entrance). One verdict each: the plan's refusal (its first words),
the morph gate that failed, or SINKABLE. Every sinkable island is tried on disc 4 too (the same point, disc 4's bytes).
Reads stock only, writes nothing to the game (a dry run). Writes out/sink_census.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sink_census.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
KEYS = ("no land lies", "owns shallow", "runs past", "no sea4 part", "shares a 4u tile", "crosses the edge",
        "entrance bits", "part-way along", "does not cover")


def verdict(at, disc):
    from ff9mapkit.world import transplant as TR
    try:
        s = TR.sink("FF9CustomMap_test_nonexistent", tuple(at), disc=disc, dry_run=True)
    except ValueError as e:
        msg = str(e)
        return {"verdict": next((k for k in KEYS if k in msg), msg[:60]), "why": msg[:400]}
    bad = [(b, g) for b, r in s["per_block"].items() for g in r["gates"] if not g.get("ok", True)]
    keep = ("at", "blocks", "tiles", "land_tris", "land_u2", "max_y", "entrance_tris", "fill_tris", "fill_area",
            "sea_replaced", "keel_to_open", "dropped", "samples")
    return {"verdict": "SINKABLE" if not bad else f"gate:{bad[0][1]['gate']}",
            "plan": {k: s.get(k) for k in keep},
            "failed": [{"block": b, **{k: v for k, v in g.items() if k in ("gate", "welds", "torn", "blocks",
                                                                         "applied", "expected", "exempt")}}
                       for b, g in bad]}


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    pool = json.loads((HERE / "out" / "island_pool_d1.json").read_text(encoding="utf-8"))
    rows = []
    for r in pool:
        v = verdict(r["at"], 1)
        row = {"cells": r["cells"][:6], "n_cells": len(r["cells"]), "land_u2": r["land_u2"], "at": r["at"], **v}
        if v["verdict"] == "SINKABLE":
            row["disc4"] = verdict(r["at"], 4)
        rows.append(row)
        print(f"{r['land_u2']:9.1f}u2 {len(r['cells']):3d} blocks {r['cells'][:3]} -> {v['verdict']}"
              + (f"   disc 4: {row['disc4']['verdict']}" if "disc4" in row else "")
              + (f"   [{v['why'][:110]}]" if "why" in v and v["verdict"] not in ("owns shallow",) else ""))
    res = {"assemblies": len(rows), "verdicts": dict(Counter(r["verdict"] for r in rows)),
           "disc4": dict(Counter(r["disc4"]["verdict"] for r in rows if "disc4" in r)), "rows": rows}
    (HERE / "out" / "sink_census.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(res["verdicts"], "disc 4:", res["disc4"])


if __name__ == "__main__":
    main()
