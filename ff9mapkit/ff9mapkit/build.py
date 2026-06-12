"""Compile a declarative ``field.toml`` project into a Memoria mod folder.

One ``field.toml`` describes one field; a mod is one or more of them sharing a mod root. The
builder turns a project into:
  * the background scene  FieldMaps/<FBG>/<FBG>.bgx + overlay PNGs + <FBG>.bgi.bytes (walkmesh)
  * the event script      field/<lang>/EVT_<name>.eb.bytes  (all languages), built from the
                          blank field by the content injectors
  * dialogue text         FF9_Data/embeddedasset/text/<lang>/field/<textBlock>.mes
  * registration          a DictionaryPatch FieldScene line, BattlePatch (if encounters),
                          and ModDescription.xml

See docs/FORMAT.md for the schema. The whole build is offline and deterministic, so it can be
validated by diffing against known-good assets before ever launching the game.
"""

from __future__ import annotations

import math
import shutil
import struct
import tomllib
from dataclasses import dataclass, field as _dc_field
from pathlib import Path

from .config import LANGS, ModLayout, fbg_name
from .content import camera as _camera
from .content import choice as _choice
from .content import cutscene as _cutscene
from .content import encounter as _enc
from .content import event as _event
from .content import gateway as _gw
from .content import jump as _jump
from .content import ladder as _ladder
from .content import movement as _movement
from .content import music as _music
from .content import npc as _npc
from .content import object as _object
from .content import onentry as _onentry
from .content import pathfind as _pathfind
from .content import prop as _prop
from .content import region as _region
from .content import party as _party
from .content import reinit as _reinit
from .content import savepoint as _savepoint
from .content import shop as _shop
from .content import startup as _startup
from .content import text as _text
from . import animations as _animations
from . import archetypes as _archetypes
from . import prop_archetypes as _prop_archetypes
from ._held_poses import HELD_POSES                  # (carrier_model, prop_model) -> (bone, held_pose)
from . import catalog as _catalog
from . import flags as _flags
from . import items as _items
from . import data as _data
from .eb import EbScript, opcodes
from .eb.disasm import iter_code
from .scene import bgi, bgx, cam, guide


class BuildError(RuntimeError):
    pass


# --------------------------------------------------------------------------- project model
# Two-surface authoring (Godot-style): the SCENE (where things are) and the LOGIC (what they do) can
# live in separate files. `<x>.field.toml` is the project (logic: dialogue, conditions, events,
# encounters + content identity by `name`); a sibling `<x>.scene.toml` is owned/overwritten by the
# Blender add-on (spatial: camera, walkmesh, layers, player spawn, camera zones, and each entity's
# position/zone tagged by name). `load` OVERLAYS the scene onto the field by name, so Blender never
# clobbers your script. Single-file field.tomls (no scene sibling) build exactly as before.

_SCENE_SCALAR = ("camera", "walkmesh", "layers", "camera_zone")   # spatial sections the scene owns
_ENTITY_LISTS = ("npc", "gateway", "event", "marker")              # split by name (logic + spatial)


def _merge_entities(base_list, scene_list):
    """Merge two entity lists by `name`: a base (logic) entity is updated with its same-named scene
    (spatial) entity's keys (scene wins per-key); scene-only entities are appended; base-only kept."""
    scene_by_name = {e["name"]: e for e in scene_list if "name" in e}
    used = set()
    out = []
    for b in base_list:
        nm = b.get("name")
        if nm is not None and nm in scene_by_name:
            out.append({**b, **scene_by_name[nm]})       # scene supplies pos/zone, base the logic
            used.add(nm)
        else:
            out.append(dict(b))
    for e in scene_list:                                  # entities placed in Blender, no logic yet
        if e.get("name") not in used:
            out.append(dict(e))
    return out


def _merge_scene(base: dict, scene: dict) -> dict:
    """Overlay a Blender `scene.toml` onto a `field.toml` dict. Spatial sections come from the scene;
    content lists merge by name (scene = position/zone, field = logic)."""
    merged = dict(base)
    for key in _SCENE_SCALAR:
        if key in scene:
            merged[key] = scene[key]
    if "player" in scene:
        merged["player"] = {**base.get("player", {}), **scene["player"]}
    for key in _ENTITY_LISTS:
        if key in base or key in scene:
            merged[key] = _merge_entities(base.get(key, []), scene.get(key, []))
    return merged


def _find_scene(field_path: Path, base: dict):
    """The scene overlay for a field.toml: explicit ``[scene] file`` wins, else a sibling
    ``<stem>.scene.toml`` (``<x>.field.toml`` -> ``<x>.scene.toml``). Returns the parsed dict or None."""
    ref = base.get("scene", {}).get("file")
    if ref:
        sp = (field_path.parent / ref)
    else:
        nm = field_path.name
        stem = nm[:-len(".field.toml")] if nm.endswith(".field.toml") else field_path.stem
        sp = field_path.parent / f"{stem}.scene.toml"
    if not sp.is_file():
        return None
    with sp.open("rb") as fh:
        return tomllib.load(fh)


@dataclass
class FieldProject:
    raw: dict
    base_dir: Path
    # Per-member campaign once-flag base (set by campaign.build_campaign). None => single-field defaults
    # (event 8000+ / cutscene 8100 / choice 8200+), which keeps single-field builds BYTE-IDENTICAL.
    flag_base: int | None = None
    flags_per_field: int = 64    # width of this member's flag block -> the overflow guard's choice cap

    @classmethod
    def load(cls, toml_path, *, flag_names: dict | None = None) -> "FieldProject":
        p = Path(toml_path)
        with p.open("rb") as fh:
            base = tomllib.load(fh)
        scene = _find_scene(p, base)
        raw = _merge_scene(base, scene) if scene is not None else base
        # Resolve named flag references (a [[flag]] table + optional campaign-level `flag_names`) to
        # integer indices BEFORE any int() reads them. A project with no named flags is left unchanged
        # (numeric flags pass through), so single-field builds stay byte-identical.
        _flags.resolve_project_flags(raw, flag_names)
        return cls(raw, p.parent)

    # convenience accessors
    @property
    def field(self) -> dict:
        return self.raw.get("field", {})

    @property
    def id(self) -> int:
        return int(self.field["id"])

    @property
    def name(self) -> str:
        return self.field["name"]

    @property
    def area(self) -> int:
        return int(self.field["area"])

    @property
    def text_block(self) -> int:
        return int(self.field.get("text_block", 1073))

    @property
    def fbg(self) -> str:
        return fbg_name(self.area, self.name)

    def path(self, rel: str) -> Path:
        return (self.base_dir / rel).resolve()

    def carry_text_plan(self):
        """The faithful text-carry plan (a ``list[content.textcarry.CarriedEntry]``) from this project's
        ``[carry_text] bin`` sidecar, or ``[]`` when there is none. The donor's referenced dialogue text +
        the donor->carried txid map; the build remaps the grafted windows to it + ships it per-language
        (import-only, opt-in -- a plain authored field has no ``[carry_text]`` and this returns ``[]``)."""
        ct = self.raw.get("carry_text")
        if not ct or not ct.get("bin"):
            return []
        from .content import textcarry as _textcarry
        return _textcarry.load_sidecar(self.path(ct["bin"]))


# --------------------------------------------------------------------------- validation

def _entry_player_call_tags(entry_bytes, donor_player_entry, carry_tags=None) -> set:
    """The player function tags a verbatim object entry ``RunScript``s in its CARRIED funcs -- decode and
    collect ``RunScript(uid, tag)`` where uid resolves to the player (250 or the donor player entry index).
    ``carry_tags`` (the init_only subset; ``None`` = whole entry) gates which funcs are scanned: a DROPPED
    interactive func can't dangle. Used by the dangling-tag lint (a carried player call to an un-grafted
    tag would softlock)."""
    from .binutils import u16
    from .eb.disasm import iter_code
    out: set = set()
    b = entry_bytes
    if len(b) < 2:
        return out
    keep = None if carry_tags is None else {int(t) for t in carry_tags}
    fc = b[1]
    funcs = [(u16(b, 2 + i * 4), u16(b, 2 + i * 4 + 2)) for i in range(fc)]   # (tag, fpos)
    for i, (tag, fpos) in enumerate(funcs):
        if keep is not None and tag not in keep:
            continue                                      # this func is DROPPED (init_only) -> not carried
        start = 2 + fpos                                  # fpos is relative to entryStart+2 (= offset 2)
        end = (2 + funcs[i + 1][1]) if i + 1 < fc else len(b)
        for ins in iter_code(b, start, end):
            if ins.op in (0x10, 0x12, 0x14):              # RunScript[Async|Sync](level, uid, tag)
                uid, t = ins.imm(1), ins.imm(2)
                if t is not None and (uid == 250 or (donor_player_entry is not None and uid == donor_player_entry)):
                    out.add(int(t))
    return out


def _entry_window_txids(entry_bytes, carry_tags=None) -> set:
    """The literal WindowSync txids a carried object entry SHOWS in its CARRIED funcs -- decode and collect
    each window op's txid immediate (``0x1F``/``0x20`` -> ``imm(2)``; ``0x95``/``0x96`` -> ``imm(3)``); an
    EXPRESSION operand (``imm`` None) is skipped. ``carry_tags`` (the init_only kept subset; ``None`` = whole
    entry) gates which funcs are scanned -- a DROPPED func's window never runs. Used by the text-carry lint:
    a carried talkable object whose donor lines aren't carried shows WRONG/missing dialogue in the fork."""
    from .binutils import u16
    from .eb.disasm import iter_code
    out: set = set()
    b = entry_bytes
    if len(b) < 2:
        return out
    keep = None if carry_tags is None else {int(t) for t in carry_tags}
    fc = b[1]
    funcs = [(u16(b, 2 + i * 4), u16(b, 2 + i * 4 + 2)) for i in range(fc)]   # (tag, fpos)
    for i, (tag, fpos) in enumerate(funcs):
        if keep is not None and tag not in keep:
            continue                                      # a dropped func's window never runs -> ignore
        start = 2 + fpos
        end = (2 + funcs[i + 1][1]) if i + 1 < fc else len(b)
        for ins in iter_code(b, start, end):
            txid = ins.imm(2) if ins.op in (0x1F, 0x20) else (ins.imm(3) if ins.op in (0x95, 0x96) else None)
            if txid is not None:
                out.add(int(txid))
    return out


def _seq_helper_problem(bin_bytes) -> str | None:
    """Reason a STARTSEQ-helper sidecar (docs/OBJECT_CARRY.md S2 v1.5) is UNSAFE to graft, or None. Mirrors
    ``eventscan._seq_helper_safe`` on a standalone entry sidecar: a type-1 Seq/region entry with a benign body
    (no warp/battle/camera/menu/window op) and no nested ``STARTSEQ`` (the closure is depth-1). Guards a
    hand-edited project; the kit's own emit always passes."""
    from . import eventscan
    from .binutils import u16
    from .eb.disasm import iter_code
    b = bytes(bin_bytes)
    if len(b) < 2:
        return "empty / too short"
    if b[0] != 1:
        return f"not a type-1 Seq/region entry (type byte {b[0]})"
    fc = b[1]
    funcs = [(u16(b, 2 + i * 4), u16(b, 2 + i * 4 + 2)) for i in range(fc)]
    for i, (_tag, fpos) in enumerate(funcs):
        start = 2 + fpos
        end = (2 + funcs[i + 1][1]) if i + 1 < fc else len(b)
        for ins in iter_code(b, start, end):
            if ins.op == eventscan.RUN_SHARED_SCRIPT:
                return "contains a nested STARTSEQ (the closure carries depth-1 helpers only)"
            if ins.op in eventscan.UNSAFE_SEQ_OPS:
                return f"contains the cutscene op {ins.name} (warp/battle/camera/menu/window) -- would fire in a static fork"
    return None


def _story_names(project: FieldProject) -> dict:
    """``{name: index}`` from the project's ``[[flag]]`` table, for resolving named flags in story-state
    writes. Defensive: a malformed ``[[flag]]`` table is reported by its own validation, so degrade to
    ``{}`` here rather than crash validate()/lint (an unresolved name then surfaces as its own problem)."""
    try:
        return _flags.collect_flag_defs(project.raw)
    except Exception:
        return {}


def _validate_story_writes(d: dict, label: str, names: dict, problems: list, *,
                           scenario_key: str = "scenario", flags_key: str = "flags") -> None:
    """Validate a story-state write block -- the ``[startup]`` presets OR a ``[[gateway]]``'s on-exit
    advance (``set_scenario``/``set_flags``). ``<scenario_key>`` is 0..SCENARIO_MAX or an area name;
    ``<flags_key>`` is a list of ``{flag = <index|name>, value = 0|1}``. Appends human-readable problems."""
    sc = d.get(scenario_key)
    if isinstance(sc, str):
        try:
            _flags.resolve_scenario(sc)
        except ValueError as e:
            problems.append(f"{label} {scenario_key}: {e}")
    elif sc is not None and (isinstance(sc, bool) or not isinstance(sc, int)
                             or not (0 <= sc <= _startup.SCENARIO_MAX)):
        problems.append(f"{label} {scenario_key} must be 0..{_startup.SCENARIO_MAX} or an area name "
                        f"(got {sc!r})")
    fl = d.get(flags_key, [])
    if not isinstance(fl, list):
        problems.append(f"{label} {flags_key} must be a list of {{flag = <index|name>, value = 0|1}}")
        return
    for i, p in enumerate(fl):
        if not isinstance(p, dict) or "flag" not in p:
            problems.append(f"{label} {flags_key} #{i} needs a `flag` (a gEventGlobal index or a "
                            f"[[flag]] name)")
            continue
        try:
            _flags.resolve(p["flag"], names)
        except ValueError as e:
            problems.append(f"{label} {flags_key} #{i}: {e}")
        if p.get("value", 1) not in (0, 1):
            problems.append(f"{label} {flags_key} #{i} value must be 0 or 1 (got {p.get('value')!r})")


def _validate_party(pty, problems: list) -> None:
    """Validate the ``[party]`` block -- ``add`` / ``remove`` lists of existing-character names (or 0..11
    CharacterOldIndex). Each name must resolve; unknown keys are flagged."""
    if not isinstance(pty, dict):
        problems.append("[party] must be a table (add = [names], remove = [names])")
        return
    for key in ("add", "remove"):
        members = pty.get(key, [])
        if not isinstance(members, list):
            problems.append(f"[party] {key} must be a list of character names (e.g. [\"steiner\", \"vivi\"])")
            continue
        for m in members:
            try:
                _party.resolve_member(m)
            except ValueError as e:
                problems.append(f"[party] {key}: {e}")
    for key in pty:
        if key not in ("add", "remove"):
            problems.append(f"[party] unknown key {key!r} (use add / remove)")
    if not pty.get("add") and not pty.get("remove"):
        problems.append("[party] has no add or remove -- give at least one (add = [\"steiner\"])")


def _validate_on_entry(hooks, names: dict, problems: list) -> None:
    """Validate the ``[[on_entry]]`` list -- field-load beats (a ``message`` and/or ``set_scenario`` /
    ``set_flags`` story writes) optionally gated by ``requires_scenario`` (a ScenarioCounter ``== N``)
    and/or ``requires_flag``. Each hook needs at least one action; the write block reuses
    :func:`_validate_story_writes`; the gates resolve like any flag/scenario reference."""
    if not isinstance(hooks, list):
        problems.append("[[on_entry]] must be a list of hooks (each: message / set_scenario / set_flags "
                        "+ optional requires_flag / requires_scenario)")
        return
    for i, h in enumerate(hooks):
        label = f"[[on_entry]] #{i}"
        if not isinstance(h, dict):
            problems.append(f"{label} must be a table")
            continue
        if not any(k in h for k in ("message", "set_scenario", "set_flags")):
            problems.append(f"{label} does nothing -- give it a message, set_scenario, and/or set_flags")
        if "message" in h and not isinstance(h["message"], str):
            problems.append(f"{label} message must be a string")
        _validate_story_writes(h, label, names, problems,
                               scenario_key="set_scenario", flags_key="set_flags")
        rs = h.get("requires_scenario")
        if isinstance(rs, str):
            try:
                _flags.resolve_scenario(rs)
            except ValueError as e:
                problems.append(f"{label} requires_scenario: {e}")
        elif rs is not None and (isinstance(rs, bool) or not isinstance(rs, int)
                                 or not (0 <= rs <= _startup.SCENARIO_MAX)):
            problems.append(f"{label} requires_scenario must be 0..{_startup.SCENARIO_MAX} or an area name "
                            f"(got {rs!r})")
        rf = h.get("requires_flag")
        if rf is not None:
            try:
                _flags.resolve(rf, names)
            except ValueError as e:
                problems.append(f"{label} requires_flag: {e}")


