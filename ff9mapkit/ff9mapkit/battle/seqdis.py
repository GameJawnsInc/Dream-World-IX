"""The read-only DISASSEMBLER VIEW for a raw17 ``btlseq`` attack sequence -- the "see the choreography" step,
the raw17 analog of :mod:`ff9mapkit.battle.battleai` (enemy AI). Decodes via the lossless :mod:`seqcodec`
parse, then renders each sub-sequence (by ``sub_no`` == attack index) as named instructions with annotated
operands + the resolved animation ids. Read-only + offline; only the open-source opcode NAMES are committed.

The companion "find the offset to patch" view (``battle-seq --sites``) delegates to :mod:`seqpatch`.
"""
from __future__ import annotations

from . import seqcodec as _sc


def _anim_note(model: _sc.Raw17, sub_no: int, ins: _sc.Instr) -> str:
    """For an Anim (0x05) instruction, resolve animCode -> the global anim id, mirroring SeqExecAnim
    (btlseq.cs:596-618): 255 = default idle; else ``animList[seqBaseAnim[sub_no] + animCode]``."""
    if ins.op != 0x05:
        return ""
    code = ins.operands[0]
    if code == 255:
        return "  # default idle"
    base = model.seq_base_anim[sub_no] if 0 <= sub_no < len(model.seq_base_anim) else 0
    idx = base + code
    if 0 <= idx < len(model.anim_list):
        return f"  # -> animList[{base}+{code}] = anim id {model.anim_list[idx]}"
    return f"  # -> animList[{base}+{code}] OUT OF RANGE (animCount {model.anim_list and len(model.anim_list)})"


def _operand_str(ins: _sc.Instr) -> str:
    parts = []
    for (name, _rel, _w, _signed, _kind), val in zip(ins.fields, ins.operands):
        if name == "_pad":
            continue                                  # the 0x19 discarded hole -- not meaningful to show
        parts.append(f"{name}={val}")
    return ", ".join(parts)


def _extra_note(ins: _sc.Instr) -> str:
    if ins.op == 0x02:
        return "  # commits a damage/effect pass (hit-count = #Calc)"
    if ins.op in (0x0E, 0x21) and (ins.operands[0] & 0x80):
        return "  # attack-name/title (bit7)"
    if ins.op == 0x12:
        return "  # camera fires only if the alt-camera predicate is true"
    return ""


def disassemble_seq(raw17: bytes) -> str:
    """Render a raw17's attack sequences as annotated text: header summary, then each ``sub_no`` (== attack
    index) as one line per instruction (named op + operands + resolved anim ids). Aliased slots are noted."""
    try:
        model = _sc.parse(raw17)
    except _sc.SeqCodecError as ex:
        return f"<unreadable/malformed raw17: {ex}>"
    n_bodies = len(model.bodies)
    lines = [f"btlseq: {model.seq_count} sequence slot(s), {model.anim_count} anim id(s), "
             f"{n_bodies} distinct body(ies), camOffset {model.cam_offset}, "
             f"camera block {len(model.camera_block)} B"]
    seen: dict = {}                                   # offset -> first sub_no (alias detection)
    for sub in range(model.seq_count):
        off = model.seq_offset[sub]
        base = model.seq_base_anim[sub] if sub < len(model.seq_base_anim) else 0
        if off == 0:
            lines.append(f"\n  -- sub {sub}  (no sequence / sentinel) --")
            continue
        if off in seen:
            lines.append(f"\n  -- sub {sub}  -> ALIAS of sub {seen[off]} (offset {off}, base-anim {base}) --")
            continue
        seen[off] = sub
        body = model.body_for(sub)
        lines.append(f"\n  -- sub {sub}  (base-anim {base}, abs {off + 4}, {len(body.instrs)} instr) --")
        for ins in body.instrs:
            ops = _operand_str(ins)
            note = _anim_note(model, sub, ins) or _extra_note(ins)
            lines.append(f"    [{ins.offset}] {ins.name}({ops}){note}")
    return "\n".join(lines)


# ----------------------------------------------------------------- scene loading (install-gated, like battleai)
def _scene_raw17(donor: str, game=None) -> bytes:
    from . import extract as _extract
    raw17 = _extract.read_scene_assets(donor, game=game).get("raw17")
    if not raw17:
        raise FileNotFoundError(f"no btlseq.raw17 found for battle scene {donor!r}")
    return raw17


def analyze_scene_seq(donor: str, game=None) -> str:
    """Read a real battle scene's ``btlseq.raw17`` LIVE from the install + disassemble its attack sequences.
    ``donor`` is the scene name after ``EVT_BATTLE_`` (e.g. ``EF_R007``)."""
    return (f"# attack sequences of scene {donor} (EVT_BATTLE_{donor}.raw17)\n"
            + disassemble_seq(_scene_raw17(donor, game=game)))


def scene_seq_sites(donor: str, game=None) -> str:
    """List a scene's patchable sequence operands (the ``[[scene.seq_patch]]`` targets): byte offset, width,
    current value, context. Read-only -- the 'find the offset to patch' companion to the disassembly."""
    from . import seqpatch as _seqpatch
    sites = _seqpatch.constant_sites(_scene_raw17(donor, game=game))
    lines = [f"# patchable sequence operands of scene {donor} ({len(sites)} sites)",
             "# cite the offset in [[scene.seq_patch]] (seq = <sub_no>, at = <offset>, old = <value>, "
             "new = <same-width value>)"]
    for s in sites:
        lines.append(f"  sub{s.sub_no:<2} at={s.offset:<6} {s.width}B  {s.kind:<10} = {s.value:<8}  {s.where}")
    return "\n".join(lines)
