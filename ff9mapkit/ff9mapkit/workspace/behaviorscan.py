"""The Behavior tab's Qt-free half -- pure view-models over a field's ``[behavior]`` block.

Rung A of the Behavior GUI (charter: ``studies/behavior-trees/GUI-VISION.md``): READ-ONLY
projections of the behavior compiler's own data, no editing. Three model families:

- :func:`cast_model` / :func:`ladder_model` / :func:`stage_model` -- instant, pure projections of
  a raw field dict (the OPEN document's truth, unsaved edits included). They are LENIENT by
  design: a view must be able to render an invalid document, so unknown verbs render as written
  and :func:`validate_problems` reports the errors in the compiler's own words.
- :func:`dry_compile` -- the Instruments' feed: the CLI ``behavior compile`` lane verbatim
  (``FieldProject.load`` from DISK -- the saved file's truth, like the deploy snapshot; the
  caller labels which truth it shows). File I/O + real compilation: worker-thread material,
  never called at construction or on tab show.

The anti-rot law this module carries: **every verb string below comes from
``behaviortoml.COND_VERBS`` / ``ACTION_VERBS``** -- there is no hand-copied vocabulary list
anywhere in the GUI, so a new compiler verb renders (and pickers, come rung B, will list it)
with zero edits here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..content import behaviortoml as BT

# Branch keys that are decorators, not the guard/action (the ladder renders them as shoulder
# tags). Derived by subtraction so a new BRANCH_KEYS entry shows up rather than vanishing.
_DECO_KEYS = tuple(k for k in ("once", "cooldown", "raise_flags", "clear_flags")
                   if k in BT.BRANCH_KEYS)


def has_behavior(raw: dict) -> bool:
    """True when the field carries a compilable ``[behavior]`` table."""
    return BT.table(raw) is not None


def summary(raw: dict) -> str:
    """One header line: '5 units · 1 group · 1 pool · timer 180s'. Empty string when none."""
    b = BT.table(raw)
    if not b:
        return ""
    parts = [f"{len(BT.units(raw))} unit{'s' if len(BT.units(raw)) != 1 else ''}"]
    for key, noun in (("group", "group"), ("pool", "pool"), ("table", "table"),
                      ("scan", "scan"), ("hud", "hud strip")):
        rows = b.get(key) or []
        if rows:
            parts.append(f"{len(rows)} {noun}{'s' if len(rows) != 1 else ''}")
    if b.get("timer"):
        parts.append(f"timer {b['timer']}s")
    return " · ".join(parts)


# ------------------------------------------------------------------ formatting (lenient)
def _verb_of(d, verbs):
    """The dict's single verb key, or None (the STRICT twin is ``BT._one_verb``; a read-only
    view renders what's written and lets validate() do the refusing)."""
    if not isinstance(d, dict):
        return None
    keys = [k for k in d if k in verbs]
    return keys[0] if len(keys) == 1 else None


def _fmt_scalar(v) -> str:
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _fmt_val(v) -> str:
    if isinstance(v, (list, tuple)):
        if v and all(isinstance(p, (list, tuple)) for p in v):     # a point list
            return " ".join("[" + ",".join(_fmt_scalar(c) for c in p) + "]" for p in v)
        return " ".join(_fmt_scalar(c) for c in v)
    return _fmt_scalar(v)


def fmt_cond(d) -> str:
    """One ``when`` row as a chip string -- the TOML's own verb, never a paraphrase."""
    verb = _verb_of(d, BT.COND_VERBS)
    if verb is None:
        if isinstance(d, dict):
            return "? " + " ".join(f"{k} {_fmt_val(v)}" for k, v in d.items())
        return f"? {d!r}"
    v = d[verb]
    return verb if v is True else f"{verb} {_fmt_val(v)}"


def fmt_action(d) -> tuple[str, str]:
    """The ``do`` dict as ``(verb, detail)``. Unknown option keys still render (the view shows
    what's written; validate names the error)."""
    verb = _verb_of(d, BT.ACTION_VERBS)
    if verb is None:
        if isinstance(d, dict):
            return ("?", " ".join(f"{k} {_fmt_val(v)}" for k, v in d.items()))
        return ("?", repr(d))
    bits = []
    if d[verb] is not True:
        bits.append(_fmt_val(d[verb]))
    bits += [f"{k} {_fmt_val(v)}" for k, v in d.items() if k != verb]
    return (verb, " · ".join(bits))


