"""``[[battle_patch]]`` / ``[[battle_enemy]]`` / ``[[battle_attack]]`` -- author ``BattlePatch.txt`` by NAME or
index: the reflection channel for the enemy/attack/scene combat data that CSV can't reach and raw16 can only
reach by FORKING the scene. This is the Phase-4 emitter (see ``docs/BATTLE_DESIGN.md`` §2a/§8).

WHY a BattlePatch channel (vs the raw16 ``[scene]`` tuner):
  * ``[scene]`` byte-patches a FORKED scene's ``dbfile0000.raw16`` -> it only works on a scene you ship a
    modified raw16 for, and it can't reach fields that aren't in the raw16 disk layout at all.
  * ``BattlePatch.txt`` patches ANY scene IN PLACE by reflection AFTER ``ReadBattleScene`` (no fork, no
    repack), and it reaches the ``[Memoria.PatchableField]``-flagged fields -- INCLUDING ones with no raw16
    slot: the drop/steal RATE arrays, ``BonusElement``, ``MaxDamageLimit``/``MaxMpDamageLimit``,
    ``WinCardRate`` (``SB2_MON_PARM.cs:53-179``) -- and the per-enemy ATTACK table (``AA_DATA``/``BTL_REF``,
    ``BTL_SCENE.cs:127-153``), which the kit could not touch at all before.
  * The by-NAME selectors (``AnyEnemyByName:`` / ``AnyAttackByName:``) patch EVERY enemy/attack of that name
    across ALL scenes -- the campaign-wide WIN over Hades Workshop ("buff every Goblin across the chain").

THE ENGINE FORMAT (``Memoria.DataPatchers.PatchBattles`` / ``ApplyBattlePatch``, ``DataPatchers.cs:538-682``):
``BattlePatch.txt`` is a STATEFUL line list. A *selector* line opens a patch context; subsequent *field*
lines (``FieldName value``) set the named ``[PatchableField]`` on the struct for that context's token type:
  * ``Battle: <id|name>``          -> a SCENE patch (sets ``BTL_SCENE_INFO`` scene flags). Narrow it with:
      ``Pattern: <i>``             -> a PATTERN patch (``SB2_PATTERN``: Rate/Camera/AP)
      ``Enemy: <i>`` / ``EnemyByName: <n>``   -> an ENEMY patch (``SB2_MON_PARM`` + ``SB2_ELEMENT``)
      ``Attack: <i>`` / ``AttackByName: <n>`` -> an ATTACK patch (``AA_DATA`` + ``BTL_REF`` + cmd info)
  * ``AnyEnemyByName: <name>``     -> a global ENEMY patch (every scene)
  * ``AnyAttackByName: <name>``    -> a global ATTACK patch (every scene)
Each narrower REUSES the current patch's scene-applicability, so within a ``Battle:`` block the order is:
scene flags first (they bind to the ``Battle:`` Scene patch), THEN the ``Pattern:``/``Enemy:``/``Attack:``
sub-blocks -- which is exactly how this module emits.

VALUE ENCODING (``ExtensionMethodsString.TryTypeParse`` / ``TryArrayParse``, ``DataPatchers.cs:572-581``):
a field's value string is parsed by its C# type -- ``String`` verbatim, an ``enum`` via ``Enum.Parse`` (which
accepts EITHER flag names OR a plain integer), numerics/Boolean via ``TryParse``, an array space-separated.
Because ``Enum.Parse`` takes integers, we emit INTEGER masks for every enum/flags/element/status/item field
(via the committed :mod:`battlecsv` name<->bit tables + :func:`ff9mapkit.items.resolve`) -- so NO new enum-name
table is committed (provenance: only your authored overrides live in the toml; the emitted ``BattlePatch.txt``
is mod build-output, never committed). Booleans emit ``True``/``False``. Narrow engine column types are
RANGE-CHECKED offline (a value past a Byte/UInt16/UInt32 cap would otherwise be silently dropped by the
engine's ``TryParse``).
"""
from __future__ import annotations

from .. import items
from . import battlecsv

