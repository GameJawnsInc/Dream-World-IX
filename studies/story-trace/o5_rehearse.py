"""O5's REHEARSALS (research/o5_design.md section 7): the stair walk and the guarded choice on STOCK Alexandria Castle,
stage by stage, the F-side load smoke and one untraced F pass before the freeze. Each traced stage warps into 153 at
entrance 325 and SC 1190, drives the DRAFT (its stage overlay merged into a COPY and checked) to its own end fields,
and records what the freeze checklist (7.3) is read from; F-SMOKE warps into each member and its stock twin with NO
trace and records what loaded; F-PASS drives one F run through the whole route with NO trace. Nothing is deployed and
nothing is frozen here.

    py tools/play.py studies/story-trace/o5_rehearse.py --field 153 --label o5-rh-stairs --timeout 240   # R-STAIRS
    py tools/play.py studies/story-trace/o5_rehearse.py --label o5-rh --timeout 240           # the default order
    set O5_STAGE=R-FULL & py tools/play.py studies/story-trace/o5_rehearse.py --label o5-rh-full --timeout 240
    set O5_STAGE=F-SMOKE & py tools/play.py studies/story-trace/o5_rehearse.py --label o5-rh-smoke --timeout 240
    set O5_STAGE=F-PASS & py tools/play.py studies/story-trace/o5_rehearse.py --label o5-rh-fpass --timeout 240
    py studies/story-trace/o5_hallway.py --rehearsal-report <run dir>

WHICH STAGE: the environment variable ``O5_STAGE`` names one (R-STAIRS, R-FULL, R-WALK-VOID, F-SMOKE, F-PASS,
R-RACE); else ``--field 153`` picks R-STAIRS, the one stage warping into 153 that is not by-name-only; else, in one
launch: R-STAIRS (the go/no-go: the grant, the walk, the guard's race), R-FULL, and R-WALK-VOID LAST -- it stops a run
mid-walk, so a failure there ends the launch. F-SMOKE, F-PASS and R-RACE run only by name.

EACH TRACED RUN: New Game; the story trace armed; the raw ``warp 153 325 1190`` (Segment.start_run); then
segment_drive.drive on the stage's predictions with its end fields, the live forbidden scan on, the run-wide input
witness and the recorder (O4's, plus the grant's published objects and the dialog-section catch) watching every poll,
and the WALK TAP on the session's ``route_to`` -- each walk's untrimmed record (its waypoints) and every sample its own
reads kept, taken the moment it returns, while the ring still holds them; the trace collected to
``rh_<stage>_<n>.jsonl``; the record written into ``o5_rehearsal.json``; end_run, its recovery rows recorded.

R-WALK-VOID: the stage overlay ``walk_stop_x`` -700 lies on the stair step of the stage's COPY of the predictions (the
freeze refuses it anywhere else), and the WALK STOP wraps ``g.send`` on the driver's own thread: the first ``hold``
step sent while the published x is at or west of it raises "the rehearsal's stop mid-walk" BEFORE it is sent -- the
send restored at once, so end_run's warp and ladder go through, and nothing keeps sending after it. Never a timer.

F-SMOKE (NO trace): o4_rehearse.smoke on O5's pairs -- member(153) / 153 at 325, member(154) / 154 at 304,
member(151) / 151 at 110, all SC 1190 -- each id read from the chain. F-PASS (NO trace; before the freeze): New Game,
``wait_frames(30)``, the raw warp into member(153), then the drive to member(151) with the live forbidden scan off and
no end-row wait; it may only STOP the session (F14), never shape a frozen value.

WHAT A STAGE MAY SETTLE (7.1): only R-FULL's traces may define or change the keys, the start, the end state or the row
pattern. The staged runs prove mechanics and are compared within their stage. Every summary is cut at the stage's end
PLACES (o5_hallway.trace_summary).
"""
from __future__ import annotations

import copy
import json
import math
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
import o4_castle as C4                                                 # noqa: E402
import o4_rehearse as O4R                                              # noqa: E402
import o5_hallway as C5                                                # noqa: E402
import segment_drive as SD                                             # noqa: E402
from ff9mapkit import storytrace as T                                  # noqa: E402
from segment_trace import members_of, place                            # noqa: E402

