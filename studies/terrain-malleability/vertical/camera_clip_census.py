"""THE CHASE-CAMERA vs TERRAIN census -- does the stock world ever put the camera eye inside terrain, or
terrain between the eye and the player? And how much vertical headroom does the camera leave?

ENGINE MODEL (all stock Memoria, cited in engine_bounds.py / NOTES.md):
  * eye plan position = actor (x,z) + the posstat DISTANCE along the camera yaw (any yaw: the camera rotates);
  * eye y (steady state, before easing) = max(actor_y + eye_h, cameraCorrect + min(H, 37.1))   (ff9.cs:2938-3001)
    where H = the max of FOUR sky-casts at eye +-5.5u in x and z (fuzzy mode, on foot) -- the eye's own plan
    position is NEVER sampled -- each cast IgnoreExceptions (no up-facing filter, no 4078 skip), FIRST TRI
    IN BUFFER ORDER of the first mesh in registration order (WMBlock.Raycast);
  * then min(eye_y, 71.80859375) (ff9.cs:3112);
  * posstat = lerp(down, up, t) with t = clamp((y*256+1000)*4096/4500, 0, 4096)/4096 (ff9.cs:3181-3191),
    (down, up) from w_cameraElement[type_cam 0 (foot), area-place(area of the ground under the actor)].
  (The camera's own 4-slot tri cache and the eye EASING are not modelled: steady state, cache-free.)

METHOD: rasterize the whole disc-1 map at 1u with BOTH engine query semantics, vectorized:
  ANY  = first-in-buffer tri, any facing, all idalls        (camera casts, flight casts)
  WALK = first-in-buffer up-facing tri, 4078/4088/2040 skipped (the walker's ground; actor sample points)
then, for every standable foot-legal cell on a 2u lattice and 16 yaws, evaluate the eye and count
  CLIP      : ANY(eye plan) > eye_y            (the eye is inside/under the terrain surface)
  NEAR      : 0 <= eye_y - ANY(eye plan) < 0.3 (within the prefab near plane, 0.3u -- render_bounds_probe.py)
  OCCLUDED  : ANY at 9 points on the segment eye->actor head (+1.5u) rises above the segment
CALIBRATION: the rasterizer is checked against the kit simulator `placement.place` (WALK semantics) at 2000
random points; it must agree on ground y within 1e-3 at >= 99.5% of non-boundary points.

Run:  py studies/terrain-malleability/vertical/camera_clip_census.py      (~1-3 min)
"""
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import numpy as np                                   # noqa: E402
from ff9mapkit.world import extract as X             # noqa: E402
from ff9mapkit.world import placement as P           # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
EB = json.loads((OUT / "engine_bounds.json").read_text())["derived"]
RES = 1.0
W, H = int(1536 / RES), int(1280 / RES)
SKIP = {4078, 4088, 2040}
FOOT_OK = set(P.WALK_OK)
DISC = 1


