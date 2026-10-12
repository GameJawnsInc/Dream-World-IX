"""Overworld minimap MARKER registry + the reveal helper (``[startup] reveal_markers``).

The 64 world-overview location markers (the town/dungeon dots) are each drawn by the engine iff their
**save-backed discovery bit** is set: ``gEventGlobal`` bit ``NAVI_BIT_BASE + locId`` — i.e. bytes 92-99 /
bits 736-799 (``keventNaviLocF0..F3``, ``ff9.cs:6957``), read by ``w_naviLocationAvailable`` (a marker draws
iff its coords are non-zero AND its bit is set). The real game sets these from a field's exit cascade
(``opE4(736+locId)=1``) as you reach each place. **A mod reveals a marker the exact same way — a plain
GLOB-bit set — so ``[startup] reveal_markers = [...]`` compiles to ``(736+locId, 1)`` bit presets with no
engine change** (see ``ff9mapkit/docs/OVERWORLD_ENGINE.md`` § minimap, and ``[[flag]]`` for the primitive).

:data:`MARKER_NAMES` is *derived reference data* (the location labels, like the InfoHub catalogs) for by-name
authoring. Names repeat across slots (``South Gate`` = 6-10, ``Qu's Marsh`` = 21/29/40/45, ``Gizamaluke's
Grotto`` = 16/20/59), so a NAME resolves to ALL its slots; author by ``locId`` (0-63) for a single dot.

⚠ **NAVIPOS COORDINATE GAP (2026-07-18):** the hardcoded ``ff9.navipos[2, 64]`` table backs locIds 49-53 and
59-63 with ``(0, 0)`` in BOTH ``w_naviMapno`` dimensions (63 is the engine alias for 49, ``Chocobo's
Paradise``). Setting a marker's discovery bit in that range (via ``reveal_markers`` or otherwise) is a
faithful ``opE4`` bit set, but the marker has no coordinates to draw at -- a custom location cannot get a
pause-map dot in that locId range without an engine table edit.
"""
from __future__ import annotations

from pathlib import Path

NAVI_BIT_BASE = 736          # gEventGlobal bit for marker locId 0 (byte 92 << 3); marker N -> bit 736+N
NAVI_LOCATION_COUNT = 64     # w_naviLocationPos is navipos[2, 64]

# locId -> display name. Derived from the world-map field text (txid 0, split by newline, index locId+1);
# slots 50-52 (placeholders "?"/"???") and 60-62 (unnamed/unused) are intentionally absent. locId 63 is an
# engine alias that shows "Chocobo's Paradise" (== locId 49). Apostrophes normalised to ASCII.
MARKER_NAMES: dict[int, str] = {
    0: "Alexandria Harbor", 1: "Alexandria", 2: "Evil Forest", 3: "Ice Cavern", 4: "Quan's Dwelling",
    5: "Treno", 6: "South Gate", 7: "South Gate", 8: "South Gate", 9: "South Gate", 10: "South Gate",
    11: "Ice Cavern", 12: "Observatory Mountain", 13: "Dali", 14: "North Gate", 15: "North Gate",
    16: "Gizamaluke's Grotto", 17: "Burmecia", 18: "Cleyra", 19: "Chocobo's Forest",
    20: "Gizamaluke's Grotto", 21: "Qu's Marsh", 22: "Pinnacle Rocks", 23: "Lindblum Dragon's Gate",
    24: "Lindblum", 25: "Lindblum Harbor", 26: "Earth Shrine", 27: "Desert Palace", 28: "Mognet Central",
    29: "Qu's Marsh", 30: "Black Mage Village", 31: "Fossil Roo", 32: "Conde Petie", 33: "Madain Sari",
    34: "Conde Petie Mountain Path", 35: "Conde Petie Mountain Path", 36: "Iifa Tree", 37: "Chocobo's Lagoon",
    38: "Wind Shrine", 39: "Daguerreo", 40: "Qu's Marsh", 41: "Oeilvert", 42: "Landing Site",
    43: "Water Shrine", 44: "Ipsen's Castle", 45: "Qu's Marsh", 46: "Shimmering Island", 47: "Esto Gaza",
    48: "Fire Shrine", 49: "Chocobo's Paradise", 53: "Memoria", 54: "Chocobo's Air Garden",
    55: "Chocobo's Air Garden", 56: "Chocobo's Air Garden", 57: "Chocobo's Air Garden",
    58: "Chocobo's Air Garden", 59: "Gizamaluke's Grotto",
}