def validate(project: FieldProject) -> list[str]:
    """Return a list of human-readable problems (empty => OK)."""
    problems = []
    story_names = _story_names(project)
    f = project.field
    for key in ("id", "name", "area"):
        if key not in f:
            problems.append(f"[field] missing required key '{key}'")
    if "area" in f and int(f["area"]) < 10:
        problems.append(f"[field] area must be >= 10 (got {f['area']}); single-digit areas black-screen")
    cfgs = camera_cfgs(project)
    if not cfgs:
        problems.append("[camera] section is required")
    for ci, cc in enumerate(cfgs):
        if "borrow" not in cc and "pitch" not in cc:
            problems.append(f"[camera] #{ci} needs either 'borrow' or 'pitch' (+ distance/fov)")
        if cc.get("borrow") and not project.path(cc["borrow"]).is_file():
            problems.append(f"[camera] borrow scene not found: {cc['borrow']}")
    zones = project.raw.get("camera_zone", [])
    if zones:
        if len(cfgs) < 2:
            problems.append("[[camera_zone]] needs at least 2 cameras ([[camera]] array)")
        for z in zones:
            if "to_camera" not in z or "zone" not in z:
                problems.append("[[camera_zone]] needs 'to_camera' and 'zone'")
            elif not 0 <= int(z["to_camera"]) < len(cfgs):
                problems.append(f"[[camera_zone]] to_camera {z['to_camera']} out of range (have {len(cfgs)} cameras)")
            elif len(z["zone"]) not in (4, 5):
                problems.append(f"[[camera_zone]] zone must have 4 or 5 points (got {len(z['zone'])})")
    wm = project.raw.get("walkmesh", {})
    if wm.get("obj") and not project.path(wm["obj"]).is_file():
        problems.append(f"[walkmesh] obj not found: {wm['obj']}")
    if wm.get("bgi") and not project.path(wm["bgi"]).is_file():
        problems.append(f"[walkmesh] bgi not found: {wm['bgi']}")
    if wm.get("links") and not project.path(wm["links"]).is_file():
        problems.append(f"[walkmesh] links not found: {wm['links']}")
    if wm.get("reference") and not project.path(wm["reference"]).is_file():
        problems.append(f"[walkmesh] reference not found: {wm['reference']}")
    bgf = project.field.get("bgs")               # NATIVE custom scene (Moguri/vanilla path): own .bgs + atlas
    if bgf:
        if not project.path(bgf).is_file():
            problems.append(f"[field] bgs (native scene) not found: {bgf}")
        atl = project.field.get("atlas")
        if not atl:
            problems.append('[field] a native scene needs an atlas too -- add  atlas = "atlas.png"')
        elif not project.path(atl).is_file():
            problems.append(f"[field] atlas not found: {atl}")
        mc = project.field.get("mapconfig")          # OPTIONAL: the field's 3D-model lighting config
        if mc and not project.path(mc).is_file():
            problems.append(f"[field] mapconfig (lighting) not found: {mc}")
        if not (wm.get("bgi") or wm.get("obj")):
            problems.append("[field] a native scene needs a [walkmesh] (bgi or obj)")
    for layer in project.raw.get("layers", []):
        if "image" not in layer:
            problems.append("[[layers]] entry missing 'image'")
        elif not project.path(layer["image"]).is_file():
            problems.append(f"[[layers]] image not found: {layer['image']}")
    for i, n in enumerate(project.raw.get("npc", [])):
        if "pos" not in n:
            problems.append(f"[[npc]] {n.get('name', '#' + str(i))!r} has no position -- set "
                            f"pos = [x, z] in the field.toml, or place its marker in the Blender scene.")
        if "model" in n and n["model"] is not None:
            try:
                resolve_npc_model(n["model"])             # a GEO name must resolve (a raw id passes through)
            except ValueError as e:
                problems.append(f"[[npc]] {n.get('name', '#' + str(i))!r} model: {e}")
        arch = n.get("archetype") or n.get("preset")
        if arch is not None:
            try:
                _archetypes.resolve(arch)                 # a named archetype (or vivi/zidane) must be known
            except ValueError as e:
                problems.append(f"[[npc]] {n.get('name', '#' + str(i))!r} archetype: {e}")
    for gc in project.raw.get("gateway_carry", []):     # #2b: a verbatim story-gated door entry sidecar
        binref = gc.get("bin")
        if not binref:
            problems.append('[[gateway_carry]] needs bin = "<file>" (a verbatim entry sidecar, from import)')
        elif not project.path(binref).is_file():
            problems.append(f"[[gateway_carry]] entry sidecar not found: {binref}")
        rt = gc.get("retarget")
        if rt is not None and not isinstance(rt, dict):
            problems.append("[[gateway_carry]] retarget must be a table { <real id> = <new id> }")
    for gw in project.raw.get("gateway", []):
        if "to" not in gw:
            problems.append("[[gateway]] needs a 'to' (destination field id).")
        z = gw.get("zone", [])
        if len(z) not in (4, 5):
            problems.append(f"[[gateway]] zone must have 4 or 5 points (got {len(z)})")
        # on-exit story advance: set_scenario / set_flags fire when the player takes this exit
        _validate_story_writes(gw, "[[gateway]]", story_names, problems,
                               scenario_key="set_scenario", flags_key="set_flags")
    for ev in project.raw.get("event", []):
        z = ev.get("zone", [])
        if len(z) not in (4, 5):
            problems.append(f"[[event]] zone must have 4 or 5 points (got {len(z)})")
        if not any(k in ev for k in ("message", "give_item", "remove_item", "gil", "set_flag")):
            problems.append("[[event]] needs at least one action "
                            "(message / give_item / remove_item / gil / set_flag)")
        for k in ("give_item", "remove_item"):
            if k in ev:
                try:
                    _items.resolve(ev[k][0])
                except (ValueError, IndexError, TypeError) as e:
                    problems.append(f"[[event]] {k}: {e}")
        for k in ("received", "require_space"):
            if ev.get(k) and "give_item" not in ev:
                problems.append(f"[[event]] {k} only applies with a give_item (it's an item-chest nicety)")
    # [start_inventory] / [[equipment]] -- new-game starting state (mod-global CSV deltas on the entry field)
    si = project.raw.get("start_inventory")
    if si is not None:
        items_list = si.get("items") if isinstance(si, dict) else None
        if not isinstance(items_list, list) or not items_list:
            problems.append('[start_inventory] needs items = [["Potion", 10], ...] (the full starting bag)')
        else:
            for it in items_list:
                try:
                    _items.resolve(it[0] if isinstance(it, (list, tuple)) else it)
                except (ValueError, IndexError, TypeError) as e:
                    problems.append(f"[start_inventory] item: {e}")
    if project.raw.get("equipment"):
        from .content import equipment as _eqp
        for q, eq in enumerate(project.raw["equipment"]):
            if not isinstance(eq, dict):
                problems.append(f"[[equipment]] #{q} must be a table (character = \"steiner\", weapon = ...)")
                continue
            try:
                _eqp.resolve_set_id(eq.get("character"))
            except (ValueError, TypeError) as e:
                problems.append(f"[[equipment]] #{q}: {e}")
            for slot in _eqp.SLOTS:
                if slot in eq and str(eq[slot]).strip().lower() not in ("", "none", "-1"):
                    try:
                        _items.resolve(eq[slot])
                    except (ValueError, TypeError) as e:
                        problems.append(f"[[equipment]] #{q} {slot}: {e}")
    # [[battle_action]] / [[status]] -- mod-global CSV-delta rebalancing (structural lint; name->id + value
    # resolution happens at build, which has the install to read the base row).
    if project.raw.get("battle_action") or project.raw.get("status"):
        from .battle import actiondelta as _adelta
        for q, ba in enumerate(project.raw.get("battle_action", [])):
            problems += [f"[[battle_action]] #{q}: {p}" for p in _adelta.validate_entry(ba, kind="battle_action")]
        for q, st in enumerate(project.raw.get("status", [])):
            problems += [f"[[status]] #{q}: {p}" for p in _adelta.validate_entry(st, kind="status")]
    # [[battle_patch]] / [[battle_enemy]] / [[battle_attack]] -- the BattlePatch.txt by-name enemy/attack/scene
    # tuner (structural + range/encoder/selector checks; all install-free since names/ids are the author's).
    if project.raw.get("battle_patch") or project.raw.get("battle_enemy") or project.raw.get("battle_attack"):
        from .battle import battlepatch as _bp
        problems += _bp.validate_blocks(project.raw.get("battle_patch", []),
                                        project.raw.get("battle_enemy", []),
                                        project.raw.get("battle_attack", []))
    # [[character]] / [[leveling]] -- player-side balance CSV deltas (structural + range; name->id + base-row
    # read happen at build, which has the install). BaseStats per-id partial; Leveling whole-file (99 rows).
    if project.raw.get("character") or project.raw.get("leveling"):
        from .battle import characterdelta as _cdelta
        _chars = project.raw.get("character", [])
        _levels = project.raw.get("leveling", [])
        _chars = _chars if isinstance(_chars, list) else [_chars]      # never traceback on a malformed block
        _levels = _levels if isinstance(_levels, list) else [_levels]
        for q, c in enumerate(_chars):
            problems += [f"[[character]] #{q}: {p}" for p in _cdelta.validate_character(c)]
        for q, lv in enumerate(_levels):
            problems += [f"[[leveling]] #{q}: {p}" for p in _cdelta.validate_leveling(lv)]
    for la in project.raw.get("ladder", []):
        if la.get("navigable"):                      # NAVIGABLE (FF9's real ladder mechanism, recreated)
            rungs = la.get("rungs")
            if rungs is not None:                    # MULTI-RUNG (bent vine): rungs replace bottom/top
                if not (isinstance(rungs, (list, tuple)) and len(rungs) >= 2
                        and all(isinstance(p, (list, tuple)) and len(p) == 3 for p in rungs)):
                    problems.append("[[ladder]] navigable: rungs must be >=2 world points [x, z, y] (bottom..top)")
                elif rungs[0][2] == rungs[-1][2]:
                    problems.append("[[ladder]] navigable: rungs top and bottom must differ in height (y)")
            else:
                for k in ("bottom", "top"):
                    v = la.get(k)
                    if not (isinstance(v, (list, tuple)) and len(v) == 3):
                        problems.append(f"[[ladder]] navigable: {k} must be [x, z, y] (a world point WITH height)")
                b, t = la.get("bottom"), la.get("top")
                if (isinstance(b, (list, tuple)) and len(b) == 3
                        and isinstance(t, (list, tuple)) and len(t) == 3 and b[2] == t[2]):
                    problems.append("[[ladder]] navigable: top and bottom must differ in height (y)")
            z = la.get("zone")
            if z is not None and len(z) not in (3, 4, 5):
                problems.append(f"[[ladder]] navigable: zone (optional) must have 3-5 points, got {len(z)}")
            ta = la.get("top_action", "floor")
            if ta not in ("floor", "field", "worldmap"):
                problems.append(f"[[ladder]] navigable: top_action must be floor/field/worldmap, got {ta!r}")
            if ta == "field" and "top_field" not in la:
                problems.append('[[ladder]] navigable: top_action="field" needs top_field (the destination field id)')
            if ta == "field" and la.get("top_field") == project.raw.get("field", {}).get("id"):
                problems.append('[[ladder]] navigable: top_field cannot be this field\'s own id -- a self-loop '
                                'Field() is a no-op (it falls through to TerminateEntry and crashes). Warp to a DIFFERENT field.')
            if ta == "worldmap" and "top_worldmap" not in la:
                problems.append('[[ladder]] navigable: top_action="worldmap" needs top_worldmap (the world-map entry)')
            continue
        if "top" in la or "bottom" in la:           # EMULATED BIDIRECTIONAL (from-scratch, no real climb)
            for k in ("top", "bottom"):
                v = la.get(k)
                if not (isinstance(v, (list, tuple)) and len(v) in (2, 3)):
                    problems.append(f"[[ladder]] {k} must be [x, z] (or [x, z, y]) for a bidirectional "
                                    "ladder (a trigger zone + landing point at each end)")
            continue
        if "arc_from" in la or "arc_to" in la:      # ANIMATED ONE-WAY climb (jump-arc, perspective-correct)
            for k in ("arc_from", "arc_to"):
                v = la.get(k)
                if not (isinstance(v, (list, tuple)) and len(v) in (2, 3)):
                    problems.append(f"[[ladder]] {k} must be [x, z] or [x, z, y] for an animated climb")
            if len(la.get("zone", [])) not in (3, 4, 5):
                problems.append(f"[[ladder]] zone must have 3-5 points (the trigger), got {len(la.get('zone', []))}")
            continue
        z = la.get("zone", [])
        if len(z) not in (3, 4, 5):
            problems.append(f"[[ladder]] zone must have 3-5 points (the base trigger), got {len(z)}")
        climb = la.get("climb")
        if climb:                                   # FAITHFUL: a real ladder's climb (from import)
            if not project.path(climb).is_file():
                problems.append(f"[[ladder]] climb function file not found: {climb}")
        else:                                       # EMULATED one-way: teleport/hop to a destination
            t = la.get("to", [])
            if not (isinstance(t, (list, tuple)) and len(t) in (2, 3)):
                problems.append('[[ladder]] needs to = [x, z] (one-way), or top=+bottom= (bidirectional), '
                                'or climb = "<file>" (a real ladder\'s climb, from import)')
    for jp in project.raw.get("jump", []):              # navigable ledge/gap jumps (Ice Cavern style)
        z = jp.get("zone", [])
        if len(z) not in (3, 4, 5):
            problems.append(f"[[jump]] zone must have 3-5 points (the take-off trigger), got {len(z)}")
        jb = jp.get("jump")
        if not jb:
            problems.append('[[jump]] needs jump = "<file>" (a real jump arc, from `ff9mapkit import`)')
        elif not project.path(jb).is_file():
            problems.append(f"[[jump]] arc file not found: {jb}")
        trig = jp.get("trigger", "action")
        if trig not in ("action", "tread"):
            problems.append(f'[[jump]] trigger must be "action" (press) or "tread" (auto), got {trig!r}')
    su = project.raw.get("startup")                     # story-state presets ([startup]: assert the beat)
    if su is not None:
        if not isinstance(su, dict):
            problems.append("[startup] must be a table (scenario = N|\"area\" and/or flags = [{flag, value}])")
        else:
            _validate_story_writes(su, "[startup]", story_names, problems)
    oe = project.raw.get("on_entry")                     # field-load beats ([[on_entry]]: gated, once)
    if oe is not None:
        _validate_on_entry(oe, story_names, problems)
    pty = project.raw.get("party")                       # party membership ([party]: add/remove members)
    if pty is not None:
        _validate_party(pty, problems)
    for sp in project.raw.get("savepoint", []):         # synthesized save point (press -> Menu(4,0))
        z = sp.get("zone", [])
        if len(z) not in (4, 5):
            problems.append(f"[[savepoint]] zone must have 4 or 5 points (the press area), got {len(z)}")
    for i, sh in enumerate(project.raw.get("shop", [])):   # custom shop ([[shop]]: inventory CSV + opener)
        sid = sh.get("id")
        if not isinstance(sid, int) or isinstance(sid, bool):
            problems.append(f"[[shop]] #{i} needs an integer id (the shop slot, >= {_shop.FIRST_CUSTOM_SHOP})")
            continue
        if not (0 <= sid <= _shop.MAX_SHOP_ID):
            problems.append(f"[[shop]] id {sid} out of range 0..{_shop.MAX_SHOP_ID} "
                            f"(it is also the Menu sub-id, a single byte)")
        sells = sh.get("sells")
        if not sells:
            problems.append(f"[[shop]] id {sid} has no `sells` items (a shop needs an inventory)")
        else:
            resolved = []
            for it in sells:
                try:
                    resolved.append(_items.resolve(it))
                except (ValueError, IndexError, TypeError) as e:
                    problems.append(f"[[shop]] id {sid} sells: {e}")
            # all entries resolve to NoItem (255) -> shop_rows drops them -> an empty shop (validate's raw
            # `not sells` check above passes a non-empty list of 255s). Catch it here, post-resolution.
            if resolved and all(r == _shop.NO_ITEM for r in resolved):
                problems.append(f"[[shop]] id {sid} sells only NoItem (255) -- a shop needs at least one real item")
        z = sh.get("zone")
        if z is not None and len(z) not in (4, 5):
            problems.append(f"[[shop]] id {sid} zone must have 4 or 5 points (the press area), got {len(z)}")
    choice_npcs = {ch["npc"] for ch in project.raw.get("choice", []) if "npc" in ch}
    for i, n in enumerate(project.raw.get("npc", [])):     # a shopkeeper NPC ([[npc]] opens_shop = id)
        os_ = n.get("opens_shop")
        if os_ is None:
            continue
        if not isinstance(os_, int) or isinstance(os_, bool) or not (0 <= os_ <= _shop.MAX_SHOP_ID):
            problems.append(f"[[npc]] {n.get('name', '#' + str(i))!r} opens_shop must be a shop id "
                            f"0..{_shop.MAX_SHOP_ID}, got {os_!r}")
        # both a [[choice]] AND opens_shop on one NPC: build's talk-body selection takes the choice and
        # SILENTLY drops the shop opener (the `elif`). Flag it so the conflict isn't a hidden no-op.
        if n.get("name") in choice_npcs:
            problems.append(f"[[npc]] {n.get('name')!r} has both a [[choice]] and opens_shop -- only one talk "
                            f"action is possible; the shop opener would be dropped (remove one)")
    for sm in project.raw.get("save_moogle", []):       # a carried (imported) save Moogle (docs/SAVEPOINT.md)
        if sm.get("carried"):                           # the cluster lives in the [[object]]/[[player_func]] blocks
            if not project.raw.get("object"):
                problems.append("[[save_moogle]] carried=true needs its cluster -- the [[object]] blocks from "
                                "`import --save-moogle` (the hidden Moogle + book/feather/tent)")
            if not project.raw.get("player_func"):
                problems.append("[[save_moogle]] carried=true needs the Moogle's pose funcs -- the [[player_func]] "
                                "blocks from `import --save-moogle` (tags 13/14/15)")
    obj_donor_idx = {ob.get("donor_idx") for ob in project.raw.get("object", [])}
    for ob in project.raw.get("object", []):            # faithful object carry (verbatim .eb entry graft)
        binref = ob.get("bin")
        if not binref:
            problems.append('[[object]] needs bin = "<file>" (a verbatim entry sidecar, from `ff9mapkit import`)')
        elif not project.path(binref).is_file():
            problems.append(f"[[object]] entry sidecar not found: {binref}")
        elif not project.path(binref).read_bytes()[:2]:
            problems.append(f"[[object]] entry sidecar is empty: {binref}")
        # STARTSEQ-helper closure (docs/OBJECT_CARRY.md S2 v1.5): each carried helper must exist, be a benign
        # self-contained type-1 Seq, and NOT also be armed as an [[object]] (a double-append). The kit's own
        # emit is always consistent; these guard a hand-edited project.
        for h in (ob.get("seqs") or []):
            sb = h.get("bin")
            if not sb:
                problems.append('[[object]] seqs entry needs bin = "<file>" (a STARTSEQ helper sidecar)')
                continue
            if not project.path(sb).is_file():
                problems.append(f"[[object]] seqs helper sidecar not found: {sb}")
                continue
            why = _seq_helper_problem(project.path(sb).read_bytes())
            if why:
                problems.append(f"[[object]] seqs helper {sb}: {why}")
            if h.get("entry") in obj_donor_idx:
                problems.append(f"[[object]] seqs helper entry {h.get('entry')} is also a carried [[object]] "
                                f"(double-append) -- it must be either armed OR Seq-launched, not both")
    pf_tags = {0, 1}                                     # the fork player's own tags + the grafted donor tags
    for pf in project.raw.get("player_func", []):        # player-function graft (carried-object interactions)
        binref = pf.get("bin")
        if not binref:
            problems.append('[[player_func]] needs bin = "<file>" (a player-func body, from import --graft-player-funcs)')
        elif not project.path(binref).is_file():
            problems.append(f"[[player_func]] body sidecar not found: {binref}")
        if "donor_tag" not in pf:
            problems.append("[[player_func]] needs donor_tag = <int> (the donor player function tag it grafts)")
        else:
            pf_tags.add(int(pf["donor_tag"]))
    # dangling-tag guard (the softlock case): a carried object that RunScripts the PLAYER at a tag NOT being
    # grafted (nor 0/1) would dispatch into a nonexistent func -> freeze. Decode each object's verbatim entry
    # and flag any player-call tag outside pf_tags. (The kit's own emit is consistent; this catches hand-edits.)
    for ob in project.raw.get("object", []):
        binref, dpe = ob.get("bin"), ob.get("donor_player_entry")
        if not binref or not project.path(binref).is_file():
            continue
        for tag in _entry_player_call_tags(project.path(binref).read_bytes(), dpe, ob.get("carry_tags")):
            if tag not in pf_tags:
                problems.append(f"[[object]] {binref}: RunScripts player tag {tag} but no [[player_func]] grafts "
                                f"it (would dangle/softlock) -- import with --graft-player-funcs, or it stays init_only")
    ct = project.raw.get("carry_text")                  # faithful text carry (import --carry-text)
    if ct:
        binref = ct.get("bin")
        if not binref:
            problems.append('[carry_text] needs bin = "<file>" (a carry sidecar, from `ff9mapkit import --carry-text`)')
        elif not project.path(binref).is_file():
            problems.append(f"[carry_text] sidecar not found: {binref}")
        else:
            try:
                plan = project.carry_text_plan()
            except (ValueError, KeyError, OSError) as e:
                problems.append(f"[carry_text] sidecar {binref} is malformed: {e}")
                plan = []
            from .content import textcarry as _textcarry
            for e in plan:
                if not (_textcarry.CARRY_BASE_TXID <= e.new_txid <= 0xFFFF):
                    problems.append(f"[carry_text] carried txid {e.new_txid} out of the safe band "
                                    f"[{_textcarry.CARRY_BASE_TXID}, 65535] (would collide with base/authored text)")
    for m in project.raw.get("marker", []):
        if "name" not in m or "pos" not in m:
            problems.append("[[marker]] needs a 'name' and pos = [x, z] (a named point for movement)")
    # dialogue choices: talk to an NPC -> pick an option -> branch. v1 attaches to an NPC by name.
    npc_names = {n.get("name") for n in project.raw.get("npc", [])}
    for c, ch in enumerate(project.raw.get("choice", [])):
        has_npc, has_zone = "npc" in ch, "zone" in ch
        if has_npc == has_zone:                  # need exactly one trigger
            problems.append(f"[[choice]] #{c} needs exactly one of npc = \"<name>\" (talk) "
                            f"or zone = [...4 corners] (walk-in)")
        if has_npc and ch["npc"] not in npc_names:
            problems.append(f"[[choice]] #{c} npc {ch['npc']!r} is not a defined [[npc]] name")
        if has_zone and len(ch.get("zone") or []) not in (4, 5):
            problems.append(f"[[choice]] #{c} zone must have 4 or 5 points "
                            f"(got {len(ch.get('zone') or [])})")
        if has_zone and ch.get("trigger", "action") not in ("action", "walk"):
            problems.append(f"[[choice]] #{c} trigger must be \"action\" (press) or \"walk\" "
                            f"(auto-pop), got {ch.get('trigger')!r}")
        if not str(ch.get("prompt", "")).strip():
            problems.append(f"[[choice]] #{c} needs a 'prompt' (the question text)")
        opts = ch.get("options", [])
        if not isinstance(opts, list) or len(opts) < 2:
            problems.append(f"[[choice]] #{c} needs at least 2 options")
        else:
            for oi, o in enumerate(opts):
                if not str(o.get("text", "")).strip():
                    problems.append(f"[[choice]] #{c} option {oi} needs 'text' (the menu row)")
                for key in ("give_item", "remove_item", "set_flag"):
                    if key in o and (not isinstance(o[key], list) or len(o[key]) < 1):
                        problems.append(f"[[choice]] #{c} option {oi} {key} must be a list, "
                                        f"e.g. [\"Potion\", 1]")
                for key in ("give_item", "remove_item"):
                    if isinstance(o.get(key), list) and o[key]:
                        try:
                            _items.resolve(o[key][0])
                        except (ValueError, TypeError) as e:
                            problems.append(f"[[choice]] #{c} option {oi} {key}: {e}")
                if "requires_flag" in o and "requires_flag_clear" in o:
                    problems.append(f"[[choice]] #{c} option {oi} can't have BOTH requires_flag and "
                                    f"requires_flag_clear -- pick one (shown when SET vs when CLEAR).")
                if "warp" in o and not (isinstance(o["warp"], int) and o["warp"] > 0):
                    problems.append(f"[[choice]] #{c} option {oi} warp {o['warp']!r} must be a field id "
                                    f"(a positive int -- the World-Hub journey destination)")
                if "set_scenario" in o and not (isinstance(o["set_scenario"], int) and 0 <= o["set_scenario"] <= 32767):
                    problems.append(f"[[choice]] #{c} option {oi} set_scenario {o['set_scenario']!r} must be "
                                    f"a ScenarioCounter value 0..32767")
        if isinstance(opts, list) and opts:
            n = len(opts)
            d = ch.get("default")
            if d is not None and not (isinstance(d, int) and 0 <= d < n):
                problems.append(f"[[choice]] #{c} default {d!r} must be an option index 0..{n-1}")
            cv = ch.get("cancel")
            if cv is not None and not (isinstance(cv, int) and -1 <= cv < n):
                problems.append(f"[[choice]] #{c} cancel {cv!r} must be an option index -1..{n-1} "
                                f"(-1 = last row)")
            if all(o.get("disabled") for o in opts):
                problems.append(f"[[choice]] #{c} has every option disabled (nothing selectable)")
        t = ch.get("tail")
        if t is not None and t not in _text.TAIL_CODES:
            problems.append(f"[[choice]] #{c} tail {t!r} is not a valid TAIL code")
    # speaker (a name prefix) + tail (the dialogue-window pointer) are optional dialogue modifiers
    for label, items in (("[[npc]]", project.raw.get("npc", [])),
                         ("[[event]]", project.raw.get("event", []))):
        for it in items:
            t = it.get("tail")
            if t is not None and t not in _text.TAIL_CODES:
                problems.append(f"{label} tail {t!r} is not a valid TAIL code "
                                f"({', '.join(sorted(_text.TAIL_CODES))})")
    cs = project.raw.get("cutscene")
    if cs is not None:
        steps = cs.get("steps")
        actor = cs.get("actor")
        global_keys = ("say", "wait", "set_flag")
        actor_keys = ("walk", "path", "teleport", "animation", "turn", "face_player")
        allowed = global_keys + (actor_keys if actor else ())
        actor_npc = next((n for n in project.raw.get("npc", []) if n.get("name") == actor), None)
        anim_token = (actor_npc.get("preset") or actor_npc.get("archetype")) if actor_npc else None
        move_reg = _position_registry(project)
        if not isinstance(steps, list) or not steps:
            problems.append("[cutscene] needs a non-empty steps = [ {say=...}, {wait=...}, ... ] list")
        else:
            for k, s in enumerate(steps):
                present = [key for key in global_keys + actor_keys if key in s]
                if len(present) != 1:
                    problems.append(f"[cutscene] step {k} needs exactly one action "
                                    f"({' / '.join(allowed)})")
                elif present[0] not in allowed:
                    problems.append(f"[cutscene] step {k} uses {present[0]!r}, which needs an actor -- "
                                    f"set [cutscene] actor = \"<npc name>\" (it runs in that NPC).")
                t = s.get("tail")
                if t is not None and t not in _text.TAIL_CODES:
                    problems.append(f"[cutscene] step {k} tail {t!r} is not a valid TAIL code")
                a = s.get("animation")                    # a named gesture must resolve on the actor's model
                if isinstance(a, str) and not a.strip().isdigit():
                    if anim_token not in _animations.TOKENS:
                        problems.append(f"[cutscene] step {k} animation {a!r} is a name, but the actor has no "
                                        f"known preset -- use a numeric id or give the NPC a preset.")
                    else:
                        try:
                            _animations.resolve(anim_token, a)
                        except ValueError as e:
                            problems.append(f"[cutscene] step {k}: {e}")
                for mk in ("walk", "teleport"):           # a named move target must resolve to a point
                    if isinstance(s.get(mk), str):
                        try:
                            _resolve_point(s[mk], move_reg)
                        except ValueError as e:
                            problems.append(f"[cutscene] step {k}: {e}")
                if isinstance(s.get("path"), list):        # each path waypoint must resolve too
                    if len(s["path"]) < 1:
                        problems.append(f"[cutscene] step {k}: path needs at least one waypoint")
                    for elem in s["path"]:
                        if isinstance(elem, str):
                            try:
                                _resolve_point(elem, move_reg)
                            except ValueError as e:
                                problems.append(f"[cutscene] step {k}: {e}")
        if actor is not None and actor not in {n.get("name") for n in project.raw.get("npc", [])}:
            problems.append(f"[cutscene] actor {actor!r} is not a defined [[npc]] name")
    return problems


