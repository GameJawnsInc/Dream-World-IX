"""Texture seams in the rot-mountain lab: grass tris whose texture spans more than one tile window.

The crack audit (rot_cracks.py, calibrated) finds no open edge or T-junction in any of the four meshes, so a
hairline seam in the grass is a TEXTURE line: a ground tri whose three UVs do not come from one (cell, quad, ori)
window of the mains tiling samples across the tile's edge into its neighbour in the atlas (THE ONE-WINDOW-PER-TRI
LAW, texgates.one_window_gate). The gate needs the per-cell window field the mint used, so it is decoded here from
the bare island's own grass (each cell's tris' UVs against every (quad, ori)), then every variant's grass is
judged against it. Prints each multi-window tri: where it is (zip annulus by the rock / apron / mint grass), and
whether the bare island already had it.
Rerun: py studies/terrain-malleability/rockstretch/rot_texseams.py
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rot_prep as P  # noqa: E402
from ff9mapkit.world import mesh as M, grassland as G, texgates as TG  # noqa: E402

QUADS = [(u, v) for u in (0, 1) for v in (0, 1)]


def cells_of(lab):
    return {(bx, by): [("Terrain", M.blockmesh_from_ff9mesh(P.LAB / lab / "FF9CustomMap-lab" / M.override_relpath(1, bx, by),
                                                            disc=1, x=bx, y=by, part="terrain"))] for bx, by in P.BLOCKS}


def decode_field(recs):
    by_cell = defaultdict(list)
    for r in TG.mains_records(recs):
        by_cell[r["cell"]].append(r)
    field = {}
    for cell, rs in by_cell.items():
        votes = defaultdict(int)
        for r in rs:
            for q in QUADS:
                for o in G.ORIS:
                    pred = [G.ground_uv(p[0], p[2], cell, q, o, r["fam"]) for p in r["world_pts"]]
                    if all(abs(pred[k][0] - r["uv"][k][0]) < TG.ONE_WINDOW_UV_TOL and
                           abs(pred[k][1] - r["uv"][k][1]) < TG.ONE_WINDOW_UV_TOL for k in range(3)):
                        votes[(q, o)] += 1
        if votes:
            field[cell] = max(votes, key=votes.get)
    return field


def main():
    island = TG.terrain_records(cells_of("island"), P.BLOCKS)
    field = decode_field(island)
    print(f"decoded {len(field)} cells of the island's mains field")
    base = None
    for lab in ("island", "A", "B", "C"):
        cm = cells_of(lab)
        recs = TG.terrain_records(cm, P.BLOCKS)
        gate = TG.one_window_gate(cm, P.BLOCKS, quad_ori=field, records=recs)
        # list the bad tris (re-run the gate's own predicate to get them, not just the count)
        bad = []
        for r in TG.mains_records(recs):
            if r["cell"] not in field:
                continue
            cands = [r["cell"]] + [(math.floor(p[0] / 4.0), math.floor(p[2] / 4.0)) for p in r["world_pts"]]
            if not any(c in field and all(
                    abs(G.ground_uv(p[0], p[2], c, *field[c], r["fam"])[k2] - r["uv"][k][k2]) < TG.ONE_WINDOW_UV_TOL
                    for k, p in enumerate(r["world_pts"]) for k2 in (0, 1)) for c in cands):
                bad.append(r)
        keys = {tuple(round(c, 2) for p in r["world_pts"] for c in p) for r in bad}
        if lab == "island":
            base = keys
        new = [r for r in bad if tuple(round(c, 2) for p in r["world_pts"] for c in p) not in base]
        T, topo = (P.load(lab) if lab != "island" else (None, None))
        rock = None if T is None else T[topo == P.ROCK].reshape(-1, 3)

        def to_rock(r):
            if rock is None:
                return None
            cx = sum(p[0] for p in r["world_pts"]) / 3
            cz = sum(p[2] for p in r["world_pts"]) / 3
            return round(min(math.hypot(cx - p[0], cz - p[2]) for p in rock), 2)
        print(f"== {lab}: judged {gate['checked']}, multi-window {gate['n_multi_window']} "
              f"(out of field {gate.get('out_of_field')}), new vs the bare island {len(new)}")
        for r in (new if lab != "island" else bad)[:14]:
            print(f"   {r['block']} cell {r['cell']} {r['fam']} centroid "
                  f"({sum(p[0] for p in r['world_pts']) / 3:.1f}, {sum(p[2] for p in r['world_pts']) / 3:.1f})"
                  + (f"  {to_rock(r)}u from rock" if rock is not None else ""))


if __name__ == "__main__":
    main()