def marker_bit(loc_id: int) -> int:
    """The ``gEventGlobal`` discovery bit index for marker ``loc_id`` (0-63)."""
    if not (0 <= loc_id < NAVI_LOCATION_COUNT):
        raise ValueError(f"marker locId must be 0..{NAVI_LOCATION_COUNT - 1} (got {loc_id})")
    return NAVI_BIT_BASE + loc_id


def _norm(s: str) -> str:
    """Case/punctuation-insensitive key for name matching ('Qu's Marsh' == 'qus marsh' == 'qusmarsh')."""
    return "".join(c for c in s.lower() if c.isalnum())


_NAME_TO_LOCIDS: dict[str, list[int]] = {}
for _loc, _nm in MARKER_NAMES.items():
    _NAME_TO_LOCIDS.setdefault(_norm(_nm), []).append(_loc)
for _k in _NAME_TO_LOCIDS:
    _NAME_TO_LOCIDS[_k].sort()


def resolve_markers(entries) -> list[int]:
    """Resolve a ``reveal_markers`` list to a sorted list of unique marker locIds (0-63).

    Each entry is an ``int`` locId (0-63), a location NAME (str; resolves to ALL its slots, so ``"South
    Gate"`` -> [6,7,8,9,10]), or the literal ``"all"`` (every slot 0-63). Raises ``ValueError`` on an unknown
    name or out-of-range id. A single string that isn't ``"all"`` and isn't a known name is an error (with a
    hint), so a typo can't silently no-op."""
    if entries is None:
        return []
    if isinstance(entries, (str, int)) and not isinstance(entries, bool):
        entries = [entries]
    out: set[int] = set()
    for e in entries:
        if isinstance(e, bool):
            raise ValueError(f"reveal_markers entry must be a locId int or a location name (got {e!r})")
        if isinstance(e, int):
            if not (0 <= e < NAVI_LOCATION_COUNT):
                raise ValueError(f"reveal_markers locId must be 0..{NAVI_LOCATION_COUNT - 1} (got {e})")
            out.add(e)
        elif isinstance(e, str):
            if e.strip().lower() == "all":
                out.update(range(NAVI_LOCATION_COUNT))
                continue
            locs = _NAME_TO_LOCIDS.get(_norm(e))
            if not locs:
                raise ValueError(
                    f"unknown worldmap marker {e!r} -- use a location name "
                    f"(e.g. 'Alexandria', 'Ice Cavern'), a locId 0..63, or 'all'")
            out.update(locs)
        else:
            raise ValueError(f"reveal_markers entry must be a locId int or a location name (got {e!r})")
    return sorted(out)


def marker_presets(entries) -> list[tuple[int, int]]:
    """``reveal_markers`` -> ``(bit_index, 1)`` GLOB-bit presets for :func:`content.startup.startup_body`."""
    return [(marker_bit(loc), 1) for loc in resolve_markers(entries)]


# --------------------------------------------------------------------------- marker RENAME (world text block 68)
# The marker's world-map LABEL is FF9TextTool.GetTableText(0u)[locId+1] (WorldHUD.cs:826): the world text block
# (mesID 68, shared by all EVT_WORLD_WORLD00..12) txid-0, split by newline AFTER its leading [TBLE=...] tag
# (DialogBoxSymbols.ParseTextSplitTags ignores the TBLE offset numbers, DialogBoxSymbols.cs:35-38). So renaming a
# marker = replace the locId+1'th newline-entry of that one message -- no offset math -- and ship the .mes as a
# mod-folder shadow (embeddedasset/text/<lang>/field/68.mes). A name repeats across slots (South Gate = 6-10), so
# by-NAME renames every slot it owns; use a locId to rename ONE dot.
WORLD_TEXT_BLOCK = 68


