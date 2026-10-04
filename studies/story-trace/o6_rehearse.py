"""O6's REHEARSALS (research/o6_design.md section 7): Steiner's naming, the assembly and his first door on STOCK
Alexandria Castle, stage by stage, the F-side load smoke and one untraced F pass before the freeze. Each traced stage
warps into its start (151 at entrance 110, or 153 at 328) at SC 1190, drives the DRAFT (its stage overlay laid on a
COPY and checked) to its own end fields, and records what the freeze checklist (7.3) is read from; F-SMOKE warps into
each member and its stock twin with NO trace and records what loaded; F-PASS drives one F run through the whole route
with NO trace. Nothing is deployed and nothing is frozen here.

    py tools/play.py studies/story-trace/o6_rehearse.py --field 151 --label o6-rh-door --timeout 240    # R-DOOR
    py tools/play.py studies/story-trace/o6_rehearse.py --label o6-rh --timeout 240             # the default order
    set O6_STAGE=R-NAMING-VOID & py tools/play.py studies/story-trace/o6_rehearse.py --label o6-rh-naming-void --timeout 240
    set O6_STAGE=R-WALK-VOID & py tools/play.py studies/story-trace/o6_rehearse.py --label o6-rh-walk-void --timeout 240
    set O6_WALK_STOP=hold & ...                      # R-WALK-VOID with F15's fallback (or a z: F15's walk_stop_z)
    set O6_STAGE=F-SMOKE & py tools/play.py studies/story-trace/o6_rehearse.py --label o6-rh-smoke --timeout 240
    set O6_STAGE=F-PASS & py tools/play.py studies/story-trace/o6_rehearse.py --label o6-rh-fpass --timeout 240
    py studies/story-trace/o6_steiner.py --rehearsal-report <run dir>

WHICH STAGE: the environment variable ``O6_STAGE`` names one (R-DOOR, R-NAMING-VOID, R-WALK-VOID, F-SMOKE, F-PASS);
else ``--field 151`` picks R-DOOR, the one stage warping into 151 that is not by-name-only; else, in one launch: R-DOOR
(the go/no-go and the predictions), then R-NAMING-VOID and R-WALK-VOID LAST -- each stops its run, so a recovery that
fails there ends the launch, and that failure is the finding. F-SMOKE and F-PASS run only by name.

EACH TRACED RUN: New Game; the story trace armed; the raw warp (Segment.start_run); then segment_drive.drive on the
stage's predictions with its end fields, the live forbidden scan on, the run-wide input witness and the recorder (O5's:
grants with the published objects, pages with ``gone_frame``, the KEYON pairs, the timed windows, the dialog-section
catch -- plus THE NAMING SCAN off the ring: the screen's first sample, 198's last before it, the close, every [STNR]
window's rendered lines) watching every poll; the WALK TAP on ``route_to`` (O5's) and the HOLD TAP on ``send`` (every
direction hold as it is sent: where he stood, and whether the field's basis was cached -- a calibration probe is not);
the trace collected to ``rh_<stage>_<n>.jsonl``; the record written into ``o6_rehearsal.json``; end_run (S15's), its
rows and its seconds recorded.

R-NAMING-VOID: the stage key ``naming_stop`` -- the NAMING STOP wraps ``g.accept_name``: its FIRST call (rule 4's)
raises "the rehearsal's stop at the naming screen" before any Confirm, the session's own restored at once; then
end_run reads S15's rows (``recover-warp-failed``, ``end-naming``, ``recover-warp-after-naming``) to the title, its time
from the stop recorded. R-WALK-VOID: the stage overlay ``walk_stop_z`` (500, or the z F15 takes from R-DOOR's hold-2
starts: ``O6_WALK_STOP=<z>``) or F15's fallback ``walk_stop_hold`` (``O6_WALK_STOP=hold``) lies on the north door step
of the stage's COPY of the predictions (the freeze refuses it anywhere else), and the WALK STOP wraps ``g.send`` on the
driver's own thread: the first direction hold sent in 153 while the published z is at or past it -- or, the fallback,
once 153's basis is cached (the calibration done) -- raises "the rehearsal's stop mid-walk" BEFORE it is sent, the send
restored at once, so end_run's warp and ladder go through and nothing keeps sending after it. Never a timer.

F-SMOKE (NO trace): o4_rehearse.smoke on O6's pairs -- member(151) / 151 at 110, member(153) / 153 at 328,
member(154) / 154 at 315, all SC 1190 -- each id read from the chain. F-PASS (NO trace; before the freeze): New Game,
``wait_frames(30)``, the raw warp into member(151), then the drive to member(154) with the live forbidden scan off and
no end-row wait; it may only STOP the session (F14), never shape a frozen value.

WHAT A STAGE MAY SETTLE (7.1): only R-DOOR's traces may define or change the keys, the start, the end state, the
naming's lines or the row pattern. The void stages prove mechanics. Every summary is cut at the stage's end PLACES
(o6_steiner.trace_summary).
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
import o5_hallway as C5                                                # noqa: E402
import o5_rehearse as O5R                                              # noqa: E402
import o6_steiner as O                                                 # noqa: E402
import segment_drive as SD                                             # noqa: E402
from ff9mapkit import storytrace as T                                  # noqa: E402
from segment_trace import members_of, place                            # noqa: E402

ENV = "O6_STAGE"
#: F15's choice for R-WALK-VOID (7.3), set by the lead after R-DOOR: a number -- the ``walk_stop_z`` taken from R-DOOR's
#: hold-2 starts -- or ``hold``, the fallback ``walk_stop_hold``. Unset: the stage's own (the draft's 500).
ENV_WALK_STOP = "O6_WALK_STOP"
#: The stops' own words (the session's V13 reads them back off the outcome).
NAMING_STOP = "the rehearsal's stop at the naming screen"
WALK_STOP = "the rehearsal's stop mid-walk"
#: R-WALK-VOID's draft z stop (7.1, F15): the floor of the band every R-DOOR record reads its walk holds in (``[this,
#: the door's line)``), whichever stop the launch runs.
WALK_STOP_Z = 500.0
#: The stages (research/o6_design.md 7.1): the warp, the end fields (per side where they differ), the runs, a run budget
#: and a cost estimate in seconds a run (F6 replaces every number from what is measured). ``by_name``: never picked by
#: ``--field``; ``optional``: only by name; ``last``: after every other stage of a launch; ``sides``: the sides a stage
#: runs (default S); ``untraced``: no storytrace verb (F-PASS); ``naming_stop``: R-NAMING-VOID's stop (a stage key
#: :func:`one` reads); ``walk_stop_z`` / ``walk_stop_hold``: R-WALK-VOID's, laid on the walk step of the stage's COPY of
#: the predictions. A member is named ``member(<donor>)``, never by its id: o4_rehearse.stage_ids reads it from the chain.
STAGES = {
    "R-DOOR": {"field": 151, "entrance": 110, "sc": 1190, "end": [154], "runs": 2, "run_s": 600, "cost_s": 150,
               "settles": "F1-F6, F8, F10-F12, F15 (the go/no-go and the predictions): 151's pages, pairs and timed "
                          "windows; the naming (the screen's first sample, every Confirm's down frame, the close, the "
                          "named row and its before); the name_on_page row (its windows' lines, its verdict; 199 -> 200); "
                          "the ip610 row; the e15 row (its attribution, frame, index and gap to ip971); the grant; the "
                          "calibration; the walk (every hold, hold 1's end and the corner, the walk holds in "
                          "[walk_stop_z, 1333), the hold-2 starts); the loss; THE LANDING PATH and S14b's walk-out; the "
                          "end cut 154 e0 t0 ip26; the keys, the masked rows, the pattern; the end state; the run time; "
                          "the longest no-progress stretch -- the ONLY stage whose traces define predictions"},
    "R-NAMING-VOID": {"field": 151, "entrance": 110, "sc": 1190, "end": [154], "runs": 1, "run_s": 300, "cost_s": 60,
                      "by_name": True, "last": True, "naming_stop": True,
                      "settles": "F7: the run stopped WITH THE SCREEN UP (rule 4's first accept_name raises, before any "
                                 "Confirm); end_run's recover-warp-failed, end-naming (the screen accepted at once, no "
                                 "close_ui before it), recover-warp-after-naming (4600), the title; its seconds from the "
                                 "stop to the title (F6)"},
    "R-WALK-VOID": {"field": 153, "entrance": 328, "sc": 1190, "end": [154], "runs": 1, "run_s": 300, "cost_s": 60,
                    "by_name": True, "last": True, "walk_stop_z": WALK_STOP_Z,
                    "settles": "F7: the walk stopped MID-WALK (the first direction hold sent in 153 at a published z at "
                               "or past walk_stop_z raises, never sent -- or, F15's fallback walk_stop_hold, the first "
                               "after 153's basis is cached: V13) with no hold after the stop; end_run (the warp to 4600 "
                               "from 153's FieldHUD, the ladder) reaches the title"},
    "F-SMOKE": {"pairs": [["member(151)", 151, 110, 1190], ["member(153)", 153, 328, 1190],
                          ["member(154)", 154, 315, 1190]], "runs": 1,
                "smoke_s": 8.0, "warp_s": 60.0, "cost_s": 180, "by_name": True, "optional": True,
                "settles": "F13: each member loads at its entrance and SC (its field, FieldHUD), its published object "
                           "sids EQUAL to its stock twin's measured set after smoke_s (the bytes predict 151@110 {4, 5, "
                           "12, 17}, 153@328 {13, 14, 16, 17}, 154@315 {5, 6, 7} -- only the twin's reading is "
                           "compared); 0 exceptions; end_run ok"},
    "F-PASS": {"field": {"S": 151, "F": "member(151)"}, "entrance": 110, "sc": 1190,
               "end": {"S": [154], "F": ["member(154)"]}, "sides": ["F"], "untraced": True, "runs": 1, "run_s": 600,
               "cost_s": 150, "by_name": True, "optional": True,
               "settles": "F14 (may only STOP the session): one F run through the whole route on the DRAFT, untraced -- "
                          "reached member(154), beats named / name_on_page / steiner_door, no V-class, no exception "
                          "through the story machinery since the warp; its record is never evidence for any key and "
                          "never shapes a frozen value"},
}


def select(stages: dict, field=None, env=None) -> list:
    """The stage names a launch runs: ``O6_STAGE`` (one, by name), else the one stage warping into ``field`` that is
    not ``by_name``, else every non-optional stage in the table's order with the ``last`` ones after the rest --
    R-NAMING-VOID, then R-WALK-VOID, end the launch."""
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


def with_walk_stop(stage: dict, env=None) -> dict:
    """R-WALK-VOID's stop as F15 settles it after R-DOOR (7.3): ``O6_WALK_STOP`` -- a number, the ``walk_stop_z`` taken
    from R-DOOR's hold-2 starts, or ``hold``, the fallback ``walk_stop_hold`` (the run stopped inside the step before his
    first walk hold) -- laid on a COPY of a stage that carries a walk stop. Unset, or a stage with no walk stop: the
    stage as it is. Any other value raises ValueError before anything is driven."""
    env = os.environ if env is None else env
    v = str(env.get(ENV_WALK_STOP) or "").strip()
    if not v or (stage.get("walk_stop_z") is None and not stage.get("walk_stop_hold")):
        return stage
    s = dict(stage)
    if v.lower() == "hold":
        s.pop("walk_stop_z", None)
        s["walk_stop_hold"] = True
        return s
    try:
        z = float(v)
    except ValueError:
        raise ValueError(f"{ENV_WALK_STOP}={v!r}: a z (F15's walk_stop_z) or 'hold' (its fallback)") from None
    s.pop("walk_stop_hold", None)
    s["walk_stop_z"] = z
    return s


def stage_pred(pred: dict, stage: dict) -> dict:
    """The draft with the stage's own start on each side, entrance and scenario; the stage's walk stop
    (``walk_stop_z`` / ``walk_stop_hold`` / ``walk_stop_x``: o6_steiner.REHEARSAL_OVERLAYS, the keys the freeze refuses)
    laid on the copy's WALK step (``walk.name``); for an untraced stage, no end-row wait (``end_row_s`` None: no trace
    to wait on). Then checked as the driver will read it -- segment_drive.naming_of, witness_of and step_of on every
    table step -- so a bad overlay refuses before anything is driven. R-NAMING-VOID's ``naming_stop`` is the stage's,
    read by :func:`one`, never the predictions'. The predictions given are never changed."""
    p = copy.deepcopy(pred)
    p.update(start={"S": O4R.stage_start(stage, "S"), "F": O4R.stage_start(stage, "F")}, entrance=stage["entrance"],
             scenario=stage["sc"])
    over = {k: stage[k] for k in sorted(O.REHEARSAL_OVERLAYS) if stage.get(k) not in (None, False)}
    if len(over) > 1:
        raise ValueError(f"a stage stops its walk one way, not {sorted(over)}")
    if over:
        name = (p.get("walk") or {}).get("name")
        steps = [s for c in p.get("table") or () for s in c["steps"] if s.get("name") == name]
        if len(steps) != 1:
            raise ValueError(f"{next(iter(over))}: {len(steps)} table step(s) named {name!r}, not the one walk")
        k, v = next(iter(over.items()))
        steps[0][k] = True if k == "walk_stop_hold" else float(v)
    if stage.get("untraced"):
        p["budget"] = dict(p.get("budget") or {}, end_row_s=None)
    SD.naming_of(p)
    SD.witness_of(p)
    for c in p.get("table") or ():
        for s in c["steps"]:
            SD.step_of(p, s)
    return p


