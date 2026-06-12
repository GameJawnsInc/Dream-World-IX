"""Swap who you WALK as in a forked field -- patch the player entry's ``SetModel`` + movement anim ids to a
different rig: one of the 8 PLAYABLES (a proven home-field table) or ANY registered model -- a moogle, an NPC,
a creature -- resolved through the kit's model->animation join (:func:`catalog.npc_anims`). The latter is the
field-side bridge toward CUSTOM characters: a custom model would be driven by exactly this path.

Field control (who you walk as) is DECOUPLED from party state (the menu/battle roster), so this changes only
the field-controlled character; the party is untouched (use a party-membership op for that). It is the
productionized form of the in-game-proven Tier-A probe: a same-length, width-aware byte patch of the player
entry's tag-0 Init -- ``.eb``-only, no DLL (memory ``project-ff9-pc-party-system`` / ``project-ff9-non-zidane-donors``).

:data:`CHARACTERS` holds each playable's canonical field player-Init values (model id + eye-height + the
movement clips), EXTRACTED from that character's own home field. The animation ids are rig-partitioned -- the
engine does NOT translate a Zidane clip id onto another rig -- so every movement clip the field's player Init
sets must be repointed to the target rig (else a wrong-skeleton anim / T-pose).

CAVEAT -- free-roam vs cutscene fields: this swaps only the 6 MOVEMENT clips (idle/walk/run/turns), which is
everything a free-roam field needs (proven clean: walk Quina/Steiner around the Hangar). But a STORY-EVENT
field can make the PLAYER play scripted GESTURES in a cutscene via ``RunAnimation`` (0x40) with a specific
clip id -- that id is NOT swapped, so it would try to play the ORIGINAL rig's clip on the new model and
glitch/T-pose. So ``--swap-player`` is clean on free-roam fields and cosmetic-and-risky on cutscene-heavy
ones; :func:`scripted_gesture_ops` flags that risk. For STORY fidelity (be a character THROUGH the story),
the right tool is a verbatim fork at the right beat with the right party, not a model swap.
"""
from __future__ import annotations

from .eb import EbScript
from .eb.disasm import argsize

SETMODEL_OP = 0x2F
ANIM_OPS = {0x33: "idle", 0x34: "walk", 0x35: "run", 0x7A: "left", 0x7B: "right", 0x52: "inactive"}
RUN_ANIM_OPS = frozenset({0x40, 0xBD})   # RunAnimation / RunAnimationEx -- scripted gesture plays (rig-specific)
ZIDANE_LEADER_MODELS = frozenset({98, 532})   # the controllable Zidane FIELD forms (ZDN + ZDD disguise)


class NoSwappablePlayer(ValueError):
    """No player entry has a ``SetModel`` to swap (a benign per-member skip in a chain). A subclass of
    ValueError so existing handlers still catch it, but distinguishable from a real patch/corruption error."""

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
    """``(canonical_name, spec)`` for a swap target. A playable name (zidane..amarant; aliases ``dagger``->
    garnet, ``salamander``->amarant) returns its proven home-field rig table. ANY OTHER registered model -- a
    ``GEO_..`` name or a numeric id (a moogle, an NPC, a creature) -- returns a spec built from the kit's
    model->animation join (:func:`catalog.npc_anims`), so you can walk as it: the field-side bridge to custom
    characters (a custom model would use the same path). ``spec`` always has ``model`` + the movement clips;
    a playable also carries ``eye`` + ``inactive``. Raises ``ValueError`` on an unknown target or a model with
    no movement animations (e.g. a static monster)."""
    k = ALIASES.get(str(name).lower().strip(), str(name).lower().strip())
    if k in CHARACTERS:
        return k, CHARACTERS[k]
    from . import catalog
    try:
        mid = catalog.resolve_model(name)
    except Exception:
        raise ValueError("unknown swap target %r -- a playable (%s; aliases dagger, salamander) or a model "
                         "name/id (see `ff9mapkit models`)" % (name, ", ".join(sorted(CHARACTERS))))
    na = catalog.npc_anims(mid)                          # {stand,walk,run,left,right} via the model->anim join
    if not na:
        from ._modeldb import MODELS
        raise ValueError("model %s has no movement animations -- can't walk as it"
                         % MODELS.get(mid, mid))
    from ._modeldb import MODELS
    spec = {"model": mid, "idle": na["stand"], "walk": na["walk"], "run": na["run"],
            "left": na["left"], "right": na["right"]}    # no 'eye' (keep the field's) / no 'inactive' (-> idle)
    return MODELS.get(mid, str(mid)), spec


def _arg_off(ins, ai):
    """Byte offset (relative to ``ins.off``) of literal operand ``ai`` -- opcode head + the argflag byte
    (ops >= 0x10 with args) + the widths of the preceding operands."""
    off = 2 if ins.op >= 0x100 else 1
    if ins.op >= 0x10 and len(ins.args) != 0:
        off += 1
    for k in range(ai):
        off += argsize(ins.op, k)
    return off


