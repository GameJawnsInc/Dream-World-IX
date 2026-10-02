"""O4's REHEARSALS (research/o4_design.md section 7): the Chanbara policy on STOCK Alexandria Castle, stage by stage, the
F-side load smoke and R-GATE after the owner-gated deploy. Each traced stage warps into its field at its entrance and
SC, drives the DRAFT (its ``chanbara_override`` merged into the policy and checked) to its own end fields, and records
what the freeze checklist (7.3) is read from; F-SMOKE warps into each member and its stock twin with NO trace and
records what loaded; R-GATE plays the PACED policy on S and then on F and reads its verdict. Nothing is deployed and
nothing is frozen here.

    py tools/play.py studies/story-trace/o4_rehearse.py --field 64 --label o4-rh-chanbara --timeout 240   # R-CHANBARA
    py tools/play.py studies/story-trace/o4_rehearse.py --label o4-rh --timeout 240           # the default order
    set O4_STAGE=R-FULL & py tools/play.py studies/story-trace/o4_rehearse.py --label o4-rh-full --timeout 240
    set O4_STAGE=F-SMOKE & py tools/play.py studies/story-trace/o4_rehearse.py --label o4-rh-smoke --timeout 240
    set O4_STAGE=R-GATE & py tools/play.py studies/story-trace/o4_rehearse.py --label o4-rh-gate --timeout 240
    py studies/story-trace/o4_castle.py --rehearsal-report <run dir>

WHICH STAGE: the environment variable ``O4_STAGE`` names one (R-CHANBARA, R-FULL, R-CHANBARA-VOID, F-SMOKE, R-GATE);
else ``--field 64`` picks R-CHANBARA, the one stage warping into 64 that is not by-name-only; else, in one launch:
R-CHANBARA (the go/no-go: the prompts' publication), R-FULL, and R-CHANBARA-VOID LAST -- it stops a run mid-fight, so a
failure there ends the launch. F-SMOKE and R-GATE run only by name, after the deploy and the relaunch.

EACH TRACED RUN: New Game; the story trace armed; the raw ``warp <field> <entrance> <sc>`` (Segment.start_run); then
segment_drive.drive on the stage's predictions with its end fields (per side), the live forbidden scan on, the input
witness (outside input anywhere in the run is V13) and the recorder (O2's, no NPC track, plus each page's windows and
the sample that no longer shows it) watching every poll; the trace collected to ``rh_<stage>_<n>.jsonl``; the record
written into ``o4_rehearsal.json``; end_run, its recovery rows recorded.

F-SMOKE (NO trace -- no ``storytrace`` verb is ever sent, so no fork data exists before the freeze): per warp, a RAW
warp with the pair's OWN entrance and SC -- New Game, ``wait_frames(30)``, the field's registration checked, ``warp
<id> <entrance> <sc>``, then a wait for the field on FieldHUD; never Session.warp(), whose wait for control 64, 150
and 153 never grant would hang 60 s a warp -- then ``smoke_s`` of Main_Init, the published object sids, the exceptions
and the Memoria.log warnings and errors since the warp, and end_run. The members first, then their stock twins.

R-GATE (7.4 G2): the paced overlay (2.4.10) on both sides -- S warps into 64, F into member(64), each ending in 150 /
member(150) -- S first, each side until an INFORMATIVE run, at most ``attempts`` a side; each run read by
o4_castle.gate_reading with the launch's own settings and engine; the verdict (o4_castle.gate_verdict) goes into the
record, never into o4_forks.json: the lead fills ``gate_witness`` from it.

WHAT A STAGE MAY SETTLE (7.1): only R-FULL's traces may define or change the keys, the start or the end state. The
staged runs prove mechanics and are compared within their stage. Every summary is cut at the stage's end PLACES
(o4_castle.trace_summary), never its end fields: an F stage ending in a member is cut there.
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
import o3_prima_vista as P                                             # noqa: E402
import o3_rehearse as O3R                                              # noqa: E402
import o4_castle as C                                                  # noqa: E402
import segment_drive as SD                                             # noqa: E402
from ff9mapkit import storytrace as T                                  # noqa: E402
from segment_trace import members_of, place                            # noqa: E402

ENV = "O4_STAGE"
#: The stages (research/o4_design.md 7.1): the warp, the end fields (per side where they differ), the runs, a run
#: budget and a cost estimate in seconds a run (F10 replaces every number from what is measured). ``by_name``: never
#: picked by ``--field``; ``optional``: only by name; ``last``: after every other stage of a launch.
STAGES = {
    "R-CHANBARA": {"field": 64, "entrance": 100, "sc": 1155, "end": [150], "runs": 2, "run_s": 300, "cost_s": 110,
                   "settles": "F1-F6, F12-F15 (the go/no-go): the prompts' published phrase_raw and texts; 49/49 "
                              "reading 122/123/127/128; j per prompt and the regime; each instance's evidence and the "
                              "merged stream's gaps; the gap after each hit; the tweens; T0 vs the first prompt; 127's "
                              "published options and selected; the fight's and the pass's length; the pairs' gates; "
                              "the pages' dropped first presses; lead_ticks; the input witness"},
    "R-FULL": {"field": 64, "entrance": 100, "sc": 1155, "end": [153], "runs": 2, "run_s": 600, "cost_s": 200,
               "by_name": True,
               "settles": "F7 (end_run from 153), F8-F10: the keys, the start rows, the residue, the end cut, the end "
                          "state, the run time -- the ONLY stage whose traces define predictions"},
    "R-CHANBARA-VOID": {"field": 64, "entrance": 100, "sc": 1155, "end": [150], "runs": 1, "run_s": 300,
                        "cost_s": 60, "by_name": True, "last": True, "chanbara_override": {"stop_after": 10},
                        "settles": "F7: a V17 mid-fight (instance 11 opens past stop_after 10) stops with nothing more "
                                   "pressed; end_run (the warp to 4600 from the fight's FieldHUD, the ladder) reaches "
                                   "the title"},
    "F-SMOKE": {"pairs": [[31240, 64, 100, 1155], [31243, 150, 325, 1155], [31245, 153, 325, 1190]], "runs": 1,
                "smoke_s": 8.0, "warp_s": 60.0, "cost_s": 150, "by_name": True, "optional": True,
                "settles": "G1: each member loads at its entrance and SC (its field, FieldHUD), its Main_Init's published "
                           "object sids equal its stock twin's after smoke_s (64@100 {5, 6, 13, 20}; 150@325 {2, 3, 5, "
                           "6, 9, 4}; 153@325 {3, 7, 31, 9, 11}); 0 exceptions through the story machinery; end_run ok; "
                           "the Memoria.log warnings"},
    "R-GATE": {"field": {"S": 64, "F": 31240}, "entrance": 100, "sc": 1155, "end": {"S": [150], "F": [31243]},
               "attempts": 3, "run_s": 300, "cost_s": 110, "by_name": True, "optional": True,
               "chanbara_override": {**C.PACED, "raw_floor": None},
               "settles": "G2: the EMinigame +30% on member(64) -- S then F, paced (j ~22-25, raw 79-99), each side "
                          "until an informative run (<= 3 attempts); the verdict and its cause, with the launch's "
                          "engine and settings"},
}


def select(stages: dict, field=None, env=None) -> list:
    """The stage names a launch runs: ``O4_STAGE`` (one, by name), else the one stage warping into ``field`` that is
    not ``by_name``, else every non-optional stage in the table's order with the ``last`` ones after the rest --
    R-CHANBARA-VOID ends the launch."""
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


def stage_start(stage: dict, side: str) -> int:
    """The field a stage warps into on ``side``: its ``field``, or ``field[side]`` when it is per side (R-GATE)."""
    f = stage["field"]
    return int(f[side]) if isinstance(f, dict) else int(f)


def stage_ends(stage: dict, side: str) -> list:
    """The end fields a stage drives to on ``side``: its ``end``, or ``end[side]`` when it is per side (R-GATE's
    member(150) on F)."""
    e = stage["end"]
    return [int(x) for x in (e[side] if isinstance(e, dict) else e)]


def stage_pred(pred: dict, stage: dict) -> dict:
    """The draft with the stage's own start on each side (its ``field``: one id, or one a side), entrance and scenario,
    and its ``chanbara_override`` merged into a copy of the policy -- a key set to None is DROPPED (the paced overlay
    drops ``raw_floor``) -- then checked by segment_drive.chanbara_of, so a bad override refuses before anything is
    driven. The predictions given are never changed: R-GATE's pace and R-CHANBARA-VOID's stop_after reach a stage
    through this overlay alone (the frozen predictions never carry them, 2.4.10)."""
    p = copy.deepcopy(pred)
    p.update(start={"S": stage_start(stage, "S"), "F": stage_start(stage, "F")}, entrance=stage["entrance"],
             scenario=stage["sc"])
    over = stage.get("chanbara_override")
    if over:
        pol = dict(p["chanbara"])
        for k, v in over.items():
            if v is None:
                pol.pop(k, None)
            else:
                pol[k] = copy.deepcopy(v)
        p["chanbara"] = pol
    SD.chanbara_of(p)
    return p


# ======================================================================== the recorder and the run's own readings
class Recorder(O2R.Recorder):
    """O2's recorder (no NPC track), plus what 7.2 reads of each page that O2's does not keep: its windows' rendered
    ``texts``, and ``gone_frame`` -- the frame of the first poll that no longer shows the page as it was (a pair's
    second window opening, or every window closed) -- for the KEYON pairs' first seen -> gone (F12) and each page's
    presses (F13). A page is what O2's records: a dialog with text, no control, no choice."""

    def __call__(self, st, ctx: dict) -> None:
        before, n = self._page, len(self.pages)
        super().__call__(st, ctx)
        if len(self.pages) > n:
            self.pages[-1]["texts"] = list(st.texts)
            self.pages[-1]["gone_frame"] = None
        if before is not None and self._page != before:
            hit = next((p for p in reversed(self.pages[:n]) if p["text"] == before and p.get("gone_frame") is None),
                       None)
            if hit is not None:
                hit["gone_frame"] = st.frame