ENV = "O5_STAGE"
#: 7.2: the stair's teleport point -- the first sample at (-1165, 856) within 32 u after the loss.
TELEPORT = (-1165.0, 856.0, 32.0)
#: 7.2 (the driver critique #11): a hold on the walk's last two legs is a SLIDE when it moved off the direction it
#: pressed by more than this, a STALL when it moved under this fraction of its intended travel.
SLIDE_DEG, STALL_FRAC = 20.0, 0.25
#: The stages (research/o5_design.md 7.1): the warp, the end fields (per side where they differ), the runs, a run budget
#: and a cost estimate in seconds a run (F6 replaces every number from what is measured). ``by_name``: never picked by
#: ``--field``; ``optional``: only by name; ``last``: after every other stage of a launch; ``sides``: the sides a stage
#: runs (default S); ``untraced``: no storytrace verb (F-PASS); ``overlay``: top-level keys laid over the stage's COPY
#: of the predictions (None drops one); ``walk_stop_x``: R-WALK-VOID's stop, laid on the walk step of that copy. A
#: member is named ``member(<donor>)``, never by its id: o4_rehearse.stage_ids reads it from the chain.
STAGES = {
    "R-STAIRS": {"field": 153, "entrance": 325, "sc": 1190, "end": [154], "runs": 2, "run_s": 300, "cost_s": 180,
                 "settles": "F1-F3, F8, F9, F11, F12, F15 (the go/no-go): the grant (position, frame, the frames from the "
                            "last page's going); the walk (the route, every hold's slide, push and stall on the last two "
                            "legs, the calibration); the loss sample (the last control sample, the first without, "
                            "published y) and the teleport sample; the published objects at the grant; 127's presses "
                            "and 128's timeline, the race margin to 128's readiness; 128 as published at readiness; "
                            "the landing; the branch page; the dialog-section catch; the KEYON pairs' gates and the "
                            "[TIME=20] windows under Confirm"},
    "R-FULL": {"field": 153, "entrance": 325, "sc": 1190, "end": [151], "runs": 2, "run_s": 600, "cost_s": 280,
               "by_name": True,
               "settles": "F4-F7: the 15 keys, the masked rows, O5-PATTERN's tuples (every visit's emitted sequence, the "
                          "four c rows' n and last), the four residue rows, the end cut 151 e0 t0 ip22, the end state "
                          "(Byte[8]'s read value recorded), the run time, the longest no-progress stretch -- the ONLY "
                          "stage whose traces define predictions"},
    "R-WALK-VOID": {"field": 153, "entrance": 325, "sc": 1190, "end": [154], "runs": 1, "run_s": 300, "cost_s": 60,
                    "by_name": True, "last": True, "walk_stop_x": -700,
                    "settles": "F7: the walk stopped MID-WALK (the first hold sent at a published x <= -700 raises, "
                               "never sent: V13) with no hold after the stop; end_run (the warp to 4600 from 153's "
                               "FieldHUD, the ladder) reaches the title"},
    "F-SMOKE": {"pairs": [["member(153)", 153, 325, 1190], ["member(154)", 154, 304, 1190],
                          ["member(151)", 151, 110, 1190]], "runs": 1,
                "smoke_s": 8.0, "warp_s": 60.0, "cost_s": 180, "by_name": True, "optional": True,
                "settles": "F13: each member loads at its entrance and SC (its field, FieldHUD), its published object "
                           "sids EQUAL to its stock twin's measured set after smoke_s (153@325 {7, 9, 11, 31}, 154@304 "
                           "{4}, 151@110 {4, 5, 12, 17} -- only the twin's reading is compared); 0 exceptions; end_run "
                           "ok"},
    "F-PASS": {"field": {"S": 153, "F": "member(153)"}, "entrance": 325, "sc": 1190,
               "end": {"S": [151], "F": ["member(151)"]}, "sides": ["F"], "untraced": True, "runs": 1, "run_s": 600,
               "cost_s": 280, "by_name": True, "optional": True,
               "settles": "F14 (may only STOP the session): one F run through the whole route on the DRAFT, untraced -- "
                          "reached member(151), beats stairs/choice128, no V-class, no exception through the story "
                          "machinery since the warp, stage 27's timed windows seen; its record is never evidence for any "
                          "key and never shapes a frozen value"},
    "R-RACE": {"field": 153, "entrance": 325, "sc": 1190, "end": [154], "runs": 3, "run_s": 300, "cost_s": 180,
               "by_name": True, "optional": True, "overlay": {"guard": None},
               "settles": "the unguarded race's frequency directly: a stray answer is recorded (the choice gone, path "
                          "0), never covered"},
}


