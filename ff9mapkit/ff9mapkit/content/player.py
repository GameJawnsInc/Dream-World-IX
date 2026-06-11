"""Player-function graft -- carry the donor field's player functions onto the fork player.

The next step after object carry (:mod:`content.object`): when a carried object's interactive function
``RunScript``s a PLAYER tag >= 2 (e.g. the field-122 cask's tag-2 does ``RunScript(player, 24)`` -> the
player turns toward the cask), that tag doesn't exist on the blank fork player (tags ``[0, 1]`` only), so
the object graft drops it to ``init_only``. This module grafts those donor player functions onto the fork
player at a fresh tag band, the object's ``RunScript`` tag is remapped to the new tag (in
:func:`content.object.remap_entry_refs`), and -- the load-bearing catch -- the donor Init's animation-pack
loads are spliced so the grafted gestures' clips are actually loaded.

It GENERALIZES the one-function jump/ladder graft (:func:`content.jump.inject_jump` /
:func:`content.ladder.inject_ladder` each add ONE player function via :func:`eb.edit.add_function`) to N
functions, with:

  * :class:`PlayerTagAllocator` -- a single next-free allocator across the ladder (17+), jump (40+) and
    object (64+) bands, so the bands never collide regardless of count.
  * :func:`remap_player_tag_calls` -- the intra-graft player->player tag remap (depth-0 in practice).
  * :func:`ensure_player_anim_packs` -- the donor Init's ``RunModelCode`` pack-loads spliced into the fork
    player Init.

Specs come from :func:`ff9mapkit.eventscan.scan_player_funcs` (only ``safety == "clean"`` funcs are
grafted; the rest leave their seeding object ``init_only``). Full recipe: ``docs/PLAYER_GRAFT.md``.
"""
from __future__ import annotations

from .. import eventscan
from ..eb import EbScript, edit, opcodes
from ..eb.disasm import iter_code
from .jump import FIRST_JUMP_TAG
from .ladder import FIRST_CLIMB_TAG, find_player_entry
from .object import _arg_byte_offset

FIRST_OBJECT_PLAYER_TAG = 64   # the object-referenced player-func band (clear of ladder 17+, jump 40+)
DEFINE_PC_OP = 0x2C            # DefinePlayerCharacter -- the splice point for the anim-pack prologue


class PlayerTagAllocator:
    """Hands out fresh fork-player function tags, never colliding across the three graft bands
    (ladder 17+ / jump 40+ / object 64+). Built from the fork player's existing tags (``{0, 1}`` on a
    blank fork); :meth:`take` starts at the band floor and slides past any prior band's overflow, so a
    field with > 24 jumps (which would push the jump band into 64) can't alias the object band. For every
    in-budget field this returns exactly the fixed-counter tags the jump/ladder grafts use today (so their
    in-game proofs + the hut golden are preserved); it only changes the previously-broken overflow case."""

    FLOORS = {"ladder": FIRST_CLIMB_TAG, "jump": FIRST_JUMP_TAG, "object": FIRST_OBJECT_PLAYER_TAG}

    def __init__(self, data):
        eb = data if isinstance(data, EbScript) else EbScript.from_bytes(data)
        self._used = {f.tag for f in eb.entry(find_player_entry(eb)).funcs}

    def take(self, kind, n=1):
        """``n`` fresh tags in ``kind``'s band ('ladder'|'jump'|'object'), none colliding with prior takes."""
        t, out = self.FLOORS[kind], []
        for _ in range(int(n)):
            while t in self._used:
                t += 1
            self._used.add(t)
            out.append(t)
            t += 1
        return out


def remap_player_tag_calls(body, tagmap) -> bytes:
    """Site (b): within a grafted player function body, remap an intra-graft player->player ``RunScript``'s
    tag arg (arg2) to its fork tag. Depth-0 in practice (the census found no object-path player func calls
    another player tag), so this is a defensive same-length pass; function-relative jumps survive untouched."""
    if not tagmap:
        return bytes(body)
    b = bytearray(body)
    for ins in iter_code(bytes(b), 0, len(b)):
        if ins.op in eventscan.RUNSCRIPT_OPS:
            uid, tag = ins.imm(1), ins.imm(2)
            if uid in (eventscan.UID_PLAYER, eventscan.UID_SELF) and tag in tagmap:
                bo = _arg_byte_offset(ins, 2)
                if bo is not None:
                    b[ins.off + bo] = tagmap[tag] & 0xFF
    return bytes(b)


def ensure_player_anim_packs(data, packs) -> bytes:
    """Splice the donor player Init's ``RunModelCode`` anim-pack loads into the fork player Init (after
    ``DefinePlayerCharacter``), so a grafted gesture's clip is actually loaded -- the fork player otherwise
    loads only the blank-field default pack, leaving a clip from another pack SILENTLY unloaded
    (docs/PLAYER_GRAFT.md S4). ``packs`` are decoded ``RunModelCode`` arg tuples (from
    :func:`ff9mapkit.eventscan.scan_player_funcs`), re-encoded byte-exact. De-duped + idempotent (skips
    packs the fork Init already loads). Generalizes :func:`content.jump.ensure_jump_animation`."""
    if not packs:
        return data
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    init = eb.entry(pe).func_by_tag(0)
    if init is None:
        return data
    have = {tuple(ins.args) for ins in eb.instrs(init)
            if ins.op == eventscan.RUN_MODEL_CODE_OP and not any(ins.arg_is_expr)}
    block = b"".join(opcodes.encode(eventscan.RUN_MODEL_CODE_OP, *p)
                     for p in packs if tuple(p) not in have)
    if not block:
        return data
    dpc = next((i for i in eb.instrs(init) if i.op == DEFINE_PC_OP), None)
    rel = (dpc.end - init.abs_start) if dpc is not None else 0
    return edit.insert_in_function(data, pe, 0, rel, block)


def graft_player_funcs(data, specs, tagmap, *, load=None) -> bytes:
    """Graft each CLEAN player function (``safety == "clean"``) verbatim onto the fork player at its fork
    tag (``tagmap[donor_tag]``) via :func:`eb.edit.add_function` -- the N-function generalization of the
    one-func jump/ladder graft. Splices the donor Init's anim packs first (so the gestures' clips load).
    Refused (non-clean) funcs are skipped (their seeding object stays ``init_only``). ``specs`` come from
    :func:`ff9mapkit.eventscan.scan_player_funcs`; bodies are inline (``body``) or loaded via
    ``load(spec["bin"])``. Returns the new ``.eb`` bytes (unchanged when nothing is graftable)."""
    clean = [s for s in specs if s.get("safety") == "clean" and int(s["donor_tag"]) in tagmap]
    if not clean:
        return data
    packs = []
    for s in clean:
        for p in s.get("donor_init_packs") or []:
            if tuple(p) not in packs:
                packs.append(tuple(p))
    data = ensure_player_anim_packs(data, packs)
    pe = find_player_entry(EbScript.from_bytes(data))
    for s in clean:
        body = s.get("body")
        if body is None:
            if load is None:
                raise ValueError(f"player_func spec (tag {s.get('donor_tag')}) has no body and no loader")
            body = load(s["bin"])
        body = remap_player_tag_calls(bytes(body), tagmap)
        data = edit.add_function(data, pe, tagmap[int(s["donor_tag"])], body)
    return data
