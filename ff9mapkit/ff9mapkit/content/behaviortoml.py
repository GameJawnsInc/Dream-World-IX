"""The ``[behavior]`` TOML surface — behavior trees as ordinary field content
(rung 4 of ``studies/behavior-trees/PLAN.md``: the kit idiom over the
:mod:`ff9mapkit.content.behavior` compiler).

Shape (a unit binds to a named ``[[npc]]``; branches are PRIORITY-ordered — the
first whose ``when`` conditions all hold selects its ``do`` each tick; the last
branch should be unconditional, a static feed):

    [behavior]
    warmup = 45                              # optional field-wide settings
    alternators = [{ name = "shift", frames = 400 }]
    public_flags = ["raid"]                  # set from OUTSIDE (a [[choice]] lever);
                                             # allocated indices print in the build report

    [[behavior.unit]]
    npc = "patroller"
    hp = 5                                   # optional: allocates + presets an HP byte
    speed = 40                               # default walk speed

      [[behavior.unit.branch]]
      when = [{ near = ["player", 400] }]
      do = { chase = "player", speed = 65 }

      [[behavior.unit.branch]]
      do = { patrol = "ringA" }              # a [[marker]] with `path=` — the SAME
                                             # route the layout probe sweeps

Condition verbs (each ``when`` row is a dict with EXACTLY the verb key):
``hp_le`` / ``hp_gt`` (int = own hp; ``["unit", n]`` = another's), ``near`` /
``not_near`` (``[target, r]``; target = a unit name or ``"player"``),
``near_point`` / ``not_near_point`` (``[point, r]``), ``flag`` / ``not_flag``,
``any_flag`` (list), ``active`` / ``not_active`` (unit), ``counter_ge`` /
``counter_le`` / ``counter_eq`` (``["counter", n]``), ``table_ge`` /
``table_le`` / ``table_eq`` (``["table", index, n]``; index = an int or a
COUNTER name — the computed-array-indexing read).

Data tables (Memoria's gScriptVector, the 0xD3 VECTOR lane — re-seeded every
field entry, so deterministic per-session state):

    [behavior]
    timer = 180                              # the countdown HUD
    counters = ["wave", "kills"]             # runtime cells, seeded 0

    [[behavior.table]]
    name = "sched"                           # wave start-times (data, not code)
    values = [170, 90]

    [[behavior.schedule]]                    # THE WAVE CLOCK: while the HUD sits
    counter = "wave"                         # below sched[wave], wave += 1 — one
    table = "sched"                          # generic engine, terminates itself
                                             # when wave walks off the table
Counters bump from trees: ``die = "kills"`` (bump once — the body runs exactly
once); branches gate on ``counter_ge``/``counter_eq``.

    [[behavior.scan]]                        # THE VECTOR LOOP (v2 rung 0): per
    name = "shrine"                          # tick, mirror the roster into
    units = ["m0", "m1", "m2"]               # position tables, loop a live index
    point = [1153, -200]                     # over them (computed-index vector
    radius = 300                             # reads AND writes), and publish the
    count = "at_shrine"                      # inside-the-box headcount into the
    flags = "near_shrine"                    # counter; flags = the per-unit 0/1
                                             # table (readable via table_* conds)

Action verbs (the ``do`` dict: one verb key + that verb's option keys):
``walk_to`` / ``hold`` (point; +speed), ``chase`` (target; +standoff, speed),
``patrol`` / ``march`` (points or a route-marker name; +arrive_r, speed, and
``route = "auto"`` — at build time, any leg the walkability sweep finds OFF-MESH
is re-routed through the walkmesh pathfinder and the detours spliced in; clear
legs stay exactly as authored),
``flee`` (threat; +to = refuge points, avoid_r, speed), ``wander`` (centre
point; +radius, every, speed), ``swing_at`` (unit; +damage, interval),
``die``, ``sfx`` (a sound-effect cue; +bank), ``flash`` (a [r, g, b] screen
flash), ``announce`` (a text line — minted into the field's .mes) /
``announce_npc`` (reuse that NPC's own dialogue line; +window).

Branch keys: ``when`` (optional), ``do`` (required), ``once = "name"`` OR
``cooldown = frames`` (the sticky decorators), ``raise_flags`` /
``clear_flags``. A ``point`` anywhere is ``[x, z]`` or a marker/NPC name.

Unknown verbs, unknown option keys, and unresolvable names are ERRORS — the
laws-as-compiler-invariants posture extends to the TOML surface (a typo\'d key
must never silently no-op).
"""
from __future__ import annotations

from . import behavior as B

COND_VERBS = {
    "hp_le": (), "hp_gt": (), "near": (), "not_near": (), "near_point": (),
    "not_near_point": (), "flag": (), "not_flag": (), "any_flag": (),
    "active": (), "not_active": (), "any_near": (), "any_active": (),
    "time_below": (), "time_above": (),
    "counter_ge": (), "counter_le": (), "counter_eq": (),
    "table_ge": (), "table_le": (), "table_eq": (),
    "have_item": (),
}
ACTION_VERBS = {
    "walk_to": ("speed",),
    "hold": ("speed",),
    "hold_post": ("speed",),
    "chase": ("standoff", "speed"),
    "patrol": ("arrive_r", "speed", "route"),
    "march": ("arrive_r", "speed", "route"),
    "flee": ("to", "avoid_r", "speed"),
    "wander": ("radius", "every", "speed"),
    "swing_at": ("damage", "interval", "anim", "hit_sfx"),
    "engage": ("radius", "contact", "damage", "interval", "speed", "nearest",
               "anim", "hit_sfx"),
    "hold_ground": (),
    "die": ("anim", "linger"),
    "battle": (),
    "award": ("item", "count"),
    "add_shop_item": (),
    "remove_shop_item": (),
    "add_shop_synth": (),
    "remove_shop_synth": (),
    "sfx": ("bank", "sustain"),
    "flash": ("pause",),
    "stop_timer": (),
    "announce": ("window", "delay", "sustain"),
    "announce_npc": ("window", "delay", "sustain"),
}
BRANCH_KEYS = {"when", "do", "once", "cooldown", "raise_flags", "clear_flags"}
UNIT_KEYS = {"npc", "hp", "speed", "branch", "pooled", "pool"}
FIELD_KEYS = {"warmup", "tick", "alternators", "public_flags", "unit", "pool", "timer",
              "counters", "table", "schedule", "scan", "group", "hud", "byte_band",
              "brains"}
POOL_KEYS = {"name", "price", "button", "request_flag", "item"}
TABLE_KEYS = {"name", "values", "id"}
SCHEDULE_KEYS = {"counter", "table"}
SCAN_KEYS = {"name", "units", "point", "radius", "count", "flags", "group",
             "alive_only"}
GROUP_KEYS = {"name", "units"}
HUD_KEYS = {"window", "text", "values", "digits"}


class BehaviorTomlError(ValueError):
    pass


def table(raw: dict):
    """The ``[behavior]`` table, or None. Presence means the field compiles a behavior."""
    b = raw.get("behavior")
    return b if isinstance(b, dict) and b.get("unit") else None


def units(raw: dict) -> list:
    b = table(raw)
    return list(b.get("unit", [])) if b else []


def _one_verb(d: dict, verbs: dict, ctx: str) -> str:
    keys = [k for k in d if k in verbs]
    if len(keys) != 1:
        raise BehaviorTomlError(
            f"{ctx}: expected exactly ONE verb key of {sorted(verbs)} (got {sorted(d)})")
    verb = keys[0]
    extra = set(d) - {verb} - set(verbs[verb])
    if extra:
        raise BehaviorTomlError(
            f"{ctx}: unknown option key(s) {sorted(extra)} for verb {verb!r} "
            f"(allowed: {sorted(verbs[verb])})")
    return verb


def published_flags(raw: dict) -> set:
    """Flag indices the compiled ticker WRITES for the outside world: each pool's
    ``hireable`` gate (what a hire row's ``requires_flag`` reads) and every declared
    ``public_flags`` name. They are set by compiled ``.eb``, not by an ``[[event]]``,
    so a flag lint that only scans events would call every generated hire menu dangling.

    Runs a THROWAWAY build to get the deterministic allocation (the same two-pass
    ``siege.resolve_hireable`` uses): routes stripped (``route = "auto"`` needs a
    walkmesh) and synthetic txids handed in (announce/hud lines are minted later, by
    the real build). Returns ``set()`` rather than raising — a lint must never fail."""
    import copy as _copy
    try:
        work = _copy.deepcopy(raw)
        for u in (table(work) or {}).get("unit", []) or []:
            for br in u.get("branch", []) or []:
                if isinstance(br.get("do"), dict):
                    br["do"].pop("route", None)
        names = [str(u["npc"]) for u in units(work)]
        txids = {(ui, bi): 900 + 10 * ui + bi for ui, bi, _ in announce_lines(work)}
        txids.update({("hud", hi): 890 + hi for hi, _h in hud_lines(work)})
        fb = build(work, npc_slots={n: i + 2 for i, n in enumerate(names)},
                   npc_txids_by_name={n.get("name"): 0 for n in work.get("npc", []) or []},
                   behavior_txids=txids)
        out = set(fb.pool_hireable.values())
        for pf in (table(work) or {}).get("public_flags", []) or []:
            out.add(fb.public_flag(str(pf)))
        return out
    except Exception:                              # noqa: BLE001 — never fail a lint
        return set()


