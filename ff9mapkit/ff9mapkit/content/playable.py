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
    return {"id": nid, "name": name, "names": names, "borrow_id": borrow_id,
            "stats": dict(stats), "params": params, "recruit": recruit, "portrait": portrait, "avatar": avatar,
            "custom_battle_model": custom_battle, "custom_battle_anims": custom_anims,
            "battle_model_id": battle_model_id,
            "battle_serial": battle_serial, "battle_model_from": battle_model_from,
            "battle_borrow_serial": battle_borrow_serial}


def parse_all(entries) -> list:
    """A list of ``[[playable]]`` tables -> ``[spec]``, raising on a duplicate id."""
    if entries is None:
        return []
    if not isinstance(entries, list):
        entries = [entries]
    specs, seen, seen_model, seen_serial = [], {}, {}, {}
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
        specs.append(spec)
    return specs


def basestats_seeds(specs) -> list:
    """Specs -> the ``new_rows`` for :func:`characterdelta.build_basestats_delta`."""
    return [{"id": s["id"], "borrow": s["borrow_id"], "name": s["name"], "overrides": s["stats"]} for s in specs]


def params_seeds(specs) -> list:
    """Specs -> the ``new_rows`` for :func:`characterdelta.build_character_params_delta`."""
    return [{"id": s["id"], "borrow": s["borrow_id"], "name": s["name"], "overrides": s["params"]} for s in specs]


def name_directive_lines(specs) -> list:
    """The mod-global ``CharacterDefaultName <id> <SYM> <name>`` DictionaryPatch lines (one per language),
    ordered by spec then LANGS. DataPatchers reads these at LAUNCH (a relaunch, not F6, applies a name change)."""
    lines = []
    for s in specs:
        for lang in LANGS:
            sym = _lang_symbol(lang)
            lines.append(f"CharacterDefaultName {s['id']} {sym} {s['names'][sym]}")
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
             "custom_anims": bool(s.get("custom_battle_anims")),
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
