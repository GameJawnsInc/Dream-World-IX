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

from .. import archetypes as _archetypes

# field kinds
STR, INT, OPTINT, BOOL, PRESET, COORD, PAIR, ZONE, ITEMCOUNT, FLAGREF, FLAGPAIR, STRLIST = (
    "str", "int", "optint", "bool", "preset", "coord", "pair", "zone", "itemcount", "flagref", "flagpair",
    "strlist")
# [startup] kinds: a scenario beat (number or area name), and the two list-of-table levers it carries
SCENARIOREF, FLAGDICTLIST, BYTEDICTLIST = "scenarioref", "flagdictlist", "bytedictlist"
FLOAT = "float"        # an OPTIONAL float (e.g. battle camera tweak offsets); empty -> None, like OPTINT
# cutscene-step kinds: a movement target (a name OR "x, z"), a route (list of those), a gesture (name OR id)
POINT, PATH, ANIM = "point", "path", "anim"

PRESETS = _archetypes.names()         # built-in archetype names for the combo (also accepts a custom string)


@dataclass
class Field:
    key: str
    label: str
    kind: str
    help: str = ""
    default: object = None            # for BOOL: the value omitted from the file (e.g. once=True)
    catalog: str = None               # comma-separated Info Hub kinds -> render a "Browse..." picker button


