"""The WORLDMAP exit for a synthesized field -- ``[[gateway]] to = "worldmap"``.

A field returns to the world map via ``WorldMap`` (opcode 0xB6) whose operand IS the
``wldMapNo`` (9000-9012). No real field hardcodes one target: all 79 world-exit fields
carry a **byte-identical EXIT CASCADE** (verified identical in field 300 Ice Cavern
e2/tag2 and field 2800 Daguerreo e21/tag2 -- OVERWORLD_ENGINE.md "the shared exit
cascade") that emits all 13 targets and selects by ``(ScenarioCounter band) x (region
key D8:2)``. The kit CARRIES that cascade verbatim -- extracted at build time from the
user's install (provenance-clean, like cameras; never committed) as the
instruction-aligned common suffix of the two verified carriers, self-checked to parse
cleanly and hold every WorldMap arm.

The field writes its own region key first (the same ``D8:2`` transition parameter a
``Field()`` warp uses as its arrival entrance -- ``region.set_field_entrance``).

THE ARRIVAL MODEL (fully decoded across 4 playtest rounds -- the cascade's switch
tables + arms + WORLD09 e5/tag0, the world player's Init; ``0x0E`` = T_NOT, so the
Init's test is ``if (!D8:2)``):

* The world player is ALWAYS placed by ``MoveInstantXZY`` from the persisted
  position vars. **There are TWO such blocks, one per player OBJECT** (R2a byte
  census over all 9 free-roam dispatchers): the ON-FOOT avatar (model 310, model
  309 in WORLD02 -- the object that takes control when ``D4:190 == 0``) reads
  ``C8:0x40``/``D8:0x43``/``C8:0x45``/``D4:0x48``; the VEHICLE-COMPOSITE object
  (model 308, ``DefinePlayerCharacter`` only inside its ``1 <= D4:190 <= 6``
  riding guard) reads ``C8:0x53``/``D8:0x56``/``C8:0x58``/``D4:0x5B``. Each
  object's own tag-1 main loop mirrors its block from itself EVERY FRAME -- that
  loop, not the engine, is the "position mirror". (The on-foot block is the same
  one the SAVE carries: :data:`ff9mapkit.save.WORLD_POS_X_OFF` = 64.) The kit
  writes BOTH blocks, so the preset holds whichever object is the player; the
  block that is not the player is inert.
* **arriving with ``D8:2 == 0``**: the Init FIRST overwrites those vars with the
  world's own DEFAULT point (each world has one; WORLD09's is the Mist-Continent
  door) -- "no arrival info -> the fallback door".
* **arriving with ``D8:2 != 0``**: the vars are left alone -- for real doors that
  is the mirror's record of where the player stood when they entered the
  field (how real towns return you to their door), and for the kit's ``arrive=``
  exit it is the coordinates the exit just wrote.
* In the CASCADE, key 62's arm runs ``D8:2 = 0; WorldMap(9009)`` (so the plain
  cascade always lands at 9009's default point -- 62 is the ONLY key that zeroes
  the arrival var, which is why it is the plain-return key and NOT the
  position-preset key), and **key 0 / any un-cased key hits the switch default --
  a bare RETURN: the door does NOTHING** (playtest-proven; the validator refuses 0).

THE DETERMINISTIC RETURN (``arrive = [x, z]``): the entrance trigger records the
CURRENT ``wldMapNo`` into the kit-reserved GLOB word :data:`WORLD_STATE_VAR`
(each dispatcher copy carries its own literal), and the exit then [writes the
arrive coords into the position vars] [sets ``D8:2`` NONZERO so nothing
overwrites them] [``WorldMap(<recorded state>)`` via the computed argFlag lane
-- the same mechanism as ``region.field_to_var``]. The player returns to the
SAME world state they left, at exactly the arrive point. If the state var is
empty (an debug-menu warp straight into the field), the exit falls back to the generic
cascade.
"""

from __future__ import annotations

from ..eb.model import EbScript

#: the two byte-verified cascade carriers: (field id, entry index, func tag)
CASCADE_DONORS = ((300, 2, 2), (2800, 21, 2))
#: the default region key: 62 = the generic cascade arm (D8:2=0 + WorldMap(9009) in
#: every SC band -> 9009's DEFAULT-point arrival). 0/un-cased keys DO NOT WARP
#: (the switch default is a bare return -- the arrival model above).
REGION_KEY_RETURN = 62
REGION_KEY_OPEN_SEA = 62  # back-compat alias
#: the nonzero D8:2 value the arrive= exit lands with ("position preset"): the
#: destination Init then leaves the position vars alone. It must be a key whose
#: CASCADE arm does NOT re-zero D8:2, because the fall-through (no recorded world
#: state) still runs the cascade -- 62 is the one key that does, in all four SC
#: bands. 35 is a real disc-1 key (13 shipping fields write the idiom
#: ``05 D8 02 7D 23 00 2C 7F``: ids 262, 350, 404, 450, 601, 617, 1367, 1419,
#: 1605, 1661, 1663, 2170, 2356) whose arms are BARE WorldMaps -- band1 9011,
#: band2 9003, band3 9007, band4 9008 -- so the preset survives AND the world
#: state re-derives from the CURRENT scenario band (disc-correct for free).
POSITION_PRESET_KEY = 35
#: kit-reserved gEventGlobal WORD (bytes 1062-1063, the outpost var's sibling at
#: 1060-1061): the entrance trigger records the CURRENT wldMapNo here; the
#: arrive= exit returns to it (computed WorldMap)
WORLD_STATE_VAR = 1062
#: the minimum WorldMap arms a healthy cascade carries (13 states; real carriers emit 19 ops)
_MIN_WORLDMAP_OPS = 13

