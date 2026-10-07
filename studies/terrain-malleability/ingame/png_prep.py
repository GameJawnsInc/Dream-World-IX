"""OFFLINE PREP for the per-cell PNG override experiment (README section 7.1 rank 6; capacity X5 / consumption C10).

Read-only on the install (it reads the donor block meshes through the kit, the Moguri atlas, Memoria.ini and archived
harness frames). Writes ONLY under ingame/out/ (gitignored):
  out/png_lab/FF9CustomMap-lab/...   the exact tree the orchestrator copies into <game>/FF9CustomMap-lab/
  out/png_prep.json                  stand points, ground heights, bearings, calibrations, registered predictions,
                                     and the sha256 manifest of the lab tree

What it does, in order (each step asserts its own calibration):
  1. LAB TREE. Re-emits the donor Block[12][10] Terrain and Sea4 meshes VERBATIM through the kit writer
     (mesh.ff9mesh_bytes) for cell A (21,1) and cell B (0,13); parses every file back and asserts every channel is
     float-equal to the donor read (zero geometry authorship: the cell looks like a stock 12,10 islet with or
     without the overrides). Solid 64x64 opaque PNGs: Terrain magenta, Sea4 red, Sea3 lime -- on A only, and Sea3
     with NO Sea3 mesh (the arm that tests "a PNG needs a same-part mesh override", WMWorld.cs:826 -> :835).
  2. GROUND at the stand point (first up-facing Terrain hit, the walk rule), the bind proof's predicted y.
  3. CAMERA CALIBRATION against session 7's vcap-under.png (actor at the `off` point (1350.63, 6.0, -120.29) --
     the loop's LAST teleport), model in png_judge.camera: bearing is the only free parameter.
  4. FOG + SHADING: session 7's plane is one atlas texel (uv 0.1, 0.8) everywhere, so each pixel o = k * texel +
     b * F; the fit gives the per-pixel shading k and fog blend b, and b is regressed on the calibrated ray distance.
  5. CLASSIFIER CALIBRATION: false positives over every archived terrain-session frame; detection of each PNG colour
     re-shaded with the measured (k, b) of every plane pixel, and the fog blend at which detection fails.
  6. PROJECTION DRY RUN: the calibrated camera at A's stand for 24 bearings -> per-part pixel fractions; picks the
     two registered bearings and the predicted red (Sea4) fraction, with the counterfactual magenta/lime areas.

Rerun:  py studies/terrain-malleability/ingame/png_prep.py
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "consumption"))
import numpy as np                                             # noqa: E402
from PIL import Image                                          # noqa: E402

from ff9mapkit.world import extract as X                       # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
import landdonor_water as LW                                   # noqa: E402
import png_judge as J                                          # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
REPO = Path(r"C:\gd\Dream-World-IX")
S7_FRAME = REPO / ".harness-runs" / "20261007-134912-terrain-session7-under" / "shots" / "vcap-under.png"
S7_ACTOR = (1350.63, 6.0, -120.29)
NEAR = 45.0                                     # judged near field (u from the eye); beyond it the mist washes out
FOG_F = np.array([190.0, 205.0, 235.0])         # fog colour estimate; the decomposition is insensitive to it (+-15)
PARTS = ("terrain", "sea1", "sea3", "sea4", "sea5")
BEARING_GRID = list(range(0, 360, 15))


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ini_fov() -> float:
    txt = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    sec = re.search(r"^\[Worldmap\](.*?)(?=^\[|\Z)", txt, re.S | re.M)
    m = re.search(r"^\s*FieldOfView\s*=\s*(\d+)", sec.group(1), re.M) if sec else None
    return float(m.group(1)) if m else 44.0


# ------------------------------------------------------------------------------------------------ 1. lab tree
def build_lab(donor):
    files = {}
    for cell, meshes, pngs in ((J.CELL_A, J.A_MESHES, J.A_PNGS), (J.CELL_B, J.B_MESHES, ())):
        for part in meshes:
            bm = donor[part.lower()]
            assert bm.vcount == len(bm.flat_index), f"donor {part} is not flat (vcount != icount)"
            assert bm.tangents, f"donor {part} has no tangents (walk IDALL)"
            data = M.ff9mesh_bytes(bm)                  # validates: nothing engine-rejectable is written
            rel = J.lab_relpath(cell, part, "ff9mesh")
            dst = J.LAB / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            back = M.read_ff9mesh(dst)                  # verbatim proof: every channel float-equal to the donor
            for key, src in (("verts", bm.verts), ("normals", bm.normals), ("uvs", bm.uvs),
                             ("tangents", bm.tangents)):
                a = np.asarray(back[key], np.float32)
                b = np.asarray(src, np.float32)
                assert a.shape == b.shape and np.array_equal(a, b), f"{rel}: {key} differs from the donor"
            assert list(back["indices"]) == list(bm.flat_index), f"{rel}: indices differ from the donor"
            files[rel] = {"sha256": sha256(dst), "bytes": dst.stat().st_size, "vcount": bm.vcount,
                          "tris": len(bm.flat_index) // 3}
        for part in pngs:
            rel = J.lab_relpath(cell, part, "png")
            dst = J.LAB / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGBA", (64, 64), J.PNG_COLOR[part] + (255,)).save(dst)
            files[rel] = {"sha256": sha256(dst), "bytes": dst.stat().st_size, "rgba": list(J.PNG_COLOR[part]) + [255]}
    return files


# ------------------------------------------------------------------------------------------------ 2. ground
def ground_at(bm, lx, lz):
    """First up-facing hit in buffer order at local (lx, lz) -- the walk rule (WMPhysics.cs:6-47, ny > 0.1)."""
    V = np.asarray(bm.verts, np.float64)
    T = bm.tangents
    for k, t in enumerate(bm.tris):
        a, b, c = V[t[0]], V[t[1]], V[t[2]]
        n = np.cross(b - a, c - a)
        if n[1] <= 0.1 * np.linalg.norm(n):
            continue
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        w0 = ((b[2] - c[2]) * (lx - c[0]) + (c[0] - b[0]) * (lz - c[2])) / d
        w1 = ((c[2] - a[2]) * (lx - c[0]) + (a[0] - c[0]) * (lz - c[2])) / d
        w2 = 1 - w0 - w1
        if min(w0, w1, w2) >= 0:
            tid = int(T[t[0]][0])
            return {"y": round(float(w0 * a[1] + w1 * b[1] + w2 * c[1]), 4), "tri": k, "idall": tid,
                    "topo": (tid & 0xFC) >> 2, "area": (tid & 0x3F00) >> 8, "event": (tid & 0xC000) >> 14,
                    "min_bary": round(float(min(w0, w1, w2)), 3)}
    return None


# ------------------------------------------------------------------------------------------------ 3-4. calibrations
def s7_plane_mask(rgb):
    R, G, B = (rgb[..., i].astype(int) for i in range(3))
    return (G > B + 15) & (R < G + 5)


def camera_calibration(fov_setting):
    rgb = J.load_rgb(S7_FRAME)
    h, w = rgb.shape[:2]
    obs = s7_plane_mask(rgb)
    S = 4
    sub = obs[S // 2::S, S // 2::S]
    hh, ww = sub.shape
    keep = np.ones_like(sub)
    keep[int(0.53 * hh):int(0.65 * hh), int(0.46 * ww):int(0.54 * ww)] = False      # the actor sprite

    def mask(bearing, render_offsets):
        eye, aim, fov = J.camera(S7_ACTOR, bearing, fov_setting=fov_setting, render_offsets=render_offsets)
        D = J.ray_dirs(eye, aim, fov, ww, hh)
        with np.errstate(divide="ignore", invalid="ignore"):
            s = (6.0 - eye[1]) / D[..., 1]
        P = eye[None, None, :] + s[..., None] * D
        return (s > 0) & (P[..., 0] >= 1344) & (P[..., 0] < 1408) & (P[..., 2] >= -128) & (P[..., 2] < -64), s, D

    res = {}
    for ro in (False, True):
        best = max(((float(((mask(b, ro)[0] & sub & keep).sum()) / max(((mask(b, ro)[0] | sub) & keep).sum(), 1)), b)
                    for b in np.arange(240.0, 300.0, 0.2)))
        res["render_offsets" if ro else "no_render_offset"] = {"iou": round(best[0], 4), "bearing": round(best[1], 2)}
    chosen = res["no_render_offset"]
    assert chosen["iou"] >= 0.93, f"camera model not calibrated (IoU {chosen['iou']})"
    # full-res distances for the fog fit
    eye, aim, fov = J.camera(S7_ACTOR, chosen["bearing"], fov_setting=fov_setting)
    D = J.ray_dirs(eye, aim, fov, w, h)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = (6.0 - eye[1]) / D[..., 1]
    dist = s * np.linalg.norm(D, axis=-1)
    return res, rgb, obs, dist


def fog_and_shading(rgb, obs, dist):
    atlas = Image.open(GAME / "MoguriMain" / "StreamingAssets" / "Assets" / "Resources" / "WorldMap" / "Textures"
                       / "res(1_24)_terrain.png").convert("RGB")
    W, H = atlas.size
    texel = np.asarray(atlas, np.float64)[int(0.2 * H), int(0.1 * W)]      # uv (0.1, 0.8), V flipped
    h, w = obs.shape
    m = obs.copy()
    m[int(0.53 * h):int(0.65 * h), int(0.46 * w):int(0.54 * w)] = False
    O = rgb[m].astype(np.float64)
    A = np.stack([texel, FOG_F], 1)
    X_, *_ = np.linalg.lstsq(A, O.T, rcond=None)
    k, b = X_[0], X_[1]
    rms = float(np.sqrt((((A @ X_).T - O) ** 2).mean()))
    d = dist[m]
    ok = np.isfinite(d)
    fit = np.polyfit(d[ok], b[ok], 1)                    # b = a1 * dist + a0
    return {"atlas_texel": texel.tolist(), "rms": round(rms, 3), "k_p1_p50_p99": np.percentile(k, [1, 50, 99]).round(3).tolist(),
            "b_p1_p50_p99": np.percentile(b, [1, 50, 99]).round(3).tolist(),
            "dist_p1_p99": np.percentile(d[ok], [1, 99]).round(2).tolist(),
            "fog_fit_a0_a1": [round(float(fit[1]), 5), round(float(fit[0]), 6)]}, k, b, d


def classifier_calibration(k, b):
    # (a) false positives over every archived terrain-session frame
    fp = {}
    frames = sorted(glob.glob(str(REPO / ".harness-runs" / "*terrain*" / "shots" / "*.png")))
    worst = {c: (0.0, None) for c in J.CLASSES}
    for f in frames:
        c = J.frame_counts(f)
        for cls in J.CLASSES:
            if c[cls + "_frac"] > worst[cls][0]:
                worst[cls] = (c[cls + "_frac"], Path(f).relative_to(REPO).as_posix())
            if c[cls] > J.noise_px(c["n"]):
                fp.setdefault(cls, []).append({"frame": Path(f).relative_to(REPO).as_posix(), "px": c[cls]})
    # (b) detection of each PNG colour under the measured per-pixel shading + fog of session 7's plane
    det = {}
    for part, col in J.PNG_COLOR.items():
        cv = np.asarray(col, np.float64)
        o = np.clip(k[:, None] * cv[None, :] + b[:, None] * FOG_F[None, :], 0, 255).astype(np.uint8)
        hit = J.class_mask(o.reshape(-1, 1, 3), J.CLASS_OF[part]).ravel()
        # the fog blend at which this colour stops classifying: o = k0 (1 - b) c + b F (k = k0 (1 - b) in the fit),
        # with k0 at the plane's 1st-percentile shading (the darkest pixel the near field showed)
        kmin = float(np.percentile(k, 1))
        bmax = None
        for bb in np.arange(0.0, 1.0, 0.01):
            px = np.clip(kmin * (1 - bb) * cv + bb * FOG_F, 0, 255).astype(np.uint8)
            if not J.class_mask(px.reshape(1, 1, 3), J.CLASS_OF[part])[0, 0]:
                bmax = round(float(bb), 2)
                break
        det[part] = {"class": J.CLASS_OF[part], "detected_frac_on_plane_pixels": round(float(hit.mean()), 5),
                     "fails_at_fog_blend": bmax}
    # (c) cross-talk: a PNG colour must not classify as another class
    cross = {}
    for part, col in J.PNG_COLOR.items():
        cv = np.asarray(col, np.float64)
        o = np.clip(k[:, None] * cv[None, :] + b[:, None] * FOG_F[None, :], 0, 255).astype(np.uint8).reshape(-1, 1, 3)
        for cls in J.CLASSES:
            if cls != J.CLASS_OF[part]:
                cross[f"{part}->{cls}"] = round(float(J.class_mask(o, cls).mean()), 5)
    return {"frames_scanned": len(frames), "frames_over_noise": fp,
            "worst_frame_frac": {c: {"frac": v[0], "frame": v[1]} for c, v in worst.items()},
            "detection": det, "cross_talk": cross}


# ------------------------------------------------------------------------------------------------ 6. projection
def scene_from(donor, step=0.25):
    sea = [(p, donor[p]) for p in ("sea1", "sea3", "sea4", "sea5")]
    owner, _topo = LW.raster_first_hit(sea, step=step)
    T = donor["terrain"]
    V = np.asarray(T.verts, np.float64)
    tris = np.array([[V[t[0]], V[t[1]], V[t[2]]] for t in T.tris])
    return {"tris": tris, "owner": owner, "owner_names": [p for p, _ in sea], "raster_step": step}


def projection(scene, actor, fov_setting, fog_fit, det):
    rows = []
    for brg in BEARING_GRID:
        lab, dist = J.render_labels(scene, J.CELL_A, actor, brg, fov_setting=fov_setting)
        h, w = lab.shape
        keep = J.keep_mask(w, h)
        n = keep.sum()
        near = keep & (dist <= NEAR)
        fb = J.fog_b(dist, fog_fit)
        row = {"bearing": brg}
        for name in ("terrain", "sea1", "sea3", "sea4", "sea5", "outside", "sky"):
            li = J.LABELS.index(name)
            row[name] = round(float(((lab == li) & keep).sum() / n), 4)
            row[name + "_near"] = round(float(((lab == li) & near).sum() / n), 4)
        # detectable fraction: the part's pixels whose fog blend is below the colour's failure blend
        for part, lname in (("Sea4", "sea4"), ("Terrain", "terrain"), ("Sea3", "sea3")):
            lim = det[part]["fails_at_fog_blend"] or 1.0
            li = J.LABELS.index(lname)
            row[part + "_detectable"] = round(float(((lab == li) & keep & (fb < lim)).sum() / n), 4)
        rows.append(row)
    return rows


def cone_check(center, radius=40.0, step_deg=5, step_u=2.0):
    """world_face safety (memory: PROBES MUST NOT WANDER): walk every bearing out to ``radius`` over the LIVE walk
    list (session1_post.ground = stock + every live override, the engine's first-hit rule) and report the first
    hazard per bearing: a ground miss, an event tile (an entrance), a foot-blocked topograph, or a non-14 area."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gap_area_layer"))
    import session1_post as SP
    from ff9mapkit.world import placement as PL
    ok_topo = set(PL.WALK_OK)

    def G(x, z):
        return SP.ground(x % 1536.0, -((-z) % 1280.0))

    g0 = G(*center)
    hazards = {}
    for brg in range(0, 360, step_deg):
        r = step_u
        while r <= radius:
            g = G(center[0] + r * math.cos(math.radians(brg)), center[1] + r * math.sin(math.radians(brg)))
            why = ("miss" if g["ground"] is None else f"event {g['event']}" if g["event"] else
                   f"topo {g['topo']}" if g["topo"] not in ok_topo else f"area {g['area']}" if g["area"] != 14 else None)
            if why:
                hazards[brg] = [r, why]
                break
            r += step_u
    return {"center": list(center), "ground": g0, "radius": radius, "hazards": hazards}


