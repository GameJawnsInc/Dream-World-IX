"""NET-NEW raw17 sequence authoring -- the LENGTH-CHANGING tier (read = :mod:`seqdis`, same-length = :mod:`seqpatch`).
The analog of ``battle/aiauthor`` for enemy AI: assemble a whole attack-sequence body from source (:mod:`seqasm`)
and SPLICE it in, driving the offset-fixup repack (:func:`seqcodec.serialize_repacked`) so every ``seqOffset`` +
``camOffset`` is recomputed and the camera block re-appends intact.

``[[scene.seq_replace]]`` (seq = sub_no, source = ...) replaces an existing attack's choreography wholesale. A
brand-NEW attack slot (growing ``seqCount`` + wiring a raw16 ``AA_DATA`` + the ``.eb`` AI to select it) is a further
step; replace is the keystone primitive it builds on. Authoring is lint-gated on the two per-file cross-references
the engine doesn't bounds-check: an out-of-range ``Anim`` code (``IndexOutOfRange`` on ``animList``) and a
``SetCamera``/``RunCamera`` id past the file's camera count (a stuck/black native camera) -- both fail the build,
not the game.
"""
from __future__ import annotations

from . import camera_codec as _cc
from . import seqasm as _seqasm
from . import seqcodec as _sc


class SeqAuthorError(ValueError):
    pass


_CAMERA_OPS = (0x10, 0x12, 0x20)                         # SetCamera / RunCamera / RunCameraForced (cam id @ operand 0)


def lint_seq(raw17: bytes) -> list:
    """Offline semantic problems of a raw17's sequences (empty => OK). The codec already guarantees decode-to-
    terminator / opcode in range / no overrun / disjoint bodies; this adds the SEMANTIC cross-references the codec
    can't see -- the two operands whose safe range is a function of THIS file's own contents:
    * an ``Anim`` (0x05) code whose ``seqBaseAnim[sub] + code`` indexes past ``animList`` (the engine does no
      bounds check -> IndexOutOfRange);
    * a ``SetCamera``/``RunCamera`` ``cam`` id >= the raw17's own camera count (the closed native SFX plugin
      selects a non-existent camera -> a stuck/black camera).
    Both are checked for every sub_no pointing at each body (aliases can differ)."""
    try:
        model = _sc.parse(raw17)
    except _sc.SeqCodecError as ex:
        return [f"unparseable raw17: {ex}"]
    cam_count = None                                     # the camera block may be absent/garbage on a hand-built
    try:                                                 # model -> skip the cam check rather than crash the lint
        cam_count = len(_cc.parse_block(raw17)[1])
    except Exception:                                    # noqa: BLE001 -- CameraCodecError or a malformed block
        cam_count = None
    problems = []
    n = model.anim_count
    for sub in range(model.seq_count):
        body = model.body_for(sub)
        if body is None:
            continue
        base = model.seq_base_anim[sub]
        for ins in body.instrs:
            if ins.op == 0x05 and ins.operands[0] != 255:        # Anim, non-idle
                idx = base + ins.operands[0]
                if idx >= n:                                     # base+code of two unsigned bytes is always >= 0
                    problems.append(f"sub {sub}: Anim code {ins.operands[0]} -> animList[{base}+{ins.operands[0]}]"
                                    f" = {idx} is out of range (animCount {n}) -- would crash the engine")
            elif ins.op in _CAMERA_OPS and cam_count is not None and ins.operands[0] >= cam_count:
                problems.append(f"sub {sub}: {ins.name} cam {ins.operands[0]} exceeds the {cam_count} camera(s) "
                                f"in this raw17 -- no camera entry to play (stuck/black camera)")
    return problems


