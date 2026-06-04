#!/usr/bin/env python3
"""Derive the per-camera Blender-VIEW offset: the 3D nudge that makes Blender's pinhole projection
of the imported walkmesh match FF9's exact 2D-BG projection (cam.to_canvas, which the footprint
nails). Validate against the user's hand-calibrated GLGV nudge (Blender 3.9016, -0.20103, 42.188).
"""
import os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ff9mapkit", "blender"))
from ff9mapkit import extract
from ff9mapkit.scene import bgs, bgi, cam
from ff9mapkit_blender import bridge


def blender_pixel(P_bl, b, res, off=(0.0, 0.0, 0.0)):
    """Blender's pinhole projection of a Blender-world point -> (px, py) in [0,res]. sensor_fit=H."""
    L = b["location"]; R = b["rotation"]; f = b["lens"]; sw = b["sensor_width"]
    rx, ry = res
    rel = [P_bl[i] + off[i] - L[i] for i in range(3)]
    # camera basis = COLUMNS of R (right, up, +Z=back); look down -Z
    xc = sum(rel[i] * R[i][0] for i in range(3))
    yc = sum(rel[i] * R[i][1] for i in range(3))
    zc = sum(rel[i] * R[i][2] for i in range(3))
    if -zc <= 1e-6:
        return None
    tan_x = (sw / 2.0) / f
    tan_y = tan_x * (ry / rx)              # sensor_fit horizontal, square pixels
    ndc_x = (xc / -zc) / tan_x
    ndc_y = (yc / -zc) / tan_y
    return ((ndc_x * 0.5 + 0.5) * rx, (0.5 - ndc_y * 0.5) * ry)


def analyze(field):
    path, folder, roles, env = extract.find_field(field)
    wm = bgi.BgiWalkmesh.from_bytes(extract._raw_bytes(env.container[roles["bgi"]].read()))
    c0 = bgs.parse_cameras(extract._raw_bytes(env.container[roles["bgs"]].read()))[0]
    ox, oy, oz = cam.walkmesh_world_offset((wm.orgPos.x, wm.orgPos.y, wm.orgPos.z))
    scrolling = c0.range[0] > 384 or c0.range[1] > 448
    b = bridge.ff9_cam_to_blender(c0, sensor_width=float(c0.range[0])) if scrolling else bridge.ff9_cam_to_blender(c0)
    res = (c0.range[0], c0.range[1])

    # floor verts = those near the MODAL raw height (the main walkable surface), world frame
    import statistics as _st
    med = _st.median([v.y for v in wm.verts])
    wv = [(v.x + ox, v.y + oy, v.z + oz) for v in wm.verts]
    floor = [p for p, v in zip(wv, wm.verts) if abs(v.y - med) < 60]
    print(f"== {folder[:30]} == scrolling={scrolling} res={res} lens={b['lens']:.1f} sw={b['sensor_width']:.0f} floor-verts={len(floor)}")

    # residual: to_canvas (GTE, exact) vs blender pinhole, for the floor
    dxs, dys = [], []
    for P in floor:
        gx, gy = cam.to_canvas(P, c0)
        Pbl = bridge.ff9_verts_to_blender([P])[0]
        bp = blender_pixel(Pbl, b, res)
        if bp is None:
            continue
        dxs.append(gx - bp[0]); dys.append(gy - bp[1])
    import statistics
    print(f"   pixel residual (GTE - pinhole): dx mean {statistics.fmean(dxs):+.1f} dy mean {statistics.fmean(dys):+.1f}")

    # fit a Blender 3D offset D so pinhole(vert + D) ~= to_canvas(vert): coordinate-descent
    D = [0.0, 0.0, 0.0]
    def cost(D):
        s = 0.0
        for P in floor:
            gx, gy = cam.to_canvas(P, c0)
            Pbl = bridge.ff9_verts_to_blender([P])[0]
            bp = blender_pixel(Pbl, b, res, D)
            if bp is None:
                return 1e18
            s += (gx - bp[0]) ** 2 + (gy - bp[1]) ** 2
        return s
    step = 64.0
    for _ in range(40):
        improved = False
        for i in range(3):
            for s in (step, -step):
                cand = D[:]; cand[i] += s
                if cost(cand) < cost(D):
                    D = cand; improved = True
        if not improved:
            step /= 2.0
            if step < 0.01:
                break
    print(f"   fitted Blender offset D = ({D[0]:.2f}, {D[1]:.2f}, {D[2]:.2f})   residual after = {cost(D)**0.5/max(1,len(floor)):.2f}px/vert")
    return D


print("--- GLGV (user calibrated Blender nudge = 3.9016, -0.20103, 42.188) ---")
analyze("glgv_map792")
print("--- GRGR (pitch ~49, should need ~0) ---")
analyze("grgr_map420_gr_cen")
print("--- BRMC (head-on) ---")
analyze("brmc_map271_bu_bed")
