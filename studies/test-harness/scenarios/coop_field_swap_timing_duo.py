"""s164 -- FIELD-SWAP TIMING, ROUND 1, the TWO-GAME bench (tools/harness/duo.py; studies/field-coop/SWAP-TIMING-S164.md rev 3,
"## Benches" / "### Duo"). [ff9mapkit netsync s164]

Two real FF9s on this desktop, paired by duo.py on 250 (HOME; AWAY is 30602, LOCKT2), `stateevery 1` on both. The solo bench
(coop_field_swap_timing.py) proves every rule on the selftest role through bench levers; this bench reads the round on a REAL lane:
the host's emits and its intent's life, the guest's seen / follow / due / commit / landing edges on ONE clock (QPC is one counter
system-wide, so both games stamp on it), the fade-aware follow at the copy's own exit, C's own passes, the story pin across a
deferred follow, and Finding 11's orphan hold on the Cat's Eye. Every guest-side lever is legal on the duo's client and `life` goes to
the host game; both games load one DLL through the instance junction, so every calibration is a LEVER, never a DLL swap.

THE CLOCK PRECONDITION (F1, F11a). DK-CLOCK runs first: K-CLOCK (the solo's judge_clock) must hold on BOTH games. It is a note,
never a red row (KIT-3's K-CLOCK precedent); when it fails, every CROSS-GAME row -- DA-LANE, DB-BIT, DP-MARK, DL-LEFT and DA-ARRIVE
whole; DC-B(a)'s gap, DF-FAST's gap and DA-LINES' host-tap clause as clauses -- is VOID with the reason. Rows inside one game still
judge.

THE LEGS (every warp, scenario and poke is data below; COOP_LEGS picks them by name, default all):
  CAL     warp 30602 and back on each sub-leg, each field held LineWindowMs + 1 s (F13): CAL0 the guest on `fade old`; CAL1 `fade
          old` + `delay 200`; CAL2 act; CAL3 act + the guest's `speedmode 1`; ARRIVE: warp ARRIVE_ID (30611, the scratch copy
          studies/movement/bench/lockt2-arrive.field.toml with `[camera] entry_settle = 68`) and back, at act and again on `fade old`.
          Rows DA-CAL, DA-JOIN, DL-LIFE, DL-NOREG, DC-FE, DF-FAST, DF-3X, DA-ARRIVE (DA-LANE and DA-PROBE-X take its transitions).
  DESK    `warp 359 0 2600`, the guest follows; the host confirms D after each line opens and every D until it closes, D in {0.3,
          1.0, 2.5}; 359's Main_11 MAPJUMPs to 351, whose entrance 15 builds the desk scene (first line win 3 text 129). REST
          continues each run: text 139's close -> Dagger_Loop case 23 -> Field(352) (first line win 4 text 142). Six runs: at each D
          one with REST at act and one REST-OLD (the guest sends `swap fade old` before text 139 closes). Rows DA-LINES, DF-FLASH,
          DF-GRACE, DF-PACE, DA-PROBE, DC-B(a), DC-B(b), DP-HALT, DP-DRESS (and DA-ARRIVE's DESK watch, DC-WON, DA-LANE).
  CAT     both on 350 by one follow; the guest at its own booster (`speedmode 1`), the host at 1x; the Cat's Eye menu gate on both
          (238 = 1, 241 = 8, 242 = 0, the guest first), the leap gate on the HOST only (297 | 1, flag 2075 = 0, read back first);
          the host picks choice 3 and pages 113-117. Rows DB-SHAPE, DB-BIT, DB-HOLD, DB-ORDER.
  OWN     s163's recipe: the host's 238 poked and read back, `warp 351 0 2600`, the gate (238 = 1, 241 = 4, 242 = 0) on both, the
          guest first; choice 2 ("Dagger Tries"). Row DC-OWN.
  MENU    the guest holds its main menu across the host's exit and closes it 1.2 s after the emit (3.5 s in the aged run); the host
          marks flag 8720 once it has landed. Rows DL-DEFER, DP-DEFER, DP-AGED.
  MARK    the host exits to AWAY; once its body stands there the bench sends `flag 8720 1` to the host; the guest on `swap fade long`
          for the leg. Row DP-MARK.
  LEFT    the host's harness `battle` 0.8 s after its landing (the swirl ends section 4 as Left), then it flees. Row DL-LEFT.
  OPEN    on 30602 the host opens the control NPC's line (relayed locked) and warps with it up. Row DF-OPEN.
  LEVERS  raw sends. Rows LVD-ROLE, LVD-LIFE (last: the host's `reset`).
  every   the host's dress.party at each emit and after each landing. Row DP-PARTY (reach-gated).

THE REACH RULES (P4, P8). Deterministic rows are red when their key never moved. PROBABILISTIC rows -- DA-LANE per transition,
DF-FLASH, DF-GRACE, DF-PACE, DP-HALT, DP-PARTY, DC-B(b), DP-MARK, DP-DEFER and DA-ARRIVE's watches -- are judged only on their reached
runs and are NEVER RED merely for being UNREACHED: such a row records GREEN with an "UNREACHED" detail and is kept out of every
calibration count. The floors: DA-LANE needs at least one reached transition in each of CAL, DESK and REST ("not reached: arrived_t was
-1 on every transition"), and DA-ARRIVE's ARRIVE run must reach its EXPOSURE -- the overlap (the host's first control-true sample after
its landing minus the guest's landing, both on the swap clock) at least DwellMs + 100 ms AND the guest's peak
`netsync.stepout.base.age_ms` between its landing and its control at least DwellMs -- or DA-ARRIVE is red "not reached", never green.
A VOID (an unfit clock, a setup clause that missed, the Cat's else path) records RED with a "VOID:" detail (KIT-3's solo convention)
and is likewise never counted as a calibration's predicted red.

DA-ARRIVE IS A DEFECT, NOT A CALIBRATION: pre-registered RED at act on round 1's code (a ~1.8 s base, past DwellMs 1500), green on
`fade old` (~1.25 s). Until the landing-scoped arrival guard ships, a plain run reads DA-ARRIVE red. It is BASELINE_RED: every
calibration reports it apart and never counts it as the word's.

THE CALIBRATIONS (COOP_CALIBRATE=<word>, refused AT LOAD when unknown -- duo.py imports the scenario before it boots the pair). Each
word turns EXACTLY its registered rows red, each with its marker (D-CAL-M); D-CAL judges the exactness (a predicted red that reads
UNREACHED or VOID fails it; every predicted red UNREACHED is VOID, never a pass):

    stamps   both games `swap stamps off`, the whole run              DA-LINES
    delay    CAL1 sends `delay 0`, still expects +200                 DA-CAL
    orphan   guest `swap orphan old` from before the CAT pick          DB-HOLD, DB-ORDER
    own      guest `swap own old` on REST-OLD only                     DC-B(b) (on its reached runs; none reached = VOID)
    nocache  guest `swap own nocache` on REST-OLD only                 none (a control)
    pin      guest `swap pin old` on MARK and the 1.2 s MENU run       DP-MARK, DP-DEFER
    life     host `swap life old` on CAL, DESK and the 1.2 s MENU run  DL-LIFE, DL-DEFER (DP-DEFER VOID; DA-PROBE records)
    fade     guest `swap fade old` wherever it would run act           DF-FAST, DF-3X, DF-FLASH, DF-OPEN, DF-PACE if reached
    long     guest `swap fade long` the same                           DF-FAST, DF-3X
    nogate   guest `swap fade nogate` the same                         DF-OPEN, DF-PACE if reached

("wherever it would run act": CAL2, CAL3, the DESK runs and REST at act, MENU and OPEN; CAL0, CAL1 and both ARRIVE runs keep their
registered levers, REST-OLD keeps `old`, MARK keeps `long`.)

THE ARRIVE FIELD is DATA here (ARRIVE_ID, ARRIVE_TOML, ARRIVE_FOLDER). A bench never deploys or launches anything inside a run (a NEW
id registers only at a relaunch anyway): the operator deploys it once, with the explicit id, through

    py studies/test-harness/scenarios/coop_field_swap_timing_duo.py deploy        (runs deploy_field.py with --id 30611)

and relaunches; CAL refuses DA-ARRIVE "not reached" with that command when ARRIVE_ID is not registered on both roots.

    py tools/harness/duo.py studies/test-harness/scenarios/coop_field_swap_timing_duo.py --keep-going
    COOP_LEGS=CAL,DESK py tools/harness/duo.py studies/test-harness/scenarios/coop_field_swap_timing_duo.py --keep-going
    COOP_CALIBRATE=orphan COOP_LEGS=CAT py tools/harness/duo.py studies/test-harness/scenarios/coop_field_swap_timing_duo.py

Prereqs as duo.py's (no FF9 from either root, no controller connected, nobody at the keyboard -- THE UNATTENDED LAW); 30602 and
ARRIVE_ID registered on both roots (the -msgs folder); the guest root's [Cheats] SpeedFactor 3 for CAT (the host at 1x).
NOT PROVEN HERE: real network latency and a laptop/desktop load difference (the next two-PC session replays with the stamps); the
laptop's Unity order (one host-alone `life old` run on a scripted exit, read through DA-PROBE). DP-COUNT (Dali's SByte[296] from a
save past 450's ping) is exploratory and not run by this bench.
"""
from __future__ import annotations

import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                          # noqa: E402 - Ledger, path, ns verbs
from harness import battlewire as BW                               # noqa: E402 - the engine's words, through its twins
from harness import duo as duo_mod                                 # noqa: E402 - watched_byte, BENCH_SCENE

try:
    from harness.channel import qpc_ms as _qpc_ms                  # noqa: E402 - the kit's read of the swap clock (None off Windows)
except ImportError:                                                # pragma: no cover
    _qpc_ms = None

HarnessError = cb.HarnessError
REPO = cb.REPO

KEY = "netsync.swap"
PROBE = KEY + ".clock"                   # key PRESENCE is the capability (protocol 5, additive)

HOME, AWAY = 250, 30602                  # duo.py's pairing field / LOCKT2 (the -msgs folder)
ARRIVE_ID = 30611                        # the scratch copy of LOCKT2 with entry_settle 68 (read free against every live
                                         # FF9CustomMap*/DictionaryPatch.txt; the -msgs folder holds 30601-30610)
ARRIVE_TOML = "studies/movement/bench/lockt2-arrive.field.toml"
ARRIVE_FOLDER = "FF9CustomMap-msgs"
ARRIVE_SETTLE_TICKS = 68                 # its [camera] entry_settle: ~2.27 s of control off at 30 TPS, no line
DESK_FIELD, DESK_SCENARIO = 359, 2600    # 359's scene runs at any scenario; Main_11 -> Field(351) entrance 15
REST_FROM, REST_DEST = 351, 352
DESK_FIRST, DESK_LAST, REST_FIRST = (3, 129), (3, 139), (4, 142)
REST_OLD_AT = ((3, 139), (3, 138))       # REST-OLD's `fade old` goes out at the guest's first sample listing either (before 139 closes)
DS = (0.3, 1.0, 2.5)                     # the host's confirm pace on DESK / REST
PACE_D = 0.3                             # DF-PACE's runs
CAT_FIELD, CAT_SCENARIO, CAT_PICK = 350, 2600, 3
CAT_FIRST, CAT_LAST, CAT_ELSE = (7, 113), (7, 117), (7, 118)
CAT_TEXTS = (113, 114, 115, 116, 117)
GATE_BYTES = (238, 241, 242)             # VAR_GenInt8_238 (availability) + the Int16 row mask at 241/242
CAT_ROWS, OWN_ROWS = 8, 4                # bit 3 "Cat's Eye" (350) / bit 2 "Dagger Tries" (351)
LEAP_BYTE, LEAP_FLAG = 297, 2075         # Cat_Loop's leap needs 297 & 1 and 2075 == 0 (the HOST only)
OWN_HUB, OWN_DEST, OWN_PICK = 351, 450, 2
P_FLAG = 8720                            # >= FIRST_SAFE_FLAG (8712)
MENU_SHORT_S, MENU_AGED_S = 1.2, 3.5
LEFT_BATTLE_S = 0.8
BATTLE_SCENE = duo_mod.BENCH_SCENE       # 67: BSC_EF_R007, one Goblin (LOCKT2's own encounter)
OPEN_NPC = (0.0, -350.0)                 # LOCKT2's control talker
OPEN_STAND = (0.0, -470.0)
PAGE_S = 0.2                             # CAT / OWN: the host's confirm pace (s163's)

DWELL_MS = 1500                          # NetSyncStepOut.DwellMs (THE ARRIVAL LAW)
ARRIVE_MARGIN_MS = 100
CAL_HOLD_S = (BW.SWAP_LINE_WINDOW_MS + 1000) / 1000.0     # each CAL field held LineWindowMs + 1 s (F13)
CAL_DELAY_MS = 200
CAL0_PRED_MS = (885, 912)                # reported (the s163 measurement)
DF_FAST_MS = (350, 600)
DF_FAST_GAIN_MS = 300                    # the host-to-guest landing gap shorter than CAL0's by this
DF_3X_MS = 220
DF_3X_TICKS = (12, 17)                   # == solo F-3X: the Prime's one frame is up to 3 ticks at 3x; a 2-tick batch can push
                                         # the first black read to 14, so the commit's read lands at 17
DL_LIFE_SPAN_MS = (1800, 2700)
DC_B_SLACK_MS = 300
DL_DEFER_MS = 200
DP_DEFER_AGE_MS = BW.PIN_MAX_AGE_MS      # 2500
DP_MARK_LEAD_MS = 300
DL_LEFT_MS = 300
FADE_TIMER_MIN_MS = 885                  # the 0.9 s timer as measured (s163 live-lane duo, FIELD-SWAP-TIMING.md §1): the guest's follow
                                         # starts after ServiceFollowWarp, so no start-frame debit (the solo bench's harness start has one)
DIP_TOL = 8                              # a cur_now step down by more than this is a dip (the flash)
FRAME_MS_DEFAULT = 1000.0 / 30
ZIDANE = 0
SEAT_S = 40.0
ARRIVE_S = 30.0
DESK_S = 240.0                           # one DESK run: HOME -> 359 -> its scene -> 351 -> the desk scene -> 352
CAT_S = 150.0
OWN_S = 180.0
FOLLOW_S = 20.0

C_TERMS = BW.SWAP_OWN_REASONS_C          # pending, committed, intent, cache
G, R, U, V = "green", "red", "unreached", "void"

LEGS = ("CAL", "DESK", "CAT", "OWN", "MENU", "MARK", "LEFT", "OPEN", "LEVERS")
LEG_ALIASES = {"REST": "DESK"}           # REST continues each DESK run: one leg
LEG_ROWS = {
    "CAL": ("DA-CAL", "DA-JOIN", "DL-LIFE", "DL-NOREG", "DC-FE", "DF-FAST", "DF-3X", "DA-ARRIVE"),
    "DESK": ("DA-LINES", "DF-FLASH", "DF-GRACE", "DF-PACE", "DA-PROBE", "DC-B(a)", "DC-B(b)", "DP-HALT", "DP-DRESS"),
    "CAT": ("DB-SHAPE", "DB-BIT", "DB-HOLD", "DB-ORDER"),
    "OWN": ("DC-OWN",),
    "MENU": ("DL-DEFER", "DP-DEFER", "DP-AGED"),
    "MARK": ("DP-MARK",),
    "LEFT": ("DL-LEFT",),
    "OPEN": ("DF-OPEN",),
    "LEVERS": ("LVD-ROLE", "LVD-LIFE"),
}
LANE_LABELS = ("CAL", "DESK", "REST")    # DA-LANE's floor: one reached transition in each
#: the cross-game rows (F11a): VOID whole under an unfit clock (DC-B(a), DF-FAST, DA-LINES lose a clause instead)
CROSS_GAME = ("DA-LANE", "DB-BIT", "DP-MARK", "DL-LEFT", "DA-ARRIVE")
#: the probabilistic rows (never red merely for being UNREACHED)
PROBABILISTIC = ("DA-LANE", "DF-FLASH", "DF-GRACE", "DF-PACE", "DP-HALT", "DP-PARTY", "DC-B(b)", "DP-MARK", "DP-DEFER", "DA-ARRIVE")
#: rows only reported, never judged (notes, never ledger rows -- K-CLOCK's precedent)
REPORTED = ("DK-CLOCK", "DC-WON", "DA-PROBE-X")
#: a pre-registered defect: red on round 1's code at act whatever the word (never counted as a calibration's red)
BASELINE_RED = ("DA-ARRIVE",)
#: rows judged after the legs that feed them (DA-ARRIVE takes DESK's 351 arrivals as its DESK watch)
LATE_ROWS = ("DA-ARRIVE",)

