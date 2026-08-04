"""C2 -- THE CURTAIN UV RULE: what a lawful curtain mint has to emit (curtain study, instrument 2).

Questions registered in studies/path-d-new-world/CURTAIN-GRAMMAR.md (C2) BEFORE this ran.
The donor exemplar is the stock (15,14) forest blob whose rim full_skirt.py found closed by
plan-degenerate vertical faces (3 plan-owners per rim edge, no once-edges).

  Q1 RIM MAP      -- locate the (15,14) rim curtains (plan-degenerate: |ny| <= 0.05 or
                     plan area < 1e-3 of 3D area): count, top/bottom heights, topograph,
                     the 3-owner plan-edge signature, verticality, bottom-edge weld.
  Q2 UV RULE      -- band-continuation of the surface above (THE BAND-CONTINUATION LAW's
                     prediction) vs a dedicated atlas strip vs the ground below's
                     continuation; v-orientation + rate per unit drop; texel-row pinning
                     of the top edge; the u law along the run (anchors, rate, adjacency).
  Q3 GENERALITY   -- every disc-1 block with forest (topo-37) blobs: same construction?
                     same strip? Plus every OTHER topograph that ships plan-degenerate
                     faces outside the decoded wall classes (49 crest walls, 58 coastal
                     cliffs): does the construction generalize to non-forest raised
                     patches, and with what per-family strips? Plus the rim-seal census:
                     is any dropped forest rim left un-curtained?
  Q4 MINT RECIPE  -- the verts/uvs/topograph/winding a lawful curtain emits, printed and
                     serialized, or the honest statement that no single rule names it.

Read-only vs stock disc-1 terrain. Artifacts -> out/curtain_uv.json,
out/curtain_uv_plan.png (the (15,14) rim in plan), out/curtain_uv_atlas.png (uv-space
scatter of every degenerate family vs the tile grid).
Regenerate: py -X utf8 curtain_uv.py   (from studies/overworld-topography/)
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

TILE_U, TILE_V = 0.0625, 0.03125
DONOR = (15, 14)
FOREST = 37
WALL_CLASSES = {49, 50, 58}                                 # decoded elsewhere; excluded from Q3
OUT = Path(__file__).with_name("out") / "curtain_uv.json"
PNG_PLAN = Path(__file__).with_name("out") / "curtain_uv_plan.png"
PNG_ATLAS = Path(__file__).with_name("out") / "curtain_uv_atlas.png"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731
kp = lambda v: (round(v[0], 2), round(v[2], 2))                   # noqa: E731  plan key


def on_border(p):
    return (min(abs(p[0]), abs(p[0] - 64.0)) < 0.5 or
            min(abs(p[2]), abs(p[2] + 64.0)) < 0.5)


def load(bx, by):
    """Block -> (tri_idx, topo, V, U, degenerate-set, edge->tris)."""
    bm = X.read_block(bx, by, disc=1, part="terrain")
    V, U, T = bm.verts, bm.uvs, bm.tangents
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[i[0]][0])))["topograph"] for i in tri_idx]
    deg = set()
    fnorm = {}
    for t in range(ntri):
        a, b, c = (V[i] for i in tri_idx[t])
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        a3 = L / 2.0
        pa = abs((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])) / 2.0
        fnorm[t] = (nx / L, ny / L, nz / L)
        if abs(ny / L) <= 0.05 or (a3 > 1e-9 and pa < 1e-3 * a3):
            deg.add(t)
    ET = defaultdict(list)
    for t, idx in enumerate(tri_idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ET[tuple(sorted((kk(V[idx[a]]), kk(V[idx[b]]))))].append(t)
    return tri_idx, topo, V, U, deg, ET, fnorm


def med(a):
    s = sorted(a)
    return s[len(s) // 2] if s else None


# =============================================================================================
# Q1 + Q2 -- the donor exemplar (15,14)
# =============================================================================================
tri_idx, topo, V, U, deg, ET, fnorm = load(*DONOR)
cur = sorted(t for t in deg if topo[t] == FOREST)
curset = set(cur)
surf = [t for t in range(len(tri_idx)) if topo[t] == FOREST and t not in curset]

tops_y, bots_y, drops = [], [], []
raw_ids_cur = Counter()
raw_ids_surf = Counter()
bm_d = X.read_block(*DONOR, disc=1, part="terrain")
for t in cur:
    raw_ids_cur[int(round(bm_d.tangents[tri_idx[t][0]][0]))] += 1
for t in surf:
    raw_ids_surf[int(round(bm_d.tangents[tri_idx[t][0]][0]))] += 1

for t in cur:
    ys = [V[i][1] for i in tri_idx[t]]
    tops_y.append(max(ys))
    bots_y.append(min(ys))
    drops.append(round(max(ys) - min(ys), 2))

# plan-edge owner signature (full_skirt's finding re-measured): for each curtain tri edge,
# project to plan; count ALL tris in the block owning that plan segment (any y)
plan_owner = defaultdict(set)
for t, idx in enumerate(tri_idx):
    for a, b in ((0, 1), (1, 2), (2, 0)):
        e = tuple(sorted((kp(V[idx[a]]), kp(V[idx[b]]))))
        if e[0] != e[1]:
            plan_owner[e].add(t)
sig = Counter()
for t in cur:
    idx = tri_idx[t]
    ys = [V[i][1] for i in idx]
    ymax = max(ys)
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ia, ib = idx[a], idx[b]
        if V[ia][1] >= ymax - 0.05 and V[ib][1] >= ymax - 0.05:   # the top edge
            e = tuple(sorted((kp(V[ia]), kp(V[ib]))))
            if e[0] != e[1]:
                sig[len(plan_owner[e])] += 1

# top/bottom 3D-edge ownership + uv continuity at shared verts
n_cont = n_disc = 0
above_cls, below_cls = Counter(), Counter()
bot_weld = Counter()
for t in cur:
    idx = tri_idx[t]
    ys = [V[i][1] for i in idx]
    ymax, ymin = max(ys), min(ys)
    for a, b in ((0, 1), (1, 2), (2, 0)):
        ia, ib = idx[a], idx[b]
        e = tuple(sorted((kk(V[ia]), kk(V[ib]))))
        owners = [o for o in ET[e] if o != t and o not in curset and o not in deg]
        is_top = V[ia][1] >= ymax - 0.05 and V[ib][1] >= ymax - 0.05
        is_bot = V[ia][1] <= ymin + 0.05 and V[ib][1] <= ymin + 0.05
        if is_bot:
            if owners:
                bot_weld["ground-welded"] += 1
            elif on_border(V[ia]) or on_border(V[ib]):
                bot_weld["block-border"] += 1
            else:
                bot_weld["open"] += 1
        for o in owners:
            (above_cls if is_top else below_cls if is_bot else Counter())[topo[o]] += 1
            for i_c in (ia, ib):
                for i_o in tri_idx[o]:
                    if kk(V[i_o]) == kk(V[i_c]):
                        d = math.hypot(U[i_o][0] - U[i_c][0], U[i_o][1] - U[i_c][1])
                        if d < 1e-4:
                            n_cont += 1
                        else:
                            n_disc += 1

# v-pinning + strip extents on the donor
v_top_pin, v_bot_pin = Counter(), Counter()
us_all, vs_all = [], []
for t in cur:
    idx = tri_idx[t]
    ys = [V[i][1] for i in idx]
    ymid = (min(ys) + max(ys)) / 2
    for i in idx:
        us_all.append(U[i][0])
        vs_all.append(U[i][1])
        (v_top_pin if V[i][1] >= ymid else v_bot_pin)[round(U[i][1] * 1024, 1)] += 1

# tiles of the surface above and the ground below (phase-free nearest-tile, crib convention)
PU = PV = 0.015625


def tile_of(t):
    us = [U[i][0] for i in tri_idx[t]]
    vs = [U[i][1] for i in tri_idx[t]]
    return (int(math.floor((min(us) - PU) / TILE_U + 0.5)),
            int(math.floor((min(vs) - PV) / TILE_V + 0.5)))


surf_tiles = Counter(tile_of(t) for t in surf)
gnd_tiles = Counter(tile_of(t) for t in range(len(tri_idx)) if topo[t] == 0)

print("== Q1 THE (15,14) RIM MAP ==")
print(f"   curtain tris (plan-degenerate topo-{FOREST}): {len(cur)} of "
      f"{len(cur) + len(surf)} forest tris (surface {len(surf)})")
print(f"   top y {min(tops_y):.2f}..{max(tops_y):.2f}  bottom y {min(bots_y):.2f}.."
      f"{max(bots_y):.2f}  drops {min(drops)}..{max(drops)} (med {med(drops)})")
print(f"   raw ids: curtain {dict(raw_ids_cur)} vs surface {dict(raw_ids_surf)}")
print(f"   plan-owner signature on top edges: {dict(sig)} (full_skirt found 3)")
print(f"   bottom-edge weld: {dict(bot_weld)}")
print(f"   3D edge ownership: above {dict(above_cls)}  below {dict(below_cls)}")

print("\n== Q2 THE UV RULE (donor) ==")
print(f"   shared-vert uv vs surface/ground owners: continuous {n_cont}, "
      f"discontinuous {n_disc}  -> BAND-CONTINUATION: "
      f"{'CONFIRMED' if n_cont > n_disc else 'REFUTED (dedicated strip)'}")
print(f"   strip u: {min(us_all):.6f}..{max(us_all):.6f} "
      f"({min(us_all) * 1024:.0f}..{max(us_all) * 1024:.0f} texels)")
print(f"   strip v: {min(vs_all):.6f}..{max(vs_all):.6f} "
      f"({min(vs_all) * 1024:.0f}..{max(vs_all) * 1024:.0f} texels)")
print(f"   v at TOP verts: {v_top_pin.most_common(3)} (texel rows x1024)")
print(f"   v at BOTTOM verts: {v_bot_pin.most_common(3)}")
print(f"   surface-above tiles {surf_tiles.most_common(4)}; "
      f"ground-below tiles {gnd_tiles.most_common(4)} -> the curtain rect matches NEITHER")

# =============================================================================================
# Q3 -- generality across disc-1 (forest + every other degenerate family)
# =============================================================================================
fam_pin = defaultdict(Counter)
fam_u = defaultdict(list)
fam_drop = defaultdict(list)
fam_above = defaultdict(Counter)
fam_below = defaultdict(Counter)
fam_cont = defaultdict(lambda: [0, 0])
fam_n = Counter()
blk_rows = []
rim_census = Counter()
u_anchor = Counter()
du_run = []
adj_u = [0, 0]
wind = [0, 0]
n_vert_col = [0, 0]                                         # bottom vert has top-vert plan twin / not

for (bx, by) in X.list_blocks(disc=1):
    try:
        tri_idx, topo, V, U, deg, ET, fnorm = load(bx, by)
    except ValueError:
        continue
    ntri = len(tri_idx)
    for t in deg:
        fam_n[topo[t]] += 1
    for fam in set(topo[t] for t in deg):
        if fam in WALL_CLASSES:
            continue
        curf = [t for t in deg if topo[t] == fam]
        for t in curf:
            idx = tri_idx[t]
            ys = [V[i][1] for i in idx]
            ymid = (min(ys) + max(ys)) / 2
            fam_drop[fam].append(round(max(ys) - min(ys), 2))
            vt = [round(U[i][1] * 1024, 1) for i in idx if V[i][1] >= ymid]
            vb = [round(U[i][1] * 1024, 1) for i in idx if V[i][1] < ymid]
            if vt and vb:
                fam_pin[fam][(min(vt), max(vb))] += 1
            for i in idx:
                fam_u[fam].append(U[i][0])
            for a, b in ((0, 1), (1, 2), (2, 0)):
                ia, ib = idx[a], idx[b]
                e = tuple(sorted((kk(V[ia]), kk(V[ib]))))
                owners = [o for o in ET[e] if o != t and o not in deg]
                is_top = V[ia][1] >= max(ys) - 0.05 and V[ib][1] >= max(ys) - 0.05
                is_bot = V[ia][1] <= min(ys) + 0.05 and V[ib][1] <= min(ys) + 0.05
                for o in owners:
                    if is_top:
                        fam_above[fam][topo[o]] += 1
                    elif is_bot:
                        fam_below[fam][topo[o]] += 1
                    for i_c in (ia, ib):
                        for i_o in tri_idx[o]:
                            if kk(V[i_o]) == kk(V[i_c]):
                                d = math.hypot(U[i_o][0] - U[i_c][0],
                                               U[i_o][1] - U[i_c][1])
                                fam_cont[fam][0 if d < 1e-4 else 1] += 1

    # forest-specific anatomy (u law, winding, verticality, rim seal census)
    cur = [t for t in deg if topo[t] == FOREST]
    curset = set(cur)
    n37 = sum(1 for t in range(ntri) if topo[t] == FOREST)
    if cur:
        blk_rows.append(dict(blk=[bx, by], n37=n37, ncur=len(cur)))
    surf_pts = [((V[tri_idx[t][0]][0] + V[tri_idx[t][1]][0] + V[tri_idx[t][2]][0]) / 3,
                 (V[tri_idx[t][0]][2] + V[tri_idx[t][1]][2] + V[tri_idx[t][2]][2]) / 3)
                for t in range(ntri) if topo[t] == FOREST and t not in curset]
    top_plan = set()
    for t in cur:
        idx = tri_idx[t]
        ys = [V[i][1] for i in idx]
        for i in idx:
            if V[i][1] >= max(ys) - 0.05:
                top_plan.add(kp(V[i]))
    for t in cur:
        idx = tri_idx[t]
        ys = [V[i][1] for i in idx]
        ymax, ymin = max(ys), min(ys)
        for i in idx:
            u_anchor[round(U[i][0] * 1024)] += 1
            if V[i][1] <= ymin + 0.05:
                n_vert_col[0 if kp(V[i]) in top_plan else 1] += 1
        tops = [i for i in idx if V[i][1] >= ymax - 0.05]
        if len(tops) == 2:
            run = math.hypot(V[tops[0]][0] - V[tops[1]][0],
                             V[tops[0]][2] - V[tops[1]][2])
            if run > 0.5:
                du_run.append((run, abs(U[tops[0]][0] - U[tops[1]][0])))
        (nx, ny, nz) = fnorm[t]
        cx = sum(V[i][0] for i in idx) / 3
        cz = sum(V[i][2] for i in idx) / 3
        if surf_pts:
            nb = min(surf_pts, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cz) ** 2)
            dx, dz = nb[0] - cx, nb[1] - cz
            if math.hypot(dx, dz) > 0.05:
                wind[0 if nx * dx + nz * dz < 0 else 1] += 1
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ia, ib = idx[a], idx[b]
            if abs(V[ia][1] - V[ib][1]) < 0.5:
                continue
            e = tuple(sorted((kk(V[ia]), kk(V[ib]))))
            for o in ET[e]:
                if o != t and o in curset:
                    for i_c in (ia, ib):
                        for i_o in tri_idx[o]:
                            if kk(V[i_o]) == kk(V[i_c]):
                                adj_u[0 if abs(U[i_o][0] - U[i_c][0]) < 1e-4
                                      else 1] += 1
    # rim seal census (forest surface boundary edges)
    if n37:
        for e, ts in ET.items():
            surf37 = [t for t in ts if topo[t] == FOREST and t not in curset]
            if not surf37:
                continue
            others = [t for t in ts if topo[t] != FOREST]
            curt = [t for t in ts if t in curset]
            if not others and not curt:
                if len(surf37) >= 2:
                    continue
                (p1, p2) = e
                rim_census["block-border" if on_border(p1) or on_border(p2)
                           else "once-open"] += 1
            elif curt:
                rim_census["curtain-sealed"] += 1
            else:
                rim_census["direct-weld"] += 1

print("\n== Q3 GENERALITY (disc-1) ==")
print(f"   plan-degenerate census by topograph: {dict(fam_n.most_common())}")
print(f"   forest curtains: {sum(r['ncur'] for r in blk_rows)} tris across "
      f"{len(blk_rows)} blocks")
for fam in sorted(fam_pin, key=lambda f: -sum(fam_pin[f].values())):
    n = sum(fam_pin[fam].values())
    pins = fam_pin[fam].most_common(4)
    print(f"   topo {fam}: n {n}, v-pins {pins}")
    print(f"      u {min(fam_u[fam]) * 1024:.0f}..{max(fam_u[fam]) * 1024:.0f} texels; "
          f"drops {min(fam_drop[fam])}..{max(fam_drop[fam])} (med {med(fam_drop[fam])}); "
          f"above {dict(fam_above[fam])}; below {dict(fam_below[fam])}; "
          f"uv-cont {fam_cont[fam][0]}/{fam_cont[fam][0] + fam_cont[fam][1]}")
print(f"   forest rim boundary census: {dict(rim_census)}")
print(f"   winding vs local interior: outward {wind[0]}, inward {wind[1]}")
print(f"   bottom-vert plan twin among top verts (columns vertical): "
      f"{n_vert_col[0]} yes / {n_vert_col[1]} no")
print(f"   u texel anchors (top 6): {u_anchor.most_common(6)}")
rates = sorted(du / r for r, du in du_run)
print(f"   du/run on top edges: n {len(rates)}, med {med(rates):.4f} "
      f"({med(rates) * 1024:.1f} texels/u), p10 {rates[len(rates) // 10]:.4f}, "
      f"p90 {rates[9 * len(rates) // 10]:.4f}")
print(f"   adjacent-quad u at shared vertical edges: same {adj_u[0]}, "
      f"different {adj_u[1]} ({adj_u[0] / max(1, sum(adj_u)):.0%} continuous)")

# =============================================================================================
# Q4 -- the mint recipe (printed; numbers serialized below)
# =============================================================================================
print("""
== Q4 THE MINT RECIPE stock implies (forest-class curtain) ==
   GIVEN a rim polyline (v_i at surface height y_i) and the ground sheet below:
   1 VERTS    per segment (v_i, v_i+1) emit a vertical quad (2 tris): top edge welded
              to the surface rim verts; bottom verts at the SAME plan positions dropped
              onto the ground sheet and WELDED into it (the ground mesh must carry
              matching verts along the rim line). Plan-degenerate by construction.
   2 TOPOGRAPH the curtain carries the SURFACE family's topograph (37 for forest),
              never the ground's, never a dedicated id.
   3 UV       a DEDICATED painted strip, uv-discontinuous with BOTH neighbors:
              v_top = 930/1024 pinned, v_bot = 961/1024 pinned (stretch over the drop,
              no rate); u advances along the run at ~15 texels/u inside u = 115..241
              texels, station anchors {115, 179, 241} (one ~64-texel tile per ~4.1u
              segment), ~3/4 of adjacent seams u-continuous, reset at strip ends.
   4 WINDING  face plan-normal OUTWARD, away from the raised surface's interior.
   5 DOMAIN   stock ships this strip for drops ~1.9-2.9u. Taller families exist:
              topo-38 (desert vegetation) uses its own 2-row strip (u 738-869,
              v rows 548/580/611) for drops to 3.4u; topo-59 mixes strips to 7.7u.""")

# =============================================================================================
# renders
# =============================================================================================
PNG_PLAN.parent.mkdir(parents=True, exist_ok=True)
tri_idx, topo, V, U, deg, ET, fnorm = load(*DONOR)
cur = set(t for t in deg if topo[t] == FOREST)
img = Image.new("RGB", (720, 760), (24, 26, 30))
dr = ImageDraw.Draw(img)
SC, OX, OY = 10.5, 24, 60


def M(p):
    return (OX + p[0] * SC, OY + (p[2] + 64.0) * SC)


for t in range(len(tri_idx)):
    pts = [M(V[i]) for i in tri_idx[t]]
    if t in cur:
        continue
    col = ((60, 120, 70) if topo[t] == FOREST else
           (70, 72, 80) if topo[t] == 0 else
           (110, 90, 70) if topo[t] == 49 else (52, 56, 66))
    dr.polygon(pts, outline=col)
for t in cur:
    pts = [M(V[i]) for i in tri_idx[t]]
    dr.line(pts + [pts[0]], fill=(235, 80, 80), width=2)
dr.text((10, 6), f"stock blk {DONOR} terrain plan: green=forest surface, red=curtain rim,",
        fill=(220, 220, 220))
dr.text((10, 22), "gray=ground, brown=rock. The rim is closed by vertical quads.",
        fill=(220, 220, 220))
img.save(PNG_PLAN)

img2 = Image.new("RGB", (1060, 560), (24, 26, 30))
dr2 = ImageDraw.Draw(img2)
AX, AY, AW, AH = 30, 40, 1000, 480


def A(u, v):
    return (AX + u * AW, AY + v * AH)


for k in range(17):
    dr2.line([A(k * TILE_U, 0), A(k * TILE_U, 1)], fill=(48, 50, 56))
for k in range(33):
    dr2.line([A(0, k * TILE_V), A(1, k * TILE_V)], fill=(48, 50, 56))
COLS = {36: (90, 220, 140), 37: (80, 160, 245), 38: (245, 170, 70),
        59: (200, 200, 205), 0: (245, 235, 90), 62: (230, 90, 200)}
for (bx, by) in X.list_blocks(disc=1):
    try:
        tri_idx, topo, V, U, deg, ET, fnorm = load(bx, by)
    except ValueError:
        continue
    for t in deg:
        if topo[t] in WALL_CLASSES or topo[t] not in COLS:
            continue
        for i in tri_idx[t]:
            x, y = A(U[i][0], U[i][1])
            dr2.ellipse([x - 1, y - 1, x + 1, y + 1], fill=COLS[topo[t]])
dr2.text((10, 6), "curtain uv vs the atlas tile grid (disc-1, all plan-degenerate tris "
         "outside wall classes 49/58):", fill=(220, 220, 220))
dr2.text((10, 22), "blue=37 forest  green=36 plateau-forest  orange=38 desert-veg  "
         "white=59  yellow=0  magenta=62  -- pinned per-family strips",
         fill=(170, 170, 180))
img2.save(PNG_ATLAS)
print(f"\nrenders -> {PNG_PLAN}\n           {PNG_ATLAS}")

OUT.write_text(json.dumps(dict(
    q1_rim_map=dict(
        donor=list(DONOR), n_curtain=len(drops), n_surface=len(surf),
        top_y=[round(min(tops_y), 2), round(max(tops_y), 2)],
        bottom_y=[round(min(bots_y), 2), round(max(bots_y), 2)],
        drops=[min(drops), med(drops), max(drops)],
        raw_ids_curtain={str(k): v for k, v in raw_ids_cur.items()},
        raw_ids_surface={str(k): v for k, v in raw_ids_surf.items()},
        plan_owner_signature_top_edges={str(k): v for k, v in sig.items()},
        bottom_edge_weld=dict(bot_weld),
        edge_ownership=dict(above={str(k): v for k, v in above_cls.items()},
                            below={str(k): v for k, v in below_cls.items()})),
    q2_uv_rule=dict(
        band_continuation="REFUTED",
        shared_vert_uv=dict(continuous=n_cont, discontinuous=n_disc),
        strip_u_texels=[round(min(us_all) * 1024, 1), round(max(us_all) * 1024, 1)],
        strip_v_texels=[round(min(vs_all) * 1024, 1), round(max(vs_all) * 1024, 1)],
        v_top_pin_texels=[[k, v] for k, v in v_top_pin.most_common(3)],
        v_bot_pin_texels=[[k, v] for k, v in v_bot_pin.most_common(3)],
        v_rate="none: v_top/v_bot PINNED, strip stretched over the drop",
        u_rate_per_unit=dict(med=round(med(rates), 4),
                             p10=round(rates[len(rates) // 10], 4),
                             p90=round(rates[9 * len(rates) // 10], 4)),
        u_anchors_texels=[[k, v] for k, v in u_anchor.most_common(6)],
        adj_u=dict(same=adj_u[0], different=adj_u[1]),
        surface_tiles=[[list(k), v] for k, v in surf_tiles.most_common(4)],
        ground_tiles=[[list(k), v] for k, v in gnd_tiles.most_common(4)]),
    q3_generality=dict(
        degenerate_census={str(k): v for k, v in fam_n.items()},
        forest_blocks=blk_rows,
        families={str(fam): dict(
            n=sum(fam_pin[fam].values()),
            v_pins=[[list(k), v] for k, v in fam_pin[fam].most_common(4)],
            u_texels=[round(min(fam_u[fam]) * 1024), round(max(fam_u[fam]) * 1024)],
            drops=[min(fam_drop[fam]), med(fam_drop[fam]), max(fam_drop[fam])],
            above={str(k): v for k, v in fam_above[fam].items()},
            below={str(k): v for k, v in fam_below[fam].items()},
            uv_cont=fam_cont[fam]) for fam in fam_pin},
        rim_census=dict(rim_census),
        winding=dict(outward=wind[0], inward=wind[1]),
        bottom_vert_plan_twin=dict(yes=n_vert_col[0], no=n_vert_col[1])),
    q4_recipe=dict(
        verts="per rim segment a vertical quad: top edge welded to surface rim; bottom "
              "verts at the same plan positions welded into the ground sheet",
        topograph="the SURFACE family's (37 forest / 36 plateau-forest / 38 desert-veg)",
        uv=dict(strip="dedicated, uv-discontinuous with both neighbors",
                forest=dict(u_texels=[115, 241], v_top=930, v_bot=961,
                            u_stations=[115, 179, 241]),
                desert38=dict(u_texels=[738, 869], v_rows=[548, 580, 611]),
                v_law="pin v_top/v_bot, stretch over the drop",
                u_law="~15 texels/u along the run, ~one 64-texel tile per ~4.1u, "
                      "3/4 of seams continuous"),
        winding="plan-normal OUTWARD (723/725 in stock)",
        drop_domain_u=[1.9, 2.9]),
    limits=[
        "disc-1 terrain part only; sea/beach/object parts not scanned",
        "plan-degenerate threshold |ny|<=0.05 or plan_area<1e-3*area3D -- faces between "
        "0.05<|ny|<=0.2 belong to C1's census, not re-measured here",
        "rim-seal census is per-block: cross-block seams counted as block-border, "
        "not followed into the neighbor",
        "u law is statistical (anchors + rate + 77% seam continuity), not a "
        "deterministic unwrap algorithm",
        "the atlas texture itself was not read; strip rects are uv-space only"]),
    indent=0))
print(f"artifact -> {OUT}")
