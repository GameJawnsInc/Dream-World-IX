"""Named NPC archetypes -- the Info Hub's "place a common NPC with one word".

A thin curated layer over the model->animation auto-resolution (:func:`catalog.npc_anims`): a friendly
name (``"garnet"``, ``"black_mage"``, ``"moogle"``) maps to a model whose gestures auto-resolve. Use it
as ``[[npc]] archetype = "garnet"`` (``preset`` is an accepted alias). For anything not curated here,
name the model directly: ``[[npc]] model = "GEO_NPC_F0_BAR"`` (browse with ``ff9mapkit models``).

Provenance-clean: only references Memoria model IDENTIFIERS (GEO names), never game bytes. The curated
set is intentionally small + high-confidence (the playable cast, plus NPC types confirmed in-game) and
grows as more models are identified -- a wrong name is worse than none.
"""
from __future__ import annotations

from . import catalog as _catalog
from .content.npc import PRESETS as _CHAR_PRESETS   # vivi / zidane: explicit anims, byte-golden

# friendly name -> a curated spec. ``model`` is a GEO name (resolved via the catalog); the model's
# gestures auto-resolve unless ``anims`` is given; ``animset`` (head height) + ``dialogue`` (a default
# line) are optional. vivi/zidane are NOT here -- they come from _CHAR_PRESETS (explicit, byte-golden).
ARCHETYPES: dict = {
    # -- the playable cast: place any party member as a field NPC --
    "garnet": {"model": "GEO_MAIN_F0_GRN"},
    "dagger": {"model": "GEO_MAIN_F0_GRN"},        # alias for garnet
    "steiner": {"model": "GEO_MAIN_F0_STN"},
    "freya": {"model": "GEO_MAIN_F0_FRJ"},
    "quina": {"model": "GEO_MAIN_F0_KUI"},
    "eiko": {"model": "GEO_MAIN_F0_EIK"},
    "amarant": {"model": "GEO_MAIN_F0_SLM"},
    # -- common NPC types (grow this as models are confirmed in-game) --
    "black_mage": {"model": "GEO_NPC_F0_BMG"},     # verified in-game
    "moogle": {"model": "GEO_NPC_F0_MOG"},         # the FF moogle code
    # -- identified via the in-game gallery (token -> what the model actually is) --
    "townswoman": {"model": "GEO_NPC_F0_APF"},       # APF "Adult Person Female"
    "woman": {"model": "GEO_NPC_F0_APF"},            # alias of townswoman
    "townsman": {"model": "GEO_NPC_F0_APM"},         # APM "Adult Person Male"
    "man": {"model": "GEO_NPC_F0_APM"},              # alias of townsman
    "bartender": {"model": "GEO_NPC_F0_BAR"},        # BAR
    "old_woman": {"model": "GEO_NPC_F0_BBA"},        # BBA (JP "baba" = granny)
    "granny": {"model": "GEO_NPC_F0_BBA"},           # alias of old_woman
    "oglop": {"model": "GEO_NPC_F0_BRI"},            # BRI (JP "burimushi" = the Oglop bug)
    "burmecian_child": {"model": "GEO_NPC_F0_BUC"},  # BUC
    "burmecian_woman": {"model": "GEO_NPC_F0_BUF"},  # BUF
    "cat": {"model": "GEO_NPC_F0_CAT"},              # CAT
    "bird": {"model": "GEO_NPC_F0_CCB"},             # CCB (pigeon-ish)
    "chocobo_child": {"model": "GEO_NPC_F0_CHC"},    # CHC (tentative -- a Black Mage Vil. chocobo)
    "fat_chocobo": {"model": "GEO_NPC_F0_CHD"},      # CHD (JP "Choco Debu")
    "chocobo": {"model": "GEO_NPC_F0_CHO"},          # CHO (the common field chocobo)
    "high_priest": {"model": "GEO_NPC_F0_CLD"},      # CLD (Cleyra Cathedral, JP "Daikanshu")
    "cleyran_woman": {"model": "GEO_NPC_F0_CLM"},    # CLM
    "cook": {"model": "GEO_NPC_F0_COK"},             # COK
    "engineer": {"model": "GEO_NPC_F0_CSA"},         # CSA (Lindblum engineer, e.g. Zebolt)
    "zebolt": {"model": "GEO_NPC_F0_CSA"},           # alias (the named Lindblum engineer)
    "lindblum_man": {"model": "GEO_NPC_F0_CSM"},     # CSM
    "guard": {"model": "GEO_NPC_F0_CSO"},            # CSO (armed Lindblum guard/soldier)
    "soldier": {"model": "GEO_NPC_F0_CSO"},          # alias of guard
    "dali_boy": {"model": "GEO_NPC_F0_DAC"},         # DAC (Dali male child)
    "dali_girl": {"model": "GEO_NPC_F0_DAF"},        # DAF (Dali female child)
    "dali_man": {"model": "GEO_NPC_F0_DAL"},         # DAL (Dali male citizen)
    "dali_woman": {"model": "GEO_NPC_F0_DAW"},       # DAW (Dali female citizen/worker)
    "dwarf": {"model": "GEO_NPC_F0_DOC"},            # DOC (Conde Petie -- "Rally-ho!")
    "dwarf_woman": {"model": "GEO_NPC_F0_DOF"},      # DOF
    "dog": {"model": "GEO_NPC_F0_DOG"},              # DOG (a literal dog)
    "dwarf_priest": {"model": "GEO_NPC_F0_DOK"},     # DOK (JP "Okashira" = chief/leader)
    "dwarf_man": {"model": "GEO_NPC_F0_DOM"},        # DOM
    "sand_oracle": {"model": "GEO_NPC_F0_FLS"},      # FLS (Cleyra's priestesses)
    "frog": {"model": "GEO_NPC_F0_FRM"},             # FRM (the catchable marsh frog)
    "burmecian_king": {"model": "GEO_NPC_F0_FUK"},   # FUK (dev humor: FUkkatsu = "Revival/Ruined" King)
    "noble": {"model": "GEO_NPC_F0_G16"},            # G16 (G = Gentleman; Treno/Lindblum noble)
    "gentleman": {"model": "GEO_NPC_F0_G16"},        # alias of noble
}


