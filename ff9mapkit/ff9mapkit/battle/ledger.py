"""``[scene.ledger]`` -- a battle writes a field's PERSISTENT table (studies/fight-ledger/, board entry #4).

An enemy's battle ``.eb`` shares the field's expression layer and vector store (rung 0, in-game 31/31), so its AI
can record how a fight went into a ``persist = true`` ``[[behavior.table]]`` that a field declares -- and the
field that catches the player, or any field later, reads it with the readers it already has (``table_eq`` /
``table_ge`` conditions, ``[[choice]]`` / HUD ``expr:`` values, ``[[text_table]]``). This module turns a
declarative ``[scene.ledger]`` into those AI splices::

    [scene.ledger]
    declared_in = "../village.field.toml"      # the field.toml that DECLARES the table
    table = "goblin_fight"                     # its id, length and check word are READ from there
    [[scene.ledger.write]]
    on = "dying"                               # init (tag 0) | reaction (tag 7) | dying (tag 9)
    slot = 0                                   # which spawned enemy (needs [scene] monster_count)
    cell = 1                                   # a constant index < the table's length ...
    set = "killer"                             # ... or flag = "<[[flag]] name>"; set = int|source, or add = int

THE LAWS, each enforced here and pinned by ``tests/test_battle_ledger.py``:

* **The table keeps its shape.** Every write is an overwrite at a constant index below the declared length, under
  the LIVE GATE (:func:`~ff9mapkit.content.behavior.persist_live_expr`: the guard holds this table's check word AND
  the table is exactly n cells). A battle can never create, append to, or grow the table -- which is what would
  make the declaring field's Main_Init re-seed (wipe) it. A table that was never seeded in this save, re-shaped since
  the battle was built, or owned by someone else is left untouched. ``flag`` rows sit OUTSIDE the gate: a story bit
  cannot append or re-seed anything, so a fight before any declaring field ran still records "it fell".
* **Identity is read, never restated.** id / length / check word / flag indices come from ``declared_in``.
* **Hooks are the engine's.** ``init`` = tag 0 (runs when Main_Init creates the enemy -- BEFORE its battle data is
  bound, so no stat reads), ``reaction`` = tag 7 (after every effect landed on the enemy, misses included),
  ``dying`` = tag 9 (only with ``die_atk``, only a player's killing blow through the damage calculator). The kit
  ORs ``die_atk`` into a ``dying`` row's enemy type, and when tag 9 takes the lethal effect it REPLAYS that slot's
  ``reaction`` rows there first (the engine refuses the lethal hit's tag-7 request -- rung 0 measured it), so a
  hit count never misses the killing blow.
* **Which enemy** is a slot: ``monster_count`` makes slot -> AI entry static (:func:`event_data.resolve_ai_entries`)
  and every row runs behind a self-bit filter (``B_SYSLIST[1] == 16 << slot``), so two slots sharing one AI entry
  write their own rows.
* **Values stay in the persistent fence** (±``ADJUST_MAG_MAX``): integers are checked at build, sources and adds
  are clamped two-sided at run time.

Splices go LAST, after the ``ai_*`` composition, and only at body offset 0 (or as an added function): they move
nothing an ``ai_patch`` offset or an ``ai_insert`` locator points at.
"""
from __future__ import annotations

import difflib
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ..content import behavior as _B
from ..eb import edit as _edit
from ..eb.labelasm import JMP_IFNOT, asm, label
from ..eb.model import EbScript
from . import event_data as _event_data
from . import scene_data as _scene_data


class LedgerError(ValueError):
    pass


HOOK_TAGS = {"init": 0, "reaction": 7, "dying": 9}
LEDGER_KEYS = frozenset({"declared_in", "table", "write"})
# the words an author reaches for -> the hook they mean (the engine-mechanism names are the kit's tag labels)
HOOK_SYNONYMS = {"death": "dying", "die": "dying", "kill": "dying", "killed": "dying", "hit": "reaction",
                 "hits": "reaction", "damage": "reaction", "spawn": "init", "start": "init", "begin": "init"}
