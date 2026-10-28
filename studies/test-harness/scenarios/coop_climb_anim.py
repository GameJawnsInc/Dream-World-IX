"""s157 -- THE CLIMB ANIMATION, the SOLO bench (studies/field-coop/GUEST-TRAVERSAL-TWO-PC.md Findings 1 + 2;
memoria-patches/s157-netsync-climb-anim.patch). [ff9mapkit netsync s157]

THE DEFECTS. Finding 1 -- a stopped climber's GHOST keeps climbing: the s156 ghost free-runs every clip at speed 1, so a
guest hanging on a ladder shows the host a ghost that climbs on. Finding 2 -- a DRESSED guest body (self-dress) plays
s140's idle ALIAS for every Zidane ladder / jump clip: Steiner slides up the rungs in an idle pose.

THE FIX (s157). (1) THE TWIN ROWS: MapAnim maps a Zidane ladder / jump clip to the worn rig's own same-suffix clip from a
closed 55-row table (battlewire.TWIN_ROWS), behind a clip-present guard; the lever `netsync selfdress twin on|off|miss`
(selftest role) and the per-load keys under `netsync.dress.self` (twins, twin_misses, twin_last, twin ...). (2) THE GHOST
FRAME: the 30 Hz type-0 lane carries [animFrame][frameN] (37 -> 39 B, no wire bump) and DriveGhost frame-follows (speed 0,
eased, wrap-aware) when the wire clip -- or its twin -- is what the ghost plays and the loco is Other; the lever `netsync
bench ghostframe on|off`, the witness `netsync.ghostframe`. On the SELFTEST MIRROR the wire frame is the body's OWN
(me.animFrame / frameN, read locally): this bench proves the SAMPLING; coop_climb_anim_peer.py proves the wire.

THE BENCH. One instance root, the selftest role, `netsync bench 0` (no spectator gate: every climb is the stock one on my
own copy -- the twins and the frame need none). The instance ini's [Netsync] GhostAs is set to "" BEFORE `selftest 1` (an
ini edit mid-run beats the forced role), so the +250 x mirror wears my wire body RAW on every field (under `auto` the
undressed mirror is the moogle and reads why "clip"). Fields 114 (UNDRESSED: the field's own Vivi) -> 207 (DRESSED as
Steiner: the ladder) -> 408 (DRESSED: the jumps). Every leg takes b0 = the raw publish before its press and b1 after; the twin
counters are PER FIELD LOAD (b0 is always taken after the load). A ghost judge reads only publishes after a 1 s settle.

  K0         provenance; refuses --attach and no --instance; GhostAs "" into the root's ini (backed up into the run dir);
             newgame; Byte[13]/[14] zeroed; warp 114 entrance 0 (THE ENV-SLOT LAW: never -1); noencounter; `selftest 1`;
             `bench 0`; the forced role; 114's post-init witness; |SelfTestOffset| < 640; the engine is the one the title
             read said (s157 iff `netsync.ghostframe.follow` AND `netsync.dress.self.twins` are published).
  K1         (s157) the proof block: 'guest traversal selftest: OK (...)' with rows / funcs / crc == the kit's JSON, then
             'dress twin selftest: OK (N rows)', then 'ghost frame selftest: OK (R rows, M mutants caught)' -- its LAST line.
  K2         (s157) ghostframe.selftest "ok", lever_off false; dress.self.twin "on", twin_selftest "ok", twin_rows 55
             (BW.TWIN_ROW_COUNT), twin_clips_on_disc 37 (BW.TWIN_CLIP_COUNT), twin_clip_missing -1; dress.ghost.mode "ini:".
  U114-UP    the stock climb up as the field's own Vivi (model 8), with a HANG (hold up until 40 u past the mount, release,
             2.5 s with no key): judge_undressed -- model 8, never armed, the body's own GEO clip, twins / twin_misses +0.
  GF114-HOLD (s157) THE FINDING-1 VERDICT on U114-UP's hang: the mirror ghost holds the body's frame (follow, speed 0, shown
             == wire_frame == the body's, time constant at shown / frame_n x length; wire_tol 0: the mirror reads it locally).
  GF114-TRACK (s157) U114-UP's climb after the hang: the ghost is DRIVEN (>= 90 % follow at speed 0, median lag <= 2.5
             frames, >= 3 body frames, steps +1, wraps +1 or more).
  U114-DN / GF114-TRACK-DN   the climb down: judge_undressed, and judge_track (wraps +1 or more).
  GF114-CAL  (s157) THE IN-RUN LEVER RED: a climb up, at the hang (no key held) `bench ghostframe off` (the documented
             exception to "levers at rest": it moves no climb state) -> after 0.3 s, 1.5 s of publishes carry the s156
             signature (frame_red_marker: follow false, why "lever", lever_off, speed 1, time advancing while the body holds);
             `bench ghostframe on` -> after 1 s the hold is back (judge_hold) and ghostframe.snaps moved by exactly +1 (the
             re-entry SNAP); then the climb out.
  K3D        at EVERY dressed arrival (207, 408 and each re-warp): dress.self.armed true, rig 3 (Steiner), player.model 5489,
             player.anim_geo == player.geo == GEO_MAIN_F0_STN, dress.ghost.model 5489 (all read off battlewire's rig row).
  TW207-UP   dressed as Steiner, the climb up WITH a hang: judge_twin over the mid-ladder publishes -- >= 80 % on one of rig
             3's TWIN ids (BW.TWIN_BY_KEY) with the worn GEO's clip, NONE on the idle / idle alias (2001 / 2002), twins +3 or
             more, twin_misses +0, twin_last a twin, the mirror on the body's clip (>= 80 %) and frame-following it (>= 80 %).
             A STILL mid-climb during the hang (a NOTE, never a check): tools/game_snap.ps1 -> <run>/shots/s207-mid-window.png
             and the engine's own `shot s207-mid` -- READ them: Steiner grips the rungs, the +250 x mirror holds his pose.
  GF207-HOLD / GF207-TRACK   (s157) as 114's, on TW207-UP's hang and climb (wraps not required: the 207 ladder is short).
  TW207-DN   the climb down: judge_twin.
  TW207-CAL-OFF  (s157) `selfdress twin off` at rest, THEN the load (re-warp 207), the climb up: twin_red_marker(mode
             "off") GREEN -- the alias on >= 80 %, twin "off" on every publish, twins +0, twin_misses +0 -- and judge_twin RED.
  TW207-CAL-MISS (s157) `selfdress twin miss`, re-warp, the climb down: twin_red_marker(mode "miss") GREEN (the clip-present
             guard fell back: twin_misses +1 or more) and judge_twin RED. Then `twin on` (the next load reads it).
  TW408 / TW408-RET   the e4 hop out (ledge -> shelf) and the e5 hop back, dressed: judge_twin over the mid-air publishes
             (>= 2; the mirror's clip not judged). A STILL mid-arc on a THIRD, unjudged hop out after TW408-RET (the
             synchronous shot stalls the watch: the s156 calibration's still-bearing TW408 kept one mid-air sample): the
             engine's `shot s408-arc` fired from the watch once the body has covered 35-75 % of the ledge -> landing x/z
             with control off (MID-FLIGHT, not a clock: a 0.45 s clock fired before take-off), and tools/game_snap.ps1
             started IN THE BACKGROUND at the press
             (-> s408-arc-window.png; when it finished vs the landing is noted -- a window capture takes ~1 s to start).
  TW408-CAL-OFF  (s157) `twin off`, re-warp 408, the hop out: twin_red_marker(mode "off") GREEN and judge_twin RED; `twin on`.
  K-TRIPS    netsync.guestlocal trips.total moved by 0 from K2 (s156: K0) to the last leg (no false trips).
  K-R        `reset`. s157: both levers are HELD INTO it (the run's calibration lever, else `twin miss` / `bench ghostframe
             off` pulled at rest just before -- so each half can fail): 'ghost frame-follow back ON (released with the
             harness)' exactly once, the self-dress release line ('selfdress self / gate / law ... levers released') exactly
             once (the `self steiner` lever and the twin lever), the role released; re-read WITH the role (cb.reread_with_role:
             the levers' getters read their rest values without it): twin "on", lever_off false. s156: the role released and
             the self-dress release line once iff `self steiner` was taken; no ghost-frame line.
  then       the root's ini restored (Instance.restore_ini: install + overlay), Memoria.log archived into the run dir, and
             THE GAME QUIT (Session.quit; never an --attach'd game -- K0 refuses those): this bench never leaves FF9 running.

THE ORDERING LAWS (coop_guest_traversal's, kept): a direction is held only after a SEEN mount (the hang helper is
ladder_run's on_mount) and released in try/finally; levers toggle at rest (GF114-CAL's mid-hang toggle is the one
exception); a lever that acts at a load is set, THEN the field is loaded (`twin`); each leg's start pose is the previous
leg's landing or a bench-0 stock repositioning climb / hop (a NOTE); 408 / 207 are entered with entrance 0 and the env-sound
slots zeroed (THE ENV-SLOT LAW); 207 under ScenarioCounter 2030 / 2225 is entered with scenario 2000 (e10 / e11 unarmed).
Never gt.arrive (its undress sends `selfdress self off`).

THE CALIBRATION. A check that cannot fail is not a check.
  * The s156 DLL calibrates AUTOMATICALLY (no `netsync.ghostframe` / `netsync.dress.self.twins`): K1, K2, every GF* row and
    every *-CAL row are DROPPED as N/A (s157 surfaces not present: never scored); `bench ghostframe` is NEVER sent (an s156
    agent reads it as `bench 1`) nor `selfdress twin`. PREDICTED_S156 = TW207-UP, TW207-DN, TW408, TW408-RET red, each with
    twin_red_marker(mode "s156") (the alias on >= 80 %, no twin key). U114-* stay green (a None delta counts as unmoved).
  * COOP_CALIBRATE=twin (s157): `selfdress twin off` pulled after K2 and HELD for the run; the TW*-CAL rows are dropped (they
    would release it). PREDICTED_TWIN = the same four TW rows red with twin_red_marker(mode "off"); GF* stay green (the
    mirror frame-follows the raw alias clip: 2002 is not rig 3's idle, so its loco is Other).
  * COOP_CALIBRATE=frame (s157): `bench ghostframe off` pulled after K2 and HELD; GF114-CAL is dropped (it would release it).
    PREDICTED_FRAME = GF114-HOLD, GF114-TRACK, GF114-TRACK-DN, GF207-HOLD, GF207-TRACK red -- a HOLD row with
    frame_red_marker(why "lever", lever_off), a TRACK row with judge_freerun_guard(why "lever") and lever_off on every
    publish. TW* stay green: under this lever their frame-follow share is GF*'s business, not judged there.
  K-CAL-M (judged before K-CAL) is green only when every predicted red carries its marker; K-CAL is green only when exactly
  the predicted set is red. The raw os.environ["COOP_CALIBRATE"] is read (cb.CALIBRATE is truthy-only): "" / "0" = plain,
  "twin", "frame"; anything else is refused at K0.

THE PREREQS: the owner's go and a RELAUNCH after `py tools/build_memoria.py --label pre-s157-climb-anim` (the s156 run below
goes first, on the live s156 DLL); `py tools/harness/instance.py ensure C:\\gd\\ff9-inst\\host`; no other FF9 from that
root, no controller, nobody at the keyboard (presses are injected in-engine), outside 04:00-06:15 (the nightly gate);
SelfTestOffset under 640 (the default 250,0). No custom field registration, no deploy. Windowed / borderless for the
game_snap stills. Never --attach or --keep-open.

    py tools/play.py studies/test-harness/scenarios/coop_climb_anim.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=twin py tools/play.py studies/test-harness/scenarios/coop_climb_anim.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=frame py tools/play.py studies/test-harness/scenarios/coop_climb_anim.py --instance C:\\gd\\ff9-inst\\host

EXPECTED (tally(mode)): on the live s156 DLL, BEFORE the deploy, the plain command reads 8/12 with K-CAL-M and K-CAL green;
on s157 the plain run reads 21/21, COOP_CALIBRATE=twin 16/20 and COOP_CALIBRATE=frame 17/22 (K-CAL-M + K-CAL green). Then
the wire half (coop_climb_anim_peer.py), the s157 regression set (coop_guest_traversal 28/28 -- its K1 / K2 read the 80-row
table only on s157 --, coop_self_dress, coop_talk_relay, coop_dialogue_authority, coop_diorama_return) and the duo
(coop_follow_race_duo, coop_dress_wire for GhostAnimRule's dressed-ghost twin branch: not reachable solo).

NOT PROVEN HERE: the WIRE (the mirror reads its frame locally -- coop_climb_anim_peer.py and the duo prove the 39-B lane);
GhostAnimRule's twin branch on a host dressing a plain-Zidane guest (duo only); Blank's / Beatrix's named jumps 977 / 8566
(no twin rows: owner policy open); FEEL -- a frame-followed ghost can read as correct and still look wrong: the stills are
for the owner, and the two-PC session is the verdict.
"""
from __future__ import annotations