#: the highest label slot the plate machinery can render: split index = case = locId+1, and
#: ``Byte[24] = case + 100`` is an 8-bit var, so case caps at 155 -> locId 154. locIds 90-92
#: (cases 91-93) are the vehicle HUD trio -- reserved (entrance.RESERVED_VIRGIN_CASES).
MAX_RENAME_LOCID = 154


def resolve_renames(cfg_list) -> dict:
    """``[{locid|name, to}]`` -> ``{locId: new_name}``. A ``name`` renames every slot it owns. Raises ValueError
    on an unknown/out-of-range selector, a missing/blank ``to``, or a ``to`` containing a newline (would add a
    marker). Later entries win on a locId collision."""
    out: dict[int, str] = {}
    for i, item in enumerate(cfg_list or []):
        if not isinstance(item, dict):
            raise ValueError(f"marker_rename #{i} must be a table with (locid | name) + to")
        to = item.get("to")
        if not isinstance(to, str) or not to.strip():
            raise ValueError(f"marker_rename #{i} needs a non-empty `to` (the new label)")
        if "\n" in to:
            raise ValueError(f"marker_rename #{i} `to` must be a single line (no newline)")
        sel = item["locid"] if item.get("locid") is not None else item.get("name")
        if sel is None:
            raise ValueError(f"marker_rename #{i} needs a `locid` (0-{MAX_RENAME_LOCID}) or a `name`")
        if isinstance(sel, int) and not isinstance(sel, bool):
            # An int locid may address the EXTENDED band (64-154 = virgin cases 65-155, slots past
            # the stock table -- apply_marker_renames extends it). resolve_markers stays capped at
            # the NAVI dot table (0-63): dots and labels are different spaces above 63.
            if not (0 <= sel <= MAX_RENAME_LOCID):
                raise ValueError(f"marker_rename #{i}: locid must be 0..{MAX_RENAME_LOCID} (got {sel}; "
                                 f"split index = locid+1 and Byte[24] caps the case space at 155)")
            if 90 <= sel <= 92:
                raise ValueError(f"marker_rename #{i}: locid {sel} is the vehicle HUD trio "
                                 f"(cases 91-93) -- reserved, pick another slot")
            out[sel] = to
            continue
        for loc in resolve_markers([sel]):
            out[loc] = to
    return out


#: what a table slot minted only to reach a HIGHER one reads if anything ever indexes it: the game's own
#: mystery-spot placeholder (stock split[51]/[52] -- the quicksand class -- are exactly this string).
EXTEND_PLACEHOLDER = "  ?  "


def apply_marker_renames(mes_body: str, renames: dict) -> str:
    """Return ``mes_body`` (a world text block 68 ``.mes``) with the marker labels in ``renames`` ({locId: name})
    applied to txid-0. Byte-preserving elsewhere (a single splice of the one message's text). A no-op (returns the
    input) if ``renames`` is empty or txid-0 is absent.

    A locId PAST the table's end EXTENDS it (padding any gap with :data:`EXTEND_PLACEHOLDER`): the stock table
    has 61 entries (cases 0-60), and the VIRGIN nameplate band (cases 61-64, locIds 60-63 -- see
    ``entrance.author_entrance``) lives in slots the stock game never shipped. The engine reads the slot as
    ``GetTableText(0)[case]`` -- a plain split-array index -- so the entry existing in OUR deployed 68.mes is
    exactly what makes the custom name renderable. (``resolve_renames`` already caps locIds at 63, which caps
    the table at the engine's 65-slot case space.)"""
    if not renames:
        return mes_body
    from ..dialogue import parse_mes
    t0 = parse_mes(mes_body).get(0)
    if t0 is None or t0.text is None:
        return mes_body
    text = t0.text
    tag_end = text.find("]") + 1 if text.startswith("[TBLE=") else 0   # skip the leading [TBLE=...] tag
    prefix, rest = text[:tag_end], text[tag_end:]
    entries = rest.split("\n")
    for loc, name in renames.items():
        idx = loc + 1                                                  # [0]=Dummy, [locId+1]=the label
        if idx < 0:
            continue
        while idx >= len(entries):                                     # the virgin band: extend, don't drop
            entries.append(EXTEND_PLACEHOLDER)
        entries[idx] = name
    new_text = prefix + "\n".join(entries)
    return mes_body.replace(text, new_text, 1) if new_text != text else mes_body


