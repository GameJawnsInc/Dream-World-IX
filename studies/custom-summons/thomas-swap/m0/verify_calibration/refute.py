"""refute.py -- ADVERSARIAL independent re-derivation of the M0(c) calibration claims.

Independent of m0/calibrate.py (own parser, own reprojection, own session split). Only shared
assumption is the native GTE ground-truth math (FORMAT.md sec5 / flight_v9) which is well-established
on this log. Runs on the sessions the analyst did NOT headline (session 4 full, session 1 short) plus a
control (session 0) for equality, and adds hostile discrimination tests the analyst did not run:
  * TIGHT scale variants (0.5, 0.9, 1.1, 2.0) -- not just /256, x256.
  * a WRONG vertical screen-center (120 instead of 110) to prove the sub-pixel dy is NOT a loose test.
  * det<0 climax-hold check (C7) recomputed from the raw composed 3x3.
  * scale-sweep (C6) recomputed from column norms.
  * VIEW==PsxMatrix2UnityMatrix(M) (C2) recomputed on an unused session.
Also cross-checks my session boundaries against the orchestrator's MODEL-reset line numbers.
"""
from __future__ import annotations
import math

LOG = r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/sfxmeshprobe.log"
OFX, OFY = 160, 120
NW, NH = 320.0, 220.0          # native screen; NH/2 = 110 is the managed vertical center

def sat16(v):
    return -32768 if v < -32768 else (32767 if v > 32767 else v)

# -------------------------------------------------- parse + segment (my own)
def parse(path):
    sessions = []
    boundaries = []          # line numbers where a new session starts (for the external cross-check)
    cur = None
    ceiling = -1
    def blank():
        return dict(psxcam={}, model={}, bones={}, view={}, proj={}, root={})
    cur = blank(); sessions.append(cur)
    for lineno, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        if not line or line[0] == "#":
            continue
        p = line.rstrip("\n").split(",")
        t = p[0]
        if t == "VIEW" or t == "PROJ":
            f = int(p[1])
        elif t in ("PSXCAM", "MODEL", "BONES", "ROOT"):
            f = int(p[2])
        else:
            continue
        if f < ceiling - 50:
            cur = blank(); sessions.append(cur); boundaries.append((lineno, t, f))
            ceiling = f
        else:
            ceiling = max(ceiling, f)
        if t == "PSXCAM":
            cur["psxcam"][f] = ([int(x) for x in p[3:12]], [int(p[12]), int(p[13]), int(p[14])],
                                int(p[17]), int(p[15]), int(p[16]))
        elif t == "MODEL" and p[3] == "S":
            cur["model"][f] = dict(anchor=(int(p[11]), int(p[12]), int(p[13])),
                                   world=(int(p[14]), int(p[15]), int(p[16])),
                                   m=[int(x) for x in p[17:26]], bones32=p[26])
        elif t == "BONES":
            cur["bones"][f] = ((int(p[7]), int(p[8]), int(p[9])), (int(p[10]), int(p[11]), int(p[12])))
        elif t == "VIEW":
            cur["view"][f] = [float(x) for x in p[2:18]]
        elif t == "PROJ":
            cur["proj"][f] = [float(x) for x in p[2:18]]
        elif t == "ROOT":
            cur["root"][f] = (int(p[3]), [int(x) for x in p[4:13]])
    return [s for s in sessions if s["psxcam"]], boundaries

# -------------------------------------------------- native GTE ground truth
def native_screen(R, T, H, v):
    px = ((R[0]*v[0] + R[1]*v[1] + R[2]*v[2]) >> 12) + T[0]
    py = ((R[3]*v[0] + R[4]*v[1] + R[5]*v[2]) >> 12) + T[1]
    pz = ((R[6]*v[0] + R[7]*v[1] + R[8]*v[2]) >> 12) + T[2]
    if pz <= 0:
        return None
    sz = min(65535, pz)
    q = (H << 16) // sz
    return (OFX + ((sat16(px)*q) >> 16), OFY + ((sat16(py)*q) >> 16), pz)

# -------------------------------------------------- managed reprojection (my own)
def view_from_M(R, T):
    # PsxCamera.PsxMatrix2UnityMatrix(pmat,0) -- exactly PsxCamera.cs:103-120
    return [ R[0]/4096.0, -R[1]/4096.0,  R[2]/4096.0, float(T[0]),
            -R[3]/4096.0,  R[4]/4096.0, -R[5]/4096.0, float(-T[1]),
            -R[6]/4096.0,  R[7]/4096.0, -R[8]/4096.0, float(-T[2]),
             0.0, 0.0, 0.0, 1.0]

