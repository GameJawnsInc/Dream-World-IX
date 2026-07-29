"""Rung 3 scoping bench: click-ray -> walkmesh raycast on REAL sloped fields.

For sampled triangle centroids of a field's walkmesh: project to canvas via the field's own
camera (to_canvas), rebuild the click ray (the same Minv construction unproject_floor uses,
offset-folded), Moller-Trumbore over ALL world-frame triangles, take the nearest hit with
s > 0. Exact recovery = the hit lands back on the sampled centroid; an occluded centroid
(another floor nearer along the ray) is VISIBILITY SEMANTICS, not error — count separately.
"""
import math
import sys

sys.path.insert(0, r"C:\gd\Dream-World-IX\.claude\worktrees\click-authoring-plan-d1f7f7\ff9mapkit")

from ff9mapkit import extract
from ff9mapkit.scene import bgi as _bgi, bgs, cam as C

FIELDS = ["fbg_n02_alxc_map056b_ac_lti_2",     # dom spread 9727u, 3 floors (a worst-8 field)
          "fbg_n43_ipsn_map740_ip_ext_0",      # dom spread 8329u, 2 floors
          "fbg_n21_grgr_map420_gr_cen_0",      # the GRGR tunnel (multi-floor reference)
          "fbg_n11_ldbm_map158_lb_plz_0"]      # the nonzero-centerOffset donor


def click_ray(cam, cx, cy):
    d = C.decompose(cam)
    Minv = C.inv3(d["R_view"])
    W, H, D = cam.range[0], cam.range[1], cam.proj
    ox, oy = cam.centerOffset
    ray = C.mv(Minv, (cx - ox - W / 2.0, H / 2.0 + oy - cy, D))
    return d["C"], ray


def moller(orig, ray, a, b, c):
    e1 = [b[i] - a[i] for i in range(3)]
    e2 = [c[i] - a[i] for i in range(3)]
    p = [ray[1] * e2[2] - ray[2] * e2[1], ray[2] * e2[0] - ray[0] * e2[2],
         ray[0] * e2[1] - ray[1] * e2[0]]
    det = e1[0] * p[0] + e1[1] * p[1] + e1[2] * p[2]
    if abs(det) < 1e-12:
        return None
    t = [orig[i] - a[i] for i in range(3)]
    u = (t[0] * p[0] + t[1] * p[1] + t[2] * p[2]) / det
    if u < -1e-9 or u > 1 + 1e-9:
        return None
    q = [t[1] * e1[2] - t[2] * e1[1], t[2] * e1[0] - t[0] * e1[2], t[0] * e1[1] - t[1] * e1[0]]
    v = (ray[0] * q[0] + ray[1] * q[1] + ray[2] * q[2]) / det
    if v < -1e-9 or u + v > 1 + 1e-9:
        return None
    s = (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2]) / det
    return s if s > 1e-9 else None


for f in FIELDS:
    _, folder, roles, env = extract.find_field(f)
    objs = dict(env.container.items())
    cam = bgs.parse_cameras(extract._raw_bytes(objs[roles["bgs"]].read()))[0]
    mesh = _bgi.BgiWalkmesh.from_bytes(extract._raw_bytes(objs[roles["bgi"]].read()))
    wv = mesh.world_verts()
    tris = [tuple(wv[vi] for vi in t.vtx) for t in mesh.tris]
    exact = occl = offcam = 0
    worst = 0.0
    step = max(1, len(tris) // 120)
    for tri in tris[::step]:
        cen = tuple(sum(p[i] for p in tri) / 3.0 for i in range(3))
        px, py, resz = C.project(cen, cam)
        if resz <= 0:
            offcam += 1
            continue
        cx, cy = C.to_canvas(cen, cam)
        orig, ray = click_ray(cam, cx, cy)
        best = None
        for a, b, c3 in tris:
            s = moller(orig, ray, a, b, c3)
            if s is not None and (best is None or s < best):
                best = s
        if best is None:
            offcam += 1
            continue
        hit = tuple(orig[i] + best * ray[i] for i in range(3))
        err = math.dist(hit, cen)
        if err < 1e-6:
            exact += 1
            worst = max(worst, err)
        else:
            occl += 1                       # a nearer surface owns this pixel (or a graze)
    n = exact + occl + offcam
    print(f"{folder}: {n} sampled -> exact {exact} ({exact/max(1,n):.0%}) · "
          f"occluded-by-nearer {occl} · off-camera {offcam} · worst exact err {worst:.2e}u")