CLAIMS = {
    "DA-LANE": "per transition emit <= intent.first_sent <= seen.arrived <= seen.first <= follow <= due <= commit <= the guest's "
               "landing (a transition with arrived_t -1 or no first send is UNREACHED); at least one reached transition in each of "
               "CAL, DESK and REST; the lane's gaps reported",
    "DA-CAL": "CAL1: commit_t - due_t = 200 ms +- 1 frame within each follow; CAL0's commit - follow (0.885-0.912 s) and CAL1 - CAL0 "
              "reported",
    "DA-JOIN": "one record per CAL transition on each copy (ids +1), the guest's nonce the host's, land_via follow (guest) / host "
               "(host), both closed by line or window",
    "DL-LIFE": "the guest's seen span (last_t - first_t) 1800-2700 ms and the host's 'ended ... I stand on it' line, per CAL "
               "transition",
    "DL-NOREG": "per CAL transition: exactly one parallel-follow line, one commit and one landing, no 'follow-warp ... cancelled', no "
                "second follow for the nonce",
    "DC-FE": "no `[NetSync] own Field(` line on the guest across CAL; own.passes +0",
    "DF-FAST": "CAL2: fade.last fast / fade / 12, by black; commit - follow 0.35-0.60 s; the host-to-guest landing gap shorter than "
               "CAL0's by >= 0.3 s",
    "DF-3X": "CAL3 (the guest's speedmode 1): fade.last.ticks 12-17; commit - follow <= 0.22 s",
    "DA-ARRIVE": "ARRIVE at act reaches its exposure (overlap >= DwellMs + 100 ms, base.age_ms >= DwellMs) with no dwell OUT; the "
                 "fade-old controls (ARRIVE on fade old, CAL0) green; the dressed watches (CAL2, DESK) green",
    "DA-LINES": "DESK: every edge line on both logs stamped; per host tap seq S: tap_t <= queued_t <= closed_t, 'waited X ms' = "
                "closed_t - queued_t +- 1 ms, 'shown Y ms' <= closed_t - that page's open stamp",
    "DF-FLASH": "DESK (REACHED on view_start heading or black): action join or ended by own, no cur_now dip from the follow start to "
                "the first of (due, field load)",
    "DF-GRACE": "DESK at act (REACHED on the Join action: view black, or heading with <= 12 ticks left): fade.last.by own",
    "DF-PACE": "D = 0.3 (REACHED when the copy lags: backlog_start line or ahead): path backlog, by timer, the guest's last close for "
               "359 before the commit",
    "DA-PROBE": "MAPJUMP intents (DESK, REST): frames / updates / sends >= 1, oob sent or overwritten, 1 <= the guest's seen copies <= "
                "sends, last_end stands under act, landed_frames >= 1",
    "DC-B(a)": "REST at act (REACHED when the intent was seen before any own jump): one guest load of 352, bounces +0, guest landing - "
               "host landing <= max(0, L139) + 0.3 s",
    "DC-B(b)": "REST-OLD (REACHED on an own jump to 352 with the intent seen before it, the lane on 0 or 351): an own pass, converted "
               "+1 on the pending term, one load, bounces +0",
    "DP-HALT": "REACHED when pin.pre_frames rose across the MAPJUMP exits: pin.max_pre_diff stays 0 (the halted-VM premise)",
    "DP-DRESS": "after the 351 -> 352 landing the guest's dress.self.want_char is the latest frame's leader",
    "DB-SHAPE": "the guest's own Field(351) passes on the host's pick (choice 3, field 350); its first sample listing (win 7, text 113) "
                ">= 4.5 s before its first with host_flags b0 on 351 (text 118 first: the else path, VOID)",
    "DB-BIT": "between the guest's 113 open and the host's scene rise: every guest sample host_flags b1 clear with b3 set, the lane on "
              "351, orphan.host_holds; every host sample control false",
    "DB-HOLD": "one 'win 7 text 113 held -- the host's control is off on my field' line, then its end line at the host's claim "
               "(predicted 'a host event claims it'); no 'is not on the host's screen'; orphan_closes +0 across 351",
    "DB-ORDER": "the guest's 113-117 each 'closed (host seq N)', N strictly increasing and the host's tap seq for the same text; no "
                "'dropped -- it is for field 351'",
    "DC-OWN": "351 -> 450 'Dagger Tries': one load of 450, the own jump's term or lane recorded",
    "DL-DEFER": "the guest's follow starts by the intent within 200 ms of its menu closing (last.follow_t - the menu's close on "
                "clock.now_ms)",
    "DP-DEFER": "REACHED when that landing came by the intent with the pin < 2500 ms old, quality pre, the host's mark in the latest "
                "frame: flag 8720 = 0 (the pin's story)",
    "DP-AGED": "the menu held to 3.5 s: flag 8720 = 1, pin.last_use aged",
    "DP-MARK": "VOID unless the host's mark precedes the guest's landing by >= 300 ms; REACHED on quality pre: flag 8720 = 0, the "
               "pin line, last_diff >= 1",
    "DL-LEFT": "the host's 'ended ... I left it' at its battle's swirl; the guest's seen.last_t stops within 300 ms of the battle start",
    "DF-OPEN": "a host line up across its warp: the guest's backlog_start open, path backlog, by timer, ms >= 885",
    "DP-PARTY": "REACHED on a landing whose host party changed between its emit and its landing: the guest's mirror_party is the "
                "host's post-landing party",
    "LVD-ROLE": "`swap life old` to the guest: the host-side refusal; `swap orphan old` to the host: the guest-side refusal; `swap "
                "hostctl off` to either: the selftest refusal",
    "LVD-LIFE": "`swap life old` to the host reads back levers.life old, and the host's `reset` releases it",
}

#: word -> (the lever, its registered red rows, its "if reached" reds) -- SWAP-TIMING-S164.md "Duo calibrations, pre-registered"
WORDS = {
    "stamps": ("both games: `swap stamps off` (the whole run)", ("DA-LINES",), ()),
    "delay": ("CAL1 sends `delay 0` and still expects +200", ("DA-CAL",), ()),
    "orphan": ("guest: `swap orphan old`, from before the CAT pick", ("DB-HOLD", "DB-ORDER"), ()),
    "own": ("guest: `swap own old`, on REST-OLD only (CAL and DESK hold `own act`)", ("DC-B(b)",), ()),
    "nocache": ("guest: `swap own nocache`, on REST-OLD only (a control: nothing turns red)", (), ()),
    "pin": ("guest: `swap pin old` on MARK and the 1.2 s MENU run only (DP-AGED keeps judging `aged`)", ("DP-MARK", "DP-DEFER"), ()),
    "life": ("host: `swap life old` on CAL, DESK and the 1.2 s MENU run", ("DL-LIFE", "DL-DEFER"), ()),
    "fade": ("guest: `swap fade old` wherever it would run act", ("DF-FAST", "DF-3X", "DF-FLASH", "DF-OPEN"), ("DF-PACE",)),
    "long": ("guest: `swap fade long` wherever it would run act", ("DF-FAST", "DF-3X"), ()),
    "nogate": ("guest: `swap fade nogate` wherever it would run act", ("DF-OPEN",), ("DF-PACE",)),
}
#: the legs each word's lever acts on (a word whose legs COOP_LEGS leaves out is refused at load)
WORD_LEGS = {"stamps": LEGS, "delay": ("CAL",), "orphan": ("CAT",), "own": ("DESK",), "nocache": ("DESK",), "pin": ("MARK", "MENU"),
             "life": ("CAL", "DESK", "MENU"), "fade": ("CAL", "DESK", "MENU", "OPEN"), "long": ("CAL", "DESK", "MENU", "OPEN"),
             "nogate": ("CAL", "DESK", "MENU", "OPEN")}
FADE_WORDS = {"fade": "old", "long": "long", "nogate": "nogate"}
FINALS = ("D-CAL-M", "D-CAL")
MARKERS = {
    "stamps": "no '(t N ms)' on any edge line of either log and no `[NetSync] swap` line on either",
    "delay": "CAL1's commit - due within 1 frame of 0 and last.delay_ms 0 (the lever was 0)",
    "orphan": "s163's rule on the held control: orphan.holds +0 across 351 and the 113 line orphaned ('is not on the host's screen') "
              "or auto-closed",
    "own": "on a reached REST-OLD run: own_verdict bounce and a second load of 352",
    "nocache": "the lever read back (a control: no predicted red)",
    "pin": "flag 8720 = 1 with pin.last_use lever and pin.last_use_quality pre (the capture still ran)",
    "life": "DL-LIFE: the host's intent.last_end old (span about the host's load); DL-DEFER: the serial follow (follow_via serial)",
    "fade": "fade.last.path old (today's start and commit)",
    "long": "fade.last path fast with frames 24 (E off)",
    "nogate": "fade.last path fast with a backlog seen (the gate never read)",
}


def _norm_legs(raw: str) -> list:
    out = []
    for tok in re.split(r"[,\s]+", raw.strip().upper()):
        if tok:
            out.append(LEG_ALIASES.get(tok, tok))
    return out


def calibration() -> str | None:
    """COOP_CALIBRATE read AT LOAD: '' / 0 none, a registered duo word, anything else REFUSED (never mapped to a lever)."""
    v = os.environ.get("COOP_CALIBRATE", "").strip().lower()
    if v in ("", "0"):
        return None
    if v in WORDS:
        return v
    raise SystemExit(f"coop_field_swap_timing_duo: COOP_CALIBRATE={v!r} is refused -- the duo takes one of {', '.join(WORDS)} and "
                     f"nothing else; refused before the pair boots.")


def legs_selected() -> str:
    """COOP_LEGS read AT LOAD: leg names (CAL, DESK, CAT, OWN, MENU, MARK, LEFT, OPEN, LEVERS; REST = DESK), commas or spaces;
    empty = every leg. An unknown name is refused before the pair boots. -> the selected legs in LEGS order, comma-joined."""
    raw = os.environ.get("COOP_LEGS", "")
    if not raw.strip():
        return ",".join(LEGS)
    toks = _norm_legs(raw)
    bad = sorted({t for t in toks if t not in LEGS})
    if bad:
        raise SystemExit(f"coop_field_swap_timing_duo: COOP_LEGS={raw!r} is refused -- unknown leg(s) {', '.join(bad)} (legs: "
                         f"{', '.join(LEGS)}; REST = DESK); refused before the pair boots.")
    return ",".join(leg for leg in LEGS if leg in toks)


def _legs(legs) -> tuple:
    return tuple(legs.split(",")) if isinstance(legs, str) else tuple(legs)


def catalog_rows(cal: str | None, legs) -> list:
    legs = _legs(legs)
    rows = ["DA-LANE"] if any(leg in legs for leg in ("CAL", "DESK")) else []
    for leg in LEGS:
        if leg in legs:
            rows += list(LEG_ROWS[leg])
    return rows + ["DP-PARTY"]


def predicted(cal: str | None, legs) -> tuple:
    """The word's MUST rows among the rows the selected legs run (its "if reached" rows join only when reached: judge_cal)."""
    if cal is None:
        return ()
    rows = catalog_rows(cal, legs)
    return tuple(r for r in WORDS[cal][1] if r in rows)


def conditional(cal: str | None, legs) -> tuple:
    if cal is None:
        return ()
    rows = catalog_rows(cal, legs)
    return tuple(r for r in WORDS[cal][2] if r in rows)


def _check_load(cal: str | None, legs) -> None:
    legs = _legs(legs)
    if cal is None:
        return
    if not any(leg in legs for leg in WORD_LEGS[cal]) or (WORDS[cal][1] and not predicted(cal, legs)):
        raise SystemExit(f"coop_field_swap_timing_duo: COOP_CALIBRATE={cal!r} acts on {', '.join(WORD_LEGS[cal])}, which "
                         f"COOP_LEGS={','.join(legs)!r} leaves out -- refused before the pair boots.")


CAL_MODE = calibration()                 # at load: duo.py imports the scenario before it boots the pair
LEGS_SEL = legs_selected()
_check_load(CAL_MODE, LEGS_SEL)


def _import_solo():
    """The solo bench's readers and judges (`so`), imported with COOP_CALIBRATE / COOP_LEGS masked: its own load checks would read
    the DUO's environment (a duo leg name is no solo leg) -- the duo's words were refused above, by the duo."""
    saved = {k: os.environ.pop(k) for k in ("COOP_CALIBRATE", "COOP_LEGS") if k in os.environ}
    try:
        import coop_field_swap_timing as solo                      # noqa: WPS433 - after the duo's own load checks
    finally:
        os.environ.update(saved)
    return solo


so = _import_solo()


def catalog(cal: str | None, legs) -> dict:
    cat = {r: CLAIMS[r] for r in catalog_rows(cal, legs)}
    if cal is not None:
        must = ", ".join(predicted(cal, legs)) or "none (a control)"
        cond = conditional(cal, legs)
        cat["D-CAL-M"] = f"the `{cal}` lever was taken and every predicted red carries its marker ({MARKERS[cal]})"
        base = [r for r in BASELINE_RED if r in cat]
        cat["D-CAL"] = (f"the `{cal}` calibration: exactly {must} red" + (f", and {', '.join(cond)} if reached" if cond else "")
                        + (f" ({', '.join(base)} is the pre-registered defect, reported apart)" if base else ""))
    return cat


def deploy_argv(python: str | None = None) -> list:
    """The ARRIVE field's deploy, with its explicit id (never the shared default slot): the operator's one-time step (`deploy`)."""
    return [python or sys.executable, str(REPO / "tools" / "deploy_field.py"), str(REPO / ARRIVE_TOML), "--id", str(ARRIVE_ID),
            "--mod-folder", ARRIVE_FOLDER]


def deploy_command() -> str:
    return f"py tools/deploy_field.py {ARRIVE_TOML} --id {ARRIVE_ID} --mod-folder {ARRIVE_FOLDER}"


# --------------------------------------------------------------------------------------------- reads (pure)
def ival(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _path(x, dotted: str, default=None):
    cur = x if isinstance(x, dict) else {}
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _t(x, dotted: str) -> int | None:
    """A swap-clock key of a swap block (dict): None for -1 (never) or absent."""
    v = ival(_path(x, dotted))
    return v if v is not None and v >= 0 else None


def _fid(x) -> int | None:
    return ival(_path(cb.raw(x), "field.id"))


def _ctl(x) -> bool:
    return _path(cb.raw(x), "player.control") is True


def _fmt(parts) -> str:
    return ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)


def _res(parts, extra: str = "") -> tuple:
    return (G if all(v for _, v in parts) else R), _fmt(parts) + (f"; {extra}" if extra else "")


def _delta(a, b, dotted: str) -> int | None:
    x, y = ival(_path(a, dotted)), ival(_path(b, dotted))
    return y - x if x is not None and y is not None else None


def land_idx(samples, dest: int, start: int = 0) -> int | None:
    """The first sample at or after ``start`` standing on ``dest`` (the landing as state shows it)."""
    return next((i for i in range(max(0, start), len(samples or [])) if _fid(samples[i]) == dest), None)


def rec_block(samples, i: int | None) -> dict:
    """The swap block of the LAST sample carrying the record ``samples[i]`` holds (its most advanced state): {} when none."""
    if i is None or not samples:
        return {}
    rid = ival(so.sget(samples[i], "last.id"))
    last = None
    for x in samples[i:]:
        if ival(so.sget(x, "last.id")) == rid:
            last = x
    return dict(so.swb(last) or {}) if last is not None else {}


def intent_block(samples, emit_t: int | None) -> dict:
    """The host's `intent` block at its last sample whose intent.emit_t is ``emit_t`` (that intent's final probe)."""
    hit = None
    for x in samples or []:
        if emit_t is None or ival(so.sget(x, "intent.emit_t")) == emit_t:
            hit = x
    return dict(so.sget(hit, "intent") or {}) if hit is not None else {}


def sample_at(samples, t: int | None):
    """The latest sample whose clock.now_ms is at or before ``t``."""
    if t is None:
        return None
    hit = None
    for x in samples or []:
        n = so.now_ms(x)
        if n is not None and n <= t:
            hit = x
    return hit


def close_t(samples, key) -> int | None:
    """The clock.now_ms of a game's first sample no longer listing (win, text) after one that did (P7, P10): None when never seen."""
    seen = False
    for x in samples or []:
        if so.win_of(x, key) is not None:
            seen = True
        elif seen:
            return so.now_ms(x)
    return None


