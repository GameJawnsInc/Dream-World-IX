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
from .content import movement as _movement
from .content import music as _music
from .content import npc as _npc
from .content import pathfind as _pathfind
from .content import region as _region
from .content import reinit as _reinit
from .content import text as _text
from . import animations as _animations
from . import items as _items
from . import data as _data
from .eb import EbScript, opcodes
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

    @classmethod
    def load(cls, toml_path) -> "FieldProject":
        p = Path(toml_path)
        with p.open("rb") as fh:
            base = tomllib.load(fh)
        scene = _find_scene(p, base)
        raw = _merge_scene(base, scene) if scene is not None else base
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


# --------------------------------------------------------------------------- validation

def validate(project: FieldProject) -> list[str]:
    """Return a list of human-readable problems (empty => OK)."""
    problems = []
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
    for layer in project.raw.get("layers", []):
        if "image" not in layer:
            problems.append("[[layers]] entry missing 'image'")
        elif not project.path(layer["image"]).is_file():
            problems.append(f"[[layers]] image not found: {layer['image']}")
    for i, n in enumerate(project.raw.get("npc", [])):
        if "pos" not in n:
            problems.append(f"[[npc]] {n.get('name', '#' + str(i))!r} has no position -- set "
                            f"pos = [x, z] in the field.toml, or place its marker in the Blender scene.")
    for gw in project.raw.get("gateway", []):
        if "to" not in gw:
            problems.append("[[gateway]] needs a 'to' (destination field id).")
        z = gw.get("zone", [])
        if len(z) not in (4, 5):
            problems.append(f"[[gateway]] zone must have 4 or 5 points (got {len(z)})")
    for ev in project.raw.get("event", []):
        z = ev.get("zone", [])
        if len(z) not in (4, 5):
            problems.append(f"[[event]] zone must have 4 or 5 points (got {len(z)})")
        if not any(k in ev for k in ("message", "give_item", "gil", "set_flag")):
            problems.append("[[event]] needs at least one action (message / give_item / gil / set_flag)")
        if "give_item" in ev:
            try:
                _items.resolve(ev["give_item"][0])
            except (ValueError, IndexError, TypeError) as e:
                problems.append(f"[[event]] give_item: {e}")
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
                for key in ("give_item", "set_flag"):
                    if key in o and (not isinstance(o[key], list) or len(o[key]) < 1):
                        problems.append(f"[[choice]] #{c} option {oi} {key} must be a list, "
                                        f"e.g. [\"Potion\", 1]")
                if isinstance(o.get("give_item"), list) and o["give_item"]:
                    try:
                        _items.resolve(o["give_item"][0])
                    except (ValueError, TypeError) as e:
                        problems.append(f"[[choice]] #{c} option {oi} give_item: {e}")
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
        anim_token = actor_npc.get("preset") if actor_npc else None
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
                auto_once.add(_event.EVENT_FLAG_BASE + counter)
            counter += 1
    cs = raw.get("cutscene")           # a cutscene also sets flags (set_flag steps + its own once-flag)
    if cs:
        for step in cs.get("steps", []):
            if "set_flag" in step:
                settable.add(int(step["set_flag"][0])); explicit.add(int(step["set_flag"][0]))
        if cs.get("once", True):
            f = int(cs["flag"]) if "flag" in cs else _cutscene.DEFAULT_CUTSCENE_FLAG
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
                auto_once.add(_choice.CHOICE_FLAG_BASE + choice_counter)
                choice_counter += 1
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

    # pre-choose: a choice's `default` can't sit at/after a greyed (`disabled`) row. The engine
    # (SetChooseParam) converts the absolute default into the AVAILABLE-row index, but Dialog then reads
    # it as ABSOLUTE -- so a default past a disabled row falls back to the first available row instead of
    # the one you meant. (Confirmed by an in-engine probe.) Warn rather than silently mis-highlight.
    for c, ch in enumerate(raw.get("choice", [])):
        d = ch.get("default")
        if isinstance(d, int) and d > 0:
            bad = [i for i, o in enumerate(ch.get("options", [])) if o.get("disabled") and i <= d]
            if bad:
                out.append(f"[[choice]] #{c} default = {d} can't be honored: option(s) {bad} at/before it "
                           f"are disabled, so FF9 highlights the first available row instead. Use default = 0 "
                           f"or don't grey out rows before the default (engine limitation).")

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
    return out


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

    for i, n in enumerate(project.raw.get("npc", [])):
        p = n.get("pos")
        if not p:
            continue
        label = f"NPC {n.get('name', f'#{i}')!r} at ({int(p[0])}, {int(p[1])})"
        if off(p[0], p[1]):
            warnings.append(f"{label} is off the walkmesh -- it will float / be unreachable. "
                            f"Move it onto the walkable area.")
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