def select(stages: dict, field=None, env=None) -> list:
    """The stage names a launch runs: ``O5_STAGE`` (one, by name), else the one stage warping into ``field`` that is
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


def stage_sides(stage: dict) -> list:
    """The sides a stage runs: its ``sides`` (F-PASS: F alone), else S."""
    return list(stage.get("sides") or ["S"])


def stage_pred(pred: dict, stage: dict) -> dict:
    """The draft with the stage's own start on each side, entrance and scenario, its ``overlay`` laid over a COPY (a key
    set to None is DROPPED: R-RACE's unguarded choice), R-WALK-VOID's ``walk_stop_x`` laid on the copy's WALK step
    (``walk.name``) -- the one key the freeze refuses -- and, for an untraced stage, no end-row wait (``end_row_s``
    None: no trace to wait on). Then checked as the driver will read it: segment_drive.guard_of, witness_of and step_of
    on every table step, so a bad overlay refuses before anything is driven. The predictions given are never changed."""
    p = copy.deepcopy(pred)
    p.update(start={"S": O4R.stage_start(stage, "S"), "F": O4R.stage_start(stage, "F")}, entrance=stage["entrance"],
             scenario=stage["sc"])
    for k, v in (stage.get("overlay") or {}).items():
        if v is None:
            p.pop(k, None)
        else:
            p[k] = copy.deepcopy(v)
    if stage.get("walk_stop_x") is not None:
        name = (p.get("walk") or {}).get("name")
        steps = [s for c in p.get("table") or () for s in c["steps"] if s.get("name") == name]
        if len(steps) != 1:
            raise ValueError(f"walk_stop_x: {len(steps)} table step(s) named {name!r}, not the one walk")
        steps[0]["walk_stop_x"] = float(stage["walk_stop_x"])
    if stage.get("untraced"):
        p["budget"] = dict(p.get("budget") or {}, end_row_s=None)
    SD.guard_of(p)
    SD.witness_of(p)
    for c in p.get("table") or ():
        for s in c["steps"]:
            SD.step_of(p, s)
    return p


# ======================================================================== the run's own instruments
class Recorder(O4R.Recorder):
    """O4's recorder (O2's grants, pages, published choices and no-progress stretch; each page's texts and the frame
    it went), plus what 7.2 reads that it does not keep: the published objects at each grant (sid, uid, position,
    ``shown``, ``coll``, ``solid``, ``r``, ``talk_r``, ``range_r``); THE DIALOG-SECTION CATCH (0.2 #18) -- every
    sample with no dialog section while the menu group is ``Dialog.Choice``, and every sample listing a marker page
    again after one without it -- with the samples read, so its rate can be judged; and the TELEPORT the driver's own
    polls saw -- the first sample in the walk's place, control off, within :data:`TELEPORT` (the walk tap keeps only
    route_to's own reads, which can end before the stair's cut moves him)."""

    def __init__(self, g, stage: dict, pred: dict):
        super().__init__(g, stage, tracks=())
        self.markers = list((pred.get("guard") or {}).get("markers") or ())
        self.walk_place = (pred.get("walk") or {}).get("donor")
        self.catch: list = []
        self.samples_read = 0
        self.teleport = None
        self._marker = None                 # None: no marker page seen yet; True: listed now; False: gone since

    def __call__(self, st, ctx: dict) -> None:
        n = len(self.grants)
        super().__call__(st, ctx)
        if len(self.grants) > n:
            self.grants[-1]["objects"] = [{k: o.get(k) for k in ("sid", "uid", "x", "z", "shown", "coll", "solid", "r",
                                                                  "talk_r", "range_r")} for o in st.objects or ()]
        tx, tz, tr = TELEPORT
        if (self.teleport is None and not st.control and st.player_x is not None and st.player_z is not None
                and ctx.get("donor") == self.walk_place and math.hypot(st.player_x - tx, st.player_z - tz) <= tr):
            self.teleport = {"frame": st.frame, "field": st.field_id, "x": round(st.player_x, 1),
                             "z": round(st.player_z, 1)}
        self.samples_read += 1
        if "dialog" not in st.raw and st.menu_group == "Dialog.Choice":
            self.catch.append({"frame": st.frame, "field": st.field_id, "kind": "no dialog section, group "
                                                                                "Dialog.Choice"})
        listed = any(m in st.text for m in self.markers) if self.markers else False
        if listed and self._marker is False:
            self.catch.append({"frame": st.frame, "field": st.field_id, "kind": "a marker page listed again"})
        if listed:
            self._marker = True
        elif self._marker:
            self._marker = False


def _raw_sample(raw: dict) -> dict:
    p = raw.get("player") or {}
    return {"frame": int(raw.get("frame", -1)), "field": (raw.get("field") or {}).get("id"),
            "control": bool(p.get("control", False)), "x": p.get("x"), "y": p.get("y"), "z": p.get("z")}


class WalkTap:
    """THE WALK TAP (7.2): the session's ``route_to`` wrapped on the instance -- each call's untrimmed record (its
    ``waypoints``) and every sample its own reads kept (``g.states_since``), taken the moment it returns, while the
    ring still holds them. :meth:`restore` puts the session's own back."""

    def __init__(self, g):
        self.g, self.walks = g, []
        self._had = "route_to" in vars(g)
        self._orig = vars(g).get("route_to")
        self._real = g.route_to
        g.route_to = self._route_to

    def _route_to(self, *a, **k):
        g = self.g
        st = g.state
        t0, rec = time.time(), None
        try:
            rec = self._real(*a, **k)
            return rec
        finally:
            try:
                raws = g.states_since(st.frame - 1)
            except Exception:                                  # noqa: BLE001 -- a record, never the run
                raws = []
            self.walks.append({"t0": t0, "t1": time.time(), "frame0": st.frame, "field": st.field_id,
                               "start": [st.player_x, st.player_z], "goal": [float(v) for v in a[:2]],
                               "waypoints": [[float(v) for v in p[:2]] for p in (rec or {}).get("waypoints") or ()],
                               "pushes": (rec or {}).get("pushes"), "pushed": (rec or {}).get("pushed"),
                               "samples": [_raw_sample(r) for r in raws]})

    def restore(self) -> None:
        if self._had:
            self.g.route_to = self._orig
        else:
            vars(self.g).pop("route_to", None)


