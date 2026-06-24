"""Inject a field-exit gateway (a region trigger that warps to another field).

Clones the proven field-109 exit-region template (a SetRegion polygon ->
CalculateExitPosition/ExitField -> PreloadField -> FadeFilter -> set FieldEntrance ->
Field(target)), patches its trigger polygon + target field + arrival entrance, appends it
into a free entry slot, and activates it by overwriting a Main_Init ``Wait(2)`` filler with
``InitRegion`` (shift-free).

Zone gotchas (baked into :func:`quad_zone`): the engine's IsInQuad tests a *fan* of
consecutive vertex triplets, so three collinear points make a dead zone — use a convex quad
with the **last vertex doubled** (5 points). Point order matters: q0->q1 is the edge the
player walks out across, so put the front edge first for a natural forward exit.
"""

from __future__ import annotations

import struct

from .. import data
from ..eb import EbScript, edit, opcodes
from . import region as _region

# offsets within the 272-byte region template
REL_PTS, REL_ENTRANCE, REL_FIELD = 13, 263, 269


def quad_zone(corners) -> list:
    """Make a 5-point IsInQuad-safe zone from 4 (x, z) corners (doubles the last vertex)."""
    pts = [tuple(c) for c in corners]
    if len(pts) != 4:
        raise ValueError("quad_zone needs 4 corners")
    return pts + [pts[-1]]


def inject_gateway(eb_bytes, target: int, *, entrance: int = 0, zone, slot: int | None = None,
                   spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0,
                   gate_flag: int | None = None, gate_require_set: bool = True,
                   on_exit_body: bytes = b"", reserve_party_band: bool = False) -> bytes:
    """Inject an exit gateway to ``Field(target)`` arriving at ``entrance``. Returns new bytes.

    ``gate_flag`` (a GlobBool index) locks the exit behind a story flag: the region's trigger returns
    early unless the flag is in the required state (``gate_require_set`` True = open when SET, e.g. a
    door that unlocks once a switch flag is set; False = open when CLEAR).

    ``on_exit_body`` (raw ``set_var`` bytes -- e.g. from :func:`ff9mapkit.content.startup.startup_body`)
    ADVANCES story state when the player TAKES this exit: it is prepended to the Range trigger behind a
    ``usercontrol`` guard, so the writes fire only on an actual walk-out (not while the player is puppeted
    through with control disabled) and -- when the exit is also ``gate_flag``-locked -- only when the gate
    passes (the flag gate sits ahead of the writes). The byte sequence runs just before the template's own
    warp path, so the ScenarioCounter / story bits commit to the save-backed gEventGlobal before the
    transition. Empty -> no change (the gateway builds byte-identically to before)."""
    zone = list(zone)
    if len(zone) != 5:
        raise ValueError("zone must be 5 points (convex quad + doubled last vertex); see quad_zone()")
    tpl = bytearray(data.region_template())
    for i, (x, z) in enumerate(zone):
        struct.pack_into("<hh", tpl, REL_PTS + i * 4, int(x), int(z))
    struct.pack_into("<H", tpl, REL_ENTRANCE, entrance)
    struct.pack_into("<H", tpl, REL_FIELD, target)

    from . import object as _object             # local: object imports region -> avoid the top-level cycle
    out, slot = _object.seat_entry(eb_bytes, bytes(tpl), reserve_party_band=reserve_party_band, slot=slot)
    out = edit.activate(out, opcodes.init_region(slot, 0), spawn_wait_n=spawn_wait_n,
                        spawn_wait_occurrence=spawn_wait_occurrence)
    # Order matters: prepend the on-exit writes first, then the flag gate, so the final Range reads
    # [flag gate] -> [usercontrol guard + writes] -> [template warp]. (Each prepend goes to Range's start.)
    if on_exit_body:
        out = _region.prepend_range_gate(out, slot, _region.MOVEMENT_GATE + on_exit_body)
    if gate_flag is not None:
        out = _region.prepend_range_gate(out, slot, _region.flag_gate(
            _region.GLOB_BOOL, gate_flag, require_set=gate_require_set))
    return out


def graft_gateway_entry(eb_bytes, entry_bytes, *, retarget=None, slot=None):
    """Graft a story-gated door's region entry VERBATIM (preserving its whole conditional state machine), then
    arm it -- the faithful counterpart to :func:`inject_gateway`'s re-synthesis. A real story-gated door
    (``eventscan.scan_gateway_entries`` ``story_gated``) checks GLOB save flags in a complex conditional the
    declarative rebuild can't reproduce; carrying the entry whole keeps that logic, and its GLOB conditions
    then read the ``[startup]``-preset story state (docs/FORK_FIDELITY.md #2b). Mirrors the object carry.

    ``retarget`` maps a real destination field id -> a new id; each ``Field(id)`` literal whose id is in the
    map is patched in place (ids NOT in the map are left as live seams, like the import's live-seam doors).
    ``slot`` defaults to the first free entry. Returns ``(new_bytes, slot)``.

    LIMIT: a door-only carry does NOT reconstruct MAP/transient vars the field's *main* logic sets on entry,
    so a door whose firing also depends on those may still mis-evaluate (documented; ~30% of gated entries
    also reference other entries and aren't carried by this path at all)."""
    eb = EbScript.from_bytes(eb_bytes)
    if slot is None:
        slot = eb.first_free_slot()
    out = edit.append_entry(eb_bytes, slot, bytes(entry_bytes))
    if retarget:
        ge = EbScript.from_bytes(out)
        buf = bytearray(out)
        for f in ge.entry(slot).funcs:
            for i in ge.instrs(f):
                if i.op == 0x2B and i.imm(0) in retarget:          # Field(id) -> retarget[id] (2-byte literal @ +2)
                    struct.pack_into("<H", buf, i.off + 2, int(retarget[i.imm(0)]) & 0xFFFF)
        out = bytes(buf)
    return edit.activate(out, opcodes.init_region(slot, 0)), slot
