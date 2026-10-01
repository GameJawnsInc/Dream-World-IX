"""THE STORY-WRITE TRACE's segment driver, shared by O1, O2 and O3 (research/o2_design.md, sections 1.4 and 2;
research/o3_design.md 1.2 S4 and 2).

``RouteVoid`` and ``pick_for`` moved here from ``o1_opening`` (which imports and re-exports both): O1's rules and
O1's ``raise RouteVoid(msg)`` behave exactly as they did. What O2 adds is additive and optional:
  - a RouteVoid may carry its VOID class (``v``: "V1".."V16"), its beat-table ``cell`` (``[donor, sc]``) and who it
    is attributed to (``by``: "driver" or "game"), so the session record and the analysis can read VOIDs per side;
  - a choice rule may carry ``sc`` (the published scenarios it applies at), ``once`` (a second answer is VOID V2)
    and ``take: "default"`` (the pick must be the game's own ready cursor, else VOID V3).

O2's BEAT-TABLE DRIVER is here too (:func:`drive`, research/o2_design.md 2.2-2.3): O1's loop -- it acts only on what
the game shows, first match wins -- with control held answered by a table of CELLS keyed ``(donor place, published
SC)``, each a list of steps run in order per field VISIT, each step by its executor (cross, trigger, confirm, wait_sc,
leave_now) and counted done only on its own evidence. Everything it cannot answer is a RouteVoid with its class (2.7).
A walk that takes him out of the field is judged where it happened, by one LANDING JUDGE every executor shares: a
landing a crossing's ``to`` does not name -- or any landing of a trigger's, a Confirm's or a wait's walk -- and a loss
of control in any registered exit of the place (whose switch is waited out) is V11, the driver's; the loop's rule 2
holds every new visit to the route's ORDER (``visits``), and lays a field change it sees right after an unfinished walk
to that walk.
It keeps the evidence 4.7's backing rule reads -- a ``press`` row for every Confirm, a ``watch`` row for every sample
in a watched cell (the ring's samples from inside a harness call included), a ``step`` row for every step, a
``visit`` row for every field visit -- and scans the run's own trace live for forbidden writes with the two PURE
functions the analysis shares: :func:`forbidden_hits` (4.7's patterns over raw ``w`` rows, from the run's start row
on) and :func:`backing` (whether the run's own log holds the stray action a hit's cause names).

O3's BATTLE BEAT (S4, research/o3_design.md 2.1-2.6) is opt-in, read only when the predictions carry it. A BATTLE
REGISTRY (``battles``: each row checked strict by :func:`battle_of`, matched by :func:`battle_row`) answers a NEW
battle -- rule 1b, before the load, route and visit rules, so the id a battle flips at its over frame is never read
as a leave or a visit -- through its executor (:meth:`_Drive.battle`): fight() within the row's bounds (V15 when it
reaches no result), the leave that stops where the field begins, the landing in two tiers (late is recorded, never
voided; V14 past the cap), and the landing judge (V16 when a fork run lands in the REAL field: the s24 redirect did
not fire; V11 anywhere else). STOP PAGES (``stop_pages``) VOID a matching page as V5 with nothing pressed. With
neither key the driver is O2's loop exactly.

THE END ROW (opt-in, ``budget.end_row_s``; research/o3_design.md 2.2 rule 1, 11.7 #3): rule 1 fires on the first poll
that publishes an end field, and the session closes the trace right after the drive returns -- story-o1e closed it
1-4 frames after the field changed, its run 3 S before any row of the end field (no end cut). With the key, rule 1
first waits, up to ``end_row_s``, for the run's first trace row in an end place (:meth:`_Drive.end_row`), and the
``end`` row records it. Without it rule 1 is O1's and O2's exactly.

THE MOVIE-SKIP POLICY (opt-in, ``movies``; PLAN.md "Movie skip (opt-in)"): a type-0 FMV is skipped the way a player
skips it. While a movie plays, FieldHUD's hit area takes a Confirm and opens the "SkipMovieDialog" choice with its
cursor on No (FieldHUD.cs:275-286); its option 0 sets ``MBG.IsSkip`` and runs ``fldfmv.FF9FieldFMVShutdown`` (:428),
the same shutdown a movie's natural end runs, so the script's movie waits (``SYSVAR[15]&127 == 1``) complete. The
agent publishes no movie state, so the policy rests on its registration (:func:`movies_of`: the cells, each a place
and an SC, and how long into the visit its press may come) and on what is published: in a registered cell, nothing
on screen and control off, ``after_s`` into the visit, it presses Confirm (:meth:`_Drive.movie_press`, a ``press``
row) and answers the skip dialog YES -- only the one its own press opened, and only when the published choice IS the
skip dialog (:func:`skip_answer`; :meth:`_Drive.movie_answer`). A dialog after its press that it does not read as the
skip dialog goes to the frozen rule that answers it, or -- with none, and the skip dialog's shape (:func:`skip_shaped`:
a localized text, an empty prompt) -- is answered at the game's default, No: the movie resumes. No dialog is pressed
for again, up to ``max_presses``; then the visit gives up ('movie-skip missed', never a VOID: the movie plays out).
Each such visit's ``movie`` row keeps its presses, the dialog as published, the frame and the seconds it was skipped
at, and how much of the cell's registered span was then left (``left_s``: its ``next_page_s`` less them -- at most what
the skip saves; the saving itself is the A/B's, from its drive times). Without the key the loop is O3's exactly, and
O1's skip rule still answers a stray skip dialog at its default (No).
"""
from __future__ import annotations

import json
import math
import time

import segment_trace as ST
from segment_trace import place

#: The step kinds of a beat-table cell (research/o2_design.md 2.3), each run by its executor in :class:`_Drive`.
STEP_KINDS = ("cross", "trigger", "confirm", "wait_sc", "leave_now")
#: What each kind's executor reads that no default gives (:func:`step_of` refuses a step without it): every walk its
#: ``goal``; a crossing its exit (``target``) and the place it leads to (``to``); a Confirm its region and the answer it
#: waits for; a wait its scenario and how long. A trigger needs a ``target`` or an ``until`` (checked apart).
STEP_NEEDS = {"cross": ("goal", "target", "to"), "leave_now": ("goal", "target", "to"), "trigger": ("goal",),
              "confirm": ("goal", "target", "expect"), "wait_sc": ("goal", "sc", "wait_s")}
#: What a confirm step's ``expect`` may name: a choice opening, or control going (2.3).
EXPECTS = ("choice", "control_lost")
#: A forbidden pattern's keys (4.7), strict: any other raises. The matchers select raw ``w`` rows (all given must
#: hold); ``cause`` names the stray action :func:`backing` looks for; ``object`` the published sid it concerns.
FORBID_KEYS = frozenset({"donor", "sid", "tag", "target", "ip_range", "off_route", "cause", "object", "why"})
FORBID_MATCHERS = ("donor", "sid", "tag", "target", "ip_range", "off_route")
CAUSES = ("contact", "confirm_hotspot", "confirm_talk", "choice", "walk")
#: ``contact``'s backing reach beyond the object's published range_r: what Vivi (60u a tick) and Jack (15u) can close
#: in the two field ticks between published samples (4.7).
CONTACT_SLACK = 150.0
#: ``confirm_hotspot``'s backing reach beyond the hot-spot's own: a moving sample's lag (4.7).
HOTSPOT_SLACK = 64.0
#: A press row's ``near``: a published object whose talk / range disc, this much wider, held him (2.2).
NEAR_SLACK = 64.0
#: Where every Confirm hot-spot writes its own position first, as store constants (0.2 #9).
HOT_X, HOT_Z = "Global.Int16[220]", "Global.Int16[222]"
#: trigger: a walk that ended with control held waits this long for the trigger to take it (2.3).
TRIGGER_WAIT_S = 2.0
#: The loop's poll (O1's).
POLL_S = 0.05
#: The comparisons an ``until`` predicate may use: ``{"x_le": 900}`` -- every one must hold.
UNTIL_OPS = {"le": lambda a, b: a <= b, "lt": lambda a, b: a < b, "ge": lambda a, b: a >= b, "gt": lambda a, b: a > b}
#: A battle registry row's keys (research/o3_design.md 2.1), strict: :func:`battle_of` refuses an unknown key, a
#: missing one or a wrong type before anything is driven.
BATTLE_KEYS = ("donor", "sc", "scene", "won", "lands", "beat", "timeout_s", "max_turns", "land_s", "land_cap_s", "why")
#: The ``won`` sets a SCRIPTED end can report: [1, 2] with WinPose off (the end reports 2, folded to 1 at the over
#: frame), [1] with it on. A defeat's 3 is never a win, and [2] or [] is no scripted end's.
BATTLE_WON = ([1, 2], [1])
#: A stop page's keys (2.1), strict: ``match`` (a substring of the page's text or of a raw_texts line) and ``why``.
STOP_PAGE_KEYS = frozenset({"match", "why"})
#: Rule 1's end-row wait (opt-in: ``budget.end_row_s``) reads the live trace this often: each read parses story.jsonl.
END_ROW_POLL_S = 0.1
#: THE MOVIE-SKIP POLICY (opt-in, ``pred["movies"]``), strict: :func:`movies_of` refuses an unknown key, a missing one
#: or a wrong type before anything is driven. ``match``/``yes``/``no`` are the skip dialog's text (default: the
#: engine's US text, below).
MOVIE_KEYS = ("policy", "cells", "press_every_s", "max_presses", "match", "yes", "no")
MOVIE_NEEDS = ("policy", "cells", "press_every_s", "max_presses")
MOVIE_POLICIES = ("skip",)
#: A registered cell: the place and the SC its movie plays at, how far into the visit the policy may first press
#: (the movie must be PLAYING: MBG.Play arms the hit area, and before the first frame MBG.IsFinished() refuses the
#: dialog), when the PAGE AFTER the movie opens, in seconds from the visit's start (``next_page_s``, optional), and the
#: Cinematic it is. ``next_page_s`` is no movie length: measured to the next page, it holds the script's tail after the
#: movie too (61: FMV003 runs 84.8 s, MoguriVideo's copy, and 61 e2 t1's Wait/SetFieldCamera/FadeFilter/Walk/Ojigi come
#: after it, before WindowAsync 72 -- R-FULL measured 90.1-90.3 s to that page). Every press must end before it (a
#: press there can turn that page), and a skip answered ``t`` s into the visit can save at most ``next_page_s - t``
#: (the row's ``left_s``): the tail runs either way. What a skip saved is the A/B's (o3_prima_vista ``--skip-ab``,
#: from the drive times), never the row's.
MOVIE_CELL_KEYS = ("donor", "sc", "after_s", "next_page_s", "why")
MOVIE_CELL_NEEDS = ("donor", "sc", "after_s", "why")
#: The skip dialog as the engine opens it (FieldHUD.OnKeyConfirm, FieldHUD.cs:275-286): Localization "SkipMovieDialog",
#: US ``Do you want to skip\nthe movie?`` (UK ``...\nthis cutscene?``), then ``[CHOO]`` ``Yes`` / ``No`` under
#: ``[PCHC=2,1]`` -- two options, the cursor on ``ETb.sChoose = 1`` (No), Cancel 1. Its option 0 skips (:428-433).
SKIP_MATCH, SKIP_YES, SKIP_NO = "want to skip", "Yes", "No"


class RouteVoid(Exception):
    """The route met something it has no rule for: the run is VOID (never a finding about the scripts).

    ``v`` / ``cell`` / ``by`` are the VOID's class ("V1".."V16": research/o2_design.md 2.7, research/o3_design.md
    2.6), its beat-table cell and its attribution; each is None unless given, so O1's ``raise RouteVoid(msg)`` still
    works and its runs record no class."""

    def __init__(self, msg: str = "", *, v: str | None = None, cell: list | None = None, by: str | None = None):
        super().__init__(msg)
        self.v, self.cell, self.by = v, cell, by


def pick_for(choice: dict, donor: int, pred: dict, *, sc: int | None = None, answered=()) -> tuple:
    """``(absolute option index or "default", the rule)`` for a ready choice, by the frozen rule table; raises
    RouteVoid when no rule matches. ``choice["options"]`` is ``[prompt, *shown lines]``; ``active`` the absolute
    index of each shown line.

    Three rule keys are optional, each skipped when absent (so O1's rules read exactly as before):
      - ``sc`` (a list): the rule applies only when the published scenario ``sc`` is in it; ``None`` = any;
      - ``once``: a rule whose index (its position in ``pred["choices"]``) is in ``answered`` is asked again:
        VOID V2;
      - ``take: "default"``: the resolved pick must be ``choice["selected"]``, the game's own ready cursor: else
        VOID V3 -- stepping the cursor is not the route.
    A choice no rule matches (V1 to the beat-table driver) and a pick on other than one line raise as O1's did,
    with no class."""
    lines = list(choice.get("options") or [])[1:]
    active = list(choice.get("active") or range(len(lines)))
    for n, rule in enumerate(pred["choices"]):
        if not _rule_fits(rule, choice, donor, sc, lines):
            continue
        if rule.get("once") and n in answered:
            raise RouteVoid(f"choice in {donor} at SC {sc}: rule {rule['match']!r} answers once and was answered "
                            f"already: {choice.get('options')}", v="V2", cell=[donor, sc], by="game")
        if rule["pick"] == "default":
            return "default", rule
        hits = [active[i] for i, ln in enumerate(lines) if rule["pick"] in ln]
        if len(hits) != 1:
            raise RouteVoid(f"choice in {donor}: rule {rule['match']!r} picks {rule['pick']!r}, which is on "
                            f"{len(hits)} lines of {lines}")
        if rule.get("take") == "default" and hits[0] != choice.get("selected"):
            raise RouteVoid(f"choice in {donor} at SC {sc}: the frozen pick {rule['pick']!r} (option {hits[0]}) is "
                            f"not the game's default {choice.get('selected')}: stepping the cursor is not the route",
                            v="V3", cell=[donor, sc], by="game")
        return hits[0], rule
    raise RouteVoid(f"choice in {donor} with no rule: {choice.get('options')}")


