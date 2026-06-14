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

    # Set-dressing (author-customizable) -- dress the hub without hand-editing the generated field.toml.
    [[hub.props]]                    # static set-dressing (the proven [[prop]] path; non-interactive)
    prop = "save_point"             #   a prop archetype by name (save_point/chest/tent/barrel/...) OR
    pos  = [300, 100]               #   model = <GEO id> + pose = "<anim>" for a bare standing figure
    [[hub.ambient_npcs]]             # a flavor character (talk -> its dialogue line, if any)
    archetype = "moogle"            #   archetype name OR model = <GEO id>
    pos       = [260, 150]
    dialogue  = "Kupo! Safe travels!"   # optional; omit for a silent standing NPC

    [[journey]]
    id    = "black_mage_village"     # stable slug (hub-choice key + seed namespace; docs/JOURNEYS.md)
    name  = "The Black Mage Village" # the menu row label (default: humanized id)
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
# Hold the screen black this many frames before the reveal fade so the engine's smooth-camera follower
# settles UNSEEN (else warping into the hub visibly eases the camera to rest -- the borrowed room's camera
# vs the warp-in delta). ~1.5s @ 30fps; engine-independent. Tune/disable (0) via [hub] entry_settle.
DEFAULT_ENTRY_SETTLE = 45
DEFAULT_TEXT_BLOCK = 1073
SHADOWED_TEXT_BLOCK = 1073       # the block the higher-priority FF9CustomMap folder defines (shadows yours)
PAGING_SOFT_MAX = 8              # journeys + the stay row beyond ~this need menu scrolling -- verify in-game
SCENARIO_MAX = 32767

_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")     # a field/journey name -> EVT_/FBG_ token + comment/subdir-safe


class HubError(ValueError):
    """A journeys.toml / hub-generation problem (caught + printed by the CLI)."""


@dataclass
class Journey:
    """One row of the journey menu, in the ``docs/JOURNEYS.md`` schema: a stable ``id`` slug (the hub-choice
    key + seed namespace), a pretty ``name`` (the menu label + the GUI breadcrumb), the ``entry`` field it
    warps into, and an optional ``set_scenario`` seed applied hub-side before the warp. (A *multi-campaign*
    journey -- ``campaigns`` / ``entry = {campaign, field}`` / ``[journey.seed]`` / ``[[journey.link]]`` --
    is the future journey ASSEMBLER's job; gen-hub builds the single-entry form, ``entry = <field id>``.)"""
    id: str
    name: str
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
    entry_settle: int = DEFAULT_ENTRY_SETTLE      # frames the hub holds black on entry so the camera settles
    text_block: int = DEFAULT_TEXT_BLOCK
    prompt: str = DEFAULT_PROMPT
    stay_text: str = DEFAULT_STAY
    player_model: "int | str" = MOOGLE_MODEL
    player_spawn: "list | None" = None
    narrator: str = DEFAULT_NARRATOR
    narrator_model: "int | str | None" = None    # None -> inherit player_model
    narrator_pos: "list | None" = None
    # Set-dressing (author-customizable): static [[prop]]s (save point / lamp / a bare standing moogle) +
    # ambient [[npc]]s (a talkable flavor character). All BG-borrow + the proven prop/npc build path.
    props: "list" = field(default_factory=list)          # each: {prop=<archetype>|model=N, pos, pose?, face?}
    ambient_npcs: "list" = field(default_factory=list)    # each: {archetype=<name>|model=N, pos, dialogue?}
    journeys: "list[Journey]" = field(default_factory=list)

    @property
    def narrator_model_resolved(self):
        return self.narrator_model if self.narrator_model is not None else self.player_model


def _humanize(name: str) -> str:
    """``black_mage_village`` -> ``Black Mage Village`` -- a default menu label from a journey's token name."""
    return " ".join(w.capitalize() for w in str(name).replace("_", " ").split()) or str(name)


