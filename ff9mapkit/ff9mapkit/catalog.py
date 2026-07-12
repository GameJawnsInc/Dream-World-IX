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
from .models.appearance import Appearance, NO_APPEARANCE, appearance_of  # story-forms / name-keyed gate census

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
    appearance: Appearance = NO_APPEARANCE   # story forms + name-keyed engine gate (NO_APPEARANCE if plain)


def _parse_geo(name: str):
    p = name.split("_")                         # GEO ACC F0 EGG
    grp = p[1] if len(p) > 1 else ""
    form = p[2] if len(p) > 2 else ""
    token = p[3] if len(p) > 3 else ""
    return grp, form, token


def _model_info(mid: int, name: str) -> Model:
    grp, form, token = _parse_geo(name)
    return Model(mid, name, grp, form, token,
                 GROUP_KIND.get(grp, "other"), form[:1] == "F", appearance_of(name))


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


# --------------------------------------- where a clip lives on disc (the engine folder redirect) -----
# A clip's p0data5 folder is derived from the anim NAME, not from the model playing it (Memoria
# ``AnimationFactory.GetRenameAnimationPath`` -> ``GetRenameAnimationDirectory``): the name's model tokens
# ``ANH_<group>_<form>_<token>_*`` name the folder-OWNING model ``GEO_<group>_<form>_<token>``, and that
# model's id is the ``Animations/<id>/`` folder -- with two hardcoded exceptions for token-models that are
# not in the GEO table at all. So ``GEO_NPC_F1_BBA`` (10) plays its catalog idle=560 (``ANH_NPC_F0_BBA_IDLE``)
# out of the DONOR folder ``Animations/112/`` (``GEO_NPC_F0_BBA``'s); the engine binds clips by bone NAME, so
# a same-rig-family donor clip plays cleanly. (The engine's ``animationPathTable`` is NOT part of this: its
# only lookup sits behind an ``animationMapping.ContainsKey`` guard that is provably empty whenever
# ``GetAnimationFolder`` runs -- ``LoadAnimationUseInEvent`` clears the mapping before the loop and fills it
# after -- so the live redirect is name-tokens -> GEO id, which is what we replicate.)
#
# AnimationDB also carries ~4.7k DUPLICATE rows (two ids sharing one ANH name). The engine loads clips by
# NAME (``AnimationDB.TryGetKey`` -> one canonical id) and only that sibling exists on disc -- e.g. the world
# Zidane's catalog idle1=4715 vs the on-disc 4716, or BBA's b=8900 vs the on-disc 9363. So resolving a
# requested id must fall through its same-name siblings (:func:`animation_aliases`) before giving up.

_ANIM_FOLDER_SPECIAL = {"GEO_MON_B3_110": 347, "GEO_MON_B3_109": 5461}   # GetRenameAnimationDirectory hardcodes
_MODEL_ID_BY_NAME: dict = {}                # lazy GEO name -> id (the engine's FF9BattleDB.GEO.TryGetKey)
_ANIM_IDS_BY_NAME: dict = {}                # lazy ANH name -> sorted [ids] (the duplicate-row sibling index)


def _model_id_by_name(name: str) -> Optional[int]:
    if not _MODEL_ID_BY_NAME:
        _MODEL_ID_BY_NAME.update({nm: mid for mid, nm in MODELS.items()})
    return _MODEL_ID_BY_NAME.get(name)


def animation_aliases(anim_id) -> list:
    """Every AnimationDB id sharing this id's ANH name -- itself first, then its duplicate-row siblings
    ascending (``animation_aliases(8900) -> [8900, 9363]``, both ``ANH_NPC_F0_BBA_B``). An id the table
    doesn't know returns ``[id]`` (a minted/custom key is its own only candidate); a non-numeric id ``[]``."""
    try:
        aid = int(anim_id)
    except (TypeError, ValueError):
        return []
    nm = ANIMATIONS.get(aid)
    if nm is None:
        return [aid]
    if not _ANIM_IDS_BY_NAME:
        by: dict = {}
        for k, v in ANIMATIONS.items():
            by.setdefault(v, []).append(k)
        for ids in by.values():
            ids.sort()
        _ANIM_IDS_BY_NAME.update(by)
    return [aid] + [k for k in _ANIM_IDS_BY_NAME.get(nm, ()) if k != aid]


def animation_folder(anim_id) -> Optional[int]:
    """The model id whose ``Animations/<id>/`` folder the ENGINE loads this clip from -- the anim name's
    token-derived owner (``animation_folder(560) -> 112``: ``ANH_NPC_F0_BBA_IDLE`` belongs to
    ``GEO_NPC_F0_BBA``), honoring the two hardcoded monster exceptions (``MON_B3_110 -> 347``,
    ``MON_B3_109 -> 5461``). None for an unknown id, a non-``ANH_`` name, or a token-model the GEO table
    lacks (the engine's by-name load would miss those too)."""
    nm = animation_name(anim_id)
    s = _split_anh(nm) if nm else None
    if not s:
        return None
    owner = f"GEO_{s[0]}_{s[1]}_{s[2]}"
    if owner in _ANIM_FOLDER_SPECIAL:
        return _ANIM_FOLDER_SPECIAL[owner]
    return _model_id_by_name(owner)


