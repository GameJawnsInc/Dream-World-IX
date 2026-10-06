"""O8's REHEARSALS (research/o8_design.md section 7): Steiner up the west tower on STOCK Alexandria Castle -- 164's first
spiral to P1 and THE KNIGHT WAIT, its second spiral through THE PINCH into e2, 165's two stretches, 166's six pages and
FMV004 played out to the arrival in REAL 55 -- stage by stage, the F-side load smoke and one untraced F pass before the
freeze. Each traced stage warps into its start (164 at entrance 342, 165 at 343, or 166 at 344) at SC 1190, drives the
DRAFT (a run's stop laid on a COPY and checked) to its own end fields, and records what the freeze checklist (7.3) is
read from; F-SMOKE warps into each member and its stock twin with NO trace and records what loaded; F-PASS drives one
F run through the whole route with NO trace. Nothing is deployed and nothing is frozen here.

    py tools/play.py studies/story-trace/o8_rehearse.py --label o8-rh --timeout 240              # the default order
    set O8_STAGE=R-FULL & py tools/play.py studies/story-trace/o8_rehearse.py --label o8-rh-full --timeout 240
    set O8_STAGE=R-SPIRAL & py tools/play.py studies/story-trace/o8_rehearse.py --label o8-rh-spiral --timeout 240
    set O8_STAGE=R-SPIRAL165 & py tools/play.py studies/story-trace/o8_rehearse.py --label o8-rh-165 --timeout 240
    set O8_STAGE=R-FMV & py tools/play.py studies/story-trace/o8_rehearse.py --label o8-rh-fmv --timeout 240
    set O8_STAGE=R-VOID & py tools/play.py studies/story-trace/o8_rehearse.py --label o8-rh-void --timeout 240
    set O8_STAGE=F-SMOKE & py tools/play.py studies/story-trace/o8_rehearse.py --label o8-rh-smoke --timeout 240
    set O8_STAGE=F-PASS & py tools/play.py studies/story-trace/o8_rehearse.py --label o8-rh-fpass --timeout 240
    py studies/story-trace/o8_west_tower.py --rehearsal-report <run dir>

WHICH STAGE: the environment variable ``O8_STAGE`` names one; else ``--field`` picks the one stage warping there that is
not by-name-only (``--field 164`` names two -- R-FULL and R-SPIRAL -- and refuses: name it; ``--field 166`` picks R-FMV);
else, in one launch: R-FULL (the go/no-go and the predictions), R-SPIRAL, R-FMV, then R-VOID LAST -- it stops its runs, so
a recovery that fails there ends the launch, and that failure is the finding. R-SPIRAL165, F-SMOKE and F-PASS run only by
name. NO STAGE STARTS BETWEEN 03:45 AND 04:45 LOCAL (the nightly gate's ``-n 6`` whole file starves the game and the
driver alike: the driver review's #10): :func:`run` refuses to start one then, a STOPPED HarnessError naming the window.

EACH TRACED RUN (7.1): O8.start_run -- THE RESEED (164, 165, 31256, 31257 forgotten: each run seeds its fields and
judges its first moves), New Game, ``wait_frames(30)``, the story trace armed, the raw warp -- then segment_drive.drive on
the stage's predictions with its end fields, the live forbidden scan on, the run-wide input witness and THE RECORDER
(O7's: grants with their published objects and y, pages with ``gone_frame``, the no-progress stretch -- wrapping O8's
observe hook, so THE KNIGHT's seat readings and FMV004's clock rows are written into the driver's log as in the session,
plus the knight's published position on every poll in 164, T0 off the RING -- the release comes during 164 #0's walk,
where the driver never polls -- and the movie's stop or poke) watching every poll; O7's WALK TAP and LADDER TAP and HOLD
TAP inside THE SEND TAP (first on, last off: it sees every send after a stop, end_run's too); the trace collected to
``rh_<stage>_<n>.jsonl``; the record written into ``o8_rehearsal.json``; end_run, its rows and its seconds recorded.

THE STOPS (R-VOID; each raised on the driver's own thread, the session's method restored at once, its message FIXED --
never a wrapped call's error text, which S21 could swallow as its own timeout): ``flag_stop`` (a wrapped ``g.wait_for``
raising on the first call whose ``what`` opens with "the flag wait" while the published place is 164 -- after S21's
``g.watch``, so its ``finally`` unwatch runs); ``pinch_stop`` (a wrapped ``g.send`` raising before the first DIRECTION
hold sent while his published x, z AND y lie in THE PINCH WINDOW during 164 #1); ``movie_stop`` (from the recorder's
observe, on the first poll in 166 -- control off, FieldHUD, no window and no choice -- ``after_s`` past the poll that
first saw the 166 e6 t1 ip502 row in the LIVE trace, ip863 not yet written). R-FMV's run 3 carries ``movie_poke``: ONE
Confirm on such a poll ``after_s`` past ip502 -- a ``press`` row, why "movie_poke" -- and nothing else: the skip net
answers the dialog No and the movie plays out. R-FMV and R-VOID RE-RUN a late-edge V5 (70 ip475 before the start, or
166's e0 t0 ip97 row) at most twice, never counted against F3: the run set aside keeps its own files and reads
``counted`` False, its re-run writes ``rh_<stage>_<n>r<k>``.

F-SMOKE (NO trace): o4_rehearse.smoke on member(164) / 164 at 342, member(165) / 165 at 343, member(166) / 166 at 344,
SC 1190, each id read from the chain. F-PASS (NO trace; before the freeze): O8.reseed, New Game, the raw warp into
member(164), the drive to REAL 55 (31258's raw Field(55): never V19) with the live forbidden scan off and no end-row
wait; it may only STOP the session (F13), never shape a frozen value.
"""
from __future__ import annotations

import copy
import datetime as _dt
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
import o7_rehearse as O7R                                              # noqa: E402
import o8_west_tower as O                                              # noqa: E402
import segment_drive as SD                                             # noqa: E402
from ff9mapkit import storytrace as T                                  # noqa: E402
from segment_trace import members_of, place                            # noqa: E402

ENV = "O8_STAGE"
#: The stops' own FIXED words (7.1): the session's V13 reads them back off the outcome; never a wrapped error's text.
FLAG_STOP = "the rehearsal's stop mid-wait (flag_stop)"
PINCH_STOP = "the rehearsal's stop in the pinch (pinch_stop)"
MOVIE_STOP = "the rehearsal's stop mid-movie (movie_stop)"
POKE = "movie_poke"
#: THE PINCH WINDOW (research/o8_design.md 2.5, 7.2): 164 #1's narrowest stretch -- x, z and his PUBLISHED y.
PINCH_WINDOW = dict(O.PINCH_WINDOW)
#: THE NIGHTLY WINDOW (7.1; the driver review's #10): no stage starts between these local times.
NIGHTLY = ((3, 45), (4, 45))
#: A stop's keys (7.1): ``flag_stop`` and ``pinch_stop`` -- their place (and step ``n``); ``movie_stop`` and
#: ``movie_poke`` -- their place and ``after_s`` (past the poll that first saw ip502 in the live trace).
STOP_KEYS = {"flag_stop": ("place", "n"), "pinch_stop": ("place", "n"), "movie_stop": ("place", "after_s"),
             POKE: ("place", "after_s")}