def lint_logic(project: FieldProject) -> list[str]:
    """Story/flag sanity checks on the merged project -- catch logic that silently can't work as rooms
    grow. Advisory (returned as build warnings; the `lint` CLI exits non-zero on any). Checks:
      * a `requires_flag` (appears/fires when SET) that NO event ever sets -> dead content;
      * an explicit flag index that collides with an auto-allocated `once`-event flag (base 200+);
      * duplicate entity names (the scene<->field merge key would be ambiguous)."""
    raw = project.raw
    out = []
    _auto = _FlagAlloc(getattr(project, "flag_base", None))   # mirror build_script's auto-allocation EXACTLY

    # flags that can ever become SET: event set_flag targets + each once-event's guard flag.
    settable, auto_once, explicit = set(), set(), set()
    counter = 0
    for ev in raw.get("event", []):
        if "set_flag" in ev:
            settable.add(int(ev["set_flag"][0])); explicit.add(int(ev["set_flag"][0]))
        if ev.get("once", True):                       # mirror build_script's auto-allocation exactly
            if "flag" in ev:
                settable.add(int(ev["flag"])); explicit.add(int(ev["flag"]))
            else:
                auto_once.add(_auto.event(counter))
            counter += 1
    cs = raw.get("cutscene")           # a cutscene also sets flags (set_flag steps + its own once-flag)
    if cs:
        for step in cs.get("steps", []):
            if "set_flag" in step:
                settable.add(int(step["set_flag"][0])); explicit.add(int(step["set_flag"][0]))
        if cs.get("once", True):
            f = int(cs["flag"]) if "flag" in cs else _auto.cutscene()
            settable.add(f); explicit.add(f)
    choice_counter = 0
    for ch in raw.get("choice", []):           # a choice option can set a story flag too
        for o in ch.get("options", []):
            if "set_flag" in o:
                settable.add(int(o["set_flag"][0])); explicit.add(int(o["set_flag"][0]))
        if "zone" in ch and (ch.get("trigger") or "action") == "walk":   # only walk-trigger uses a gate flag
            if "flag" in ch:
                settable.add(int(ch["flag"])); explicit.add(int(ch["flag"]))
            else:
                auto_once.add(_auto.choice(choice_counter))
                choice_counter += 1
    for gw in raw.get("gateway", []):          # a gateway's on-exit set_flags SETS story flags (#3 advance)
        for p in gw.get("set_flags", []) or []:
            if isinstance(p, dict) and isinstance(p.get("flag"), int) and int(p.get("value", 1)):
                settable.add(int(p["flag"])); explicit.add(int(p["flag"]))
    su = raw.get("startup")                    # [startup] presets a flag SET unconditionally at field load
    if isinstance(su, dict):
        for p in su.get("flags", []) or []:
            if isinstance(p, dict) and isinstance(p.get("flag"), int) and int(p.get("value", 1)):
                settable.add(int(p["flag"])); explicit.add(int(p["flag"]))
    for k, h in enumerate(raw.get("on_entry", [])):   # [[on_entry]] sets flags on entry + has a once-flag
        if not isinstance(h, dict):
            continue
        for p in h.get("set_flags", []) or []:
            if isinstance(p, dict) and isinstance(p.get("flag"), int) and int(p.get("value", 1)):
                settable.add(int(p["flag"])); explicit.add(int(p["flag"]))
        if h.get("once", True):
            if isinstance(h.get("flag"), int):
                settable.add(int(h["flag"])); explicit.add(int(h["flag"]))
            elif _auto.base is None:                   # campaign members need an explicit flag (build enforces)
                auto_once.add(_auto.on_entry(k))
    settable |= auto_once

    # everything that READS a flag (require SET needs a setter; require CLEAR is fine by default).
    need_set = []
    for coll, label in (("npc", "NPC"), ("gateway", "gateway"), ("event", "event")):
        for i, e in enumerate(raw.get(coll, [])):
            gf, gs = _gate_of(e)
            if gf is None:
                continue
            explicit.add(gf)
            who = e.get("name") or e.get("to") or f"#{i}"
            if gs:
                need_set.append((gf, f"{label} {who!r}"))
    for c, ch in enumerate(raw.get("choice", [])):     # a choice option hidden until its flag is SET
        for oi, o in enumerate(ch.get("options", [])):
            if "requires_flag" in o:
                explicit.add(int(o["requires_flag"]))
                need_set.append((int(o["requires_flag"]), f"choice #{c} option {oi}"))
    for k, h in enumerate(raw.get("on_entry", [])):    # an on_entry beat gated on a flag being SET
        if isinstance(h, dict) and isinstance(h.get("requires_flag"), int):
            explicit.add(int(h["requires_flag"]))
            if h.get("requires_set", True):
                need_set.append((int(h["requires_flag"]), f"on_entry #{k}"))

    for flag, who in need_set:
        if flag not in settable:
            out.append(f"{who} requires flag {flag}, but no event sets it -- it can never appear/fire. "
                       f"Add an event with set_flag = [{flag}, 1] (or fix the flag index).")
    clash = sorted(explicit & auto_once)
    if clash:
        out.append(f"flag index(es) {clash} are used explicitly AND auto-allocated for 'once' events "
                   f"(base {_event.EVENT_FLAG_BASE}+) -- they will clash. Put an explicit `flag = N` on "
                   f"your once-events, or move story flags out of the {_event.EVENT_FLAG_BASE}+ band.")
    for coll, label in (("npc", "NPC"), ("gateway", "gateway"), ("event", "event")):
        counts = {}
        for e in raw.get(coll, []):
            if e.get("name"):
                counts[e["name"]] = counts.get(e["name"], 0) + 1
        for nm, c in sorted(counts.items()):
            if c > 1:
                out.append(f"duplicate {label} name {nm!r} ({c}x) -- the scene<->field merge by name "
                           f"will be ambiguous; give each a unique name.")

    # #2 (FORK_FIDELITY.md): collapsed story-branch doors. The scanner flattens a real
    # if(flag){Field(A)}else{Field(B)} into 2+ [[gateway]] blocks at the SAME zone; ungated they ALL arm in the
    # fork, so the player hits whichever fires first (usually the wrong branch). Warn unless each is gated.
    by_zone = {}
    for gw in raw.get("gateway", []):
        z = tuple(tuple(p) for p in gw.get("zone", []))
        if z:
            by_zone.setdefault(z, []).append(gw)
    for group in by_zone.values():
        if len(group) > 1 and any(_gate_of(g)[0] is None for g in group):
            tos = ", ".join(str(g.get("to")) for g in group)
            out.append(f"{len(group)} gateways share one zone (exits to {tos}) but not all are gated -- they "
                       f"will ALL arm and the player hits the wrong branch. This is a collapsed story-branch "
                       f"door; gate each with requires_flag / requires_flag_clear so only the right one fires "
                       f"per story beat. (FORK_FIDELITY.md #2)")

    # #5 (FORK_FIDELITY.md): a carried TALKABLE object whose donor dialogue isn't carried -> WRONG/missing
    # text in the fork. A plain import (no --carry-text) keeps a self-contained talk handler (a bare
    # WindowSync) but doesn't ship its words, so the WindowSync points at a donor txid the fork's text block
    # doesn't hold. (The build remaps a carried window to the [carry_text] band; an UN-carried one is the gap.)
    # The dangling-PLAYER-tag softlock half of #5 is already a build-blocking validate() problem.
    objs = raw.get("object", [])
    if objs:
        try:
            carried = {e.donor_txid for e in project.carry_text_plan()}
        except Exception:
            carried = set()
        for ob in objs:
            binref = ob.get("bin")
            if not binref or not project.path(binref).is_file():
                continue
            shown = _entry_window_txids(project.path(binref).read_bytes(), ob.get("carry_tags"))
            missing = sorted(t for t in shown if t not in carried)
            if missing:
                out.append(f"[[object]] {binref} ({ob.get('kind', 'object')}) shows dialogue the fork doesn't "
                           f"carry (donor txid {missing}) -- it will render WRONG/missing text in-game. Import "
                           f"with --carry-text (ships the donor's lines + remaps the windows), or author the line.")

    # (a --verbatim fork now fires BOTH [startup] and [[on_entry]] -- state-advances AND narration messages
    # (the message is appended to the donor .mes above its txids, build._verbatim_on_entry_messages) -- so
    # there is no longer a verbatim-specific on_entry limitation to warn about.)

    # pre-choose: a choice's `default` can't sit at/after a greyed (`disabled`) row. The engine
    # (SetChooseParam) converts the absolute default into the AVAILABLE-row index, but Dialog then reads
    # it as ABSOLUTE -- so a default past a disabled row falls back to the first available row instead of
    # the one you meant. (Confirmed by an in-engine probe.) Warn rather than silently mis-highlight.
    for c, ch in enumerate(raw.get("choice", [])):
        d = ch.get("default")
        if isinstance(d, int) and d > 0:
            bad = [i for i, o in enumerate(ch.get("options", []))
                   if (o.get("disabled") or "requires_flag" in o or "requires_flag_clear" in o) and i <= d]
            if bad:
                out.append(f"[[choice]] #{c} default = {d} can't be honored: option(s) {bad} at/before it "
                           f"can be hidden, so FF9 highlights the first available row instead. Use default = 0 "
                           f"or don't hide rows before the default (engine limitation).")

    # dialogue that won't fit on screen. With wrapping ON, only an unbreakable over-wide word can
    # still overflow; with wrapping OFF, any hand-written line over the budget will run off-screen.
    wrap = _wrap_width(project)
    texts = []
    for n in raw.get("npc", []):
        if "dialogue" in n:
            texts.append((f"NPC {n.get('name', '?')!r}", _text.with_speaker(n.get("speaker"), n["dialogue"])))
    for ev in raw.get("event", []):
        if "message" in ev:
            texts.append((f"event {ev.get('name', '?')!r}", _text.with_speaker(ev.get("speaker"), ev["message"])))
    for k, s in enumerate(raw.get("cutscene", {}).get("steps", [])):
        if "say" in s:
            texts.append((f"cutscene say #{k}", _text.with_speaker(s.get("speaker"), s["say"])))
    for who, t in texts:
        if wrap is None:                       # wrapping disabled: every over-budget line overflows
            for ln in t.replace("[PAGE]", "\n").split("\n"):
                if _text.measure(ln) > _text.DEFAULT_WRAP_WIDTH:
                    out.append(f"{who} dialogue line is wider than the screen and [dialogue] wrap is "
                               f"off -- add line breaks (\\n) or enable wrapping. Line: {ln!r}")
        else:
            for ln in _text.overflow_lines(t, wrap):
                out.append(f"{who} has a word too wide to fit one line ({ln!r}) -- it will overflow; "
                           f"shorten it or raise [dialogue] wrap.")

    # reference-data sanity (Info Hub): an [[npc]] model id / animation id the engine won't recognise.
    # A model NAME is handled by validate() (fatal); here we WARN on a raw id outside the known tables
    # (it may be valid -- the tables aren't a hard whitelist -- but a typo usually isn't).
    def _is_raw_int(v):
        return (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, str) and v.strip().lstrip("-").isdigit())
    for i, n in enumerate(raw.get("npc", [])):
        mv = n.get("model")
        if mv is not None and _is_raw_int(mv) and _catalog.model(int(mv)) is None:
            out.append(f"[[npc]] {n.get('name', '#' + str(i))!r} model id {int(mv)} isn't in the model table "
                       f"-- it may not render. Run `ff9mapkit models` to find a valid id/name.")
        for slot, aid in (n.get("anims") or {}).items():
            if _catalog.animation_name(aid) is None:
                out.append(f"[[npc]] {n.get('name', '#' + str(i))!r} anims[{slot!r}] = {aid!r} isn't a known "
                           f"animation id. Run `ff9mapkit models <name>` to list a model's gestures.")
    for k, s in enumerate(raw.get("cutscene", {}).get("steps", [])):
        a = s.get("animation")
        if _is_raw_int(a) and _catalog.animation_name(int(a)) is None:
            out.append(f"[cutscene] step {k} animation id {a} isn't a known animation id "
                       f"(run `ff9mapkit models <character>` to list gestures).")
    return out


def lint_flag_bands(project: FieldProject) -> list[str]:
    """Warn when a RAW story-flag index lands in a reserved ``gEventGlobal`` region -- the treasure-chest
    'opened' bitfield (8376-8511), the byte-23 menu handshake, the worldmap-unlock bits, or the choice-mask
    scratch -- where a WRITE corrupts real save/engine state and a READ is meaningless. Named ``[[flag]]``s
    are already validated into the safe custom band (``flags.resolve_project_flags``); this catches the
    literal indices that bypass that path (``set_flag = [N, 1]`` / a hand-written once ``flag = N`` /
    ``requires_flag = N``). Lint-only -- NOT run during the build, so the golden output is byte- AND
    warning-identical."""
    raw = project.raw
    out: list[str] = []

    def _flag_index(v):
        """The flag index from a ``set_flag`` value -- ``[idx, val]`` (the documented shape) or a bare
        ``idx`` -- or None for an empty/odd value. Defensive so a malformed toml never crashes the lint."""
        if isinstance(v, (list, tuple)):
            return v[0] if v else None
        return v

    def _write(idx, who):
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return
        if _flags.is_reserved(idx):
            r = _flags.bit_region(idx)
            out.append(f"{who} writes story flag {idx}, inside FF9's reserved '{r.name}' region "
                       f"({r.meaning}) -- writing here corrupts real save/engine state. Use a named "
                       f"[[flag]] (auto-allocated into the safe band) or an index >= "
                       f"{_flags.FIRST_SAFE_FLAG}.")

    def _read(idx, who):
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return
        if _flags.CHEST_FLAG_LO <= idx <= _flags.CHEST_FLAG_HI:
            out.append(f"{who} gates on flag {idx}, in the treasure-chest 'opened' bitfield (bits "
                       f"{_flags.CHEST_FLAG_LO}-{_flags.CHEST_FLAG_HI}) -- those are real chest state set by "
                       f"a shared dispatch block in ~48 fields, so gating on them couples your logic to FF9's "
                       f"chest behavior. Gate on a named [[flag]] instead. (advisory)")

    for k, ev in enumerate(raw.get("event", [])):
        who = f"event {ev.get('name', '#' + str(k))!r}"
        if "set_flag" in ev:
            _write(_flag_index(ev["set_flag"]), who)
        if "flag" in ev and ev.get("once", True):
            _write(ev["flag"], who)
        gf, _gs = _gate_of(ev)
        if gf is not None:
            _read(gf, who)
    for k, n in enumerate(raw.get("npc", [])):
        gf, _gs = _gate_of(n)
        if gf is not None:
            _read(gf, f"NPC {n.get('name', '#' + str(k))!r}")
    for p in raw.get("prop", []):                 # props gate exactly like NPCs (same _gate_of read path)
        gf, _gs = _gate_of(p)
        if gf is not None:
            _read(gf, f"prop {p.get('prop', p.get('name', '?'))!r}")
    for gw in raw.get("gateway", []):
        gf, _gs = _gate_of(gw)
        if gf is not None:
            _read(gf, f"gateway -> {gw.get('to')}")
        for i, p in enumerate(gw.get("set_flags", []) or []):   # on-exit story advance (set/clear bits)
            if isinstance(p, dict) and "flag" in p:
                _write(p["flag"], f"gateway -> {gw.get('to')} set_flags #{i}")
    cs = raw.get("cutscene")
    if cs:
        for j, s in enumerate(cs.get("steps", [])):
            if "set_flag" in s:
                _write(_flag_index(s["set_flag"]), f"cutscene step #{j}")
        if "flag" in cs and cs.get("once", True):
            _write(cs["flag"], "cutscene")
    for c, ch in enumerate(raw.get("choice", [])):
        if "flag" in ch and (ch.get("trigger") or "action") == "walk":
            _write(ch["flag"], f"choice #{c}")
        for oi, o in enumerate(ch.get("options", [])):
            if "set_flag" in o:
                _write(_flag_index(o["set_flag"]), f"choice #{c} option {oi}")
            if "requires_flag" in o:
                _read(o["requires_flag"], f"choice #{c} option {oi}")
    su = raw.get("startup")                            # [startup] presets assert real flags by design, but
    if isinstance(su, dict):                           # a preset into a RESERVED region still corrupts state
        for i, p in enumerate(su.get("flags", []) or []):
            if isinstance(p, dict) and "flag" in p:
                _write(p["flag"], f"[startup] preset #{i}")
    for k, h in enumerate(raw.get("on_entry", [])):    # [[on_entry]] beats write (set_flags / once-flag)
        if not isinstance(h, dict):                     # + read (requires_flag) story flags
            continue
        for i, p in enumerate(h.get("set_flags", []) or []):
            if isinstance(p, dict) and "flag" in p:
                _write(p["flag"], f"[[on_entry]] #{k} set_flags #{i}")
        if "flag" in h and h.get("once", True):
            _write(h["flag"], f"[[on_entry]] #{k} once-flag")
        if "requires_flag" in h:
            _read(h["requires_flag"], f"[[on_entry]] #{k}")
    return out


@dataclass
class LintReport:
    """Every offline check in one structured pass (the ``ff9mapkit lint`` command). ``errors`` are fatal
    schema problems (a build can't proceed); the rest are advisory warnings grouped by what they're about.
    ``source`` notes how the walkmesh was resolved (custom scene / BG-borrow / not resolvable)."""
    errors: list = _dc_field(default_factory=list)        # validate(): schema / structural (build-blocking)
    logic: list = _dc_field(default_factory=list)         # lint_logic(): story flags, dialogue, dup names
    flags: list = _dc_field(default_factory=list)         # lint_flag_bands(): reserved-band flag use
    placement: list = _dc_field(default_factory=list)     # verify_walkmesh(): geometry/placement/layer/cutscene
    camera: list = _dc_field(default_factory=list)         # camera pitch outside the supported range
    source: str = "?"

    @property
    def warnings(self) -> list:
        return self.logic + self.flags + self.placement + self.camera

    @property
    def ok(self) -> bool:
        return not self.errors and not self.warnings


def lint_all(project: FieldProject) -> LintReport:
    """Run EVERY offline validator in one pass and return a :class:`LintReport`: schema (:func:`validate`),
    story/flag logic (:func:`lint_logic` + :func:`lint_flag_bands`), walkmesh geometry + content placement +
    layer art + cutscene movement (:func:`verify_walkmesh`), and camera pitch range. Degrades gracefully --
    a project whose camera/walkmesh can't resolve still returns the schema + logic results, with the resolve
    failure recorded as an error (so one broken section never masks the others). This is the single source
    of truth behind the ``lint`` CLI; a clean ``lint_all`` is what a clean build expects."""
    rep = LintReport(errors=validate(project), logic=lint_logic(project), flags=lint_flag_bands(project))
    # `lint` runs against arbitrary user TOML + (for forks) game-derived binaries, so resolving the
    # camera/walkmesh can fail in many ways (a missing borrow .bgx -> FileNotFoundError, a malformed quad
    # -> TypeError, a truncated .bgi -> struct.error, ...). A linter must NEVER traceback on bad input --
    # any resolve failure is itself a finding -- so both resolve blocks catch broadly and report instead.
    try:
        wm = verify_walkmesh(project)
        rep.source = wm.get("source", "?")
        # the "no walkmesh to verify" note (a BG-borrow without a custom walkmesh) is informational, not a
        # problem -- the engine uses the real field's mesh -- so it folds into the source, not the warnings.
        rep.placement = [w for w in wm.get("warnings", []) if "no walkmesh to verify" not in w]
        if len(rep.placement) != len(wm.get("warnings", [])):
            rep.source += " (no custom walkmesh -- geometry/placement checks skipped)"
    except Exception as e:                    # noqa: BLE001 -- never-crash contract (see comment above)
        rep.source = "not resolvable"
        rep.errors.append(f"couldn't resolve the camera/walkmesh to run geometry checks: "
                          f"{type(e).__name__}: {e}")
    try:
        cams = resolve_cameras(project)
        for ci, c in enumerate(cams):
            w = cam.pitch_warning(cam.pitch_deg(c))
            if w:
                rep.camera.append((f"camera #{ci}: " if len(cams) > 1 else "") + w)
    except Exception:                         # noqa: BLE001 -- the same resolve failure is already an error
        pass                                  # (reported by validate() and/or the geometry block above)
    return rep


