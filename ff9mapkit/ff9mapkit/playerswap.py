"""Swap who you WALK as in a forked field -- patch the player entry's ``SetModel`` + movement anim ids to a
different EXISTING character's rig.

Field control (who you walk as) is DECOUPLED from party state (the menu/battle roster), so this changes only
the field-controlled character; the party is untouched (use a party-membership op for that). It is the
productionized form of the in-game-proven Tier-A probe: a same-length, width-aware byte patch of the player
entry's tag-0 Init -- ``.eb``-only, no DLL (memory ``project-ff9-pc-party-system`` / ``project-ff9-non-zidane-donors``).

:data:`CHARACTERS` holds each playable's canonical field player-Init values (model id + eye-height + the
movement clips), EXTRACTED from that character's own home field. The animation ids are rig-partitioned -- the
engine does NOT translate a Zidane clip id onto another rig -- so every movement clip the field's player Init
sets must be repointed to the target rig (else a wrong-skeleton anim / T-pose).
"""
from __future__ import annotations

from .eb import EbScript
from .eb.disasm import argsize

SETMODEL_OP = 0x2F
ANIM_OPS = {0x33: "idle", 0x34: "walk", 0x35: "run", 0x7A: "left", 0x7B: "right", 0x52: "inactive"}

# Canonical field player-Init values per playable, read from each character's home field (model, eye-height,
# movement clips). idle/walk/run/left/right exist for all 8; ``inactive`` (the idle-break) only where the home
# field set a generic one -- :func:`swap_player` falls back to ``idle`` for a clip the target lacks (a valid
# clip on that rig). Verified in-game for Steiner (the Tier-A probe).
CHARACTERS = {
    "zidane":  {"model": 98,   "eye": 93,  "idle": 200,  "walk": 25,   "run": 38,   "left": 40,   "right": 41,   "inactive": 57},
    "vivi":    {"model": 8,    "eye": 61,  "idle": 148,  "walk": 571,  "run": 419,  "left": 917,  "right": 918,  "inactive": 912},
    "steiner": {"model": 5489, "eye": 104, "idle": 2001, "walk": 1996, "run": 2005, "left": 1986, "right": 2010, "inactive": 119},
    "garnet":  {"model": 185,  "eye": 91,  "idle": 2089, "walk": 2086, "run": 2091, "left": 2088, "right": 2084},
    "freya":   {"model": 192,  "eye": 94,  "idle": 2556, "walk": 2553, "run": 2558, "left": 2555, "right": 2551},
    "quina":   {"model": 273,  "eye": 92,  "idle": 3228, "walk": 3237, "run": 3230, "left": 3235, "right": 3227},
    "eiko":    {"model": 443,  "eye": 63,  "idle": 7503, "walk": 7518, "run": 7506, "left": 7516, "right": 7514},
    "amarant": {"model": 509,  "eye": 122, "idle": 8307, "walk": 8316, "run": 8312, "left": 8310, "right": 8314},
}
ALIASES = {"dagger": "garnet", "salamander": "amarant"}


def resolve_char(name):
    """``(canonical_name, spec)`` for a character name (case-insensitive; aliases ``dagger``->garnet,
    ``salamander``->amarant). Raises ``ValueError`` on an unknown name."""
    k = ALIASES.get(str(name).lower().strip(), str(name).lower().strip())
    if k not in CHARACTERS:
        raise ValueError("unknown character %r -- choose from %s (aliases: dagger, salamander)"
                         % (name, ", ".join(sorted(CHARACTERS))))
    return k, CHARACTERS[k]


def _arg_off(ins, ai):
    """Byte offset (relative to ``ins.off``) of literal operand ``ai`` -- opcode head + the argflag byte
    (ops >= 0x10 with args) + the widths of the preceding operands."""
    off = 2 if ins.op >= 0x100 else 1
    if ins.op >= 0x10 and len(ins.args) != 0:
        off += 1
    for k in range(ai):
        off += argsize(ins.op, k)
    return off


def player_entry_to_swap(eb):
    """The entry whose player to swap = the CONTROLLED one (:func:`forkreport.controlled_player`) when it has
    a ``SetModel`` in its Init, else the first player entry that does. ``None`` if none has a ``SetModel``."""
    from . import eventscan, forkreport
    pents = eventscan.resolve_player_entries(eb)
    if not pents:
        return None

    def has_setmodel(p):
        init = eb.entry(p).func_by_tag(0)
        return init is not None and any(i.op == SETMODEL_OP for i in eb.instrs(init))

    ctrl = forkreport.controlled_player(eb)[0]
    if ctrl is not None and has_setmodel(ctrl):
        return ctrl
    return next((p for p in pents if has_setmodel(p)), None)


def swap_player(eb_bytes, char, *, entry=None) -> bytes:
    """Patch the player entry's Init ``SetModel`` + movement anim ids to ``char``'s rig (same-length,
    width-aware). ``entry`` defaults to the controlled player entry. Returns new ``.eb`` bytes
    (round-trip-checked). Raises ``ValueError`` on an unknown char / no swappable player entry."""
    _name, spec = resolve_char(char)
    eb = EbScript.from_bytes(eb_bytes)
    if entry is None:
        entry = player_entry_to_swap(eb)
    if entry is None:
        raise ValueError("no player entry with a SetModel to swap")
    init = eb.entry(entry).func_by_tag(0)
    out = bytearray(eb_bytes)

    def put(ins, ai, value):
        w = argsize(ins.op, ai)
        if int(value) >= (1 << (8 * w)):
            raise ValueError("value %d does not fit arg %d (%d byte(s)) of op %#x" % (value, ai, w, ins.op))
        o = ins.off + _arg_off(ins, ai)
        out[o:o + w] = int(value).to_bytes(w, "little")

    for ins in eb.instrs(init):
        if any(ins.arg_is_expr):
            continue
        if ins.op == SETMODEL_OP and len(ins.args) >= 2:
            put(ins, 0, spec["model"])
            put(ins, 1, spec["eye"])
        elif ins.op in ANIM_OPS and ins.args:
            put(ins, 0, spec.get(ANIM_OPS[ins.op], spec["idle"]))

    out = bytes(out)
    if EbScript.from_bytes(out).to_bytes() != out:                # the patch must not corrupt the structure
        raise ValueError("player swap produced a non-round-tripping .eb")
    return out