def managed_screen(view, proj, v, sign, scale, vcenter=110.0):
    ux, uy, uz = v[0]*sign[0]*scale, v[1]*sign[1]*scale, v[2]*sign[2]*scale
    # world -> camera
    vx = view[0]*ux + view[1]*uy + view[2]*uz + view[3]
    vy = view[4]*ux + view[5]*uy + view[6]*uz + view[7]
    vz = view[8]*ux + view[9]*uy + view[10]*uz + view[11]
    # camera -> clip (proj row-major)
    cx = proj[0]*vx + proj[1]*vy + proj[2]*vz + proj[3]
    cy = proj[4]*vx + proj[5]*vy + proj[6]*vz + proj[7]
    cw = proj[12]*vx + proj[13]*vy + proj[14]*vz + proj[15]
    if abs(cw) < 1e-6:
        return None
    ndcx, ndcy = cx/cw, cy/cw
    return (OFX + (NW/2.0)*ndcx, vcenter - (NH/2.0)*ndcy, cw)

CANDS = {
    "A (x,-y,z) s1":  ((1, -1, 1), 1.0),
    "B (x,-y,-z) s1": ((1, -1, -1), 1.0),
    "C (x,y,z) s1":   ((1, 1, 1), 1.0),
    "D (-x,-y,z) s1": ((-1, -1, 1), 1.0),
    "A s0.5":         ((1, -1, 1), 0.5),
    "A s0.9":         ((1, -1, 1), 0.9),
    "A s1.1":         ((1, -1, 1), 1.1),
    "A s2.0":         ((1, -1, 1), 2.0),
}
DEPTH_MIN = 200.0

