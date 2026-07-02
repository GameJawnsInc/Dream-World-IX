"""Texture NEW overworld geometry by reusing the shared atlas -- a UV palette learned from real blocks (no DLL).

The overworld terrain/object textures are two GLOBAL shared atlases (terrain is 1024x1024, `WMConstants.cs:83-85`;
object paired). Every block's mesh binds the SAME static `TerrainMaterial`/`ObjectMaterial` (`WMWorldPrefabMaker.cs:193`)
and picks its tile purely by per-vertex UVs (normalized 0..1). A face's `topograph` (`tangent.x` IDALL) does NOT select
the texture -- but real faces of the same topograph reuse a small, stable set of atlas tiles, so we can LEARN a
`topograph -> real donor UV-triplets` map from shipping blocks and stamp those onto new faces (which otherwise carry
`[0,0]` = the atlas corner). No atlas edit, no DLL: the stamped UVs ride the same shared material and deploy via the
loose `.ff9mesh` override the `s34` engine patch already loads.

Robust primitive: **copy a real same-topograph donor face's UV triplet** (topograph is a broad bucket -- e.g. topo 49
spans many tiles -- so there is no single canonical rect; the MODAL, most-frequent tile is the default, and callers
can pick a `variant`). Tiling caveat (from the probe): a real terrain tri's UV rect is only ~5-6% of the atlas, so a
donor triplet is stamped PER TRIANGLE (its 3 UVs -> the tri's 3 corners); do not stretch one tile across a big face.

The `[0,0]` gap this closes lives at `mesh.add_solid_base` (the synthetic collision hull) and any Blender OBJ built
without UVs; :func:`apply_palette_uvs` fixes both by post-stamping every zero-UV face.
"""
from __future__ import annotations

import json

# quantize donor UVs so identical tiles merge (4 decimals ~ sub-pixel on a 1024 atlas)
_UV_Q = 4
_PALETTE_CACHE = ".ff9palette"          # cached next to StreamingAssets, keyed by (disc, part)


def _q(uv) -> tuple:
    return (round(float(uv[0]), _UV_Q), round(float(uv[1]), _UV_Q))


def _is_zero_uv(uvs) -> bool:
    """True if all of a face's corner UVs are ~[0,0] (the placeholder new geometry gets)."""
    return all(abs(u) < 1e-6 and abs(v) < 1e-6 for u, v in uvs)


def sample_donor_faces(disc: int = 1, part: str = "terrain", *, blocks=None, max_blocks: int = 24, game=None):
    """Yield ``(topograph, uv_triplet)`` for every triangle of real ``part`` blocks (up to ``max_blocks``, spread
    across the map for tile variety). ``uv_triplet`` = the 3 corner UVs (quantized). Skips blocks without UVs."""
    from . import extract as X
    from .extract import decode_id
    if blocks is None:
        allb = X.list_blocks(disc=disc, game=game) if part == "terrain" else X.list_object_blocks(disc=disc, game=game)
        if max_blocks and len(allb) > max_blocks:                  # even stride -> spatial spread, not one corner
            step = len(allb) / float(max_blocks)
            blocks = [allb[int(i * step)] for i in range(max_blocks)]
        else:
            blocks = allb
    for (x, y) in blocks:
        try:
            bm = X.read_block(x, y, disc=disc, part=part, game=game)
        except (ValueError, FileNotFoundError):
            continue
        uvs, tans, tris = bm.uvs, bm.tangents, bm.tris
        if not uvs or not tans:
            continue
        for tri in tris:
            topo = decode_id(int(round(tans[tri[0]][0])))["topograph"]
            yield topo, (_q(uvs[tri[0]]), _q(uvs[tri[1]]), _q(uvs[tri[2]]))


