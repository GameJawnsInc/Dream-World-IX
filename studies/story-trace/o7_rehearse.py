"""O7's REHEARSALS (research/o7_design.md section 7): Steiner's walk through the castle on STOCK Alexandria Castle --
154's balcony and west flight, 158, 159's forced monologue, 160, 162 and 163's stair foot to the arrival in 164 -- stage
by stage, the F-side load smoke and one untraced F pass before the freeze. Each traced stage warps into its start (154
at entrance 315, 163 at 341, or 159 at 331) at SC 1190, drives the DRAFT (a run's stop laid on a COPY and checked) to
its own end fields, and records what the freeze checklist (7.3) is read from; F-SMOKE warps into each member and its
stock twin with NO trace and records what loaded; F-PASS drives one F run through the whole route with NO trace. Nothing
is deployed and nothing is frozen here.

    py tools/play.py studies/story-trace/o7_rehearse.py --label o7-rh --timeout 240              # the default order
    set O7_STAGE=R-FULL & py tools/play.py studies/story-trace/o7_rehearse.py --label o7-rh-full --timeout 240
    set O7_STAGE=R-WALK154 & py tools/play.py studies/story-trace/o7_rehearse.py --label o7-rh-walk154 --timeout 240
    py tools/play.py studies/story-trace/o7_rehearse.py --field 163 --label o7-rh-stair --timeout 240  # R-STAIR
    set O7_STAGE=R-WALK-VOID & py tools/play.py studies/story-trace/o7_rehearse.py --label o7-rh-walk-void --timeout 240
    set O7_STAGE=F-SMOKE & py tools/play.py studies/story-trace/o7_rehearse.py --label o7-rh-smoke --timeout 240
    set O7_STAGE=F-PASS & py tools/play.py studies/story-trace/o7_rehearse.py --label o7-rh-fpass --timeout 240
    py studies/story-trace/o7_castle_walk.py --rehearsal-report <run dir>

WHICH STAGE: the environment variable ``O7_STAGE`` names one (R-FULL, R-WALK154, R-STAIR, R-WALK-VOID, F-SMOKE,
F-PASS); else ``--field 163`` picks R-STAIR, the one stage warping into 163 that is not by-name-only (``--field 154``
names two -- R-FULL and R-WALK154 -- and refuses: name it); else, in one launch: R-FULL (the go/no-go and the
predictions), R-WALK154, R-STAIR, then R-WALK-VOID LAST -- it stops its runs, so a recovery that fails there ends the
launch, and that failure is the finding. F-SMOKE and F-PASS run only by name.

EACH TRACED RUN (7.1): O7.start_run -- THE RESEED (every seeded field's basis forgotten, S and F: 0.2 #20, so EVERY run
of every stage seeds its fields and judges its first moves), New Game, ``wait_frames(30)``, the story trace armed, the
raw warp -- then segment_drive.drive on the stage's predictions with its end fields, the live forbidden scan on, the
run-wide input witness and the recorder (O5's: grants with their published objects and y, pages with ``gone_frame``,
the no-progress stretch -- plus THE STATIC WATCH, the session's own rows, and Dojebon's published position on every poll
in his place) watching every poll; the WALK TAP on ``route_to`` (every call's samples, its basis and record) with THE
LADDER TAP inside it (``_unstick_leg`` wrapped on the instance for the call alone: each entry's sample, the stalled hold
it followed, its outcome and the rungs it climbed -- waits, pushes, the blocker placed after it, frozen, boxed); the HOLD
TAP on ``send`` (every direction hold as it is sent: where he stood, his published y, whether the field's basis was
cached); the trace collected to ``rh_<stage>_<n>.jsonl``; the record written into ``o7_rehearsal.json``; end_run, its
rows and its seconds recorded.

R-WALK-VOID's two runs (``each``): run 1 warps into 154 with ``hold_stop`` {"place": 154, "n": 0, "holds": 3} -- THE HOLD
STOP wraps ``g.send`` on the driver's own thread: before the 4th DIRECTION hold of 154's step 0 sent once the field's
basis is cached (under the seed every hold is a walk hold) it raises "the rehearsal's stop mid-walk", the session's send
restored at once; run 2 warps into 159 with ``page_stop`` {"place": 159} -- THE PAGE STOP wraps ``g.press``: rule 7's
first Confirm while the published field's place is 159 and a window is listed raises "the rehearsal's stop
mid-monologue" BEFORE it is pressed, restored at once. Each stop lies on its step of the run's COPY of the predictions
(the freeze refuses it anywhere: o7_castle_walk.REHEARSAL_OVERLAYS). Never a timer.

F-SMOKE (NO trace): o4_rehearse.smoke on O7's seven pairs -- member(154) / 154 at 315, member(158) / 158 at 300,
member(159) / 159 at 331, member(160) / 160 at 332, member(162) / 162 at 333, member(163) / 163 at 341, member(164) /
164 at 342, all SC 1190 -- each id read from the chain. F-PASS (NO trace; before the freeze): O7.reseed, New Game,
``wait_frames(30)``, the raw warp into member(154), then the drive to member(164) with the live forbidden scan off and
no end-row wait; it may only STOP the session (F13), never shape a frozen value.

WHAT A STAGE MAY SETTLE (7.1): only R-FULL's traces may define or change the keys, the start, the end state or the
pattern. The staged runs prove mechanics. Every summary is cut at the stage's end PLACES (o7_castle_walk.trace_summary).
THE FOOT WINDOW (x 2000-2260, z 3750-4100 in 163 / 31255) is :data:`FOOT_WINDOW` (a seam: ``run(..., foot=...)``):
F5's verdict per run reads every ladder rung that followed a hold starting or ending in it; a rung after a hold wholly
elsewhere on the stair is recorded, never judged.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

import o2_rehearse as O2R                                              # noqa: E402
import o3_rehearse as O3R                                              # noqa: E402
import o4_rehearse as O4R                                              # noqa: E402
import o5_rehearse as O5R                                              # noqa: E402
import o6_rehearse as O6R                                              # noqa: E402
import o7_castle_walk as O                                             # noqa: E402
import segment_drive as SD                                             # noqa: E402
from ff9mapkit import storytrace as T                                  # noqa: E402
from segment_trace import members_of, place                            # noqa: E402

ENV = "O7_STAGE"
#: The stops' own words (the session's V13 reads them back off the outcome).
WALK_STOP = "the rehearsal's stop mid-walk"
PAGE_STOP = "the rehearsal's stop mid-monologue"
#: THE FOOT WINDOW (research/o7_design.md 7.1, 0.2 #12): 163's stair foot -- the pinch, under 120 from z ~3840 to
#: ~3920 -- with its approaches, in 163's frame (31255 on F). F5 reads every ladder rung that followed a hold starting
#: or ending in it.
FOOT_WINDOW = {"place": 163, "x": [2000.0, 2260.0], "z": [3750.0, 4100.0]}
#: A stop's keys (7.1): ``hold_stop`` -- the place, its step (``n``, default 0) and the walk holds sent before the stop;
#: ``page_stop`` -- the place (and ``n``, the step it lies on: default 0).
STOP_KEYS = {"hold_stop": ("place", "n", "holds"), "page_stop": ("place", "n")}
#: The step row keys a run's record keeps (the whole row is in its log file), and the route record's.
STEP_KEYS = ("field", "donor", "visit", "n", "kind", "attempt", "outcome", "frame0", "frame", "to", "lost", "landed",
             "flip_frame", "clearance", "basis", "door", "v", "by", "why", "prior_basis")
ROUTE_KEYS = ("basis", "basis_check", "fps", "waits", "pushes", "pushed", "blockers", "frozen", "boxed", "replans")
#: The stages (research/o7_design.md 7.1): the warp, the end fields (per side where they differ), the runs, a run budget
#: and a cost estimate in seconds a run (F8 replaces every number from what is measured). ``by_name``: never picked by
#: ``--field``; ``optional``: only by name; ``last``: after every other stage of a launch; ``sides``: the sides a stage
#: runs (default S); ``untraced``: no storytrace verb (F-PASS); ``each``: a stage whose runs differ -- run k is the stage
#: with ``each[k-1]`` laid over it (:func:`stage_run`: R-WALK-VOID's warps and stops); ``hold_stop`` / ``page_stop``: a
#: run's stop (:data:`STOP_KEYS`), laid on its step of the run's COPY of the predictions. A member is named
#: ``member(<donor>)``, never by its id: o4_rehearse.stage_ids reads it from the chain.
STAGES = {
    "R-FULL": {"field": 154, "entrance": 315, "sc": 1190, "end": [164], "runs": 2, "run_s": 600, "cost_s": 120,
               "settles": "F1-F8, F10-F11, F14 (the go/no-go and the predictions): every grant (its sample, objects and "
                          "published y), every first-move check, every walk and cross (the route, holds, slides, "
                          "stalls, losses, landings), the monologue (its loss, pages, rows, re-grant), Dojebon static, "
                          "the end cut, the keys, the masked rows, the pattern, the end state (live, and the trace's "
                          "Byte[13]), the run time, the longest no-progress stretch, the render rate -- the ONLY stage "
                          "whose traces define predictions"},
    "R-WALK154": {"field": 154, "entrance": 315, "sc": 1190, "end": [158], "runs": 2, "run_s": 300, "cost_s": 60,
                  "settles": "F2: the balcony grant (y ~1716), no probe pressed, each run's first-move check, step 0's "
                             "arrival on the ground (y ~5 within 45 u of (0, -600)), step 1's loss inside e8 on the "
                             "ground, the landing in 158; THE DESCENT (every hold of the walk: predicted reach, measured "
                             "travel, the slide off the leg, published y at both ends); Dojebon's first reading and his "
                             "published position every poll in 154"},
    "R-STAIR": {"field": 163, "entrance": 341, "sc": 1190, "end": [164], "runs": 2, "run_s": 300, "cost_s": 40,
                "settles": "F5 (the go/no-go): the foot at clearance 110 -- every hold starting or ending in THE FOOT "
                           "WINDOW (its travel, slide and samples: --rehearsal-report measures the narrowest wall gap "
                           "on the stock mesh, level-aware), every ladder rung that followed such a hold; a rung after a "
                           "hold wholly elsewhere on the stair recorded, never judged; the loss in e2; the landing"},
    "R-WALK-VOID": {"each": [{"field": 154, "entrance": 315, "end": [158],
                              "hold_stop": {"place": 154, "n": 0, "holds": 3}},
                             {"field": 159, "entrance": 331, "end": [160], "page_stop": {"place": 159}}],
                    "sc": 1190, "runs": 2, "run_s": 300, "cost_s": 60, "by_name": True, "last": True,
                    "settles": "F9: run 1 stopped before 154 #0's 4th walk hold (on the balcony or the flight, control "
                               "held: hold_stop), run 2 on its first page press in 159 (mid-monologue, 296 up: "
                               "page_stop) -- each run V13, no hold and no press after the raise, end_run's recover-warp "
                               "(4600), then the title"},
    "F-SMOKE": {"pairs": [["member(154)", 154, 315, 1190], ["member(158)", 158, 300, 1190],
                          ["member(159)", 159, 331, 1190], ["member(160)", 160, 332, 1190],
                          ["member(162)", 162, 333, 1190], ["member(163)", 163, 341, 1190],
                          ["member(164)", 164, 342, 1190]], "runs": 1,
                "smoke_s": 8.0, "warp_s": 60.0, "cost_s": 300, "by_name": True, "optional": True,
                "settles": "F12: each member loads at its entrance and SC (its field, FieldHUD), its published object "
                           "sids EQUAL to its stock twin's measured set after smoke_s (only the twin's reading is "
                           "compared); 0 exceptions; end_run ok"},
    "F-PASS": {"field": {"S": 154, "F": "member(154)"}, "entrance": 315, "sc": 1190,
               "end": {"S": [164], "F": ["member(164)"]}, "sides": ["F"], "untraced": True, "runs": 1, "run_s": 600,
               "cost_s": 120, "by_name": True, "optional": True,
               "settles": "F13 (may only STOP the session): one F run through the whole route on the DRAFT, untraced and "
                          "reseeded first -- reached member(164), every beat, no V-class, no exception through the story "
                          "machinery since the warp; its record is never evidence for any key and never shapes a frozen "
                          "value"},
}


def select(stages: dict, field=None, env=None) -> list:
    """The stage names a launch runs: ``O7_STAGE`` (one, by name), else the one stage warping into ``field`` that is
    not ``by_name``, else every non-optional stage in the table's order with the ``last`` ones after the rest --
    R-WALK-VOID ends the launch."""
    env = os.environ if env is None else env
    name = env.get(ENV)
    if name:
        if name not in stages:
            raise ValueError(f"{ENV}={name!r} is no stage: {sorted(stages)}")
        return [name]
    if field is not None:
        hits = [n for n, s in stages.items() if s.get("field") == int(field) and not s.get("by_name")]
        if len(hits) != 1:
            raise ValueError(f"--field {field} picks {hits}: name the stage with {ENV}")
        return hits
    names = [n for n, s in stages.items() if not s.get("optional")]
    return [n for n in names if not stages[n].get("last")] + [n for n in names if stages[n].get("last")]


stage_sides = O5R.stage_sides


def stage_run(stage: dict, n: int) -> dict:
    """Run ``n`` (1-based) of ``stage``: the stage itself, or -- a stage with ``each`` (R-WALK-VOID) -- the stage with
    ``each[n-1]`` laid over a copy (its warp, its end and its stop) and ``each`` dropped. ValueError for a run the stage
    has no entry for, or an ``each`` whose length is not the stage's ``runs``."""
    each = stage.get("each")
    if each is None:
        return stage
    if not isinstance(each, list) or len(each) != int(stage.get("runs", 0)):
        raise ValueError(f"each: one entry a run ({stage.get('runs')} runs), not {each!r}")
    if not 1 <= int(n) <= len(each):
        raise ValueError(f"run {n}: the stage has {len(each)} run(s)")
    s = {k: copy.deepcopy(v) for k, v in stage.items() if k != "each"}
    s.update(copy.deepcopy(each[int(n) - 1]))
    return s


