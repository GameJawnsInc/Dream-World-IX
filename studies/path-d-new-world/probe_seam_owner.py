"""Seam forensics: WHICH triangles own the light waterline pixels? READ-ONLY.

The playtest-8 'light seaming' — detect light/neutral pixels adjacent to sea
pixels at the close cameras, look up their owner triangles via the raster's
id buffer, and report each owner's part / centroid / uv / geometry class.
No more guessing which construction paints the seam.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_gate as RG                                    # noqa: E402


def classify(part, verts, uvs, tri):
    a, b, c = verts[tri[0]], verts[tri[1]], verts[tri[2]]
    cy = (a[1] + b[1] + c[1]) / 3.0
    n = np.cross(b - a, c - a)
    nl = np.linalg.norm(n)
    ny = n[1] / nl if nl > 1e-12 else 0.0
    vs = [float(uvs[i][1]) for i in tri]
    if part != "Terrain":
        return part
    if cy > 3.0 and abs(ny) > 0.7:
        return "lawn(y~3.2)"
    if cy < 0.2 and abs(ny) > 0.7:
        return "apron/shelf(y~0)"
    if abs(ny) <= 0.35:
        return f"wall(v {min(vs):.3f}-{max(vs):.3f})"
    return f"slope(y {cy:.1f}, ny {ny:+.2f})"


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "live"
    batches = RG.load_batches(RG.state_src(tag))
    for vn in ("owner_close", "graze"):
        img, ids = RG.raster(RG.VIEWS[vn], batches, f"forensic_{tag}_{vn}",
                             want_ids=True)
        f = img.astype(np.int32)
        light = f.min(axis=2) > 110                          # neutral-bright px
        sea = (f[:, :, 2] > f[:, :, 0] + 25) & (f[:, :, 2] > 90)  # blue-ish
        near_sea = np.zeros_like(sea)
        R = 6                                               # within 6 px of sea
        for dy in range(-R, R + 1):
            near_sea |= np.roll(sea, dy, axis=0)
        for dx in range(-R, R + 1):
            near_sea |= np.roll(near_sea, dx, axis=1)
        m = light & near_sea & (ids >= 0)
        n = int(m.sum())
        own = Counter(ids[m].tolist())
        print(f"\n[{vn}] {n} light-near-sea px, {len(own)} owner tris; top:")
        for oid, cnt in own.most_common(14):
            bi, ti = oid >> 20, oid & ((1 << 20) - 1)
            part, verts, uvs, tris = batches[bi]
            t = tris[ti]
            cx = (verts[t[0]] + verts[t[1]] + verts[t[2]]) / 3.0
            cls = classify(part, verts, uvs, t)
            uv0 = uvs[t[0]]
            print(f"   {cnt:5d}px  {part:8s} b{bi}#t{ti}  "
                  f"@({cx[0]:7.2f},{cx[1]:6.2f},{cx[2]:8.2f})  {cls}  "
                  f"uv0=({uv0[0]:.4f},{uv0[1]:.4f})")
        vis = (img // 3).astype(np.uint8)
        vis[m] = (255, 240, 40)
        from PIL import Image
        Image.fromarray(vis).save(RG.OUTD / f"seampx_{tag}_{vn}.png")


if __name__ == "__main__":
    main()
