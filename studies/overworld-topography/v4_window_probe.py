"""V4 WINDOW PROBE -- look closely at the census's donor candidates before choosing.

For each candidate window: a band-colored plan render (sea gap / lowland / mid / high /
escarpment / other-blocked), walkable-shelf contiguity stats (largest connected mid/high
patch in plan area), frame-crossing land runs per edge (where land crosses the window
frame + the y-span there -- the cut-relief question), and the y-histogram of walkable area.

Run from the repo root:  py studies/overworld-topography/v4_window_probe.py
Writes out/v4_win_<name>.png per window.
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                   # noqa: E402

FOOT = set(range(0, 8)) | {10, 11, 12, 13} | set(range(16, 24)) | {27, 28, 30, 31} \
     | set(range(32, 39)) | {41, 42, 45, 46, 52}
LOW_HI, MID_HI = 9.5, 18.0
SCALE = 6                                                  # px per world unit
out_dir = Path(__file__).parent / "out"

WINDOWS = {
    "terrace_2x2": [(5, 15), (6, 15), (5, 16), (6, 16)],
    "terrace_3x2": [(5, 15), (6, 15), (7, 15), (5, 16), (6, 16), (7, 16)],
}
RIVER_PARTS = ("river", "falls", "riverjoint", "beach1")
RIVER_COL = {"river": (70, 140, 235), "falls": (160, 210, 255),
             "riverjoint": (110, 170, 245), "beach1": (235, 225, 150)}

COL = {"low": (110, 200, 90), "mid": (235, 200, 80), "high": (250, 120, 60),
       "esc": (120, 100, 110), "blocked": (80, 80, 95), "downface": (50, 50, 60)}


def classify(topo, ny, cy):
    if topo == 49 or topo == 58:
        return "esc"
    if ny <= 0.1:
        return "downface"
    if topo not in FOOT:
        return "blocked"
    if cy <= LOW_HI:
        return "low"
    if cy <= MID_HI:
        return "mid"
    return "high"


for name, blocks in WINDOWS.items():
    xs = [b[0] for b in blocks]
    ys = [b[1] for b in blocks]
    x0, y0 = min(xs), min(ys)
    W = (max(xs) - x0 + 1) * 64
    H = (max(ys) - y0 + 1) * 64
    img = Image.new("RGB", (W * SCALE, H * SCALE), (25, 40, 70))
    dr = ImageDraw.Draw(img)
    stats = defaultdict(float)
    cells = defaultdict(set)                                # 2u cell -> classes (contiguity)
    frame_runs = defaultdict(list)
    ywalk = []
    overlays = []

    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1)
        except Exception:
            continue
        # river/falls/beach overlays (drawn after the terrain pass, before save)
        for part in RIVER_PARTS:
            try:
                pm = X.read_block(bx, by, disc=1, part=part)
            except Exception:
                continue
            PV = np.asarray(pm.verts, dtype=np.float64)
            pidx = np.asarray(pm.flat_index, dtype=np.int64).reshape(-1, 3)
            oox, ooz = (bx - x0) * 64.0, -(by - y0) * 64.0
            for i in pidx:
                pts = [((PV[j][0] + oox) * SCALE, (-(PV[j][2] + ooz)) * SCALE) for j in i]
                overlays.append((pts, RIVER_COL[part]))
        V = np.asarray(bm.verts, dtype=np.float64)
        T = np.asarray(bm.tangents, dtype=np.float64)
        idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
        ox, oz = (bx - x0) * 64.0, -(by - y0) * 64.0        # window-local origin
        for t in range(len(idx)):
            i = idx[t]
            a, b, c = V[i[0]], V[i[1]], V[i[2]]
            n = np.cross(b - a, c - a)
            ln = float(np.linalg.norm(n)) or 1.0
            ny = n[1] / ln
            cy = (a[1] + b[1] + c[1]) / 3.0
            topo = X.decode_id(int(round(T[i[0]][0])))["topograph"]
            cls = classify(topo, ny, cy)
            pts = [((p[0] + ox) * SCALE, (-(p[2] + oz)) * SCALE) for p in (a, b, c)]
            dr.polygon(pts, fill=COL[cls])
            stats[cls + "_a"] += 0.5 * abs(n[1])
            if cls in ("mid", "high"):
                cx = (a[0] + b[0] + c[0]) / 3.0 + ox
                cz = -((a[2] + b[2] + c[2]) / 3.0 + oz)
                cells[cls].add((int(cx // 2), int(cz // 2)))
            if cls in ("low", "mid", "high"):
                ywalk.append((cy, 0.5 * abs(n[1])))
            # window-frame land crossings (window-local frame planes)
            for p in (a, b, c):
                wx, wz = p[0] + ox, p[2] + oz
                if p[1] <= 0.6:
                    continue
                for e, (axis, plane, coord) in {
                        "W": (0, 0.0, wz), "E": (0, W * 1.0, wz),
                        "N": (2, 0.0, wx), "S": (2, -H * 1.0, wx)}.items():
                    v = wx if axis == 0 else wz
                    if abs(v - plane) < 0.05:
                        frame_runs[e].append((coord, p[1]))

    # largest connected mid/high patch (2u cells, 4-neighbour)
    def biggest(cellset):
        best, seen = 0, set()
        for s in cellset:
            if s in seen:
                continue
            comp, st = {s}, [s]
            while st:
                q = st.pop()
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nb = (q[0] + d[0], q[1] + d[1])
                    if nb in cellset and nb not in comp:
                        comp.add(nb)
                        st.append(nb)
            seen |= comp
            best = max(best, len(comp))
        return best * 4                                     # ~u^2

    print(f"\n== {name}  blocks {blocks}")
    print("   " + "  ".join(f"{k[:-2]} {stats[k]:6.0f}" for k in
                            ("low_a", "mid_a", "high_a", "esc_a", "blocked_a")))
    print(f"   largest contiguous shelf: mid ~{biggest(cells['mid'])}u^2, "
          f"high ~{biggest(cells['high'])}u^2")
    hy = np.array([y for y, _ in ywalk])
    hw = np.array([w for _, w in ywalk])
    if len(hy):
        qs = [1, 5, 12, 30]
        hist = [(f"y{lo}-{hi}", float(hw[(hy >= lo) & (hy < hi)].sum()))
                for lo, hi in zip([0] + qs, qs + [60])]
        print("   walkable y-hist: " + "  ".join(f"{k}:{v:.0f}" for k, v in hist if v > 0))
    for e in "WENS":
        runs = frame_runs.get(e, [])
        if not runs:
            continue
        # contiguous crossing runs (gap > 6u splits)
        pts = sorted(runs)
        spans, cur = [], [pts[0]]
        for q in pts[1:]:
            if q[0] - cur[-1][0] > 6.0:
                spans.append(cur)
                cur = []
            cur.append(q)
        spans.append(cur)
        for sp in spans:
            print(f"   LAND crossing frame {e}: {sp[0][0]:.0f}..{sp[-1][0]:.0f} "
                  f"(width {sp[-1][0] - sp[0][0]:.0f}u, ymax {max(y for _, y in sp):.1f})")
    if not frame_runs:
        print("   frame: CLOSED (no land vert on any window frame)")
    for pts, colr in overlays:
        dr.polygon(pts, fill=colr)
    p = out_dir / f"v4_win_{name}.png"
    img.save(p)
    print(f"   -> {p.name}")