def text_of(samples, key) -> str | None:
    """The dialog text a game shows while its state lists (win, text) (the first sample that lists it and shows a text)."""
    for x in samples or []:
        if so.win_of(x, key) is not None:
            t = ((cb.raw(x).get("dialog") or {}).get("texts") or [None])[0]
            if t:
                return t
    return None


def host_close_t(hs, gs, key) -> int | None:
    """The HOST's close of (win, text) from its state (P10). Window tracking is guest-only (NetSyncDialog's GuestView: a host's
    `netsync.windows` lists nothing), so the host's own list is read first and, when it never lists the key, the line is found by its
    TEXT -- the one the guest shows while it lists the key: the clock.now_ms of the host's first sample after one showing it that no
    longer does."""
    t = close_t(hs, key)
    if t is not None:
        return t
    want = text_of(gs, key)
    if not want:
        return None
    seen = False
    for x in hs or []:
        shown = ((cb.raw(x).get("dialog") or {}).get("texts") or [None])[0]
        if shown == want and (cb.raw(x).get("dialog") or {}).get("open"):
            seen = True
        elif seen:
            return so.now_ms(x)
    return None


def fade_left_start(gs, follow_t: int | None, dest: int) -> int | None:
    """`fade.left_start` as the follow published it (a per-follow static: read while the follow runs, never after its end)."""
    if follow_t is None:
        return None
    for x in gs or []:
        n = so.now_ms(x)
        if n is None or n < follow_t:
            continue
        if _fid(x) == dest:
            break
        v = ival(so.sget(x, "fade.left_start"))
        if v is not None and v >= 0:
            return v
    return None


def first_listing_t(samples, key) -> int | None:
    x = next((s for s in samples or [] if so.win_of(s, key) is not None), None)
    return so.now_ms(x) if x is not None else None


def is_dwell_out(line: str) -> bool:
    c = so.unstamped(line)
    return c.startswith("[NetSync] step-out: OUT on field ") and c.endswith(" -- dwell")


def tr_evidence(lane: str, sub: str, dest: int, frm: int, hs, gs, hl=(), gl=(), kind: str | None = None) -> dict:
    """One transition off the leg window's samples of each game (raw dicts; `netsync.swap` present), in the ENGINE's shapes: the host
    and guest record blocks at their most advanced sample (``h`` / ``g``), the host's intent block for that emit (``hi``), the blocks
    before (``h0`` / ``g0``), the landings and the overlap on the swap clock, the step-out window (landing -> control), the host's
    party at the emit and after the landing, and the guest's party mirror after its landing."""
    hs, gs = list(hs or []), list(gs or [])
    hi_, gi_ = land_idx(hs, dest), land_idx(gs, dest)
    h, g = rec_block(hs, hi_), rec_block(gs, gi_)
    hint = intent_block(hs, _t(h, "last.emit_t"))
    g_land = _t(g, "last.land_t")
    if g_land is None and gi_ is not None:
        g_land = so.now_ms(gs[gi_])
    h_land = _t(h, "last.land_t")
    if h_land is None and hi_ is not None:
        h_land = so.now_ms(hs[hi_])
    h_ctl = next((so.now_ms(x) for x in hs[hi_:] if _fid(x) == dest and _ctl(x)), None) if hi_ is not None else None
    g_ctl_i = next((i for i in range(gi_, len(gs)) if _fid(gs[i]) == dest and _ctl(gs[i])), None) if gi_ is not None else None
    win = gs[gi_:(g_ctl_i + 1 if g_ctl_i is not None else len(gs))] if gi_ is not None else []
    peaks = [v for v in (ival(_path(x, "netsync.stepout.base.age_ms")) for x in win) if v is not None]
    dw = [v for v in (ival(_path(x, "netsync.stepout.out_why.dwell")) for x in win) if v is not None]
    land_h = sample_at(hs, g_land) or (hs[hi_] if hi_ is not None else None)
    on_dest = [x for x in gs[gi_:] if _fid(x) == dest] if gi_ is not None else []
    want = ival(_path(gs[gi_], "netsync.dress.self.want_char")) if gi_ is not None else None
    return {"lane": lane, "sub": sub, "kind": kind, "dest": dest, "from": frm, "h": h, "g": g, "hi": hint,
            "h0": dict(so.swb(hs[0]) or {}) if hs else {}, "g0": dict(so.swb(gs[0]) or {}) if gs else {},
            "g_land_t": g_land, "h_land_t": h_land, "h_ctl_t": h_ctl,
            "overlap": (h_ctl - g_land) if h_ctl is not None and g_land is not None else None,
            "base_peak": max(peaks) if peaks else None, "dwell_count": (dw[-1] - dw[0]) if dw else 0,
            "active": any(_path(x, "netsync.stepout.active") is True for x in win), "dressed": want is not None and want >= 0 and want != ZIDANE,
            "party_emit": _path(sample_at(hs, _t(h, "last.emit_t")), "netsync.dress.party"),
            "party_land": _path(land_h, "netsync.dress.party"),
            "mirror_after": _path(on_dest[-1], "netsync.dress.mirror_party") if on_dest else None,
            "hl": list(hl or []), "gl": list(gl or [])}


def arrival_of(tr: dict, kind: str) -> dict:
    """DA-ARRIVE's view of one arrival: gate | control | watch | watch-desk | control-desk."""
    return {"kind": kind, "sub": tr.get("sub"), "dest": tr.get("dest"), "overlap": tr.get("overlap"), "base_peak": tr.get("base_peak"),
            "dwell_lines": sum(1 for ln in tr.get("gl") or () if is_dwell_out(ln)), "dwell_count": tr.get("dwell_count") or 0,
            "active": bool(tr.get("active")), "dressed": bool(tr.get("dressed"))}


def fade_cur_window(gs, follow_t: int | None, due_t: int | None, dest: int) -> list:
    """`fade.cur_now` from the follow's start to the first of (its due, the field load)."""
    out = []
    if follow_t is None:
        return out
    for x in gs or []:
        n = so.now_ms(x)
        if n is None or n < follow_t:
            continue
        if _fid(x) == dest or (due_t is not None and n > due_t):
            break
        out.append(ival(so.sget(x, "fade.cur_now")))
    return out


def dipped(cur) -> bool:
    vals = [v for v in cur or [] if v is not None and v >= 0]
    return any(b < a - DIP_TOL for a, b in zip(vals, vals[1:]))


def last_close_on(samples, fld: int) -> int | None:
    """The clock.now_ms of the guest's last line close on ``fld`` (a sample listing a window, then the first listing none)."""
    out, prev = None, False
    for x in samples or []:
        if _fid(x) != fld:
            prev = False
            continue
        listed = bool(so.windows(x))
        if prev and not listed:
            out = so.now_ms(x)
        prev = listed
    return out


def menu_close_t(gs) -> int | None:
    """The clock.now_ms of the guest's first sample off its main menu after one on it."""
    on = False
    for x in gs or []:
        if cb.raw(x).get("ui_state") == "MainMenu":
            on = True
        elif on:
            return so.now_ms(x)
    return None


# --------------------------------------------------------------------------------------------- the lines (pure)
_RX = {k: re.compile(BW.S163_FORMS[k]) for k in ("dialog_tap", "dlg_queued", "dlg_applied", "dlg_opened_locked", "follow_intent",
                                                  "ate_hub_pass")}
_CANCEL = re.compile(r"\[NetSync\] follow-warp to field (\d+) cancelled")


def _strip(line: str) -> tuple:
    """(core, t, waited, shown) of a logged line (Memoria's prefix cut, then battlewire's stamp / tail strip)."""
    return BW.swap_strip_line(so.core(line))


def edge_lines(lines) -> list:
    """The lines that carry a stamp while stamps are on: every instrument and behaviour line (L-CLOCK carries its t inside) and every
    s163 line the design stamps (an S163_FORMS form once its stamp and tail are removed). Harness and fault lines are never stamped."""
    out = []
    for ln in lines or []:
        c = so.core(ln)
        if not c.startswith("[NetSync]") or c.startswith("[NetSync] swap clock: "):
            continue
        cls = BW.swap_line_class(c)
        if cls in ("harness", "fault"):
            continue
        if cls in ("instrument", "behaviour") or BW.swap_s163_form(_strip(c)[0]):
            out.append(c)
    return out


def follow_lines(lines, dest: int) -> list:
    return [ln for ln in lines or [] if (m := _RX["follow_intent"].fullmatch(_strip(ln)[0])) and int(m.group(1)) == dest]


def stands_lines(lines, n: int, dest: int, why: int = BW.INTENT_END_STANDS) -> list:
    rx = re.compile(rf"\[NetSync\] transition intent {n} to field {dest} ended after -?\d+ ms -- {re.escape(BW.INTENT_END_WORDS[why])}")
    return [ln for ln in lines or [] if rx.fullmatch(so.unstamped(ln))]


def taps(lines) -> dict:
    """The host's dialog taps: seq -> {win, text, closes, t}."""
    out = {}
    for ln in lines or []:
        core, t, _w, _s = _strip(ln)
        m = _RX["dialog_tap"].fullmatch(core)
        if m:
            out[int(m.group(8))] = {"win": int(m.group(2)), "text": int(m.group(3)), "closes": bool(m.group(7)), "t": t}
    return out


def queued(lines) -> dict:
    out = {}
    for ln in lines or []:
        core, t, _w, _s = _strip(ln)
        m = _RX["dlg_queued"].fullmatch(core)
        if m:
            out.setdefault(int(m.group(1)), t)
    return out


def applied(lines) -> dict:
    """The guest's applied closes / advances: seq -> {win, text, verb, t, waited, shown}."""
    out = {}
    for ln in lines or []:
        core, t, w, s = _strip(ln)
        m = _RX["dlg_applied"].fullmatch(core)
        if m:
            out[int(m.group(4))] = {"win": int(m.group(1)), "text": int(m.group(2)), "verb": m.group(3), "t": t, "waited": w, "shown": s}
    return out


def opened(lines) -> list:
    """The guest's 'opened locked' lines: [(win, text, t)]."""
    out = []
    for ln in lines or []:
        core, t, _w, _s = _strip(ln)
        m = _RX["dlg_opened_locked"].fullmatch(core)
        if m:
            out.append((int(m.group(1)), int(m.group(2)), t))
    return out


# --------------------------------------------------------------------------------------------- judges (pure; -> (status, detail))
def _void_clock(why: str) -> tuple:
    return V, f"DK-CLOCK: {why} -- a cross-game row is VOID, never red"


def lane_times(tr: dict) -> dict:
    h, g, hi = tr.get("h") or {}, tr.get("g") or {}, tr.get("hi") or {}
    emit = _t(h, "last.emit_t")
    return {"emit": emit if emit is not None else _t(hi, "emit_t"), "first_sent": _t(hi, "first_sent_t"),
            "arrived": _t(g, "last.arrived_t"), "seen": _t(g, "last.seen_t"), "follow": _t(g, "last.follow_t"),
            "due": _t(g, "last.due_t"), "commit": _t(g, "last.commit_t"), "land": _t(g, "last.land_t")}


def judge_da_lane(trs, legs=LANE_LABELS, clock_ok: bool = True, clock_why: str = "") -> tuple:
    """DA-LANE (PURE): ``trs`` with `lane` CAL / DESK / REST. A transition is REACHED when its arrived_t and its first send were seen
    (F10); the order is judged over its edges (follow, due and commit required when it landed via the follow: an own pass that won
    has none). The floor (P8): every lane label in ``legs`` needs one reached transition."""
    if not clock_ok:
        return _void_clock(clock_why or "the instrument is unfit")
    per = {leg: [0, 0] for leg in legs}
    bad, gaps = [], []
    for tr in trs or []:
        lane = tr.get("lane")
        if lane not in per:
            continue
        per[lane][1] += 1
        t = lane_times(tr)
        if t["arrived"] is None or t["first_sent"] is None:
            continue
        per[lane][0] += 1
        need = ["emit", "first_sent", "arrived", "seen", "land"]
        if _path(tr.get("g"), "last.land_via") == "follow":
            need += ["follow", "due", "commit"]
        order = [t[k] for k in ("emit", "first_sent", "arrived", "seen", "follow", "due", "commit", "land") if t[k] is not None]
        if any(t[k] is None for k in need) or order != sorted(order):
            bad.append(f"{lane} {tr.get('sub')} -> {tr.get('dest')}: {t}")
        gaps.append(f"{lane}/{tr.get('sub')}: send +{_minus(t['first_sent'], t['emit'])}, arrive->seen +{_minus(t['seen'], t['arrived'])}, "
                    f"seen->follow +{_minus(t['follow'], t['seen'])}, landing gap {_minus(t['land'], tr.get('h_land_t'))} ms")
    floor = [leg for leg in legs if per[leg][0] == 0]
    tally = ", ".join(f"{leg} {per[leg][0]}/{per[leg][1]}" for leg in legs)
    if floor:
        return R, f"not reached: arrived_t was -1 on every transition of {', '.join(floor)} (reached/total {tally})"
    if bad:
        return R, f"order broken on {len(bad)}: {bad[:2]}; reached/total {tally}"
    return G, f"reached/total {tally}; reported: {'; '.join(gaps[:8])}"


def _minus(a, b):
    return (a - b) if ival(a) is not None and ival(b) is not None else None


def commit_minus_due(g) -> int | None:
    return _minus(_t(g, "last.commit_t"), _t(g, "last.due_t"))


def commit_minus_follow(g) -> int | None:
    return _minus(_t(g, "last.commit_t"), _t(g, "last.follow_t"))


def judge_da_cal(cal0, cal1, fms: float, want: int = CAL_DELAY_MS) -> tuple:
    """DA-CAL (PURE): ``cal0`` / ``cal1`` the guest's record blocks of each sub-leg's transitions."""
    d1 = [commit_minus_due(g) for g in cal1 or []]
    f0 = [x for x in (commit_minus_follow(g) for g in cal0 or []) if x is not None]
    f1 = [x for x in (commit_minus_follow(g) for g in cal1 or []) if x is not None]
    tol = fms + 1
    parts = [("CAL1 transitions", bool(d1)), (f"commit - due = {want} +- 1 frame in each", bool(d1) and all(x is not None and abs(x - want)
                                                                                                    <= tol for x in d1))]
    rep = (f"CAL1 commit - due {d1} (frame {fms:.1f}); reported: CAL0 commit - follow {f0} (predicted {CAL0_PRED_MS[0]}-"
           f"{CAL0_PRED_MS[1]}), CAL1 - CAL0 {round(statistics.mean(f1) - statistics.mean(f0)) if f0 and f1 else None} ms")
    return _res(parts, rep)


def judge_da_join(trs) -> tuple:
    """DA-JOIN (PURE): ``trs`` the CAL transitions (``h_id0`` / ``g_id0``: each copy's record id before it)."""
    bad = []
    for tr in trs or []:
        h, g = tr.get("h") or {}, tr.get("g") or {}
        hid0, gid0 = ival(_path(tr.get("h0"), "last.id")), ival(_path(tr.get("g0"), "last.id"))
        ok = (hid0 is not None and ival(_path(h, "last.id")) == hid0 + 1 and gid0 is not None and ival(_path(g, "last.id")) == gid0 + 1
              and ival(_path(g, "last.nonce")) is not None and ival(_path(g, "last.nonce")) >= 0
              and _path(g, "last.nonce") == _path(h, "last.nonce") and _path(g, "last.land_via") == "follow"
              and _path(h, "last.land_via") == "host"
              and all(_path(b, "last.state") == "done" and _path(b, "last.close_why") in ("line", "window") for b in (h, g)))
        if not ok:
            bad.append(f"{tr.get('sub')} -> {tr.get('dest')}: ids {hid0}->{_path(h, 'last.id')} / {gid0}->{_path(g, 'last.id')}, nonce "
                       f"{_path(h, 'last.nonce')}/{_path(g, 'last.nonce')}, via {_path(h, 'last.land_via')}/{_path(g, 'last.land_via')}, "
                       f"close {_path(h, 'last.close_why')}/{_path(g, 'last.close_why')}")
    return _res([("CAL transitions", bool(trs)), ("one record per transition on each copy, joined", not bad)], "; ".join(bad[:3]))