WRITE_KEYS = frozenset({"on", "slot", "cell", "flag", "set", "add"})
MAX_WRITES = 64
FENCE = _B.ADJUST_MAG_MAX
MAX_EB = 0xFFFF
# every [scene] key the battle build reads (the ledger's near-miss check must never trip a real one)
KNOWN_SCENE_KEYS = frozenset({
    "ai_function", "ai_insert", "ai_patch", "ai_phase", "ap", "camera", "camera_keyframes", "camera_pitch",
    "camera_yaw", "camera_zoom", "enemy", "flags", "monster_count", "pattern", "seq_insert", "seq_patch",
    "seq_replace", "ledger"})

R_BIND = ("init runs before the engine binds this enemy's battle data (StartEvents runs Init; InitEnemyData "
          "assigns its battle id later), so a member read here finds no unit and returns 0")
R_LEVEL = ("B_SYSVAR[28]/[29] read the TRIGGERING command only at call level <= 2 (reaction = 2, dying = 0); in "
           "init they read the enemy's own current command, which is not bound yet")
R_KILLER = ("B_SYSLIST[0] is the killer only inside dying (the Dying request sets it); in init/reaction it is a "
            "counter caster, the AI's own target pick, or stale")
R_ZERO = "hp inside dying always reads 0 -- use on = \"reaction\" for the HP an effect left (the replay records the lethal 0)"


@dataclass(frozen=True)
class Source:
    rpn: str
    refused: tuple = ()                   # ((hook, reason), ...)

    def why_not(self, hook: str):
        return dict(self.refused).get(hook)


SOURCES = {
    "field": Source("B_SYSVAR[191]"),                                              # fldMapNo: the catching field
    "hp": Source("B_SYSLIST[1] B_MEMBER(36) B_PICK", (("init", R_BIND), ("dying", R_ZERO))),
    "command": Source("B_SYSVAR[28]", (("init", R_LEVEL),)),
    "ability": Source("B_SYSVAR[29]", (("init", R_LEVEL),)),
    "killer": Source("B_SYSLIST[0] B_MEMBER(70) B_PICK", (("init", R_KILLER), ("reaction", R_KILLER))),
    "killer_hp": Source("B_SYSLIST[0] B_MEMBER(36) B_PICK", (("init", R_KILLER), ("reaction", R_KILLER))),
}
# frame-shared engine slots: exact with one effect per frame
FRAME_SHARED = frozenset({"killer", "killer_hp", "command", "ability"})
SOURCE_HINTS = {
    "scene": "the scene id is a build-time constant: write set = <scene_id>",
    "max_hp": "a type's max HP is a build-time constant of this scene: write the number",
    "level": "a type's level is a build-time constant of this scene: write the number",
}


@dataclass(frozen=True)
class LedgerTable:
    name: str
    tid: int
    values: tuple
    path: Path
    flags: tuple                           # ((normalized name, index), ...) from declared_in's [[flag]] table

    @property
    def n(self) -> int:
        return len(self.values)

    @property
    def word(self) -> int:
        return _B.persist_check_word(self.name, self.n)

    @property
    def guard(self) -> int:
        return self.tid + _B.PERSIST_GUARD_OFFSET


@dataclass(frozen=True)
class Write:
    row: int                               # the authored row, 1-based (messages)
    on: str
    slot: int
    cell: "int | None"
    flag: "str | None"
    flag_index: "int | None"
    op: str                                # "set" | "add"
    value: object                          # int, or a SOURCES name


@dataclass(frozen=True)
class Binding:
    slot: int
    type_no: int
    entry: int
    put_flags: int


@dataclass(frozen=True)
class Splice:
    entry: int
    tag: int
    mode: str                              # "prepend" | "add"
    body: bytes
    note: str