def walk_field(pred: dict, side: str) -> int | None:
    """The field the walk runs in on ``side``: its place (``walk.donor``) on S, the one member forking it on F."""
    donor = (pred.get("walk") or {}).get("donor")
    if donor is None or side != "F":
        return donor
    hits = sorted(f for f, d in members_of(pred).items() if d == donor)
    return hits[0] if len(hits) == 1 else None


def door_line(pred: dict):
    """The door's line (the z its tag-2 test must pass: 1333) read from the predictions' pinned texts
    (o6_steiner._door_test_of, O6-GOALS (c'')'s reading), or None."""
    door = (pred.get("walk") or {}).get("door")
    if not door:
        return None
    _text, test = O._door_test_of(pred, door)
    return None if test is None else test[1]


# ======================================================================== the run's own instruments
class Recorder(O5R.Recorder):
    """O5's recorder (grants with their published objects, pages with ``gone_frame``, the published choices, the
    no-progress stretch, the dialog-section catch -- no guard, no stair teleport) plus THE NAMING SCAN (7.2, F3), read
    off the RING at every poll -- each sample the harness read since the last scan, once, oldest first, so the samples
    of accept_name's blocking call are read too: the screen's first sample (``ui_state`` NameSetting) and the last one
    listing the naming's marker (``name.before.marker``: 198's "And, Captain") before it; the close (the first sample
    after it off the screen); and every window whose raw holds the page witness's tag ([STNR]) -- by its raw: its frozen
    mes (the entry naming it, else None), field, first frame, the samples read while it was listed, how many of them
    listed it UNPARSED (the tag in its text: expected none, 0.2 #8) and its distinct rendered texts."""

    def __init__(self, g, stage: dict, pred: dict):
        super().__init__(g, stage, pred, guard={})
        self.walk_place = None                          # O5's stair teleport: O6's walk has none
        nm = pred.get("name") or {}
        self.marker = (nm.get("before") or {}).get("marker")
        reg = next(iter(SD.naming_of(pred)), None) or {}
        page = reg.get("on_page") or {}
        self.tag = page.get("tag") or "[STNR]"
        self.frozen = list(page.get("windows") or ())
        self.naming = {"screen_first": None, "last_198": None, "close_frame": None}
        self.stnr: dict = {}
        self._nscanned = None

    def naming_scan(self, st) -> None:
        since = st.frame - 1 if self._nscanned is None else self._nscanned
        try:
            raws = self.g.states_since(since)
        except Exception:                                      # noqa: BLE001 -- a record, never the run
            return
        n = self.naming
        for raw in raws:
            f = int(raw.get("frame", -1))
            if self._nscanned is not None and f <= self._nscanned:
                continue
            self._nscanned = f
            fld = int((raw.get("field") or {}).get("id", -1))
            ui = raw.get("ui_state")
            rows = SD.dialog_rows(raw)
            if n["screen_first"] is None:
                if ui == "NameSetting":
                    n["screen_first"] = {"frame": f, "field": fld}
                elif self.marker and any(self.marker in ph or self.marker in tx for ph, tx in rows):
                    n["last_198"] = {"frame": f, "field": fld}
            elif n["close_frame"] is None and ui != "NameSetting":
                n["close_frame"] = f
            for ph, tx in rows:
                if self.tag not in ph:
                    continue
                w = self.stnr.get(ph)
                if w is None:
                    mes = next((e["mes"] for e in self.frozen if e["raw_holds"] in ph), None)
                    w = self.stnr[ph] = {"mes": mes, "raw": ph[:100], "field": fld, "first": f, "samples": 0,
                                         "unparsed": 0, "lines": []}
                w["samples"] += 1
                if self.tag in tx:
                    w["unparsed"] += 1
                elif tx not in w["lines"]:
                    w["lines"].append(tx)

    def __call__(self, st, ctx: dict) -> None:
        super().__call__(st, ctx)
        self.naming_scan(st)


