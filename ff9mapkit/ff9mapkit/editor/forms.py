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
ARRIVALLIST = "arrivallist"   # [[player.arrival]] rows: "entrance, x, z[, face]" per row (the dict-list idiom)
FLOAT = "float"        # an OPTIONAL float (e.g. battle camera tweak offsets); empty -> None, like OPTINT
# CATINT -- an Info Hub reference the BUILD resolves to a numeric id: a number -> int, a catalog NAME -> the
# name string (kept verbatim in the .toml, exactly like FLAGREF/SCENARIOREF). Its Browse picker still fills
# the ID (:func:`wants_id`), because a picker LABEL is not always a resolvable identifier -- the warm
# 'encounter' kind lists "Goblin, Fang -- Evil Forest (field 250, random)". Use it wherever the build calls a
# catalog resolver (build.resolve_encounter_scenes, build.resolve_npc_model) instead of a bare int().
CATINT = "catint"
# cutscene-step kinds: a movement target (a name OR "x, z"), a route (list of those), a gesture (name OR id)
POINT, PATH, ANIM = "point", "path", "anim"
# ANIMSET -- the five movement slots of an [[npc]] as ONE text field: "stand=560, walk=571" <-> {slot: id}.
# The only DICT-valued form kind: every other kind is a scalar or a list, and str()-ing a dict through
# entity_to_values wrote `{'stand': 560}` into the widget and back out as a parse error.
ANIMSET = "animset"
# the slots the field engine drives (content.npc.ANIM_ORDER), spelled where the form layer can see them
# without importing the .eb writer.
ANIM_SLOTS = ("stand", "walk", "run", "left", "right")
# Catalog kinds whose picker is a WORKSPACE dialog (a rendered clip preview), not the Info Hub index.
# The tk editor has no such dialog, so its form renders NO Browse for them -- a button whose picker
# cannot answer is a dead control, and the round-6 census counted six of those.
GUI_ONLY_CATALOGS = frozenset({"anim", "animset"})

PRESETS = _archetypes.names()         # built-in archetype names for the combo (also accepts a custom string)


@dataclass
class Field:
    key: str
    label: str
    kind: str
    help: str = ""
    default: object = None            # for BOOL: the value omitted from the file (e.g. once=True)
    catalog: str = None               # comma-separated Info Hub kinds -> render a "Browse..." picker button
    placeholder: str = None           # override the generated line-edit placeholder (:func:`placeholder_for`)
                                      # -- for a catalog whose FIRST kind's labels aren't typeable identifiers
    file: str = None                  # a QFileDialog name-filter (e.g. "Audio (*.wav *.mp3)") -> the Qt
                                      # editor renders a Browse-for-file button; the tk editor shows a
                                      # plain entry (value stays an ordinary STR either way)
    concept: str = None               # a workspace.concepts term -> the Qt form renders a "?" badge on the
                                      # label that opens the plain-language concept card (Phase 5 learnability)
    advanced: bool = False            # an expert field -> the Guided beginner mode tucks it into a per-form
                                      # 'Advanced options' drawer (Phase 7). Fields whose help starts with
                                      # "advanced" are auto-detected too; this flags the rest (e.g. the mesID).


# --- section specs (the editor's logic vocabulary) ---------------------------------------
# One shared explanation of the speech-bubble pointer codes -- reused across the NPC / EVENT / CHEST / CHOICE
# specs so the gloss reads identically everywhere (each spec appends its own default).
_TAIL_HELP = ("speech-bubble pointer corner — UP/LO = upper/lower, R/L/C = right/left/center "
              "(e.g. UPR = upper-right)")

