"""THE MAP ERASE: take land a mod folder REMOVED off the painted world map (``world-minimap``'s erase pass).

``world-minimap`` draws a folder's deployed land onto the full-screen chart, but a folder can also take land AWAY
(``world-sink`` sinks an island, an in-place coast cut pulls a coast back) and the chart still painted it. This pass
repaints such land as the sea round it.

THE CHART IS HAND-PAINTED, so the geometry cannot say on its own which pixels draw an island. Over the registered
art frame the painted coasts sit up to ~15px (~20u) off the true geometry, and their shapes differ (a lagoon
island at (553, -1127) is drawn ~18px north of where it stands). Its sea is a parchment with a gentle stain, each
coast wears a soft green HALO (some of its shallow water; about half the shallow water is plain parchment) and a
drop shadow to the south-east. So the erase works on the ART, with the geometry as the seed:

1. **What the folder removed** (:func:`class_rasters`): every map pixel is deep (0), shallow (1: sea1/2/3/5) or
   land (2: terrain, beach, Object, the river parts), rasterized from stock and from the folder's overrides over
   stock; a pixel whose class falls is removed. A removal under :data:`MIN_REMOVED_PX` is a coast tweak, not lost
   land.
2. **What the chart draws** (:func:`chart_features`): a pixel is a FEATURE when its colour stands off the local
   parchment (a field fitted to the clean parchment round it); a feature is HALO when it is greener than the
   parchment at the same brightness and a region at least 3px across (a thinner ring is a coast's rim), else land,
   rim or shadow.
3. **Local alignment**: round each removal the stock geometry is slid over the chart up to :data:`ALIGN_REACH` px
   to best overlap the drawn features (intersection over union), round where the chart's measured drift puts it
   when the caller knows that (the all-world chart drifts linearly off its frame, up to ~24px at its top and bottom
   edges: ``navimap.WORLD_MAP_DRIFT``). A site that overlaps under
   :data:`ALIGN_MIN_IOU`, or only at the edge of the reach, is one the chart does not draw (the corner island at
   (0, 0) sits under the frame): it is skipped and reported, never guessed at.
4. **What goes**: land-coloured features whose nearest land is removed land (grown through the island's adjacent
   pieces, so a beach stripe drawn apart from its island goes too), halo-coloured pixels on removed land (grass
   reads as halo), halo whose nearest geometry is shallow water that became deep, and, beside what goes, a light
   rim's trace that passed the halo test but stands off the halo drawn round it.
5. **The repaint**: where the new water is deep, parchment; elsewhere whatever the kept chart beside it draws (halo
   or parchment), so the erase never invents a halo edge the chart does not have. Colour = the local field of that
   class (parchment field, or the halo drawn nearby) plus the parchment's own grain, copied from clean parchment
   beside the site.

Nothing outside the chart's art frame is touched (the frame line, the emblem) and nothing but the erased pixels
changes. numpy + Pillow only. In-game proof is a relaunch + a look at the map; offline, the before/after crops.
"""
from __future__ import annotations

import re
from collections import defaultdict

import numpy as np

#: Map pixel classes.
DEEP, SHALLOW, LAND = 0, 1, 2
#: Parts the chart draws as land (everything not water), and the shallow water it may wear a halo over.
LAND_PARTS = frozenset({"terrain", "beach1", "beach2", "object", "falls", "river", "riverjoint", "stream",
                        "volcanocrater", "volcanolava"})
SHALLOW_PARTS = frozenset({"sea1", "sea2", "sea3", "sea5"})
SUPERSAMPLE = 2           # geometry raster: 2x2 sub-pixels, a pixel is covered at half
MIN_REMOVED_PX = 12       # a removal smaller than this (~15 u2) is a coast tweak, not land the chart lost
FEATURE_DIST = 15         # colour distance from the local parchment (3x3-smoothed) that marks a drawn feature
FEATURE_DIST_RAW = 30     # ... or unsmoothed (a 1px rim or shadow line the smoothing would lose)
HALO_GREEN = 10           # halo: (dG - dR) over the parchment above this ...
HALO_BRIGHT = 22          # ... at a brightness within this of the parchment's
HALO_TRACE = 20           # a "halo" pixel this far off the halo drawn round it, beside an erase, is a rim's trace
ALIGN_REACH = 20          # px: how far the chart may sit from the geometry
ALIGN_MIN_IOU = 0.35      # below this the chart does not draw the site
WINDOW_PAD = 48           # px of context round each removal
SEED_REACH = 30           # px: how far a pixel looks for its nearest geometry
HIDDEN_Y = -40.0          # a part blanked by a hidden stub sits far below the world


