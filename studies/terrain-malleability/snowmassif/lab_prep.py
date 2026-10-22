"""comp9 IN GAME (round 21), the offline half: what the run must read, from the three built variants.

mountainspread/lab_prep.py's down-ray and probes, on SNOW (topograph 27), with comp9's Object-part plugs in the
ground, per-variant views (each rotation seats its own centre), and one thing new: THE INLET. The carried inlet floor
is located in each variant by fitting the donor's rigid rock onto the carved rock (rock is verbatim, so the fit is
exact), then mapping the donor's inlet floor tris through it. Registers, per variant:
  SUMMIT  the highest rock point off the 4u lattice within 1.5u of the peak, and its height;
  RING    12 points on the snow 2u outside the rock's last hit, one per 30 deg from the rock centroid;
  INLET   the carried floor's tris (world), a castable probe on the floor + its height, and a home on the
          island's snow facing the inlet mouth with where a walk in stops;
  VIEWS   the castable island-snow home per sector nearest VIEW_ROCK (28u) from the rock (east/north/west/south of the rock centroid), with
          8u of snow toward the massif, its bearing and where a walk along it stops.
Every teleport target is off the 4u lattice AND >= 0.08 inside its tri.
Writes out/lab/prep.json.  Rerun: py studies/terrain-malleability/snowmassif/lab_prep.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "mountaindonors"))
import inlet_floor as F  # noqa: E402  (COMP9, COMP9_INLET, the worktree-pinned kit)
IN, M, _ = F._kit()
from ff9mapkit.world import extract as X  # noqa: E402
import importlib.util  # noqa: E402
# mountainspread's lab_prep (Ground, castable, off_lattice), loaded under its own name: this module is lab_prep too
_spec = importlib.util.spec_from_file_location("spread_lab_prep", HERE.parent / "mountainspread" / "lab_prep.py")
SP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SP)

LAB = HERE / "out" / "lab"
NAME = "FF9CustomMap-lab"
BUILD = json.loads((LAB / "build.json").read_text(encoding="utf-8"))
VARIANTS = {k: v["rot"] for k, v in BUILD.items()}
ROCK = frozenset(IN.MOUNTAIN_ROCK_TOPOS)
SNOW = 27
RING_OUT = 2.0
VIEW_ROCK = 28.0                          # a view home's distance from the nearest rock
MOUTH_HOME = (588.6, -85.7)               # the inlet mouth's midpoint at home, world x/z (INLET.md, comp9_diagnose.py)
STEP_UP = SP.STEP_UP
GROUND_PARTS = ("Terrain", "Object")      # the down-ray's parts (Object registers ahead of Terrain; plugs live there)


def blocks_of(variant: str) -> list:
    root = LAB / variant / NAME / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    out = set()
    for p in root.rglob("Block*Terrain.ff9mesh"):
        bx, by = p.name.split("]")[0][6:], p.name.split("[")[2].split("]")[0]
        out.add((int(bx), int(by)))
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


def walk_stop(g, x, z, ux, uz, reach=80.0):
    """mountainspread's walk, rock = any MOUNTAIN_ROCK_TOPOS."""
    y = g(x, z)[0]
    for r in np.arange(0.1, reach, 0.1):
        hs = [h for h in g.hits(x + ux * r, z + uz * r) if h[0] <= y + STEP_UP]
        if not hs:
            return float(r)
        y2, topo = hs[-1]
        if is_rock(topo):
            return float(r)
        y = y2
    return None


def first_rock(g, x, z, ux, uz, reach=90.0):
    for r in np.arange(0.0, reach, 0.1):
        h = g(x + ux * r, z + uz * r)
        if h is not None and is_rock(h[1]):
            return float(r)
    return None


def last_rock(g, cx, cz, ux, uz, reach=90.0):
    r_last = None
    for r in np.arange(0.0, reach, 0.1):
        h = g(cx + ux * r, cz + uz * r)
        if h is not None and is_rock(h[1]):
            r_last = float(r)
    return r_last


