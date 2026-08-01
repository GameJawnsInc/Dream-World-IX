"""SELF-TERMINATING DONOR CENSUS -- read-only, stock disc-1 (+ disc-4 as a second sample).

THE FALSIFIER for the context-first design. The design's premise: the bench island is a
CALM, SMALL, LATTICE-LAWFUL host, and the honest move is to choose a feature that a host
of that class actually carries -- rather than to reshape the host until it can absorb a
feature that stock only ever builds as the toe of a range.

The (15,14) donor is measurably NOT self-contained (lattice_swap_feasibility.py):
  S frame  0 non-grass verts               -> free
  E frame 34 verts, y 3.11..19.80          -> continues, but TAPERS to y 7.19 by 24u
  W frame 18 verts, y 4.40.. 6.81          -> continues, y 17.28 by 24-32u into (14,14)
  N frame 17 verts, y 2.73..19.80          -> continues into a y-40 range in (15,13)
So two of its four sides are amputated range flanks, and every round since the whole-mesa
carry has shipped those cuts unaccounted.

This instrument asks: does stock contain a rock feature that is SELF-TERMINATING (every
frame-touching rock vert within TAPER_TOL of its own foot altitude, i.e. THE TAPER LAW
satisfied inside one block) AND sits on ground calm enough for a flat lattice island?
"""
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\angry-williamson-08e8bb")
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X  # noqa: E402

OUT = ROOT / "studies/overworld-topography/out/self_terminating_donors.json"
GRASS = {0, 1, 2, 3, 42}
ROCK = {49}
UP = {10, 11, 12, 13}
TAPER_TOL = 2.5      # a frame vert this close to the component's foot y counts as tapered
MIN_SPAN = 8.0       # a real wall
MIN_EXT = 20.0       # plan extent


def pct(a, q):
    return float(np.percentile(np.asarray(a, float), q)) if len(a) else None


def scan(disc):
    rows = []
    for (bx, by) in X.list_blocks(disc=disc):
        try:
            bm = X.read_block(bx, by, disc=disc, part="terrain")
        except Exception:
            continue
        V = bm.chan_arrays[X.CH_POS]
        T = bm.chan_arrays[X.CH_TAN]
        fi = bm.flat_index
        nt = len(fi) // 3
        tris = [tuple(int(v) for v in fi[3 * t:3 * t + 3]) for t in range(nt)]
        tp = [X.decode_id(int(round(T[t[0]][0])))["topograph"] for t in tris]
        rock = [i for i in range(nt) if tp[i] in ROCK]
        if len(rock) < 12:
            continue
        # connected rock components by shared rounded position edge
        key = {}
        for i in rock:
            for v in tris[i]:
                key[v] = (round(float(V[v][0]), 2), round(float(V[v][1]), 2),
                          round(float(V[v][2]), 2))
        eown = defaultdict(list)
        for i in rock:
            a, b, c = tris[i]
            for e in ((a, b), (b, c), (c, a)):
                eown[tuple(sorted((key[e[0]], key[e[1]])))].append(i)
        adj = defaultdict(set)
        for e, owners in eown.items():
            for a in owners:
                for b in owners:
                    if a != b:
                        adj[a].add(b)
        seen = set()
        for s in rock:
            if s in seen:
                continue
            comp, q = [], deque([s])
            seen.add(s)
            while q:
                u = q.popleft()
                comp.append(u)
                for w in adj[u]:
                    if w not in seen:
                        seen.add(w)
                        q.append(w)
            if len(comp) < 12:
                continue
            pts = [(float(V[v][0]), float(V[v][1]), float(V[v][2]))
                   for i in comp for v in tris[i]]
            ys = [p[1] for p in pts]
            span = max(ys) - min(ys)
            ex = max(p[0] for p in pts) - min(p[0] for p in pts)
            ez = max(p[2] for p in pts) - min(p[2] for p in pts)
            if span < MIN_SPAN or max(ex, ez) < MIN_EXT:
                continue
            foot = pct(ys, 5)
            # frame-touching rock verts
            frame = [p for p in pts
                     if abs(p[0]) < 1e-3 or abs(p[0] - 64.0) < 1e-3
                     or abs(p[2]) < 1e-3 or abs(p[2] + 64.0) < 1e-3]
            frame_hi = [p[1] for p in frame if p[1] > foot + TAPER_TOL]
            # walkable top?
            hull_x = (min(p[0] for p in pts), max(p[0] for p in pts))
            hull_z = (min(p[2] for p in pts), max(p[2] for p in pts))
            top = 0
            for i in range(nt):
                if tp[i] not in UP:
                    continue
                cx = sum(float(V[v][0]) for v in tris[i]) / 3
                cz = sum(float(V[v][2]) for v in tris[i]) / 3
                cy = sum(float(V[v][1]) for v in tris[i]) / 3
                if hull_x[0] <= cx <= hull_x[1] and hull_z[0] <= cz <= hull_z[1] \
                        and cy > foot + 8.0:
                    top += 1
            # host calmness: grass ground y span in the block
            gy = [float(V[v][1]) for i in range(nt) if tp[i] in GRASS for v in tris[i]]
            rows.append({
                "disc": disc, "block": [bx, by], "tris": len(comp),
                "y_span": round(span, 2), "foot_y": round(foot, 2),
                "extent": [round(ex, 1), round(ez, 1)],
                "frame_rock_verts": len(frame),
                "frame_above_foot": len(frame_hi),
                "frame_ymax_excess": round(max(frame_hi) - foot, 2) if frame_hi else 0.0,
                "self_terminating": len(frame_hi) == 0,
                "walkable_top_tris": top,
                "block_grass_span": round(max(gy) - min(gy), 2) if gy else None,
                "block_grass_n": len(gy),
            })
    return rows


rows = scan(1) + scan(4)
st = [r for r in rows if r["self_terminating"]]
st_top = [r for r in st if r["walkable_top_tris"] >= 4]
st_top_calm = [r for r in st_top if (r["block_grass_span"] or 99) <= 6.0]
res = {
    "criteria": {"TAPER_TOL": TAPER_TOL, "MIN_SPAN": MIN_SPAN, "MIN_EXT": MIN_EXT,
                 "calm": "block grass y-span <= 6.0u"},
    "n_components": len(rows),
    "n_self_terminating": len(st),
    "n_self_terminating_with_walkable_top": len(st_top),
    "n_self_terminating_top_calm_host": len(st_top_calm),
    "frame_above_foot_distribution": {
        "share_zero": round(len(st) / len(rows), 4) if rows else None,
        "med": round(pct([r["frame_above_foot"] for r in rows], 50), 2),
        "p90": round(pct([r["frame_above_foot"] for r in rows], 90), 2),
    },
    "self_terminating_with_top": sorted(
        st_top, key=lambda r: -r["y_span"])[:20],
    "self_terminating_top_calm": sorted(
        st_top_calm, key=lambda r: -r["y_span"])[:20],
    "donor_15_14_row": [r for r in rows if r["disc"] == 1 and r["block"] == [15, 14]],
}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1)[:6000])
print("\nwrote", OUT)
