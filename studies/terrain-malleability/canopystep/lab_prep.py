"""comp26 with its canopy IN GAME, the offline half: what the run must read, from the four built variants.

snowmassif/lab_prep.py's down-ray and probes on DESERT (topograph 17), with canopyspread's canopy model: a party on
canopy (topograph 38 here) stands CANOPY_SINK = 1.171875 BELOW its surface (RESULTS section 2). Registers, per variant:
  SUMMIT  the highest rock point off the 4u lattice within 1.5u of the peak, and its height;
  RING    12 points on the desert 2u outside the CARRIED blob's last hit (rock or canopy), one per 30 deg from the
          rock centroid: the zip seam all round, the canopy's wall foot included;
  CANOPY  up to 5 castable points on the carried canopy (nearest its centre, then spread), each surface - the sink;
  INTO    the walk into the canopy: a desert home 8-16u out from the canopy's outer edge, on the line from the rock
          centroid through the canopy's farthest point, facing the rock; where the canopy starts along the line, where
          the rock starts, and the walk model's stop (the climb onto canopy is a slow step, not a wall: round 3);
  VIEWS   the castable desert home per sector nearest VIEW_DIST (28u) from the carried blob, with 8u of desert
          toward the rock centroid, its bearing, and where a walk along it meets rock.
Every teleport target is off the 4u lattice AND >= 0.08 inside its tri.
Writes out/lab/prep.json.  Rerun: py studies/terrain-malleability/canopystep/lab_prep.py
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "mountaindonors"))
import step_carry as C  # noqa: E402  (the worktree-pinned kit)
IN, M, _ = C.S._kit()
from ff9mapkit.world import extract as X  # noqa: E402
# mountainspread's lab_prep (Ground, castable, off_lattice), loaded under its own name: this module is lab_prep too
_spec = importlib.util.spec_from_file_location("spread_lab_prep", HERE.parent / "mountainspread" / "lab_prep.py")
SP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SP)

LAB = HERE / "out" / "lab"
NAME = "FF9CustomMap-lab"
BUILD = json.loads((LAB / "build.json").read_text(encoding="utf-8"))
VARIANTS = {k: v["rot"] for k, v in BUILD.items()}
ROCK = frozenset(IN.MOUNTAIN_ROCK_TOPOS)
DESERT = 17
CANOPY = 38
CANOPY_SINK = 1.171875
RING_OUT = 2.0
VIEW_DIST = 28.0
STEP_UP = SP.STEP_UP
GROUND_PARTS = ("Terrain", "Object")


def blocks_of(variant: str) -> list:
    root = LAB / variant / NAME / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    out = set()
    for p in root.rglob("Block*Terrain.ff9mesh"):
        out.add((int(p.name.split("[")[1].split("]")[0]), int(p.name.split("[")[2].split("]")[0])))
    return sorted(out)


def load(variant: str):
    tris, topo = [], []
    for bx, by in blocks_of(variant):
        for part in GROUND_PARTS:
            p = LAB / variant / NAME / M.override_relpath(1, bx, by, part=part)
            if not p.is_file():
                continue
            d = M.read_ff9mesh(p)
            if not d["indices"]:
                continue
            V = np.asarray(d["verts"], float) + np.array([64.0 * bx, 0.0, -64.0 * by])
            idx = np.asarray(d["indices"]).reshape(-1, 3)
            tris.append(V[idx])
            topo += [X.decode_id(int(round(d["tangents"][t[0]][0])))["topograph"] for t in idx]
    return np.concatenate(tris), np.array(topo)


def is_rock(t) -> bool:
    return int(t) in ROCK


def expect_y(hit) -> float:
    """Where the party stands on a surface hit: the canopy sinks him."""
    return hit[0] - CANOPY_SINK if hit[1] == CANOPY else hit[0]


def along(g, x, z, ux, uz, reach=80.0):
    """(first canopy, first rock) along the ray, units from (x, z)."""
    fc = fr = None
    for r in np.arange(0.0, reach, 0.1):
        h = g(x + ux * r, z + uz * r)
        if h is None:
            continue
        if fc is None and h[1] == CANOPY:
            fc = float(r)
        if is_rock(h[1]):
            fr = float(r)
            break
    return fc, fr


def last_hit(g, cx, cz, ux, uz, topos, reach=80.0):
    r_last = None
    for r in np.arange(0.0, reach, 0.1):
        h = g(cx + ux * r, cz + uz * r)
        if h is not None and (is_rock(h[1]) or h[1] in topos):
            r_last = float(r)
    return r_last


def prep_variant(name, rot):
    T, topo = load(name)
    g = SP.Ground(T, topo)
    rmask = np.array([is_rock(t) for t in topo])
    cmask = topo == CANOPY
    R = T[rmask].reshape(-1, 3)
    Cv = T[cmask].reshape(-1, 3)
    cx, cz = float(R[:, 0].mean()), float(R[:, 2].mean())
    pk = R[R[:, 1].argmax()]
    best = None
    for sx in np.arange(pk[0] - 1.5, pk[0] + 1.51, 0.1):
        for sz in np.arange(pk[2] - 1.5, pk[2] + 1.51, 0.1):
            if SP.castable(g, sx, sz):
                h = g(sx, sz)
                if h and is_rock(h[1]) and (best is None or h[0] > best[2][0]):
                    best = (float(sx), float(sz), h)
    if best is None:
        raise SystemExit(f"{name}: no lawful summit probe")
    summit = {"world": [round(best[0], 3), round(best[1], 3)], "y": round(best[2][0], 4), "peak_y": round(float(pk[1]), 4)}
    ring = []
    for deg in range(0, 360, 30):
        ux, uz = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        r0 = last_hit(g, cx, cz, ux, uz, {CANOPY})
        found = None
        for side in (0.0, 0.6, -0.6, 1.0, -1.0, 1.6, -1.6):
            for extra in np.arange(0.0, 3.01, 0.2):
                r = r0 + RING_OUT + extra
                x, z = cx + ux * r - uz * side, cz + uz * r + ux * side
                hh = g(x, z)
                if hh and hh[1] == DESERT and SP.castable(g, x, z):
                    found = (x, z, hh)
                    break
            if found:
                break
        if not found:
            raise SystemExit(f"{name}: no lawful ring probe at {deg} deg")
        x, z, hh = found
        ring.append({"deg": deg, "world": [round(x, 3), round(z, 3)], "y": round(hh[0], 4), "blob_r": round(r0, 2)})
    # CANOPY points: castable, on the canopy as the down-ray's top hit, nearest the canopy centre first, then spread
    ccx, ccz = float(Cv[:, 0].mean()), float(Cv[:, 2].mean())
    cand = []
    for t in T[cmask]:
        for w in ((1 / 3, 1 / 3, 1 / 3), (0.6, 0.2, 0.2), (0.2, 0.6, 0.2), (0.2, 0.2, 0.6)):
            px, pz = float(w @ t[:, 0]), float(w @ t[:, 2])
            hh = g(px, pz)
            if hh and hh[1] == CANOPY and SP.castable(g, px, pz):
                cand.append((math.hypot(px - ccx, pz - ccz), px, pz, hh))
    cand.sort()
    canopy = []
    for _, px, pz, hh in cand:
        if all(math.hypot(px - q["world"][0], pz - q["world"][1]) >= 3.0 for q in canopy):
            canopy.append({"world": [round(px, 3), round(pz, 3)], "surface": round(hh[0], 4),
                           "y": round(hh[0] - CANOPY_SINK, 4)})
        if len(canopy) == 5:
            break
    # INTO: from the rock centroid out through the canopy's farthest vertex
    far = Cv[np.argmax(np.hypot(Cv[:, 0] - cx, Cv[:, 2] - cz))]
    ox, oz = float(far[0] - cx), float(far[2] - cz)
    on = math.hypot(ox, oz)
    ox, oz = ox / on, oz / on
    into = None
    edge = last_hit(g, cx, cz, ox, oz, {CANOPY})
    for dist in np.arange(8.0, 16.1, 0.5):
        for off in (0.0, 0.7, -0.7, 1.4, -1.4):
            hx, hz = cx + ox * (edge + dist) - oz * off, cz + oz * (edge + dist) + ox * off
            hh = g(hx, hz)
            if not (hh and hh[1] == DESERT and SP.castable(g, hx, hz)):
                continue
            d = math.hypot(cx - hx, cz - hz)
            ux, uz = (cx - hx) / d, (cz - hz) / d
            fc, fr = along(g, hx, hz, ux, uz)
            if fc is None or fr is None or fr - fc < 3.0:
                continue
            into = {"world": [round(hx, 3), round(hz, 3)], "ground_y": round(hh[0], 4),
                    "bearing_deg": round(math.degrees(math.atan2(uz, ux)), 2), "canopy_from": round(fc, 2),
                    "rock_from": round(fr, 2), "margin": round(g.margin(hx, hz), 3)}
            break
        if into:
            break
    # VIEWS
    from scipy.spatial import cKDTree
    blobk = cKDTree(np.vstack([R, Cv])[:, [0, 2]])
    xs, zs = T[:, :, 0], T[:, :, 2]
    cands = []
    for x in np.arange(float(xs.min()), float(xs.max()), 0.5):
        for z in np.arange(float(zs.min()), float(zs.max()), 0.5):
            if not (SP.off_lattice(x) and SP.off_lattice(z)) or g.margin(x, z) < SP.MARGIN:
                continue
            rd = float(blobk.query([x, z])[0])
            if rd < 10.0:
                continue
            hh = g(x, z)
            if not hh or hh[1] != DESERT:
                continue
            if any((g(x + 2 * math.cos(a), z + 2 * math.sin(a)) or (0, -1))[1] != DESERT
                   for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)):
                continue
            d = math.hypot(cx - x, cz - z)
            ux, uz = (cx - x) / d, (cz - z) / d
            if any((g(x + ux * t, z + uz * t) or (0, -1))[1] != DESERT for t in np.arange(0.5, 8.5, 0.5)):
                continue
            cands.append((x, z, d, math.degrees(math.atan2(z - cz, x - cx)) % 360, rd))
    picks = {}
    for x, z, d, az, rd in cands:
        sec = int(((az + 45) % 360) // 90)
        key = (round(abs(rd - VIEW_DIST), 1), -d)
        if sec not in picks or key < picks[sec][0]:
            picks[sec] = (key, (x, z, d))
    names = {0: "east", 1: "north", 2: "west", 3: "south"}
    views = {}
    for sec, (_, (x, z, d)) in sorted(picks.items()):
        ux, uz = (cx - x) / d, (cz - z) / d
        fc, fr = along(g, x, z, ux, uz)
        views[names[sec]] = {"world": [round(x, 3), round(z, 3)], "dist": round(d, 2),
                             "bearing_deg": round(math.degrees(math.atan2(cz - z, cx - x)), 2),
                             "ground_y": round(g(x, z)[0], 4), "canopy_from": fc, "first_rock": fr,
                             "margin": round(g.margin(x, z), 3)}
    return {"rot": rot, "blocks": blocks_of(name), "centre": [round(cx, 3), round(cz, 3)], "summit": summit,
            "ring": ring, "canopy": canopy, "into": into, "views": views, "view_candidates": len(cands),
            "rock_tris": int(rmask.sum()), "canopy_tris": int(cmask.sum())}


def main():
    out = {"variants": {}, "sink": CANOPY_SINK}
    for name, rot in VARIANTS.items():
        rep = prep_variant(name, rot)
        out["variants"][name] = rep
        print(f"{name} rot {rot}: rock {rep['rock_tris']} canopy {rep['canopy_tris']}; summit y {rep['summit']['y']}; "
              f"ring y {min(p['y'] for p in rep['ring']):.2f}..{max(p['y'] for p in rep['ring']):.2f}; canopy pts "
              f"{len(rep['canopy'])}; into {rep['into']}; views "
              f"{ {k: (v['dist'], v['canopy_from'], v['first_rock']) for k, v in rep['views'].items()} }")
    (LAB / "prep.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {LAB / 'prep.json'}")


if __name__ == "__main__":
    main()
