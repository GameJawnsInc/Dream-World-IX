"""Named PROP archetypes -- the Info Hub's "place a common set piece with one word".

A friendly name (``"chest"``, ``"tent"``, ``"save_book"``) maps to a GEO prop model + its canonical
resting **pose** -- the ``SetStandAnimation`` id shipping fields settle that model to, harvested by
``tools/extract_prop_poses.py``. A prop's true pose usually ISN'T a named model animation (the save
book rests at clip 1872 = its 'b'+1), so the pose is a curated number here, not a name-join lookup.

Use as ``[[prop]] prop = "chest"``. For anything not curated, place it directly with
``[[prop]] model = "GEO_ACC_F0_XXX"`` + an optional ``pose`` (an action name or a raw clip id).

Provenance-clean: only GEO model IDENTIFIERS + animation IDs (numbers), never game bytes. The set is
intentionally small + high-confidence and grows as ACC props are identified in-game (a wrong name/pose
is worse than none).
"""
from __future__ import annotations

from . import catalog as _catalog

# friendly name -> {model: GEO name, pose: canonical SetStandAnimation id (from extract_prop_poses)}.
PROP_ARCHETYPES: dict = {
    "chest": {"model": "GEO_ACC_F0_TBX", "pose": 7339},        # TBX -- a closed treasure chest ('close')
    "treasure_chest": {"model": "GEO_ACC_F0_TBX", "pose": 7339},  # alias of chest
    "tent": {"model": "GEO_ACC_F0_TNT", "pose": 7667},          # TNT -- a world-map camping tent ('camp_sleep')
    "save_book": {"model": "GEO_ACC_F0_MGR", "pose": 1872},     # MGR -- the moogle's save book (raw pose 1872)
    "feather": {"model": "GEO_ACC_F0_MGP", "pose": 1874},       # MGP -- the save-point feather / quill (raw 1874)
}


def names() -> list:
    """Every prop-archetype name, sorted."""
    return sorted(PROP_ARCHETYPES)


def is_prop_archetype(name) -> bool:
    """True if ``name`` is a known prop archetype (case-insensitive)."""
    return str(name).strip().lower() in PROP_ARCHETYPES


def resolve(name):
    """``(model_id, pose_id)`` for a prop-archetype name. Raises ValueError (listing the known names) on
    an unknown one."""
    key = str(name).strip().lower()
    if key not in PROP_ARCHETYPES:
        raise ValueError(f"unknown prop archetype {name!r}. Known: {', '.join(names())}. "
                         f"Or place a model directly with model = \"GEO_ACC_F0_...\" (see `ff9mapkit models`).")
    spec = PROP_ARCHETYPES[key]
    return _catalog.resolve_model(spec["model"]), int(spec["pose"])