def build_script(project: FieldProject, lang: str, dialogue_txids: dict,
                 control_value: int = -1, event_txids: dict | None = None,
                 cutscene_txids: list | None = None, walkmesh=None,
                 choice_txids: dict | None = None) -> bytes:
    """Build one language's .eb by applying the project's content to the blank field."""
    event_txids = event_txids or {}
    cutscene_txids = cutscene_txids or []
    choice_txids = choice_txids or {}
    # a choice attached to an NPC (choice.npc == npc.name) replaces that NPC's talk with a branch.
    choice_by_npc = {ch["npc"]: (c, ch) for c, ch in enumerate(project.raw.get("choice", []))
                     if "npc" in ch}
    eb = _data.blank_field_bytes(lang)
    # movement control-direction first (shift-free, before any appends that move bytecode)
    if control_value != -1:
        eb = _movement.set_control_direction(eb, control_value)
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
        cs_once_flag = int(cs["flag"]) if "flag" in cs else _cutscene.DEFAULT_CUTSCENE_FLAG
    actor_choreo = None
    if cs_actor:
        actor_npc = next((n for n in project.raw.get("npc", []) if n.get("name") == cs_actor), None)
        steps = _resolve_anim_steps(cs["steps"], actor_npc)   # animation = "glad" -> the numeric id
        steps = _resolve_move_steps(steps, project, actor_npc)  # names -> [x,z]; @object walks stop short
        steps = _autoroute_steps(steps, project, walkmesh, actor_npc)  # route blocked walks around obstacles
        cs_fclass, cs_fidx = _cutscene.once_flag_for(cs)   # GLOB (once ever) or MAP (replay per visit)
        actor_choreo = _cutscene.build_choreography(
            steps, cutscene_txids, cs_fidx, flag_class=cs_fclass,
            warmup=int(cs.get("warmup", _cutscene.DEFAULT_WARMUP)))

    # NPCs (cloned from the player object) first, so their cloned positions are independent.
    gated_npc_slots = {}     # flag index -> [npc entry slots] (for live reveal when an event flips it)
    for i, n in enumerate(project.raw.get("npc", [])):
        pos = n["pos"]
        txid = dialogue_txids.get(i, int(n.get("text_id", _text.DEFAULT_BASE_TXID)))
        kwargs = {}
        if "preset" in n:
            kwargs["preset"] = n["preset"]
        else:
            kwargs.update(model=n.get("model"), animset=n.get("animset"), anims=n.get("anims"))
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
        eb = _npc.inject_npc(eb, int(pos[0]), int(pos[1]), talk_text_id=txid, slot=slot,
                             gate_flag=gf, gate_require_set=gs, intro=intro, speak_body=sb, **kwargs)
        if gf is not None:
            gated_npc_slots.setdefault(gf, []).append(slot)

    # gateways
    for gw in project.raw.get("gateway", []):
        zone = gw["zone"]
        if len(zone) == 4:
            zone = _gw.quad_zone(zone)
        gf, gs = _gate_of(gw)
        eb = _gw.inject_gateway(eb, int(gw["to"]), entrance=int(gw.get("entrance", 0)),
                                zone=[tuple(p) for p in zone], gate_flag=gf, gate_require_set=gs)

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
            if "give_item" in ev:
                gi = ev["give_item"]
                parts.append(_event.give_item(gi[0], int(gi[1]) if len(gi) > 1 else 1))   # id or name
            if "gil" in ev:
                parts.append(_event.give_gil(int(ev["gil"])))
            if j in event_txids:
                parts.append(_event.message(event_txids[j]))
            if "set_flag" in ev:
                sf = ev["set_flag"]
                fidx = int(sf[0])
                parts.append(_event.set_flag(fidx, int(sf[1]) if len(sf) > 1 else 1))
                # live reveal: re-init any NPC gated on this flag so it appears/vanishes immediately
                # (its Init re-checks the gate with the flag's new value), not just on field re-entry.
                for npc_slot in gated_npc_slots.get(fidx, []):
                    parts.append(_event.reveal_object(npc_slot))
            once_flag = None
            if ev.get("once", True):
                once_flag = int(ev["flag"]) if "flag" in ev else (_event.EVENT_FLAG_BASE + flag_counter)
                flag_counter += 1
            gf, gs = _gate_of(ev)
            specs.append({"zone": [tuple(p) for p in ev["zone"][:4]],
                          "body": b"".join(parts), "once_flag": once_flag,
                          "requires_flag": gf, "requires_set": gs})
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
            fidx = int(ch["flag"]) if "flag" in ch else (_choice.CHOICE_FLAG_BASE + choice_flag_counter)
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

    # player spawn (order-independent w.r.t. the appends above)
    if "player" in project.raw and "spawn" in project.raw["player"]:
        sp = project.raw["player"]["spawn"]
        eb = _npc.set_player_spawn(eb, int(sp[0]), int(sp[1]))

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
    preset = actor_npc.get("preset") if actor_npc else None
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
    """Return (mes_body, npc_txids, event_txids, cutscene_txids, choice_txids). All field text (NPC
    dialogue, event messages, cutscene 'say' lines, choice prompts + replies) shares one .mes block,
    in that order (so a field with no events/cutscene/choices is byte-identical to the old layout).
    ``cutscene_txids`` is a list (one per 'say' step); ``choice_txids[c]`` = ``{"prompt": id,
    "replies": {opt_index: id}}``.

    Lines are auto-wrapped to fit the screen (FF9 doesn't wrap; see content.text) unless
    ``[dialogue] wrap = false``; a line that already fits is left byte-identical."""
    lines, tails = [], []
    npc_pos, ev_pos, cs_pos = {}, {}, []
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
    if not lines:
        return "", {}, {}, [], {}
    body, mapping = _text.build_mes(lines, start_txid=_text.DEFAULT_BASE_TXID, tails=tails)
    npc_txids = {i: mapping[p] for i, p in npc_pos.items()}
    event_txids = {j: mapping[p] for j, p in ev_pos.items()}
    cutscene_txids = [mapping[p] for p in cs_pos]
    choice_txids = {c: {"prompt": mapping[p],
                        "replies": {oi: mapping[ch_reply_pos[(cc, oi)]]
                                    for (cc, oi) in ch_reply_pos if cc == c}}
                    for c, p in ch_prompt_pos.items()}
    return body, npc_txids, event_txids, cutscene_txids, choice_txids