def _decos(br: dict) -> list:
    out = []
    for k in _DECO_KEYS:
        if k not in br:
            continue
        v = br[k]
        if k in ("raise_flags", "clear_flags"):
            names = ", ".join(str(x) for x in v) if isinstance(v, (list, tuple)) else str(v)
            out.append(("raise" if k == "raise_flags" else "clear") + f" {names}")
        elif v is True:
            out.append(k)
        else:
            out.append(f"{k} {_fmt_val(v)}")
    return out


# ------------------------------------------------------------------ the three projections
def cast_model(raw: dict) -> dict:
    """The left rail: units / groups / pools / data rows, each as (name, note) material."""
    b = BT.table(raw) or {}
    units = []
    for u in BT.units(raw):
        units.append({"name": str(u.get("npc", "?")), "hp": u.get("hp"),
                      "speed": u.get("speed"), "pooled": bool(u.get("pooled")),
                      "pool": u.get("pool"), "branches": len(u.get("branch") or [])})
    groups = [{"name": str(g.get("name", "?")),
               "members": [str(x) for x in (g.get("units") or [])]}
              for g in (b.get("group") or [])]
    pools = []
    for p in (b.get("pool") or []):
        if p.get("item") is not None:
            note = f"item {p['item']}"
        elif p.get("price") is not None:
            note = f"{p['price']} gil" + (" · button" if p.get("button") else "")
        else:
            note = "free"
        pools.append({"name": str(p.get("name", "?")), "note": note})
    data = []
    for nm in (b.get("counters") or []):
        data.append({"kind": "counter", "name": str(nm), "note": "runtime cell"})
    for t in (b.get("table") or []):
        vals = t.get("values") or []
        prev = ", ".join(_fmt_scalar(v) for v in vals[:6]) + (" …" if len(vals) > 6 else "")
        data.append({"kind": "table", "name": str(t.get("name", "?")), "note": f"[{prev}]"})
    for s in (b.get("schedule") or []):
        data.append({"kind": "schedule", "name": f"{s.get('counter', '?')} ← {s.get('table', '?')}",
                     "note": "wave clock"})
    for s in (b.get("scan") or []):
        n = len(s.get("units") or [])
        src = f"group {s['group']}" if s.get("group") else f"{n} unit{'s' if n != 1 else ''}"
        data.append({"kind": "scan", "name": str(s.get("name", "?")), "note": src})
    for i, h in enumerate(b.get("hud") or []):
        data.append({"kind": "hud", "name": f"window {h.get('window', '?')}",
                     "note": f"{len(h.get('values') or [])} slots"})
    return {"units": units, "groups": groups, "pools": pools, "data": data,
            "timer": b.get("timer"), "public_flags": [str(f) for f in (b.get("public_flags") or [])]}


def ladder_model(raw: dict, unit_name: str) -> list:
    """The selected unit's branches as ladder rows, TOML order (== priority order). Each:
    ``{"index", "conds", "verb", "detail", "decos", "unconditional"}``."""
    unit = next((u for u in BT.units(raw) if str(u.get("npc")) == unit_name), None)
    rows = []
    for bi, br in enumerate(unit.get("branch") or [] if unit else []):
        when = br.get("when") if isinstance(br, dict) else None
        conds = [fmt_cond(c) for c in when] if isinstance(when, list) else \
                ([] if when is None else [f"? {when!r}"])
        do = br.get("do") if isinstance(br, dict) else None
        verb, detail = fmt_action(do) if isinstance(do, dict) else ("?", repr(do))
        rows.append({"index": bi + 1, "conds": conds, "verb": verb, "detail": detail,
                     "decos": _decos(br) if isinstance(br, dict) else [],
                     "unconditional": not conds})
    return rows