@dataclass(frozen=True)
class LedgerPlan:
    table: LedgerTable
    writes: tuple
    bindings: tuple
    or_types: tuple                        # ((type_no, old_word, new_word), ...)
    splices: tuple
    warnings: tuple
    summary: tuple


# ------------------------------------------------------------------------------------------------ keys
def _near(word: str, choices) -> str:
    m = difflib.get_close_matches(str(word), sorted(choices), n=1, cutoff=0.6)
    return f" -- did you mean {m[0]!r}?" if m else ""


def scene_key_problems(sc: dict) -> list:
    """The shape of ``[scene.ledger]`` itself, and the typo that would make it silently inert: the battle build
    ignores unknown ``[scene]`` keys, so ``[scene.leger]`` would never write and never say so."""
    out = []
    if "ledger" in sc and not isinstance(sc["ledger"], dict):
        out.append("write [scene.ledger] as ONE table (declared_in, table, [[scene.ledger.write]] rows) -- "
                   "a battle writes one ledger")
    for k in sc:
        if k in KNOWN_SCENE_KEYS:
            continue
        if difflib.SequenceMatcher(None, str(k).lower(), "ledger").ratio() >= 0.6:
            out.append(f"[scene] has {k!r} -- did you mean [scene.ledger]? The build ignores unknown [scene] "
                       f"keys, so a mistyped ledger never writes")
    return out


# ------------------------------------------------------------------------------------------------ table
def resolve_table(base_dir, spec: dict) -> LedgerTable:
    """The ledger's identity, READ from the field.toml that declares it (never restated in the battle).
    Raises :class:`LedgerError` -- never a parse traceback -- on anything a battle cannot trust."""
    from ..content import behaviortoml as _BT
    from .. import flags as _flags
    ref = spec.get("declared_in")
    if not isinstance(ref, str) or not ref.strip():
        raise LedgerError("[scene.ledger] needs declared_in = \"<path>\" -- a PATH, relative to this battle.toml, "
                          "to the field.toml whose [[behavior.table]] (persist = true) declares the ledger")
    path = Path(base_dir) / ref
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError:
        raise LedgerError(f"declared_in {ref!r}: not found (resolved to {path.resolve()}) -- a PATH, relative to "
                          f"this battle.toml, to the field.toml that declares the table")
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as ex:
        raise LedgerError(f"declared_in {ref!r}: not readable TOML ({ex})")
    name = spec.get("table")
    if not isinstance(name, str) or not name:
        raise LedgerError("[scene.ledger] needs table = \"<name>\" -- the persist = true [[behavior.table]] "
                          f"name in {ref}")
    b = raw.get("behavior") if isinstance(raw.get("behavior"), dict) else {}
    rows = b.get("table") if isinstance(b.get("table"), list) else []
    named = [r for r in rows if isinstance(r, dict) and r.get("name") == name]
    persistent = sorted(str(r.get("name")) for r in rows if isinstance(r, dict) and r.get("persist") is True)
    if len(named) > 1:
        raise LedgerError(f"{ref} declares table {name!r} twice -- the battle cannot know which shape it writes")
    if not named:
        raise LedgerError(f"{name!r} is not a persist = true [[behavior.table]] in {ref} (persistent tables "
                          f"there: {persistent or 'none'})")
    row = named[0]
    if row.get("persist") is not True:
        raise LedgerError(f"{name!r} in {ref} is an ordinary table: its field re-seeds it at every entry, so a "
                          f"fight's rows would be wiped before anything reads them -- declare persist = true with "
                          f"an id in {_B.PERSIST_TID_LO}..{_B.PERSIST_TID_HI}")
    probs = _B.persist_declaration_problems(name, row.get("id"), row.get("values"))
    if probs:
        raise LedgerError(f"the declaration of {name!r} in {ref} is invalid: {'; '.join(probs)} -- fix the field "
                          f"first")
    if not any(t[0] == name for t in _BT.persistent_tables(raw)):
        raise LedgerError(f"{name!r} in {ref} never compiles: a [behavior] block's tables are emitted only when "
                          f"it has a [[behavior.unit]] -- the field would never seed the ledger")
    try:
        fdefs = _flags.collect_flag_defs(raw)
    except (ValueError, TypeError) as ex:
        raise LedgerError(f"{ref}'s [[flag]] table is invalid: {ex}")
    return LedgerTable(name, int(row["id"]), tuple(int(v) for v in row["values"]), path,
                       tuple(sorted(fdefs.items())))