def draining_once_warnings(raw: dict) -> list:
    """LINT (warnings): stacked event-``once`` branches gated on a condition that can
    STOP HOLDING — THE DRAINING-CONDITION LAW (the ARMOURY round-3 playtest).

    The selector picks ONE branch per unit per tick, so N once-branches sharing a
    condition fire on N CONSECUTIVE ticks. That is fine for a STICKY condition (a
    raised flag, a spent clock band, a dead unit's hp) and broken for one that
    drains: the first branch fires, the condition goes false, and every branch below
    it starves — silently, and only sometimes, because it depends on how long the
    world happens to hold still.

    Sticky by construction: ``flag``/``not_flag``/``any_flag`` (nothing clears them
    here), ``time_below`` (remaining time only falls), ``hp_le`` (hp only falls —
    swings gate on hp > 0), and ``counter_ge`` on a counter no ``[[behavior.scan]]``
    feeds (a scan headcount rises AND falls; a schedule or kill tally only rises).
    Everything else — ``have_item``, ``near``/``any_near``, ``active``,
    ``counter_eq``, ``time_above``, … — can drain."""
    b = table(raw)
    if not b:
        return []
    scan_fed = {str(s.get("count")) for s in (b.get("scan") or []) if s.get("count")}
    cleared = {str(n) for u in (b.get("unit") or [])
               for br in (u.get("branch") or [])
               for n in (br.get("clear_flags") or [])}

    def sticky(cond: dict) -> bool:
        if not isinstance(cond, dict) or len(cond) != 1:
            return False
        (verb, val), = cond.items()
        if verb in ("flag", "not_flag"):
            return str(val) not in cleared
        if verb == "any_flag":
            return all(str(v) not in cleared for v in (val or []))
        if verb in ("time_below", "hp_le"):
            return True
        if verb == "counter_ge":
            return isinstance(val, list) and str(val[0]) not in scan_fed
        return False

    out = []
    for u in b.get("unit") or []:
        groups: dict = {}
        for bi, br in enumerate(u.get("branch") or []):
            if not br.get("once") or not isinstance(br.get("do"), dict):
                continue
            when = br.get("when") or []
            if not when or all(sticky(c) for c in when):
                continue
            key = repr(when)
            groups.setdefault(key, []).append((bi, br))
        for key, rows in groups.items():
            if len(rows) < 2:
                continue
            names = ", ".join(repr(r[1].get("once")) for r in rows)
            drains = [c for c in (rows[0][1].get("when") or []) if not sticky(c)]
            out.append(
                f"[[behavior.unit]] {str(u.get('npc'))!r}: {len(rows)} `once` branches "
                f"({names}) share the gate {key} — one branch fires PER TICK, so they "
                f"need it to hold for {len(rows)} consecutive ticks, and "
                f"{drains[0]!r} can stop holding before then (THE DRAINING-CONDITION "
                f"LAW). The lower branches would silently never fire. Fix: give the "
                f"FIRST branch `raise_flags = [\"<moment>\"]` and gate the rest on "
                f"`{{ flag = \"<moment>\" }}` — a raised flag does not drain.")
    return out


def clock_coupled_warnings(raw: dict, *, game=None, probe=None) -> list:
    """LINT (warnings, not errors): every ``battle`` this TIMED field fires whose scene AI
    READS THE COUNTDOWN — ``B_SYSVAR[17]`` is ``TimerUI.Time``, and the Hunt scenes end
    themselves the instant it reads 0 (THE CLOCK-COUPLED BATTLE LAW; see
    ``battle.battleai.reads_timer``). The field's own ending theater is what lets the clock
    run out before the battle fires, so this is a warning about a COMBINATION, not a bad
    scene.

    Quiet when: the field has no ``timer``, fires no battle, the scene's ``.eb`` can't be
    read (no install — "unknown", never assumed safe: the message says so), or the behavior
    uses ``stop_timer`` ANYWHERE (the author has met the law; ``[siege]`` always does).
    ``probe``: ``scene -> bool|None`` override, for tests without an install."""
    b = table(raw)
    if not b or b.get("timer") is None:
        return []
    scenes, has_stop = [], False
    for u in b.get("unit", []) or []:
        for br in u.get("branch", []) or []:
            do = br.get("do")
            if not isinstance(do, dict):
                continue
            if do.get("stop_timer"):
                has_stop = True
            if isinstance(do.get("battle"), int):
                scenes.append((str(u.get("npc")), int(do["battle"])))
    if not scenes or has_stop:
        return []
    if probe is None:
        from ..battle import battleai as _ai

        def probe(s):
            return _ai.scene_reads_timer(s, game=game)
    out = []
    for unit, sid in dict.fromkeys(scenes):
        try:
            hit = probe(sid)
        except Exception:                          # noqa: BLE001 — never fail lint on this
            hit = None
        if hit:
            out.append(
                f"[[behavior.unit]] {unit!r}: battle scene {sid}'s AI READS THE COUNTDOWN "
                f"(B_SYSVAR[17] = TimerUI.Time) and will END ITSELF if the clock reads 0 "
                f"when it starts — the Festival of the Hunt rule, which lives inside the "
                f"battle script. This field runs a timer, so any theater before the battle "
                f"(a sting, staged text) can let the clock expire first and the fight dies "
                f"on entry. Fix: `do = {{ stop_timer = true }}` on a branch that outranks "
                f"the battle (this warning goes quiet once the behavior uses it), or pick a "
                f"scene whose AI ignores the clock (`ff9mapkit battle-ai <scene>`).")
    return out


def resolve_gesture(v, model, ctx: str) -> int:
    """An ``anim`` option: a raw clip id (int, passed through) or a GESTURE NAME
    resolved against ``model``'s OWN clips (``catalog.animations_for_model`` — the
    (group, token) join). THE OWN-CLIP LAW at the call site: a name the model does
    not own is an ERROR listing what it does own, never a silently foreign clip
    that plays wrong or not at all. ``model`` None (an npc with no model key) can
    only take a raw id."""
    if isinstance(v, bool) or (not isinstance(v, int) and not isinstance(v, str)):
        raise BehaviorTomlError(f"{ctx}: anim must be a clip id int or a gesture "
                                f"name (e.g. \"attack_cid_1\")")
    if isinstance(v, int):
        if not 0 <= v <= 0xFFFF:
            raise BehaviorTomlError(f"{ctx}: anim id must be 0..65535")
        return v
    if not model:
        raise BehaviorTomlError(f"{ctx}: anim = {v!r} is a gesture NAME but this "
                                f"unit's [[npc]] has no `model` to resolve it "
                                f"against — give a raw clip id instead")
    from .. import catalog as _cat
    try:
        owned = _cat.own_form_gestures(model)       # SAME-FORM only (the trap below)
        any_form = _cat.animations_for_model(model)
    except Exception as e:                      # noqa: BLE001 — no install / unknown model
        raise BehaviorTomlError(f"{ctx}: cannot resolve gesture {v!r} for model "
                                f"{model!r} ({e})")
    if v in owned:
        return int(owned[v])
    if v in any_form:
        # THE CROSS-FORM CLIP TRAP — proven in-game: an F3-form attack clip on an
        # F1 rig twists the model upside-down. A different FORM is a different
        # SKELETON, so this is refused, not silently played.
        raise BehaviorTomlError(
            f"{ctx}: gesture {v!r} exists for model {model!r}'s token but only in "
            f"ANOTHER FORM ({_cat.ANIMATIONS.get(any_form[v])}) — a different form "
            f"is a different skeleton and plays TWISTED in-game (the cross-form "
            f"clip trap). This rig's own-form gestures: {sorted(owned)}")
    raise BehaviorTomlError(
        f"{ctx}: model {model!r} owns no gesture {v!r} — the own-clip law "
        f"refuses a foreign clip. It owns: {sorted(owned) or '(no field clips)'}")


def _resolve_point(v, positions: dict, ctx: str):
    if isinstance(v, (list, tuple)) and len(v) >= 2 \
            and all(isinstance(c, (int, float)) for c in v[:2]):
        return (int(v[0]), int(v[1]))
    key = str(v)
    if key in positions:
        return positions[key]
    raise BehaviorTomlError(f"{ctx}: point {v!r} is not [x, z] or a known marker/NPC name")


def _resolve_route(v, positions: dict, marker_paths: dict, ctx: str) -> list:
    """Patrol/march/flee-refuge points: a route-marker name (its swept `path`),
    or an inline list of points (each [x, z] or a name)."""
    if isinstance(v, str):
        if v in marker_paths:
            return [(int(x), int(z)) for x, z in marker_paths[v][0]]
        if v in positions:
            raise BehaviorTomlError(
                f"{ctx}: marker {v!r} has no `path` — a route verb needs a route marker "
                f"([[marker]] path = [[x,z], ...]) or an inline point list")
        raise BehaviorTomlError(f"{ctx}: unknown route marker {v!r}")
    if isinstance(v, (list, tuple)):
        return [_resolve_point(p, positions, ctx) for p in v]
    raise BehaviorTomlError(f"{ctx}: route {v!r} is not a marker name or a point list")


def pooled_npcs(raw: dict) -> set:
    """Names of [[npc]]s bound to POOLED behavior units — the build seats their entry
    but SKIPS the boot ``InitObject`` (``inject_npc(boot_spawn=False)``); the compiled
    ticker spawns them at runtime when their pool's request flag is set."""
    return {str(u.get("npc")) for u in units(raw) if u.get("pooled")}


def pool_specs(raw: dict) -> list:
    """The parsed ``[[behavior.pool]]`` rows as :class:`behavior.PoolSpec` — the
    economy/UX config (price / buy-anywhere button / explicit request flag). A
    ``button = true`` resolves to :data:`behavior.DEFAULT_HIRE_BUTTONS`."""
    b = table(raw)
    out = []
    for row in (b.get("pool", []) if b else []) or []:
        btn = row.get("button")
        if btn is True:
            btn = B.DEFAULT_HIRE_BUTTONS
        elif btn is False:
            btn = None
        item = row.get("item")
        if item is not None:
            from .. import items as _items
            item = _items.resolve(item)                   # name or id -> resolved id
        out.append(B.PoolSpec(
            name=str(row.get("name", "")),
            price=(int(row["price"]) if row.get("price") is not None else None),
            button=(int(btn) if btn is not None else None),
            request_flag=(int(row["request_flag"])
                          if row.get("request_flag") is not None else None),
            item=item,
            item_name=(str(row.get("item")) if isinstance(row.get("item"), str) else "")))
    return out


def table_specs(raw: dict) -> list:
    """The parsed ``[[behavior.table]]`` rows as :class:`behavior.TableSpec` — named
    int arrays backed by gScriptVector (the 0xD3 VECTOR lane), re-seeded at every
    field entry."""
    b = table(raw)
    out = []
    for row in (b.get("table", []) if b else []) or []:
        out.append(B.TableSpec(
            name=str(row.get("name", "")),
            values=tuple(row.get("values", []) or []),
            id=(int(row["id"]) if row.get("id") is not None else None)))
    return out


def counter_names(raw: dict) -> tuple:
    b = table(raw)
    return tuple(str(c) for c in ((b.get("counters", []) if b else []) or []))


def hud_lines(raw: dict) -> list:
    """(index, row) per ``[[behavior.hud]]`` — the build mints each row's text
    like an announce (``collect_text`` keys them ``("hud", i)``)."""
    b = table(raw)
    return list(enumerate((b.get("hud", []) if b else []) or []))


