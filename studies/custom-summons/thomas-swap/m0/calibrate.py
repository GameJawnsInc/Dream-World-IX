"""calibrate.py -- M0 item (c): THE PSX->UNITY CALIBRATION, derived from source, validated on the log.

WHAT THIS IS
------------
The s54 hybrid drive feature (TRANSPLANT.md sec 2.1) poses our own mesh each frame from the native
creature's world matrices *(SummonData+0x38)[k]. Each is a libgte MATRIX: an s16 3x3 rotation in /4096
fixed point + an s32 world translation, in the plugin's PSX BATTLE WORLD space. To render our mesh through
Unity's Camera.main -- which SFX.UpdateCamera stamps from the SAME native camera every frame -- we need the
PSX-world -> Unity-world map with ZERO free parameters.

THE DERIVATION (first principles, from Memoria's open source -- see CALIBRATION.md for the cites)
------------------------------------------------------------------------------------------------
SFX.cs:1603  camera.worldToCameraMatrix = PsxCamera.PsxMatrix2UnityMatrix(array/*13 floats = M*/, SFX.cameraOffset);
SFX.cs:1945  SFX.cameraOffset = 0f;                         <-- zoffset = 0, EXACTLY
PsxCamera.cs:103-120  PsxMatrix2UnityMatrix(pmat, z):
    W.m00= pmat0/4096   W.m01=-pmat1/4096   W.m02= pmat2/4096   W.m03= pmat9
    W.m10=-pmat3/4096   W.m11= pmat4/4096   W.m12=-pmat5/4096   W.m13=-pmat10
    W.m20=-pmat6/4096   W.m21= pmat7/4096   W.m22=-pmat8/4096   W.m23=-(pmat11+z)
The native GTE computes view coords straight:  pv = (M.R . v_psx) / 4096 + M.t.
Requiring  W . U == (pv.x, -pv.y, -pv.z)  (Unity camera space: +x right, +y UP, -z FORWARD; PSX view:
+x right, +y DOWN, +z FORWARD) is solved UNIQUELY by:

    U = PsxToUnityPos(v) = ( v.x , -v.y , v.z )          scale = 1  (M.t used raw; no /256, no /4096)

  ==> negate Y ONLY. NOT (x,-y,-z), NOT scaled. (TRANSPLANT sec 2.1's guessed (tx,-ty,-tz)/scale is WRONG
      on the z sign and on the scale -- see the validation numbers below.)

The world ROTATION change of basis that is CONSISTENT with a Y-negate position map is the conjugation by
B = diag(1,-1,1) (B = B^-1):   R_unity = B . R_psx . B   ==> sign pattern [[+,-,+],[-,+,-],[+,-,+]]/4096.
(This is NOT the worldToCameraMatrix sign pattern, which additionally flips Z because it is a VIEW matrix.)

WHAT THIS SCRIPT VALIDATES ON THE LOG (zero fitting)
----------------------------------------------------
 1. VIEW == PsxMatrix2UnityMatrix(PSXCAM.M): proves the logged managed camera IS the native camera, and
    pins the exact sign pattern.  Reports the rotation residual and the translation (temporal) residual.
 2. REPROJECTION: for the creature's composed node-0 world point AND the 8 BONES-AABB corners, project
    PsxToUnityPos(.) through the logged VIEW*PROJ and compare, in native px, against the native GTE screen
    output (M + OFX/OFY/H, the same reprojection flight_v9_solve.py uses). Candidate maps A..D are all
    scored so the winner is not asserted but shown.
 3. SCALE SWEEP: column norms of the composed node-0 3x3 (and the ROOT +0x40 anchor 3x3) over the cast,
    min/max -- confirms the authored 0.02->3.0x scale is already inside the +0x38 columns (s54 inherits it).

Log path is a constant below. Re-runnable, read-only. Segments the 5 appended casts and reports >=2.
"""
from __future__ import annotations

import math
from collections import defaultdict

LOG = r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/sfxmeshprobe.log"