def hubspec_from_table(h: dict, journeys: "list[Journey]") -> HubSpec:
    """Build a :class:`HubSpec` from a parsed ``[hub]`` table + a resolved journey list. The single source
    of truth for the ``[hub]`` presentation schema -- both :func:`load_journeys` (gen-hub's single-entry
    rows) and the multi-campaign journey assembler (:mod:`ff9mapkit.journey`, which resolves campaign entries
    to global ids before calling here) construct their HubSpec through this. Raises :class:`HubError` on a
    missing required key; semantic checks stay in :func:`validate_hub`."""
    if "name" not in h:
        raise HubError("[hub] missing required key 'name' (becomes EVT_<name>.eb / FBG_N<area>_<name>)")
    if "id" not in h:
        raise HubError("[hub] missing required key 'id' (the hub field id, >= 4000)")
    return HubSpec(
        name=str(h["name"]),
        id=int(h["id"]),
        area=int(h.get("area", DEFAULT_AREA)),
        borrow_bg=str(h.get("borrow_bg", "")),
        borrow_field=int(h["borrow_field"]) if h.get("borrow_field") is not None else None,
        camera=str(h.get("camera", DEFAULT_CAMERA)),
        entry_settle=int(h.get("entry_settle", DEFAULT_ENTRY_SETTLE)),
        text_block=int(h.get("text_block", DEFAULT_TEXT_BLOCK)),
        prompt=str(h.get("prompt", DEFAULT_PROMPT)),
        stay_text=str(h.get("stay_text", DEFAULT_STAY)),
        player_model=h.get("player_model", MOOGLE_MODEL),
        player_spawn=list(h["player_spawn"]) if "player_spawn" in h else None,
        narrator=str(h.get("narrator", DEFAULT_NARRATOR)),
        narrator_model=h.get("narrator_model"),
        narrator_pos=list(h["narrator_pos"]) if "narrator_pos" in h else None,
        props=[dict(p) for p in h.get("props", [])],
        ambient_npcs=[dict(n) for n in h.get("ambient_npcs", [])],
        journeys=journeys,
    )