def synth_mint_map(raw: dict) -> dict:
    """RESULT item id -> the recipe id the ``[[synthesis]]`` CSV emitter will mint —
    the same deterministic base-max+1 allocation, recomputed here so a
    ``add_shop_synth = [shop, "<result>"]`` string selector bakes the right literal
    into the ``.eb``. Keyed by RESOLVED item id (authors write "Phoenix Down", the
    catalog's canonical name is "PhoenixDown" — ``items.resolve`` bridges both, the
    kit's convention for every item key). Two recipes minting the same result item:
    the FIRST keeps the name — select the other by its int id. Needs the install's
    base ``Synthesis.csv`` (the allocator's floor); unreachable install -> an empty
    map, and a string selector fails at compile with a clear message (int selectors
    never need this)."""
    blocks = raw.get("synthesis", []) or []
    if not blocks:
        return {}
    try:
        from ..config import find_game_path            # ConfigError is a RuntimeError
        from . import synthesis as _synth
        from .itemdata import _read_text
        base = _read_text(find_game_path(None) / "StreamingAssets" / "Data"
                          / "Items" / "Synthesis.csv")
        out: dict = {}
        for mint, _shop, _price, result, _ing, _c in _synth.recipe_rows(blocks, base):
            out.setdefault(int(result), mint)            # first wins on a dup result
        return out
    except (OSError, RuntimeError, ValueError):
        return {}


def hud_value(v) -> str:
    """Resolve one hud VALUE SOURCE for :meth:`behavior.FieldBehavior.hud`: an
    ``item:<name-or-id>`` source gets its item resolved to the numeric id here
    (the compiler layer only speaks ids); everything else passes through."""
    v = str(v)
    if v.startswith("item:"):
        from .. import items as _items
        return f"item:{_items.resolve(v[5:])}"
    return v


def hud_mes_text(row: dict) -> str:
    """The final ``.mes`` text for a hud row: the author's text with ``[IMME]``
    (never type in) and ``[NFOC]`` (NoFocus -> ``Dialog.FlagButtonInh``, so the
    player's confirm can NEVER close the strip — playtest 2: clicking through a
    dialogue closed the HUD permanently) prepended when absent."""
    t = str(row.get("text", ""))
    for tag in ("[NFOC]", "[IMME]"):
        if tag not in t:
            t = tag + t
    return t


def schedule_rows(raw: dict) -> list:
    b = table(raw)
    return list((b.get("schedule", []) if b else []) or [])


def pool_menu_choice(raw: dict, request_flag: int):
    """The index of the ZONE [[choice]] whose options set this pool's request flag —
    the parked hire menu a button poller RunScriptSyncs. Returns (index, count):
    ``count`` != 1 is a validate error for a button pool (0 = no menu authored,
    2+ = ambiguous)."""
    hits = []
    for c, ch in enumerate(raw.get("choice", []) or []):
        if "zone" not in ch:
            continue
        for o in ch.get("options", []) or []:
            sf = o.get("set_flag")
            if isinstance(sf, (list, tuple)) and sf and int(sf[0]) == int(request_flag):
                hits.append(c)
                break
    return (hits[0] if hits else None), len(hits)


def marker_paths(raw: dict) -> dict:
    """{marker name: (points, closed)} for every [[marker]] carrying a ``path``."""
    out = {}
    for m in raw.get("marker", []) or []:
        if m.get("name") and m.get("path"):
            out[m["name"]] = ([(float(p[0]), float(p[1])) for p in m["path"]],
                              bool(m.get("closed", False)))
    return out


def announce_lines(raw: dict) -> list:
    """(unit_idx, branch_idx, branch dict) for every branch minting its own
    ``announce`` text — registered in this exact order by ``collect_text``."""
    out = []
    for ui, u in enumerate(units(raw)):
        for bi, br in enumerate(u.get("branch", []) or []):
            do = br.get("do")
            if isinstance(do, dict) and isinstance(do.get("announce"), str):
                out.append((ui, bi, br))
    return out


def route_names(raw: dict) -> set:
    """Route-marker names referenced by patrol/march/flee verbs (for lint sweeps)."""
    names = set()
    for u in units(raw):
        for br in u.get("branch", []) or []:
            do = br.get("do")
            if not isinstance(do, dict):
                continue
            for verb in ("patrol", "march"):
                if isinstance(do.get(verb), str):
                    names.add(do[verb])
            if "flee" in do and isinstance(do.get("to"), str):
                names.add(do["to"])
    return names


ROUTE_CEILING = 8                    # Patrol/March take 2..8 points (unrolled if-chain)


def movement_route_refs(raw: dict) -> list:
    """Every patrol/march/flee route reference, in TOML order:
    ``{"ui", "bi", "unit", "verb", "value" (marker name or inline list),
    "autoroute" (bool)}``. The lint sweep and the autoroute plan iterate THIS, so
    what's checked == what's compiled."""
    refs = []
    for ui, u in enumerate(units(raw)):
        for bi, br in enumerate(u.get("branch", []) or []):
            do = br.get("do")
            if not isinstance(do, dict):
                continue
            for verb in ("patrol", "march"):
                if verb in do:
                    refs.append({"ui": ui, "bi": bi, "unit": str(u.get("npc")),
                                 "verb": verb, "value": do[verb],
                                 "autoroute": do.get("route") == "auto"})
            if "flee" in do and "to" in do:
                refs.append({"ui": ui, "bi": bi, "unit": str(u.get("npc")),
                             "verb": "flee", "value": do["to"], "autoroute": False})
    return refs


def _engagement_radius(branch: dict, target: str):
    """The tightest ``near``/``any_near`` radius in ``branch`` that binds ``target``.

    A branch's ``when`` rows are ANDed, so the smallest radius naming the target is
    what actually gates the action; ``None`` = the branch never bounds the distance to
    that target, so the pursuit family is the whole field. ``not_near`` is IGNORED (it
    excludes CLOSE pairs, which would widen the family, so honouring it could only make
    the report louder on a construct nobody writes)."""
    best = None
    for c in (branch.get("when") or []):
        if not isinstance(c, dict):
            continue
        r = None
        if isinstance(c.get("near"), (list, tuple)) and len(c["near"]) >= 2 \
                and str(c["near"][0]) == target:
            r = int(c["near"][1])
        elif isinstance(c.get("any_near"), (list, tuple)) and len(c["any_near"]) >= 2 \
                and target in [str(t) for t in c["any_near"][0]]:
            r = int(c["any_near"][1])
        if r is not None and (best is None or r < best):
            best = r
    return best


def _source_box(branch: dict, positions: dict):
    """A ``(x0, x1, z0, z1)`` restriction on where the ACTING unit can be, from a
    ``near_point`` row (Chebyshev, matching the compiler's box), else ``None``."""
    box = None
    for c in (branch.get("when") or []):
        if not isinstance(c, dict) or not isinstance(c.get("near_point"), (list, tuple)):
            continue
        v = c["near_point"]
        if len(v) < 2:
            continue
        try:
            px, pz = _resolve_point(v[0], positions, "near_point")
        except BehaviorTomlError:
            continue
        r = int(v[1])
        b = (px - r, px + r, pz - r, pz + r)
        box = b if box is None else (max(box[0], b[0]), min(box[1], b[1]),
                                     max(box[2], b[2]), min(box[3], b[3]))
    return box


def pursuit_refs(raw: dict) -> list:
    """Every DYNAMIC movement reference (``chase`` / ``wander``), in TOML order — the
    pursuit-sweep analogue of :func:`movement_route_refs`.

    These are the feeds ``route = "auto"`` REFUSES: their destination is a runtime
    position, so there is no build-time line to splice (the Path-B study). What IS
    checkable is the family of legs the branch's own engagement gate admits. Each row:
    ``{"ui", "bi", "unit", "verb", "target", "radius" (None = ungated), "standoff",
    "source_box", "target_box"}``."""
    positions = _npc_marker_positions(raw)
    refs = []
    for ui, u in enumerate(units(raw)):
        for bi, br in enumerate(u.get("branch", []) or []):
            do = br.get("do")
            if not isinstance(do, dict):
                continue
            if "chase" in do:
                tgt = str(do["chase"])
                refs.append({"ui": ui, "bi": bi, "unit": str(u.get("npc")),
                             "verb": "chase", "target": tgt,
                             "radius": _engagement_radius(br, tgt),
                             "standoff": int(do.get("standoff", 140)),
                             "source_box": _source_box(br, positions),
                             "target_box": None})
            if "wander" in do:
                try:
                    cx, cz = _resolve_point(do["wander"], positions, "wander")
                except BehaviorTomlError:
                    continue                   # unresolvable -> validate reported it
                r = int(do.get("radius", 400))
                box = (cx - r, cx + r, cz - r, cz + r)
                # a roll lands anywhere in the box, so the walker can be at one corner
                # and its fresh target at the other: the family spans 2r per axis
                refs.append({"ui": ui, "bi": bi, "unit": str(u.get("npc")),
                             "verb": "wander", "target": f"({cx},{cz})+-{r}",
                             "radius": 2 * r, "standoff": 0,
                             "source_box": box, "target_box": box})
    return refs


def wants_autoroute(raw: dict) -> bool:
    """True when any patrol/march sets ``route = "auto"`` — the only case the build
    needs a walkmesh (a field without the key never resolves one: byte-identical)."""
    return any(r["autoroute"] for r in movement_route_refs(raw))


def _route_label(value) -> str:
    return f"'{value}'" if isinstance(value, str) else "inline route"


