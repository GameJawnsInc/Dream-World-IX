"""The ``.ebs`` SOURCE form — whole-file, byte-exact `.eb` round-trip (eb-roundtrip Rungs 2-3).

:func:`write_source` decompiles a complete field event binary to re-assemblable text;
:func:`assemble_source` is its exact inverse. Function bodies ride the proven
:mod:`ff9mapkit.eb.cmdasm` labeled source (jump/switch targets as ``L<n>`` labels); this module
adds the FILE ENVELOPE: header, the per-language name block, the entry table, and func tables.

Grammar v1 — frozen by the Rung-1 census (``studies/eb-roundtrip/FINDINGS.md``; measured over
all 818 field EVTs x 7 languages), hardened by the adversarial review (see git log):

    .ebs 1                                 format version (required, first directive)
    .byte2 N                               header byte [2] (only when != 2; census: always 2)
    .name <248 hex chars>                  the 124-byte name block [0x04..0x80), STORED VERBATIM
                                           (per-language; jp carries a 2nd name + binary blob)
    .entry I EMPTY [off=N]                 an empty entry-table slot
    .entry I type=T loc=L flags=F [pad=P] [off=N]     a non-empty slot
    .entry I loc=L flags=F [pad=P] [off=N] raw=<hex>  ESCAPE HATCH: the whole entry blob
                                           (type byte + func table + bodies) verbatim, for an
                                           entry whose func table cannot be represented
                                           structurally (e.g. the kit's blank-template entry 0)
    .gap off=N raw=<hex>                   ESCAPE HATCH: file bytes covered by NO entry's
                                           declared span, verbatim. The kit's blank-template
                                           lineage declares entry 0 SMALLER than its func
                                           table's reach, so its Main_Loop body physically
                                           lives between entries -- the engine reads funcs by
                                           fpos and never consults the size, so those orphan
                                           bytes are live code and must survive the round trip
    .func TAG                              a function of the current (non-raw) entry
    <cmdasm source lines>                  the function body (may be absent = zero-length func)

``#`` starts a comment anywhere; a leading UTF-8 BOM is tolerated. Every slot index
``0..slots-1`` must appear exactly once (max index 254 — the header slot count is a u8).
Everything not stored is DERIVED, per the census: entry bodies contiguous in slot order from
the table end; func tables canonical (``fpos[0] == funcCount*4``, ascending); an EMPTY slot's
``off`` = the next non-empty entry's off, trailing empties park at the LAST non-empty entry's
off (proven 38325/38325). The ``off=`` overrides exist because KIT-BUILT/EDITED files deviate
(stale parked offs after length-changing edits; append_entry places a middle slot's body at
EOF): the writer emits an override exactly where a file deviates from the derived layout, so
the toolkit's own output round-trips too — stock files emit none.

Safety stance: :func:`write_source` always SELF-VERIFIES — it reassembles its own output and
raises :class:`EbSrcError` on any byte difference — and every failure on either side
(unparseable input bytes, hand-authored source errors) is an :class:`EbSrcError` naming where,
never a raw traceback.

Rung 4 adds trailing ``#`` COMMENTS from the kit's own offline semantic layers (the logic map,
the model/item/scene/field catalogs, an optional parsed ``.mes``) — see the enrichment section
below. They are PRESENTATION: both parsers strip ``#`` before they see a token, so the
self-verify above reassembles the COMMENTED text and still demands byte equality.
"""
from __future__ import annotations

import re
from struct import error as struct_error

from . import cmdasm, disasm, exprasm
from .model import EbScript, ENTRY_TABLE_OFF
from ..eventscan import INIT_OPS, PARTY_UIDS, armed_slot

NAME_END = ENTRY_TABLE_OFF                  # the name block is [0x04..0x80)
NAME_LO = 4
NAME_LEN = NAME_END - NAME_LO               # 124 bytes
FORMAT_VERSION = 1
MAX_SLOT = 254                              # slot count lives in a u8: 255 slots -> max index 254

# error classes the per-function assembler can raise on hand-authored bodies; all are converted
# to EbSrcError with entry/tag context (exprasm.AssembleError is a ValueError but NOT a
# CmdAsmError; a non-numeric immediate raises int()'s ValueError; a malformed operand list can
# IndexError inside the encoder)
_BODY_ERRORS = (cmdasm.CmdAsmError, exprasm.AssembleError, ValueError, IndexError)


class EbSrcError(ValueError):
    pass


# --------------------------------------------------------------------------- comment enrichment
#
# Everything below only ever APPENDS ``  # <one line>`` to a source line. It cannot move a byte:
# ``_parse`` and ``cmdasm._parse_line`` both do ``line.split("#", 1)[0]`` before they tokenize, so
# write_source's self-verify reassembles the commented text and still demands equality. The whole
# layer is OFFLINE -- no install access happens in this module; the caller passes any parsed
# ``.mes`` entries / manifest field names in (the CLI reads them, ebsrc never does).