def stage_model(raw: dict) -> dict:
    """The spatial projection, in WORLD coordinates (x, z). The canvas maps +z up-screen --
    the layout probe's own frame, so the two instruments agree. Unresolvable references are
    SKIPPED (validate reports them); geometry never raises."""
    positions = BT._npc_marker_positions(raw)
    mpaths = BT.marker_paths(raw)
    posts, rings, wanders = [], {}, []
    for u in BT.units(raw):
        nm = str(u.get("npc", ""))
        if nm in positions:
            posts.append({"name": nm, "x": positions[nm][0], "z": positions[nm][1],
                          "pooled": bool(u.get("pooled"))})
        for bi, br in enumerate(u.get("branch") or []):
            if not isinstance(br, dict):
                continue
            for c in (br.get("when") or []):
                if not isinstance(c, dict):
                    continue
                try:
                    if isinstance(c.get("near"), (list, tuple)) and len(c["near"]) >= 2:
                        rings.setdefault(nm, []).append(
                            {"radius": int(c["near"][1]), "bi": bi,
                             "label": f"near {c['near'][0]} {int(c['near'][1])}"})
                    elif isinstance(c.get("any_near"), (list, tuple)) and len(c["any_near"]) >= 2:
                        rings.setdefault(nm, []).append(
                            {"radius": int(c["any_near"][1]), "bi": bi,
                             "label": f"any_near {int(c['any_near'][1])}"})
                    elif isinstance(c.get("near_point"), (list, tuple)) and len(c["near_point"]) >= 2:
                        px, pz = BT._resolve_point(c["near_point"][0], positions, "near_point")
                        rings.setdefault(nm, []).append(
                            {"radius": int(c["near_point"][1]), "bi": bi, "x": px, "z": pz,
                             "label": f"near_point {int(c['near_point'][1])}"})
                except (BT.BehaviorTomlError, TypeError, ValueError):
                    continue
            do = br.get("do")
            if isinstance(do, dict) and "wander" in do:
                try:
                    wx, wz = BT._resolve_point(do["wander"], positions, "wander")
                    wanders.append({"unit": nm, "x": wx, "z": wz,
                                    "r": int(do.get("radius", 400))})
                except (BT.BehaviorTomlError, TypeError, ValueError):
                    pass
    routes, refuges = [], []
    for ref in BT.movement_route_refs(raw):
        try:
            pts = BT._resolve_route(ref["value"], positions, mpaths, ref["unit"] or "?")
        except BT.BehaviorTomlError:
            continue
        if ref["verb"] == "flee":
            refuges.append({"unit": ref["unit"], "points": pts})
        else:
            closed = ref["verb"] == "patrol"
            routes.append({"unit": ref["unit"], "verb": ref["verb"], "points": pts,
                           "closed": closed, "auto": bool(ref["autoroute"])})
    scans = []
    for s in ((BT.table(raw) or {}).get("scan") or []):
        if s.get("point") and s.get("radius"):
            try:
                sx, sz = BT._resolve_point(s["point"], positions, "scan")
                scans.append({"name": str(s.get("name", "?")), "x": sx, "z": sz,
                              "r": int(s["radius"])})
            except (BT.BehaviorTomlError, TypeError, ValueError):
                continue
    player = positions.get("player")
    xs, zs = [], []
    for p in posts:
        xs.append(p["x"]); zs.append(p["z"])
    for r in routes:
        for x, z in r["points"]:
            xs.append(x); zs.append(z)
    for r in refuges:
        for x, z in r["points"]:
            xs.append(x); zs.append(z)
    for box in scans + wanders:
        xs += [box["x"] - box["r"], box["x"] + box["r"]]
        zs += [box["z"] - box["r"], box["z"] + box["r"]]
    if player:
        xs.append(player[0]); zs.append(player[1])
    bounds = (min(xs), min(zs), max(xs), max(zs)) if xs else None
    return {"posts": posts, "routes": routes, "refuges": refuges, "rings": rings,
            "scans": scans, "wanders": wanders, "player": player, "bounds": bounds}


def validate_problems(raw: dict) -> list:
    """The compiler's own static problems, verbatim (the Instruments' always-on row)."""
    return BT.validate(raw, verbatim="verbatim_eb" in raw)


