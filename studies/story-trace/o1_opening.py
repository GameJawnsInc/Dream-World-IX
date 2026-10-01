"""THE STORY-WRITE TRACE, O1 -- THE OPENING: New Game to Alexandria, stock Prima Vista against its verbatim whole-zone
fork, on the game's own route, both sides played by one driver (studies/story-trace/PLAN.md, "O1").

    py tools/play.py studies/story-trace/o1_opening.py --label story-o1 --timeout 240
    py studies/story-trace/o1_opening.py --offline-check           # the build against its donors, the keys against the bytes
    py studies/story-trace/o1_opening.py --preflight               # the live install (read-only)
    py studies/story-trace/o1_opening.py --analyse <run dir>       # the analysis alone, on saved traces
    py studies/story-trace/o1_opening.py --freeze                  # write o1_predictions_v1.json (once, before any run)

THE SIDES (o1_forks.json; the chain deployed to FF9CustomMap 31200-31219, ONE RELAUNCH before the session):
  S  stock: the install's scripts. Start: 50 (Prima Vista, the Cargo Room).
  F  `import-chain 50 --verbatim --whole-zone --fresh-ids --id-base 31200 --name-prefix O1`: the tshp zone's 20
     fields. Start: 31200 (its 50). Field 100 (alxt) is no member, so member(52)'s `Field(100)` is a seam into the
     real game: the segment's end on both sides.

THE ENTRY: New Game, trace on, then in field 70 a raw `warp <start> 0 -1` (rung 3's start). The New-Game override is
left alone; the warp skips FMV001 and field 70's two post-FMV writes on both sides alike.

THE ROUTE (:func:`drive`, one driver for both sides). It acts only on what the game shows, first match wins:
  field 100 -> the end; the naming screen -> accept_name(); a battle -> fight() (it closes the tutorial screen,
  attacks, and leaves the result screen); a READY choice -> the frozen rule table (by option text) or VOID; a dialogue
  page -> Confirm; control held in 50 before the candle -> route to the candle and interact; control held anywhere
  else -> VOID. Optional pickups are never taken.

THE SESSION: one launch, S F S F S F; a side short of min_covered covered runs re-runs (S first), at most rerun.max.
Each run's trace and log are saved as it ends, the session record rewritten after every run. The shared install is
fingerprinted around every run: a run begun on a changed install is skipped, one the install changed under is never
read (both VOID).

THE ANALYSIS (:func:`analyse`): each covered run is cut at its first row in the end field, digested
(storytrace.digest, the fork side with its members) and compared (storytrace.compare). The checks and the verdict
read the predictions the session recorded, and nowhere else.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

from ff9mapkit import storytrace as T                                   # noqa: E402
import segment_trace as ST                                              # noqa: E402
# moved to the shared engine (research/o2_design.md 1.2-1.4) and re-exported here under their O1 names
from segment_drive import RouteVoid, pick_for                           # noqa: E402,F401
from segment_trace import (RECOVERY_FIELD, SIDES, THROWS, WHERE, is_noise, members_of,  # noqa: E402,F401
                           verdict, wkey)

#: v1 (sha 49fd880f) walked to the candle region's CENTRE, which is the table: session story-o1 run 1 stood in the
#: region with the "?" up, pressed against the table (the owner, watching), and went VOID. v2 walks to that spot.
#: v2 (sha 681398ac) matched the candle choice on "Light the candle": the agent publishes that first choice line as
#: "ight the candle" (the line after [CHOO][MOVE=18,0] loses its first character) -- session story-o1b run 1 VOID.
#: v3 (sha 05fb803e) counted the battle won only at result 1: scene 336 ends by script (RunBattleCode) and the engine
#: reports 2, "victory-no-pose" -- session story-o1c run 1, which reached 100 with every beat. v4 counts 1 or 2.
PREDICTIONS = HERE / "o1_predictions_v4.json"
MANIFEST = HERE / "o1_forks.json"
SESSION_FILE = "o1_session.json"
CHAIN_DIR = Path(r"C:\gd\_ns_playtest\o1\fork")
BUILD_DIR = Path(r"C:\gd\_ns_playtest\o1\build")
REPORT_FILE = "o1_report.txt"
_MODULE_DOC = __doc__


# ======================================================================== the predictions
def chain_from_campaign(campaign: Path = CHAIN_DIR / "campaign.toml") -> tuple:
    """``({fork id: donor}, {fork id: member name})`` of the built chain."""
    return ST.chain_from_campaign(campaign)


def draft_predictions() -> dict:
    """The registered claims. Every number here was read off the stock bytes (the --offline-check re-derives each
    one) or the chain's campaign.toml; nothing is read from a run."""
    members, names = chain_from_campaign()
    key = lambda donor, sid, tag, ip, off, target, value, what: {                     # noqa: E731
        "donor": donor, "m": T.FIELD_MODE, "src": "eb", "sid": sid, "tag": tag, "ip": ip, "off": off,
        "target": target, "value": value, "what": what}
    return {
        "version": 4,
        "what": "O1: New Game -> 50 -> 52 -> Field(100), stock vs the tshp zone's verbatim fork (PLAN.md, O1)",
        "supersedes": "v3 (05fb803e): it counted only result 1 as a won battle, and scene 336 ends at 2 (story-o1c "
                      "VOID); v2 (681398ac): its candle rule missed the published 'ight the candle' (story-o1b VOID); "
                      "v1 (49fd880f): its candle point was the region's centre, the table (story-o1 VOID)",
        "order": ["S", "F", "S", "F", "S", "F"],
        "min_covered": 2,
        "rerun": {"max": 2},
        "budget": {"run_s": 720, "run_min_s": 540, "session_s": 7200, "settle_s": 1.0},
        "start": {"S": 50, "F": 31200},
        "entrance": 0,
        "end_field": 100,
        "stock_fields": [50, 52, 100],
        "members": {str(f): d for f, d in sorted(members.items())},
        "names": {str(f): n for f, n in sorted(names.items())},
        # the candle: regions e4-e7 of 50, four triangles meeting at (0, 350) -- where the table stands -- spanning
        # x -300..300, z 120..650. This point is where session story-o1's run 1 stood with the "?" up, right of the
        # table; a Confirm there opens "Light the candle / Cancel".
        "candle": {"donor": 50, "x": 180.0, "z": 290.0, "tolerance": 45.0},
        # a READY choice is answered by the first rule whose `match` is a substring of any option line
        "choices": [
            {"donor": 50, "match": "the candle", "pick": "the candle", "beat": "candle"},   # published: "ight the candle"
            {"donor": 52, "match": "Garnet", "pick": "Garnet", "beat": "garnet"},
            {"donor": None, "match": "want to skip", "pick": "default", "beat": None},   # the skip-movie window
        ],
        # O1-LADDER: every covered run of both sides writes each of these, in donor terms (WriteKey)
        "ladder": [
            key(50, 17, 1, 1804, 1249, "Global.UInt16[0]", 1000, "SC 0 -> 1000, before control in 50"),
            key(50, 17, 1, 3240, 2685, "Global.Byte[6]", 1, "Byte[6] |= 1, after the naming screen"),
            key(50, 15, 1, 635, 536, "Global.Int16[2]", 100, "FieldEntrance := 100, 50's exit to 52"),
            key(52, 3, 1, 1249, 1140, "Global.Int16[2]", 102, "FieldEntrance := 102, 52's exit to 100"),
        ],
        "sc_writes": 1,              # SC (field rows, Global.UInt16[0]) is written exactly once in a covered run
        # registered noise: never a STOCK ONLY / FORK ONLY / UNSTABLE finding. Scene 336's AI (not a field row).
        "noise": [
            {"not_m": T.FIELD_MODE, "target": "Global.Byte[206]", "why": "the Masked Man AI's random wait"},
            {"not_m": T.FIELD_MODE, "target": "Global.Byte[199]", "why": "set only if a member carries status 512"},
        ],
        "beats": ["candle", "named", "battle", "garnet"],
        # the battle beat is done at a WIN: 1 victory, 2 victory-no-pose (the scripted end, RunBattleCode)
        "battle_won": [1, 2],
    }