_PREVIEW_WIDTH = 60          # dialogue preview budget in characters (logic_map._line_text's default)
_MAX_COMMENT = 200           # hard ceiling: a comment is always ONE readable line

_FIELD_OP = 0x2B             # Field(dest)                    -- a field-to-field warp
_BATTLE_OP = 0x2A            # Battle(rush, btlId)            -- scene = btlId & 0x7FFF, arg 1
_BATTLE_EX_OP = 0x8C         # BattleEx(rush, group, btlId)   -- same mask, btlId at arg 2
_RANDOM_BATTLES_OP = 0x3C    # SetRandomBattles(pattern, s1..s4)
_SET_MODEL_OP = 0x2F         # SetModel(model, animset)
_ADD_ITEM_OP = 0x48          # AddItem(item, count)
_REMOVE_ITEM_OP = 0x49       # RemoveItem(item, count)
_INIT_OBJECT_OP = 0x09       # InitObject(entry, arg)         -- one of eventscan.INIT_OPS
_BATTLE_SCENE_MASK = 0x7FFF  # btlId bit 15 is Steiner's state, not the scene (eventscan)
_BATTLE_ARG = {_BATTLE_OP: 1, _BATTLE_EX_OP: 2}      # where each battle op's btlId sits

# The THREE ops that arm an entry (``eventscan.INIT_OPS``, operand 0 = the entry index): what each
# says, and how it reads when the operand is an expression the engine only resolves at runtime.
# An entry armed by ANY of them is live -- reading only InitObject calls 77% of the corpus's labeled
# entries "defined, not spawned" when the field arms them as code (0x07) or as a region (0x08).
_INIT_FACT = {
    0x09: ("spawn entry", "spawns an entry chosen at runtime"),
    0x07: ("arm code entry", "arms a code entry chosen at runtime"),
    0x08: ("arm region entry", "arms a region entry chosen at runtime"),
}

# a GLOB story-flag index inside a pretty-printed expression operand -- the ONE place this layer
# reads decoded TEXT rather than an opcode, because a flag ref is a token of the expression tree,
# not an instruction operand of its own.
_FLAG_RE = re.compile(r"Global\.Bit\[(\d+)\]")

_GAP_NOTE = ("gap: bytes covered by NO entry's declared span -- live code the engine reaches by "
             "func fpos, kept verbatim")


def _one_line(text, width: int = _MAX_COMMENT) -> str:
    """Any text -> ONE comment-safe line. A ``#`` inside a comment is harmless; a NEWLINE would
    turn the tail into a source line, so every whitespace run (incl. newlines/tabs) collapses to a
    single space and the result is truncated."""
    s = " ".join(str(text).split())
    return (s[:max(width - 3, 0)] + "...") if len(s) > width else s


def _annot(line: str, comment) -> str:
    """``line`` with a trailing ``# comment`` (or unchanged when there is nothing to say)."""
    c = _one_line(comment) if comment else ""
    return f"{line}  # {c}" if c else line


