"""O2's stock REHEARSALS (research/o2_design.md section 7): the beat-table driver on STOCK Alexandria, stage by stage,
before any deploy and before the lead freezes the predictions. Each stage warps into its field at its own entrance
and scenario, drives the DRAFT's table to its own end field, and records what the freeze checklist (7.3) is read from.

    py tools/play.py studies/story-trace/o2_rehearse.py --field 115 --label o2-rh-115 --timeout 240
    set O2_STAGE=R-115a & py tools/play.py studies/story-trace/o2_rehearse.py --label o2-rh-115a --timeout 240
    py tools/play.py studies/story-trace/o2_rehearse.py --label o2-rh --timeout 240          # every stage
    py studies/story-trace/o2_alexandria.py --rehearsal-report <run dir>

WHICH STAGE: the environment variable ``O2_STAGE`` names one (R-115, R-115a, R-105, R-106, R-116, R-FULL, R-103);
else ``--field N`` picks the one stage that warps into N (115 is R-115: R-115a warps into 115 too, and is picked only
by name); else every stage but the optional R-103 runs in one launch, the cheapest run first (by the estimates below),
which puts R-115 first: its climb is freeze item F1, and if ``hold up`` does not climb, O2 stops there.

EACH RUN: New Game; the story trace armed; the raw ``warp <field> <entrance> <sc>`` (Segment.start_run); then
segment_drive.drive on the draft with the stage's end fields, the live forbidden scan on, and a recorder watching
every poll; the trace collected to ``rh_<stage>_<n>.jsonl``; the record written into ``o2_rehearsal.json``; end_run.

WHAT A STAGE MAY SETTLE (7.1): only R-FULL's traces may define or change the ladder, the chain, the writes, the noise,
the start residue or the end state. A staged run starts at another SC and entrance and writes keys the route never
writes (115 at SC 1155 writes Int16[2] := 215): it proves driver mechanics only, compared within its own stage.
"""
from __future__ import annotations

import copy
import hashlib
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

import o2_alexandria as A                                              # noqa: E402
import segment_drive as SD                                             # noqa: E402
from ff9mapkit import storytrace as T                                  # noqa: E402

ENV = "O2_STAGE"
#: The stages (research/o2_design.md 7.1): the warp, the end fields, the runs, a run budget, and a COST estimate in
#: seconds a run (the launch runs the cheapest run first; F7 replaces every number from what is measured).
STAGES = {
    "R-115": {"field": 115, "entrance": 215, "sc": 1155, "end": [116], "runs": 3, "run_s": 600, "cost_s": 120,
              "settles": "does `hold up` reach B_KEY(16)? the climb: y per burst, frames to the top (F1)"},
    "R-115a": {"field": 115, "entrance": 213, "sc": 1153, "end": [116], "runs": 2, "run_s": 900, "cost_s": 300,
               "by_name": True,
               "settles": "the whole 115 scene as the route plays it: the ladder confirm, choice 367, stage 10's "
                          "REAL control grant with Kupo in his route state, the climb (F1, F10)"},
    "R-105": {"field": 105, "entrance": 205, "sc": 1150, "end": [106], "runs": 5, "run_s": 900, "cost_s": 240,
              "settles": "Jack and the leave-now exit (F2); choices 305/310/314; e12; e11's fade race"},
    "R-106": {"field": 106, "entrance": 111, "sc": 1152, "end": [115], "runs": 2, "run_s": 600, "cost_s": 150,
              "settles": "the wait point, Puck, SC 1153, the hints, e14's fade (F3)"},
    "R-116": {"field": 116, "entrance": 0, "sc": 1155, "end": [61], "runs": 2, "run_s": 900, "cost_s": 240,
              "settles": "the three triggers, Puck's pace, the naming, the end-state read, end_run from 61 (F8, F10)"},
    "R-FULL": {"field": 100, "entrance": 102, "sc": 1000, "end": [61], "runs": 2, "run_s": 1800, "cost_s": 720,
               "movie": {"donor": 100},
               "settles": "everything in sequence, mbg101, the start residue, the end state, the total time: the "
                          "ONLY stage whose traces define predictions (F6, F9, F11)"},
    "R-103": {"field": 103, "entrance": 203, "sc": 1000, "end": [105], "runs": 2, "run_s": 900, "cost_s": 240,
              "optional": True, "settles": "a cheaper iteration on the booth, 104 and the second 103 visit"},
}
#: The NPC tracks (7.2): every published sample of these objects, in these places only (``sc_from``: from that SC).
TRACKS = [{"donor": 105, "sid": 7, "sc_from": 1152, "name": "Alleyway Jack", "lookout": [-244, 2562]},
          {"donor": 106, "sid": 2, "name": "Puck"},
          {"donor": 115, "sid": 2, "sc_from": 1155, "name": "Kupo"},
          {"donor": 116, "sid": 2, "name": "Puck"}]


