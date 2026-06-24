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
from ..eb.disasm import argsize, expr_obj_uid_offsets, iter_code
from . import region as _region

_LOOP_TAG = 1             # an object's per-frame LOOP function
_FIELD_OP = 0x2B          # Field(dest) -- a warp; in an object's LOOP it makes the object a cutscene director


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


def _loop_warps(entry_bytes) -> bool:
    """True if the entry's LOOP (tag 1) fires a ``Field()`` warp -- a cutscene WARP director carried as an NPC.
    A SYNTHESIZED fork must NOT carry these: their loop re-fires the warp / cast-rotation against the asserted
    beat (the #13 stacked-spawn / warp-out bug seen forking the Dali shop). Checked on the CARRIED bytes, so an
    ``init_only`` object whose loop was already dropped is NOT flagged (it still renders). Only an actual
    ``Field()`` flags it -- phase-switch-only animated props and the save Moogle (no LOOP warp) are unaffected,
    so the proven prop/save-point carries keep working; ``--verbatim`` keeps directors whole regardless."""
    b = bytes(entry_bytes)
    if len(b) < 2:
        return False
    fc = b[1]
    funcs = [(u16(b, 2 + i * 4), u16(b, 2 + i * 4 + 2)) for i in range(fc)]
    for i, (tag, fpos) in enumerate(funcs):
        if tag != _LOOP_TAG:
            continue
        start = 2 + fpos
        end = (2 + funcs[i + 1][1]) if i + 1 < fc else len(b)
        return any(ins.op == _FIELD_OP for ins in iter_code(b, start, end))
    return False


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
    """Remap one slot/uid value when an entry moves ``donor_idx`` -> ``new_slot`` (docs/OBJECT_CARRY.md S3).
    ``donor_player_entry`` is the primary PC entry index (int) OR the full collection of PC entry indices
    (a field with several ``DefinePlayerCharacter`` entries -- ANY of them aliases the controlUID 250)."""
    if val == donor_idx:                              # self by slot / entry index -> the new slot
        return new_slot
    if kind == "uid":
        if val in (eventscan.UID_PLAYER, eventscan.UID_SELF) or val in eventscan.PARTY_UIDS:
            return val                                # engine specials -- slot-independent, kept
        if eventscan._is_player_entry(val, donor_player_entry):
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
            if spec:
                for kind in ("slot", "uid"):
                    for ai in spec.get(kind, ()):
                        if ai >= len(ins.arg_is_expr) or ins.arg_is_expr[ai]:
                            continue
                        val = ins.imm(ai)
                        if val is None:
                            continue
                        if kind == "uid" and ins.op in eventscan.INIT_OPS and val == 0:
                            continue                  # uid 0 aliases the slot -- not an explicit ref
                        new = _remap_value(kind, val, donor_idx, slot, donor_player_entry, donor2new)
                        if new == val:
                            continue
                        bo = _arg_byte_offset(ins, ai)
                        if bo is None or argsize(ins.op, ai) != 1:
                            continue                  # only same-length 1-byte operands are patchable
                        b[ins.off + bo] = new & 0xFF
                if player_tag_remap and ins.op in eventscan.RUNSCRIPT_OPS:  # site (a): the called PLAYER tag
                    uid, tag = ins.imm(1), ins.imm(2)
                    if (uid == eventscan.UID_PLAYER or eventscan._is_player_entry(uid, donor_player_entry)) \
                            and tag in player_tag_remap:
                        bo = _arg_byte_offset(ins, 2)
                        if bo is not None and argsize(ins.op, 2) == 1:
                            b[ins.off + bo] = player_tag_remap[tag] & 0xFF
        # site (b): a sibling uid read inside an EXPRESSION operand -- the op78 (B_OBJSPECA) token. The
        # immediate REF_OPS loop above skips expr args, so without this a grafted body that reads
        # `op78(<entry>)` (e.g. a MoveInstantXZY positioned off a sibling, or a Seq helper's self/sibling
        # read) keeps the DONOR index after the move -> acts on the wrong/empty fork entry. The uid is a
        # 1-byte token operand (same-length patch). Decoder-walked (NOT a raw 0x78 scan -> no false hits).
        for off in expr_obj_uid_offsets(data, f.abs_start, f.abs_end):
            new = _remap_value("uid", b[off], donor_idx, slot, donor_player_entry, donor2new)
            if new != b[off]:
                b[off] = new & 0xFF
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