def _stop_step(pred: dict, key: str, stop) -> dict:
    """The table step a run's stop lies on (:data:`STOP_KEYS`): place ``stop["place"]``'s ONE cell, its step
    ``stop.get("n", 0)``. ValueError, naming the stop, for anything else -- an unknown key, a place that is no int or
    has no single cell, a step it does not have, a ``hold_stop`` whose ``holds`` is no int >= 0."""
    if not isinstance(stop, dict) or not SD._is_int(stop.get("place")):
        raise ValueError(f"{key}: a dict with the place, e.g. {{'place': 154}}, not {stop!r}")
    unknown = sorted(set(stop) - set(STOP_KEYS[key]))
    if unknown:
        raise ValueError(f"{key} {stop}: no key {unknown} (a {key} takes {list(STOP_KEYS[key])})")
    if key == "hold_stop" and not (SD._is_int(stop.get("holds")) and stop["holds"] >= 0):
        raise ValueError(f"hold_stop {stop}: holds is an int >= 0 (the walk holds sent before the stop)")
    n = stop.get("n", 0)
    cells = [c for c in pred.get("table") or () if c.get("donor") == stop["place"]]
    if len(cells) != 1 or not SD._is_int(n) or not 0 <= n < len(cells[0]["steps"]):
        raise ValueError(f"{key} {stop}: {len(cells)} table cell(s) of place {stop['place']} -- not one cell with a "
                         f"step #{n}")
    return cells[0]["steps"][n]


