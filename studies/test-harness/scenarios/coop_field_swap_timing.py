"""s164 -- FIELD-SWAP TIMING, ROUND 1 (studies/field-coop/SWAP-TIMING-S164.md rev 3, "## Benches" / "### Solo"), the SOLO bench.
[ff9mapkit netsync s164]

THE ROUND. Five items in one engine round: A the instrument (millisecond swap stamps on the QPC clock, one swap RECORD per
transition), B Finding 11's orphan hold (a plain line waits out the host's control-off stretch on my field), C the guest's own
Field() passing on the host's announced field (and its intent cache), PIN the story pin, LIFE the host's intent lifetime, D+E the
fade-aware follow and its 12-tick fade -- all behind ONE lever scheme, `netsync swap <op> [arg]`, and one state block,
`netsync.swap` (netsync's last key).

THE BENCH. One game on the selftest role (`netsync selftest 1`, `bench 1`, `stateevery 1`). HOME is the dialogue bench field 30801
(its keeper's journal menu is the line leg B opens by relay, `coop_dialogue_authority.py`'s `_open_by_relay`); AWAY is 30602 (LOCKT2,
registered and walkable). A harness `warp` never reaches RedirectGuestFieldJump (it goes through SetNextMap), so own-jump rows use a
REAL script Field(): leg C's 351 desk scene. `COOP_LEGS` picks legs from K, A, B, C, P, L and F (letters, any order, e.g. `KAB`);
leg K always runs, and the legs run in K A B C P L F order.

  K-PROOF    the proof line `field swap selftest: OK (N rows, M mutants caught, clock ...)` (battlewire.SWAP_PROOF_RE pins every
             constant; N and M are never judged against literals), `netsync.swap.selftest` "ok", the dialogue selftest still OK.
  K-CLOCK    a LOAD-TIME PRECONDITION, never a red row and never in the ledger: >= 20 samples with 0 <= kit qpc_ms() - clock.now_ms
             <= the sample's age (kit wall ms - clock.utc_ms) + 100 ms, src "qpc", hz and hires published. GREEN, UNFIT (with its
             reason: the instrument is unfit for the duo, DK-CLOCK) or SKIP (off Windows, qpc_ms() None) -- logged as a note.
  K-REFUSE   (bench still off) `swap delay 5000` and `swap orphan maybe` get the usage line; `swap intent 30602` the bench refusal;
             after `netsync selftest 0`, `swap orphan old` gets "co-op is off". Then the re-arm.
  K-LEVER    each op's ack line and its read-back in `levers`; `act` restores; `clear` restores every lever (its CLEAR line).
  K-RELEASE  every lever set, then `reset`: one release line and everything back; a second `reset` logs nothing; the re-arm and
             one `swap intent 30602`: `last.commit_t - last.due_t` <= 1 frame (no delay leaked).
  A-FOLLOW   `swap intent 30602`: one record (id +1) opened by `seen`, seen_t <= follow_t <= due_t <= commit_t <= land_t,
             follow_via intent, land_via follow, land_field 30602, closed by `line` or `window`.
  A-STAMP    each edge line's stamp (the follow line, L-COMMIT, L-LAND, L-CLOSE) exactly equals the record's own t.
  A-DELAY    two follows, `delay 0` then `delay 300`: commit_t - due_t = the leg's delay +- 1 measured frame, `last.delay_ms` 300 on
             leg 2; the legs' commit - follow difference is reported, not judged (F6).
  A-WORD     every stamped s163 line (stamp and waited/shown tail removed) matches its battlewire.S163_FORMS regex.
  B-HOST     a fresh line by relay under hostscene 1, `swap hostctl off`, `hostscene 0`: within 2 frames host_flags b1 b0 clear with b3
             set, orphan.host_holds, levers.hostctl_off, host_settled_ms >= 0.
  B-HOLD     held OrphanGraceMs + AutoReadMs + 2 s: every sample locked, host_settled_ms >= 2000, orphan_closes +0, holds +1, one
             hold line, no "is not on the host's screen" line.
  B-RELEASE  `swap hostctl on`: orphaned within 0.5 s, the end line "(the host's control is back)" with N within +-0.3 s of the
             sampled hold, last_end control, the auto-close AutoReadMs later, orphan_closes +1.
  B-BLIP     a fresh held line, on, then off 1.0 s later: orphaned, then locked; one relock line; relocks +1; no auto-close through
             AutoReadMs + 1 s.
  B-SCENE    B-BLIP's held line, then `hostscene 1`: the end line "(the host is busy (a scene or a line))"; the bench host's ADV closes
             the line "closed (host seq".
  B-BLIP2    a fresh single-page line orphaned at t0, off for 0.5 s at t0 + 1.0 / 2.5 / 4.0 / 5.5 s: exactly one relock line before
             the close (relocks +1), the auto-close by t0 + AutoReadMs + 0.3 s, orphan_closes +1, nothing counted after it.
  B-CTLON    a fresh line, `hostctl on`, `hostscene 0`: orphans OrphanGraceMs after the settle and auto-closes; holds +0.
  C-*        the 351 desk scene (warp 351 entrance 15 scenario 2600, `swap fade old` (T8), `lock 1`, the bench pages each line):
             REACHED only when "win 3 text 129 opened locked" logs within 30 s (else the leg is VOID). A dry run under `own old`
             measures Delta (text 139's close to the own jump, from state) and carries C-BOUNCE; then C-CACHE (`swap cache 352` at
             close + Delta - 1.0 s), C-PEND (`swap intent 352` at the own jump - 0.45 s; REACHED on the own-jump edge with
             session.follow.pending 352 in the sample before it, else VOID), C-AGE (the cache >= 3 s early) and C-SRC (a cache on HOME,
             then the warp). Each attempt starts from HOME (a field change between attempts: the bounce budget's spacing).
  P-*        the pin bench: `flag 8720 0`, `watch 8720`, `swap pinbench 30602 8720 [age 3000 | to 30604 | landed | party 1 <c>]`;
             the leg ends with `swap clear` (P-PARTY reads the party mirror before it and null after it, G2).
  L-*        `swap lifebench 30602`: the landing hook's 'I landed' line and intent.landed_ms >= 0 (both outlive the intent's end;
             the on_intent sample with the intent active is reported, never required); then `last_end` stands with
             last_life_ms - max(2000, landed_ms + 1000) in [0, 400]. Under `life`, an intent s163's rule ended before the hook ran
             (last_end old, no line, landed_ms -1: the R1 hole) leaves L-LAND VOID.
  F-*        eleven fade follows to 30602 (blackout / speedmode / lock / unmatched / a host key set up as the design registers).

THE REACH RULES (P4, P8). Every solo row is DETERMINISTIC: an op that was acked but whose key is still at its sentinel afterwards is
RED ("the engine never ran X"). A setup clause that misses (leg C's first line, C-PEND's pending sample, the keeper's uid) marks the
rows VOID with the reason -- recorded red, never green, and never counted as a calibration's predicted red.

THE CALIBRATIONS (COOP_CALIBRATE=<word>, refused AT LOAD when unknown: tools/play.py imports the scenario before its Session launches
FF9, so a refused word never costs a boot). Each word turns EXACTLY its registered rows red, each with its marker (K-CAL-M), and K-CAL
judges the exactness (a predicted red that reads UNREACHED fails it; all predicted UNREACHED is VOID, never a pass):

    stamps    `swap stamps off` (leg A)                         A-STAMP
    delay     leg 2 of A-DELAY sends `delay 0`, still expects 300  A-DELAY
    orphan    `swap orphan old` (leg B)                         B-HOLD, B-RELEASE, B-BLIP, B-BLIP2, B-SCENE
    own       `swap own old` (leg C)                            C-CACHE, C-PEND
    nocache   `swap own nocache` (leg C)                        C-CACHE
    pin       `swap pin old` around P-PIN / P-PARTY only (P3)   P-PIN, P-PARTY
    life      `swap life old` (leg L)                           L-STANDS
    fade      `swap fade old` (leg F; leg C keeps its own)      every F row
    long      `swap fade long` (leg F; F-REASSERT not run)      F-FAST, F-3X, F-HURRY
    nogate    `swap fade nogate` (leg F)                        F-OPEN, F-AHEAD, F-RECHECK, F-KEY
    norecheck `swap fade norecheck` (leg F)                     F-RECHECK
    nohurry   `swap fade nohurry` (leg F)                       F-HURRY

A word whose rows lie in no leg COOP_LEGS selects is refused at load too. An engine that publishes no `netsync.swap` (s163 or older)
is refused before any leg: every row closes red with that reason.

THE STAND-IN (tools/harness/fakegame.py, the `swap` rung) models K, A and B only: on an engine, a C, P, L or F leg's sentinel keys
after an acked op are red, so a stand-in run of them proves nothing (P8). ff9mapkit/tests/test_coop_field_swap_timing_bench.py runs
COOP_LEGS=KAB there.

    py tools/play.py studies/test-harness/scenarios/coop_field_swap_timing.py --instance C:\\gd\\ff9-inst\\host
    COOP_LEGS=KAB py tools/play.py studies/test-harness/scenarios/coop_field_swap_timing.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=orphan COOP_LEGS=KB py tools/play.py studies/test-harness/scenarios/coop_field_swap_timing.py
"""
from __future__ import annotations

import os
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

try:                                                       # play.py puts THIS worktree's tools/ first on sys.path
    from harness import battlewire as BW                   # noqa: E402 - the engine's words, through its twins
except ImportError:                                        # pragma: no cover - imported outside the driver
    sys.path.insert(0, str(cb.REPO / "tools"))
    from harness import battlewire as BW                   # noqa: E402
try:
    from harness.channel import qpc_ms as _qpc_ms          # noqa: E402 - the kit's read of the swap clock (None off Windows)
except ImportError:                                        # pragma: no cover
    _qpc_ms = None

HarnessError = cb.HarnessError

KEY = "netsync.swap"
PROBE = KEY + ".clock"                   # key PRESENCE is the capability (protocol 5, additive)

HOME, AWAY = 30801, 30602                # the dialogue bench field (the keeper) / LOCKT2
KEEPER_AT = (210.0, -837.0)              # coop_dialogue_authority.EAST: beside the keeper (its journal menu, a single page)
KEEPER_NEAR = 300.0                      # the keeper is the talk object nearest that spot, within this
C_FIELD, C_ENTRANCE, C_SCENARIO, C_DEST = 351, 15, 2600, 352   # leg C's desk scene (test2_94.txt:60-76, 3304-3317, 3850-3879)
C_FIRST, C_LAST = (3, 129), (3, 139)     # its first line, and the line whose close Delta is anchored at (P6)
C_REACH_S = 30.0                         # "win 3 text 129 opened locked" within this of the landing, else VOID
C_RUN_S = 120.0                          # one attempt's budget (the scene, the own jump, its landing)
C_CACHE_LEAD_S, C_PEND_LEAD_S, C_AGE_LEAD_S = 1.0, 0.45, 3.2
P_FLAG = 8720                            # >= FIRST_SAFE_FLAG (8712): the pin bench's story flag
P_OTHER = 30604                          # P-OTHER's `to <E>`: a registered bench field other than 30602 (COOPPARTY)
P_AGE_MS = 3000

GRACE_MS = BW.DIALOG_ORPHAN_GRACE_MS     # NetSyncDialog.OrphanGraceMs (2000)
AUTO_READ_MS = BW.DIALOG_AUTO_READ_MS    # NetSyncDialog.AutoReadMs (2000)
EARLY_MS = 80                            # a lower bound's allowance: TickCount's ~16 ms resolution + a frame + the publish
LATE_MS = 600                            # an upper bound's allowance: a tick + the publish + our poll
HOLD_S = (GRACE_MS + AUTO_READ_MS + 2000) / 1000.0
RELEASE_ORPHAN_MS = 500
HOLD_N_TOL_MS = 300
BLIP_OFF_S = 1.0
BLIP2_OFFS = (1.0, 2.5, 4.0, 5.5)        # t0 + these: the bench host's control off for BLIP2_OFF_S each (V4, P2)
BLIP2_OFF_S = 0.5
BLIP2_LATE_MS = 300
SETTLE_MIN_MS = 2000                     # B-HOLD: host_settled_ms at least this by the hold's end
B_HOST_FRAMES = 2
FRAME_MS_DEFAULT = 1000.0 / 30
SELFTEST_S = 20.0
ARRIVE_S = 25.0
FOLLOW_S = 12.0                          # a bench follow's landing
CLOSE_S = BW.SWAP_LINE_WINDOW_MS / 1000.0 + 8.0
CLOCK_MIN = 20
CLOCK_SLACK_MS = 100
CLOCK_WATCH_S = 4.0
REST_LEVERS = {"stamps": (None, "on"), "orphan": (None, "act"), "own": (None, "act"), "pin": (None, "act"), "life": (None, "act"),
               "fade": (None, "act")}
FADE_TIMER_MIN_MS = 885                  # the 0.9 s timer as measured (T12: 0.885-0.912 s)
LEGS = "KABCPLF"

LEG_ROWS = {
    "K": ("K-PROOF", "K-REFUSE", "K-LEVER", "K-RELEASE"),
    "A": ("A-FOLLOW", "A-STAMP", "A-DELAY", "A-WORD"),
    "B": ("B-HOST", "B-HOLD", "B-RELEASE", "B-BLIP", "B-SCENE", "B-BLIP2", "B-CTLON"),
    "C": ("C-BOUNCE", "C-CACHE", "C-PEND", "C-AGE", "C-SRC"),
    "P": ("P-PIN", "P-AGED", "P-OTHER", "P-LATE", "P-PARTY"),
    "L": ("L-LAND", "L-STANDS"),
    "F": ("F-FAST", "F-3X", "F-BLACK", "F-JOIN", "F-HURRY", "F-OPEN", "F-AHEAD", "F-AGED", "F-RECHECK", "F-REASSERT", "F-KEY"),
}
F_ROWS = LEG_ROWS["F"]