def resolve_npc_model(value):
    """Resolve an ``[[npc]] model`` value to the numeric model id ``SetModel`` takes.

    Accepts a raw id (int / digit string -> passed through unchanged, so existing fields and the golden
    builds stay byte-identical) OR an exact GEO model name ('GEO_NPC_F0_BAR', from `ff9mapkit models`)
    resolved via :mod:`ff9mapkit.catalog`. ``None`` -> ``None`` (keep the cloned player's model). Raises
    ValueError with near-miss suggestions on an unknown name (``validate`` surfaces this cleanly before
    the build runs). A raw id outside the model table passes through here and is flagged as a lint
    warning. (For a playable character by friendly name use ``preset = "vivi"`` instead.)"""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("[[npc]] model cannot be a boolean")
    if isinstance(value, int) or str(value).strip().isdigit():
        return int(value)
    return _catalog.resolve_model(value)


def _resolve_prop_pose(mid, pose):
    """A ``[[prop]] pose`` -> the animation id the prop is held at. ``pose`` may be an action NAME
    ('close', 'save_open' -- resolved via the model->anim catalog), a raw id, or None. When omitted we
    pick a sensible *resting* pose, preferring a real idle/closed state over the 'b'/'p' bind pose (the
    bind pose reads as an OPEN chest / a bare moogle feather -- the in-game-verified gotcha)."""
    actions = _catalog.animations_for_model(mid) if mid is not None else {}
    if isinstance(pose, str):
        if pose.strip().isdigit():
            return int(pose)                       # a raw clip id as a string (e.g. a real SetStandAnimation id)
        if pose in actions:
            return actions[pose]
        raise ValueError(f"[[prop]] pose {pose!r} isn't an action of this model "
                         f"(have: {', '.join(sorted(actions)) or 'none'})")
    if pose is not None:
        return int(pose)
    for cand in ("idle", "close", "stand", "save_open", "b", "p"):   # resting-state preference
        if cand in actions:
            return actions[cand]
    return actions[sorted(actions)[0]] if actions else 0


def _resolve_held_model(value):
    """A ``[[npc]] holds`` entry -> the held prop's model id. ``value`` is a prop-archetype name
    ('cup', 'sword', 'glass') or a model id / GEO name ('GEO_ACC_F0_GRS')."""
    if _prop_archetypes.is_prop_archetype(value):
        return _prop_archetypes.resolve(value)[0]
    return resolve_npc_model(value)


# --------------------------------------------------------------------------- scene assembly

def camera_cfgs(project: FieldProject) -> list:
    """The field's camera config dict(s). ``[camera]`` (a table) -> one; ``[[camera]]`` (an array of
    tables, for a MULTI-camera field) -> N, in index order (camera 0 is the default at load)."""
    c = project.raw.get("camera")
    if isinstance(c, list):
        return c
    return [c] if c else []


def is_scrolling(project: FieldProject) -> bool:
    """True if the field is a larger-than-screen scrolling room ([camera.scroll] enabled)."""
    cfgs = camera_cfgs(project)
    return bool(cfgs and cfgs[0].get("scroll", {}).get("enabled"))


def _resolve_one_camera(project: FieldProject, c: dict, scrolling: bool) -> cam.Cam:
    if "borrow" in c:
        cams = cam.parse_bgx_cameras(str(project.path(c["borrow"])))
        if not cams:
            raise BuildError(f"no CAMERA in borrowed scene {c['borrow']}")
        return cams[0]
    range_wh = tuple(c.get("range", (384, 448)))
    # viewport: explicit wins; else auto scroll bounds (span the painting) for a scrolling field;
    # else the static single-screen default.
    if "viewport" in c:
        viewport = tuple(c["viewport"])
    elif scrolling:
        viewport = cam.scroll_bounds(range_wh)
    else:
        viewport = guide.DEFAULT_VIEWPORT
    common = dict(
        yaw_deg=float(c.get("yaw", 0)), range_wh=range_wh,
        depth_offset=int(c.get("depth_offset", guide.DEFAULT_DEPTH_OFFSET)),
        viewport=viewport, center_offset=tuple(c.get("center_offset", (0, 0))),
    )
    pitch, dist = float(c["pitch"]), float(c.get("distance", 4500))
    # focal length: an explicit `proj` wins; else FOV measured at `window_width` (the visible screen
    # width for a scrolling field — default = the painting width, so normal fields are unchanged).
    # This decouples the focal length from a wide Range (a 768-wide painting must not double the FOV).
    if "proj" in c:
        return guide.make_camera(pitch, dist, proj=int(c["proj"]), **common)
    fov = float(c.get("fov", 42.2))
    win_w = int(c.get("window_width", range_wh[0]))
    if win_w != range_wh[0]:
        return guide.make_camera(pitch, dist, proj=guide.proj_from_fov_x(fov, win_w), **common)
    return guide.make_camera(pitch, dist, fov_x_deg=fov, **common)


def resolve_cameras(project: FieldProject) -> list:
    """All of the field's cameras (one for a single ``[camera]``, N for ``[[camera]]``). Camera 0 is
    the active one at load; a multi-camera field switches between them via ``[[camera_zone]]``."""
    cfgs = camera_cfgs(project)
    scrolling = is_scrolling(project)
    return [_resolve_one_camera(project, c, scrolling) for c in cfgs]


def resolve_camera(project: FieldProject) -> cam.Cam:
    """The primary (index-0) camera -- drives the walkmesh frame, movement, content guidance."""
    cams = resolve_cameras(project)
    if not cams:
        raise BuildError("[camera] section is required")
    return cams[0]


def _read_links(links_path):
    """Parse a walkmesh.links.toml adjacency sidecar -> (seams, header). Seams in the shape
    `BgiWalkmesh.apply_seams` expects: (a_floor, a_edge, b_floor, b_edge), each edge a sorted pair of
    (x,y,z) tuples (matching the WORLD-position keys extract_seams emits)."""
    with open(links_path, "rb") as fh:
        d = tomllib.load(fh)
    seams = []
    for s in d.get("seam", []):
        a = tuple(sorted(tuple(int(c) for c in p) for p in s["a_edge"]))
        b = tuple(sorted(tuple(int(c) for c in p) for p in s["b_edge"])) if s.get("b_edge") else None
        seams.append((int(s["a_floor"]), a, int(s.get("b_floor", s["a_floor"])), b))
    return seams, d.get("header", {})


def _apply_links(mesh, links_path, warnings):
    """Reconcile cross-floor seams (+ restore header) onto a freshly (re)built multi-floor walkmesh."""
    seams, header = _read_links(links_path)
    linked, missing, misses = mesh.apply_seams(seams)
    if "active_floor" in header:
        mesh.activeFloor = int(header["active_floor"])
    if "active_tri" in header:
        mesh.activeTri = int(header["active_tri"])
    cp = header.get("char_pos")
    if cp and len(cp) == 3:
        mesh.charPos = bgi.Vec3(int(cp[0]), int(cp[1]), int(cp[2]))
    if missing and warnings is not None:
        fa, a_edge, fb, _ = misses[0]
        warnings.append(
            f"walkmesh: {missing} of {linked + missing} cross-floor seam(s) couldn't be matched "
            f"(a connecting edge was moved/deleted, e.g. floor {fa}<->{fb} near {a_edge[0]}). "
            f"Re-anchor it in the .obj or restore [walkmesh] bgi (docs/WALKMESH_EDITING.md).")


def _png_size(path):
    """(width, height) from a PNG's IHDR header, or None -- no PIL dependency (build stays stdlib)."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
    except OSError:
        return None
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def _validate_layer_art(project: FieldProject, range_wh, warnings: list) -> None:
    """Warn when a layer's PNG aspect doesn't match its `size` -- the engine maps the texture onto a
    `size`-logical quad (BGSCENE overlay mesh), so a repaint at the wrong aspect is STRETCHED /
    misaligned in-game. `size` defaults to the camera canvas (range); the convention is PNG = size x4."""
    rw, rh = int(range_wh[0]), int(range_wh[1])
    for layer in project.raw.get("layers", []):
        img = project.path(layer["image"])
        dims = _png_size(img)
        if dims is None:
            continue                                       # missing/non-PNG: validate() handles missing
        pw, ph = dims
        size = layer.get("size", [rw, rh])
        sw, sh = int(size[0]), int(size[1])
        if min(pw, ph, sw, sh) <= 0:
            continue
        if abs(pw / ph - sw / sh) > 0.01:                  # aspect mismatch => non-uniform stretch
            warnings.append(
                f"layer {Path(layer['image']).name!r} is {pw}x{ph}px (aspect {pw / ph:.2f}) but its "
                f"size {sw}x{sh} expects aspect {sw / sh:.2f} -- it'll be stretched / misaligned. "
                f"Repaint at {sw * 4}x{sh * 4} (size x4) or keep the aspect ratio.")


def _borrow_walkmesh(project: FieldProject):
    """The real walkmesh a BG-borrow fork runs on, for content validation ONLY (never shipped). Uses
    `[walkmesh] reference` if set, else the sibling `walkmesh.bgi` the importer wrote next to the
    field.toml. Returns a BgiWalkmesh, or None if neither is present (hand-written borrow toml)."""
    ref = project.raw.get("walkmesh", {}).get("reference")
    p = project.path(ref) if ref else (project.base_dir / "walkmesh.bgi")
    return bgi.BgiWalkmesh.from_bytes(p.read_bytes()) if p.is_file() else None


def _ladder_sequences(project: FieldProject, climb_ref, climb_bytes):
    """Load the STARTSEQ-referenced sequence sidecars for a FAITHFUL ladder climb (the concurrent
    helper entries the climb launches, e.g. the SetPitchAngle forward-lean). The climb references them
    by entry index via STARTSEQ (0x43); `ff9mapkit import` wrote each as '<climb-stem>.seq<index>.bin'
    next to the climb sidecar. Returns {index: bytes}, or None for a simple (no-STARTSEQ) climb."""
    idxs = sorted({i.args[0] for i in iter_code(climb_bytes, 0, len(climb_bytes))
                   if i.op == _ladder.STARTSEQ and i.args})
    if not idxs:
        return None
    if not climb_ref.endswith(".climb.bin"):
        raise ValueError(f"[[ladder]] climb {climb_ref!r} launches STARTSEQ sequences; name its sidecar "
                         f"'<name>.climb.bin' so the '.seq<N>.bin' helpers can be located")
    stem = climb_ref[:-len(".climb.bin")]
    seqs = {}
    for ei in idxs:
        p = project.path(f"{stem}.seq{ei}.bin")
        if not p.is_file():
            raise FileNotFoundError(
                f"[[ladder]] climb launches STARTSEQ entry {ei} but its sidecar {stem}.seq{ei}.bin is "
                f"missing -- regenerate the fork with `ff9mapkit import`")
        seqs[ei] = p.read_bytes()
    return seqs


def _point_on_rungs(rungs, frac):
    """The world point at ``frac`` of the total HEIGHT along a multi-rung (bent) vine -- for the re-entry
    spawn, which must sit ON the bent path, not the straight bottom->top chord."""
    pts = [[int(c) for c in p] for p in rungs]
    by, ty = pts[0][2], pts[-1][2]
    wy = by + frac * (ty - by)
    for (px, pz, py), (qx, qz, qy) in zip(pts, pts[1:]):
        lo, hi = (py, qy) if py <= qy else (qy, py)
        if qy != py and lo <= wy <= hi:
            t = (wy - py) / (qy - py)
            return round(px + t * (qx - px)), round(pz + t * (qz - pz)), round(wy)
    return pts[-1][0], pts[-1][1], round(wy)


def _validate_content_placement(project: FieldProject, wmesh, warnings: list) -> None:
    """Warn when authored content sits OFF the walkable area -- the recurring in-game mistake (an NPC
    floats / the player can't reach a trigger / spawns off the floor). Top-down XZ point-in-walkmesh
    test. Custom-scene only (where the kit has the walkmesh); a warning, never a hard error.

    Also an ADVISORY near-edge check for NPCs + the player spawn: content on the mesh but within the
    player COLLISION_RADIUS_W of a wall, which the point-in-walkmesh test passes but the player's
    centre can't actually reach (it stops ~that far from any wall). NOT applied to gateways -- an
    exit zone is edge-placed by design, so that would false-positive on every door."""
    R = cam.COLLISION_RADIUS_W
    def off(x, z):
        return wmesh.point_on_walkmesh(int(round(x)), int(round(z))) is None

    def near_edge(x, z):
        """Distance to the nearest wall if on-mesh AND within the collision radius, else None."""
        d = wmesh.distance_to_boundary(int(round(x)), int(round(z)))
        return d if (d is not None and d < R) else None

    # An off-mesh NPC is only a real problem if the player can't reach talking range. NPCs are placed by a
    # world transform and render regardless of the walkmesh -- a normal FF9 NPC stands against the BACK
    # WALL, just past the floor edge, and the player talks to it from the adjacent floor (proven by the
    # in-game-verified hut oracle: Vivi sits ~100u beyond the floor's back edge and works). So we only HARD
    # warn when an NPC is GROSSLY off -- farther than talk reach (~2x the object-collision radius) outside
    # the floor's bounding box, i.e. a clear misplacement -- and treat a near-footprint NPC as intentional.
    wv = wmesh.world_verts()
    if wv:
        _minx, _maxx = min(v[0] for v in wv), max(v[0] for v in wv)
        _minz, _maxz = min(v[2] for v in wv), max(v[2] for v in wv)
    else:
        _minx = _maxx = _minz = _maxz = 0.0
    NPC_REACH = 2.0 * cam.OBJECT_COLLISION_W          # an NPC this close to the floor footprint is reachable

    def gross_off(x, z):
        """Distance the point lies OUTSIDE the walkmesh bounding box (0 if within it), > talk reach."""
        dx, dz = max(_minx - x, x - _maxx, 0.0), max(_minz - z, z - _maxz, 0.0)
        return (dx * dx + dz * dz) ** 0.5 > NPC_REACH

    for i, n in enumerate(project.raw.get("npc", [])):
        p = n.get("pos")
        if not p:
            continue
        label = f"NPC {n.get('name', f'#{i}')!r} at ({int(p[0])}, {int(p[1])})"
        if off(p[0], p[1]):
            if gross_off(p[0], p[1]):                 # far outside the floor footprint -- a misplacement
                warnings.append(f"{label} is far off the walkmesh (well outside the floor footprint) -- "
                                f"it will render in empty space and the player can't reach it. Put it on, "
                                f"or just behind, the walkable floor.")
            # else: a back-wall NPC just past the floor edge -- normal placement, no warning.
        else:
            d = near_edge(p[0], p[1])
            if d is not None:
                warnings.append(f"{label} is only ~{d:.0f}u from a walkmesh edge (< the ~{R:.0f}u "
                                f"player collision radius) -- the player may not be able to walk up "
                                f"to it. Move it inward, or extend the walkmesh past it. (advisory)")
    sp = project.raw.get("player", {}).get("spawn")
    if sp:
        if off(sp[0], sp[1]):
            warnings.append(f"player spawn ({int(sp[0])}, {int(sp[1])}) is off the walkmesh -- "
                            f"you'll start off the floor.")
        else:
            d = near_edge(sp[0], sp[1])
            if d is not None:
                warnings.append(f"player spawn ({int(sp[0])}, {int(sp[1])}) is only ~{d:.0f}u from a "
                                f"walkmesh edge (< the ~{R:.0f}u collision radius) -- the engine will "
                                f"shove you inward on entry. Move it toward the floor centre. (advisory)")
    for gw in project.raw.get("gateway", []):
        zone = gw.get("zone", [])
        if zone:
            cx, cz = sum(p[0] for p in zone) / len(zone), sum(p[1] for p in zone) / len(zone)
            if off(cx, cz):
                warnings.append(
                    f"gateway -> field {gw.get('to')}: zone centre ({int(cx)}, {int(cz)}) is off the "
                    f"walkmesh -- the player may not be able to reach the trigger.")
    for k, ev in enumerate(project.raw.get("event", [])):
        zone = ev.get("zone", [])
        if zone:
            cx, cz = sum(p[0] for p in zone) / len(zone), sum(p[1] for p in zone) / len(zone)
            if off(cx, cz):
                warnings.append(
                    f"event #{k}: zone centre ({int(cx)}, {int(cz)}) is off the walkmesh -- "
                    f"the player may not be able to walk into it.")
    for j, lad in enumerate(project.raw.get("ladder", [])):
        if not lad.get("navigable"):
            continue                                         # the 2-tag bidirectional path lands on its own zones
        bottom = lad.get("bottom") or []
        top = lad.get("top") or []
        fl = lad.get("floor_landing") or (bottom[:2] if len(bottom) >= 2 else None)
        if fl and off(fl[0], fl[1]):                         # the bottom always dismounts onto a floor
            warnings.append(
                f"ladder #{j}: floor_landing ({int(fl[0])}, {int(fl[1])}) is off the walkmesh -- "
                f"you'll dismount off the floor at the bottom.")
        if lad.get("top_action", "floor") == "floor":        # a gateway/worldmap top has no floor to land on
            tl = lad.get("top_landing") or (top[:2] if len(top) >= 2 else None)
            if tl and off(tl[0], tl[1]):
                warnings.append(
                    f"ladder #{j}: top_landing ({int(tl[0])}, {int(tl[1])}) is off the walkmesh -- "
                    f"you'll dismount into a non-navigable area at the top. Put it on the walkable "
                    f"floor, or use a gateway/worldmap top_action if there's no floor up there.")
    _validate_cutscene_movement(project, wmesh, warnings)    # an actor cutscene's walks must not stall


def _validate_walkmesh_geometry(project: FieldProject, wmesh, warnings: list) -> None:
    """Reachability + degenerate-tri warnings for a (re)BUILT walkmesh (obj/quad/auto). A verbatim
    [walkmesh] bgi is the authoritative original and is SKIPPED -- some real fields legitimately reach
    floors by script, not on foot (e.g. UDFT: 9 of 23 walk-reachable), so checking it cries wolf."""
    if project.raw.get("walkmesh", {}).get("bgi"):
        return
    stranded = wmesh.all_floors() - wmesh.reachable_floors()
    if stranded:
        warnings.append(
            f"walkmesh: floor(s) {sorted(stranded)} not walk-reachable from the start "
            f"({len(stranded)} of {len(wmesh.all_floors())} floors stranded). A multi-floor "
            f"[walkmesh] obj loses cross-floor links (rebuild_neighbors only links within a "
            f"floor) -- ship the original with [walkmesh] bgi, or declare seams "
            f"(docs/WALKMESH_EDITING.md).")
    degen = wmesh.degenerate_tris()
    if degen:
        warnings.append(
            f"walkmesh: {len(degen)} zero-area triangle(s) {degen[:5]}"
            f"{'...' if len(degen) > 5 else ''} -- collinear verts make a dead zone in the "
            f"engine's IsInQuad test (the player can't stand there); fix them in the .obj.")


def _walkmesh_stats(wmesh) -> dict:
    """Geometry summary of a BgiWalkmesh for the `walkmesh verify` report."""
    floors = sorted(wmesh.all_floors())
    reach = sorted(wmesh.reachable_floors())
    wv = wmesh.world_verts()
    xs, zs = [v[0] for v in wv], [v[2] for v in wv]
    return {"floors": floors, "reachable": reach, "stranded": sorted(set(floors) - set(reach)),
            "degenerate": wmesh.degenerate_tris(), "seams": len(wmesh.extract_seams()),
            "tris": len(wmesh.tris), "verts": len(wmesh.verts),
            "bounds": {"x": [min(xs), max(xs)], "z": [min(zs), max(zs)]} if wv else None}


def verify_walkmesh(project: FieldProject) -> dict:
    """Run the walkmesh + content-placement checks for a project WITHOUT building the mod (the
    `walkmesh verify` CLI). Resolves the walkmesh exactly as build does -- a custom scene's
    obj/quad/bgi, or a BG-borrow fork's reference/sibling walkmesh -- then returns
    {**stats, source, warnings}. Same checks build_field runs, so a clean verify == a clean build."""
    warnings: list = []
    if project.field.get("borrow_bg"):
        wmesh = _borrow_walkmesh(project)
        source = f"BG-borrow ({project.field['borrow_bg']})"
        if wmesh is None:
            return {"source": source, "warnings": [
                "no walkmesh to verify -- a BG-borrow fork without a [walkmesh] reference or a sibling "
                "walkmesh.bgi (hand-written borrow toml). The engine uses the real field's walkmesh."]}
        _validate_content_placement(project, wmesh, warnings)     # content only (borrowed mesh is authoritative)
    else:
        camera = resolve_camera(project)
        wmesh = bgi.BgiWalkmesh.from_bytes(resolve_walkmesh(project, camera, warnings))
        source = "custom scene"
        _validate_content_placement(project, wmesh, warnings)
        _validate_layer_art(project, camera.range, warnings)
        _validate_walkmesh_geometry(project, wmesh, warnings)
    return {"source": source, **_walkmesh_stats(wmesh), "warnings": warnings}


def resolve_walkmesh(project: FieldProject, camera: cam.Cam, warnings=None) -> bytes:
    wm = project.raw.get("walkmesh", {})
    if wm.get("bgi"):
        # ship a pre-built .bgi verbatim (e.g. an imported real field's walkmesh). This PRESERVES its
        # exact floors + neighbor/edge connectivity -- a multi-floor obj->build would rebuild links by
        # shared vertex index and disconnect floors that use disjoint vertex sets (stairs/tunnels).
        return project.path(wm["bgi"]).read_bytes()
    # All authored walkmeshes are in TRUE WORLD coords (org=0): the player renders at its world
    # position (= to_canvas), so the walkmesh IS the painted floor -- no character offset (MEASURED
    # in-game Session 18; the old org=(0,0,300) + character_offset=298 double-count is gone). The
    # `frame` and `character_offset` keys are accepted-but-ignored for back-compat.
    if wm.get("obj"):
        verts, faces, floor_ids = bgi.load_obj_floors(str(project.path(wm["obj"])))
        mesh = bgi.build(verts, faces, floor_ids=floor_ids)
        if wm.get("links"):
            # reconcile the imported field's cross-floor connectivity onto the edited geometry
            # (rebuild_neighbors only links within a floor). v2 -- see docs/WALKMESH_EDITING.md.
            _apply_links(mesh, project.path(wm["links"]), warnings)
        return mesh.to_bytes()
    if wm.get("quad"):
        corners = [(c[0], 0, c[1]) if len(c) == 2 else tuple(c) for c in wm["quad"]]
        return bgi.build(corners, [(0, 1, 2), (0, 2, 3)]).to_bytes()
    # auto: frame the floor from the camera; the frame corners ARE world coords (via to_canvas).
    _cfgs = camera_cfgs(project)
    fr = (_cfgs[0].get("frame", {}) if _cfgs else {})
    try:
        frame = guide.frame_floor(camera, back_canvas_y=float(fr.get("back", 205)),
                                  front_canvas_y=float(fr.get("front", 432)))
    except ValueError as e:
        raise BuildError(f"[camera.frame] {e}") from e
    corners = [(x, 0, z) for (x, z) in guide.walkmesh_corners(frame)]
    return bgi.build(corners, [(0, 1, 2), (0, 2, 3)]).to_bytes()


def build_overlays(project: FieldProject, range_wh=(384, 448)) -> list:
    overlays = []
    for layer in project.raw.get("layers", []):
        pos = layer.get("position", [0, 0])
        overlays.append(bgx.Overlay(
            image=Path(layer["image"]).name,
            position=(int(pos[0]), int(pos[1]), int(layer["z"])),
            # a full-cover layer defaults to the painted canvas size (the camera Range), so a
            # larger-than-screen scrolling painting isn't clipped to a single 384x448 screen.
            size=tuple(layer.get("size", (int(range_wh[0]), int(range_wh[1])))),
            shader=layer.get("shader", bgx.DEFAULT_SHADER),
            # which camera shows this layer (multi-camera fields paint a backdrop per camera).
            camera_id=int(layer.get("camera", 0)),
        ))
    return overlays


# --------------------------------------------------------------------------- script assembly

def resolve_control_value(project: FieldProject, camera: cam.Cam) -> int:
    """The SetControlDirection (TWIST) value that makes WASD match the camera.

    Explicit ``[camera] control_direction`` wins; otherwise it is derived from the camera's yaw so a
    yawed/orbited camera still moves "up = up the screen". A front-facing camera yields -1 (the kit
    default = 0 deg), so front-facing fields are byte-identical to before."""
    cfgs = camera_cfgs(project)
    c = cfgs[0] if cfgs else {}
    if "control_direction" in c:
        return int(c["control_direction"])
    return _movement.control_value_for_angle(cam.yaw_deg(camera))


def _gate_of(d: dict):
    """(flag_index, require_set) from a content item's flag condition, or (None, True). ``requires_flag``
    = active when that GlobBool is SET; ``requires_flag_clear`` = active when it is CLEAR."""
    if "requires_flag" in d:
        return int(d["requires_flag"]), True
    if "requires_flag_clear" in d:
        return int(d["requires_flag_clear"]), False
    return None, True


def _gateway_on_exit_body(gw: dict, names: dict) -> bytes:
    """The story-state advance a ``[[gateway]]`` applies when the player TAKES this exit: the raw
    ``set_var`` bytes from ``set_scenario`` (ScenarioCounter) + ``set_flags`` (gEventGlobal bits), built
    with the shared :func:`ff9mapkit.content.startup.startup_body`. ``b""`` when the gateway has neither
    (so the build is byte-identical to a gateway without on-exit writes)."""
    sc = gw.get("set_scenario")
    if isinstance(sc, str):
        sc = _flags.resolve_scenario(sc)
    presets = [(_flags.resolve(p["flag"], names), int(p.get("value", 1))) for p in gw.get("set_flags", [])]
    if sc is None and not presets:
        return b""
    return _startup.startup_body(presets, sc)


# Per-member event-flag reserve inside a campaign member's K-wide block (see _FlagAlloc). With the
# default flags_per_field=64: cutscene at base+0, events base+1..+31, choices base+32..+63.
EVENTS_PER_FIELD = 31


class _FlagAlloc:
    """Auto once-flag allocator. ``base is None`` (single-field build) reproduces the historical
    per-category bands EXACTLY (event 8000+, cutscene 8100, choice 8200+) -> byte-identical output.
    When a campaign assigns a per-member ``flag_base``, the field's auto once-flags pack into that
    member's own block via a FIXED sub-partition (order-independent, so :func:`lint_logic` mirrors
    :func:`build_script` regardless of which it allocates first), keeping every member's once-flags
    disjoint from its siblings' -- the fix for the per-field-counter-resets-per-build aliasing bug."""

    def __init__(self, base: int | None):
        self.base = base

    def event(self, i: int) -> int:
        return (_event.EVENT_FLAG_BASE + i) if self.base is None else (self.base + 1 + i)

    def cutscene(self) -> int:
        return _cutscene.DEFAULT_CUTSCENE_FLAG if self.base is None else self.base

    def choice(self, i: int) -> int:
        return (_choice.CHOICE_FLAG_BASE + i) if self.base is None else (self.base + 1 + EVENTS_PER_FIELD + i)

    def on_entry(self, i: int) -> int:
        """Auto once-flag for an ``[[on_entry]]`` hook. Single-field only -- a campaign member's
        K-wide block is already fully partitioned (cutscene/events/choices), so an on_entry hook there
        needs an explicit ``flag = N`` (build_script raises a clear error rather than alias a sibling)."""
        if self.base is None:
            return _onentry.ONENTRY_FLAG_BASE + i
        raise BuildError(
            "an [[on_entry]] hook in a campaign member needs an explicit `flag = N` -- the per-member "
            "flag block is fully reserved for cutscene/events/choices, so an auto once-flag would alias "
            "a sibling member. Pick an index in this member's free band or use a shared [[flag]].")