def stage_pred(pred: dict, stage: dict) -> dict:
    """The draft with the run's own start on each side, entrance and scenario; the run's stop (``hold_stop`` /
    ``page_stop``: o7_castle_walk.REHEARSAL_OVERLAYS, the keys the freeze refuses) laid on its step of the COPY
    (:func:`_stop_step`; a run stops one way); for an untraced stage, no end-row wait (``end_row_s`` None: no trace to
    wait on). Then checked as the driver will read it -- segment_drive.naming_of, witness_of and step_of on every table
    step -- so a bad stop refuses before anything is driven. ``stage`` is ONE run's (:func:`stage_run`). The predictions
    given are never changed."""
    if stage.get("each") is not None:
        raise ValueError("a stage with each is laid run by run: stage_pred(pred, stage_run(stage, n))")
    p = copy.deepcopy(pred)
    p.update(start={"S": O4R.stage_start(stage, "S"), "F": O4R.stage_start(stage, "F")}, entrance=stage["entrance"],
             scenario=stage["sc"])
    over = {k: stage[k] for k in sorted(O.REHEARSAL_OVERLAYS) if stage.get(k) not in (None, False)}
    if len(over) > 1:
        raise ValueError(f"a run stops one way, not {sorted(over)}")
    for k, v in over.items():
        step = _stop_step(p, k, v)
        step[k] = {x: y for x, y in v.items() if x not in ("place", "n")} or True
    if stage.get("untraced"):
        p["budget"] = dict(p.get("budget") or {}, end_row_s=None)
    SD.naming_of(p)
    SD.witness_of(p)
    for c in p.get("table") or ():
        for s in c["steps"]:
            SD.step_of(p, s)
    return p


def field_of(pred: dict, side: str, where: int) -> int | None:
    """The field place ``where`` is on ``side``: itself on S, the one member forking it on F (else None)."""
    if side != "F":
        return where
    hits = sorted(f for f, d in members_of(pred).items() if d == where)
    return hits[0] if len(hits) == 1 else None


def _r(v):
    return None if v is None else round(float(v), 1)


def in_window(foot: dict, p) -> bool:
    """Whether point ``p`` -- ``[x, z]`` or ``{"x", "z"}`` -- stands in THE FOOT WINDOW ``foot`` (its x and z bands,
    both ends included)."""
    if p is None:
        return False
    x, z = (p.get("x"), p.get("z")) if isinstance(p, dict) else (p[0], p[1])
    if x is None or z is None:
        return False
    return foot["x"][0] <= x <= foot["x"][1] and foot["z"][0] <= z <= foot["z"][1]


# ======================================================================== the run's own instruments
#: A grant's published objects as 7.2 keeps them (O5's).
GRANT_OBJECT_KEYS = ("sid", "uid", "x", "z", "shown", "coll", "solid", "r", "talk_r", "range_r")


class Recorder(O5R.Recorder):
    """O5's recorder (pages with ``gone_frame``, the published choices, the no-progress stretch, the dialog-section
    catch -- no guard, no stair teleport) with THE GRANTS read off the RING (:meth:`grant_scan`), plus THE STATIC WATCH
    (o7_castle_walk.static_watch: the session's own ``static`` rows, one ``seen`` a visit and one ``moved``, written into
    the driver's ``log``) and each watched object's published (x, z) on EVERY poll in its place (``polls``: Dojebon's in
    154 / member(154), 7.2)."""

    def __init__(self, g, stage: dict, pred: dict, log: list):
        super().__init__(g, stage, pred, guard={})
        self.walk_place = None                          # O5's stair teleport: O7's walk has none
        self.members = members_of(pred)
        self.places = set(pred.get("visits") or pred.get("route") or ())
        self.static = O.static_watch(pred, log)
        self.watched = [(o["donor"], o["sid"]) for o in pred.get("static_objects") or ()]
        self.polls: dict = {k: [] for k in self.watched}
        self._gscanned = None                           # the ring's last frame grant_scan read
        self._gcontrol = None                           # control on that sample

    def arm(self, frame: int) -> None:
        """THE GRANTS' scan from ``frame`` on -- the run's start, before its New Game and warp -- so the first visit's
        grant is read however late the driver's first poll comes."""
        self._gscanned, self._gcontrol = int(frame) - 1, None

    def grant_scan(self, st, ctx: dict) -> None:
        """THE GRANTS (7.2, F1) off the RING at every poll -- each sample the harness read since the last scan (since
        :meth:`arm`'s frame at first), once, oldest first: every move from no control to control with his position
        published, in a field of the route's places, is a grant (its frame, field, place, the poll's SC, x, z, published
        y, the launch's rate, the published objects there). The driver polls only between steps, so a grant made inside
        one -- route_to's wait for the landing, then for control in the next field -- never reaches a poll as a change,
        and O2's poll-to-poll rule would miss it; the ring kept it. New Game's field 70 is no route place."""
        since = st.frame - 1 if self._gscanned is None else self._gscanned
        try:
            raws = self.g.states_since(since)
        except Exception:                                      # noqa: BLE001 -- a record, never the run
            return
        for raw in raws:
            f = int(raw.get("frame", -1))
            if self._gscanned is not None and f <= self._gscanned:
                continue
            self._gscanned = f
            p = raw.get("player") or {}
            control = bool(p.get("control", False))
            fld = int((raw.get("field") or {}).get("id", -1))
            if (control and self._gcontrol is False and p.get("x") is not None
                    and place(fld, self.members) in self.places):
                objs = raw.get("objects")
                self.grants.append({"t": round(time.time(), 2), "frame": f, "field": fld,
                                    "donor": place(fld, self.members), "sc": ctx.get("sc"), "x": p.get("x"),
                                    "z": p.get("z"), "y": p.get("y"), "fps": self._fps(),
                                    "objects": None if not isinstance(objs, list) else
                                    [{k: o.get(k) for k in GRANT_OBJECT_KEYS} for o in objs]})
            self._gcontrol = control

    def __call__(self, st, ctx: dict) -> None:
        n = len(self.grants)
        super().__call__(st, ctx)
        del self.grants[n:]                             # O2's poll-to-poll grants: the ring's scan reads every sample
        self.grant_scan(st, ctx)
        self.static(st, ctx)
        here = ctx.get("donor")
        for donor, sid in self.watched:
            if here != donor:
                continue
            b = next((o for o in st.objects or () if o.get("sid") == sid), None)
            if b is not None and b.get("x") is not None and b.get("z") is not None:
                self.polls[(donor, sid)].append([st.frame, round(float(b["x"]), 1), round(float(b["z"]), 1)])


class HoldTap:
    """THE HOLD TAP (7.2): ``g.send`` wrapped on the instance -- each request holding a DIRECTION hold recorded as it is
    sent: its wall time, the published frame, field, position, y and control, and whether that field's basis was
    cached in ``g._axes`` then (``cached`` False: a calibration probe, never a walk hold) -- then sent. :meth:`last` is
    the last hold sent in a field (THE LADDER TAP's stalled hold); :meth:`restore` puts the session's own back."""

    def __init__(self, g):
        self.g, self.holds = g, []
        self._had = "send" in vars(g)
        self._orig = vars(g).get("send")
        real = g.send

        def send(*steps, **kw):
            if any(O6R._direction_hold(s) for s in steps):
                st = g.state
                self.holds.append({"t": time.time(), "frame": st.frame, "field": st.field_id, "x": _r(st.player_x),
                                   "z": _r(st.player_z), "y": _r(st.player_y), "control": bool(st.control),
                                   "cached": O6R._cached(g, st.field_id), "steps": [str(s) for s in steps]})
            return real(*steps, **kw)
        g.send = send

    def last(self, field) -> dict | None:
        h = next((h for h in reversed(self.holds) if h["field"] == field), None)
        return None if h is None else {k: h[k] for k in ("frame", "x", "z", "y")}

    def restore(self) -> None:
        if self._had:
            self.g.send = self._orig
        else:
            vars(self.g).pop("send", None)


