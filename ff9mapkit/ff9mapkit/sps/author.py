"""``[[sps]]`` -- author a NEW from-scratch field particle effect (Tier 2 creator), NO DLL.

A ``[[sps]]`` block defines a brand-new effect: its GEOMETRY (a clone of an existing donor effect, re-authored;
or a fully inline quad cloud via :func:`codec.build`) over a REUSED / BORROWED ``spt.tcb`` texture. This is
**Route A** -- the new effect's ``tpage``/``clut``/UVs index pixels that already exist in some field's texture,
so it draws purely from the TCB already in VRAM (``CommonSPSSystem.SetupSPSTexture`` falls through to the TCB for
any id not in the hardcoded ``SPSConst.SPSTexture`` dict). Guaranteed no-DLL.

The build writes ``<id>.sps.bytes`` + supplies the ``spt.tcb`` into ``FieldMaps/<FBG>/`` (``build._write_authored_sps``)
and emits a ``RunSPSCode`` create+place trigger into the field's ``.eb`` (``content/sps_trigger.py``) so the effect
spawns on field load. **Route B** (a custom PNG for genuinely NEW art) needs a Memoria patch -- the spsId->texture
map is a hardcoded engine dict with no data hook -- so a ``texture = { png = ... }`` block is rejected with that
pointer. -> [[project-ff9-sps-authoring]], docs/SPS.md.

Schema (``field.toml``)::

    # Clone a real donor effect's texture + colours, re-author the animation (the easiest creator primitive).
    [[sps]]
    id        = 5000
    copy_from = { field = "303", sps = 2266 }   # take tpage/clut/uv/rgb/size from Ice-Cavern effect 2266
    frames    = [ [ {pos=[0,0], uv=0, rgb=1} ], [ {pos=[2,-2], uv=0, rgb=2} ] ]   # optional: new geometry
    pos       = [120, 30, -40]                  # world x, y, z (engine negates y); or [x, z] + y = N
    slot      = 15
    abr       = 1                               # 0=50%add 1=add 2=sub 3=25%add (omit = leave default)
    framerate = 16                              # 16 = 1x

    # Fully inline (power user): borrow a donor's tcb, author every byte via codec.build.
    [[sps]]
    id      = 5001
    texture = { borrow_tcb = "303", tpage = { tp = 0, tx = 8, ty = 1 }, clut = { cluty = 251, clutx = 20 } }
    size    = [9, 9]
    uv      = [[0, 96], [32, 96]]
    rgb     = [[255, 200, 80], [255, 120, 0]]
    frames  = [ [ {pos=[0,0], uv=0, rgb=0} ], [ {pos=[2,-1], uv=1, rgb=1} ] ]
    pos     = [0, 0, 0]
    slot    = 14
"""
from __future__ import annotations

import copy

from . import codec as _codec
from .lint import lint_sps

# placement defaults: a high SPS slot avoids colliding with a donor's low-slot effects on a verbatim fork
DEFAULT_SLOT = 15
SCALE_ONE = 4096
FRAMERATE_ONE = 16


class SpsAuthorError(ValueError):
    pass


def _block_list(blocks):
    if not isinstance(blocks, list):
        raise SpsAuthorError("[[sps]] must be an array of tables ([[sps]], not [sps])")
    for n, b in enumerate(blocks):
        if not isinstance(b, dict):
            raise SpsAuthorError(f"[[sps]] #{n} must be a table, got {type(b).__name__}")
    return blocks


def _int(b, key, ctx):
    v = b.get(key)
    if not isinstance(v, int) or isinstance(v, bool):
        raise SpsAuthorError(f"{ctx}: {key!r} must be an integer, got {v!r}")
    return v


def _default_donor_loader(field_token, sps_id) -> _codec.Sps:
    """Load donor ``field``'s effect ``sps_id`` to a codec model, live from the install (for ``copy_from``)."""
    from . import catalog as _cat
    rows = _cat.list_field_sps(field_token)
    entry = next((e for e in rows if e.sps_id == int(sps_id)), None)
    if entry is None:
        have = [e.sps_id for e in rows]
        raise SpsAuthorError(f"copy_from: field {field_token!r} has no SPS effect {sps_id} "
                             + (f"(has: {have})" if have else "(no install / not readable)"))
    return _cat.load_sps(entry)