#: The stops laid on a step of the run's COPY of the table (the freeze refuses them there); the movie's two have no
#: step (166 has no cell): they reach the recorder through the stage alone.
STEP_STOPS = ("flag_stop", "pinch_stop")
#: The stages (research/o8_design.md 7.1): the warp, the end fields, the runs, a run budget and a cost estimate in
#: seconds a run (F8 replaces every number from what is measured). ``by_name``: never picked by ``--field``;
#: ``optional``: only by name; ``last``: after every other stage of a launch; ``sides``: the sides a stage runs
#: (default S); ``untraced``: no storytrace verb (F-PASS); ``each``: a stage whose runs differ -- run k is the stage with
#: ``each[k-1]`` laid over it; ``reruns``: how many times a late-edge V5 is re-run (R-FMV, R-VOID). A member is named
#: ``member(<donor>)``, never by its id: o4_rehearse.stage_ids reads it from the chain.
STAGES = {
    "R-FULL": {"field": 164, "entrance": 342, "sc": 1190, "end": [55], "runs": 2, "run_s": 600, "cost_s": 150,
               "settles": "F1-F8, F10, F11, F14 (the go/no-go and the predictions): both grants (sample, objects, "
                          "published y), both first moves, every step (route, holds, slides, stalls, losses with y, "
                          "landings, flips), THE KNIGHT (T0, ip230's frame, the wait's seconds, the seat rows), THE "
                          "PINCH, the dead-level crossings, 166's pages, FMV004's span and rate, the 166 -> 55 crossing, "
                          "the cut, the 23 keys and 6 masked rows, the pattern, the end state (live, and Int16[2] / "
                          "Byte[8] from the trace), the run time, the longest no-progress stretch, the render rate -- the "
                          "ONLY stage whose traces define predictions"},
    "R-SPIRAL": {"field": 164, "entrance": 342, "sc": 1190, "end": [165], "runs": 2, "run_s": 300, "cost_s": 60,
                 "settles": "F2, F5: 164's grant (y ~4780), the 'left' first move, step 0's at_y, THE KNIGHT (T0, ip230 "
                            "at ~T0 + 140, the wait, the seat), step 1 through THE PINCH WINDOW -- every hold starting or "
                            "ending in it, every ladder rung after one, each stall classified -- e2's loss y (~13008), "
                            "the landing 165"},
    "R-SPIRAL165": {"field": 165, "entrance": 343, "sc": 1190, "end": [166], "runs": 2, "run_s": 300, "cost_s": 40,
                    "by_name": True, "optional": True,
                    "settles": "F4: 165's grant (y ~10280), 'up+left' (<= 4 deg), step 0's at_y, e3's dead-level "
                               "crossings with no loss, e2's loss y (~15169), the landing 166"},
    "R-FMV": {"each": [{}, {}, {POKE: {"place": 166, "after_s": 10.0}}], "field": 166, "entrance": 344, "sc": 1190,
              "end": [55], "runs": 3, "run_s": 300, "cost_s": 90, "reruns": 2,
              "settles": "F3: pages 307-313 under rule 7, no press after 313 until ip863, no skip dialog, the movie span "
                         "ip502 -> ip863 (frames, the clocked rate, seconds), 55's cut row, the live end-state reads; RUN "
                         "3 with movie_poke: ONE Confirm mid-movie -- the skip dialog as published, the net's No, the "
                         "movie RESUMED and played out (ip863, then 55: REACHED); a late-edge V5 re-run, never counted"},
    "R-VOID": {"each": [{"field": 164, "entrance": 342, "end": [165], "flag_stop": {"place": 164}},
                        {"field": 164, "entrance": 342, "end": [165], "pinch_stop": {"place": 164, "n": 1}},
                        {"field": 166, "entrance": 344, "end": [55], "movie_stop": {"place": 166, "after_s": 15.0}}],
               "sc": 1190, "runs": 3, "run_s": 300, "cost_s": 60, "by_name": True, "last": True, "reruns": 2,
               "settles": "F9: each run V13 by the driver with its FIXED message, no direction hold and no press after "
                          "the raise, the sends after it exactly S21's unwatch (run 1), collect_story's storytrace 0 and "
                          "end_run's recovery warp and ladder; run 3's stop frame after the ip502 row's"},
    "F-SMOKE": {"pairs": [["member(164)", 164, 342, 1190], ["member(165)", 165, 343, 1190],
                          ["member(166)", 166, 344, 1190]], "runs": 1,
                "smoke_s": 8.0, "warp_s": 60.0, "cost_s": 180, "by_name": True, "optional": True,
                "settles": "F12: each member loads at its entrance and SC (its field, FieldHUD), its published object "
                           "sids EQUAL to its stock twin's measured set after smoke_s; 0 exceptions; end_run ok"},
    "F-PASS": {"field": {"S": 164, "F": "member(164)"}, "entrance": 342, "sc": 1190, "end": [55], "sides": ["F"],
               "untraced": True, "runs": 1, "run_s": 600, "cost_s": 150, "by_name": True, "optional": True,
               "settles": "F13 (may only STOP the session): one F run through the whole route on the DRAFT, untraced and "
                          "reseeded first -- reached REAL 55 through 31258's raw Field(55), every beat, no V-class, no "
                          "exception; its record is never evidence for any key and never shapes a frozen value"},
}


def select(stages: dict, field=None, env=None) -> list:
    """The stage names a launch runs: ``O8_STAGE`` (one, by name), else the one stage warping into ``field`` that is not
    ``by_name``, else every non-optional stage in the table's order with the ``last`` ones after the rest -- R-VOID ends
    the launch."""
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


def in_nightly(now: _dt.datetime) -> bool:
    """Whether ``now`` (local) lies in THE NIGHTLY WINDOW, 03:45 to 04:45 (both ends included)."""
    t = (now.hour, now.minute)
    return NIGHTLY[0] <= t <= NIGHTLY[1]


def refuse_nightly(now: _dt.datetime, name: str) -> None:
    """A STOPPED HarnessError naming the window when ``now`` lies in it (7.1): no stage starts there."""
    from harness import HarnessError
    if in_nightly(now):
        raise HarnessError(f"STOPPED: {name} would start at {now:%H:%M} local, inside THE NIGHTLY WINDOW 03:45-04:45 "
                           f"(the nightly gate's -n 6 starves the game and the driver): start it after 04:45")