# --- party-band-aware NPC insertion (add a NEW kit NPC to a VERBATIM fork) -----------------------
# The engine reserves the LAST `PARTY_BAND_SIZE` entry slots for the 9 playable characters, addressed
# POSITIONALLY (the character with event id `e` is the entry at slot `sSourceObjN-9+e`; EventEngine.cs
# SetupPartyUID + the comment "9 entry slots are reserved at the end of the entry list"). An NPC is, by
# the engine's own definition (`GetNumberNPC`: `sid < sSourceObjN-9`), an object BELOW that band. So a new
# NPC can't just take eb.first_free_slot() (which on a real field is an unused CHARACTER slot inside the
# band -- 818/818 real fields, measured); it must be seated below the band, pushing the 9 characters up one
# slot each. That renumber is transparent to the engine's UID indirection but NOT to the ~790/818 fields
# that reference a band character by RAW slot/uid (Main_Init `InitObject`s each present character by its raw
# slot) -- those are remapped +1 here.
PARTY_BAND_SIZE = 9
_SPECIAL_UIDS = frozenset((eventscan.UID_PLAYER, eventscan.UID_SELF, *eventscan.PARTY_UIDS))


def shift_slot_refs(data, lo: int, hi: int, delta: int) -> bytes:
    """Add ``delta`` to every RAW slot/uid reference whose value is in ``[lo, hi]`` (inclusive), across
    every entry -- the same-length operand patch that keeps references valid when a contiguous block of
    entry SLOTS is renumbered. Reuses the decoder-derived operand surface (:data:`ff9mapkit.eventscan.REF_OPS`
    slot/uid args + the ``op78`` obj-uid expression token), the SAME one :func:`remap_entry_refs` uses for a
    grafted entry -- here over a value RANGE rather than one moved index. Engine specials (250 player / 255
    self / 251-254 party) and a uid-0 slot-alias on ``Init*`` are never touched."""
    eb = EbScript.from_bytes(data)
    b = bytearray(eb.to_bytes())
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                spec = eventscan.REF_OPS.get(ins.op)
                if spec:
                    for kind in ("slot", "uid"):
                        for ai in spec.get(kind, ()):
                            if ai >= len(ins.arg_is_expr) or ins.arg_is_expr[ai]:
                                continue
                            val = ins.imm(ai)
                            if val is None or not lo <= val <= hi:
                                continue
                            if kind == "uid" and (val in _SPECIAL_UIDS
                                                  or (ins.op in eventscan.INIT_OPS and val == 0)):
                                continue
                            if argsize(ins.op, ai) != 1:        # only same-length 1-byte operands are patchable
                                continue
                            bo = _arg_byte_offset(ins, ai)
                            if bo is not None:
                                b[ins.off + bo] = (val + delta) & 0xFF
            for off in expr_obj_uid_offsets(eb.data, f.abs_start, f.abs_end):   # op78 sibling-uid reads
                v = eb.data[off]
                if v not in _SPECIAL_UIDS and lo <= v <= hi:
                    b[off] = (v + delta) & 0xFF
    return bytes(b)


def insert_entry_before_band(data, entry_bytes, *, band_size: int = PARTY_BAND_SIZE):
    """Insert ``entry_bytes`` as a NEW object entry at the slot JUST BELOW the reserved party-character
    band (the last ``band_size`` slots); return ``(new_data, new_slot)``.

    Two steps: (1) ``+1``-remap every reference to a band slot (``[N-band_size, N-1]``) across the whole
    script -- the characters' slot index rises by one when we make room below them; (2) insert the new entry
    at index ``N-band_size`` (:func:`ff9mapkit.eb.edit.insert_entry_at`), shifting the band records up one and
    bumping the entry count. The 9 character BODIES are byte-identical afterward (only their slot index +
    table offset change), and ``new_slot == N-band_size`` is below the now-shifted band, so the engine
    counts it as an NPC (``GetNumberNPC``: ``sid < sSourceObjN-9``). The caller arms it from Main_Init.
    Raises if there is no full band to insert below (entry count <= ``band_size``)."""
    eb = EbScript.from_bytes(data)
    n = eb.entry_count
    band_lo = n - band_size
    if band_lo < 1:
        raise ValueError(f"field has only {n} entries; need > {band_size} to seat an NPC below the party band")
    shifted = shift_slot_refs(data, band_lo, n - 1, 1)
    out = edit.insert_entry_at(shifted, band_lo, entry_bytes)
    return out, band_lo


def seat_entry(data, entry_bytes, *, reserve_party_band: bool = False, slot=None):
    """Place a new entry and return ``(new_bytes, slot)`` -- the shared allocator behind every content
    injector (NPC / region / gateway / event). On the SYNTHESIZE path it appends into a free slot (a blank
    field has spare NPC slots); on a VERBATIM fork (``reserve_party_band``) it INSERTS just below the engine's
    reserved party-character band (:func:`insert_entry_before_band`), so the new entry is a true below-band
    NPC/region and the 9 characters stay the top slots. Sequential calls compose: each insert shifts the band
    up one and remaps band refs, leaving earlier-seated entries (which sit below the band) untouched."""
    if reserve_party_band:
        return insert_entry_before_band(data, entry_bytes)
    eb = EbScript.from_bytes(data)
    if slot is None:
        slot = eb.first_free_slot()
    return edit.append_entry(data, slot, entry_bytes), slot


