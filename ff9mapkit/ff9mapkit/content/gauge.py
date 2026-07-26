"""``[[gauge]]`` -- a background-art value bar, the DLL-free tile gauge.

FF9 has no gauge opcode (the minigame-UI survey headline); what it HAS is the
tile vocabulary: a scene ``ANIMATION`` is a list of TARGET overlays, and
``SetTileAnimationFrame`` (0xE7, ``EBG_animShowFrame``) activates exactly the
overlay whose frame index matches -- out-of-range (255) hides them all. So a
gauge is: ``segments+1`` build-generated fill-state PNGs appended as
pure-Memoria overlays + one script-controlled (``Loop``-less = ``SingleFrame``)
ANIMATION over them, driven by ONE opcode per tick from a looping daemon entry.

Goldens (all engine-source or stock-bytes verified this arc):
  * ``BGSCENE_DEF.ReadMemoriaBGS`` -- the OVERLAY/ANIMATION ``.bgx`` schema;
    ``USE_BASE_SCENE`` loads the donor atlas+EBG first, appended blocks index
    after the donor's own counts (``handleOverlays`` renders the hybrid).
  * ``FieldMap.EBG_animShowFrame`` -- frame *i* shows ``frameList[i].target``.
  * Field 64 (``test2_15`` Code1): the Sin-pulse daemon, carried VERBATIM --
    ``allocate 2``; ``loc1 += 1; loc0 = Sin(loc1 << 2)/360 + 144;
    SetTileColor(t, loc0, loc0, loc0); Wait(1); loop``. Locals live in the
    entry-table ``loc`` byte (``Obj.ctor`` sizes the var area from it), read
    as ``Instance.Byte[i]`` -- the daemon is the kit's first loc>0 mint.
  * ``EBG_overlaySetShadeColor`` -- rgb/128 on the overlay material (128 =
    neutral); Memoria overlays own a MeshRenderer, so the shade path applies.

The daemon is ONE seated entry for ALL gauges (ticker-shaped: single tag-0
function, internal ``Wait(1)`` loop, armed by ``init_code``), and the level is
computed INLINE in the opcode's expression arg -- no global scratch at all, so
``[[gauge]]`` coexists with ``[behavior]`` (fort condor's HUD wants both).

The bar is authored in CANVAS pixels (the ``[[layers]]`` frame) and is WORLD
anchored -- scene furniture like every stock tile, not a floating HUD (the
engine's ScreenAnchored flag lives inside the sprite-loop machinery and does
not generalize to Memoria overlays). Single-screen minigame arenas are the
target; on scrolling fields the bar stays where the art is.
"""
from __future__ import annotations

import io
import struct
from dataclasses import dataclass

from ..eb import exprasm, opcodes
from ..eb.labelasm import JMP, JMP_IFNOT, asm, label

GAUGE_TAG = 0                     # the daemon's single function tag (ticker shape)
LOC_SHADE = 0                     # Instance.Byte[0] -- computed shade (stock Code1 loc0)
LOC_PHASE = 1                     # Instance.Byte[1] -- tick counter   (stock Code1 loc1)
LOC_BYTES = 2                     # the entry-table loc byte: stock's `allocate 2`
HIDE_FRAME = 255                  # out-of-range frame = every target overlay off
SHADE_NEUTRAL = 128               # EBG_overlaySetShadeColor: rgb/128 = 1.0

SEG_MIN, SEG_MAX = 2, 24
_KEYS = {"name", "source", "max", "segments", "pos", "width", "height",
         "color", "back_color", "depth", "pulse_below", "requires_flag", "camera"}


class GaugeError(ValueError):
    pass