CLAIMS = {
    "K-PROOF": "the proof line 'field swap selftest: OK (N rows, M mutants caught, clock ...)' with every constant, "
               "`netsync.swap.selftest` 'ok', and the dialogue selftest still OK",
    "K-REFUSE": "`swap delay 5000` / `swap orphan maybe` get the usage line; `swap intent 30602` before `bench 1` the bench refusal; "
                "`swap orphan old` after `netsync selftest 0` 'co-op is off'",
    "K-LEVER": "each op's ack line and its read-back in `levers`; act restores; `clear` restores every lever with its CLEAR line",
    "K-RELEASE": "every lever set, then `reset`: one release line and everything back; a second `reset` logs nothing; re-armed, one "
                 "`swap intent 30602` commits within 1 frame of its due (no delay leaked)",
    "A-FOLLOW": "`swap intent 30602`: one record (id +1) opened by `seen`, seen <= follow <= due <= commit <= land, follow_via intent, "
                "land_via follow, land_field 30602, closed by `line` or `window`",
    "A-STAMP": "each edge line's stamp (follow, L-COMMIT, L-LAND, L-CLOSE) exactly equals the record's own t",
    "A-DELAY": "`delay 0` then `delay 300`: commit_t - due_t = the leg's delay +- 1 measured frame; last.delay_ms 300 on leg 2",
    "A-WORD": "every stamped s163 line, its stamp and tail removed, matches its S163_FORMS regex",
    "B-HOST": "hostctl off + hostscene 0 under a relayed line: within 2 frames host_flags b1 b0 clear with b3 set, orphan.host_holds, "
              "levers.hostctl_off, host_settled_ms >= 0",
    "B-HOLD": "held OrphanGraceMs + AutoReadMs + 2 s: every sample locked, host_settled_ms >= 2000, orphan_closes +0, holds +1, one "
              "hold line, no 'is not on the host's screen' line",
    "B-RELEASE": "`hostctl on`: orphaned within 0.5 s, the end line '(the host's control is back)' with N within 0.3 s of the sampled "
                 "hold, last_end control, the auto-close AutoReadMs later, orphan_closes +1",
    "B-BLIP": "a held line, on, then off 1.0 s later: orphaned then locked, one relock line, relocks +1, no auto-close through "
              "AutoReadMs + 1 s",
    "B-SCENE": "B-BLIP's held line, then hostscene 1: the end line '(the host is busy (a scene or a line))', the bench host's ADV "
               "closes it 'closed (host seq'",
    "B-BLIP2": "a single-page line orphaned at t0, off 0.5 s at t0 + 1.0/2.5/4.0/5.5: one relock line, relocks +1, the auto-close by "
               "t0 + AutoReadMs + 0.3 s, orphan_closes +1, nothing counted after it",
    "B-CTLON": "hostctl on, hostscene 0: the line orphans OrphanGraceMs after the settle and auto-closes; holds +0",
    "C-BOUNCE": "the dry run (no injection): the own jump bounces (own_verdict bounce, own_why not-host), bounces +1, a landing on 351 "
                "via a bounce reload with the record still open (reloads +1), own.passes +0",
    "C-CACHE": "`swap cache 352` before the jump: the cache write line, the '(cache)' pass line, by.cache +1, one 'Map: 352', bounces "
               "+0, the Left clear '(the cached field)', no 'field 352 loaded' clear",
    "C-PEND": "`swap intent 352` aimed inside the old 0.9 s window: the '(pending)' pass line, converted +1, one load, fade.ends.own +1, "
              "no s154 cancelled / dropped / never-landed line",
    "C-AGE": "a cache injected >= 3 s before the jump: the 'aged 2000 ms' clear, then a bounce",
    "C-SRC": "a cache on HOME, then the warp to 351: the Left clear for HOME, then a bounce",
    "P-PIN": "`swap pinbench 30602 8720`: flag 8720 = 0 after the landing, the 'stages intent N's frame for its story' line (the latest "
             "differs at 1 story bytes), pin.last_use pin, last.story pin",
    "P-AGED": "`age 3000`: flag 8720 = 1, pin.last_use aged",
    "P-OTHER": "`to 30604`: flag 8720 = 1, the held entry still names 30602, pin.other +1",
    "P-LATE": "`landed`: flag 8720 = 1, pin.last_use late, pin.last_use_quality late",
    "P-PARTY": "`party 1 <c>`: flag 8720 = 0 and dress.mirror_party[1] = c before the leg's `swap clear`, pin.last_party latest; after "
               "it mirror_party null and the clear line names the pin bench's party mirror",
    "L-LAND": "`swap lifebench 30602`: the 'I landed' line and intent.landed_ms >= 0 (the on_intent sample with the intent active is "
              "reported, not required); VOID under `life` when s163's rule ended the intent before the hook",
    "L-STANDS": "intent.last_end stands; last_life_ms - max(2000, landed_ms + 1000) in [0, 400]",
    "F-FAST": "fade.last fast / fade / 12, by black, primed, ticks 12-14, ms < 600",
    "F-3X": "speedmode 1: fade.last ms < 250, ticks 12-17",
    "F-BLACK": "blackout 1 first: view_start black, action join, by black, black_ticks >= 3, ms < 250, no cur_now under 248 to the due",
    "F-JOIN": "blackout 8 first: heading, left <= 8, join, due within left + 3 + 2 ticks",
    "F-HURRY": "blackout 60 first: hurry with frames 12, by black within 14 ticks, cur_now never drops",
    "F-OPEN": "a locked line open: backlog_start open, path backlog, by timer, ms >= 885",
    "F-AHEAD": "`netsync unmatched` within 1 s: backlog_start ahead, path backlog, by timer",
    "F-AGED": "`netsync unmatched` 3.2 s earlier: path fast (the age cap)",
    "F-RECHECK": "`netsync unmatched` right after the intent: path fast, held, by recheck, ms >= 885",
    "F-REASSERT": "`swap blackout off` 3 ticks into the fade: one reassert line, fade.reasserts +1, by black",
    "F-KEY": "a bench host key for my field: backlog_start key, path backlog, by timer, ms >= 885",
}

#: word -> (the lever, its registered red rows) -- SWAP-TIMING-S164.md "Solo calibrations, pre-registered"
WORDS = {
    "stamps": ("`swap stamps off` (leg A)", ("A-STAMP",)),
    "delay": ("leg 2 of A-DELAY sends `delay 0` and still expects +300", ("A-DELAY",)),
    "orphan": ("`swap orphan old` (leg B)", ("B-HOLD", "B-RELEASE", "B-BLIP", "B-BLIP2", "B-SCENE")),
    "own": ("`swap own old` (leg C)", ("C-CACHE", "C-PEND")),
    "nocache": ("`swap own nocache` (leg C)", ("C-CACHE",)),
    "pin": ("`swap pin old` around the P-PIN and P-PARTY pinbench calls only (P3)", ("P-PIN", "P-PARTY")),
    "life": ("`swap life old` (leg L)", ("L-STANDS",)),
    "fade": ("`swap fade old` (leg F; leg C keeps its own `fade old`)", F_ROWS),
    "long": ("`swap fade long` (leg F; F-REASSERT is not run under it)", ("F-FAST", "F-3X", "F-HURRY")),
    "nogate": ("`swap fade nogate` (leg F)", ("F-OPEN", "F-AHEAD", "F-RECHECK", "F-KEY")),
    "norecheck": ("`swap fade norecheck` (leg F)", ("F-RECHECK",)),
    "nohurry": ("`swap fade nohurry` (leg F)", ("F-HURRY",)),
}
FINALS = ("K-CAL-M", "K-CAL")


def calibration() -> str | None:
    """COOP_CALIBRATE read AT LOAD: '' / 0 none, a registered word, anything else REFUSED (never mapped to a lever)."""
    v = os.environ.get("COOP_CALIBRATE", "").strip().lower()
    if v in ("", "0"):
        return None
    if v in WORDS:
        return v
    raise SystemExit(f"coop_field_swap_timing: COOP_CALIBRATE={v!r} is refused -- the solo bench takes one of "
                     f"{', '.join(WORDS)} and nothing else; refused before the game boots.")


def legs_selected() -> str:
    """COOP_LEGS read AT LOAD: letters from K A B C P L F (any order, case-insensitive, commas / spaces ignored); empty = every leg.
    Leg K always runs. An unknown letter is refused before the game boots."""
    raw = os.environ.get("COOP_LEGS", "").strip().upper().replace(",", "").replace(" ", "")
    if not raw:
        return LEGS
    bad = sorted({c for c in raw if c not in LEGS})
    if bad:
        raise SystemExit(f"coop_field_swap_timing: COOP_LEGS={raw!r} is refused -- unknown leg(s) {', '.join(bad)} (legs: K A B C P L "
                         f"F); refused before the game boots.")
    return "".join(c for c in LEGS if c == "K" or c in raw)


def predicted(cal: str | None, legs: str) -> tuple:
    """The word's registered reds among the rows the selected legs run."""
    if cal is None:
        return ()
    rows = catalog_rows(cal, legs)
    return tuple(r for r in WORDS[cal][1] if r in rows)


def catalog_rows(cal: str | None, legs: str) -> list:
    rows = [r for leg in legs for r in LEG_ROWS[leg]]
    if cal == "long":
        rows = [r for r in rows if r != "F-REASSERT"]        # a 24-tick re-fade lands on the 0.9 s timer: a coin flip
    return rows


def _check_load(cal: str | None, legs: str) -> None:
    if cal is not None and not predicted(cal, legs):
        raise SystemExit(f"coop_field_swap_timing: COOP_CALIBRATE={cal!r} reds {', '.join(WORDS[cal][1])}, which COOP_LEGS={legs!r} "
                         f"leaves out -- refused before the game boots.")


CAL_MODE = calibration()                 # at load: tools/play.py imports the scenario before its Session launches FF9
LEGS_SEL = legs_selected()
_check_load(CAL_MODE, LEGS_SEL)


def catalog(cal: str | None, legs: str) -> dict:
    cat = {r: CLAIMS[r] for r in catalog_rows(cal, legs)}
    if cal is not None:
        rows = ", ".join(predicted(cal, legs))
        cat["K-CAL-M"] = f"the `{cal}` lever was taken and every predicted red carries its marker ({MARKERS[cal]})"
        cat["K-CAL"] = f"the `{cal}` calibration: exactly {rows} red"
    return cat


# --------------------------------------------------------------------------------------------- reads (pure)
def swb(x) -> dict | None:
    b = cb.path(x, KEY)
    return b if isinstance(b, dict) else None


def sget(x, dotted: str, default=None):
    cur = swb(x)
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def nget(x, dotted: str, default=None):
    return cb.path(x, "netsync." + dotted, default)


def ival(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def now_ms(x) -> int | None:
    v = ival(sget(x, "clock.now_ms"))
    return v if v is not None and v >= 0 else None


def frame_of(x) -> int | None:
    return ival(cb.raw(x).get("frame"))


def core(line: str) -> str:
    """A Memoria.log line without its prefix (from "[NetSync]" on)."""
    i = (line or "").find("[NetSync]")
    return line[i:] if i >= 0 else (line or "")


def stamp_of(line: str) -> int:
    ok, t, _bare = BW.swap_parse_stamp(core(line))
    return t if ok else -1


def unstamped(line: str) -> str:
    return BW.swap_parse_stamp(core(line))[2]


def rose(a, b, by: int = 1) -> bool:
    """``b - a == by`` with both ints -- an ABSENT counter is never a 0 that stayed."""
    return ival(a) is not None and ival(b) is not None and b - a == by


def _fmt(parts) -> str:
    return ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)


def _verdict(parts, extra: str = "") -> tuple:
    return all(v for _, v in parts), _fmt(parts) + (f"; {extra}" if extra else "")


def windows(x) -> list:
    w = nget(x, "windows")
    return [d for d in w if isinstance(d, dict)] if isinstance(w, list) else []


def win_of(x, key) -> dict | None:
    return next((w for w in windows(x) if (w.get("win"), w.get("text")) == tuple(key)), None)


def cls_of(x, key) -> str | None:
    w = win_of(x, key)
    return w.get("cls") if w else None


def bcount(x) -> dict:
    """B's counters: orphan_closes (the dialogue's), and the swap block's holds / relocks."""
    return {"closes": ival(nget(x, "orphan_closes")), "holds": ival(sget(x, "orphan.holds")),
            "relocks": ival(sget(x, "orphan.relocks"))}


def first(samples, pred):
    return next((s for s in samples if _safe(pred, s)), None)


def _safe(pred, s) -> bool:
    try:
        return bool(pred(s))
    except (TypeError, KeyError, AttributeError, IndexError, ValueError):
        return False


def frame_ms(samples) -> float:
    """One MEASURED frame: the median positive step of `clock.now_ms` between consecutive samples (`stateevery 1`), else 1/30 s."""
    ts = [now_ms(s) for s in samples]
    steps = [b - a for a, b in zip(ts, ts[1:]) if a is not None and b is not None and b > a]
    return float(statistics.median(steps)) if steps else FRAME_MS_DEFAULT


def lines_with(lines, needle: str) -> list:
    return [ln for ln in lines if needle in ln]


# --------------------------------------------------------------------------------------------- K judges (pure)
#: review fix F09's diagnostic line, once per SelfTest call before the proof line: REPORTED in K-PROOF's detail, never judged (it
#: records the Unity Mono figure; it has no class, no stamp and no `selftest: ` text)
PROOF_COST = "[NetSync] field swap proof cost: "


def judge_proof(lines, verdict) -> tuple:
    """K-PROOF: the swap proof line OK (battlewire.SWAP_PROOF_RE: every constant pinned; N and M never against literals), no FAIL,
    the published verdict 'ok', and the dialogue selftest's OK line (B changes its KeyScript row) with no FAIL. The proof's cost line
    (PROOF_COST) is reported in the detail, never judged."""
    rx = re.compile(BW.SWAP_PROOF_RE)
    ok_line = [ln for ln in lines if rx.search(ln)]
    fail = [ln for ln in lines if BW.PROOF_FIELD_SWAP + "FAIL (" in ln]
    dlg_ok = [ln for ln in lines if "dialogue authority selftest: OK (" in ln]
    dlg_fail = [ln for ln in lines if "dialogue authority selftest: FAIL" in ln]
    m = rx.search(ok_line[0]) if ok_line else None
    parts = [("the OK line", len(ok_line) == 1), ("no FAIL line", not fail), ("selftest 'ok'", verdict == "ok"),
             ("the dialogue selftest OK", bool(dlg_ok)), ("no dialogue FAIL", not dlg_fail)]
    cost = [ln.split(PROOF_COST, 1)[1] for ln in lines if PROOF_COST in ln]
    return _verdict(parts, f"verdict {verdict!r}" + (f"; rows {m.group(1)}, mutants {m.group(2)}, clock {m.group(3)} {m.group(4)} Hz "
                                                      f"{m.group(5)}" if m else "") + f"; {cb.grep(lines, 'selftest: FAIL')}"
                           + (f"; proof cost {cost[-1]}" if cost else "; no proof cost line (an engine before review fix F09)"))


def judge_clock(reads, have_kit: bool) -> tuple:
    """K-CLOCK (PURE): ``reads`` = [(kit qpc ms, kit wall ms, sample)]. -> (verdict, detail), verdict "green" | "unfit" | "skip".
    SKIP when the kit has no QPC (off Windows). UNFIT (the instrument unfit for the duo, DK-CLOCK) when `src` is not qpc (a
    Stopwatch may count from the process's own start), hz / hires are not published, fewer than CLOCK_MIN samples, or any sample's
    kit - engine difference leaves [0, its age + CLOCK_SLACK_MS]. Never a red row."""
    if not have_kit:
        return "skip", "SKIP: the kit has no QueryPerformanceCounter here (qpc_ms() is None, off Windows) -- K-CLOCK not judged"
    srcs = sorted({str(sget(s, "clock.src")) for _q, _w, s in reads})
    diffs, bad = [], []
    for q, w, s in reads:
        n, utc = now_ms(s), ival(sget(s, "clock.utc_ms"))
        if q is None or n is None:
            bad.append("an unreadable pair")
            continue
        age = max(0, w - utc) if utc is not None and utc >= 0 else 0
        d = q - n
        diffs.append(d)
        if not 0 <= d <= age + CLOCK_SLACK_MS:
            bad.append(f"kit - engine {d} ms (age {age} ms)")
    hz = [ival(sget(s, "clock.hz")) for _q, _w, s in reads]
    hires = [sget(s, "clock.hires") for _q, _w, s in reads]
    why = []
    if srcs != ["qpc"]:
        why.append(f"clock.src {srcs} (not qpc: a Stopwatch may count from the process's own start)")
    if not reads or not all(h is not None and h > 0 for h in hz):
        why.append("hz not published")
    if not reads or not all(isinstance(h, bool) for h in hires):
        why.append("hires not published")
    if len(reads) < CLOCK_MIN:
        why.append(f"{len(reads)} samples (< {CLOCK_MIN})")
    if bad:
        why.append(f"{len(bad)} samples off the band: {bad[:3]}")
    span = f"kit - engine {min(diffs)}..{max(diffs)} ms over {len(reads)} samples" if diffs else "no pairs"
    if why:
        return "unfit", "UNFIT (the instrument is unfit for the duo, DK-CLOCK): " + "; ".join(why) + f"; {span}"
    return "green", f"GREEN: src qpc, hz {hz[0]}, {'high-res' if hires[0] else 'low-res'}; {span}"