# ======================================================================== the driver
def drive(g, pred: dict, side: str, log: list, *, deadline: float, floor_for=None, prior_for=None,
          progress: dict | None = None) -> dict:
    """Play the segment from the start field to the end field. Returns the run's outcome:
    ``{"end": "reached" | "void", "why", "beats", "pages", "choices", "t"}``. ``floor_for(donor)`` / ``prior_for(donor)``
    give the candle walk its walkmesh and movement prior (default: the donor's stock walkmesh as the player walks it,
    and :meth:`key_prior` of the donor -- a member's own are its donor's, P-FLOOR). ``progress`` (a dict) is filled
    with the live beats/pages/choices, so a run that raises still says how far it got."""
    from harness import HarnessError
    from ff9mapkit import extract
    from ff9mapkit.content import pathfind
    floor_for = floor_for or (lambda d: pathfind.PlayerWalkmesh(extract.stock_walkmesh(d)))
    prior_for = prior_for or g.key_prior
    members = members_of(pred) if side == "F" else {}
    beats = {"candle": False, "named": False, "battle": None, "garnet": False}
    pages: list = []
    taken: list = []
    overlays: list = []
    tries = {"candle": 0}
    held = {"n": 0, "at": None}
    settle_polls = max(1, int(pred["budget"]["settle_s"] / 0.05))
    t0 = time.time()
    if progress is not None:
        progress.update(beats=beats, pages=pages, choices=taken)

    def out(end: str, why: str) -> dict:
        return {"end": end, "why": why, "beats": beats, "pages": pages, "choices": taken,
                "t": round(time.time() - t0, 1)}

    while time.time() < deadline:
        st = g.state
        fid = st.field_id
        donor = members.get(fid, fid)
        if fid == pred["end_field"]:
            log.append({"k": "end", "field": fid, "t": round(time.time() - t0, 1)})
            return out("reached", f"field {fid}")
        if st.ui_state == "NameSetting":
            g.accept_name()
            beats["named"] = True
            log.append({"k": "named", "field": fid})
            continue
        if st.ui_state == "Tutorial" and not st.in_battle:
            g._dismiss_tutorial()
            continue
        if st.in_battle:
            result = g.fight(timeout=max(30.0, deadline - time.time()), finish=True)
            beats["battle"] = result
            log.append({"k": "battle", "field": fid, "result": result, "turns": (g.last_fight or {}).get("turns")})
            continue
        if st.choice is not None:
            held["n"] = 0
            if not g._choice_ready(st):
                time.sleep(0.05)
                continue
            snap = json.dumps(st.choice, sort_keys=True)
            if held["at"] is None or held["at"][0] != snap:
                held["at"] = (snap, time.time(), st.frame)
                time.sleep(0.05)
                continue
            if time.time() - held["at"][1] < pred["budget"]["settle_s"] or st.frame <= held["at"][2]:
                time.sleep(0.05)
                continue
            held["at"] = None
            index, rule = pick_for(st.choice, donor, pred)
            if index == "default":
                took = g._take_default_choice(st)
                taken.append({"field": fid, "donor": donor, "options": st.choice.get("options"), "index": "default",
                              "took": took})
            else:
                g.choose(index)
                taken.append({"field": fid, "donor": donor, "options": st.choice.get("options"), "index": index})
                if rule.get("beat"):
                    beats[rule["beat"]] = True
            log.append({"k": "choice", **taken[-1]})
            continue
        if st.dialog_open and st.text.strip() and not st.control:
            # a page the script waits on (control withheld). A window up WHILE he has control is an overlay hint
            # (50's "Press the X button when the ? appears.", async, closed by the script): never paged.
            held["n"] = 0
            if not pages or pages[-1] != st.text:
                pages.append(st.text)
            g.press("confirm", 3)
            g.wait_frames(g.rate().frames_for_ticks(g.CUTSCENE_PAGE_TICKS))
            continue
        if st.control and st.player_x is not None and not st.fading:
            if st.dialog_open and st.text.strip() and st.text not in overlays:
                overlays.append(st.text)
                log.append({"k": "overlay", "field": fid, "text": st.text})
            held["n"] += 1
            if held["n"] < settle_polls:
                time.sleep(0.05)
                continue
            held["n"] = 0
            c = pred["candle"]
            if donor == c["donor"] and not beats["candle"]:
                tries["candle"] += 1
                if tries["candle"] > 2:
                    raise RouteVoid(f"two candle attempts opened no choice (at {g.state.player_x}, {g.state.player_z})")
                rec = g.route_to(c["x"], c["z"], walkmesh=floor_for(donor), prior=prior_for(donor),
                                 tolerance=c.get("tolerance", 45.0), timeout=60.0, unstick=True, smooth=True, npcs=True,
                                 overlay_ok=True)
                # a plain Confirm: interact() refuses to press while a window is up, and the region's own hint is
                # up exactly while he stands where the Confirm works
                g.press("confirm", 4)
                try:
                    g.wait_for(lambda s: s.choice is not None, timeout=4.0, what="the candle's choice")
                    opened = True
                except HarnessError:
                    opened = False
                log.append({"k": "candle", "field": fid, "reached": rec.get("reached"), "try": tries["candle"],
                            "at": [g.state.player_x, g.state.player_z], "opened": opened})
                continue
            raise RouteVoid(f"control held in {fid} (donor {donor}) where the route never gives it")
        held["n"] = 0
        time.sleep(0.05)
    raise HarnessError(f"the run's budget ran out in field {g.state.field_id}")