# ------------------------------------------------------------------------------------------------ rows
def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def parse_writes(spec: dict, table: LedgerTable, n_slots: int) -> tuple:
    """``(writes, errors)``: every row validated and expanded to one :class:`Write` per slot."""
    from .. import flags as _flags
    errors: list = []
    writes: list = []
    rows = spec.get("write")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_WRITES \
            or not all(isinstance(r, dict) for r in rows):
        return [], [f"[scene.ledger] needs 1..{MAX_WRITES} [[scene.ledger.write]] rows (tables)"]
    flag_idx = dict(table.flags)
    for k, r in enumerate(rows, 1):
        at = f"[[scene.ledger.write]] #{k}"
        for extra in sorted(set(r) - WRITE_KEYS):
            errors.append(f"{at}: unknown key {extra!r} -- the build ignores it{_near(extra, WRITE_KEYS)}")
        on = r.get("on")
        if on not in HOOK_TAGS:
            hint = (f" -- did you mean {HOOK_SYNONYMS[on.lower()]!r}?" if isinstance(on, str)
                    and on.lower() in HOOK_SYNONYMS else _near(on, HOOK_TAGS))
            errors.append(f"{at}: on = {on!r}: the hooks are init (tag 0), reaction (tag 7), dying (tag 9){hint}")
            continue
        slots = r.get("slot")
        slots = [slots] if _int(slots) else slots
        if not isinstance(slots, list) or not slots or not all(_int(s) for s in slots) \
                or len(set(slots)) != len(slots):
            errors.append(f"{at}: slot must be an int or a list of unique ints")
            continue
        bad = [s for s in slots if not 0 <= s < n_slots]
        if bad:
            errors.append(f"{at}: slot {bad[0]}: this scene spawns monster_count = {n_slots} "
                          f"(slots 0-{n_slots - 1})")
            continue
        if ("cell" in r) == ("flag" in r):
            errors.append(f"{at}: give exactly one of cell = <index> / flag = \"<name>\"")
            continue
        cell = flag = fidx = None
        if "cell" in r:
            cell = r["cell"]
            if not _int(cell) or not 0 <= cell < table.n:
                errors.append(f"{at}: cell {cell!r} is outside {table.name} ({table.n} cells, 0..{table.n - 1}) -- "
                              f"a write at index == length APPENDS a cell (EBin.cs:1926), and the next declaring "
                              f"field's Main_Init then re-seeds (wipes) the whole table")
                continue
        else:
            flag = r["flag"]
            fidx = flag_idx.get(_flags._norm(flag)) if isinstance(flag, str) else None
            if fidx is None:
                errors.append(f"{at}: flag {flag!r} is not a [[flag]] in {spec.get('declared_in')} (flags there: "
                              f"{sorted(n for n, _ in table.flags) or 'none'})")
                continue
        if ("set" in r) == ("add" in r):
            errors.append(f"{at}: give exactly one of set / add")
            continue
        if flag is not None:
            if "add" in r:
                errors.append(f"{at}: add writes cells only; a flag takes set = 0 or 1")
                continue
            if r["set"] not in (0, 1) or isinstance(r["set"], bool):
                errors.append(f"{at}: a flag's set must be 0 or 1")
                continue
            op, value = "set", r["set"]
        elif "add" in r:
            value = r["add"]
            if not _int(value) or value == 0 or abs(value) > FENCE:
                errors.append(f"{at}: add must be a nonzero integer within ±{FENCE}")
                continue
            op = "add"
        else:
            value, op = r["set"], "set"
            if _int(value):
                if abs(value) > FENCE:
                    errors.append(f"{at}: set {value} is outside the persistent value fence ±{FENCE}")
                    continue
            elif isinstance(value, str) and value in SOURCES:
                why = SOURCES[value].why_not(on)
                if why:
                    errors.append(f"{at}: set = {value!r} is not readable on {on}: {why}")
                    continue
            else:
                hint = SOURCE_HINTS.get(value) if isinstance(value, str) else None
                errors.append(f"{at}: set = {value!r}: sources are {', '.join(sorted(SOURCES))}, or an integer"
                              + (f" ({hint})" if hint else _near(value, SOURCES) if isinstance(value, str) else ""))
                continue
        for s in slots:
            writes.append(Write(k, on, s, cell, flag, fidx, op, value))
    seen: dict = {}
    for w in writes:
        key = (w.on, w.slot, w.cell if w.cell is not None else ("flag", w.flag_index))
        if key in seen:
            what = f"cell {w.cell}" if w.cell is not None else f"flag {w.flag!r}"
            errors.append(f"[[scene.ledger.write]] #{seen[key]} and #{w.row} both write {what} on {w.on} for "
                          f"slot {w.slot}")
        seen.setdefault(key, w.row)
    return writes, errors