class _Enrichment:
    """The offline semantic layer behind the writer's comments: ONE
    :func:`ff9mapkit.logic_map.build_logic_map` over the whole file (entry roles, per-routine
    summaries, flag banding) plus a per-instruction pass joined to the disassembler BY ABSOLUTE
    OFFSET (``func.abs_start + rel_off == Instr.off``). Pure and deterministic: same bytes + same
    ``mes_entries``/``field_names`` -> same text.

    EVERY comment is computed HERE, in ``__init__`` -- the accessors are dict lookups that cannot
    raise. That is deliberate: :func:`_build_enrichment` guards construction, so precomputing puts
    the whole naming layer inside that guard and leaves no path where a catalog defect reaches the
    line emitter (and the byte-exact round trip) mid-write."""

    def __init__(self, data: bytes, eb: EbScript, *, mes_entries=None, field_names=None):
        from .. import logic_map as _lm
        self._lm = _lm
        self.degraded = ""
        try:
            self.lm = _lm.build_logic_map(data, entries=mes_entries, field_names=field_names)
        except Exception as ex:      # noqa: BLE001 -- keep the per-instruction half
            # A file whose func table LIES (the kit's blank-template lineage points an fpos past
            # the entry end -- the same shape that makes the writer fall back to raw=) sends the
            # whole-file scanner walking garbage. The per-instruction pass below clamps per func,
            # so it survives: keep those comments, drop only the structural labels, and SAY SO.
            self.lm = _lm.LogicMap()
            self.degraded = f"entry/routine labels unavailable ({type(ex).__name__}: {ex})"
        self.info = {e.index: e for e in self.lm.entries}
        # build_logic_map appends exactly one Node per func, in entry-then-func order -- so a
        # POSITIONAL join is exact even when an entry repeats a tag (which a (entry, tag) key
        # would silently collapse)
        self.nodes: dict = {}
        for n in self.lm.nodes:
            self.nodes.setdefault(n.entry, []).append(n)
        self.mes = mes_entries or {}
        self.names = field_names or {}
        # `iter_code` gives the TYPED operands (imm/expr) but renders an expression in the RAW
        # `opC4(191)` token form; a flag ref is only recognizable in the NAMED `Global.Bit[191]`
        # form, which comes from the pretty renderer. So walk both and join by offset -- exactly
        # what cmdasm.disassemble_items does. Both walks are KEPT (`self.decoded`, keyed on the
        # func's raw (abs_start, abs_end)) and handed back to `disassemble_items` via its
        # `predecoded=` kwarg, so the writer decodes each function ONCE instead of twice.
        from ..battle.battleai import _decode_func_pretty
        self.instr: dict[int, str] = {}
        self.decoded: dict = {}
        self.armed: dict = {}      # entry index -> how many Init* calls anywhere in the file arm it
        for e in eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                # clamp exactly as disassemble_items does, so the two walks stay aligned on a
                # forked/truncated .eb whose func claims bytes past the buffer
                lo, hi = f.abs_start, min(f.abs_end, len(data))
                try:
                    pretty = {off: (mn, ops) for off, mn, ops in _decode_func_pretty(data, lo, hi)}
                    instrs = list(disasm.iter_code(data, lo, hi))
                    # keyed on the RAW (abs_start, abs_end) the writer will ask with; the decode
                    # itself used the clamped hi, exactly as disassemble_items clamps
                    self.decoded[(f.abs_start, f.abs_end)] = (instrs, pretty)
                    for ins in instrs:
                        if ins.op in INIT_OPS:
                            self._note_arm(ins)
                        c = self._instr_comment(ins, (pretty.get(ins.off) or ("", ()))[1])
                        if c:
                            self.instr[ins.off] = c
                except (IndexError, ValueError, KeyError):
                    continue          # a lying func table walks garbage -- that entry emits raw=
        self.entry_c = {e.index: self._entry_comment(e.index) for e in self.lm.entries}
        self.func_c = {(ei, fi): self._func_comment(ei, fi)
                       for ei, ns in self.nodes.items() for fi in range(len(ns))}
        self.header = self._header_comment()

    # -- the emitted lines (pure lookups) ------------------------------------
    def header_comment(self) -> str:
        return self.header

    def entry_comment(self, index: int) -> str:
        return self.entry_c.get(index, "")

    def func_comment(self, entry_index: int, func_index: int) -> str:
        return self.func_c.get((entry_index, func_index), "")

    def instr_comment(self, abs_off: int) -> str:
        return self.instr.get(abs_off, "")

    def predecoded(self, abs_start: int, abs_end: int):
        """This func's already-decoded ``(instrs, pretty)`` for :func:`cmdasm.disassemble_items`,
        or None when it was never decodable here (the writer then decodes it itself and gets the
        same ``CmdAsmError`` -> ``raw=`` fallback it always did)."""
        return self.decoded.get((abs_start, abs_end))

    # -- the armed-entry set -------------------------------------------------
    def _note_arm(self, ins) -> None:
        """Record that this ``Init*`` instruction ARMS its operand-0 entry. The WHICH-slot decision
        is :func:`ff9mapkit.eventscan.armed_slot` -- the ONE owner of the armed semantics (all three
        ``INIT_OPS`` anywhere in the file; ``InitObject``'s 251-254 party selectors arm nothing) --
        shared with ``logic_map.EntryInfo.spawns``. Only the COUNTING lives here, fused into the
        comment walk so each function decodes once."""
        slot = armed_slot(ins)
        if slot is not None:
            self.armed[slot] = self.armed.get(slot, 0) + 1

    # -- how each is worded --------------------------------------------------
    _TAIL = "Comments are informational -- eb-asm strips every '#'."

    def _header_comment(self) -> str:
        if self.degraded:
            return f"{self.degraded}; per-instruction comments only. {self._TAIL}"
        used = sum(1 for e in self.lm.entries if e.role != "empty")
        text = "dialogue previews from the .mes" if self.mes else "no .mes given -- no line previews"
        return f"{used} entries, {len(self.lm.nodes)} routines; {text}. {self._TAIL}"

    def _entry_comment(self, index: int) -> str:
        e = self.info.get(index)
        if e is None or e.role == "empty":
            return ""
        head = self._lm.entry_label(e)
        if e.model_name:
            head += f" ({e.model_name})"
        elif e.model_id is not None:
            head += f" (model {e.model_id})"
        bits = [head]
        if e.talkable:
            bits.append("talkable")
        # self.armed, not EntryInfo.spawns: same semantics (both from eventscan.armed_slot), but
        # THIS walk is clamped + per-func fault-tolerant, so it still counts on a truncated .eb
        # where the whole-file scanner degraded
        arms = self.armed.get(index, 0)
        if e.role not in ("main", "player") and not arms:
            bits.append("defined, not spawned")
        elif arms > 1:
            bits.append(f"armed x{arms}")
        return ", ".join(bits)

    def _func_comment(self, entry_index: int, func_index: int) -> str:
        n = self.nodes[entry_index][func_index]
        label = self._lm.kind_label(n.kind)
        summary = self._lm.node_summary(n)
        return f"{label} -- {summary}" if summary else label

    # -- the per-instruction joins -------------------------------------------
    def _instr_comment(self, ins, pretty_ops=()) -> str:
        """The facts this instruction states, keyed on its OPCODE + decoded operands (never on the
        rendered mnemonic text -- the sole exception is a flag ref, which lives inside an
        expression, hence ``pretty_ops``). Several facts join with '; '."""
        op, facts = ins.op, []
        if op == _FIELD_OP:
            facts.append(self._field_fact(ins.imm(0)))
        elif op in _BATTLE_ARG:                          # Battle / BattleEx, same mask
            btl = ins.imm(_BATTLE_ARG[op])
            if btl is not None:
                facts.append(self._scene_fact(int(btl) & _BATTLE_SCENE_MASK))
        elif op == _RANDOM_BATTLES_OP:
            picks, named = [ins.imm(i) for i in range(1, 5)], []
            for s in picks:                             # the 4 slots often repeat ONE scene
                if s is not None and int(s) not in named:
                    named.append(int(s))
            if named:
                facts.append("random encounters: "
                             + ", ".join(self._scene_fact(s) for s in named))
        elif op == _SET_MODEL_OP:
            mid = ins.imm(0)
            if mid is not None:
                from .._modeldb import MODELS
                facts.append(MODELS.get(int(mid)) or f"unnamed model {int(mid)}")
        elif op in (_ADD_ITEM_OP, _REMOVE_ITEM_OP):
            iid = ins.imm(0)
            if iid is not None:
                from ..forkreport import item_label
                facts.append(item_label(int(iid)))
        elif op in _INIT_FACT:
            facts.append(self._init_fact(op, ins.imm(0)))
        elif op in self._lm.WINDOW_OPS and self.mes:
            txid = ins.imm(self._lm.WINDOW_OPS[op])
            preview = self._lm._line_text(self.mes, txid, _PREVIEW_WIDTH) if txid is not None else None
            if preview:
                facts.append(f'"{preview}"')
        facts.extend(self._flag_facts(pretty_ops))
        return "; ".join(f for f in facts if f)

    def _field_fact(self, dest) -> str:
        if dest is None:
            return "-> warp target computed at runtime"
        from .._fieldtable import FIELD_BY_ID
        fid = int(dest)
        row = FIELD_BY_ID.get(fid)
        friendly, evt = self.names.get(fid) or "", (row[1] if row else "")
        if friendly and evt:
            return f"-> {friendly} ({evt})"
        return f"-> {friendly or evt}" if (friendly or evt) else ""

    def _scene_fact(self, scene_id: int) -> str:
        from .. import catalog
        name = catalog.scene_name(scene_id)
        out = f"scene {scene_id}" + (f" {name}" if name else "")
        if catalog.is_model_bucket_scene(scene_id):     # a BSC_B3_* holder crashes as an encounter
            out += " -- NOT fightable (model bucket)"
        return out

    def _init_fact(self, op: int, slot) -> str:
        """What an ``Init*`` call arms, in that op's own words: an object SPAWNS, code and regions
        are ARMED. ``InitObject`` alone reads 251-254 as PARTY SLOTS (engine: ``partyUID[sid-251]``
        — a member of the CURRENT party, not entry 251), so those name the slot instead."""
        head, at_runtime = _INIT_FACT[op]
        if slot is None:
            return at_runtime
        slot = int(slot)
        if op == _INIT_OBJECT_OP and slot in PARTY_UIDS:
            return f"spawn party member (slot {PARTY_UIDS.index(slot)})"
        e = self.info.get(slot)
        bits = [self._lm.entry_label(e)] if (e is not None and e.role != "empty") else []
        if e is not None and e.model_name:
            bits.append(e.model_name)
        return f"{head} {slot}" + (f" ({', '.join(bits)})" if bits else "")

    def _flag_facts(self, pretty_ops) -> list:
        """``flag_phrase`` for each DISTINCT GLOB story-flag index this instruction's (pretty-
        rendered) operands touch -- the band (kit / Mognet lock / read-mail scratch) is what a
        reader needs, and it is the difference between a donor's own story bit and one this fork
        added."""
        out, seen = [], []
        for arg in pretty_ops:
            for m in _FLAG_RE.finditer(str(arg)):
                idx = int(m.group(1))
                if idx not in seen:
                    seen.append(idx)
                    out.append(self._lm.flag_phrase(idx))
        return out