def lever_want(op: str, word: str):
    """What `levers` must read after `swap <op> <word>`: (key, the acceptable values)."""
    if op == "delay":
        return "delay_ms", (int(word),)
    if op == "hostctl":
        return "hostctl_off", (word == "off",)
    if op == "stamps":
        return "stamps", ("off",) if word == "off" else REST_LEVERS["stamps"]
    return op, REST_LEVERS[op] if word == "act" else (word,)


def lever_line(op: str, word: str) -> str:
    return BW.swap_harness_delay(int(word)) if op == "delay" else BW.swap_harness_lever_line(op, word)


def levers_at_rest(lv) -> bool:
    return (isinstance(lv, dict) and all(lv.get(k, "?") in vals for k, vals in REST_LEVERS.items())
            and ival(lv.get("delay_ms")) == 0 and lv.get("hostctl_off") is False)


def judge_levers(steps, rest_levers, clear_lines) -> tuple:
    """K-LEVER (PURE): ``steps`` = [{op, word, ok, why, lines, levers}] -- each acked, its ack line logged, its read-back; then
    ``rest_levers`` (after `clear`) all at rest and ``clear_lines`` holding the CLEAR line."""
    bad = []
    for s in steps:
        key, vals = lever_want(s["op"], s["word"])
        line = lever_line(s["op"], s["word"])
        lv = s.get("levers") if isinstance(s.get("levers"), dict) else {}
        if not s.get("ok"):
            bad.append(f"{s['op']} {s['word']}: refused ({str(s.get('why'))[:80]})")
        elif not any(core(ln) == line for ln in s.get("lines") or ()):
            bad.append(f"{s['op']} {s['word']}: no ack line")
        elif lv.get(key, "?") not in vals:
            bad.append(f"{s['op']} {s['word']}: levers.{key} {lv.get(key, '?')!r}")
    parts = [("every op acked, logged and read back", bool(steps) and not bad),
             ("clear: every lever at rest", levers_at_rest(rest_levers)),
             ("the CLEAR line", any(core(ln) == BW.swap_harness_clear(False) for ln in clear_lines or ()))]
    return _verdict(parts, f"{len(steps)} ops; " + ("; ".join(bad[:4]) or "none bad") + f"; rest {rest_levers!r}"[:300])


def judge_refuse(res: dict) -> tuple:
    """K-REFUSE (PURE): ``res`` = {name: why} for the four sends (why "" when it ACTED)."""
    parts = [("delay 5000: the usage line", BW.SWAP_USAGE in (res.get("delay") or "")),
             ("orphan maybe: the usage line", BW.SWAP_USAGE in (res.get("word") or "")),
             ("intent before bench 1: the bench refusal", BW.swap_refusal_bench("intent") in (res.get("bench") or "")),
             ("orphan old with co-op off: 'co-op is off'", BW.SWAP_REFUSAL_COOP_OFF in (res.get("off") or ""))]
    return _verdict(parts, "; ".join(f"{k}: {str(v)[:90]!r}" for k, v in res.items()))


def commit_minus_due(rec) -> int | None:
    rec = rec if isinstance(rec, dict) else {}
    c, d = ival(rec.get("commit_t")), ival(rec.get("due_t"))
    return c - d if c is not None and d is not None and c >= 0 and d >= 0 else None


def judge_release(rel_lines, levers_after, second_lines, rec, fms: float) -> tuple:
    """K-RELEASE (PURE): one release line (no pin-bench mirror tail: no pin bench ran), every lever at rest after the `reset`, the
    second `reset` silent, and the re-armed follow committing within one measured frame of its due (no delay leaked)."""
    want = BW.swap_harness_release(False)
    n = sum(1 for ln in rel_lines if core(ln).startswith("[NetSync] harness: swap levers released ("))
    cmd = commit_minus_due(rec)
    parts = [("one release line", n == 1 and any(core(ln) == want for ln in rel_lines)),
             ("every lever back", levers_at_rest(levers_after)),
             ("a second reset logs nothing", not any("harness: swap levers released" in ln for ln in second_lines)),
             ("the follow committed", cmd is not None),
             ("no delay leaked (commit - due <= 1 frame)", cmd is not None and 0 <= cmd <= fms + 1),
             ("last.delay_ms 0", ival((rec or {}).get("delay_ms")) == 0)]
    return _verdict(parts, f"commit - due {cmd} ms (frame {fms:.1f}); levers {levers_after!r}"[:400])


# --------------------------------------------------------------------------------------------- A judges (pure)
def judge_follow(rec, id0: int, away: int = AWAY) -> tuple:
    """A-FOLLOW (PURE): ``rec`` = `last` after the record closed, ``id0`` the id before the intent."""
    r = rec if isinstance(rec, dict) else {}
    ts = [ival(r.get(k)) for k in ("seen_t", "follow_t", "due_t", "commit_t", "land_t")]
    parts = [("one record (id +1)", ival(r.get("id")) == id0 + 1), ("open_by seen", r.get("open_by") == "seen"),
             ("seen <= follow <= due <= commit <= land", all(t is not None and t >= 0 for t in ts) and ts == sorted(ts)),
             ("follow_via intent", r.get("follow_via") == "intent"), ("land_via follow", r.get("land_via") == "follow"),
             (f"land_field {away}", ival(r.get("land_field")) == away),
             ("closed by line or window", r.get("state") == "done" and r.get("close_why") in ("line", "window"))]
    return _verdict(parts, f"id {r.get('id')} (was {id0}); t {ts}; close {r.get('close_why')!r}")


def _edge_lines(lines, rec, away: int) -> dict:
    """The record's edge lines: name -> (the lines, the t they must carry)."""
    r = rec if isinstance(rec, dict) else {}
    k = ival(r.get("id")) or 0
    cs = [core(ln) for ln in lines]
    return {"follow": ([c for c in cs if c.startswith(f"[NetSync] intent: following the peer to field {away} (parallel)")], r.get("follow_t")),
            "commit": ([c for c in cs if c.startswith(f"[NetSync] swap: follow-warp to field {away} committed ") and f"(swap #{k})" in c],
                       r.get("commit_t")),
            "land": ([c for c in cs if c.startswith(f"[NetSync] swap: landed on field {away} via the follow (swap #{k})")], r.get("land_t")),
            "close": ([c for c in cs if c.startswith(f"[NetSync] swap #{k} to field {away} (from ")], r.get("close_t"))}


def judge_stamp(lines, rec, away: int = AWAY) -> tuple:
    """A-STAMP (PURE): the follow line, L-COMMIT, L-LAND and L-CLOSE each logged once, each stamp EXACTLY its record key."""
    parts, seen = [], []
    for name, (ls, t) in _edge_lines(lines, rec, away).items():
        st = [stamp_of(c) for c in ls]
        parts.append((f"{name} stamp = its t", len(ls) == 1 and ival(t) is not None and t >= 0 and st == [t]))
        seen.append(f"{name} {st} vs {t}")
    return _verdict(parts, "; ".join(seen))


def judge_delay(rec1, rec2, fms: float, want2: int = 300) -> tuple:
    """A-DELAY (PURE): leg 1 (`delay 0`) and leg 2 (`delay want2`), each judged within its own follow (F6)."""
    d1, d2 = commit_minus_due(rec1), commit_minus_due(rec2)
    r1, r2 = rec1 if isinstance(rec1, dict) else {}, rec2 if isinstance(rec2, dict) else {}
    tol = fms + 1
    f1 = (ival(r1.get("commit_t")) or 0) - (ival(r1.get("follow_t")) or 0)
    f2 = (ival(r2.get("commit_t")) or 0) - (ival(r2.get("follow_t")) or 0)
    parts = [("leg 1: commit - due = 0 +- 1 frame", d1 is not None and abs(d1) <= tol),
             (f"leg 2: commit - due = {want2} +- 1 frame", d2 is not None and abs(d2 - want2) <= tol),
             (f"leg 2: last.delay_ms {want2}", ival(r2.get("delay_ms")) == want2),
             ("two records", ival(r1.get("id")) is not None and ival(r2.get("id")) is not None and r2["id"] > r1["id"])]
    return _verdict(parts, f"commit - due {d1} / {d2} ms (frame {fms:.1f}); reported: commit - follow {f1} / {f2} ms, "
                           f"difference {f2 - f1} ms")


_INNER_STAMP = re.compile(r" \(t \d+ ms\)")


def judge_word(lines) -> tuple:
    """A-WORD (PURE): every STAMPED line that is not an s164 class (battlewire.swap_line_class) matches an S163_FORMS form once its
    stamp and waited/shown tail are removed, and no such line carries a stamp anywhere but at its very end (the stamp goes after any
    closing ")": the `stamp_inside` shape); at least one s163 form line in the span (stamped or not: `stamps off` keeps it)."""
    bad, inside, stamped, forms = [], [], 0, 0
    for ln in lines:
        c = core(ln)
        has, _t, bare = BW.swap_parse_stamp(c)
        stripped = BW.swap_strip_line(c)[0]
        if BW.swap_s163_form(stripped):
            forms += 1
        if BW.swap_line_class(c) is not None:
            continue
        if _INNER_STAMP.search(bare if has else c):
            inside.append(c[:120])
        if has:
            stamped += 1
            if BW.swap_s163_form(stripped) is None:
                bad.append(stripped[:120])
    parts = [("an s163 line in the span", forms > 0), ("every stamped s163 line strips to its form", not bad),
             ("no stamp inside a line", not inside)]
    return _verdict(parts, f"{stamped} stamped s163 lines, {forms} form lines; bad: {bad[:3]}; inside: {inside[:2]}")


# --------------------------------------------------------------------------------------------- B judges (pure)
def hold_words(key) -> str:
    return BW.swap_place_stamp(f"[NetSync] dialogue orphan: win {key[0]} text {key[1]} held -- the host's control is off on my field",
                               False, -1)


def end_lines(lines, key) -> list:
    """The hold's end lines for ``key``: [(N ms, why words)]."""
    rx = re.compile(rf"\[NetSync\] dialogue orphan: win {key[0]} text {key[1]} -- the control hold ends after (-?\d+) ms \((.+)\)")
    out = []
    for ln in lines:
        m = rx.fullmatch(unstamped(ln))
        if m:
            out.append((int(m.group(1)), m.group(2)))
    return out


def not_on_screen(lines, key) -> list:
    return lines_with(lines, f"[NetSync] dialogue orphan: win {key[0]} text {key[1]} is not on the host's screen")


def host_closed(lines, key) -> list:
    return lines_with(lines, f"[NetSync] dialogue: win {key[0]} text {key[1]} closed (host seq")


def judge_b_host(samples, f_ack, key) -> tuple:
    """B-HOST (PURE): ``samples`` from the `hostscene 0` step on, ``f_ack`` its ack's frame: every term by f_ack + 2 frames."""
    win = [s for s in samples if frame_of(s) is not None and f_ack is not None and frame_of(s) <= f_ack + B_HOST_FRAMES]
    hf = lambda s: ival(nget(s, "host_flags"))                                             # noqa: E731
    parts = [("samples within 2 frames", bool(win)),
             ("host_flags b1 b0 clear, b3 set", any(hf(s) is not None and hf(s) >= 0 and hf(s) & 0x03 == 0 and hf(s) & 0x08 for s in win)),
             ("orphan.host_holds", any(sget(s, "orphan.host_holds") is True for s in win)),
             ("levers.hostctl_off", any(sget(s, "levers.hostctl_off") is True for s in win)),
             ("host_settled_ms >= 0", any((ival(nget(s, "host_settled_ms")) or -1) >= 0 for s in win)),
             ("the line tracked", any(win_of(s, key) for s in win))]
    return _verdict(parts, f"{len(win)} of {len(samples)} samples by frame {f_ack}+{B_HOST_FRAMES}; host_flags "
                           f"{sorted({str(nget(s, 'host_flags')) for s in win})}")


def judge_b_hold(samples, lines, key, b0) -> tuple:
    """B-HOLD (PURE): the hold window from `hostscene 0` (``b0`` the counters before it)."""
    b1 = bcount(samples[-1]) if samples else {}
    t = [now_ms(s) for s in samples if now_ms(s) is not None]
    span = (t[-1] - t[0]) if len(t) > 1 else 0
    parts = [("held the whole window", span >= HOLD_S * 1000 - 150),
             ("every sample locked", bool(samples) and all(cls_of(s, key) == "locked" for s in samples)),
             (f"host_settled_ms >= {SETTLE_MIN_MS}", bool(samples) and (ival(nget(samples[-1], "host_settled_ms")) or -1) >= SETTLE_MIN_MS),
             ("orphan_closes +0", rose(b0.get("closes"), b1.get("closes"), 0)), ("holds +1", rose(b0.get("holds"), b1.get("holds"))),
             ("one hold line", sum(1 for ln in lines if unstamped(ln) == hold_words(key)) == 1),
             ("no 'is not on the host's screen' line", not not_on_screen(lines, key))]
    return _verdict(parts, f"span {span} ms; cls {sorted({str(cls_of(s, key)) for s in samples})}; {cb.grep(lines, 'dialogue orphan')}")


def held_t0(samples) -> int | None:
    """The swap-clock time the hold began: the first sample with orphan.holding >= 1."""
    s = first(samples, lambda s: (ival(sget(s, "orphan.holding")) or 0) >= 1)
    return now_ms(s) if s is not None else None