def actor_box(actor, bearing, fov_setting, w=1280, h=720):
    eye, aim, fov = J.camera(actor, bearing, fov_setting=fov_setting)
    pts = [(actor[0] + dx, actor[1] + dy, actor[2] + dz) for dx in (-0.7, 0.7) for dz in (-0.7, 0.7) for dy in (0, 2.2)]
    x, y = J.project(pts, eye, aim, fov, w, h)
    return [round(float(x.min()), 1), round(float(x.max()), 1), round(float(y.min()), 1), round(float(y.max()), 1)]


def main():
    J.OUT.mkdir(exist_ok=True)
    donor = {p: X.read_block(J.DONOR[0], J.DONOR[1], disc=J.DISC, part=p) for p in PARTS}
    files = build_lab(donor)
    print(f"[1] lab tree: {len(files)} files under {J.LAB} (meshes verbatim = donor, float-equal on every channel)")

    g = ground_at(donor["terrain"], *J.STAND_LOCAL)
    assert g and g["topo"] == 0 and g["min_bary"] >= 0.1, f"stand point not inside a lawn tri: {g}"
    stands = {tag: {"world": J.stand_world(cell), "ground_y": g["y"]} for tag, cell in (("A", J.CELL_A), ("B", J.CELL_B))}
    print(f"[2] stand local {J.STAND_LOCAL} -> tri {g['tri']} topo {g['topo']} area {g['area']} y {g['y']}; "
          f"A {stands['A']['world']}  B {stands['B']['world']}")

    fov_setting = ini_fov()
    cam, rgb, obs, dist = camera_calibration(fov_setting)
    print(f"[3] camera calibration on session 7 (FieldOfView {fov_setting:g}): {cam}")
    shade, k, b, d = fog_and_shading(rgb, obs, dist)
    print(f"[4] shading/fog: {shade}")
    cls = classifier_calibration(k, b)
    print(f"[5] classifier: scanned {cls['frames_scanned']} frames; over-noise {cls['frames_over_noise'] or 'none'}; "
          f"worst {cls['worst_frame_frac']}")
    print(f"    detection {cls['detection']}")
    print(f"    cross-talk {cls['cross_talk']}")

    scene = scene_from(donor)
    actor = (stands["A"]["world"][0], g["y"], stands["A"]["world"][1])
    rows = projection(scene, actor, fov_setting, shade["fog_fit_a0_a1"], cls["detection"])
    print("[6] projection at A (fractions of the scored frame; *_near = within 45u of the eye):")
    for r in rows:
        print(f"    brg {r['bearing']:3d}: terrain {r['terrain']:.3f} sea4 {r['sea4']:.3f} (near {r['sea4_near']:.3f}, "
              f"detectable {r['Sea4_detectable']:.3f}) sea3 {r['sea3']:.3f} sea5 {r['sea5']:.3f} "
              f"outside {r['outside']:.3f} sky {r['sky']:.3f}")
    # The two registered bearings: each maximises the smaller of the Sea3 and Sea4 detectable areas plus a quarter
    # of the islet's (every arm in every frame); P2 is the best bearing >= 90 deg away from P1 (an independent view).
    def score(r):
        return min(r["Sea4_detectable"], r["Sea3_detectable"]) + 0.25 * r["Terrain_detectable"]
    p1 = max(rows, key=score)
    p2 = max((r for r in rows if abs(((r["bearing"] - p1["bearing"] + 180) % 360) - 180) >= 90), key=score)
    poses = []
    for tag, r in (("P1", p1), ("P2", p2)):
        poses.append({"tag": tag, "bearing": r["bearing"], "projected": r,
                      "actor_box_px_1280x720": actor_box(actor, r["bearing"], fov_setting)})
    print(f"    chosen: {[(p['tag'], p['bearing']) for p in poses]}; actor boxes "
          f"{[p['actor_box_px_1280x720'] for p in poses]}; PLAYER_BOX px "
          f"{[round(J.PLAYER_BOX[0] * 1280), round(J.PLAYER_BOX[1] * 1280), round(J.PLAYER_BOX[2] * 720), round(J.PLAYER_BOX[3] * 720)]}")
    for p in poses:
        bx = p["actor_box_px_1280x720"]
        assert (bx[0] >= J.PLAYER_BOX[0] * 1280 and bx[1] <= J.PLAYER_BOX[1] * 1280 and
                bx[2] >= J.PLAYER_BOX[2] * 720 and bx[3] <= J.PLAYER_BOX[3] * 720), f"actor box escapes PLAYER_BOX: {bx}"

    face = cone_check(J.FACE_HOME)
    landing = cone_check((68.37, -444.61))
    assert not face["hazards"], f"FACE_HOME is not clear: {face['hazards']}"
    print(f"[7] world_face home {J.FACE_HOME}: ground {face['ground']['ground']} area {face['ground']['area']}, "
          f"40u disc clear on all 72 bearings; the 6603 landing (68.37, -444.61) has hazards on "
          f"{len(landing['hazards'])} bearings: {landing['hazards']}")

    prep = {
        "face_home": face, "landing_cone": landing,
        "cells": {"A": list(J.CELL_A), "B": list(J.CELL_B), "donor": list(J.DONOR)},
        "stand_local": list(J.STAND_LOCAL), "stand_ground": g, "stands": stands,
        "fov_setting": fov_setting, "camera_calibration": cam, "shading_fog": shade, "classifier": cls,
        "near_u": NEAR, "projection": rows, "poses": poses,
        "lab_root": str(J.LAB), "lab_files": files,
    }
    J.PREP_JSON.write_text(json.dumps(prep, indent=1), encoding="utf-8")
    print(f"wrote {J.PREP_JSON}")


