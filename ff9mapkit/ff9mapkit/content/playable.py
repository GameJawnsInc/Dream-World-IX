"""``[[playable]]`` -- define a genuine 13th (or 14th..) PLAYABLE character: a NEW ``CharacterId`` that joins
the party ALONGSIDE the 12 canon characters (NOT a reskin of an existing slot). Tier C of the PC/party map.

★ ZERO-DLL, save-safe (memory ``project-ff9-13th-character``; every claim verified against the Memoria source).
The engine model:
  * ``FF9StateGlobal.player`` is a ``Dictionary<CharacterId, PLAYER>`` and ``FF9Play_Init`` allocates a PLAYER
    for **every loaded CharacterParameters row** -- so a ``CharacterParameters.csv`` row with ``Id=12`` (the
    ALLOCATOR) brings the 13th character into existence. The BaseStats / CharacterParameters coverage gates are
    MINIMUMS (``for i < 12``), so an extra id-12 row PASSES; the menu / battle / equip UIs all iterate the
    dictionary, so the 13th appears for free.
  * The menu/battle NAME comes from a ``CharacterDefaultName <id> <SYM> <name>`` DictionaryPatch directive
    (``DataPatchers`` patches ``CharacterNamesFormatter.DefaultNamesByLang`` at launch, no 0-11 clamp).
  * Recruit is pure ``.eb``: ``B_PARTYADD`` (op 0x6D) with the new id -> the party. Author it with ``recruit =
    true`` here, or ``[party] add = ["<name>"]`` / ``[party] add = [12]``.

This block DEFINES the character (mod-global -- put it on the ENTRY field, like ``[[equipment]]``). It clones a
base character 0-11 (``borrow``) for the stat/identity/model bytes -- so a minimal ``[[playable]]`` is a fully
working, fightable, save-persistent party member -- then applies the author's overrides on top.

    [[playable]]
    id     = 12          # optional; default 12 (the first free slot). Band 12-15 (12 is in-game-proven).
    name   = "Marcus"    # the menu/battle name -> CharacterDefaultName for every language
    borrow = "vivi"      # a base character 0-11 to clone stats / command-set / equip-set / battle-model from
    recruit = true       # optional: also ADD this character to the party at THIS field's load (a one-block proof)
    names  = { jp = "マーカス" }              # optional per-language names (unlisted langs fall back to `name`)
    stats  = { strength = 24, magic = 30 }   # optional BaseStats overrides (same keys as [[character]])
    params = { equip_set = "vivi" }          # optional CharacterParameters overrides (same keys as [[character_param]])

Caveats carried by the recon (do NOT open the in-game name-entry screen for the custom char -- its name comes
from the DictionaryPatch; and FF9 renders only the party LEADER in fields, so the 13th shows in the menu/battle,
not as a walking field follower). See ``project-ff9-13th-character`` and ``project-ff9-pc-party-system``.
"""
from __future__ import annotations

from ..config import LANGS
from ..battle import characterdelta as _cd
from . import equipment as _eqp
from . import portrait as _portrait


class PlayableError(ValueError):
    pass


def _lang_symbol(lang: str) -> str:
    """A kit lang code (lowercase ``us``/``jp``/...) -> the engine ``DefaultNamesByLang`` symbol (uppercase
    ``US``/``JP``/...). The 7 symbols are US/UK/JP/GR/FR/IT/ES (``CharacterNamesFormatter.cs``)."""
    return str(lang).upper()


def _default_name_keyword(nid: int) -> str:
    """A UNIQUE ``NameKeyword`` for the custom char. The engine registers ``NameKeyword -> Id``
    (``RegisterCustomNameKeywork``), so reusing the donor's keyword would collide with the donor's own text tag
    -> generate a distinct 4-char token (matches the CSV String column)."""
    return f"CU{nid:02d}"          # e.g. CU12 -- distinct from every base keyword (ZDNE/VIVI/...)


# the custom battle-model defaults: a MINT id (>=6000, per character) + a BattleParameters serial (>=19).
_BATTLE_MODEL_MINT_BASE = 6100     # id 12 -> mint GEO 6100, id 13 -> 6101, ... (clear of the generic [[mint]] band base)
_BATTLE_SERIAL_BASE = 19           # id 12 -> serial 19, ... (0-18 are the base game's)


def _battle_model_id(val, nid: int) -> int:
    """The minted battle-model GEO id for the custom look (default per character; >= 6000)."""
    if val is None:
        return _BATTLE_MODEL_MINT_BASE + (nid - _cd.CUSTOM_CHAR_MIN)
    if isinstance(val, bool) or not isinstance(val, (int, str)) or not str(val).strip().lstrip("-").isdigit():
        raise PlayableError(f"[[playable]] id {nid}: battle_model_id must be an integer >= 6000")
    v = int(val)
    if v < 6000:
        raise PlayableError(f"[[playable]] id {nid}: battle_model_id {v} is below the mint band 6000")
    return v


def _battle_serial(val, nid: int) -> int:
    """The new BattleParameters serial for the custom look (default per character; >= 19)."""
    if val is None:
        return _BATTLE_SERIAL_BASE + (nid - _cd.CUSTOM_CHAR_MIN)
    if isinstance(val, bool) or not isinstance(val, (int, str)) or not str(val).strip().lstrip("-").isdigit():
        raise PlayableError(f"[[playable]] id {nid}: battle_serial must be an integer >= 19")
    v = int(val)
    if v < 19:
        raise PlayableError(f"[[playable]] id {nid}: battle_serial {v} is below 19 (0-18 are the base game's)")
    return v


