"""O3's REHEARSALS (research/o3_design.md section 7): the beat-table driver on STOCK Prima Vista, stage by stage, and
the F-side load smoke, before the lead freezes the predictions. Each traced stage warps into its field at entrance 0
and SC 1155, drives the DRAFT (its ``battle_override`` applied and checked) to its own end field, and records what
the freeze checklist (7.3) is read from; F-SMOKE warps into each member and its stock twin with NO trace and records
what loaded. Nothing is deployed and nothing is frozen here.

    set O3_STAGE=R-START & py tools/play.py studies/story-trace/o3_rehearse.py --label o3-rh-start --timeout 240
    py tools/play.py studies/story-trace/o3_rehearse.py --field 62 --label o3-rh-62 --timeout 240
    py tools/play.py studies/story-trace/o3_rehearse.py --label o3-rh --timeout 240           # the default order
    py studies/story-trace/o3_prima_vista.py --rehearsal-report <run dir>

WHICH STAGE: the environment variable ``O3_STAGE`` names one (R-START, F-SMOKE, R-62, R-FULL, R-SKIP,
R-BATTLE-VOID); else ``--field N`` picks the one stage that warps into N and is not by-name-only (61 is R-START, 62 is
R-62); else, in one launch: R-START (the go/no-go: FMV003 after the warp has cut FMV001), F-SMOKE, R-62, R-FULL, and
R-BATTLE-VOID LAST -- a failure there ends the launch, since the next run would start from an unknown state. R-SKIP
runs only by name.

EACH TRACED RUN: New Game; the story trace armed; the raw ``warp <field> 0 1155`` (Segment.start_run); then
segment_drive.drive on the draft with the stage's end fields, the live forbidden scan on, and o2_rehearse's Recorder
(no NPC track) watching every poll -- R-SKIP's wrapped to press Confirm once, ``skip_after_s`` into the movie; the
trace collected to ``rh_<stage>_<n>.jsonl``; the record written into ``o3_rehearsal.json``; end_run, its recovery
rows recorded.

F-SMOKE (NO trace -- no ``storytrace`` verb is ever sent, so no fork data exists before the freeze): per warp,
start_run's RAW warp -- New Game, ``wait_frames(30)``, the field's registration checked, the raw ``warp <id> 0 1155``,
then a wait for the field and FieldHUD; never Session.warp(), whose wait for control 61-63 never grant would hang 60 s
a warp -- then ``smoke_s`` of Main_Init, the published object sids, the exceptions and the Memoria.log warnings and
errors since the warp, and end_run. The members first, then their stock twins; each member's sids against its twin's.

WHAT A STAGE MAY SETTLE (7.1): only R-FULL's traces may define or change the writes, the chain, the noise, the start
or the end state. A staged run starts mid-route: it proves driver mechanics only, compared within its own stage.
"""
from __future__ import annotations

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
import o3_prima_vista as P                                             # noqa: E402
import segment_drive as SD                                             # noqa: E402
import segment_trace as ST                                             # noqa: E402
from ff9mapkit import storytrace as T                                  # noqa: E402

