"""The Info Hub: a unified, read-only view over the kit's baked FF9 reference catalogs.

Where the two authoring pillars are *spatial* (Blender -> ``scene.toml``) and *logic* (the editor ->
``field.toml``), this is the *library* pillar -- the shared game-object data that lives outside any one
field: which **models**, **animations**, **items**, **battle scenes**, and **fields** the engine knows
about. It is pure-Python identifier data baked from Memoria's open-source tables (no game bytes, no
install needed); see ``docs/PROVENANCE.md``.

The headline feature is the **model -> animations** join. FF9 has no standalone "NPC" object: an NPC
is a model id + animation ids placed inline in a field. A model name ``GEO_<group>_<form>_<token>`` and
an animation name ``ANH_<group>_<form>_<token>_<action>`` share a (group, token); so a model's gestures
are the anims with the same (group, token). Verified end-to-end: model id 8 = ``GEO_MAIN_F0_VIV``, and
``animations_for_model(8)`` yields idle=148 / walk=571 / run=419 / turn_l=917 / turn_r=918 -- exactly
the kit's built-in ``vivi`` preset.

Usage::

    from ff9mapkit import catalog
    catalog.models("npc", group="NPC")          # browse townsfolk models
    m = catalog.model(8)                          # Model(id=8, name='GEO_MAIN_F0_VIV', token='VIV', ...)
    catalog.animations_for_model("GEO_NPC_F0_BAR")   # {action: anim_id} a model can play
    catalog.battle_scenes("alex")                 # encounter ids by region
    catalog.search("vivi")                        # cross-kind discovery
"""

from __future__ import annotations

import difflib
from typing import NamedTuple, Optional

from ._animdb_all import ANIMATIONS
from ._fieldtable import FBG_TO_EVT, FIELD_BY_ID
from ._itemdb import ITEMS
from ._modeldb import MODELS
from ._scenedb import SCENES
from .animations import TOKENS as _CHAR_ALIAS     # friendly playable name -> token (vivi -> VIV)

# GEO/ANH group code -> human label (the model's role).
GROUP_KIND = {
    "MAIN": "playable",
    "NPC": "npc",
    "MON": "monster",
    "ACC": "object",
    "SUB": "sub-character",
    "WEP": "weapon",
}
# form-code first letter -> the pose family the model belongs to.
FORM_KIND = {"F": "field", "B": "battle", "W": "world"}


class Model(NamedTuple):
    """One actor/field model. ``id`` is what ``SetModel()`` takes; ``token`` ties it to its anims."""
    id: int
    name: str           # GEO_<group>_<form>_<token>
    group: str          # MAIN / NPC / MON / ACC / SUB / WEP
    form: str           # F0 / B3 / W0 ...
    token: str          # VIV / BAR / EGG / 000 ...
    kind: str           # playable / npc / monster / object / sub-character / weapon
    field: bool         # True for field-form (F*) models -- the ones you place as a field NPC


def _parse_geo(name: str):
    p = name.split("_")                         # GEO ACC F0 EGG
    grp = p[1] if len(p) > 1 else ""
    form = p[2] if len(p) > 2 else ""
    token = p[3] if len(p) > 3 else ""
    return grp, form, token


def _model_info(mid: int, name: str) -> Model:
    grp, form, token = _parse_geo(name)
    return Model(mid, name, grp, form, token,
                 GROUP_KIND.get(grp, "other"), form[:1] == "F")


# ---------------------------------------------------------------- models -----
def all_models() -> list:
    """Every model as a :class:`Model`, sorted by name (so groups cluster)."""
    return [_model_info(mid, MODELS[mid]) for mid in sorted(MODELS, key=lambda i: (MODELS[i], i))]


def model(name_or_id) -> Optional[Model]:
    """Look up one model by id (int / digit-string) or exact GEO name (case-insensitive). None if
    unknown. (For a name with a typo, use :func:`resolve_model`, which suggests near-misses.)"""
    if isinstance(name_or_id, bool):
        return None
    if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.strip().isdigit()):
        mid = int(name_or_id)
        return _model_info(mid, MODELS[mid]) if mid in MODELS else None
    key = str(name_or_id).strip().upper()
    for mid, nm in MODELS.items():
        if nm.upper() == key:
            return _model_info(mid, nm)
    return None