def verify_installed() -> int:
    """READ-ONLY post-deploy gate for the orchestrator: (1) FF9CustomMap-lab is FIRST in Memoria.ini FolderNames;
    (2) every manifest file is in <game>/FF9CustomMap-lab byte-identical (sha256), and the lab holds nothing else
    under the two cells; (3) NO other FolderNames folder holds any Block file for cell A or B -- a lower folder's
    `Block[21][1] Sea3.ff9mesh` would arm TryLoadTexture for the lab's Sea3.png and silently change arm S3, and a
    foreign Terrain/Sea4 would be shadowed but still means the cell is not ours."""
    prep = json.loads(J.PREP_JSON.read_text(encoding="utf-8"))
    ini = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', ini, re.M)
    folders = re.findall(r'"([^"]*)"', m.group(1)) if m else []
    problems = []
    if not folders or folders[0] != "FF9CustomMap-lab":
        problems.append(f"FolderNames does not start with FF9CustomMap-lab: {folders}")
    lab = GAME / "FF9CustomMap-lab"
    for rel, info in prep["lab_files"].items():
        p = lab / rel
        if not p.is_file():
            problems.append(f"missing {p}")
        elif sha256(p) != info["sha256"]:
            problems.append(f"sha256 differs: {p}")
    # ONE CHANGE PER IN-GAME TEST: the lab holds this manifest and nothing else. Other terrain lanes deploy into the
    # same scratch folder (cost_ and veh_ use (21,1); veh_ also (1,13), B's east neighbour), one run at a time.
    if lab.is_dir():
        import os
        for dirpath, _dirs, names in os.walk(lab):
            for nm in names:
                rel = (Path(dirpath) / nm).relative_to(lab).as_posix()
                if rel not in prep["lab_files"]:
                    problems.append(f"extra file in the lab (another lane's?): {rel}")
    pat = re.compile(r"^Block\[(\d+)\]\[(\d+)\] ")
    cells = {tuple(J.CELL_A), tuple(J.CELL_B)}
    for f in folders:
        root = GAME / f / "FF9_Data" / "WorldMap"
        if not root.is_dir():
            continue
        for dd in root.iterdir():
            for sub in (dd / "0_1").iterdir() if (dd / "0_1").is_dir() else []:
                for p in sub.iterdir() if sub.is_dir() else []:   # literal iterdir: '[' is a glob class
                    mm = pat.match(p.name)
                    if not mm or (int(mm.group(1)), int(mm.group(2))) not in cells:
                        continue
                    rel = p.relative_to(GAME / f).as_posix()
                    if f != "FF9CustomMap-lab":
                        problems.append(f"foreign file for an experiment cell in {f}: {rel}")
                    elif rel not in prep["lab_files"]:
                        problems.append(f"unexpected lab file: {rel}")
    print("FolderNames:", folders)
    print("VERIFY OK: the lab tree is installed exactly, first in FolderNames, and alone on cells A and B"
          if not problems else "VERIFY FAILED:\n  " + "\n  ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    if "--verify-installed" in sys.argv:
        sys.exit(verify_installed())
    main()