def _counters(record) -> dict:
    r = record if isinstance(record, dict) else {}
    return {"waits": int(r.get("waits") or 0), "pushes": int(r.get("pushes") or 0),
            "blockers": len(r.get("blockers") or ()), "frozen": bool(r.get("frozen")), "boxed": bool(r.get("boxed"))}


def ladder_rungs(entries: list, final) -> list:
    """THE LADDER TAP's entries of one route call, each with the RUNGS it climbed (7.2), pure: ``wait`` for each wait
    counted during it, ``push`` for each push, ``blocker`` for each unseen blocker route_to placed after it (the entry's
    own count: :class:`WalkTap` taps ``_blocker_ahead``, route_to's one placement -- the record's list is no witness, a
    call whose replans never moved him withdraws it), ``boxed`` when it returned "boxed", ``frozen`` on the call's LAST
    entry when the record (``final``) ended frozen. Each entry keeps its sample, the stalled hold it followed
    (``after_hold``: that hold's start), its ``outcome`` (``_unstick_leg``'s return) and where its blockers went."""
    out = []
    end = _counters(final)
    for i, e in enumerate(entries):
        b, a = e["before"], e.get("after") or e["before"]
        rungs = (["wait"] * max(0, a["waits"] - b["waits"]) + ["push"] * max(0, a["pushes"] - b["pushes"])
                 + ["blocker"] * int(e.get("blockers") or 0))
        if e.get("outcome") == "boxed":
            rungs.append("boxed")
        if i == len(entries) - 1 and end["frozen"]:
            rungs.append("frozen")
        out.append({**{k: e.get(k) for k in ("frame", "field", "x", "z", "y", "after_hold", "outcome")},
                    "blockers_at": list(e.get("blockers_at") or []), "rungs": rungs})
    return out


class WalkTap(O5R.WalkTap):
    """THE WALK TAP (7.2; O5's): the session's ``route_to`` wrapped on the instance -- each call's untrimmed record (its
    waypoints, pushes, basis, ``basis_check``, rate, waits, blockers, frozen, boxed), whether its field's basis was
    cached when it began, and every sample its own reads kept (with y), taken the moment it returns -- plus THE LADDER
    TAP (rev. 2, the driver review #8): for the call alone ``_unstick_leg`` is wrapped ON THE INSTANCE (restored at the
    call's end, as the hold stop restores ``send``), each entry recorded -- its sample (frame, field, x, z, y), the
    stalled hold it followed (the hold tap's last hold in the field: its start), its outcome and its counters -- and so
    is ``_blocker_ahead``, route_to's one unseen-blocker placement, each placement counted on the entry it followed;
    all turned into rungs at the call's end (:func:`ladder_rungs`)."""

    def __init__(self, g, holds: HoldTap):
        self.holds = holds
        super().__init__(g)

    def _route_to(self, *a, **k):
        g = self.g
        st = g.state
        t0, rec, entries, held = time.time(), None, [], {}
        cached = O6R._cached(g, st.field_id)
        kept = {n: ("_" + n in vars(g), vars(g).get("_" + n)) for n in ("unstick_leg", "blocker_ahead")}
        real, real_ba = g._unstick_leg, g._blocker_ahead

        def unstick(*ua, **uk):
            record = ua[6] if len(ua) > 6 else uk.get("record")
            held["record"] = record
            s = g.state
            e = {"frame": s.frame, "field": s.field_id, "x": _r(s.player_x), "z": _r(s.player_z),
                 "y": _r(s.player_y), "after_hold": self.holds.last(s.field_id), "outcome": None,
                 "before": _counters(record), "blockers": 0, "blockers_at": []}
            entries.append(e)
            try:
                got = real(*ua, **uk)
                e["outcome"] = got
                return got
            finally:
                e["after"] = _counters(record)

        def blocker_ahead(*ba, **bk):
            body = real_ba(*ba, **bk)
            if entries:
                entries[-1]["blockers"] += 1
                entries[-1]["blockers_at"].append([round(float(body[0])), round(float(body[1]))])
            return body
        g._unstick_leg, g._blocker_ahead = unstick, blocker_ahead
        try:
            rec = self._real(*a, **k)
            return rec
        finally:
            for n, (had, orig) in kept.items():
                if had:
                    setattr(g, "_" + n, orig)
                else:
                    vars(g).pop("_" + n, None)
            try:
                raws = g.states_since(st.frame - 1)
            except Exception:                                  # noqa: BLE001 -- a record, never the run
                raws = []
            final = rec if isinstance(rec, dict) else held.get("record")
            r = final if isinstance(final, dict) else {}
            self.walks.append({"t0": t0, "t1": time.time(), "frame0": st.frame, "field": st.field_id,
                               "start": [st.player_x, st.player_z], "goal": [float(v) for v in a[:2]],
                               "waypoints": [[float(v) for v in p[:2]] for p in r.get("waypoints") or ()],
                               "pushes": r.get("pushes"), "pushed": r.get("pushed"), "waits": r.get("waits"),
                               "blockers": r.get("blockers"), "frozen": r.get("frozen"), "boxed": r.get("boxed"),
                               "basis": r.get("basis"), "basis_check": r.get("basis_check"), "fps": r.get("fps"),
                               "cached_before": cached, "ladder": ladder_rungs(entries, final),
                               "samples": [O5R._raw_sample(x) for x in raws]})


class HoldStop:
    """R-WALK-VOID run 1's STOP (7.1, F9): ``g.send`` wrapped on the driver's own thread -- the direction holds of place
    ``place``'s step ``n`` sent in ``field`` once its basis is cached in ``g._axes`` (under the seed every hold is a walk
    hold: O6's hold tap tells a probe from a hold) are counted; the (``holds``+1)-th raises "the rehearsal's stop
    mid-walk" BEFORE it is sent, the session's own send restored at once (end_run's warp and ladder go through it;
    nothing keeps sending after the raise). The step is read off the driver's ``log``: step ``n`` runs while the place
    holds ``n`` done step rows. ``fired``: the stop's frame, field, position, y, wall time, and the steps it held back;
    ``count`` the walk holds sent before it. Never a timer."""

    def __init__(self, g, field: int, *, place: int, n: int, holds: int, log: list):
        from harness import HarnessError
        self.g, self.field, self.place, self.n, self.holds, self.log = g, int(field), int(place), int(n), int(holds), log
        self.count, self.fired = 0, None
        self._had = "send" in vars(g)
        self._orig = vars(g).get("send")
        real = g.send

        def send(*steps, **kw):
            if self.fired is None and any(O6R._direction_hold(s) for s in steps):
                st = g.state
                if st.field_id == self.field and self.in_step() and O6R._cached(g, self.field):
                    if self.count >= self.holds:
                        self.fired = {"t": time.time(), "frame": st.frame, "field": st.field_id, "x": _r(st.player_x),
                                      "z": _r(st.player_z), "y": _r(st.player_y), "control": bool(st.control),
                                      "steps": [str(s) for s in steps]}
                        self.restore()
                        raise HarnessError(f"{WALK_STOP}: before walk hold {self.count + 1} of {self.place} #{self.n} at "
                                           f"({self.fired['x']}, {self.fired['z']}) in {self.field}, never sent")
                    self.count += 1
            return real(*steps, **kw)
        g.send = send

    def in_step(self) -> bool:
        done = sum(1 for r in self.log if r.get("k") == "step" and r.get("donor") == self.place
                   and r.get("outcome") == "done")
        return done == self.n

    def restore(self) -> None:
        if self._had:
            self.g.send = self._orig
        else:
            vars(self.g).pop("send", None)