def deploy_marker_renames(cfg_list, *, mod_folder: str, game=None, langs=None) -> list:
    """Write the marker-rename override into ``<mod>/FF9_Data/embeddedasset/text/<lang>/field/68.mes`` for each
    language (so it shadows the base world text). Returns the written ``Path`` list. RELAUNCH to apply. Raises
    ``ValueError`` on a bad config."""
    from pathlib import Path
    from .. import config, dialogue
    from ..fsutil import atomic_write_text
    renames = resolve_renames(cfg_list)                                # validates
    if not renames:
        return []
    langs = list(langs) if langs else list(config.LANGS)
    root = config.find_mod_root(config.find_game_path(game), mod_folder)
    layout = config.ModLayout(root)
    written = []
    for lang in langs:
        dest = Path(layout.mes_path(lang, WORLD_TEXT_BLOCK))
        if dest.is_file():
            # MERGE with the already-deployed override, never rebuild from the base text: the
            # deployed file IS base + every prior rename, so re-extracting the base here would
            # silently WIPE every name a previous entrance registered (the R3 Lamplight deploy
            # erased R1's "Lantern Quay" split[53] exactly this way -- caught by a byte check,
            # invisible to every other gate). apply_marker_renames splices only the locIds given,
            # so layering on the deployed file is idempotent and preserves the rest verbatim.
            # (Universal-newline read: a CRLF file an older deploy wrote heals to LF here.)
            base = dest.read_text(encoding="utf-8")
        else:
            base = dialogue.extract_field_mes(9000, lang=lang, game=game, zone_id=WORLD_TEXT_BLOCK)
        if not base:
            continue                                                   # this lang's block 68 not found -> skip
        out = apply_marker_renames(base, renames)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # newline="\n": stock block 68 is pure LF; a bare text-mode write on Windows put a CRLF into
        # EVERY world message (item-get, Moguo, Zorn/Thorn, the navigation menus), not just the label.
        atomic_write_text(dest, out, newline="\n")
        written.append(dest)
    return written


# --------------------------------------------------------------------- the world-map image
# The big in-game map ("world_map_full_all") is a MOD-OVERRIDABLE loose PNG:
# WorldHUD.DisplayFullmapInfo -> AssetManager.SearchAssetOnDisc("EmbeddedAsset/UI/
# Sprites/world_map_full_all.png") searches the stacked FolderNames (Moguri ships
# its own HD copy), so a custom continent can be DRAWN ONTO THE MAP with no DLL.
# The projection is the ENGINE'S OWN (w_naviGetPos, ff9.cs:7019): the mapped world
# is exactly 1536x1280 units -> normalized (sx, syTop); the world sits on the
# REGISTERED art sub-rect (WORLD_MAP_ART_FRAME below -- FFT-registered against the
# true stock terrain geometry; the navipos marker fit vx ~ wx*240/1536 independently
# confirms the extents). The disc-1 "mistcontinent" map (shown below scenario 5990) is
# a separately painted close-up of the Mist continent that excludes the SW pocket: new
# land is drawn on the all-world map only, but land a folder REMOVED is erased from
# both (world/maperase.py).

#: the engine's mapped world extents (w_naviGetPos, map 1)
WORLD_MAP_EXTENT = (1536.0, 1280.0)

MAP_SPRITE_REL = "FF9_Data/EmbeddedAsset/ui/sprites/world_map_full_all.png"
MIST_SPRITE_REL = "FF9_Data/EmbeddedAsset/ui/sprites/world_map_full_mistcontinent.png"


