"""Final ranking for THE NEW CONTINENT: apply island.verify_landmass's REAL shape gate
(8.0 <= med_turn <= 35.0, acute <= 0.12, max_turn < 150) + the seam/edge margins on top of the
free-map footprint test. Read-only."""
import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "studies", "overworld-topography"))
import continent_site_scan as C
from ff9mapkit.world import mesh as M

MARGIN = 12.0   # keep land this far off the z=0 / z=-1280 world edges and the x=0/1536 seam


def shape_of(cx, cz, R, lobes, seed):
    radii, _, _ = C.PROF[(lobes, seed)]
    n = len(radii)
    pts = [(cx + R * radii[i] * math.cos(2 * math.pi * i / n),
            cz + R * radii[i] * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return pts, M.outline_shape_stats(pts)


rows = []
for R in (96.0, 108.0, 120.0, 132.0, 144.0):
    for lobes in (2, 3):
        for (cx, cz, clr, near) in C.CENTRES:
            for s in range(C.NSEED):
                radii, rmx, rmn = C.PROF[(lobes, s)]
                rmax = R * rmx
                if cx - rmax < MARGIN or cx + rmax > 1536.0 - MARGIN:
                    continue
                if cz + rmax > -MARGIN or cz - rmax < -1280.0 + MARGIN:
                    continue
                h = C.evaluate(cx, cz, clr, near, R, lobes, s)
                if not h:
                    continue
                pts, st = shape_of(cx, cz, R, lobes, s)
                ok = (8.0 <= st["med_turn"] <= 35.0 and st["acute"] <= 0.12 and st["max_turn"] < 150.0)
                if not ok:
                    continue
                h["shape"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in st.items()}
                h["shape_margin"] = round(st["med_turn"] - 8.0, 2)
                h["span_x"] = round(max(p[0] for p in pts) - min(p[0] for p in pts), 1)
                h["span_z"] = round(max(p[1] for p in pts) - min(p[1] for p in pts), 1)
                h["elong"] = round(rmx / rmn, 2)
                rows.append(h)

rows.sort(key=lambda h: -h["area_u2"])
print(f"{len(rows)} candidates pass footprint + shape gate + edge margins\n")
hdr = "  area   blk  R  lob seed   centre           span        rmin/rmax  elong medturn corner acute"
print(hdr)
for h in rows[:25]:
    print(f"{h['area_u2']:7d} {h['n_blocks']:4d} {int(h['radius']):4d} {h['lobes']:3d} {h['seed']:4d} "
          f"({h['center'][0]:6.0f},{h['center'][1]:7.0f}) {h['span_x']:6.1f}x{h['span_z']:<6.1f} "
          f"{h['rmin_u']:5.1f}/{h['rmax_u']:<6.1f} {h['elong']:5.2f} {h['shape']['med_turn']:6.2f} "
          f"{h['shape']['corner']:6.3f} {h['shape']['acute']:6.3f}")

out = os.path.join(C.OUT, "continent_ranked.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"n": len(rows), "top": rows[:40]}, f, indent=1)
print("\nwrote", out)
if rows:
    b = rows[0]
    print("\nTOP block list:", b["blocks"])