def _pair_window(raw: str) -> bool:
    """A KEYON pair's window (105/106, 107/108, 109/110, 150's 98/99): a timed page (``[TIME=-1]``, closed by its
    script after the KEYON), never a prompt (no ``[DBTN=``)."""
    return "[TIME=-1]" in raw and "[DBTN=" not in raw


def _fps(log: list):
    """The fight's measured frame rate (the zone row's), or None."""
    z = C.zone_of(log)
    rate = (z or {}).get("rate") or {}
    return rate.get("fps") or None


def pairs_of(pages: list, log: list) -> list:
    """F12's reading: each KEYON pair as the recorder saw it -- consecutive pages whose windows are all pair windows --
    ``{"texts", "first_frame", "second_frame", "gone_frame", "s", "s_after_second", "presses", "seqs"}``: its windows,
    the first poll showing it, the first showing both windows, the first showing neither (``gone_frame``), seconds
    first seen -> gone and second window -> gone at the zone's measured rate (None without one), and the page Confirms
    whose texts hold one of its windows."""
    fps = _fps(log)
    presses = [p for p in log if p.get("k") == "press" and p.get("why") == "page"]
    groups, cur = [], []
    for pg in pages:
        raws = pg.get("raw_texts") or []
        if raws and all(_pair_window(x) for x in raws):
            cur.append(pg)
            continue
        if cur:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    out = []
    for g_ in groups:
        texts = []
        for pg in g_:
            texts += [t for t in pg.get("texts") or () if t not in texts]
        second = next((pg["frame"] for pg in g_ if len(pg.get("raw_texts") or ()) >= 2), None)
        gone = g_[-1].get("gone_frame")
        hit = [p for p in presses if set(p.get("texts") or ()) & set(texts)]

        def secs(a):
            return None if a is None or gone is None or not fps else round((gone - a) / fps, 2)
        out.append({"texts": texts, "first_frame": g_[0]["frame"], "second_frame": second, "gone_frame": gone,
                    "s": secs(g_[0]["frame"]), "s_after_second": secs(second), "presses": len(hit),
                    "seqs": [p.get("seq") for p in hit]})
    return out


