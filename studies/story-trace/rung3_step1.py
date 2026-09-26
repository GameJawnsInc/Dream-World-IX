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
  exits (the geometry of that spot, like NO ROUTE; nothing waited or pushed). BOUNCES of them: unreachable.
- a LIVE miss says something about the village, and does not strike: the walk stalled with control held, waited,
  pushed or routed round (or found movement held -- `frozen`, which also covers a first blocker that sealed the
  way before he had moved again: nothing tells that from a hold), and still ended short, OUTSIDE the zone. The
  exit goes behind the field's other exits and is tried again; only after LIVE of them is it unreachable, so a
  village that never clears still cannot hold the tour.

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
has gone by -- a walk that waited on walkers and then found nothing it could press is LIVE too, not BOXED. Per
crossing the log names the objects avoided, the trigger radii entered (a Range that reached him as control went
included), the bodies pushed through, the movement re-plans and the waits for walkers (``npcs`` says whether the
engine listed its objects at all: "cannot" on an engine without s89, where the walk is the blind unstick one above).

S1-SEGMENT  the scripted segment hands control back in 352 at SC 2600
S1-TOUR     the tour ran: crossings attempted / landed, the fields reached, the stop reason
S1-PING     the premise: a script write Bit[2102] := 1 in field 450 -- and the WRITERS of 2102 := 1 are only 450
S1-ADVANCE  the story moved on (SC left 2600) inside the budget
S1-JOIN     every script row joins its store in the stock bytes
NC-THROW
"""
from __future__ import annotations

import json
import sys
import time
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit import eventscan, extract, storytrace as T  # noqa: E402
from ff9mapkit.content import pathfind  # noqa: E402

try:
    from harness import HarnessError
except ImportError:
    from tools.harness import HarnessError  # noqa: E402

START, START_SC, BEAT = 359, 2540, 2600
LABEL = "Dali/"
MAX_CROSSINGS, MAX_PASSES, BUDGET_S = 80, 3, 40 * 60
MARGIN = pathfind.KEEPOUT_MARGIN_W        # keep-out around every gateway zone the crossing is not aimed at
BOUNCES = 2                               # REAL failures (the docstring) before a (field, exit) is unreachable
LIVE = 3                                  # LIVE misses (the village in the way) before it is unreachable too
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")

_names: dict = {}
_floors: dict = {}
_gates: dict = {}
_goals: dict = {}
_oneway: dict = {}
_stock = T.stock_script_source()


def say(*parts) -> None:
    """Every log line, flushed: the first run's block-buffered prints surfaced only at exit."""
    print("[rung3-s1]", *parts, flush=True)


def label(fid: int) -> str:
    if fid not in _names:
        rows = [r for r in extract.find_fields(str(fid)) if int(r["id"]) == fid]
        _names[fid] = (rows[0]["name"] or "") if rows else ""
    return _names[fid]


def floor(fid: int):
    """Field ``fid``'s stock walkmesh as the controlled player may walk it (pathfind.PlayerWalkmesh); raises like
    extract.stock_walkmesh when the id has none."""
    if fid not in _floors:
        _floors[fid] = pathfind.PlayerWalkmesh(extract.stock_walkmesh(fid))
    return _floors[fid]


def gateways(fid: int) -> list:
    """EVERY walk-in gateway of the field, one per distinct (destination, zone), in scan order: [(to, entrance,
    zone)]. 350 lists its 353 exit twice with one zone -- one exit, not two."""
    if fid not in _gates:
        idx = _stock(fid)
        out = []
        for gw in (eventscan.scan_gateways(idx.data) if idx else []):
            if all((gw["to"], gw["zone"]) != (t, z) for t, _e, z in out):
                out.append((gw["to"], gw["entrance"], gw["zone"]))
        _gates[fid] = out
    return _gates[fid]


def exits(fid: int) -> list:
    """The exits the tour takes: the gateways whose destination carries the location label, in scan order."""
    return [gw for gw in gateways(fid) if label(gw[0]).startswith(LABEL)]


def avoid_for(fid: int, zone) -> list:
    """Every OTHER gateway zone of the field -- label-bounded or not: a door out of Dali is still a door."""
    return [z for _t, _e, z in gateways(fid) if z != zone]


def goal_for(fid: int, i: int):
    """A standable point inside exit i's zone (pathfind.region_goal on the player's floor), or None."""
    if (fid, i) not in _goals:
        try:
            _goals[(fid, i)] = pathfind.region_goal(floor(fid), exits(fid)[i][2])
        except (OSError, ValueError, RuntimeError) as err:     # no walkmesh for this id: no goal, no route
            say(f"field {fid}: no walkmesh to aim exit {i} on ({type(err).__name__}: {err})")
            _goals[(fid, i)] = None
    return _goals[(fid, i)]