@dataclass(frozen=True)
class GaugeSpec:
    """One ``[[gauge]]``, validated + resolved. ``source`` is canonical:
    ``global:<byteoff>`` (a save-backed ``Global.Int16``), ``item:<id>``
    (live inventory count), or ``gil``. ``max`` maps the value onto
    ``segments`` cells (value >= max = full; negatives clamp to empty)."""
    name: str
    source: str
    max: int
    segments: int = 10
    pos: tuple = (24, 24)             # canvas px, top-left of the bar
    width: int = 96                   # art size in canvas px
    height: int = 10
    color: tuple = (64, 200, 255)     # filled-cell RGB
    back_color: tuple = (42, 42, 58)  # empty-cell RGB
    depth: int = 1                    # overlay z: smaller = nearer the camera
    pulse_below: int = 0              # level <= this -> the field-64 shimmer (0 = off)
    requires_flag: int | None = None  # GLOB bit; CLEAR -> the whole bar hides
    camera: int = 0                   # which scene camera shows it


def _color(v, ctx: str, key: str, default: tuple) -> tuple:
    if v is None:
        return default
    if isinstance(v, str) and len(v.lstrip("#")) == 6:
        s = v.lstrip("#")
        try:
            return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            pass
    if isinstance(v, list) and len(v) == 3 and all(isinstance(c, int) and 0 <= c <= 255 for c in v):
        return tuple(v)
    raise GaugeError(f"{ctx}: {key} must be \"#rrggbb\" or [r, g, b]")


def from_raw(block: dict, idx: int, *, resolve_item=None) -> GaugeSpec:
    ctx = f"[[gauge]] #{idx}"
    extra = set(block) - _KEYS
    if extra:
        raise GaugeError(f"{ctx}: unknown key(s) {sorted(extra)}")
    name = block.get("name")
    if not isinstance(name, str) or not name.strip():
        raise GaugeError(f"{ctx}: needs a name")
    ctx = f"[[gauge]] {name!r}"

    src = block.get("source")
    if not isinstance(src, str) or not src.strip():
        raise GaugeError(f"{ctx}: needs a source — \"global:<byteoff>\" (a save-backed "
                         f"Global.Int16 your script writes), \"item:<name-or-id>\" "
                         f"(live inventory count), or \"gil\"")
    src = src.strip()
    if src == "gil":
        pass
    elif src.startswith("global:"):
        try:
            off = int(src.split(":", 1)[1])
        except ValueError:
            off = -1
        if not 4 <= off <= 2016:
            raise GaugeError(f"{ctx}: global source byte offset must be 4..2016 "
                             f"(2018+ is kit modal scratch / the co-op cells)")
        src = f"global:{off}"
    elif src.startswith("item:"):
        sel = src.split(":", 1)[1]
        try:
            iid = int(sel)
        except ValueError:
            if resolve_item is None:
                raise GaugeError(f"{ctx}: item source {sel!r} needs name resolution "
                                 f"(pass a numeric item id)")
            try:
                iid = int(resolve_item(sel))
            except Exception:
                raise GaugeError(f"{ctx}: item {sel!r} did not resolve to an id")
        if not 0 <= iid <= 255:
            raise GaugeError(f"{ctx}: item id must be 0..255")
        src = f"item:{iid}"
    else:
        raise GaugeError(f"{ctx}: unknown source {src!r} — use \"global:<byteoff>\", "
                         f"\"item:<name-or-id>\", or \"gil\"")

    mx = block.get("max")
    if not isinstance(mx, int) or mx < 1:
        raise GaugeError(f"{ctx}: max must be a positive int (the value that reads FULL)")
    seg = block.get("segments", 10)
    if not isinstance(seg, int) or not SEG_MIN <= seg <= SEG_MAX:
        raise GaugeError(f"{ctx}: segments must be {SEG_MIN}..{SEG_MAX}")
    pos = block.get("pos", [24, 24])
    if not (isinstance(pos, list) and len(pos) == 2
            and all(isinstance(c, int) for c in pos)):
        raise GaugeError(f"{ctx}: pos must be [x, y] canvas pixels")
    w = block.get("width", 96)
    h = block.get("height", 10)
    if not isinstance(w, int) or not isinstance(h, int) or h < 4 or w < 2 + 2 * seg + (seg - 1):
        raise GaugeError(f"{ctx}: width/height too small — need height >= 4 and "
                         f"width >= {2 + 2 * seg + (seg - 1)} for {seg} cells "
                         f"(2px border + 2px cells + 1px gaps)")
    depth = block.get("depth", 1)
    if not isinstance(depth, int) or depth < 0:
        raise GaugeError(f"{ctx}: depth must be >= 0 (smaller = nearer the camera)")
    pb = block.get("pulse_below", 0)
    if not isinstance(pb, int) or not 0 <= pb <= seg:
        raise GaugeError(f"{ctx}: pulse_below must be 0..segments")
    rf = block.get("requires_flag")
    if rf is not None and not (isinstance(rf, int) and 0 <= rf <= 16383):
        raise GaugeError(f"{ctx}: requires_flag must be a gEventGlobal BIT index")
    cam = block.get("camera", 0)
    if not isinstance(cam, int) or not 0 <= cam <= 7:
        raise GaugeError(f"{ctx}: camera must be 0..7")
    return GaugeSpec(
        name=name.strip(), source=src, max=mx, segments=seg,
        pos=(pos[0], pos[1]), width=w, height=h,
        color=_color(block.get("color"), ctx, "color", GaugeSpec.color),
        back_color=_color(block.get("back_color"), ctx, "back_color", GaugeSpec.back_color),
        depth=depth, pulse_below=pb, requires_flag=rf, camera=cam)


