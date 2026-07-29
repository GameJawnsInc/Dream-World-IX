"""Rung 3c -- THE DEPARTURE-LANE PROBE (offline, read-only).

The origin-port departure reverses each port's ARRIVE lane: the ship reveals DOCKED at the
origin quay, comes about, and sails out dock -> far (dock + 40u along the outbound bearing,
the reverse of the arrival's inbound heading), riding through the closing fade at far_pre
(28u out) -- the exact leg-split geometry of the proven Ashvale departure, generalized.

Verdicts needed per port:
  * the OUT-LANE dock -> far, every 1u sample WATER topograph {53,54,57} (visual law);
  * a DEPARTURE EYE point, WATER. The candidate ladder starts at dock + 12u out + 14u
    abeam (the ship passes ~14u abeam mid-shot, the rung-1b proven distance class) and
    falls back toward the arrival's own probed-wet eye. The abeam SIDE per port is the
    arrival eye's side -- the side already proven wet (Ashvale's -perp mirror is shoal).

Run: py probe_departure_lanes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from probe_arrival_lanes import query, is_water   # noqa: E402  (read-only machinery)

# port code -> (name, dock(x,z), outbound unit vec, perp unit vec [the arrival eye's wet
# side], arrival eye(x,z) [known wet, the last-resort candidate])
PORTS = {
    1: ("Ashvale",  (29.0, -1168.0),  (0.0, -1.0), (-1.0, 0.0), (21.0, -1196.0)),
    2: ("Tidefall", (394.0, -1232.0), (-1.0, 0.0), (0.0, 1.0),  (366.0, -1224.0)),
    3: ("Grimhorn", (1182.0, -1192.0), (-1.0, 0.0), (0.0, 1.0), (1154.0, -1184.0)),
    4: ("Larkspur", (726.5, -616.0),  (1.0, 0.0),  (0.0, -1.0), (754.5, -624.0)),
}

FAR = 40.0        # the full sail-out (Ashvale's proven 40u)
FAR_PRE = 28.0    # the fade starts here (Ashvale's proven split)
# eye candidates as (units out along the lane, units abeam) -- first wet wins
EYE_CANDIDATES = ((12.0, 14.0), (12.0, 10.0), (8.0, 8.0))


def probe_port(code: int) -> None:
    name, (dx, dz), (ox, oz), (px, pz), arr_eye = PORTS[code]
    far = (dx + ox * FAR, dz + oz * FAR)
    far_pre = (dx + ox * FAR_PRE, dz + oz * FAR_PRE)
    print(f"\n== port {code} {name}: dock ({dx},{dz}) far ({far[0]},{far[1]}) "
          f"far_pre ({far_pre[0]},{far_pre[1]}) ==")
    bad = []
    n = int(FAR) + 1
    for i in range(n):
        t = i / (n - 1)
        wx, wz = dx + (far[0] - dx) * t, dz + (far[1] - dz) * t
        g = query(wx, wz)
        if not is_water(g):
            bad.append((round(wx % 1536, 1), round(wz, 1),
                        "NO MESH" if g is None else f"{g[0]} topo {g[1]}"))
    print(f"  out-lane dock->far: {'LANE WET' if not bad else f'{len(bad)} dry sample(s)'}")
    for b in bad[:6]:
        print("     !!", b)
    for out_u, abeam_u in EYE_CANDIDATES:
        ex, ez = dx + ox * out_u + px * abeam_u, dz + oz * out_u + pz * abeam_u
        g = query(ex, ez)
        tag = "WATER" if is_water(g) else ("NO MESH" if g is None else f"{g[0]} topo {g[1]}")
        print(f"  eye candidate out {out_u}u abeam {abeam_u}u -> ({ex},{ez}): {tag}")
        if is_water(g):
            print(f"  >> PICK eye ({ex},{ez})")
            return
    g = query(*arr_eye)
    print(f"  fallback: arrival eye {arr_eye}: {'WATER' if is_water(g) else 'NOT WATER?!'}")
    print(f"  >> PICK eye {arr_eye} (arrival point reused)")


def main() -> None:
    for code in (1, 2, 3, 4):
        probe_port(code)


if __name__ == "__main__":
    main()
