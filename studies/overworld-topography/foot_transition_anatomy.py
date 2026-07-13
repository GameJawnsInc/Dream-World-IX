"""FOOT-TRANSITION ANATOMY -- how the REAL grass->mountain transition tiles are laid.

The synth massif's window mechanics are in-game approved (cuts clean, density right);
the remaining verdict is the TRANSITION BAND: the rock quads touching grass still read
stretched/misplaced. This study measures the real construction on all three sheet-class
mountains -- Uaho (0,0), the Daguerreo horseshoe (5-6,15-16), and the crag island
(9-10,5-7) -- per unknown:

  A. WHICH tiles do boundary-touching rock quads wear (col,row histogram vs mid-face)?
  B. V-PINNING -- is the boundary edge pinned to a specific tile-v (the painted grass
     fringe at the tile bottom sitting exactly ON the boundary), or free?
  C. ORIENTATION -- does the window u-axis run ALONG the boundary (chained), and which
     way does the tile's v point (up-slope)?
  D. DENSITY at the boundary (du/dt along, dv/dperp across) vs the mid-face values.
  E. DEPTH -- how far up the transition vocabulary reaches (1 course? more?).
  F. THE GRASS SIDE -- do adjacent grass tris use special tiles vs the plain mains?

Plus a labeled ATLAS CONTACT PRINT (rows 6-11 x cols 4-10) to SEE which tiles carry
transition art and where their grass edge sits. Artifacts -> out/foot_transition.json +
out/atlas_contact.png. Run from the repo root.
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config                                # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402

TILE_U, TILE_V = 0.0625, 0.03125
GRASS = {0, 1, 2, 3, 42}
SPECIMENS = {
    "uaho": [(0, 0)],
    "daguerreo": [(5, 15), (6, 15), (5, 16), (6, 16)],
    "crag": [(9, 5), (10, 5), (9, 6), (10, 6), (9, 7), (10, 7)],
}
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

stage1 = json.loads((OUTD / "daguerreo_massif.json").read_text())
pu, pv = stage1["phase"]

report = {}
for name, blocks in SPECIMENS.items():
    tris = []
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except Exception:
            continue
        idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
        for i in idx:
            tris.append(dict(
                w=[(bm.verts[j][0] + 64.0 * bx, bm.verts[j][1],
                    bm.verts[j][2] - 64.0 * by) for j in i],
                uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in i],
                topo=X.decode_id(int(round(bm.tangents[i[0]][0])))["topograph"]))
    edge_tris = defaultdict(list)
    for ti, t in enumerate(tris):
        ps = [kk(v) for v in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((ps[a], ps[b])))].append(ti)
    rock = {ti for ti, t in enumerate(tris) if t["topo"] == 49}
    # boundary edges: rock|grass
    bnd_edges = []
    bnd_rock = set()
    for e, ts in edge_tris.items():
        if len(ts) != 2:
            continue
        r = [ti for ti in ts if ti in rock]
        g = [ti for ti in ts if tris[ti]["topo"] in GRASS]
        if len(r) == 1 and len(g) == 1:
            bnd_edges.append((e, r[0], g[0]))
            bnd_rock.add(r[0])
    if not bnd_edges:
        continue

    # pair rock tris into quads
    e2r = defaultdict(list)
    for ti in rock:
        ps = [kk(v) for v in tris[ti]["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e2r[tuple(sorted((ps[a], ps[b])))].append(ti)
    qof = {}
    qgrp = []
    for e, ts in e2r.items():
        if len(ts) != 2 or ts[0] in qof or ts[1] in qof:
            continue
        if len({kk(v) for t2 in ts for v in tris[t2]["w"]}) != 4:
            continue
        qof[ts[0]] = qof[ts[1]] = len(qgrp)
        qgrp.append(list(ts))
    for ti in rock:
        if ti not in qof:
            qof[ti] = len(qgrp)
            qgrp.append([ti])

    # per BOUNDARY quad: tile, v-pinning, orientation, density
    tiles_b, tiles_mid = Counter(), Counter()
    vfrac_bnd, vfrac_int = [], []
    u_along, dens_along, dens_perp = [], [], []
    win_du, win_dv = [], []
    for gi, grp in enumerate(qgrp):
        uvm, wm = {}, {}
        for t2 in grp:
            for k in range(3):
                key = kk(tris[t2]["w"][k])
                uvm[key] = tris[t2]["uv"][k]
                wm[key] = tris[t2]["w"][k]
        us = [q[0] for q in uvm.values()]
        vs = [q[1] for q in uvm.values()]
        col = int(math.floor((min(us) - pu) / TILE_U + 0.5))
        row = int(math.floor((min(vs) - pv) / TILE_V + 0.5))
        is_b = any(t2 in bnd_rock for t2 in grp)
        (tiles_b if is_b else tiles_mid)[(col, row)] += 1
        if not is_b:
            continue
        win_du.append((max(us) - min(us)) / TILE_U)
        win_dv.append((max(vs) - min(vs)) / TILE_V)
        # boundary verts of this quad = verts on any boundary edge
        bnd_pts = set()
        for e, r2, g2 in bnd_edges:
            if r2 in grp:
                bnd_pts.update(e)
        vb = [uvm[p][1] for p in uvm if p in bnd_pts]
        vi = [uvm[p][1] for p in uvm if p not in bnd_pts]
        tile_v0 = pv + row * TILE_V
        vfrac_bnd += [(v2 - tile_v0) / TILE_V for v2 in vb]
        vfrac_int += [(v2 - tile_v0) / TILE_V for v2 in vi]
        # orientation: correlate u with the boundary tangent
        if len(bnd_pts) >= 2:
            bp = sorted(bnd_pts)
            d = np.array(wm[bp[-1]]) - np.array(wm[bp[0]])
            L = math.hypot(d[0], d[2])
            if L > 0.5:
                du2 = uvm[bp[-1]][0] - uvm[bp[0]][0]
                dv2 = uvm[bp[-1]][1] - uvm[bp[0]][1]
                u_along.append(abs(du2) / (abs(du2) + abs(dv2) + 1e-9))
                dens_along.append(abs(du2) * 2048 / L)
        # perp density: interior vs boundary point pair
        if vi and vb and len(bnd_pts) >= 1:
            p_i = [p for p in uvm if p not in bnd_pts][0]
            p_b = sorted(bnd_pts)[0]
            d3 = np.array(wm[p_i]) - np.array(wm[p_b])
            L3 = np.linalg.norm(d3)
            if L3 > 0.5:
                dens_perp.append(abs(uvm[p_i][1] - uvm[p_b][1]) * 4096 / L3)
    # grass side tiles
    g_bnd, g_far = Counter(), Counter()
    for ti, t in enumerate(tris):
        if t["topo"] not in GRASS:
            continue
        us = [q[0] for q in t["uv"]]
        vs = [q[1] for q in t["uv"]]
        col = int(math.floor((min(us) - pu) / TILE_U + 0.5))
        row = int(math.floor((min(vs) - pv) / TILE_V + 0.5))
        near = any(ti == g2 for _, _, g2 in bnd_edges)
        (g_bnd if near else g_far)[(col, row)] += 1

    print(f"\n== {name.upper()}: {len(bnd_edges)} boundary edges, "
          f"{sum(tiles_b.values())} boundary quads / {sum(tiles_mid.values())} mid quads")
    print(f"   A. boundary tiles: {tiles_b.most_common(8)}")
    print(f"      mid-face tiles: {tiles_mid.most_common(8)}")
    print(f"   B. v-frac within tile at BOUNDARY verts: med "
          f"{np.median(vfrac_bnd):.2f} p10 {np.percentile(vfrac_bnd, 10):.2f} "
          f"p90 {np.percentile(vfrac_bnd, 90):.2f}" if vfrac_bnd else "   B. n/a")
    print(f"      v-frac at INTERIOR verts:            med "
          f"{np.median(vfrac_int):.2f} p10 {np.percentile(vfrac_int, 10):.2f} "
          f"p90 {np.percentile(vfrac_int, 90):.2f}" if vfrac_int else "")
    print(f"   C. u-share of uv change along the boundary: med "
          f"{np.median(u_along):.2f} (1.0 = u runs along the foot)" if u_along else "")
    print(f"   D. density along the boundary {np.median(dens_along):.0f} px/u; "
          f"perpendicular {np.median(dens_perp):.0f} px/u"
          if dens_along and dens_perp else "")
    print(f"      boundary window sizes: du med {np.median(win_du):.2f} tile, "
          f"dv med {np.median(win_dv):.2f} tile")
    print(f"   F. grass tiles AT the boundary: {g_bnd.most_common(5)}")
    print(f"      grass tiles far away:        {g_far.most_common(5)}")
    report[name] = dict(
        boundary_tiles={f"{c},{r}": n for (c, r), n in tiles_b.most_common()},
        mid_tiles={f"{c},{r}": n for (c, r), n in tiles_mid.most_common(12)},
        vfrac_bnd=[round(float(np.median(vfrac_bnd)), 3),
                   round(float(np.percentile(vfrac_bnd, 10)), 3),
                   round(float(np.percentile(vfrac_bnd, 90)), 3)] if vfrac_bnd else None,
        vfrac_int=[round(float(np.median(vfrac_int)), 3)] if vfrac_int else None,
        u_along=round(float(np.median(u_along)), 3) if u_along else None,
        dens=[round(float(np.median(dens_along)), 1) if dens_along else None,
              round(float(np.median(dens_perp)), 1) if dens_perp else None],
        win=[round(float(np.median(win_du)), 3), round(float(np.median(win_dv)), 3)],
        grass_bnd={f"{c},{r}": n for (c, r), n in g_bnd.most_common(8)},
    )

# ---- the atlas contact print -----------------------------------------------------------------------
gp = Path(config.find_game_path(None))
MOG = gp / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
atlas = Image.open(MOG).convert("RGB")
AW, AH = atlas.size
CELLPX = 160
COLS = range(4, 11)
ROWS = range(6, 12)
sheet = Image.new("RGB", (len(list(COLS)) * (CELLPX + 8) + 8,
                          len(list(ROWS)) * (CELLPX + 22) + 8), (20, 20, 28))
dr = ImageDraw.Draw(sheet)
for ri, row in enumerate(ROWS):
    for ci, col in enumerate(COLS):
        u0 = pu + col * TILE_U
        v0 = pv + row * TILE_V
        px0 = int(u0 * AW)
        py0 = int((1.0 - (v0 + TILE_V)) * AH)
        tile = atlas.crop((px0, py0, px0 + int(TILE_U * AW), py0 + int(TILE_V * AH)))
        tile = tile.resize((CELLPX, CELLPX), Image.NEAREST)
        ox = 8 + ci * (CELLPX + 8)
        oy = 8 + ri * (CELLPX + 22)
        sheet.paste(tile, (ox, oy))
        dr.text((ox, oy + CELLPX + 3), f"col {col}, row {row}", fill=(230, 230, 230))
OUTD.mkdir(exist_ok=True)
sheet.save(OUTD / "atlas_contact.png")
print(f"\n-> {OUTD / 'atlas_contact.png'} (tiles are shown as stored; remember atlas v "
      f"grows DOWN the sheet = down the mountain)")
(OUTD / "foot_transition.json").write_text(json.dumps(report, indent=1))
print(f"-> {OUTD / 'foot_transition.json'}")
