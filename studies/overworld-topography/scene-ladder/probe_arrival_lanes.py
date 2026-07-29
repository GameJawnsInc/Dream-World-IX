"""Scene ladder rung 3 -- THE ARRIVAL-LANE PROBE (offline, read-only).

For each ferry port, derive the sail-in theater the arrival scene needs:

  * the WATERLINE seaward of the player's arrive point (seaward = opposite arrive_face's
    inland direction; face bytes: 64 = west, 192 = east -- the hall toml's own convention),
  * a DOCK point ~6u off the waterline (the Ashvale mooring sits 5.5u off its shore),
  * an APPROACH point ~36u further out along the same lane (where the reveal finds the ship),
  * a lane verdict: every 1u sample dock->approach must be WATER topograph {53,54,57}
    (visual law, not a legality need -- a scripted scenery ship sails over anything, but a
    lane crossing land would LOOK like it).

Falls back through candidate bearings (straight seaward, then +/-22.5deg, +/-45deg) until a
lane is fully wet. Ashvale is printed for reference but the scene reuses the proven mooring
(29,-1168) with the departure lane run in reverse.

Run: py probe_arrival_lanes.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.world import extract as W   # noqa: E402
from ff9mapkit.world import mesh as M      # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MOD = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
WATER_TOPOS = {53, 54, 57}
PARTS_ORDER = ("Object", "Terrain", "Beach1", "Sea1", "Sea2", "Sea3", "Sea5", "Sea4")

# port code -> (name, arrive x, arrive z, arrive_face byte)
PORTS = {
    1: ("Ashvale", 60.0, -1168.0, 192),
    2: ("Tidefall", 432.0, -1232.0, 192),
    3: ("Grimhorn", 1214.0, -1192.0, 192),
    4: ("Larkspur", 688.0, -616.0, 64),
}

DOCK_OFF = 6.0       # dock this far off the waterline
LANE_LEN = 36.0      # approach this far beyond the dock

_cache: dict = {}


def load_parts(bx, by):
    key = (bx, by)
    if key in _cache:
        return _cache[key]
    parts = []
    for part in PARTS_ORDER:
        p = MOD / "Disc1" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"
        bm = None
        if p.is_file():
            try:
                bm = M.blockmesh_from_ff9mesh(str(p), disc=1, x=bx, y=by, part=part.lower())
            except Exception:
                bm = None
        else:
            try:
                bm = W.read_block(bx, by, disc=1, part=part.lower())
            except Exception:
                bm = None
        if bm is not None and len(bm.tris):
            parts.append((part, bm))
    _cache[key] = parts
    return parts


def query(wx, wz):
    wx %= 1536.0
    bx, by = math.floor(wx / 64), math.floor(-wz / 64)
    ox, oz = W.block_world_origin(bx, by)
    for nm, bm in load_parts(bx, by):
        for t in range(len(bm.tris)):
            a, b, c = [(bm.verts[k][0] + ox, bm.verts[k][1], bm.verts[k][2] + oz)
                       for k in bm.tris[t]]
            d = (b[0]-a[0])*(c[2]-a[2]) - (c[0]-a[0])*(b[2]-a[2])
            if abs(d) < 1e-12:
                continue
            w1 = ((wx-a[0])*(c[2]-a[2]) - (c[0]-a[0])*(wz-a[2])) / d
            w2 = ((b[0]-a[0])*(wz-a[2]) - (wx-a[0])*(b[2]-a[2])) / d
            if w1 < -1e-9 or w2 < -1e-9 or w1 + w2 > 1 + 1e-9:
                continue
            return (nm, W.decode_id(int(round(bm.tangents[bm.tris[t][0]][0])))["topograph"])
    if not load_parts(bx, by):
        return ("SeaBlockPrefab", 57)
    return None


def is_water(g) -> bool:
    return g is not None and g[1] in WATER_TOPOS


def face_to_seaward(face: int) -> float:
    """arrive_face points INLAND; seaward is the opposite. 192=east inland -> seaward
    bearing 180deg (west, -x); 64=west inland -> 0deg (east, +x). Returns radians where
    dx=cos, dz=0 (the map's z-axis stays fixed; lanes vary by rotating around this)."""
    return math.pi if face == 192 else 0.0


def probe_port(code: int):
    name, ax, az, face = PORTS[code]
    base = face_to_seaward(face)
    print(f"\n== port {code} {name}: arrive ({ax},{az}) face {face} ==")
    for ddeg in (0, -22.5, 22.5, -45, 45):
        ang = base + math.radians(ddeg)
        dx, dz = math.cos(ang), math.sin(ang)
        # march to the waterline
        wl = None
        for i in range(1, 121):
            s = i * 0.5
            g = query(ax + dx*s, az + dz*s)
            if is_water(g):
                wl = s
                break
        if wl is None:
            print(f"  bearing {ddeg:+.1f}deg: no waterline within 60u")
            continue
        dock = (ax + dx*(wl + DOCK_OFF), az + dz*(wl + DOCK_OFF))
        appr = (ax + dx*(wl + DOCK_OFF + LANE_LEN), az + dz*(wl + DOCK_OFF + LANE_LEN))
        bad = []
        n = int(LANE_LEN) + 1
        for i in range(n):
            t = i / (n - 1)
            wx, wz = dock[0] + (appr[0]-dock[0])*t, dock[1] + (appr[1]-dock[1])*t
            g = query(wx, wz)
            if not is_water(g):
                bad.append((round(wx % 1536, 1), round(wz, 1),
                            "NO MESH" if g is None else f"{g[0]} topo {g[1]}"))
        verdict = "LANE WET" if not bad else f"{len(bad)} dry sample(s)"
        print(f"  bearing {ddeg:+.1f}deg: waterline at {wl}u  dock ({dock[0]:.1f},{dock[1]:.1f})"
              f"  approach ({appr[0]:.1f},{appr[1]:.1f})  -> {verdict}")
        for b in bad[:6]:
            print("     !!", b)
        if not bad:
            # heading byte approach->dock: map bearing to the face convention (64=west
            # inland means +x=east... the SHIP travels dock-ward = -seaward direction).
            print(f"  >> PICK: dock=({dock[0]:.1f},{dock[1]:.1f}) "
                  f"approach=({appr[0]:.1f},{appr[1]:.1f})")
            return
    print("  !! no wet lane found on any bearing -- widen the search")


def main() -> None:
    for code in (2, 3, 4, 1):
        probe_port(code)


if __name__ == "__main__":
    main()
