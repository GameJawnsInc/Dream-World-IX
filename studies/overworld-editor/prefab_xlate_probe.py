"""PREFAB FEASIBILITY probe 1: is a seeded world-island mint the same land when it is moved?

A prefab can only carry its in-game verdict to a new place if placing it there writes the SAME bytes (shifted).
This builds the mint (``island.build_landmass``, no install needed) at a base centre and at shifted centres and
compares every triangle's world-relative position + UV.  Run from the repo root:  py studies/overworld-editor/prefab_xlate_probe.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
import ff9mapkit.world.island as I  # noqa: E402

assert pathlib.Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__


def soup(built, cx, cz, uv=True):
    out = []
    for (bx, by), bm in built["blocks"].items():
        ox, oz = bx * 64, -by * 64
        for t in bm.tris:
            tri = []
            for i in t:
                v, u = bm.verts[i], bm.uvs[i]
                p = (round(v[0] + ox - cx, 3), round(v[1], 3), round(v[2] + oz - cz, 3))
                tri.append(p + ((round(u[0], 5), round(u[1], 5)) if uv else ()))
            out.append(tuple(sorted(tri)))
    return sorted(out)


BASE = (400.0, -700.0)
CASES = [
    ("grass r30 lobes2", dict(base_radius=30.0, seed=7.0, lobes=2)),
    ("desert r40", dict(base_radius=40.0, seed=3.0, ground="desert")),
    ("snow r60 lobes2", dict(base_radius=60.0, seed=11.0, lobes=2, ground="snow")),
    ("grass relief, seed from centre", dict(base_radius=30.0, seed=7.0, relief_amp=1.3)),
    ("grass relief, relief_seed pinned", dict(base_radius=30.0, seed=7.0, relief_amp=1.3, relief_seed=5.0)),
]
for name, kw in CASES:
    a = I.build_landmass(center=BASE, **kw)
    sa, ga = soup(a, *BASE), soup(a, *BASE, uv=False)
    row = []
    for d in (4, 32, 64, 128, 192):
        c = (BASE[0] + d, BASE[1] - d)
        b = I.build_landmass(center=c, **kw)
        same_geo = soup(b, *c, uv=False) == ga
        same_all = soup(b, *c) == sa
        row.append(f"{d}:{'SAME' if same_all else ('geo-only' if same_geo else 'diff')}")
    print(f"{name:34} {len(sa):5} tris  " + "  ".join(row))
