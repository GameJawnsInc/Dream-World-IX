r"""THE SUMMON TEXEL REPAINT (lever #2): repaint a STOCK summon's own texture pages in place.

    ff9mapkit summon-reskin export-art --ef 227          # decode every creature page to a paintable PNG
    ff9mapkit summon-reskin plan   bahamut_emblem.toml   # resolve every texel target + run every gate
    ff9mapkit summon-reskin build  bahamut_emblem.toml   # stage the patched container + scripts + previews
    ff9mapkit summon-reskin verify bahamut_emblem.toml   # re-check what is staged, AS BYTES

or as an API::

    from ff9mapkit.summons import repaint
    spec = repaint.load_spec("bahamut_emblem.toml")
    b    = repaint.build(spec, "bahamut_emblem.toml")    # reads the install, splices the pages
    b.check = repaint.self_check(b)                      # every gate, on OUR bytes
    repaint.stage(b)                                     # override + revert scripts + previews

WHAT THIS IS, AND WHY IT IS A SIBLING RATHER THAN MORE ``reskin.py``
---------------------------------------------------------------------
:mod:`ff9mapkit.summons.reskin` is lever #1 -- a per-index COLOUR FUNCTION over the container's own
CLUTs. It can rotate a hue; it structurally cannot move a texel from one index to another, so it can
never change a shape, an edge or a silhouette. This module is lever #2: it rewrites the INDICES.
``reskin.py``'s own docstring earmarks itself as lever-#1-only and says the repaint "is a different
lane and this module refuses to do it" -- honoured here. What ``reskin.py`` already DERIVES is
consumed rather than re-derived (``creature_pages``, ``PaletteMap``, ``texanim_region``, ``_regions``,
``scenery_pages``/``id9_pages`` for the collision census), exactly the way ``reskin.py`` itself
consumes :mod:`~ff9mapkit.summons.container`.

THE SCOPE OF THIS RUNG (W6a) -- CREATURE PAGES, INDEXED LANE, AND NOTHING ELSE
------------------------------------------------------------------------------
The id-4 creature pages are the one texel class that is measurably free of every known hazard, so
they are the whole of W6a and every other class REFUSES with its reason named
(:data:`W6B_REASON`) rather than being half-supported:

* **single-writer, 24/24.** Re-measured over the corpus this rung: 24 decodable creature packages,
  93 pages, **0 VRAM-cell collisions and 0 file-span collisions** against every scenery page rect and
  every id-9 alternate block. The creature owns VRAM ``x`` in ``[192, 384)`` (measured: every one of
  the 93 pages sits at x 192/256/320) and nothing else in the container writes there. That is
  CHECKED per target (:func:`_gate_collisions`), not assumed -- six corpus effects place id-9 slots
  at x = 320, precisely the ladder rungs their own ``partCount`` leaves unused, so the near miss is
  real and only a derived test can tell it from a hit.
* **uniform 8bpp.** ``texture_check`` reports the 128x128 / ``partCount * 0x4000`` layout decodable
  on 24/24. A 4bpp or 15bpp-direct page is a different codec and is refused.
* **one chunk's worth of writers.** The corpus's whole multi-writer page census is 34 cells in 5
  containers (ef225/227/251/381/447) and every one of them is SCENERY. The CO-TRANSFORM LAW is the
  multi-chunk law, and creature pages are outside it -- but the gate tests the cells, not the chunk
  count, because ef227 IS a two-chunk container and a chunk-count refusal would refuse the one
  effect this rung is proven on.

THE FORMAT OF RECORD: AN INDEXED (P-MODE) PNG, NOT RGBA
-------------------------------------------------------
Measured over all 93 stock pages: ``decode -> P-mode PNG (palette = the CLUT row, tRNS = entry 0) ->
reload -> indices`` is **byte-identical 93/93**. The RGBA lane is not: 8.31% of the corpus's palette
entries are duplicates of the full 16-bit word, so an identity RGBA round-trip already flips 1,844 of
16,384 texels on ef251 part 0 and byte-identity -- and with it the gate this whole lane rests on --
simply dies. So the indexed lane is the format of record, the PNG's palette is DISPLAY ONLY (the
container remains the palette authority and this lane writes zero CLUT bytes), and RGBA / quantize /
mint-CLUT are W6b and refuse by name.

THE CUTOUT LAW, AT THE TEXEL LEVEL
-----------------------------------
``texture.bgr555_rgba`` maps ``0x0000 -> (0,0,0,0)``: transparency is by VALUE, and the corpus puts
exactly one such entry in every row, always at index 0 (93/93; it is the only STP-clear entry in the
whole corpus, 93 of 23,808). A texel edit therefore controls the SILHOUETTE, which a palette edit
never could. So: a texel whose index crosses the transparent-entry boundary is counted **in both
directions** -- ``punch`` (opaque -> hole) and ``fill`` (hole -> opaque) -- and any non-zero count
REFUSES unless the row says ``acknowledge_cutout_reshape = true``. That is the one escape hatch this
lane needs and the CLUT lane does not: reshaping a torn wing edge is a legitimate texel-level move.
The transparent index set is DERIVED from the active palette, not assumed to be ``{0}``.

THE DEAD PAD -- REPORTED, NEVER FATAL
--------------------------------------
Only **64.0%** of the corpus's creature texels are sampled by any face (975,202 of 1,523,712); the
rest is pad. And >99.6% of a page's dead texels form ONE border-connected margin, so "paint inside
the island" is a complete instruction -- which is why every export ships a ``<name>.coverage.png``
whose green hatch is the never-sampled region, rasterised from the container's OWN uv pools
(:func:`coverage`). It cannot be derived from the pixels: ef227's dominant pad INDEX differs per part
(138/111/109/164/80/104) while all six decode to the same word, and the pad index also occurs inside
the sampled island. Editing dead texels is INERT, exactly the way a hue rotation is inert on
``reskin.py``'s achromatic cloud bands -- so it is reported with its count and never fails a build.

THE REGION PARTITION IS INVERTED, NOT COPIED
---------------------------------------------
``reskin.py``'s ``_regions`` gates "the id-4 header + all N texel pages" byte-identical -- correct for
a CLUT-only lane and exactly backwards for this one. It takes a ``partition`` parameter now: this
lane licenses ``[tex_file_offset, +tex_bytes)`` and gates the id-4 header, the CLUT strip, the sector
pad, sector 0, every id-3 program, the id-5 model image (which is where the texanim table and the
UVs live), every camera block and every GEOM block. One function, two partitions -- never a second
copy that drifts.

COMPOSITION WITH THE CLUT LANE
-------------------------------
The two levers are byte-disjoint by construction (palettes at ``[0x621a0, 0x62da0)`` on ef227, texel
pages at ``[0x4a1a0, 0x621a0)``) and the kit PROVES it rather than asserting it: this build's
changed-offset set is intersected with a rebuilt sibling's. Two composition routes, one artifact:

* **one spec, both tables** -- a spec carrying ``[[reskin.target]]`` AND ``[[reskin.texel]]`` builds
  the CLUT lane first and hands its patched bytes to this one (the CLI's own path);
* **``[reskin.orthogonality] reskin = "..."`` + ``compose = true``** -- a texel-only spec composes on
  a SHIPPED reskin spec's rebuild, so the palette half keeps exactly one source of truth instead of
  being copied into a second file that can drift.

Either way it is ONE container, ONE ledger and ONE revert, and the composed delta is gated disjoint.

HOT RELOAD
----------
Stronger here than for the CLUT lane: ``SFX.Play`` re-reads the container from disc every cast AND
calls ``PSXTextureMgr.Reset()`` unconditionally, and a PAGE upload is itself the event that
invalidates the decoded-texture cache. Recast to see it -- no ``~`` reload, no warp, no relaunch.

PROVENANCE
----------
The container is read at RUN TIME from the user's own install under a sha256 drift guard. **Every
exported page PNG is decoded Square-Enix content**: :func:`export_art` puts every destination through
:func:`ff9mapkit.summons.export.assert_local_only` (a git checkout, a ``StreamingAssets`` tree and
the resolved install are all refused, with no ``--force``), and the manifest carries the stock sha256
so a repaint can never be packed against a container it was not exported from. This module carries
offsets, counts and VRAM coordinates -- no run of stock bytes and no stock palette.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import struct
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from . import container as EC
from . import export
from . import rescore as R
from . import reskin as RS
from . import texture as KT
from .ledger import Ledger

__all__ = [
    "RepaintError", "W6B_REASON",
    "MOD_SUBPATH", "STAGING_BASE", "staging_root", "CREATURE_VRAM_X", "ART_MANIFEST",
    "TexelPage", "creature_texel_pages", "texel_page", "other_page_writers",
    "Coverage", "coverage", "coverage_mask", "border_flood",
    "palette_words", "transparent_indices", "png_palette",
    "write_indexed_png", "read_indexed_png", "write_coverage_png",
    "export_art", "scaffold_text",
    "TexelTarget", "TexelBuild", "load_spec", "build",
    "Gate", "SelfCheck", "self_check", "ORTH_REBUILDERS",
    "render_previews", "stage", "verify", "modfilelist_refusal",
    "describe", "derivation_lines", "check_lines",
]


class RepaintError(RuntimeError):
    """A refusal from the texel lane. A refusal is a RESULT of this tool, never an exception to hide."""


def _ack_bool(d: dict, key: str, where: str) -> bool:
    """A safety acknowledgement must be a LITERAL BOOLEAN -- W5's own minted law, re-stated here so a
    texel refusal raises a texel error. ``acknowledge_cutout_reshape = "false"`` must REFUSE, never
    arm: an acknowledgement is stated, never inferred from a truthy string."""
    v = d.get(key, False)
    if not isinstance(v, bool):
        raise RepaintError("%s: %s must be a BOOLEAN (true/false), not %r.  A safety acknowledgement "
                           "must be stated, never inferred from a truthy string." % (where, key, v))
    return v


#: THE W6b REASON, quoted verbatim by every out-of-scope refusal so a report line names the rung that
#: owns the surface instead of reading like a bug. Each clause is a MEASURED hazard, not a worry:
#: co-transform (34 multi-writer page cells in 5 containers, 0 of 156 writer pairs byte-identical),
#: same-bytes-two-bindings (ef211's col 640 shares 1,659 halfwords between two 4bpp bindings with
#: DIFFERENT palettes -- a depth-only test misses it), u-spill (41 of 316 so-bound models sample past
#: their own column, sometimes into a different resource) and 15bpp-direct (24 bindings over 12
#: effects, no CLUT to index against at all).
W6B_REASON = ("the scenery texel lane is W6b: co-transform / same-bytes-two-bindings / u-spill / "
              "15bpp unhandled")

#: the on-disc override lane, shared with both sibling lanes (extensionless -- ``LoadFromDisc`` reads
#: the raw path, so ``ef227.bytes`` would never be found).
MOD_SUBPATH = R.MOD_SUBPATH

#: THE STAGING BASE -- a per-effect directory lands under it, and it is re-checked through
#: :func:`ff9mapkit.summons.export.assert_local_only` every time it is used as a default. Distinct
#: from the reskin and rescore bases on purpose: a composed build stages a DIFFERENT container from a
#: plain reskin of the same effect, and two lanes sharing one root would have them overwrite each
#: other's ledger -- and the ledger is the artifact whose loss is unrecoverable.
STAGING_BASE = export.DEFAULT_OUT_DIR / "repaint"

#: the VRAM ``x`` band (in halfwords) the creature owns outright. MEASURED, not assumed: all 93 stock
#: creature pages sit at x 192, 256 or 320, and no scenery rect or id-9 block in the corpus declares a
#: cell inside the band. It is a DISCLOSURE used in refusal text; the actual gate is the per-target
#: cell/span intersection in :func:`_gate_collisions`, because a band test cannot see a collision that
#: a future container puts inside the band.
CREATURE_VRAM_X = (192, 384)

#: the sidecar every export writes and every import re-reads as a drift guard.
ART_MANIFEST = "art.manifest.json"

#: the scaffold an export drops beside the PNGs: a fully guarded, pre-seeded-OFF texel spec.
SCAFFOLD_NAME = "texel.scaffold.toml"


def staging_root(effect: int, root=None) -> str:
    """The per-effect staging root: ``<root or STAGING_BASE>/ef###``.

    PER EFFECT for the same reason ``reskin.staging_root`` is: with one root for every effect a second
    summon staged in the same session silently overwrites the first one's container, previews,
    manifest and revert script.
    """
    return os.path.join(str(root or STAGING_BASE), "ef%03d" % int(effect))


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ============================================================ (1) THE PAGE MAP -- all derived
@dataclass(frozen=True)
class TexelPage:
    """One addressable texel page: where its bytes are, what shape they decode to, and which CLUT row
    colours them. Every field is DERIVED from the container's own id-4 header through the kit's
    shipped decoder -- a span derived from a header nobody read is a guess."""
    name: str                    # "tex.part0" -- the texel namespace, deliberately not the CLUT one
    index: int
    page_offset: int
    page_bytes: int
    w: int
    h: int
    bpp: int
    clut_offset: int
    clut_entries: int
    tpage: int
    clut: int
    v_offset: int
    vram: Tuple[int, int]
    palette_name: str            # the CLUT lane's own name for the row this page indexes into

    @property
    def wh(self) -> Tuple[int, int]:
        return (self.w, self.h)


def creature_texel_pages(blob: bytes) -> List[TexelPage]:
    """Every creature page of one container, or ``[]`` when it carries no decodable creature package.

    Consumes :func:`ff9mapkit.summons.texture.texture_check` rather than re-deriving the layout: the
    ``partCount * 0x4000`` / ``clutRows * 0x200`` / 8bpp laws are corpus-proven there, and a second
    implementation of them here would be a second thing to keep true.
    """
    mp = EC.creature_package(blob)
    if mp is None:
        return []
    chk = KT.texture_check(blob, mp)
    if not chk["decodable"]:
        return []
    out: List[TexelPage] = []
    for p in chk["parts"]:
        out.append(TexelPage(
            name="tex.part%d" % p.index, index=p.index, page_offset=p.page_offset,
            page_bytes=KT.PAGE_BYTES, w=KT.PAGE_W, h=KT.PAGE_H, bpp=8,
            clut_offset=p.clut_offset, clut_entries=KT.PALETTE_LEN, tpage=p.tpage, clut=p.clut,
            v_offset=p.v_offset, vram=p.vram, palette_name="creature.part%d" % p.index))
    return out


def creature_refusal(blob: bytes) -> str:
    """Why this container has no addressable creature page, in the author's terms (``""`` if it has)."""
    mp = EC.creature_package(blob)
    if mp is None:
        return ("this container declares no id-4 + id-5 creature package (348 of the corpus's 372 do "
                "not) -- there is no creature page to repaint.  %s" % W6B_REASON)
    chk = KT.texture_check(blob, mp)
    if not chk["decodable"]:
        return ("this container's creature texture block is not the 8bpp 128x128 page layout:\n  - "
                + "\n  - ".join(chk["reasons"]) + "\n  %s" % W6B_REASON)
    return ""


