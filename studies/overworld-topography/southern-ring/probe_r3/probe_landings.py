"""R5c -- THE LANDING-SITES PROBE: where can the crimson Narciss actually put you ashore?

The engine dismount (ff9.w_movementGetGetoff, mode 7) has two requirements the R5c loop inherits
verbatim: (1) the tile probed AHEAD of the hull reads topograph 53 (beach-front water) -- the gate;
(2) a raycast sweep around the hull finds ground that is NOT boat-legal water -- the landing point.

Offline approximation over the STACKED live meshes (same query machinery as probe_sea_lane): a
LANDING SITE is a sample whose own topograph is 53 with non-{53,54,57} ground within ~12u. Reports
per-island counts + representative coordinates so the playtest knows where dismount will say yes.
Read-only; exits nonzero if any ring island has NO landing site at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from probe_sea_lane import BOAT_TOPOS, query   # noqa: E402  (reuses the stacked-mesh resolver)

STEP = 4.0
NEIGHBORS = ((10, 0), (-10, 0), (0, 10), (0, -10), (7, 7), (-7, 7), (7, -7), (-7, -7))

# Scan boxes (world coords, generous margins around each site's centre).
BOXES = {
    "boat islet (home)": (470, 515, -1145, -1095),
    "Ashvale":           (20, 80, -1195, -1135),
    "Tidefall":          (390, 450, -1255, -1195),
    "Grimhorn":          (1175, 1235, -1215, -1155),
    "Larkspur":          (670, 730, -640, -580),
    "Lamplight":         (1395, 1455, -1195, -1135),
    "the horseshoe":     (1260, 1360, -1230, -1120),
}


def is_ground(g):
    return g is not None and g[1] not in BOAT_TOPOS


def main() -> int:
    hard_fail = False
    for name, (x0, x1, z0, z1) in BOXES.items():
        sites = []
        x = x0
        while x <= x1:
            z = z0
            while z <= z1:
                g = query(x, z)
                if g is not None and g[1] == 53:
                    if any(is_ground(query(x + dx, z + dz)) for dx, dz in NEIGHBORS):
                        sites.append((x, z))
                z += STEP
            x += STEP
        if sites:
            xs = sorted(sites)
            west, east = xs[0], xs[-1]
            print(f"{name}: {len(sites)} landing sample(s)  "
                  f"west~({west[0]:.0f},{west[1]:.0f})  east~({east[0]:.0f},{east[1]:.0f})")
        else:
            print(f"{name}: NO landing site -- the getoff gate will always refuse here")
            hard_fail = True
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