class PageStop:
    """R-WALK-VOID run 2's STOP (7.1, F9): ``g.press`` wrapped on the instance -- the first Confirm pressed while the
    published field's place is ``where`` and a window is listed (rule 7's first page press there: 296 up) raises "the
    rehearsal's stop mid-monologue" BEFORE it is pressed, the session's own press restored at once, so nothing presses
    after it. ``fired``: the stop's wall time, frame, field, UI, position and the windows listed."""

    def __init__(self, g, *, where: int, members: dict):
        from harness import HarnessError
        self.g, self.place, self.members, self.fired = g, int(where), dict(members or {}), None
        self._had = "press" in vars(g)
        self._orig = vars(g).get("press")
        real = g.press

        def press(*a, **kw):
            button = a[0] if a else kw.get("button")
            if self.fired is None and str(button).lower() == "confirm":
                st = g.state
                if place(st.field_id, self.members) == self.place and list(st.texts or ()):
                    self.fired = {"t": time.time(), "frame": st.frame, "field": st.field_id, "ui": st.ui_state,
                                  "x": _r(st.player_x), "z": _r(st.player_z), "control": bool(st.control),
                                  "texts": [str(t)[:80] for t in st.texts]}
                    self.restore()
                    raise HarnessError(f"{PAGE_STOP}: the first page press in {st.field_id} (place {self.place}), "
                                       f"{len(self.fired['texts'])} window(s) listed, never pressed")
            return real(*a, **kw)
        g.press = press

    def restore(self) -> None:
        if self._had:
            self.g.press = self._orig
        else:
            vars(self.g).pop("press", None)


# ======================================================================== the records (pure)
def _y_at(walks: list, field, frame):
    """His published y at ``frame`` in ``field``: the walk samples' at that frame, else the last before it, else None."""
    best = None
    for w in walks:
        for s in w.get("samples") or ():
            if s.get("field") != field or s.get("y") is None or frame is None or s["frame"] > frame:
                continue
            if best is None or s["frame"] >= best["frame"]:
                best = s
    return None if best is None else _r(best["y"])


def step_records(log: list, walks: list) -> tuple:
    """``(steps, bases)``, pure: every driver step row trimmed (:data:`STEP_KEYS`, its route record's
    :data:`ROUTE_KEYS`, the rate -- ``fps``, which a step row's trimmed record drops -- from the walk tap's own record of
    the call); and per routed step row THE BASES (7.2) -- its field, place, visit, step and attempt, the basis
    the call walked on (the route record's ``basis``: "prior" when it seeded, "cached" when it found one; with none --
    a step without ``basis`` -- "calibrated" when the field had no basis as the call began, else "cached") and its
    ``basis_check`` (the seeded first move judged)."""
    steps, bases = [], []
    for r in log or ():
        if r.get("k") != "step":
            continue
        route = r.get("route") or {}
        walk = O6R._walk_of(walks, r) if route else None
        s = {k: r.get(k) for k in STEP_KEYS if k in r}
        s["route"] = {k: route.get(k) for k in ROUTE_KEYS if k in route}
        if route and s["route"].get("fps") is None:       # a step row trims the rate away: the call's own record
            s["route"]["fps"] = None if walk is None else walk.get("fps")
        steps.append(s)
        if not route:
            continue
        label = route.get("basis") or (None if walk is None else ("cached" if walk.get("cached_before")
                                                                  else "calibrated"))
        bases.append({"field": r.get("field"), "donor": r.get("donor"), "visit": r.get("visit"), "n": r.get("n"),
                      "attempt": r.get("attempt"), "kind": r.get("kind"), "basis": label,
                      "check": route.get("basis_check"), "prior_basis": r.get("prior_basis")})
    return steps, bases


def _hold_ys(walk: dict, rows: list) -> list:
    """Each hold row's published y at its start and end (the walk's own samples: the previous hold's ack, or the walk's
    first frame, then its own ack)."""
    out, prev = [], walk.get("frame0")
    samples = walk.get("samples") or []
    for h in rows:
        a, b = O5R._at(samples, prev), O5R._at(samples, h["ack_frame"])
        out.append((None if a is None else _r(a.get("y")), None if b is None else _r(b.get("y"))))
        prev = h["ack_frame"]
    return out


def descent_record(walks: list, log: list, steps: list, axes: dict, *, fps=None, tick_hz=30.0) -> dict:
    """THE DESCENT (7.2; 0.2 #17), pure: every hold of every ``walk``-kind step's walk (154 #0's: the west arm, the
    flight, the ground) -- its ack frame and attempt, where it began and ended, how far it moved against its PREDICTED
    REACH (its frames at a run: o7_castle_walk.RUN_U_PER_TICK a tick, ``tick_hz / fps`` ticks a frame), the slide off
    the leg (``off_leg``) and off the pressed direction (``off_pressed``, ``slide``), ``stall``, and the published y at
    both ends."""
    out = []
    for s in (r for r in log or () if r.get("k") == "step" and r.get("kind") == "walk"):
        walk = O6R._walk_of(walks, s)
        if walk is None:
            continue
        rows = O5R.hold_rows(walk, list(steps), axes.get(walk["field"]))
        for h, (y0, y1) in zip(rows, _hold_ys(walk, rows)):
            reach = (None if not fps or h.get("frames") is None
                     else round(h["frames"] * O.RUN_U_PER_TICK * tick_hz / fps, 1))
            out.append({"frame": h["ack_frame"], "field": walk["field"], "donor": s.get("donor"), "n": s.get("n"),
                        "attempt": s.get("attempt"), "from": h["from"], "to": h["to"], "frames": h.get("frames"),
                        "reach": reach, "moved": h["moved"], "off_leg": h["off_leg"], "off_pressed": h["off_pressed"],
                        "slide": h["slide"], "stall": h["stall"], "control_lost": h["control_lost"], "y0": y0, "y1": y1})
    return {"holds": out}


#: A walk hold as THE WALKS keep it (o5_rehearse.hold_rows's row less its request).
HOLD_KEYS = ("ack_frame", "frames", "from", "to", "moved", "leg", "off_leg", "off_pressed", "slide", "stall",
             "control_lost")


def walks_record(walks: list, log: list, steps: list, axes: dict) -> list:
    """THE WALKS (7.2: O6's walk tap record, every step's; F4), pure: per routed step row, its route call (the walk
    tap's, joined by field and frames) -- the start, the goal and the planned waypoints, every hold
    (o5_rehearse.hold_rows: where it began and ended, its travel, the leg it pressed on, the slide off that leg and off
    the pressed direction, the stall; :data:`HOLD_KEYS`), how many samples its reads kept, the last control sample and
    the first without -- tied to the row's place, visit, step, attempt and outcome."""
    out = []
    for r in (x for x in log or () if x.get("k") == "step" and x.get("route")):
        w = O6R._walk_of(walks, r)
        if w is None:
            continue
        hr = O5R.hold_rows(w, list(steps), axes.get(w["field"]))
        samples = w.get("samples") or []
        last_c = first_without = None
        for x in samples:
            if x["control"]:
                last_c = x
            elif last_c is not None:
                first_without = x
                break
        out.append({**{k: r.get(k) for k in ("field", "donor", "visit", "n", "attempt", "outcome")},
                    "start": w.get("start"), "goal": w.get("goal"), "waypoints": w.get("waypoints"),
                    "holds": [{k: h.get(k) for k in HOLD_KEYS} for h in hr], "samples": len(samples),
                    "last_control": last_c, "first_without": first_without})
    return out