def _apply_startup(project: FieldProject, eb: bytes) -> bytes:
    """Prepend the ``[startup]`` presets (ScenarioCounter + gEventGlobal story bits) to Main_Init so every
    gate evaluated afterwards sees the asserted beat. Shared by :func:`build_script` (synthesize path) AND
    the verbatim-`.eb` path in :func:`build_field` (which bypasses build_script, so it would otherwise drop
    ``[startup]`` entirely -- the pairing the docs promise). No ``[startup]`` -> unchanged (byte-identical)."""
    su = project.raw.get("startup")
    if not su:
        return eb
    names = _flags.collect_flag_defs(project.raw)
    sc = su.get("scenario")
    if isinstance(sc, str):
        sc = _flags.resolve_scenario(sc)
    presets = [(_flags.resolve(p["flag"], names), int(p.get("value", 1))) for p in su.get("flags", [])]
    return _startup.inject_startup(eb, presets, sc)


def _apply_party(project: FieldProject, eb: bytes, warnings: list | None = None) -> bytes:
    """Prepend the ``[party]`` add/remove sequence to Main_Init (party MEMBERSHIP -- who's in the menu/battle;
    decoupled from who you control). Shared by :func:`build_script` (synthesize) AND the verbatim-`.eb` path in
    :func:`build_field` (which bypasses build_script). No ``[party]`` -> unchanged (byte-identical). On a
    verbatim fork whose Main_Init rebuilds the roster (``SetPartyReserve`` 0xB4, which runs AFTER our prepend
    and can wipe the add), warn (``warnings`` is in scope only on the verbatim path)."""
    pty = project.raw.get("party")
    if not pty:
        return eb
    adds = [_party.resolve_member(m) for m in pty.get("add", [])]
    removes = [_party.resolve_member(m) for m in pty.get("remove", [])]
    if not adds and not removes:
        return eb
    if warnings is not None and (adds or removes) and _party.field_resets_party(eb):
        warnings.append("[party]: this field rebuilds the party roster (SetPartyReserve, 0xB4) at load, which "
                        "runs AFTER the [party] op(s) and can override them -- the add(s)/remove(s) may not "
                        "stick. The reset can be partial or scenario-gated, so verify in-game; or use a field "
                        "that doesn't reset the party.")
    return _party.inject_party(eb, adds, removes)


def _field_load_inject(label: str, field_name: str, fn):
    """Run a field-load injection (``_apply_startup`` / ``_apply_party`` / ``_apply_on_entry``), converting the
    byte inserter's opaque "0x06 jump table -- insert unsupported" ``ValueError`` into a clear, actionable
    :class:`BuildError`. ~11% of real fields (e.g. field 100) have a jump table at the top of Main_Init that
    :func:`edit.insert_in_function` can't yet shift past; on a verbatim fork of one of those, prepending a
    field-load block fails closed with a useful message instead of an opaque mid-build traceback. (Harmless on
    the synthesize path -- the kit-built Main_Init never has a jump table -- but the same guard is cheap there.)"""
    try:
        return fn()
    except ValueError as e:
        if "jump table" in str(e):
            raise BuildError(
                f"field {field_name}: cannot prepend {label} to Main_Init -- this donor's Main_Init has a 0x06 "
                f"jump table, which the byte inserter can't yet shift past (affects ~11% of real fields, e.g. "
                f"field 100). Fork this field WITHOUT {label} (a verbatim fork already carries its real logic + "
                f"cast), or choose a different donor.") from e
        raise


def _apply_on_entry(project: FieldProject, eb: bytes, on_entry_txids: dict, auto,
                    *, drop_messages: bool = False, warnings: list | None = None) -> bytes:
    """Arm the ``[[on_entry]]`` hooks (gated, once field-LOAD beats) into ``eb`` -- each a code entry run by
    an ``InitCode`` in Main_Init (the declarative entry-beat hook, FORK_FIDELITY.md #10). Shared by
    :func:`build_script` (synthesize path) AND the verbatim-`.eb` path in :func:`build_field` (which bypasses
    build_script, so it would otherwise drop ``[[on_entry]]`` -- the same gap ``[startup]`` had). ``auto`` is
    the field's :class:`_FlagAlloc` (for an unflagged hook's auto once-flag). ``drop_messages`` (verbatim): a
    verbatim fork ships the DONOR's `.mes` (index-implicit txids), with no channel for an authored narration
    line, so a ``message`` beat is dropped (and warned) while its gated state-advance still fires. No
    ``[[on_entry]]`` -> unchanged (byte-identical)."""
    on_entry = project.raw.get("on_entry") or []
    if not on_entry:
        return eb
    oe_names = _flags.collect_flag_defs(project.raw)
    hooks = []
    for k, h in enumerate(on_entry):
        sc = h.get("set_scenario")
        if isinstance(sc, str):
            sc = _flags.resolve_scenario(sc)
        rsc = h.get("requires_scenario")
        if isinstance(rsc, str):
            rsc = _flags.resolve_scenario(rsc)
        pairs = [(_flags.resolve(p["flag"], oe_names), int(p.get("value", 1)))
                 for p in h.get("set_flags", [])]
        rf = h.get("requires_flag")
        rf = _flags.resolve(rf, oe_names) if rf is not None else None
        once_flag = None
        if h.get("once", True):
            if "flag" in h:
                once_flag = int(h["flag"])
            else:
                once_flag = auto.on_entry(k)            # single-field 8300+k (campaign: raises -> explicit flag)
                if once_flag >= _flags.CHEST_FLAG_LO:   # would write into FF9's reserved chest bitfield
                    raise BuildError(
                        f"field {project.name}: too many auto-flagged [[on_entry]] hooks -- hook #{k}'s auto "
                        f"once-flag {once_flag} reaches FF9's reserved chest bitfield "
                        f"({_flags.CHEST_FLAG_LO}-{_flags.CHEST_FLAG_HI}) -> save corruption. Give the later "
                        f"hooks an explicit flag = N (>= {_flags.FIRST_SAFE_FLAG}).")
        txid = on_entry_txids.get(k)
        if drop_messages and txid is not None:
            txid = None                                 # no authored-text channel in a verbatim fork
            if warnings is not None:
                warnings.append(f"[[on_entry]] #{k}: narration message dropped in a verbatim fork (the donor "
                                f".mes ships verbatim, with no slot for authored text); the gated state-advance "
                                f"still fires.")
        hooks.append({"message_txid": txid, "set_flag_pairs": pairs,
                      "scenario": sc, "once_flag": once_flag, "requires_flag": rf,
                      "requires_set": bool(h.get("requires_set", True)), "requires_scenario": rsc})
    return _onentry.inject_on_entries(eb, hooks)


def _verbatim_on_entry_messages(project: FieldProject, langs) -> tuple[dict, dict]:
    """For a verbatim fork's ``[[on_entry]]`` narration MESSAGE hooks: give each message a txid ABOVE the
    donor `.mes`'s max (so it can't collide with the donor's index-txids) and the `.mes` lines to APPEND to
    each language's donor body. The verbatim `.eb`'s ``WindowSync`` then resolves into the appended entry, so
    the message SHOWS instead of being dropped. Returns ``(txid_by_hook, suffix_by_lang)`` -- ``({}, {})`` when
    the fork has no message hook (a state-only verbatim fork is then unchanged). The authored message is
    single-block: the SAME text for every language (like the synthesize path), appended at the same txid in
    each language's body -- so the `.eb` (injected once, language-identical) stays valid.

    The band floor is :data:`content.textcarry.CARRY_BASE_TXID` (1000, the unconditionally-safe id above
    real-field text); a donor whose text reaches it pushes the base to ``max donor txid + 1``. This is the
    same append-and-resolve trick ``--carry-text`` uses, so the donor's verbatim text stays untouched."""
    from .content import verbatim as _verbatim, textcarry as _textcarry
    from . import dialogue as _dialogue
    msg_hooks = [(k, h) for k, h in enumerate(project.raw.get("on_entry") or []) if h.get("message")]
    if not msg_hooks:
        return {}, {}
    bodies = {lang: (_verbatim.verbatim_mes(project, lang) or "") for lang in langs}
    max_txid = 0
    for body in bodies.values():
        ids = _dialogue.parse_mes(body) if body else {}
        if ids:
            max_txid = max(max_txid, max(ids))
    base = max(max_txid + 1, _textcarry.CARRY_BASE_TXID)
    wrap = _wrap_width(project)
    lines, tails, txid_by_hook = [], [], {}
    for i, (k, h) in enumerate(msg_hooks):
        line = _text.with_speaker(h.get("speaker"), h["message"])
        if wrap is not None:
            line = _text.wrap_text(line, wrap)[0]
        lines.append(line)
        tails.append(h.get("tail"))
        txid_by_hook[k] = base + i
    suffix, _ = _text.build_mes(lines, start_txid=base, tails=tails)
    return txid_by_hook, {lang: suffix for lang in langs}


