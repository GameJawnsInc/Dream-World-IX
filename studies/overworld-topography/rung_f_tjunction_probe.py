"""ROUND-3 DIRECTIVE step 1 (corollary): MEASURE the cross-border T-junction potential at each
candidate shift -- never assume. finding_3 (rung_f_build.json round3_diagnosis) blamed the 148 border
T-junctions on round-1's -800u (=-12.5 block, HALF-BLOCK phase) x-shift: a target block border cutting
through a donor tri at a non-vertex point leaves a T-junction. A WHOLE-BLOCK x-shift maps donor
x-borders onto target x-borders (verts land ON the border -> crossing at a vertex -> no T-junction),
so only the z-borders (phase-shifted) generate them.

This counts, on the VERBATIM-CORE kept tris (the DROP set = interwoven mountain/rock/forest/water),
how many tri-edges cross a target x-border and a target z-border STRICTLY interior to the edge (a
potential T-junction site the stitch must weld) at each candidate shift. Directly quantifies the
whole-block-x benefit.

READ-ONLY. Writes out/rung_f/tjunction_probe.json.
"""
import sys, io, contextlib, math, json
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, '../../ff9mapkit'); sys.path.insert(0, '.')
import contract_mass_gates as G

HERE = Path(__file__).resolve().parent
CELL = 4.0; BLOCK = 64.0
DROP = {49, 50, 58, 7, 62, 45, 46, 36, 37, 27, 28, 48, 51, 10, 59}
TOL = 1e-4

def kept_core_tris():
    core = [(x, y) for x in (13, 14, 15) for y in (11, 12)]
    with contextlib.redirect_stdout(io.StringIO()):
        cand = G.load_candidate('stock', None, core_blocks=core)
    return [t for t in cand['core_tris'] if t['topo'] not in DROP]

def border_crossings(tris, shift_wx, shift_wz):
    """count tri-edges crossing a target block border (world coord == 0 mod 64) strictly interior."""
    nx = nz = 0
    seen_x = set(); seen_z = set()
    for t in tris:
        w = [(p[0] + shift_wx, p[2] + shift_wz) for p in t['w']]   # (x,z) after shift
        for i in range(3):
            (x1, z1) = w[i]; (x2, z2) = w[(i + 1) % 3]
            ekey = tuple(sorted([(round(x1, 2), round(z1, 2)), (round(x2, 2), round(z2, 2))]))
            # x-borders between x1 and x2
            lo, hi = sorted([x1, x2])
            k0 = math.ceil(lo / BLOCK); k1 = math.floor(hi / BLOCK)
            for k in range(k0, k1 + 1):
                b = k * BLOCK
                if lo + TOL < b < hi - TOL:            # strictly interior
                    # endpoint on border? then it's a vertex crossing, not a T-junction
                    if abs(x1 - b) < TOL or abs(x2 - b) < TOL:
                        continue
                    if ekey not in seen_x:
                        seen_x.add(ekey); nx += 1
            lo, hi = sorted([z1, z2])
            k0 = math.ceil(lo / BLOCK); k1 = math.floor(hi / BLOCK)
            for k in range(k0, k1 + 1):
                b = k * BLOCK
                if lo + TOL < b < hi - TOL:
                    if abs(z1 - b) < TOL or abs(z2 - b) < TOL:
                        continue
                    if ekey not in seen_z:
                        seen_z.add(ekey); nz += 1
    return nx, nz

def main():
    tris = kept_core_tris()
    MECX, MECZ = 935.8, -767.3
    cands = {
        "round1_halfblock_x (SHIFT -800,-384)": (-800.0, -384.0),
        "round2_wholeblock (SHIFT -832,+576, WRAPS seam)": (-832.0, +576.0),
        "PRIMARY wholeblock-x SOUTH (167.8,-1127.3)": (167.8 - MECX, -1127.3 - MECZ),
        "ALT maxmargin SOUTH (155.8,-1119.3)": (155.8 - MECX, -1119.3 - MECZ),
        "ALT NORTH bay (151.8,-167.3)": (151.8 - MECX, -167.3 - MECZ),
    }
    out = {"n_kept_core_tris": len(tris), "note":
           "x_border_crossings + z_border_crossings = potential T-junction sites the stitch welds. "
           "whole-block-x shift -> x-crossings collapse to vertex crossings (0 interior). Measured, "
           "not assumed.", "shifts": {}}
    for name, (sx, sz) in cands.items():
        nx, nz = border_crossings(tris, sx, sz)
        out["shifts"][name] = dict(shift_world=[round(sx, 1), round(sz, 1)],
                                   shift_cells=[round(sx / CELL, 2), round(sz / CELL, 2)],
                                   x_whole_block=(abs(sx % BLOCK) < 0.5 or abs(sx % BLOCK - BLOCK) < 0.5),
                                   z_whole_block=(abs(sz % BLOCK) < 0.5 or abs(sz % BLOCK - BLOCK) < 0.5),
                                   x_border_crossings=nx, z_border_crossings=nz, total=nx + nz)
        print(f"{name:52} x={nx:4} z={nz:4} total={nx+nz:4}")
    (HERE / "out" / "rung_f" / "tjunction_probe.json").write_text(json.dumps(out, indent=1))
    print("wrote out/rung_f/tjunction_probe.json")

if __name__ == "__main__":
    main()
