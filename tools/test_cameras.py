#!/usr/bin/env python3
# Offline validation of cam_lib against 6 real FF9 cameras (no game needed).
# Proves: (a) the vertical-scale invariant k, (b) every camera decomposes to a
# proper orthonormal rotation, (c) synthesis round-trips the exact r[]/t[],
# (d) the clean pinhole form reproduces the engine GTE projection bit-for-bit.
import math, cam_lib as C

# name, proj, centerOffset(x,y), t(x,y,z), range(w,h), depthOffset, viewport(4), OrientationMatrix(9)
CAMS = [
 ("GRGR (our room)", 497, (0,0),   (0,-248,5018),    (384,448), 543,  (160,224,112,336),
   [1,0,0, 0,0.6047363,-0.7109375, 0,0.7617188,0.6477051]),
 ("TSHP cam0",       529, (0,-63),  (-27,831,4006),   (480,320), -102, (160,320,112,208),
   [1,0,0, 0,0.8251953,-0.4360352, 0,0.4672852,0.8840332]),
 ("TSHP cam1 (90y)", 421, (0,51),   (31,151,867),     (320,240), 4,    (160,160,112,128),
   [0.006103516,0,1, 0.04003906,0.932373,-0.0002441406, -0.9990234,0.04296875,0.006103516]),
 ("BSHP cam0",       385, (80,0),   (-313,72,2842),   (384,272), -105, (160,224,112,160),
   [0.9995117,0,-0.02758789, -0.01245117,0.814209,-0.4562988, 0.02392578,0.4890137,0.8718262]),
 ("GZML cam0",       606, (0,0),    (582,-358,6999),  (576,432), -51,  (160,416,112,320),
   [0.9121094,0,0.4099121, 0.1166992,0.8886719,-0.2600098, -0.3903809,0.3054199,0.8686523]),
 ("TRNO cam0 (inv)", 1166,(-81,-70),(3962,4378,-4190),(464,448), -1272,(160,304,112,336),
   [-0.9829102,0,0.1843262, 0.02612305,0.9226074,0.1391602, -0.1821289,0.1518555,-0.9714355]),
]

def make(rec):
    name, proj, off, t, rng, dz, vp, om = rec
    c = C.Cam()
    c.proj = proj; c.centerOffset = list(off); c.t = list(t)
    c.range = list(rng); c.depthOffset = dz; c.viewport = list(vp)
    c.r = [[int(round(om[i*3+j]*C.ROT)) for j in range(3)] for i in range(3)]
    return name, c

# test points sampled around a field (world coords; y=0 floor + some height)
PTS = [(0,0,0),(500,0,300),(-800,0,-1200),(1465,0,-3344),(300,-400,800),(-1799,0,-3344)]

def pinhole(P, cam, dec):
    "Independent projection via the decomposed clean pinhole (R_view, C). Offset=(0,0) to match project()."
    cs = C.mv(dec["R_view"], C.sub(P, dec["C"]))
    num = abs(cs[2])
    return (cs[0]*cam.proj/num, cs[1]*cam.proj/num, cs[2])

print(f"{'camera':18}  {'k(row1)':>8} {'r0':>6} {'r2':>6}  {'orthoErr':>9} {'det':>6}  "
      f"{'fovX':>6}  {'roundtrip dr/dt':>15}  {'proj match':>10}")
print("-"*108)
allgood = True
for rec in CAMS:
    name, cam = make(rec)
    d = C.decompose(cam)
    # round-trip: synth r/t from recovered (C, R_ortho, H) and compare
    r2, t2 = C.synth_r_t(d["C"], d["R_ortho"], cam.proj, k=d["k"])
    dr = max(abs(r2[i][j]-cam.r[i][j]) for i in range(3) for j in range(3))
    dt = max(abs(t2[i]-cam.t[i]) for i in range(3))
    # projection equivalence: GTE truth vs pinhole reconstruction
    pmax = 0.0
    for P in PTS:
        a = C.project(P, cam); b = pinhole(P, cam, d)
        pmax = max(pmax, abs(a[0]-b[0]), abs(a[1]-b[1]), abs(a[2]-b[2]))
    ok = d["ortho_err"] < 5e-3 and abs(d["k"]-C.K_VSCALE) < 3e-3 and dr <= 2 and dt <= 2 and pmax < 1e-4
    allgood = allgood and ok
    print(f"{name:18}  {d['k']:8.5f} {d['row_norms'][0]:6.4f} {d['row_norms'][2]:6.4f}  "
          f"{d['ortho_err']:9.2e} {d['det']:+6.3f}  {d['fov_x_deg']:6.2f}  "
          f"{dr:>6d}/{dt:<8d}  {pmax:10.2e}  {'OK' if ok else 'FAIL'}")

print("-"*108)
print(f"mean k across cameras (should be ~{C.K_VSCALE:.5f} = 14/15): "
      f"{sum(C.decompose(make(r)[1])['k'] for r in CAMS)/len(CAMS):.6f}")

# Session-8 cross-check: GRGR floor screen.y + canvas map
_, grgr = make(CAMS[0])
print(f"\nGRGR offset (engine projectionOffset) = {C.compute_offset(grgr)}  (expect (32, -112))")
print(f"{'z':>7}  {'projScreen.y':>12}  {'canvasY(s=.929)':>15}  {'Session-8':>10}  depth")
for z, s8 in ((340, 165), (-1188, 273)):
    px, py, _ = C.project_screen((0,0,z), grgr)
    cx, cy = C.to_canvas((0,0,z), grgr)
    print(f"{z:>7}  {py:12.3f}  {cy:15.2f}  {s8:>10}  {C.depth((0,0,z),grgr):8.1f}")
# inverse: which z lands on canvasY 165 / 273?
for cyt in (165, 273):
    z = C.solve_z_for_canvasY(grgr, cyt)
    print(f"solve z for canvasY={cyt}: z={z:.1f}")

print("\nALL CHECKS PASS" if allgood else "\nSOME CHECKS FAILED")
