"""Graft a real field object's VERBATIM ``.eb`` entry into a fork -- faithful object carry.

The faithful alternative to the player-clone synthesis (:mod:`content.npc` / :mod:`content.prop`):
instead of re-synthesizing an imported NPC/prop by cloning the player and swapping the model (which
renders it upside-down / mis-sized -- "Zidane in a barrel skin"), this APPENDS the donor object's real
entry bytes at a free slot and arms it from ``Main_Init``, remapping only its explicit slot/uid
references. The object then renders byte-identical to the source field.

This is the generalization of :func:`content.ladder.inject_ladder`'s ``sequences`` graft (append a
helper entry at a free slot + remap its ``STARTSEQ`` arg) from one helper function to a whole object
entry + its instancing. The specs come from :func:`ff9mapkit.eventscan.scan_objects_verbatim` (or an
import ``[[object]]`` sidecar); each carries the verbatim entry bytes, the ``carry_tags`` subset
(``init_only`` objects drop interactive funcs that call a player tag a blank fork lacks), the
``InitObject`` instances, and -- when the object is positioned from ``Main_Init``'s D9 vars rather than
self-positioning -- the ``needs_d9`` placement. Full recipe + the cross-reference remap table:
``docs/OBJECT_CARRY.md``. The AUTHORED ``[[npc]]``/``[[prop]]`` path is untouched -- this is import-only.
"""
from __future__ import annotations

import struct

from .. import eventscan
from ..binutils import u16
from ..eb import EbScript, edit, opcodes
from ..eb.disasm import argsize
from . import region as _region


def carry_bytes(entry_bytes, carry_tags=None) -> bytes:
    """Return the entry holding only ``carry_tags`` functions (``None`` = the whole entry, verbatim).

    Re-emits the type byte + a rebuilt function table + the kept bodies VERBATIM (intra-func jumps are
    function-relative, so dropping a sibling function never disturbs a kept one; ``fpos`` is recomputed
    for the new layout). ``carry_tags=None`` (or a superset of the entry's tags) round-trips byte-for-byte.
    """
    b = bytes(entry_bytes)
    etype, fc = b[0], b[1]
    funcs = [(u16(b, 2 + i * 4), u16(b, 2 + i * 4 + 2)) for i in range(fc)]      # (tag, fpos)
    bodies = []
    for i, (tag, fpos) in enumerate(funcs):
        start = 2 + fpos                              # fpos is relative to entryStart+2 (= slice offset 2)
        end = (2 + funcs[i + 1][1]) if i + 1 < fc else len(b)
        bodies.append((tag, b[start:end]))
    if carry_tags is not None:
        keep = set(carry_tags)
        bodies = [(t, body) for t, body in bodies if t in keep]
    table, pos = b"", len(bodies) * 4
    for tag, body in bodies:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
    return bytes([etype, len(bodies)]) + table + b"".join(body for _, body in bodies)


def _arg_byte_offset(ins, ai):
    """Byte offset (relative to ``ins.off``) of immediate operand ``ai``. Decoder-derived (opcode head +
    the argflag byte when present + the widths of the preceding immediates), so it is correct for both
    the no-argflag low opcodes (``Init*`` < 0x10) and the argflag-carrying ones -- unlike the ladder's
    fixed ``+2``. Returns None if a preceding operand is an expression (variable width)."""
    off = 2 if ins.op >= 0x100 else 1                 # opcode head (0xFF-paged = 2 bytes)
    if ins.op >= 0x10 and len(ins.args) != 0:         # the argflag bitmask byte
        off += 1
    for k in range(ai):
        if k < len(ins.arg_is_expr) and ins.arg_is_expr[k]:
            return None
        off += argsize(ins.op, k)
    return off


def _remap_value(kind, val, donor_idx, new_slot, donor_player_entry, donor2new):
    """Remap one slot/uid value when an entry moves ``donor_idx`` -> ``new_slot`` (docs/OBJECT_CARRY.md S3)."""
    if val == donor_idx:                              # self by slot / entry index -> the new slot
        return new_slot
    if kind == "uid":
        if val in (eventscan.UID_PLAYER, eventscan.UID_SELF) or val in eventscan.PARTY_UIDS:
            return val                                # engine specials -- slot-independent, kept
        if donor_player_entry is not None and val == donor_player_entry:
            return eventscan.UID_PLAYER               # player BY ENTRY INDEX -> the controlUID alias 250
    if val in donor2new:                              # a carried sibling -> its new slot
        return donor2new[val]
    return val                                        # uncarried (a kept func never has one) -> leave


