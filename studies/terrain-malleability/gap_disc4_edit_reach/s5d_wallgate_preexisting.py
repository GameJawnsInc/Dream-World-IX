"""STEP 5d (side observation) -- WHY does world-terrain's one-way-wall gate refuse so many synthetic edits ON DISC 1?

s5 found terrain._walk_gate (terrain.py:31-87) refusing 4,978 of 17,507 raise-8 and 11,701 of 17,507 raise-24
edits at walkable lattice points of refused cells. The gate scans EVERY edge of every triangle that has a moved
vertex (terrain.py:60-74) -- including edges whose slope the edit did not create. Hypothesis: most refusals are
PRE-EXISTING stock walls/cliffs (vertical edges) adjacent to the support, not slopes the reshape produced.
Measure, on a deterministic sample of disc-1-refused edits: is the worst offending edge already above the wall
ceiling in STOCK (before the deform)? CALIBRATION: the vectorized gate here is s5's (V1: 80/80 agreement with
terrain.reshape(dry_run=True)); a flat synthetic block with a +40 spike must be refused for a CREATED slope.
Writes out/s5d_wallgate.json.
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s5d_wallgate_preexisting.py
"""
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
import numpy as np                                    # noqa: E402

data = L.load_cache()
meshes = data["meshes"]
WALL = L.P.WALK_RAY_START / L.P.WALK_SPEED
rows = {tuple(map(int, k.split(","))): r for k, r in json.loads((L.OUT / "s1_gate.json").read_text(encoding="utf-8"))["rows"].items()}
refused = sorted(c for c, r in rows.items() if r["land"] and r["shipped"].startswith("SKIP"))


def gate(V, T, p_local, r, amt):
    """Returns (refused?, worst_t_post, worst_t_pre_of_that_edge)."""
    dist = np.hypot(V[:, 0] - p_local[0], V[:, 2] - p_local[1])
    t = np.clip(dist / r, 0, 1)
    w = 1 - t * t * (3 - 2 * t)
    moved = w > 0
    if not moved.any():
        return False, 0, 0
    y1 = V[:, 1] + amt * w
    tri = moved[T].any(1)
    E = np.concatenate([T[tri][:, [0, 1]], T[tri][:, [1, 2]], T[tri][:, [2, 0]]])
    run = np.hypot(V[E[:, 1], 0] - V[E[:, 0], 0], V[E[:, 1], 2] - V[E[:, 0], 2])
    def slope(y):
        rise = np.abs(y[E[:, 1]] - y[E[:, 0]])
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(run > 1e-9, rise / np.where(run > 1e-9, run, 1), np.where(rise > 1e-9, np.inf, 0.0))
    post, pre = slope(y1), slope(V[:, 1])
    k = int(np.argmax(post))
    return bool(post[k] > WALL), float(post[k]), float(pre[k])


# calibration: flat 3x3 grid, a raise r=1 at a vertex -> created slope
g = np.array([[x, 0.0, -z] for z in range(0, 9, 4) for x in range(0, 9, 4)], float)
T = []
for zi in range(2):
    for xi in range(2):
        a = zi * 3 + xi
        T += [[a, a + 1, a + 3], [a + 1, a + 4, a + 3]]
ref, post, pre = gate(g, np.array(T), (4.0, -4.0), 4.0, 40.0)
assert ref and pre == 0.0, "calibration: a CREATED steep slope must refuse with a flat pre-slope"
print("calibration OK: created slope refuses (post %.2f, pre %.2f)" % (post, pre))

rng = random.Random(3)
res = {"sampled_refusals": 0, "preexisting_wall": 0, "created": 0}
tries = 0
while res["sampled_refusals"] < 2000 and tries < 40000:
    tries += 1
    c = rng.choice(refused)
    m = meshes[(1, c[0], c[1], "terrain")]
    p = (4 * rng.randrange(16), -4 * rng.randrange(16))
    r = rng.choice([8.0, 16.0, 24.0])
    amt = rng.choice([4.0, -4.0])
    ref, post, pre = gate(m["V"], m["T"], p, r, amt)          # single-block approximation of the touched set
    if not ref:
        continue
    res["sampled_refusals"] += 1
    if pre > WALL:
        res["preexisting_wall"] += 1
    else:
        res["created"] += 1
res["preexisting_share"] = round(res["preexisting_wall"] / max(1, res["sampled_refusals"]), 4)
print(res)
(L.OUT / "s5d_wallgate.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
