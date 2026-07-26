"""Blender camera-view FIDELITY CENSUS -- every real field x every camera, offline.

The add-on's Blender camera is posed via ``cam.decompose`` (the ``R_ff9 = diag(1,k,1) * R_ortho``
invariant, MEASURED ACROSS SIX real cameras) + ``bridge.ff9_cam_to_blender`` (a single isotropic
lens, no principal-point shift). The kit's ``cam.to_canvas`` needs none of that -- it projects
through the RAW matrix and is in-game proven (the walkmesh<->art alignment law). So the oracle and
the candidate are independently computable, bpy-free, for all ~674 fields:

    oracle    px  = to_canvas(P_render, cam_raw)                     (exact, in-game proven)
    candidate px  = pinhole( ff9_cam_to_blender(cam) , P_render )    (what Blender DISPLAYS)

Any field where they disagree is a field the add-on MISFRAMES (the render/export stays exact --
forks ship the real .bgx; this is view/paint-guide fidelity only). Bucketing the failures by the
decompose invariant's residuals (row norms vs (1, k, 1), orthonormality error, determinant sign,
pitch, scrolling) finds the SHARED root causes instead of debugging field-by-field.

Trigger: GameJawns importing TWIN_ALTAR (field 2301, canvas 512x256, decomposed pitch -8.1 deg)
-- "the camera only looks at a small portion of the walkmesh".

Run from the repo root (writes census.csv + prints the bucket summary):
    py studies/blender-camera-fidelity/census.py [--limit N]
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(ROOT / "ff9mapkit" / "blender"))

from ff9mapkit import extract                                   # noqa: E402
from ff9mapkit.scene import bgi, bgs, cam as C                  # noqa: E402
from ff9mapkit_blender import bridge                            # noqa: E402

MAX_VERTS = 240          # subsample cap per field (stride) -- plenty to expose a misframe


def _pinhole_px(b, rw, rh, p_bl, pixel_aspect_y=15.0 / 14.0):
    """The pixel where Blender DISPLAYS a world point through the add-on's camera: params from
    ``ff9_cam_to_blender`` (location/rotation/lens/sensor, sensor_fit HORIZONTAL, no shift),
    render resolution (rw, rh) at ``pixel_aspect_y`` (the add-on sets 15/14 so the vertical
    px-gain carries FF9's K_VSCALE; pass 1.0 to model the PRE-fix isotropic camera -- that run
    measured 738/741 cameras misframed, the census that found this). Returns (px, py) top-left
    origin, or None (behind the camera)."""
    loc, R, lens, sensor = b["location"], b["rotation"], b["lens"], b["sensor_width"]
    d = [p_bl[i] - loc[i] for i in range(3)]
    xc = sum(d[i] * R[i][0] for i in range(3))                  # columns of R = local axes in world
    yc = sum(d[i] * R[i][1] for i in range(3))
    zc = sum(d[i] * R[i][2] for i in range(3))
    if zc >= -1e-6:                                             # camera looks down local -Z
        return None
    depth = -zc
    u = lens * xc / depth
    v = lens * yc / depth
    return ((u / sensor + 0.5) * rw,
            (0.5 - v * rw / (sensor * rh * pixel_aspect_y)) * rh)


def census(limit=None):
    fields = extract.list_fields()
    if limit:
        fields = fields[:limit]
    rows, skipped = [], 0
    for n, (folder, _area, _mapid) in enumerate(fields, 1):
        try:
            _path, _folder, roles, env = extract.find_field(folder)
            if "bgs" not in roles or "bgi" not in roles:
                skipped += 1
                continue
            objs = {k: v for k, v in env.container.items()}
            cams = bgs.parse_cameras(extract._raw_bytes(objs[roles["bgs"]].read()))
            wm = bgi.BgiWalkmesh.from_bytes(extract._raw_bytes(objs[roles["bgi"]].read()))
        except Exception as e:                                   # noqa: BLE001 -- census never dies on one field
            print(f"  !! {folder}: {type(e).__name__}: {e}", file=sys.stderr)
            skipped += 1
            continue
        verts = wm.world_verts()
        stride = max(1, len(verts) // MAX_VERTS)
        # the engine negates walkmesh Y before the GTE (WalkMesh.cs:54) and the Blender import ships
        # the render frame -- census both sides in the RENDER frame
        pts = [(v[0], -v[1], v[2]) for v in verts[::stride]]
        for ci, c in enumerate(cams):
            rw, rh = int(c.range[0]), int(c.range[1])
            if not rw or not rh or not c.proj:
                continue
            scrolling = rw > 384 or rh > 448
            dec = C.decompose(c)
            b = bridge.ff9_cam_to_blender(c, sensor_width=float(rw)) if scrolling \
                else bridge.ff9_cam_to_blender(c)                # exactly _pose_camera_from_ff9
            errs = []
            for p in pts:
                sx, sy, resz = C.project(p, c)
                if resz <= 0:                                    # behind the raw camera
                    continue
                # DELIBERATELY the offset-less canvas form, NOT cam.to_canvas (which since 2026-07
                # folds in the GTE centerOffset): this census validates the Blender POSE
                # (ff9_cam_to_blender models no principal-point shift), and a camera's constant
                # centerOffset shift is absorbed downstream by the per-camera view nudge (ops.py).
                ox, oy = sx + rw / 2.0, rh / 2.0 - sy
                cand = _pinhole_px(b, rw, rh, bridge.ff9_verts_to_blender([p])[0])
                if cand is None:
                    errs.append(1e9)                             # oracle sees it, Blender doesn't: max fault
                    continue
                errs.append(math.hypot(cand[0] - ox, cand[1] - oy))
            if not errs:
                continue
            errs.sort()
            e_p95 = errs[int(0.95 * (len(errs) - 1))]
            pitch = round(math.degrees(math.asin(max(-1.0, min(1.0, -dec["R_ortho"][2][1])))), 2) \
                if dec["det"] > 0 else None                      # forward-row pitch (readout only)
            rows.append({
                "field": folder, "cam": ci, "ncams": len(cams), "w": rw, "h": rh,
                "scroll": int(scrolling), "verts": len(errs),
                "e_p95": round(min(e_p95, 99999.0), 2), "e_max": round(min(errs[-1], 99999.0), 2),
                "k_row1": round(dec["row_norms"][1], 5),
                "rn_dev": round(max(abs(dec["row_norms"][0] - 1.0), abs(dec["row_norms"][2] - 1.0)), 5),
                "ortho_err": round(dec["ortho_err"], 5), "det": round(dec["det"], 4),
                "pitch": pitch if pitch is not None else "",
            })
        if n % 50 == 0:
            print(f"  ...{n}/{len(fields)} fields", file=sys.stderr)
    return rows, skipped


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    rows, skipped = census(limit)
    out = Path(__file__).parent / "census.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} field-cameras censused ({skipped} fields skipped) -> {out}")
    for thr in (2, 10, 50, 500):
        bad = [r for r in rows if r["e_p95"] > thr]
        print(f"  e_p95 > {thr:>3}px : {len(bad):4d} cameras "
              f"({len({r['field'] for r in bad})} fields)")
    bad = sorted((r for r in rows if r["e_p95"] > 2), key=lambda r: -r["e_p95"])
    if bad:
        print("\nworst 20:")
        for r in bad[:20]:
            print(f"  {r['field']:44s} cam{r['cam']} {r['w']}x{r['h']} e95={r['e_p95']:>9} "
                  f"k1={r['k_row1']} rn_dev={r['rn_dev']} ortho={r['ortho_err']} det={r['det']}")
        # bucket the failures by which invariant they break
        def frac(pred):
            hit = [r for r in bad if pred(r)]
            return f"{len(hit):4d}/{len(bad)}"
        print("\nfailure buckets (of the >2px set):")
        print(f"  det < 0 (mirrored R)        : {frac(lambda r: r['det'] < 0)}")
        print(f"  ortho_err > 0.01            : {frac(lambda r: r['ortho_err'] > 0.01)}")
        print(f"  row0/2 norms off 1 (>0.01)  : {frac(lambda r: r['rn_dev'] > 0.01)}")
        print(f"  k_row1 off 14/15 (>0.01)    : {frac(lambda r: abs(r['k_row1'] - 14/15) > 0.01)}")
        print(f"  scrolling                   : {frac(lambda r: r['scroll'])}")
        print(f"  multicam (cam > 0)          : {frac(lambda r: r['cam'] > 0)}")


if __name__ == "__main__":
    main()