def _direction_hold(s) -> bool:
    parts = str(s).split()
    return len(parts) > 1 and parts[0] == "hold" and parts[1] in O5R._BUTTON_AXIS


def _cached(g, fid) -> bool:
    """Whether the session holds a basis for field ``fid`` (route_to's calibration done there)."""
    try:
        return fid in getattr(g, "_axes", {})
    except Exception:                                          # noqa: BLE001 -- a record, never the run
        return False


class HoldTap:
    """THE HOLD TAP (7.2): ``g.send`` wrapped on the instance -- each request holding a DIRECTION hold recorded as it
    is sent: its wall time, the published frame, field, position and control, and whether that field's basis was
    cached in ``g._axes`` then (``cached`` False: route_to's calibration probes, never a walk hold) -- then sent.
    :meth:`restore` puts the session's own back."""

    def __init__(self, g):
        self.g, self.holds = g, []
        self._had = "send" in vars(g)
        self._orig = vars(g).get("send")
        real = g.send

        def send(*steps, **kw):
            if any(_direction_hold(s) for s in steps):
                st = g.state
                self.holds.append({"t": time.time(), "frame": st.frame, "field": st.field_id,
                                   "x": None if st.player_x is None else round(st.player_x, 1),
                                   "z": None if st.player_z is None else round(st.player_z, 1),
                                   "control": bool(st.control), "cached": _cached(g, st.field_id),
                                   "steps": [str(s) for s in steps]})
            return real(*steps, **kw)
        g.send = send

    def restore(self) -> None:
        if self._had:
            self.g.send = self._orig
        else:
            vars(self.g).pop("send", None)