ENV = "O3_STAGE"
#: The stages (research/o3_design.md 7.1): the warp, the end fields, the runs, a run budget and a cost estimate in
#: seconds a run (F9 replaces every number from what is measured). ``by_name``: never picked by ``--field``;
#: ``optional``: only by name; ``last``: after every other stage of a launch.
STAGES = {
    "R-START": {"field": 61, "entrance": 0, "sc": 1155, "end": [62], "runs": 2, "run_s": 600, "cost_s": 150,
                "movie": {"donor": 61},
                "settles": "F1, F7: FMV003 plays after the warp has cut FMV001 (type 0 into type 0, never measured); "
                           "no skip dialog; arrival -> page 72 (frames, seconds); the start rows -- the residue, 61 "
                           "ip22, ip119 old 1 (the first measurement of the incoming Byte[13] IN 61). The "
                           "InitMovieHitPoint warning is no signal (0.2 #20)"},
    "F-SMOKE": {"pairs": [[31211, 61], [31212, 62], [31213, 63]], "entrance": 0, "sc": 1155, "runs": 1,
                "smoke_s": 8.0, "warp_s": 60.0, "cost_s": 150, "by_name": True,
                "settles": "F5: each member loads at entrance 0 SC 1155 (its field, FieldHUD) and its Main_Init runs "
                           "-- its published object sids equal its stock twin's; 0 exceptions through EventEngine, "
                           "EBin or HarnessAgent; end_run from mid-movie, mid-play, mid-scene"},
    "R-62": {"field": 62, "entrance": 0, "sc": 1155, "end": [64], "runs": 2, "run_s": 900, "cost_s": 240,
             "settles": "F2, F8: the battle beat (the registry matched on the published scene, the epoch, the result "
                        "fight() returned, turns, seconds, tutorials 0, the leave's presses, the flip and its result, "
                        "the landing in 63 and its latency), the cmd-37 landing on STOCK under the trace (63 e0 t0 "
                        "ip22 the first field row after 62 ip1285), 63's pages, end_run from 64"},
    "R-FULL": {"field": 61, "entrance": 0, "sc": 1155, "end": [64], "runs": 2, "run_s": 1200, "cost_s": 360,
               "by_name": True, "movie": {"donor": 61},
               "settles": "everything in sequence; the ONLY stage whose traces define predictions (F6, F7, F11); the "
                          "total time (F9)"},
    "R-SKIP": {"field": 61, "entrance": 0, "sc": 1155, "end": [62], "runs": 1, "run_s": 600, "cost_s": 150,
               "optional": True, "by_name": True, "movie": {"donor": 61}, "skip_after_s": 10.0,
               "settles": "F4: one Confirm 10 s into FMV003 -- the skip dialog's published choice (prompt, options, "
                          "active, selected at readiness); the rule answers it; FMV003 continues"},
    "R-BATTLE-VOID": {"field": 62, "entrance": 0, "sc": 1155, "end": [64], "runs": 1, "run_s": 600, "cost_s": 90,
                      "by_name": True, "last": True, "battle_override": {"max_turns": 0},
                      "settles": "F3: fight() raises FightTimeout at the FIRST command prompt, before any attack (V15, "
                                 "0 turns, no battlecmd), so the run stops mid-fight in BattleHUD by construction; "
                                 "end_run takes S3's soft reset from BattleHUD (recover-in-battle, recover-reset, no "
                                 "recover-reset-failed) and reaches the title"},
}


def select(stages: dict, field=None, env=None) -> list:
    """The stage names a launch runs: ``O3_STAGE`` (one, by name), else the one stage warping into ``field`` that is
    not ``by_name`` (a smoke warps into several and answers no field), else every non-optional stage in the table's
    order with the ``last`` ones after the rest -- R-BATTLE-VOID ends the launch."""
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


def stage_pred(pred: dict, stage: dict) -> dict:
    """The draft with the stage's own start (o2_rehearse.stage_pred: its field, entrance and scenario) and its
    ``battle_override`` on every registry row -- each row then checked by segment_drive.battle_of like any (R-BATTLE-
    VOID's ``max_turns`` 0 is legal), so a bad override refuses before anything is driven."""
    p = O2R.stage_pred(pred, stage)
    if stage.get("battle_override"):
        p["battles"] = [dict(b, **stage["battle_override"]) for b in p.get("battles") or ()]
    for b in p.get("battles") or ():
        SD.battle_of(p, b)
    return p


class Skipper:
    """R-SKIP's wrapper round the recorder (7.1): every poll goes to the recorder; ``skip_after_s`` after the run's
    first poll in the movie's place it presses Confirm ONCE -- the stray Confirm that opens the skip dialog -- and
    records the frame and the seconds."""

    def __init__(self, g, inner, stage: dict):
        self.g, self.inner, self.stage = g, inner, stage
        self.first = None
        self.pressed = None

    def __call__(self, st, ctx: dict) -> None:
        self.inner(st, ctx)
        if self.pressed is not None or ctx.get("donor") != self.stage["movie"]["donor"]:
            return
        now = time.time()
        if self.first is None:
            self.first = now
        elif now - self.first >= float(self.stage["skip_after_s"]):
            self.g.press("confirm", 4)
            self.pressed = {"frame": st.frame, "field": st.field_id, "s": round(now - self.first, 2)}


