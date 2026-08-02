"""THE BLANK-PAINT GATE — hunt near-white texels showing on terrain, at every
committed camera. READ-ONLY.

Playtest 11: "a couple whitish pixels seaming through". The atlas's unpainted
regions render WHITE in-game (blank-tile law), and the ear/wall uv validation
had two holes: it tested FULL white only (>235 per channel) and it tested the
EXACT uv footprint, while render-time NEAREST sampling can land a texel just
outside it. Both are fixed at the call site; this is the independent check —
it looks at pixels, not at intentions, and it reports WHICH face owns each.

  py probe_blank_paint.py [staged|live]
"""
from __future__ import annotations

import sys
import json
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_gate as RG                                    # noqa: E402
import vcorner_transplant as VT                             # noqa: E402
import probe_cove_cam as PC                                 # noqa: E402

EXTRA = {
    "cove_cam": PC.VIEW,
    "ear": dict(kind="persp", eye=(381.0, 16.0, -505.0), at=(377.0, 3.2, -513.0),
                fov=45.0, reach=40.0),
    "lawn_n": dict(kind="persp", eye=(374.0, 14.0, -500.0), at=(374.0, 3.2, -510.0),
                   fov=45.0, reach=40.0),
    "lawn_s": dict(kind="persp", eye=(379.0, 14.0, -534.0), at=(376.0, 3.2, -524.0),
                   fov=45.0, reach=40.0),
}
# CALIBRATED (2026-08-02): blank paint samples to EXACTLY (255,255,255)
# (world/atlas.py's blank-tile law, reproduced in render_gate.sample). A
# looser threshold measures the rock band's own bright highlights instead:
# at 190 the owner-APPROVED baseline scored 2411 px vs the rebuild's 2087,
# i.e. the gate was reporting the island itself as defective. Judge 250+.
THRESH = 250
CRACK_MAX = 3                   # a crack is thin; a sky gap between hills is not
HOLE_BASE = HERE / "hole_baseline.json"


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "staged"
    if tag == "calibrate":
        r = _run("baseline")
        HOLE_BASE.write_text(json.dumps(
            {"total": r["holes"],
             "note": "thin sky gaps in the bench's own silhouette, measured on the "
                     "pre-corner baseline. The hole gate fails only ABOVE this."},
            indent=1))
        print(f"hole baseline recorded: {r['holes']} px -> {HOLE_BASE.name}")
        return r
    return _run(tag)


def _run(tag):
    # CALIBRATE BEFORE JUDGING: the rock band carries genuinely bright
    # highlights, so a raw white-pixel count is meaningless on its own. The
    # only reading that means anything is MY faces vs the owner-approved
    # coast's own rate — hence the `baseline` corpus state.
    src = dict(VT.staged_src()) if tag == "staged" else RG.state_src(tag)
    batches = RG.load_batches(src)
    views = dict(RG.VIEWS)
    views.update(EXTRA)
    total = 0
    holes = 0
    worst = None
    for name, v in views.items():
        img, ids = RG.raster(v, batches, f"blank_{tag}_{name}", want_ids=True)
        f = img.astype(np.int32)
        # THE HOLE GATE (same raster pass): background pixels ENCLOSED by land —
        # terrain both above and below in the same column. That is the signature
        # of a crack, and it is invisible to the blank-paint test because a hole
        # shows SKY, not unpainted atlas. Measured cost of not having this: 26 px
        # of background opened by a repair whose tolerance was not exact.
        # CALIBRATED: "background with land above and below" also describes the
        # legitimate sky between two distant silhouettes, and scored the
        # owner-accepted bench as defective. A crack is a THIN gap, so require a
        # vertical background run of at most CRACK_MAX px bounded by land.
        bgm = ids < 0
        enc = np.zeros_like(bgm)
        h_img = bgm.shape[0]
        for run in range(1, CRACK_MAX + 1):
            if h_img < run + 2:
                continue
            # start row r: rows r..r+run-1 background, r-1 and r+run both land
            core = np.ones((h_img - run - 1, bgm.shape[1]), dtype=bool)
            for k in range(run):
                core &= bgm[1 + k:h_img - run + k]
            core &= (~bgm[0:h_img - run - 1]) & (~bgm[1 + run:h_img])
            for k in range(run):
                enc[1 + k:h_img - run + k] |= core
        n_holes = int(enc.sum())
        holes += n_holes
        if n_holes:
            ys, xs = np.nonzero(enc)
            print(f"   {name:12s} {n_holes:6d} ENCLOSED background px "
                  f"(crack) e.g. ({xs[0]},{ys[0]})")
        white = (f.min(axis=2) > THRESH) & (ids >= 0)
        # exclude sea sparkle: the caustic textures carry legitimate white
        own = Counter(ids[white].tolist())
        bad = {}
        for oid, cnt in own.items():
            bi = oid >> 20
            if batches[bi][0] in ("Terrain", "Object"):
                bad[oid] = cnt
        n = sum(bad.values())
        total += n
        flag = "" if n == 0 else "   <== BLANK PAINT"
        print(f"   {name:12s} {n:6d} white terrain px{flag}")
        for oid, cnt in sorted(bad.items(), key=lambda kv: -kv[1])[:4]:
            bi, ti = oid >> 20, oid & ((1 << 20) - 1)
            part, verts, uvs, tris = batches[bi]
            t = tris[ti]
            cx = (verts[t[0]] + verts[t[1]] + verts[t[2]]) / 3.0
            if worst is None or cnt > worst[0]:
                worst = (cnt, f"{name} b{bi}#t{ti} @({cx[0]:.2f},{cx[1]:.2f},{cx[2]:.2f})")
            print(f"        {cnt:5d}px {part} b{bi}#t{ti} "
                  f"@({cx[0]:7.2f},{cx[1]:6.2f},{cx[2]:8.2f}) "
                  f"uv {[(round(float(uvs[i][0]), 4), round(float(uvs[i][1]), 4)) for i in t]}")
    print(f"\nBLANK-PAINT GATE [{tag}]: {total} white terrain px "
          f"-> {'PASS' if total == 0 else 'FAIL'}")
    # DIFFERENTIAL, like every gate that survived contact with a playtest: the
    # bench's own silhouette carries thin sky gaps (measured identical on the
    # accepted build and on the baseline), so an absolute zero is the wrong
    # question. Judge against the recorded baseline; regenerate it with
    # `py probe_blank_paint.py calibrate`.
    base = json.loads(HOLE_BASE.read_text())["total"] if HOLE_BASE.is_file() else None
    if base is None:
        print(f"HOLE GATE [{tag}]: {holes} enclosed background px, NO BASELINE "
              f"-> run `probe_blank_paint.py calibrate`")
        holes_ok = False
    else:
        holes_ok = holes <= base
        print(f"HOLE GATE [{tag}]: {holes} enclosed background px vs baseline "
              f"{base} -> {'PASS' if holes_ok else 'FAIL'}")
    return dict(ok=total == 0, white_px=total, worst=worst,
                holes_ok=holes_ok, holes=holes, holes_baseline=base)


if __name__ == "__main__":
    main()