def build_script(project: FieldProject, lang: str, dialogue_txids: dict,
                 control_value: int = -1, event_txids: dict | None = None,
                 cutscene_txids: list | None = None, walkmesh=None,
                 choice_txids: dict | None = None, on_entry_txids: dict | None = None) -> bytes:
    """Build one language's .eb by applying the project's content to the blank field."""
    _auto = _FlagAlloc(getattr(project, "flag_base", None))
    event_txids = event_txids or {}
    cutscene_txids = cutscene_txids or []
    choice_txids = choice_txids or {}
    on_entry_txids = on_entry_txids or {}
    # a choice attached to an NPC (choice.npc == npc.name) replaces that NPC's talk with a branch.
    choice_by_npc = {ch["npc"]: (c, ch) for c, ch in enumerate(project.raw.get("choice", []))
                     if "npc" in ch}
    eb = _data.blank_field_bytes(lang)
    # movement control-direction first (shift-free, before any appends that move bytecode)
    if control_value != -1:
        eb = _movement.set_control_direction(eb, control_value)
    # story-state presets ([startup]): assert the beat the forked field represents (ScenarioCounter +
    # gEventGlobal story bits), prepended to Main_Init so every gate evaluated afterwards sees the
    # asserted state. Absent -> no injection, so the build is byte-identical to before.
    eb = _apply_startup(project, eb)
    # party membership ([party]): add/remove existing playable characters at field load (B_PARTYADD /
    # RemoveParty), prepended to Main_Init. Decoupled from [startup] (party state, not story flags). A
    # synthesized field's Main_Init never rebuilds the roster, so no wipe warning is needed here.
    eb = _apply_party(project, eb)
    has_encounter = "encounter" in project.raw

    # larger-than-screen scrolling: enable the field's camera services (Active flag) so the engine's
    # 3D scroll follows the player. The wide Range + scroll Viewport come from the camera/scene.
    _cfgs = camera_cfgs(project)
    sc = _cfgs[0].get("scroll", {}) if _cfgs else {}
    if sc.get("enabled"):
        eb = _camera.enable_camera_services(eb, frame_count=int(sc.get("frame_count", 0)),
                                            scroll_type=int(sc.get("scroll_type", 0)))

    # cutscene plumbing computed up-front: an ACTOR cutscene's gated choreography is spliced into the
    # named NPC's Init (so it runs in that NPC's own context -- gExec == the NPC -- letting walk/
    # animation/turn act on it with base opcodes). A narration cutscene (no actor) is a standalone
    # director code entry, injected after the content blocks below.
    cs = project.raw.get("cutscene")
    cs_actor = cs.get("actor") if cs else None
    cs_once_flag = None
    if cs and cs.get("once", True):
        cs_once_flag = int(cs["flag"]) if "flag" in cs else _auto.cutscene()
    actor_choreo = None
    if cs_actor:
        actor_npc = next((n for n in project.raw.get("npc", []) if n.get("name") == cs_actor), None)
        steps = _resolve_anim_steps(cs["steps"], actor_npc)   # animation = "glad" -> the numeric id
        steps = _resolve_move_steps(steps, project, actor_npc)  # names -> [x,z]; @object walks stop short
        steps = _autoroute_steps(steps, project, walkmesh, actor_npc)  # route blocked walks around obstacles
        cs_fclass, cs_fidx = _cutscene.once_flag_for(cs)   # GLOB (once ever) or MAP (replay per visit)
        if _auto.base is not None and "flag" not in cs and cs.get("once", True):
            cs_fidx = _auto.cutscene()                     # campaign: pack into this member's block
        actor_choreo = _cutscene.build_choreography(
            steps, cutscene_txids, cs_fidx, flag_class=cs_fclass,
            warmup=int(cs.get("warmup", _cutscene.DEFAULT_WARMUP)))

    # NPCs (cloned from the player object) first, so their cloned positions are independent.
    gated_npc_slots = {}     # flag index -> [npc entry slots] (for live reveal when an event flips it)
    npc_slots = {}           # npc name -> entry slot (so a [[prop]] can attach_to it)
    for i, n in enumerate(project.raw.get("npc", [])):
        pos = n["pos"]
        txid = dialogue_txids.get(i, int(n.get("text_id", _text.DEFAULT_BASE_TXID)))
        kwargs = {}
        arch = n.get("archetype") or n.get("preset")      # a named archetype (playable cast or NPC type)
        if arch is not None:
            model, animset, anims, _dlg = _archetypes.resolve(arch)
            kwargs.update(model=model, animset=animset, anims=anims)
        else:
            mid = resolve_npc_model(n.get("model"))
            anims = n.get("anims")
            if mid is not None and not anims:
                anims = _catalog.npc_anims(mid) or None    # any model by name -> its own gestures (Info Hub)
            kwargs.update(model=mid, animset=n.get("animset"), anims=anims)
        # held items resolved EARLY (before injecting the NPC): each held prop's (model, bone, held pose)
        # AND the HOLDER's own holding pose, from HELD_POSES per (this holder's model, prop). We re-pose
        # the holder to hold -- else it idles and the prop looks wrong (a sword held backwards). A pairing
        # not in the catalog falls back to bone 11 + the prop's resting pose with no holder re-pose.
        carrier_model = kwargs.get("model")
        _holds = n.get("holds")
        _holds = _holds if isinstance(_holds, list) else ([_holds] if _holds is not None else [])
        holds_specs, holder_pose = [], None
        for hv in _holds:
            pmid = _resolve_held_model(hv)
            bp = HELD_POSES.get((carrier_model, pmid))
            hbone, hpose, hcpose = bp if bp else (11, _resolve_prop_pose(pmid, None), None)
            holds_specs.append((pmid, hbone, hpose))
            if holder_pose is None and hcpose:
                holder_pose = hcpose
        if holder_pose and not n.get("anims") and isinstance(kwargs.get("anims"), dict):
            kwargs["anims"] = {**kwargs["anims"], "stand": holder_pose}   # pose the holder to hold
        gf, gs = _gate_of(n)
        slot = EbScript.from_bytes(eb).first_free_slot()
        intro = actor_choreo if (cs_actor and n.get("name") == cs_actor) else None
        # a dialogue choice on this NPC: talk -> menu -> branch (replaces the plain WindowSync)
        sb = None
        if n.get("name") in choice_by_npc:
            c, ch = choice_by_npc[n["name"]]
            ct = choice_txids.get(c, {})
            replies = ct.get("replies", {})
            opt_bodies = [_choice.option_body(o, replies.get(oi))
                          for oi, o in enumerate(ch.get("options", []))]
            setup, _ = _choice.pre_choose(ch)
            sb = _choice.speak_body(ct["prompt"], opt_bodies, setup=setup)
        elif n.get("opens_shop") is not None:
            # a shopkeeper: talk -> (optional greeting window ->) open the shop (Menu(2, id)). The greeting
            # is this NPC's own `dialogue` line (txid assigned above); no dialogue -> straight to the shop.
            sb = _shop.shop_speak_body(int(n["opens_shop"]),
                                       greeting_txid=txid if n.get("dialogue") else None)
        eb = _npc.inject_npc(eb, int(pos[0]), int(pos[1]), talk_text_id=txid, slot=slot,
                             gate_flag=gf, gate_require_set=gs, intro=intro, speak_body=sb, **kwargs)
        if gf is not None:
            gated_npc_slots.setdefault(gf, []).append(slot)
        if n.get("name") is not None:
            npc_slots[n["name"]] = slot
        # attach the held prop(s) to this NPC's bone (resolved above, before the holder was injected)
        for pmid, hbone, hpose in holds_specs:
            hslot = EbScript.from_bytes(eb).first_free_slot()
            eb = _prop.inject_prop(eb, int(pos[0]), int(pos[1]), model=pmid, pose=hpose,
                                   slot=hslot, attach_to=slot, bone=hbone)

    # props (static set-dressing: SetModel + a fixed pose + EnableHeadFocus(0) -- a non-character object
    # that does NOT turn to face the player, the real FF9 prop recipe). Same gating as an NPC.
    for p in project.raw.get("prop", []):
        pos = p["pos"]
        x, z, face = int(pos[0]), int(pos[1]), p.get("face")
        gf, gs = _gate_of(p)
        name = p.get("prop")
        # resolve to a list of (model, pose) PARTS -- a composite is several parts at the same (x, z)
        # (the way shipping fields build e.g. a save point: moogle + book + feather + letter co-located).
        if name is not None and _prop_archetypes.is_composite(name):
            parts = _prop_archetypes.resolve_composite(name)
        elif name is not None:                              # a single named prop archetype (model + pose)
            mid, pose = _prop_archetypes.resolve(name)
            if p.get("pose") is not None:                   # explicit pose still overrides the baked one
                pose = _resolve_prop_pose(mid, p["pose"])
            parts = [(mid, pose, 0, 0)]
        else:                                               # a raw model + optional pose
            mid = resolve_npc_model(p.get("model"))
            parts = [(mid, _resolve_prop_pose(mid, p.get("pose")), 0, 0)]
        at = p.get("attach_to")                             # bind the prop to a named NPC's bone (held item)
        attach_slot = npc_slots.get(at) if at is not None else None
        if at is not None and attach_slot is None:
            raise ValueError(f"[[prop]] attach_to {at!r} is not a defined [[npc]] name")
        bone = int(p.get("bone", 11))
        for mid, pose, dx, dz in parts:                     # a composite may offset a part from the anchor
            slot = EbScript.from_bytes(eb).first_free_slot()
            eb = _prop.inject_prop(eb, x + dx, z + dz, model=mid, pose=pose, face=face, slot=slot,
                                   attach_to=attach_slot, bone=bone, gate_flag=gf, gate_require_set=gs)

    # gateways
    gw_names = _story_names(project)                    # [[flag]] name -> index, for set_flags resolution
    for gw in project.raw.get("gateway", []):
        zone = gw["zone"]
        if len(zone) == 4:
            zone = _gw.quad_zone(zone)
        gf, gs = _gate_of(gw)
        eb = _gw.inject_gateway(eb, int(gw["to"]), entrance=int(gw.get("entrance", 0)),
                                zone=[tuple(p) for p in zone], gate_flag=gf, gate_require_set=gs,
                                on_exit_body=_gateway_on_exit_body(gw, gw_names))

    # multi-camera switch zones (area model): each zone owns the floor area where its camera is
    # active; crossing into it cuts the active background camera + re-tunes movement for that camera's
    # yaw. Scales to N cameras (flag = current camera index prevents re-fire; non-overlapping zones
    # can't flap). cam_restore is stashed for the after-battle restore added after the reinit below.
    cam_restore = None
    zones = project.raw.get("camera_zone", [])
    if zones:
        cams = resolve_cameras(project)
        cvs = [_movement.control_value_for_angle(cam.yaw_deg(c)) for c in cams]
        zspecs = [(int(z["to_camera"]), [tuple(p) for p in z["zone"][:4]]) for z in zones]
        eb = _camera.inject_camera_zones(eb, zspecs, cvs)
        cam_restore = ({tc for tc, _ in zspecs}, cvs)

    # events: walk-in triggers (message / give item / gil / set flag), optionally once. All N events
    # are armed by ONE shared init entry (so they don't each eat a Main_Init Wait filler).
    events = project.raw.get("event", [])
    if events:
        specs, flag_counter = [], 0
        for j, ev in enumerate(events):
            parts = []
            item_id = _items.resolve(ev["give_item"][0]) if "give_item" in ev else None
            if "give_item" in ev:
                gi = ev["give_item"]
                parts.append(_event.give_item(item_id, int(gi[1]) if len(gi) > 1 else 1))
            if "remove_item" in ev:                       # the symmetric take-item lever (a trade / consume)
                ri = ev["remove_item"]
                parts.append(_event.take_item(ri[0], int(ri[1]) if len(ri) > 1 else 1))
            if "gil" in ev:
                parts.append(_event.give_gil(int(ev["gil"])))
            # Apply the EFFECTS (item/gil already above, now the flag) BEFORE the acknowledgement
            # message. An event does NOT lock movement, so the effect must land the instant you trigger
            # it -- not only when you close the window (you could walk off first). "You found X" then
            # reads as an acknowledgement of what already happened (the chest/found-item convention).
            if "set_flag" in ev:
                sf = ev["set_flag"]
                fidx = int(sf[0])
                parts.append(_event.set_flag(fidx, int(sf[1]) if len(sf) > 1 else 1))
                # live reveal: re-init any NPC gated on this flag so it appears/vanishes immediately
                # (its Init re-checks the gate with the flag's new value), not just on field re-entry.
                for npc_slot in gated_npc_slots.get(fidx, []):
                    parts.append(_event.reveal_object(npc_slot))
            if j in event_txids:
                if ev.get("received") and item_id is not None:
                    # the canonical FF9 item-get window (type 7) showing "Received <item>!": set text
                    # slot 0 to the item so the [ITEM=0] tag renders its name, then the window-7 message.
                    parts.append(opcodes.set_text_variable(0, item_id))
                    parts.append(_event.message(event_txids[j], window=7, flags=0))
                else:
                    parts.append(_event.message(event_txids[j]))
            once_flag = None
            if ev.get("once", True):
                if _auto.base is not None and "flag" not in ev and flag_counter >= EVENTS_PER_FIELD:
                    raise BuildError(
                        f"field {project.name}: more than {EVENTS_PER_FIELD} auto-flagged 'once' events "
                        f"overflow this campaign member's flag block -- raise [campaign] flags_per_field, set "
                        f"an explicit flag = N on some events, or split the field. (Auto event flags would "
                        f"alias the choice sub-band -> save corruption.)")
                once_flag = int(ev["flag"]) if "flag" in ev else _auto.event(flag_counter)
                flag_counter += 1
            gf, gs = _gate_of(ev)
            # chest space-check: skip the reward (and don't set the once-flag) if the bag is full
            space_item = item_id if ev.get("require_space") and item_id is not None else None
            specs.append({"zone": [tuple(p) for p in ev["zone"][:4]],
                          "body": b"".join(parts), "once_flag": once_flag,
                          "requires_flag": gf, "requires_set": gs, "space_item": space_item})
        eb = _event.inject_events(eb, specs)

    # zone-triggered choices: a region the player triggers for a choice menu (a lever / sign).
    #   trigger="action" (default): press-action-in-quad (tag 3). Edge-triggered by the button, so it
    #     NEVER loops, needs no gate flag, and is re-usable -- "decline" is non-destructive. The body
    #     is the full choice func (speak_body). Optional requires_flag gates it (e.g. a one-shot lever
    #     whose "pull" option sets a flag the choice is gated CLEAR on).
    #   trigger="walk": auto-pops on tread (tag 2) -- LEVEL-triggered, so it needs the event-style flag
    #     gate to be loop-safe (a synchronous menu would re-pop every frame). once=true persists (once
    #     ever); once=false resets in Init (once per visit). GLOB flag only (the 80-byte MAP array
    #     can't hold a high index -> crash). NOTE: a "walk" decline still consumes it for that arming.
    choice_flag_counter = 0
    for c, ch in enumerate(project.raw.get("choice", [])):
        if "zone" not in ch:
            continue
        ct = choice_txids.get(c, {})
        replies = ct.get("replies", {})
        opt_bodies = [_choice.option_body(o, replies.get(oi))
                      for oi, o in enumerate(ch.get("options", []))]
        setup, _ = _choice.pre_choose(ch)
        zone = [tuple(p) for p in ch["zone"][:4]]
        gf, gs = _gate_of(ch)
        if (ch.get("trigger") or "action") == "action":
            # one-shot lever = requires_flag_clear + a "consume" option that sets that flag. When the
            # flag ends up set (consume picked), TerminateEntry the region so its interaction prompt
            # vanishes -- but AFTER EnableMove (region_body's last op), so the player keeps control;
            # a terminate inside the option body (before EnableMove) would kill the entry early and
            # leave the player frozen. The Init only sets the quad while the flag is clear, so a spent
            # lever shows no prompt on later visits either.
            one_shot = gf is not None and not gs
            if one_shot:
                body = (_choice.region_body(ct["prompt"], opt_bodies, setup=setup)
                        + _region.if_block(_region.cond_truthy(_region.GLOB_BOOL, gf),
                                           opcodes.terminate_entry(255)) + opcodes.RETURN)
                body = _region.flag_gate(_region.GLOB_BOOL, gf, require_set=gs) + body
                init_body = _region.gated_set_region(zone, _region.GLOB_BOOL, gf)
            else:
                body = _choice.speak_body(ct["prompt"], opt_bodies, setup=setup)
                if gf is not None:
                    body = _region.flag_gate(_region.GLOB_BOOL, gf, require_set=gs) + body
                init_body = None
            eb, _slot = _region.inject_region(eb, zone, body, tag=_region.INTERACT_TAG, init_body=init_body)
        else:
            if (_auto.base is not None and "flag" not in ch
                    and choice_flag_counter >= getattr(project, "flags_per_field", 64) - 1 - EVENTS_PER_FIELD):
                raise BuildError(
                    f"field {project.name}: too many auto-flagged walk-choices overflow this campaign "
                    f"member's flag block -- raise [campaign] flags_per_field or set an explicit flag = N. "
                    f"(Auto choice flags would alias the next member's block -> save corruption.)")
            fidx = int(ch["flag"]) if "flag" in ch else _auto.choice(choice_flag_counter)
            if "flag" not in ch:
                choice_flag_counter += 1
            rb = _event.event_range_body(_choice.region_body(ct["prompt"], opt_bodies, setup=setup), fidx,
                                         flag_class=_region.GLOB_BOOL, requires_flag=gf, requires_set=gs)
            reset = b"" if ch.get("once", True) else _region.set_var(_region.GLOB_BOOL, fidx, 0)
            eb, _slot = _region.inject_region(eb, zone, rb, init_extra=reset)

    # cutscene (narration, no actor): an ordered, control-locked sequence on entry (once), run as a
    # standalone director code entry. Steps = say / wait / set_flag. An ACTOR cutscene was already
    # spliced into its NPC's Init above (actor_choreo), so it's skipped here.
    if cs and not cs_actor:
        steps = [_cutscene.compile_steps(cs["steps"], cutscene_txids)]
        eb = _cutscene.inject_cutscene(eb, steps, once_flag=cs_once_flag)

    # on-entry beats ([[on_entry]]): a gated, once field-load hook -- a narration message and/or a
    # story-state write (set_scenario / set_flags), fired the moment the player enters but ONLY when
    # requires_flag / requires_scenario match. Re-authors an entry cutscene for a SYNTHESIZE fork (a
    # verbatim fork carries the real one in the donor .eb; docs/FORK_FIDELITY.md #10). Each hook is
    # a code entry armed by InitCode in Main_Init. Absent -> no injection (byte-identical).
    eb = _apply_on_entry(project, eb, on_entry_txids, _auto)

    # ladders: FF9's real ladder mechanism -- walk to the base ("!" prompt via tread Bubble) + press
    # action to climb (the region's action func RunScriptSyncs the player's climb function, which runs
    # in the player's own context so it moves the player). Each ladder gets a distinct climb tag.
    # FAITHFUL (climb = "<file>", what import emits): graft the real ladder's exact climb (perspective-
    # correct jump arcs). EMULATED (to = [x, z, y]): a generic teleport to the destination.
    # BIDIRECTIONAL (top=+bottom=): a from-scratch ladder with no real climb -- a zone at each end,
    # each teleporting to the other (consumes two climb tags). A running tag counter keeps multiple
    # ladders (and the two-tag bidirectional ones) from colliding.
    tag = _ladder.FIRST_CLIMB_TAG
    for lad in project.raw.get("ladder", []):
        if lad.get("navigable"):                     # NAVIGABLE: the real FF9 ladder, recreated from 2 endpoints
            zone = None
            if lad.get("zone"):
                z = lad["zone"]
                zone = [tuple(p) for p in (_gw.quad_zone(z) if len(z) == 4 else z)]
            kw = {}
            for k in ("step", "up_mask", "down_mask", "mount_steps", "mount_anim",
                      "top_mount_anim", "top_mount_steps",                # two-way mount: the TOP arc
                      "climb_anim", "climb_frames", "face_angle",
                      "top_field", "top_entrance", "top_worldmap"):
                if k in lad:
                    kw[k] = int(lad[k])
            for k in ("dismount_anim", "dismount_steps"):   # scalar OR [bottom, top] per-end (e.g. CPMP)
                if k in lad:
                    v = lad[k]
                    kw[k] = [int(v[0]), int(v[1])] if isinstance(v, (list, tuple)) else int(v)
            if lad.get("two_way_mount"):                    # mount from EITHER floor (needs top_zone)
                kw["two_way_mount"] = True
            if lad.get("right_alias"):
                kw["right_alias"] = True
            if "dirs" in lad:                            # explicit input bindings: [[mask,"up"|"down"], ...]
                kw["dirs"] = [(int(m), str(d)) for m, d in lad["dirs"]]
            if "top_action" in lad:
                kw["top_action"] = str(lad["top_action"])
            rungs_pts = lad.get("rungs")
            if rungs_pts:                                # MULTI-RUNG (bent vine): rungs override bottom/top
                kw["rungs"] = [[int(c) for c in p] for p in rungs_pts]
                bot, topp = list(rungs_pts[0]), list(rungs_pts[-1])
            else:
                bot, topp = lad["bottom"], lad["top"]
            eb, _ = _ladder.inject_navigable_ladder(
                eb, bottom=bot, top=topp,
                floor_landing=lad.get("floor_landing"), top_landing=lad.get("top_landing"),
                zone=zone, top_zone=lad.get("top_zone"),               # two-way: 2nd trigger at the top floor
                radius=int(lad.get("zone_radius", 200)), climb_tag=tag, **kw)
            # re-entry on-vine spawn: returning via reentry_entrance puts you HIGH on the vine (climb down)
            if "reentry_entrance" in lad:
                frac = float(lad.get("reentry_frac", 0.85))      # how far up the vine you return (0..1)
                if rungs_pts:
                    rx, rz, ry = _point_on_rungs(kw["rungs"], frac)   # ON the bent path, not the chord
                else:
                    bx, bz, by = [int(v) for v in bot]
                    tx, tz, ty = [int(v) for v in topp]
                    rx, rz, ry = round(bx + frac * (tx - bx)), round(bz + frac * (tz - bz)), round(by + frac * (ty - by))
                eb, _ = _ladder.inject_reentry_spawn(
                    eb, int(lad["reentry_entrance"]), rx, rz, ry, climb_tag=tag,
                    face=int(lad.get("face_angle", 0)), climb_anim=int(lad.get("climb_anim", _ladder.CLIMB_ANIM)))
            tag += 1
            continue
        if "top" in lad and "bottom" in lad:
            eb, tag = _ladder.inject_bidirectional_ladder(
                eb, lad["top"], lad["bottom"], radius=int(lad.get("zone_radius", 150)),
                rungs=int(lad.get("rungs", 4)), steps=int(lad.get("steps", 6)),
                animation=lad.get("animation"), first_tag=tag)
            continue
        if "arc_from" in lad and "arc_to" in lad:    # ANIMATED ONE-WAY climb (jump-arc, perspective-correct)
            azone = lad["zone"]
            if len(azone) == 4:
                azone = _gw.quad_zone(azone)
            eb, _ = _ladder.inject_ladder(eb, [tuple(p) for p in azone],
                                          arc_from=lad["arc_from"], arc_to=lad["arc_to"],
                                          rungs=int(lad.get("rungs", 4)), steps=int(lad.get("steps", 6)),
                                          climb_tag=tag)
            tag += 1
            continue
        zone = lad["zone"]
        if len(zone) == 4:
            zone = _gw.quad_zone(zone)
        climb_ref = lad.get("climb")
        climb_bytes = project.path(climb_ref).read_bytes() if climb_ref else None
        sequences = _ladder_sequences(project, climb_ref, climb_bytes) if climb_bytes else None
        eb, _ = _ladder.inject_ladder(eb, [tuple(p) for p in zone],
                                      None if climb_bytes is not None else lad["to"],
                                      climb_bytes=climb_bytes, sequences=sequences,
                                      climb_tag=tag, animation=lad.get("animation"))
        tag += 1

    # jumps: FF9's navigable ledge/gap hops (Ice Cavern etc.) -- a region the player triggers ("!"+press
    # for trigger="action", auto on walk-in for "tread") that RunScriptSyncs the player's verbatim jump
    # arc (the perspective-tuned SetupJump/Jump parabola, copied byte-for-byte from import). The arc's
    # RunJumpAnimation needs a clip, so splice the player's jump animation in once (Zidane's, the blank
    # field's player). Each jump gets a distinct tag, clear of the ladder climb tags above.
    jumps = project.raw.get("jump", [])
    if jumps:
        eb = _jump.ensure_jump_animation(eb)
        jtag = _jump.FIRST_JUMP_TAG
        for jp in jumps:
            jz = jp["zone"]
            if len(jz) == 4:
                jz = _gw.quad_zone(jz)
            jbytes = project.path(jp["jump"]).read_bytes()
            eb, _ = _jump.inject_jump(eb, [tuple(p) for p in jz], jbytes, jump_tag=jtag,
                                      trigger=jp.get("trigger", "action"), bubble=jp.get("bubble", True))
            jtag += 1

    # save points: a press-to-interact region that opens the SAVE menu (Menu(4,0) -> OpenSaveMenu), the
    # functional core of FF9's save moogle (the barrel/moogle/jump-out are cosmetic set-dressing). Unlike a
    # jump, no player-function graft -- the save is a self-contained engine call. docs/SAVEPOINT.md.
    savepoints = project.raw.get("savepoint", [])
    if savepoints:
        sps = [{"zone": _gw.quad_zone(sp["zone"]) if len(sp["zone"]) == 4 else sp["zone"],
                "bubble": sp.get("bubble", True)} for sp in savepoints]
        eb, _ = _savepoint.inject_savepoints(eb, sps)

    # shops: a [[shop]] with a `zone` mints a standalone press-region opener (Menu(2, id), the save-point
    # shape). Shops opened from an NPC instead (via opens_shop) carry no zone and are skipped here; the
    # inventory CSV is written mod-global at the build_mod stage. docs/FORMAT.md.
    shops = [sh for sh in project.raw.get("shop", []) if sh.get("zone")]
    if shops:
        shs = [{"id": int(sh["id"]),
                "zone": _gw.quad_zone(sh["zone"]) if len(sh["zone"]) == 4 else sh["zone"],
                "bubble": sh.get("bubble", True)} for sh in shops]
        eb, _ = _shop.inject_shop_regions(eb, shs)

    # player-function graft: carry the donor PLAYER funcs a carried object RunScripts onto the fork player,
    # so the interactions fire (the cask EXAMINE turn, the box gestures) -- docs/PLAYER_GRAFT.md. The tag
    # allocator is built AFTER the ladder/jump grafts above, so it sees their tags as used and the object
    # band (64+) never collides. graft_player_funcs splices the donor anim packs + adds each func; the
    # resulting tag map then drives the object graft's RunScript(player, T) remap. No-op without [[player_func]].
    player_funcs = project.raw.get("player_func", [])
    player_tag_remap = None
    # text carry un-refuses "text" player funcs: their window TXIDs are remapped + the words shipped, so
    # the func is graft-safe. Without carry, only "clean" funcs graft (a stray "text" stays refused).
    _has_carry = bool(project.raw.get("carry_text", {}).get("bin"))
    _graftable = ("clean", "text") if _has_carry else ("clean",)
    if player_funcs:
        from .content import player as _player
        pf_specs = [{"donor_tag": int(p["donor_tag"]), "safety": p.get("safety", "clean"),
                     "body": project.path(p["bin"]).read_bytes(),
                     "donor_init_packs": p.get("donor_init_packs", [])} for p in player_funcs
                    if p.get("safety", "clean") in _graftable]
        fork_tags = _player.PlayerTagAllocator(eb).take("object", len(pf_specs))
        player_tag_remap = {s["donor_tag"]: ft for s, ft in zip(pf_specs, fork_tags)}
        eb = _player.graft_player_funcs(eb, pf_specs, player_tag_remap, graftable_safeties=_graftable)

    # objects: FAITHFUL carry of the real field's persistent NPCs/props -- graft each donor object's
    # VERBATIM .eb entry at a free slot + arm it from Main_Init (docs/OBJECT_CARRY.md). The authored
    # [[npc]]/[[prop]] blocks (below) are the player-clone synthesis; this is the import-only verbatim
    # graft (renders byte-identical, not "Zidane in a barrel skin"). No-op without [[object]].
    objects = project.raw.get("object", [])
    object_slot_map = {}
    if objects:
        eb = _object.graft_objects(eb, [dict(o) for o in objects],
                                   load=lambda ref: project.path(ref).read_bytes(),
                                   player_tag_remap=player_tag_remap, out_slot_map=object_slot_map)
        # a grafted player func may TurnTowardObject a CARRIED sibling (the save Moogle's 13/14/15 turn toward
        # the Moogle); now that the object graft placed each sibling at its fork slot, remap those uids (a
        # same-length 1-byte patch). No-op without carried siblings (docs/SAVEPOINT.md).
        if player_tag_remap:
            from .content import player as _player
            eb = _player.remap_player_func_siblings(eb, player_tag_remap, object_slot_map)

    # save-Moogle DIRECTOR (docs/SAVEPOINT.md): the carried Moogle is a PUPPET driven by the donor field's
    # entry-0 tag-1 loop (it advances the Moogle's state via shared MAP vars). The object carry misses it
    # (it's main-loop logic, not an object), so graft it into the fork's empty entry-0 tag-1 -- then the
    # Moogle + cask + director reconstitute the source state machine (lower-in-barrel, pop-out, flourish,
    # save). No-op without [[save_moogle]] director. Runs after the object graft so the cluster exists.
    for sm in project.raw.get("save_moogle", []):
        d = sm.get("director")
        if d:
            eb = _savepoint.graft_director(eb, project.path(d).read_bytes())

    # #2b (docs/FORK_FIDELITY.md): STORY-GATED doors carried VERBATIM. A real story-gated door is a complex
    # GLOB-flag conditional the declarative inject_gateway can't reproduce; graft the entry whole + retarget
    # its Field() destinations, so the conditional logic survives (its GLOB conditions read the [startup]
    # story state). No-op without [[gateway_carry]].
    for gc in project.raw.get("gateway_carry", []):
        retarget = {int(k): int(v) for k, v in (gc.get("retarget") or {}).items()}
        eb, _ = _gw.graft_gateway_entry(eb, project.path(gc["bin"]).read_bytes(), retarget=retarget or None)

    # faithful TEXT CARRY (docs/TEXT_CARRY.md): the grafted objects' windows + grafted text player funcs
    # still name the DONOR's .mes txids; remap each to the carried band (>=1000) -- a same-length 2-byte
    # in-place patch -- so they resolve to the verbatim text shipped in the per-language .mes (build_field).
    # No-op without [[carry_text]] (import --carry-text). Runs AFTER both grafts so the fork slots/tags exist.
    carry_plan = project.carry_text_plan()
    if carry_plan:
        from .content import player as _player
        from .content import textcarry as _textcarry
        txid_map = {e.donor_txid: e.new_txid for e in carry_plan}
        if object_slot_map:
            eb = _textcarry.remap_object_windows(eb, [dict(o) for o in objects], object_slot_map, txid_map)
        if player_tag_remap:
            pe = _player.find_player_entry(EbScript.from_bytes(eb))
            eb = _textcarry.remap_player_func_windows(eb, pe, player_tag_remap, txid_map)

    # player spawn (order-independent w.r.t. the appends above)
    if "player" in project.raw and "spawn" in project.raw["player"]:
        sp = project.raw["player"]["spawn"]
        eb = _npc.set_player_spawn(eb, int(sp[0]), int(sp[1]))
    # [player] model= : re-skin the player avatar (the World-Hub Moogle PC, or any model on a free-roam
    # field). Resolved like an [[npc]] model (name/GEO/id -> movement clips via the Info Hub join). Movement
    # clips only -- a scripted-gesture field would glitch (same caveat as --swap-player), so it's free-roam-only.
    if "player" in project.raw and project.raw["player"].get("model") is not None:
        pm = resolve_npc_model(project.raw["player"]["model"])
        eb = _npc.set_player_model(eb, pm, _catalog.npc_anims(pm) or None)

    # encounter (+ the after-battle reinit it requires)
    if has_encounter:
        e = project.raw["encounter"]
        eb = _enc.inject_encounter(eb, scene=int(e["scene"]), freq=int(e.get("freq", 255)),
                                   pattern=int(e.get("pattern", 1)),
                                   scenes=e.get("scenes"))
        eb = _reinit.add_reinit(eb, with_fade=True)

    # field music
    if "music" in project.raw:
        song = int(project.raw["music"]["song"])
        eb = _music.add_field_music(eb, song)
        if has_encounter:  # resume after battle
            eb = _music.add_music_to_reinit(eb, song)
    elif has_encounter:
        # encounter but no music still needs reinit (added above); nothing else to do
        pass

    # after-battle camera restore: a multi-camera field with encounters runs tag-10 (not Main_Init)
    # on battle return, so the flag isn't reset -- re-apply the stored camera. Needs the tag-10 that
    # add_reinit created above.
    if cam_restore is not None and has_encounter:
        used_cams, cvs = cam_restore
        eb = _camera.add_camera_restore(eb, used_cams, cvs)

    return eb