def autoroute_plan(raw: dict, wmesh) -> dict:
    """Compute the routed point list for every ``route = "auto"`` patrol/march.

    Returns ``{(ui, bi): {"verb", "label", "points", "inserted"}}`` — ``points`` is the
    post-splice list ``build`` compiles, ``inserted`` the ``[(leg, [waypoints])]``
    detours (empty = every leg was already clear and the authored points survive
    byte-for-byte). Patrol routes its WRAP leg too (the compiler always cycles
    ``(i+1)%n``); march is open-ended. Deterministic: pure A* over the walkmesh, TOML
    order, walls-only obstacles. Raises :class:`BehaviorTomlError` naming the field,
    unit, branch, and leg on an unroutable leg or a waypoint-ceiling overflow."""
    from . import pathfind as _pathfind
    plan: dict = {}
    refs = [r for r in movement_route_refs(raw) if r["autoroute"]]
    if not refs:
        return plan
    fld = raw.get("field", {}) or {}
    where = f"field {fld.get('id', '?')} {fld.get('name', '')!r}"
    if wmesh is None:
        raise BehaviorTomlError(
            f"{where}: route = \"auto\" needs a resolvable walkmesh (none was found) -- "
            f"the routed bytes must match what the build compiles")
    positions = _npc_marker_positions(raw)
    mpaths = marker_paths(raw)
    for r in refs:
        ctx = (f"{where} [[behavior.unit]] {r['unit']!r} branch #{r['bi']}: "
               f"{r['verb']} {_route_label(r['value'])}")
        pts = _resolve_route(r["value"], positions, mpaths, ctx)
        closed = r["verb"] == "patrol"
        try:
            routed, inserted = _pathfind.route_polyline(wmesh, pts, closed=closed)
        except _pathfind.RouteLegError as e:
            raise BehaviorTomlError(f"{ctx} route=\"auto\": {e}") from e
        if len(routed) > ROUTE_CEILING and inserted:
            worst = max(inserted, key=lambda li: len(li[1]))
            a = pts[worst[0]] if worst[0] < len(pts) else pts[0]
            b = pts[(worst[0] + 1) % len(pts)]
            raise BehaviorTomlError(
                f"{ctx} route=\"auto\": the routed route needs {len(routed)} points but "
                f"{r['verb']} takes at most {ROUTE_CEILING} (the compiler unrolls the "
                f"waypoint chain). Biggest detour: leg {worst[0] + 1} "
                f"({a[0]:.0f},{a[1]:.0f})->({b[0]:.0f},{b[1]:.0f}) "
                f"needs +{len(worst[1])} waypoints. Split the route into two markers, or "
                f"relay the jamming leg by hand so fewer detours are needed")
        plan[(r["ui"], r["bi"])] = {"verb": r["verb"], "label": _route_label(r["value"]),
                                    "points": routed, "inserted": inserted}
    return plan


def describe_autoroute(plan: dict, raw: dict) -> list:
    """Human-readable lines for the legs the plan actually re-routed (empty plan
    entries — every leg clear — stay quiet). Shared by build warnings, ``behavior
    lint``, and ``behavior compile`` so all three tell the same story."""
    lines = []
    us = units(raw)
    for (ui, bi), p in plan.items():
        unit = str(us[ui].get("npc")) if ui < len(us) else "?"
        for leg, wps in p["inserted"]:
            lines.append(
                f"{p['verb']} {p['label']} (unit {unit!r} branch #{bi}): leg {leg + 1} "
                f"auto-routed around an off-mesh span, +{len(wps)} waypoint(s) "
                f"({len(p['points'])}/{ROUTE_CEILING} points used)")
    return lines


def _build_cond(fb: B.FieldBehavior, me: str, d: dict, positions: dict, ctx: str):
    verb = _one_verb(d, COND_VERBS, ctx)
    v = d[verb]
    if verb in ("hp_le", "hp_gt"):
        unit, n = (me, v) if isinstance(v, (int, float)) else (str(v[0]), int(v[1]))
        return fb.hp_le(unit, int(n)) if verb == "hp_le" else fb.hp_gt(unit, int(n))
    if verb in ("near", "not_near"):
        tgt, r = str(v[0]), int(v[1])
        c = fb.near(me, tgt, r)
        return B.Invert(c) if verb == "not_near" else c
    if verb in ("near_point", "not_near_point"):
        pt = _resolve_point(v[0], positions, ctx)
        c = fb.near_point(me, pt, int(v[1]))
        return B.Invert(c) if verb == "not_near_point" else c
    if verb in ("flag", "not_flag"):
        c = fb.flag(str(v))
        return B.Invert(c) if verb == "not_flag" else c
    if verb == "any_flag":
        return fb.any_flag(*[str(n) for n in v])
    if verb == "time_below":
        return fb.time_below(int(v))
    if verb == "time_above":
        return fb.time_above(int(v))
    if verb == "have_item":
        # "Potion" (>= 1) or ["Potion", 2]; names resolved like every item key
        from .. import items as _items
        entry, n = (v, 1) if not isinstance(v, list) else (v[0], int(v[1]) if len(v) > 1 else 1)
        return fb.have_item(_items.resolve(entry), n)
    if verb in ("counter_ge", "counter_le", "counter_eq"):
        return getattr(fb, verb)(str(v[0]), int(v[1]))
    if verb in ("table_ge", "table_le", "table_eq"):
        idx = v[1] if isinstance(v[1], str) else int(v[1])
        return getattr(fb, verb)(str(v[0]), idx, int(v[2]))
    if verb == "any_near":
        # THE WATCHER IDIOM: any of these units within r of me, each behind its own
        # active gate -- any_of(all_of(active(t), near(me, t, r)), ...)
        targets, r = [str(t) for t in v[0]], int(v[1])
        legs = [fb.all_of(fb.active(t), fb.near(me, t, r)) for t in targets]
        return legs[0] if len(legs) == 1 else fb.any_of(*legs)
    if verb == "any_active":
        return fb.any_flag(*[f"{str(t)}.active" for t in v])
    c = fb.active(str(v))
    return B.Invert(c) if verb == "not_active" else c


def _build_action(fb: B.FieldBehavior, d: dict, *, positions, mpaths, txid, npc_txid,
                  ctx: str, routed_points=None, model=None):
    verb = _one_verb(d, ACTION_VERBS, ctx)
    v = d[verb]
    spd = d.get("speed")
    if "route" in d:
        if d["route"] != "auto":
            raise BehaviorTomlError(f"{ctx}: route = {d['route']!r} -- the only value is "
                                    f"\"auto\"")
        if routed_points is None:
            raise BehaviorTomlError(
                f"{ctx}: route = \"auto\" but no autoroute plan was passed -- the caller "
                f"must run autoroute_plan(raw, wmesh) and hand build() the result "
                f"(routing silently skipped would ship the jamming route)")
    if verb == "walk_to":
        return B.WalkTo(_resolve_point(v, positions, ctx), speed=spd)
    if verb == "hold":
        return B.Hold(_resolve_point(v, positions, ctx), speed=spd)
    if verb == "hold_post":
        if v is not True:
            raise BehaviorTomlError(f"{ctx}: hold_post takes `true` (it holds the unit's "
                                    f"own placement post — no point argument)")
        return B.HoldPost(speed=spd)
    if verb == "chase":
        return B.Chase(str(v), standoff=int(d.get("standoff", 140)), speed=spd)
    if verb == "patrol":
        pts = routed_points if routed_points is not None \
            else _resolve_route(v, positions, mpaths, ctx)
        return B.Patrol(pts, arrive_r=int(d.get("arrive_r", 150)), speed=spd)
    if verb == "march":
        pts = routed_points if routed_points is not None \
            else _resolve_route(v, positions, mpaths, ctx)
        return B.March(pts, arrive_r=int(d.get("arrive_r", 150)), speed=spd)
    if verb == "flee":
        if "to" not in d:
            raise BehaviorTomlError(f"{ctx}: flee needs `to = [refuge points]`")
        return B.Flee(str(v), _resolve_route(d["to"], positions, mpaths, ctx),
                      avoid_r=int(d.get("avoid_r", 600)), speed=spd)
    if verb == "wander":
        return B.Wander(_resolve_point(v, positions, ctx),
                        radius=int(d.get("radius", 400)),
                        hold=int(d.get("every", 90)), speed=spd)
    if verb == "swing_at":
        return B.SwingAt(str(v), interval=int(d.get("interval", 30)),
                         damage=int(d.get("damage", 1)),
                         anim=(resolve_gesture(d["anim"], model, ctx)
                               if d.get("anim") is not None else None),
                         hit_sfx=(int(d["hit_sfx"])
                                  if d.get("hit_sfx") is not None else None))
    if verb == "hold_ground":
        if v is not True:
            raise BehaviorTomlError(f"{ctx}: hold_ground takes `true` (stand and "
                                    f"idle while the branch holds — the pin)")
        return B.HoldGround()
    if verb == "die":
        # die = true, or die = "kills" (bump that counter once — the body runs
        # exactly once, the entry terminates); + THE DEATH BEAT (anim, linger)
        return B.Die(count=(str(v) if isinstance(v, str) else None),
                     anim=(resolve_gesture(d["anim"], model, ctx)
                           if d.get("anim") is not None else None),
                     linger=int(d.get("linger", 0)))
    if verb == "battle":
        return B.Battle(int(v))
    if verb == "award":
        # award = <gil int> (+ item = name/id, count = n); exactly-once BY the
        # event-Once machinery — validate requires `once` on the branch
        return B.Award(gil=int(v), item=d.get("item"), count=int(d.get("count", 1)))
    if verb in ("add_shop_item", "remove_shop_item"):
        # [shop_id, item] — the AddShopItem 0x115 runtime stock mutation; the same
        # event-Once lane as award (session-global state, re-asserted per entry)
        return B.ShopStock(shop=int(v[0]), item=v[1], add=(verb == "add_shop_item"))
    if verb in ("add_shop_synth", "remove_shop_synth"):
        # [shop_id, recipe] — AddShopSynthesis 0x116; recipe = a vanilla int id or
        # a [[synthesis]] RESULT name (resolved via fb.synth_mints at compile)
        return B.ShopSynth(shop=int(v[0]), synth=v[1], add=(verb == "add_shop_synth"))
    if verb == "sfx":
        # sfx = <sound id> (+ bank, sustain) — RunSoundCode3, chest-proven params
        return B.Sfx(int(v), bank=int(d.get("bank", B.SFX_BANK)),
                     sustain=int(d.get("sustain", 0)))
    if verb == "stop_timer":
        # stop_timer = true — RunTimer(0); freezes the countdown at its reading
        return B.StopTimer()
    if verb == "flash":
        # flash = [r, g, b] (+ pause frames) — stock's ADD-channel flash pair
        # (the option is `pause`, not `hold` — `hold` is the feed verb)
        return B.Flash(tuple(int(c) for c in v),
                       pause=int(d.get("pause", B.FLASH_PAUSE_FRAMES)))
    if verb == "announce":
        if txid is None:
            raise BehaviorTomlError(f"{ctx}: no minted txid for this announce line "
                                    f"(collect_text must register it)")
        return B.Announce(int(txid), window=int(d.get("window", 0)),
                          delay=int(d.get("delay", 0)),
                          sustain=int(d.get("sustain", 0)))
    # announce_npc
    if npc_txid is None:
        raise BehaviorTomlError(f"{ctx}: announce_npc = {v!r} — that NPC has no dialogue line")
    return B.Announce(int(npc_txid), window=int(d.get("window", 0)),
                      delay=int(d.get("delay", 0)),
                      sustain=int(d.get("sustain", 0)))


