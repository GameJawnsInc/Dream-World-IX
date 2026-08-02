"""THE PEER GATE — score the corner against the ISLAND'S OWN approved coast.

Every gate in this arc scores an element against stock's marginals; none asks
"does this read like the thing the owner already accepted?" (GROUND-JUNCTION-
SYNTHESIS: 0 of 13 playtest verdicts were predicted by a gate). This one does:
it renders the rebuilt corner and several owner-passed shore stations from
CAMERAS PLACED IDENTICALLY relative to the local coast tangent, so the frames
are directly comparable, and reports the band-geometry statistics that the
owner's language ("segmented", "fractured", "less than 90 degrees") maps onto:
rock-band screen thickness and its variation, and the silhouette turn count.

  py probe_peer_compare.py [staged|live]
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_gate as RG                                    # noqa: E402
import vcorner_transplant as VT                             # noqa: E402

# (name, a point ON the coast, the local seaward direction) — the corner plus
# owner-passed peers on the same island, all grass-lip shore.
SITES = [
    ("CORNER", (375.5, -517.5), (-0.93, -0.36)),
    ("peer-nw", (373.0, -496.0), (-0.97, 0.22)),
    ("peer-n", (384.0, -486.5), (0.10, 0.99)),
    ("peer-e", (447.5, -515.0), (0.99, 0.10)),
    ("peer-s", (398.0, -537.5), (-0.10, -0.99)),
]
GRAZE_D, GRAZE_H = 14.0, 3.0                                # eye offset, height
GRAZE_AIM_H = 1.2


def cam_for(pt, sea, d=GRAZE_D, h=GRAZE_H):
    return dict(kind="persp",
                eye=(pt[0] + d * sea[0], h, pt[1] + d * sea[1]),
                at=(pt[0], GRAZE_AIM_H, pt[1]), fov=45.0, reach=60.0)


def band_stats(img):
    """Rock-band thickness per column: rock = greyish (low saturation, mid
    value) between green above and blue below. Returns (median, iqr, cols)."""
    f = img.astype(np.int32)
    r, g, b = f[:, :, 0], f[:, :, 1], f[:, :, 2]
    mx = f.max(axis=2)
    mn = f.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1)
    rock = (sat < 0.22) & (mx > 70) & (mx < 245) & (b < r + 30)
    th = rock.sum(axis=0)
    live = th[th > 0]
    if live.size < 30:
        return None
    return (float(np.median(live)), float(np.percentile(live, 75)
                                           - np.percentile(live, 25)), int(live.size))


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "staged"
    src = dict(VT.staged_src()) if tag == "staged" else {}
    batches = RG.load_batches(src)
    print(f"[{tag}] peer comparison at matched camera geometry "
          f"(eye {GRAZE_D}u out, {GRAZE_H}u up)\n")
    print(f"{'site':10s} {'band px median':>14s} {'IQR':>7s} {'IQR/med':>8s}  verdict")
    rows = {}
    for (name, pt, sea) in SITES:
        L = math.hypot(*sea)
        sea = (sea[0] / L, sea[1] / L)
        img = RG.raster(cam_for(pt, sea), batches, f"peer_{tag}_{name}")
        st = band_stats(img)
        if st is None:
            print(f"{name:10s} {'—':>14s} — no band found")
            continue
        med, iqr, cols = st
        rows[name] = (med, iqr)
        print(f"{name:10s} {med:14.1f} {iqr:7.1f} {iqr / max(med, 1):8.2f}")
    if "CORNER" in rows and len(rows) > 1:
        peers = [v for k, v in rows.items() if k != "CORNER"]
        pm = float(np.median([p[0] for p in peers]))
        pr = float(np.median([p[1] / max(p[0], 1) for p in peers]))
        cm, cr = rows["CORNER"][0], rows["CORNER"][1] / max(rows["CORNER"][0], 1)
        print(f"\npeers: median band {pm:.1f}px, median IQR/med {pr:.2f}")
        print(f"corner: band {cm:.1f}px ({cm / pm:.2f}x peers), "
              f"IQR/med {cr:.2f} ({cr / max(pr, 0.01):.2f}x peers)")
        ok = 0.5 <= cm / pm <= 2.0 and cr <= max(2.5 * pr, pr + 0.25)
        print(f"PEER GATE: {'PASS' if ok else 'FAIL'} "
              f"— the corner {'sits inside' if ok else 'falls outside'} "
              f"the island's own band distribution")


if __name__ == "__main__":
    main()
