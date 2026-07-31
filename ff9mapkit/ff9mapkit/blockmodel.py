"""Which MODEL a content block wears -- the ONE precedence, shared by the build and the GUI.

A ``[[npc]]`` names its model three ways: a named ``archetype``/``preset`` (the majority of blocks), a
bare ``model =`` (raw id or exact GEO name), or nothing at all (it keeps the cloned player's model).
An explicit ``anims=``/``animset=`` on the block always keeps the last word over whatever the archetype
resolved. That precedence used to live only inside ``build._npc_model_kwargs``; every surface that
wants to SHOW a block's model -- scoping an animation picker to the clips that rig can actually play,
resolving a cutscene actor's gestures -- needs the same answer, and a second copy would drift off the
one the build spends. So the rule lives HERE, Qt-free and install-free (identifier data only), and
``build`` calls it.

``[player]`` is the same question with a different default: its ``model`` key re-skins the avatar, and
its absence means the stock cloned player, who is Zidane (:data:`PLAYER_DEFAULT_GEO`).
"""
from __future__ import annotations

from typing import NamedTuple, Optional

from . import archetypes as _archetypes
from . import catalog as _catalog

PLAYER_DEFAULT_GEO = "GEO_MAIN_F0_ZDN"      # the avatar a field with no `[player] model` clones


class BlockModel(NamedTuple):
    """What one content block resolves to. ``model`` is None when the block deliberately has none (the
    ``zidane`` preset / a bare ``[[npc]]``) -- ``reason`` then says so in words a picker can show."""
    model: Optional[int]        # the id SetModel takes, or None (keeps the cloned player's model)
    source: str                 # archetype | preset | model | player | player-default | none
    anims_source: str           # explicit | archetype | catalog | none
    animset: Optional[int]
    anims: Optional[dict]
    reason: Optional[str]       # why there is no model, or why resolution failed (strict=False)


def resolve_model_value(value):
    """A block's ``model`` value -> the numeric model id ``SetModel`` takes.

    A raw id (int / digit string) passes through UNCHANGED -- that is what keeps every shipped numeric
    example byte-identical -- an exact GEO name resolves through the catalog, and ``None`` stays None
    (keep the cloned player's model). Raises ValueError with near-miss suggestions on an unknown name."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("[[npc]] model cannot be a boolean")
    if isinstance(value, int) or str(value).strip().isdigit():
        return int(value)
    return _catalog.resolve_model(value)


def resolve_block_model(block, *, kind: str = "npc", strict: bool = True) -> BlockModel:
    """One ``[[npc]]`` (or ``[player]``, ``kind="player"``) block -> its :class:`BlockModel`.

    ``strict`` (the build's setting) lets an unresolvable model NAME raise, exactly as the build needs
    it to; ``strict=False`` (a GUI's setting) captures the message into ``reason`` and answers with
    ``model=None`` instead, so a half-typed toml never breaks a picker."""
    b = block or {}
    try:
        return _resolve(b, kind)
    except ValueError as e:
        if strict:
            raise
        return BlockModel(None, "none", "none", b.get("animset"), b.get("anims") or None, str(e))


def _resolve(b: dict, kind: str) -> BlockModel:
    if kind == "player":
        mv = b.get("model")
        mid = resolve_model_value(mv) if mv is not None else _catalog.resolve_model(PLAYER_DEFAULT_GEO)
        anims = (_catalog.npc_anims(mid) or None) if mid is not None else None
        return BlockModel(mid, "player" if mv is not None else "player-default",
                          "catalog" if anims else "none", None, anims, None)

    arch = b.get("archetype") or b.get("preset")
    if arch is not None:
        model, animset, anims, _dlg = _archetypes.resolve(arch)
        asrc = "archetype" if anims else "none"
        if b.get("animset") is not None:
            animset = b.get("animset")
        if b.get("anims"):
            anims, asrc = b["anims"], "explicit"
        reason = None if model is not None else (
            f"the {str(arch).strip().lower()!r} preset keeps the cloned player's model, so this block "
            f"has no model of its own")
        return BlockModel(model, "archetype" if b.get("archetype") else "preset",
                          asrc, animset, anims, reason)

    mid = resolve_model_value(b.get("model"))
    anims = b.get("anims")
    asrc = "explicit" if anims else "none"
    if mid is not None and not anims:
        anims = _catalog.npc_anims(mid) or None       # any model by name -> its own gestures (Info Hub)
        asrc = "catalog" if anims else "none"
    reason = None if mid is not None else "no model = on this block -- it keeps the cloned player's model"
    return BlockModel(mid, "model" if b.get("model") is not None else "none",
                      asrc, b.get("animset"), anims, reason)