def models(query=None, *, group=None, field_only=False) -> list:
    """Filtered model list. ``query`` = substring of the GEO name or token, OR a friendly playable name
    ('vivi'/'dagger' -> its token); ``group`` = a group code ('NPC') or kind label ('npc');
    ``field_only`` keeps field-form models (the ones you place as a field NPC)."""
    grp = (group or "").upper()
    grp_kind = (group or "").lower()
    q = (query or "").lower()
    alias = _CHAR_ALIAS.get(q)                   # 'vivi' -> 'VIV' so a friendly name finds the model
    out = []
    for m in all_models():
        if field_only and not m.field:
            continue
        if group and m.group != grp and m.kind != grp_kind:
            continue
        if q and q not in m.name.lower() and q not in m.token.lower() and not (alias and m.token == alias):
            continue
        out.append(m)
    return out


def resolve_model(name_or_id) -> int:
    """Resolve a model NAME or id to its numeric id (what ``SetModel`` wants). Raises ValueError with
    near-miss suggestions on an unknown name / out-of-table id."""
    if isinstance(name_or_id, bool):
        raise ValueError("model cannot be a boolean")
    m = model(name_or_id)
    if m:
        return m.id
    if isinstance(name_or_id, int) or str(name_or_id).strip().isdigit():
        raise ValueError(f"model id {int(name_or_id)} not in the GEO table")
    names = {nm.upper(): nm for nm in MODELS.values()}
    hints = difflib.get_close_matches(str(name_or_id).strip().upper(), list(names), n=6, cutoff=0.4)
    extra = f" Did you mean: {', '.join(names[h] for h in hints)}?" if hints else \
        " Run `ff9mapkit models` to browse them."
    raise ValueError(f"unknown model {name_or_id!r}.{extra}")


# ------------------------------------------------------------ animations -----
def animation_name(anim_id) -> Optional[str]:
    """The full anim name for an id (7302 -> 'ANH_MAIN_F0_VIV_TALK_3_1'), or None for an unknown
    or non-numeric id (honors the 'or None' contract instead of raising on e.g. a bad string)."""
    try:
        return ANIMATIONS.get(int(anim_id))
    except (TypeError, ValueError):
        return None


def _split_anh(name: str):
    """(group, form, token, action_lower) for an ``ANH_..`` name, or None."""
    p = name.split("_")                         # ANH MAIN F0 VIV TALK 3 1
    if len(p) < 5 or p[0] != "ANH":
        return None
    return p[1], p[2], p[3], "_".join(p[4:]).lower()


def _form_rank(form: str):
    """Sort key preferring field forms (F*, by number) over battle/world -- the field gesture wins."""
    if form[:1] == "F" and form[1:].isdigit():
        return (0, int(form[1:]))
    return (1, 0)


def animations_for_model(name_or_id) -> dict:
    """``{action_label: anim_id}`` -- the gestures a model can play, by the (group, token) join.

    Field forms are preferred when an action exists in more than one form (the field clip is what an
    on-field NPC uses); ties break to the smaller id. Returns ``{}`` for a model with no matching anims
    (e.g. a numbered battle-only token). Standard movement actions appear as idle/walk/run/turn_l/turn_r.
    """
    m = model(name_or_id)
    if not m or not m.token:
        return {}
    best = {}                                   # action -> (form_rank, id)
    for aid, nm in ANIMATIONS.items():
        s = _split_anh(nm)
        if not s or s[0] != m.group or s[2] != m.token:
            continue
        rank = (_form_rank(s[1]), aid)
        if s[3] not in best or rank < best[s[3]]:
            best[s[3]] = rank
    return {action: rank_id[1] for action, rank_id in best.items()}


def animation_actions(name_or_id) -> list:
    """Sorted ``[(action_label, anim_id), ...]`` for a model (for display / the CLI)."""
    return sorted(animations_for_model(name_or_id).items())


# the five field-NPC animation slots the injector drives (``content.npc.ANIM_ORDER``) and the join
# action each is resolved from. The engine plays a clip by NAME, so any id naming the right clip works.
NPC_SLOT_ACTION = {"stand": "idle", "walk": "walk", "run": "run", "left": "turn_l", "right": "turn_r"}