_U16 = 0xFFFF
_U32 = 0xFFFFFFFF
_I32 = 2 ** 31 - 1
_U64 = 2 ** 64 - 1
_STATUS_SET_MAX = 38    # the highest StatusSetId the base engine defines (StatusSetId.cs: None=0 .. =38)

# A field spec = (EngineFieldName, encoder, max). `max` is None for the multi-value encoders (items/rates),
# which range-check each element themselves. Encoders: int / bool / elements / status / script / items / rates.
# The EngineFieldName is the EXACT C# field name DataPatchers matches by reflection (case-sensitive).

# ---- ENEMY token: SB2_MON_PARM + SB2_ELEMENT [PatchableField]s (SB2_MON_PARM.cs:33-179, SB2_ELEMENT.cs) ----
ENEMY_FIELDS = {
    "max_hp": ("MaxHP", "int", _U32), "max_mp": ("MaxMP", "int", _U32),
    "gil": ("WinGil", "int", _U32), "exp": ("WinExp", "int", _U32),
    "level": ("Level", "int", 0xFF), "category": ("Category", "int", 0xFF),
    "hit_rate": ("HitRate", "int", 0xFF),
    "phys_def": ("PhysicalDefence", "int", _I32), "phys_evade": ("PhysicalEvade", "int", _I32),
    "mag_def": ("MagicalDefence", "int", _I32), "mag_evade": ("MagicalEvade", "int", _I32),
    "blue_magic": ("BlueMagic", "int", _I32),
    # SB2_ELEMENT (the 4 core battle stats; reflection routes these via scene.MonAddr[i].Element)
    "speed": ("Speed", "int", 0xFF), "strength": ("Strength", "int", 0xFF),
    "magic": ("Magic", "int", 0xFF), "spirit": ("Spirit", "int", 0xFF),
    # element-affinity bitmasks (Byte each; element NAMES -> bitmask). `null`/`guard` = nullified/immune.
    "null": ("GuardElement", "elements", 0xFF), "guard": ("GuardElement", "elements", 0xFF),
    "absorb": ("AbsorbElement", "elements", 0xFF), "half": ("HalfElement", "elements", 0xFF),
    "weak": ("WeakElement", "elements", 0xFF),
    "bonus_element": ("BonusElement", "elements", 0xFF),     # BP-only: the element the enemy's OWN attacks carry
    # status masks (BattleStatus, a 64-bit [Flags] enum; status NAMES -> bitmask)
    "resist_status": ("ResistStatus", "status", _U64), "auto_status": ("AutoStatus", "status", _U64),
    "initial_status": ("InitialStatus", "status", _U64),
    # rewards: 4-item drop/steal lists (names/ids; "none"->255) + their odds arrays + the Tetra card
    "drop": ("WinItems", "items", None), "drop_rates": ("WinItemRates", "rates", None),
    "steal": ("StealItems", "items", None), "steal_rates": ("StealItemRates", "rates", None),
    "win_card": ("WinCard", "int", 0xFF), "win_card_rate": ("WinCardRate", "int", _U16),
    "max_damage_limit": ("MaxDamageLimit", "int", _U32),         # BP-only: per-enemy >9999 break
    "max_mp_damage_limit": ("MaxMpDamageLimit", "int", _U32),
}

# ---- ATTACK token: BTL_REF + AA_DATA [PatchableField]s (BTL_REF.cs, AA_DATA.cs:30-39) ----
ATTACK_FIELDS = {
    "power": ("Power", "int", _I32),                            # BTL_REF (single BYTE on disk, but Int32 in mem)
    "element": ("Elements", "elements", 0xFF), "elements": ("Elements", "elements", 0xFF),
    "rate": ("Rate", "int", _I32),
    "script": ("ScriptId", "script", _I32), "script_id": ("ScriptId", "script", _I32),
    "mp": ("MP", "int", _I32),                                  # AA_DATA
    "category": ("Category", "int", 0xFF), "type": ("Type", "int", 0xFF),
    # AddStatusNo is a StatusSetId enum (a StatusSets.csv ROW id, NOT a status bitmask). The engine parses it
    # via Enum.Parse, which casts ANY integer through WITHOUT bounds-checking, then indexes it with a RAW
    # Dictionary get (FF9Battle.add_status[...] / StatusSets[...]) built only from the 0..38 base rows -> an
    # undefined id (39+) is a KeyNotFoundException CRASH at command-build, not a no-op. So cap at the engine max.
    "status_set": ("AddStatusNo", "int", _STATUS_SET_MAX),
}

