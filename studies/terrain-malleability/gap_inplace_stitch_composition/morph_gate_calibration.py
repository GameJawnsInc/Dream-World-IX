"""CALIBRATION of the in-place morph's new gates (terrain study defects 6 and 10-11, 2026-10-08).

``transplant.morph_in_place`` now runs two more gate rows: ``stitch`` (every weld on the cell, the parts it does not
load held where they are) and ``entrance`` (the morph moves the land of a cell with walk-on entrance tiles). Before
trusting them, run them over the ACCEPTED population: every morph the ``world-morphs`` scanner certifies (the
scanner probes each verb down its depth ladder and counts a rung only if ``morph_in_place``'s dry run is clean; the
in-game-proven coast morphs are drawn from this catalog).

Each ``morph_in_place`` call the scanner makes is recorded. A call is OLD-CLEAN when every gate except the two new
rows passes (what the scanner certified before the change). The scanner stops at the first clean rung of each
ladder, so the number of calls depends on the gates in force: compare the old-clean calls of ONE run, not counts
across runs. Registered predictions:
  * stitch fires on 0 old-clean morphs whose tweaks touch only the loaded parts' own welds; any that fires names a
    partner outside ``transplant.PARTS`` (the study's S10: Object, Stream, River, RiverJoint, Falls, Volcano,
    Beach2, Sea6);
  * entrance fires only on cells carrying stock entrance tiles. A refusal (raised landing ground, a dropped tile)
    is counted apart from a report (a tile moved within the limits).
Result 2026-10-08, final gates: 453 old-clean morphs; stitch refuses 4, all one cliff window at (8,15) whose
~0.75u move left a Sea6 vertex behind; entrance refuses 0 and reports moved tiles on 2 ((13,3), (14,2)). An
earlier run under a whole-block entrance rule refused 686 of 1,075 old-clean morphs on 31 cells: why it was dropped.
Writes out/morph_gate_calibration.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/morph_gate_calibration.py
      [--blocks 7,17 18,3 ...]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
from ff9mapkit.world import coastscan as CS            # noqa: E402
from ff9mapkit.world import extract as X               # noqa: E402
from ff9mapkit.world import transplant as TR           # noqa: E402

NEW = {"stitch", "entrance"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", nargs="*", default=None, help="x,y blocks (default: every disc-1 land block)")
    a = ap.parse_args()
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    blocks = ([tuple(int(v) for v in b.split(",")) for b in a.blocks] if a.blocks
              else sorted({(b[0], b[1]) for b in X.list_blocks(disc=1, game=S.GAME)}))
    calls = []
    real = TR.morph_in_place

    def spy(mod_folder, *, cell, tweaks, **k):
        s = real(mod_folder, cell=cell, tweaks=tweaks, **k)
        old_ok = all(g.get("ok", True) for g in s["gates"] if g["gate"] not in NEW)
        st = next((g for g in s["gates"] if g["gate"] == "stitch"), None)
        en = next((g for g in s["gates"] if g["gate"] == "entrance"), None)
        calls.append({"cell": list(cell), "tweaks": [type(t).__name__ for t in tweaks], "touched": s["touched"],
                      "old_clean": old_ok, "stitch_ok": st is None or st["ok"],
                      "stitch": {k2: st[k2] for k2 in ("welds", "torn", "max_sep", "by_mesh", "sample")} if st else None,
                      "entrance": en["blocks"] if en else None, "new_clean": s["clean"]})
        return s
    TR.morph_in_place = spy
    t0 = time.time()
    per_block = {}
    for (bx, by) in blocks:
        n0 = len(calls)
        try:
            CS.scan_block(bx, by, game=S.GAME)
        except Exception as e:                                                  # noqa: BLE001
            per_block[f"{bx},{by}"] = {"error": f"{type(e).__name__}: {str(e)[:160]}"}
            continue
        if len(calls) > n0:
            per_block[f"{bx},{by}"] = {"calls": len(calls) - n0}
            print(f"  ({bx},{by}): {len(calls) - n0} morph dry-runs, {time.time() - t0:.0f}s", flush=True)
    TR.morph_in_place = real
    old = [c for c in calls if c["old_clean"]]
    st_fire = [c for c in old if not c["stitch_ok"]]
    en_fire = [c for c in old if c["entrance"] and any(h["refused"] for h in c["entrance"])]
    en_note = [c for c in old if c["entrance"] and not any(h["refused"] for h in c["entrance"])]
    partners = Counter(m.split(" ", 1)[1] for c in st_fire for m in c["stitch"]["by_mesh"])
    res = {"blocks": len(blocks), "calls": len(calls), "old_clean": len(old),
           "stitch_fired_on_old_clean": len(st_fire), "entrance_fired_on_old_clean": len(en_fire),
           "entrance_reported_only": len(en_note),
           "stitch_partners": dict(partners),
           "stitch_cells": sorted({tuple(c["cell"]) for c in st_fire}),
           "entrance_cells": sorted({tuple(c["cell"]) for c in en_fire}),
           "entrance_reported_cells": sorted({tuple(c["cell"]) for c in en_note}),
           "still_clean": sum(1 for c in old if c["new_clean"]),
           "per_block": per_block, "stitch_examples": st_fire[:12], "entrance_examples": (en_fire + en_note)[:6],
           "seconds": round(time.time() - t0)}
    p = S.OUT / "morph_gate_calibration.json"
    p.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("per_block", "stitch_examples", "entrance_examples")},
                     indent=1, default=str))
    print("->", p)


if __name__ == "__main__":
    main()
