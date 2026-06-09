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
    # -- identified via the in-game prop gallery (token -> what it is, JP/decode in the note) --
    "balloon": {"model": "GEO_ACC_F0_BLL", "pose": 3349},       # BLL -- "BaLLoon": the moogle save-point marker
    "save_marker": {"model": "GEO_ACC_F0_BLL", "pose": 3349},   # alias of balloon
    "letter": {"model": "GEO_ACC_F0_LTT", "pose": 2479},        # LTT -- a Mognet "LeTTer"
    "cactus": {"model": "GEO_ACC_F0_GAS", "pose": 8186},        # GAS -- a Gargan cactus (JP "GArgantua" + "Saboten" = cactus)
    "save_the_queen": {"model": "GEO_ACC_F0_STQ", "pose": 1894},  # STQ -- "Save The Queen" (Beatrix's sword) as a prop
    "sword": {"model": "GEO_ACC_F0_SWD", "pose": 4470},         # SWD -- a "SWorD" (the theatrical replica from "I Want to Be Your Canary")
    "cask": {"model": "GEO_ACC_F0_CSK", "pose": 1904},          # CSK -- a "CaSK" / barrel (Dali storage, Lindblum alleys)
    "barrel": {"model": "GEO_ACC_F0_CSK", "pose": 1904},        # alias of cask
    "great_leaf": {"model": "GEO_ACC_F0_ELE", "pose": 1894},    # ELE -- Cleyra's Great Leaf / the leaf elevator pad (Iifa roots, Cleyra climbs)
    "fish": {"model": "GEO_ACC_F0_FS1", "pose": 10751},         # FS1 -- "FiSh 1", the orange fish kitchen prop (Madain Sari, Memoria)
    "hand_bell": {"model": "GEO_ACC_F0_HDB", "pose": 2471},     # HDB -- "HanD Bell": the small Burmecian hand bell (not Gizamaluke's giant one)
    "lever": {"model": "GEO_ACC_F0_KOM", "pose": 301},          # KOM -- a small switch/toggle lever (JP Komon/Komadori; Fossil Roo track switches)
    "switch_lever": {"model": "GEO_ACC_F0_KOM", "pose": 301},   # alias of lever
    "ladder": {"model": "GEO_ACC_F0_LDD", "pose": 758},         # LDD -- a "LaDDer" (Vivi's, the Alexandria rooftops)
    "book": {"model": "GEO_ACC_F0_OPB", "pose": 1892},          # OPB -- a library book (default closed; "OPen Book" -- opens via animation)
    "pickaxe": {"model": "GEO_ACC_F0_TUR", "pose": 10643},      # TUR -- a mining pickaxe (Fossil Roo mining site)
    "vat": {"model": "GEO_ACC_F0_BBT", "pose": 62},             # BBT -- "Big Barrel Tank": a huge storage vat (Dali underground production)
    "tank": {"model": "GEO_ACC_F0_BBT", "pose": 62},            # alias of vat
    "aircab": {"model": "GEO_ACC_F0_V10", "pose": 1608},        # V10 -- "Vehicle 10": the Lindblum aircab car (flies, has doors)
    "aircab_car": {"model": "GEO_ACC_F0_V10", "pose": 1608},    # alias of aircab
    "trap": {"model": "GEO_ACC_F0_ISB", "pose": 10689},         # ISB -- a static ancient-ruins trap mechanism (Ipsen's Castle / Pinnacle Rocks / Earth Shrine). TENTATIVE -- couldn't get a clear look
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
