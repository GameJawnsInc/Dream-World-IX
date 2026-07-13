"""``[[coop]]`` two-plate gates -- field content designed for TWO players (netsync V2, engine s37).

The engine side (``NetSyncClient.WriteCoopCells``) broadcasts the PEER's presence + walkmesh
position into kit-reserved ``gEventGlobal`` cells every frame while ``[Netsync] Enabled = 1``;
this module compiles the declarative ``[[coop]]`` block into ordinary region entries whose
per-frame Range bodies read those cells as plain GLOB vars. Engine = mechanism, ``.eb`` = policy
(the split that won the vehicle system): the engine knows nothing about plates, and the built
field carries no hard engine dependency -- on a stock engine the presence byte is never 1, so a
gate simply never fires (fail-safe vanilla).

THE COOP CELLS (byte offsets into ``gEventGlobal``; must mirror ``NetSyncClient.CoopCellBase``):

    2032        presence  (GLOB byte)   1 = the peer's player stands on MY current field
    2034-2035   peer X    (GLOB Int16)  walkmesh units, little-endian, sign-extended
    2036-2037   peer Z    (GLOB Int16)  the same coordinate space SetRegion quads use
    2033, 2038-2039        reserved

They sit at the TOP of the kit's custom flag band, beside the choice-mask scratch at byte 2040,
and are registered as a reserved :data:`ff9mapkit.flags.BIT_REGIONS` entry so the flag lint keeps
authored flags out. Addressing verified against ``EBin.GetVariableValueInternal`` (byte-offset LE
reads) -- the same encoding :func:`ff9mapkit.content.region._push_var` emits, incl. the
long-index bit for offsets > 0xFF.

THE GATE (rung 1): two axis-aligned plates; the gate fires ONCE when the players stand on both
simultaneously, in either arrangement. Each plate becomes a region (the proven camera-switch
shape -- Range tag-2 runs every frame while standing inside) whose body is::

    if (!flag) {                      # the once-latch -- OUTSIDE the peer check on purpose:
        if (peer in the OTHER plate)  # standing on a plate alone must NOT latch
            { flag = 1; message? }    # flag FIRST (FF9's chest convention): loop-safe
    }

Each machine computes its gate locally and sets its OWN save's flag -- zero state sync, zero
story-divergence problem (both sides run the same authored field). The minted flag then gates
doors / gateways / cutscenes / NPCs through the EXISTING vocabulary; ``[[coop]]`` only mints it.

SOLO-PROVABLE: ``Role = selftest`` mirrors the player at exactly +250 x and the engine writes the
mirror's position into the cells -- plates spaced :data:`SELFTEST_MIRROR_DX` apart center-to-center
fire the gate with one player standing on plate A.
"""

from __future__ import annotations

import struct

from ..eb import opcodes
from . import event as _event
from . import region as _region

#: byte offsets of the engine-written cells (mirror NetSyncClient.CoopCellBase et seq.)
COOP_PRESENCE_BYTE = 2032
COOP_PEER_X = 2034
COOP_PEER_Z = 2036
#: the Role=selftest mirror stands at exactly +x this many walkmesh units from the player
SELFTEST_MIRROR_DX = 250


def normalize_rect(rect, who: str = "[[coop]] plate"):
    """Validate + normalize a ``[x1, z1, x2, z2]`` plate rect: 4 numbers, Int16 range, corners
    sorted so x1 < x2 and z1 < z2. Raises ValueError with an author-usable message."""
    try:
        vals = [int(v) for v in rect]
    except (TypeError, ValueError):
        raise ValueError(f"{who} must be [x1, z1, x2, z2] (numbers), got {rect!r}")
    if len(vals) != 4:
        raise ValueError(f"{who} must be [x1, z1, x2, z2] (4 numbers), got {len(vals)}")
    x1, z1, x2, z2 = vals
    if x1 > x2:
        x1, x2 = x2, x1
    if z1 > z2:
        z1, z2 = z2, z1
    if x1 == x2 or z1 == z2:
        raise ValueError(f"{who} has zero width or depth ({vals!r}) -- a plate needs area")
    for v in (x1, z1, x2, z2):
        if not -32768 <= v <= 32767:
            raise ValueError(f"{who} coordinate {v} is outside the walkmesh Int16 range")
    return x1, z1, x2, z2


def rect_zone(rect) -> list:
    """The SetRegion corner list for a plate rect -- perimeter order (no bowtie quad)."""
    x1, z1, x2, z2 = normalize_rect(rect)
    return [(x1, z1), (x2, z1), (x2, z2), (x1, z2)]


def cond_peer_in_rect(rect) -> bytes:
    """``if (presence == 1 && peerX >= x1 && peerX <= x2 && peerZ >= z1 && peerZ <= z2)`` as ONE
    compound RPN expression (chained ``&&``), reading the engine-written coop cells as ordinary
    GLOB vars: the presence byte via GLOB_BYTE (single byte -- never clobbers a neighbour) and the
    coordinates via GLOB_INT16 (byte-addressed LE, sign-extended -- EBin's exact read)."""
    x1, z1, x2, z2 = normalize_rect(rect)
    t = (_region._push_var(_region.GLOB_BYTE, COOP_PRESENCE_BYTE)
         + bytes([_region.T_CONST]) + struct.pack("<h", 1) + bytes([_region.T_EQ]))
    for var_idx, lo, hi in ((COOP_PEER_X, x1, x2), (COOP_PEER_Z, z1, z2)):
        t += (_region._push_var(_region.GLOB_INT16, var_idx)
              + bytes([_region.T_CONST]) + struct.pack("<h", lo)
              + bytes([_region.T_GE, _region.T_ANDAND]))
        t += (_region._push_var(_region.GLOB_INT16, var_idx)
              + bytes([_region.T_CONST]) + struct.pack("<h", hi)
              + bytes([_region.T_LE, _region.T_ANDAND]))
    return bytes([_region.EXPR_OP]) + t + bytes([_region.T_END])


def gate_range_body(other_rect, flag: int, message_txid: int | None = None) -> bytes:
    """One plate's Range body: movement gate, then the once-latch wrapping the peer condition
    (see the module doc for why the nesting is this way round). The flag is set BEFORE the
    message (FF9's treasure-chest convention) so the gate can't double-fire while the window
    is open."""
    fire = _region.set_var(_region.GLOB_BOOL, int(flag), 1)
    if message_txid is not None:
        fire += _event.message(int(message_txid))
    body = _region.if_block(_region.cond_not(_region.GLOB_BOOL, int(flag)),
                            _region.if_block(cond_peer_in_rect(other_rect), fire))
    return _region.MOVEMENT_GATE + body + opcodes.RETURN


def inject_gate(data, plate_a, plate_b, flag: int, message_txid: int | None = None):
    """Inject ONE two-plate gate: a region per plate, each body checking the peer against the
    OTHER plate -- symmetric, so it fires no matter which player takes which plate. Returns the
    new ``.eb`` bytes. (Synthesize-path shape: per-region activation like the zone-choices.)"""
    out = data if isinstance(data, (bytes, bytearray)) else data.to_bytes()
    out, _slot = _region.inject_region(out, rect_zone(plate_a),
                                       gate_range_body(plate_b, flag, message_txid))
    out, _slot = _region.inject_region(out, rect_zone(plate_b),
                                       gate_range_body(plate_a, flag, message_txid))
    return out
