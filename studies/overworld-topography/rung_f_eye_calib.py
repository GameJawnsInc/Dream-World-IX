"""RUNG F EYE -- CALIBRATION panels (READ-ONLY vs the install).

Render pure-stock reference panels with the EXACT same projection + family colours as
rung_f_build.stage8, so the eye judges the build against ground truth:
  1. the REAL grass|desert junction at blocks (13-15, 11-12) -- the bytes this build carries
  2. the junction IN CONTEXT (11-17, 9-14) -- the real desert MASS the ecotone is the margin of
  3. a pure stock grass coast region -- the flat-grass island language

Outputs -> out/rung_f/renders/calib_*.png . No writes to the install.
"""
from __future__ import annotations
import math, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent
REPO = STUDY.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(STUDY))

from ff9mapkit.world import extract as X          # noqa: E402
from seam_null_recon import FAM_OF                # noqa: E402
from PIL import Image, ImageDraw                  # noqa: E402

RENDER_DIR = STUDY / "out" / "rung_f" / "renders"
RENDER_DIR.mkdir(parents=True, exist_ok=True)

FAM_COL = {"grass": (86, 140, 60), "desert": (200, 176, 110), "dunes": (222, 200, 140),
           "scrub": (150, 165, 90), "brush": (170, 150, 80), "snow": (225, 230, 235),
           "canyon": (180, 120, 90), "rock": (120, 112, 104), "hole": (40, 60, 40),
           None: (150, 150, 150)}


def gather_tris(blocks, part="terrain"):
    tris = []
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part=part)
        except Exception as e:
            print(f"  block {bx},{by} part={part}: {e}")
            continue
        if bm is None or not bm.tris:
            continue
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            try:
                p3 = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
                idall0 = int(round(bm.tangents[tri[0]][0]))
                topo = X.decode_id(idall0)["topograph"]
            except Exception:
                continue
            fam = FAM_OF.get(topo)
            if topo == 49:
                fam = "rock"
            tris.append((p3, FAM_COL.get(fam, FAM_COL[None]), sum(p[1] for p in p3) / 3.0))
    return tris


def planview(tris, fname, title, shade=False):
    if not tris:
        print(f"  no tris for {fname}"); return
    xs = [p[0] for (p3, _c, _y) in tris for p in p3]
    zs = [p[2] for (p3, _c, _y) in tris for p in p3]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    W, H, pad = 900, 900, 30
    s = min((W - 2 * pad) / (x1 - x0 or 1), (H - 2 * pad) / (z1 - z0 or 1))
    img = Image.new("RGB", (W, H + 26), (20, 22, 26))
    dr = ImageDraw.Draw(img)
    dr.text((pad, 6), title, fill=(235, 225, 170))
    light = (0.5, 0.8, 0.3); ll = math.sqrt(sum(c * c for c in light))
    lv = [c / ll for c in light]
    for (p3, col, _my) in sorted(tris, key=lambda t: t[2]):
        pts = [(pad + (p[0] - x0) * s, 26 + H - pad - (p[2] - z0) * s) for p in p3]
        c = col
        if shade:
            e1 = [p3[1][k] - p3[0][k] for k in range(3)]
            e2 = [p3[2][k] - p3[0][k] for k in range(3)]
            gn = [e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0]]
            gl = math.sqrt(sum(q*q for q in gn)) or 1.0
            sh = max(0.35, min(1.0, 0.45 + 0.55 * abs(sum(gn[k]*lv[k] for k in range(3)) / gl)))
            c = tuple(int(v * sh) for v in col)
        dr.polygon(pts, fill=c)
    img.save(RENDER_DIR / fname)
    print(f"  wrote {fname}  (bbox {x0:.0f},{z0:.0f} .. {x1:.0f},{z1:.0f})")