class WalkStop:
    """THE WALK STOP (7.1, F7; O5's generalized): ``g.send`` wrapped on the driver's own thread -- the first request
    holding a DIRECTION hold sent in ``field`` while the published x stands at or west of ``x_stop`` (O5's), the
    published z at or past ``z_stop`` (R-WALK-VOID's: 153's hold 2, inside e23's quad in its non-firing band), or, with
    ``hold_stop``, once ``field``'s basis is cached in ``g._axes`` (F15's fallback: the calibration done, before his
    first walk hold -- never a calibration probe) raises "the rehearsal's stop mid-walk" BEFORE it is sent, the
    session's own send restored at once (end_run's warp and ladder go through it; nothing keeps sending after the
    raise). ``fired``: the stop's frame, position, wall time, which stop, and the steps it held back. Never a timer: a
    timer expires in route_to's settle, its rate wait or its calibration, never where the stop must land."""

    def __init__(self, g, field: int, *, x_stop=None, z_stop=None, hold_stop: bool = False):
        from harness import HarnessError
        kinds = [k for k, v in (("x", x_stop), ("z", z_stop), ("hold", hold_stop or None)) if v is not None]
        if len(kinds) != 1:
            raise ValueError(f"a walk stop is one of x_stop, z_stop or hold_stop, not {kinds or 'none'}")
        self.g, self.field = g, int(field)
        self.x_stop = None if x_stop is None else float(x_stop)
        self.z_stop = None if z_stop is None else float(z_stop)
        self.hold_stop = bool(hold_stop)
        self.by = (f"walk_stop_x {self.x_stop:g}" if self.x_stop is not None else
                   f"walk_stop_z {self.z_stop:g}" if self.z_stop is not None else "walk_stop_hold")
        self.fired = None
        self._had = "send" in vars(g)
        self._orig = vars(g).get("send")
        real = g.send

        def send(*steps, **kw):
            if self.fired is None and any(_direction_hold(s) for s in steps):
                st = g.state
                if st.field_id == self.field and self.hit(st):
                    x = None if st.player_x is None else round(st.player_x, 1)
                    z = None if st.player_z is None else round(st.player_z, 1)
                    self.fired = {"t": time.time(), "frame": st.frame, "x": x, "z": z, "by": self.by,
                                  "cached": _cached(g, self.field), "steps": list(steps)}
                    self.restore()
                    raise HarnessError(f"{WALK_STOP}: a hold at ({x}, {z}) ({self.by}) in {self.field}, never sent")
            return real(*steps, **kw)
        g.send = send

    def hit(self, st) -> bool:
        if self.x_stop is not None:
            return st.player_x is not None and st.player_x <= self.x_stop
        if self.z_stop is not None:
            return st.player_z is not None and st.player_z >= self.z_stop
        return _cached(self.g, self.field)

    def restore(self) -> None:
        if self._had:
            self.g.send = self._orig
        else:
            vars(self.g).pop("send", None)