def stage_run(stage: dict, n: int) -> dict:
    """Run ``n`` (1-based) of ``stage``: the stage itself, or -- a stage with ``each`` -- the stage with ``each[n-1]`` laid
    over a copy and ``each`` dropped (o7_rehearse.stage_run's rule)."""
    return O7R.stage_run(stage, n)


#: The step row keys O8's record keeps beyond O7's (o7_rehearse.STEP_KEYS): the walk's level (S20's ``at_y``), THE
#: KNIGHT WAIT (S21's ``wait_flag``) and the pinch's fallback (S23's ``unstick``).
STEP_KEYS8 = ("at_y", "wait_flag", "unstick")


def _check_stop(key: str, stop) -> dict:
    """A stop's own dict checked (:data:`STOP_KEYS`): ValueError, naming the stop, for anything else."""
    if not isinstance(stop, dict) or not SD._is_int(stop.get("place")):
        raise ValueError(f"{key}: a dict with the place, e.g. {{'place': 164}}, not {stop!r}")
    unknown = sorted(set(stop) - set(STOP_KEYS[key]))
    if unknown:
        raise ValueError(f"{key} {stop}: no key {unknown} (a {key} takes {list(STOP_KEYS[key])})")
    if "after_s" in STOP_KEYS[key] and not (isinstance(stop.get("after_s"), (int, float))
                                            and not isinstance(stop.get("after_s"), bool) and stop["after_s"] >= 0):
        raise ValueError(f"{key} {stop}: after_s is a number of seconds >= 0")
    return stop


def stage_pred(pred: dict, stage: dict) -> dict:
    """The draft with the run's own start on each side, entrance and scenario; a run's ``flag_stop`` / ``pinch_stop``
    laid on its step of the COPY (o8_west_tower.REHEARSAL_OVERLAYS8: the keys the freeze refuses) -- the movie's two
    (``movie_stop``, ``movie_poke``) checked and left on the stage (166 has no cell); a run stops one way; for an
    untraced stage no end-row wait. Then checked as the driver will read it -- segment_drive.naming_of, witness_of and
    step_of on every table step -- so a bad stop refuses before anything is driven. ``stage`` is ONE run's
    (:func:`stage_run`). The predictions given are never changed."""
    if stage.get("each") is not None:
        raise ValueError("a stage with each is laid run by run: stage_pred(pred, stage_run(stage, n))")
    p = copy.deepcopy(pred)
    p.update(start={"S": O4R.stage_start(stage, "S"), "F": O4R.stage_start(stage, "F")}, entrance=stage["entrance"],
             scenario=stage["sc"])
    over = {k: stage[k] for k in sorted(O.REHEARSAL_OVERLAYS8) if stage.get(k) not in (None, False)}
    if len(over) > 1:
        raise ValueError(f"a run stops one way, not {sorted(over)}")
    for k, v in over.items():
        if k not in STOP_KEYS:
            raise ValueError(f"{k}: not one of this stage's stops {sorted(STOP_KEYS)}")
        _check_stop(k, v)
        if k in STEP_STOPS:
            n = v.get("n", 0 if k == "flag_stop" else 1)
            cells = [c for c in p.get("table") or () if c.get("donor") == v["place"]]
            if len(cells) != 1 or not SD._is_int(n) or not 0 <= n < len(cells[0]["steps"]):
                raise ValueError(f"{k} {v}: {len(cells)} table cell(s) of place {v['place']} -- not one cell with a "
                                 f"step #{n}")
            cells[0]["steps"][n][k] = True
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
    return O7R.field_of(pred, side, where)


_r = O7R._r


def in_pinch(win: dict, p) -> bool:
    """Whether a sample ``p`` -- ``{"x", "z", "y"}`` or ``[x, z, y]`` -- stands in THE PINCH WINDOW ``win`` (its x, z and
    published-y bands, both ends included)."""
    if p is None:
        return False
    x, z, y = (p.get("x"), p.get("z"), p.get("y")) if isinstance(p, dict) else (p[0], p[1], p[2] if len(p) > 2 else None)
    if x is None or z is None or y is None:
        return False
    return (win["x"][0] <= x <= win["x"][1] and win["z"][0] <= z <= win["z"][1] and win["y"][0] <= y <= win["y"][1])