def parse_playable(entry, *, n: int = 0) -> dict:
    """One ``[[playable]]`` table -> a normalized spec, or raise :class:`PlayableError`. Pure (no install):
    ``{id, name, names:{SYM: str for every language}, borrow_id, stats:{}, params:{}, recruit:bool}``."""
    if not isinstance(entry, dict):
        raise PlayableError(f"[[playable]] #{n} must be a table (id / name / borrow ...)")
    try:
        nid = _cd._resolve_new_char_id(entry.get("id", _cd.CUSTOM_CHAR_MIN), "[[playable]]")
    except _cd.CharacterDeltaError as ex:
        raise PlayableError(str(ex))
    name = entry.get("name")
    if not (isinstance(name, str) and name.strip()):
        raise PlayableError(f"[[playable]] id {nid} needs a 'name' (the menu/battle name)")
    name = " ".join(name.split())
    # The name lands in the BaseStats.csv Comment column (col 0, BEFORE the Id column) and the CharacterParameters
    # trailing comment, so a ';' (the CSV delimiter) would shift the Id column -> the engine's Byte.Parse throws
    # -> a hard boot ConfirmQuit; a leading '#' (the comment marker) would drop the whole BaseStats row -> the
    # 13th char loads with no base stats. Reject both up front (mirrors _encode_param's ';' guard for String cols).
    if ";" in name or "#" in name:
        raise PlayableError(f"[[playable]] id {nid}: name {name!r} can't contain ';' or '#' -- they collide with "
                            f"the CSV delimiter / comment marker and would corrupt the character's data row")
    borrow = entry.get("borrow")
    if borrow is None:
        raise PlayableError(f"[[playable]] id {nid} needs a 'borrow' (a base character 0-11 to clone from)")
    try:
        borrow_id = _cd._resolve_char_id(borrow)
    except _cd.CharacterDeltaError:
        raise PlayableError(f"[[playable]] id {nid}: borrow {borrow!r} is not a base character (a name "
                            f"Zidane..Beatrix or a 0-11 id)")
    # per-language names: `name` for every symbol, then overridden by `names = { us = ..., jp = ... }`
    names = {_lang_symbol(l): name for l in LANGS}
    raw_names = entry.get("names")
    if raw_names is not None:
        if not isinstance(raw_names, dict):
            raise PlayableError(f"[[playable]] id {nid}: 'names' must be a table (e.g. names = {{ jp = \"...\" }})")
        for k, v in raw_names.items():
            sym = _lang_symbol(k)
            if sym not in names:
                raise PlayableError(f"[[playable]] id {nid}: unknown language {k!r} in 'names' "
                                    f"(use one of {', '.join(sorted(LANGS))})")
            if not (isinstance(v, str) and v.strip()):
                raise PlayableError(f"[[playable]] id {nid}: names.{k} must be a non-empty string")
            names[sym] = " ".join(v.split())
    stats = entry.get("stats") or {}
    params = entry.get("params") or {}
    if not isinstance(stats, dict):
        raise PlayableError(f"[[playable]] id {nid}: 'stats' must be a table (strength = 24, ...)")
    if not isinstance(params, dict):
        raise PlayableError(f"[[playable]] id {nid}: 'params' must be a table (equip_set = \"vivi\", ...)")
    # offline key checks (typos caught by lint without the install; value/range resolution is at build)
    for k in stats:
        if k not in _cd.CHARACTER_FIELDS:
            raise PlayableError(f"[[playable]] id {nid} stats: unknown field {k!r} (known: "
                                f"{', '.join(sorted(set(s[0] for s in _cd.CHARACTER_FIELDS.values())))})")
    for k in params:
        if k not in _cd.CHARACTER_PARAM_FIELDS:
            raise PlayableError(f"[[playable]] id {nid} params: unknown field {k!r} "
                                f"(known: {', '.join(sorted(_cd.CHARACTER_PARAM_FIELDS))})")
    params = dict(params)
    # equip_set / equipment_set is a numeric EquipmentSetId; accept a character NAME too (like `borrow`/`preset`),
    # resolving it to the id here so the CSV writer still gets an int (else a `equip_set = "vivi"` would only fail
    # at build with an unhelpful "must be an integer").
    for _k in ("equip_set", "equipment_set"):
        v = params.get(_k)
        if isinstance(v, str) and not v.strip().lstrip("-").isdigit():
            try:
                params[_k] = _eqp.resolve_set_id(v)
            except (ValueError, TypeError) as ex:
                raise PlayableError(f"[[playable]] id {nid} params {_k}: {ex}")
    params.setdefault("name_keyword", _default_name_keyword(nid))     # a unique tag by default
    recruit = entry.get("recruit", False)
    if not isinstance(recruit, bool):
        raise PlayableError(f"[[playable]] id {nid}: 'recruit' must be true/false")
    # custom battle look (mint an independent editable model) and/or a custom menu PORTRAIT -- either needs a NEW
    # BattleParameters serial row (the ModelId + AvatarSprite live there). Sets serial_formula to the new serial.
    custom_battle = entry.get("custom_battle_model", False)
    if not isinstance(custom_battle, bool):
        raise PlayableError(f"[[playable]] id {nid}: 'custom_battle_model' must be true/false")
    # give the MINTED battle model its own independent, editable animset (else it shares the donor's clips by name)
    custom_anims = entry.get("custom_battle_anims", False)
    if not isinstance(custom_anims, bool):
        raise PlayableError(f"[[playable]] id {nid}: 'custom_battle_anims' must be true/false")
    if custom_anims and not custom_battle:
        raise PlayableError(f"[[playable]] id {nid}: custom_battle_anims needs custom_battle_model = true "
                            f"(the independent animset binds to the MINTED battle model's own id)")
    # persist Blender edits: a .glb (from `playable-anims --export`, edited) the BUILD ships onto the animset, so
    # the edits survive a re-deploy (vs the quick `playable-anims --edit` which is wiped by the next deploy).
    anim_edits = entry.get("anim_edits")
    if anim_edits is not None:
        if not (isinstance(anim_edits, str) and anim_edits.strip()):
            raise PlayableError(f"[[playable]] id {nid}: 'anim_edits' must be a path to a Blender-edited .glb")
        if not custom_anims:
            raise PlayableError(f"[[playable]] id {nid}: anim_edits needs custom_battle_anims = true "
                                f"(it edits that minted animset)")
    portrait = entry.get("portrait")                       # a custom avatar image (path to a 132x190 PNG)
    if portrait is not None and not (isinstance(portrait, str) and portrait.strip()):
        raise PlayableError(f"[[playable]] id {nid}: 'portrait' must be a path to a PNG image")
    needs_serial = custom_battle or portrait is not None
    battle_model_id = None
    battle_serial = None
    battle_borrow_serial = None
    avatar = None
    battle_model_from = entry.get("battle_model_from")
    if battle_model_from is not None and not (isinstance(battle_model_from, str) and battle_model_from.strip()):
        raise PlayableError(f"[[playable]] id {nid}: 'battle_model_from' must be a GEO name")
    if custom_battle:
        battle_model_id = _battle_model_id(entry.get("battle_model_id"), nid)
    elif entry.get("battle_model_id") is not None or battle_model_from:
        raise PlayableError(f"[[playable]] id {nid}: battle_model_id/battle_model_from need custom_battle_model = true")
    if needs_serial:
        battle_serial = _battle_serial(entry.get("battle_serial"), nid)
        bbs = entry.get("battle_borrow_serial")            # a donor BattleParameters serial (0-18) to clone from
        if bbs is not None:
            if isinstance(bbs, bool) or not isinstance(bbs, (int, str)) or not str(bbs).strip().lstrip("-").isdigit():
                raise PlayableError(f"[[playable]] id {nid}: battle_borrow_serial must be an integer serial 0-18")
            battle_borrow_serial = int(bbs)
            if not 0 <= battle_borrow_serial <= 18:
                raise PlayableError(f"[[playable]] id {nid}: battle_borrow_serial {battle_borrow_serial} "
                                    f"out of range (0-18, a base game serial)")
        if portrait is not None:
            avatar = _portrait.sprite_name(nid)            # the atlas sprite name for this character's portrait
        # point the character's battle model/portrait at the new serial (a params override; the new-row build wins)
        if "serial_formula" in params and str(params["serial_formula"]).strip() != str(battle_serial):
            raise PlayableError(f"[[playable]] id {nid}: params.serial_formula collides with custom_battle_model/"
                                f"portrait (which set serial {battle_serial}) -- drop the explicit serial_formula")
        params["serial_formula"] = str(battle_serial)
    elif entry.get("battle_serial") is not None or entry.get("battle_borrow_serial") is not None:
        raise PlayableError(f"[[playable]] id {nid}: battle_serial/battle_borrow_serial need "
                            f"custom_battle_model = true or portrait")
    # [playable.abilities] -- give the character its OWN CharacterPresetId (a custom band 20-23): its own battle
    # command MENU + its own learnable ability list, cloned from a base donor preset (project-ff9-ability-preset-
    # system). ZERO-DLL: a custom preset resolves to a numeric Abilities/<id>.csv + a merged CommandSets row.
    ability_preset_id = ability_menu_from = ability_slots = ability_learn = None
    minted_commands = []
    ab = entry.get("abilities")
    if ab is not None:
        if not isinstance(ab, dict):
            raise PlayableError(f"[[playable]] id {nid}: 'abilities' must be a table ([playable.abilities])")
        ptok = ab.get("preset", "custom")
        if isinstance(ptok, str) and ptok.strip().lower() == "custom":
            ability_preset_id = _cd._PRESET_CUSTOM_MIN + (nid - _cd.CUSTOM_CHAR_MIN)   # 12->20, 13->21, ...
        else:
            try:
                ability_preset_id, _ = _cd._resolve_preset(ptok, f"[[playable]] id {nid} abilities.preset")
            except _cd.CharacterDeltaError as ex:
                raise PlayableError(str(ex))
            if not _cd._PRESET_CUSTOM_MIN <= ability_preset_id <= _cd._PRESET_CUSTOM_MAX:
                raise PlayableError(f"[[playable]] id {nid}: abilities.preset must be \"custom\" or a custom-band id "
                                    f"{_cd._PRESET_CUSTOM_MIN}-{_cd._PRESET_CUSTOM_MAX} (a base 0-19 is a canon char's)")
        mf = ab.get("menu_from")                           # base donor preset to clone the menu + seed the learn list
        if mf is None:
            # default = the borrow donor's preset -- valid only for the 8 MAIN chars (CharacterId 0-7 == PresetId);
            # a guest (8-11) has a DIFFERENT preset id, so require an explicit menu_from rather than silently misalign.
            if borrow_id > 7:
                raise PlayableError(f"[[playable]] id {nid}: abilities.menu_from is required when borrow is a guest "
                                    f"(CharacterId {borrow_id}) -- set it to a base preset 0-15 (a canon caster/"
                                    f"fighter) to clone the command menu + seed the learn list")
            mf = borrow_id
        try:
            mf_id, mf_name = _cd._resolve_preset(mf, f"[[playable]] id {nid} abilities.menu_from")
        except _cd.CharacterDeltaError:
            raise PlayableError(f"[[playable]] id {nid}: abilities.menu_from {mf!r} is not a base preset -- "
                                f"set menu_from to a canon character/preset (0-15) to clone the menu + learn list")
        if not 0 <= mf_id <= 15:                            # Stage presets 16-19 have a CommandSet but NO Abilities file
            raise PlayableError(f"[[playable]] id {nid}: abilities.menu_from must be a base preset 0-15 (a canon "
                                f"character with a learn file to seed from; Stage presets 16-19 have none)")
        ability_menu_from = (mf_id, mf_name)
        ability_slots, minted_commands = {}, []
        for key, slot in (("command1", "ability1"), ("command2", "ability2"),
                          ("command1_trance", "ability1_trance"), ("command2_trance", "ability2_trance")):
            val = ab.get(key)
            if val is None:
                continue
            if isinstance(val, dict):                      # an inline table -> MINT a unique command with its OWN pool
                if key.endswith("_trance"):
                    raise PlayableError(f"[[playable]] id {nid}: abilities.{key} can't mint a command -- put the "
                                        f"inline command table on command1/command2 (it auto-applies in trance too)")
                mc = _parse_minted_command(val, nid, key)
                mc["slot"] = slot                          # ability1/ability2; the id + trance mirror are set in parse_all
                minted_commands.append(mc)
            else:
                try:                                       # resolve offline (a BattleCommandId name/id -> id)
                    _cd._resolve_command(val, f"[[playable]] id {nid} abilities.{key}")
                except _cd.CharacterDeltaError as ex:
                    raise PlayableError(str(ex))
                ability_slots[slot] = val
        ability_slots.setdefault("ability1_trance", ability_slots.get("ability1"))   # trance mirrors the regular slot
        ability_slots.setdefault("ability2_trance", ability_slots.get("ability2"))
        ability_slots = {k: v for k, v in ability_slots.items() if v is not None}
        lrn = ab.get("learn", [])
        if not isinstance(lrn, list):
            raise PlayableError(f"[[playable]] id {nid}: abilities.learn must be a list of {{ ability, ap }} tables")
        for l in lrn:
            if not isinstance(l, dict) or l.get("ability") is None:
                raise PlayableError(f"[[playable]] id {nid}: each abilities.learn entry needs an 'ability'")
        # A minted command's POOL auto-seeds the learn list at ap=0 (learnable/usable NOW) so its menu isn't empty.
        # The seeds are PREPENDED, not appended: build_learn_file resolves every entry to its AA:id token and is
        # last-write-wins, so putting the author's explicit `learn` entries LAST makes them win even when the same
        # ability is written in a DIFFERENT token form (pool "Fire" vs learn "AA:25") -- the documented "explicit ap
        # wins" invariant, which a raw-string dedup alone would miss. (The dedup below still skips a same-FORM repeat.)
        _explicit = {str(l["ability"]).strip().lower() for l in lrn}
        seeds, _seeded = [], set()
        for mc in minted_commands:
            for a in mc["abilities"]:
                if isinstance(a, dict):                    # a custom ability -> allocated + auto-learned in parse_all
                    continue
                key = str(a).strip().lower()
                if key not in _explicit and key not in _seeded:
                    seeds.append({"ability": a, "ap": 0})
                    _seeded.add(key)
        ability_learn = seeds + list(lrn)
        if params.get("menu_type") is not None or params.get("preset") is not None:
            raise PlayableError(f"[[playable]] id {nid}: [playable.abilities] owns the preset -- drop the explicit "
                                f"params.menu_type/preset")
        params["menu_type"] = ability_preset_id            # point CharacterParameters col-4 at the custom preset
    return {"id": nid, "name": name, "names": names, "borrow_id": borrow_id,
            "stats": dict(stats), "params": params, "recruit": recruit, "portrait": portrait, "avatar": avatar,
            "custom_battle_model": custom_battle, "custom_battle_anims": custom_anims, "anim_edits": anim_edits,
            "battle_model_id": battle_model_id,
            "battle_serial": battle_serial, "battle_model_from": battle_model_from,
            "battle_borrow_serial": battle_borrow_serial,
            "ability_preset_id": ability_preset_id, "ability_menu_from": ability_menu_from,
            "ability_slots": ability_slots, "ability_learn": ability_learn,
            "minted_commands": minted_commands}