class NamingStop:
    """R-NAMING-VOID's STOP (7.1, F7): ``g.accept_name`` wrapped on the instance -- its FIRST call (rule 4's, with the
    screen up) raises "the rehearsal's stop at the naming screen" before any Confirm, the session's own restored at once,
    so end_run's own accept_name (S15's ``end-naming``) is the real one. ``fired``: the stop's wall time, frame, UI and
    field."""

    def __init__(self, g):
        from harness import HarnessError
        self.g, self.fired = g, None
        self._had = "accept_name" in vars(g)
        self._orig = vars(g).get("accept_name")

        def accept_name(*a, **kw):
            st = g.state
            self.fired = {"t": time.time(), "frame": st.frame, "ui": st.ui_state, "field": st.field_id}
            self.restore()
            raise HarnessError(f"{NAMING_STOP}: the screen up in {st.field_id} (ui {st.ui_state}), before any Confirm")
        g.accept_name = accept_name

    def restore(self) -> None:
        if self._had:
            self.g.accept_name = self._orig
        else:
            vars(self.g).pop("accept_name", None)


# ======================================================================== the records (pure)
def _walk_of(walks: list, s: dict):
    """The tapped walk of step row ``s`` (O5's join: its field, begun from the row's frame0 to its frame)."""
    return next((x for x in walks if x["field"] == s.get("field") and s.get("frame0") is not None
                 and x["frame0"] >= s["frame0"] - 2 and x["frame0"] <= (s.get("frame") or x["frame0"])), None)


def _path(row: dict):
    """THE LANDING PATH of a door step row (S14): A -- route_to returned before the map switch (``route.landed``
    None) -- or B -- after it; None for a step that is not done."""
    if row.get("outcome") != "done":
        return None
    return "A" if (row.get("route") or {}).get("landed") is None else "B"