# ======================================================================== the run's own instruments
class Recorder(O7R.Recorder):
    """O7's recorder (grants off the ring with their objects and y, pages with ``gone_frame``, the no-progress stretch,
    the static watch -- none registered in O8) with O8's observe hook (o8_west_tower.o8_observe: THE KNIGHT's seat and
    start1 rows, FMV004's clock and skip_seen rows, written into the driver's ``log``), the knight's published position
    on every poll in his place (``knight_polls``), T0 off the RING (:meth:`t0_scan`: the driver polls only between
    steps, and the release comes DURING step 0's walk), the first poll that saw 166's ip502 row in the LIVE trace (read
    at most once a second while in 166), and the movie's ``movie_stop`` / ``movie_poke`` from the stage."""

    def __init__(self, g, stage: dict, pred: dict, log: list):
        super().__init__(g, stage, pred, log)
        self.log = log
        self.hook = O.o8_observe(g, pred, log)
        sw = pred.get("seat_watch") or {}
        self.knight = (sw.get("donor"), sw.get("sid"))
        self.release = sw.get("release") or {"y_ge": 8400}
        self.knight_polls: list = []
        self.t0 = None
        self._kscanned = None                           # the ring's last frame t0_scan read
        self._kgap = None                               # the last eviction gap t0_scan met: [last read, oldest held]
        self._kbelow = False                            # a sample in his place under the release read since that gap
        mv = pred.get("movie") or {}
        self.movie_place = mv.get("donor")
        self.ip502 = tuple((mv.get("from") or [0, 0, 0, 0])[1:])
        self.ip863 = tuple((mv.get("to") or [0, 0, 0, 0])[1:])
        self.seen502 = None                             # {"t", "frame"} of the poll that first saw ip502 live
        self.seen863 = False
        self._read_t = 0.0
        self.stop = stage.get("movie_stop")
        self.poke = stage.get(POKE)
        self.stop_fired = None
        self.poke_fired = None

    def arm(self, frame: int) -> None:
        """O7's grant scan from ``frame`` on, and :meth:`t0_scan`'s too: the run's start, before its New Game."""
        super().arm(frame)
        self._kscanned = int(frame) - 1
        self._kgap, self._kbelow = None, False

    def t0_scan(self, st) -> None:
        """T0 (7.2, F2) off the RING at every poll until found: each sample the harness read since the last scan,
        once, oldest first -- the first in the knight's place whose published player y passes his release
        (``seat_watch.release``: y >= 8400 on 164's loop 2) is T0, ``{"frame", "y", "field"}``.

        THE RING EVICTS (research/o8_design.md 11.4, the review's #1): it holds the last STATE_RING distinct samples
        (~10 s at 60 fps), and no poll -- so no scan -- runs inside a step's executor (164 #0's walk and THE KNIGHT
        WAIT). A scan whose ring no longer holds the last frame read (its oldest sample is newer) has LOST the samples
        between, the crossing perhaps among them: from then on the first passing sample is T0 only once a sample in his
        place UNDER the release has been read after that gap (the crossing then on record); else T0 is UNMEASURED,
        ``{"frame": None, "evicted": True, "after": the last frame read before the gap, "held_from": the oldest frame
        held after it, "first": the first passing sample read}`` -- never a late frame read as his release. (A climb
        that crossed, fell back under the release and crossed again inside the gap would read the second crossing: the
        walk to P1 climbs.)"""
        if self.t0 is not None or self.knight[0] is None:
            return
        since = st.frame - 1 if self._kscanned is None else self._kscanned
        try:
            held = self.g.states_since(-1)                         # the whole ring, oldest first
        except Exception:                                      # noqa: BLE001 -- a record, never the run
            return
        oldest = int(held[0].get("frame", -1)) if held else None
        if oldest is not None and oldest > since:              # nothing at or before `since` left: an eviction gap
            self._kgap, self._kbelow = [since, oldest], False
        for raw in held:
            f = int(raw.get("frame", -1))
            if f <= since:
                continue
            self._kscanned = f
            y = (raw.get("player") or {}).get("y")
            fld = int((raw.get("field") or {}).get("id", -1))
            if y is None or place(fld, self.members) != self.knight[0]:
                continue
            if not O.gate_holds(self.release, y):
                self._kbelow = True
                continue
            first = {"frame": f, "y": _r(y), "field": fld}
            if self._kgap is not None and not self._kbelow:
                self.t0 = {"frame": None, "evicted": True, "after": self._kgap[0], "held_from": self._kgap[1],
                           "first": first}
            else:
                self.t0 = first
            return

    def _live(self, st) -> None:
        """At most once a second in the movie's place: the live trace's rows -- the first ip502 row seen, ip863's."""
        now = time.time()
        if now - self._read_t < 1.0 or self.seen863:
            return
        self._read_t = now
        try:
            rows = self.g.story_rows()
        except Exception:                                      # noqa: BLE001 -- a record, never the run
            return
        mem = self.members
        for x in rows:
            if x.k != "w" or place(x.fld, mem) != self.movie_place:
                continue
            if (x.sid, x.tag, x.ip) == self.ip502 and self.seen502 is None:
                self.seen502 = {"t": now, "frame": st.frame, "row_f": x.f}
            if (x.sid, x.tag, x.ip) == self.ip863:
                self.seen863 = True

    def __call__(self, st, ctx: dict) -> None:
        from harness import HarnessError
        super().__call__(st, ctx)
        self.hook(st, ctx)
        here = ctx.get("donor")
        kd, ks = self.knight
        self.t0_scan(st)
        if here == kd:
            b = next((o for o in st.objects or () if o.get("sid") == ks), None)
            if b is not None and b.get("x") is not None:
                self.knight_polls.append([st.frame, _r(b["x"]), _r(b["z"])])
        if here != self.movie_place:
            return
        self._live(st)
        quiet = (not st.control and st.ui_state == "FieldHUD" and not list(st.texts or ()) and not st.choice)
        if self.seen502 is None or self.seen863 or not quiet:
            return
        waited = time.time() - self.seen502["t"]
        if self.poke and self.poke_fired is None and waited >= float(self.poke["after_s"]):
            pre = {"frame": st.frame, "control": False, "x": None, "z": None}
            self.g.press("confirm")
            self.poke_fired = {"t": time.time(), "frame": st.frame, "after_s": round(waited, 1)}
            self.log.append({"k": "press", "why": POKE, "field": ctx.get("field"), "donor": here, "visit": None,
                             "sc": ctx.get("sc"), "pre": pre, "post": None, "near": [], "button": "confirm"})
        if self.stop and self.stop_fired is None and waited >= float(self.stop["after_s"]):
            self.stop_fired = {"t": time.time(), "frame": st.frame, "field": ctx.get("field"), "x": _r(st.player_x),
                               "z": _r(st.player_z), "y": _r(st.player_y), "after_s": round(waited, 1),
                               "f502": self.seen502["row_f"]}
            raise HarnessError(MOVIE_STOP)


class SendTap:
    """Every request sent after a stop fired (F9: exactly S21's ``unwatch``, collect_story's ``storytrace 0`` and
    end_run's recovery warp and ladder): ``g.send`` wrapped on the instance once :meth:`arm` is called."""

    def __init__(self, g):
        self.g, self.sent, self.on = g, [], False
        self._had = "send" in vars(g)
        self._orig = vars(g).get("send")
        real = g.send

        def send(*steps, **kw):
            if self.on:
                self.sent.append(" ".join(str(s) for s in steps)[:80])
            return real(*steps, **kw)
        g.send = send

    def arm(self) -> None:
        self.on = True

    def restore(self) -> None:
        if self._had:
            self.g.send = self._orig
        else:
            vars(self.g).pop("send", None)


class FlagStop:
    """R-VOID run 1's STOP (7.1, F9): ``g.wait_for`` wrapped on the instance -- the first call whose ``what`` opens with
    "the flag wait" while the published field's place is ``place`` raises :data:`FLAG_STOP` (after S21's ``watch``: its
    ``finally`` unwatch runs), the session's own wait_for restored at once. Never a timer."""

    def __init__(self, g, *, place_: int, members: dict, on_fire=None):
        from harness import HarnessError
        self.g, self.place, self.members, self.fired, self.on_fire = g, int(place_), dict(members or {}), None, on_fire
        self._had = "wait_for" in vars(g)
        self._orig = vars(g).get("wait_for")
        real = g.wait_for

        def wait_for(*a, **kw):
            what = str(kw.get("what") or (a[2] if len(a) > 2 else ""))
            if self.fired is None and what.startswith("the flag wait"):
                st = g.state
                if place(st.field_id, self.members) == self.place:
                    self.fired = {"t": time.time(), "frame": st.frame, "field": st.field_id, "x": _r(st.player_x),
                                  "z": _r(st.player_z), "y": _r(st.player_y), "what": what}
                    self.restore()
                    if self.on_fire is not None:
                        self.on_fire()
                    raise HarnessError(FLAG_STOP)
            return real(*a, **kw)
        g.wait_for = wait_for

    def restore(self) -> None:
        if self._had:
            self.g.wait_for = self._orig
        else:
            vars(self.g).pop("wait_for", None)