# ------------------------------------------------------------------------------------------------ emit
def _write_items(table: LedgerTable, w: Write, tag: str) -> list:
    if w.flag_index is not None:
        return [_B._stmt(f"Global.Bit[{w.flag_index}] const({int(w.value)}) B_LET")]
    ref = f"{_B._cnum(table.tid)} {_B._cnum(w.cell)} B_VECTOR"
    if w.op == "add":
        return [_B._stmt(f"{ref} {ref} {_B._cnum(w.value)} B_PLUS B_LET"), *_B.clamp_items(ref, -FENCE, FENCE, tag)]
    if isinstance(w.value, int):                      # fenced at build (parse_writes)
        return [_B._stmt(f"{ref} {_B._cnum(w.value)} B_LET")]
    return [_B._stmt(f"{ref} {SOURCES[w.value].rpn} B_LET"), *_B.clamp_items(ref, -FENCE, FENCE, tag)]


def fragment(table: LedgerTable, cell_groups, flag_groups, *, added: bool, pfx: str) -> bytes:
    """One hook's code for one AI entry. ``cell_groups`` / ``flag_groups``: ``[(slot, [Write, ...]), ...]`` in
    ascending slot order. Layout: [live gate -> per-slot filter -> cell writes] then [per-slot filter -> flag
    writes] (+ ``RET`` when the function is ADDED; a prepend falls through into the existing body). Straight-line
    code with no yield: from the gate to the last write it runs in one ProcessCode step."""
    items: list = []
    if cell_groups:
        items += [_B._stmt(_B.persist_live_expr(table.name, table.tid, table.n)), (JMP_IFNOT, f"{pfx}_dead")]
        for slot, ws in cell_groups:
            items += [_B._stmt(f"B_SYSLIST[1] {_B._cnum(16 << slot)} B_EQ"), (JMP_IFNOT, f"{pfx}_c{slot}")]
            for i, w in enumerate(ws):
                items += _write_items(table, w, f"{pfx}_s{slot}_{i}")
            items.append(label(f"{pfx}_c{slot}"))
        items.append(label(f"{pfx}_dead"))
    for slot, ws in flag_groups:
        items += [_B._stmt(f"B_SYSLIST[1] {_B._cnum(16 << slot)} B_EQ"), (JMP_IFNOT, f"{pfx}_f{slot}")]
        for i, w in enumerate(ws):
            items += _write_items(table, w, f"{pfx}_g{slot}_{i}")
        items.append(label(f"{pfx}_f{slot}"))
    if added:
        items.append(bytes([0x04]))                   # RET
    return asm(items)


