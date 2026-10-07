"""STEP 5c -- does a REPLAYED reshape still weld at block borders on disc 4?

terrain.reshape moves a vertex by a function of its WORLD position only (mesh.deform_radial/_falloff), so two
COINCIDENT border vertices of neighbouring blocks always receive the identical delta: a coincident weld can never
open. What CAN open is a border T-JUNCTION: a vertex on A's border with no coincident vertex on B's border while
B's border spans that along-coordinate. There the smooth falloff is not linear along B's edge, so a reshape opens a
second-order gap |delta(p) - lerp(delta(q1), delta(q2))| (on disc 1 as on disc 4).

So the replay-weld question reduces to: does disc 4 add border T-junctions that disc 1 does not have? For every
4-adjacent land|land pair (Terrain on both sides) on each disc: count A-border vertices whose along-coordinate is
covered by B's border extent but has no B vertex there (and vice versa).
CALIBRATION: the census must find 0 T-junctions on a pair of byte-identical neighbours whose borders are known to
weld exactly (an all-PASS pair from s1), and must find >0 on a synthetic copy of B with one border vertex nudged
along the border by 0.5u.
Also a direct REPLAY check on a sample of multi-block edits from s5's population: after deforming every touched
disc-4 block, the max |Y_A - Y_B| over coincident border vertices must equal the stock disc-4 value (0 new gap).
Writes out/s5c_border_welds.json.
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s5c_border_welds.py
"""
import copy
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
import numpy as np                                    # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402

data = L.load_cache()
meshes = data["meshes"]
rows = {tuple(map(int, k.split(","))): r for k, r in json.loads((L.OUT / "s1_gate.json").read_text(encoding="utf-8"))["rows"].items()}
land = {(x, y) for (d, x, y, p) in meshes if p == "terrain" and d == 1}


def border(V, side):
    """{along: [y,...]} of one block-local border (E: x=64, W: x=0, S: z=-64, N: z=0)."""
    out = {}
    for v in V:
        if side == "E" and abs(v[0] - 64) < 1e-3:
            out.setdefault(round(float(v[2]), 3), []).append(float(v[1]))
        elif side == "W" and abs(v[0]) < 1e-3:
            out.setdefault(round(float(v[2]), 3), []).append(float(v[1]))
        elif side == "S" and abs(v[2] + 64) < 1e-3:
            out.setdefault(round(float(v[0]), 3), []).append(float(v[1]))
        elif side == "N" and abs(v[2]) < 1e-3:
            out.setdefault(round(float(v[0]), 3), []).append(float(v[1]))
    return out


def tjunc(a, b):
    """# of along-coords present on one side only while inside the other side's covered span."""
    n = 0
    for s, t in ((a, b), (b, a)):
        if not t:
            continue
        lo, hi = min(t), max(t)
        n += sum(1 for k in s if lo < k < hi and k not in t)
    return n


def pair_tj(d, A, B, side):
    VA, VB = meshes[(d, A[0], A[1], "terrain")]["V"], meshes[(d, B[0], B[1], "terrain")]["V"]
    opp = {"E": "W", "S": "N"}[side]
    a, b = border(VA, side), border(VB, opp)
    # along coordinate frames agree: E/W borders share local z; S/N share local x
    return tjunc(a, b)


# calibration
cal = None
for A in sorted(land):
    B = (A[0] + 1, A[1])
    if B in land and rows[A]["shipped"].startswith("PASS") and rows[B]["shipped"].startswith("PASS") \
            and pair_tj(1, A, B, "E") == 0 and len(border(meshes[(1, A[0], A[1], "terrain")]["V"], "E")) > 3:
        cal = (A, B)
        break
assert cal, "need a clean calibration pair"
A, B = cal
VB = meshes[(1, B[0], B[1], "terrain")]["V"].copy()
wv = [i for i, v in enumerate(VB) if abs(v[0]) < 1e-3 and -60 < v[2] < -4]
VB[wv[0], 2] += 0.5
a, b = border(meshes[(1, A[0], A[1], "terrain")]["V"], "E"), border(VB, "W")
assert tjunc(a, b) > 0, "calibration: a nudged border vertex must register"
print("calibration OK: clean pair", cal, "0 T-junctions; nudged copy ->", tjunc(a, b))

res = {"pairs": 0, "tj_d1": 0, "tj_d4": 0, "pairs_more_on_d4": [], "pairs_fewer_on_d4": 0}
for A in sorted(land):
    for side, B in (("E", (A[0] + 1, A[1])), ("S", (A[0], A[1] + 1))):
        if B not in land:
            continue
        t1, t4 = pair_tj(1, A, B, side), pair_tj(4, A, B, side)
        res["pairs"] += 1
        res["tj_d1"] += t1
        res["tj_d4"] += t4
        if t4 > t1:
            res["pairs_more_on_d4"].append([list(A), list(B), t1, t4])
        elif t4 < t1:
            res["pairs_fewer_on_d4"] += 1
print(f"land|land pairs {res['pairs']}: border T-junction verts disc1 {res['tj_d1']} / disc4 {res['tj_d4']}; "
      f"pairs with MORE on disc 4: {len(res['pairs_more_on_d4'])} {res['pairs_more_on_d4'][:8]}; fewer: {res['pairs_fewer_on_d4']}")

# direct replay weld check on multi-block edits (coincident verts)
rng = random.Random(5)
refused = [c for c, r in rows.items() if r["land"] and r["shipped"].startswith("SKIP")]
chk = {"edits": 0, "new_gap_max": 0.0}
for _ in range(300):
    c = rng.choice(refused)
    i, j = rng.choice([0, 15]), rng.randrange(16)          # on/near a W or E border so the edit spans blocks
    p = (64 * c[0] + 4 * i, -(64 * c[1] + 4 * j))
    r = rng.choice([8.0, 16.0, 24.0])
    cells = [(c[0] + dx, c[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (c[0] + dx, c[1] + dy) in land]
    pre, post = {}, {}
    for cc in cells:
        V = meshes[(4, cc[0], cc[1], "terrain")]["V"].copy()
        pre[cc] = V.copy()
        wx, wz = V[:, 0] + 64 * cc[0], V[:, 2] - 64 * cc[1]
        t = np.clip(np.hypot(wx - p[0], wz - p[1]) / r, 0, 1)
        V[:, 1] += 4.0 * (1 - t * t * (3 - 2 * t))
        post[cc] = V
    moved = False
    for cc in cells:
        for side, nb in (("E", (cc[0] + 1, cc[1])), ("S", (cc[0], cc[1] + 1))):
            if nb not in pre:
                continue
            opp = {"E": "W", "S": "N"}[side]
            a0, b0 = border(pre[cc], side), border(pre[nb], opp)
            a1, b1 = border(post[cc], side), border(post[nb], opp)
            for k in set(a0) & set(b0):
                g0 = abs(min(a0[k]) - min(b0[k]))
                g1 = abs(min(a1[k]) - min(b1[k]))
                chk["new_gap_max"] = max(chk["new_gap_max"], g1 - g0)
                moved |= a1[k] != a0[k]
    chk["edits"] += moved
print("replay coincident-weld check:", chk)
assert chk["new_gap_max"] < 1e-9, "a replayed reshape must not open a coincident weld"
res["replay_weld_check"] = chk
(L.OUT / "s5c_border_welds.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