def replace_sequence(raw17: bytes, sub_no: int, source: str) -> tuple:
    """Replace sub_no's attack-sequence body with one assembled from ``source`` (a :mod:`seqasm` block ending in a
    terminator). Returns (new_raw17, warnings). The whole file is repacked (offsets recomputed, camera block kept).
    Raises SeqAuthorError on a bad sub_no / unassemblable source / a body whose edit would crash (lint)."""
    try:
        model = _sc.parse(raw17)
    except _sc.SeqCodecError as ex:
        raise SeqAuthorError(f"malformed raw17: {ex}")
    if not isinstance(sub_no, int) or isinstance(sub_no, bool) or not 0 <= sub_no < model.seq_count:
        raise SeqAuthorError(f"seq = {sub_no!r} is not a valid sub_no (0..{model.seq_count - 1})")
    if model.seq_offset[sub_no] == 0:
        raise SeqAuthorError(f"seq {sub_no} has no sequence (seqOffset 0 sentinel) -- nothing to replace")
    body = model.body_for(sub_no)
    try:
        instrs = _seqasm.assemble(source)
    except _seqasm.SeqAsmError as ex:
        raise SeqAuthorError(f"seq {sub_no} source: {ex}")
    warnings = []
    others = tuple(s for s in range(model.seq_count) if model.seq_offset[s] == body.offset and s != sub_no)
    if others:
        warnings.append(f"seq {sub_no} also shares its body with sub(s) {','.join(str(s) for s in others)} "
                        f"-- replacing it rewrites ALL of them")
    body.instrs = [_sc.Instr(i.op, 0, list(i.operands)) for i in instrs]    # offsets are recomputed by the repack
    try:
        out = _sc.serialize_repacked(model)                                 # may raise on an i16-overflowing body
    except _sc.SeqCodecError as ex:
        raise SeqAuthorError(f"seq {sub_no}: {ex}")
    problems = lint_seq(out)                                                # the composed result must lint clean
    if problems:
        raise SeqAuthorError(f"seq {sub_no} would produce an invalid raw17: {'; '.join(problems)}")
    return out, warnings


def _locate(body, locator, kind: str) -> int:
    """Resolve a ``before``/``after`` locator -> an instruction INDEX in ``body.instrs``. The locator is an int
    (instruction index) or a str (an opcode NAME -> its first occurrence)."""
    if isinstance(locator, bool) or not isinstance(locator, (int, str)):
        raise SeqAuthorError(f"{kind} must be an instruction index (int) or an opcode name (str)")
    if isinstance(locator, int):
        if not 0 <= locator < len(body.instrs):
            raise SeqAuthorError(f"{kind} = {locator} out of range (0..{len(body.instrs) - 1})")
        return locator
    for idx, ins in enumerate(body.instrs):
        if ins.name == locator:
            return idx
    raise SeqAuthorError(f"{kind} = {locator!r}: no such opcode in this sequence "
                         f"(has {[i.name for i in body.instrs]})")


def insert_sequence(raw17: bytes, sub_no: int, source: str, *, before=None, after=None) -> tuple:
    """Splice an assembled FRAGMENT (no terminator) into sub_no's body at a ``before``/``after`` locator (an
    instruction index or an opcode name). The body's terminator stays last. Returns (new_raw17, warnings)."""
    try:
        model = _sc.parse(raw17)
    except _sc.SeqCodecError as ex:
        raise SeqAuthorError(f"malformed raw17: {ex}")
    if not isinstance(sub_no, int) or isinstance(sub_no, bool) or not 0 <= sub_no < model.seq_count:
        raise SeqAuthorError(f"seq = {sub_no!r} is not a valid sub_no (0..{model.seq_count - 1})")
    if model.seq_offset[sub_no] == 0:
        raise SeqAuthorError(f"seq {sub_no} has no sequence (seqOffset 0 sentinel)")
    if (before is None) == (after is None):
        raise SeqAuthorError("give exactly one of before / after (an instruction index or opcode name)")
    body = model.body_for(sub_no)
    try:
        frag = _seqasm.assemble_fragment(source)
    except _seqasm.SeqAsmError as ex:
        raise SeqAuthorError(f"seq {sub_no} fragment: {ex}")
    pos = _locate(body, before, "before") if before is not None else _locate(body, after, "after") + 1
    if pos >= len(body.instrs):                          # never splice at/after the terminator
        raise SeqAuthorError(f"seq {sub_no}: insert position {pos} is at/after the terminator -- "
                             f"insert before the final {body.instrs[-1].name}")
    warnings = []
    others = tuple(s for s in range(model.seq_count) if model.seq_offset[s] == body.offset and s != sub_no)
    if others:
        warnings.append(f"seq {sub_no} also shares its body with sub(s) {','.join(str(s) for s in others)} "
                        f"-- the insert applies to ALL of them")
    new = [_sc.Instr(i.op, 0, list(i.operands)) for i in body.instrs]
    for k, ins in enumerate(frag):
        new.insert(pos + k, _sc.Instr(ins.op, 0, list(ins.operands)))
    body.instrs = new
    try:
        out = _sc.serialize_repacked(model)
    except _sc.SeqCodecError as ex:
        raise SeqAuthorError(f"seq {sub_no}: {ex}")
    problems = lint_seq(out)
    if problems:
        raise SeqAuthorError(f"seq {sub_no} insert would produce an invalid raw17: {'; '.join(problems)}")
    return out, warnings