def _rule_fits(rule: dict, choice: dict, donor, sc, lines: list) -> bool:
    """Whether a frozen choice rule applies to a ready ``choice`` (``lines``: its shown lines): its ``donor`` (None =
    any), its ``sc`` (None = any) and its ``match`` in the prompt or a shown line -- :func:`pick_for`'s matching, in
    its order, which :func:`rule_for` shares."""
    if rule["donor"] not in (None, donor):
        return False
    if rule.get("sc") is not None and sc not in rule["sc"]:
        return False
    return any(rule["match"] in ln for ln in [choice.get("options", [""])[0], *lines])


def rule_for(choice: dict, donor: int, pred: dict, *, sc: int | None = None) -> dict | None:
    """The first frozen choice rule that applies to a ready ``choice`` -- the one :func:`pick_for` would answer it by
    -- or None: no rule answers it (pure; nothing is resolved, so nothing raises)."""
    lines = list(choice.get("options") or [])[1:]
    return next((rule for rule in pred["choices"] if _rule_fits(rule, choice, donor, sc, lines)), None)


# ======================================================================== the beat table's helpers (pure)
def cell(pred: dict, donor: int, sc: int) -> dict | None:
    """The table's cell for ``(donor place, published SC)``, or None (2.1)."""
    return next((c for c in pred.get("table") or () if c["donor"] == donor and c["sc"] == sc), None)


def region(pred: dict, key: str) -> dict:
    """A frozen region (2.5): ``{"points": [[x, z], ...] (the engine's SetRegion order), "role", ...}``."""
    try:
        return pred["regions"][key]
    except KeyError:
        raise KeyError(f"region {key!r} is not registered in the predictions") from None


def polys(pred: dict, keys) -> list:
    """The points of each region ``keys`` names -- a step's ``avoid`` as route_to takes it."""
    return [region(pred, k)["points"] for k in keys or ()]


def until_ok(expr: dict, x, z) -> bool:
    """Whether (``x``, ``z``) satisfies an ``until`` predicate: ``{"x_le": 900}``, ``{"x_gt": 3000, "z_gt": 10300}``
    -- every comparison (``x|z`` + ``_`` + ``le|lt|ge|gt``) must hold. An unknown key raises; a missing position is
    False."""
    if x is None or z is None:
        return False
    ok = True
    for k, v in expr.items():
        axis, _, op = k.partition("_")
        if axis not in ("x", "z") or op not in UNTIL_OPS:
            raise ValueError(f"until {expr!r}: {k!r} is not x|z + _ + le|lt|ge|gt")
        ok = ok and UNTIL_OPS[op](float(x if axis == "x" else z), float(v))
    return ok


def closed_tris(pred: dict, step: dict, wmesh) -> list:
    """The triangles a step's walk must treat as closed (H5): its ``closed_tris`` plus every triangle of each floor in
    its ``closed_floors`` (``EnablePath(floor, 0)``), on ``wmesh`` (a PlayerWalkmesh's raw mesh, or a BgiWalkmesh)."""
    mesh = getattr(wmesh, "mesh", wmesh)
    out = {int(t) for t in step.get("closed_tris") or ()}
    floors = {int(f) for f in step.get("closed_floors") or ()}
    if floors:
        tf = mesh._tri_floor()
        out |= {ti for ti, t in enumerate(mesh.tris) if tf.get(ti, t.floor_ndx) in floors}
    return sorted(out)


def on_route(fid: int, members: dict, route, end_fields) -> bool:
    """Whether field ``fid`` is one a run may stand in before its end (2.2, rule 2): an end field; on the S side
    (``members`` empty) a field of ``route``; on the F side only a MEMBER whose donor is on ``route`` -- a real route
    field reached from the chain is OFF it (the claim-integrity critique #2)."""
    if fid in end_fields:
        return True
    if members:
        return fid in members and members[fid] in route
    return fid in route


def exit_regions(pred: dict, donor) -> list:
    """The registered exits of place ``donor`` (2.5): ``[(key, points)]`` for every region of role ``exit`` whose key
    names that place (``"<donor>.e<sid>"``) or whose ``donor`` is it. A region that names no place at all (a synthetic
    table's) is every place's. O2-REGIONS proves the route fields' list complete (every gateway scan_gateways finds is
    registered), which the landing judge (:meth:`_Drive.exit_at`) rests on."""
    out = []
    for key, r in (pred.get("regions") or {}).items():
        if r.get("role") != "exit":
            continue
        head = str(key).split(".", 1)[0]
        where = r.get("donor", int(head) if head.lstrip("-").isdigit() else None)
        if where is None or where == donor:
            out.append((key, r["points"]))
    return out


def step_of(pred: dict, raw: dict) -> dict:
    """A step with ``steps_default`` under it (4.1); its ``climb`` merged the same way. Refuses (ValueError) a step its
    executor could not run, so a table typo fails the offline check (O2-GOALS reads every step through here) and the
    driver's start, never a run mid-walk: an unknown ``kind``; ``target`` with ``until``; anything :data:`STEP_NEEDS`
    names missing; a trigger with neither ``target`` nor ``until``; an ``until`` that is empty or has a key
    :func:`until_ok` does not know; an ``expect`` not in :data:`EXPECTS`; a ``goal`` that is no point; and a ``target``
    or ``avoid`` key that is no registered region."""
    base = pred.get("steps_default") or {}
    out = {**base, **raw}
    out["climb"] = {**(base.get("climb") or {}), **(raw.get("climb") or {})}
    kind = out.get("kind")
    if kind not in STEP_KINDS:
        raise ValueError(f"step {raw!r}: kind is not one of {STEP_KINDS}")
    if out.get("target") is not None and out.get("until") is not None:
        raise ValueError(f"step {raw!r}: target and until are exclusive")
    missing = [k for k in STEP_NEEDS[kind] if out.get(k) is None]
    if missing:
        raise ValueError(f"step {raw!r}: a {kind} step needs {missing}")
    if kind == "trigger" and out.get("target") is None and out.get("until") is None:
        raise ValueError(f"step {raw!r}: a trigger step needs a target or an until")
    if out.get("until") is not None:
        if not isinstance(out["until"], dict) or not out["until"]:
            raise ValueError(f"step {raw!r}: until is a non-empty predicate, e.g. {{'x_le': 900}}")
        until_ok(out["until"], 0, 0)                      # an unknown key raises
    if kind == "confirm" and out["expect"] not in EXPECTS:
        raise ValueError(f"step {raw!r}: expect is one of {EXPECTS}")
    goal = out["goal"]
    if not isinstance(goal, (list, tuple)) or len(goal) != 2 or not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in goal):
        raise ValueError(f"step {raw!r}: goal is a point [x, z]")
    regions = pred.get("regions") or {}
    unknown = [k for k in [out.get("target"), *(out.get("avoid") or ())] if k is not None and k not in regions]
    if unknown:
        raise ValueError(f"step {raw!r}: {unknown} is no registered region")
    return out


# ======================================================================== S4: the battle registry, stop pages (pure)
def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_pos(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0


def battle_of(pred: dict, raw: dict) -> dict:
    """A battle registry row (research/o3_design.md 2.1), checked STRICT before anything is driven -- and at the
    freeze -- as :func:`step_of` checks a step. ValueError on: an unknown key, a missing one, or a wrong type
    (``donor``, ``scene``, ``lands`` ints; ``sc`` an int or None; ``beat`` and ``why`` non-empty strings; a bool is no
    int); a ``won`` that is not exactly [1, 2] or [1] (``[1, 2, 3]`` would count a defeat won; ``[2]`` and ``[]`` are
    no scripted end's); a ``beat`` that is not one of ``pred["beats"]``, or that a table step, a naming rule, a choice
    rule, ``steps_default`` or a battle row of another slot (donor, sc, scene) also names -- only the executor sets
    it, with the battle's int result (S1 counts nothing else); a row of the SAME slot is this registration, so an
    override of it (R-BATTLE-VOID's ``max_turns`` 0) validates against the predictions it overrides; a
    ``timeout_s``, ``land_s`` or ``land_cap_s`` that is not a positive number, or a
    ``land_s`` above ``land_cap_s``; a ``max_turns`` that is not an int >= 0 (0 is R-BATTLE-VOID's: fight() stops at
    the first prompt). Returns a copy."""
    if not isinstance(raw, dict):
        raise ValueError(f"battle row {raw!r}: a row is a dict of {BATTLE_KEYS}")
    unknown = sorted(set(raw) - set(BATTLE_KEYS))
    missing = [k for k in BATTLE_KEYS if k not in raw]
    if unknown or missing:
        raise ValueError(f"battle row {raw!r}: " + "; ".join(
            ([f"unknown key(s) {unknown}"] if unknown else []) + ([f"missing {missing}"] if missing else []))
            + f" -- a row is exactly {', '.join(BATTLE_KEYS)}")
    bad = [k for k in ("donor", "scene", "lands") if not _is_int(raw[k])]
    if raw["sc"] is not None and not _is_int(raw["sc"]):
        bad.append("sc")
    bad += [k for k in ("beat", "why") if not isinstance(raw[k], str) or not raw[k]]
    if bad:
        raise ValueError(f"battle row {raw!r}: {bad} of the wrong type (donor, scene and lands ints, sc an int or "
                         f"None, beat and why non-empty strings)")
    won = raw["won"]
    if not isinstance(won, (list, tuple)) or not all(_is_int(v) for v in won) or list(won) not in BATTLE_WON:
        raise ValueError(f"battle row {raw!r}: won is {won!r} -- exactly [1, 2] (WinPose off: a scripted end reports "
                         f"2) or [1] (on); a defeat's 3 is never won")
    if not all(_is_pos(raw[k]) for k in ("timeout_s", "land_s", "land_cap_s")):
        raise ValueError(f"battle row {raw!r}: timeout_s, land_s and land_cap_s are positive numbers")
    if raw["land_s"] > raw["land_cap_s"]:
        raise ValueError(f"battle row {raw!r}: land_s {raw['land_s']} is above land_cap_s {raw['land_cap_s']} (the "
                         f"late mark comes before the cap)")
    if not _is_int(raw["max_turns"]) or raw["max_turns"] < 0:
        raise ValueError(f"battle row {raw!r}: max_turns is an int >= 0, not {raw['max_turns']!r}")
    beat = raw["beat"]
    if beat not in (pred.get("beats") or ()):
        raise ValueError(f"battle row {raw!r}: beat {beat!r} is not one of the predictions' beats {pred.get('beats')}")
    named = [f"step {s.get('name') or s.get('kind')!r} of cell ({c.get('donor')}, {c.get('sc')})"
             for c in pred.get("table") or () for s in c.get("steps") or () if s.get("beat") == beat]
    named += [f"naming rule ({r.get('donor')}, {r.get('sc')})" for r in pred.get("naming") or ()
              if r.get("beat") == beat]
    named += [f"choice rule {r.get('match')!r}" for r in pred.get("choices") or () if r.get("beat") == beat]
    slot = (raw["donor"], raw["sc"], raw["scene"])         # a row of the same slot is this registration (an override)
    named += [f"battle row (scene {b.get('scene')}, donor {b.get('donor')}, sc {b.get('sc')})"
              for b in pred.get("battles") or () if isinstance(b, dict) and b.get("beat") == beat
              and (b.get("donor"), b.get("sc"), b.get("scene")) != slot]
    if (pred.get("steps_default") or {}).get("beat") == beat:
        named.append("steps_default")
    if named:
        raise ValueError(f"battle row {raw!r}: beat {beat!r} is also named by {named} -- only the battle sets it, "
                         f"with its int result")
    return dict(raw)


def battle_row(pred: dict, where, sc, scene, answered=()) -> tuple | None:
    """The registry row a NEW battle answers to (research/o3_design.md 2.3 step 1), pure: ``(index, row)`` of the first
    ``battles`` row whose ``scene`` is the published one, whose ``donor`` is ``where`` -- the place of the VISIT the
    battle began in -- whose ``sc`` is None or the published SC, and whose index is not in ``answered`` (the rows this
    run has answered). None: no row -- another scene, another place or SC, or the same row asked twice."""
    for n, b in enumerate(pred.get("battles") or ()):
        if n not in answered and b["scene"] == scene and b["donor"] == where and b["sc"] in (None, sc):
            return n, b
    return None


def _check_stop_page(p) -> None:
    """A stop page is exactly ``{"match", "why"}``, both non-empty strings (2.1): a typo is an error, never a page that
    matches nothing."""
    if not isinstance(p, dict) or set(p) != STOP_PAGE_KEYS or not all(isinstance(p[k], str) and p[k] for k in p):
        raise ValueError(f"stop page {p!r}: exactly {sorted(STOP_PAGE_KEYS)}, each a non-empty string")


def stop_page(pred: dict, st) -> dict | None:
    """The first registered stop page (2.1) the published page matches -- its ``match`` a substring of the page's
    rendered text or of any ``raw_texts`` line -- or None (always None without ``stop_pages``)."""
    for p in pred.get("stop_pages") or ():
        if p["match"] in st.text or any(p["match"] in t for t in st.raw_texts):
            return p
    return None


# ======================================================================== the movie-skip policy (opt-in, pure)
def _is_str(v) -> bool:
    return isinstance(v, str) and bool(v)


def movies_of(pred: dict) -> dict | None:
    """The movie-skip policy (``pred["movies"]``), checked STRICT before anything is driven, as :func:`battle_of`
    checks a registry row -- or None: the predictions carry no ``movies`` and the driver is O3's exactly.

    ValueError on: a policy that is no dict, an unknown key or a missing one (:data:`MOVIE_KEYS`,
    :data:`MOVIE_NEEDS`); a ``policy`` not in :data:`MOVIE_POLICIES`; ``cells`` not a non-empty list;
    ``press_every_s`` not a positive number; ``max_presses`` not an int >= 1; a ``match``, ``yes`` or ``no`` given
    and not a non-empty string; a cell that is no dict, has an unknown or a missing key, a ``donor`` that is no int, an
    ``sc`` that is no int and not None, an ``after_s`` that is not a positive number, a ``next_page_s`` that is
    neither None nor a positive number, or a ``why`` that is no non-empty string; two cells one place and SC would
    both match; and a cell whose presses could reach its next page -- with a ``next_page_s``, the last press
    (``after_s`` + (``max_presses`` - 1) x ``press_every_s``) and its wait (``press_every_s``) must end before it, or a
    press could turn that page. A bool is never a number. Returns a copy, with ``match``/``yes``/``no`` filled in from
    the engine's text when absent."""
    raw = pred.get("movies")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"movies {raw!r}: the policy is a dict of {MOVIE_KEYS}")
    unknown = sorted(set(raw) - set(MOVIE_KEYS))
    missing = [k for k in MOVIE_NEEDS if k not in raw]
    if unknown or missing:
        raise ValueError(f"movies {raw!r}: " + "; ".join(
            ([f"unknown key(s) {unknown}"] if unknown else []) + ([f"missing {missing}"] if missing else []))
            + f" -- the policy's keys are {MOVIE_KEYS}, of which {MOVIE_NEEDS} are needed")
    if raw["policy"] not in MOVIE_POLICIES:
        raise ValueError(f"movies: policy {raw['policy']!r} is not one of {MOVIE_POLICIES}")
    cells = raw["cells"]
    if not isinstance(cells, list) or not cells:
        raise ValueError(f"movies: cells {cells!r} is a non-empty list of cells")
    every, most = raw["press_every_s"], raw["max_presses"]
    if not _is_pos(every):
        raise ValueError(f"movies: press_every_s {every!r} is a positive number")
    if not _is_int(most) or most < 1:
        raise ValueError(f"movies: max_presses {most!r} is an int >= 1")
    bad = [k for k in ("match", "yes", "no") if k in raw and not _is_str(raw[k])]
    if bad:
        raise ValueError(f"movies: {bad} must be non-empty strings (the skip dialog's text)")
    out = {**raw, "cells": [], "match": raw.get("match", SKIP_MATCH), "yes": raw.get("yes", SKIP_YES),
           "no": raw.get("no", SKIP_NO)}
    seen: dict = {}
    for c in cells:
        if not isinstance(c, dict):
            raise ValueError(f"movie cell {c!r}: a cell is a dict of {MOVIE_CELL_KEYS}")
        unknown = sorted(set(c) - set(MOVIE_CELL_KEYS))
        missing = [k for k in MOVIE_CELL_NEEDS if k not in c]
        if unknown or missing:
            raise ValueError(f"movie cell {c!r}: " + "; ".join(
                ([f"unknown key(s) {unknown}"] if unknown else []) + ([f"missing {missing}"] if missing else []))
                + f" -- a cell's keys are {MOVIE_CELL_KEYS}, of which {MOVIE_CELL_NEEDS} are needed")
        wrong = (["donor"] if not _is_int(c["donor"]) else []) \
            + (["sc"] if c["sc"] is not None and not _is_int(c["sc"]) else []) \
            + (["after_s"] if not _is_pos(c["after_s"]) else []) \
            + (["next_page_s"] if c.get("next_page_s") is not None and not _is_pos(c["next_page_s"]) else []) \
            + (["why"] if not _is_str(c["why"]) else [])
        if wrong:
            raise ValueError(f"movie cell {c!r}: {wrong} of the wrong type (donor an int, sc an int or None, after_s "
                             f"and next_page_s positive numbers, why a non-empty string)")
        sc = c["sc"]
        clash = next((v for k, v in seen.items() if k[0] == c["donor"] and None in (sc, k[1])), None) \
            or seen.get((c["donor"], sc))
        if clash is not None:
            raise ValueError(f"movie cell {c!r}: place {c['donor']} at SC {sc} is registered twice ({clash!r})")
        seen[(c["donor"], sc)] = c
        if c.get("next_page_s") is not None:
            last = float(c["after_s"]) + (int(most) - 1) * float(every)
            if last + float(every) > float(c["next_page_s"]):
                raise ValueError(f"movie cell {c!r}: its last press comes {last:g} s into the visit and is waited on "
                                 f"{float(every):g} s more, past its next page at {c['next_page_s']:g} s -- a press "
                                 f"there can turn that page")
        out["cells"].append(dict(c))
    return out


