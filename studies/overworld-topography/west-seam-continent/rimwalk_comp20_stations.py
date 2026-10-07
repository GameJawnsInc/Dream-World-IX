"""Where the comp20 rim walk stands -- computed from the DEPLOYED continent, read-only.

rimwalk_stations.py's machinery (the mesh query, the "massif rises here" test, the clean-approach finder, the
seam and grass-run finders), re-aimed at comp20 (deployed 2026-10-06 at (1486,-386) rot 90). The owner passed
every face in-game (COMP20-BENCH.md C4), so every station is a CONTROL: rock should stop him at the contact
with no climb where the face rises, and he should walk on with no curb where it does not.

Writes ``rimwalk_comp20.json`` beside this file (the shape rimwalk_stations.json has).

    py -X utf8 studies/overworld-topography/west-seam-continent/rimwalk_comp20_stations.py
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rimwalk_stations as RS                              # noqa: E402
from envelope_profile import read_loose, stations, GRASS   # noqa: E402

OUT = HERE / "rimwalk_comp20.json"
MASSIF = (1486.0, -386.0)                                   # the deployed placement
REACH = 48.0                                                # r_rim 31.5u + the zip/apron band
BEARINGS = list(range(0, 360, 30))                          # one station per 30 deg of the rim, where lawful
VIEW_AT = [((1519.8, -389.3), "east-coastal-rock")]          # the owner-look teleport (faces west)


def main():
    tris = []
    for bx in RS.COLS:
        for by in RS.ROWS:
            tris.extend(read_loose(bx, by))
    g = RS.Ground(tris)
    raw = [s for s in stations(tris) if math.hypot(s[0] - MASSIF[0], s[1] - MASSIF[1]) <= REACH]
    print(f"continent tris {len(tris)}; comp20 rock-grass contact edges {len(raw)}")
    seen, picked = [], []
    for x, z, ux, uz in sorted(raw):
        if any(math.hypot(x - a, z - b) < 3.0 for a, b in seen):
            continue
        seen.append((x, z))
        picked.append((x, z, ux, uz))

    def bearing(p):
        return math.degrees(math.atan2(p[1] - MASSIF[1], p[0] - MASSIF[0])) % 360

    rows, used = [], []
    for want in BEARINGS:
        cands = sorted(picked, key=lambda p: min(abs(bearing(p) - want), 360 - abs(bearing(p) - want)))
        for p in cands:
            off = min(abs(bearing(p) - want), 360 - abs(bearing(p) - want))
            if off > 15 or p in used:
                continue
            lawn = g.top(p[0], p[1])
            if lawn is None:
                continue
            a, d = RS._approach(g, p[0], p[1], p[2], p[3], lawn[0])
            if a is None:
                continue
            used.append(p)
            rises = RS._rises(g, p[0], p[1], p[2], p[3])
            rows.append({"kind": "control", "contact": [round(p[0], 2), round(p[1], 2)],
                         "uphill": [round(p[2], 4), round(p[3], 4)], "rises": rises,
                         "lawn_y": round(lawn[0], 2), "approach": a, "approach_d": d,
                         "bearing": round(math.degrees(math.atan2(p[3], p[2])) % 360, 1),
                         "rim_bearing": round(bearing(p), 1)})
            print(f"  rim {bearing(p):5.1f} deg ({p[0]:7.1f},{p[1]:7.1f}) {'RISES' if rises else 'flat '} lawn "
                  f"{lawn[0]:5.2f} approach {a} (d={d})")
            break
        else:
            print(f"  rim {want:3d} deg: no lawful station (no clean lawn approach within 15 deg)")

    # seam latitudes + the grass run: rimwalk_stations' own finders, re-run on today's mesh
    seam = []
    xs = [1490.0 + 2 * i for i in range(23)] + [2.0 * i for i in range(21)]
    for zi in range(-264, -640, -8):
        ys = RS._flat_grass(g, [(x, float(zi)) for x in xs])
        if ys is not None:
            seam.append({"z": float(zi), "from_x": 1490.0, "to_x": 40.0, "y": round(sum(ys) / len(ys), 2)})
    if len(seam) > 2:
        seam = [seam[0], seam[-1]]
    run = None
    for b in range(0, 360, 15):
        ux, uz = math.cos(math.radians(b)), math.sin(math.radians(b))
        length = 0
        for d in range(2, 122, 2):
            if RS._flat_grass(g, [(RS.LANDING[0] + ux * d, RS.LANDING[1] + uz * d)], y0=g.top(*RS.LANDING)[0]) is None:
                break
            length = d
        if run is None or length > run["length"]:
            run = {"start": list(RS.LANDING), "bearing": float(b), "length": float(length)}

    # look-only views: the owner-look teleport, then N/S/W standpoints ~34u out on flat grass facing the massif
    views = []
    for (vx, vz), name in VIEW_AT:
        views.append({"name": name, "at": [vx, vz], "bearing": round(math.degrees(math.atan2(MASSIF[1] - vz, MASSIF[0] - vx)) % 360, 1)})
    for b, name in ((90, "north"), (270, "south"), (180, "west")):
        for dist in (34.0, 40.0, 46.0, 28.0):
            vx = MASSIF[0] + math.cos(math.radians(b)) * dist
            vz = MASSIF[1] + math.sin(math.radians(b)) * dist
            t = g.top(vx, vz)
            ring = [g.top(vx + ox, vz + oz) for ox, oz in ((6, 0), (-6, 0), (0, 6), (0, -6))]
            if t and t[1] == GRASS and all(r is not None and r[1] == GRASS for r in ring):
                views.append({"name": name, "at": [round(vx, 2), round(vz, 2)],
                              "bearing": round((b + 180.0) % 360.0, 1), "dist": dist})
                break
    print(f"stations {len(rows)} ({sum(r['rises'] for r in rows)} rising); seam {[s['z'] for s in seam]}; "
          f"grass run {run}; views {[v['name'] for v in views]}")
    OUT.write_text(json.dumps({"stations": rows, "seam": seam, "grass_run": run, "views": views,
                               "massif": list(MASSIF), "landing": list(RS.LANDING)}, indent=1), encoding="utf-8")
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