def page_presses_of(pages: list, log: list) -> list:
    """F13's reading, in frame order: each page that is no pair and no prompt (111, 122, 123, 128, 150's) --
    ``{"text", "frame", "gone_frame", "presses", "to_down"}``: the page Confirms decided while it was up and, for each,
    the frames from first seen to its down frame (None for a press whose accepted event was not joined). 111 is the
    zone's own (its executor presses it in Z0, between the recorder's polls): read off the zone row's ``start_page`` --
    its first frame, its presses' seqs, its first sample without (T0). Every other page as the recorder saw it: the
    presses whose texts hold one of its windows, decided (``pre`` frame) in [first seen, gone)."""
    presses = [p for p in log if p.get("k") == "press" and p.get("why") == "page"]
    out = []
    for z in (x for x in log if x.get("k") == "zone"):
        sp = z.get("start_page") or {}
        seqs, lo = set(sp.get("presses") or ()), sp.get("seen_frame")
        hit = [p for p in presses if p.get("seq") in seqs]
        if hit:
            out.append({"text": "\n".join(hit[0].get("texts") or ()), "frame": lo,
                        "gone_frame": sp.get("first_without_frame"), "presses": len(hit),
                        "to_down": [None if p.get("down_frame") is None or lo is None else p["down_frame"] - lo
                                    for p in hit]})
    for pg in pages:
        raws = pg.get("raw_texts") or []
        if not raws or all(_pair_window(x) for x in raws) or any("[DBTN=" in x for x in raws):
            continue                                    # a pair; a prompt; 111 (the zone row's, above)
        texts, lo, hi = set(pg.get("texts") or ()), pg["frame"], pg.get("gone_frame")
        hit = [p for p in presses if set(p.get("texts") or ()) & texts
               and lo <= ((p.get("pre") or {}).get("frame") or -1) < (hi if hi is not None else 1 << 62)]
        out.append({"text": pg["text"], "frame": lo, "gone_frame": hi, "presses": len(hit),
                    "to_down": [None if p.get("down_frame") is None else p["down_frame"] - lo for p in hit]})
    return sorted(out, key=lambda x: (x["frame"] is None, x["frame"] or 0))