def _land_anchors():
    """The 49 live dim-1 marker WORLD coords (navipos tx/256, ty/256, extracted
    from the engine table) -- every one a real town/dungeon on painted LAND in
    any faithful world map; the calibration + colour-sampling targets."""
    return [(191.6, -474.5), (223.2, -607.3), (305.8, -934.0), (326.2, -569.1),
            (341.8, -489.4), (372.5, -239.0), (380.3, -1025.5), (394.6, -798.2),
            (454.6, -318.9), (468.3, -621.2), (471.8, -1076.6), (504.0, -116.1),
            (513.1, -903.8), (593.5, -1131.4), (730.7, -592.9), (781.6, -320.7),
            (850.3, -275.5), (865.2, -1102.3), (885.8, -233.2), (894.7, -352.1),
            (895.9, -1086.8), (896.7, -775.3), (910.6, -190.0), (916.0, -1018.8),
            (920.2, -402.1), (934.8, -942.7), (942.4, -1092.1), (954.2, -390.7),
            (961.7, -711.2), (979.4, -875.3), (992.6, -803.6), (1025.8, -310.4),
            (1037.4, -755.2), (1075.5, -106.1), (1088.0, -952.4), (1094.7, -806.4),
            (1111.7, -793.9), (1160.4, -843.1), (1168.1, -367.7), (1172.2, -902.0),
            (1184.9, -277.4), (1197.3, -799.6), (1217.5, -747.4), (1253.3, -436.4),
            (1282.2, -958.4), (1283.9, -698.9), (1305.8, -644.5), (1349.8, -678.0),
            (1398.7, -922.3)]


def _ocean_probes():
    """Known PURE-OCEAN world coords, all INTERIOR to the map art (the SW pocket's
    pre-continent blocks, certified open ocean by the continent-siting census and
    clear of the frame) -- the calibration's negative constraints."""
    return [(256.0, -900.0), (192.0, -780.0), (288.0, -1200.0),
            (140.0, -1220.0), (200.0, -970.0), (256.0, -1100.0)]


from .frames import wrap_world_xz as _wrap_world     # the ONE fold (audit rec 12); was local


def _load_active_world_map(mod_folder=None, *, game=None, sprite_rel: str = MAP_SPRITE_REL):
    """The ACTIVE map image (``sprite_rel``: the all-world map by default) + its source:
    the highest-priority loose PNG across the stacked FolderNames (skipping
    ``mod_folder``'s own override -- the compositor must not composite over its own
    prior output), else the stock ``sharedassets2.assets`` texture."""
    import re as _re
    from PIL import Image
    from .. import config
    gp = config.find_game_path(game)
    ini = gp / "Memoria.ini"
    folders = []
    if ini.is_file():
        m = _re.search(r"^FolderNames\s*=\s*(.+)$",
                       ini.read_text(encoding="utf-8", errors="ignore"), _re.M)
        if m:
            folders = [f.strip().strip('"') for f in m.group(1).split(",")]
    for f in folders:
        if mod_folder and f == mod_folder:
            continue
        p = gp / f / sprite_rel
        if not p.is_file():
            p2 = gp / f / sprite_rel.replace("ui/sprites", "UI/Sprites")
            p = p2 if p2.is_file() else p
        if p.is_file():
            return Image.open(p).convert("RGB"), str(p)
    import UnityPy
    name = sprite_rel.rsplit("/", 1)[-1][:-len(".png")]
    env = UnityPy.load(str(gp / "x64/FF9_Data/sharedassets2.assets"))
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            d = obj.read()
            if str(getattr(d, "m_Name", "")) == name:
                return d.image.convert("RGB"), "sharedassets2.assets"
    raise ValueError(f"{name} not found in any mod folder or sharedassets2")


# Where the painted world sits inside the map PNG, as FRACTIONS of the image:
# the world's 1536x1280 maps onto the sub-rect X = 51 + u*1168, Y = 42 + t*1002 of
# the 1273x1080 art (u = wx/1536, t = (-wz)/1280). REGISTERED against the TRUE
# stock world geometry (2026-07-12): every stock Block Terrain land tri rasterized
# to a world land mask and FFT-correlated against the stock map's land pixels --
# the peak hugs every painted coastline, and the Dali navipos dot cross-checks
# within ~9px. NOTE the engine's PLAYER ICON draws ~30px WEST of this art frame
# (a constant engine-side bias, measured in-game at two known positions -- present
# over vanilla land too); the art frame, the navipos dots, and the painted vanilla
# continents all agree with THIS mapping.
WORLD_MAP_ART_FRAME = (51 / 1273.0, 42 / 1080.0, 1168 / 1273.0, 1002 / 1080.0)


