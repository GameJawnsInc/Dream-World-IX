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
# editing, so it reads first in the form. `flags` are the encounter RULES (header scene_flags). (The camera
# floats + ai_*/seq_* sub-tables are still out of this spec.)
SCENE_SPEC = [
    Field("monster_count", "Monster count", OPTINT,
          "how many enemies spawn (1-4) -- SET THIS to compose the formation + unlock per-slot edits"),
    Field("camera", "Camera", OPTINT, "opening camera: 0-2 = a fixed PSX pose, >=3 = random"),
    Field("ap", "AP reward", OPTINT, "the gameplay AP this fight awards"),
    Field("pattern", "Pattern", OPTINT, "which formation pattern to tune (default 0)"),
    Field("flags", "Encounter rules", STRLIST,
          "scene RULES (any of): back_attack, preemptive, no_escape, no_exp -- absent keeps the donor's"),
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


# ===== PLAYER / ABILITY tuning ==========================================================================
# Mod-GLOBAL CSV deltas a battle.toml may ALSO carry (the same blocks a field.toml can -- see
# ``ff9mapkit.battle.build.player_csv_problems`` / ``_emit_player_data``), so a battle fork tunes the PARTY
# that fights it in the SAME deployable doc. Each spec is FLAT over the existing field kinds; the FIRST field
# is the row "selector" (the tree label). The values name->id + base-CSV merge happens at build (which has the
# install); these specs only shape the override. Nested / multiline / list tables -- ``[[learn]]`` (sub-tables),
# ``[[ability_feature]]`` (a code body), ``[[status_set]]`` / ``[[magic_sword_set]]`` (offline list bundles) --
# stay build-supported + hand-authorable; they're out of the v1 forms (a later sub-increment).

# [[character]] -> BaseStats.csv (per-character base stats). The canonical CHARACTER_FIELDS keys.
CHARACTER_SPEC = [
    Field("character", "Character", STR, "name (Zidane..Beatrix) or a 0-11 id"),
    Field("strength", "Strength", OPTINT, "base Strength 0-255"),
    Field("magic", "Magic", OPTINT, "base Magic 0-255"),
    Field("dexterity", "Dexterity", OPTINT, "base Dexterity 0-255"),
    Field("will", "Will (Spirit)", OPTINT, "base Will / Spirit 0-255"),
    Field("gems", "Magic stones", OPTINT, "starting Gems / magic-stone count"),
]

# [[battle_action]] -> Actions.csv (rebalance a shared player ability). The common scalar levers; the
# targeting BOOLEANS + vfx ids stay hand-authorable (a delta omits an unchecked bool, which can't express
# "turn this OFF", so the form would silently fail to override it -- see build_entity's BOOL rule).
BATTLE_ACTION_SPEC = [
    Field("action", "Ability", STR, "name (e.g. Fire) or a 0-191 id"),
    Field("power", "Power", OPTINT, "base damage/heal power"),
    Field("element", "Elements", STRLIST, "element names, e.g. Fire, Ice (sets the element bitmask)"),
    Field("rate", "Rate / accuracy", OPTINT, "the action's hit/status rate"),
    Field("mp", "MP cost", OPTINT, "MP the ability costs"),
    Field("category", "Category", OPTINT, "ability category bits (0-255)"),
    Field("type", "Type", OPTINT, "ability type (0-255)"),
    Field("status_index", "Status set", OPTINT, "the StatusSets.csv row this action inflicts/cures"),
]

# [[status]] -> StatusData.csv (retune an ailment).
STATUS_SPEC = [
    Field("status", "Status", STR, "name (e.g. Poison) or a 0-32 id"),
    Field("tick", "Per-tick effect", OPTINT, "OprCount: the per-tick magnitude 0-255"),
    Field("duration", "Duration", OPTINT, "ContiCount: 0 = until cured (0-65535)"),
    Field("clear_on_apply", "Clears on apply", STRLIST, "statuses applying this one CLEARS, e.g. Sleep"),
    Field("immunity_provided", "Grants immunity to", STRLIST, "statuses this one blocks while active"),
]

# [[ability_gem]] -> AbilityGems.csv (the support-ability gem COST).
ABILITY_GEM_SPEC = [
    Field("ability", "Support ability", STR, "name (e.g. Auto-Haste / AutoHaste) or a 0-63 id"),
    Field("gems", "Gem cost", OPTINT, "magic stones to equip it"),
]

# [[character_param]] -> CharacterParameters.csv (per-character menu/row/preset wiring).
CHARACTER_PARAM_SPEC = [
    Field("character", "Character", STR, "name (Zidane..Beatrix) or a 0-11 id"),
    Field("row", "Front/back row", OPTINT, "0 = front, 1 = back (0-255)"),
    Field("win_pose", "Win pose", OPTINT, "victory-pose id (0-255)"),
    Field("category", "Category", OPTINT, "category bits (0-255)"),
    Field("menu_type", "Menu preset", STR, "a CharacterPresetId name (e.g. Steiner) or a 0-19 id"),
    Field("equipment_set", "Equipment set", OPTINT, "which equipment set governs this character (0-255)"),
    Field("serial_formula", "Serial formula", STR, "advanced: the serial-stat formula string"),
    Field("name_keyword", "Name keyword", STR, "advanced: the name-resolution keyword string"),
]

# [[command_set]] -> CommandSets.csv (re-point a character's battle-menu command SLOTS to BattleCommandIds).
COMMAND_SET_SPEC = [
    Field("preset", "Character preset", STR, "a CharacterPresetId name (e.g. Zidane) or a 0-19 id"),
    Field("attack", "Attack", OPTINT, "BattleCommandId 0-47"),
    Field("defend", "Defend", OPTINT, "BattleCommandId 0-47"),
    Field("ability1", "Ability 1", OPTINT, "BattleCommandId 0-47"),
    Field("ability2", "Ability 2", OPTINT, "BattleCommandId 0-47"),
    Field("item", "Item", OPTINT, "BattleCommandId 0-47"),
    Field("change", "Change", OPTINT, "BattleCommandId 0-47"),
    Field("attack_trance", "Attack (Trance)", OPTINT, "BattleCommandId 0-47"),
    Field("defend_trance", "Defend (Trance)", OPTINT, "BattleCommandId 0-47"),
    Field("ability1_trance", "Ability 1 (Trance)", OPTINT, "BattleCommandId 0-47"),
    Field("ability2_trance", "Ability 2 (Trance)", OPTINT, "BattleCommandId 0-47"),
    Field("item_trance", "Item (Trance)", OPTINT, "BattleCommandId 0-47"),
    Field("change_trance", "Change (Trance)", OPTINT, "BattleCommandId 0-47"),
]

# [[leveling]] -> Leveling.csv (the per-level growth curve; WHOLE-FILE re-emit, patched by level).
LEVELING_SPEC = [
    Field("level", "Level", INT, "1-99 (the level this row tunes)"),
    Field("exp", "EXP to next", OPTINT, "experience to the NEXT level (UInt32)"),
    Field("bonus_hp", "Bonus HP", OPTINT, "HP grows BonusHP*Strength/50 (UInt16)"),
    Field("bonus_mp", "Bonus MP", OPTINT, "MP grows BonusMP*Magic/100 (UInt16)"),
]

# the v1 "Party & abilities" tree branch: ordered (key, label, spec, selector_key, default_entry).
PLAYER_TABLES = [
    ("character", "Character stats", CHARACTER_SPEC, "character", {"character": "Zidane"}),
    ("battle_action", "Ability rebalance", BATTLE_ACTION_SPEC, "action", {"action": "Fire"}),
    ("status", "Status ailment", STATUS_SPEC, "status", {"status": "Poison"}),
    ("ability_gem", "Ability gem cost", ABILITY_GEM_SPEC, "ability", {"ability": "Auto-Haste"}),
    ("character_param", "Character params", CHARACTER_PARAM_SPEC, "character", {"character": "Zidane"}),
    ("command_set", "Battle command set", COMMAND_SET_SPEC, "preset", {"preset": "Zidane"}),
    ("leveling", "Leveling curve", LEVELING_SPEC, "level", {"level": 1}),
]
PLAYER_SPECS = {k: spec for (k, _l, spec, _s, _d) in PLAYER_TABLES}
PLAYER_LABEL = {k: lbl for (k, lbl, _sp, _s, _d) in PLAYER_TABLES}
PLAYER_SELECTOR = {k: sel for (k, _l, _sp, sel, _d) in PLAYER_TABLES}
PLAYER_DEFAULT = {k: dict(d) for (k, _l, _sp, _s, d) in PLAYER_TABLES}