def _parse_frames(frames, ctx) -> list:
    """``[[{pos=[x,y], uv=I, rgb=J}, ...], ...]`` -> ``list[list[codec.Prim]]``."""
    if not isinstance(frames, list) or not frames:
        raise SpsAuthorError(f"{ctx}: 'frames' must be a non-empty array of frames")
    out = []
    for fi, frame in enumerate(frames):
        if not isinstance(frame, list):
            raise SpsAuthorError(f"{ctx}: frame {fi} must be an array of prims")
        prims = []
        for pi, p in enumerate(frame):
            if not isinstance(p, dict):
                raise SpsAuthorError(f"{ctx}: frame {fi} prim {pi} must be a table {{pos, uv, rgb}}")
            pos = p.get("pos")
            if not (isinstance(pos, list) and len(pos) == 2 and all(isinstance(c, int) for c in pos)):
                raise SpsAuthorError(f"{ctx}: frame {fi} prim {pi} 'pos' must be [x, y] ints, got {pos!r}")
            uv = p.get("uv", 0)
            rgb = p.get("rgb", 0)
            if not all(isinstance(v, int) and not isinstance(v, bool) for v in (uv, rgb)):
                raise SpsAuthorError(f"{ctx}: frame {fi} prim {pi} uv/rgb must be integer indices")
            try:
                prims.append(_codec.prim(pos[0], pos[1], uv, rgb))
            except _codec.SpsCodecError as ex:
                raise SpsAuthorError(f"{ctx}: frame {fi} prim {pi}: {ex}") from ex
        out.append(prims)
    return out


def _texture_words(texture, ctx):
    """Resolve ``tpage``/``clut`` (raw ints or fielded tables) to the two u16 words."""
    def word(key, maker):
        v = texture.get(key)
        if isinstance(v, int) and not isinstance(v, bool):
            return v
        if isinstance(v, dict):
            return maker(**{k: int(n) for k, n in v.items()})
        raise SpsAuthorError(f"{ctx}: texture.{key} must be a u16 int or a fielded table, got {v!r}")
    return word("tpage", _codec.make_tpage), word("clut", _codec.make_clut)


def build_sps_from_block(block: dict, *, donor_loader=None) -> _codec.Sps:
    """Resolve one ``[[sps]]`` block to a :class:`codec.Sps`. ``copy_from`` clones a donor effect (then an
    optional ``frames``/``rgb``/``size`` override); otherwise an inline ``texture``+``size``+``uv``+``rgb``+
    ``frames`` is built via :func:`codec.build`. Lints the result (raises :class:`SpsAuthorError` on a problem)."""
    if "id" not in block:
        raise SpsAuthorError("[[sps]]: every block needs an integer `id` (the effect id)")
    sid = _int(block, "id", "[[sps]]")
    ctx = f"[[sps]] id={sid}"
    if "png" in (block.get("texture") or {}):
        raise SpsAuthorError(f"{ctx}: texture.png (Route B, new art) needs a Memoria SPSConst.SPSTexture "
                             "registration patch -- not yet supported. Use copy_from / texture.borrow_tcb (Route A).")
    loader = donor_loader or _default_donor_loader

    if "copy_from" in block:
        if "texture" in block or "uv" in block or "rgb" in block:
            raise SpsAuthorError(f"{ctx}: copy_from is exclusive with inline texture/uv/rgb")
        cf = block["copy_from"]
        if not (isinstance(cf, dict) and "field" in cf and "sps" in cf):
            raise SpsAuthorError(f"{ctx}: copy_from must be {{ field = <token>, sps = <id> }}")
        model = copy.deepcopy(loader(cf["field"], cf["sps"]))
        model.frame_offsets = None                          # re-laid canonically on serialize
        model.tail = b""
        if "frames" in block:
            model.frames = _parse_frames(block["frames"], ctx)
        if "rgb" in block:
            model.rgb_table = [(*_rgb3(c, ctx), 0) for c in block["rgb"]]
        if "size" in block:
            model.h_raw, model.w_raw = _size(block["size"], ctx)
    else:
        for req in ("texture", "size", "uv", "rgb", "frames"):
            if req not in block:
                raise SpsAuthorError(f"{ctx}: inline effect needs {req!r} (or use copy_from)")
        tpage_raw, clut_raw = _texture_words(block["texture"], ctx)
        h_raw, w_raw = _size(block["size"], ctx)
        model = _codec.build(
            tpage_raw=tpage_raw, clut_raw=clut_raw, h_raw=h_raw, w_raw=w_raw,
            uv_table=[tuple(_xy(c, ctx)) for c in block["uv"]],
            rgb_table=[(*_rgb3(c, ctx), 0) for c in block["rgb"]],
            frames=_parse_frames(block["frames"], ctx),
        )
    problems = lint_sps(model)
    if problems:
        raise SpsAuthorError(f"{ctx}: invalid effect -- " + "; ".join(problems))
    return model


