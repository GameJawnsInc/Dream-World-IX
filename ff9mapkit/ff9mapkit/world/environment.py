"""Overworld WEATHER / environment authoring -- emit Memoria's ``Environment.txt`` (no DLL).

Memoria's ``WorldConfiguration.PatchWorldEnvironment`` (``WorldConfiguration.cs:93``) reads a per-mod-folder
``Environment.txt`` -- stacked over ``Configuration.Mod.FolderNames`` -- and lets a mod override the overworld's
mist / rain / weather-light / effects / place alternate-forms, plus the continent-title banner rect. It parses
line tokens ``^(Place|Effect|Mist|Disc4|Rain|Light|Title)\\s+(.*)$``; each ``[Condition=<expr>]`` is an **NCalc**
boolean (so ``true`` / ``false`` force on / off), and a modifier is active if ANY of its conditions is true.

This module turns a small declarative config into that file. The file lands at
``<modFolder>/StreamingAssets/Data/World/Environment.txt`` (``DataResources.World.EnvironmentPatchFile``); the
engine re-reads it when the overworld (re)loads. Grammar (byte-for-byte against the engine parser):

  Mist  [Condition=<expr>]                 -- force the Mist-Continent mist on/off (Disc4 the same, for disc-4 forms)
  Rain  Add [Position=(x,z)] [RadiusLarge=N] [RadiusSmall=N] [RainSpeed=N] [RainStrength=N] [Condition=<expr>]
  Light Add [Position=(x,z)] [Radius=N] [Light=N] [Condition=<expr>]
  Effect <WorldEffect> [Condition=<expr>]  -- force a named world effect (e.g. AlexandriaWaterfall) on/off
  Place  <WorldPlace>  [Condition=<expr>]  -- force a place's alternate form (e.g. Alexandria destroyed)

``[Position]`` / radii are WORLD units (the engine multiplies by 256 via ``ff9.S``). The ``Title`` token (banner
rect/timing) is intentionally omitted from v1 -- it's continent-banner tuning, not weather.
"""
from __future__ import annotations

# The engine mod path for the file (relative to a mod folder root): DataResources.World, PureDataDirectory="Data/".
ENVIRONMENT_REL_PATH = "StreamingAssets/Data/World/Environment.txt"

# Valid enum names (Memoria/World/WorldPlace.cs + WorldEffect.cs) -- for by-name validation.
WORLD_PLACES = {
    "Dummy", "AlexandriaHarbour", "Alexandria", "EvilForest", "IceCavern_Bottom", "QuanDwelling", "Treno",
    "SouthGate_NorthBottom", "SouthGate_NorthEast", "SouthGate_NorthWest", "SouthGate_SouthTop",
    "SouthGate_SouthBottom", "IceCavern_Top", "ObservatoryMountain", "Dali", "NorthGate_East", "NorthGate_West",
    "GizamalukeGrotto_North", "Burmecia", "Cleyra", "ChocoboForest", "GizamalukeGrotto_South", "QuMarsh_Mist",
    "PinnacleRocks", "LindblumDragonGate", "Lindblum", "LindblumHarbour", "EarthShrine", "DesertPalace_Cave",
    "MognetCentral", "QuMarsh_Outer", "BlackMageVillage", "FossilRoo", "CondePetie", "MadainSari",
    "MountainPath_North", "MountainPath_West", "IifaTree", "ChocoboLagoon", "WindShrine", "Daguerreo",
    "QuMarsh_Archipelago", "Oeilvert", "LandingSite", "WaterShrine", "IpsenCastle", "QuMarsh_Forgotten",
    "ShimmeringIsland", "EstoGaza", "FireShrine", "ChocoboParadise", "DesertPalace_SandPit", "SandPit",
    "Memoria_FirstTime", "Memoria", "ChocoboAirGarden_Alexandria", "ChocoboAirGarden_Peninsula",
    "ChocoboAirGarden_Canyon", "ChocoboAirGarden_Archipelago", "ChocoboAirGarden_Ocean", "GizamalukeGrotto_Top",
    "SouthGate_Gate", "NorthGate_Gate", "Bridge", "QuanDwelling_Platform",
}
WORLD_EFFECTS = {
    "Unknown0", "FireShrine", "SandPit", "SandStorm", "AlexandriaWaterfall", "Memoria", "Windmill",
    "Unknown7", "Unknown8", "WaterShrine", "WindShrine", "Unknown11",
}


def _cond(value) -> str:
    """A ``[Condition=<expr>]`` payload: ``True`` -> ``true``, ``False`` -> ``false``, a str -> the NCalc expr."""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value).strip()


def _pos(p) -> str:
    return "(" + ",".join(str(int(c)) for c in p) + ")"