class WalkStop:
    """R-WALK-VOID's STOP (7.1, F7): ``g.send`` wrapped on the driver's own thread -- the first request holding a
    ``hold`` step sent while the published x stands at or west of ``x_stop`` in ``field`` raises "the rehearsal's stop
    mid-walk" BEFORE it is sent, the session's own send restored at once (end_run's warp and ladder go through it;
    nothing keeps sending after the raise). ``fired``: the stop's frame, position, wall time and the steps it held
    back. Never a timer: a timer expires in route_to's settle, its rate wait or its calibration, never on the stair."""

    def __init__(self, g, x_stop: float, field: int):
        from harness import HarnessError
        self.g, self.x_stop, self.field = g, float(x_stop), int(field)
        self.fired = None
        self._had = "send" in vars(g)
        self._orig = vars(g).get("send")
        real = g.send

        def send(*steps, **kw):
            if self.fired is None and any(str(s).startswith("hold ") for s in steps):
                st = g.state
                if st.field_id == self.field and st.player_x is not None and st.player_x <= self.x_stop:
                    self.fired = {"t": time.time(), "frame": st.frame, "x": round(st.player_x, 1),
                                  "z": None if st.player_z is None else round(st.player_z, 1), "steps": list(steps)}
                    self.restore()
                    raise HarnessError(f"the rehearsal's stop mid-walk: a hold at x {st.player_x:.0f} (<= walk_stop_x "
                                       f"{self.x_stop:g}) in {self.field}, never sent")
            return real(*steps, **kw)
        g.send = send

    def restore(self) -> None:
        if self._had:
            self.g.send = self._orig
        else:
            vars(self.g).pop("send", None)


# ======================================================================== the records (pure, but for the rate)
def _rate(g) -> tuple:
    """``(fps, tick_hz)`` measured on the launch now, or ``(None, 30.0)``."""
    try:
        r = g.rate()
        return (round(float(r.fps), 2) if r.fps else None), float(getattr(r, "tick_hz", 30.0) or 30.0)
    except Exception:                                          # noqa: BLE001 -- a record, never the run
        return None, 30.0


def _ticks(frames, fps, tick_hz=30.0):
    return None if frames is None or not fps else round(frames * tick_hz / fps, 1)


def _secs(frames, fps):
    return None if frames is None or not fps else round(frames / fps, 2)


def _steps_rows(g) -> list:
    """The session's steps.jsonl rows (every request: its steps, wall time, ack frame), or none."""
    path = Path(g.run_dir) / "steps.jsonl"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            row = json.loads(ln)
        except ValueError:
            continue
        if row.get("kind") == "step":
            out.append(row)
    return out


def _holds(row: dict) -> list:
    return [str(s).split() for s in row.get("steps") or () if str(s).startswith("hold ")]


_BUTTON_AXIS = {"up": ("v", 1.0), "down": ("v", -1.0), "right": ("h", 1.0), "left": ("h", -1.0)}


def pressed_dir(basis: dict | None, holds: list):
    """The world direction a request's ``hold`` steps press through the calibrated ``basis`` ({"v": up, "h": right}),
    unit, or None (no basis, no direction button)."""
    if not basis:
        return None
    dx = dz = 0.0
    for parts in holds:
        ax = _BUTTON_AXIS.get(parts[1] if len(parts) > 1 else "")
        if ax is None or basis.get(ax[0]) is None:
            continue
        v = basis[ax[0]]
        dx, dz = dx + ax[1] * float(v[0]), dz + ax[1] * float(v[1])
    n = math.hypot(dx, dz)
    return None if n == 0 else (dx / n, dz / n)


def _angle(a, b) -> float | None:
    if a is None or b is None:
        return None
    na, nb = math.hypot(*a), math.hypot(*b)
    if na == 0 or nb == 0:
        return None
    c = max(-1.0, min(1.0, (a[0] * b[0] + a[1] * b[1]) / (na * nb)))
    return round(math.degrees(math.acos(c)), 1)


def _seg_dist(p, a, b) -> float:
    ax, az, bx, bz = a[0], a[1], b[0], b[1]
    dx, dz = bx - ax, bz - az
    L = dx * dx + dz * dz
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - az) * dz) / L))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (az + t * dz))


def _at(samples: list, frame) -> dict | None:
    """The last sample at or before ``frame`` with a position (the walk's own reads)."""
    best = None
    for s in samples:
        if s["frame"] <= frame and s.get("x") is not None:
            best = s
    return best