def _actor_token(actor_npc):
    """The animation-catalog model token for a cutscene actor NPC (its ``preset``), or ``None`` if it
    can't be inferred (a custom model => animation steps must use numeric ids)."""
    preset = (actor_npc.get("preset") or actor_npc.get("archetype")) if actor_npc else None
    return preset if preset in _animations.TOKENS else None


def _resolve_anim_steps(steps, actor_npc):
    """Return ``steps`` with each *named* ``animation`` resolved to a numeric id via the actor's
    catalog (``animation = "glad"`` -> the id). Numeric ids pass through untouched. Raises ValueError
    for a name when the actor's model isn't a known preset."""
    token = _actor_token(actor_npc)
    out = []
    for s in steps:
        a = s.get("animation")
        if a is not None and not isinstance(a, bool) and not isinstance(a, int) and not str(a).strip().isdigit():
            if token is None:
                raise ValueError(f"cutscene animation {a!r} is a name, but the actor's model isn't a known "
                                 f"preset -- use a numeric anim id, or give the NPC a preset (vivi/zidane/...).")
            s = {**s, "animation": _animations.resolve(token, a)}
        out.append(s)
    return out


def _position_registry(project: FieldProject) -> dict:
    """name -> (x, z) for movement references in cutscenes: ``player`` / ``spawn`` (the player spawn),
    each ``[[npc]]`` by name, and each ``[[marker]]`` by name. Markers are build-time-only named points
    (placed in Blender / typed in the toml) so a cutscene can ``walk = "fountain"`` instead of raw coords."""
    reg = {}
    sp = project.raw.get("player", {}).get("spawn")
    if sp:
        reg["player"] = reg["spawn"] = (int(sp[0]), int(sp[1]))
    for n in project.raw.get("npc", []):
        if n.get("name") and n.get("pos"):
            reg[n["name"]] = (int(n["pos"][0]), int(n["pos"][1]))
    for m in project.raw.get("marker", []):
        if m.get("name") and m.get("pos"):
            reg[m["name"]] = (int(m["pos"][0]), int(m["pos"][1]))
    return reg


def _resolve_point(value, reg: dict):
    """A walk/teleport target -> (x, z). A ``[x, z]`` list passes through; a string is a marker / NPC /
    player name (a leading ``@`` is optional). Raises ValueError (listing names) on an unknown name."""
    if isinstance(value, (list, tuple)):
        return (int(value[0]), int(value[1]))
    key = str(value).strip()
    key = key[1:] if key.startswith("@") else key
    if key in reg:
        return reg[key]
    raise ValueError(f"movement target {value!r} isn't a [x, z] or a known marker/NPC name. "
                     f"Known: {', '.join(sorted(reg)) or '(none)'} (define a [[marker]] or use [x, z]).")


def _object_names(project: FieldProject) -> set:
    """Names that refer to a LIVE in-game object with a collision box (the player + each NPC) -- as
    opposed to a phantom ``[[marker]]`` point. A walk TO one of these must stop short of its box."""
    names = {"player", "spawn"}
    names.update(n["name"] for n in project.raw.get("npc", []) if n.get("name"))
    return names


# stop a walk-to-an-object this far OUTSIDE the collision box (2 characters collide within
# 2*OBJECT_COLLISION_W = 192u; + this margin so the walk's closest approach stays clear, no press-in).
_APPROACH_MARGIN = 40.0


def _approach_offset(start, target):
    """Pull ``target`` toward ``start`` so the actor stops just outside the target object's collision
    box (walking onto a live object stalls the synchronous walk). Returns ``start`` if already inside."""
    dx, dz = target[0] - start[0], target[1] - start[1]
    d = (dx * dx + dz * dz) ** 0.5
    stop = 2 * cam.OBJECT_COLLISION_W + _APPROACH_MARGIN
    if d <= stop:
        return (int(start[0]), int(start[1]))
    f = (d - stop) / d
    return (int(round(start[0] + dx * f)), int(round(start[1] + dz * f)))


def _resolve_move_steps(steps, project: FieldProject, actor_npc=None):
    """Resolve named ``walk`` / ``teleport`` targets (markers / ``@player`` / NPC names) to ``[x, z]``.
    Coord lists pass through. A ``walk`` to a live OBJECT (player/NPC) auto-stops SHORT of its collision
    box (walk *up to* it), tracking the actor's position through the steps. Raises on an unknown name."""
    reg = _position_registry(project)
    objs = _object_names(project)
    pos = (int(actor_npc["pos"][0]), int(actor_npc["pos"][1])) if (actor_npc and actor_npc.get("pos")) else None
    def _one(v, offset):
        """Resolve one walk/path target to (x, z); offset @object refs short of their box if `offset`."""
        nonlocal pos
        if isinstance(v, str):
            name = v[1:] if v.startswith("@") else v
            tgt = _resolve_point(v, reg)
            if offset and name in objs and pos is not None:
                tgt = _approach_offset(pos, tgt)         # stop adjacent, not inside the object's box
            tgt = (int(tgt[0]), int(tgt[1]))
        else:
            tgt = (int(v[0]), int(v[1]))
        pos = tgt
        return [tgt[0], tgt[1]]

    out = []
    for s in steps:
        s2 = s
        for mk in ("walk", "teleport"):
            if mk in s:
                if s2 is s:
                    s2 = dict(s)
                s2[mk] = _one(s[mk], offset=(mk == "walk"))
        if "path" in s:                                  # a route: each leg resolves like a walk
            if s2 is s:
                s2 = dict(s)
            s2["path"] = [_one(elem, offset=True) for elem in s["path"]]
        out.append(s2)
    return out


def _segment_leaves_floor(wmesh, a, b) -> bool:
    """True if the straight segment a->b, ONCE on the walkmesh, later leaves it (a wall/gap crossing).
    Samples ~every collision radius. Tolerant of an off-mesh START (a walk-in from off-screen) -- the
    path just has to stay on the floor once it's entered. A field walk is straight-line + synchronous,
    so a path that leaves the floor presses into the wall forever and hangs the scene."""
    dx, dz = b[0] - a[0], b[1] - a[1]
    dist = (dx * dx + dz * dz) ** 0.5
    n = max(2, int(dist / max(1.0, cam.COLLISION_RADIUS_W)) + 1)
    on = False
    for i in range(n + 1):
        t = i / n
        here = wmesh.point_on_walkmesh(int(round(a[0] + dx * t)), int(round(a[1] + dz * t))) is not None
        if here:
            on = True
        elif on:
            return True
    return False


def _object_collisions(project: FieldProject, point, exclude_actor):
    """Labels of OTHER live objects (the player + NPCs) whose collision box ``point`` lands inside -- a
    walk there presses into the box and stalls. Threshold ~ two default characters (2*OBJECT_COLLISION_W)."""
    thresh = 2 * cam.OBJECT_COLLISION_W
    objs = []
    sp = project.raw.get("player", {}).get("spawn")
    if sp:
        objs.append(("the player's spawn", sp))
    for n in project.raw.get("npc", []):
        if n.get("name") != exclude_actor and n.get("pos"):
            objs.append((f"NPC {n['name']!r}", n["pos"]))
    return [label for label, p in objs
            if ((point[0] - p[0]) ** 2 + (point[1] - p[1]) ** 2) ** 0.5 < thresh]


def _point_segment_dist(p, a, b) -> float:
    """Exact min distance from point ``p`` to segment ``a``->``b`` (clamped to the segment)."""
    dx, dz = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dz * dz
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / l2))
    cx, cz = a[0] + dx * t, a[1] + dz * t
    return ((p[0] - cx) ** 2 + (p[1] - cz) ** 2) ** 0.5


def _segment_hits_object(project: FieldProject, a, b, exclude_actor):
    """The first OTHER object whose collision box the straight path ``a``->``b`` passes THROUGH (exact
    point-to-segment distance < the collision box). A walk that grazes a standing character is blocked
    there and stalls -- even if both endpoints are clear. Returns the object label or None."""
    thresh = 2 * cam.OBJECT_COLLISION_W
    objs = []
    sp = project.raw.get("player", {}).get("spawn")
    if sp:
        objs.append(("the player's spawn", sp))
    for n in project.raw.get("npc", []):
        if n.get("name") != exclude_actor and n.get("pos"):
            objs.append((f"NPC {n['name']!r}", n["pos"]))
    for label, p in objs:
        if _point_segment_dist(p, a, b) < thresh:
            return label
    return None


def _obstacle_points(project: FieldProject, exclude_actor):
    """(x, z) centres of the live characters a walk must avoid: the player spawn + every other NPC."""
    pts = []
    sp = project.raw.get("player", {}).get("spawn")
    if sp:
        pts.append((int(sp[0]), int(sp[1])))
    for n in project.raw.get("npc", []):
        if n.get("name") != exclude_actor and n.get("pos"):
            pts.append((int(n["pos"][0]), int(n["pos"][1])))
    return pts


def _autoroute_steps(steps, project: FieldProject, wmesh, actor_npc):
    """Auto-pathing: replace a blocked straight ``walk`` (path crosses a wall or a character) with a
    computed route (a ``path``) around the obstacles. A clear walk is left UNTOUCHED (byte-identical);
    ``path`` / ``teleport`` steps are left as authored. No-op without a walkmesh. Used by both the
    builder and the validator so what's checked == what's compiled."""
    if wmesh is None or actor_npc is None or not actor_npc.get("pos"):
        return steps
    actor = actor_npc.get("name")
    obstacles = _obstacle_points(project, actor)
    pos = (int(actor_npc["pos"][0]), int(actor_npc["pos"][1]))
    out = []
    for s in steps:
        if "walk" in s:
            tgt = (int(s["walk"][0]), int(s["walk"][1]))
            target_ok = (wmesh.point_on_walkmesh(tgt[0], tgt[1]) is not None
                         and not _object_collisions(project, tgt, actor))
            blocked = _segment_leaves_floor(wmesh, pos, tgt) or _segment_hits_object(project, pos, tgt, actor)
            if target_ok and blocked:
                wps = _pathfind.route(wmesh, pos, tgt, obstacles)
                if wps and len(wps) > 1:                 # an actual detour, not just the target
                    s = {k: v for k, v in s.items() if k != "walk"}
                    s["path"] = [[int(x), int(z)] for (x, z) in wps]
            pos = tgt
        elif "path" in s:
            if s.get("path"):
                pos = (int(s["path"][-1][0]), int(s["path"][-1][1]))
        elif "teleport" in s:
            pos = (int(s["teleport"][0]), int(s["teleport"][1]))
        out.append(s)
    return out


def _check_walk_leg(project, wmesh, k, frm, tgt, actor, warnings) -> None:
    """One straight walk leg ``frm``->``tgt``: warn if it would stall (target off the floor / inside a
    character's box, or the path crosses a wall / through a character). Shared by ``walk`` + ``path``."""
    if wmesh.point_on_walkmesh(tgt[0], tgt[1]) is None:
        warnings.append(f"[cutscene] step {k}: walk target {tgt} is off the walkmesh -- the actor "
                        f"can't reach it and the scene will stall. Aim at a floor point / marker.")
        return
    hits = _object_collisions(project, tgt, actor)
    blocker = _segment_hits_object(project, frm, tgt, actor)
    if hits:
        warnings.append(f"[cutscene] step {k}: walk target {tgt} is inside {hits[0]}'s collision box -- "
                        f"the actor presses into it and the scene stalls. Walk to @<that object> "
                        f"(auto-stops adjacent), or aim beside it.")
    elif blocker:
        warnings.append(f"[cutscene] step {k}: the walk from {frm} to {tgt} passes through {blocker}'s "
                        f"collision box -- the actor is blocked mid-path and the scene stalls. Route "
                        f"around it via an intermediate marker / a path.")
    elif _segment_leaves_floor(wmesh, frm, tgt):
        warnings.append(f"[cutscene] step {k}: the walk from {frm} to {tgt} crosses off the walkmesh -- "
                        f"the actor presses into the wall and the scene hangs. Route around it via an "
                        f"intermediate marker / a path.")


def _validate_cutscene_movement(project: FieldProject, wmesh, warnings: list) -> None:
    """Warn when an ACTOR cutscene's walk would STALL in-game (a field walk is synchronous + straight-
    line, so a blocked leg softlocks the scene). Validates the FINAL resolved targets (with @object
    auto-approach applied), for ``walk`` AND each ``path`` leg. Turns a runtime hang into a build warning."""
    cs = project.raw.get("cutscene")
    if not cs or not cs.get("actor"):
        return
    actor_npc = next((n for n in project.raw.get("npc", []) if n.get("name") == cs["actor"]), None)
    if not actor_npc or not actor_npc.get("pos"):
        return
    try:
        steps = _resolve_move_steps(cs.get("steps", []), project, actor_npc)   # final targets (offset applied)
    except ValueError:
        return       # an unresolved name -- validate() already reports it
    steps = _autoroute_steps(steps, project, wmesh, actor_npc)   # route blocked walks, then check the result
    pos = (int(actor_npc["pos"][0]), int(actor_npc["pos"][1]))
    for k, s in enumerate(steps):
        if "teleport" in s:
            pos = (int(s["teleport"][0]), int(s["teleport"][1]))
        elif "walk" in s:
            tgt = (int(s["walk"][0]), int(s["walk"][1]))
            _check_walk_leg(project, wmesh, k, pos, tgt, cs["actor"], warnings)
            pos = tgt
        elif "path" in s:
            for wp in s["path"]:
                tgt = (int(wp[0]), int(wp[1]))
                _check_walk_leg(project, wmesh, k, pos, tgt, cs["actor"], warnings)
                pos = tgt


def _wrap_width(project: FieldProject):
    """The dialogue auto-wrap budget (width units) from ``[dialogue] wrap``, or ``None`` if disabled
    (``wrap = false`` / ``0``). Default :data:`content.text.DEFAULT_WRAP_WIDTH` (wrapping ON)."""
    w = project.raw.get("dialogue", {}).get("wrap", _text.DEFAULT_WRAP_WIDTH)
    if w is False or w == 0:
        return None
    if w is True:
        return _text.DEFAULT_WRAP_WIDTH
    return float(w)


def collect_text(project: FieldProject):
    """Return (mes_body, npc_txids, event_txids, cutscene_txids, choice_txids, on_entry_txids). All
    field text (NPC dialogue, event messages, cutscene 'say' lines, choice prompts + replies, on-entry
    messages) shares one .mes block, in that order (so a field with no events/cutscene/choices/on_entry
    is byte-identical to the old layout). ``cutscene_txids`` is a list (one per 'say' step);
    ``choice_txids[c]`` = ``{"prompt": id, "replies": {opt_index: id}}``; ``on_entry_txids[k]`` = the
    txid of hook ``k``'s message (only for hooks that have one).

    Lines are auto-wrapped to fit the screen (FF9 doesn't wrap; see content.text) unless
    ``[dialogue] wrap = false``; a line that already fits is left byte-identical."""
    lines, tails = [], []
    npc_pos, ev_pos, cs_pos = {}, {}, []
    oe_pos = {}                               # on_entry hook idx -> message line
    ch_prompt_pos, ch_reply_pos = {}, {}      # choice idx -> prompt line; (choice, opt) -> reply line
    wrap = _wrap_width(project)

    def _add(src, text):
        # apply the optional `speaker` prefix + per-line `tail`, then auto-wrap; record where it landed
        line = _text.with_speaker(src.get("speaker"), text)
        if wrap is not None:
            line = _text.wrap_text(line, wrap)[0]
        lines.append(line)
        tails.append(src.get("tail"))
        return len(lines) - 1

    def _add_raw(line, tail):
        lines.append(line)                    # pre-assembled (e.g. a choice prompt) -- added verbatim
        tails.append(tail)
        return len(lines) - 1

    for i, n in enumerate(project.raw.get("npc", [])):
        if "dialogue" in n:
            npc_pos[i] = _add(n, n["dialogue"])
    for j, ev in enumerate(project.raw.get("event", [])):
        if "message" in ev:
            ev_pos[j] = _add(ev, ev["message"])
        elif ev.get("received") and "give_item" in ev:
            # canonical item-get text: [ITEM=0] renders the item name from text-var slot 0 (set at
            # runtime by SetTextVariable(0, item)); shown in the window-7 item-get box. Added verbatim
            # (the [ITEM=0] tag must survive wrapping).
            ev_pos[j] = _add_raw("Received [ITEM=0]!", ev.get("tail"))
    for step in project.raw.get("cutscene", {}).get("steps", []):
        if "say" in step:
            cs_pos.append(_add(step, step["say"]))
    # choices: the prompt + option rows are ONE entry (prompt[CHOO][MOVE]opt0\n[MOVE]opt1...); each
    # option's optional `reply` is its own entry. The question is wrapped; the menu rows are not (a row
    # is short by design -- an over-wide one is caught by lint, not silently re-flowed).
    for c, ch in enumerate(project.raw.get("choice", [])):
        q = _text.with_speaker(ch.get("speaker"), ch.get("prompt", ""))
        if wrap is not None:
            q = _text.wrap_text(q, wrap)[0]
        opts = [str(o.get("text", "")) for o in ch.get("options", [])]
        pre_tag = _choice.pre_choose(ch)[1]   # [PCHC]/[PCHM] config tag (default/cancel/disabled); "" if none
        prompt_line = pre_tag + q + _text.CHOICE_OPEN + ("\n" + _text.CHOICE_INDENT).join(opts)
        ch_prompt_pos[c] = _add_raw(prompt_line, ch.get("tail"))
        for oi, o in enumerate(ch.get("options", [])):
            if o.get("reply"):
                ch_reply_pos[(c, oi)] = _add(o, o["reply"])
    # on-entry beats: a hook's narration message. Added LAST so a field without [[on_entry]] is
    # byte-identical to the previous layout (no existing line shifts).
    for k, h in enumerate(project.raw.get("on_entry", [])):
        if isinstance(h, dict) and "message" in h:
            oe_pos[k] = _add(h, h["message"])
    if not lines:
        return "", {}, {}, [], {}, {}
    body, mapping = _text.build_mes(lines, start_txid=_text.DEFAULT_BASE_TXID, tails=tails)
    npc_txids = {i: mapping[p] for i, p in npc_pos.items()}
    event_txids = {j: mapping[p] for j, p in ev_pos.items()}
    cutscene_txids = [mapping[p] for p in cs_pos]
    choice_txids = {c: {"prompt": mapping[p],
                        "replies": {oi: mapping[ch_reply_pos[(cc, oi)]]
                                    for (cc, oi) in ch_reply_pos if cc == c}}
                    for c, p in ch_prompt_pos.items()}
    on_entry_txids = {k: mapping[p] for k, p in oe_pos.items()}
    return body, npc_txids, event_txids, cutscene_txids, choice_txids, on_entry_txids