def select(stages: dict, field=None, env=None) -> list:
    """The stage names a launch runs: ``O2_STAGE`` (one, by name), else the one stage warping into ``field`` (a
    ``by_name`` stage never answers a field), else every non-optional stage, the cheapest run first."""
    env = os.environ if env is None else env
    name = env.get(ENV)
    if name:
        if name not in stages:
            raise ValueError(f"{ENV}={name!r} is no stage: {sorted(stages)}")
        return [name]
    if field is not None:
        hits = [n for n, s in stages.items() if s["field"] == int(field) and not s.get("by_name")]
        if len(hits) != 1:
            raise ValueError(f"--field {field} picks {hits}: name the stage with {ENV}")
        return hits
    return sorted((n for n, s in stages.items() if not s.get("optional")), key=lambda n: (stages[n]["cost_s"], n))


def stage_pred(pred: dict, stage: dict) -> dict:
    """The draft with the stage's own start: its field (on the S side), entrance and scenario."""
    p = copy.deepcopy(pred)
    p.update(start={"S": stage["field"], "F": stage["field"]}, entrance=stage["entrance"], scenario=stage["sc"])
    return p


# ======================================================================== the recorder (the driver's observe hook)
class Recorder:
    """Everything 7.2 asks of a run that the driver's own log does not keep, from every poll the driver makes
    (``observe(st, ctx)``): the control grants, the pages, the published choices, the NPC tracks, the longest
    stretch with nothing published changing, and -- for a stage with a ``movie`` -- mbg101's arrival, first page and
    fps."""

    def __init__(self, g, stage: dict, tracks=TRACKS):
        self.g, self.stage, self.tracks = g, stage, list(tracks)
        self.grants, self.pages, self.choices = [], [], []
        self.samples: dict = {}
        self.no_progress = {"longest_s": 0.0, "where": None}
        self.movie = None if not stage.get("movie") else {"arrival_frame": None, "first_page_frame": None,
                                                           "fps_before": None, "fps_during": [], "fps_after": None}
        self._control = None
        self._page = self._choice = self._sig = None
        self._since = time.time()
        self._logged = 0                    # how much of the driver's log has been read

    def _fps(self):
        try:
            return round(self.g.rate().fps, 1)
        except Exception:                                      # noqa: BLE001 -- a record, never a failure
            return None

    def __call__(self, st, ctx: dict) -> None:
        now = time.time()
        donor, sc = ctx.get("donor"), ctx.get("sc")
        if st.control and self._control is False and st.player_x is not None:
            self.grants.append({"t": round(now, 2), "frame": st.frame, "field": st.field_id, "donor": donor, "sc": sc,
                                "x": st.player_x, "z": st.player_z, "y": st.player_y, "fps": self._fps()})
        self._control = bool(st.control)
        page = st.dialog_open and bool(st.text.strip()) and not st.control and st.choice is None   # the driver's rule
        if page and st.text != self._page:
            self.pages.append({"frame": st.frame, "field": st.field_id, "sc": sc, "text": st.text,
                               "raw_texts": list(st.raw_texts), "timed": any("[TIME=" in t for t in st.raw_texts)})
        self._page = st.text if page else None
        if st.choice is not None:
            snap = json.dumps(st.choice, sort_keys=True)
            if snap != self._choice:
                self.choices.append({"frame": st.frame, "field": st.field_id, "sc": sc, **st.choice})
            self._choice = snap
        else:
            self._choice = None
        for t in self.tracks:
            if donor != t["donor"] or (t.get("sc_from") is not None and (sc or 0) < t["sc_from"]):
                continue
            for o in st.objects or ():
                if o.get("sid") != t["sid"]:
                    continue
                d = (None if st.player_x is None
                     else round(math.hypot(o["x"] - st.player_x, o["z"] - st.player_z), 1))
                self.samples.setdefault(f"{t['donor']}.{t['sid']}", []).append(
                    {"frame": st.frame, "uid": o.get("uid"), "sid": o.get("sid"), "x": round(o["x"], 1),
                     "z": round(o["z"], 1), "moving": o.get("moving"), "r": o.get("r"), "range_r": o.get("range_r"),
                     "talk_r": o.get("talk_r"), "dist": d, "control": bool(st.control)})
        sig = (st.field_id, sc, st.ui_state, tuple(st.texts), json.dumps(st.choice, sort_keys=True), st.control,
               None if st.player_x is None else round(st.player_x / 8),
               None if st.player_z is None else round(st.player_z / 8), (st.storytrace or {}).get("rows"))
        log = ctx.get("log") or []
        stepped = any(x.get("k") == "step" for x in log[self._logged:])
        self._logged = len(log)
        if sig != self._sig or stepped:     # the driver's watchdog rule: an executor call is bounded by its own
            self._sig, self._since = sig, now   # timeouts, so a step ending is progress (segment_drive run_step)
        elif now - self._since > self.no_progress["longest_s"]:
            self.no_progress = {"longest_s": round(now - self._since, 1),
                                "where": {"field": st.field_id, "donor": donor, "sc": sc, "ui": st.ui_state,
                                          "frame": st.frame}}
        mv = self.movie
        if mv is not None and donor == self.stage["movie"]["donor"]:
            if mv["arrival_frame"] is None:
                mv["arrival_frame"], mv["fps_before"] = st.frame, self._fps()
            elif mv["first_page_frame"] is None:
                if page:
                    mv["first_page_frame"], mv["fps_after"] = st.frame, self._fps()
                    mv["frames"] = st.frame - mv["arrival_frame"]
                else:
                    fps = self._fps()
                    if fps is not None:
                        lo, hi = (mv["fps_during"] or [fps, fps])
                        mv["fps_during"] = [min(lo, fps), max(hi, fps)]


