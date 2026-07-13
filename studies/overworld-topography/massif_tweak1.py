"""MASSIF TWEAK 1 -- Stage-2 single-variable tile probes on the LIVE v4 island.

The sheet-massif study (daguerreo_massif_anatomy.py) decoded the organization; before any
synthesis, two cheap in-game questions decide how strict a `world-mountain` retile recipe
must be. Two ONE-QUAD probes on the massif's west outer face (deployed cell (1,16), the
donor-(5,15) bytes), each swapping a quad's 128px tile to another tile PROVEN to exist in
the massif's own language -- so the TILE stays in-language and only the ORGANIZATION breaks:

  PROBE A (the window question): same row, col jumped +-2 within the base band -- breaks
    windowed col continuation. Invisible in-game => col choice is cosmetically free and
    synthesis only needs rows right. A visible seam => the window continuity must be
    reproduced.
  PROBE B (the course question): same col, row 9 -> 7 -- puts an upper-body course tile at
    a low course. Invisible => rows aren't load-bearing either (unlikely -- the old
    bright-mid-stripe failure came from band mixing). Visible => rows are the axis synthesis
    must respect (expected).

UV-ONLY edit: positions/normals/tangents byte-identical, so placement/census CANNOT change
(UVs don't participate in ground queries). Dry-run by default; --apply writes with a sibling
.bak-<ts> backup (the suffix never matches the engine override glob). Revert = restore the
.bak. NOTE: the disc-4 mirror copy is deliberately NOT touched -- do not re-run world-mirror
while the probes are live (the disc1/disc4 divergence is intentional and temporary).

Run from the repo root: py studies/overworld-topography/massif_tweak1.py [--apply]
Needs out/daguerreo_massif.json (regenerate via daguerreo_massif_anatomy.py).
"""
import argparse
import json
import math
import shutil
import sys
import time
import types
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config                                # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

CELL = (1, 16)                                             # carries donor (5,15) = the west face
TILE_U, TILE_V = 0.0625, 0.03125
BLOCK = 64.0
LOWLAND_TP = (75.5, -1074.5)                               # the proven v4 lowland teleport
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true")
ap.add_argument("--mod-folder", default="FF9CustomMap-world")
args = ap.parse_args()

stage1 = json.loads((OUTD / "daguerreo_massif.json").read_text())
pu, pv = stage1["phase"]
inventory = {tuple(int(x) for x in k.split(",")) for k in stage1["tiles"]}

gp = Path(config.find_game_path(None))
mesh_path = (gp / args.mod_folder / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
             / f"r{CELL[1]}" / f"Block[{CELL[0]}][{CELL[1]}] Terrain.ff9mesh")
bm = M.blockmesh_from_ff9mesh(mesh_path, disc=1, x=CELL[0], y=CELL[1], part="terrain")
V = [list(v) for v in bm.verts]
N = [list(n) for n in bm.normals]
U = [list(u) for u in bm.uvs]
T = [list(t) for t in bm.tangents]
IDX = list(bm.flat_index)
ntri = len(IDX) // 3
tri_idx = [IDX[3 * t:3 * t + 3] for t in range(ntri)]
print(f"deployed {mesh_path.name}: {bm.vcount} verts, {ntri} tris")

def wpos(j):
    return (V[j][0] + BLOCK * CELL[0], V[j][1], V[j][2] - BLOCK * CELL[1])
topo = [X.decode_id(int(round(T[i[0]][0])))["topograph"] for i in tri_idx]
wall = {t for t in range(ntri) if topo[t] == 49}

