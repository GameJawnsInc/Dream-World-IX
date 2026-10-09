"""SITE SCAN for in-game round 9 (2026-10-09): a real cliff coast that disc 4 redrew, for the disc-4 replay of
`world-transplant --in-place --cliff-bump`. Reads stock only; writes out/r9_site_scan.json.

The candidates are the terrain study's 116 coastal cells where a certified cliff bump replays cleanly on disc 4
(gap_disc4_edit_reach/s7_morph_replay.py, part B). The round's measure is a walk: the cliff band (topograph 58) is not
walkable, so walking seaward stops at its top edge (the crease), and the bump moves that edge out by depth*sin^2(pi t).
A site is usable when, at the window's middle column, on BOTH discs:
  - the seaward normal is within 12 deg of a cardinal bearing (the harness walks straight lines on a bearing);
  - 6u inland of the crease, every 0.5u back to it, is walkable ground (topograph in WALK_OK) on the Terrain part;
  - no live mod folder overrides the cell (the lab's files must be the only change there).
Ranked by how far disc 4's crease sits from disc 1's (a site where the two discs' coasts differ at the walk line shows
that disc 4 got its OWN coast bumped, not disc 1's copied), then by the bump depth at the middle.
Run:  py studies/terrain-malleability/ingame/r9_site_scan.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3_build as RB                                # noqa: E402  (the sky ground query, the bind oracle)

S7 = HERE.parent / "gap_disc4_edit_reach" / "out" / "s7_morph_replay.json"
INLAND = 6.0
STEP = 0.5


def column(win, depth):
    """The middle column: (base, crease, nhat, d) where the bump is deepest."""
    ts = win.arc_params()
    i = max(range(1, len(ts) - 1), key=lambda k: math.sin(math.pi * ts[k]) ** 2)
    return win.base[i], win.crease[i], win.nhat, depth * math.sin(math.pi * ts[i]) ** 2


def cardinal(nhat):
    b = math.degrees(math.atan2(nhat[1], nhat[0])) % 360.0
    c = round(b / 90.0) * 90.0 % 360.0
    return b, c, abs((b - c + 180.0) % 360.0 - 180.0)


def inland_ok(disc, crease, nhat):
    from ff9mapkit.world.placement import WALK_OK
    rows = []
    for k in range(1, int(INLAND / STEP) + 1):
        s = k * STEP
        g = RB.ground(None, disc, crease[0] - s * nhat[0], crease[2] - s * nhat[1])
        rows.append((s, g["part"], g["topo"]))
        if g["part"] != "Terrain" or g["topo"] not in WALK_OK:
            return False, rows
    return True, rows


def main():
    import ff9mapkit
    from ff9mapkit.world import coastmorph as CM
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    rows = [r for r in json.loads(S7.read_text(encoding="utf-8"))["partB"]["rows"] if r["replay_d4_clean"]]
    live = {(ns, bx, by) for (ns, bx, by) in RB._cells(None)}
    out = []
    for r in rows:
        cell, (p0, p1), depth = tuple(r["cell"]), r["window"], r["depth"]
        rec = {"cell": cell, "window": [p0, p1], "depth": depth, "touched": r["touched_parts"]}
        if (1, *cell) in live or (4, *cell) in live:
            rec["why"] = "a live mod folder overrides the cell"
            out.append(rec)
            continue
        cols = {}
        for d in (1, 4):
            w = CM.CliffWindow(cell, tuple(p0), tuple(p1), disc=d, game=RB.A.GAME)
            b, c, n, dm = column(w, depth)
            bear, card, off = cardinal(n)
            ok, prof = inland_ok(d, c, n)
            cols[d] = {"base": b, "crease": c, "nhat": n, "d_mid": round(dm, 3), "bearing": round(bear, 1),
                       "cardinal": card, "off_cardinal": round(off, 1), "inland_ok": ok, "inland": prof[-3:]}
        rec["discs"] = cols
        rec["crease_gap"] = round(math.dist((cols[1]["crease"][0], cols[1]["crease"][2]),
                                            (cols[4]["crease"][0], cols[4]["crease"][2])), 3)
        why = []
        if cols[1]["cardinal"] != cols[4]["cardinal"]:
            why.append("the discs face different bearings")
        for d in (1, 4):
            if cols[d]["off_cardinal"] > 12.0:
                why.append(f"disc {d} faces {cols[d]['bearing']} deg")
            if not cols[d]["inland_ok"]:
                why.append(f"disc {d} inland not walkable Terrain")
        rec["why"] = "; ".join(why) or None
        out.append(rec)
        print(f"{cell} d{depth} gap {rec['crease_gap']:.2f} bear {cols[1]['bearing']}/{cols[4]['bearing']} "
              f"-> {rec['why'] or 'USABLE'}")
    usable = sorted((r for r in out if r.get("why") is None),
                    key=lambda r: (-min(r["crease_gap"], 3.0), -r["discs"][1]["d_mid"]))
    res = {"tested": len(rows), "usable": len(usable), "ranked": usable[:15], "all": out}
    dst = HERE / "out" / "r9_site_scan.json"
    dst.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(f"{len(usable)} usable of {len(rows)} -> {dst}")
    for r in usable[:15]:
        c1, c4 = r["discs"][1], r["discs"][4]
        print(f"  {tuple(r['cell'])} gap {r['crease_gap']:.2f}  d_mid {c1['d_mid']}/{c4['d_mid']}  bearing "
              f"{c1['cardinal']:.0f} ({c1['off_cardinal']}/{c4['off_cardinal']} off)  crease y "
              f"{c1['crease'][1]:.2f}/{c4['crease'][1]:.2f}")


if __name__ == "__main__":
    main()