def judge_b_release(samples, lines, key, b0, t_on, hold_t0) -> tuple:
    """B-RELEASE (PURE): ``samples`` from the `hostctl on` step (``t_on`` its swap-clock time), ``hold_t0`` the hold's first held
    sample (B-HOLD's), ``b0`` the counters before the step."""
    so = first(samples, lambda s: cls_of(s, key) == "orphaned")
    se = first(samples, lambda s: (ival(sget(s, "orphan.holding")) or 0) == 0)
    sc = first(samples, lambda s: (ival(nget(s, "orphan_closes")) or -1) >= (b0.get("closes") or 0) + 1)
    b1 = bcount(samples[-1]) if samples else {}
    ends = end_lines(lines, key)
    sampled = (now_ms(se) - hold_t0) if se is not None and hold_t0 is not None and now_ms(se) is not None else None
    t_o = now_ms(so) if so is not None else None
    t_c = now_ms(sc) if sc is not None else None
    parts = [("orphaned within 0.5 s", t_o is not None and t_on is not None and t_o - t_on <= RELEASE_ORPHAN_MS),
             ("one end line by control", len(ends) == 1 and ends[0][1] == BW.SWAP_HOLD_END_WORDS[BW.SWAP_HOLD_END_CONTROL]),
             ("N = the sampled hold +- 0.3 s", len(ends) == 1 and sampled is not None and abs(ends[0][0] - sampled) <= HOLD_N_TOL_MS),
             ("last_end control", bool(samples) and sget(samples[-1], "orphan.last_end") == "control"),
             ("the auto-close AutoReadMs later", t_o is not None and t_c is not None
              and AUTO_READ_MS - EARLY_MS <= t_c - t_o <= AUTO_READ_MS + LATE_MS),
             ("orphan_closes +1", rose(b0.get("closes"), b1.get("closes")))]
    return _verdict(parts, f"orphaned {None if t_o is None or t_on is None else t_o - t_on} ms after on; closed "
                           f"{None if t_o is None or t_c is None else t_c - t_o} ms after; end {ends}; sampled hold {sampled} ms")


def judge_b_blip(samples, lines_after_on, key, b0, t_relock_min_ms: int = AUTO_READ_MS + 1000) -> tuple:
    """B-BLIP (PURE): ``samples`` from the `hostctl on` step, ``lines_after_on`` the log since it, ``b0`` the counters before it."""
    k_o = next((i for i, s in enumerate(samples) if cls_of(s, key) == "orphaned"), None)
    k_l = next((i for i, s in enumerate(samples) if k_o is not None and i > k_o and cls_of(s, key) == "locked"), None)
    b1 = bcount(samples[-1]) if samples else {}
    t_l = now_ms(samples[k_l]) if k_l is not None else None
    t_end = now_ms(samples[-1]) if samples else None
    relock_lines = sum(1 for ln in lines_after_on if unstamped(ln) == hold_words(key))
    parts = [("orphaned", k_o is not None), ("then locked", k_l is not None), ("one relock line", relock_lines == 1),
             ("relocks +1", rose(b0.get("relocks"), b1.get("relocks"))),
             ("no auto-close", rose(b0.get("closes"), b1.get("closes"), 0) and not any(cls_of(s, key) is None for s in samples[k_l or 0:])),
             ("watched AutoReadMs + 1 s past the relock", t_l is not None and t_end is not None and t_end - t_l >= t_relock_min_ms - 100)]
    return _verdict(parts, f"relock lines {relock_lines}; counters {b0} -> {b1}; watched {None if t_l is None else t_end - t_l} ms")


def judge_b_scene(samples, lines, key, b0) -> tuple:
    """B-SCENE (PURE): ``samples`` / ``lines`` from the `hostscene 1` step on (``b0`` the counters before it)."""
    ends = end_lines(lines, key)
    busy = BW.SWAP_HOLD_END_WORDS[BW.SWAP_HOLD_END_BUSY]
    i_end = next((i for i, ln in enumerate(lines) if end_lines([ln], key)), None)
    i_cls = next((i for i, ln in enumerate(lines) if host_closed([ln], key)), None)
    b1 = bcount(samples[-1]) if samples else {}
    parts = [("one end line, the host busy", len(ends) == 1 and ends[0][1] == busy),
             ("the ADV closes it 'closed (host seq'", i_cls is not None), ("the end before the close", i_end is not None and i_cls is not None
                                                                         and i_end < i_cls),
             ("last_end busy", any(sget(s, "orphan.last_end") == "busy" for s in samples)),
             ("not by the orphan rule (orphan_closes +0)", rose(b0.get("closes"), b1.get("closes"), 0))]
    return _verdict(parts, f"end {ends}; {cb.grep(lines, 'dialogue orphan', 'closed (host seq')}")


def judge_b_blip2(samples, lines, key, b0) -> tuple:
    """B-BLIP2 (PURE): ``samples`` from the first line's open (before the orphan) to past the last off; ``b0`` the counters before."""
    s0 = first(samples, lambda s: cls_of(s, key) == "orphaned")
    k_c = next((i for i, s in enumerate(samples) if (ival(nget(s, "orphan_closes")) or -1) >= (b0.get("closes") or 0) + 1), None)
    t0 = now_ms(s0) if s0 is not None else None
    t_c = now_ms(samples[k_c]) if k_c is not None else None
    at_c = bcount(samples[k_c]) if k_c is not None else {}
    b1 = bcount(samples[-1]) if samples else {}
    relock_lines = sum(1 for ln in lines if unstamped(ln) == hold_words(key))
    parts = [("orphaned at t0", t0 is not None), ("closed", t_c is not None),
             ("one relock line", relock_lines == 1), ("relocks +1 at the close", rose(b0.get("relocks"), at_c.get("relocks"))),
             ("closed at t0 + AutoReadMs (+0.3 s)", t0 is not None and t_c is not None
              and AUTO_READ_MS - EARLY_MS <= t_c - t0 <= AUTO_READ_MS + BLIP2_LATE_MS),
             ("orphan_closes +1", rose(b0.get("closes"), b1.get("closes"))),
             ("nothing counted after the close", bool(at_c) and b1.get("relocks") == at_c.get("relocks")
              and b1.get("holds") == at_c.get("holds") and b1.get("closes") == at_c.get("closes"))]
    return _verdict(parts, f"closed {None if t0 is None or t_c is None else t_c - t0} ms after t0; relock lines {relock_lines}; "
                           f"{b0} -> at close {at_c} -> {b1}")


def judge_b_ctlon(samples, key, b0, t_settle) -> tuple:
    """B-CTLON (PURE): ``samples`` from `hostscene 0` (``t_settle`` its swap-clock time) with the bench host's control ON."""
    so = first(samples, lambda s: cls_of(s, key) == "orphaned")
    sc = first(samples, lambda s: (ival(nget(s, "orphan_closes")) or -1) >= (b0.get("closes") or 0) + 1)
    t_o, t_c = (now_ms(so) if so else None), (now_ms(sc) if sc else None)
    b1 = bcount(samples[-1]) if samples else {}
    parts = [("orphaned OrphanGraceMs after the settle", t_o is not None and t_settle is not None
              and GRACE_MS - EARLY_MS <= t_o - t_settle <= GRACE_MS + LATE_MS),
             ("auto-closed AutoReadMs later", t_o is not None and t_c is not None and AUTO_READ_MS - EARLY_MS <= t_c - t_o <= AUTO_READ_MS + LATE_MS),
             ("holds +0", rose(b0.get("holds"), b1.get("holds"), 0)), ("orphan_closes +1", rose(b0.get("closes"), b1.get("closes")))]
    return _verdict(parts, f"orphaned {None if t_o is None or t_settle is None else t_o - t_settle} ms after the settle, closed "
                           f"{None if t_o is None or t_c is None else t_c - t_o} ms after; {b0} -> {b1}")


# --------------------------------------------------------------------------------------------- C judges (pure)
def maps(lines, fld: int) -> int:
    return sum(1 for ln in lines if f"Map: {fld} " in ln or ln.rstrip().endswith(f"Map: {fld}"))


def pass_lines(lines, term: str, dest: int = C_DEST, src: int = C_FIELD) -> list:
    return [c for c in (core(ln) for ln in lines)
            if c.startswith(f"[NetSync] own Field({dest}) passes on field {src} -- the host's announced field ({term})")]


def cache_write_lines(lines, dest: int = C_DEST, src: int = C_FIELD) -> list:
    rx = re.compile(rf"\[NetSync\] intent cache: field {dest} \(nonce \d+\) cached on field {src} \(host lane -?\d+\)")
    return [ln for ln in lines if rx.fullmatch(unstamped(ln))]


def cache_clear(lines, reason: str, dest: int = C_DEST) -> list:
    return [ln for ln in lines if unstamped(ln) == f"[NetSync] intent cache: field {dest} cleared -- {reason}"]


def bounced(last) -> bool:
    r = last if isinstance(last, dict) else {}
    return r.get("own_verdict") == "bounce" and r.get("own_why") == "not-host"


def judge_c_bounce(last, lines, b0, b1) -> tuple:
    """C-BOUNCE (PURE): ``last`` the record right after the bounce's landing, ``b0`` / ``b1`` the swap blocks before / after."""
    r = last if isinstance(last, dict) else {}
    k = ival(r.get("id")) or 0
    land = [ln for ln in lines if unstamped(ln) == f"[NetSync] swap: landed on field {C_FIELD} via a bounce reload (swap #{k})"]
    parts = [("own_verdict bounce, own_why not-host", bounced(r)),
             ("counts.bounces +1", rose(cb.path(b0, "counts.bounces"), cb.path(b1, "counts.bounces"))),
             ("reloads +1", ival(r.get("reloads")) == 1 and (ival(r.get("reload_t")) or -1) >= 0),
             (f"landed on {C_FIELD} via a bounce reload (swap #K)", len(land) == 1),
             ("the record still open", r.get("state") == "open"),
             ("own.passes +0", rose(cb.path(b0, "own.passes"), cb.path(b1, "own.passes"), 0))]
    return _verdict(parts, f"own {r.get('own_verdict')!r}/{r.get('own_why')!r}, state {r.get('state')!r}, reloads {r.get('reloads')}; "
                           f"{cb.grep(lines, 'own Field(', 'via a bounce')}")


def judge_c_cache(lines, last, b0, b1) -> tuple:
    """C-CACHE (PURE)."""
    w = cache_write_lines(lines)
    p = pass_lines(lines, "cache")
    i_w = next((i for i, ln in enumerate(lines) if cache_write_lines([ln])), None)
    i_p = next((i for i, ln in enumerate(lines) if pass_lines([ln], "cache")), None)
    parts = [("the cache write line", bool(w)), ("the '(cache)' pass line once", len(p) == 1),
             ("written before the pass", i_w is not None and i_p is not None and i_w < i_p),
             ("own.by.cache +1", rose(cb.path(b0, "own.by.cache"), cb.path(b1, "own.by.cache"))),
             ("one 'Map: 352'", maps(lines, C_DEST) == 1),
             ("counts.bounces +0", rose(cb.path(b0, "counts.bounces"), cb.path(b1, "counts.bounces"), 0)),
             ("the Left clear (the cached field)", bool(cache_clear(lines, BW.intent_cache_left_reason(C_FIELD, C_DEST, C_DEST)))),
             ("no 'field 352 loaded' clear", not cache_clear(lines, BW.intent_cache_loaded_reason(C_DEST)))]
    return _verdict(parts, f"own {(last or {}).get('own_verdict')!r}; {cb.grep(lines, 'intent cache', 'own Field(')}")


def judge_c_pend(lines, last, b0, b1) -> tuple:
    """C-PEND (PURE, on a REACHED run)."""
    bad = [ln for ln in lines if re.search(rf"follow-warp to field {C_DEST} (cancelled|dropped|never landed)", ln)]
    parts = [("the '(pending)' pass line once", len(pass_lines(lines, "pending")) == 1),
             ("own.converted +1", rose(cb.path(b0, "own.converted"), cb.path(b1, "own.converted"))),
             ("one load of 352", maps(lines, C_DEST) == 1),
             ("fade.ends.own +1", rose(cb.path(b0, "fade.ends.own"), cb.path(b1, "fade.ends.own"))),
             ("no s154 cancelled / dropped / never-landed line", not bad)]
    return _verdict(parts, f"own {(last or {}).get('own_verdict')!r}/{(last or {}).get('own_why')!r}; {cb.grep(lines, 'own Field(')}")


def judge_c_age(lines, last, b0, b1) -> tuple:
    """C-AGE (PURE, the control)."""
    parts = [("the 'aged 2000 ms' clear", bool(cache_clear(lines, "aged 2000 ms"))), ("then a bounce", bounced(last)),
             ("counts.bounces +1", rose(cb.path(b0, "counts.bounces"), cb.path(b1, "counts.bounces")))]
    return _verdict(parts, cb.grep(lines, "intent cache", "own Field("))


def judge_c_src(lines, last, b0, b1, src: int = HOME) -> tuple:
    """C-SRC (PURE, the control): a cache on ``src``, then the warp to 351."""
    parts = [(f"the Left clear for {src}", bool(cache_clear(lines, BW.intent_cache_left_reason(src, C_FIELD, C_DEST)))),
             ("then a bounce", bounced(last)),
             ("counts.bounces +1", rose(cb.path(b0, "counts.bounces"), cb.path(b1, "counts.bounces")))]
    return _verdict(parts, cb.grep(lines, "intent cache", "own Field("))


def pend_reach(samples, last) -> tuple:
    """C-PEND's REACH (P4): the own-jump edge (`last.own_t` set, own_dest 352, from 351) with the last sample before own_t reading
    session.follow.pending 352. -> (reached, why)."""
    r = last if isinstance(last, dict) else {}
    t = ival(r.get("own_t"))
    if t is None or t < 0 or ival(r.get("own_dest")) != C_DEST or ival(r.get("from")) != C_FIELD:
        return False, f"no own jump to {C_DEST} from {C_FIELD} (own_t {r.get('own_t')}, own_dest {r.get('own_dest')}, from {r.get('from')})"
    before = [s for s in samples if now_ms(s) is not None and now_ms(s) < t]
    p = ival(nget(before[-1], "session.follow.pending")) if before else None
    if p != C_DEST:
        return False, f"the last sample before the own jump read session.follow.pending {p!r}, not {C_DEST}"
    return True, f"own jump at t {t} with pending {C_DEST}"


# --------------------------------------------------------------------------------------------- P judges (pure)
def flag_of(x, bit: int = P_FLAG):
    v = (cb.raw(x).get("flags") or {}).get(str(bit))
    return v if isinstance(v, bool) else None


def stages_lines(lines, dest: int = AWAY) -> list:
    rx = re.compile(rf"\[NetSync\] story pin: field {dest} stages intent (\d+)'s frame for its story, the latest frame for its party and "
                    r"dress \(age (-?\d+) ms; the latest differs at (\d+) story bytes\)")
    return [m for m in (rx.fullmatch(unstamped(ln)) for ln in lines) if m]


def judge_p_pin(flag, pin, last, lines) -> tuple:
    p = pin if isinstance(pin, dict) else {}
    st = stages_lines(lines)
    parts = [("flag 8720 = 0", flag is False), ("the stages line (1 story byte)", len(st) == 1 and int(st[0].group(3)) == 1),
             ("pin.last_use pin", p.get("last_use") == "pin"), ("last.story pin", (last or {}).get("story") == "pin")]
    return _verdict(parts, f"flag {flag!r}; last_use {p.get('last_use')!r} ({p.get('last_use_quality')!r}); {cb.grep(lines, 'story pin')}")


def judge_p_guard(flag, pin, why: str, quality: str | None = None) -> tuple:
    """P-AGED / P-LATE (PURE): the flag from the latest frame (1), and the pin's why (and, for P-LATE, its quality)."""
    p = pin if isinstance(pin, dict) else {}
    parts = [("flag 8720 = 1", flag is True), (f"pin.last_use {why}", p.get("last_use") == why)]
    if quality is not None:
        parts.append((f"pin.last_use_quality {quality}", p.get("last_use_quality") == quality))
    return _verdict(parts, f"flag {flag!r}; pin {p.get('last_use')!r} / {p.get('last_use_quality')!r}")


