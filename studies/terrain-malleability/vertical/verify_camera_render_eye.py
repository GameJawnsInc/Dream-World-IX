"""VERIFIER for V5/V6 -- re-run the chase-camera clip census with the RENDER eye, not the internal one.

The lane's camera_clip_census.py models ff9.w_cameraWorldEye (ff9.cs:2938-3112). But the camera that RENDERS is
placed at w_cameraWorldEye + b (ff9.cs:2747 `mainCamera.transform.position = ff9.w_cameraWorldEye + b;`), where
with FixTypeCam (default TRUE, WorldState.cs:22) b.y = FixTypeCamEyeY/256 * CameraHeight/100 (ff9.cs:2738), and
FixTypeCamEyeY eases to the per-type_cam target set in w_tweakSomeValues (ff9.cs:6057-6091): type_cam 0/1
(foot, ground chocobos) 558 -> +2.1797u; type_cam 3 (Hilda/Invincible) 1419 -> +5.543u; type_cam 2 (Narciss) 320.
CameraHeight is 100 in the live Memoria.ini.

This script re-uses the lane's rasterizer verbatim (ANY + WALK semantics, calibrated against placement.place) and
evaluates four eye models on the same 2u lattice x 16 yaws:
  L  : the lane's model (internal eye, probe ring centred on the eye, no sink)          -> must reproduce clip=1
  R  : L + the render offset +558/256                                                    -> the camera that draws
  RS : R + the walker's canopy sink (actor y = ground - 1.171875 on topo 36/37/38)      (V3 applied to the camera)
  RSD: RS + the engine's probe-centre shift (eye + w_cameraDirVector/4 = actor + 0.75*offset, ff9.cs:2940-2942)
and the player-toggled HIGH camera (upperCounter=4096 -> posstat 'fly' for type_cam 0 = posstat 7,
ff9.cs:3164-3176) under RSD.
Discs 1 and 4 (disc 4's (11,4) Object spike is 38.19, disc 1's 35.50).

Read-only. Writes out/verify_camera_render_eye.json.
Run: py studies/terrain-malleability/vertical/verify_camera_render_eye.py
"""
import json
import math
import re
import sys
from collections import defaultdict
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
RENDER_DY = 558 / 256.0
SINK = 1.171875