def _build_enrichment(data: bytes, eb: EbScript, mes_entries, field_names):
    """``(_Enrichment, "")`` or ``(None, note)``. Comments are cosmetic and the whole-corpus gate
    runs through this path, so a defect in a NAMING layer must never cost the byte-exact round
    trip -- but the degradation is REPORTED in the output's header, never swallowed silently."""
    try:
        return _Enrichment(data, eb, mes_entries=mes_entries, field_names=field_names), ""
    except Exception as ex:                    # noqa: BLE001 -- presentation must not fail the writer
        return None, f"comments unavailable ({type(ex).__name__}: {ex})"


# --------------------------------------------------------------------------- writer (decompile)

def _structured_funcs(data: bytes, e, ctx=None) -> "list[str] | None":
    """The ``.func`` source lines for a well-formed entry, or None when the entry's func table
    cannot be represented structurally (non-canonical fpos, a func range outside the entry, or
    a body the labeled disassembler refuses) — the caller then falls back to ``raw=``.
    With ``ctx`` the lines carry explanatory comments (``disassemble_items`` gives one tuple per
    source line, so an instruction's comment joins on ``f.abs_start + rel_off``; a ``L<n>:`` label
    line has ``rel_off is None`` and never takes one) — and each body is handed the decode ``ctx``
    already did, so enriching costs no second pass over the bytecode."""
    fp = [f.fpos for f in e.funcs]
    if not fp or fp[0] != e.func_count * 4 or any(b <= a for a, b in zip(fp, fp[1:])):
        return None
    if any(f.abs_start > f.abs_end or f.abs_end > e.abs_end for f in e.funcs):
        return None
    lines: list[str] = []
    for f in e.funcs:
        head = f".func {f.tag}"
        lines.append(_annot(head, ctx.func_comment(e.index, f.index)) if ctx else head)
        if f.length:
            try:
                items = cmdasm.disassemble_items(
                    data, f.abs_start, f.abs_end,
                    predecoded=ctx.predecoded(f.abs_start, f.abs_end) if ctx else None)
            except cmdasm.CmdAsmError:
                return None
            if ctx is None:
                lines.append("\n".join(text for _off, text in items))
            else:
                lines.append("\n".join(
                    text if off is None else _annot(text, ctx.instr_comment(f.abs_start + off))
                    for off, text in items))
    return lines


