"""scan_structure.py -- ADVERSARIAL structural recon of the archived cast log.

Independent of depth_gate.py. Answers:
  * effectId breakdown per tag (does the log hold >1 effect? -- the gate never filters by effectId)
  * frame ranges per (effectId, tag): do PRIM frames of one effect OVERLAP the PSXCAM/BONES frames of
    ANOTHER effect? (if so, the gate's frame-keyed join cross-contaminates)
  * PRIM count per (effectId, frame): where does the big volume actually live
  * otz polarity spot: logged sign distribution
"""
import sys
from collections import defaultdict

LOG = r"C:\gd\SCRATCH\summon-transplant\logs\sfxmeshprobe.20260724-012109.log"

tag_counts = defaultdict(int)
# per tag: effectId -> (count, minframe, maxframe)
eff_tag = defaultdict(lambda: defaultdict(lambda: [0, 10**9, -10**9]))
# frames present per (tag, effectId)
frames_present = defaultdict(lambda: defaultdict(set))
otz_sign = defaultdict(int)
prim_per_effframe = defaultdict(int)  # (eff,frame)->count

n = 0
with open(LOG, "r", encoding="utf-8", errors="replace") as fh:
    for line in fh:
        if not line or line[0] == "#":
            continue
        p = line.rstrip("\n").split(",")
        tag = p[0]
        tag_counts[tag] += 1
        n += 1
        try:
            if tag in ("PSXCAM", "BONES", "MODEL", "PRIM", "STATE", "ROOT"):
                eff = int(p[1])
                frame = int(p[2])
                rec = eff_tag[tag][eff]
                rec[0] += 1
                if frame < rec[1]:
                    rec[1] = frame
                if frame > rec[2]:
                    rec[2] = frame
                if tag in ("PSXCAM", "BONES", "PRIM", "MODEL"):
                    frames_present[tag][eff].add(frame)
                if tag == "PRIM":
                    prim_per_effframe[(eff, frame)] += 1
                    ot = float(p[6])
                    otz_sign["neg" if ot < 0 else ("zero" if ot == 0 else "pos")] += 1
            elif tag in ("VIEW", "PROJ", "CAM"):
                pass
        except (ValueError, IndexError):
            continue

print("=== tag counts ===")
for t in sorted(tag_counts):
    print(f"  {t:8s} {tag_counts[t]:>10d}")

print("\n=== per-tag effectId breakdown (count, minFrame, maxFrame) ===")
for t in ("PSXCAM", "BONES", "MODEL", "PRIM", "STATE", "ROOT"):
    if t not in eff_tag:
        continue
    print(f"  {t}:")
    for eff in sorted(eff_tag[t]):
        c, lo, hi = eff_tag[t][eff]
        print(f"    eff {eff:5d}: n={c:>9d} frames [{lo}..{hi}]")

# Cross-contamination test: for each PRIM effect, how many of its frames also have a PSXCAM/BONES row
# from a DIFFERENT effect at the same frame number?
print("\n=== cross-effect frame collision (PRIM frame shared with PSXCAM/BONES of ANOTHER effect) ===")
prim_effs = sorted(frames_present["PRIM"])
cam_effs = sorted(frames_present["PSXCAM"])
bones_effs = sorted(frames_present["BONES"])
for pe in prim_effs:
    pf = frames_present["PRIM"][pe]
    for ce in cam_effs:
        if ce == pe:
            continue
        overlap = pf & frames_present["PSXCAM"][ce]
        if overlap:
            print(f"    PRIM eff {pe} shares {len(overlap)} frames with PSXCAM eff {ce}: "
                  f"{sorted(overlap)[:8]}{'...' if len(overlap) > 8 else ''}")
    for be in bones_effs:
        if be == pe:
            continue
        overlap = pf & frames_present["BONES"][be]
        if overlap:
            print(f"    PRIM eff {pe} shares {len(overlap)} frames with BONES eff {be}: "
                  f"{sorted(overlap)[:8]}{'...' if len(overlap) > 8 else ''}")

# same-effect join coverage
print("\n=== same-effect PRIM<->PSXCAM<->BONES frame coverage ===")
for pe in prim_effs:
    pf = frames_present["PRIM"][pe]
    cam = frames_present["PSXCAM"].get(pe, set())
    bones = frames_present["BONES"].get(pe, set())
    print(f"    eff {pe}: PRIM frames={len(pf)} [{min(pf)}..{max(pf)}], "
          f"of which have PSXCAM={len(pf & cam)}, have BONES={len(pf & bones)}, have BOTH={len(pf & cam & bones)}")

print("\n=== logged otz sign distribution (PRIM) ===")
for k in ("neg", "zero", "pos"):
    print(f"    {k}: {otz_sign[k]}")

# biggest prim-volume frames
top = sorted(prim_per_effframe.items(), key=lambda kv: -kv[1])[:10]
print("\n=== top-10 (eff,frame) by PRIM count ===")
for (eff, fr), c in top:
    print(f"    eff {eff} frame {fr}: {c} prims")