def _has_setmodel(eb, p):
    init = eb.entry(p).func_by_tag(0)
    return init is not None and any(i.op == SETMODEL_OP for i in eb.instrs(init))


def leader_model(eb):
    """The model of the character you actually CONTROL -- the swap target. On a ZIDANE-PRESENT field control
    routes through the party SLOT to the Zidane party-leader, NOT the last-``DefinePlayerCharacter`` binder
    (:func:`forkreport.controlled_player` mispredicts there -- it returns a co-actor on 66/169 such fields), so
    target a Zidane field form (98/532) when one is defined. On a no-Zidane FIXED-SID field, use the proven
    binder (Treno -> Garnet). Single-PC -> the one. Returns the model id, or ``None`` if no swappable entry."""
    from . import eventscan, forkreport
    pents = eventscan.resolve_player_entries(eb)
    have = {p: eventscan._player_model(eb, p) for p in pents
            if eventscan._player_model(eb, p) is not None and _has_setmodel(eb, p)}
    if not have:
        return None
    zid = [m for m in have.values() if m in ZIDANE_LEADER_MODELS]
    if zid:
        return zid[0]                                   # Zidane-present -> you control the Zidane party-leader
    ctrl = forkreport.controlled_player(eb)[0]          # no Zidane -> the proven last-0x2C binder
    return have.get(ctrl, next(iter(have.values())))


def swap_targets(eb):
    """The player entries the swap patches = ALL entries whose Init ``SetModel`` == the controlled-leader model
    (so a Zidane-present field hits the real leader -- not a companion -- and a duplicate leader entry is handled
    too). Empty when no swappable entry exists."""
    from . import eventscan
    m = leader_model(eb)
    if m is None:
        return []
    return [p for p in eventscan.resolve_player_entries(eb)
            if eventscan._player_model(eb, p) == m and _has_setmodel(eb, p)]


def scripted_gesture_ops(eb_bytes, *, entry=None) -> int:
    """How many scripted-gesture ops (``RunAnimation``/``RunAnimationEx``) the player entry plays. These
    reference the ORIGINAL rig's clips (the swap only repoints the 6 movement clips), so any count > 0 means
    ``--swap-player`` will glitch those gestures on the new model -- i.e. the field is a cutscene-heavy one
    where the swap is cosmetic-and-risky, not a clean free-roam swap. Used to WARN at swap time."""
    eb = EbScript.from_bytes(eb_bytes)
    targets = [entry] if entry is not None else swap_targets(eb)
    return sum(1 for e in targets for f in eb.entry(e).funcs for i in eb.instrs(f) if i.op in RUN_ANIM_OPS)


def swap_player(eb_bytes, char, *, entry=None) -> bytes:
    """Patch the controlled-leader player entr(ies)' Init ``SetModel`` + movement anim ids to ``char``'s rig
    (same-length, width-aware). ``entry`` overrides the target; otherwise ALL :func:`swap_targets` (every entry
    matching the controlled-leader model) are patched. Returns new ``.eb`` bytes (round-trip-checked). Raises
    :class:`NoSwappablePlayer` when no player entry has a ``SetModel``, ``ValueError`` on an unknown char or a
    patch that would overflow / corrupt the script."""
    _name, spec = resolve_char(char)
    eb = EbScript.from_bytes(eb_bytes)
    targets = [entry] if entry is not None else swap_targets(eb)
    if not targets:
        raise NoSwappablePlayer("no player entry with a SetModel to swap")
    out = bytearray(eb_bytes)

    def put(ins, ai, value):
        w = argsize(ins.op, ai)
        if int(value) >= (1 << (8 * w)):
            raise ValueError("value %d does not fit arg %d (%d byte(s)) of op %#x" % (value, ai, w, ins.op))
        o = ins.off + _arg_off(ins, ai)
        out[o:o + w] = int(value).to_bytes(w, "little")

    for tgt in targets:
        for ins in eb.instrs(eb.entry(tgt).func_by_tag(0)):
            if any(ins.arg_is_expr):
                continue
            if ins.op == SETMODEL_OP and ins.args:
                put(ins, 0, spec["model"])
                if "eye" in spec and len(ins.args) >= 2:        # playables carry an eye-height; an arbitrary
                    put(ins, 1, spec["eye"])                    # model keeps the field's (cosmetic dialog anchor)
            elif ins.op in ANIM_OPS and ins.args:
                put(ins, 0, spec.get(ANIM_OPS[ins.op], spec["idle"]))

    out = bytes(out)
    if EbScript.from_bytes(out).to_bytes() != out:                # the patch must not corrupt the structure
        raise ValueError("player swap produced a non-round-tripping .eb")
    return out