class PinchStop:
    """R-VOID run 2's STOP (7.1, F9): ``g.send`` wrapped on the instance -- the first DIRECTION hold sent while his
    published x, z AND y lie in THE PINCH WINDOW during ``place``'s step ``n`` (the log holds ``n`` done step rows of the
    place) raises :data:`PINCH_STOP` BEFORE it is sent, the session's own send restored at once. Loop 1 passes under
    the same XZ ~5000 lower: never fired there."""

    def __init__(self, g, *, place_: int, n: int, members: dict, log: list, win: dict, on_fire=None):
        from harness import HarnessError
        self.g, self.place, self.n, self.members, self.log, self.win = g, int(place_), int(n), dict(members or {}), \
            log, dict(win)
        self.fired, self.on_fire = None, on_fire
        self._had = "send" in vars(g)
        self._orig = vars(g).get("send")
        real = g.send

        def send(*steps, **kw):
            if self.fired is None and any(O6R._direction_hold(s) for s in steps):
                st = g.state
                if (place(st.field_id, self.members) == self.place and self.in_step()
                        and in_pinch(self.win, {"x": st.player_x, "z": st.player_z, "y": st.player_y})):
                    self.fired = {"t": time.time(), "frame": st.frame, "field": st.field_id, "x": _r(st.player_x),
                                  "z": _r(st.player_z), "y": _r(st.player_y), "control": bool(st.control),
                                  "steps": [str(s) for s in steps]}
                    self.restore()
                    if self.on_fire is not None:
                        self.on_fire()
                    raise HarnessError(PINCH_STOP)
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


# ======================================================================== the records (pure)
def step_records8(log: list, walks: list) -> tuple:
    """o7_rehearse.step_records (every step row trimmed, its route record's keys and rate; THE BASES) with O8's step
    keys (:data:`STEP_KEYS8`: ``at_y``, ``wait_flag``, ``unstick``) kept on each row that carries them."""
    steps, bases = O7R.step_records(log, walks)
    rows = [r for r in log or () if r.get("k") == "step"]
    for s, r in zip(steps, rows):
        s.update({k: r[k] for k in STEP_KEYS8 if k in r})
    return steps, bases


def knight_record(rec_obs, log: list, pred: dict, trace: dict) -> dict:
    """THE KNIGHT (7.2, F2), pure but for the recorder: T0 (the first poll in his place at published y inside his
    release), ip230's trace frame and line (the summary's), THE EXEMPT SPAN, the wait (step 0's ``wait_flag``: frame0,
    read frame, wall and game seconds, the samples that published the bit, its last value), the ``seat`` and
    ``start1`` rows, his published position on every poll in his place, any ``observe_error`` row. ``{}`` when the run
    never reached his place."""
    sw = pred.get("seat_watch") or {}
    d = sw.get("donor")
    rows = [r for r in log or () if r.get("k") == "step" and r.get("donor") == d]
    if not rows and not getattr(rec_obs, "knight_polls", None):
        return {}
    s0 = [r for r in rows if r.get("n") == 0]
    kr = O.knight_rows(log, pred)
    return {"t0": getattr(rec_obs, "t0", None), "ip230": (trace or {}).get("knight", {}).get("ip230"),
            "span": list(O.exempt_span(log, d)), "wait": (s0[-1].get("wait_flag") if s0 else None),
            "seat": kr["seat"], "start1": kr["start1"], "polls": list(getattr(rec_obs, "knight_polls", []) or []),
            "errors": kr["errors"]}


def _stall_class(h: dict, rungs: list) -> str:
    """A stall in THE PINCH WINDOW classified (2.5, 7.2; the driver review's #8): ``blocker-sealed`` when a ladder rung
    after it placed a blocker and the call ended boxed or frozen (a placed disc closed the corridor, the replan found no
    route); ``slid`` when the hold deflected (its ``slide``); else ``rejected`` (ticks ran, he moved nothing)."""
    for x in rungs:
        if "blocker" in (x.get("rungs") or ()) and ({"boxed", "frozen"} & set(x.get("rungs") or ())
                                                    or x.get("outcome") in ("boxed", None)):
            return "blocker-sealed"
    return "slid" if h.get("slide") else "rejected"


def pinch_record(walks: list, log: list, ladder: list, steps: list, axes: dict, win: dict, members: dict) -> dict:
    """THE PINCH (7.2, F5), pure: in THE PINCH WINDOW's place, every hold of every walk -- its ack frame, start, end
    (with his published y at both), pressed direction, travel, slide and stall -- ``pinch`` when it STARTED or ENDED in
    the window (x, z AND y), such a hold with its samples (``[frame, x, y, z]``: --rehearsal-report measures the
    narrowest wall gap on them, level-aware); every ladder rung there, those after a hold wholly elsewhere apart
    (recorded, never judged); each STALL in the window classified (:func:`_stall_class`); and F5's verdict -- GO when the
    place's step 1 is done and no rung followed a pinch hold, else NO-GO naming why. ``{}`` when the run never walked
    there."""
    fp = win["place"]
    mine = [w for w in walks if place(w["field"], members) == fp]
    if not mine:
        return {}
    holds = []
    for w in mine:
        basis = axes.get(w["field"])
        rows = O5R.hold_rows(w, list(steps), basis)
        ys = O7R._hold_ys(w, rows)
        prev = w.get("frame0")
        for h, (y0, y1) in zip(rows, ys):
            pressed = O5R.pressed_dir(basis, [str(s).split() for s in h.get("steps") or () if str(s).startswith("hold ")])
            a = {"x": (h["from"] or [None, None])[0], "z": (h["from"] or [None, None])[1], "y": y0}
            b = {"x": (h["to"] or [None, None])[0], "z": (h["to"] or [None, None])[1], "y": y1}
            f = in_pinch(win, a) or in_pinch(win, b)
            hold = {"frame": h["ack_frame"], "field": w["field"], "from": h["from"], "to": h["to"], "y0": y0, "y1": y1,
                    "pressed": None if pressed is None else [round(pressed[0], 3), round(pressed[1], 3)],
                    "moved": h["moved"], "slide": h["slide"], "stall": h["stall"], "pinch": f}
            if f:
                hold["samples"] = [[x["frame"], x.get("x"), x.get("y"), x.get("z")] for x in w.get("samples") or ()
                                   if x.get("x") is not None and prev is not None and prev <= x["frame"] <= h["ack_frame"]]
            holds.append(hold)
            prev = h["ack_frame"]
    rungs = [x for x in ladder if x.get("place") == fp]
    bad = [x for x in rungs if x.get("pinch")]
    stalls = []
    for h in holds:
        if h["pinch"] and h["stall"]:
            after = [x for x in rungs if x.get("frame") is not None and x["frame"] >= h["frame"]][:1]
            stalls.append({"frame": h["frame"], "x": (h["from"] or [None])[0], "z": (h["from"] or [None, None])[1],
                           "class": _stall_class(h, after), "why": f"moved {h['moved']}, slide {h['slide']}"})
    done = any(r.get("outcome") == "done" for r in log or () if r.get("k") == "step" and r.get("donor") == fp
               and r.get("n") == 1)
    if not done:
        f5 = f"NO-GO: {fp} #1 is not done in this run"
    elif bad:
        f5 = (f"NO-GO: a ladder rung ({'/'.join(bad[0]['rungs']) or bad[0].get('outcome')}) at frame {bad[0]['frame']} "
              f"followed a hold that started or ended in THE PINCH WINDOW")
    else:
        f5 = "GO"
    return {"place": fp, "window": {k: list(win[k]) for k in ("x", "z", "y")}, "holds": holds,
            "pinch_holds": [h for h in holds if h["pinch"]], "rungs": rungs,
            "elsewhere": [x for x in rungs if not x.get("pinch")], "stalls": stalls, "narrowest": None, "f5": f5}