def remap_entry_refs(data, slot, donor_idx, donor_player_entry, donor2new, player_tag_remap=None) -> bytes:
    """Same-length, in-place remap of every slot/uid reference the grafted entry at ``slot`` makes.
    Patches each :data:`ff9mapkit.eventscan.REF_OPS` immediate operand byte via the decoder-derived
    offset (never a fixed +N); only width-1 operands are touched, so internal jumps survive untouched.

    ``player_tag_remap`` (the player-function graft, docs/PLAYER_GRAFT.md): when an object ``RunScript``s
    the PLAYER, the called function moved to a fresh fork tag, so this also remaps the RunScript TAG (arg2)
    -- but ONLY when the call targets the player (uid 250 or the donor player entry index); a self/sibling
    call's tag lives in that object's own tag space and is left verbatim (the field-122 cask's tag-2 has
    BOTH forms: ``RunScript(player, 24)`` -> remap, ``RunScript(self, 30)`` -> keep)."""
    eb = EbScript.from_bytes(data)
    b = bytearray(data)
    for f in eb.entry(slot).funcs:
        for ins in eb.instrs(f):
            spec = eventscan.REF_OPS.get(ins.op)
            if not spec:
                continue
            for kind in ("slot", "uid"):
                for ai in spec.get(kind, ()):
                    if ai >= len(ins.arg_is_expr) or ins.arg_is_expr[ai]:
                        continue
                    val = ins.imm(ai)
                    if val is None:
                        continue
                    if kind == "uid" and ins.op in eventscan.INIT_OPS and val == 0:
                        continue                      # uid 0 aliases the slot -- not an explicit ref
                    new = _remap_value(kind, val, donor_idx, slot, donor_player_entry, donor2new)
                    if new == val:
                        continue
                    bo = _arg_byte_offset(ins, ai)
                    if bo is None or argsize(ins.op, ai) != 1:
                        continue                      # only same-length 1-byte operands are patchable
                    b[ins.off + bo] = new & 0xFF
            if player_tag_remap and ins.op in eventscan.RUNSCRIPT_OPS:      # site (a): the called PLAYER tag
                uid, tag = ins.imm(1), ins.imm(2)
                if (uid == eventscan.UID_PLAYER or (donor_player_entry is not None and uid == donor_player_entry)) \
                        and tag in player_tag_remap:
                    bo = _arg_byte_offset(ins, 2)
                    if bo is not None and argsize(ins.op, 2) == 1:
                        b[ins.off + bo] = player_tag_remap[tag] & 0xFF
    return bytes(b)


def _arm(data, slot, arg, needs_d9):
    """Spawn the grafted object from ``Main_Init``. A self-positioning object arms with a shift-free
    ``InitObject`` (overwrite a ``Wait`` filler, else insert). A ``Main_Init``-D9-positioned object gets
    its D9 placement set immediately before the ``InitObject`` (one inserted block, so the order holds)."""
    if needs_d9:
        # TOML inline-table keys arrive as strings ("0"/"4"); coerce to the int var index the engine reads
        block = b"".join(_region.set_var(eventscan.POS_VAR_CLASS, idx, val)
                         for idx, val in sorted((int(i), int(v)) for i, v in needs_d9.items()))
        block += opcodes.init_object(slot, arg)
        f0 = EbScript.from_bytes(data).entry(0).func_by_tag(0)
        if f0 is None:
            raise ValueError("field has no Main_Init (entry 0 tag 0) to arm the object from")
        return edit.insert_bytes(data, f0.abs_start, block)
    return edit.activate(data, opcodes.init_object(slot, arg))


def graft_objects(data, specs, *, load=None, player_tag_remap=None, out_slot_map=None) -> bytes:
    """Graft each spec's VERBATIM object entry into ``data`` and arm it. ``specs`` come from
    :func:`ff9mapkit.eventscan.scan_objects_verbatim` (entry bytes inline) or an import sidecar (a ``bin``
    ref + a ``load(ref) -> bytes`` callable). Objects flagged ``graft_safety == "refuse"`` are skipped
    (the importer leaves those to the authored ``[[npc]]``/``[[prop]]`` path). Returns the new bytes.

    Two passes, like the ladder ``sequences`` graft: (1) append every entry first so all new slots exist
    (so a sibling cross-reference can resolve); (2) remap each entry's references + arm it from Main_Init.

    ``out_slot_map`` (optional): a dict the caller passes in; on return it holds ``{donor_idx: fork_slot}``
    for every grafted (non-refused) object. The text-carry path (:mod:`content.textcarry`) needs it to find
    each grafted entry and remap its window TXIDs; existing callers omit it and are unaffected.
    """
    specs = [s for s in specs if s.get("graft_safety") != "refuse"]
    if not specs:
        return data
    donor2new, appended = {}, []
    for s in specs:                                   # PASS 1 -- reserve every slot
        raw = s.get("entry_bytes")
        if raw is None:
            if load is None:
                raise ValueError(f"object spec {s.get('donor_idx')} has no entry_bytes and no loader")
            raw = load(s["bin"])
        raw = carry_bytes(raw, s.get("carry_tags"))
        slot = EbScript.from_bytes(data).first_free_slot()
        data = edit.append_entry(data, slot, raw)
        donor2new[int(s["donor_idx"])] = slot
        appended.append((s, slot))
    for s, slot in appended:                          # PASS 2 -- remap references + arm from Main_Init
        data = remap_entry_refs(data, slot, int(s["donor_idx"]), s.get("donor_player_entry"), donor2new,
                                player_tag_remap)
        for inst in (s.get("instances") or [{"arg": 0}]):
            data = _arm(data, slot, int(inst.get("arg", 0)), s.get("needs_d9") or {})
    if out_slot_map is not None:
        out_slot_map.update(donor2new)
    return data
