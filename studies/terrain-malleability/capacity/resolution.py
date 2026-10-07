"""CAPACITY lane, step 7 -- RESOLUTION: (a) the atlas sizes the engine can render (vanilla p0data Texture2D
header vs the loose HD override the engine resolves -- PNG IHDR only, no pixels decoded); (b) the stock
vertex QUANTIZATION (are terrain verts on a 1/256-u PSX grid? on the 4u lattice?); (c) the texel density
model -> texels per world unit and per 4u lattice cell, from out/census_cache.json's measured UV rates.

Calibration for (b): the generic ocean fill Sea4f (12,0) is a perfect 16x16 4u grid (README.md:1210) ->
it must read 100% on-lattice and 100% on the 1/256 grid.

Read-only on the install. Writes out/resolution.json.  Run:  py studies/terrain-malleability/capacity/resolution.py
"""
import glob
import json
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world import atlas as A  # noqa: E402
from census import decode, PAT  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")


def png_dims(p):
    b = Path(p).read_bytes()[:24]
    assert b[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    return struct.unpack(">II", b[16:24])


def bundle_tex_dims(names):
    import UnityPy
    sa = GAME / "StreamingAssets"
    found = {}
    for p in sorted(glob.glob(str(sa / "p0data*.bin")), key=lambda q: (0 if "p0data3." in Path(q).name else 1, q)):
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        for o in env.objects:
            if o.type.name != "Texture2D":
                continue
            d = o.read()
            nm = getattr(d, "m_Name", "")
            if nm in names and nm not in found:
                found[nm] = (int(d.m_Width), int(d.m_Height), str(d.m_TextureFormat), Path(p).name)
        if len(found) == len(names):
            break
    return found


def grid_frac(V, step):
    q = V / step
    return float(np.mean(np.all(np.abs(q - np.round(q)) < 1e-4, axis=1)))


def main():
    res = {}
    names = {"res(1_24)_terrain", "res(1_24)_objects"}
    res["bundle_textures"] = bundle_tex_dims(names)
    res["engine_resolved"] = {}
    for part in ("terrain", "object"):
        kind, path = A.resolve_atlas_source(part)
        res["engine_resolved"][part] = {"kind": kind, "path": str(path) if path else None,
                                        "dims": png_dims(path) if path else None}
    # (b) quantization over every disc-1 0_1 mesh, per part
    env = X._worldmap_env(1)
    idx = X._mesh_index(env)
    per = {}
    for c, o in idx.items():
        m = PAT.search(c)
        if not m or int(m.group(1)) != 1 or m.group(2) != "0_1":
            continue
        V, *_ = decode(o.read())
        part = m.group(6)
        xz = V[:, [0, 2]]
        acc = per.setdefault(part, {"n": 0, "xz256": 0.0, "y256": 0.0, "lat4": 0.0, "lat1": 0.0})
        n = len(V)
        acc["n"] += n
        acc["xz256"] += grid_frac(xz, 1 / 256) * n
        acc["y256"] += grid_frac(V[:, [1]], 1 / 256) * n
        acc["lat4"] += grid_frac(xz, 4.0) * n
        acc["lat1"] += grid_frac(xz, 1.0) * n
        if part == "sea4f":
            res["calib_sea4f"] = {"lat4": grid_frac(xz, 4.0), "xz256": grid_frac(xz, 1 / 256), "n": n}
    res["quantization"] = {p: {k: (round(v / a["n"], 4) if k != "n" else v) for k, v in a.items()}
                           for p, a in sorted(per.items())}
    # (c) texel density from the census UV-rate distributions
    cen = json.loads((OUT / "census_cache.json").read_text(encoding="utf-8"))["dist"]["disc1|0_1|terrain"]
    hd_max, hd_min = cen["rate_hd_max"]["p50"], cen["rate_hd_min"]["p50"]
    va_max, va_min = cen["rate_vanilla_max"]["p50"], cen["rate_vanilla_min"]["p50"]
    edge = cen["edge3d"]["p50"]
    res["texel_model"] = {
        "terrain_px_per_u_vanilla_median_[max,min]": [va_max, va_min],
        "terrain_px_per_u_hd_median_[max,min]": [hd_max, hd_min],
        "vanilla_anisotropy_median": round(va_max / va_min, 3),
        "hd_anisotropy_median": round(hd_max / hd_min, 3),
        "hd_texel_size_u": round(1 / ((hd_max + hd_min) / 2), 4),
        "vanilla_texel_size_u_[fine,coarse]": [round(1 / va_max, 4), round(1 / va_min, 4)],
        "median_terrain_edge_u": edge,
        "hd_texels_along_median_edge": round(edge * (hd_max + hd_min) / 2, 1),
        "tile_px_vanilla_[u,v]": [1024 * 0.0625, 1024 * 0.03125], "tile_px_hd_[u,v]": [2048 * 0.0625, 4096 * 0.03125],
    }
    (OUT / "resolution.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