import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _climb_anim_judges as J                             # noqa: E402 - the s157 pure judges
import coop_guest_traversal as gt                          # noqa: E402 - s156's climb / hop drivers, geometry, recover

try:                                                       # play.py puts THIS worktree's tools/ first on sys.path
    from harness import battlewire as BW                   # noqa: E402
    from harness import fakegame as FG                     # noqa: E402 - the engine's log texts, as the stand-in pins them
except ImportError:                                        # pragma: no cover - imported outside the driver
    sys.path.insert(0, str(cb.REPO / "tools"))
    from harness import battlewire as BW                   # noqa: E402
    from harness import fakegame as FG                     # noqa: E402

HarnessError = cb.HarnessError

# ---- the keys -------------------------------------------------------------------------------------------------------
GF_KEY = J.GF                            # "netsync.ghostframe"
SELF_KEY = J.SELF                        # "netsync.dress.self"
GF_PROBE = GF_KEY + ".follow"            # key PRESENCE is the capability (protocol 5, additive)
TWIN_PROBE = SELF_KEY + ".twins"
TWINS_KEY, MISSES_KEY = SELF_KEY + ".twins", SELF_KEY + ".twin_misses"
CAL_ENV = "COOP_CALIBRATE"

# ---- the body the bench dresses as (every value read off battlewire's rig row: never a literal) ----------------------
DRESS_NAME = "steiner"
RIG = BW.NAME_TO_RIG[DRESS_NAME]
RIG_ROW = BW.rig_row(RIG)
DRESS_MODEL = RIG_ROW["model"]
DRESS_GEO = BW.rig_geo(RIG)
TWIN_IDS = frozenset(v for (r, _src), v in BW.TWIN_BY_KEY.items() if r == RIG)
ALIAS_IDS = frozenset((RIG_ROW["idle"], RIG_ROW["idle_alias"]))
GHOST_AS = ""                            # the mirror wears my wire body RAW (auto: the undressed mirror is the moogle)
INI_UPDATES = {"GhostAs": GHOST_AS}

# ---- the engine's lines ---------------------------------------------------------------------------------------------
TWIN_OK_RX = re.compile(re.escape(BW.PROOF_DRESS_TWIN) + r"OK \((\d+) rows\)")
GF_OK_RX = re.compile(FG.GHOSTFRAME_PROOF_RE)
#: the self-dress release line's head, s140's and s141's texts alike (NetSyncSelfDress.ReleaseBench; s157 kept it byte-identical)
DRESS_RELEASE = "[NetSync] harness: " + os.path.commonprefix([BW.SELF_RELEASE_LINE, BW.SELF_RELEASE_LINE_S140]).rstrip()

# ---- timing (seconds of wall clock; the agent publishes every 2 frames) ---------------------------------------------
HANG_PAST_U = 40.0                       # the hang starts this far past the mount (inside the loop: a mid-ladder pose)
HANG_MOVE_S = 0.4                        # the 40 u hold's cap
HANG_HOLD_FRAMES = 600                   # its frame cap (the try/finally release ends it sooner)
HANG_S = 2.5                             # the hang: no key held
SETTLE_S = 1.0                           # a ghost judge reads only publishes this long after the last change (ease ~0.7 s)
CAL_OFF_WAIT_S = 0.3
CAL_OFF_S = 1.5
CAL_ON_S = 2.5
SELFTEST_S = 20.0
DRESS_S = 6.0                            # K3D's poll after a dressed arrival (the arm lands at the load, the ghost after)
ARRIVE_S = 15.0
ARC_SHOT = (0.35, 0.75)                  # the 408 still: control off, this share of the ledge -> landing x/z covered
GRAB_TIMEOUT_S = 45.0
TWIN_MIN_207 = 3                         # TW207-UP: the mount, the loop and the exit each map (twins +3 or more)
SHARE = 0.8
LEDGER_WIDTH = 2400