def hold_rows(walk: dict, steps: list, basis: dict | None) -> list:
    """7.2's per-hold reading of one walk (the driver critique #11): every request of the walk's wall-time span that
    holds a direction -- its seq, steps and ack frame; where he stood at the previous hold's ack (or the walk's start)
    and at its own, from the walk's own samples; how far he moved and the heading; the LEG it pressed on (the planned
    route ``[start] + waypoints``, the leg nearest where it began) and how far the move strayed from that leg's
    heading (``off_leg``, quantized by the 8-way pad, reported) and from the direction its buttons PRESS through the
    calibrated basis (``off_pressed``); SLIDE when ``off_pressed`` > :data:`SLIDE_DEG`, STALL when it moved under
    :data:`STALL_FRAC` of its intended travel (its frames x the walk's fastest hold per frame). A hold during which
    control went (a sample of its span without it: the trigger took him mid-hold) is ``control_lost`` -- neither."""
    samples = walk.get("samples") or []
    pts = [tuple(walk["start"])] if None not in (walk.get("start") or [None]) else []
    pts += [tuple(p) for p in walk.get("waypoints") or ()]
    legs = list(zip(pts, pts[1:]))
    rows, prev = [], walk.get("frame0")
    for r in steps:
        if not (walk["t0"] <= float(r.get("t", 0)) <= walk["t1"]) or not _holds(r) or r.get("frame") is None:
            continue
        if not any(len(h) > 1 and h[1] in _BUTTON_AXIS for h in _holds(r)):
            continue                                    # a run button alone, a reset: no direction to judge
        a, b = _at(samples, prev), _at(samples, r["frame"])
        frames = max((int(h[2]) for h in _holds(r) if len(h) > 2 and h[2].lstrip("-").isdigit()), default=None)
        lost = any(not s["control"] for s in samples if (prev or -1) < s["frame"] <= r["frame"])
        out = {"seq": r.get("seq"), "steps": r.get("steps"), "ack_frame": r["frame"], "frames": frames,
               "from": None if a is None else [a["x"], a["z"]], "to": None if b is None else [b["x"], b["z"]],
               "moved": None, "leg": None, "off_leg": None, "off_pressed": None, "control_lost": lost}
        if a is not None and b is not None:
            mv = (b["x"] - a["x"], b["z"] - a["z"])
            out["moved"] = round(math.hypot(*mv), 1)
            if legs:
                k = min(range(len(legs)), key=lambda i: _seg_dist((a["x"], a["z"]), *legs[i]))
                out["leg"] = k + 1
                la, lb = legs[k]
                out["off_leg"] = _angle(mv, (lb[0] - la[0], lb[1] - la[1]))
            out["off_pressed"] = _angle(mv, pressed_dir(basis, _holds(r)))
        rows.append(out)
        prev = r["frame"]
    speeds = [x["moved"] / x["frames"] for x in rows if x["moved"] and x["frames"] and not x["control_lost"]]
    top = max(speeds) if speeds else None
    for x in rows:
        judged = not x["control_lost"]
        x["slide"] = bool(judged and x["off_pressed"] is not None and x["moved"] and x["off_pressed"] > SLIDE_DEG)
        x["stall"] = bool(judged and top is not None and x["frames"] is not None and x["moved"] is not None
                          and x["moved"] < STALL_FRAC * top * x["frames"])
    return rows


def walk_record(walks: list, log: list, pred: dict, rec_obs, *, basis=None, steps=(), fps=None, tick_hz=30.0) -> dict:
    """7.2's walk record: the grant (the last control grant before the walk: its frame and position, the frames from
    the last page's going to it, the published objects there); the stair step's rows WHOLE; per attempt its walk (the
    tap's), the planned route, every hold (:func:`hold_rows`) with the last two legs' slides, stalls and the walk's
    pushes; the last control sample and the first without (their published y); the teleport sample (the first at
    :data:`TELEPORT` after the loss) and its ticks after it; and the calibration basis."""
    steps_rows = C5.walk_rows(log, pred)
    w = pred.get("walk") or {}
    out = {"name": w.get("name"), "step_rows": steps_rows, "attempts": [], "grant": None,
           "calibration": None if basis is None else {k: basis.get(k) for k in ("v", "h")}}
    f0 = steps_rows[0].get("frame0") if steps_rows else None
    grants = [x for x in rec_obs.grants if f0 is None or x["frame"] <= f0]
    if grants:
        gr = grants[-1]
        before = [p for p in rec_obs.pages if p["frame"] <= gr["frame"]]
        gone = before[-1].get("gone_frame") if before else None
        out["grant"] = {**{k: gr.get(k) for k in ("frame", "field", "x", "z", "y", "objects")},
                        "from_last_page_frames": None if gone is None else gr["frame"] - gone,
                        "last_page": before[-1]["text"][:80] if before else None}
    for s in steps_rows:
        walk = next((x for x in walks if x["field"] == s.get("field") and s.get("frame0") is not None
                     and x["frame0"] >= s["frame0"] - 2 and x["frame0"] <= (s.get("frame") or x["frame0"])), None)
        att = {"attempt": s.get("attempt"), "outcome": s.get("outcome"), "lost": s.get("lost"), "door": s.get("door"),
               "landed": s.get("landed"), "walk": None}
        if walk is not None:
            holds = hold_rows(walk, list(steps), basis)
            n = len(walk.get("waypoints") or ())
            last2 = [h for h in holds if h["leg"] is not None and h["leg"] >= n - 1]
            samples = walk.get("samples") or []
            last_c = None
            for x in samples:
                if x["control"]:
                    last_c = x
                elif last_c is not None:
                    break
            first_without = next((x for x in samples if last_c is not None and x["frame"] > last_c["frame"]
                                  and not x["control"]), None)
            tx, tz, tr = TELEPORT
            loss = (s.get("lost") or {}).get("frame")
            tele = next(({**x, "source": "the walk's samples"} for x in samples if loss is not None
                         and x["frame"] > loss and x.get("x") is not None and math.hypot(x["x"] - tx, x["z"] - tz) <= tr),
                        None)
            seen = getattr(rec_obs, "teleport", None)
            if tele is None and seen is not None and loss is not None and seen["frame"] > loss:
                tele = {**seen, "source": "the driver's polls"}
            att["walk"] = {"goal": walk.get("goal"), "start": walk.get("start"), "waypoints": walk.get("waypoints"),
                           "legs": n, "holds": holds, "pushes": walk.get("pushes"), "pushed": walk.get("pushed"),
                           "last_two_legs": {"holds": len(last2), "slides": sum(1 for h in last2 if h["slide"]),
                                             "stalls": sum(1 for h in last2 if h["stall"]),
                                             "pushes": walk.get("pushes")},
                           "last_control": last_c, "first_without": first_without,
                           "teleport": None if tele is None else {**tele, "ticks_after_loss":
                                                                  _ticks(tele["frame"] - loss, fps, tick_hz)},
                           "samples": len(samples)}
        out["attempts"].append(att)
    return out


