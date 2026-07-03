"""Extract + preview the overworld texture ATLAS -- the picker behind `world-mesh-build --texture` and T2 HD reskin.

The overworld terrain/object textures are two shared **1024×1024 RGBA** atlases, `res(1_24)_terrain` and
`res(1_24)_objects` (p0data3; the material texture paths in `WMBlock.cs:312-315`). A block's mesh samples a tile by
per-vertex UVs (`pixel = (u·W, (1-v)·H)` -- Unity V is bottom-up, PIL top-down, so V flips). **Blank tiles are
TRANSPARENT** (alpha 0): the `[0,0]` corner and the object atlas's common backing filler ≈(0.15,0.93) are alpha-0 and
render white -- which is why the palette's raw modal could pick a "white" tile. So we detect blank tiles by ALPHA and
drop them, and we crop real tiles for a visual catalog so a user can pick a look by eye.

Two products: **extract** (atlas → PNG, cached) for previewing/repainting, and **crop/blank/catalog** helpers the
palette + CLI use. Repainting the PNG and dropping it at :func:`atlas_override_path` is the no-DLL **T2 HD reskin**
(`AssetManager.SearchAssetOnDisc` checks that mod path first, `WMBlock.cs:290`).
"""
from __future__ import annotations

ATLAS_NAMES = {"terrain": "res(1_24)_terrain", "object": "res(1_24)_objects"}
ATLAS_SIZE = 1024
# T2 reskin override path (SearchAssetOnDisc: Assets/Resources/<name>.png under StreamingAssets; shared, no disc)
_OVERRIDE_REL = "StreamingAssets/assets/resources/worldmap/textures/{name}.png"
_ATLAS_CACHE = ".ff9atlas_{part}.png"                     # cached PNG next to StreamingAssets


def _part_name(part: str) -> str:
    if part not in ATLAS_NAMES:
        raise ValueError(f"part must be 'terrain' or 'object' (got {part!r})")
    return ATLAS_NAMES[part]


def load_atlas(part: str = "terrain", *, game=None, cache: bool = True):
    """The atlas as a PIL ``Image`` (RGBA). Extracted from p0data on first use and cached to a PNG next to
    StreamingAssets; later calls read the cache. Raises if Pillow/UnityPy or the install is missing."""
    import glob
    from pathlib import Path
    from PIL import Image
    from .. import config
    from . import extract as X
    name = _part_name(part)
    sa = Path(config.find_game_path(game)) / "StreamingAssets"
    cache_path = sa / _ATLAS_CACHE.format(part=part)
    if cache and cache_path.is_file():
        return Image.open(cache_path).convert("RGBA")
    X._unitypy()
    import UnityPy
    for p in sorted(glob.glob(str(sa / "p0data*.bin")), key=lambda q: (0 if "p0data3." in Path(q).name else 1, q)):
        try:
            env = UnityPy.load(p)
        except Exception:                                # noqa: BLE001
            continue
        for o in env.objects:
            if o.type.name != "Texture2D":
                continue
            d = o.read()
            if getattr(d, "m_Name", "") == name:
                img = d.image.convert("RGBA")
                if cache:
                    try:
                        img.save(cache_path)
                    except OSError:
                        pass
                return img
    raise ValueError(f"overworld atlas texture {name!r} not found in StreamingAssets/p0data*.bin")


def extract_atlas(part: str = "terrain", *, out, game=None):
    """Save the ``part`` atlas PNG to ``out`` (for previewing or repainting). Returns the written ``Path``."""
    from pathlib import Path
    img = load_atlas(part, game=game)
    dest = Path(out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)
    return dest


def _uv_to_px(u: float, v: float, w: int, h: int) -> tuple:
    """Atlas pixel for a UV (V flipped: Unity bottom-up → PIL top-down). Clamped to the image."""
    px = min(max(int(round(u * (w - 1))), 0), w - 1)
    py = min(max(int(round((1.0 - v) * (h - 1))), 0), h - 1)
    return px, py


def tile_bbox_px(triplet, w: int = ATLAS_SIZE, h: int = ATLAS_SIZE, pad: int = 0) -> tuple:
    """The pixel ``(left, top, right, bottom)`` bounding box of a UV triplet's tile (min 1px), padded by ``pad``."""
    pts = [_uv_to_px(u, v, w, h) for (u, v) in triplet]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    l, t, r, b = min(xs) - pad, min(ys) - pad, max(xs) + 1 + pad, max(ys) + 1 + pad
    return (max(0, l), max(0, t), min(w, max(r, min(xs) + 1)), min(h, max(b, min(ys) + 1)))