def movie_cell(policy: dict | None, donor, sc) -> tuple | None:
    """``(index, cell)`` of the policy's registered cell for (``donor`` place, published ``sc``) -- a cell's ``sc``
    None is every SC -- or None (always None without a policy)."""
    for n, c in enumerate((policy or {}).get("cells") or ()):
        if c["donor"] == donor and c["sc"] in (None, sc):
            return n, c
    return None


def _line_is(line, word: str) -> bool:
    """A published choice line is ``word``: as published, or short its first character -- the agent's line after
    ``[CHOO]`` can lose it (O1's candle rule met "ight the candle"). Surrounding blanks aside; an empty line is none."""
    s = str(line or "").strip()
    return bool(s) and s in (word, word[1:])


def skip_answer(choice: dict | None, texts=(), policy: dict | None = None) -> int | None:
    """The ABSOLUTE option that answers YES when the ready ``choice`` is the engine's skip dialog -- else None (pure).

    It is that dialog only when ALL of these hold (``policy``'s ``match``/``yes``/``no``, default the engine's US
    text): the prompt (``options[0]``) holds ``match`` ("want to skip": US "the movie?" and UK "this cutscene?" alike,
    and a prompt short its first character too) -- or, when the agent publishes the prompt EMPTY, a published dialog
    text (``texts``) holds it; the shown lines are exactly two, ``yes`` then ``no``, each as published or short its
    first character (:func:`_line_is`); and the yes line is ABSOLUTE option 0, the one FieldHUD skips on (``active``,
    default the shown order). Another prompt, a third line, a reordered pair or a "Yes" at another index is None:
    never answered as a skip."""
    if not choice:
        return None
    p = policy or {}
    match, yes, no = p.get("match", SKIP_MATCH), p.get("yes", SKIP_YES), p.get("no", SKIP_NO)
    opts = list(choice.get("options") or [])
    if not opts:
        return None
    prompt, lines = str(opts[0] or ""), opts[1:]
    if match not in prompt:
        if prompt.strip() or not any(match in str(t or "") for t in texts or ()):
            return None
    if len(lines) != 2 or not _line_is(lines[0], yes) or not _line_is(lines[1], no):
        return None
    active = list(choice.get("active") or range(len(lines)))
    if len(active) != 2 or active[0] != 0:
        return None
    return 0


def skip_shaped(choice: dict | None) -> bool:
    """Whether a ready ``choice`` has the engine's skip dialog's SHAPE, whatever its text (pure): exactly two shown
    lines, both enabled (``active`` [0, 1], or not published), the cursor on the second -- ``[PCHC=2,1]`` under
    ``ETb.sChoose = 1``, which FieldHUD.OnKeyConfirm sets before it attaches the dialog (FieldHUD.cs:280). The dialog
    in a text :func:`skip_answer` cannot read (another language, a prompt published empty) keeps it; a dialog of any
    other shape is no skip dialog, whoever's press came before it."""
    if not choice:
        return False
    lines = list(choice.get("options") or [])[1:]
    active = choice.get("active")
    return len(lines) == 2 and (active is None or list(active) == [0, 1]) and choice.get("selected") == 1


def _raw_in_battle(raw: dict) -> bool:
    """``State.in_battle`` of a raw state document (the ring's): the battle up, and not the diorama."""
    b = raw.get("battle") or {}
    return bool(b.get("active")) and not b.get("debug")


def depth_in(points, x, z) -> float | None:
    """How deep (x, z) stands inside a region by the engine's rule: None outside it (IsInQuad,
    content.doorface.region_contains), else the distance to its nearest edge."""
    from ff9mapkit.content import doorface
    from ff9mapkit.scene import routes
    if x is None or z is None or not doorface.region_contains(x, z, points):
        return None
    pts = [(float(p[0]), float(p[1])) for p in points]
    return min(routes.seg_dist_xz(x, z, pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))


def hotspots_of(pred: dict, donor: int) -> list:
    """The frozen hot-spots of a place (2.5): ``[{"sid", "x", "z", "n"[, "reach"]}]``."""
    spots = pred.get("hotspots") or {}
    return list(spots.get(str(donor)) or spots.get(donor) or ())


def hotspot_reach(h: dict) -> float:
    """A hot-spot's reach: its tag 1 fires within ``32 * sqrt(n)`` of its own position (0.2 #9), rounded down."""
    return float(h["reach"]) if h.get("reach") is not None else float(int(32 * math.sqrt(h["n"])))


def _s16(v) -> int:
    return ((int(v) + 0x8000) & 0xFFFF) - 0x8000


def sample(st) -> dict:
    """A published state as the evidence rows keep it: ``{"frame", "control", "x", "z"}``."""
    x, z = st.player_x, st.player_z
    return {"frame": st.frame, "control": bool(st.control), "x": None if x is None else round(x, 1),
            "z": None if z is None else round(z, 1)}


def raw_sample(raw: dict) -> dict:
    """:func:`sample` of a raw state document (the ring's)."""
    p = raw.get("player") or {}
    x, z = p.get("x"), p.get("z")
    return {"frame": int(raw.get("frame", -1)), "control": bool(p.get("control", False)),
            "x": None if x is None else round(x, 1), "z": None if z is None else round(z, 1)}


def trim_route(r: dict | None) -> dict | None:
    """A route_to / route_cross record as a step row keeps it (dali_tour's trimming): its scalars, the waypoint count,
    and each object list as ``[uid, kind]`` pairs."""
    if r is None:
        return None
    keep = ("from", "landed", "changed_to", "reached", "inside", "travelled", "during", "replans", "waits", "cleared",
            "pushes", "pushed", "blocked", "frozen", "boxed", "boxed_by", "npcs", "npc_replans", "npc_waits",
            "box_waits", "box_cleared", "held_by", "handoff", "lost", "blockers")
    out = {k: r.get(k) for k in keep if k in r}
    out["route"] = len(r["waypoints"]) if r.get("waypoints") is not None else None
    for k in ("avoided", "entered", "through", "sealed", "boxers", "pinned"):
        if r.get(k):
            out[k] = [[o.get("uid"), o.get("kind")] for o in r[k]]
    return out


# ======================================================================== forbidden writes and their backing (pure)
def _check_forbid(p: dict) -> None:
    """A forbidden pattern is exactly 4.7's schema: its keys among FORBID_KEYS, a registered ``cause``, a ``why``, at
    least one matcher. Anything else raises -- a typo is an error, never a pattern that matches nothing."""
    unknown = sorted(set(p) - FORBID_KEYS)
    if unknown:
        raise ValueError(f"forbidden pattern {p!r}: unknown key(s) {unknown} -- the schema is {sorted(FORBID_KEYS)}")
    if p.get("cause") not in CAUSES:
        raise ValueError(f"forbidden pattern {p!r}: cause is not one of {CAUSES}")
    if not p.get("why") or not any(k in p for k in FORBID_MATCHERS):
        raise ValueError(f"forbidden pattern {p!r}: needs a why and at least one of {FORBID_MATCHERS}")
    if "ip_range" in p and (not isinstance(p["ip_range"], (list, tuple)) or len(p["ip_range"]) != 2):
        raise ValueError(f"forbidden pattern {p!r}: ip_range is [lo, hi]")


def _forbid_matches(p: dict, r, where: int, members: dict, route, ends) -> bool:
    if p.get("off_route") and on_route(r.fld, members, route, ends):
        return False
    if "donor" in p and where != p["donor"]:
        return False
    if "sid" in p and r.sid != p["sid"]:
        return False
    if "tag" in p and r.tag != p["tag"]:
        return False
    if "target" in p and r.target != p["target"]:
        return False
    if "ip_range" in p and not p["ip_range"][0] <= r.ip <= p["ip_range"][1]:
        return False
    return True


def _hotspot_at(rows: list, i: int, where: int, members: dict, pred: dict) -> dict | None:
    """The registered hot-spot a hit at ``rows[i]`` names: the run's own ``Int16[220]`` / ``[222]`` values there -- the
    last of each written in the same place at or before the hit (s16) -- matched to the place's frozen hot-spots.
    A hot-spot writes x before z, so a hit ON its x store takes the z written next in that place. None: no such pair,
    or one that is no registered hot-spot (the hit is then unbacked)."""
    spots = hotspots_of(pred, where)

    def last(target, upto):
        for j in range(upto, -1, -1):
            r = rows[j]
            if r.k == "w" and r.target == target and place(r.fld, members) == where:
                return r.new
        return None

    def after(target, frm):
        for j in range(frm, len(rows)):
            r = rows[j]
            if r.k in ("w", "r") and place(r.fld, members) != where:
                return None
            if r.k == "w" and r.target == target:
                return r.new
        return None
    x = last(HOT_X, i)
    for z in (last(HOT_Z, i), after(HOT_Z, i)):
        if x is None or z is None:
            continue
        for h in spots:
            if (int(h["x"]), int(h["z"])) == (_s16(x), _s16(z)):
                return {"sid": h.get("sid"), "x": int(h["x"]), "z": int(h["z"]), "reach": hotspot_reach(h)}
    return None