_cache: dict = {}


def _handler(eb_bytes: bytes, entry_i: int, tag: int) -> bytes:
    s = EbScript.from_bytes(eb_bytes)
    f = s.entry(entry_i).func_by_tag(tag)
    if f is None:
        raise ValueError(f"cascade donor has no entry{entry_i}/tag{tag} handler")
    return s.data[f.abs_start:f.abs_end]


def _instr_offsets(body: bytes) -> list:
    from ..eb.disasm import read_code
    offs, pos = [], 0
    while pos < len(body):
        offs.append(pos)
        _, pos = read_code(body, pos)
    offs.append(len(body))
    return offs


def cascade_bytes(game=None) -> bytes:
    """The shared exit cascade, verbatim real bytes: the instruction-aligned longest
    common suffix of the two verified carriers. Self-verifying -- the suffix must
    start on an instruction boundary of BOTH donors, parse cleanly to the end, and
    carry >= 13 ``WorldMap`` arms; anything less raises (a game-data drift guard)."""
    key = ("cascade", id(game) if game is not None else None)
    if key in _cache:
        return _cache[key]
    from ..extract import EventBundle
    bundle = EventBundle(game)
    bodies = []
    for fid, ei, tag in CASCADE_DONORS:
        eb = bundle.eb_for_id(fid)
        if eb is None:
            raise ValueError(f"cascade donor field {fid} has no event script in the install")
        bodies.append(_handler(eb, ei, tag))
    a, b = bodies
    # the cascade = the donors' longest common block (their heads differ -- each
    # field writes its OWN region keys; their tails differ only by 0x00 padding)
    import difflib
    m = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(
        0, len(a), 0, len(b))
    if m.size < 512:
        raise ValueError(f"the cascade donors share only a {m.size}-byte block -- not "
                         f"the shared exit cascade the engine study verified")
    pad_a = len(a) - (m.a + m.size)
    pad_b = len(b) - (m.b + m.size)
    if pad_a > 2 or pad_b > 2 or any(c != 0 for c in a[m.a + m.size:]) \
            or any(c != 0 for c in b[m.b + m.size:]):
        raise ValueError("the common block does not reach the donors' handler ends "
                         "(beyond 0x00 padding) -- not the terminal exit cascade")
    # snap the block start FORWARD to the first instruction boundary shared by both
    # donors' streams (a byte-level match can extend backward into coincidentally
    # equal operand bytes mid-instruction)
    offs_a, offs_b = set(_instr_offsets(a)), set(_instr_offsets(b))
    k = next((k for k in range(0, 129)
              if (m.a + k) in offs_a and (m.b + k) in offs_b), None)
    if k is None:
        raise ValueError("no shared instruction-aligned cascade start within the common block")
    out = a[m.a + k:m.a + m.size]
    # the health check: parses cleanly + carries every WorldMap arm
    from ..eb.disasm import read_code
    pos, wm = 0, 0
    while pos < len(out):
        ins, pos = read_code(out, pos)
        if ins.op == 0xB6:
            wm += 1
    if wm < _MIN_WORLDMAP_OPS:
        raise ValueError(f"the extracted cascade carries only {wm} WorldMap arms "
                         f"(expected >= {_MIN_WORLDMAP_OPS}) -- not the shared exit cascade")
    _cache[key] = out
    return out


#: the world player's persisted-position vars, as ``(x, y, z, face)`` var pairs:
#: x/z are int32 fixed-point (world * 256, the 0x7E 32-bit const token), y an
#: int16, facing a byte var. Writing them before the exit makes the arrival
#: DETERMINISTIC -- the world places the player at these coords instead of
#: wherever that object's own main-loop mirror last ticked.
#:
#: ON FOOT (``D4:190 == 0``) -- the object that actually takes control in all 9
#: free-roam dispatchers (model 310; 309 in WORLD02). Byte-decoded from WORLD11
#: e14 tag0/tag1 and cross-checked against every other dispatcher.
_POS_ONFOOT = ((0xC8, 0x40), (0xD8, 0x43), (0xC8, 0x45), (0xD4, 0x48))
#: RIDING (``1 <= D4:190 <= 6``) -- the model-308 vehicle-composite player object
#: (WORLD09 e5/tag0). Inert while on foot.
_POS_VEHICLE = ((0xC8, 0x53), (0xD8, 0x56), (0xC8, 0x58), (0xD4, 0x5B))
#: both are written: only one of the two objects is the player on any given exit,
#: and the other block's ~36 bytes are inert -- which removes the whole class of
#: "wrote the preset into the object that is not driving" bug.
_POS_BLOCKS = (_POS_ONFOOT, _POS_VEHICLE)


