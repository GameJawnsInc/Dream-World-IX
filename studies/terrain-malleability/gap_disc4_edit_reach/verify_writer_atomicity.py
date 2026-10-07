"""VERIFY (adversarial) -- G3 counterexample hunt: is the WRITER itself edit-atomic on disc 1?

terrain.reshape (terrain.py:126-167) deploys each touched block INSIDE the loop, immediately after that block's
own one-way-wall gate. If a LATER block (loop order: bx ascending, then by ascending) fails its gate, the
ValueError propagates after the earlier blocks were already written to Disc1, and auto_mirror never runs.
That would be a DISC-1 crack (a partial edit on the source disc) -- an atomicity defect upstream of the mirror.

(a) END-TO-END: search the s5 population (refused cells, walkable 4u lattice, raise +4 r8/r16/r24) for an edit
    whose FIRST touched block (loop order) passes its gate and a LATER one fails; run the shipped
    terrain.reshape(dry_run=False, skip_mirror=True) into a SCRATCH folder; catch the ValueError; check that the
    passing block's Disc1 override exists and the failing block's does not; measure the disc-1 border step.
(b) RATE: over the same population, the share of disc-1-gate-refused raises/lowers that leave >= 1 block
    written (vectorized gate, same as s5's V1-calibrated instrument), and the share that also move a vertex on
    the border between a written and an unwritten block.
Scratch only (GAP_DISC4_CACHE / verify_atomic); nothing under the install or the repo is written except
out/verify_writer_atomicity.json.
"""
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
import numpy as np                                    # noqa: E402
from scipy.spatial import cKDTree                     # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402
from ff9mapkit.world import terrain as TER           # noqa: E402

G = L.GAME
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
    blk[(x, y)] = {"V": V, "T": T, "E": E, "Et": Et, "XZ": Vw[:, [0, 2]], "kd": cKDTree(Vw[:, [0, 2]])}


def falloff(t):
    t = np.clip(t, 0, 1)
    return 1.0 - t * t * (3.0 - 2.0 * t)


def block_gate(c, p, r, amt):
    b = blk[c]
    dist = np.hypot(b["XZ"][:, 0] - p[0], b["XZ"][:, 1] - p[1])
    w = falloff(dist / r)
    moved = w > 0
    if not moved.any():
        return None                                    # not written (kit: `if not moved: continue`)
    y = b["V"][:, 1] + amt * w
    sel = moved[b["T"]].any(1)[b["Et"]]
    E = b["E"][sel]
    rise = np.abs(y[E[:, 1]] - y[E[:, 0]])
    run = np.hypot(b["V"][E[:, 1], 0] - b["V"][E[:, 0], 0], b["V"][E[:, 1], 2] - b["V"][E[:, 0], 2])
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(run > 1e-9, rise / np.where(run > 1e-9, run, 1), np.where(rise > 1e-9, np.inf, 0.0))
    return bool(t.max() <= WALL)


def loop_blocks(p, r):
    """terrain.reshape's own loop order over its bounding range, keeping land blocks with a moved vertex."""
    bx0, bx1 = int(math.floor((p[0] - r) / 64)), int(math.floor((p[0] + r) / 64))
    by0, by1 = int(math.floor(-(p[1] + r) / 64)), int(math.floor(-(p[1] - r) / 64))
    out = []
    for bx in range(bx0, bx1 + 1):
        for by in range(by0, by1 + 1):
            if (bx, by) in blk:
                g = block_gate((bx, by), p, r, AMT_SIGN * 4.0)
                if g is not None:
                    out.append(((bx, by), g))
    return out


s1g = json.loads((L.OUT / "s1_gate.json").read_text(encoding="utf-8"))
refused = sorted(tuple(map(int, k.split(","))) for k, r in s1g["rows"].items() if r["land"] and r["shipped"].startswith("SKIP"))
objs = L.mesh_objects()
gfn = {}


def walkable(c, lx, lz):
    if c not in gfn:
        ml = L.walk_meshlist(L.blockmeshes(1, c[0], c[1], objs))
        gfn[c] = (ml, [L.P.build_index(bm) for _, bm in ml])
    ml, ix = gfn[c]
    g = L.P.place(ml, lx, lz, 0.0, sky=True, index=ix)
    return g[3] is not None and g[3] in L.P.WALK_OK and g[1] != "MISS"


rate = Counter()
example = None
for c in refused:
    for i in range(16):
        for j in range(16):
            if not walkable(c, 4 * i + 0.013, -(4 * j) - 0.017):
                continue
            p = (64 * c[0] + 4 * i, -(64 * c[1] + 4 * j))
            for r in (8.0, 16.0, 24.0):
                for AMT_SIGN in (1, -1):
                    seq = loop_blocks(p, r)
                    if all(g for _, g in seq):
                        rate["lawful"] += 1
                        continue
                    rate["refused"] += 1
                    k = next(n for n, (_, g) in enumerate(seq) if not g)
                    if k > 0:
                        rate["refused_partial_write"] += 1
                        if example is None and AMT_SIGN == 1:
                            example = (p, r, [cc for cc, _ in seq[:k]], seq[k][0])
print("population rate:", dict(rate))
res = {"rate": dict(rate)}
if example:
    p, r, written, failing = example
    print("example: raise +4 r", r, "at", p, "-> written first", written, "then fails at", failing)
    scratch = L.CACHE_DIR / "verify_atomic"
    if scratch.exists():
        shutil.rmtree(scratch)
    err = None
    try:
        TER.reshape(str(scratch), radius=r, at=p, amount=4.0, disc=1, game=G, skip_mirror=False)
    except ValueError as e:
        err = str(e)[:140]
    files = sorted(str(q.relative_to(scratch)) for q in scratch.rglob("*.ff9mesh"))
    print("ValueError:", err)
    print("Disc1 files left behind:", files)
    res["example"] = {"at": list(p), "radius": r, "amount": 4.0, "predicted_written": [list(c) for c in written],
                      "failing_block": list(failing), "error": err, "files_left": files}
(L.OUT / "verify_writer_atomicity.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
