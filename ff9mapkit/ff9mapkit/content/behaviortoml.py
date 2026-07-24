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
``any_flag`` (list), ``active`` / ``not_active`` (unit).

Action verbs (the ``do`` dict: one verb key + that verb's option keys):
``walk_to`` / ``hold`` (point; +speed), ``chase`` (target; +standoff, speed),
``patrol`` / ``march`` (points or a route-marker name; +arrive_r, speed),
``flee`` (threat; +to = refuge points, avoid_r, speed), ``wander`` (centre
point; +radius, every, speed), ``swing_at`` (unit; +damage, interval),
``die``, ``announce`` (a text line — minted into the field's .mes) /
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
}
ACTION_VERBS = {
    "walk_to": ("speed",),
    "hold": ("speed",),
    "hold_post": ("speed",),
    "chase": ("standoff", "speed"),
    "patrol": ("arrive_r", "speed"),
    "march": ("arrive_r", "speed"),
    "flee": ("to", "avoid_r", "speed"),
    "wander": ("radius", "every", "speed"),
    "swing_at": ("damage", "interval"),
    "die": (),
    "announce": ("window",),
    "announce_npc": ("window",),
}
BRANCH_KEYS = {"when", "do", "once", "cooldown", "raise_flags", "clear_flags"}
UNIT_KEYS = {"npc", "hp", "speed", "branch", "pooled", "pool"}
FIELD_KEYS = {"warmup", "tick", "alternators", "public_flags", "unit"}


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


def _build_action(fb: B.FieldBehavior, d: dict, *, positions, mpaths, txid, npc_txid, ctx: str):
    verb = _one_verb(d, ACTION_VERBS, ctx)
    v = d[verb]
    spd = d.get("speed")
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
        return B.Patrol(_resolve_route(v, positions, mpaths, ctx),
                        arrive_r=int(d.get("arrive_r", 150)), speed=spd)
    if verb == "march":
        return B.March(_resolve_route(v, positions, mpaths, ctx),
                       arrive_r=int(d.get("arrive_r", 150)), speed=spd)
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
                         damage=int(d.get("damage", 1)))
    if verb == "die":
        return B.Die()
    if verb == "announce":
        if txid is None:
            raise BehaviorTomlError(f"{ctx}: no minted txid for this announce line "
                                    f"(collect_text must register it)")
        return B.Announce(int(txid), window=int(d.get("window", 0)))
    # announce_npc
    if npc_txid is None:
        raise BehaviorTomlError(f"{ctx}: announce_npc = {v!r} — that NPC has no dialogue line")
    return B.Announce(int(npc_txid), window=int(d.get("window", 0)))


def build(raw: dict, *, npc_slots: dict, npc_txids_by_name: dict | None = None,
          behavior_txids: dict | None = None) -> B.FieldBehavior | None:
    """Construct the :class:`FieldBehavior` from the ``[behavior]`` table.

    ``npc_slots``: npc name -> entry slot (the build's own injection map — no
    discovery needed). ``npc_txids_by_name``: npc name -> its dialogue txid (for
    ``announce_npc``). ``behavior_txids``: ``(unit_idx, branch_idx) -> txid`` for
    minted ``announce`` lines (from ``collect_text``). Construction order is the
    TOML order — the deterministic-allocation contract."""
    b = table(raw)
    if not b:
        return None
    behavior_txids = behavior_txids or {}
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
    fb = B.FieldBehavior(specs, warmup=int(b.get("warmup", 45)), tick=int(b.get("tick", 1)))
    for nm in b.get("public_flags", []) or []:
        fb.public_flag(str(nm))
    for alt in b.get("alternators", []) or []:
        fb.alternator(str(alt["name"]), int(alt["frames"]))

    for ui, u in enumerate(b.get("unit", [])):
        name = str(u["npc"])
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
            npc_txid = None
            if isinstance(do, dict) and "announce_npc" in do:
                npc_txid = npc_txids_by_name.get(str(do["announce_npc"]))
            action = _build_action(fb, do, positions=positions, mpaths=mpaths,
                                   txid=behavior_txids.get((ui, bi)),
                                   npc_txid=npc_txid, ctx=ctx)
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
    for ui, u in enumerate(b.get("unit", [])):
        me = u.get("npc")
        for bi, br in enumerate(u.get("branch", []) or []):
            ctx = f"[[behavior.unit]] {me!r} branch #{bi}"
            try:
                if "do" not in br:
                    problems.append(f"{ctx}: needs a `do` action")
                    continue
                do = br["do"]
                verb = _one_verb(do, ACTION_VERBS, ctx)
                v = do[verb]
                if verb in ("chase",) and str(v) not in valid_targets:
                    problems.append(f"{ctx}: chase target {v!r} is not a behavior unit or player")
                if verb == "swing_at":
                    if str(v) not in set(unit_names):
                        problems.append(f"{ctx}: swing_at {v!r} is not a behavior unit")
                    elif str(v) not in hp_units:
                        problems.append(f"{ctx}: swing_at {v!r} — that unit has no `hp`")
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
                if verb == "announce_npc":
                    npc = next((n for n in raw.get("npc", []) or []
                                if n.get("name") == str(v)), None)
                    if npc is None or "dialogue" not in npc:
                        problems.append(f"{ctx}: announce_npc {v!r} — no such [[npc]] with "
                                        f"a `dialogue` line")
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
            except BehaviorTomlError as e:
                problems.append(str(e))
    return problems