# ---- PATTERN token: SB2_PATTERN [PatchableField]s (SB2_PATTERN.cs:12-24; MonsterCount/Monster are NOT) ----
PATTERN_FIELDS = {
    "rate": ("Rate", "int", 0xFF), "camera": ("Camera", "int", 0xFF), "ap": ("AP", "int", _U32),
}

# ---- SCENE token: BTL_SCENE_INFO [PatchableField] Booleans (BTL_SCENE_INFO.cs:7-47; SB2_HEAD has none) ----
SCENE_FLAGS = {
    "special_start": ("SpecialStart", "bool", None), "preemptive": ("Preemptive", "bool", None),
    "back_attack": ("BackAttack", "bool", None), "no_game_over": ("NoGameOver", "bool", None),
    "no_exp": ("NoExp", "bool", None), "win_pose": ("WinPose", "bool", None),
    "runaway": ("Runaway", "bool", None), "can_escape": ("Runaway", "bool", None),
    "no_neighboring": ("NoNeighboring", "bool", None), "no_magical": ("NoMagical", "bool", None),
    "reverse_attack": ("ReverseAttack", "bool", None),
    "fixed_camera1": ("FixedCamera1", "bool", None), "fixed_camera2": ("FixedCamera2", "bool", None),
    "after_event": ("AfterEvent", "bool", None), "field_bgm": ("FieldBGM", "bool", None),
}

# keys that select/structure a block rather than set a field
_ENEMY_SEL = {"index", "name"}
_ATTACK_SEL = {"index", "name"}
_PATTERN_SEL = {"index"}
_SCENE_STRUCT = {"scene", "enemy", "attack", "pattern"}


class BattlePatchError(ValueError):
    pass


# ---- value encoding (shared by build + offline validate) ---------------------------------------------
def _to_int(value, key) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise BattlePatchError(f"{key} must be an integer (got {value!r})")
    try:
        return int(value)
    except ValueError:
        raise BattlePatchError(f"{key} must be an integer (got {value!r})")


def _resolve_items(value, key) -> list[int]:
    """4 drop/steal slots: each a name/id (engine RegularItem) or "none"/""/"-" -> 255 (NoItem). Mirrors
    scene_data._resolve_items (in-game proven on the Phase-1 Goblin drop)."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise BattlePatchError(f"{key} must be a list of exactly 4 items (name/id; \"none\" or 255 = empty)")
    out = []
    for it in value:
        if isinstance(it, str) and it.strip().lower() in ("none", "", "-"):
            out.append(255)
        else:
            try:
                out.append(items.resolve(it))
            except (ValueError, TypeError) as ex:
                raise BattlePatchError(f"{key}: {ex}")
    return out


def _resolve_rates(value, key) -> list[int]:
    """4 drop/steal ODDS (UInt16 each). The engine reads the WHOLE array, so all 4 are required."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise BattlePatchError(f"{key} must be a list of exactly 4 rates (UInt16 0-{_U16}; the engine reads "
                               f"all 4 -- defaults are drop {{256,96,32,1}} / steal {{256,64,16,1}})")
    out = []
    for r in value:
        v = _to_int(r, key)
        if not 0 <= v <= _U16:
            raise BattlePatchError(f"{key} value {v} out of range (0-{_U16})")
        out.append(v)
    return out


