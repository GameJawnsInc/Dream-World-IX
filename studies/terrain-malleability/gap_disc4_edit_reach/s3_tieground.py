"""STEP 3 -- strategy (i), the ORDER-INVARIANT gate: is the tie-ground difference of a permuted cell acceptable?

A cell that is an exact all-channel PERMUTATION across discs (s1: 10 land cells) differs only in triangle buffer
order. Within one mesh the engine grounds on the FIRST passing triangle in buffer order (WMPhysics.Raycast,
first-hit; placement.place rule 4), so where two up-facing triangles both pass at one (x, z) the order picks the
IDALL. Mirroring a disc-1 edit byte-for-byte onto such a cell replaces disc-4's order with disc-1's.

Instrument: placement.place (engine-faithful: registration order, buffer-order first hit, IDALL 4078/4088/2040
skip, 0x31EE mesh veto, geometric-winding ny>0.1 filter) on each cell's Form-1 walk parts, disc 1 vs disc 4.
  (a) the disc4 lane's 0.5u cell-centre lattice (16,384 samples) -> must REPRODUCE D4-18's per-block counts
      ((7,3) 24, (21,13) 16, (22,11) 8, (22,13) 8 idall/topo samples, dy 0) -- calibration;
  (b) for every differing sample: the hit triangle's minimum barycentric weight on each disc (an edge tie has a
      weight ~0) and the count of passing sheets (all_sheets, non-strict) -- a tie vs a genuine overlap;
  (c) 16,384 JITTERED samples per block (uniform random, fixed seed) -- a tie set has measure zero, so a
      difference that survives jitter is a genuine overlap, not a tie;
  (d) control: a cell with REAL disc-4 edits ((9,17), (19,14)) must show differences under jitter too, so (c)
      can fail.
Writes out/s3_tieground.json.
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s3_tieground.py
"""
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402

s1 = json.loads((L.OUT / "s1_gate.json").read_text(encoding="utf-8"))
perm_cells = [tuple(c) for c in s1["orderinv_flips_land"]]
controls = [(9, 17), (19, 14)]
objs = L.mesh_objects()
P = L.P


def hit_weight(ml, x, z, name, idall):
    """min barycentric weight of the first passing tri in mesh `name` (re-scan, same filters as place())."""
    for nm, bm in ml:
        if nm != name:
            continue
        V, T, fi = bm.verts, bm.tangents, bm.flat_index
        for t in range(len(fi) // 3):
            idx = fi[3 * t:3 * t + 3]
            ida = int(round(T[idx[0]][0]))
            if ida in P.IDALL_SKIP:
                continue
            a, b, c = V[idx[0]], V[idx[1]], V[idx[2]]
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            ny = uz * vx - ux * vz
            Ln = math.sqrt((uy * vz - uz * vy) ** 2 + ny * ny + (ux * vy - uy * vx) ** 2) or 1.0
            if ny / Ln <= 0.1:
                continue
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            w0 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
            w1 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
            w2 = 1 - w0 - w1
            if min(w0, w1, w2) < -1e-9:
                continue
            return min(w0, w1, w2)
    return None


def run(cell, jitter_n=16384):
    ml = {d: L.walk_meshlist(L.blockmeshes(d, cell[0], cell[1], objs)) for d in (1, 4)}
    ix = {d: [P.build_index(bm) for _, bm in ml[d]] for d in (1, 4)}
    lat = {"samples": 0, "dy": 0, "dy_exact": 0, "idall": 0, "topo": 0, "max_minw": 0.0, "sheets_max": 0}
    for i in range(128):
        for j in range(128):
            x, z = (i + 0.5) * 0.5, -(j + 0.5) * 0.5
            g1 = P.place(ml[1], x, z, 0.0, sky=True, index=ix[1])
            g4 = P.place(ml[4], x, z, 0.0, sky=True, index=ix[4])
            lat["samples"] += 1
            if abs(g1[0] - g4[0]) > 1e-4:          # D4-18's own threshold (reorder_check.py:64)
                lat["dy"] += 1
            if g1[0] != g4[0]:                      # exact: float noise of a shared-edge tie shows here
                lat["dy_exact"] += 1
            if g1[2] != g4[2]:
                lat["idall"] += 1
                w1 = hit_weight(ml[1], x, z, g1[1], g1[2])
                w4 = hit_weight(ml[4], x, z, g4[1], g4[2])
                lat["max_minw"] = max(lat["max_minw"], abs(w1 or 0), abs(w4 or 0))
                ns = len(P.all_sheets(ml[1], x, z, strict=False, index=ix[1]))
                lat["sheets_max"] = max(lat["sheets_max"], ns)
            if g1[3] != g4[3]:
                lat["topo"] += 1
    rng = random.Random(1000 * cell[0] + cell[1])
    jit = {"samples": jitter_n, "dy": 0, "idall": 0, "topo": 0}
    for _ in range(jitter_n):
        x, z = rng.uniform(0, 64), -rng.uniform(0, 64)
        g1 = P.place(ml[1], x, z, 0.0, sky=True, index=ix[1])
        g4 = P.place(ml[4], x, z, 0.0, sky=True, index=ix[4])
        jit["dy"] += abs(g1[0] - g4[0]) > 1e-4
        jit["idall"] += g1[2] != g4[2]
        jit["topo"] += g1[3] != g4[3]
    return {"lattice": lat, "jitter": jit}


d4 = {tuple(r["block"]): r for r in json.loads((L.D4OUT / "reorder_check.json").read_text(encoding="utf-8"))["ground"]}
res = {}
for c in perm_cells + controls:
    r = run(c)
    res[f"{c[0]},{c[1]}"] = r
    ref = d4.get(c)
    print(c, "lattice", r["lattice"], "| jitter", r["jitter"], "| D4-18 ref", {k: ref[k] for k in ("dy", "topo", "idall")} if ref else None)
    if ref and c in perm_cells:
        assert (r["lattice"]["dy"], r["lattice"]["topo"], r["lattice"]["idall"]) == (ref["dy"], ref["topo"], ref["idall"]), \
            f"calibration: must reproduce D4-18 at {c}"
for c in controls:
    assert res[f"{c[0]},{c[1]}"]["jitter"]["idall"] > 0, "control must differ under jitter (instrument can fail)"
tot_lat = sum(v["lattice"]["idall"] for k, v in res.items() if tuple(map(int, k.split(","))) in perm_cells)
tot_jit = sum(v["jitter"]["idall"] for k, v in res.items() if tuple(map(int, k.split(","))) in perm_cells)
print(f"permutation cells: lattice idall diffs {tot_lat} / {16384 * len(perm_cells)}; jittered {tot_jit} / {16384 * len(perm_cells)}")
(L.OUT / "s3_tieground.json").write_text(json.dumps({"perm_cells": [list(c) for c in perm_cells], "controls": [list(c) for c in controls],
                                                      "rows": res, "lattice_total": tot_lat, "jitter_total": tot_jit}, indent=1), encoding="utf-8")