def prompt_records(log: list) -> list:
    """7.2's per-instance reading of the fight (F1, F3-F5, F14): its published texts and phrase_raw, ``j_lo`` /
    ``j_hi`` and the regime, the evidence, the ticks from its down frame to the last sample listing it
    (``listed_ticks``) and to the first without it (``gone_ticks``), the longest read gap, the gap from its going to
    the next instance's first sample (``gap_ticks``) and the pass (``pass_ticks``: seen to the next seen), the slide,
    and ``lead_ticks`` -- (down frame - the frame its press was decided on) x per_frame (2.4.10's latency)."""
    _z, prompts, ppress, _other = C.fight_rows(log)
    by_n = {p.get("n"): p for p in ppress}
    out = []
    for i, p in enumerate(prompts):
        rate = SD.rate_of(p["rate"]) if p.get("rate") else None
        nxt = prompts[i + 1] if i + 1 < len(prompts) else {}

        def ticks(a, b):
            return None if rate is None or a is None or b is None else rate.ticks_most(max(0, int(b) - int(a)))
        pre = ((by_n.get(p["n"]) or {}).get("pre") or {}).get("frame")
        lead = (None if rate is None or pre is None or p.get("down_frame") is None
                else round((p["down_frame"] - pre) * rate.per_frame(), 2))
        pub = p.get("published") or {}
        out.append({"n": p["n"], "dbtn": p["dbtn"], "texts": pub.get("texts"), "phrase_raw": pub.get("phrase_raw"),
                    "j_lo": p.get("j_lo"), "j_hi": p.get("j_hi"), "regime": p.get("regime"),
                    "evidence": p.get("evidence"), "listed_ticks": ticks(p.get("down_frame"), p.get("last_listed_frame")),
                    "gone_ticks": ticks(p.get("down_frame"), p.get("gone_frame")), "read_gap": p.get("read_gap"),
                    "gap_ticks": ticks(p.get("gone_frame"), nxt.get("seen_frame")),
                    "pass_ticks": ticks(p.get("seen_frame"), nxt.get("seen_frame")), "slide": p.get("slide"),
                    "lead_ticks": lead})
    return out