def _parse_minted_command(val, nid, key) -> dict:
    """An inline ``command1``/``command2`` table -> a minted-command spec ``{name, abilities}``. A unique battle
    command with its OWN ability pool (project-ff9-ability-preset-system): the id is allocated + the trance slot
    mirrored in :func:`parse_all`."""
    name = val.get("name")
    if not isinstance(name, str) or not name.strip():
        raise PlayableError(f"[[playable]] id {nid}: abilities.{key} (an inline command) needs a 'name'")
    abils = val.get("abilities")
    if not isinstance(abils, list) or not abils:
        raise PlayableError(f"[[playable]] id {nid}: abilities.{key} command {name!r} needs a non-empty 'abilities' "
                            f"pool (a list of ability names/ids, e.g. [\"Fire\", \"Cure\"])")
    pool = []
    for a in abils:
        if isinstance(a, dict):                            # an inline table -> MINT a custom ability (its own behaviour)
            pool.append({"__custom__": _parse_custom_ability(a, nid, key, name.strip())})
            continue
        if a is None or isinstance(a, bool) or (isinstance(a, str) and not a.strip()):
            raise PlayableError(f"[[playable]] id {nid}: abilities.{key} command {name!r} has an empty ability in its pool")
        # a BARE id must be a stock ability (0-191); a custom ability (192+) is only mintable via an inline table.
        if (isinstance(a, int) and a >= 192) or (isinstance(a, str) and a.strip().lstrip("-").isdigit() and int(a) >= 192):
            raise PlayableError(f"[[playable]] id {nid}: abilities.{key} command {name!r}: a bare ability id >=192 "
                                f"must be MINTED via an inline table {{ name, from }} -- bare ids are stock 0-191")
        pool.append(a)
    extra = set(val) - {"name", "abilities"}
    if extra:
        raise PlayableError(f"[[playable]] id {nid}: abilities.{key} command {name!r} has unknown key(s) "
                            f"{sorted(extra)} (only 'name' and 'abilities')")
    return {"name": name.strip(), "abilities": pool}