def _world_art_rect(im, frame=WORLD_MAP_ART_FRAME):
    """The registered world art rect ``(x0, y0, x1, y1)``, scaled to ``im``."""
    fx, fy, fw, fh = frame
    return (fx * im.width, fy * im.height,
            (fx + fw) * im.width, (fy + fh) * im.height)


# The disc-1 MIST chart, same form (the world's 1536x1280 onto X = fx*W + u*fw*W, Y = fy*H + t*fh*H): a close-up,
# so the world rect overhangs the image. REGISTERED 2026-10-12 like the all-world frame -- the stock land mask
# rescaled and correlated against the chart's land pixels over a sweep of x and y scales, the optimum interior to
# both (Dice 0.91-0.93 by land mask; the outline hugs the painted coast): 1.300 px/u across, 1.3075 down, world (0, 0) at
# (-778, -586). It shows world x ~598..1578, z ~-448..-1274.
MIST_MAP_ART_FRAME = (-778 / 1273.0, -586 / 1080.0, 1.300 * 1536 / 1273.0, 1.3075 * 1280 / 1080.0)
# THE CHART'S DRIFT (2026-10-12, studies/terrain-malleability/mapchart census): the all-world chart is not its
# registered frame scaled. The local offsets of 46 islands, each found on the art, fit a plane to ~1.3px rms: the
# painted world is ~4% short down and ~0.9% narrow across, so a coast near the top or bottom edge is painted up to
# ~24px from where WORLD_MAP_ART_FRAME puts it (the middle agrees). (dx/W, dy/H) = a + b*(x/W) + c*(y/H) per axis.
# The map erase starts its search there; new land is still drawn on the frame. The Mist frame was registered with
# its two scales apart and needs none (16 islands, all within 7px).
WORLD_MAP_DRIFT = ((-0.87 / 1273.0, -0.0089, 0.0002 * 1080 / 1273.0),
                   (19.22 / 1080.0, -0.0014 * 1273 / 1080.0, -0.0401))


def _drift(im, coeffs):
    """``coeffs`` (a :data:`WORLD_MAP_DRIFT`-form plane) as ``(x, y) -> (dx, dy)`` in ``im``'s pixels."""
    (ax, bx, cx), (ay, by, cy) = coeffs
    W, H = im.width, im.height
    return lambda x, y: (W * (ax + bx * x / W + cx * y / H), H * (ay + by * x / W + cy * y / H))


# Both charts share one drawn frame: the painted art lies inside it (the all-world art rect pulled in 8px). The
# erase never touches the frame, or the Mist chart's corner emblem.
CHART_INSIDE = (59 / 1273.0, 50 / 1080.0, 1211 / 1273.0, 1036 / 1080.0)
MIST_EMBLEM = (0.0, 880 / 1080.0, 245 / 1273.0, 1.0)


def _chart_inside(im, exclude=()):
    """The pixels inside the chart's drawn frame, minus ``exclude`` boxes (image fractions ``(x0, y0, x1, y1)``)."""
    import numpy as np
    m = np.zeros((im.height, im.width), bool)
    for i, (fx0, fy0, fx1, fy1) in enumerate((CHART_INSIDE,) + tuple(exclude)):
        box = (slice(int(round(fy0 * im.height)), int(round(fy1 * im.height))),
               slice(int(round(fx0 * im.width)), int(round(fx1 * im.width))))
        m[box] = i == 0
    return m


def _erase_chart(im, mod_folder, *, disc, lod, game, frame, exclude=(), drift=None):
    """Run the map erase (:mod:`.maperase`) over chart ``im`` registered by ``frame``: ``(image, stock, edited,
    reports)``. ``stock`` is the chart's per-pixel stock class map (DEEP/SHALLOW/LAND) round the edited cells."""
    import numpy as np
    from PIL import Image
    from . import maperase as ME
    x0, y0, x1, y1 = _world_art_rect(im, frame)
    ext_x, ext_z = WORLD_MAP_EXTENT

    def to_px(wx, wz):                       # world_tris are absolute (x in [0, 1536]): no fold
        return x0 + (wx / ext_x) * (x1 - x0), y0 + ((-wz) / ext_z) * (y1 - y0)
    stock, effective, edited = ME.class_rasters(mod_folder, disc=disc, to_px=to_px, size=im.size, lod=lod,
                                                game=game)
    if not edited:
        return im, stock, edited, []
    A = np.asarray(im, dtype=float).copy()
    reports = ME.erase_removed(A, stock, effective, inside=_chart_inside(im, exclude),
                               drift=_drift(im, drift) if drift else None)
    if any(r.get("erased_px") for r in reports):
        im = Image.fromarray(np.clip(np.rint(A), 0, 255).astype(np.uint8))
    return im, stock, edited, reports


