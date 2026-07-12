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
"""
from __future__ import annotations

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
            raise ValueError(f"marker_rename #{i} needs a `locid` (0-63) or a `name`")
        for loc in resolve_markers([sel]):
            out[loc] = to
    return out


def apply_marker_renames(mes_body: str, renames: dict) -> str:
    """Return ``mes_body`` (a world text block 68 ``.mes``) with the marker labels in ``renames`` ({locId: name})
    applied to txid-0. Byte-preserving elsewhere (a single splice of the one message's text). A no-op (returns the
    input) if ``renames`` is empty or txid-0 is absent."""
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
        if 0 <= idx < len(entries):
            entries[idx] = name
    new_text = prefix + "\n".join(entries)
    return mes_body.replace(text, new_text, 1) if new_text != text else mes_body


def deploy_marker_renames(cfg_list, *, mod_folder: str, game=None, langs=None) -> list:
    """Write the marker-rename override into ``<mod>/FF9_Data/embeddedasset/text/<lang>/field/68.mes`` for each
    language (so it shadows the base world text). Returns the written ``Path`` list. RELAUNCH to apply. Raises
    ``ValueError`` on a bad config."""
    from pathlib import Path
    from .. import config, dialogue
    renames = resolve_renames(cfg_list)                                # validates
    if not renames:
        return []
    langs = list(langs) if langs else list(config.LANGS)
    root = config.find_mod_root(config.find_game_path(game), mod_folder)
    layout = config.ModLayout(root)
    written = []
    for lang in langs:
        base = dialogue.extract_field_mes(9000, lang=lang, game=game, zone_id=WORLD_TEXT_BLOCK)
        if not base:
            continue                                                   # this lang's block 68 not found -> skip
        out = apply_marker_renames(base, renames)
        dest = Path(layout.mes_path(lang, WORLD_TEXT_BLOCK))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(out, encoding="utf-8")
        written.append(dest)
    return written


# --------------------------------------------------------------------- the world-map image
# The big in-game map ("world_map_full_all") is a MOD-OVERRIDABLE loose PNG:
# WorldHUD.DisplayFullmapInfo -> AssetManager.SearchAssetOnDisc("EmbeddedAsset/UI/
# Sprites/world_map_full_all.png") searches the stacked FolderNames (Moguri ships
# its own HD copy), so a custom continent can be DRAWN ONTO THE MAP with no DLL.
# The projection is the ENGINE'S OWN (w_naviGetPos, ff9.cs:7019): the mapped world
# is exactly 1536x1280 units -> normalized (sx, syTop); the PNG adds only a
# decorative FRAME, detected structurally from the image (the letterbox bars +
# the drawn frame line); the world maps onto the frame's inner rect (visually
# verified against all 49 town anchors). The navipos marker fit (vx ~ wx*240/1536)
# independently confirms the extents. The disc-1 "mistcontinent" map is a crop that excludes the
# SW pocket, so only the all-world map is composited.

#: the engine's mapped world extents (w_naviGetPos, map 1)
WORLD_MAP_EXTENT = (1536.0, 1280.0)

MAP_SPRITE_REL = "FF9_Data/EmbeddedAsset/ui/sprites/world_map_full_all.png"


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


def _wrap_world(wx, wz):
    """Fold ABSOLUTE world coords into the engine's mapped 1536x1280 window (the
    navipos tx/ty use absolute/unwrapped units; the overworld wraps)."""
    return wx % WORLD_MAP_EXTENT[0], -((-wz) % WORLD_MAP_EXTENT[1])


def _load_active_world_map(mod_folder=None, *, game=None):
    """The ACTIVE all-world map image + its source: the highest-priority loose PNG
    across the stacked FolderNames (skipping ``mod_folder``'s own override -- the
    compositor must not composite over its own prior output), else the stock
    ``sharedassets2.assets`` texture."""
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
        p = gp / f / MAP_SPRITE_REL
        if not p.is_file():
            p2 = gp / f / MAP_SPRITE_REL.replace("ui/sprites", "UI/Sprites")
            p = p2 if p2.is_file() else p
        if p.is_file():
            return Image.open(p).convert("RGB"), str(p)
    import UnityPy
    env = UnityPy.load(str(gp / "x64/FF9_Data/sharedassets2.assets"))
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            d = obj.read()
            if str(getattr(d, "m_Name", "")) == "world_map_full_all":
                return d.image.convert("RGB"), "sharedassets2.assets"
    raise ValueError("world_map_full_all not found in any mod folder or sharedassets2")


def _detect_art_rect(im):
    """The map ART rectangle inside the PNG, detected structurally: the black
    letterbox bars end where column brightness rises, and the drawn FRAME line is
    the darkest column/row in the margin band just inside them. The world's
    1536x1280 extent maps onto this rect (visually verified: all 49 town anchors
    land on their continents, incl. Shimmering Island mid-sea)."""
    W, H = im.width, im.height
    g = im.convert("L")
    px = g.load()
    colm = [sum(px[x, y] for y in range(0, H, 4)) / (H // 4) for x in range(W)]
    rowm = [sum(px[x, y] for x in range(0, W, 4)) / (W // 4) for y in range(H)]
    lbar = next((x for x in range(W) if colm[x] > 40), 0)
    rbar = next((x for x in range(W - 1, -1, -1) if colm[x] > 40), W - 1)
    band = max(8, int(W * 0.06))
    x0 = min(range(lbar, min(lbar + band, W)), key=lambda x: colm[x])
    x1 = min(range(max(rbar - band, 0), rbar + 1), key=lambda x: colm[x])
    y0 = min(range(int(H * 0.015), int(H * 0.08)), key=lambda y: rowm[y])
    y1 = min(range(H - int(H * 0.08), H - int(H * 0.015)), key=lambda y: rowm[y])
    if x1 - x0 < W * 0.6 or y1 - y0 < H * 0.6:
        raise ValueError(f"world-map art-rect detection failed ({x0},{y0})-({x1},{y1}) "
                         f"-- an unexpected map image layout")
    aspect = (x1 - x0) / (y1 - y0)
    want = WORLD_MAP_EXTENT[0] / WORLD_MAP_EXTENT[1]
    if not (0.8 * want <= aspect <= 1.25 * want):
        raise ValueError(f"world-map art rect aspect {aspect:.2f} is far from the world's "
                         f"{want:.2f} -- an unexpected map image layout")
    return x0, y0, x1, y1


def _islet_anchors():
    """Interiors of REAL SMALL ISLANDS (world coords): the colour source for the
    painted land -- on the parchment-style chart, sea and land share the base
    tone and an islet is a slightly distinct fill + a darker drawn rim, so the
    fill must come from how the map itself draws ISLETS, not continent tops."""
    return [(480.0, -1120.0), (608.0, -1120.0), (12.0, -20.0)]


def composite_world_map(mod_folder: str, *, disc: int = 1, lod: str = "0_1", game=None,
                        dry_run: bool = False, verbose: bool = True) -> dict:
    """Draw the mod folder's deployed overworld LAND onto the all-world map image
    and ship it as the folder's own ``world_map_full_all.png`` override.

    Reads every ``Block[x][y] Terrain.ff9mesh`` under the folder's WorldMap tree,
    projects the terrain triangles through the engine's own map projection
    (frame-calibrated), and paints them in colours sampled from the map itself
    (fill = the median land colour at the real-town anchors; rim = that colour
    darkened). Data-derived end to end -- no hand art. RELAUNCH to see it."""
    import re as _re
    from PIL import ImageDraw
    from .. import config
    from . import mesh as M
    gp = config.find_game_path(game)
    im, src = _load_active_world_map(mod_folder, game=game)
    x0, y0, x1, y1 = _detect_art_rect(im)
    if verbose:
        print(f"  art rect ({x0},{y0})-({x1},{y1}) in {im.width}x{im.height}")
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

    root = gp / mod_folder / f"FF9_Data/WorldMap/Disc{disc}/{lod}"
    blocks = sorted(root.rglob("Block[[]*[]] Terrain.ff9mesh"))
    if not blocks:
        raise ValueError(f"{mod_folder} has no deployed WorldMap Terrain overrides to draw")
    draw = ImageDraw.Draw(im)
    n_tris = 0
    polys = []
    for p in blocks:
        m = _re.match(r"Block\[(\d+)\]\[(\d+)\]", p.name)
        bx, by = int(m.group(1)), int(m.group(2))
        bm = M.blockmesh_from_ff9mesh(p, disc=disc, x=bx, y=by, lod=lod, part="terrain")
        ox, oz = 64.0 * bx, -64.0 * by
        for tri in bm.tris:
            pts = [to_px(bm.verts[i][0] + ox, bm.verts[i][2] + oz) for i in tri]
            polys.append(pts)
            n_tris += 1
    for pts in polys:                       # rim pass: a 1px outline under the fills
        draw.polygon(pts, outline=rim)
    for pts in polys:
        draw.polygon(pts, fill=fill)
    out = gp / mod_folder / MAP_SPRITE_REL
    summary = {"source": src, "blocks": len(blocks), "tris": n_tris, "fill": fill,
               "art_rect": [x0, y0, x1, y1], "out": str(out), "dry_run": dry_run}
    if not dry_run:
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out)
    return summary