# --------------------------------------------------------------------------- the build

@dataclass
class FieldResult:
    dict_line: str
    battle: tuple | None = None     # (scene, music) for BattlePatch, or None
    fbg: str = ""
    warnings: list = _dc_field(default_factory=list)


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
    cutscene_wmesh = None                       # walkmesh used to auto-route cutscene walks (custom or borrow)
    if not borrow_bg:
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

    # --- dialogue + per-language script ---
    mes_body, txids, event_txids, cutscene_txids, choice_txids = collect_text(project)
    control_value = resolve_control_value(project, camera)
    for lang in langs:
        eb = build_script(project, lang, txids, control_value, event_txids=event_txids,
                          cutscene_txids=cutscene_txids, walkmesh=cutscene_wmesh,
                          choice_txids=choice_txids)
        layout.eb_path(lang, f"EVT_{project.name}.eb.bytes").write_bytes(eb)
        if mes_body:
            layout.mes_path(lang, project.text_block).write_text(mes_body, encoding="utf-8", newline="\n")

    bg_mapid = borrow_bg if borrow_bg else project.name
    dict_line = f"FieldScene {project.id} {project.area} {bg_mapid} {project.name} {project.text_block}"
    battle = None
    if "encounter" in project.raw:
        e = project.raw["encounter"]
        battle = (int(e["scene"]), int(e.get("battle_music", 0)))
    return FieldResult(dict_line=dict_line, battle=battle, fbg=fbg, warnings=warnings)


def build_mod(projects, out_root, *, mod_name="FF9CustomMap", author="", description="",
              langs=LANGS) -> dict:
    """Build one or more fields into a mod at ``out_root``; write the registration files."""
    layout = ModLayout(Path(out_root).resolve())
    results = [build_field(p, layout, langs=langs) for p in projects]

    layout.dictionary_patch.write_text(
        "\n".join(r.dict_line for r in results) + "\n", encoding="utf-8", newline="\n")

    battles = [r.battle for r in results if r.battle]
    if battles:
        lines = []
        for scene, mus in battles:
            lines.append(f"Battle: {scene}")
            lines.append(f"Music: {mus}")
        layout.battle_patch.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

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
            "warnings": [w for r in results for w in r.warnings]}