def write_source(data: bytes, *, title: str = "", enrich: bool = True, mes_entries=None,
                 field_names=None) -> str:
    """Decompile a whole ``.eb`` to ``.ebs`` source. ``title`` becomes a leading comment line.
    ALWAYS self-verifies: the returned text reassembles (:func:`assemble_source`) to exactly
    ``data``, or this raises :class:`EbSrcError` (with the first differing offset).

    ``enrich`` (default on) appends explanatory ``#`` comments from the kit's offline semantic
    layers; ``enrich=False`` emits the bare grammar. ``mes_entries`` is a parsed ``.mes``
    (``{txid: MesEntry}``) so a dialogue window can preview its line, ``field_names`` a
    ``{field_id: friendly}`` map so a ``Field()`` warp can name its destination — both optional,
    both supplied by the CALLER (this module never touches the install)."""
    try:
        eb = EbScript.from_bytes(data)
    except (ValueError, IndexError, struct_error) as ex:
        raise EbSrcError(f"not a parseable .eb: {ex}") from ex
    ctx, note = _build_enrichment(data, eb, mes_entries, field_names) if enrich else (None, "")
    lines: list[str] = []
    if title:
        lines.append(f"# {_one_line(title)}")
    if ctx is not None or note:
        lines.append(f"# {_one_line(note or ctx.header_comment())}")
    lines.append(f".ebs {FORMAT_VERSION}")
    if data[2] != 2:
        lines.append(f".byte2 {data[2]}")
    lines.append(f".name {data[NAME_LO:NAME_END].hex()}")

    nonempty = [e for e in eb.entries if not e.empty]
    if not nonempty:
        raise EbSrcError("this .eb has no non-empty entries -- nothing to decompile")
    # the assembler's placement cursor, replayed on the ACTUAL offs: an entry (or empty slot)
    # matching the derived value emits no off=; a deviating one gets an explicit override
    pos = eb.entry_count * 8
    for e in eb.entries:
        slot = data[ENTRY_TABLE_OFF + e.index * 8: ENTRY_TABLE_OFF + (e.index + 1) * 8]
        pad = int.from_bytes(slot[6:8], "little")
        if e.empty:
            nxt = next((n for n in eb.entries[e.index + 1:] if not n.empty), None)
            want = nxt.off if nxt is not None else nonempty[-1].off
            head = f".entry {e.index} EMPTY"
            if e.off != want:
                head += f" off={e.off}"
            lines.append(head)
            continue
        head = f".entry {e.index} type={e.type} loc={e.loc} flags={e.flags}"
        if pad:
            head += f" pad={pad}"
        if e.off != pos:
            head += f" off={e.off}"
        pos = max(pos, e.off + e.size)
        funcs = _structured_funcs(data, e, ctx)
        comment = ctx.entry_comment(e.index) if ctx else ""
        if funcs is None:                    # the escape hatch: entry blob verbatim
            blob = data[e.abs_start:e.abs_end].hex()
            lines.append(_annot(head.replace(f" type={e.type}", "", 1) + f" raw={blob}", comment))
        else:
            lines.append(_annot(head, comment))
            lines.extend(funcs)

    # bytes covered by NO entry span (blank-template overhang code, EOF slack) -> .gap records
    covered = bytearray(len(data))
    covered[:ENTRY_TABLE_OFF + eb.entry_count * 8] = b"\x01" * (ENTRY_TABLE_OFF + eb.entry_count * 8)
    for e in nonempty:
        covered[e.abs_start:e.abs_end] = b"\x01" * (e.abs_end - e.abs_start)
    i = 0
    while i < len(data):
        if covered[i]:
            i += 1
            continue
        j = i
        while j < len(data) and not covered[j]:
            j += 1
        lines.append(_annot(f".gap off={i - ENTRY_TABLE_OFF} raw={data[i:j].hex()}",
                            _GAP_NOTE if ctx else ""))
        i = j
    src = "\n".join(lines) + "\n"

    out = assemble_source(src)
    if out != data:
        n = min(len(out), len(data))
        at = next((i for i in range(n) if out[i] != data[i]), n)
        raise EbSrcError(
            f"self-verify failed: reassembly differs at byte {at} "
            f"(source {len(data)}B, reassembled {len(out)}B) -- this file has a layout the "
            f".ebs grammar cannot yet express (uncovered gap bytes or EOF slack?); please "
            f"report it (studies/eb-roundtrip/FINDINGS.md)")
    return src