def judge_p_other(flag, pin, other0) -> tuple:
    p = pin if isinstance(pin, dict) else {}
    held = [h for h in (p.get("held") or []) if isinstance(h, dict)]
    parts = [("flag 8720 = 1", flag is True), (f"the held entry still names {AWAY}", any(ival(h.get("field")) == AWAY for h in held)),
             ("pin.other +1", rose(other0, p.get("other")))]
    return _verdict(parts, f"flag {flag!r}; held {held!r}; other {other0} -> {p.get('other')}"[:300])


def judge_p_party(flag, pin, mirror_before, c: int, mirror_after, clear_lines) -> tuple:
    p = pin if isinstance(pin, dict) else {}
    parts = [("flag 8720 = 0 (the story from the pin)", flag is False),
             (f"mirror_party[1] = {c} (the party from the latest frame)", isinstance(mirror_before, list) and len(mirror_before) > 1
              and mirror_before[1] == c),
             ("pin.last_party latest", p.get("last_party") == "latest"),
             ("after the clear: mirror_party null", mirror_after is None),
             ("the clear line names the party mirror", any(core(ln) == BW.swap_harness_clear(True) for ln in clear_lines))]
    return _verdict(parts, f"flag {flag!r}; mirror {mirror_before!r} -> {mirror_after!r}; {cb.grep(clear_lines, 'swap CLEAR')}")


# --------------------------------------------------------------------------------------------- L judges (pure)
def _l_landed_line(dest: int):
    return re.compile(rf"\[NetSync\] transition intent \d+: I landed on field {dest} after -?\d+ ms -- section 4 stays until my body "
                      r"stands there, 2 s since the emit and 1 s since this landing")


def _l_landed_ms(samples) -> int:
    return max([v for v in (ival(sget(s, "intent.landed_ms")) for s in samples) if v is not None] or [-1])


def judge_l_land(samples, lines, dest: int = AWAY) -> tuple:
    """L-LAND (PURE): the landing hook's evidence that OUTLIVES the intent's end -- the 'I landed' line (NoteIntentLanded prints it
    at the hook under either lever) and `intent.landed_ms` >= 0 in some sample (`_intentLandedMs` survives the end; only the next
    emit or a session reset clears it). The sample with `intent.landing` on_intent and the intent active is REPORTED, never
    required: `intent.landing` reads null once the intent ends, and under `swap life old` s163's rule ends it at the first L4 step
    once the body is bound, which can run in the hook's own frame (StartEvents and updateModelsToBeAdded follow the hook), so that
    sample may never be published -- and L-LAND is lever `none` (`life` reddens only L-STANDS)."""
    hook = [s for s in samples if sget(s, "intent.landing") == "on_intent" and sget(s, "intent.active") is True]
    landed = _l_landed_ms(samples)
    rx = _l_landed_line(dest)
    parts = [("the 'I landed' line", any(rx.fullmatch(unstamped(ln)) for ln in lines)), ("intent.landed_ms >= 0", landed >= 0)]
    return _verdict(parts, f"landing {sorted({str(sget(s, 'intent.landing')) for s in samples})}; on_intent with the intent active "
                           f"{'seen' if hook else 'not seen (reported, not required)'}; landed_ms {landed}; "
                           f"{cb.grep(lines, 'transition intent')}")


def l_land_void(samples, lines, cal: str | None, dest: int = AWAY) -> str | None:
    """L-LAND's VOID reason (PURE), or None. Only under the `life` calibration (`swap life old`): the run ends with last_end old, no
    'I landed' line and landed_ms -1 in every sample -- s163's rule ended the intent BEFORE the landing hook ran (the R1 hole), so
    the hook had no live intent to land. VOID counts neither as an unpredicted red nor as a pass; under any other word the same
    evidence is a real red."""
    if cal != "life":
        return None
    fin = samples[-1] if samples else {}
    rx = _l_landed_line(dest)
    if sget(fin, "intent.last_end") == "old" and _l_landed_ms(samples) < 0 and not any(rx.fullmatch(unstamped(ln)) for ln in lines):
        return ("s163's rule (`swap life old`) ended the intent before the landing hook ran (last_end old, no 'I landed' line, "
                "landed_ms -1): the R1 hole")
    return None


def judge_l_stands(samples) -> tuple:
    """L-STANDS (PURE): ``samples`` across the life; landed_ms is read from the samples (it may reset at the end)."""
    fin = samples[-1] if samples else {}
    life = ival(sget(fin, "intent.last_life_ms"))
    landed = max([v for v in (ival(sget(s, "intent.landed_ms")) for s in samples) if v is not None] or [-1])
    gap = life - max(BW.INTENT_MIN_LIFE_MS, landed + BW.INTENT_LAND_TAIL_MS) if life is not None and landed >= 0 else None
    parts = [("last_end stands", sget(fin, "intent.last_end") == "stands"), ("landed_ms read", landed >= 0),
             ("life - max(2000, landed + 1000) in [0, 400]", gap is not None and 0 <= gap <= 400)]
    return _verdict(parts, f"last_end {sget(fin, 'intent.last_end')!r}, life {life} ms, landed {landed} ms, gap {gap}")


# --------------------------------------------------------------------------------------------- F judges (pure)
def fade_window(samples) -> list:
    """The samples from the follow's start to its due, on the swap clock: [fade.last.due_t - fade.last.ms, fade.last.due_t] (the
    follow's own; `last.follow_t` is a JOINED record's first follow)."""
    fin = samples[-1] if samples else {}
    t1, ms = ival(sget(fin, "fade.last.due_t")), ival(sget(fin, "fade.last.ms"))
    if t1 is None or ms is None or t1 < 0 or ms < 0:
        return []
    t0 = t1 - ms
    return [s for s in samples if now_ms(s) is not None and t0 <= now_ms(s) <= t1]


def _fade_parts(fl, want: dict, ranges: dict) -> list:
    f = fl if isinstance(fl, dict) else {}
    parts = [("the engine ran the follow fade (fade.last set)", f.get("path") is not None and f.get("by") is not None),
             (f"fade.last.field {AWAY}", ival(f.get("field")) == AWAY)]
    for k, v in want.items():
        parts.append((f"{k} {v}", f.get(k) == v))
    for k, (lo, hi) in ranges.items():
        x = ival(f.get(k))
        parts.append((f"{k} {lo if lo is not None else ''}..{hi if hi is not None else ''}",
                      x is not None and x >= 0 and (lo is None or x >= lo) and (hi is None or x <= hi)))
    return parts


def _fade_detail(fl) -> str:
    f = fl if isinstance(fl, dict) else {}
    return ("fade.last " + ", ".join(f"{k} {f.get(k)!r}" for k in ("path", "action", "frames", "by", "primed", "ms", "ticks",
                                                                    "view_start", "backlog_start")))


def judge_fade(row: str, samples, lines=(), b0=None) -> tuple:
    """Every F row (PURE): ``samples`` across the follow (the last one after its due), ``lines`` its log, ``b0`` the swap block before
    the intent. Each row's terms as SWAP-TIMING-S164.md registers them."""
    fin = samples[-1] if samples else {}
    fl = sget(fin, "fade.last")
    win = fade_window(samples)
    cur = [ival(sget(s, "fade.cur_now")) for s in win]
    extra = []
    if row == "F-FAST":
        parts = _fade_parts(fl, {"path": "fast", "action": "fade", "frames": BW.FADE_FAST_FRAMES, "by": "black", "primed": True},
                            {"ticks": (12, 14), "ms": (None, 599)})
    elif row == "F-3X":
        parts = _fade_parts(fl, {}, {"ms": (None, 249), "ticks": (12, 17)})    # == duo DF-3X (the Prime at 3x, a 2-tick batch)
    elif row == "F-BLACK":
        bt = max([v for v in (ival(sget(s, "fade.black_ticks")) for s in samples) if v is not None] or [-1])
        parts = _fade_parts(fl, {"view_start": "black", "action": "join", "by": "black"}, {"ms": (None, 249)})
        parts += [("black_ticks >= 3", bt >= 3),
                  ("no cur_now under 248 to the due", bool(win) and all(c is not None and c >= BW.FADE_BLACK_FLOOR for c in cur))]
        extra.append(f"black_ticks {bt}; cur_now {sorted(set(cur))[:6]}")
    elif row == "F-JOIN":
        left = next((v for v in (ival(sget(s, "fade.left_start")) for s in samples) if v is not None and v >= 0), None)
        ticks = ival((fl or {}).get("ticks"))
        parts = _fade_parts(fl, {"view_start": "heading", "action": "join"}, {})
        parts += [("left <= 8", left is not None and left <= 8),
                  ("due within left + 3 + 2 ticks", left is not None and ticks is not None and 0 <= ticks <= left + BW.FADE_JOIN_GRACE_TICKS + 2)]
        extra.append(f"left {left}")
    elif row == "F-HURRY":
        parts = _fade_parts(fl, {"action": "hurry", "frames": BW.FADE_FAST_FRAMES, "by": "black"}, {"ticks": (0, 14)})
        parts.append(("cur_now never drops", bool(win) and all(c is not None for c in cur)
                      and all(b >= a for a, b in zip(cur, cur[1:]))))
        extra.append(f"cur_now {cur[:12]}")
    elif row == "F-OPEN":
        parts = _fade_parts(fl, {"backlog_start": "open", "path": "backlog", "by": "timer"}, {"ms": (FADE_TIMER_MIN_MS, None)})
    elif row == "F-AHEAD":                               # path backlog too: under `fade old` the start still READS the backlog
        parts = _fade_parts(fl, {"backlog_start": "ahead", "path": "backlog", "by": "timer"}, {})
    elif row == "F-AGED":
        parts = _fade_parts(fl, {"path": "fast"}, {})
    elif row == "F-RECHECK":
        held = any(sget(s, "fade.held") is True for s in samples)
        parts = _fade_parts(fl, {"path": "fast", "by": "recheck"}, {"ms": (FADE_TIMER_MIN_MS, None)})
        parts.append(("held", held))
    elif row == "F-REASSERT":
        rl = [ln for ln in lines if core(ln).startswith("[NetSync] follow fade: the fade slot turned away from black mid-follow (")]
        parts = _fade_parts(fl, {"by": "black"}, {})
        parts += [("one reassert line", len(rl) == 1),
                  ("fade.reasserts +1", rose(cb.path(b0, "fade.reasserts"), sget(fin, "fade.reasserts")))]
    elif row == "F-KEY":
        parts = _fade_parts(fl, {"backlog_start": "key", "path": "backlog", "by": "timer"}, {"ms": (FADE_TIMER_MIN_MS, None)})
    else:
        raise KeyError(row)
    return _verdict(parts, "; ".join([_fade_detail(fl)] + extra))


# --------------------------------------------------------------------------------------------- the calibration (pure)
MARKERS = {
    "stamps": "the record's edges set (follow, commit, land) with no '(t N ms)' on the follow line and no `[NetSync] swap` line",
    "delay": "leg 2's commit - due within 1 frame of 0 and last.delay_ms 0 (the lever was 0)",
    "orphan": "s163's rule under the held control: orphan.host_holds true with holds +0 and relocks +0, the line orphaned or never held",
    "own": "own_verdict bounce / own_why not-host with the term's input there (the cache written, or pending 352), no pass line",
    "nocache": "the cache written, then own_verdict bounce with by.cache +0",
    "pin": "flag 8720 = 1 with pin.last_use lever and pin.last_use_quality pre (the capture still ran)",
    "life": "intent.last_end old (s163's self-clear)",
    "fade": "fade.last.path old (today's start and commit)",
    "long": "fade.last path fast with frames 24 (E off)",
    "nogate": "fade.last path fast with a backlog that would have gated (or, F-RECHECK, never held)",
    "norecheck": "fade.last path fast, never held, by black",
    "nohurry": "fade.last action join on a heading screen with more than 12 ticks left",
}


def marker(word: str, row: str, ev) -> tuple:
    """A predicted red's marker (PURE): ``ev`` the evidence the row's leg kept (ctx.marks[row]). -> (ok, detail)."""
    ev = ev if isinstance(ev, dict) else {}
    if word == "stamps":
        rec, lines = ev.get("rec") or {}, ev.get("lines") or []
        fl = [core(ln) for ln in lines if core(ln).startswith(f"[NetSync] intent: following the peer to field {AWAY} (parallel)")]
        parts = [("the record ran", all((ival(rec.get(k)) or -1) >= 0 for k in ("follow_t", "commit_t", "land_t"))),
                 ("the follow line unstamped", bool(fl) and all(stamp_of(c) < 0 for c in fl)),
                 ("no swap line", not any(BW.swap_line_class(core(ln)) == "instrument" for ln in lines))]
    elif word == "delay":
        rec = ev.get("rec") or {}
        d = commit_minus_due(rec)
        parts = [("commit - due within 1 frame of 0", d is not None and abs(d) <= (ev.get("frame") or FRAME_MS_DEFAULT) + 1),
                 ("last.delay_ms 0", ival(rec.get("delay_ms")) == 0)]
    elif word == "orphan":
        samples, b0 = ev.get("samples") or [], ev.get("b0") or {}
        b1 = bcount(samples[-1]) if samples else {}
        key = ev.get("key")
        parts = [("orphan.host_holds witnessed", any(sget(s, "orphan.host_holds") is True for s in samples)),
                 ("holds +0", rose(b0.get("holds"), b1.get("holds"), 0)), ("relocks +0", rose(b0.get("relocks"), b1.get("relocks"), 0)),
                 ("the line orphaned or never held", key is not None and (any(cls_of(s, key) == "orphaned" for s in samples)
                                                                           or bool(not_on_screen(ev.get("lines") or [], key))
                                                                           or not end_lines(ev.get("lines") or [], key)))]
    elif word in ("own", "nocache"):
        last, lines = ev.get("last") or {}, ev.get("lines") or []
        if row == "C-PEND":
            parts = [("bounce / not-host", bounced(last)), ("pending 352 before the jump", ev.get("pending") == C_DEST),
                     ("the L-OWN bounce line", any(f"bounced to a reload of {C_FIELD}" in ln for ln in lines)),
                     ("no '(pending)' line", not pass_lines(lines, "pending"))]
        else:
            parts = [("the cache written", bool(cache_write_lines(lines))), ("bounce / not-host", bounced(last)),
                     ("no '(cache)' line", not pass_lines(lines, "cache"))]
            if word == "nocache":
                parts.append(("by.cache +0", rose(cb.path(ev.get("b0"), "own.by.cache"), cb.path(ev.get("b1"), "own.by.cache"), 0)))
    elif word == "pin":
        pin = ev.get("pin") or {}
        parts = [("flag 8720 = 1", ev.get("flag") is True), ("pin.last_use lever", pin.get("last_use") == "lever"),
                 ("pin.last_use_quality pre", pin.get("last_use_quality") == "pre")]
    elif word == "life":
        parts = [("intent.last_end old", (ev.get("intent") or {}).get("last_end") == "old")]
    else:                                                # the fade words
        fl = ev.get("fade") or {}
        if word == "fade":
            parts = [("path old", fl.get("path") == "old")]
        elif word == "long":
            parts = [("path fast", fl.get("path") == "fast"), ("frames 24", ival(fl.get("frames")) == BW.FADE_OLD_FRAMES)]
        elif word == "nohurry":
            parts = [("action join", fl.get("action") == "join"), ("heading", fl.get("view_start") == "heading"),
                     ("more than 12 ticks left", (ival(ev.get("left")) or -1) > BW.FADE_FAST_FRAMES)]
        elif row == "F-RECHECK":                         # nogate / norecheck: the gate never held, the black committed
            parts = [("path fast", fl.get("path") == "fast"), ("never held", ev.get("held") is False), ("by black", fl.get("by") == "black")]
        else:                                            # nogate on OPEN / AHEAD / KEY: the fast path over a backlog
            parts = [("path fast", fl.get("path") == "fast"), ("a backlog seen", fl.get("backlog_start") in ("open", "ahead", "key"))]
    return _verdict(parts)