def _islet_anchors():
    """Interiors of REAL SMALL ISLANDS (world coords): the colour source for the
    painted land -- on the parchment-style chart, sea and land share the base
    tone and an islet is a slightly distinct fill + a darker drawn rim, so the
    fill must come from how the map itself draws ISLETS, not continent tops."""
    return [(480.0, -1120.0), (608.0, -1120.0), (12.0, -20.0)]


def composite_world_map(mod_folder: str, *, disc: int = 1, lod: str = "0_1", game=None,
                        dry_run: bool = False, verbose: bool = True,
                        target_disc: int | None = None) -> dict:
    """:func:`render_world_maps`, then write the folder's chart override(s) (none on a dry run)."""
    summary, im, mim = render_world_maps(mod_folder, disc=disc, lod=lod, game=game, verbose=verbose,
                                         target_disc=target_disc)
    summary["dry_run"] = dry_run
    if not dry_run:
        for img, out in ((im, summary["out"]), (mim, (summary["mist"] or {}).get("out"))):
            if img is not None and out:
                Path(out).parent.mkdir(parents=True, exist_ok=True)
                img.save(out)
    return summary


def render_world_maps(mod_folder: str, *, disc: int = 1, lod: str = "0_1", game=None, verbose: bool = True,
                      target_disc: int | None = None) -> tuple:
    """Draw the mod folder's deployed overworld LAND onto the all-world map image
    (shipped by :func:`composite_world_map` as the folder's own ``world_map_full_all.png``
    override). Returns ``(summary, all-world image, Mist image or None)``.

    Reads every ``Block[x][y] Terrain.ff9mesh`` under the folder's WorldMap tree,
    projects the terrain triangles through the engine's own map projection
    (frame-calibrated), and paints them in colours sampled from the map itself
    (fill = the median land colour at the real-town anchors; rim = that colour
    darkened). Data-derived end to end -- no hand art. RELAUNCH to see it.

    THE ERASE (disc 1 and 4): land the folder REMOVED from a real cell (``world-sink``, an
    in-place coast cut) is taken off the chart first, repainted as the sea round it
    (:mod:`.maperase`), on the all-world chart and, on disc 1, the Mist chart too (its own
    ``world_map_full_mistcontinent.png`` override, written when it erases something or the
    folder already has one). A real cell's own stock land is never repainted flat: only the
    land a folder ADDS is drawn. A site the chart does not draw is skipped and reported.

    THE READ/WRITE DISC SPLIT. ``target_disc`` moves the deployed-tree SCAN to that namespace
    (a synthetic world's land lives only there; scanning Disc1 would draw the real disc-1
    islands on a map the caller believes describes a synthetic world). ⚠ The produced sprite
    override is per MOD FOLDER, not per disc -- one ``world_map_full_all.png`` serves every
    world the folder hosts, so compositing a synthetic namespace OVERWRITES the sprite a
    disc-1 composite produced (last writer wins). A synthetic namespace is never erased."""
    import re as _re
    from PIL import ImageDraw
    from .. import config
    from . import mesh as M
    gp = config.find_game_path(game)
    im, src = _load_active_world_map(mod_folder, game=game)
    x0, y0, x1, y1 = _world_art_rect(im)
    if verbose:
        print(f"  art rect ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) in {im.width}x{im.height}")
    W, H = im.width, im.height
    ext_x, ext_z = WORLD_MAP_EXTENT

    def to_px(wx, wz):
        wxw, wzw = _wrap_world(wx, wz)
        return (x0 + (wxw / ext_x) * (x1 - x0),
                y0 + ((-wzw) / ext_z) * (y1 - y0))

    samples = []
    for wx, wz in _islet_anchors():
        px, py = to_px(wx, wz)
        if 0 <= px < W and 0 <= py < H:
            samples.append(im.getpixel((int(px), int(py))))
    samples.sort(key=lambda cc: cc[0] + cc[1] + cc[2])
    fill = samples[len(samples) // 2]
    rim = tuple(int(v * 0.55) for v in fill)

    rtarget = disc if target_disc is None else int(target_disc)
    root = gp / mod_folder / f"FF9_Data/WorldMap/Disc{rtarget}/{lod}"
    blocks = sorted(root.rglob("Block[[]*[]] Terrain.ff9mesh"))
    if not blocks:
        raise ValueError(f"{mod_folder} has no deployed Disc{rtarget} WorldMap Terrain overrides to draw")
    stock, edited, erased = None, set(), []
    if rtarget in (1, 4):                    # a real disc: take off the land the folder removed
        from .maperase import LAND, dilate
        im, stock, edited, erased = _erase_chart(im, mod_folder, disc=rtarget, lod=lod, game=game,
                                                 frame=WORLD_MAP_ART_FRAME, drift=WORLD_MAP_DRIFT)
        edited = set(edited)
        stock_land = dilate(stock == LAND, 2)   # a kept coast's thin tri centres a half-covered pixel
    draw = ImageDraw.Draw(im)
    n_tris = 0
    polys = []
    for p in blocks:
        m = _re.match(r"Block\[(\d+)\]\[(\d+)\]", p.name)
        bx, by = int(m.group(1)), int(m.group(2))
        bm = M.blockmesh_from_ff9mesh(p, disc=rtarget, x=bx, y=by, lod=lod, part="terrain")
        ox, oz = 64.0 * bx, -64.0 * by
        for tri in bm.tris:
            a, b, c = (bm.verts[i] for i in tri)
            area2 = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
            if max(a[1], b[1], c[1]) < -40.0 or abs(area2) <= 1e-6:
                continue                     # a hidden stub / divert-arm stub: not land (it drew a stray dot)
            # the block ORIGIN is already a wrapped label (<=1472), so wx = ox + local stays in
            # [0,1536] and needs NO further fold -- to_px's per-vertex _wrap_world would fold a
            # vert at exactly x=1536 to 0 and smear a seam block's polygon across the whole
            # chart. x=1536 maps to the art rect's right edge; a seam landmass then draws split
            # at the chart edges, which is exactly how the engine's own minimap unrolls a torus.
            pts = [(x0 + ((bm.verts[i][0] + ox) / ext_x) * (x1 - x0),
                    y0 + ((-(bm.verts[i][2] + oz)) / ext_z) * (y1 - y0)) for i in tri]
            if (bx, by) in edited:           # a real cell: draw only the land the folder ADDED
                cx, cy = (int(sum(q[0] for q in pts) / 3), int(sum(q[1] for q in pts) / 3))
                if 0 <= cx < W and 0 <= cy < H and stock_land[cy, cx]:
                    continue
            polys.append(pts)
            n_tris += 1
    for pts in polys:                       # rim pass: a 1px outline under the fills
        draw.polygon(pts, outline=rim)
    for pts in polys:
        draw.polygon(pts, fill=fill)
    out = gp / mod_folder / MAP_SPRITE_REL
    summary = {"source": src, "blocks": len(blocks), "tris": n_tris, "fill": fill,
               "art_rect": [x0, y0, x1, y1], "out": str(out), "erased": erased, "mist": None}
    mim = None
    if rtarget == 1 and edited:              # the Mist chart (disc 1 below scenario 5990): erase only
        mist_out = gp / mod_folder / MIST_SPRITE_REL
        mim, msrc = _load_active_world_map(mod_folder, game=game, sprite_rel=MIST_SPRITE_REL)
        mim, _s, _e, merased = _erase_chart(mim, mod_folder, disc=1, lod=lod, game=game, frame=MIST_MAP_ART_FRAME,
                                            exclude=(MIST_EMBLEM,))
        if any(r.get("erased_px") for r in merased) or mist_out.is_file():
            summary["mist"] = {"source": msrc, "out": str(mist_out), "erased": merased}
        else:
            mim = None
    return summary, im, mim
