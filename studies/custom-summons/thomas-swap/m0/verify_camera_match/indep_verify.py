"""indep_verify.py -- ADVERSARIAL independent re-derivation of the M0 camera-match claims.

Written from scratch against the C# column layout (SfxMeshProbe.cs WriteNativeCamera / WriteModelRow /
LogCamera) and the camera math in PsxCamera.cs (PsxMatrix2UnityMatrix, PerspectiveOffCenter,
PsxProj2UnityProj) + FieldMap.cs (PsxScreenHeightNative=220 -> HalfScreenHeight=110). Does NOT import the
verifiee's module. Goal: try to REFUTE the headline numbers, and demonstrate DISCRIMINATION power by
showing deliberately-wrong variants FAIL.

Column layout (0-indexed after comma-split), verified against SfxMeshProbe.cs:
  PSXCAM: [0]tag [1]effectId [2]frame [3..11]m00..m22 (9) [12..14]tx,ty,tz [15]ofx [16]ofy [17]h [18]psxPtr
  MODEL : [0]tag [1]effectId [2]frame [3]kind [4]slot [5]active [6]hasMotion [7]hasParent [8..10]aux
          [11..13]ax,ay,az(anchor) [14..16]wx,wy,wz(composed) [17..25]m00..m22 [26]bones32
  VIEW  : [0]tag [1]frame [2..17]m00,m01,m02,m03,m10,...,m33 (row-major 4x4)
  PROJ  : [0]tag [1]frame [2..17]row-major 4x4

Native GTE (FORMAT sec 5): p_view = (M.R @ v)>>12 + M.T ; SX = OFX + ((sat16(px)*((H<<16)//sz))>>16), sz=min(65535,pz).
Managed: u = (sx*wx, sy*wy, sz*wz) ; clip = PROJ @ VIEW @ [u,1] ; ndc = clip.xy/clip.w ;
         SX = OFX + halfw*(ndc_x + P02), SY = OFY - HALF_H*(ndc_y + P12), halfw = HALF_H*P11/P00.
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

LOG = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\sfxmeshprobe.log")

DL = np.diag([1.0, -1.0, -1.0])
DR = np.diag([1.0, -1.0, 1.0])
HALF_H = 110.0     # FieldMap.PsxScreenHeightNative(220)/2 -- the projection vertical half. NOT the center (OFY=120).


def sat16(v: int) -> int:
    return -32768 if v < -32768 else (32767 if v > 32767 else v)


# ---------------------------------------------------------------- independent parser
def parse(path: Path, drop: int = 50):
    """Segment into cast sessions by the >drop frame-reset rule. Returns list of dicts of lane data.
    last-wins per (frame) for PSXCAM/MODEL-S; VIEW/PROJ keep the LAST substep of the frame."""
    sessions = []
    cur = None
    smax = -1

    def newsess():
        return dict(psx={}, mods={}, view={}, proj={}, view_n={}, proj_n={})

    cur = newsess(); sessions.append(cur); smax = -1
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] == "#":
                continue
            p = line.rstrip("\n").split(",")
            tag = p[0]
            try:
                if tag in ("VIEW", "PROJ", "CAM"):
                    f = int(p[1])
                elif tag in ("PSXCAM", "MODEL", "MESH", "ROOT", "BONES", "PRIM", "STATE"):
                    f = int(p[2])
                else:
                    continue
            except (ValueError, IndexError):
                continue
            if f < smax - drop:
                cur = newsess(); sessions.append(cur); smax = f
            else:
                smax = max(smax, f)
            try:
                if tag == "PSXCAM":
                    cur["psx"][f] = dict(M=[int(x) for x in p[3:12]], T=[int(x) for x in p[12:15]],
                                         ofx=int(p[15]), ofy=int(p[16]), H=int(p[17]))
                elif tag == "MODEL" and p[3] == "S":
                    cur["mods"][f] = dict(ax=int(p[11]), ay=int(p[12]), az=int(p[13]),
                                          wx=int(p[14]), wy=int(p[15]), wz=int(p[16]), bones=p[26])
                elif tag == "VIEW":
                    m = np.array([float(x) for x in p[2:18]]).reshape(4, 4)
                    cur["view"][f] = m           # last-wins
                    cur["view_n"][f] = cur["view_n"].get(f, 0) + 1
                elif tag == "PROJ":
                    m = np.array([float(x) for x in p[2:18]]).reshape(4, 4)
                    cur["proj"][f] = m
            except (ValueError, IndexError):
                continue
    return sessions


# ---------------------------------------------------------------- native GTE
def gte(cam, w):
    R, T, H = cam["M"], cam["T"], cam["H"]
    vx, vy, vz = w
    px = ((R[0] * vx + R[1] * vy + R[2] * vz) >> 12) + T[0]
    py = ((R[3] * vx + R[4] * vy + R[5] * vz) >> 12) + T[1]
    pz = ((R[6] * vx + R[7] * vy + R[8] * vz) >> 12) + T[2]
    if pz <= 0:
        return None
    sz = min(65535, pz)
    q = (H << 16) // sz
    sx = cam["ofx"] + ((sat16(px) * q) >> 16)
    sy = cam["ofy"] + ((sat16(py) * q) >> 16)
    return float(sx), float(sy), float(pz)


# ---------------------------------------------------------------- managed reprojection
def managed(view, proj, cam, w, signs, scale, half_h=HALF_H):
    u = np.array([signs[0] * scale * w[0], signs[1] * scale * w[1], signs[2] * scale * w[2], 1.0])
    clip = proj @ (view @ u)
    cw = clip[3] if clip[3] != 0 else 1e-9
    ndx, ndy = clip[0] / cw, clip[1] / cw
    p00, p02, p11, p12 = proj[0, 0], proj[0, 2], proj[1, 1], proj[1, 2]
    halfw = half_h * p11 / p00
    sx = cam["ofx"] + halfw * (ndx + p02)
    sy = cam["ofy"] - half_h * (ndy + p12)
    return sx, sy, ndx, ndy


def rot_resid(view, cam):
    M = np.array(cam["M"], dtype=float).reshape(3, 3) / 4096.0
    return float(np.abs(view[:3, :3] - (DL @ M @ DR)).max())


# ---------------------------------------------------------------- drawn-frame collection
def drawn(sess, foff=0):
    out = []
    for f, m in sorted(sess["mods"].items()):
        if m["bones"] == "00000000":
            continue
        if abs(m["wx"] - m["ax"]) > 5000 or abs(m["wy"] - m["ay"]) > 5000 or abs(m["wz"] - m["az"]) > 5000:
            continue
        cf = f + foff
        cam = sess["psx"].get(cf); view = sess["view"].get(cf); proj = sess["proj"].get(cf)
        if cam is None or view is None or proj is None:
            continue
        g = gte(cam, (m["wx"], m["wy"], m["wz"]))
        if g is None:
            continue
        inc = rot_resid(view, cam)
        out.append(dict(f=f, cam=cam, view=view, proj=proj, w=(m["wx"], m["wy"], m["wz"]),
                        sxn=g[0], syn=g[1], pz=g[2], inc=inc, coh=(inc < 0.02)))
    return out


def pct(a, q):
    return float(np.percentile(np.abs(a), q))


def run(path: Path):
    sessions = parse(path)
    print(f"INDEP verify  log={path}")
    print(f"sessions: {len(sessions)}")
    for i, s in enumerate(sessions):
        multi = sum(1 for f, n in s["view_n"].items() if n > 1)
        print(f"  S{i}: psx={len(s['psx'])} modS={len(s['mods'])} view={len(s['view'])} "
              f"proj={len(s['proj'])} multi-substep-frames={multi}")

    # ===== PART (b) per session =====
    print("\n=== PART (b): VIEW.R == DL.(M/4096).DR ; near=110*P11 vs H ; cameraOffset ===")
    print(f"{'sess':>4} | {'nCam':>5} | {'coh%':>5} | {'cohRmax':>9} | {'max|near-H|':>11} | {'camOff mean':>11} | {'camOff range':>16}")
    for i, s in enumerate(sessions):
        rr_coh = []
        near_h = []
        camoff = []
        ncam = 0
        for f, cam in s["psx"].items():
            view = s["view"].get(f); proj = s["proj"].get(f)
            if view is None:
                continue
            ncam += 1
            r = rot_resid(view, cam)
            near = HALF_H * proj[1, 1] if proj is not None else float("nan")
            near_h.append(near - cam["H"])
            # translation-co-sampled: m03==T0 and m13==-T1 to <2 units => VIEW.T and M.T same tick
            offx = view[0, 3] - cam["T"][0]
            offy = view[1, 3] + cam["T"][1]
            offz = -view[2, 3] - cam["T"][2]     # m23 == -(T2+off) => off = -m23 - T2
            if r < 0.02:
                rr_coh.append(r)
                if abs(offx) < 2.0 and abs(offy) < 2.0:
                    camoff.append(offz)
        coh_pct = 100.0 * len(rr_coh) / ncam if ncam else 0.0
        nh = np.abs(near_h).max() if near_h else float("nan")
        co = np.array(camoff) if camoff else np.array([np.nan])
        print(f"{i:>4} | {ncam:>5} | {coh_pct:5.1f} | {max(rr_coh) if rr_coh else float('nan'):9.2e} | "
              f"{nh:11.4f} | {co.mean():+11.4f} | [{co.min():+7.2f},{co.max():+7.2f}]")

    # near vs H, and the 120 WRONG variant -- pooled
    allP11H = []
    for s in sessions:
        for f, cam in s["psx"].items():
            proj = s["proj"].get(f)
            if proj is not None:
                allP11H.append((proj[1, 1], cam["H"]))
    a = np.array(allP11H)
    d110 = np.abs(110.0 * a[:, 0] - a[:, 1])
    d120 = np.abs(120.0 * a[:, 0] - a[:, 1])
    d100 = np.abs(100.0 * a[:, 0] - a[:, 1])
    print(f"\n  FOCAL discrimination (pooled {len(a)} frames):")
    print(f"    near=110*P11 vs H : max|d|={d110.max():.4f}  mean={d110.mean():.4f}   <-- claim")
    print(f"    near=120*P11 vs H : max|d|={d120.max():.4f}  mean={d120.mean():.4f}   (the 240/2 trap -- WRONG)")
    print(f"    near=100*P11 vs H : max|d|={d100.max():.4f}  mean={d100.mean():.4f}   (wrong)")

    # ===== PART (a) per session, on-screen (|managed ndc|<1) =====
    print("\n=== PART (a): source map (1,-1,1),1.0 -- ON-SCREEN (|ndc|<1) per session ===")
    print(f"{'sess':>4} | {'nOn':>5} | {'Xmed':>6} {'Xp95':>6} | {'Ymed':>6} {'Yp95':>6} | {'Rp95':>6} | {'biasX':>6} {'biasY':>6}")
    pool_dx, pool_dy = [], []
    for i, s in enumerate(sessions):
        rows = [r for r in drawn(s, 0) if r["coh"]]
        dxs, dys = [], []
        for r in rows:
            sx, sy, ndx, ndy = managed(r["view"], r["proj"], r["cam"], r["w"], (1, -1, 1), 1.0)
            if abs(ndx) < 1.0 and abs(ndy) < 1.0:
                dxs.append(sx - r["sxn"]); dys.append(sy - r["syn"])
        dxs = np.array(dxs); dys = np.array(dys)
        pool_dx.append(dxs); pool_dy.append(dys)
        print(f"{i:>4} | {len(dxs):>5} | {np.median(np.abs(dxs)):6.2f} {pct(dxs,95):6.2f} | "
              f"{np.median(np.abs(dys)):6.2f} {pct(dys,95):6.2f} | "
              f"{pct(np.sqrt(dxs**2+dys**2),95):6.2f} | {dxs.mean():+6.2f} {dys.mean():+6.2f}")
    DX = np.concatenate(pool_dx); DY = np.concatenate(pool_dy)
    R = np.sqrt(DX**2 + DY**2)
    print(f"  POOLED n={len(DX)}: X med={np.median(np.abs(DX)):.3f} p95={pct(DX,95):.3f} | "
          f"Y med={np.median(np.abs(DY)):.3f} p95={pct(DY,95):.3f} | R med={np.median(R):.3f} p95={np.percentile(R,95):.3f}")
    print(f"  POOLED signed bias: dX={DX.mean():+.3f}  dY={DY.mean():+.3f}")

    # ===== DISCRIMINATION on a clean full session (S2, independent of their S0/S1 emphasis) =====
    print("\n=== DISCRIMINATION (session 2, coherent+on-screen frames) ===")
    s = sessions[2]
    base_rows = [r for r in drawn(s, 0) if r["coh"]]

    def eval_variant(signs, scale, half_h, onscreen=True):
        dxs, dys = [], []
        for r in base_rows:
            sx, sy, ndx, ndy = managed(r["view"], r["proj"], r["cam"], r["w"], signs, scale, half_h)
            if onscreen and not (abs(ndx) < 1.0 and abs(ndy) < 1.0):
                continue
            dxs.append(sx - r["sxn"]); dys.append(sy - r["syn"])
        dxs = np.array(dxs); dys = np.array(dys)
        rr = np.sqrt(dxs**2 + dys**2)
        return len(dxs), float(np.median(rr)), pct(dxs, 95), pct(dys, 95), float(np.percentile(rr, 95))

    print(f"  {'variant':<28} | {'n':>4} | {'Rmed':>7} | {'Xp95':>7} | {'Yp95':>7} | {'Rp95':>8}")
    variants = [
        ("SOURCE (1,-1,1) s1 h110", (1, -1, 1), 1.0, 110.0),
        ("HALF_H=120 (240/2 trap)", (1, -1, 1), 1.0, 120.0),
        ("HALF_H=100", (1, -1, 1), 1.0, 100.0),
        ("signs (1,1,1)  no Y flip", (1, 1, 1), 1.0, 110.0),
        ("signs (1,-1,-1) Z flip", (1, -1, -1), 1.0, 110.0),
        ("signs (-1,-1,1) X flip", (-1, -1, 1), 1.0, 110.0),
        ("scale 1.05", (1, -1, 1), 1.05, 110.0),
        ("scale 0.95", (1, -1, 1), 0.95, 110.0),
    ]
    for name, sg, sc, hh in variants:
        n, rmed, xp, yp, rp = eval_variant(sg, sc, hh)
        print(f"  {name:<28} | {n:>4} | {rmed:7.2f} | {xp:7.2f} | {yp:7.2f} | {rp:8.2f}")

    # phase-lead: median radial by camera-frame offset, source map, on-screen coherent
    print("\n  phase-lead (source map, on-screen coherent, S2): median radial px")
    for foff in (-2, -1, 0, 1, 2):
        rows = [r for r in drawn(s, foff) if r["coh"]]
        dd = []
        for r in rows:
            sx, sy, ndx, ndy = managed(r["view"], r["proj"], r["cam"], r["w"], (1, -1, 1), 1.0)
            if abs(ndx) < 1.0 and abs(ndy) < 1.0:
                dd.append(np.hypot(sx - r["sxn"], sy - r["syn"]))
        dd = np.array(dd)
        print(f"    offset {foff:+d}: median={np.median(dd):.4f}  n={len(dd)}")

    # ===== ALTERNATIVE on-screen definition: NATIVE SX,SY inside frame (independent of managed ndc) =====
    print("\n=== ALT on-screen definition (native SX in [0,320], SY in [0,240]) -- pooled all sessions ===")
    adx, ady = [], []
    for s in sessions:
        for r in [rr for rr in drawn(s, 0) if rr["coh"]]:
            if 0 <= r["sxn"] <= 320 and 0 <= r["syn"] <= 240:
                sx, sy, _, _ = managed(r["view"], r["proj"], r["cam"], r["w"], (1, -1, 1), 1.0)
                adx.append(sx - r["sxn"]); ady.append(sy - r["syn"])
    adx = np.array(adx); ady = np.array(ady)
    ar = np.sqrt(adx**2 + ady**2)
    print(f"  n={len(adx)}: X med={np.median(np.abs(adx)):.3f} p95={pct(adx,95):.3f} | "
          f"Y med={np.median(np.abs(ady)):.3f} p95={pct(ady,95):.3f} | R p95={np.percentile(ar,95):.3f}")


if __name__ == "__main__":
    run(Path(sys.argv[1]) if len(sys.argv) > 1 else LOG)