def forbidden_hits(rows: list, pred: dict, members: dict, start_place: int, *, end_fields=None) -> list:
    """4.7's forbidden patterns over a run's RAW rows: every ``w`` row -- masked sites, seam rows and every mode
    included -- from the run's START ROW (its first ``w`` row whose frozen place is ``start_place``) on, so the warp's
    residue and field 70 are never scanned. A row's place is the FROZEN one (:func:`segment_trace.place` over
    ``members``: ``{}`` on the S side). ``rows`` should already be cut at the run's end (the live scan and the analysis
    pass the same window). Returns one hit a matching (row, pattern): ``{"line", "f", "fld", "place", "sid", "tag",
    "ip", "target", "new", "pattern" (its index), "cause", "object", "why"}``, and for a ``confirm_hotspot`` hit the
    hot-spot the run's own position rows name (``hotspot``, or None). No start row: nothing is scanned."""
    pats = list(pred.get("forbidden") or ())
    for p in pats:
        _check_forbid(p)
    route = list(pred.get("route") or ())
    ends = list(end_fields if end_fields is not None else (pred.get("end_fields") or [pred.get("end_field")]))
    start = next((i for i, r in enumerate(rows) if r.k == "w" and place(r.fld, members) == start_place), None)
    if start is None:
        return []
    out = []
    for i in range(start, len(rows)):
        r = rows[i]
        if r.k != "w":
            continue
        where = place(r.fld, members)
        for n, p in enumerate(pats):
            if not _forbid_matches(p, r, where, members, route, ends):
                continue
            hit = {"line": r.line, "f": r.f, "fld": r.fld, "place": where, "sid": r.sid, "tag": r.tag, "ip": r.ip,
                   "target": r.target, "new": r.new, "pattern": n, "cause": p["cause"], "object": p.get("object"),
                   "why": p["why"]}
            if p["cause"] == "confirm_hotspot":
                hit["hotspot"] = _hotspot_at(rows, i, where, members, pred)
            out.append(hit)
    return out


def _visit_at(log: list, frame: int, fld: int) -> int | None:
    """The driver's visit a row of field ``fld`` at ``frame`` belongs to: the last ``visit`` row of that field at or
    before the frame (None: the driver never saw that field by then)."""
    got = None
    for row in log:
        if row.get("k") == "visit" and row.get("field") == fld and row.get("frame", 1 << 62) <= frame:
            got = row.get("visit")
    return got


def backing(hit: dict, log: list, pred: dict) -> dict | None:
    """4.7's BACKING RULE: whether the run's own driver ``log`` holds, at a frame BEFORE the hit's row frame (the trace's
    ``f`` and a state's ``frame`` are both Time.frameCount), the stray action the hit's ``cause`` names -- then the hit
    is the driver's walk divergence (live V12; the analysis uncovers the run), else a finding. Returns
    ``{"cause", "what", "row"}`` (the evidence), or None (unbacked).

      contact          a ``watch`` row with control held and the pattern's object within its published range_r + 150u
      confirm_hotspot  a ``press`` row in the hit's place and visit with control held at ``pre`` or ``post``, standing
                       within the named hot-spot's reach + 64u (the hot-spot from the run's own position rows)
      confirm_talk     a ``press`` row with control held whose ``near`` lists the object's talk disc
      choice           a ``choice`` row in the hit's place that took other than the game's default
      walk             a ``step`` row whose walk landed in the hit's field (its V11: the executor's landing judge, or
                       rule 2's on the last unfinished walk), started before the hit"""
    f, cause = hit["f"], hit["cause"]
    for row in log:
        k = row.get("k")
        if cause == "contact" and k == "watch" and row.get("control") and row.get("frame", 1 << 62) < f:
            for o in row.get("objects") or ():
                rr, d = o.get("range_r"), o.get("dist")
                if o.get("sid") == hit.get("object") and rr is not None and d is not None and d <= rr + CONTACT_SLACK:
                    return {"cause": cause, "what": f"a watch sample at frame {row['frame']} with sid {o['sid']} "
                                                    f"{d:.0f}u away (range_r {rr:.0f})", "row": row}
        elif cause in ("confirm_hotspot", "confirm_talk") and k == "press":
            if cause == "confirm_hotspot":
                hs = hit.get("hotspot")
                if hs is None or row.get("donor") != hit["place"] or row.get("visit") != _visit_at(log, f, hit["fld"]):
                    continue
            for side in ("pre", "post"):
                s = row.get(side) or {}
                if not s.get("control") or s.get("frame", 1 << 62) >= f or s.get("x") is None:
                    continue
                if cause == "confirm_hotspot":
                    d = math.hypot(s["x"] - hs["x"], s["z"] - hs["z"])
                    if d <= hs["reach"] + HOTSPOT_SLACK:
                        return {"cause": cause, "what": f"a Confirm at frame {s['frame']} {d:.0f}u from hot-spot e"
                                                        f"{hs['sid']} ({hs['x']}, {hs['z']}), reach {hs['reach']:.0f}",
                                "row": row}
                elif any(n.get("sid") == hit.get("object") and n.get("kind") == "talk" for n in row.get("near") or ()):
                    return {"cause": cause, "what": f"a Confirm at frame {s['frame']} inside sid {hit.get('object')}'s "
                                                    f"talk disc", "row": row}
        elif cause == "choice" and k == "choice" and row.get("donor") == hit["place"] \
                and row.get("frame", 1 << 62) < f and row.get("index") not in ("default", row.get("selected")):
            return {"cause": cause, "what": f"a choice answered {row.get('index')} over the default "
                                            f"{row.get('selected')}", "row": row}
        elif cause == "walk" and k == "step" and row.get("v") == "V11" and row.get("landed") == hit["fld"] \
                and row.get("frame0", 1 << 62) < f:
            return {"cause": cause, "what": f"step {row.get('name')!r} walked him into {row.get('landed')}",
                    "row": row}
    return None


def _hit_row(hit: dict) -> dict:
    """A hit as a log row names it: the row's fld / place / sid / tag / ip / target / new, its line and frame."""
    return {k: hit.get(k) for k in ("line", "f", "fld", "place", "sid", "tag", "ip", "target", "new")}


# ======================================================================== the end state
def target_bits(target: str) -> list:
    """The gEventGlobal bits a ``Global.<Width>[<i>]`` target spans: its bit for a Bit, else every bit of its bytes."""
    from ff9mapkit import storytrace as T
    width, index = target.split(".", 1)[1].rstrip("]").split("[")
    if width in T.BIT_WIDTHS:
        return [int(index)]
    return [int(index) * 8 + i for i in range(8 * T.WIDTH_BYTES[width])]


def value_of(target: str, bits: list) -> int:
    """A target's value from its bits (:func:`target_bits`' order, least significant first), two's complement for a
    signed width (SByte, Int16, Int24)."""
    v = sum(1 << i for i, b in enumerate(bits) if b)
    width = target.split(".", 1)[1].split("[")[0]
    if width in ("SByte", "Int16", "Int24", "UInt24") and bits and bits[-1]:
        v -= 1 << len(bits)
    return v


def read_end_state(g, pred: dict, timeout: float = 10.0) -> dict:
    """The predictions' ``end_state`` variables as the game holds them now (2.2, rule 1): every bit they span watched
    (``watch``), the next state that publishes them all read, then ``unwatch``. ``{target: value}``."""
    want = list((pred.get("end_state") or {}).keys())
    if not want:
        return {}
    spans = {t: target_bits(t) for t in want}
    bits = sorted({b for bs in spans.values() for b in bs})
    g.watch(*bits)
    try:
        st = g.wait_for(lambda s: all(s.flag(b) is not None for b in bits), timeout=timeout,
                        what="the end state's watched bits")
    finally:
        g.unwatch()
    return {t: value_of(t, [st.flag(b) for b in spans[t]]) for t in want}