def _parse_field_spec(fld, nid, aname, _ss) -> dict:
    """Parse a custom ability's ``script.field`` (a PAIRED field-menu effect) -> ``{template}`` or ``{body}``
    (project-ff9-scripts-dll P7). Mirrors the battle ``script`` validation against ``scriptsource.FIELD_TEMPLATES``."""
    if not isinstance(fld, dict):
        raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} script.field must be a table "
                            f"{{ template = \"...\" }} or {{ body = \"<C#>\" }}")
    if fld.get("body") is not None:
        fbody = fld.get("body")
        if not isinstance(fbody, str) or not fbody.strip():
            raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} script.field.body must be a "
                                f"non-empty C# Apply() body string")
        return {"body": fbody}
    ftmpl = fld.get("template")
    if not isinstance(ftmpl, str) or ftmpl not in _ss.FIELD_TEMPLATES:
        raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} script.field.template must be one of "
                            f"{sorted(_ss.FIELD_TEMPLATES)} (or set script.field.body = \"<C# Apply() body>\")")
    return {"template": ftmpl}


def _parse_status_spec(s, nid, aname) -> dict:
    """A custom-status table item in an ability's ``status = [...]`` -> ``{name, template?/body?/hooks?}`` (a minted
    ``[StatusScript]`` behaviour). Mirrors :func:`_parse_field_spec` (project-ff9-scripts-dll P7)."""
    from ..battle import scriptsource as _ss
    name = s.get("name")
    if not isinstance(name, str) or not name.strip():
        raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} custom status needs a 'name' "
                            f"(e.g. status = [{{ name = \"Rebirth\", template = \"auto_life\" }}])")
    out = {"name": name.strip()}
    if s.get("body") is not None:
        body = s.get("body")
        if not isinstance(body, str) or not body.strip():
            raise PlayableError(f"[[playable]] id {nid}: custom status {name!r} body must be a non-empty C# class-body")
        hooks = s.get("hooks") or []
        if not isinstance(hooks, list) or any(not isinstance(h, str) or h not in _ss.STATUS_HOOKS for h in hooks):
            raise PlayableError(f"[[playable]] id {nid}: custom status {name!r} body needs hooks = a list of "
                                f"{sorted(_ss.STATUS_HOOKS)} (the lifecycle interfaces it implements)")
        out["body"], out["hooks"] = body, list(hooks)
    else:
        tmpl = s.get("template")
        if not isinstance(tmpl, str) or tmpl not in _ss.STATUS_TEMPLATES:
            raise PlayableError(f"[[playable]] id {nid}: custom status {name!r} template must be one of "
                                f"{sorted(_ss.STATUS_TEMPLATES)} (or set body = \"<C#>\" + hooks = [...])")
        out["template"] = tmpl
    icon = s.get("icon")                                   # explicit override, else the template's default HUD icon
    if icon is None and out.get("template"):
        icon = _ss.STATUS_TEMPLATES[out["template"]].get("icon")
    if icon is not None:                                   # borrow a vanilla status's HUD icon (a DictionaryPatch line)
        if not isinstance(icon, str) or icon.strip().lower() not in _ss._STATUS_ICON_DONORS:
            raise PlayableError(f"[[playable]] id {nid}: custom status {name!r} icon must be a vanilla status name to "
                                f"borrow its HUD icon from (e.g. \"AutoLife\", \"Regen\", \"Berserk\")")
        out["icon"] = icon.strip()
    pw = s.get("power")                                    # a template knob (auto_life: revive % of max HP)
    if pw is not None:
        if isinstance(pw, bool) or not isinstance(pw, int) or not 1 <= pw <= 100:
            raise PlayableError(f"[[playable]] id {nid}: custom status {name!r} power must be an integer 1-100 "
                                f"(for auto_life it's the revive % of max HP, e.g. power = 50)")
        out["power"] = pw
    over = s.get("over_model")                             # the ON-MODEL visual (particle/over-model chevron/tint)
    if over is None:
        over = out.get("icon")                             # default: match the panel-icon donor (AutoLife has none)
    if over is not None:                                   # borrow a vanilla status's on-model visual (SPS/SHP/Color)
        from ..battle import battlecsv as _bc
        if not isinstance(over, str) or over.strip().lower() not in {n.lower() for _, n in _bc.STATUSES}:
            raise PlayableError(f"[[playable]] id {nid}: custom status {name!r} over_model must be a vanilla status "
                                f"name to borrow its on-model visual (e.g. \"Haste\"/\"Slow\" [chevron], \"Berserk\")")
        out["over_model"] = over.strip()
    return out


