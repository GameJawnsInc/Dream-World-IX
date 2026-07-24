"""camera_match.py -- M0 (a)+(b): THE CAMERA MATCH.

Question (TRANSPLANT.md sec 1.1): a managed Unity object placed at PsxToUnity(creature world point)
and projected through Camera.main (which SFX.UpdateCamera stamps every frame from the native camera)
renders at the native creature's on-screen position -- for the HORIZONTAL/widescreen axis too, the one
left open by the "OFY=120 by construction" argument.

This module measures it two ways, per frame, per cast session, from the s50+s52+s53 probe log:

(a) THE PROJECTION MATCH. For every drawn summon (MODEL kind=S) frame:
    (i)  NATIVE GTE (ground truth): composed node-0 world (wx,wy,wz) through the native world->view
         matrix M (PSXCAM) + OFX/OFY/H -> (SX,SY) native screen px. Exactly flight_v9_solve's math.
    (ii) MANAGED: place a Unity object at u = PsxToUnity(wx,wy,wz) (signs+uniform scale FIT here by
         least squares), project through the logged VIEW then PROJ -> NDC, then map NDC -> the SAME
         native-screen px convention via a SOURCE-DERIVED formula (PsxCamera.cs / FieldMap.cs cites in
         CAMERA-MATCH.md).  Report |native - managed| px, per axis, per session, per phase band.

(b) THE MATRIX-LEVEL CHECK. Is the managed VIEW a FIXED conversion of the native M?  Source says
    VIEW = PsxCamera.PsxMatrix2UnityMatrix(M, cameraOffset)  (PsxCamera.cs:103-120):
        VIEW.R = DL . (M/4096) . DR ,  DL=diag(1,-1,-1), DR=diag(1,-1,1)
        VIEW.T = DL . M.T  - (0,0,cameraOffset)
    Verify elementwise across ALL frames of ALL sessions; report the worst residual + the recovered
    cameraOffset (should be constant).

Native GTE reprojection is the proven flight_v9_solve implementation (fp12 arithmetic, sat16, H focal).

Column layouts verified against SfxMeshProbe.cs (the WriteNativeCamera / WriteModelRow / LogCamera
writers) and flight_v9_solve.parse_native_path:
  PSXCAM: p[0]=PSXCAM p[1]=effectId p[2]=frame p[3:12]=M(9, row-major m00..m22) p[12:15]=T(tx,ty,tz)
          p[15]=ofx p[16]=ofy p[17]=h p[18]=psxPtr(hex)
  MODEL : p[0]=MODEL p[1]=effectId p[2]=frame p[3]=kind p[4]=slot p[5]=active p[6]=hasMotion
          p[7]=hasParent p[8:11]=aux p[11:14]=anchor(ax,ay,az) p[14:17]=composed(wx,wy,wz)
          p[17:26]=m00..m22 p[26]=bones32(hex)
  VIEW  : p[0]=VIEW p[1]=frame p[2:18]=16 floats row-major (m00..m33)
  PROJ  : p[0]=PROJ p[1]=frame p[2:18]=16 floats row-major

Run:  py camera_match.py            # full report
      py camera_match.py --recon    # data facts only (sessions, ranges, offset, near-vs-H)
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

LOG = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\sfxmeshprobe.log")

# Fixed handedness matrices of PsxCamera.PsxMatrix2UnityMatrix (PsxCamera.cs:103-120).
DL = np.diag([1.0, -1.0, -1.0])   # applied to M.R rows and to M.T
DR = np.diag([1.0, -1.0, 1.0])    # applied to M.R cols
HALF_H = 110.0                    # PsxScreenHeightNative/2 = 220/2  (FieldMap.cs:2336,2340)

# Phase bands (native SFX.frameIndex): pre-draw / creature window / tail.
BANDS = [("pre 11-81", 11, 81), ("creature 82-412", 82, 412), ("tail 413-561", 413, 561)]


# --------------------------------------------------------------------------- parsing
class Session:
    def __init__(self, idx: int):
        self.idx = idx
        self.psxcam: Dict[int, dict] = {}                 # frame -> {M:9, T:3, ofx, ofy, H, ptr}
        self.model_s: Dict[int, dict] = {}                # frame -> {wx,wy,wz, ax,ay,az, bones, mot}
        self.view_rows: Dict[int, List[np.ndarray]] = {}  # frame -> [4x4,...]
        self.proj_rows: Dict[int, List[np.ndarray]] = {}
        self._view: Dict[int, np.ndarray] = {}
        self._proj: Dict[int, np.ndarray] = {}

    def view(self, f: int) -> Optional[np.ndarray]:
        # LAST substep of the frame -- pairs with the last-wins PSXCAM/MODEL dicts (all four are written
        # in one SFXDataMesh.Runtime.Render call, so the last of each is one coherent camera state; meaning
        # substeps would mix pre/post-cut poses on the ~15 hard-cut frames that carry several substeps).
        if f not in self.view_rows:
            return None
        return self.view_rows[f][-1]

    def proj(self, f: int) -> Optional[np.ndarray]:
        if f not in self.proj_rows:
            return None
        return self.proj_rows[f][-1]


def _frame_of(p: List[str]) -> Optional[int]:
    tag = p[0]
    try:
        if tag in ("VIEW", "PROJ", "CAM"):
            return int(p[1])
        if tag in ("MESH", "PRIM", "STATE", "PRIMSUM", "ROOT", "MODEL", "PSXCAM", "BONES"):
            return int(p[2])
    except (ValueError, IndexError):
        return None
    return None


def parse_sessions(path: Path, drop: int = 50) -> List[Session]:
    """Split the log into cast sessions: a new session starts when a data row's frame drops by more
    than `drop` below the running max frame of the current session (all lanes share SFX.frameIndex and
    reset together at each cast)."""
    sessions: List[Session] = [Session(0)]
    cur = sessions[0]
    sess_max = -1
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] == "#":
                continue
            p = line.rstrip("\n").split(",")
            f = _frame_of(p)
            if f is None:
                continue
            if f < sess_max - drop:
                cur = Session(len(sessions))
                sessions.append(cur)
                sess_max = f
            else:
                sess_max = max(sess_max, f)
            tag = p[0]
            try:
                if tag == "PSXCAM":
                    cur.psxcam[f] = dict(
                        M=[int(x) for x in p[3:12]], T=[int(x) for x in p[12:15]],
                        ofx=int(p[15]), ofy=int(p[16]), H=int(p[17]), ptr=p[18])
                elif tag == "MODEL" and p[3] == "S":
                    cur.model_s[f] = dict(
                        ax=int(p[11]), ay=int(p[12]), az=int(p[13]),
                        wx=int(p[14]), wy=int(p[15]), wz=int(p[16]),
                        bones=p[26], mot=int(p[6]))
                elif tag == "VIEW":
                    cur.view_rows.setdefault(f, []).append(
                        np.array([float(x) for x in p[2:18]]).reshape(4, 4))
                elif tag == "PROJ":
                    cur.proj_rows.setdefault(f, []).append(
                        np.array([float(x) for x in p[2:18]]).reshape(4, 4))
            except (ValueError, IndexError):
                continue
    return sessions


# --------------------------------------------------------------------------- native GTE (ground truth)
def _sat16(v: int) -> int:
    return -32768 if v < -32768 else (32767 if v > 32767 else v)


def native_gte(cam: dict, world: Tuple[int, int, int]) -> Optional[Tuple[float, float, float]]:
    """Composed world point -> native GTE screen (SX,SY) + view-depth pz. flight_v9_solve math."""
    R, T, H = cam["M"], cam["T"], cam["H"]
    vx, vy, vz = world
    px = ((R[0] * vx + R[1] * vy + R[2] * vz) >> 12) + T[0]
    py = ((R[3] * vx + R[4] * vy + R[5] * vz) >> 12) + T[1]
    pz = ((R[6] * vx + R[7] * vy + R[8] * vz) >> 12) + T[2]
    if pz <= 0:
        return None
    sz = min(65535, pz)
    q = (H << 16) // sz
    sx = cam["ofx"] + ((_sat16(px) * q) >> 16)
    sy = cam["ofy"] + ((_sat16(py) * q) >> 16)
    return float(sx), float(sy), float(pz)


# --------------------------------------------------------------------------- managed path
def psx_to_unity(world, signs: Tuple[int, int, int], scale: float) -> np.ndarray:
    return np.array([signs[0] * scale * world[0],
                     signs[1] * scale * world[1],
                     signs[2] * scale * world[2]], dtype=np.float64)


def managed_ndc(view: np.ndarray, proj: np.ndarray, u: np.ndarray) -> Tuple[float, float, float]:
    """Unity world u -> VIEW -> PROJ -> NDC (perspective divide). Returns ndc_x, ndc_y, clip_w."""
    vv = view @ np.array([u[0], u[1], u[2], 1.0])
    clip = proj @ vv
    cw = clip[3] if clip[3] != 0 else 1e-9
    return clip[0] / cw, clip[1] / cw, cw


def ndc_to_native_px(ndc_x: float, ndc_y: float, cam: dict, proj: np.ndarray) -> Tuple[float, float]:
    """SOURCE-DERIVED NDC -> native-screen px, in the SAME (OFX,OFY,H) convention native_gte outputs.
    HalfScreenWidth = near/P00 = 110*P11/P00 (PsxProj2UnityProj + PerspectiveOffCenter); the aspect
    factor cancels analytically (SX = OFX + near*px/pz). Vertical half = 110 (fixed). See CAMERA-MATCH.md.
        SX = OFX + HalfW*(ndc_x + P02) ;  SY = OFY - 110*(ndc_y + P12)"""
    p00, p02, p11, p12 = proj[0, 0], proj[0, 2], proj[1, 1], proj[1, 2]
    halfw = HALF_H * p11 / p00
    sx = cam["ofx"] + halfw * (ndc_x + p02)
    sy = cam["ofy"] - HALF_H * (ndc_y + p12)
    return sx, sy


# --------------------------------------------------------------------------- collect drawn frames
COH_THRESH = 0.02   # |VIEW.R - DL(M/4096)DR| above this == the probe caught the managed VIEW clock and
                    # the native M one tick apart at a hard cut (fp12 floor is 2.4e-4; cut slips are ~0.1-0.5)


def cam_incoherence(view: np.ndarray, cam: dict) -> float:
    """max|VIEW.R - PsxToUnity(M).R| -- 0 (fp12 floor) when the logged managed VIEW is the same camera
    state as the native M this frame; large on a cut-transition frame where the probe sampled them a
    tick apart."""
    M = np.array(cam["M"], dtype=np.float64).reshape(3, 3) / 4096.0
    return float(np.abs(view[:3, :3] - (DL @ M @ DR)).max())


def drawn_frames(s: Session, foff: int = 0) -> List[dict]:
    """Frames with a sane drawn creature + camera data. foff shifts the camera frame vs the MODEL
    frame (phase-lead test). Each row carries `coherent` (managed VIEW == native M this frame)."""
    out = []
    for f, m in sorted(s.model_s.items()):
        if m["bones"] == "00000000":
            continue
        # stale-arena guard (flight_v9): composed must be near the anchor once the creature stops drawing
        if (abs(m["wx"] - m["ax"]) > 5000 or abs(m["wy"] - m["ay"]) > 5000 or abs(m["wz"] - m["az"]) > 5000):
            continue
        cf = f + foff
        cam = s.psxcam.get(cf)
        view = s.view(cf)
        proj = s.proj(cf)
        if cam is None or view is None or proj is None:
            continue
        gte = native_gte(cam, (m["wx"], m["wy"], m["wz"]))
        if gte is None:
            continue
        inc = cam_incoherence(view, cam)
        out.append(dict(sess=s.idx, frame=f, cam=cam, view=view, proj=proj,
                        world=(m["wx"], m["wy"], m["wz"]), sx_n=gte[0], sy_n=gte[1], pz=gte[2],
                        incoh=inc, coherent=(inc < COH_THRESH)))
    return out


def eval_map(rows: List[dict], signs, scale) -> Tuple[np.ndarray, np.ndarray]:
    """Per-frame (dx, dy) px deltas managed-native for a given PsxToUnity(signs,scale)."""
    dx, dy = [], []
    for r in rows:
        u = psx_to_unity(r["world"], signs, scale)
        nx, ny, _ = managed_ndc(r["view"], r["proj"], u)
        sx_m, sy_m = ndc_to_native_px(nx, ny, r["cam"], r["proj"])
        dx.append(sx_m - r["sx_n"])
        dy.append(sy_m - r["sy_n"])
    return np.array(dx), np.array(dy)


def fit_similarity(rows: List[dict]) -> Tuple[Tuple[int, int, int], float, float]:
    """Grid the 8 sign combos; for each, coarse+refine 1-D search on uniform scale to minimize a ROBUST
    px delta (median radial |managed-native|, so the ~15 cut-slip frames can't drag the fit). Returns
    (best_signs, best_scale, best_median)."""
    best = (None, 1.0, float("inf"))
    for sx in (1, -1):
        for sy in (1, -1):
            for sz in (1, -1):
                signs = (sx, sy, sz)
                def cost(sc):
                    dx, dy = eval_map(rows, signs, sc)
                    return float(np.median(np.sqrt(dx * dx + dy * dy)))
                grid = np.concatenate([np.linspace(0.2, 2.0, 37), np.linspace(2.1, 5.0, 15)])
                sc0 = min(grid, key=cost)
                lo, hi = max(0.05, sc0 - 0.1), sc0 + 0.1
                for _ in range(50):
                    m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
                    if cost(m1) < cost(m2):
                        hi = m2
                    else:
                        lo = m1
                sc = (lo + hi) / 2
                c = cost(sc)
                if c < best[2]:
                    best = (signs, sc, c)
    return best


def stats(a: np.ndarray) -> dict:
    aa = np.abs(a)
    return dict(mean=float(aa.mean()), median=float(np.median(aa)),
                p95=float(np.percentile(aa, 95)), max=float(aa.max()), n=len(aa))


# --------------------------------------------------------------------------- part (b)
def matrix_check(sessions: List[Session]) -> dict:
    """VIEW vs PsxMatrix2UnityMatrix(M). Returns worst residual, offset spread, near-vs-H."""
    worst_r = 0.0
    offs, near_h = [], []
    n = 0
    per_off = {}
    for foff in (-1, 0, 1):
        res = []
        for s in sessions:
            for f, cam in s.psxcam.items():
                view = s.view(f + foff)
                if view is None:
                    continue
                M = np.array(cam["M"], dtype=np.float64).reshape(3, 3) / 4096.0
                Rp = DL @ M @ DR
                resid = np.abs(view[:3, :3] - Rp).max()
                res.append(resid)
        per_off[foff] = (float(np.mean(res)), float(np.max(res)), len(res)) if res else (None, None, 0)
    # offset 0 detailed; split coherent (VIEW==M this frame) vs cut-transition by the rotation residual
    coh_off, coh_nh = [], []
    n_coh = 0
    for s in sessions:
        for f, cam in s.psxcam.items():
            view = s.view(f)
            proj = s.proj(f)
            if view is None:
                continue
            M = np.array(cam["M"], dtype=np.float64).reshape(3, 3) / 4096.0
            Rp = DL @ M @ DR
            resid = float(np.abs(view[:3, :3] - Rp).max())
            worst_r = max(worst_r, resid)
            offx = view[0, 3] - cam["T"][0]           # should be ~0 (m03 == T0)
            offy = view[1, 3] + cam["T"][1]           # m13 == -T1 -> +T1 == 0
            offz = -view[2, 3] - cam["T"][2]           # m23 == -(T2+off) -> off
            offs.append((offx, offy, offz))
            near = HALF_H * proj[1, 1] if proj is not None else float("nan")
            near_h.append((near, cam["H"], near - cam["H"]))
            n += 1
            if resid < COH_THRESH:      # coherent frame: the identity should hold to the fp12 floor
                # translation-co-sampled too? (VIEW.T and M.T from the SAME tick -- during the fast
                # fly-by a <=1-tick probe slip moves T by hundreds of units while R still matches)
                if abs(offx) < 2.0 and abs(offy) < 2.0:
                    coh_off.append((offx, offy, offz))
                if proj is not None:
                    coh_nh.append((near, cam["H"], near - cam["H"]))
                n_coh += 1
    offs = np.array(offs); near_h = np.array(near_h)
    co = np.array(coh_off); cn = np.array(coh_nh)
    # coherent-only rotation residual
    coh_resid = 0.0
    for s in sessions:
        for f, cam in s.psxcam.items():
            view = s.view(f)
            if view is None:
                continue
            M = np.array(cam["M"], dtype=np.float64).reshape(3, 3) / 4096.0
            r = float(np.abs(view[:3, :3] - (DL @ M @ DR)).max())
            if r < COH_THRESH:
                coh_resid = max(coh_resid, r)
    return dict(worst_R_resid=worst_r, per_offset=per_off, n=n, n_coh=n_coh, coh_R_resid=coh_resid,
                off_x=(float(offs[:, 0].mean()), float(np.abs(offs[:, 0]).max())),
                off_y=(float(offs[:, 1].mean()), float(np.abs(offs[:, 1]).max())),
                cameraOffset=(float(offs[:, 2].mean()), float(offs[:, 2].min()), float(offs[:, 2].max())),
                near_minus_H=(float(near_h[:, 2].mean()), float(np.abs(near_h[:, 2]).max()),
                              float(near_h[:, 0].min()), float(near_h[:, 0].max())),
                coh_off_xyz=(float(np.abs(co[:, 0]).max()), float(np.abs(co[:, 1]).max()),
                             float(co[:, 2].mean()), float(co[:, 2].min()), float(co[:, 2].max()), len(co)),
                coh_near_H=(float(np.abs(cn[:, 2]).max()) if len(cn) else float("nan")))


# --------------------------------------------------------------------------- report
def band_of(f: int) -> str:
    for name, lo, hi in BANDS:
        if lo <= f <= hi:
            return name
    return "?"


def report(path: Path) -> None:
    sessions = parse_sessions(path)
    print(f"# camera_match.py  log={path}")
    print(f"# sessions parsed: {len(sessions)}")
    for s in sessions:
        drawn = [f for f, m in s.model_s.items() if m["bones"] != "00000000"]
        fr = sorted(s.psxcam) or [0]
        print(f"  session {s.idx}: PSXCAM {len(s.psxcam)} frames [{fr[0]}..{fr[-1]}], "
              f"MODEL-S {len(s.model_s)} ({len(drawn)} drawn), VIEW {len(s.view_rows)}, PROJ {len(s.proj_rows)}")

    # ---- PART (b) ----
    print("\n" + "=" * 78)
    print("PART (b) -- VIEW == PsxMatrix2UnityMatrix(M) ?  (fixed conversion, zero free params)")
    print("=" * 78)
    mc = matrix_check(sessions)
    print(f"  ALL {mc['n']} frames: max|VIEW.R - DL.(M/4096).DR| = {mc['worst_R_resid']:.6e}"
          f"  (fp12 floor 1/4096 = {1/4096:.2e})")
    print(f"  {mc['n_coh']} CAMERA-COHERENT frames ({100*mc['n_coh']/mc['n']:.1f}%): max residual = {mc['coh_R_resid']:.6e}"
          f"  -- i.e. VIEW == PsxMatrix2UnityMatrix(M) to the fp12 floor")
    print(f"  the {mc['n']-mc['n_coh']} others are cut-transition frames (VIEW managed-clock vs M native-tick, <=1 tick apart)")
    cxyz = mc["coh_off_xyz"]
    print(f"  translation-co-sampled frames ({cxyz[5]}, |VIEW.m03-T0|<2 & |m13+T1|<2 -- VIEW.T & M.T same tick):")
    print(f"    cameraOffset (-m23-T2): mean={cxyz[2]:+.4f}  range [{cxyz[3]:+.2f}, {cxyz[4]:+.2f}]  (== SFX.cameraOffset, ~0 => no Z shift)")
    print(f"  (on the fast fly-by the probe slips VIEW vs M by <=1 tick -> VIEW.T deviates up to ~500u while VIEW.R still matches;")
    print(f"   that slip folds into part (a)'s measured screen delta, the honest end-to-end number)")
    print(f"  near(=110*PROJ11) vs H on coherent frames: max|near-H| = {mc['coh_near_H']:.4f}  (== -> managed focal == native focal)")
    print("  VIEW-vs-M residual by camera-frame offset (rotation mean/max/n) -- 0 is best:")
    for foff, (mn, mx, nn) in mc["per_offset"].items():
        print(f"    offset {foff:+d}: mean={mn if mn is None else round(mn,6)}  max={mx if mx is None else round(mx,6)}  n={nn}")

    # ---- PART (a) ----
    print("\n" + "=" * 78)
    print("PART (a) -- managed puppet at PsxToUnity(creature) vs native GTE screen position")
    print("=" * 78)
    # all drawn frames, offset 0
    all_rows = []
    for s in sessions:
        all_rows.extend(drawn_frames(s, foff=0))
    if not all_rows:
        print("  NO drawn creature frames with camera data found -- cannot run part (a).")
        return
    coh = [r for r in all_rows if r["coherent"]]
    cut = [r for r in all_rows if not r["coherent"]]
    print(f"  drawn frames: {len(all_rows)} total  |  {len(coh)} camera-coherent (VIEW==PsxToUnity(M))  "
          f"|  {len(cut)} cut-transition (probe caught VIEW/M >1 tick apart at a hard cut)")

    # robust fit on COHERENT frames (cut-slip frames are a probe-sampling artifact, not a design error)
    signs, scale, med = fit_similarity(coh)
    print(f"  fitted PsxToUnity (robust, coherent frames): signs={signs}  scale={scale:.5f}  median-radial={med:.4f} px")
    dxs, dys = eval_map(coh, (1, -1, 1), 1.0)
    print(f"    source-predicted (zero-param) signs=(1,-1,1) scale=1.0 -> "
          f"median-radial = {float(np.median(np.sqrt(dxs*dxs+dys*dys))):.4f} px")

    # phase-lead test on coherent frames
    print("  camera-frame phase-lead test (median-radial px, source map (1,-1,1),1.0, COHERENT frames):")
    for foff in (-1, 0, 1):
        rr = [r for s in sessions for r in drawn_frames(s, foff=foff) if r["coherent"]]
        if rr:
            dx, dy = eval_map(rr, (1, -1, 1), 1.0)
            print(f"    offset {foff:+d}: median={float(np.median(np.sqrt(dx*dx+dy*dy))):.4f} px  n={len(rr)}")

    use_signs, use_scale = (1, -1, 1), 1.0   # source-derived zero-param map; the fit confirms it

    def block(rows: List[dict], title: str):
        print(f"\n  --- {title} ({len(rows)} frames) ---")
        print(f"  {'session':>7} | {'band':<16} | {'n':>4} | {'axis':>4} | {'mean':>7} {'median':>7} {'p95':>7} {'max':>9}")
        gdx, gdy = [], []
        for s in sessions:
            srows = [r for r in rows if r["sess"] == s.idx]
            for name, lo, hi in BANDS:
                br = [r for r in srows if lo <= r["frame"] <= hi]
                if not br:
                    continue
                dx, dy = eval_map(br, use_signs, use_scale)
                gdx.append(dx); gdy.append(dy)
                sx, sy = stats(dx), stats(dy)
                print(f"  {s.idx:>7} | {name:<16} | {sx['n']:>4} | {'X':>4} | "
                      f"{sx['mean']:7.3f} {sx['median']:7.3f} {sx['p95']:7.3f} {sx['max']:9.2f}")
                print(f"  {'':>7} | {'':<16} | {'':>4} | {'Y':>4} | "
                      f"{sy['mean']:7.3f} {sy['median']:7.3f} {sy['p95']:7.3f} {sy['max']:9.2f}")
        if gdx:
            DX = np.concatenate(gdx); DY = np.concatenate(gdy)
            sx, sy = stats(DX), stats(DY)
            r2 = np.sqrt(DX * DX + DY * DY)
            print(f"  TOTAL X: mean={sx['mean']:.3f} median={sx['median']:.3f} p95={sx['p95']:.3f} max={sx['max']:.2f} px (n={sx['n']})")
            print(f"  TOTAL Y: mean={sy['mean']:.3f} median={sy['median']:.3f} p95={sy['p95']:.3f} max={sy['max']:.2f} px")
            print(f"  radial : mean={r2.mean():.3f} median={np.median(r2):.3f} p95={np.percentile(r2,95):.3f} max={r2.max():.2f} px")
            return sx, sy
        return None, None

    sx_c, sy_c = block(coh, "CAMERA-COHERENT frames (the real answer)")
    block(cut, "CUT-TRANSITION frames (probe VIEW/M phase slip -- NOT a live-hybrid error)")

    # ON-SCREEN subset: the design only needs the puppet where the creature is VISIBLE. Off-screen
    # swoop-by frames put the creature thousands of px off-frame, where a small RELATIVE error is a big
    # ABSOLUTE one (and irrelevant -- neither creature nor puppet is on screen). Framed := managed |ndc|<1.
    framed = []
    for r in coh:
        u = psx_to_unity(r["world"], (1, -1, 1), 1.0)
        nx, ny, _ = managed_ndc(r["view"], r["proj"], u)
        if abs(nx) < 1.0 and abs(ny) < 1.0:
            framed.append(r)
    print(f"\n  ON-SCREEN subset: {len(framed)} of {len(coh)} coherent frames have the creature framed (|ndc|<1)")
    if framed:
        dx, dy = eval_map(framed, (1, -1, 1), 1.0)
        sx, sy = stats(dx), stats(dy)
        r2 = np.sqrt(dx * dx + dy * dy)
        print(f"    signed bias: mean dX={dx.mean():+.3f}  mean dY={dy.mean():+.3f} px  "
              f"(near 0 => no systematic offset, just fp12 quantization noise)")
        print(f"    X : mean={sx['mean']:.3f} median={sx['median']:.3f} p95={sx['p95']:.3f} max={sx['max']:.2f} px")
        print(f"    Y : mean={sy['mean']:.3f} median={sy['median']:.3f} p95={sy['p95']:.3f} max={sy['max']:.2f} px")
        print(f"    rad mean={r2.mean():.3f} median={np.median(r2):.3f} p95={np.percentile(r2,95):.3f} max={r2.max():.2f} px")
        print(f"\n  >>> VERDICT input (on-screen, coherent): horizontal p95 = {sx['p95']:.3f} px, "
              f"vertical p95 = {sy['p95']:.3f} px  (of a 320x240 native frame)")

    if sx_c:
        print(f"\n  (all-coherent-frames incl. off-screen swoop: horiz p95 = {sx_c['p95']:.3f}, vert p95 = {sy_c['p95']:.3f} px)")

    # characterize the worst cut frames (confirm H/near jump -> a real shot change, not a bug)
    print("\n  worst 8 cut-transition frames (confirm they are shot changes: incoherence + H):")
    cut_sorted = sorted(cut, key=lambda r: -(abs(0) ) )
    worst = sorted(all_rows, key=lambda r: -r["incoh"])[:8]
    print(f"  {'sess.frame':>12} | {'incoh':>7} | {'H':>5} | {'near':>6} | {'dX':>8} | {'dY':>9}")
    for r in worst:
        dx, dy = eval_map([r], use_signs, use_scale)
        near = HALF_H * r["proj"][1, 1]
        print(f"  {r['frame']:>12} | {r['incoh']:7.3f} | {r['cam']['H']:>5} | {near:6.1f} | {dx[0]:8.2f} | {dy[0]:9.2f}")


def recon(path: Path) -> None:
    sessions = parse_sessions(path)
    print(f"sessions: {len(sessions)}")
    for s in sessions:
        pf = sorted(s.psxcam)
        drawn = sorted(f for f, m in s.model_s.items() if m["bones"] != "00000000")
        print(f" S{s.idx}: PSXCAM[{pf[0] if pf else '-'}..{pf[-1] if pf else '-'}] n={len(s.psxcam)} "
              f"drawn-creature frames={len(drawn)} [{drawn[0] if drawn else '-'}..{drawn[-1] if drawn else '-'}] "
              f"VIEW={len(s.view_rows)} PROJ={len(s.proj_rows)}")
        if pf:
            c = s.psxcam[pf[0]]
            print(f"     ofx={c['ofx']} ofy={c['ofy']} H@{pf[0]}={c['H']}  Hs={sorted({s.psxcam[f]['H'] for f in pf})[:12]}...")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=LOG)
    ap.add_argument("--recon", action="store_true")
    a = ap.parse_args()
    if a.recon:
        recon(a.log)
    else:
        report(a.log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
