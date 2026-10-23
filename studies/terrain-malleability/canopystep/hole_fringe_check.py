"""HOLES.md H3 + H1: the fix keeps only fringe, and the three lab islands re-mint hole-free.

H3, independent of the fix's clipper: mint one island with the OLD cut (all-corners, monkeypatched in) and with the
new one, in memory; every Sea4 tri the new cut keeps that the old dropped must have sample points (a 21-step
barycentric grid) under NO land tri of its block -- it reaches past the land -- and every tri both keep or the new
keeps must not be wholly covered on that grid. H1: hole_scan on the three lab islands re-minted with the CLI.
RUN:  py studies/terrain-malleability/canopystep/hole_fringe_check.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import island as I  # noqa: E402
from ff9mapkit.world.extract import CH_POS  # noqa: E402
import hole_scan as H  # noqa: E402

LAB_ISLANDS = {
    "round 23 (grass r66 one-lobe)": ["--ground", "grass", "--center", "1380,-96", "--radius", "66", "--lobes", "1"],
    "round 22 (desert r55 one-lobe)": ["--ground", "desert", "--center", "1380,-100", "--radius", "55", "--lobes", "1"],
    "round 21 (snow r88 two-lobe)": ["--ground", "snow", "--center", "1408,-96", "--radius", "88", "--lobes", "2"],
}
GRID = [(i / 20, j / 20) for i in range(21) for j in range(21 - i)]


def sea_tris(bm):
    P = bm.chan_arrays[CH_POS]
    return {tuple(sorted((round(P[j][0], 4), round(P[j][2], 4)) for j in t)) for t in bm.tris}


def samples_out(cover, tri):
    (ax, az), (bx, bz), (cx, cz) = tri
    out = 0
    for u, v in GRID:
        w = 1 - u - v
        if not I._xz_inside(cover, u * ax + v * bx + w * cx, u * az + v * bz + w * cz):
            out += 1
    return out


def h3():
    old_cut = I._cut_plane

    def all_corners(plane, bx, by, cut_cells, under=None, label_x=None):
        saved = I._xz_uncovered_area
        I._xz_uncovered_area = lambda cover, tri: 0.0          # the old rule: corners decide alone
        try:
            return old_cut(plane, bx, by, cut_cells, under, label_x)
        finally:
            I._xz_uncovered_area = saved
    built_new = I.build_landmass(center=(1380.0, -96.0), base_radius=66.0, seed=42.0, lobes=1, n_patches=0)
    I._cut_plane = all_corners
    try:
        built_old = I.build_landmass(center=(1380.0, -96.0), base_radius=66.0, seed=42.0, lobes=1, n_patches=0)
    finally:
        I._cut_plane = old_cut
    plane = I._sea_plane()
    fringe_ok, covered_kept, new_kept = 0, 0, 0
    for blk, land in built_new["blocks"].items():
        cover = I._xz_tri_cover(land)
        new = sea_tris(I._cut_plane(plane, blk[0], blk[1], frozenset(), land))
        old = sea_tris(all_corners(plane, blk[0], blk[1], frozenset(), built_old["blocks"][blk]))
        for t in new - old:
            new_kept += 1
            if samples_out(cover, t) > 0:
                fringe_ok += 1
        for t in new:
            if samples_out(cover, t) == 0 and I._xz_uncovered_area(cover, list(t)) < I.SEA_CUT_EPS_AREA:
                covered_kept += 1
    print(f"H3: {new_kept} sea tri(s) newly kept, {fringe_ok} reach past the land on the sample grid; "
          f"{covered_kept} kept tri(s) wholly under land -> {'holds' if fringe_ok == new_kept and not covered_kept else 'FALSIFIED'}")


def h1():
    for name, args in LAB_ISLANDS.items():
        tmp = Path(tempfile.mkdtemp(prefix="ff9_h1_"))
        try:
            p = subprocess.run([sys.executable, "-m", "ff9mapkit", "world-island", "--mod-folder", str(tmp / "m"),
                                *args, "--patches", "0", "--seed", "42", "--skip-mirror"], cwd=ROOT / "ff9mapkit",
                               capture_output=True, text=True)
            if p.returncode:
                print(f"H1 {name}: mint refused: {(p.stdout + p.stderr).strip().splitlines()[-1][:120]}")
                continue
            r = H.scan(tmp / "m")
            print(f"H1 {name}: {r['holes']} uncovered point(s)")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    h3()
    h1()