def summarise_tracks(samples: dict, tracks=TRACKS) -> dict:
    """Per track: its samples, the closest the player came against the published range_r there, the first frame it
    came within range_r of him (control held), and -- with a ``lookout`` -- the first frame it came within range_r of
    that spot (Jack's contact time, F2)."""
    out = {}
    for key, rows in samples.items():
        t = next((x for x in tracks if f"{x['donor']}.{x['sid']}" == key), {})
        near = [x for x in rows if x["dist"] is not None]
        best = min(near, key=lambda x: x["dist"]) if near else None
        within = next((x["frame"] for x in near if x["range_r"] is not None and x["control"]
                       and x["dist"] <= x["range_r"]), None)
        s = {"name": t.get("name"), "samples": len(rows), "min_dist": None if best is None else best["dist"],
             "range_r_at_min": None if best is None else best["range_r"], "first_within_range_frame": within}
        if t.get("lookout"):
            lx, lz = t["lookout"]
            s["lookout_contact_frame"] = next((x["frame"] for x in rows if x["range_r"] is not None
                                               and math.hypot(x["x"] - lx, x["z"] - lz) <= x["range_r"]), None)
        out[key] = s
    return out


def latency(grants: list, log: list) -> list:
    """For every leave_now step (F2): the control sample it acted on, the lunge's first held frame and its end, and
    the first watched sample with him moved off the grant's spot."""
    out = []
    for s in (x for x in log if x.get("k") == "step" and x.get("kind") == "leave_now"):
        g0 = next((gr for gr in reversed(grants) if gr["field"] == s["field"] and gr["frame"] <= s["frame0"]), None)
        lunge = s.get("lunge") or {}
        moved = None
        if g0 is not None:
            moved = next((w["frame"] for w in log if w.get("k") == "watch" and w.get("field") == s["field"]
                          and w["frame"] > g0["frame"] and w.get("x") is not None
                          and math.hypot(w["x"] - g0["x"], w["z"] - g0["z"]) >= 1.0), None)
        out.append({"grant_frame": None if g0 is None else g0["frame"], "step_frame0": s.get("frame0"),
                    "lunge_sample_frame": lunge.get("sample_frame"), "lunge_done_frame": lunge.get("done_frame"),
                    "first_move_frame": moved, "outcome": s.get("outcome")})
    return out


# ======================================================================== a run, a stage, a launch
def _draft_sha(pred: dict) -> str:
    return hashlib.sha256((json.dumps(pred, indent=1, sort_keys=True) + "\n").encode("utf-8")).hexdigest()