def locate_animation(anim_id, model_id, disc) -> Optional[tuple]:
    """Where a requested clip PHYSICALLY exists for ``model_id`` -> ``(anim_key, folder_id)``, or None.

    ``disc`` maps ``{folder_id: iterable-of-anim-keys}`` (the caller's scan of p0data5 --
    ``models._gltf_io.anim_disc_map`` -- or any offline stand-in). Engine-faithful resolution order, per
    same-name candidate (:func:`animation_aliases`, requested id first):

    1. the model's OWN id folder -- ``AddAnimToGameObject(addAutoAnim)`` bulk-loads it regardless of what
       the clip is named (BBA's two native clips are F0-named yet live in her ``Animations/10/``);
    2. the name-token DONOR folder (:func:`animation_folder`, i.e. ``GetRenameAnimationDirectory``).

    So a phantom duplicate id resolves to its on-disc sibling (8900 -> (9363, 112)), and a donor-folder
    action resolves to the folder the engine actually reads (560 -> (560, 112) for model 10)."""
    try:
        own = int(model_id) if model_id is not None else None
    except (TypeError, ValueError):
        own = None
    for cand in animation_aliases(anim_id):
        if own is not None and cand in (disc.get(own) or ()):
            return cand, own
        folder = animation_folder(cand)
        if folder is not None and folder != own and cand in (disc.get(folder) or ()):
            return cand, folder
    return None


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
    rigs), the REAL clips real standing NPCs use are preferred -- but every resolved id MUST be one of the
    model's OWN clips: a clip whose name joins the model's (group, token) -- any form, so Stiltzkin's
    F3-MOG rig keeps its real F3 clips -- given as that name's CANONICAL row (its lowest id, the one the
    ``ff9mapkit models <name>`` list and the kit's proven presets use). A baked id that is a same-name
    DUPLICATE row (the ~4.7k two-ids-one-name AnimationDB rows above) is canonicalized --
    ``GEO_NPC_F0_TMM``'s modal stand 706 -> its own idle 654: the duplicate id left the NPC
    unposed/INVISIBLE on a synthesized field (in-game 2026-07-12) even though both ids name the same
    clip. A baked slot naming a truly FOREIGN token's clip falls back to the gesture-name resolution; a
    model with no own movement gestures at all keeps its baked real-NPC clips verbatim (real observed
    values beat nothing -- the frog rigs FRC/FRF only ever played FRM clips). Off-catalog models (incl.
    party GEO_MAIN, so the vivi preset stays) use the gesture-name resolution directly.
    ``use_catalog=False`` forces the by-NAME gesture resolution (used by the archetype-gallery
    completeness guard, which asks "does this model auto-resolve by GESTURE NAME" -- a stricter bar than
    "has real clips in the catalog")."""
    a = animations_for_model(name_or_id)

    def pick(*actions):
        for act in actions:
            if act in a:
                return a[act]
        return None

    byname = {}
    stand = pick("idle", "walk", "run")
    if stand is not None:                        # nothing standable -> not a by-name-usable field-NPC model
        byname = {
            "stand": stand,
            "walk": pick("walk", "run", "idle") or stand,
            "run": pick("run", "walk", "idle") or stand,
            "left": pick("turn_l", "turn_r", "idle") or stand,
            "right": pick("turn_r", "turn_l", "idle") or stand,
        }
    if not use_catalog:
        return byname
    from ._npcparams import NPC_PARAMS
    try:
        mid = resolve_model(name_or_id)
    except (ValueError, TypeError):              # not a known model -> the by-name result (-> {})
        mid = None
    if mid is None or mid not in NPC_PARAMS:
        return byname
    m = model(mid)
    out = {}
    for slot, baked in NPC_PARAMS[mid]["anims"].items():
        nm = animation_name(baked)
        s = _split_anh(nm) if nm else None
        if s and s[0] == m.group and s[2] == m.token:
            out[slot] = min(animation_aliases(baked))    # the model's own clip -> its canonical row
        else:
            out[slot] = byname.get(slot, baked)          # foreign token -> the model's own gesture (or keep)
    return out


# ------------------------------------------------------------- world models --
# A world-form (``GEO_SUB_W0_*``) model is an OVERWORLD actor. The overworld places it via the SAME path as a
# field NPC -- ``ModelFactory.CreateModel`` in the event engine's ``gMode == 3`` branch -- and attaches its
# clips via the disc-probed ``AnimationFactory`` (the ``SetStand/Walk/Run`` opcodes are not gMode-gated). So a
# reskin (loose FBX) AND an ``.anim`` edit are BOTH DLL-free here, exactly like a field model. THE ONE
# EXCEPTION is the hardcoded Bee / Chocobo-minigame scene (``WMActor.Initialize`` adds bundled ``WMAnimationBank``
# clips) -- there an ``.anim`` override won't show (the mesh reskin still does).
# AUTHORITATIVE overworld-character map -- transcribed from ``WMAnimationBank.cs`` (the engine names these six
# by their clip fields, e.g. ``ZidaneIdleClip = ANH_SUB_W0_001_STAND``). The other ``GEO_SUB_W0_*`` are more
# walker/vehicle chibis the world ``.eb`` SetModels; the engine doesn't name them, so we DON'T fabricate an
# identity for them (``world_role`` gives a coarse role instead). NOTE ``W0_001`` is Zidane, not the chocobo --
# his model carries the chocobo-RIDING clips (``_CHO``: the rider's mounted animations live on the rider); the
# actual chocobo is ``W0_003``.
WORLD_MODEL_CHARACTER = {
    "GEO_SUB_W0_001": "Zidane",
    "GEO_SUB_W0_002": "Dagger (Garnet)",
    "GEO_SUB_W0_003": "Chocobo",
    "GEO_SUB_W0_008": "Blue Narciss",
    "GEO_SUB_W0_009": "Hilda Garde 3",
    "GEO_SUB_W0_010": "Invincible",
}


def world_character(name_or_id) -> str:
    """The overworld character a world-form model IS, when the engine NAMES it (``WMAnimationBank.cs``) -- e.g.
    ``'Zidane'`` for ``GEO_SUB_W0_001``. ``''`` for an unnamed world chibi (or a non-world model): authoritative,
    never guessed. Pair with :func:`world_role` for the coarse role of the unnamed ones."""
    m = model(name_or_id)
    return WORLD_MODEL_CHARACTER.get(m.name, "") if m else ""


def world_role(name_or_id) -> str:
    """A coarse role for a world-form (W*) model, inferred from its clip vocabulary: ``'vehicle'`` (airship/ship
    -- has a TAKEOFF/ROCKET clip) / ``'walker'`` (a character chibi -- has plain run/stand/idle) / ``'chocobo'``
    (only ``_CHO`` mounted clips, no on-foot walk) / ``''``. Offline; a discovery aid, NOT an identity claim --
    use :func:`world_character` for the authoritative name. (Order matters: a rider like Zidane has BOTH on-foot
    AND ``_CHO`` clips, so 'walker' must win over 'chocobo'; and 'fly' can't gate 'vehicle' -- it substrings
    ``fly_cho`` on the rider -- so 'takeoff' does.)"""
    m = model(name_or_id)
    if not m or m.form[:1] != "W":
        return ""
    labels = set(animations_for_model(m.id))
    if "run" in labels or "walk" in labels:               # PLAIN on-foot locomotion -> a character chibi
        return "walker"                                   # (a rider like Zidane also carries _CHO mount clips)
    if any("cho" in a for a in labels):                   # only mounted _CHO clips, no on-foot walk -> chocobo
        return "chocobo"
    if any("takeoff" in a or "rocket" in a for a in labels):
        return "vehicle"                                  # airship / ship (Blue Narciss, Hilda Garde, Invincible)
    if labels & {"stand", "idle", "idle1"}:               # only stand/idle -> still a character (no run clip)
        return "walker"
    return ""


# ----------------------------------------------------------- battle scenes ---
def _is_model_bucket(name) -> bool:
    """A ``BSC_B3_*`` name is the MODEL bucket (176 entries) -- a model holder, NOT a fightable encounter.
    Picking one as a field's random-battle scene crashes in-game (``InitBattleScene`` null-ref; see the
    ``scene_name`` note + ``eb/opcodes.py``). The two scene namespaces are disjoint (this published BSC_ table
    vs the install's region-coded loadable set), so there's no install cross-ref -- this name rule IS the guard."""
    return bool(name) and str(name).upper().startswith("BSC_B3_")


def battle_scenes(query=None, *, include_model_bucket=False) -> list:
    """``[(name, id), ...]`` sorted by name; ``query`` filters by name substring (case-insensitive). The
    ``BSC_B3_*`` MODEL bucket (176 non-fightable model holders that crash as an encounter) is EXCLUDED by
    default -- it's not a pickable encounter; pass ``include_model_bucket=True`` for the raw table."""
    q = (query or "").lower()
    return sorted((nm, sid) for nm, sid in SCENES.items()
                  if (include_model_bucket or not _is_model_bucket(nm)) and (not q or q in nm.lower()))


def is_model_bucket_scene(scene_id) -> bool:
    """True if an encounter id resolves to a ``BSC_B3_*`` model-bucket name (not fightable) -- the build/Check
    lint uses this to flag a hand-authored or mis-picked ``[encounter] scene``."""
    return _is_model_bucket(scene_name(scene_id))


_SCENE_BY_ID = None


def scene_name(scene_id) -> "str | None":
    """The published BSC_ name for an encounter id, or None if the id isn't in the table (the table is the
    full published name<->id map, NOT a guarantee the scene's DATA loads -- e.g. the BSC_B3_* model bucket)."""
    global _SCENE_BY_ID
    if _SCENE_BY_ID is None:
        _SCENE_BY_ID = {}
        for nm, sid in SCENES.items():
            _SCENE_BY_ID.setdefault(sid, nm)        # first name wins if an id has aliases
    return _SCENE_BY_ID.get(int(scene_id))


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