def launch_readings(g, pred: dict, *, engine=None, live_engine=None) -> dict:
    """The launch's own readings (7.2, F11): the stacked folders the driven game's Memoria.ini names, the engine's
    reading of the frozen settings keys (P-SETTINGS), field 70's override (P-OVERRIDE) and the live engine DLLs
    (P-ENGINE against ``engine``, the pinned; ``live_engine`` a seam for the fake). P-LAUNCH, P-DONOR-LOG and P-PAD
    are the capabilities' (recorded beside)."""
    import dali_tour as D
    game = Path(g.game_path)
    try:
        roots = D.mod_roots(game)
    except OSError:
        roots = []
    want = pred.get("settings") or C.SETTINGS
    settings = P.install_settings(game, roots, want)
    live = live_engine if live_engine is not None else C.engine_shas(game)
    pinned = engine or pred.get("engine") or C.ENGINE
    checks = [[*P.p_settings(want, settings)], [*C.p_override(C.override70_of(roots), pred.get("override70")
                                                               or C.OVERRIDE70)],
              [*C.p_engine(live, pinned)]]
    titles = ("P-SETTINGS", "P-OVERRIDE", "P-ENGINE")
    return {"roots": [Path(r).name for r in roots], "settings": settings,
            "engine": {"x64": live.get("x64"), "x86": live.get("x86")},
            "checks": [[ok, C.O4.title(t), detail] for t, (ok, detail) in zip(titles, checks)]}


# ======================================================================== a run, a smoke, the gate, a launch
def one(g, name: str, stage: dict, pred: dict, n: int, *, side: str = "S", t0: float, floor_for=None,
        prior_for=None, stock=None, recovery=None, witness=None) -> dict:
    """One traced rehearsal run of ``stage`` on ``side`` (7.1): its record (7.2) -- O3's sections (grants, the pages
    with ``timed``, the published choices, the press evidence, the longest no-progress stretch, the end state, end_run's
    rows) plus the zone and prompt rows whole, the fight's summary, the per-instance reading, the pairs, each page's
    presses, the score and gil pages as published, the observed and input rows, and the trace through O4's summary cut
    at the stage's end PLACES on that side. A run the instrument stopped (a HarnessError: outside input, the budget, a
    refused press; or an unexpected exception) records the class V13 (driver), as the session's read of a STOPPED run
    does -- R-GATE's reading needs it (the review, research/o4_design.md 11.5 #6). ``witness`` (the outside-input
    witness; default the ctypes one) is a seam for the fake."""
    from harness import HarnessError
    spred = stage_pred(pred, stage)
    ends = stage_ends(stage, side)
    members = members_of(spred) if side == "F" else {}
    log, progress, marks = [], {}, {}
    rec_obs = Recorder(g, stage, tracks=())
    trace_name = f"rh_{name}_{n}.jsonl"
    rec = {"stage": name, "n": n, "side": side, "t0": round(time.time() - t0, 1), "trace_file": trace_name}
    outcome = {"end": "void", "why": "not driven"}
    try:
        C.O4.start_run(g, side, spred, marks)
        outcome = SD.drive(g, spred, side, log, deadline=time.time() + float(stage["run_s"]), floor_for=floor_for,
                           prior_for=prior_for, progress=progress, end_fields=list(ends), observe=rec_obs,
                           forbid_live=True, witness=witness if witness is not None else C.input_witness(g))
    except SD.RouteVoid as err:
        outcome = {"end": "void", "why": f"route: {err}", "v": err.v, "cell": err.cell, "by": err.by}
    except HarnessError as err:                               # the instrument's: V13, as the session reads a STOPPED
        outcome = {"end": "void", "why": f"STOPPED: {str(err)[:300]}", "v": "V13", "by": "driver"}
    except Exception as err:                                  # noqa: BLE001 -- one run's bug must not cost the others
        outcome = {"end": "void", "why": f"STOPPED (unexpected): {type(err).__name__}: {str(err)[:300]}", "v": "V13",
                   "by": "driver"}
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
        trace = C.trace_summary(rows, spred, side=side, start_place=place(stage_start(stage, side), members),
                                end_fields=list(ends), stock=stock, log=log) if rows else {}
    except T.TraceError as err:
        trace = {"error": str(err)[:300]}
    pages = rec_obs.pages
    rec.update(
        outcome={k: outcome.get(k) for k in ("end", "why", "v", "cell", "by", "t")},
        beats=outcome.get("beats"),
        grants=rec_obs.grants,
        zone_rows=[x for x in log if x.get("k") == "zone"],
        prompt_rows=[x for x in log if x.get("k") == "prompt"],
        fight=C.fight_line(log, outcome),
        prompts=prompt_records(log),
        pairs=pairs_of(pages, log),
        page_presses=page_presses_of(pages, log),
        choices=[x for x in log if x.get("k") == "choice"],
        published_choices=rec_obs.choices,
        pages=pages,
        transcript=list(outcome.get("pages") or []),
        score_page=next((p["text"] for p in pages if SD.SCORE_MARK in p["text"]), None),
        gil_page=next((p["text"] for p in pages if SD.GIL_MARK in p["text"]), None),
        evidence={"press": [x for x in log if x.get("k") == "press"],
                  "forbidden": [x for x in log if x.get("k") == "forbidden"],
                  "observed": [x for x in log if x.get("k") == "observed"],
                  "input": [x for x in log if x.get("k") == "input"],
                  "page_judge": [x for x in log if x.get("k") == "page_judge"]},
        no_progress=rec_obs.no_progress,
        end={"end_state": outcome.get("end_state"), "end_run": None},
        trace=trace,
        log_file=f"rh_{name}_{n}_log.json",
    )
    end_log: list = []
    try:
        C.O4.end_run(g, end_log, recovery=recovery)
        rec["end"]["end_run"] = {"ok": True, "title": g.state.ui_state == "Title", "how": end_log}
    except HarnessError as err:
        rec["end"]["end_run"] = {"ok": False, "why": str(err)[:300], "how": end_log}
    (g.run_dir / rec["log_file"]).write_text(json.dumps({"outcome": outcome, "log": log + end_log}, indent=1,
                                                        default=str), encoding="utf-8")
    rec["t1"] = round(time.time() - t0, 1)
    return rec


