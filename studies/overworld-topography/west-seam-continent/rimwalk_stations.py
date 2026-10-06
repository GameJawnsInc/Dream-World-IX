"""Where the harness rim walk stands -- computed from the DEPLOYED continent, read-only.

The take-8 rim walk (rimwalk_take8.py, the first overworld harness scenario) needs points it can
teleport to SAFELY and walk from: a teleport keeps the current height and lets movement re-ground
it, so a point over rock, sea or a cliff lip is exactly the bad-geometry-under-the-actor class the
overworld skill warns about. Every point here is checked against the live mesh first.

Writes ``rimwalk_stations.json`` beside this file:

  stations  -- every rock-grass foot station in take 8's SW window (THE PROFILE LAW's 11), plus
               CONTROL stations on the owner-passed faces, each with:
                 contact (x, z)         the rock-grass edge midpoint (envelope_profile.stations)
                 uphill  (ux, uz)       the rock plane's gradient direction
                 rises                  THE TAKE-8 PREDICATE: the massif climbs >= 2.5u within 6u
                                        uphill -- where it does, rock should stop him; where it does
                                        not, take 8 emits grass and he should walk on with no curb
                 approach (x, z)        a lawn point behind the contact, every 2u sample between it
                                        and the contact on GRASS within 1u of the contact's height
                 lawn_y                 the ground height at the contact
  seam      -- latitudes where a walk from x 1490 east across the x-seam to x 40 stays on flat grass
  grass_run -- a straight all-grass segment near the east-bay landing, for the no-encounter walk

    py studies/overworld-topography/west-seam-continent/rimwalk_stations.py
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from envelope_profile import WINDOW, ROCK, GRASS, read_loose, stations   # noqa: E402

OUT = HERE / "rimwalk_stations.json"
SPAN = 1536.0                                   # 24 blocks x 64u: the x-seam
COLS = (21, 22, 23, 0, 1)                       # the continent's wrapped columns
ROWS = range(4, 10)
LANDING = (68.0, -444.0)                        # 6603's walk-out arrival (landing.field.toml)
MASSIF = (1462.0, -462.0)                       # R4's printed placement


class Ground:
    """The TOP triangle at (x, z) -- its height and topograph -- over a triangle soup, 4u hash."""

    def __init__(self, tris):
        self.tris = tris
        self.grid = {}
        for i, (p0, p1, p2, _) in enumerate(tris):
            xs, zs = (p0[0], p1[0], p2[0]), (p0[2], p1[2], p2[2])
            for cx in range(int(min(xs) // 4), int(max(xs) // 4) + 1):
                for cz in range(int(min(zs) // 4), int(max(zs) // 4) + 1):
                    self.grid.setdefault((cx, cz), []).append(i)

    def top(self, x, z):
        x %= SPAN
        best = None
        for i in self.grid.get((int(x // 4), int(z // 4)), ()):
            p0, p1, p2, tp = self.tris[i]
            d = (p1[2] - p2[2]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[2] - p2[2])
            if abs(d) < 1e-9:
                continue
            w0 = ((p1[2] - p2[2]) * (x - p2[0]) + (p2[0] - p1[0]) * (z - p2[2])) / d
            w1 = ((p2[2] - p0[2]) * (x - p2[0]) + (p0[0] - p2[0]) * (z - p2[2])) / d
            w2 = 1.0 - w0 - w1
            if min(w0, w1, w2) < -1e-6:
                continue
            y = w0 * p0[1] + w1 * p1[1] + w2 * p2[1]
            if best is None or y > best[0]:
                best = (y, tp)
        return best


def _rises(g, x, z, ux, uz):
    """take 8's `_fc_rock_here`: the massif rises >= 2.5u within 6u uphill of the contact."""
    base = g.top(x, z)
    if base is None:
        return False
    peak = max((g.top(x + ux * d, z + uz * d) or (base[0], 0))[0] for d in (2.0, 4.0, 6.0))
    return peak - base[0] >= 2.5


def _approach(g, x, z, ux, uz, lawn_y):
    """The farthest lawn point (8..20u) behind the contact with clean grass all the way in."""
    best = None
    for d in range(4, 22, 2):
        t = g.top(x - ux * d, z - uz * d)
        if t is None or t[1] != GRASS or abs(t[0] - lawn_y) > 1.0:
            break
        best = d
    if best is None or best < 8:
        return None, best
    return (round(x - ux * best, 2), round(z - uz * best, 2)), best


def _flat_grass(g, pts, y0=None, tol=1.0):
    ys = []
    for x, z in pts:
        t = g.top(x, z)
        if t is None or t[1] != GRASS:
            return None
        ys.append(t[0])
    if y0 is None:
        y0 = ys[0]
    return ys if all(abs(y - y0) <= tol for y in ys) else None