def _has(eb: EbScript, entry: int, tag: int) -> bool:
    e = eb.entries[entry] if 0 <= entry < len(eb.entries) else None
    return e is not None and not e.empty and e.func_by_tag(tag) is not None


def _func_bytes(eb: EbScript, entry: int, tag: int) -> bytes:
    f = eb.entries[entry].func_by_tag(tag)
    return bytes(eb.data[f.abs_start:f.abs_end])


def _describe(w: Write) -> str:
    tgt = f"c{w.cell}" if w.cell is not None else f"flag {w.flag}({w.flag_index})"
    return f"{tgt}{'+=' if w.op == 'add' else '='}{w.value}"


# ------------------------------------------------------------------------------------------------ plan
def plan(base_dir, sc: dict, *, raw16: bytes, eb_donor: bytes, eb_composed: bytes) -> tuple:
    """``(LedgerPlan | None, errors, warnings)`` for a ``[scene]`` with a ``ledger``. ``raw16`` = the patched scene
    (after the ``[scene]`` edits); ``eb_donor`` = the forked eb; ``eb_composed`` = :func:`build._compose_ai`'s output
    (the ledger splices go on top of it). Every refusal lives here; validate and build both call it."""
    errors: list = []
    warnings: list = []
    spec = sc.get("ledger")
    if not isinstance(spec, dict):
        return None, errors, warnings                  # scene_key_problems reports the shape
    for extra in sorted(set(spec) - LEDGER_KEYS):
        errors.append(f"[scene.ledger]: unknown key {extra!r} -- the build ignores it{_near(extra, LEDGER_KEYS)}")
    mc = sc.get("monster_count")
    if not _int(mc):
        errors.append("[scene.ledger] names enemies by slot, and only [scene] monster_count makes slot -> AI entry "
                      "-> self bit (16 << slot) static; a donor Main_Init may pick the entry by the rolled pattern "
                      "(EF_R007: SWITCH(B_SYSVAR[31]))")
        return None, errors, warnings
    try:
        table = resolve_table(base_dir, spec)
    except LedgerError as ex:
        errors.append(f"[scene.ledger]: {ex}")
        return None, errors, warnings
    try:
        slot_types = [_scene_data.slot_put(raw16, s)[0] for s in range(mc)]
        from .build import _ai_entries
        entries = _event_data.resolve_ai_entries(eb_donor, slot_types, _ai_entries(sc, mc))
    except (ValueError, TypeError) as ex:
        errors.append(f"[scene.ledger] AI binding: {ex}")
        return None, errors, warnings
    bindings = tuple(Binding(s, slot_types[s], entries[s], _scene_data.slot_put(raw16, s)[1]) for s in range(mc))
    writes, errs = parse_writes(spec, table, mc)
    errors += [f"[scene.ledger] {e}" if not e.startswith("[") else e for e in errs]
    for s in sorted({w.slot for w in writes}):
        if bindings[s].put_flags & _scene_data.PUT_FLAG_MULTIPART:
            errors.append(f"[scene.ledger]: slot {s} is a MULTIPART part: its hits and death route to its master's "
                          f"object -- give that slot a 'type' in [[scene.enemy]] (a single-part enemy) or name the "
                          f"master slot")
    if errors:
        return None, errors, warnings

    donor, composed = EbScript.from_bytes(eb_donor), EbScript.from_bytes(eb_composed)
    explicit = set()
    for e in sc.get("enemy", []) or []:
        if isinstance(e, dict) and "flags" in e and _int(e.get("slot")) and 0 <= e["slot"] < 4:
            explicit.add(_scene_data.slot_put(raw16, e["slot"])[0])
    or_types = []
    for t in sorted({bindings[w.slot].type_no for w in writes if w.on == "dying"}):
        word = _scene_data.mon_flags(raw16, t)
        slots_t = [b.slot for b in bindings if b.type_no == t]
        if word & _scene_data.MON_FLAG_NON_DYING_BOSS:
            errors.append(f"[scene.ledger]: slot {slots_t[0]}'s type {t} carries non_dying_boss: it can stop above "
                          f"0 HP, so its dying hook never runs")
            continue
        if word & _scene_data.MON_FLAG_DIE_ATK:
            continue
        if t in explicit:
            errors.append(f"[scene.ledger]: slot {slots_t[0]} (type {t}): [[scene.enemy]] flags REPLACES the type's "
                          f"flag word without die_atk, but a dying row needs it (tag 9 runs only with die_atk) -- add "
                          f"\"die_atk\" to that flags list, or drop flags and let the ledger OR it in")
            continue
        dormant = [b.entry for b in bindings if b.type_no == t and _has(donor, b.entry, 9)
                   and _has(composed, b.entry, 9) and _func_bytes(donor, b.entry, 9) == _func_bytes(composed, b.entry, 9)]
        if dormant:
            e0 = dormant[0]
            errors.append(f"[scene.ledger]: type {t} lacks die_atk and entry {e0} carries a donor tag-9 function "
                          f"({len(_func_bytes(donor, e0, 9))} bytes) that has never run -- OR-ing die_atk would bring "
                          f"it to life. To keep it, add \"die_atk\" to [[scene.enemy]] flags explicitly; to drop it, "
                          f"[[scene.ai_function]] entry = {e0}, tag = 9, replace = true, source = \"RET()\"")
            continue
        or_types.append((t, word, word | _scene_data.MON_FLAG_DIE_ATK))
        warnings.append(f"[scene.ledger]: die_atk added to type {t} (flags 0x{word:04x} -> "
                        f"0x{word | _scene_data.MON_FLAG_DIE_ATK:04x}) for its dying rows: every slot of type {t} "
                        f"({', '.join(map(str, slots_t))}) now dies through the die_atk path, and its AI entry's own "
                        f"tag 7 no longer runs on the killing blow -- stall-free in-game for EF_R007's Goblin "
                        f"(fight-ledger rung 0); bench the death once for another enemy")
    for s in sorted({w.slot for w in writes if w.on == "reaction"}):
        if _has(composed, bindings[s].entry, 6):
            errors.append(f"[scene.ledger]: slot {s}'s AI entry {bindings[s].entry} has a Counter (tag 6): a player's "
                          f"non-lethal hit calls it at level 1 and the engine then REFUSES that hit's Reaction "
                          f"(level 2) -- a reaction row would miss almost every hit. Counting hits on a countering "
                          f"enemy is not supported")
    if errors:
        return None, errors, warnings
    if any(isinstance(w.value, str) and w.value in FRAME_SHARED for w in writes):
        warnings.append("[scene.ledger]: killer / killer_hp / command / ability read frame-shared engine slots "
                        "(SysList[0], the last request's command): exact with one effect per frame; when two "
                        "effects resolve in one frame (Battle Speed 'Simultaneous', several enemies) a value can "
                        "belong to the other event")

    or_set = {t for t, _o, _n in or_types}
    die_atk = {b.slot: bool((_scene_data.mon_flags(raw16, b.type_no) & _scene_data.MON_FLAG_DIE_ATK)
                            or b.type_no in or_set) for b in bindings}
    dying_entries = {bindings[w.slot].entry for w in writes if w.on == "dying"}
    splices = []
    for entry in sorted({b.entry for b in bindings}):
        slots_e = [b.slot for b in bindings if b.entry == entry]
        tag9_final = _has(composed, entry, 9) or entry in dying_entries
        for hook, tag in HOOK_TAGS.items():
            cell_groups, flag_groups, notes = [], [], []
            for s in slots_e:
                replay = ([w for w in writes if w.slot == s and w.on == "reaction"]
                          if tag == 9 and tag9_final and die_atk[s] else [])
                own = [w for w in writes if w.slot == s and w.on == hook]
                cells = [w for w in replay + own if w.cell is not None]
                flags_ = [w for w in replay + own if w.flag is not None]
                if cells:
                    cell_groups.append((s, cells))
                if flags_:
                    flag_groups.append((s, flags_))
                if cells or flags_:
                    rp = f"replay[{' '.join(_describe(w) for w in replay)}] " if replay else ""
                    notes.append(f"s{s} {rp}{' '.join(_describe(w) for w in own)}".rstrip())
            if not cell_groups and not flag_groups:
                continue
            mode = "prepend" if _has(composed, entry, tag) else "add"
            body = fragment(table, cell_groups, flag_groups, added=(mode == "add"), pfx=f"ldg{entry}_{tag}")
            splices.append(Splice(entry, tag, mode, body,
                                  f"entry {entry} tag {tag} ({hook}, {'ADDED' if mode == 'add' else 'prepended'} "
                                  f"+{len(body)} B): " + " / ".join(notes)))
    p = LedgerPlan(table, tuple(writes), bindings, tuple(or_types), tuple(splices), tuple(warnings), ())
    try:
        final = apply(eb_composed, p)
    except (LedgerError, ValueError) as ex:
        return None, [f"[scene.ledger]: {ex}"], warnings
    if len(final) > MAX_EB:
        return None, [f"[scene.ledger]: the ledger would grow the battle eb to {len(final)} bytes, past the u16 "
                      f"entry-offset ceiling ({MAX_EB}) -- write fewer rows"], warnings
    try:
        rel = spec["declared_in"]
    except KeyError:
        rel = str(table.path)
    summary = (f"ledger {table.name}: id {table.tid}, {table.n} cells, check word {table.word}, guard {table.guard} "
               f"(declared in {rel})",
               f"writes only while the live guard matches ({table.name}, {table.n}); a stale or never-seeded ledger "
               f"is left untouched (flag rows still land)",
               *(sp.note for sp in splices))
    return LedgerPlan(table, tuple(writes), bindings, tuple(or_types), tuple(splices), tuple(warnings),
                      summary), [], warnings