def crop_tile(img, triplet, *, pad: int = 1):
    """Crop the atlas region a UV triplet samples (for a preview thumbnail)."""
    return img.crop(tile_bbox_px(triplet, img.width, img.height, pad))


def tile_is_blank(img, triplet, *, alpha_thresh: int = 24) -> bool:
    """True if the tile's atlas region is (near-)fully TRANSPARENT -- a blank filler that renders white. Detected on
    the alpha channel (mean alpha below ``alpha_thresh``)."""
    from PIL import ImageStat
    box = tile_bbox_px(triplet, img.width, img.height, 0)
    region = img.crop(box)
    if region.width < 1 or region.height < 1:
        return True                                          # degenerate region -> treat as blank
    if region.mode != "RGBA":
        return False                                         # no alpha channel -> can't be transparent-blank
    return ImageStat.Stat(region.getchannel("A")).mean[0] < alpha_thresh


def filter_blank(palette: dict, part: str = "terrain", *, game=None) -> dict:
    """Return ``palette`` with transparent-filler tiles dropped (per topograph), so the modal becomes a REAL tile.
    A no-op (returns the input) if the atlas can't be loaded (e.g. on a public clone)."""
    try:
        img = load_atlas(part, game=game)
    except Exception:                                    # noqa: BLE001 -- no atlas -> can't filter, keep as-is
        return palette
    out = {}
    for topo, entries in palette.items():
        kept = [(uv, n) for uv, n in entries if not tile_is_blank(img, uv)]
        if kept:
            out[topo] = kept
    return out


# --------------------------------------------------------------------------- visual tile catalog (the picker)

