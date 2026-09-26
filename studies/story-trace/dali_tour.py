"""THE BLIND DALI TOUR -- rung 3's route rule, shared by its drivers: rung3_step1.py (stock Dali) and
rung3_trace.py (stock and the two fork chains). The rules themselves (why each exists, and the runs that taught
them) are rung3_step1.py's docstring; this module is their one implementation.

A PLACE IS ITS DONOR. On a fork run the game stands in fork ids (a chain's members, rung3_forks.json: fork id ->
donor id); a real field is its own donor. Every RULE reads the place: the "Dali/" label bound, the exit order, the
one-way rule, the walkmesh (a verbatim member ships its donor's .bgi byte for byte -- rung3_trace.py's P-FLOOR
proves it on the deployed files before a run) and the calibration prior (a fork id has no install script to read
the SetControlDirection twist from; the member runs its donor's Main_Init, so the donor's prior is its own). And
the tour's memory is kept per place: an exit tried in member(350) is tried in the real 350 too, so a fork run that
crosses a seam into the real game walks on exactly as the stock run walks from the same place.

THE EXITS ARE THE RUNNING BYTES'. Where a crossing LEADS is read from the .eb the game runs in that field -- the
mod folder's for a member (scan_gateways on it gives the remapped targets), the install's for a real field. That
is how a seam is crossed at all: member(350)'s exit to 450 was left pointing at the real 450, and the tour follows
it there and carries on under the same rules. A member whose running exits are not its donor's -- same order,
zones and entrances, targets that map back to the donor's -- is refused (TourError) at the call that would read
them, never walked by the donor's rules as if it were.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for p in (REPO / "ff9mapkit", REPO / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from ff9mapkit import eventscan, extract, storytrace as T  # noqa: E402
from ff9mapkit.content import pathfind  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LABEL = "Dali/"
MARGIN = pathfind.KEEPOUT_MARGIN_W        # keep-out around every gateway zone the crossing is not aimed at
BOUNCES = 2                               # REAL failures (rung3_step1's docstring) before a place's exit is unreachable
LIVE = 3                                  # LIVE misses (the village in the way) before it is unreachable too
CROSS_TIMEOUT = 20                        # route_cross's wait for a crossing to land
SCENE_TIMEOUT = 240                       # one scene sat through (watch_cutscene)


class TourError(RuntimeError):
    """The tour cannot apply its rules to where it stands -- never walked through as if it could."""


def mod_roots(game: Path = GAME) -> list:
    """The mod folders Memoria.ini stacks (``[Mod] FolderNames``), in priority order, that exist."""
    text = (game / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', text, re.M)
    return [game / n for n in (re.findall(r'"([^"]+)"', m.group(1)) if m else []) if (game / n).is_dir()]


def _harness_error():
    from harness import HarnessError
    return HarnessError


def settle(g, log, why: str, say=print) -> None:
    """Sit through whatever the game plays until the player has control again -- answering every choice with
    the option the game's own cursor rests on (watch_cutscene(choices="default")), each one logged."""
    st = g.state
    if not st.control:
        pages = g.watch_cutscene(timeout=SCENE_TIMEOUT, choices="default")
        rec = {"k": "scene", "why": why, "field": g.state.field_id, "sc": g.state.scenario,
               "pages": len(pages), "first": (pages[0][:80] if pages else ""), "choices": pages.choices}
        log.append(rec)
        say(json.dumps(rec))