def judge_cal(word: str, failed, void, pred) -> tuple:
    """K-CAL (PURE): exactly the predicted rows red. A predicted row that read UNREACHED / VOID fails the exactness (never a 'not
    green'); every predicted row UNREACHED is VOID, never a pass; a VOID row elsewhere is reported, not counted as a red."""
    pred = set(pred)
    failed, void = set(failed) - set(FINALS), set(void)
    unreached = sorted(pred & void)
    if pred and set(unreached) == pred:
        return False, f"VOID: every predicted red read UNREACHED ({', '.join(unreached)})"
    missing = sorted(pred - failed - void)
    extra = sorted(failed - pred - void)
    ok = not missing and not unreached and not extra
    return ok, (f"`{word}`: predicted reds that stayed GREEN: {missing or 'none'}; predicted reds UNREACHED: {unreached or 'none'}; "
                f"unpredicted reds: {extra or 'none'}; VOID elsewhere: {sorted(void - pred) or 'none'}")


# --------------------------------------------------------------------------------------------- the run
class Ctx:
    def __init__(self, cal: str | None, legs: str):
        self.cal = cal
        self.legs = legs
        self.ready = False
        self.keeper_uid: int | None = None
        self.clock = ("skip", "not run")
        self.void: set = set()
        self.marks: dict = {}
        self.lever_taken = False
        self.delta_ms: int | None = None
        self.fms = FRAME_MS_DEFAULT


def _ns(g, sub: str, *args) -> tuple:
    return cb.try_ns(g, sub, *args)


def _must(g, sub: str, *args):
    try:
        return cb.ns_verb(g, sub, *args)
    except HarnessError as err:
        raise HarnessError(f"netsync {sub} {' '.join(str(a) for a in args)} refused: {str(err)[:240]}")


def _swap(g, *args):
    return _must(g, "swap", *args)


def _try_full(g, sub: str, *args) -> str:
    """The step's refusal IN FULL ("" when it acted): cb.try_ns cuts at 400 characters, and the swap usage line is longer."""
    try:
        cb.ns_verb(g, sub, *args)
        return ""
    except HarnessError as err:
        return str(err)


def _span_clear(g, timeout: float = BW.SWAP_RECORD_SPAN_MS / 1000.0 + 6.0) -> None:
    """Wait until the last record can no longer collect edges: JoinRule joins an edge for the same destination to ANY live record
    (open, landed or done) within RecordSpanMs of its open_t, so a second follow to AWAY inside that span is the SAME record."""
    def clear(s) -> bool:
        st, t_open, n = sget(s, "last.state"), ival(sget(s, "last.open_t")), now_ms(s)
        return st is None or t_open is None or t_open < 0 or (n is not None and n - t_open >= BW.SWAP_RECORD_SPAN_MS + 200)
    if cb.poll(g, clear, timeout, "the last swap record out of its span") is None:
        raise HarnessError("the last swap record never left its RecordSpanMs span")


def _void(led: cb.Ledger, ctx: Ctx, rows, why: str) -> None:
    for r in rows:
        if r in led.catalog and r not in led.done:
            ctx.void.add(r)
            led.check(r, False, f"VOID: {why}")


def _unreached(led: cb.Ledger, ctx: Ctx, rows, why: str) -> None:
    for r in rows:
        if r in led.catalog and r not in led.done:
            ctx.void.add(r)
    led.unreached(rows, why)


def watch(g, seconds: float, until=None, t0: float | None = None, on_sample=None) -> tuple:
    """Every distinct publish for ``seconds`` (or until ``until(sample)``), each a raw dict stamped ``_t`` (seconds since ``t0``).
    ``on_sample(sample)`` runs on each (a pager, a scheduled send). -> (samples, the sample that ended it or None)."""
    t0 = time.time() if t0 is None else t0
    out, seen, hit = [], None, None
    deadline = time.time() + seconds
    while time.time() < deadline:
        st = g.state
        if st.frame != seen:
            seen = st.frame
            d = dict(cb.raw(st))
            d["_t"] = time.time() - t0
            out.append(d)
            if on_sample is not None:
                on_sample(d)
            if until is not None and _safe(until, d):
                hit = d
                break
        time.sleep(0.004)
    return out, hit


def _free_on(g, fid: int, timeout: float = ARRIVE_S) -> tuple:
    deadline = time.time() + timeout
    st = g.state
    while time.time() < deadline:
        st = g.state
        if st.field_id == fid and st.control and not st.dialog_open:
            return True, ""
        g.wait_frames(6)
    return False, f"no control on {fid}: field {st.field_id} control {st.control} dialog {st.dialog_open}"


def _home(g) -> None:
    """Back on HOME with control and no line (a warp when elsewhere)."""
    if g.state.field_id != HOME:
        g.warp(HOME)
        g.wait_frames(20)
    ok, why = _free_on(g, HOME)
    if not ok:
        raise HarnessError(why)


def _arm(g) -> None:
    """The selftest role, the field-gate bench, a publish every frame."""
    _must(g, "selftest", 1)
    st = cb.poll(g, lambda s: bool((s.netsync or {}).get("forced")) and bool((s.netsync or {}).get("selftest")), 5.0, "the forced role")
    if st is None:
        raise HarnessError("the forced selftest role never came up")
    _must(g, "bench", 1)
    try:
        g.state_every(1)
    except HarnessError as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]}) -- every publish read at the default cadence")


def _block(g) -> dict:
    return dict(swb(g.state) or {})


def landed_after(s, dest: int, c0: int) -> bool:
    """On ``dest`` after a commit newer than ``c0``. The field flip IS the landing: a record's own land_t is no witness, because a
    landing on a record that is already DONE but still inside RecordSpanMs is IGNORED by JoinRule (no land_t, no reload_t), while the
    commit edge before it JOINS that record (a later F follow to AWAY does exactly this)."""
    c = ival(sget(s, "last.commit_t"))
    return (s.get("field") or {}).get("id") == dest and c is not None and c > c0


def _follow_to(g, dest: int, *, until_done: bool = False, timeout: float = FOLLOW_S, extra=None) -> tuple:
    """`swap intent <dest>` and watch to its landing (or the record's close). -> (samples, lines, the final `last`)."""
    c0 = ival(sget(g.state, "last.commit_t"))
    c0 = c0 if c0 is not None else -1
    at = cb.mark(g)
    t0 = time.time()
    _swap(g, "intent", dest)
    if extra is not None:
        extra()
    samples, hit = watch(g, timeout, until=lambda s: landed_after(s, dest, c0), t0=t0)
    if until_done and hit is not None:
        more, _ = watch(g, CLOSE_S, until=lambda s: sget(s, "last.state") == "done", t0=t0)
        samples += more
    return samples, cb.new(g, at), (sget(samples[-1], "last") if samples else None) or {}


def run(g, field: int | None = None):
    cal, legs = CAL_MODE, LEGS_SEL                       # read at load: an unknown word or leg never reached a booted game
    st0 = cb.poll(g, lambda s: s.netsync is not None, 15.0, "the netsync block (protocol 5)") or g.state
    ctx = Ctx(cal, legs)
    led = cb.Ledger(g, catalog(cal, legs), finals=FINALS, width=1400)
    if field is not None:
        g.note(f"--field {field} is ignored: the bench uses {HOME} (HOME) and {AWAY} (AWAY), and 351 for leg C")
    try:
        if not cb.has(st0, PROBE):
            _unreached(led, ctx, [r for r in led.catalog if r not in FINALS],
                       "this engine publishes no `netsync.swap` (s163 or older) -- the run is refused")
            return
        ctx.ready = _setup(g, ctx, led)
        if not ctx.ready:
            return
        _leg_k(g, ctx, led)
        for leg, fn in (("A", _leg_a), ("B", _leg_b), ("C", _leg_c), ("P", _leg_p), ("L", _leg_l), ("F", _leg_f)):
            if leg in legs:
                _guard(g, ctx, led, LEG_ROWS[leg], lambda fn=fn: fn(g, ctx, led))
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        _unreached(led, ctx, led.pending(), f"the run raised ({str(err)[:200]})")
    finally:
        for step in (lambda: _ns(g, "hostscene", 0), lambda: _ns(g, "lock", 0), lambda: _ns(g, "swap", "clear")):
            try:
                step()
            except (HarnessError, AttributeError):
                pass
        g.note(f"K-CLOCK: {ctx.clock[1]}")
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'field-swap-' + (cal or 'plain'))}")
        for r in led.pending():
            if r not in FINALS:
                ctx.void.add(r)
        led.close("not reached: the run ended before this check")
        if cal is not None:
            pred = predicted(cal, legs)
            marks = {r: marker(cal, r, ctx.marks[r]) if r in ctx.marks else (False, "NO RUN") for r in pred}
            led.check("K-CAL-M", ctx.lever_taken and all(ok for ok, _ in marks.values()),
                      f"lever {'taken' if ctx.lever_taken else 'NOT TAKEN'}; " + "; ".join(f"{r}: {d}" for r, (_ok, d) in marks.items()))
            ok, detail = judge_cal(cal, led.failed(), ctx.void, pred)
            led.check("K-CAL", ok, detail)
        led.close(final=True)


def _guard(g, ctx: Ctx, led: cb.Ledger, rows: tuple, fn) -> None:
    todo = [r for r in rows if r in led.catalog and r not in led.done]
    if not todo:
        return
    try:
        fn()
    except HarnessError as err:
        _unreached(led, ctx, todo, f"the leg raised: {str(err)[:300]}")
    except Exception as err:                             # noqa: BLE001 - a BENCH bug: red and loud, the run goes on
        g.note(f"{'/'.join(todo)} FAULTED (a bench bug, not a verdict): {err!r}"[:400])
        _unreached(led, ctx, todo, f"the leg FAULTED (a bench bug): {err!r}"[:300])
    _unreached(led, ctx, todo, "the leg recorded nothing")


def _setup(g, ctx: Ctx, led: cb.Ledger) -> bool:
    cb.provenance(g)
    why = ""
    if getattr(g, "attach", False):
        why = "refused: --attach (a reused process carries earlier counters and records)"
    else:
        try:
            g.newgame()
            g.warp(HOME)
            g.wait_frames(30)
            ok, why = _free_on(g, HOME)
            if ok:
                why = ""
                try:
                    g.no_encounters(True)
                except (HarnessError, AttributeError) as err:
                    g.note(f"noencounter refused ({str(err)[:120]})")
                _must(g, "selftest", 1)
                try:
                    g.state_every(1)
                except HarnessError as err:
                    g.note(f"stateevery 1 refused ({str(err)[:120]})")
        except HarnessError as err:
            why = f"the setup raised: {str(err)[:300]}"
    if why:
        _unreached(led, ctx, [r for r in led.catalog if r not in FINALS], why)
        return False
    return True


# ---- K
def _leg_k(g, ctx: Ctx, led: cb.Ledger) -> None:
    cb.wait_log(g, 0, BW.PROOF_FIELD_SWAP, timeout=SELFTEST_S)   # the proof block logs once per process: the WHOLE log is read
    st = cb.poll(g, lambda s: sget(s, "selftest") is not None, SELFTEST_S, "netsync.swap.selftest") or g.state
    ok, detail = judge_proof(cb.log_lines(g), sget(st, "selftest"))
    led.check("K-PROOF", ok, detail)
    _k_clock(g, ctx)
    _guard(g, ctx, led, ("K-REFUSE",), lambda: _k_refuse(g, ctx, led))
    _guard(g, ctx, led, ("K-LEVER",), lambda: _k_lever(g, ctx, led))
    _guard(g, ctx, led, ("K-RELEASE",), lambda: _k_release(g, ctx, led))
    ns = g.state.netsync or {}
    if not (ns.get("forced") and ns.get("selftest") and ns.get("bench")):
        _arm(g)                                          # a K-RELEASE that failed between its `reset` and its re-arm
    _home(g)


def _k_clock(g, ctx: Ctx) -> None:
    have = _qpc_ms is not None and _qpc_ms() is not None
    reads = []
    if have:
        out, seen = [], None
        deadline = time.time() + CLOCK_WATCH_S
        while time.time() < deadline and len(out) < CLOCK_MIN + 10:
            st = g.state
            if st.frame != seen:
                seen = st.frame
                out.append((_qpc_ms(), int(time.time() * 1000), dict(cb.raw(st))))
            time.sleep(0.004)
        reads = out
    ctx.clock = judge_clock(reads, have)
    g.note(f"K-CLOCK (a load-time precondition, never a red row): {ctx.clock[1]}")


def _k_refuse(g, ctx: Ctx, led: cb.Ledger) -> None:
    res = {}
    for name, args in (("delay", ("delay", 5000)), ("word", ("orphan", "maybe")), ("bench", ("intent", AWAY))):
        res[name] = _try_full(g, "swap", *args)
    _must(g, "selftest", 0)
    cb.poll(g, lambda s: not (s.netsync or {}).get("forced"), 5.0, "the role down")
    res["off"] = _try_full(g, "swap", "orphan", "old")
    _arm(g)
    ok, detail = judge_refuse(res)
    led.check("K-REFUSE", ok, detail)


K_LEVER_SEQ = (("stamps", "off"), ("stamps", "on"), ("delay", "300"), ("delay", "0"), ("orphan", "old"), ("orphan", "act"),
               ("own", "old"), ("own", "nocache"), ("own", "act"), ("pin", "old"), ("pin", "act"), ("life", "old"), ("life", "act"),
               ("fade", "old"), ("fade", "long"), ("fade", "nogate"), ("fade", "norecheck"), ("fade", "nohurry"), ("fade", "act"),
               ("hostctl", "off"), ("hostctl", "on"))
K_SET_ALL = (("stamps", "off"), ("delay", "500"), ("orphan", "old"), ("own", "nocache"), ("pin", "old"), ("life", "old"),
             ("fade", "long"), ("hostctl", "off"))