def build(raw: dict, *, npc_slots: dict, npc_txids_by_name: dict | None = None,
          behavior_txids: dict | None = None,
          routed: dict | None = None) -> B.FieldBehavior | None:
    """Construct the :class:`FieldBehavior` from the ``[behavior]`` table.

    ``npc_slots``: npc name -> entry slot (the build's own injection map — no
    discovery needed). ``npc_txids_by_name``: npc name -> its dialogue txid (for
    ``announce_npc``). ``behavior_txids``: ``(unit_idx, branch_idx) -> txid`` for
    minted ``announce`` lines (from ``collect_text``). ``routed``: the
    :func:`autoroute_plan` result when any verb sets ``route = "auto"`` (a branch
    carrying the key with no plan entry is an ERROR — routing must never silently
    skip). Construction order is the TOML order — the deterministic-allocation
    contract."""
    b = table(raw)
    if not b:
        return None
    behavior_txids = behavior_txids or {}
    routed = routed or {}
    npc_txids_by_name = npc_txids_by_name or {}
    positions = _npc_marker_positions(raw)
    mpaths = marker_paths(raw)

    specs = []
    for ui, u in enumerate(b.get("unit", [])):
        name = str(u.get("npc") or "")
        if name not in npc_slots:
            raise BehaviorTomlError(f"[[behavior.unit]] #{ui}: npc {name!r} is not an "
                                    f"injected named [[npc]] (known: {sorted(npc_slots)})")
        npc = next((n for n in raw.get("npc", []) if n.get("name") == name), {})
        pos = npc.get("pos") or (0, 0)
        specs.append(B.UnitSpec(name, int(npc_slots[name]),
                                spawn=(int(pos[0]), int(pos[1])),
                                hp=(int(u["hp"]) if u.get("hp") is not None else None),
                                walk_speed=int(u.get("speed", 50)),
                                pooled=bool(u.get("pooled", False)),
                                pool=str(u.get("pool", "pool"))))
    band = str(b.get("byte_band", "safe"))
    if band not in ("safe", "wide"):
        raise BehaviorTomlError('[behavior] byte_band must be "safe" (campaign-compatible, the '
                                'default) or "wide" (the historical 770-byte band, bytes 1220-1989 '
                                '-- overlaps campaign per-member flag windows; standalone-only)')
    bb = B.Blackboard(byte_base=B.WIDE_BYTE_BASE) if band == "wide" else None
    fb = B.FieldBehavior(specs, blackboard=bb,
                         warmup=int(b.get("warmup", 45)), tick=int(b.get("tick", 1)),
                         pools=pool_specs(raw),
                         timer=(int(b["timer"]) if b.get("timer") is not None else None),
                         tables=table_specs(raw), counters=counter_names(raw),
                         brains=bool(b.get("brains", False)))
    fb.synth_mints = synth_mint_map(raw)                  # ShopSynth string selectors
    for nm in b.get("public_flags", []) or []:
        fb.public_flag(str(nm))
    for alt in b.get("alternators", []) or []:
        fb.alternator(str(alt["name"]), int(alt["frames"]))
    for s in schedule_rows(raw):
        fb.schedule(str(s.get("counter", "")), str(s.get("table", "")))
    for gr in b.get("group", []) or []:
        fb.group(str(gr.get("name", "")),
                 [str(u) for u in gr.get("units", []) or []])
    for s in b.get("scan", []) or []:
        fb.scan(str(s.get("name", "")),
                units=([str(u) for u in s["units"]] if s.get("units") else None),
                point=(tuple(s["point"]) if s.get("point") is not None else None),
                radius=(int(s["radius"]) if s.get("radius") is not None else None),
                count=str(s.get("count", "")),
                flags=(str(s["flags"]) if s.get("flags") else None),
                group=(str(s["group"]) if s.get("group") else None),
                alive_only=bool(s.get("alive_only", False)))
    for hi, h in hud_lines(raw):
        fb.hud(str(h.get("text", "")),
               [hud_value(v) for v in h.get("values", []) or []],
               window=int(h.get("window", 6)),
               txid=behavior_txids.get(("hud", hi)),
               digits=(list(h["digits"]) if isinstance(h.get("digits"), list)
                       else int(h.get("digits", 2))))

    for ui, u in enumerate(b.get("unit", [])):
        name = str(u["npc"])
        # the unit's own MODEL — gesture names resolve against it (the own-clip law)
        umodel = next((n.get("model") for n in raw.get("npc", []) or []
                       if n.get("name") == name), None)
        branches = []
        for bi, br in enumerate(u.get("branch", []) or []):
            ctx = f"[[behavior.unit]] {name!r} branch #{bi}"
            extra = set(br) - BRANCH_KEYS
            if extra:
                raise BehaviorTomlError(f"{ctx}: unknown key(s) {sorted(extra)}")
            if "do" not in br:
                raise BehaviorTomlError(f"{ctx}: needs a `do` action")
            if br.get("once") is not None and br.get("cooldown") is not None:
                raise BehaviorTomlError(f"{ctx}: once and cooldown are mutually exclusive")
            do = br["do"]
            if isinstance(do, dict) and "engage" in do:
                # THE GROUP LOOP verb — expands to the two-phase subtree
                # (contact -> strike dispatch / else -> pursue feed) through
                # the standard node vocabulary; the acquire loop registers
                # with the unit. No raise/clear flags in v2 rung 1.
                if br.get("raise_flags") or br.get("clear_flags"):
                    raise BehaviorTomlError(
                        f"{ctx}: engage takes no raise_flags/clear_flags")
                sub = fb.engage_node(name, B.Engage(
                    group=str(do["engage"]),
                    radius=int(do.get("radius", 900)),
                    contact=int(do.get("contact", 170)),
                    damage=int(do.get("damage", 1)),
                    interval=int(do.get("interval", 25)),
                    speed=(int(do["speed"]) if do.get("speed") is not None
                           else None),
                    nearest=bool(do.get("nearest", False)),
                    anim=(resolve_gesture(do["anim"], umodel, ctx)
                          if do.get("anim") is not None else None),
                    hit_sfx=(int(do["hit_sfx"])
                             if do.get("hit_sfx") is not None else None)))
                conds = [_build_cond(fb, name, c, positions, ctx)
                         for c in (br.get("when") or [])]
                node = B.Sequence(*conds, sub) if conds else sub
                if br.get("once") is not None:
                    node = B.Once(str(br["once"]), node)
                elif br.get("cooldown") is not None:
                    node = B.Cooldown(int(br["cooldown"]), node)
                branches.append(node)
                continue
            npc_txid = None
            if isinstance(do, dict) and "announce_npc" in do:
                npc_txid = npc_txids_by_name.get(str(do["announce_npc"]))
            rp = routed.get((ui, bi))
            action = _build_action(fb, do, positions=positions, mpaths=mpaths,
                                   txid=behavior_txids.get((ui, bi)),
                                   npc_txid=npc_txid, ctx=ctx,
                                   routed_points=(rp["points"] if rp else None),
                                   model=umodel)
            do_node = B.Do(action, raise_flags=tuple(br.get("raise_flags", []) or []),
                           clear_flags=tuple(br.get("clear_flags", []) or []))
            conds = [_build_cond(fb, name, c, positions, ctx)
                     for c in (br.get("when") or [])]
            node = B.Sequence(*conds, do_node) if conds else do_node
            if br.get("once") is not None:
                node = B.Once(str(br["once"]), node)
            elif br.get("cooldown") is not None:
                node = B.Cooldown(int(br["cooldown"]), node)
            branches.append(node)
        if not branches:
            raise BehaviorTomlError(f"[[behavior.unit]] {name!r}: no branches")
        fb.units[name].tree = B.Selector(*branches)
    return fb


def _npc_marker_positions(raw: dict) -> dict:
    """name -> (x, z) over named NPCs, markers, and the player spawn — the same
    registry shape build's cutscenes use, computed locally so the module stands
    alone (CLI use has no FieldProject)."""
    reg = {}
    sp = (raw.get("player", {}) or {}).get("spawn")
    if sp:
        reg["player"] = reg["spawn"] = (int(sp[0]), int(sp[1]))
    for n in raw.get("npc", []) or []:
        if n.get("name") and n.get("pos"):
            reg[n["name"]] = (int(n["pos"][0]), int(n["pos"][1]))
    for m in raw.get("marker", []) or []:
        if m.get("name") and m.get("pos"):
            reg[m["name"]] = (int(m["pos"][0]), int(m["pos"][1]))
    return reg