def guard_record(log: list, pred: dict, rec_obs, *, fps=None, tick_hz=30.0) -> dict:
    """7.2's guard record: the marker page (127) as the recorder saw it -- first seen, gone -- and its presses (the
    driver's ``press`` rows holding a marker: decision, accepted, down and ack frames); the guard row whole (armed,
    the quiet window's open frame and re-arms, ``marker_last``, the choice's first/ready/close, the answer's span,
    ``closing_seq``, ``strays``, the branch page, the verdict); 128 as published -- its first publication, the choice
    row at readiness, and whether its options or active lines changed after it (``[IMME]``: they must not); the
    guarded rule's choice rows and ``choose_landed``'s presses; THE RACE MARGIN, 127's last listed sample to 128's
    readiness, in frames, ticks and seconds at the launch's rate."""
    marks = list((pred.get("guard") or {}).get("markers") or ())
    pages = [p for p in rec_obs.pages if any(m in p["text"] for m in marks)]
    gr = [x for x in log if x.get("k") == "guard"]
    g = gr[0] if gr else None
    acks = {x.get("seq"): x.get("ack_frame") for x in log if x.get("k") == "press"}
    if g is not None:                                   # the guard row's own: each press placed by its accepted event
        presses = [{**{k: p.get(k) for k in ("seq", "decision_frame", "accepted_frame", "down_frame")},
                    "ack_frame": acks.get(p.get("seq"))} for p in g.get("presses") or () if p.get("marker")]
    else:                                               # no guard row (an unguarded stage): the log's marker presses
        presses = [{"seq": x.get("seq"), "decision_frame": (x.get("pre") or {}).get("frame"), "accepted_frame": None,
                    "down_frame": None, "ack_frame": x.get("ack_frame")} for x in log
                   if x.get("k") == "press" and x.get("why") == "page"
                   and (x.get("marker") or any(m in t for t in (x.get("raws") or ()) for m in marks))]
    rows = C5.choice_rows(log, pred)
    ch = rows[0] if rows else None
    rule = next((r for r in pred.get("choices") or () if r.get("match") == (pred.get("guard") or {}).get("choice")),
                {})
    pubs = [c for c in rec_obs.choices if any(rule.get("match", "\0") in str(o) for o in c.get("options") or ())]
    changed = None
    if ch is not None:
        later = [c for c in pubs if c["frame"] > ch["frame"]]
        changed = any((c.get("options"), c.get("active")) != (ch.get("options"), ch.get("active")) for c in later)
    margin = None
    if g is not None and g.get("choice_ready") is not None and g.get("marker_last") is not None:
        f = g["choice_ready"] - g["marker_last"]
        margin = {"frames": f, "ticks": _ticks(f, fps, tick_hz), "s": _secs(f, fps)}
    return {"marker_pages": [{k: p.get(k) for k in ("frame", "gone_frame", "text")} for p in pages],
            "marker_presses": presses, "guard": g, "guard_rows": len(gr), "choice": ch, "choice_rows": len(rows),
            "published": {"first_frame": pubs[0]["frame"] if pubs else None, "snapshots": len(pubs),
                          "changed_after_ready": changed},
            "choose": [x for x in log if x.get("k") == "press" and x.get("why") == "choose"],
            "race_margin": margin}


def _shows(press: dict, texts, raws) -> bool:
    """Whether a page press was decided on a window of ``texts`` (rendered) / ``raws`` (phrase_raw): the press row's
    own ``texts`` or ``raws`` (the O5 drive rows its presses with their phrase_raw)."""
    return bool(set(press.get("texts") or ()) & set(texts) or set(press.get("raws") or ()) & set(raws))