# ---------------------------------------------------------------------------------------------------- raster helpers

def _box(a, r):
    """Box mean of radius ``r`` over the first two axes (edge-padded, running sums)."""
    k = 2 * r + 1
    c = np.cumsum(np.pad(a, [(r + 1, r)] + [(0, 0)] * (a.ndim - 1), mode="edge"), axis=0)
    a = (c[k:] - c[:-k]) / k
    c = np.cumsum(np.pad(a, [(0, 0), (r + 1, r)] + [(0, 0)] * (a.ndim - 2), mode="edge"), axis=1)
    return (c[:, k:] - c[:, :-k]) / k


def blur(a, r):
    """~Gaussian blur of radius ``r`` (three box passes), edge-padded."""
    k = max(1, int(round(r / 1.7)))
    a = np.asarray(a, float)
    for _ in range(3):
        a = _box(a, k)
    return a


def fill_field(img, mask, radii):
    """Normalized convolution of ``img`` (H, W, 3) over ``mask``: the local mean colour of the masked pixels, from
    the tightest radius with support, widening where it has none. Returns ``(field, got)``."""
    out = np.zeros(img.shape, float)
    got = np.zeros(mask.shape, bool)
    m = mask.astype(float)
    for r in radii:
        den = blur(m, r)
        num = blur(img * m[..., None], r)
        ok = ~got & (den > 0.02)
        out[ok] = num[ok] / den[ok][:, None]
        got |= ok
    return out, got


def dilate(m, r):
    """4-connected dilation by ``r`` px (no wrap)."""
    out = m.copy()
    for _ in range(r):
        o = out.copy()
        o[1:] |= out[:-1]
        o[:-1] |= out[1:]
        o[:, 1:] |= out[:, :-1]
        o[:, :-1] |= out[:, 1:]
        out = o
    return out


def label(m):
    """4-connected components of ``m``: ``(labels, n)``."""
    lab = np.zeros(m.shape, np.int32)
    n = 0
    h, w = m.shape
    for y, x in zip(*np.nonzero(m)):
        if lab[y, x]:
            continue
        n += 1
        lab[y, x] = n
        stack = [(y, x)]
        while stack:
            cy, cx = stack.pop()
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = n
                    stack.append((ny, nx))
    return lab, n


def _crop(a, y0, y1, x0, x1):
    """``a[y0:y1, x0:x1]`` with zeros where the box runs past ``a``."""
    out = np.zeros((y1 - y0, x1 - x0) + a.shape[2:], a.dtype)
    sy0, sy1, sx0, sx1 = max(y0, 0), min(y1, a.shape[0]), max(x0, 0), min(x1, a.shape[1])
    if sy0 < sy1 and sx0 < sx1:
        out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = a[sy0:sy1, sx0:sx1]
    return out


def _shift(a, dy, dx):
    """``a`` moved by (dy, dx), zero-filled (no wrap)."""
    out = np.zeros_like(a)
    h, w = a.shape
    out[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = a[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)]
    return out


def nearest(seeds, vals, reach):
    """Each pixel takes the label/value of its nearest seed (8-connected, chessboard), out to ``reach`` px; 0 past
    it."""
    lab, val = seeds.copy(), vals.copy()
    for _ in range(reach):
        free = lab == 0
        if not free.any():
            break
        nl, nv = lab.copy(), val.copy()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            sl, sv = _shift(lab, dy, dx), _shift(val, dy, dx)
            take = free & (nl == 0) & (sl != 0)
            nl[take] = sl[take]
            nv[take] = sv[take]
        lab, val = nl, nv
    return lab, val


# ------------------------------------------------------------------------------------------------- what was removed

def deployed_cells(mod_folder: str, *, disc: int, lod: str = "0_1", game=None) -> tuple:
    """``({block: {part, ...}}, {sidecar block, ...})``: the parts the folder overrides on ``disc``, and the cells it
    re-points at a donor prefab (``Donor.txt``: an ocean cell turned land, not a real cell edited)."""
    from .. import config
    root = config.find_game_path(game) / mod_folder / f"FF9_Data/WorldMap/Disc{disc}/{lod}"
    parts, donor = defaultdict(set), set()
    if not root.is_dir():
        return {}, set()
    for p in root.rglob("Block[[]*"):
        m = re.match(r"Block\[(\d+)\]\[(\d+)\] (\w+)", p.name)
        if not m:
            continue
        b = (int(m.group(1)), int(m.group(2)))
        if p.name.endswith("Donor.txt"):
            donor.add(b)
        elif p.suffix == ".ff9mesh":
            parts[b].add(m.group(3).lower())
    return dict(parts), donor