def pinch_ladder(walks: list, log: list, win: dict, members: dict) -> list:
    """THE LADDER (7.2), pure: o7_rehearse.ladder_record's rungs, each flagged ``pinch`` (not ``foot``) when it lies in
    THE PINCH WINDOW's place and the stalled hold it followed STARTED (``after_hold``) or ENDED (the rung's own sample)
    in the window -- x, z AND y."""
    out = []
    for x in O7R.ladder_record(walks, log, {"place": win["place"], "x": win["x"], "z": win["z"]}, members):
        here = x.get("place") == win["place"]
        x = {k: v for k, v in x.items() if k != "foot"}
        x["pinch"] = bool(here and (in_pinch(win, x.get("after_hold")) or in_pinch(win, x)))
        out.append(x)
    return out


def dead_level_record(walks: list, pred: dict, members: dict) -> list:
    """THE DEAD-LEVEL CROSSINGS (7.2, F2 / F4), pure: each entry of a walk's samples into a registered exit's polygon
    (in its place's field) at a published height where the exit's GATE fails -- the door cannot fire there: no loss.
    ``[{"key", "frame", "field", "x", "z", "y", "gate"}]``, one per entry."""
    from ff9mapkit.content import doorface
    regs = [(k, r) for k, r in sorted((pred.get("regions") or {}).items()) if r.get("role") == "exit" and r.get("gate")]
    out = []
    for w in walks:
        p = place(w["field"], members)
        inside = {}
        for s in w.get("samples") or ():
            if s.get("x") is None or s.get("y") is None:
                continue
            for k, r in regs:
                if str(k).split(".")[0] != str(p):
                    continue
                now = doorface.region_contains(float(s["x"]), float(s["z"]), r["points"])
                if now and not inside.get(k) and not O.gate_holds(r["gate"], s["y"]):
                    out.append({"key": k, "frame": s["frame"], "field": w["field"], "x": _r(s["x"]), "z": _r(s["z"]),
                                "y": _r(s["y"]), "gate": O.gate_text(r["gate"])})
                inside[k] = now
    return out


def movie_record(rec_obs, log: list, pred: dict, rows: list, members: dict, outcome: dict) -> dict:
    """FMV004 (7.2, F3), pure but for the recorder: the 313 press (the last page press before ip502), the span over the
    run's own rows and log (o8_west_tower.movie_span: frames, the clocked rate, seconds, presses, choices and skip
    dialogs in it), ui and control during it (its clock rows), the poke (its frame, the dialog seen, the net's choice
    rows, the frame the movie resumed at), 166's Byte[13] old (its ip119 or ip97 row) and whether the run was a
    LATE-EDGE V5 (70 ip475 among the pre rows, or a 166 e0 t0 ip97 row: re-run, never counted). ``{}`` when the run
    never reached the movie's place."""
    mv = pred.get("movie") or {}
    d = mv.get("donor")
    if not any(place(x.fld, members) == d for x in rows or () if x.k in ("w", "r")) and not any(
            x.get("donor") == d for x in log or () if x.get("k") in ("visit", "press")):
        return {}
    span = O.movie_span({"rows": rows, "log": log}, pred, members)
    presses = [x for x in log or () if x.get("k") == "press" and x.get("donor") == d and x.get("why") != POKE]
    p313 = next((x for x in reversed(presses) if span["f502"] is None or (x.get("pre") or {}).get("frame", 0)
                 <= span["f502"]), None)
    b13 = next((x for x in rows or () if x.k == "w" and place(x.fld, members) == d and (x.sid, x.tag) == (0, 0)
                and x.target == "Global.Byte[13]"), None)
    pre70 = any(x.k == "w" and x.fld == O.NEWGAME_FIELD and (x.sid, x.tag, x.ip) == (0, 0, 475) for x in rows or ())
    late = (outcome or {}).get("v") == "V5" and (pre70 or (b13 is not None and b13.ip == 97))
    poke = None
    if getattr(rec_obs, "poke_fired", None):
        pf = rec_obs.poke_fired
        dialogs = [x for x in log or () if x.get("k") == "skip_seen" and x.get("frame", 0) >= pf["frame"]]
        chs = [x for x in log or () if x.get("k") == "choice" and x.get("frame", 0) >= pf["frame"]]
        clocks = [x for x in log or () if x.get("k") == "clock" and x.get("frame", 0) > pf["frame"]]
        resumed = next((x["frame"] for x in clocks if not x.get("control") and x.get("windows") == 0
                        and (not chs or x["frame"] > chs[0].get("frame", 0))), None)
        poke = {"frame": pf["frame"], "after_s": pf["after_s"], "dialog": dialogs[0] if dialogs else None,
                "choices": [{k: c.get(k) for k in ("frame", "options", "selected", "index", "rule")} for c in chs],
                "resumed": resumed, "second": len(dialogs) > 1}
    return {"p313": None if p313 is None else (p313.get("pre") or {}).get("frame"),
            "span": {k: span.get(k) for k in ("f502", "f863", "fps", "s", "skipped")} | {"clocks": len(span["clocks"])},
            "ui": sorted({x.get("ui") for x in span["clocks"]}), "presses": len(span["presses"]),
            "choices": len(span["choices"]), "skips": len(span["skips"]),
            "byte13_old": None if b13 is None else {"ip": b13.ip, "old": b13.old, "new": b13.new},
            "late_v5": bool(late), "poke": poke}