def validate(raw: dict, *, verbatim: bool = False) -> list:
    """Static problems with the [behavior] table (build ``validate()`` + `behavior
    lint`). Structural only — a full dry compile is the CLI's job."""
    b = table(raw)
    if not b:
        return []
    problems = []
    if verbatim:
        problems.append("[behavior] on a VERBATIM fork is not wired (the donor's real .eb "
                        "runs; behavior needs the kit's injected NPC entries) — use a "
                        "--native/--editable fork or a novel field")
        return problems
    extra = set(b) - FIELD_KEYS
    if extra:
        problems.append(f"[behavior]: unknown key(s) {sorted(extra)}")
    if b.get("timer") is not None and (not isinstance(b["timer"], int)
                                       or not 1 <= b["timer"] <= 30000):
        problems.append("[behavior]: timer must be an int 1..30000 (seconds — the "
                        "countdown HUD)")
    npc_names = {n.get("name") for n in raw.get("npc", []) or [] if n.get("name")}
    unit_names = []
    positions = _npc_marker_positions(raw)
    mpaths = marker_paths(raw)
    for ui, u in enumerate(b.get("unit", [])):
        ctx = f"[[behavior.unit]] #{ui}"
        extra = set(u) - UNIT_KEYS
        if extra:
            problems.append(f"{ctx}: unknown key(s) {sorted(extra)}")
        name = u.get("npc")
        if not name:
            problems.append(f"{ctx}: needs `npc = ` naming a [[npc]]")
            continue
        if name not in npc_names:
            problems.append(f"{ctx}: npc {name!r} is not a named [[npc]]")
        if name in unit_names:
            problems.append(f"{ctx}: duplicate unit for npc {name!r}")
        unit_names.append(name)
        npc = next((n for n in raw.get("npc", []) or [] if n.get("name") == name), {})
        for bad_key, why in (("holds", "a held-prop NPC's entry layout differs"),
                             ("requires_flag", "reveal-gating conflicts with the warm-up wake"),
                             ("scenario_min", "scenario gating conflicts with the warm-up wake"),
                             ("scenario_max", "scenario gating conflicts with the warm-up wake")):
            if npc.get(bad_key) is not None:
                problems.append(f"{ctx}: npc {name!r} has `{bad_key}` — {why}; not supported "
                                f"on a behavior unit"
                                + (" (a pooled unit needs NO flag — the build itself skips "
                                   "its boot spawn)" if bad_key == "requires_flag"
                                   and u.get("pooled") else ""))
        if u.get("pooled") is not None and not isinstance(u.get("pooled"), bool):
            problems.append(f"{ctx}: pooled must be true/false")
        if u.get("pool") is not None:
            if not u.get("pooled"):
                problems.append(f"{ctx}: `pool =` needs `pooled = true`")
            import re as _re
            if not _re.fullmatch(r"[A-Za-z0-9_]+", str(u.get("pool"))):
                problems.append(f"{ctx}: pool name {u.get('pool')!r} must be [A-Za-z0-9_]+")
        if u.get("pooled"):
            att = [p.get("prop") or p.get("model") for p in raw.get("prop", []) or []
                   if p.get("attach_to") == name]
            if att:
                problems.append(f"{ctx}: prop(s) {att} attach_to pooled npc {name!r} — a "
                                f"boot-spawned prop cannot bind to a not-yet-spawned unit")
    # [[behavior.pool]] rows: economy/UX config per pool
    declared_pools = {str(u.get("pool", "pool")) for u in b.get("unit", [])
                      if u.get("pooled")}
    seen_pool_rows = set()
    for pi, row in enumerate(b.get("pool", []) or []):
        ctx = f"[[behavior.pool]] #{pi}"
        extra = set(row) - POOL_KEYS
        if extra:
            problems.append(f"{ctx}: unknown key(s) {sorted(extra)}")
        nm = row.get("name")
        if not nm:
            problems.append(f"{ctx}: needs `name = ` (a pooled unit's pool)")
            continue
        if nm not in declared_pools:
            problems.append(f"{ctx}: no pooled unit declares pool = {nm!r}")
        if nm in seen_pool_rows:
            problems.append(f"{ctx}: pool {nm!r} configured twice")
        seen_pool_rows.add(nm)
        if row.get("price") is not None and (not isinstance(row["price"], int)
                                             or not 0 <= row["price"] <= 0xFFFFFF):
            problems.append(f"{ctx}: price must be an int 0..16777215 (24-bit gil)")
        if row.get("item") is not None:
            # THE ITEM POOL (the shop bridge): holding the item IS the request —
            # no flag lane, so the request/button/price machinery is off-limits
            try:
                from .. import items as _items
                _items.resolve(row["item"])
            except Exception as e:
                problems.append(f"{ctx}: item {row['item']!r} does not resolve ({e})")
            for bad in ("price", "button", "request_flag"):
                if row.get(bad) is not None:
                    problems.append(f"{ctx}: item is exclusive with {bad} — the item IS "
                                    f"the price and the request (the shop is the menu)")
        btn = row.get("button")
        if btn is not None and not isinstance(btn, (bool, int)):
            problems.append(f"{ctx}: button must be true or a PSX button-mask int")
        rf = row.get("request_flag")
        if rf is not None and not isinstance(rf, int):
            problems.append(f"{ctx}: request_flag must be a GLOB bit index int")
        if btn:
            if rf is None:
                problems.append(f"{ctx}: button needs an explicit request_flag = N "
                                f"(the parked hire [[choice]] row must set_flag it)")
            else:
                _idx, n = pool_menu_choice(raw, rf)
                if n == 0:
                    problems.append(f"{ctx}: no zone [[choice]] sets flag {rf} — author "
                                    f"the parked hire menu (a zone choice parked far "
                                    f"off-mesh; its Hire row set_flag = [{rf}, 1])")
                elif n > 1:
                    problems.append(f"{ctx}: {n} zone [[choice]]s set flag {rf} — the "
                                    f"hire menu match must be unique")
    # data tables / counters / schedules (the 0xD3 VECTOR lane)
    import re as _re2
    declared_counters = []
    for ci, cn in enumerate(b.get("counters", []) or []):
        if not _re2.fullmatch(r"[A-Za-z0-9_]+", str(cn)):
            problems.append(f"[behavior] counters #{ci}: name {cn!r} must be [A-Za-z0-9_]+")
        if str(cn) in declared_counters:
            problems.append(f"[behavior] counters: duplicate {cn!r}")
        declared_counters.append(str(cn))
    declared_tables: dict = {}
    seen_tids = set()
    for ti, row in enumerate(b.get("table", []) or []):
        ctx = f"[[behavior.table]] #{ti}"
        extra = set(row) - TABLE_KEYS
        if extra:
            problems.append(f"{ctx}: unknown key(s) {sorted(extra)}")
        nm = row.get("name")
        if not nm or not _re2.fullmatch(r"[A-Za-z0-9_]+", str(nm)):
            problems.append(f"{ctx}: needs `name = ` ([A-Za-z0-9_]+)")
            nm = None
        elif str(nm) in declared_tables:
            problems.append(f"{ctx}: duplicate table {nm!r}")
        elif str(nm) in declared_counters:
            problems.append(f"{ctx}: table {nm!r} collides with a counter name")
        vals = row.get("values")
        if (not isinstance(vals, list) or not vals
                or len(vals) > B.TABLE_MAX_LEN
                or any(not isinstance(v, int) for v in vals)):
            problems.append(f"{ctx}: values must be 1..{B.TABLE_MAX_LEN} ints")
        elif any(not B.TABLE_VALUE_MIN <= v <= B.TABLE_VALUE_MAX for v in vals):
            problems.append(f"{ctx}: values must sit in the 26-bit CalcStack domain "
                            f"({B.TABLE_VALUE_MIN}..{B.TABLE_VALUE_MAX})")
        if nm is not None:
            declared_tables[str(nm)] = len(vals) if isinstance(vals, list) else 0
        tid = row.get("id")
        if tid is not None:
            if not isinstance(tid, int) or not 0 <= tid <= B.TABLE_VALUE_MAX:
                problems.append(f"{ctx}: id must be an int 0..{B.TABLE_VALUE_MAX} "
                                f"(a gScriptVector id)")
            elif tid in seen_tids:
                problems.append(f"{ctx}: id {tid} used twice")
            else:
                seen_tids.add(tid)
    scheduled = set()
    for si, row in enumerate(b.get("schedule", []) or []):
        ctx = f"[[behavior.schedule]] #{si}"
        extra = set(row) - SCHEDULE_KEYS
        if extra:
            problems.append(f"{ctx}: unknown key(s) {sorted(extra)}")
        cn, tn = str(row.get("counter", "")), str(row.get("table", ""))
        if cn not in declared_counters:
            problems.append(f"{ctx}: counter {cn!r} is not in [behavior] counters")
        elif cn in scheduled:
            problems.append(f"{ctx}: counter {cn!r} already has a schedule")
        scheduled.add(cn)
        if tn not in declared_tables:
            problems.append(f"{ctx}: table {tn!r} is not a [[behavior.table]]")
        if b.get("timer") is None:
            problems.append(f"{ctx}: a schedule needs field-level `timer = <seconds>` "
                            f"(the countdown HUD is the clock it reads)")
    # groups (the engage rosters — v2)
    declared_groups: dict = {}
    member_of: dict = {}
    _hp_units = {u.get("npc") for u in b.get("unit", []) if u.get("hp") is not None}
    for gi, row in enumerate(b.get("group", []) or []):
        ctx = f"[[behavior.group]] #{gi}"
        extra = set(row) - GROUP_KEYS
        if extra:
            problems.append(f"{ctx}: unknown key(s) {sorted(extra)}")
        nm = str(row.get("name", ""))
        if not _re2.fullmatch(r"[a-z][a-z0-9_]*", nm):
            problems.append(f"{ctx}: needs `name = ` ([a-z][a-z0-9_]*)")
        elif nm in declared_groups:
            problems.append(f"{ctx}: duplicate group {nm!r}")
        us = row.get("units")
        if not isinstance(us, list) or not us:
            problems.append(f"{ctx}: needs `units = [<behavior unit npcs>]`")
            us = []
        if len(us) > B.TABLE_MAX_LEN:
            problems.append(f"{ctx}: {len(us)} units > the {B.TABLE_MAX_LEN}-cell cap")
        if len(set(map(str, us))) != len(us):
            problems.append(f"{ctx}: duplicate units")
        for u in us:
            un = str(u)
            if un not in unit_names:
                problems.append(f"{ctx}: {un!r} is not a [[behavior.unit]] npc")
            elif un not in _hp_units:
                problems.append(f"{ctx}: member {un!r} has no `hp` (the roster hp "
                                f"table is a member's only hit-point home)")
            if un in member_of:
                problems.append(f"{ctx}: {un!r} is already in group {member_of[un]!r}")
            member_of[un] = nm
        declared_groups[nm] = {str(u) for u in us}
        # the group's tables are readable by the table_* conds
        for suffix in ("px", "pz", "act", "hp"):
            declared_tables.setdefault(f"group.{nm}.{suffix}", len(us))
    # scans (the vector loop — v2 rung 0)
    scan_names = set()
    for si, row in enumerate(b.get("scan", []) or []):
        ctx = f"[[behavior.scan]] #{si}"
        extra = set(row) - SCAN_KEYS
        if extra:
            problems.append(f"{ctx}: unknown key(s) {sorted(extra)}")
        nm = str(row.get("name", ""))
        if not _re2.fullmatch(r"[a-z][a-z0-9_]*", nm):
            problems.append(f"{ctx}: needs `name = ` ([a-z][a-z0-9_]*)")
        elif nm in scan_names:
            problems.append(f"{ctx}: duplicate scan {nm!r}")
        scan_names.add(nm)
        gr = row.get("group")
        us = row.get("units")
        roster_len = 0
        if (gr is None) == (us is None):
            problems.append(f"{ctx}: give exactly one of units= / group=")
        if gr is not None:
            if str(gr) not in declared_groups:
                problems.append(f"{ctx}: group {gr!r} is not a [[behavior.group]]")
            else:
                roster_len = len(declared_groups[str(gr)])
        elif us is not None:
            if not isinstance(us, list) or not us:
                problems.append(f"{ctx}: needs `units = [<behavior unit npcs>]`")
            else:
                roster_len = len(us)
                if len(us) > B.TABLE_MAX_LEN:
                    problems.append(f"{ctx}: {len(us)} units > the "
                                    f"{B.TABLE_MAX_LEN}-cell cap")
                for u in us:
                    if str(u) not in unit_names:
                        problems.append(f"{ctx}: {u!r} is not a [[behavior.unit]] npc")
                if len(set(map(str, us))) != len(us):
                    problems.append(f"{ctx}: duplicate units")
        alive = row.get("alive_only", False)
        if not isinstance(alive, bool):
            problems.append(f"{ctx}: alive_only takes true/false")
        elif alive and gr is None:
            problems.append(f"{ctx}: alive_only needs group= (only a roster "
                            f"carries act/hp tables)")
        pt = row.get("point")
        r = row.get("radius")
        if (pt is None) != (r is None):
            problems.append(f"{ctx}: point and radius come together")
        if pt is None and gr is None:
            problems.append(f"{ctx}: the units form needs point/radius "
                            f"(a rosterless headcount is static — use group=)")
        if pt is not None and (not isinstance(pt, list) or len(pt) != 2
                               or any(not isinstance(v, int) for v in pt)):
            problems.append(f"{ctx}: needs `point = [x, z]` (ints)")
        if r is not None and (not isinstance(r, int) or not 1 <= r <= 30000):
            problems.append(f"{ctx}: radius must be an int 1..30000")
        cn = str(row.get("count", ""))
        if cn not in declared_counters:
            problems.append(f"{ctx}: count {cn!r} is not in [behavior] counters")
        fl = row.get("flags")
        if fl is not None and pt is None:
            problems.append(f"{ctx}: flags need a point/radius box")
        if fl is not None and str(fl) in declared_tables:
            problems.append(f"{ctx}: flags {fl!r} collides with a [[behavior.table]]")
        elif nm and roster_len:
            # scans DECLARE tables too — the flags table (user-named or the
            # scan.<name>.near default, box scans only) plus, in the units
            # form, the position pair — readable by the table_* conds
            tn_new = []
            if pt is not None:
                tn_new.append(str(fl) if fl else f"scan.{nm}.near")
            if gr is None:
                tn_new += [f"scan.{nm}.px", f"scan.{nm}.pz"]
            for tn2 in tn_new:
                declared_tables.setdefault(tn2, roster_len)
    # hud strips (the live-counter substrate)
    hud_windows = set()
    for hi, row in enumerate(b.get("hud", []) or []):
        ctx = f"[[behavior.hud]] #{hi}"
        extra = set(row) - HUD_KEYS
        if extra:
            problems.append(f"{ctx}: unknown key(s) {sorted(extra)}")
        w = row.get("window", 6)
        if not isinstance(w, int) or not 0 <= w <= 7:
            problems.append(f"{ctx}: window must be an int 0..7 (Dialog.WindowID)")
        elif w in hud_windows:
            problems.append(f"{ctx}: window {w} already carries a strip")
        hud_windows.add(w if isinstance(w, int) else -1)
        txt = str(row.get("text", ""))
        if not txt.strip():
            problems.append(f"{ctx}: needs `text = ` (the strip's .mes line — "
                            f"[NUMB=i] slots, [MPOS=x,y] to place it)")
        vals = row.get("values")
        dg = row.get("digits", 2)
        if isinstance(dg, list):
            if (not all(isinstance(d, int) and 1 <= d <= 7 for d in dg)
                    or (isinstance(vals, list) and len(dg) != len(vals))):
                problems.append(f"{ctx}: a digits LIST needs one int 1..7 per value")
        elif not isinstance(dg, int) or not 1 <= dg <= 7:
            problems.append(f"{ctx}: digits must be an int 1..7 (or a per-value "
                            f"list) — the widest value a slot will show")
        if not isinstance(vals, list) or not 1 <= len(vals) <= 8:
            problems.append(f"{ctx}: values must be 1..8 sources (the engine has "
                            f"8 gMesValue slots)")
        else:
            for v in vals:
                s = str(v)
                if s in ("gil", "timer"):
                    continue
                if s.startswith("hp:"):
                    if s[3:] not in unit_names:
                        problems.append(f"{ctx}: value {v!r} — {s[3:]!r} is not a "
                                        f"[[behavior.unit]] npc")
                    elif s[3:] not in _hp_units:
                        problems.append(f"{ctx}: value {v!r} — {s[3:]!r} has no `hp`")
                    continue
                if s.startswith("item:"):
                    try:
                        from .. import items as _items
                        _items.resolve(s[5:])
                    except Exception as e:
                        problems.append(f"{ctx}: value {v!r} — item does not "
                                        f"resolve ({e})")
                    continue
                if s not in declared_counters:
                    problems.append(f"{ctx}: value {v!r} is not a counter, "
                                    f"'gil', 'timer', 'hp:<unit>', or 'item:<item>'")
            for mnum in _re2.finditer(r"\[NUMB=(\d+)", txt):
                if int(mnum.group(1)) >= len(vals):
                    problems.append(f"{ctx}: [NUMB={mnum.group(1)}] has no value "
                                    f"(only {len(vals)} given)")
    # a behavior unit may not also be a cutscene cast actor (the conductor drives
    # actors at the same REQ level the dispatch bodies use)
    from . import cutscene as _cutscene
    cast = set()
    for cb in _cutscene.blocks(raw.get("cutscene")):
        cast |= {a for a in (cb.get("actors") or [])}
    clash = cast & set(unit_names)
    if clash:
        problems.append(f"[behavior]: unit(s) {sorted(clash)} are also [cutscene] cast actors "
                        f"— the conductor and the behavior dispatch share REQ level 4")
    valid_targets = set(unit_names) | {B.PLAYER}
    hp_units = {u.get("npc") for u in b.get("unit", []) if u.get("hp") is not None}
    engaged_units: set = set()
    for ui, u in enumerate(b.get("unit", [])):
        me = u.get("npc")
        # this unit's OWN model — bound per unit here, NOT reused from the pass
        # above (that `npc` is stale by now: the announce_npc check rebinds it)
        me_model = next((n.get("model") for n in raw.get("npc", []) or []
                         if n.get("name") == me), None)
        for bi, br in enumerate(u.get("branch", []) or []):
            ctx = f"[[behavior.unit]] {me!r} branch #{bi}"
            try:
                if "do" not in br:
                    problems.append(f"{ctx}: needs a `do` action")
                    continue
                do = br["do"]
                if isinstance(do, dict) and "route" in do:
                    if not ({"patrol", "march"} & set(do)):
                        problems.append(
                            f"{ctx}: `route = ` only applies to patrol/march -- a "
                            f"walk_to/hold/flee walk starts wherever the unit happens to "
                            f"be when the branch selects (no build-time origin to route "
                            f"from), and spliced flee points would become extra REFUGES "
                            f"(avoid_r semantics), not waypoints")
                    elif do["route"] != "auto":
                        problems.append(f"{ctx}: route = {do['route']!r} -- the only "
                                        f"value is \"auto\"")
                verb = _one_verb(do, ACTION_VERBS, ctx)
                v = do[verb]
                if verb in ("chase",) and str(v) not in valid_targets:
                    problems.append(f"{ctx}: chase target {v!r} is not a behavior unit or player")
                if verb == "swing_at":
                    if str(v) not in set(unit_names):
                        problems.append(f"{ctx}: swing_at {v!r} is not a behavior unit")
                    elif str(v) not in hp_units:
                        problems.append(f"{ctx}: swing_at {v!r} — that unit has no `hp`")
                if verb == "engage":
                    if str(v) not in declared_groups:
                        problems.append(f"{ctx}: engage group {v!r} is not a "
                                        f"[[behavior.group]]")
                    elif str(me) in declared_groups[str(v)]:
                        problems.append(f"{ctx}: {me!r} cannot engage its own "
                                        f"group {v!r}")
                    if str(me) in engaged_units:
                        problems.append(f"{ctx}: {me!r} already has an engage "
                                        f"(one target register per unit)")
                    engaged_units.add(str(me))
                    r = do.get("radius", 900)
                    c = do.get("contact", 170)
                    if not (isinstance(r, int) and 1 <= r <= 30000):
                        problems.append(f"{ctx}: engage radius must be an int 1..30000")
                    elif not (isinstance(c, int) and 1 <= c < r):
                        problems.append(f"{ctx}: engage contact must be an int "
                                        f"1..radius-1")
                    if not isinstance(do.get("nearest", False), bool):
                        problems.append(f"{ctx}: engage nearest takes true/false")
                    if br.get("raise_flags") or br.get("clear_flags"):
                        problems.append(f"{ctx}: engage takes no "
                                        f"raise_flags/clear_flags")
                if verb == "flee" and str(v) not in valid_targets:
                    problems.append(f"{ctx}: flee threat {v!r} is not a behavior unit or player")
                if verb in ("patrol", "march"):
                    _resolve_route(v, positions, mpaths, ctx)
                if verb == "flee" and "to" in do:
                    _resolve_route(do["to"], positions, mpaths, ctx)
                if verb in ("walk_to", "hold", "wander"):
                    _resolve_point(v, positions, ctx)
                if verb == "hold_post" and v is not True:
                    problems.append(f"{ctx}: hold_post takes `true` (it holds the unit's "
                                    f"own placement post)")
                if verb == "hold_ground" and v is not True:
                    problems.append(f"{ctx}: hold_ground takes `true` (stand and idle "
                                    f"while the branch holds — the pin)")
                if verb == "battle":
                    if not isinstance(v, int) or not 0 <= v <= 0xFFFF:
                        problems.append(f"{ctx}: battle takes a battle SCENE id int "
                                        f"(0..65535; a STOCK scene needs no BattlePatch)")
                if verb in ("die", "swing_at", "engage"):
                    # THE OWN-CLIP LAW at the call site: a gesture the model does
                    # not own is refused here, with the owned list in the message
                    if do.get("anim") is not None:
                        try:
                            resolve_gesture(do["anim"], me_model, ctx)
                        except BehaviorTomlError as e:
                            problems.append(str(e))
                    for opt, lo, hi in (("hit_sfx", 0, 0xFFFF),
                                        ("linger", 0, 255)):
                        ov = do.get(opt)
                        if ov is not None and (isinstance(ov, bool)
                                               or not isinstance(ov, int)
                                               or not lo <= ov <= hi):
                            problems.append(f"{ctx}: {verb} {opt} must be an int "
                                            f"{lo}..{hi}")
                if verb == "die":
                    if v is not True and not isinstance(v, str):
                        problems.append(f"{ctx}: die takes `true` or a counter name "
                                        f"(die = \"kills\" bumps it once)")
                    elif isinstance(v, str) and v not in declared_counters:
                        problems.append(f"{ctx}: die counts {v!r} — not in "
                                        f"[behavior] counters")
                if verb == "award":
                    if not isinstance(v, int) or not 0 <= v <= 0xFFFFFF:
                        problems.append(f"{ctx}: award takes a gil int 0..16777215 "
                                        f"(+ optional item/count)")
                    elif not v and do.get("item") is None:
                        problems.append(f"{ctx}: award needs gil and/or an item")
                    if br.get("once") is None:
                        problems.append(f"{ctx}: award needs `once = \"name\"` — the "
                                        f"payout is exactly-once BY that machinery")
                    cnt = do.get("count")
                    if cnt is not None and (not isinstance(cnt, int)
                                            or not 1 <= cnt <= 99):
                        problems.append(f"{ctx}: award count must be 1..99")
                    if do.get("item") is not None:
                        try:
                            from .. import items as _items
                            _items.resolve(do["item"])
                        except Exception as e:
                            problems.append(f"{ctx}: award item {do['item']!r} does "
                                            f"not resolve ({e})")
                if verb in ("add_shop_item", "remove_shop_item"):
                    # AddShopItem 0x115: the engine SILENTLY no-ops on a shop id
                    # absent from ShopItems.csv — an unknown id must never pass lint
                    if (not isinstance(v, list) or len(v) != 2
                            or not isinstance(v[0], int)):
                        problems.append(f"{ctx}: {verb} takes [shop_id, item]")
                    else:
                        own = {int(sh.get("id", -1)) for sh in raw.get("shop", []) or []}
                        if not 0 <= v[0] <= 255:
                            problems.append(f"{ctx}: {verb} shop id must be 0..255")
                        elif v[0] not in own and not 0 <= v[0] <= 31:
                            problems.append(f"{ctx}: {verb} shop {v[0]} is neither a "
                                            f"[[shop]] in this field nor a vanilla "
                                            f"shop 0-31 — the engine would silently "
                                            f"no-op on a shop ShopItems.csv lacks")
                        try:
                            from .. import items as _items
                            _items.resolve(v[1])
                        except Exception as e:
                            problems.append(f"{ctx}: {verb} item {v[1]!r} does not "
                                            f"resolve ({e})")
                    if not br.get("once"):
                        problems.append(f"{ctx}: {verb} needs `once = \"name\"` — the "
                                        f"mutation is session state, asserted "
                                        f"exactly-once per entry by that machinery")
                if verb in ("add_shop_synth", "remove_shop_synth"):
                    # AddShopSynthesis 0x116: the guard is on the RECIPE (silent
                    # no-op on an unknown id), and the target shop only renders
                    # recipes if it opens as SYNTHESIS = absent from ShopItems.csv
                    if (not isinstance(v, list) or len(v) != 2
                            or not isinstance(v[0], int)):
                        problems.append(f"{ctx}: {verb} takes [shop_id, recipe]")
                    else:
                        buy_ids = {int(sh.get("id", -1))
                                   for sh in raw.get("shop", []) or []}
                        if not 0 <= v[0] <= 255:
                            problems.append(f"{ctx}: {verb} shop id must be 0..255")
                        elif v[0] in buy_ids or 0 <= v[0] <= 31:
                            problems.append(f"{ctx}: {verb} shop {v[0]} is a BUY shop "
                                            f"(a [[shop]] here, or vanilla 0-31 in "
                                            f"ShopItems.csv) — it opens as Buy and "
                                            f"can never render synthesis recipes")
                        sel = v[1]
                        if isinstance(sel, str):
                            # compare RESOLVED item ids — authors may spell "Phoenix
                            # Down" here and "PhoenixDown" there; resolve bridges both
                            from .. import items as _items

                            def _rid(x):
                                try:
                                    return _items.resolve(x)
                                except (ValueError, TypeError):
                                    return None
                            results = {_rid(rc.get("result"))
                                       for sb in raw.get("synthesis", []) or []
                                       for rc in sb.get("recipes", []) or []}
                            if _rid(sel) is None or _rid(sel) not in results:
                                problems.append(f"{ctx}: {verb} recipe {sel!r} is not a "
                                                f"[[synthesis]] result in this project "
                                                f"(a vanilla recipe takes its int id)")
                        elif not (isinstance(sel, int) and 0 <= sel <= 1023):
                            problems.append(f"{ctx}: {verb} recipe must be an int id or "
                                            f"a [[synthesis]] result name")
                    if not br.get("once"):
                        problems.append(f"{ctx}: {verb} needs `once = \"name\"` — the "
                                        f"mutation is session state, asserted "
                                        f"exactly-once per entry by that machinery")
                if verb == "sfx":
                    if isinstance(v, bool) or not isinstance(v, int) \
                            or not 0 <= v <= 0xFFFF:
                        problems.append(f"{ctx}: sfx takes a sound id int 0..65535 "
                                        f"(`ff9mapkit sfx-list`; 108 = the item-get "
                                        f"jingle)")
                    bk = do.get("bank")
                    if bk is not None and (isinstance(bk, bool)
                                           or not isinstance(bk, int)
                                           or not 0 <= bk <= 0xFFFF):
                        problems.append(f"{ctx}: sfx bank must be an int 0..65535 "
                                        f"(default 53248 = 0xD000, the field-SFX "
                                        f"bank)")
                    su = do.get("sustain")
                    if su is not None and (isinstance(su, bool)
                                           or not isinstance(su, int)
                                           or not 0 <= su <= 255):
                        problems.append(f"{ctx}: sfx sustain must be an int 0..255 "
                                        f"frames (holds the dispatch level while "
                                        f"the cue rings)")
                if verb == "stop_timer":
                    if v is not True:
                        problems.append(f"{ctx}: stop_timer takes `true` (it pauses "
                                        f"the field countdown — no argument)")
                    elif b.get("timer") is None:
                        problems.append(f"{ctx}: stop_timer needs field-level "
                                        f"`timer = <seconds>` (there is no "
                                        f"countdown to stop)")
                if verb == "flash":
                    if (not isinstance(v, list) or len(v) != 3
                            or not all(isinstance(c, int) and not isinstance(c, bool)
                                       and 0 <= c <= 255 for c in v)):
                        problems.append(f"{ctx}: flash takes [r, g, b] — three ints "
                                        f"0..255 (the screen-flash colour)")
                    hd = do.get("pause")
                    if hd is not None and (isinstance(hd, bool)
                                           or not isinstance(hd, int)
                                           or not 0 <= hd <= 255):
                        problems.append(f"{ctx}: flash pause must be an int 0..255 "
                                        f"frames (the beat held at the colour)")
                for c in (br.get("when") or []):
                    _cv = _one_verb(c, COND_VERBS, ctx)
                    if _cv in ("time_below", "time_above"):
                        if b.get("timer") is None:
                            problems.append(f"{ctx}: {_cv} needs field-level "
                                            f"`timer = <seconds>` (the countdown HUD)")
                        if not isinstance(c[_cv], int) or not 0 <= c[_cv] <= 30000:
                            problems.append(f"{ctx}: {_cv} takes seconds 0..30000")
                    if _cv == "have_item":
                        _hv = c[_cv]
                        _entry = _hv[0] if isinstance(_hv, list) else _hv
                        try:
                            from .. import items as _items
                            _items.resolve(_entry)
                        except Exception as e:
                            problems.append(f"{ctx}: have_item {_entry!r} does not "
                                            f"resolve ({e})")
                        if isinstance(_hv, list) and len(_hv) > 1 and (
                                not isinstance(_hv[1], int) or not 1 <= _hv[1] <= 99):
                            problems.append(f"{ctx}: have_item count must be 1..99")
                if verb == "announce_npc":
                    npc = next((n for n in raw.get("npc", []) or []
                                if n.get("name") == str(v)), None)
                    if npc is None or "dialogue" not in npc:
                        problems.append(f"{ctx}: announce_npc {v!r} — no such [[npc]] with "
                                        f"a `dialogue` line")
                if verb in ("announce", "announce_npc"):
                    for opt in ("delay", "sustain"):
                        ov = do.get(opt)
                        if ov is not None and (isinstance(ov, bool)
                                               or not isinstance(ov, int)
                                               or not 0 <= ov <= 255):
                            problems.append(f"{ctx}: announce {opt} must be an int "
                                            f"0..255 frames (holds the dispatch "
                                            f"level around the window open)")
                for c in (br.get("when") or []):
                    cv = _one_verb(c, COND_VERBS, ctx)
                    val = c[cv]
                    if cv in ("near", "not_near") and str(val[0]) not in valid_targets | {me}:
                        problems.append(f"{ctx}: near target {val[0]!r} is not a behavior "
                                        f"unit or player")
                    if cv in ("active", "not_active") and str(val) not in valid_targets:
                        problems.append(f"{ctx}: active({val!r}) is not a behavior unit or player")
                    if cv == "any_near":
                        for t in val[0]:
                            if str(t) not in valid_targets:
                                problems.append(f"{ctx}: any_near target {t!r} is not a "
                                                f"behavior unit or player")
                    if cv == "any_active":
                        for t in val:
                            if str(t) not in set(unit_names):
                                problems.append(f"{ctx}: any_active({t!r}) is not a behavior unit")
                    if cv in ("near_point", "not_near_point"):
                        _resolve_point(val[0], positions, ctx)
                    if cv in ("counter_ge", "counter_le", "counter_eq"):
                        if (not isinstance(val, list) or len(val) != 2
                                or not isinstance(val[1], int)):
                            problems.append(f"{ctx}: {cv} takes [\"counter\", n]")
                        elif str(val[0]) not in declared_counters:
                            problems.append(f"{ctx}: {cv} counter {val[0]!r} is not in "
                                            f"[behavior] counters")
                    if cv in ("table_ge", "table_le", "table_eq"):
                        if (not isinstance(val, list) or len(val) != 3
                                or not isinstance(val[2], int)):
                            problems.append(f"{ctx}: {cv} takes [\"table\", index, n] "
                                            f"(index = an int or a counter name)")
                        else:
                            tn, ix = str(val[0]), val[1]
                            if tn not in declared_tables:
                                problems.append(f"{ctx}: {cv} table {tn!r} is not a "
                                                f"[[behavior.table]]")
                            elif isinstance(ix, str):
                                if ix not in declared_counters:
                                    problems.append(f"{ctx}: {cv} index {ix!r} is not in "
                                                    f"[behavior] counters")
                            elif (not isinstance(ix, int)
                                    or not 0 <= ix < declared_tables[tn]):
                                problems.append(f"{ctx}: {cv} index {ix!r} out of range "
                                                f"0..{declared_tables[tn] - 1}")
            except BehaviorTomlError as e:
                problems.append(str(e))
    return problems