def _parse_custom_ability(a, nid, key, cmd_name) -> dict:
    """An inline pool table -> a custom-ability spec ``{name, from, overrides}``. A UNIQUE spell that clones a stock
    donor (``from``) and retunes it (project-ff9-ability-preset-system). The id is allocated (the 192+ band) + the
    ability auto-learned in :func:`parse_all`; the overrides' values are range-checked at build (they need the install
    to read the donor row)."""
    aname = a.get("name")
    if not isinstance(aname, str) or not aname.strip():
        raise PlayableError(f"[[playable]] id {nid}: a custom ability in abilities.{key} ({cmd_name!r}) needs a 'name'")
    if ";" in aname or aname.lstrip().startswith("#"):
        raise PlayableError(f"[[playable]] id {nid}: custom ability name {aname!r} can't contain ';' or start with '#'")
    donor = a.get("from")
    if donor is None or isinstance(donor, bool) or (isinstance(donor, str) and not donor.strip()):
        raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} needs 'from' = a stock ability to clone "
                            f"(its animation + damage formula; e.g. from = \"Fire\")")
    # `status = [names]` (auto-minted into a StatusSets row + the action's status_index) and `effect` = a "[code=...]"
    # AbilityFeatures body are NOT Actions.csv columns -- pull them out; everything else is an ACTION_FIELDS override.
    status = a.get("status")
    status_names, custom_statuses = [], []     # existing-status name strings / minted custom-behaviour status tables
    if status is not None:
        if not isinstance(status, list) or not status:
            raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} status must be a non-empty list of "
                                f"status names and/or custom-status tables (e.g. status = [\"Silence\"] or "
                                f"status = [{{ name = \"Rebirth\", template = \"auto_life\" }}])")
        for s in status:
            if isinstance(s, str) and s.strip():
                status_names.append(s)
            elif isinstance(s, dict):                      # a custom-behaviour status (minted [StatusScript]) (P7)
                custom_statuses.append(_parse_status_spec(s, nid, aname.strip()))
            else:
                raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} status entry {s!r} must be a "
                                    f"status name or a {{ name, template/body }} table")
        if status_names:                                   # validate the existing names offline (a typo fails lint)
            try:
                from ..battle import battlecsv as _bc
                _bc.encode_status_list(status_names)
            except (ValueError, TypeError) as ex:
                raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} status: {ex}")
    eff_keys = [k for k in ("effect", "code", "feature") if a.get(k) is not None]
    if len(eff_keys) > 1:
        raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r}: set only one of effect/code/feature")
    effect = None
    if eff_keys:
        effect = a.get(eff_keys[0])
        if not isinstance(effect, str) or not effect.strip():
            raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} {eff_keys[0]} must be a non-empty "
                                f"\"[code=...]\" string")
        # structure-check the [code=...] body OFFLINE (balanced tags, a known AA [code=TAG], single-line) so `lint`
        # catches a malformed effect -- else the build is the first to reject it. (The id is a placeholder; the real
        # one is allocated in parse_all. The NCalc formula stays opaque -- the engine validates it.)
        from ..battle import abilityfeatures as _af
        _probs = _af.validate_blocks([{"kind": "AA", "ability": _cd._MAX_ACTIVE_ABILITY, "features": effect}])
        if _probs:
            raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} {eff_keys[0]}: {_probs[0]}")
    # `script = {template = "..."}` (or `{body = "<C#>"}`) -> a MINTED battle FORMULA (a Memoria.Scripts.<Mod>.dll
    # BattleScript, id 256+; project-ff9-scripts-dll) -- a behaviour the data path can't express (drain, %-max-HP,
    # ...). A SCALAR `script` (an existing scriptId int/name) is NOT pulled out: it stays an ACTION_FIELDS override
    # that re-points at an EXISTING (0-191) formula (data-only, no DLL). The real id is allocated in parse_all.
    script_spec = None
    sc = a.get("script")
    if isinstance(sc, dict):
        from ..battle import scriptsource as _ss
        if sc.get("body") is not None:
            body = sc.get("body")
            if not isinstance(body, str) or not body.strip():
                raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} script.body must be a "
                                    f"non-empty C# Perform() body string")
            script_spec = {"body": body}
        elif sc.get("template") is not None:
            tmpl = sc.get("template")
            if tmpl not in _ss.TEMPLATES:
                raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} script.template must be one of "
                                    f"{sorted(_ss.TEMPLATES)} (or set script.body = \"<C# Perform() body>\")")
            script_spec = {"template": tmpl}
        # script.field = {template/body} -> a PAIRED field-menu effect at the SAME minted scriptId, so the ability
        # behaves both IN and OUT of combat. It requires the battle half (a field-only effect isn't supported yet --
        # a stock field scriptId would clobber a vanilla effect globally). project-ff9-scripts-dll (P7).
        fld = sc.get("field")
        if fld is not None:
            if script_spec is None:
                raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} script.field needs a paired "
                                    f"battle formula (set script.template or script.body too) -- they share one "
                                    f"minted scriptId; a field-only effect isn't supported yet")
            script_spec["field"] = _parse_field_spec(fld, nid, aname.strip(), _ss)
        if script_spec is None:
            raise PlayableError(f"[[playable]] id {nid}: custom ability {aname!r} script table must set a template "
                                f"or body (or use a scalar script = <id> to reuse an existing formula)")
    overrides = {k: v for k, v in a.items()
                 if k not in ("name", "from", "status", "effect", "code", "feature")
                 and not (k == "script" and isinstance(v, dict))}
    return {"name": aname.strip(), "from": donor, "overrides": overrides,
            "status": status_names or None, "effect": effect, "script": script_spec,
            "custom_statuses": custom_statuses}