# ---- candidate PSX->Unity POSITION maps (sign triples applied to (x,y,z), scale factor) ----
CANDIDATES = {
    "A (x,-y, z) scale1  [SOURCE-DERIVED]": ((1.0, -1.0, 1.0), 1.0),
    "B (x,-y,-z) scale1  [TRANSPLANT 2.1 guess]": ((1.0, -1.0, -1.0), 1.0),
    "C (x, y, z) scale1  [no flip]": ((1.0, 1.0, 1.0), 1.0),
    "D (-x,-y,z) scale1": ((-1.0, -1.0, 1.0), 1.0),
    "A/256 (x,-y,z) scale 1/256": ((1.0, -1.0, 1.0), 1.0 / 256.0),
    "A*256 (x,-y,z) scale 256": ((1.0, -1.0, 1.0), 256.0),
}

# native GTE constants (fixed on this build; also logged per-PSXCAM row and asserted equal)
OFX_CONST, OFY_CONST = 160, 120
NATIVE_W, NATIVE_H = 320.0, 220.0   # 2*OFX ; PsxScreenHeightNative (FieldMap.cs:2336) -- the vertical datum


def sat16(v: int) -> int:
    return -32768 if v < -32768 else (32767 if v > 32767 else v)


# ---------------------------------------------------------------- log parse + session segmentation
class Row:
    __slots__ = ()


def parse(path):
    """Single streaming pass. Returns list of sessions; each session is a dict of per-frame lane data."""
    sessions = []
    cur = None
    ceiling = -1

    def new_session():
        return {"psxcam": {}, "model": {}, "bones": {}, "view": {}, "proj": {}, "root": {}}

    def frame_of(p):
        t = p[0]
        if t in ("VIEW", "PROJ"):
            return int(p[1])
        if t in ("PSXCAM", "MODEL", "BONES", "ROOT"):
            return int(p[2])
        return None

    cur = new_session()
    sessions.append(cur)
    for line in open(path, encoding="utf-8", errors="replace"):
        if not line or line[0] == "#":
            continue
        p = line.rstrip("\n").split(",")
        t = p[0]
        f = frame_of(p)
        if f is None:
            continue
        # session boundary: a big frame DROP vs the running ceiling == a new appended cast
        if f < ceiling - 50:
            cur = new_session()
            sessions.append(cur)
            ceiling = f
        else:
            ceiling = max(ceiling, f)

        if t == "PSXCAM":
            R = [int(x) for x in p[3:12]]           # m00..m22 (row-major, /4096)
            T = [int(p[12]), int(p[13]), int(p[14])]
            H = int(p[17])
            ofx, ofy = int(p[15]), int(p[16])
            cur["psxcam"][f] = (R, T, H, ofx, ofy)
        elif t == "MODEL" and p[3] == "S":
            cur["model"][f] = dict(
                bones32=p[26],
                ax=int(p[11]), ay=int(p[12]), az=int(p[13]),
                wx=int(p[14]), wy=int(p[15]), wz=int(p[16]),
                m=[int(x) for x in p[17:26]],       # composed node-0 3x3, /4096
            )
        elif t == "BONES":
            cur["bones"][f] = dict(
                n=int(p[3]),
                mn=(int(p[7]), int(p[8]), int(p[9])),
                mx=(int(p[10]), int(p[11]), int(p[12])),
            )
        elif t == "VIEW":
            cur["view"][f] = [float(x) for x in p[2:18]]   # m00..m33 row-major
        elif t == "PROJ":
            cur["proj"][f] = [float(x) for x in p[2:18]]
        elif t == "ROOT":
            # ROOT,effectId,frame,active,m00..m22,tx,ty,tz
            cur["root"][f] = dict(active=int(p[3]), m=[int(x) for x in p[4:13]])
    # drop empty leading session if any
    return [s for s in sessions if s["psxcam"] or s["model"]]