# --------------------------------------------------------------------------- parser + assembler

def _int_attr(lineno: int, k: str, v: str) -> int:
    try:
        return int(v, 0)
    except ValueError as ex:
        raise EbSrcError(f"line {lineno}: attribute {k}={v!r} is not an integer") from ex


def _parse_entry_attrs(lineno: int, idx: int, tokens) -> dict:
    """The key=value tail of a non-EMPTY .entry line -> {ints... , 'raw': bytes|None}."""
    out: dict = {"raw": None}
    seen: set = set()
    for t in tokens:
        if "=" not in t:
            raise EbSrcError(f"line {lineno}: malformed attribute {t!r} (want key=value)")
        k, _, v = t.partition("=")
        if k in seen:
            raise EbSrcError(f"line {lineno}: duplicate attribute {k!r}")
        seen.add(k)
        if k == "raw":
            try:
                out["raw"] = bytes.fromhex(v)
            except ValueError as ex:
                raise EbSrcError(f"line {lineno}: raw= is not valid hex") from ex
        elif k in ("type", "loc", "flags", "pad", "off"):
            out[k] = _int_attr(lineno, k, v)
        else:
            raise EbSrcError(f"line {lineno}: unknown attribute {k!r}")
    if out["raw"] is not None:
        if "type" in out:
            raise EbSrcError(f"line {lineno}: a raw= entry carries no type= "
                             f"(the type byte is inside the raw blob)")
        if len(out["raw"]) < 2:
            raise EbSrcError(f"line {lineno}: raw= blob must be at least 2 bytes (type + funcCount)")
    elif "type" not in out:
        raise EbSrcError(f"line {lineno}: .entry {idx} needs type= (or raw=/EMPTY)")
    return out