def judge_dl_life(trs) -> tuple:
    """DL-LIFE (PURE): per CAL transition, the guest's seen span for the host's nonce and the host's "I stand on it" line."""
    bad, spans = [], []
    for tr in trs or []:
        h, g = tr.get("h") or {}, tr.get("g") or {}
        n, dest = ival(_path(h, "last.nonce")), tr.get("dest")
        same = n is not None and ival(_path(g, "seen.nonce")) == n
        span = _minus(_t(g, "seen.last_t"), _t(g, "seen.first_t")) if same else None
        spans.append(span)
        line = bool(stands_lines(tr.get("hl"), n, dest)) if n is not None else False
        if not (span is not None and DL_LIFE_SPAN_MS[0] <= span <= DL_LIFE_SPAN_MS[1] and line):
            bad.append(f"{tr.get('sub')} -> {dest}: span {span} ms, stands line {line}, last_end {_path(tr.get('hi'), 'last_end')!r}")
    return _res([("CAL transitions", bool(trs)), (f"seen span {DL_LIFE_SPAN_MS[0]}-{DL_LIFE_SPAN_MS[1]} ms with the 'I stand on it' line",
                                                  not bad)], f"spans {spans}; " + "; ".join(bad[:3]))


def judge_dl_noreg(trs) -> tuple:
    """DL-NOREG (PURE): per CAL transition one parallel-follow line, one commit, one landing, no cancel, one follow for the nonce."""
    bad = []
    for tr in trs or []:
        g, dest = tr.get("g") or {}, tr.get("dest")
        fl = follow_lines(tr.get("gl"), dest)
        cancels = [ln for ln in tr.get("gl") or [] if _CANCEL.search(ln)]
        landed = _delta(tr.get("g0"), g, "counts.landings")
        ok = (len(fl) == 1 and ival(_path(g, "last.follows")) == 1 and _t(g, "last.commit_t") is not None
              and _t(g, "last.land_t") is not None and landed == 1 and not cancels)
        if not ok:
            bad.append(f"{tr.get('sub')} -> {dest}: follow lines {len(fl)}, follows {_path(g, 'last.follows')}, commit "
                       f"{_path(g, 'last.commit_t')}, landings +{landed}, cancels {len(cancels)}")
    return _res([("CAL transitions", bool(trs)), ("one follow, one commit, one landing each; no cancel", not bad)], "; ".join(bad[:3]))


def judge_dc_fe(lines, g0, g1) -> tuple:
    """DC-FE (PURE): no own Field() line on the guest across CAL; own.passes +0."""
    own = [ln for ln in lines or [] if so.core(ln).startswith("[NetSync] own Field(")]
    d = _delta(g0, g1, "own.passes")
    return _res([("no '[NetSync] own Field(' line", not own), ("own.passes +0", d == 0)], cb.grep(own, "own Field(", limit=300))


def _landing_gap(tr) -> int | None:
    return _minus(tr.get("g_land_t"), tr.get("h_land_t"))


def fresh_fade(tr) -> bool:
    """THE REACH RULE (PURE): a transition's fade.last is ITS follow's record -- due_t past the one in the transition's first guest
    sample (``g0``). A record left over from the previous transition means the guest never ran this follow (the solo F judges' term)."""
    due = ival(_path(tr.get("g") or {}, "fade.last.due_t"))
    due0 = ival(_path(tr.get("g0") or {}, "fade.last.due_t"))
    return due is not None and due > (due0 if due0 is not None else -1)


def judge_df_fast(cal2, cal0, clock_ok: bool = True) -> tuple:
    """DF-FAST (PURE): each CAL2 transition's fade.last and commit - follow; the landing gap against CAL0's (cross-game: dropped,
    with the reason, under an unfit clock)."""
    bad = []
    for tr in cal2 or []:
        g = tr.get("g") or {}
        fl = _path(g, "fade.last") or {}
        cf = commit_minus_follow(g)
        ok = (fresh_fade(tr) and fl.get("path") == "fast" and fl.get("action") == "fade" and ival(fl.get("frames")) == BW.FADE_FAST_FRAMES
              and fl.get("by") == "black" and cf is not None and DF_FAST_MS[0] <= cf <= DF_FAST_MS[1])
        if not ok:
            bad.append(f"-> {tr.get('dest')}: fade.last {fl.get('path')}/{fl.get('action')}/{fl.get('frames')} by {fl.get('by')}, "
                       f"commit - follow {cf}")
    g2 = [x for x in (_landing_gap(tr) for tr in cal2 or []) if x is not None]
    g0 = [x for x in (_landing_gap(tr) for tr in cal0 or []) if x is not None]
    gain = round(statistics.mean(g0) - statistics.mean(g2)) if g0 and g2 else None
    parts = [("CAL2 transitions", bool(cal2)), ("fast / fade / 12, by black, commit - follow 0.35-0.60 s", not bad)]
    if clock_ok:
        parts.append((f"landing gap shorter than CAL0's by >= {DF_FAST_GAIN_MS} ms", gain is not None and gain >= DF_FAST_GAIN_MS))
    rep = f"landing gaps CAL2 {g2} vs CAL0 {g0} (gain {gain} ms){'' if clock_ok else ' -- VOID: DK-CLOCK unfit (the gap clause)'}"
    return _res(parts, "; ".join(bad[:2] + [rep]))


def judge_df_3x(cal3) -> tuple:
    bad = []
    for tr in cal3 or []:
        g = tr.get("g") or {}
        ticks, cf = ival(_path(g, "fade.last.ticks")), commit_minus_follow(g)
        if not (fresh_fade(tr) and ticks is not None and DF_3X_TICKS[0] <= ticks <= DF_3X_TICKS[1] and cf is not None and 0 <= cf <= DF_3X_MS):
            bad.append(f"-> {tr.get('dest')}: ticks {ticks}, commit - follow {cf}, path {_path(g, 'fade.last.path')}")
    return _res([("CAL3 transitions", bool(cal3)), (f"ticks {DF_3X_TICKS[0]}-{DF_3X_TICKS[1]}, commit - follow <= {DF_3X_MS} ms",
                                                    not bad)], "; ".join(bad[:2]))


def arrive_reached(a: dict) -> bool:
    ov, bp = ival(a.get("overlap")), ival(a.get("base_peak"))
    return ov is not None and ov >= DWELL_MS + ARRIVE_MARGIN_MS and bp is not None and bp >= DWELL_MS


def _out(a: dict) -> bool:
    desk = (a.get("kind") or "").endswith("-desk")
    return (a.get("dwell_lines") or 0) > 0 or (a.get("dwell_count") or 0) > 0 or (bool(a.get("active")) and not desk)


def judge_da_arrive(arrivals, clock_ok: bool = True, clock_why: str = "") -> tuple:
    """DA-ARRIVE (PURE): ``arrivals`` (arrival_of). The gate (ARRIVE at act) must REACH its exposure -- the overlap >= DwellMs + 100
    AND the guest's peak netsync.stepout.base.age_ms >= DwellMs -- else red "not reached". Judged: the reached gates, every control
    (the guest on fade old), the dressed watches; any dwell OUT is red (on DESK an OUT by line is lawful: only the dwell counts)."""
    if not clock_ok:
        return _void_clock(clock_why or "the instrument is unfit")
    arrivals = list(arrivals or [])
    gates = [a for a in arrivals if a.get("kind") == "gate"]
    reached = [a for a in gates if arrive_reached(a)]
    rep = "; ".join(f"{a.get('kind')} {a.get('sub')} -> {a.get('dest')}: overlap {a.get('overlap')}, base peak {a.get('base_peak')}"
                    f"{', DWELL OUT' if _out(a) else ''}" for a in arrivals)[:900]
    if not reached:
        return R, f"not reached: ARRIVE at act never reached its exposure (overlap >= {DWELL_MS + ARRIVE_MARGIN_MS} ms, base.age_ms >= {DWELL_MS} ms) -- {rep}"
    judged = reached + [a for a in arrivals if (a.get("kind") or "").startswith("control")]
    judged += [a for a in arrivals if (a.get("kind") or "").startswith("watch") and a.get("dressed")]
    bad = [a for a in judged if _out(a)]
    names = ", ".join(f"{a.get('kind')}/{a.get('sub')}" for a in bad)
    return (R if bad else G), f"gates reached {len(reached)}/{len(gates)}; judged {len(judged)}, dwell OUTs {len(bad)} ({names}); {rep}"


def judge_da_lines(runs, clock_ok: bool = True) -> tuple:
    """DA-LINES (PURE): ``runs`` [{hl, gl}] across DESK. Every edge line on both logs stamped; per host tap seq S with the guest's
    queued and applied lines: tap_t <= queued_t (cross-game: dropped under an unfit clock) <= closed_t, waited = closed - queued +- 1,
    shown <= closed - the page's open stamp; at least one tap judged whole."""
    unstamped, judged, bad = [], 0, []
    for run in runs or []:
        for role in ("hl", "gl"):
            for c in edge_lines(run.get(role)):
                if not BW.swap_parse_stamp(c)[0]:
                    unstamped.append(c[:100])
        tp, qd, ap, op = taps(run.get("hl")), queued(run.get("gl")), applied(run.get("gl")), opened(run.get("gl"))
        for seq, tap in sorted(tp.items()):
            q, a = qd.get(seq), ap.get(seq)
            if q is None or a is None:
                continue
            judged += 1
            opens = [t for (w, x, t) in op if (w, x) == (a["win"], a["text"]) and t >= 0 and a["t"] >= 0 and t <= a["t"]]
            ok = (q >= 0 and a["t"] >= 0 and q <= a["t"] and (not clock_ok or (tap["t"] >= 0 and tap["t"] <= q))
                  and a["waited"] >= 0 and abs(a["waited"] - (a["t"] - q)) <= 1 and bool(opens) and 0 <= a["shown"] <= a["t"] - max(opens))
            if not ok:
                bad.append(f"seq {seq}: tap {tap['t']}, queued {q}, closed {a['t']} (waited {a['waited']}, shown {a['shown']}), "
                           f"opened {opens[-1:] or None}")
    parts = [("every edge line stamped", not unstamped), ("a tap judged whole", judged > 0), ("tap <= queued <= closed, waited, shown", not bad)]
    return _res(parts, f"{judged} taps judged; unstamped {len(unstamped)} {unstamped[:2]}; bad {bad[:2]}"
                       + ("" if clock_ok else "; tap <= queued not judged (DK-CLOCK unfit: cross-game)"))


def _status_over(results, none_why: str) -> tuple:
    """A probabilistic row over its runs: [(reached, ok, why)] -> UNREACHED when none reached, else every reached run green."""
    reached = [r for r in results if r[0]]
    if not reached:
        return U, f"{none_why} (0 of {len(results)} reached)"
    bad = [r for r in reached if not r[1]]
    return (R if bad else G), f"{len(reached)} of {len(results)} reached; " + "; ".join(r[2] for r in (bad or reached)[:3])


def judge_df_flash(fades) -> tuple:
    """DF-FLASH (PURE): ``fades`` [{D, fade (fade.last), cur}] -- REACHED on view_start heading or black."""
    res = []
    for f in fades or []:
        fl = f.get("fade") or {}
        reached = fl.get("view_start") in ("heading", "black")
        ok = (fl.get("action") == "join" or fl.get("by") == "own") and not dipped(f.get("cur"))
        res.append((reached, ok, f"D {f.get('D')}: {fl.get('view_start')}/{fl.get('path')}/{fl.get('action')} by {fl.get('by')}, "
                                 f"dip {dipped(f.get('cur'))}"))
    return _status_over(res, "no follow started on a heading or black screen")


def judge_df_grace(fades) -> tuple:
    """DF-GRACE (PURE): REACHED on the Join action (view black, or heading with <= 12 ticks left); green: ended by own."""
    res = []
    for f in fades or []:
        fl = f.get("fade") or {}
        left = ival(fl.get("left_start")) if "left_start" in fl else ival(f.get("left"))
        reached = fl.get("action") == "join" and (fl.get("view_start") == "black" or (fl.get("view_start") == "heading" and left is not None
                                                                                       and 0 <= left <= BW.FADE_FAST_FRAMES))
        res.append((reached, fl.get("by") == "own", f"D {f.get('D')}: {fl.get('view_start')} left {left}, by {fl.get('by')}"))
    return _status_over(res, "no Join start on DESK")


def judge_df_pace(fades) -> tuple:
    """DF-PACE (PURE): ``fades`` the D = 0.3 runs [{fade, commit_t, last_close_t}] -- REACHED when the copy lags (backlog_start line or
    ahead). Green: path backlog, by timer, the guest's last close for 359 before the commit."""
    res = []
    for f in fades or []:
        fl = f.get("fade") or {}
        reached = fl.get("backlog_start") in ("line", "ahead")
        lc, ct = ival(f.get("last_close_t")), ival(f.get("commit_t"))
        ok = fl.get("path") == "backlog" and fl.get("by") == "timer" and lc is not None and ct is not None and lc <= ct
        res.append((reached, ok, f"backlog {fl.get('backlog_start')}, path {fl.get('path')} by {fl.get('by')}, last close {lc} vs commit {ct}"))
    return _status_over(res, "the copy never lagged at the intent")


def probe_site(hi: dict):
    """The intent's emit site: `site` while it is live, `last_site` once it ended (the probe snapshot is taken at its end)."""
    return hi.get("site") or hi.get("last_site")


def judge_da_probe(trs, life_old: bool = False) -> tuple:
    """DA-PROBE (PURE): the MAPJUMP transitions' host intent blocks (``hi``) and the guest's seen copies. A transition whose
    intent.last_site is not mapjump is refused (not judged). Under the `life` word the life clauses are recorded, not judged."""
    judged, refused, bad, rep = 0, 0, [], []
    for tr in trs or []:
        hi, g = tr.get("hi") or {}, tr.get("g") or {}
        if probe_site(hi) != "mapjump":
            refused += 1
            continue
        judged += 1
        sends, copies = ival(hi.get("sends")), ival(_path(g, "last.seen_copies"))
        ok = (all((ival(hi.get(k)) or 0) >= 1 for k in ("frames", "updates", "sends")) and hi.get("oob") in ("sent", "overwritten")
              and copies is not None and sends is not None and 1 <= copies <= sends)
        if not life_old:
            ok = ok and hi.get("last_end") == "stands" and (ival(hi.get("landed_frames")) or 0) >= 1
        if not ok:
            bad.append(f"-> {tr.get('dest')}: frames {hi.get('frames')}, updates {hi.get('updates')}, sends {sends}, oob {hi.get('oob')!r}, "
                       f"copies {copies}, last_end {hi.get('last_end')!r}, landed_frames {hi.get('landed_frames')}")
        rep.append(f"-> {tr.get('dest')}: life {hi.get('last_life_ms')} ms ({hi.get('last_end')}), fps {hi.get('host_fps')}, emit dt "
                   f"{hi.get('emit_dt_us')} us, pin quality {_path(g, 'pin.last_use_quality')!r}")
    parts = [("a MAPJUMP intent judged", judged > 0), ("consistent" + ("" if life_old else ", stands, landed frames"), not bad)]
    return _res(parts, f"judged {judged}, refused (not mapjump) {refused}; {'; '.join(bad[:2])}; reported: {'; '.join(rep[:4])}")


def dcb_a_reached(g) -> bool:
    seen, own = _t(g, "last.seen_t"), _t(g, "last.own_t")
    return own is None or (seen is not None and seen <= own)


def judge_dc_b_a(runs, clock_ok: bool = True) -> tuple:
    """DC-B(a) (PURE): REST at act [{D, g, g0, maps, l139, g_land_t, h_land_t}]. An own jump before the intent (the s158 shape) is
    recorded "C2 not built" and not judged; every run that shape is VOID. The gap clause is cross-game (dropped when unfit); an L139
    never read makes the row VOID."""
    judged, c2, bad, rep = 0, 0, [], []
    for r in runs or []:
        g = r.get("g") or {}
        if not dcb_a_reached(g):
            c2 += 1
            continue
        judged += 1
        l139, gap = ival(r.get("l139")), _minus(r.get("g_land_t"), r.get("h_land_t"))
        if clock_ok and l139 is None:
            return V, f"D {r.get('D')}: L139 unread (a game's state never listed (win 3, text 139) and then dropped it)"
        bounces = _delta(r.get("g0"), g, "counts.bounces")
        ok = r.get("maps") == 1 and bounces == 0 and (not clock_ok or (gap is not None and gap <= max(0, l139) + DC_B_SLACK_MS))
        rep.append(f"D {r.get('D')}: gap {gap} ms, L139 {l139} ms")
        if not ok:
            bad.append(f"D {r.get('D')}: loads {r.get('maps')}, bounces +{bounces}, gap {gap} vs max(0, {l139}) + {DC_B_SLACK_MS}")
    if not judged:
        return V, f"every REST run took the s158 shape (an own jump before the intent: C2 not built) -- {c2} run(s)"
    return (R if bad else G), (f"judged {judged}, C2 not built {c2}; {'; '.join(bad[:2])}; reported: {'; '.join(rep)}"
                               + ("" if clock_ok else "; the gap clause VOID (DK-CLOCK unfit)"))