FIELD_SPEC = [
    Field("id", "Field ID", INT, "a unique number for your field (use >= 4000)"),
    Field("name", "Name", STR, "short tag, e.g. MY_ROOM (letters, digits, underscore)"),
    Field("area", "Area", INT, "must be >= 10 (lower areas don't render in-game)"),
    Field("text_block", "Text block", OPTINT, "leave EMPTY to derive it from the field id (auto-registered); set it only to share dialogue or to carry a fork donor's block", concept="mes",
          advanced=True),
    Field("title", "Title", STR, "a human label for your own notes (optional)"),
    Field("location", "Location", STR, 'the in-game menu place-name (the "LOCATION" card), e.g. "Mog\'s Hut"; '
                                       "blank = a fork inherits its donor's, a new field shows none"),
    Field("borrow_bg", "Borrow BG", STR, "advanced: reuse a real field's art; leave blank otherwise",
          concept="bg-borrow"),
]
NPC_SPEC = [
    Field("name", "Name", STR, "a label (also links this NPC to its Blender marker)"),
    Field("preset", "Preset", PRESET, "who it looks like (any archetype/creature)",
          catalog="archetype,creature"),
    Field("model", "Model", CATINT, "advanced: a custom model instead of a preset — an id or an exact GEO "
          "name", catalog="model"),
    Field("animset", "Animset id", OPTINT, "advanced: with a custom model (also add anims in the .toml)"),
    Field("anims", "Movement clips", ANIMSET,
          "advanced: pin the five movement clips this NPC plays — Browse previews the model's own clips; "
          "blank = resolved from the model/preset",
          catalog="animset", advanced=True, placeholder="stand=560, walk=571"),
    Field("dialogue", "Dialogue", STR, "the line shown when the player talks to it"),
    Field("speaker", "Speaker name", STR, "optional name before the line, e.g. Vivi (or [VIVI] for a renameable party name)"),
    Field("tail", "Window tail", STR, _TAIL_HELP + ". Default UPR."),
    Field("pos", "Position (x, z)", COORD, "where it stands on the floor; usually placed in Blender"),
    Field("face", "Facing (0-255)", OPTINT,
          "which way it stands: 0=south (toward the camera), 64=west, 128=north, 192=east"),
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
    Field("tail", "Window tail", STR, _TAIL_HELP + ". Default UPR."),
    Field("give_item", "Give item (id, count)", PAIR, "e.g. 232, 1"),
    Field("received", "Item-get window", BOOL, "for Give item: show the real centered 'Received <item>!' box "
          "(needs no message; with one, your text fills the box and you own its codes)",
          default=False),
    Field("require_space", "Skip if bag full", BOOL, "for Give item: chest-style — don't fire if you can't carry it",
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
CHEST_SPEC = [
    Field("pos", "Position (x, z)", COORD, "where the chest sits on the floor; usually placed in Blender"),
    Field("model", "Chest model", STR, "leave blank for the default wooden chest. Advanced: F0 / F1 (two chest "
          "looks), or a raw model id (e.g. 75 / 91 / 701 / 702)"),
    Field("item", "Reward item (id/name, count)", ITEMCOUNT, 'the treasure, e.g. "Potion, 1" (set item OR gil)',
          catalog="item"),
    Field("gil", "Reward gil", OPTINT, "give gil instead of an item (set item OR gil)"),
    Field("flag", "Opened-flag", FLAGREF, "REQUIRED save bit that marks it looted (stays open across saves) -- a [[flag]] name (recommended) or a safe-band index >= 8712.", catalog="flag"),
    Field("requires_flag", "Appears when flag set", FLAGREF,
          "story gate: the chest only appears after this flag (name or index) is set", catalog="flag"),
    Field("requires_flag_clear", "Appears when flag clear", FLAGREF,
          "the chest only appears while this flag (name or index) is unset", catalog="flag"),
    Field("face", "Facing (0-255)", OPTINT, "rotate the chest model (0=south, 64=west, 128=north, 192=east)"),
    Field("message", "Custom box text", STR, "advanced: replace the 'Received <item>!' box (you own the "
          "[WDTH]/codes); blank = the real FF9 box"),
    Field("box", "Box size (width, lines)", PAIR, "advanced: centers a custom message, e.g. 69, 3"),
    Field("tail", "Window tail", STR, _TAIL_HELP + ". Default DEFT (the centered system box)."),
]
PROP_SPEC = [
    # [[prop]] -- static set-dressing (docs/FORMAT.md): NOT a character, so no dialogue/turn-to-player keys.
    Field("name", "Name", STR, "a label (shows in the tree; optional)"),
    Field("prop", "Prop", STR, "a built-in prop archetype — chest, tent, save_book, barrel, lever, … "
          "(model + its canonical resting pose)", catalog="prop"),
    Field("model", "Model", STR, "advanced: a prop model id or exact GEO name instead of an archetype",
          catalog="model"),
    Field("pose", "Pose", STR, "advanced: a static pose — an action name or a raw clip id; blank = the "
          "archetype's resting pose", catalog="anim"),
    Field("pos", "Position (x, z)", COORD, "where it sits on the floor (on the walkmesh)"),
    Field("face", "Facing (0-255)", OPTINT, "rotate it (0=south, 64=west, 128=north, 192=east)"),
    Field("collision", "Solid (blocks walking)", BOOL, "off = a walk-through prop (floor markers, dense "
          "scenery)", default=True),
    Field("requires_flag", "Appears when flag set", FLAGREF,
          "story gate: show only after this flag (name or index) is set", catalog="flag"),
    Field("requires_flag_clear", "Appears when flag clear", FLAGREF,
          "show only while this flag (name or index) is unset", catalog="flag"),
    Field("attach_to", "Attach to NPC", STR, "advanced: an [[npc]] name — the prop binds to that NPC's "
          "bone and follows it (a held item)", advanced=True),
    Field("bone", "Attachment bone", OPTINT, "advanced: with Attach to — the bone index (default 11, the "
          "right hand)", advanced=True),
]
SPS_SPEC = [
    Field("id", "Effect ID", INT, "a unique number for this effect (use >= 5000; must not clash with a "
          "carried donor effect)"),
    Field("template", "Template", STR, 'a named preset -- fire / bonfire / smoke / sparkle / embers / glimmer '
          '(Browse to pick + preview). For a field that does NOT carry its own texture (BG-borrow / synth). On '
          'a fork that ships its own effects, use "Clone carried effect" instead.', catalog="sps_template"),
    Field("clone_sps", "Clone carried effect", OPTINT, "Browse THIS field's own effects + preview one -- clones "
          "it, reusing the field's texture (the right base on a native/verbatim fork). Use this OR Template.",
          catalog="sps"),
    Field("pos", "Position (x, z)", COORD, "where it sits on the floor; the height is AUTO-GROUNDED from the "
          "walkmesh (place it in OPEN space, not behind a wall, or it's hidden by the scene)"),
    Field("slot", "SPS slot", OPTINT, "0-15; blank = auto-assigned (top-down from 15, to dodge a fork's effects)"),
    Field("abr", "Blend mode", OPTINT, "blank = additive (the right glow for fire/smoke). 0 = 50% add · "
          "1 = add · 2 = subtract · 3 = 25% add · 15 = opaque"),
    Field("framerate", "Frame rate", OPTINT, "16 = 1x (normal ~15 fps loop); smaller = slower; blank = default"),
]
ENCOUNTER_SPEC = [
    Field("scene", "Battle scene", CATINT, "which monsters spawn: an id (e.g. 67 = Evil Forest) or a BSC_ "
          "scene name; blank = no random battles", catalog="encounter,scene",
          placeholder="a scene id, or a BSC_ name"),
    Field("freq", "Frequency (0-255)", OPTINT, "default 255"),
    Field("battle_music", "Battle music id", OPTINT, "default 0 = battle theme"),
]
MUSIC_SPEC = [
    Field("song", "Field BGM song id", OPTINT, "an existing game song, e.g. 9 = Vivi's Theme; blank = no "
                                               "field music (or mint YOUR OWN track via File below)",
          catalog="song"),
    Field("file", "File (custom track)", STR, "an audio file (wav/mp3/ogg/flac…, relative to this field.toml) "
                                              "minted into a NEW song at build — needs ffmpeg; IGNORED when a "
                                              "Song id is set above; hear it after a game restart",
          file="Audio (*.wav *.mp3 *.ogg *.flac *.m4a *.opus);;All files (*)"),
    Field("loop_start", "Loop start (samples)", OPTINT,
          "with File: loop point in SAMPLES; blank = loop the whole track"),
    Field("loop_end", "Loop end (samples)", OPTINT, "with File: loop end in samples; blank = track end"),
]
PARTY_SPEC = [
    Field("add", "Add members", STRLIST,
          "playable characters to ADD to the party at field load (names or 0-11), e.g. Steiner, Beatrix"),
    Field("remove", "Remove members", STRLIST,
          "playable characters to REMOVE at field load, e.g. Eiko"),
]
PLAYABLE_SPEC = [
    # the FLAT keys of a [[playable]] block (a custom 13th+ party member). The nested tables --
    # stats / params / names / abilities / command1 / command2 / status / script -- are deliberately
    # NOT here: the editor's save keeps unknown keys verbatim (shell._commit pops only spec keys),
    # so an ability kit authored in TOML survives a form edit untouched.
    Field("id", "Character id", OPTINT, "the new CharacterId — 12 or higher (blank = auto)"),
    Field("name", "Name", STR, "the menu/battle name (no ';' or '#')"),
    Field("borrow", "Borrow from", STR,
          "the base character whose kit/rig this clones — a name Zidane…Beatrix or an id 0-11"),
    Field("recruit", "Recruit at field load", BOOL, "join the party when this field loads",
          default=False),
    Field("custom_battle_model", "Custom battle model", BOOL,
          "mint an independent, Blender-editable battle model at its own id (≥ 6000)", default=False),
    Field("custom_battle_anims", "Custom battle animset", BOOL,
          "give the minted model its OWN editable animset (needs the custom battle model)",
          default=False),
    Field("anim_edits", "Animset edits (.glb)", STR,
          "a Blender-edited donor .glb the build ships onto the animset — survives re-deploys "
          "(needs the custom animset; see `ff9mapkit playable-anims`)",
          file="glTF (*.glb *.gltf);;All files (*)"),
    Field("portrait", "Portrait PNG", STR, "a 132×190 PNG for the menu/battle avatar",
          file="Images (*.png);;All files (*)"),
    Field("battle_model_from", "Battle model donor", STR,
          "mint from this GEO battle model instead of the borrow character's", catalog="model"),
    Field("battle_model_id", "Minted model id", OPTINT,
          "the minted battle model's id (blank = auto, 6100 + slot; must be ≥ 6000)"),
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
    Field("actors", "Cast", STRLIST, "[[npc]] names (and/or \"player\") the scene drives; blank = narration"),
    Field("once", "Play once", BOOL, "off = replays every visit", default=True),
    Field("requires_scenario", "Requires beat", SCENARIOREF,
          "the DIRECTOR GATE: only plays when the ScenarioCounter == this beat (number or area name); "
          "blank = always"),
    Field("requires_flag", "Requires flag set", FLAGREF,
          "only plays while this story flag (name/idx) is set", catalog="flag"),
    Field("set_scenario", "Then set beat", SCENARIOREF,
          "the DIRECTOR ADVANCE: at scene end, move the story to this beat (once, only when it played)"),
    Field("then_warp", "Then warp to field", OPTINT,
          "end the scene with a fade + warp to this field id (how a forced-ATE scene returns)"),
    Field("warmup", "Warmup frames", OPTINT, "default 30 (let the field settle)"),
]
MARKER_SPEC = [
    Field("name", "Name", STR, "a label; reference it in a cutscene as walk = \"<name>\""),
    Field("pos", "Position (x, z)", COORD, "where it sits on the floor; or place it in Blender"),
]
FLAG_SPEC = [
    Field("name", "Name", STR, "the story-flag name you reference in events / gateways / choices "
          "(set_flag, show-while-unset, …)"),
    Field("index", "gEventGlobal bit", INT, "a save-persistent bit in the custom band [8712, 16320); "
          "Story State labels a set bit with this name"),
]
CHOICE_SPEC = [
    Field("npc", "NPC", STR, "talk-triggered: the [[npc]] name (set npc OR zone, not both)"),
    Field("zone", "Zone (x z; x z; ...)", ZONE, "zone trigger: 4 corners (a lever); or place in Blender"),
    Field("trigger", "Trigger (zone)", STR, "blank = action (press to use, re-usable); 'walk' = auto-pop"),
    Field("once", "Fires once ever", BOOL, "walk-trigger only: on = once ever; off = once per visit", default=True),
    Field("prompt", "Prompt", STR, "the question shown above the options"),
    Field("speaker", "Speaker name", STR, "optional name before the prompt"),
    Field("tail", "Window tail", STR, _TAIL_HELP + ". Default UPR."),
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
PLAYER_SPEC = [
    Field("spawn", "Spawn (x, z)", COORD, "where the player appears -- the DEFAULT arrival (a debug-menu warp, or "
          "any door without a per-door row below); usually placed in Blender"),
    Field("face", "Spawn facing (0-255)", OPTINT,
          "0=south (toward the camera), 64=west, 128=north, 192=east"),
    Field("model", "Walk-as model", FLAGREF, "re-skin WHO YOU WALK AS (a model id, an exact GEO name, or an "
          "archetype name). Movement clips only -- free-roam fields", catalog="archetype,creature,model"),
    Field("arrival", "Per-door arrivals", ARRIVALLIST,
          "one row per entrance -- 'entrance, x, z' or 'entrance, x, z, face' (rows split by ';'). The "
          "arriving door picks its row via the entrance= its gateway wrote; no row = the spawn above. "
          "Imports fill these from the donor's real table automatically"),
]

# one-line purpose for each section, shown at the top of its form (the "what is this" cue).
SECTION_HELP = {
    "field": "The field's identity: a unique id (>= 4000), a short name, and the area (>= 10).",
    "camera": "Camera / walkmesh / layers / positions are SPATIAL -- author them in Blender. The one LOGIC "
              "key -- entry_settle, the frames held black on entry (a count, or \"auto\" = computed) -- is "
              "editable here.",
    "dialogue": "Text options. Auto-wrap breaks long dialogue lines to fit the screen (FF9 won't).",
    "encounter": "Random battles on this field (battle scene + frequency + battle music).",
    "music": "The field's background music — an existing game song (a song id), or your own audio file "
             "minted into the mod at build.",
    "party": "Who's in the party (menu + battle) on this field -- add/remove playable characters at load. "
             "Separate from who you WALK as (an Import option).",
    "player": "Where (and which way) the player appears on entry. The spawn is the default landing; the "
              "per-door rows dispatch on the entrance the arriving gateway wrote, so each door can land + "
              "face the player differently (like real FF9 fields).",
    "startup": "Assert the story beat this field boots in (a forked field starts at scenario zero): set the "
               "scenario and any story flags, unconditionally, at field load.",
    "cutscene": "A scripted scene. Steps run in order with control locked; a CAST (actors = [names]) lets "
                "steps walk/animate those NPCs (a step's Actor picks who; blank = the sole cast member). "
                "Gate it to a story beat (requires scenario) and advance the beat at scene end (set "
                "scenario) -- the story-event director. Repeat [[cutscene]] blocks (one per beat) in the "
                "TOML for a multi-beat dispatch.",
    "npc": "People who stand in the room: a model (preset), a line of dialogue, optional story gate.",
    "gateway": "An exit zone -> another field (the door the player walks into).",
    "event": "A walk-in trigger: show a message, give an item/gil, or set a story flag.",
    "chest": "An openable, savable treasure chest: a model you PRESS to open -> it gives an item/gil, shows the "
             "centered 'Received' box, and stays open across saves.",
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
    "set_flag": "story flag as \"index, value\" -- e.g. 8712, 1 (custom flags live in 8712+)",
    "walk": "a marker name, @player, or \"x, z\" (auto-routes around obstacles)",
    "path": "a route through waypoints: \"a; b; c\" (names or x z)",
    "teleport": "instantly move to a marker / @player / \"x, z\"",
    "animation": "a gesture name (e.g. glad, angry, nod) or a numeric id",
    "turn": "face an angle 0-255 (0=south, 64=west, 128=north, 192=east)",
    "face_player": "(no value) turn to face the player",
}
GLOBAL_STEPS = ("say", "wait", "set_flag")
ACTOR_STEPS = ("walk", "path", "teleport", "animation", "turn", "face_player")
# Which kinds may run IN PARALLEL with the preceding beat (`with_prev`). Mirrors
# ``build.PARALLEL_STEP_KINDS`` -- the compiler's own rule -- and is fenced against it in
# test_workspace_cutscene, so the checkbox can never offer a beat the validator will reject.
PARALLEL_STEPS = ("walk", "path", "animation", "turn")


def single_block(container, section, *, create=False) -> dict:
    """The ONE dict a *single*-section form edits, for a section the toml may store either way.

    ``[cutscene]`` (one table) and ``[[cutscene]]`` (the story-event DISPATCH -- several scenes on one
    field, each gated to its own beat) both reach a form as one editable block: **index 0**. Every path
    that reads or folds a single form has to agree on that, or they disagree about the TYPE of the thing
    they are handling.

    They did disagree, in both editors:

    * **Qt** -- ``Workspace._commit`` normalized the list; ``_commit_active`` and
      ``_form_matches_baseline`` did not, so they ran ``list.pop(key, None)`` -> ``TypeError``. Because
      ``_commit_active_ck`` sits on the nav / undo / redo / refresh / Check / save boundary, mounting
      Cutscene on any ``[[cutscene]]`` field TRAPPED the editor -- silently, since there is no excepthook
      and the entry point is a ``.pyw``.
    * **Tk** -- ``app._show_cutscene`` did ``cs.get("steps", [])`` straight off the list ->
      ``AttributeError``, after ``entity_to_values`` had already drawn an all-blank form (it reads misses
      as defaults, so a list silently yields blanks rather than raising).

    Both shipped stolen-ember examples tripped both editors. One owner now, per THE CALL-SITE LAW.

    ``create=True`` materializes (the commit paths); the default reads without dirtying the doc (the
    baseline / compare / render paths, which must never materialize an empty section).
    """
    cur = container.setdefault(section, {}) if create else (container.get(section) or {})
    if not isinstance(cur, list):
        return cur
    if not cur or not isinstance(cur[0], dict):      # a plural section -> the form edits BLOCK 0
        if not create:
            return {}
        cur.insert(0, {})
    return cur[0]


def all_blocks(raw) -> list:
    """Every block of a maybe-plural section, in author order -- a singleton table comes out as the
    one-block case. The editor-side twin of :func:`ff9mapkit.content.cutscene.blocks` (the build's owner);
    kept here so the GUI does not drag in the ``content`` -> ``eb`` import chain, and FENCED against it in
    ``test_workspace_cutscene`` so the two can never disagree about what a dispatch is."""
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [raw]
    return [b for b in raw if isinstance(b, dict)]


def block_count(container, section) -> int:
    """How many blocks a single-section key actually holds (1 for a singleton, N for an array-of-tables,
    0 when absent) -- what a surface needs to TELL the author it is editing one of several."""
    cur = container.get(section)
    if cur is None:
        return 0
    return len(cur) if isinstance(cur, list) else 1


# --- field rules shared by BOTH editors (Tk app.py + Qt forms_qt.py) ----------------------
# THE CALL-SITE LAW: these two were inline expressions duplicated in each editor, and they drifted --
# forms_qt's placeholder promised "a {catalog} name or id" on fields whose parser rejected every name.
# One owner each, so a new kind cannot flip a picker's behaviour by accident.
def wants_id(field) -> bool:
    """Does this field's ``Browse…`` picker hand back the entry's numeric ID instead of its name?

    True for the plain numeric kinds AND for :data:`CATINT`. A CATINT field *accepts* a typed name, but the
    picker still fills an id, because a picker LABEL is not always a typeable identifier: the warm
    ``encounter`` kind labels a scene "Goblin, Fang -- Evil Forest (field 250, random)", which no resolver
    takes. Handing back the id keeps every shipped numeric example byte-identical.

    :data:`ANIMSET` answers **False**: its picker writes a whole ``stand=…, walk=…`` LINE, not one id, and
    the ``anim`` (gesture) picker writes the action NAME the build resolves through the actor's own rig.
    Both are still id-BEARING underneath -- ``wants_id`` is about what the widget receives, not what the
    engine eats."""
    return field.kind in (INT, OPTINT, CATINT)


def tk_browsable(field) -> bool:
    """Does the TK editor's Info-Hub picker know this field's catalog? (See :data:`GUI_ONLY_CATALOGS`.)

    The tk form used to render Browse for ANY ``catalog=`` field, so a Workspace-only kind would grow a
    button whose picker indexes nothing and answers nothing."""
    kinds = [k.strip() for k in (field.catalog or "").split(",") if k.strip()]
    return any(k not in GUI_ONLY_CATALOGS for k in kinds)


def placeholder_for(field) -> str:
    """The line-edit placeholder for a catalog-backed field -- it must not promise more than the PARSER
    accepts. ``[encounter] scene`` shipped "a encounter name or id" over a parser that refused every name
    (`expected a whole number, got 'BSC_CA_E013'`); the catalogs that are still id-only (song, sps) say so.
    ``Field.placeholder`` overrides when the first catalog kind isn't the typeable one."""
    if field.placeholder:
        return field.placeholder
    if not field.catalog:
        return ""
    kind = field.catalog.split(",")[0].strip()
    art = "an" if kind[:1].lower() in "aeiou" else "a"
    if field.kind in (INT, OPTINT):                  # numeric-only: the build int()s it, a name would die
        return f"{art} {kind} id"
    return f"{art} {kind} name or id"


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


def parse_arrivallist(s):
    """[[player.arrival]] rows: semicolon/newline rows, each ``"entrance, x, z"`` or
    ``"entrance, x, z, face"`` -> a list of ``{entrance, pos: [x, z][, face]}`` dicts (face 0-255 compass).
    Empty -> None. Round-trips with :func:`format_arrivallist` (the [startup]-flags dict-list idiom)."""
    s = _str(s).strip()
    if s == "":
        return None
    out = []
    for row in re.split(r"[;\n]+", s):
        if not row.strip():
            continue
        parts = [p.strip() for p in row.split(",")]
        if len(parts) not in (3, 4) or not all(_is_int(p) for p in parts):
            raise ValueError(f"arrival row {row.strip()!r}: expected 'entrance, x, z' or "
                             f"'entrance, x, z, face' (whole numbers)")
        d = {"entrance": int(parts[0]), "pos": [int(parts[1]), int(parts[2])]}
        if len(parts) == 4:
            d["face"] = int(parts[3])
        out.append(d)
    return out or None


def format_arrivallist(v):
    if not isinstance(v, (list, tuple)):
        return str(v)
    rows = []
    for d in v:
        pos = d.get("pos") if isinstance(d, dict) else None
        if not (isinstance(pos, (list, tuple)) and len(pos) >= 2):
            continue                                   # a malformed row is the build's error to explain
        rows.append(f"{d.get('entrance', 0)}, {int(pos[0])}, {int(pos[1])}"
                    + (f", {int(d['face'])}" if d.get("face") is not None else ""))
    return "; ".join(rows)


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


def parse_animset(raw):
    """``[[npc]] anims``: ``"stand=560, walk=571"`` -> ``{"stand": 560, "walk": 571}``. Empty -> None.

    Slot names are validated against :data:`ANIM_SLOTS` -- the .eb Init writes exactly those five setters,
    so a typo'd slot would be silently dropped by ``content.npc._complete_anims`` (it fills from ``stand``)
    and the NPC would ship the wrong clip with no error anywhere.

    Values are whole CLIP IDS, not gesture names: the anim-setter args are u16 and ``content.npc._anim16``
    ``int()``s the value, so a name typed here would die mid-build rather than at the form. The Browse
    picker fills the ids (and previews them first)."""
    s = _str(raw).strip()
    if s == "":
        return None
    out = {}
    for row in re.split(r"[,;\n]+", s):
        row = row.strip()
        if not row:
            continue
        slot, sep, val = row.partition("=") if "=" in row else row.partition(":")
        slot, val = slot.strip().lower(), val.strip()
        if not sep or not slot:
            raise ValueError(f"animations: each entry is \"slot = id\", got {row!r} "
                             f"(slots: {', '.join(ANIM_SLOTS)})")
        if slot not in ANIM_SLOTS:
            raise ValueError(f"animations: unknown slot {slot!r} (use {', '.join(ANIM_SLOTS)})")
        try:
            out[slot] = int(val)
        except ValueError:
            raise ValueError(f"animations: {slot} needs a whole clip id, got {val!r}") from None
    return out or None


def format_animset(v):
    """``{'stand': 560, ...}`` -> ``"stand=560, walk=571"`` in the canonical slot order (round-trips with
    :func:`parse_animset`). A hand-authored non-dict / non-numeric value is shown VERBATIM rather than
    reformatted -- the form must never quietly rewrite something it cannot parse back."""
    if not isinstance(v, dict):
        return _str(v)
    known = [f"{slot}={v[slot]}" for slot in ANIM_SLOTS if slot in v]
    extra = [f"{k}={v[k]}" for k in v if k not in ANIM_SLOTS]
    return ", ".join(known + extra)


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
    if kind == CATINT:
        return parse_flagref(raw)                   # an id -> int, a catalog NAME -> str (resolved at build by
                                                    # resolve_encounter_scenes / resolve_npc_model)
    if kind == FLAGDICTLIST:
        return parse_flagdictlist(raw)
    if kind == BYTEDICTLIST:
        return parse_bytedictlist(raw)
    if kind == ARRIVALLIST:
        return parse_arrivallist(raw)
    if kind == ANIMSET:
        return parse_animset(raw)
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
        elif f.kind == ARRIVALLIST:
            vals[f.key] = format_arrivallist(v)
        elif f.kind == ANIMSET:
            vals[f.key] = format_animset(v)       # a DICT -- str() would write "{'stand': 560}" into the widget
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
    """A one-line summary for the step list, e.g. ``say: "hello"``, ``guard · walk: 0, -800`` (the actor
    tag prefixes), or ``vivi · animation: glad  [with prev]`` (a parallel beat)."""
    k = step_key(step)
    if not k:
        return "(empty)"
    body = "face_player" if k == "face_player" else f"{k}: {step_value_text(step)}"
    a = step.get("actor")
    if a:
        body = f"{a} · {body}"
    if step.get("with_prev"):
        body += "  [with prev]"
    return body


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