def build_palette(disc: int = 1, part: str = "terrain", *, blocks=None, max_blocks: int = 24, game=None,
                  cache: bool = True) -> dict:
    """``{topograph: [(uv_triplet, count), ...]}`` (donor tiles ranked most-frequent first) learned from real blocks.

    Cached per ``(disc, part)`` next to StreamingAssets (first build scans blocks; later ones are instant). Pass
    ``cache=False`` / an explicit ``blocks`` list to force a fresh scan."""
    import collections
    from pathlib import Path
    from .. import config
    cache_path = None
    if cache and blocks is None:
        try:
            cache_path = Path(config.find_game_path(game)) / "StreamingAssets" / f"{_PALETTE_CACHE}_{part}_disc{disc}.json"
            if cache_path.is_file():
                raw = json.loads(cache_path.read_text(encoding="utf-8"))
                return {int(k): [(tuple(map(tuple, uv)), n) for uv, n in v] for k, v in raw.items()}
        except (OSError, ValueError, config.ConfigError):
            cache_path = None
    counts: dict = collections.defaultdict(collections.Counter)
    for topo, triplet in sample_donor_faces(disc, part, blocks=blocks, max_blocks=max_blocks, game=game):
        counts[topo][triplet] += 1
    palette = {topo: [(uv, n) for uv, n in c.most_common()] for topo, c in counts.items()}
    if cache_path is not None and palette:
        try:
            cache_path.write_text(json.dumps({str(k): [[list(map(list, uv)), n] for uv, n in v]
                                              for k, v in palette.items()}), encoding="utf-8")
        except OSError:
            pass
    return palette


def _global_modal(palette: dict):
    """The most-frequent donor triplet across ALL topographs (the fallback tile)."""
    best, best_n = None, -1
    for entries in palette.values():
        if entries and entries[0][1] > best_n:
            best, best_n = entries[0][0], entries[0][1]
    return best


def pick_uvs(palette: dict, topograph: int, *, variant: int = 0):
    """The ``variant``-th most-common donor UV triplet for ``topograph`` as ``[[u,v],[u,v],[u,v]]``. Falls back to
    that topograph's modal tile (if ``variant`` out of range), else the GLOBAL modal tile (if the topograph is absent),
    else ``None`` (empty palette)."""
    entries = palette.get(topograph)
    if entries:
        uv = entries[variant if 0 <= variant < len(entries) else 0][0]
        return [list(c) for c in uv]
    g = _global_modal(palette)
    return [list(c) for c in g] if g else None


def apply_palette_uvs(bm, palette: dict | None = None, *, topograph=None, variant: int = 0,
                      disc: int = 1, part: str = "terrain", only_zero: bool = True, game=None):
    """Return a copy of ``bm`` with real donor UVs stamped onto its faces. For each triangle whose UVs are all
    ``[0,0]`` (``only_zero=True``; else every triangle), look up a donor triplet by the triangle's own topograph
    (or the ``topograph`` override) and map its 3 UVs onto the tri's 3 corners. Builds the palette if not supplied.

    New geometry (an ``add_solid_base`` hull, a UV-less Blender OBJ) thus renders with a real FF9 tile instead of the
    atlas-corner smear. Returns ``bm`` unchanged if there is nothing to stamp or the palette is empty."""
    from .extract import BlockMesh, decode_id, CH_UV
    if CH_UV not in bm.channels:
        return bm
    if palette is None:
        palette = build_palette(disc, part, game=game)
    if not palette:
        return bm
    uvch = [list(v) for v in bm.chan_arrays[CH_UV]]
    tans = bm.tangents
    changed = 0
    for tri in bm.tris:
        corner_uvs = [uvch[i] for i in tri]
        if only_zero and not _is_zero_uv(corner_uvs):
            continue
        topo = topograph if topograph is not None else decode_id(int(round(tans[tri[0]][0])))["topograph"]
        donor = pick_uvs(palette, topo, variant=variant)
        if donor is None:
            continue
        for vi, uv in zip(tri, donor):
            uvch[vi] = list(uv)
        changed += 1
    if not changed:
        return bm
    chan = {ci: ([list(v) for v in uvch] if ci == CH_UV else [list(v) for v in bm.chan_arrays[ci]])
            for ci in bm.channels}
    return BlockMesh(name=bm.name, disc=bm.disc, x=bm.x, y=bm.y, lod=bm.lod, vcount=bm.vcount, stride=bm.stride,
                     channels=dict(bm.channels), chan_arrays=chan, flat_index=list(bm.flat_index),
                     tris=[list(t) for t in bm.tris], raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def palette_summary(palette: dict) -> list:
    """``[(topograph, n_tiles, n_faces, modal_uv_triplet)]`` sorted by topograph -- for the inspect CLI."""
    out = []
    for topo in sorted(palette):
        entries = palette[topo]
        out.append((topo, len(entries), sum(n for _, n in entries), entries[0][0] if entries else None))
    return out