def dcb_b_reached(g, pre) -> bool:
    if _t(g, "last.own_t") is None or ival(_path(g, "last.own_dest")) != REST_DEST:
        return False
    seen = ival(so.sget(pre, "own.cache.field")) == REST_DEST or ival(so.nget(pre, "session.follow.pending")) == REST_DEST
    return seen and ival(so.sget(pre, "own.host_lane")) in (0, REST_FROM)


def judge_dc_b_b(runs) -> tuple:
    """DC-B(b) (PURE): REST-OLD [{D, g, g0, maps, pre}] -- ``pre`` the guest's last sample before its own jump."""
    res = []
    for r in runs or []:
        g, g0 = r.get("g") or {}, r.get("g0") or {}
        reached = dcb_b_reached(g, r.get("pre"))
        term = _path(g, "own.last.term")
        passed = _delta(g0, g, "own.passes") == 1 and _path(g, "last.own_verdict") == "pass" and _path(g, "last.own_why") in C_TERMS
        conv = _delta(g0, g, "own.converted")
        ok = (passed and (term != "pending" or conv == 1) and r.get("maps") == 1 and _delta(g0, g, "counts.bounces") == 0)
        res.append((reached, ok, f"D {r.get('D')}: {_path(g, 'last.own_verdict')}/{_path(g, 'last.own_why')} term {term!r}, converted "
                                 f"+{conv}, loads {r.get('maps')}, bounces +{_delta(g0, g, 'counts.bounces')}"))
    return _status_over(res, "no own jump to 352 with the intent seen before it")


def judge_dp_halt(runs) -> tuple:
    """DP-HALT (PURE): per DESK run [{g0, g}] -- REACHED on pin.pre_frames +>= 1; green: max_pre_diff 0."""
    res = []
    for r in runs or []:
        d = _delta(r.get("g0"), r.get("g"), "pin.pre_frames")
        mx = ival(_path(r.get("g"), "pin.max_pre_diff"))
        res.append((d is not None and d >= 1, mx == 0, f"pre_frames +{d}, max_pre_diff {mx}"))
    return _status_over(res, "no later pre-landing frame of a held nonce was compared")


def judge_dp_dress(runs) -> tuple:
    """DP-DRESS (PURE): [{want, leader}] after each 351 -> 352 landing; VOID when the host's leader or the guest's dress was unread."""
    pairs = [(ival(r.get("want")), ival(r.get("leader"))) for r in runs or []]
    if not pairs or any(w is None or w < 0 or ld is None or ld < 0 for w, ld in pairs):
        return V, f"the guest's want_char / the host's leader unread on some landing (self-dress off?): {pairs}"
    return _res([("want_char = the latest frame's leader", all(w == ld for w, ld in pairs))], f"(want, leader) {pairs}")


def cat_t0(gs) -> tuple:
    """(the guest's first (win 7, text 113) listing t, its first sample on 351 with host_flags b0 set, the else path ran)."""
    t113, t118 = first_listing_t(gs, CAT_FIRST), first_listing_t(gs, CAT_ELSE)
    b0 = next((so.now_ms(x) for x in gs or [] if _fid(x) == REST_FROM and (ival(so.nget(x, "host_flags")) or -1) >= 0
               and ival(so.nget(x, "host_flags")) & 0x01), None)
    return t113, b0, t118 is not None and (t113 is None or t118 < t113)


def judge_db_shape(ev) -> tuple:
    t113, tb0, else_path = cat_t0(ev.get("gs"))
    if else_path:
        return V, "text 118 opened first: 350's else path ran"
    passes = [ln for ln in ev.get("gl") or [] if (m := _RX["ate_hub_pass"].fullmatch(_strip(ln)[0]))
              and (int(m.group(1)), int(m.group(2)), int(m.group(3))) == (REST_FROM, CAT_PICK, CAT_FIELD)]
    parts = [("the own Field(351) passes on the host's pick (choice 3, field 350)", len(passes) >= 1),
             ("113 listed >= 4.5 s before host_flags b0 on 351", t113 is not None and tb0 is not None and tb0 - t113 >= 4500)]
    return _res(parts, f"113 at {t113}, b0 at {tb0} ({_minus(tb0, t113)} ms)")


def judge_db_bit(ev, clock_ok: bool = True, clock_why: str = "") -> tuple:
    if not clock_ok:
        return _void_clock(clock_why or "the instrument is unfit")
    t113, tb0, else_path = cat_t0(ev.get("gs"))
    if else_path:
        return V, "text 118 opened first: 350's else path ran"
    if t113 is None or tb0 is None:
        return R, f"no window: 113 at {t113}, b0 at {tb0}"
    inw = lambda x: so.now_ms(x) is not None and t113 <= so.now_ms(x) < tb0           # noqa: E731
    gw, hw = [x for x in ev.get("gs") or [] if inw(x)], [x for x in ev.get("hs") or [] if inw(x)]
    hf = lambda x: ival(so.nget(x, "host_flags")) if ival(so.nget(x, "host_flags")) is not None else -1   # noqa: E731
    parts = [("guest samples in the window", bool(gw)), ("host samples in the window", bool(hw)),
             ("host_flags b1 clear, b3 set", all(hf(x) >= 0 and not hf(x) & 0x02 and hf(x) & 0x08 for x in gw)),
             ("the lane on 351", all(ival(so.sget(x, "own.host_lane")) == REST_FROM for x in gw)),
             ("orphan.host_holds", all(so.sget(x, "orphan.host_holds") is True for x in gw)),
             ("every host sample control false", all(not _ctl(x) for x in hw))]
    return _res(parts, f"window {t113}..{tb0}: {len(gw)} guest / {len(hw)} host samples")


def judge_db_hold(ev) -> tuple:
    t113, _tb0, else_path = cat_t0(ev.get("gs"))
    if else_path:
        return V, "text 118 opened first: 350's else path ran"
    gl, key = ev.get("gl") or [], CAT_FIRST
    i_hold = [i for i, ln in enumerate(gl) if so.unstamped(ln) == so.hold_words(key)]
    ends = [(i, so.end_lines([ln], key)) for i, ln in enumerate(gl)]
    ends = [(i, e[0]) for i, e in ends if e]
    claim = (BW.SWAP_HOLD_END_WORDS[BW.SWAP_HOLD_END_EVENT], BW.SWAP_HOLD_END_WORDS[BW.SWAP_HOLD_END_BUSY])
    after = [e for i, e in ends if i_hold and i > i_hold[0]]
    closes = _minus(ival(ev.get("closes1")), ival(ev.get("closes0")))
    parts = [("one hold line", len(i_hold) == 1), ("then its end line at the host's claim", len(after) == 1 and after[0][1] in claim),
             ("no 'is not on the host's screen'", not so.not_on_screen(gl, key)), ("orphan_closes +0 across 351", closes == 0)]
    return _res(parts, f"end {after} (predicted '{claim[0]}'); {cb.grep(gl, 'dialogue orphan', limit=300)}")


def judge_db_order(ev) -> tuple:
    t113, _tb0, else_path = cat_t0(ev.get("gs"))
    if else_path:
        return V, "text 118 opened first: 350's else path ran"
    tp = taps(ev.get("hl"))
    host_seq = {}
    for seq, tap in sorted(tp.items()):
        if tap["win"] == CAT_FIRST[0] and tap["text"] in CAT_TEXTS and tap["closes"]:
            host_seq[tap["text"]] = seq
    ap = applied(ev.get("gl"))
    guest_seq = {a["text"]: seq for seq, a in sorted(ap.items()) if a["win"] == CAT_FIRST[0] and a["text"] in CAT_TEXTS and a["verb"] == "closed"}
    ns = [guest_seq.get(t) for t in CAT_TEXTS]
    drops = [ln for ln in ev.get("gl") or [] if f"dropped -- it is for field {REST_FROM}" in ln]
    parts = [("113-117 each closed by a host seq", all(n is not None for n in ns)),
             ("strictly increasing", all(n is not None for n in ns) and all(b > a for a, b in zip(ns, ns[1:]))),
             ("the host's tap seq for the same text", all(guest_seq.get(t) == host_seq.get(t) for t in CAT_TEXTS)),
             ("no 'dropped -- it is for field 351'", not drops)]
    return _res(parts, f"guest seqs {ns}, host seqs {[host_seq.get(t) for t in CAT_TEXTS]}")


def judge_dc_own(ev) -> tuple:
    g = ev.get("g") or {}
    rec = _path(g, "last.own_why") is not None or _path(g, "own.last.term") is not None or (ival(_path(g, "own.last.lane")) or -1) >= 0
    return _res([("one load of 450", so.maps(ev.get("gl"), OWN_DEST) == 1), ("the term or the lane recorded", rec)],
                f"own {_path(g, 'last.own_verdict')!r}/{_path(g, 'last.own_why')!r}, term {_path(g, 'own.last.term')!r}, lane "
                f"{_path(g, 'own.last.lane')}")


def judge_dl_defer(ev, fms: float = FRAME_MS_DEFAULT) -> tuple:
    g = ev.get("g") or {}
    d = _minus(_t(g, "last.follow_t"), ival(ev.get("menu_close_t")))
    return _res([("the follow came by the intent", _path(g, "last.follow_via") == "intent"),
                 (f"within {DL_DEFER_MS} ms of the menu's close", d is not None and -fms <= d <= DL_DEFER_MS)],
                f"follow_via {_path(g, 'last.follow_via')!r}, follow - menu close {d} ms")


def judge_dp_defer(ev, life_word: bool = False) -> tuple:
    """DP-DEFER (PURE): REACHED on a landing by the intent with the pin < 2500 ms old, quality pre and the host's mark in the latest
    frame (pin.last_diff >= 1: the stage was falsifiable); a late capture is UNREACHED; VOID under the `life` word."""
    if life_word:
        return V, "the `life` word: the deferred follow fires serially (s163's life), so the landing never comes by the intent"
    g = ev.get("g") or {}
    pin = _path(g, "pin") or {}
    if pin.get("last_use_quality") == "late":
        return U, f"the first frame I saw came after the host's landing (pin.late {pin.get('late')})"
    age = ival(pin.get("last_use_age_ms"))
    reached = (_path(g, "last.follow_via") == "intent" and age is not None and 0 <= age < DP_DEFER_AGE_MS and pin.get("last_use_quality") == "pre"
               and (ival(pin.get("last_diff")) or 0) >= 1)
    if not reached:
        return U, f"not reached: follow_via {_path(g, 'last.follow_via')!r}, age {age}, quality {pin.get('last_use_quality')!r}, diff {pin.get('last_diff')}"
    return _res([("flag 8720 = 0 (the pin's story)", ev.get("flag") is False)], f"flag {ev.get('flag')!r}; last_use {pin.get('last_use')!r}")


def judge_dp_aged(ev) -> tuple:
    pin = _path(ev.get("g"), "pin") or {}
    return _res([("flag 8720 = 1", ev.get("flag") is True), ("pin.last_use aged", pin.get("last_use") == "aged")],
                f"flag {ev.get('flag')!r}; last_use {pin.get('last_use')!r} age {pin.get('last_use_age_ms')}")


def judge_dp_mark(ev, clock_ok: bool = True, clock_why: str = "") -> tuple:
    if not clock_ok:
        return _void_clock(clock_why or "the instrument is unfit")
    g = ev.get("g") or {}
    lead = _minus(_t(g, "last.land_t"), ival(ev.get("host_flag_t")))
    if lead is None or lead < DP_MARK_LEAD_MS:
        return V, f"the host's mark preceded the guest's landing by {lead} ms (< {DP_MARK_LEAD_MS})"
    pin = _path(g, "pin") or {}
    if pin.get("last_use_quality") != "pre":
        return U, f"quality {pin.get('last_use_quality')!r}: the first frame I saw came after the host's landing"
    st = so.stages_lines(ev.get("gl"), ev.get("dest", AWAY))
    return _res([("flag 8720 = 0", ev.get("flag") is False), ("the pin line", bool(st)), ("last_diff >= 1", (ival(pin.get("last_diff")) or 0) >= 1)],
                f"lead {lead} ms; last_use {pin.get('last_use')!r}")


def judge_dl_left(ev, clock_ok: bool = True, clock_why: str = "") -> tuple:
    if not clock_ok:
        return _void_clock(clock_why or "the instrument is unfit")
    h, g = ev.get("h") or {}, ev.get("g") or {}
    n, start = ival(_path(h, "intent.nonce")), ival(ev.get("start_t"))
    last = _t(g, "seen.last_t")
    parts = [("the host's 'ended ... I left it' line", bool(stands_lines(ev.get("hl"), n, ev.get("dest", AWAY), BW.INTENT_END_LEFT))),
             ("intent.last_end left", _path(h, "intent.last_end") == "left"),
             ("the guest saw that nonce", ival(_path(g, "seen.nonce")) == n and last is not None),
             (f"seen.last_t within {DL_LEFT_MS} ms of the battle start", last is not None and start is not None and last <= start + DL_LEFT_MS)]
    return _res(parts, f"nonce {n}, battle start {start}, seen.last_t {last}")


def judge_df_open(ev) -> tuple:
    if ev.get("refused"):
        return V, f"the host's warp was refused with a window up ({str(ev['refused'])[:160]}): DF-PACE stands in as the backlog row"
    fl = ev.get("fade") or {}
    ms = ival(fl.get("ms"))
    return _res([("backlog_start open", fl.get("backlog_start") == "open"), ("path backlog", fl.get("path") == "backlog"),
                 ("by timer", fl.get("by") == "timer"), (f"ms >= {FADE_TIMER_MIN_MS}", ms is not None and ms >= FADE_TIMER_MIN_MS)],
                f"fade.last {fl}"[:300])


def judge_dp_party(trs) -> tuple:
    res = []
    for tr in trs or []:
        pe, pl = tr.get("party_emit"), tr.get("party_land")
        reached = isinstance(pe, list) and isinstance(pl, list) and pe != pl
        res.append((reached, tr.get("mirror_after") == pl, f"{tr.get('sub')} -> {tr.get('dest')}: party {pe} -> {pl}, mirror {tr.get('mirror_after')}"))
    return _status_over(res, "no landing changed the host's party between its emit and its landing")


def judge_lvd_role(res: dict) -> tuple:
    parts = [("guest life old: the host-side refusal", BW.swap_refusal_host_side("life") in (res.get("guest_life") or "")),
             ("host orphan old: the guest-side refusal", BW.swap_refusal_guest_side("orphan") in (res.get("host_orphan") or "")),
             ("host hostctl off: the selftest refusal", BW.swap_refusal_selftest("hostctl") in (res.get("host_hostctl") or "")),
             ("guest hostctl off: the selftest refusal", BW.swap_refusal_selftest("hostctl") in (res.get("guest_hostctl") or ""))]
    return _res(parts, "; ".join(f"{k}: {str(v)[:90]!r}" for k, v in res.items()))


def judge_lvd_life(acked: bool, lv_set, lv_reset) -> tuple:
    return _res([("acked", acked), ("levers.life old", _path(lv_set, "life") == "old"),
                 ("the reset releases it", isinstance(lv_reset, dict) and _path(lv_reset, "life") in (None, "act"))],
                f"set {lv_set!r}; after reset {lv_reset!r}"[:300])


