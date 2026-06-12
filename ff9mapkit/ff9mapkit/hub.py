"""World-Hub generator (overworld's lane): a ``journeys.toml`` registry -> a hub ``field.toml``.

A *World Hub* is the New-Game-landing **journey selector** (memory: ``project-ff9-world-hub``): you walk as
a Moogle, talk to a narrator NPC, pick a **journey** (a complete arc = one or more chained campaign slices)
from a dialogue menu, and warp into its entry field -- optionally seeding the story beat first. The hub is
THIN: per journey it needs only ``{display name, entry field id, seed}``; HOW a journey plays internally is
the journey's own business (story_flags' campaign lane). This module is the "hardcoded MVP -> generator"
step the world-hub MVP left as a follow-up: it turns a small ``journeys.toml`` into a complete hub
``field.toml``, built on the in-game-proven primitives -- the choice ``warp`` action
(:func:`ff9mapkit.content.event.warp`) + ``[player] model=`` (the Moogle PC).

It **emits a field.toml** (the existing build/deploy path then compiles it -- no new build path), mirroring
:func:`ff9mapkit.campaign.render_campaign_toml`'s emit-then-build pattern. The generated hub is a normal
synthesized BG-borrow field: a camera ``borrow`` + a Moogle player + a narrator NPC + one ``[[choice]]``
whose options ``warp`` to each journey's entry, plus a trailing no-warp "stay" row (the cancel target).

``journeys.toml`` shape::

    [hub]
    name      = "WORLD_HUB"          # -> EVT_<name>.eb / FBG_N<area>_<name>
    id        = 4500                 # the hub field id (>= 4000)
    area      = 21                   # >= 10 (the BG-borrow loader reads 2 digits; single digits black-screen)
    borrow_bg = "GRGR_MAP420_GR_CEN_0"   # BG-borrow a real room for the backdrop (the MVP art path)
    camera    = "camera_hub.bgx"     # that room's camera (you extract it from your own install; gitignored)
    text_block = 8                   # a real MesDB id NOT shadowed by a higher folder (1073 IS -> wrong menu)
    prompt    = "Kupo! Which journey will you take?"
    stay_text = "Stay here, kupo..." # the trailing no-warp (cancel) row label
    player_model   = 220             # the Moogle PC (220 = GEO_NPC_F0_MOG, the iconic save moogle)
    player_spawn   = [404, 127]
    narrator       = "Stiltzkin"
    narrator_model = 220             # default = player_model
    narrator_pos   = [480, 127]

    [[journey]]
    name  = "black_mage_village"
    title = "The Black Mage Village" # the menu row label (default: humanized name)
    entry = 4501                     # the journey's entry field id (the warp target)
    set_scenario = 2600              # optional: seed the beat hub-side before the warp

Regenerate the hub after editing the registry (``ff9mapkit gen-hub journeys.toml``); the emitted
``hub.field.toml`` is a build artifact -- don't hand-edit it.
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# The iconic save Moogle (GEO_NPC_F0_MOG). NOT 199 (GEO_NPC_F5, a bat-winged variant that surprised the
# world-hub playtest -- memory project-ff9-world-hub). Both share the MOG movement clips via catalog.npc_anims.
MOOGLE_MODEL = 220
DEFAULT_AREA = 21
DEFAULT_PROMPT = "Kupo! Which journey will you take?"
DEFAULT_STAY = "Stay here, kupo..."
DEFAULT_NARRATOR = "Stiltzkin"
DEFAULT_CAMERA = "camera_hub.bgx"
DEFAULT_TEXT_BLOCK = 1073
SHADOWED_TEXT_BLOCK = 1073       # the block the higher-priority FF9CustomMap folder defines (shadows yours)
PAGING_SOFT_MAX = 8              # journeys + the stay row beyond ~this need menu scrolling -- verify in-game
SCENARIO_MAX = 32767

_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")     # a field/journey name -> EVT_/FBG_ token + comment/subdir-safe


class HubError(ValueError):
    """A journeys.toml / hub-generation problem (caught + printed by the CLI)."""


@dataclass
class Journey:
    """One row of the journey menu: a display ``title``, the ``entry`` field it warps into, and an optional
    ``set_scenario`` seed applied hub-side before the warp. ``name`` is the stable token (comments/diffs)."""
    name: str
    title: str
    entry: int
    set_scenario: "int | None" = None


@dataclass
class HubSpec:
    """The whole hub registry: the hub field's identity + backdrop + Moogle/narrator rig + the journeys."""
    name: str
    id: int
    area: int = DEFAULT_AREA
    borrow_bg: str = ""
    borrow_field: "int | None" = None       # the real field id whose camera `gen-hub --extract-camera` pulls
    camera: str = DEFAULT_CAMERA
    text_block: int = DEFAULT_TEXT_BLOCK
    prompt: str = DEFAULT_PROMPT
    stay_text: str = DEFAULT_STAY
    player_model: "int | str" = MOOGLE_MODEL
    player_spawn: "list | None" = None
    narrator: str = DEFAULT_NARRATOR
    narrator_model: "int | str | None" = None    # None -> inherit player_model
    narrator_pos: "list | None" = None
    journeys: "list[Journey]" = field(default_factory=list)

    @property
    def narrator_model_resolved(self):
        return self.narrator_model if self.narrator_model is not None else self.player_model