def names() -> list:
    """Every archetype name (playable presets + curated NPC types), sorted."""
    return sorted(set(_CHAR_PRESETS) | set(ARCHETYPES))


def is_archetype(name) -> bool:
    """True if ``name`` is a known archetype (case-insensitive)."""
    key = str(name).strip().lower()
    return key in _CHAR_PRESETS or key in ARCHETYPES


def resolve(name):
    """``(model_id|None, animset|None, anims|None, default_dialogue|None)`` for an archetype name.

    ``vivi``/``zidane`` resolve to their byte-golden character preset (explicit anims; zidane keeps the
    cloned player's model). Every other archetype resolves its model (GEO name -> id) and auto-resolves
    the model's gestures via :func:`catalog.npc_anims`. Raises ValueError (listing the known names) on an
    unknown one. Feeding this to ``inject_npc(model=, animset=, anims=)`` reproduces the old
    ``inject_npc(preset="vivi")`` byte-for-byte, so existing builds are unaffected.
    """
    key = str(name).strip().lower()
    if key in _CHAR_PRESETS:
        model, animset, anims = _CHAR_PRESETS[key]
        return model, animset, anims, None
    if key in ARCHETYPES:
        spec = ARCHETYPES[key]
        model = _catalog.resolve_model(spec["model"])
        anims = spec.get("anims") or _catalog.npc_anims(model) or None
        return model, spec.get("animset"), anims, spec.get("dialogue")
    raise ValueError(f"unknown archetype {name!r}. Known: {', '.join(names())}. "
                     f"Or name a model directly with model = \"GEO_...\" (see `ff9mapkit models`).")