# ======================================================================== O1 on the shared engine
class O1Segment(ST.Segment):
    """O1 on :class:`segment_trace.Segment`: its constants, its check texts exactly as the archived sessions print
    them, its LADDER, its report-only dialogue line, and its unchanged :func:`drive`. Every other line of the session
    and the analysis is the shared engine's (the O1 regression gate, segment_regress.py, proves it byte-identical)."""

    tag = "O1"
    doc = _MODULE_DOC
    predictions = PREDICTIONS
    manifest = MANIFEST
    session_file = SESSION_FILE
    report_file = REPORT_FILE
    chain_dir = CHAIN_DIR
    build_dir = BUILD_DIR
    accept_us_build = True               # the deployed O1 chain predates the kit's own-language capture (3d8b7f1b)
    core_ids = ("LADDER", "NULL", "STABLE", "JOIN")
    titles = {
        "P-CAP": "P-CAP: the engine advertises the story trace at proto 1",
        "P-MANIFEST": "P-MANIFEST: the frozen members are the deployed chain's (o1_forks.json, deployed)",
        "P-DEPLOY": "P-DEPLOY: every member registered once under its name, and mapped once to its donor",
        "P-EB": "P-EB: every member's live .eb (7 languages) is the offline-checked build's",
        "P-FLOOR": "P-FLOOR: every member's deployed walkmesh is its donor's",
        "P-STOCK": "P-STOCK: no mod folder overrides stock 50, 52 or 100",
        "BUILD": "O1-BUILD: every member's US .eb is its donor's with only in-chain Field() literals remapped; "
                 "each other language is its own donor's (the kit now) or the us build (the kit before 3d8b7f1b)",
        "KEYS": "O1-KEYS: every ladder key is a store of its variable at its ip in the donor's stock bytes",
        "FROZEN": "O1-FROZEN: the predictions are the file the session recorded, unchanged",
        "COVER": "O1-COVER: at least {min_covered} covered runs a side",
        "LADDER": "O1-LADDER: every covered run writes the four ladder keys, and SC exactly once",
        "NULL": "O1-NULL: STOCK ONLY and FORK ONLY are empty outside the registered noise",
        "STABLE": "O1-STABLE: no key outside the registered noise is written in some runs of a side and not others",
        "JOIN": "O1-JOIN: every script row joins a store in the bytes its field ran",
        "THROW": "O1-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
    }
    drive = staticmethod(drive)

    def draft(self) -> dict:
        return draft_predictions()

    def core_checks(self, runs: list, cov: dict, pred: dict) -> list:
        """O1-LADDER (the four ladder keys in every covered run, and SC written exactly once), then the shared
        NULL, STABLE and JOIN."""
        covered = cov["S"] + cov["F"]
        bad = []
        for r in covered:
            keys = set(r["digest"].keys)
            for k in pred["ladder"]:
                if wkey(k) not in keys:
                    bad.append(f"{r['side']}#{r['i']} lacks {k['what']}")
            sc = [x for x in r["rows"] if x.k == "w" and x.m == T.FIELD_MODE and x.target == "Global.UInt16[0]"]
            if len(sc) != pred["sc_writes"]:
                bad.append(f"{r['side']}#{r['i']} wrote SC {len(sc)} times")
        ladder = (not bad, self.title("LADDER"),
                  "; ".join(bad[:6]) or f"{len(covered)} runs x {len(pred['ladder'])} keys")
        return [ladder] + super().core_checks(runs, cov, pred)

    def report_extra(self, run_dir: Path, session: dict, pred: dict, runs: list, checks: list) -> list:
        """Report-only: each covered fork run's dialogue beside the first covered stock run's."""
        lines = []
        logs = {r["i"]: json.loads((run_dir / r["rec"]["log"]).read_text(encoding="utf-8"))
                for r in runs if r["covered"] and (run_dir / r["rec"].get("log", "")).is_file()}
        s0 = next((logs[r["i"]]["outcome"]["pages"] for r in runs if r["side"] == "S" and r["i"] in logs), None)
        for r in runs:
            if r["side"] == "F" and r["i"] in logs and s0 is not None:
                same = logs[r["i"]]["outcome"]["pages"] == s0
                lines.append(f"report: F#{r['i']} dialogue {'==' if same else '!='} the first covered stock run's "
                             f"({len(logs[r['i']]['outcome']['pages'])} vs {len(s0)} pages)")
        return lines


