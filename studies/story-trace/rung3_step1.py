"""THE STORY-WRITE TRACE, RUNG 3 STEP 1 -- can the stock Dali morning be driven unattended, and does the trace
see the one write that matters? One stock run: no deploy, no relaunch, no DLL.

    py tools/play.py studies/story-trace/rung3_step1.py --label story-rung3-s1 --timeout 180

THE ROUTE IS NOT CHOSEN. The start is the story's own: the village entrance 359 at SC 2540 (312 writes 2540 and
leaves only to the world map; 359 reads neither SC nor its entrance and sets the party itself), and the game plays
359 -> 351 -> 352 (arrival, the inn, the night, the wake) on its own. From control in 352 a BLIND tour crosses
every exit of every field it reaches -- in the order `eventscan.scan_gateways` lists them, bounded by the in-game
location label "Dali/" (not by FBG zone: 450 Dali/Field is zone `airp`, the village `vgdl`), never talking to
anyone, ignoring ATE prompts -- until the scenario counter LEAVES 2600, i.e. until the story itself moves on. The
research (studies/story-trace/PLAN.md, rung 3) found that SC 2610 needs latch 2079, 2079 needs bit 2102, and only
field 450 writes 2102 = 1 -- so "until the story moves on" reaches 450 without anyone choosing it. This run tests
that claim; it does not assume it.

HOW AN EXIT IS CROSSED (after the first run ping-ponged 350 <-> 351 eighty times: it arrived in 350 standing 18u
from 351's own door, and every step toward the next exit -- a one-axis walk_to, a calibration probe, or a held
correction burst that outlived the fade -- walked it straight back). Each exit is taken with Session.route_cross:
a route over the field's real walkmesh to a standable point INSIDE the exit's zone, keeping out of every OTHER
gateway zone of the field (all of them, Dali-labelled or not), calibrated without pressing toward any of them, and
no press issued once control is gone. An exit counts as TRIED only when a crossing into ITS destination actually
happened (read after the scene settles, so an arrival scene that outlasts the crossing's timeout still counts);
landing anywhere else is a BOUNCE, finding no route a NO ROUTE, and not landing at all a MISS -- logged, never
marked tried, the field's other exits taken first, and after BOUNCES of them the (field, exit) is UNREACHABLE and
the tour moves on, so it cannot loop.

THE VILLAGE IS LIVE (after the second run: 350 -> 450 and 350 -> 355 planned a route and travelled 0, pressed
into a villager and into a Dali child with control held -- the "ACTIVE TIME EVENT" corner card in those frames is
the optional-ATE indicator, on screen through walks of 2446u and 3665u too, and holds nothing; each miss struck the
exit, and 450 went unreachable without its door ever being tried). Every crossing runs with
route_cross(unstick=True): a stall with control held is waited out, then PUSHED through (one unbroken hold: the
engine lets the player through anyone without object flag 16 once he insists, no NPC on 350 sets it, and the
short bursts of a routed walk never insisted long enough), and only then routed round as an unseen body. So a
failed crossing is one of two things, and only one of them STRIKES:
- a REAL failure says something about the exit, and strikes it -- a BOUNCE (landed elsewhere), a MISS whose
  destination took control and never gave it back (353: Mayor Kapu's arrival scene puts the player back where he
  came from), a MISS that stood INSIDE the zone and nothing fired (350 -> 358 once its scene has played: the story
  shut the region; judged by zone membership, route_cross's `inside`, not by the goal distance), a MISS where
  something else took control mid-walk, NO ROUTE, BLOCKED -- he moved after the first unseen blocker went in,
  and then blockers sealed the way -- or BOXED: the smooth walk stood where no press keeps clear of the other
  exits and of the villagers standing still round him, and no walker's going would change that (the geometry of
  that spot, like NO ROUTE; nothing waited or pushed). BOUNCES of them: unreachable.
- a LIVE miss says something about the village, and does not strike: the walk stalled with control held, waited,
  pushed or routed round (or found movement held -- `frozen`, which also covers a first blocker that sealed the
  way before he had moved again: nothing tells that from a hold), or waited out walkers that boxed him in and let
  him go, and still ended short, OUTSIDE the zone -- or villagers WALKING round him boxed him in and outlasted the
  walk's wait for them (below). The exit goes behind the field's other exits and is tried again; only after LIVE
  of them is it unreachable, so a village that never clears still cannot hold the tour.

THE ROUTER WALKS THE PLAYER'S FLOOR (after the second run: 356 -> 358 stalled four times exactly the controller
radius off stock 356's triangle 50, a door strip whose triFlags 0xA001 bar the controlled player while the
attribute mask is 255 -- 356's own door walk lowers it to 127 -- and pathfind knew nothing of the rule). Goals,
routes and the one-way rule all use pathfind.PlayerWalkmesh: closed triangles are walls. Across Dali that changes
exactly one exit -- 356 -> 358, now NO ROUTE from anywhere in 356, a clean REAL failure instead of a stall.

A ONE-WAY DOOR GOES LAST. A door is one-way when its destination's own script puts the arriving player where
none of that destination's exits can be routed to: 350 -> 358 lands on a walkmesh piece 358's only gateway zone
is not on (the way back to 350 is a scripted position check, not a gateway region). Crossed in scan order it
stranded an offline dry run of this tour in 358, one exit short of 450. So a pass takes one-way doors only once
nothing two-way is left, and never hops through one. The rule reads only walkmesh and script bytes -- it knows
nothing of 450 or the story; an arrival spot the scan cannot decode counts as two-way.

A CHOICE IS THE GAME'S (after the third run: the tour reached 450, the story moved, and the run stopped in 354 on
Garnet's "You changed the way you talk!" -- the scene waiter turns boxes and stopped at the choice until its 240 s
ran out). Every scene is sat through with watch_cutscene(choices="default"): a choice is answered with the option
the game's own cursor rests on once the window is ready -- the script's defaultChoice, never one the tour prefers,
so the route stays the story's -- and each one taken is logged (rung3s1_log.json "choices", and per scene).

THE WALK IS SMOOTH (the owner, watching the third run: it works, the movement is choppy). Every crossing is
route_cross(smooth=True): each planned leg walked in whole holds, two keys at once on a diagonal, instead of
one-axis bursts with a settle after each; a hold is only as long as its straight line, movement tail included --
and every line within the calibrated basis's heading error of it -- stays clear of every other exit zone and near
the leg still to walk. And the zone goes with it: the last leg finishes IN the exit's zone (its nearest spot
where his centre can stand), not within a walk frame of a goal point that may lie outside what he can reach.

THE ROUTER SEES THE VILLAGERS (the owner: other maps may not be as forgiving as this one -- a body found only by
bumping into it can be a true movement lock). Every crossing is route_cross(npcs=True): the live engine publishes
the field's objects (memoria-patch s89, deployed), so each villager is an obstacle of its own collision radius in the
same plan the other exits are kept out of, and each contact trigger (an entry's Range: 350's Vivi warps the run to
358 from 314u) is kept out of like an exit zone -- entered only when no route stays clear, and then logged. A
non-solid villager is pushed through only when no route goes round; a solid one never, and solids that seal every
way are BLOCKED (a REAL failure -- unless a sealing solid is itself walking: that is the village, LIVE). A villager
walking onto the path re-plans the route, a bounded number of times, and a WALKING trigger is waited for until it
has gone by -- a walk that waited on walkers and then found nothing it could press is LIVE too, not BOXED.

A BOX BY WALKERS IS NOT THE SPOT (rung-3 session 2, run 2: two Dali children -- talk-only walkers, non-solid bodies of
r 152 -- walked into Zidane in 350 and stood there, held; every press toward any exit came nearer one of them, so
crossings 24-30 all came back BOXED from that one spot, each a REAL strike, until the passes ran out: VOID). The
engine undoes every step a scripted walker takes into the player (MoveToward.cs:187-189): the
children would have waited on him for ever, and he on them. Now a spot where no press keeps the rules is BOXED at once
only when the walkers among what refuses the presses (published walking, or seen walking by the call -- a wanderer
reads still at the turns of its loop) are not the cause: planned without them, still no press. Where their going would
free one, the walk stands and reads again, steps out of the way of any walker HELD ON HIM (within its own step of
contact -- the engine undoes a whole step, and the children outpace his run -- still walking, not moved in half a
second: one hold along the pad that ends furthest from the line it was walking, or from the line at him when it was
never seen walking, as long as the room round him lets a slide carry him nowhere near a door or a Range: beside a
door, shorter or walked), and plans again once a press is free -- a box they let go of is no box at all, and strikes
nothing. One that outlasts that wait is the village holding him (``boxed_by`` "walkers"): LIVE, not BOXED. A
talk-only villager (a talk script, no Range) is a body and nothing more: inside its talk radius the "!" is a prompt
for a Confirm the tour never presses. Per
crossing the log names the objects avoided, the trigger radii entered (a Range that reached him as control went
included), the bodies pushed through, the movement re-plans, the waits for walkers, and the objects that boxed him
in with the waits (and steps aside) that box cost and whether it let go (``npcs`` says whether the
engine listed its objects at all: "cannot" on an engine without s89, where the walk is the blind unstick one above).

S1-SEGMENT  the scripted segment hands control back in 352 at SC 2600
S1-TOUR     the tour ran: crossings attempted / landed, the fields reached, the stop reason
S1-PING     the premise: a script write Bit[2102] := 1 in field 450 -- and the WRITERS of 2102 := 1 are only 450
S1-ADVANCE  the story moved on (SC left 2600) inside the budget
S1-JOIN     every script row joins its store in the stock bytes
NC-THROW

The tour itself (the rules above) lives in dali_tour.py, shared with rung3_trace.py's fork-side runs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dali_tour as D  # noqa: E402
from dali_tour import T  # noqa: E402

try:
    from harness import HarnessError
except ImportError:
    from tools.harness import HarnessError  # noqa: E402

START, START_SC, BEAT = 359, 2540, 2600
MAX_CROSSINGS, MAX_PASSES, BUDGET_S = 80, 3, 40 * 60
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")

_stock = T.stock_script_source()
_tour = D.Tour(stock=_stock, tag="rung3-s1")
say = _tour.say


def run(g) -> None:
    cap = g.state.storytrace
    if not g.check(isinstance(cap, dict) and cap.get("proto") == T.PROTO,
                   "P-CAP: the engine advertises the story trace at proto 1", str(cap)):
        return
    mark = g.log_mark()
    log: list = []
    rows: list = []
    stop = "not reached"
    seg_ok = False
    try:
        g.newgame()
        g.wait_frames(30)
        g.storytrace(True)
        seg_ok = D.segment(g, log, start=START, sc=START_SC, beat=BEAT)["ok"]
        if seg_ok:
            stop = _tour.run(g, log, beat=BEAT, max_crossings=MAX_CROSSINGS, max_passes=MAX_PASSES,
                             budget_s=BUDGET_S)   # route_cross calibrates each field itself, clear of its doors
            D.settle(g, log, "after the tour", say)
        g.storytrace(False)
        rows = g.story_rows()
    except HarnessError as err:
        stop = f"STOPPED: {type(err).__name__}: {str(err)[:300]}"
    finally:
        choices = [dict(c, why=x["why"]) for x in log if x["k"] == "scene" for c in x.get("choices", [])]
        (g.run_dir / "story_rung3s1.jsonl").write_text(g.channel.story_text() or "", encoding="utf-8")
        (g.run_dir / "rung3s1_log.json").write_text(
            json.dumps({"stop": stop, "choices": choices, "log": log}, indent=1), encoding="utf-8")
        say(f"{len(choices)} default choice(s) taken: "
            f"{[(c['field'], c['index'], c['text']) for c in choices]}")
    g.check(seg_ok, f"S1-SEGMENT: the game's own segment 359 -> 351 -> 352 hands control back in 352 at SC {BEAT}",
            str([x for x in log if x["k"] == "segment"]))
    crossings = [x for x in log if x["k"] == "cross"]
    landed = [x for x in crossings if x.get("landed")]
    fields = sorted({x["now"] for x in crossings if x.get("now")})
    g.check(bool(crossings), "S1-TOUR: the blind tour ran",
            f"{len(crossings)} crossings, {len(landed)} landed, fields {fields}; stop: {stop}")
    run_ = T.split_runs(rows)[0] if rows else []
    ping = [r for r in run_ if r.k == "w" and r.src == "eb" and r.target == "Global.Bit[2102]" and r.new == 1]
    writers = sorted({r.don for r in ping})
    g.check(bool(ping) and writers == [450],
            "S1-PING: the story's own route wrote Bit[2102] := 1, and only field 450 wrote it",
            f"{len(ping)} rows; writers {writers}; at "
            f"{[(r.fld, r.sid, r.tag, r.ip) for r in ping[:4]]}")
    g.check(stop.startswith("SC left"), f"S1-ADVANCE: the story moved on past SC {BEAT} inside the budget", stop)
    if run_:
        ran = T.mod_script_source(D.mod_roots(), fallback=_stock)   # the bytes the game RAN (field 70 override)
        fails = []
        for r in run_:
            if r.k == "w" and r.src == "eb" and not r.add:
                idx = ran(r.fld)
                j = idx.join(r, donor=r.don) if idx else None
                if j is None or not j.ok:
                    fails.append((r.fld, r.target, r.ip, j.reason if j else "no stock script"))
        g.check(not fails, "S1-JOIN: every script row joins its store in the bytes the game ran",
                f"{len(fails)} failures {fails[:4]}")
    every = g.exceptions_since(mark)
    ours = [e for e in every if e.name in THROWS and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not ours, "NC-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
            str([(e.name, e.where) for e in ours[:5]]))