def encode_field(key, value, spec, *, warnings=None) -> str:
    """Resolve + RANGE-CHECK one override value -> its BattlePatch value string (space-joined for arrays).
    Raises BattlePatchError offline so a bad value fails the lint/build, never the running game."""
    engine_name, enc, vmax = spec
    if enc == "int":
        v = _to_int(value, key)
    elif enc == "bool":
        if not isinstance(value, bool):
            raise BattlePatchError(f"{key} must be true or false (got {value!r})")
        return "True" if value else "False"
    elif enc == "elements":
        try:
            v = battlecsv.encode_elements(value)
        except (ValueError, TypeError) as ex:
            raise BattlePatchError(f"{key}: {ex}")
    elif enc == "status":
        try:
            v = battlecsv.encode_status(value)
        except (ValueError, TypeError) as ex:
            raise BattlePatchError(f"{key}: {ex}")
    elif enc == "script":
        if isinstance(value, str) and not value.strip().lstrip("-").isdigit():
            sid = {n.lower(): i for i, n in battlecsv.SCRIPT_IDS.items()}.get(value.strip().lower())
            if sid is None:
                raise BattlePatchError(f"{key}: unknown scriptId formula {value!r} "
                                       f"(see `ff9mapkit battle-actions --script-ids`)")
            v = sid
        else:
            v = _to_int(value, key)
        if warnings is not None and not battlecsv.is_stock_script(v):
            warnings.append(f"{key}: scriptId {v} is not in the externalized formula catalog -- re-pointing an "
                            f"attack at an existing formula is data, but a BRAND-NEW formula needs a "
                            f"Memoria.Scripts.<Mod>.dll (not the engine DLL)")
    elif enc == "items":
        return " ".join(str(i) for i in _resolve_items(value, key))
    elif enc == "rates":
        return " ".join(str(i) for i in _resolve_rates(value, key))
    else:
        raise BattlePatchError(f"internal: bad encoder {enc!r}")
    if vmax is not None and not 0 <= v <= vmax:
        raise BattlePatchError(f"{key}={v} out of range (0-{vmax})")
    return str(v)


# ---- field-line emission for one token's override dict ------------------------------------------------
def _field_lines(overrides, fields_map, *, ctx, warnings) -> list[str]:
    """``FieldName value`` lines for every override key found in ``fields_map`` (skipping the selector keys
    already consumed by the caller). Raises on an unknown field key."""
    lines: list[str] = []
    for k, val in overrides.items():
        spec = fields_map.get(k)
        if spec is None:
            raise BattlePatchError(f"{ctx}: unknown field {k!r} (known: {', '.join(sorted(fields_map))})")
        try:
            lines.append(f"{spec[0]} {encode_field(k, val, spec, warnings=warnings)}")
        except BattlePatchError as ex:
            raise BattlePatchError(f"{ctx} {ex}")
    return lines


def _selector_name(token, value, key) -> str:
    """A by-name selector arg -- the US battle-text name, verbatim (spaces kept; the engine matches the WHOLE
    remainder of the line)."""
    if not isinstance(value, str) or not value.strip():
        raise BattlePatchError(f"{key} must be a non-empty enemy/attack name (a string)")
    return value.strip()


def _require_table(blk, ctx) -> dict:
    """A battle block must be a table (TOML dict). Raise BattlePatchError (NOT a TypeError/AttributeError) so a
    malformed toml fails the lint/build cleanly -- the linter must never traceback on bad input."""
    if not isinstance(blk, dict):
        raise BattlePatchError(f"{ctx} must be a table (got {type(blk).__name__}) -- "
                               f"e.g. {{ name = \"Goblin\", max_hp = 500 }}")
    return blk


def _scene_selector(value, ctx) -> str:
    """The ``Battle:`` selector arg: an int scene id (the engine parses it with Int32.TryParse) OR a non-empty
    BSC_ scene name. A float/list/over-Int32 value would emit a DEAD ``Battle:`` line the engine never matches
    (the block silently no-ops + is pruned) -- exactly the silent-drop this module exists to prevent."""
    if isinstance(value, int) and not isinstance(value, bool):
        if not 0 <= value <= _I32:
            raise BattlePatchError(f"{ctx} scene id {value} out of range (a battle scene id, 0-{_I32})")
        return str(value)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise BattlePatchError(f"{ctx} scene must be an int scene id or a \"BSC_...\" name (got {value!r})")