def validate_environment(cfg: dict) -> list[str]:
    """Human-readable problems with a ``[world_environment]`` config (empty list = clean)."""
    problems: list[str] = []
    if not isinstance(cfg, dict):
        return ["[world_environment] must be a table"]
    for key in ("mist", "disc4"):
        v = cfg.get(key)
        if v is not None and not isinstance(v, (bool, str)):
            problems.append(f"[world_environment] {key} must be true/false or an NCalc condition string (got {v!r})")
    for kind, keyset in (("rain", None), ("light", None)):
        for i, item in enumerate(cfg.get(kind, []) or []):
            if not isinstance(item, dict):
                problems.append(f"[[world_environment.{kind}]] #{i} must be a table"); continue
            pos = item.get("position")
            if pos is None or not isinstance(pos, (list, tuple)) or len(pos) not in (2, 3) \
                    or any(isinstance(c, bool) or not isinstance(c, (int, float)) for c in pos):
                problems.append(f"[[world_environment.{kind}]] #{i} needs position = [x, z] (or [x, y, z]) world coords")
            for nk in (("radius_large", "radius_small", "speed", "strength") if kind == "rain"
                       else ("radius", "light")):
                nv = item.get(nk)
                if nv is not None and (isinstance(nv, bool) or not isinstance(nv, int)):
                    problems.append(f"[[world_environment.{kind}]] #{i} {nk} must be an integer (got {nv!r})")
    for kind, keyset in (("effect", WORLD_EFFECTS), ("place", WORLD_PLACES)):
        for i, item in enumerate(cfg.get(kind, []) or []):
            if not isinstance(item, dict) or "name" not in item:
                problems.append(f"[[world_environment.{kind}]] #{i} needs a `name` ({kind} enum)"); continue
            if item["name"] not in keyset:
                problems.append(f"[[world_environment.{kind}]] #{i} unknown {kind} name {item['name']!r}")
            on, cond = item.get("on"), item.get("condition")
            if on is not None and not isinstance(on, bool):
                problems.append(f"[[world_environment.{kind}]] #{i} `on` must be true/false (got {on!r})")
            if cond is not None and not isinstance(cond, str):
                problems.append(f"[[world_environment.{kind}]] #{i} `condition` must be an NCalc string")
    return problems


def build_environment_txt(cfg: dict) -> str:
    """Render a ``[world_environment]`` config to the ``Environment.txt`` text (deterministic line order).

    Raises ``ValueError`` if the config is invalid (call :func:`validate_environment` first for friendly errors)."""
    problems = validate_environment(cfg)
    if problems:
        raise ValueError("; ".join(problems))
    lines: list[str] = ["# ff9mapkit: overworld environment overrides (Memoria WorldConfiguration.Environment.txt)"]
    if "mist" in cfg and cfg["mist"] is not None:
        lines.append(f"Mist [Condition={_cond(cfg['mist'])}]")
    if "disc4" in cfg and cfg["disc4"] is not None:
        lines.append(f"Disc4 [Condition={_cond(cfg['disc4'])}]")
    for r in cfg.get("rain", []) or []:
        parts = ["Rain Add", f"[Position={_pos(r['position'])}]"]
        for key, tok in (("radius_large", "RadiusLarge"), ("radius_small", "RadiusSmall"),
                         ("speed", "RainSpeed"), ("strength", "RainStrength")):
            if r.get(key) is not None:
                parts.append(f"[{tok}={int(r[key])}]")
        if r.get("condition") is not None:
            parts.append(f"[Condition={_cond(r['condition'])}]")
        lines.append(" ".join(parts))
    for lt in cfg.get("light", []) or []:
        parts = ["Light Add", f"[Position={_pos(lt['position'])}]"]
        for key, tok in (("radius", "Radius"), ("light", "Light")):
            if lt.get(key) is not None:
                parts.append(f"[{tok}={int(lt[key])}]")
        if lt.get("condition") is not None:
            parts.append(f"[Condition={_cond(lt['condition'])}]")
        lines.append(" ".join(parts))
    for kind, tok in (("effect", "Effect"), ("place", "Place")):
        for it in cfg.get(kind, []) or []:
            cond = it["condition"] if it.get("condition") is not None else it.get("on", True)
            lines.append(f"{tok} {it['name']} [Condition={_cond(cond)}]")
    return "\n".join(lines) + "\n"


def write_environment(cfg: dict, *, mod_folder: str, game=None):
    """Render + write ``Environment.txt`` into ``<game>/<mod_folder>/StreamingAssets/Data/World/``. Returns the
    written :class:`pathlib.Path`. RELAUNCH (or re-enter the overworld) to apply; the mod folder must be in
    ``Memoria.ini [Mod] FolderNames``. Raises ``ValueError`` on an invalid config."""
    from pathlib import Path
    from .. import config
    txt = build_environment_txt(cfg)                       # validates
    root = config.find_mod_root(config.find_game_path(game), mod_folder)
    dest = Path(root) / ENVIRONMENT_REL_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(txt, encoding="utf-8")
    return dest
