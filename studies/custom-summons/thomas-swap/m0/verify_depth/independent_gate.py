"""independent_gate.py -- ADVERSARIAL, from-scratch re-derivation of the depth-interleave verdict.

Written WITHOUT importing depth_gate.py. Shares only the physics (the native GTE reprojection, which is
ground truth, re-implemented here) and the 7 BODY SFXKeys. Everything downstream -- the discriminator,
the classification, the rollup, the validation, the knob sweep, the spatial-specificity control -- is an
independent code path. Goal: reproduce or REFUTE the author's MIXED/NATIVE-NEEDED verdict.

Independent design choices vs depth_gate.py:
  * effectId FILTER: only eff 227 (the Bahamut cast). depth_gate.py does not filter -- prove it doesn't matter.
  * reliability window derived here from MODEL(S) rows my own way; compared to the gate's 82..412.
  * body signal cross-checked against MESH body tri counts (a source the gate never touches).
  * classification split rolled up per-phase AND overall, with explicit denominators for a >100% audit.
"""
from __future__ import annotations
import statistics
from collections import defaultdict
import numpy as np

LOG = r"C:\gd\SCRATCH\summon-transplant\logs\sfxmeshprobe.20260724-012109.log"
EFF = 227
BODY = {"0033B990", "0033B9D0", "0035BAD0", "0035BA90", "0034BA10", "0034BA50", "0097BD02"}
STALE_TOL = 5000
AABB_PAD = 8.0
NDC_MARGIN = 1.50
MIN_SIDE = 3
FT3_CODE = 36     # POLY_FT3 -- the body's dominant primitive per DEPTH-GATE

PHASES = [
    (82, 144, "P1->P2 rise-to-far"),
    (144, 157, "P2->P3 far-dip"),
    (157, 172, "P3->P4 far-deep hold"),
    (172, 179, "P4->P5 return-cut"),
    (179, 204, "P5->P6 2nd-approach"),
    (204, 207, "P6->P7 charge-cut"),
    (207, 250, "P7->P8 charge-hold"),
    (250, 414, "P8->P9 ground-reign"),
    (414, 417, "P9->P10 exit-edge"),
]


def phase_for(f):
    for lo, hi, lab in PHASES:
        if lo <= f < hi:
            return lab
    return "OUT"


def sat16(v):
    return -32768 if v < -32768 else (32767 if v > 32767 else v)


def project(R, T, H, v):
    """Fresh native-GTE reprojection. world (int) -> (sx, sy, pz) in native 320x240, pz>0 else None."""
    vx, vy, vz = int(v[0]), int(v[1]), int(v[2])
    px = ((R[0] * vx + R[1] * vy + R[2] * vz) >> 12) + T[0]
    py = ((R[3] * vx + R[4] * vy + R[5] * vz) >> 12) + T[1]
    pz = ((R[6] * vx + R[7] * vy + R[8] * vz) >> 12) + T[2]
    if pz <= 0 or H == 0:
        return None
    sz = min(65535, pz)
    q = (H << 16) // sz
    sx = 160 + ((sat16(int(px)) * q) >> 16)
    sy = 120 + ((sat16(int(py)) * q) >> 16)
    return (float(sx), float(sy), float(pz))


# ---- pass 1: PSXCAM, BONES, MODEL(S), MESH(body) -- eff 227 only ----
psxcam, bones, smodel = {}, {}, {}
mesh_body_tri = defaultdict(int)   # frame -> summed body tri count
mesh_body_keys = defaultdict(set)
with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
    for line in fh:
        if not line or line[0] == "#":
            continue
        p = line.rstrip("\n").split(",")
        t = p[0]
        try:
            if t == "PSXCAM" and int(p[1]) == EFF:
                f = int(p[2])
                psxcam[f] = ([int(x) for x in p[3:12]], [int(x) for x in p[12:15]], int(p[17]))
            elif t == "BONES" and int(p[1]) == EFF:
                f = int(p[2])
                bones[f] = dict(cx=float(p[4]), cy=float(p[5]), cz=float(p[6]),
                                mnx=float(p[7]), mny=float(p[8]), mnz=float(p[9]),
                                mxx=float(p[10]), mxy=float(p[11]), mxz=float(p[12]))
            elif t == "MODEL" and len(p) > 26 and p[3] == "S" and int(p[1]) == EFF:
                f = int(p[2])
                smodel[f] = (p[26], int(p[14]), int(p[15]), int(p[16]), int(p[11]), int(p[12]), int(p[13]))
            elif t == "MESH" and int(p[1]) == EFF and p[4] in BODY:
                f = int(p[2])
                mesh_body_tri[f] += int(p[6])
                mesh_body_keys[f].add(p[4])
        except (ValueError, IndexError):
            continue

