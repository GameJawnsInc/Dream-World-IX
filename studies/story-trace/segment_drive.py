"""THE STORY-WRITE TRACE's segment driver, shared by O1, O2 and O3 (research/o2_design.md, sections 1.4 and 2;
research/o3_design.md 1.2 S4 and 2).

``RouteVoid`` and ``pick_for`` moved here from ``o1_opening`` (which imports and re-exports both): O1's rules and
O1's ``raise RouteVoid(msg)`` behave exactly as they did. What O2 adds is additive and optional:
  - a RouteVoid may carry its VOID class (``v``: "V1".."V19"), its beat-table ``cell`` (``[donor, sc]``) and who it
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

THE ENDS PER SIDE (opt-in, ``side_ends``; research/o4_design.md 1.2 S6): a segment whose fork side ends IN A MEMBER
(O4: S in real 153, F in member(153)) gives each side its own END FIELDS (``segment_trace.side_ends``), and the drive
keeps them apart from the END PLACES its cuts compare (``segment_trace.end_places``): rule 1 fires on the side's own
end field, the live scan and the end row cut at the end places, and on F a REAL field the chain forks is V19 by the
game -- a Field() the build did not retarget: a finding -- where it would be V11. Without the key both come from the
predictions' one list, and with no end field a member (O1-O3) every list and place is today's.

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

THE CHANBARA POLICY (opt-in, ``chanbara``; research/o4_design.md 2.4, S7-S9): 64's sword fight, played by the driver to
the owner's displayed 100/100. :func:`chanbara_of` reads the policy STRICT (the one button map, :data:`DBTN_CONTROL`:
``circle`` is Control.Confirm, the Cross bit, and is refused). RULE 6b, before rule 7, claims a published prompt
(:func:`prompt_dbtn`: one [DBTN], "Press", [TIME=-1] in ``phrase_raw``) or the zone start (:func:`is_zone_start`: 111)
in the policy's cell, and its executor (:class:`_ChanbaraZone`) owns the loop until the zone's end text: 111 pressed
page-once, a quiet wait, then a tight loop over the MERGED sample stream (its own reads and the ring's) -- the input
witness, the UI, the field, control, the fail-closed claims (any other dialog or a choice is V17 with an ``observed``
row), the instance tracker (a prompt closing beside its successor is never a new instance), one mapped press per
instance (fast, or paced to a target in game ticks), the lost press -- and at its end the rows completed (each press
placed by its accepted event, the evidence, the j and raw bounds, the slides) and :func:`chanbara_judge`: V17 (the
driver's: its input is not proven the frozen play) or V18 (the game's: a sample SHOWED it deviate -- a finding).
Rule 7 under the policy refuses an unrecognized [DBTN] page, presses page-once per window, keeps the quiet window after
123, reads the score and gil pages in two consecutive samples, and sends a replay after the encore answer to
:func:`stray_answer` (V17 or V2); ``answer`` rows ``choose``'s own presses. ``drive``'s ``witness`` -- outside input,
polled through the whole run -- stops a run V13. Without the key the loop is O3's exactly.

THE RUN-WIDE WITNESS (opt-in, ``witness``; research/o5_design.md 1.2 S12): ``drive``'s outside-input witness polled
through the whole run (:func:`witness_of`, checked strict), not only under the Chanbara policy -- a stored answer
(O5's Bit[3795]) makes outside input anywhere a false-finding risk: a non-neutral reading is an ``input`` row, then V13.
VISIT-SCOPED CELLS (opt-in, a cell's ``visit``; S13): a cell carrying ``visit`` -- the 1-based position of a visit in
``visits`` -- answers only that visit (:func:`cell`), so control at a REVISIT of the same place at the same SC is V4
(the game's), never the walk a first visit runs; and under such a table every VOID's and ``observed`` row's cell is
``[place, sc, visit]`` (:meth:`_Drive.vcell`), so one class at two visits of a place is two keys for VOID-ASYM. Without
either key the loop is O4's exactly.

THE PRE-CHOICE GUARD (opt-in, ``guard``; research/o5_design.md 1.2 S10, 2.5) closes the race between a marker page and
the choice it precedes (O5's 127 -> 128: a Confirm decided on a stale or closing 127 lands on 128 at its cursor). Read
STRICT (:func:`guard_of`), it makes rule 7 PAGE-ONCE on the marker page -- a window pressed only past its own hold-off
AND past the hold-off of the driver's LAST press of any kind -- opens a QUIET WINDOW at the first sample after it with no
marker window, presses nothing until the choice is published (a page there is V17, game-observed; the marker page seen
again re-arms it; no choice within ``quiet_cap_s``, the ring scanned first, is V13), rows every press with its ``seq``,
and JUDGES the run at the first page after the answer (:meth:`_Drive.guard_judge`): the marker page never pressed by
page-once, or a press of the driver's own down in [the marker page's last sample, the choice's close)
(:func:`guard_strays`), is V17; the OTHER branch's first page -- the game's own record of the answer it took -- is V13.
The choice gone with no answer of the driver's is V17 or V13 (:meth:`_Drive.guard_stray`) -- read on the next page,
or by the answer itself when the choice is taken before its first Confirm (:meth:`_Drive.answer_gone`); asked again
after its verified answer, V2 (game). Under the guard rule 6 answers a non-default pick through THE VERIFIED LANDING
(S11: :meth:`Session.choose_landed`), its presses rowed, the witness polled at once, and the answer proven the driver's:
not landed, unseen or unplaceable is V17; the cursor off the pick as its Confirm went down, V13. Without the key the
loop is O4's exactly (O4's ``stray_answer`` untouched).

THE LANDING-AWARE TRIGGER (opt-in, a trigger step's ``to``; research/o6_design.md 1.2 S14, S14b; decision 3): a door
whose ExitField walks him on after it takes control (O6's 153 e23: MOVJ toward a point beyond the floor's end for the
25 ticks before its Field()) hands the run to the next field either before route_to's settle returns (path A) or after
it (path B) -- the engine's timing, never the walk's. A trigger step carrying ``to`` (the place its door leads to) is
run by :meth:`_Drive.x_trigger_to` and judged by :func:`trigger_to_verdict`: done when the step's evidence held at the
loss sample read IN THE WALK'S FIELD and the run has not left yet or left for ``to``; the evidence held and a landing
ELSEWHERE is ``left`` -- the landing kept under ``misroute``, and rule 2 judges it on the next poll as it judges any
field change (V11 by the game, or V19 on F for a real field a member forks): the walk cannot cause it; a loss never
read in the walk's field is V13, the instrument's. Rule 1 then puts the done step's walk-out on its row
(:meth:`_Drive.walkout_record`): the samples from the loss to the flip, the flip's frame and the landing's, in both
paths. Without ``to`` a trigger is O5's exactly.

THE NAME ON THE PAGE (opt-in, a naming registration's ``on_page``; research/o6_design.md 1.2 S16; decision 4): the name
a naming screen saves is PLAYER.Name, no gEventGlobal store, so the trace never sees it -- the page that renders it does
([STNR] on O6's 199 and 200). The registrations are read STRICT before anything is driven (:func:`naming_of`). Under one
carrying ``on_page``, rule 4 keeps the ring's last sample that listed a window before the screen (the ``named`` row's
``before``: what came before the naming, read before accept_name's Confirms), and arms THE PAGE WITNESS: every poll
after rule 3 it scans the ring for the first sample in the naming's field listing a PARSED window a frozen entry names
(:meth:`_Drive.page_witness`) and JUDGES its lines against the frozen ones -- equal, a ``name_on_page`` row (``verdict``
"ok") and its beat; another name, the row (``verdict`` "V13") and the run VOID V13 by the driver: input at the naming
screen, inside accept_name's blocking call, where the run-wide witness does not look. A new visit takes a last scan and
disarms it -- nothing found, the beat stays False: the run uncovered, never failed. Without ``on_page`` rule 4 is O5's
exactly.

THE WALK, THE CLEARANCE AND THE PRIOR BASIS (opt-in; research/o7_design.md 1.2 S17-S19): a ``walk`` step's evidence is
an ARRIVAL (:meth:`_Drive.x_walk`: the landing judge first, then done only with control held within its tolerance of
the goal); a step's ``clearance`` is the wall clearance route_to's plans keep, and its ``basis`` "prior" seeds the
field's basis from the step's prior -- no calibration probe -- its first move judged by the session. A seed the first
move disagrees with raises a HarnessError carrying ``prior_basis``, which :meth:`_Drive.run_step` turns into the step
row's V13 (the driver's instrument) whatever the step's own keys. :func:`step_of` reads every key strict; a table with
none of them -- every one frozen before O7's -- is driven exactly as before.

THE ARRIVAL'S HEIGHT AND THE KNIGHT WAIT (opt-in; research/o8_design.md 1.2 S20-S21): a walk's ``at_y`` proves its
arrival on its LEVEL -- his published y within the band at the arrival's sample, else the walk failed (a goal whose XZ
stacks three levels says nothing alone); its ``wait_flag`` then waits there, pressing nothing, for a watched story bit
(:meth:`_Drive.wait_flag`: run out only once both the wall's and the game's clocks ran its timeout; the game's V8 only
on a bit the agent published, else the driver's V13). :func:`step_of` reads both strict and adds nothing: a table with
neither -- every one frozen before O8's -- is driven exactly as before.
"""
from __future__ import annotations

import itertools
import json
import math
import re
import time

import segment_trace as ST
from segment_trace import place

#: The step kinds of a beat-table cell (research/o2_design.md 2.3), each run by its executor in :class:`_Drive`. S17
#: (research/o7_design.md 1.2): ``walk`` -- a step whose evidence is an ARRIVAL, opt-in (no table before O7's has one).
STEP_KINDS = ("cross", "trigger", "confirm", "wait_sc", "leave_now", "walk")
#: What each kind's executor reads that no default gives (:func:`step_of` refuses a step without it): every walk its
#: ``goal``; a crossing its exit (``target``) and the place it leads to (``to``); a Confirm its region and the answer it
#: waits for; a wait its scenario and how long. A trigger needs a ``target`` or an ``until`` (checked apart).
STEP_NEEDS = {"cross": ("goal", "target", "to"), "leave_now": ("goal", "target", "to"), "trigger": ("goal",),
              "confirm": ("goal", "target", "expect"), "wait_sc": ("goal", "sc", "wait_s"), "walk": ("goal",)}
#: S17: keys a walk step may not carry (in the RAW step: steps_default fills some for every kind) -- its evidence is
#: its goal, reached with control held; a door, an until, a landing or an answer is another kind's.
WALK_REFUSES = ("target", "until", "to", "expect", "sc", "wait_s", "then")
#: S18/S19 (research/o7_design.md 1.2): the opt-in keys every kind may carry, each checked strict -- ``clearance`` (a
#: positive number: the planner's wall clearance for the step's walks) and ``basis`` (one of these: ``"prior"`` seeds the
#: field's basis from the step's prior, no probe pressed, its first move judged).
BASIS_KINDS = ("prior",)
#: S20/S21 (research/o8_design.md 1.2): the keys only a walk may carry -- its arrival's height band and THE KNIGHT WAIT.
WALK_ONLY = ("at_y", "wait_flag")
#: S21: a wait_flag's keys, exactly these.
WAIT_FLAG_KEYS = ("flag", "value", "timeout_s")
#: S21: the highest gEventGlobal bit (Byte[2048]).
MAX_FLAG_BIT = 16383
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
    2.6; V17, V18 and V19: research/o4_design.md 2.6 -- V17 the fight's input not proven the frozen play, the
    driver's; V18 the game SHOWN deviating from a proven play, a finding; V19 a real donor field entered on F), its
    beat-table cell and its attribution; each is None unless given, so O1's ``raise RouteVoid(msg)`` still works and its
    runs record no class."""

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
def cell(pred: dict, donor: int, sc: int, visit: int | None = None) -> dict | None:
    """The table's cell for ``(donor place, published SC)``, or None (2.1). S13 (research/o5_design.md 1.2), opt-in: a
    cell carrying ``visit`` -- the 1-based position of a visit in ``visits`` -- matches only that visit (``visit`` given
    and equal to it); a cell without it matches every visit, as every table before O5's."""
    return next((c for c in pred.get("table") or ()
                 if c["donor"] == donor and c["sc"] == sc and ("visit" not in c or c["visit"] == visit)), None)


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
    names missing; a trigger with neither ``target`` nor ``until``; a trigger's ``to`` (S14, research/o6_design.md
    1.2: the place its door leads to) that is no int; an ``until`` that is empty or has a key :func:`until_ok` does not
    know; an ``expect`` not in :data:`EXPECTS`; a ``goal`` that is no point; and a ``target`` or ``avoid`` key that is
    no registered region. S17-S19 (research/o7_design.md 1.2), each opt-in: a ``walk`` whose RAW step carries any of
    :data:`WALK_REFUSES`; a ``clearance`` that is no positive number (a bool is no number); a ``basis`` not in
    :data:`BASIS_KINDS`. S20, S21 and S23 (research/o8_design.md 1.2), each opt-in: a :data:`WALK_ONLY` key on a step
    that is no walk; an ``at_y`` that is not two numbers, the first under the second; a ``wait_flag`` without ``at_y``
    (the wait begins at a proven point) or that is not exactly :data:`WAIT_FLAG_KEYS` -- ``flag`` an int in
    0..:data:`MAX_FLAG_BIT`, ``value`` 0 or 1, ``timeout_s`` a positive number; an ``unstick`` that is no bool. Each is
    a check only: it raises or passes, and never adds, drops or normalises a key (the claim critic's #5). A table
    carrying none of these keys -- every one frozen before O8's -- merges exactly as before."""
    base = pred.get("steps_default") or {}
    out = {**base, **raw}
    out["climb"] = {**(base.get("climb") or {}), **(raw.get("climb") or {})}
    kind = out.get("kind")
    if kind not in STEP_KINDS:
        raise ValueError(f"step {raw!r}: kind is not one of {STEP_KINDS}")
    if kind == "walk":
        carried = [k for k in WALK_REFUSES if k in raw]
        if carried:
            raise ValueError(f"step {raw!r}: a walk carries no {carried} -- its evidence is its goal, reached with "
                             f"control held (a door, an until, a landing or an answer is another kind's)")
    clearance = out.get("clearance")
    if clearance is not None and (not isinstance(clearance, (int, float)) or isinstance(clearance, bool)
                                  or not clearance > 0):
        raise ValueError(f"step {raw!r}: clearance is a positive number of world units (a bool is no number), not "
                         f"{clearance!r}")
    if out.get("basis") is not None and out["basis"] not in BASIS_KINDS:
        raise ValueError(f"step {raw!r}: basis is one of {BASIS_KINDS}, not {out['basis']!r}")
    walk_only = [k for k in WALK_ONLY if out.get(k) is not None]          # S20/S21 (opt-in): a walk's keys alone
    if walk_only and kind != "walk":
        raise ValueError(f"step {raw!r}: {walk_only} only a walk carries -- its arrival's height (at_y) and the "
                         f"knight wait (wait_flag), never a {kind}'s")
    band = out.get("at_y")
    if band is not None and not (isinstance(band, (list, tuple)) and len(band) == 2
                                 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in band)
                                 and band[0] < band[1]):
        raise ValueError(f"step {raw!r}: at_y is [lo, hi], two numbers of his published y (a bool is no number), lo "
                         f"under hi -- not {band!r}")
    wf = out.get("wait_flag")
    if wf is not None:
        if band is None:
            raise ValueError(f"step {raw!r}: a wait_flag needs at_y -- the wait begins at a proven point")
        if not isinstance(wf, dict) or set(wf) != set(WAIT_FLAG_KEYS):
            raise ValueError(f"step {raw!r}: wait_flag holds exactly {list(WAIT_FLAG_KEYS)}, not "
                             f"{sorted(wf) if isinstance(wf, dict) else wf!r}")
        if not _is_int(wf["flag"]) or not 0 <= wf["flag"] <= MAX_FLAG_BIT:
            raise ValueError(f"step {raw!r}: wait_flag's flag is a gEventGlobal bit, an int in 0..{MAX_FLAG_BIT} (a "
                             f"bool is no int), not {wf['flag']!r}")
        if not _is_int(wf["value"]) or wf["value"] not in (0, 1):
            raise ValueError(f"step {raw!r}: wait_flag's value is 0 or 1, not {wf['value']!r}")
        if not _is_pos(wf["timeout_s"]):
            raise ValueError(f"step {raw!r}: wait_flag's timeout_s is a positive number of seconds, not "
                             f"{wf['timeout_s']!r}")
    if out.get("unstick") is not None and not isinstance(out["unstick"], bool):     # S23 (opt-in): route_to's own
        raise ValueError(f"step {raw!r}: unstick is a bool (route_to's own), not {out['unstick']!r}")
    if out.get("target") is not None and out.get("until") is not None:
        raise ValueError(f"step {raw!r}: target and until are exclusive")
    missing = [k for k in STEP_NEEDS[kind] if out.get(k) is None]
    if missing:
        raise ValueError(f"step {raw!r}: a {kind} step needs {missing}")
    if kind == "trigger" and out.get("target") is None and out.get("until") is None:
        raise ValueError(f"step {raw!r}: a trigger step needs a target or an until")
    if kind == "trigger" and out.get("to") is not None and not _is_int(out["to"]):
        raise ValueError(f"step {raw!r}: a trigger's to is a place, an int (a bool is no int)")
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


def trigger_to_verdict(lost, fid: int, ok: bool, landed, to_place, to: int) -> tuple:
    """S14's verdict, pure (research/o6_design.md 1.2; decision 3): ``lost`` the walk's loss sample (route_to's probe,
    or the trigger wait's read) with its ``field``; ``fid`` the field the walk ran in; ``ok`` whether ``lost`` satisfies
    the step's evidence (``until``, or standing in its ``target``); ``landed`` the landing -- route_to's own record, or
    the switch waited out once the published id left -- None while he is still in ``fid``; ``to_place`` its frozen
    place. Returns ("done", landed) -- the evidence held where control went IN THIS FIELD, and the run either has not
    left yet or left for ``to`` (path A: None; path B: the next field); ("left", landed) -- the evidence held but the
    landing is ANOTHER place: by the step's soundness proof (O6-GOALS (d') and (e)) the loss was the door's own, whose
    only live ``Field()`` leads to ``to``, so the landing is its script's, the fork's or the engine's, never the walk's
    -- rule 2's verdict for that field, the GAME's (rev. 2, 11.5 #1); ("v13", why) -- the loss was never read in this
    field (``lost`` None, or ``lost["field"]`` another field: a read gap across the door's fade -- the instrument's, the
    evidence unjudgeable); ("v11", why) -- the walk left the field from an in-field loss WITHOUT the evidence (today's
    ``strayed``): the driver's, the ONLY driver V11 under ``to``; ("judge", None) -- an in-field loss without the
    evidence and no landing: today's last lines decide (door_loss, interrupted)."""
    if lost is None or lost.get("field") != fid:
        where = "never read" if lost is None else f"read only in {lost.get('field')}"
        return "v13", (f"the loss of control went unseen in {fid} ({where}"
                       + ("" if landed is None else f"; the run in {landed}")
                       + "): a read gap across the door's fade -- the instrument's, its evidence unjudgeable")
    if ok:
        return ("done" if landed is None or to_place == to else "left"), landed
    if landed is not None:
        return "v11", (f"the trigger's walk left {fid} without the step's evidence: control went at "
                       f"({lost.get('x')}, {lost.get('z')})")
    return "judge", None


# ======================================================================== S16: the name on the page (pure)
#: A naming registration's keys (research/o6_design.md 1.2 S16): ``donor`` and ``sc`` (ints, required: the place and the
#: published SC the screen may open at), ``beat`` (a non-empty str or None: set when it is accepted), ``why`` (a str)
#: and, opt-in, ``on_page`` (the page witness, :data:`ON_PAGE_KEYS`). O2's ``{"donor", "sc", "beat"}`` is one.
NAMING_KEYS = ("donor", "sc", "beat", "on_page", "why")
#: The page witness's keys: ``tag`` (the text tag a page renders the name with, ``"[STNR]"``), ``beat`` (set by an "ok"
#: row), ``windows`` (the frozen entries, each exactly :data:`WINDOW_KEYS`) and ``why`` (optional).
ON_PAGE_KEYS = ("tag", "beat", "windows", "why")
#: A frozen window's keys: ``mes``; ``raw_holds`` (what its raw holds: the source line, the tag in it); ``line`` (the
#: line of its rendered text the name lands on); ``text`` (that line as the default name renders it: no tag, no "[").
WINDOW_KEYS = ("mes", "raw_holds", "line", "text")
#: A text tag as the registration names one: ``[STNR]``.
_NAME_TAG = re.compile(r"\[[A-Z0-9]+\]")


def naming_of(pred: dict) -> list:
    """``pred["naming"]`` checked STRICT before anything is driven (research/o6_design.md 1.2 S16): a list of
    registrations (none: ``[]``), each a dict of :data:`NAMING_KEYS` -- ``donor`` and ``sc`` ints (a bool is no int),
    ``beat`` a non-empty str or None, ``why`` a str -- and, opt-in, ``on_page``: exactly keys of :data:`ON_PAGE_KEYS`
    (``why`` optional) -- ``tag`` a text tag (``"[STNR]"``), ``beat`` a non-empty str, ``windows`` a non-empty list,
    each exactly :data:`WINDOW_KEYS` -- ``mes`` an int, ``raw_holds`` a non-empty str holding ``tag``, ``line`` an int
    >= 0, ``text`` a non-empty str holding no ``tag`` and no ``[``. ValueError naming the first fault. O2's ``{"donor",
    "sc", "beat"}`` passes unchanged. Returns the registrations."""
    regs = pred.get("naming")
    if regs is None:
        return []
    if not isinstance(regs, list):
        raise ValueError(f"naming: a list of registrations, not {regs!r}")
    for i, r in enumerate(regs):
        at = f"naming[{i}]"
        if not isinstance(r, dict):
            raise ValueError(f"{at}: a registration is a dict, not {r!r}")
        unknown = sorted(set(r) - set(NAMING_KEYS))
        if unknown:
            raise ValueError(f"{at}: no key {unknown} (a registration takes {list(NAMING_KEYS)})")
        for k in ("donor", "sc"):
            if not _is_int(r.get(k)):
                raise ValueError(f"{at}: {k} is an int (a bool is no int), not {r.get(k)!r}")
        if r.get("beat") is not None and not (isinstance(r["beat"], str) and r["beat"]):
            raise ValueError(f"{at}: beat is a non-empty str or None, not {r['beat']!r}")
        if "why" in r and not isinstance(r["why"], str):
            raise ValueError(f"{at}: why is a str, not {r['why']!r}")
        if "on_page" in r:
            _on_page_of(r["on_page"], f"{at}.on_page")
    return regs


