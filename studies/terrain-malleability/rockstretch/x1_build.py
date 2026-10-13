"""X1 -- ROCK STRETCH TOLERANCE (README 7.1 rank 9, uvclass NOTES "Open items"): the build, offline.

The bench is the verbatim Uaho block carried whole onto the Path D world: Disc9 cell (13,15) in FF9CustomMap-world
(Donor.txt 0,0, so its alcove roof is the stock prefab's own Object). Its rock (topograph 49, 134 tris) is stretched
pure-Y about its rim by x1.25 / x1.5 / x2.0, UV carried; everything else stays byte-identical.

The map: y' = b(x,z) + s * (y - b(x,z)) on every FREE rock position, where
  - PINNED rock positions never move: the 26 the rock shares with grass / forest / cliff tris (its foot welds) and
    the 4 on the Terrain's open edges (the alcove aperture the prefab Object closes);
  - b is the least-squares plane through the pinned positions plus an inverse-distance blend of their residuals, so
    b equals the rim height AT every pinned position and the rim never moves.
Welds are by POSITION (THE ENTRY-VS-POSITION LAW), so the map is applied per unique position to every entry there.
Normals take the map's inverse transpose (the Terrain shader binds none; kept consistent anyway); UVs and tangents
(IDALL) are verbatim.

Registered prediction (uvclass NOTES, X1): x1.25 reads like the rigid carry (95.4% of M.flow inside the stock
envelope under a pure height scale), x1.5 borderline (89.9%), x2.0 visibly stretched (63.5%). This script reports the
same survival number for THESE 134 tris under THIS map (the rim pin adds a small shear a pure scale does not have).
It cannot separate the variants here: Uaho's rock is mostly M.free (114 of 134 tris), not M.flow, and the rigid
carry itself scores ~66% on the M.flow envelope. So the build also reports the direct measure, each rock tri's
texture stretch against the rigid carry (UV carried, the principal stretch IS the texel stretch).

Gates (any failure refuses to write):
  G1 identity: s = 1.0 through the pipeline reproduces the live file byte for byte;
  G2 only free rock entries change: every other entry (position, normal, uv, tangent) byte-identical;
  G3 welds: no position shared with a non-rock tri moves; the open-edge (once-edge) set is unchanged;
  G4 no rock tri flips its facing (geometric normal y sign) and none degenerates;
  G5 the prefab Object's vertices still coincide with Terrain positions (the alcove roof stays closed).

Also picks the stills' viewpoints: plain-grass homes off the 4u lattice, with clear grass toward the massif.

Writes out/x1/<variant>/FF9_Data/WorldMap/Disc9/0_1/r15/Block[13][15] Terrain.ff9mesh and out/x1/build.json.
Rerun: py studies/terrain-malleability/rockstretch/x1_build.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__   # this tree's kit, not master's
from ff9mapkit.world import extract as X, mesh as M, transplant as TR  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LIVE = "FF9CustomMap-world"
DISC, BX, BY = 9, 13, 15
DONOR = (0, 0)                        # Donor.txt: the Uaho block's own prefab (its Object rides along)
ROCK = 49
SCALES = {"s125": 1.25, "s150": 1.5, "s200": 2.0}
PRED = {"s125": 95.4, "s150": 89.9, "s200": 63.5}   # uvclass NOTES X1 (M.flow, pure height scale)
MAIN_UVCLASS = Path(r"C:\gd\Dream-World-IX\studies\terrain-malleability\uvclass\out")   # gitignored census output
OUT = HERE / "out" / "x1"
REL = M.override_relpath(DISC, BX, BY)
IDW_POWER = 2.0
OX, OZ = BX * 64.0, -BY * 64.0        # block-local -> world


def key(p):
    return (round(float(p[0]), 4), round(float(p[1]), 4), round(float(p[2]), 4))


def topo_of(tan):
    return X.decode_id(int(round(tan[0])))["topograph"]


def load_live():
    path = GAME / LIVE / REL
    d = M.read_ff9mesh(path)
    return path, d


def anatomy(d):
    V = np.asarray(d["verts"], float)
    idx = np.asarray(d["indices"]).reshape(-1, 3)
    topo = np.array([topo_of(d["tangents"][t[0]]) for t in idx])
    rock_pos, other_pos = set(), set()
    for t, tp in zip(idx, topo):
        for k in t:
            (rock_pos if tp == ROCK else other_pos).add(key(V[k]))
    edges = Counter()
    for t in idx:
        ks = [key(V[k]) for k in t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges[tuple(sorted((ks[a], ks[b])))] += 1
    once = {e for e, c in edges.items() if c == 1}
    once_pos = {p for e in once for p in e}
    pinned = (rock_pos & other_pos) | (rock_pos & once_pos)
    free = rock_pos - pinned
    return dict(V=V, idx=idx, topo=topo, rock_pos=rock_pos, other_pos=other_pos, once=once,
                pinned=pinned, free=free)


def base_field(pinned):
    """b(x,z) = least-squares plane through the pinned positions + an IDW blend of their residuals (exact at them)."""
    P = np.array(sorted(pinned))
    A = np.c_[P[:, 0], P[:, 2], np.ones(len(P))]
    coef, *_ = np.linalg.lstsq(A, P[:, 1], rcond=None)
    res = P[:, 1] - A @ coef

    def b(x, z):
        d2 = (P[:, 0] - x) ** 2 + (P[:, 2] - z) ** 2
        plane = coef[0] * x + coef[1] * z + coef[2]
        if d2.min() < 1e-12:
            return float(plane + res[int(d2.argmin())])
        w = d2 ** (-IDW_POWER / 2.0)
        return float(plane + (w * res).sum() / w.sum())

    tilt = math.degrees(math.atan(math.hypot(coef[0], coef[1])))
    return b, {"plane": [round(float(c), 5) for c in coef], "tilt_deg": round(tilt, 2),
               "residual_max": round(float(np.abs(res).max()), 3)}


def stretch(d, an, s, b):
    """A copy of the mesh dict with every free rock entry mapped y' = b + s(y - b). b is a pure function of plan
    position, so coincident entries (one weld) map to one point."""
    h = 1e-3
    verts = [list(v) for v in d["verts"]]
    normals = [list(n) for n in d["normals"]] if d["normals"] else None
    for k, v in enumerate(d["verts"]):
        if key(v) not in an["free"]:
            continue
        x, y, z = v
        bb = b(x, z)
        verts[k] = [x, y + (s - 1.0) * (y - bb), z]       # = b + s(y - b), exact at s = 1 (G1)
        if normals is not None:
            bx_ = (b(x + h, z) - b(x - h, z)) / (2 * h)
            bz_ = (b(x, z + h) - b(x, z - h)) / (2 * h)
            a_, c_ = (1 - s) * bx_, (1 - s) * bz_      # J = [[1,0,0],[a,s,c],[0,0,1]]  ->  n' ~ J^-T n
            nx, ny, nz = normals[k]
            m = np.array([nx - a_ * ny / s, ny / s, nz - c_ * ny / s])
            ln = math.sqrt(nx * nx + ny * ny + nz * nz)
            normals[k] = (m * (ln / (np.linalg.norm(m) or 1.0))).tolist()   # the original length: exact at s = 1
    out = dict(d)
    out["verts"], out["normals"] = verts, normals
    return out


def write(d, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    chan, channels = {CH_POS: d["verts"]}, {CH_POS: (0, 3)}
    if d["normals"]:
        chan[CH_NRM], channels[CH_NRM] = d["normals"], (12, 3)
    if d["uvs"]:
        chan[CH_UV], channels[CH_UV] = d["uvs"], (24, 2)
    if d["tangents"]:
        chan[CH_TAN], channels[CH_TAN] = d["tangents"], (32, 4)
    idx = list(d["indices"])
    m = BlockMesh(name=f"Block[{BX}][{BY}] Terrain", disc=DISC, x=BX, y=BY, lod="0_1", vcount=d["vcount"],
                  stride=48, channels=channels, chan_arrays=chan, flat_index=idx,
                  tris=[idx[i:i + 3] for i in range(0, len(idx), 3)], raw_vbuf=b"", raw_ibuf=b"", use32=True,
                  submeshes=[])
    return M.write_ff9mesh(m, path)


def tri_normal(P):
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    return n, 0.5 * np.linalg.norm(n, axis=1)


def jac_stats(P, UV):
    """Per-tri texel density (px/u) and anisotropy, the uvclass definition (Moguri atlas 2048 x 4096)."""
    T = np.stack([UV[..., 0] * 2048.0, UV[..., 1] * 4096.0], axis=-1)
    e1, e2 = P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]
    D = np.stack([T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]], axis=2)
    J = D @ np.linalg.pinv(np.stack([e1, e2], axis=2))
    sv = np.linalg.svd(J, compute_uv=False)
    return np.sqrt(sv[:, 0] * sv[:, 1]), sv[:, 0] / np.maximum(sv[:, 1], 1e-9)


def mflow_envelope():
    """M.flow's stock envelope exactly as uvc_deform.py takes it (density p1..p99, anisotropy <= p99, tris with
    area > 0.05), from the census output in the main repo (gitignored) and the shared disc-1 terrain cache."""
    import os
    cache = Path(os.environ.get("TEMP", ".")) / "ff9_uvclass_cache" / "disc1_terrain.npz"
    z = np.load(cache)
    P, UV, BLK = z["P"], z["UV"], z["BLK"]
    sub = np.load(MAIN_UVCLASS / "classes_terrain.npz")["sub"]
    assert len(sub) == len(P), (len(sub), len(P))
    dens, aniso = jac_stats(P, UV)
    _, area = tri_normal(P)
    ok = (area > 0.05) & np.isfinite(dens)
    m = ok & (sub == "M.flow")
    env = {"dens_lo": float(np.percentile(dens[m], 1)), "dens_hi": float(np.percentile(dens[m], 99)),
           "aniso_hi": float(np.percentile(aniso[m], 99)), "tris": int(m.sum())}
    topo = (z["IDALL"] & 0xFC) >> 2
    uaho = (BLK[:, 0] == DONOR[0]) & (BLK[:, 1] == DONOR[1]) & (topo == ROCK)
    env["uaho_rock_classes"] = dict(Counter(sub[uaho].tolist()))
    return env


def survival(d, an, env, s_const=None):
    V = np.asarray(d["verts"], float)
    UV = np.asarray(d["uvs"], float)[:, :2]
    idx = an["idx"][an["topo"] == ROCK]
    P = V[idx].copy()
    if s_const is not None:                       # uvc_deform's own case: a pure height scale, no rim pin
        P[..., 1] *= s_const
    _, area = tri_normal(P)
    dens, aniso = jac_stats(P, UV[idx])
    ok = area > 0.05
    inside = (dens >= env["dens_lo"]) & (dens <= env["dens_hi"]) & (aniso <= env["aniso_hi"])
    return round(100.0 * float(inside[ok].mean()), 1), int(ok.sum())


def strain(live, var, an):
    """Per rock tri, the principal stretches of the map rigid tri -> stretched tri (UV carried, so this IS how far
    its painted texture is stretched): area-weighted p50/p90/max of the larger one, and the share of rock area
    stretched past x1.1 and x1.25."""
    V0, V1 = np.asarray(live["verts"], float), np.asarray(var["verts"], float)
    idx = an["idx"][an["topo"] == ROCK]
    P0, P1 = V0[idx], V1[idx]
    E0 = np.stack([P0[:, 1] - P0[:, 0], P0[:, 2] - P0[:, 0]], axis=2)
    E1 = np.stack([P1[:, 1] - P1[:, 0], P1[:, 2] - P1[:, 0]], axis=2)
    F = E1 @ np.linalg.pinv(E0)
    smax = np.linalg.svd(F, compute_uv=False)[:, 0]
    _, area = tri_normal(P0)
    o = np.argsort(smax)
    cw = np.cumsum(area[o]) / area.sum()
    q = lambda f: round(float(smax[o][np.searchsorted(cw, f)]), 3)  # noqa: E731
    return {"stretch_p50": q(0.5), "stretch_p90": q(0.9), "stretch_max": round(float(smax.max()), 3),
            "area_over_1.1_pct": round(100 * float(area[smax > 1.1].sum() / area.sum()), 1),
            "area_over_1.25_pct": round(100 * float(area[smax > 1.25].sum() / area.sum()), 1)}


def gates(live, var, an, s, obj_pos):
    V0, V1 = np.asarray(live["verts"], float), np.asarray(var["verts"], float)
    fails = []
    free_entries = {k for k, v in enumerate(live["verts"]) if key(v) in an["free"]}
    for k in range(live["vcount"]):
        if k in free_entries:
            continue
        if (live["verts"][k] != var["verts"][k] or live["uvs"][k] != var["uvs"][k]
                or live["tangents"][k] != var["tangents"][k] or live["normals"][k] != var["normals"][k]):
            fails.append(f"G2 entry {k} (not a free rock entry) changed")
            break
    if any(var["uvs"][k] != live["uvs"][k] or var["tangents"][k] != live["tangents"][k] for k in free_entries):
        fails.append("G2 a free rock entry changed its uv/tangent")
    moved = {key(live["verts"][k]) for k in range(live["vcount"]) if not np.allclose(V0[k], V1[k], atol=0)}
    if moved & an["other_pos"]:
        fails.append(f"G3 {len(moved & an['other_pos'])} welded positions moved")
    an1 = anatomy(var)
    if len(an1["once"]) != len(an["once"]):
        fails.append(f"G3 open edges {len(an['once'])} -> {len(an1['once'])}")
    idx = an["idx"][an["topo"] == ROCK]
    n0, a0 = tri_normal(V0[idx])
    n1, a1 = tri_normal(V1[idx])
    flips = int((np.sign(n0[:, 1]) != np.sign(n1[:, 1])).sum())
    if flips:
        fails.append(f"G4 {flips} rock tris flipped facing")
    if (a1 < 1e-4).any():
        fails.append("G4 a rock tri degenerated")
    pos1 = {key(v) for v in var["verts"]}
    open_obj = [p for p in obj_pos if p not in pos1]
    if len(open_obj) != obj_pos_missing_live(live, obj_pos):
        fails.append(f"G5 {len(open_obj)} prefab-Object vertices no longer meet the Terrain")
    return fails, {"moved_positions": len(moved), "flips": flips, "min_rock_area": round(float(a1.min()), 4)}


def obj_pos_missing_live(live, obj_pos):
    pos0 = {key(v) for v in live["verts"]}
    return sum(1 for p in obj_pos if p not in pos0)


# ------------------------------------------------------------------------------------------------ viewpoints
def ground(an, d, x, z):
    """(topograph, y) of the highest Terrain tri over block-local (x, z): the engine's down-ray, first hit."""
    V = an["V"]
    best = None
    for t, tp in zip(an["idx"], an["topo"]):
        a, b, c = V[t[0]], V[t[1]], V[t[2]]
        den = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(den) < 1e-12:
            continue
        l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / den
        l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / den
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) < -1e-9:
            continue
        y = l1 * a[1] + l2 * b[1] + l3 * c[1]
        if best is None or y > best[1]:
            best = (int(tp), float(y))
    return best