def oblique(tris, fname, title, pitch=32.0, az_deg=215.0):
    if not tris:
        print(f"  no tris for {fname}"); return
    xs = [p[0] for (p3, _c, _y) in tris for p in p3]
    zs = [p[2] for (p3, _c, _y) in tris for p in p3]
    ys = [p[1] for (p3, _c, _y) in tris for p in p3]
    cxw, czw = (min(xs)+max(xs))/2, (min(zs)+max(zs))/2
    land_h = min(ys)
    W, H = 1000, 620
    az, pr = math.radians(az_deg), math.radians(pitch)
    order = sorted(tris, key=lambda t: -(math.cos(az)*(sum(p[0] for p in t[0])/3-cxw)
                                         + math.sin(az)*(sum(p[2] for p in t[0])/3-czw)))
    proj, pts_all = [], []
    for (p3, col, _my) in order:
        sp = []
        for p in p3:
            dx, dz, dy = p[0]-cxw, p[2]-czw, p[1]-land_h
            rx = math.cos(az)*dx - math.sin(az)*dz
            rz = math.sin(az)*dx + math.cos(az)*dz
            sy = rz*math.sin(pr) - dy*math.cos(pr)
            sp.append((rx, sy)); pts_all.append((rx, sy))
        proj.append((sp, p3, col))
    pxs = [q[0] for q in pts_all]; pys = [q[1] for q in pts_all]
    s = min((W-40)/(max(pxs)-min(pxs) or 1), (H-40)/(max(pys)-min(pys) or 1))
    img = Image.new("RGB", (W, H + 26), (20, 22, 26))
    dr = ImageDraw.Draw(img)
    dr.text((20, 6), title, fill=(235, 225, 170))
    lv = (0.4, 0.82, 0.4); ll = math.sqrt(sum(c*c for c in lv)); lv = [c/ll for c in lv]
    for (sp, p3, col) in proj:
        pts = [(20 + (q[0]-min(pxs))*s, 26 + 20 + (q[1]-min(pys))*s) for q in sp]
        e1 = [p3[1][k]-p3[0][k] for k in range(3)]
        e2 = [p3[2][k]-p3[0][k] for k in range(3)]
        gn = [e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0]]
        gl = math.sqrt(sum(q*q for q in gn)) or 1.0
        sh = max(0.35, min(1.0, 0.45 + 0.55 * abs(sum(gn[k]*lv[k] for k in range(3)) / gl)))
        dr.polygon(pts, fill=tuple(int(v*sh) for v in col))
    img.save(RENDER_DIR / fname)
    print(f"  wrote {fname}")


if __name__ == "__main__":
    # 1. the real junction, tight
    j_blocks = [(x, y) for y in (11, 12) for x in (13, 14, 15)]
    tj = gather_tris(j_blocks)
    print(f"junction tight tris={len(tj)}")
    planview(tj, "calib_junction_plan.png",
             "STOCK CALIB -- real grass|desert junction (13-15,11-12) planview [ground truth]")
    oblique(tj, "calib_junction_oblique.png",
            "STOCK CALIB -- real junction (13-15,11-12) oblique az215/pitch32")

    # 2. the junction IN CONTEXT -- the real desert MASS
    ctx_blocks = [(x, y) for y in range(9, 15) for x in range(11, 18)]
    tc = gather_tris(ctx_blocks)
    print(f"context tris={len(tc)}")
    planview(tc, "calib_context_plan.png",
             "STOCK CALIB -- junction in context (11-17,9-14): the ecotone is the MARGIN of a desert MASS")
    oblique(tc, "calib_context_oblique.png",
            "STOCK CALIB -- desert-mass context oblique az215/pitch32")

    # 3. a pure stock grass coast region for the island silhouette language
    grass_blocks = [(x, y) for y in range(2, 6) for x in range(2, 6)]
    tg = gather_tris(grass_blocks)
    print(f"grass-coast tris={len(tg)}")
    planview(tg, "calib_grasscoast_plan.png",
             "STOCK CALIB -- a stock grass coast region (2-5,2-5): FF9 landmass silhouette language")
