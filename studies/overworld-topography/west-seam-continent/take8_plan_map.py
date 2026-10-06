"""A top-down map of take 8's SW window: who authored each triangle, and which atlas tile it wears.

Read-only. Draws every tri in the ROI from above (north up, east right), filled by class:
  carried rock (donor geometry)   grey      minted rock (take 8's zip/foot/contact)   red
  carried grass                   dark green minted grass (zip emitted as grass)      bright green
  lawn (minted ground, flat)      pale green
with the tile code on the low course (ymin < lawn + 3) and the harness stations marked. Writes
take8_plan_map.png into the take-8 harness run dir (+ a second panel: height, dark = low).

    py studies/overworld-topography/west-seam-continent/take8_plan_map.py
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from take8_defect_census import LAWN, ROI, geom, load, tile      # noqa: E402
from profile_base_measure import classify, donor_data, fit_transform, uvkey   # noqa: E402

S = 16                                         # pixels per world unit
W, H = int((ROI[2] - ROI[0]) * S), int((ROI[3] - ROI[1]) * S)


def px(x, z):
    return ((x - ROI[0]) * S, (ROI[3] - z) * S)     # north (+z) up


def main():
    dn_tris, dn_keys = donor_data()
    rows = load()
    st = [(r["w"][0], r["w"][1], r["w"][2], r["topo"]) for r in rows]
    sk = [uvkey(r["uv"]) for r in rows]
    xf = fit_transform(st, sk, dn_tris, dn_keys)
    carried = classify(st, sk, dn_keys, dn_tris, xf)
    cls_img = Image.new("RGB", (W, H), (20, 20, 40))
    h_img = Image.new("RGB", (W, H), (20, 20, 40))
    dc, dh = ImageDraw.Draw(cls_img), ImageDraw.Draw(h_img)
    labels = []
    for r, c in zip(rows, carried):
        g = geom(r["w"])
        x, _, z = g["c"]
        if not (ROI[0] - 8 <= x <= ROI[2] + 8 and ROI[1] - 8 <= z <= ROI[3] + 8):
            continue
        poly = [px(p[0], p[2]) for p in r["w"]]
        rock = r["topo"] == 49
        flat = g["ymax"] - g["ymin"] < 0.3 and abs(g["ymax"] - LAWN) < 0.3
        if rock:
            col = (150, 150, 150) if c else (220, 60, 60)
        elif r["topo"] == 0:
            col = (60, 110, 40) if c else ((170, 210, 140) if flat else (60, 230, 60))
        else:
            col = (60, 60, 200)
        dc.polygon(poly, fill=col, outline=(0, 0, 0))
        v = max(0, min(255, int((g["ymax"] - 1.0) / 30.0 * 255)))
        dh.polygon(poly, fill=(v, v, v), outline=(40, 40, 40))
        if rock and g["ymin"] < LAWN + 3.0 and ROI[0] <= x <= ROI[2] and ROI[1] <= z <= ROI[3]:
            tr, tc = tile(r["uv"])
            labels.append((px(x, z), f"{tr}.{tc}"))
    for (lx, ly), t in labels:
        dc.text((lx - 8, ly - 5), t, fill=(255, 255, 0))
    plan = json.loads((HERE / "rimwalk_stations.json").read_text(encoding="utf-8"))
    for i, s in enumerate(plan["stations"]):
        if s["approach"] is None:
            continue
        cx, cz = s["contact"]
        for img in (cls_img, h_img):
            d = ImageDraw.Draw(img)
            x0, y0 = px(cx, cz)
            d.ellipse((x0 - 5, y0 - 5, x0 + 5, y0 + 5), outline=(0, 255, 255), width=2)
    # 4u grid
    for img in (cls_img, h_img):
        d = ImageDraw.Draw(img)
        for gx in range(int(ROI[0]), int(ROI[2]) + 1, 4):
            d.line([px(gx, ROI[1]), px(gx, ROI[3])], fill=(60, 60, 90) if gx % 16 else (120, 120, 160))
            if gx % 8 == 0:
                d.text(px(gx, ROI[3]), str(gx), fill=(200, 200, 255))
        for gz in range(int(ROI[1]), int(ROI[3]) + 1, 4):
            d.line([px(ROI[0], gz), px(ROI[2], gz)], fill=(60, 60, 90) if gz % 16 else (120, 120, 160))
            if gz % 8 == 0:
                d.text(px(ROI[0], gz), str(gz), fill=(200, 200, 255))
    out = Image.new("RGB", (W * 2 + 10, H), (0, 0, 0))
    out.paste(cls_img, (0, 0))
    out.paste(h_img, (W + 10, 0))
    dest = HERE.parents[2] / ".harness-runs" / "20261006-105632-rimwalk-take8" / "take8_plan_map.png"
    dest.parent.mkdir(parents=True, exist_ok=True)       # gitignored, beside the frames it explains
    out.save(dest)
    print(f"wrote take8_plan_map.png {out.size}")


if __name__ == "__main__":
    main()
