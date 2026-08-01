"""Post-census analysis for walk_sim: the class map, the pin dig, the corrected gate.
Classes per stacked-walkable point:
  LAWN-UNDER (defect): a walkable sheet BELOW the top one AND the scan (buffer order)
    or any approach grounds on it -> the actor walks under the carried surface.
  DEAD-UNDER (benign-ish): the top sheet wins the scan; the lower sheet is shadowed
    (still an invariant violation; armed only via ring history).
Renders a PNG map + prints the pin's sheet stack with buffer positions and the kept
lawn tri's geometry (why did the shingle cut keep it?).
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402

OUT = HERE / "out" / "walk_sim"


def main():
    world = W.load_world()
    x0, x1, z0, z1 = W.REGION
    nx = int((x1 - x0) / W.GRID) + 1
    nz = int((z1 - z0) / W.GRID) + 1

    img = Image.new("RGB", (nx, nz), (20, 20, 28))
    px = img.load()
    stacked_pts = []
    for i in range(nx):
        x = x0 + i * W.GRID
        for j in range(nz):
            z = z0 + j * W.GRID
            sh = W.all_sheets(world, x, z)
            jj = nz - 1 - j
            if not sh:
                continue
            walk = [s for s in sh if s[1] in W.WALK_OK]
            if not walk:
                px[i, jj] = (45, 45, 90)                    # blocked-only (sea/rock)
                continue
            if len(walk) < 2:
                px[i, jj] = (40, 70, 40)                    # clean single-sheet
                continue
            ys = sorted(s[0] for s in walk)
            gap = ys[-1] - ys[0]
            first_walk = walk[0]
            first_is_top = abs(first_walk[0] - ys[-1]) <= W.DEDUP_EPS
            cls = "DEAD-UNDER" if first_is_top else "LAWN-UNDER"
            stacked_pts.append(dict(x=x, z=z, gap=round(gap, 3), cls=cls,
                                    armed=gap > W.OFFSET))
            if cls == "LAWN-UNDER":
                px[i, jj] = (230, 60, 60) if gap > W.OFFSET else (235, 160, 60)
            else:
                px[i, jj] = (90, 120, 220) if gap > W.OFFSET else (110, 190, 220)

    # overlay: SUNKEN events (white) + the pin (magenta cross)
    rep = json.load(open(OUT / "report.json"))
    for e in rep["events_live"]:
        if e["ev"] != "SUNKEN":
            continue
        i = int(round((e["x"] - x0) / W.GRID))
        jj = nz - 1 - int(round((e["z"] - z0) / W.GRID))
        if 0 <= i < nx and 0 <= jj < nz:
            px[i, jj] = (255, 255, 255)
    pi = int(round((W.PIN[0] - x0) / W.GRID))
    pj = nz - 1 - int(round((W.PIN[1] - z0) / W.GRID))
    for k in range(-6, 7):
        for (a, b) in ((pi + k, pj), (pi, pj + k)):
            if 0 <= a < nx and 0 <= b < nz:
                px[a, b] = (255, 0, 255)
    img = img.resize((nx * 2, nz * 2), Image.NEAREST)
    img.save(OUT / "class_map.png")

    lawn_under = [p for p in stacked_pts if p["cls"] == "LAWN-UNDER"]
    dead_under = [p for p in stacked_pts if p["cls"] == "DEAD-UNDER"]
    print(f"stacked {len(stacked_pts)}: LAWN-UNDER {len(lawn_under)} "
          f"(armed {sum(1 for p in lawn_under if p['armed'])}), "
          f"DEAD-UNDER {len(dead_under)} (armed {sum(1 for p in dead_under if p['armed'])})")
    dmin = min(math.hypot(p["x"] - W.PIN[0], p["z"] - W.PIN[1]) for p in stacked_pts)
    dmin_lu = min((math.hypot(p["x"] - W.PIN[0], p["z"] - W.PIN[1]) for p in lawn_under),
                  default=float("inf"))
    print(f"min stacked-point distance to pin: {dmin:.2f}  (LAWN-UNDER: {dmin_lu:.2f})  "
          f"-> corrected g2: {'PASS' if dmin_lu <= W.PIN_R else 'FAIL'}")

    # ---- the pin dig
    print(f"\n--- sheets at the pin {W.PIN} (scan order) ---")
    sh = W.all_sheets(world, *W.PIN)
    bk = W.block_key(*W.PIN)
    for (y, topo, mi, ti) in sh:
        mesh = world[bk][mi]
        tri = mesh["tris"][ti]
        span = max(tri[6][1] - tri[6][0], tri[6][3] - tri[6][2])
        print(f"   y={y:6.2f} topo={topo:3d} mesh={mesh['name']:8s} tri#{ti:5d}/{len(mesh['tris'])} "
              f"ny={tri[5]:+.2f} plan-span={span:5.1f}u "
              f"verts={[tuple(round(v, 1) for v in p) for p in (tri[0], tri[1], tri[2])]}")

    # LAWN-UNDER connected extent around the pin (how deep does the kept lawn run?)
    near = [p for p in lawn_under
            if math.hypot(p["x"] - W.PIN[0], p["z"] - W.PIN[1]) <= 20.0]
    if near:
        xs = [p["x"] for p in near]; zs = [p["z"] for p in near]
        print(f"\nLAWN-UNDER within 20u of pin: {len(near)} pts, "
              f"bbox x[{min(xs)},{max(xs)}] z[{min(zs)},{max(zs)}], "
              f"max gap {max(p['gap'] for p in near)}")
    json.dump(dict(lawn_under=len(lawn_under), dead_under=len(dead_under),
                   pin_min_lawn_under=dmin_lu), open(OUT / "class_map.json", "w"))
    print(f"\nmap: {OUT / 'class_map.png'}")


if __name__ == "__main__":
    main()