def _drawable(t) -> bool:
    """A triangle the chart could show: not a hidden stub (far below the world), not zero-area."""
    if max(v[0][1] for v in t) < HIDDEN_Y:
        return False
    (ax, _, az), (bx, _, bz), (cx, _, cz) = (v[0] for v in t)
    return abs((bx - ax) * (cz - az) - (cx - ax) * (bz - az)) > 1e-6


def class_rasters(mod_folder: str, *, disc: int, to_px, size, lod: str = "0_1", game=None) -> tuple:
    """``(stock, effective, edited)``: per-pixel DEEP/SHALLOW/LAND maps (uint8, ``size`` = (W, H)) of stock and of
    the folder's overrides over stock, over every edited real cell and two cells round it (the context an alignment
    window sees), and the edited real cells. ``to_px(wx, wz)`` maps world to chart pixels. Cells re-pointed at a donor
    (``Donor.txt``) are not real cells edited and stay stock here (they ADD land; the paint pass draws it)."""
    from PIL import Image, ImageDraw
    from . import discmirror as DM, transplant as T
    real = DM._real_parts(disc, lod, game=game)
    parts, donor = deployed_cells(mod_folder, disc=disc, lod=lod, game=game)
    edited = sorted(b for b in parts if b not in donor and b in real)
    ctx = sorted({((bx + dx) % 24, by + dy) for bx, by in edited for dx in range(-2, 3) for dy in range(-2, 3)
                  if 0 <= by + dy < 20})
    w, h = size
    ss = SUPERSAMPLE

    def raster(effective: bool):
        land, shal = Image.new("L", (w * ss, h * ss), 0), Image.new("L", (w * ss, h * ss), 0)
        dl, ds = ImageDraw.Draw(land), ImageDraw.Draw(shal)
        for b in ctx:
            mine = effective and b in edited
            for p in sorted(set(real.get(b, ())) | (parts.get(b, set()) if mine else set())):
                if p not in LAND_PARTS and p not in SHALLOW_PARTS:
                    continue
                if mine:
                    tris, _ = T.world_tris_stacked(mod_folder, b[0], b[1], p, disc=disc, lod=lod, game=game)
                else:
                    tris = T.world_tris(b[0], b[1], p, disc=disc, lod=lod, game=game)
                draw = dl if p in LAND_PARTS else ds
                for t in tris:
                    if _drawable(t):
                        draw.polygon([(x * ss, y * ss) for x, y in (to_px(v[0][0], v[0][2]) for v in t)], fill=255)
        g = np.zeros((h, w), np.uint8)
        g[np.array(shal.resize((w, h), Image.BOX)) > 127] = SHALLOW
        g[np.array(land.resize((w, h), Image.BOX)) > 127] = LAND
        return g

    if not edited:
        z = np.zeros((h, w), np.uint8)
        return z, z.copy(), []
    return raster(False), raster(True), edited


# ------------------------------------------------------------------------------------------------- what the chart draws

def chart_features(A, inside, seed_land):
    """``(parchment, dist, feature, halo)`` of chart ``A`` (H, W, 3 float): the local parchment field, each pixel's
    colour distance from it, the drawn features and the halo among them, all within ``inside``. ``seed_land`` (any
    rough land/shallow mask) bootstraps the parchment fit: it is first fitted far (16px+) from it, then to every
    pixel that is not a feature."""
    far = ~dilate(seed_land, 16) & inside
    F, _ = fill_field(A, far, (20, 60, 160))
    for final in (False, True):
        D = A - F
        dist = np.sqrt((D ** 2).sum(-1))
        feat = ((blur(dist, 1) > FEATURE_DIST) | (dist > FEATURE_DIST_RAW)) & inside
        feat &= _box(feat.astype(float), 1) * 9 > 2.5          # parchment grain: drop a speck of 1-2px
        if not final:
            F, _ = fill_field(A, ~dilate(feat, 2) & inside, (10, 30, 90, 240))
    halo = feat & ((D[..., 1] - D[..., 0]) > HALO_GREEN) & (np.abs(D.mean(-1)) < HALO_BRIGHT)
    halo &= dilate(~dilate(~halo, 1), 1)            # halo is a REGION: a 1-2px blend ring is a rim, not halo
    return F, dist, feat, halo