def door_walk_record(walks: list, log: list, pred: dict, rec_obs, *, basis=None, steps=(), holds=(), band=(None, None),
                     fps=None, tick_hz=30.0) -> dict:
    """7.2's walk record for the north door: O5's (the grant -- its frame, position, the frames from the last page's
    going, the published objects; each attempt's tapped walk, every hold read from steps.jsonl with its slide and
    stall, the last control sample and the first without; the calibration basis), no stair teleport, plus per attempt
    THE LANDING PATH (``path`` A or B, ``route.landed``, ``changed_to``, ``handoff``, S14b's ``flip_frame`` /
    ``flip_late`` / ``landed_frame`` and the walk-out's samples -- where it stopped -- and the frames loss -> flip ->
    landing) and, from the hold tap (``holds``), the walk's direction holds sent AFTER the calibration (``cached``):
    hold 1's end point (where hold 2 began, else the loss), THE CORNER (hold 1's own reading -- moved, off the pressed
    direction, slide, stall -- the walk's pushes, the route's replans and blockers), every walk hold sent while the
    published z lay in ``band`` (``[walk_stop_z, the door's line)``: F15), hold 2's start, and the probes counted."""
    out = O5R.walk_record(walks, log, pred, rec_obs, basis=basis, steps=steps, fps=fps, tick_hz=tick_hz)
    lo, hi = band
    for att, row in zip(out["attempts"], C5.walk_rows(log, pred)):
        route = row.get("route") or {}
        wo = row.get("walkout") or []
        lost = row.get("lost") or {}
        loss, flip, landed = lost.get("frame"), row.get("flip_frame"), row.get("landed_frame")
        att.update(path=_path(row), route_landed=route.get("landed"), changed_to=route.get("changed_to"),
                   handoff=route.get("handoff"), flip_frame=flip, flip_late=row.get("flip_late"), landed_frame=landed,
                   misroute=row.get("misroute"), walkout_samples=len(wo),
                   walkout_stop=None if not wo else {"frame": wo[-1][0], "x": wo[-1][1], "z": wo[-1][2],
                                                     "control": wo[-1][3]},
                   frames={"loss_to_flip": None if loss is None or flip is None else flip - loss,
                           "flip_to_landed": None if flip is None or landed is None else landed - flip})
        w = att.get("walk")
        walk = _walk_of(walks, row)
        if w is None or walk is None:
            continue
        w.pop("teleport", None)
        span = [h for h in holds if walk["t0"] <= h["t"] <= walk["t1"] and h["field"] == walk["field"]]
        wh = [h for h in span if h["cached"]]
        h1 = next((h for h in w.get("holds") or () if wh and h.get("ack_frame") is not None
                   and h["ack_frame"] >= wh[0]["frame"]), None)
        end1 = ([wh[1]["x"], wh[1]["z"]] if len(wh) > 1 else
                [lost.get("x"), lost.get("z")] if lost.get("x") is not None else None)
        w.update(walk_holds=[{k: h[k] for k in ("frame", "x", "z", "control")} for h in wh],
                 probes=len(span) - len(wh), hold1_end=end1,
                 corner={"hold1": None if h1 is None else {k: h1.get(k) for k in ("from", "to", "moved", "off_pressed",
                                                                                   "slide", "stall")},
                         "pushes": walk.get("pushes"), "pushed": walk.get("pushed"), "replans": route.get("replans"),
                         "blockers": route.get("blockers")},
                 in_band={"lo": lo, "hi": hi, "holds": [[h["frame"], h["x"], h["z"]] for h in wh
                                                        if lo is not None and h["z"] is not None and h["z"] >= lo
                                                        and (hi is None or h["z"] < hi)]},
                 hold2=None if len(wh) < 2 else {k: wh[1][k] for k in ("frame", "x", "z")})
    return out


def naming_record(rec_obs, log: list, rows: list, pred: dict, *, steps=(), events=(), members=None) -> dict:
    """7.2's naming record (F3): the recorder's naming scan -- the screen's first sample, the last 198 sample before it,
    the close -- and every Confirm REQUEST (steps.jsonl) whose down frame (events.jsonl's accepted + 1, else its ack
    frame) lies after that last 198 sample and at or before the close, each named by whose it was: ``rule 7`` (a page
    press of the driver's log, joined to its request: o5_rehearse.page_requests) or ``accept_name`` -- which press did
    Confirm 1's job; the ``named`` row (its ``before``) and the ``name_on_page`` row (its windows and ``verdict``), with
    their counts; every [STNR] window the recorder read, in first-seen order; the frames from the first frozen window's
    first sample to the second's (199 -> 200: the bytes' ~6 ticks); and the frame of the naming's store row
    (``name.store``: 151 e3 t1 ip610) in the trace."""
    n = dict(getattr(rec_obs, "naming", None) or {})
    named, pages = O.naming_rows(log, pred)
    acc: dict = {}
    for e in events or ():
        if e.get("kind") == "accepted" and e.get("seq") is not None:
            try:
                acc.setdefault(int(e["seq"]), int(e["frame"]))
            except (TypeError, ValueError):
                continue
    rule7 = {q["seq"] for _row, q in O5R.page_requests(log, steps, events) if q.get("seq") is not None}
    lo = ((n.get("last_198") or n.get("screen_first")) or {}).get("frame")
    hi = n.get("close_frame")
    confirms = []
    for r in steps or ():
        if lo is None or r.get("seq") is None or SD._press_button(r.get("steps")) not in SD.CONFIRM_NAMES:
            continue
        seq = int(r["seq"])
        a = acc.get(seq)
        down = None if a is None else a + 1
        at = down if down is not None else r.get("frame")
        if at is None or at <= lo or (hi is not None and at > hi):
            continue
        confirms.append({"seq": seq, "why": "rule 7" if seq in rule7 else "accept_name", "down_frame": down,
                         "ack_frame": r.get("frame")})
    stnr = sorted((getattr(rec_obs, "stnr", None) or {}).values(), key=lambda w: w["first"])
    firsts: dict = {}
    for w in stnr:
        if w.get("mes") is not None:
            firsts.setdefault(w["mes"], w["first"])
    reg = next(iter(SD.naming_of(pred)), None) or {}
    order = [e["mes"] for e in (reg.get("on_page") or {}).get("windows") or ()]
    lag = (firsts[order[1]] - firsts[order[0]] if len(order) > 1 and order[0] in firsts and order[1] in firsts
           else None)
    store = (pred.get("name") or {}).get("store") or {}
    hit = next((x for x in rows or () if x.k == "w" and place(x.fld, members or {}) == store.get("place")
                and (x.sid, x.tag, x.ip, x.target) == (store.get("sid"), store.get("tag"), store.get("ip"),
                                                       store.get("target"))), None)
    return {**n, "confirms": confirms, "named": named[0] if named else None, "named_rows": len(named),
            "page": pages[0] if pages else None, "page_rows": len(pages), "stnr": stnr, "lag_199_200": lag,
            "f610": None if hit is None else hit.f}