# ---- the catalog ----------------------------------------------------------------------------------------------------
CLAIMS = {
    "K0": "the setup: a fresh process from an instance root (no --attach), GhostAs '' into the ROOT's ini before `selftest "
          "1`, newgame, warp 114 entrance 0 (env slots zeroed), noencounter, the forced selftest role, `bench 0`, 114's "
          "post-init witness, |SelfTestOffset| < 640, and the engine the title read said (s157 iff netsync.ghostframe.follow "
          "and netsync.dress.self.twins)",
    "K1": "the proof block: 'guest traversal selftest: OK' with the kit JSON's rows / funcs / crc, then 'dress twin selftest: "
          "OK (N rows)', then 'ghost frame selftest: OK (R rows, M mutants caught)' as its LAST line",
    "K2": "the s157 keys before any lever: ghostframe.selftest 'ok' + lever_off false; dress.self twin 'on', twin_selftest "
          "'ok', twin_rows == BW.TWIN_ROW_COUNT, twin_clips_on_disc == BW.TWIN_CLIP_COUNT, twin_clip_missing -1; "
          "dress.ghost.mode 'ini:' (the GhostAs edit read)",
    "U114-UP": "UNDRESSED 114 (Vivi, model 8), the stock climb up with a hang: the climb lands, and judge_undressed (model 8, "
               "never armed, the body's own GEO clip, twins / twin_misses +0)",
    "GF114-HOLD": "FINDING 1 on 114: through the hang the mirror ghost HOLDS the body's frame (judge_hold, wire_tol 0)",
    "GF114-TRACK": "114 up after the hang: the ghost is driven, not free-running (judge_track, wraps +1 or more)",
    "U114-DN": "UNDRESSED 114, the stock climb down: the climb lands, judge_undressed",
    "GF114-TRACK-DN": "114 down: the ghost is driven (judge_track, wraps +1 or more)",
    "GF114-CAL": "the in-run lever red: mid-hang `bench ghostframe off` -> the s156 signature (frame_red_marker why 'lever'); "
                 "`on` -> the hold back (judge_hold) and snaps +1 exactly; the climb lands",
    "K3D": "DRESSED at every 207 / 408 arrival: armed true, rig == Steiner's, player.model == the rig's model, anim_geo == geo "
           "== the rig's GEO, dress.ghost.model == the rig's model",
    "TW207-UP": "FINDING 2 on 207 (Steiner), the climb up with a hang: the climb lands; judge_twin (a twin id with the worn "
                "GEO, never the alias / idle, twins +3 or more, twin_misses +0, twin_last a twin, the mirror on the body's "
                "clip and frame-following it)",
    "GF207-HOLD": "FINDING 1 dressed: through TW207-UP's hang the mirror holds the body's frame (judge_hold)",
    "GF207-TRACK": "207 up after the hang: the ghost is driven (judge_track)",
    "TW207-DN": "207 (Steiner), the climb down: the climb lands; judge_twin",
    "TW207-CAL-OFF": "`selfdress twin off`, re-warp, the climb up: twin_red_marker(off) GREEN and judge_twin RED",
    "TW207-CAL-MISS": "`selfdress twin miss`, re-warp, the climb down: twin_red_marker(miss) GREEN (twin_misses +1 or more) "
                      "and judge_twin RED",
    "TW408": "408 (Steiner), the e4 hop out: the hop lands; judge_twin over the mid-air publishes (>= 2)",
    "TW408-RET": "408 (Steiner), the e5 hop back: the hop lands; judge_twin over the mid-air publishes (>= 2)",
    "TW408-CAL-OFF": "`twin off`, re-warp 408, the hop out: twin_red_marker(off) GREEN and judge_twin RED",
    "K-TRIPS": "netsync.guestlocal trips.total moved by 0 from K2 (s156: K0) to the last leg",
    "K-R": "`reset` with the levers held into it: the ghost-frame release line once (s157), the self-dress release line once "
           "(when a self-dress lever was set), the role released; re-read with the role (s157): twin 'on', lever_off false",
}
GF_ROWS = ("GF114-HOLD", "GF114-TRACK", "GF114-TRACK-DN", "GF207-HOLD", "GF207-TRACK")
CAL_ROWS = ("GF114-CAL", "TW207-CAL-OFF", "TW207-CAL-MISS", "TW408-CAL-OFF")
TW_ROWS = ("TW207-UP", "TW207-DN", "TW408", "TW408-RET")
#: the rows each mode cannot discriminate: dropped from its catalog, never scored
NA = {"s156": ("K1", "K2") + GF_ROWS + CAL_ROWS,
      "twin": ("TW207-CAL-OFF", "TW207-CAL-MISS", "TW408-CAL-OFF"),
      "frame": ("GF114-CAL",),
      "plain": (), "bad": ()}
NA_NO_GUESTLOCAL = ("K-TRIPS",)           # an engine before s156 publishes no netsync.guestlocal
PREDICTED = {"s156": TW_ROWS, "twin": TW_ROWS, "frame": GF_ROWS}
MARKERS = {"s156": "twin_red_marker(mode 's156'): the alias on >= 80 % of the mid publishes, no twin key",
           "twin": "twin_red_marker(mode 'off'): the alias on >= 80 %, twin 'off' throughout, twins +0, twin_misses +0",
           "frame": "a HOLD row: frame_red_marker(why 'lever', lever_off) over the hang; a TRACK row: judge_freerun_guard(why "
                    "'lever') with lever_off on every publish"}
FINALS = ("K3D", "K-TRIPS", "K-R", "K-CAL-M", "K-CAL")


def is_s157(x) -> bool:
    """The s157 engine: BOTH halves' keys published (the ghost frame's block and the twin rows' per-load counter)."""
    return cb.has(x, GF_PROBE) and cb.has(x, TWIN_PROBE)


def mode_of(cal: str, s157: bool) -> str:
    """'s156' (no s157 keys: the automatic calibration, whatever COOP_CALIBRATE says), 'plain', 'twin', 'frame', or 'bad'
    (a COOP_CALIBRATE value this bench has no lever for: K0 refuses)."""
    if not s157:
        return "s156"
    v = (cal or "").strip().lower()
    if v in ("", "0"):
        return "plain"
    return v if v in ("twin", "frame") else "bad"


def predicted(mode: str) -> tuple:
    return PREDICTED.get(mode, ())


def catalog(mode: str, has_gl: bool = True) -> dict:
    drop = set(NA.get(mode, ())) | (set() if has_gl else set(NA_NO_GUESTLOCAL))
    c = {k: v for k, v in CLAIMS.items() if k not in drop}
    if mode in PREDICTED:
        c["K-CAL-M"] = f"CALIBRATION: every predicted red carries its marker ({MARKERS[mode]}); a red for any other reason is " \
                       f"no calibration"
        c["K-CAL"] = (f"CALIBRATION ({'the s156 DLL, automatic' if mode == 's156' else 'the held ' + mode + ' lever'}): "
                      f"exactly {', '.join(predicted(mode))} red (K-CAL-M green)")
    return c


def tally(mode: str, has_gl: bool = True) -> tuple:
    """(green, total) the run should read on a correct engine of that mode."""
    n = len(catalog(mode, has_gl))
    return n - len(predicted(mode)), n


def calibration_env() -> str:
    return os.environ.get(CAL_ENV, "")


# ================================================================================================ the pure judges
def _last_index(lines, needle: str):
    hits = [i for i, ln in enumerate(lines) if needle in ln]
    return hits[-1] if hits else None


def judge_k1(lines, table) -> tuple:
    """The proof block's three lines, IN ORDER, each OK (the counts are reported, never judged against a literal; the
    guest traversal line's table against the kit's JSON, as coop_guest_traversal's K1)."""
    lines = list(lines or ())
    i_gt = _last_index(lines, gt.GL_SELFTEST_HEAD)
    i_tw = _last_index(lines, "[NetSync] " + BW.PROOF_DRESS_TWIN)
    i_gf = _last_index(lines, "[NetSync] " + FG.PROOF_GHOST_FRAME)
    tw = TWIN_OK_RX.search(lines[i_tw]) if i_tw is not None else None
    gf = GF_OK_RX.search(lines[i_gf]) if i_gf is not None else None
    g_ok, g_why = gt.judge_k1(gt.parse_selftest(lines), table)
    order = None not in (i_gt, i_tw, i_gf) and i_gt < i_tw < i_gf
    parts = [("guest traversal OK on the kit's table", g_ok), ("dress twin OK", tw is not None),
             ("ghost frame OK", gf is not None), ("in that order (ghost frame LAST)", order)]
    detail = (f"twin: {lines[i_tw].split('|')[-1].strip() if i_tw is not None else 'no line'}; ghost frame: "
              f"{lines[i_gf].split('|')[-1].strip() if i_gf is not None else 'no line'}; guest traversal: {g_why}")
    return all(v for _, v in parts), gt._parts(parts) + " -- " + detail


def judge_k2(x) -> tuple:
    got = {"ghostframe.selftest": cb.path(x, GF_KEY + ".selftest"), "ghostframe.lever_off": cb.path(x, GF_KEY + ".lever_off"),
           "self.twin": cb.path(x, SELF_KEY + ".twin"), "self.twin_selftest": cb.path(x, SELF_KEY + ".twin_selftest"),
           "self.twin_rows": cb.path(x, SELF_KEY + ".twin_rows"),
           "self.twin_clips_on_disc": cb.path(x, SELF_KEY + ".twin_clips_on_disc"),
           "self.twin_clip_missing": cb.path(x, SELF_KEY + ".twin_clip_missing"),
           "ghost.mode": cb.path(x, "netsync.dress.ghost.mode")}
    want = {"ghostframe.selftest": "ok", "ghostframe.lever_off": False, "self.twin": BW.TWIN_LEVER_NAMES[BW.TWIN_LEVER_ON],
            "self.twin_selftest": BW.DRESS_TWIN_SELFTEST_OK, "self.twin_rows": BW.TWIN_ROW_COUNT,
            "self.twin_clips_on_disc": BW.TWIN_CLIP_COUNT, "self.twin_clip_missing": -1, "ghost.mode": "ini:" + GHOST_AS}
    bad = {k: (got[k], want[k]) for k in want if got[k] != want[k]}
    return not bad, f"read {got}" + (f"; WRONG (got, want): {bad}" if bad else "")


def judge_dressed(x) -> tuple:
    """K3D's read of one arrival: armed, Steiner's rig, his model on the body and the mirror, his GEO on the body's clip."""
    p = cb.raw(x).get("player") or {}
    got = {"armed": cb.path(x, SELF_KEY + ".armed"), "rig": cb.path(x, SELF_KEY + ".rig"), "model": p.get("model"),
           "geo": p.get("geo"), "anim_geo": p.get("anim_geo"), "ghost.model": cb.path(x, "netsync.dress.ghost.model")}
    want = {"armed": True, "rig": RIG, "model": DRESS_MODEL, "geo": DRESS_GEO, "anim_geo": DRESS_GEO,
            "ghost.model": DRESS_MODEL}
    bad = {k: (got[k], want[k]) for k in want if got[k] != want[k]}
    return not bad, f"{got}" + (f" WRONG (got, want): {bad}" if bad else "")