def segment(g, log, *, start: int, sc: int, beat: int, place=lambda f: f, until: int = 352,
            timeout: float = 900, stable: float = 30.0, woke=None) -> dict:
    """The game's own segment from a raw ``warp <start> 0 <sc>`` (warp() waits for control this segment never
    gives) until control returns AT the beat -- in place ``until`` (the 352 wake), or, if control is held at the
    beat for ``stable`` s anywhere else, there (``ok`` False: not where the story hands it back). Scenes are sat
    through with the game's default choices. Returns (and logs) the segment record.

    ``woke()`` -> whether the run's own trace shows the wake's store (rung 3: 352's SC := beat): with it, control
    at the beat counts only after the wake ran, on every side alike. SC alone cannot say so -- a fork whose
    prefix stamps the beat on arrival sits at it through the whole night scene."""
    g.send(f"warp {start} 0 {sc}")
    g.wait_for(lambda s: s.field_id == start, timeout=60, what=f"field {start} to load")
    deadline = time.time() + timeout
    held = None
    while time.time() < deadline:
        st = g.state
        if st.control and st.scenario == beat and (woke is None or woke()):
            if place(st.field_id) == until:
                break
            held = held or time.time()
            if time.time() - held >= stable:
                break
        else:
            held = None
        if not st.control:
            pages = g.watch_cutscene(timeout=300, choices="default")
            log.append({"k": "scene", "why": "segment", "field": g.state.field_id, "sc": g.state.scenario,
                        "pages": len(pages), "choices": pages.choices})
        else:
            g.wait_frames(15)
    st = g.state
    rec = {"k": "segment", "field": st.field_id, "place": place(st.field_id), "sc": st.scenario,
           "control": st.control}
    if woke is not None:
        rec["woke"] = bool(woke())
    rec["ok"] = bool(rec["place"] == until and st.control and st.scenario == beat and rec.get("woke", True))
    rec["at_beat"] = bool(st.control and st.scenario == beat and rec.get("woke", True))
    log.append(rec)
    return rec


def failure(rec: dict) -> str:
    """What a crossing that did not land where its exit leads was, by rung3_step1's strike rule:
    "bounce", "no route", "blocked", "boxed" or "miss" (REAL: they strike the exit), or "live" (the village was
    in the way: a stall with control held that the walk waited on, pushed or routed round, a villager walking
    onto the path, or walkers that boxed him in and let him go (``box_waits``), ending short OUTSIDE the zone;
    published solids sealing the way while one of them walks; or a walk that waited on walking triggers, or on
    walkers boxing him in, and was then left with nothing it could press). Standing inside the zone with nothing
    fired is a miss whatever the walk met on the way. A seal by published solids has no route either, and is
    BLOCKED, not NO ROUTE: the walls and zones alone had one.

    BOXED is the SPOT, and only the spot (route_to's ``boxed_by`` "spot": no press keeps the rules, and no walker's
    going would change that). A box walkers let go of is never ``boxed`` at all, so it strikes nothing: the walk goes
    on, and its end is judged like any other; one they held past route_to's wait (``boxed_by`` "walkers": villagers
    that walked onto him and stayed) is the village in the way, LIVE."""
    if rec.get("landed") is not None:
        return "bounce"
    if rec.get("blocked"):
        return "live" if any(moving for _uid, moving in rec.get("sealed") or ()) else "blocked"
    if "route" in rec and rec["route"] is None:
        return "no route"
    if rec.get("boxed"):
        return "live" if rec.get("npc_waits") or rec.get("boxed_by") == "walkers" else "boxed"
    if rec.get("inside"):
        return "miss"
    if ("error" not in rec and rec.get("during") is None and not rec.get("reached")
            and (rec.get("waits") or rec.get("pushes") or rec.get("blockers") or rec.get("frozen")
                 or rec.get("npc_replans") or rec.get("box_waits"))):
        return "live"
    return "miss"