# ------------------------------------------------------------------ the Instruments' feed
@dataclass
class CompileResult:
    """What one dry-compile produced. ``ok`` False => ``problems`` says why in the compiler's
    words; everything else is best-effort (a failed lane leaves its field empty, never raises)."""
    ok: bool = False
    problems: list = field(default_factory=list)
    report: str = ""                       # the blackboard map (cb.report -- the ~ Flags trace)
    size_text: str = ""                    # cb.size_report() -- the byte histogram, verbatim
    size_rows: list = field(default_factory=list)     # [(owner, bytes)] largest first
    new_bytes: int | None = None           # total compiled behavior bytes this build
    public_flags: list = field(default_factory=list)  # [(name, index)]
    pool_flags: list = field(default_factory=list)    # [(pool name, index)]
    routed: list = field(default_factory=list)        # describe_autoroute lines
    stable_hash: str = ""


def _size_rows(cb) -> list:
    """Per-OWNER byte totals from ``cb.sizes`` (ticker segment + duty walk + dispatch bodies),
    largest first. Best-effort: an unexpected shape yields [] and the verbatim text still shows."""
    try:
        s = cb.sizes or {}
        seg = {}
        for nm, n in s.get("ticker_segments", []):
            seg[nm] = seg.get(nm, 0) + int(n)
        disp = {nm: sum(int(row[-1]) for row in fns)
                for nm, fns in (s.get("dispatch") or {}).items()}
        duty = {nm: int(n) for nm, n in (s.get("duty") or {}).items()}
        rows = [(nm, seg.get(nm, 0) + disp.get(nm, 0) + duty.get(nm, 0))
                for nm in set(seg) | set(disp) | set(duty)]
        return sorted((r for r in rows if r[1] > 0), key=lambda r: (-r[1], r[0]))
    except Exception:                      # noqa: BLE001 -- a histogram must never sink the report
        return []


def dry_compile(toml_path) -> CompileResult:
    """The CLI ``behavior compile`` lane, as data: load the SAVED field from disk, validate,
    resolve the autoroute plan iff the field asks for one, compile with placeholder slots, and
    collect the report surfaces. Worker-thread material (file I/O + possibly a walkmesh
    resolve); never raises -- every failure comes back as a problem line."""
    res = CompileResult()
    try:
        from .. import build as _build
        project = _build.FieldProject.load(toml_path)
        raw = project.raw
        if not BT.table(raw):
            res.problems = ["no [behavior] table (with [[behavior.unit]] rows) in this field.toml"]
            return res
        res.problems = BT.validate(raw, verbatim="verbatim_eb" in raw)
        plan = {}
        if BT.wants_autoroute(raw):
            try:
                plan = BT.autoroute_plan(raw, _build.behavior_walkmesh(project))
            except Exception as e:         # noqa: BLE001 -- the plan's own message is the report
                res.problems.append(str(e))
        if res.problems:
            return res
        units = BT.units(raw)
        slots = {str(u["npc"]): i + 2 for i, u in enumerate(units)}   # placeholders (build binds real ones)
        fb = BT.build(raw, npc_slots=slots,
                      npc_txids_by_name={n.get("name"): 0 for n in raw.get("npc", []) or []
                                         if n.get("name") and "dialogue" in n},
                      behavior_txids={**{(ui, bi): 0 for ui, bi, _ in BT.announce_lines(raw)},
                                     **{("hud", hi): 0 for hi, _h in BT.hud_lines(raw)}},
                      routed=plan)
        cb = fb.compile()
        res.ok = True
        res.report = cb.report
        res.size_text = cb.size_report()
        res.size_rows = _size_rows(cb)
        try:
            disp = sum(len(b) for fns in cb.action_funcs.values() for _t, b in fns)
            duty = sum(len(b) for b in cb.duty_bodies.values())
            res.new_bytes = len(cb.ticker_body) + len(cb.main_init) + duty + disp
        except Exception:                  # noqa: BLE001
            res.new_bytes = None
        b = raw["behavior"]
        res.public_flags = [(str(nm), fb.bb.flag(str(nm)))
                            for nm in (b.get("public_flags") or [])]
        res.pool_flags = list(getattr(fb, "pool_flags", {}).items())
        res.routed = BT.describe_autoroute(plan, raw)
        res.stable_hash = cb.stable_hash()
    except Exception as e:                 # noqa: BLE001 -- surfaced as a problem, never a crash
        res.ok = False
        res.problems = res.problems or []
        res.problems.append(f"compile failed: {e}")
    return res