def _parse(text: str):
    """Parse ``.ebs`` text -> (byte2, name_bytes, entries): a dense list over slots 0..N-1 of
    dicts — ``{'empty': True, 'off': int|None}`` or
    ``{'empty': False, type/loc/flags/pad/off, 'raw': bytes|None, 'funcs': [(tag, [lines])]}``."""
    text = text.lstrip(chr(0xFEFF))     # tolerate a UTF-8 BOM from Windows editors
    byte2 = 2
    name: bytes | None = None
    seen_version = False
    entries: dict[int, dict] = {}
    gaps: list[tuple[int, bytes]] = []      # (rel off, verbatim bytes) uncovered by any entry
    cur: dict | None = None                 # the open structured (non-raw) entry
    cur_func: list | None = None            # its open function's body-line list

    for lineno, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if not line.startswith("."):
            # a cmdasm body line (instruction or L<n>: label) of the open function
            if cur_func is None:
                raise EbSrcError(f"line {lineno}: instruction outside a .func block: {line!r}")
            cur_func.append(line)
            continue
        tok = line.split()
        d = tok[0]
        if not seen_version:
            if d != ".ebs":
                raise EbSrcError(f"line {lineno}: the first directive must be '.ebs {FORMAT_VERSION}'")
            if len(tok) != 2 or tok[1] != str(FORMAT_VERSION):
                raise EbSrcError(f"line {lineno}: unsupported .ebs version {tok[1:]!r} "
                                 f"(this tool reads version {FORMAT_VERSION})")
            seen_version = True
            continue
        if d == ".ebs":
            raise EbSrcError(f"line {lineno}: duplicate .ebs directive")
        if d == ".byte2":
            if len(tok) != 2:
                raise EbSrcError(f"line {lineno}: .byte2 takes one integer")
            byte2 = _int_attr(lineno, ".byte2", tok[1])
            if not 0 <= byte2 <= 255:
                raise EbSrcError(f"line {lineno}: .byte2 {byte2} out of u8 range")
        elif d == ".name":
            if name is not None:
                raise EbSrcError(f"line {lineno}: duplicate .name")
            if len(tok) != 2:
                raise EbSrcError(f"line {lineno}: .name takes one hex string")
            try:
                name = bytes.fromhex(tok[1])
            except ValueError as ex:
                raise EbSrcError(f"line {lineno}: .name is not valid hex") from ex
            if len(name) != NAME_LEN:
                raise EbSrcError(f"line {lineno}: .name must be {NAME_LEN} bytes ({NAME_LEN * 2} hex chars), "
                                 f"got {len(name)}")
        elif d == ".entry":
            if len(tok) < 3:
                raise EbSrcError(f"line {lineno}: .entry needs an index and EMPTY or attributes")
            idx = _int_attr(lineno, "entry index", tok[1])
            if idx < 0 or idx > MAX_SLOT:
                raise EbSrcError(f"line {lineno}: entry index {idx} out of range 0..{MAX_SLOT} "
                                 f"(the slot count is a u8, so {MAX_SLOT} is the highest index)")
            if idx in entries:
                raise EbSrcError(f"line {lineno}: duplicate .entry {idx}")
            if tok[2] == "EMPTY":
                off = None
                for t in tok[3:]:
                    k, _, v = t.partition("=")
                    if k != "off" or not v:
                        raise EbSrcError(f"line {lineno}: .entry EMPTY takes only an off= override")
                    if off is not None:
                        raise EbSrcError(f"line {lineno}: duplicate attribute 'off'")
                    off = _int_attr(lineno, "off", v)
                entries[idx] = {"empty": True, "off": off}
                cur, cur_func = None, None
            else:
                attrs = _parse_entry_attrs(lineno, idx, tok[2:])
                e = {"empty": False, "type": attrs.get("type"), "loc": attrs.get("loc", 0),
                     "flags": attrs.get("flags", 0), "pad": attrs.get("pad", 0),
                     "off": attrs.get("off"), "raw": attrs["raw"], "funcs": []}
                entries[idx] = e
                if e["raw"] is not None:
                    cur, cur_func = None, None    # a raw entry has no .func blocks
                else:
                    cur, cur_func = e, None
        elif d == ".gap":
            g_off, g_raw = None, None
            for t in tok[1:]:
                k, _, v = t.partition("=")
                if k == "off" and g_off is None and v:
                    g_off = _int_attr(lineno, "off", v)
                elif k == "raw" and g_raw is None and v:
                    try:
                        g_raw = bytes.fromhex(v)
                    except ValueError as ex:
                        raise EbSrcError(f"line {lineno}: .gap raw= is not valid hex") from ex
                else:
                    raise EbSrcError(f"line {lineno}: .gap takes exactly off= and raw=")
            if g_off is None or g_raw is None or not g_raw:
                raise EbSrcError(f"line {lineno}: .gap takes exactly off= and raw= (non-empty)")
            gaps.append((g_off, g_raw))
        elif d == ".func":
            if cur is None:
                raise EbSrcError(f"line {lineno}: .func outside a non-empty structured .entry "
                                 f"(EMPTY and raw= entries take no .func blocks)")
            if len(tok) != 2:
                raise EbSrcError(f"line {lineno}: .func takes one tag integer")
            tag = _int_attr(lineno, ".func tag", tok[1])
            if not 0 <= tag <= 0xFFFF:
                raise EbSrcError(f"line {lineno}: .func tag {tag} out of u16 range")
            cur_func = []
            cur["funcs"].append((tag, cur_func))
        else:
            raise EbSrcError(f"line {lineno}: unknown directive {d!r}")

    if not seen_version:
        raise EbSrcError("empty source (missing .ebs directive)")
    if name is None:
        raise EbSrcError("missing .name directive")
    if not entries:
        raise EbSrcError("no .entry directives")
    slots = max(entries) + 1
    missing = [i for i in range(slots) if i not in entries]
    if missing:
        raise EbSrcError(f"missing .entry for slot(s) {missing} (every slot 0..{slots - 1} must appear)")
    return byte2, name, [entries[i] for i in range(slots)], gaps