def windows_record(pages: list, log: list, *, fps=None, tick_hz=30.0) -> dict:
    """7.2's KEYON pairs and timed windows, as the recorder saw them: each pair (consecutive pages of ``[TIME=-1]``
    windows, no ``[DBTN=``) -- its windows, first seen, both seen, gone, its life in seconds and the page Confirms
    decided on one of its windows; each timed window (a ``[TIME=n]`` page, n > 0: 137 and 140 in 153) -- first seen,
    gone, its life in ticks, the Confirms decided while it was listed."""
    presses = [p for p in log if p.get("k") == "press" and p.get("why") == "page"]
    groups, cur = [], []
    for pg in pages:
        raws = pg.get("raw_texts") or []
        if raws and all(O4R._pair_window(x) for x in raws):
            cur.append(pg)
            continue
        if cur:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    pairs = []
    for grp in groups:
        texts, raws = [], []
        for pg in grp:
            texts += [t for t in pg.get("texts") or () if t not in texts]
            raws += [t for t in pg.get("raw_texts") or () if t not in raws]
        second = next((pg["frame"] for pg in grp if len(pg.get("raw_texts") or ()) >= 2), None)
        gone = grp[-1].get("gone_frame")
        hit = [p for p in presses if _shows(p, texts, raws)]
        pairs.append({"texts": texts, "first_frame": grp[0]["frame"], "second_frame": second, "gone_frame": gone,
                      "s": None if gone is None else _secs(gone - grp[0]["frame"], fps),
                      "s_after_second": None if gone is None or second is None else _secs(gone - second, fps),
                      "presses": len(hit), "seqs": [p.get("seq") for p in hit]})
    timed, seen = [], {}
    for pg in pages:                                    # one per WINDOW: a page that adds a pair keeps it listed
        for x in pg.get("raw_texts") or ():
            if "[TIME=" not in x or "[TIME=-1]" in x:
                continue
            if x in seen:
                seen[x]["gone_frame"] = pg.get("gone_frame")
            else:
                seen[x] = {"text": x, "frame": pg["frame"], "gone_frame": pg.get("gone_frame")}
                timed.append(seen[x])
    for t in timed:
        lo, hi = t["frame"], t["gone_frame"]
        hit = [p for p in presses if _shows(p, (), [t["text"]])
               and lo <= ((p.get("pre") or {}).get("frame") or -1) < (hi if hi is not None else 1 << 62)]
        t.update(ticks=None if hi is None else _ticks(hi - lo, fps, tick_hz), presses=len(hit))
    return {"pairs": pairs, "timed": timed}


def _holds_between(steps: list, t0: float, t1: float) -> list:
    """The direction holds requested in (``t0``, ``t1``): steps.jsonl rows holding a ``hold`` of a direction."""
    return [r for r in steps if t0 < float(r.get("t", 0)) < t1
            and any(len(h) > 1 and h[1] in _BUTTON_AXIS for h in _holds(r))]


# ======================================================================== a run, an untraced start, a launch
def fpass_start(g, side: str, spred: dict) -> None:
    """F-PASS's UNTRACED start (7.1): New Game, ``wait_frames(30)``, the raw warp into the side's start at the stage's
    entrance and SC, the wait for the field -- Segment.start_run without the ``storytrace`` verb."""
    g.newgame()
    g.wait_frames(30)
    start = spred["start"][side]
    g._check_field_id(start, "warp", True)
    g.send(f"warp {start} {spred['entrance']} {spred.get('scenario', -1)}")
    g.wait_for(lambda s: s.field_id == start, timeout=60.0, what=f"field {start} to load")


