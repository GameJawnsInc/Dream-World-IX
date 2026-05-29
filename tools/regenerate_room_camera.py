#!/usr/bin/env python3
# Faithfulness check: read a room's .bgx camera, decompose it to human-meaningful
# geometry (position C, orientation R_ortho, FOV), then RE-SYNTHESIZE the camera
# block from those values via cam_lib.synth_r_t and rewrite the .bgx.
#
# If the tool is faithful, the regenerated camera == the known-good camera (within
# Int16 rounding) and the room renders identically in-game.
#
# Surgical: only the CAMERA block's Position + OrientationMatrix lines are rewritten;
# all comments, OVERLAY blocks, and other camera fields are preserved verbatim.
#
# Usage: regenerate_room_camera.py <in.bgx> <out.bgx>
import sys, math, cam_lib as C

inp, outp = sys.argv[1], sys.argv[2]
cams = C.parse_bgx_cameras(inp)
assert len(cams) >= 1, "no CAMERA block found"
cam = cams[0]
d = C.decompose(cam)

# pull out a clean "pitch about X" angle if the camera is a pure X-rotation (GRGR is)
Ro = d["R_ortho"]
pitch = math.degrees(math.atan2(Ro[2][1], Ro[2][2]))   # rot about X
print("=== decomposed (human-meaningful) ===")
print(f"  camera world pos C : ({d['C'][0]:.1f}, {d['C'][1]:.1f}, {d['C'][2]:.1f})")
print(f"  vertical scale k    : {d['k']:.6f}   (canonical 14/15 = {14/15:.6f})")
print(f"  orthonormality err  : {d['ortho_err']:.2e}   det = {d['det']:+.4f}")
print(f"  pitch (about X)     : {pitch:.3f} deg")
print(f"  ViewDistance H      : {cam.proj}   -> FOV_x ~ {d['fov_x_deg']:.2f} deg")

# re-synthesize r/t from the decomposed geometry (uses the per-camera k so r is exact)
r2, t2 = C.synth_r_t(d["C"], d["R_ortho"], cam.proj, k=d["k"])
dr = max(abs(r2[i][j]-cam.r[i][j]) for i in range(3) for j in range(3))
dt = max(abs(t2[i]-cam.t[i]) for i in range(3))
print(f"\n=== resynth vs original ===   max |dr|={dr} (Int16)   max |dt|={dt}")

# build the new camera object (preserve all non-rotation/position fields)
newcam = C.Cam()
newcam.proj = cam.proj; newcam.centerOffset = cam.centerOffset[:]
newcam.range = cam.range[:]; newcam.depthOffset = cam.depthOffset
newcam.viewport = cam.viewport[:]
newcam.t = t2; newcam.r = r2

# format the regenerated Position + OrientationMatrix lines
Rf = newcam.Rf()
new_pos = f"Position: {t2[0]}, {t2[1]}, {t2[2]}"
new_om  = "OrientationMatrix: " + ", ".join(C._fmt(Rf[i][j]) for i in range(3) for j in range(3))

# surgical rewrite: within the (single) CAMERA block, swap Position + OrientationMatrix
lines = open(inp, encoding="utf-8").read().splitlines()
out, in_cam = [], False
old_pos = old_om = None
for ln in lines:
    s = ln.strip()
    if s == "CAMERA":
        in_cam = True; out.append(ln); continue
    if in_cam and s.startswith("Position:"):
        old_pos = s; out.append(new_pos); continue
    if in_cam and s.startswith("OrientationMatrix:"):
        old_om = s; out.append(new_om); continue
    out.append(ln)

open(outp, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

print("\n=== CAMERA block diff (only these two lines change) ===")
print(f"- {old_pos}")
print(f"+ {new_pos}")
print(f"- {old_om}")
print(f"+ {new_om}")
print(f"\nwrote {outp}")