_HOME: dict = {}


def home_blob():
    """comp9's donor blob with the inlet, as carve_mountain reads it: rock verts and the inlet floor tris."""
    if not _HOME:
        B = IN._mountain_blob(F.COMP9, rock_topos=ROCK, alcove_box=F.COMP9_INLET, log=lambda *a: None)
        dV = np.asarray(B["dV2"], float)         # the de-tilted positions: what the carve carries (not the raw dV)
        rock_t = [t for t in B["blob"] if B["dtopo"][t] in ROCK]
        floor_t = [t for t in B["blob"] if B["dtopo"][t] not in ROCK]
        _HOME["rock"] = dV[np.asarray([B["dtri"][t] for t in rock_t]).reshape(-1)]
        _HOME["floor"] = dV[np.asarray([B["dtri"][t] for t in floor_t])]
    return _HOME


def fit(variant_rock: np.ndarray, rot: int):
    """world = R(rot) . (home - hc) + (wc, dy), rot_pt's sense (dx' = c dx + s dz, dz' = -s dx + c dz, k = rot/90),
    plus the carve's one height lift dy. The rock is verbatim and rigid, so the fitted home rock must land exactly on
    the carved rock. The carved rock carries extra vertices (tris split at block borders), so the centroid is only a
    start: plan nearest-neighbour iterations from a 1u grid of starts round it (one start can settle in a wrong
    minimum), the best kept; then dy = the median height difference. Returns (map, plan p95, height spread p95)."""
    from scipy.spatial import cKDTree
    h = home_blob()["rock"]
    hc = h[:, [0, 2]].mean(0)
    k = rot / 90.0
    c, s = math.cos(k * math.pi / 2), math.sin(k * math.pi / 2)
    d = h[:, [0, 2]] - hc
    turned = np.stack([c * d[:, 0] + s * d[:, 1], -s * d[:, 0] + c * d[:, 1]], 1)
    tree = cKDTree(variant_rock[:, [0, 2]])
    c0 = variant_rock[:, [0, 2]].mean(0)
    best = None
    for ox in np.arange(-6.0, 6.01, 1.0):
        for oz in np.arange(-6.0, 6.01, 1.0):
            wc = c0 + (ox, oz)
            for _ in range(30):
                _, idx = tree.query(turned + wc)
                step = np.median(variant_rock[idx][:, [0, 2]] - (turned + wc), axis=0)
                wc = wc + step
                if np.hypot(*step) < 1e-6:
                    break
            r = float(np.percentile(tree.query(turned + wc)[0], 95))
            if best is None or r < best[0]:
                best = (r, wc)
    plan, wc = best
    _, idx = tree.query(turned + wc)
    dyv = variant_rock[idx][:, 1] - h[:, 1]
    dy = float(np.median(dyv))
    spread = float(np.percentile(np.abs(dyv - dy), 95))

    def mp(P):
        q = P[..., [0, 2]] - hc
        out = P.copy()
        out[..., 0] = wc[0] + c * q[..., 0] + s * q[..., 1]
        out[..., 2] = wc[1] - s * q[..., 0] + c * q[..., 1]
        out[..., 1] = P[..., 1] + dy
        return out
    return mp, plan, spread, dy