O1 = O1Segment()


# ======================================================================== O1's public names (thin wrappers)
def load_predictions(path: Path = PREDICTIONS) -> tuple:
    return O1.load(path)


def freeze(path: Path = PREDICTIONS) -> str:
    """Write the predictions ONCE (LF, sorted keys); refuses to overwrite a frozen file."""
    return O1.freeze(path)


_stock_lang = ST.stock_lang
_changed = ST._changed
_show = ST._show


def build_check(pred: dict, build: Path = BUILD_DIR, stock_lang=None) -> tuple:
    return O1.build_check(pred, build, stock_lang)


def keys_check(pred: dict, stock) -> tuple:
    return O1.keys_check(pred, stock)


def offline_check(pred: dict, build: Path = BUILD_DIR) -> list:
    return O1.offline_check(pred, build)


def _roots():
    return O1.roots()


def preflight(pred: dict, roots: list, build: Path = BUILD_DIR, manifest: Path = MANIFEST) -> list:
    """What must hold before the session spends an hour: ``[(ok, what, detail)]``."""
    return O1.preflight(pred, roots, build, manifest)


def fingerprint(roots: list, pred: dict) -> dict:
    """What the runs rely on in the SHARED install, JSON-shaped (two reads compare with ==)."""
    return O1.fingerprint(roots, pred)