def smoke(g, name: str, stage: dict, *, t0: float, recovery=None) -> tuple:
    """F-SMOKE (7.1, G1): ``(records, twins)``. Each field of ``stage["pairs"]`` (``[member, twin, entrance, sc]``) --
    the members first, then their stock twins -- by a RAW warp with the pair's OWN entrance and SC (New Game,
    ``wait_frames(30)``, the registration checked, ``warp <id> <entrance> <sc>``, a wait for the field on FieldHUD --
    never Session.warp(): 64, 150 and 153 never grant the control it waits for), ``smoke_s`` of its Main_Init, then its
    published object sids and objects_status, the exceptions and Memoria.log warnings/errors since the warp, and
    end_run. No ``storytrace`` verb is sent. A failed end_run stops the smoke (the next warp would start from an
    unknown state). ``twins``: each member's sids against its twin's."""
    from harness import HarnessError
    pairs = [[int(m), int(t), int(e), int(s)] for m, t, e, s in stage["pairs"]]
    order = [(m, e, s) for m, _t, e, s in pairs] + [(t, e, s) for _m, t, e, s in pairs]
    out = []
    for n, (field, entrance, sc) in enumerate(order, 1):
        rec = {"stage": name, "n": n, "field": field, "entrance": entrance, "sc": sc, "t0": round(time.time() - t0, 1)}
        mark = g.log_mark()
        try:
            g.newgame()
            g.wait_frames(30)
            g._check_field_id(field, "warp", True)
            tw = time.time()
            g.send(f"warp {field} {entrance} {sc}")
            st = g.wait_for(lambda s: s.field_id == field and s.ui_state == "FieldHUD",
                            timeout=float(stage["warp_s"]), what=f"field {field} on the field HUD")
            rec["reached"] = {"field": st.field_id, "ui": st.ui_state, "frame": st.frame, "control": bool(st.control),
                              "s": round(time.time() - tw, 2)}
            time.sleep(float(stage["smoke_s"]))                 # its Main_Init runs; what it inits is published
            st = g.state
            rec["at"] = {"field": st.field_id, "ui": st.ui_state, "frame": st.frame, "control": bool(st.control),
                         "sc": st.scenario}
            rec["objects_status"] = st.objects_status
            rec["sids"] = None if st.objects is None else sorted(int(o.get("sid", -1)) for o in st.objects)
        except HarnessError as err:
            rec["error"] = str(err)[:300]
        rec["exceptions"] = O3R._exceptions(g, mark)
        rec["log_lines"] = O3R._new_log_lines(g, mark)
        end_log: list = []
        try:
            C.O4.end_run(g, end_log, recovery=recovery)
            rec["end_run"] = {"ok": True, "title": g.state.ui_state == "Title", "how": end_log}
        except HarnessError as err:
            rec["end_run"] = {"ok": False, "why": str(err)[:300], "how": end_log}
        rec["t1"] = round(time.time() - t0, 1)
        out.append(rec)
        print(f"[o4-rh] {name} warp {n} ({field} {entrance} {sc}): "
              + (f"FieldHUD in {rec['reached']['s']}s, sids {rec.get('sids')}" if rec.get("reached") else
                 f"NOT REACHED: {rec.get('error')}") + f"; end_run {'ok' if rec['end_run']['ok'] else 'FAILED'}",
              flush=True)
        if not rec["end_run"]["ok"]:
            break
    by = {r["field"]: r for r in out}
    twins = []
    for m, t, _e, _s in pairs:
        ms, ts = (by.get(m) or {}).get("sids"), (by.get(t) or {}).get("sids")
        twins.append({"member": m, "twin": t, "member_sids": ms, "twin_sids": ts, "equal": ms is not None and ms == ts})
    return out, twins


