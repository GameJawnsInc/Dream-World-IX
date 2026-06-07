"""Author-facing character animation catalog for cutscenes.

Pick a gesture by NAME -- ``animation = "glad"`` -- instead of hunting a numeric id. Backed by
:mod:`ff9mapkit._animdb` (FF9 anim id <-> name, from Memoria's open-source ``AnimationDB``). An anim
name encodes its model + action: ``ANH_MAIN_F0_VIV_TALK_3_1`` -> character ``VIV`` (Vivi), form
``F0``, action ``TALK_3_1``. The engine loads an anim by name->id onto the matching model on demand
(``AnimationFactory``), so any anim tokened to a character's model plays on that model -- proven
in-game with Vivi 7302 (= ``TALK_3_1``).

Usage::

    from ff9mapkit import animations
    animations.resolve("vivi", "glad")        # -> 1234  (action by name on Vivi's model)
    animations.resolve("vivi", "idle")        # -> 148   (a universal CORE gesture)
    animations.resolve("vivi", 7302)          # -> 7302  (a raw id passes through)
    animations.actions("vivi")                # -> [("angry", 111), ("angry_2", ...), ...]

Only the 8 playable characters are covered (the cutscene presets); see ``_animdb``.
"""

from __future__ import annotations

import difflib

from ._animdb import MAIN_ANIMATIONS

# preset / friendly name -> the character's anim-name TOKEN.
TOKENS = {
    "vivi": "VIV", "zidane": "ZDN",
    "garnet": "GRN", "dagger": "GRN", "princess": "GRN",
    "steiner": "STN", "freya": "FRJ", "quina": "KUI", "eiko": "EIK",
    "amarant": "SLM", "salamander": "SLM",
}
_VALID_TOKENS = set(TOKENS.values())

# Universal gestures that exist for every playable character (friendly alias -> action label). These
# are the standard field-movement clips the engine itself uses; safe on any main-character model.
CORE = {
    "idle": "IDLE", "stand": "IDLE",
    "walk": "WALK", "run": "RUN",
    "turn_left": "TURN_L", "turn_l": "TURN_L",
    "turn_right": "TURN_R", "turn_r": "TURN_R",
}


def _token(model) -> str:
    """Normalize a preset name / friendly name / raw token to a character TOKEN (e.g. 'VIV')."""
    if model is None:
        raise ValueError("no character given -- pass a preset like 'vivi' or a token like 'VIV'")
    key = str(model).strip()
    if key.upper() in _VALID_TOKENS:
        return key.upper()
    if key.lower() in TOKENS:
        return TOKENS[key.lower()]
    raise ValueError(f"unknown character {model!r}; known: "
                     f"{', '.join(sorted(set(TOKENS) | {t.lower() for t in _VALID_TOKENS}))}")


def _split(name: str):
    """(form_number, token, action_label_lower) for an anim name, or None if it isn't a MAIN anim."""
    p = name.split("_")                       # ANH MAIN F0 VIV TALK 3 1
    if len(p) < 5 or p[0] != "ANH" or p[1] != "MAIN":
        return None
    form = int(p[2][1:]) if p[2][:1] == "F" and p[2][1:].isdigit() else 99
    return form, p[3], "_".join(p[4:]).lower()


def catalog(model) -> dict:
    """``{action_label: anim_id}`` for one character, preferring the canonical F0 form when an action
    appears in more than one form (F0 is the field model)."""
    token = _token(model)
    best = {}                                  # action -> (form_number, id)
    for anim_id, name in MAIN_ANIMATIONS.items():
        s = _split(name)
        if not s or s[1] != token:
            continue
        form, _, action = s
        if action not in best or form < best[action][0]:
            best[action] = (form, anim_id)
    return {action: aid for action, (form, aid) in best.items()}


def actions(model) -> list:
    """Sorted ``[(action_label, anim_id), ...]`` for a character (for display / the CLI)."""
    return sorted(catalog(model).items())


def resolve(model, action) -> int:
    """Resolve an ``animation`` value to a numeric anim id. ``action`` may be:
      * an int (or digit string) -> passed through unchanged (a raw id, even if not in the catalog);
      * a CORE alias ('idle' / 'walk' / 'run' / 'turn_left' / 'turn_right');
      * an action label from this character's catalog (case-insensitive, '-'/space -> '_').
    Raises ValueError (with near-miss suggestions) on an unknown name."""
    if isinstance(action, bool):
        raise ValueError("animation cannot be a boolean")
    if isinstance(action, int):
        return action
    s = str(action).strip()
    if s.isdigit():
        return int(s)
    key = s.lower().replace("-", "_").replace(" ", "_")
    if key in CORE:
        key = CORE[key].lower()
    cat = catalog(model)
    if key in cat:
        return cat[key]
    hints = difflib.get_close_matches(key, cat, n=6, cutoff=0.4)
    extra = f" Did you mean: {', '.join(hints)}?" if hints else \
        f" Run `ff9mapkit animations {model}` to list gestures."
    raise ValueError(f"unknown animation {action!r} for {model!r}.{extra}")


def name_of(anim_id: int):
    """The full anim name for an id (e.g. 7302 -> 'ANH_MAIN_F0_VIV_TALK_3_1'), or None."""
    return MAIN_ANIMATIONS.get(int(anim_id))


def characters() -> list:
    """The preset/friendly character names that have a catalog (for the CLI / docs)."""
    return sorted(TOKENS)
