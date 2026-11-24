"""Rung P5 measurement: a prefab's walked land TURNED (world/prefab.py, THE QUARTER TURN), on real bytes, offline.

For each island prefab and each quarter turn it stages the turned placement exactly as ``world-prefab --turn`` does
(the walked land composed at its catalog site and held to the catalog, then turned onto the target) and runs two
checks:

1. world-prefab's own identity verdict (``_identity_turned``): the written triangles are the catalog's, turned.
2. An INDEPENDENT oracle, the engine-faithful ground query (``coastnav._query_top``: registration order, the IDALL
   skip set, up-facing by geometric winding): every 2u sample over the walked land must answer the same part,
   topograph and height at its turned point in the turned land. This one never reads the turn's own code paths except
   ``turn_point`` (the rigid map it checks against).

Nothing is written to the install: every folder is a temp folder outside it. Usage (from the worktree root):
    py studies/overworld-editor/prefab_turn_probe.py [--sites 1,14 1,16 0,12] [--names desert-peak-isle ...]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
PKG = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(PKG))
import ff9mapkit  # noqa: E402

assert Path(ff9mapkit.__file__).resolve().is_relative_to(PKG), ff9mapkit.__file__   # the worktree's package
from ff9mapkit.world import coastnav as CN  # noqa: E402
from ff9mapkit.world import prefab as PF  # noqa: E402


def ground_answers(root, prefab, cell, turn, src_cell, map_turn=None):
    """(compared, mismatches[:10]) over 2u samples of the walked footprint at src_cell vs the turned land on cell."""
    src = CN._Loader(str(root["source"]["root"]), 1, None)
    tgt = CN._Loader(str(root["root"]), 1, None)
    n, bad = 0, []
    ox, oz = PF.origin(src_cell)
    for b in PF._source_foot(prefab):
        x0, ztop = ox + 64.0 * b[0], oz + 64.0 - 64.0 * b[1]
        for i in range(32):
            for j in range(32):
                x, z = x0 + 1.0 + 2.0 * i, ztop - 1.0 - 2.0 * j
                a = CN._query_top(src, x, z)
                # the same frame-relative point of the land anchored on `cell`, turned
                rx, rz = x - ox, z - oz
                tx, tz = PF.turn_point(PF.origin(cell)[0] + rx, PF.origin(cell)[1] + rz, prefab, cell,
                                       turn if map_turn is None else map_turn)
                c = CN._query_top(tgt, tx, tz)
                n += 1
                ka = None if a is None else (a[0], a[1], round(a[2], 4))
                kc = None if c is None else (c[0], c[1], round(c[2], 4))
                if ka != kc:
                    bad.append({"at": [x, z], "turned": [tx, tz], "walked": ka, "turned_land": kc})
    return n, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", nargs="*", default=["desert-peak-isle", "meadow-grove-isle"])
    ap.add_argument("--sites", nargs="*", default=["1,14", "1,16", "0,12"])
    ap.add_argument("--turns", nargs="*", type=int, default=[90, 180, 270])
    ap.add_argument("--fcell", nargs="*", default=[], help="name=bx,by: a source site for an entry that names none")
    ap.add_argument("--out", default=str(HERE.parent / "evidence" / "prefab-turn" / "probe.json"))
    a = ap.parse_args()
    out = []
    for name in a.names:
        entry = dict(PF.get(name), turns=[0, 90, 180, 270])
        for f in a.fcell:
            k, v = f.split("=")
            if k == name:
                entry["fingerprint_cell"] = [int(c) for c in v.split(",")]
        for site in a.sites:
            cell = tuple(int(v) for v in site.split(","))
            for turn in a.turns:
                view = PF.turned(entry, turn)
                t0 = time.time()
                row = {"name": name, "cell": list(cell), "turn": turn, "footprint": view["footprint"]}
                st = None
                try:
                    st = PF.stage_turned(entry, turn, cell)
                    row["blocks"] = len(st["blocks"])
                    try:
                        row["identity"] = PF._identity_turned(view, name, cell, st, game=None, log=lambda *_: None)
                    except PF.PrefabRefused as e:
                        row["identity"] = f"REFUSED[{e.gate}]: {e}"
                    near = PF.stock_land_near(view, cell)
                    row["beside_stock_land"] = sorted(near)
                    n, bad = ground_answers(st, entry, cell, turn, PF.source_cell(entry))
                    row["ground_samples"] = n
                    row["ground_mismatches"] = len(bad)
                    # beside stock land the stamp re-classes margin sea: report class-only diffs apart
                    row["ground_mismatch_examples"] = bad[:8]
                    # THE NEGATIVE CONTROL: the same comparison through the WRONG map (one quarter turn short) must
                    # mismatch, or the oracle cannot fail
                    _, wrong = ground_answers(st, entry, cell, turn, PF.source_cell(entry), map_turn=(turn - 90) % 360)
                    row["control_wrong_map_mismatches"] = len(wrong)
                    row["height_or_part_mismatches"] = sum(
                        1 for m in bad if (m["walked"] is None) != (m["turned_land"] is None)
                        or (m["walked"] and (m["walked"][0] != m["turned_land"][0]
                                             or abs(m["walked"][2] - m["turned_land"][2]) > 1e-3)))
                except PF.PrefabRefused as e:
                    row["identity"] = f"REFUSED[{e.gate}]: {e}"
                finally:
                    PF._drop(st)
                row["seconds"] = round(time.time() - t0, 1)
                print(json.dumps({k: v for k, v in row.items() if k != "ground_mismatch_examples"}), flush=True)
                out.append(row)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