# --------------------------------------------------------------------------------------------- the calibration (pure)
def marker(word: str, row: str, ev) -> tuple:
    """A predicted red's marker (PURE): ``ev`` the evidence the row's leg kept (ctx.marks[row]). -> (ok, detail)."""
    ev = ev if isinstance(ev, dict) else {}
    if word == "stamps":
        lines = [ln for run in ev.get("runs") or [] for role in ("hl", "gl") for ln in run.get(role) or []]
        el = edge_lines(lines)
        parts = [("edge lines seen", bool(el)), ("none stamped", not any(BW.swap_parse_stamp(c)[0] for c in el)),
                 ("no swap line", not any(BW.swap_line_class(so.core(ln)) == "instrument" for ln in lines))]
    elif word == "delay":
        fms = ev.get("frame") or FRAME_MS_DEFAULT
        gs = ev.get("cal1") or []
        parts = [("CAL1 ran", bool(gs)), ("commit - due within 1 frame of 0", bool(gs) and all(
            commit_minus_due(g) is not None and abs(commit_minus_due(g)) <= fms + 1 for g in gs)),
                 ("last.delay_ms 0", bool(gs) and all(ival(_path(g, "last.delay_ms")) == 0 for g in gs))]
    elif word == "orphan":
        gl = ev.get("gl") or []
        auto = [ln for ln in gl if f"dialogue orphan: win {CAT_FIRST[0]} text {CAT_FIRST[1]} auto-closed" in ln]
        parts = [("orphan.holds +0", _minus(ival(ev.get("holds1")), ival(ev.get("holds0"))) == 0),
                 ("113 orphaned or auto-closed", bool(so.not_on_screen(gl, CAT_FIRST)) or bool(auto))]
    elif word == "own":
        runs = [r for r in ev.get("runs") or [] if dcb_b_reached(r.get("g") or {}, r.get("pre"))]
        parts = [("a reached run", bool(runs)), ("a bounce and a second load", any(
            _path(r.get("g"), "last.own_verdict") == "bounce" and (r.get("maps") or 0) >= 2 for r in runs))]
    elif word == "pin":
        pin = _path(ev.get("g"), "pin") or {}
        parts = [("flag 8720 = 1", ev.get("flag") is True), ("pin.last_use lever", pin.get("last_use") == "lever"),
                 ("pin.last_use_quality pre", pin.get("last_use_quality") == "pre")]
    elif word == "life":
        if row == "DL-LIFE":
            his = ev.get("intents") or []
            parts = [("CAL intents", bool(his)), ("last_end old", bool(his) and all(hi.get("last_end") == "old" for hi in his))]
        else:
            parts = [("the serial follow", _path(ev.get("g"), "last.follow_via") == "serial")]
    elif word == "nocache":
        parts = [("no predicted red", False)]
    else:                                                # the fade words
        fades = [f.get("fade") or {} for f in ev.get("fades") or []]
        if word == "fade":
            parts = [("a follow", bool(fades)), ("path old", bool(fades) and all(f.get("path") == "old" for f in fades))]
        elif word == "long":
            parts = [("a follow", bool(fades)), ("path fast, frames 24", bool(fades) and all(
                f.get("path") == "fast" and ival(f.get("frames")) == BW.FADE_OLD_FRAMES for f in fades))]
        else:
            parts = [("a follow", bool(fades)), ("path fast over a backlog", bool(fades) and all(
                f.get("path") == "fast" and f.get("backlog_start") in ("line", "ahead", "key", "open") for f in fades))]
    return _res(parts)


def judge_cal(word: str, failed, void, unreached, legs) -> tuple:
    """D-CAL (PURE): exactly the predicted rows red -- the word's MUST rows plus its "if reached" rows that were reached. A predicted
    row that read UNREACHED or VOID fails the exactness (never a 'not green'); every MUST row UNREACHED or VOID is VOID, never a pass;
    BASELINE_RED (the pre-registered defect) and VOID / UNREACHED rows elsewhere are reported, never counted."""
    must, cond = set(predicted(word, legs)), set(conditional(word, legs))
    out = set(void) | set(unreached)
    pred = must | (cond - out)
    failed = set(failed) - set(FINALS)
    if must and must <= out:
        return False, f"VOID: every predicted red read UNREACHED or VOID ({', '.join(sorted(must))})"
    missing = sorted(pred - failed - out)
    lost = sorted(must & out)
    extra = sorted(failed - pred - out - set(BASELINE_RED))
    ok = not missing and not lost and not extra
    return ok, (f"`{word}`: predicted reds that stayed GREEN: {missing or 'none'}; predicted reds UNREACHED/VOID: {lost or 'none'}; "
                f"unpredicted reds: {extra or 'none'}; conditional reds reached: {sorted(cond - out) or 'none'}; baseline "
                f"{sorted(failed & set(BASELINE_RED)) or 'green'}; VOID/UNREACHED elsewhere: {sorted(out - pred) or 'none'}")


def predicted_now(word: str, void, unreached, legs) -> tuple:
    """The rows a word must red on this run (its MUST rows and its reached "if reached" rows): D-CAL-M's marker set."""
    out = set(void) | set(unreached)
    return tuple(predicted(word, legs)) + tuple(r for r in conditional(word, legs) if r not in out)


# --------------------------------------------------------------------------------------------- the run
class Ctx:
    def __init__(self, cal: str | None, legs: str):
        self.cal = cal
        self.legs = _legs(legs)
        self.clock = {"host": ("skip", "not run"), "guest": ("skip", "not run")}
        self.clock_ok = False
        self.clock_why = "not run"
        self.void: set = set()
        self.unreached: set = set()
        self.marks: dict = {}
        self.lever_taken = False
        self.lane: list = []                             # DA-LANE's transitions (CAL, DESK, REST)
        self.all_trs: list = []                          # DP-PARTY's
        self.arrivals: list = []                         # DA-ARRIVE's
        self.won: list = []                              # DC-WON's report
        self.probe_x: list = []                          # DA-PROBE-X's report
        self.fms = FRAME_MS_DEFAULT
        self.registered: dict = {}


def record(led: cb.Ledger, ctx: Ctx, rid: str, res: tuple) -> None:
    """Record one judge's (status, detail): green; red; UNREACHED (green, never red for that alone, out of every count); VOID (red,
    out of every count)."""
    status, detail = res
    if rid not in led.catalog or rid in led.done:
        return
    if status == G:
        led.check(rid, True, detail)
    elif status == U:
        ctx.unreached.add(rid)
        led.check(rid, True, f"UNREACHED (never red for that alone): {detail}")
    elif status == V:
        ctx.void.add(rid)
        led.check(rid, False, f"VOID: {detail}")
    else:
        led.check(rid, False, detail)


def _lost(led: cb.Ledger, ctx: Ctx, rows, why: str) -> None:
    for r in rows:
        if r in led.catalog and r not in led.done:
            ctx.void.add(r)
            led.check(r, False, f"not reached: {why}")


def slim(st) -> dict:
    """One publish as the judges read it (the engine's nesting, pruned): what a long leg can afford to keep per frame."""
    raw = cb.raw(st)
    ns = raw.get("netsync") or {}
    sess, sto, dr = ns.get("session") or {}, ns.get("stepout") or {}, ns.get("dress") or {}
    dl = raw.get("dialog") or {}
    sw = ns.get("swap") if isinstance(ns.get("swap"), dict) else None
    if sw is not None:
        sw = {k: v for k, v in sw.items() if k != "slot"}
    return {"frame": raw.get("frame"), "field": {"id": (raw.get("field") or {}).get("id")},
            "player": {"control": (raw.get("player") or {}).get("control")}, "ui_state": raw.get("ui_state"), "scene": raw.get("scene"),
            "dialog": {"open": dl.get("open"), "texts": list(dl.get("texts") or [])[:1], "choice": dl.get("choice")},
            "flags": dict(raw.get("flags") or {}),
            "netsync": {"windows": ns.get("windows"), "host_flags": ns.get("host_flags"), "host_settled_ms": ns.get("host_settled_ms"),
                        "orphan_closes": ns.get("orphan_closes"), "session": {"follow": {"pending": (sess.get("follow") or {}).get("pending")}},
                        "stepout": {"active": sto.get("active"), "base": {"age_ms": (sto.get("base") or {}).get("age_ms")},
                                    "out_why": dict(sto.get("out_why") or {})},
                        "dress": {"party": dr.get("party"), "mirror_party": dr.get("mirror_party"),
                                  "self": {"want_char": (dr.get("self") or {}).get("want_char")},
                                  "guard": {"leader": (dr.get("guard") or {}).get("leader")}},
                        "swap": sw}}


class _Watch:
    """Both games' publishes, every distinct frame each read sees (slim), with hooks run on each new sample."""

    def __init__(self, d):
        self.d = d
        self.s = {"host": [], "guest": []}
        self.seen = {"host": None, "guest": None}
        self.t0 = time.time()
        self.hooks: list = []

    def pump(self) -> None:
        for role in ("host", "guest"):
            st = (self.d.host if role == "host" else self.d.guest).state
            if st.frame == self.seen[role]:
                continue
            self.seen[role] = st.frame
            x = slim(st)
            x["_t"] = time.time() - self.t0
            self.s[role].append(x)
            for h in list(self.hooks):
                h(role, x)

    def until(self, cond, timeout: float, poll: float = 0.004) -> bool:
        deadline = time.time() + timeout
        while True:
            self.pump()
            try:
                if cond(self):
                    return True
            except (TypeError, KeyError, AttributeError, IndexError, ValueError):
                pass
            if time.time() >= deadline:
                return False
            time.sleep(poll)

    def hold(self, seconds: float) -> None:
        self.until(lambda w: False, seconds)

    def last(self, role: str) -> dict:
        return self.s[role][-1] if self.s[role] else {}


class _HostPager:
    """The host confirms ``pace_s`` after each line opens and again every ``pace_s`` until it closes (a press on a line still typing
    only finishes it: the host taps only on a confirm that advances, NetSyncClient.cs:7293-7294)."""

    def __init__(self, host, pace_s: float):
        self.host, self.pace = host, pace_s
        self.key, self.since, self.presses, self.on = None, 0.0, 0, True

    def __call__(self, role: str, x: dict) -> None:
        if role != "host" or not self.on:
            return
        dl = x.get("dialog") or {}
        if not dl.get("open"):
            self.key = None
            return
        k = (((dl.get("texts") or [""])[0] or "")[:80], bool(dl.get("choice")))
        now = time.time()
        if k != self.key:
            self.key, self.since = k, now
        elif now - self.since >= self.pace:
            try:
                self.host.press("confirm", 2)
                self.presses += 1
            except HarnessError:
                pass
            self.since = time.time()


def _msgs(d, role: str, at: int = 0) -> list:
    return [m for _t, _l, m in d.lines(role)[at:]]


class _DuoG:
    """cb.Ledger's ``g``: each row recorded on the duo (and the guest's report), its id the catalog's."""

    def __init__(self, d):
        self.d = d

    def check(self, ok, what, detail=""):
        return self.d.check(bool(ok), str(what), str(detail), role="guest", cid=str(what).split(":", 1)[0])

    def note(self, msg):
        self.d.note(str(msg))


def _ns(g, sub: str, *args) -> tuple:
    return cb.try_ns(g, sub, *args)


def _lever(g, ctx: Ctx, op: str, word, *, word_lever: bool = False) -> bool:
    """`swap <op> <word>` on one game, read back in `levers`; a word's own lever marks it taken."""
    ok, why = _ns(g, "swap", op, word)
    key, vals = so.lever_want(op, str(word))
    back = ok and cb.poll(g, lambda s: so.sget(s, "levers." + key, "?") in vals, 3.0, f"levers.{key}") is not None
    if word_lever and back:
        ctx.lever_taken = True
    if not ok:
        g.note(f"swap {op} {word} refused: {why[:200]}")
    return back


def _settled(d, field: int) -> bool:
    g, h = d.guest.state, d.host.state
    return (g.field_id == field and h.field_id == field and g.control and h.control and not g.dialog_open
            and cb.path(g, "netsync.session.follow.pending", -1) == -1)


def _seat(d, field: int) -> None:
    """Both on ``field`` with control and no follow in flight: the host warps there and the guest follows (a guest left elsewhere
    after SEAT_S is warped there itself, noted)."""
    if _settled(d, field):
        return
    if d.host.state.field_id != field:
        d.host.send(f"warp {field} -1 -1", wait=False)
    deadline = time.time() + SEAT_S
    while time.time() < deadline and not _settled(d, field):
        st = d.host.state
        if st.dialog_open:
            d.host.press("confirm", 2)
        time.sleep(0.2)
    if d.guest.state.field_id != field:
        d.note(f"re-seat: the guest is on {d.guest.state.field_id}, not {field}, after {SEAT_S:g} s -- warping it there")
        d.guest.send(f"warp {field} -1 -1", wait=False)
        deadline = time.time() + SEAT_S
        while time.time() < deadline and not _settled(d, field):
            time.sleep(0.2)
    if not _settled(d, field):
        raise HarnessError(f"the pair never settled on {field}")
    time.sleep(1.0)


def _closed(x) -> bool:
    return so.sget(x, "last.state") == "done"


def _transition(d, lane: str, sub: str, dest: int, *, entrance: int = 0, scenario: int = -1, hold_s: float = CAL_HOLD_S,
                kind: str | None = None) -> dict:
    """The host's harness warp to ``dest`` with the guest following, watched until both landed and (``hold_s`` after) both records
    closed: one transition's evidence (tr_evidence)."""
    host = d.host
    frm = host.state.field_id
    ah, ag = len(d.lines("host")), len(d.lines("guest"))
    w = _Watch(d)
    w.pump()
    host.send(f"warp {dest} {entrance} {scenario}", wait=False)
    landed = w.until(lambda w: _fid(w.last("guest")) == dest and _fid(w.last("host")) == dest, ARRIVE_S)
    t_land = time.time()
    w.until(lambda w: time.time() - t_land >= hold_s and _closed(w.last("guest")) and _closed(w.last("host")), hold_s + 8.0)
    tr = tr_evidence(lane, sub, dest, frm, w.s["host"], w.s["guest"], _msgs(d, "host", ah), _msgs(d, "guest", ag), kind)
    tr["landed"] = landed
    tr["fms"] = so.frame_ms(w.s["guest"])
    return tr


def run_duo(d) -> None:
    cal, legs = CAL_MODE, LEGS_SEL                       # read at load: an unknown word or leg never reached a booted pair
    ctx = Ctx(cal, legs)
    led = cb.Ledger(_DuoG(d), catalog(cal, legs), finals=FINALS if cal else (), width=1400)
    strict, d.strict = d.strict, False
    try:
        _run(d, led, ctx)
    except HarnessError as err:
        d.note(f"the run raised: {str(err)[:400]}")
        _lost(led, ctx, [r for r in led.pending() if r not in FINALS], f"the run raised ({str(err)[:200]})")
    finally:
        _teardown(d, ctx)
        d.note(f"DK-CLOCK (a precondition, never a red row): host {ctx.clock['host'][0].upper()}, guest {ctx.clock['guest'][0].upper()} "
               f"-- {ctx.clock_why}")
        d.note(f"DC-WON (reported, never judged): {'; '.join(ctx.won) or 'no DESK run'}")
        d.note(f"DA-PROBE-X (exploratory, reported only): {'; '.join(ctx.probe_x[:12]) or 'no CAL transition'}")
        try:
            d.note(f"logs archived: {d.archive('field-swap-' + (cal or 'plain'))}")
        except Exception as err:                            # noqa: BLE001 - teardown must not mask the verdicts
            d.note(f"archive failed: {err}")
        for r in led.pending():
            if r not in FINALS:
                ctx.void.add(r)
        led.close("not reached: the run ended before this check")
        if cal is not None:
            pred = predicted_now(cal, ctx.void, ctx.unreached, ctx.legs)
            marks = {r: marker(cal, r, ctx.marks[r]) if r in ctx.marks else (R, "NO RUN") for r in pred}
            ok = ctx.lever_taken and all(st == G for st, _ in marks.values())
            led.check("D-CAL-M", ok, f"lever {'taken' if ctx.lever_taken else 'NOT TAKEN'}; "
                                     + ("; ".join(f"{r}: {dt}" for r, (_st, dt) in marks.items()) or "no predicted red (a control)"))
            ok, detail = judge_cal(cal, led.failed(), ctx.void, ctx.unreached, ctx.legs)
            led.check("D-CAL", ok, detail)
        led.close(final=True)
        d.strict = strict


def _teardown(d, ctx: Ctx) -> None:
    for step in (lambda: _ns(d.guest, "swap", "clear"), lambda: _ns(d.host, "swap", "clear"), lambda: d.guest.speedmode(False),
                 lambda: d.host.flag(P_FLAG, False), lambda: d.guest.state_every(2), lambda: d.host.state_every(2)):
        try:
            step()
        except Exception as err:                            # noqa: BLE001 - a dead game says so in its own rows
            d.note(f"teardown step failed: {str(err)[:160]}")