def _humanize(name: str) -> str:
    """``black_mage_village`` -> ``Black Mage Village`` -- a default menu label from a journey's token name."""
    return " ".join(w.capitalize() for w in str(name).replace("_", " ").split()) or str(name)


def load_journeys(path) -> HubSpec:
    """Parse a ``journeys.toml`` into a :class:`HubSpec`. Raises :class:`HubError` on a STRUCTURAL problem
    (no ``[hub]`` table, a ``[[journey]]`` missing ``name``/``entry``); semantic checks (id band, dup names,
    missing ``borrow_bg`` ...) are :func:`validate_hub`'s job so the CLI can print them all at once."""
    p = Path(path)
    with open(p, "rb") as fh:
        data = tomllib.load(fh)
    if "hub" not in data:
        raise HubError(f"{p}: not a journeys manifest (no [hub] table)")
    h = data["hub"]
    if "name" not in h:
        raise HubError("[hub] missing required key 'name' (becomes EVT_<name>.eb / FBG_N<area>_<name>)")
    if "id" not in h:
        raise HubError("[hub] missing required key 'id' (the hub field id, >= 4000)")

    journeys = []
    for i, j in enumerate(data.get("journey", [])):
        if "name" not in j:
            raise HubError(f"[[journey]] #{i}: missing required key 'name'")
        nm = str(j["name"])
        if "entry" not in j:
            raise HubError(f"[[journey]] {nm!r}: missing required key 'entry' (the journey's entry field id)")
        sc = j.get("set_scenario")
        journeys.append(Journey(
            name=nm,
            title=str(j.get("title") or _humanize(nm)),
            entry=int(j["entry"]),
            set_scenario=int(sc) if sc is not None else None,
        ))

    return HubSpec(
        name=str(h["name"]),
        id=int(h["id"]),
        area=int(h.get("area", DEFAULT_AREA)),
        borrow_bg=str(h.get("borrow_bg", "")),
        borrow_field=int(h["borrow_field"]) if h.get("borrow_field") is not None else None,
        camera=str(h.get("camera", DEFAULT_CAMERA)),
        text_block=int(h.get("text_block", DEFAULT_TEXT_BLOCK)),
        prompt=str(h.get("prompt", DEFAULT_PROMPT)),
        stay_text=str(h.get("stay_text", DEFAULT_STAY)),
        player_model=h.get("player_model", MOOGLE_MODEL),
        player_spawn=list(h["player_spawn"]) if "player_spawn" in h else None,
        narrator=str(h.get("narrator", DEFAULT_NARRATOR)),
        narrator_model=h.get("narrator_model"),
        narrator_pos=list(h["narrator_pos"]) if "narrator_pos" in h else None,
        journeys=journeys,
    )