def levels_record(grants: list, log: list, walks: list, steps: list, axes: dict) -> dict:
    """THE LEVELS (7.2), pure: the published y at each grant (``[field, frame, y]``), at each step row's loss (its
    frame's sample in the walks', else the last before it) and at the start and end of EVERY walk hold in a field of
    the walk's place (154 / 31246: its ``walk``-kind steps' -- the walk's holds and the cross's after it;
    ``[field, frame, y0, y1]``)."""
    losses = []
    for r in log or ():
        lost = r.get("lost") if r.get("k") == "step" else None
        if lost and lost.get("frame") is not None:
            fld = lost.get("field", r.get("field"))
            losses.append([fld, lost["frame"], _y_at(walks, fld, lost["frame"])])
    rows = [r for r in log or () if r.get("k") == "step"]
    places = {r.get("donor") for r in rows if r.get("kind") == "walk"}
    fields = {r.get("field") for r in rows if r.get("donor") in places}
    holds = []
    for w in walks:
        if w["field"] not in fields:
            continue
        hr = O5R.hold_rows(w, list(steps), axes.get(w["field"]))
        holds += [[w["field"], h["ack_frame"], y0, y1] for h, (y0, y1) in zip(hr, _hold_ys(w, hr))]
    return {"grants": [[g.get("field"), g.get("frame"), _r(g.get("y"))] for g in grants or ()],
            "losses": losses, "walk_holds": holds}


def ladder_record(walks: list, log: list, foot: dict, members: dict) -> list:
    """THE LADDER (7.2), pure: every route call's rungs (:class:`WalkTap`), in order, each tied to its step and attempt
    (the step row of its field whose frames hold it) and flagged ``foot`` when it lies in THE FOOT WINDOW's place and
    the stalled hold it followed STARTED (``after_hold``) or ENDED (the rung's own sample) in the window."""
    rows = [r for r in log or () if r.get("k") == "step"]
    out = []
    for w in walks:
        for x in w.get("ladder") or ():
            s = next((r for r in rows if r.get("field") == x["field"] and r.get("frame0") is not None
                      and r["frame0"] - 2 <= x["frame"] <= (r.get("frame") or x["frame"])), None)
            here = place(x["field"], members) == foot["place"]
            out.append({**x, "place": place(x["field"], members),
                        "step": None if s is None else {k: s.get(k) for k in ("donor", "visit", "n", "attempt")},
                        "foot": bool(here and (in_window(foot, x.get("after_hold")) or in_window(foot, x)))})
    return out


def squeeze_record(walks: list, log: list, ladder: list, steps: list, axes: dict, foot: dict, members: dict) -> dict:
    """THE SQUEEZE (7.2, F5), pure: in THE FOOT WINDOW's place, every hold of every walk -- its ack frame, start, end,
    pressed direction (through the basis), travel, slide and stall -- ``foot`` when it STARTED or ENDED in the window,
    such a hold with its samples (``[frame, x, y, z]``: --rehearsal-report measures the narrowest wall gap on them, on
    the stock mesh, level-aware); every ladder rung there (``rungs``), those after a hold wholly elsewhere apart
    (``elsewhere``: recorded, never judged); and F5's verdict for the run -- GO when the place's step is done and no rung
    followed a foot hold, else NO-GO naming why. A run that never walked there: ``{}``."""
    fp = foot["place"]
    mine = [w for w in walks if place(w["field"], members) == fp]
    if not mine:
        return {}
    holds = []
    for w in mine:
        basis = axes.get(w["field"])
        rows = O5R.hold_rows(w, list(steps), basis)
        prev = w.get("frame0")
        for h in rows:
            pressed = O5R.pressed_dir(basis, [str(s).split() for s in h.get("steps") or () if str(s).startswith("hold ")])
            f = in_window(foot, h["from"]) or in_window(foot, h["to"])
            hold = {"frame": h["ack_frame"], "field": w["field"], "from": h["from"], "to": h["to"],
                    "pressed": None if pressed is None else [round(pressed[0], 3), round(pressed[1], 3)],
                    "moved": h["moved"], "slide": h["slide"], "stall": h["stall"], "foot": f}
            if f:
                hold["samples"] = [[x["frame"], x.get("x"), x.get("y"), x.get("z")] for x in w.get("samples") or ()
                                   if x.get("x") is not None and prev is not None and prev <= x["frame"] <= h["ack_frame"]]
            holds.append(hold)
            prev = h["ack_frame"]
    rungs = [x for x in ladder if x.get("place") == fp]
    bad = [x for x in rungs if x.get("foot")]
    done = any(r.get("outcome") == "done" for r in log or () if r.get("k") == "step" and r.get("donor") == fp)
    if not done:
        f5 = f"NO-GO: {fp}'s step is not done in this run"
    elif bad:
        f5 = (f"NO-GO: a ladder rung ({'/'.join(bad[0]['rungs']) or bad[0].get('outcome')}) at frame {bad[0]['frame']} "
              f"followed a hold that started or ended in THE FOOT WINDOW")
    else:
        f5 = "GO"
    return {"place": fp, "window": {"x": list(foot["x"]), "z": list(foot["z"])}, "holds": holds,
            "foot_holds": [h for h in holds if h["foot"]], "rungs": rungs,
            "elsewhere": [x for x in rungs if not x.get("foot")], "narrowest": None, "f5": f5}


def dojebon_record(rec_obs, log: list, pred: dict) -> dict:
    """DOJEBON (7.2, F2), pure but for the recorder's polls: the first static object's per-visit reading through the
    session's own rows (o7_castle_walk.static_lines) -- its first visit's ``seen`` row (None: UNOBSERVED) and ``moved``
    row (None: none), every visit's -- and his published (x, z) on every poll in his place. ``{}`` when the run never
    reached it."""
    objs = list(pred.get("static_objects") or ())
    if not objs:
        return {}
    o = objs[0]
    lines = [x for x in O.static_lines(log, pred) if x[0] is o and x[1] is not None]
    if not lines:
        return {}
    visits = [{"visit": v.get("visit"), "field": v.get("field"), "frame": v.get("frame"), "seen": s, "moved": m}
              for _o, v, s, m in lines]
    return {"name": o.get("name"), "donor": o["donor"], "sid": o["sid"], "seen": visits[0]["seen"],
            "moved": visits[0]["moved"], "visits": visits,
            "polls": list((getattr(rec_obs, "polls", None) or {}).get((o["donor"], o["sid"]), []))}


def monologue_record(log: list, pred: dict, rec_obs, trace: dict, *, steps=(), events=(), members=None) -> dict:
    """THE MONOLOGUE (7.2, F3), pure: the registered interruption's place -- its ``interrupted`` rows (each attempt's
    frames and loss), the pages the recorder saw from the first loss to the re-grant (each first and gone frame), every
    rule-7 Confirm decided on them joined to its request (o5_rehearse.page_requests: its seq, decision, accepted, down
    and ack frames -- a dropped Confirm has no accepted frame), the trace's three rows with their frames (the summary's
    ``interruption_rows``), THE RE-GRANT (the first grant in the place after the loss: its sample and its distance from
    the loss) and the re-run (the next step row: its outcome and its loss). ``{}`` when no interruption is registered or
    the run never reached its place."""
    regs = list(pred.get("interruptions") or ())
    if not regs:
        return {}
    where = regs[0]["donor"]
    members = members or {}
    rows = [r for r in log or () if r.get("k") == "step" and r.get("donor") == where]
    if not rows:
        return {}
    inter = [r for r in rows if r.get("outcome") == "interrupted"]
    first = inter[0] if inter else None
    loss = (first or {}).get("lost") or {}
    lo = loss.get("frame")
    regrant = None
    if lo is not None:
        gr = next((g for g in rec_obs.grants if place(g.get("field"), members) == where and g["frame"] > lo), None)
        if gr is not None:
            d = (None if loss.get("x") is None or gr.get("x") is None
                 else round(((gr["x"] - loss["x"]) ** 2 + (gr["z"] - loss["z"]) ** 2) ** 0.5, 1))
            regrant = {"frame": gr["frame"], "x": _r(gr.get("x")), "z": _r(gr.get("z")), "y": _r(gr.get("y")),
                       "from_loss": d}
    hi = None if regrant is None else regrant["frame"]
    pages = [{"text": p["text"][:80], "frame": p["frame"], "gone_frame": p.get("gone_frame")}
             for p in rec_obs.pages if lo is not None and place(p.get("field"), members) == where
             and p["frame"] >= lo and (hi is None or p["frame"] <= hi)]
    confirms = []
    for row, q in O5R.page_requests(log, list(steps), list(events)):
        pre = (row.get("pre") or {}).get("frame")
        if row.get("donor") != where or lo is None or pre is None or pre < lo or (hi is not None and pre > hi):
            continue
        confirms.append({"seq": q["seq"], "decision_frame": pre, "accepted_frame": q["accepted_frame"],
                         "down_frame": q["down_frame"], "ack_frame": q["ack_frame"]})
    nxt = next((r for r in rows if first is not None and r is not first and (r.get("frame0") or -1) >= (first.get("frame")
                                                                                                         or 0)), None)
    return {"place": where, "interrupted": [{k: r.get(k) for k in ("attempt", "frame0", "frame", "lost")} for r in inter],
            "pages": pages, "confirms": confirms, "rows": list((trace or {}).get("interruption_rows") or []),
            "regrant": regrant,
            "rerun": None if nxt is None else {k: nxt.get(k) for k in ("attempt", "outcome", "lost", "landed", "door")}}


