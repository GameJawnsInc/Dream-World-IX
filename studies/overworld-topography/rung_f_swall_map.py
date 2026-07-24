"""RUNG F attempt 2 -- ASCII map of the donor region to nail the S-WALL keep-mask (read-only).

Dumps, in WORLD-CELL coords, an ASCII grid of the junction context so the keep-mask for the
S-wall true-mesh carry is chosen from measured bytes, not guessed. Each cell shows a glyph:
  ecotone (topo 16/17/19/20/41) = its family initial (d/D/n/etc), rock = R(height decile), grass = .
  low rock (<8u foot) = r, ocean = ' '. Also prints the ecotone bbox + candidate S-wall band cells
  (rock cells south-adjacent to the ecotone, walked to their lowland foot) and the window that would
  capture them.

Run: cd studies/overworld-topography && py rung_f_swall_map.py
Writes ONLY out/rung_f/swall_map.txt + this script.
"""
from __future__ import annotations
import math, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                     # noqa: E402
from ff9mapkit.world import extract as X          # noqa: E402

CELL = 4.0
BLOCK = 64.0
OUT = HERE / "out" / "rung_f" / "swall_map.txt"
MASS_TOPOS = frozenset({16, 17, 19, 20, 41})
ROCK_TOPOS = frozenset(t for t, f in SNR.FAM_OF.items() if f == "rock") | {49}
CONTEXT_X = range(10, 19)
CONTEXT_Z = range(8, 16)
JUNCTION_BLOCKS = [(bx, by) for bx in range(13, 16) for by in range(11, 13)]


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
            fam = SNR.FAM_OF.get(topo)
            if topo == 49:
                fam = "rock"
            cx = sum(bm.verts[j][0] + ox for j in tri) / 3.0
            cz = sum(bm.verts[j][2] + oz for j in tri) / 3.0
            y = sum(bm.verts[j][1] for j in tri) / 3.0
            c = (math.floor(cx / CELL), math.floor(cz / CELL))
            d = cells.setdefault(c, dict(topo=Counter(), fam=Counter(), ys=[]))
            d["topo"][topo] += 1; d["fam"][str(fam)] += 1; d["ys"].append(y)

    # ecotone bbox
    eco = set()
    for (bx, by) in JUNCTION_BLOCKS:
        ox, oz = X.block_world_origin(bx, by)
        cx0, cz0 = int(ox // CELL), int(oz // CELL)
        for dx in range(16):
            for dz in range(16):
                c = (cx0 + dx, cz0 + dz)
                d = cells.get(c)
                if d and dominant(d["topo"]) in MASS_TOPOS:
                    eco.add(c)
    exs = [c[0] for c in eco]; ezs = [c[1] for c in eco]
    exlo, exhi, ezlo, ezhi = min(exs), max(exs), min(ezs), max(ezs)

    def glyph(c):
        d = cells.get(c)
        if d is None:
            return " "
        topo = dominant(d["topo"])
        ys = sorted(d["ys"]); p50 = ys[len(ys) // 2]
        fam = dominant(d["fam"])
        if topo in MASS_TOPOS:
            return {16: "d", 17: "D", 41: "n", 19: "s", 20: "b"}.get(topo, "m")
        if topo in ROCK_TOPOS:
            return "R" if p50 >= 8 else "r"
        if fam == "grass":
            return "." if p50 < 8 else "^"   # ^ = highland grass/plateau
        return "?"

    # print map over a window a bit larger than the ecotone, both z directions
    zx0, zx1 = exlo - 20, exhi + 20
    zz0, zz1 = ezlo - 24, ezhi + 24
    lines = []
    lines.append(f"ecotone bbox_cell x[{exlo},{exhi}] z[{ezlo},{ezhi}]  "
                 f"world x[{exlo*4},{(exhi+1)*4}] z[{ezlo*4},{(ezhi+1)*4}]")
    lines.append(f"glyphs: d/D=desert16/17 n=dunes41 R=rock>=8u r=rock<8u .=grass ^=highland-grass ' '=ocean")
    lines.append(f"z increases DOWNWARD (south=larger z per swall_probe). ecotone rows marked '*'")
    lines.append("     " + "".join(str((x // 10) % 10) for x in range(zx0, zx1 + 1)))
    lines.append("     " + "".join(str(x % 10) for x in range(zx0, zx1 + 1)))
    for z in range(zz0, zz1 + 1):
        mark = "*" if ezlo <= z <= ezhi else " "
        row = "".join(glyph((x, z)) for x in range(zx0, zx1 + 1))
        lines.append(f"{z:5d}{mark}{row}")

    # candidate S-wall band: from each ecotone-south-edge column, walk south while rock, record extent
    log_band = []
    band_cells = set()
    for cx in range(exlo, exhi + 1):
        z = ezhi + 1
        started = False
        wallcells = []
        while z < ezhi + 30:
            d = cells.get((cx, z))
            if d is None:
                break
            topo = dominant(d["topo"]); ys = sorted(d["ys"]); p50 = ys[len(ys)//2]
            is_rock = topo in ROCK_TOPOS
            if is_rock:
                started = True; wallcells.append((cx, z, round(p50, 1)))
            elif started and p50 < 8:
                break  # reached the lowland foot
            z += 1
        if wallcells:
            for (a, b, h) in wallcells:
                band_cells.add((a, b))
            log_band.append((cx, wallcells[0][1], wallcells[-1][1], max(h for _,_,h in wallcells)))
    lines.append("")
    lines.append(f"S-wall band candidate: {len(band_cells)} rock cells south of the ecotone")
    if band_cells:
        bzs = [c[1] for c in band_cells]; bxs = [c[0] for c in band_cells]
        lines.append(f"  band bbox_cell x[{min(bxs)},{max(bxs)}] z[{min(bzs)},{max(bzs)}]  "
                     f"depth={ (max(bzs)-min(bzs)+1)*4 }u  world z[{min(bzs)*4},{(max(bzs)+1)*4}]")
        # combined keep footprint (ecotone + band) extent -> needed window
        kx = exs + bxs; kz = ezs + bzs
        lines.append(f"  ecotone+band keep footprint: x[{min(kx)},{max(kx)}] z[{min(kz)},{max(kz)}]  "
                     f"span {(max(kx)-min(kx)+1)*4}x{(max(kz)-min(kz)+1)*4}u")
        # block window needed
        bx0 = min(kx)*4 // BLOCK; bx1 = max(kx)*4 // BLOCK
        lines.append(f"  per-column wall extent (cx, z_start, z_end, peak_h): {log_band}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