def _k_lever(g, ctx: Ctx, led: cb.Ledger) -> None:
    steps = []
    for op, word in K_LEVER_SEQ:
        at = cb.mark(g)
        ok, why = _ns(g, "swap", op, word)
        lines = cb.wait_log(g, at, lever_line(op, word), timeout=2.0) if ok else cb.new(g, at)
        st = cb.poll(g, lambda s, op=op, word=word: sget(s, "levers." + lever_want(op, word)[0], "?") in lever_want(op, word)[1], 2.0,
                     f"levers after {op} {word}") or g.state
        steps.append({"op": op, "word": word, "ok": ok, "why": why, "lines": lines, "levers": sget(st, "levers")})
    for op, word in (("orphan", "old"), ("delay", "200"), ("fade", "long"), ("hostctl", "off")):
        _ns(g, "swap", op, word)
    at = cb.mark(g)
    _ns(g, "swap", "clear")
    clear_lines = cb.wait_log(g, at, "harness: swap CLEAR", timeout=2.0)
    st = cb.poll(g, lambda s: levers_at_rest(sget(s, "levers")), 2.0, "every lever at rest after clear") or g.state
    ok, detail = judge_levers(steps, sget(st, "levers"), clear_lines)
    led.check("K-LEVER", ok, detail)


def _k_release(g, ctx: Ctx, led: cb.Ledger) -> None:
    for op, word in K_SET_ALL:
        _swap(g, op, word)
    at = cb.mark(g)
    cb.release(g)
    rel = cb.wait_log(g, at, "harness: swap levers released", timeout=3.0)
    st = cb.poll(g, lambda s: levers_at_rest(sget(s, "levers")), 3.0, "the levers released") or g.state
    after = sget(st, "levers")
    at2 = cb.mark(g)
    cb.release(g)
    g.wait_frames(20)
    second = cb.new(g, at2)
    _arm(g)
    _home(g)
    samples, _lines, rec = _follow_to(g, AWAY)
    ctx.fms = frame_ms(samples)
    ok, detail = judge_release(rel, after, second, rec, ctx.fms)
    led.check("K-RELEASE", ok, detail)


# ---- A
def _leg_a(g, ctx: Ctx, led: cb.Ledger) -> None:
    _home(g)
    if ctx.cal == "stamps":
        _swap(g, "stamps", "off")
        ctx.lever_taken = True
    try:
        _swap(g, "delay", 0)
        _span_clear(g)                                   # K-RELEASE's follow to AWAY would JOIN this one inside its span
        id0 = ival(sget(g.state, "last.id")) or 0
        s1, lines1, rec1 = _follow_to(g, AWAY, until_done=True)
        ctx.fms = frame_ms(s1)
        ctx.marks["A-STAMP"] = {"lines": lines1, "rec": rec1}
        ok, detail = judge_follow(rec1, id0)
        led.check("A-FOLLOW", ok, detail)
        ok, detail = judge_stamp(lines1, rec1)
        led.check("A-STAMP", ok, detail)
        ok, detail = judge_word(lines1)
        led.check("A-WORD", ok, detail)
        _home(g)
        d2 = 0 if ctx.cal == "delay" else 300
        if ctx.cal == "delay":
            ctx.lever_taken = True
        _swap(g, "delay", d2)
        _span_clear(g)                                   # leg 1's record would JOIN leg 2 inside its span
        s2, _lines2, rec2 = _follow_to(g, AWAY)
        fms = min(ctx.fms, frame_ms(s2)) if s2 else ctx.fms
        ctx.marks["A-DELAY"] = {"rec": rec2, "frame": fms}
        ok, detail = judge_delay(rec1, rec2, fms, 300)
        led.check("A-DELAY", ok, detail)
    finally:
        _ns(g, "swap", "delay", 0)
        if ctx.cal == "stamps":
            _ns(g, "swap", "stamps", "on")


# ---- B
def _keeper_uid(g) -> int:
    """The keeper's object uid on HOME: the talk object nearest KEEPER_AT in `objects` (s89), else a LOCAL talk (bench off) and its
    `player.listener` (coop_dialogue_authority's _references)."""
    objs = g.state.objects or []
    near = sorted(((o.get("x", 0.0) - KEEPER_AT[0]) ** 2 + (o.get("z", 0.0) - KEEPER_AT[1]) ** 2, o) for o in objs
                  if isinstance(o, dict) and o.get("talk") is True and isinstance(o.get("uid"), int))
    if near and near[0][0] <= KEEPER_NEAR ** 2:
        return int(near[0][1]["uid"])
    _must(g, "bench", 0)
    try:
        g.walk_to(*KEEPER_AT, tolerance=45, strict=False)
        opened = g.interact(timeout=6.0)
        uid = int((opened.raw.get("player") or {}).get("listener", -1)) if opened is not None else -1
        for _ in range(24):                              # clear the menu by the player's own input (its last row is Close)
            st = g.state
            if not st.dialog_open:
                break
            if st.choice is not None:
                try:
                    g.choose(int(st.choice.get("count", 1)) - 1)
                    continue
                except HarnessError:
                    pass
            g.press("confirm", 4)
            g.wait_frames(12)
    finally:
        _must(g, "bench", 1)
    if not 0 <= uid < 0xFFFF:
        raise HarnessError("no talk object near the keeper's post on HOME, and a local talk read no listener")
    return uid


def _quiet(g, timeout: float = 10.0) -> None:
    st = cb.poll(g, lambda s: not s.dialog_open and not windows(s) and s.control, timeout, "the screen clear and control back")
    if st is None:
        raise HarnessError("the previous line never cleared")


def _open_line(g, ctx: Ctx) -> tuple:
    """A FRESH line by the host's relayed start (`netsync talk <keeper>`) under hostscene 1, tracked locked -> its (win, text)."""
    _quiet(g)
    _must(g, "hostscene", 1)
    _must(g, "talk", ctx.keeper_uid)
    st = cb.poll(g, lambda s: s.dialog_open and any(w.get("cls") == "locked" for w in windows(s)), 6.0, "the relayed line, locked")
    if st is None:
        raise HarnessError(f"the relayed start for uid {ctx.keeper_uid} opened no locked line")
    w = windows(st)[-1]
    return int(w["win"]), int(w["text"])


def _host_close(g) -> None:
    """The bench host's ADV for the open line (`netsync choice <its Close row>` on a menu, `netsync advance` on a page)."""
    st = g.state
    if st.choice is not None:
        _must(g, "choice", int(st.choice.get("count", 1)) - 1)
    else:
        _must(g, "advance")


def _leg_b(g, ctx: Ctx, led: cb.Ledger) -> None:
    _home(g)
    ctx.keeper_uid = _keeper_uid(g)
    _must(g, "lock", 1)
    _must(g, "hostscene", 1)
    cb.poll(g, lambda s: (s.netsync or {}).get("lock_engaged") is True, 3.0, "the bench lock to engage")
    if ctx.cal == "orphan":
        _swap(g, "orphan", "old")
        ctx.lever_taken = True
    try:
        _b_hold_line(g, ctx, led)
        _guard(g, ctx, led, ("B-BLIP", "B-SCENE"), lambda: _b_blip(g, ctx, led))
        _guard(g, ctx, led, ("B-BLIP2",), lambda: _b_blip2(g, ctx, led))
        _guard(g, ctx, led, ("B-CTLON",), lambda: _b_ctlon(g, ctx, led))
    finally:
        for step in (("swap", "hostctl", "on"), ("hostscene", 0)) + ((("swap", "orphan", "act"),) if ctx.cal == "orphan" else ()):
            _ns(g, *step)


def _b_hold_line(g, ctx: Ctx, led: cb.Ledger) -> None:
    """B-HOST -> B-HOLD -> B-RELEASE: one line (B-RELEASE's auto-close consumes it)."""
    key = _open_line(g, ctx)
    _swap(g, "hostctl", "off")
    b0 = bcount(g.state)
    at = cb.mark(g)
    t0 = time.time()
    ack = _must(g, "hostscene", 0)
    first_s = dict(cb.raw(ack))                          # the step's own ack: frame f_ack itself
    first_s["_t"] = time.time() - t0
    samples, _ = watch(g, HOLD_S, t0=t0)
    samples = [first_s] + samples
    lines = cb.new(g, at)
    ok, detail = judge_b_host(samples, ack.frame, key)
    led.check("B-HOST", ok, detail)
    ctx.marks["B-HOLD"] = {"samples": samples, "lines": lines, "key": key, "b0": b0}
    ok, detail = judge_b_hold(samples, lines, key, b0)
    led.check("B-HOLD", ok, detail)
    h0 = held_t0(samples)
    b1 = bcount(samples[-1] if samples else g.state)
    at2 = cb.mark(g)
    t_on = now_ms(g.state)
    _swap(g, "hostctl", "on")
    rel, _ = watch(g, (RELEASE_ORPHAN_MS + AUTO_READ_MS + 1500) / 1000.0,
                   until=lambda s: (ival(nget(s, "orphan_closes")) or -1) >= (b1["closes"] or 0) + 1 and not windows(s))
    lines2 = cb.new(g, at2)
    ctx.marks["B-RELEASE"] = {"samples": samples + rel, "lines": lines + lines2, "key": key, "b0": b0}
    ok, detail = judge_b_release(rel, lines2, key, b1, t_on, h0)
    led.check("B-RELEASE", ok, detail)


def _b_blip(g, ctx: Ctx, led: cb.Ledger) -> None:
    """B-BLIP -> B-SCENE: a fresh held line, on, off 1.0 s later; then hostscene 1 and the bench host's ADV."""
    key = _open_line(g, ctx)
    _swap(g, "hostctl", "off")
    b_pre = bcount(g.state)
    at0 = cb.mark(g)
    _must(g, "hostscene", 0)
    pre, _ = watch(g, (GRACE_MS + 1500) / 1000.0, until=lambda s: (ival(sget(s, "orphan.holding")) or 0) >= 1
                   and (ival(nget(s, "host_settled_ms")) or -1) >= GRACE_MS + 300)
    b0 = bcount(g.state)
    at = cb.mark(g)
    t_on = time.time()
    _swap(g, "hostctl", "on")
    samples, _ = watch(g, BLIP_OFF_S, t0=t_on)
    _swap(g, "hostctl", "off")
    more, _ = watch(g, (AUTO_READ_MS + 1300) / 1000.0, t0=t_on)
    samples += more
    lines = cb.new(g, at)
    ctx.marks["B-BLIP"] = {"samples": pre + samples, "lines": cb.new(g, at0), "key": key, "b0": b_pre}
    ok, detail = judge_b_blip(samples, lines, key, b0)
    led.check("B-BLIP", ok, detail)
    b2 = bcount(g.state)
    at2 = cb.mark(g)
    _must(g, "hostscene", 1)
    sc, _ = watch(g, 0.6)
    try:
        _host_close(g)
    except HarnessError as err:
        g.note(f"B-SCENE: the bench host's ADV refused ({str(err)[:160]})")
    sc2, _ = watch(g, 3.0, until=lambda s: not windows(s) and not (s.get("dialog") or {}).get("open", False))
    lines2 = cb.new(g, at2)
    ctx.marks["B-SCENE"] = {"samples": pre + samples + sc + sc2, "lines": cb.new(g, at0), "key": key, "b0": b_pre}
    ok, detail = judge_b_scene(sc + sc2, lines2, key, b2)
    led.check("B-SCENE", ok, detail)
    _ns(g, "swap", "hostctl", "on")


def _b_blip2(g, ctx: Ctx, led: cb.Ledger) -> None:
    key = _open_line(g, ctx)
    _swap(g, "hostctl", "on")
    b0 = bcount(g.state)
    at = cb.mark(g)
    t_start = time.time()
    _must(g, "hostscene", 0)
    samples, hit = watch(g, (GRACE_MS + 2500) / 1000.0, until=lambda s: cls_of(s, key) == "orphaned", t0=t_start)
    if hit is None:
        lines = cb.new(g, at)
        ctx.marks["B-BLIP2"] = {"samples": samples, "lines": lines, "key": key, "b0": b0}
        led.check("B-BLIP2", False, f"the line never orphaned: {judge_b_blip2(samples, lines, key, b0)[1]}")
        return
    t0_wall = time.time()
    for off in BLIP2_OFFS:
        more, _ = watch(g, max(0.0, t0_wall + off - time.time()), t0=t_start)
        samples += more
        _ns(g, "swap", "hostctl", "off")
        more, _ = watch(g, max(0.0, t0_wall + off + BLIP2_OFF_S - time.time()), t0=t_start)
        samples += more
        _ns(g, "swap", "hostctl", "on")
    more, _ = watch(g, 0.8, t0=t_start)
    samples += more
    lines = cb.new(g, at)
    ctx.marks["B-BLIP2"] = {"samples": samples, "lines": lines, "key": key, "b0": b0}
    ok, detail = judge_b_blip2(samples, lines, key, b0)
    led.check("B-BLIP2", ok, detail)


def _b_ctlon(g, ctx: Ctx, led: cb.Ledger) -> None:
    key = _open_line(g, ctx)
    _swap(g, "hostctl", "on")
    b0 = bcount(g.state)
    t_settle = now_ms(g.state)
    _must(g, "hostscene", 0)
    samples, _ = watch(g, (GRACE_MS + AUTO_READ_MS + 2000) / 1000.0,
                       until=lambda s: (ival(nget(s, "orphan_closes")) or -1) >= (b0["closes"] or 0) + 1 and not windows(s))
    ok, detail = judge_b_ctlon(samples, key, b0, t_settle)
    led.check("B-CTLON", ok, detail)


# ---- C (engine only: the stand-in has no MAPJUMP)
class _Pager:
    """Pages each locked line of the desk scene as it opens (one host ADV per tracked page; a menu gets its default row), tracks text
    139's close from state, and fires one scheduled send at a swap-clock time measured from that close."""

    def __init__(self, g, lead_s: float | None, send):
        self.g, self.lead_s, self.send = g, lead_s, send
        self.paged: set = set()
        self.saw_last = False
        self.close_t: int | None = None
        self.close_wall: float | None = None
        self.fired = False
        self.delta_ms: int | None = None

    def __call__(self, s) -> None:
        listed = win_of(s, C_LAST) is not None
        if listed:
            self.saw_last = True
        elif self.saw_last and self.close_t is None:
            self.close_t, self.close_wall = now_ms(s), time.time()
        for w in windows(s):
            if w.get("cls") != "locked":
                continue
            k = (w.get("win"), w.get("text"), w.get("page"))
            if k in self.paged:
                continue
            self.paged.add(k)
            st = self.g.state
            if st.choice is not None:
                cb.try_ns(self.g, "choice", int(st.choice.get("selected", 0) or 0))
            else:
                cb.try_ns(self.g, "advance")
        if (self.lead_s is not None and not self.fired and self.close_wall is not None and self.delta_ms is not None
                and time.time() >= self.close_wall + max(0.0, self.delta_ms / 1000.0 - self.lead_s)):
            self.fired = True
            self.send()


def c_own_word(mode: str, cal: str | None) -> str:
    """Leg C's `own` lever for an attempt: the dry run is `own old` (registered); every other attempt carries the word's lever."""
    return "old" if mode == "dry" else {"own": "old", "nocache": "nocache"}.get(cal, "act")


def c_last(samples, id0: int) -> dict:
    """The attempt's record: on a bounce, the first sample of a NEW record (id > ``id0``) after its bounce reload, still open; else the
    final sample's."""
    s = first(samples, lambda s: (ival(sget(s, "last.id")) or 0) > id0 and (ival(sget(s, "last.reload_t")) or -1) >= 0
              and sget(s, "last.state") == "open")
    return (sget(s, "last") if s is not None else None) or (sget(samples[-1], "last") if samples else None) or {}