def _enemy_block(e, *, ctx, warnings, scoped) -> list[str]:
    """Emit one enemy patch: a selector (``Enemy: i`` / ``EnemyByName: n`` within a scene, or
    ``AnyEnemyByName: n`` globally) + its SB2_MON_PARM/SB2_ELEMENT field lines."""
    _require_table(e, ctx)
    has_idx, has_name = "index" in e, "name" in e
    if scoped:
        if has_idx == has_name:
            raise BattlePatchError(f"{ctx} needs exactly one of index = <type 0..> or name = \"<enemy name>\"")
        sel = f"Enemy: {_to_int(e['index'], ctx + ' index')}" if has_idx \
            else f"EnemyByName: {_selector_name('enemy', e['name'], ctx + ' name')}"
    else:                                                   # global [[battle_enemy]] -> AnyEnemyByName
        if not has_name or has_idx:
            raise BattlePatchError(f"{ctx} is global (every scene) -- it needs name = \"<enemy name>\" "
                                   f"(use a scene-scoped [[battle_patch.enemy]] with index = N to target a slot)")
        sel = f"AnyEnemyByName: {_selector_name('enemy', e['name'], ctx + ' name')}"
    body = {k: v for k, v in e.items() if k not in _ENEMY_SEL}
    if not body:
        raise BattlePatchError(f"{ctx} sets no fields (give e.g. max_hp = 500 or weak = [\"Fire\"])")
    return [sel, *_field_lines(body, ENEMY_FIELDS, ctx=ctx, warnings=warnings)]


def _attack_block(a, *, ctx, warnings, scoped) -> list[str]:
    _require_table(a, ctx)
    has_idx, has_name = "index" in a, "name" in a
    if scoped:
        if has_idx == has_name:
            raise BattlePatchError(f"{ctx} needs exactly one of index = <attack 0..> or name = \"<attack name>\"")
        sel = f"Attack: {_to_int(a['index'], ctx + ' index')}" if has_idx \
            else f"AttackByName: {_selector_name('attack', a['name'], ctx + ' name')}"
    else:
        if not has_name or has_idx:
            raise BattlePatchError(f"{ctx} is global (every scene) -- it needs name = \"<attack name>\"")
        sel = f"AnyAttackByName: {_selector_name('attack', a['name'], ctx + ' name')}"
    body = {k: v for k, v in a.items() if k not in _ATTACK_SEL}
    if not body:
        raise BattlePatchError(f"{ctx} sets no fields (give e.g. power = 40 or element = [\"Fire\"])")
    return [sel, *_field_lines(body, ATTACK_FIELDS, ctx=ctx, warnings=warnings)]


def _pattern_block(p, *, ctx, warnings) -> list[str]:
    _require_table(p, ctx)
    if "index" not in p:
        raise BattlePatchError(f"{ctx} needs index = <pattern 0..> (which formation)")
    sel = f"Pattern: {_to_int(p['index'], ctx + ' index')}"
    body = {k: v for k, v in p.items() if k not in _PATTERN_SEL}
    if not body:
        raise BattlePatchError(f"{ctx} sets no fields (give e.g. rate = 16 or ap = 12)")
    return [sel, *_field_lines(body, PATTERN_FIELDS, ctx=ctx, warnings=warnings)]


def _scene_block(blk, n, *, warnings) -> list[str]:
    """One ``[[battle_patch]]`` -> ``Battle: <id>`` + scene flags + nested pattern/enemy/attack sub-blocks."""
    ctx = f"[[battle_patch]] #{n}"
    _require_table(blk, ctx)
    scene = blk.get("scene")
    if scene is None or isinstance(scene, bool):
        raise BattlePatchError(f"{ctx} needs scene = <id or BSC_ name> (the BTL_SCENE to patch)")
    lines = [f"Battle: {_scene_selector(scene, ctx)}"]
    # scene flags bind to the Battle (Scene) patch -> they MUST come before any Pattern/Enemy/Attack narrower
    flags = {k: v for k, v in blk.items() if k not in _SCENE_STRUCT}
    lines += _field_lines(flags, SCENE_FLAGS, ctx=ctx, warnings=warnings)
    for i, p in enumerate(_as_list(blk.get("pattern"), f"{ctx} [[battle_patch.pattern]]")):
        lines += _pattern_block(p, ctx=f"{ctx} pattern #{i}", warnings=warnings)
    for i, e in enumerate(_as_list(blk.get("enemy"), f"{ctx} [[battle_patch.enemy]]")):
        lines += _enemy_block(e, ctx=f"{ctx} enemy #{i}", warnings=warnings, scoped=True)
    for i, a in enumerate(_as_list(blk.get("attack"), f"{ctx} [[battle_patch.attack]]")):
        lines += _attack_block(a, ctx=f"{ctx} attack #{i}", warnings=warnings, scoped=True)
    if len(lines) == 1:                                    # only "Battle: X", no fields anywhere -> a no-op block
        raise BattlePatchError(f"{ctx} sets nothing -- add a scene flag, or a [[battle_patch.enemy]] / "
                               f"[[battle_patch.attack]] / [[battle_patch.pattern]] sub-block")
    return lines


