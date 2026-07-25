"""THE NEW CONTINENT -- block-level interior siting on the CHOSEN outline.

Chosen mint: world-island --center 176,-176 --radius 96 --lobes 3 --seed 31 --ground grass
(the largest candidate that survives continent_verify.py's FINE footprint test: 19 blocks,
41,087 u2, span 209x258, rmin 76.6 / rmax 135.0, med_turn 10.16 vs the gate floor 8.0).

Computes the interior distance-to-rim field and greedily sites the interior verbs against
their REAL clearance constants (interior.py): mountain benches, canopy blobs, hills.
Read-only; writes JSON + PNG to out/world-design/.
"""
from __future__ import annotations
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ff9mapkit"))
from ff9mapkit.world import mesh as M  # noqa: E402

OUT = os.path.join(HERE, "out", "world-design")
BLOCK = 64.0
CX, CZ, R, LOBES, SEED = 176.0, -176.0, 96.0, 3, 31.0

pts, radii = M.multi_blob_outline(CX, CZ, lobes=LOBES, base_radius=R, seed=SEED)
n = len(radii)


def r_at(th):
    f = (th % (2 * math.pi)) / (2 * math.pi) * n
    i = int(f) % n
    t = f - int(f)
    return radii[i] * (1 - t) + radii[(i + 1) % n] * t


def dist_to_rim(px, pz):
    """+ inside (distance to the outline along the ray, a good proxy for a star-convex blob)."""
    dx, dz = px - CX, pz - CZ
    d = math.hypot(dx, dz)
    if d < 1e-6:
        return min(radii)
    return r_at(math.atan2(dz, dx)) - d


# --- true nearest-rim distance (the clearance the verbs actually gate on) -------------------
RIMPTS = pts


def clearance(px, pz):
    if dist_to_rim(px, pz) <= 0:
        return -1.0
    return min(math.hypot(px - a, pz - b) for (a, b) in RIMPTS)


STEP = 4.0
grid = []
gx = CX - max(radii) - 8
while gx <= CX + max(radii) + 8:
    gz = CZ - max(radii) - 8
    while gz <= CZ + max(radii) + 8:
        c = clearance(gx, gz)
        if c > 0:
            grid.append((gx, gz, c))
        gz += STEP
    gx += STEP

# --- the interior programme, each entry = (label, verb, required clearance from the rim) ----
# interior.py constants: RIM_MARGIN 5.0 (forest footprint), RIM_CLEAR 6.0 + FOOT=r+2 (hill),
# MTN_GBLEND 12.0 (mountain ground-apron blend reach) + the donor's own foot-ring radius.
PROGRAMME = [
    # label            verb            footprint_r  rim_need   mutual clearance to others
    ("massif-A (horseshoe ensemble, r54.3 foot ring)", "world-mountain --donor 5-6,15-16", 54.3, 54.3 + 12 + 6, 8.0),
    ("massif-B (Uaho, r~20 pocket)", "world-mountain --donor 0,0", 20.0, 20.0 + 12 + 6, 8.0),
    ("forest-1 (topo-37 canopy, donor 15,15)", "world-forest", 22.0, 22.0 + 5.0, 6.0),
    ("forest-2", "world-forest", 22.0, 22.0 + 5.0, 6.0),
    ("forest-3", "world-forest", 22.0, 22.0 + 5.0, 6.0),
] + [(f"hill-{i}", "world-hill --height 4.2 --radius 18", 20.0, 20.0 + 6.0, 4.0) for i in range(1, 11)]

placed = []
for (label, verb, foot, rimneed, mutual) in PROGRAMME:
    best = None
    for (gx, gz, c) in grid:
        if c < rimneed:
            continue
        ok = True
        for p in placed:
            if math.hypot(gx - p["at"][0], gz - p["at"][1]) < foot + p["foot"] + max(mutual, p["mutual"]):
                ok = False
                break
        if not ok:
            continue
        # prefer the most-interior site for massifs, spread for the rest
        score = c if not placed else (c - 0.35 * min(math.hypot(gx - p["at"][0], gz - p["at"][1])
                                                     for p in placed))
        if best is None or score > best[0]:
            best = (score, gx, gz, c)
    if best:
        placed.append({"label": label, "verb": verb, "foot": foot, "mutual": mutual,
                       "at": [round(best[1], 1), round(best[2], 1)],
                       "rim_clearance_u": round(best[3], 1),
                       "block": [int(best[1] // BLOCK), int(-best[2] // BLOCK)]})
    else:
        placed.append({"label": label, "verb": verb, "foot": foot, "mutual": mutual,
                       "at": None, "rim_clearance_u": None, "REFUSED": "no site with the required rim clearance"})

blocks = set()
for i in range(n):
    t = 0.0
    th = 2 * math.pi * i / n
    while t <= radii[i]:
        x = CX + t * math.cos(th)
        z = CZ + t * math.sin(th)
        blocks.add((int(x // BLOCK), int(-z // BLOCK)))
        t += 2.0

rep = {"mint": {"cmd": f"world-island --center {CX:.0f},{CZ:.0f} --radius {R:.0f} --lobes {LOBES} "
                       f"--seed {SEED:.0f} --ground grass --height 3.2 --patches 3",
                "center": [CX, CZ], "radius": R, "lobes": LOBES, "seed": SEED,
                "rmin_u": round(min(radii), 1), "rmax_u": round(max(radii), 1),
                "span_x": round(max(p[0] for p in pts) - min(p[0] for p in pts), 1),
                "span_z": round(max(p[1] for p in pts) - min(p[1] for p in pts), 1),
                "area_u2": round(0.5 * sum(radii[i] * radii[(i + 1) % n] * math.sin(2 * math.pi / n)
                                           for i in range(n))),
                "blocks": sorted(blocks), "n_blocks": len(blocks),
                "shape": M.outline_shape_stats(pts)},
       "interior": placed,
       "max_interior_clearance_u": round(max(c for _, _, c in grid), 1)}

print(json.dumps(rep["mint"], indent=1)[:1200])
print("\nmax interior clearance:", rep["max_interior_clearance_u"])
for p in placed:
    print(f"  {p['label']:<50} at={p['at']} rim_clear={p.get('rim_clearance_u')} block={p.get('block')}"
          + ("  <<< " + p["REFUSED"] if "REFUSED" in p else ""))

with open(os.path.join(OUT, "continent_layout.json"), "w", encoding="utf-8") as f:
    json.dump(rep, f, indent=1)
print("wrote", os.path.join(OUT, "continent_layout.json"))