def crossing_record(rows: list, pred: dict, members: dict) -> dict:
    """THE CROSSING (7.2): 166 e6 t1 ip863's frame, REAL 55's ip22 frame and every row between them. ``{}`` without
    ip863."""
    seam = O.seam_spec(pred)
    ex = tuple((seam.get("exit") or [0, 0, 0, 0])[1:])
    i = next((j for j, x in enumerate(rows or ()) if x.k == "w" and place(x.fld, members) == seam.get("donor")
              and (x.sid, x.tag, x.ip) == ex), None)
    if i is None:
        return {}
    k = next((j for j in range(i + 1, len(rows)) if rows[j].k in ("w", "r") and rows[j].fld == seam.get("to")), None)
    between = [f"{x.k} fld {x.fld} f{x.f}" for x in rows[i + 1:k if k is not None else len(rows)]]
    return {"ip863": rows[i].f, "ip22": None if k is None else rows[k].f, "between": between}


# ======================================================================== a run, an untraced start, a launch
def fpass_start(g, side: str, spred: dict) -> None:
    """F-PASS's UNTRACED start (7.1): O8.reseed FIRST (164, 165, 31256, 31257 forgotten), then O5's -- New Game,
    ``wait_frames(30)``, the raw warp into the side's start, the wait for the field -- with no ``storytrace`` verb."""
    O.O8.reseed(g, spred)
    O5R.fpass_start(g, side, spred)


def one(g, name: str, stage: dict, pred: dict, n: int, *, side: str = "S", t0: float, floor_for=None,
        prior_for=None, stock=None, recovery=None, witness=None, pinch=None, attempt: int = 0) -> dict:
    """One rehearsal run ``n`` of ``stage`` on ``side`` (7.1): its record (7.2) -- O7's (the outcome, the beats, the warp,
    the render rate, the grants, THE BASES and every step row, the calibration, the hold tap's holds, THE WALKS, THE
    LEVELS, THE LADDER, the pages and the transcript, the evidence, the longest no-progress stretch, the end state,
    end_run's rows and seconds) with O8's: THE KNIGHT, THE PINCH (every stall classified, F5's verdict), the dead-level
    crossings, the movie, the crossing into 55, the trace through o8_west_tower.trace_summary8 cut at the stage's end
    PLACES, and the run's stop with the sends after it. An untraced stage (F-PASS) starts by :func:`fpass_start` and
    records the exceptions and Memoria.log lines since the warp instead of a trace. ``attempt`` (a late-edge V5's
    re-run: 1, 2) names the run's own files apart (``rh_<stage>_<n>r<attempt>``): a re-run never overwrites the run it
    re-runs. ``witness`` and ``pinch`` (default :data:`PINCH_WINDOW`) are seams for the fake."""
    from harness import HarnessError
    stage = stage_run(stage, n)
    spred = stage_pred(pred, stage)
    ends = O4R.stage_ends(stage, side)
    start = O4R.stage_start(stage, side)
    members = members_of(spred) if side == "F" else {}
    win = dict(PINCH_WINDOW if pinch is None else pinch)
    traced = not stage.get("untraced")
    log, progress, marks = [], {}, {}
    rec_obs = Recorder(g, stage, spred, log)
    stem = f"rh_{name}_{n}" + (f"r{int(attempt)}" if attempt else "")
    trace_name = f"{stem}.jsonl" if traced else None
    t_run = time.time()
    rec = {"stage": name, "n": n, "side": side, "t0": round(t_run - t0, 1), "trace_file": trace_name,
           "traced": traced, "forbid_live": traced,
           "warp": {"field": start, "entrance": stage["entrance"], "sc": stage["sc"]}, "end_fields": list(ends)}
    outcome = {"end": "void", "why": "not driven"}
    mark = g.log_mark()
    sends = SendTap(g)                                        # first on, last off: every wrapper below is inside it
    holds = O7R.HoldTap(g)
    tap = O7R.WalkTap(g, holds)
    fs, ps = stage.get("flag_stop"), stage.get("pinch_stop")
    fstop = FlagStop(g, place_=fs["place"], members=members, on_fire=sends.arm) if fs else None
    pstop = (PinchStop(g, place_=ps["place"], n=ps.get("n", 1), members=members, log=log, win=win, on_fire=sends.arm)
             if ps else None)
    try:
        try:
            rec_obs.arm(g.state.frame)
            if traced:
                O.O8.start_run(g, side, spred, marks)
            else:
                fpass_start(g, side, spred)
            outcome = SD.drive(g, spred, side, log, deadline=time.time() + float(stage["run_s"]), floor_for=floor_for,
                               prior_for=prior_for, progress=progress, end_fields=list(ends), observe=rec_obs,
                               forbid_live=traced, witness=witness if witness is not None else O.C4.input_witness(g))
        except SD.RouteVoid as err:
            outcome = {"end": "void", "why": f"route: {err}", "v": err.v, "cell": err.cell, "by": err.by}
        except HarnessError as err:                           # the instrument's: V13, as the session reads a STOPPED
            if str(err) == MOVIE_STOP:
                sends.arm()
            outcome = {"end": "void", "why": f"STOPPED: {str(err)[:300]}", "v": "V13", "by": "driver"}
        except Exception as err:                              # noqa: BLE001 -- one run's bug must not cost the others
            outcome = {"end": "void", "why": f"STOPPED (unexpected): {type(err).__name__}: {str(err)[:300]}",
                       "v": "V13", "by": "driver"}
            log.append({"k": "error", "traceback": traceback.format_exc()[-3000:]})
        try:
            log.append({"k": "rate", **g.rate().as_dict()})
        except Exception:                                     # noqa: BLE001 -- a record, never the run
            log.append({"k": "rate", "fps": None})
    finally:                                                  # the reverse of the wrapping: each puts back what it found
        if pstop is not None:
            pstop.restore()
        if fstop is not None:
            fstop.restore()
        tap.restore()
        holds.restore()
    t_drive = time.time()
    rate = O7R._rate_record(g)
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
        trace = O.trace_summary8(rows, spred, side=side, start_place=place(start, members), end_fields=list(ends),
                                 stock=stock, log=log) if rows else {}
    except T.TraceError as err:
        trace = {"error": str(err)[:300]}
    steps = O5R._steps_rows(g)
    step_rows, bases = step_records8(log, tap.walks)
    ladder = pinch_ladder(tap.walks, log, win, members)
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
        walks=O7R.walks_record(tap.walks, log, steps, axes),
        levels=O7R.levels_record(rec_obs.grants, log, tap.walks, steps, axes),
        ladder=ladder,
        knight=knight_record(rec_obs, log, spred, trace),
        pinch=pinch_record(tap.walks, log, ladder, steps, axes, win, members),
        dead_level=dead_level_record(tap.walks, spred, members),
        movie=movie_record(rec_obs, log, spred, rows, members, outcome),
        crossing=crossing_record(rows, spred, members),
        holds=[{k: h[k] for k in ("frame", "field", "x", "z", "y", "control", "cached")} for h in holds.holds],
        pages=rec_obs.pages,
        transcript=list(outcome.get("pages") or []),
        evidence={"press": [x for x in log if x.get("k") == "press"],
                  "forbidden": [x for x in log if x.get("k") == "forbidden"],
                  "observed": [x for x in log if x.get("k") == "observed"],
                  "input": [x for x in log if x.get("k") == "input"]},
        no_progress=rec_obs.no_progress,
        end={"end_state": outcome.get("end_state"), "end_run": None},
        trace=trace,
        log_file=f"{stem}_log.json",
    )
    if not traced:
        rec["exceptions"] = O3R._exceptions(g, mark)
        rec["log_lines"] = O3R._new_log_lines(g, mark)

    def stopped(key, fired, why, extra=None):
        rec[key] = (None if fired is None else
                    {**{k: v for k, v in fired.items() if k != "t"}, "why": why,
                     "holds_after": len(O5R._holds_between(steps, fired["t"], t_drive)),
                     "presses_after": len(O7R._confirms_between(steps, fired["t"], t_drive)), **(extra or {})})
    if fstop is not None:
        stopped("flag_stop", fstop.fired, FLAG_STOP)
    if pstop is not None:
        stopped("pinch_stop", pstop.fired, PINCH_STOP)
    if stage.get("movie_stop"):
        stopped("movie_stop", rec_obs.stop_fired, MOVIE_STOP)
    end_log: list = []
    t_end = time.time()
    try:
        O.O8.end_run(g, end_log, recovery=recovery)
        rec["end"]["end_run"] = {"ok": True, "title": g.state.ui_state == "Title", "how": end_log,
                                 "s": round(time.time() - t_end, 1)}
    except HarnessError as err:
        rec["end"]["end_run"] = {"ok": False, "why": str(err)[:300], "how": end_log, "s": round(time.time() - t_end, 1)}
    finally:
        sends.restore()
    for key in ("flag_stop", "pinch_stop", "movie_stop"):
        if rec.get(key):
            rec[key]["sends_after"] = list(sends.sent)
    (g.run_dir / rec["log_file"]).write_text(json.dumps({"outcome": outcome, "log": log + end_log}, indent=1,
                                                        default=str), encoding="utf-8")
    rec["t1"] = round(time.time() - t0, 1)
    return rec