def judge_twin_leg(mode: str, mid, d_twins, d_misses, *, hop: bool) -> tuple:
    """A TW row's twin half (J.judge_twin): the ladder's mid publishes judged with the mirror on the body's clip and, but
    under the held frame lever, frame-following it; a hop's mid-air publishes with neither (>= 2)."""
    if hop:
        return J.judge_twin(mid, twin_ids=TWIN_IDS, alias_ids=ALIAS_IDS, d_twins=d_twins, d_misses=d_misses, share=SHARE,
                            ghost_share=None, follow_share=None, min_n=2)
    return J.judge_twin(mid, twin_ids=TWIN_IDS, alias_ids=ALIAS_IDS, d_twins=d_twins, d_misses=d_misses, share=SHARE,
                        ghost_share=SHARE, follow_share=None if mode == "frame" else SHARE)


def marker_for(mode: str, row: str, rec) -> tuple:
    """The predicted red's signature for ``row`` under ``mode`` (K-CAL-M)."""
    if not isinstance(rec, dict):
        return False, "the leg never recorded its publishes"
    if mode == "s156":
        return J.twin_red_marker(rec.get("mid") or [], alias_ids=ALIAS_IDS, mode="s156", share=SHARE)
    if mode == "twin":
        return J.twin_red_marker(rec.get("mid") or [], alias_ids=ALIAS_IDS, mode="off", d_twins=rec.get("d_twins"),
                                 d_misses=rec.get("d_misses"), share=SHARE)
    if mode == "frame":
        if row.endswith("-HOLD"):
            return J.frame_red_marker(rec.get("hang") or [], why="lever", lever=True)
        s = rec.get("mid") or []
        ok, why = J.judge_freerun_guard(s, why="lever")
        lever = bool(s) and all(J.get(x, GF_KEY + ".lever_off") is True for x in s)
        return ok and lever, why + f"; lever_off on every publish: {lever}"
    return False, f"no marker for mode {mode!r}"


def judge_markers(mode: str, marks: dict) -> tuple:
    seen = {c: marker_for(mode, c, (marks or {}).get(c)) for c in predicted(mode)}
    return (bool(seen) and all(ok for ok, _ in seen.values()),
            "; ".join(f"{c} SEEN" if ok else f"{c} NOT seen ({why})" for c, (ok, why) in seen.items()))


def judge_release(*, s157: bool, n_gf: int, n_dress: int, want_gf: int, want_dress: int, ns: dict, reread=None,
                  into_ok=True) -> tuple:
    """K-R: the role released, each release line exactly as often as a lever was held into the reset, and (s157) the
    re-read WITH the role at the rest values. ``into_ok`` False = a lever could not be held into it (that half could not
    fail: red)."""
    parts = [("the role released", ns.get("forced") is False and ns.get("bench") is not True),
             (f"the ghost-frame release line x{want_gf}", n_gf == want_gf),
             (f"the self-dress release line x{want_dress}", n_dress == want_dress)]
    if s157:
        parts += [("both levers held into the reset", into_ok is True),
                  ("re-read: twin 'on'", cb.path(reread, SELF_KEY + ".twin") == BW.TWIN_LEVER_NAMES[BW.TWIN_LEVER_ON]),
                  ("re-read: lever_off false", cb.path(reread, GF_KEY + ".lever_off") is False)]
    return all(v for _, v in parts), (gt._parts(parts) + f" -- lines: ghost frame {n_gf}, self-dress {n_dress}; forced "
                                      f"{ns.get('forced')!r} bench {ns.get('bench')!r}; re-read twin "
                                      f"{cb.path(reread, SELF_KEY + '.twin')!r} lever_off "
                                      f"{cb.path(reread, GF_KEY + '.lever_off')!r}")


# ================================================================================================ acting
class Ctx:
    def __init__(self, mode: str, s157: bool, has_gl: bool, cal_raw: str = ""):
        self.mode, self.s157, self.has_gl, self.cal_raw = mode, s157, has_gl, cal_raw
        self.g = gt.Ctx("plain", has_gl)          # coop_guest_traversal's per-leg context (press_rec / ladder_run / pose)
        self.k0_ok = False
        self.ini_edited = False
        self.cal_held = False
        self.self_set = False                      # `selfdress self steiner` taken (the release then logs its line)
        self.trips0 = None
        self.k3d: list = []                        # (label, field, ok, why) per dressed arrival
        self.marks: dict = {}                      # a predicted row -> its publishes (K-CAL-M)
        self.stills: list = []


def _run_dir(g) -> Path:
    return Path(getattr(g, "scenario_dir", None) or g.run_dir)


def _shots_dir(g) -> Path:
    d = _run_dir(g) / "shots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _rec(led: cb.Ledger, cid: str, ok, why) -> None:
    """Record ``cid`` only when this mode's catalog has it (an N/A row is never scored)."""
    if cid in led.catalog:
        led.check(cid, ok, why)


def _mark(ctx: Ctx, row: str, rec: dict) -> None:
    if row in predicted(ctx.mode):
        ctx.marks[row] = rec


def _act(g, ctx: Ctx, led: cb.Ledger, rows, fid: int, fn) -> None:
    """Run one leg (it records ``rows``); a raise records its pending rows 'not reached' and recovers (no key down, no
    window, off any ladder); a bench bug is red and loud and the run goes on."""
    rows = [r for r in rows if r in led.catalog and r not in led.done]
    if not rows:
        return
    try:
        fn(rows)
    except HarnessError as err:
        led.unreached(rows, f"the leg raised: {str(err)[:240]}")
        gt.recover(g, fid)
    except Exception as err:                             # noqa: BLE001 - a BENCH bug: red and loud, the run goes on
        g.note(f"{rows[0]} FAULTED (a bench bug, not a verdict): {err!r}"[:400])
        led.unreached(rows, f"the leg FAULTED (a bench bug): {err!r}"[:300])
        gt.recover(g, fid)
    led.unreached(rows, "the leg recorded nothing")


def _warp(g, fid: int, scenario: int | None = None) -> None:
    """warp(fid, entrance 0) with both env-sound slots zeroed first (THE ENV-SLOT LAW: a debug warp skips the exit's cleanup;
    408 / 207 then raise 'Error Env Play()' and never give control)."""
    try:
        g.poke(13, 0)
        g.poke(14, 0)
    except (HarnessError, AttributeError) as err:
        g.note(f"warp {fid}: the env-slot poke refused ({str(err)[:120]}) -- the field may raise 'Error Env Play()'")
    g.warp(fid, entrance=0, scenario=scenario)


def _lever(g, ctx: Ctx, kind: str, value: str) -> tuple:
    """A lever at rest, read back: kind 'twin' (`selfdress twin on|off|miss`) or 'frame' (`bench ghostframe on|off`). NEVER
    sent to an s156 engine (it reads `bench ghostframe` as `bench 1`; the driver refuses `selfdress twin` there too)."""
    if not ctx.s157:
        return False, "this engine publishes no s157 key: never sent"
    if kind == "twin":
        ok, why = cb.try_ns(g, "selfdress", "twin", value)
        st = cb.poll(g, lambda s: cb.path(s, SELF_KEY + ".twin") == value, 3.0, f"twin {value} read back")
    else:
        ok, why = cb.try_ns(g, "bench", "ghostframe", value)
        st = cb.poll(g, lambda s: cb.path(s, GF_KEY + ".lever_off") is (value == "off"), 3.0, f"ghostframe {value} read back")
    return ok and st is not None, why or ("" if st is not None else f"`{kind} {value}` never read back")


# ---- the hang ------------------------------------------------------------------------------------------------------
def _past(spec: dict, direction: str, s) -> bool:
    """The body HANG_PAST_U past the mount the climb started from, in the .eb frame (y negative up)."""
    p = gt.pos(s)
    if p is None:
        return False
    mount = spec["mount_bottom"] if direction == "up" else spec["mount_top"]
    return p[1] <= mount[1] - HANG_PAST_U if direction == "up" else p[1] >= mount[1] + HANG_PAST_U


def _hold_past(g, spec: dict, direction: str) -> tuple:
    """Hold the climb direction (a mount was SEEN: this runs as ladder_run's on_mount) until the body is HANG_PAST_U past the
    mount, then release -- in try/finally. (samples, moved)."""
    button = spec["buttons"][direction]
    g.hold(button, HANG_HOLD_FRAMES)
    try:
        samples, hit = cb.watch(g, lambda s: _past(spec, direction, s), HANG_MOVE_S)
    finally:
        try:
            g.release(button)
        except HarnessError:
            pass
    return samples, hit is not None


def _settled(samples, after: float = SETTLE_S) -> list:
    """The publishes at least ``after`` seconds into ``samples`` (raw) -- a ghost judge's window."""
    if not samples:
        return []
    t0 = samples[0].read_at
    return [cb.raw(s) for s in samples if s.read_at - t0 >= after]


def hang_on_mount(g_ctx: Ctx, fid: int, direction: str, *, still: str | None = None):
    """ladder_run's on_mount: 40 u past the mount, release, hang HANG_S with no key. res["hang"] = the publishes after the
    1 s settle; res["hang_all"] = every publish from the mount on; res["n_pre"] = the press -> mount publishes (the climb
    after the hang is res["samples"][n_pre:]). ``still``: the stills are taken at the end of the hang (still hanging)."""
    spec = gt.LADDERS[fid]

    def on_mount(gg, res):
        res["n_pre"] = len(res.get("samples") or [])
        moving, moved = _hold_past(gg, spec, direction)
        w = cb.hold_for(gg, HANG_S)
        res["hang_moved"] = moved
        res["hang_all"] = [cb.raw(s) for s in list(moving) + list(w)]
        res["hang"] = _settled(w)
        if still:
            _still_hang(gg, g_ctx, still)
    return on_mount