def _confirms_between(steps: list, t0: float, t1: float) -> list:
    """The Confirm requests sent in (``t0``, ``t1``): steps.jsonl rows pressing a Confirm."""
    return [r for r in steps if t0 < float(r.get("t", 0)) < t1 and SD._press_button(r.get("steps")) in SD.CONFIRM_NAMES]


def _rate_record(g) -> dict:
    """The launch's measured render rate now (``g.rate().as_dict()``), or ``{"fps": None}``."""
    try:
        return g.rate().as_dict()
    except Exception:                                          # noqa: BLE001 -- a record, never the run
        return {"fps": None}


# ======================================================================== a run, an untraced start, a launch
def fpass_start(g, side: str, spred: dict) -> None:
    """F-PASS's UNTRACED start (7.1): O7.reseed FIRST (every seeded field forgotten, S and F), then O5's -- New Game,
    ``wait_frames(30)``, the raw warp into the side's start at the stage's entrance and SC, the wait for the field --
    Segment.start_run without the ``storytrace`` verb."""
    O.O7.reseed(g, spred)
    O5R.fpass_start(g, side, spred)


def one(g, name: str, stage: dict, pred: dict, n: int, *, side: str = "S", t0: float, floor_for=None,
        prior_for=None, stock=None, recovery=None, witness=None, foot=None) -> dict:
    """One rehearsal run ``n`` of ``stage`` on ``side`` (7.1; R-WALK-VOID's run its own warp and stop:
    :func:`stage_run`): its record (7.2) -- the outcome, the beats, the warp, THE RENDER RATE (``g.rate().as_dict()``
    and every route record's ``fps``), the grants (sample, objects, y), THE BASES and every step row (:func:`step_records`),
    the calibration record (each walked field's basis at the drive's end: seeded or calibrated), the hold tap's holds,
    THE WALKS (every routed step's holds), THE LEVELS, THE DESCENT, THE LADDER, THE SQUEEZE with F5's verdict, DOJEBON,
    THE MONOLOGUE, the pages and the
    transcript, the press, forbidden, observed and input evidence, the longest no-progress stretch, the end state (live;
    the trace's Byte[13] in its summary), end_run's rows and seconds, and the trace through O7's summary cut at the
    stage's end PLACES (the crossings, the interruption's rows, the raced Byte[13], the start reads). An untraced stage
    (F-PASS) starts by :func:`fpass_start` (reseeded first), drives with the live forbidden scan off and records the
    exceptions and Memoria.log lines since the warp instead of a trace. A run's stop records itself -- its frame,
    place, the walk holds sent before it and every direction hold and Confirm requested after it before end_run (there
    must be none). A run the instrument stopped (a HarnessError: outside input, the budget, a refused press, a stop; or
    an unexpected exception) records the class V13 (driver). ``witness`` (default the ctypes one) and ``foot``
    (default :data:`FOOT_WINDOW`) are seams for the fake."""
    from harness import HarnessError
    stage = stage_run(stage, n)
    spred = stage_pred(pred, stage)
    ends = O4R.stage_ends(stage, side)
    start = O4R.stage_start(stage, side)
    members = members_of(spred) if side == "F" else {}
    foot = dict(FOOT_WINDOW if foot is None else foot)
    traced = not stage.get("untraced")
    log, progress, marks = [], {}, {}
    rec_obs = Recorder(g, stage, spred, log)
    trace_name = f"rh_{name}_{n}.jsonl" if traced else None
    t_run = time.time()
    rec = {"stage": name, "n": n, "side": side, "t0": round(t_run - t0, 1), "trace_file": trace_name,
           "traced": traced, "forbid_live": traced,
           "warp": {"field": start, "entrance": stage["entrance"], "sc": stage["sc"]}, "end_fields": list(ends)}
    outcome = {"end": "void", "why": "not driven"}
    mark = g.log_mark()
    holds = HoldTap(g)
    tap = WalkTap(g, holds)
    hs, ps = stage.get("hold_stop"), stage.get("page_stop")
    hstop = (HoldStop(g, field_of(spred, side, hs["place"]), place=hs["place"], n=hs.get("n", 0), holds=hs["holds"],
                      log=log) if hs else None)
    pstop = PageStop(g, where=ps["place"], members=members) if ps else None
    try:
        try:
            rec_obs.arm(g.state.frame)
            if traced:
                O.O7.start_run(g, side, spred, marks)
            else:
                fpass_start(g, side, spred)
            outcome = SD.drive(g, spred, side, log, deadline=time.time() + float(stage["run_s"]), floor_for=floor_for,
                               prior_for=prior_for, progress=progress, end_fields=list(ends), observe=rec_obs,
                               forbid_live=traced, witness=witness if witness is not None else O.C4.input_witness(g))
        except SD.RouteVoid as err:
            outcome = {"end": "void", "why": f"route: {err}", "v": err.v, "cell": err.cell, "by": err.by}
        except HarnessError as err:                           # the instrument's: V13, as the session reads a STOPPED
            outcome = {"end": "void", "why": f"STOPPED: {str(err)[:300]}", "v": "V13", "by": "driver"}
        except Exception as err:                              # noqa: BLE001 -- one run's bug must not cost the others
            outcome = {"end": "void", "why": f"STOPPED (unexpected): {type(err).__name__}: {str(err)[:300]}",
                       "v": "V13", "by": "driver"}
            log.append({"k": "error", "traceback": traceback.format_exc()[-3000:]})
    finally:                                                  # the reverse of the wrapping: each puts back what it found
        if pstop is not None:
            pstop.restore()
        if hstop is not None:
            hstop.restore()
        tap.restore()
        holds.restore()
    t_drive = time.time()
    fps, tick_hz = O5R._rate(g)
    rate = _rate_record(g)
    known = getattr(g, "_axes", None) or {}
    axes = {w["field"]: known.get(w["field"]) for w in tap.walks}
    rows = []
    smark = marks.get("story")
    if smark is not None:
        try:
            rec["collected"] = g.collect_story(g.run_dir / trace_name, smark)
            if (g.run_dir / trace_name).is_file():
                rows = T.read_trace(g.run_dir / trace_name)
        except (HarnessError, T.TraceError) as err:
            rec["trace_error"] = str(err)[:300]
    for k, v in progress.items():
        outcome.setdefault(k, v)
    try:
        trace = O.trace_summary(rows, spred, side=side, start_place=place(start, members), end_fields=list(ends),
                                stock=stock, log=log) if rows else {}
    except T.TraceError as err:
        trace = {"error": str(err)[:300]}
    steps = O5R._steps_rows(g)
    try:
        events = list(g.channel.events())
    except Exception:                                          # noqa: BLE001 -- a record, never the run
        events = []
    step_rows, bases = step_records(log, tap.walks)
    descent = descent_record(tap.walks, log, steps, axes, fps=fps, tick_hz=tick_hz)
    ladder = ladder_record(tap.walks, log, foot, members)
    rec.update(
        outcome={k: outcome.get(k) for k in ("end", "why", "v", "cell", "by", "t")},
        beats=outcome.get("beats"),
        rate=rate,
        route_fps=[[s.get("field"), s.get("n"), s.get("attempt"), (s.get("route") or {}).get("fps")]
                   for s in step_rows if s.get("route")],
        grants=rec_obs.grants,
        bases=bases,
        calibration={str(f): None if b is None else {k: [round(float(v), 4) for v in b[k]] for k in ("v", "h") if k in b}
                     for f, b in axes.items()},
        steps=step_rows,
        walks=walks_record(tap.walks, log, steps, axes),
        levels=levels_record(rec_obs.grants, log, tap.walks, steps, axes),
        descent=descent,
        ladder=ladder,
        squeeze=squeeze_record(tap.walks, log, ladder, steps, axes, foot, members),
        dojebon=dojebon_record(rec_obs, log, spred),
        monologue=monologue_record(log, spred, rec_obs, trace, steps=steps, events=events, members=members),
        holds=[{k: h[k] for k in ("frame", "field", "x", "z", "y", "control", "cached")} for h in holds.holds],
        catch={"samples": rec_obs.samples_read, "caught": rec_obs.catch},
        pages=rec_obs.pages,
        transcript=list(outcome.get("pages") or []),
        evidence={"press": [x for x in log if x.get("k") == "press"],
                  "forbidden": [x for x in log if x.get("k") == "forbidden"],
                  "observed": [x for x in log if x.get("k") == "observed"],
                  "input": [x for x in log if x.get("k") == "input"]},
        no_progress=rec_obs.no_progress,
        end={"end_state": outcome.get("end_state"), "end_run": None},
        trace=trace,
        log_file=f"rh_{name}_{n}_log.json",
    )
    if not traced:
        rec["exceptions"] = O3R._exceptions(g, mark)
        rec["log_lines"] = O3R._new_log_lines(g, mark)
    if hstop is not None:
        f = hstop.fired
        rec["hold_stop"] = (None if f is None else
                            {**{k: v for k, v in f.items() if k != "t"}, "why": WALK_STOP, "place": hstop.place,
                             "n": hstop.n, "walk_holds_before": hstop.count,
                             "holds_before": len(O5R._holds_between(steps, t_run, f["t"])),
                             "holds_after": len(O5R._holds_between(steps, f["t"], t_drive)),
                             "presses_after": len(_confirms_between(steps, f["t"], t_drive))})
    if pstop is not None:
        f = pstop.fired
        rec["page_stop"] = (None if f is None else
                            {**{k: v for k, v in f.items() if k != "t"}, "why": PAGE_STOP, "place": pstop.place,
                             "presses_before": len(_confirms_between(steps, t_run, f["t"])),
                             "holds_after": len(O5R._holds_between(steps, f["t"], t_drive)),
                             "presses_after": len(_confirms_between(steps, f["t"], t_drive))})
    end_log: list = []
    t_end = time.time()
    try:
        O.O7.end_run(g, end_log, recovery=recovery)
        rec["end"]["end_run"] = {"ok": True, "title": g.state.ui_state == "Title", "how": end_log,
                                 "s": round(time.time() - t_end, 1)}
    except HarnessError as err:
        rec["end"]["end_run"] = {"ok": False, "why": str(err)[:300], "how": end_log, "s": round(time.time() - t_end, 1)}
    (g.run_dir / rec["log_file"]).write_text(json.dumps({"outcome": outcome, "log": log + end_log}, indent=1,
                                                        default=str), encoding="utf-8")
    rec["t1"] = round(time.time() - t0, 1)
    return rec