def apply_seq_inserts(raw17: bytes, specs) -> tuple:
    """Apply ``[{seq, source, before|after}, ...]`` fragment inserts in order. Returns (new_raw17, warnings)."""
    if not isinstance(specs, list):
        raise SeqAuthorError("[[scene.seq_insert]] must be a list of tables")
    b = raw17
    warnings: list = []
    for n, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise SeqAuthorError(f"[[scene.seq_insert]] #{n} must be a table (got {type(spec).__name__})")
        unknown = set(spec) - {"seq", "source", "before", "after"}
        if unknown:
            raise SeqAuthorError(f"[[scene.seq_insert]] #{n}: unknown key(s) {sorted(unknown)} "
                                 f"(expected seq / source / before / after)")
        seq, source = spec.get("seq"), spec.get("source")
        if not isinstance(seq, int) or isinstance(seq, bool):
            raise SeqAuthorError(f"[[scene.seq_insert]] #{n} needs an integer seq")
        if not isinstance(source, str) or not source.strip():
            raise SeqAuthorError(f"[[scene.seq_insert]] #{n} needs a non-empty source string")
        try:
            b, w = insert_sequence(b, seq, source, before=spec.get("before"), after=spec.get("after"))
        except SeqAuthorError as ex:
            raise SeqAuthorError(f"[[scene.seq_insert]] #{n}: {ex}")
        warnings += w
    return b, warnings


def apply_seq_replaces(raw17: bytes, specs) -> tuple:
    """Apply ``[{seq, source}, ...]`` body replacements in order. Returns (new_raw17, warnings)."""
    if not isinstance(specs, list):
        raise SeqAuthorError("[[scene.seq_replace]] must be a list of tables")
    b = raw17
    warnings: list = []
    for n, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise SeqAuthorError(f"[[scene.seq_replace]] #{n} must be a table (got {type(spec).__name__})")
        unknown = set(spec) - {"seq", "source"}
        if unknown:
            raise SeqAuthorError(f"[[scene.seq_replace]] #{n}: unknown key(s) {sorted(unknown)} (expected seq / source)")
        seq, source = spec.get("seq"), spec.get("source")
        if not isinstance(seq, int) or isinstance(seq, bool):
            raise SeqAuthorError(f"[[scene.seq_replace]] #{n} needs an integer seq (the sub_no to replace)")
        if not isinstance(source, str) or not source.strip():
            raise SeqAuthorError(f"[[scene.seq_replace]] #{n} needs a non-empty source string")
        try:
            b, w = replace_sequence(b, seq, source)
        except SeqAuthorError as ex:
            raise SeqAuthorError(f"[[scene.seq_replace]] #{n}: {ex}")
        warnings += w
    return b, warnings


def validate_replaces(raw17: bytes, specs) -> list:
    """Offline problems (empty => OK): re-run the replaces on a copy + surface any SeqAuthorError as a message."""
    try:
        apply_seq_replaces(raw17, specs)
        return []
    except SeqAuthorError as ex:
        return [str(ex)]


def validate_inserts(raw17: bytes, specs) -> list:
    """Offline problems (empty => OK): re-run the inserts on a copy + surface any SeqAuthorError as a message."""
    try:
        apply_seq_inserts(raw17, specs)
        return []
    except SeqAuthorError as ex:
        return [str(ex)]