# ======================================================================== the launch's own readings
def launch_readings(g, pred: dict, *, census=None) -> dict:
    """The settings and P-STOCK-BATTLE as THIS launch's install holds them (7.2: F10, F12): the stacked folders the
    driven game's Memoria.ini names, the engine's reading of the frozen settings keys, P-SETTINGS and
    P-STOCK-BATTLE (``census`` stands in for the scene read, a seam for the fake). P-LAUNCH and P-DONOR-LOG are the
    capabilities' (recorded beside)."""
    import dali_tour as D
    game = Path(g.game_path)
    try:
        roots = D.mod_roots(game)
    except OSError:
        roots = []
    want = pred.get("settings") or P.SETTINGS
    settings = P.install_settings(game, roots, want)
    ok, detail = P.p_settings(want, settings)
    return {"roots": [Path(r).name for r in roots], "settings": settings,
            "checks": [[ok, P.O3.title("P-SETTINGS"), detail], list(P.O3.stock_battle_check(pred, roots,
                                                                                            census=census))]}


def _new_log_lines(g, mark) -> list:
    """Memoria.log's warning and error lines (``|W|`` / ``|E|``) written since ``mark`` (Session.log_mark)."""
    from harness.logs import MEMORIA_LOG, read_from
    for name, path in g._log_paths():
        if name != MEMORIA_LOG:
            continue
        offset = 0
        if mark and name in mark and Path(mark[name][0]) == path:
            offset = int(mark[name][1])
        try:
            text = read_from(path, offset)
        except OSError:
            return []
        return [ln for ln in text.splitlines() if "|W|" in ln or "|E|" in ln][:40]
    return []


def _exceptions(g, mark) -> list:
    """Every exception the logs recorded since ``mark``, each marked when it went through the story machinery
    (O3-THROW's set: EventEngine, EBin, StoryTrace, HarnessAgent)."""
    return [{"name": e.name, "where": e.where, "ours": e.name in ST.THROWS and (not e.trace or e.through(*ST.WHERE))}
            for e in g.exceptions_since(mark)]


