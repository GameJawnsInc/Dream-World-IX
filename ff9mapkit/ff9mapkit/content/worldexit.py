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

THE KEY MODEL (fully decoded -- the cascade's switch tables + arms + WORLD09
e5/tag0, the world player's Init):

* a CASED key other than 62 (what real exit fields write): ``WorldMap(<state>)``
  with the key LEFT SET -- the destination world's Init sees ``D8:2`` nonzero and
  teleports the player to its HARDCODED door arrival (the real-town pattern).
* **key 62**: the arm itself runs ``D8:2 = 0; WorldMap(9009)`` in EVERY
  ScenarioCounter band -- arrival sees zero, so the Init skips the door override
  and ``MoveInstantXZY`` places the player from the PERSISTED position vars
  (``C8:0x53``/``D8:0x56``/``C8:0x58``, mirrored from the live position every
  frame). "Return exactly where you stood, in the all-vehicle free-roam
  superset" -- the right semantic for a field on kit-built land, and the kit
  default. (No real field writes 62; the lane is the game's own maintained
  generic return.)
* **key 0 / any un-cased key**: the switch default is a bare RETURN -- the
  handler exits WITHOUT warping and the door reads as dead (playtest-proven).
  0 is the "no exit set" guard, never a valid exit key.

Dev caveat: an F6 teleport that lands ON the entrance trigger fires the warp the
SAME frame, before one position-mirror tick -- the persisted position then still
holds the pre-teleport spot. Walked entries (the shipping path) are always
current.
"""

from __future__ import annotations

from ..eb.model import EbScript

#: the two byte-verified cascade carriers: (field id, entry index, func tag)
CASCADE_DONORS = ((300, 2, 2), (2800, 21, 2))
#: the default region key: 62 = the generic-return arm (D8:2=0 + WorldMap(9009) in
#: every SC band -> the persisted-position arrival). 0/un-cased keys DO NOT WARP
#: (the switch default is a bare return -- the key model above).
REGION_KEY_RETURN = 62
REGION_KEY_OPEN_SEA = 62  # back-compat alias
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


def worldmap_exit_body(*, region_key: int = REGION_KEY_RETURN, on_exit_body: bytes = b"",
                       game=None) -> bytes:
    """The Range body of a walk-out worldmap exit: [usercontrol guard] -> [optional
    on-exit story writes] -> [D8:2 = region_key] -> [the verbatim shared cascade].
    The cascade's own arms terminate the function (each ends in ``WorldMap`` + the
    donor's return), so nothing follows."""
    from . import region as R
    return R.MOVEMENT_GATE + bytes(on_exit_body) \
        + R.set_var(R.GLOB_INT16, R.FIELD_ENTRANCE_IDX, region_key) \
        + cascade_bytes(game)