class Tour:
    """The blind tour over one side's fields. ``members`` = ``{fork id: donor id}``, THAT side's chain only (one
    Tour per side: with every chain's ids mapped, a member's exit into ANOTHER chain would read as its donor's
    and pass :meth:`gateways`); ``scripts(fid)`` -> the ScriptIndex the game RUNS in field ``fid`` (default: the
    install's); ``stock(fid)`` -> the install's own (the donors' data). Caches live here; a run's memory lives in
    :meth:`run`."""

    def __init__(self, *, members=None, scripts=None, stock=None, tag: str = "rung3"):
        self.stock = stock or T.stock_script_source()
        self.ran = scripts or self.stock
        self.members = {int(f): int(d) for f, d in (members or {}).items()}
        self.tag = tag
        self._names: dict = {}
        self._floors: dict = {}
        self._gates: dict = {}
        self._goals: dict = {}
        self._oneway: dict = {}

    def say(self, *parts) -> None:
        """Every log line, flushed: the first run's block-buffered prints surfaced only at exit."""
        print(f"[{self.tag}]", *parts, flush=True)

    # -- the place a field is ------------------------------------------------------------------------
    def place(self, fid: int) -> int:
        """The donor a fork id runs (the member set), else the field itself."""
        return self.members.get(fid, fid)

    def label(self, fid: int) -> str:
        """The in-game location label of the PLACE ``fid`` is ("Dali/Field")."""
        pid = self.place(fid)
        if pid not in self._names:
            rows = [r for r in extract.find_fields(str(pid)) if int(r["id"]) == pid]
            self._names[pid] = (rows[0]["name"] or "") if rows else ""
        return self._names[pid]

    def floor(self, fid: int):
        """The place's stock walkmesh as the controlled player may walk it (pathfind.PlayerWalkmesh); raises like
        extract.stock_walkmesh when the id has none."""
        pid = self.place(fid)
        if pid not in self._floors:
            self._floors[pid] = pathfind.PlayerWalkmesh(extract.stock_walkmesh(pid))
        return self._floors[pid]

    @staticmethod
    def _scan(idx) -> list:
        """EVERY walk-in gateway of a script, one per distinct (destination, zone), in scan order: [(to,
        entrance, zone)]. 350 lists its 353 exit twice with one zone -- one exit, not two."""
        out = []
        for gw in (eventscan.scan_gateways(idx.data) if idx else []):
            if all((gw["to"], gw["zone"]) != (t, z) for t, _e, z in out):
                out.append((gw["to"], gw["entrance"], gw["zone"]))
        return out

    def gateways(self, fid: int) -> list:
        """Field ``fid``'s gateways as the bytes it RUNS decode them -- for a member, checked to be its donor's
        with only the targets remapped (the rules read the donor's order), or TourError."""
        if fid not in self._gates:
            mine = self._scan(self.ran(fid))
            pid = self.place(fid)
            if pid != fid:
                theirs = self._scan(self.stock(pid))
                same = len(mine) == len(theirs) and all(
                    (e, z) == (e2, z2) and self.place(t) == t2 for (t, e, z), (t2, e2, z2) in zip(mine, theirs))
                if not same:
                    raise TourError(
                        f"field {fid} (member of donor {pid}) runs exits {[(t, e) for t, e, _z in mine]}, not its "
                        f"donor's {[(t, e) for t, e, _z in theirs]} with only the targets remapped -- the donor's "
                        f"rules would walk a different field")
            self._gates[fid] = mine
        return self._gates[fid]

    def exits(self, fid: int) -> list:
        """The exits the tour takes: the gateways whose destination's PLACE carries the location label."""
        return [gw for gw in self.gateways(fid) if self.label(gw[0]).startswith(LABEL)]

    def avoid_for(self, fid: int, zone) -> list:
        """Every OTHER gateway zone of the field -- label-bounded or not: a door out of Dali is still a door."""
        return [z for _t, _e, z in self.gateways(fid) if z != zone]

    def goal_for(self, fid: int, i: int):
        """A standable point inside exit i's zone (pathfind.region_goal on the place's floor), or None."""
        key = (self.place(fid), i)
        if key not in self._goals:
            try:
                self._goals[key] = pathfind.region_goal(self.floor(fid), self.exits(fid)[i][2])
            except (OSError, ValueError, RuntimeError) as err:     # no walkmesh for this id: no goal, no route
                self.say(f"field {fid}: no walkmesh to aim exit {i} on ({type(err).__name__}: {err})")
                self._goals[key] = None
        return self._goals[key]

    def arrival(self, pid: int, entrance: int):
        """Where place ``pid``'s own script stands the player arriving by ``entrance`` (its table row, else its
        default), or None when neither decodes -- 351, 353, 354 and 450 place him some other way."""
        idx = self.stock(pid)
        t = eventscan.scan_arrival_table(idx.data) if idx else {"table": [], "default": None}
        row = next((r for r in t["table"] if r["entrance"] == entrance), None) or t["default"]
        return tuple(row["pos"]) if row else None

    def one_way(self, fid: int, i: int) -> bool:
        """Could the tour NOT walk back out of exit i's destination? Decided on the DONORS' data alone (the
        place's exit, the destination place's arrival spot, floor and exits), so it is one answer on every side.
        True only when the arrival spot is known and none of the destination's exits routes from it (350 -> 358).
        An undecoded arrival is two-way."""
        pid = self.place(fid)
        if (pid, i) not in self._oneway:
            to, entrance, _zone = self.exits(pid)[i]
            pos = self.arrival(to, entrance)
            back = pos is None
            for j, (_t, _e, zone) in enumerate(self.exits(to) if pos is not None else ()):
                goal = self.goal_for(to, j)                    # None also when the walkmesh cannot be read
                if goal is not None and pathfind.route_avoiding(self.floor(to), pos, goal,
                                                                self.avoid_for(to, zone), MARGIN) is not None:
                    back = True
                    break
            self._oneway[(pid, i)] = not back
            if not back:
                self.say(f"place {pid} exit {i} (to {to}, entrance {entrance}) is ONE-WAY: no exit of {to} routes "
                         f"from its arrival {pos} -- it goes last")
        return self._oneway[(pid, i)]

    def next_hop(self, start: int, want, dead: set):
        """BFS over the RUNNING exit graph from ``start`` -- never through an unreachable or a one-way exit -- to
        the nearest field satisfying ``want``: the index of the first exit to take, or None."""
        seen, q = {start}, deque([(start, None)])
        while q:
            f, first = q.popleft()
            if f != start and want(f):
                return first
            for i, (to, _e, _z) in enumerate(self.exits(f)):
                if (self.place(f), i) not in dead and to not in seen and not self.one_way(f, i):
                    seen.add(to)
                    q.append((to, first if first is not None else i))
        return None

    # -- one tour --------------------------------------------------------------------------------------
    def run(self, g, log, *, beat: int, max_crossings: int, max_passes: int, budget_s: float,
            deadline: float | None = None, engine_donor=None) -> str:
        """Tour until SC leaves ``beat``, the passes run out, or the budget does (``budget_s`` from now, and never
        past ``deadline``, the session's). ``engine_donor(fid)`` -> the donor the engine's trace rows name for a
        fork id (None: no row yet); a member whose engine donor is not the member set's stops the tour --
        every rule would read the wrong place. Returns the stop reason."""
        HarnessError = _harness_error()
        t0 = time.time()
        end = t0 + budget_s if deadline is None else min(t0 + budget_s, deadline)
        n = 0
        fails: dict = {}                     # (place, exit) -> its REAL failures (failure()), across passes
        live: dict = {}                      # (place, exit) -> its LIVE misses, across passes
        dead: set = set()                    # (place, exit) unreachable this run
        visit, later = None, set()           # (field, exit)s that failed on THIS visit: its other exits go first
        confirmed: set = set()               # fork ids whose engine donor was read and agreed
        for p in range(1, max_passes + 1):
            tried: set = set()               # (place, exit)

            def open_(h, one_ways=False):
                k = self.place(h)
                return [j for j in range(len(self.exits(h))) if (k, j) not in tried and (k, j) not in dead
                        and (one_ways or not self.one_way(h, j))]

            while True:
                st = g.state
                if st.scenario != beat:
                    return f"SC left {beat}: now {st.scenario} in field {st.field_id} (pass {p}, crossing {n})"
                if n >= max_crossings or time.time() > end:
                    why = "session budget" if deadline is not None and time.time() > deadline else "budget"
                    return f"{why} spent (crossings {n}, {time.time() - t0:.0f}s)"
                f = st.field_id
                k = self.place(f)
                if f != visit:
                    visit, later = f, set()
                    if k != f and f not in confirmed and engine_donor is not None:
                        don = engine_donor(f)
                        if don is not None:
                            rec = {"k": "donor", "field": f, "members": k, "engine": don}
                            log.append(rec)
                            self.say(json.dumps(rec))
                            if don != k:
                                return f"donor mismatch: the engine runs field {f} as {don}, the member set says {k}"
                            confirmed.add(f)
                mine = sorted(open_(f), key=lambda j: (f, j) in later)
                if mine:
                    i, leg = mine[0], "tour"
                else:
                    i, leg = self.next_hop(f, lambda h: bool(open_(h)), dead), "back"
                if i is None:
                    # nothing two-way is left anywhere reachable: now the one-way doors, last -- past one, the
                    # tour may well have no way back
                    mine = sorted(open_(f, True), key=lambda j: (f, j) in later)
                    if mine:
                        i, leg = mine[0], "one-way"
                    else:
                        i, leg = self.next_hop(f, lambda h: bool(open_(h, True)), dead), "back"
                        if i is None:
                            break                                        # this pass has crossed everything
                to, _e, zone = self.exits(f)[i]
                n += 1
                goal = self.goal_for(f, i)
                rec = {"k": "cross", "n": n, "pass": p, "leg": leg, "from": f, "exit": i, "to": to,
                       "target": list(goal) if goal else None, "sc0": st.scenario}
                if k != f or self.place(to) != to:
                    rec.update(place=k, to_place=self.place(to))
                if goal is None:
                    dead.add((k, i))
                    rec.update(verdict="unreachable: no standable goal inside its zone")
                    log.append(rec)
                    self.say(json.dumps(rec))
                    continue
                try:
                    r = g.route_cross(goal[0], goal[1], avoid=self.avoid_for(f, zone), margin=MARGIN,
                                      timeout=CROSS_TIMEOUT, walkmesh=self.floor(f), prior=g.key_prior(k),
                                      unstick=True, zone=zone, smooth=True, npcs=True)
                    rec.update(landed=r["landed"], reached=r["reached"], inside=r["inside"],
                               travelled=round(r["travelled"]), during=r["during"], replans=r["replans"],
                               route=len(r["waypoints"]) if r["waypoints"] is not None else None,
                               waits=r["waits"], cleared=r["cleared"], pushes=r["pushes"], pushed=r["pushed"],
                               blockers=r["blockers"], remembered=r["remembered"], blocked=r["blocked"],
                               frozen=r["frozen"], boxed=r["boxed"], boxed_by=r["boxed_by"], npcs=r["npcs"],
                               avoided=[(o["uid"], o["kind"]) for o in r["avoided"]],
                               entered=[(o["uid"], o["kind"], o["radius"]) for o in r["entered"]],
                               through=[o["uid"] for o in r["through"]],
                               sealed=[(o["uid"], o["moving"]) for o in r["sealed"]], npc_replans=r["npc_replans"],
                               npc_waits=r["npc_waits"], box_waits=r["box_waits"], box_cleared=r["box_cleared"],
                               boxers=[(o["uid"], o["kind"], o["moving"]) for o in r["boxers"]])
                except HarnessError as err:
                    rec.update(landed=None, error=str(err)[:200])
                settle(g, log, f"after crossing {n}", self.say)
                now = g.state.field_id
                if rec.get("landed") is None and now != f and now > 0:
                    # the crossing call gave up but the room DID change -- e.g. the destination held control
                    # past its timeout for an arrival scene ("never became playable"), which settle() just
                    # sat through. Where he stands now is where the crossing led.
                    rec.update(landed=now, landed_late=True)
                if rec.get("landed") == to:
                    if leg != "back":
                        tried.add((k, i))
                    rec["verdict"] = "crossed"
                else:
                    # no route is a failed attempt like the others, not a verdict: it was planned from where he
                    # stood THIS time, and the next visit arrives somewhere else
                    kind = failure(rec)
                    later.add((f, i))
                    tally = (live if kind == "live" else fails).setdefault((k, i), [])
                    tally.append(kind)
                    cap = LIVE if kind == "live" else BOUNCES
                    rec["verdict"] = f"{kind} {len(tally)}/{cap}"
                    if len(tally) >= cap:
                        dead.add((k, i))
                        rec["verdict"] += " -> unreachable"
                    if kind in ("miss", "live", "blocked", "boxed"):
                        g.shot(f"{kind}-{n}-{f}-to-{to}")
                rec.update(now=g.state.field_id, sc1=g.state.scenario, t=round(time.time() - t0))
                log.append(rec)
                self.say(json.dumps(rec))
        return f"passes exhausted ({max_passes}) without the story moving on"