def main():
    tris = []
    for bx in COLS:
        for by in ROWS:
            tris.extend(read_loose(bx, by))
    if not tris:
        sys.exit("no continent blocks under FF9CustomMap-world -- is the continent deployed?")
    g = Ground(tris)
    print(f"continent tris {len(tris)}")

    # ---- the foot stations: the window's, then controls on the owner-passed faces ----
    raw = stations(tris)
    seen, picked = [], []
    for x, z, ux, uz in sorted(raw):
        if any(math.hypot(x - a, z - b) < 3.0 for a, b in seen):
            continue
        seen.append((x, z))
        inw = WINDOW[0] <= x <= WINDOW[2] and WINDOW[1] <= z <= WINDOW[3]
        picked.append((inw, x, z, ux, uz))
    window = [p for p in picked if p[0]]
    # controls: owner-passed faces that clearly rise, spread around the massif by bearing
    passed = [p for p in picked if not p[0] and _rises(g, p[1], p[2], p[3], p[4])
              and math.hypot(p[1] - MASSIF[0], p[2] - MASSIF[1]) < 90]
    controls, used = [], []
    for want in (90.0, 0.0, 270.0, 180.0):             # N, E, S, W of the massif centre
        def off(p):
            b = math.degrees(math.atan2(p[2] - MASSIF[1], p[1] - MASSIF[0])) % 360
            return min(abs(b - want), 360 - abs(b - want))
        for p in sorted(passed, key=off):
            if off(p) > 40 or p in used:
                continue
            lawn = g.top(p[1], p[2])
            a, _ = _approach(g, p[1], p[2], p[3], p[4], lawn[0]) if lawn else (None, None)
            if a is not None:
                controls.append(p)
                used.append(p)
                break

    rows = []
    for kind, group in (("window", window), ("control", controls)):
        for _, x, z, ux, uz in group:
            lawn = g.top(x, z)
            if lawn is None:
                continue
            rises = _rises(g, x, z, ux, uz)
            a, d = _approach(g, x, z, ux, uz, lawn[0])
            row = {"kind": kind, "contact": [round(x, 2), round(z, 2)],
                   "uphill": [round(ux, 4), round(uz, 4)], "rises": rises,
                   "lawn_y": round(lawn[0], 2), "approach": a, "approach_d": d,
                   "bearing": round(math.degrees(math.atan2(uz, ux)) % 360, 1)}
            rows.append(row)
            flag = "RISES" if rises else "flat "
            print(f"  {kind:7s} ({x:7.1f},{z:7.1f}) {flag} lawn {lawn[0]:5.2f} "
                  f"bearing {row['bearing']:5.1f}  approach {a} (d={d})")

    # ---- seam latitudes: x 1490 -> 1536|0 -> 40 on flat grass ----
    seam = []
    xs = [1490.0 + 2 * i for i in range(23)] + [2.0 * i for i in range(21)]
    for zi in range(-264, -640, -8):
        z = float(zi)
        ys = _flat_grass(g, [(x, z) for x in xs])
        if ys is not None:
            seam.append({"z": z, "from_x": 1490.0, "to_x": 40.0, "y": round(sum(ys) / len(ys), 2)})
    # keep two well apart: the northernmost and the southernmost
    if len(seam) > 2:
        seam = [seam[0], seam[-1]]
    print(f"seam latitudes: {[s['z'] for s in seam]}")

    # ---- a grass run near the landing: the longest flat straight segment from it ----
    run = None
    for b in range(0, 360, 15):
        ux, uz = math.cos(math.radians(b)), math.sin(math.radians(b))
        length = 0
        for d in range(2, 122, 2):
            if _flat_grass(g, [(LANDING[0] + ux * d, LANDING[1] + uz * d)],
                           y0=g.top(*LANDING)[0]) is None:
                break
            length = d
        if run is None or length > run["length"]:
            run = {"start": list(LANDING), "bearing": float(b), "length": float(length),
                   "end": [round((LANDING[0] + ux * length) % SPAN, 2), round(LANDING[1] + uz * length, 2)]}
    print(f"grass run: {run}")

    OUT.write_text(json.dumps({"stations": rows, "seam": seam, "grass_run": run,
                               "massif": list(MASSIF), "landing": list(LANDING)}, indent=1),
                   encoding="utf-8")
    print(f"wrote {OUT.name}: {len(rows)} stations "
          f"({sum(r['approach'] is not None for r in rows)} walkable), "
          f"{len(seam)} seam lines")


if __name__ == "__main__":
    main()