# ======================================================================== the driver
class _Drive:
    """One run of the beat-table driver: its counters, its evidence, its rules and its step executors. :func:`drive`
    is the entry; research/o2_design.md 2.2 is the loop, 2.3 the executors, 2.7 the VOID classes, 4.7 the evidence."""

    def __init__(self, g, pred, side, log, *, deadline, floor_for, prior_for, progress, end_fields, observe,
                 forbid_live):
        self.g, self.pred, self.side, self.log, self.deadline = g, pred, side, log, deadline
        self.floor_for, self.prior_for, self.observe, self.forbid_live = floor_for, prior_for, observe, forbid_live
        self.members = ST.members_of(pred) if side == "F" else {}
        self.ends = list(end_fields if end_fields is not None else (pred.get("end_fields") or [pred["end_field"]]))
        self.route = list(pred.get("route") or ())
        self.start_place = place(pred["start"][side], self.members)
        # rule 2's ORDER: the places a run visits, in turn (``visits``; default ``route``, each once), from the start
        # place's first entry -- a rehearsal stage starts mid-route
        self.order = list(pred.get("visits") or self.route)
        if self.start_place not in self.order:
            raise ValueError(f"the start place {self.start_place} is not in the route's visit order {self.order}")
        self.at = self.order.index(self.start_place) - 1        # the place of the current visit, in self.order
        for c in pred.get("table") or ():                   # a malformed table refuses before anything is walked
            for raw in c["steps"]:
                step_of(pred, raw)
        # S4 (research/o3_design.md 2.1-2.3), OPT-IN: the battle registry and the stop pages, each checked strict
        # before anything is driven. With neither, nothing below reads them: the loop is O2's exactly.
        self.battles = [battle_of(pred, b) for b in pred.get("battles") or ()]
        for p in pred.get("stop_pages") or ():
            _check_stop_page(p)
        # OPT-IN (PLAN.md "Movie skip (opt-in)"): the movie-skip policy, checked strict before anything is driven.
        # Without it (None) nothing below reads it: the loop is O3's exactly.
        self.movies = movies_of(pred)
        self.movie_rows: list = []         # the policy's ``movie`` rows: one a visit it pressed in
        self.mv = None                     # the current visit's row, open until its outcome is set
        self.mv_last = None                # the wall time of that row's last press
        self.visit_t0 = None               # the wall time the current visit began (a cell's after_s counts from it)
        budget = pred["budget"]
        self.settle_s = float(budget["settle_s"])
        self.settle_polls = max(1, int(self.settle_s / POLL_S))
        self.no_progress_s = float(budget.get("no_progress_s", 120))
        # OPT-IN (O3; research/o3_design.md 11.7 #3): rule 1 waits for the run's first trace row in an end place
        self.end_row_s = None if budget.get("end_row_s") is None else float(budget["end_row_s"])
        self.beats = {b: False for b in pred.get("beats") or ()}
        self.pages, self.timed, self.choices, self.steps = [], [], [], []
        self.overlays, self.forbidden = [], []
        self.end_state = None
        self.answered: set = set()
        self.done: dict = {}               # (visit, donor, sc) -> steps done
        self.tries: dict = {}              # (visit, donor, sc, n) -> {"failed", "interrupted"}
        self.visit, self.cur = 0, None     # the visit counter and the field it is of
        self.fid = self.donor = self.sc = None
        self.held = 0                      # consecutive control polls (the settle)
        self.hold = None                   # a ready choice's (snapshot, since, frame)
        self.pending = None                # the last press row, its post not yet read
        self.walked = None                 # the last step row, while its walk ended unfinished and nothing acted since
        self.seen: set = set()             # (line, pattern) of every forbidden hit already judged
        self.floors: dict = {}
        self.sig, self.since = None, time.time()
        self.t0 = time.time()
        self.battle_log: list = []         # S4: the battle rows (2.3 step 6), out()'s and progress's "battles"
        self.battle_answered: set = set()  # S4: the registry rows this run has answered
        self.battle_epoch0 = self.battle_seen = None
        if self.battles:                   # only DELTAS of the epoch mean anything: the one published now is the zero
            self.battle_epoch0 = self.battle_seen = g.state.battle_epoch
        if progress is not None:
            progress.update(beats=self.beats, pages=self.pages, timed=self.timed, choices=self.choices,
                            steps=self.steps, overlays=self.overlays, forbidden=self.forbidden)
            if self.battles:               # a run that raises inside a battle still records them
                progress.update(battles=self.battle_log, battle_epoch0=self.battle_epoch0)
            if self.movies is not None:    # and one that raises mid-skip its movie rows
                progress.update(movies=self.movie_rows)

    # -- the outcome, a VOID ------------------------------------------------------------------------------------
    def out(self, end: str, why: str) -> dict:
        o = {"end": end, "why": why, "void": None, "beats": self.beats, "pages": self.pages, "timed": self.timed,
             "choices": self.choices, "steps": self.steps, "overlays": self.overlays, "forbidden": self.forbidden,
             "end_state": self.end_state, "t": round(time.time() - self.t0, 1)}
        if self.battles:                   # S4: only with a registry, so O2's outcome keeps its keys
            o.update(battles=self.battle_log, battle_epoch0=self.battle_epoch0)
        if self.movies is not None:        # the movie-skip policy: only with it, so O3's outcome keeps its keys
            o["movies"] = self.movie_rows
        return o

    def void(self, v: str, by: str, why: str):
        return RouteVoid(why, v=v, cell=[self.donor, self.sc], by=by)

    def stray(self, why: str) -> RouteVoid:
        """Rule 2's V11 (2.7), attributed: the DRIVER's when the last thing the run did was a walk that ended unfinished
        (``interrupted`` or ``failed``) with nothing pressed, answered or named since -- a door the executor did not
        see fire (its switch came after ``exit_wait_s``, or it is none the table registers). That step row then carries
        the landing (``landed``, ``v``, ``by``; ``late``: judged by the loop), which is what 4.7's ``walk`` backing reads,
        and the VOID its cell. Otherwise the GAME's: a scripted transition."""
        row = self.walked
        if row is None:
            return self.void("V11", "game", why)
        row.update(landed=self.fid, v="V11", by="driver", late=True,
                   why=f"{row.get('why')}; then {why}, with nothing done since the walk")
        return RouteVoid(f"{why}, after step {row.get('name') or row.get('n')!r} ({row.get('outcome')}) with nothing "
                         f"done since", v="V11", cell=[row.get("donor"), row.get("sc")], by="driver")

    # -- evidence -------------------------------------------------------------------------------------------------
    def near(self, st) -> list:
        """The published objects whose talk / range disc, NEAR_SLACK wider, holds him at ``st`` (a press row's)."""
        out = []
        if st.player_x is None:
            return out
        for o in st.objects or ():
            d = math.hypot(o["x"] - st.player_x, o["z"] - st.player_z)
            for kind, key in (("talk", "talk_r"), ("range", "range_r")):
                r = o.get(key)
                if r is not None and d <= r + NEAR_SLACK:
                    out.append({"sid": o.get("sid"), "uid": o.get("uid"), "kind": kind, "dist": round(d, 1),
                                "radius": r})
        return out

    def press(self, why: str, st, frames: int) -> dict:
        """Confirm, with its ``press`` row: ``pre`` the sample it was decided on, ``post`` filled from the ring's next
        sample (:meth:`post`), ``near`` the objects in reach at ``pre``."""
        row = {"k": "press", "why": why, "field": self.fid, "donor": self.donor, "visit": self.visit,
               "sc": self.sc, "pre": sample(st), "post": None, "near": self.near(st)}
        self.g.press("confirm", frames)
        self.log.append(row)
        self.pending = row
        return row

    def post(self) -> None:
        """The pending press row's ``post``: the first sample any read kept after its ``pre`` (no extra read)."""
        row, self.pending = self.pending, None
        if row is not None and row["post"] is None:
            nxt = next(iter(self.g.states_since(row["pre"]["frame"])), None)
            row["post"] = raw_sample(nxt) if nxt is not None else None

    def watch_row(self, raw: dict, c: dict) -> dict:
        """A ``watch`` row of a raw state in a watched cell: him, control, and the watched sids' published bodies --
        the field the SAMPLE was published in, and its frozen place."""
        s = raw_sample(raw)
        fid = int((raw.get("field") or {}).get("id", -1))
        sids = {w["sid"] for w in c.get("watch") or ()}
        objs = []
        for o in raw.get("objects") or ():
            if o.get("sid") in sids and s["x"] is not None:
                objs.append({"sid": o["sid"], "x": round(o["x"], 1), "z": round(o["z"], 1), "range_r": o.get("range_r"),
                             "talk_r": o.get("talk_r"),
                             "dist": round(math.hypot(o["x"] - s["x"], o["z"] - s["z"]), 1)})
        return {"k": "watch", **s, "field": fid, "donor": place(fid, self.members), "objects": objs}

    def watch_poll(self, st, c: dict) -> None:
        """A poll in a watched cell: its ``watch`` row, and V6 for a watched object within its radius, control held."""
        row = self.watch_row(st.raw, c)
        self.log.append(row)
        if not row["control"]:
            return
        for w in c.get("watch") or ():
            for o in row["objects"]:
                if o["sid"] != w["sid"]:
                    continue
                radius = o.get(w["radius"]) if isinstance(w.get("radius"), str) else w.get("radius")
                if radius is not None and o["dist"] <= radius:
                    raise self.void("V6", "driver", f"watched {w.get('name') or w['sid']} (sid {w['sid']}) is "
                                                    f"{o['dist']:.0f}u away with control held, within its "
                                                    f"{w['radius']} {radius:.0f}")

    def contact_before(self, frame: int, c: dict) -> bool:
        """V5's attribution: whether the log holds, before ``frame``, a watched object in contact reach (4.7)."""
        return any(backing({"f": frame, "cause": "contact", "object": w["sid"]}, self.log, self.pred)
                   for w in c.get("watch") or ())

    def scan(self) -> None:
        """The live forbidden scan (2.2, rule 3): the run's own rows (after its last arm, cut at its end), 4.7's
        patterns from its start row on. A hit the log backs is V12; an unbacked one is logged and the run goes on."""
        rows = self.g.story_rows()
        arm = max((i for i, r in enumerate(rows) if r.k == "e" and r.why == "arm"), default=None)
        if arm is None:
            return
        kept, _end = ST.cut_at_end(rows[arm:], self.ends, self.members)
        for hit in forbidden_hits(kept, self.pred, self.members, self.start_place, end_fields=self.ends):
            key = (hit["line"], hit["pattern"])
            if key in self.seen:
                continue
            self.seen.add(key)
            b = backing(hit, self.log, self.pred)
            row = {"k": "forbidden", "backed": b is not None, "row": _hit_row(hit), "pattern": hit["pattern"],
                   "cause": hit["cause"], "why": hit["why"], "hotspot": hit.get("hotspot"),
                   "by": None if b is None else b["what"]}
            self.log.append(row)
            self.forbidden.append(row)
            if b is not None:
                raise self.void("V12", "driver", f"a forbidden write the driver's own log backs: {hit['why']} "
                                                 f"({hit['fld']} e{hit['sid']} t{hit['tag']} ip{hit['ip']} "
                                                 f"{hit['target']}={hit['new']}), backed by {b['what']}")

    def end_row(self) -> dict:
        """Rule 1's opt-in wait (``budget.end_row_s``; research/o3_design.md 2.2, 11.7 #3): the run's FIRST trace row
        in an end place -- the row the analysis cuts at (:func:`segment_trace.cut_at_end` on the live trace after its
        last arm) -- waited for, up to ``end_row_s`` and never past the run's deadline. ``{"seen", "f", "s"}``: whether
        it came, its frame (``f``, None when it did not), the seconds waited. A row that never comes is no VOID here:
        the analysis reads that run (A-NOEND). A trace the harness cannot read raises, as the live scan does."""
        t0 = time.time()
        until = min(t0 + self.end_row_s, self.deadline)
        while True:
            rows = self.g.story_rows()
            arm = max((i for i, r in enumerate(rows) if r.k == "e" and r.why == "arm"), default=None)
            line = None if arm is None else ST.cut_at_end(rows[arm:], self.ends, self.members)[1]
            if line is not None or time.time() >= until:
                hit = next((r for r in rows if r.line == line), None) if line is not None else None
                return {"seen": hit is not None, "f": None if hit is None else hit.f, "s": round(time.time() - t0, 2)}
            time.sleep(END_ROW_POLL_S)

    # -- the walks ------------------------------------------------------------------------------------------------
    def floor(self, closed=()):
        key = (self.donor, tuple(closed))
        if key not in self.floors:
            self.floors[key] = self.floor_for(self.donor, list(closed))
        return self.floors[key]

    def walk_kw(self, step: dict) -> dict:
        """What every walk of a step passes (2.3): the donor's floor as the player walks it, with the step's closed
        triangles; its prior; the unstick / smooth / handoff walk; the step's npcs, overlay and settle."""
        from ff9mapkit.content import pathfind
        closed = closed_tris(self.pred, step, self.floor())
        return dict(walkmesh=self.floor(closed), prior=self.prior_for(self.donor), unstick=True, smooth=True,
                    margin=pathfind.KEEPOUT_MARGIN_W, timeout=float(step["timeout_s"]), npcs=bool(step["npcs"]),
                    overlay_ok=bool(step["overlay_ok"]), settle=step["settle"], handoff=True)

    # -- the landing judge (every executor): where a walk that lost control, or left the field, took him ----------
    def exit_at(self, x, z, slack: float) -> str | None:
        """The registered exit of this place (:func:`exit_regions`) that (``x``, ``z``) stands in or within ``slack``
        of -- where a door's ExitField took control: the nearest when two are that close. None: in no exit, or no
        position."""
        from ff9mapkit.content import pathfind
        if x is None or z is None:
            return None
        near = [(pathfind.poly_gap(x, z, pts), key) for key, pts in exit_regions(self.pred, self.donor)]
        near = [(gap, key) for gap, key in near if gap <= slack]
        return min(near)[1] if near else None

    def switch(self, out: dict, where: str, wait: float) -> int | None:
        """The map switch after control went in ``where`` (2.3): up to ``wait`` s of live frames for the published id
        to leave this field (``out["flip_frame"]`` the frame it was seen to), then for it to be positive -- the field he
        landed in. None: the id never left (or came back). A frozen or silent channel raises; an id that left and was
        never positive again is V14 (game)."""
        from harness import HarnessError
        g, fid = self.g, self.fid
        st = g.state
        if st.field_id == fid:
            try:
                st = g.wait_for(lambda s: s.field_id != fid, timeout=wait, what=f"{where}'s map switch")
            except HarnessError as err:
                if "live samples" not in str(err):
                    raise                               # a frozen or silent channel says nothing about the exit
                return None
        out.setdefault("flip_frame", st.frame)
        if st.field_id > 0:
            return st.field_id
        try:
            return g.wait_for(lambda s: s.field_id > 0 and s.field_id != fid, timeout=wait,
                              what=f"the field after {where}").field_id
        except HarnessError as err:
            if "live samples" not in str(err):
                raise
            raise self.void("V14", "game", f"the field id left {fid} and was never positive again within "
                                           f"{wait:.0f}s") from err

    def left_for(self, rec: dict, out: dict, where: str, wait: float) -> int | None:
        """The field the walk (``rec``) -- or anything since -- took him to: the record's landing, else the published
        id when it has already left this one (a load's id waited out to a positive one). None: still here."""
        new = rec.get("landed")
        if new == self.fid:
            new = None
        if new is None and self.g.state.field_id != self.fid:
            new = self.switch(out, where, wait)
        return new

    def strayed(self, step: dict, out: dict, new: int, why: str) -> tuple:
        """A walk that took him into ``new``, where its step leads nowhere: VOID V11, the driver's (2.7: a walk into
        the wrong door), with ``landed`` on the step row -- what 4.7's ``walk`` backing reads -- and the registered
        ``door`` his loss of control stood in, when one did (however late the switch was seen)."""
        lost = out.get("lost") or {}
        if out.get("door") is None:
            out["door"] = self.exit_at(lost.get("x"), lost.get("z"), float(step["exit_slack"]))
        out["landed"] = new
        out.update(v="V11", by="driver", why=f"{why}: landed in {new} (place {place(new, self.members)})")
        return "void", out

    def door_loss(self, step: dict, out: dict, why: str) -> tuple | None:
        """A control loss without the step's own evidence, standing in (or within ``exit_slack`` of) a registered exit
        of this place: that door's ExitField. Its switch is waited out here (``exit_wait_s``, never in the loop: a page
        up during the fade is no page) -- a landing is the walk's stray (V11, driver), no switch ``interrupted``. None:
        the loss was in no exit (the caller's verdict)."""
        lost = out.get("lost") or {}
        door = self.exit_at(lost.get("x"), lost.get("z"), float(step["exit_slack"]))
        if door is None:
            return None
        out["door"] = door
        new = self.switch(out, door, float(step["exit_wait_s"]))
        if new is not None:
            return self.strayed(step, out, new, f"{why}: control went in {door}")
        out["why"] = f"{why}: control went in {door} and the field held {float(step['exit_wait_s']):.0f}s"
        return "interrupted", out

    def crossed(self, step: dict, rec: dict, pts) -> tuple:
        """A crossing's verdict (2.3 ``cross``; the landing judge): the field changed -- the walk's landing, or the id
        already left (a load waited out) -> done in the step's ``to``, else V11; control went with the field unchanged
        -> at or inside the target (``exit_slack``) its FADE, waited out here for the map switch (``exit_wait_s``) --
        never in the loop, so a hint left up is no page -- at or inside ANOTHER registered exit of this place that
        door's, waited out the same way (a landing through it is V11, the driver's: the wrong door), anywhere else
        ``interrupted``; the walk ended with control held -> ``failed``."""
        from ff9mapkit.content import pathfind
        g, fid = self.g, self.fid
        wait, slack = float(step["exit_wait_s"]), float(step["exit_slack"])
        out = {"route": trim_route(rec), "lost": rec.get("lost"), "landed": None}
        st = g.state
        if out["lost"] is None and rec.get("landed") is None and st.field_id == fid and not st.control:
            out["lost"] = sample(st)                 # control went after the call's last read
        lost, door = out["lost"], step["target"]
        if lost is not None and lost.get("x") is not None and pathfind.poly_gap(lost["x"], lost["z"], pts) > slack:
            door = self.exit_at(lost["x"], lost["z"], slack)     # another exit of this place took him, or none did
        if door not in (None, step["target"]):
            out["door"] = door
        new = self.left_for(rec, out, door or step["target"], wait)
        if new is None and lost is not None:
            if door is None:
                out["why"] = (f"control went at ({lost['x']:.0f}, {lost['z']:.0f}), outside {step['target']} and "
                              f"every other exit")
                return "interrupted", out
            new = self.switch(out, door, wait)
            if new is None:
                out["why"] = f"control went in {door} and the field held {wait:.0f}s"
                return "interrupted", out
        if new is not None:
            out["landed"] = new
            if place(new, self.members) == step["to"]:
                return "done", out
            out.update(v="V11", by="driver", why=f"the crossing to {step['to']} landed in {new} (place "
                                                 f"{place(new, self.members)})"
                                                 + ("" if door in (None, step["target"]) else
                                                    f": control went in {door}, not {step['target']}"))
            return "void", out
        out["why"] = f"the walk ended with control held and nothing crossed (inside {rec.get('inside')})"
        return "failed", out

    def x_cross(self, step: dict) -> tuple:
        pts = region(self.pred, step["target"])["points"]
        rec = self.g.route_cross(*step["goal"], zone=pts, region=pts, avoid=polys(self.pred, step.get("avoid")),
                                 **self.walk_kw(step))
        return self.crossed(step, rec, pts)

    def x_leave_now(self, step: dict) -> tuple:
        """leave_now (2.3): the lunge on the first sample -- skipped when ``lunge_ticks`` is 0 or the field has no
        cached basis -- then the crossing at once (settle 0 unless the step says otherwise), judged as a cross."""
        from harness import HarnessError
        pts = region(self.pred, step["target"])["points"]
        avoid = polys(self.pred, step.get("avoid"))
        kw = self.walk_kw(step)
        if kw["settle"] is None:
            kw["settle"] = 0.0
        lunge = None
        if step.get("lunge_ticks") and self.fid in self.g._axes:
            try:
                lunge = self.g.lunge(*step["goal"], ticks=int(step["lunge_ticks"]), avoid=avoid,
                                     walkmesh=kw["walkmesh"])
            except HarnessError as err:
                lunge = {"pressed": False, "error": str(err)[:200]}
        st = self.g.state
        if st.field_id == self.fid and st.control:
            rec = self.g.route_cross(*step["goal"], zone=pts, region=pts, avoid=avoid, **kw)
        else:                                            # control went before the walk: judged where it went
            rec = {"landed": None, "inside": None,
                   "lost": sample(st) if st.field_id == self.fid and not st.control else None}
        verdict, out = self.crossed(step, rec, pts)
        out["lunge"] = lunge
        return verdict, out

    def x_trigger(self, step: dict) -> tuple:
        """trigger (2.3): the walk (into the ``target`` zone, or to the goal); control gone with the evidence at the
        loss sample -- standing in the target, or the ``until`` predicate holding -- is done (the trigger took him:
        what its script does next is the loop's to read). Anything else is the landing judge's: the field changed
        during the walk or after it -> V11 (driver); control gone in a registered exit of this place -> its switch
        waited out, V11 on a landing; otherwise ``interrupted``. A walk that ended with control held waits
        TRIGGER_WAIT_S for it to go, else ``failed``."""
        from harness import HarnessError
        from ff9mapkit.content import doorface
        g, fid = self.g, self.fid
        wait = float(step["exit_wait_s"])
        pts = region(self.pred, step["target"])["points"] if step.get("target") else None
        rec = g.route_to(*step["goal"], zone=pts, avoid=polys(self.pred, step.get("avoid")),
                         tolerance=float(step["tolerance"]), **self.walk_kw(step))
        out = {"route": trim_route(rec), "lost": rec.get("lost"), "landed": None}

        def evidence(s) -> bool:
            x, z = s.get("x"), s.get("z")
            return (x is not None and doorface.region_contains(x, z, pts)) if pts is not None \
                else until_ok(step["until"], x, z)
        if out["lost"] is not None and rec.get("landed") in (None, fid) and evidence(out["lost"]):
            return "done", out
        new = self.left_for(rec, out, "the trigger's walk", wait)
        if new is not None:
            return self.strayed(step, out, new, f"the trigger's walk left {fid}")
        if out["lost"] is None:
            st = g.state
            if st.control and st.field_id == fid:
                try:
                    st = g.wait_for(lambda s: not s.control or s.field_id != fid, timeout=TRIGGER_WAIT_S,
                                    what="the trigger to take control")
                except HarnessError as err:
                    if "live samples" not in str(err):
                        raise
                    out["why"] = "the walk ended with control held and nothing took it"
                    return "failed", out
            if st.field_id != fid:
                new = self.switch(out, "the trigger's wait", wait)
                if new is not None:
                    return self.strayed(step, out, new, f"the field left {fid} as the trigger was waited for")
                st = g.state
            out["lost"] = sample(st)
            if evidence(out["lost"]):
                return "done", out
        lost = out["lost"]
        why = f"control went at ({lost.get('x')}, {lost.get('z')}) without the step's evidence"
        verdict = self.door_loss(step, out, why)
        if verdict is not None:
            return verdict
        out["why"] = why
        return "interrupted", out

    def x_confirm(self, step: dict) -> tuple:
        """confirm (2.3): the walk to the goal WITHOUT the zone (a zone ends the walk at its edge), judged by the
        landing judge -- the field changed during the walk or the settle -> V11 (driver); control gone in a registered
        exit -> its switch waited out, V11 on a landing; else ``interrupted``. Settled, he must stand in the target by
        the engine's rule at depth >= ``min_depth`` or nothing is pressed (``failed``); then Confirm (a ``press`` row)
        and the ``expect``ed answer within ``confirm_s``; with ``then: "climb"`` the climb (H2): "until" done,
        "control" (he slid back) ``failed``, anything else V9."""
        from harness import HarnessError
        g, fid = self.g, self.fid
        wait = float(step["exit_wait_s"])
        pts = region(self.pred, step["target"])["points"]
        rec = g.route_to(*step["goal"], tolerance=float(step["tolerance"]), avoid=polys(self.pred, step.get("avoid")),
                         **self.walk_kw(step))
        out = {"route": trim_route(rec), "lost": rec.get("lost"), "landed": None, "depth": None}
        new = self.left_for(rec, out, "the Confirm's walk", wait)
        if new is not None:
            return self.strayed(step, out, new, f"the walk to the Confirm left {fid}")
        if out["lost"] is not None:
            why = "control went during the walk to the Confirm"
            verdict = self.door_loss(step, out, why)
            if verdict is not None:
                return verdict
            out["why"] = why
            return "interrupted", out
        st = g.settle()
        if st.field_id != fid:
            new = self.switch(out, "the Confirm's settle", wait)
            if new is not None:
                return self.strayed(step, out, new, f"the field left {fid} as he settled for the Confirm")
            st = g.state
        if not st.control:
            out["lost"] = sample(st)
            why = "control went as he settled"
            verdict = self.door_loss(step, out, why)
            if verdict is not None:
                return verdict
            out["why"] = why
            return "interrupted", out
        d = depth_in(pts, st.player_x, st.player_z)
        out["depth"] = None if d is None else round(d, 1)
        if d is None or d < float(step["min_depth"]):
            out["why"] = (f"settled at ({st.player_x:.0f}, {st.player_z:.0f}), "
                          + ("outside" if d is None else f"{d:.0f}u deep in") + f" {step['target']} (min_depth "
                          f"{step['min_depth']}): nothing pressed")
            return "failed", out
        row = self.press("confirm", st, 4)
        expect = step["expect"]
        want = (lambda s: s.choice is not None) if expect == "choice" else (lambda s: not s.control)
        try:
            g.wait_for(want, timeout=float(step["confirm_s"]), what=f"the Confirm's {expect}")
        except HarnessError as err:
            if "live samples" not in str(err):
                raise
            self.post()
            out["why"] = f"the Confirm showed no {expect} within {step['confirm_s']}s"
            return "failed", out
        self.post()
        out["press"] = row["pre"]["frame"]
        if step.get("then") != "climb":
            return "done", out
        climb = dict(step.get("climb") or {})

        def until(s):                         # no y bound: the published y RISES up 115's ladder (o2-rh-115), and
            return ((s.dialog_open and bool(s.text.strip()) and not s.control)      # the design's `y < -2431`
                    or s.field_id != fid)                                            # could never fire
        res = g.climb("up", until=until, **climb)
        out["climb"] = res
        if res["ended"] in ("until", "field"):
            return "done", out
        if res["ended"] == "control":
            out["why"] = "the climb slid back: control came back at the bottom"
            return "failed", out
        out.update(v="V9", by="driver", why=f"the climb ended {res['ended']}: y {res['y0']} -> {res['y1']} over "
                                            f"{res['bursts']} bursts")
        return "void", out

    def x_wait_sc(self, step: dict) -> tuple:
        """wait_sc (2.3): the walk to the wait point, judged by the landing judge first -- the field changed -> V11
        (driver); control gone in a registered exit -> its switch waited out, V11 on a landing -- then the SC: already
        ``sc`` -> done. A walk that lost control anywhere else is ``interrupted``; one that ended SHORT of the point (not
        ``reached``, or he stands farther than ``tolerance`` from it: blocked, boxed, no route) is ``failed`` with
        nothing waited -- the SC the table waits for may need him there (106: within 1400 of Puck's stop), so a wait
        from short of it is the driver's walk, not the game's. Then the wait for the published SC: reached -> done;
        the field changed -> V11 (driver); control gone -> the landing judge, else ``interrupted``; the wait out -> V8
        (game): only a wait begun AT the point is the game's."""
        from harness import HarnessError
        g, fid, want = self.g, self.fid, int(step["sc"])
        wait, tol = float(step["exit_wait_s"]), float(step["tolerance"])
        gx, gz = (float(v) for v in step["goal"])
        rec = g.route_to(gx, gz, tolerance=tol, avoid=polys(self.pred, step.get("avoid")), **self.walk_kw(step))
        out = {"route": trim_route(rec), "lost": rec.get("lost"), "landed": None}
        new = self.left_for(rec, out, "the wait's walk", wait)
        if new is not None:
            return self.strayed(step, out, new, f"the walk to the wait point left {fid}")
        if out["lost"] is not None:
            why = f"control went during the walk to the wait point, at SC {g.state.scenario}"
            verdict = self.door_loss(step, out, why)
            if verdict is not None:
                return verdict
            if g.state.scenario == want:
                return "done", out
            out["why"] = why
            return "interrupted", out
        st = g.state
        if st.scenario == want:
            return "done", out
        d = None if st.player_x is None else math.hypot(st.player_x - gx, st.player_z - gz)
        if not rec.get("reached") or d is None or d > tol:
            out["why"] = (f"the walk to the wait point ended " + ("where he stands unknown" if d is None
                                                                  else f"{d:.0f}u from it")
                          + f" (reached {rec.get('reached')}, route {out['route'].get('route')}, blocked "
                            f"{rec.get('blocked')}, boxed {rec.get('boxed')}, frozen {rec.get('frozen')}): no wait")
            return "failed", out
        try:
            st = g.wait_for(lambda s: s.scenario == want or not s.control or s.field_id != fid,
                            timeout=float(step["wait_s"]), what=f"SC {want}")
        except HarnessError as err:
            if "live samples" not in str(err):
                raise
            out.update(v="V8", by="game", why=f"SC never reached {want} within {step['wait_s']}s of a wait begun at "
                                              f"the point (it reads {g.state.scenario})")
            return "void", out
        if st.scenario == want:
            return "done", out
        if st.field_id != fid:
            new = self.switch(out, "the wait", wait)
            if new is not None:
                return self.strayed(step, out, new, f"the field left {fid} during the wait for SC {want}")
            st = g.state
        out["lost"] = sample(st)
        why = f"control went at SC {st.scenario}, before SC {want}"
        verdict = self.door_loss(step, out, why)
        if verdict is not None:
            return verdict
        out["why"] = why
        return "interrupted", out

    # -- one step -------------------------------------------------------------------------------------------------
    def run_step(self, c: dict, n: int, st) -> None:
        """Run step ``n`` of cell ``c`` (rule 8): its executor, its ``step`` row, the counters (2.3) -- done moves the
        cell on, ``failed`` spends an attempt, ``interrupted`` an interruption, either out of them VOID V7 -- and, in a
        watched cell, the ring's samples of the call as ``watch`` rows."""
        step = step_of(self.pred, c["steps"][n])
        key = (self.visit, self.donor, self.sc, n)
        tries = self.tries.setdefault(key, {"failed": 0, "interrupted": 0})
        frame0, t0 = st.frame, time.time()
        verdict, rec = getattr(self, "x_" + step["kind"])(step)
        after = self.g.state
        if c.get("watch"):
            # every sample the call's own reads kept, while he was still in the watched cell's field: a race lost
            # INSIDE a harness call stays on record (the ring runs on into the next field; those are not the cell's)
            for raw in self.g.states_since(frame0):
                if int((raw.get("field") or {}).get("id", -1)) == self.fid:
                    self.log.append(self.watch_row(raw, c))
        row = {"k": "step", "field": self.fid, "donor": self.donor, "sc": self.sc, "visit": self.visit, "n": n,
               "kind": step["kind"], "name": step.get("name"), "attempt": 1 + tries["failed"] + tries["interrupted"],
               "outcome": verdict, "t0": round(t0 - self.t0, 2), "t1": round(time.time() - self.t0, 2),
               "frame0": frame0, "frame": after.frame, "from": sample(st), "to": sample(after),
               "lost": rec.get("lost"), "landed": rec.get("landed"), "flip_frame": rec.get("flip_frame"),
               "door": rec.get("door"), "route": rec.get("route"), "lunge": rec.get("lunge"), "climb": rec.get("climb"),
               "depth": rec.get("depth"), "v": rec.get("v"), "by": rec.get("by"), "why": rec.get("why")}
        self.log.append(row)
        self.steps.append(row)
        self.since = time.time()                 # an executor is bounded by its own timeouts, not the watchdog
        # a walk that ended unfinished is what a field change seen next -- nothing pressed or answered between --
        # is laid to (rule 2)
        self.walked = row if verdict in ("interrupted", "failed") else None
        if verdict == "done":
            self.done[(self.visit, self.donor, self.sc)] = n + 1
            if step.get("beat"):
                self.beats[step["beat"]] = True
        elif verdict == "failed":
            tries["failed"] += 1
            if tries["failed"] >= int(step["attempts"]):
                raise self.void("V7", "driver", f"step {step.get('name') or n} ({step['kind']}) failed "
                                                f"{tries['failed']} of its {step['attempts']} attempts: {rec.get('why')}")
        elif verdict == "interrupted":
            tries["interrupted"] += 1
            if tries["interrupted"] > int(step["interrupts"]):
                raise self.void("V7", "driver", f"step {step.get('name') or n} ({step['kind']}) interrupted "
                                                f"{tries['interrupted']} times, over its {step['interrupts']}: "
                                                f"{rec.get('why')}")
        else:
            raise self.void(rec["v"], rec["by"], rec["why"])

    # -- the battle beat (S4, opt-in: a battle registry) ---------------------------------------------------------
    def battle(self, st) -> None:
        """Rule 1b's executor (research/o3_design.md 2.3): a NEW battle -- its epoch past every one this run has seen
        -- owns the loop until its landing field is up.

        1. Match: the published ``battle.scene``, the place of the VISIT it began in (never the poll's, which the
           over frame can flip; the poll's only before any visit) and the published SC, against the registry
           (:func:`battle_row`). No row: V10 (game). Either way the epoch is seen.
        2. Fight: ``g.fight(timeout=min(the row's timeout_s, the run's time left), max_turns=the row's, finish=False)``
           -- the default policy, the tutorials closed inside. No result within the row's own bounds
           (``FightTimeout``) is V15, the driver's: its policy and its bounds own the fight; a bound the run's
           deadline cut is the budget (V13). A scene that went away with no result while both bounds held
           (``FightTimeout`` kind "gone": a soft reset, a crash to the title) is no bound at all: an instrument stop,
           ``HarnessError`` (STOPPED, V13) with its own message, the battle row logged first (the review, 11.7 #2).
        3. Leave: ``g.leave_battle(stop_on_field=True, timeout=min(the row's land_cap_s, the run's time left))``, each
           of its Confirms a ``press`` row (``why`` "leave_battle", ``pre`` the sample it was decided on, ``post``
           None, ``near`` []). A leave that stops on its bound ("timeout") goes on to the landing, whose own clocks
           (and the deadline) then end the run: V14 past ``land_cap_s``, V13 past the deadline.
        4. Land, in two tiers: the field up (out of the battle, FieldHUD, a positive id) within ``land_s`` of the
           leave's end; else the wait goes on to ``land_cap_s`` (or the run's deadline), and a landing then is
           ``land_late`` ``{"frames", "s"}`` -- recorded, never a VOID. No field by the cap: V14 (game); by the
           deadline: the budget (V13).
        5. The flip: the first sample the ring holds in the battle at another field id -- its frame and its result.
        6. The ``battle`` row, logged and in ``out()["battles"]``; ``beats[the row's beat]`` the int result.
        7. The landing judge: S, the landed id is ``lands``; F, a member whose donor is ``lands`` -- REAL ``lands``
           is V16 (game: the s24 redirect did not fire, a FINDING) -- and anything else is V11 (game)."""
        from harness import FightTimeout, HarnessError
        g = self.g
        epoch, scene, fid = st.battle_epoch, (st.battle or {}).get("scene"), self.fid
        where = place(self.cur, self.members) if self.cur is not None else self.donor
        cell = [where, self.sc]
        self.battle_seen = epoch
        hit = battle_row(self.pred, where, self.sc, scene, self.battle_answered)
        if hit is None:
            raise RouteVoid(f"an unregistered battle: scene {scene} (epoch {epoch}) in {fid} (place {where}) at SC "
                            f"{self.sc}", v="V10", cell=cell, by="game")
        n, row = hit
        self.battle_answered.add(n)
        frame0, t0 = st.frame, time.time()
        rec = {"k": "battle", "field": fid, "donor": where, "visit": self.visit, "sc": self.sc, "scene": scene,
               "epoch": epoch, "row": n, "beat": row["beat"], "frame0": frame0, "t0": round(t0 - self.t0, 2),
               "result": None, "turns": None, "seconds": None, "tutorials": None, "timed_out": None, "leave": None,
               "flip_frame": None, "flip_result": None, "landed": None, "landed_place": None, "land_frame": None,
               "land_late": None, "t1": None, "v": None, "by": None, "why": None}

        def logged(v=None, by=None, why=None) -> None:
            rec.update(v=v, by=by, why=why, t1=round(time.time() - self.t0, 2))
            self.log.append(rec)
            self.battle_log.append(rec)
            self.since = time.time()          # the executor is bounded by its row, never by the watchdog
            self.walked = None

        def fought() -> None:
            last = g.last_fight or {}
            rec.update(turns=last.get("turns"), seconds=last.get("seconds"), tutorials=last.get("tutorials"),
                       timed_out=last.get("timed_out"))
        # 2 -- the fight, bounded by the row and by the run
        cap = float(row["timeout_s"])
        bound = min(cap, self.deadline - time.time())
        budget = f"the run's budget ran out in battle {scene}"
        if bound <= 0:
            logged("V13", "driver", budget)
            raise HarnessError(budget)
        try:
            result = g.fight(timeout=bound, max_turns=int(row["max_turns"]), finish=False)
        except FightTimeout as err:
            fought()
            if err.kind == "gone":            # the scene went with no result, no bound ran out: an instrument stop
                why = f"battle {scene}'s scene went away with no result: {str(err)[:200]}"
                logged("V13", "driver", why)
                raise HarnessError(why) from err
            rec["timed_out"] = True
            if err.kind == "timeout" and bound < cap:
                logged("V13", "driver", budget)
                raise HarnessError(budget) from err
            why = f"battle {scene} reached no result within {bound:.0f} s / {row['max_turns']} turns"
            logged("V15", "driver", f"{why}: {str(err)[:200]}")
            raise RouteVoid(why, v="V15", cell=cell, by="driver") from err
        fought()
        rec["result"] = result
        # 3 -- the leave: Confirm only while the battle scene is up, each Confirm a press row; bounded by the row's
        # land_cap_s and the run's deadline (the review, 11.7 #1: the loop's own 40 Confirms are no time bound)
        g.leave_battle(stop_on_field=True, timeout=max(0.0, min(float(row["land_cap_s"]), self.deadline - time.time())))
        leave = g.last_leave or {}
        presses = list(leave.get("presses") or ())
        for p in presses:
            self.log.append({"k": "press", "why": "leave_battle", "field": p.get("field"),
                             "donor": place(p.get("field"), self.members), "visit": self.visit, "sc": self.sc,
                             "pre": dict(p), "post": None, "near": []})
        uis: list = []
        for p in presses:
            if p.get("ui") not in uis:
                uis.append(p.get("ui"))
        rec["leave"] = {"presses": len(presses), "uis": uis, "stopped": leave.get("stopped")}
        # 4 -- the landing, in two tiers: past land_s it is late, not lost; past land_cap_s (or the deadline) it is
        t_end, f_end = time.time(), leave.get("frame")
        late_at, cap_at = t_end + float(row["land_s"]), t_end + float(row["land_cap_s"])

        def landed(s) -> bool:
            return not s.in_battle and s.ui_state == "FieldHUD" and s.field_id > 0
        land = self.land_wait(landed, min(late_at, self.deadline))
        if land is None:
            land = self.land_wait(landed, min(cap_at, self.deadline))
            if land is not None:
                rec["land_late"] = {"frames": None if f_end is None else land.frame - f_end,
                                    "s": round(time.time() - t_end, 2)}
        # 5 -- the flip: the first sample the ring holds in the battle at another field id
        flip = next((r for r in g.states_since(frame0)
                     if _raw_in_battle(r) and int((r.get("field") or {}).get("id", -1)) != fid), None)
        if flip is not None:
            rec.update(flip_frame=int(flip.get("frame", -1)), flip_result=(flip.get("battle") or {}).get("result"))
        if land is None:
            if self.deadline < cap_at:
                why = f"the run's budget ran out waiting for battle {scene}'s field"
                logged("V13", "driver", why)
                raise HarnessError(why)
            why = f"battle {scene} ended and no field came up within {float(row['land_cap_s']):g} s"
            logged("V14", "game", why)
            raise RouteVoid(why, v="V14", cell=cell, by="game")
        new = land.field_id
        rec.update(landed=new, landed_place=place(new, self.members), land_frame=land.frame)
        # 6 -- the beat: the battle's int result (S1 counts nothing else)
        self.beats[row["beat"]] = result
        # 7 -- the landing judge
        want = int(row["lands"])
        ok = (new in self.members and self.members[new] == want) if self.members else new == want
        if ok:
            logged()
            return
        if self.members and new == want:
            member = next((f for f, d in sorted(self.members.items()) if d == want), None)
            v, why = "V16", (f"battle {scene} landed in real {want}, not member({want}) {member}: the s24 redirect "
                             f"did not fire")
        else:
            v, why = "V11", f"battle {scene} landed in {new} (place {place(new, self.members)}), not {want}"
        logged(v, "game", why)
        raise RouteVoid(why, v=v, cell=cell, by="game")

    def land_wait(self, landed, until: float):
        """The battle's landing (2.3 step 4): the first state ``landed`` holds on by ``until`` (wall time), else None
        -- with no time left, the state as it is now (``wait_for`` would misreport a zero wait). A frozen or silent
        channel raises: it says nothing about the landing."""
        from harness import HarnessError
        left = until - time.time()
        if left <= 0:
            st = self.g.state
            return st if landed(st) else None
        try:
            return self.g.wait_for(landed, timeout=left, what="the battle's field (FieldHUD, out of the battle)")
        except HarnessError as err:
            if "live samples" not in str(err):
                raise
            return None

    # -- the movie-skip policy (opt-in: ``movies``) ----------------------------------------------------------------
    def movie_row(self) -> dict | None:
        """The current visit's ``movie`` row while it is open (no outcome yet), else None."""
        row = self.mv
        if row is None or row["visit"] != self.visit or row["outcome"] is not None:
            return None
        return row

    def movie_end(self, row: dict, outcome: str, why: str | None = None) -> None:
        """A visit's skip is settled: ``skipped``, or ``missed`` with its reason ('movie-skip missed: ...')."""
        row["outcome"] = outcome
        if outcome == "missed":
            row["missed"] = f"movie-skip missed: {why}"

    def movie_close(self, why: str) -> None:
        """The visit (or the run) ends with its row still open: missed, ``why``."""
        if self.mv is not None and self.mv["outcome"] is None:
            self.movie_end(self.mv, "missed", why)

    def movie_press(self, st) -> bool:
        """The policy's press (rule 9's, opt-in): in a REGISTERED cell (:func:`movie_cell`: this place and SC), on the
        field HUD with no dialog up, no choice and no control -- what 61 publishes from the arrival to page 72, FMV003
        and the script's tail after it -- at least the cell's ``after_s`` into the visit, and this visit's movie
        neither skipped nor given up: ONE Confirm, its
        ``press`` row (``why`` "movie_skip": its frame and sample), recorded on the visit's ``movie`` row (opened at the
        first press). FieldHUD's hit area takes it while the movie plays and opens the skip dialog, which rule 6
        answers (:meth:`movie_answer`). A press no dialog answers is pressed again ``press_every_s`` later, up to
        ``max_presses``; ``press_every_s`` after the last the visit gives up -- 'movie-skip missed', never a VOID: the
        movie plays out. True when it pressed (the loop polls again at once)."""
        if st.dialog_open or st.choice is not None or st.control or st.ui_state != "FieldHUD":
            return False
        hit = movie_cell(self.movies, self.donor, self.sc)
        if hit is None or self.visit_t0 is None:
            return False
        n, c = hit
        if self.mv is not None and self.mv["visit"] == self.visit and self.mv["outcome"] is not None:
            return False                                 # this visit's movie is skipped, or given up
        row = self.movie_row()
        now = time.time()
        t = now - self.visit_t0
        if t < float(c["after_s"]):
            return False
        every, most = float(self.movies["press_every_s"]), int(self.movies["max_presses"])
        if row is not None:
            if now - self.mv_last < every:
                return False                             # the last press's wait for its dialog
            if len(row["presses"]) >= most:
                self.movie_end(row, "missed", f"no skip dialog after {len(row['presses'])} press(es) "
                                              f"{every:g} s apart"
                               + (f" ({len(row['refused'])} dialog(s) refused as not the skip text)"
                                  if row["refused"] else ""))
                return False
        else:
            row = {"k": "movie", "field": self.fid, "donor": self.donor, "sc": self.sc, "visit": self.visit,
                   "cell": n, "why": c["why"], "after_s": c["after_s"], "next_page_s": c.get("next_page_s"),
                   "presses": [], "refused": [], "dialog": None, "outcome": None, "frame": None, "t": None,
                   "left_s": None, "missed": None}
            self.mv = row
            self.log.append(row)
            self.movie_rows.append(row)
        p = self.press("movie_skip", st, 4)
        row["presses"].append({"frame": p["pre"]["frame"], "t": round(t, 2)})
        self.mv_last = now
        self.walked = None
        return True

    def movie_answer(self, st) -> bool:
        """Rule 6's skip answer (opt-in): the ready choice is answered YES -- ABSOLUTE option 0, FieldHUD's skip
        (``g.choose``) -- only while this visit's ``movie`` row is open with a press of the policy's own behind it,
        and only when the choice IS the skip dialog (:func:`skip_answer`: its prompt, its two lines). Its ``choice``
        row (``rule`` "movie_skip": a choice the driver took over the game's default, as 4.7's ``choice`` backing
        reads it) and the movie row's dialog (prompt, options, active, selected, count), frame, seconds into the
        visit and ``left_s`` (the cell's ``next_page_s`` less them: the most the skip can save, since the script's
        tail after the movie runs either way -- what it saved is the A/B's, from the drive times).

        A dialog no press of the policy opened is the ordinary rules' (False), as with no policy at all. One it
        REFUSES (not the skip text) while its press is behind it is kept on the row as ``refused`` (once), and then:
        a frozen rule that answers it answers it (:func:`rule_for`; False -- a script's choice that came instead is
        the route's, its pick, ``once`` and beat included); with no rule, a dialog of the skip dialog's shape
        (:func:`skip_shaped`: the skip dialog in a text it cannot read -- the engine localizes it, FieldHUD.cs:281 --
        or a prompt published empty) is the policy's own press's, so the policy answers it at the game's own default
        (No: the engine resumes the movie on any answer but 0, :428-440) -- a ``choice`` row, index "default", ``rule``
        "movie_skip_default" -- and the attempts count on to 'movie-skip missed': never a VOID, and the frozen table is
        never asked. A dialog of any other shape is no skip dialog: the ordinary rules' (False; V1, the game's, with no
        rule). True when it answered (or its default's Confirm did not land: asked again on a later poll)."""
        row = self.movie_row()
        if row is None or not row["presses"]:
            return False
        ch = st.choice
        snap = {k: ch.get(k) for k in ("options", "active", "selected", "count")}
        index = skip_answer(ch, st.texts, self.movies)
        if index is None:
            if snap not in row["refused"]:
                row["refused"].append(snap)
            if rule_for(ch, self.donor, self.pred, sc=self.sc) is not None or not skip_shaped(ch):
                return False
            took = self.g._take_default_choice(st)
            if took is None:
                return True                              # the Confirm did not land: the dialog is asked again
            self.walked = None
            crow = {"k": "choice", "field": self.fid, "donor": self.donor, "sc": self.sc, "frame": st.frame,
                    "options": ch.get("options"), "active": ch.get("active"), "selected": ch.get("selected"),
                    "count": ch.get("count"), "index": "default", "rule": "movie_skip_default", "took": took}
            self.choices.append(crow)
            self.log.append(crow)
            return True
        self.g.choose(index)
        t = time.time() - self.visit_t0
        self.walked = None
        crow = {"k": "choice", "field": self.fid, "donor": self.donor, "sc": self.sc, "frame": st.frame,
                "options": ch.get("options"), "active": ch.get("active"), "selected": ch.get("selected"),
                "count": ch.get("count"), "index": index, "rule": "movie_skip", "took": {"index": index}}
        self.choices.append(crow)
        self.log.append(crow)
        span = row.get("next_page_s")
        row.update(dialog=snap, frame=st.frame, t=round(t, 2),
                   left_s=None if span is None else round(float(span) - t, 1))
        self.movie_end(row, "skipped")
        return True

    def movie_page(self, st) -> None:
        """A page up while this visit's row waits on its press (rule 7, opt-in): it came INSTEAD of the skip dialog --
        the movie is over, or was never there -- so the visit's skip is given up (missed) before the page rule turns
        it; no press of the policy follows it."""
        row = self.movie_row()
        if row is not None and row["presses"]:
            self.movie_end(row, "missed", f"a page opened instead of the skip dialog: {st.text[:80]!r}")

    # -- the loop -------------------------------------------------------------------------------------------------
    def go(self) -> dict:
        from harness import HarnessError
        g, pred = self.g, self.pred
        while time.time() < self.deadline:
            st = g.state
            if self.pending is not None:
                self.post()
            self.fid, self.sc = st.field_id, st.scenario
            self.donor = place(self.fid, self.members)
            if self.observe is not None:
                self.observe(st, {"field": self.fid, "donor": self.donor, "sc": self.sc, "visit": self.visit,
                                  "log": self.log})
            # 1 -- the end: the end state, the last scan, done -- and, opt-in, the end place's first trace row waited for
            if self.fid in self.ends:
                self.end_state = read_end_state(g, pred)
                if self.forbid_live:
                    self.scan()
                row = {"k": "end", "field": self.fid, "frame": st.frame, "sc": self.sc, "end_state": self.end_state,
                       "t": round(time.time() - self.t0, 1)}
                if self.end_row_s is not None:
                    row["end_row"] = self.end_row()
                self.log.append(row)
                if self.movies is not None:
                    self.movie_close("the run reached its end with no skip dialog")
                return self.out("reached", f"field {self.fid}")
            # the stall watchdog: nothing published changed for no_progress_s
            sig = (self.fid, self.sc, st.ui_state, tuple(st.texts), json.dumps(st.choice, sort_keys=True), st.control,
                   None if st.player_x is None else round(st.player_x / 8),
                   None if st.player_z is None else round(st.player_z / 8), (st.storytrace or {}).get("rows"))
            if sig != self.sig:
                self.sig, self.since = sig, time.time()
            elif time.time() - self.since >= self.no_progress_s:
                raise self.void("V14", "game", f"no progress for {self.no_progress_s:.0f} s in {self.fid} (place "
                                               f"{self.donor}) at SC {self.sc}")
            # 1b -- a NEW battle (S4, opt-in: a registry): its executor owns the loop until the landing field is up.
            # BEFORE rules 9, 2 and 3, so the field id a battle publishes at its over frame (research/o3_design.md
            # 0.2 #8) is never read as a load, a leave or a visit
            if self.battles and st.in_battle and st.battle_epoch > self.battle_seen:
                self.held = 0
                self.battle(st)
                continue
            if self.fid <= 0:                        # 9 -- a load: waited out
                self.held = 0
                time.sleep(POLL_S)
                continue
            # 2 -- the route: a field on it, and (at a new visit) the place its order goes to next
            if not on_route(self.fid, self.members, self.route, self.ends):
                raise self.stray(f"left the route: entered {self.fid} (place {self.donor})")
            # 3 -- a new visit
            if self.fid != self.cur:
                want = self.order[self.at + 1] if self.at + 1 < len(self.order) else None
                if self.donor != want:
                    raise self.stray(f"out of the route's order: entered {self.fid} (place {self.donor}), where the "
                                     f"route goes next to {want}")
                self.at += 1
                self.walked = None
                self.visit, self.cur = self.visit + 1, self.fid
                self.log.append({"k": "visit", "field": self.fid, "donor": self.donor, "visit": self.visit,
                                 "frame": st.frame, "sc": self.sc})
                if self.movies is not None:          # the policy's clock: a cell's after_s counts from the visit
                    self.movie_close("the visit ended with no skip dialog")
                    self.visit_t0 = time.time()
                if self.forbid_live:
                    self.scan()
            c = cell(pred, self.donor, self.sc)
            if c is not None and c.get("watch"):
                self.watch_poll(st, c)
            # 4 -- the naming screen
            if st.ui_state == "NameSetting":
                self.held = 0
                reg = next((x for x in pred.get("naming") or () if x["donor"] == self.donor and x["sc"] == self.sc),
                           None)
                if reg is None:
                    raise self.void("V10", "game", f"a naming screen in {self.fid} (place {self.donor}) at SC "
                                                   f"{self.sc}, where the route registers none")
                g.accept_name()
                self.walked = None
                if reg.get("beat"):
                    self.beats[reg["beat"]] = True
                self.log.append({"k": "named", "field": self.fid, "donor": self.donor, "sc": self.sc,
                                 "frame": st.frame})
                continue
            # 5 -- a tutorial or a battle: the route registers neither
            if st.ui_state == "Tutorial" or st.in_battle:
                raise self.void("V10", "game", f"{'a battle' if st.in_battle else 'a tutorial'} in {self.fid} "
                                               f"(place {self.donor}) at SC {self.sc}, where the route registers none")
            # 6 -- a choice: O1's readiness hold, then the frozen rules
            if st.choice is not None:
                self.held = 0
                if not g._choice_ready(st):
                    time.sleep(POLL_S)
                    continue
                snap = json.dumps(st.choice, sort_keys=True)
                if self.hold is None or self.hold[0] != snap:
                    self.hold = (snap, time.time(), st.frame)
                    time.sleep(POLL_S)
                    continue
                if time.time() - self.hold[1] < self.settle_s or st.frame <= self.hold[2]:
                    time.sleep(POLL_S)
                    continue
                self.hold = None
                if self.movies is not None and self.movie_answer(st):    # opt-in: the skip dialog its press opened
                    continue
                self.answer(st)
                continue
            # 7 -- a page (control off)
            if st.dialog_open and st.text.strip() and not st.control:
                self.held = 0
                stop = stop_page(pred, st)
                if stop is not None:                 # S4, opt-in: a stop page VOIDs with NOTHING pressed -- the
                    # driver's in the run's first visit, the start place (the warp's start state); else the game's
                    by = "driver" if self.visit == 1 and place(self.cur, self.members) == self.start_place else "game"
                    raise self.void("V5", by, f"a stop page ({stop['why']}), nothing pressed: {st.text[:160]!r}")
                if c is not None and c.get("no_pages"):
                    by = "driver" if self.contact_before(st.frame, c) else "game"
                    raise self.void("V5", by, f"a page where the route has none: {st.text[:160]!r}")
                if not self.pages or self.pages[-1] != st.text:
                    self.pages.append(st.text)
                    if any("[TIME=" in t for t in st.raw_texts):
                        self.timed.append(len(self.pages) - 1)
                if self.movies is not None:          # opt-in: a page that came instead of the skip dialog
                    self.movie_page(st)
                self.press("page", st, 3)
                self.walked = None
                g.wait_frames(g.rate().frames_for_ticks(g.CUTSCENE_PAGE_TICKS))
                continue
            # 8 -- control held: settled O1's way (settle_s of consecutive control polls, unless the cell's next step
            # is ``immediate``) BEFORE either V4 -- a single control sample in a scene is not control -- then the
            # cell's next step
            if st.control and st.player_x is not None and not st.fading:
                if st.dialog_open and st.text.strip() and st.text not in self.overlays:
                    self.overlays.append(st.text)
                    self.log.append({"k": "overlay", "field": self.fid, "frame": st.frame, "text": st.text})
                n = self.done.get((self.visit, self.donor, self.sc), 0)
                nxt = step_of(pred, c["steps"][n]) if c is not None and n < len(c["steps"]) else None
                if nxt is None or not nxt.get("immediate"):
                    self.held += 1
                    if self.held < self.settle_polls:
                        time.sleep(POLL_S)
                        continue
                self.held = 0
                if c is None:
                    raise self.void("V4", "game", f"control held in {self.fid} (place {self.donor}) at SC "
                                                  f"{self.sc}, where the table has no entry")
                if nxt is None:
                    raise self.void("V4", "game", f"control held in {self.fid} (place {self.donor}) at SC "
                                                  f"{self.sc} after the cell's last step")
                self.run_step(c, n, st)
                continue
            # 9 -- anything else (a movie, a fade, a scene between pages): wait -- or, opt-in, the movie-skip press
            self.held = 0
            if self.movies is not None and self.movie_press(st):
                continue
            time.sleep(POLL_S)
        raise HarnessError(f"the run's budget ran out in field {g.state.field_id}")

    def answer(self, st) -> None:
        """Rule 6's answer: the frozen rule (pick_for; a classless RouteVoid there is V1, game), the game's own default
        taken for a ``take: "default"`` rule (the cursor never moved) or O1's ``choose``, and its ``choice`` row. A
        default whose Confirm did not land is asked again on a later poll, never counted answered."""
        g = self.g
        try:
            index, rule = pick_for(st.choice, self.donor, self.pred, sc=self.sc, answered=self.answered)
        except RouteVoid as err:
            if err.v is None:
                raise self.void("V1", "game", str(err)) from err
            raise
        n = next(i for i, r in enumerate(self.pred["choices"]) if r is rule)
        if index == "default" or rule.get("take") == "default":
            took = g._take_default_choice(st)
            if took is None:
                return
        else:
            g.choose(index)
            took = {"index": index}
        self.walked = None
        ch = st.choice
        row = {"k": "choice", "field": self.fid, "donor": self.donor, "sc": self.sc, "frame": st.frame,
               "options": ch.get("options"), "active": ch.get("active"), "selected": ch.get("selected"),
               "count": ch.get("count"), "index": index, "rule": n, "took": took}
        self.choices.append(row)
        self.log.append(row)
        self.answered.add(n)
        if rule.get("beat"):
            self.beats[rule["beat"]] = True