# --------------------------------------------------------------------------------------------------------- the erase

def erase_removed(A, stock, effective, *, inside, drift=None):
    """Repaint, in place on chart ``A`` (H, W, 3 float), the land and halo ``effective`` removed from ``stock``.
    ``inside`` = the pixels the erase may touch (the art inside its frame). ``drift(x, y) -> (dx, dy)``, when given,
    is where the chart is known to sit from the geometry round pixel (x, y) (a measured trend): the alignment then
    searches :data:`ALIGN_REACH` round it instead of round no shift. Returns one report dict per site."""
    removed = (effective < stock) & inside   # land past the frame (a close-up chart's margin) is not drawn
    lab, n = label(removed)
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    removed &= sizes[lab] >= MIN_REMOVED_PX
    if not removed.any():
        return []
    F, dist, feat, halo = chart_features(A, inside, stock > DEEP)
    landc = feat & ~halo
    clean = ~dilate(feat, 2) & inside
    grain = A - F
    halo_all = np.median(A[halo], axis=0) if halo.any() else np.array([151.0, 131.0, 71.0])
    H, W = removed.shape
    iy, ix = np.nonzero(inside)
    ay0, ay1, ax0, ax1 = iy.min(), iy.max() + 1, ix.min(), ix.max() + 1
    R = ALIGN_REACH
    sites, ns = label(dilate(removed, 12))
    reports = []
    for si in range(1, ns + 1):
        mine = (sites == si) & removed       # this site only: a neighbour site in the window is erased on its own shift
        ys, xs = np.nonzero(mine)
        if not len(ys):
            continue
        wy0, wy1 = max(ay0, ys.min() - WINDOW_PAD), min(ay1, ys.max() + WINDOW_PAD + 1)
        wx0, wx1 = max(ax0, xs.min() - WINDOW_PAD), min(ax1, xs.max() + WINDOW_PAD + 1)
        rep = {"window": (int(wx0), int(wy0), int(wx1), int(wy1)), "removed_px": int(len(ys))}
        reports.append(rep)
        phi = feat[wy0:wy1, wx0:wx1]
        hc, xc = halo[wy0:wy1, wx0:wx1], landc[wy0:wy1, wx0:wx1]
        hh, ww = phi.shape
        px0, py0 = (int(round(v)) for v in (drift(xs.mean(), ys.mean()) if drift else (0, 0)))
        P = R + max(abs(px0), abs(py0))      # the farthest slide the search can ask for

        def moved(a, dx, dy):                # ``a`` slid by (dx, dy), seen through the window
            return _crop(a, wy0 - P, wy1 + P, wx0 - P, wx1 + P)[P - dy:P - dy + hh, P - dx:P - dx + ww]
        geo = _crop(dilate(_crop(stock, wy0 - P - 1, wy1 + P + 1, wx0 - P - 1, wx1 + P + 1) > DEEP, 1),
                    1, hh + 2 * P + 1, 1, ww + 2 * P + 1)   # a drawn feature reads 1px wide of its edge: like with like

        def iou(dx, dy):
            s = geo[P - dy:P - dy + hh, P - dx:P - dx + ww]
            return (s & phi).sum() / max(1, (s | phi).sum())
        near = range(-R, R + 1, 2)
        _, bx, by = max((iou(px0 + x, py0 + y), px0 + x, py0 + y) for x in near for y in near)
        score, dx, dy = max((iou(x, y), x, y) for x in range(bx - 1, bx + 2) for y in range(by - 1, by + 2)
                            if abs(x - px0) <= R and abs(y - py0) <= R)
        rep.update(shift=(dx, dy), iou=round(float(score), 3), iou_unshifted=round(float(iou(0, 0)), 3))
        if drift:
            rep["expected"] = (px0, py0)
        if score < ALIGN_MIN_IOU or max(abs(dx - px0), abs(dy - py0)) >= R:
            rep.update(skipped="the chart does not draw this land here", erased_px=0)
            continue
        rm, g0, g1 = moved(mine, dx, dy), moved(stock, dx, dy), moved(effective, dx, dy)
        kept = (g0 == g1) & (g0 > DEEP)
        lost_land = (g0 == LAND) & (g1 < LAND)
        kept_land = (g0 == LAND) & (g1 == LAND)
        # nearest geometry: removed vs kept features (for halo), removed vs kept LAND (for land, rim, shadow)
        nlA, nvA = nearest(np.where(rm, 1, np.where(kept, 2, 0)).astype(np.int32),
                           np.where(rm, g1, g0).astype(np.int32), SEED_REACH)
        nlL, nvL = nearest(np.where(lost_land, 1, np.where(kept_land, 2, 0)).astype(np.int32),
                           np.where(lost_land, g1, LAND).astype(np.int32), SEED_REACH)
        near_lost = (nlL == 1) | ((nlL == 0) & (nlA == 1))
        pieces, _ = label(phi & ~hc)
        reach = dilate(rm, 3)
        gone = np.zeros_like(phi)
        for _ in range(6):                   # grow through the island's adjacent land-coloured pieces
            touched = np.unique(pieces[reach & (pieces > 0)])
            nxt = (np.isin(pieces, touched) & (pieces > 0) & xc) | (hc & lost_land & reach)
            nxt &= near_lost
            if not (nxt & ~gone).any():
                break
            gone |= nxt
            reach = dilate(gone, 2)
        win_in = inside[wy0:wy1, wx0:wx1]
        gone |= dilate(gone, 1) & (dist[wy0:wy1, wx0:wx1] > 12) & ~hc & (nlL != 2) & win_in   # the 1px fringe
        comps, _ = label(phi)
        drawn = np.isin(comps, np.unique(comps[dilate(rm, 3) & (comps > 0)])) & (comps > 0)
        halo_deep = drawn & hc & (nlA == 1) & (nvA == DEEP) & ~gone
        Aw = A[wy0:wy1, wx0:wx1]
        kept_halo = hc & ~gone & ~halo_deep
        Hf, got = fill_field(Aw, kept_halo, (6, 18, 60))
        Hf[~got] = halo_all
        # a TRACE: a light rim blended into the halo (it passed the halo test) beside what goes, standing off the halo
        # drawn round it (the halo's own mottle: p99 23)
        trace = kept_halo & dilate(gone, 3) & (np.sqrt(((Aw - Hf) ** 2).sum(-1)) > HALO_TRACE)
        erase = (gone | halo_deep | trace) & win_in
        if not erase.any():
            rep.update(erased_px=0)
            continue
        if trace.any():
            Hf, got = fill_field(Aw, hc & ~erase, (6, 18, 60))
            Hf[~got] = halo_all
        # target: parchment where the new water is deep; else what the kept chart beside it draws
        edge = ~erase & dilate(erase, 1)
        side = np.where(edge & hc, 1, np.where(edge & ~phi, 2, 0)).astype(np.int32)
        beside, _ = nearest(side, side, 2 * SEED_REACH)
        deep = np.where(nlL == 1, nvL == DEEP, nvA == DEEP)
        to_halo = erase & ~halo_deep & ~deep & (beside == 1)
        # the grain: the parchment's own texture, copied from clean parchment half a window away
        ey, ex = np.nonzero(erase)
        best, off = -1.0, (0, 0)
        for oy, ox in ((0, ww // 2), (0, -(ww // 2)), (hh // 2, 0), (-(hh // 2), 0), (hh // 2, ww // 2),
                       (-(hh // 2), -(ww // 2)), (hh // 2, -(ww // 2)), (-(hh // 2), ww // 2)):
            sy, sx = ey + wy0 + oy, ex + wx0 + ox
            ok = (sy >= 0) & (sy < H) & (sx >= 0) & (sx < W)
            cov = float(clean[sy[ok], sx[ok]].sum()) / len(ey)
            if cov > best:
                best, off = cov, (oy, ox)
        sy = np.clip(ey + wy0 + off[0], 0, H - 1)
        sx = np.clip(ex + wx0 + off[1], 0, W - 1)
        tex = np.where(clean[sy, sx][:, None], grain[sy, sx], 0.0)
        th = to_halo[ey, ex]
        Aw[ey, ex] = np.where(th[:, None], Hf[ey, ex], F[wy0:wy1, wx0:wx1][ey, ex]) + tex
        rep.update(erased_px=int(erase.sum()), to_halo_px=int(th.sum()), halo_to_sea_px=int(halo_deep.sum()))
    return reports