# ---- reliability (creature present) -- my own derivation ----
reliable = set()
for f, (b32, wx, wy, wz, ax, ay, az) in smodel.items():
    if b32 == "00000000":
        continue
    if abs(wx - ax) > STALE_TOL or abs(wy - ay) > STALE_TOL or abs(wz - az) > STALE_TOL:
        continue
    reliable.add(f)
print(f"[reliable creature frames] n={len(reliable)}  window [{min(reliable)}..{max(reliable)}]")
print(f"[MESH body-key window]     frames [{min(mesh_body_tri)}..{max(mesh_body_tri)}]  "
      f"(frames with >=1 body key: {sum(1 for f in mesh_body_tri if mesh_body_tri[f] > 0)})")

# ---- build creature frames: AABB + depth band + framed ----
class CF:
    __slots__ = ("aabb", "zmin", "zmax", "depth", "framed", "csx", "csy")

creature = {}
for f in reliable:
    cam = psxcam.get(f)
    b = bones.get(f)
    if cam is None or b is None:
        continue
    R, T, H = cam
    corners = [(x, y, z) for x in (b["mnx"], b["mxx"]) for y in (b["mny"], b["mxy"]) for z in (b["mnz"], b["mxz"])]
    sxs, sys_, pzs = [], [], []
    for c in corners:
        pr = project(R, T, H, c)
        if pr:
            sxs.append(pr[0]); sys_.append(pr[1]); pzs.append(pr[2])
    if not sxs:
        continue
    cen = project(R, T, H, (b["cx"], b["cy"], b["cz"]))
    if cen is None:
        continue
    cf = CF()
    cf.aabb = (min(sxs) - AABB_PAD, max(sxs) + AABB_PAD, min(sys_) - AABB_PAD, max(sys_) + AABB_PAD)
    cf.zmin, cf.zmax, cf.depth = min(pzs), max(pzs), cen[2]
    ndc_x = (cen[0] - 160.0) / 160.0
    ndc_y = (120.0 - cen[1]) / 120.0
    cf.framed = abs(ndc_x) <= NDC_MARGIN and abs(ndc_y) <= NDC_MARGIN
    cf.csx, cf.csy = cen[0], cen[1]
    creature[f] = cf
n_framed = sum(1 for c in creature.values() if c.framed)
print(f"[creature frames w/ PSXCAM+BONES] n={len(creature)}  framed={n_framed}")


def margin(depth, frac=0.055, floor=64.0):
    return max(floor, frac * depth)


# ---- self-calibrate widescreen offset (my own: median x-delta of depth+y-matched prims) ----
def calibrate_offset():
    deltas = []
    with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.startswith("PRIM,"):
                continue
            p = line.rstrip("\n").split(",")
            try:
                if int(p[1]) != EFF:
                    continue
                f = int(p[2]); raw = -float(p[6]); x = float(p[7]); y = float(p[8])
            except (ValueError, IndexError):
                continue
            cf = creature.get(f)
            if cf is None or not cf.framed:
                continue
            if abs(y - cf.csy) > 8.0:
                continue
            if abs(raw - cf.depth) > 0.10 * max(1.0, cf.depth):
                continue
            deltas.append(x - cf.csx)
    return (statistics.median(deltas) if len(deltas) >= 8 else 0.0), len(deltas)


OFFSET, ncal = calibrate_offset()
print(f"[widescreen offset] {OFFSET:+.2f}px (n={ncal})")


# ---- pass 2: classify inside-silhouette prims. Collect richly so I can run MANY variants offline. ----
# per framed frame: list of (raw_otz, code) for prims inside the (offset-corrected) silhouette box.
inside = defaultdict(list)
ft3_per_frame_all = defaultdict(int)     # ALL FT3 prims in stream (body signal, no box) -- for tail check
with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
    for line in fh:
        if not line.startswith("PRIM,"):
            continue
        p = line.rstrip("\n").split(",")
        try:
            if int(p[1]) != EFF:
                continue
            f = int(p[2]); code = int(p[4]); raw = -float(p[6]); x = float(p[7]); y = float(p[8])
        except (ValueError, IndexError):
            continue
        if (code & 252) == FT3_CODE:
            ft3_per_frame_all[f] += 1
        cf = creature.get(f)
        if cf is None or not cf.framed:
            continue
        xmin, xmax, ymin, ymax = cf.aabb
        xc = x - OFFSET
        if xmin <= xc <= xmax and ymin <= y <= ymax:
            inside[f].append((raw, code))