# ---- quads on the wall (the stage-1 pairing) ----------------------------------------------------
e2t = defaultdict(list)
for t in wall:
    p = [kk(wpos(j)) for j in tri_idx[t]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        e2t[tuple(sorted((p[a], p[b])))].append(t)
paired, quads = {}, []
for e, ts in e2t.items():
    if len(ts) != 2 or ts[0] in paired or ts[1] in paired:
        continue
    vs = {kk(wpos(j)) for t in ts for j in tri_idx[t]}
    if len(vs) != 4:
        continue
    vs = sorted(vs, key=lambda p: p[1])
    lo, hi = vs[:2], vs[2:]
    if abs(lo[0][1] - lo[1][1]) > 1.5 or abs(hi[0][1] - hi[1][1]) > 1.5:
        continue
    us = [U[j][0] for t in ts for j in tri_idx[t]]
    vs2 = [U[j][1] for t in ts for j in tri_idx[t]]
    du, dv = max(us) - min(us), max(vs2) - min(vs2)
    if not (0.5 * TILE_U < du <= TILE_U + 1e-4 and 0.5 * TILE_V < dv <= TILE_V + 1e-4):
        continue                                           # want clean one-tile quads
    a3, b3, c3 = (np.array(wpos(tri_idx[ts[0]][k])) for k in range(3))
    fn = np.cross(b3 - a3, c3 - a3)
    a3, b3, c3 = (np.array(wpos(tri_idx[ts[1]][k])) for k in range(3))
    fn = fn + np.cross(b3 - a3, c3 - a3)
    L = math.hypot(fn[0], fn[2]) or 1.0
    paired[ts[0]] = paired[ts[1]] = len(quads)
    quads.append(dict(tris=list(ts),
                      col=round((min(us) - pu) / TILE_U), row=round((min(vs2) - pv) / TILE_V),
                      y=sum(p[1] for p in lo + hi) / 4,
                      az=math.atan2(fn[2] / L, fn[0] / L),
                      cen=np.mean([np.array(p) for p in lo + hi], axis=0)))
print(f"wall tris {len(wall)}, clean one-tile quads {len(quads)}")

# side neighbors + local turn
q_of_vert = defaultdict(set)
for qi, q in enumerate(quads):
    for t in q["tris"]:
        for j in tri_idx[t]:
            q_of_vert[kk(wpos(j))].add(qi)
side = defaultdict(set)
for p, qs in q_of_vert.items():
    for a in qs:
        for b in qs:
            if a < b and abs(quads[a]["y"] - quads[b]["y"]) < 2.0:
                side[a].add(b); side[b].add(a)
for qi, q in enumerate(quads):
    turns = [abs((q["az"] - quads[o]["az"] + math.pi) % (2 * math.pi) - math.pi)
             for o in side[qi]]
    q["turn"] = math.degrees(max(turns)) if turns else 0.0

# ---- probe selection: west-facing, row 9, straight, window-interior, westernmost ---------------
def pick(row, want_westmost_after=None, relax=0):
    cand = []
    for qi, q in enumerate(quads):
        if q["row"] != row or q["turn"] >= 15:
            continue
        if math.cos(q["az"]) > (-0.5 if relax < 2 else 0.0):
            continue                                       # want a west-facing quad
        nb = [quads[o] for o in side[qi]]
        clean = sum(1 for o in nb if o["row"] == row and abs(o["col"] - q["col"]) == 1)
        if relax < 1 and clean < 2:
            continue                                       # a window interior (both sides adj)
        if want_westmost_after is not None and \
                math.hypot(q["cen"][0] - want_westmost_after[0],
                           q["cen"][2] - want_westmost_after[2]) < 12.0:
            continue                                       # keep the probes separated
        cand.append(qi)
    return sorted(cand, key=lambda qi: quads[qi]["cen"][0])

sel_a = None
for relax in (0, 1, 2):
    got = pick(9, relax=relax)
    if got:
        sel_a = got[0]
        print(f"probe A picked at relax level {relax}")
        break
if sel_a is None:
    sys.exit("no probe-A candidate found")
qa = quads[sel_a]
target_a = (qa["col"] + 2, 9) if (qa["col"] + 2, 9) in inventory else (qa["col"] - 2, 9)
if target_a not in inventory:
    sys.exit(f"no in-language col+-2 target for col {qa['col']} row 9")

sel_b = None
for relax in (0, 1, 2):
    for qi in pick(9, want_westmost_after=qa["cen"], relax=relax):
        if (quads[qi]["col"], 7) in inventory:
            sel_b = qi
            print(f"probe B picked at relax level {relax}")
            break
    if sel_b is not None:
        break
if sel_b is None:
    sys.exit("no probe-B candidate with an in-language (col,7) target")
qb = quads[sel_b]
target_b = (qb["col"], 7)

def describe(tag, q, tgt):
    dx = q["cen"][0] - LOWLAND_TP[0]
    dz = q["cen"][2] - LOWLAND_TP[1]
    print(f"  PROBE {tag}: quad at world ({q['cen'][0]:.1f}, {q['cen'][1]:.1f}, "
          f"{q['cen'][2]:.1f})  tile ({q['col']},{q['row']}) -> {tgt}  "
          f"facing az {math.degrees(q['az']):.0f}deg turn {q['turn']:.0f}deg")
    print(f"           from the lowland teleport {LOWLAND_TP}: {dx:+.0f}u east, "
          f"{-dz:+.0f}u south")
print("selection:")
describe("A (col window break)", qa, target_a)
describe("B (row course break)", qb, target_b)

# ---- apply: shift UVs on the probe tris, splitting shared verts first ---------------------------
use_count = defaultdict(int)
for j in IDX:
    use_count[j] += 1
def shift_quad(q, du_tiles, dv_tiles):
    slots = [(3 * t + k) for t in q["tris"] for k in range(3)]
    probe_use = defaultdict(int)
    for s in slots:
        probe_use[IDX[s]] += 1
    remap = {}
    for s in slots:
        j = IDX[s]
        if use_count[j] > probe_use[j]:                    # shared beyond the probe: split
            if j not in remap:
                V.append(list(V[j])); N.append(list(N[j]))
                U.append(list(U[j])); T.append(list(T[j]))
                remap[j] = len(V) - 1
            IDX[s] = remap[j]
    for j in {IDX[s] for s in slots}:
        U[j][0] += du_tiles * TILE_U
        U[j][1] += dv_tiles * TILE_V
    return len(remap)
splits_a = shift_quad(qa, target_a[0] - qa["col"], 0)
splits_b = shift_quad(qb, 0, target_b[1] - qb["row"])
print(f"vert splits: A {splits_a}, B {splits_b}; verts {bm.vcount} -> {len(V)}")

# ---- marker render -------------------------------------------------------------------------------
S = 6
x0, z1 = CELL[0] * BLOCK, -CELL[1] * BLOCK
W = H = int(BLOCK * S)
img = Image.new("RGB", (W, H), (16, 16, 24))
px = img.load()
def paint(tri2d, color):
    xs = [p[0] for p in tri2d]; ys = [p[1] for p in tri2d]
    (ax, ay), (bx, by), (cx, cy) = tri2d
    d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(d) < 1e-9:
        return
    for yy in range(max(0, int(min(ys))), min(H - 1, int(max(ys)) + 1) + 1):
        for xx in range(max(0, int(min(xs))), min(W - 1, int(max(xs)) + 1) + 1):
            w0 = ((by - cy) * (xx - cx) + (cx - bx) * (yy - cy)) / d
            w1 = ((cy - ay) * (xx - cx) + (ax - cx) * (yy - cy)) / d
            if w0 >= -0.001 and w1 >= -0.001 and (1 - w0 - w1) >= -0.001:
                px[xx, yy] = color
def to2d(p):
    return ((p[0] - x0) * S, (z1 - p[2]) * S)
order = sorted(range(ntri), key=lambda t: min(V[j][1] for j in tri_idx[t]))
for t in order:
    ws = [wpos(j) for j in tri_idx[t]]
    y = float(np.mean([w[1] for w in ws]))
    if t in wall:
        c = (150, 110, 80) if y < 12 else (190, 150, 110)
    else:
        g = int(70 + min(1.0, y / 20.0) * 100)
        c = (g - 20, g, g - 30)
    paint([to2d(w) for w in ws], c)
for q, col in ((qa, (255, 40, 40)), (qb, (40, 120, 255))):
    for t in q["tris"]:
        paint([to2d(wpos(j)) for j in tri_idx[t]], col)
tp = to2d((LOWLAND_TP[0], 0, LOWLAND_TP[1]))
for dx in range(-4, 5):
    for dy in range(-4, 5):
        if abs(dx) + abs(dy) <= 4 and 0 <= tp[0] + dx < W and 0 <= tp[1] + dy < H:
            px[int(tp[0]) + dx, int(tp[1]) + dy] = (255, 255, 0)
OUTD.mkdir(exist_ok=True)
img.save(OUTD / "massif_tweak1.png")
print(f"-> {OUTD / 'massif_tweak1.png'} (red = probe A, blue = probe B, "
      f"yellow diamond = the lowland teleport)")

if not args.apply:
    print("\nDRY RUN (no write). Re-run with --apply to deploy the probes.")
    sys.exit(0)

# ---- write + verify ------------------------------------------------------------------------------
bak = mesh_path.with_name(mesh_path.name + f".bak-{time.strftime('%Y%m%d-%H%M%S')}")
shutil.copy2(mesh_path, bak)
out_bm = types.SimpleNamespace(verts=V, normals=N, uvs=U, tangents=T,
                               flat_index=IDX, vcount=len(V))
M.write_ff9mesh(out_bm, mesh_path)
chk = M.blockmesh_from_ff9mesh(mesh_path, disc=1, x=CELL[0], y=CELL[1], part="terrain")
cidx = list(chk.flat_index)
assert len(cidx) == len(IDX), "tri count changed"
probe_slots = {3 * t + k for q in (qa, qb) for t in q["tris"] for k in range(3)}
bad = 0
orig = M.blockmesh_from_ff9mesh(bak, disc=1, x=CELL[0], y=CELL[1], part="terrain")
oidx = list(orig.flat_index)
for s in range(len(cidx)):
    op, cp = orig.verts[oidx[s]], chk.verts[cidx[s]]
    on, cn = orig.normals[oidx[s]], chk.normals[cidx[s]]
    ot, ct = orig.tangents[oidx[s]], chk.tangents[cidx[s]]
    ou, cu2 = orig.uvs[oidx[s]], chk.uvs[cidx[s]]
    if any(abs(a - b) > 1e-6 for a, b in zip(op, cp)) or \
       any(abs(a - b) > 1e-6 for a, b in zip(on, cn)) or \
       any(abs(a - b) > 1e-6 for a, b in zip(ot, ct)):
        bad += 1
    uv_same = all(abs(a - b) < 1e-6 for a, b in zip(ou, cu2))
    if (s in probe_slots) == uv_same:
        bad += 1
assert bad == 0, f"verify FAILED on {bad} slots"
print(f"\nAPPLIED + VERIFIED: geometry byte-true per slot; UVs changed on exactly "
      f"{len(probe_slots)} slots. Backup: {bak.name}")
print("Revert: copy the .bak back over the .ff9mesh. Do NOT re-run world-mirror "
      "while the probes are live (disc 4 intentionally keeps the pristine copy).")