# --- section specs (the editor's logic vocabulary) ---------------------------------------
FIELD_SPEC = [
    Field("id", "Field ID", INT, "a unique number for your field (use >= 4000)"),
    Field("name", "Name", STR, "short tag, e.g. MY_ROOM (letters, digits, underscore)"),
    Field("area", "Area", INT, "must be >= 10 (lower areas don't render in-game)"),
    Field("text_block", "Text block", OPTINT, "leave at 1073 unless you know you need another"),
    Field("title", "Title", STR, "a human label for your own notes (optional)"),
    Field("location", "Location", STR, 'the in-game menu place-name (the "LOCATION" card), e.g. "Pimp House"; '
                                       "blank = a fork inherits its donor's, a new field shows none"),
    Field("borrow_bg", "Borrow BG", STR, "advanced: reuse a real field's art; leave blank otherwise"),
]
NPC_SPEC = [
    Field("name", "Name", STR, "a label (also links this NPC to its Blender marker)"),
    Field("preset", "Preset", PRESET, "who it looks like (any archetype/creature)",
          catalog="archetype,creature"),
    Field("model", "Model id", OPTINT, "advanced: a custom model instead of a preset"),
    Field("animset", "Animset id", OPTINT, "advanced: with a custom model (also add anims in the .toml)"),
    Field("dialogue", "Dialogue", STR, "the line shown when the player talks to it"),
    Field("speaker", "Speaker name", STR, "optional name before the line, e.g. Vivi (or [VIVI] for a renameable party name)"),
    Field("tail", "Window tail", STR, "dialogue pointer corner: UPR/UPL/LOR/LOL/UPC/LOC (default UPR)"),
    Field("pos", "Position (x, z)", COORD, "where it stands on the floor; usually placed in Blender"),
    Field("requires_flag", "Appears when flag set", FLAGREF,
          "story gate: show only after this flag (name or index) is set", catalog="flag"),
    Field("requires_flag_clear", "Appears when flag clear", FLAGREF,
          "show only while this flag (name or index) is unset", catalog="flag"),
]
GATEWAY_SPEC = [
    Field("name", "Name", STR, "a label (links to its Blender marker)"),
    Field("to", "To field id", INT, "the field id to send the player to"),
    Field("entrance", "Entrance", OPTINT, "which entrance to arrive at (default 0)"),
    Field("zone", "Zone (x z; x z; ...)", ZONE, "the trigger quad; usually placed in Blender"),
    Field("requires_flag", "Opens when flag set", FLAGREF, "only usable once this flag (name/idx) is set",
          catalog="flag"),
    Field("requires_flag_clear", "Opens when flag clear", FLAGREF, "only usable while this flag is unset",
          catalog="flag"),
]
EVENT_SPEC = [
    Field("name", "Name", STR, "a label (links to its Blender marker)"),
    Field("message", "Message", STR, "text shown when the player steps in"),
    Field("speaker", "Speaker name", STR, "optional name before the message (blank for an unsigned popup)"),
    Field("tail", "Window tail", STR, "dialogue pointer corner: UPR/UPL/LOR/LOL/UPC/LOC (default UPR)"),
    Field("give_item", "Give item (id, count)", PAIR, "e.g. 232, 1"),
    Field("received", "Item-get window", BOOL, "give_item: show the canonical 'Received <item>!' window",
          default=False),
    Field("require_space", "Skip if bag full", BOOL, "give_item: chest-style -- don't fire if you can't carry it",
          default=False),
    Field("gil", "Gil", OPTINT, "gil to award"),
    Field("set_flag", "Set flag (name/idx, val)", FLAGPAIR, "raise a story flag, e.g. boss_dead, 1 (name or index)"),
    Field("once", "Fire once", BOOL, "off = fires every step you stand in it", default=True),
    Field("zone", "Zone (x z; x z; ...)", ZONE, "the trigger quad; usually placed in Blender"),
    Field("requires_flag", "Fires when flag set", FLAGREF, "only fires after this flag (name/idx) is set",
          catalog="flag"),
    Field("requires_flag_clear", "Fires when flag clear", FLAGREF, "only fires while this flag is unset",
          catalog="flag"),
]
ENCOUNTER_SPEC = [
    Field("scene", "Battle scene id", OPTINT, "e.g. 67 = Evil Forest; blank = no random battles",
          catalog="scene"),
    Field("freq", "Frequency (0-255)", OPTINT, "default 255"),
    Field("battle_music", "Battle music id", OPTINT, "default 0 = battle theme"),
]
MUSIC_SPEC = [
    Field("song", "Field BGM song id", OPTINT, "e.g. 9 = Vivi's Theme; blank = no field music"),
]
PARTY_SPEC = [
    Field("add", "Add members", STRLIST,
          "playable characters to ADD to the party at field load (names or 0-11), e.g. Steiner, Beatrix"),
    Field("remove", "Remove members", STRLIST,
          "playable characters to REMOVE at field load, e.g. Eiko"),
]
STARTUP_SPEC = [
    Field("scenario", "Scenario beat", SCENARIOREF,
          "assert the story beat this field stands for: a number (0-32767) or an area name (e.g. dali)"),
    Field("flags", "Set story flags", FLAGDICTLIST,
          'story bits to assert at load: "name, 1; other, 0" (name or index; value 0 or 1)'),
    Field("words", "Word writes (advanced)", BYTEDICTLIST,
          'save-backed 16-bit writes "byte, value; ...", e.g. the ATE mask 236, 65280 (rarely needed)'),
    Field("bytes", "Byte writes (advanced)", BYTEDICTLIST,
          'save-backed single-byte writes "byte, value; ...", e.g. 361, 4 (rarely needed)'),
]
CUTSCENE_SPEC = [
    Field("actor", "Actor NPC", STR, "an [[npc]] name; blank = narration"),
    Field("once", "Play once", BOOL, "off = replays every visit", default=True),
    Field("warmup", "Warmup frames", OPTINT, "default 30 (let the field settle)"),
]
MARKER_SPEC = [
    Field("name", "Name", STR, "a label; reference it in a cutscene as walk = \"<name>\""),
    Field("pos", "Position (x, z)", COORD, "where it sits on the floor; or place it in Blender"),
]
FLAG_SPEC = [
    Field("name", "Name", STR, "the story-flag name you reference in events / gateways / choices "
          "(set_flag, show-while-unset, …)"),
    Field("index", "gEventGlobal bit", INT, "a save-persistent bit in the custom band [8512, 16320); "
          "Story State labels a set bit with this name"),
]
CHOICE_SPEC = [
    Field("npc", "NPC", STR, "talk-triggered: the [[npc]] name (set npc OR zone, not both)"),
    Field("zone", "Zone (x z; x z; ...)", ZONE, "zone trigger: 4 corners (a lever); or place in Blender"),
    Field("trigger", "Trigger (zone)", STR, "blank = action (press to use, re-usable); 'walk' = auto-pop"),
    Field("once", "Fires once ever", BOOL, "walk-trigger only: on = once ever; off = once per visit", default=True),
    Field("prompt", "Prompt", STR, "the question shown above the options"),
    Field("speaker", "Speaker name", STR, "optional name before the prompt"),
    Field("tail", "Window tail", STR, "UPR/UPL/LOR/LOL/UPC/LOC (default UPR)"),
    Field("default", "Default row", OPTINT, "option index highlighted first (0 = top; default 0)"),
    Field("cancel", "Cancel row", OPTINT, "option index B/Cancel picks (-1 or blank = last row)"),
]
CHOICE_OPTION_SPEC = [
    Field("text", "Option text", STR, "the menu row the player selects (keep it short)"),
    Field("disabled", "Hidden", BOOL, "on = always removed from the menu (cursor can't reach it)",
          default=False),
    Field("requires_flag", "Show if flag set", FLAGREF, "hide this row UNTIL this flag (name/idx) is set",
          catalog="flag"),
    Field("requires_flag_clear", "Show if flag clear", FLAGREF, "hide this row ONCE this flag is set",
          catalog="flag"),
    Field("reply", "Reply", STR, "optional line shown after choosing this option"),
    Field("give_item", "Give item", ITEMCOUNT, 'item + count, e.g. "Potion, 1" (name or id)',
          catalog="item"),
    Field("gil", "Gil", OPTINT, "gil; NEGATIVE charges the player (e.g. -100)"),
    Field("set_flag", "Set flag (name/idx, val)", FLAGPAIR, "raise a story flag, e.g. boss_dead, 1"),
]
DIALOGUE_SPEC = [
    Field("wrap", "Auto-wrap width", OPTINT, "max chars per line (default 28); set 0 to turn wrapping off"),
]