# ------------------------------------------------------------------- the art
def png_name(spec: GaugeSpec, k: int) -> str:
    return f"gauge_{spec.name}_{k:02d}.png"


def art_pngs(spec: GaugeSpec) -> list:
    """``[(filename, png_bytes)]`` for fill states 0..segments. Each state is a
    complete self-backed bar (plate + cells) so the ANIMATION's one-visible-frame
    swap needs no separate backplate overlay and frame 255 hides the WHOLE bar.
    Flat PSX-flavored cells: 1px black border, dark plate, per-cell top bevel."""
    from PIL import Image, ImageDraw

    w, h, seg = spec.width, spec.height, spec.segments
    inner = w - 2 - (seg - 1)                 # px available to the cells
    base_cw = inner // seg
    extras = inner - base_cw * seg            # leftmost cells get the remainder px
    fill, back = tuple(spec.color), tuple(spec.back_color)
    bevel = tuple(min(255, c + 70) for c in fill)
    out = []
    for k in range(seg + 1):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, w - 1, h - 1], fill=(12, 12, 20, 235), outline=(0, 0, 0, 255))
        x = 1
        for i in range(seg):
            cw = base_cw + (1 if i < extras else 0)
            c = fill if i < k else back
            d.rectangle([x, 1, x + cw - 1, h - 2], fill=c + (255,))
            if i < k:
                d.line([x, 1, x + cw - 1, 1], fill=bevel + (255,))
            x += cw + 1
        buf = io.BytesIO()
        im.save(buf, "PNG")
        out.append((png_name(spec, k), buf.getvalue()))
    return out


# ------------------------------------------------------------------- the .bgx blocks
def overlay_blocks(spec: GaugeSpec):
    """The ``segments+1`` fill-state OVERLAY blocks, in frame order (0 = empty)."""
    from ..scene import bgx as _bgx
    return [_bgx.Overlay(image=png_name(spec, k),
                         position=(spec.pos[0], spec.pos[1], spec.depth),
                         size=(spec.width, spec.height), camera_id=spec.camera)
            for k in range(spec.segments + 1)]


def animation_block(spec: GaugeSpec, overlay_base: int):
    """The script-controlled (``SingleFrame``) selector over those overlays."""
    from ..scene import bgx as _bgx
    return _bgx.Animation(overlays=list(range(overlay_base, overlay_base + spec.segments + 1)),
                          camera_id=spec.camera)


# ------------------------------------------------------------------- the .eb daemon
def _stmt(text: str) -> bytes:
    return bytes([0x05]) + exprasm.assemble(text + " B_EXPR_END")


def source_expr(spec: GaugeSpec) -> str:
    if spec.source == "gil":
        return "B_SYSVAR[6]"                              # stock's live-gil read
    kind, _, val = spec.source.partition(":")
    if kind == "item":
        return f"const({int(val)}) B_HAVE_ITEM"           # live inventory count
    return f"Global.Int16[{int(val)}]"


