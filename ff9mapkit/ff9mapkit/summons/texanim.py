r"""THE TEXANIM READER -- the id-5 model image's texel-blit clip table, decoded.  **READ ONLY.**

This module reads the byte range :func:`ff9mapkit.summons.reskin.texanim_region` measures -- the
``[firstBlock, min(motionOffsets))`` span of a summon's creature model image -- and returns it as a
typed table.  It **layers on top of** ``reskin.texanim_region()`` and never re-measures the region
itself: that measurement is the same arithmetic the id-5 loader performs (``header[+0x40] = psx(header
+ firstBlock)``), and the engine's own emptiness predicate keys on it.

THE FORMAT (SYNTHESIS.md sec 1.1-1.3, reconciled from two independent lanes -- a static disassembly of
the shipped ``FF9SpecialEffectPlugin.dll`` and a measurement sweep over the 372-container stock dump
corpus).  Region base = ``SummonData+0x70`` = ``psx(header + firstBlock)``; every offset below is
REGION-RELATIVE::

    u32 clipCount;                     /* +0x00.  3 on ef038, 9 on the ef177 family              */

    struct Clip {                      /* x clipCount, stride 0x14, packed at region+0x04        */
      /*+0x00*/ u8  flags;             /* RUNTIME STATE -- 0 on disk in 24/24 stock records      */
      /*+0x01*/ u8  frameCount;        /* == len(frameList)/4, exact on 39/39 stock clips        */
      /*+0x02*/ u16 rate;              /* OPEN: 8.8 hold-ticks or 1/4096 speed.  Carried only.   */
      /*+0x04*/ u16 paramA;            /* OPEN: the auto-cycle pair, non-zero on ONE clip/table  */
      /*+0x06*/ u16 paramB;            /* OPEN: ditto                                            */
      /*+0x08*/ u32 timer;             /* RUNTIME STATE -- 0 on disk in 24/24                    */
      /*+0x0c*/ u8  unk1;              /* OPEN: constant 1 on all 39 stock clips.  UNREAD.       */
      /*+0x0d*/ u8  partIndex;         /* which creature part's 128x128 page this clip lives in  */
      /*+0x0e*/ u16 scale;             /* RUNTIME STATE -- 0 on disk in 24/24                    */
      /*+0x10*/ u32 nodeOff;           /* region-relative -> Window                              */
    };

    struct Window {                    /* x clipCount, stride 0x0c, packed after the clips       */
      /*+0x00*/ u16 x;                 /* destination, VRAM HALFWORDS  -> texel x = 2*x          */
      /*+0x02*/ u16 y;                 /* destination, page rows                                 */
      /*+0x04*/ u16 w;                 /* width, VRAM HALFWORDS        -> texel w = 2*w          */
      /*+0x06*/ u16 h;                 /* height, rows.  x+w <= 64 halfwords = one page wide.    */
      /*+0x08*/ u32 leafOff;           /* region-relative -> frame list                          */
    };

    /* FRAME LIST: frameCount x { u16 srcX (halfwords); u16 srcY (rows) } -- the source ORIGIN;
       the rect's SIZE is inherited from the clip's own Window. */

and that is why the only two region sizes in the corpus are what they are::

    ef038                        3 clips,  4 frames   4 + 60  + 36  + 16 == 116
    ef177 / ef493 / ef494 / ef495  9 clips, 18 frames   4 + 180 + 108 + 72 == 364

(the four 364-byte regions are byte-identical -- one Carbuncle shipped as four ability rows).  Note
what the sizes do **not** divide by: ``partCount * 0x18``.  ``0x18`` is the x64 *runtime* struct size
(``nodeOff`` widens to a real pointer), the file record is ``0x14``, and the count counts **clips**,
not parts -- so HLE op 12's ``$a1`` is a CLIP index and the affected part is named by ``clip+0x0d``.

WHAT THE TABLE DESCRIBES: a texel blit.  Copy a ``w x h`` rect of 8-bit palette INDICES from
``(srcX, srcY)`` to ``(x, y)`` inside the *same* 128x128 page.  It never binds or writes a CLUT word,
never writes CLUT contents, never touches a UV, and never leaves the part's own page.

REFUSE, DO NOT GUESS -- the validation is the decode
-----------------------------------------------------
:func:`parse_region` rejects any offset that leaves the region, any ``x+w > 64`` halfwords, any
``partIndex >= partCount``, and -- the property that proved the format -- any table whose three
sub-arrays plus the 4-byte count do not tile the region **exactly**: zero slack, zero double-cover.
A table that fails validation is *armed and unread*, which is the pre-W7 state, so every consumer
degrades to the OLD refusal instead of silently passing.  That fallback is part of the API: use
:func:`read`, whose :class:`ReadResult` separates **armed+parsed** from **armed+unparseable**.

Runtime-state fields (``flags`` / ``timer`` / ``scale``) are zero on disk in 24/24 stock records.  The
reader **asserts** that and reports a non-zero one as a WARNING -- the cheapest corruption detector
for a container someone has already patched.  It never normalises one silently.  The OPEN fields
(``rate``, ``paramA``, ``paramB``, ``unk1``) are carried verbatim and are round-trip-exact; nothing
here invents a meaning for them.

THE HARD RULE THIS MODULE EXISTS TO PIN (:data:`REGION_RULE`, SYNTHESIS sec 3 / R1)
-----------------------------------------------------------------------------------
Never resize, relocate or zero the region, and never edit ``firstBlock``.  ``firstBlock ==
motionOffsets[0]`` is a LIVE engine predicate: with a non-empty region the loader hands
``Hi_RegisterSummonModel`` the per-part VRAM page table instead of NULL, which changes what
``summonRecord+0x20..0x51`` holds.  Recolour and repaint work never needs to -- both are in-place
splices -- so honouring it costs nothing.

NO WRITER (SYNTHESIS sec 4.2 / R2).  :func:`encode` exists so the parse can be proven byte-exact and
for nothing else; it is deliberately not reachable from any CLI verb.  There is no consumer of this
table in either build of the plugin beyond three state-byte writes, so no authored edit to it could be
*verified* -- and on x64 the arming op already writes past the record it means to arm.

PROVENANCE: this module carries offsets, strides, field names and rect arithmetic.  It embeds no stock
bytes and no stock rect.  Every corpus number quoted above is a measurement recorded in the W7 lane
dossiers, not data shipped here.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

from . import container as EC
from . import texture as KT

if TYPE_CHECKING:                       # :mod:`reskin` is this module's region SOURCE *and* one of its
    from . import reskin as RS          # consumers, so the runtime import is deferred to the call site

__all__ = [
    "TexAnimError",
    "CLIP_STRIDE", "WINDOW_STRIDE", "FRAME_STRIDE", "COUNT_BYTES", "PAGE_W_HALFWORDS",
    "REGION_RULE",
    "Rect", "Frame", "Clip", "TexAnimTable", "ReadResult",
    "parse", "parse_region", "read", "encode",
    "protected_rects", "protected_groups", "overlap_groups", "page_file_offset",
    "describe",
]

#: on-disk record strides (SYNTHESIS sec 1.1).  ``0x14`` is the FILE record; the x64 runtime row is
#: ``0x18`` because ``nodeOff`` widens to a pointer -- never use the runtime stride on a file.
CLIP_STRIDE = 0x14
WINDOW_STRIDE = 0x0C
FRAME_STRIDE = 4
COUNT_BYTES = 4

#: one 128x128 8bpp page is 64 VRAM halfwords wide; ``x + w <= 64`` holds on 39/39 stock clips and is
#: the measurement that settled the halfword unit (texel agreement 0.905-0.976 vs 0.071-0.341).
PAGE_W_HALFWORDS = KT.PAGE_W // 2

#: the one new hard rule W7 minted.  Quoted verbatim by the gates so the rule and its enforcement can
#: never drift apart.
REGION_RULE = ("never resize, relocate or zero the texanim region, and never edit firstBlock -- "
               "firstBlock == motionOffsets[0] is a live engine predicate that changes "
               "Hi_RegisterSummonModel's arguments")


class TexAnimError(RuntimeError):
    """A malformed texanim region.  Raised, never swallowed inside this module -- callers that need
    the degrade-to-the-old-refusal behaviour call :func:`read` instead of :func:`parse`."""


# ============================================================ (1) the typed table
@dataclass(frozen=True)
class Rect:
    """A rect in **TEXEL** space (one texel = one byte; a row is :data:`ff9mapkit.summons.texture.PAGE_W`
    bytes), page-local to the part its clip names.

    The file stores ``x`` and ``w`` in VRAM HALFWORDS; this type has already doubled them, so ``x`` and
    ``w`` are always even on anything :func:`parse_region` produced.  ``y``/``h`` are rows either way.
    """
    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

    def intersects(self, other: "Rect") -> bool:
        """Strict overlap -- two rects that merely touch along an edge do NOT intersect."""
        return (self.x < other.x2 and other.x < self.x2
                and self.y < other.y2 and other.y < self.y2)

    def texels(self):
        """Every ``(x, y)`` this rect covers -- the unit a co-transform must not apply twice."""
        for yy in range(self.y, self.y2):
            for xx in range(self.x, self.x2):
                yield (xx, yy)

    def __str__(self) -> str:                                    # pragma: no cover - cosmetic
        return "(%d,%d,%d,%d)" % self.as_tuple()


@dataclass(frozen=True)
class Frame:
    """One frame-list entry: a SOURCE ORIGIN, with the size inherited from the clip's own window.

    The file stores only ``(srcX, srcY)`` -- 4 bytes.  ``src`` is that origin already resolved against
    the window's ``(w, h)`` and converted to texel space, which is the only form a repaint can act on.
    """
    index: int
    src: Rect


@dataclass(frozen=True)
class Clip:
    """One 20-byte clip record, its 12-byte window and its frame list, resolved.

    ``rate`` / ``param_a`` / ``param_b`` / ``unk1`` are **OPEN** (SYNTHESIS sec 1.2): carried verbatim,
    round-trip exact, no semantics invented.  ``flags`` / ``timer`` / ``scale`` are RUNTIME STATE and
    are zero on disk in every stock record -- a non-zero one is surfaced as a table warning, not
    normalised away.
    """
    index: int
    part: int
    frames: int                          # frameCount as stored; == len(sources)
    rate: int                            # OPEN
    param_a: int                         # OPEN
    param_b: int                         # OPEN
    window: Rect                         # TEXEL space
    sources: Tuple[Rect, ...]            # TEXEL space, one per frame, size inherited from `window`
    flags: int                           # RUNTIME STATE, 0 on disk
    timer: int                           # RUNTIME STATE, 0 on disk
    scale: int                           # RUNTIME STATE, 0 on disk
    unk1: int                            # OPEN, constant 1 corpus-wide
    node_off: int                        # region-relative, as stored (carried for the round trip)
    leaf_off: int                        # region-relative, as stored

    @property
    def frame_list(self) -> Tuple[Frame, ...]:
        """The per-frame view of :attr:`sources` (the sec 5.1 sketch's ``Frame``)."""
        return tuple(Frame(index=i, src=r) for i, r in enumerate(self.sources))

    @property
    def rects(self) -> Tuple[Rect, ...]:
        """Every texel rect this clip touches: its live window plus every source it blits from."""
        return (self.window,) + tuple(self.sources)


@dataclass(frozen=True)
class TexAnimTable:
    """A fully decoded, exactly-tiling texanim region."""
    count: int
    clips: Tuple[Clip, ...]
    #: the ``reskin.TexAnim`` measurement this table was read out of -- ``None`` for a raw-region parse
    region: Optional["RS.TexAnim"]
    nbytes: int
    part_count: Optional[int]
    #: always ``b""`` -- the exact-tiling law leaves no slack.  The field exists so that a future shape
    #: which legitimately carries trailing bytes would be a visible object rather than a silent
    #: truncation in the round trip.
    trailing: bytes = b""
    #: non-fatal observations (non-zero runtime state, an out-of-page rect).  Never auto-corrected.
    warnings: Tuple[str, ...] = ()

    @property
    def parts(self) -> Tuple[int, ...]:
        """The distinct part indices this table animates, ascending."""
        return tuple(sorted({c.part for c in self.clips}))

    @property
    def frame_total(self) -> int:
        return sum(c.frames for c in self.clips)


@dataclass(frozen=True)
class ReadResult:
    """THE FALLBACK CONTRACT, as an object.

    Three states, and a consumer must handle all three:

    * ``not armed``        -- the region is empty; nothing to protect, nothing to refuse.
    * ``parsed``           -- armed AND decoded; ``table`` is authoritative and the lift is available.
    * ``unparseable``      -- armed and NOT decoded; ``error`` says why.  This is the pre-W7 state and
      the ONLY correct response is the pre-W7 refusal.  An unknown future shape degrades here instead
      of silently passing.
    """
    region: Optional["RS.TexAnim"]       # present / armed / nbytes / lo / hi
    table: Optional[TexAnimTable] = None
    error: Optional[str] = None

    @property
    def present(self) -> bool:
        return bool(getattr(self.region, "present", False))

    @property
    def armed(self) -> bool:
        return bool(getattr(self.region, "armed", False))

    @property
    def parsed(self) -> bool:
        return self.armed and self.table is not None

    @property
    def unparseable(self) -> bool:
        return self.armed and self.table is None

    @property
    def warnings(self) -> Tuple[str, ...]:
        return self.table.warnings if self.table is not None else ()


# ============================================================ (2) the coverage proof
class _Coverage:
    """Every byte of the region, claimed exactly once -- the property that proved the format.

    This is not a bookkeeping convenience: a walk that tiles the region with zero slack and zero
    double-cover is the whole evidence that the three strides (20 / 12 / 4) are right.  Enforcing it
    at parse time is what makes the decoder refuse a shape it does not actually understand.
    """

    def __init__(self, n: int) -> None:
        self.n = n
        self.owner: List[Optional[str]] = [None] * n

    def claim(self, off: int, nbytes: int, what: str) -> None:
        if off < 0 or nbytes < 0 or off + nbytes > self.n:
            raise TexAnimError(
                "%s claims region[%#x..%#x) which LEAVES the %d-byte region -- refusing to read past "
                "the span the loader itself measures" % (what, off, off + nbytes, self.n))
        for i in range(off, off + nbytes):
            if self.owner[i] is not None:
                raise TexAnimError(
                    "%s claims region[%#x] which %s already claimed -- the sub-arrays must tile the "
                    "region exactly (zero double-cover); this is not the format"
                    % (what, i, self.owner[i]))
            self.owner[i] = what

    def unclaimed(self) -> List[int]:
        return [i for i, o in enumerate(self.owner) if o is None]


def _u8(b: bytes, o: int) -> int: return b[o]
def _u16(b: bytes, o: int) -> int: return struct.unpack_from("<H", b, o)[0]
def _u32(b: bytes, o: int) -> int: return struct.unpack_from("<I", b, o)[0]


# ============================================================ (3) the reader
def parse_region(data: bytes, part_count: Optional[int],
                 region: Optional["RS.TexAnim"] = None) -> TexAnimTable:
    """Decode ONE texanim region's bytes.  Raises :class:`TexAnimError` on anything malformed.

    ``part_count`` is the creature package's own ``partCount``; pass ``None`` only when it is genuinely
    unknown, which costs the ``partIndex`` bound check and says so in a warning.  ``region`` is carried
    through onto the table untouched (the ``reskin.TexAnim`` measurement, when there is one).
    """
    n = len(data)
    if n < COUNT_BYTES:
        raise TexAnimError("region is %d bytes -- too short to hold even the u32 clip count" % n)

    cov = _Coverage(n)
    cov.claim(0, COUNT_BYTES, "clipCount")
    count = _u32(data, 0)
    if count <= 0:
        raise TexAnimError(
            "clipCount is %d but the region is %d bytes long -- an armed region always carries at "
            "least one clip" % (count, n))
    need = COUNT_BYTES + CLIP_STRIDE * count
    if need > n:
        raise TexAnimError(
            "clipCount %d needs %d bytes of clip records (4 + 0x14*%d) but the region is only %d"
            % (count, need, count, n))

    warnings: List[str] = []
    if part_count is None:
        warnings.append("partCount unknown: the partIndex bound check was SKIPPED")

    # --- level 1: the clip records, packed at region+4 -------------------------------------------
    raw: List[dict] = []
    for i in range(count):
        off = COUNT_BYTES + CLIP_STRIDE * i
        cov.claim(off, CLIP_STRIDE, "clip %d" % i)
        c = dict(index=i, flags=_u8(data, off), frames=_u8(data, off + 1),
                 rate=_u16(data, off + 2), param_a=_u16(data, off + 4),
                 param_b=_u16(data, off + 6), timer=_u32(data, off + 8),
                 unk1=_u8(data, off + 0x0C), part=_u8(data, off + 0x0D),
                 scale=_u16(data, off + 0x0E), node_off=_u32(data, off + 0x10))
        if c["frames"] <= 0:
            raise TexAnimError("clip %d declares %d frames -- a clip with no frame list cannot be "
                               "expressed by this format" % (i, c["frames"]))
        if part_count is not None and c["part"] >= part_count:
            raise TexAnimError(
                "clip %d names part %d but the creature package declares partCount %d -- the clip "
                "cannot address a page that does not exist" % (i, c["part"], part_count))
        for fld, val in (("flags", c["flags"]), ("timer", c["timer"]), ("scale", c["scale"])):
            if val:
                warnings.append(
                    "clip %d: %s = %#x -- RUNTIME STATE, zero on disk in 24/24 stock records.  A "
                    "non-zero value means these bytes were written after they were authored.  "
                    "Carried verbatim, NOT normalised." % (i, fld, val))
        raw.append(c)

    # --- level 2: the destination windows --------------------------------------------------------
    for c in raw:
        off = c["node_off"]
        cov.claim(off, WINDOW_STRIDE, "clip %d window" % c["index"])
        x, y, w, h = (_u16(data, off), _u16(data, off + 2), _u16(data, off + 4), _u16(data, off + 6))
        if x + w > PAGE_W_HALFWORDS:
            raise TexAnimError(
                "clip %d window x+w == %d halfwords > %d -- the rect leaves the part's own 128x128 "
                "page, which no stock clip does (39/39)"
                % (c["index"], x + w, PAGE_W_HALFWORDS))
        c["leaf_off"] = _u32(data, off + 8)
        c["window"] = Rect(2 * x, y, 2 * w, h)
        if y + h > KT.PAGE_H:
            warnings.append("clip %d window %s runs past row %d of its page"
                            % (c["index"], c["window"], KT.PAGE_H))

    # --- level 3: the frame lists ----------------------------------------------------------------
    for c in raw:
        off = c["leaf_off"]
        cov.claim(off, FRAME_STRIDE * c["frames"], "clip %d frames" % c["index"])
        win: Rect = c["window"]
        srcs: List[Rect] = []
        for j in range(c["frames"]):
            sx, sy = _u16(data, off + 4 * j), _u16(data, off + 4 * j + 2)
            if sx * 2 + win.w > KT.PAGE_W:
                raise TexAnimError(
                    "clip %d frame %d source x+w == %d texels > %d -- the source rect leaves the "
                    "part's own page" % (c["index"], j, sx * 2 + win.w, KT.PAGE_W))
            r = Rect(2 * sx, sy, win.w, win.h)
            if r.y2 > KT.PAGE_H:
                warnings.append("clip %d frame %d source %s runs past row %d of its page"
                                % (c["index"], j, r, KT.PAGE_H))
            srcs.append(r)
        c["sources"] = tuple(srcs)

    # --- the tiling proof ------------------------------------------------------------------------
    left = cov.unclaimed()
    if left:
        raise TexAnimError(
            "%d of %d region bytes are unclaimed (first at %#x) -- the three sub-arrays must tile the "
            "region EXACTLY (zero slack); an unexplained byte means this is not the format"
            % (len(left), n, left[0]))

    clips = tuple(Clip(index=c["index"], part=c["part"], frames=c["frames"], rate=c["rate"],
                       param_a=c["param_a"], param_b=c["param_b"], window=c["window"],
                       sources=c["sources"], flags=c["flags"], timer=c["timer"], scale=c["scale"],
                       unk1=c["unk1"], node_off=c["node_off"], leaf_off=c["leaf_off"])
                  for c in raw)
    return TexAnimTable(count=count, clips=clips, region=region, nbytes=n, part_count=part_count,
                        trailing=b"", warnings=tuple(warnings))


def parse(blob: bytes) -> Optional[TexAnimTable]:
    """Decode a container's texanim table.

    ``None`` when the container has no creature package or its region is EMPTY (19 of the corpus's 24
    creature packages).  Raises :class:`TexAnimError` when the region is armed but does not decode --
    a caller that must not raise uses :func:`read`.
    """
    from . import reskin as RS                     # deferred: reskin is also this module's CONSUMER

    ta = RS.texanim_region(blob)
    if ta is None or not ta.armed:
        return None
    mp = EC.creature_package(blob)
    part_count = mp.part_count if mp is not None else None
    return parse_region(blob[ta.lo:ta.hi], part_count, region=ta)


def read(blob: bytes) -> ReadResult:
    """:func:`parse` with the failure turned into a value -- the form a GATE consumes.

    An armed region that does not decode comes back as ``unparseable``, which every consumer must
    treat as the pre-W7 "armed and unread" state and refuse exactly as it did before W7.  The lift is
    conditional on a successful parse; it is never conditional on the absence of an exception.

    No table-level failure escapes.  The one thing that still propagates is a failure to MEASURE the
    region at all (a container so malformed that ``reskin.texanim_region`` itself raises) -- swallowing
    that would report ``armed = False``, i.e. "nothing to protect", about a container nobody could
    read, and every pre-W7 caller already raised there.
    """
    from . import reskin as RS                     # deferred, as in parse()

    ta = RS.texanim_region(blob)
    if ta is None or not ta.armed:
        return ReadResult(region=ta, table=None, error=None)
    try:
        return ReadResult(region=ta, table=parse(blob), error=None)
    except TexAnimError as exc:
        return ReadResult(region=ta, table=None, error=str(exc))
    except Exception as exc:                        # a truncated/garbled blob must not crash a gate
        return ReadResult(region=ta, table=None, error="%s: %s" % (type(exc).__name__, exc))


# ============================================================ (4) the round-trip proof (R2: no writer)
def encode(table: TexAnimTable) -> bytes:
    """Re-emit a table as region bytes.

    **This exists for the round-trip test and for nothing else** (SYNTHESIS sec 4.2, R2): there is no
    consumer of this table in the engine, so no authored edit to it could be verified, and no CLI verb
    reaches this function.  Its job is to prove the reader claimed every byte for the right reason.

    Each record is written at the offset the file itself stored, into a buffer the region's own length,
    so a table whose sub-records are ordered unusually round-trips as faithfully as a canonical one.
    """
    buf = bytearray(table.nbytes)
    struct.pack_into("<I", buf, 0, table.count)
    if len(table.clips) != table.count:
        raise TexAnimError("table declares %d clips but carries %d" % (table.count, len(table.clips)))
    for i, c in enumerate(table.clips):
        off = COUNT_BYTES + CLIP_STRIDE * i
        struct.pack_into("<BBHHHIBBHI", buf, off, c.flags, c.frames, c.rate, c.param_a, c.param_b,
                         c.timer, c.unk1, c.part, c.scale, c.node_off)
        for r, what in ((c.window, "window"),) + tuple((s, "source") for s in c.sources):
            if r.x % 2 or r.w % 2:
                raise TexAnimError(
                    "clip %d %s %s has an odd texel x or w -- the file stores those in VRAM "
                    "HALFWORDS, so an odd value cannot be represented" % (i, what, r))
        struct.pack_into("<HHHHI", buf, c.node_off, c.window.x // 2, c.window.y, c.window.w // 2,
                         c.window.h, c.leaf_off)
        if len(c.sources) != c.frames:
            raise TexAnimError("clip %d declares %d frames but carries %d source rects"
                               % (i, c.frames, len(c.sources)))
        for j, s in enumerate(c.sources):
            struct.pack_into("<HH", buf, c.leaf_off + FRAME_STRIDE * j, s.x // 2, s.y)
    if table.trailing:
        buf[len(buf) - len(table.trailing):] = table.trailing
    return bytes(buf)


# ============================================================ (5) the protected rect set
def page_file_offset(blob: bytes, part: int) -> int:
    """Absolute file offset of part ``part``'s 128x128 8bpp page -- ``tex_file_offset + part*0x4000``.

    One texel is one byte and one row is :data:`ff9mapkit.summons.texture.PAGE_W` bytes, so a
    :class:`Rect` addresses ``page + y*PAGE_W + x``.
    """
    mp = EC.creature_package(blob)
    if mp is None:
        raise TexAnimError("this container carries no creature package")
    if not 0 <= part < mp.part_count:
        raise TexAnimError("part %d is outside this package's %d parts" % (part, mp.part_count))
    return mp.tex_file_offset + part * KT.PAGE_BYTES


def protected_rects(blob: bytes) -> Dict[int, List[Rect]]:
    """``{part: [rect, ...]}`` -- every texel rect a running texanim would read or write, TEXEL space.

    The set is the union of every clip's live window and every frame it can blit from.  A localised
    texel repaint that intersects any of these must co-transform them all (SYNTHESIS sec 4.1, L4);
    a whole-page repaint co-transforms them by construction.

    ``{}`` when the region is EMPTY.  **Raises when the region is armed but does not decode** -- an
    empty dict there would read as "nothing to protect", which is the one wrong answer; an armed and
    unread region is a refusal, not a clean bill of health.
    """
    res = read(blob)
    if not res.armed:
        return {}
    if res.table is None:
        raise TexAnimError(
            "TEXANIM ARMED (%d bytes) and the table does NOT decode, so its protected rect set is "
            "unknown: %s" % (getattr(res.region, "nbytes", 0), res.error))
    return _rects_by_part(res.table)


def _rects_by_part(table: TexAnimTable) -> Dict[int, List[Rect]]:
    """``{part: [rect, ...]}``, DE-DUPLICATED and sorted.  Clips share windows and re-use frames
    heavily (the Carbuncle table's 9 clips name 2 windows and 7 distinct sources), so the set matters
    and the multiset does not."""
    out: Dict[int, List[Rect]] = {}
    for c in table.clips:
        seen = out.setdefault(c.part, [])
        for r in c.rects:
            if r not in seen:
                seen.append(r)
    return {p: sorted(rs, key=lambda r: r.as_tuple()) for p, rs in sorted(out.items())}


def overlap_groups(rects: Sequence[Rect]) -> List[List[Rect]]:
    """Partition rects into transitively OVERLAPPING groups -- the co-transform UNITS.

    The co-transform law, made mechanical: the Carbuncle mouth-closed frames differ by exactly one row
    and share texels, so applying a per-texel transform to each of them independently would apply it
    TWICE to the shared texels.  Everything in one group must be transformed as one pass over the
    union of its texels.  Rects that merely touch along an edge share nothing and stay apart.

    A GROUP, deliberately, and not a bounding box: the box of an overlapping group covers texels that
    are not protected at all (on the Carbuncle strip it would sweep in 500+ of them), and transforming
    those would be a repaint the author never asked for.
    """
    groups: List[List[Rect]] = []
    for r in sorted(rects, key=lambda r: r.as_tuple()):
        merged, rest = [r], []
        changed = True
        while changed:                # absorbing one group can bring the pile into contact with more
            changed, rest = False, []
            for g in groups:
                if any(a.intersects(b) for a in g for b in merged):
                    merged, changed = merged + g, True
                else:
                    rest.append(g)
            groups = rest
        groups.append(sorted(merged, key=lambda r: r.as_tuple()))
    return sorted(groups, key=lambda g: g[0].as_tuple())


def protected_groups(blob: bytes) -> Dict[int, List[List[Rect]]]:
    """:func:`protected_rects` partitioned per part into :func:`overlap_groups` -- what L4 transforms."""
    return {p: overlap_groups(rs) for p, rs in protected_rects(blob).items()}


# ============================================================ (6) the readout (L6: pure disclosure)
def describe(blob: bytes) -> List[str]:
    """The readout lines for the scaffold / survey / ``--explain`` writers (L6 -- pure disclosure).

    Reports an undecodable table as ARMED-and-unread rather than failing: a readout is what an author
    reads BEFORE a gate fires, so it has to survive exactly the containers the gate is about to refuse.
    Carries the same caveat as :func:`read` for a container whose region cannot be measured at all.
    """
    res = read(blob)
    L = ["  THE TEXANIM TABLE (the id-5 model image's texel-blit clip table)"]
    ta = res.region
    if ta is None or not res.present:
        L.append("    no id-4 creature package")
        return L
    if not res.armed:
        L.append("    region is EMPTY (firstBlock == motionOffsets[0]) -- nothing is animated")
        return L
    span = "%d bytes at %#x..%#x" % (ta.nbytes, ta.lo, ta.hi)
    if res.table is None:
        L.append("    ARMED (%s) but UNPARSEABLE -- treated as armed-and-unread" % span)
        L.append("      %s" % res.error)
        L.append("    RULE  %s" % REGION_RULE)
        return L

    t = res.table
    L.append("    ARMED (%s): %d clip(s) over part(s) %s of %s"
             % (span, t.count, ", ".join(str(p) for p in t.parts),
                "?" if t.part_count is None else str(t.part_count)))
    for c in t.clips:
        L.append("      clip %-2d part %d  %d frame(s)  rate %#06x  param %d/%d  window %s <- %s"
                 % (c.index, c.part, c.frames, c.rate, c.param_a, c.param_b, c.window,
                    " ".join(str(s) for s in c.sources)))
    L.append("      (rate / param / the constant-1 byte are OPEN -- carried verbatim, not interpreted)")
    prot = {p: overlap_groups(rs) for p, rs in _rects_by_part(t).items()}
    L.append("    THE PROTECTED RECT SET (texel space; [] groups OVERLAP and co-transform as one)")
    for p in sorted(prot):
        L.append("      part %d @ page %s: %s"
                 % (p, _page_or_unknown(blob, p),
                    " ".join("[%s]" % " ".join(str(r) for r in g) if len(g) > 1 else str(g[0])
                             for g in prot[p])))
    for w in t.warnings:
        L.append("    WARNING  %s" % w)
    L.append("    RULE  %s" % REGION_RULE)
    return L


def _page_or_unknown(blob: bytes, part: int) -> str:
    try:
        return "%#x" % page_file_offset(blob, part)
    except TexAnimError:                                        # pragma: no cover - defensive
        return "?"