def parse_all(entries) -> list:
    """A list of ``[[playable]]`` tables -> ``[spec]``, raising on a duplicate id."""
    if entries is None:
        return []
    if not isinstance(entries, list):
        entries = [entries]
    specs, seen, seen_model, seen_serial, seen_preset = [], {}, {}, {}, {}
    for n, e in enumerate(entries):
        spec = parse_playable(e, n=n)
        if spec["id"] in seen:
            raise PlayableError(f"[[playable]] id {spec['id']} is defined twice (#{seen[spec['id']]} and #{n})")
        seen[spec["id"]] = n
        # A shared battle_model_id would mint two characters into the SAME Models/<id>/ + the SAME animset key band
        # (one would play the other's model/anims); a shared battle_serial would collide their BattleParameters rows.
        mid = spec.get("battle_model_id")
        if mid is not None:
            if mid in seen_model:
                raise PlayableError(f"[[playable]] id {spec['id']}: battle_model_id {mid} is already used by "
                                    f"[[playable]] #{seen_model[mid]} -- each custom character needs its own "
                                    f"(default is 6100 + the character's slot; drop the explicit value or change it)")
            seen_model[mid] = n
        sid = spec.get("battle_serial")
        if sid is not None:
            if sid in seen_serial:
                raise PlayableError(f"[[playable]] id {spec['id']}: battle_serial {sid} is already used by "
                                    f"[[playable]] #{seen_serial[sid]} -- each needs its own (default 19 + slot)")
            seen_serial[sid] = n
        pre = spec.get("ability_preset_id")               # a shared custom preset would collide the CommandSets row + learn file
        if pre is not None:
            if pre in seen_preset:
                raise PlayableError(f"[[playable]] id {spec['id']}: abilities preset {pre} is already used by "
                                    f"[[playable]] #{seen_preset[pre]} -- each needs its own (default 20 + slot)")
            seen_preset[pre] = n
        specs.append(spec)
    # allocate custom-band ids for any minted unique commands (dedup across ALL specs -> a distinct Commands.csv id
    # each), then wire each into its CommandSet slot + mirror it to the trance slot (unless the author pinned one).
    cmd_alloc = 0
    for spec in specs:
        for mc in spec.get("minted_commands", []):
            if cmd_alloc >= len(_cd._CMD_CUSTOM_BAND):
                raise PlayableError(f"[[playable]] too many minted commands: the custom command band "
                                    f"{list(_cd._CMD_CUSTOM_BAND)} ({len(_cd._CMD_CUSTOM_BAND)} slots) is exhausted")
            cid = _cd._CMD_CUSTOM_BAND[cmd_alloc]
            cmd_alloc += 1
            mc["id"] = cid
            spec["ability_slots"][mc["slot"]] = cid              # ability1/ability2 -> the minted command id
            spec["ability_slots"].setdefault(mc["slot"] + "_trance", cid)   # trance mirrors unless explicitly set
    # allocate the custom-ABILITY band (192+) for inline custom spells in the command pools (dedup across ALL specs):
    # rewrite each pool marker -> its allocated int id, collect the Actions.csv new-rows, and auto-learn each (ap=0).
    from ..battle import actiondelta as _ad
    act_alloc = _ad._CUSTOM_ACTION_MIN
    script_alloc = _ad._CUSTOM_SCRIPT_MIN                     # a minted battle FORMULA's scriptId (256+, dict band)
    status_set_ids: dict = {}                                # a status-name-list -> a shared minted StatusSets id (dedup)
    status_alloc = _ad._CUSTOM_STATUS_MIN                    # a minted custom STATUS's BattleStatusId (33-63)
    custom_status_ids: dict = {}                             # a custom-status NAME -> (id, enum) (dedup across specs)
    custom_status_defs: dict = {}                            # a custom-status NAME -> its defining table (collision check)
    _STATUS_DEF_KEYS = ("template", "body", "hooks", "icon", "power", "over_model")
    for spec in specs:
        for mc in spec.get("minted_commands", []):
            new_pool = []
            for a in mc["abilities"]:
                if isinstance(a, dict) and "__custom__" in a:
                    if act_alloc > _ad._CUSTOM_ACTION_MAX:
                        raise PlayableError(f"[[playable]] too many custom abilities: the custom-ability band "
                                            f"{_ad._CUSTOM_ACTION_MIN}-{_ad._CUSTOM_ACTION_MAX} is exhausted")
                    ca = dict(a["__custom__"])
                    ca["id"] = act_alloc
                    act_alloc += 1
                    for cs in ca.get("custom_statuses", []):      # status = [{name, template/body}] -> a minted [StatusScript]
                        ckey = cs["name"].strip().lower()
                        ent = custom_status_ids.get(ckey)
                        if ent is not None:
                            prior = custom_status_defs[ckey]
                            if any(cs.get(k) != prior.get(k) for k in _STATUS_DEF_KEYS):
                                raise PlayableError(f"[[playable]] custom status {cs['name']!r} is defined twice with "
                                                    f"different template/body/hooks/power/icon/over_model -- give the "
                                                    f"redefinition its own name or make both definitions identical")
                        if ent is None:
                            if status_alloc > _ad._CUSTOM_STATUS_MAX:
                                raise PlayableError(f"[[playable]] too many custom statuses: the band "
                                                    f"{_ad._CUSTOM_STATUS_MIN}-{_ad._CUSTOM_STATUS_MAX} is exhausted")
                            enum = f"CustomStatus{status_alloc - _ad._CUSTOM_STATUS_MIN + 1}"
                            ent = custom_status_ids[ckey] = (status_alloc, enum)
                            custom_status_defs[ckey] = cs
                            spec.setdefault("minted_status_scripts", []).append(
                                {"id": status_alloc, "status_enum": enum, "name": cs["name"],
                                 **{k: v for k, v in cs.items() if k in ("template", "body", "hooks", "icon", "power")}})
                            spec.setdefault("minted_status_data", []).append(
                                {"id": status_alloc, "name": cs["name"],
                                 **({"over_model": cs["over_model"]} if cs.get("over_model") else {})})
                            status_alloc += 1
                        if ca.get("status") is None:              # inflict it via THIS ability's StatusSets row (below)
                            ca["status"] = []
                        if ent[1] not in ca["status"]:
                            ca["status"].append(ent[1])
                    if ca.get("status"):                         # status = [...] -> an auto-minted StatusSets row +
                        skey = tuple(sorted(s.strip().lower() for s in ca["status"]))   # a dedup key (shared row)
                        sid = status_set_ids.get(skey)
                        if sid is None:
                            sid = _ad._CUSTOM_STATUS_SET_MIN + len(status_set_ids)
                            status_set_ids[skey] = sid
                            spec.setdefault("minted_status_sets", []).append(
                                {"id": sid, "name": ca["name"], "statuses": list(ca["status"])})
                        ca["status_index"] = sid                 # the kit-trusted status_index (the row exists this build)
                    if ca.get("effect"):                         # effect = "[code=...]" -> an [[ability_feature]] block
                        spec.setdefault("minted_features", []).append(
                            {"kind": "AA", "ability": ca["id"], "features": ca["effect"], "comment": ca["name"]})
                    if ca.get("script"):                         # script = {template/body} -> a minted battle FORMULA
                        if script_alloc > _ad._CUSTOM_SCRIPT_MAX:  # a Memoria.Scripts.<Mod>.dll [BattleScript(256+)]
                            raise PlayableError(f"[[playable]] too many scripted abilities: the custom-script band "
                                                f"{_ad._CUSTOM_SCRIPT_MIN}-{_ad._CUSTOM_SCRIPT_MAX} is exhausted")
                        ca["script_id"] = script_alloc           # repoint the Actions.csv scriptId at the minted formula
                        script_alloc += 1
                        _scd = ca["script"]
                        spec.setdefault("minted_scripts", []).append(        # the BATTLE formula (drop the field half)
                            {"id": ca["script_id"], "name": ca["name"],
                             **{k: v for k, v in _scd.items() if k != "field"}})
                        if _scd.get("field"):                    # script.field -> a PAIRED field effect at the SAME id
                            spec.setdefault("minted_field_scripts", []).append(
                                {"id": ca["script_id"], "name": ca["name"], **_scd["field"]})
                    spec.setdefault("minted_actions", []).append(ca)
                    new_pool.append(ca["id"])                    # the pool's ListEntry references the allocated int id
                    # learn it at ap=0 (usable now). PREPEND (like the stock pool seeds) so an explicit `learn` entry
                    # would still win under build_learn_file's last-write-wins -- the "explicit ap wins" invariant.
                    spec["ability_learn"].insert(0, {"ability": f"AA:{ca['id']}", "ap": 0})
                else:
                    new_pool.append(a)
            mc["abilities"] = new_pool
    return specs


