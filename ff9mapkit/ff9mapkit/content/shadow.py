"""The stock field BLOB SHADOW under a kit-field actor -- ``[player] shadow`` / ``[[npc]] shadow``.

WHY A KIT FIELD HAD NONE. A real field never scripts its actors' shadows: its MapConfigData does
(:mod:`ff9mapkit.mapconfig`). Every frame ``fldmcf.ff9fieldMCFService`` gives each actor
``FF9ShadowSetAmpField(uid, shadowI << 3)`` + ``FF9ShadowSetScaleField(uid, shadowR, shadowR)`` from the
field's per-model rows. A synthesized field ships no MapConfigData, so that service returns at its first
line, the actor's ``new FF9Shadow()`` keeps ``xScale = zScale = 0``, and ``EventEngine.SetRenderer`` copies
that zero into the shadow quad on the actor's first frame -- the blob is there, zero wide.

THE FIX IS THE SAME TWO ENGINE CALLS, REACHED FROM THE SCRIPT. ``SetShadowSize`` (0x81) is
``FF9ShadowSetScaleField(uid, x, z)`` and ``SetShadowAmplifier`` (0x85) is ``FF9ShadowSetAmpField(uid, a)``
(``EventEngine.DoEventCode`` SHADOWSCALE / SHADOWAMP). Emitted as ``SetShadowSize(size, size)`` +
``SetShadowAmplifier(intensity << 3)`` they set exactly what the MCF service would have set, and on a field
with no MCF nothing ever overwrites them. The VALUES are the census (:mod:`ff9mapkit._shadowparams`): per
model, the modal ``shadowR``/``shadowI`` the 818 shipping fields' MCFs apply to it. The SHAPE is stock's:
an object Init that sets its shadow does it at the tail, ``81 00 RR RR`` straight into the ``04`` RETURN
(field 576's Brahne ``SetShadowSize(5, 5)``), size before amplifier (field 207's chest,
``81 00 20 20 85 00 C0``); a player Init does it after its ``SetHeadFocusMask`` (field 451's Zidane).

Only a field WITHOUT MapConfigData takes it: a native fork ships its donor's MCF (``[field] mapconfig``),
whose service would overwrite a script value on the first frame anyway -- so those builds, and every
verbatim fork, stay byte-identical.

The TOML key, on ``[player]`` and every ``[[npc]]`` (so every behavior unit)::

    shadow = false                            # no shadow (the ops are not emitted)
    shadow = { size = 12 }                    # override the census size (intensity stays the census')
    shadow = { size = 12, intensity = 6 }     # both; absent/true = the census values for the model

SET PIECES FOLLOW STOCK'S SCRIPT TOO, NOT ONLY ITS MCF. The MCF gives EVERY actor a shadow, but an object's
Init can ``DisableShadow`` it, and stock does that to most set dressing: for 68 of the 84 accessory models it
shows standing free, its objects switch the shadow off on every path through their Init (the tent 66 of 67,
the save book 58 of 58, the letter 57 of 57), while the chests (the four TBX models, 221 of 224) and the
cask (19 of 19) keep theirs. That per-model verdict is ``_shadowparams.STOCK_CASTS`` (:func:`stock_casts`),
and it is the DEFAULT for a ``[[prop]]`` -- absent ``shadow`` casts only when stock would; ``true`` / a table
casts anyway. A HELD prop (``attach_to`` / ``[[npc]] holds``) never casts: stock disables 139 of its 140
held objects, and the engine positions an attached object's quad badly (``GetShadowCurrentPos`` takes its
HEIGHT from ``transform.localPosition`` -- for an attached object, the bone-local offset). The rest of
stock's casting set pieces get the same ops at the same Init tail: ``[[chest]]`` (every TBX model casts)
and the save point's moogle + its barrel_pop cask (58 of 58 stock save moogles keep theirs; the act's own
``DisableShadow`` / ``EnableShadow`` hop pair -- verbatim from the donor -- now has a shadow to hide). The
act's book + feather keep their donor ``DisableShadow`` and get no ops. (In-game: a cask's census blob is
real but drawn entirely under the barrel's own footprint, as stock's is -- studies/actor-shadow/PLAN.md.)
"""
from __future__ import annotations

from .. import _shadowparams
from ..eb import EbScript, edit, opcodes
from .ladder import find_player_entry

SET_SHADOW_SIZE = 0x81          # SHADOWSCALE -> ff9shadow.FF9ShadowSetScaleField(uid, x, z)
SET_SHADOW_AMP = 0x85           # SHADOWAMP   -> ff9shadow.FF9ShadowSetAmpField(uid, amp)
SET_HEAD_FOCUS_MASK = 0x8B      # the player-Init anchor (field 451's Zidane sets its shadow right after it)
SET_MODEL = 0x2F

