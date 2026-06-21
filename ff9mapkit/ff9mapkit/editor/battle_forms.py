"""Form specs for the Battle document (ENCOUNTER-FIRST), reusing the field editor's tk-free spec machinery
(:mod:`ff9mapkit.editor.forms` -- the :class:`~ff9mapkit.editor.forms.Field` dataclass, the field kinds, and
``build_entity`` / ``entity_to_values``).

A ``battle.toml`` is authored as an ENCOUNTER, not a loose enemy (the engine itself enforces this: a scene IS
a formation, and per-slot edits only apply once ``[scene] monster_count`` composes the formation). The three
specs here mirror that:

* :data:`BATTLEMAP_SPEC` -- ``[battlemap]``: the map's identity (the BBG slot it ships as, its geometry, and
  the mint/repoint scene wiring).
* :data:`SCENE_SPEC` -- ``[scene]``: the FORMATION (how many enemies, the opening camera, the AP reward).
* :data:`ENEMY_SPEC` -- ``[[scene.enemy]]``: one formation SLOT's enemy -- identity & stats, element/status
  affinities, rewards, placement, and a model re-skin.

The scalar stats are int fields; the element/status/drop/flags lists are :data:`~forms.STRLIST` (the same
comma-separated name list ``[party]`` uses); placement is a :data:`~forms.COORD`. The player-side CSV tuning
tables (``[[battle_action]]`` / ``[[status]]`` / ``[[character]]`` / ...) are a SEPARATE, scene-independent
spec set (a later sub-increment); they don't belong on a per-enemy slot. The advanced ``[scene]`` camera
floats and the ``ai_*`` / ``seq_*`` disassembly tiers are likewise out of this declarative spec.
"""
from __future__ import annotations

from .forms import COORD, INT, OPTINT, STR, STRLIST, Field

# [battlemap] -- the map identity (validate_battle: bbg is required + must look like BBG_B013; scene_id needs
# scene_name; scene_id (mint) and repoint_scene are mutually exclusive; char_tint/shadow are cosmetic).
BATTLEMAP_SPEC = [
    Field("bbg", "Background slot", STR,
          "the BBG_* slot this map ships as, e.g. BBG_B013 (= the forked slot to OVERRIDE that real map)"),
    Field("fbx", "Geometry (.fbx)", STR, "the FBX geometry file in this folder (default <bbg>.fbx)"),
    Field("repoint_scene", "Repoint scene id", OPTINT,
          "point an EXISTING battle scene's background at this map (mutually exclusive with a mint)"),
    Field("scene_id", "Mint scene id", OPTINT, "advanced: a NEW battle-scene id to mint (needs a scene name)"),
    Field("scene_name", "Mint scene name", STR, "advanced: the new scene's name (pair with the mint id)"),
    Field("char_tint", "Char tint (r, g, b)", STRLIST,
          "RGB the engine lights party/enemies with on this map (0-255 each; default 128, 128, 128)"),
    Field("shadow", "Shadow", OPTINT, "shadow intensity 0-255 (default 32)"),
]

# [scene] -- the FORMATION. monster_count is the keystone: it recomposes every pattern and unlocks per-slot
# editing, so it reads first in the form. (The camera floats + ai_*/seq_* sub-tables are out of this spec.)
SCENE_SPEC = [
    Field("monster_count", "Monster count", OPTINT,
          "how many enemies spawn (1-4) -- SET THIS to compose the formation + unlock per-slot edits"),
    Field("camera", "Camera", OPTINT, "opening camera: 0-2 = a fixed PSX pose, >=3 = random"),
    Field("ap", "AP reward", OPTINT, "the gameplay AP this fight awards"),
    Field("pattern", "Pattern", OPTINT, "which formation pattern to tune (default 0)"),
]

# [[scene.enemy]] -- one formation slot's enemy. Stats are per-TYPE: two slots sharing a type share ALL stats.
ENEMY_SPEC = [
    Field("slot", "Slot", INT, "the formation slot 0-3 (required)"),
    Field("type", "Type", OPTINT, "the enemy TYPE to place here (must already exist in the scene)"),
    # identity & stats (all per-type, 0-255 unless noted)
    Field("hp", "HP", OPTINT, "max HP (0-65535)"),
    Field("mp", "MP", OPTINT, "max MP (0-65535)"),
    Field("speed", "Speed", OPTINT, "0-255"),
    Field("strength", "Strength", OPTINT, "0-255"),
    Field("magic", "Magic", OPTINT, "0-255"),
    Field("spirit", "Spirit", OPTINT, "0-255"),
    Field("level", "Level", OPTINT, "0-255 (drives variance, steal, Level-N spells)"),
    Field("category", "Category", OPTINT, "race/killer/flight/undead category bits (0-255)"),
    Field("hit_rate", "Hit rate", OPTINT, "physical accuracy (0-255)"),
    Field("phys_def", "Phys. defence", OPTINT, "0-255"),
    Field("phys_evade", "Phys. evade", OPTINT, "0-255"),
    Field("mag_def", "Mag. defence", OPTINT, "0-255"),
    Field("mag_evade", "Mag. evade", OPTINT, "0-255"),
    Field("blue_magic", "Blue magic id", OPTINT, "the Quina Eat / Blue-magic learn id"),
    # affinities (element / status NAME lists)
    Field("null", "Null elements", STRLIST, "elements this enemy is IMMUNE to, e.g. Fire, Ice"),
    Field("absorb", "Absorb elements", STRLIST, "elements this enemy ABSORBS (heals from)"),
    Field("half", "Halve elements", STRLIST, "elements this enemy takes HALF from"),
    Field("weak", "Weak elements", STRLIST, "elements this enemy is WEAK to"),
    Field("resist_status", "Resist status", STRLIST, "statuses this enemy resists, e.g. Poison, Sleep"),
    Field("auto_status", "Auto status", STRLIST, "statuses always active on this enemy"),
    Field("initial_status", "Initial status", STRLIST, "statuses on this enemy at battle start"),
    # rewards
    Field("gil", "Gil", OPTINT, "gil awarded (0-65535)"),
    Field("exp", "EXP", OPTINT, "EXP awarded (0-65535)"),
    Field("drop", "Drops (4 items)", STRLIST, 'win items: 4 entries (name/id; "none" for an empty slot)'),
    Field("steal", "Steals (4 items)", STRLIST, 'stealable items: 4 entries (name/id; "none" for empty)'),
    Field("win_card", "Win card", OPTINT, "the Tetra Master card id awarded"),
    Field("flags", "Flags", STRLIST, "behaviour flags: die_atk, die_dmg, non_dying_boss"),
    # placement
    Field("pos", "Position (x, z)", COORD, "where this enemy stands in the formation"),
    Field("y", "Height (y)", OPTINT, "vertical placement offset"),
    Field("rot", "Rotation", OPTINT, "facing rotation"),
    # re-skin (visual transplant)
    Field("model", "Re-skin model id", OPTINT, "advanced: borrow another enemy TYPE's model + animations"),
    Field("model_scene", "Re-skin donor scene", STR, "advanced: a donor battle scene to borrow a model from"),
    Field("model_type", "Re-skin donor type", OPTINT, "advanced: which type in the donor scene to borrow"),
    Field("ai_entry", "AI entry", OPTINT, "advanced: explicit AI entry for this slot (needs monster_count)"),
]