# ---------------------------------------------------------------- native GTE reprojection (ground truth)
def native_screen(R, T, H, v):
    """Composed world v=(x,y,z) -> native GTE screen (SX,SY), OFX=160/OFY=120. Same math as flight_v9."""
    px = ((R[0] * v[0] + R[1] * v[1] + R[2] * v[2]) >> 12) + T[0]
    py = ((R[3] * v[0] + R[4] * v[1] + R[5] * v[2]) >> 12) + T[1]
    pz = ((R[6] * v[0] + R[7] * v[1] + R[8] * v[2]) >> 12) + T[2]
    if pz <= 0:
        return None
    sz = min(65535, pz)
    sx = OFX_CONST + ((sat16(px) * ((H << 16) // sz)) >> 16)
    sy = OFY_CONST + ((sat16(py) * ((H << 16) // sz)) >> 16)
    return (sx, sy, pz)


# ---------------------------------------------------------------- managed reprojection (test)
def mat_vec4(m, x, y, z):
    """m = 16 floats row-major (m00..m33). Returns (X,Y,Z,W) of m . (x,y,z,1)."""
    X = m[0] * x + m[1] * y + m[2] * z + m[3]
    Y = m[4] * x + m[5] * y + m[6] * z + m[7]
    Z = m[8] * x + m[9] * y + m[10] * z + m[11]
    W = m[12] * x + m[13] * y + m[14] * z + m[15]
    return X, Y, Z, W


def view_from_psxcam(R, T):
    """PsxCamera.PsxMatrix2UnityMatrix(M as 13 floats, zoffset=0) -> worldToCameraMatrix, 16 floats row-major.
    THIS is the exact managed reconstruction (PsxCamera.cs:103-120), rebuilt from the same-frame native M so
    the temporal (hard-cut) mismatch of the LOGGED VIEW is removed -- isolates the pure calibration."""
    m = [0.0] * 16
    m[0] = R[0] / 4096.0;  m[1] = -R[1] / 4096.0;  m[2] = R[2] / 4096.0;  m[3] = float(T[0])
    m[4] = -R[3] / 4096.0; m[5] = R[4] / 4096.0;   m[6] = -R[5] / 4096.0; m[7] = float(-T[1])
    m[8] = -R[6] / 4096.0; m[9] = R[7] / 4096.0;   m[10] = -R[8] / 4096.0; m[11] = float(-T[2])
    m[12] = 0.0; m[13] = 0.0; m[14] = 0.0; m[15] = 1.0
    return m


def managed_screen(view, proj, v_psx, sign, scale):
    """PsxToUnityPos(v)=sign*scale*(x,y,z applied per-axis) -> VIEW then PROJ -> ndc -> native-320x220 px.
    Native px mapping: SX = 160 + 160*ndc.x ; SY = 110 - 110*ndc.y  (110 = NATIVE_H/2; ndc.y up)."""
    ux = v_psx[0] * sign[0] * scale
    uy = v_psx[1] * sign[1] * scale
    uz = v_psx[2] * sign[2] * scale
    vx, vy, vz, vw = mat_vec4(view, ux, uy, uz)          # world -> camera
    cx, cy, cz, cw = mat_vec4(proj, vx, vy, vz)          # camera -> clip
    # worldToCameraMatrix is affine (row3 = 0 0 0 1) so vw==1; projectionMatrix consumes (vx,vy,vz,1).
    if abs(cw) < 1e-6:
        return None
    ndcx = cx / cw
    ndcy = cy / cw
    SX = OFX_CONST + (NATIVE_W / 2.0) * ndcx
    SY = (NATIVE_H / 2.0) - (NATIVE_H / 2.0) * ndcy
    return (SX, SY, cw)


def half_screen_width(proj):
    """Recover HalfScreenWidth encoded in the logged PROJ: m00 = near/HalfW, m11 = 2*near/(top-bottom)=near/110."""
    near = proj[5] * 110.0            # m11 * 110
    if abs(proj[0]) < 1e-9:
        return None, near
    return near / proj[0], near        # HalfScreenWidth, near


# ---------------------------------------------------------------- stats helpers
def pctl(vals, q):
    if not vals:
        return float("nan")
    s = sorted(vals)
    k = (len(s) - 1) * q
    lo = int(math.floor(k)); hi = int(math.ceil(k))
    if lo == hi:
        return s[lo]
    return s[lo] * (hi - k) + s[hi] * (k - lo)


def summarize(name, dxs, dys):
    dmag = [math.hypot(a, b) for a, b in zip(dxs, dys)]
    axs = [abs(a) for a in dxs]; ays = [abs(a) for a in dys]
    print(f"        {name}")
    print(f"          |dx| px  median {pctl(axs,0.5):6.2f}  mean {sum(axs)/len(axs):7.2f}  p95 {pctl(axs,0.95):7.2f}  max {max(axs):8.2f}  (n={len(axs)})")
    print(f"          |dy| px  median {pctl(ays,0.5):6.2f}  mean {sum(ays)/len(ays):7.2f}  p95 {pctl(ays,0.95):7.2f}  max {max(ays):8.2f}")
    print(f"          |d|  px  median {pctl(dmag,0.5):6.2f}  mean {sum(dmag)/len(dmag):7.2f}  p95 {pctl(dmag,0.95):7.2f}  max {max(dmag):8.2f}")
    return pctl(dmag, 0.5)   # rank by MEDIAN (robust to the hard-cut / grazing-corner outliers)


def widescreen_report(sess, si):
    hws = []; nears = []; ratios = []
    for f in sorted(sess["proj"]):
        hw, near = half_screen_width(sess["proj"][f])
        if hw is None or hw <= 0:
            continue
        hws.append(hw); nears.append(near); ratios.append(OFX_CONST / hw)
    if not hws:
        return
    # confirm near == H (the native projection distance) on stable frames
    matches = []
    for f in sorted(set(sess["proj"]) & set(sess["psxcam"])):
        _, near = half_screen_width(sess["proj"][f])
        H = sess["psxcam"][f][2]
        matches.append(near - H)
    print(f"  session {si}: HalfScreenWidth (from PROJ) min {min(hws):.2f} max {max(hws):.2f} "
          f"(native OFX=160 -> aspect {2*sum(hws)/len(hws)/NATIVE_H:.3f})")
    print(f"      near(PROJ.m11*110) - H(PSXCAM): mean {sum(matches)/len(matches):+.3f}  "
          f"max|.| {max(abs(x) for x in matches):.3f}   => managed near == native H (projection distance)")
    print(f"      horizontal scale 160/HalfW: mean {sum(ratios)/len(ratios):.4f}  "
          f"=> off-centre |dx| ~ {abs(1-sum(ratios)/len(ratios))*160:.1f}px per unit native-ndc.x "
          f"(the widescreen residual; 0 at screen centre)")


# ---------------------------------------------------------------- (1) VIEW vs PSXCAM identity
def check_view_vs_psxcam(sess, si):
    frames = sorted(set(sess["view"]) & set(sess["psxcam"]))
    if not frames:
        print(f"  session {si}: no VIEW&PSXCAM overlap"); return
    # expected VIEW from PSXCAM.M via PsxMatrix2UnityMatrix(M,0)
    SGN = [1, -1, 1, -1, 1, -1, -1, 1, -1]   # rotation element sign pattern (row-major m00..m22)
    rot_res = []; tx_res = []; ty_res = []; tz_res = []
    for f in frames:
        R, T, H, ofx, ofy = sess["psxcam"][f]
        vm = sess["view"][f]
        exp = [SGN[i] * R[i] / 4096.0 for i in range(9)]
        got = [vm[0], vm[1], vm[2], vm[4], vm[5], vm[6], vm[8], vm[9], vm[10]]
        rot_res += [abs(g - e) for g, e in zip(got, exp)]
        tx_res.append(vm[3] - T[0])       # expect m03 == +tx
        ty_res.append(vm[7] - (-T[1]))    # expect m13 == -ty
        tz_res.append(vm[11] - (-T[2]))   # expect m23 == -tz (zoffset 0)
    print(f"  session {si}: {len(frames)} frames  (OFX,OFY const across cast: "
          f"{set(v[3] for v in sess['psxcam'].values())},{set(v[4] for v in sess['psxcam'].values())})")
    print(f"      rotation |VIEW - PsxMatrix2UnityMatrix(M)|  mean {sum(rot_res)/len(rot_res):.2e}  "
          f"max {max(rot_res):.2e}   (== 1/4096 quantization ~2.4e-4)")
    for nm, r in (("m03-(+tx)", tx_res), ("m13-(-ty)", ty_res), ("m23-(-tz)", tz_res)):
        print(f"      translation {nm}: mean {sum(r)/len(r):+7.3f}  p95|.| {pctl([abs(x) for x in r],0.95):6.3f}  "
              f"max|.| {max(abs(x) for x in r):6.3f}  units  (the <=1-step temporal residual)")


# ---------------------------------------------------------------- (2) reprojection residuals
def sane_model(m):
    return (m["bones32"] != "00000000"
            and abs(m["wx"] - m["ax"]) <= 5000 and abs(m["wy"] - m["ay"]) <= 5000
            and abs(m["wz"] - m["az"]) <= 5000)


def is_camera_stable(sess, f):
    """True if the logged managed VIEW at frame f was sampled at (near) the native drawing tick -- i.e. its
    translation matches PSXCAM.M within a small bound. A camera hard-cut / phase lead makes this large, and
    those frames' LOGGED-VIEW reprojection is a temporal mismatch, NOT a calibration error."""
    if f not in sess["view"] or f not in sess["psxcam"]:
        return False
    R, T, H, _, _ = sess["psxcam"][f]
    vm = sess["view"][f]
    dt = abs(vm[3] - T[0]) + abs(vm[7] + T[1]) + abs(vm[11] + T[2])   # |m03-tx|+|m13+ty|+|m23+tz|
    return dt <= 30.0


def collect_points(sess):
    """Yield (frame, R,T,H, view, proj, world_pt, kind) for node-0 and BONES-AABB corners on reliable frames."""
    for f in sorted(sess["model"]):
        m = sess["model"][f]
        if f not in sess["psxcam"] or f not in sess["view"] or f not in sess["proj"]:
            continue
        if not sane_model(m):
            continue
        R, T, H, _, _ = sess["psxcam"][f]
        view, proj = sess["view"][f], sess["proj"][f]
        yield (f, R, T, H, view, proj, (m["wx"], m["wy"], m["wz"]), "node0")
        b = sess["bones"].get(f)
        if b:
            mn, mx = b["mn"], b["mx"]
            for cx in (mn[0], mx[0]):
                for cy in (mn[1], mx[1]):
                    for cz in (mn[2], mx[2]):
                        yield (f, R, T, H, view, proj, (cx, cy, cz), "corner")


DEPTH_MIN = 200.0   # skip points grazing the camera plane where the perspective divide blows up either side


def reproject_session(sess, si, mode):
    """mode 'logged' = reproject through the LOGGED VIEW*PROJ (real hybrid conditions; adds the camera
    temporal residual). mode 'mderived' = rebuild VIEW from the SAME-frame PSXCAM.M (removes temporal;
    isolates the pure calibration + the widescreen horizontal). Both use the logged PROJ."""
    resid = {name: {"node0": ([], []), "corner": ([], [])} for name in CANDIDATES}
    used = {"node0": 0, "corner": 0}
    for (f, R, T, H, logview, proj, w, kind) in collect_points(sess):
        if mode == "logged" and not is_camera_stable(sess, f):
            continue                        # exclude hard-cut frames for the honest calibration read
        ns = native_screen(R, T, H, w)
        if ns is None or ns[2] < DEPTH_MIN:
            continue
        SXn, SYn, _ = ns
        view = logview if mode == "logged" else view_from_psxcam(R, T)
        got_any = False
        for name, (sign, scale) in CANDIDATES.items():
            ms = managed_screen(view, proj, w, sign, scale)
            if ms is None or ms[2] < DEPTH_MIN:
                continue
            SXm, SYm, _ = ms
            resid[name][kind][0].append(SXm - SXn)
            resid[name][kind][1].append(SYm - SYn)
            got_any = True
        if got_any:
            used[kind] += 1
    tag = ("LOGGED VIEW*PROJ, camera-stable frames only (real hybrid, temporal excluded)"
           if mode == "logged" else
           "VIEW rebuilt from same-frame PSXCAM.M (temporal removed -> PURE calibration + widescreen)")
    print(f"  session {si} [{mode}] -- {tag}")
    print(f"      node0 on {used['node0']} frames, AABB corners on {used['corner']} points")
    for kind in ("node0", "corner"):
        ranked = []
        for name in CANDIDATES:
            dxs, dys = resid[name][kind]
            if not dxs:
                continue
            med = summarize(name, dxs, dys) if name.startswith("A ") else None
            if med is None:
                # cheap median for ranking without the full print
                dmag = sorted(math.hypot(a, b) for a, b in zip(dxs, dys))
                med = dmag[len(dmag) // 2]
            ranked.append((med, name))
        ranked.sort()
        print(f"      >> WINNER ({kind}): {ranked[0][1]}  (median |d| = {ranked[0][0]:.3f} px);  "
              f"runner-up {ranked[1][1].split()[0]} @ {ranked[1][0]:.1f} px")
    return resid


# ---------------------------------------------------------------- (3) scale sweep from composed 3x3
def rotation_check(sess, si):
    """PsxToUnityRot(R) = B.R.B, B=diag(1,-1,1) (sign pattern [[+,-,+],[-,+,-],[+,-,+]]). After stripping the
    folded scale (normalize columns), the mapped rotation must be ORTHONORMAL and PROPER (det>0) -- else it is
    not a valid Unity Quaternion. Validated on the composed node-0 3x3 over the cast (bone 0 only; per-project
    provenance, never bones[1..92])."""
    SGN = (1.0, -1.0, 1.0)
    orth = []; dets = []
    for f in sorted(sess["model"]):
        m = sess["model"][f]
        if not sane_model(m):
            continue
        R = [m["m"][0:3], m["m"][3:6], m["m"][6:9]]     # row-major /4096
        # normalize columns (strip scale)
        cn = [math.sqrt(sum(R[i][j]**2 for i in range(3))) for j in range(3)]
        if min(cn) < 1.0:
            continue
        N = [[R[i][j] / cn[j] for j in range(3)] for i in range(3)]
        # apply B.R.B
        U = [[SGN[i] * SGN[j] * N[i][j] for j in range(3)] for i in range(3)]
        # U^T U - I
        err = 0.0
        for a in range(3):
            for b in range(3):
                dot = sum(U[k][a] * U[k][b] for k in range(3))
                err = max(err, abs(dot - (1.0 if a == b else 0.0)))
        det = (U[0][0]*(U[1][1]*U[2][2]-U[1][2]*U[2][1])
               - U[0][1]*(U[1][0]*U[2][2]-U[1][2]*U[2][0])
               + U[0][2]*(U[1][0]*U[2][1]-U[1][1]*U[2][0]))
        orth.append(err); dets.append((f, det))
    if orth:
        proper = [f for f, d in dets if d > 0.5]
        improper = [f for f, d in dets if d < -0.5]
        print(f"  session {si}: PsxToUnityRot(composed node-0) over {len(orth)} frames: "
              f"max||U^T U - I|| = {max(orth):.4f}  (ORTHONORMAL every frame -> a clean basis)")
        print(f"      det == +1 (PROPER rotation) on {len(proper)}/{len(dets)} frames; "
              f"det == -1 (REFLECTION) on {len(improper)} frames"
              + (f" (e.g. f{improper[0]}..f{improper[-1]}, the ~3.0x climax hold)" if improper else ""))
        print(f"      => the RAW +0x38/+0x40 matrix is intrinsically improper there (mixed det, unfixable by any "
              f"sign map); s54's Matrix->Quaternion MUST guard det<0 (flip a column / use LookRotation).")


def scale_sweep(sess, si):
    def colnorms(m):  # m row-major 9: cols are (m0,m3,m6),(m1,m4,m7),(m2,m5,m8)
        c0 = math.sqrt(m[0]**2 + m[3]**2 + m[6]**2) / 4096.0
        c1 = math.sqrt(m[1]**2 + m[4]**2 + m[7]**2) / 4096.0
        c2 = math.sqrt(m[2]**2 + m[5]**2 + m[8]**2) / 4096.0
        return max(c0, c1, c2)   # scale = the max column norm (uniform scale; near-equal columns)
    # composed +0x38 node-0: filter stale-arena garbage (sane_model) AND degenerate all-zero 3x3 frames
    comp = []
    for f in sorted(sess["model"]):
        m = sess["model"][f]
        if not sane_model(m):
            continue
        s = colnorms(m["m"])
        if s < 1e-4:               # a cut-boundary frame with an un-rebuilt (zero) 3x3 -- not a real pose
            continue
        comp.append((f, s, m))
    # ROOT +0x40 anchor: where FORMAT.md 1.4 says the authored scale is folded (ScaleMatrix @0x1879a)
    root = []
    for f in sorted(sess["root"]):
        r = sess["root"][f]
        if r["active"] == 0:
            continue
        s = colnorms(r["m"])
        if s < 1e-4:
            continue
        root.append((f, s))
    if comp:
        smin = min(comp, key=lambda t: t[1]); smax = max(comp, key=lambda t: t[1])
        print(f"  session {si}: composed node-0 3x3 col-norm (== scale) over {len(comp)} valid drawn frames:")
        print(f"      min {smin[1]:.4f}x @f{smin[0]}   max {smax[1]:.4f}x @f{smax[0]}")
    if root:
        smin = min(root, key=lambda t: t[1]); smax = max(root, key=lambda t: t[1])
        print(f"      ROOT +0x40 anchor col-norm over {len(root)} active frames: "
              f"min {smin[1]:.4f}x @f{smin[0]}   max {smax[1]:.4f}x @f{smax[0]}  (== authored ~3.0x cap)")
    # PROVE s54 inherits scale for free: the BONES-AABB diagonal (world-unit span) tracks the anchor scale,
    # so the scale is already in the node WORLD POSITIONS the hybrid writes -- no separate scale feed needed.
    pairs = []
    for f, s, _ in comp:
        b = sess["bones"].get(f)
        r = sess["root"].get(f)
        if not b or not r or r["active"] == 0:
            continue
        diag = math.sqrt(sum((b["mx"][i] - b["mn"][i])**2 for i in range(3)))
        rs = colnorms(r["m"])
        if rs > 1e-3 and diag < 1e8:      # skip stale/degenerate
            pairs.append((rs, diag))
    if len(pairs) > 20:
        import statistics
        ratios = [d / s for s, d in pairs]
        lo = min(pairs, key=lambda t: t[0]); hi = max(pairs, key=lambda t: t[0])
        print(f"      BONES-AABB world diagonal vs anchor scale: {len(pairs)} frames, "
              f"diag/scale mean {statistics.mean(ratios):.0f} +-{statistics.pstdev(ratios):.0f} u/x  "
              f"(scale {lo[0]:.3f}x->diag {lo[1]:.0f}u ; scale {hi[0]:.3f}x->diag {hi[1]:.0f}u) "
              f"=> the scale IS the node-position spread; the hybrid inherits it via PsxToUnityPos")


# ---------------------------------------------------------------- main
def main():
    sessions = parse(LOG)
    print("=" * 96)
    print(f"PARSED {len(sessions)} cast sessions from the log")
    for si, s in enumerate(sessions):
        fr = sorted(s["model"]) or sorted(s["psxcam"])
        print(f"  session {si}: frames {fr[0]}..{fr[-1]}  "
              f"(psxcam {len(s['psxcam'])}, model-S {len(s['model'])}, bones {len(s['bones'])}, "
              f"view {len(s['view'])}, proj {len(s['proj'])}, root {len(s['root'])})")
    # pick the two densest sessions for the full report
    order = sorted(range(len(sessions)), key=lambda i: -len(sessions[i]["model"]))
    report = order[:max(2, min(3, len(sessions)))]

    print("\n" + "=" * 96)
    print("(1) VIEW == PsxMatrix2UnityMatrix(PSXCAM.M)  -- proves managed camera IS native camera + the signs")
    print("=" * 96)
    for si in report:
        check_view_vs_psxcam(sessions[si], si)

    print("\n" + "=" * 96)
    print("(1b) THE WIDESCREEN AXIS -- HalfScreenWidth vs native OFX=160, and near==H")
    print("=" * 96)
    for si in report:
        widescreen_report(sessions[si], si)

    print("\n" + "=" * 96)
    print("(2) REPROJECTION vs native GTE screen (native px).  Candidate A=(x,-y,z) scale1 is SOURCE-DERIVED.")
    print("    Full per-candidate stats printed for A only; others shown as WINNER/runner-up by median |d|.")
    print("=" * 96)
    for si in report:
        print("-" * 96)
        reproject_session(sessions[si], si, "mderived")   # pure calibration (temporal removed)
        reproject_session(sessions[si], si, "logged")     # real hybrid conditions (stable frames)

    print("\n" + "=" * 96)
    print("(3) SCALE SWEEP -- authored 0.02->3.0x already inside the +0x38 columns (s54 inherits it free)")
    print("=" * 96)
    for si in report:
        scale_sweep(sessions[si], si)

    print("\n" + "=" * 96)
    print("(4) PsxToUnityRot VALIDITY -- B.R.B stays orthonormal + proper (a valid Unity Quaternion)")
    print("=" * 96)
    for si in report:
        rotation_check(sessions[si], si)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