def run(g, field=None, *, stages=None, pred=None, floor_for=None, prior_for=None, stock=None, recovery=None,
        env=None, witness=None, pads=..., engine=None, live_engine=None, pinch=None, clock=None) -> None:
    """The rehearsal launch (tools/play.py's entry; ``field`` from ``--field``). Before anything, each selected stage
    takes its ids from the chain (o4_rehearse.stage_ids: ``member(N)`` resolved, every F-side id checked), EVERY run's
    predictions are built and checked (:func:`stage_run`, :func:`stage_pred`) and the launch's start is read against
    THE NIGHTLY WINDOW (``clock``, a seam: ``() -> datetime``, default the local now) -- a refusal raises here, the
    session untouched. The capabilities first (P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG over 164, 165, 166 and 55, P-LAUNCH
    with the engine, P-PAD), the launch's own readings (the settings -- VSync among them --, P-SETTINGS, P-OVERRIDE,
    P-ENGINE), then each selected stage -- its runs on its sides, or its smoke -- refused when it would START inside the
    window (``stopped`` recorded, the STOPPED HarnessError raised), the record rewritten after every run into
    ``o8_rehearsal.json``. R-FMV and R-VOID re-run a LATE-EDGE V5 (``reruns``; each run record's ``counted`` False for
    the one set aside, never counted). A run whose end_run cannot reach the title stops the launch. Every keyword is a
    seam for the fake (``pinch``: THE PINCH WINDOW)."""
    from harness import HarnessError
    stages = STAGES if stages is None else stages
    pred = O.O8.draft() if pred is None else pred
    clock = clock or _dt.datetime.now
    names = select(stages, field, env)
    stages = {n: O4R.stage_ids(stages[n], pred, name=n) for n in names}     # the chain's ids, or a refusal, first
    for n in names:
        if not stages[n].get("pairs"):
            for k in range(1, int(stages[n]["runs"]) + 1):
                stage_pred(pred, stage_run(stages[n], k))                   # a bad stop refuses before the session
    refuse_nightly(clock(), names[0])                       # a launch inside the window: refused before the session
    win = dict(PINCH_WINDOW if pinch is None else pinch)
    t0 = time.time()
    record = {"what": "O8 rehearsals (research/o8_design.md 7): R-FULL's traces alone may define predictions; the staged "
                      "runs prove mechanics; R-VOID proves the stops and the recoveries; F-SMOKE loads the members, "
                      "untraced; F-PASS drives one F run untraced and may only stop the session",
              "draft_sha256": O2R._draft_sha(pred), "stages_run": names,
              "stage_defs": {n: stages[n] for n in names}, "pinch": win,
              "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "capabilities": [], "launch": {}, "stages": {},
              "twins": {}}
    path = g.run_dir / O.REHEARSAL_FILE

    def save() -> None:
        path.write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
    caps = O.O8.capabilities(g, pads=pads, engine=engine, live_engine=live_engine)
    record["capabilities"] = [[ok, what, detail] for ok, what, detail in caps]
    for ok, what, detail in caps:
        g.check(ok, what, detail)
    record["launch"] = O4R.launch_readings(g, pred, engine=engine, live_engine=live_engine)
    save()
    if not all(ok for ok, _w, _d in caps):
        return
    kw = {"floor_for": floor_for, "prior_for": prior_for, "stock": stock, "recovery": recovery, "witness": witness,
          "pinch": win}
    for name in names:
        stage = stages[name]
        try:
            refuse_nightly(clock(), name)
        except HarnessError as err:
            record["stopped"] = str(err)
            save()
            raise
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
                tries = 1 + int(stage.get("reruns") or 0)
                for attempt in range(tries):
                    g.shot_prefix = f"{name}-{n}" + (f"r{attempt}" if attempt else "")
                    try:
                        rec = one(g, name, stage, pred, n, side=side, t0=t0, attempt=attempt, **kw)
                    finally:
                        g.shot_prefix = ""
                    if attempt:
                        rec["rerun_of"] = n
                    late = bool((rec.get("movie") or {}).get("late_v5"))
                    rec["counted"] = not late                # a late-edge V5 is re-run, never counted (F3)
                    record["stages"].setdefault(name, []).append(rec)
                    save()
                    print(f"[o8-rh] {name} run {n} ({side}){' re-run' if attempt else ''}: {rec['outcome']['end']} -- "
                          f"{rec['outcome']['why']}", flush=True)
                    if not (rec["end"]["end_run"] or {}).get("ok"):
                        record["stopped"] = f"{name} run {n}: end_run could not reach the title"
                        save()
                        return
                    if not late:
                        break
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