# --------------------------------------------------------------------------- the build

@dataclass
class FieldResult:
    dict_line: str
    battle: tuple | None = None     # (scene, music) for BattlePatch, or None
    fbg: str = ""
    warnings: list = _dc_field(default_factory=list)


def _autofill_ladder_landing_y(project: FieldProject, wmesh) -> None:
    """Fill an OMITTED navigable-ladder dismount-floor Y from the walkmesh height, so the dismount lands
    at the floor's real height instead of arcing to Y=0 then snapping up (the fall+slingshot on elevated
    floors -- e.g. CPMP). The SetupJump dest's height is -worldY, so the landing Y = -height_at(x,z). A
    flat floor (height 0) is left unchanged, so flat rooms stay byte-identical. Only fills [x, z] landings
    (no explicit Y); an author-supplied Y is respected."""
    if wmesh is None:
        return
    for lad in project.raw.get("ladder", []):
        if not lad.get("navigable"):
            continue
        for key in ("floor_landing", "top_landing"):
            p = lad.get(key)
            if p and len(p) == 2:                      # (x, z) with no Y -> look up the floor height
                h = wmesh.height_at(int(p[0]), int(p[1]))
                if h:                                  # elevated floor (non-zero / on-mesh)
                    lad[key] = [int(p[0]), int(p[1]), -int(h)]


def build_field(project: FieldProject, layout: ModLayout, *, langs=LANGS) -> FieldResult:
    """Write one field's assets into the mod ``layout``. Returns its registration info."""
    problems = validate(project)
    if problems:
        raise BuildError("invalid field project:\n  - " + "\n  - ".join(problems))

    fbg = project.fbg
    layout.ensure_dirs(fbg, langs=langs)

    camera = resolve_camera(project)
    warnings = list(lint_logic(project))          # story/flag sanity (dangling requires, collisions, dup names)
    pw = cam.pitch_warning(cam.pitch_deg(camera))
    if pw:
        warnings.append(pw)

    # BG-borrow (import mode): the DictionaryPatch points the BG lookup at a REAL base-game field
    # (areaID + borrow_bg mapid), so the engine renders that field's art + walkmesh + camera while
    # running OUR script. We ship only the .eb (no custom scene). The borrowed `camera.bgx` still
    # drives movement/scroll derivation + content guidance. Proven path (Session 4). Otherwise build
    # a full custom scene (camera + walkmesh + overlays -> .bgx / .bgi / PNGs).
    borrow_bg = project.field.get("borrow_bg")
    native_bgs = project.field.get("bgs")       # NATIVE custom scene (Moguri/vanilla path): own .bgs + atlas
    cutscene_wmesh = None                       # walkmesh used to auto-route cutscene walks (custom or borrow)
    if native_bgs:
        # Ship atlas.png + <FBG>.bgs.bytes + the custom <FBG>.bgi.bytes and NO .bgx, so the engine's
        # BGSCENE_DEF.LoadResources takes the NATIVE branch (LoadAtlasAndEBG, not ReadMemoriaBGS): a
        # point-sampled atlas + per-tile-depth quads = NO seams + faithful occlusion (the .bgs already
        # carries per-tile depth -- unlike a .bgx, which pins one depth per overlay PNG). This is exactly
        # how Moguri ships (vanilla .bgs + a high-res atlas, no .bgx). Repaint = swap atlas.png / the
        # Memoria PSD pipeline. Area is remapped >= 10 by the importer so the FBG lookup doesn't black-screen.
        bgi_bytes = resolve_walkmesh(project, camera, warnings)
        wmesh = bgi.BgiWalkmesh.from_bytes(bgi_bytes)
        cutscene_wmesh = wmesh
        _validate_content_placement(project, wmesh, warnings)
        _validate_walkmesh_geometry(project, wmesh, warnings)
        fm = layout.fieldmap_dir(fbg)
        shutil.copyfile(project.path(native_bgs), fm / f"{fbg}.bgs.bytes")
        if project.field.get("atlas"):
            shutil.copyfile(project.path(project.field["atlas"]), fm / "atlas.png")
        (fm / f"{fbg}.bgi.bytes").write_bytes(bgi_bytes)
        # the field's 3D-model LIGHTING (MapConfigData: per-floor lights + shadows + per-object colors),
        # shipped under the fork's event name so the engine lights the models like the real field. Loaded
        # by the SAME event name as the .eb (MapConfiguration.LoadMapConfigData) -> EVT_<name>.bytes.
        mapconfig = project.field.get("mapconfig")
        if mapconfig:
            dst = layout.mapconfig_path(f"EVT_{project.name}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(project.path(mapconfig), dst)
    elif not borrow_bg:
        bgi_bytes = resolve_walkmesh(project, camera, warnings)
        wmesh = bgi.BgiWalkmesh.from_bytes(bgi_bytes)
        cutscene_wmesh = wmesh
        # content placement: warn when an NPC / spawn / gateway sits OFF the walkable area -- the
        # recurring in-game mistake (an NPC floats, the player can't reach a trigger). Always checked.
        _validate_content_placement(project, wmesh, warnings)
        # art: warn when a (repainted) layer's PNG aspect won't match its size quad (stretch/misalign).
        _validate_layer_art(project, camera.range, warnings)
        _validate_walkmesh_geometry(project, wmesh, warnings)
        overlays = build_overlays(project, range_wh=tuple(camera.range))
        # multi-camera: write all N CAMERA blocks (overlays carry their camera_id); single-camera
        # fields pass one Cam and are byte-identical to before.
        cameras = resolve_cameras(project)
        scene_cam = cameras if len(cameras) > 1 else camera
        bgx_text = bgx.build(scene_cam, overlays, header_comment=project.field.get("title", project.name))

        fm = layout.fieldmap_dir(fbg)
        (fm / f"{fbg}.bgx").write_text(bgx_text, encoding="utf-8", newline="\n")
        (fm / f"{fbg}.bgi.bytes").write_bytes(bgi_bytes)
        for layer in project.raw.get("layers", []):
            src = project.path(layer["image"])
            shutil.copyfile(src, fm / Path(layer["image"]).name)
    else:
        # BG-borrow ships no walkmesh (the engine uses the borrowed field's real one), but we can still
        # validate content placement against it: [walkmesh] reference (or the sibling walkmesh.bgi the
        # importer wrote). Makes the off-walkmesh guard universal -- borrow forks are the common case.
        ref = _borrow_walkmesh(project)
        cutscene_wmesh = ref
        if ref is not None:
            _validate_content_placement(project, ref, warnings)

    _autofill_ladder_landing_y(project, cutscene_wmesh)   # elevated dismount floors get their real Y
    # --- dialogue + per-language script ---
    mes_body, txids, event_txids, cutscene_txids, choice_txids, on_entry_txids = collect_text(project)
    control_value = resolve_control_value(project, camera)
    # faithful text carry: the donor's referenced dialogue, shipped VERBATIM per language and APPENDED after
    # the authored block (its own [TXID=>=1000] re-index keeps it disjoint -- authored text + the hut golden
    # are byte-identical). build_script remaps the grafted windows to these txids. Empty plan -> no change.
    carry_plan = project.carry_text_plan()
    # Verbatim-.eb fork (docs/FORK_FIDELITY.md, the entry-0 carry): ship the donor's WHOLE event script
    # (entry-0 + all objects + all gateways, layout intact, Field() destinations remapped) instead of
    # synthesizing one -- the field runs its real logic. None unless the project has a [verbatim_eb] block.
    from .content import verbatim as _verbatim
    verbatim_bytes = _verbatim.verbatim_eb(project)
    oe_suffix: dict = {}
    if verbatim_bytes is not None:
        # the verbatim .eb bypasses build_script, so apply the field-load hooks HERE too -- else the
        # documented "pair with [startup] to boot a beat" is a silent no-op (the fork would boot at
        # scenario-zero), and [[on_entry]] beats would never fire. Both arm into the donor's Main_Init;
        # the .eb is language-identical, so inject once before the per-language loop. An [[on_entry]]
        # narration MESSAGE is given a text channel by APPENDING it to the donor `.mes` above the donor's
        # txids (oe_suffix, added per-language below); its WindowSync resolves into that appended entry.
        # ~11% of real fields have a 0x06 jump table at the top of Main_Init that the byte inserter can't shift
        # past -> fail closed with a clear BuildError (not an opaque ValueError) if the author asked for a
        # field-load block on such a donor (shared by all three levers; a no-block field never calls insert).
        verbatim_bytes = _field_load_inject("[startup]", project.name,
                                            lambda: _apply_startup(project, verbatim_bytes))
        verbatim_bytes = _field_load_inject("[party]", project.name,
                                            lambda: _apply_party(project, verbatim_bytes, warnings=warnings))
        oe_msg_txids, oe_suffix = _verbatim_on_entry_messages(project, langs)
        verbatim_bytes = _field_load_inject("[[on_entry]]", project.name,
                                            lambda: _apply_on_entry(project, verbatim_bytes, oe_msg_txids,
                                            _FlagAlloc(getattr(project, "flag_base", None)), warnings=warnings))
        # a [[shop]] OPENER (a standalone `zone` region, or an `[[npc]] opens_shop`) is synthesized in
        # build_script, which the verbatim path bypasses -- so it is NOT injected here (the donor's own
        # logic ships instead). The inventory CSV still ships (mod-write stage). Warn so it isn't a silent
        # no-op; wire the opener on a synthesized field, or open the shop from the donor's own carried logic.
        _shop_openers = ([s for s in project.raw.get("shop", []) if s.get("zone")]
                         + [n for n in project.raw.get("npc", []) if n.get("opens_shop") is not None])
        if _shop_openers:
            warnings.append("[[shop]] opener (zone region / [[npc]] opens_shop) is NOT injected into a verbatim "
                            "fork -- the donor's own .eb ships instead; the shop inventory CSV is still written. "
                            "Author the opener on a synthesized field if you need it.")
    for lang in langs:
        if verbatim_bytes is not None:
            eb = verbatim_bytes
            # the donor's WHOLE text (index-txids) + any appended [[on_entry]] narration lines (high txids)
            lang_body = (_verbatim.verbatim_mes(project, lang) or "") + oe_suffix.get(lang, "")
        else:
            eb = build_script(project, lang, txids, control_value, event_txids=event_txids,
                              cutscene_txids=cutscene_txids, walkmesh=cutscene_wmesh,
                              choice_txids=choice_txids, on_entry_txids=on_entry_txids)
            lang_body = mes_body
            if carry_plan:
                from .content import textcarry as _textcarry
                lang_body = (mes_body or "") + _textcarry.carried_mes_body(carry_plan, lang)
        layout.eb_path(lang, f"EVT_{project.name}.eb.bytes").write_bytes(eb)
        if lang_body:
            layout.mes_path(lang, project.text_block).write_text(lang_body, encoding="utf-8", newline="\n")

    bg_mapid = borrow_bg if borrow_bg else project.name
    dict_line = f"FieldScene {project.id} {project.area} {bg_mapid} {project.name} {project.text_block}"
    battle = None
    if "encounter" in project.raw:
        e = project.raw["encounter"]
        battle = (int(e["scene"]), int(e.get("battle_music", 0)))
    return FieldResult(dict_line=dict_line, battle=battle, fbg=fbg, warnings=warnings)


def _field_name(project) -> str:
    return str((project.raw.get("field") or {}).get("name", "?"))


def _emit_battle_data(projects, layout) -> list:
    """Emit the mod-GLOBAL battle-data CSV deltas from every project's ``[[battle_action]]`` / ``[[status]]``
    blocks -> ``Data/Battle/Actions.csv`` / ``StatusData.csv``. These are always-on global data (NOT
    new-game/entry-restricted), so they aggregate across ALL fields in the build. Reads the base CSVs from the
    install (whole-row replacement); raises BuildError if the install can't be read or an entry is invalid."""
    actions = [a for p in projects for a in p.raw.get("battle_action", [])]
    statuses = [s for p in projects for s in p.raw.get("status", [])]
    if not actions and not statuses:
        return []
    from .battle import actiondelta as _adelta
    try:
        return _adelta.write_battle_data(layout, actions=actions, statuses=statuses)
    except _adelta.ActionDeltaError as ex:
        raise BuildError(str(ex))


def _emit_character_data(projects, layout) -> list:
    """Emit the mod-GLOBAL player-side balance CSVs from every project's ``[[character]]`` (BaseStats.csv, per-id
    partial delta) / ``[[leveling]]`` (Leveling.csv, WHOLE-FILE 99 rows) blocks. Always-on global data,
    aggregated across ALL fields. Reads the base CSVs from the install; raises BuildError on a bad entry."""
    # normalize a single-table [character]/[leveling] (a dict) to a one-element list, matching validate_field --
    # so a `[character]` typo (vs the array-of-tables `[[character]]`) builds the same one entry the lint sees,
    # instead of iterating the dict's KEYS into a misleading "must be a table (got str)" error.
    def _blocks(key):
        out = []
        for p in projects:
            b = p.raw.get(key, [])
            out += b if isinstance(b, list) else [b]
        return out
    characters = _blocks("character")
    levelings = _blocks("leveling")
    if not characters and not levelings:
        return []
    from .battle import characterdelta as _cdelta
    try:
        return _cdelta.write_character_data(layout, characters=characters, levelings=levelings)
    except _cdelta.CharacterDeltaError as ex:
        raise BuildError(str(ex))


def _emit_battle_patch(projects) -> tuple:
    """Aggregate every project's ``[[battle_patch]]`` (scene-scoped) + ``[[battle_enemy]]`` / ``[[battle_attack]]``
    (global by-name) blocks -> (battle_patch_lines, warnings). Mod-GLOBAL reflection patches (always-on, not
    new-game-scoped), so they aggregate across ALL built fields -- the same model as ``[[battle_action]]``.
    Pure/offline (names are the author's; masks come from the committed tables); raises BuildError on a bad
    block. Returns ([], []) when no field carries one (no BattlePatch contribution)."""
    scene_patches = [b for p in projects for b in p.raw.get("battle_patch", [])]
    enemies = [b for p in projects for b in p.raw.get("battle_enemy", [])]
    attacks = [b for p in projects for b in p.raw.get("battle_attack", [])]
    if not (scene_patches or enemies or attacks):
        return [], []
    from .battle import battlepatch as _bp
    try:
        return _bp.build_lines(scene_patches, enemies, attacks)
    except _bp.BattlePatchError as ex:
        raise BuildError(str(ex))


def _emit_start_state(projects, layout, entry_project=None) -> list:
    """Emit the mod-GLOBAL new-game CSV deltas ONCE into the mod root, from the ENTRY field's blocks:
    ``[start_inventory]`` -> ``Data/Items/InitialItems.csv`` (the FULL starting bag, highest-priority-wins) and
    ``[[equipment]]`` -> ``Data/Characters/DefaultEquipment.csv`` (a partial per-character delta, merged by the
    engine). These are mod-global files (not field ``.eb`` bytes), so they're written at the mod-write stage,
    not during eb-synthesis. Returns warnings (the non-entry-field lint + the shadow-hazard note).

    ``entry_project`` (a campaign's entry member) makes the non-entry lint PRECISE: a block on ANY non-entry
    member is warned + ignored, and the emit reads the entry member's block. For a single-field / plain build
    (``entry_project`` None) the sole block-carrier IS the de-facto entry, and >1 carriers is warned."""
    from .content import equipment as _eqp
    from .content import inventory as _inv
    warnings: list = []
    inv_fields = [p for p in projects if p.raw.get("start_inventory")]
    eqp_fields = [p for p in projects if p.raw.get("equipment")]

    def _pick(fields, block):
        """The authoritative carrier of a mod-GLOBAL block (exactly one), plus the non-entry/duplicate lint."""
        if entry_project is not None:                       # campaign: precise -- only the entry member is authoritative
            for p in fields:
                if p is not entry_project:
                    warnings.append(f"{block} is on a NON-entry field ({_field_name(p)}) -- it is mod-global; "
                                    f"put it on the entry field ({_field_name(entry_project)}) only (ignored)")
            return entry_project if entry_project in fields else None
        if len(fields) > 1:                                 # plain build: the first block-carrier is the de-facto entry
            warnings.append(f"{block} is mod-GLOBAL but is on {len(fields)} fields "
                            f"({', '.join(_field_name(p) for p in fields)}) -- only the ENTRY field should carry "
                            f"it; using {_field_name(fields[0])}, ignoring the rest")
        return fields[0] if fields else None

    inv_src = _pick(inv_fields, "[start_inventory]")
    eqp_src = _pick(eqp_fields, "[[equipment]]")
    if inv_src is not None:
        _inv.write_initial_items(layout, inv_src.raw["start_inventory"].get("items", []))
        warnings.append("[start_inventory] -> InitialItems.csv is HIGHEST-priority-wins: it REPLACES the base "
                        "starting bag, a stacked mod folder's InitialItems.csv would SHADOW it, and it only "
                        "affects a true New Game (not an F6/campaign mid-game entry)")
    if eqp_src is not None:
        _eqp.write_default_equipment(layout, eqp_src.raw["equipment"])
    return warnings


def _emit_shops(projects, layout) -> list:
    """Emit the mod-GLOBAL custom-shop inventory delta (``Data/Items/ShopItems.csv``) from EVERY built field's
    ``[[shop]]`` blocks. Unlike the new-game state, shops are NOT entry-restricted -- the engine merges them by
    id, so any field may define its own shops; only their ids must be unique across the mod (a duplicate id is
    warned + last-wins). No ``[[shop]]`` anywhere -> no file written (no base clobber). Returns warnings."""
    warnings: list = []
    shops, seen = [], {}
    for p in projects:
        for sh in p.raw.get("shop", []):
            try:                                            # build doesn't run validate(); don't crash on a bad id
                sid = int(sh["id"])
            except (KeyError, TypeError, ValueError):
                warnings.append(f"[[shop]] on {_field_name(p)} has a missing/invalid id {sh.get('id')!r} -- "
                                f"skipped (run `ff9mapkit lint` for the precise error)")
                continue
            # the two checks are INDEPENDENT (a vanilla id defined twice is both a dup AND an override)
            if sid in seen:
                warnings.append(f"[[shop]] id {sid} is defined twice ({seen[sid]} and {_field_name(p)}) -- the "
                                f"later one wins (the engine merges shops by id)")
            if sid < _shop.FIRST_CUSTOM_SHOP:
                warnings.append(f"[[shop]] id {sid} OVERRIDES vanilla shop {sid} (base shops are "
                                f"0-{_shop.FIRST_CUSTOM_SHOP - 1}); use id >= {_shop.FIRST_CUSTOM_SHOP} for a net-new shop")
            seen[sid] = _field_name(p)
            shops.append(sh)
    # a shopkeeper NPC (opens_shop) pointing at a CUSTOM id (>= 32) that no [[shop]] defines opens an empty
    # shop -- usually a typo or a forgotten [[shop]] block. A vanilla id (0-31) is fine (it's in the base CSV).
    for p in projects:
        for n in p.raw.get("npc", []):
            ref = n.get("opens_shop")
            if isinstance(ref, int) and not isinstance(ref, bool) \
                    and ref >= _shop.FIRST_CUSTOM_SHOP and ref not in seen:
                warnings.append(f"[[npc]] {n.get('name', '?')!r} opens_shop = {ref}, but no [[shop]] defines "
                                f"shop {ref} -- it will be empty (define a [[shop]] id = {ref})")
    if shops:
        _shop.write_shop_items(layout, shops)
    return warnings


def build_mod(projects, out_root, *, mod_name="FF9CustomMap", author="", description="",
              langs=LANGS, entry_project=None) -> dict:
    """Build one or more fields into a mod at ``out_root``; write the registration files. ``entry_project``
    (a campaign's entry member) makes the mod-global new-game-state lint precise -- see :func:`_emit_start_state`."""
    layout = ModLayout(Path(out_root).resolve())
    results = [build_field(p, layout, langs=langs) for p in projects]

    layout.dictionary_patch.write_text(
        "\n".join(r.dict_line for r in results) + "\n", encoding="utf-8", newline="\n")

    # BattlePatch.txt = the per-encounter BGM block (Battle:/Music:) + the Phase-4 by-name enemy/attack/scene
    # tuning blocks ([[battle_patch]] / [[battle_enemy]] / [[battle_attack]]). Both are mod-global reflection
    # patches that coexist in one file -- each Battle:/AnyEnemyByName: selector opens an independent patch.
    bp_lines: list[str] = []
    for scene, mus in (r.battle for r in results if r.battle):
        bp_lines += [f"Battle: {scene}", f"Music: {mus}"]
    tune_lines, bp_warnings = _emit_battle_patch(projects)
    bp_lines += tune_lines
    if bp_lines:
        layout.battle_patch.write_text("\n".join(bp_lines) + "\n", encoding="utf-8", newline="\n")

    # mod-global new-game starting state (CSV deltas, written once into the mod root -- not field bytes)
    start_warnings = _emit_start_state(projects, layout, entry_project)
    start_warnings += _emit_shops(projects, layout)
    start_warnings += _emit_battle_data(projects, layout)
    start_warnings += _emit_character_data(projects, layout)
    start_warnings += bp_warnings

    layout.mod_description.write_text(
        "<Mod>\n"
        f"    <Name>{mod_name}</Name>\n"
        f"    <Author>{author}</Author>\n"
        f"    <InstallationPath>{mod_name}</InstallationPath>\n"
        "    <Category></Category>\n"
        f"    <Description>{description}</Description>\n"
        "</Mod>\n",
        encoding="utf-8", newline="\n")

    return {"root": str(layout.root), "fields": [r.fbg for r in results],
            "dictionary": [r.dict_line for r in results],
            "warnings": [w for r in results for w in r.warnings] + start_warnings}