def validate_hub(spec: HubSpec) -> "tuple[list, list]":
    """Validate a :class:`HubSpec`. Returns ``(errors, warnings)`` -- errors abort generation, warnings are
    advisory (like :func:`ff9mapkit.campaign.lint_campaign`). The emitted field.toml then runs the kit's own
    :func:`ff9mapkit.build.validate` at build time; this catches the hub-spec-level problems early + clearly."""
    errors, warnings = [], []

    if not spec.name or not _NAME_RE.match(spec.name):
        errors.append(f"[hub] name {spec.name!r} must be a non-empty token (A-Z, 0-9, _) -- it becomes "
                      f"EVT_<name> / FBG_N<area>_<name>")
    if not (4000 <= spec.id <= 32767):
        errors.append(f"[hub] id {spec.id} out of range -- custom field ids are 4000-32767 (the live "
                      f"fldMapNo is Int16, so a higher id registers but is unreachable)")
    if spec.area < 10:
        errors.append(f"[hub] area {spec.area} must be >= 10 -- the BG-borrow loader builds 'FBG_N<area>' "
                      f"and reads 2 digits, so single-digit areas black-screen")
    if not spec.borrow_bg:
        errors.append("[hub] borrow_bg is required -- BG-borrow a real room (area >= 10) for the hub "
                      "backdrop. Authoring novel hub art is out of the generator's scope (paint layers + a "
                      "custom [camera]/[walkmesh] by hand, then hand-author the field.toml).")
    if not spec.camera:
        errors.append("[hub] camera is required -- the borrowed room's .bgx (extract it from your install; "
                      "it's gitignored, you supply the bytes). Or set borrow_field = <id> and run "
                      "`gen-hub --extract-camera` to cache it automatically.")
    if spec.borrow_field is not None and not (isinstance(spec.borrow_field, int) and spec.borrow_field > 0):
        errors.append(f"[hub] borrow_field {spec.borrow_field!r} must be a positive real field id (the room "
                      f"whose camera --extract-camera pulls into the cache)")
    if not spec.journeys:
        errors.append("a hub needs at least one [[journey]] -- nothing to select")

    seen: set = set()
    for i, j in enumerate(spec.journeys):
        if not j.name or not _NAME_RE.match(j.name):
            errors.append(f"[[journey]] #{i}: name {j.name!r} must be a token (A-Z, 0-9, _)")
        elif j.name in seen:
            errors.append(f"[[journey]] name {j.name!r} is duplicated -- journey names must be unique")
        seen.add(j.name)
        if not (isinstance(j.entry, int) and j.entry > 0):
            errors.append(f"[[journey]] {j.name!r}: entry {j.entry!r} must be a positive field id "
                          f"(the warp destination)")
        elif j.entry == spec.id:
            warnings.append(f"[[journey]] {j.name!r}: entry {j.entry} is the hub itself -- picking it warps "
                            f"the hub onto itself")
        if j.set_scenario is not None and not (0 <= j.set_scenario <= SCENARIO_MAX):
            errors.append(f"[[journey]] {j.name!r}: set_scenario {j.set_scenario} out of range "
                          f"(0-{SCENARIO_MAX})")

    if spec.text_block == SHADOWED_TEXT_BLOCK:
        warnings.append(f"[hub] text_block {SHADOWED_TEXT_BLOCK} is SHADOWED by the FF9CustomMap folder in a "
                        f"stacked setup -- the menu shows that folder's text, not yours. Pick a distinct real "
                        f"MesDB id; deploy_field's shadow check suggests free ones.")
    rows = len(spec.journeys) + 1     # + the trailing stay row
    if rows > PAGING_SOFT_MAX:
        warnings.append(f"{rows} menu rows (journeys + stay) -- FF9 choice menus show ~4 at a time and "
                        f"scroll; verify the long list reads well in-game (paging / sub-hubs are a future "
                        f"enhancement).")
    return errors, warnings


def _q(s) -> str:
    """A TOML-safe basic-string value (escape backslash + double-quote)."""
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def _model_toml(v) -> str:
    """Emit a model value: a numeric id (or digit string) bare, a GEO name quoted."""
    if isinstance(v, int):
        return str(v)
    s = str(v)
    return s if s.isdigit() else f'"{_q(s)}"'