def median(xs):
    s = sorted(xs); n = len(s)
    return s[n//2] if n % 2 else 0.5*(s[n//2-1]+s[n//2])

def stable(sess, f):
    if f not in sess["view"] or f not in sess["psxcam"]:
        return False
    R, T, H, _, _ = sess["psxcam"][f]
    vm = sess["view"][f]
    return abs(vm[3]-T[0]) + abs(vm[7]+T[1]) + abs(vm[11]+T[2]) <= 30.0

def points(sess):
    for f in sorted(sess["model"]):
        m = sess["model"][f]
        if m["bones32"] == "00000000":
            continue
        w = m["world"]; a = m["anchor"]
        if abs(w[0]-a[0]) > 5000 or abs(w[1]-a[1]) > 5000 or abs(w[2]-a[2]) > 5000:
            continue
        if f not in sess["psxcam"] or f not in sess["view"] or f not in sess["proj"]:
            continue
        yield f, "node0", w
        if f in sess["bones"]:
            mn, mx = sess["bones"][f]
            for cx in (mn[0], mx[0]):
                for cy in (mn[1], mx[1]):
                    for cz in (mn[2], mx[2]):
                        yield f, "corner", (cx, cy, cz)

def reproject(sess, mode, vcenter=110.0):
    res = {c: {"node0": ([], []), "corner": ([], [])} for c in CANDS}
    for f, kind, w in points(sess):
        if mode == "logged" and not stable(sess, f):
            continue
        R, T, H, _, _ = sess["psxcam"][f]
        ns = native_screen(R, T, H, w)
        if ns is None or ns[2] < DEPTH_MIN:
            continue
        view = sess["view"][f] if mode == "logged" else view_from_M(R, T)
        proj = sess["proj"][f]
        for c, (sign, scale) in CANDS.items():
            ms = managed_screen(view, proj, w, sign, scale, vcenter)
            if ms is None or ms[2] < DEPTH_MIN:
                continue
            res[c][kind][0].append(ms[0]-ns[0]); res[c][kind][1].append(ms[1]-ns[1])
    return res

def report_reproj(sess, si, mode, vcenter=110.0):
    res = reproject(sess, mode, vcenter)
    tag = "mderived(pure calib)" if mode == "mderived" else "logged(stable)"
    vc = "" if vcenter == 110.0 else f"  [WRONG vcenter={vcenter}]"
    print(f"  session {si} [{tag}]{vc}")
    for kind in ("node0", "corner"):
        rows = []
        for c in CANDS:
            dxs, dys = res[c][kind]
            if not dxs:
                continue
            mdx = median([abs(x) for x in dxs]); mdy = median([abs(y) for y in dys])
            md = median([math.hypot(a, b) for a, b in zip(dxs, dys)])
            rows.append((md, c, mdx, mdy, len(dxs)))
        rows.sort()
        win = rows[0]
        runner = rows[1] if len(rows) > 1 else (float("nan"), "-", 0, 0, 0)
        print(f"    {kind:6s} WIN {win[1]:14s} med|d|={win[0]:8.2f}px (dx={win[2]:.2f} dy={win[3]:.2f} n={win[4]})"
              f"   runner {runner[1]:14s} {runner[0]:.1f}px")
        # explicitly show A and the tight scale variants for discrimination
        for c in ("A (x,-y,z) s1", "A s0.9", "A s1.1", "A s0.5", "A s2.0", "B (x,-y,-z) s1", "D (-x,-y,z) s1"):
            dxs, dys = res[c][kind]
            if dxs:
                md = median([math.hypot(a, b) for a, b in zip(dxs, dys)])
                mdy = median([abs(y) for y in dys])
                print(f"        {c:16s} med|d|={md:9.2f}px  med|dy|={mdy:7.2f}px")

def view_check(sess, si):
    SGN = [1, -1, 1, -1, 1, -1, -1, 1, -1]
    rot = []; tr = []
    for f in sorted(set(sess["view"]) & set(sess["psxcam"])):
        R, T, H, _, _ = sess["psxcam"][f]
        vm = sess["view"][f]
        got = [vm[0], vm[1], vm[2], vm[4], vm[5], vm[6], vm[8], vm[9], vm[10]]
        exp = [SGN[i]*R[i]/4096.0 for i in range(9)]
        rot += [abs(g-e) for g, e in zip(got, exp)]
        tr.append(abs(vm[3]-T[0]) + abs(vm[7]+T[1]) + abs(vm[11]+T[2]))
    print(f"  session {si}: VIEW vs PsxMatrix2UnityMatrix(M): rot mean {sum(rot)/len(rot):.2e} max {max(rot):.2e};"
          f" translation |sum| mean {sum(tr)/len(tr):.2f} (temporal)")

def det3(m):  # m row-major 9
    return (m[0]*(m[4]*m[8]-m[5]*m[7]) - m[1]*(m[3]*m[8]-m[5]*m[6]) + m[2]*(m[3]*m[7]-m[4]*m[6]))

def det_check(sess, si):
    proper = improper = 0; imp_frames = []
    for f in sorted(sess["model"]):
        m = sess["model"][f]
        if m["bones32"] == "00000000":
            continue
        mm = m["m"]
        cn = [math.sqrt(mm[j]**2 + mm[j+3]**2 + mm[j+6]**2) for j in range(3)]
        if min(cn) < 1.0:
            continue
        d = det3(mm)
        if d > 0:
            proper += 1
        else:
            improper += 1; imp_frames.append(f)
    span = f"f{imp_frames[0]}..f{imp_frames[-1]}" if imp_frames else "-"
    print(f"  session {si}: raw composed node-0 3x3 det: proper {proper}, IMPROPER(det<0) {improper}  ({span})")
    return imp_frames

def scale_sweep(sess, si):
    def cn(m):
        return max(math.sqrt(m[0]**2+m[3]**2+m[6]**2), math.sqrt(m[1]**2+m[4]**2+m[7]**2),
                   math.sqrt(m[2]**2+m[5]**2+m[8]**2)) / 4096.0
    vals = []
    for f in sorted(sess["model"]):
        m = sess["model"][f]
        if m["bones32"] == "00000000":
            continue
        s = cn(m["m"])
        if s > 1e-4:
            vals.append((f, s))
    rvals = []
    for f in sorted(sess["root"]):
        act, m = sess["root"][f]
        if act == 0:
            continue
        s = cn(m)
        if s > 1e-4:
            rvals.append((f, s))
    if vals:
        lo = min(vals, key=lambda t: t[1]); hi = max(vals, key=lambda t: t[1])
        print(f"  session {si}: composed col-norm scale {lo[1]:.4f}x@f{lo[0]} .. {hi[1]:.4f}x@f{hi[0]}", end="")
    if rvals:
        lo = min(rvals, key=lambda t: t[1]); hi = max(rvals, key=lambda t: t[1])
        print(f"   | ROOT anchor {lo[1]:.4f}x .. {hi[1]:.4f}x")
    else:
        print()

def main():
    sessions, boundaries = parse(LOG)
    print(f"PARSED {len(sessions)} sessions")
    for si, s in enumerate(sessions):
        fr = sorted(s["model"])
        print(f"  session {si}: model-S frames {fr[0]}..{fr[-1]} ({len(fr)}), psxcam {len(s['psxcam'])}")
    print("session boundary line numbers (my split):", [b[0] for b in boundaries])
    print("  (orchestrator MODEL-reset line numbers: 50608, 72192, 122732, 173220)")

    print("\n== C2: VIEW == PsxMatrix2UnityMatrix(M)  on UNUSED session 4 + short session 1 ==")
    for si in (4, 1):
        view_check(sessions[si], si)

    print("\n== C1/C3/C4/C5: reprojection + discrimination on UNUSED session 4, short session 1, control 0 ==")
    for si in (4, 1, 0):
        report_reproj(sessions[si], si, "mderived")
    print("\n  -- real-hybrid (logged VIEW) on session 4 --")
    report_reproj(sessions[4], 4, "logged")

    print("\n== discrimination: FORCE a WRONG vertical center (120 not 110) on session 4, map A ==")
    report_reproj(sessions[4], 4, "mderived", vcenter=120.0)

    print("\n== C7: det<0 climax hold (unused session 4 + control 0) ==")
    for si in (4, 0):
        det_check(sessions[si], si)

    print("\n== C6: scale sweep (unused session 4 + control 0) ==")
    for si in (4, 0):
        scale_sweep(sessions[si], si)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