def block_parts(disc):
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            per[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
    return per


def rasterize(disc):            # verbatim logic of camera_clip_census.rasterize
    any_y = np.full((H, W), np.nan)
    walk_y = np.full((H, W), np.nan)
    walk_id = np.zeros((H, W), np.int64)
    bp = block_parts(disc)
    for (bx, by), parts in sorted(bp.items()):
        names = [p for p in parts if P.canonical_part(p) is not None]
        order = sorted(names, key=lambda p: P.REGISTRATION_ORDER.index(P.canonical_part(p)))
        ox, oz = X.block_world_origin(bx, by)
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
                i0 = max(0, int(math.floor(min(xs) / RES - 0.5))); i1 = min(n - 1, int(math.ceil(max(xs) / RES - 0.5)))
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
                    any_done[jj[sel_any], ii[sel_any]] = True
                if ids[t] not in SKIP and ny[t] > 0.1:
                    sel_w = inside & ~walk_done[jj, ii]
                    if sel_w.any():
                        walk_y[gz0 + jj[sel_w], gx0 + ii[sel_w]] = hy[sel_w]
                        walk_id[gz0 + jj[sel_w], gx0 + ii[sel_w]] = ids[t]
                        walk_done[jj[sel_w], ii[sel_w]] = True
    return any_y, walk_y, walk_id


PS = EB["camera_posstat_units"]
ELEM = EB["camera_element"]
A2P = {int(a): int(pl) for pl, areas in EB["camera_area2place"].items() for a in areas}
CLAMP = EB["camera_ride_clamp_other"]
CEIL = EB["camera_eye_abs_ceiling_u"]
FUZZ = EB["camera_fuzzy_radius"]

result = {"render_dy_foot": RENDER_DY, "sink": SINK}
for DISC in (1, 4):
    print(f"rasterizing disc {DISC} ...", flush=True)
    ANY, WALK, WID = rasterize(DISC)
    ANY0 = np.where(np.isnan(ANY), 0.0, ANY)
    topo_w = (WID & 0xFC) >> 2
    area_w = (WID & 0x3F00) >> 8
    stand = np.isfinite(WALK) & np.isin(topo_w, list(FOOT_OK))
    sub = np.zeros_like(stand); sub[::2, ::2] = True
    pts = np.argwhere(stand & sub)
    gy = WALK[pts[:, 0], pts[:, 1]]
    tp = topo_w[pts[:, 0], pts[:, 1]]
    ax = (pts[:, 1] + 0.5) * RES; az = -(pts[:, 0] + 0.5) * RES
    place = np.array([A2P.get(int(a), 0) for a in area_w[pts[:, 0], pts[:, 1]]])

    def samp(x, z):
        gx = np.floor(np.mod(x, 1536) / RES).astype(int) % W
        gz = np.floor(np.mod(-z, 1280) / RES).astype(int) % H
        return ANY0[gz, gx]

    def run(model, upper=False):
        ay = gy - (SINK if model in ("RS", "RSD") else 0.0) * np.isin(tp, [36, 37, 38])
        t = np.clip(((ay * 256 + 1000) * 4096 / 4500), 0, 4096) / 4096
        if upper:          # full 'fly' posstat of type_cam 0 (posstat 7)
            fl = np.array([ELEM[f"0,{p}"]["fly"] for p in place])
            pd = lambda k: np.array([PS[i][k] for i in fl])
            dist, eyeh, cc = pd("distance_u"), pd("eye_height_u"), pd("correct_u")
        else:
            dn = np.array([ELEM[f"0,{p}"]["down"] for p in place]); up = np.array([ELEM[f"0,{p}"]["up"] for p in place])
            pdd = lambda k, arr: np.array([PS[i][k] for i in arr])
            dist = pdd("distance_u", dn) * (1 - t) + pdd("distance_u", up) * t
            eyeh = pdd("eye_height_u", dn) * (1 - t) + pdd("eye_height_u", up) * t
            cc = pdd("correct_u", dn) * (1 - t) + pdd("correct_u", up) * t
        clip = 0; ex_list = []; margins = []
        cap_binds = 0
        clip_far_from_spike = 0          # clips whose eye is > 20u from the w_effectLastPos spike (768,-320)
        clip_eye_xz = []
        for k in range(16):
            yaw = 2 * math.pi * k / 16
            ox, oz = dist * math.sin(yaw), dist * math.cos(yaw)
            ex, ez = ax + ox, az + oz
            if model == "RSD":
                cx, cz = ax + 0.75 * ox, az + 0.75 * oz       # eye + dirVector/4, dirVector = aim - eye = -offset
            else:
                cx, cz = ex, ez
            probes = np.stack([samp(cx + FUZZ, cz), samp(cx - FUZZ, cz), samp(cx, cz + FUZZ), samp(cx, cz - FUZZ)])
            Hp = probes.max(axis=0)
            eye = np.maximum(ay + eyeh, cc + np.minimum(Hp, CLAMP))
            cap_binds += int((eye > CEIL).sum())
            eye = np.minimum(eye, CEIL)
            if model != "L":
                eye = eye + RENDER_DY
            hc = samp(ex, ez)
            m = eye - hc
            margins.append(m)
            c = m < 0
            clip += int(c.sum())
            dspk = np.hypot(np.mod(ex, 1536) - 767.98, np.mod(ez, -1280) + 320.32)
            clip_far_from_spike += int((c & (dspk > 20)).sum())
            clip_eye_xz += [(float(np.mod(ex[i], 1536)), float(np.mod(ez[i], -1280))) for i in np.where(c)[0]]
            for i in np.where(c)[0][:2]:
                if len(ex_list) < 8:
                    ex_list.append({"actor": [round(float(ax[i]), 1), round(float(ay[i]), 2), round(float(az[i]), 1)],
                                    "yaw16": k, "eye_y": round(float(eye[i]), 2), "terrain_at_eye": round(float(hc[i]), 2),
                                    "eye_xz": [round(float(ex[i]), 2), round(float(ez[i]), 2)]})
        M = np.concatenate(margins)
        near = int(((M >= 0) & (M < 0.3)).sum())
        bbox = ([round(min(p[0] for p in clip_eye_xz), 1), round(max(p[0] for p in clip_eye_xz), 1),
                 round(min(p[1] for p in clip_eye_xz), 1), round(max(p[1] for p in clip_eye_xz), 1)]
                if clip_eye_xz else None)
        return {"evaluations": int(len(M)), "clip": clip, "clip_eye_gt_20u_from_spike": clip_far_from_spike,
                "clip_eye_bbox_x0x1z0z1": bbox, "near_lt_0.3": near, "eye_cap_binds": cap_binds,
                "margin_pcts": {f"p{q}": round(float(np.percentile(M, q)), 3) for q in (0.01, 0.1, 1, 50)},
                "margin_min": round(float(M.min()), 3), "clip_examples": ex_list}

    rd = {"points": int(len(pts))}
    for model in ("L", "R", "RS", "RSD"):
        rd[model] = run(model)
        print(DISC, model, {k: v for k, v in rd[model].items() if k != "clip_examples"}, rd[model]["clip_examples"][:2], flush=True)
    rd["RSD_high_camera"] = run("RSD", upper=True)
    print(DISC, "RSD_high", {k: v for k, v in rd["RSD_high_camera"].items() if k != "clip_examples"},
          rd["RSD_high_camera"]["clip_examples"][:2], flush=True)
    result[f"disc{DISC}"] = rd

(OUT / "verify_camera_render_eye.json").write_text(json.dumps(result, indent=1))
print("wrote", OUT / "verify_camera_render_eye.json")