def _on_page_of(page, at: str) -> None:
    """A registration's ``on_page`` checked STRICT (:func:`naming_of`)."""
    if not isinstance(page, dict):
        raise ValueError(f"{at}: the page witness is a dict, not {page!r}")
    bad = sorted(set(page) - set(ON_PAGE_KEYS)) + sorted(k for k in ON_PAGE_KEYS if k != "why" and k not in page)
    if bad:
        raise ValueError(f"{at}: exactly keys of {list(ON_PAGE_KEYS)} (why optional), not {sorted(page)}")
    tag = page["tag"]
    if not (isinstance(tag, str) and _NAME_TAG.fullmatch(tag)):
        raise ValueError(f"{at}: tag is a text tag such as '[STNR]', not {tag!r}")
    if not (isinstance(page["beat"], str) and page["beat"]):
        raise ValueError(f"{at}: beat is a non-empty str, not {page['beat']!r}")
    if "why" in page and not isinstance(page["why"], str):
        raise ValueError(f"{at}: why is a str, not {page['why']!r}")
    wins = page["windows"]
    if not isinstance(wins, list) or not wins:
        raise ValueError(f"{at}: windows is a non-empty list of frozen windows, not {wins!r}")
    for n, w in enumerate(wins):
        where = f"{at}.windows[{n}]"
        if not isinstance(w, dict) or set(w) != set(WINDOW_KEYS):
            got = sorted(w) if isinstance(w, dict) else w
            raise ValueError(f"{where}: exactly keys {list(WINDOW_KEYS)}, not {got!r}")
        if not _is_int(w["mes"]):
            raise ValueError(f"{where}: mes is an int, not {w['mes']!r}")
        if not (isinstance(w["raw_holds"], str) and w["raw_holds"] and tag in w["raw_holds"]):
            raise ValueError(f"{where}: raw_holds is the source the raw holds, the tag {tag} in it, not "
                             f"{w['raw_holds']!r}")
        if not (_is_int(w["line"]) and w["line"] >= 0):
            raise ValueError(f"{where}: line is the rendered text's line index, an int >= 0, not {w['line']!r}")
        if not (isinstance(w["text"], str) and w["text"] and tag not in w["text"] and "[" not in w["text"]):
            raise ValueError(f"{where}: text is the line as the default name renders it -- non-empty, no tag, no '[' "
                             f"-- not {w['text']!r}")


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
    and each object list as ``[uid, kind]`` pairs. S18/S19 (research/o7_design.md 1.2): ``clearance``, ``basis`` and
    ``basis_check`` too -- each in a record only when its walk was given one (or, ``basis_check``, judged a seeded
    basis's first move), so every O1-O6 row is as it was."""
    if r is None:
        return None
    keep = ("from", "landed", "changed_to", "reached", "inside", "travelled", "during", "replans", "waits", "cleared",
            "pushes", "pushed", "blocked", "frozen", "boxed", "boxed_by", "npcs", "npc_replans", "npc_waits",
            "box_waits", "box_cleared", "held_by", "handoff", "lost", "blockers", "clearance", "basis", "basis_check")
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


# ======================================================================== S7: the Chanbara policy (opt-in, pure)
#: THE BUTTON MAP (research/o4_design.md 2.4.4), the one this policy takes: each prompt's [DBTN] to the press whose
#: Control sets the bit 64 e3 t1 polls for it (ip34-363) under cfg.control 0 (0.2 #6): LEFT 0x80, RIGHT 0x20, UP 0x10,
#: DOWN 0x40 (the directions, set straight by ProcessInput), TRIANGLE ``menu`` (Menu | Triangle 0x1000), CROSS
#: ``confirm`` (Confirm | Cross 0x4000), CIRCLE ``cancel`` (Cancel | Circle 0x2000), SQUARE ``special`` (Special |
#: Square 0x8000). :func:`chanbara_of` refuses any other.
DBTN_CONTROL = {"LEFT": "left", "RIGHT": "right", "UP": "up", "DOWN": "down", "TRIANGLE": "menu", "CROSS": "confirm",
                "CIRCLE": "cancel", "SQUARE": "special"}
#: Why another spelling is no map (:func:`chanbara_of` names it): HarnessAgent.ParseControl's aliases (HarnessAgent.cs:
#: 1430-1449) -- ``circle``, ``x``, ``a`` and ``ok`` are Control.Confirm, the CROSS bit; ``start`` / ``pause`` is
#: Start, which 64 e3 t1 ip412 reads as a LEVEL; the rest are one Control's second spelling.
DBTN_ALIAS_WHY = {
    "circle": "Control.Confirm -- the Cross bit 0x4000 (HarnessAgent.cs:1434), never Circle's 0x2000",
    "x": "Control.Confirm -- the Cross bit (HarnessAgent.cs:1434)", "a": "Control.Confirm -- the Cross bit",
    "ok": "Control.Confirm -- the Cross bit",
    "start": "Start (Control.Pause), which 64 e3 t1 ip412 reads as a LEVEL (B_KEY(8)): held, a miss every poll",
    "pause": "Start (Control.Pause), which 64 e3 t1 ip412 reads as a LEVEL (B_KEY(8)): held, a miss every poll",
    "b": "Control.Cancel's second spelling (one spelling per Control: cancel)",
    "back": "Control.Cancel's second spelling (one spelling per Control: cancel)",
    "triangle": "Control.Menu's second spelling (one spelling per Control: menu)",
    "y": "Control.Menu's second spelling (one spelling per Control: menu)",
    "square": "Control.Special's second spelling (one spelling per Control: special)",
    "north": "an alias of up (one spelling per Control)", "south": "an alias of down (one spelling per Control)",
    "west": "an alias of left (one spelling per Control)", "east": "an alias of right (one spelling per Control)"}
#: The policy's keys (4.10), strict: ``pace`` and ``stop_after`` optional; ``raw_floor`` the fast policy's, ``pace``
#: the paced one's (2.4.10).
CHANBARA_KEYS = ("policy", "donor", "sc", "buttons", "press_frames", "prompts", "j_cap", "raw_floor", "gone_ticks",
                 "zone_start", "zone_end", "first_prompt_s", "zone_stall_s", "page_once_ticks", "quiet", "quiet_cap_s",
                 "score_page", "gil_page", "encore_match", "poll_s", "state_every", "input_every_s", "ring_every_s",
                 "why", "pace", "stop_after")
CHANBARA_POLICIES = ("fast", "paced")
PACE_KEYS = ("target_ticks", "lead_ticks", "raw_band")
#: A prompt's life in field ticks: TimeLeft 50 (e20 t1 ip736), a hit at the j-th poll credits 50 - j (e3 t1 ip487-498).
PROMPT_TICKS = 50
#: A window is listed from its arm to its timeout at the 50th poll, then its close tween (0.09 s and a frame, ~4 ticks):
#: a sample more than PROMPT_TICKS + this many SURE ticks after an instance's seen frame cannot list that instance's
#: window -- its DBTN listed there is a successor's (prompts never repeat back to back, e20 ip681: a read gap hid the
#: instance between).
LIFE_MARGIN_TICKS = 5
#: The raw score's divisor (64 e4 t1 ip208: (Int16[30] + Int16[32]) / 29).
RAW_DIVISOR = 29
#: Every [DBTN=..] tag of a line, whatever it names.
_DBTN_TAG = re.compile(r"\[DBTN=([^\]]*)\]")


def _is_text(v) -> bool:
    return isinstance(v, str) and bool(v)


def chanbara_of(pred: dict) -> dict | None:
    """THE CHANBARA POLICY (``pred["chanbara"]``; research/o4_design.md 2.4, 4.10), checked STRICT before anything is
    driven, as :func:`movies_of` checks the movie-skip policy -- or None: no ``chanbara``, and nothing below reads it.

    ValueError, each naming its cause, on: a policy that is no dict; an unknown key or a missing one; a ``policy`` not
    "fast" or "paced"; under "fast" a ``pace`` or no ``raw_floor`` (an int 79-126) and a ``j_cap`` outside 1-16 (a
    hit's gap is >= ~8 ticks, 0.2 #2); under "paced" no ``pace``, a ``raw_floor``, or a ``j_cap`` outside 1-40;
    ``buttons`` other than EXACTLY :data:`DBTN_CONTROL` (an alias is named with its cause: ``circle`` is
    Control.Confirm); ``donor``, ``sc``, ``prompts`` (>= 1), ``page_once_ticks`` (>= 1) not ints, ``press_frames`` not an
    int 1-4, ``gone_ticks`` not an int 5-20, ``stop_after`` not an int 1-48; the ``_s`` keys not positive numbers,
    ``input_every_s`` above 0.1 or ``ring_every_s`` above 5 (the ring keeps ~10 s); ``score_page``, ``gil_page``,
    ``encore_match``, ``why`` not non-empty strings; ``zone_start`` not exactly ``{"match": text, "dbtns": 8}``;
    ``zone_end`` or ``quiet`` not non-empty lists of non-empty strings; ``state_every`` neither None nor 1; a ``pace``
    not exactly ``{"target_ticks" 1-50, "lead_ticks" 0 .. target - 1, "raw_band" [lo, hi] ints, 1 <= lo <= hi}``. A
    bool is never a number. Returns a copy."""
    raw = pred.get("chanbara")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"chanbara {raw!r}: the policy is a dict of {CHANBARA_KEYS}")
    unknown = sorted(set(raw) - set(CHANBARA_KEYS))
    missing = [k for k in CHANBARA_KEYS if k not in ("pace", "stop_after", "raw_floor") and k not in raw]
    if unknown or missing:
        raise ValueError(f"chanbara: " + "; ".join(([f"unknown key(s) {unknown}"] if unknown else [])
                                                    + ([f"missing {missing}"] if missing else []))
                         + f" -- the policy's keys are {CHANBARA_KEYS} (pace, stop_after, raw_floor by the policy)")
    policy = raw["policy"]
    if policy not in CHANBARA_POLICIES:
        raise ValueError(f"chanbara: policy {policy!r} is not one of {CHANBARA_POLICIES}")
    if policy == "fast":
        if "pace" in raw:
            raise ValueError("chanbara: a pace under the fast policy -- the pace is R-GATE's (policy paced, 2.4.10)")
        if not _is_int(raw.get("raw_floor")) or not 79 <= raw["raw_floor"] <= 126:
            raise ValueError(f"chanbara: the fast policy's raw_floor is an int 79-126, not {raw.get('raw_floor')!r}")
        cap = 16
    else:
        if "raw_floor" in raw:
            raise ValueError("chanbara: a raw_floor under the paced policy -- its band is pace.raw_band (2.4.10)")
        if "pace" not in raw:
            raise ValueError("chanbara: the paced policy needs a pace (target_ticks, lead_ticks, raw_band)")
        cap = 40
    btn = raw["buttons"]
    if not isinstance(btn, dict) or btn != DBTN_CONTROL:
        why = []
        if isinstance(btn, dict):
            for d, name in btn.items():
                want = DBTN_CONTROL.get(d)
                if want is None:
                    why.append(f"{d!r} is no prompt button")
                elif name != want:
                    cause = DBTN_ALIAS_WHY.get(str(name).lower())
                    why.append(f"{d} -> {name!r}" + (f" is {cause}" if cause else f", where the map is {want!r}"))
            why += [f"{d} is missing" for d in DBTN_CONTROL if d not in btn]
        raise ValueError(f"chanbara: buttons must be exactly {DBTN_CONTROL}"
                         + (f": {'; '.join(why)}" if why else f", not {btn!r}"))
    bad = [k for k in ("donor", "sc") if not _is_int(raw[k])]
    bad += [k for k in ("prompts", "page_once_ticks") if not _is_int(raw[k]) or raw[k] < 1]
    if not _is_int(raw["press_frames"]) or not 1 <= raw["press_frames"] <= 4:
        bad.append("press_frames (an int 1-4: a tap)")
    if not _is_int(raw["gone_ticks"]) or not 5 <= raw["gone_ticks"] <= 20:
        bad.append("gone_ticks (an int 5-20)")
    if not _is_int(raw["j_cap"]) or not 1 <= raw["j_cap"] <= cap:
        bad.append(f"j_cap (an int 1-{cap} under the {policy} policy)")
    if "stop_after" in raw and (not _is_int(raw["stop_after"]) or not 1 <= raw["stop_after"] <= 48):
        bad.append("stop_after (an int 1-48)")
    bad += [k for k in ("first_prompt_s", "zone_stall_s", "quiet_cap_s", "poll_s", "input_every_s", "ring_every_s")
            if not _is_pos(raw[k])]
    if _is_pos(raw["input_every_s"]) and raw["input_every_s"] > 0.1:
        bad.append("input_every_s (at most 0.1)")
    if _is_pos(raw["ring_every_s"]) and raw["ring_every_s"] > 5:
        bad.append("ring_every_s (at most 5: the ring keeps ~10 s)")
    bad += [k for k in ("score_page", "gil_page", "encore_match", "why") if not _is_text(raw[k])]
    zs = raw["zone_start"]
    if not isinstance(zs, dict) or set(zs) != {"match", "dbtns"} or not _is_text(zs.get("match")) \
            or not _is_int(zs.get("dbtns")) or zs["dbtns"] != 8:
        bad.append("zone_start (exactly {match: text, dbtns: 8})")
    bad += [k for k in ("zone_end", "quiet") if not isinstance(raw[k], list) or not raw[k]
            or not all(_is_text(t) for t in raw[k])]
    if raw["state_every"] not in (None, 1) or isinstance(raw["state_every"], bool):
        bad.append("state_every (None or 1)")
    if policy == "paced":
        pace = raw["pace"]
        ok = isinstance(pace, dict) and set(pace) == set(PACE_KEYS) and _is_int(pace.get("target_ticks")) \
            and 1 <= pace["target_ticks"] <= PROMPT_TICKS and _is_int(pace.get("lead_ticks")) \
            and 0 <= pace["lead_ticks"] < pace["target_ticks"]
        band = pace.get("raw_band") if isinstance(pace, dict) else None
        ok = ok and isinstance(band, (list, tuple)) and len(band) == 2 and all(_is_int(b) for b in band) \
            and 1 <= band[0] <= band[1]
        if not ok:
            bad.append("pace (exactly {target_ticks 1-50, lead_ticks 0 .. target - 1, raw_band [lo, hi]})")
    if bad:
        raise ValueError(f"chanbara: {bad} of the wrong type or out of range")
    return json.loads(json.dumps(raw))


def prompt_dbtn(line) -> str | None:
    """A published ``phrase_raw`` line that is a PROMPT (research/o4_design.md 2.4.1), pure: it holds EXACTLY ONE
    ``[DBTN=X]`` with X one of :data:`DBTN_CONTROL`'s eight, and holds ``Press`` and ``[TIME=-1]`` -> X; else None.
    Rendered ``texts`` are never read for it: the glyph renders to nothing, so all eight read "Press  !". 111 (eight
    tags) is none, nor is 150's window 55 (two tags, no "Press")."""
    s = str(line or "")
    tags = _DBTN_TAG.findall(s)
    if len(tags) != 1 or tags[0] not in DBTN_CONTROL or "Press" not in s or "[TIME=-1]" not in s:
        return None
    return tags[0]


def is_zone_start(lines, pol: dict) -> bool:
    """Whether a published ``phrase_raw`` line is the ZONE START (111): it holds ``zone_start.match`` and exactly
    ``zone_start.dbtns`` [DBTN] tags."""
    zs = pol["zone_start"]
    return any(zs["match"] in str(ln or "") and len(_DBTN_TAG.findall(str(ln or ""))) == zs["dbtns"]
               for ln in lines or ())


def is_zone_end(texts, pol: dict) -> bool:
    """Whether a published rendered text holds one of ``zone_end`` (107, 108)."""
    return any(e in str(t or "") for t in texts or () for e in pol["zone_end"])


def rate_of(d: dict):
    """A :class:`harness.tickrate.Rate` rebuilt from a row's ``rate`` (its ``as_dict()``)."""
    from harness.tickrate import Rate
    return Rate(fps=float(d["fps"]), fps_lo=float(d["fps_lo"]), fps_hi=float(d["fps_hi"]),
                tick_hz=float(d["tick_hz"]), source=d.get("source", "default"), samples=int(d.get("samples", 0)),
                frame=int(d.get("frame", -1)), stale=bool(d.get("stale", False)))


def j_bounds(row: dict) -> tuple:
    """``(j_lo, j_hi)`` of a prompt row (research/o4_design.md 2.4.7), pure; ``(None, None)`` without its down, prev
    and seen frames or its rate. j is the ticks from the arm tick S to the tick the press's edge lands on. The edge
    lands on the first tick of the frames >= ``down_frame`` in either publication order (the input is frame-scheduled
    and read before a frame's ticks, FPSManager.cs:77-139); S lies in the ticks of frames [``prev_frame``,
    ``seen_frame`` - 1] (agent first) or [``prev_frame`` + 1, ``seen_frame``] (agent last). So ``j_hi =
    ticks_most(down - prev) + 1 + ceil(excess)`` (the jitter tick TAIL_TICKS carries, and a hitch's caught-up ticks) and
    ``j_lo = max(1, ticks_sure(down - seen - 1))`` -- both sound under either order."""
    down, prev, seen, rate = (row.get(k) for k in ("down_frame", "prev_frame", "seen_frame", "rate"))
    if down is None or prev is None or seen is None or not rate:
        return None, None
    r = rate_of(rate)
    hi = r.ticks_most(max(0, down - prev)) + 1 + math.ceil(float(row.get("excess") or 0.0))
    lo = max(1, r.ticks_sure(max(0, down - seen - 1)))
    return lo, hi


def row_bounds(row: dict) -> tuple:
    """``(j_lo, j_hi)`` of one prompt row as the judge and :func:`raw_bounds` read it, pure: its recorded bounds when
    both are recorded, else :func:`j_bounds` of its frames -- ``(None, None)`` when neither gives them."""
    if row.get("j_lo") is not None and row.get("j_hi") is not None:
        return row["j_lo"], row["j_hi"]
    return j_bounds(row)


def _unbounded_why(row: dict) -> str:
    """What a row without j bounds lacks: its prev, seen or down frame, or its rate."""
    gone = [what for what, v in (("prev frame", row.get("prev_frame")), ("seen frame", row.get("seen_frame")),
                                 ("down frame", row.get("down_frame")), ("rate", row.get("rate") or None)) if v is None]
    return ", ".join(f"no {x}" for x in gone) or "no bounds"


def raw_bounds(rows: list) -> tuple:
    """``(raw_lo, raw_hi)`` over a fight's prompt rows (2.4.7), pure: n hits credit ``sum(50 - j)`` to Int16[30], the
    phantom pass the last one's again, and ``0 + 1 + ... + n`` to Int16[32] (1225 at 49) -- each j clamped to 1..50;
    raw_lo from every ``j_hi``, raw_hi from every ``j_lo`` (:func:`row_bounds`: a row's recorded bounds, else
    :func:`j_bounds` of its frames). ``(None, None)`` for no rows or a row without bounds."""
    los, his = [], []
    for r in rows:
        lo, hi = row_bounds(r)
        if lo is None or hi is None:
            return None, None
        los.append(min(PROMPT_TICKS, max(1, lo)))
        his.append(min(PROMPT_TICKS, max(1, hi)))
    if not rows:
        return None, None
    i32 = len(rows) * (len(rows) + 1) // 2

    def raw(js):
        return (sum(PROMPT_TICKS - j for j in js) + (PROMPT_TICKS - js[-1]) + i32) // RAW_DIVISOR
    return raw(his), raw(los)


def prompt_evidence(row: dict, samples: list, gone_ticks: int, *, until: int | None = None) -> dict:
    """What the MERGED stream PROVES about one instance's press (research/o4_design.md 2.4.6), pure, over the samples
    after its ``seen_frame`` and before ``until`` (the next instance of the same button's seen frame, if any) -- each
    sample's ``dbtns`` the prompts it lists. ``mark = down_frame + frames_for_ticks(gone_ticks)`` at the row's rate:
    ``"before"`` -- a sample at or before ``down_frame`` already lacks the window: it left before the press could land;
    ``"lingered"`` -- a sample lists it at or past ``mark``: the game read no key; ``"closed"`` -- a sample lists it at
    or after ``down_frame`` and the first sample without it after that lies at or before ``mark``: the game read A key
    (e3 closes the window on a hit and a wrong key alike; only the slide or the score tells which); else
    ``"unobserved"`` -- a read gap straddles the down frame or the mark. ``{"evidence", "mark", "last_listed_frame",
    "gone_frame", "gone_kind"}``: the last sample listing the window, the first after it without ("dbtn" when that one
    lists another prompt, else "none"); ``evidence`` None without a down frame (no accepted event) or a rate. A sample
    more than PROMPT_TICKS + :data:`LIFE_MARGIN_TICKS` sure ticks after ``seen_frame`` never lists the window: its DBTN
    there is a successor's."""
    dbtn, seen, down = row["dbtn"], row["seen_frame"], row.get("down_frame")
    life = rate_of(row["rate"]) if row.get("rate") else None

    def lists(s: dict) -> bool:
        return dbtn in s["dbtns"] and (life is None or life.ticks_sure(max(0, s["frame"] - seen))
                                       <= PROMPT_TICKS + LIFE_MARGIN_TICKS)
    after = [s for s in samples if s["frame"] > seen and (until is None or s["frame"] < until)]
    listing = [s["frame"] for s in after if lists(s)]
    last = max(listing) if listing else seen
    gone = next((s for s in after if s["frame"] > last and not lists(s)), None)
    out = {"evidence": None, "mark": None, "last_listed_frame": last,
           "gone_frame": None if gone is None else gone["frame"],
           "gone_kind": None if gone is None else ("dbtn" if gone["dbtns"] else "none")}
    if down is None or not row.get("rate"):
        return out
    mark = down + rate_of(row["rate"]).frames_for_ticks(gone_ticks)
    out["mark"] = mark
    if any(s["frame"] <= down and not lists(s) for s in after):
        out["evidence"] = "before"
    elif any(s["frame"] >= mark and lists(s) for s in after):
        out["evidence"] = "lingered"
    else:
        at = [s["frame"] for s in after if s["frame"] >= down and lists(s)]
        first = next((s["frame"] for s in after if at and s["frame"] > max(at) and not lists(s)), None)
        out["evidence"] = "closed" if first is not None and first <= mark else "unobserved"
    return out


