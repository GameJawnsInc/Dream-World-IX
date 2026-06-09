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
    "aircab": {"model": "GEO_ACC_F0_V10", "pose": 1608},        # V10 -- "Vehicle 10": the generic/station Lindblum aircab car (flies, has doors); cf. `cab_carriage` (TRK) = the high-res rideable carriage
    "aircab_car": {"model": "GEO_ACC_F0_V10", "pose": 1608},    # alias of aircab
    "trap": {"model": "GEO_ACC_F0_ISB", "pose": 10689},         # ISB -- likely the Gargan Roo TRACK/RAIL the Gargant (GRG) rides (in-game: GRG connects to ISB paths), not a trap; also Ipsen's/Pinnacle/Earth Shrine. TENTATIVE
    "scale": {"model": "GEO_ACC_F0_TNB", "pose": 12884},        # TNB -- the Desert Palace balance scale (JP "tenbin" 天秤). The four weights are `wood_weight`/`clay_weight`/`stone_weight`/`iron_weight` (WT0-3); flag-gated in the puzzle, but render fine static. The full at-rest set piece (scale + weights) is the `scale_set` composite.
    "balance_scale": {"model": "GEO_ACC_F0_TNB", "pose": 12884},  # alias of scale
    # -- set dressing identified via the prop gallery (token -> what it is) --
    "orange_fish": {"model": "GEO_ACC_F0_FS1", "pose": 10751},   # FS1 -- the orange fish (alias of `fish`); Madain Sari kitchen
    "blue_fish": {"model": "GEO_ACC_F0_FS2", "pose": 10749},     # FS2 -- a blue fish (Madain Sari kitchen, Chocobo's Lagoon)
    "green_fish": {"model": "GEO_ACC_F0_FS3", "pose": 10747},    # FS3 -- a green fish (Madain Sari kitchen)
    "gargant": {"model": "GEO_ACC_F0_GRG", "pose": 1138},       # GRG -- the Gargant, the giant beetle ridden through Gargan Roo; it rides the ISB track, so placed ALONE it has collision/alignment quirks
    "gondola": {"model": "GEO_ACC_F0_V11", "pose": 8004},       # V11 "Vehicle 11" -- the Alexandria lake boat / gondola
    "extraction_ring": {"model": "GEO_ACC_F0_CER", "pose": 10727},  # CER "CERemony" -- the glowing eidolon-extraction ring (the Zorn/Thorn ritual; A. Castle altar, Gulug extraction site)
    "shelf": {"model": "GEO_ACC_F0_BBX", "pose": 6962},         # BBX -- a Dali underground production shelf / box ("Black Mage Box"?); tentative
    "stone_dial": {"model": "GEO_ACC_F0_FEL", "pose": 792},      # FEL -- a stone dial lever (Pandemonium control room / elevators)
    "fishing_rod": {"model": "GEO_ACC_F0_FIS", "pose": 2226},   # FIS -- a fishing rod with a long line (Quan's Dwelling fishing area, Madain Sari kitchen)
    "altar_stone": {"model": "GEO_ACC_F0_HSK", "pose": 13720},  # HSK -- the triangular "Hogo Seki" protective altar stone (保護石 = protective stone/seal; Palace Sanctum, Oeilvert tombstone, Esto Gaza)
    "teleport_pad": {"model": "GEO_ACC_F0_IFE", "pose": 1896},  # IFE -- the Iifa field emblem / teleport pad (Iifa Tree roots)
    "scroll": {"model": "GEO_ACC_F0_MAP", "pose": 1882},        # MAP -- a rolled map scroll (the Prima Vista map tables; Evil Forest exit, Lindblum walls)
    "map": {"model": "GEO_ACC_F0_MAP", "pose": 1882},           # alias of scroll
    "pot": {"model": "GEO_ACC_F0_SUP", "pose": 1896},           # SUP -- Eiko's soup pot (Madain Sari kitchen)
    "soup_pot": {"model": "GEO_ACC_F0_SUP", "pose": 1896},      # alias of pot
    # -- set dressing, batch 3 (some are HUGE structural assets) --
    "cab_carriage": {"model": "GEO_ACC_F0_TRK", "pose": 7380},  # TRK -- the rideable Air Cab CARRIAGE itself (rides the Lindblum Castle transit tracks); cf. `aircab` (V10) = the generic/station car
    "ship_model": {"model": "GEO_ACC_F0_TSM", "pose": 1105},    # TSM -- the Tantalus thieves' miniature toy model of the Cargo Ship (Mountain shack, Lindblum hideout, Ending)
    "skiff": {"model": "GEO_ACC_F0_BOT", "pose": 1890},         # BOT "BOaT" -- the Madain Sari fishing skiff (the Cove)
    "boat": {"model": "GEO_ACC_F0_BOT", "pose": 1890},          # alias of skiff (cf. `gondola` = the Alexandria V11)
    "gear_wall": {"model": "GEO_ACC_F0_CBH", "pose": 3933},     # CBH "Cargo Belt Housing" -- the HUGE Dali subterranean gear/conveyor/lift wall engine (dwarfs the floor placed alone)
    "dagger": {"model": "GEO_ACC_F0_DAG", "pose": 216},         # DAG -- Garnet's royal dagger (her namesake; Ice Cavern, A. Castle tomb)
    "wind_mirror": {"model": "GEO_ACC_F0_HKG", "pose": 7378},   # HKG -- the Wind Shrine mirror / seal medallion slotted into the altar; the Ipsen's Castle mural object (保護鏡源 "protective mirror source")
    "seal_medallion": {"model": "GEO_ACC_F0_HKG", "pose": 7378},  # alias of wind_mirror
    # -- set dressing, batch 4 --
    "weight_lift": {"model": "GEO_ACC_F0_IRF", "pose": 13156},  # IRF "Ipsen's Room Floor" -- the chandelier weight-lift puzzle platform (Zidane's weight hoists the treasure chandelier up)
    "hatchery": {"model": "GEO_ACC_F0_KGG", "pose": 71},        # KGG -- the Dali Black Mage egg incubator / hatchery (孵化器; Production Area)
    "incubator": {"model": "GEO_ACC_F0_KGG", "pose": 71},       # alias of hatchery
    "trapdoor": {"model": "GEO_ACC_F0_KOR", "pose": 297},       # KOR -- a floor altar trapdoor / pit hole (Fossil Roo cavern, Earth Shrine passage)
    "pit": {"model": "GEO_ACC_F0_KOR", "pose": 297},            # alias of trapdoor
    "neptune_statue": {"model": "GEO_ACC_F0_NEP", "pose": 7146},  # NEP -- the Alexandria "Neptune" guardian statue (A. Castle/Neptune)
    "neptune": {"model": "GEO_ACC_F0_NEP", "pose": 7146},       # alias of neptune_statue
    "ribbon": {"model": "GEO_ACC_F0_RBN", "pose": 13725},       # RBN -- a ribbon, the Madain Sari eidolon-wall offering (Secret Room; also Gulug)
    "rope": {"model": "GEO_ACC_F0_ROP", "pose": 964},           # ROP -- a rope: both the children's jump rope (Alexandria Square) and the steeple bell rope
    # -- set dressing, batch 5 --
    "frog_cart": {"model": "GEO_ACC_F0_V02", "pose": 1460},     # V02 "Vehicle 02" -- Regent Cid's motorized frog-cart (Lindblum Theater Ave.)
    "cargo_ship": {"model": "GEO_ACC_F0_BLK", "pose": 7382},    # BLK -- the full-size Dali Black Mage cargo airship (the vessel hijacked through South Gate); cf. `ship_model` (TSM) = the toy model of it
    "cargo_airship": {"model": "GEO_ACC_F0_BLK", "pose": 7382},  # alias of cargo_ship
    # the four Desert Palace balance-scale WEIGHTS (the `scale`/TNB puzzle); render fine static; material mapping TENTATIVE (per user: Wood/Clay/Stone/Iron in WT0-3 order)
    "wood_weight": {"model": "GEO_ACC_F0_WT0", "pose": 12888},  # WT0 -- scale weight (tentative: Wood)
    "clay_weight": {"model": "GEO_ACC_F0_WT1", "pose": 13132},  # WT1 -- scale weight (tentative: Clay)
    "stone_weight": {"model": "GEO_ACC_F0_WT2", "pose": 13128},  # WT2 -- scale weight (tentative: Stone)
    "iron_weight": {"model": "GEO_ACC_F0_WT3", "pose": 13124},  # WT3 -- scale weight (tentative: Iron)
    # -- set dressing, batch 6 (each in a single field -- rare/specific) --
    "bookcase": {"model": "GEO_ACC_F0_BTN", "pose": 3962},      # BTN "Bookcase Trigger Node" -- the Desert Palace secret-library bookcase
    "windmill_crank": {"model": "GEO_ACC_F0_CRS", "pose": 5959},  # CRS -- the Dali windmill brake crank + grain hopper mechanism (Windmill 2F)
    "round_pillar": {"model": "GEO_ACC_F0_DLB", "pose": 13049},  # DLB -- the Daguerreo lift column B, a cylindrical pillar (Right Hall)
    "square_pillar": {"model": "GEO_ACC_F0_DLF", "pose": 7144},  # DLF -- the Daguerreo lift column F, a square pillar (Left Hall)
    "mage_egg": {"model": "GEO_ACC_F0_EGG", "pose": 71},        # EGG -- the unhatched Black Mage pod/egg (the one Vivi finds under Dali; the "Lindblum Residence" field is a warp overlap); cf. `hatchery` (KGG)
    "egg": {"model": "GEO_ACC_F0_EGG", "pose": 71},             # alias of mage_egg
    "elevator": {"model": "GEO_ACC_F0_ELV", "pose": 5346},      # ELV -- the Prima Vista cargo-hold lift platform (theater-ship internal; hauls props/actors between decks)
    "cargo_lift": {"model": "GEO_ACC_F0_ELV", "pose": 5346},    # alias of elevator
    # -- set dressing, batch 7 (GNT + KOS have offset origins -> render as a tiny dot in an empty viewport) --
    "surveillance_eye": {"model": "GEO_ACC_F0_EYE", "pose": 13175},  # EYE -- the Pandemonium surveillance eye (security laser/camera tracking Zidane at the Exit)
    "eye": {"model": "GEO_ACC_F0_EYE", "pose": 13175},          # alias of surveillance_eye
    "floor_tile": {"model": "GEO_ACC_F0_FLR", "pose": 1386},    # FLR -- a Desert Palace dungeon puzzle floor grid tile (the path-lighting puzzle; glow toggles per step)
    "grid_tile": {"model": "GEO_ACC_F0_FLR", "pose": 1386},     # alias of floor_tile
    "goddess_statue": {"model": "GEO_ACC_F0_GNT", "pose": 4747},  # GNT "GiaNT" -- the colossal Summoner Goddess statue (A. Castle Tomb); origin anchored in its base -> renders as a tiny dot on a flat grid
    "giant_statue": {"model": "GEO_ACC_F0_GNT", "pose": 4747},  # alias of goddess_statue
    "mage_robe": {"model": "GEO_ACC_F0_HOD", "pose": 2477},     # HOD "HOoD" -- Garnet's white-mage robe disguise, discarded in the Prima Vista cabins after her escape
    "hood": {"model": "GEO_ACC_F0_HOD", "pose": 2477},          # alias of mage_robe
    "collapsing_floor": {"model": "GEO_ACC_F0_KOS", "pose": 1894},  # KOS "Koseki" -- the Earth Shrine collapsing-floor trap anchor; hidden until triggered -> default mesh collapses to (0,0,0), renders as a dot
    "trap_anchor": {"model": "GEO_ACC_F0_KOS", "pose": 1894},   # alias of collapsing_floor
    "pull_chain": {"model": "GEO_ACC_F0_LEV", "pose": 6962},    # LEV "LEVer" -- the Gargan Roo ceiling pull-chain track switch (redirects the Gargant); cf. `lever` (KOM) = the small Fossil Roo toggle
    "track_switch": {"model": "GEO_ACC_F0_LEV", "pose": 6962},  # alias of pull_chain
    # -- set dressing, batch 8 --
    "planks": {"model": "GEO_ACC_F0_LG2", "pose": 12940},       # LG2 "Log 2" -- the Alexandria rooftop tied planks (manual-labor prop; cf. `log`/`timber` = LG1)
    "roof_planks": {"model": "GEO_ACC_F0_LG2", "pose": 12940},  # alias of planks
    "hologram_projector": {"model": "GEO_ACC_F0_LIF", "pose": 6960},  # LIF "Life" -- the Oeilvert Terran holographic-history projector (narrates Terra's history)
    "projector": {"model": "GEO_ACC_F0_LIF", "pose": 6960},     # alias of hologram_projector
    "campfire": {"model": "GEO_ACC_F0_MAK", "pose": 6963},      # MAK "Maki" 薪 -- the Evil Forest campfire / firewood bundle (the cozy rest before the forest petrifies)
    "firewood": {"model": "GEO_ACC_F0_MAK", "pose": 6963},      # alias of campfire
    "tiki_torch": {"model": "GEO_ACC_F0_TKE", "pose": 4684},    # TKE -- a torch (Daguerreo Left Hall); TENTATIVE ("Tee-Key" ~ tiki torch)
    "torch": {"model": "GEO_ACC_F0_TKE", "pose": 4684},         # alias of tiki_torch
    # -- set dressing, batch 9 (final GEO_ACC set-dressing) --
    "altar": {"model": "GEO_ACC_F0_ORD", "pose": 8002},         # ORD "Ordeal" -- the central altar / Ordeal pedestal of Ipsen's Castle (Sword Room)
    "pedestal": {"model": "GEO_ACC_F0_ORD", "pose": 8002},      # alias of altar
    "parade_float": {"model": "GEO_ACC_F0_V01", "pose": 1888},  # V01 "Vehicle 01" -- a Lindblum theater parade float / street prop cart (holiday + summit set-dressing; L. Castle Event)
    "float": {"model": "GEO_ACC_F0_V01", "pose": 1888},         # alias of parade_float
    "luxury_cab": {"model": "GEO_ACC_F0_V03", "pose": 1507},    # V03 "Vehicle 03" -- Cid's private luxury air-cab (the Hilda Garde prototype shuttle); cf. `aircab` V10, `cab_carriage` TRK
    "cid_shuttle": {"model": "GEO_ACC_F0_V03", "pose": 1507},   # alias of luxury_cab
    "tunnel_beam": {"model": "GEO_ACC_F0_YIB", "pose": 8099},   # YIB "Y-Intersection Beam" -- a Fossil Roo tunnel support timber / Gargant track-switcher rail (aligns with the pull animations)
    "support_beam": {"model": "GEO_ACC_F0_YIB", "pose": 8099},  # alias of tunnel_beam
    "spear": {"model": "GEO_ACC_F0_YRI", "pose": 12739},        # YRI "Yari" 槍 -- the Burmecian Mythril Spear (Freya salvages it from the armory ruins)
    "mythril_spear": {"model": "GEO_ACC_F0_YRI", "pose": 12739},  # alias of spear
    # -- common HELD items (place static via [[prop]], or via [[npc]] holds = "cup" -> auto held pose) --
    "cup": {"model": "GEO_ACC_F0_CUP", "pose": 1894},           # CUP -- a cup / tankard (held by drinkers)
    "glass": {"model": "GEO_ACC_F0_GRS", "pose": 8239},         # GRS -- a drinking glass (bartender / pub)
    "ticket": {"model": "GEO_ACC_F0_TKT", "pose": 10359},       # TKT -- a play / theater ticket
    "bottle": {"model": "GEO_ACC_F0_BON", "pose": 813},         # BON -- a bottle (the Doom Pub); tentative
    # -- held items identified via the held-item gallery (carrier holds it; pose auto-resolves) --
    "log": {"model": "GEO_ACC_F0_LG1", "pose": 4346},           # LG1 "Log 1" -- a timber beam a worker hauls (maybe a ladder shaft)
    "timber": {"model": "GEO_ACC_F0_LG1", "pose": 4346},        # alias of log
    "axe": {"model": "GEO_ACC_F0_LNW", "pose": 1894},           # LNW "LaNi's Weapon" -- Lani's battle axe (rests on her back at idle)
    "sack": {"model": "GEO_ACC_F0_ZBR", "pose": 13160},         # ZBR "ZuBoRa" (ずぼら = sloppy/lazy/casual) -- a loosely-modeled sack template, carried in the story
    "wreath": {"model": "GEO_ACC_F0_WRE", "pose": 8006},        # WRE "WREath" -- a wreath (Doctor Tot holds one)
    "dagger_doll": {"model": "GEO_ACC_F0_DGR", "pose": 1027},   # DGR "DaGgeR" -- a Dagger (Garnet) puppet; the Tantalus puppet show (Baku holds it)
    "brahne_doll": {"model": "GEO_ACC_F0_DBR", "pose": 1038},   # DBR "Debu BRahne" (デブ = fat) -- a Fat Brahne puppet (Baku holds it)
    "vial": {"model": "GEO_ACC_F0_BIN", "pose": 1880},          # BIN "Bin" (瓶 = bottle/vial) -- Blank's medicine vial, the Evil Forest spore antidote
}


