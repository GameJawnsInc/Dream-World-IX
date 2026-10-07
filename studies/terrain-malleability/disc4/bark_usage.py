"""STEP 8 -- the BARK TILE: how widely does each disc use the atlas tile the disc-4 crescents concentrate on?

ridge_art_owner.py found the crescent triangles' texels concentrated in 32px atlas cells (23..24, 20..23)
= pixel window x[736,800) y[640,768) of the 1024^2 terrain atlas (by eye: a fibrous, diagonally-grained
bark/root tile with green moss flecks -- crop kept OUT of the repo). Here: every terrain triangle (both discs,
Form 1) whose UV CENTROID falls in that window -> per-block counts, topographs, and mean height above the
surrounding ground. Disc-1 users = where the art already existed; disc-4-only users = where it was stamped.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/bark_usage.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X                                  # noqa: E402
from ff9mapkit.world import locate as LOC            # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
N = 1024
WIN = (736, 800, 640, 768)                           # px x0,x1,y0,y1 (PIL top-down; v flipped)
objs = L.mesh_objects()


def in_win(uv):
    u = sum(p[0] for p in uv) / 3
    v = sum(p[1] for p in uv) / 3
    px, py = u * (N - 1), (1 - v) * (N - 1)
    return WIN[0] <= px < WIN[2 - 1] and WIN[2] <= py < WIN[3]


use = {1: defaultdict(Counter), 4: defaultdict(Counter)}
for (d, lod, x, y, p), o in sorted(objs.items()):
    if lod != "0_1" or p != "terrain":
        continue
    bm = L.decode(o, d, x, y, lod)
    for r in L.tri_records(bm):
        if r["uv"] and in_win(r["uv"]):
            use[d][(x, y)][X.decode_id(r["id"])["topograph"]] += 1
b1, b4 = set(use[1]), set(use[4])
print(f"bark-window tris: disc1 {sum(sum(c.values()) for c in use[1].values())} on {len(b1)} blocks; "
      f"disc4 {sum(sum(c.values()) for c in use[4].values())} on {len(b4)} blocks")
print(f"blocks using it on BOTH: {len(b1 & b4)}; disc4-only: {len(b4 - b1)}; disc1-only: {len(b1 - b4)}")
print("disc-1 users (block: topo counts, landmark):")
for b in sorted(b1):
    lm = LOC.nearest_landmark(b[0] * 64 + 32, -b[1] * 64 - 32)
    print(f"   {b}: {dict(use[1][b])}  ~{lm['name']} ({lm['dist']:.0f}u)")
t4 = Counter()
for b in b4 - b1:
    t4.update(use[4][b])
print("topographs of the bark tris on disc-4-only blocks:", dict(t4.most_common()))
cont = Counter()
for b in b4 - b1:
    cont[LOC.nearest_landmark(b[0] * 64 + 32, -b[1] * 64 - 32)["name"]] += 1
print("disc-4-only bark blocks by nearest landmark:", dict(cont.most_common()))
(OUT / "bark_usage.json").write_text(json.dumps({
    "window_px": WIN, "disc1_blocks": {str(b): dict(c) for b, c in use[1].items()},
    "disc4_blocks": {str(b): dict(c) for b, c in use[4].items()}}, indent=0), encoding="utf-8")
print("->", OUT / "bark_usage.json")
