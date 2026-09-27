"""THE STORY-WRITE TRACE, RUNG 3 -- THE RETRODICTION: stock Dali against two fork chains of it, on the story's own
route, and the trace (not a human reading scripts) names what each chain gets wrong.

    py tools/play.py studies/story-trace/rung3_trace.py --label story-rung3 --timeout 240
    py studies/story-trace/rung3_trace.py --analyse <run dir>      # the analysis alone, offline, on saved traces,
                                                                   # against the predictions the session recorded
                                                                   # (--predictions FILE overrides; P-FROZEN judges it)

THE SIDES (studies/story-trace/rung3_forks.json; deployed to FF9CustomMap, ONE RELAUNCH before the session):
  S   stock Dali -- the install's scripts. Start: 359.
  F0  today's `import-chain 351 --verbatim --whole-zone`, no seed: 11 members (30831-30841), and NOT 450 (Dali/Field
      is FBG zone airp, the village vgdl). Its one defect: member(350)'s exit to 450 was left pointing at the real
      450 -- a SEAM into the real game. Start: 30841 (its 359).
  F4  the same chain seeded at beat 2600 by the round-4 kit (git d3e2f4a1): latches 2064/2075/2079 pre-set, and
      words 239 = 6 and 296 = 192 -- a 16-bit write whose high byte zeroes hub byte 297 in every member it runs in.
      Start: 30852 (its 359; its own prefix stamps SC 2600, so the warp's 2540 does not survive Main_Init).

THE SESSION: one launch, nine runs interleaved S F0 F4 x3. Each run: (the recovery ladder back to the title, except
the first) -> New Game -> `storytrace 1` -> raw `warp <start> 0 2540` -> the game's own segment 359 -> 351 -> 352
(scenes sat through, choices answered with the game's default) until control returns in 352 at SC 2600 AFTER the
wake -- the run's own trace must show the wake's SC := 2600 (F4's prefix stamps 2600 on arrival, so SC alone would
start its tour mid-night) -> the walk (dali_tour.py -- the step-1 rules; one Tour per side, over that side's chain
alone: on a fork run every rule reads the member's DONOR, the exits come from the bytes the field runs, and a seam
into the real game is crossed and toured like any other place) until SC leaves 2600, the passes run out, or the
budget does -> `storytrace 0`, verified whole. Each run's trace and log are saved as it ends
(run<i>_<side>.jsonl / run<i>_<side>_log.json), with the session record (rung3_session.json) rewritten after every
run, so a session that dies keeps every run it finished.

THE WALK IS THE PARTNER'S (predictions v2, "replay"). S and F4 runs walk the blind tour. An F0 run REPLAYS its stock
PARTNER's walk first (Tour.replay): the partner's crossings that ENTERED another field, landed or bounced back
(353), in order, in donor terms -- each step crossed by the tour's own call under its own strike rules (a retry
after a REAL failure walked from where the step began: a miss leaves him inside the zone, where a retry fires
nothing), and required to enter the partner's place -- and only then, the story still at 2600, tours blind on the
budget left. The story moving on stops it at that crossing, which is never judged: where the story's own move took
him is the fork's doing. Session 2 is why: the sides walked Dali in different ORDERS (every stock run boxed at 350
-> 355, every F0 run through it), and SByte[296] -- the countdown 450's ping arms and each room's controller steps
down -- writes the visit order into the trace, so pattern-level STOCK ONLY / FORK ONLY read a systematic order
difference as a fork difference. Replayed, the order is the same by construction. THE PAIRING: the round's F0
partners the round's S (the S just before it); a re-run F0 partners the oldest COVERED S with no covered F0 twin
yet whose walk has not already broken max_breaks replays ("replay broke": a walk that will not replay is partnered
no more, so the re-runs cannot starve on it), and when there is none S re-runs first for a fresh walk; each covered
S is partnered by at most one covered F0. An F0 whose partner is VOID -- or cannot be read -- is recorded VOID
without being driven ("partner S#k VOID"). The session record stores each F0 run's "partner" and the "walk" it was
given; the analysis checks them and recomputes every re-run's plan from the runs before it (R3-RUNS), and reads the
replay off the run's own log (coverage).

THE SHARED INSTALL IS RE-READ AROUND EVERY RUN. The members live in FF9CustomMap, which another session's
deploy_campaign replaces wholesale: before and after each run the session fingerprints what its runs rely on
(each member's registrations and ForkDonorPatch rows across the Memoria.ini folders, the sha256 of the .eb and
walkmesh it runs, the folder list, any mod override of a stock Dali script) against the fingerprint the pre-flight
passed on. A run begun on a changed install is skipped, a run the install changed under is kept but never read --
both VOID, with what changed.

COVERAGE, NOT OUTCOME, DECIDES WHAT A RUN IS (the predictions' "coverage"). A blind walker failing -- an exit gone
dead, a scene that never returned control, the budget -- says nothing about the scripts. So each run is COVERED
only when the drive gave it the chance to show what the checks read (its trace closed, the wake ran, its tour ended
its side's way, 351's lobby exit and 450's e19 exit both ran -- their unconditional stores, never the guarded
writes the checks judge -- and on S/F0 the controller flipped and Garnet moved the story on, on F4 it toured at
least as far as stock needed to; and on F0, under v2, its partner is covered and its log's replay steps ARE the
partner's walk -- or, when the story moved on during the replay, its steps before the crossing it moved on at are
the partner's first steps: that crossing is the fork's doing, not the drive's). Anything else is VOID: listed with
why, never read as a falsification. Every check reads covered runs only and is VOID -- not PASS -- while a side it
needs has fewer than min_covered. So, under v2, is R3-NULL-PRE's non-vacuity guard short on the STOCK side (too
few stock keys before 450, too few of them in every stock tour, a tour donor with none): the evidence the claim
needs does not exist, which is coverage. Short only on the F0 side -- the stock evidence there, the members writing
part of it in only SOME covered F0 runs -- it FAILs, as under v1: that is a fork difference, not too little
evidence. After the nine, a side short of covered runs RUNS AGAIN while the budget holds (S first; F0 by the
pairing; at most rerun.max); the analysis reads every run the session recorded.

THE BUDGET (the predictions' "budget", one rule for every side): a segment gets 12 min (step 1's took ~2.5), a tour
18 min (x2.2 step 1's 8.2) and at most 3 passes / 80 crossings -- an F0 run's replay and the tour after it share
its 18 min and its 80 crossings. F4 never advances (its 297 is 0), so it runs to its passes or its 18 min.
Expected (v1): S ~11 min, F0 ~11 min, F4 ~22 min -> ~2 h 12 min for the nine; measured (session 2): 9-13 min a run
on every side, F4's tours ending on their passes -- the nine in 1 h 44 min. The session is capped at 3 h: a run
starts only with 12 min left, and no tour runs past the cap (it stops "session budget spent", VOID -- a cut session
is a VOID session, never a short pass).

THE PREDICTIONS ARE FROZEN (rung3_predictions.json, v1, written before any fork-side run -- sessions 1 and 2 ran
against it; rung3_predictions_v2.json, written after session 2 and before session 3, the one a session now
registers): every check below reads its expectation from the file the session recorded and from nowhere else, and
the session records that file's path and sha256 before its first run. The analysis reads the recorded file unless
told otherwise (--predictions), refuses a file that no longer matches (P-FROZEN), so a run cannot be read to fit,
and refuses outright to read a session whose F0 runs are not replays against v2 (NotReplays) -- never a verdict.

P-CAP       the engine advertises the story trace at proto 1
P-MANIFEST  the frozen member sets are the deployed chains' (rung3_forks.json)
P-DEPLOY    every member is registered exactly once across the Memoria.ini folders, under its name, and
            ForkDonorPatch maps it to its donor, once
P-FLOOR     every member's deployed walkmesh is its donor's stock walkmesh (what the tour routes on)
P-EXITS     every member's running exits are its donor's with only the targets remapped INTO ITS OWN CHAIN
P-STOCK     no mod folder overrides a stock Dali script (else the stock side is not stock)
P-FROZEN    the predictions the analysis reads are the ones the session recorded
R3-RUNS     the frozen nine in order, then re-runs only; every trace keeps the contract; (v2) the pairing is the
            registered one, and every re-run the plan names from the runs before it; >= min_covered covered runs
            per side (VOID short of that)
R3-DONOR    every member row names its donor, every real row itself; no side strays into another's ids
R3-JOIN     0 join failures, no note: every script row joins a store in the bytes its side ran
R3-PING     stock: Bit[2102] := 1 in every covered run, and WRITERS names only 450 for it
R3-NULL-PRE F0: nothing stock writes before 450 is missing from the members -- rung 2 at zone scale, and at
            TOUR scale (keys first written in the tour, from its member donors), not just the scripted segment;
            (v2) its non-vacuity guard short on the STOCK side, nothing missing: VOID; short only on F0's: FAIL
R3-SEAM     F0: every covered run reaches 450 only across member(350)'s seam; the ping is REACHED ONLY ACROSS A
            SEAM, and written by no F0 donor
R3-MIRROR   F0: FORK ONLY and STOCK ONLY empty, no clobber
R3-ADVANCE  F0 leaves SC 2600 in a real field, across the seam; F4 never does
R3-LATCH    F4: the hub-gated writes are STOCK ONLY; the CLOBBER report names byte 297; F4 did reach the real 450
            and walk its e19 exit (not vacuous)
R3-PREEMPT  F4: PRE-EMPTED names the latches 2064/2079/2075 beside the stock writers that set them themselves
NC-THROW
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dali_tour as D  # noqa: E402
from dali_tour import T  # noqa: E402

PREDICTIONS_V1 = HERE / "rung3_predictions.json"      # sessions 1 and 2 (sha 220532a8); FROZEN, never edited
PREDICTIONS = HERE / "rung3_predictions_v2.json"       # what a session registers now: F0 replays its partner
MANIFEST = HERE / "rung3_forks.json"
SESSION_FILE = "rung3_session.json"
SIDES = ("S", "F0", "F4")
DALI_STOCK = (312, *range(350, 360), 450)
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "StoryTrace", "HarnessAgent")


# ======================================================================== the frozen predictions
def load_predictions(path: Path = PREDICTIONS) -> tuple:
    """``(predictions, sha256 of the file's bytes)``."""
    data = Path(path).read_bytes()
    return json.loads(data.decode("utf-8")), hashlib.sha256(data).hexdigest()


def recorded_predictions(session: dict) -> Path:
    """The predictions file a session recorded before its first run: its ``predictions`` path, or the file of that
    name here when the path is gone (another worktree's); a record that names none predates the path and ran v1.
    P-FROZEN still judges the bytes against the recorded sha256."""
    named = session.get("predictions")
    if not named:
        return PREDICTIONS_V1
    p = Path(named)
    return p if p.is_file() else HERE / p.name


class NotReplays(ValueError):
    """Predictions that pair F0 with a stock partner (v2 "replay") asked to read a session whose F0 runs are not
    replays: refused, never a verdict -- such a session is read against the file it recorded."""


def replaying(pred: dict) -> bool:
    """Do these predictions have F0 replay its stock partner's walk (v2)?"""
    return bool(pred.get("replay"))


def round_partner(order: list, i: int) -> int | None:
    """The stock run a frozen-order F0 at run ``i`` partners: its round's S, the nearest S before it in ``order``.
    None past the frozen order: a re-run has no round (rerun_plan names its partner)."""
    if i > len(order):
        return None
    return next((j for j in range(i - 1, 0, -1) if order[j - 1] == "S"), None)


def short_sides(runs: list, pred: dict) -> list:
    """The sides with fewer than min_covered covered runs, in SIDES order."""
    n = pred["coverage"]["min_covered"]
    return [s for s in SIDES if sum(1 for r in runs if r["side"] == s and not r["why_void"]) < n]


def broken_on(runs: list) -> Counter:
    """How many F0 replays each stock run's walk has broken: ``{partner i: n}`` over the F0 runs that stopped "replay
    broke" (a step entered another place, struck out, or left him elsewhere) -- the walk's own failures, never a
    budget, an error or a segment that handed back no control."""
    return Counter(r["rec"].get("partner") for r in runs if r["side"] == "F0" and _stop(r).startswith("replay broke"))


def untwinned(runs: list, max_breaks: int | None = None) -> list:
    """The covered stock runs no covered F0 run partners yet, oldest first (their ``i``) -- less those whose walk has
    broken ``max_breaks`` replays already (v2 "replay".max_breaks): a walk that will not replay is partnered no more,
    so the re-runs cannot starve on it."""
    twinned = {r["rec"].get("partner") for r in runs if r["side"] == "F0" and not r["why_void"]}
    broke = broken_on(runs) if max_breaks is not None else Counter()
    return [r["i"] for r in runs if r["side"] == "S" and not r["why_void"] and r["i"] not in twinned
            and (max_breaks is None or broke[r["i"]] < max_breaks)]


def rerun_plan(runs: list, pred: dict) -> tuple | None:
    """What runs next after the nine, from the judged runs (:func:`judge`): ``(side, partner)``, or None when no side
    is short. S first when it is short (every comparison and F4's crossing floor read it); then F0 -- under v2
    partnering the oldest covered stock run with no covered F0 twin whose walk has not broken ``max_breaks`` replays,
    and when there is none, S runs first to give it a fresh walk; then F4. ``partner`` is None but for an F0 re-run
    under v2. R3-RUNS recomputes this plan for every re-run from the runs before it (:func:`pairing_faults`), so a
    session that ran anything else FAILs it."""
    short = short_sides(runs, pred)
    if not short:
        return None
    if short[0] == "F0" and replaying(pred):
        free = untwinned(runs, pred["replay"].get("max_breaks"))
        return ("F0", free[0]) if free else ("S", None)
    return (short[0], None)


def chain_members(pred: dict) -> dict:
    """``{"F0": {fork id: donor}, "F4": {...}}`` as the predictions froze them."""
    return {side: {int(f): int(d) for f, d in m.items()} for side, m in pred["members"].items()}


def run_names(i: int, side: str) -> tuple:
    return f"run{i}_{side}.jsonl", f"run{i}_{side}_log.json"


def tours(chains: dict, *, scripts=None, stock=None) -> dict:
    """One :class:`dali_tour.Tour` per side, each over its OWN chain (S: none) -- so a member whose exit leads into
    another chain's ids is refused by its side's gateways(), not read as its donor's exit."""
    return {side: D.Tour(members=chains.get(side, {}), scripts=scripts, stock=stock, tag="rung3") for side in SIDES}


# ======================================================================== pre-flight (pure, offline)
def _fork_donor_rows(root: Path) -> list:
    """``[(fork id, donor)]`` of one mod root's ForkDonorPatch.txt, in file order."""
    try:
        text = (root / "ForkDonorPatch.txt").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for ln in text.splitlines():
        p = ln.split("#", 1)[0].split()
        if len(p) >= 2 and p[0].isdigit() and p[1].isdigit():
            out.append((int(p[0]), int(p[1])))
    return out


def _deployed_walkmesh(root: Path, fid: int):
    """The .bgi bytes mod root ``root`` ships for field ``fid`` (its FieldScene line's FBG_N<area>_<map>), or None."""
    from ff9mapkit.config import ModLayout
    try:
        text = (root / "DictionaryPatch.txt").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for ln in text.splitlines():
        p = ln.split()
        if len(p) >= 5 and p[0] == "FieldScene" and p[1] == str(fid) and p[2].isdigit():
            fbg = f"FBG_N{int(p[2]):02d}_{p[3]}"
            path = ModLayout(root).fieldmap_dir(fbg) / f"{fbg}.bgi.bytes"
            return path.read_bytes() if path.is_file() else None
    return None


def preflight(pred: dict, roots: list, stock, sides: dict, manifest: Path = MANIFEST) -> list:
    """The checks that must hold before two hours are spent on a session: ``[(ok, what, detail)]``. ``sides`` =
    :func:`tours` -- P-EXITS reads each chain through its own side's Tour."""
    from ff9mapkit.scene.bgi import BgiWalkmesh
    from ff9mapkit import extract
    out = []
    want = chain_members(pred)
    every = {f: d for m in want.values() for f, d in m.items()}
    man = json.loads(Path(manifest).read_text(encoding="utf-8"))
    got = {side: {int(f): int(d) for f, d in man["chains"][side]["members"].items()} for side in want}
    out.append((got == want, "P-MANIFEST: the frozen member sets are the deployed chains' (rung3_forks.json)",
                f"frozen {want} / manifest {got}" if got != want else f"{len(every)} members"))
    names = {int(f): n for side in man["chains"].values() for f, n in side["names"].items()}
    regs = [(Path(r), T.mod_registrations(r)) for r in roots]
    rows = [(Path(r), f, d) for r in roots for f, d in _fork_donor_rows(Path(r))]
    bad = []
    for fid, donor in sorted(every.items()):
        hits = [(r.name, reg[fid]) for r, reg in regs if fid in reg]
        if len(hits) != 1 or hits[0][1] != names.get(fid):
            bad.append(f"{fid}: registered {hits}, want once as {names.get(fid)}")
        fdp = [(r.name, d) for r, f, d in rows if f == fid]
        if fdp != [(fdp[0][0] if fdp else "", donor)]:
            bad.append(f"{fid}: ForkDonorPatch rows {fdp}, want one -> {donor}")
    out.append((not bad, "P-DEPLOY: every member registered once across the Memoria.ini folders under its name, and "
                         "mapped once to its donor in ForkDonorPatch", "; ".join(bad[:6]) or f"{len(every)} members"))
    bad = []
    for fid, donor in sorted(every.items()):
        mine = [b for b in (_deployed_walkmesh(Path(r), fid) for r in roots) if b is not None]
        if len(mine) != 1:
            bad.append(f"{fid}: {len(mine)} deployed walkmeshes")
        elif BgiWalkmesh.from_bytes(mine[0]).to_bytes() != extract.stock_walkmesh(donor).to_bytes():
            bad.append(f"{fid}: its walkmesh is not donor {donor}'s")
    out.append((not bad, "P-FLOOR: every member's deployed walkmesh is its donor's stock walkmesh -- the floor the "
                         "tour routes on", "; ".join(bad[:6]) or f"{len(every)} members, each its donor's"))
    bad = []
    for side, members in want.items():
        for fid in sorted(members):
            try:
                sides[side].gateways(fid)
            except D.TourError as err:
                bad.append(f"{side} {str(err)[:200]}")
    out.append((not bad, "P-EXITS: every member's running exits are its donor's with only the targets remapped, "
                         "each into its own chain", "; ".join(bad[:3]) or f"{len(every)} members"))
    over = {fid: [r.name for r in T.stock_overrides(fid, roots)] for fid in DALI_STOCK}
    over = {f: v for f, v in over.items() if v}
    out.append((not over, "P-STOCK: no mod folder overrides a stock Dali script (312, 350-359, 450)", str(over)))
    return out


def fingerprint(roots: list, every: dict) -> dict:
    """What the session's runs rely on in the SHARED install, read fresh: the Memoria.ini folders, and per member
    its registrations and ForkDonorPatch rows across them and the sha256 of the .eb and walkmesh it runs; and the
    mod overrides of stock Dali scripts. JSON-shaped, so two reads compare with ``==``."""
    def sha(data) -> str | None:
        return hashlib.sha256(data).hexdigest() if data is not None else None

    fresh = T.mod_script_source(roots)
    regs = [(Path(r).name, T.mod_registrations(r)) for r in roots]
    rows = [(Path(r).name, f, d) for r in roots for f, d in _fork_donor_rows(Path(r))]
    out = {"folders": [Path(r).name for r in D.mod_roots()],
           "stock": {str(f): [r.name for r in T.stock_overrides(f, roots)] for f in DALI_STOCK}}
    for fid in sorted(every):
        try:
            idx = fresh(fid)
            eb = sha(idx.data) if idx is not None else None
        except T.TraceError as err:
            eb = f"unreadable: {str(err)[:120]}"
        out[str(fid)] = {"reg": [[n, reg[fid]] for n, reg in regs if fid in reg],
                         "fdp": [[n, d] for n, f, d in rows if f == fid], "eb": eb,
                         "bgi": [sha(b) for b in (_deployed_walkmesh(Path(r), fid) for r in roots) if b is not None]}
    return out


def _changed(before: dict, now: dict) -> str:
    """The fingerprint entries that differ, named -- "" when none."""
    keys = [k for k in sorted(set(before) | set(now)) if before.get(k) != now.get(k)]
    return (f"{len(keys)} changed: " + ", ".join(keys[:8])) if keys else ""


# ======================================================================== the session
def run(g) -> None:
    from harness import HarnessError

    cap = g.state.storytrace
    if not g.check(isinstance(cap, dict) and cap.get("proto") == T.PROTO,
                   "P-CAP: the engine advertises the story trace at proto 1", str(cap)):
        return
    pred, sha = load_predictions()
    b, wk = pred["budget"], pred["wake"]
    chains = chain_members(pred)
    every = {f: d for m in chains.values() for f, d in m.items()}
    stock = T.stock_script_source()
    roots = D.mod_roots()
    ran = T.mod_script_source(roots, fallback=stock)
    side_tours = tours(chains, scripts=ran, stock=stock)
    pre = preflight(pred, roots, stock, side_tours)
    for ok, what, detail in pre:
        g.check(ok, what, detail)
    if not all(ok for ok, _w, _d in pre):
        return                      # hours on a chain that is not the one the predictions name would prove nothing
    fp0 = fingerprint(roots, every)
    scripts = g.run_dir / "scripts"   # the bytes each member ran, kept: the analysis outlives the deploy
    scripts.mkdir(exist_ok=True)
    for fid in sorted(every):
        (scripts / f"{fid}.eb").write_bytes(ran(fid).data)
    session = {"label": g.run_dir.name, "predictions": str(PREDICTIONS), "predictions_sha256": sha,
               "predictions_version": pred.get("version", 1), "order": pred["order"], "budget": b,
               "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "install": fp0, "runs": []}

    def save() -> None:
        (g.run_dir / SESSION_FILE).write_text(json.dumps(session, indent=1), encoding="utf-8")

    save()
    mark = g.log_mark()
    t0 = time.time()
    deadline = t0 + b["session_s"]

    def partner_walk(k: int | None) -> tuple:
        """``(walk, why not)`` for an F0 partnering stock run ``k``: that run judged by the frozen coverage rule
        (read_session, the analysis's own reading) -- its entered walk when it is covered, else why the F0 is VOID.
        Reading every recorded run before each F0 must not cost the session: whatever that read raises makes this
        one F0 VOID (unread partner), never the runs after it."""
        if k is None:
            return None, "no stock run before it to partner"
        try:
            runs = {r["i"]: r for r in read_session(g.run_dir, pred, stock=stock, roots=roots, session=session)}
            p = runs.get(k)
            if p is None or p["side"] != "S":
                return None, f"its partner #{k} is not a recorded stock run"
            if p["why_void"]:
                return None, f"partner S#{k} VOID: {'; '.join(p['why_void'])[:200]}"
            return D.entered_walk(p["log"]["log"]), None
        except Exception as err:                  # noqa: BLE001 -- one unreadable record must not end the session
            return None, f"partner S#{k} unreadable: {type(err).__name__}: {str(err)[:200]}"

    def one(i: int, side: str, rerun: bool = False, partner: int | None = None) -> None:
        tour = side_tours[side]
        trace_name, log_name = run_names(i, side)
        rec = {"i": i, "side": side, "start": pred["start"][side], "trace": trace_name, "log": log_name}
        if rerun:
            rec["rerun"] = True
        walk = None
        if side == "F0" and replaying(pred):
            # THE PAIRING, at the call site: a round's F0 partners its round's S; a re-run F0 the partner the
            # re-run plan chose (rerun_plan: a covered S with no covered twin). A VOID partner is not driven.
            rec["partner"] = partner if rerun else round_partner(pred["order"], i)
            walk, why = partner_walk(rec["partner"])
            if walk is None:
                rec["skipped"] = why
            else:
                rec["walk"] = walk
        if not rec.get("skipped"):
            if time.time() + b["run_min_s"] > deadline:
                rec["skipped"] = f"session budget: under {b['run_min_s']}s of the {b['session_s']}s left"
            else:
                moved = _changed(fp0, fingerprint(roots, every))
                if moved:
                    rec["install"] = "before the run: " + moved
        if rec.get("skipped") or rec.get("install"):
            session["runs"].append(rec)
            save()
            tour.say(f"run {i} ({side}) VOID, not run: {rec.get('skipped') or rec['install']}")
            return
        log: list = []
        stop = "not reached"
        smark = None
        rec["t0"] = round(time.time() - t0)
        g.shot_prefix = f"run{i}-{side}"
        try:
            if i > 1:
                ok, why = g.restore_baseline()
                if not ok:
                    raise HarnessError(f"between runs, the title could not be restored: {why}")
            g.newgame()
            g.wait_frames(30)
            smark = g.story_mark()
            before = len(g.channel.story_text() or "")
            g.storytrace(True)
            seen = {"n": -1, "rows": []}

            def live_rows() -> list:
                """This run's rows so far, parsed once per growth of the file (an append in flight held back)."""
                text = g.channel.story_text() or ""
                tail = text[before:] if len(text) >= before else text
                if len(tail) != seen["n"]:
                    try:
                        seen["rows"] = T.parse_text(tail[:tail.rfind("\n") + 1], live=True)
                    except T.TraceError:
                        seen["rows"] = []
                    seen["n"] = len(tail)
                return seen["rows"]

            def engine_donor(fid: int):
                """The donor this run's own trace rows name for ``fid`` (the engine's ForkDonorPatch), or None."""
                dons = [r.don for r in live_rows() if r.fld == fid and r.k != "c"]
                return dons[-1] if dons else None

            def woke() -> bool:
                """The run's own trace shows the wake: 352's SC := beat (e17 tag 1), in its place on this side."""
                return any(r.k == "w" and tour.place(r.fld) == wk["donor"] and r.sid == wk["sid"] and r.tag == wk["tag"]
                           and r.target == wk["target"] and r.new in wk["value"] for r in live_rows())

            seg = D.segment(g, log, start=pred["start"][side], sc=pred["start_sc"], beat=pred["beat"],
                            place=tour.place, until=pred["segment_place"], timeout=b["segment_s"], woke=woke)
            rec["segment"] = seg
            tour.say(f"run {i} ({side}) segment: {json.dumps(seg)}")
            if seg["ok"] and walk is not None:
                stop = tour.replay(g, log, walk, beat=pred["beat"], max_crossings=b["max_crossings"],
                                   max_passes=b["max_passes"], budget_s=b["tour_s"], deadline=deadline,
                                   engine_donor=engine_donor)
            elif seg["ok"]:
                stop = tour.run(g, log, beat=pred["beat"], max_crossings=b["max_crossings"],
                                max_passes=b["max_passes"], budget_s=b["tour_s"], deadline=deadline,
                                engine_donor=engine_donor)
            if seg["ok"]:
                try:                # Garnet's scene, sat through before the trace closes: the tour's stop stands
                    D.settle(g, log, "after the tour", tour.say)
                except HarnessError as err:
                    rec["settle_error"] = str(err)[:300]
            else:
                stop = f"segment: no control in {pred['segment_place']} at {pred['beat']} after the wake"
        except (HarnessError, D.TourError) as err:
            stop = f"STOPPED: {type(err).__name__}: {str(err)[:300]}"
        except Exception as err:                  # noqa: BLE001 -- one run's bug must not cost the other eight
            stop = f"STOPPED (unexpected): {type(err).__name__}: {str(err)[:300]}"
            log.append({"k": "error", "traceback": traceback.format_exc()[-3000:]})
            tour.say(f"!! run {i} ({side}) raised: {traceback.format_exc()[-1500:]}")
        finally:
            g.shot_prefix = ""
            if smark is not None:
                try:
                    rec["traced"] = g.collect_story(g.run_dir / trace_name, smark)
                except HarnessError as err:
                    rec["trace_error"] = str(err)[:300]
            crossings = [x for x in log if x["k"] == "cross"]
            # landed: the crossings that landed where their exit leads, tour ("crossed") and replay alike
            rec.update(stop=stop, t1=round(time.time() - t0), crossings=len(crossings),
                       landed=sum(1 for x in crossings if x.get("landed") is not None and x["landed"] == x.get("to")),
                       fields=sorted({x["now"] for x in crossings if x.get("now")}))
            if walk is not None:
                rec["replayed"] = sum(1 for x in crossings if x.get("verdict") == "replayed")
            moved = _changed(fp0, fingerprint(roots, every))
            if moved:
                rec["install"] = "during the run: " + moved
            choices = [dict(c, why=x["why"]) for x in log if x["k"] == "scene" for c in x.get("choices", [])]
            (g.run_dir / log_name).write_text(json.dumps({"stop": stop, "choices": choices, "log": log}, indent=1),
                                              encoding="utf-8")
            session["runs"].append(rec)
            save()
            tour.say(f"run {i} ({side}) done at {rec['t1']}s: {stop}" + (f" -- VOID: {moved}" if moved else ""))

    for i, side in enumerate(pred["order"], 1):
        one(i, side)
    reruns = 0
    while reruns < pred["rerun"]["max"]:
        try:
            runs = read_session(g.run_dir, pred, stock=stock, roots=roots, session=session)
            plan = rerun_plan(runs, pred)
        except Exception as err:                  # noqa: BLE001 -- the nine are kept and analysed all the same
            session["rerun_stop"] = (f"the runs could not be read to plan a re-run: {type(err).__name__}: "
                                     f"{str(err)[:200]}")
            side_tours["S"].say(f"!! re-runs stopped: {traceback.format_exc()[-1500:]}")
            break
        if plan is None:
            break
        if time.time() + b["run_min_s"] > deadline:
            session["rerun_stop"] = (f"sides {short_sides(runs, pred)} still short of covered runs, and no run fits "
                                     f"the budget left")
            break
        reruns += 1
        one(len(session["runs"]) + 1, plan[0], rerun=True, partner=plan[1])
    session["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    checks, reports = analyse(g.run_dir, stock=stock, roots=roots)
    for name, text in reports.items():
        (g.run_dir / name).write_text(text, encoding="utf-8")
    print(reports.get("rung3_summary.txt", "")[:4000], flush=True)
    for ok, what, detail in checks:
        g.check(ok is True, what, ("VOID -- " if ok is None else "") + detail)
    every_exc = g.exceptions_since(mark)
    ours = [e for e in every_exc if e.name in THROWS
            and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
    g.check(not ours, "NC-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
            str([(e.name, e.where) for e in ours[:5]]))


# ======================================================================== reading a session (pure, offline)
def _matches(pat: dict, k) -> bool:
    """A frozen pattern against a WriteKey: every field the pattern names must agree (``off``/``value`` lists are
    alternatives)."""
    return (k.target == pat["target"] and k.value in pat["value"]
            and all(getattr(k, f) == pat[f] for f in ("donor", "sid", "tag") if f in pat)
            and ("off" not in pat or k.off in pat["off"]))


def _has(d, pat) -> bool:
    """The run wrote a key matching ``pat`` -- in a member or across a seam alike."""
    return any(_matches(pat, k) for k in (*d.keys, *d.seam_keys))


def _first_line(rows, pred) -> int | None:
    """The line of the first placed row (not a count) satisfying ``pred``, or None."""
    return next((r.line for r in rows if r.k != "c" and pred(r)), None)


def from_start(rows, start: int) -> tuple:
    """``(rows, fields)``: one run's rows from its first row in its start field on -- every epoch row kept, the
    ``w``/``r`` rows before it dropped with the count rows of their sites -- and the fields those stood in. They
    are New Game's and the harness's (field 70, and wherever the New Game override leads before the raw warp),
    read on neither side. A run that never stood in ``start`` is returned whole."""
    cut = next((i for i, r in enumerate(rows) if r.k in ("w", "r") and r.fld == start), None)
    if cut is None:
        return list(rows), []
    kept, live = [], set()          # live: the sites the current epoch kept a row at -- its counts fold onto them
    for i, r in enumerate(rows):
        if r.k == "e":
            kept.append(r)
            live = set()
        elif r.k == "c":
            if r.site in live:
                kept.append(r)
        elif i >= cut:
            kept.append(r)
            if r.k == "w":
                live.add(r.site)
    return kept, sorted({r.fld for r in rows[:cut] if r.k in ("w", "r")})


def wake_line(d, pred) -> int | None:
    """The line of the wake's own store (352's SC := beat, e17 tag 1) in a digested run, or None."""
    lines = [o.at for k, o in d.keys.items() if _matches(pred["wake"], k)]
    return min(lines) if lines else None


def tour_line(rows, d, pred, members: dict) -> int | None:
    """Where the TOUR began in a run's rows: the first placed row after the wake in a place other than 352 (the
    tour's first crossing out of the room the segment handed control back in), or None."""
    w = wake_line(d, pred)
    if w is None:
        return None
    return _first_line(rows, lambda r: r.line > w and members.get(r.fld, r.fld) != pred["wake"]["donor"])


def read_run(run_dir: Path, rec: dict, pred: dict, chains: dict, ran, stock) -> dict:
    """One recorded run, read: ``{i, side, label, rec, rows, pre, log, digest, broken, void}``. ``broken`` = what
    breaks the instrument (a trace off the row contract: the check FAILS); ``void`` = why the drive left nothing to
    read (a skip, the install moving, no trace). The rows are :func:`from_start`'s."""
    i, side = rec["i"], rec["side"]
    trace_name, log_name = run_names(i, side)
    r = {"i": i, "side": side, "label": f"{side}#{i}", "rec": rec, "rows": None, "pre": [], "log": None,
         "digest": None, "broken": [], "void": []}
    if rec.get("skipped") or rec.get("install"):
        r["void"].append(rec.get("skipped") or f"the install changed {rec['install']}")
        return r                        # a run the install moved under is never read: its bytes are not the snapshot's
    tp, lp = run_dir / rec.get("trace", trace_name), run_dir / rec.get("log", log_name)
    if tp.is_file():
        try:
            split = T.split_runs(T.read_trace(tp))
        except T.TraceError as err:
            split = None
            r["broken"].append(f"its trace breaks the row contract ({str(err)[:100]})")
        if split is not None and len(split) != 1:
            r["broken"].append(f"{len(split)} traced runs in its file")
        elif split is not None:
            r["rows"], r["pre"] = from_start(split[0], pred["start"][side])
    else:
        r["void"].append("no trace")
    if lp.is_file():
        r["log"] = json.loads(lp.read_text(encoding="utf-8"))
    else:
        r["void"].append("no log")
    if r["rows"] is not None:
        try:
            r["digest"] = T.digest(r["label"], r["rows"], scripts=ran, donor_scripts=stock, members=chains.get(side))
        except T.TraceError as err:
            r["broken"].append(f"cannot be digested ({str(err)[:100]})")
    return r


def _stop(r) -> str:
    return str((r.get("log") or {}).get("stop", r["rec"].get("stop", "")))


def _void_why(r, pred, chains, floor) -> list:
    """Why run ``r`` is VOID by the frozen coverage rule (``pred["coverage"]``) -- [] when it is covered."""
    C = pred["coverage"]
    out = list(r["void"]) + list(r["broken"])
    d, rows, side = r["digest"], r["rows"], r["side"]
    if d is None:
        return out or ["not read"]
    if d.incomplete:
        out.append("INCOMPLETE (no `off`)")
    if not any(x.fld == pred["start"][side] for x in rows if x.k != "c"):
        out.append(f"never stood in its start field {pred['start'][side]}")
    segs = [x for x in (r["log"] or {}).get("log", []) if x.get("k") == "segment"]
    if not (segs and segs[-1].get("ok")):
        out.append(f"the segment handed back no control in {pred['segment_place']} at {pred['beat']}")
    if wake_line(d, pred) is None:
        out.append("the trace shows no wake")
    stop = _stop(r)
    if not any(stop.startswith(s) for s in C["clean_stop"][side]):
        out.append(f"stopped: {stop[:120]}")
    out += [f"{p['name']}: never" for p in C["ran"] if not _has(d, p)]
    if side in C["advancing"]:
        if not _has(d, C["flip"]):
            out.append(f"{C['flip']['name']}: never")
        if not any(x.sc >= C["advanced_sc"] for x in rows if x.k != "c"):
            out.append(f"the story never reached SC {C['advanced_sc']}")
    if side in C["floor"] and any(stop.startswith(s) for s in C["floor_stops"]):
        n = sum(1 for x in (r["log"] or {}).get("log", []) if x.get("k") == "cross")
        if floor is None:
            out.append("no covered stock run sets the crossing floor")
        elif n < floor:
            out.append(f"toured {n} crossings, under the {floor} a covered stock run needed to move on")
    return out


def _replay_why(r, by_i: dict, pred, chains) -> list:
    """Why F0 run ``r`` is not a replay of a covered partner (v2 "replay", its coverage clause) -- [] when it is:
    its recorded partner must be an earlier stock run, covered, and the replay steps its own log records --
    ``[place, exit, entered place]`` of every replay crossing that entered a field, in order -- must BE the partner's
    entered walk; or, when the story moved on during the replay (the run stopped "SC left" -- coverage has the trace
    show the advance), its steps BEFORE the crossing the story moved on at must be the partner's first steps. That
    crossing itself is never judged -- where the story's own move took him is the fork's doing -- and a flip that
    came between crossings (no replay crossing settled off the beat) leaves every step recorded to be judged."""
    if r["rec"].get("skipped") or r["rec"].get("install"):
        return []                                  # never driven: VOID already, and the skip says why
    k = r["rec"].get("partner")
    p = by_i.get(k)
    if not isinstance(k, int) or p is None or p["side"] != "S" or k >= r["i"]:
        return [f"not a replay: its partner {k} is not an earlier stock run"]
    if p["why_void"]:
        return [f"partner S#{k} VOID"]
    if r["log"] is None or p["log"] is None:
        return []                                  # no log: VOID already, and said so ("no log")
    want = D.entered_walk(p["log"]["log"])
    steps = [x for x in r["log"]["log"] if x.get("k") == "cross" and x.get("leg") == "replay"]
    got = D.entered_walk(steps, chains.get("F0"))
    if got == want:
        return []
    moved = _stop(r).startswith("SC left")
    if moved:
        at = next((j for j, x in enumerate(steps) if x.get("sc1", pred["beat"]) != pred["beat"]), len(steps))
        got = D.entered_walk(steps[:at], chains.get("F0"))
        if got == want[:len(got)]:
            return []
    bad = next((j for j, (a, b) in enumerate(zip(got, want)) if a != b), None)
    if bad is not None:
        return [f"its replay of S#{k}'s walk diverged at step {bad + 1}: {D.step_name(got[bad])}, not "
                f"{D.step_name(want[bad])}"]
    return [f"it replayed {len(got)} of the {len(want)} steps of S#{k}'s walk"]


def crossing_floor(stock_runs, pred) -> int | None:
    """The most crossings any covered stock run needed before SC reached the advance (its log's first crossing
    whose settled SC is there), or None with no such run."""
    need = [next((x["n"] for x in (r["log"] or {}).get("log", []) if x.get("k") == "cross"
                  and x.get("sc1", 0) >= pred["coverage"]["advanced_sc"]), None) for r in stock_runs]
    need = [n for n in need if n is not None]
    return max(need) if need else None


def judge(runs: list, pred: dict) -> list:
    """Judge read runs (:func:`read_run` dicts) by the frozen coverage rule, in place: each gets ``why_void`` (the
    rule's reasons, [] = covered). S is judged first, then F0 (under v2 its coverage reads its partner's), then F4
    (its crossing floor reads the covered stock runs) -- over ``runs`` alone, so the runs a session had recorded when
    it planned a re-run are judged as it judged them."""
    chains = chain_members(pred)
    by_i = {r["i"]: r for r in runs}
    for side in ("S", "F0"):
        for r in runs:
            if r["side"] == side:
                r["why_void"] = _void_why(r, pred, chains, None)
                if side == "F0" and replaying(pred):
                    r["why_void"] += _replay_why(r, by_i, pred, chains)
    floor = crossing_floor([r for r in runs if r["side"] == "S" and not r["why_void"]], pred)
    for r in runs:
        if r["side"] == "F4":
            r["why_void"] = _void_why(r, pred, chains, floor)
    return runs


def read_session(run_dir, pred: dict, *, stock, roots, session: dict | None = None) -> list:
    """Every run the session recorded, read (:func:`read_run`) and judged (:func:`judge`)."""
    run_dir = Path(run_dir)
    session = session or json.loads((run_dir / SESSION_FILE).read_text(encoding="utf-8"))
    chains = chain_members(pred)
    snap = {int(p.stem): p.read_bytes() for p in (run_dir / "scripts").glob("*.eb")}
    ran = T.mod_script_source(roots, fallback=stock, explicit=snap)
    return judge([read_run(run_dir, rec, pred, chains, ran, stock) for rec in session.get("runs", [])], pred)


def pairing_faults(runs: list, pred: dict) -> list:
    """Where the session broke the registered pairing (v2 "replay".partner) -- [] when it kept it. Every F0 run
    names an earlier stock run as its partner; a frozen-order F0 its round's S; the walk the session gave it is that
    partner's entered walk, read off the partner's log now; no covered stock run has two covered F0 twins; and every
    re-run is the one the plan names (:func:`rerun_plan`) from the runs recorded before it, judged as the session
    judged them then -- S first while S is short, an F0 on the oldest untwinned stock run whose walk has not broken
    max_breaks replays, S for a fresh walk when there is none. A session's own rule broken is the instrument's fault:
    it FAILs R3-RUNS, never a VOID."""
    order = pred["order"]
    by_i = {r["i"]: r for r in runs}
    out = []
    for r in runs:
        if r["side"] != "F0":
            continue
        k = r["rec"].get("partner")
        p = by_i.get(k)
        if not isinstance(k, int) or p is None or p["side"] != "S" or k >= r["i"]:
            out.append(f"{r['label']}'s partner {k} is not an earlier stock run")
            continue
        own = round_partner(order, r["i"])
        if r["i"] <= len(order) and k != own:
            out.append(f"{r['label']} partners S#{k}, not its round's S#{own}")
        if "walk" in r["rec"] and p["log"] is not None and r["rec"]["walk"] != D.entered_walk(p["log"]["log"]):
            out.append(f"{r['label']} was given a walk that is not S#{k}'s")
    twins = Counter(r["rec"].get("partner") for r in runs if r["side"] == "F0" and not r["why_void"])
    out += [f"S#{k} is partnered by {n} covered F0 runs" for k, n in sorted(twins.items()) if n > 1]
    for r in runs:
        if r["i"] <= len(order):
            continue
        plan = rerun_plan(judge([dict(x) for x in runs if x["i"] < r["i"]], pred), pred)
        ran = (r["side"], r["rec"].get("partner") if r["side"] == "F0" and replaying(pred) else None)
        if plan != ran:
            out.append(f"{r['label']} re-ran {ran[0]}" + (f" on S#{ran[1]}" if ran[1] is not None else "")
                       + (f", where the plan named {plan[0]}" + (f" on S#{plan[1]}" if plan[1] is not None else "")
                          if plan else ", where no side was short"))
    return out


def _places(rows, members: dict) -> str:
    """The run's field visits in order, as places: a member by its donor, and on a fork run a real field starred
    ("... 350 450* 350* ...": the run is across a seam, in the real game)."""
    out, last = [], None
    for r in rows:
        if r.k != "c" and r.fld != last:
            last = r.fld
            out.append(str(members[r.fld]) if r.fld in members
                       else f"{r.fld}*" if members and T.real_field(r.fld) and r.fld != 70 else str(r.fld))
    return " ".join(out)


# ======================================================================== the analysis (pure, offline)
def analyse(run_dir, *, pred_path: Path | None = None, stock=None, roots=None) -> tuple:
    """The rung's checks over one session's saved traces and logs: ``([(ok, what, detail)], {file name: text})``,
    ``ok`` True (PASS), False (FAIL) or None (VOID: a side it needs has too few covered runs to say). Pure given
    the install and the session dir (the members' .eb come from the session's own snapshot when it has one, so
    the analysis outlives the deploy). The predictions are the file the session recorded
    (:func:`recorded_predictions`) unless ``pred_path`` overrides it -- P-FROZEN judges either against the recorded
    sha256 -- and predictions that pair F0 with a stock partner (v2) refuse a session whose F0 runs are not replays:
    :class:`NotReplays`, never a verdict."""
    run_dir = Path(run_dir)
    session = json.loads((run_dir / SESSION_FILE).read_text(encoding="utf-8"))
    pred_path = recorded_predictions(session) if pred_path is None else Path(pred_path)
    pred, sha = load_predictions(pred_path)
    replay = replaying(pred)
    if replay:
        bare = [f"F0#{x.get('i')}" for x in session.get("runs", []) if x.get("side") == "F0" and "partner" not in x]
        if bare:
            raise NotReplays(
                f"session {session.get('label')}: F0 runs are not replays -- {', '.join(bare)} name no stock partner, "
                f"so they walked their own blind tours and the sides' orders were never paired; {pred_path.name} "
                f"(predictions v{pred.get('version')}) reads only a session whose every F0 run replayed its partner's "
                f"walk. This session recorded {Path(str(session.get('predictions') or PREDICTIONS_V1)).name} "
                f"(sha {str(session.get('predictions_sha256'))[:8]}): analyse it against that file")
    C, n_min = pred["checks"], pred["coverage"]["min_covered"]
    out = []
    out.append((session.get("predictions_sha256") == sha,
                "P-FROZEN: the predictions this analysis reads are the ones the session recorded before its first run",
                f"session {str(session.get('predictions_sha256'))[:16]} / file {sha[:16]}"))
    chains = chain_members(pred)
    stock = stock or T.stock_script_source()
    roots = D.mod_roots() if roots is None else roots
    runs = read_session(run_dir, pred, stock=stock, roots=roots, session=session)
    cov = {s: [r for r in runs if r["side"] == s and not r["why_void"]] for s in SIDES}
    dig = {s: [r["digest"] for r in cov[s]] for s in SIDES}
    read = [r for r in runs if r["digest"] is not None]

    def enough(*sides) -> bool:
        return all(len(cov[s]) >= n_min for s in sides)

    def void(*sides) -> str:
        return "too few covered runs -- " + ", ".join(f"{s} {len(cov[s])}/{n_min}" for s in sides)

    # -- R3-RUNS -------------------------------------------------------------------------------------------
    order, recs = pred["order"], session.get("runs", [])
    struct = []
    if [x["side"] for x in recs[:len(order)]] != order[:len(recs[:len(order)])]:
        struct.append(f"the runs are {[x['side'] for x in recs[:len(order)]]}, not the frozen order")
    extra = recs[len(order):]
    if any(not x.get("rerun") for x in extra) or len(extra) > pred["rerun"]["max"]:
        struct.append(f"{len(extra)} runs after the nine, {sum(1 for x in extra if x.get('rerun'))} of them "
                      f"re-runs (at most {pred['rerun']['max']})")
    if [x.get("i") for x in recs] != list(range(1, len(recs) + 1)):
        struct.append("the runs are not numbered 1..n")
    if replay:
        struct += pairing_faults(runs, pred)
    struct += [f"{r['label']}: {b}" for r in runs for b in r["broken"]]
    tally = "; ".join(f"{s} {len(cov[s])} covered / {sum(1 for r in runs if r['side'] == s) - len(cov[s])} VOID"
                      for s in SIDES)
    voids = [f"{r['label']}: {', '.join(r['why_void'][:3])}" for r in runs if r["why_void"]]
    out.append((False if struct else True if enough(*SIDES) else None,
                f"R3-RUNS: the frozen nine in order, then re-runs only; >= {n_min} covered runs per side",
                ("; ".join(struct[:4]) + " || " if struct else "") + tally
                + (" || VOID " + " | ".join(voids[:6]) if voids else "")))

    # -- R3-DONOR (every run read) -------------------------------------------------------------------------
    bad, member_rows = [], Counter()
    for r in read:
        mine = chains.get(r["side"], {})
        others = {f for s, m in chains.items() if s != r["side"] for f in m}
        wrong = Counter()
        for x in r["rows"]:
            if x.fld in mine:
                member_rows[r["label"]] += 1
                if x.don != mine[x.fld]:
                    wrong[f"member {x.fld} don {x.don} (want {mine[x.fld]})"] += 1
            elif x.fld in others:
                wrong[f"another side's id {x.fld}"] += 1
            elif T.real_field(x.fld) and x.don != x.fld:
                wrong[f"real {x.fld} don {x.don}"] += 1
        bad += [f"{r['label']}: {w} x{n}" for w, n in wrong.items()]
        if r["side"] != "S" and not member_rows[r["label"]]:
            bad.append(f"{r['label']}: no row in any member")
    out.append((False if bad else True if member_rows else None,
                "R3-DONOR: every member row names its donor (ForkDonorPatch, live), every real row itself; no side "
                "strays into another's ids", "; ".join(bad[:6]) or
                (f"member rows per fork run {dict(member_rows)}" if member_rows else "no fork run read")))

    # -- R3-JOIN (every run read) --------------------------------------------------------------------------
    fails = [(r["label"], x.fld, x.target, x.ip, why) for r in read for x, why in r["digest"].failures]
    notes = sorted({f"{r['label']}: {n}" for r in read for n in r["digest"].notes})
    out.append((False if len(fails) > C["R3-JOIN"]["max_failures"] or notes else True if read else None,
                "R3-JOIN: every script row joins a store in the bytes its side ran",
                f"{len(fails)} failures {fails[:4]}; notes {notes[:3]}" + ("" if read else "; no run read")))

    reports = {}
    c0 = T.compare(dig["S"], dig["F0"], members=chains["F0"]) if dig["S"] and dig["F0"] else None
    c4 = T.compare(dig["S"], dig["F4"], members=chains["F4"]) if dig["S"] and dig["F4"] else None
    if c0 is not None:
        reports["rung3_report_S_vs_F0.txt"] = T.report(
            c0, title=f"story trace: stock Dali x{len(dig['S'])} vs F0 (import-chain, no 450) x{len(dig['F0'])} "
                      f"(covered runs)", writers=True)
    if c4 is not None:
        reports["rung3_report_S_vs_F4.txt"] = T.report(
            c4, title=f"story trace: stock Dali x{len(dig['S'])} vs F4 (round-4 seed) x{len(dig['F4'])} "
                      f"(covered runs)", writers=True)

    # -- R3-PING -------------------------------------------------------------------------------------------
    p = C["R3-PING"]
    what = f"R3-PING: {p['target']} := {p['value']} in every covered stock run, and WRITERS names only 450"
    if not enough("S"):
        out.append((None, what, void("S")))
    else:
        got = dict(T.writers(dig["S"]).get((p["target"], p["value"]), Counter()))
        want = {int(w): len(dig["S"]) for w in p["writers"]}
        out.append((got == want, what, f"writers {got} (want {want}) over {len(dig['S'])} covered stock runs"))

    # -- R3-NULL-PRE (F0) ----------------------------------------------------------------------------------
    p = C["R3-NULL-PRE"]
    what = ("R3-NULL-PRE: F0 -- nothing stock writes before 450 is missing from the members (rung 2 at zone scale, "
            "and at tour scale)")
    if not enough("S", "F0"):
        out.append((None, what, void("S", "F0")))
    else:
        seam_field = p["seam_field"]
        cut, tl = {}, {}
        for r in cov["S"]:
            line = _first_line(r["rows"], lambda x: x.fld == seam_field)
            cut[r["label"]] = line if line is not None else float("inf")
            tl[r["label"]] = tour_line(r["rows"], r["digest"], pred, {})
        pre = [k for k in dig["S"][0].keys
               if all(k in d.keys and d.keys[k].at < cut[d.label] for d in dig["S"])]
        n_f0 = Counter(k for d in dig["F0"] for k in d.keys)
        missing = sorted((k for k in pre if not n_f0[k]), key=T.WriteKey.sort_key)
        matched = [k for k in pre if n_f0[k] == len(dig["F0"])]
        partial = [k for k in pre if 0 < n_f0[k] < len(dig["F0"])]
        in_tour = [k for k in matched if all(tl[d.label] is not None and d.keys[k].at >= tl[d.label]
                                             for d in dig["S"])]
        donors = Counter(k.donor for k in in_tour)
        lacking = sorted(set(p["tour_donors"]) - set(donors))
        short = []                   # the non-vacuity guard, as v1 reads it: matched in every covered F0 run
        if len(matched) < p["min_matched"]:
            short.append(f"{len(matched)} matched (want >= {p['min_matched']})")
        if len(in_tour) < p["min_tour_keys"]:
            short.append(f"{len(in_tour)} tour keys (want >= {p['min_tour_keys']})")
        if lacking:
            short.append(f"none from {lacking}")
        # the same guard on the STOCK side alone: does the evidence the claim needs exist? matched is a subset of pre,
        # in_tour of stock_tour, so a stock shortfall is always a short guard; the converse is F0 writing the
        # evidence in only SOME runs (partial) -- a fork difference, never too little evidence
        stock_tour = [k for k in pre if all(tl[d.label] is not None and d.keys[k].at >= tl[d.label] for d in dig["S"])]
        thin = []
        if len(pre) < p["min_matched"]:
            thin.append(f"{len(pre)} stock keys before 450 (want >= {p['min_matched']})")
        if len(stock_tour) < p["min_tour_keys"]:
            thin.append(f"{len(stock_tour)} of them first written in every stock tour (want >= {p['min_tour_keys']})")
        s_lacking = sorted(set(p["tour_donors"]) - {k.donor for k in stock_tour})
        if s_lacking:
            thin.append(f"no stock tour key from {s_lacking}")
        split = p.get("shortfall") == "VOID"       # v2: a thin stock side is VOID; v1 (no field): any short guard FAILs
        ok = False if missing else (None if split and thin else False) if short else True
        show = lambda ks: [f"{k.donor} e{k.sid} t{k.tag} {k.off:+d} {k.target}={k.value}" for k in ks[:4]]  # noqa: E731
        out.append((ok, what,
                    f"{len(pre)} stock keys before 450 in every covered stock run; {len(matched)} written by the "
                    f"members in every covered F0 run, {len(partial)} in some; MISSING {len(missing)} "
                    f"{show(missing)}; "
                    f"{len(in_tour)} of the matched first written in the TOUR (want >= {p['min_tour_keys']}), by "
                    f"donor {dict(sorted(donors.items()))}" + (f" -- none from {lacking}" if lacking else "")
                    + (f" || the claim held on this evidence, but the stock side's evidence is short "
                       f"({'; '.join(thin)}): too little evidence to say, not a falsification" if ok is None else "")
                    + (f" || the stock evidence is there ({len(pre)} keys, {len(stock_tour)} in every stock tour), but "
                       f"the members wrote {len(partial)} of them in only some covered F0 runs ({'; '.join(short)}): "
                       f"PARTIAL {show(sorted(partial, key=T.WriteKey.sort_key))}"
                       if split and ok is False and not missing else "")))

    # -- R3-SEAM (F0) --------------------------------------------------------------------------------------
    p = C["R3-SEAM"]
    what = ("R3-SEAM: F0 -- every covered run reaches 450 only across member(350)'s seam, and the ping is REACHED "
            "ONLY ACROSS A SEAM, written by no F0 donor")
    if not enough("S", "F0"):
        out.append((None, what, void("S", "F0")))
    else:
        want_seam = (p["seam"]["donor"], p["seam"]["to"])
        per = []
        for d in dig["F0"]:
            first = d.seams[0] if d.seams else None
            into = [s for s in d.seams if p["seam"]["to"] in s.fields]
            member_450 = [k for k in d.keys if k.donor == p["seam"]["to"]]
            per.append((d.label, first is not None and (first.donor, first.to) == want_seam and bool(into)
                        and all(s.donor == want_seam[0] for s in into) and not member_450,
                        first.origin + f" -> {first.to}" if first else "no seam"))
        ping = p["ping"]
        hit = [k for k in c0.across_seam if _matches(dict(ping, value=[ping["value"]]), k)]
        seam_ok = bool(hit) and all(c0.seam_counts.get(k, 0) == len(dig["F0"]) and c0.seam_seen[k].seam is not None
                                    and c0.seam_seen[k].seam.donor == want_seam[0] for k in hit)
        in_members = [k for k, (s, f) in c0.counts.items() if f and (k.target, k.value)
                      == (ping["target"], ping["value"])]
        who = set(c0.writers.get((ping["target"], ping["value"]), ()))
        by_donor = sorted(who & set(chains["F0"].values()))
        ok = all(ok_ for _l, ok_, _o in per) and seam_ok and not in_members and bool(who) and not by_donor
        out.append((ok, what,
                    f"first seams {[(l, o) for l, _ok, o in per]}; ping across the seam "
                    f"{[(str(k.donor), k.sid, k.tag, k.off, c0.seam_counts.get(k)) for k in hit]}; member ping keys "
                    f"{len(in_members)}; stock writers {sorted(who)}, of them F0 donors {by_donor}"))

    # -- R3-MIRROR (F0) ------------------------------------------------------------------------------------
    what = "R3-MIRROR: F0 -- FORK ONLY and STOCK ONLY are empty, and no neighbour-byte clobber"
    if not enough("S", "F0"):
        out.append((None, what, void("S", "F0")))
    else:
        show = lambda ks: [f"{k.donor} e{k.sid} t{k.tag} {k.off:+d} {k.target}={k.value}" for k in ks[:4]]  # noqa: E731
        out.append((not c0.fork_only and not c0.stock_only and not c0.clobbers, what,
                    f"{len(c0.fork_only)} FORK ONLY {show(c0.fork_only)}; {len(c0.stock_only)} STOCK ONLY "
                    f"{show(c0.stock_only)}; {len(c0.clobbers)} clobbers"))

    # -- R3-ADVANCE ----------------------------------------------------------------------------------------
    p = C["R3-ADVANCE"]
    what = "R3-ADVANCE: F0 leaves SC 2600 in a real field, across the seam; F4 never does"
    every = {f for m in chains.values() for f in m}
    moved = {}
    for r in cov["F0"] + cov["F4"]:
        first = next((x for x in r["rows"] if x.k != "c" and x.sc >= p["sc"]), None)
        moved[r["label"]] = None if first is None else first.fld
    if not enough("F0", "F4"):
        out.append((None, what, void("F0", "F4")))
    else:
        ok = (all(moved[r["label"]] is not None and moved[r["label"]] not in every and T.real_field(moved[r["label"]])
                  for r in cov["F0"])
              and all(moved[r["label"]] is None for r in cov["F4"]))
        out.append((ok, what, f"first field at SC >= {p['sc']}: {moved}"))

    # -- R3-LATCH (F4) -------------------------------------------------------------------------------------
    p = C["R3-LATCH"]
    what = ("R3-LATCH: F4 -- the hub-gated writes are STOCK ONLY, the CLOBBER report names byte 297, and F4 reached "
            "the real 450 and walked out through e19")
    if not enough("S", "F4"):
        out.append((None, what, void("S", "F4")))
    else:
        parts, bad = [], []
        for pat in p["stock_only"]:
            in_stock = all(any(_matches(pat, k) for k in d.keys) for d in dig["S"])
            in_f4 = sorted({f"{k.donor} e{k.sid} {k.off:+d}" for d in dig["F4"]
                            for k in (*d.keys, *d.seam_keys) if _matches(pat, k) and k.off >= 0})
            secs = [name for name, keys in (("STOCK ONLY", c4.stock_only), ("UNSTABLE", c4.unstable),
                                            ("ACROSS SEAM", c4.across_seam), ("MATCHED", c4.matched))
                    if any(_matches(pat, k) for k in keys)]
            if not (in_stock and not in_f4):
                bad.append(f"{pat['name']}: in every covered stock run {in_stock}, F4 wrote it at {in_f4}")
            parts.append(f"{pat['name']} [{'/'.join(secs) or '-'}]")
        cl = p["clobber"]
        clobbers = [x for x in c4.clobbers
                    if (x.byte, x.old, x.new, x.key.target, x.key.value) == (cl["byte"], cl["old"], cl["new"],
                                                                             cl["target"], cl["value"])
                    and x.key.off < 0 and cl["evidence"] in x.why]
        if not any(x.runs >= len(dig["F4"]) for x in clobbers):
            bad.append(f"no clobber of byte {cl['byte']} {cl['old']} -> {cl['new']} by the prepend's {cl['target']} = "
                       f"{cl['value']} in every covered F4 run ({[(x.key.donor, x.runs) for x in clobbers]}; all "
                       f"{[(x.key.target, x.byte, x.old, x.new) for x in c4.clobbers][:4]})")
        sm = p["seam"]
        reached = [d.label for d in dig["F4"] if any(s.donor == sm["donor"] and sm["to"] in s.fields for s in d.seams)]
        if len(reached) < len(dig["F4"]):
            bad.append(f"only {reached} entered the real {sm['to']} across member({sm['donor']})'s seam -- the 450 "
                       f"writes would be absent because 450 never ran")
        found = [(x.key.donor, x.byte, x.old, x.new, x.runs) for x in clobbers]
        out.append((not bad, what, ("; ".join(bad[:5]) if bad else "all three parts hold") + " || "
                    + "; ".join(parts) + f" || clobbers {found}"))

    # -- R3-PREEMPT (F4) -----------------------------------------------------------------------------------
    p = C["R3-PREEMPT"]
    what = "R3-PREEMPT: F4 -- PRE-EMPTED names the latches 2064/2079/2075 beside the stock writers that set them"
    if not enough("S", "F4"):
        out.append((None, what, void("S", "F4")))
    else:
        pe = {(x.target, x.value): x for x in c4.pre_empted}
        bad, named = [], []
        for latch in p["latches"]:
            x = pe.get((latch["target"], latch["value"]))
            if x is None:
                bad.append(f"{latch['target']} := {latch['value']} is not PRE-EMPTED")
                continue
            short = [d.label for d in dig["S"] if not any(_matches(latch["stock"], k) for k in d.keys)]
            if short:
                bad.append(f"{latch['target']} := {latch['value']}: no stock write at {latch['stock']['name']} "
                           f"in {short}")
            named.append(f"{latch['target']} := {latch['value']} stamped in {sorted({k.donor for k in x.stamps})}, "
                         f"stock at {sorted({(k.donor, k.sid, k.tag, k.off) for k in x.stock})}")
        out.append((not bad, what, ("; ".join(bad) if bad else "all three named") + " || " + "; ".join(named)
                    + f" || PRE-EMPTED {[(x.target, x.value) for x in c4.pre_empted]}"))

    # -- the summary ---------------------------------------------------------------------------------------
    lines = [f"story trace rung 3 -- session {session.get('label')} ({session.get('started')} .. "
             f"{session.get('finished', 'unfinished')})"
             + (f"; re-runs stopped: {session['rerun_stop']}" if session.get("rerun_stop") else "")
             + (f"; predictions {pred_path.name} v{pred.get('version')} (F0 replays its stock partner)"
                if replay else ""), ""]
    by_i = {r["i"]: r for r in runs}
    for r in runs:
        rec = r["rec"]
        lines.append(f"  {r['label']:<6} {rec.get('t0', '?')}..{rec.get('t1', '?')}s  "
                     f"{'VOID' if r['why_void'] else 'covered'}{' (re-run)' if rec.get('rerun') else ''}  "
                     f"stop: {rec.get('stop', rec.get('skipped', rec.get('install', '?')))}")
        if r["why_void"]:
            lines.append(f"         VOID: {'; '.join(r['why_void'])}")
        if replay and r["side"] == "F0":
            mate = by_i.get(rec.get("partner"))
            want = D.entered_walk(mate["log"]["log"]) if mate is not None and mate["log"] is not None else None
            got = D.entered_walk(r["log"]["log"], chains["F0"], legs=("replay",)) if r["log"] is not None else None
            lines.append(f"         partner: S#{rec.get('partner')}"
                         + (f"; replayed {len(got)} of its {len(want)} steps" if got is not None and want is not None
                            else ""))
        if r["rows"] is not None:
            lines.append(f"         places: {_places(r['rows'], chains.get(r['side'], {}))}"
                         + (f"   (rows before the start field, not read: fields {r['pre']})" if r["pre"] else ""))
    word = {True: "PASS", False: "FAIL", None: "VOID"}
    lines += ["", "CHECKS"] + [f"  {word[ok]}  {what}\n        {detail}" for ok, what, detail in out]
    reports["rung3_summary.txt"] = "\n".join(lines) + "\n"
    return out, reports


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Rung 3's analysis, offline, on a session's saved traces.")
    ap.add_argument("--analyse", required=True, metavar="RUN_DIR", help="the session's run directory")
    ap.add_argument("--predictions", metavar="FILE", default=None,
                    help="read these predictions instead of the file the session recorded (P-FROZEN still judges "
                         "them against the sha256 the session recorded)")
    a = ap.parse_args(argv)
    try:
        checks, reports = analyse(a.analyse, pred_path=None if a.predictions is None else Path(a.predictions))
    except NotReplays as err:
        print(f"REFUSED: {err}", file=sys.stderr)
        return 2
    for name, text in reports.items():
        (Path(a.analyse) / name).write_text(text, encoding="utf-8")
    print(reports["rung3_summary.txt"])
    return 0 if all(ok is True for ok, _w, _d in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
