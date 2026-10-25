"""Native-platform driver for ``test_worldview3d.py`` (not a test module: pytest collects ``test_*.py`` only).

The GPU comparison needs a real OpenGL context, which the offscreen Qt platform every GUI test runs on does not
have, so the tests run this script in a child process on the native platform and read one JSON line back.
Prints ``{"gl": false, ...}`` when no context can be made (a headless box): the caller skips on that and only that.

    python _worldview3d_native.py hermetic      # synthetic scene + the break-it mutations
    python _worldview3d_native.py bench         # the six committed V-shore bench cameras on the install
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # THIS checkout's package, never an installed one
import numpy as np                                             # noqa: E402
from PySide6.QtGui import QGuiApplication                    # noqa: E402


def _hermetic_scene():
    rng = np.random.default_rng(11)
    n = 12
    xs, zs = np.meshgrid(np.linspace(0, 40, n), np.linspace(-40, 0, n))
    ys = rng.uniform(0, 4, xs.shape)
    verts = np.c_[xs.ravel(), ys.ravel(), zs.ravel()]
    uvs = np.c_[xs.ravel() / 13.0, zs.ravel() / 9.0 + 0.3]
    tris = []
    for i in range(n - 1):
        for j in range(n - 1):
            a, b, c, d = i * n + j, i * n + j + 1, (i + 1) * n + j, (i + 1) * n + j + 1
            tris += [(a, c, b), (b, c, d)]
    ground = ("Terrain", verts, uvs, np.array(tris))
    # a wall standing on the ground (both windings: one side faces the camera, one is culled)
    wv = np.array([[8.0, 0.0, -30.0], [30.0, 0.0, -30.0], [8.0, 14.0, -30.0], [30.0, 14.0, -30.0]])
    wall = ("Object", wv, np.array([[0, 0], [2, 0], [0, 1.3], [2, 1.3]], float),
            np.array([(0, 2, 1), (1, 2, 3), (0, 1, 2), (1, 3, 2)]))
    # a lid floating over the ground, facing DOWN: the oracle culls it from above; nothing else hides it
    lid = ("Sea4", np.array([[14.0, 9.0, -22.0], [26.0, 9.0, -22.0], [20.0, 9.0, -10.0]]),
           np.array([[0.1, 0.1], [0.9, 0.1], [0.5, 0.9]]), np.array([(0, 1, 2)]))
    return [ground, wall, lid]


def _hermetic_textures():
    rng = np.random.default_rng(5)
    t = rng.integers(0, 256, (64, 64, 4), dtype=np.uint8)
    t[..., 3] = 255
    t[:16, :16, 3] = 0                                       # a blank corner: drawn white by both
    w = rng.integers(0, 256, (32, 32, 4), dtype=np.uint8)
    w[..., 3] = 255
    return {"Terrain": t, "Object": w, "Sea4": None}         # Sea4 untextured: magenta in both


HERMETIC_VIEWS = {
    "persp_reach": dict(kind="persp", eye=(-10.0, 25.0, -55.0), at=(20.0, 1.0, -20.0), fov=50.0, reach=60.0),
    "persp_near": dict(kind="persp", eye=(20.0, 6.0, -42.0), at=(20.0, 2.0, -20.0), fov=60.0),
    "ortho": dict(kind="ortho", x0=-2.0, x1=42.0, z0=-42.0, z1=2.0),
}


def hermetic(V, R):
    site = R.RenderSite(cells=(), res=(320, 200), game=".")
    batches = _hermetic_scene()
    tex = _hermetic_textures()
    look = tex.get
    out = {"gl": True, "views": {}, "mutations": {}}
    for vn, v in HERMETIC_VIEWS.items():
        a = R.raster(v, batches, vn, site=site, tex_lookup=look, verbose=False)
        g = V.render_still(batches, v, res=site.res, tex_lookup=look)
        c = V.compare(a, g)
        c["sky_frac"] = float((a == R.SKY).all(axis=2).mean())
        out["views"][vn] = c
    flipped = {k: (t[::-1].copy() if t is not None else None) for k, t in tex.items()}
    mutants = {
        "texture_v_not_flipped": dict(tex_lookup=flipped.get),
        "cull_off": dict(tex_lookup=look, cull=False),
        "a_batch_dropped": dict(tex_lookup=look, batches=[batches[0], batches[2]]),   # the wall (the lid is culled)
    }
    # THE GAME'S FOG (C18): the shader's fog against world.fog's software twin (render.raster's depth, fog_still),
    # graded over each view (a ramp from its own depths, the height term on), and the break-it: the GPU fogged, the
    # oracle not
    from ff9mapkit.world import fog as FG
    out["fog"], out["fog_mutation"] = {}, {"blob": 0}
    for vn, v in HERMETIC_VIEWS.items():
        if v["kind"] != "persp":
            continue
        a, dep = R.raster(v, batches, vn, site=site, tex_lookup=look, verbose=False, want_depth=True)
        p20, p80 = np.percentile(dep[np.isfinite(dep)], [20, 80])
        fog = FG.Fog(start=float(p20), end=float(p80), per_u=1.5, floor=1.0)
        af = FG.fog_still(a, dep, v, fog)
        g = V.render_still(batches, v, res=site.res, tex_lookup=look, fog=fog)
        c = V.compare(af, g, sky=fog.rgb, tol=1)          # one level: float32 against float64 rounding, no more
        c["fogged_frac"] = float((np.abs(af.astype(int) - a.astype(int)).max(axis=2) > 8).mean())
        out["fog"][vn] = c
        out["fog_mutation"]["blob"] = max(out["fog_mutation"]["blob"], V.compare(a, g)["blob"])
    for mn, kw in mutants.items():
        worst = {"blob": 0, "coverage": 0}
        for vn, v in HERMETIC_VIEWS.items():
            a = R.raster(v, batches, vn, site=site, tex_lookup=look, verbose=False)
            kw2 = dict(kw)
            b = kw2.pop("batches", batches)
            g = V.render_still(b, v, res=site.res, **kw2)
            c = V.compare(a, g)
            worst = {k: max(worst[k], c[k]) for k in worst}
        out["mutations"][mn] = worst
    return out


def bench(V, R):
    site = R.BENCH_VSHORE
    batches = R.load_batches(site)
    out = {"gl": True, "tris": int(sum(len(t) for *_, t in batches)), "views": {}}
    for vn, v in R.BENCH_VIEWS.items():
        a = R.raster(v, batches, vn, site=site, verbose=False)
        g = V.render_still(batches, v, res=site.res, site=site)
        c = V.compare(a, g)
        c["sky_frac"] = float((a == R.SKY).all(axis=2).mean())
        out["views"][vn] = c
    return out


def main(mode):
    app = QGuiApplication(sys.argv[:1])                      # noqa: F841 -- the GL platform must exist
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import render as R
    assert Path(V.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[1]), V.__file__
    if not V.gl_available():
        return {"gl": False, "platform": QGuiApplication.platformName()}
    return {"hermetic": hermetic, "bench": bench}[mode](V, R)


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1])))