# one-line purpose for each section, shown at the top of its form (the "what is this" cue).
SECTION_HELP = {
    "field": "The field's identity: a unique id (>= 4000), a short name, and the area (>= 10).",
    "camera": "Camera / walkmesh / layers / positions are SPATIAL -- author them in Blender. Read-only here.",
    "dialogue": "Text options. Auto-wrap breaks long dialogue lines to fit the screen (FF9 won't).",
    "encounter": "Random battles on this field (battle scene id + frequency + battle music).",
    "music": "The field's background music (a song id, e.g. 9 = Vivi's Theme).",
    "party": "Who's in the party (menu + battle) on this field -- add/remove playable characters at load. "
             "Separate from who you WALK as (an Import option).",
    "startup": "Assert the story beat this field boots in (a forked field starts at scenario zero): set the "
               "scenario and any story flags, unconditionally, at field load.",
    "cutscene": "A scripted scene. Steps run in order with control locked; an 'actor' NPC can walk/emote.",
    "npc": "People who stand in the room: a model (preset), a line of dialogue, optional story gate.",
    "gateway": "An exit zone -> another field (the door the player walks into).",
    "event": "A walk-in trigger: show a message, give an item/gil, or set a story flag.",
    "marker": "Named points on the floor. A cutscene walk/path can reach them by name (no coords).",
    "choice": "Talk to an NPC -> a menu -> branch. Each option can reply, give item/gil, set a flag.",
}