def prep_variant(name, rot):
    T, topo = load(name)
    g = SP.Ground(T, topo)
    rmask = np.array([is_rock(t) for t in topo])
    R = T[rmask].reshape(-1, 3)
    cx, cz = float(R[:, 0].mean()), float(R[:, 2].mean())
    pk = R[R[:, 1].argmax()]
    best = None
    for sx in np.arange(pk[0] - 1.5, pk[0] + 1.51, 0.1):
        for sz in np.arange(pk[2] - 1.5, pk[2] + 1.51, 0.1):
            if not SP.castable(g, sx, sz):
                continue
            h = g(sx, sz)
            if h and is_rock(h[1]) and (best is None or h[0] > best[2][0]):
                best = (float(sx), float(sz), h)
    if best is None:
        raise SystemExit(f"{name}: no lawful summit probe")
    sx, sz, h = best
    summit = {"world": [round(sx, 3), round(sz, 3)], "y": round(h[0], 4), "peak_y": round(float(pk[1]), 4)}
    ring = []
    for deg in range(0, 360, 30):
        ux, uz = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        r0 = last_rock(g, cx, cz, ux, uz)
        found = None
        for side in (0.0, 0.6, -0.6, 1.0, -1.0, 1.6, -1.6):
            for extra in np.arange(0.0, 3.01, 0.2):
                r = r0 + RING_OUT + extra
                x, z = cx + ux * r - uz * side, cz + uz * r + ux * side
                hh = g(x, z)
                if hh and hh[1] == SNOW and SP.castable(g, x, z):
                    found = (x, z, hh)
                    break
            if found:
                break
        if not found:
            raise SystemExit(f"{name}: no lawful ring probe at {deg} deg")
        x, z, hh = found
        ring.append({"deg": deg, "world": [round(x, 3), round(z, 3)], "y": round(hh[0], 4), "rock_r": round(r0, 2)})
    # THE INLET: the donor floor mapped through the rock fit
    mp, plan, spread, dy = fit(R, rot)
    floor = mp(home_blob()["floor"])                       # (n, 3, 3)
    fc = floor.reshape(-1, 3).mean(0)
    inlet = {"fit_plan_p95": round(plan, 5), "fit_height_spread_p95": round(spread, 5), "lift": round(dy, 4),
             "floor_tris": int(len(floor)),
             "floor_centre": [round(float(fc[0]), 3), round(float(fc[1]), 3), round(float(fc[2]), 3)]}
    probe = None                                          # a castable point on the carried floor, nearest its centre
    for t in sorted(floor, key=lambda t: math.hypot(t[:, 0].mean() - fc[0], t[:, 2].mean() - fc[2])):
        px, pz = float(t[:, 0].mean()), float(t[:, 2].mean())
        hh = g(px, pz)
        if hh and hh[1] == SNOW and SP.castable(g, px, pz) and abs(hh[0] - float(t[:, 1].mean())) < 0.3:
            probe = {"world": [round(px, 3), round(pz, 3)], "y": round(hh[0], 4)}
            break
    inlet["probe"] = probe
    # the mouth home: snow on the island, 14-30u from the floor probe out THROUGH the inlet's mouth (the home mouth,
    # INLET.md's (588.6, -85.7), mapped by the fit), with snow all the way from it to the floor probe (the walk in)
    mouth = mp(np.array([[*MOUTH_HOME[:1], 0.0, MOUTH_HOME[1]]]))[0]
    inlet["mouth"] = [round(float(mouth[0]), 3), round(float(mouth[2]), 3)]
    if probe:
        ox, oz = probe["world"]
        ax, az = float(mouth[0]) - ox, float(mouth[2]) - oz
        an = math.hypot(ax, az) or 1.0
        ax, az = ax / an, az / an
        home = None
        for dist in np.arange(14.0, 30.1, 0.5):
            for off in (0.0, 0.7, -0.7, 1.4, -1.4):
                hx, hz = ox + ax * dist - az * off, oz + az * dist + ax * off
                hh = g(hx, hz)
                if not (hh and hh[1] == SNOW and SP.castable(g, hx, hz)):
                    continue
                ux, uz = (ox - hx), (oz - hz)
                d = math.hypot(ux, uz)
                ux, uz = ux / d, uz / d
                if all((g(hx + ux * t, hz + uz * t) or (0, -1))[1] == SNOW for t in np.arange(0.5, d, 0.5)):
                    home = (hx, hz, hh, ux, uz, d)
            if home:
                break
        if home:
            hx, hz, hh, ux, uz, d = home
            inlet["home"] = {"world": [round(hx, 3), round(hz, 3)], "ground_y": round(hh[0], 4),
                             "bearing_deg": round(math.degrees(math.atan2(uz, ux)), 2), "to_probe": round(d, 2),
                             "walk_stop": round(walk_stop(g, hx, hz, ux, uz) or -1, 2),
                             "first_rock": round(first_rock(g, hx, hz, ux, uz) or -1, 2),
                             "margin": round(g.margin(hx, hz), 3)}
    # VIEWS: per sector, the farthest castable island snow from the rock centroid with 2u of snow round it, >= 10u
    # from any rock vertex, and 8u of snow toward the centroid
    from scipy.spatial import cKDTree
    rk = cKDTree(R[:, [0, 2]])
    xs, zs = T[:, :, 0], T[:, :, 2]
    cand = []
    for x in np.arange(float(xs.min()), float(xs.max()), 0.5):
        for z in np.arange(float(zs.min()), float(zs.max()), 0.5):
            rd = float(rk.query([x, z])[0])
            if not (SP.off_lattice(x) and SP.off_lattice(z)) or rd < 10.0:
                continue
            if g.margin(x, z) < SP.MARGIN:
                continue
            hh = g(x, z)
            if not hh or hh[1] != SNOW:
                continue
            if any((g(x + 2 * math.cos(a), z + 2 * math.sin(a)) or (0, -1))[1] != SNOW
                   for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)):
                continue
            d = math.hypot(cx - x, cz - z)
            ux, uz = (cx - x) / d, (cz - z) / d
            if any((g(x + ux * t, z + uz * t) or (0, -1))[1] != SNOW for t in np.arange(0.5, 8.5, 0.5)):
                continue
            cand.append((x, z, d, math.degrees(math.atan2(z - cz, x - cx)) % 360, rd))
    # per sector, the home nearest VIEW_ROCK from the rock (a 130u ridge seen from its far coast is a sliver; from
    # 10u, a wall), the farther from the centroid on a tie
    picks = {}
    for x, z, d, az, rd in cand:
        sec = int(((az + 45) % 360) // 90)
        key = (round(abs(rd - VIEW_ROCK), 1), -d)
        if sec not in picks or key < picks[sec][0]:
            picks[sec] = (key, (x, z, d, az))
    picks = {sec: v for sec, (_, v) in picks.items()}
    names = {0: "east", 1: "north", 2: "west", 3: "south"}
    views = {}
    for sec, (x, z, d, az) in sorted(picks.items()):
        ux, uz = (cx - x) / d, (cz - z) / d
        views[names[sec]] = {"world": [round(x, 3), round(z, 3)], "dist": round(d, 2),
                             "bearing_deg": round(math.degrees(math.atan2(cz - z, cx - x)), 2),
                             "ground_y": round(g(x, z)[0], 4), "first_rock": round(first_rock(g, x, z, ux, uz), 2),
                             "walk_stop": round(walk_stop(g, x, z, ux, uz) or -1, 2), "margin": round(g.margin(x, z), 3)}
    return {"rot": rot, "blocks": blocks_of(name), "centre": [round(cx, 3), round(cz, 3)], "summit": summit,
            "ring": ring, "inlet": inlet, "views": views, "view_candidates": len(cand),
            "rock_tris": int(rmask.sum())}


def main():
    out = {"variants": {}}
    for name, rot in VARIANTS.items():
        rep = prep_variant(name, rot)
        out["variants"][name] = rep
        print(f"{name} rot {rot}: centre {rep['centre']} summit y {rep['summit']['y']} (peak {rep['summit']['peak_y']}) "
              f"ring y {min(p['y'] for p in rep['ring']):.2f}..{max(p['y'] for p in rep['ring']):.2f}; "
              f"inlet fit {rep['inlet']['fit_plan_p95']}/{rep['inlet']['fit_height_spread_p95']} lift {rep['inlet']['lift']} probe {rep['inlet']['probe']} "
              f"home {rep['inlet'].get('home')}; views {sorted(rep['views'])}")
    (LAB / "prep.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {LAB / 'prep.json'}")


if __name__ == "__main__":
    main()