def texel_page(blob: bytes, name: str) -> TexelPage:
    """Resolve a spec-declared texel name, or REFUSE with the whole addressable set named.

    A ``page.*`` / ``id9.*`` style name resolves to nothing here on purpose: the scenery texel lane is
    W6b, and a name that silently matched nothing would be a build that did nothing while reporting
    success -- the exact silent failure this lane cannot afford.
    """
    pages = creature_texel_pages(blob)
    for p in pages:
        if p.name == name:
            return p
    why = creature_refusal(blob)
    if why:
        raise RepaintError("no texel page named %r -- %s" % (name, why))
    raise RepaintError(
        "no texel page named %r -- this container declares %s.\nOnly the id-4 CREATURE pages are "
        "addressable in this rung; %s."
        % (name, ", ".join(p.name for p in pages), W6B_REASON))


def other_page_writers(blob: bytes) -> Dict[Tuple[int, int], List[Tuple[str, int, int]]]:
    """``{(vram x, vram y): [(source, file offset, nbytes)]}`` for every NON-creature page writer.

    Both streamed classes, from ``reskin.py``'s own derivations: the id-0 page-rect stream
    (:func:`ff9mapkit.summons.reskin.scenery_pages`) and the id-9 alternate blocks
    (:func:`~ff9mapkit.summons.reskin.id9_pages`). An ``h == 256`` rect is SPLIT into the two stacked
    128-line cells the engine actually uploads -- collapsing it into one entry would make the lower
    cell unaddressable and therefore invisible to the collision gate.
    """
    out: Dict[Tuple[int, int], List[Tuple[str, int, int]]] = {}
    for _key, r in RS.scenery_pages(blob).items():
        n = max(1, r.h // 128)
        for k in range(n):
            out.setdefault((r.x, r.y + 128 * k), []).append(
                ("%s id-0 page rect" % r.source, r.off + k * KT.PAGE_BYTES, KT.PAGE_BYTES))
    for _key, rects in RS.id9_pages(blob).items():
        for r in rects:
            out.setdefault((r.x, r.y), []).append(("%s alternate block" % r.source, r.off, r.nbytes))
    return out


# ============================================================ (2) THE UV COVERAGE RASTERISER
def _fill_tri(mask: bytearray, w: int, h: int, tri) -> None:
    """Mark every texel whose CENTRE ``(x+0.5, y+0.5)`` lies inside the triangle."""
    (x0, y0), (x1, y1), (x2, y2) = tri
    ymin = max(0, int(min(y0, y1, y2)))
    ymax = min(h - 1, int(max(y0, y1, y2)) + 1)
    xmin = max(0, int(min(x0, x1, x2)))
    xmax = min(w - 1, int(max(x0, x1, x2)) + 1)
    d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if d == 0:
        return
    for py in range(ymin, ymax + 1):
        cy = py + 0.5
        for px in range(xmin, xmax + 1):
            cx = px + 0.5
            a = ((y1 - y2) * (cx - x2) + (x2 - x1) * (cy - y2)) / d
            bb = ((y2 - y0) * (cx - x2) + (x0 - x2) * (cy - y2)) / d
            c = 1.0 - a - bb
            if a >= -1e-9 and bb >= -1e-9 and c >= -1e-9:
                mask[py * w + px] = 1


def _face_polys(pts):
    """UV corner list -> triangles. A quad's four corners are perimeter-ordered, so it fans
    ``(0,1,2) + (0,2,3)`` -- the same triangulation ``summons.build._mesh_tris`` emits."""
    if len(pts) == 4:
        return [(pts[0], pts[1], pts[2]), (pts[0], pts[2], pts[3])]
    return [(pts[0], pts[1], pts[2])]


def coverage_mask(blob: bytes, part_index: int, *, page_w: int = KT.PAGE_W,
                  page_h: int = KT.PAGE_H) -> Tuple[bytearray, dict]:
    """The per-texel SAMPLED mask for one creature part, rasterised from the container's own uv pools.

    A UV-pool entry is ``u16 == u | v << 8`` (the same reading
    :func:`ff9mapkit.summons.texture.uv_texcoord` and ``summons.build._mesh_uvs`` use); ``v`` is used
    raw because the V-offset bake and the block's own VRAM placement cancel (measured: every stock
    part's ``v`` lands in ``[0, 127]``).

    Polygon fill at texel centres, then the CORNERS are OR-ed in. The corner-OR is not a nicety: a
    one-texel-thin face has no centre inside it at all, so a pure centre test would report its texels
    dead and the overlay would tell a painter to leave live geometry alone.
    """
    mask = bytearray(page_w * page_h)
    mp = EC.creature_package(blob)
    if mp is None:
        raise RepaintError("no creature package -- nothing to rasterise")
    g = EC.creature_geom(blob, mp)
    nf = 0
    umin = vmin = 1 << 30
    umax = vmax = -1
    corners: Set[int] = set()
    for mesh in g.meshes:
        pool = g.base + mesh.p_uv
        for prim in EC.iter_primitives(blob, g, mesh):
            if not prim.get("uv") or prim.get("part") != part_index:
                continue
            nf += 1
            pts = []
            for ui in prim["uv"]:
                word = struct.unpack_from("<H", blob, pool + 2 * ui)[0]
                u, v = word & 0xFF, (word >> 8) & 0xFF
                umin, umax = min(umin, u), max(umax, u)
                vmin, vmax = min(vmin, v), max(vmax, v)
                if 0 <= u < page_w and 0 <= v < page_h:
                    corners.add(v * page_w + u)
                pts.append((u + 0.5, v + 0.5))
            for t in _face_polys(pts):
                _fill_tri(mask, page_w, page_h, t)
    for i in corners:
        mask[i] = 1
    return mask, {"faces": nf, "u": (umin, umax) if nf else (0, 0),
                  "v": (vmin, vmax) if nf else (0, 0)}


def border_flood(mask: Sequence[int], w: int, h: int) -> bytearray:
    """Dead texels reachable from the page border THROUGH dead texels -- i.e. the outer pad.

    Whatever is dead and NOT in this set is an interior hole, which is the one case a painter has to
    be told about differently: a hole is enclosed by live geometry, so paint that lands in it is still
    invisible but sits in the middle of the picture rather than outside it.
    """
    seen = bytearray(w * h)
    stack: List[int] = []
    for x in range(w):
        for y in (0, h - 1):
            i = y * w + x
            if not mask[i] and not seen[i]:
                seen[i] = 1
                stack.append(i)
    for y in range(h):
        for x in (0, w - 1):
            i = y * w + x
            if not mask[i] and not seen[i]:
                seen[i] = 1
                stack.append(i)
    while stack:
        i = stack.pop()
        x, y = i % w, i // w
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < w and 0 <= yy < h:
                j = yy * w + xx
                if not mask[j] and not seen[j]:
                    seen[j] = 1
                    stack.append(j)
    return seen


@dataclass
class Coverage:
    """One page's sampled/dead census. ``available`` False is an honest verdict, not a failure: a
    container whose GEOM will not parse still has repaintable pages, it just cannot be told which
    texels are live -- so the dead-texel report says UNAVAILABLE instead of reporting zero."""
    available: bool
    reason: str = ""
    mask: Optional[bytearray] = None
    covered: int = 0
    dead: int = 0
    faces: int = 0
    interior_holes: int = 0
    u_range: Tuple[int, int] = (0, 0)
    v_range: Tuple[int, int] = (0, 0)
    total: int = KT.PAGE_W * KT.PAGE_H

    @property
    def covered_fraction(self) -> float:
        return (self.covered / self.total) if self.total else 0.0


def coverage(blob: bytes, part_index: int, *, holes: bool = True) -> Coverage:
    """:func:`coverage_mask` plus the pad/hole split, with every failure turned into a verdict."""
    try:
        mask, st = coverage_mask(blob, part_index)
    except Exception as e:                                       # geom drift / a synthetic container
        return Coverage(available=False, reason="%s: %s" % (type(e).__name__, e))
    total = len(mask)
    cov = sum(mask)
    dead = total - cov
    nholes = 0
    if holes and dead:
        pad = border_flood(mask, KT.PAGE_W, KT.PAGE_H)
        nholes = dead - sum(pad)
    return Coverage(available=True, mask=mask, covered=cov, dead=dead, faces=st["faces"],
                    interior_holes=nholes, u_range=st["u"], v_range=st["v"], total=total)


# ============================================================ (3) THE INDEXED CODEC
def palette_words(blob: bytes, page: TexelPage) -> Tuple[int, ...]:
    """The live CLUT row for one page, as raw BGR555 halfwords."""
    return struct.unpack_from("<%dH" % page.clut_entries, blob, page.clut_offset)


def transparent_indices(words: Sequence[int]) -> Tuple[int, ...]:
    """Which palette indices decode to alpha 0 -- DERIVED, never assumed to be ``{0}``.

    ``bgr555_rgba`` makes exactly one word transparent: ``0x0000``. The corpus puts exactly one such
    word in every one of its 93 rows and always at index 0, but a gate that hard-coded index 0 would
    be asserting the corpus rather than reading the palette in front of it -- and under a composed
    CLUT edit the palette in front of it is not the stock one.
    """
    return tuple(i for i, w in enumerate(words) if w == 0)


def png_palette(words: Sequence[int]) -> bytes:
    """CLUT words -> a flat 768-byte PIL palette. DISPLAY ONLY -- the container stays the palette
    authority and this lane never writes a CLUT byte, which is exactly why the import re-reads only
    the INDICES and ignores whatever palette the returning PNG carries."""
    out = bytearray(768)
    for i, w in enumerate(words[:256]):
        r, g, b, _a = KT.bgr555_rgba(w)
        out[3 * i:3 * i + 3] = bytes((r, g, b))
    return bytes(out)


def _need_pil():
    try:
        from PIL import Image                     # noqa: F401
    except ImportError as e:                      # pragma: no cover - env dependent
        raise RepaintError("the texel lane needs Pillow (py -m pip install Pillow): %s" % e)
    from PIL import Image
    return Image


def _indexed_image(px: bytes, words: Sequence[int], w: int, h: int):
    Image = _need_pil()
    im = Image.frombytes("P", (w, h), bytes(px))
    im.putpalette(png_palette(words))
    return im


def write_indexed_png(px: bytes, words: Sequence[int], w: int, h: int, path) -> str:
    """One page -> a P-mode PNG whose pixels ARE the indices and whose ``tRNS`` marks the cutout.

    This is the format of record: the 93/93 byte-identical round trip is measured on exactly this
    encoding, and a painter who works in indices cannot accidentally destroy a silhouette or invent a
    fringe index the way an RGBA editor does.
    """
    im = _indexed_image(px, words, w, h)
    zeros = transparent_indices(words)
    kw = {"transparency": zeros[0]} if zeros else {}
    im.save(str(path), **kw)
    return str(path)


def encode_indexed_png(px: bytes, words: Sequence[int], w: int, h: int) -> bytes:
    """The same encoding, to memory -- what the round-trip identity gate re-reads."""
    im = _indexed_image(px, words, w, h)
    zeros = transparent_indices(words)
    buf = io.BytesIO()
    im.save(buf, format="PNG", **({"transparency": zeros[0]} if zeros else {}))
    return buf.getvalue()


def _read_indices(fp, where: str, w: int, h: int, palette_len: int) -> bytes:
    Image = _need_pil()
    with Image.open(fp) as im:
        mode, size = im.mode, im.size
        if mode != "P":
            raise RepaintError(
                "%s re-opens as mode %r, not \"P\".  This lane's format of record is an INDEXED PNG "
                "(the pixels ARE the palette indices).  An RGBA / quantize / mint-CLUT import is "
                "W6b: measured, an identity RGBA round trip already moves 1,844 of 16,384 texels on "
                "ef251 part 0, because 8.31%% of the corpus's palette entries are duplicate words -- "
                "so byte-identity, and with it this lane's whole gate, dies.  Re-export with "
                "`summon-reskin export-art` and edit the indices.  (%s)" % (where, mode, W6B_REASON))
        if size != (w, h):
            raise RepaintError(
                "%s is %dx%d, but this page is %dx%d.  There is no rescale here on purpose: an index "
                "page has no meaningful resample (interpolating between two indices invents a third "
                "colour and can invent a cutout)." % (where, size[0], size[1], w, h))
        px = im.tobytes()
    if len(px) != w * h:                                         # pragma: no cover - PIL guarantees it
        raise RepaintError("%s decoded to %d bytes, expected %d" % (where, len(px), w * h))
    top = max(px) if px else 0
    if top >= palette_len:
        raise RepaintError(
            "%s uses palette index %d, but this page's CLUT row has only %d entries.  An index past "
            "the row samples another part's palette at run time." % (where, top, palette_len))
    return px


def read_indexed_png(path, w: int, h: int, palette_len: int) -> bytes:
    """Load an edited page back as raw indices, REFUSING anything the lane cannot honour."""
    p = Path(path)
    if not p.is_file():
        raise RepaintError("no such source image: %s" % p)
    return _read_indices(str(p), str(p), w, h, palette_len)


def _round_trip_ok(px: bytes, words: Sequence[int], w: int, h: int) -> bool:
    """THE X0-CLASS GATE, in memory: encode -> decode -> the same bytes."""
    return _read_indices(io.BytesIO(encode_indexed_png(px, words, w, h)),
                         "(in-memory round trip)", w, h, len(words)) == px


def write_coverage_png(px: bytes, words: Sequence[int], mask: Sequence[int], w: int, h: int,
                       path) -> str:
    """The paintable page with its NEVER-SAMPLED region hatched: green = outer pad, red = interior
    hole. Sampled texels render verbatim so the two images line up texel for texel."""
    Image = _need_pil()
    rgba = [KT.bgr555_rgba(x) for x in words]
    pad = border_flood(mask, w, h)
    out = []
    for i in range(w * h):
        x, y = i % w, i // w
        r, g, b, _a = rgba[px[i]]
        if mask[i]:
            out.append((r, g, b, 255))
            continue
        hatch = ((x + y) % 8) < 3
        key = (0, 255, 0) if pad[i] else (255, 0, 0)
        out.append(key + (255,) if hatch else (r // 4, g // 4, b // 4, 255))
    im = Image.new("RGBA", (w, h))
    im.putdata(out)
    im.save(str(path))
    return str(path)


# ============================================================ (4) THE EXPORT LANE
#: the export lanes this rung ships. ``rgba`` is named so it can REFUSE by name rather than not exist
#: -- an author who asks for it gets the measurement that rules it out, not a usage error.
ART_LANES = ("indexed", "rgba")


def export_art(blob: bytes, effect: int, out_dir=None, *, source: str = "", lane: str = "indexed",
               overlays: bool = True, scaffold: bool = True) -> dict:
    """Decode every addressable page to a paintable PNG + its coverage overlay + the manifest.

    Every destination goes through :func:`ff9mapkit.summons.export.assert_local_only` -- decoded pages
    are Square-Enix content, so the repo, any ``StreamingAssets`` tree and the install are refused with
    no ``--force``. The manifest records the stock sha256 and, per page, every number a
    ``[[reskin.texel]]`` guard states; :func:`build` re-reads it and refuses a pack whose container is
    not the one the art came out of.
    """
    if lane not in ART_LANES:
        raise RepaintError("unknown art lane %r -- this rung ships %s"
                           % (lane, ", ".join(ART_LANES)))
    if lane != "indexed":
        raise RepaintError(
            "the `%s` export lane is W6b and refuses rather than half-works.  MEASURED over the 93 "
            "stock creature pages: the INDEXED round trip is byte-identical 93/93, while an RGBA "
            "round trip that painted nothing at all still moves 1,844 of 16,384 texels on ef251 part "
            "0 (8.31%% of the corpus's palette entries are duplicates of the full 16-bit word, STP "
            "included) -- and the exact-recovery rate ranges 88.75%%..99.24%% per page BEFORE anyone "
            "paints.  A lane whose no-op is not a no-op cannot carry a byte-identity gate.  %s"
            % (lane, W6B_REASON))
    pages = creature_texel_pages(blob)
    if not pages:
        raise RepaintError("ef%03d exports no texel art -- %s" % (effect, creature_refusal(blob)))
    out = Path(export.assert_local_only(out_dir if out_dir else
                                        Path(staging_root(effect)) / "art"))
    out.mkdir(parents=True, exist_ok=True)
    stock_sha = _sha(blob)
    entries = []
    written: List[str] = []
    for p in pages:
        words = palette_words(blob, p)
        px = blob[p.page_offset:p.page_offset + p.page_bytes]
        png = out / ("%s.png" % p.name)
        written.append(write_indexed_png(px, words, p.w, p.h, png))
        cov = coverage(blob, p.index) if overlays else Coverage(False, "overlays disabled")
        cov_png = ""
        if cov.available and overlays:
            cov_png = write_coverage_png(px, words, cov.mask, p.w, p.h,
                                         out / ("%s.coverage.png" % p.name))
            written.append(cov_png)
        zeros = transparent_indices(words)
        entries.append({
            "name": p.name, "index": p.index, "png": os.path.basename(str(png)),
            "coverage_png": os.path.basename(cov_png) if cov_png else "",
            "page_offset": p.page_offset, "page_bytes": p.page_bytes, "wh": [p.w, p.h],
            "bpp": p.bpp, "clut_offset": p.clut_offset, "clut_entries": p.clut_entries,
            "palette_name": p.palette_name, "tpage": p.tpage, "clut": p.clut,
            "v_offset": p.v_offset, "vram": list(p.vram),
            "covered_texels": cov.covered if cov.available else None,
            "dead_texels": cov.dead if cov.available else None,
            "interior_holes": cov.interior_holes if cov.available else None,
            "coverage_available": cov.available,
            "coverage_reason": cov.reason,
            "faces": cov.faces if cov.available else None,
            "distinct_indices": len(set(px)),
            "transparent_indices": list(zeros),
            "index0_texels": sum(1 for x in px if x in zeros),
            "page_sha256": _sha(px),
        })
    man = {"tool": "ff9mapkit summon-reskin export-art", "lane": lane, "effect": int(effect),
           "stock_sha256": stock_sha, "source": source or "(caller-supplied bytes)",
           "container_bytes": len(blob), "parts": entries}
    from .. import fsutil
    mpath = out / ART_MANIFEST
    fsutil.atomic_write_text(mpath, json.dumps(man, indent=2), encoding="utf-8", newline="\n")
    written.append(str(mpath))
    if scaffold:
        spath = out / SCAFFOLD_NAME
        fsutil.atomic_write_text(spath, scaffold_text(effect, stock_sha, entries),
                                 encoding="utf-8", newline="\n")
        written.append(str(spath))
    man["out_dir"] = str(out)
    man["files"] = written
    return man


def scaffold_text(effect: int, stock_sha: str, entries: Sequence[dict]) -> str:
    """A COMPLETE, guarded ``[[reskin.texel]]`` scaffold, emitted from the derivation.

    Every ``expect_*`` is emitted rather than typed, so a guard cannot start life disagreeing with the
    bytes; every row starts ``enabled = false``, so the first build is provably a no-op and the author
    switches on one page at a time.
    """
    L = ["# AUTO-SCAFFOLDED by `ff9mapkit summon-reskin export-art --ef %d`." % effect,
         "# Every number is DERIVED from the container's own id-4 header.  Two kinds of line only:",
         "#   * GUARDS (`expect_*`, `expect_sha256`) -- what the derivation MUST find.  They refuse;",
         "#     they instruct nothing.  Re-export rather than retyping them.",
         "#   * AUTHORED DECISIONS (`source`, `enabled`, `acknowledge_cutout_reshape`).",
         "#",
         "# Paint the `<name>.png` files IN INDEX SPACE (a P-mode editor), keeping the file name --",
         "# the name is the contract.  `<name>.coverage.png` hatches the never-sampled pad: paint",
         "# inside the island, or the edit is inert (reported, never fatal).",
         "",
         "[reskin]",
         "effect = %d" % effect,
         'label  = "ef%03d-texel-scaffold"' % effect,
         '# the drift guard: sha256 of the pristine stock container in YOUR install.  A HASH, not',
         '# data -- no stock byte is committable.',
         'expect_sha256 = "%s"' % stock_sha,
         ""]
    for e in entries:
        cov = ("%d of %d texels sampled (%.1f%%), %d dead, %d interior hole(s)"
               % (e["covered_texels"], e["wh"][0] * e["wh"][1],
                  100.0 * e["covered_texels"] / max(1, e["wh"][0] * e["wh"][1]),
                  e["dead_texels"], e["interior_holes"])
               if e["coverage_available"] else "coverage UNAVAILABLE (%s)" % e["coverage_reason"])
        L += ["[[reskin.texel]]",
              'name = "%s"' % e["name"],
              'source = "%s"' % e["png"],
              "expect_page_offset = %#08x" % e["page_offset"],
              "expect_page_bytes  = %d" % e["page_bytes"],
              "expect_page_wh     = [%d, %d]" % tuple(e["wh"]),
              "enabled = false",
              "acknowledge_cutout_reshape = false",
              '# palette_from = "%s"   # optional cross-reference; omitted = the STOCK palette,'
              % e["palette_name"],
              "#                              0 CLUT bytes touched (this rung's default).",
              "# measured: %s" % cov,
              "# measured: %d distinct indices, %d transparent texels at index %s"
              % (e["distinct_indices"], e["index0_texels"],
                 ",".join(str(i) for i in e["transparent_indices"]) or "-"),
              ""]
    return "\n".join(L) + "\n"


# ============================================================ (5) THE BUILD
#: every key one ``[[reskin.texel]]`` row understands. Unknown keys REFUSE rather than being ignored:
#: a mistyped ``acknowledge_cutout_reshape`` fails closed, which is fine, but a mistyped
#: ``expect_page_offset`` silently drops a guard -- and a guard may only ever fail CLOSED.
_TEXEL_KEYS = frozenset((
    "name", "source", "enabled", "note", "palette_from", "acknowledge_cutout_reshape",
    "expect_page_offset", "expect_page_bytes", "expect_page_wh",
))


@dataclass
class TexelTarget:
    """One resolved texel row: its page, the art, and every census the gates read."""
    name: str
    enabled: bool
    source: str
    page: TexelPage
    note: str = ""
    palette_from: str = ""
    ack_cutout: bool = False
    stock: bytes = b""
    new: bytes = b""
    changed: Tuple[int, ...] = ()
    cutout_punch: int = 0
    cutout_fill: int = 0
    dead_changed: int = 0
    live_changed: int = 0
    cov: Optional[Coverage] = None
    distinct_stock: int = 0
    distinct_new: int = 0
    round_trip: bool = True
    #: what the art-side drift guard had to say (see :func:`_gate_manifest`).
    manifest_note: str = ""

    @property
    def cutout_flips(self) -> int:
        return self.cutout_punch + self.cutout_fill


@dataclass
class TexelBuild:
    effect: int
    label: str
    spec_path: str
    source: str
    #: the PRISTINE stock container the drift guard ran against.
    stock: bytes
    #: what THIS lane spliced into -- ``stock``, or a sibling lane's patched bytes when composed.
    orig: bytes
    patched: bytes
    sha_stock: str
    sha_out: str
    pages: List[TexelPage]
    targets: List[TexelTarget]
    pmap: RS.PaletteMap
    guard: str = "none -- UNGUARDED"
    #: how ``orig`` came to be: ``""`` when it is the stock container, else the sibling that made it.
    base_label: str = ""
    base_changed: Tuple[int, ...] = ()
    orth_specs: Dict[str, str] = field(default_factory=dict)
    check: Optional["SelfCheck"] = None

    @property
    def enabled(self) -> List[TexelTarget]:
        return [t for t in self.targets if t.enabled]

    @property
    def composed(self) -> bool:
        return bool(self.base_label)

    @property
    def sha_in(self) -> str:
        return _sha(self.orig)


def load_spec(path) -> dict:
    """Load a ``[reskin]`` spec that carries a texel table, a target table, or BOTH.

    ONE spec, two levers, deliberately: their byte spans are provably disjoint, so making an author
    keep two files in step for one container would invent a drift risk the format does not have.
    """
    with open(path, "rb") as fh:
        spec = tomllib.load(fh)
    r = spec.get("reskin")
    if not isinstance(r, dict):
        raise RepaintError("%s has no [reskin] table" % path)
    if "effect" not in r:
        raise RepaintError("[reskin] needs `effect`")
    if not r.get("texel") and not r.get("target"):
        raise RepaintError("%s declares neither [[reskin.target]] (the CLUT lever) nor "
                           "[[reskin.texel]] (the texel lever) -- nothing to do" % path)
    return spec


def _spec_dir(spec_path: str) -> str:
    """Where a RELATIVE ``source`` / sibling name resolves from: the SPEC FILE'S own directory.

    Never this module's -- a package directory holds no PNG, so a module-relative base would make
    every relative source a missing file for every user while reading like a lookup.
    """
    sp = str(spec_path or "")
    if not sp or sp == "?":
        return os.getcwd()
    return os.path.dirname(os.path.abspath(sp))


def _gate_collisions(blob: bytes, page: TexelPage) -> None:
    """THE CO-TRANSFORM REFUSAL, evaluated per target instead of assumed away.

    Two independent tests, because a VRAM cell and a file span are two different ways to collide:
    another writer declaring the SAME cell means the picture on screen is whichever upload ran last,
    and another writer whose FILE SPAN overlaps means one edit silently rewrites two pictures. The
    corpus answer for creature pages is 0 and 0 over 24 packages / 93 pages -- which is exactly why
    this is cheap to check and expensive to assume: six corpus effects park id-9 slots at x = 320,
    the ladder rung their own ``partCount`` leaves unused, so the near miss is one header field away.
    """
    others = other_page_writers(blob)
    hits = others.get(page.vram, [])
    if hits:
        raise RepaintError(
            "CO-TRANSFORM REFUSAL on %s: VRAM cell %s is ALSO written by %s.  Every multi-writer page "
            "pair in the corpus is genuinely different art shown at different cast phases (0 of 156 "
            "pairs is byte-identical), so repainting one writer leaves the others stock and the cast "
            "flickers between two pictures.  Naming every writer is %s"
            % (page.name, str(page.vram),
               "; ".join("%s @%#x" % (s, o) for s, o, _n in hits), W6B_REASON))
    lo, hi = page.page_offset, page.page_offset + page.page_bytes
    for cell, ws in sorted(others.items()):
        for src, off, nb in ws:
            if off < hi and lo < off + nb:
                raise RepaintError(
                    "CO-TRANSFORM REFUSAL on %s: its file span %#x..%#x overlaps %s (%#x..%#x, VRAM "
                    "%s).  One splice would rewrite two declared pictures.  %s"
                    % (page.name, lo, hi, src, off, off + nb, str(cell), W6B_REASON))


def _gate_texanim(blob: bytes, targets: Sequence[TexelTarget]) -> None:
    """THE TEXANIM REFUSAL -- unconditional on the five armed packages, no key lifts it.

    ``reskin.py``'s own gate keys on ``Palette.slot < 0`` to spot a creature target; a texel target has
    no palette at all, so the predicate is re-implemented here rather than inherited -- an inherited
    one would simply never fire and the gate would be a comment.

    The refusal is HARDER for a texel edit than for a recolour, and the reason is now stateable rather
    than merely unread: the region decodes as ``u32 count`` + ``count`` 20-byte records whose pointers
    all close inside the region, and every target's first four fields read as a texel RECT that fits a
    128x128 page -- ``(27,62,11x12)`` on ef038, ``(33,78,9x14)`` and ``(24,102,8x14)`` on the ef177
    family. Both surviving readings hurt a repaint of that window: a frame blit overwrites repainted
    texels mid-cast, and a moving sample window shows frames the author never previewed.
    """
    live = [t.name for t in targets if t.enabled]
    if not live:
        return
    ta = RS.texanim_region(blob)
    if ta is None or not ta.armed:
        return
    raise RepaintError(
        "TEXANIM ARMED (%d bytes at %#x..%#x) and this spec repaints CREATURE pages (%s).  The record "
        "is PER PART and addresses a small texel WINDOW inside the part's own page, so a running "
        "animation either blits frames over the repainted texels mid-cast or slides the sample window "
        "across art the author never previewed.  This is not a knob: read the table first.  (The "
        "corpus class is ef038 / ef177 / ef493 / ef494 / ef495.)"
        % (ta.nbytes, ta.lo, ta.hi, ", ".join(live)))


def _gate_manifest(blob: bytes, src: Path, target_name: str, page: TexelPage) -> str:
    """THE STOCK-SHA DRIFT GUARD, applied where the ART is rather than where the spec is.

    ``export_art`` drops :data:`ART_MANIFEST` beside the PNGs it writes. When one is there, the pack
    refuses unless its ``stock_sha256`` is the container being patched and its record of this page
    agrees with the header's own derivation. Without it a re-exported page from a patched install
    would pack cleanly into a container it never came out of -- the silent failure with no symptom.
    Absent manifest = no extra guard (the spec's ``expect_sha256`` still ran); it is never fabricated.
    """
    mf = src.parent / ART_MANIFEST
    if not mf.is_file():
        return "no %s beside %s -- the spec's own expect_sha256 is the only guard" % (ART_MANIFEST,
                                                                                      src.name)
    try:
        man = json.loads(mf.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise RepaintError("%s is unreadable (%s) -- delete it or re-run export-art" % (mf, e))
    got = man.get("stock_sha256")
    want = _sha(blob)
    if got != want:
        raise RepaintError(
            "ART DRIFT on %s: %s was exported from a container with sha256 %s, but the container "
            "being patched is %s.  The art and the bytes underneath it are not the same summon (a "
            "Steam/Moguri patch, another mod, or a stale export directory).  Re-run "
            "`summon-reskin export-art` against this install." % (target_name, mf, got, want))
    rec = next((e for e in (man.get("parts") or []) if e.get("name") == target_name), None)
    if rec is None:
        raise RepaintError("ART DRIFT on %s: %s carries no record for that page (it records %s)"
                           % (target_name, mf, ", ".join(e.get("name", "?")
                                                         for e in (man.get("parts") or []))))
    for key, mine in (("page_offset", page.page_offset), ("page_bytes", page.page_bytes)):
        if rec.get(key) != mine:
            raise RepaintError("ART DRIFT on %s: %s records %s %s, the header derives %s"
                               % (target_name, mf, key, rec.get(key), mine))
    if list(rec.get("wh") or []) != [page.w, page.h]:
        raise RepaintError("ART DRIFT on %s: %s records wh %s, the header derives %s"
                           % (target_name, mf, rec.get("wh"), [page.w, page.h]))
    return "%s stock_sha256 MATCHES; page record agrees with the header" % ART_MANIFEST


def _resolve_base(spec: dict, spec_path: str, blob: bytes, game, compose: Optional[bool]):
    """The bytes this lane splices INTO, and the label saying where they came from.

    ``[reskin.orthogonality] reskin = "..."`` + ``compose = true`` rebuilds a SHIPPED CLUT spec and
    hands its patched container over, so a composed artifact keeps exactly one source of truth for the
    palette half instead of copying its rows into a second file that can drift out of step with it.
    """
    orth = (spec["reskin"].get("orthogonality") or {})
    want = bool(orth.get("compose", False)) if compose is None else bool(compose)
    sib = orth.get("reskin")
    if not want:
        return blob, "", ()
    if not sib:
        raise RepaintError("[reskin.orthogonality] says `compose = true` but names no `reskin` "
                           "sibling to compose onto")
    path = sib if os.path.isabs(sib) else os.path.join(_spec_dir(spec_path), sib)
    if not os.path.isfile(path):
        raise RepaintError("compose: no reskin sibling at %s" % path)
    b1 = RS.build(RS.load_spec(path), path, game, blob=blob)
    if b1.effect != int(spec["reskin"]["effect"]):
        raise RepaintError("compose: %s targets ef%03d, this repaint targets ef%03d -- composing "
                           "another effect's edits would corrupt this container"
                           % (os.path.basename(path), b1.effect, int(spec["reskin"]["effect"])))
    delta = tuple(i for i in range(len(blob)) if blob[i] != b1.patched[i])
    return b1.patched, ("composed on %s (%d CLUT bytes)" % (os.path.basename(path), len(delta))), delta


def build(spec: dict, spec_path: str = "?", game=None, blob: Optional[bytes] = None,
          base: Optional[bytes] = None, base_label: str = "",
          compose: Optional[bool] = None) -> TexelBuild:
    """Read the install, resolve every texel target, run every gate, splice the pages.

    ``blob`` supplies the STOCK container directly and skips the install read, so the whole guard /
    gate / drift pipeline is exercisable on synthetic bytes with no install -- a law that held on only
    one of two entry paths would not be one. ``base`` supplies already-patched bytes from a sibling
    lane (the CLI's one-spec composition); ``compose`` overrides the spec's own
    ``[reskin.orthogonality] compose`` (``False`` is what an orthogonality REBUILD passes, so a spec
    that composes onto its sibling can never recurse into rebuilding itself).
    """
    r = spec["reskin"]
    effect = int(r["effect"])
    if blob is None:
        blob, source = R.read_stock_effect(effect, game)
    else:
        source = "(caller-supplied bytes)"
    if not r.get("expect_sha256") and effect not in R.EXPECTED_STOCK_SHA \
            and not r.get("allow_unguarded"):
        raise RepaintError(
            "ef%03d has NO drift guard: the spec declares no `expect_sha256` and the effect is not in "
            "rescore.EXPECTED_STOCK_SHA.  A repaint splices at header-derived offsets; if a "
            "Steam/Moguri patch or another mod moved a page under the edit, nothing would notice.  "
            "Run `ff9mapkit summon-reskin export-art --ef %d` to emit the guard from your own "
            "install, or say `allow_unguarded = true` deliberately." % (effect, effect))
    sha_stock = R.drift_guard(effect, blob, r.get("expect_sha256"))
    guard = ("the spec's own expect_sha256 -- MATCHES" if r.get("expect_sha256") else
             ("REGISTERED in rescore.EXPECTED_STOCK_SHA -- MATCHES"
              if effect in R.EXPECTED_STOCK_SHA
              else "none -- UNGUARDED (allow_unguarded = true)"))

    if base is None:
        base, base_label, base_delta = _resolve_base(spec, spec_path, blob, game, compose)
    else:
        base_delta = tuple(i for i in range(len(blob)) if blob[i] != base[i])
        base_label = base_label or "composed on a caller-supplied build (%d bytes)" % len(base_delta)
    if len(base) != len(blob):                                   # pragma: no cover - by construction
        raise RepaintError("the composition base is a different length from the stock container")

    pmap = RS.palette_map(blob, effect=effect)
    pages = creature_texel_pages(blob)
    rows = r.get("texel") or []
    if not rows:
        raise RepaintError("%s declares no [[reskin.texel]] -- nothing for the texel lane to do"
                           % spec_path)

    targets: List[TexelTarget] = []
    seen: Set[str] = set()
    base_dir = _spec_dir(spec_path)
    for i, d in enumerate(rows):
        where = "[[reskin.texel]] #%d" % i
        unknown = sorted(set(d) - _TEXEL_KEYS)
        if unknown:
            raise RepaintError(
                "%s declares unknown key(s) %s.  Refused rather than ignored: a mistyped guard "
                "silently drops the guard, and a guard may only ever fail CLOSED.  Known keys: %s"
                % (where, ", ".join(repr(u) for u in unknown), ", ".join(sorted(_TEXEL_KEYS))))
        name = d.get("name")
        if not name:
            raise RepaintError("%s has no `name`" % where)
        if name in seen:
            raise RepaintError("texel target %r is declared twice" % name)
        seen.add(name)
        page = texel_page(blob, name)
        where = "texel target %s" % name
        if "expect_page_offset" in d and int(d["expect_page_offset"]) != page.page_offset:
            raise RepaintError("%s: the spec guards file %#x, the derivation says %#x"
                               % (where, int(d["expect_page_offset"]), page.page_offset))
        if "expect_page_bytes" in d and int(d["expect_page_bytes"]) != page.page_bytes:
            raise RepaintError("%s: the spec guards %d page bytes, the derivation says %d"
                               % (where, int(d["expect_page_bytes"]), page.page_bytes))
        if "expect_page_wh" in d and tuple(int(x) for x in d["expect_page_wh"]) != page.wh:
            raise RepaintError("%s: the spec guards %s, the derivation says %s"
                               % (where, list(d["expect_page_wh"]), list(page.wh)))
        pal_from = str(d.get("palette_from", "") or "")
        if pal_from:
            try:
                pal = pmap.by_name(pal_from)
            except RS.ReskinError as e:
                raise RepaintError("%s: `palette_from` -- %s" % (where, e)) from None
            if pal.name != page.palette_name:
                raise RepaintError(
                    "%s: `palette_from = %r` resolves to %s, but this page indexes into %s.  A page's "
                    "palette is a HEADER FACT (its own CLUT word), not a choice -- naming another "
                    "row would mean authoring indices against colours the engine will never apply "
                    "here." % (where, pal_from, pal.name, page.palette_name))
        targets.append(TexelTarget(
            name=name, enabled=bool(d.get("enabled", True)), source=str(d.get("source", "")),
            page=page, note=str(d.get("note", "")), palette_from=pal_from,
            ack_cutout=_ack_bool(d, "acknowledge_cutout_reshape", where)))

    _gate_texanim(blob, targets)

    out = bytearray(base)
    for t in targets:
        if not t.enabled:
            continue
        _gate_collisions(blob, t.page)
        if not t.source:
            raise RepaintError("texel target %s is enabled but names no `source` image" % t.name)
        src = Path(t.source)
        if not src.is_absolute():
            src = Path(base_dir) / src
        t.manifest_note = _gate_manifest(blob, src, t.name, t.page)
        words = palette_words(base, t.page)
        t.stock = bytes(base[t.page.page_offset:t.page.page_offset + t.page.page_bytes])
        t.new = read_indexed_png(src, t.page.w, t.page.h, len(words))
        t.changed = tuple(i for i in range(len(t.stock)) if t.stock[i] != t.new[i])
        zeros = set(transparent_indices(words))
        t.cutout_punch = sum(1 for i in t.changed if t.stock[i] not in zeros and t.new[i] in zeros)
        t.cutout_fill = sum(1 for i in t.changed if t.stock[i] in zeros and t.new[i] not in zeros)
        if t.cutout_flips and not t.ack_cutout:
            raise RepaintError(
                "THE CUTOUT LAW, %s: this edit moves %d texel(s) across the transparent-index "
                "boundary (%d punched opaque->hole, %d filled hole->opaque).  Index %s is the "
                "palette's only alpha-0 entry, so those texels change the model's SILHOUETTE -- "
                "something the CLUT lever structurally cannot do, and therefore something this lane "
                "makes you say out loud.  Reshaping a torn wing edge is legitimate: say "
                "`acknowledge_cutout_reshape = true` on that row.  Painting through a hole by "
                "accident is not, and is what this catches."
                % (t.name, t.cutout_flips, t.cutout_punch, t.cutout_fill,
                   ",".join(str(z) for z in sorted(zeros)) or "(none)"))
        t.cov = coverage(blob, t.page.index)
        if t.cov.available:
            t.dead_changed = sum(1 for i in t.changed if not t.cov.mask[i])
            t.live_changed = len(t.changed) - t.dead_changed
        else:
            t.live_changed = len(t.changed)
        t.distinct_stock, t.distinct_new = len(set(t.stock)), len(set(t.new))
        t.round_trip = _round_trip_ok(t.new, words, t.page.w, t.page.h)
        out[t.page.page_offset:t.page.page_offset + t.page.page_bytes] = t.new
    patched = bytes(out)
    if len(patched) != len(base):                                # pragma: no cover - in-place splice
        raise RepaintError("the splice changed the container length -- impossible by construction")

    orth = {k: v for k, v in (r.get("orthogonality") or {}).items() if isinstance(v, str)}
    return TexelBuild(effect=effect, label=str(r.get("label", "repaint")), spec_path=str(spec_path),
                      source=source, stock=blob, orig=bytes(base), patched=patched,
                      sha_stock=sha_stock, sha_out=_sha(patched), pages=pages, targets=targets,
                      pmap=pmap, guard=guard, base_label=base_label,
                      base_changed=tuple(base_delta), orth_specs=orth)


# ============================================================ (6) THE SELF-CHECK
Gate = RS.Gate


@dataclass
class SelfCheck:
    accounting: List[Gate]
    rules: List[Gate]
    regions: List[Gate]
    orthogonality: List[Gate]
    quality: List[Gate]
    changed: List[int]
    per_target: Dict[str, int]

    @property
    def gates(self) -> List[Gate]:
        return self.accounting + self.rules + self.regions + self.orthogonality + self.quality

    @property
    def ok(self) -> bool:
        return all(g.ok for g in self.gates)


def _rebuild_reskin(path: str, mine: Set[int], blob: bytes) -> Tuple[Set[int], str]:
    """Rebuild a CLUT reskin from its own toml and return ``(changed offsets, the detail line)``."""
    b2 = RS.build(RS.load_spec(path), path, blob=blob)
    d = {i for i in range(len(b2.orig)) if b2.orig[i] != b2.patched[i]}
    return d, ("the CLUT lane changes %d bytes from %s; intersection %d"
               % (len(d), os.path.basename(path), len(d & mine)))


def _rebuild_rescore(path: str, mine: Set[int], blob: bytes) -> Tuple[Set[int], str]:
    b2 = R.build_patched(R.load_spec(path), path, blob=blob)
    d = {i for i in range(len(b2.orig)) if b2.orig[i] != b2.patched[i]}
    return d, ("W2 changes %d bytes (the camera Code at %s); intersection %d"
               % (len(d), ", ".join("%#x" % o for o in sorted(d)), len(d & mine)))


#: ``[reskin.orthogonality]`` table name -> the callable that REBUILDS that sibling lane. Same posture
#: as ``reskin.ORTH_REBUILDERS``: a table this package cannot rebuild gets an explicit SKIP naming the
#: reason, never a crash and never a silent pass that reads like a proof.
#:
#: The signature takes the STOCK BLOB as a third argument, which the reskin lane's own registry does
#: not. Two reasons, both load-bearing here and not there: a composed build already rebuilds a sibling
#: for its splice base, so re-reading ``resources.assets`` per gate would run a UnityPy load three
#: times for one command; and both halves of a composed proof MUST be intersected against the same
#: container -- re-reading the install per gate silently allows two different ones.
ORTH_REBUILDERS: Dict[str, Callable[[str, Set[int], bytes], Tuple[Set[int], str]]] = {
    "reskin": _rebuild_reskin,
    "rescore": _rebuild_rescore,
}

#: sibling table -> the TOP-LEVEL TOML table its own spec declares. A reskin spec's table is
#: ``[reskin]``; a rescore spec's is ``[rescore]``.
_ORTH_TABLE = {"reskin": "reskin", "rescore": "rescore", "retime": "retime"}


def _orthogonality(b: TexelBuild, mine: Set[int]) -> List[Gate]:
    """Rebuild each declared sibling lane from its OWN spec and intersect its edits with this one's.

    A gate exists for every sibling the spec NAMES, plus the CLUT lane always -- because that is the
    one this rung composes with, and a composed build whose two halves were never intersected would
    be shipping the disjointness as a claim.
    """
    out: List[Gate] = []
    base = _spec_dir(b.spec_path)
    for table in ["reskin"] + sorted(k for k in b.orth_specs if k != "reskin"):
        title = "the %s lane's edits are disjoint from this repaint's" % table
        name = b.orth_specs.get(table)
        if not name:
            out.append(Gate(True, title,
                            "SKIPPED: this spec names no `%s` sibling under [reskin.orthogonality], "
                            "so disjointness with the %s lane is UNPROVEN here -- not proven.  Name a "
                            "sibling spec for the same effect to turn this skip into a real "
                            "changed-offset intersection." % (table, table)))
            continue
        path = name if os.path.isabs(name) else os.path.join(base, name)
        if not os.path.isfile(path):
            out.append(Gate(False, title, "SKIPPED: no %s spec at %s -- but the spec NAMED it"
                            % (table, path)))
            continue
        ef = RS._sibling_effect(path, _ORTH_TABLE.get(table, table))
        if ef != b.effect:
            out.append(Gate(True, title,
                            "SKIPPED: %s targets ef%s, this repaint targets ef%03d -- rebuilding "
                            "another effect's edits would prove nothing about this one"
                            % (os.path.basename(path), "%03d" % ef if ef is not None else "?",
                               b.effect)))
            continue
        rebuild = ORTH_REBUILDERS.get(table)
        if rebuild is None:
            out.append(Gate(True, title,
                            "SKIPPED (LANE NOT IN THIS PACKAGE): %s targets this effect but the `%s` "
                            "lane cannot be rebuilt here, so its disjointness is UNPROVEN -- not "
                            "proven.  Register a rebuilder in repaint.ORTH_REBUILDERS[%r]."
                            % (os.path.basename(path), table, table)))
            continue
        try:
            d, detail = rebuild(path, mine, b.stock)
            out.append(Gate(not (d & mine), title, detail))
        except Exception as e:                                   # pragma: no cover - spec-dependent
            out.append(Gate(False, title, "FAILED to rebuild %s: %s" % (os.path.basename(path), e)))
    return out


def self_check(b: TexelBuild) -> SelfCheck:
    """Every gate, on OUR bytes -- the accounting, the hard rules, the inverted region partition, the
    sibling intersections and the quality census."""
    changed = [i for i in range(len(b.orig)) if b.orig[i] != b.patched[i]]
    mine = set(changed)

    # ---- (1) byte accounting: every changed byte inside a named target's own licensed page span
    owner: Dict[int, str] = {}
    per_target: Dict[str, int] = {}
    for t in b.enabled:
        per_target[t.name] = len(t.changed)
        for o in t.changed:
            owner[t.page.page_offset + o] = t.name
    unexplained = [o for o in changed if o not in owner]
    spans = [(t.page.name, t.page.page_offset, t.page.page_offset + t.page.page_bytes)
             for t in b.enabled]
    span_miss = [o for o in changed if not any(lo <= o < hi for _n, lo, hi in spans)]
    envelope = sum(p.page_bytes for p in b.pages)
    acc = [
        Gate(not unexplained, "every changed byte belongs to a named texel target",
             "%d bytes changed, %d unexplained%s"
             % (len(changed), len(unexplained),
                "" if not unexplained else " at " + ", ".join("%#x" % o for o in unexplained[:8]))),
        Gate(not span_miss, "every changed byte lands inside a derived PAGE span",
             ("spans: " + " | ".join("%s %#x..%#x (%d B)" % (n, lo, hi, hi - lo)
                                     for n, lo, hi in spans)) if spans else
             "no enabled target -- this build splices nothing"),
        Gate(len(changed) <= envelope, "under the DERIVED texel envelope",
             "%d changed of the %d-byte %d-page envelope (%.3f%% of the %d-byte container); the "
             "envelope is partCount * 0x4000, derived per effect"
             % (len(changed), envelope, len(b.pages),
                100.0 * len(changed) / max(1, len(b.orig)), len(b.orig))),
        Gate(len(b.patched) == len(b.orig), "same length by construction",
             "%d B in, %d B out" % (len(b.orig), len(b.patched))),
    ]

    # ---- (2) the hard rules of THIS lane
    bad_rt = [t.name for t in b.enabled if not t.round_trip]
    flips = [t for t in b.enabled if t.cutout_flips]
    unack = [t.name for t in flips if not t.ack_cutout]
    zero_law = []
    clut_hits = 0
    for t in b.enabled:
        z = transparent_indices(palette_words(b.orig, t.page))
        if list(z) != [0]:
            zero_law.append("%s: transparent indices %s" % (t.name, list(z)))
        clut_hits += sum(1 for o in range(t.page.clut_offset,
                                          t.page.clut_offset + 2 * t.page.clut_entries)
                         if o in mine)
    rules = [
        Gate(not bad_rt, "THE INDEXED ROUND TRIP is byte-identical on every patched page",
             "%d page(s) re-encoded to a P-mode PNG and re-read as the same indices%s"
             % (len(b.enabled), "" if not bad_rt else " -- DRIFT at " + ", ".join(bad_rt))),
        Gate(not unack, "THE CUTOUT LAW: no unacknowledged index-0 boundary crossing",
             "no texel crossed the transparent-index boundary" if not flips else
             "; ".join("%s punched %d / filled %d (%s)"
                       % (t.name, t.cutout_punch, t.cutout_fill,
                          "ACKNOWLEDGED" if t.ack_cutout else "NOT acknowledged")
                       for t in flips)),
        Gate(True, "the transparent-index law (reported: exactly one alpha-0 entry, at index 0)",
             "holds on every patched page (corpus: 93/93)" if not zero_law else
             "DEVIATES -- " + "; ".join(zero_law) + ".  The cutout census used the DERIVED set, so "
             "the gate is still correct; the note exists because a row that is not the corpus shape "
             "is worth knowing about before a cast."),
        Gate(all(t.page.bpp == 8 for t in b.enabled), "every patched page is the 8bpp 128x128 layout",
             ", ".join("%s %dx%d %dbpp" % (t.name, t.page.w, t.page.h, t.page.bpp)
                       for t in b.enabled) or "no enabled target"),
        Gate(clut_hits == 0, "this lane wrote ZERO CLUT bytes",
             "%d byte(s) of the %d row(s) this build's pages index into moved.  The palette is "
             "DISPLAY ONLY in the exported PNG; the container remains the palette authority, and "
             "the CLUT lever is `[[reskin.target]]`."
             % (clut_hits, len({t.page.clut_offset for t in b.enabled}))),
    ]

    # ---- (3) the INVERTED region partition + a strict re-parse
    regions: List[Gate] = []
    try:
        c = EC.parse_header(b.patched, strict=True)
        regions.append(Gate(c.cursor_end == len(b.patched), "the container re-parses STRICT",
                            "walker cursor %#x == file length %#x" % (c.cursor_end, len(b.patched))))
    except EC.ContainerError as e:                               # pragma: no cover
        regions.append(Gate(False, "the container re-parses STRICT", str(e)))
    gated = RS._regions(b.orig, b.effect, partition="texel")
    hits = []
    for name, lo, hi in gated:
        n = sum(1 for o in changed if lo <= o < hi)
        if n:
            hits.append("%s (%d bytes)" % (name, n))
    regions.append(Gate(not hits, "the CLUT strip, the id-4 header and every geometry / program / "
                                  "camera / sequence region are BYTE-IDENTICAL",
                        "%d regions gated (%d B of the container) under the TEXEL partition -- the "
                        "pages are licensed, everything else is not; %s%s"
                        % (len(gated), sum(hi - lo for _n, lo, hi in gated),
                           "no hits" if not hits else "HIT: " + "; ".join(hits),
                           "" if not b.composed else
                           ".  Measured on THIS LANE's delta: the CLUT strip is deliberately moved "
                           "by the sibling this build composes onto, and that the two never touch "
                           "the same byte is the COMPOSED HALVES gate below, not this one")))
    mp_p = EC.creature_package(b.patched)
    ok_dec = mp_p is not None and KT.texture_check(b.patched, mp_p)["decodable"]
    regions.append(Gate(ok_dec, "the patched id-4 package still DECODES",
                        "texture_check passes on the patched container (%d parts)"
                        % (mp_p.part_count if mp_p else 0)))
    pm_s, pm_p = b.pmap, RS.palette_map(b.patched, effect=b.effect)
    same_pal = ([(p.name, p.off, p.entries) for p in pm_s.palettes]
                == [(p.name, p.off, p.entries) for p in pm_p.palettes]) and all(
        b.orig[p.off:p.off + p.nbytes] == b.patched[p.off:p.off + p.nbytes] for p in pm_p.palettes)
    regions.append(Gate(same_pal, "every DERIVED palette re-derives and is byte-exact",
                        "%d palettes, %d spans -- the CLUT lever's whole surface is untouched by this "
                        "lane" % (len(pm_p.palettes), len(pm_p.spans))))

    # ---- (4) orthogonality, and the composition's own disjointness
    orth = _orthogonality(b, mine)
    if b.composed:
        inter = set(b.base_changed) & mine
        orth.append(Gate(not inter, "THE COMPOSED HALVES ARE DISJOINT",
                         "%s; this lane changed %d texel bytes; intersection %d.  Union = %d bytes "
                         "vs stock (sha %s)"
                         % (b.base_label, len(changed), len(inter),
                            len(set(b.base_changed) | mine), b.sha_out[:16])))

    # ---- (5) quality: the dead-pad report, the coverage share, the index census
    qual: List[Gate] = []
    dead_rows = [t for t in b.enabled if t.dead_changed]
    qual.append(Gate(True, "texels the geometry never samples (reported, not fatal)",
                     "no edited texel is outside the sampled island" if not dead_rows else
                     "; ".join("%s %d of %d edited texels are in the never-sampled pad (%.1f%% of "
                               "the edit) -- inert at run time, exactly as a hue rotation is inert "
                               "on an achromatic palette"
                               % (t.name, t.dead_changed, len(t.changed),
                                  100.0 * t.dead_changed / max(1, len(t.changed)))
                               for t in dead_rows)))
    ran = "; ".join("%s %d/%d sampled (%.1f%%), %d interior hole(s), %d faces"
                    % (t.name, t.cov.covered, t.cov.total, 100.0 * t.cov.covered_fraction,
                       t.cov.interior_holes, t.cov.faces)
                    for t in b.enabled if t.cov and t.cov.available) or "no coverage computed"
    no_cov = [t.name for t in b.enabled if t.cov is not None and not t.cov.available]
    if no_cov:
        ran += ("  |  UNAVAILABLE for %s -- the dead-pad census cannot run there, so it reports "
                "nothing rather than reporting zero" % ", ".join(no_cov))
    qual.append(Gate(True, "the UV coverage instrument ran (reported, not fatal)", ran))
    qual.append(Gate(True, "index census (reported)",
                     ", ".join("%s distinct %d->%d, %d texels moved (%.2f%% of the page)"
                               % (t.name, t.distinct_stock, t.distinct_new, len(t.changed),
                                  100.0 * len(t.changed) / max(1, t.page.page_bytes))
                               for t in b.enabled) or "no enabled target"))
    inert = [t.name for t in b.enabled if not t.changed]
    qual.append(Gate(True, "targets whose art matches the container already (reported, not fatal)",
                     "none" if not inert else ", ".join(inert)
                     + " -- an unedited re-export is a byte-exact no-op, which is the property that "
                       "makes a re-pack idempotent"))
    return SelfCheck(acc, rules, regions, orth, qual, changed, per_target)


# ============================================================ (7) THE PREVIEWS
def render_previews(b: TexelBuild, out_dir) -> List[str]:
    """Before / after / moved-texel sheets per enabled target, plus the coverage overlay.

    DECODED STOCK ART -- local-only for the same reason the export is, and written only under a root
    that has already passed the provenance guard.
    """
    Image = _need_pil()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    S = 3
    for t in b.enabled:
        words = palette_words(b.orig, t.page)
        rgba = [KT.bgr555_rgba(w) for w in words]
        w, h = t.page.w, t.page.h

        def _img(px):
            im = Image.new("RGBA", (w, h))
            im.putdata([rgba[i] for i in px])
            bg = Image.new("RGBA", (w, h), (24, 24, 28, 255))
            return Image.alpha_composite(bg, im)

        before, after = _img(t.stock), _img(t.new)
        moved = Image.new("RGBA", (w, h), (18, 18, 22, 255))
        ch = set(t.changed)
        moved.putdata([(255, 64, 200, 255) if i in ch else (24, 24, 28, 255)
                       for i in range(w * h)])
        sheet = Image.new("RGBA", (3 * w * S, h * S), (12, 12, 14, 255))
        for k, im in enumerate((before, after, moved)):
            sheet.paste(im.resize((w * S, h * S), Image.NEAREST), (k * w * S, 0))
        p = out / ("%s.repaint.png" % t.name)
        sheet.save(str(p))
        written.append(str(p))
        if t.cov is not None and t.cov.available:
            cp = out / ("%s.coverage.png" % t.name)
            write_coverage_png(t.new, words, t.cov.mask, w, h, cp)
            written.append(str(cp))
    return written


# ============================================================ (8) STAGING + THE LEDGERED SCRIPTS
def modfilelist_refusal(mod_root) -> Optional[str]:
    """THE SILENT-FALLBACK LAW, shared verbatim with both sibling lanes: a mod folder carrying a
    ``ModFileList.txt`` makes every unlisted override INVISIBLE and ``SFX.Play`` suppresses the
    missing-asset error, so "nothing changed" would be the only symptom. This lane REFUSES rather than
    half-owning somebody else's registry, and NEVER creates a list."""
    return R.modfilelist_refusal(mod_root)


def stage(b: TexelBuild, root=None, game_root=None, allow_install: bool = False,
          previews: bool = True, mod_root=None, refuse_modfilelist: bool = False) -> dict:
    """Write the patched container, the previews and the two ``--root``-aware live scripts.

    Deliberately the same shape as :func:`ff9mapkit.summons.reskin.stage` and driven by the SAME
    plan-rendered script templates: one deploy/revert implementation with a plan injected into it,
    never a second copy of a first-deploy snapshot scheme that can drift from the one that is proven.
    """
    if root is None:
        root = export.assert_local_only(staging_root(b.effect))
    root = Path(R._refuse_repo_path(root))
    if not allow_install:
        R._refuse_install_path(root, game_root)
    deploying = mod_root is not None
    mod_root = Path(R._refuse_repo_path(mod_root)) if deploying else root / "mod"
    if deploying and not allow_install:
        R._refuse_install_path(mod_root, game_root)
    if refuse_modfilelist:
        why = modfilelist_refusal(mod_root)
        if why:
            raise RepaintError(why)

    root.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(root / "backups", mod_root=mod_root)
    rel = "/".join(MOD_SUBPATH.split("/") + ["ef%03d" % b.effect])
    dest = Path(mod_root).joinpath(*rel.split("/"))
    sha = ledger.write_bytes(dest, b.patched)

    preview_files: List[str] = []
    if previews:
        preview_files = render_previews(b, root / "previews")

    live_mod = Path(game_root) / "FF9CustomMap" if game_root else None
    note = ("this artifact is STOCK ef%03d + the texel repaint '%s'%s; it REPLACES whatever container "
            "the mod folder holds for that effect.  The first-deploy snapshot restores it "
            "byte-for-byte." % (b.effect, b.label,
                                " composed on the CLUT lane (%s)" % b.base_label if b.composed
                                else ""))
    plan = {
        "effect": b.effect,
        "label": b.label,
        "default_mod_root": str(live_mod) if live_mod else "",
        "snapshot_base": str(root / "live-snapshot"),
        "revert_script": str(root / ("revert_summon_repaint_%d.py" % b.effect)),
        "targets": [{"src": str(dest), "rel": rel, "sha256": sha}],
        "expect_live_sha256": None,
        "note": note,
    }
    if live_mod is not None:
        live = live_mod.joinpath(*rel.split("/"))
        if live.exists():
            plan["expect_live_sha256"] = _sha(live.read_bytes())
    scripts = {
        "deploy": str(RS._write_script(root / "deploy_repaint.py", RS._DEPLOY_TEMPLATE, plan)),
        "revert": str(RS._write_script(root / ("revert_summon_repaint_%d.py" % b.effect),
                                       RS._REVERT_TEMPLATE, plan)),
    }
    if deploying:
        scripts["ledger_revert"] = str(ledger.write_revert_script(
            root, "%d" % b.effect, prefix="revert_summon_repaint_ledger"))

    manifest = {
        "spec": b.spec_path, "effect": b.effect, "label": b.label, "lane": "texel/indexed",
        "stock_sha256": b.sha_stock, "base_sha256": b.sha_in, "patched_sha256": sha,
        "composed": b.composed, "composed_on": b.base_label,
        "composed_base_bytes": len(b.base_changed),
        "container": str(dest), "scripts": scripts, "previews": preview_files,
        "changed_bytes": len(b.check.changed) if b.check else None,
        "per_target_bytes": b.check.per_target if b.check else None,
        "staging_root": str(root), "mod_root": str(mod_root),
        "texels": {t.name: {"enabled": t.enabled, "source": t.source,
                            "page_offset": t.page.page_offset, "page_bytes": t.page.page_bytes,
                            "wh": list(t.page.wh), "changed": len(t.changed),
                            "cutout_punch": t.cutout_punch, "cutout_fill": t.cutout_fill,
                            "acknowledge_cutout_reshape": t.ack_cutout,
                            "dead_changed": t.dead_changed, "palette_from": t.palette_from}
                   for t in b.targets},
    }
    from .. import fsutil
    fsutil.atomic_write_text(root / "build_manifest.json",
                             json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")
    manifest["staged_files"] = len(ledger.files)
    return manifest


def verify(b: TexelBuild, root=None) -> dict:
    """Re-check what is STAGED, as bytes -- not as a rebuild's promise."""
    root = Path(root or staging_root(b.effect))
    mf = root / "build_manifest.json"
    lines: List[str] = []
    if not mf.exists():
        return {"ok": False, "root": str(root), "manifest": str(mf),
                "lines": ["VERIFY FAILED: no build manifest at %s" % mf]}
    man = json.loads(mf.read_text(encoding="utf-8"))
    ok = True
    p = Path(man["container"])
    if not p.exists():
        lines.append("VERIFY container   MISSING at %s" % p)
        ok = False
    else:
        got = p.read_bytes()
        same = got == b.patched
        ok = ok and same
        lines.append("VERIFY container   %d B sha %s -> %s"
                     % (len(got), _sha(got)[:16], "MATCHES the rebuild" if same else "DIVERGES"))
        if man.get("patched_sha256") != _sha(got):
            lines.append("VERIFY manifest    sha in the manifest does not match the staged file")
            ok = False
    if man.get("stock_sha256") != b.sha_stock:
        lines.append("VERIFY stock       the manifest was built against %s, this rebuild reads %s"
                     % (str(man.get("stock_sha256"))[:16], b.sha_stock[:16]))
        ok = False
    for name, sp in sorted((man.get("scripts") or {}).items()):
        exists = Path(sp).exists()
        ok = ok and exists
        lines.append("VERIFY %-11s %s" % (name, sp if exists else "MISSING: %s" % sp))
    missing = [f for f in (man.get("previews") or []) if not Path(f).exists()]
    lines.append("VERIFY previews    %d staged, %d missing"
                 % (len(man.get("previews") or []), len(missing)))
    ok = ok and not missing
    for name, tr in sorted((man.get("texels") or {}).items()):
        t = next((x for x in b.targets if x.name == name), None)
        if t is None or (t.enabled, t.page.page_offset, len(t.changed)) != (
                tr["enabled"], tr["page_offset"], tr["changed"]):
            lines.append("VERIFY texel       %s DIVERGES from the manifest" % name)
            ok = False
    return {"ok": ok, "root": str(root), "manifest": str(mf), "container": man.get("container"),
            "lines": lines}


# ============================================================ (9) REPORTING
def derivation_lines(blob: bytes, pages: Sequence[TexelPage]) -> List[str]:
    L = ["  THE DERIVED TEXEL PAGES (from the id-4 header, not from a table)"]
    if not pages:
        L.append("    none -- %s" % (creature_refusal(blob) or "no creature package"))
        return L
    others = other_page_writers(blob)
    for p in pages:
        clash = others.get(p.vram, [])
        L.append("    %-12s %#08x..%#08x  %dx%d %dbpp  VRAM %-11s CLUT row @%#08x (%s)%s"
                 % (p.name, p.page_offset, p.page_offset + p.page_bytes, p.w, p.h, p.bpp,
                    "(%d,%d)" % p.vram, p.clut_offset, p.palette_name,
                    "  ** %d OTHER WRITER(S)" % len(clash) if clash else ""))
    L += ["", "  THE PAGE-WRITER CENSUS (every non-creature page upload this container declares)",
          "    %d declared cell(s); creature band VRAM x [%d,%d) -- corpus: 0 collisions over 24 "
          "packages / 93 pages" % (len(others), CREATURE_VRAM_X[0], CREATURE_VRAM_X[1])]
    ta = RS.texanim_region(blob)
    L += ["", "  THE TEXANIM GATE"]
    if ta is None or not ta.present:
        L.append("    no id-4 creature package")
    elif not ta.armed:
        L.append("    region is EMPTY (firstBlock == motionOffsets[0]) -- creature texel scope is open")
    else:
        L.append("    ARMED: %d bytes at %#x..%#x -- creature texel scope REFUSED outright, no key "
                 "lifts it" % (ta.nbytes, ta.lo, ta.hi))
    return L


def describe(b: TexelBuild) -> List[str]:
    L = ["ef%03d  %s   [TEXEL REPAINT -- lever #2]" % (b.effect, b.label),
         "  stock source   : %s" % b.source,
         "  stock sha256   : %s  (drift guard %s)" % (b.sha_stock, b.guard),
         "  splice base    : %s" % (b.base_label or "the stock container"),
         "  repaint sha256 : %s" % b.sha_out,
         "  container      : %d B in, %d B out (same length -- every page is spliced in place)"
         % (len(b.orig), len(b.patched)),
         ""]
    L += derivation_lines(b.stock, b.pages)
    L += ["", "  THE TEXEL TARGETS"]
    for t in b.targets:
        if not t.enabled:
            L.append("    off  %-12s %s" % (t.name, t.note or "(disabled -- states an intent)"))
            continue
        cov = ("%d/%d sampled (%.1f%%)" % (t.cov.covered, t.cov.total, 100.0 * t.cov.covered_fraction)
               if t.cov and t.cov.available else "coverage UNAVAILABLE")
        L.append("    ON   %-12s <- %s" % (t.name, t.source))
        L.append("         %5d/%d texels moved (%.2f%%) | live %d, dead-pad %d | cutout punch %d "
                 "fill %d%s | distinct %d->%d | %s"
                 % (len(t.changed), t.page.page_bytes,
                    100.0 * len(t.changed) / max(1, t.page.page_bytes), t.live_changed,
                    t.dead_changed, t.cutout_punch, t.cutout_fill,
                    " (ACKNOWLEDGED)" if t.ack_cutout and t.cutout_flips else "",
                    t.distinct_stock, t.distinct_new, cov))
        if t.manifest_note:
            L.append("         art guard: %s" % t.manifest_note)
        if t.note:
            L.append("         %s" % t.note)
    return L


def check_lines(b: TexelBuild) -> List[str]:
    c = b.check
    L = ["", "  SELF-CHECK  (%d/%d gates)" % (sum(1 for g in c.gates if g.ok), len(c.gates))]
    for title, gates in (("byte accounting", c.accounting), ("the hard rules", c.rules),
                         ("untouched regions (TEXEL partition)", c.regions),
                         ("orthogonality", c.orthogonality), ("quality", c.quality)):
        L.append("    -- %s" % title)
        for g in gates:
            L.append("    [%s] %s" % ("ok" if g.ok else "!!", g.name))
            L.append("         %s" % g.detail)
    L.append("")
    L.append("    per-target changed bytes: " + (", ".join(
        "%s %d" % (k, v) for k, v in c.per_target.items()) or "none"))
    L.append("    TOTAL %d bytes of %d (%.4f%%)"
             % (len(c.changed), len(b.orig), 100.0 * len(c.changed) / max(1, len(b.orig))))
    return L