def load_journeys(path) -> HubSpec:
    """Parse a ``journeys.toml`` into a :class:`HubSpec`. Raises :class:`HubError` on a STRUCTURAL problem
    (no ``[hub]`` table, a ``[[journey]]`` missing ``id``/``entry``, or a multi-campaign journey that needs the
    assembler); semantic checks (id band, dup ids, missing ``borrow_bg`` ...) are :func:`validate_hub`'s job so
    the CLI can print them all at once."""
    p = Path(path)
    with open(p, "rb") as fh:
        data = tomllib.load(fh)
    if "hub" not in data:
        raise HubError(f"{p}: not a journeys manifest (no [hub] table)")

    journeys = []
    for i, j in enumerate(data.get("journey", [])):
        if "campaigns" in j or isinstance(j.get("entry"), dict):
            raise HubError(f"[[journey]] #{i}: a multi-campaign journey (campaigns / entry = {{campaign, "
                           f"field}}) needs the journey ASSEMBLER (`ff9mapkit assemble-journey`, "
                           f"docs/JOURNEYS.md), not gen-hub. gen-hub builds the single-entry form: "
                           f"entry = <field id>.")
        if "id" not in j:
            raise HubError(f"[[journey]] #{i}: missing required key 'id' (the stable slug; docs/JOURNEYS.md)")
        jid = str(j["id"])
        if "entry" not in j:
            raise HubError(f"[[journey]] {jid!r}: missing required key 'entry' (the journey's entry field id)")
        sc = j.get("set_scenario")
        journeys.append(Journey(
            id=jid,
            name=str(j.get("name") or _humanize(jid)),
            entry=int(j["entry"]),
            set_scenario=int(sc) if sc is not None else None,
        ))

    return hubspec_from_table(data["hub"], journeys)


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
        if not j.id or not _NAME_RE.match(j.id):
            errors.append(f"[[journey]] #{i}: id {j.id!r} must be a token (A-Z, 0-9, _) -- the stable slug")
        elif j.id in seen:
            errors.append(f"[[journey]] id {j.id!r} is duplicated -- journey ids must be unique")
        seen.add(j.id)
        if not (isinstance(j.entry, int) and j.entry > 0):
            errors.append(f"[[journey]] {j.id!r}: entry {j.entry!r} must be a positive field id "
                          f"(the warp destination)")
        elif j.entry == spec.id:
            warnings.append(f"[[journey]] {j.id!r}: entry {j.entry} is the hub itself -- picking it warps "
                            f"the hub onto itself")
        if j.set_scenario is not None and not (0 <= j.set_scenario <= SCENARIO_MAX):
            errors.append(f"[[journey]] {j.id!r}: set_scenario {j.set_scenario} out of range "
                          f"(0-{SCENARIO_MAX})")

    spawn = spec.player_spawn or [0, 0]      # the narrator defaults to the player spawn -> they'd overlap
    npos = spec.narrator_pos if spec.narrator_pos is not None else spawn
    if list(npos) == list(spawn):
        warnings.append(f"[hub] narrator_pos {list(npos)} == player_spawn (or unset) -- the player spawns "
                        f"INSIDE the narrator. Set distinct player_spawn / narrator_pos a few units apart on "
                        f"the walkmesh (e.g. player [404,127], narrator [480,127] for a Gargan Roo backdrop).")

    if spec.text_block == SHADOWED_TEXT_BLOCK:
        warnings.append(f"[hub] text_block {SHADOWED_TEXT_BLOCK} is SHADOWED by the FF9CustomMap folder in a "
                        f"stacked setup -- the menu shows that folder's text, not yours. Pick a distinct real "
                        f"MesDB id; deploy_field's shadow check suggests free ones.")
    rows = len(spec.journeys) + 1     # + the trailing stay row
    if rows > PAGING_SOFT_MAX:
        warnings.append(f"{rows} menu rows (journeys + stay) -- FF9 choice menus show ~4 at a time and "
                        f"scroll; verify the long list reads well in-game (paging / sub-hubs are a future "
                        f"enhancement).")

    # set-dressing structural checks (unknown prop/archetype NAMES are caught by build.validate on the
    # emitted field.toml -- here we just ensure each row is well-formed so the emit produces valid TOML).
    def _check_pos(label, row):
        if not (isinstance(row.get("pos"), (list, tuple)) and len(row["pos"]) == 2):
            errors.append(f"{label}: needs pos = [x, z] (a point on the hub walkmesh)")
    for k, p in enumerate(spec.props):
        if p.get("prop") is None and p.get("model") is None:
            errors.append(f"[[hub.props]] #{k}: needs a 'prop' (archetype name, e.g. \"save_point\") or "
                          f"'model' (a GEO id) + optional 'pose'")
        _check_pos(f"[[hub.props]] #{k}", p)
    for k, n in enumerate(spec.ambient_npcs):
        if n.get("archetype") is None and n.get("model") is None:
            errors.append(f"[[hub.ambient_npcs]] #{k}: needs an 'archetype' (name, e.g. \"moogle\") or "
                          f"'model' (a GEO id)")
        _check_pos(f"[[hub.ambient_npcs]] #{k}", n)
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


def _prop_block(p: dict) -> list:
    """A ``[[prop]]`` toml block from a ``[[hub.props]]`` row -- static set-dressing (a prop archetype by
    name, e.g. ``save_point``/``lamp``, or a raw ``model`` + ``pose`` for a bare standing figure)."""
    out = ["[[prop]]"]
    if p.get("prop") is not None:
        out.append(f'prop = "{_q(p["prop"])}"')
    elif p.get("model") is not None:
        out.append(f"model = {_model_toml(p['model'])}")
    pos = p.get("pos") or [0, 0]
    out.append(f"pos = [{int(pos[0])}, {int(pos[1])}]")
    if p.get("pose") is not None:
        out.append(f"pose = {_model_toml(p['pose'])}")
    if p.get("face") is not None:
        out.append(f"face = {int(p['face'])}")
    out.append("")
    return out


