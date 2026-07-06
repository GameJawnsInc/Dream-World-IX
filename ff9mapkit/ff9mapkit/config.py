"""Path resolution + the FF9/Memoria mod-folder layout.

This module is the single place that knows where things live on disk, replacing the
absolute paths hardcoded into a dozen of the original bespoke scripts. Game-path
resolution is, in priority order:

    1. an explicit path passed in code / via the CLI ``--game`` flag
    2. the ``FF9_GAME_PATH`` environment variable
    3. a ``game_path`` key in the user config file ``~/.ff9mapkit.toml``
    4. a small list of common Steam install locations (best-effort fallback)

Nothing here touches the game install; these are pure path computations. A ``ModLayout``
wraps a *mod root* (e.g. ``<game>/FF9CustomMap``) and yields the canonical sub-paths the
builder writes to. The same layout works whether the mod root is the live game folder or
a scratch/staging directory — that decoupling is what lets the builder be validated
offline (build into a temp dir, diff against the deployed assets).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - we require 3.11 but fail soft
    tomllib = None  # type: ignore[assignment]

# The seven shipped language folders. Field event scripts (.eb) and dialogue (.mes) are
# stored per-language; in practice the bytecode is identical across all seven and only the
# text differs, but we always write all seven so no locale loses the field.
LANGS: tuple[str, ...] = ("us", "uk", "fr", "gr", "it", "es", "jp")

# The mod folder Memoria reads first (highest override priority) on this project's install.
DEFAULT_MOD_FOLDER = "FF9CustomMap"

# User config file (TOML) — optional convenience so users set their game path once.
USER_CONFIG = Path.home() / ".ff9mapkit.toml"

# Best-effort fallbacks for a Steam install (Windows). Only used if nothing else resolves.
_COMMON_STEAM_PATHS = (
    r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX",
    r"C:\Program Files\Steam\steamapps\common\FINAL FANTASY IX",
    r"D:\SteamLibrary\steamapps\common\FINAL FANTASY IX",
)

# FF9 store identifiers -- used to read the per-game install path from the Windows registry (the SAME keys
# Memoria's patcher reads, so we resolve exactly the folder it patches -- correct even on a secondary drive
# / custom Steam library). Steam + GOG are the same Unity port with an identical on-disk layout; the
# Microsoft Store / Xbox Game Pass build is a different, non-Unity, DRM-locked package Memoria can't patch,
# so the detector never targets it.  Refs: Albeoris/Memoria Memoria.Patcher/GameInfo/.
_STEAM_APPID = "377840"
_GOG_GAMEID = "1375008492"
_FF9_DIRNAME = "FINAL FANTASY IX"


class ConfigError(RuntimeError):
    """Raised when a required path cannot be resolved or does not exist."""


def _read_user_config() -> dict:
    if tomllib is None or not USER_CONFIG.is_file():
        return {}
    try:
        with USER_CONFIG.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, ValueError):
        return {}


def save_game_path(game_path: str | os.PathLike) -> Path:
    """Persist ``game_path`` into the user config (``~/.ff9mapkit.toml``) so later commands resolve the
    install without ``--game`` / ``$FF9_GAME_PATH``. Surgical: rewrites only the ``game_path`` line and
    preserves any other keys/comments. Stores the path with forward slashes so the TOML basic string can
    never trip a backslash escape on Windows (``Path`` reads forward slashes fine). Returns the config path.
    """
    p = str(Path(game_path).resolve()).replace("\\", "/")
    line = f'game_path = "{p}"'
    existing = USER_CONFIG.read_text(encoding="utf-8") if USER_CONFIG.is_file() else ""
    if re.search(r"(?m)^[ \t]*game_path[ \t]*=", existing):
        new = re.sub(r"(?m)^[ \t]*game_path[ \t]*=.*$", line, existing)
    elif existing.strip():
        new = existing.rstrip("\n") + "\n" + line + "\n"
    else:
        new = line + "\n"
    USER_CONFIG.write_text(new, encoding="utf-8")
    return USER_CONFIG


def _is_ff9_root(p: Path) -> bool:
    """True if ``p`` is a real, MODDABLE FF9 install (Steam or GOG -- same layout). Keys off Memoria's own
    sentinel (``FF9_Launcher.exe``) plus ``StreamingAssets`` and the managed-DLL tree -- which also rejects
    the un-moddable Microsoft Store build (no launcher / no Managed dir) and stale empty folders."""
    try:
        return ((p / "FF9_Launcher.exe").is_file()
                and (p / "StreamingAssets").is_dir()
                and ((p / "x64" / "FF9_Data" / "Managed").is_dir()
                     or (p / "x86" / "FF9_Data" / "Managed").is_dir()))
    except OSError:
        return False


def _reg_str(hive, subkey: str, value: str) -> str | None:
    """Read one registry string value, trying the 64-bit THEN 32-bit view (FF9's keys live under
    ``WOW6432Node`` on 64-bit Windows). Windows-only; returns None elsewhere or if the key/value is absent."""
    if os.name != "nt":
        return None
    import winreg  # noqa: PLC0415 - Windows-only, lazy
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKeyEx(hive, subkey, 0, winreg.KEY_READ | view) as key:
                data, _ = winreg.QueryValueEx(key, value)
                if data:
                    return str(data)
        except OSError:
            continue
    return None


def _registry_candidates() -> list[Path]:
    """FF9 roots from the per-game Steam + GOG registry keys (the exact keys Memoria reads). These point at
    the ACTUAL install dir, so they find FF9 even on a secondary drive or a custom-named Steam library."""
    if os.name != "nt":
        return []
    import winreg  # noqa: PLC0415
    out: list[Path] = []
    steam = _reg_str(winreg.HKEY_LOCAL_MACHINE,
                     rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App {_STEAM_APPID}",
                     "InstallLocation")
    if steam:
        out.append(Path(steam))
    gog = _reg_str(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\GOG.com\Games\{_GOG_GAMEID}", "path")
    if gog:
        out.append(Path(gog))
    return out


def _parse_vdf_library_paths(text: str) -> list[str]:
    """Library-folder paths from a Steam ``libraryfolders.vdf`` -- handles both the old ``"1" "<path>"`` and
    the new ``"path" "<path>"`` schemas (and ignores the new schema's ``"apps"`` appid->buildid map). The
    file doubles its backslashes, so they're unescaped here."""
    keyed = re.findall(r'"path"\s+"([^"]+)"', text) if '"path"' in text \
        else re.findall(r'"\d+"\s+"([^"]+)"', text)
    return [p.replace("\\\\", "\\") for p in keyed]


def _steam_library_candidates() -> list[Path]:
    """FF9 under every Steam library (a fallback when the per-game Uninstall key is missing): locate Steam
    via the registry, parse ``libraryfolders.vdf``, and join ``steamapps/common/FINAL FANTASY IX``."""
    if os.name != "nt":
        return []
    import winreg  # noqa: PLC0415
    steam = (_reg_str(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath")
             or _reg_str(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"))
    if not steam:
        return []
    steam_dir = Path(steam)
    out: list[Path] = [steam_dir / "steamapps" / "common" / _FF9_DIRNAME]
    for vdf in (steam_dir / "steamapps" / "libraryfolders.vdf", steam_dir / "config" / "libraryfolders.vdf"):
        try:
            text = vdf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lib in _parse_vdf_library_paths(text):
            out.append(Path(lib) / "steamapps" / "common" / _FF9_DIRNAME)
    return out


def _fallback_candidates() -> list[Path]:
    """Last-resort default install folders (Steam + GOG) if registry/library lookups don't resolve."""
    gog = [Path(b) / _FF9_DIRNAME for b in
           (r"C:\GOG Games", r"D:\GOG Games", r"C:\Program Files (x86)\GOG Galaxy\Games")]
    return [Path(p) for p in _COMMON_STEAM_PATHS] + gog


def find_game_path(explicit: str | os.PathLike | None = None) -> Path:
    """Resolve the Final Fantasy IX install folder.

    Order: explicit arg > ``$FF9_GAME_PATH`` > ``~/.ff9mapkit.toml`` (``game_path``) > auto-detect. The
    auto-detector mirrors Memoria's: the per-game Steam + GOG registry keys, then a Steam-library scan, then
    the common default folders. Explicit/env/config paths are trusted if they exist; auto-detected ones are
    validated as a real, moddable FF9 install (which also skips the un-moddable Microsoft Store build).
    Raises ConfigError with actionable guidance if nothing resolves.
    """
    # 1) user-specified -- trusted on existence
    for c in (Path(p) for p in (explicit, os.environ.get("FF9_GAME_PATH"),
                                _read_user_config().get("game_path")) if p):
        if c.is_dir():
            return c.resolve()

    # 2) auto-detect Steam + GOG, validated as a real install; de-dupe by resolved path
    seen: set[Path] = set()
    for c in _registry_candidates() + _steam_library_candidates() + _fallback_candidates():
        try:
            rc = c.resolve()
        except OSError:
            continue
        if rc in seen:
            continue
        seen.add(rc)
        if _is_ff9_root(c):
            return rc

    raise ConfigError(
        "Could not locate the Final Fantasy IX install folder (checked Steam + GOG via the registry,\n"
        "the Steam libraries, and the common install paths).\n"
        "Set it one of these ways:\n"
        "  - pass --game \"<path>\" on the command line\n"
        "  - export FF9_GAME_PATH=\"<path>\"\n"
        f"  - add  game_path = \"<path>\"  to {USER_CONFIG}\n"
        "The folder should contain FF9_Launcher.exe and a StreamingAssets directory.\n"
        "(The Microsoft Store / Xbox Game Pass version is not moddable -- use the Steam or GOG release.)"
    )


def find_mod_root(game_path: Path, mod_folder: str = DEFAULT_MOD_FOLDER) -> Path:
    """The mod root inside the game install (created by the builder if absent)."""
    return (game_path / mod_folder).resolve()


@dataclass(frozen=True)
class ModLayout:
    """Canonical sub-paths within a Memoria mod root.

    `root` may be the live ``<game>/FF9CustomMap`` or any staging directory. All methods are
    pure path joins (they neither read nor create anything) except ``ensure_dirs``.
    """

    root: Path

    # --- top-level registration files Memoria reads from the mod root ---
    @property
    def dictionary_patch(self) -> Path:
        return self.root / "DictionaryPatch.txt"

    @property
    def battle_patch(self) -> Path:
        return self.root / "BattlePatch.txt"

    @property
    def text_patch(self) -> Path:
        """Item/ability/card NAME + DESCRIPTION overrides (``TextPatch.txt``, a ``>DATABASE`` find/replace
        patch -- ``Memoria.TextPatcher``). A per-mod-folder drop-in like the dictionary/battle patches,
        read once at ``DataPatchers.Initialize`` -> a text change needs a RELAUNCH (not F6 Reload)."""
        return self.root / "TextPatch.txt"

    @property
    def mod_description(self) -> Path:
        return self.root / "ModDescription.xml"

    # --- field background scene (camera/overlays + walkmesh + PNGs) ---
    @property
    def fieldmaps_dir(self) -> Path:
        return self.root / "StreamingAssets" / "assets" / "resources" / "FieldMaps"

    def fieldmap_dir(self, fbg_name: str) -> Path:
        """Folder holding ``<fbg>.bgx``, ``<fbg>.bgi.bytes`` and the overlay PNGs."""
        return self.fieldmaps_dir / fbg_name

    # --- loose 3D model override / MINT: the engine probes this before the bundle (ModelFactory) ---
    def model_dir(self, type_int: int, geo_id: int) -> Path:
        """``…/Assets/Resources/Models/<typeInt>/<id>/`` — holds ``<id>.fbx`` + its ``<stem>.png`` textures.
        The folder ``ModelFactory.CreateModel`` probes on disc before the bundle: an OVERRIDE when ``id`` is
        a real GEO id, a MINT when it's a new id registered via a ``3DModel <id> <name>`` DictionaryPatch
        line. Casing matches ``_battle_resources`` (capitalized Assets/Resources), verbatim-proven in-game."""
        return self.root / "StreamingAssets" / "Assets" / "Resources" / "Models" / str(type_int) / str(geo_id)

    # --- battle background (BBG): a loose FBX + image#.png the engine loads instead of the bundle ---
    @property
    def battlemap_all_dir(self) -> Path:
        # NOTE: the capitalized "Assets/Resources/BattleMap" segments are VERBATIM -- this exact casing
        # round-tripped in-game (2026-06-09); do NOT lowercase it to match fieldmaps_dir above.
        return (self.root / "StreamingAssets" / "Assets" / "Resources"
                / "BattleMap" / "BattleModel" / "battleMap_all")

    def battlemap_dir(self, bbg: str) -> Path:
        """Folder holding ``<bbg>.fbx`` + its ``image#.png`` textures (the loose-FBX override slot)."""
        return self.battlemap_all_dir / bbg

    # --- minted battle SCENE assets (tier c). Paths VERBATIM-proven in-game (C1/C2, 2026-06-09);
    #     casing matches battlemap_all_dir above (capitalized BattleMap), not the lowercase field tree. ---
    @property
    def _battle_resources(self) -> Path:
        return self.root / "StreamingAssets" / "Assets" / "Resources"

    def battle_scene_dir(self, scene_name: str) -> Path:
        """``…/BattleMap/BattleScene/EVT_BATTLE_<NAME>`` — holds ``dbfile0000.raw16.bytes`` (gameplay) +
        ``<scene_id>.raw17.bytes`` (btlseq + camera)."""
        return self._battle_resources / "BattleMap" / "BattleScene" / f"EVT_BATTLE_{scene_name}"

    @property
    def battle_info_dir(self) -> Path:
        """``…/BattleMap/BattleInfo`` — holds ``INB_B<N>.inb.bytes`` (BBGINFO: bbgnumber + anim flags)."""
        return self._battle_resources / "BattleMap" / "BattleInfo"

    def battle_eb_path(self, lang: str, scene_name: str) -> Path:
        """``…/CommonAsset/EventEngine/EventBinary/Battle/<lang>/EVT_BATTLE_<NAME>.eb.bytes`` (battle AI)."""
        return (self._battle_resources / "CommonAsset" / "EventEngine" / "EventBinary"
                / "Battle" / lang / f"EVT_BATTLE_{scene_name}.eb.bytes")

    def battle_text_dir(self, lang: str) -> Path:
        """``<root>/FF9_Data/embeddedasset/text/<lang>/battle`` — holds ``<scene_id>.mes`` (battle text)."""
        return self.root / "FF9_Data" / "embeddedasset" / "text" / lang / "battle"

    # --- field event scripts (.eb), one folder per language ---
    @property
    def eventbinary_field_dir(self) -> Path:
        return (
            self.root
            / "StreamingAssets" / "assets" / "resources" / "commonasset"
            / "eventengine" / "eventbinary" / "field"
        )

    def eb_path(self, lang: str, evt_name: str) -> Path:
        """``<root>/.../eventbinary/field/<lang>/<evt_name>`` (evt_name includes .eb.bytes)."""
        return self.eventbinary_field_dir / lang / evt_name

    def mapconfig_path(self, evt_name: str) -> Path:
        """``<root>/.../commonasset/mapconfigdata/<evt_name>.bytes`` -- the field's 3D-model LIGHTING config
        (per-floor lights + shadows + per-object colors), loaded at field setup by the SAME event name as
        the ``.eb`` (``MapConfiguration.LoadMapConfigData`` / ``fldmcf.cs``). Not per-language."""
        return (self.root / "StreamingAssets" / "assets" / "resources" / "commonasset"
                / "mapconfigdata" / f"{evt_name}.bytes")

    # --- dialogue text (.mes), one folder per language ---
    def text_field_dir(self, lang: str) -> Path:
        return self.root / "FF9_Data" / "embeddedasset" / "text" / lang / "field"

    def mes_path(self, lang: str, mes_id: int) -> Path:
        return self.text_field_dir(lang) / f"{mes_id}.mes"

    # --- item / character DATA CSVs (mod-global; the engine merges/overrides them across FolderNames at
    #     new-game). Written at the mod-write stage from the entry field's [start_inventory]/[equipment]. ---
    @property
    def initial_items_csv(self) -> Path:
        """The new-game starting bag (``Data/Items/InitialItems.csv``). HIGHEST-priority-wins -> a mod must
        write the FULL bag, and a stacked folder SHADOWS it (lint)."""
        return self.root / "StreamingAssets" / "Data" / "Items" / "InitialItems.csv"

    @property
    def default_equipment_csv(self) -> Path:
        """Per-character starting equipment (``Data/Characters/DefaultEquipment.csv``). MERGED low->high by
        the engine -> a partial delta (only the characters you change) works."""
        return self.root / "StreamingAssets" / "Data" / "Characters" / "DefaultEquipment.csv"

    @property
    def shop_items_csv(self) -> Path:
        """Custom shop inventories (``Data/Items/ShopItems.csv``). MERGED by id low->high by the engine -> a
        partial delta (only the custom shops, ids >= 32) works; the base supplies shops 0-31."""
        return self.root / "StreamingAssets" / "Data" / "Items" / "ShopItems.csv"

    @property
    def synthesis_csv(self) -> Path:
        """Custom synthesis recipes (``Data/Items/Synthesis.csv`` = FF9MIX_DATA: Shops/Price/Result/Ingredients).
        MERGED by id low->high (whole-row, ff9mix.LoadSynthesis) -> a partial delta works; the kit MINTS recipe
        ids above the base max so it only ADDS recipes. A shop id opens as Synthesis iff it is absent from
        ShopItems.csv (ff9buy.FF9Buy_GetType); a recipe shows at every shop id in its ``Shops`` list."""
        return self.root / "StreamingAssets" / "Data" / "Items" / "Synthesis.csv"

    @property
    def weapons_csv(self) -> Path:
        """Weapon combat data (``Data/Items/Weapons.csv``: Power/Elements/Category...). MERGED by id low->high
        (WHOLE-ROW replace) -> a partial delta (the base header + only the rows you tune) works."""
        return self.root / "StreamingAssets" / "Data" / "Items" / "Weapons.csv"

    @property
    def armors_csv(self) -> Path:
        """Armor defence data (``Data/Items/Armors.csv``: P.Def/P.Eva/M.Def/M.Eva). MERGED by id low->high
        (whole-row replace) -> a partial delta works."""
        return self.root / "StreamingAssets" / "Data" / "Items" / "Armors.csv"

    @property
    def items_csv(self) -> Path:
        """Item info (``Data/Items/Items.csv``: Price/SellingPrice/equip...). MERGED by id low->high (whole-row
        replace) -> a partial delta works. (NOT InitialItems.csv -- that's the new-game bag, highest-wins.)"""
        return self.root / "StreamingAssets" / "Data" / "Items" / "Items.csv"

    @property
    def stats_csv(self) -> Path:
        """Equip stat bonuses + elemental affinity (``Data/Items/Stats.csv`` = ItemStats, keyed by BonusId).
        MERGED by id low->high (whole-row replace, ff9equip.cs:26) -> a partial delta works; new minted bonus
        rows just add entries. The input the level-up stat-growth accumulator reads (ff9play.cs:302-305)."""
        return self.root / "StreamingAssets" / "Data" / "Items" / "Stats.csv"

    @property
    def item_effects_csv(self) -> Path:
        """Consumable use-effects (``Data/Items/ItemEffects.csv`` = ItemEffect, keyed by EffectId). MERGED by id
        low->high (whole-row replace, ff9item.LoadItemEffects) -> a partial delta works; EffectId is 1:1 with a
        usable item (no shared Empty row), so a row is edited in place. Power/Rate/Element/Status/Dead are the
        gameplay knobs; the ScriptId (the behaviour) stays."""
        return self.root / "StreamingAssets" / "Data" / "Items" / "ItemEffects.csv"

    @property
    def actions_csv(self) -> Path:
        """Shared player abilities (``Data/Battle/Actions.csv``). MERGED by id low->high (whole-row replace) ->
        a partial delta (only the abilities you change) works; the base supplies the other 192 rows."""
        return self.root / "StreamingAssets" / "Data" / "Battle" / "Actions.csv"

    @property
    def status_data_csv(self) -> Path:
        """Status definitions (``Data/Battle/StatusData.csv``). MERGED by id low->high (whole-row replace) ->
        a partial delta (only the statuses you change) works; the base supplies the other 33 rows."""
        return self.root / "StreamingAssets" / "Data" / "Battle" / "StatusData.csv"

    @property
    def status_sets_csv(self) -> Path:
        """Named multi-status BUNDLES (``Data/Battle/StatusSets.csv``) an action's ``status_index`` points at.
        MERGED by id low->high -> a partial works (ids 0-38 are the base sets; use >=39 for a custom one)."""
        return self.root / "StreamingAssets" / "Data" / "Battle" / "StatusSets.csv"

    @property
    def magic_sword_sets_csv(self) -> Path:
        """Combo-unlock sets (``Data/Battle/MagicSwordSets.csv``): a Supporter's abilities unlock a Beneficiary's
        (Vivi -> Steiner's Magic Sword). MERGED by id low->high -> a partial (only the author's sets) works."""
        return self.root / "StreamingAssets" / "Data" / "Battle" / "MagicSwordSets.csv"

    @property
    def base_stats_csv(self) -> Path:
        """Per-character base combat stats (``Data/Characters/BaseStats.csv``). MERGED by CharacterId low->high
        -> a partial delta (only the characters you change) works; the base supplies the other 11."""
        return self.root / "StreamingAssets" / "Data" / "Characters" / "BaseStats.csv"

    @property
    def character_parameters_csv(self) -> Path:
        """Per-character identity (``Data/Characters/CharacterParameters.csv``): row / category / menu-preset /
        equip-set. MERGED by CharacterId low->high -> a partial delta works (the base supplies the rest)."""
        return self.root / "StreamingAssets" / "Data" / "Characters" / "CharacterParameters.csv"

    @property
    def command_sets_csv(self) -> Path:
        """Per-character battle-menu command LAYOUTS (``Data/Characters/CommandSets.csv``), keyed by preset 0-19.
        MERGED low->high -> a partial delta (only the presets you re-point) works."""
        return self.root / "StreamingAssets" / "Data" / "Characters" / "CommandSets.csv"

    @property
    def battle_parameters_csv(self) -> Path:
        """Per-character COSMETIC battle data (``Data/Characters/BattleParameters.csv``), keyed by
        CharacterSerialNumber: the battle ModelId + 34 animation names + avatar sprite + bones. MERGED per-serial
        low->high (``EnumerateCsvFromLowToHigh``) -> a partial delta works (add a NEW serial >=19 that reuses a
        donor's anims but a custom ModelId -> a custom battle look for a 13th character). NOT combat stats
        (those are BaseStats.csv)."""
        return self.root / "StreamingAssets" / "Data" / "Characters" / "BattleParameters.csv"

    @property
    def leveling_csv(self) -> Path:
        """The 99-row growth curve (``Data/Characters/Leveling.csv``). HIGHEST-priority-wins (WHOLE-FILE, gated at
        >=99 rows) -> a mod must emit the FULL 99-row file, and a stacked folder SHADOWS it (lint)."""
        return self.root / "StreamingAssets" / "Data" / "Characters" / "Leveling.csv"

    @property
    def ability_gems_csv(self) -> Path:
        """Support-ability gem COSTS (``Data/Characters/Abilities/AbilityGems.csv``). MERGED per-SupportAbility
        low->high -> a partial delta (only the abilities you re-cost) works; the base supplies the other 63."""
        return self.root / "StreamingAssets" / "Data" / "Characters" / "Abilities" / "AbilityGems.csv"

    def abilities_csv(self, preset_name: str) -> Path:
        """A per-preset learn list (``Data/Characters/Abilities/<CharacterPresetId>.csv``, e.g. ``Vivi.csv``).
        WHOLE-FILE highest-priority-wins -> the kit re-emits the complete list. A METHOD (not a property): the
        Abilities learn lists are a FILE SET (one per preset), like ``battle_eb_path(lang, scene)``."""
        return self.root / "StreamingAssets" / "Data" / "Characters" / "Abilities" / f"{preset_name}.csv"

    @property
    def ability_features_txt(self) -> Path:
        """The ability-EFFECT DSL (``Data/Characters/Abilities/AbilityFeatures.txt``). MERGED per-ability
        low->high (accumulator) -> a partial file (only the abilities you change) works; the base supplies the
        rest. Authored from ``[[ability_feature]]`` (:mod:`battle.abilityfeatures`)."""
        return self.root / "StreamingAssets" / "Data" / "Characters" / "Abilities" / "AbilityFeatures.txt"

    def ensure_dirs(self, fbg_name: str | None = None, *, bbg: str | None = None,
                    langs: tuple[str, ...] = LANGS) -> None:
        """Create the directory skeleton a field (and/or battle-map) write needs."""
        self.root.mkdir(parents=True, exist_ok=True)
        if fbg_name:
            self.fieldmap_dir(fbg_name).mkdir(parents=True, exist_ok=True)
        if bbg:
            self.battlemap_dir(bbg).mkdir(parents=True, exist_ok=True)
        for lang in langs:
            (self.eventbinary_field_dir / lang).mkdir(parents=True, exist_ok=True)
            self.text_field_dir(lang).mkdir(parents=True, exist_ok=True)


# ---- FBG (background scene) naming -------------------------------------------------------

MIN_AREA = 10  # the area id must be >= 10: the FieldScene parser builds "FBG_N"+area with no
#                zero-padding and the asset loader reads exactly 2 chars, so 00-09 black-screen.


def fbg_name(area: int, name: str) -> str:
    """Build the canonical background-scene folder/key name, e.g. (11, 'HUT_EXT') -> 'FBG_N11_HUT_EXT'.

    Raises ConfigError for single-digit areas (the zero-padding gotcha from the field plumbing).
    """
    if area < MIN_AREA:
        raise ConfigError(
            f"area id must be >= {MIN_AREA} (got {area}). The FieldScene directive builds the "
            f"background name as 'FBG_N{{area}}' with no zero-padding and the loader reads exactly "
            f"two characters, so single-digit areas (00-09) fail to resolve and black-screen."
        )
    return f"FBG_N{area}_{name}"
