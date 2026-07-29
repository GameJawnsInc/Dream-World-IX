"""The walkmesh floor-height census — Rung 3's `plane_y` decision (studies/click-authoring/PLAN.md).

The camera census proved the click homography exact on every real camera; this measures the
OTHER half of real-field placement: where the floors actually ARE. A click un-projects onto a
plane at height h — exact when the floor under the art is flat at a known h (THE PLANE LAW),
structurally wrong when it slopes. So, for every real field's default walkmesh, in the WORLD
frame (vert + orgPos + floor.org — the import-frame law): per-floor world-y spread (flat or
not), the dominant floor's height (how wrong y=0 would be), floors per field, animated floors.

Read-only against the install:  py studies/click-authoring/floor_census.py
"""
import json
import re
import statistics
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "ff9mapkit"))

from ff9mapkit import extract                                  # noqa: E402
from ff9mapkit.scene import bgi as _bgi                        # noqa: E402

FLAT_EPS = 16.0          # a floor whose world-y spread is under this is FLAT for placement
                         # (plane error h shifts the un-projected point ~h/tan(pitch); 16u is
                         # well under half a collision radius at any vanilla pitch)


def census(verbose=True):
    index = extract.build_field_index(verbose=verbose)
    by_bundle = {}
    for folder, bundle in index.items():
        by_bundle.setdefault(bundle, []).append(folder)
    sa = extract._streaming_assets()
    rows, unreadable = [], []
    for bundle in sorted(by_bundle):
        env = extract._load_env(sa / bundle)
        objs = dict(env.container.items())
        keys = {}
        for k in objs:
            m = re.search(r"fieldmaps/([^/]+)/([^/]+)\.bgi\.bytes$", k.lower())
            if m:
                keys.setdefault(m.group(1), k)
        for folder in sorted(by_bundle[bundle]):
            k = keys.get(folder)
            if k is None:
                unreadable.append((folder, "no .bgi in bundle"))
                continue
            try:
                mesh = _bgi.BgiWalkmesh.from_bytes(extract._raw_bytes(objs[k].read()))
                rows.append(_census_one(folder, mesh))
            except Exception as e:                             # noqa: BLE001 -- census records, never dies
                unreadable.append((folder, f"{type(e).__name__}: {e}"))
        if verbose:
            print(f"  {bundle}: {len(rows)} fields censused", flush=True)
    return rows, unreadable


def _census_one(folder, mesh):
    wv = mesh.world_verts()
    floors = []
    for fl in mesh.floors:
        vids = sorted({vi for ti in fl.tri_ndx_list if 0 <= ti < len(mesh.tris)
                       for vi in mesh.tris[ti].vtx if 0 <= vi < len(wv)})
        ys = [wv[vi][1] for vi in vids]
        if not ys:
            continue
        floors.append({"n": len(vids), "y_med": statistics.median(ys),
                       "spread": max(ys) - min(ys)})
    row = {"field": folder, "floors": len(floors),
           "anms": len(mesh.anms), "verts": len(mesh.verts)}
    if floors:
        dom = max(floors, key=lambda f: f["n"])
        row.update(dom_y=round(dom["y_med"], 1), dom_spread=round(dom["spread"], 1),
                   flat_floors=sum(1 for f in floors if f["spread"] <= FLAT_EPS),
                   max_spread=round(max(f["spread"] for f in floors), 1),
                   floor_stats=[{"n": f["n"], "y": round(f["y_med"], 1),
                                 "spread": round(f["spread"], 1)} for f in floors])
    return row


def main():
    rows, unreadable = census()
    meas = [r for r in rows if "dom_y" in r]
    n = len(meas)
    print(f"\nfields with a walkmesh: {n}   unreadable/no-bgi: {len(unreadable)}")

    all_flat = [r for r in meas if r["flat_floors"] == r["floors"]]
    dom_flat = [r for r in meas if r["dom_spread"] <= FLAT_EPS]
    print(f"\nALL floors flat (spread <= {FLAT_EPS:g}u):      {len(all_flat)}  ({len(all_flat)/n:.0%})")
    print(f"DOMINANT floor flat:                  {len(dom_flat)}  ({len(dom_flat)/n:.0%})")

    off0 = [r for r in meas if abs(r["dom_y"]) > FLAT_EPS]
    print(f"dominant floor's height NOT ~y=0:     {len(off0)}  ({len(off0)/n:.0%})  "
          f"<- how often un-projecting onto y=0 would misplace")
    ys = sorted(abs(r["dom_y"]) for r in meas)
    print(f"|dominant y| median {ys[n // 2]:.0f}u · p90 {ys[int(n * .9)]:.0f}u · max {ys[-1]:.0f}u")

    fc = sorted(r["floors"] for r in meas)
    multi = sum(1 for r in meas if r["floors"] > 1)
    print(f"\nfloors per field: median {fc[n // 2]} · p90 {fc[int(n * .9)]} · max {fc[-1]} · "
          f"multi-floor fields {multi} ({multi/n:.0%})")
    anm = sum(1 for r in meas if r["anms"])
    print(f"fields with ANIMATED floors (platforms): {anm}")

    print("\ndominant-floor spread tiers (how sloped is the main ground):")
    lo = 0.0
    for hi, label in ((1, "<= 1u (exact plane)"), (FLAT_EPS, f"<= {FLAT_EPS:g}u (flat)"),
                      (64, "<= 64u (steps/ramps)"), (float("inf"), "> 64u (sloped -- Blender's)")):
        c = sum(1 for r in meas if lo < r["dom_spread"] <= hi or (lo == 0 and r["dom_spread"] == 0))
        print(f"  {label:28s}: {c:4d}  ({c/n:.0%})")
        lo = hi

    worst = sorted(meas, key=lambda r: -r["dom_spread"])[:8]
    print("\nmost-sloped dominant floors:")
    for r in worst:
        print(f"  {r['field']}: dom spread {r['dom_spread']:g}u · {r['floors']} floors")
    out = Path(__file__).with_name("floor_census.json")
    out.write_text(json.dumps({"rows": rows, "unreadable": unreadable}, indent=0),
                   encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
