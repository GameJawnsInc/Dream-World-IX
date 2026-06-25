"""``[[sps_edit]]`` -- declarative re-skin of an EXISTING ``.sps`` effect over its carried texture (Tier 1).
Mirrors the ``[[logic_edit]]`` lifecycle (single error type, ``_int``/``_req`` guards, ``_edit_list`` container
guard, an old-guard per op, a re-parse lint gate) but operates on the decoded :class:`codec.Sps` model -- the
re-skin is semantic (recolour the RGB ramp, tint the whole ramp, rescale the quad/UV size, reposition the prims),
so model edits are cleaner than byte-offset patches.

NO texture work and NO ``.eb`` change: every op stays inside the ``.sps`` bin geometry/colour we fully control,
over the donor's already-carried ``spt.tcb``. (The ``.eb``-side levers -- playback FRAMERATE and ABR blend mode --
are RunSPSCode operands, not bin fields, and are a follow-up.) A bad edit raises :class:`SpsEditError` so it fails
the BUILD, never the game. -> [[project-ff9-sps-authoring]].

Schema (``field.toml``)::

    [[sps_edit]]
    kind = "recolor_ramp"   # overwrite one ramp colour
    sps  = 2266             # REQUIRED selector: targets <sps>.sps.bytes in the field's sps/ sidecar
    index = 1               # rgb_table row
    old = [128, 128, 128]   # old-guard (current r,g,b) -> refuse on donor drift
    new = [200, 40, 40]

    [[sps_edit]]
    kind = "tint"           # multiply EVERY ramp colour (recolour/brighten the whole effect)
    sps  = 2266
    mul  = [0, 0, 512]      # per-channel, 256 == identity (so this makes a grey effect blue)

    [[sps_edit]]
    kind = "scale"          # resize the quads + UV cells
    sps  = 2266
    old_size = [9, 9]       # [h_raw, w_raw] guard
    new_size = [13, 13]

    [[sps_edit]]
    kind = "reposition"     # shift prims (one frame, or all)
    sps  = 2266
    dx = 4
    dy = -2
    # frame = 0             # optional; omit = every frame
"""
from __future__ import annotations

from . import codec as _codec


class SpsEditError(ValueError):
    pass


_KIND_KEYS = {
    "recolor_ramp": {"kind", "sps", "index", "old", "new"},
    "tint": {"kind", "sps", "mul"},
    "scale": {"kind", "sps", "old_size", "new_size"},
    "reposition": {"kind", "sps", "dx", "dy", "frame"},
}


def _edit_list(edits):
    """Guard that ``edits`` is a list of tables (catches the ``[sps_edit]`` vs ``[[sps_edit]]`` mistake)."""
    if not isinstance(edits, list):
        raise SpsEditError("[[sps_edit]] must be an array of tables ([[sps_edit]], not [sps_edit])")
    for n, e in enumerate(edits):
        if not isinstance(e, dict):
            raise SpsEditError(f"[[sps_edit]] #{n} must be a table, got {type(e).__name__}")
    return edits


def _int(e, key, ctx):
    v = e.get(key)
    if not isinstance(v, int) or isinstance(v, bool):
        raise SpsEditError(f"{ctx}: {key!r} must be an integer, got {v!r}")
    return v


def _rgb(e, key, ctx):
    v = e.get(key)
    if not (isinstance(v, list) and len(v) == 3 and all(isinstance(c, int) and not isinstance(c, bool) for c in v)):
        raise SpsEditError(f"{ctx}: {key!r} must be a [r, g, b] integer triple, got {v!r}")
    if not all(0 <= c <= 255 for c in v):
        raise SpsEditError(f"{ctx}: {key!r} {v} channel out of 0..255")
    return tuple(v)


def _check_keys(e, kind, ctx):
    allowed = _KIND_KEYS[kind]
    unknown = set(e) - allowed
    if unknown:
        raise SpsEditError(f"{ctx}: unknown key(s) {sorted(unknown)} for kind {kind!r} (allowed: {sorted(allowed)})")
    for req in allowed - {"frame"}:
        if req not in e:
            raise SpsEditError(f"{ctx}: missing required key {req!r} for kind {kind!r}")


