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
``Field()`` warp uses as its arrival entrance -- ``region.set_field_entrance``). The
default key **62 is 9009's own key that NO real field writes**: within every SC band it
resolves (by case or default arm) to **9009, the all-vehicle free-roam superset** --
the right return for a field on kit-built land in open ocean, whatever state the
player arrived in. The world actor position persists across the visit (the engine
restores it, exactly like leaving a real town).
"""

from __future__ import annotations

from ..eb.model import EbScript

#: the two byte-verified cascade carriers: (field id, entry index, func tag)
CASCADE_DONORS = ((300, 2, 2), (2800, 21, 2))
#: the un-written region key that resolves to wldMapNo 9009 in every SC band
REGION_KEY_OPEN_SEA = 62
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


def worldmap_exit_body(*, region_key: int = REGION_KEY_OPEN_SEA, on_exit_body: bytes = b"",
                       game=None) -> bytes:
    """The Range body of a walk-out worldmap exit: [usercontrol guard] -> [optional
    on-exit story writes] -> [D8:2 = region_key] -> [the verbatim shared cascade].
    The cascade's own arms terminate the function (each ends in ``WorldMap`` + the
    donor's return), so nothing follows."""
    from . import region as R
    return R.MOVEMENT_GATE + bytes(on_exit_body) \
        + R.set_var(R.GLOB_INT16, R.FIELD_ENTRANCE_IDX, region_key) \
        + cascade_bytes(game)