def _timeline(res: dict) -> list:
    """Every publish of a climb in order: press -> mount, the hang, the climb on."""
    s = list(res.get("samples") or [])
    n = res.get("n_pre")
    return s if n is None else s[:n] + list(res.get("hang_all") or []) + s[n:]


def _after_hang(res: dict) -> list:
    s = list(res.get("samples") or [])
    n = res.get("n_pre")
    return s if n is None else s[n:]


# ---- the stills (SEAMS: the offline test replaces grab_frame / start_grab / finish_grab -- no window there) ----------
def _snap_args(g, path: Path) -> list:
    args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(cb.REPO / "tools" / "game_snap.ps1"),
            "-OutPath", str(path)]
    try:
        pid = getattr(g, "pid", None)
    except Exception:                                    # noqa: BLE001 - a pid probe never kills a still
        pid = None
    return args + (["-Id", str(int(pid))] if pid else [])


def grab_frame(g, path: Path) -> tuple:
    """tools/game_snap.ps1 on THIS session's game (-Id its pid when known), synchronous: (path | None, why)."""
    try:
        out = subprocess.run(_snap_args(g, path), capture_output=True, text=True, timeout=GRAB_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as err:
        return None, f"game_snap failed: {type(err).__name__}: {str(err)[:160]}"
    if out.returncode == 0 and Path(path).is_file():
        return Path(path), "grabbed"
    return None, f"game_snap exit {out.returncode}: {((out.stderr or '') + (out.stdout or ''))[-200:]}"


def start_grab(g, path: Path) -> dict:
    """tools/game_snap.ps1 started IN THE BACKGROUND (a hop is over before a synchronous one would capture)."""
    h = {"path": Path(path), "t0": time.time(), "proc": None, "why": ""}
    try:
        h["proc"] = subprocess.Popen(_snap_args(g, path), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as err:
        h["why"] = f"game_snap could not start: {err}"
    return h


def finish_grab(h: dict) -> tuple:
    """(path | None, why, seconds from the start to the script's exit)."""
    proc = h.get("proc")
    if proc is None:
        return None, h.get("why") or "never started", None
    try:
        out, err = proc.communicate(timeout=GRAB_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        proc.kill()
        return None, "game_snap timed out", None
    took = time.time() - h["t0"]
    if proc.returncode == 0 and h["path"].is_file():
        return h["path"], "grabbed", took
    return None, f"game_snap exit {proc.returncode}: {((err or '') + (out or ''))[-200:]}", took


def _still_hang(g, ctx: Ctx, name: str) -> None:
    """207's still mid-climb: the window and the engine's own frame, the body still hanging (a NOTE, never a check)."""
    p1, w1 = grab_frame(g, _shots_dir(g) / f"{name}-window.png")
    p2, w2 = cb.shot(g, name)
    ctx.stills.append((name, str(p1) if p1 else w1, str(p2) if p2 else w2))
    g.note(f"STILL {name} (a NOTE, not a check): game_snap -> {p1 or w1}; engine shot -> {p2 or w2}. READ them: "
           f"{DRESS_NAME.capitalize()} grips the rungs (his own ladder clip), the +250 x mirror holds the same pose")


# ---- one climb / one hop ---------------------------------------------------------------------------------------------
def climb(g, ctx: Ctx, leg: str, fid: int, direction: str, pose: str, *, on_mount=None) -> dict:
    """The start pose (a bench-0 stock reposition when needed: a NOTE), `bench 0`, b0 AFTER the load and the pose, the
    stock climb (gt.ladder_run, act False), b1. res: the climb's behaviour verdict ("climb"), the twin deltas, "mid" (every
    mid-ladder publish, the hang included) and "climb_mid" (the mid-ladder publishes after the hang)."""
    ok, why = gt.ensure_pose(g, ctx.g, leg, fid, pose)
    if not ok:
        return {"pose_why": f"its start pose ({pose} on {fid}) was not reached: {why}"}
    ok, why = gt.set_bench(g, False)
    if not ok:
        return {"pose_why": f"`bench 0` failed: {why}"}
    spec = gt.LADDERS[fid]
    b0 = cb.raw(gt.rest(g))
    res = gt.ladder_run(g, ctx.g, leg, fid, direction, act=False, on_mount=on_mount)
    b1 = cb.raw(g.state)
    res.update(b0r=b0, b1r=b1, d_twins=J.delta(b0, b1, TWINS_KEY), d_misses=J.delta(b0, b1, MISSES_KEY))
    res["climb"] = gt.judge_ladder(res, spec, direction, act=False, has_key=False)
    res["mid"] = gt.mid_samples(_timeline(res), spec)
    res["climb_mid"] = gt.mid_samples(_after_hang(res), spec)
    if not gt.control(g.state):
        gt.recover(g, fid)
    return res


def hop(g, ctx: Ctx, leg: str, way: str, pose: str, *, still: str | None = None) -> dict:
    """408's hop with NO key held (never at a hop), scenario-local so a still can fire mid-arc: ``still`` starts game_snap
    in the background at the press and fires ONE engine `shot` from the watch at ARC_SHOT of the way to the landing while
    control is off (g.shot is a synchronous round trip: the watch resumes after it)."""
    hp = gt.HOPS[way]
    ok, why = gt.ensure_pose(g, ctx.g, leg, hp["field"], pose)
    if not ok:
        return {"pose_why": f"its start pose ({pose} on 408) was not reached: {why}"}
    ok, why = gt.set_bench(g, False)
    if not ok:
        return {"pose_why": f"`bench 0` failed: {why}"}
    b0 = cb.raw(gt.rest(g))
    res = gt.press_rec(g, ctx.g, leg, hp["field"], hp["entry"])
    grab = start_grab(g, _shots_dir(g) / f"{still}-window.png") if still else None
    shot: dict = {}
    t0 = time.time()

    span = gt.dist_xz(res.get("before"), hp["land"])

    def on_sample(st):
        dt = time.time() - t0
        if not still or shot or gt.control(st) or not (0 < span < math.inf):
            return
        frac = gt.dist_xz(res.get("before"), gt.pos(st)) / span
        if ARC_SHOT[0] <= frac <= ARC_SHOT[1]:
            shot["at"], shot["frac"] = dt, frac
            shot["path"], shot["why"] = cb.shot(g, still)

    g.press("confirm", 2)
    samples, hit = cb.watch(g, lambda s: not gt.control(s), max(gt.HOP_OFF_S, gt.HOLD_S), on_sample=on_sample)
    res["samples"] = gt._stamp(samples, t0)
    gt._window(res, res["samples"])
    res["left"] = hit is not None and (time.time() - t0) <= gt.HOP_OFF_S + 0.5
    res["land"] = None
    if hit is not None:
        more, land = cb.watch(g, gt.control, gt.HOP_S, on_sample=on_sample)
        res["samples"] += gt._stamp(more, t0)
        res["land"] = dict(cb.raw(land)) if land is not None else None
        res["land_s"] = time.time() - t0
        res["last_pos"] = gt.pos(more[-1]) if more else None
    b1 = cb.raw(g.state)
    res.update(b0r=b0, b1r=b1, d_twins=J.delta(b0, b1, TWINS_KEY), d_misses=J.delta(b0, b1, MISSES_KEY))
    res["hop"] = gt.judge_hop(res, hp, act=False, has_key=False)
    res["mid"] = gt.mid_air(res["samples"], res["before"], hp["land"])
    if still:
        p, w, took = finish_grab(grab)
        land_s = res.get("land_s")
        ctx.stills.append((still, str(p) if p else w, str(shot.get("path")) if shot.get("path") else shot.get("why")))
        g.note(f"STILL {still} (a NOTE, not a check): engine shot "
               + (f"at {shot['at']:.2f} s after the press, {shot['frac']:.0%} of the way -> "
                  f"{shot.get('path') or shot.get('why')}" if shot else
                  f"NOT taken (no control-off publish {ARC_SHOT[0]:.0%}-{ARC_SHOT[1]:.0%} of the way to the landing)")
               + f"; game_snap (started at the press) -> {p or w}"
               + (f", its script exited {took:.2f} s after the press" if took is not None else "")
               + (f" (the landing at {land_s:.2f} s: the window capture is mid-arc only if it finished first)"
                  if land_s is not None else "") + ". READ them: Steiner's own jump clip, the mirror in the same pose")
    if not gt.control(g.state):
        gt.recover(g, hp["field"])
    return res


# ---- the arrivals -----------------------------------------------------------------------------------------------------
def arrive_dressed(g, ctx: Ctx, fid: int, label: str) -> tuple:
    """`selfdress self steiner` at rest (the arm lands at the NEXT load), then warp(fid, entrance 0) -- 207 under
    ScenarioCounter 2030 / 2225 with scenario 2000 --, the post-init witness, and K3D's read (polled DRESS_S). An arm that
    did not land is re-issued with ONE re-warp. Never gt.arrive: its undress sends `selfdress self off`."""
    try:
        gt.rest(g)
    except HarnessError:
        pass
    last = ""
    for attempt in (1, 2):
        ok, why = cb.try_ns(g, "selfdress", "self", DRESS_NAME)
        ctx.self_set = ctx.self_set or ok
        if not ok:
            return False, f"`selfdress self {DRESS_NAME}` refused: {why}"
        sc = None
        if fid == 207 and g.state.scenario in gt.SC_UNARMED_207:
            sc = gt.SC_SAFE_207
            g.note(f"207's precondition: ScenarioCounter {g.state.scenario} leaves e10/e11 unarmed -- warping with "
                   f"scenario={sc}")
        try:
            _warp(g, fid, sc)
        except HarnessError as err:
            return False, f"warp {fid} failed: {str(err)[:200]}"
        st = cb.poll(g, lambda s: gt.arrived(s, fid)[0], ARRIVE_S, f"field {fid}'s post-init witness")
        a_ok, a_why = gt.arrived(st or g.state, fid)
        if not a_ok:
            return False, f"no post-init witness on {fid}: {a_why}"
        st = cb.poll(g, lambda s: judge_dressed(s)[0], DRESS_S, f"the {DRESS_NAME} dress on {fid}") or g.state
        d_ok, d_why = judge_dressed(st)
        last = d_why
        if d_ok or cb.path(st, SELF_KEY + ".armed") is True or attempt == 2:
            ctx.k3d.append((label, fid, d_ok, f"{label}: {d_why}"))
            return True, a_why
        g.note(f"{label}: dress.self.armed read false after the load -- re-issuing `selfdress self {DRESS_NAME}` and "
               f"re-warping once")
    return True, last


# ================================================================================================ the run
def run(g, field: int | None = None):
    st0 = cb.poll(g, lambda s: s.netsync is not None, 15.0, "the netsync block (protocol 5)") or g.state
    s157 = is_s157(st0)
    has_gl = cb.has(st0, gt.PROBE)
    cal = calibration_env()
    ctx = Ctx(mode_of(cal, s157), s157, has_gl, cal)
    led = cb.Ledger(g, catalog(ctx.mode, has_gl), finals=FINALS, width=LEDGER_WIDTH)
    if field is not None:
        g.note(f"--field {field} is ignored: the bench picks its own fields (114 -> 207 -> 408)")
    g.note(f"s157 climb animation, solo, mode {ctx.mode!r} ({CAL_ENV}={cal!r}); the engine reads as "
           f"{'s157' if s157 else 's156 or older'}; expected {'%d/%d' % tally(ctx.mode, has_gl)}")
    if not s157:
        g.note("s156: THE AUTOMATIC CALIBRATION -- the s157 surfaces are not present: K1, K2, every GF* row and every *-CAL "
               "row are dropped as N/A (never scored), `bench ghostframe` / `selfdress twin` are never sent; predicted RED: "
               + ", ".join(predicted("s156")) + f" ({MARKERS['s156']})" + (f"; {CAL_ENV}={cal!r} is ignored" if cal else ""))
    if not has_gl:
        g.note("no netsync.guestlocal (an engine before s156): K-TRIPS dropped as N/A")
    try:
        ctx.k0_ok = _k0(g, ctx, led)
        if not ctx.k0_ok:
            led.close("not reached: K0 (the setup or a preflight) refused")
            return
        _k1_k2(g, ctx, led)
        ctx.trips0 = gt.gl_get(gt.gl(g.state), "trips.total", int)
        _hold_calibration(g, ctx)
        _field_114(g, ctx, led)
        _field_207(g, ctx, led)
        _field_408(g, ctx, led)
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    except Exception as err:                             # noqa: BLE001 - a BENCH bug: red and loud, the finally still runs
        g.note(f"the run FAULTED (a bench bug, not a verdict): {err!r}"[:400])
        led.close(f"not reached: the run FAULTED (a bench bug): {err!r}"[:300])
    finally:
        _finish(g, ctx, led)


def _safe(g, what: str, fn) -> None:
    try:
        fn()
    except Exception as err:                             # noqa: BLE001 - teardown: every later step must still run
        try:
            g.note(f"{what} failed: {err!r}"[:400])
        except Exception:                                # noqa: BLE001 - the game may be gone
            print(f"[coop_climb_anim] {what} failed: {err!r}")


def _finish(g, ctx: Ctx, led: cb.Ledger) -> None:
    """THE TEARDOWN, every step guarded: no key down; K3D, K-TRIPS and K-R; the root's ini back; the log archived; the
    calibration verdicts; the ledger closed -- and, LAST, the game quit (never an --attach'd one)."""
    try:
        _safe(g, "the key release", lambda: gt._release_all(g))
        _safe(g, "K3D", lambda: _k3d(g, ctx, led))
        _safe(g, "K-TRIPS", lambda: _k_trips(g, ctx, led))
        if ctx.k0_ok:
            _safe(g, "K-R", lambda: _k_r(g, ctx, led))
        else:
            if not getattr(g, "attach", False):
                _safe(g, "the release after K0's refusal", lambda: cb.release(g))
            led.unreached(["K-R"], "K0 refused: the bench never ran a leg (the role, if taken, released unjudged)")
        if ctx.ini_edited:
            _safe(g, "the ini restore", lambda: g.note(
                f"the instance root's Memoria.ini put back to install + overlay: "
                f"{'rewritten' if g.instance.restore_ini() else 'already so'}"))
        _safe(g, "the log archive", lambda: g.note(
            f"Memoria.log archived: {cb.archive_log(g, 'climb-anim-' + ctx.mode)}"))
        if ctx.mode in PREDICTED:
            led.close("not reached: the run ended before this check")
            ok, why = judge_markers(ctx.mode, ctx.marks)
            led.check("K-CAL-M", ok, why)
            led.judge_calibration("K-CAL", predicted(ctx.mode))
        led.close(final=True)
        if ctx.stills:
            _safe(g, "the stills note", lambda: g.note(
                "STILLS to READ: " + "; ".join(f"{n}: window {a}, engine {b}" for n, a, b in ctx.stills)))
    finally:
        _quit(g)


def _quit(g) -> None:
    """THE GAME QUITS when the bench ends (memory feedback-close-the-game-after-a-lab): Session.quit -- the request, then
    the wait for the process to exit (Session.stop then finds it gone). Never a game this run did not launch (--attach)."""
    if getattr(g, "attach", False):
        print("[coop_climb_anim] --attach: the game is not this run's to close -- left running")
        return
    if getattr(g, "keep_open", False):
        print("[coop_climb_anim] --keep-open is OVERRIDDEN: this bench always closes its game")
    fn = getattr(g, "quit", None)
    if fn is None:
        return
    try:
        fn()
    except Exception as err:                             # noqa: BLE001 - Session.stop still asks again and kills it
        print(f"[coop_climb_anim] the quit did not land ({err!r}) -- the session's teardown kills the game")


def _k0(g, ctx: Ctx, led: cb.Ledger) -> bool:
    cb.provenance(g)
    if ctx.mode == "bad":
        led.check("K0", False, f"refused: {CAL_ENV}={ctx.cal_raw!r} names no lever this bench has (unset / 0 = plain, "
                               f"twin, frame) -- nothing was edited")
        return False
    if getattr(g, "attach", False):
        led.check("K0", False, "refused: --attach (the ghost-frame counters and the proof block are per PROCESS, and the ini "
                               "edit must be read by a fresh field load -- play.py launches one)")
        return False
    if getattr(g, "instance", None) is None:
        led.check("K0", False, "refused: no --instance root (the bench writes [Netsync] GhostAs into an instance ROOT's "
                               "Memoria.ini, never the shared install's: py tools/harness/instance.py ensure "
                               "C:\\gd\\ff9-inst\\host, then --instance C:\\gd\\ff9-inst\\host)")
        return False
    ctx.ini_edited = True                                 # set first: a write that fails half-way is still restored
    try:
        bak = g.instance.netsync(dict(INI_UPDATES), backup_to=_run_dir(g) / "ini")
        g.note(f"the instance ini: [Netsync] GhostAs = {GHOST_AS!r} (the mirror wears my wire body raw); backup {bak}")
    except Exception as err:                             # noqa: BLE001 - an ini write never kills the run
        led.check("K0", False, f"the instance ini edit failed: {err!r}"[:400])
        return False
    try:
        g.newgame()
        _warp(g, 114)
    except HarnessError as err:
        led.check("K0", False, f"newgame / warp 114 failed: {str(err)[:300]}")
        return False
    try:
        g.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        g.note(f"noencounter refused ({str(err)[:120]}) -- a random battle may interrupt a leg")
    g.wait_frames(45)
    ok1, why1 = cb.try_ns(g, "selftest", 1)
    ok2, why2 = cb.try_ns(g, "bench", 0)
    st = cb.poll(g, lambda s: bool((s.netsync or {}).get("forced")) and bool((s.netsync or {}).get("selftest")), 5.0,
                 "the forced selftest role") or g.state
    ns = st.netsync or {}
    arr = cb.poll(g, lambda s: gt.arrived(s, 114)[0], ARRIVE_S, "114's post-init witness")
    a_ok, a_why = gt.arrived(arr or g.state, 114)
    dx, dz, src = gt.offset_from(cb.log_lines(g), cb.ini_value(g, "Netsync", "SelfTestOffset"))
    off_ok = gt.offset_ok(dx, dz)
    same = is_s157(g.state) == ctx.s157
    good = (ok1 and ok2 and bool(ns.get("forced")) and bool(ns.get("selftest")) and ns.get("bench") is False and a_ok
            and off_ok and same)
    led.check("K0", good, f"selftest={ns.get('selftest')!r} forced={ns.get('forced')!r} bench={ns.get('bench')!r}; 114: "
                          f"{a_why}; SelfTestOffset {dx},{dz} ({src}): "
                          + ("ok" if off_ok else f"REFUSED: |offset| >= {gt.OFFSET_LIMIT:g} arms the auto-teleport")
                          + ("" if same else f"; the engine's keys CHANGED since the title (s157 {ctx.s157} -> "
                                             f"{is_s157(g.state)}): the catalog is wrong")
                          + (f"; {why1 or why2}" if (why1 or why2) else ""))
    return good


def _k1_k2(g, ctx: Ctx, led: cb.Ledger) -> None:
    if not ctx.s157:
        return
    table, twhy = gt.kit_table()
    g.note(f"the kit's committed table: {table!r} ({twhy})")
    lines = cb.wait_log(g, 0, FG.PROOF_GHOST_FRAME, timeout=SELFTEST_S)
    led.check("K1", *judge_k1(lines, table))
    st = cb.poll(g, lambda s: cb.path(s, GF_KEY + ".selftest") is not None
                 and cb.path(s, SELF_KEY + ".twin_selftest") is not None, SELFTEST_S, "the s157 proof verdicts") or g.state
    led.check("K2", *judge_k2(st))


def _hold_calibration(g, ctx: Ctx) -> None:
    if ctx.mode not in ("twin", "frame"):
        return
    ok, why = _lever(g, ctx, ctx.mode, "off")
    ctx.cal_held = ok
    g.note(f"CALIBRATION: `{'selfdress twin off' if ctx.mode == 'twin' else 'bench ghostframe off'}` "
           f"{'taken' if ok else 'REFUSED: ' + why}, held for the whole run; predicted red "
           f"{', '.join(predicted(ctx.mode))}")


# ------------------------------------------------------------------------------------------------ field 114 (undressed)
def _field_114(g, ctx: Ctx, led: cb.Ledger) -> None:
    rows = [c for c in ("U114-UP", "GF114-HOLD", "GF114-TRACK", "U114-DN", "GF114-TRACK-DN", "GF114-CAL") if c in led.catalog]
    st = cb.poll(g, lambda s: gt.arrived(s, 114)[0], ARRIVE_S, "114's post-init witness")
    ok, why = gt.arrived(st or g.state, 114)
    if not ok:
        led.unreached(rows, f"no post-init witness on 114: {why}")
        return
    _act(g, ctx, led, ("U114-UP", "GF114-HOLD", "GF114-TRACK"), 114, lambda r: _u114(g, ctx, led, "up"))
    _act(g, ctx, led, ("U114-DN", "GF114-TRACK-DN"), 114, lambda r: _u114(g, ctx, led, "down"))
    _act(g, ctx, led, ("GF114-CAL",), 114, lambda r: _gf114_cal(g, ctx, led))


def _u114(g, ctx: Ctx, led: cb.Ledger, direction: str) -> None:
    up = direction == "up"
    leg = "U114-UP" if up else "U114-DN"
    res = climb(g, ctx, leg, 114, direction, "bottom" if up else "top",
                on_mount=hang_on_mount(ctx, 114, direction) if up else None)
    if "pose_why" in res:
        led.unreached([leg] + (["GF114-HOLD", "GF114-TRACK"] if up else ["GF114-TRACK-DN"]), res["pose_why"])
        return
    c_ok, c_why = res["climb"]
    u_ok, u_why = J.judge_undressed(res["mid"], model=gt.GEOM[114]["body"], d_twins=res["d_twins"],
                                    d_misses=res["d_misses"], share=SHARE)
    led.check(leg, c_ok and u_ok, f"climb: {c_why} || undressed: {u_why}")
    if up:
        rec = {"hang": res.get("hang") or [], "mid": res["climb_mid"]}
        _mark(ctx, "GF114-HOLD", rec)
        _mark(ctx, "GF114-TRACK", rec)
        _rec(led, "GF114-HOLD", *J.judge_hold(res.get("hang") or [], wire_tol=0))
        _rec(led, "GF114-TRACK", *J.judge_track(res["climb_mid"], min_wraps=1))
    else:
        _mark(ctx, "GF114-TRACK-DN", {"mid": res["climb_mid"]})
        _rec(led, "GF114-TRACK-DN", *J.judge_track(res["climb_mid"], min_wraps=1))


def _gf114_cal(g, ctx: Ctx, led: cb.Ledger) -> None:
    spec = gt.LADDERS[114]
    cal: dict = {}

    def on_mount(gg, res):
        res["n_pre"] = len(res.get("samples") or [])
        moving, moved = _hold_past(gg, spec, "up")
        settle = cb.hold_for(gg, SETTLE_S)
        at = cb.mark(gg)
        b0 = cb.raw(gg.state)
        cal["off"] = cb.try_ns(gg, "bench", "ghostframe", "off")   # THE DOCUMENTED EXCEPTION: mid-hang, no key held
        cb.hold_for(gg, CAL_OFF_WAIT_S)
        off = [cb.raw(s) for s in cb.hold_for(gg, CAL_OFF_S)]
        b1 = cb.raw(gg.state)
        cal["on"] = cb.try_ns(gg, "bench", "ghostframe", "on")
        w = cb.hold_for(gg, CAL_ON_S)
        b2 = cb.raw(gg.state)
        cal.update(moved=moved, off_s=off, on_s=_settled(w), lines=cb.new(gg, at),
                   d_restores=J.delta(b0, b1, GF_KEY + ".restores"), d_snaps=J.delta(b1, b2, GF_KEY + ".snaps"))
        res["hang_all"] = [cb.raw(s) for s in list(moving) + list(settle)] + off + [cb.raw(s) for s in w]

    res = climb(g, ctx, "GF114-CAL", 114, "up", "bottom", on_mount=on_mount)
    if "pose_why" in res:
        led.unreached(["GF114-CAL"], res["pose_why"])
        return
    if "off" not in cal:
        led.check("GF114-CAL", False, f"no mount, so no hang: {res['climb'][1]}")
        return
    lines = cal.get("lines") or []
    m_ok, m_why = J.frame_red_marker(cal["off_s"], why="lever", lever=True)
    h_ok, h_why = J.judge_hold(cal["on_s"], wire_tol=0)
    c_ok, c_why = res["climb"]
    parts = [("`ghostframe off` taken", cal["off"][0]), ("its OFF line", cb.count(lines, FG.GHOSTFRAME_LOG_OFF) == 1),
             ("the s156 signature while off", m_ok), ("`ghostframe on` taken", cal["on"][0]),
             ("its ON line", cb.count(lines, FG.GHOSTFRAME_LOG_ON) == 1), ("the hold back after on", h_ok),
             ("snaps +1 at the re-entry", cal.get("d_snaps") == 1), ("the climb out", c_ok)]
    led.check("GF114-CAL", all(v for _, v in parts),
              gt._parts(parts) + f" -- off: {m_why}; on: {h_why}; restores +{cal.get('d_restores')} snaps "
                                 f"+{cal.get('d_snaps')}; climb: {c_why}"
              + "".join(f"; refused: {w}" for k in ("off", "on") for ok_, w in [cal[k]] if not ok_))


# ------------------------------------------------------------------------------------------------ field 207 (Steiner)
def _field_207(g, ctx: Ctx, led: cb.Ledger) -> None:
    rows = [c for c in ("TW207-UP", "GF207-HOLD", "GF207-TRACK", "TW207-DN", "TW207-CAL-OFF", "TW207-CAL-MISS")
            if c in led.catalog]
    if not rows:
        return
    ok, why = arrive_dressed(g, ctx, 207, "207")
    if not ok:
        led.unreached(rows, why)
        return
    _act(g, ctx, led, ("TW207-UP", "GF207-HOLD", "GF207-TRACK"), 207,
         lambda r: _tw207(g, ctx, led, "TW207-UP", "up", "bottom", hang=True, still="s207-mid"))
    _act(g, ctx, led, ("TW207-DN",), 207, lambda r: _tw207(g, ctx, led, "TW207-DN", "down", "top"))
    twin_moved = False
    for leg, lever, direction, pose in (("TW207-CAL-OFF", "off", "up", "bottom"), ("TW207-CAL-MISS", "miss", "down", "top")):
        if leg not in led.catalog:
            continue
        twin_moved = True
        _act(g, ctx, led, (leg,), 207, lambda r, leg=leg, lever=lever, d=direction, p=pose:
             _tw207_cal(g, ctx, led, leg, lever, d, p))
    if twin_moved:
        ok, why = _lever(g, ctx, "twin", "on")
        g.note(f"after the 207 calibration legs: `selfdress twin on` {'taken' if ok else 'REFUSED: ' + why} (the next load "
               f"reads it)")


def _tw207(g, ctx: Ctx, led: cb.Ledger, leg: str, direction: str, pose: str, *, hang: bool = False,
           still: str | None = None) -> None:
    res = climb(g, ctx, leg, 207, direction, pose,
                on_mount=hang_on_mount(ctx, 207, direction, still=still) if hang else None)
    gf_rows = ["GF207-HOLD", "GF207-TRACK"] if hang else []
    if "pose_why" in res:
        led.unreached([leg] + gf_rows, res["pose_why"])
        return
    c_ok, c_why = res["climb"]
    t_ok, t_why = judge_twin_leg(ctx.mode, res["mid"], res["d_twins"], res["d_misses"], hop=False)
    need = TWIN_MIN_207 if direction == "up" else 1
    enough = J._num(res["d_twins"]) and res["d_twins"] >= need
    _mark(ctx, leg, {"mid": res["mid"], "d_twins": res["d_twins"], "d_misses": res["d_misses"]})
    led.check(leg, c_ok and t_ok and enough, f"climb: {c_why} || twin: {t_why} || twins +{res['d_twins']} (want >= {need})")
    if hang:
        rec = {"hang": res.get("hang") or [], "mid": res["climb_mid"]}
        _mark(ctx, "GF207-HOLD", rec)
        _mark(ctx, "GF207-TRACK", rec)
        _rec(led, "GF207-HOLD", *J.judge_hold(res.get("hang") or [], wire_tol=0))
        _rec(led, "GF207-TRACK", *J.judge_track(res["climb_mid"]))


def _tw207_cal(g, ctx: Ctx, led: cb.Ledger, leg: str, lever: str, direction: str, pose: str) -> None:
    """Set the twin lever at rest, THEN load (re-warp 207: K3D again), then the climb: the predicted red's signature must
    show (twin_red_marker GREEN) and the twin judge must go RED."""
    ok, why = _lever(g, ctx, "twin", lever)
    if not ok:
        led.check(leg, False, f"`selfdress twin {lever}`: {why}")
        return
    a_ok, a_why = arrive_dressed(g, ctx, 207, f"{leg} re-warp")
    if not a_ok:
        led.unreached([leg], a_why)
        return
    res = climb(g, ctx, leg, 207, direction, pose)
    if "pose_why" in res:
        led.unreached([leg], res["pose_why"])
        return
    c_ok, c_why = res["climb"]
    m_ok, m_why = J.twin_red_marker(res["mid"], alias_ids=ALIAS_IDS, mode=lever, d_twins=res["d_twins"],
                                    d_misses=res["d_misses"], share=SHARE)
    t_ok, t_why = judge_twin_leg(ctx.mode, res["mid"], res["d_twins"], res["d_misses"], hop=False)
    led.check(leg, c_ok and m_ok and not t_ok, f"climb: {c_why} || marker ({lever}): {m_why} || judge_twin (must be RED): "
                                             f"{'GREEN -- the lever did not bite' if t_ok else 'red'}: {t_why}")


# ------------------------------------------------------------------------------------------------ field 408 (Steiner)
def _field_408(g, ctx: Ctx, led: cb.Ledger) -> None:
    rows = [c for c in ("TW408", "TW408-RET", "TW408-CAL-OFF") if c in led.catalog]
    if not rows:
        return
    ok, why = arrive_dressed(g, ctx, 408, "408")
    if not ok:
        led.unreached(rows, why)
        return
    _act(g, ctx, led, ("TW408",), 408, lambda r: _tw408(g, ctx, led, "TW408", "out", "ledge"))
    _act(g, ctx, led, ("TW408-RET",), 408, lambda r: _tw408(g, ctx, led, "TW408-RET", "ret", "shelf"))
    _still_408(g, ctx)
    if "TW408-CAL-OFF" in led.catalog:
        _act(g, ctx, led, ("TW408-CAL-OFF",), 408, lambda r: _tw408_cal(g, ctx, led))
        ok, why = _lever(g, ctx, "twin", "on")
        g.note(f"after TW408-CAL-OFF: `selfdress twin on` {'taken' if ok else 'REFUSED: ' + why}")


def _tw408(g, ctx: Ctx, led: cb.Ledger, leg: str, way: str, pose: str, *, still: str | None = None) -> None:
    res = hop(g, ctx, leg, way, pose, still=still)
    if "pose_why" in res:
        led.unreached([leg], res["pose_why"])
        return
    h_ok, h_why = res["hop"]
    t_ok, t_why = judge_twin_leg(ctx.mode, res["mid"], res["d_twins"], res["d_misses"], hop=True)
    _mark(ctx, leg, {"mid": res["mid"], "d_twins": res["d_twins"], "d_misses": res["d_misses"]})
    led.check(leg, h_ok and t_ok, f"hop: {h_why} || twin: {t_why}")


def _still_408(g, ctx: Ctx) -> None:
    """The 408 STILL on a hop of its OWN, never on a judged one: the engine `shot` is a synchronous round trip that stalls
    the watch for most of the arc (the s156 calibration's TW408 kept ONE mid-air sample while it fired, TW408-RET nine).
    TW408-RET lands on the ledge, so this is the e4 hop out again; a NOTE, never a check."""
    try:
        res = hop(g, ctx, "STILL-408", "out", "ledge", still="s408-arc")
        if "pose_why" in res:
            g.note(f"STILL s408-arc NOT taken: {res['pose_why']}")
    except Exception as err:                             # noqa: BLE001 - a still is a note: never a verdict, never a stop
        g.note(f"STILL s408-arc FAULTED (a note, not a verdict): {err!r}"[:300])
        gt.recover(g, 408)


def _tw408_cal(g, ctx: Ctx, led: cb.Ledger) -> None:
    leg = "TW408-CAL-OFF"
    ok, why = _lever(g, ctx, "twin", "off")
    if not ok:
        led.check(leg, False, f"`selfdress twin off`: {why}")
        return
    a_ok, a_why = arrive_dressed(g, ctx, 408, f"{leg} re-warp")
    if not a_ok:
        led.unreached([leg], a_why)
        return
    res = hop(g, ctx, leg, "out", "ledge")
    if "pose_why" in res:
        led.unreached([leg], res["pose_why"])
        return
    h_ok, h_why = res["hop"]
    m_ok, m_why = J.twin_red_marker(res["mid"], alias_ids=ALIAS_IDS, mode="off", d_twins=res["d_twins"],
                                    d_misses=res["d_misses"], share=SHARE)
    t_ok, t_why = judge_twin_leg(ctx.mode, res["mid"], res["d_twins"], res["d_misses"], hop=True)
    led.check(leg, h_ok and m_ok and not t_ok, f"hop: {h_why} || marker (off): {m_why} || judge_twin (must be RED): "
                                             f"{'GREEN -- the lever did not bite' if t_ok else 'red'}: {t_why}")


# ------------------------------------------------------------------------------------------------ the finals
def _k3d(g, ctx: Ctx, led: cb.Ledger) -> None:
    if "K3D" not in led.catalog or "K3D" in led.done:
        return
    if not ctx.k3d:
        led.unreached(["K3D"], "no dressed arrival was reached")
        return
    fields = {f for _, f, _, _ in ctx.k3d}
    both = {207, 408} <= fields
    led.check("K3D", both and all(ok for _, _, ok, _ in ctx.k3d),
              "; ".join(w for _, _, _, w in ctx.k3d) + f" ({len(ctx.k3d)} dressed arrival(s)"
              + ("" if both else ": 207 AND 408 are both required -- the run ended first") + ")")


def _k_trips(g, ctx: Ctx, led: cb.Ledger) -> None:
    if "K-TRIPS" not in led.catalog or "K-TRIPS" in led.done:
        return
    if ctx.trips0 is None:
        led.unreached(["K-TRIPS"], "trips.total was never read after the setup (the run ended first)")
        return
    t1 = gt.gl_get(gt.gl(g.state), "trips.total", int)
    led.check("K-TRIPS", t1 is not None and t1 == ctx.trips0,
              f"trips.total {ctx.trips0!r} after the setup -> {t1!r} after the last leg; last trip "
              f"{gt.gl_get(gt.gl(g.state), 'trips.last')!r}")


def _k_r(g, ctx: Ctx, led: cb.Ledger) -> None:
    """`reset` with both s157 levers HELD INTO it -- the calibration lever as held, the other pulled at rest now -- so the
    release line and each half of the re-read are checks that can fail (a release that forgot a lever reads it there)."""
    into_ok, gf_into, twin_into = True, False, False
    if ctx.s157:
        st = gt.rest(g)
        if cb.path(st, SELF_KEY + ".twin") == BW.TWIN_LEVER_NAMES[BW.TWIN_LEVER_ON]:
            ok, why = _lever(g, ctx, "twin", "miss")
            into_ok = into_ok and ok
        if cb.path(g.state, GF_KEY + ".lever_off") is not True:
            ok, why = _lever(g, ctx, "frame", "off")
            into_ok = into_ok and ok
        st = g.state
        twin_into = cb.path(st, SELF_KEY + ".twin") not in (None, BW.TWIN_LEVER_NAMES[BW.TWIN_LEVER_ON])
        gf_into = cb.path(st, GF_KEY + ".lever_off") is True
        g.note(f"K-R: into the reset -- twin {cb.path(st, SELF_KEY + '.twin')!r}, ghostframe lever_off "
               f"{cb.path(st, GF_KEY + '.lever_off')!r}, `selfdress self {DRESS_NAME}` {'set' if ctx.self_set else 'never set'}")
    at = cb.mark(g)
    cb.release(g)
    want_gf = 1 if gf_into else 0
    want_dress = 1 if (ctx.self_set or twin_into) else 0
    if want_gf:
        cb.wait_log(g, at, FG.GHOSTFRAME_LOG_RELEASE, 2.0)
    if want_dress:
        cb.wait_log(g, at, DRESS_RELEASE, 2.0)
    cb.hold_for(g, 0.5)                                  # room for a line that should NOT come
    lines = cb.new(g, at)
    st = g.state
    reread, why = (None, "")
    if ctx.s157:
        reread, why = cb.reread_with_role(g)
    ok, detail = judge_release(s157=ctx.s157, n_gf=cb.count(lines, FG.GHOSTFRAME_LOG_RELEASE),
                               n_dress=cb.count(lines, DRESS_RELEASE), want_gf=want_gf, want_dress=want_dress,
                               ns=st.netsync or {}, reread=reread, into_ok=into_ok and (gf_into and twin_into or
                                                                                        not ctx.s157))
    led.check("K-R", ok, detail + (f"; {why}" if why else ""))
