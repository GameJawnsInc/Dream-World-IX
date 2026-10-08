"""CALIBRATION of the carry stitch gate (terrain study defect 10 and ranked experiment O1's last step, 2026-10-08).

``transplant`` / ``transplant_region`` now run a ``stitch`` gate row: every donor weld must hold in the carry, the
carried parts mapped through the tweaks, the rotation and the shift, the parts the carry does not take (Object,
river, falls, volcano ...) held at the pose the donor's prefab renders them. ``weld_audit`` (the gate it backs up)
flags only near-miss pairs under 0.05u.

Population: every disc-1 land block as a single-cell donor, carried onto open-ocean (23,10) with the kit defaults
(rot 0, shift auto, strips auto), dry run. Records, per donor, the stitch row, the object-anchor row and whether the
carry was clean before the change (every other gate ok).

Registered prediction (README O1): "fires on 0 accepted carries; any carry that fires names a partner outside
PARTS". The population here is wider than the accepted carries (a default carry of any block), so firing is expected
where the auto shift moves the carried ground off a prefab part it is welded to; the object-anchor gate already
refuses the Object half of that class.
Writes out/carry_gate_calibration.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/carry_gate_calibration.py
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
from ff9mapkit.world import extract as X               # noqa: E402
from ff9mapkit.world import transplant as TR           # noqa: E402

TARGET = (23, 10)


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    donors = sorted({(b[0], b[1]) for b in X.list_blocks(disc=1, game=S.GAME)})
    rows, t0 = [], time.time()
    for d in donors:
        try:
            s = TR.transplant("FF9CustomMap-calibration-absent", cell=TARGET, donor=d, game=S.GAME, dry_run=True)
        except ValueError as e:
            rows.append({"donor": list(d), "error": str(e)[:160]})
            continue
        st = next(g for g in s["gates"] if g["gate"] == "stitch")
        oa = next((g for g in s["gates"] if g["gate"] == "object-anchor"), None)
        old_clean = all(g["ok"] for g in s["gates"] if g["gate"] != "stitch")
        rows.append({"donor": list(d), "shift": s["shift"], "old_clean": old_clean, "stitch_ok": st["ok"],
                     "torn": st["torn"], "rewelded": st["rewelded"], "welds": st["welds"], "max_sep": st["max_sep"],
                     "by_mesh": st["by_mesh"], "sample": st["sample"],
                     "object_anchor_ok": None if oa is None else oa["ok"]})
        if not st["ok"]:
            print(f"  {d}: shift {s['shift']} torn {st['torn']} max {st['max_sep']} {sorted(st['by_mesh'])} "
                  f"old_clean={old_clean} object_anchor={None if oa is None else oa['ok']}", flush=True)
    ok_rows = [r for r in rows if "error" not in r]
    fired = [r for r in ok_rows if not r["stitch_ok"]]
    fired_old_clean = [r for r in fired if r["old_clean"]]
    partners = Counter(m for r in fired for m in r["by_mesh"] if not m.startswith("carried"))
    partners_old_clean = Counter(m for r in fired_old_clean for m in r["by_mesh"] if not m.startswith("carried"))
    res = {"target": list(TARGET), "donors": len(donors), "ran": len(ok_rows),
           "errors": len(rows) - len(ok_rows), "old_clean": sum(1 for r in ok_rows if r["old_clean"]),
           "fired": len(fired), "fired_on_old_clean": len(fired_old_clean),
           "fired_zero_shift": sum(1 for r in fired if r["shift"] == [0.0, 0.0]),
           "fired_with_object_anchor_ok": sum(1 for r in fired if r["object_anchor_ok"] is not False),
           "partners": dict(partners), "partners_old_clean": dict(partners_old_clean),
           "old_clean_fired_donors": [r["donor"] for r in fired_old_clean],
           "seconds": round(time.time() - t0), "rows": rows}
    p = S.OUT / "carry_gate_calibration.json"
    p.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1, default=str))
    print("->", p)


if __name__ == "__main__":
    main()
