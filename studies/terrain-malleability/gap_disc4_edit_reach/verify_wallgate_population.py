"""VERIFY (adversarial) -- G12 on the ACTUAL s5 population, not s5d's proxy sample.

s5d samples ANY 4u lattice point of a refused cell (walkable or not -- a centre ON a cliff included), with a
single-block approximation of the touched set, and asks whether the WORST post-edit edge was already over the
ceiling in stock. G12 then attaches that 99.35% to s5's refusals (walkable centres, multi-block touched sets).
Here, on exactly s5's population (refused cells, disc-1-walkable 4u lattice, raise/lower 4u, r 8/16/24, every
touched block in the kit's own loop range): for each disc-1 refusal --
  worst_preexisting : the worst edge (argmax post slope, first block that fails) was already > WALL in stock (s5d's metric);
  all_preexisting   : EVERY over-ceiling edge was already over the ceiling in stock (no edge newly crosses it);
  relaxed_pass      : no over-ceiling edge got STEEPER than stock (post <= pre + 1e-9) -- what a pre-vs-post
                      gate would accept.
Read-only. Writes out/verify_wallgate_population.json.
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
import numpy as np                                    # noqa: E402

data = L.load_cache()
meshes = data["meshes"]
WALL = L.P.WALK_RAY_START / L.P.WALK_SPEED
blk = {}
for (d, x, y, p), m in meshes.items():
    if d != 1 or p != "terrain":
        continue
    V, T = m["V"], m["T"]
    Vw = V.copy(); Vw[:, 0] += 64 * x; Vw[:, 2] -= 64 * y
    E = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
    Et = np.concatenate([np.arange(len(T))] * 3)
    blk[(x, y)] = {"V": V, "T": T, "E": E, "Et": Et, "XZ": Vw[:, [0, 2]]}


def slope(y, V, E):
    rise = np.abs(y[E[:, 1]] - y[E[:, 0]])
    run = np.hypot(V[E[:, 1], 0] - V[E[:, 0], 0], V[E[:, 1], 2] - V[E[:, 0], 2])
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(run > 1e-9, rise / np.where(run > 1e-9, run, 1), np.where(rise > 1e-9, np.inf, 0.0))


def evaluate(p, r, amt):
    bx0, bx1 = int(math.floor((p[0] - r) / 64)), int(math.floor((p[0] + r) / 64))
    by0, by1 = int(math.floor(-(p[1] + r) / 64)), int(math.floor(-(p[1] - r) / 64))
    refused, worst_pre, all_pre, relaxed = False, None, True, True
    for bx in range(bx0, bx1 + 1):
        for by in range(by0, by1 + 1):
            b = blk.get((bx, by))
            if b is None:
                continue
            dist = np.hypot(b["XZ"][:, 0] - p[0], b["XZ"][:, 1] - p[1])
            t = np.clip(dist / r, 0, 1)
            w = 1 - t * t * (3 - 2 * t)
            moved = w > 0
            if not moved.any():
                continue
            sel = moved[b["T"]].any(1)[b["Et"]]
            E = b["E"][sel]
            post = slope(b["V"][:, 1] + amt * w, b["V"], E)
            pre = slope(b["V"][:, 1], b["V"], E)
            over = post > WALL
            if not over.any():
                continue
            if not refused:                              # the kit raises on the FIRST failing block in loop order
                k = int(np.argmax(post))
                worst_pre = bool(pre[k] > WALL)
            refused = True
            if (pre[over] <= WALL).any():
                all_pre = False
            if (post[over] > pre[over] + 1e-9).any():
                relaxed = False
    return refused, worst_pre, all_pre, relaxed


s1g = json.loads((L.OUT / "s1_gate.json").read_text(encoding="utf-8"))
refused_cells = sorted(tuple(map(int, k.split(","))) for k, r in s1g["rows"].items() if r["land"] and r["shipped"].startswith("SKIP"))
objs = L.mesh_objects()
cnt = Counter()
by_r = Counter()
for c in refused_cells:
    parts = L.blockmeshes(1, c[0], c[1], objs)
    ml = L.walk_meshlist(parts)
    ix = [L.P.build_index(bm) for _, bm in ml]
    for i in range(16):
        for j in range(16):
            g = L.P.place(ml, 4 * i + 0.013, -(4 * j) - 0.017, 0.0, sky=True, index=ix)
            if g[3] is None or g[3] not in L.P.WALK_OK or g[1] == "MISS":
                continue
            p = (64 * c[0] + 4 * i, -(64 * c[1] + 4 * j))
            for r in (8.0, 16.0, 24.0):
                for amt in (4.0, -4.0):
                    ref, wp, ap, rx = evaluate(p, r, amt)
                    cnt["edits"] += 1
                    if not ref:
                        continue
                    cnt["refused"] += 1
                    cnt["worst_preexisting"] += wp
                    cnt["all_preexisting"] += ap
                    cnt["relaxed_pass"] += rx
                    by_r[(r, "refused")] += 1
                    by_r[(r, "relaxed_pass")] += rx
res = dict(cnt)
res["shares"] = {k: round(cnt[k] / cnt["refused"], 4) for k in ("worst_preexisting", "all_preexisting", "relaxed_pass")}
res["by_radius"] = {f"r{int(r)}": {"refused": by_r[(r, 'refused')], "relaxed_pass": by_r[(r, 'relaxed_pass')]} for r in (8.0, 16.0, 24.0)}
print(json.dumps(res, indent=1))
(L.OUT / "verify_wallgate_population.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