def _run(d, led: cb.Ledger, ctx: Ctx) -> None:
    host, guest = d.host, d.guest
    cb.provenance(guest)
    if not (cb.has(guest.state, PROBE) and cb.has(host.state, PROBE)):
        _lost(led, ctx, [r for r in led.catalog if r not in FINALS],
              "an engine publishes no `netsync.swap` (s163 or older) -- the run is refused")
        return
    try:
        ctx.registered = {"host": host.registered_fields()[0], "guest": guest.registered_fields()[0]}
    except (HarnessError, OSError) as err:
        d.note(f"registrations unreadable: {err}")
    for g in (host, guest):
        for step in (lambda g=g: g.state_every(1), lambda g=g: g.no_encounters(True)):
            try:
                step()
            except (HarnessError, AttributeError) as err:
                d.note(f"setup step refused ({str(err)[:120]})")
    _seat(d, HOME)
    _dk_clock(d, ctx)
    if ctx.cal == "stamps":
        a = _lever(host, ctx, "stamps", "off")
        b = _lever(guest, ctx, "stamps", "off")
        ctx.lever_taken = a and b
    for leg, fn in (("CAL", _leg_cal), ("DESK", _leg_desk), ("CAT", _leg_cat), ("OWN", _leg_own), ("MENU", _leg_menu),
                    ("MARK", _leg_mark), ("LEFT", _leg_left), ("OPEN", _leg_open)):
        if leg in ctx.legs:
            _guard(d, ctx, led, tuple(r for r in LEG_ROWS[leg] if r not in LATE_ROWS), lambda fn=fn: fn(d, ctx, led))
    if "CAL" in ctx.legs:                                # after DESK: its 351 arrivals are DA-ARRIVE's DESK watch
        record(led, ctx, "DA-ARRIVE", judge_da_arrive(ctx.arrivals, ctx.clock_ok, ctx.clock_why))
    if any(leg in ctx.legs for leg in ("CAL", "DESK")):
        legs = tuple(x for x in LANE_LABELS if (x == "CAL" and "CAL" in ctx.legs) or (x != "CAL" and "DESK" in ctx.legs))
        record(led, ctx, "DA-LANE", judge_da_lane(ctx.lane, legs, ctx.clock_ok, ctx.clock_why))
    record(led, ctx, "DP-PARTY", judge_dp_party(ctx.all_trs))
    if "LEVERS" in ctx.legs:
        _guard(d, ctx, led, LEG_ROWS["LEVERS"], lambda: _leg_levers(d, ctx, led))


def _guard(d, ctx: Ctx, led: cb.Ledger, rows: tuple, fn) -> None:
    todo = [r for r in rows if r in led.catalog and r not in led.done]
    if not todo:
        return
    try:
        fn()
    except HarnessError as err:
        _lost(led, ctx, todo, f"the leg raised: {str(err)[:300]}")
    except Exception as err:                             # noqa: BLE001 - a BENCH bug: red and loud, the run goes on
        d.note(f"{'/'.join(todo)} FAULTED (a bench bug, not a verdict): {err!r}"[:400])
        _lost(led, ctx, todo, f"the leg FAULTED (a bench bug): {err!r}"[:300])
    _lost(led, ctx, todo, "the leg recorded nothing")


def _dk_clock(d, ctx: Ctx) -> None:
    """DK-CLOCK: the solo's K-CLOCK judge on BOTH games (a note; its failure VOIDs every cross-game row)."""
    have = _qpc_ms is not None and _qpc_ms() is not None
    for role in ("host", "guest"):
        g = d.host if role == "host" else d.guest
        reads, seen = [], None
        deadline = time.time() + so.CLOCK_WATCH_S
        while have and time.time() < deadline and len(reads) < so.CLOCK_MIN + 10:
            st = g.state
            if st.frame != seen:
                seen = st.frame
                reads.append((_qpc_ms(), int(time.time() * 1000), dict(cb.raw(st))))
            time.sleep(0.004)
        ctx.clock[role] = so.judge_clock(reads, have)
    ctx.clock_ok = all(v[0] == "green" for v in ctx.clock.values())
    ctx.clock_why = "; ".join(f"{r} {v[1][:200]}" for r, v in ctx.clock.items())


# ---- CAL
def cal_subs(word: str | None) -> list:
    """CAL's sub-legs (name, guest fade lever, guest delay, guest speedmode, destination, arrival kinds out / home): the word's fade
    lever replaces `act` on CAL2 and CAL3 only; CAL0 / CAL1 / both ARRIVE runs keep their registered levers."""
    act = FADE_WORDS.get(word, "act")
    delay = 0 if word == "delay" else CAL_DELAY_MS
    return [("CAL0", "old", 0, False, AWAY, "control", "control"), ("CAL1", "old", delay, False, AWAY, None, None),
            ("CAL2", act, 0, False, AWAY, "watch", "watch"), ("CAL3", act, 0, True, AWAY, None, None),
            ("ARRIVE", "act", 0, False, ARRIVE_ID, "gate", "watch"), ("ARRIVE-OLD", "old", 0, False, ARRIVE_ID, "control", "control")]


def _leg_cal(d, ctx: Ctx, led: cb.Ledger) -> None:
    host, guest = d.host, d.guest
    _seat(d, HOME)
    life = ctx.cal == "life"
    arrive_ok = all(ARRIVE_ID in (ctx.registered.get(r) or {}) for r in ("host", "guest"))
    if not arrive_ok:
        d.note(f"ARRIVE_ID {ARRIVE_ID} is not registered on both roots -- deploy it once: {deploy_command()} (then relaunch)")
    by: dict = {}
    if life:
        _lever(host, ctx, "life", "old", word_lever=True)
    try:
        for name, fade, delay, speed, dest, k_out, k_home in cal_subs(ctx.cal):
            if dest == ARRIVE_ID and not arrive_ok:
                continue
            _lever(guest, ctx, "fade", fade, word_lever=(ctx.cal in FADE_WORDS and name in ("CAL2", "CAL3")))
            _lever(guest, ctx, "delay", delay, word_lever=(ctx.cal == "delay" and name == "CAL1"))
            if speed:
                guest.speedmode(True)
            try:
                for to, kind in ((dest, k_out), (HOME, k_home)):
                    tr = _transition(d, "CAL", name, to, kind=kind)
                    by.setdefault(name, []).append(tr)
                    ctx.lane.append(tr)
                    ctx.all_trs.append(tr)
                    if kind:
                        ctx.arrivals.append(arrival_of(tr, kind))
                    ctx.probe_x.append(f"{name} -> {to}: site {probe_site(tr['hi'])}, frames "
                                       f"{tr['hi'].get('frames')}, updates {tr['hi'].get('updates')}, sends {tr['hi'].get('sends')}, "
                                       f"oob {tr['hi'].get('oob')!r}, life {tr['hi'].get('last_life_ms')} ({tr['hi'].get('last_end')})")
            finally:
                if speed:
                    guest.speedmode(False)
                _ns(guest, "swap", "delay", 0)
                _ns(guest, "swap", "fade", "act")
    finally:
        if life:
            _ns(host, "swap", "life", "act")
    cal = [tr for k in ("CAL0", "CAL1", "CAL2", "CAL3") for tr in by.get(k, [])]
    ctx.fms = min([tr["fms"] for tr in cal] or [FRAME_MS_DEFAULT])
    cal1 = [tr["g"] for tr in by.get("CAL1", [])]
    ctx.marks["DA-CAL"] = {"cal1": cal1, "frame": ctx.fms}
    ctx.marks["DL-LIFE"] = {"intents": [tr["hi"] for tr in cal]}
    ctx.marks["DF-FAST"] = {"fades": [{"fade": _path(tr["g"], "fade.last")} for tr in by.get("CAL2", [])]}
    ctx.marks["DF-3X"] = {"fades": [{"fade": _path(tr["g"], "fade.last")} for tr in by.get("CAL3", [])]}
    record(led, ctx, "DA-CAL", judge_da_cal([tr["g"] for tr in by.get("CAL0", [])], cal1, ctx.fms))
    record(led, ctx, "DA-JOIN", judge_da_join(cal))
    record(led, ctx, "DL-LIFE", judge_dl_life(cal))
    record(led, ctx, "DL-NOREG", judge_dl_noreg(cal))
    record(led, ctx, "DC-FE", judge_dc_fe([ln for tr in cal for ln in tr["gl"]], cal[0]["g0"] if cal else {}, cal[-1]["g"] if cal else {}))
    record(led, ctx, "DF-FAST", judge_df_fast(by.get("CAL2", []), by.get("CAL0", []), ctx.clock_ok))
    record(led, ctx, "DF-3X", judge_df_3x(by.get("CAL3", [])))
    if not arrive_ok:
        record(led, ctx, "DA-ARRIVE", (R, f"not reached: ARRIVE_ID {ARRIVE_ID} is not registered on both roots (deploy: "
                                          f"{deploy_command()}, then relaunch)"))


# ---- DESK + REST
def desk_runs(word: str | None) -> list:
    """The six DESK runs: (D, REST-OLD) -- at each D one with REST at act and one REST-OLD."""
    return [(dd, old) for dd in DS for old in (False, True)]


def desk_evidence(D: float, rest_old: bool, hs, gs, hl, gl, word: str | None = None) -> dict:
    """One DESK run's evidence off its samples (pure): the three transitions, the 351 follow's fade, DC-B's inputs, DP-HALT's,
    DP-DRESS's, DA-LINES' lines and DC-WON's counts."""
    hs, gs = list(hs or []), list(gs or [])
    h359, g359 = land_idx(hs, DESK_FIELD) or 0, land_idx(gs, DESK_FIELD) or 0
    h351, g351 = land_idx(hs, REST_FROM, h359), land_idx(gs, REST_FROM, g359)
    act_fade = FADE_WORDS.get(word, "act")
    t359 = tr_evidence("DESK", f"D{D}", DESK_FIELD, HOME, hs, gs)
    t351 = tr_evidence("DESK", f"D{D}", REST_FROM, DESK_FIELD, hs[h359:], gs[g359:],
                       kind="control-desk" if act_fade == "old" else "watch-desk")
    t352 = tr_evidence("REST", f"D{D}{'-OLD' if rest_old else ''}", REST_DEST, REST_FROM, hs[h351 or 0:], gs[g351 or 0:])
    g = t351["g"]
    fl = dict(_path(g, "fade.last") or {})
    fl["left_start"] = fade_left_start(gs[g359:], _t(g, "last.follow_t"), REST_FROM)
    cur = fade_cur_window(gs[g359:], _t(g, "last.follow_t"), _t(fl, "due_t"), REST_FROM)
    g3 = t352["g"]
    own_t = _t(g3, "last.own_t")
    pre = sample_at(gs, own_t - 1) if own_t is not None else None
    g0_rest = dict(so.swb(gs[g351]) or {}) if g351 is not None else {}
    on352 = [x for x in gs if _fid(x) == REST_DEST]
    h352 = [x for x in hs if _fid(x) == REST_DEST]
    leader = ival(so.nget(h352[-1], "dress.guard.leader")) if h352 else None
    if (leader is None or leader < 0) and h352:
        party = so.nget(h352[-1], "dress.party") or []
        leader = ival(party[0]) if party else None
    return {"D": D, "old": rest_old, "t359": t359, "t351": t351, "t352": t352,
            "fade": {"D": D, "fade": fl, "cur": cur, "commit_t": _t(g, "last.commit_t"), "last_close_t": last_close_on(gs, DESK_FIELD)},
            "rest": {"D": D, "g": g3, "g0": g0_rest, "maps": so.maps(gl, REST_DEST), "pre": pre,
                     "l139": _minus(close_t(gs, DESK_LAST), host_close_t(hs, gs, DESK_LAST)),
                     "g_land_t": t352["g_land_t"], "h_land_t": t352["h_land_t"]},
            "halt": {"g0": dict(so.swb(gs[0]) or {}) if gs else {}, "g": dict(so.swb(gs[-1]) or {}) if gs else {}},
            "dress": {"want": ival(so.nget(on352[-1], "dress.self.want_char")) if on352 else None, "leader": leader},
            "lines": {"hl": list(hl or []), "gl": list(gl or [])},
            "won": {"desk": (_delta(t359["g0"], t351["g"], "counts.follow_won"), _path(t351["g"], "own.by")),
                    "rest": (_delta(g0_rest, g3, "counts.follow_won"), _path(g3, "own.by"))}}


def _leg_desk(d, ctx: Ctx, led: cb.Ledger) -> None:
    host, guest = d.host, d.guest
    act_fade = FADE_WORDS.get(ctx.cal, "act")
    runs = []
    if ctx.cal == "life":
        _lever(host, ctx, "life", "old", word_lever=True)
    try:
        for D, rest_old in desk_runs(ctx.cal):
            runs.append(_desk_run(d, ctx, D, rest_old, act_fade))
    finally:
        _ns(guest, "swap", "fade", "act")
        _ns(guest, "swap", "own", "act")
        if ctx.cal == "life":
            _ns(host, "swap", "life", "act")
    for r in runs:
        ctx.lane += [r["t359"], r["t351"], r["t352"]]
        ctx.all_trs += [r["t359"], r["t351"], r["t352"]]
        ctx.arrivals.append(arrival_of(r["t351"], r["t351"]["kind"]))
        ctx.won.append(f"D {r['D']}{' REST-OLD' if r['old'] else ''}: DESK follow_won +{r['won']['desk'][0]} by {r['won']['desk'][1]}; "
                       f"REST follow_won +{r['won']['rest'][0]} by {r['won']['rest'][1]}")
    fades = [r["fade"] for r in runs]
    ctx.marks["DA-LINES"] = {"runs": [r["lines"] for r in runs]}
    ctx.marks["DF-FLASH"] = {"fades": fades}
    ctx.marks["DF-PACE"] = {"fades": [r["fade"] for r in runs if r["D"] == PACE_D]}
    ctx.marks["DC-B(b)"] = {"runs": [r["rest"] for r in runs if r["old"]]}
    record(led, ctx, "DA-LINES", judge_da_lines([r["lines"] for r in runs], ctx.clock_ok))
    record(led, ctx, "DF-FLASH", judge_df_flash(fades))
    record(led, ctx, "DF-GRACE", judge_df_grace(fades))     # under `fade` the Old path never joins: UNREACHED by its own reach
    record(led, ctx, "DF-PACE", judge_df_pace([r["fade"] for r in runs if r["D"] == PACE_D]))
    record(led, ctx, "DA-PROBE", judge_da_probe([t for r in runs for t in (r["t351"], r["t352"])], life_old=ctx.cal == "life"))
    record(led, ctx, "DC-B(a)", judge_dc_b_a([r["rest"] for r in runs if not r["old"]], ctx.clock_ok))
    record(led, ctx, "DC-B(b)", judge_dc_b_b([r["rest"] for r in runs if r["old"]]))
    record(led, ctx, "DP-HALT", judge_dp_halt([r["halt"] for r in runs]))
    record(led, ctx, "DP-DRESS", judge_dp_dress([r["dress"] for r in runs]))


def _desk_run(d, ctx: Ctx, D: float, rest_old: bool, act_fade: str) -> dict:
    host, guest = d.host, d.guest
    _seat(d, HOME)
    _lever(guest, ctx, "fade", act_fade, word_lever=act_fade != "act")
    _lever(guest, ctx, "own", "act")
    ah, ag = len(d.lines("host")), len(d.lines("guest"))
    w = _Watch(d)
    pager = _HostPager(host, D)
    w.hooks.append(pager)
    fired = {"old": False}

    def rest_lever(role: str, x: dict) -> None:            # REST-OLD: before text 139 closes (P6)
        if not rest_old or fired["old"] or role != "guest" or _fid(x) != REST_FROM:
            return
        if any(so.win_of(x, k) is not None for k in REST_OLD_AT):
            fired["old"] = True
            _lever(guest, ctx, "fade", "old")
            if ctx.cal in ("own", "nocache"):
                _lever(guest, ctx, "own", "old" if ctx.cal == "own" else "nocache", word_lever=True)
    w.hooks.append(rest_lever)
    w.pump()
    host.send(f"warp {DESK_FIELD} 0 {DESK_SCENARIO}", wait=False)
    w.until(lambda w: _fid(w.last("guest")) == REST_DEST and _fid(w.last("host")) == REST_DEST, DESK_S)
    w.until(lambda w: _closed(w.last("guest")) and so.sget(w.last("host"), "intent.active") is False, 15.0)
    w.hold(1.0)
    pager.on = False
    if rest_old and not fired["old"]:
        d.note(f"DESK D {D} REST-OLD: the guest never listed text 138 / 139 on 351 -- its `fade old` was never sent")
    return desk_evidence(D, rest_old, w.s["host"], w.s["guest"], _msgs(d, "host", ah), _msgs(d, "guest", ag), ctx.cal)


# ---- CAT
def _gate(g, rows: int) -> None:
    g.poke(GATE_BYTES[0], 1)
    g.poke(GATE_BYTES[1], rows & 0xFF)
    g.poke(GATE_BYTES[2], (rows >> 8) & 0xFF)


def _gate_reads(st) -> tuple:
    return tuple(duo_mod.watched_byte(st, b) for b in GATE_BYTES)