def drive(g, pred: dict, side: str, log: list, *, deadline: float, floor_for=None, prior_for=None,
          progress: dict | None = None, end_fields=None, observe=None, forbid_live: bool = True) -> dict:
    """Play the segment by its beat table (research/o2_design.md 2.2), from wherever the run stands to an end field.

    Returns ``{"end": "reached", "why", "void": None, "beats", "pages", "timed", "choices", "steps", "overlays",
    "forbidden", "end_state", "t"}`` -- and, with a battle registry (research/o3_design.md S4), ``"battles"`` (the
    battle rows) and ``"battle_epoch0"`` (the epoch published when the drive started); with a movie-skip policy
    (``movies``, PLAN.md "Movie skip (opt-in)"), ``"movies"`` (its ``movie`` rows); anything the table cannot
    answer raises :class:`RouteVoid` with its class, cell and attribution (2.7), and the budget ``HarnessError``
    (V13). ``floor_for(donor, closed)`` gives a walk its
    floor (default: the donor's stock walkmesh as the player walks it, ``closed`` shut -- a member walks its donor's,
    P-FLOOR), ``prior_for(donor)`` its prior (default ``g.key_prior``); ``end_fields`` overrides the predictions' (a
    rehearsal stage); ``observe(st, ctx)`` sees every poll (the rehearsal recorder); ``forbid_live`` runs the live
    forbidden scan (V12; it needs the story trace running). ``progress`` is filled with the live beats, pages, choices,
    steps, overlays and forbidden rows, so a run that raises still says how far it got."""
    if floor_for is None:
        from ff9mapkit import extract
        from ff9mapkit.content import pathfind

        def floor_for(donor, closed):
            return pathfind.PlayerWalkmesh(extract.stock_walkmesh(donor), closed=closed)
    return _Drive(g, pred, side, log, deadline=deadline, floor_for=floor_for, prior_for=prior_for or g.key_prior,
                  progress=progress, end_fields=end_fields, observe=observe, forbid_live=forbid_live).go()
