"""gui lane, prototypes for the per-mouse-move and per-frame costs on the GUI thread.

    py studies/overworld-editor/perf/gui_proto_preview.py [reps]

P3  forestedit.footprint_preview (93% of a forest ghost drag's 61-75 ms per move, gui_interact): it reduces the WHOLE
    island soup's corners (corner.max/min over every tri) on every call although SoupIndex already holds them
    (ix.lo / ix.hi), and its coast test builds a (verts x every coast point) distance matrix. The prototype uses
    ix.lo / ix.hi (the same arrays) and drops the coast points that lie farther than RIM_MARGIN outside the box of
    the verts tested (such a point is never within RIM_MARGIN of any of them, so the boolean is the same).
P4  worldview3d.ground_y (the game camera's probe: gamecam.pose calls it 4x, ~20 ms each over every packed triangle,
    so a game-camera orbit frame costs 100-130 ms): a per-part 16u plan grid of triangle ids; the query takes the one
    grid cell's ids, ascending, and runs the SAME arithmetic on them (a tri whose plan box holds the point always
    overlaps the point's cell, so the candidate set is the same).
Identity: P3's dict == the shipped dict at every probe point (a lattice over the island, lawful and refused, coast
and inland); P4's height == the shipped height (float ==) at every probe point, None included.
The soup is the forest card's own read (ForestTool._read_soup's call: read_deployed_blocks WHOLE_MAP of the draft
under out/perf/gui/drafts); the Packed is load_scene of the game's stack (read only).
Evidence: out/perf/gui/gui_proto_preview.json.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

import numpy as np                                                    # noqa: E402

DRAFTS = C.OUT / "drafts"
FOREST_SPOT, FOREST_DONOR = (1400.0, -460.0), (13, 15)


def footprint_preview_p3(ix, rim_xz):
    """forestedit.footprint_preview with ix.lo/ix.hi and a box-culled coast; every other line as shipped."""
    from ff9mapkit.world import interior as IN
    from ff9mapkit.world.forestedit import _near, _pip
    poly = np.asarray(rim_xz, dtype=np.float64)
    if not len(ix.tris):
        return {"ok": False, "seen": None, "where": [], "why": "no island here"}
    lo, hi = poly.min(axis=0) - IN.SCAN_BAND, poly.max(axis=0) + IN.SCAN_BAND
    cand = np.flatnonzero(((ix.hi >= lo) & (ix.lo <= hi)).all(axis=1))          # P3: ix.hi/ix.lo ARE corner.max/min
    hit = _pip(ix.cent[cand], poly) | _near(ix.cent[cand], poly, IN.SCAN_BAND)
    rest = ~hit
    if rest.any():
        cor = ix.corner[cand[rest]]
        ch = (_pip(cor, poly) | _near(cor, poly, IN.SCAN_BAND)).any(axis=1)
        hit[np.flatnonzero(rest)[ch]] = True
    idx = cand[hit]
    bad = [i for i in idx if not ix.grass[i]]
    where, why = [tuple(ix.cent[i]) for i in bad[:12]], (ix.what[bad[0]] if bad else "")
    if not bad and len(ix.coast) and len(idx):
        v = ix.pos[ix.tris[idx]][..., [0, 2]].reshape(-1, 2)
        m = IN.RIM_MARGIN
        vlo, vhi = v.min(axis=0) - m, v.max(axis=0) + m                       # P3: a coast point outside this box is
        keep = ((ix.coast >= vlo) & (ix.coast <= vhi)).all(axis=1)             # >= m from every v on one axis
        coast = ix.coast[keep]
        if len(coast):
            d2 = ((v[:, None, :] - coast[None, :, :]) ** 2).sum(axis=-1).min(axis=1)
            near_coast = d2 < IN.RIM_MARGIN ** 2
        else:
            near_coast = np.zeros(len(v), dtype=bool)
        if near_coast.any():
            where, why = [tuple(p) for p in v[near_coast][:12]], "the coast rim"
    if where:
        return {"ok": False, "seen": None, "where": where, "why": why}
    seen = int(len(idx))
    return {"ok": seen >= 40, "seen": seen, "where": [] if seen >= 40 else [tuple(poly.mean(axis=0))],
            "why": "" if seen >= 40 else "too little plain grass under it"}


class GroundGrid:
    """P4: per part, {(i, j): ascending tri ids whose plan box overlaps 16u cell (i, j)}."""

    CELL = 16.0

    def __init__(self, packed):
        self.packed = packed
        self.grid = {}
        for part in packed.arrays:
            v0, e1, e2, n = packed.pick_arrays(part)
            lo = np.minimum(v0, np.minimum(v0 + e1, v0 + e2))
            hi = np.maximum(v0, np.maximum(v0 + e1, v0 + e2))
            up = np.flatnonzero(n[:, 1] > 0.0)
            i0, i1 = np.floor(lo[up, 0] / self.CELL).astype(np.int64), np.floor(hi[up, 0] / self.CELL).astype(np.int64)
            j0, j1 = np.floor(lo[up, 2] / self.CELL).astype(np.int64), np.floor(hi[up, 2] / self.CELL).astype(np.int64)
            cells = {}
            for t, a, b, c, d in zip(up.tolist(), i0.tolist(), i1.tolist(), j0.tolist(), j1.tolist()):
                for i in range(a, b + 1):
                    for j in range(c, d + 1):
                        cells.setdefault((i, j), []).append(t)
            self.grid[part] = {k: np.asarray(v, dtype=np.int64) for k, v in cells.items()}

    def ground_y(self, x, z):
        """worldview3d.ground_y on the cell's candidates: the same tests, the same arithmetic, the same max."""
        best = None
        key = (math.floor(x / self.CELL), math.floor(z / self.CELL))
        for part in self.packed.arrays:
            cand = self.grid[part].get(key)
            if cand is None:
                continue
            v0, e1, e2, n = self.packed.pick_arrays(part)
            v0c, e1c, e2c, nc = v0[cand], e1[cand], e2[cand], n[cand]
            ok = nc[:, 1] > 0.0
            lo = np.minimum(v0c, np.minimum(v0c + e1c, v0c + e2c))
            hi = np.maximum(v0c, np.maximum(v0c + e1c, v0c + e2c))
            ok &= (lo[:, 0] <= x) & (x <= hi[:, 0]) & (lo[:, 2] <= z) & (z <= hi[:, 2])
            idx = np.flatnonzero(ok)
            if not len(idx):
                continue
            a, b, c = v0c[idx], v0c[idx] + e1c[idx], v0c[idx] + e2c[idx]
            d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
            good = np.abs(d) > 1e-12
            d = np.where(good, d, 1.0)
            w0 = ((b[:, 2] - c[:, 2]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (z - c[:, 2])) / d
            w1 = ((c[:, 2] - a[:, 2]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (z - c[:, 2])) / d
            w2 = 1.0 - w0 - w1
            inside = good & (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
            if inside.any():
                y = float((w0 * a[:, 1] + w1 * b[:, 1] + w2 * c[:, 1])[inside].max())
                best = y if best is None else max(best, y)
        return best


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    from ff9mapkit.world import forestedit as FE
    from ff9mapkit.world import interior as IN
    from ff9mapkit.world import draft as D
    from ff9mapkit.workspace import worldforest as WF
    out = {}
    # ---------------------------------------------------------------- P3
    draft = D.draft_path(C.SOURCE, root=DRAFTS)
    assert D.read_meta(draft) is not None, "run gui_firstshow.py first (it makes the draft)"
    near, reach = WF.WHOLE_MAP
    t = time.perf_counter()
    ix = FE.SoupIndex(IN.soup_from_blocks(IN.read_deployed_blocks(str(draft), near=near, reach=reach, game=C.GAME)))
    out["soup_read_s"] = round(time.perf_counter() - t, 3)
    out["soup"] = {"tris": int(len(ix.tris)), "coast_pts": int(len(ix.coast)), "blocks": len(ix.blocks)}
    ol = FE.outline(FOREST_DONOR, game=C.GAME)
    # probe points: a lattice round the forest spot and over every island block's centre (lawful + refused)
    pts = [(FOREST_SPOT[0] + dx, FOREST_SPOT[1] + dz) for dx in range(-40, 41, 8) for dz in range(-40, 41, 8)]
    pts += [((bx + 0.5) * 64.0, -(by + 0.5) * 64.0) for bx, by in sorted(ix.blocks)]
    rims = []
    for x, z in pts:
        _t, rim0 = FE.placed(ol, (x, z), ground_y=0.0)
        rims.append(rim0[:, [0, 2]])
    same, kinds = True, {}
    for rim in rims:
        a, b = FE.footprint_preview(ix, rim), footprint_preview_p3(ix, rim)
        same &= (a == b)
        kinds[a["why"] or ("ok" if a["ok"] else "?")] = kinds.get(a["why"] or ("ok" if a["ok"] else "?"), 0) + 1
    out["P3_identical_all_points"] = bool(same)
    out["P3_points"], out["P3_verdict_kinds"] = len(rims), kinds
    t0s, t1s = [], []
    for _ in range(reps):
        t = time.perf_counter()
        for rim in rims:
            FE.footprint_preview(ix, rim)
        t0s.append((time.perf_counter() - t) / len(rims))
        t = time.perf_counter()
        for rim in rims:
            footprint_preview_p3(ix, rim)
        t1s.append((time.perf_counter() - t) / len(rims))
    out["P3_per_call_shipped"], out["P3_per_call_proto"] = C.stats(t0s), C.stats(t1s)
    print("P3", out["soup"], "identical", same, kinds, "shipped", round(min(t0s) * 1e3, 2), "ms proto",
          round(min(t1s) * 1e3, 2), "ms")

    # ---------------------------------------------------------------- P4
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    site = R.RenderSite(cells=cells, disc=1, game=C.GAME, stack=R.game_stack(C.GAME))
    packed, _tex = V.load_scene(site)
    t = time.perf_counter()
    gg = GroundGrid(packed)
    out["P4_grid_build_s"] = round(time.perf_counter() - t, 3)
    rng = np.random.default_rng(9)
    probe = [(float(x), float(z)) for x, z in zip(rng.uniform(-150, 1700, 1500), rng.uniform(-1300, 20, 1500))]
    probe += [(FOREST_SPOT[0] + 0.37 * k, FOREST_SPOT[1] - 0.29 * k) for k in range(200)]
    probe += [(16.0 * i, -16.0 * j) for i in range(0, 96, 7) for j in range(0, 80, 7)]       # on the grid lines
    a = [V.ground_y(packed, x, z) for x, z in probe]
    b = [gg.ground_y(x, z) for x, z in probe]
    out["P4_identical_all_points"] = a == b
    out["P4_points"], out["P4_points_with_ground"] = len(probe), sum(v is not None for v in a)
    sub = probe[:200]
    t0s, t1s = [], []
    for _ in range(reps):
        t = time.perf_counter()
        for x, z in sub:
            V.ground_y(packed, x, z)
        t0s.append((time.perf_counter() - t) / len(sub))
        t = time.perf_counter()
        for x, z in sub:
            gg.ground_y(x, z)
        t1s.append((time.perf_counter() - t) / len(sub))
    out["P4_per_call_shipped"], out["P4_per_call_proto"] = C.stats(t0s), C.stats(t1s)
    # the game camera's pose (4 probes) both ways, as GameCamera.view() calls it
    from ff9mapkit.world import gamecam as G
    settings = G.Settings.from_game(C.GAME)
    table = G.transport_table(C.GAME)
    poses = {}
    for name, fn in (("shipped", lambda gx, gz: V.ground_y(packed, gx, gz)), ("proto", gg.ground_y)):
        ts, views = [], []
        for _ in range(reps):
            for k in range(6):
                cam = V.GameCamera((FOREST_SPOT[0], 3.2, FOREST_SPOT[1]), 20.0 * k, settings=settings, ground=fn,
                                   table=table)
                t = time.perf_counter()
                views.append(cam.view())
                ts.append(time.perf_counter() - t)
        poses[name] = (C.stats(ts), views)
    out["P4_pose_shipped"], out["P4_pose_proto"] = poses["shipped"][0], poses["proto"][0]
    out["P4_pose_identical"] = poses["shipped"][1] == poses["proto"][1]
    print("P4 identical", out["P4_identical_all_points"], "pose identical", out["P4_pose_identical"],
          "ground_y shipped", round(min(t0s) * 1e3, 2), "ms proto", round(min(t1s) * 1e3, 3), "ms; pose",
          out["P4_pose_shipped"]["min_s"], "->", out["P4_pose_proto"]["min_s"], "grid build", out["P4_grid_build_s"])
    C.dump("gui_proto_preview.json", out)


if __name__ == "__main__":
    main()
