"""THE ROCK-WALL MASSING DECODE -- the silhouette study the refutation demanded.

The terrace-wall prediction test closed 2026-07-30 with the tile-language discriminant
REFUTED: correct tiles on invented massing still failed at form (studies/path-d-new-world/
TERRACE-WALL-PREDICTION.md). The owner's specific verdicts name geometry, not texture:
"sharp edges at the bottom" (a lattice-polyline foot on smooth ground), "grass-cliff tiling
mid-wall" (ledge-textured tiles on an unledged cone). This study decodes the MASSING of the
same stock plateau walls the tile decodes used -- the component extraction is verbatim from
rock_wall_instances.py, so the three studies share one instrument.

Measured, per wall component / per quad instance / per welded vertical pair:

  A. DIP per course position (bottom / middle / top third of the local wall) -- talus check:
     do real feet flare shallower than the body?
  B. THE JOG: dihedral angle + horizontal step depth across each welded vertical pair --
     are stacked courses coplanar sheets or in/out-stepped ledges?
  C. LEDGE SHELVES: near-horizontal rock tris embedded in the wall (slope < 25 deg,
     mid-height) -- count, depth (horizontal extent), and which course boundary they ride.
  D. THE FOOT LINE: the wall|walkable-ground boundary -- consecutive-edge turn-angle
     histogram, edge lengths, and 4u-lattice adherence (the SPUR's "real feet follow the
     lattice" was proven on the coastal massif; is it true of interior walls?).
  E. THE CREST LINE: same measures at the top + height jitter along the run.
  F. SILHOUETTE PROFILES: per column (a chain of vertically-welded instances), the
     (outward-offset, y) polyline of its quad corners, overlaid per component and rendered
     -- the coursed silhouette made visible for the eye.

Output: out/rock_wall_massing.json + profile PNGs + a printed summary ending in the
question the study exists to answer: is this massing lawfully COMPRESSIBLE (a generator's
parameter set) or mural-like (the Rung-F carry conclusion extends to walls)? Read-only.
Regenerate: py -X utf8 rock_wall_massing.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

PLATEAU = {10, 11, 12}
TILE_U, TILE_V = 0.0625, 0.03125
CELL = 4.0
OUT = Path(__file__).with_name("out") / "rock_wall_massing.json"
RENDERS = Path(__file__).with_name("out") / "massing"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731

dips = {"bottom": [], "middle": [], "top": []}
jogs = []                                                   # (dihedral_deg, step_depth_u)
shelves = []                                                # (depth_u, rel_height)
foot_turns = []
foot_edge_lens = []
foot_lattice_hits = 0
foot_edges_n = 0
crest_turns = []
crest_jitter = []
profiles_all = []                                           # per component: list of column profiles
comp_meta = []

blocks = X.list_blocks(disc=1)
for (bx, by) in blocks:
    try:
        bm = X.read_block(bx, by, disc=1)
    except Exception:                                       # noqa: BLE001
        continue
    V, U, T = bm.verts, bm.uvs, bm.tangents
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]
    if not any(t in PLATEAU for t in topo):
        continue
    ox, oz = 64.0 * bx, -64.0 * by

    edge_tris = defaultdict(list)
    for t, idx in enumerate(tri_idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((kk(V[idx[a]]), kk(V[idx[b]]))))].append(t)

    crest49 = set()
    for e, ts in edge_tris.items():
        if len(ts) == 2:
            pair = {topo[ts[0]], topo[ts[1]]}
            if 49 in pair and pair & PLATEAU:
                crest49.add(ts[0] if topo[ts[0]] == 49 else ts[1])
    adj49 = defaultdict(set)
    for e, ts in edge_tris.items():
        r = [t for t in ts if topo[t] == 49]
        for i in range(len(r)):
            for j in range(i + 1, len(r)):
                adj49[r[i]].add(r[j])
                adj49[r[j]].add(r[i])
    comp_of = {}
    seen = set()
    for s in crest49:
        if s in seen:
            continue
        comp = {s}
        st = [s]
        while st:
            t = st.pop()
            for t2 in adj49[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        for t in comp:
            comp_of[t] = s
    wall_tris = set(comp_of)
    if not wall_tris:
        continue

    # ---- A + C: per-tri dip by relative height; embedded shelves ----------------------------
    comp_tris = defaultdict(list)
    for t in wall_tris:
        comp_tris[comp_of[t]].append(t)
    for root, ts in comp_tris.items():
        ys = [V[i][1] for t in ts for i in tri_idx[t]]
        y0, y1 = min(ys), max(ys)
        if y1 - y0 < 6.0 or len(ts) < 12:
            continue                                        # too small to have a silhouette
        for t in ts:
            a, b, c = (np.array(V[i]) for i in tri_idx[t])
            fn = np.cross(b - a, c - a)
            L = float(np.linalg.norm(fn))
            if L < 1e-6:
                continue
            dip = math.degrees(math.acos(max(-1.0, min(1.0, abs(fn[1]) / L))))
            cy = float((a[1] + b[1] + c[1]) / 3)
            rel = (cy - y0) / (y1 - y0)
            band = "bottom" if rel < 1 / 3 else ("middle" if rel < 2 / 3 else "top")
            dips[band].append(dip)
            if dip < 25.0 and 0.15 < rel < 0.9:             # an embedded near-flat ledge
                span = max(float(np.linalg.norm((b - a)[[0, 2]])),
                           float(np.linalg.norm((c - a)[[0, 2]])),
                           float(np.linalg.norm((c - b)[[0, 2]])))
                shelves.append((round(span, 2), round(rel, 2)))

    # ---- quads (instances) + welded vertical pairs, verbatim mechanics ----------------------
    parent = {t: t for t in wall_tris}

    def find(t):
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    def bbox_of(ts):
        us = [U[i][0] for t in ts for i in tri_idx[t]]
        vs = [U[i][1] for t in ts for i in tri_idx[t]]
        return min(us), min(vs), max(us), max(vs)

    members = {t: {t} for t in wall_tris}
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in wall_tris]
        if len(w) != 2:
            continue
        t1, t2 = w
        uv1 = {kk(V[i]): tuple(np.round(U[i], 5)) for i in tri_idx[t1]}
        uv2 = {kk(V[i]): tuple(np.round(U[i], 5)) for i in tri_idx[t2]}
        if not all(uv1.get(p) == uv2.get(p) for p in e):
            continue
        r1, r2 = find(t1), find(t2)
        if r1 == r2:
            continue
        u0, v0, u1, v1 = bbox_of(members[r1] | members[r2])
        if (u1 - u0) > TILE_U + 1e-4 or (v1 - v0) > TILE_V + 1e-4:
            continue
        parent[r2] = r1
        members[r1] |= members[r2]
        del members[r2]

    inst_of_tri = {}
    inst_data = {}
    for r, ts in members.items():
        pts = np.array([[V[i][0], V[i][1], V[i][2]] for t in ts for i in tri_idx[t]])
        n_sum = np.zeros(3)
        for t in ts:
            a, b, c = (np.array(V[i]) for i in tri_idx[t])
            n_sum += np.cross(b - a, c - a)
        inst_data[r] = dict(cen=pts.mean(axis=0), n=n_sum, comp=comp_of[next(iter(ts))],
                            ymin=float(pts[:, 1].min()), ymax=float(pts[:, 1].max()),
                            pts=pts)
        for t in ts:
            inst_of_tri[t] = r

    v_adj = defaultdict(set)
    seen_p = set()
    for e, ts in edge_tris.items():
        w = sorted({inst_of_tri[t] for t in ts if t in inst_of_tri})
        if len(w) != 2 or tuple(w) in seen_p:
            continue
        seen_p.add(tuple(w))
        A, B = inst_data[w[0]], inst_data[w[1]]
        d = B["cen"] - A["cen"]
        if abs(d[1]) > math.hypot(d[0], d[2]):
            lo, hi = (w[0], w[1]) if A["cen"][1] <= B["cen"][1] else (w[1], w[0])
            v_adj[lo].add(hi)
            # ---- B: the jog across this welded pair --------------------------------------
            nA, nB = inst_data[lo]["n"], inst_data[hi]["n"]
            LA, LB = np.linalg.norm(nA), np.linalg.norm(nB)
            if LA > 1e-6 and LB > 1e-6:
                dihedral = math.degrees(math.acos(max(-1.0, min(1.0,
                                                                float(nA @ nB) / (LA * LB)))))
                # step depth: horizontal offset between the two faces' centroids projected on
                # the mean face normal (in/out ledge depth)
                nm = (nA / LA + nB / LB)
                nm[1] = 0.0
                Lm = np.linalg.norm(nm)
                step = 0.0
                if Lm > 1e-6:
                    step = abs(float((inst_data[hi]["cen"] - inst_data[lo]["cen"]) @ (nm / Lm)))
                jogs.append((round(dihedral, 1), round(step, 2)))

    # ---- D + E: foot and crest boundary lines -----------------------------------------------
    for kind, other_ok, sink_turn in (("foot", lambda tt: tt not in (49,) and tt not in PLATEAU,
                                       foot_turns),
                                      ("crest", lambda tt: tt in PLATEAU, crest_turns)):
        chains_e = []
        for e, ts in edge_tris.items():
            w = [t for t in ts if t in wall_tris]
            o = [t for t in ts if t not in wall_tris and other_ok(topo[t])]
            if len(w) >= 1 and len(o) >= 1:
                chains_e.append(e)
        adj_p = defaultdict(list)
        for a, b in chains_e:
            adj_p[a].append(b)
            adj_p[b].append(a)
        used = set()
        for e in chains_e:
            if e in used:
                continue
            # walk a run from an endpoint (or anywhere on a loop)
            start = e[0]
            prev = None
            run = [start]
            while True:
                nxts = [q for q in adj_p[run[-1]] if q != prev]
                if not nxts:
                    break
                prev = run[-1]
                run.append(nxts[0])
                if run[-1] == start or len(run) > 4000:
                    break
            if len(run) < 4:
                continue
            for i in range(len(run) - 1):
                used.add(tuple(sorted((run[i], run[i + 1]))))
            for i in range(1, len(run) - 1):
                v1 = np.array(run[i]) - np.array(run[i - 1])
                v2 = np.array(run[i + 1]) - np.array(run[i])
                v1[1] = v2[1] = 0.0
                L1, L2 = np.linalg.norm(v1), np.linalg.norm(v2)
                if L1 < 1e-6 or L2 < 1e-6:
                    continue
                ang = math.degrees(math.acos(max(-1.0, min(1.0, float(v1 @ v2) / (L1 * L2)))))
                sink_turn.append(round(ang, 1))
            if kind == "foot":
                for i in range(len(run) - 1):
                    a, b = run[i], run[i + 1]
                    foot_edge_lens.append(round(math.dist((a[0], a[2]), (b[0], b[2])), 2))
                    foot_edges_n += 1
                    wx, wz = a[0] + ox, a[2] + oz
                    on_lat = (abs(wx / CELL - round(wx / CELL)) < 0.05 or
                              abs(wz / CELL - round(wz / CELL)) < 0.05)
                    foot_lattice_hits += 1 if on_lat else 0
            else:
                ys_r = [p[1] for p in run]
                if len(ys_r) >= 6:
                    crest_jitter.append(round(float(np.std(ys_r)), 2))

    # ---- F: silhouette profiles (per column = chain of welded instances) --------------------
    roots_here = [r for r in inst_data if inst_data[r]["ymax"] - inst_data[r]["ymin"] > 1.0]
    has_below = {hi for lo in v_adj for hi in v_adj[lo]}
    col_profiles = []
    for r in roots_here:
        if r in has_below:
            continue
        chain = [r]
        while chain[-1] in v_adj and v_adj[chain[-1]]:
            chain.append(sorted(v_adj[chain[-1]],
                                key=lambda q: inst_data[q]["cen"][1])[0])
            if len(chain) > 12:
                break
        if len(chain) < 3:
            continue
        base = inst_data[chain[0]]
        nm = base["n"].copy()
        nm[1] = 0.0
        L = np.linalg.norm(nm)
        if L < 1e-6:
            continue
        nm /= L
        prof = []
        for q in chain:
            d = inst_data[q]
            for (py, po) in ((d["ymin"], None), (d["ymax"], None)):
                sel = d["pts"][np.abs(d["pts"][:, 1] - py) < 0.4]
                if not len(sel):
                    continue
                off = float(((sel[:, [0, 2]] - base["cen"][[0, 2]]) @ nm[[0, 2]]).mean())
                prof.append((round(off, 2), round(py - base["ymin"], 2)))
        prof = sorted(set(prof), key=lambda p: p[1])
        if len(prof) >= 4:
            col_profiles.append(prof)
    if col_profiles:
        profiles_all.append(dict(blk=[bx, by], profiles=col_profiles))
        comp_meta.append(dict(blk=[bx, by], n_cols=len(col_profiles)))

# ---- summaries ------------------------------------------------------------------------------
def pct(a, q):
    return round(float(np.percentile(a, q)), 1) if a else None

print("A. DIP by course position (deg):")
for band in ("bottom", "middle", "top"):
    d = dips[band]
    print(f"   {band:6s}: n={len(d)}  p25={pct(d, 25)}  med={pct(d, 50)}  p75={pct(d, 75)}  "
          f"p10={pct(d, 10)}")
J = np.array(jogs) if jogs else np.zeros((0, 2))
print(f"\nB. THE JOG over {len(jogs)} welded vertical pairs: dihedral med "
      f"{pct(J[:, 0].tolist(), 50)} deg (p75 {pct(J[:, 0].tolist(), 75)}, p90 "
      f"{pct(J[:, 0].tolist(), 90)}); step depth med {pct(J[:, 1].tolist(), 50)}u "
      f"(p75 {pct(J[:, 1].tolist(), 75)}, p90 {pct(J[:, 1].tolist(), 90)})")
print(f"   coplanar (<10 deg) {float(np.mean(J[:, 0] < 10)) if len(J) else 0:.0%}, "
      f"jogged (>=25 deg) {float(np.mean(J[:, 0] >= 25)) if len(J) else 0:.0%}")
print(f"\nC. LEDGE SHELVES embedded mid-wall: n={len(shelves)}; depth med "
      f"{pct([s[0] for s in shelves], 50)}u p90 {pct([s[0] for s in shelves], 90)}u")
print(f"\nD. THE FOOT LINE: {foot_edges_n} edges; turn angle med {pct(foot_turns, 50)} deg "
      f"(p90 {pct(foot_turns, 90)}); edge len med {pct(foot_edge_lens, 50)}u; "
      f"lattice-aligned verts {foot_lattice_hits}/{foot_edges_n} "
      f"({foot_lattice_hits / max(1, foot_edges_n):.0%})")
print(f"   right-angle turns (80-100 deg): "
      f"{sum(1 for a in foot_turns if 80 <= a <= 100) / max(1, len(foot_turns)):.0%} -- the "
      f"'lattice jag' T1 shipped; straight-ish (<20 deg): "
      f"{sum(1 for a in foot_turns if a < 20) / max(1, len(foot_turns)):.0%}")
print(f"\nE. THE CREST LINE: turn med {pct(crest_turns, 50)} deg (p90 {pct(crest_turns, 90)}); "
      f"height jitter per run med {pct(crest_jitter, 50)}u")

# ---- profile renders ------------------------------------------------------------------------
RENDERS.mkdir(parents=True, exist_ok=True)
big = sorted(profiles_all, key=lambda c: -len(c["profiles"]))[:6]
for ci, comp in enumerate(big):
    Wp, Hp = 700, 520
    img = Image.new("RGB", (Wp, Hp), (24, 26, 30))
    dr = ImageDraw.Draw(img)
    SC = 14.0
    for prof in comp["profiles"]:
        pts = [(60 + p[0] * SC, Hp - 40 - p[1] * SC) for p in prof]
        dr.line(pts, fill=(120, 200, 140), width=1)
        for q in pts:
            dr.ellipse([q[0] - 1.5, q[1] - 1.5, q[0] + 1.5, q[1] + 1.5], fill=(230, 230, 120))
    dr.text((10, 8), f"block {comp['blk']} -- {len(comp['profiles'])} column profiles "
                     f"(offset u -> , height u ^)", fill=(220, 220, 220))
    img.save(RENDERS / f"profiles_{comp['blk'][0]}_{comp['blk'][1]}.png")
print(f"\nprofile renders ({len(big)} components) -> {RENDERS}")

OUT.write_text(json.dumps(dict(
    dips={k: v for k, v in dips.items()}, jogs=jogs, shelves=shelves,
    foot=dict(turns=foot_turns, edge_lens=foot_edge_lens,
              lattice=[foot_lattice_hits, foot_edges_n]),
    crest=dict(turns=crest_turns, jitter=crest_jitter),
    profiles=profiles_all), indent=0))
print(f"artifacts -> {OUT}")
print("\nTHE QUESTION THIS STUDY EXISTS TO ANSWER (judge from the numbers + the profile "
      "renders): is the massing a small lawful parameter set (a generator is plausible), or "
      "is the silhouette itself mural-like (the Rung-F conclusion extends: CARRY the mesh)?")