#: The slide a LEFT / RIGHT HIT makes both bodies take (64 e20 t1 ip918-1211, e13 t11 ip1617-1916): -300 / +300.
LR_WANT = {"LEFT": -300.0, "RIGHT": 300.0}
#: A slide's bracketing samples must lie this many SURE ticks after the previous instance's ``seen_frame`` (2.4.6): the
#: earlier slide is done after its arm + 6, and a jitter tick.
SLIDE_CLEAR_TICKS = 7


def _slide_verdict(want: float, wants: list, dxp, dxb) -> dict:
    """A measured slide's reading: both bodies at ``want`` (within 1 unit) -> ok; both at ``want`` less some of
    ``wants`` (whole L/R slides left out: the game read those keys as misses) -> not ok, ``left_out`` those instances;
    anything else -> not ok, ``left_out`` None (the samples are not what 2.4.6 needs: the instrument's)."""
    cands = [(want, None)]
    for k in range(1, len(wants) + 1):
        for combo in itertools.combinations(wants, k):
            cands.append((want - sum(w for _n, w in combo), sorted(n for n, _w in combo)))
    for value, left in cands:
        if abs(dxp - value) <= 1.0 and abs(dxb - value) <= 1.0:
            return {"ok": True, "left_out": None} if left is None else {"ok": False, "left_out": left}
    return {"ok": False, "left_out": None}


def measure_slides(rows: list, end_sample: dict | None, prompts: int) -> dict:
    """THE LEFT/RIGHT SLIDE WITNESS (research/o4_design.md 2.4.6), pure: ``{n: slide}`` for every LEFT / RIGHT
    instance. A hit on prompt n slides Blank and Zidane in pass n's reaction, the one that arms prompt n + 1 at S', done
    after S'+6 (0.3 #3); BASE is instance n+1's ``prev`` sample (``x_prev``: its state precedes S'), END instance n+2's
    (it precedes prompt n+2's arm, where prompt n+1's own slide would begin) -- each counted only when it lies
    :data:`SLIDE_CLEAR_TICKS` sure ticks after the previous instance's ``seen_frame``. The last two prompts slide in the
    arms of the last and of the phantom pass, which publishes nothing (0.3 #9): with the zone end's first sample
    (``end_sample``: ``frame``, ``x_player``, ``x_blank``) they are measured JOINTLY from the last instance's ``prev``
    sample to it, ``want`` the sum of their L/R wants, the one result on both rows -- "unmeasured" when they are L/R
    with opposite wants. A slide is ``{"want", "base", "end", "dx_player", "dx_blank", "ok": True | False |
    "unmeasured", "left_out"}`` (and ``joint`` for the tail's)."""
    by_n = {r["n"]: r for r in rows}
    out: dict = {}

    def clear(later, earlier) -> bool:
        if later is None or earlier is None or later.get("prev_frame") is None or not later.get("rate"):
            return False
        return rate_of(later["rate"]).ticks_sure(max(0, later["prev_frame"] - earlier["seen_frame"])) \
            >= SLIDE_CLEAR_TICKS

    def dx(a, b, body: str):
        if not a or not b or a.get(body) is None or b.get(body) is None:
            return None
        return round(float(b[body]) - float(a[body]), 1)
    tail = {prompts - 1, prompts} if end_sample is not None and len(rows) >= prompts else set()
    for r in rows:
        n = r["n"]
        if r["dbtn"] not in LR_WANT or n in tail:
            continue
        nxt, nxt2 = by_n.get(n + 1), by_n.get(n + 2)
        s = {"want": LR_WANT[r["dbtn"]], "base": None if nxt is None else nxt.get("prev_frame"),
             "end": None if nxt2 is None else nxt2.get("prev_frame"), "dx_player": None, "dx_blank": None,
             "ok": "unmeasured", "left_out": None}
        if clear(nxt, r) and clear(nxt2, nxt):
            s["dx_player"] = dx(nxt.get("x_prev"), nxt2.get("x_prev"), "player")
            s["dx_blank"] = dx(nxt.get("x_prev"), nxt2.get("x_prev"), "blank")
            if s["dx_player"] is not None and s["dx_blank"] is not None:
                s.update(_slide_verdict(s["want"], [(n, s["want"])], s["dx_player"], s["dx_blank"]))
        out[n] = s
    if tail:
        a, b = by_n.get(prompts - 1), by_n.get(prompts)
        wants = [(x["n"], LR_WANT[x["dbtn"]]) for x in (a, b) if x is not None and x["dbtn"] in LR_WANT]
        if wants:
            want = sum(w for _n, w in wants)
            end = {"player": end_sample.get("x_player"), "blank": end_sample.get("x_blank")}
            s = {"want": want, "base": None if b is None else b.get("prev_frame"), "end": end_sample["frame"],
                 "dx_player": None, "dx_blank": None, "ok": "unmeasured", "left_out": None,
                 "joint": [n for n, _w in wants]}
            opposite = len(wants) == 2 and wants[0][1] != wants[1][1]
            if not opposite and clear(b, a):
                s["dx_player"] = dx(b.get("x_prev"), end, "player")
                s["dx_blank"] = dx(b.get("x_prev"), end, "blank")
                if s["dx_player"] is not None and s["dx_blank"] is not None:
                    s.update(_slide_verdict(want, wants, s["dx_player"], s["dx_blank"]))
            for n, _w in wants:
                out[n] = s
    return out


def page_reading(texts: list, want: str) -> tuple:
    """The score or gil page as two CONSECUTIVE samples read it (research/o4_design.md 2.4.12; [NUMB] is filled in when
    the label renders, 0.3 #6), pure: ``texts`` the page's text in each consecutive merged sample listing it, in frame
    order. The first pair of consecutive samples that read the same text decides: ``("equal", text)`` when it is
    ``want``, ``("differs", text)`` when it is another; a text still holding a raw ``[NUMB`` tag is no reading. ``(None,
    None)``: no pair decides yet."""
    for a, b in zip(texts, texts[1:]):
        if a is None or b is None or a != b or "[NUMB" in a:
            continue
        return ("equal" if a == want else "differs"), a
    return None, None


def chanbara_judge(zone: dict, prompts: list, presses: list, pol: dict, *, page: dict | None = None) -> dict:
    """THE FIGHT'S JUDGE (research/o4_design.md 2.4.8), pure: ``{"v", "by", "why", "faults", "raw"}`` over a zone's
    row, its ``prompt`` rows and the visit's ``press`` rows (each with its ``seq`` and, joined, its ``down_frame``).
    V18 rests on POSITIVE evidence only -- something a merged sample SHOWED; a missing sample is the driver's
    sampling: V17, never V18.

    V17 (driver), the first fault in this order: an instance with no press; two presses; a wrong name; no ``accepted``
    event; ``evidence`` "before"; ``evidence`` "unobserved" (the instrument: a read gap); an instance with NO j bounds
    (:func:`row_bounds`: no prev, seen or down frame, or no rate -- its press cannot be placed against its arm, so
    neither ``j_cap`` nor the raw can be judged on it); ``j_hi > j_cap``; on a complete zone (its end seen, no instance
    stopped) a raw that is UNBOUNDED, else (fast) ``raw_lo < raw_floor`` / (paced) ``[raw_lo, raw_hi]`` outside
    ``pace.raw_band`` ("uninformative") -- the floor and the band are never skipped silently; a non-prompt press whose
    down frame lies at or after the first prompt's ``prev_frame`` and before the zone's end; a rate not measured; a
    measured slide that is neither its want nor its want with whole L/R slides left out; a complete zone with fewer
    than ``prompts`` instances and a ``max_read_gap`` above a prompt's life (50 ticks). An instance the run STOPPED at
    (``stopped``: opened, never to be pressed) is judged by none of them.
    V18 (game, a finding) -- no V17 fault, and: a proper press whose evidence is "lingered"; a proper LEFT/RIGHT press
    whose measured slide shows it left out; more instances than ``prompts``; a complete zone with fewer and its
    ``max_read_gap`` within 50 ticks; or ``page`` (``{"kind", "want", "texts"}``: the score or gil page in consecutive
    samples) read as another text in two samples (:func:`page_reading`).
    None -- the play is proven the frozen play."""
    rows = [r for r in prompts if not r.get("stopped")]
    want_n, ended = int(pol["prompts"]), zone.get("end") is not None
    complete = ended and bool(rows) and len(rows) == len(prompts)
    mine: dict = {}
    for p in presses:
        if p.get("why") == "prompt":
            mine.setdefault(p.get("n"), []).append(p)
    lo, hi = raw_bounds(rows) if complete else (None, None)
    unbounded = [r for r in rows if None in row_bounds(r)]
    v17: list = []
    v17 += [f"instance {r['n']} ({r['dbtn']}) has no press: it ended before the driver pressed" for r in rows
            if not mine.get(r["n"])]
    v17 += [f"instance {r['n']} was pressed {len(mine[r['n']])} times" for r in rows if len(mine.get(r["n"], ())) > 1]
    v17 += [f"instance {r['n']} ({r['dbtn']}) was pressed {r.get('button')!r}, not {pol['buttons'][r['dbtn']]!r}"
            for r in rows if mine.get(r["n"]) and r.get("button") != pol["buttons"][r["dbtn"]]]
    v17 += [f"instance {r['n']}'s press (seq {r.get('seq')}) has no accepted event" for r in rows
            if mine.get(r["n"]) and r.get("accepted_frame") is None]
    v17 += [f"instance {r['n']}'s window left before its press could land (evidence before)" for r in rows
            if r.get("evidence") == "before"]
    v17 += [f"instrument: a read gap of {((r.get('read_gap') or {}).get('s'))} s straddles instance {r['n']}'s mark "
            f"(evidence unobserved)" for r in rows if r.get("evidence") == "unobserved"]
    v17 += [f"instance {r['n']} ({r['dbtn']}) has no j bounds ({_unbounded_why(r)}): its press cannot be placed "
            f"against its arm" for r in unbounded]
    v17 += [f"instance {r['n']}'s j_hi {row_bounds(r)[1]} is over j_cap {pol['j_cap']}" for r in rows
            if row_bounds(r)[1] is not None and row_bounds(r)[1] > pol["j_cap"]]
    if complete:
        what = "raw_floor" if pol["policy"] == "fast" else "raw band"
        if lo is None or hi is None:
            v17.append(f"raw unbounded: the zone is complete but instance(s) {[r['n'] for r in unbounded][:6]} have "
                       f"no j bounds, so its {what} cannot be judged")
        elif pol["policy"] == "fast" and lo < pol["raw_floor"]:
            v17.append(f"raw_lo {lo} is under raw_floor {pol['raw_floor']}")
        elif pol["policy"] == "paced":
            band = pol["pace"]["raw_band"]
            if lo < band[0] or hi > band[1]:
                v17.append(f"uninformative: raw [{lo}, {hi}] is outside the band {list(band)}")
    if rows:
        first = rows[0].get("prev_frame")
        last = (zone.get("end") or {}).get("frame")
        for p in presses:
            d = p.get("down_frame")
            if p.get("why") != "prompt" and d is not None and first is not None and d >= first \
                    and (last is None or d < last):
                v17.append(f"a {p.get('why')} press (seq {p.get('seq')}) went down at frame {d}, inside the fight")
    v17 += [f"instance {r['n']}'s rate is not measured ({(r.get('rate') or {}).get('source')}"
            f"{', stale' if (r.get('rate') or {}).get('stale') else ''})" for r in rows
            if not r.get("rate") or r["rate"].get("source") == "default" or r["rate"].get("stale")]
    slid: dict = {}
    for r in rows:
        s = r.get("slide")
        if isinstance(s, dict) and s.get("ok") is False:
            slid.setdefault(tuple(s.get("joint") or [r["n"]]), s)
    v17 += [f"the slide of instance(s) {list(k)} measured {s['dx_player']} / {s['dx_blank']} (want {s['want']}): "
            f"the instrument's samples" for k, s in slid.items() if s.get("left_out") is None]
    gap = (zone.get("max_read_gap") or {}).get("ticks")
    if ended and len(prompts) < want_n and gap is not None and gap > PROMPT_TICKS:
        v17.append(f"{len(prompts)} instances, and a read gap of {gap} ticks could hide a prompt's whole life")
    if v17:
        return {"v": "V17", "by": "driver", "why": v17[0], "faults": v17, "raw": [lo, hi]}
    v18: list = []
    v18 += [f"instance {r['n']} ({r['dbtn']}) was still listed at or past its mark: the game read no key" for r in rows
            if r.get("evidence") == "lingered"]
    v18 += [f"the slide of instance(s) {s['left_out']} was left out (both bodies unmoved by it): the game read the "
            f"key as a miss" for s in slid.values() if s.get("left_out")]
    if len(prompts) > want_n:
        v18.append(f"{len(prompts)} prompts: more than the {want_n} the bytes arm (64 e20 t1 ip710)")
    if ended and len(prompts) < want_n and (gap is None or gap <= PROMPT_TICKS):
        v18.append(f"{len(prompts)} prompts, fewer than {want_n}, and no read gap could hide one")
    if page is not None:
        verdict, text = page_reading(page.get("texts") or [], page["want"])
        if verdict == "differs":
            v18.append(f"the {page['kind']} page reads {text!r} in two samples, not {page['want']!r}")
    if v18:
        return {"v": "V18", "by": "game", "why": v18[0], "faults": v18, "raw": [lo, hi]}
    return {"v": None, "by": None, "why": None, "faults": [], "raw": [lo, hi]}


def _press_button(steps) -> str | None:
    """The button a ``press`` step names (``["press confirm 4"]`` -> "confirm"), or None."""
    for s in steps or ():
        parts = str(s).split()
        if len(parts) >= 2 and parts[0].lower() == "press":
            return parts[1].lower()
    return None


#: The agent's Confirm spellings (HarnessAgent.ParseControl): a press of any of them is a Confirm on a choice.
CONFIRM_NAMES = ("confirm", "ok", "x", "circle", "a")


def stray_answer(log: list, events: list, steps: list, first_frame: int, close_frame: int | None) -> dict:
    """THE ENCORE ATTRIBUTION (research/o4_design.md 2.4.11), pure: who made the game replay. The Confirm-bearing
    presses of the run's log -- every ``press`` row with a ``seq`` (page, prompt and ``choose``'s), its button from the
    row or its step (``steps``: the session's steps.jsonl rows), its down frame its ``accepted`` event's frame + 1
    (``events``: events.jsonl) -- whose down frame lies in [``first_frame``, ``close_frame``): 127's first publication to
    the first merged sample without it (``close_frame`` None: open) -- EXCEPT the answer's own Confirm when the last
    sample before its down frame published the cursor on No (``selected_before`` 1). One or more (or a Confirm with no
    accepted event, which cannot be placed): V17, the driver's -- "a Confirm of the driver's own landed on choice 127
    ..."; none: V2, the game's -- "the game replayed though the driver confirmed No". ``{"v", "by", "why",
    "presses"}``."""
    accepted: dict = {}
    for e in events or ():
        if e.get("kind") == "accepted" and e.get("seq") is not None:
            try:
                accepted.setdefault(int(e["seq"]), int(e["frame"]))
            except (TypeError, ValueError):
                continue
    by_seq = {int(s["seq"]): s.get("steps") for s in steps or () if s.get("seq") is not None}
    strays = []
    for row in log or ():
        if row.get("k") != "press" or row.get("seq") is None:
            continue
        button = row.get("button") or _press_button(by_seq.get(int(row["seq"])))
        if str(button or "").lower() not in CONFIRM_NAMES:
            continue
        acc = accepted.get(int(row["seq"]))
        if acc is None:
            strays.append({"seq": row["seq"], "why": row.get("why"), "down_frame": None})
            continue
        down = acc + 1
        if down < first_frame or (close_frame is not None and down >= close_frame):
            continue
        if row.get("why") == "choose" and row.get("answer") and row.get("selected_before") == 1:
            continue                                        # the answer's own Confirm, the cursor on No
        strays.append({"seq": row["seq"], "why": row.get("why"), "down_frame": down,
                       "selected_before": row.get("selected_before")})
    if strays:
        s = strays[0]
        how = ("with the cursor on Yes" if s["why"] == "choose" and s["down_frame"] is not None else
               "with no accepted event to place it" if s["down_frame"] is None else "before its answer")
        return {"v": "V17", "by": "driver", "presses": strays,
                "why": f"a Confirm of the driver's own (seq {s['seq']}, {s['why']}) landed on choice 127 {how}"}
    return {"v": "V2", "by": "game", "presses": [], "why": "the game replayed though the driver confirmed No"}


# ======================================================================== S12: the run-wide witness (opt-in, pure)
#: The run-wide outside-input witness's keys (research/o5_design.md 1.2 S12, 4.10), strict: ``why`` optional.
WITNESS_KEYS = ("input_every_s", "why")


def witness_of(pred: dict) -> dict | None:
    """THE RUN-WIDE OUTSIDE-INPUT WITNESS (``pred["witness"]``; research/o5_design.md 1.2 S12, decision 4), checked
    STRICT before anything is driven -- or None: no ``witness``, and :func:`drive`'s ``witness`` is polled only under
    the Chanbara policy (O4's). With it the driver polls that callable through the WHOLE run, every ``input_every_s``: a
    stored answer (O5's Bit[3795]) makes outside input anywhere a false-finding risk.

    ValueError, each naming its cause, on: a policy that is no dict; an unknown key; no ``input_every_s``; an
    ``input_every_s`` that is no positive number (a bool is never a number) or is above 0.1; a ``why`` given that is no
    non-empty string. Returns a copy."""
    raw = pred.get("witness")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"witness {raw!r}: the policy is a dict of {WITNESS_KEYS}")
    unknown = sorted(set(raw) - set(WITNESS_KEYS))
    missing = [] if "input_every_s" in raw else ["input_every_s"]
    if unknown or missing:
        raise ValueError("witness: " + "; ".join(([f"unknown key(s) {unknown}"] if unknown else [])
                                                 + ([f"missing {missing}"] if missing else []))
                         + f" -- the policy's keys are {WITNESS_KEYS} (why optional)")
    every = raw["input_every_s"]
    if not _is_pos(every):
        raise ValueError(f"witness: input_every_s {every!r} is a positive number (seconds between polls)")
    if every > 0.1:
        raise ValueError(f"witness: input_every_s {every!r} is at most 0.1 (a tap lasts a few frames)")
    if "why" in raw and not _is_text(raw["why"]):
        raise ValueError(f"witness: why {raw['why']!r} is a non-empty string")
    return dict(raw)


# ======================================================================== S10: the pre-choice guard (opt-in, pure)
#: The guard's keys (research/o5_design.md 1.2 S10, 4.10), strict: ``why`` optional.
GUARD_KEYS = ("donor", "sc", "markers", "choice", "branch", "page_once_ticks", "quiet_cap_s", "why")


def guard_of(pred: dict) -> dict | None:
    """THE PRE-CHOICE GUARD (``pred["guard"]``; research/o5_design.md 1.2 S10, 2.5), checked STRICT before anything is
    driven -- or None: no ``guard``, and nothing below reads it (the loop is O4's exactly).

    ValueError, each naming its cause, on: a guard that is no dict; a key not in :data:`GUARD_KEYS` or one missing
    (``why`` optional); the predictions also carrying a ``chanbara`` policy (one input policy a segment); ``donor``,
    ``sc`` not ints (a bool is no int); ``markers`` not a non-empty list of non-empty strings; ``branch`` not a list of
    two distinct non-empty strings (the pick's branch page marker, then the other branch's); ``page_once_ticks`` not an
    int 4-30; ``quiet_cap_s`` not a number in (0, 10]; a ``why`` given that is no non-empty string; ``choice`` not the
    ``match`` of exactly one rule of ``pred["choices"]``, or that rule a default one (``pick`` "default" or ``take:
    "default"``: the guard exists for a non-default pick). Returns a copy."""
    raw = pred.get("guard")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"guard {raw!r}: the guard is a dict of {GUARD_KEYS}")
    unknown = sorted(set(raw) - set(GUARD_KEYS))
    missing = [k for k in GUARD_KEYS if k != "why" and k not in raw]
    if unknown or missing:
        raise ValueError("guard: " + "; ".join(([f"unknown key(s) {unknown}"] if unknown else [])
                                               + ([f"missing {missing}"] if missing else []))
                         + f" -- the guard's keys are {GUARD_KEYS} (why optional)")
    if pred.get("chanbara") is not None:
        raise ValueError("guard: the predictions also carry a chanbara policy -- one input policy a segment")
    bad = [k for k in ("donor", "sc") if not _is_int(raw[k])]
    marks = raw["markers"]
    if not isinstance(marks, list) or not marks or not all(_is_text(m) for m in marks):
        bad.append("markers (a non-empty list of non-empty strings)")
    br = raw["branch"]
    if not isinstance(br, list) or len(br) != 2 or not all(_is_text(b) for b in br) or br[0] == br[1]:
        bad.append("branch (two distinct non-empty strings: the pick's branch page marker, then the other's)")
    if not _is_int(raw["page_once_ticks"]) or not 4 <= raw["page_once_ticks"] <= 30:
        bad.append("page_once_ticks (an int 4-30)")
    if not _is_pos(raw["quiet_cap_s"]) or raw["quiet_cap_s"] > 10:
        bad.append("quiet_cap_s (a number in (0, 10])")
    if "why" in raw and not _is_text(raw["why"]):
        bad.append("why (a non-empty string)")
    if bad:
        raise ValueError(f"guard: {bad} of the wrong type or out of range")
    rules = [r for r in pred.get("choices") or () if r.get("match") == raw["choice"]]
    if len(rules) != 1:
        raise ValueError(f"guard: choice {raw['choice']!r} is the match of {len(rules)} rules of the predictions' "
                         f"choices, not exactly one")
    if rules[0].get("pick") == "default" or rules[0].get("take") == "default":
        raise ValueError(f"guard: the rule {raw['choice']!r} takes the game's default -- the guard exists for a "
                         f"non-default pick")
    return json.loads(json.dumps(raw))