def block_parts(disc):
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            per[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
    return per


def rasterize(disc):
    any_y = np.full((H, W), np.nan)
    any_part = np.full((H, W), -1, np.int8)
    walk_y = np.full((H, W), np.nan)
    walk_id = np.zeros((H, W), np.int64)
    bp = block_parts(disc)
    for (bx, by), parts in sorted(bp.items()):
        names = [p for p in parts if P.canonical_part(p) is not None]
        order = sorted(names, key=lambda p: P.REGISTRATION_ORDER.index(P.canonical_part(p)))
        ox, oz = X.block_world_origin(bx, by)
        # cell centres of this block (world): x in [ox, ox+64), z in (oz-64, oz]
        gx0, gz0 = int(ox / RES), int(-oz / RES)
        n = int(64 / RES)
        any_done = np.zeros((n, n), bool)
        walk_done = np.zeros((n, n), bool)
        for p in order:
            bm = X.read_block(bx, by, disc=disc, part=p)
            V = np.asarray(bm.verts, dtype=np.float64)
            if V.size == 0:
                continue
            F = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
            T = bm.tangents
            ids = np.array([int(round(T[i][0])) for i in F[:, 0]]) if T is not None else np.zeros(len(F), int)
            a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
            cr = np.cross(b - a, c - a)
            L = np.linalg.norm(cr, axis=1)
            ny = np.where(L > 0, cr[:, 1] / np.where(L > 0, L, 1), 0)
            for t in range(len(F)):
                xs = (a[t, 0], b[t, 0], c[t, 0]); zs = (a[t, 2], b[t, 2], c[t, 2])
                i0 = max(0, int(math.floor(min(xs) / RES - 0.5)) ); i1 = min(n - 1, int(math.ceil(max(xs) / RES - 0.5)))
                j0 = max(0, int(math.floor(-max(zs) / RES - 0.5))); j1 = min(n - 1, int(math.ceil(-min(zs) / RES - 0.5)))
                if i1 < i0 or j1 < j0:
                    continue
                ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
                px = (ii + 0.5) * RES; pz = -(jj + 0.5) * RES
                d = (b[t, 2] - c[t, 2]) * (a[t, 0] - c[t, 0]) + (c[t, 0] - b[t, 0]) * (a[t, 2] - c[t, 2])
                if abs(d) < 1e-12:
                    continue
                w0 = ((b[t, 2] - c[t, 2]) * (px - c[t, 0]) + (c[t, 0] - b[t, 0]) * (pz - c[t, 2])) / d
                w1 = ((c[t, 2] - a[t, 2]) * (px - c[t, 0]) + (a[t, 0] - c[t, 0]) * (pz - c[t, 2])) / d
                w2 = 1 - w0 - w1
                inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
                if not inside.any():
                    continue
                hy = w0 * a[t, 1] + w1 * b[t, 1] + w2 * c[t, 1]
                sel_any = inside & ~any_done[jj, ii]
                if sel_any.any():
                    any_y[gz0 + jj[sel_any], gx0 + ii[sel_any]] = hy[sel_any]
                    any_part[gz0 + jj[sel_any], gx0 + ii[sel_any]] = P.REGISTRATION_ORDER.index(P.canonical_part(p))
                    any_done[jj[sel_any], ii[sel_any]] = True
                if ids[t] not in SKIP and ny[t] > 0.1:
                    sel_w = inside & ~walk_done[jj, ii]
                    if sel_w.any():
                        walk_y[gz0 + jj[sel_w], gx0 + ii[sel_w]] = hy[sel_w]
                        walk_id[gz0 + jj[sel_w], gx0 + ii[sel_w]] = ids[t]
                        walk_done[jj[sel_w], ii[sel_w]] = True
            # a mesh with ANY hit ends the scan for that cell only if it hit -- already encoded by *_done
    return any_y, walk_y, walk_id, bp, any_part


print("rasterizing disc", DISC, "at", RES, "u ...")
ANY, WALK, WID, BP, APART = rasterize(DISC)
ANY0 = np.where(np.isnan(ANY), 0.0, ANY)          # miss -> defaultHeight 0
print("  ANY coverage", float(np.isfinite(ANY).mean()), " WALK coverage", float(np.isfinite(WALK).mean()))

# ---- calibration vs the kit simulator ------------------------------------------------------------------------
rng = np.random.default_rng(7)
agree = tot = 0
mismatch = []
ml_cache = {}
for _ in range(2000):
    gx = int(rng.integers(0, W)); gz = int(rng.integers(0, H))
    bx, by = int(gx * RES // 64), int(gz * RES // 64)
    if (bx, by) not in BP:
        continue
    parts = BP[(bx, by)]
    if any("volcano" in p for p in parts) or by * 24 + bx == 219:
        continue
    if (bx, by) not in ml_cache:
        by_name = {p: X.read_block(bx, by, disc=DISC, part=p) for p in parts if P.canonical_part(p) is not None}
        ml = P.build_meshlist(by_name)
        ml_cache[(bx, by)] = (ml, P.build_meshlist_index(ml))
    ml, idx = ml_cache[(bx, by)]
    lx = (gx + 0.5) * RES - bx * 64; lz = -((gz + 0.5) * RES - by * 64)
    gy, mesh, idall, topo = P.place(ml, lx, lz, 0.0, sky=True, index=idx)
    ry = WALK[gz, gx]
    ry = 0.0 if np.isnan(ry) else ry
    tot += 1
    if abs(ry - gy) < 1e-3:
        agree += 1
    elif len(mismatch) < 5:
        mismatch.append(((gx, gz), round(float(ry), 3), round(gy, 3), mesh))
cal = {"agree": agree, "total": tot, "rate": agree / max(tot, 1), "examples": mismatch}
print("CALIBRATION raster(WALK) vs placement.place:", cal)

# ---- camera evaluation ---------------------------------------------------------------------------------------
PS = EB["camera_posstat_units"]
ELEM = EB["camera_element"]
A2P = {}
for place, areas in EB["camera_area2place"].items():
    for a in areas:
        A2P[a] = int(place)
CLAMP = EB["camera_ride_clamp_other"]
CEIL = EB["camera_eye_abs_ceiling_u"]
FUZZ = EB["camera_fuzzy_radius"]

topo_w = (WID & 0xFC) >> 2
area_w = (WID & 0x3F00) >> 8
stand = np.isfinite(WALK) & np.isin(topo_w, list(FOOT_OK))
sub = np.zeros_like(stand); sub[::2, ::2] = True
pts = np.argwhere(stand & sub)                     # (gz, gx)
ay = WALK[pts[:, 0], pts[:, 1]]
ax = (pts[:, 1] + 0.5) * RES; az = -(pts[:, 0] + 0.5) * RES
place = np.array([A2P.get(int(a), 0) for a in area_w[pts[:, 0], pts[:, 1]]])
t = np.clip(((ay * 256 + 1000) * 4096 / 4500), 0, 4096) / 4096
dn = np.array([ELEM[f"0,{p}"]["down"] for p in place]); up = np.array([ELEM[f"0,{p}"]["up"] for p in place])
pd = lambda k, arr: np.array([PS[i][k] for i in arr])
dist = pd("distance_u", dn) * (1 - t) + pd("distance_u", up) * t
eyeh = pd("eye_height_u", dn) * (1 - t) + pd("eye_height_u", up) * t
cc = pd("correct_u", dn) * (1 - t) + pd("correct_u", up) * t


def samp(x, z):
    gx = np.floor(np.mod(x, 1536) / RES).astype(int) % W
    gz = np.floor(np.mod(-z, 1280) / RES).astype(int) % H
    return ANY0[gz, gx]


res = {"calibration": cal, "points": int(len(pts)), "yaws": 16,
       "points_by_area_place": {int(k): int(v) for k, v in Counter(place.tolist()).items()},
       "place1_low_actor_min_clip_threshold": round(float((cc + CLAMP)[(place == 1)].min()), 3) if (place == 1).any() else None,
       "min_clip_threshold_all_points": round(float((cc + CLAMP).min()), 3)}
clip = near = occl = 0
clip_ex, occl_ex = [], []
margins = []
clip_by_center_spike = 0
for k in range(16):
    yaw = 2 * math.pi * k / 16
    ex, ez = ax + dist * math.sin(yaw), az + dist * math.cos(yaw)
    probes = np.stack([samp(ex + FUZZ, ez), samp(ex - FUZZ, ez), samp(ex, ez + FUZZ), samp(ex, ez - FUZZ)])
    Hp = probes.max(axis=0)
    eye = np.maximum(ay + eyeh, cc + np.minimum(Hp, CLAMP))
    eye = np.minimum(eye, CEIL)
    hc = samp(ex, ez)
    m = eye - hc
    margins.append(m)
    c = m < 0
    clip += int(c.sum()); near += int(((m >= 0) & (m < 0.3)).sum())
    clip_by_center_spike += int((c & (hc <= Hp)).sum() == 0 and 0 or (c & (hc > Hp)).sum())
    for i in np.where(c)[0][:3]:
        if len(clip_ex) < 12:
            clip_ex.append({"actor": [round(float(ax[i]), 1), round(float(ay[i]), 2), round(float(az[i]), 1)],
                            "yaw16": k, "eye_y": round(float(eye[i]), 2), "terrain_at_eye": round(float(hc[i]), 2),
                            "max4probes": round(float(Hp[i]), 2), "place": int(place[i]),
                            "eye_xz": [round(float(ex[i]), 2), round(float(ez[i]), 2)],
                            "mesh_at_eye": P.REGISTRATION_ORDER[int(APART[int(np.floor(np.mod(-ez[i], 1280) / RES)) % H,
                                                                       int(np.floor(np.mod(ex[i], 1536) / RES)) % W])]})
    # occlusion: 9 points on the segment eye -> actor head
    hy = ay + 1.5
    blocked = np.zeros(len(ay), bool)
    for s in np.linspace(0.1, 0.9, 9):
        sx, sz = ex + (ax - ex) * s, ez + (az - ez) * s
        sy = eye + (hy - eye) * s
        blocked |= samp(sx, sz) > sy
    occl += int(blocked.sum())
    for i in np.where(blocked)[0][:2]:
        if len(occl_ex) < 10:
            occl_ex.append({"actor": [round(float(ax[i]), 1), round(float(ay[i]), 2), round(float(az[i]), 1)], "yaw16": k})
M = np.concatenate(margins)
res.update({"evaluations": int(len(M)), "clip": clip, "clip_center_above_all_probes": clip_by_center_spike,
            "near_lt_0.3": near, "occluded": occl,
            "margin_pcts": {f"p{q}": round(float(np.percentile(M, q)), 3) for q in (0.01, 0.1, 1, 5, 50)},
            "clip_examples": clip_ex, "occlusion_examples": occl_ex,
            "stock_any_max": float(np.nanmax(ANY)), "stock_walk_max_footlegal": float(WALK[stand].max())})
# ---- flight envelope from the ANY raster (flight + camera casts are IgnoreExceptions, first-in-buffer) --------
fl = {}
for name, th in (("mist_29", 29.0), ("flyer_cam_clamp_33.2", 33.2), ("foot_cam_clamp_37.1", 37.1),
                 ("flight_ceiling_42.1875", EB["flight_ceiling"])):
    m = np.nan_to_num(ANY, nan=-99) > th
    fl[name] = {"area_u2": float(m.sum() * RES * RES)}
    if th >= 42:
        cells = np.argwhere(m)
        fl[name]["cells_world_xz"] = [[float((c[1] + 0.5) * RES), float(-(c[0] + 0.5) * RES),
                                       round(float(ANY[c[0], c[1]]), 3)] for c in cells[:40]]
res["flight_floor_any_raster_above"] = fl
print(json.dumps({k: v for k, v in res.items() if k not in ("clip_examples", "occlusion_examples")}, indent=1))
print("clip examples:", clip_ex[:6])
print("occlusion examples:", occl_ex[:5])
(OUT / "camera_clip_census.json").write_text(json.dumps(res, indent=1))
print("wrote", OUT / "camera_clip_census.json")