def _ambient_npc_block(n: dict, idx: int) -> list:
    """A non-narrator ``[[npc]]`` block from a ``[[hub.ambient_npcs]]`` row -- a flavor character (talk -> its
    ``dialogue`` line, if any). Resolved by ``archetype`` name or raw ``model``."""
    out = ["[[npc]]", f'name = "{_q(n.get("name") or f"Ambient_{idx}")}"']
    if n.get("archetype") is not None:
        out.append(f'archetype = "{_q(n["archetype"])}"')
    elif n.get("model") is not None:
        out.append(f"model = {_model_toml(n['model'])}")
    pos = n.get("pos") or [0, 0]
    out.append(f"pos = [{int(pos[0])}, {int(pos[1])}]")
    if n.get("dialogue"):
        out.append(f'dialogue = "{_q(n["dialogue"])}"')
    out.append("")
    return out


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
        *([f"entry_settle = {spec.entry_settle}   # hold black on entry so the camera settles unseen "
           f"(no warp-in ease); 0 = off"] if spec.entry_settle else []),
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
    ]
    if spec.props or spec.ambient_npcs:
        L.append("# Set-dressing (author-customizable via [[hub.props]] / [[hub.ambient_npcs]]): static props")
        L.append("# + ambient flavor NPCs. All BG-borrow; the proven prop/npc build path compiles them.")
        L.append("")
    for p in spec.props:
        L += _prop_block(p)
    for k, n in enumerate(spec.ambient_npcs):
        L += _ambient_npc_block(n, k)
    L += [
        "# The journey menu: each option warps to a journey's entry field; set_scenario (optional) seeds",
        "# the beat hub-side before the warp. The trailing row has no warp -- it just closes the menu.",
        "[[choice]]",
        f'npc = "{_q(spec.narrator)}"',
        f'prompt = "{_q(spec.prompt)}"',
        f"cancel = {cancel}                  # B / cancel -> the last row (no warp)",
        "instant = true                  # pop the menu fully drawn ([IMME]) -- a selector, like FF9 shop menus",
        "",
    ]
    for j in spec.journeys:
        L.append("[[choice.options]]")
        L.append(f'text = "{_q(j.name)}"')
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


def extract_camera_into_spec(spec: HubSpec, out_dir, *, game=None, force=False) -> dict:
    """Pull the ``[hub] borrow_field`` room's camera into the gitignored workspace cache and point
    ``spec.camera`` at that ONE central copy (a repo-relative path from ``out_dir``). Returns the
    ``extract.cache_field`` result. Shared by :func:`generate` (gen-hub) and the journey assembler's hub emit
    (:func:`ff9mapkit.journey.generate_hub`) so both auto-provision the borrowed camera identically. Needs the
    install + UnityPy."""
    if not spec.borrow_field:
        raise HubError("camera extraction needs [hub] borrow_field = <real field id> (the room whose camera "
                       "to extract; e.g. borrow_field = 950). Or supply the [hub] camera .bgx yourself.")
    from . import extract as _extract
    extracted = _extract.cache_field(spec.borrow_field, game=game, force=force)
    spec.camera = _relpath(extracted["camera"], Path(out_dir))   # point at the ONE central cache copy
    return extracted


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
        extracted = extract_camera_into_spec(spec, out_path.parent, game=game, force=force)

    text = render_hub_field_toml(spec, source=journeys_path.name)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    return {"path": out_path, "spec": spec, "warnings": warnings, "journeys": len(spec.journeys),
            "extracted": extracted}