# ======================================================================== a run, a smoke, a launch
def one(g, name: str, stage: dict, pred: dict, n: int, *, t0: float, floor_for=None, prior_for=None, stock=None,
        recovery=None) -> dict:
    """One traced rehearsal run of ``stage`` (7.1): its record (7.2). ``g.last_fight`` and ``g.last_leave`` are
    cleared first: the Session resets them only at a suite member's start, so a run that never fights would otherwise
    record the previous run's fight and leave as its own (the review, research/o3_design.md 11.7 #7)."""
    from harness import HarnessError
    g.last_fight = g.last_leave = None
    spred = stage_pred(pred, stage)
    log, progress, marks = [], {}, {}
    rec_obs = O2R.Recorder(g, stage, tracks=())
    observe = Skipper(g, rec_obs, stage) if stage.get("skip_after_s") else rec_obs
    trace_name = f"rh_{name}_{n}.jsonl"
    rec = {"stage": name, "n": n, "t0": round(time.time() - t0, 1), "trace_file": trace_name}
    outcome = {"end": "void", "why": "not driven"}
    try:
        P.O3.start_run(g, "S", spred, marks)
        outcome = SD.drive(g, spred, "S", log, deadline=time.time() + float(stage["run_s"]), floor_for=floor_for,
                           prior_for=prior_for, progress=progress, end_fields=list(stage["end"]), observe=observe,
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
        trace = P.trace_summary(rows, spred, side="S", start_place=stage["field"], end_fields=list(stage["end"]),
                                stock=stock, log=log) if rows else {}
    except T.TraceError as err:
        trace = {"error": str(err)[:300]}
    rec.update(
        outcome={k: outcome.get(k) for k in ("end", "why", "v", "cell", "by", "t")},
        grants=rec_obs.grants,
        choices=[x for x in log if x.get("k") == "choice"],
        published_choices=rec_obs.choices,
        pages=rec_obs.pages,
        evidence={"press": [x for x in log if x.get("k") == "press"],
                  "forbidden": [x for x in log if x.get("k") == "forbidden"]},
        battles={"rows": [x for x in log if x.get("k") == "battle"], "battle_epoch0": outcome.get("battle_epoch0")},
        fight=g.last_fight,
        leave=g.last_leave,
        no_progress=rec_obs.no_progress,
        movie=rec_obs.movie,
        skip=observe.pressed if isinstance(observe, Skipper) else None,
        end={"end_state": outcome.get("end_state"), "end_run": None},
        trace=trace,
        log_file=f"rh_{name}_{n}_log.json",
    )
    end_log: list = []
    try:
        P.O3.end_run(g, end_log, recovery=recovery)
        rec["end"]["end_run"] = {"ok": True, "title": g.state.ui_state == "Title", "how": end_log}
    except HarnessError as err:
        rec["end"]["end_run"] = {"ok": False, "why": str(err)[:300], "how": end_log}
    (g.run_dir / rec["log_file"]).write_text(json.dumps({"outcome": outcome, "log": log + end_log}, indent=1,
                                                        default=str), encoding="utf-8")
    rec["t1"] = round(time.time() - t0, 1)
    return rec


def smoke(g, name: str, stage: dict, *, t0: float, recovery=None) -> tuple:
    """F-SMOKE (7.1, F5): ``(records, twins)``. Each field of ``stage["pairs"]`` -- the members first, then their
    stock twins -- by start_run's RAW warp (New Game, ``wait_frames(30)``, the registration checked, ``warp <id>
    <entrance> <sc>``, a wait for the field on FieldHUD -- never Session.warp(): 61-63 never grant the control it
    waits for), ``smoke_s`` of its Main_Init, then its published object sids and objects_status, the exceptions and
    Memoria.log warnings/errors since the warp, and end_run. No ``storytrace`` verb is sent. A failed end_run stops
    the smoke (the next warp would start from an unknown state). ``twins``: each member's sids against its twin's."""
    from harness import HarnessError
    order = [m for m, _t in stage["pairs"]] + [t for _m, t in stage["pairs"]]
    out = []
    for n, field in enumerate(order, 1):
        rec = {"stage": name, "n": n, "field": field, "t0": round(time.time() - t0, 1)}
        mark = g.log_mark()
        try:
            g.newgame()
            g.wait_frames(30)
            g._check_field_id(field, "warp", True)
            tw = time.time()
            g.send(f"warp {field} {stage['entrance']} {stage['sc']}")
            st = g.wait_for(lambda s: s.field_id == field and s.ui_state == "FieldHUD",
                            timeout=float(stage["warp_s"]), what=f"field {field} on the field HUD")
            rec["reached"] = {"field": st.field_id, "ui": st.ui_state, "frame": st.frame, "control": bool(st.control),
                              "s": round(time.time() - tw, 2)}
            time.sleep(float(stage["smoke_s"]))                 # its Main_Init runs; what it inits is published
            st = g.state
            rec["at"] = {"field": st.field_id, "ui": st.ui_state, "frame": st.frame, "control": bool(st.control)}
            rec["objects_status"] = st.objects_status
            rec["sids"] = None if st.objects is None else sorted(int(o.get("sid", -1)) for o in st.objects)
        except HarnessError as err:
            rec["error"] = str(err)[:300]
        rec["exceptions"] = _exceptions(g, mark)
        rec["log_lines"] = _new_log_lines(g, mark)
        end_log: list = []
        try:
            P.O3.end_run(g, end_log, recovery=recovery)
            rec["end_run"] = {"ok": True, "title": g.state.ui_state == "Title", "how": end_log}
        except HarnessError as err:
            rec["end_run"] = {"ok": False, "why": str(err)[:300], "how": end_log}
        rec["t1"] = round(time.time() - t0, 1)
        out.append(rec)
        print(f"[o3-rh] {name} warp {n} ({field}): "
              + (f"FieldHUD in {rec['reached']['s']}s, sids {rec.get('sids')}" if rec.get("reached") else
                 f"NOT REACHED: {rec.get('error')}") + f"; end_run {'ok' if rec['end_run']['ok'] else 'FAILED'}",
              flush=True)
        if not rec["end_run"]["ok"]:
            break
    by = {r["field"]: r for r in out}
    twins = []
    for m, t in stage["pairs"]:
        ms, ts = (by.get(m) or {}).get("sids"), (by.get(t) or {}).get("sids")
        twins.append({"member": m, "twin": t, "member_sids": ms, "twin_sids": ts,
                      "equal": ms is not None and ms == ts})
    return out, twins


def run(g, field=None, *, stages=None, pred=None, floor_for=None, prior_for=None, stock=None, recovery=None,
        env=None, census=None) -> None:
    """The rehearsal launch (tools/play.py's entry; ``field`` from ``--field``). The capabilities first (P-CAP,
    P-OBJECTS, P-LANG, P-DONOR-LOG, P-LAUNCH: a session's), the launch's own readings (settings, P-SETTINGS,
    P-STOCK-BATTLE), then each selected stage -- its runs, or its smoke -- the record rewritten after every run into
    ``o3_rehearsal.json``. A run whose end_run cannot reach the title stops the launch. ``stages``/``pred``/
    ``floor_for``/``prior_for``/``stock``/``recovery``/``env``/``census`` are seams for the fake; each defaults to
    the real thing."""
    stages = STAGES if stages is None else stages
    pred = P.draft_predictions() if pred is None else pred
    names = select(stages, field, env)
    t0 = time.time()
    record = {"what": "O3 rehearsals (research/o3_design.md 7): staged runs prove driver mechanics only; R-FULL's "
                      "traces alone may define predictions; F-SMOKE loads the members, untraced",
              "draft_sha256": O2R._draft_sha(pred), "stages_run": names,
              "stage_defs": {n: stages[n] for n in names}, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "capabilities": [], "launch": {}, "stages": {}, "twins": {}}
    path = g.run_dir / P.REHEARSAL_FILE

    def save() -> None:
        path.write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
    caps = P.O3.capabilities(g)
    record["capabilities"] = [[ok, what, detail] for ok, what, detail in caps]
    for ok, what, detail in caps:
        g.check(ok, what, detail)
    record["launch"] = launch_readings(g, pred, census=census)
    save()
    if not all(ok for ok, _w, _d in caps):
        return
    for name in names:
        stage = stages[name]
        if stage.get("pairs"):
            g.shot_prefix = name
            try:
                recs, twins = smoke(g, name, stage, t0=t0, recovery=recovery)
            finally:
                g.shot_prefix = ""
            record["stages"][name], record["twins"][name] = recs, twins
            save()
            if not all((r.get("end_run") or {}).get("ok") for r in recs):
                record["stopped"] = f"{name}: end_run could not reach the title"
                save()
                return
            continue
        for n in range(1, int(stage["runs"]) + 1):
            g.shot_prefix = f"{name}-{n}"
            try:
                rec = one(g, name, stage, pred, n, t0=t0, floor_for=floor_for, prior_for=prior_for, stock=stock,
                          recovery=recovery)
            finally:
                g.shot_prefix = ""
            record["stages"].setdefault(name, []).append(rec)
            save()
            print(f"[o3-rh] {name} run {n}: {rec['outcome']['end']} -- {rec['outcome']['why']}", flush=True)
            if not (rec["end"]["end_run"] or {}).get("ok"):
                record["stopped"] = f"{name} run {n}: end_run could not reach the title"
                save()
                return
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
