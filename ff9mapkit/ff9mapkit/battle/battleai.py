"""Phase-6a: the enemy-AI DISASSEMBLER VIEW -- the read-only "see the enemy's AI" step.

A battle scene's ``EVT_BATTLE_<NAME>.eb`` is the SAME ``.eb`` container as a field script, run by the same
``EventEngine`` interpreter -- so the kit already round-trips it (``EbScript``) and decodes its bytecode
(``eb.disasm``). What was missing to READ enemy AI is the vocabulary: this module names the battle structure
(entry 0 = Main_Init spawn-binding; entries ``1..TypCount`` = per-enemy-type AI; functions by TAG = AI phases),
the COMMAND opcodes (via the field ``OP_NAMES``, incl. ``BTLCMD`` = the attack-select command), and the
EXPRESSION operators + variable reads (via :mod:`ff9mapkit.eb._exprtable` -- ``B_CURHP``/``B_LT`` and decoded
``Global.Bit[..]`` story-flag / ``obj(uid).f[..]`` battle-char reads). The output is the import->SEE step that
authoring (Phase 6b/6c: same-length constant patches, then new branches) will build on.

Read-only + offline: no engine, no edit. Provenance: only the open-source opcode/operator NAMES are committed;
the donor bytes are read live from the install, never committed.
"""
from __future__ import annotations

from ..eb import disasm as _disasm
from ..eb._optables import OP_ARG_COUNT
from ..eb.model import EbScript

# Battle-AI function TAGS -> their role (the engine dispatches an enemy object's functions by these tags via
# Request/RequestAction). Tag 0 = the entry's Init; the rest are AI phases. (project-ff9-battle-tuning §2b.)
_BATTLE_TAGS = {0: "Init", 1: "Main", 2: "Tag2", 6: "Counter", 7: "ATB", 9: "Dying", 10: "Reinit"}

# the low CONTROL opcodes the engine handles in EBin.jumpToCommand (not DoEventCode), which OP_NAMES leaves
# unnamed (they are "rsvNN" in event_code_binary). Naming them is what makes the AI's branches readable.
_CTRL_NAMES = {0x01: "JMP", 0x02: "JMP_IFNOT", 0x03: "JMP_IF", 0x04: "RET", 0x05: "SET", 0x06: "SWITCHEX",
               0x0B: "SWITCH", 0x0D: "SWITCH2"}


def _tag_role(tag: int) -> str:
    return _BATTLE_TAGS.get(tag, f"tag{tag}")


def _cmd_name(op: int) -> str:
    """Command mnemonic: the control overlay first, then the field OP_NAMES, then opXX."""
    return _CTRL_NAMES.get(op, _disasm.op_name(op))


def _decode_func_pretty(raw: bytes, start: int, end: int):
    """Yield ``(offset, mnemonic, [operand_str...])`` for each instruction in ``raw[start:end]``. Mirrors
    ``disasm.read_code``'s operand walk EXACTLY (same arg-flag / variable-count handling) but renders expression
    operands with :func:`disasm.pretty_expr` (named) instead of the raw ``opXX`` form."""
    pos = start
    guard = 0
    while pos < end and guard < 100000:
        guard += 1
        off = pos
        op = raw[pos]; pos += 1
        if op == 0xFF:
            op = 0x100 | raw[pos]; pos += 1
        ac = OP_ARG_COUNT[op] if op < len(OP_ARG_COUNT) else 0
        arg_flag = 0
        if op >= 0x10 and ac != 0:
            arg_flag = raw[pos]; pos += 1
        if op == 0x05:
            arg_flag = 1
        if ac < 0:
            ac = raw[pos]; pos += 1
            if op == 0x0D:
                ac |= raw[pos] << 8; pos += 1
            if op == 0x06:
                ac = 1 + 2 * ac
            elif op in (0x0B, 0x0D):
                ac = 2 + ac
        operands = []
        for i in range(ac):
            if arg_flag & (1 << i):
                s, pos = _disasm.pretty_expr(raw, pos)
                operands.append(s)
            else:
                sz = _disasm.argsize(op, i)
                v = 0
                for k in range(sz):
                    v |= raw[pos + k] << (8 * k)
                pos += sz
                operands.append(str(v))
        yield off, _cmd_name(op), operands


def disassemble_ai(eb_bytes: bytes) -> str:
    """Render a battle ``.eb``'s enemy AI as annotated text: each entry (Main_Init + per-type AI), each tagged
    function (its phase role), each instruction (named command + annotated operands). Read-only."""
    try:                                                 # a truncated/corrupt eb can have a valid 'EV' magic but
        eb = EbScript.from_bytes(eb_bytes)               # an entry table that indexes past the buffer
    except (ValueError, IndexError) as ex:
        return f"<unreadable/malformed .eb: {type(ex).__name__}: {ex}>"
    lines: list[str] = [f"battle AI: {len(eb.entries)} entries ({eb!r})"]
    for e in eb.entries:
        if e.empty:
            continue
        role = "Main_Init (spawn/AI binding)" if e.index == 0 else f"Enemy type {e.index - 1} AI"
        lines.append(f"\n=== entry {e.index}: {role}  (type byte {e.type}, {e.func_count} func(s)) ===")
        for f in e.funcs:
            lines.append(f"  -- tag {f.tag} [{_tag_role(f.tag)}]  ({f.length} bytes) --")
            end = min(f.abs_end, len(eb.data))           # a truncated/corrupt eb can claim a func past the buffer
            try:
                for off, mn, operands in _decode_func_pretty(eb.data, f.abs_start, end):
                    lines.append(f"    [{off}] {mn}({', '.join(operands)})")
            except IndexError:                            # malformed bytecode runs off the end -> a legible note,
                lines.append(f"    <truncated/malformed bytecode -- decode stopped at offset {len(eb.data)}>")
    return "\n".join(lines)


def _scene_eb(donor: str, game=None, lang: str = "us") -> bytes:
    from . import extract as _extract
    assets = _extract.read_scene_assets(donor, game=game)
    eb = assets.get("eb", {}).get(lang) or next((b for b in assets.get("eb", {}).values() if b), None)
    if not eb:
        raise FileNotFoundError(f"no EVT_BATTLE_{donor}.eb found for scene {donor!r}")
    return eb


def scene_ai_sites(donor: str, game=None, lang: str = "us") -> str:
    """List a scene AI's patchable numeric constants (the ``[[scene.ai_patch]]`` targets): byte offset, width,
    current value, context. Read-only -- the 'find the offset to patch' companion to the disassembly."""
    from . import aipatch as _aipatch
    sites = _aipatch.constant_sites(_scene_eb(donor, game=game, lang=lang))
    lines = [f"# patchable AI constants of scene {donor} ({len(sites)} sites)",
             f"# cite the offset in [[scene.ai_patch]] (at = <offset>, old = <value>, new = <same-width value>)"]
    for s in sites:
        lines.append(f"  at={s.offset:<6} {s.width}B  = {s.value:<8}  {s.where}")
    return "\n".join(lines)


def analyze_scene(donor: str, game=None, lang: str = "us") -> str:
    """Read a real battle scene's ``EVT_BATTLE_<donor>.eb`` LIVE from the install + disassemble its AI. ``donor``
    is the scene name after ``EVT_BATTLE_`` (e.g. ``EF_R007``). Raises on a missing install/donor."""
    return (f"# enemy AI of scene {donor} (EVT_BATTLE_{donor}, {lang})\n"
            + disassemble_ai(_scene_eb(donor, game=game, lang=lang)))
