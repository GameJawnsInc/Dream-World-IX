r"""TIER W rung W6b-1 -- CAST 3: THE GROUND-POOL STAMP GENERATOR (the committed half of the proof).

    py phoenix_pool_stamp.py --from C:\gd\SCRATCH\summon-format\ef211.bytes ^
       --root C:\gd\SCRATCH\summon-format\repaint-w6b\ef211-pool

WHY A SECOND GENERATOR AND NOT A FLAG ON ``phoenix_field_stamp.py``
-------------------------------------------------------------------
``phoenix_field_stamp.py`` places ONE figure at the centroid of a cell's whole UV cover.  That is the
right instrument for a cell with ONE reader.  ``cell.s0.x640_y256`` has TWO, and they are the two
opposite ends of THE UV-SHREDDING BOUND -- so a centroid-placed figure would straddle both and the
cast could not say which surface answered.  This generator places a figure inside each reader's
PRIVATE region instead, and the two figures are deliberately different SHAPES so the screen says
which model drew it.  Cast 2's pinned artifacts regenerate byte-identically because that file is not
touched.

THE MEASUREMENT THIS CAST RESTS ON (re-derived at run time by :func:`uv_report`)
--------------------------------------------------------------------------------
Both readers are 4bpp on tpage 0x1a (VRAM page 640,256).  They could not be less alike:

  geom 0x2d344  CLUT (80,244)  192 FT3   THE CONICAL FLAME SKIRT.  16 segments x 2 rings, and every
                                         segment maps the SAME 64x63 UV patch at its own world
                                         rotation: UV overlap x23.6, and the per-face rotation of the
                                         u-axis is UNIFORMLY distributed (resultant R = 0.000).  A
                                         figure drawn here appears 16 times, each turned -- which is
                                         precisely the column-576 shredding cast 2b measured.
  geom 0x2ed7c  CLUT (96,244)   10 GT4   THE GROUND ARC BAND.  Ten quads tile ONE 255 x 63 strip with
                                         matched u breakpoints (0/25/51/76/101/127/152/177/203/229/
                                         254), no repeat, overlap x1.18, and the strip wraps a
                                         semicircular band on the ground plane.  One chart, one pass,
                                         consistent orientation (R = 0.750).  A figure drawn here
                                         survives.

So the verdict is not "this cell is flat" or "this cell shreds" -- it is that the cell is SPLIT, and
the shape goes in the flat reader's half.

THE ZONES ARE DERIVED FROM THE COVERS, NEVER TYPED
---------------------------------------------------
* **zone A = strip-only** -- the halfwords 0x2ed7c reads and 0x2d344 does not.  Whatever appears here
  was drawn by the ARC BAND and by nothing else.
* **zone B = cone-only** -- the halfwords 0x2d344 reads and 0x2ed7c does not.
The two are disjoint by construction (the intersection, 1,659 halfwords, is left STOCK -- it is the
one region a reading could not attribute, so nothing is written into it).

THE FIGURES, AND WHY EACH IS THE ONE ITS SURFACE CAN CARRY
-----------------------------------------------------------
* zone A gets **bold punched WHEELS** -- ring + three radial spokes, cast 2b's bold profile.  Their
  size is not chosen: the strip's own UV<->XYZ pairs give world units per u-texel and per v-texel, and
  the wheel is stretched by exactly that ratio so it lands on the ground as a CIRCLE.  A wheel is
  the figure this tier's owner has already learned to read, and it is not translation-invariant --
  which is the whole point, because stripes are, and that is why cast 1c proved a byte path and
  nothing about shape.
* zone B gets **plain horizontal BANDS** -- the only figure a 16x-repeated patch can carry, and
  therefore the honest instrument for the reader whose UV shreds.  It is there so a null result on
  the wheels is a MEASUREMENT ("the arc band is bound but not drawn") instead of an ambiguity.

WHY PUNCH TO INDEX 0 -- AND WHY THAT IS PALETTE-INVARIANT HERE, MEASURED
-------------------------------------------------------------------------
This cell is class C: one index array read under two CLUTs.  The write value is therefore chosen as
the index whose **worst-case (maximum) luminance across BOTH views** is the lowest -- so "dark" is a
property under every palette that reads these bytes, not under the one we happened to open.  On stock
ef211 that resolves to index 0, and the two views disagree interestingly:

    pal.s0.x80_y244.e16  (the editable key, the cone)   idx 0 = 0x8022, L = 9.5 of a 134.3 peak
    pal.s0.x96_y244.e16  (the alternate view, the arc)  idx 0 = 0x0000  -- the TRUE CUTOUT, L = 0.0

so the punch is a genuine transparent hole on the surface the shape verdict rides on, and the darkest
live entry (7% of peak) on the other.  Under additive compositing both read as absence, which is the
one channel casts 1a/1b/2 proved legible on this container.  Note the consequence for the kit's
cutout gate: ``transparent_indices`` on the EDITABLE key finds none (that row has no 0x0000 word), so
``cutout_punch`` and ``cutout_fill`` are 0 and no ``acknowledge_cutout_reshape`` is owed -- while
under the alternate view the same write does create cutout texels.  That asymmetry is disclosed here
rather than discovered later.

THE COVER RASTERISER IS OVERRIDDEN, AND THE REASON IS A MEASURED KIT DEFECT
----------------------------------------------------------------------------
``repaint._face_polys`` fans a quad ``(0,1,2) + (0,2,3)`` on the documented assumption that the four
corners are perimeter-ordered.  ef211's scenery GT4s are **Z-ordered** (the PSX GPU's own quad order:
v0v1v2 + v1v2v3), and the perimeter fan on a Z-ordered quad is a BOWTIE -- its two triangles carry
OPPOSITE winding, double-cover one half and leave a wedge uncovered.  Re-derived here, per run, so
this is a measurement and not a claim: :func:`quad_order_evidence` reports the winding of both fans on
every quad, and the two fans' covers are both counted.  On 0x2ed7c the perimeter fan reports 3,332
halfwords where the Z fan reports 4,032 -- **700 halfwords, 17.4%, of live art the kit calls dead**.
This generator masks with the Z fan, which is why the kit's own build will report a non-zero
"outside the cover" count for this target: that number is the defect, not a stray edit, and the spec
quotes it.  Nothing here changes the kit; the fix is a separate change with its own re-measurement of
every published cover count.

PROVENANCE
----------
No stock byte run appears in this file.  The container is read at run time; every destination goes
through :func:`ff9mapkit.summons.export.assert_local_only`.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "ff9mapkit"))

from ff9mapkit.summons import container as EC                     # noqa: E402
from ff9mapkit.summons import export as EX                        # noqa: E402
from ff9mapkit.summons import repaint as RP                       # noqa: E402
from ff9mapkit.summons import reskin as RS                        # noqa: E402
from ff9mapkit.summons import texture as KT                       # noqa: E402

EFFECT = 211
CELL = "cell.s0.x640_y256"
DEFAULT_ROOT = r"C:\gd\SCRATCH\summon-format\repaint-w6b\ef211-pool"

#: THE PROFILE, and the ONE deliberate departure from cast 2b.
#: cast 2b ran stroke ``0.30 R`` / duty ``0.72`` because its surface SHREDDED and the figure had to
#: reach stripe-class coverage just to register as erosion.  At that weight the ring band spans
#: ``d in [0.56, 1.04] R`` and the spokes fill most of what is left, so the figure renders as a DISC
#: with notches -- which is exactly the shape a shape verdict must not rest on ("a wheel, not a disc"
#: is the phrase, and a disc answers nothing a blob would not).  This cast's whole premise is that
#: its surface does NOT shred, so the weight is spent on FORM instead of on coverage: a stroke that
#: leaves an open hub and three open sectors, at ~14% of the wheel's diameter -- thick enough to
#: survive the on-screen size (measured below in world units, not guessed), thin enough that ring,
#: spokes and holes are three distinguishable things.  Total removed area is kept in cast 2b's band
#: by zone B's control bands, not by fattening the figure.
RING_R = 0.80
BOLD_STROKE_OF_RING = 0.22
SPOKES = 3
BOLD_SPOKE_DUTY = 0.76
#: the wheel leaves this many texel rows of the band untouched at top and bottom, so the ring's
#: extremes do not ride the band's own faded edge.
V_MARGIN = 2
#: texels of clear air between neighbouring wheels (they must read as SEPARATE figures).
WHEEL_GAP = 4
#: zone B's bands: how many, how tall (byte-rows of the cell), as a fraction of the zone.
BANDS = 2
BAND_ROWS = 12


# ------------------------------------------------------------------ the corrected quad triangulation
def z_polys(pts: Sequence[Tuple[int, int]]) -> List[Tuple]:
    """The PSX quad fan: ``(0,1,2) + (1,3,2)``.  A GT4/FT4 record's four corners are the GPU's own
    Z-order, not a perimeter walk, so this is the fan that tiles the face instead of bowtie-ing it."""
    if len(pts) == 4:
        return [(pts[0], pts[1], pts[2]), (pts[1], pts[3], pts[2])]
    return [tuple(pts[:3])]


def _wind(t) -> float:
    (x0, y0), (x1, y1), (x2, y2) = t
    return (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)


def quad_order_evidence(faces: Sequence[Sequence[Tuple[int, int]]]) -> Dict[str, int]:
    """Which fan keeps a quad's two triangles on the SAME winding -- the discriminator, per run.

    A correctly-ordered fan cannot flip winding inside one planar face; a bowtie always does.  Both
    fans are scored on every quad so the answer is a count, not an assertion.
    """
    z_ok = p_ok = quads = 0
    for pts in faces:
        if len(pts) != 4:
            continue
        quads += 1
        zt = [(pts[0], pts[1], pts[2]), (pts[1], pts[3], pts[2])]
        pt = [(pts[0], pts[1], pts[2]), (pts[0], pts[2], pts[3])]
        if _wind(zt[0]) * _wind(zt[1]) > 0:
            z_ok += 1
        if _wind(pt[0]) * _wind(pt[1]) > 0:
            p_ok += 1
    return {"quads": quads, "z_consistent": z_ok, "perimeter_consistent": p_ok}


def _fill(cover: Set[int], tri, page_x: int, page_y: int, per: int, cell) -> None:
    (x0, y0), (x1, y1), (x2, y2) = [(p[0] + 0.5, p[1] + 0.5) for p in tri]
    d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if d == 0:
        return
    for py in range(int(min(y0, y1, y2)), int(max(y0, y1, y2)) + 1):
        cy = py + 0.5
        for px in range(int(min(x0, x1, x2)), int(max(x0, x1, x2)) + 1):
            cx = px + 0.5
            a = ((y1 - y2) * (cx - x2) + (x2 - x1) * (cy - y2)) / d
            bb = ((y2 - y0) * (cx - x2) + (x0 - x2) * (cy - y2)) / d
            if a >= -1e-9 and bb >= -1e-9 and (1.0 - a - bb) >= -1e-9:
                hx, vy = page_x + px // per, page_y + py
                if (hx // RS.PAGE_CELL_W) * RS.PAGE_CELL_W == cell[0] and \
                   (vy // RP.CELL_LINES) * RP.CELL_LINES == cell[1]:
                    cover.add((vy - cell[1]) * RS.PAGE_CELL_W + (hx - cell[0]))


def reader_geometry(blob: bytes, cell: Tuple[int, int]) -> Dict[int, dict]:
    """Per so-bound reader of ``cell``: its true halfword cover, its faces, and its UV<->XYZ pairs."""
    out: Dict[int, dict] = {}
    for m in RP.bound_models(blob):
        if cell not in m.cover:
            continue
        g = next(x for x in EC.scan_geom(blob) if x.base == m.geom)
        per = KT.TEXELS_PER_HW[m.bpp]
        cover: Set[int] = set()
        faces: List[List[Tuple[int, int]]] = []
        pairs: List[Tuple[Tuple[int, int], Tuple[int, int, int]]] = []
        for mesh in g.meshes:
            vs = list(EC.vertices(blob, g, mesh))
            pool = g.base + mesh.p_uv
            for prim in EC.iter_primitives(blob, g, mesh):
                uvs = prim.get("uv")
                if not uvs:
                    continue
                pts = []
                for ui in uvs:
                    w = struct.unpack_from("<H", blob, pool + 2 * ui)[0]
                    pts.append((w & 0xFF, (w >> 8) & 0xFF))
                faces.append(pts)
                for k, vi in enumerate(prim["v"][:len(uvs)]):
                    pairs.append((pts[k], tuple(vs[vi][:3])))
                for t in z_polys(pts):
                    _fill(cover, t, m.page[0], m.page[1], per, cell)
                for (u, v) in pts:
                    hx, vy = m.page[0] + u // per, m.page[1] + v
                    if (hx // RS.PAGE_CELL_W) * RS.PAGE_CELL_W == cell[0] and \
                       (vy // RP.CELL_LINES) * RP.CELL_LINES == cell[1]:
                        cover.add((vy - cell[1]) * RS.PAGE_CELL_W + (hx - cell[0]))
        out[m.geom] = {"model": m, "cover": cover, "kit_cover": set(m.cover[cell]),
                       "faces": faces, "pairs": pairs,
                       "order": quad_order_evidence(faces)}
    return out


def world_metric(pairs: Sequence[Tuple[Tuple[int, int], Tuple[int, int, int]]]) -> Dict[str, float]:
    """World units per u-texel and per v-texel, from the model's own UV<->XYZ corner pairs.

    Every pair of corners that differs in exactly ONE of u / v contributes one sample; the answer is
    the MEDIAN, so one degenerate edge cannot set the wheel's aspect.  This is what makes the figure
    round on the ground instead of round in the texture -- the two are different by 2.1x here.
    """
    du: List[float] = []
    dv: List[float] = []
    for i in range(len(pairs)):
        (u0, v0), p0 = pairs[i]
        for j in range(i + 1, len(pairs)):
            (u1, v1), p1 = pairs[j]
            d = math.dist(p0, p1)
            if v0 == v1 and u0 != u1:
                du.append(d / abs(u1 - u0))
            elif u0 == u1 and v0 != v1:
                dv.append(d / abs(v1 - v0))
    du.sort()
    dv.sort()
    if not du or not dv:
        raise SystemExit("this reader's UV pairs do not separate u from v -- no metric derivable")
    return {"per_u": du[len(du) // 2], "per_v": dv[len(dv) // 2],
            "aspect": du[len(du) // 2] / dv[len(dv) // 2],
            "n_u": len(du), "n_v": len(dv)}


def zone_rect(cover: Set[int]) -> Tuple[int, int, int, int]:
    """``(x0, x1, y0, y1)`` in HALFWORD columns and cell lines -- the zone's own bounding box."""
    xs = sorted({h % RS.PAGE_CELL_W for h in cover})
    ys = sorted({h // RS.PAGE_CELL_W for h in cover})
    return xs[0], xs[-1], ys[0], ys[-1]


def _luma(word: int) -> float:
    r, g, b, _a = KT.bgr555_rgba(word)
    return 0.299 * r + 0.587 * g + 0.114 * b


def choose_dark(views: Sequence[Sequence[int]]) -> Tuple[int, List[float]]:
    """The index whose WORST-CASE luminance over every CLUT that reads these bytes is the lowest.

    A class-C cell is one index array under N renderings, so "dark" has to hold under all of them or
    the figure is a hole in one view and a highlight in another.  Ties break to the LOWEST index --
    stated, so determinism is a property of the rule.
    """
    n = min(len(v) for v in views)
    worst = [max(_luma(v[i]) for v in views) for i in range(n)]
    idx = min(range(n), key=lambda i: (worst[i], i))
    return idx, worst


def _wheel_texels(cx: int, cy: float, ru: int, rv: int, u0: int, u1: int, y0: int, y1: int,
                  w: int, mask: Sequence[int]) -> List[int]:
    """The texel indices ONE wheel would write, inside the zone and inside the reader's cover."""
    out: List[int] = []
    ring, half = RING_R, BOLD_STROKE_OF_RING * RING_R
    for y in range(max(y0, int(cy - rv) - 1), min(y1, int(cy + rv) + 1) + 1):
        for x in range(max(u0, cx - ru - 1), min(u1, cx + ru + 1) + 1):
            i = y * w + x
            if not mask[i]:
                continue
            dx, dy = (x - cx) / float(ru), (y - cy) / float(rv)
            d = math.hypot(dx, dy)
            th = math.atan2(dy, dx)
            if abs(d - ring) <= half or (
                    d <= ring and abs(((th * SPOKES / math.pi) % 2.0) - 1.0) > BOLD_SPOKE_DUTY):
                out.append(i)
    return out


def stamp_wheels(px: bytearray, mask: Sequence[int], w: int, zone: Tuple[int, int, int, int],
                 metric: Dict[str, float], value: int,
                 luma_of_index: Sequence[float]) -> Dict[str, object]:
    """The row of world-CIRCULAR wheels across zone A, placed where there is LIGHT TO REMOVE.

    Size is not chosen: ``rv`` is the band's own half-height less a margin, and ``ru`` is whatever
    makes the wheel round ON THE GROUND at this reader's measured ``per_u`` / ``per_v``.  Placement
    is not chosen either.  A punch is a SUBTRACTIVE mark on an additive surface, so its contrast is
    the luminance it removes; the whole necklace therefore slides along zone A to the offset that
    maximises the summed stock luminance under the figure.  A wheel stamped over texels that were
    already near-black would be a correct edit that renders as nothing -- the exact failure mode
    cast 1a paid for, in its other polarity.
    """
    hx0, hx1, y0, y1 = zone
    u0, u1 = hx0 * 4, hx1 * 4 + 3
    rv = (y1 - y0) // 2 - V_MARGIN
    ru = max(2, int(round(rv * metric["per_v"] / metric["per_u"])))
    pitch = 2 * ru + WHEEL_GAP
    n = max(1, (u1 - u0 + 1) // pitch)
    span = n * pitch
    cy = (y0 + y1) / 2.0
    best = None
    for left in range(u0, u0 + (u1 - u0 + 1 - span) + 1):
        centres = [left + pitch // 2 + k * pitch for k in range(n)]
        idx = [i for cx in centres for i in _wheel_texels(cx, cy, ru, rv, u0, u1, y0, y1, w, mask)]
        lit = sum(luma_of_index[px[i]] for i in idx)
        if best is None or lit > best[0]:
            best = (lit, left, centres, idx)
    lit, left, centres, idx = best
    mean_before = lit / max(1, len(idx))
    for i in idx:
        px[i] = value
    return {"wheels": n, "centres": centres, "cy": cy, "ru": ru, "rv": rv, "pitch": pitch,
            "left": left, "offsets_tried": (u1 - u0 + 1 - span) + 1,
            "stroke_of_ring": BOLD_STROKE_OF_RING, "spoke_duty": BOLD_SPOKE_DUTY,
            "world_w": 2 * ru * metric["per_u"], "world_h": 2 * rv * metric["per_v"],
            "world_stroke": 2 * BOLD_STROKE_OF_RING * RING_R * rv * metric["per_v"],
            "roundness": (2 * ru * metric["per_u"]) / (2 * rv * metric["per_v"]),
            "mean_luma_removed": round(mean_before, 2), "texels": len(idx)}


def stamp_bands(px: bytearray, mask: Sequence[int], w: int, zone: Tuple[int, int, int, int],
                value: int) -> Dict[str, object]:
    """Zone B's plain horizontal bands -- translation-invariant, the only figure a 16x-repeated patch
    can carry, and therefore the control that turns a null on the wheels into a measurement."""
    hx0, hx1, y0, y1 = zone
    u0, u1 = hx0 * 4, hx1 * 4 + 3
    hit = 0
    tops = []
    for k in range(BANDS):
        centre = int(y0 + (k + 0.5) * (y1 - y0 + 1) / BANDS)
        top = max(y0, min(y1 - BAND_ROWS + 1, centre - BAND_ROWS // 2))
        tops.append(top)
        for y in range(top, top + BAND_ROWS):
            for x in range(u0, u1 + 1):
                i = y * w + x
                if mask[i]:
                    px[i] = value
                    hit += 1
    return {"bands": BANDS, "rows": BAND_ROWS, "tops": tops, "texels": hit}


def generate(root: Optional[str] = None, from_path: Optional[str] = None, game=None,
             export: bool = True, no_bands: bool = False) -> Dict[str, object]:
    if from_path:
        stock = Path(from_path).read_bytes()
        source = str(from_path)
    else:
        stock, source = RS.R.read_stock_effect(EFFECT, game)

    root_p = Path(EX.assert_local_only(root or DEFAULT_ROOT))
    art = root_p / "art"
    if export:
        man = RP.export_art(stock, EFFECT, art, source=source, lane="indexed")
        art = Path(man["out_dir"])
    art.mkdir(parents=True, exist_ok=True)

    page = RP.texel_page(stock, CELL, EFFECT)
    if page.bpp != 4:
        raise SystemExit("%s is %dbpp -- this generator is the 4bpp nibble lane's" % (CELL, page.bpp))
    w, h = page.wh
    raw = stock[page.page_offset:page.page_offset + page.page_bytes]
    px0 = RP.unpack4(raw)
    # THE IDENTITY GATE, before anything is drawn: the unstamped indices must re-pack to the stock
    # bytes, or the codec is not the one this container speaks and no edit below means what it says.
    noop = RP.pack4(bytes(px0)) if hasattr(RP, "pack4") else None
    if noop is not None and noop != raw:
        raise SystemExit("NO-OP FAILED on %s: unpack4/pack4 is not byte-identical here" % CELL)

    geo = reader_geometry(stock, page.cell)
    if len(geo) != 2:
        raise SystemExit("%s has %d so-readers; this cast is written for the measured TWO"
                         % (CELL, len(geo)))
    # the CONE is the repeated-patch model (many faces, high UV overlap); the ARC is the chart.
    cone_geom = max(geo, key=lambda k: len(geo[k]["faces"]))
    arc_geom = min(geo, key=lambda k: len(geo[k]["faces"]))
    arc, cone = geo[arc_geom], geo[cone_geom]
    zoneA = arc["cover"] - cone["cover"]
    zoneB = cone["cover"] - arc["cover"]
    if not zoneA or not zoneB:
        raise SystemExit("the two readers do not partition -- zone A %d, zone B %d"
                         % (len(zoneA), len(zoneB)))

    per = KT.TEXELS_PER_HW[page.bpp]

    def texel_mask(cover: Set[int]) -> bytearray:
        mk = bytearray(w * h)
        for hw in cover:
            line, hx = divmod(hw, RS.PAGE_CELL_W)
            for k in range(per):
                mk[line * w + hx * per + k] = 1
        return mk

    mA, mB = texel_mask(zoneA), texel_mask(zoneB)
    metric = world_metric(arc["pairs"])

    # the write value, under EVERY CLUT that reads these bytes
    views, view_names = [], []
    for gk, rec in sorted(geo.items()):
        pal = RS.palette_map(stock, EFFECT).by_name(
            "pal.s0.x%d_y%d.e%d" % (rec["model"].clut_cell[0], rec["model"].clut_cell[1],
                                    rec["model"].clut_entries))
        views.append(struct.unpack_from("<%dH" % pal.entries, stock, pal.off))
        view_names.append(pal.name)
    value, worst = choose_dark(views)

    # the contrast metric the placement maximises is measured under the ARC's own view -- that is
    # the surface the shape verdict rides on, so its palette is the one whose light gets removed.
    arc_view = views[[k for k, _ in sorted(geo.items())].index(arc_geom)]
    luma_of_index = [_luma(word) for word in arc_view]

    px = bytearray(px0)
    wheels = stamp_wheels(px, mA, w, zone_rect(zoneA), metric, value, luma_of_index)
    bands = ({"bands": 0, "rows": 0, "tops": [], "texels": 0} if no_bands
             else stamp_bands(px, mB, w, zone_rect(zoneB), value))

    changed = [i for i in range(len(px0)) if px0[i] != px[i]]
    outside = sum(1 for i in changed if not (mA[i] or mB[i]))
    kit_cover = cone["kit_cover"] | arc["kit_cover"]
    kit_dead = sum(1 for i in changed if ((i // w) * RS.PAGE_CELL_W + (i % w) // per) not in kit_cover)

    words = RP.palette_words(stock, page)
    zeros = RP.transparent_indices(words)
    out_png = art / ("%s.png" % page.name)
    RP.write_indexed_png(bytes(px), words, w, h, out_png)

    return {
        "effect": EFFECT, "cell": page.name, "source": source, "root": str(root_p),
        "art": str(art), "png": str(out_png),
        "page_offset": page.page_offset, "page_bytes": page.page_bytes, "wh": [w, h],
        "bpp": page.bpp, "vram": list(page.cell),
        "palette_from": page.palette_name, "views": view_names,
        "value": value, "value_words": ["%#06x" % v[value] for v in views],
        "value_worst_luma": round(worst[value], 2),
        "value_runner_up": round(sorted(worst)[1], 2),
        "transparent_on_editable_key": list(zeros),
        "readers": {("%#x" % k): {
            "clut": list(v["model"].clut_cell), "faces": len(v["faces"]),
            "cover_z": len(v["cover"]), "cover_kit": len(v["kit_cover"]),
            "order": v["order"]} for k, v in geo.items()},
        "arc": "%#x" % arc_geom, "cone": "%#x" % cone_geom,
        "zoneA_halfwords": len(zoneA), "zoneB_halfwords": len(zoneB),
        "shared_halfwords": len(arc["cover"] & cone["cover"]),
        "zoneA_rect": list(zone_rect(zoneA)), "zoneB_rect": list(zone_rect(zoneB)),
        "metric": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in metric.items()},
        "wheels": wheels, "bands": bands,
        "changed_texels": len(changed), "outside_both_zones": outside,
        "kit_dead_texels": kit_dead,
        "figure_share_of_page": round(len(changed) / float(w * h), 4),
        "noop_identity": noop is not None and noop == raw,
    }


def report(d: Dict[str, object]) -> List[str]:
    W = d["wheels"]
    B = d["bands"]
    tot = d["wh"][0] * d["wh"][1]
    return [
        "ef%03d %s  <- %s" % (d["effect"], d["cell"], d["source"]),
        "  cell            %#08x .. %#08x   VRAM %s   %dx%d @ %dbpp   NO-OP identity %s"
        % (d["page_offset"], d["page_offset"] + d["page_bytes"], d["vram"], d["wh"][0], d["wh"][1],
           d["bpp"], "OK" if d["noop_identity"] else "NOT CHECKED"),
        "  readers         " + " | ".join(
            "%s CLUT %s faces %d cover z-fan %d vs kit %d (quads %d: z-consistent %d, "
            "perimeter-consistent %d)"
            % (k, v["clut"], v["faces"], v["cover_z"], v["cover_kit"], v["order"]["quads"],
               v["order"]["z_consistent"], v["order"]["perimeter_consistent"])
            for k, v in sorted(d["readers"].items())),
        "  ARC (the chart) %s      CONE (the repeated patch) %s" % (d["arc"], d["cone"]),
        "  zones           A(arc-only) %d hw %s | B(cone-only) %d hw %s | SHARED left stock %d hw"
        % (d["zoneA_halfwords"], d["zoneA_rect"], d["zoneB_halfwords"], d["zoneB_rect"],
           d["shared_halfwords"]),
        "  world metric    %.2f units per u-texel, %.2f per v-texel -> texture aspect %.2f : 1 "
        "(from %d u-pairs / %d v-pairs)"
        % (d["metric"]["per_u"], d["metric"]["per_v"], d["metric"]["aspect"],
           d["metric"]["n_u"], d["metric"]["n_v"]),
        "  ink             index %d -- the DARKEST under EVERY view: worst-case L=%.2f "
        "(runner-up %.2f); words %s across %s"
        % (d["value"], d["value_worst_luma"], d["value_runner_up"],
           ", ".join(d["value_words"]), ", ".join(d["views"])),
        "                  transparent indices on the EDITABLE key %s -> the kit's cutout gate sees "
        "punch 0 / fill 0 and no acknowledgement is owed"
        % (list(d["transparent_on_editable_key"]) or "NONE"),
        "  WHEELS          %d, ru %d rv %d pitch %d at u %s, cy %.1f -> %.0f x %.0f world units "
        "(roundness %.2f), rim %.0f units = %.0f%% of the diameter, %d texels"
        % (W["wheels"], W["ru"], W["rv"], W["pitch"], W["centres"], W["cy"],
           W["world_w"], W["world_h"], W["roundness"], W["world_stroke"],
           100.0 * W["world_stroke"] / W["world_h"], W["texels"]),
        "                  profile ring %.2f R, stroke %.2f of the ring, %d spokes at duty %.2f; "
        "placement = the brightest of %d offsets (mean stock L removed %.2f)"
        % (RING_R, W["stroke_of_ring"], SPOKES, W["spoke_duty"], W["offsets_tried"],
           W["mean_luma_removed"]),
        "  BANDS           %d x %d rows at y %s, %d texels"
        % (B["bands"], B["rows"], B["tops"], B["texels"]),
        "  MEASURED        %d texels changed (%.1f%% of the page); outside BOTH zones %d; "
        "texels the KIT's perimeter fan calls dead %d (the defect, quantified)"
        % (d["changed_texels"], 100.0 * d["changed_texels"] / tot, d["outside_both_zones"],
           d["kit_dead_texels"]),
        "  wrote           %s" % d["png"],
    ]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="staging root (default %s)" % DEFAULT_ROOT)
    ap.add_argument("--from", dest="from_path", default=None,
                    help="read this container FILE instead of the install")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--no-bands", action="store_true",
                    help="zone A only -- the wheels with no cone-side control")
    ap.add_argument("--json", default=None, help="also write the full derivation here")
    ap.add_argument("--game", default=None)
    a = ap.parse_args(argv)
    d = generate(a.root, a.from_path, a.game, export=not a.no_export, no_bands=a.no_bands)
    print("\n".join(report(d)))
    if a.json:
        Path(a.json).write_text(json.dumps(d, indent=1, default=str), encoding="utf-8")
        print("  derivation      %s" % a.json)
    # THE TWO NUMBERS THE CLAIM RESTS ON: nothing may land outside the two attributed zones (the
    # shared region has to stay stock or the cast cannot say which reader answered), and the no-op
    # identity has to have been checked.
    return 0 if (d["outside_both_zones"] == 0 and d["noop_identity"]) else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