def _as_list(value, ctx):
    if value is None:
        return []
    if not isinstance(value, list):
        raise BattlePatchError(f"{ctx} must be a list of tables")
    return value


# ---- public: build the BattlePatch lines from aggregated toml blocks ----------------------------------
def build_lines(scene_patches=None, enemies=None, attacks=None) -> tuple[list[str], list[str]]:
    """Aggregate ``[[battle_patch]]`` (scene-scoped) + ``[[battle_enemy]]`` / ``[[battle_attack]]`` (global
    by-name) blocks -> (battle_patch_lines, warnings). Pure + offline (no install needed -- names/ids are the
    author's, masks come from the committed tables)."""
    warnings: list[str] = []
    lines: list[str] = []
    for n, blk in enumerate(_as_list(scene_patches, "[[battle_patch]]")):
        lines += _scene_block(blk, n, warnings=warnings)
    for n, e in enumerate(_as_list(enemies, "[[battle_enemy]]")):
        lines += _enemy_block(e, ctx=f"[[battle_enemy]] #{n}", warnings=warnings, scoped=False)
    for n, a in enumerate(_as_list(attacks, "[[battle_attack]]")):
        lines += _attack_block(a, ctx=f"[[battle_attack]] #{n}", warnings=warnings, scoped=False)
    return lines, warnings


# ---- offline structural + range validation (for `lint`, no install) ----------------------------------
def validate_blocks(scene_patches=None, enemies=None, attacks=None) -> list[str]:
    """Re-run the emission on a copy and surface every BattlePatchError as a message (empty => OK). All checks
    are install-free: structure, the field-name/range/encoder guards, and the selector rules."""
    problems: list[str] = []
    try:
        build_lines(scene_patches, enemies, attacks)
    except BattlePatchError as ex:
        # build_lines stops at the first error; surface it (the author fixes one at a time, like the scene lint)
        problems.append(str(ex))
    return problems


# ---- non-clobbering merge into a live BattlePatch.txt (deploy) ---------------------------------------
def _markers(field_id):
    return (f"// >>> ff9mapkit field {field_id} BattlePatch (auto -- edit the field.toml, not here)",
            f"// <<< ff9mapkit field {field_id}")


def merge_battle_patch(live_text: str, block_lines, field_id) -> str:
    """Splice ``block_lines`` into ``live_text`` between this field's ``//`` sentinel markers, REPLACING any
    prior block for the same id and PRESERVING every other line (a co-deployed battle's BGM/repoint lines, a
    stacked worktree's lines). The engine skips ``//`` lines (``DataPatchers.cs:551``), so the markers are inert.
    An empty ``block_lines`` just strips our prior block (a redeploy after the toml's battle blocks were removed).
    Idempotent: re-merging the same block yields the same text."""
    begin, end = _markers(field_id)
    kept, skip = [], False
    for ln in live_text.splitlines():
        if ln.strip() == begin:
            skip = True
            continue
        if ln.strip() == end:
            skip = False
            continue
        if not skip:
            kept.append(ln)
    while kept and not kept[-1].strip():                   # trim trailing blank lines before re-appending
        kept.pop()
    block = [ln for ln in (block_lines or []) if ln.strip()]
    out = list(kept)
    if block:
        out += [begin, *block, end]
    return ("\n".join(out) + "\n") if out else ""
