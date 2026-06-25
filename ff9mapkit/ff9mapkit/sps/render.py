"""Offline preview of an ``.sps`` effect (Tier 0). Composites each frame's quad cloud over the decoded
``spt.tcb`` page into a PNG / contact-sheet / GIF -- "see what FF9's effects look like" without launching
the game (the bespoke analogue of Memoria's in-engine Model Viewer).

The composite is an ADDITIVE approximation: each prim's UV cell is cropped from the page, tinted by its
RGB-ramp colour, premultiplied by its texel alpha, and added onto a black canvas at the prim's screen
offset (``pos_x, pos_y``, +Y up). Additive matches fire/smoke/magic (most field SPS are additive-blended);
pass ``additive=False`` for an alpha-over paste. This is a catalog preview, not the exact engine projection
(no per-camera GTE transform / depth sort). -> [[project-ff9-sps-authoring]].
"""
from __future__ import annotations

from . import texture
from .codec import Sps


def _page_image(sps: Sps, tcb: bytes):
    from PIL import Image  # noqa: PLC0415 - only the preview path needs PIL
    w, h, rgba = texture.tcb_page_rgba(tcb, sps.tpage_raw, sps.clut_raw)
    return Image.frombytes("RGBA", (w, h), rgba)


def _frame_bounds(sps: Sps, cell_w: int, cell_h: int, pad: int):
    """Canvas size + origin covering EVERY frame's prims (so frames align in a strip/GIF)."""
    xs, ys = [], []
    for frame in sps.frames:
        for p in frame:
            xs.append(p.pos_x)
            ys.append(p.pos_y)
    if not xs:
        return cell_w + 2 * pad, cell_h + 2 * pad, 0.0, 0.0
    hx, hy = cell_w / 2, cell_h / 2
    min_x, max_x = min(xs) - hx, max(xs) + hx
    min_y, max_y = min(ys) - hy, max(ys) + hy
    w = int(round(max_x - min_x)) + 2 * pad
    h = int(round(max_y - min_y)) + 2 * pad
    return max(w, 1), max(h, 1), min_x - pad, max_y + pad  # origin x-left / y-top (Y inverted)


def render_frame(sps: Sps, tcb: bytes, frame_index: int = 0, *, scale: int = 3,
                 additive: bool = True, _page=None, _bounds=None):
    """Render one frame's quad cloud to a PIL RGBA image (black/transparent where empty)."""
    from PIL import Image, ImageChops  # noqa: PLC0415

    page = _page if _page is not None else _page_image(sps, tcb)
    uv_w = max(1, sps.w_raw - 1)
    uv_h = max(1, sps.h_raw - 1)
    cell_w, cell_h = uv_w * scale, uv_h * scale
    if _bounds is not None:
        W, H, ox, oy = _bounds
    else:
        W, H, ox, oy = _frame_bounds(sps, cell_w, cell_h, pad=cell_w)

    acc = Image.new("RGB", (W, H), (0, 0, 0))
    if not sps.frames:
        return acc.convert("RGBA")
    prims = sps.frames[frame_index % len(sps.frames)]
    for p in prims:
        ux, uy = sps.uv_table[p.uv_index] if p.uv_index < len(sps.uv_table) else (0, 0)
        cell = page.crop((ux, uy, ux + uv_w, uy + uv_h)).convert("RGBA")
        r, g, b, _pad = sps.rgb_table[p.rgb_index] if p.rgb_index < len(sps.rgb_table) else (255, 255, 255, 0)
        rr, gg, bb, aa = cell.split()
        tint = lambda band, k: band.point(lambda v, k=k: (v * k) >> 8)  # noqa: E731 (×k/256)
        rr, gg, bb = tint(rr, r), tint(gg, g), tint(bb, b)
        if additive:
            # premultiply by alpha so transparent texels add nothing, then add onto the canvas
            rgb = Image.merge("RGB", (ImageChops.multiply(rr, aa), ImageChops.multiply(gg, aa),
                                      ImageChops.multiply(bb, aa)))
            layer = Image.new("RGB", (W, H), (0, 0, 0))
            cx = int(round(p.pos_x - ox)) - cell_w // 2
            cy = int(round(oy - p.pos_y)) - cell_h // 2
            layer.paste(rgb.resize((cell_w, cell_h), Image.NEAREST), (cx, cy))
            acc = ImageChops.add(acc, layer)
        else:
            rgba = Image.merge("RGBA", (rr, gg, bb, aa)).resize((cell_w, cell_h), Image.NEAREST)
            cx = int(round(p.pos_x - ox)) - cell_w // 2
            cy = int(round(oy - p.pos_y)) - cell_h // 2
            acc = acc.convert("RGBA")
            acc.alpha_composite(rgba, (cx, cy))
            acc = acc.convert("RGB")
    # alpha = per-pixel brightness so the preview overlays cleanly (black -> transparent)
    rr, gg, bb = acc.split()
    alpha = ImageChops.lighter(ImageChops.lighter(rr, gg), bb)
    return Image.merge("RGBA", (rr, gg, bb, alpha))


def render_strip(sps: Sps, tcb: bytes, *, scale: int = 3, cols: int = 8, gap: int = 4):
    """Render every frame into one contact-sheet image (frames share a canvas size, so motion aligns)."""
    from PIL import Image  # noqa: PLC0415

    page = _page_image(sps, tcb)
    uv_w, uv_h = max(1, sps.w_raw - 1), max(1, sps.h_raw - 1)
    bounds = _frame_bounds(sps, uv_w * scale, uv_h * scale, pad=uv_w * scale)
    W, H = bounds[0], bounds[1]
    n = max(1, sps.frame_count)
    cols = max(1, min(cols, n))
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * W + (cols - 1) * gap, rows * H + (rows - 1) * gap), (0, 0, 0, 0))
    for i in range(n):
        cell = render_frame(sps, tcb, i, scale=scale, _page=page, _bounds=bounds)
        sheet.alpha_composite(cell, ((i % cols) * (W + gap), (i // cols) * (H + gap)))
    return sheet


def save_png(image, path) -> None:
    image.save(path)


def save_gif(sps: Sps, tcb: bytes, path, *, scale: int = 3, duration_ms: int = 66) -> None:
    """Write an animated GIF of the effect (default ~15 fps, the engine tick). Black background."""
    page = _page_image(sps, tcb)
    uv_w, uv_h = max(1, sps.w_raw - 1), max(1, sps.h_raw - 1)
    bounds = _frame_bounds(sps, uv_w * scale, uv_h * scale, pad=uv_w * scale)
    frames = [render_frame(sps, tcb, i, scale=scale, _page=page, _bounds=bounds).convert("RGB")
              for i in range(max(1, sps.frame_count))]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=duration_ms, loop=0)
