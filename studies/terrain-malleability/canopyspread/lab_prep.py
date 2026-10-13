"""`world-forest --spread / --rot` IN GAME, the offline half: what the run must read, from the four built variants.

From each variant's four Terrain overrides (the engine's down-ray: the highest Terrain hit; on topograph 37 the party
stands 1.171875 BELOW the surface, the canopy sink, RESULTS section 2) this registers:
  - CANOPY: 9 points on the canopy (its centre and 8 round it at half its reach), each castable, and the height the
    party must publish there (ground - 1.171875);
  - RING: 12 points on the grass 2u outside the canopy's last hit, one per 30 deg, and their heights -- the zip must
    hold the player at the built height all round (a crack drops him to the sea);
  - VIEWS: plain-grass homes shared by all four variants, 4-18u short of the canopy along the bearing to its centre in
    every variant, each with that bearing and the WALK THROUGH it: where the canopy starts and ends along the line,
    and where the grass resumes on the far side. Every teleport target is castable (off the 4u lattice, >= 0.08
    inside its tri: round 16's lesson).
Writes out/lab/prep.json.  Rerun: py studies/terrain-malleability/canopyspread/lab_prep.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "rockstretch"))
import rot_prep as RP  # noqa: E402  (Ground, castable, the kit import with its worktree assert)
from ff9mapkit.world import mesh as M, extract as X, grassland as G  # noqa: E402

LAB = HERE / "out" / "lab"
NAME = "FF9CustomMap-lab"
BLOCKS = [(bx, by) for by in range(3) for bx in range(20, 23)]
VARIANTS = {"A": {"spread": 1.0, "rot": 0}, "B": {"spread": 1.0, "rot": 45},
            "C": {"spread": 1.25, "rot": 0}, "D": {"spread": 1.5, "rot": 0}}
CANOPY = 37
GRASS = G.GROUNDS["grass"]["topo"]
SINK = 1.171875
RING_OUT = 2.0
PIVOT = (1380.0, -92.0)                   # lab_build.CENTER: every variant is carved about it


def load(variant: str):
    tris, topo = [], []
    for bx, by in BLOCKS:
        d = M.read_ff9mesh(LAB / variant / NAME / M.override_relpath(1, bx, by))
        V = np.asarray(d["verts"], float) + np.array([64.0 * bx, 0.0, -64.0 * by])
        idx = np.asarray(d["indices"]).reshape(-1, 3)
        tris.append(V[idx])
        topo += [X.decode_id(int(round(d["tangents"][t[0]][0])))["topograph"] for t in idx]
    return np.concatenate(tris), np.array(topo)


def along_line(g, x, z, ux, uz, reach=90.0):
    """(first canopy, last canopy, first grass after it) along the ray, in units from (x, z)."""
    first = last = after = None
    for r in np.arange(0.0, reach, 0.1):
        h = g(x + ux * r, z + uz * r)
        if h is None:
            continue
        if h[1] == CANOPY:
            first = r if first is None else first
            last = r
        elif last is not None and h[1] == GRASS and after is None and r > last:
            after = r
            break
    return (None if first is None else round(float(first), 2), None if last is None else round(float(last), 2),
            None if after is None else round(float(after), 2))


def nudge(g, x, z, want, ux, uz):
    """The nearest castable point on topograph ``want`` within 1.5u of (x, z)."""
    for rr in (0.0, 0.3, 0.6, 0.9, 1.2, 1.5):
        for a in range(0, 360, 30 if rr else 360):
            px, pz = x + rr * math.cos(math.radians(a)), z + rr * math.sin(math.radians(a))
            h = g(px, pz)
            if h and h[1] == want and RP.castable(g, px, pz):
                return px, pz, h
    return None


def prep_variant(name):
    T, topo = load(name)
    g = RP.Ground(T, topo)
    C = T[topo == CANOPY].reshape(-1, 3)
    cx, cz = float((C[:, 0].min() + C[:, 0].max()) / 2), float((C[:, 2].min() + C[:, 2].max()) / 2)
    canopy = []
    for k, deg in enumerate([None] + list(range(0, 360, 45))):
        if deg is None:
            x, z, ux, uz = cx, cz, 1.0, 0.0
        else:
            ux, uz = math.cos(math.radians(deg)), math.sin(math.radians(deg))
            _, last, _ = along_line(g, cx, cz, ux, uz)
            x, z = cx + ux * last / 2, cz + uz * last / 2
        got = nudge(g, x, z, CANOPY, ux, uz)
        if not got:
            raise SystemExit(f"{name}: no castable canopy point near ({x:.1f},{z:.1f})")
        px, pz, h = got
        canopy.append({"deg": deg, "world": [round(px, 3), round(pz, 3)], "ground": round(h[0], 4),
                       "y": round(h[0] - SINK, 4)})
    ring = []
    for deg in range(0, 360, 30):
        ux, uz = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        _, last, _ = along_line(g, cx, cz, ux, uz)
        got = None
        for extra in np.arange(0.0, 3.01, 0.2):
            r = last + RING_OUT + extra
            got = nudge(g, cx + ux * r, cz + uz * r, GRASS, ux, uz)
            if got:
                break
        if not got:
            raise SystemExit(f"{name}: no castable ring point at {deg} deg")
        px, pz, h = got
        ring.append({"deg": deg, "world": [round(px, 3), round(pz, 3)], "y": round(h[0], 4),
                     "canopy_r": round(last, 2)})
    return g, (cx, cz), {"centre": [round(cx, 3), round(cz, 3)], "canopy": canopy, "ring": ring,
                         "canopy_tris": int((topo == CANOPY).sum()),
                         "extent": [round(float(C[:, 0].max() - C[:, 0].min()), 2),
                                    round(float(C[:, 2].max() - C[:, 2].min()), 2)]}


def main():
    ground, centres, out = {}, {}, {"variants": {}, "sink": SINK}
    for name, spec in VARIANTS.items():
        ground[name], centres[name], rep = prep_variant(name)
        out["variants"][name] = {**spec, **rep}
        print(f"{name} {spec}: centre {rep['centre']}, extent {rep['extent']}, canopy y "
              f"{min(p['y'] for p in rep['canopy']):.2f}..{max(p['y'] for p in rep['canopy']):.2f}, ring y "
              f"{min(p['y'] for p in rep['ring']):.2f}..{max(p['y'] for p in rep['ring']):.2f}")
    # views: on rays through the shared carve centre (PIVOT, lab_build.CENTER), every 3 deg. Per variant, the
    # profile along the whole diameter (topograph and height every 0.2u); a home on the ray must be castable plain
    # grass with 2u of grass round it, 4-18u short of the canopy, and the walk through (toward the pivot and on out
    # the far side) must meet only grass and canopy, grass resuming within 1u of the canopy's far edge.
    T = np.arange(-60.0, 60.01, 0.2)
    cand = []
    for az in range(0, 360, 3):
        ux, uz = math.cos(math.radians(az)), math.sin(math.radians(az))
        prof = {}
        for name, g in ground.items():
            row = []
            for t in T:
                h = g(PIVOT[0] + ux * t, PIVOT[1] + uz * t)
                row.append(h[1] if h else -1)
            prof[name] = np.array(row)
        for th in np.arange(20.0, 58.01, 0.5):
            x, z = PIVOT[0] + ux * th, PIVOT[1] + uz * th
            if not RP.off_lattice(x) or not RP.off_lattice(z):
                continue
            ok, lines = True, {}
            for name, g in ground.items():
                h = g(x, z)
                if (not h or h[1] != GRASS or g.margin(x, z) < RP.MARGIN
                        or any((g(x + 2 * math.cos(a), z + 2 * math.sin(a)) or (0, -1))[1] != GRASS
                               for a in np.linspace(0, 2 * math.pi, 8, endpoint=False))):
                    ok = False
                    break
                tp = prof[name]
                can = np.where(tp == CANOPY)[0]
                if not len(can):
                    ok = False
                    break
                t_hi, t_lo = T[can.max()], T[can.min()]          # the walk meets t_hi first, leaves at t_lo
                first, last = th - t_hi, th - t_lo
                beyond = np.where((T < t_lo) & (tp == GRASS))[0]
                if not len(beyond) or not 4.0 <= first <= 18.0:
                    ok = False
                    break
                after = th - T[beyond.max()]
                span = (T <= th) & (T >= th - after - 2.5)
                if after - last > 1.0 or not np.isin(tp[span], (GRASS, CANOPY)).all():
                    ok = False
                    break
                lines[name] = (round(float(first), 2), round(float(last), 2), round(float(after), 2), -ux, -uz, h[0])
            if ok:
                cand.append((x, z, sum(v[0] for v in lines.values()), az, lines))
    picks = {}
    for x, z, d, az, lines in cand:                  # the nearest in each sector: the canopy fills the frame
        sec = int(((az + 45) % 360) // 90)
        if sec not in picks or d < picks[sec][2]:
            picks[sec] = (x, z, d, az, lines)
    names = {0: "east", 1: "north", 2: "west", 3: "south"}
    views = {}
    for sec, (x, z, d, az, lines) in sorted(picks.items()):
        v = {"world": [round(x, 3), round(z, 3)], "per_variant": {}}
        for name, (first, last, after, ux, uz, gy) in lines.items():
            v["per_variant"][name] = {"bearing_deg": round(math.degrees(math.atan2(uz, ux)), 2),
                                      "ground_y": round(gy, 4), "canopy_from": first, "canopy_to": last,
                                      "grass_after": after, "margin": round(ground[name].margin(x, z), 3)}
        views[names[sec]] = v
    out["views"] = views
    out["candidates"] = len(cand)
    (LAB / "prep.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(views, indent=1))
    print(f"wrote {LAB / 'prep.json'} ({len(cand)} view candidates)")


if __name__ == "__main__":
    main()