print("done pass 2")
np.save("inside.npy", np.array([1]))  # touch (unused, keeps import warm)


# ============================ VALIDATIONS ============================
print("\n================= VALIDATION 1: undrawn-tail body signal =================")
# FT3 (body) prim count per frame across the drawn->undrawn boundary.
for f in range(408, 420):
    tag = ""
    if f in reliable and f not in [x for x in reliable if x > 415]:
        pass
    mark = "reliable" if f in reliable else "STALE/undrawn"
    print(f"  f{f}: FT3(all)={ft3_per_frame_all.get(f,0):5d}  body-MESH-tri={mesh_body_tri.get(f,0):5d}  "
          f"keys={len(mesh_body_keys.get(f,set()))}  [{mark}]")
tail_frames = [f for f in ft3_per_frame_all if f > 417]
tail_ft3 = [ft3_per_frame_all[f] for f in tail_frames]
print(f"  tail (f>417): {len(tail_frames)} frames, total FT3={sum(tail_ft3)}, "
      f"max/frame={max(tail_ft3) if tail_ft3 else 0}")

print("\n================= VALIDATION 2: FT3 prims vs MESH body tri (correlation) =================")
# On drawn frames, body FT3 prim count should track the summed drawn body tri count.
xs, ys = [], []
for f in sorted(reliable):
    if mesh_body_tri.get(f, 0) > 0 and ft3_per_frame_all.get(f, 0) > 0:
        xs.append(mesh_body_tri[f]); ys.append(ft3_per_frame_all[f])
if len(xs) > 5:
    r = np.corrcoef(xs, ys)[0, 1]
    ratio = np.median([b / a for a, b in zip(xs, ys)])
    print(f"  n={len(xs)} drawn frames; corr(MESH body tri, FT3 prim count) = {r:.3f}; "
          f"median FT3/tri ratio = {ratio:.2f}")
    print(f"  (a high corr => the FT3 'body signal' really tracks the drawn body mesh, not effects)")

print("\n================= VALIDATION 3: body-FT3 overshoot beyond band (DEPTH_EPS_FRAC calib) =================")
# For framed frames, take FT3 prims INSIDE the silhouette that fall OUTSIDE [zmin,zmax]; measure the
# overshoot as a fraction of centroid depth. This is the author's 0.055 (p90) claim -- reproduce it.
overshoot_frac = []
for f, prims in inside.items():
    cf = creature[f]
    for raw, code in prims:
        if (code & 252) != FT3_CODE:
            continue
        if raw < cf.zmin:
            overshoot_frac.append((cf.zmin - raw) / max(1.0, cf.depth))
        elif raw > cf.zmax:
            overshoot_frac.append((raw - cf.zmax) / max(1.0, cf.depth))
if overshoot_frac:
    a = np.array(overshoot_frac)
    print(f"  n={len(a)} out-of-band FT3 prims; overshoot/depth  p50={np.percentile(a,50):.4f} "
          f"p90={np.percentile(a,90):.4f} p99={np.percentile(a,99):.4f}  (author claims p90~=0.055)")


