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

A ONE-WAY DOOR GOES LAST. A door is one-way when its destination's own script puts the arriving player where
none of that destination's exits can be routed to: 350 -> 358 lands on a walkmesh piece 358's only gateway zone
is not on (the way back to 350 is a scripted position check, not a gateway region). Crossed in scan order it
stranded an offline dry run of this tour in 358, one exit short of 450. So a pass takes one-way doors only once
nothing two-way is left, and never hops through one. The rule reads only walkmesh and script bytes -- it knows
nothing of 450 or the story; an arrival spot the scan cannot decode counts as two-way.

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
BOUNCES = 2                               # failed crossings (bounce or miss) before a (field, exit) is unreachable
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")

_names: dict = {}
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
    """A standable point inside exit i's zone (pathfind.region_goal on the install's walkmesh), or None."""
    if (fid, i) not in _goals:
        try:
            _goals[(fid, i)] = pathfind.region_goal(extract.stock_walkmesh(fid), exits(fid)[i][2])
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
            if goal is not None and pathfind.route_avoiding(extract.stock_walkmesh(to), pos, goal,
                                                            avoid_for(to, zone), MARGIN) is not None:
                back = True
                break
        _oneway[(fid, i)] = not back
        if not back:
            say(f"field {fid} exit {i} (to {to}, entrance {entrance}) is ONE-WAY: no exit of {to} routes from "
                f"its arrival {pos} -- it goes last")
    return _oneway[(fid, i)]


def settle(g, log, why: str) -> None:
    """Sit through whatever the game plays until the player has control again."""
    st = g.state
    if not st.control:
        pages = g.watch_cutscene(timeout=240)
        rec = {"k": "scene", "why": why, "field": g.state.field_id, "sc": g.state.scenario,
               "pages": len(pages), "first": (pages[0][:80] if pages else "")}
        log.append(rec)
        say(json.dumps(rec))


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
    fails: dict = {}                     # (field, exit) -> ["bounce" | "miss" | "no route", ...], across passes
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
                r = g.route_cross(goal[0], goal[1], avoid=avoid_for(f, zone), margin=MARGIN, timeout=20)
                rec.update(landed=r["landed"], reached=r["reached"], travelled=round(r["travelled"]),
                           during=r["during"], replans=r["replans"],
                           route=len(r["waypoints"]) if r["waypoints"] is not None else None)
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
                kind = ("bounce" if rec.get("landed") is not None
                        else "no route" if "route" in rec and rec["route"] is None else "miss")
                later.add((f, i))
                fails.setdefault((f, i), []).append(kind)
                rec["verdict"] = f"{kind} {len(fails[(f, i)])}/{BOUNCES}"
                if len(fails[(f, i)]) >= BOUNCES:
                    dead.add((f, i))
                    rec["verdict"] += " -> unreachable"
                if kind == "miss":
                    g.shot(f"miss-{n}-{f}-to-{to}")
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
                pages = g.watch_cutscene(timeout=300)
                log.append({"k": "scene", "why": "segment", "field": g.state.field_id, "sc": g.state.scenario,
                            "pages": len(pages)})
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
        (g.run_dir / "story_rung3s1.jsonl").write_text(g.channel.story_text() or "", encoding="utf-8")
        (g.run_dir / "rung3s1_log.json").write_text(json.dumps({"stop": stop, "log": log}, indent=1),
                                                     encoding="utf-8")
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