def basestats_seeds(specs) -> list:
    """Specs -> the ``new_rows`` for :func:`characterdelta.build_basestats_delta`."""
    return [{"id": s["id"], "borrow": s["borrow_id"], "name": s["name"], "overrides": s["stats"]} for s in specs]


def params_seeds(specs) -> list:
    """Specs -> the ``new_rows`` for :func:`characterdelta.build_character_params_delta`."""
    return [{"id": s["id"], "borrow": s["borrow_id"], "name": s["name"], "overrides": s["params"]} for s in specs]


def command_set_seeds(specs) -> list:
    """Specs with a ``[playable.abilities]`` block -> the ``command_set_new_rows`` for
    :func:`characterdelta.write_character_data`: a NEW custom-preset CommandSets row cloned from ``menu_from`` with
    the author's command-slot picks."""
    return [{"id": s["ability_preset_id"], "clone_from": s["ability_menu_from"][0],
             "slots": s["ability_slots"], "comment": s["name"]}
            for s in specs if s.get("ability_preset_id") is not None]


def learn_seeds(specs) -> list:
    """Specs with a ``[playable.abilities]`` block -> the ``learns_new`` for :func:`characterdelta.write_character_data`:
    the custom preset's ``Abilities/<id>.csv`` learn list, seeded from ``menu_from``'s file."""
    return [{"preset_name": str(s["ability_preset_id"]), "read_from": s["ability_menu_from"][1],
             "abilities": s["ability_learn"] or [], "removes": []}
            for s in specs if s.get("ability_preset_id") is not None]


def command_seeds(specs) -> list:
    """Specs with a minted ``command1``/``command2`` inline table -> the ``new_commands`` for
    :func:`characterdelta.write_character_data`: each unique command's ``Commands.csv`` row + ``com_name.mes`` name
    ({id, name, abilities}). The id is allocated in :func:`parse_all`."""
    return [{"id": mc["id"], "name": mc["name"], "abilities": mc["abilities"]}
            for s in specs for mc in s.get("minted_commands", [])]