def npc_anims(name_or_id, *, use_catalog: bool = True) -> dict:
    """``{stand, walk, run, left, right}`` animation ids to place a model as a field NPC -- the Info
    Hub's payoff: ANY model becomes ready to drop in.

    Each movement slot the field engine drives is resolved from the model's OWN gestures
    (:func:`animations_for_model`) with graceful fallbacks (missing run -> walk, missing turn -> idle),
    so a slot never holds a foreign clip. For ``GEO_MAIN_F0_VIV`` this reproduces the built-in ``vivi``
    preset (by clip name). Returns ``{}`` for a model with no field gestures (a battle-only / effect
    model) -- give explicit ``anims`` for those.

    For a model in the baked per-model catalog (:data:`ff9mapkit._npcparams.NPC_PARAMS` -- 156 GEO_NPC/MON
    rigs), the REAL clips that rig uses as an NPC are returned verbatim (the most faithful set -- e.g. the
    moogle's exact 2904/2927/2907/2923/2911, not the by-name join's near-miss). Off-catalog models (incl.
    party GEO_MAIN, so the vivi preset stays) keep the gesture-name resolution below. ``use_catalog=False``
    forces the by-NAME gesture resolution (used by the archetype-gallery completeness guard, which asks
    "does this model auto-resolve by GESTURE NAME" -- a stricter bar than "has real clips in the catalog")."""
    if use_catalog:
        from ._npcparams import NPC_PARAMS
        try:
            mid = resolve_model(name_or_id)
        except (ValueError, TypeError):              # not a known model -> fall through to by-name (-> {})
            mid = None
        if mid is not None and mid in NPC_PARAMS:
            return dict(NPC_PARAMS[mid]["anims"])
    a = animations_for_model(name_or_id)
    if not a:
        return {}

    def pick(*actions):
        for act in actions:
            if act in a:
                return a[act]
        return None

    stand = pick("idle", "walk", "run")
    if stand is None:                            # nothing standable -> not a usable field-NPC model
        return {}
    return {
        "stand": stand,
        "walk": pick("walk", "run", "idle") or stand,
        "run": pick("run", "walk", "idle") or stand,
        "left": pick("turn_l", "turn_r", "idle") or stand,
        "right": pick("turn_r", "turn_l", "idle") or stand,
    }


# ----------------------------------------------------------- battle scenes ---
def battle_scenes(query=None) -> list:
    """``[(name, id), ...]`` sorted by name; ``query`` filters by name substring (case-insensitive)."""
    q = (query or "").lower()
    return sorted((nm, sid) for nm, sid in SCENES.items() if not q or q in nm.lower())


def resolve_scene(name_or_id) -> int:
    """Resolve a battle-scene NAME (BSC_..) or id to its numeric encounter id. A raw id passes through
    unchanged (the table isn't exhaustive of every valid id). Raises ValueError on an unknown name."""
    if isinstance(name_or_id, bool):
        raise ValueError("scene cannot be a boolean")
    if isinstance(name_or_id, int) or str(name_or_id).strip().isdigit():
        return int(name_or_id)
    key = str(name_or_id).strip().upper()
    by_name = {nm.upper(): sid for nm, sid in SCENES.items()}
    if key in by_name:
        return by_name[key]
    hints = difflib.get_close_matches(key, list(by_name), n=6, cutoff=0.4)
    extra = f" Did you mean: {', '.join(hints)}?" if hints else " Run `ff9mapkit scenes` to browse them."
    raise ValueError(f"unknown battle scene {name_or_id!r}.{extra}")


# -------------------------------------------------- items / fields (thin) ----
def items(query=None) -> list:
    """``[(id, name), ...]`` (excludes the NoItem sentinel); ``query`` filters by name substring."""
    q = (query or "").lower()
    return sorted((i, n) for i, n in ITEMS.items() if n != "NoItem" and (not q or q in n.lower()))


def fields(query=None) -> list:
    """``[(fbg_folder, field_id, evt_name), ...]`` for EVERY field (id-keyed, so the ~142 fields that SHARE a
    background folder with another -- the same room at a different story beat -- BOTH appear, each with its own
    event); ``query`` filters by fbg/evt substring."""
    q = (query or "").lower()
    out = [(fbg, fid, evt) for fid, (fbg, evt) in FIELD_BY_ID.items()
           if not q or q in fbg.lower() or q in evt.lower()]
    return sorted(out, key=lambda r: (r[0], r[1]))


# ----------------------------------------------------------- cross-kind ------
def search(query: str) -> dict:
    """Discovery across every catalog: ``{'models': [...], 'items': [...], 'scenes': [...],
    'fields': [...]}`` matching ``query`` (substring). The Info Hub's "grab anything by name"."""
    return {
        "models": models(query),
        "items": items(query),
        "scenes": battle_scenes(query),
        "fields": fields(query),
    }