# cutscene steps: each is a dict with exactly one action key.
STEP_KIND = {
    "say": STR, "wait": INT, "set_flag": PAIR,                    # any cutscene
    "walk": POINT, "path": PATH, "teleport": POINT,              # actor only (movement)
    "animation": ANIM, "turn": INT, "face_player": BOOL,        # actor only (anim/facing)
}
STEP_LABEL = {
    "say": "Say (dialogue)", "wait": "Wait (frames)", "set_flag": "Set flag (idx, val)",
    "walk": "Walk to", "path": "Walk a route", "teleport": "Teleport to",
    "animation": "Play animation", "turn": "Turn (angle 0-255)", "face_player": "Face the player",
}
# live hint shown for the selected step type (what to type in the Value box).
STEP_HELP = {
    "say": "dialogue text shown in a window",
    "wait": "frames to pause (30 ≈ 1 second)",
    "set_flag": "story flag as \"index, value\" -- e.g. 8000, 1",
    "walk": "a marker name, @player, or \"x, z\" (auto-routes around obstacles)",
    "path": "a route through waypoints: \"a; b; c\" (names or x z)",
    "teleport": "instantly move to a marker / @player / \"x, z\"",
    "animation": "a gesture name (e.g. glad, angry, nod) or a numeric id",
    "turn": "face an angle 0-255 (0=south, 64=west, 128=north, 192=east)",
    "face_player": "(no value) turn to face the player",
}
GLOBAL_STEPS = ("say", "wait", "set_flag")
ACTOR_STEPS = ("walk", "path", "teleport", "animation", "turn", "face_player")


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


def parse_optfloat(s):
    s = _str(s).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"expected a number, got {s!r}")


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


def parse_itemcount(s):
    """give_item: ``"item, count"`` -> ``[item, count]``. ``item`` is an int when numeric, else a name
    string ("Potion", "236", "Phoenix Down, 3" all work -- split on the FIRST comma so item names may
    contain spaces). ``count`` defaults to 1. Empty -> None."""
    s = _str(s).strip()
    if s == "":
        return None
    item, _, cnt = s.partition(",")
    item = item.strip()
    if item == "":
        raise ValueError("give item: needs an item name or id")
    item_v = int(item) if item.lstrip("-").isdigit() else item
    cnt = cnt.strip()
    try:
        count = int(cnt) if cnt else 1
    except ValueError:
        raise ValueError(f"give item: count must be a whole number, got {cnt!r}")
    return [item_v, count]


def format_itemcount(v):
    return "" if not v else f"{v[0]}, {int(v[1]) if len(v) > 1 else 1}"


def parse_flagref(s):
    """A story-flag gate: a numeric index -> int, a [[flag]] NAME -> the name string, empty -> None.
    Names resolve to indices at build time (flags.resolve_project_flags)."""
    s = _str(s).strip()
    if s == "":
        return None
    return int(s) if s.lstrip("-").isdigit() else s


def parse_flagpair(s):
    """set_flag: ``"flag, value"`` -> ``[flag, value]``. ``flag`` is an int index OR a [[flag]] NAME; the
    value defaults to 1. Empty -> None. Mirrors give_item so a name + value author the same way."""
    s = _str(s).strip()
    if s == "":
        return None
    flag, _, val = s.partition(",")
    flag = flag.strip()
    if flag == "":
        raise ValueError("set flag: needs a flag name or index")
    flag_v = int(flag) if flag.lstrip("-").isdigit() else flag
    val = val.strip()
    try:
        value = int(val) if val else 1
    except ValueError:
        raise ValueError(f"set flag: value must be a whole number, got {val!r}")
    return [flag_v, value]


def format_flagpair(v):
    return "" if not v else f"{v[0]}, {int(v[1]) if len(v) > 1 else 1}"