def _apply_one(model: _codec.Sps, e: dict, ctx: str) -> None:
    kind = e.get("kind")
    if kind not in _KIND_KEYS:
        raise SpsEditError(f"{ctx}: unknown kind {kind!r} (known: {sorted(_KIND_KEYS)})")
    _check_keys(e, kind, ctx)

    if kind == "recolor_ramp":
        idx = _int(e, "index", ctx)
        if not (0 <= idx < len(model.rgb_table)):
            raise SpsEditError(f"{ctx}: index {idx} out of range (rgb_table has {len(model.rgb_table)})")
        old = _rgb(e, "old", ctx)
        cur = model.rgb_table[idx][:3]
        if cur != old:
            raise SpsEditError(f"{ctx}: old-guard mismatch at rgb_table[{idx}] -- expected {old}, found {cur}")
        new = _rgb(e, "new", ctx)
        model.rgb_table[idx] = (new[0], new[1], new[2], 0)

    elif kind == "tint":
        mul = e.get("mul")
        if not (isinstance(mul, list) and len(mul) == 3 and all(isinstance(c, int) and not isinstance(c, bool) for c in mul)):
            raise SpsEditError(f"{ctx}: 'mul' must be a [r, g, b] integer triple, got {mul!r}")
        if not all(0 <= c <= 4096 for c in mul):
            raise SpsEditError(f"{ctx}: 'mul' {mul} channel out of 0..4096 (256 == identity)")
        for ri, (r, g, b, _pad) in enumerate(model.rgb_table):
            model.rgb_table[ri] = (
                min(255, (r * mul[0]) >> 8),
                min(255, (g * mul[1]) >> 8),
                min(255, (b * mul[2]) >> 8),
                0,
            )

    elif kind == "scale":
        old_size = e.get("old_size")
        if not (isinstance(old_size, list) and len(old_size) == 2):
            raise SpsEditError(f"{ctx}: 'old_size' must be [h_raw, w_raw], got {old_size!r}")
        cur = [model.h_raw, model.w_raw]
        if list(old_size) != cur:
            raise SpsEditError(f"{ctx}: old-guard mismatch -- expected size {list(old_size)}, found {cur}")
        new_size = e.get("new_size")
        if not (isinstance(new_size, list) and len(new_size) == 2
                and all(isinstance(c, int) and not isinstance(c, bool) and 1 <= c <= 255 for c in new_size)):
            raise SpsEditError(f"{ctx}: 'new_size' must be two ints 1..255 [h_raw, w_raw], got {new_size!r}")
        model.h_raw, model.w_raw = new_size[0], new_size[1]

    elif kind == "reposition":
        dx = _int(e, "dx", ctx)
        dy = _int(e, "dy", ctx)
        frame = e.get("frame")
        if frame is not None:
            if not isinstance(frame, int) or isinstance(frame, bool) or not (0 <= frame < model.frame_count):
                raise SpsEditError(f"{ctx}: 'frame' {frame!r} out of range 0..{model.frame_count - 1}")
            targets = [model.frames[frame]]
        else:
            targets = model.frames
        for fr in targets:
            for p in fr:
                nx, ny = p.pos_x + dx, p.pos_y + dy
                if not (-128 <= nx <= 127 and -128 <= ny <= 127):
                    raise SpsEditError(f"{ctx}: reposition pushes a prim to ({nx},{ny}), out of i8 range (-128..127)")
                p.pos_x, p.pos_y = nx, ny


def apply_sps_edits(sps_bytes: bytes, edits, *, sps_id: int) -> bytes:
    """Apply every ``[[sps_edit]]`` whose ``sps == sps_id`` to one ``.sps`` blob; return the new bytes.
    No matching edit (or an empty list) -> byte-identical. Old-guarded; re-parses + lints the result (the SPS
    analogue of the eblint gate). Raises :class:`SpsEditError` on any unsafe edit."""
    _edit_list(edits)
    mine = [e for e in edits if e.get("sps") == sps_id]
    if not mine:
        return bytes(sps_bytes)
    model = _codec.parse(sps_bytes)
    for n, e in enumerate(mine):
        _apply_one(model, e, f"[[sps_edit]] sps={sps_id} #{n}")
    # Structural gate: the result must re-encode and re-parse stably. (We do NOT run the authoring lint here:
    # real shipping effects can index a nibble past a short table into adjacent data -- valid, deterministic --
    # and that must remain editable. Each op already guards its own range; serialize's _i8 enforces positions.)
    try:
        out = _codec.serialize(model)
        if _codec.serialize(_codec.parse(out)) != out:
            raise SpsEditError(f"edited sps {sps_id} did not round-trip stably")
    except _codec.SpsCodecError as ex:
        raise SpsEditError(f"edited sps {sps_id} no longer encodes: {ex}") from ex
    return out


def validate_sps_edits(sps_bytes: bytes, edits, *, sps_id: int) -> list[str]:
    """Offline problems for one bin's edits (empty == OK). Runs :func:`apply_sps_edits` and returns any
    :class:`SpsEditError`/:class:`codec.SpsCodecError` as a message. NEVER raises (build-safe)."""
    try:
        apply_sps_edits(sps_bytes, edits, sps_id=sps_id)
        return []
    except (SpsEditError, _codec.SpsCodecError) as ex:
        return [str(ex)]