def one(g, name: str, stage: dict, pred: dict, n: int, *, t0: float, floor_for=None, prior_for=None, stock=None,
        recovery=None, tracks=TRACKS) -> dict:
    """One rehearsal run of ``stage`` (7.1 steps 1-7): its record."""
    from harness import HarnessError
    spred = stage_pred(pred, stage)
    log, progress, marks = [], {}, {}
    rec_obs = Recorder(g, stage, tracks)
    trace_name = f"rh_{name}_{n}.jsonl"
    rec = {"stage": name, "n": n, "t0": round(time.time() - t0, 1), "trace_file": trace_name}
    outcome = {"end": "void", "why": "not driven"}
    try:
        A.O2.start_run(g, "S", spred, marks)
        outcome = SD.drive(g, spred, "S", log, deadline=time.time() + float(stage["run_s"]), floor_for=floor_for,
                           prior_for=prior_for, progress=progress, end_fields=list(stage["end"]), observe=rec_obs,
                           forbid_live=True)
    except SD.RouteVoid as err:
        outcome = {"end": "void", "why": f"route: {err}", "v": err.v, "cell": err.cell, "by": err.by}
    except HarnessError as err:
        outcome = {"end": "void", "why": f"STOPPED: {str(err)[:300]}"}
    except Exception as err:                                  # noqa: BLE001 -- one run's bug must not cost the others
        outcome = {"end": "void", "why": f"STOPPED (unexpected): {type(err).__name__}: {str(err)[:300]}"}
        log.append({"k": "error", "traceback": traceback.format_exc()[-3000:]})
    rows = []
    smark = marks.get("story")
    if smark is not None:
        try:
            rec["traced"] = g.collect_story(g.run_dir / trace_name, smark)
            if (g.run_dir / trace_name).is_file():
                rows = T.read_trace(g.run_dir / trace_name)
        except (HarnessError, T.TraceError) as err:
            rec["trace_error"] = str(err)[:300]
    for k, v in progress.items():
        outcome.setdefault(k, v)
    try:
        trace = A.trace_summary(rows, spred, side="S", start_place=stage["field"], end_fields=list(stage["end"]),
                                stock=stock, log=log) if rows else {}
    except T.TraceError as err:
        trace = {"error": str(err)[:300]}
    rec.update(
        outcome={k: outcome.get(k) for k in ("end", "why", "v", "cell", "by", "t")},
        grants=rec_obs.grants,
        steps=[x for x in log if x.get("k") == "step"],
        choices=[x for x in log if x.get("k") == "choice"],
        published_choices=rec_obs.choices,
        pages=rec_obs.pages,
        evidence={"press": [x for x in log if x.get("k") == "press"],
                  "watch": [x for x in log if x.get("k") == "watch"],
                  "forbidden": [x for x in log if x.get("k") == "forbidden"]},
        tracks=rec_obs.samples,
        track_summary=summarise_tracks(rec_obs.samples, tracks),
        latency=latency(rec_obs.grants, log),
        no_progress=rec_obs.no_progress,
        mbg101=rec_obs.movie,
        end={"end_state": outcome.get("end_state"), "end_run": None},
        trace=trace,
        log_file=f"rh_{name}_{n}_log.json",
    )
    end_log: list = []
    try:
        A.O2.end_run(g, end_log, recovery=recovery)
        rec["end"]["end_run"] = {"ok": True, "title": g.state.ui_state == "Title", "how": end_log}
    except HarnessError as err:
        rec["end"]["end_run"] = {"ok": False, "why": str(err)[:300], "how": end_log}
    (g.run_dir / rec["log_file"]).write_text(json.dumps({"outcome": outcome, "log": log + end_log}, indent=1,
                                                        default=str), encoding="utf-8")
    rec["t1"] = round(time.time() - t0, 1)
    return rec


def run(g, field=None, *, stages=None, pred=None, floor_for=None, prior_for=None, stock=None, recovery=None,
        tracks=TRACKS, env=None) -> None:
    """The rehearsal launch (tools/play.py's entry; ``field`` from ``--field``). The capabilities first (P-CAP,
    P-OBJECTS, P-LANG: the same as a session's), then each selected stage's runs, the record rewritten after every
    run into ``o2_rehearsal.json``. ``stages``/``pred``/``floor_for``/``prior_for``/``stock``/``recovery``/``env``
    are seams for the fake; each defaults to the real thing."""
    stages = STAGES if stages is None else stages
    pred = A.draft_predictions() if pred is None else pred
    names = select(stages, field, env)
    t0 = time.time()
    record = {"what": "O2 stock rehearsals (research/o2_design.md 7): staged runs prove driver mechanics only; "
                      "R-FULL's traces alone may define predictions",
              "draft_sha256": _draft_sha(pred), "stages_run": names,
              "stage_defs": {n: stages[n] for n in names}, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "capabilities": [], "stages": {}}
    path = g.run_dir / A.REHEARSAL_FILE

    def save() -> None:
        path.write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
    caps = A.O2.capabilities(g)
    record["capabilities"] = [[ok, what, detail] for ok, what, detail in caps]
    for ok, what, detail in caps:
        g.check(ok, what, detail)
    save()
    if not all(ok for ok, _w, _d in caps):
        return
    for name in names:
        stage = stages[name]
        for n in range(1, int(stage["runs"]) + 1):
            g.shot_prefix = f"{name}-{n}"
            try:
                rec = one(g, name, stage, pred, n, t0=t0, floor_for=floor_for, prior_for=prior_for, stock=stock,
                          recovery=recovery, tracks=tracks)
            finally:
                g.shot_prefix = ""
            record["stages"].setdefault(name, []).append(rec)
            save()
            print(f"[o2-rh] {name} run {n}: {rec['outcome']['end']} -- {rec['outcome']['why']}", flush=True)
            if not (rec["end"]["end_run"] or {}).get("ok"):
                record["stopped"] = f"{name} run {n}: end_run could not reach the title"
                save()
                return
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
