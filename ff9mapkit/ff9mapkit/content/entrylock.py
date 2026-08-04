"""``[player] locked_entrances`` -- arrive with control WITHHELD at named entrances.

Stock's race-free arrive-locked mechanism (the movement census, ``studies/movement/SURVEY.md``):
the engine zeroes ``usercontrol`` on EVERY field load and only ever mirrors it -- the script's own
grant is the sole way control comes back, and stock gates that grant on ``General_FieldEntrance``
(64 sites, e.g. Dali/Windmill 358: ``if (FieldEntrance != 21 && != 22) { DefinePlayerCharacter;
grant }``) so a chained cutscene arrives still locked. No reorder-wait, no spin, no watchdog --
the grant simply never fires for that entrance.

The synthesized template has TWO grant sites, both carrying the stock five-flag macro verbatim:

* the PLAYER-INIT latch arm -- ``set MAP158 = 1`` + the 159-conditional enable macro (inert on a
  fresh save where MAP159 is 0, but LIVE mid-session once Main_Init has set 159);
* the MAIN_INIT tail re-affirm -- ``if (MAP158 == 1) { the enable macro }``, which fires because
  the player init armed the latch. **This is the grant that actually lands on a fresh save.**

Both must be entrance-gated, or a warp path that leaves MAP158 armed re-grants on arrival. The
gate is a chain of ``if (FieldEntrance == e) skip-the-grant`` jumps inserted immediately before
each site -- located by byte pattern (the macro is byte-invariant in the template), inserted via
the fpos-fixing :func:`ff9mapkit.eb.edit.insert_in_function`.

The unlock is then some later beat's job -- an ``[[on_entry]]`` hook with ``grant_control`` (the
build wires this automatically), a cutscene's ``EnableMove``, etc. Synthesized fields only: a
donor's grant sites are its own conditional forest, not this template shape.
"""
from __future__ import annotations

import struct

from ..eb import EbScript, edit
from . import region as _region
from .ladder import find_player_entry

# The template's stock-macro anchors (MAP bits 144/156/158/159 are the engine-idiom control
# latches the blank template carries verbatim; 158 = "control should be ON").
_SET_LATCH = bytes([_region.EXPR_OP, _region.MAP_BOOL, 158, 0x7D, 1, 0, 0x2C, _region.T_END])
_TEST_LATCH = bytes([_region.EXPR_OP, _region.MAP_BOOL, 158, 0x7D, 1, 0, 0x20, _region.T_END])
RETURN_OP = 0x04


def _entrance_gate(entrances, block_len: int) -> bytes:
    """``if (FieldEntrance == e) skip`` per locked entrance, each jumping past the remaining
    conditions AND the ``block_len`` bytes of the grant block that follows the chain."""
    conds = [_region.cond_eq(_region.GLOB_INT16, _region.FIELD_ENTRANCE_IDX, int(e))
             for e in entrances]
    hop = 3                                        # JMP_TRUE + i16 operand
    out = b""
    for i, cond in enumerate(conds):
        rest = sum(len(c) + hop for c in conds[i + 1:])
        out += cond + bytes([_region.JMP_TRUE]) + struct.pack("<h", rest + block_len)
    return out


def gate_grant_on_entrances(data, entrances) -> bytes:
    """Entrance-gate BOTH template grant sites. Returns new ``.eb`` bytes; raises if either site's
    stock-macro anchor is missing (a non-template player/Main_Init -- e.g. a verbatim donor)."""
    entrances = [int(e) for e in entrances]
    if not entrances:
        return data if isinstance(data, (bytes, bytearray)) else data.to_bytes()
    out = data if isinstance(data, (bytes, bytearray)) else bytes(data)

    # Site A -- the player-init latch arm: wrap from `set MAP158 = 1` to the terminal RETURN.
    eb = EbScript.from_bytes(out)
    pe = find_player_entry(eb)
    init = eb.entry(pe).func_by_tag(0)
    body = out[init.abs_start:init.abs_end]
    a = body.find(_SET_LATCH)
    if a < 0:
        raise ValueError("[player] locked_entrances: the player Init has no `set MAP158 = 1` latch "
                         "arm -- not the synthesized template (locked_entrances is synth-only)")
    ret = next((ins.off - init.abs_start for ins in eb.instrs(init)
                if ins.op == RETURN_OP and ins.off - init.abs_start >= a), None)
    if ret is None:
        raise ValueError("[player] locked_entrances: no RETURN after the player-init grant block")
    out = edit.insert_in_function(out, pe, 0, a, _entrance_gate(entrances, ret - a))

    # Site B -- the Main_Init tail re-affirm: wrap the `if (MAP158 == 1) {...}` block (its extent
    # is the JMP_FALSE's own target -- parse the jump that follows the test).
    eb = EbScript.from_bytes(out)
    main = eb.entry(0).func_by_tag(0)
    body = out[main.abs_start:main.abs_end]
    b = body.find(_TEST_LATCH)
    if b < 0 or body[b + len(_TEST_LATCH)] != _region.JMP_FALSE:
        raise ValueError("[player] locked_entrances: Main_Init has no `if (MAP158 == 1)` re-affirm "
                         "-- not the synthesized template (locked_entrances is synth-only)")
    jo = b + len(_TEST_LATCH)
    skip = struct.unpack_from("<h", body, jo + 1)[0]
    block_end = jo + 3 + skip                       # the JMP_FALSE target = end of the taken branch
    out = edit.insert_in_function(out, 0, 0, b, _entrance_gate(entrances, block_end - b))
    return out