def action_seeds(specs) -> list:
    """Specs with an inline CUSTOM ability in a command pool -> the ``new_actions`` for the Actions.csv delta +
    the ``aa_name.mes`` overlay: each ``{id, name, from, overrides, status_index?}`` (a donor clone). The id is
    allocated in :func:`parse_all`."""
    return [ca for s in specs for ca in s.get("minted_actions", [])]


def status_set_seeds(specs) -> list:
    """Specs with a custom ability that inflicts a ``status = [...]`` -> the auto-minted ``StatusSets.csv`` rows
    ({id, name, statuses}) an action's ``status_index`` points at (deduped by status list in :func:`parse_all`).
    Merged with any author ``[[status_set]]`` blocks at build."""
    return [ss for s in specs for ss in s.get("minted_status_sets", [])]


def feature_seeds(specs) -> list:
    """Specs with a custom ability carrying an ``effect`` -> the ``[[ability_feature]]`` blocks
    ({kind:"AA", ability:<custom id>, features:<code>}) merged with any author blocks at build."""
    return [f for s in specs for f in s.get("minted_features", [])]


def script_seeds(specs) -> list:
    """Specs with a custom ability carrying ``script = {template/body}`` -> the minted battle-FORMULA sources
    ({id, name, template?/body?}) that :func:`build._emit_scripts` emits + compiles into
    ``Memoria.Scripts.<Mod>.dll``. The id (256+, the engine's ``BattleExtendedScripts`` floor) is allocated in
    :func:`parse_all` and matches the Actions.csv ``scriptId`` cell that binds it at cast (project-ff9-scripts-dll)."""
    return [sc for s in specs for sc in s.get("minted_scripts", [])]


def field_script_seeds(specs) -> list:
    """Specs with a custom ability carrying ``script.field = {template/body}`` -> the minted FIELD ability-effect
    sources ({id, name, template?/body?}) that :func:`build._emit_scripts` emits as a ``[FieldAbilityScript(id)]``
    into the SAME ``Memoria.Scripts.<Mod>.dll``. The id EQUALS the paired battle formula's scriptId, so the same
    Actions.csv ``scriptId`` cell binds the formula IN combat and the field effect OUT of it (project-ff9-scripts-dll P7)."""
    return [sc for s in specs for sc in s.get("minted_field_scripts", [])]


def status_script_seeds(specs) -> list:
    """Specs with a custom-behaviour status (an ability's ``status = [{template/body}]``) -> the minted
    ``[StatusScript]`` sources ({id, status_enum, name, template?/body?/hooks?}) that :func:`build._emit_scripts`
    compiles into ``Memoria.Scripts.<Mod>.dll``. The id is the BattleStatusId (33-63) allocated in :func:`parse_all`
    (project-ff9-scripts-dll P7); the behaviour hooks fire off the applied-effects dict (per-tick ``OnOpr`` is engine-gated)."""
    return [s for sp in specs for s in sp.get("minted_status_scripts", [])]


def status_data_seeds(specs) -> list:
    """Specs with a custom-behaviour status -> the ``{id, name}`` rows :func:`build._emit_battle_data` mints into a
    ``StatusData.csv`` delta (id 33-63) so the engine can INFLICT the status (else ``statusDatabase[id]`` KeyNotFounds
    at apply, btl_stat.cs:71). The row is inert data; the behaviour is the paired ``[StatusScript]``."""
    return [s for sp in specs for s in sp.get("minted_status_data", [])]


def name_directive_lines(specs) -> list:
    """The mod-global ``CharacterDefaultName <id> <SYM> <name>`` DictionaryPatch lines (one per language),
    ordered by spec then LANGS. DataPatchers reads these at LAUNCH (a relaunch, not the menu reload, applies a name change)."""
    lines = []
    for s in specs:
        for lang in LANGS:
            sym = _lang_symbol(lang)
            lines.append(f"CharacterDefaultName {s['id']} {sym} {s['names'][sym]}")
    return lines


def status_icon_directive_lines(specs) -> list:
    """The mod-global ``BuffIcon``/``DebuffIcon <statusId> <spriteIndex>`` DictionaryPatch lines that give each minted
    custom status a HUD icon (borrowing a vanilla status's sprite). DataPatchers registers them at LAUNCH, so the icon
    shows everywhere the engine reads Buff/DebuffIconNames -- the party panel, the target/'hover' status, resists +
    results (project-ff9-scripts-dll P7)."""
    from ..battle import scriptsource as _ss
    lines = []
    for s in status_script_seeds(specs):
        line = _ss.status_icon_directive(s["id"], s.get("icon"))
        if line:
            lines.append(line)
    return lines


def recruit_ids(specs) -> list:
    """The ids that asked to be recruited at their field's load (``recruit = true``)."""
    return [s["id"] for s in specs if s["recruit"]]


def custom_serial_specs(specs) -> list:
    """The specs that need a NEW BattleParameters serial row -- a custom battle MODEL and/or a custom PORTRAIT ->
    ``[{playable_id, name, borrow_id, custom_model, model_id, serial, model_from, borrow_serial, portrait,
    avatar}]``. ``custom_model`` gates the mint; ``portrait``/``avatar`` gate the atlas + the AvatarSprite cell."""
    return [{"playable_id": s["id"], "name": s["name"], "borrow_id": s["borrow_id"],
             "custom_model": bool(s.get("custom_battle_model")),
             "custom_anims": bool(s.get("custom_battle_anims")), "anim_edits": s.get("anim_edits"),
             "model_id": s["battle_model_id"], "serial": s["battle_serial"], "model_from": s["battle_model_from"],
             "borrow_serial": s["battle_borrow_serial"], "portrait": s.get("portrait"), "avatar": s.get("avatar")}
            for s in specs if s.get("custom_battle_model") or s.get("portrait")]


def registry(specs) -> dict:
    """``name (lowercased) -> id`` -- lets ``[party] add = ["<custom name>"]`` recruit a custom character."""
    return {s["name"].lower(): s["id"] for s in specs}


def validate_playable(entry) -> list:
    """Offline structural problems for one ``[[playable]]`` (empty => OK)."""
    try:
        parse_playable(entry)
        return []
    except PlayableError as ex:
        return [str(ex)]