def level_expr(spec: GaugeSpec) -> str:
    """``clamp(value * segments / max, 0, segments)`` as a PURE (branch-free)
    expression, computable inline in an opcode arg: ``min(a,b) = a-(a>b)*(a-b)``
    then ``max(x,0) = x*(x>0)`` (comparisons push 1/0; eval is Int24-wide, so
    value*segments cannot overflow)."""
    v, s, m = source_expr(spec), spec.segments, spec.max
    raw = f"{v} const({s}) B_MULT const({m}) B_DIV"
    mn = f"{raw} {raw} const({s}) B_GT {raw} const({s}) B_MINUS B_MULT B_MINUS"
    return f"{mn} {mn} const(0) B_GT B_MULT"


def _frame_expr(spec: GaugeSpec) -> bytes:
    return exprasm.assemble(level_expr(spec) + " B_EXPR_END")


def _visible_overlay_expr(spec: GaugeSpec, overlay_base: int) -> bytes:
    return exprasm.assemble(f"const({overlay_base}) {level_expr(spec)} B_PLUS B_EXPR_END")


def daemon_body(resolved: list) -> bytes:
    """The one-entry gauge daemon: per tick, one ``SetTileAnimationFrame`` per
    gauge (the hide branch on a clear ``requires_flag``), the field-64 shade
    pulse on low gauges, ``Wait(1)``, loop. ``resolved``: a list of
    ``(spec, anim_id, overlay_base)``. Locals per stock Code1 (``allocate 2``):
    ``Instance.Byte[0]`` = shade, ``Instance.Byte[1]`` = phase counter."""
    any_pulse = any(g.pulse_below for g, _a, _b in resolved)
    B: list = [label("top")]
    if any_pulse:
        # field 64 Code1_Loop, verbatim: loc1 += 1; loc0 = Sin(loc1 << 2)/360 + 144
        B.append(_stmt(f"Instance.Byte[{LOC_PHASE}] Instance.Byte[{LOC_PHASE}] "
                       f"const(1) B_PLUS B_LET"))
        B.append(_stmt(f"Instance.Byte[{LOC_SHADE}] Instance.Byte[{LOC_PHASE}] "
                       f"const(2) B_SHIFT_LEFT B_SIN const(360) B_DIV "
                       f"const(144) B_PLUS B_LET"))
    for i, (g, anim, base) in enumerate(resolved):
        if g.requires_flag is not None:
            B.append(_stmt(f"Global.Bit[{g.requires_flag}]"))
            B.append((JMP_IFNOT, f"hide{i}"))
        B.append(opcodes.encode(0xE7, anim, _frame_expr(g), arg_flags=0b10))
        if g.pulse_below:
            ovl = _visible_overlay_expr(g, base)
            sh = exprasm.assemble(f"Instance.Byte[{LOC_SHADE}] B_EXPR_END")
            B.append(_stmt(f"{level_expr(g)} const({g.pulse_below}) B_LE"))
            B.append((JMP_IFNOT, f"calm{i}"))
            B.append(opcodes.encode(0x59, ovl, sh, sh, sh, arg_flags=0b1111))
            B.append((JMP, f"next{i}"))
            B.append(label(f"calm{i}"))
            B.append(opcodes.encode(0x59, ovl, SHADE_NEUTRAL, SHADE_NEUTRAL,
                                    SHADE_NEUTRAL, arg_flags=0b0001))
            B.append(label(f"next{i}"))
        if g.requires_flag is not None:
            B.append((JMP, f"seen{i}"))
            B.append(label(f"hide{i}"))
            B.append(opcodes.encode(0xE7, anim, HIDE_FRAME))
            B.append(label(f"seen{i}"))
    B.append(opcodes.wait(1))
    B.append((JMP, "top"))
    B.append(opcodes.RETURN)
    return asm(B)


def entry_bytes(resolved: list) -> bytes:
    """The seated daemon entry (the behavior-ticker shape: type 0, ONE tag-0
    function, internal loop). Seat with ``loc=LOC_BYTES`` and arm with
    ``init_code(slot, 0)``."""
    return bytes([0x00, 0x01]) + struct.pack("<HH", GAUGE_TAG, 4) + daemon_body(resolved)