def build_plan(base_dir, sc: dict, *, raw16: bytes, eb_donor: bytes, eb_composed: bytes) -> LedgerPlan:
    """:func:`plan` for the build: raises :class:`LedgerError` on any refusal (validate ran first; this is the
    defence in depth that keeps a direct build call honest)."""
    p, errors, _w = plan(base_dir, sc, raw16=raw16, eb_donor=eb_donor, eb_composed=eb_composed)
    if errors or p is None:
        raise LedgerError("; ".join(errors) or "[scene.ledger] could not be planned")
    return p


def apply_die_atk(raw16: bytes, p: LedgerPlan) -> bytes:
    """OR ``die_atk`` into every type the plan needs it for (every other flag bit kept)."""
    for t, _old, new in p.or_types:
        raw16 = _scene_data.with_mon_flags(raw16, t, new)
    return raw16


def apply(eb: bytes, p: LedgerPlan) -> bytes:
    """Splice the plan into one language's composed eb. Each splice re-checks its precondition (a prepend needs
    the function, an add needs it absent), so a language whose eb differs fails loud instead of mis-splicing."""
    for sp in p.splices:
        have = _has(EbScript.from_bytes(eb), sp.entry, sp.tag)
        if (sp.mode == "prepend") != have:
            raise LedgerError(f"entry {sp.entry} tag {sp.tag}: planned as {sp.mode} but this eb "
                              f"{'has' if have else 'lacks'} the function -- the languages' ebs differ")
        if sp.mode == "prepend":
            eb = _edit.insert_in_function(eb, sp.entry, sp.tag, 0, sp.body)
        else:
            eb = _edit.add_function(eb, sp.entry, sp.tag, sp.body)
    return eb