def one(g, name: str, stage: dict, pred: dict, n: int, *, side: str = "S", t0: float, floor_for=None,
        prior_for=None, stock=None, recovery=None, witness=None) -> dict:
    """One rehearsal run of ``stage`` on ``side`` (7.1): its record (7.2) -- O4's sections (the outcome, the beats, the
    grants, the choice rows and the published choices, the pages and the transcript, the press, forbidden, observed and
    input evidence, the longest no-progress stretch, the end state, end_run's rows) plus THE WALK (:func:`walk_record`),
    THE GUARD (:func:`guard_record`: the race margin in ticks and seconds at the launch's rate), the KEYON pairs and the
    timed windows (:func:`windows_record`), the dialog-section catch and its rate, the launch's measured rate, and the
    trace through O5's summary cut at the stage's end PLACES. An untraced stage (F-PASS) starts by :func:`fpass_start`,
    drives with the live forbidden scan off (``forbid_live`` False in the record) and records the exceptions and
    Memoria.log lines since the warp instead of a trace. R-WALK-VOID's :class:`WalkStop` records its stop, the direction
    holds the run requested before it (the walk had begun: at least one) and after it, before end_run (there must be
    none). A run the instrument stopped (a HarnessError: outside input, the budget, a refused
    press, the walk stop; or an unexpected exception) records the class V13 (driver). ``witness`` (the outside-input
    witness; default the ctypes one) is a seam for the fake."""
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
    tap = WalkTap(g)
    stop = WalkStop(g, stage["walk_stop_x"], start) if stage.get("walk_stop_x") is not None else None
    try:
        try:
            if traced:
                C5.O5.start_run(g, side, spred, marks)
            else:
                fpass_start(g, side, spred)
            outcome = SD.drive(g, spred, side, log, deadline=time.time() + float(stage["run_s"]), floor_for=floor_for,
                               prior_for=prior_for, progress=progress, end_fields=list(ends), observe=rec_obs,
                               forbid_live=traced, witness=witness if witness is not None else C4.input_witness(g))
        except SD.RouteVoid as err:
            outcome = {"end": "void", "why": f"route: {err}", "v": err.v, "cell": err.cell, "by": err.by}
        except HarnessError as err:                           # the instrument's: V13, as the session reads a STOPPED
            outcome = {"end": "void", "why": f"STOPPED: {str(err)[:300]}", "v": "V13", "by": "driver"}
        except Exception as err:                              # noqa: BLE001 -- one run's bug must not cost the others
            outcome = {"end": "void", "why": f"STOPPED (unexpected): {type(err).__name__}: {str(err)[:300]}",
                       "v": "V13", "by": "driver"}
            log.append({"k": "error", "traceback": traceback.format_exc()[-3000:]})
    finally:
        tap.restore()
        if stop is not None:
            stop.restore()
    t_drive = time.time()
    fps, tick_hz = _rate(g)
    basis = getattr(g, "_axes", {}).get(start) if hasattr(g, "_axes") else None
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
        trace = C5.trace_summary(rows, spred, side=side, start_place=place(start, members), end_fields=list(ends),
                                 stock=stock, log=log) if rows else {}
    except T.TraceError as err:
        trace = {"error": str(err)[:300]}
    steps = _steps_rows(g)
    pages = rec_obs.pages
    rec.update(
        outcome={k: outcome.get(k) for k in ("end", "why", "v", "cell", "by", "t")},
        beats=outcome.get("beats"),
        rate={"fps": fps, "tick_hz": tick_hz},
        grants=rec_obs.grants,
        walk=walk_record(tap.walks, log, spred, rec_obs, basis=basis, steps=steps, fps=fps, tick_hz=tick_hz),
        guard=guard_record(log, spred, rec_obs, fps=fps, tick_hz=tick_hz),
        windows=windows_record(pages, log, fps=fps, tick_hz=tick_hz),
        catch={"samples": rec_obs.samples_read, "caught": rec_obs.catch},
        choices=[x for x in log if x.get("k") == "choice"],
        published_choices=rec_obs.choices,
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
        rec["walk_stop"] = (None if stop.fired is None else
                            {**stop.fired, "x_stop": stop.x_stop,
                             "holds_before": len(_holds_between(steps, t_run, stop.fired["t"])),
                             "holds_after": len(_holds_between(steps, stop.fired["t"], t_drive))})
    end_log: list = []
    try:
        C5.O5.end_run(g, end_log, recovery=recovery)
        rec["end"]["end_run"] = {"ok": True, "title": g.state.ui_state == "Title", "how": end_log}
    except HarnessError as err:
        rec["end"]["end_run"] = {"ok": False, "why": str(err)[:300], "how": end_log}
    (g.run_dir / rec["log_file"]).write_text(json.dumps({"outcome": outcome, "log": log + end_log}, indent=1,
                                                        default=str), encoding="utf-8")
    rec["t1"] = round(time.time() - t0, 1)
    return rec


def run(g, field=None, *, stages=None, pred=None, floor_for=None, prior_for=None, stock=None, recovery=None,
        env=None, witness=None, pads=..., engine=None, live_engine=None) -> None:
    """The rehearsal launch (tools/play.py's entry; ``field`` from ``--field``). Before anything, each selected stage
    takes its ids from the chain (o4_rehearse.stage_ids: ``member(N)`` resolved, every F-side id checked) and its
    predictions are built and checked (:func:`stage_pred`) -- a refusal raises here, the session untouched; the record
    keeps the resolved stages. The capabilities first (P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG over 151/153/154, P-LAUNCH
    with the engine, P-PAD), the launch's own readings (the settings, P-SETTINGS, P-OVERRIDE, P-ENGINE), then each
    selected stage -- its runs on its sides, or its smoke -- the record rewritten after every run into
    ``o5_rehearsal.json``. A run whose end_run cannot reach the title stops the launch. Every keyword is a seam for the
    fake; each defaults to the real thing."""
    stages = STAGES if stages is None else stages
    pred = C5.O5.draft() if pred is None else pred
    names = select(stages, field, env)
    stages = {n: O4R.stage_ids(stages[n], pred, name=n) for n in names}     # the chain's ids, or a refusal, first
    for n in names:
        if not stages[n].get("pairs"):
            stage_pred(pred, stages[n])                                     # a bad overlay refuses before the session
    t0 = time.time()
    record = {"what": "O5 rehearsals (research/o5_design.md 7): staged runs prove driver mechanics only; R-FULL's "
                      "traces alone may define predictions; F-SMOKE loads the members, untraced; F-PASS drives one F "
                      "run untraced and may only stop the session",
              "draft_sha256": O2R._draft_sha(pred), "stages_run": names,
              "stage_defs": {n: stages[n] for n in names}, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "capabilities": [], "launch": {}, "stages": {}, "twins": {}}
    path = g.run_dir / C5.REHEARSAL_FILE

    def save() -> None:
        path.write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
    caps = C5.O5.capabilities(g, pads=pads, engine=engine, live_engine=live_engine)
    record["capabilities"] = [[ok, what, detail] for ok, what, detail in caps]
    for ok, what, detail in caps:
        g.check(ok, what, detail)
    launch = O4R.launch_readings(g, pred, engine=engine, live_engine=live_engine)
    record["launch"] = launch
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
                print(f"[o5-rh] {name} run {n} ({side}): {rec['outcome']['end']} -- {rec['outcome']['why']}",
                      flush=True)
                if not (rec["end"]["end_run"] or {}).get("ok"):
                    record["stopped"] = f"{name} run {n}: end_run could not reach the title"
                    save()
                    return
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