def tile_catalog(part: str = "terrain", *, disc: int = 1, out, per_topo: int = 8, thumb: int = 40,
                 game=None):
    """Render a contact-sheet PNG: one ROW per topograph, its top ``per_topo`` non-blank donor tiles as ``thumb``-px
    thumbnails, labeled ``topo:variant`` -- so a user picks a look by eye and passes ``--tile TOPO:VARIANT``. Variant
    indices match the (blank-filtered) palette order. Returns the written ``Path``."""
    from pathlib import Path
    from PIL import Image, ImageDraw
    from . import palette as PAL
    img = load_atlas(part, game=game)
    pal = PAL.build_palette(disc=disc, part=part, game=game)     # already blank-filtered by default
    topos = sorted(pal)
    pad, lblw, rowh = 6, 54, thumb + 14
    W = lblw + per_topo * (thumb + pad) + pad
    H = pad + len(topos) * rowh
    sheet = Image.new("RGBA", (W, H), (30, 30, 30, 255))
    draw = ImageDraw.Draw(sheet)
    for ri, topo in enumerate(topos):
        y = pad + ri * rowh
        draw.text((6, y + thumb // 2), f"topo {topo}", fill=(230, 230, 230, 255))
        for vi, (uv, _n) in enumerate(pal[topo][:per_topo]):
            tile = crop_tile(img, uv, pad=1).resize((thumb, thumb), Image.NEAREST)
            x = lblw + vi * (thumb + pad)
            sheet.paste(tile, (x, y), tile if tile.mode == "RGBA" else None)
            draw.text((x, y + thumb + 1), f"{topo}:{vi}", fill=(180, 180, 180, 255))
    dest = Path(out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(dest)
    return dest


# --------------------------------------------------------------------------- T2 HD reskin deploy

def atlas_override_path(part: str, *, mod_folder: str, game=None):
    """The mod-folder path to drop a repainted atlas PNG (T2 reskin): the `SearchAssetOnDisc` disc path
    (`AssetManager.cs:804`, `WMBlock.cs:290`). Same layout for all discs."""
    from pathlib import Path
    from .. import config
    root = config.find_mod_root(config.find_game_path(game), mod_folder)
    return Path(root) / _OVERRIDE_REL.format(name=_part_name(part))


def _px_to_uv(px: int, py: int, w: int, h: int) -> tuple:
    """Pixel → UV (inverse of :func:`_uv_to_px`; V flipped)."""
    return (px / float(w), 1.0 - py / float(h))


def find_free_region(img, tile_px: int = 48, *, cell: int = 16, alpha_thresh: int = 8):
    """Find an unused (fully-transparent) square of ``tile_px`` px in the atlas -- room to PAINT a NEW tile (T3).
    Scans a ``cell``-px occupancy grid; returns the pixel box ``(l, t, r, b)`` of the first free spot, or ``None`` if
    the atlas has no gap that big. Searches from the bottom-right (where the free space clusters)."""
    from PIL import ImageStat
    w, h = img.size
    need = max(1, -(-tile_px // cell))                       # cells per side (ceil)
    free = {}                                                # (cx,cy) cell -> is-free

    def cell_free(cx, cy):
        key = (cx, cy)
        if key not in free:
            box = img.crop((cx * cell, cy * cell, cx * cell + cell, cy * cell + cell))
            a = box.getchannel("A") if box.mode == "RGBA" else None
            free[key] = (a is not None and ImageStat.Stat(a).mean[0] < alpha_thresh)
        return free[key]

    ncx, ncy = w // cell, h // cell
    for cy in range(ncy - need, -1, -1):                     # bottom-up, right-to-left (free space clusters low/right)
        for cx in range(ncx - need, -1, -1):
            if all(cell_free(cx + dx, cy + dy) for dy in range(need) for dx in range(need)):
                l, t = cx * cell, cy * cell
                return (l, t, l + tile_px, t + tile_px)
    return None


def load_tile_png(path):
    """Load a tile PNG as an RGBA PIL image (the new-art the user painted). Raises if missing/unreadable."""
    from pathlib import Path
    from PIL import Image
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"tile PNG not found: {p}")
    return Image.open(p).convert("RGBA")


def make_test_tile(size: int = 44, kind: str = "checker"):
    """A procedural TEST tile (a functional pattern, not art) to prove the T3 pipeline -- a bright checker or solid."""
    from PIL import Image
    img = Image.new("RGBA", (size, size), (255, 0, 255, 255))     # magenta = unmistakably custom
    if kind == "checker":
        px = img.load()
        for y in range(size):
            for x in range(size):
                if ((x // 6) + (y // 6)) % 2:
                    px[x, y] = (30, 220, 90, 255)             # green/magenta checker
    return img


def paint_tile(img, tile, box, *, inset: int = 1):
    """Composite ``tile`` (a PIL image) into the atlas ``img`` at pixel ``box`` (l,t,r,b). Returns
    ``(new_img, uv_rect)`` where ``uv_rect = (umin, vmin, umax, vmax)`` is INSET by ``inset`` px so bilinear sampling
    stays strictly inside the painted tile (no bleed into the surrounding transparent gap)."""
    out = img.convert("RGBA").copy()
    l, t, r, b = box
    out.paste(tile.convert("RGBA").resize((r - l, b - t)), (l, t))
    w, h = out.size
    u0, v_b = _px_to_uv(l + inset, b - inset, w, h)          # bottom-left (V flips, so b→vmin)
    u1, v_t = _px_to_uv(r - inset, t + inset, w, h)          # top-right
    return out, (u0, v_b, u1, v_t)


def add_tile(tile, part: str = "terrain", *, mod_folder: str, game=None, tile_px: int = 48):
    """Paint a NEW ``tile`` (PIL image) into a free atlas region + deploy the reskinned atlas (T3). Returns
    ``{uv_rect, box, dest}`` -- stamp ``uv_rect`` onto custom geometry (``world-mesh-build --tile-uv``). Raises if the
    atlas has no free gap of ``tile_px``. RELAUNCH to apply."""
    img = load_atlas(part, game=game)
    box = find_free_region(img, tile_px)
    if box is None:
        raise ValueError(f"no free {tile_px}px region in the {part} atlas to add a tile")
    painted, uv_rect = paint_tile(img, tile, box)
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.gettempdir()) / f"ff9_atlas_{part}_reskin.png"
    painted.save(tmp)
    dest = deploy_atlas(tmp, part, mod_folder=mod_folder, game=game)
    return {"uv_rect": uv_rect, "box": box, "dest": str(dest)}


def deploy_atlas(png_path, part: str = "terrain", *, mod_folder: str, game=None):
    """Copy a repainted atlas PNG to its mod-override path (T2 HD reskin, no DLL; keep the same UV layout).
    Returns the written ``Path``. RELAUNCH to apply."""
    import shutil
    from pathlib import Path
    src = Path(png_path)
    if not src.is_file():
        raise ValueError(f"atlas PNG not found: {src}")
    dest = atlas_override_path(part, mod_folder=mod_folder, game=game)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    return dest
