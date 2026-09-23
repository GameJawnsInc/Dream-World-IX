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

Only a field WITHOUT MapConfigData takes it: a native, editable or BG-borrow fork ships its donor's MCF
(``[field] mapconfig``), whose service shadows every actor -- grafted donor objects included -- and would overwrite a
script value on the first frame anyway -- so native and verbatim forks stay byte-identical.

The TOML key, on ``[player]`` and every ``[[npc]]`` (so every behavior unit)::

    shadow = false                            # no shadow (the ops are not emitted)
    shadow = { size = 12 }                    # override the census size (intensity stays the census')
    shadow = { size = 12, intensity = 6 }     # both; absent/true = the census values for the model

AN AUTHORED INTENSITY STOPS AT 15, BECAUSE THE BLOB'S COLOUR WRAPS AFTER IT. The op carries ``intensity << 3``
in one byte, so 0-31 all encode. But ``EventEngine.SetRenderer`` draws the blob in colour
``(Byte)(amp * 2)``, and from amp 128 up that wraps: intensity ``i`` >= 16 draws exactly as ``i - 16``. So 16
draws no shadow at all and 31 draws the same as 15. In-game on bench 30922, the same slot at 15 and at 31 is
pixel-identical, and so is 16 against 0 (studies/actor-shadow/intensity_wrap.py). ``validate`` refuses an
authored 16-31 and names the census value instead. The census itself keeps its two 16s (models 200 and 488).
Those are stock's own MapConfigData values, which wrap the same way in stock, so an absent key reproduces
stock exactly.

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

ON A FIELD THAT SHIPS MAPCONFIGDATA A SET PIECE'S ONE LEVER IS OFF, AS STOCK'S IS. The MCF shadows every
actor at its own size, so a ``[[prop]]`` part that casts gets no ops there, and one that must not -- a held
prop, or ``shadow`` resolving to false (a model stock disables, or the author's ``false``) -- gets stock's
``DisableShadow`` (:data:`DISABLE_SHADOW`) at its Init tail, straight into the RETURN, as stock places it on
86 free-standing and 37 held objects (``content.prop.inject_prop(mcf=True)``). Without it the MCF drew a
blob under a tent or a held cup that stock never shows (studies/actor-shadow/held_shadow_census.py).

AN ``[[npc]]`` AND THE ``[player]`` DO NOT FOLLOW ``STOCK_CASTS``: an absent key casts the census for any
model. For a creature or character, stock's disables follow where the object is: perched or flying, walkmesh-
unbound in the frog pond, or hidden until a scene. A kit actor always stands on the walkmesh, where stock's
objects cast 2141 of 2191 times (studies/actor-shadow/NPC-STOCK-CASTS.md; tests/test_shadow_npc_default.py).
"""
from __future__ import annotations

from .. import _shadowparams
from ..eb import EbScript, edit, opcodes
from .ladder import find_player_entry

SET_SHADOW_SIZE = 0x81          # SHADOWSCALE -> ff9shadow.FF9ShadowSetScaleField(uid, x, z)
SET_SHADOW_AMP = 0x85           # SHADOWAMP   -> ff9shadow.FF9ShadowSetAmpField(uid, amp)
DISABLE_SHADOW = 0x80           # SHADOWOFF   -> ff9shadow.FF9ShadowOffField(uid): char attr bit 16, which the
                                #                MCF service's per-frame scale/amp writes never clear
SET_HEAD_FOCUS_MASK = 0x8B      # the player-Init anchor (field 451's Zidane sets its shadow right after it)
SET_MODEL = 0x2F

SIZE_MAX = 255                  # getv1 (one byte); the quad is 224*size/16 x 192*size/16 field units
INTENSITY_MAX = 15              # the AUTHORED cap: 16-31 encode, but the blob's DRAW colour wraps (see the docstring)
INTENSITY_ENCODABLE_MAX = 31    # amp = intensity << 3 must fit SetShadowAmplifier's one byte (the census obeys this)

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


def _intensity_advice(v, model) -> str:
    """Why an authored intensity past :data:`INTENSITY_MAX` is refused, and what to write instead."""
    if model is None:
        census = "drop `intensity` for the census value for the actor's model (mostly 3-4)"
    else:
        ci = params_for(model)[1]
        census = (f"drop `intensity` for this model's census value ({ci})" if ci <= INTENSITY_MAX else
                  f"drop `intensity` for this model's census value ({ci}): stock's own value, which wraps "
                  f"the same way in stock, so dropping the key matches stock exactly")
    wrap = ""
    if isinstance(v, int) and not isinstance(v, bool) and INTENSITY_MAX < v <= INTENSITY_ENCODABLE_MAX:
        wrap = f" and {v} would draw exactly as {v - 16}" + (" (no shadow at all)" if v == 16 else "")
    return (f": the engine draws the blob in colour (amp * 2) & 0xFF with amp = intensity << 3, so 16-31 "
            f"wrap{wrap}. Pick 0-{INTENSITY_MAX}, or {census}")


def problems(value, label: str, model=None) -> list:
    """Validation messages for one ``shadow`` value (empty = fine). Shared by validate and the build.
    ``model``, when the caller knows it, lets an out-of-range intensity name that model's census value."""
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
                msg = f"{label} shadow.{k} must be an integer 0-{hi}, got {v!r}"
                if k == "intensity" and isinstance(v, int) and not isinstance(v, bool) and v > hi:
                    msg += _intensity_advice(v, model)
                out.append(msg)
    return out


def resolve(value, model):
    """``(size, intensity)`` for one actor, or None when it casts no shadow. ``value`` is the TOML
    ``shadow`` key: absent/None/true = the census for ``model``; false = none; a table overrides."""
    if value is False:
        return None
    msgs = problems(value, "shadow", model)
    if msgs:
        raise ValueError("; ".join(msgs))
    size, intensity = params_for(model)
    if isinstance(value, dict):
        size = int(value.get("size", size))
        intensity = int(value.get("intensity", intensity))
    return size, intensity


def blob_colour(intensity: int) -> int:
    """The grey the engine draws a field actor's blob in: ``EventEngine.SetRenderer``'s ``(Byte)(amp * 2)``
    with amp = ``intensity << 3`` (the op's argument). It wraps from 16, so :data:`INTENSITY_MAX` is 15."""
    return ((int(intensity) << 3) * 2) & 0xFF


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
    ``[player] model`` re-skin. Any model casts, including one ``STOCK_CASTS`` disables: 1022 of stock's
    1054 player objects cast, and the 32 that do not are scripted scenes, not the model
    (studies/actor-shadow/NPC-STOCK-CASTS.md)."""
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
