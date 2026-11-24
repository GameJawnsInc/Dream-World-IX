"""Does the ear-clipper produce overlapping triangles on a SIMPLE concave polygon?"""
from ff9mapkit import imagefield as I

def tri_area_sum(verts, faces):
    return sum(abs(I._cross(verts[a], verts[b], verts[c])) / 2 for a, b, c in faces)

def check(name, poly):
    v, f = I.triangulate(poly)
    print(name, "faces", len(f), "expected", len(poly) - 2, "tri sum", round(tri_area_sum(v, f)),
          "poly", round(abs(I._signed_area(poly))))
    return v, f

U = [(0, 0), (3000, 0), (3000, 2000), (1530, 2000), (1530, 300), (1470, 300), (1470, 2000), (0, 2000)]
check("U", U)
v, f = check("Uout", I.outset_polygon(U, 48))
for t in f:
    print("  ", [tuple(round(c) for c in v[i]) for i in t], round(abs(I._cross(*[v[i] for i in t])) / 2))
# a simpler comb
comb = [(0, 0), (1000, 0), (1000, 1000), (600, 1000), (600, 200), (400, 200), (400, 1000), (0, 1000)]
check("comb", comb)
# narrow notch < 2*48 -> outset crosses itself
N = [(0, 0), (3000, 0), (3000, 2000), (1520, 2000), (1520, 300), (1480, 300), (1480, 2000), (0, 2000)]
o = I.outset_polygon(N, 48)
print("narrow notch outset", [tuple(round(c) for c in p) for p in o])
check("Nout", o)