def graft_objects(data, specs, *, load=None, player_tag_remap=None, out_slot_map=None, out_skipped=None) -> bytes:
    """Graft each spec's VERBATIM object entry into ``data`` and arm it. ``specs`` come from
    :func:`ff9mapkit.eventscan.scan_objects_verbatim` (entry bytes inline) or an import sidecar (a ``bin``
    ref + a ``load(ref) -> bytes`` callable). Objects flagged ``graft_safety == "refuse"`` are skipped
    (the importer leaves those to the authored ``[[npc]]``/``[[prop]]`` path); cutscene WARP-directors (a
    ``Field()`` in the kept LOOP) are ALSO skipped (#13b -- they'd re-warp the fork; ``--verbatim`` keeps them).
    Pass ``out_skipped`` (a list) to collect the dropped directors' ``donor_idx``. Returns the new bytes.

    Two passes, like the ladder ``sequences`` graft: (1) append every entry first so all new slots exist
    (so a sibling cross-reference can resolve); (2) remap each entry's references + arm it from Main_Init.

    ``out_slot_map`` (optional): a dict the caller passes in; on return it holds ``{donor_idx: fork_slot}``
    for every grafted (non-refused) OBJECT. The text-carry path (:mod:`content.textcarry`) needs it to find
    each grafted entry and remap its window TXIDs; existing callers omit it and are unaffected.

    ``seqs`` on a spec (docs/OBJECT_CARRY.md S2 v1.5): the BENIGN ``STARTSEQ`` helper entries the object
    launches from a kept tag (``{entry, bytes}`` or ``{entry, bin}``). Each is appended at a free slot
    FIELD-SCOPED-DEDUPED (a shared helper once, not once per consumer) and its launcher arg is remapped via
    ``donor2new`` like the ladder ``sequences`` graft -- but a helper is a runtime-launched Seq, so it is
    appended-and-remapped, NEVER ``InitObject``'d.
    """
    specs = [s for s in specs if s.get("graft_safety") != "refuse"]
    # #13b: a SYNTHESIZED fork must NOT carry cutscene WARP-directors -- an object whose KEPT loop (tag 1) fires
    # Field() re-warps / rotates the cast at the asserted beat (the stacked-spawn / warp-out bug seen forking the
    # Dali shop). Drop them here (`--verbatim` keeps them whole; the author can re-add a static [[npc]]). Checked
    # on the carry_tags-filtered bytes so an init_only object that already drops its loop is left rendering.
    kept = []
    for s in specs:
        raw = s.get("entry_bytes")
        if raw is None and load is not None and s.get("bin") is not None:
            raw = load(s["bin"])
        if raw is not None and _loop_warps(carry_bytes(raw, s.get("carry_tags"))):
            if out_skipped is not None:
                out_skipped.append(int(s.get("donor_idx", -1)))
            continue
        kept.append(s)
    specs = kept
    if not specs:
        return data

    def _pents(s):                                    # primary PC int OR the full PC-entry list (multi-PC)
        return s.get("donor_player_entries") or s.get("donor_player_entry")

    donor2new, appended, helpers = {}, [], []
    for s in specs:                                   # PASS 1 -- reserve every slot (objects + their helpers)
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
        for h in (s.get("seqs") or []):               # the STARTSEQ helpers this object carries
            hi = int(h["entry"])
            if hi in donor2new:                       # field-scoped dedup -- a shared helper is appended once
                continue
            hraw = h.get("bytes")
            if hraw is None:
                if load is None:
                    raise ValueError(f"seq helper {hi} has no bytes and no loader")
                hraw = load(h["bin"])
            hslot = EbScript.from_bytes(data).first_free_slot()
            data = edit.append_entry(data, hslot, hraw)
            donor2new[hi] = hslot
            helpers.append((hi, hslot, _pents(s)))
    for s, slot in appended:                          # PASS 2 -- remap references + arm from Main_Init
        data = remap_entry_refs(data, slot, int(s["donor_idx"]), _pents(s), donor2new, player_tag_remap)
        for inst in (s.get("instances") or [{"arg": 0}]):
            data = _arm(data, slot, int(inst.get("arg", 0)), s.get("needs_d9") or {})
    for hi, hslot, pents in helpers:                  # helpers: remap their own refs, but NEVER arm (Seq-launched)
        data = remap_entry_refs(data, hslot, hi, pents, donor2new, player_tag_remap)
    if out_slot_map is not None:
        out_slot_map.update({int(s["donor_idx"]): slot for s, slot in appended})
    return data
