"""The imported-camera census — the Rung 3 HARD GATE of studies/click-authoring/PLAN.md.

For EVERY camera of every real field in the install: run the shipped conversion pair
(``imagefield.unproject_floor`` -> ``cam.to_canvas``) over a canvas grid below the camera's
horizon and record the worst round-trip residual, plus the decompose diagnostics that would
explain any drift (ortho_err, det, k, pitch, centerOffset). The gate's question: is the
click->world homography exact on the real camera population, or only on the synthesized
envelope it was proven against (pitch 10-45 / yaw +/-25, centerOffset 0)?

Read-only against the install. Run from anywhere:

    py studies/click-authoring/camera_census.py [--out census.json]

Writes the per-camera table as JSON next to this script and prints the distribution.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "ff9mapkit"))

from ff9mapkit import extract, imagefield as IF               # noqa: E402
from ff9mapkit.scene import bgs, cam as C                     # noqa: E402

_LANG_BGS = re.compile(r"_(es|fr|gr|it|jp)\.bgs")
_HORIZON_MARGIN = 3.0        # skip grid rows within this many px below the horizon (s blows up AT it)


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
            kl = k.lower()
            m = re.search(r"fieldmaps/([^/]+)/([^/]+\.bgs)\.bytes$", kl)
            if m and not _LANG_BGS.search(m.group(2)):
                keys.setdefault(m.group(1), k)
        for folder in sorted(by_bundle[bundle]):
            k = keys.get(folder)
            if k is None:
                unreadable.append((folder, "no .bgs in bundle"))
                continue
            try:
                cams = bgs.parse_cameras(extract._raw_bytes(objs[k].read()))
            except Exception as e:                             # noqa: BLE001 -- census records, never dies
                unreadable.append((folder, f"bgs parse: {e}"))
                continue
            for ci, cm in enumerate(cams):
                rows.append(_census_one(folder, ci, cm))
        if verbose:
            print(f"  {bundle}: {len(by_bundle[bundle])} fields done ({len(rows)} cameras)", flush=True)
    return rows, unreadable


def _census_one(folder, ci, cm):
    """One camera, measured per-point through the SHIPPED conversion (no side-of-horizon
    pre-filter: a camera below the y=0 plane has its floor intersections ABOVE the horizon
    line, and an instrument assuming 'floor = below' silently mis-censuses that whole class
    — the first run's 37 phantom errors). A refusal is data, not an error."""
    w, h = int(cm.range[0]), int(cm.range[1])
    row = {"field": folder, "cam": ci, "w": w, "h": h,
           "centerOffset": list(cm.centerOffset), "proj": cm.proj}
    try:
        d = C.decompose(cm)
        row.update(pitch=round(C.pitch_deg(cm), 2), yaw=round(C.yaw_deg(cm), 2),
                   k=round(d["k"], 6), ortho_err=d["ortho_err"], det=round(d["det"], 6),
                   cam_y=round(d["C"][1], 1))
        row["horizon_y"] = round(C.horizon_canvas_y(cm), 1)
    except Exception as e:                                     # noqa: BLE001
        row["error"] = f"decompose: {e}"
        return row
    xs = range(6, max(7, w - 5), max(12, w // 24))
    ys = range(2, max(3, h - 2), max(12, h // 28))
    worst, accepted, refused = 0.0, 0, 0
    for cx in xs:
        for cy in ys:
            try:
                (X, Z), = IF.unproject_floor(cm, [(cx, cy)])
            except IF.ImageFieldError:
                refused += 1                                   # at/above the horizon: expected
                continue
            except Exception as e:                             # noqa: BLE001
                row["error"] = f"unproject ({cx},{cy}): {e}"
                return row
            bx, by = C.to_canvas((X, 0.0, Z), cm)
            worst = max(worst, math.hypot(bx - cx, by - cy))
            accepted += 1
    row.update(grid_accepted=accepted, grid_refused=refused)
    if accepted:
        row["worst_px"] = worst
    else:
        row["note"] = "no grid point intersects the y=0 plane (camera at plane height?)"
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("camera_census.json")))
    args = ap.parse_args()
    rows, unreadable = census()
    fields = {r["field"] for r in rows}
    measured = [r for r in rows if "worst_px" in r]
    errors = [r for r in rows if "error" in r]
    floorless = [r for r in rows if r.get("note")]
    offs = [r for r in rows if r["centerOffset"] != [0, 0]]
    below = [r for r in rows if r.get("cam_y", 1) < 0]
    print(f"\nfields: {len(fields)}  cameras: {len(rows)}  measured: {len(measured)}  "
          f"nonzero-centerOffset: {len(offs)}  below-the-y0-plane: {len(below)}  "
          f"floorless: {len(floorless)}  errors: {len(errors)}  unreadable fields: {len(unreadable)}")
    buckets = [(1e-9, "< 1e-9"), (1e-6, "< 1e-6"), (0.01, "< 0.01"), (0.25, "< 0.25 (the tripwire)"),
               (math.inf, ">= 0.25  ** OUTSIDE THE ENVELOPE **")]
    lo = 0.0
    for hi, label in buckets:
        n = sum(1 for r in measured if lo <= r["worst_px"] < hi)
        print(f"  worst residual {label:38s}: {n}")
        lo = hi
    worst10 = sorted(measured, key=lambda r: -r["worst_px"])[:10]
    print("\nworst 10 cameras:")
    for r in worst10:
        print(f"  {r['field']} cam{r['cam']}: {r['worst_px']:.3g} px  (pitch {r['pitch']}, "
              f"yaw {r['yaw']}, off {r['centerOffset']}, ortho_err {r['ortho_err']:.1e})")
    for r in errors:
        print(f"  ERROR {r['field']} cam{r['cam']}: {r['error']}")
    for f, why in unreadable:
        print(f"  UNREADABLE {f}: {why}")
    Path(args.out).write_text(json.dumps(
        {"rows": rows, "unreadable": unreadable}, indent=0), encoding="utf-8")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