# ======================================================================== a run and a launch
def one(g, name: str, stage: dict, pred: dict, n: int, *, side: str = "S", t0: float, floor_for=None,
        prior_for=None, stock=None, recovery=None, witness=None) -> dict:
    """One rehearsal run of ``stage`` on ``side`` (7.1): its record (7.2) -- O5's sections (the outcome, the beats, the
    launch's measured rate, the grants, the pages and the transcript, the KEYON pairs and the timed windows, the
    dialog-section catch, the press, forbidden, observed and input evidence, the longest no-progress stretch, the end
    state, end_run's rows) plus THE NAMING (:func:`naming_record`), THE WALK (:func:`door_walk_record`: the landing
    path, hold 1 and the corner, the band's holds, hold 2), and the trace through O6's summary cut at the stage's end
    PLACES (the crossings, the e15 row, the start-dependent rows); end_run's seconds. An untraced stage (F-PASS) starts by
    o5_rehearse.fpass_start, drives with the live forbidden scan off and records the exceptions and Memoria.log lines
    since the warp instead of a trace. R-WALK-VOID's :class:`WalkStop` records its stop and the direction holds the run
    requested before it (the walk had begun) and after it, before end_run (there must be none); R-NAMING-VOID's
    :class:`NamingStop` its stop and the seconds from it to the title. A run the instrument stopped (a HarnessError:
    outside input, the budget, a refused press, a stop; or an unexpected exception) records the class V13 (driver).
    ``witness`` (the outside-input witness; default the ctypes one) is a seam for the fake."""
    from harness import HarnessError
    spred = stage_pred(pred, stage)
    ends = O4R.stage_ends(stage, side)
    start = O4R.stage_start(stage, side)
    members = members_of(spred) if side == "F" else {}
    traced = not stage.get("untraced")
    log, progress, marks = [], {}, {}
    rec_obs = Recorder(g, stage, spred)
    trace_name = f"rh_{name}_{n}.jsonl" if traced else None
    t_run = time.time()
    rec = {"stage": name, "n": n, "side": side, "t0": round(t_run - t0, 1), "trace_file": trace_name,
           "traced": traced, "forbid_live": traced}
    outcome = {"end": "void", "why": "not driven"}
    mark = g.log_mark()
    wfield = walk_field(spred, side)
    tap = O5R.WalkTap(g)
    holds = HoldTap(g)
    stop = None
    if any(stage.get(k) not in (None, False) for k in O.REHEARSAL_OVERLAYS):
        stop = WalkStop(g, wfield, x_stop=stage.get("walk_stop_x"), z_stop=stage.get("walk_stop_z"),
                        hold_stop=bool(stage.get("walk_stop_hold")))
    nstop = NamingStop(g) if stage.get("naming_stop") else None
    try:
        try:
            if traced:
                O.O6.start_run(g, side, spred, marks)
            else:
                O5R.fpass_start(g, side, spred)
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
    finally:
        if nstop is not None:
            nstop.restore()
        if stop is not None:
            stop.restore()
        holds.restore()
        tap.restore()
    t_drive = time.time()
    fps, tick_hz = O5R._rate(g)
    basis = getattr(g, "_axes", {}).get(wfield) if hasattr(g, "_axes") and wfield is not None else None
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
    pages = rec_obs.pages
    rec.update(
        outcome={k: outcome.get(k) for k in ("end", "why", "v", "cell", "by", "t")},
        beats=outcome.get("beats"),
        rate={"fps": fps, "tick_hz": tick_hz},
        grants=rec_obs.grants,
        naming=naming_record(rec_obs, log, rows, spred, steps=steps, events=events, members=members),
        walk=door_walk_record(tap.walks, log, spred, rec_obs, basis=basis, steps=steps, holds=holds.holds,
                              band=(float(stage.get("walk_stop_z") or WALK_STOP_Z), door_line(spred)), fps=fps,
                              tick_hz=tick_hz),
        windows=O5R.windows_record(pages, log, fps=fps, tick_hz=tick_hz),
        catch={"samples": rec_obs.samples_read, "caught": rec_obs.catch},
        pages=pages,
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
    if stop is not None:
        f = stop.fired
        rec["walk_stop"] = (None if f is None else
                            {**{k: v for k, v in f.items() if k != "t"},
                             "holds_before": len(O5R._holds_between(steps, t_run, f["t"])),
                             "holds_after": len(O5R._holds_between(steps, f["t"], t_drive))})
    end_log: list = []
    t_end = time.time()
    try:
        O.O6.end_run(g, end_log, recovery=recovery)
        rec["end"]["end_run"] = {"ok": True, "title": g.state.ui_state == "Title", "how": end_log,
                                 "s": round(time.time() - t_end, 1)}
    except HarnessError as err:
        rec["end"]["end_run"] = {"ok": False, "why": str(err)[:300], "how": end_log, "s": round(time.time() - t_end, 1)}
    if nstop is not None:
        f = nstop.fired
        ok = rec["end"]["end_run"]["ok"]
        rec["naming_stop"] = (None if f is None else
                              {**{k: v for k, v in f.items() if k != "t"}, "why": NAMING_STOP,
                               "recovery_s": round(time.time() - f["t"], 1) if ok else None})
    (g.run_dir / rec["log_file"]).write_text(json.dumps({"outcome": outcome, "log": log + end_log}, indent=1,
                                                        default=str), encoding="utf-8")
    rec["t1"] = round(time.time() - t0, 1)
    return rec


def run(g, field=None, *, stages=None, pred=None, floor_for=None, prior_for=None, stock=None, recovery=None,
        env=None, witness=None, pads=..., engine=None, live_engine=None) -> None:
    """The rehearsal launch (tools/play.py's entry; ``field`` from ``--field``). Before anything, each selected stage
    takes its ids from the chain (o4_rehearse.stage_ids: ``member(N)`` resolved, every F-side id checked) and F15's walk
    stop from ``O6_WALK_STOP`` (:func:`with_walk_stop`), and its predictions are built and checked (:func:`stage_pred`)
    -- a refusal raises here, the session untouched; the record keeps the resolved stages. The capabilities first
    (P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG over 151/153/154, P-LAUNCH with the engine, P-PAD), the launch's own readings
    (the settings, P-SETTINGS, P-OVERRIDE, P-ENGINE), then each selected stage -- its runs on its sides, or its smoke --
    the record rewritten after every run into ``o6_rehearsal.json``. A run whose end_run cannot reach the title stops
    the launch. Every keyword is a seam for the fake; each defaults to the real thing."""
    stages = STAGES if stages is None else stages
    pred = O.O6.draft() if pred is None else pred
    names = select(stages, field, env)
    stages = {n: with_walk_stop(O4R.stage_ids(stages[n], pred, name=n), env) for n in names}
    for n in names:
        if not stages[n].get("pairs"):
            stage_pred(pred, stages[n])                                     # a bad overlay refuses before the session
    t0 = time.time()
    record = {"what": "O6 rehearsals (research/o6_design.md 7): R-DOOR's traces alone may define predictions; the void "
                      "stages prove the stops and the recoveries; F-SMOKE loads the members, untraced; F-PASS drives one "
                      "F run untraced and may only stop the session",
              "draft_sha256": O2R._draft_sha(pred), "stages_run": names,
              "stage_defs": {n: stages[n] for n in names}, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "capabilities": [], "launch": {}, "stages": {}, "twins": {}}
    path = g.run_dir / O.REHEARSAL_FILE

    def save() -> None:
        path.write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
    caps = O.O6.capabilities(g, pads=pads, engine=engine, live_engine=live_engine)
    record["capabilities"] = [[ok, what, detail] for ok, what, detail in caps]
    for ok, what, detail in caps:
        g.check(ok, what, detail)
    record["launch"] = O4R.launch_readings(g, pred, engine=engine, live_engine=live_engine)
    save()
    if not all(ok for ok, _w, _d in caps):
        return
    kw = {"floor_for": floor_for, "prior_for": prior_for, "stock": stock, "recovery": recovery, "witness": witness}
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
                print(f"[o6-rh] {name} run {n} ({side}): {rec['outcome']['end']} -- {rec['outcome']['why']}",
                      flush=True)
                if not (rec["end"]["end_run"] or {}).get("ok"):
                    record["stopped"] = f"{name} run {n}: end_run could not reach the title"
                    save()
                    return
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