def arrival(fid: int, entrance: int):
    """Where field ``fid``'s own script stands the player arriving by ``entrance`` (its table row, else its
    default), or None when neither decodes -- 351, 353, 354 and 450 place him some other way."""
    idx = _stock(fid)
    t = eventscan.scan_arrival_table(idx.data) if idx else {"table": [], "default": None}
    row = next((r for r in t["table"] if r["entrance"] == entrance), None) or t["default"]
    return tuple(row["pos"]) if row else None


def one_way(fid: int, i: int) -> bool:
    """Could the tour NOT walk back out of exit i's destination? True only when the destination's arrival spot
    for this exit's entrance is known and none of the destination's exits routes from it (see the module
    docstring: 350 -> 358). An undecoded arrival is two-way."""
    if (fid, i) not in _oneway:
        to, entrance, _zone = exits(fid)[i]
        pos = arrival(to, entrance)
        back = pos is None
        for j, (_t, _e, zone) in enumerate(exits(to) if pos is not None else ()):
            goal = goal_for(to, j)                       # None also when the walkmesh cannot be read
            if goal is not None and pathfind.route_avoiding(floor(to), pos, goal,
                                                            avoid_for(to, zone), MARGIN) is not None:
                back = True
                break
        _oneway[(fid, i)] = not back
        if not back:
            say(f"field {fid} exit {i} (to {to}, entrance {entrance}) is ONE-WAY: no exit of {to} routes from "
                f"its arrival {pos} -- it goes last")
    return _oneway[(fid, i)]


def settle(g, log, why: str) -> None:
    """Sit through whatever the game plays until the player has control again -- answering every choice with
    the option the game's own cursor rests on (watch_cutscene(choices="default")), each one logged."""
    st = g.state
    if not st.control:
        pages = g.watch_cutscene(timeout=240, choices="default")
        rec = {"k": "scene", "why": why, "field": g.state.field_id, "sc": g.state.scenario,
               "pages": len(pages), "first": (pages[0][:80] if pages else ""), "choices": pages.choices}
        log.append(rec)
        say(json.dumps(rec))


def failure(rec: dict) -> str:
    """What a crossing that did not land where its exit leads was, by the module docstring's strike rule:
    "bounce", "no route", "blocked", "boxed" or "miss" (REAL: they strike the exit), or "live" (the village was
    in the way: a stall with control held that the walk waited on, pushed or routed round, or a villager walking
    onto the path, ending short OUTSIDE the zone; published solids sealing the way while one of them walks; or a
    walk that waited on walking triggers and was then left with nothing it could press). Standing inside the zone
    with nothing fired is a miss whatever the walk met on the way. A seal by published solids has no route either,
    and is BLOCKED, not NO ROUTE: the walls and zones alone had one."""
    if rec.get("landed") is not None:
        return "bounce"
    if rec.get("blocked"):
        return "live" if any(moving for _uid, moving in rec.get("sealed") or ()) else "blocked"
    if "route" in rec and rec["route"] is None:
        return "no route"
    if rec.get("boxed"):
        return "live" if rec.get("npc_waits") else "boxed"
    if rec.get("inside"):
        return "miss"
    if ("error" not in rec and rec.get("during") is None and not rec.get("reached")
            and (rec.get("waits") or rec.get("pushes") or rec.get("blockers") or rec.get("frozen")
                 or rec.get("npc_replans"))):
        return "live"
    return "miss"


def next_hop(start: int, want, dead: set):
    """BFS over the exit graph from ``start`` -- never through an unreachable or a one-way exit -- to the
    nearest field satisfying ``want``: the index of the first exit to take, or None."""
    seen, q = {start}, deque([(start, None)])
    while q:
        f, first = q.popleft()
        if f != start and want(f):
            return first
        for i, (to, _e, _z) in enumerate(exits(f)):
            if (f, i) not in dead and to not in seen and not one_way(f, i):
                seen.add(to)
                q.append((to, first if first is not None else i))
    return None