def _leg_cat(d, ctx: Ctx, led: cb.Ledger) -> None:
    host, guest = d.host, d.guest
    _seat(d, HOME)
    tr = _transition(d, "CAT", "CAT", CAT_FIELD, scenario=CAT_SCENARIO, hold_s=2.0)
    ctx.all_trs.append(tr)
    if not _settle_both(d, CAT_FIELD):
        raise HarnessError("the pair never settled on 350")
    for g in (host, guest):
        g.watch(*(b * 8 + i for b in GATE_BYTES for i in range(8)))
    host.watch(*(LEAP_BYTE * 8 + i for i in range(8)), LEAP_FLAG)
    guest.speedmode(True)
    try:
        b297 = duo_mod.watched_byte(cb.poll(host, lambda s: duo_mod.watched_byte(s, LEAP_BYTE) is not None, 3.0, "297") or host.state,
                                    LEAP_BYTE)
        host.poke(LEAP_BYTE, (b297 or 0) | 1)
        host.flag(LEAP_FLAG, False)
        _gate(guest, CAT_ROWS)
        if ctx.cal == "orphan":
            _lever(guest, ctx, "orphan", "old", word_lever=True)
        st = cb.poll(host, lambda s: (cb.raw(s).get("flags") or {}).get(str(LEAP_FLAG)) is False
                     and (duo_mod.watched_byte(s, LEAP_BYTE) or 0) & 1, 3.0, "the host's leap gate")
        if st is None:
            host.flag(LEAP_FLAG, False)                  # 350's Code2_Loop sets 2075 when it offers the Cat's Eye: re-poke
        _gate(host, CAT_ROWS)
        want = (1, CAT_ROWS & 0xFF, (CAT_ROWS >> 8) & 0xFF)
        cb.poll(guest, lambda s: _gate_reads(s) == want, 3.0, "the guest's gate bytes")
        cb.poll(host, lambda s: _gate_reads(s) == want, 3.0, "the host's gate bytes")
        ah, ag = len(d.lines("host")), len(d.lines("guest"))
        w = _Watch(d)
        w.hooks.append(_HostPager(host, PAGE_S))
        last = {"listed": False, "closed": False}

        def track(role: str, x: dict) -> None:              # O(1) per sample: the guest's 117 listed, then gone
            if role != "guest" or last["closed"]:
                return
            if so.win_of(x, CAT_LAST) is not None:
                last["listed"] = True
            elif last["listed"]:
                last["closed"] = True
        w.hooks.append(track)
        host.press("select", 2)
        if cb.poll(host, lambda x: x.choice is not None, 5.0, "the host's ATE menu") is None:
            raise HarnessError("the host's Cat's Eye menu never opened on 350 (the gate bytes?)")
        host.choose_landed(CAT_PICK)
        w.until(lambda w: last["closed"] or (_fid(w.last("guest")) == REST_FROM and so.win_of(w.last("guest"), CAT_ELSE) is not None),
                CAT_S)
        w.hold(1.5)
        on351 = [x for x in w.s["guest"] if _fid(x) == REST_FROM]
        ev = {"gs": w.s["guest"], "hs": w.s["host"], "gl": _msgs(d, "guest", ag), "hl": _msgs(d, "host", ah),
              "closes0": ival(so.nget(on351[0], "orphan_closes")) if on351 else None,
              "closes1": ival(so.nget(on351[-1], "orphan_closes")) if on351 else None,
              "holds0": ival(so.sget(on351[0], "orphan.holds")) if on351 else None,
              "holds1": ival(so.sget(on351[-1], "orphan.holds")) if on351 else None}
    finally:
        guest.speedmode(False)
        if ctx.cal == "orphan":
            _ns(guest, "swap", "orphan", "act")
    ctx.marks["DB-HOLD"] = ctx.marks["DB-ORDER"] = {"gl": ev["gl"], "holds0": ev["holds0"], "holds1": ev["holds1"]}
    record(led, ctx, "DB-SHAPE", judge_db_shape(ev))
    record(led, ctx, "DB-BIT", judge_db_bit(ev, ctx.clock_ok, ctx.clock_why))
    record(led, ctx, "DB-HOLD", judge_db_hold(ev))
    record(led, ctx, "DB-ORDER", judge_db_order(ev))


def _settle_both(d, field: int, timeout: float = SEAT_S) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _settled(d, field):
            return True
        if d.host.state.dialog_open:
            d.host.press("confirm", 2)
        time.sleep(0.2)
    return False


# ---- OWN
def _leg_own(d, ctx: Ctx, led: cb.Ledger) -> None:
    host, guest = d.host, d.guest
    _seat(d, HOME)
    for g in (host, guest):
        g.watch(*(b * 8 + i for b in GATE_BYTES for i in range(8)))
    host.poke(GATE_BYTES[0], 1)                          # the instrument: 351's load must wipe it (s163's recipe)
    cb.poll(host, lambda s: _gate_reads(s)[0] == 1, 3.0, "the host's 238 poked before the warp")
    host.warp(OWN_HUB, entrance=0, scenario=DESK_SCENARIO)
    if not _settle_both(d, OWN_HUB):
        raise HarnessError("the pair never settled on 351")
    _gate(guest, OWN_ROWS)
    _gate(host, OWN_ROWS)
    want = (1, OWN_ROWS & 0xFF, (OWN_ROWS >> 8) & 0xFF)
    cb.poll(guest, lambda s: _gate_reads(s) == want, 3.0, "the guest's gate bytes")
    cb.poll(host, lambda s: _gate_reads(s) == want, 3.0, "the host's gate bytes")
    ag = len(d.lines("guest"))
    w = _Watch(d)
    w.hooks.append(_HostPager(host, PAGE_S))
    host.press("select", 2)
    if cb.poll(host, lambda x: x.choice is not None, 5.0, "the host's ATE menu") is None:
        raise HarnessError("the host's ATE menu never opened on 351 (the gate bytes?)")
    host.choose_landed(OWN_PICK)
    w.until(lambda w: _fid(w.last("guest")) == OWN_DEST, 60.0)
    w.hold(2.0)
    gi = land_idx(w.s["guest"], OWN_DEST)
    ev = {"g": rec_block(w.s["guest"], gi), "gl": _msgs(d, "guest", ag)}
    record(led, ctx, "DC-OWN", judge_dc_own(ev))
    w.until(lambda w: _fid(w.last("guest")) == OWN_HUB and _fid(w.last("host")) == OWN_HUB, OWN_S)   # the ATE plays out, both home


# ---- MENU
def _menu_run(d, ctx: Ctx, hold_s: float, *, short: bool) -> dict:
    host, guest = d.host, d.guest
    _seat(d, HOME)
    act_fade = FADE_WORDS.get(ctx.cal, "act")
    _lever(guest, ctx, "fade", act_fade, word_lever=act_fade != "act")
    host.flag(P_FLAG, False)
    for g in (host, guest):
        g.watch(P_FLAG)
    pin_old = short and ctx.cal == "pin"
    life_old = short and ctx.cal == "life"
    if pin_old:
        _lever(guest, ctx, "pin", "old", word_lever=True)
    if life_old:
        _lever(host, ctx, "life", "old", word_lever=True)
    try:
        guest.open_menu()
        ag = len(d.lines("guest"))
        w = _Watch(d)
        w.pump()
        e0 = ival(so.sget(w.last("host"), "intent.emit_t"))
        state = {"emit_wall": None, "marked": False, "pressed": 0.0}

        def step(role: str, x: dict) -> None:
            e = ival(so.sget(x, "intent.emit_t"))
            if role == "host" and state["emit_wall"] is None and e is not None and e >= 0 and e != e0:
                n = so.now_ms(x)
                state["emit_wall"] = time.time() - ((n - e) / 1000.0 if n is not None else 0.0)
            if role == "host" and not state["marked"] and _fid(x) == AWAY:
                state["marked"] = True
                host.flag(P_FLAG, True)                    # the host marks 8720 once it has landed (after the pin's frames)
            if (role == "guest" and state["emit_wall"] is not None and time.time() >= state["emit_wall"] + hold_s
                    and x.get("ui_state") == "MainMenu" and time.time() - state["pressed"] >= 0.6):
                state["pressed"] = time.time()             # one cancel at a time: the watch keeps sampling (menu_close_t reads it)
                guest.press("cancel", 6)
        w.hooks.append(step)
        host.send(f"warp {AWAY} -1 -1", wait=False)
        w.until(lambda w: _fid(w.last("guest")) == AWAY and w.last("guest").get("ui_state") != "MainMenu" and state["pressed"] > 0,
                FOLLOW_S + hold_s + 5.0)
        w.hold(1.0)
        gi = land_idx(w.s["guest"], AWAY)
        on = [x for x in w.s["guest"][gi or 0:] if _fid(x) == AWAY]
        ev = {"g": rec_block(w.s["guest"], gi), "menu_close_t": menu_close_t(w.s["guest"]),
              "flag": (cb.raw(on[-1]).get("flags") or {}).get(str(P_FLAG)) if on else None, "gl": _msgs(d, "guest", ag)}
        tr = tr_evidence("MENU", f"MENU{hold_s}", AWAY, HOME, w.s["host"], w.s["guest"])
        ctx.all_trs.append(tr)
        return ev
    finally:
        if pin_old:
            _ns(guest, "swap", "pin", "act")
        if life_old:
            _ns(host, "swap", "life", "act")
        _ns(guest, "swap", "fade", "act")
        host.flag(P_FLAG, False)


def _leg_menu(d, ctx: Ctx, led: cb.Ledger) -> None:
    ev = _menu_run(d, ctx, MENU_SHORT_S, short=True)
    ctx.marks["DL-DEFER"] = {"g": ev["g"]}
    ctx.marks["DP-DEFER"] = {"g": ev["g"], "flag": ev["flag"]}
    record(led, ctx, "DL-DEFER", judge_dl_defer(ev, ctx.fms))
    record(led, ctx, "DP-DEFER", judge_dp_defer(ev, life_word=ctx.cal == "life"))
    ev2 = _menu_run(d, ctx, MENU_AGED_S, short=False)
    record(led, ctx, "DP-AGED", judge_dp_aged(ev2))


# ---- MARK
def _leg_mark(d, ctx: Ctx, led: cb.Ledger) -> None:
    host, guest = d.host, d.guest
    _seat(d, HOME)
    host.flag(P_FLAG, False)
    for g in (host, guest):
        g.watch(P_FLAG)
    _lever(guest, ctx, "fade", "long")                   # the leg's own lever: it widens the window
    if ctx.cal == "pin":
        _lever(guest, ctx, "pin", "old", word_lever=True)
    try:
        ag = len(d.lines("guest"))
        w = _Watch(d)
        state = {"marked": False}

        def mark(role: str, x: dict) -> None:
            if role == "host" and not state["marked"] and _fid(x) == AWAY and (
                    (ival(so.sget(x, "intent.body_ms")) or -1) >= 0 or _ctl(x)):
                state["marked"] = True
                host.flag(P_FLAG, True)                    # once the host's body stands on D
        w.hooks.append(mark)
        w.pump()
        host.send(f"warp {AWAY} -1 -1", wait=False)
        w.until(lambda w: _fid(w.last("guest")) == AWAY and _closed(w.last("guest")), FOLLOW_S + 12.0)
        gi = land_idx(w.s["guest"], AWAY)
        g = rec_block(w.s["guest"], gi)
        on = [x for x in w.s["guest"][gi or 0:] if _fid(x) == AWAY]
        hf = next((so.now_ms(x) for x in w.s["host"] if (cb.raw(x).get("flags") or {}).get(str(P_FLAG)) is True), None)
        ev = {"g": g, "flag": (cb.raw(on[-1]).get("flags") or {}).get(str(P_FLAG)) if on else None, "host_flag_t": hf,
              "gl": _msgs(d, "guest", ag), "dest": AWAY}
        ctx.all_trs.append(tr_evidence("MARK", "MARK", AWAY, HOME, w.s["host"], w.s["guest"]))
    finally:
        _ns(guest, "swap", "fade", "act")
        if ctx.cal == "pin":
            _ns(guest, "swap", "pin", "act")
        host.flag(P_FLAG, False)
    ctx.marks["DP-MARK"] = {"g": ev["g"], "flag": ev["flag"]}
    record(led, ctx, "DP-MARK", judge_dp_mark(ev, ctx.clock_ok, ctx.clock_why))


# ---- LEFT
def _leg_left(d, ctx: Ctx, led: cb.Ledger) -> None:
    host, guest = d.host, d.guest
    _seat(d, HOME)
    ah = len(d.lines("host"))
    w = _Watch(d)
    w.pump()
    host.send(f"warp {AWAY} -1 -1", wait=False)
    if not w.until(lambda w: _fid(w.last("host")) == AWAY and _ctl(w.last("host")), ARRIVE_S):
        raise HarnessError("the host never landed on 30602")
    w.hold(LEFT_BATTLE_S)
    try:
        host.start_battle(BATTLE_SCENE)
    finally:
        hs = host.state
        gs = guest.state
    h = dict(so.swb(hs) or {})
    ev = {"h": h, "g": dict(so.swb(gs) or {}), "hl": _msgs(d, "host", ah), "dest": AWAY,
          "start_t": _t(h, "intent.end_t") if _path(h, "intent.last_end") == "left" else next(
              (so.now_ms(x) for x in w.s["host"] if cb.raw(x).get("scene") not in (None, "FieldMap")), None)}
    record(led, ctx, "DL-LEFT", judge_dl_left(ev, ctx.clock_ok, ctx.clock_why))
    try:
        host.flee()
    except HarnessError as err:
        d.note(f"LEFT: the host's flee failed ({str(err)[:160]})")


# ---- OPEN
def _leg_open(d, ctx: Ctx, led: cb.Ledger) -> None:
    host, guest = d.host, d.guest
    _seat(d, AWAY)
    act_fade = FADE_WORDS.get(ctx.cal, "act")
    _lever(guest, ctx, "fade", act_fade, word_lever=act_fade != "act")
    try:
        host.walk_to(*OPEN_STAND, tolerance=45, strict=False)
        host.interact(timeout=6.0)
        if cb.poll(guest, lambda s: any(w.get("cls") == "locked" for w in so.windows(s)), 6.0, "the relayed line, locked") is None:
            raise HarnessError("the host's NPC line never opened locked on the guest")
        w = _Watch(d)
        w.pump()
        refused = None
        try:
            host.send(f"warp {HOME} -1 -1")
        except HarnessError as err:
            refused = str(err)
        if refused is None:
            w.until(lambda w: _fid(w.last("guest")) == HOME, FOLLOW_S)
            w.hold(0.5)
        ev = {"refused": refused, "fade": _path(so.swb(guest.state), "fade.last") or {}}
    finally:
        _ns(guest, "swap", "fade", "act")
        for _ in range(6):
            if not host.state.dialog_open:
                break
            host.press("confirm", 2)
            host.wait_frames(15)
    ctx.marks["DF-OPEN"] = {"fades": [{"fade": ev["fade"]}]}
    record(led, ctx, "DF-OPEN", judge_df_open(ev))


# ---- LEVERS
def _leg_levers(d, ctx: Ctx, led: cb.Ledger) -> None:
    host, guest = d.host, d.guest
    res = {"guest_life": so._try_full(guest, "swap", "life", "old"), "host_orphan": so._try_full(host, "swap", "orphan", "old"),
           "host_hostctl": so._try_full(host, "swap", "hostctl", "off"), "guest_hostctl": so._try_full(guest, "swap", "hostctl", "off")}
    record(led, ctx, "LVD-ROLE", judge_lvd_role(res))
    acked = so._try_full(host, "swap", "life", "old") == ""
    st = cb.poll(host, lambda s: so.sget(s, "levers.life") == "old", 3.0, "the host's life lever") or host.state
    lv_set = so.sget(st, "levers")
    cb.release(host)                                     # the host's `reset`: HarnessReleaseBench -> NetSyncSwap.HarnessRelease
    st2 = cb.poll(host, lambda s: so.sget(s, "levers.life", "?") in (None, "act"), 5.0, "the release") or host.state
    record(led, ctx, "LVD-LIFE", judge_lvd_life(acked, lv_set, so.sget(st2, "levers")))


def main(argv=None) -> int:
    """`deploy`: the ARRIVE field's one-time deploy with its explicit id (the operator's step; relaunch afterwards)."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] != ["deploy"]:
        print(__doc__)
        print(f"usage: py {Path(__file__).name} deploy    -- {deploy_command()}")
        return 2
    print("running: " + " ".join(deploy_argv()))
    return subprocess.call(deploy_argv(), cwd=str(REPO))


if __name__ == "__main__":
    raise SystemExit(main())