def parse_strlist(s):
    """A comma/space-separated list of names or ids -> a list (a numeric token -> int, else the name
    string); empty -> None. Round-trips with :func:`format_strlist`. Used by ``[party]`` add/remove --
    each token is a character name or a 0..11 CharacterOldIndex (resolved at build, like FLAGREF)."""
    s = _str(s).strip()
    if s == "":
        return None
    toks = [t for t in re.split(r"[,\s]+", s) if t]
    if not toks:
        return None
    return [int(t) if t.lstrip("-").isdigit() else t for t in toks]


def format_strlist(v):
    # a STRLIST is normally a list, but a hand-authored TOML may give a scalar (a bare name, or a raw-int
    # escape hatch like `flags = 9`) -- show it as-is instead of iterating it (which would split a string into
    # chars / TypeError on an int).
    if not isinstance(v, (list, tuple)):
        return str(v)
    return ", ".join(str(x) for x in v)


def parse_flagdictlist(s):
    """[startup] flags: semicolon/newline rows, each ``"flag, value"`` -> a list of ``{flag, value}`` dicts
    (flag = int index or a [[flag]] NAME; value defaults to 1). Empty -> None. Round-trips with
    :func:`format_flagdictlist`; reuses :func:`parse_flagpair` per row so a bare name means value 1."""
    s = _str(s).strip()
    if s == "":
        return None
    out = []
    for row in re.split(r"[;\n]+", s):
        if not row.strip():
            continue
        pair = parse_flagpair(row)                  # "flag, value" -> [flag, value] (name or idx; default 1)
        out.append({"flag": pair[0], "value": pair[1]})
    return out or None


def format_flagdictlist(v):
    return "; ".join(f"{d['flag']}, {int(d.get('value', 1))}" for d in v)


def parse_bytedictlist(s):
    """[startup] words/bytes: semicolon/newline rows, each ``"byte, value"`` -> a list of ``{byte, value}``
    dicts (both whole numbers). Empty -> None. Round-trips with :func:`format_bytedictlist`."""
    s = _str(s).strip()
    if s == "":
        return None
    out = []
    for row in re.split(r"[;\n]+", s):
        if not row.strip():
            continue
        nums = _ints(row, 2, "byte write")          # "byte, value" -> [byte, value]
        out.append({"byte": nums[0], "value": nums[1]})
    return out or None


def format_bytedictlist(v):
    return "; ".join(f"{int(d['byte'])}, {int(d['value'])}" for d in v)


def _is_int(s):
    return bool(re.fullmatch(r"-?\d+", str(s).strip()))


def _format_point(v):
    """A movement point: ``[x, z]`` -> "x, z"; a name string -> itself."""
    return format_pair(v) if isinstance(v, (list, tuple)) else _str(v)


def parse_point(raw):
    """A movement target: "x, z" -> [x, z], or any other text -> a marker / @player / @npc name."""
    s = _str(raw).strip()
    if s == "":
        raise ValueError("needs a marker name or \"x, z\"")
    parts = [p for p in re.split(r"[ ,]+", s) if p]
    if len(parts) == 2 and _is_int(parts[0]) and _is_int(parts[1]):
        return [int(parts[0]), int(parts[1])]
    return s


def parse_path(raw):
    """A route: "a; b; c" (or newlines) -> a list of points (each a name or [x, z])."""
    chunks = [c.strip() for c in re.split(r"[;\n]+", _str(raw)) if c.strip()]
    if not chunks:
        raise ValueError("a route needs at least one waypoint, e.g. \"a; b; c\"")
    return [parse_point(c) for c in chunks]


