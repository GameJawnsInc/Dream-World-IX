"""VERIFIER (adversarial) -- independent re-derivations and counterexample hunts for lane
gap_inplace_stitch_composition. Read-only on the install; reads the lane's out/*.json and the scratch compose
folder the (re-run) composition_probe.py wrote. Writes out/verify_claims.json.

  V-S2   per-block Terrain weld totals (5,648/49,419 & 5,704/49,950) + partner block counts, from the census JSON
  V-S11  unit check: 1,222 is a weld-PAIR count -- how many UNIQUE Terrain positions weld to a part outside PARTS?
  V-S15  any stock mesh in column 23 / row 19?
  V-S13  (a) every uncovered Terrain border stretch closed by another part? (interval union, recomputed)
         (b) the 7 open pairs' open edges: are they vertical (same along-coordinate) wall edges ending at the border?
  V-S7   Treno gate: an ENGINE-FAITHFUL re-implementation of WMBlock.Raycast/WMPhysics.Raycast/intersect3D_
         RayTriangle (registration order, buffer order, idall skip, up-facing filter, 0x31EE veto) on stock and on
         the REAL writer's deform (mesh.deform_radial on a read_block copy); plus the cache caveat.
  V-S8   exposure restricted to samples that actually lie on a Terrain tri (the lane samples every 4u lattice point
         of a land-BEARING block, water included).
  V-S17  mesh.weld_audit on the stock disc-4 (18,4) PARTS meshes, split by transplant._split_frame_pairs.
  V-S5   independent torn-weld recount on the re-run F3 deploy (rounded 1e-4 keying, not exact keys).
  V-WALK placement.WALK_OK == the topographs set in the engine's on-foot limit mask.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
import stitch_census as C                              # noqa: E402
import border_closure as BC                            # noqa: E402
from ff9mapkit.world import extract as X               # noqa: E402
from ff9mapkit.world import mesh as KM                 # noqa: E402
from ff9mapkit.world import placement as P             # noqa: E402
from ff9mapkit.world import transplant as TR           # noqa: E402

res = {}
cen = json.loads((S.OUT / "stitch_census.json").read_text(encoding="utf-8"))
M1 = S.load_disc(1)
M4 = S.load_disc(4)

# ------------------------------------------------------------------ V-S2 -------------------------------------
for d in (1, 4):
    pb = cen[f"disc{d}"]["per_block_terrain_partners"]
    tot = sum(v["terrain_positions"] for v in pb.values())
    wnt = sum(v.get("welded_nonterrain", 0) for v in pb.values())
    blocks_with = Counter()
    for v in pb.values():
        for k in v:
            if "@" in k:
                blocks_with[k.split("@")[0]] += 0          # placeholder to list keys
        parts = {k.split("@")[0] for k in v if "@" in k}
        for p in parts:
            blocks_with[p] += 1
    res[f"S2_disc{d}"] = {"terrain_positions_sum": tot, "welded_nonterrain_sum": wnt,
                          "frac": round(wnt / tot, 4), "blocks_with_partner": dict(blocks_with.most_common())}
    print(f"V-S2 disc {d}: welded-to-non-Terrain {wnt} of {tot} ({wnt / tot:.1%}); blocks with partner "
          f"{dict(blocks_with.most_common(14))}")

# ------------------------------------------------------------------ V-S11 ------------------------------------
for d, M in ((1, M1), (4, M4)):
    owners = defaultdict(set)
    for k, m in M.items():
        for p in m.wv:
            owners[S.wrap_key(p)].add(k)
    outside = Counter()
    uniq = set()
    for k, m in M.items():
        if k[2] != "terrain":
            continue
        for p in set(m.wv):
            wk = S.wrap_key(p)
            parts = {o[2] for o in owners[wk]} - {"terrain"}
            ext = parts - set(TR.PARTS)
            if ext:
                uniq.add(wk)
                for q in ext:
                    outside[q] += 1
    res[f"S11_disc{d}"] = {"unique_terrain_positions_welded_outside_PARTS": len(uniq),
                           "by_part_unique_positions(per terrain owner)": dict(outside)}
    print(f"V-S11 disc {d}: UNIQUE wrapped positions where Terrain welds a part outside PARTS = {len(uniq)} "
          f"(lane's 1,222/1,259 is the weld-PAIR count); per-part {dict(outside)}")

# ------------------------------------------------------------------ V-S15 ------------------------------------
for d, M in ((1, M1), (4, M4)):
    c23 = sorted({(x, y) for (x, y, p) in M if x == 23})
    r19 = sorted({(x, y) for (x, y, p) in M if y == 19})
    c0 = sorted({(x, y) for (x, y, p) in M if x == 0})
    r0 = sorted({(x, y) for (x, y, p) in M if y == 0})
    res[f"S15_disc{d}"] = {"col23": c23, "row19": r19, "col0_any_part": c0, "row0_any_part": r0}
    print(f"V-S15 disc {d}: meshes in col 23 {c23}, row 19 {r19}; col 0 {c0}; row 0 {r0}")

# ------------------------------------------------------------------ V-S13 ------------------------------------
def union(ivs):
    ivs = sorted([list(v) for v in ivs])
    out = []
    for a, b in ivs:
        if out and a <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


for d, M in ((1, M1), (4, M4)):
    resid_rows = []
    tot_unc = 0.0
    for r in cen[f"disc{d}"]["borders"]:
        for who, blk, side in (("A_only", tuple(r["b"][:2]), r["b"][2]), ("B_only", tuple(r["a"][:2]), r["a"][2])):
            st = r[f"uncovered_{who}"]
            if not st:
                continue
            tot_unc += sum(b - a for a, b in st)
            cov = []
            for (bx, by, p) in M:
                if (bx, by) != blk or p == "terrain":
                    continue
                cov += C.border_profile(M, blk, side, part=p)["cover"]
            rem = C.subtract(st, union(cov))
            rl = sum(b - a for a, b in rem)
            if rl > 1e-4:
                resid_rows.append({"a": r["a"], "b": r["b"], "who": who, "residual": round(rl, 3), "rem": rem})
    res[f"S13a_disc{d}"] = {"uncovered_total": round(tot_unc, 2), "rows_with_residual": resid_rows}
    print(f"V-S13a disc {d}: uncovered Terrain stretch total {tot_unc:.2f}u; stretches NOT covered by another "
          f"part: {len(resid_rows)} {resid_rows[:5]}")

bcj = json.loads((S.OUT / "border_closure.json").read_text(encoding="utf-8"))
edges_report = []
for row in bcj["disc1"]["open_rows"]:
    (x, y, side), (nx, ny, opp) = row["a"], row["b"]
    EA, EB = BC.crossing_edges(M1, (x, y), side), BC.crossing_edges(M1, (nx, ny), opp)
    cu = BC.curtains(M1, (x, y), side) + BC.curtains(M1, (nx, ny), opp)
    ck = BC.corner_closer(M1, (x, y), side)
    for lab, o in (("A", BC.open_stretches(EA, EB, cu, ck)), ("B", BC.open_stretches(EB, EA, cu, ck))):
        for e in o:
            vertical = abs(e["a"][0] - e["b"][0]) < 1e-6
            at_end = min(abs(e["a"][0]), abs(e["a"][0] - 64), abs(e["a"][0] + 64)) < 1e-6
            edges_report.append({"pair": [row["a"], row["b"]], "side": lab, "part": e["part"],
                                 "a": e["a"], "b": e["b"], "vertical_in_plane": vertical,
                                 "along_at_block_corner": at_end, "open_len": round(e["open_len"], 3)})
res["S13b_open_edges_disc1"] = edges_report
nv = sum(1 for e in edges_report if e["vertical_in_plane"])
print(f"V-S13b disc 1: {len(edges_report)} open edges; vertical-in-plane {nv}; examples:")
for e in edges_report:
    print("    ", e)

# ------------------------------------------------------------------ V-S7 -------------------------------------
REG = ["object", "terrain", "volcanocrater", "volcanolava", "beach1", "beach2", "stream", "river", "riverjoint",
       "falls", "sea1", "sea2", "sea3", "sea4", "sea5", "sea6"]


def ray_tri(o, d, p0, p1, p2):
    """intersect3D_RayTriangle (WMPhysics.cs:71-120), float64."""
    u = [p1[i] - p0[i] for i in range(3)]
    v = [p2[i] - p0[i] for i in range(3)]
    n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    if n == [0.0, 0.0, 0.0]:
        return -1, None
    w0 = [o[i] - p0[i] for i in range(3)]
    a = -sum(n[i] * w0[i] for i in range(3))
    b = sum(n[i] * d[i] for i in range(3))
    if abs(b) < 1e-8:
        return (2 if a == 0 else 0), None
    r = a / b
    if r < 0:
        return 0, None
    I = [o[i] + r * d[i] for i in range(3)]
    uu = sum(x * x for x in u); uv = sum(u[i] * v[i] for i in range(3)); vv = sum(x * x for x in v)
    w = [I[i] - p0[i] for i in range(3)]
    wu = sum(w[i] * u[i] for i in range(3)); wv = sum(w[i] * v[i] for i in range(3))
    D = uv * uv - uu * vv
    s = (uv * wv - vv * wu) / D
    if s < 0 or s > 1:
        return 0, None
    t = (uv * wu - uu * wv) / D
    if t < 0 or s + t > 1:
        return 0, None
    return 1, I


def engine_scan(meshes, origin):
    """WMBlock.Raycast(ray, walkMeshes) -> first mesh whose WMPhysics.Raycast hits and whose mapid != 0x31EE."""
    d = (0.0, -1.0, 0.0)
    for name, verts, fi, idall in meshes:
        hit = None
        for t in range(len(fi) // 3):
            ida = idall[fi[3 * t]]
            if ida in (4078, 4088, 2040):
                continue
            p0, p1, p2 = verts[fi[3 * t]], verts[fi[3 * t + 1]], verts[fi[3 * t + 2]]
            cx = [p1[i] - p0[i] for i in range(3)]
            cy = [p2[i] - p0[i] for i in range(3)]
            nrm = [cx[1] * cy[2] - cx[2] * cy[1], cx[2] * cy[0] - cx[0] * cy[2], cx[0] * cy[1] - cx[1] * cy[0]]
            L = math.sqrt(sum(x * x for x in nrm)) or 1.0
            if nrm[1] / L <= 0.1:
                continue
            k, I = ray_tri(origin, d, p0, p1, p2)
            if k == 1:
                hit = (t, I[1], ida)
                break
        if hit is not None:
            if hit[2] == 0x31EE:
                continue
            return name, hit[0], hit[1], hit[2]
    return None


def all_hits(meshes, x, z):
    out = []
    for order, (name, verts, fi, idall) in enumerate(meshes):
        for t in range(len(fi) // 3):
            p0, p1, p2 = verts[fi[3 * t]], verts[fi[3 * t + 1]], verts[fi[3 * t + 2]]
            k, I = ray_tri((x, 1000.0, z), (0.0, -1.0, 0.0), p0, p1, p2)
            if k == 1:
                cx = [p1[i] - p0[i] for i in range(3)]
                cy = [p2[i] - p0[i] for i in range(3)]
                nrm = [cx[1] * cy[2] - cx[2] * cy[1], cx[2] * cy[0] - cx[0] * cy[2], cx[0] * cy[1] - cx[1] * cy[0]]
                L = math.sqrt(sum(q * q for q in nrm)) or 1.0
                out.append({"mesh": name, "mesh_order": order, "tri": t, "y": round(I[1], 4),
                            "topo": S.topo(idall[fi[3 * t]]), "idall": idall[fi[3 * t]],
                            "up_facing": nrm[1] / L > 0.1})
    return out


blk = (19, 14)
ox, oz = blk[0] * 64.0, -blk[1] * 64.0
ter_bm = X.read_block(blk[0], blk[1], disc=1, part="terrain", game=S.GAME)
pre_y = [v[1] for v in ter_bm.verts]
KM.deform_radial(ter_bm, amount=1.0, radius=8.0, center=(1274.219, -954.016), falloff="smooth",
                 world_origin=X.block_world_origin(*blk))
raised = [tuple(v) for v in ter_bm.verts]
stock_ter = M1[(blk[0], blk[1], "terrain")]
assert len(raised) == len(stock_ter.lv) and all(abs(a[0] - b[0]) < 1e-6 and abs(a[2] - b[2]) < 1e-6
                                                for a, b in zip(raised, stock_ter.lv)), "slot order"


def meshes_for(terrain_verts):
    out = []
    for p in REG:
        m = M1.get((blk[0], blk[1], p))
        if m is None:
            continue
        v = terrain_verts if p == "terrain" else m.lv
        out.append((p, v, m.fi, m.idall))
    return out


ms_stock, ms_raised = meshes_for(stock_ter.lv), meshes_for(raised)
WALK = P.WALK_OK
pd = json.loads((S.OUT / "probe_detail.json").read_text(encoding="utf-8"))
s7 = []
for w in pd["P2_treno_gate_plus1"]["walls"] if "P2_treno_gate_plus1" in pd else []:
    pass
# the lane's 4 wall examples (world coords) -- recompute every one
cases = [((1277.6, -951.19), (1278.38, -951.32)), ((1277.98, -950.92), (1278.38, -951.32)),
         ((1278.98, -951.0), (1278.35, -951.32))]
for (fx, fz), (tx, tz) in cases:
    row = {"from": [fx, fz], "to": [tx, tz]}
    for lab, ms in (("stock", ms_stock), ("raised", ms_raised)):
        lfx, lfz, ltx, ltz = fx - ox, fz - oz, tx - ox, tz - oz
        st = engine_scan(ms, (lfx, 400.0, lfz))
        if st is None:
            row[lab] = "start-miss"
            continue
        sname, stri, sy, sida = st
        stopo = S.topo(sida)
        slice_ = -1.171875 if stopo in (36, 37, 38) else 0.0
        actor = sy + slice_
        step = engine_scan(ms, (ltx, actor + 2.34375, ltz))
        legal = step is not None and S.topo(step[3]) in WALK
        row[lab] = {"start": [sname, stri, round(sy, 4), stopo], "actor_y": round(actor, 4),
                    "ray_origin": round(actor + 2.34375, 4),
                    "step_hit": None if step is None else [step[0], step[1], round(step[2], 4), S.topo(step[3])],
                    "legal": legal}
    # cache caveat: if the walkable sheet the stock step grounded on is cached, RaycastOnSpecifiedTriangle
    # (no up-facing/idall filter) is tested BEFORE the scan
    if isinstance(row.get("stock"), dict) and row["stock"]["step_hit"] and isinstance(row.get("raised"), dict):
        sh = row["stock"]["step_hit"]
        ms = dict((n, (v, f, i)) for n, v, f, i in ms_raised)
        v, f, i = ms[sh[0]]
        k, I = ray_tri((tx - ox, row["raised"]["ray_origin"], tz - oz), (0, -1, 0),
                       v[f[3 * sh[1]]], v[f[3 * sh[1] + 1]], v[f[3 * sh[1] + 2]])
        row["cache_rescue_if_stock_step_tri_cached"] = (k != 0)
    row["all_sheets_at_target_stock"] = all_hits(ms_stock, tx - ox, tz - oz)
    s7.append(row)
res["S7_engine_faithful"] = s7
for r in s7:
    print(f"V-S7 {r['from']}->{r['to']}: stock {r['stock'] if isinstance(r['stock'], str) else (r['stock']['legal'], r['stock']['step_hit'], r['stock']['ray_origin'])} | "
          f"raised {r['raised'] if isinstance(r['raised'], str) else (r['raised']['legal'], r['raised']['step_hit'], r['raised']['ray_origin'])} | "
          f"cache-rescue {r.get('cache_rescue_if_stock_step_tri_cached')}")
print("    sheets at target (stock):", [(h['mesh'], h['tri'], h['y'], h['topo'], h['up_facing']) for h in s7[0]["all_sheets_at_target_stock"]])

# ------------------------------------------------------------------ V-S8 -------------------------------------
from ff9mapkit.world.mesh import _falloff                # noqa: E402


def tmax(A):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if abs(A) * _falloff(mid) > S.TOL:
            lo = mid
        else:
            hi = mid
    return lo


def on_terrain(m, lx, lz, grid):
    for t in grid.get((math.floor(lx / 4), math.floor(lz / 4)), ()):
        a, b, c = (m.lv[m.fi[3 * t + k]] for k in range(3))
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        w0 = ((b[2] - c[2]) * (lx - c[0]) + (c[0] - b[0]) * (lz - c[2])) / d
        w1 = ((c[2] - a[2]) * (lx - c[0]) + (a[0] - c[0]) * (lz - c[2])) / d
        if min(w0, w1, 1 - w0 - w1) >= -1e-9:
            return S.topo(m.tri_idall(t))
    return None


for d, M in ((1, M1), (4, M4)):
    owners = defaultdict(set)
    for k, m in M.items():
        for p in m.wv:
            owners[S.wrap_key(p)].add(k)
    pts_any, pts_walk = [], []
    for (x, y, p), m in M.items():
        if p != "terrain":
            continue
        for wp in set(m.wv):
            o = {q[2] for q in owners[S.wrap_key(wp)]} - {"terrain"}
            if o:
                pts_any.append((wp[0], wp[2]))
                if o & {"beach1", "beach2", "object"}:
                    pts_walk.append((wp[0], wp[2]))
    G = {}
    for lab, pts in (("any", pts_any), ("walk", pts_walk)):
        g = defaultdict(list)
        for q in pts:
            g[(math.floor(q[0] / 16), math.floor(q[1] / 16))].append(q)
        G[lab] = g

    def near(g, x, z, r):
        for gx in range(math.floor((x - r) / 16), math.floor((x + r) / 16) + 1):
            for gz in range(math.floor((z - r) / 16), math.floor((z + r) / 16) + 1):
                for (px, pz) in g.get((gx, gz), ()):
                    if (px - x) ** 2 + (pz - z) ** 2 < r * r:
                        return True
        return False
    samples_all, samples_land, samples_walkland = [], [], []
    for (x, y, p), m in M.items():
        if p != "terrain":
            continue
        grid = defaultdict(list)
        for t in range(m.ntri):
            cs = [m.lv[m.fi[3 * t + k]] for k in range(3)]
            for gx in range(math.floor(min(c[0] for c in cs) / 4), math.floor(max(c[0] for c in cs) / 4) + 1):
                for gz in range(math.floor(min(c[2] for c in cs) / 4), math.floor(max(c[2] for c in cs) / 4) + 1):
                    grid[(gx, gz)].append(t)
        for i in range(16):
            for j in range(16):
                lx, lz = 2 + 4 * i, -(2 + 4 * j)
                wx, wz = x * 64 + lx, -(y * 64) + lz
                samples_all.append((wx, wz))
                tp = on_terrain(m, lx, lz, grid)
                if tp is not None:
                    samples_land.append((wx, wz))
                    if tp in WALK:
                        samples_walkland.append((wx, wz))
    rows = {}
    for A in (1.0, 3.0):
        tm = tmax(A)
        for R in (8.0, 16.0, 96.0):
            r = tm * R
            rows[f"A{A:g}_R{R:g}"] = {
                lab: {"n": len(ss), "tears_any": round(sum(1 for (x, z) in ss if near(G["any"], x, z, r)) / len(ss), 4),
                      "tears_walkable": round(sum(1 for (x, z) in ss if near(G["walk"], x, z, r)) / len(ss), 4)}
                for lab, ss in (("lane_all_lattice", samples_all), ("on_terrain_tri", samples_land),
                                ("on_walkable_terrain", samples_walkland))}
    res[f"S8_disc{d}"] = rows
    print(f"V-S8 disc {d}: lattice {len(samples_all)}, on a Terrain tri {len(samples_land)}, on walkable Terrain "
          f"{len(samples_walkland)}")
    for k, v in rows.items():
        print(f"    {k}: " + "; ".join(f"{lab} any {q['tears_any']:.1%} walk {q['tears_walkable']:.1%}"
                                       for lab, q in v.items()))

# ------------------------------------------------------------------ V-S17 ------------------------------------
class _BM:
    def __init__(self, verts):
        self.verts = verts


for d, M in ((1, M1), (4, M4)):
    ms = [_BM(M[(18, 4, p)].lv) for p in TR.PARTS if (18, 4, p) in M]
    pairs = KM.weld_audit(ms)
    inn, fr = TR._split_frame_pairs(pairs, (0.0, 64.0), (0.0, -64.0))
    res[f"S17_disc{d}_18_4"] = {"parts": [p for p in TR.PARTS if (18, 4, p) in M], "pairs": len(pairs),
                                "interior": len(inn), "frame": len(fr), "examples": inn[:4]}
    print(f"V-S17 disc {d} (18,4) PARTS {[p for p in TR.PARTS if (18, 4, p) in M]}: weld_audit pairs {len(pairs)} "
          f"(interior {len(inn)}, frame {len(fr)}) {inn[:3]}")
# all disc-4 blocks: which carry interior weld_audit pairs among PARTS on unmodified stock?
bad = {}
for (x, y) in sorted({(k[0], k[1]) for k in M4}):
    ms = [_BM(M4[(x, y, p)].lv) for p in TR.PARTS if (x, y, p) in M4]
    if not ms:
        continue
    inn, fr = TR._split_frame_pairs(KM.weld_audit(ms), (0.0, 64.0), (0.0, -64.0))
    if inn:
        bad[f"{x},{y}"] = len(inn)
res["S17_disc4_blocks_with_interior_pairs"] = bad
print("V-S17 disc-4 blocks whose stock PARTS fail weld_audit's interior gate:", bad)

# ------------------------------------------------------------------ V-S5 -------------------------------------
comp = json.loads((S.OUT / "composition_probe.json").read_text(encoding="utf-8"))
root = Path(comp["scratch_root"]) / "F3_beach_reshape" / "FF9CustomMap-probe"
torn, torn_pos = Counter(), 0
for f in sorted(root.rglob("*Terrain.ff9mesh")):
    import re as _re
    mm = _re.search(r"Block\[(\d+)\]\[(\d+)\]", f.name)
    bx, by = int(mm.group(1)), int(mm.group(2))
    dep = KM.read_ff9mesh(f)
    st = M1[(bx, by, "terrain")]
    key = lambda p: (round(p[0], 4), round(p[1], 4), round(p[2], 4))
    partner = defaultdict(set)
    for (x, y, p), m in M1.items():
        if p == "terrain" or max(abs(x - bx), abs(y - by)) > 1:
            continue
        for wp in m.wv:
            partner[key(wp)].add(p)
    done = set()
    for lv0, dv in zip(st.lv, dep["verts"]):
        wp = key((lv0[0] + bx * 64, lv0[1], lv0[2] - by * 64))
        if wp in done:
            continue
        done.add(wp)
        if partner.get(wp) and abs(dv[1] - lv0[1]) > 0.05:
            torn_pos += 1
            for p in partner[wp]:
                torn[p] += 1
res["S5_independent_recount"] = {"files": [str(f) for f in root.rglob("*.ff9mesh")], "torn_positions": torn_pos,
                                 "by_partner": dict(torn)}
print(f"V-S5 independent recount on the deployed bytes (rounded keys): torn positions {torn_pos} {dict(torn)}")

# ------------------------------------------------------------------ V-WALK -----------------------------------
mask = frozenset(t for t in range(64)
                 if (((0x0010667F >> (t - 32)) & 1) if t >= 32 else ((0xD8FF3CFF >> t) & 1)))
res["WALK_OK_equals_engine_mask"] = (mask == P.WALK_OK)
print("V-WALK placement.WALK_OK == engine on-foot mask:", mask == P.WALK_OK, sorted(mask ^ P.WALK_OK))

out = S.OUT / "verify_claims.json"
out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print("->", out)