def guard_exclude(answer, closing_seq) -> set:
    """The presses the guard's stray window leaves out (research/o5_design.md 1.2 S10, 2.5.4), pure: every seq of the
    answer's span ``(before, after]`` -- select's Down and every Confirm of ``choose_landed``, not only the one rowed
    ``answer`` -- and the marker page's CLOSING press (the last press page-once made on a marker), which goes down on
    the marker page by construction (it is pressed only past every press's hold-off, the page up and waiting)."""
    out = set() if not answer else set(range(int(answer[0]) + 1, int(answer[1]) + 1))
    if closing_seq is not None:
        out.add(int(closing_seq))
    return out


def guard_strays(log: list, events: list, steps: list, lo, hi, *, exclude=()) -> list:
    """THE GUARD'S STRAY ATTRIBUTION (research/o5_design.md 1.2 S10, 2.5.4), pure: every ``press`` row of ``log`` with a
    ``seq`` not in ``exclude`` whose DOWN frame -- its ``accepted`` event's frame + 1 (``events``: events.jsonl;
    HarnessAgent.cs:599-607) -- or, with no accepted event to place it, its DECISION frame (``pre.frame``: fail-closed,
    O4's SWORD (f) rule) lies in [``lo``, ``hi``) (either None: open on that side). A press with neither frame cannot be
    placed and counts (fail-closed). ``steps`` (the session's steps.jsonl rows) name each stray's button where its row
    does not. ``[{"seq", "why", "button", "down_frame", "decision_frame", "placed"}]``, ``placed`` True when an accepted
    event placed it."""
    accepted: dict = {}
    for e in events or ():
        if e.get("kind") == "accepted" and e.get("seq") is not None:
            try:
                accepted.setdefault(int(e["seq"]), int(e["frame"]))
            except (TypeError, ValueError):
                continue
    by_seq = {int(s["seq"]): s.get("steps") for s in steps or () if s.get("seq") is not None}
    skip = {int(s) for s in exclude}
    out = []
    for row in log or ():
        if row.get("k") != "press" or row.get("seq") is None or int(row["seq"]) in skip:
            continue
        seq = int(row["seq"])
        acc = accepted.get(seq)
        down = None if acc is None else acc + 1
        decision = (row.get("pre") or {}).get("frame")
        at = down if down is not None else decision
        if at is not None and ((lo is not None and at < lo) or (hi is not None and at >= hi)):
            continue
        out.append({"seq": seq, "why": row.get("why"), "button": row.get("button") or _press_button(by_seq.get(seq)),
                    "down_frame": down, "decision_frame": decision, "placed": down is not None})
    return out


# ======================================================================== S7: the fight zone's executor (opt-in)
#: The fight's other body (research/o4_design.md 2.4.1): Blank, the published field object sid 20 (64 e0 t0 ip449's
#: InitObject(20)); Zidane is the player.
BLANK_SID = 20
#: S9's page markers (research/o4_design.md 2.4.12): a page holding SCORE_MARK is a score page (120's "Of the 100
#: nobles watching," and 122's "Of 100 nobles watching,"), one holding GIL_MARK the gil page (128) -- US text, as the
#: frozen ``score_page`` and ``gil_page`` are.
SCORE_MARK, GIL_MARK = "nobles watching", "They shower you with"


def dialog_rows(raw: dict) -> list:
    """The published dialog block of a raw state, ALIGNED: ``[(phrase_raw, text), ...]`` -- read off the raw lists,
    never State.raw_texts / texts, which drop empty lines and so lose the alignment (research/o4_design.md 2.4.1)."""
    d = raw.get("dialog") or {}
    phr, txt = list(d.get("phrase_raw") or []), list(d.get("texts") or [])

    def at(xs: list, i: int) -> str:
        return "" if i >= len(xs) or xs[i] is None else str(xs[i])
    return [(at(phr, i), at(txt, i)) for i in range(max(len(phr), len(txt)))]


def cb_sample(raw: dict, read_at=None, mtime=None) -> dict:
    """A MERGED-stream sample (research/o4_design.md 2.4.1): ``{"frame", "read_at", "mtime", "rt", "ui_state",
    "control", "field", "sc", "seq", "dialogs": [(phrase_raw, text)], "dbtns" (the prompts it lists), "choice",
    "x_player", "z_player", "x_blank"}`` -- Blank the published object sid 20."""
    dialogs = dialog_rows(raw)
    p = raw.get("player") or {}
    blank = next((o.get("x") for o in raw.get("objects") or () if isinstance(o, dict) and o.get("sid") == BLANK_SID),
                 None)
    return {"frame": int(raw.get("frame", -1)), "read_at": read_at, "mtime": mtime, "rt": raw.get("rt"),
            "ui_state": raw.get("ui_state"), "control": bool(p.get("control", False)),
            "field": int((raw.get("field") or {}).get("id", -1)), "sc": int(raw.get("scenario", -1)),
            "seq": int(raw.get("seq", -1)), "dialogs": dialogs,
            "dbtns": [d for d in (prompt_dbtn(ph) for ph, _t in dialogs) if d],
            "choice": (raw.get("dialog") or {}).get("choice"), "x_player": p.get("x"), "z_player": p.get("z"),
            "x_blank": blank}


def ring_since(g, frame: int) -> list:
    """``[(read_at, raw)]`` of every sample the session's ring holds after ``frame``, oldest first -- every read the
    harness made, a blocking press's own polls included (research/o4_design.md 0.3 #4); their read times from the ring
    itself where the session keeps one, else None (:meth:`Session.states_since`)."""
    buf = getattr(getattr(g, "_ring", None), "_buf", None)
    if buf is not None:
        return [(t, raw) for t, _age, raw in list(buf) if int(raw.get("frame", -1)) > frame]
    return [(None, raw) for raw in g.states_since(frame)]


def _ring_reads(g, frame: int) -> list:
    """``[(raw, mtime)]`` of every sample the session's ring holds after ``frame``, oldest first, each with its write
    time put back (``read_at - age``: Session._reads_since's rule) where the ring keeps one, else None -- what
    :func:`_game_t` times a ring sample by when it publishes no ``rt`` (S10's quiet window)."""
    ring = getattr(g, "_ring", None)
    if ring is not None and hasattr(ring, "reads_since"):
        return [(raw, None if t is None or age is None else t - age) for t, age, raw in ring.reads_since(frame)]
    return [(raw, None) for raw in g.states_since(frame)]


def _game_t(s: dict | None) -> tuple:
    """A sample's game clock: ``("rt", seconds)`` where the agent publishes one (the fake), else ``("mtime", seconds)``
    for an own read (state.json's write time: the clock the rate is measured from), else ``(None, None)``."""
    if s is None:
        return None, None
    if isinstance(s.get("rt"), (int, float)) and not isinstance(s.get("rt"), bool):
        return "rt", float(s["rt"])
    if isinstance(s.get("mtime"), (int, float)):
        return "mtime", float(s["mtime"])
    return None, None


class _ChanbaraZone:
    """RULE 6b's EXECUTOR (research/o4_design.md 2.4): the fight zone, from its start -- 111, the tutorial, or with no
    111 a first prompt -- to its end text (107 / 108), owning the loop.

    Z0, the zone start: 111 pressed (a ``page`` press row with its ``seq``; 111 joins ``pages``), and again only when it
    is still listed ``page_once_ticks`` past that press's ack-read frame (a Confirm dropped in 111's opening, 0.3 #1);
    its first sample without it is the driver's T0. Z1: quiet until the first prompt -- nothing pressed, fail-closed,
    V14 past ``first_prompt_s``. A zone ENTERED ON A PROMPT (no 111: 2.4.2) starts at Z2, and instance 1's ``prev`` --
    which no sample of the zone can give, its first lists the prompt -- is the ring's last sample of the visit's field
    before the entry that does not list it (``before``: read, never stepped), so its j bounds, the raw and SWORD (f)'s
    window rest on a sample, never on nothing. Z2, the fight, a TIGHT LOOP every ``poll_s``: ONE ``g.state`` read (it
    feeds the clock and the ring), the ring merged (the MERGED stream, 2.4.1: the executor's reads and every harness
    call's, deduplicated on frame, in frame order -- every frame-valued fact is read off it), and per merged sample, in
    order:
    the input witness (every ``input_every_s``; outside input is V13), the run's deadline (V13), the UI (off FieldHUD:
    V13), the field (rule 2's verdict), control (held ``settle_s``: V4), a choice (V17, observed), the zone end (Z3),
    any dialog that is neither a prompt nor 111 (V17, observed -- never rule 7's Confirm), and the INSTANCE TRACKER
    (``cur`` and ``closing``: a prompt still listed in its close tween beside its successor is never a new instance,
    0.2 #1). Then THE PRESS -- one mapped press per instance, blocking for its ack (fast: at once; paced: once its
    elapsed game time reaches ``target_ticks - lead_ticks``); then THE LOST PRESS (a pressed window listed at or past
    its mark, or its end unobserved: stop, the judge decides); then the stall (V14). Z3, the close: the ring merged a
    last time, the accepted events joined (each press's down frame), each instance's evidence, j bounds, read gap and
    slide, the zone judged (:func:`chanbara_judge`) -- a fault ends the run, else the main loop resumes on 107 / 108.

    At a SWITCH -- a new prompt listed -- the new instance's row is opened first (the evidence of what the game
    published) and then the switch is judged: the old instance's press not LANDED by the switch sample (:meth:`landed`:
    the sample published before the agent accepted it -- the instance ended before the driver's press could reach it)
    stops the run, the judge deciding; so does an instance past ``prompts`` (V18) and, in a rehearsal, past
    ``stop_after`` (V17). Nothing is pressed for the instance a stop opened (its row ``stopped``). THE HIDDEN SWITCH:
    instances are told apart by their DBTN, and prompts never repeat back to back, so the newest instance's DBTN listed
    past its window's longest life (:meth:`expired`) is a successor's, every instance between hidden by a read gap --
    a press that stalls before it is sent is one: the run stops, the judge deciding (:func:`prompt_evidence` never reads
    such a listing as the window's). A stalled press is caught at the first read after the stall, which the press
    itself makes before it writes its request."""

    def __init__(self, d, st):
        self.d, self.g, self.pol = d, d.g, d.chanbara
        self.samples: dict = {}                    # frame -> merged sample
        self.order: list = []                      # the merged samples processed, in frame order
        self.before: list = []                     # entered on a prompt: the ring's samples before the entry
        self.cursor = -1                           # the newest frame merged
        self.rows: list = []                       # the zone's prompt rows
        self.cur = None                            # the newest instance's row
        self.closing: dict = {}                    # dbtn -> row: an instance still listed beside its successor
        self.phase = None                          # "z0" | "z1" | "z2" | "z3"
        self.start_page = None
        self.zs_hold = -1                          # Z0: 111's page-once hold-off, a frame
        self.t_phase = self.t_inst = time.time()
        self.control_since = None
        self.witness_t = 0.0
        self.end = None                            # the zone end's first merged sample
        self.last_st = st
        self.zone: dict = {}

    # -- the merged stream
    def merge(self, st=None) -> list:
        new: dict = {}
        for t, raw in ring_since(self.g, self.cursor):
            f = int(raw.get("frame", -1))
            if f not in self.samples and f not in new:
                new[f] = cb_sample(raw, t)
        if st is not None and st.frame > self.cursor and st.frame not in self.samples:
            new[st.frame] = cb_sample(st.raw, st.read_at, st.mtime)
        out = [new[f] for f in sorted(new)]
        for s in out:
            self.samples[s["frame"]] = s
        if out:
            self.cursor = max(self.cursor, out[-1]["frame"])
        return out

    def ring_before(self, frame: int) -> list:
        """The ring's samples of the visit's field BEFORE ``frame``, in frame order, reduced as merged samples and never
        stepped: where instance 1's ``prev`` comes from when the zone is entered on a prompt (2.4.2). A sample of
        another field, or none at all, gives no ``prev`` -- and the judge reads that row unbounded (V17)."""
        out: dict = {}
        for t, raw in ring_since(self.g, -1):
            f = int(raw.get("frame", -1))
            if f < frame and f not in out:
                s = cb_sample(raw, t)
                if s["field"] == self.d.fid:
                    out[f] = s
        return [out[f] for f in sorted(out)]

    # -- the run
    def run(self, st) -> None:
        d, pol = self.d, self.pol
        self.zone = {"k": "zone", "field": d.fid, "donor": d.donor, "visit": d.visit, "sc": d.sc,
                     "policy": pol["policy"], "start_page": None, "first_prompt": None, "end": None, "instances": 0,
                     "presses": 0, "samples": 0, "max_read_gap": None, "input": [], "rate": None, "raw": [None, None],
                     "slides": None, "judge": None, "t0": round(time.time() - d.t0, 2), "t1": None, "v": None,
                     "by": None, "why": None}
        d.zones.append(self.zone)
        self.cursor = st.frame - 1
        first = self.merge(st)
        entry = self.samples[st.frame]
        if is_zone_start([p for p, _t in entry["dialogs"]], pol):
            self.phase = "z0"
            self.start_page = {"seen_frame": entry["frame"], "presses": [], "last_with_frame": entry["frame"],
                               "first_without_frame": None}
            self.zone["start_page"] = self.start_page
            text = next(t for p, t in entry["dialogs"] if is_zone_start([p], pol))
            if text and (not d.pages or d.pages[-1] != text):
                d.pages.append(text)
        else:
            self.phase = "z2"                      # entered on a prompt: 111 closed with no press of the driver's
            self.before = self.ring_before(st.frame)
        for s in first:
            self.step(s)
        while self.phase != "z3":
            self.witness_check()                                       # 0
            if time.time() >= d.deadline:                              # 1
                self.stop("V13", "driver", "the run's budget ran out in the fight", judge=False)
            self.last_st = self.g.state
            for s in self.merge(self.last_st):
                self.step(s)                                           # 2-8
                if self.phase == "z3":
                    break
            if self.phase == "z3":
                break
            self.press_due()                                           # 9
            self.lost_check()                                          # 10
            self.stall_check()                                         # 11
            time.sleep(float(pol["poll_s"]))                           # 12
        self.close_out()
        verdict = chanbara_judge(self.zone, self.rows, self.visit_presses(), pol)
        if verdict["v"] is not None:
            self.finish(verdict["v"], verdict["by"], verdict["why"], verdict)
        self.finish(None, None, None, verdict)
        d.cb["zone_done"], d.cb["zone_end_frame"] = True, self.end["frame"]
        if d.observe is not None:
            d.observe(self.last_st, {"field": d.fid, "donor": d.donor, "sc": d.sc, "visit": d.visit, "log": d.log})

    def step(self, s: dict) -> None:
        """Steps 2-8 of the tight loop on one merged sample (2.4.3)."""
        d, pol = self.d, self.pol
        self.order.append(s)
        if s["ui_state"] != "FieldHUD":                                # 2
            self.stop("V13", "driver", f"the fight left FieldHUD ({s['ui_state']}), nothing pressed", judge=False)
        if s["field"] != d.fid:                                        # 3
            due = [f for f, dn in sorted(d.members.items()) if dn == s["field"]] \
                if d.side_ends is not None and s["field"] not in d.members else []
            if due:
                self.stop("V19", "game", f"the fork run entered REAL {s['field']}, where member({s['field']}) {due[0]} "
                                         f"was due, in the fight", judge=False)
            self.stop("V11", "game", f"the field left {d.fid} for {s['field']} in the fight", judge=False)
        now = s["read_at"] if s["read_at"] is not None else time.time()
        if s["control"]:                                               # 4
            self.control_since = now if self.control_since is None else self.control_since
            if now - self.control_since >= d.settle_s:
                self.stop("V4", "game", f"control held in the fight zone (frame {s['frame']})", judge=False)
        else:
            self.control_since = None
        if s["choice"] is not None:                                    # 5
            self.observe_stop("unclaimed_choice", s, f"a choice the prompt rule does not claim in the fight zone: "
                                                     f"{(s['choice'].get('options') or [''])[0]!r}")
        texts = [t for _p, t in s["dialogs"]]
        if self.phase in ("z1", "z2") and is_zone_end(texts, pol):     # 6
            self.end = s
            self.zone["end"] = {"frame": s["frame"], "text": next(t for t in texts if is_zone_end([t], pol))}
            self.phase = "z3"
            return
        zs = is_zone_start([p for p, _t in s["dialogs"]], pol)
        others = [t or p for p, t in s["dialogs"] if (p or t) and not prompt_dbtn(p)
                  and not (zs and is_zone_start([p], pol))]
        if others:                                                     # 7
            self.observe_stop("unclaimed_dialog", s, f"a dialog the prompt rule does not claim in the fight zone: "
                                                     f"{others[0][:120]!r}")
        if self.phase == "z0":
            if zs:
                self.start_page["last_with_frame"] = s["frame"]
                if s["dbtns"]:
                    self.observe_stop("prompt_beside_zone_start", s, "a prompt published beside 111, nothing pressed")
                return
            self.start_page["first_without_frame"] = s["frame"]      # the driver's T0
            self.phase, self.t_phase = "z1", time.time()
        if self.phase == "z1" and s["dbtns"]:
            self.phase = "z2"
        if self.phase == "z2":
            self.track(s)                                              # 8

    def track(self, s: dict) -> None:
        """Step 8, the instance tracker (2.4.3; rev. 2)."""
        dbtns = s["dbtns"]
        for dbtn, row in list(self.closing.items()):
            if dbtn in dbtns:
                row["last_listed_frame"] = s["frame"]
            else:
                if row.get("gone_frame") is None:
                    row["gone_frame"] = s["frame"]
                del self.closing[dbtn]
        cur = self.cur
        if cur is not None:
            if cur["dbtn"] in dbtns and self.expired(cur, s):       # THE HIDDEN SWITCH: a successor's listing
                self.stop(None, None, f"a read gap hid an instance: {cur['dbtn']} listed at frame {s['frame']}, past "
                                      f"instance {cur['n']}'s window's longest life, is a successor's")
            if cur["dbtn"] in dbtns:
                cur["last_listed_frame"] = s["frame"]
            elif cur.get("gone_frame") is None:
                cur["gone_frame"] = s["frame"]
            if not dbtns:
                cur["gap"] = True
        fresh = [y for y in dbtns if y not in self.closing and (cur is None or y != cur["dbtn"])]
        if not fresh:
            return
        if len(fresh) > 1:
            self.stop("V17", "driver", f"a read gap hid an instance: {fresh} first listed together at frame "
                                       f"{s['frame']}", judge=False)
        row = self.open_instance(fresh[0], s)
        if cur is not None and cur["dbtn"] in dbtns:
            self.closing[cur["dbtn"]] = cur
        self.cur = row
        if cur is not None and not self.landed(cur, s):
            row["stopped"] = True
            self.stop(None, None, f"instance {cur['n']} ({cur['dbtn']}) ended before the driver's press landed: "
                                  f"instance {row['n']} was listed at frame {s['frame']}")
        if row["n"] > int(self.pol["prompts"]):
            row["stopped"] = True
            self.stop(None, None, f"instance {row['n']}: more prompts than the {self.pol['prompts']} the bytes arm")
        if self.pol.get("stop_after") is not None and row["n"] > int(self.pol["stop_after"]):
            row["stopped"] = True
            self.stop("V17", "driver", f"the rehearsal's stop after instance {self.pol['stop_after']}", judge=False)

    @staticmethod
    def landed(row: dict, s: dict) -> bool:
        """Whether the instance's press had reached the agent by sample ``s``: pressed, and ``s`` published after the
        agent ACCEPTED the request (its ``seq`` at or past the press's). A sample before that shows a game the press
        cannot have touched -- every read a blocking press makes before its acceptance is one (the ring keeps them)."""
        return row.get("seq") is not None and s["seq"] >= row["seq"]

    def expired(self, row: dict, s: dict) -> bool:
        """Whether ``s`` lies past the longest life the instance's window can have: more than PROMPT_TICKS +
        :data:`LIFE_MARGIN_TICKS` sure ticks after its seen frame (the window was armed before it)."""
        rate = row.get("rate")
        return bool(rate) and rate_of(rate).ticks_sure(max(0, s["frame"] - row["seen_frame"])) \
            > PROMPT_TICKS + LIFE_MARGIN_TICKS

    def open_instance(self, dbtn: str, s: dict) -> dict:
        d = self.d
        prev = next((x for x in reversed(self.order[:-1]) if dbtn not in x["dbtns"]), None)
        if prev is None:                           # entered on a prompt: the ring's last sample before the entry
            prev = next((x for x in reversed(self.before) if dbtn not in x["dbtns"]), None)
        n = len(self.rows) + 1
        rate = self.g.rate()
        row = {"k": "prompt", "n": n, "dbtn": dbtn, "button": None, "field": d.fid, "donor": d.donor,
               "visit": d.visit, "sc": d.sc, "prev_frame": None if prev is None else prev["frame"],
               "prev_kind": None if prev is None else ("dbtn" if prev["dbtns"] else "none"),
               "seen_frame": s["frame"], "seen_t": round((s["read_at"] or time.time()) - d.t0, 3),
               "published": {"texts": [t for _p, t in s["dialogs"]], "phrase_raw": [p for p, _t in s["dialogs"]]},
               "x_prev": None if prev is None else {"player": prev["x_player"], "blank": prev["x_blank"]},
               "x_seen": {"player": s["x_player"], "blank": s["x_blank"]},
               "seq": None, "pressed_t": None, "ack_frame": None, "ack_t": None, "accepted_frame": None,
               "down_frame": None, "last_listed_frame": s["frame"], "gone_frame": None, "gone_kind": None,
               "evidence": None, "read_gap": None, "rate": rate.as_dict(), "excess": None, "j_lo": None, "j_hi": None,
               "regime": str(int(round(rate.fps))), "slide": None, "v": None, "why": None}
        self.rows.append(row)
        d.prompts.append(row)
        d.log.append(row)
        self.zone["instances"] = len(self.rows)
        if n == 1:
            t0 = (self.start_page or {}).get("first_without_frame")
            self.zone["first_prompt"] = {"seen_frame": s["frame"], "t0_frame": t0,
                                         "after_t0_ticks": None if t0 is None else
                                         [rate.ticks_sure(s["frame"] - t0), rate.ticks_most(s["frame"] - t0)]}
        self.t_inst = time.time()
        return row

    # -- step 9, the press
    def press_due(self) -> None:
        from harness import HarnessError
        pol, latest = self.pol, self.order[-1] if self.order else None
        if latest is None:
            return
        if self.phase == "z0":
            if is_zone_start([p for p, _t in latest["dialogs"]], pol) and not latest["dbtns"] \
                    and latest["frame"] >= self.zs_hold:
                st = self.last_st
                row = self.d.press("page", st, 3)
                seq = self.g.channel.seq
                st2 = self.g.state
                row.update(seq=seq, ack_frame=st2.frame, button="confirm",
                           texts=[t for _p, t in latest["dialogs"] if t])
                self.start_page["presses"].append(seq)
                self.zs_hold = st2.frame + self.g.rate().frames_for_ticks(int(pol["page_once_ticks"]))
            return
        cur = self.cur
        if self.phase != "z2" or cur is None or cur.get("seq") is not None or cur.get("stopped") \
                or cur["dbtn"] not in latest["dbtns"] or not self.due(latest):
            return
        d, g = self.d, self.g
        button = pol["buttons"][cur["dbtn"]]
        row = {"k": "press", "why": "prompt", "n": cur["n"], "button": button, "field": d.fid, "donor": d.donor,
               "visit": d.visit, "sc": d.sc, "pre": {"frame": latest["frame"], "control": latest["control"],
                                                     "x": latest["x_player"], "z": latest["z_player"]},
               "post": None, "near": [], "seq": None, "ack_frame": None}
        t = time.time()
        try:
            g.press(button, int(pol["press_frames"]))
        except HarnessError as err:
            row["error"] = str(err)[:300]
            d.log.append(row)
            self.stop("V13", "driver", f"instance {cur['n']}'s press was refused or failed: {str(err)[:200]}",
                      judge=False)
        seq = g.channel.seq
        st2 = g.state
        rate = g.rate()
        try:
            excess = float(g._clock.excess_ticks(cur["prev_frame"], st2.frame, rate)) \
                if cur["prev_frame"] is not None else 0.0
        except Exception:                                  # noqa: BLE001 - a clock without the frames: no excess known
            excess = 0.0
        row.update(seq=seq, ack_frame=st2.frame)
        d.log.append(row)
        cur.update(seq=seq, button=button, pressed_t=round(t - d.t0, 3), ack_frame=st2.frame,
                   ack_t=round(time.time() - d.t0, 3), rate=rate.as_dict(), excess=round(excess, 3),
                   regime=str(int(round(rate.fps))))
        self.zone["presses"] += 1
        self.last_st = st2

    def due(self, latest: dict) -> bool:
        """Fast: at once. Paced (2.4.10): once the instance's ELAPSED GAME TIME reaches ``target_ticks - lead_ticks``
        ticks -- the game clock's seconds x the rate's ``tick_hz`` (the clock the rate is measured from: the published
        ``rt``, else state.json's write time), or frames x ``per_frame()`` when the two samples share no clock."""
        if self.pol["policy"] == "fast":
            return True
        pace = self.pol["pace"]
        rate = self.g.rate()
        seen = self.samples.get(self.cur["seen_frame"])
        (ka, ta), (kb, tb) = _game_t(seen), _game_t(latest)
        if ka is not None and ka == kb:
            ticks = (tb - ta) * rate.tick_hz
        else:
            ticks = (latest["frame"] - self.cur["seen_frame"]) * rate.per_frame()
        return ticks >= float(pace["target_ticks"] - pace["lead_ticks"])

    # -- step 10, the lost press and the unobserved end; step 11, the stall; step 0, the witness
    def lost_check(self) -> None:
        for row in self.rows:
            if row.get("ack_frame") is None or row.get("_settled") or row.get("stopped"):
                continue
            mark = row["ack_frame"] + rate_of(row["rate"]).frames_for_ticks(int(self.pol["gone_ticks"]))
            if row["last_listed_frame"] >= mark:
                self.stop(None, None, f"instance {row['n']} ({row['dbtn']}) was still listed at frame "
                                      f"{row['last_listed_frame']}, past its mark {mark}")
            gone = row.get("gone_frame")
            if gone is not None:
                if gone > mark:
                    self.stop(None, None, f"instance {row['n']}'s end is unobserved: no sample between its mark {mark} "
                                          f"and frame {gone}")
                row["_settled"] = True

    def stall_check(self) -> None:
        pol, now = self.pol, time.time()
        if self.phase == "z0" and now - self.t_phase > float(pol["zone_stall_s"]):
            self.stop("V14", "game", f"111 stayed up {float(pol['zone_stall_s']):g} s", judge=False)
        if self.phase == "z1" and now - self.t_phase > float(pol["first_prompt_s"]):
            self.stop("V14", "game", f"no prompt within {float(pol['first_prompt_s']):g} s of 111's close",
                      judge=False)
        if self.phase == "z2" and now - self.t_inst > float(pol["zone_stall_s"]):
            self.stop("V14", "game", f"no new prompt and no zone end for {float(pol['zone_stall_s']):g} s",
                      judge=False)

    def witness_check(self) -> None:
        w, now = self.d.witness, time.time()
        if w is None or now - self.witness_t < float(self.pol["input_every_s"]):
            return
        self.witness_t = now
        what = w()
        if what:
            self.zone["input"].append({"t": round(now - self.d.t0, 3), "frame": self.cursor, "what": str(what)})
            self.stop("V13", "driver", f"outside input during the fight: {what}", judge=False)

    # -- the close, the stop
    def visit_presses(self) -> list:
        d = self.d
        return [r for r in d.log if r.get("k") == "press" and r.get("seq") is not None and r.get("visit") == d.visit]

    def close_out(self) -> None:
        """Z3's completion -- also a stop's (2.4.9): the ring merged a last time, every press of the visit placed by its
        accepted event (``down_frame`` = accepted + 1, events.jsonl read once), each instance's evidence, j bounds,
        regime and read gap, the slides, the zone's counts."""
        g, pol = self.g, self.pol
        self.merge(None)
        acc: dict = {}
        for e in g.channel.events():
            if e.get("kind") == "accepted" and e.get("seq") is not None:
                try:
                    acc.setdefault(int(e["seq"]), int(e["frame"]))
                except (TypeError, ValueError):
                    continue
        for p in self.visit_presses():
            a = acc.get(int(p["seq"]))
            p["accepted_frame"], p["down_frame"] = a, None if a is None else a + 1
        samples = sorted(self.samples.values(), key=lambda s: s["frame"])
        end_frame = None if self.end is None else self.end["frame"]
        for i, r in enumerate(self.rows):
            if r.get("seq") is not None:
                a = acc.get(int(r["seq"]))
                r["accepted_frame"], r["down_frame"] = a, None if a is None else a + 1
            until = next((x["seen_frame"] for x in self.rows[i + 1:] if x["dbtn"] == r["dbtn"]), None)
            ev = prompt_evidence(r, samples, int(pol["gone_ticks"]), until=until)
            r.update(evidence=ev["evidence"], last_listed_frame=ev["last_listed_frame"], gone_frame=ev["gone_frame"],
                     gone_kind=ev["gone_kind"])
            r["j_lo"], r["j_hi"] = j_bounds(r)
            nxt = self.rows[i + 1]["seen_frame"] if i + 1 < len(self.rows) else end_frame
            r["read_gap"] = self.gap(samples, r["seen_frame"], nxt, r.get("rate"))
            r.pop("_settled", None)
        live = [r for r in self.rows if not r.get("stopped")]
        end = None if self.end is None else {"frame": self.end["frame"], "x_player": self.end["x_player"],
                                             "x_blank": self.end["x_blank"]}
        slides = measure_slides(live, end, int(pol["prompts"]))
        for r in self.rows:
            r["slide"] = slides.get(r["n"]) if r["dbtn"] in LR_WANT else None
        seen = {id(s): s for s in slides.values()}.values()
        self.zone.update(samples=len(samples), instances=len(self.rows),
                         max_read_gap=self.gap(samples, samples[0]["frame"] if samples else None, end_frame,
                                               (self.rows[-1] if self.rows else {}).get("rate")),
                         rate=(self.rows[-1] if self.rows else {}).get("rate"),
                         raw=list(raw_bounds(live)) if end_frame is not None and live else [None, None],
                         slides={"ok": sum(1 for s in seen if s["ok"] is True),
                                 "unmeasured": sum(1 for s in seen if s["ok"] == "unmeasured"),
                                 "not_ok": sum(1 for s in seen if s["ok"] is False)})

    @staticmethod
    def gap(samples: list, a, b, rate) -> dict | None:
        """The longest step between consecutive merged samples from frame ``a`` to ``b`` (None: to the last): in frames,
        in ``ticks_most`` at ``rate`` and in seconds of their read times (where both were read with one)."""
        if a is None:
            return None
        span = [s for s in samples if s["frame"] >= a and (b is None or s["frame"] <= b)]
        if len(span) < 2:
            return {"frames": 0, "ticks": 0, "s": 0.0}
        frames, secs = 0, 0.0
        for x, y in zip(span, span[1:]):
            frames = max(frames, y["frame"] - x["frame"])
            if x["read_at"] is not None and y["read_at"] is not None:
                secs = max(secs, y["read_at"] - x["read_at"])
        return {"frames": frames, "ticks": None if not rate else rate_of(rate).ticks_most(frames),
                "s": round(secs, 3)}

    def observe_stop(self, kind: str, s: dict, why: str) -> None:
        self.d.observed(kind, s)
        self.stop("V17", "driver", why, judge=False)

    def finish(self, v, by, why, verdict) -> None:
        """The zone row completed and logged (2.4.9); a VOID raised at once -- V13 as the instrument's HarnessError,
        anything else a RouteVoid with the zone's cell. Nothing more is pressed."""
        from harness import HarnessError
        d = self.d
        self.zone.update(v=v, by=by, why=why, judge=verdict, t1=round(time.time() - d.t0, 2))
        d.log.append(self.zone)
        d.since, d.sig, d.walked = time.time(), None, None
        if v is None:
            return
        if v == "V13":
            raise HarnessError(why)
        raise RouteVoid(why, v=v, cell=d.vcell(d.donor, d.sc), by=by)

    def stop(self, v, by, why, *, judge: bool = True) -> None:
        """A stop in the zone: the rows completed (:meth:`close_out`), then -- with ``judge`` -- the judge decides
        (its verdict over the live reason: a V17 fault or a V18 finding; with none, V17 with the live reason)."""
        self.close_out()
        verdict = None
        if judge:
            verdict = chanbara_judge(self.zone, self.rows, self.visit_presses(), self.pol)
            if verdict["v"] is not None:
                v, by, why = verdict["v"], verdict["by"], verdict["why"]
            elif v is None:
                v, by = "V17", "driver"
        self.finish(v, by, why, verdict)