# Composite props -- a multi-part set piece: several objects placed at the prop's (x, z), each with an
# optional (dx, dz) offset. Found via tools/find_composite_props.py + dump_field_objects.py. Most parts
# CO-LOCATE at one (x, z), y=0 (field 300's save point -- the floating feather/letter are baked into the
# MODELS, not script offsets); a few sit BESIDE the anchor (field 2203's scale -- the wood weight is
# offset from the scale body). Each part is (GEO model name, pose id) OR (GEO, pose, dx, dz).
#
# WIRED -- build.py expands `prop = "save_point"` to one inject_prop per part at the prop's (x, z). The
# save set {MOG, MGR, MGP, LTT} co-locates in 47 shipping fields (the most common composite); only MOG
# (moogle) + MGR (book) are placed STATIC -- MGP (feather)/LTT (letter) show ONLY during the save
# animation (their tag-37 does SetObjectFlags(7) = show bit; at rest flags(14) hides them -- field 300 e5).
# In-game: VERIFIED (2026-06-09) -- the moogle sits ON the book, co-located + facing down toward the
# player (the default facing is correct, no `face` needed); renders clean next to a normal single prop.
PROP_COMPOSITES: dict = {
    "save_point": [                       # the iconic moogle save point (Ice Cavern field 300, +46 more)
        ("GEO_NPC_F0_MOG", 2904),         # the moogle (an NPC model, placed static -- sits on the book)
        ("GEO_ACC_F0_MGR", 1872),         # the save book
        # NB: the real save point ALSO co-locates the feather (MGP, pose 1874) + Mognet letter (LTT, 2479)
        # here, but both are HIDDEN at rest -- their Init sets SetObjectFlags(14) (no "show model" bit) and
        # their resting pose is tucked away. They only animate into view during the SAVE interaction (the
        # feather's tag-37 func does RunAnimation(4652) + SetObjectFlags(7)=show -- the moogle writing). So
        # they add nothing to a STATIC set piece -- omitted here. (In-game-verified: only moogle+book show.)
    ],
    "scale_set": [                        # the Desert Palace balance scale LOADED at rest (static set piece; field 2203 "Rack")
        ("GEO_ACC_F0_TNB", 2561),         # scale -- field 2203's loaded/tilted pose (the `scale` archetype's even 12884 is the EMPTY pose)
        ("GEO_ACC_F0_WT1", 6263),         # clay weight  -- lifted onto a pan (field 2203's on-pan pose)
        ("GEO_ACC_F0_WT2", 6267),         # stone weight -- on a pan
        ("GEO_ACC_F0_WT3", 6271),         # iron weight  -- on a pan
        ("GEO_ACC_F0_WT0", 12888, 188, -102),  # wood weight -- on the ground BESIDE the scale (offset from field 2203)
        # These are field 2203's AT-REST poses, NOT the weights' canonical archetype poses (13132/13128/13124 =
        # their off-scale state -- co-located with the scale BODY those sit low + hidden inside it; 6263/6267/6271
        # lift them onto the pans). Field 2204 ("Odyssey") spreads the weights out = the live PUZZLE, not a set piece.
        # In-game: VERIFIED (2026-06-09) -- 3 weights on the (loaded, tilted) scale + the wood weight beside it.
    ],
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


def is_composite(name) -> bool:
    """True if ``name`` is a known **composite** prop (a multi-part set piece, e.g. ``save_point``)."""
    return str(name).strip().lower() in PROP_COMPOSITES


def resolve_composite(name):
    """``[(model_id, pose_id, dx, dz), ...]`` -- the parts of a composite prop, each placed at the prop's
    ``pos`` plus its (dx, dz) offset. Most parts co-locate (dx=dz=0, the way a save point stacks); a few
    sit beside the anchor (the scale's side weight). Raises ValueError on an unknown composite."""
    key = str(name).strip().lower()
    if key not in PROP_COMPOSITES:
        raise ValueError(f"unknown composite prop {name!r}. Known: {', '.join(sorted(PROP_COMPOSITES))}.")
    parts = []
    for part in PROP_COMPOSITES[key]:
        geo, pose = part[0], part[1]
        dx, dz = (int(part[2]), int(part[3])) if len(part) >= 4 else (0, 0)
        parts.append((_catalog.resolve_model(geo), int(pose), dx, dz))
    return parts
