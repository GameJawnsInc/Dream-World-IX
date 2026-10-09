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

STACKING (terrain study defect 20). The engine reads the base file, then every FolderNames folder from the LOWEST
priority to the highest (``WorldConfiguration.cs:105-113``), and conditions for one key ACCUMULATE: two folders that
set ``Place Cleyra`` OR their conditions. So by default each ``Place``/``Effect``/``Mist``/``Disc4`` line is preceded
by its ``Clear`` (``:400-410``, ``:431-435``), and this folder's condition REPLACES what lower folders set for that key;
a higher folder is read later and still ORs (or clears) on top. ``stack = "combine"`` emits no ``Clear``. Rain and
light zones are lists and always add. Memoria's shipped header says ``Clean``; the parser reads only ``Clear``, so a
``Clean`` line does nothing (:func:`stack_report` flags one in any stacked folder).
"""
from __future__ import annotations

from .forms import PLACE_CELLS

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
# The only places the engine ever asks about (``ff9.w_worldChangeBlockSet``, ff9.cs:9153-9208, and two effects in
# ``WorldConfiguration.UseWorldEffect``): the 9 with an alternate block form, over 26 cells (``forms.PLACE_CELLS``). A
# ``Place`` line for any other WorldPlace name parses and does nothing (terrain study defect 20).
FORM_PLACES = tuple(PLACE_CELLS)
STACK_MODES = ("replace", "combine")
_TOKEN_RE = r"^(Place|Effect|Mist|Disc4|Rain|Light|Title)\s+(.*)$"      # WorldConfiguration.cs:370
_ARG_RE = r"\s*(\[[^\]]*\]|[^\]][^\s]*)"                                 # :373


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
    if cfg.get("stack", "replace") not in STACK_MODES:
        problems.append(f"[world_environment] stack must be one of {list(STACK_MODES)} (got {cfg.get('stack')!r})")
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
        seen: set = set()
        for i, item in enumerate(cfg.get(kind, []) or []):
            if not isinstance(item, dict) or "name" not in item:
                problems.append(f"[[world_environment.{kind}]] #{i} needs a `name` ({kind} enum)"); continue
            if item["name"] not in keyset:
                problems.append(f"[[world_environment.{kind}]] #{i} unknown {kind} name {item['name']!r}")
            elif kind == "place" and item["name"] not in FORM_PLACES:
                problems.append(f"[[world_environment.place]] #{i} {item['name']!r} has no alternate form, so the "
                                f"engine never reads its condition; only these 9 places switch: {', '.join(FORM_PLACES)}")
            if item["name"] in seen:
                problems.append(f"[[world_environment.{kind}]] #{i} {item['name']!r} is listed twice; give it one "
                                f"condition (join two with ||)")
            seen.add(item["name"])
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
    replace = cfg.get("stack", "replace") == "replace"
    lines: list[str] = ["# ff9mapkit: overworld environment overrides (Memoria WorldConfiguration.Environment.txt)"]
    if replace:
        lines.append("# each Clear drops what lower-priority mod folders set for that key, so the line after it replaces "
                     "them (stack = \"combine\" ORs instead)")

    def keyed(head: str, cond) -> None:
        if replace:
            lines.append(f"{head} Clear")
        lines.append(f"{head} [Condition={_cond(cond)}]")
    if "mist" in cfg and cfg["mist"] is not None:
        keyed("Mist", cfg["mist"])
    if "disc4" in cfg and cfg["disc4"] is not None:
        keyed("Disc4", cfg["disc4"])
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
            keyed(f"{tok} {it['name']}", it["condition"] if it.get("condition") is not None else it.get("on", True))
    return "\n".join(lines) + "\n"


def _keys(txt: str) -> list:
    """``[(key, line, clean)]`` for every line of an ``Environment.txt`` the engine parses that touches a keyed
    modifier: key ``"Mist"``/``"Disc4"``/``"Place Cleyra"``/``"Effect Windmill"``, or ``"Place *"`` for a bare
    ``Place Clear`` (every place). ``clean`` = the line uses Memoria's documented ``Clean``, which the parser ignores."""
    import re
    out = []
    for m in re.finditer(_TOKEN_RE, txt, re.M):
        kind = m.group(1)
        if kind not in ("Place", "Effect", "Mist", "Disc4"):
            continue
        args = [a.group(1) for a in re.finditer(_ARG_RE, m.group(2).strip())]
        if not args:
            continue
        line = m.group(0).strip()
        if kind in ("Mist", "Disc4"):
            out.append((kind, line, args[0] == "Clean"))
        elif args[0] in ("Clear", "Clean"):
            out.append((f"{kind} *", line, args[0] == "Clean"))
        else:
            out.append((f"{kind} {args[0]}", line, len(args) > 1 and args[1] == "Clean"))
    return out


def stack_report(cfg: dict, *, mod_folder: str, game_dir, folder_names=None) -> dict:
    """What the OTHER stacked ``Environment.txt`` files set for the keys this config writes (terrain study defect 20).

    ``below`` = ``[(source, line)]`` from the base file and lower-priority folders, read BEFORE this one: replaced by
    this file's ``Clear`` lines (``stack = "replace"``) or OR'd with it (``"combine"``). ``above`` = from higher-priority
    folders, read AFTER this one: they still OR on top, or clear it. ``clean`` = ``[(source, line)]`` in any stacked
    file using ``Clean``, a silent no-op. ``in_stack`` = ``mod_folder`` is in FolderNames (else nothing loads it).
    Reads ``Memoria.ini`` unless ``folder_names`` is given; an unreadable ini reads as an empty stack."""
    from pathlib import Path
    from ..deploystack import parse_folder_names
    game_dir = Path(game_dir)
    order = folder_names
    if order is None:
        ini = game_dir / "Memoria.ini"
        order = parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    mine = {"Mist"} if cfg.get("mist") is not None else set()
    mine |= {"Disc4"} if cfg.get("disc4") is not None else set()
    for kind, tok in (("effect", "Effect"), ("place", "Place")):
        mine |= {f"{tok} {it['name']}" for it in cfg.get(kind, []) or []}
    pos = order.index(mod_folder) if mod_folder in order else None
    sources = [("(base game)", game_dir / ENVIRONMENT_REL_PATH, "below")]
    for i, f in enumerate(order):
        if f != mod_folder:
            side = "below" if pos is None or i > pos else "above"
            sources.append((f, game_dir / f / ENVIRONMENT_REL_PATH, side))
    rep = {"in_stack": pos is not None, "below": [], "above": [], "clean": []}
    for name, path, side in sources:
        try:
            txt = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for key, line, clean in _keys(txt):
            if clean:
                rep["clean"].append((name, line))
            elif key in mine or (key.endswith(" *") and any(k.startswith(key[:-1]) for k in mine)):
                rep[side].append((name, line))
    return rep


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
