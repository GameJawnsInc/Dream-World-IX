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
    # -- main-character alt-forms (a specific scripted version of a hero) --
    "zidane_npc": {"model": "GEO_MAIN_F0_ZDN"},          # ZDN -- Zidane's own field model placed as an NPC (vs "zidane" = the cloned player)
    "steiner_carrying_dagger": {"model": "GEO_MAIN_F0_STD"},  # STD -- "STeiner + Dagger": Steiner carrying Princess Garnet (Evil Forest)
    "zidane_carrying_dagger": {"model": "GEO_MAIN_F0_ZDD"},   # ZDD -- "ZiDane + Dagger": Zidane carrying Princess Garnet
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
    "noblewoman": {"model": "GEO_NPC_F0_G17"},       # G17 (female noble)
    "noble_man": {"model": "GEO_NPC_F0_G18"},        # G18 (another male-noble variant)
    "queen_stella": {"model": "GEO_NPC_F0_G19"},     # G19 (the Treno noble Queen Stella)
    "stella": {"model": "GEO_NPC_F0_G19"},           # alias of queen_stella
    "aristocrat": {"model": "GEO_NPC_F0_G20"},       # G20 (another male-noble variant)
    "tour_guide": {"model": "GEO_NPC_F0_GUD"},       # GUD (Alexandria tour guide)
    "commoner": {"model": "GEO_NPC_F0_HEK"},         # HEK (JP "Heikin" = average/commoner)
    "bandit": {"model": "GEO_NPC_F0_HTH"},           # HTH (JP "Heikin Thief")
    "thief": {"model": "GEO_NPC_F0_HTH"},            # alias of bandit
    "fan_club_member": {"model": "GEO_NPC_F0_HUF"},  # HUF (Lowell's fan club, a woman)
    "human_male": {"model": "GEO_NPC_F0_HUM"},       # HUM (a generic adult man)
    "old_man": {"model": "GEO_NPC_F0_JJY"},          # JJY (JP "jijii" = old man)
    "grandpa": {"model": "GEO_NPC_F0_JJY"},          # alias of old_man
    "alexandria_child": {"model": "GEO_NPC_F0_KAC"}, # KAC (Alexandria kid, e.g. Hippaul)
    "hippaul": {"model": "GEO_NPC_F0_KAC"},          # alias (the named Alexandria boy)
    "bishop": {"model": "GEO_NPC_F0_NAN"},           # NAN (Esto Gaza altar)
    "alexandria_soldier": {"model": "GEO_NPC_F0_OFF"},  # OFF (Alexandria's female soldiers)
    "auctioneer": {"model": "GEO_NPC_F0_ORC"},       # ORC (Treno Auction House)
    "scholar": {"model": "GEO_NPC_F0_OSC"},          # OSC (A. Castle Library)
    "burmecian_soldier": {"model": "GEO_NPC_F0_RAS"},  # RAS (Gizamaluke bell guards)
    "red_mage_woman": {"model": "GEO_NPC_F0_RMF"},   # RMF (Red Mage, Female)
    "red_mage_man": {"model": "GEO_NPC_F0_RMM"},     # RMM (Red Mage, Male)
    "red_mage": {"model": "GEO_NPC_F0_RMM"},         # alias of red_mage_man
    "puck": {"model": "GEO_NPC_F0_RTC"},             # RTC ("Rat Child" -- the Burmecian boy-thief Zidane befriends)
    "lowell": {"model": "GEO_NPC_F0_STR"},           # STR ("star" -- the famous actor; HUF = his fan club)
    "theater_star": {"model": "GEO_NPC_F0_STR"},     # alias of lowell
    "tadpole": {"model": "GEO_NPC_F0_TAD"},          # TAD (Qu's Marsh)
    "little_boy": {"model": "GEO_NPC_F0_TBY"},       # TBY ("Tag Boy" -- Alexandria kid, plays tag with TGR)
    "boy": {"model": "GEO_NPC_F0_TBY"},              # alias of little_boy
    "ticket_master": {"model": "GEO_NPC_F0_TCK"},    # TCK ("ticket" -- Alexandria play ticketmaster)
    "ticketmaster": {"model": "GEO_NPC_F0_TCK"},     # alias of ticket_master
    "little_girl": {"model": "GEO_NPC_F0_TGR"},      # TGR ("Tag Girl" -- Alexandria kid, chases TBY)
    "girl": {"model": "GEO_NPC_F0_TGR"},             # alias of little_girl
    "conductor": {"model": "GEO_NPC_F0_BND"},        # BND ("band" -- the Prima Vista's conductor)
    "band_member": {"model": "GEO_NPC_F0_BND"},      # alias of conductor (a Tantalus musician)
    "alexandria_woman": {"model": "GEO_NPC_F0_TMF"}, # TMF (an Alexandria townswoman -- e.g. Hippaul's mother)
    "hippauls_mom": {"model": "GEO_NPC_F0_TMF"},     # alias (the named Alexandria mother)
    "innkeeper": {"model": "GEO_NPC_F0_TMM"},        # TMM (Alexandria townsman / the inn keeper, "Fish Man")
    "fish_man": {"model": "GEO_NPC_F0_TMM"},         # alias of innkeeper (the named Alexandria man)
    "servant": {"model": "GEO_NPC_F0_TRF"},          # TRF (a noble's servant -- e.g. Queen Stella's, in Treno)
    "stellas_servant": {"model": "GEO_NPC_F0_TRF"},  # alias of servant
    "worker": {"model": "GEO_NPC_F0_WRK"},           # WRK ("worker" -- a laborer, e.g. Dante the Alexandria signmaker)
    "signmaker": {"model": "GEO_NPC_F0_WRK"},        # alias of worker
    "dante": {"model": "GEO_NPC_F0_WRK"},            # alias (the named Alexandria signmaker)
    # -- SUB group: the named story cast (a unique character; same model->anim auto-resolve as an NPC) --
    "hilda": {"model": "GEO_SUB_F0_CDW"},            # CDW -- Cid's Wife (Hilda); seen kidnapped, Lindblum Castle
    "quale": {"model": "GEO_SUB_F0_KUT"},            # KUT -- Quina's master, in Qu's Marsh (KU = Qu Tribe romaji ク族 + T = Teacher/Top = Master)
    "qu_master": {"model": "GEO_SUB_F0_KUT"},        # alias of quale
    "quan": {"model": "GEO_SUB_F0_KUW"},             # KUW -- Vivi's grandfather, Quan's Dwelling (KU = Qu Tribe + W = elder/grandpa suffix, JP おじいさん)
    "garnets_mother": {"model": "GEO_SUB_F0_MOM"},   # MOM ("mother") -- the woman in Garnet's Memoria recollection (likely her birth mother; user: "Jane"). TENTATIVE
    "genome": {"model": "GEO_SUB_F0_NTC"},           # NTC -- a genome; the roaming Terra one (normal stand/walk, best as a general placeable)
    "genome_2": {"model": "GEO_SUB_F0_NTA"},         # NTA -- a Bran Bal genome (distinct idle posture; some are seated)
    "genome_3": {"model": "GEO_SUB_F0_NTB"},         # NTB -- a Bran Bal genome (distinct idle posture)
    "genome_4": {"model": "GEO_SUB_F0_NTD"},         # NTD -- a Bran Bal genome (distinct idle posture)
    # Tantalus -- the theater-troupe thieves (all aboard the Prima Vista)
    "baku": {"model": "GEO_SUB_F0_BAK"},             # BAK -- Tantalus' boss
    "blank": {"model": "GEO_SUB_F0_BLN"},            # BLN -- Tantalus thief (Zidane's friend)
    "marcus": {"model": "GEO_SUB_F0_MRC"},           # MRC -- Tantalus thief
    "cinna": {"model": "GEO_SUB_F0_CNA"},            # CNA -- Tantalus thief (the hammer)
    "ruby": {"model": "GEO_SUB_F0_RBY"},             # RBY -- Tantalus' actress
    "zenero": {"model": "GEO_SUB_F0_ZNR"},           # ZNR -- a Tantalus "Nero family" member (ZNR ~ Zenero); tentative
    # Alexandria royalty / antagonists
    "brahne": {"model": "GEO_SUB_F0_BRN"},           # BRN -- Queen Brahne of Alexandria
    "queen_brahne": {"model": "GEO_SUB_F0_BRN"},     # alias of brahne
    "beatrix": {"model": "GEO_SUB_F0_BTX"},          # BTX -- General Beatrix of Alexandria
    "kuja": {"model": "GEO_SUB_F0_KJA"},             # KJA -- the antagonist
    "zorn": {"model": "GEO_SUB_F0_ZON"},             # ZON -- Brahne's jester (paired with Thorn)
    "lani": {"model": "GEO_SUB_F0_SBW"},             # SBW -- "Scarlet Bounty Woman": Lani, the bounty hunter
    "pluto_knight": {"model": "GEO_SUB_F0_SSB"},     # SSB -- "Soldier Steiner Base": a male Alexandrian soldier / Knight of Pluto (e.g. Haagen, Weimar)
    # other named figures
    "garland": {"model": "GEO_SUB_F0_GRL"},          # GRL -- Garland of Terra (its field is literally "Invincible/Garland")
    "cid": {"model": "GEO_SUB_F0_CID"},              # CID -- Regent Cid Fabool IX of Lindblum
    "regent_cid": {"model": "GEO_SUB_F0_CID"},       # alias of cid
    "fratley": {"model": "GEO_SUB_F0_FLT"},          # FLT -- Sir Fratley, Burmecian Dragon Knight (Freya's lost love); JP フラットレイ "Furattorei"
    "doctor_tot": {"model": "GEO_SUB_F0_TOT"},       # TOT -- Doctor Tot, the Treno scholar ("Tot Residence")
    "tot": {"model": "GEO_SUB_F0_TOT"},              # alias of doctor_tot
    # Black Waltzes -- Brahne's hunter-mages (No. 2 + Trance Kuja are special boss models with no
    # standard idle/walk anim, so they're intentionally not archetypes -- place by model id if needed)
    "black_waltz_1": {"model": "GEO_SUB_F0_BW1"},    # BW1 -- Black Waltz No. 1 (Ice Cavern)
    "black_waltz_3": {"model": "GEO_SUB_F0_BW3"},    # BW3 -- Black Waltz No. 3 (Cargo Ship)
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