def tour(g, log) -> str:
    t0 = time.time()
    n = 0
    fails: dict = {}                     # (field, exit) -> its REAL failures (failure()), across passes
    live: dict = {}                      # (field, exit) -> its LIVE misses, across passes
    dead: set = set()                    # (field, exit) unreachable this run
    visit, later = None, set()           # exits that failed on THIS visit: the field's other exits go first
    for p in range(1, MAX_PASSES + 1):
        tried: set = set()

        def open_(h, one_ways=False):
            return [j for j in range(len(exits(h))) if (h, j) not in tried and (h, j) not in dead
                    and (one_ways or not one_way(h, j))]

        while True:
            st = g.state
            if st.scenario != BEAT:
                return f"SC left {BEAT}: now {st.scenario} in field {st.field_id} (pass {p}, crossing {n})"
            if n >= MAX_CROSSINGS or time.time() - t0 > BUDGET_S:
                return f"budget spent (crossings {n}, {time.time() - t0:.0f}s)"
            f = st.field_id
            if f != visit:
                visit, later = f, set()
            mine = sorted(open_(f), key=lambda j: (f, j) in later)
            if mine:
                i, leg = mine[0], "tour"
            else:
                i, leg = next_hop(f, lambda h: bool(open_(h)), dead), "back"
            if i is None:
                # nothing two-way is left anywhere reachable: now the one-way doors, last -- past one, the
                # tour may well have no way back
                mine = sorted(open_(f, True), key=lambda j: (f, j) in later)
                if mine:
                    i, leg = mine[0], "one-way"
                else:
                    i, leg = next_hop(f, lambda h: bool(open_(h, True)), dead), "back"
                    if i is None:
                        break                                        # this pass has crossed everything
            to, _e, zone = exits(f)[i]
            n += 1
            goal = goal_for(f, i)
            rec = {"k": "cross", "n": n, "pass": p, "leg": leg, "from": f, "exit": i, "to": to,
                   "target": list(goal) if goal else None, "sc0": st.scenario}
            if goal is None:
                dead.add((f, i))
                rec.update(verdict="unreachable: no standable goal inside its zone")
                log.append(rec)
                say(json.dumps(rec))
                continue
            try:
                r = g.route_cross(goal[0], goal[1], avoid=avoid_for(f, zone), margin=MARGIN, timeout=20,
                                  walkmesh=floor(f), unstick=True, zone=zone, smooth=True, npcs=True)
                rec.update(landed=r["landed"], reached=r["reached"], inside=r["inside"],
                           travelled=round(r["travelled"]), during=r["during"], replans=r["replans"],
                           route=len(r["waypoints"]) if r["waypoints"] is not None else None,
                           waits=r["waits"], cleared=r["cleared"], pushes=r["pushes"], pushed=r["pushed"],
                           blockers=r["blockers"], remembered=r["remembered"], blocked=r["blocked"],
                           frozen=r["frozen"], boxed=r["boxed"], npcs=r["npcs"],
                           avoided=[(o["uid"], o["kind"]) for o in r["avoided"]],
                           entered=[(o["uid"], o["kind"], o["radius"]) for o in r["entered"]],
                           through=[o["uid"] for o in r["through"]],
                           sealed=[(o["uid"], o["moving"]) for o in r["sealed"]], npc_replans=r["npc_replans"],
                           npc_waits=r["npc_waits"])
            except HarnessError as err:
                rec.update(landed=None, error=str(err)[:200])
            settle(g, log, f"after crossing {n}")
            now = g.state.field_id
            if rec.get("landed") is None and now != f and now > 0:
                # the crossing call gave up but the room DID change -- e.g. the destination held control
                # past its timeout for an arrival scene ("never became playable"), which settle() just
                # sat through. Where he stands now is where the crossing led.
                rec.update(landed=now, landed_late=True)
            if rec.get("landed") == to:
                if leg != "back":
                    tried.add((f, i))
                rec["verdict"] = "crossed"
            else:
                # no route is a failed attempt like the others, not a verdict: it was planned from where he
                # stood THIS time, and the next visit arrives somewhere else
                kind = failure(rec)
                later.add((f, i))
                tally = (live if kind == "live" else fails).setdefault((f, i), [])
                tally.append(kind)
                cap = LIVE if kind == "live" else BOUNCES
                rec["verdict"] = f"{kind} {len(tally)}/{cap}"
                if len(tally) >= cap:
                    dead.add((f, i))
                    rec["verdict"] += " -> unreachable"
                if kind in ("miss", "live", "blocked", "boxed"):
                    g.shot(f"{kind}-{n}-{f}-to-{to}")
            rec.update(now=g.state.field_id, sc1=g.state.scenario, t=round(time.time() - t0))
            log.append(rec)
            say(json.dumps(rec))
    return f"passes exhausted ({MAX_PASSES}) without the story moving on"


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
        g.send(f"warp {START} 0 {START_SC}")                 # raw: warp() waits for control this segment never gives
        g.wait_for(lambda s: s.field_id == START, timeout=60, what=f"field {START} to load")
        deadline = time.time() + 900
        while time.time() < deadline:
            st = g.state
            if st.field_id == 352 and st.control and st.scenario == BEAT:
                break
            if not st.control:
                pages = g.watch_cutscene(timeout=300, choices="default")
                log.append({"k": "scene", "why": "segment", "field": g.state.field_id, "sc": g.state.scenario,
                            "pages": len(pages), "choices": pages.choices})
            else:
                g.wait_frames(15)
        st = g.state
        seg_ok = st.field_id == 352 and st.control and st.scenario == BEAT
        log.append({"k": "segment", "field": st.field_id, "sc": st.scenario, "control": st.control})
        if seg_ok:
            stop = tour(g, log)                  # route_cross calibrates each field itself, clear of its doors
            settle(g, log, "after the tour")
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
        import re as _re
        text = (Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX") / "Memoria.ini").read_text(
            encoding="utf-8", errors="replace")
        m = _re.search(r'^\s*FolderNames\s*=\s*(.+)$', text, _re.M)
        game = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
        roots = [game / n for n in (_re.findall(r'"([^"]+)"', m.group(1)) if m else []) if (game / n).is_dir()]
        ran = T.mod_script_source(roots, fallback=_stock)             # the bytes the game RAN (field 70 override)
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