def parse_anim(raw):
    """A gesture: a numeric id -> int, or a name (e.g. "glad") -> the name string."""
    s = _str(raw).strip()
    if s == "":
        raise ValueError("needs a gesture name or id")
    return int(s) if _is_int(s) else s


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
    if kind == FLOAT:
        return parse_optfloat(raw)
    if kind == COORD:
        return parse_coord(raw)
    if kind == PAIR:
        return parse_pair(raw)
    if kind == ZONE:
        return parse_zone(raw)
    if kind == ITEMCOUNT:
        return parse_itemcount(raw)
    if kind == FLAGREF:
        return parse_flagref(raw)
    if kind == FLAGPAIR:
        return parse_flagpair(raw)
    if kind == STRLIST:
        return parse_strlist(raw)
    if kind == SCENARIOREF:
        return parse_flagref(raw)                   # a beat number -> int, an area name -> str (resolved at build)
    if kind == FLAGDICTLIST:
        return parse_flagdictlist(raw)
    if kind == BYTEDICTLIST:
        return parse_bytedictlist(raw)
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
        if v is None and f.kind == INT:                # INT is the REQUIRED int kind (OPTINT is the optional one):
            raise ValueError(f"{f.label or f.key}: a whole number is required")   # a blank one is an error, not a
        if v is not None:                              # silent drop (the GUI callers surface this as 'fix the field')
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
        elif f.kind == ITEMCOUNT:
            vals[f.key] = format_itemcount(v)
        elif f.kind == FLAGPAIR:
            vals[f.key] = format_flagpair(v)
        elif f.kind == STRLIST:
            vals[f.key] = format_strlist(v)
        elif f.kind == FLAGDICTLIST:
            vals[f.key] = format_flagdictlist(v)
        elif f.kind == BYTEDICTLIST:
            vals[f.key] = format_bytedictlist(v)
        else:
            vals[f.key] = str(v)              # FLAGREF/SCENARIOREF (int or name), STR, INT, OPTINT, PRESET
    return vals


# --- cutscene steps ----------------------------------------------------------------------
def make_step(key: str, raw) -> dict:
    """One cutscene step dict from a step type + a raw value (face_player ignores the value)."""
    if key not in STEP_KIND:
        raise ValueError(f"unknown step {key!r}")
    kind = STEP_KIND[key]
    if kind == BOOL:                       # face_player
        return {key: True}
    if kind == POINT:
        return {key: parse_point(raw)}
    if kind == PATH:
        return {key: parse_path(raw)}
    if kind == ANIM:
        return {key: parse_anim(raw)}
    v = _parse_field(kind, raw)
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
    kind = STEP_KIND.get(k)
    if not k or kind == BOOL:
        return ""
    v = step[k]
    if kind in (COORD, PAIR):
        return format_pair(v)
    if kind == POINT:
        return _format_point(v)
    if kind == PATH:
        return "; ".join(_format_point(p) for p in v)
    if isinstance(v, list):                 # any other list value -- show, don't crash
        return ", ".join(str(p) for p in v)
    return str(v)


def step_summary(step: dict) -> str:
    """A one-line summary for the step list, e.g. ``say: "hello"`` or ``walk: 0, -800``."""
    k = step_key(step)
    if not k:
        return "(empty)"
    if k == "face_player":
        return "face_player"
    return f"{k}: {step_value_text(step)}"


# --- choices (npc + prompt + a list of options) ------------------------------------------
def choice_summary(ch: dict) -> str:
    """One-line label for the choice tree, e.g. ``Vivi: What'll it be? (3)`` or ``zone: Pull? (2)``."""
    who = ch.get("npc") or ("zone" if "zone" in ch else "?")
    q = (ch.get("prompt") or "").strip()
    n = len(ch.get("options", []))
    return f"{who}: {q[:28]}{'...' if len(q) > 28 else ''} ({n})"


def option_summary(o: dict) -> str:
    """One-line label for an option row, e.g. ``Yes  [reply, item, -100g, flag 8001]``."""
    txt = o.get("text") or "(no text)"
    tags = []
    if o.get("reply"):
        tags.append("reply")
    if o.get("give_item"):
        tags.append("item")
    if o.get("gil") is not None:
        tags.append(f"{int(o['gil']):+}g")
    if o.get("set_flag"):
        tags.append(f"flag {o['set_flag'][0]}")
    return txt + (f"  [{', '.join(tags)}]" if tags else "")
