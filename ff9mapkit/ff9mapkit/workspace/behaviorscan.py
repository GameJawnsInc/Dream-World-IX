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
    for ui, u in enumerate(BT.units(raw)):
        nm = str(u.get("npc", ""))
        if nm in positions:
            posts.append({"name": nm, "x": positions[nm][0], "z": positions[nm][1],
                          "pooled": bool(u.get("pooled"))})
        for bi, br in enumerate(u.get("branch") or []):
            if not isinstance(br, dict):
                continue
            for ci, c in enumerate(br.get("when") or []):
                if not isinstance(c, dict):
                    continue
                try:
                    # "rid" is the ring's RESIZE handle (rung C: apply_radius)
                    if isinstance(c.get("near"), (list, tuple)) and len(c["near"]) >= 2:
                        rings.setdefault(nm, []).append(
                            {"radius": int(c["near"][1]), "bi": bi,
                             "rid": ("radius", ui, bi, ci, "near"),
                             "label": f"near {c['near'][0]} {int(c['near'][1])}"})
                    elif isinstance(c.get("any_near"), (list, tuple)) and len(c["any_near"]) >= 2:
                        rings.setdefault(nm, []).append(
                            {"radius": int(c["any_near"][1]), "bi": bi,
                             "rid": ("radius", ui, bi, ci, "any_near"),
                             "label": f"any_near {int(c['any_near'][1])}"})
                    elif isinstance(c.get("near_point"), (list, tuple)) and len(c["near_point"]) >= 2:
                        px, pz = BT._resolve_point(c["near_point"][0], positions, "near_point")
                        rings.setdefault(nm, []).append(
                            {"radius": int(c["near_point"][1]), "bi": bi, "x": px, "z": pz,
                             "rid": ("radius", ui, bi, ci, "near_point"),
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


# ------------------------------------------------------------------ rung B: edit operations
# All pure, in-place mutations of the raw dict (the OPEN document -- the shell checkpoints the
# whole doc around each call, so undo needs nothing from us). Every op is LENIENT about the
# surrounding doc but STRICT about its own indices (an out-of-range index is a caller bug).

# Verb templates for the insert menus. MEMBERSHIP is derived (the menus list the tables' own
# keys); this map only supplies an exemplar ARG SHAPE, with a generic fallback -- so a brand-new
# compiler verb appears in the menu the day it ships, merely with a plainer template.
_COND_EXAMPLES = {
    "hp_le": "{ hp_le = 1 }", "hp_gt": "{ hp_gt = 0 }",
    "near": '{ near = ["unit", 300] }', "not_near": '{ not_near = ["unit", 300] }',
    "near_point": '{ near_point = [[0, 0], 300] }',
    "not_near_point": '{ not_near_point = [[0, 0], 300] }',
    "flag": '{ flag = "name" }', "not_flag": '{ not_flag = "name" }',
    "any_flag": '{ any_flag = ["a", "b"] }',
    "active": '{ active = "unit" }', "not_active": '{ not_active = "unit" }',
    "any_near": '{ any_near = [["a", "b"], 300] }', "any_active": '{ any_active = ["a", "b"] }',
    "time_below": "{ time_below = 60 }", "time_above": "{ time_above = 60 }",
    "counter_ge": '{ counter_ge = ["name", 1] }', "counter_le": '{ counter_le = ["name", 1] }',
    "counter_eq": '{ counter_eq = ["name", 1] }',
    "table_ge": '{ table_ge = ["table", 0, 1] }', "table_le": '{ table_le = ["table", 0, 1] }',
    "table_eq": '{ table_eq = ["table", 0, 1] }',
    "have_item": '{ have_item = ["Potion", 1] }',
}
_ACTION_EXAMPLES = {
    "walk_to": '{ walk_to = [0, 0], speed = 40 }', "hold": "{ hold = [0, 0] }",
    "hold_post": "{ hold_post = true }",
    "chase": '{ chase = "unit", standoff = 160, speed = 60 }',
    "patrol": '{ patrol = "route_marker" }', "march": '{ march = "route_marker" }',
    "flee": '{ flee = "threat", to = ["a", "b"], speed = 70 }',
    "wander": '{ wander = [0, 0], radius = 300 }',
    "swing_at": '{ swing_at = "unit", damage = 1, interval = 25 }',
    "engage": '{ engage = "group", radius = 900, contact = 170, damage = 1 }',
    "die": "{ die = true }", "battle": "{ battle = 35 }",
    "award": "{ award = 1000 }", "announce": '{ announce = "..." }',
    "announce_npc": '{ announce_npc = "..." }',
    "add_shop_item": '{ add_shop_item = [0, "item"] }',
    "remove_shop_item": '{ remove_shop_item = [0, "item"] }',
    "add_shop_synth": '{ add_shop_synth = [0, "item"] }',
    "remove_shop_synth": '{ remove_shop_synth = [0, "item"] }',
    "hold_ground": "{ hold_ground = true }",
}


def cond_templates() -> list:
    """(verb, snippet) for the When insert menu -- one row per COND_VERBS key."""
    return [(v, _COND_EXAMPLES.get(v, f"{{ {v} = 0 }}")) for v in sorted(BT.COND_VERBS)]


def action_templates() -> list:
    """(verb, snippet) for the Do insert menu -- one row per ACTION_VERBS key."""
    return [(v, _ACTION_EXAMPLES.get(v, f"{{ {v} = 0 }}")) for v in sorted(BT.ACTION_VERBS)]


def _toml_value(v) -> str:
    """A TOML literal for the values a branch holds (str/int/float/bool/list/inline dict)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {_toml_value(x)}" for k, x in v.items()) + " }"
    return str(v)


def branch_toml(branch: dict) -> str:
    """One branch as editable TOML text -- `when` on its own line per cond (readable), the rest
    inline. Round-trip pinned: ``parse_branch(branch_toml(b)) == b``."""
    lines = []
    when = branch.get("when")
    if when:
        if len(when) == 1:
            lines.append(f"when = [{_toml_value(when[0])}]")
        else:
            rows = ",\n        ".join(_toml_value(c) for c in when)
            lines.append(f"when = [ {rows} ]")
    for k in ("do", *_DECO_KEYS):
        if k in branch:
            lines.append(f"{k} = {_toml_value(branch[k])}")
    return "\n".join(lines) + "\n"


def parse_branch(text: str):
    """``(branch dict, None)`` or ``(None, error text)``. Structure only -- key membership per
    the compiler's BRANCH_KEYS; verb legality stays validate()'s job on the applied doc."""
    import tomllib as _toml
    try:
        d = _toml.loads(text)
    except Exception as e:                         # noqa: BLE001 -- the message IS the feedback
        return None, f"not valid TOML: {e}"
    extra = set(d) - BT.BRANCH_KEYS
    if extra:
        return None, (f"unknown branch key(s) {sorted(extra)} — a branch takes "
                      f"{sorted(BT.BRANCH_KEYS)}")
    if "do" not in d:
        return None, "a branch needs `do = { <action verb> ... }`"
    if "when" in d and not isinstance(d["when"], list):
        return None, "`when` is a LIST of condition rows: when = [{ verb = ... }, ...]"
    return d, None


def _unit_row(raw: dict, unit_name: str):
    for u in BT.units(raw):
        if str(u.get("npc")) == unit_name:
            return u
    raise KeyError(f"no behavior unit {unit_name!r}")


def set_branch(raw: dict, unit_name: str, bi: int, branch: dict) -> None:
    _unit_row(raw, unit_name)["branch"][bi] = branch


def move_branch(raw: dict, unit_name: str, bi: int, delta: int) -> int:
    """Swap a branch up/down the priority ladder; returns its new index (clamped)."""
    br = _unit_row(raw, unit_name).setdefault("branch", [])
    nj = max(0, min(len(br) - 1, bi + delta))
    br[bi], br[nj] = br[nj], br[bi]
    return nj


NEW_BRANCH = {"when": [{"flag": "never"}], "do": {"hold_post": True}}   # inert until edited:
#                                                 the flag starts unraised, so it never fires


def add_branch(raw: dict, unit_name: str, at: int | None = None) -> int:
    """Insert a fresh (inert) branch; default position is just above the fallback row."""
    br = _unit_row(raw, unit_name).setdefault("branch", [])
    at = max(0, len(br) - 1) if at is None else max(0, min(len(br), at))
    br.insert(at, {"when": [dict(c) for c in NEW_BRANCH["when"]], "do": dict(NEW_BRANCH["do"])})
    return at


def duplicate_branch(raw: dict, unit_name: str, bi: int) -> int:
    import copy as _copy
    br = _unit_row(raw, unit_name)["branch"]
    br.insert(bi + 1, _copy.deepcopy(br[bi]))
    return bi + 1


def delete_branch(raw: dict, unit_name: str, bi: int) -> None:
    del _unit_row(raw, unit_name)["branch"][bi]


def npc_candidates(raw: dict) -> list:
    """Named [[npc]]s not already behavior units -- the Add-unit picker's rows."""
    taken = {str(u.get("npc")) for u in BT.units(raw)}
    return [n["name"] for n in raw.get("npc", []) or []
            if n.get("name") and n["name"] not in taken]


def add_unit(raw: dict, npc_name: str) -> None:
    """Seat a minimal LEGAL unit: a death branch + an unconditional hold fallback."""
    b = raw.setdefault("behavior", {})
    b.setdefault("unit", []).append({
        "npc": npc_name, "hp": 3,
        "branch": [{"when": [{"hp_le": 0}], "do": {"die": True}},
                   {"do": {"hold_post": True}}],   # holds its own spawn post -- position-free
    })


def delete_unit(raw: dict, unit_name: str) -> None:
    b = BT.table(raw) or {}
    b["unit"] = [u for u in b.get("unit", []) if str(u.get("npc")) != unit_name]


def check_edit(raw: dict, unit_name: str, bi: int, branch: dict) -> list:
    """validate() over a COPY with the edit applied -- the live legality feed while typing.
    Never mutates ``raw``."""
    import copy as _copy
    trial = _copy.deepcopy(raw)
    try:
        set_branch(trial, unit_name, bi, branch)
    except (KeyError, IndexError) as e:
        return [str(e)]
    return validate_problems(trial)


# ------------------------------------------------------------------ rung C: author on the stage
# HANDLES are the stage's draggable points. Each carries a stable tuple id naming its
# write-back path in the raw dict. A point that is a NAME REFERENCE moves the NAMED
# owner's pos (the honest edit: everything referencing the marker follows) — it is never
# silently converted to a literal; its LIST SLOT (for insert/delete) rides along as
# ``list_id``. All ops are pure in-place mutations under the rung-B contract (the shell
# checkpoints the whole doc around each commit).

def _npc_row(raw: dict, name: str):
    for n in raw.get("npc", []) or []:
        if str(n.get("name")) == name:
            return n
    return None


def _marker_row(raw: dict, name: str):
    for m in raw.get("marker", []) or []:
        if str(m.get("name")) == name:
            return m
    return None


def stage_handles(raw: dict) -> list:
    """Every draggable stage point: ``{"id", "x", "z", "kind", "label", "list_id"}``.
    Ids: ``("pos", name)`` · ``("player",)`` · ``("path", marker, i)`` ·
    ``("route_pt", ui, bi, key, i)`` · ``("wander", ui, bi)`` ·
    ``("near_point"|"not_near_point", ui, bi, ci)`` · ``("scan_pt", si)``.
    Unresolvable references are SKIPPED (validate names them); never raises."""
    positions = BT._npc_marker_positions(raw)
    out, seen_pos = [], set()

    def add_point(hid_literal, v, kind, label, list_id=None):
        """A point that is a literal [x,z] (owned by ``hid_literal``) or a name (moves
        the named owner). A repeated CENTRE reference dedupes; a list slot never does
        (its slot op is its own affordance)."""
        try:
            x, z = BT._resolve_point(v, positions, "stage")
        except (BT.BehaviorTomlError, TypeError, ValueError):
            return
        if isinstance(v, (list, tuple)):
            out.append({"id": hid_literal, "x": x, "z": z, "kind": kind,
                        "label": label, "list_id": list_id})
            return
        hid = ("pos", str(v))
        if list_id is None and hid in seen_pos:
            return
        seen_pos.add(hid)
        out.append({"id": hid, "x": x, "z": z, "kind": kind,
                    "label": f"{label} → {v}", "list_id": list_id})

    for u in BT.units(raw):
        nm = str(u.get("npc", ""))
        if nm in positions:
            seen_pos.add(("pos", nm))
            out.append({"id": ("pos", nm), "x": positions[nm][0], "z": positions[nm][1],
                        "kind": "post", "label": f"{nm}'s post", "list_id": None})
    if positions.get("player"):
        out.append({"id": ("player",), "x": positions["player"][0],
                    "z": positions["player"][1], "kind": "player",
                    "label": "player spawn", "list_id": None})
    for ref in BT.movement_route_refs(raw):
        ui, bi = ref["ui"], ref["bi"]
        key = "to" if ref["verb"] == "flee" else ref["verb"]
        kind = "refuge" if ref["verb"] == "flee" else "route"
        v = ref["value"]
        if isinstance(v, str):
            m = _marker_row(raw, v)
            if m and isinstance(m.get("path"), list):
                for i, p in enumerate(m["path"]):
                    out.append({"id": ("path", v, i), "x": int(p[0]), "z": int(p[1]),
                                "kind": kind, "label": f"'{v}' point {i + 1}",
                                "list_id": ("path", v, i)})
        elif isinstance(v, (list, tuple)):
            for i, p in enumerate(v):
                add_point(("route_pt", ui, bi, key, i), p, kind,
                          f"{ref['unit']} {ref['verb']} point {i + 1}",
                          list_id=("route_pt", ui, bi, key, i))
    for ui, u in enumerate(BT.units(raw)):
        for bi, br in enumerate(u.get("branch") or []):
            if not isinstance(br, dict):
                continue
            do = br.get("do")
            if isinstance(do, dict) and "wander" in do:
                add_point(("wander", ui, bi), do["wander"], "wander",
                          f"{u.get('npc')}'s wander centre")
            for ci, c in enumerate(br.get("when") or []):
                if not isinstance(c, dict):
                    continue
                for verb in ("near_point", "not_near_point"):
                    v = c.get(verb)
                    if isinstance(v, (list, tuple)) and len(v) >= 2:
                        add_point((verb, ui, bi, ci), v[0], "ring",
                                  f"{u.get('npc')} {verb} centre")
    b = BT.table(raw) or {}
    for si, s in enumerate(b.get("scan") or []):
        if s.get("point") is not None and s.get("radius"):
            add_point(("scan_pt", si), s["point"], "scan",
                      f"scan '{s.get('name', si)}' centre")
    return out


def apply_move(raw: dict, hid: tuple, x, z) -> str:
    """Write a handle's new position (ints); returns the undo-step label. A bad id is
    a caller bug (KeyError/IndexError, the rung-B convention)."""
    x, z = int(round(x)), int(round(z))
    k = hid[0]
    if k == "pos":
        # marker first: _npc_marker_positions lets a marker OVERWRITE an npc of the
        # same name, so the write must land where the resolver reads
        row = _marker_row(raw, hid[1]) or _npc_row(raw, hid[1])
        if row is None:
            raise KeyError(f"no [[npc]]/[[marker]] named {hid[1]!r}")
        row["pos"] = [x, z]
        return f"move {hid[1]}"
    if k == "player":
        sp = raw.setdefault("player", {}).setdefault("spawn", [0, 0])
        sp[0], sp[1] = x, z                        # keep any trailing components
        return "move player spawn"
    if k == "path":
        row = _marker_row(raw, hid[1])
        if row is None or not isinstance(row.get("path"), list):
            raise KeyError(f"no route marker {hid[1]!r}")
        row["path"][hid[2]] = [x, z]
        return f"move '{hid[1]}' point {hid[2] + 1}"
    if k == "route_pt":
        _k, ui, bi, key, i = hid
        BT.units(raw)[ui]["branch"][bi]["do"][key][i] = [x, z]
        return f"move route point {i + 1}"
    if k == "wander":
        _k, ui, bi = hid
        u = BT.units(raw)[ui]
        u["branch"][bi]["do"]["wander"] = [x, z]
        return f"move {u.get('npc')}'s wander centre"
    if k in ("near_point", "not_near_point"):
        _k, ui, bi, ci = hid
        u = BT.units(raw)[ui]
        v = list(u["branch"][bi]["when"][ci][k])
        v[0] = [x, z]
        u["branch"][bi]["when"][ci][k] = v
        return f"move {u.get('npc')} {k} centre"
    if k == "scan_pt":
        (BT.table(raw) or {})["scan"][hid[1]]["point"] = [x, z]
        return "move scan centre"
    raise KeyError(f"unknown stage handle {hid!r}")


RADIUS_FLOOR = 16                    # below this a near ring is a contact test, not a gate


def apply_radius(raw: dict, rid: tuple, r) -> str:
    """Write a ring's new radius (``("radius", ui, bi, ci, verb)`` from stage_model);
    floored at :data:`RADIUS_FLOOR`, always an int. Returns the undo-step label."""
    _k, ui, bi, ci, verb = rid
    u = BT.units(raw)[ui]
    v = list(u["branch"][bi]["when"][ci][verb])
    v[1] = max(RADIUS_FLOOR, int(round(r)))
    u["branch"][bi]["when"][ci][verb] = v
    return f"resize {u.get('npc')} {verb} radius to {v[1]}"


def _route_list(raw: dict, lid: tuple):
    if lid[0] == "path":
        row = _marker_row(raw, lid[1])
        if row is None or not isinstance(row.get("path"), list):
            raise KeyError(f"no route marker {lid[1]!r}")
        return row["path"], lid[2]
    if lid[0] == "route_pt":
        _k, ui, bi, key, i = lid
        lst = BT.units(raw)[ui]["branch"][bi]["do"][key]
        if not isinstance(lst, list):
            raise KeyError("route is a marker reference, not an inline list")
        return lst, i
    raise KeyError(f"unknown route slot {lid!r}")


def insert_route_point(raw: dict, lid: tuple, x=None, z=None) -> str:
    """Insert a literal ``[x, z]`` AFTER the slot — default is the midpoint to the NEXT
    point (a new point lands ON the leg, ready to drag), or a small offset at a route's
    tail. Ceilings (patrol/march take 2..8 points) stay validate()'s job — the doc shows
    its words instantly."""
    lst, i = _route_list(raw, lid)
    if x is None:
        positions = BT._npc_marker_positions(raw)

        def rp(e):
            try:
                return BT._resolve_point(e, positions, "insert")
            except (BT.BehaviorTomlError, TypeError, ValueError):
                return None

        a = rp(lst[i])
        b = rp(lst[i + 1]) if i + 1 < len(lst) else None
        if a and b:
            x, z = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        elif a:
            x, z = a[0] + 80, a[1] + 80
        else:
            x = z = 0
    lst.insert(i + 1, [int(round(x)), int(round(z))])
    return "insert route point"


def delete_route_point(raw: dict, lid: tuple) -> str:
    """Delete the slot's point. A 2-point route is the floor EVERY route verb shares —
    below it the geometry is meaningless, so this one refusal lives in the op."""
    lst, i = _route_list(raw, lid)
    if len(lst) <= 2:
        raise ValueError("a route needs at least 2 points — delete the branch instead")
    del lst[i]
    return "delete route point"


# ------------------------------------------------------------------ rung D: archetype stamps
# Whole PROVEN trees stamped onto a named [[npc]] — the charter's rung D, first slice. Every
# shape below is grounded in BEHAVIOR.md's own idioms (the watcher pattern, the bolting
# civilian, the beat walker) and the demo watchman's in-game-proven ladder; all bind against
# "player" (a first-class target — the module's own front-page example) so a stamp needs no
# second unit. Combat archetypes that need a TARGET unit binding are D's remainder, with the
# Info Hub cards and the [siege] whole-block stamp. Each stamp is fenced by a REAL dry-compile.

BEHAVIOR_ARCHETYPES = [
    {"key": "sentry", "name": "Sentry — watch, alarm, chase",
     "teach": "Announces once and raises 'alarm' when the player closes, chases from mid "
              "range, and walks a minted beat otherwise. Gate other trees' combat on "
              '{ flag = "alarm" } — the watcher pattern.'},
    {"key": "patroller", "name": "Patroller — walk the beat",
     "teach": "Walks a minted 4-point beat around its post forever (route = \"auto\" heals "
              "jammed legs at build). Drag the points into place on the stage."},
    {"key": "civilian", "name": "Civilian — panic and flee",
     "teach": "Bolts from the player to refuge points in priority order, strolls a small "
              "wander box at home otherwise (the speed contrast IS the character)."},
    {"key": "guard", "name": "Guard — fight a unit (pick the enemy)", "needs_target": True,
     "teach": "BEHAVIOR.md's own front example: the badly wounded run for minted refuges, "
              "fight what's in reach, chase what's in sight, hold the post otherwise. Give "
              "the TARGET a swing branch back and you have mutual combat, no referee."},
    {"key": "shift_pair", "name": "Shift patrol pair — trade the beat on the clock",
     "needs_partner": True,
     "teach": "Two guards share one minted beat: an alternator flips a flag every ~13s, "
              "the on-shift guard walks the route, the other stands watch at its post — "
              "BEHAVIOR.md's own shift idiom (flag / not_flag on the same alternator)."},
]


def stamp_siege(raw: dict) -> str:
    """Write a minimal LEGAL [siege] skeleton (the REDOUBT fixture's proven shape, sized
    around the player spawn, ``autoroute`` on so raider legs heal at build) — the authoring
    half of the tab's [siege] face; the read-only view renders it the same tick and the
    Editor form's [siege] section is the editing surface. Refusals raise ValueError with
    the reason (the doc shows it): [siege] OWNS the behavior table, one block per field,
    and a verbatim fork has no kit entries to seat."""
    if BT.table(raw):
        raise ValueError("this field already has [behavior] — [siege] OWNS the behavior "
                         "table; delete the [behavior] block first (or author by hand)")
    if raw.get("siege"):
        raise ValueError("this field already has a [siege] block — edit it in the Editor "
                         "form ([siege] section)")
    if "verbatim_eb" in raw:
        raise ValueError("[siege] is not wired on a VERBATIM fork (the donor's real .eb "
                         "runs) — use a --native/--editable fork or a novel field")
    sp = (raw.get("player", {}) or {}).get("spawn") or [0, 0]
    px, pz = int(sp[0]), int(sp[1])
    raw["siege"] = {
        "timer": 60, "waves": [55, 40, 20], "stipend": 3000,
        "win_gil": 2000, "loss_battle": 35,
        "base": {"model": "GEO_NPC_F4_CSO", "pos": [px, pz + 400], "hp": 24},
        "ally": [
            {"name": "soldier", "label": "Soldier (chases, melee)",
             "model": "GEO_NPC_F0_CSO", "count": 3, "price": 300,
             "stance": "chase", "radius": 2000, "speed": 65},
        ],
        "raider": [   # a COMPACT footprint (~700u tall): skeleton points must land on
            {"name": "mu", "model": "GEO_MON_F0_MUU", "count": 2, "wave": 1,   # small floors
             "entrance": [[px - 600, pz - 300], [px - 750, pz - 300]],   # too -- drag from
             "route": [[px - 300, pz], [px, pz + 300]], "autoroute": True},   # the Editor form
        ],
    }
    return "stamp [siege] skeleton"


def siege_view(raw: dict):
    """A [siege] field's GENERATED behavior, for READ-ONLY rendering: the desugared copy
    (the same expansion the build runs), or None when the field has no [siege]. The tab's
    projections read this; edits stay refused — the [siege] block owns the table."""
    if not raw.get("siege") or BT.table(raw):
        return None
    import copy as _copy
    from ..content import siege as _siege
    view = _copy.deepcopy(raw)
    try:
        _siege.desugar(view)
    except Exception:                  # noqa: BLE001 -- malformed [siege]: validate's job
        return None
    return view if BT.table(view) else None


def _mint_beat_marker(raw: dict, npc_name: str, pos) -> str:
    """A closed 4-point diamond beat around the post (220u legs — clear of the ~192u
    actor-jam spacing), name-deduped. Rung C's drag handles shape it from there."""
    taken = {str(m.get("name")) for m in raw.get("marker", []) or []}
    base = f"{npc_name}_beat"
    name, n = base, 2
    while name in taken:
        name, n = f"{base}_{n}", n + 1
    x, z = pos
    raw.setdefault("marker", []).append(
        {"name": name, "closed": True,
         "path": [[x + 220, z], [x, z + 220], [x - 220, z], [x, z - 220]]})
    return name


def stamp_archetype(raw: dict, key: str, npc_name: str, target: str | None = None) -> str:
    """Seat ``npc_name`` as a behavior unit wearing the archetype's proven tree; returns
    the undo-step label. ``target`` binds a needs_target archetype to an existing unit.
    Unknown key/npc are caller bugs (the picker lists the tables)."""
    positions = BT._npc_marker_positions(raw)
    x, z = positions.get(npc_name, (0, 0))
    die = {"when": [{"hp_le": 0}], "do": {"die": True}}
    if key == "shift_pair":
        if not target:
            raise KeyError("the shift_pair archetype needs a partner npc")
        b = raw.setdefault("behavior", {})
        taken = {str(a.get("name")) for a in (b.get("alternators") or [])}
        flag, n = "shift", 2
        while flag in taken:
            flag, n = f"shift_{n}", n + 1
        b.setdefault("alternators", []).append({"name": flag, "frames": 400})
        beat = _mint_beat_marker(raw, npc_name, (x, z))
        for nm, gate in ((npc_name, {"flag": flag}), (target, {"not_flag": flag})):
            b.setdefault("unit", []).append({"npc": nm, "hp": 3, "branch": [
                {"when": [{"hp_le": 0}], "do": {"die": True}},   # fresh dicts per unit --
                {"when": [gate],                                 # shared nesting would alias
                 "do": {"patrol": beat, "route": "auto", "speed": 40}},
                {"do": {"hold_post": True}},
            ]})
        return f"stamp shift pair on {npc_name} + {target}"
    if key == "guard":
        if not target:
            raise KeyError("the guard archetype needs a target unit")
        branches = [
            die,
            {"when": [{"hp_le": 1}],
             "do": {"flee": target, "to": [[x + 400, z], [x - 400, z]], "speed": 75}},
            {"when": [{"active": target}, {"near": [target, 300]}],
             "do": {"swing_at": target, "damage": 1, "interval": 25}},
            {"when": [{"active": target}, {"near": [target, 900]}],
             "do": {"chase": target, "standoff": 180, "speed": 65}},
            {"do": {"hold_post": True}},
        ]
        b = raw.setdefault("behavior", {})
        b.setdefault("unit", []).append({"npc": npc_name, "hp": 5, "branch": branches})
        return f"stamp guard archetype on {npc_name} vs {target}"
    if key == "sentry":
        beat = _mint_beat_marker(raw, npc_name, (x, z))
        branches = [
            die,
            {"when": [{"near": ["player", 450]}], "do": {"announce": "Who goes there?!"},
             "once": True, "raise_flags": ["alarm"]},
            {"when": [{"near": ["player", 900]}],
             "do": {"chase": "player", "standoff": 180, "speed": 65}},
            {"do": {"patrol": beat, "route": "auto"}},
        ]
    elif key == "patroller":
        beat = _mint_beat_marker(raw, npc_name, (x, z))
        branches = [die, {"do": {"patrol": beat, "route": "auto", "speed": 40}}]
    elif key == "civilian":
        branches = [
            die,
            {"when": [{"near": ["player", 350]}],
             "do": {"flee": "player", "to": [[x + 400, z], [x - 400, z]], "speed": 80}},
            {"do": {"wander": [x, z], "radius": 300, "speed": 30}},
        ]
    else:
        raise KeyError(f"unknown behavior archetype {key!r}")
    b = raw.setdefault("behavior", {})
    b.setdefault("unit", []).append({"npc": npc_name, "hp": 3, "branch": branches})
    return f"stamp {key} archetype on {npc_name}"


# ------------------------------------------------------------------ rung C: the sweep lane
@dataclass
class SweepResult:
    """What one walkability sweep produced — the ``behavior lint`` lane as DATA, so the
    stage can paint verdicts IN PLACE while the text lines stay word-for-word the CLI's
    (:func:`ff9mapkit.scene.routes.describe_leg_problems` / ``describe_pursuit_problems``)."""
    ok: bool = False                       # the sweeps ran (walkmesh in hand)
    error: str = ""                        # why not, when they did not
    jams: list = field(default_factory=list)      # {"a","b","t0","t1","mid","span","name"}
    hugs: list = field(default_factory=list)      # {"a","b","minwall","name"}
    pursuits: list = field(default_factory=list)  # {"label","tested","blocked","worst":[...]}
    lines: list = field(default_factory=list)     # [(kind, text)] kind: error|warn|info


def load_walkmesh(toml_path):
    """The sweep lane's one DISK read: the SAVED field's walkmesh (behavior edits never
    change the mesh, so the two-truths split is honest — mesh from disk, geometry from
    the open document). Returns ``(wmesh, "")`` or ``(None, why)``. Worker material."""
    try:
        from .. import build as _build
        return _build.behavior_walkmesh(_build.FieldProject.load(toml_path)), ""
    except Exception as e:                 # noqa: BLE001 -- the message is the teaching
        return None, str(e)


def sweep_geometry(raw: dict, wmesh, *, pursuit: bool = True) -> SweepResult:
    """Sweep the OPEN document's routes and pursuit families against ``wmesh`` — the
    ``behavior lint`` walkability lane, mirrored ref-for-ref (autoroute refs judge the
    ROUTED line, dedupe included) so what the stage paints == what the CLI prints."""
    from ..scene import routes as _routes
    res = SweepResult()
    if wmesh is None:
        res.error = "no walkmesh"
        return res
    try:
        bedges = _routes.mesh_boundary_edges(wmesh)
        positions = BT._npc_marker_positions(raw)
        mpaths = BT.marker_paths(raw)
        plan = {}
        if BT.wants_autoroute(raw):
            try:
                plan = BT.autoroute_plan(raw, wmesh)
            except BT.BehaviorTomlError as e:
                res.lines.append(("error", str(e)))
        seen, jam_hint = set(), False
        for ref in BT.movement_route_refs(raw):
            key = (ref["ui"], ref["bi"])
            if ref["autoroute"] and key in plan:
                pts = plan[key]["points"]
                closed = ref["verb"] == "patrol"
                name = f"{ref['verb']} {BT._route_label(ref['value'])} ({ref['unit']!r})"
            elif ref["autoroute"]:
                continue                   # plan errored -- already a line above
            else:
                try:
                    pts = BT._resolve_route(ref["value"], positions, mpaths,
                                            ref["unit"] or "?")
                except BT.BehaviorTomlError:
                    continue               # unresolvable -> validate reported it
                closed = (ref["verb"] == "patrol" or
                          (ref["verb"] == "flee" and isinstance(ref["value"], str)
                           and mpaths.get(ref["value"], ((), False))[1]))
                name = (ref["value"] if isinstance(ref["value"], str)
                        else f"{ref['unit']}#{ref['bi']} {ref['verb']}")
            dk = (tuple(map(tuple, pts)), closed)
            if dk in seen:
                continue
            seen.add(dk)
            legs = _routes.sweep_polyline(pts, wmesh, bedges, closed=closed)
            for p in _routes.describe_leg_problems(name, legs):
                res.lines.append(("error" if "OFF-MESH" in p else "warn", p))
            for leg in legs:
                for t0, t1 in leg["spans"]:
                    (ax, az), (bx, bz) = leg["a"], leg["b"]
                    mt = (t0 + t1) / 2
                    res.jams.append({"a": leg["a"], "b": leg["b"], "t0": t0, "t1": t1,
                                     "mid": (ax + (bx - ax) * mt, az + (bz - az) * mt),
                                     "span": max((t1 - t0) * leg["len"], 40.0),
                                     "name": str(name)})
                    if ref["verb"] in ("patrol", "march") and not ref["autoroute"]:
                        jam_hint = True
                if not leg["spans"] and leg["minwall"] is not None \
                        and leg["minwall"] < _routes.WALL_CLEARANCE_W:
                    res.hugs.append({"a": leg["a"], "b": leg["b"],
                                     "minwall": leg["minwall"], "name": str(name)})
        if jam_hint:
            res.lines.append(("info", 'hint: patrol/march accept route = "auto" -- the '
                              'build re-routes jammed legs through the walkmesh '
                              'pathfinder (clear legs stay as authored)'))
        if pursuit:
            extent = _routes.pursuit_extent(wmesh)
            pseen = set()
            for ref in BT.pursuit_refs(raw):
                radius = ref["radius"]
                ungated = radius is None
                if ungated:
                    radius = extent
                dk = (ref["verb"], radius, ref["standoff"], ref["source_box"],
                      ref["target_box"])
                if dk in pseen:
                    continue
                pseen.add(dk)
                pres = _routes.sweep_pursuit(wmesh, radius, standoff=ref["standoff"],
                                             bedges=bedges,
                                             source_box=ref["source_box"],
                                             target_box=ref["target_box"])
                label = (f"{ref['verb']} {ref['target']!r} ({ref['unit']!r} "
                         f"branch #{ref['bi']})")
                if ungated:
                    label += (" [UNGATED: no near/any_near row bounds this target, so "
                              f"the family is the whole field ({extent:.0f}u)]")
                probs = _routes.describe_pursuit_problems(label, pres)
                res.lines.extend(("warn", p) for p in probs)
                if probs and pres["blocked"]:
                    res.pursuits.append({"label": label, "unit": ref["unit"],
                                         "tested": pres["tested"],
                                         "blocked": pres["blocked"],
                                         "worst": pres["worst"]})
        res.ok = True
        if not res.lines:
            res.lines.append(("info", "behavior sweep: clean — every authored leg stays "
                              "on the walkmesh"))
    except Exception as e:                 # noqa: BLE001 -- surfaced, never a crash
        res.ok = False
        res.error = f"sweep failed: {e}"
    return res


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