def _set_var32(var_class: int, idx: int, value: int) -> bytes:
    """``set VAR = value`` with the 32-bit const token -- ``05 <var> 7E <i32> 2C 7F``
    (the exact idiom WORLD09's own Init uses to load the position vars)."""
    import struct
    from . import region as R
    return bytes([0x05, var_class, idx, 0x7E]) + struct.pack("<i", int(value)) \
        + bytes([0x2C, 0x7F])


def arrive_writes(x: float, z: float, *, y: float = 4.0, face: int = 0) -> bytes:
    """Preset the world player's persisted-position vars to a WORLD coordinate --
    the walk-out's arrival point (the actor re-grounds on the next movement tick,
    so ``y`` is a seed). BOTH player-object blocks are written (:data:`_POS_BLOCKS`)
    so the preset lands whether the player leaves on foot or vehicle-borne."""
    from . import region as R
    out = b""
    for (xc, xi), (yc, yi), (zc, zi), (fc, fi) in _POS_BLOCKS:
        out += (_set_var32(xc, xi, round(x * 256))
                + R.set_var(yc, yi, round(y * 256))
                + _set_var32(zc, zi, round(z * 256))
                + R.set_var(fc, fi, int(face) & 0xFF))
    return out


def worldmap_to_var(var_class: int = 0xD8, idx: int = WORLD_STATE_VAR) -> bytes:
    """``WorldMap(<VAR>)`` -- opcode 0xB6 with its argFlag bit set, the destination
    read from a variable through the engine's expression path (``getv2`` ->
    ``CalcExpr``; engine-pinned at EventEngine.DoEventCode WMAPJUMP -- the exact
    computed lane :func:`ff9mapkit.content.region.field_to_var` proved for
    ``Field``). Transitions away -- must be the last reachable op on its path."""
    from . import region as R
    return bytes([0xB6, 0x01]) + R._push_var(var_class, idx) + bytes([R.T_END])


def exit_fade() -> bytes:
    """The field->worldmap FADE-OUT, matching the real exit head (field 2800 e21/tag2 @39-100):
    ``DisableMove ; FadeFilter(6,24,white) ; Wait(25)`` -- SUB toward white == the screen fading to
    BLACK over 24 frames, so leaving a field DIMS before the ``WorldMap`` transition instead of
    hard-cutting to the overworld. The verbatim cascade the kit carries is only the shared SUFFIX
    (routing + the ``WorldMap`` arms); the fade lives in each real field's per-field HEAD, which the
    cascade extraction drops -- so a synthesized worldmap exit must re-add it. (``content.event.WARP_FADE``
    is the same mode-6 fade the choice/gateway warps use.)"""
    from ..eb import opcodes as O
    from .event import WARP_FADE
    return O.DISABLE_MOVE + O.fade_filter(*WARP_FADE) + O.wait(25)


def worldmap_exit_body(*, region_key: int = REGION_KEY_RETURN, arrive=None,
                       arrive_face: int = 0, on_exit_body: bytes = b"", fade: bool = True,
                       game=None) -> bytes:
    """The Range body of a walk-out worldmap exit.

    With ``arrive = (x, z)`` (THE DETERMINISTIC RETURN): [usercontrol guard] ->
    [on-exit story writes] -> [FADE-OUT to black] -> [write the arrive coords into the
    position vars] -> [``D8:2`` = nonzero, so the destination Init leaves them alone] ->
    [if the recorded world state is set: ``WorldMap(<it>)`` computed; else fall back to
    the generic cascade]. The player returns to the SAME world state they left,
    at exactly the arrive point.

    Without ``arrive``: [guard] -> [writes] -> [FADE-OUT] -> [``D8:2 = region_key``] ->
    [the verbatim shared cascade] -- lands at the routed world's DEFAULT point (the
    arrival model above). The cascade's arms terminate the function.

    ``fade`` (default True) prepends :func:`exit_fade` so leaving DIMS before the WorldMap
    transition (the real exit behavior); the carried cascade has no fade of its own."""
    import struct
    from . import region as R
    pre = exit_fade() if fade else b""
    if arrive is not None:
        ax, az = arrive
        wm = worldmap_to_var()
        return (R.MOVEMENT_GATE + bytes(on_exit_body) + pre
                + arrive_writes(float(ax), float(az), face=arrive_face)
                + R.set_var(R.GLOB_INT16, R.FIELD_ENTRANCE_IDX, POSITION_PRESET_KEY)
                + R.cond_truthy(0xD8, WORLD_STATE_VAR)
                + bytes([R.JMP_FALSE]) + struct.pack("<h", len(wm))
                + wm
                + cascade_bytes(game))
    return R.MOVEMENT_GATE + bytes(on_exit_body) + pre \
        + R.set_var(R.GLOB_INT16, R.FIELD_ENTRANCE_IDX, region_key) \
        + cascade_bytes(game)