# ============================ THE GATE (my rollup), parametric ============================
def run_gate(frac, floor=64.0, mode="band", min_side=MIN_SIDE, box_shift=None, label=""):
    """mode: 'band' = author's band exclusion; 'centroid' = split at centroid depth (NO body exclusion);
    box_shift=(dx,dy) => translate every creature box by (dx,dy) screen px (spatial-specificity control)."""
    ph = {lab: dict(frmd=0, front=0, behind=0, strad=0) for _, _, lab in PHASES}
    ph["OUT"] = dict(frmd=0, front=0, behind=0, strad=0)
    for f, cf in creature.items():
        if not cf.framed:
            continue
        lab = phase_for(f)
        ph[lab]["frmd"] += 1
        # recompute inside-box membership if shifting the box
        if box_shift is None:
            prims = inside[f]
        else:
            dx, dy = box_shift
            xmin, xmax, ymin, ymax = cf.aabb
            xmin += dx; xmax += dx; ymin += dy; ymax += dy
            prims = [(raw, code) for (raw, code, x, y) in inside_xy[f]
                     if xmin <= (x - OFFSET) <= xmax and ymin <= y <= ymax]
        m = margin(cf.depth, frac, floor)
        nf = nb = 0
        for raw, code in prims:
            if mode == "band":
                if raw < cf.zmin - m:
                    nf += 1
                elif raw > cf.zmax + m:
                    nb += 1
            else:  # centroid split -- no body band at all
                if raw < cf.depth - m:
                    nf += 1
                elif raw > cf.depth + m:
                    nb += 1
        front = nf >= min_side
        behind = nb >= min_side
        if front:
            ph[lab]["front"] += 1
        if behind:
            ph[lab]["behind"] += 1
        if front and behind:
            ph[lab]["strad"] += 1
    # verdict
    def verdict(d):
        if d["frmd"] < 5:
            return "INSUF"
        st = d["strad"] / d["frmd"]; fr = d["front"] / d["frmd"]
        if st > 0.15 or fr > 0.33:
            return "NATIVE"
        if fr > 0.05 or st > 0:
            return "BORDER"
        return "HYBRID"
    tot_frmd = tot_fr = tot_st = tot_bh = 0
    natives = []
    print(f"\n  [{label}] mode={mode} frac={frac} floor={floor} min_side={min_side} "
          f"box_shift={box_shift}")
    print(f"    {'phase':22s} {'frmd':>4} {'front':>5} {'strad':>5} {'behind':>6}  verdict")
    for _, _, lab in PHASES:
        d = ph[lab]
        if d["frmd"] == 0:
            continue
        v = verdict(d)
        if v == "NATIVE":
            natives.append(lab)
        tot_frmd += d["frmd"]; tot_fr += d["front"]; tot_st += d["strad"]; tot_bh += d["behind"]
        print(f"    {lab:22s} {d['frmd']:4d} {d['front']/d['frmd']:5.0%} {d['strad']/d['frmd']:5.0%} "
              f"{d['behind']/d['frmd']:6.0%}  {v}")
    if tot_frmd:
        print(f"    {'OVERALL':22s} {tot_frmd:4d} {tot_fr/tot_frmd:5.0%} {tot_st/tot_frmd:5.0%} "
              f"{tot_bh/tot_frmd:6.0%}   NATIVE-phases={natives}")
    return natives, (tot_fr, tot_st, tot_bh, tot_frmd)


# For box-shift variants I need x,y too:
inside_xy = defaultdict(list)
with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
    for line in fh:
        if not line.startswith("PRIM,"):
            continue
        p = line.rstrip("\n").split(",")
        try:
            if int(p[1]) != EFF:
                continue
            f = int(p[2]); code = int(p[4]); raw = -float(p[6]); x = float(p[7]); y = float(p[8])
        except (ValueError, IndexError):
            continue
        cf = creature.get(f)
        if cf is None or not cf.framed:
            continue
        # store ALL prims on framed frames (not just inside) so a shifted box can re-select
        inside_xy[f].append((raw, code, x, y))

print("\n================= THE GATE: nominal (my independent rollup) =================")
run_gate(0.055, mode="band", label="NOMINAL")

print("\n================= KNOB SWEEP (discrimination power) =================")
run_gate(0.0275, mode="band", label="frac 0.5x")
run_gate(0.110, mode="band", label="frac 2x")
run_gate(0.220, mode="band", label="frac 4x (DEPTH_EPS x4)")
run_gate(2.0, mode="band", label="frac HUGE (band swallows everything)")
run_gate(0.055, mode="centroid", label="NO BODY EXCLUSION (centroid split)")

print("\n================= SPATIAL SPECIFICITY (random-box control) =================")
import random
random.seed(1234)
# creature box sizes: measure typical w,h
ws = [cf.aabb[1] - cf.aabb[0] for cf in creature.values() if cf.framed]
hs = [cf.aabb[3] - cf.aabb[2] for cf in creature.values() if cf.framed]
print(f"  creature box median w={statistics.median(ws):.0f} h={statistics.median(hs):.0f} px "
      f"(native 320x240 frame)")
for trial, (dx, dy) in enumerate([(90, 0), (-90, 0), (0, 70), (0, -70), (70, 70)]):
    run_gate(0.055, mode="band", box_shift=(dx, dy), label=f"box shifted ({dx:+d},{dy:+d})")
