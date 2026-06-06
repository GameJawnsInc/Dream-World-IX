"""Form specs + parsers for the editor (tk-FREE, fully testable).

Each logic section is described by a list of :class:`Field` specs (key, label, kind). The UI renders a
form generically from a spec; this module converts between the form's raw widget values and the
entity dict (:func:`build_entity` / :func:`entity_to_values`) and parses the text fields. Keeping all
parsing/normalization here (not in the Tk layer) means the tricky bits are unit-tested without a
display, exactly like the Blender ``bridge`` is bpy-free.

The contract: ``build_entity(spec, entity_to_values(spec, e)) == e`` for any entity ``e`` whose keys
are covered by ``spec`` (round-trip), proven in ``tests/test_editor_forms.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# field kinds
STR, INT, OPTINT, BOOL, PRESET, COORD, PAIR, ZONE = (
    "str", "int", "optint", "bool", "preset", "coord", "pair", "zone")

PRESETS = ["vivi", "zidane"]          # known NPC presets (combo also accepts a custom string)


@dataclass
class Field:
    key: str
    label: str
    kind: str
    help: str = ""
    default: object = None            # for BOOL: the value omitted from the file (e.g. once=True)


# --- section specs (the editor's logic vocabulary) ---------------------------------------
FIELD_SPEC = [
    Field("id", "Field ID", INT, "a unique number for your field (use >= 4000)"),
    Field("name", "Name", STR, "short tag, e.g. MY_ROOM (letters, digits, underscore)"),
    Field("area", "Area", INT, "must be >= 10 (lower areas don't render in-game)"),
    Field("text_block", "Text block", OPTINT, "leave at 1073 unless you know you need another"),
    Field("title", "Title", STR, "a human label for your own notes (optional)"),
    Field("borrow_bg", "Borrow BG", STR, "advanced: reuse a real field's art; leave blank otherwise"),
]
NPC_SPEC = [
    Field("name", "Name", STR, "a label (also links this NPC to its Blender marker)"),
    Field("preset", "Preset", PRESET, "who it looks like: vivi or zidane (the easy path)"),
    Field("model", "Model id", OPTINT, "advanced: a custom model instead of a preset"),
    Field("animset", "Animset id", OPTINT, "advanced: with a custom model (also add anims in the .toml)"),
    Field("dialogue", "Dialogue", STR, "the line shown when the player talks to it"),
    Field("pos", "Position (x, z)", COORD, "where it stands on the floor; usually placed in Blender"),
    Field("requires_flag", "Appears when flag set", OPTINT, "story gate: show only after this flag is set"),
    Field("requires_flag_clear", "Appears when flag clear", OPTINT, "show only while this flag is unset"),
]
GATEWAY_SPEC = [
    Field("name", "Name", STR, "a label (links to its Blender marker)"),
    Field("to", "To field id", INT, "the field id to send the player to"),
    Field("entrance", "Entrance", OPTINT, "which entrance to arrive at (default 0)"),
    Field("zone", "Zone (x z; x z; ...)", ZONE, "the trigger quad; usually placed in Blender"),
    Field("requires_flag", "Opens when flag set", OPTINT, "only usable once this flag is set"),
    Field("requires_flag_clear", "Opens when flag clear", OPTINT, "only usable while this flag is unset"),
]
EVENT_SPEC = [
    Field("name", "Name", STR, "a label (links to its Blender marker)"),
    Field("message", "Message", STR, "text shown when the player steps in"),
    Field("give_item", "Give item (id, count)", PAIR, "e.g. 232, 1"),
    Field("gil", "Gil", OPTINT, "gil to award"),
    Field("set_flag", "Set flag (idx, val)", PAIR, "raise a story flag, e.g. 8000, 1"),
    Field("once", "Fire once", BOOL, "off = fires every step you stand in it", default=True),
    Field("zone", "Zone (x z; x z; ...)", ZONE, "the trigger quad; usually placed in Blender"),
    Field("requires_flag", "Fires when flag set", OPTINT, "only fires after this flag is set"),
    Field("requires_flag_clear", "Fires when flag clear", OPTINT, "only fires while this flag is unset"),
]
ENCOUNTER_SPEC = [
    Field("scene", "Battle scene id", INT, "e.g. 67 = Evil Forest"),
    Field("freq", "Frequency (0-255)", OPTINT, "default 255"),
    Field("battle_music", "Battle music id", OPTINT, "default 0 = battle theme"),
]
MUSIC_SPEC = [
    Field("song", "Field BGM song id", INT, "e.g. 9 = Vivi's Theme"),
]
CUTSCENE_SPEC = [
    Field("actor", "Actor NPC", STR, "an [[npc]] name; blank = narration"),
    Field("once", "Play once", BOOL, "off = replays every visit", default=True),
    Field("warmup", "Warmup frames", OPTINT, "default 30 (let the field settle)"),
]

# cutscene steps: each is a dict with exactly one action key.
STEP_KIND = {
    "say": STR, "wait": INT, "set_flag": PAIR,                    # any cutscene
    "walk": COORD, "teleport": COORD, "animation": INT, "turn": INT, "face_player": BOOL,  # actor only
}
STEP_LABEL = {
    "say": "Say (dialogue)", "wait": "Wait (frames)", "set_flag": "Set flag (idx, val)",
    "walk": "Walk to (x, z)", "teleport": "Teleport to (x, z)", "animation": "Play animation (id)",
    "turn": "Turn (angle 0-255)", "face_player": "Face the player",
}
GLOBAL_STEPS = ("say", "wait", "set_flag")
ACTOR_STEPS = ("walk", "teleport", "animation", "turn", "face_player")


# --- parsers (raise ValueError with a clear message on bad input) -------------------------
def _ints(s, n, what):
    parts = [p for p in re.split(r"[ ,]+", str(s).strip()) if p != ""]
    if len(parts) != n:
        raise ValueError(f"{what}: expected {n} number(s), got {len(parts)}")
    try:
        return [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"{what}: must be whole numbers, got {s!r}")


def _str(s):
    return "" if s is None else str(s)


def parse_optint(s):
    s = _str(s).strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        raise ValueError(f"expected a whole number, got {s!r}")


def parse_coord(s):
    return None if _str(s).strip() == "" else _ints(s, 2, "position")


def parse_pair(s):
    return None if _str(s).strip() == "" else _ints(s, 2, "pair")


def parse_zone(s):
    s = _str(s).strip()
    if s == "":
        return None
    chunks = [c for c in re.split(r"[;\n]+", s) if c.strip()]
    out = [_ints(c, 2, "zone point") for c in chunks]
    if len(out) not in (4, 5):
        raise ValueError(f"zone needs 4 or 5 points (got {len(out)})")
    return out


def format_pair(v):
    return ", ".join(str(int(x)) for x in v)


def format_zone(v):
    return "; ".join(f"{int(x)} {int(z)}" for (x, z) in v)


def _parse_field(kind, raw):
    """Parse one widget value to its TOML value (or None to omit). Raises ValueError on bad input."""
    if kind in (STR, PRESET):
        s = _str(raw).strip()
        return s or None
    if kind == INT:
        s = _str(raw).strip()
        if s == "":
            return None
        try:
            return int(s)
        except ValueError:
            raise ValueError(f"expected a whole number, got {s!r}")
    if kind == OPTINT:
        return parse_optint(raw)
    if kind == COORD:
        return parse_coord(raw)
    if kind == PAIR:
        return parse_pair(raw)
    if kind == ZONE:
        return parse_zone(raw)
    raise ValueError(f"unknown field kind {kind!r}")


# --- entity <-> form values --------------------------------------------------------------
def build_entity(spec, values: dict) -> dict:
    """Build an entity dict from raw form values (omit empty optionals; coerce types). A BOOL equal to
    its spec default is omitted (so e.g. ``once=true`` isn't written; ``once=false`` is)."""
    out = {}
    for f in spec:
        if f.kind == BOOL:
            b = bool(values.get(f.key, f.default))     # a missing bool means its default
            if b != f.default:
                out[f.key] = b
            continue
        v = _parse_field(f.kind, values.get(f.key, ""))
        if v is not None:
            out[f.key] = v
    return out


def entity_to_values(spec, entity: dict) -> dict:
    """Flat widget values for a form from an entity dict (missing keys -> '' / the BOOL default)."""
    vals = {}
    for f in spec:
        if f.key not in entity:
            vals[f.key] = f.default if f.kind == BOOL else ""
            continue
        v = entity[f.key]
        if f.kind == BOOL:
            vals[f.key] = bool(v)
        elif f.kind in (COORD, PAIR):
            vals[f.key] = format_pair(v)
        elif f.kind == ZONE:
            vals[f.key] = format_zone(v)
        else:
            vals[f.key] = str(v)
    return vals


# --- cutscene steps ----------------------------------------------------------------------
def make_step(key: str, raw) -> dict:
    """One cutscene step dict from a step type + a raw value (face_player ignores the value)."""
    if key not in STEP_KIND:
        raise ValueError(f"unknown step {key!r}")
    if key == "face_player":
        return {"face_player": True}
    v = _parse_field(STEP_KIND[key], raw)
    if v is None:
        raise ValueError(f"step '{key}' needs a value")
    return {key: v}


def step_key(step: dict) -> str:
    """The single action key of a step (the first recognized one)."""
    for k in step:
        if k in STEP_KIND:
            return k
    return next(iter(step), "")


def step_value_text(step: dict) -> str:
    """The step's value as editable text ('' for face_player)."""
    k = step_key(step)
    if not k or k == "face_player":
        return ""
    v = step[k]
    if STEP_KIND[k] in (COORD, PAIR):
        return format_pair(v)
    return str(v)


def step_summary(step: dict) -> str:
    """A one-line summary for the step list, e.g. ``say: "hello"`` or ``walk: 0, -800``."""
    k = step_key(step)
    if not k:
        return "(empty)"
    if k == "face_player":
        return "face_player"
    return f"{k}: {step_value_text(step)}"
