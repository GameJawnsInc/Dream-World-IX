"""`world-mountain --rot` IN GAME, the offline half: the lab's three carves and what the run must read.

The lab (out/rotlab/, gitignored) is one scratch island minted on open ocean that no live folder touches, blocks
(20,0)-(21,1) (`world-island --center 1340.5,-70.5 --radius 31 --lobes 1 --patches 0 --seed 42`), copied three
times and carved with the Uaho massif (`world-mountain --near 1340.5,-70.5`):
  A  --rot 0              the rigid carry, the control
  B  --rot 45             rotation alone, at the angle most across the grass lattice
  C  --rot 30 --rock-height 1.5    both new options
From each variant's four Terrain overrides (the engine's down-ray: the highest Terrain hit), this registers:
  - SUMMIT: the highest rock point off the 4u lattice within 1.5u of the peak, and its height (topograph 49 has no walk sink);
  - RING: 12 points on the grass 2u outside the rock's last hit, one per 30 deg round the massif, and their
    heights -- the foot seam must hold the player at the built height all round (a crack drops him to the sea);
  - VIEWS: plain-grass homes shared by all three variants, each with the bearing to that variant's massif and
    where a walk along it stops (walk_stop: the surface he can step onto turns to rock; under Uaho's alcove roof
    he walks on the floor). Every teleport target is off the 4u lattice AND >= 0.08 inside its tri (castable):
    round 16's first run hung the player at y 0 on a grass cell's diagonal.
Writes out/rotlab/prep.json.  Rerun: py studies/terrain-malleability/rockstretch/rot_prep.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import mesh as M, extract as X, grassland as G  # noqa: E402

LAB = HERE / "out" / "rotlab"
BLOCKS = [(20, 0), (21, 0), (20, 1), (21, 1)]
VARIANTS = {"A": {"rot": 0, "height": 1.0}, "B": {"rot": 45, "height": 1.0}, "C": {"rot": 30, "height": 1.5}}
ROCK = 49
GRASS = G.GROUNDS["grass"]["topo"]
RING_OUT = 2.0


def load(variant: str):
    tris, topo = [], []
    for bx, by in BLOCKS:
        p = LAB / variant / "FF9CustomMap-lab" / M.override_relpath(1, bx, by)
        d = M.read_ff9mesh(p)
        V = np.asarray(d["verts"], float) + np.array([64.0 * bx, 0.0, -64.0 * by])
        idx = np.asarray(d["indices"]).reshape(-1, 3)
        tris.append(V[idx])
        topo += [X.decode_id(int(round(d["tangents"][t[0]][0])))["topograph"] for t in idx]
    return np.concatenate(tris), np.array(topo)


class Ground:
    """The engine's down-ray over the Terrain: the highest hit at (x, z) -> (y, topograph) or None."""

    def __init__(self, T, topo):
        self.T, self.topo = T, topo
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        self.den = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
        self.ok = np.abs(self.den) > 1e-12

    def _bary(self, x, z):
        T = self.T
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            l1 = ((b[:, 2] - c[:, 2]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (z - c[:, 2])) / self.den
            l2 = ((c[:, 2] - a[:, 2]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (z - c[:, 2])) / self.den
        l3 = 1 - l1 - l2
        hit = self.ok & (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        y = l1 * a[:, 1] + l2 * b[:, 1] + l3 * c[:, 1]
        return hit, y, np.minimum(np.minimum(l1, l2), l3)

    def __call__(self, x, z):
        hit, y, _ = self._bary(x, z)
        if not hit.any():
            return None
        k = np.where(hit)[0][np.argmax(y[hit])]
        return float(y[k]), int(self.topo[k])

    def hits(self, x, z):
        """Every surface over (x, z), lowest first: [(y, topograph)]."""
        hit, y, _ = self._bary(x, z)
        return sorted((float(y[k]), int(self.topo[k])) for k in np.where(hit)[0])

    def margin(self, x, z):
        """How far (x, z) sits inside the top tri (its smallest barycentric coordinate): a one-shot cast exactly
        on an edge can miss both tris (round 16's north home, on a grass cell's diagonal: the player hung at y 0)."""
        hit, y, m = self._bary(x, z)
        if not hit.any():
            return 0.0
        k = np.where(hit)[0][np.argmax(y[hit])]
        return float(m[k])


def off_lattice(v: float) -> bool:
    return min(v % 4.0, 4.0 - v % 4.0) >= 0.4


MARGIN = 0.08


def castable(g, x, z) -> bool:
    """A teleport target: off the 4u lattice lines AND inside its tri, not on an edge (diagonals included)."""
    return off_lattice(x) and off_lattice(z) and g.margin(x, z) >= MARGIN


STEP_UP = 2.34375                          # the walk's climb limit (engine step)


def walk_stop(g, x, z, ux, uz, reach=40.0):
    """Where a walk straight along (ux, uz) from (x, z) stops: follow the surface he stands on (the hit nearest his
    height that he can step onto), and stop where it turns to rock or no surface is in reach. Under an overhang
    (Uaho's alcove roof) he stays on the floor -- the highest hit is the roof, which is not where he walks."""
    y = g(x, z)[0]
    for r in np.arange(0.1, reach, 0.1):
        hs = [h for h in g.hits(x + ux * r, z + uz * r) if h[0] <= y + STEP_UP]
        if not hs:
            return float(r)
        y2, topo = hs[-1]                      # the highest surface he can step onto
        if topo == ROCK:
            return float(r)
        y = y2
    return None


def last_rock(g: Ground, cx, cz, ux, uz, reach=34.0):
    r_last = None
    for r in np.arange(0.0, reach, 0.1):
        h = g(cx + ux * r, cz + uz * r)
        if h is not None and h[1] == ROCK:
            r_last = float(r)
    return r_last


def first_rock(g: Ground, x, z, ux, uz, reach=40.0):
    for r in np.arange(0.0, reach, 0.1):
        h = g(x + ux * r, z + uz * r)
        if h is not None and h[1] == ROCK:
            return float(r)
    return None


def prep_variant(name):
    T, topo = load(name)
    g = Ground(T, topo)
    R = T[topo == ROCK].reshape(-1, 3)
    cx, cz = float(R[:, 0].mean()), float(R[:, 2].mean())
    pk = R[R[:, 1].argmax()]
    # the summit probe: the highest rock point within 1.5u of the peak vertex, off the 4u lattice
    best = None
    for sx in np.arange(pk[0] - 1.5, pk[0] + 1.51, 0.1):
        for sz in np.arange(pk[2] - 1.5, pk[2] + 1.51, 0.1):
            if not castable(g, sx, sz):
                continue
            h = g(sx, sz)
            if h and h[1] == ROCK and (best is None or h[0] > best[2][0]):
                best = (float(sx), float(sz), h)
    if best is None:
        raise SystemExit(f"{name}: no lawful summit probe")
    sx, sz, h = best
    summit = {"world": [round(sx, 3), round(sz, 3)], "y": round(h[0], 4), "peak_y": round(float(pk[1]), 4)}
    ring = []
    for deg in range(0, 360, 30):
        ux, uz = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        r0 = last_rock(g, cx, cz, ux, uz)
        found = None                        # outward first, then a sideways nudge (a ray along a lattice line)
        for side in (0.0, 0.6, -0.6, 1.0, -1.0):
            for extra in np.arange(0.0, 3.01, 0.2):
                r = r0 + RING_OUT + extra
                x, z = cx + ux * r - uz * side, cz + uz * r + ux * side
                h = g(x, z)
                if h and h[1] == GRASS and castable(g, x, z):
                    found = (x, z, h)
                    break
            if found:
                break
        if not found:
            raise SystemExit(f"{name}: no lawful ring probe at {deg} deg")
        x, z, h = found
        ring.append({"deg": deg, "world": [round(x, 3), round(z, 3)], "y": round(h[0], 4),
                     "rock_r": round(r0, 2)})
    return g, (cx, cz), {"centre": [round(cx, 3), round(cz, 3)], "summit": summit, "ring": ring,
                         "rock_tris": int((topo == ROCK).sum())}


def main():
    ground, centres, out = {}, {}, {"variants": {}}
    for name, spec in VARIANTS.items():
        ground[name], centres[name], rep = prep_variant(name)
        out["variants"][name] = {**spec, **rep}
        print(f"{name} rot {spec['rot']} x{spec['height']}: centre {rep['centre']}, summit y {rep['summit']['y']} "
              f"(peak {rep['summit']['peak_y']}), ring y {min(p['y'] for p in rep['ring']):.2f}.."
              f"{max(p['y'] for p in rep['ring']):.2f}")
    # shared viewpoints: plain grass with 2u of grass round it in EVERY variant, 14-22u from every massif centre,
    # 8u of walkable ground (not rock, not cliff) toward each, off the lattice; the farthest in each of 4 sectors
    mx = sum(c[0] for c in centres.values()) / 3
    mz = sum(c[1] for c in centres.values()) / 3
    cand = []
    for x in np.arange(1300.0, 1384.0, 0.5):
        for z in np.arange(-112.0, -28.0, 0.5):
            if not (off_lattice(x) and off_lattice(z)):
                continue
            ok = True
            for name, g in ground.items():
                if g.margin(x, z) < MARGIN:
                    ok = False
                    break
                cx, cz = centres[name]
                d = math.hypot(cx - x, cz - z)
                if not 14.0 <= d <= 22.0:
                    ok = False
                    break
                h = g(x, z)
                if not h or h[1] != GRASS or any((g(x + 2 * math.cos(a), z + 2 * math.sin(a)) or (0, -1))[1] != GRASS
                                                 for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)):
                    ok = False
                    break
                ux, uz = (cx - x) / d, (cz - z) / d
                if any((g(x + ux * t, z + uz * t) or (0, -1))[1] != GRASS for t in np.arange(0.5, 8.5, 0.5)):
                    ok = False
                    break
            if ok:
                az = math.degrees(math.atan2(z - mz, x - mx)) % 360
                cand.append((x, z, math.hypot(x - mx, z - mz), az))
    picks = {}
    for x, z, d, az in cand:
        sec = int(((az + 45) % 360) // 90)
        if sec not in picks or d > picks[sec][2]:
            picks[sec] = (x, z, d, az)
    names = {0: "east", 1: "north", 2: "west", 3: "south"}
    views = {}
    for sec, (x, z, d, az) in sorted(picks.items()):
        v = {"world": [round(x, 3), round(z, 3)], "per_variant": {}}
        for name, g in ground.items():
            cx, cz = centres[name]
            dd = math.hypot(cx - x, cz - z)
            ux, uz = (cx - x) / dd, (cz - z) / dd
            v["per_variant"][name] = {"bearing_deg": round(math.degrees(math.atan2(cz - z, cx - x)), 2),
                                      "ground_y": round(g(x, z)[0], 4),
                                      "first_rock": round(first_rock(g, x, z, ux, uz), 2),
                                      "walk_stop": round(walk_stop(g, x, z, ux, uz), 2),
                                      "margin": round(g.margin(x, z), 3)}
        views[names[sec]] = v
    out["views"] = views
    out["candidates"] = len(cand)
    (LAB / "prep.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(views, indent=1))
    print(f"wrote {LAB / 'prep.json'} ({len(cand)} view candidates)")


if __name__ == "__main__":
    main()