def end_run(g, log: list, *, recovery: int = RECOVERY_FIELD) -> None:
    """Back to the title after a run: warp to ``recovery`` first (a covered run stands in field 100 as Alexandria's
    opening starts, and the soft reset does not reach the title through it: story-o1d), then the reset."""
    return O1.end_run(g, log, recovery=recovery)


def run(g) -> None:
    """The session (tools/play.py's entry): O1Segment.run."""
    return O1.run(g)


def cut_at_end(rows: list, end_field: int) -> tuple:
    """``(the run up to its first write in the end field, that row's line or None)``: segment_trace's cut on frozen
    places, with no members -- O1's end field 100 is no member's donor, so this is O1's field rule exactly."""
    return ST.cut_at_end(rows, [end_field], {})


def read_session(run_dir, pred: dict, *, session: dict | None = None, stock=None) -> list:
    """Every recorded run, read: ``[{i, side, rec, rows, cut, digest, covered, why_void, ...}]``."""
    return O1.read_session(run_dir, pred, session=session, stock=stock)


def judge(runs: list, pred: dict, *, frozen: tuple) -> list:
    """The registered checks over the read runs: ``[(True | False | None, what, detail)]`` -- None = VOID."""
    return O1.judge(runs, pred, frozen=frozen)


def analyse(run_dir, *, pred_path: Path | None = None, stock=None) -> tuple:
    """``(checks, report text)`` for a session directory, against the predictions the session recorded."""
    return O1.analyse(run_dir, pred_path=pred_path, stock=stock)


# ======================================================================== CLI
def main(argv=None) -> int:
    return O1.main(argv)


if __name__ == "__main__":
    sys.exit(main())