def _c_attempt(g, ctx: Ctx, mode: str) -> dict:
    """One desk-scene run from HOME: ``mode`` dry | cache | pend | age | src. -> {reached, why, samples, lines, b0, b1, last, pager}.
    The record before (a bounce leaves it open) would JOIN this one's own edge inside RecordSpanMs, so its span runs out first."""
    _home(g)
    _span_clear(g)
    _ns(g, "lock", 0)
    if mode == "src":
        _swap(g, "cache", C_DEST)                        # a cache written on HOME: the warp to 351 must clear it as Left
    lead = {"cache": C_CACHE_LEAD_S, "pend": C_PEND_LEAD_S, "age": C_AGE_LEAD_S}.get(mode)
    send = {"cache": lambda: _ns(g, "swap", "cache", C_DEST), "age": lambda: _ns(g, "swap", "cache", C_DEST),
            "pend": lambda: _ns(g, "swap", "intent", C_DEST)}.get(mode, lambda: None)
    pager = _Pager(g, lead, send)
    pager.delta_ms = ctx.delta_ms
    _swap(g, "fade", "old")                              # T8: leg C's registered lever
    _swap(g, "own", c_own_word(mode, ctx.cal))
    if mode != "dry" and ctx.cal in ("own", "nocache"):
        ctx.lever_taken = True
    _must(g, "lock", 1)
    b0 = _block(g)
    id0 = ival(cb.path(b0, "last.id")) or 0
    at = cb.mark(g)
    t0 = time.time()
    g.warp(C_FIELD, entrance=C_ENTRANCE, scenario=C_SCENARIO)
    first_line = f"dialogue lock: win {C_FIRST[0]} text {C_FIRST[1]} opened locked"
    cb.poll(g, lambda s: s.field_id == C_FIELD and s.on_field, ARRIVE_S, "351's landing")
    reach = cb.wait_log(g, at, first_line, timeout=C_REACH_S)
    if cb.count(reach, first_line) == 0:
        return {"reached": False, "why": f"'{first_line}' never logged within {C_REACH_S:.0f} s of the landing", "lines": reach,
                "samples": [], "b0": b0, "b1": _block(g), "last": sget(g.state, "last") or {}, "pager": pager}

    def done(s) -> bool:
        t = ival(sget(s, "last.own_t"))
        if t is None or t < 0 or ival(sget(s, "last.own_dest")) != C_DEST:
            return False
        return s.get("field", {}).get("id") == C_DEST or (ival(sget(s, "last.reload_t")) or -1) >= t
    samples, hit = watch(g, C_RUN_S, until=done, t0=t0, on_sample=pager)
    more, _ = watch(g, 1.5, t0=t0)                      # the landing's own lines and clears settle
    samples += more
    lines = cb.new(g, at)
    out = {"reached": hit is not None, "why": "" if hit is not None else "no own jump to 352 within the budget", "samples": samples,
           "lines": lines, "b0": b0, "b1": swb(samples[-1]) or {}, "pager": pager, "last": c_last(samples, id0)}
    if mode == "dry" and pager.close_t is not None and hit is not None:
        out["delta_ms"] = ival(sget(hit, "last.own_t")) - pager.close_t
    return out


def _leg_c(g, ctx: Ctx, led: cb.Ledger) -> None:
    try:
        dry = _c_attempt(g, ctx, "dry")
        if not dry["reached"]:
            _void(led, ctx, LEG_ROWS["C"], f"leg C not reached: {dry['why']}")
            return
        ctx.delta_ms = dry.get("delta_ms")
        g.note(f"leg C's Delta (text 139's close to the own jump, from state): {ctx.delta_ms} ms (about 161 ticks plus Dagger's script "
               f"19 expected, INFER)")
        ok, detail = judge_c_bounce(dry["last"], dry["lines"], dry["b0"], dry["b1"])
        led.check("C-BOUNCE", ok, detail)
        if ctx.delta_ms is None:
            _void(led, ctx, ("C-CACHE", "C-PEND", "C-AGE"), "the dry run measured no Delta (text 139's close or the own jump unseen)")
        if "C-CACHE" not in led.done:
            r = _c_attempt(g, ctx, "cache")
            ctx.marks["C-CACHE"] = {"last": r["last"], "lines": r["lines"], "b0": r["b0"], "b1": r["b1"]}
            if not r["reached"] or not r["pager"].fired:
                _void(led, ctx, ("C-CACHE",), r["why"] or "the cache was never injected")
            else:
                ok, detail = judge_c_cache(r["lines"], r["last"], r["b0"], r["b1"])
                led.check("C-CACHE", ok, detail)
        if "C-PEND" not in led.done:
            r = _c_attempt(g, ctx, "pend")
            reached, why = pend_reach(r["samples"], r["last"]) if r["reached"] else (False, r["why"])
            before = [s for s in r["samples"] if now_ms(s) is not None and now_ms(s) < (ival((r["last"] or {}).get("own_t")) or 0)]
            ctx.marks["C-PEND"] = {"last": r["last"], "lines": r["lines"],
                                   "pending": ival(nget(before[-1], "session.follow.pending")) if before else None}
            if not reached:
                _void(led, ctx, ("C-PEND",), f"C-PEND not reached: {why}")
            else:
                ok, detail = judge_c_pend(r["lines"], r["last"], r["b0"], r["b1"])
                led.check("C-PEND", ok, detail)
        if "C-AGE" not in led.done:
            r = _c_attempt(g, ctx, "age")
            if not r["reached"] or not r["pager"].fired:
                _void(led, ctx, ("C-AGE",), r["why"] or "the cache was never injected")
            else:
                ok, detail = judge_c_age(r["lines"], r["last"], r["b0"], r["b1"])
                led.check("C-AGE", ok, detail)
        r = _c_attempt(g, ctx, "src")
        if not r["reached"]:
            _void(led, ctx, ("C-SRC",), r["why"])
        else:
            ok, detail = judge_c_src(r["lines"], r["last"], r["b0"], r["b1"], HOME)
            led.check("C-SRC", ok, detail)
    finally:
        for step in (("lock", 0), ("swap", "fade", "act"), ("swap", "own", "act")):
            _ns(g, *step)
        try:
            _home(g)
        except HarnessError:
            pass


# ---- P (engine only: the stand-in has no story frames)
def _p_run(g, ctx: Ctx, *args, dest: int = AWAY) -> tuple:
    """`flag 8720 0`, `watch 8720`, `swap pinbench 30602 8720 <args>`, watched to the landing on ``dest``. -> (final sample, lines)."""
    _home(g)
    g.flag(P_FLAG, False)
    g.watch(P_FLAG)
    at = cb.mark(g)
    _swap(g, "pinbench", AWAY, P_FLAG, *args)
    samples, _ = watch(g, FOLLOW_S, until=lambda s: s.get("field", {}).get("id") == dest and flag_of(s) is not None
                       and sget(s, "pin.last_use") is not None)
    more, _ = watch(g, 0.5)
    fin = (more or samples or [dict(cb.raw(g.state))])[-1]
    return fin, cb.new(g, at)


def _leg_p(g, ctx: Ctx, led: cb.Ledger) -> None:
    pin_word = ctx.cal == "pin"
    try:
        if pin_word:
            _swap(g, "pin", "old")
            ctx.lever_taken = True
        fin, lines = _p_run(g, ctx)
        ctx.marks["P-PIN"] = {"flag": flag_of(fin), "pin": sget(fin, "pin")}
        ok, detail = judge_p_pin(flag_of(fin), sget(fin, "pin"), sget(fin, "last"), lines)
        led.check("P-PIN", ok, detail)
        if pin_word:
            _swap(g, "pin", "act")                       # P3: the guards keep judging their own why
        fin, _ = _p_run(g, ctx, "age", P_AGE_MS)
        ok, detail = judge_p_guard(flag_of(fin), sget(fin, "pin"), "aged")
        led.check("P-AGED", ok, detail)
        other0 = ival(sget(g.state, "pin.other"))
        fin, _ = _p_run(g, ctx, "to", P_OTHER, dest=P_OTHER)
        ok, detail = judge_p_other(flag_of(fin), sget(fin, "pin"), other0)
        led.check("P-OTHER", ok, detail)
        fin, _ = _p_run(g, ctx, "landed")
        ok, detail = judge_p_guard(flag_of(fin), sget(fin, "pin"), "late", "late")
        led.check("P-LATE", ok, detail)
        _home(g)
        party = nget(g.state, "dress.party") or [-1, -1, -1, -1]
        c = next(x for x in (1, 2, 3, 4, 5) if x != (party[1] if len(party) > 1 else -1))
        if pin_word:
            _swap(g, "pin", "old")
        fin, _ = _p_run(g, ctx, "party", 1, c)
        before = nget(fin, "dress.mirror_party")
        ctx.marks["P-PARTY"] = {"flag": flag_of(fin), "pin": sget(fin, "pin")}
        at = cb.mark(g)
        _swap(g, "clear")
        clear_lines = cb.wait_log(g, at, "harness: swap CLEAR", timeout=2.0)
        st = cb.poll(g, lambda s: nget(s, "dress.mirror_party", "?") is None, 2.0, "the party mirror cleared") or g.state
        ok, detail = judge_p_party(flag_of(fin), sget(fin, "pin"), before, c, nget(st, "dress.mirror_party", "?"), clear_lines)
        led.check("P-PARTY", ok, detail)
    finally:
        _ns(g, "swap", "pin", "act")
        try:
            _home(g)
        except HarnessError:
            pass


# ---- L (engine only: the stand-in has no host probe)
def _leg_l(g, ctx: Ctx, led: cb.Ledger) -> None:
    _home(g)
    if ctx.cal == "life":
        _swap(g, "life", "old")
        ctx.lever_taken = True
    try:
        at = cb.mark(g)
        t0 = time.time()
        _swap(g, "lifebench", AWAY)
        samples, _ = watch(g, BW.INTENT_LOAD_CAP_MS / 1000.0 + 3.0, until=lambda s: sget(s, "intent.last_end") is not None
                           and sget(s, "intent.active") is False and (ival(sget(s, "intent.end_t")) or -1) >= 0, t0=t0)
        lines = cb.new(g, at)
        why = l_land_void(samples, lines, ctx.cal)
        if why:
            _void(led, ctx, ["L-LAND"], why)
        else:
            ok, detail = judge_l_land(samples, lines)
            led.check("L-LAND", ok, detail)
        ctx.marks["L-STANDS"] = {"intent": sget(samples[-1], "intent") if samples else {}}
        ok, detail = judge_l_stands(samples)
        led.check("L-STANDS", ok, detail)
    finally:
        _ns(g, "swap", "life", "act")


# ---- F (engine only: the stand-in has no fade slot)
def _f_follow(g, ctx: Ctx, row: str, *, lock: bool, setup=None, mid=None, teardown=None) -> tuple:
    _home(g)
    _must(g, "lock", 1 if lock else 0)
    if setup is not None:
        setup()
    b0 = _block(g)
    due0 = ival(cb.path(b0, "fade.last.due_t"))
    due0 = due0 if due0 is not None else -1
    c0 = ival(cb.path(b0, "last.commit_t"))
    c0 = c0 if c0 is not None else -1
    at = cb.mark(g)
    t0 = time.time()
    try:
        _swap(g, "intent", AWAY)
        if mid is not None:
            mid()
        samples, _ = watch(g, FOLLOW_S, until=lambda s: (ival(sget(s, "fade.last.due_t")) or -1) > due0 and landed_after(s, AWAY, c0),
                           t0=t0)
    finally:
        if teardown is not None:
            try:
                teardown()
            except HarnessError:
                pass
    return samples, cb.new(g, at), b0


def _leg_f(g, ctx: Ctx, led: cb.Ledger) -> None:
    word = ctx.cal if ctx.cal in ("fade", "long", "nogate", "norecheck", "nohurry") else None
    if word is not None:
        _swap(g, "fade", "old" if word == "fade" else word)
        ctx.lever_taken = True
    blackout = lambda n: (lambda: (_swap(g, "blackout", n), g.wait_frames(3)))          # noqa: E731
    off = lambda: _ns(g, "swap", "blackout", "off")                                     # noqa: E731
    talk = lambda: (_quiet(g), _must(g, "hostscene", 1), _must(g, "talk", _f_keeper(g, ctx)),        # noqa: E731
                    cb.poll(g, lambda s: any(w.get("cls") == "locked" for w in windows(s)), 6.0, "the locked line"))
    unmatched = lambda wait=0.0: (lambda: (_must(g, "unmatched"), time.sleep(wait)))     # noqa: E731
    key = lambda: _must(g, "host", "key", _f_keeper(g, ctx), 64)                          # noqa: E731
    specs = (
        ("F-FAST", dict(lock=False)),
        ("F-3X", dict(lock=False, setup=lambda: g.speedmode(True), teardown=lambda: g.speedmode(False))),
        ("F-BLACK", dict(lock=False, setup=blackout(1), teardown=off)),
        ("F-JOIN", dict(lock=False, setup=blackout(8), teardown=off)),
        ("F-HURRY", dict(lock=False, setup=blackout(60), teardown=off)),
        ("F-OPEN", dict(lock=True, setup=talk, teardown=lambda: _f_clear(g))),
        ("F-AHEAD", dict(lock=True, setup=unmatched(0.0))),
        ("F-AGED", dict(lock=True, setup=unmatched(3.2))),
        ("F-RECHECK", dict(lock=True, mid=lambda: _must(g, "unmatched"))),
        ("F-REASSERT", dict(lock=False, mid=lambda: (g.wait_frames(3), off()))),
        ("F-KEY", dict(lock=True, setup=key)),
    )
    try:
        for row, spec in specs:
            if row not in led.catalog:
                continue
            _guard(g, ctx, led, (row,), lambda row=row, spec=spec: _f_one(g, ctx, led, row, spec))
    finally:
        for step in (("swap", "blackout", "off"), ("lock", 0), ("hostscene", 0), ("swap", "fade", "act")):
            _ns(g, *step)


def _f_keeper(g, ctx: Ctx) -> int:
    if ctx.keeper_uid is None:
        ctx.keeper_uid = _keeper_uid(g)
    return ctx.keeper_uid


def _f_clear(g) -> None:
    """After F-OPEN: the open line closed by the bench host, the scene down."""
    for _ in range(6):
        if not g.state.dialog_open:
            break
        try:
            _host_close(g)
        except HarnessError:
            break
        g.wait_frames(20)
    _ns(g, "hostscene", 0)


def _f_one(g, ctx: Ctx, led: cb.Ledger, row: str, spec: dict) -> None:
    samples, lines, b0 = _f_follow(g, ctx, row, **spec)
    fin = samples[-1] if samples else {}
    fl = sget(fin, "fade.last") or {}
    win = fade_window(samples)
    ctx.marks[row] = {"fade": fl, "held": any(sget(s, "fade.held") is True for s in samples),
                      "left": next((v for v in (ival(sget(s, "fade.left_start")) for s in samples) if v is not None and v >= 0), None),
                      "window": len(win)}
    ok, detail = judge_fade(row, samples, lines, b0)
    led.check(row, ok, detail)
