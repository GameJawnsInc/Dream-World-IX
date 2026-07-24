"""RUNG F attempt 2 -- the SHAPED (ecotone + S-wall) keep-footprint PERIMETER test (read-only).

Attempt-1 falsified the RECTANGULAR 4x4 window (its E outer edge is a 37u cliff). Attempt-2's idea:
cut a SHAPED region = ecotone + the south-wall band, dropping the N/E/W massif, so the strip's own
foot welds to minted grass. For that to weld lawfully, the SHAPED footprint's FULL outer perimeter
must be lowland-weldable (land <8u or ocean) -- a rock-cliff (>=8u) anywhere on the perimeter is an
exposed cut massif face (off-language, the attempt-1 failure mode).

This measures the ecotone+S-band keep footprint's perimeter: for each of the 4 sides, the fraction of
boundary cells that are rock-cliff (>=8u) vs lowland/ocean. If any side is cliff-dominated, the shaped
carry cannot weld there => the S-wall-inclusive carry is FALSIFIED at this site and attempt-2 stages
option (c) alone.

Run: cd studies/overworld-topography && py rung_f_swall_perim.py
Writes ONLY out/rung_f/swall_perim.json + this script.
"""
from __future__ import annotations
import json, math, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                     # noqa: E402
from ff9mapkit.world import extract as X          # noqa: E402

CELL = 4.0
OUT = HERE / "out" / "rung_f" / "swall_perim.json"
MASS_TOPOS = frozenset({16, 17, 19, 20, 41})
ROCK_TOPOS = frozenset(t for t, f in SNR.FAM_OF.items() if f == "rock") | {49}
HIGH_U = 8.0
CONTEXT_X = range(9, 19)
CONTEXT_Z = range(8, 16)

# the shaped keep footprint from swall_map: ecotone bbox x[216,248] z[-192,-181] + S-band z down to -161
KEEP_X = (216, 248)
KEEP_Z = (-192, -161)          # ecotone north edge (-192) to S-band foot line (-161)


def dominant(c): return c.most_common(1)[0][0] if c else None


def main():
    cells = {}
    for (bx, by) in [(x, y) for x in CONTEXT_X for y in CONTEXT_Z]:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except Exception:
            continue
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            cx = sum(bm.verts[j][0] + ox for j in tri) / 3.0
            cz = sum(bm.verts[j][2] + oz for j in tri) / 3.0
            y = sum(bm.verts[j][1] for j in tri) / 3.0
            c = (math.floor(cx / CELL), math.floor(cz / CELL))
            d = cells.setdefault(c, dict(topo=Counter(), ys=[]))
            d["topo"][topo] += 1; d["ys"].append(y)

    def classify(c):
        d = cells.get(c)
        if d is None:
            return ("ocean", None)
        ys = sorted(d["ys"]); p50 = ys[len(ys) // 2]
        topo = dominant(d["topo"])
        is_rock = topo in ROCK_TOPOS
        if is_rock and p50 >= HIGH_U:
            return ("rock_cliff", round(p50, 1))
        return ("lowland", round(p50, 1))     # low land OR low rock foot = weldable

    x0, x1 = KEEP_X; z0, z1 = KEEP_Z
    sides = {"N": [(x, z0) for x in range(x0, x1 + 1)],
             "S": [(x, z1) for x in range(x0, x1 + 1)],
             "W": [(x0, z) for z in range(z0, z1 + 1)],
             "E": [(x1, z) for z in range(z0, z1 + 1)]}
    # the outer RING one cell beyond the footprint (what the minted coast/grass would weld against)
    outer = {"N": [(x, z0 - 1) for x in range(x0, x1 + 1)],
             "S": [(x, z1 + 1) for x in range(x0, x1 + 1)],
             "W": [(x0 - 1, z) for z in range(z0, z1 + 1)],
             "E": [(x1 + 1, z) for z in range(z0, z1 + 1)]}

    result = {"keep_footprint_cell": {"x": list(KEEP_X), "z": list(KEEP_Z),
              "span_u": [(x1 - x0 + 1) * CELL, (z1 - z0 + 1) * CELL]}, "sides": {}}
    print("=" * 88)
    print("RUNG F attempt 2 -- SHAPED (ecotone+S-band) keep-footprint PERIMETER weldability")
    print(f"keep footprint cells x[{x0},{x1}] z[{z0},{z1}]  span "
          f"{(x1-x0+1)*CELL:.0f}x{(z1-z0+1)*CELL:.0f}u")
    print("=" * 88)
    any_cliff_side = []
    for side in ("N", "S", "E", "W"):
        edge = [classify(c) for c in sides[side]]
        ring = [classify(c) for c in outer[side]]
        # weldability judged on the OUTER ring (what a minted coast abuts) AND the edge itself
        edge_cliff = sum(1 for k, _ in edge if k == "rock_cliff")
        ring_cliff = sum(1 for k, _ in ring if k == "rock_cliff")
        n = len(edge)
        edge_heights = [h for _, h in edge if h is not None]
        rec = dict(n_cells=n,
                   edge_cliff_frac=round(edge_cliff / n, 2),
                   ring_cliff_frac=round(ring_cliff / n, 2),
                   edge_h_p50=round(sorted(edge_heights)[len(edge_heights)//2], 1) if edge_heights else None,
                   edge_h_max=round(max(edge_heights), 1) if edge_heights else None,
                   weldable=(ring_cliff / n <= 0.15 and edge_cliff / n <= 0.30))
        result["sides"][side] = rec
        if not rec["weldable"]:
            any_cliff_side.append(side)
        print(f"  {side}: edge_cliff={rec['edge_cliff_frac']*100:.0f}% ring_cliff={rec['ring_cliff_frac']*100:.0f}%  "
              f"edge_h p50={rec['edge_h_p50']} max={rec['edge_h_max']}  weldable={rec['weldable']}")

    carriable = len(any_cliff_side) == 0
    result["cliff_sides"] = any_cliff_side
    result["shaped_carry_weldable"] = carriable
    verdict = ("The shaped ecotone+S-wall footprint welds lawfully on ALL sides -> attempt-2 CAN carry it."
               if carriable else
               f"The shaped footprint exposes a ROCK-CLIFF face on side(s) {any_cliff_side} (the "
               "continuous massif flank). A minted coast/grass cannot weld to a >=8u cut rock face "
               "(off-language, the attempt-1 failure mode, now on the W/other flank). The ecotone is "
               "PINNED against the continuous massif -- there is no shaped (ecotone+south-wall) cut "
               "whose full perimeter is lowland. => the S-wall-inclusive carry is FALSIFIED at this "
               "site; attempt-2 stages OPTION (c) ALONE, the FRESH EYE judges it against the measured "
               "partial-pocket stock context.")
    result["verdict"] = verdict
    print("-" * 88); print(verdict)
    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}")
    return result


if __name__ == "__main__":
    main()