def _rgb3(c, ctx):
    if not (isinstance(c, list) and len(c) == 3 and all(isinstance(v, int) and 0 <= v <= 255 for v in c)):
        raise SpsAuthorError(f"{ctx}: an rgb entry must be [r, g, b] ints 0..255, got {c!r}")
    return c[0], c[1], c[2]


def _xy(c, ctx):
    if not (isinstance(c, list) and len(c) == 2 and all(isinstance(v, int) and 0 <= v <= 255 for v in c)):
        raise SpsAuthorError(f"{ctx}: a uv entry must be [x, y] ints 0..255, got {c!r}")
    return c[0], c[1]


def _size(s, ctx):
    if not (isinstance(s, list) and len(s) == 2 and all(isinstance(v, int) and 1 <= v <= 255 for v in s)):
        raise SpsAuthorError(f"{ctx}: 'size' must be [h_raw, w_raw] ints 1..255, got {s!r}")
    return s[0], s[1]


def tcb_source(block: dict) -> tuple[str, str | None]:
    """How to supply the effect's ``spt.tcb``: ``("borrow", donor_token)`` (``copy_from`` or
    ``texture.borrow_tcb``) or ``("reuse", None)`` (use the field's already-carried tcb)."""
    if "copy_from" in block:
        return "borrow", str(block["copy_from"]["field"])
    tex = block.get("texture") or {}
    if tex.get("borrow_tcb") is not None:
        return "borrow", str(tex["borrow_tcb"])
    return "reuse", None


def trigger_spec(block: dict, *, slot: int | None = None) -> dict:
    """The placement -> the ``RunSPSCode`` create+place spec (consumed by ``content.sps_trigger``)."""
    sid = _int(block, "id", "[[sps]]")
    ctx = f"[[sps]] id={sid}"
    pos = block.get("pos", [0, 0, 0])
    if not (isinstance(pos, list) and len(pos) in (2, 3) and all(isinstance(c, int) for c in pos)):
        raise SpsAuthorError(f"{ctx}: 'pos' must be [x, y, z] (or [x, z] with separate y=), got {pos!r}")
    if len(pos) == 3:
        x, y, z = pos
    else:
        x, z = pos
        y = int(block.get("y", 0))
    for k in ("x", "y", "z"):
        v = {"x": x, "y": y, "z": z}[k]
        if not -32768 <= v <= 32767:
            raise SpsAuthorError(f"{ctx}: pos {k}={v} out of the i16 range RunSPSCode carries")
    spec = {"slot": slot if slot is not None else int(block.get("slot", DEFAULT_SLOT)),
            "sps_id": sid, "pos": (x, y, z)}
    for key in ("abr", "framerate", "scale"):
        if key in block:
            spec[key] = _int(block, key, ctx)
    if not 0 <= spec["slot"] <= 15:
        raise SpsAuthorError(f"{ctx}: slot {spec['slot']} out of range 0..15 (FIELD_DEFAULT_OBJCOUNT=16)")
    return spec


def validate_sps_block(block: dict, *, donor_loader=None) -> list[str]:
    """Offline problems for one ``[[sps]]`` block (empty == OK). Never raises (build-safe). The donor read is
    install-gated, so a copy_from/borrow whose donor can't be read offline degrades to a clean message."""
    try:
        build_sps_from_block(block, donor_loader=donor_loader)
        trigger_spec(block)
        return []
    except (SpsAuthorError, _codec.SpsCodecError) as ex:
        return [str(ex)]
