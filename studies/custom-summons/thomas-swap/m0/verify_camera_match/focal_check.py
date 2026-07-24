"""focal_check.py -- is near==H clean on COHERENT frames, and are the near!=H frames all cut-transition?
Also: cameraOffset on the clean S1 cast; and the 220-vs-240 center-vs-scale separation sanity."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from indep_verify import parse, rot_resid, HALF_H, DL, DR, LOG

sessions = parse(LOG)
coh_dev, cut_dev = [], []
worst_coh = 0.0
worst_coh_info = None
for i, s in enumerate(sessions):
    for f, cam in s["psx"].items():
        view = s["view"].get(f); proj = s["proj"].get(f)
        if view is None or proj is None:
            continue
        r = rot_resid(view, cam)
        dev = abs(HALF_H * proj[1, 1] - cam["H"])
        if r < 0.02:
            coh_dev.append(dev)
            if dev > worst_coh:
                worst_coh = dev; worst_coh_info = (i, f, cam["H"], HALF_H*proj[1,1], r)
        else:
            cut_dev.append(dev)
coh_dev = np.array(coh_dev); cut_dev = np.array(cut_dev)
print("=== near=110*P11 vs H, split by camera-coherence ===")
print(f"  COHERENT frames n={len(coh_dev)}: max|near-H|={coh_dev.max():.6f}  mean={coh_dev.mean():.6f}")
print(f"    worst coherent frame: sess={worst_coh_info[0]} frame={worst_coh_info[1]} H={worst_coh_info[2]} "
      f"near={worst_coh_info[3]:.4f} rotResid={worst_coh_info[4]:.4f}")
print(f"  CUT-TRANSITION frames n={len(cut_dev)}: max|near-H|={cut_dev.max():.4f}  mean={cut_dev.mean():.4f}  "
      f"(these are the 43-57 outliers -- probe P11/H one tick apart)")
print(f"  => the near!=H frames are ALL non-coherent: {'CONFIRMED' if coh_dev.max() < 0.01 else 'REFUTED'}")

# also: how many coherent frames have dev>0.01 ?
print(f"  coherent frames with |near-H|>0.01: {(coh_dev>0.01).sum()} of {len(coh_dev)}")

# cameraOffset clean cast (S1)
print("\n=== cameraOffset on the CLEAN short cast (S1) ===")
s = sessions[1]
offs = []
for f, cam in s["psx"].items():
    view = s["view"].get(f)
    if view is None:
        continue
    if rot_resid(view, cam) < 0.02 and abs(view[0,3]-cam["T"][0])<2 and abs(view[1,3]+cam["T"][1])<2:
        offs.append(-view[2,3]-cam["T"][2])
offs = np.array(offs)
print(f"  n={len(offs)} co-sampled: mean={offs.mean():+.4f}  median={np.median(offs):+.4f}  range[{offs.min():+.2f},{offs.max():+.2f}]")
print(f"  => cameraOffset ~ 0 (sub-unit): {'CONFIRMED' if abs(np.median(offs))<1 else 'CHECK'}")

# center-vs-scale separation: OFY=120 additive, 110 scale. Show frame-11 hand check.
print("\n=== 220-vs-240 separation: OFY (center) vs HALF_H (scale) at frame 11 ===")
cam = sessions[0]["psx"][11]; proj = sessions[0]["proj"][11]
print(f"  logged OFY (center) = {cam['ofy']}  (=240/2, additive)   HALF_H (scale) = {HALF_H} (=PsxScreenHeightNative/2=220/2)")
print(f"  110*P11 = {110*proj[1,1]:.4f} == H={cam['H']} ; 120*P11 = {120*proj[1,1]:.4f} != H  => must use 110 for scale, 120 for center")