def render_hub_field_toml(spec: HubSpec, *, source: "str | None" = None) -> str:
    """The hub ``field.toml`` text -- valid TOML the existing build/deploy path compiles. Mirrors the proven
    hand-authored ``examples/world_hub/hub.field.toml`` shape (BG-borrow + Moogle PC + narrator + the journey
    ``[[choice]]``). ``source`` (the journeys.toml name) is noted in the header comment."""
    src = f" from {source}" if source else ""
    cancel = len(spec.journeys)            # the trailing stay row's 0-based index = number of journeys
    spawn = spec.player_spawn or [0, 0]
    npos = spec.narrator_pos or list(spawn)
    L = [
        "# ============================================================================",
        f"#  WORLD HUB -- generated by `ff9mapkit gen-hub`{src}.",
        "#  A journey selector: walk as the Moogle, talk to the narrator -> a menu of journeys ->",
        "#  each row warps you into that journey's entry field (the in-game-proven choice `warp`",
        "#  action + `[player] model=`). REGENERATE after editing the journeys.toml -- this file is a",
        "#  build artifact, hand edits are overwritten. (memory: project-ff9-world-hub)",
        "# ============================================================================",
        "",
        "[field]",
        f"id = {spec.id}",
        f'name = "{_q(spec.name)}"',
        f'borrow_bg = "{_q(spec.borrow_bg)}"   # a real room as the backdrop (area >= 10)',
        f"area = {spec.area}",
        f"text_block = {spec.text_block}   # a real MesDB id NOT shadowed by a higher mod folder",
        "",
        "[camera]",
        f'borrow = "{_q(spec.camera)}"   # the borrowed room\'s camera (gitignored; extract from your install)',
        "",
        "[player]",
        f"spawn = [{spawn[0]}, {spawn[1]}]",
        f"model = {_model_toml(spec.player_model)}   # walk the hub as the Moogle ([player] model=)",
        "",
        "[[npc]]",
        f'name = "{_q(spec.narrator)}"   # the narrator -- talk to open the journey menu',
        f"pos = [{npos[0]}, {npos[1]}]",
        f"model = {_model_toml(spec.narrator_model_resolved)}",
        "",
        "# The journey menu: each option warps to a journey's entry field; set_scenario (optional) seeds",
        "# the beat hub-side before the warp. The trailing row has no warp -- it just closes the menu.",
        "[[choice]]",
        f'npc = "{_q(spec.narrator)}"',
        f'prompt = "{_q(spec.prompt)}"',
        f"cancel = {cancel}                  # B / cancel -> the last row (no warp)",
        "",
    ]
    for j in spec.journeys:
        L.append("[[choice.options]]")
        L.append(f'text = "{_q(j.title)}"')
        L.append(f"warp = {j.entry}")
        if j.set_scenario is not None:
            L.append(f"set_scenario = {j.set_scenario}")
        L.append("")
    L.append("[[choice.options]]")
    L.append(f'text = "{_q(spec.stay_text)}"   # no warp -- closes the menu')
    L.append("")
    return "\n".join(L)


def _relpath(target, start_dir) -> str:
    """A forward-slash path from ``start_dir`` to ``target`` -- repo-relative (portable across clones/OSes),
    falling back to absolute only across Windows drives."""
    target, start_dir = Path(target).resolve(), Path(start_dir).resolve()
    try:
        return Path(os.path.relpath(target, start_dir)).as_posix()
    except ValueError:                              # different drives on Windows -> can't relativize
        return target.as_posix()


def generate(journeys_path, out_path=None, *, extract_camera=False, game=None, force=False) -> dict:
    """Load a ``journeys.toml``, validate it, and emit the hub ``field.toml``. Returns a summary
    ``{path, spec, warnings, journeys, extracted}``. Raises :class:`HubError` on a validation error.
    ``out_path`` defaults to ``hub.field.toml`` beside the registry; a directory ``out_path`` writes
    ``hub.field.toml`` inside it.

    ``extract_camera`` (needs the install + UnityPy): pull the borrowed room's camera (``[hub]
    borrow_field``) into the gitignored workspace cache once and point the emitted ``[camera] borrow`` at
    that single central copy -- so ``gen-hub`` then build/deploy "just works", no manual extract step."""
    journeys_path = Path(journeys_path)
    spec = load_journeys(journeys_path)
    errors, warnings = validate_hub(spec)
    if errors:
        raise HubError("journeys.toml validation failed:\n  - " + "\n  - ".join(errors))
    out_path = Path(out_path) if out_path else (journeys_path.parent / "hub.field.toml")
    if out_path.is_dir():
        out_path = out_path / "hub.field.toml"

    extracted = None
    if extract_camera:
        if not spec.borrow_field:
            raise HubError("--extract-camera needs [hub] borrow_field = <real field id> (the room whose "
                           "camera to extract; e.g. borrow_field = 950 for the example hub).")
        from . import extract as _extract
        extracted = _extract.cache_field(spec.borrow_field, game=game, force=force)
        spec.camera = _relpath(extracted["camera"], out_path.parent)   # point at the ONE central cache copy

    text = render_hub_field_toml(spec, source=journeys_path.name)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    return {"path": out_path, "spec": spec, "warnings": warnings, "journeys": len(spec.journeys),
            "extracted": extracted}