def assemble_source(text: str) -> bytes:
    """Assemble ``.ebs`` source -> the complete ``.eb`` bytes (the exact inverse of
    :func:`write_source`). Entry offs/sizes, func-table fpos, and empty-slot offs are derived
    per the census-proven layout rules; explicit ``off=`` / ``raw=`` overrides win where given."""
    byte2, name, entries, gaps = _parse(text)

    # -- per-entry blobs --
    blobs: list[bytes | None] = []
    for idx, e in enumerate(entries):
        if e["empty"]:
            blobs.append(None)
            continue
        if e["raw"] is not None:
            blobs.append(e["raw"])
            continue
        if not 0 <= e["type"] <= 255:
            raise EbSrcError(f"entry {idx}: type {e['type']} out of u8 range")
        fc = len(e["funcs"])
        if not 1 <= fc <= 255:
            raise EbSrcError(f"entry {idx}: needs 1..255 .func blocks, has {fc}")
        table = bytearray()
        bodies = bytearray()
        fpos = fc * 4
        for tag, body_lines in e["funcs"]:
            body = b""
            if body_lines:
                try:
                    body = cmdasm.assemble_block("\n".join(body_lines))
                except _BODY_ERRORS as ex:
                    raise EbSrcError(f"entry {idx} tag {tag}: {ex}") from ex
            if fpos > 0xFFFF:
                raise EbSrcError(f"entry {idx}: func table overflows u16 fpos at tag {tag}")
            table += tag.to_bytes(2, "little") + fpos.to_bytes(2, "little")
            bodies += body
            fpos += len(body)
        blobs.append(bytes([e["type"], fc]) + bytes(table) + bytes(bodies))

    if all(b is None for b in blobs):
        raise EbSrcError("a .eb needs at least one non-empty entry (the empty-slot off rule "
                         "is undefined with none)")

    # -- placement: derived cursor in slot order; an explicit off= wins and the cursor tracks
    #    the furthest end, so out-of-order physical layouts (append_entry) are representable --
    slots = len(blobs)
    offs: list[int | None] = [None] * slots
    pos = slots * 8                                       # rel to ENTRY_TABLE_OFF
    for i, b in enumerate(blobs):
        if b is None:
            continue
        off = entries[i]["off"]
        offs[i] = off if off is not None else pos
        if not 0 <= offs[i] <= 0xFFFF:
            raise EbSrcError(f"entry {i}: off {offs[i]} out of the u16 offset space")
        if offs[i] < slots * 8:
            raise EbSrcError(f"entry {i}: off {offs[i]} overlaps the entry table")
        pos = max(pos, offs[i] + len(b))
    nonempty = [i for i, b in enumerate(blobs) if b is not None]
    last_off = offs[nonempty[-1]]
    empty_offs: list[int | None] = [None] * slots
    for i in range(slots):
        if offs[i] is not None:
            continue
        explicit = entries[i]["off"]
        if explicit is not None:
            empty_offs[i] = explicit
        else:
            nxt = next((offs[j] for j in range(i + 1, slots) if offs[j] is not None), None)
            empty_offs[i] = nxt if nxt is not None else last_off
        if not 0 <= empty_offs[i] <= 0xFFFF:
            raise EbSrcError(f"entry {i}: empty-slot off {empty_offs[i]} out of u16 range")

    # -- header + name + table + bodies (placed at their offs; derived layouts are contiguous) --
    for g_off, g_raw in gaps:
        if g_off < slots * 8:
            raise EbSrcError(f".gap off={g_off} overlaps the entry table")
        pos = max(pos, g_off + len(g_raw))
    total = ENTRY_TABLE_OFF + max(pos, slots * 8)
    out = bytearray(total)
    out[0:2] = b"EV"
    out[2] = byte2
    out[3] = slots
    out[NAME_LO:NAME_END] = name
    for i, b in enumerate(blobs):
        e = entries[i]
        off = offs[i] if b is not None else empty_offs[i]
        sz = len(b) if b is not None else 0
        loc = e.get("loc", 0) or 0
        flags = e.get("flags", 0) or 0
        pad = e.get("pad", 0) or 0
        for v, nm in ((sz, "size"), (loc, "loc"), (flags, "flags"), (pad, "pad")):
            hi = 0xFFFF if nm in ("size", "pad") else 0xFF
            if not 0 <= v <= hi:
                raise EbSrcError(f"entry {i}: {nm} {v} out of range")
        base = ENTRY_TABLE_OFF + i * 8
        out[base:base + 2] = off.to_bytes(2, "little")
        out[base + 2:base + 4] = sz.to_bytes(2, "little")
        out[base + 4] = loc
        out[base + 5] = flags
        out[base + 6:base + 8] = pad.to_bytes(2, "little")
        if b is not None:
            out[ENTRY_TABLE_OFF + off: ENTRY_TABLE_OFF + off + len(b)] = b
    for g_off, g_raw in gaps:
        out[ENTRY_TABLE_OFF + g_off: ENTRY_TABLE_OFF + g_off + len(g_raw)] = g_raw
    return bytes(out)