SIZE_MAX = 255                  # getv1 (one byte); the quad is 224*size/16 x 192*size/16 field units
INTENSITY_MAX = 31              # amp = intensity << 3 must fit SetShadowAmplifier's one byte

_KEYS = ("size", "intensity")


def params_for(model) -> tuple:
    """``(size, intensity)`` the shipping fields give ``model`` -- the census, else its ``DEFAULT``."""
    try:
        return _shadowparams.SHADOW_PARAMS.get(int(model), _shadowparams.DEFAULT)
    except (TypeError, ValueError):
        return _shadowparams.DEFAULT


def stock_casts(model) -> bool:
    """Whether stock lets ``model``'s shadow show on a free-standing object (``_shadowparams.STOCK_CASTS``:
    its objects do not ``DisableShadow`` it on every path through their Init), else
    ``PROP_DEFAULT_CASTS`` for a model no stock object shows standing free."""
    try:
        return bool(_shadowparams.STOCK_CASTS.get(int(model), _shadowparams.PROP_DEFAULT_CASTS))
    except (TypeError, ValueError):
        return bool(_shadowparams.PROP_DEFAULT_CASTS)


def set_piece_value(value, model):
    """The ``shadow`` value a SET PIECE (``[[prop]]`` part, chest, barrel_pop cask) casts with: an absent
    key (None) becomes stock's verdict for ``model`` (:func:`stock_casts` -> True, else False); an explicit
    true / false / table is the author's and passes through. Feed the result to :func:`init_ops`."""
    return stock_casts(model) if value is None else value


def problems(value, label: str) -> list:
    """Validation messages for one ``shadow`` value (empty = fine). Shared by validate and the build."""
    if value is None or isinstance(value, bool):
        return []
    if not isinstance(value, dict):
        return [f"{label} shadow must be true, false, or a table {{ size = N, intensity = N }}, "
                f"got {value!r}"]
    out = []
    unknown = sorted(set(value) - set(_KEYS))
    if unknown:
        out.append(f"{label} shadow: unknown key(s) {', '.join(unknown)} (have: size, intensity)")
    for k, hi in (("size", SIZE_MAX), ("intensity", INTENSITY_MAX)):
        if k in value:
            v = value[k]
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= hi:
                out.append(f"{label} shadow.{k} must be an integer 0-{hi}, got {v!r}")
    return out


def resolve(value, model):
    """``(size, intensity)`` for one actor, or None when it casts no shadow. ``value`` is the TOML
    ``shadow`` key: absent/None/true = the census for ``model``; false = none; a table overrides."""
    if value is False:
        return None
    msgs = problems(value, "shadow")
    if msgs:
        raise ValueError("; ".join(msgs))
    size, intensity = params_for(model)
    if isinstance(value, dict):
        size = int(value.get("size", size))
        intensity = int(value.get("intensity", intensity))
    return size, intensity


def ops(size: int, intensity: int) -> bytes:
    """``SetShadowSize(size, size)`` + ``SetShadowAmplifier(intensity << 3)`` -- stock's order and bytes."""
    return (opcodes.encode(SET_SHADOW_SIZE, int(size), int(size))
            + opcodes.encode(SET_SHADOW_AMP, int(intensity) << 3))


def init_ops(model, value=None) -> bytes:
    """The Init-tail shadow ops for an actor wearing ``model`` (``b""`` when ``value`` opts out)."""
    r = resolve(value, model)
    return b"" if r is None else ops(*r)


def player_model(data) -> int:
    """The model the field player's Init ``SetModel``s (after any ``[player] model`` re-skin)."""
    eb = EbScript.from_bytes(data)
    f0 = eb.entry(find_player_entry(eb)).func_by_tag(0)
    sm = next((i for i in eb.instrs(f0) if i.op == SET_MODEL), None)
    if sm is None or sm.imm(0) is None:
        raise ValueError("the field player's Init has no literal SetModel -- cannot size its shadow")
    return int(sm.imm(0))


def cast_player_shadow(data, value=None) -> bytes:
    """Splice the player's shadow ops into its Init right after ``SetHeadFocusMask`` (field 451's
    Zidane; straight-line setup code, ahead of the grant chain's jumps). ``value`` is ``[player] shadow``;
    false returns ``data`` unchanged. Sized from the player's CURRENT model, so run it after the
    ``[player] model`` re-skin."""
    ins = init_ops(player_model(data), value)
    if not ins:
        return data
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    f0 = eb.entry(pe).func_by_tag(0)
    hf = next((i for i in eb.instrs(f0) if i.op == SET_HEAD_FOCUS_MASK), None)
    if hf is None:
        raise ValueError("the field player's Init has no SetHeadFocusMask -- no stock anchor for its shadow")
    return edit.insert_in_function(data, pe, 0, hf.end - f0.abs_start, ins)