# ======================================================================== the driver
class _Drive:
    """One run of the beat-table driver: its counters, its evidence, its rules and its step executors. :func:`drive`
    is the entry; research/o2_design.md 2.2 is the loop, 2.3 the executors, 2.7 the VOID classes, 4.7 the evidence."""

    def __init__(self, g, pred, side, log, *, deadline, floor_for, prior_for, progress, end_fields, observe,
                 forbid_live, witness=None):
        self.g, self.pred, self.side, self.log, self.deadline = g, pred, side, log, deadline
        self.floor_for, self.prior_for, self.observe, self.forbid_live = floor_for, prior_for, observe, forbid_live
        self.members = ST.members_of(pred) if side == "F" else {}
        # S6 (research/o4_design.md 1.2), OPT-IN: the ends PER SIDE (``side_ends``, checked strict before anything is
        # driven). The END FIELDS -- raw ids: rule 1's arrival, on_route, the live scan's patterns -- and the END
        # PLACES -- frozen: what scan() and end_row() cut at -- are kept apart. Without ``side_ends`` both come from the
        # predictions' one list (or the ``end_fields`` given), and with no end field a member, every list and every
        # place is today's (O1-O3).
        self.side_ends = ST.side_ends_of(pred)
        self.ends = list(end_fields) if end_fields is not None else ST.side_ends(pred, side)
        self.end_places = sorted({place(f, self.members) for f in self.ends})
        self.route = list(pred.get("route") or ())
        self.start_place = place(pred["start"][side], self.members)
        # rule 2's ORDER: the places a run visits, in turn (``visits``; default ``route``, each once), from the start
        # place's first entry -- a rehearsal stage starts mid-route
        self.order = list(pred.get("visits") or self.route)
        if self.start_place not in self.order:
            raise ValueError(f"the start place {self.start_place} is not in the route's visit order {self.order}")
        self.at = self.order.index(self.start_place) - 1        # the place of the current visit, in self.order
        for c in pred.get("table") or ():                   # a malformed table refuses before anything is walked
            if "visit" in c and not (_is_int(c["visit"]) and c["visit"] >= 1):
                raise ValueError(f"table cell ({c.get('donor')}, {c.get('sc')}): visit {c['visit']!r} is the 1-based "
                                 f"position of a visit in visits, an int >= 1")
            for raw in c["steps"]:
                step_of(pred, raw)
        # S13 (research/o5_design.md 1.2), OPT-IN: a table with any VISIT-SCOPED cell (``visit``) keys every VOID and
        # every ``observed`` row by ``[place, sc, visit]`` (:meth:`vcell`); without one, ``[place, sc]`` as ever.
        self.visit_cells = any("visit" in c for c in pred.get("table") or ())
        # S16 (research/o6_design.md 1.2): the naming registrations, checked strict before anything is driven; the page
        # witness (``pw``) armed by rule 4 under one carrying ``on_page`` -- without one, rule 4 is O5's exactly
        self.naming = naming_of(pred)
        self.pw = None
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
        # S7-S9 (research/o4_design.md 2.4), OPT-IN: THE CHANBARA POLICY, checked strict before anything is driven, and
        # the outside-input witness it polls. Without the policy (None) nothing below reads either: the loop is O3's.
        self.chanbara = chanbara_of(pred)
        self.witness, self.witness_t = witness, 0.0
        # S12 (research/o5_design.md 1.2), OPT-IN: THE RUN-WIDE WITNESS -- the same callable polled through the whole
        # run under ``pred["witness"]`` (checked strict), at its ``input_every_s``; under the Chanbara policy at the
        # policy's (O4's, unchanged). With neither, nothing polls it.
        self.witness_pol = witness_of(pred)
        self.witness_every = (self.witness_pol or self.chanbara or {}).get("input_every_s")
        # S10-S11 (research/o5_design.md 1.2), OPT-IN: THE PRE-CHOICE GUARD, checked strict before anything is driven,
        # and the guarded rule it answers through the VERIFIED landing; its state (``gd``) is a visit's (rule 3).
        # Without it (None) nothing below reads either: the loop is O4's exactly.
        self.guard = guard_of(pred)
        self.guard_rule = None if self.guard is None else next(r for r in pred["choices"]
                                                               if r.get("match") == self.guard["choice"])
        self.gd = None
        self.zones: list = []              # the policy's ``zone`` rows
        self.prompts: list = []            # ... and its ``prompt`` rows
        self.cb: dict = {"zone_done": False, "zone_end_frame": None, "score_read": False, "held_off": {},
                         "quiet": None, "choice_first": {}, "encore": None, "visit_frame": -1}
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
        self.to_row = None                 # S14b: the last DONE trigger step row carrying ``to``, its walk-out unread
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
            if self.chanbara is not None:  # and one that raises in the fight its zone and prompt rows
                progress.update(zones=self.zones, prompts=self.prompts)

    # -- the outcome, a VOID ------------------------------------------------------------------------------------
    def out(self, end: str, why: str) -> dict:
        o = {"end": end, "why": why, "void": None, "beats": self.beats, "pages": self.pages, "timed": self.timed,
             "choices": self.choices, "steps": self.steps, "overlays": self.overlays, "forbidden": self.forbidden,
             "end_state": self.end_state, "t": round(time.time() - self.t0, 1)}
        if self.battles:                   # S4: only with a registry, so O2's outcome keeps its keys
            o.update(battles=self.battle_log, battle_epoch0=self.battle_epoch0)
        if self.movies is not None:        # the movie-skip policy: only with it, so O3's outcome keeps its keys
            o["movies"] = self.movie_rows
        if self.chanbara is not None:      # the Chanbara policy: only with it, so O1-O3's outcomes keep their keys
            o.update(zones=self.zones, prompts=self.prompts)
        return o

    def vcell(self, donor, sc) -> list:
        """A VOID's cell, and an ``observed`` row's (S13, research/o5_design.md 1.2): ``[donor, sc]`` -- and under a
        table with any visit-scoped cell ``[donor, sc, visit]``, the visit the 1-based position in ``visits`` of the one
        the run stands in (``self.at + 1``; before rule 3 counts a new one, the visit just left), so one class at two
        visits of a place is two keys for VOID-ASYM."""
        return [donor, sc, self.at + 1] if self.visit_cells else [donor, sc]

    def void(self, v: str, by: str, why: str):
        return RouteVoid(why, v=v, cell=self.vcell(self.donor, self.sc), by=by)

    def stray(self, why: str) -> RouteVoid:
        """Rule 2's V11 (2.7), attributed: the DRIVER's when the last thing the run did was a walk that ended unfinished
        (``interrupted`` or ``failed``) with nothing pressed, answered or named since -- a door the executor did not
        see fire (its switch came after ``exit_wait_s``, or it is none the table registers). That step row then carries
        the landing (``landed``, ``v``, ``by``; ``late``: judged by the loop), which is what 4.7's ``walk`` backing reads,
        and the VOID its cell -- under a visit-scoped table the walk's visit too (S13: the walked row is always the
        current visit's, rule 3 clears it at a new one, and rule 2 judges before it counts one). Otherwise the GAME's: a
        scripted transition."""
        row = self.walked
        if row is None:
            return self.void("V11", "game", why)
        row.update(landed=self.fid, v="V11", by="driver", late=True,
                   why=f"{row.get('why')}; then {why}, with nothing done since the walk")
        return RouteVoid(f"{why}, after step {row.get('name') or row.get('n')!r} ({row.get('outcome')}) with nothing "
                         f"done since", v="V11", cell=self.vcell(row.get("donor"), row.get("sc")), by="driver")

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
        """The live forbidden scan (2.2, rule 3): the run's own rows (after its last arm, cut at its end PLACES), 4.7's
        patterns from its start row on. A hit the log backs is V12; an unbacked one is logged and the run goes on."""
        rows = self.g.story_rows()
        arm = max((i for i, r in enumerate(rows) if r.k == "e" and r.why == "arm"), default=None)
        if arm is None:
            return
        kept, _end = ST.cut_at_end(rows[arm:], self.end_places, self.members)
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
        last arm, at the end PLACES: S6, so an F side ending in member(153) is cut at its place 153) -- waited for, up
        to ``end_row_s`` and never past the run's deadline. ``{"seen", "f", "s"}``: whether it came, its frame (``f``,
        None when it did not), the seconds waited. A row that never comes is no VOID here: the analysis reads that run
        (A-NOEND). A trace the harness cannot read raises, as the live scan does."""
        t0 = time.time()
        until = min(t0 + self.end_row_s, self.deadline)
        while True:
            rows = self.g.story_rows()
            arm = max((i for i, r in enumerate(rows) if r.k == "e" and r.why == "arm"), default=None)
            line = None if arm is None else ST.cut_at_end(rows[arm:], self.end_places, self.members)[1]
            if line is not None or time.time() >= until:
                hit = next((r for r in rows if r.line == line), None) if line is not None else None
                return {"seen": hit is not None, "f": None if hit is None else hit.f, "s": round(time.time() - t0, 2)}
            time.sleep(END_ROW_POLL_S)

    # -- S16: the name on the page (research/o6_design.md 1.2) ------------------------------------------------------
    def last_listed(self, frame: int) -> dict | None:
        """The ``named`` row's ``before``: the ring's latest sample that listed a window before the naming screen's
        first sample -- the run of ``NameSetting`` samples ending at ``frame`` -- as ``{"frame", "raws"}`` (its
        phrase_raw column), or None. Read on rule 4's poll, BEFORE accept_name's Confirms: the ring is a bounded window
        of reads, and the screen's own reads push the page before it out (the analysis's A-NAMING reads it)."""
        samples = [raw for _t, raw in ring_since(self.g, -1) if int(raw.get("frame", -1)) <= frame]
        i = len(samples)
        while i > 0 and samples[i - 1].get("ui_state") == "NameSetting":
            i -= 1
        for raw in reversed(samples[:i]):
            rows = dialog_rows(raw)
            if any(ph or tx for ph, tx in rows):
                return {"frame": int(raw.get("frame", -1)), "raws": [ph for ph, _tx in rows]}
        return None

    def page_windows(self, raw: dict) -> list:
        """The frozen windows a sample lists PARSED: each dialog row whose raw holds an entry's ``raw_holds`` and whose
        text holds no tag -- ``{"mes", "raw", "text", "line", "want", "ok"}``, ``line`` its rendered text's line the
        entry names and ``ok`` whether it is the entry's ``text`` exactly. An unparsed window (its tag left in the text)
        and a window no entry names are never listed."""
        pw, out = self.pw, []
        for ph, tx in dialog_rows(raw):
            if pw["tag"] in tx:
                continue
            w = next((w for w in pw["windows"] if w["raw_holds"] in ph), None)
            if w is None:
                continue
            lines = tx.split("\n")
            line = lines[w["line"]] if w["line"] < len(lines) else ""
            out.append({"mes": w["mes"], "raw": ph, "text": tx, "line": line, "want": w["text"],
                        "ok": line == w["text"]})
        return out

    def page_witness(self, *, final: bool = False) -> None:
        """THE PAGE WITNESS (S16, research/o6_design.md 1.2; 0.2 #8), armed after a registered naming with ``on_page``:
        the ring since its last scan, for the first sample IN THE NAMING'S FIELD listing a PARSED window a frozen entry
        names (:meth:`page_windows`). On it ONE ``name_on_page`` row -- ``{"field", "donor", "visit", "frame", "tag",
        "windows", "verdict"}``, exactly the windows that sample lists -- and the witness disarmed: every line its
        entry's text, ``verdict`` "ok" and the entry's beat set; any other name, ``verdict`` "V13" and the run VOID V13
        by the driver at the naming's cell -- input at the naming screen (accept_name's blocking call, which the
        run-wide witness does not see), the driver's to re-run -- or a patched default name, which the message names
        too (a stacked DictionaryPatch.txt CharacterDefaultName line, or [Import] Text: the screen pre-fills it on every
        run, so every run VOIDs alike; O6's preflight P-NAME refuses either before the session -- the review,
        research/o6_design.md 11.7 #1). ``final`` (a new visit): the last scan of the field it leaves, then disarmed
        whatever it found -- no such sample, no row: the beat stays False, the run uncovered."""
        pw = self.pw
        hit = None
        for _t, raw in ring_since(self.g, pw["scanned"]):
            pw["scanned"] = max(pw["scanned"], int(raw.get("frame", -1)))
            if int((raw.get("field") or {}).get("id", -1)) != pw["field"]:
                continue
            wins = self.page_windows(raw)
            if wins:
                hit = (int(raw.get("frame", -1)), wins)
                break
        if hit is None:
            if final:
                self.pw = None
            return
        frame, wins = hit
        verdict = "ok" if all(w["ok"] for w in wins) else "V13"
        self.log.append({"k": "name_on_page", "field": pw["field"], "donor": pw["donor"], "visit": pw["visit"],
                         "frame": frame, "tag": pw["tag"], "windows": wins, "verdict": verdict})
        self.pw = None
        if verdict == "ok":
            self.beats[pw["beat"]] = True
            return
        bad = next(w for w in wins if not w["ok"])
        raise RouteVoid(f"the name on the page is not the default: mes {bad['mes']} renders {bad['line']!r}, "
                        f"registered {bad['want']!r} -- input at the naming screen (accept_name's blocking call, which "
                        f"the run-wide witness does not see), or a patched default name (a stacked DictionaryPatch.txt "
                        f"CharacterDefaultName line, or [Import] Text: the preflight's P-NAME refuses either)",
                        v="V13", cell=pw["cell"], by="driver")

    # -- the walks ------------------------------------------------------------------------------------------------
    def floor(self, closed=()):
        key = (self.donor, tuple(closed))
        if key not in self.floors:
            self.floors[key] = self.floor_for(self.donor, list(closed))
        return self.floors[key]

    def walk_kw(self, step: dict) -> dict:
        """What every walk of a step passes (2.3): the donor's floor as the player walks it, with the step's closed
        triangles; its prior; the unstick / smooth / handoff walk; the step's npcs, overlay and settle. S18/S19
        (research/o7_design.md 1.2), opt-in: the step's ``clearance`` (the planner's wall clearance) and ``basis`` go to
        route_to ONLY when the step carries them, so every O1-O6 call is exactly what it was."""
        from ff9mapkit.content import pathfind
        closed = closed_tris(self.pred, step, self.floor())
        kw = dict(walkmesh=self.floor(closed), prior=self.prior_for(self.donor), unstick=True, smooth=True,
                  margin=pathfind.KEEPOUT_MARGIN_W, timeout=float(step["timeout_s"]), npcs=bool(step["npcs"]),
                  overlay_ok=bool(step["overlay_ok"]), settle=step["settle"], handoff=True)
        if step.get("clearance") is not None:                  # S18 (opt-in)
            kw["clearance"] = float(step["clearance"])
        if step.get("basis") is not None:                      # S19 (opt-in)
            kw["basis"] = step["basis"]
        return kw

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
        if step.get("to") is not None:                   # S14 (opt-in): the landing-aware trigger
            return self.x_trigger_to(step)
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

    def x_trigger_to(self, step: dict) -> tuple:
        """S14, THE LANDING-AWARE TRIGGER (research/o6_design.md 1.2; decision 3), a trigger step carrying ``to``: the
        walk as :meth:`x_trigger` walks it; a walk that ended with control held waits TRIGGER_WAIT_S for it to go
        (``failed`` without), a read with control gone IN THIS FIELD its loss sample; then the landing
        (:meth:`left_for`: route_to's own record, or the switch waited out once the published id left) and
        :func:`trigger_to_verdict`. Done -- path A (route_to returned before the map switch: ``landed`` None) or path B
        (after it: the next field, its ``flip_frame`` read off the ring); ``left`` -- the evidence held and the run
        landed in another place, kept under ``misroute`` with ``landed`` None and no class: rule 2 judges the landing
        on the next poll; V13 by the driver -- the loss never read here; V11 by the driver -- an in-field loss without
        the evidence that lands (:meth:`strayed`); else today's landing judge (:meth:`door_loss`, ``interrupted``)."""
        from harness import HarnessError
        from ff9mapkit.content import doorface
        g, fid = self.g, self.fid
        wait = float(step["exit_wait_s"])
        pts = region(self.pred, step["target"])["points"] if step.get("target") else None
        rec = g.route_to(*step["goal"], zone=pts, avoid=polys(self.pred, step.get("avoid")),
                         tolerance=float(step["tolerance"]), **self.walk_kw(step))
        out = {"route": trim_route(rec), "lost": rec.get("lost"), "landed": None}
        if out["lost"] is None and rec.get("landed") in (None, fid):
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
            if st.field_id == fid and not st.control:      # control gone IN THIS FIELD: the loss sample
                out["lost"] = {**sample(st), "field": st.field_id}
        landed = self.left_for(rec, out, "the trigger's door", wait)
        lost = out["lost"]
        here = lost is not None and lost.get("field") == fid
        ok = here and ((lost.get("x") is not None and doorface.region_contains(lost["x"], lost["z"], pts))
                       if pts is not None else until_ok(step["until"], lost.get("x"), lost.get("z")))
        to = step.get("to")
        to_place = None if landed is None else place(landed, self.members)
        verdict, what = trigger_to_verdict(lost, fid, ok, landed, to_place, to)
        if here and landed is not None and rec.get("landed") == landed:     # route_to saw the landing: its flip
            after = ring_since(g, int(lost["frame"]))
            out.setdefault("flip_frame", next((int(raw.get("frame", -1)) for _t, raw in after
                                               if int((raw.get("field") or {}).get("id", -1)) != fid), None))
        if verdict == "done":
            out["landed"] = landed
            return "done", out
        if verdict == "left":
            out["misroute"] = {"fld": landed, "place": to_place}
            out["why"] = (f"the door's evidence held at ({lost.get('x')}, {lost.get('z')}) in {fid} and the run landed "
                          f"in {landed} (place {to_place}), not {to}: rule 2's")
            return "left", out
        if verdict == "v13":
            out["landed"] = landed
            out.update(v="V13", by="driver", why=what)
            return "void", out
        if verdict == "v11":
            return self.strayed(step, out, landed, what)
        why = f"control went at ({lost.get('x')}, {lost.get('z')}) without the step's evidence"
        verdict = self.door_loss(step, out, why)
        if verdict is not None:
            return verdict
        out["why"] = why
        return "interrupted", out

    def walkout_record(self, lands) -> None:
        """S14b, THE WALK-OUT ON RECORD (research/o6_design.md 1.2; the driver critic's #5), on the loop's first poll in
        the field a DONE trigger step carrying ``to`` landed in -- rule 1's in an end field, rule 3's at the new visit
        when that field is no end (the review, research/o6_design.md 11.7 #7: a door that leads to no end must not keep
        its row to the run's end, where the ring no longer holds its loss and the end's first sample would be read as
        its landing): that step row (``self.to_row``) updated IN PLACE -- as :meth:`stray` updates a walked row -- from
        the ring since its loss sample: ``walkout``, ``[frame, x, z, control]`` of every sample still in the step's
        field (where ExitField's walk-out took him, and where it stopped); ``flip_frame``, when the executor read none
        (path A: route_to returned before the map switch), the first sample in another field, with ``flip_late`` True
        (False when the executor had one: path B, or the switch waited out); and ``landed_frame``, the first sample in a
        field of ``lands`` (rule 1's: the end fields; rule 3's: the new visit's field; none: an earlier door's row no
        visit has read, recorded before a later door's row takes the handle -- its landing unread, None). Both landing
        paths then carry the loss -> flip -> landing frames."""
        row, self.to_row = self.to_row, None
        lost = row.get("lost") or {}
        if lost.get("frame") is None:
            return
        fld, walk, flip, landed = row.get("field"), [], None, None
        for _t, raw in ring_since(self.g, int(lost["frame"])):
            f = int((raw.get("field") or {}).get("id", -1))
            s = raw_sample(raw)
            if f == fld:
                walk.append([s["frame"], s["x"], s["z"], s["control"]])
                continue
            if flip is None:
                flip = s["frame"]
            if landed is None and f in lands:
                landed = s["frame"]
        row["walkout"] = walk
        row["flip_late"] = row.get("flip_frame") is None
        if row["flip_late"]:
            row["flip_frame"] = flip
        row["landed_frame"] = landed

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

    def x_walk(self, step: dict) -> tuple:
        """S17 (research/o7_design.md 1.2): the walk to the goal, judged by the landing judge first -- the field changed
        -> V11 (driver: strayed); control gone in (or within exit_slack of) a registered exit -> its switch waited out,
        V11 on a landing, else interrupted (door_loss); control gone anywhere else -> interrupted -- then, control held in
        this field within tolerance of the goal and route_to's reached -> done; else failed (blocked, boxed, frozen,
        no route, or short). S20 (research/o8_design.md 1.2), opt-in: with ``at_y`` the arrival is proven on its LEVEL
        too -- his published y at that sample within the band, else failed (an attempt spent, the next re-plans from
        where he stands); the row's ``at_y`` the band and the y read. S21, opt-in: with ``wait_flag``, THE KNIGHT WAIT
        at the proven point (:meth:`wait_flag`) decides the step."""
        g, fid = self.g, self.fid
        wait, tol = float(step["exit_wait_s"]), float(step["tolerance"])
        gx, gz = (float(v) for v in step["goal"])
        rec = g.route_to(gx, gz, tolerance=tol, avoid=polys(self.pred, step.get("avoid")), **self.walk_kw(step))
        out = {"route": trim_route(rec), "lost": rec.get("lost"), "landed": None}
        new = self.left_for(rec, out, "the walk", wait)
        if new is not None:
            return self.strayed(step, out, new, f"the walk left {fid}")
        st = g.state
        if out["lost"] is None and not st.control:
            out["lost"] = sample(st)                         # control went after the call's last read
        if out["lost"] is not None:
            why = "control went during the walk"
            verdict = self.door_loss(step, out, why)
            if verdict is not None:
                return verdict
            out["why"] = why
            return "interrupted", out
        d = None if st.player_x is None else math.hypot(st.player_x - gx, st.player_z - gz)
        if not rec.get("reached") or d is None or d > tol:
            out["why"] = (f"the walk ended " + ("where he stands unknown" if d is None else f"{d:.0f}u from its goal")
                          + f" (reached {rec.get('reached')}, route {out['route'].get('route')}, blocked "
                            f"{rec.get('blocked')}, boxed {rec.get('boxed')}, frozen {rec.get('frozen')})")
            return "failed", out
        band = step.get("at_y")                            # S20 (opt-in): the arrival's height, published y
        if band is not None:
            y = st.player_y
            out["at_y"] = {"band": [float(band[0]), float(band[1])], "y": None if y is None else round(y, 1)}
            if y is None or not float(band[0]) <= y <= float(band[1]):
                out["why"] = (f"the walk ended {d:.0f}u from its goal at published y "
                              + ("unread" if y is None else f"{y:.0f}")
                              + f", outside at_y {list(band)}: not the goal's level")
                return "failed", out
        if step.get("wait_flag") is not None:              # S21 (opt-in): THE KNIGHT WAIT, at the proven point
            return self.wait_flag(step, out)
        return "done", out

    def wait_flag(self, step: dict, out: dict) -> tuple:
        """S21, THE KNIGHT WAIT (research/o8_design.md 1.2): standing at a walk's proven goal with control held, press
        nothing until the watched gEventGlobal bit ``flag`` reads ``value``: ``g.watch(flag)`` (the agent publishes
        ``flags`` every 2 frames: no store, no trace row), ``g.wait_for`` the bit, control gone or another field -- and
        ``g.unwatch()`` in a ``finally``. In order: the run's deadline cut the wait -> V13 by the driver (the budget);
        the field changed -> V11 by the GAME (nothing was pressed: only the game's script moves the field; O8-GOALS
        (g5') proves the wait point clear of every exit); the bit read -> done; control gone -> the landing judge
        (door_loss), else interrupted. The wait RUNS OUT only once BOTH clocks ran ``timeout_s`` -- the wall's and the
        GAME's (``_game_seconds``: the fake's published ``rt``, else the engine's state.json write time, which in game
        IS the wall's): a starved harness stretches the wall's alone, never the game's (the claim review's #5). Run out,
        it is V8 by the GAME only when the window's last sample PUBLISHED the bit -- it latches on the route (O8-CENSUS:
        164's only store to Bit[3811] is e1 t1 ip230 := 1), so its last published value is its value throughout -- and
        V13 by the DRIVER when that sample carried no bit (the watch dropped: AppendWatch publishes ``"flags":{}`` on
        any fault, HarnessAgent.cs:2162-2166 -- the instrument's: the reviews' A4 / B4). The row's ``wait_flag``:
        ``{flag, value, read, frame0, frame, s, game_s, published, last}`` (``published`` the distinct frames that
        carried the bit, ``last`` its last published value)."""
        from harness import HarnessError
        from harness.session import _game_seconds
        g, fid = self.g, self.fid
        wf = step["wait_flag"]
        flag, value, limit = int(wf["flag"]), int(wf["value"]), float(wf["timeout_s"])
        st0, t0 = g.state, time.time()
        c0 = _game_seconds(st0)
        rec = out["wait_flag"] = {"flag": flag, "value": value, "read": None, "frame0": st0.frame, "frame": None,
                                  "s": None, "game_s": None, "published": 0, "last": None}
        seen: set = set()

        def has(s) -> bool:
            v = s.flag(flag)
            if v is not None and s.frame not in seen:       # every sample the wait reads: the bit as published
                seen.add(s.frame)
                rec["last"] = int(v)
            return v is not None and int(v) == value

        def game_ran(s):
            c = _game_seconds(s)
            return None if c is None or c0 is None else c - c0

        st, end = None, None
        g.watch(flag)
        try:
            while end is None:
                left = self.deadline - time.time()
                if left <= 0:
                    end = "deadline"
                    break
                try:
                    st = g.wait_for(lambda s: has(s) or not s.control or s.field_id != fid,
                                    timeout=min(limit, left), what=f"the flag wait: Bit[{flag}] == {value}")
                    end = "event"
                except HarnessError as err:
                    if "live samples" not in str(err):
                        raise
                    st = g.state                        # one read: the window's last sample
                    ran = game_ran(st)
                    if time.time() - t0 >= limit and (ran is None or ran >= limit):
                        end = "out"                     # both clocks ran it (one it cannot read: the wall's)
        finally:
            g.unwatch()
        ran = None if st is None else game_ran(st)
        rec.update(s=round(time.time() - t0, 2), game_s=None if ran is None else round(ran, 2), published=len(seen))
        if end == "deadline":
            out.update(v="V13", by="driver", why=f"the run's budget ran out during the flag wait for Bit[{flag}] == "
                                                 f"{value}, {rec['s']:.1f}s into its {limit:.0f}s: the budget")
            rec["read"] = False
            return "void", out
        if st.field_id != fid:
            new = self.switch(out, "the flag wait", float(step["exit_wait_s"]))
            if new is not None:
                out.update(landed=new, v="V11", by="game",
                           why=f"the field left {fid} during the flag wait, nothing pressed: landed in {new} (place "
                               f"{place(new, self.members)})")
                return "void", out
            st = g.state
        if has(st):
            rec.update(read=True, frame=st.frame)
            return "done", out
        if not st.control:
            out["lost"] = sample(st)
            why = f"control went during the flag wait for Bit[{flag}] == {value}"
            verdict = self.door_loss(step, out, why)
            if verdict is not None:
                return verdict
            out["why"] = why
            return "interrupted", out
        rec["read"] = False                                 # run out on both clocks, control held, the bit unread
        if st.flag(flag) is None:
            out.update(v="V13", by="driver", why=f"the watch never published Bit[{flag}] at the wait's end "
                                                 f"({len(seen)} sample(s) carried it): the instrument's")
        else:
            out.update(v="V8", by="game", why=f"Bit[{flag}] read {int(st.flag(flag))}, never {value}, through "
                                              f"{limit:.0f}s of both clocks of a wait begun at the proven point "
                                              f"(published in {len(seen)} sample(s); the bit latches)")
        return "void", out

    # -- one step -------------------------------------------------------------------------------------------------
    def run_step(self, c: dict, n: int, st) -> None:
        """Run step ``n`` of cell ``c`` (rule 8): its executor, its ``step`` row, the counters (2.3) -- done moves the
        cell on, ``failed`` spends an attempt, ``interrupted`` an interruption, either out of them VOID V7; S14's
        ``left`` (opt-in, research/o6_design.md 1.2) moves nothing and raises nothing, its landing rule 2's on the next
        poll -- and, in a watched cell, the ring's samples of the call as ``watch`` rows."""
        from harness import HarnessError
        step = step_of(self.pred, c["steps"][n])
        key = (self.visit, self.donor, self.sc, n)
        tries = self.tries.setdefault(key, {"failed": 0, "interrupted": 0})
        frame0, t0 = st.frame, time.time()
        try:
            verdict, rec = getattr(self, "x_" + step["kind"])(step)
        except HarnessError as err:
            # S19 (research/o7_design.md 1.2): a seeded prior basis the first move disagreed with -- keyed on the ERROR's
            # marker alone, whatever the step's keys (a step with no ``basis`` judges a seed an earlier step left
            # pending): the driver's instrument, V13 on this step's row. Only a seeded field can raise the marker, and
            # O1-O6 never seed: every other HarnessError propagates exactly as before.
            prior_basis = getattr(err, "prior_basis", None)
            if prior_basis is None:
                raise
            verdict, rec = "void", {"v": "V13", "by": "driver", "prior_basis": prior_basis,
                                    "why": f"the prior basis disagreed with the first move: {err}"}
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
        for key in ("clearance", "basis"):       # S18/S19 (opt-in): on the row only when the step carries them
            if step.get(key) is not None:
                row[key] = step[key]
        for key in ("at_y", "wait_flag"):        # S20/S21 (opt-in): the arrival's height, the wait -- the executor's
            if rec.get(key) is not None:
                row[key] = rec[key]
        if rec.get("prior_basis") is not None:   # S19: the first move's disagreement, on the V13 row that names it
            row["prior_basis"] = rec["prior_basis"]
        if rec.get("misroute") is not None:      # S14 (opt-in): the landing after a door's evidence held -- rule 2's
            row["misroute"] = rec["misroute"]
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
            if step["kind"] == "trigger" and step.get("to") is not None:
                if self.to_row is not None:      # S14b: an earlier door's row no visit has read (the review, 11.7 #7):
                    self.walkout_record(())      # its walk-out recorded, its landing unread -- never overwritten
                self.to_row = row                # S14b: rule 1 (an end) or rule 3 (a new visit) puts its walk-out on it
        elif verdict == "left":                  # S14 (opt-in): no beat, no raise -- rule 2 judges the landing
            pass
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
        t = round(time.time() - self.visit_t0, 2)         # the row's t, and the t its left_s is computed from:
        self.walked = None                                   # the row reads the same to anyone who recomputes it
        crow = {"k": "choice", "field": self.fid, "donor": self.donor, "sc": self.sc, "frame": st.frame,
                "options": ch.get("options"), "active": ch.get("active"), "selected": ch.get("selected"),
                "count": ch.get("count"), "index": index, "rule": "movie_skip", "took": {"index": index}}
        self.choices.append(crow)
        self.log.append(crow)
        span = row.get("next_page_s")
        row.update(dialog=snap, frame=st.frame, t=t, left_s=None if span is None else round(float(span) - t, 1))
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
            if self.chanbara is not None or self.witness_pol is not None:     # S7 / S12, opt-in: outside input V13
                self.poll_witness(st)
            # 1 -- the end: the end state, the last scan, done -- and, opt-in, the end place's first trace row waited for
            if self.fid in self.ends:
                self.end_state = read_end_state(g, pred)
                if self.forbid_live:
                    self.scan()
                if self.to_row is not None:          # S14b (opt-in): the done door step's walk-out, flip and landing
                    self.walkout_record(self.ends)
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
            # 2 -- the route: a field on it, and (at a new visit) the place its order goes to next. S6, opt-in (with
            # ``side_ends``): on F a REAL field the chain forks is V19, the game's -- a Field() the build did not
            # retarget, or an engine id leak: a finding; anything else off the route stays V11 (stray)
            if not on_route(self.fid, self.members, self.route, self.ends):
                due = [f for f, d in sorted(self.members.items()) if d == self.fid] \
                    if self.side_ends is not None and self.fid not in self.members else []
                if due:
                    raise self.void("V19", "game", f"the fork run entered REAL {self.fid}, where member({self.fid}) "
                                                   f"{due[0]} was due: a Field() the chain did not retarget")
                raise self.stray(f"left the route: entered {self.fid} (place {self.donor})")
            # 3 -- a new visit
            if self.fid != self.cur:
                want = self.order[self.at + 1] if self.at + 1 < len(self.order) else None
                if self.donor != want:
                    raise self.stray(f"out of the route's order: entered {self.fid} (place {self.donor}), where the "
                                     f"route goes next to {want}")
                if self.pw is not None:              # S16: a new visit -- the armed field's last scan, then disarmed
                    self.page_witness(final=True)
                if self.to_row is not None:          # S14b (opt-in): a done door's landing in a field that is no end
                    self.walkout_record({self.fid})  # (the review, research/o6_design.md 11.7 #7)
                self.at += 1
                self.walked = None
                self.visit, self.cur = self.visit + 1, self.fid
                self.log.append({"k": "visit", "field": self.fid, "donor": self.donor, "visit": self.visit,
                                 "frame": st.frame, "sc": self.sc})
                if self.chanbara is not None:        # the policy's state is a visit's
                    self.cb_reset(st)
                if self.guard is not None:           # S10: and so is the guard's
                    self.guard_reset(st)
                if self.movies is not None:          # the policy's clock: a cell's after_s counts from the visit
                    self.movie_close("the visit ended with no skip dialog")
                    self.visit_t0 = time.time()
                if self.forbid_live:
                    self.scan()
            c = cell(pred, self.donor, self.sc, self.at + 1)           # S13: a visit-scoped cell answers its visit
            if c is not None and c.get("watch"):
                self.watch_poll(st, c)
            if self.chanbara is not None:            # S8 c, opt-in: the quiet window opens, or runs out (V14)
                self.quiet_tick()
            if self.guard is not None:               # S10, opt-in: the quiet window opens, a choice closes it, or V13
                self.guard_quiet_tick(st)
            # 3b -- THE PAGE WITNESS (S16, opt-in: armed by rule 4 under a registration's ``on_page``)
            if self.pw is not None:
                self.page_witness()
            # 4 -- the naming screen
            if st.ui_state == "NameSetting":
                self.held = 0
                reg = next((x for x in self.naming if x["donor"] == self.donor and x["sc"] == self.sc), None)
                if reg is None:
                    raise self.void("V10", "game", f"a naming screen in {self.fid} (place {self.donor}) at SC "
                                                   f"{self.sc}, where the route registers none")
                page = reg.get("on_page")
                before = None if page is None else self.last_listed(st.frame)    # S16: read before the Confirms
                g.accept_name()
                self.walked = None
                if reg.get("beat"):
                    self.beats[reg["beat"]] = True
                row = {"k": "named", "field": self.fid, "donor": self.donor, "sc": self.sc, "frame": st.frame}
                if page is not None:                 # S16: what came before the screen, and the page witness armed
                    row["before"] = before
                    self.pw = {"tag": page["tag"], "beat": page["beat"], "windows": page["windows"],
                               "frame": st.frame, "field": self.fid, "donor": self.donor, "visit": self.visit,
                               "cell": self.vcell(self.donor, self.sc), "scanned": st.frame}
                self.log.append(row)
                continue
            # 5 -- a tutorial or a battle: the route registers neither
            if st.ui_state == "Tutorial" or st.in_battle:
                raise self.void("V10", "game", f"{'a battle' if st.in_battle else 'a tutorial'} in {self.fid} "
                                               f"(place {self.donor}) at SC {self.sc}, where the route registers none")
            # 6 -- a choice: O1's readiness hold, then the frozen rules
            if st.choice is not None:
                self.held = 0
                if self.chanbara is not None:        # S9, opt-in: its first frame kept; the quiet window closed
                    self.note_choice(st)
                if self.guard is not None:           # S10, opt-in: the same, for the guarded choice
                    self.guard_note_choice(st.choice, st.frame)
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
            # 6b -- THE FIGHT ZONE (opt-in: ``chanbara``; research/o4_design.md 2.4): a published prompt or the zone
            # start (111) in the policy's cell -- its place, its published SC, control off -- and the executor owns the
            # loop until the zone ends; one anywhere else is V17 with nothing pressed (game-observed). BEFORE rule 7,
            # whose Confirm is the Cross bit: a wrong key on 7 of 8 prompts
            if self.chanbara is not None and self.zone_line(st):
                self.held = 0
                if self.in_cell(st):
                    _ChanbaraZone(self, st).run(st)
                    continue
                self.observed("prompt_outside_cell", st)
                raise self.void("V17", "driver", f"a prompt outside the policy's cell (place {self.donor}, SC "
                                                 f"{self.sc}), nothing pressed: {st.text[:120]!r}")
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
                if self.chanbara is not None:        # S8, S9, opt-in: page-once, the quiet window, the two-sample pages
                    self.policy_page(st)
                    continue
                if self.guard is not None:           # S10, opt-in: the judgment, the gone choice, the quiet window,
                    self.guard_page(st)              # page-once on the marker page; every press with its seq
                    continue
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
        taken for a ``take: "default"`` rule (the cursor never moved) or O1's ``choose`` -- under the guard (S11) the
        VERIFIED landing (:meth:`answer_landed`) -- and its ``choice`` row. A default whose Confirm did not land is
        asked again on a later poll, never counted answered. Under the guard the guarded rule asked again after its
        verified answer is V2, the game's, outright (:meth:`guard_stray` "choice_reask")."""
        g = self.g
        try:
            index, rule = pick_for(st.choice, self.donor, self.pred, sc=self.sc, answered=self.answered)
        except RouteVoid as err:
            if err.v is None:
                raise self.void("V1", "game", str(err)) from err
            if err.v == "V2" and self.chanbara is not None and self.encore_rule(st) is not None:
                self.encore_stray()                  # S9: a second encore -- who confirmed it, V17 or V2
            if err.v == "V2" and self.guard is not None and self.is_guard_choice(st.choice):
                self.guard_stray("choice_reask", st)     # S10: V2 (game) outright, logged with the guard row
            if self.visit_cells:                     # S13: pick_for's own V2 / V3 cell gains the visit
                err.cell = self.vcell(self.donor, self.sc)
            raise
        n = next(i for i, r in enumerate(self.pred["choices"]) if r is rule)
        if index == "default" or rule.get("take") == "default":
            took = g._take_default_choice(st)
            if took is None:
                return
        elif self.guard is not None:                 # S11, opt-in: the verified landing, rowed and witnessed
            took = self.answer_landed(st, index, rule)
        else:
            before = g.channel.seq
            g.choose(index)
            took = {"index": index}
            if self.chanbara is not None:            # S9, opt-in: choose's own presses, rowed with their seqs
                self.row_choose(before, g.channel.seq, st)
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
        if self.chanbara is not None and rule.get("match") == self.chanbara["encore_match"]:
            key = str((ch.get("options") or [""])[0])            # S9: the encore answered -- its first page is judged
            self.cb["encore"] = {"key": key, "first_frame": self.cb["choice_first"].get(key, st.frame),
                                 "answered_frame": st.frame, "close_frame": None, "judged": False}

    # -- S7-S9: the Chanbara policy (opt-in: ``chanbara``; research/o4_design.md 2.4) ----------------------------------
    def cb_reset(self, st) -> None:
        """A new visit's policy state: no zone yet, no score read, no page held off, no quiet window, no choice seen, no
        encore answered."""
        self.cb = {"zone_done": False, "zone_end_frame": None, "score_read": False, "held_off": {}, "quiet": None,
                   "choice_first": {}, "encore": None, "visit_frame": st.frame}

    def in_cell(self, st) -> bool:
        """The policy's cell: its place and published SC, control off (2.4.1)."""
        pol = self.chanbara
        return self.donor == pol["donor"] and self.sc == pol["sc"] and not st.control

    def zone_line(self, st) -> bool:
        """A published ``phrase_raw`` line that is a prompt or the zone start (rule 6b)."""
        lines = [p for p, _t in dialog_rows(st.raw)]
        return any(prompt_dbtn(p) for p in lines) or is_zone_start(lines, self.chanbara)

    def observed(self, kind: str, src) -> dict:
        """An ``observed`` row (2.4.6; rev. 2, the claim critique #5): logged just before a V17 whose cause is something
        the GAME showed -- ``{"k": "observed", "kind", "cell", "frame", "texts", "phrase_raw"}`` (and the choice, when
        one was published). VOID-ASYM (d) reads them. Its cell is the VOID's (S13: :meth:`vcell`)."""
        if isinstance(src, dict):
            frame, rows, choice = src["frame"], src["dialogs"], src.get("choice")
        else:
            frame, rows, choice = src.frame, dialog_rows(src.raw), src.choice
        row = {"k": "observed", "kind": kind, "cell": self.vcell(self.donor, self.sc), "frame": frame,
               "texts": [t for _p, t in rows], "phrase_raw": [p for p, _t in rows]}
        if choice is not None:
            row["choice"] = choice
        self.log.append(row)
        return row

    def poll_witness(self, st, *, now_too: bool = False) -> None:
        """The outside-input witness (2.4.3 step 0), polled between the main loop's own blocking calls, at most
        every ``input_every_s`` -- the run-wide policy's (S12) or the Chanbara policy's -- and at once with ``now_too``
        (S11: right after a verified answer): a non-neutral reading is an ``input`` row, then V13 -- the instrument's,
        wherever it falls."""
        from harness import HarnessError
        if self.witness is None:
            return
        now = time.time()
        if not now_too and now - self.witness_t < float(self.witness_every):
            return
        self.witness_t = now
        what = self.witness()
        if what:
            self.log.append({"k": "input", "t": round(now - self.t0, 3), "frame": st.frame, "what": str(what)})
            raise HarnessError(f"outside input: {what}")

    def quiet_tick(self) -> None:
        """S8 c, THE QUIET WINDOW (2.4.11; rev. 2): armed once a window holding a ``quiet`` marker was pressed, it OPENS
        at the first merged sample without any such window (a first press dropped in the page's opening leaves it up,
        and page-once presses it again); open, nothing is pressed until a choice is published, a page is V17 (rule 7),
        and no choice within ``quiet_cap_s`` of its opening is V14 (game)."""
        q = (self.cb or {}).get("quiet")
        if q is None:
            return
        pol = self.chanbara
        if q["open_frame"] is None:
            for raw in self.g.states_since(q["armed_frame"]):
                if not any(m in t for _p, t in dialog_rows(raw) for m in pol["quiet"]):
                    q["open_frame"], q["open_t"] = int(raw.get("frame", -1)), time.time()
                    self.log.append({"k": "quiet", "field": self.fid, "visit": self.visit,
                                     "open_frame": q["open_frame"], "armed_frame": q["armed_frame"]})
                    break
        elif time.time() - q["open_t"] > float(pol["quiet_cap_s"]):
            raise self.void("V14", "game", f"no choice within {float(pol['quiet_cap_s']):g} s of the quiet window's "
                                           f"opening (frame {q['open_frame']})")

    def note_choice(self, st) -> None:
        """S9: a published choice closes the quiet window, and its FIRST publication in this visit is kept (the ring's
        earliest sample of it) -- the encore attribution's window opens there."""
        cb = self.cb
        cb["quiet"] = None
        key = str((st.choice.get("options") or [""])[0])
        if key in cb["choice_first"]:
            return
        first = st.frame
        for raw in self.g.states_since(cb["visit_frame"]):
            ch = (raw.get("dialog") or {}).get("choice")
            if ch and str((ch.get("options") or [""])[0]) == key:
                first = int(raw.get("frame", st.frame))
                break
        cb["choice_first"][key] = first

    def policy_page(self, st) -> None:
        """RULE 7 UNDER THE POLICY (S8, S9; research/o4_design.md 2.2 rule 7, 2.4.11, 2.4.12), after the stop pages:
        (S8 a) a page in the policy's cell whose ``phrase_raw`` holds ``[DBTN=`` and is not the zone start is V17,
        nothing pressed (game-observed); (S8 c) a page while the quiet window is open is V17 (game-observed); (S9) the
        first page after the encore answer is judged by what it is (:meth:`after_encore`), the first score page after
        the zone is read in two consecutive samples (:meth:`score_page`) -- each waits for its reading; (S8 b)
        PAGE-ONCE, per window: Confirm only while some listed window's own text is not held off -- a text pressed is
        held off until ``page_once_ticks`` past that press's ack-read frame -- the press row carrying its ``seq``,
        ``ack_frame`` and the texts it pressed; a pressed window holding a ``quiet`` marker arms the quiet window. Then
        O1's wait."""
        g, pol, cb = self.g, self.chanbara, self.cb
        rows = dialog_rows(st.raw)
        lines, texts = [p for p, _t in rows], [t for _p, t in rows]
        cell = self.donor == pol["donor"] and self.sc == pol["sc"]
        if cell and any("[DBTN=" in p for p in lines) and not is_zone_start(lines, pol):
            self.observed("unrecognized_dbtn", st)
            raise self.void("V17", "driver", f"a [DBTN= page neither recognizer claims, nothing pressed: "
                                             f"{st.text[:120]!r}")
        q = cb.get("quiet")
        if q is not None and q.get("open_frame") is not None:
            self.observed("quiet_page", st)
            raise self.void("V17", "driver", f"a page in the quiet window, nothing pressed: {st.text[:120]!r}")
        if cb.get("encore") is not None and not cb["encore"]["judged"]:
            if not self.after_encore(st, rows):
                time.sleep(POLL_S)
                return
        elif cell and cb["zone_done"] and not cb["score_read"] and any(SCORE_MARK in t for t in texts):
            if not self.score_page():
                time.sleep(POLL_S)
                return
        held = cb["held_off"]
        if not any(t and st.frame >= held.get(t, -1) for t in texts):
            time.sleep(POLL_S)                     # page-once: every listed window was pressed lately
            return
        if not self.pages or self.pages[-1] != st.text:
            self.pages.append(st.text)
            if any("[TIME=" in t for t in st.raw_texts):
                self.timed.append(len(self.pages) - 1)
        if self.movies is not None:
            self.movie_page(st)
        row = self.press("page", st, 3)
        seq = g.channel.seq
        st2 = g.state
        until = st2.frame + g.rate().frames_for_ticks(int(pol["page_once_ticks"]))
        row.update(seq=seq, ack_frame=st2.frame, button="confirm", texts=[t for t in texts if t])
        for t in texts:
            if t:
                held[t] = until
        if cb.get("quiet") is None and any(m in t for t in texts for m in pol["quiet"]):
            cb["quiet"] = {"armed_frame": st.frame, "open_frame": None, "open_t": None}
        self.walked = None
        g.wait_frames(g.rate().frames_for_ticks(g.CUTSCENE_PAGE_TICKS))

    def page_samples(self, match, since: int) -> list:
        """The page's text in each consecutive merged sample after ``since`` (the ring's), in frame order: the first
        window text ``match`` holds, or None for a sample that lists none."""
        out = []
        for raw in self.g.states_since(since):
            hits = [t for _p, t in dialog_rows(raw) if match(t)]
            out.append(hits[0] if hits else None)
        return out

    def score_page(self) -> bool:
        """S9: the first page of the cell after the zone holding "nobles watching", read in TWO consecutive samples
        (2.4.12; [NUMB] is filled in when it renders, 0.3 #6): ``score_page`` -- the beat ``sword`` set, True (press
        it); another number -- the fight's judge stops the run (:meth:`page_stop`); no reading yet -- False (wait)."""
        got = self.page_samples(lambda t: SCORE_MARK in t, self.cb["zone_end_frame"] or self.cb["visit_frame"])
        verdict, _text = page_reading(got, self.chanbara["score_page"])
        if verdict is None:
            return False
        if verdict == "differs":
            self.page_stop("score", got)
        self.cb["score_read"] = True
        if "sword" in self.beats:
            self.beats["sword"] = True
        return True

    def after_encore(self, st, rows: list) -> bool:
        """S9: THE FIRST PAGE AFTER THE ENCORE ANSWER, judged by what it is (2.4.12; rev. 2, the claim critique #8): a
        gil page ("They shower you with") read in two consecutive samples -- ``gil_page``: True (press it); another
        number: the fight's judge (:meth:`page_stop`); no reading yet: False (wait); a REPLAY page -- the replay's KEYON
        pair, 64 mes 109/110, ``[TIME=-1]`` and no ``[DBTN=`` -- goes to :meth:`encore_stray` (V17 or V2); anything else
        is V17 (game-observed)."""
        enc = self.cb["encore"]
        if any(GIL_MARK in t for _p, t in rows):
            got = self.page_samples(lambda t: GIL_MARK in t, enc["answered_frame"])
            verdict, _text = page_reading(got, self.chanbara["gil_page"])
            if verdict is None:
                return False
            if verdict == "differs":
                self.page_stop("gil", got)
            enc["judged"] = True
            return True
        if any("[TIME=-1]" in p and "[DBTN=" not in p for p, _t in rows):
            self.encore_stray()
        self.observed("after_encore", st)
        raise self.void("V17", "driver", f"a page after the encore answer that is neither the gil page nor a replay, "
                                         f"nothing pressed: {st.text[:120]!r}")

    def page_stop(self, kind: str, texts: list) -> None:
        """A score or gil page that reads another text in two samples: the fight's judge over this visit's zone and
        prompt rows (2.4.8) -- V18 when the play is proven, V17 otherwise -- logged, nothing pressed."""
        pol = self.chanbara
        zone = next((z for z in reversed(self.zones) if z.get("visit") == self.visit), {})
        prompts = [r for r in self.prompts if r.get("visit") == self.visit]
        presses = [r for r in self.log if r.get("k") == "press" and r.get("seq") is not None
                   and r.get("visit") == self.visit]
        verdict = chanbara_judge(zone, prompts, presses, pol,
                                 page={"kind": kind, "want": pol[f"{kind}_page"], "texts": texts})
        v, by, why = verdict["v"], verdict["by"], verdict["why"]
        if v is None:
            v, by, why = "V17", "driver", f"the {kind} page differs and the judge read no finding"
        self.log.append({"k": "page_judge", "kind": kind, "field": self.fid, "visit": self.visit,
                         "texts": [t for t in texts if t][-4:], "verdict": verdict})
        raise self.void(v, by, why)

    def encore_rule(self, st) -> dict | None:
        r = rule_for(st.choice, self.donor, self.pred, sc=self.sc)
        return r if r is not None and r.get("match") == self.chanbara["encore_match"] else None

    def steps_rows(self) -> list:
        """The session's steps.jsonl rows (every request's literal steps by ``seq``), [] when there is none."""
        path = getattr(self.g, "run_dir", None)
        path = None if path is None else path / "steps.jsonl"
        if path is None or not path.exists():
            return []
        out = []
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
        return out

    def choice_close(self, enc: dict) -> int | None:
        """The first merged sample after the encore choice's first publication that no longer lists it, or None."""
        for raw in self.g.states_since(enc["first_frame"]):
            ch = (raw.get("dialog") or {}).get("choice")
            if not ch or str((ch.get("options") or [""])[0]) != enc["key"]:
                return int(raw.get("frame", -1))
        return None

    def encore_stray(self) -> None:
        """S9: a replay page or a second encore choice -- who confirmed it (2.4.11, :func:`stray_answer`): V17 when a
        Confirm of the driver's own landed on 127 other than the answer's own on a cursor at No, else V2 (game). Never
        the fight's judge. Logged, then raised with the cell."""
        enc = self.cb["encore"]
        if enc.get("close_frame") is None:
            enc["close_frame"] = self.choice_close(enc)
        log = [r for r in self.log if r.get("visit") == self.visit]
        res = stray_answer(log, self.g.channel.events(), self.steps_rows(), enc["first_frame"], enc["close_frame"])
        self.log.append({"k": "encore_stray", "field": self.fid, "visit": self.visit, "first_frame": enc["first_frame"],
                         "close_frame": enc["close_frame"], **res})
        raise RouteVoid(res["why"], v=res["v"], cell=self.vcell(self.donor, self.sc), by=res["by"])

    def row_choose(self, before: int, after: int, st) -> None:
        """S9 (research/o4_design.md 0.3 #10): ``g.choose``'s own presses -- ``press down/up 4`` until the cursor sits,
        then ``press confirm 4`` -- as ``press`` rows (``why`` "choose"), the requests between the channel's seq before
        and after it: each from the session's steps.jsonl, its accepted frame from events.jsonl (its down frame + 1),
        the confirm marked ``answer`` and given the cursor the last ring sample before its down frame published
        (``selected_before``) -- what :func:`stray_answer` reads."""
        steps = {int(r["seq"]): r for r in self.steps_rows()
                 if r.get("seq") is not None and before < int(r["seq"]) <= after}
        acc: dict = {}
        for e in self.g.channel.events():
            if e.get("kind") == "accepted" and e.get("seq") is not None:
                try:
                    acc.setdefault(int(e["seq"]), int(e["frame"]))
                except (TypeError, ValueError):
                    continue
        presses = [(seq, _press_button(steps[seq].get("steps"))) for seq in sorted(steps)]
        presses = [(seq, b) for seq, b in presses if b]
        last = max((seq for seq, b in presses if b in CONFIRM_NAMES), default=None)
        ring = self.g.states_since(st.frame - 1)
        for seq, button in presses:
            down = None if acc.get(seq) is None else acc[seq] + 1
            sel = None
            if down is not None:
                prior = [raw for raw in ring if int(raw.get("frame", -1)) < down]
                ch = (prior[-1].get("dialog") or {}).get("choice") if prior else None
                sel = None if not ch else ch.get("selected")
            self.log.append({"k": "press", "why": "choose", "button": button, "seq": seq, "field": self.fid,
                             "donor": self.donor, "visit": self.visit, "sc": self.sc, "pre": None, "post": None,
                             "near": [], "accepted_frame": acc.get(seq), "down_frame": down, "selected_before": sel,
                             "answer": seq == last})

    # -- S10-S11: the pre-choice guard and the verified answer (opt-in: ``guard``; research/o5_design.md 1.2) ----------
    def guard_reset(self, st) -> None:
        """A new visit's guard state (rule 3): no choice seen, none answered, no quiet window, nothing held off."""
        self.gd = {"visit_frame": st.frame, "seen_frame": st.frame, "first": None, "answered": False, "answer": None,
                   "quiet": None, "rearms": 0, "held": {}, "last_ack": None, "judged": False, "row": None}

    def has_marker(self, s) -> bool:
        """Whether a window's raw or text holds one of the guard's markers."""
        return any(m in str(s or "") for m in self.guard["markers"])

    def lists_marker(self, raw: dict) -> bool:
        """Whether a published sample lists a MARKER WINDOW: a marker in some window's ``phrase_raw`` or its text."""
        return any(self.has_marker(p) or self.has_marker(t) for p, t in dialog_rows(raw))

    def is_guard_choice(self, choice) -> bool:
        """Whether a published choice is the guarded one: the frozen rule that answers it here is the guard's."""
        return bool(choice) and rule_for(choice, self.donor, self.pred, sc=self.sc) is self.guard_rule

    def guard_note_choice(self, choice, frame: int) -> None:
        """Rule 6 under the guard (S10): a published choice closes the quiet window; the GUARDED choice's first
        publication is kept (``gd["first"]``: the ring's earliest sample of it since the visit's first frame)."""
        gd = self.gd
        q = gd["quiet"]
        if q is not None and not q["closed"]:
            q.update(closed=True, close_frame=frame)
        if gd["first"] is not None or not self.is_guard_choice(choice):
            return
        first = frame
        for raw in self.g.states_since(gd["visit_frame"]):
            if self.is_guard_choice((raw.get("dialog") or {}).get("choice")):
                first = min(first, int(raw.get("frame", frame)))
                break
        gd["first"] = first

    def guard_quiet_tick(self, st) -> None:
        """S10, every poll (rule 3's place, where O4 runs ``quiet_tick``): THE QUIET WINDOW, then the guarded choice.
        Armed and not open: the first ring sample after it was armed (or re-armed) listing no marker window OPENS it
        (``open_frame``; ``open_game`` that sample's game clock). Open: FIRST the ring since the opening and the current
        sample are scanned, and one publishing a choice closes it (rule 6 answers it on this poll) -- a stalled read
        never meets the cap with the choice already up; only then the cap: no choice within ``quiet_cap_s`` of the game
        clock since ``open_game`` (``rt``, else the state file's write time: on the engine a wall clock, 0.2 #17), or
        within 10 x ``quiet_cap_s`` of wall time, is V13 -- the instrument's, never the game's. Last, the guarded choice
        published between the driver's own polls (a blocking call's reads: the ring's) is noted as rule 6 notes the
        one it reads -- a choice up and gone unread by rule 6 still reads as published."""
        gd, pol = self.gd, self.guard
        q = gd["quiet"]
        if q is not None and not q["closed"]:
            if q["open_frame"] is None:
                for raw, mtime in _ring_reads(self.g, q["from"]):
                    if not self.lists_marker(raw):
                        q.update(open_frame=int(raw.get("frame", -1)), open_t=time.time(),
                                 open_game=list(_game_t({"rt": raw.get("rt"), "mtime": mtime})))
                        self.log.append({"k": "quiet", "field": self.fid, "visit": self.visit,
                                         "armed_frame": q["armed_frame"], "open_frame": q["open_frame"],
                                         "open_game": q["open_game"], "rearms": gd["rearms"]})
                        break
            if q["open_frame"] is not None:
                for raw in [*self.g.states_since(q["open_frame"] - 1), st.raw]:
                    ch = (raw.get("dialog") or {}).get("choice")
                    if ch is not None:
                        self.guard_note_choice(ch, int(raw.get("frame", st.frame)))
                        break
                if not q["closed"]:
                    cap = float(pol["quiet_cap_s"])
                    kind, now = _game_t({"rt": st.raw.get("rt"), "mtime": st.mtime})
                    k0, t0 = q["open_game"]
                    if (kind is not None and kind == k0 and now - t0 > cap) or time.time() - q["open_t"] > 10 * cap:
                        raise RouteVoid(f"no choice read within {cap:g} s of the quiet window's opening (frame "
                                        f"{q['open_frame']}): the instrument's", v="V13",
                                        cell=self.vcell(self.donor, self.sc), by="driver")
        if gd["first"] is None:
            for raw in self.g.states_since(gd["seen_frame"]):
                ch = (raw.get("dialog") or {}).get("choice")
                if self.is_guard_choice(ch):
                    self.guard_note_choice(ch, int(raw.get("frame", st.frame)))
                    break
        gd["seen_frame"] = max(gd["seen_frame"], st.frame)

    def guard_page(self, st) -> None:
        """RULE 7 UNDER THE GUARD (S10; research/o5_design.md 1.2, 2.5), after the stop pages and ``no_pages``, in order:
        (o) THE JUDGMENT, once, at the first page after the guarded choice's VERIFIED answer (:meth:`guard_judge`):
        anything but "ok" VOIDs the run with nothing pressed, "ok" goes on to (iv); (i) the guarded choice published and
        gone with no answer of the driver's -- judged on a page sample NEWER than the choice's first publication: an
        older one (a stale read, served after a blocking call's own reads already met the choice) shows nothing of its
        going, and goes on to (ii)-(iv), page-once's hold-off holding a stale marker page off (research/o5_design.md
        11.5, PART B) -- :meth:`guard_stray` "choice_gone"; (ii) the quiet window OPEN -- a page
        holding a marker is the marker page itself (a sample listing no window opened it early: the agent's
        dialog-section catch, 0.2 #18), so the window RE-ARMS and the page goes on to (iii); any other page is V17
        (game-observed: an ``observed`` row ``quiet_page``), nothing pressed; (iii) in the guard's cell, a page listing
        a marker window -- PAGE-ONCE: pressed only when some marker window's ``phrase_raw`` is not held off (a pressed
        raw is held off until its press's ack-read frame + ``page_once_ticks``) AND the sample's frame is past the
        hold-off of the driver's LAST press of any kind (2.5.5: a press on the page before can go down on the marker
        page and close it, and its close-tween samples carry a raw page-once never held off); its first press ARMS the
        quiet window; (iv) any other page: O1's rule 7. Every press a row with ``seq``, ``ack_frame``, ``raws`` and
        ``marker`` (:meth:`guard_press`)."""
        gd, pol = self.gd, self.guard
        rows = dialog_rows(st.raw)
        if gd["answered"] and not gd["judged"]:
            self.guard_judge(st, rows)                           # (o): raises unless "ok"
            self.guard_press(st, rows, marker=False)
            return
        if gd["first"] is not None and not gd["answered"] and st.frame > gd["first"]:
            self.guard_stray("choice_gone", st)                  # (i): raises
        marked = [(p, t) for p, t in rows if self.has_marker(p) or self.has_marker(t)]
        q = gd["quiet"]
        if q is not None and not q["closed"] and q["open_frame"] is not None:        # (ii)
            if not marked:
                self.observed("quiet_page", st)
                raise self.void("V17", "driver", f"a page in the quiet window, nothing pressed: {st.text[:120]!r}")
            gd["rearms"] += 1
            q.update({"open_frame": None, "open_game": None, "open_t": None, "from": st.frame})
            self.log.append({"k": "quiet", "field": self.fid, "visit": self.visit, "rearm": gd["rearms"],
                             "frame": st.frame, "armed_frame": q["armed_frame"]})
        if marked and self.donor == pol["donor"] and self.sc == pol["sc"] and not st.control:  # (iii)
            hold = self.g.rate().frames_for_ticks(int(pol["page_once_ticks"]))
            free = [p or t for p, t in marked if st.frame >= gd["held"].get(p or t, -1)]
            if not free or (gd["last_ack"] is not None and st.frame < gd["last_ack"] + hold):
                time.sleep(POLL_S)                               # held off: it, or any page, was pressed lately
                return
            self.guard_press(st, rows, marker=True)
            if gd["quiet"] is None:
                gd["quiet"] = {"armed_frame": st.frame, "from": st.frame, "open_frame": None, "open_game": None,
                               "open_t": None, "closed": False, "close_frame": None}
            return
        self.guard_press(st, rows, marker=False)                 # (iv)

    def guard_press(self, st, rows: list, *, marker: bool) -> dict:
        """A page press under the guard: O1's rule 7 -- the page recorded, Confirm, O1's wait -- its row carrying
        ``seq``, ``ack_frame`` (the read right after the press returns: O4's policy_page shape), ``raws`` (the listed
        windows' ``phrase_raw``) and ``marker``; ``gd["last_ack"]`` the latest ack frame of the visit; a MARKER press
        holds off every window it listed, by its raw, until its ack frame + ``page_once_ticks``."""
        g, gd = self.g, self.gd
        if not self.pages or self.pages[-1] != st.text:
            self.pages.append(st.text)
            if any("[TIME=" in t for t in st.raw_texts):
                self.timed.append(len(self.pages) - 1)
        if self.movies is not None:
            self.movie_page(st)
        row = self.press("page", st, 3)
        seq = g.channel.seq
        st2 = g.state
        row.update(seq=seq, ack_frame=st2.frame, button="confirm", raws=[p for p, _t in rows], marker=marker)
        gd["last_ack"] = st2.frame if gd["last_ack"] is None else max(gd["last_ack"], st2.frame)
        if marker:
            until = st2.frame + g.rate().frames_for_ticks(int(self.guard["page_once_ticks"]))
            for p, t in rows:
                if p or t:
                    gd["held"][p or t] = until
        self.walked = None
        g.wait_frames(g.rate().frames_for_ticks(g.CUTSCENE_PAGE_TICKS))
        return row

    def guard_row(self, st, rows: list) -> dict:
        """THE ``guard`` ROW (S10), from the visit's own record: the quiet window's arming, opening and re-arms; the
        marker page's LAST listed sample before the guarded choice's first (``marker_last``, the ring's); the choice's
        first publication, its readiness (the first sample with the group ``Dialog.Choice``) and its CLOSE (the first
        sample after it with no choice block while the menu group is not ``Dialog.Choice``: a sample with no choice but
        that group is the agent's dialog-section catch, 0.2 #18); the answer's seq span and the marker page's closing
        press; every press of the visit with a ``seq`` -- its accepted frame joined from ONE events read -- and the
        strays in [``marker_last``, the close) (:func:`guard_strays`, :func:`guard_exclude`); the branch the page ``st``
        holds (``rows``: its dialog rows). Its ``verdict`` is the caller's."""
        g, gd, pol = self.g, self.gd, self.guard
        first, q = gd["first"], gd["quiet"] or {}
        fr = [(int(raw.get("frame", -1)), raw) for raw in g.states_since(gd["visit_frame"])]
        marker_last = None if first is None else max((f for f, raw in fr if f < first and self.lists_marker(raw)),
                                                     default=None)
        choice_ready = choice_close = None
        for f, raw in fr if first is not None else ():
            if f < first:
                continue
            ch, group = (raw.get("dialog") or {}).get("choice"), (raw.get("menu") or {}).get("group")
            if choice_ready is None and ch is not None and group == g.CHOICE_GROUP:
                choice_ready = f
            if f > first and ch is None and group != g.CHOICE_GROUP:
                choice_close = f
                break
        events = list(g.channel.events())
        acc: dict = {}
        for e in events:
            if e.get("kind") == "accepted" and e.get("seq") is not None:
                try:
                    acc.setdefault(int(e["seq"]), int(e["frame"]))
                except (TypeError, ValueError):
                    continue
        mine = [r for r in self.log if r.get("k") == "press" and r.get("seq") is not None
                and r.get("visit") == self.visit]
        presses = [{"seq": int(r["seq"]), "why": r.get("why"), "marker": bool(r.get("marker")),
                    "accepted_frame": acc.get(int(r["seq"])),
                    "down_frame": None if acc.get(int(r["seq"])) is None else acc[int(r["seq"])] + 1,
                    "decision_frame": (r.get("pre") or {}).get("frame"), "raws": r.get("raws")} for r in mine]
        closing = max((p["seq"] for p in presses if p["marker"]), default=None)
        strays = guard_strays(mine, events, self.steps_rows(), marker_last, choice_close,
                              exclude=guard_exclude(gd["answer"], closing))
        pick, other = pol["branch"]
        holds = (lambda m: any(m in p or m in t for p, t in rows))
        return {"k": "guard", "field": self.fid, "visit": self.visit, "armed_frame": q.get("armed_frame"),
                "open_frame": q.get("open_frame"), "rearms": gd["rearms"], "marker_last": marker_last,
                "choice_first": first, "choice_ready": choice_ready, "choice_close": choice_close,
                "answer": gd["answer"], "closing_seq": closing, "presses": presses, "strays": strays,
                "branch": "other" if holds(other) else "pick" if holds(pick) else None, "branch_frame": st.frame,
                "branch_raw": [p for p, _t in rows], "verdict": None}

    def guard_judge(self, st, rows: list) -> None:
        """THE JUDGMENT (S10 (o)), once, at the first page after the guarded choice's VERIFIED answer -- its ``guard``
        row written and judged, in order: never ARMED (the marker page closed by a press page-once did not make): V17; a
        STRAY in [the marker page's last sample, the choice's close): V17; the page holds the OTHER branch's marker --
        the game took the other answer (outside input, or a cursor move no sample showed): V13; it holds NEITHER: an
        ``observed`` row (``after_answer``) and V17 (game-observed); else "ok", the branch the pick's. Every VOID the
        driver's, nothing pressed (0.2 #20)."""
        gd, pol = self.gd, self.guard
        gd["judged"] = True
        row = self.guard_row(st, rows)
        kind = verdict = None
        if row["armed_frame"] is None:
            kind, verdict = "armed", ("V17", "the marker page was closed by a press page-once did not make")
        elif row["strays"]:
            s = row["strays"][0]
            kind, verdict = "stray", ("V17", f"a press of the driver's own (seq {s['seq']}, {s['why']}) went down in "
                                             f"[the marker page's last sample, the guarded choice's close) before its "
                                             f"answer")
        elif row["branch"] == "other":
            kind, verdict = "other", ("V13", f"the game took the other branch (its first page holds "
                                             f"{pol['branch'][1]!r}): the answer it took is not the pick -- outside "
                                             f"input, or a cursor move no sample showed")
        elif row["branch"] is None:
            kind, verdict = "neither", ("V17", f"the first page after the answer holds neither branch's marker, "
                                               f"nothing pressed: {st.text[:120]!r}")
        row["verdict"] = "ok" if verdict is None else verdict[0]
        if verdict is not None:
            row["why"] = verdict[1]
        gd["row"] = row
        self.log.append(row)
        if verdict is None:
            return
        if kind == "neither":
            self.observed("after_answer", st)
        raise RouteVoid(verdict[1], v=verdict[0], cell=self.vcell(self.donor, self.sc), by="driver")

    def guard_stray(self, kind: str, st, *, note: str | None = None) -> None:
        """S10's two strays, each logged (``{"k": "guard_stray", "kind", "lo", "hi", "strays", "v", "by"}``, with the
        ``guard`` row when none was written yet) and raised: "choice_gone" -- the guarded choice left with no answer of
        the driver's: a press of the driver's own in [the marker page's last sample, its close) is V17, none is V13
        (the driver's: unattributed input the witness missed -- member(153)'s e3/e31 are the donor's and no dialog code
        keys on the route's fields, so the game cannot answer one side's choice alone); "choice_reask" -- the guarded
        rule asked again after its VERIFIED landing: V2, the GAME's, outright (neither answer brings the choice back,
        and no press of the driver's can). ``note`` (the row's ``note``) says where the gone choice was read when it was
        not rule 7's (i): :meth:`answer_gone`."""
        gd = self.gd
        row = gd["row"] or self.guard_row(st, dialog_rows(st.raw))
        strays = row["strays"]
        if kind == "choice_reask":
            v, by, why = "V2", "game", (f"the guarded choice was asked again after its verified answer (the rule "
                                        f"{self.guard['choice']!r} answers once)")
        elif strays:
            s = strays[0]
            v, by, why = "V17", "driver", (f"a press of the driver's own (seq {s['seq']}, {s['why']}) went down in "
                                           f"[the marker page's last sample, the guarded choice's close) before its "
                                           f"answer")
        else:
            v, by, why = "V13", "driver", ("the guarded choice left with no press of the driver's in [the marker page's "
                                           "last sample, its close): unattributed input")
        srow = {"k": "guard_stray", "kind": kind, "lo": row["marker_last"], "hi": row["choice_close"],
                "strays": strays, "v": v, "by": by}
        if note is not None:
            srow["note"] = note
        self.log.append(srow)
        if gd["row"] is None:
            row.update(verdict=v, why=why)
            gd["row"] = row
            self.log.append(row)
        raise RouteVoid(why, v=v, cell=self.vcell(self.donor, self.sc), by=by)

    def answer_landed(self, st, index: int, rule: dict) -> dict:
        """S11 IN THE DRIVER (research/o5_design.md 1.2, 2.5.3), under the guard: the pick answered through
        :meth:`Session.choose_landed` -- the landing VERIFIED on the game's clock, never a blind wait -- its presses rowed
        (:meth:`row_choose`: each a ``press`` row ``why`` "choose", the last Confirm marked ``answer`` with
        ``selected_before``), the witness polled at once (S12), then the driver's own V-classes: the landing unseen
        (ChoiceUnseen), the answer not landed, or its Confirm unplaceable (no accepted event, or no sample before its
        down frame publishing the cursor): V17; the cursor read off the pick as the answer's Confirm went down: V13
        (outside input). The guarded choice TAKEN under the answer before its first Confirm -- ``select`` meeting it
        gone -- is S10's gone choice, not the instrument's stop (:meth:`answer_gone`). The guarded rule's answer is kept
        (``gd["answered"]``, its seq span ``gd["answer"]``), and the hold-off of the last press counts from the reads
        after it."""
        from harness import HarnessError
        from harness.session import ChoiceUnseen
        g, gd = self.g, self.gd
        before = g.channel.seq
        try:
            took = g.choose_landed(index)
        except ChoiceUnseen as err:
            self.row_choose(before, g.channel.seq, st)
            raise RouteVoid(f"the answer's landing went unseen: {err}", v="V17",
                            cell=self.vcell(self.donor, self.sc), by="driver") from err
        except HarnessError as err:
            self.answer_gone(st, before, rule, err)          # raises: S10's gone choice, or ``err`` itself
        after = g.channel.seq
        self.row_choose(before, after, st)
        self.poll_witness(st, now_too=True)
        if not took.get("landed"):
            raise RouteVoid(f"the answer {index} did not land: {took.get('why')}", v="V17",
                            cell=self.vcell(self.donor, self.sc), by="driver")
        ans = [r for r in self.log if r.get("k") == "press" and r.get("why") == "choose" and r.get("answer")
               and r.get("seq") is not None and before < int(r["seq"]) <= after]
        sel = ans[-1].get("selected_before") if ans else None
        if sel is None:
            why = ("no accepted event" if not ans or ans[-1].get("down_frame") is None else
                   "no sample before its down frame published the choice's cursor")
            raise RouteVoid(f"the answer's Confirm could not be placed: {why}", v="V17",
                            cell=self.vcell(self.donor, self.sc), by="driver")
        if sel != index:
            raise RouteVoid(f"the cursor read {sel}, not the pick, as the answer's Confirm went down: outside input",
                            v="V13", cell=self.vcell(self.donor, self.sc), by="driver")
        if rule is self.guard_rule:
            gd["answered"], gd["answer"] = True, [before, after]
        seen = [int(raw.get("frame", -1)) for raw in g.states_since(st.frame)]
        if seen:
            gd["last_ack"] = max(seen) if gd["last_ack"] is None else max(gd["last_ack"], max(seen))
        return took

    def answer_gone(self, st, before: int, rule: dict, err) -> None:
        """S10 UNDER S11 (research/o5_design.md 2.5.3-2.5.4; the review's): ``choose_landed`` raised a plain HarnessError
        on the guarded choice rule 6 had read READY -- ``select`` met it gone ("the choice dialogue closed while
        selecting", after pressing Down into its close tween when its cursor still read off the pick), or a wait for it
        ran out. When NO Confirm of the attempt was sent (every request in (``before``, now] read off steps.jsonl --
        one missing proves nothing -- and none a Confirm: nothing of the driver's answer can have answered it) and a
        read newer than rule 6's shows the choice taking no answers -- no choice block with the menu group not
        ``Dialog.Choice`` (gone; never the agent's dialog-section catch, which keeps that group), or the guarded one
        published with a group that is neither that nor None (its close tween: a group None reads ready,
        ``_choice_ready``) -- someone else answered it under the driver's answer: outside input, or a press of the
        driver's own going down on it at its cursor (2.5.5). So the attempt's presses (select's Down / Up) are rowed
        (:meth:`row_choose`) and kept as the answer's seq span ``gd["answer"]`` -- the answer's own presses, never strays
        (:func:`guard_exclude`; ``gd["answered"]`` stays False) -- the witness polled at once (S12), and the gone choice
        judged as rule 7's (i) judges it: :meth:`guard_stray` "choice_gone" -- V17 for a press of the driver's own in [the
        marker page's last sample, the choice's close), else V13 (unattributed input). Anything else -- another rule's
        choice, a Confirm sent, a stale read, the choice still ready, the catch -- raises ``err`` itself: the
        instrument's stop."""
        g, gd = self.g, self.gd
        after = g.channel.seq
        span = {int(r["seq"]): r for r in self.steps_rows()
                if r.get("seq") is not None and before < int(r["seq"]) <= after}
        if (rule is not self.guard_rule or len(span) != after - before
                or any(_press_button(r.get("steps")) in CONFIRM_NAMES for r in span.values())):
            raise err
        now = g.state
        gone = ((now.choice is None and now.menu_group != g.CHOICE_GROUP)
                or (now.menu_group not in (None, g.CHOICE_GROUP) and self.is_guard_choice(now.choice)))
        if not gone or now.frame <= st.frame:
            raise err
        self.row_choose(before, after, st)
        gd["answer"] = [before, after]
        self.poll_witness(now, now_too=True)
        self.guard_stray("choice_gone", now, note=f"read by the answer, before its first Confirm: {str(err)[:160]}")


def drive(g, pred: dict, side: str, log: list, *, deadline: float, floor_for=None, prior_for=None,
          progress: dict | None = None, end_fields=None, observe=None, forbid_live: bool = True,
          witness=None) -> dict:
    """Play the segment by its beat table (research/o2_design.md 2.2), from wherever the run stands to an end field.

    Returns ``{"end": "reached", "why", "void": None, "beats", "pages", "timed", "choices", "steps", "overlays",
    "forbidden", "end_state", "t"}`` -- and, with a battle registry (research/o3_design.md S4), ``"battles"`` (the
    battle rows) and ``"battle_epoch0"`` (the epoch published when the drive started); with a movie-skip policy
    (``movies``, PLAN.md "Movie skip (opt-in)"), ``"movies"`` (its ``movie`` rows); with the Chanbara policy
    (``chanbara``, research/o4_design.md 2.4), ``"zones"`` and ``"prompts"`` (its rows); anything the table cannot
    answer raises :class:`RouteVoid` with its class, cell and attribution (2.7), and the budget ``HarnessError``
    (V13). ``floor_for(donor, closed)`` gives a walk its
    floor (default: the donor's stock walkmesh as the player walks it, ``closed`` shut -- a member walks its donor's,
    P-FLOOR), ``prior_for(donor)`` its prior (default ``g.key_prior``); ``end_fields`` overrides the side's end fields
    (a rehearsal stage; else ``side_ends[side]``, else the predictions' one list -- S6); ``observe(st, ctx)`` sees every
    poll (the rehearsal recorder); ``forbid_live`` runs the live
    forbidden scan (V12; it needs the story trace running); ``witness()`` (opt-in, read under the Chanbara policy or,
    run-wide, under ``pred["witness"]``: S12) is the outside-input witness -- None while the pads and keys are
    neutral, else what it read (V13).
    ``progress`` is filled with the live beats, pages, choices, steps, overlays and forbidden rows, so a run that raises
    still says how far it got."""
    if floor_for is None:
        from ff9mapkit import extract
        from ff9mapkit.content import pathfind

        def floor_for(donor, closed):
            return pathfind.PlayerWalkmesh(extract.stock_walkmesh(donor), closed=closed)
    return _Drive(g, pred, side, log, deadline=deadline, floor_for=floor_for, prior_for=prior_for or g.key_prior,
                  progress=progress, end_fields=end_fields, observe=observe, forbid_live=forbid_live,
                  witness=witness).go()