def gate_read(rec: dict, log: list, outcome: dict, spred: dict, launch: dict) -> dict:
    """One R-GATE run as its verdict reads it (o4_castle.gate_reading): the run's zone and prompt rows and EVERY press
    of the visit (as Z3's judge read them: a stray press in the fight is the driver's V17), its transcript and
    page_judge rows, the trace's ip338 row's new value (Byte[475]), the stage's paced policy, the launch's recorded
    settings and engine, and the run's own VOID class (V13 for an instrument stop: :func:`one` records it)."""
    z, prompts, ppress, other = C.fight_rows(log)
    rows = ((rec.get("trace") or {}).get("sword") or {}).get("score", {}).get("rows") or []
    return C.gate_reading(rec["side"], zone=z, prompts=prompts, presses=ppress + other,
                          pages=list(outcome.get("pages") or []),
                          page_judge=[x for x in log if x.get("k") == "page_judge"],
                          byte475=rows[-1][2] if rows else None, pol=spred["chanbara"],
                          settings=launch.get("settings"), engine=launch.get("engine"),
                          v=(rec.get("outcome") or {}).get("v"))


def gate(g, name: str, stage: dict, pred: dict, *, t0: float, launch: dict, record: dict, save, engine=None,
         **kw) -> dict:
    """R-GATE (7.4 G2): S first, each side until an INFORMATIVE run, at most ``attempts`` a side; every run read by
    :func:`gate_read`. F runs only when S stands: an informative S run that shows 100 through the stock +30% -- with
    none, the verdict is UNINFORMATIVE, and with another number INVALID, whatever F would show (STOP, 7.4). The verdict
    (o4_castle.gate_verdict, against 4.13's settings and the pinned ``engine``) goes into ``record["gate"][name]`` --
    never into o4_forks.json. A run whose end_run cannot reach the title stops it."""
    spred = stage_pred(pred, stage)
    settings, pinned = pred.get("settings") or C.SETTINGS, engine or pred.get("engine") or C.ENGINE
    readings, k = [], 0
    for side in ("S", "F"):
        if side == "F":
            so_far = C.gate_verdict(readings, settings=settings, engine=pinned)
            if so_far["s_run"] is None or so_far["verdict"] == "INVALID":
                break
        for _attempt in range(int(stage.get("attempts", C.GATE_ATTEMPTS))):
            k += 1
            g.shot_prefix = f"{name}-{k}"
            try:
                rec = one(g, name, stage, pred, k, side=side, t0=t0, **kw)
            finally:
                g.shot_prefix = ""
            doc = json.loads((g.run_dir / rec["log_file"]).read_text(encoding="utf-8"))
            rec["gate"] = gate_read(rec, doc["log"], doc["outcome"], spred, launch)
            readings.append(rec["gate"])
            record["stages"].setdefault(name, []).append(rec)
            save()
            print(f"[o4-rh] {name} run {k} ({side}): {rec['outcome']['end']} -- {rec['gate']['why']}", flush=True)
            if not (rec["end"]["end_run"] or {}).get("ok"):
                record["stopped"] = f"{name} run {k}: end_run could not reach the title"
                break
            if rec["gate"]["informative"]:
                break
        if record.get("stopped"):
            break
    verdict = C.gate_verdict(readings, settings=settings, engine=pinned)
    record.setdefault("gate", {})[name] = verdict
    save()
    print(f"[o4-rh] {name}: {verdict['verdict']} (cause {verdict['cause'] or 'none'}) -- {verdict['detail']}",
          flush=True)
    return verdict