def viewpoints(an, d):
    """One plain-grass home per sector round the massif: off the 4u lattice (the lattice-edge teleport trap), 2u of
    plain grass all round, and 10u of walkable ground (grass or canopy) straight toward the rock so world_face's
    probes (~10u, home-anchored) can measure the heading."""
    R = np.array(sorted(an["rock_pos"]))
    top = R[R[:, 1].argmax()]
    cx, cz = float(R[:, 0].mean()), float(R[:, 2].mean())
    cand = []
    for x in np.arange(1.0, 63.5, 0.5):
        for z in np.arange(-63.0, -0.5, 0.5):
            if min(x % 4, 4 - x % 4) < 0.6 or min(-z % 4, 4 + z % 4) < 0.6:
                continue
            dist = math.hypot(x - cx, z - cz)
            if not 13.0 <= dist <= 26.0:
                continue
            g = ground(an, d, x, z)
            if g is None or g[0] != 0:
                continue
            if any((ground(an, d, x + 2 * math.cos(a), z + 2 * math.sin(a)) or (None,))[0] != 0
                   for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)):
                continue
            ux, uz = (cx - x) / dist, (cz - z) / dist
            path = [ground(an, d, x + ux * t, z + uz * t) for t in np.arange(1.0, 10.5, 1.0)]
            if any(p is None or p[0] not in (0, 37) for p in path):
                continue
            az = math.degrees(math.atan2(z - cz, x - cx)) % 360
            cand.append((x, z, dist, az, g[1]))
    picks = {}
    for x, z, dist, az, y in cand:
        sector = int(((az + 45) % 360) // 90)               # 0 = east of the massif, 1 = north (+z), 2 west, 3 south
        if sector not in picks or dist > picks[sector][2]:
            picks[sector] = (x, z, dist, az, y)
    names = {0: "east", 1: "north", 2: "west", 3: "south"}
    out = {}
    for sec, (x, z, dist, az, y) in sorted(picks.items()):
        wx, wz = OX + x, OZ + z
        bearing = math.degrees(math.atan2((OZ + cz) - wz, (OX + cx) - wx))
        out[names[sec]] = {"world": [round(wx, 3), round(wz, 3)], "local": [x, z], "ground_y": round(y, 4),
                           "dist_to_massif": round(dist, 2), "bearing_deg": round(bearing, 2)}
    return out, {"centroid_world": [round(OX + cx, 3), round(OZ + cz, 3)],
                 "summit_world": [round(OX + float(top[0]), 3), round(OZ + float(top[2]), 3)],
                 "summit_y": round(float(top[1]), 3), "candidates": len(cand)}


def main():
    path, live = load_live()
    raw = path.read_bytes()
    an = anatomy(live)
    obj = TR.world_tris(DONOR[0], DONOR[1], "object", disc=1)
    obj_pos = {key(v[0]) for tri in obj for v in tri}
    report = {"live": str(path), "live_sha256": hashlib.sha256(raw).hexdigest(), "vcount": live["vcount"],
              "rock_tris": int((an["topo"] == ROCK).sum()), "rock_positions": len(an["rock_pos"]),
              "pinned": len(an["pinned"]), "free": len(an["free"]),
              "pinned_welds": len(an["rock_pos"] & an["other_pos"]),
              "pinned_open_edge_only": len((an["rock_pos"] & {p for e in an["once"] for p in e}) - an["other_pos"]),
              "object_vertices": len(obj_pos), "object_vertices_on_terrain": len(obj_pos) - obj_pos_missing_live(live, obj_pos)}
    b, binfo = base_field(an["pinned"])
    report["base"] = binfo
    R = np.array(sorted(an["rock_pos"]))
    report["rock_y"] = [round(float(R[:, 1].min()), 3), round(float(R[:, 1].max()), 3)]

    # G1 identity
    ident = stretch(live, an, 1.0, b)
    tmp = OUT / "_identity" / "x.ff9mesh"
    write(ident, tmp)
    if tmp.read_bytes() != raw:
        raise SystemExit("G1 FAILED: s=1.0 through the pipeline does not reproduce the live file")
    tmp.unlink()
    tmp.parent.rmdir()
    report["G1_identity"] = "byte-identical"

    env = mflow_envelope()
    report["mflow_envelope"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in env.items()}
    report["survival_rigid"] = survival(live, an, env)[0]
    report["variants"] = {}
    for name, s in SCALES.items():
        var = stretch(live, an, s, b)
        fails, info = gates(live, var, an, s, obj_pos)
        if fails:
            raise SystemExit(f"{name}: gate FAILED: {fails}")
        V1 = np.asarray(var["verts"], float)
        top = max(V1[k][1] for k in range(var["vcount"]))
        surv, n = survival(var, an, env)
        surv_pure, _ = survival(live, an, env, s_const=s)
        st = strain(live, var, an)
        dest = OUT / name / REL
        write(var, dest)
        back = M.read_ff9mesh(dest)
        assert back["vcount"] == live["vcount"] and back["indices"] == live["indices"]
        report["variants"][name] = {"scale": s, "summit_y": round(float(top), 3), "survival_pct": surv,
                                    "survival_pure_height_scale_pct": surv_pure, "predicted_pct": PRED[name],
                                    "rock_tris_scored": n, "strain": st, **info,
                                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(), "path": str(dest)}
        print(f"{name}: x{s} summit {report['rock_y'][1]:.2f} -> {top:.2f}  texture stretch p50/p90/max "
              f"{st['stretch_p50']}/{st['stretch_p90']}/{st['stretch_max']}, rock area past x1.1 "
              f"{st['area_over_1.1_pct']}%, past x1.25 {st['area_over_1.25_pct']}%")
        print(f"       inside the M.flow envelope "
              f"{surv}% (a pure height scale: {surv_pure}%, registered {PRED[name]}%)  moved {info['moved_positions']}"
              f" positions, gates G2-G5 pass")
    # THE NUMERIC CONTROL: a teleport onto the rock near its summit reads the served file's height (topograph 49
    # has no walk sink). Off the summit vertex and off the 4u lattice; the same plan point in every variant.
    R0 = np.array(sorted(an["rock_pos"]))
    tx, tz = float(R0[R0[:, 1].argmax()][0]) + 0.37, float(R0[R0[:, 1].argmax()][2]) - 0.29
    probe = {"world": [round(OX + tx, 3), round(OZ + tz, 3)], "local": [round(tx, 3), round(tz, 3)], "y": {}}
    for name, mesh in [("rigid", live)] + [(n, M.read_ff9mesh(OUT / n / REL)) for n in SCALES]:
        g = ground(anatomy(mesh), mesh, tx, tz)
        assert g is not None and g[0] == ROCK, (name, g)
        probe["y"][name] = round(g[1], 4)
    report["probe"] = probe
    print(f"summit probe {probe['world']}: y {probe['y']}")
    vp, vinfo = viewpoints(an, live)
    report["viewpoints"], report["massif"] = vp, vinfo
    (OUT / "build.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("rock_tris", "rock_positions", "pinned", "free", "pinned_welds",
                                              "pinned_open_edge_only", "object_vertices", "object_vertices_on_terrain",
                                              "base", "rock_y", "survival_rigid", "mflow_envelope")}, indent=1))
    print(json.dumps({"massif": vinfo, "viewpoints": vp}, indent=1))
    print(f"wrote {OUT / 'build.json'}")


if __name__ == "__main__":
    main()
