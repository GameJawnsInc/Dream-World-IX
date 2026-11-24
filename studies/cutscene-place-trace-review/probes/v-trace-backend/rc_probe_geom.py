"""Geometry backend probes: outset/triangulate on hostile input, zone Int16, acute spikes."""
import math, sys
from ff9mapkit import imagefield as I
from ff9mapkit.scene import guide

def area(poly):
    return abs(I._signed_area(poly))

def tri_area_sum(verts, faces):
    s = 0
    for a, b, c in faces:
        s += abs(I._cross(verts[a], verts[b], verts[c])) / 2
    return s

print("== bowtie (self-intersecting) ==")
bow = [(0, 0), (1000, 1000), (1000, 0), (0, 1000)]
v, f = I.triangulate(bow)
print("signed area", I._signed_area(bow), "faces", f, "tri area sum", tri_area_sum(v, f))

print("== collinear 3 ==")
col = [(0, 0), (500, 0), (1000, 0)]
v, f = I.triangulate(col)
print("faces", f, "area", tri_area_sum(v, f))
print("outset collinear:", I.outset_polygon(col, 48))

print("== duplicate vertex square ==")
sq = [(0, 0), (1000, 0), (1000, 0), (1000, 1000), (0, 1000)]
o = I.outset_polygon(sq, 48)
print("outset:", [tuple(round(c, 1) for c in p) for p in o])

print("== acute spike (5 deg) ==")
ang = math.radians(5)
spike = [(0, 0), (2000, 0), (2000 + 0, 0)]  # placeholder
spike = [(0, 0), (2000, 0), (0, 2000 * math.tan(ang))]
o = I.outset_polygon(spike, 48)
for p, q in zip(I._as_ccw(spike), o):
    print("  vert", tuple(round(c) for c in p), "->", tuple(round(c) for c in q),
          "moved", round(math.hypot(q[0] - p[0], q[1] - p[1])))

print("== concave L outset+inset invert ==")
L = [(0, 0), (2000, 0), (2000, 500), (500, 500), (500, 2000), (0, 2000)]
o = I.outset_polygon(L, 48)
back = I.outset_polygon(o, -48)
print("L back err:", max(math.hypot(a[0]-b[0], a[1]-b[1]) for a, b in zip(I._as_ccw(L), back)))

print("== concave narrow notch: outset self-overlap ==")
U = [(0, 0), (3000, 0), (3000, 2000), (1530, 2000), (1530, 300), (1470, 300), (1470, 2000), (0, 2000)]
o = I.outset_polygon(U, 48)
print("U notch outset:", [tuple(round(c) for c in p) for p in o])
print("signed area in", I._signed_area(U), "out", I._signed_area(o))
v, f = I.triangulate(o)
print("tri area sum", round(tri_area_sum(v, f)), "poly area", round(area(o)))

print("== zone near horizon ==")
cam = guide.make_camera(26.0, 3000.0, fov_x_deg=42.0, range_wh=(384, 448))
from ff9mapkit.scene import cam as C
hy = C.horizon_canvas_y(cam)
print("horizon y", hy)
for dy in (0.5, 2, 5, 10):
    try:
        print(" y=hy+%g" % dy, I.click_to_world(cam, (192, hy + dy)))
    except Exception as e:
        print(" y=hy+%g ERR %s" % (dy, e))