def run(g, field=None, *, stages=None, pred=None, floor_for=None, prior_for=None, stock=None, recovery=None,
        env=None, witness=None, pads=..., engine=None, live_engine=None, foot=None) -> None:
    """The rehearsal launch (tools/play.py's entry; ``field`` from ``--field``). Before anything, each selected stage
    takes its ids from the chain (o4_rehearse.stage_ids: ``member(N)`` resolved, every F-side id checked) and EVERY run's
    predictions are built and checked (:func:`stage_run`, :func:`stage_pred`) -- a refusal raises here, the session
    untouched; the record keeps the resolved stages. The capabilities first (P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG over
    the seven route donors, P-LAUNCH with the engine, P-PAD), the launch's own readings (the settings, P-SETTINGS --
    4.13's, [AnalogControl] among them -- P-OVERRIDE, P-ENGINE), then each selected stage -- its runs on its sides, or
    its smoke -- the record rewritten after every run into ``o7_rehearsal.json``. A run whose end_run cannot reach the
    title stops the launch. Every keyword is a seam for the fake; each defaults to the real thing (``foot``: THE FOOT
    WINDOW, :data:`FOOT_WINDOW`)."""
    stages = STAGES if stages is None else stages
    pred = O.O7.draft() if pred is None else pred
    names = select(stages, field, env)
    stages = {n: O4R.stage_ids(stages[n], pred, name=n) for n in names}     # the chain's ids, or a refusal, first
    for n in names:
        if not stages[n].get("pairs"):
            for k in range(1, int(stages[n]["runs"]) + 1):
                stage_pred(pred, stage_run(stages[n], k))                   # a bad stop refuses before the session
    foot = dict(FOOT_WINDOW if foot is None else foot)
    t0 = time.time()
    record = {"what": "O7 rehearsals (research/o7_design.md 7): R-FULL's traces alone may define predictions; the staged "
                      "runs prove mechanics; R-WALK-VOID proves the stops and the recoveries; F-SMOKE loads the members, "
                      "untraced; F-PASS drives one F run untraced and may only stop the session",
              "draft_sha256": O2R._draft_sha(pred), "stages_run": names,
              "stage_defs": {n: stages[n] for n in names}, "foot": foot,
              "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "capabilities": [], "launch": {}, "stages": {},
              "twins": {}}
    path = g.run_dir / O.REHEARSAL_FILE

    def save() -> None:
        path.write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
    caps = O.O7.capabilities(g, pads=pads, engine=engine, live_engine=live_engine)
    record["capabilities"] = [[ok, what, detail] for ok, what, detail in caps]
    for ok, what, detail in caps:
        g.check(ok, what, detail)
    record["launch"] = O4R.launch_readings(g, pred, engine=engine, live_engine=live_engine)
    save()
    if not all(ok for ok, _w, _d in caps):
        return
    kw = {"floor_for": floor_for, "prior_for": prior_for, "stock": stock, "recovery": recovery, "witness": witness,
          "foot": foot}
    for name in names:
        stage = stages[name]
        if stage.get("pairs"):
            g.shot_prefix = name
            try:
                recs, twins = O4R.smoke(g, name, stage, t0=t0, recovery=recovery)
            finally:
                g.shot_prefix = ""
            record["stages"][name], record["twins"][name] = recs, twins
            save()
            if not all((r.get("end_run") or {}).get("ok") for r in recs):
                record["stopped"] = f"{name}: end_run could not reach the title"
                save()
                return
            continue
        for side in stage_sides(stage):
            for n in range(1, int(stage["runs"]) + 1):
                g.shot_prefix = f"{name}-{n}"
                try:
                    rec = one(g, name, stage, pred, n, side=side, t0=t0, **kw)
                finally:
                    g.shot_prefix = ""
                record["stages"].setdefault(name, []).append(rec)
                save()
                print(f"[o7-rh] {name} run {n} ({side}): {rec['outcome']['end']} -- {rec['outcome']['why']}",
                      flush=True)
                if not (rec["end"]["end_run"] or {}).get("ok"):
                    record["stopped"] = f"{name} run {n}: end_run could not reach the title"
                    save()
                    return
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
