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


def find_game_path(explicit: str | os.PathLike | None = None) -> Path:
    """Resolve the Final Fantasy IX install folder.

    Order: explicit arg > $FF9_GAME_PATH > ~/.ff9mapkit.toml(game_path) > common Steam dirs.
    Raises ConfigError with actionable guidance if none of them point at a real folder.
    """
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("FF9_GAME_PATH")
    if env:
        candidates.append(Path(env))
    cfg = _read_user_config().get("game_path")
    if cfg:
        candidates.append(Path(cfg))
    candidates.extend(Path(p) for p in _COMMON_STEAM_PATHS)

    for c in candidates:
        if c.is_dir():
            return c.resolve()

    raise ConfigError(
        "Could not locate the Final Fantasy IX install folder.\n"
        "Set it one of these ways:\n"
        "  - pass --game \"<path>\" on the command line\n"
        "  - export FF9_GAME_PATH=\"<path>\"\n"
        f"  - add  game_path = \"<path>\"  to {USER_CONFIG}\n"
        "The folder should contain FF9_Launcher.exe and a StreamingAssets directory."
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
    def mod_description(self) -> Path:
        return self.root / "ModDescription.xml"

    # --- field background scene (camera/overlays + walkmesh + PNGs) ---
    @property
    def fieldmaps_dir(self) -> Path:
        return self.root / "StreamingAssets" / "assets" / "resources" / "FieldMaps"

    def fieldmap_dir(self, fbg_name: str) -> Path:
        """Folder holding ``<fbg>.bgx``, ``<fbg>.bgi.bytes`` and the overlay PNGs."""
        return self.fieldmaps_dir / fbg_name

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