def run(g, field=None, *, stages=None, pred=None, floor_for=None, prior_for=None, stock=None, recovery=None,
        env=None, witness=None, pads=..., engine=None, live_engine=None) -> None:
    """The rehearsal launch (tools/play.py's entry; ``field`` from ``--field``). The capabilities first (P-CAP,
    P-OBJECTS, P-LANG, P-DONOR-LOG, P-LAUNCH with the engine, P-PAD: a session's), the launch's own readings (the
    settings, P-SETTINGS, P-OVERRIDE, P-ENGINE), then each selected stage -- its runs, its smoke, or R-GATE's sides --
    the record rewritten after every run into ``o4_rehearsal.json``. A run whose end_run cannot reach the title stops
    the launch. ``stages``/``pred``/``floor_for``/``prior_for``/``stock``/``recovery``/``env``/``witness``/``pads``
    and ``engine``/``live_engine`` (the pinned and the live engine DLLs' shas) are seams for the fake; each defaults to
    the real thing."""
    stages = STAGES if stages is None else stages
    pred = C.O4.draft() if pred is None else pred
    names = select(stages, field, env)
    t0 = time.time()
    record = {"what": "O4 rehearsals (research/o4_design.md 7): staged runs prove driver mechanics only; R-FULL's "
                      "traces alone may define predictions; F-SMOKE loads the members, untraced; R-GATE witnesses the "
                      "+30% on member(64), outside the frozen claim",
              "draft_sha256": O2R._draft_sha(pred), "stages_run": names,
              "stage_defs": {n: stages[n] for n in names}, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "capabilities": [], "launch": {}, "stages": {}, "twins": {}, "gate": {}}
    path = g.run_dir / C.REHEARSAL_FILE

    def save() -> None:
        path.write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
    caps = C.O4.capabilities(g, pads=pads, engine=engine, live_engine=live_engine)
    record["capabilities"] = [[ok, what, detail] for ok, what, detail in caps]
    for ok, what, detail in caps:
        g.check(ok, what, detail)
    launch = launch_readings(g, pred, engine=engine, live_engine=live_engine)
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
        if isinstance(stage.get("field"), dict):                   # R-GATE: both sides, the verdict
            gate(g, name, stage, pred, t0=t0, launch=launch, record=record, save=save, engine=engine, **kw)
            if record.get("stopped"):
                save()
                return
            continue
        for n in range(1, int(stage["runs"]) + 1):
            g.shot_prefix = f"{name}-{n}"
            try:
                rec = one(g, name, stage, pred, n, t0=t0, **kw)
            finally:
                g.shot_prefix = ""
            record["stages"].setdefault(name, []).append(rec)
            save()
            print(f"[o4-rh] {name} run {n}: {rec['outcome']['end']} -- {rec['outcome']['why']}", flush=True)
            if not (rec["end"]["end_run"] or {}).get("ok"):
                record["stopped"] = f"{name} run {n}: end_run could not reach the title"
                save()
                return
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
