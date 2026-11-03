"""s165 -- WORLD-MAP CO-OP, THE GUEST FOLLOWS THE HOST OUT (memoria-patch s165, rung 1 of GUEST-FOLLOW.md): the bench, run unattended.
[ff9mapkit netsync s165] Three instruments in one file, on coop_world_wait.py's route and judges (imported, never copied: that 2k-line
file and its slow_leg registry stay put): the SOLO leg (one game in the selftest role, a FABRICATED host frame through the engine's
own encoders), the T2 `walk` leg (the desktop as a real GUEST, the COOP_TAPE_WORLD_WALK host replayed) and the DUO leg (two real
games). Every leg is judged on witnesses the engine does not compute -- ui_state on every sample, the world x/z the walker stands at
against the pose the host frame carried (the tape's own section 0, decoded offline by coop_peer; the duo host's own `world.x/z`), a
held direction's displacement over advancing frames, the save container's mtime -- beside the engine's own claim (`netsync.world.out`
/ `host` / `dot`, `netsync.saveguard`, `netsync.host.world`).

THE OWNER's CALL (studies/world-coop/S165-DESIGN.md, decisions 1-18): R1 a following, mirroring guest on a field follows a host whose
section 7 says b6 onto the world 9000 + section0[102], on foot, after THE LIVE DEBOUNCE (1200 ms of host-ALIVE time), and lands at the
host's live section-0 pose -- frozen there by s144 until the s144 rejoin; R2 a dot on the guest's MINIMAP shows the host (section 0,
no wire change); R3 the rejoin may arm from 9012 (it waits on the player); R4 a manual save is refused at SaveLoadUI's Save sites
(`saveguard old` is DRY: it reports would_save and still refuses). The wire stays v14, the harness protocol 5.

THE ROUTE (every leg): New Game -> 6603 FARSHORE (FF9CustomMap-world; RE-READ its registration first) -> world 9011 (WORLD11 at the
New-Game scenario) -- the follow-out's own commit, or the proven walk out (coop_world_wait.walk_out) where a row needs the world map
without it. A route that leaves the host at its landing cannot tell the live pose from the exit's arrival constant (both read
FS_LANDING (68, -444)), so EVERY LIVE-POSE ROW MAKES THE HOST STAND AT ICE_TILE (1197.37, -796.7): 1183 u away in plain x/z (only ~538 u
the short way round the torus: 68 + 1536 lies 407 u east of the tile -- so FAR_U is judged in PLAIN x/z, and the torus distance is
reported beside it), and ~59 u from WORLD11's own default pose (1145.7, -825.5: what a FieldEntrance 0 would reset the walker to).
THE PRE-INIT SAMPLE: every world landing is judged only on a sample with `world.block_ready` true AND `world.ticks` advancing (the first
WorldHUD frame precedes the guest's ~4.4 s all-block load). THE ACTOR-BRICK LAW: no world-map save; R4's rows refuse the save they
open, and run only on a sandboxed save root (`save_sandboxed`).

THE OFFLINE ORACLE (S165-OR): coop_world_wait.read_oracle (6603's door to the world map, its WorldMap(9011), WORLD11's Field(300),
block (18,12) stock, no fork of 300, the battle scene registered). Every expected text is battlewire's (the s165 contract section).

SOLO (COOP_WF_LEG=solo, the default; the selftest role with `netsync bench 1` and FollowHost set: `netsync worldfollow host <x> <z>
[idx] [mode] [entrance] [veg]` builds a host frame through the real encoders, b6 set; refused unless FollowHost is set and
SuppressEncounters reads true, so a bench world landing never autosaves a fabricated pose). COOP_WF_SOLO=out|dot|save picks ONE
section (the design's bench order: the follow-out first and alone, with `dot off`; then the dot rows; then R3 / R4), all by default.
  setup  INI (READ-ONLY: [Netsync] Enabled 0 or absent, FollowHost 1 -- selftest_block.sh) -> OR -> S0 (newgame, the COOPPARTY seed,
         6603, encounters off, the forced selftest role) -> P0 (the s165 keys in the agent's order -- `netsync.world` ends r3, out, host,
         dot; `netsync` ends swap, saveguard, host; the top-level world block ends `block_ready` -- and the proof line 'world follow
         selftest: OK (N rows, M mutants)' (one combined table, the dot's 'world dot selftest' line beside it when logged), none FAIL)
         -> P1 (`netsync bench 1`; every lever at rest: out on, hold false, dot on, r3 act, saveguard act -- or, COOP_CALIBRATE=1 on
         s165, the lever COOP_WF_LEVER pulled here and held through the run).
  OUT (on FieldHUD 6603; each refusal row: one fabricated host frame, REFUSE_S watched -- the guest on FieldHUD 6603 on EVERY sample,
       `out.why` the engine's token, `out.starts` +0, the host cache reading the frame (b6, valid); the content refusals' 'waits:'
       line logged -- then `host off`, the b6 visit over):
    RIDES     [190] 1 (the host on a chocobo): why 'riding' (decision 5: on foot only)
    CHOCO     [181] 1 (the host calling Choco): why 'choco_call' (its replay would make the guest's own Choco run in)
    EVENT     [102] 1, 4, 6, 12 (9001 / 9004 / 9006 / 9012): why 'event_world' each (decision 6: never followed into)
    RANGE     [102] 13 (no world this install has): why 'idx_range'
    ETB       Mogdrift's line open on 6603 (`netsync talk <uid>`, the keeper's own talk): why one of term 6's tokens -- 'no_control',
              'line', 'backlog' (the 0.9 s timer would cut the line) -- the line closed after
    HOLD      `worldfollow hold`: why 'hold' (it holds the START only); `release` after
    DEBOUNCE  the frame and `host stale` in ONE request (the heartbeat frozen: the host's own synchronous block load): why 'debounce',
              `out.debounce_ms` < 1200 on every sample -- a frozen heartbeat never counts (a wall-clock debounce would start the guest)
    LEVER     `worldfollow off`: why 'lever'; `on` after
    SUPERSEDE `swap delay 2000` (the s164 lever: the world-out's commit waits past its own due -- the window to act inside the fade),
              the frame at ICE_TILE, `out.state` 'fading', then `netsync swap intent 300` (the s164 bench op: the host's field intent
              through the real codec): `superseded` +1, its line, the guest lands on FieldHUD 300 and is NEVER on WorldHUD (decision 8:
              a field follow before the commit wins and takes the darkening slot); then home to 6603
    LEAVE     THE FIRST C# FIELD-TO-WORLD COMMIT: the frame at ICE_TILE with FieldEntrance 0 -> WorldHUD 9011 within LEAVE_S, starts /
              commits / lands +1, the start / commit / 'landed on world map 9011' lines, never another field on the way
    BLOCK     THE PRE-INIT SAMPLE: a WorldHUD 9011 sample with `world.block_ready` true and `world.ticks` advancing over the next
    POSE      ...on it: the walker within POSE_TOL of ICE_TILE (the fabricated pose), >= DEFAULT_MIN_U from WORLD11's default (1145.7,
              -825.5) and >= FAR_U (plain) from FS_LANDING; `out.last.frame` 'latest'
    ENTRANCE  the entrance rule: `entrance_fix` +1 and FieldEntrance 35 (POSITION_PRESET_KEY: 0 would have reset the walker)
    FOOT      on foot: `world.vehicle` ([190]) 0 and `world.ctl` 0
    FROZEN    s144's freeze took it: `hold up` moves < HELD_U over advancing frames, freeze.on, freeze.edges +1 since the leave
    ONFOOT    the on-foot substitution: back on 6603, `swap delay 2000`, the frame at ICE_TILE, then -- inside the fade -- the host
              MOUNTED elsewhere (`host 500 -500 11 1`): the guest lands at ICE_TILE (the start pin's pose), on foot, `substituted` +1
  DOT (on the world map: the ONFOOT landing, else the guest's own walk out; teleported onto ICE_TILE, inside the disc-1 Mist window):
    DOT-HUD   Select pressed ONCE (a New Game lands with the minimap off: the host's mirrored [100] = 0) -> `dot.hud` 'HUD', minimap
    DOT-SELF  `host self` (my own live 64-72): shown, ON MY OWN ARROW within DOT_PX_TOL px (px / py against own_px / own_py), not at
              the edge, the donor census read
    DOT-MARK  `host 1197.3 -799.6` (the Ice Cavern marker): the raw map point (sx, sy) = DOT_MARK_SXSY within SXSY_TOL
    DOT-EDGE  `host 68 -444` (FS_LANDING, just EAST of the window's right edge): shown, `edge` true, the raw sx < 0 (the raw map puts it
              far LEFT) and px at the RIGHT edge -- the minimap's width read off DOT-MARK's own px / sx
    DOT-STALE `host self` then `host stale`: past DotFreshMs, why_not 'stale', hidden
    DOT-NOB6  `host self` then `host nob6`: why_not 'no_b6', hidden
    DOT-OTHER the marker at [102] 2: why_not 'other_world', hidden
    DOT-LEVER `dot off`: hidden, why_not 'lever', still WANTED (the lever hides a wanted dot); `dot on`: shown again
  SAVE:
    R3        `netsync.world.r3` at rest ('act', arms_from_9012 0) and its lever round trip (`r3 old` -> 'old', `r3 act` -> 'act'); R3's
              truth table is the proof line's (P0): decision 13 calibrates by lever and by its pure table with mutants, no 9012 visit
    R4        THE SAVE GUARD (sandboxed saves only): `savemenu` (the Alt+F5 adapter), a slot picked, refused: `saveguard.refused` +1,
              `would_save` +0, its reason, 'save refused while following your partner' logged; the save files' mtimes unchanged
    R4-DRY    `saveguard old` (DRY): the same pick refused, `would_save` +1 INSTEAD of `refused` (+0: the engine's counting; s164's gate
              -- mirroring or a diorama -- would have saved the bench), the files unchanged; `saveguard act` after
    R4-S      `netsync bench 0`: the S term alone (SuppressEncounters: FollowHost on the selftest role -- it holds through the ~2.3 s link
              stall while L flickers false) still refuses; `bench 1` after
  R      `worldfollow off` pulled, then `reset`: the role released and 'worldfollow levers released (with the harness)' once; re-read
         WITH the role: every lever at rest.

T2 (COOP_WF_LEG=walk; the desktop is a REAL client: Memoria.ini [Netsync] written through _coop_peer_bench.IniGuard (coop_world_wait's
GUEST_VALUES: FollowHost 1, SessionGraceMs 30000), backed up first, restored byte-exact; tools/harness/coop_peer.py `replay-host`
replays THE WORLD-WALK TAPE whole, holding at its end -- COOP_TAPE_WORLD_WALK=1 coop_tape_record.py, recorded on the deployed s164 host
(rung 1 changes no host byte: a valid oracle); latest-world-walk.json in its own dir; COOP_TAPE names one):
  T2-TAPE  the tape reads back and its six facts hold (_coop_peer_bench.world_walk_tape_facts: paired on 6603, the story frames, b6 on
           foot on world 9011, the landing stand, the TILE stand >= 60 s, then 300)
  T2-PEER  port free, the owner's bridge DOWN, the guest config written (the engine's own config line), the replay-host listening, the
           guest connected, the replay started
  WK-I     the instrument: paired on 6603 and 'state-mirror ARMED' before the host's world exit (the peer's 'host field 6603 -> 0'),
           the guest on FieldHUD 6603; on s165 `worldfollow hold` sent BEFORE the replay (never on an engine without
           `netsync.world.out`: s164 fails the sub-verb closed -- nothing new is ever sent there)
  WK-WAIT  the hold holds the START only: from the exit until the tape's host stands at the tile (the guest's own `netsync.world.host`
           reading the tile for HOLD_SETTLE_S), every sample on FieldHUD 6603, `out.why` 'hold', `out.hold` true, the host cache b6
  WK-LEAVE `worldfollow release` -> WorldHUD 9011 within LEAVE_S, starts / commits / lands +1 -- judged after block_ready + ticks
  WK-POSE  the landing within POSE_TOL (torus) of the TAPE's OWN section-0 pose over the guest's seam bracket (its last sample before
           `lands` +1 and its first after, mapped onto the tape clock through the replay's own anchor), and >= FAR_U (plain) from
           FS_LANDING; `out.last.frame` 'latest' or 'pin'
  WK-FROZEN frozen there: `hold up` < HELD_U, freeze.on ('live' / 'mirroring')
  WK-DOT   Select once; the dot shown, its host_x / host_z within DOT_TOL of the tape's own pose at that sample (the `coop_peer where
           --pose` decode), its raw (sx, sy) navi_get_pos of that pose within SXSY_TOL
  WK-REJOIN the tape's host enters 300: the guest rejoins 300 from the world map (FieldHUD 300, rejoin.lands +1, 'world rejoin landed
           on field 300'), and [s164] THE ARRIVAL GUARD's world exclusion (coop_world_wait.judge_arrive_world)
  T2-SAVE / T2-INI the finals (no title fallback; Memoria.ini byte-exact).

DUO (`py tools/harness/duo.py studies/test-harness/scenarios/coop_world_follow.py`; PAIR on 6603; keyed by the GUEST's stage):
  D0       the instrument: both on FieldHUD 6603, the guest mirroring
  D-FO1    the host walks out: the guest follows out -- WorldHUD 9011 within FO_S of the host's walk out, starts / commits / lands +1,
           landed within POSE_TOL of the host's OWN world x/z (judged after block_ready + ticks); the heartbeat witness (did the
           guest's own `world.host.hb_age_ms` read the host's block-load stall and its resume before the commit?) and the landing gap
           REPORTED, never judged -- the first duos committed inside the host's load on one run of two and landed at the same pose
           (height included) as the run that waited it out (ONE-PC LOAD CONTENTION; decision 4 as corrected)
  D-HOST   the host's own lines once each ('host: world-map exit from field 6603 to world 9011', 'host: on world map 9011 (b6) at world
           frame N, blocks ready ...') and `netsync.host.world` b6 true, wmapjumps +1 (E6: no wire byte)
  D-DOT    the guest presses Select once; at the landing and after the host teleports onto ICE_TILE the guest's dot shown with host_x /
           host_z within DOT_TOL of the host's own world x / z, the guest's own pose unmoved (frozen)
  D-REJOIN the host Confirms on the tile into 300: the guest rejoins 300 (coop_world_wait.judge_rejoin_land + the arrival guard's world
           clause) and its dot is NEVER shown once the host stood on 300, nor inside the guest's own rejoin window (hidden before its
           fade: judged where a sample fell inside it -- THE BRACKET LAW)
  D-FO2    both back on 6603 (the host's warp; the guest's field follow); `worldfollow hold` on the guest; the host walks out and
           teleports onto ICE_TILE; once the guest's host cache reads the tile, `release`: the guest lands at ICE_TILE (POSE_TOL),
           >= FAR_U (plain) from FS_LANDING
  D-SHARED THE SHARED-FILE LAW (an INSTRUMENT row, never an engine verdict): no 'Sharing violation' / 'When importing FBX' in either
           game's log since D0 (the two world loads on one PC)

CALIBRATION -- a check that cannot fail is not a check.
  * OLD_PREDICTED, on the deployed s164 (COOP_CALIBRATE=1): no `netsync.world.out` -- the bench PROBES first and never sends a
    `worldfollow` op or `savemenu` there. SOLO: every s165 row red (the keys and the verb absent); green INI, OR, S0, R. T2: the guest
    stays on FieldHUD 6603 -- WAIT, LEAVE, POSE, FROZEN, DOT, REJOIN red (the host's entry into 300 is then s164's field-to-field
    follow, never a world rejoin); the instrument rows green. DUO: D-HOST, D-FO1, D-DOT, D-REJOIN, D-FO2 red; D0, D-SHARED green.
  * LEVER_PREDICTED, on s165 (COOP_CALIBRATE=1, COOP_WF_LEVER=out|dot|r3|saveguard, held from P1): `out` (`worldfollow off`) -- every
    OUT row but LEVER (each refusal reads 'lever', nothing starts); `dot` (`dot off`) -- DOT-SELF, DOT-EDGE (the placement is still
    published: only `shown` goes); `r3` (`r3 old`) -- R3; `saveguard` (`saveguard old`, DRY) -- R4 and R4-S (would_save +1: s164's gate, mirroring or a
    diorama, would have saved both). T2 (`out`): WAIT,
    LEAVE, POSE (the guest then walks out on its own, so FROZEN / DOT / REJOIN still run).
  * OFFLINE: the stand-in (tools/harness/fakegame.py, rung `worldfollow`; its WORLD_FOLLOW_FAULTS) and ff9mapkit/tests/
    test_coop_world_follow.py: every leg smoked against it through the real Session, each fault red in exactly its *_FAULT_REDS rows,
    the s164 stand-in exactly OLD_PREDICTED, each lever exactly LEVER_PREDICTED, the pure judges red on each wrong shape.

THE REGRESSION RE-KEY (design "Regression"): every s144 / s145 leg that tests the guest's OWN exit sends `netsync worldfollow off` and
`dot off` to its guest when the probe shows `netsync.world.out` (coop_world_wait.follow_off), so it runs byte-identical to s164.

WHAT NO LEG HERE REACHES (named, not hidden): THE SESSION-END EXIT RAMP INSIDE THE FOLLOW-OUT's FADE -- the selftest role has no
session to end (SessionRampArms needs a mirroring client), and a real client's grace (>= 2 s plus the stale span) outlasts the 0.9 s
fade even with `swap delay` 2000: the ramp's `safeToLoad` reading FollowFadeInFlight is pinned at its call site by the kit's s165
source pins (tests/test_world_coop_harness.py) and is an owner check; the guest's OWN door inside the fade (decision 11: control is off
from the start, so no harness walk reaches the door); a world-to-world host move (decision 18: the dot's 'other_world' row stands in);
the full-map dot (not in rung 1); 9013 (decision 2's known limit); the dot's look (tint, size, depth: the owner's two-PC look,
`game_snap -Id`).

PRECONDITIONS -- THE OPERATOR'S JOB: the DLL under test deployed (the bench deploys nothing); controllers OFF, nobody at the keyboard
(THE UNATTENDED LAW), FF9 unfocused; 6603 registered; SOLO: [Netsync] Enabled 0 and FollowHost 1, a sandboxed save root for R4; T2:
the world-walk tape recorded on s164, the bench port free, [SaveFile] AutoSaveOnlyAtMoogle 0, THE OWNER's OWN BRIDGE DOWN
(127.0.0.1:49201); close the game after a lab.

    py tools/play.py studies/test-harness/scenarios/coop_world_follow.py --field 6603
    COOP_WF_SOLO=out py tools/play.py studies/test-harness/scenarios/coop_world_follow.py --field 6603
    COOP_CALIBRATE=1 COOP_WF_LEVER=dot py tools/play.py studies/test-harness/scenarios/coop_world_follow.py --field 6603
    COOP_WF_LEG=walk py tools/play.py studies/test-harness/scenarios/coop_world_follow.py
    py tools/harness/duo.py studies/test-harness/scenarios/coop_world_follow.py
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _coop_peer_bench as pb                              # noqa: E402 - the T2 two-role bench helpers
import coop_world_wait as cw                               # noqa: E402 - the s144 route and judges (imported, never copied)

HarnessError = cb.HarnessError
BW = cw._bw()                                              # battlewire (the driver puts tools/ on sys.path)

#: the s165 capability: key PRESENCE (State.coop_world_follow). An engine without it fails `netsync worldfollow` closed.
PROBE = "netsync.world.out"
LEGS = ("solo", "walk")
SECTIONS = ("out", "dot", "save")
LEVERS = ("out", "dot", "r3", "saveguard")


def _leg(raw) -> str | None:
    n = (raw or "solo").strip().lower()
    n = {"t2": "walk", "world-walk": "walk", "": "solo"}.get(n, n)
    return n if n in LEGS else None


_RAW_LEG = os.environ.get("COOP_WF_LEG", "solo")
LEG = _leg(_RAW_LEG)
_RAW_SOLO = os.environ.get("COOP_WF_SOLO", "all").strip().lower() or "all"
SOLO_SECTIONS = SECTIONS if _RAW_SOLO == "all" else tuple(s for s in SECTIONS if s == _RAW_SOLO)
_RAW_LEVER = os.environ.get("COOP_WF_LEVER", "out").strip().lower() or "out"
LEVER = _RAW_LEVER if _RAW_LEVER in LEVERS else None

# ------------------------------------------------------------------------------------------------ the route (coop_world_wait's)
FARSHORE, FS_DOOR, FS_LANDING, WORLD = cw.FARSHORE, cw.FS_DOOR, cw.FS_LANDING, cw.WORLD
ICE_CAVERN, ICE_TILE = cw.ICE_CAVERN, cw.ICE_TILE
#: WORLD11's dispatcher default when FieldEntrance (Int16[2]) reads 0 -- the record (293294, 58663, -211336) decoded (test_coop_peer
#: pins it): what an entrance-0 landing resets the walker to, ~59 u from ICE_TILE
WORLD11_DEFAULT = (1145.7, -825.5)
#: the Ice Cavern marker and its raw map point on the disc-1 Mist window (BW.navi_get_pos: (1197.3 - 645.12) / 890.88, 1 - (799.6 -
#: 428.8) / 851.2) -- the dot's placement math, judged on the engine's own published sx / sy
DOT_MARK = (1197.3, -799.6)
DOT_MARK_SXSY = (0.620, 0.564)
#: the keeper of the landing (landing.field.toml [[npc]] Mogdrift): the ETB row's line is his own talk
KEEPER_AT = (1600.0, -700.0)
KEEPER_NEAR = 160.0
#: the supersede's injected host intent: the s164 `swap intent` bench op's field (the route's own stock field)
INTENT_DEST = ICE_CAVERN
EVENT_IDXS = (1, 4, 6, 12)                                 # 9001 / 9004 / 9006 / 9012: the static ff9.eventWorldMaps set
RANGE_IDX = BW.WORLD_IDX_MAX + 1                           # 13: no world this install has
RIDE_MODE = 1                                              # [190] 1: the chocobo
CHOCO_VEG = 1                                              # [181] nonzero: the Choco call
MOUNT_AT = (500.0, -500.0)                                 # ONFOOT: where the host has ridden off to inside the guest's fade
OTHER_IDX = 2                                              # DOT-OTHER: a host on 9002

# ------------------------------------------------------------------------------------------------ the measures
POSE_TOL = 8.0           # a landing within this (torus) of the pose the host frame carried (coop_world_wait.ROUTE_TOL)
FAR_U = 1000.0           # ...and at least this far (PLAIN x/z) from FS_LANDING: 1183 u plain (the torus' 538 u is reported beside it)
DEFAULT_MIN_U = 30.0     # ...and this far from WORLD11's default (ICE_TILE stands 59.2 u from it)
HELD_U = cw.HELD_U
WALK_FRAMES = cw.WALK_FRAMES
DOT_PX_TOL = 1.0         # `host self`: the dot on my own arrow within this many minimap px
SXSY_TOL = 0.005         # the raw map point within this of navi_get_pos
EDGE_PX_TOL = 1.0        # the edge pin within this of the minimap's right edge
DOT_TOL = 8.0            # a dot's host_x / host_z within this of the host's own pose (the duo, T2)
DEBOUNCE_MS = BW.WORLD_OUT_DEBOUNCE_MS
REFUSE_S = 3.0           # a refusal row watches this long: past THE LIVE DEBOUNCE (1.2 s of host-alive time) with room
START_S = 8.0            # a fabricated frame -> `out.state` 'fading'
LEAVE_S = 60.0           # the start -> WorldHUD with its blocks ready (the guest's own ~4.4 s all-block load inside it)
FIELD_S = 30.0           # a supersede's field follow -> FieldHUD 300
HOME_S = 30.0            # back on FieldHUD 6603
DOT_S = 4.0              # a dot row's frame -> its published verdict
STALE_S = 2.5            # `host stale` -> past DotFreshMs (1000 ms)
SETTLE_FRAMES = 20
SUPERSEDE_DELAY_MS = 2000   # `swap delay`'s range top (BW.SWAP_DELAY_RANGE): the world-out's commit waits this long past its due
PICK_PRESSES = 3         # R4: Confirm presses to reach the Save site (the slot list, then the file)
PICK_S = 1.5
CLOSE_PRESSES = 6
POLL_S = 0.1
DETAIL_W = 1400

# ---- T2 / duo
PORT, CODE = cw.PORT, cw.CODE
GUEST_VALUES = cw.GUEST_VALUES
REPLAY_SPEED = 1.0       # replay-host replays in real time (a test seam: the stub replays faster)
DIAL_S = cw.DIAL_S
PAIR_S = cw.PAIR_S
EXIT_S = cw.EXIT_S
TILE_SLACK_S = 20.0      # the tape's tile stand on the wire -> the guest's host cache reading it
HOLD_SETTLE_S = 2.0      # ...read there this long before the release
REJOIN_S = 40.0          # the tape's / the host's entry into 300 -> the guest on 300
FO_S = 45.0              # the duo host's walk out returned -> the guest landed (its own ~4.4 s load after the debounce)
DUO_HOME_S = 40.0        # the duo host's warp to 6603 -> the guest followed it there
FORCE = pb.env_flag("COOP_WF_FORCE")

# ================================================================================================ the catalogs
SOLO_SETUP = {
    "S165-INI": "precondition (Memoria.ini, READ-ONLY): [Netsync] Enabled 0 or absent and FollowHost 1 (the selftest role with the "
                "fabricated host's gate)",
    "S165-OR": "the offline oracle (coop_world_wait.read_oracle): 6603's door to the world map, its WorldMap(9011), WORLD11's "
               "Field(300), block (18,12) stock, no fork of 300",
    "S165-S0": "newgame -> (the COOPPARTY seed) -> 6603 -> encounters off -> the forced selftest role",
    "S165-P0": "the s165 keys in the agent's order (netsync.world ends r3/out/host/dot; netsync ends swap/saveguard/host, then "
               "s166's wire_peer on a v15 engine; world ends "
               "block_ready) and the proof line 'world follow selftest: OK (N rows, M mutants)', none FAIL",
}
SOLO_OUT = {
    "S165-RIDES": "the host riding ([190] 1): the guest waits on FieldHUD 6603, why 'riding', starts +0, the waits line",
    "S165-CHOCO": "the host calling Choco ([181] 1): waits, why 'choco_call'",
    "S165-EVENT": "the host on an event world ([102] 1 / 4 / 6 / 12): waits, why 'event_world' each",
    "S165-RANGE": "a [102] past 12 (no world this install has): waits, why 'idx_range'",
    "S165-ETB": "a line open on 6603 (Mogdrift's own talk): waits, why 'no_control' / 'line' / 'backlog' (term 6)",
    "S165-HOLD": "`worldfollow hold`: waits, why 'hold' (the START only)",
    "S165-DEBOUNCE": "THE LIVE DEBOUNCE: the frame with its heartbeat frozen (`host stale`, one request): why 'debounce', "
                     "debounce_ms < 1200 throughout, never a start",
    "S165-LEVER": "`worldfollow off`: waits, why 'lever'",
    "S165-SUPERSEDE": "a field intent inside the fade (`swap intent 300`, `swap delay` holding the commit): superseded +1 and its "
                      "line, the guest on FieldHUD 300, never on WorldHUD",
    "S165-LEAVE": "THE FIRST C# FIELD-TO-WORLD COMMIT: the frame at ICE_TILE (FieldEntrance 0) -> WorldHUD 9011, starts / commits / "
                  "lands +1, the start / commit / landed lines, no other field on the way",
    "S165-BLOCK": "THE PRE-INIT SAMPLE: world.block_ready true and world.ticks advancing on the landing's world",
    "S165-POSE": "...the walker at the fabricated pose (ICE_TILE within POSE_TOL), never WORLD11's default nor FS_LANDING; "
                 "out.last.frame 'latest'",
    "S165-ENTRANCE": "entrance 0 -> 35: entrance_fix +1, FieldEntrance 35",
    "S165-FOOT": "on foot: world.vehicle 0 and world.ctl 0",
    "S165-FROZEN": "frozen there (s144): `hold up` < HELD_U, freeze.on, freeze.edges +1 since the leave",
    "S165-ONFOOT": "the host mounted inside the guest's fade: the guest lands at the start pin's pose (ICE_TILE), on foot, "
                   "substituted +1",
}
SOLO_DOT = {
    "S165-DOT-HUD": "Select once (a New Game lands minimap-off): dot.hud 'HUD', the minimap on",
    "S165-DOT-SELF": "`host self`: the dot shown ON MY OWN ARROW (within 1 px), not at the edge, the donor census read",
    "S165-DOT-MARK": "`host 1197.3 -799.6`: the raw map point (0.620, 0.564)",
    "S165-DOT-EDGE": "`host 68 -444` (FS_LANDING, east of the Mist window): shown, edge true, the raw sx < 0 and px at the RIGHT edge",
    "S165-DOT-STALE": "`host stale`: why_not 'stale', hidden",
    "S165-DOT-NOB6": "`host nob6`: why_not 'no_b6', hidden",
    "S165-DOT-OTHER": "a host on 9002: why_not 'other_world', hidden",
    "S165-DOT-LEVER": "`dot off`: hidden, why_not 'lever', still wanted; `dot on`: shown",
}
SOLO_SAVE = {
    "S165-R3": "netsync.world.r3 at rest ('act', arms_from_9012 0) and its lever round trip; R3's truth table is P0's proof line",
    "S165-R4": "`savemenu` + a slot pick: refused +1, would_save +0, its reason and line; the save files unchanged",
    "S165-R4-DRY": "`saveguard old` (DRY): would_save +1 instead of refused (+0); the save files unchanged",
    "S165-R4-S": "`bench 0`: the S term alone (SuppressEncounters) still refuses: refused +1; the save files unchanged",
}
SOLO_FINAL = {
    "S165-R": "`reset` (a lever pulled just before it) releases the role and every worldfollow lever ('worldfollow levers released "
              "(with the harness)' once); re-read WITH the role: every lever at rest",
}
SECTION_ROWS = {"out": tuple(SOLO_OUT), "dot": tuple(SOLO_DOT), "save": tuple(SOLO_SAVE)}
SOLO_ALL = tuple(SOLO_SETUP) + ("S165-P1",) + tuple(SOLO_OUT) + tuple(SOLO_DOT) + tuple(SOLO_SAVE) + tuple(SOLO_FINAL)


def solo_catalog(calibrate: bool, sections=SECTIONS, lever=None) -> dict:
    c = dict(SOLO_SETUP)
    c["S165-P1"] = (f"`netsync bench 1` accepted and the CALIBRATION lever `{lever}` pulled and read back (held through the run)"
                    if calibrate and lever else
                    "`netsync bench 1` accepted (the field-gate bench on) and every lever at rest: out on, hold false, dot on, r3 act, "
                    "saveguard act")
    for sec in SECTIONS:
        if sec in sections:
            c.update({k: v for k, v in (SOLO_OUT, SOLO_DOT, SOLO_SAVE)[SECTIONS.index(sec)].items()})
    c.update(SOLO_FINAL)
    if calibrate:
        c["S165-CAL"] = ("CALIBRATION: the engine's stage decides the set -- before s165 exactly OLD_PREDICTED red, on s165 under the "
                         "pulled lever exactly LEVER_PREDICTED[lever] red")
    return c


#: [calibration] an engine before s165 (the deployed s164): every row the s165 keys or the verb carry
OLD_PREDICTED = tuple(c for c in SOLO_ALL if c not in ("S165-INI", "S165-OR", "S165-S0", "S165-R"))
#: [calibration] s165 under the lever pulled at P1 and held: exactly these red
LEVER_PREDICTED = {
    "out": tuple(c for c in SOLO_OUT if c != "S165-LEVER"),
    "dot": ("S165-DOT-SELF", "S165-DOT-EDGE"),
    "r3": ("S165-R3",),
    "saveguard": ("S165-R4", "S165-R4-S"),              # DRY: both act-lever rows count would_save, not refused (s164's gate saved them)
}
#: the stand-in's FAULT LEVERS (fakegame.WORLD_FOLLOW_FAULTS) -> exactly the SOLO rows each turns red (all sections; tests pin it)
SOLO_FAULT_REDS = {
    "proof_fail": ("S165-P0",),
    "never_starts": ("S165-SUPERSEDE", "S165-LEAVE", "S165-BLOCK", "S165-POSE", "S165-ENTRANCE", "S165-FOOT", "S165-FROZEN",
                     "S165-ONFOOT"),
    "wallclock_debounce": ("S165-DEBOUNCE",),
    "pose_exit": ("S165-POSE", "S165-ONFOOT"),
    "no_substitution": ("S165-ONFOOT",),
    "entrance_kept": ("S165-POSE", "S165-ENTRANCE"),
    "event_followed": ("S165-EVENT",),
    "rides_followed": ("S165-RIDES",),
    "choco_followed": ("S165-CHOCO",),
    "landing_free": ("S165-FROZEN",),
    "no_supersede": ("S165-SUPERSEDE",),
    "etb_ignored": ("S165-ETB",),
    "block_ready_dark": ("S165-BLOCK", "S165-POSE", "S165-ENTRANCE", "S165-FOOT", "S165-FROZEN", "S165-ONFOOT", "S165-DOT-SELF",
                         "S165-DOT-MARK", "S165-DOT-EDGE", "S165-DOT-STALE", "S165-DOT-NOB6", "S165-DOT-OTHER", "S165-DOT-LEVER"),
    "dot_dark": ("S165-DOT-SELF", "S165-DOT-EDGE", "S165-DOT-LEVER"),
    "dot_stale_shown": ("S165-DOT-STALE",),
    "dot_nob6_shown": ("S165-DOT-NOB6",),
    "dot_other_world": ("S165-DOT-OTHER",),
    "dot_no_edge": ("S165-DOT-EDGE",),
    "dot_lever_ignored": ("S165-DOT-LEVER",),
    "r3_old": (),                                          # the 9012 arm only: no solo row visits 9012 (R3 is lever + table here)
    "saveguard_open": ("S165-R4", "S165-R4-DRY", "S165-R4-S"),
    "saveguard_no_s": ("S165-R4-S",),
    "lever_stuck_wf": ("S165-R",),
    "host_lines_dark": (),                                 # the host's own lines: the duo's D-HOST
    "out_lever_ignored": ("S165-LEVER",),
    "hold_ignored": ("S165-HOLD",),
    "range_followed": ("S165-RANGE",),
}

# ---- T2
T2_COMMON = {
    "T2-TAPE": "the world-walk tape reads back and its six facts hold (_coop_peer_bench.world_walk_tape_facts)",
    "T2-PEER": f"port {PORT} free, the owner's bridge down; the guest config written (the engine's own config line); the "
               "replay-host listening, the guest connected, the replay started",
    "T2-SAVE": "THE PRECHECK: [SaveFile] AutoSaveOnlyAtMoogle off, and no 'session ended, no autosave to resume -> title screen' line",
    "T2-INI": "Memoria.ini restored byte-exact (sha256) after the run -- the install is shared",
}
T2_CHECKS = {
    "S165-WK-I": "the instrument: paired on 6603 + 'state-mirror ARMED' before the host's world exit, the guest on FieldHUD 6603; "
                 "on s165 `worldfollow hold` sent before the replay (never on an engine without netsync.world.out)",
    "S165-WK-WAIT": "the hold holds the START only: every sample on FieldHUD 6603 until the tape's host stands at the tile, out.why "
                    "'hold', out.hold true, the host cache b6",
    "S165-WK-LEAVE": "`release` -> WorldHUD 9011 within LEAVE_S, starts / commits / lands +1 (after block_ready + ticks)",
    "S165-WK-POSE": "the landing within POSE_TOL of the TAPE's own section-0 pose over the guest's seam bracket, >= FAR_U (plain) "
                    "from FS_LANDING; out.last.frame latest / pin",
    "S165-WK-FROZEN": "frozen there: `hold up` < HELD_U, freeze.on (live / mirroring)",
    "S165-WK-DOT": "Select once: the dot shown, host_x / host_z within DOT_TOL of the tape's own pose, its raw (sx, sy) that pose's",
    "S165-WK-REJOIN": "the tape's host enters 300: the guest rejoins 300 from the world map (lands +1, the landed line) + the "
                      "arrival guard's world clause",
}
T2_ROWS = tuple(T2_CHECKS)
T2_OLD_PREDICTED = ("S165-WK-WAIT", "S165-WK-LEAVE", "S165-WK-POSE", "S165-WK-FROZEN", "S165-WK-DOT", "S165-WK-REJOIN")
T2_LEVER_PREDICTED = {"out": ("S165-WK-WAIT", "S165-WK-LEAVE", "S165-WK-POSE")}
#: the stand-in faults -> exactly the T2 rows each turns red (the stub peer's smoke; tests pin a family each)
T2_FAULT_REDS = {"never_starts": ("S165-WK-LEAVE", "S165-WK-POSE"),
                 "pose_exit": ("S165-WK-POSE",),
                 "landing_free": ("S165-WK-FROZEN",),
                 "dot_dark": ("S165-WK-DOT",),
                 "hold_ignored": ("S165-WK-WAIT", "S165-WK-LEAVE")}   # it starts before the release: LEAVE reads it


def t2_catalog(calibrate: bool) -> dict:
    cat = {"T2-TAPE": T2_COMMON["T2-TAPE"], "T2-PEER": T2_COMMON["T2-PEER"]}
    cat.update(T2_CHECKS)
    if calibrate:
        cat["S165-WK-CAL"] = ("CALIBRATION: by the GUEST's stage -- before s165 exactly T2_OLD_PREDICTED red, on s165 under "
                              "`worldfollow off` exactly T2_LEVER_PREDICTED['out'] red")
    cat["T2-SAVE"] = T2_COMMON["T2-SAVE"]
    cat["T2-INI"] = T2_COMMON["T2-INI"]
    return cat


# ---- the duo
DUO_CHECKS = {
    "S165-D0": "the instrument: both on FieldHUD 6603, the guest mirroring",
    "S165-D-FO1": "the host walks out: the guest follows out to WorldHUD 9011 within FO_S, lands +1, at the host's own x/z (after "
                  "block_ready + ticks); the heartbeat witness and the landing gap reported",
    "S165-D-HOST": "the host's own two lines once each and netsync.host.world b6 true, wmapjumps +1",
    "S165-D-DOT": "Select once: the guest's dot at the host's own x/z (DOT_TOL) at the landing and after the host's teleport onto "
                  "ICE_TILE; the guest's own pose unmoved",
    "S165-D-REJOIN": "the host Confirms into 300: the guest rejoins 300 (+ the arrival guard's world clause), its dot never shown once "
                     "the host stood on 300 nor inside its own rejoin window",
    "S165-D-FO2": "both back on 6603; `hold`, the host out and onto ICE_TILE, `release`: the guest lands at ICE_TILE, >= FAR_U "
                  "(plain) from FS_LANDING",
    "S165-D-SHARED": "THE SHARED-FILE LAW (the instrument): no 'Sharing violation' / 'When importing FBX' in either game's log",
}
DUO_ORDER = tuple(DUO_CHECKS)
DUO_OLD_PREDICTED = ("S165-D-FO1", "S165-D-HOST", "S165-D-DOT", "S165-D-REJOIN", "S165-D-FO2")
DUO_FAULT_REDS = {"never_starts": ("S165-D-FO1", "S165-D-DOT", "S165-D-REJOIN", "S165-D-FO2"),
                  "host_lines_dark": ("S165-D-HOST",),
                  "dot_dark": ("S165-D-DOT",),
                  "pose_exit": ("S165-D-FO2",)}
SHARED_NEEDLES = ("Sharing violation", "When importing FBX")
#: duo.py's CLI calls ``d.pair(**PAIR)``: both games New Game onto 6603 (the host first), the roles from their own inis
PAIR = {"field": FARSHORE}


# ================================================================================================ pure readers / judges
def _o(x, key, default=None):
    """A ``netsync.world.out`` leaf (absent = ``default``: an engine before s165)."""
    return cb.path(x, "netsync.world.out." + key, default)


def _h(x, key, default=None):
    """A ``netsync.world.host`` leaf."""
    return cb.path(x, "netsync.world.host." + key, default)


def _d(x, key, default=None):
    """A ``netsync.world.dot`` leaf."""
    return cb.path(x, "netsync.world.dot." + key, default)


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _delta(a, b, dotted: str):
    """b's ``<dotted>`` - a's; None when either is unread (never a zero)."""
    va, vb = _num(cb.path(a, dotted)), _num(cb.path(b, dotted))
    return None if va is None or vb is None else vb - va


def odelta(a, b, key):
    return _delta(a, b, "netsync.world.out." + key)


def stage_of(x) -> int:
    """165 when the engine publishes `netsync.world.out`; 164 with s164's swap block; else coop_world_wait's reading."""
    if cb.has(x, PROBE):
        return 165
    if cb.has(x, "netsync.swap"):
        return 164
    return cw.stage_of(x)


def torus(a, b) -> float:
    return BW.world_torus_distance(a, b)


def plain(a, b) -> float:
    return cw.dist(a, b)


def world_xz(x) -> tuple:
    return cw.world_xz(x)


def judged(s) -> bool:
    """THE PRE-INIT SAMPLE's first half (PURE): a live WorldHUD sample whose blocks are in."""
    return s is not None and s.ui_state == "WorldHUD" and cb.path(s, "world.block_ready") is True


def first_judged(samples):
    """(PURE) The first sample with `world.block_ready` true on WorldHUD whose `world.ticks` ADVANCED by the next such sample -- the
    world landing's first judgeable sample -- else None."""
    live = [s for s in samples if judged(s) and _num(cb.path(s, "world.ticks")) is not None]
    for a, b in zip(live, live[1:]):
        if cb.path(b, "world.ticks") > cb.path(a, "world.ticks"):
            return a
    return None


def judge_probe(st, lines) -> tuple:
    """P0 (PURE): the s165 keys in the agent's order and the proof line OK (one combined table, or two), none FAIL."""
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}` -- an engine before s165"
    world = cb.path(st, "netsync.world") or {}
    ns = list(cb.path(st, "netsync") or {})
    wkeys = list(cb.raw(st).get("world") or {})
    blocks = {"r3": BW.WORLD_R3_SENTINELS, "out": BW.WORLD_OUT_SENTINELS, "host": BW.WORLD_HOST_SENTINELS,
              "dot": BW.WORLD_DOT_SENTINELS}
    bad = [k for k, want in blocks.items() if list(world.get(k) or {}) != list(want)]
    # [ff9mapkit netsync s166] BY THE ENGINE'S STAGE: an A2 engine (wire v15) appends `wire_peer` after `host` (the prefix law: s165's
    # keys unmoved, `wire_peer` netsync's LAST key)
    tail = list(BW.NETSYNC_TOP_KEYS_S165) + (list(BW.NETSYNC_TOP_KEYS_S166) if cb.has(st, "netsync.wire_peer") else [])
    top = ns[-len(tail):] == tail and "swap" in ns and ns.index("swap") == len(ns) - len(tail) - 1
    sg = list(cb.path(st, "netsync.saveguard") or {}) == list(BW.SAVEGUARD_SENTINELS)
    hw = list(cb.path(st, "netsync.host.world") or {}) == list(BW.HOST_WORLD_SENTINELS)
    # [ff9mapkit netsync s166] BY THE ENGINE'S STAGE: an s166 engine's `world` adds `kitcell` after `dot` (the prefix law: s165's unmoved)
    want_world = BW.WORLD_SENTINELS_S166 if cb.has(st, "netsync.world.kitcell") else BW.WORLD_SENTINELS_S165
    if cb.has(st, "netsync.world.pairpull"):
        want_world = BW.WORLD_SENTINELS_S166B   # [ff9mapkit netsync s166] A0b: `pairpull` after `kitcell` (the prefix law)
    keys_ok = (list(world) == list(want_world) and not bad and top and sg and hw
               and wkeys[-1:] == list(BW.WORLD_LIVE_KEYS_S165))
    rx = re.compile(BW.WORLD_FOLLOW_PROOF_RE)
    oks = [m for m in (rx.search(ln) for ln in lines) if m]
    follow = [m.group(0) for m in oks if m.group(1) == "follow"]
    dot = [m.group(0) for m in oks if m.group(1) == "dot"]
    fails = cb.count(lines, BW.PROOF_WORLD_FOLLOW + "FAIL") + cb.count(lines, BW.PROOF_WORLD_DOT + "FAIL")
    ok = keys_ok and bool(follow) and not fails
    return ok, (f"world {list(world)} (blocks off-shape {bad or 'none'}); netsync tail {ns[-3:]}; saveguard {sg}, host.world {hw}; "
                f"world tail {wkeys[-2:]}; proof {follow[:1] or 'NONE'}{(' + ' + dot[0]) if dot else ''}; FAIL lines {fails}")


def rest_levers(st) -> tuple:
    """The five levers' published words (PURE)."""
    return (_o(st, "lever"), _o(st, "hold"), _d(st, "lever"), cb.path(st, "netsync.world.r3.lever"),
            cb.path(st, "netsync.saveguard.lever"))


AT_REST = ("on", False, "on", "act", "act")
#: each calibration lever: the op that pulls it, the one that releases it, and how its word reads pulled
LEVER_OPS = {"out": (("off",), ("on",), lambda st: _o(st, "lever") == "off"),
             "dot": (("dot", "off"), ("dot", "on"), lambda st: _d(st, "lever") == "off"),
             "r3": (("r3", "old"), ("r3", "act"), lambda st: cb.path(st, "netsync.world.r3.lever") == "old"),
             "saveguard": (("saveguard", "old"), ("saveguard", "act"), lambda st: cb.path(st, "netsync.saveguard.lever") == "old")}


def judge_rest(st) -> tuple:
    """P1 (PURE): the bench on and every lever at rest."""
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}` (the levers' keys)"
    got = rest_levers(st)
    bench = cb.path(st, "netsync.bench")
    return got == AT_REST and bench is True, f"levers {got} (want {AT_REST}); netsync.bench {bench!r}"


def judge_refusal(base, samples, lines, want, *, logged: bool = True, field: int = FARSHORE) -> tuple:
    """A refusal row (PURE): every sample on FieldHUD ``field``; the last one's `out.why` among ``want`` (the engine's tokens),
    `out.starts` +0 since ``base``, the host cache reading the fabricated frame (b6); with ``logged`` a 'waits:' line in ``lines``."""
    if not samples:
        return False, "not reached: no sample after the frame"
    if not cb.has(samples[-1], PROBE):
        return False, f"absent: no `{PROBE}`"
    off = [(s.ui_state, s.field_id) for s in samples if not (s.ui_state == "FieldHUD" and s.field_id == field)]
    last = samples[-1]
    why, ds = _o(last, "why"), odelta(base, last, "starts")
    b6 = any(_h(s, "b6") is True for s in samples)
    n = cb.count(lines, BW.LOG_WORLD_OUT_WAITS)
    ok = not off and why in tuple(want) and ds == 0 and b6 and (n >= 1 or not logged)
    return ok, (f"{len(samples)} sample(s): " + (f"LEFT FieldHUD {field}: {off[:3]}" if off else f"all FieldHUD {field}")
                + f"; why {why!r} (want {' / '.join(want)}); starts +{ds}; host cache b6 {'read' if b6 else 'NEVER read'}; "
                f"the waits line {n}x" + ("" if logged else " (not required)"))


def judge_debounce(base, samples) -> tuple:
    """DEBOUNCE (PURE): the frame read (b6), its heartbeat frozen -- why 'debounce' on the last sample, `debounce_ms` below the seed on
    EVERY sample (a frozen heartbeat never counts), never a start, every sample on FieldHUD 6603."""
    ok, why = judge_refusal(base, samples, (), ("debounce",), logged=False)
    acc = [_num(_o(s, "debounce_ms")) for s in samples]
    top = max((a for a in acc if a is not None), default=None)
    held = top is not None and top < DEBOUNCE_MS
    return ok and held, f"{why}; debounce_ms max {top} (want < {DEBOUNCE_MS} on every sample)"


def judge_supersede(base, samples, lines, *, dest: int = INTENT_DEST) -> tuple:
    """SUPERSEDE (PURE): `superseded` +1 and its line, a FieldHUD sample on ``dest``, NO WorldHUD sample, the world-out idle at the
    end."""
    if not samples:
        return False, "not reached: no sample after the intent"
    last = samples[-1]
    dsup = odelta(base, last, "superseded")
    world = [cb.raw(s).get("frame") for s in samples if s.ui_state == "WorldHUD"]
    on = any(s.ui_state == "FieldHUD" and s.field_id == dest for s in samples)
    n = cb.count(lines, BW.LOG_WORLD_OUT_SUPERSEDED)
    ok = dsup == 1 and n >= 1 and on and not world and _o(last, "state") in ("idle", "waiting")
    return ok, (f"superseded +{dsup} (want 1), its line {n}x; FieldHUD {dest} {'reached' if on else 'NEVER reached'}; WorldHUD on "
                f"{len(world)} sample(s) (want none); out.state {_o(last, 'state')!r} at the end")


def judge_leave(base, samples, lines, *, wld: int = WORLD, src: int = FARSHORE) -> tuple:
    """LEAVE (PURE): a WorldHUD ``wld`` sample, starts / commits / lands +1 since ``base``, the three lines, and no field but ``src``
    on any sample (the commit wrote the world, never a field)."""
    if not samples:
        return False, "not reached: no sample after the frame"
    last = samples[-1]
    d = {k: odelta(base, last, k) for k in ("starts", "commits", "lands")}
    on = any(s.ui_state == "WorldHUD" and s.world_id == wld for s in samples)
    other = sorted({s.field_id for s in samples if s.ui_state == "FieldHUD" and s.field_id != src})
    n = {k: cb.count(lines, v) for k, v in (("start", BW.LOG_WORLD_OUT_START), ("commit", BW.LOG_WORLD_OUT_COMMIT),
                                            ("landed", BW.LOG_WORLD_OUT_LANDED + str(wld)))}
    ok = on and all(v == 1 for v in d.values()) and all(v >= 1 for v in n.values()) and not other
    return ok, (f"WorldHUD {wld} {'reached' if on else 'NEVER reached'}; starts/commits/lands +{d['starts']}/+{d['commits']}/"
                f"+{d['lands']} (want 1 each); lines start {n['start']}x commit {n['commit']}x landed {n['landed']}x"
                + (f"; ANOTHER FIELD on the way: {other}" if other else ""))


def judge_block(samples) -> tuple:
    """BLOCK (PURE): THE PRE-INIT SAMPLE -- a WorldHUD sample with block_ready true and world.ticks advancing past it."""
    j = first_judged(samples)
    br = [cb.path(s, "world.block_ready") for s in samples if s.ui_state == "WorldHUD"]
    return j is not None, (f"{len(br)} WorldHUD sample(s), block_ready {sorted(set(map(repr, br)))}; "
                           + (f"judged at world.ticks {cb.path(j, 'world.ticks')}" if j is not None else
                              "no sample with the blocks in and the world ticking (not judged)"))


def judge_pose(st, want, *, frame_words=("latest",), far_from=FS_LANDING, default=WORLD11_DEFAULT) -> tuple:
    """POSE (PURE): ``st`` (the first judged sample) within POSE_TOL (torus) of ``want``, >= DEFAULT_MIN_U from ``default``, >= FAR_U
    (PLAIN) from ``far_from`` (the torus distance reported beside it); `out.last.frame` among ``frame_words``."""
    if st is None:
        return False, "not judged: no sample with the blocks in and the world ticking"
    x, z = world_xz(st)
    if x is None:
        return False, "not reached: no world position on the judged sample"
    d, dd, df, tf = torus((x, z), want), plain((x, z), default), plain((x, z), far_from), torus((x, z), far_from)
    last = _o(st, "last") or {}
    ok = d <= POSE_TOL and dd >= DEFAULT_MIN_U and df >= FAR_U and last.get("frame") in frame_words
    return ok, (f"at ({x:.1f}, {z:.1f}): {d:.1f}u from {tuple(want)} (want <= {POSE_TOL:g}), {dd:.1f}u from WORLD11's default (>= "
                f"{DEFAULT_MIN_U:g}), {df:.0f}u plain / {tf:.0f}u torus from FS_LANDING (plain >= {FAR_U:g}); out.last {last}")


def judge_entrance(base, st) -> tuple:
    """ENTRANCE (PURE): entrance_fix +1, FieldEntrance 35."""
    if st is None:
        return False, "not judged: no judged world sample"
    de = odelta(base, st, "entrance_fix")
    fe = st.field_entrance
    return de == 1 and fe == BW.POSITION_PRESET_KEY, f"entrance_fix +{de} (want 1); FieldEntrance {fe} (want 35)"


def judge_foot(st) -> tuple:
    """FOOT (PURE): world.vehicle 0 and world.ctl 0."""
    if st is None:
        return False, "not judged: no judged world sample"
    v, c = st.vehicle, st.world_ctl
    return v == 0 and c == 0, f"world.vehicle {v} ([190]), world.ctl {c} (want 0 / 0: on foot)"


def judge_frozen_here(base, st, moved, advanced) -> tuple:
    """FROZEN (PURE): the hold held, freeze.on, freeze.edges +1 since ``base``."""
    w_ok, w_why = cw.judge_walk(moved, advanced, WALK_FRAMES, held=True)
    on = cb.path(st, "netsync.world.freeze.on") if st is not None else None
    de = _delta(base, st, "netsync.world.freeze.edges")
    return w_ok and on is True and de == 1, f"{w_why}; freeze.on {on!r}, edges +{de} (want 1)"


def judge_onfoot(base, st, want) -> tuple:
    """ONFOOT (PURE): substituted +1, at the start pin's pose ``want`` (POSE_TOL), on foot."""
    if st is None:
        return False, "not judged: no judged world sample"
    x, z = world_xz(st)
    if x is None:
        return False, "not reached: no world position"
    ds = odelta(base, st, "substituted")
    d = torus((x, z), want)
    ok = ds == 1 and d <= POSE_TOL and st.vehicle == 0 and st.world_ctl == 0
    return ok, (f"substituted +{ds} (want 1); at ({x:.1f}, {z:.1f}) {d:.1f}u from the pin {tuple(want)}; vehicle {st.vehicle} ctl "
                f"{st.world_ctl}; out.last {_o(st, 'last')}")


def judge_hud(st) -> tuple:
    hud, mm = _d(st, "hud"), _d(st, "minimap")
    return hud == "HUD" and mm is True, f"dot.hud {hud!r} (want 'HUD'), minimap {mm!r}"


def judge_dot_self(d: dict) -> tuple:
    """DOT-SELF (PURE over a `netsync.world.dot` block): shown, no refusal, on my own arrow within DOT_PX_TOL, not at the edge, the
    census read."""
    px, py, ox, oy = (_num(d.get(k)) for k in ("px", "py", "own_px", "own_py"))
    near = None not in (px, py, ox, oy) and abs(px - ox) <= DOT_PX_TOL and abs(py - oy) <= DOT_PX_TOL
    ok = d.get("shown") is True and d.get("why_not") is None and near and d.get("edge") is False and d.get("census") is not None
    return ok, (f"shown {d.get('shown')!r}, why_not {d.get('why_not')!r}, edge {d.get('edge')!r}; px/py {px}/{py} vs my arrow "
                f"{ox}/{oy} (within {DOT_PX_TOL:g} px); census {'read' if d.get('census') is not None else 'NONE'}")


def judge_dot_mark(d: dict, want=DOT_MARK_SXSY, host=DOT_MARK) -> tuple:
    """DOT-MARK (PURE): the raw map point (sx, sy) within SXSY_TOL of ``want``, the host cache at ``host``; still wanted."""
    sx, sy = _num(d.get("sx")), _num(d.get("sy"))
    hx, hz = _num(d.get("host_x")), _num(d.get("host_z"))
    ok = (sx is not None and sy is not None and abs(sx - want[0]) <= SXSY_TOL and abs(sy - want[1]) <= SXSY_TOL
          and hx is not None and hz is not None and plain((hx, hz), host) <= 1.0 and d.get("want") is True)
    return ok, f"sx/sy {sx}/{sy} (want {want} within {SXSY_TOL}); host {hx}/{hz}; want {d.get('want')!r}"


def edge_width(mark: dict) -> float | None:
    """The minimap's width off DOT-MARK's own placement (PURE): px / sx (a clamped sx in (0, 1) is the raw one)."""
    px, sx = _num((mark or {}).get("px")), _num((mark or {}).get("sx"))
    return px / sx if px is not None and sx else None


def judge_dot_edge(d: dict, width) -> tuple:
    """DOT-EDGE (PURE): shown, edge true, the raw sx < 0 (the raw map put the host far LEFT), px at the RIGHT edge (``width``)."""
    px, sx = _num(d.get("px")), _num(d.get("sx"))
    if width is None:
        return False, "not judged: no minimap width (DOT-MARK's px / sx unread)"
    right = px is not None and abs(px - width) <= EDGE_PX_TOL
    ok = d.get("shown") is True and d.get("edge") is True and sx is not None and sx < 0 and right
    return ok, (f"shown {d.get('shown')!r}, edge {d.get('edge')!r}; raw sx {sx} (want < 0); px {px} vs the right edge {width:.1f} "
                f"(within {EDGE_PX_TOL:g})")


def judge_dot_hidden(d: dict, want: str) -> tuple:
    """DOT-STALE / NOB6 / OTHER (PURE): why_not ``want``, hidden. The sampler waits for BOTH (the first s165 solo bench: `why_not` is
    the live verdict, `shown` the last drawn frame, so a time-based flip -- stale -- read once on the frame it crossed showed the dot
    still up; a dot that never hides still times out red)."""
    return d.get("why_not") == want and d.get("shown") is False, (f"why_not {d.get('why_not')!r} (want {want!r}), shown "
                                                                   f"{d.get('shown')!r}")


def judge_dot_lever(off: dict, on: dict | None) -> tuple:
    """DOT-LEVER (PURE): under `dot off` hidden, why_not 'lever', still wanted; after `dot on` shown (``on`` None = not re-read: the
    calibration holds the lever)."""
    o_ok = off.get("shown") is False and off.get("why_not") == "lever" and off.get("want") is True
    n_ok = True if on is None else on.get("shown") is True
    return o_ok and n_ok, (f"off: shown {off.get('shown')!r} why_not {off.get('why_not')!r} want {off.get('want')!r}; on: "
                           + ("not re-read (the calibration holds `dot off`)" if on is None else f"shown {on.get('shown')!r}"))


def judge_r3(st0, old, act) -> tuple:
    """R3 (PURE): at rest 'act' with no arm from 9012; `r3 old` reads 'old'; `r3 act` reads 'act' again."""
    r0, ro, ra = (cb.path(s, "netsync.world.r3") or {} for s in (st0, old, act))
    ok = r0.get("lever") == "act" and r0.get("arms_from_9012") == 0 and ro.get("lever") == "old" and ra.get("lever") == "act"
    return ok, f"at rest {r0}; under `r3 old` {ro.get('lever')!r}; after `r3 act` {ra.get('lever')!r}"


def judge_save(sg0: dict, sg1: dict, lines, files0, files1, *, dry: bool, logged: bool = False, hud_back: bool = True) -> tuple:
    """R4 / R4-DRY / R4-S (PURE): refused +1 and would_save +0, or (``dry``) refused +0 and would_save +1 -- the engine counts a DRY
    would-save INSTEAD of a refusal (NetSyncField.ManualSaveRefusedNow; BW.save_guard_step) -- a reason, the line (``logged``: once
    per place per process, so only the first row requires it), the save files unchanged (mtime / size), back on the HUD."""
    if not sg1:
        return False, "absent: no `netsync.saveguard`"
    dr = (sg1.get("refused") or 0) - (sg0.get("refused") or 0)
    dw = (sg1.get("would_save") or 0) - (sg0.get("would_save") or 0)
    n = cb.count(lines, BW.LOG_SAVE_REFUSED)
    same = files0 is not None and files0 == files1
    want_r, want_w = (0, 1) if dry else (1, 0)
    ok = dr == want_r and dw == want_w and bool(sg1.get("last_why")) and (n >= 1 or not logged) and same and hud_back
    return ok, (f"refused +{dr} (want {want_r}), would_save +{dw} (want {want_w}), last_why {sg1.get('last_why')!r}; the refusal "
                f"line {n}x" + ("" if logged else " (once per place: not required)") + "; save files "
                + ("UNCHANGED" if same else ("UNREAD" if files0 is None else "CHANGED")) + f"; back on the HUD {hud_back}")


def save_files(st) -> dict | None:
    """The save sandbox's files {name: (mtime_ns, size)} (None when no sandboxed save path is published: R4 never runs there)."""
    sp = cb.raw(st).get("save_path")
    if not sp or cb.raw(st).get("save_sandboxed") is not True:
        return None
    d = Path(str(sp)).parent
    try:
        return {p.name: (p.stat().st_mtime_ns, p.stat().st_size) for p in sorted(d.iterdir()) if p.is_file()}
    except OSError:
        return None


def tape_t(wall, start_wall, t0, speed=None):
    """(PURE) The tape second the replay had reached at ``wall`` (its own anchor: ``start_wall`` <-> tape ``t0``), None when unread."""
    if wall is None or start_wall is None or t0 is None:
        return None
    return float(t0) + (wall - start_wall).total_seconds() * float(speed or REPLAY_SPEED)


def tape_poses_in(rows, lo: float, hi: float) -> list:
    """(PURE) The tape's b6 section-0 poses (x, z) with tape seconds in [lo, hi]."""
    return [(r["pose"]["x"], r["pose"]["z"]) for r in rows
            if r.get("b6") and r.get("pose") is not None and lo <= r["t"] <= hi]


def judge_tape_pose(st, rows, bracket, *, frame_words=("latest", "pin")) -> tuple:
    """WK-POSE (PURE): the judged landing ``st`` within POSE_TOL (torus) of a tape pose over the seam ``bracket`` (tape seconds, lo /
    hi, widened by half a second each side), >= FAR_U (plain) from FS_LANDING, `out.last.frame` among ``frame_words``."""
    if st is None:
        return False, "not judged: the guest never stood on a judged world sample"
    if bracket is None or None in bracket:
        return False, "not judged: no seam bracket on the tape clock (the landing's samples or the replay anchor unread)"
    x, z = world_xz(st)
    if x is None:
        return False, "not reached: no world position"
    lo, hi = bracket[0] - 0.5, bracket[1] + 0.5
    pts = tape_poses_in(rows, lo, hi)
    if not pts:
        return False, f"no tape b6 pose in tape [{lo:.2f}, {hi:.2f}] s (the seam fell outside the host's world frames)"
    d = min(torus((x, z), p) for p in pts)
    df = plain((x, z), FS_LANDING)
    last = _o(st, "last") or {}
    ok = d <= POSE_TOL and df >= FAR_U and last.get("frame") in frame_words
    return ok, (f"at ({x:.1f}, {z:.1f}): {d:.1f}u from the tape's pose over [{lo:.2f}, {hi:.2f}] s ({len(pts)} frame(s); want <= "
                f"{POSE_TOL:g}); {df:.0f}u plain from FS_LANDING (>= {FAR_U:g}); out.last {last}")


def judge_dot_track(d: dict, pts, mapno) -> tuple:
    """WK-DOT / D-DOT (PURE): shown, host_x / host_z within DOT_TOL of one of ``pts`` (the host's own pose near the sample), and --
    ``mapno`` given -- the raw (sx, sy) that pose's navi_get_pos within SXSY_TOL."""
    hx, hz = _num(d.get("host_x")), _num(d.get("host_z"))
    if hx is None or not pts:
        return False, f"host_x/z {hx}/{hz}; {len(pts or [])} reference pose(s)"
    near = min(pts, key=lambda p: torus((hx, hz), p))
    dd = torus((hx, hz), near)
    ok = d.get("shown") is True and dd <= DOT_TOL
    why = f"shown {d.get('shown')!r}; host {hx:.1f}/{hz:.1f} {dd:.1f}u from the host's own {tuple(round(v, 1) for v in near)}"
    if mapno is not None:
        wx, wy = BW.navi_get_pos(near[0], near[1], int(mapno))
        sx, sy = _num(d.get("sx")), _num(d.get("sy"))
        m_ok = sx is not None and sy is not None and abs(sx - wx) <= SXSY_TOL * 4 and abs(sy - wy) <= SXSY_TOL * 4
        ok = ok and m_ok
        why += f"; sx/sy {sx}/{sy} vs {wx:.3f}/{wy:.3f}"
    return ok, why


def judge_shared(host_lines, guest_lines) -> tuple:
    """D-SHARED (PURE): no shared-file read failure in either game's log -- the INSTRUMENT (THE SHARED-FILE LAW)."""
    hits = [(who, ln) for who, lines in (("host", host_lines), ("guest", guest_lines)) for ln in lines
            if any(n in ln for n in SHARED_NEEDLES)]
    return not hits, ("no shared-file failure in either log" if not hits else
                      f"the INSTRUMENT (THE SHARED-FILE LAW, never an engine verdict): {hits[:2]}")


def hb_resumed_before(samples, t_commit) -> tuple:
    """D-FO1's heartbeat witness (PURE over (wall, state) samples): after the host's b6 rose (the guest's host cache b6), a stalled
    heartbeat (hb_age_ms > the alive window) followed by a moving one again, both before ``t_commit`` -> (resumed: True | False |
    None = no stall sampled, why)."""
    rows = [(t, _num(_h(s, "hb_age_ms"))) for t, s in samples if _h(s, "b6") is True and (t_commit is None or t <= t_commit)]
    stall = next((i for i, (_t, a) in enumerate(rows) if a is not None and a > BW.WORLD_OUT_ALIVE_MS), None)
    if stall is None:
        return None, f"no stalled heartbeat sampled before the commit ({len(rows)} b6 sample(s))"
    back = next(((t, a) for t, a in rows[stall:] if a is not None and 0 <= a <= BW.WORLD_OUT_ALIVE_MS), None)
    if back is None:
        return False, f"the heartbeat stalled at {rows[stall][0]:%H:%M:%S.%f} and never moved again before the commit"
    return True, f"the heartbeat stalled at {rows[stall][0]:%H:%M:%S.%f} and moved again at {back[0]:%H:%M:%S.%f}, before the commit"


# ================================================================================================ the moves
class Tap(threading.Thread):
    """A session's publishes on a thread, wall-stamped, while the main thread drives the OTHER game (its walk blocks): distinct frames;
    a read that fails is skipped. Nothing else reads this session while it runs."""

    def __init__(self, g, period: float = 0.04):
        super().__init__(daemon=True)
        self.g, self.period, self.halt, self.samples, self._seen = g, period, threading.Event(), [], None

    def run(self) -> None:
        while not self.halt.is_set():
            try:
                st = self.g.state
            except HarnessError:
                st = None
            if st is not None and st.frame != self._seen:
                self._seen = st.frame
                self.samples.append((_dt.datetime.now(), st))
            time.sleep(self.period)

    def stop(self) -> list:
        self.halt.set()
        self.join(5.0)
        return list(self.samples)


def _wf(g, *args) -> tuple:
    """`netsync worldfollow <args>` (ok, why) -- callers PROBE first: never sent to an engine without `netsync.world.out`."""
    return cb.try_ns(g, "worldfollow", *args)


def _watch(g, seconds: float, until=None) -> list:
    samples, _ = cb.watch(g, until or (lambda s: False), seconds)
    return samples or [g.state]


def _host_off(g) -> None:
    ok, why = _wf(g, "host", "off")
    if not ok:
        g.note(f"`worldfollow host off` refused: {why[:160]}")
    g.wait_frames(6)


def _home(g, ctx: dict) -> bool:
    """Back on FieldHUD 6603 with the bench host off (a row that left it: a fault, a follow-out, a supersede). A world-out still in its
    fade or committed is waited out first -- past the point of no return only a load ends it (s42), so a row that started one (a
    fault) must never hand the next row a fade in flight."""
    _host_off(g)
    if _o(g.state, "state") in ("fading", "committed"):
        cb.poll(g, lambda s: _o(s, "state") not in ("fading", "committed") and s.ui_state in ("WorldHUD", "FieldHUD"), LEAVE_S,
                "the world-out in flight to end")
        g.wait_frames(SETTLE_FRAMES)
    st = g.state
    if st.ui_state == "FieldHUD" and st.field_id == FARSHORE:
        return True
    try:
        if st.ui_state == "WorldHUD":
            g.world_warp(FARSHORE)
        else:
            g.warp(FARSHORE)
    except HarnessError as err:
        g.note(f"the way home to {FARSHORE} failed: {str(err)[:200]}")
    st = cb.poll(g, lambda s: s.ui_state == "FieldHUD" and s.field_id == FARSHORE and s.control, HOME_S, "home on 6603")
    g.wait_frames(SETTLE_FRAMES)
    return st is not None


def _keeper_uid(g) -> int | None:
    """Mogdrift's object uid on 6603: the talk object nearest KEEPER_AT in `objects`, else None."""
    objs = g.state.objects or []
    near = sorted(((o.get("x", 0.0) - KEEPER_AT[0]) ** 2 + (o.get("z", 0.0) - KEEPER_AT[1]) ** 2, o) for o in objs
                  if isinstance(o, dict) and o.get("talk") is True and isinstance(o.get("uid"), int))
    return int(near[0][1]["uid"]) if near and near[0][0] <= KEEPER_NEAR ** 2 else None


def _close_line(g) -> None:
    for _ in range(14):
        st = g.state
        if not st.dialog_open:
            return
        if st.choice is not None:
            try:
                g.choose(int(st.choice.get("count", 1)) - 1)
                continue
            except HarnessError:
                pass
        g.press("confirm", 4)
        g.wait_frames(12)


def _on_world(g, ctx: dict) -> bool:
    """The world map for a row that needs it: there already, else -- the bench host off -- the guest's own walk out from 6603."""
    if g.state.ui_state == "WorldHUD":
        return True
    _host_off(g)
    if not (g.state.ui_state == "FieldHUD" and g.state.field_id == FARSHORE):
        _home(g, ctx)
    ok, why, _st = cw.walk_out(g)
    g.note(f"the world map by the guest's OWN walk out: {ok} ({why[:160]})")
    return ok


def _cal_restore(g, ctx: dict, lever: str) -> None:
    """A row that exercised the calibration's own lever puts it back as the calibration holds it."""
    if ctx.get("pulled") == lever:
        _wf(g, *LEVER_OPS[lever][0])


# ================================================================================================ the run
def run(g, field: int | None = None):
    leg = LEG
    if leg is None:
        led = cb.Ledger(g, {"T2-TAPE": T2_COMMON["T2-TAPE"]})
        led.check("T2-TAPE", False, f"COOP_WF_LEG={_RAW_LEG!r} is no leg: one of {LEGS}")
        return
    if field is not None and field != FARSHORE:
        g.note(f"--field {field} is ignored: the bench runs on {FARSHORE} and the world map")
    if leg == "solo":
        _run_solo(g)
    else:
        _run_walk(g)


# ---------------------------------------------------------------------------------------------- SOLO
def _run_solo(g) -> None:
    calibrate = cb.CALIBRATE
    sections = SOLO_SECTIONS or SECTIONS
    led = cb.Ledger(g, solo_catalog(calibrate, sections, LEVER), finals=("S165-R", "S165-CAL"), width=DETAIL_W)
    ctx = {"calibrate": calibrate, "stage": None, "pulled": None, "sections": sections, "mark": None}
    try:
        _solo(g, led, ctx)
    except HarnessError as err:
        g.note(f"the solo leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'world-follow-solo')}")
        led.close()
        _release_solo(g, led, ctx)
        if calibrate:
            stage = ctx.get("stage")
            if stage is None:
                led.check("S165-CAL", False, "no engine stage was read (the run died before P0)")
            else:
                pred = OLD_PREDICTED if stage < 165 else LEVER_PREDICTED.get(LEVER or "", ())
                g.note(f"S165-CAL: s{stage}, lever {LEVER!r}: predicted reds {sorted(set(pred) & set(led.catalog))}")
                led.judge_calibration("S165-CAL", [c for c in pred if c in led.catalog])
        led.close(final=True)


def _ini_ok(g) -> tuple:
    en, fh = cb.ini_value(g, "Netsync", "Enabled"), cb.ini_value(g, "Netsync", "FollowHost")
    off = en is None or str(en).strip() in ("0", "")
    follow = fh is not None and str(fh).strip() == "1"
    return off and follow, (f"[Netsync] Enabled {en!r}, FollowHost {fh!r}"
                            + ("" if off else " -- the selftest role needs Enabled off (selftest_block.sh)")
                            + ("" if follow else " -- the fabricated host needs FollowHost 1 (its gate: SuppressEncounters)"))


def _solo(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why = _ini_ok(g)
    led.check("S165-INI", ok, why)
    if not ok:
        led.close("the install's ini refuses the bench (S165-INI)")
        return
    oracle = cw.read_oracle(Path(g.game_path))
    led.check("S165-OR", not oracle["problems"], f"problems {oracle['problems'] or 'none'}; read {oracle['facts']}")
    ok, why = cb.setup(g, FARSHORE, label="s165: world-map co-op, the guest follows the host out -- the solo bench"
                                          + (" -- CALIBRATION" if ctx["calibrate"] else ""))
    led.check("S165-S0", ok and g.state.field_id == FARSHORE, why + f"; on field {g.state.field_id}")
    if not ok:
        led.close(f"the selftest role never came up -- {why}")
        return
    st = g.state
    ctx["stage"] = stage_of(st)
    g.note(f"engine stage: s{ctx['stage']} ({cb.stage_note(st)})")
    led.check("S165-P0", *judge_probe(st, cb.log_lines(g)))
    _p1(g, led, ctx)
    if ctx["stage"] < 165:
        g.note(f"s{ctx['stage']}: no `{PROBE}` -- no `worldfollow` op and no `savemenu` is EVER sent (s164 fails the sub-verb closed)")
        led.close(f"not reached: an engine before s165 (no `{PROBE}`): nothing new is sent")
        return
    if "out" in ctx["sections"]:
        _section_out(g, led, ctx)
    if "dot" in ctx["sections"]:
        _section_dot(g, led, ctx)
    if "save" in ctx["sections"]:
        _section_save(g, led, ctx)


def _p1(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why = cb.try_ns(g, "bench", 1)
    st = cb.poll(g, lambda s: (s.netsync or {}).get("bench") is True, 3.0, "the field-gate bench") or g.state
    if not ok:
        led.check("S165-P1", False, f"`netsync bench 1` refused: {why}")
        return
    if ctx["stage"] < 165:
        led.check("S165-P1", *judge_rest(st))
        return
    if ctx["calibrate"] and LEVER:
        pull, _rel, read = LEVER_OPS[LEVER]
        okl, whyl = _wf(g, *pull)
        st = cb.poll(g, read, 3.0, f"the calibration lever {LEVER}") or g.state
        ctx["pulled"] = LEVER if okl else None
        led.check("S165-P1", okl and read(st), whyl or f"`worldfollow {' '.join(pull)}` pulled: levers {rest_levers(st)}")
        g.note(f"CALIBRATION: `worldfollow {' '.join(pull)}` pulled -- held through the run")
        return
    led.check("S165-P1", *judge_rest(st))


# ---- OUT
def _frame(g, *args) -> tuple:
    """One fabricated host frame: `worldfollow host <args>`; (ok, why)."""
    return _wf(g, "host", *[f"{a:g}" if isinstance(a, float) else str(a) for a in args])


def _refusal_row(g, led, ctx, cid, args, want, *, logged=True, setup=None, teardown=None) -> None:
    if not _home(g, ctx):
        led.check(cid, False, "not reached: the guest is not on FieldHUD 6603")
        return
    base, at = g.state, cb.mark(g)
    try:
        if setup is not None:
            pre = setup()
            if pre is not None:
                led.check(cid, False, pre)
                return
        ok, why = _frame(g, *args)
        if not ok:
            led.check(cid, False, f"`worldfollow host {' '.join(map(str, args))}` refused: {why}")
            return
        samples = _watch(g, REFUSE_S)
        led.check(cid, *judge_refusal(base, samples, cb.new(g, at), want, logged=logged))
    finally:
        _host_off(g)
        if teardown is not None:
            try:
                teardown()
            except HarnessError as err:
                g.note(f"{cid}: its teardown raised: {str(err)[:160]}")
        _home(g, ctx)


def _etb_setup(g, ctx):
    def setup():
        uid = _keeper_uid(g)
        if uid is None:
            return "not reached: the keeper (Mogdrift) is not among the published talk objects near " + str(KEEPER_AT)
        ok, why = cb.try_ns(g, "talk", uid)
        if not ok:
            return f"not reached: `netsync talk {uid}` refused: {why}"
        if cb.poll(g, lambda s: s.dialog_open, 4.0, "the keeper's line") is None:
            return f"not reached: the keeper's line never opened (uid {uid}) -- the instrument"
        return None
    return setup


def _section_out(g, led: cb.Ledger, ctx: dict) -> None:
    tile = ICE_TILE
    _refusal_row(g, led, ctx, "S165-RIDES", (*tile, 11, RIDE_MODE), ("riding",))
    _refusal_row(g, led, ctx, "S165-CHOCO", (*tile, 11, 0, BW.POSITION_PRESET_KEY, CHOCO_VEG), ("choco_call",))
    _event_row(g, led, ctx)
    _refusal_row(g, led, ctx, "S165-RANGE", (*tile, RANGE_IDX), ("idx_range",))
    _refusal_row(g, led, ctx, "S165-ETB", tile, ("no_control", "line", "backlog"), setup=_etb_setup(g, ctx),
                 teardown=lambda: _close_line(g))
    _refusal_row(g, led, ctx, "S165-HOLD", tile, ("hold",), logged=False, setup=lambda: (_wf(g, "hold"), None)[1],
                 teardown=lambda: _wf(g, "release"))
    _debounce_row(g, led, ctx)
    _refusal_row(g, led, ctx, "S165-LEVER", tile, ("lever",), logged=False, setup=lambda: (_wf(g, "off"), None)[1],
                 teardown=lambda: (_wf(g, "on") if ctx.get("pulled") != "out" else None))
    _supersede_row(g, led, ctx)
    _leave_rows(g, led, ctx)
    _onfoot_row(g, led, ctx)


def _event_row(g, led: cb.Ledger, ctx: dict) -> None:
    parts, ok_all = [], True
    for idx in EVENT_IDXS:
        if not _home(g, ctx):
            ok_all = False
            parts.append(f"[102] {idx}: not reached (not home)")
            continue
        base, at = g.state, cb.mark(g)
        ok, why = _frame(g, *ICE_TILE, idx)
        if not ok:
            ok_all = False
            parts.append(f"[102] {idx}: the frame refused ({why[:80]})")
            _host_off(g)
            continue
        samples = _watch(g, REFUSE_S)
        r_ok, r_why = judge_refusal(base, samples, cb.new(g, at), ("event_world",))
        ok_all = ok_all and r_ok
        parts.append(f"[102] {idx} (world {BW.WORLD_BASE + idx}): {'ok' if r_ok else 'RED'} -- {r_why[:160]}")
        _host_off(g)
    _home(g, ctx)
    led.check("S165-EVENT", ok_all, " | ".join(parts))


def _debounce_row(g, led: cb.Ledger, ctx: dict) -> None:
    if not _home(g, ctx):
        led.check("S165-DEBOUNCE", False, "not reached: the guest is not on FieldHUD 6603")
        return
    base = g.state
    try:
        # ONE request: the agent's queue runs the two steps Block(2) frames apart -- no driver round trip lets the heartbeat count
        g.send(f"netsync worldfollow host {ICE_TILE[0]:g} {ICE_TILE[1]:g}", "netsync worldfollow host stale")
    except HarnessError as err:
        led.check("S165-DEBOUNCE", False, f"the frame + `host stale` refused: {str(err)[:200]}")
        _home(g, ctx)
        return
    samples = _watch(g, REFUSE_S)
    led.check("S165-DEBOUNCE", *judge_debounce(base, samples))
    _home(g, ctx)


def _fading(g) -> object:
    return cb.poll(g, lambda s: _o(s, "state") == "fading", START_S, "the follow-out's fade")


def _supersede_row(g, led: cb.Ledger, ctx: dict) -> None:
    cid = "S165-SUPERSEDE"
    if not _home(g, ctx):
        led.check(cid, False, "not reached: the guest is not on FieldHUD 6603")
        return
    base, at = g.state, cb.mark(g)
    try:
        cb.try_ns(g, "swap", "delay", SUPERSEDE_DELAY_MS)
        ok, why = _frame(g, *ICE_TILE)
        if not ok or _fading(g) is None:
            led.check(cid, False, f"not reached: the follow-out never started its fade ({why or _o(g.state, 'why')!r})")
            return
        ok, why = cb.try_ns(g, "swap", "intent", INTENT_DEST)
        if not ok:
            led.check(cid, False, f"`swap intent {INTENT_DEST}` refused: {why}")
            return
        _host_off(g)                                       # the host's MAPJUMP: it is entering a field, its b6 falls with it
        samples = _watch(g, FIELD_S, until=lambda s: s.ui_state == "FieldHUD" and s.field_id == INTENT_DEST and s.control)
        samples += cb.hold_for(g, 0.5)
        led.check(cid, *judge_supersede(base, samples, cb.new(g, at)))
    finally:
        _host_off(g)
        cb.try_ns(g, "swap", "delay", 0)
        _home(g, ctx)


def _land(g, base, seconds: float = LEAVE_S) -> list:
    """The samples from a start to the landing's first judgeable world sample (block_ready + ticks advancing), or the timeout."""
    samples = []

    def until(s):
        samples.append(s)
        return first_judged([x for x in samples if x.ui_state == "WorldHUD"][-6:]) is not None
    got, _ = cb.watch(g, until, seconds)
    return got or samples


def _leave_rows(g, led: cb.Ledger, ctx: dict) -> None:
    rows = ("S165-LEAVE", "S165-BLOCK", "S165-POSE", "S165-ENTRANCE", "S165-FOOT", "S165-FROZEN")
    if not _home(g, ctx):
        led.unreached(rows, "the guest is not on FieldHUD 6603")
        return
    base, at = g.state, cb.mark(g)
    ok, why = _frame(g, *ICE_TILE, 11, 0, 0)                 # FieldEntrance 0: the dispatcher's default would reset the walker
    if not ok:
        led.unreached(rows, f"`worldfollow host` refused: {why}")
        return
    samples = _land(g, base)
    lines = cb.new(g, at)
    led.check("S165-LEAVE", *judge_leave(base, samples, lines))
    led.check("S165-BLOCK", *judge_block(samples))
    st = first_judged([s for s in samples if s.ui_state == "WorldHUD"])
    led.check("S165-POSE", *judge_pose(st, ICE_TILE))
    led.check("S165-ENTRANCE", *judge_entrance(base, st))
    led.check("S165-FOOT", *judge_foot(st))
    _host_off(g)
    if st is None:
        led.check("S165-FROZEN", False, "not judged: no judged world sample (the landing never settled)")
        return
    moved, adv, st2 = cw.hold_walk(g, WALK_FRAMES)
    led.check("S165-FROZEN", *judge_frozen_here(base, st2, moved, adv))


def _onfoot_row(g, led: cb.Ledger, ctx: dict) -> None:
    cid = "S165-ONFOOT"
    if not _home(g, ctx):
        led.check(cid, False, "not reached: the guest is not on FieldHUD 6603")
        return
    base = g.state
    try:
        cb.try_ns(g, "swap", "delay", SUPERSEDE_DELAY_MS)
        ok, why = _frame(g, *ICE_TILE)
        if not ok or _fading(g) is None:
            led.check(cid, False, f"not reached: the follow-out never started its fade ({why or _o(g.state, 'why')!r})")
            return
        _frame(g, *MOUNT_AT, 11, RIDE_MODE)                  # the host mounted, elsewhere, inside the guest's fade
        samples = _land(g, base)
        st = first_judged([s for s in samples if s.ui_state == "WorldHUD"])
        led.check(cid, *judge_onfoot(base, st, ICE_TILE))
    finally:
        _host_off(g)
        cb.try_ns(g, "swap", "delay", 0)


# ---- DOT
def _dot_block(s) -> dict:
    return dict(cb.path(s, "netsync.world.dot") or {})


def _dot_after(g, *frames, seconds: float = DOT_S, until=None) -> dict:
    """Each fabricated frame of ``frames`` (a word -- self / stale / nob6 -- or an (x, z[, idx ...]) tuple), then the dot block once
    ``until`` holds on it (or after ``seconds``)."""
    for f in frames:
        ok, why = _frame(g, *f) if isinstance(f, tuple) else _frame(g, f)
        if not ok:
            g.note(f"a dot frame refused: {why[:160]}")
    g.wait_frames(SETTLE_FRAMES)
    hit = cb.poll(g, lambda s: until(_dot_block(s)), seconds, "the dot") if until is not None else None
    return _dot_block(hit or g.state)


def _section_dot(g, led: cb.Ledger, ctx: dict) -> None:
    rows = tuple(SOLO_DOT)
    if not _on_world(g, ctx):
        led.unreached(rows, "the world map was never reached (neither the follow-out nor the guest's own walk out)")
        return
    _host_off(g)
    try:
        cw.teleport_settle(g, ICE_TILE)                      # inside the disc-1 Mist window: my own arrow is never pinned there
    except HarnessError as err:
        g.note(f"the teleport onto ICE_TILE raised: {str(err)[:160]}")
    g.press("select")
    g.wait_frames(30)
    led.check("S165-DOT-HUD", *judge_hud(g.state))
    d = _dot_after(g, "self", until=lambda d: d.get("shown") is True)
    led.check("S165-DOT-SELF", *judge_dot_self(d))
    mark = _dot_after(g, DOT_MARK, until=lambda d: d.get("want") is True and _num(d.get("host_x")) is not None
                      and abs(d["host_x"] - DOT_MARK[0]) < 1.0)
    led.check("S165-DOT-MARK", *judge_dot_mark(mark))
    edge = _dot_after(g, FS_LANDING, until=lambda d: d.get("edge") is True)
    led.check("S165-DOT-EDGE", *judge_dot_edge(edge, edge_width(mark)))
    _dot_after(g, "self", until=lambda d: d.get("want") is True)
    stale = _dot_after(g, "stale", seconds=STALE_S + DOT_S, until=lambda d: d.get("why_not") == "stale" and d.get("shown") is False)
    led.check("S165-DOT-STALE", *judge_dot_hidden(stale, "stale"))
    _dot_after(g, "self", until=lambda d: d.get("want") is True)
    nob6 = _dot_after(g, "nob6", until=lambda d: d.get("why_not") == "no_b6" and d.get("shown") is False)
    led.check("S165-DOT-NOB6", *judge_dot_hidden(nob6, "no_b6"))
    other = _dot_after(g, (*DOT_MARK, OTHER_IDX), until=lambda d: d.get("why_not") == "other_world" and d.get("shown") is False)
    led.check("S165-DOT-OTHER", *judge_dot_hidden(other, "other_world"))
    _dot_after(g, "self", until=lambda d: d.get("want") is True)
    _wf(g, "dot", "off")
    off = _dot_after(g, until=lambda d: d.get("why_not") == "lever")
    on = None
    if ctx.get("pulled") != "dot":
        _wf(g, "dot", "on")
        on = _dot_after(g, until=lambda d: d.get("shown") is True)
    led.check("S165-DOT-LEVER", *judge_dot_lever(off, on))
    _host_off(g)


# ---- SAVE
def _sg_answers(sg: dict | None) -> int:
    """[ff9mapkit netsync s165] The Save site's answers so far: `refused` + `would_save` (the engine counts a DRY would-save in
    `would_save` INSTEAD of `refused`: NetSyncField.ManualSaveRefusedNow, BW.save_guard_step)."""
    sg = sg or {}
    return (sg.get("refused") or 0) + (sg.get("would_save") or 0)


def _save_pick(g) -> tuple:
    """`savemenu`, then Confirm until the Save site answers (refused or would_save +1) or PICK_PRESSES; then Cancel back to the HUD.
    (state before, state after, back on the HUD)."""
    st0 = g.state
    n0 = _sg_answers(st0.saveguard_block)
    g.savemenu()
    g.wait_frames(30)
    for _ in range(PICK_PRESSES):
        if _sg_answers(g.state.saveguard_block) > n0:
            break
        if g.state.ui_state in ("WorldHUD", "FieldHUD"):
            hit = cb.poll(g, lambda s: _sg_answers(s.saveguard_block) > n0, PICK_S, "the save refusal")
            if hit is not None:
                break
        g.press("confirm")
        g.wait_frames(int(PICK_S * 30))
    for _ in range(CLOSE_PRESSES):
        if g.state.ui_state in ("WorldHUD", "FieldHUD"):
            break
        g.press("cancel")
        g.wait_frames(20)
    st1 = g.state
    return st0, st1, st1.ui_state in ("WorldHUD", "FieldHUD")


def _save_row(g, led, ctx, cid, *, dry=False, bench_off=False, logged=False) -> None:
    st = g.state
    files0 = save_files(st)
    if files0 is None:
        led.check(cid, False, "not reached: no SANDBOXED save path published (R4 never opens a save on the owner's slots)")
        return
    at = cb.mark(g)
    try:
        if dry:
            _wf(g, "saveguard", "old")
        if bench_off:
            cb.try_ns(g, "bench", 0)
        st0, st1, back = _save_pick(g)
    except HarnessError as err:
        led.check(cid, False, f"`savemenu` raised: {str(err)[:240]}")
        return
    finally:
        if dry and ctx.get("pulled") != "saveguard":
            _wf(g, "saveguard", "act")
        if bench_off:
            cb.try_ns(g, "bench", 1)
    led.check(cid, *judge_save(dict(st0.saveguard_block or {}), dict(st1.saveguard_block or {}), cb.log_lines(g)
                               if logged else cb.new(g, at), files0, save_files(g.state), dry=dry, logged=logged,
                               hud_back=back))


def _section_save(g, led: cb.Ledger, ctx: dict) -> None:
    st0 = g.state
    _wf(g, "r3", "old")
    old = cb.poll(g, lambda s: cb.path(s, "netsync.world.r3.lever") == "old", 3.0, "r3 old") or g.state
    _wf(g, "r3", "act")
    act = cb.poll(g, lambda s: cb.path(s, "netsync.world.r3.lever") == "act", 3.0, "r3 act") or g.state
    _cal_restore(g, ctx, "r3")
    led.check("S165-R3", *judge_r3(st0, old, act))
    if not _on_world(g, ctx):
        led.unreached(("S165-R4", "S165-R4-DRY", "S165-R4-S"), "the world map was never reached")
        return
    _host_off(g)
    _save_row(g, led, ctx, "S165-R4", logged=True)
    _save_row(g, led, ctx, "S165-R4-DRY", dry=True)
    _save_row(g, led, ctx, "S165-R4-S", bench_off=True)


def _release_solo(g, led: cb.Ledger, ctx: dict) -> None:
    """A lever pulled (stage >= 165), then `reset` (HarnessSelfTest(false) -> HarnessReleaseBench -> HarnessReleaseWorldFollow): the
    role released, the release line once; then the re-read WITH the role. One verdict after both reads."""
    stage = ctx.get("stage") or 0
    pulled = _wf(g, "off")[0] if stage >= 165 else False
    at = cb.mark(g)
    try:
        cb.release(g)
    except HarnessError as err:
        led.check("S165-R", False, f"`reset` failed: {str(err)[:300]}")
        return
    st = g.state
    ns = st.netsync or {}
    ok = ns.get("forced") is False
    detail = f"forced={ns.get('forced')!r}"
    if stage >= 165:
        n = cb.count(cb.wait_log(g, at, BW.LOG_WORLDFOLLOW_RELEASED, 2.0), BW.LOG_WORLDFOLLOW_RELEASED)
        st2, why = cb.reread_with_role(g)
        levers = rest_levers(st2) if st2 is not None else None
        ok = ok and pulled and n == 1 and levers == AT_REST
        detail += (f"; a lever pulled before the reset: {pulled}; the release line {n}x (want 1); {why or ''} re-read with the role: "
                   f"levers {levers} (want {AT_REST})")
    led.check("S165-R", ok, detail)


# ---------------------------------------------------------------------------------------------- T2: the world-walk tape
def _run_walk(g) -> None:
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, t2_catalog(calibrate), finals=("T2-SAVE", "T2-INI", "S165-WK-CAL"), width=DETAIL_W)
    ctx = cw._T2()
    ctx.field = FARSHORE
    ctx.sent, ctx.poses, ctx.t0, ctx.lever = [], [], None, ("out" if calibrate else None)
    try:
        _walk(g, led, ctx)
    except HarnessError as err:
        g.note(f"the walk leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        _walk_teardown(g, led, ctx)
        if calibrate:
            try:
                ctx.stage = max(ctx.stage, stage_of(g.state))
            except HarnessError:
                pass
            pred = T2_OLD_PREDICTED if ctx.stage < 165 else T2_LEVER_PREDICTED["out"]
            g.note(f"S165-WK-CAL: the guest reads as s{ctx.stage or '<117'}; predicted reds {sorted(pred)}")
            led.close("not reached: the leg ended before this check")
            led.judge_calibration("S165-WK-CAL", pred)
        led.close(final=True)


def _walk_teardown(g, led: cb.Ledger, ctx) -> None:
    if ctx.sent:
        ok, why = _wf(g, "clear")
        g.note(f"`worldfollow clear` (the levers this leg sent: {ctx.sent}): {'ok' if ok else why[:160]}")
    if ctx.peer is not None and ctx.peer.how_ended is None:
        g.note(f"coop_peer replay-host: {ctx.peer.stop()}")
    if "T2-SAVE" not in led.done:
        fell = pb.hits(ctx.eng.lines(), "ramp_failed") if ctx.eng is not None else []
        led.check("T2-SAVE", not fell, f"the exit ramp fell back to the TITLE: {pb.show(fell, 1)}" if fell else
                  "no title fallback" + ("" if ctx.eng is not None else " (the guest never ran a session)"))
    if ctx.guard is not None:
        ok, why = ctx.guard.restore()
        led.check("T2-INI", ok, why)
    else:
        led.check("T2-INI", True, "Memoria.ini was never edited (the leg stopped before the edit)")
    g.note(f"Memoria.log archived: {cb.archive_log(g, 'world-follow-walk')}")


def _walk_preflight(g, led: cb.Ledger) -> bool:
    free, why = (False, f"COOP_PEER_PORT={PORT} is the owner's bridge port (pick a private port; default {pb.WORLD_PORT})") \
        if PORT == pb.OWNER_PORT else pb.port_free(PORT)
    if not free:
        led.check("T2-PEER", False, why)
        led.close("not reached: the bench port is taken (nothing was edited)")
        return False
    owner_free, _owhy = pb.port_free(pb.OWNER_PORT)
    if not owner_free:
        led.check("T2-PEER", False, f"the owner's bridge is UP on 127.0.0.1:{pb.OWNER_PORT}: this guest game launched on the owner's "
                                    "Memoria.ini dials it before any edit and joins the owner's LIVE session -- stop it first")
        led.close("not reached: the owner's bridge is up (nothing was edited)")
        return False
    try:
        moogle = pb.ini_autosave_moogle_only((Path(g.game_path) / "Memoria.ini").read_text(encoding="utf-8", errors="replace"))
    except OSError:
        moogle = False
    if moogle:
        led.check("T2-SAVE", False, "[SaveFile] AutoSaveOnlyAtMoogle = 1: no own autosave on 6603 for the exit ramp (nothing "
                                    "was edited)")
        led.close("the guest can have no own autosave on the bench field (T2-SAVE)")
        return False
    return True


def _walk(g, led: cb.Ledger, ctx) -> None:
    rows = list(T2_ROWS)
    ctx.tape = pb.latest_world_walk_tape()
    if ctx.tape is None or not Path(ctx.tape).exists():
        led.check("T2-TAPE", False, f"no tape ({ctx.tape or pb.world_walk_tape_dir()}): record one -- COOP_TAPE_WORLD_WALK=1 "
                                    "coop_tape_record.py on the deployed s164 host")
        led.close("not reached: no tape")
        return
    try:
        cp = pb.coop_peer_module()
        _h0, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                              # noqa: BLE001
        led.check("T2-TAPE", False, f"{ctx.tape} does not read back: {err}")
        led.close("not reached: the tape does not read back")
        return
    ctx.facts = pb.world_walk_tape_facts(records, cp)
    ctx.poses = cp.tape_poses(records)
    facts_ok = all(ctx.facts[f"wk{i}"]["ok"] for i in range(1, 7))
    bad = [f"wk{i}: {ctx.facts[f'wk{i}']['why']}" for i in range(1, 7) if not ctx.facts[f"wk{i}"]["ok"]]
    led.check("T2-TAPE", facts_ok, f"{Path(ctx.tape).name} ({len(records)} records{f', torn {torn} B' if torn else ''}): "
                                   + ("the six facts hold" if facts_ok else "CANNOT -- " + "; ".join(bad))
                                   + f"; tile {ctx.facts.get('tile')}, enter {ctx.facts.get('enter')}")
    if not facts_ok and not FORCE:
        led.close("not reached: this tape cannot carry the walk leg")
        return
    if not _walk_preflight(g, led):
        return
    # C. the guest's own game on 6603
    cb.provenance(g)
    g.note("s165 T2 walk leg: the guest on 6603, the world-walk host replayed")
    g.newgame()
    g.warp(FARSHORE)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.watch(*(pb.MARKER_BYTE * 8 + b for b in range(8)))
    g.wait_frames(45)                                     # the field entry's autosave: the exit ramp's own Continue
    ctx.stage = stage_of(g.state)
    g.note(f"the guest engine reads as s{ctx.stage or '<117'}")
    # D. the ini, the engine's own config line
    ctx.eng = pb.EngineLog(g.engine_log())
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", GUEST_VALUES, label="coop-world-follow-walk",
                            run_dir=cw._run_dir(g))
    try:
        g.note(ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("T2-PEER", False, f"the Memoria.ini edit failed: {err}")
        led.close("not reached: Memoria.ini could not be edited")
        return
    cfg = cw._wait_config(g, ctx)
    if not cfg:
        led.check("T2-PEER", False, f"the engine never logged the guest config (seen: {pb.show(pb.hits(ctx.eng.lines(), 'config'))})")
        led.close("not reached: the guest config never applied")
        return
    # E. the probe, then the levers -- BEFORE the replay (never on an engine without netsync.world.out)
    s165 = cb.has(g.state, PROBE)
    lever_note = f"s{ctx.stage}: no `{PROBE}` -- nothing sent"
    if s165:
        sent = []
        if ctx.lever == "out":
            sent.append(("off", _wf(g, "off")))
        sent.append(("hold", _wf(g, "hold")))
        ctx.sent = [op for op, (ok, _w) in sent if ok]
        lever_note = "; ".join(f"`worldfollow {op}` {'sent' if ok else 'REFUSED: ' + w[:80]}" for op, (ok, w) in sent)
    g.note(lever_note)
    # F. the replay-host: the whole tape, holding at its end
    rd = cw._run_dir(g)
    ctx.peer = pb.PeerProc("replay-host", [ctx.tape, "--port", str(PORT), "--code", CODE, "--at-end", "hold"],
                           log_path=rd / "coop_peer-replay-world-walk.log", out_path=rd / "coop_peer-replay-world-walk.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0, tick=lambda: cw._sample(g, ctx))
    conn = ctx.peer.wait_for(pb.PEER["guest_connected"], DIAL_S, tick=lambda: cw._sample(g, ctx)) if up else None
    start = ctx.peer.wait_for(pb.PEER["replay_start"], 10.0, tick=lambda: cw._sample(g, ctx)) if conn else None
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "guest" and m.group(2) == CODE)
    wire = pb.wire_gate(ctx.peer, pb.probe_wire(g)) if start else (False, "no replay start")   # [ff9mapkit netsync s166] THE LIVE HEADER
    ok = up is not None and conn is not None and start is not None and bool(relay) and wire[0]
    led.check("T2-PEER", ok, f"wire: {wire[1]}; config: {pb.show(cfg, 1)}; peer: {up[1] if up else 'never listened'} / "
                             f"{conn[1] if conn else 'no guest'} / {start[1] if start else 'no replay start'}; engine: "
                             f"{pb.show(relay, 1)}")
    if not ok:
        led.unreached(rows, "the instrument never started (T2-PEER)")
        return
    ctx.anchors["start"] = start[0]
    m = pb.PEER["replay_start"].search(start[1])
    ctx.t0 = float(m.group(1)) if m else None
    _walk_rows(g, led, ctx, s165, lever_note)


def _walk_rows(g, led: cb.Ledger, ctx, s165: bool, lever_note: str) -> None:
    # WK-I: paired + ARMED on 6603 before the host's world exit
    start = ctx.anchors["start"]
    cw._until(g, ctx, lambda s: "exit" in ctx.anchors, PAIR_S + EXIT_S)
    exit_at = ctx.anchors.get("exit")
    lines = ctx.eng.lines()
    paired = pb.hits(lines, "paired", after=start, before=exit_at, pred=lambda m: int(m.group(1)) == FARSHORE)
    armed = pb.hits(lines, "armed", after=start, before=exit_at)
    before = [s for ts, s in ctx.samples if exit_at is not None and ts <= exit_at]
    on6603 = bool(before) and before[-1].ui_state == "FieldHUD" and before[-1].field_id == FARSHORE
    hold_ok = (not s165) or ("hold" in ctx.sent)
    i_ok = exit_at is not None and bool(paired) and bool(armed) and on6603 and hold_ok
    led.check("S165-WK-I", i_ok, f"paired {pb.show(paired, 1)}; armed {pb.show(armed, 1)}; the host's exit "
                                 f"{'at ' + exit_at.strftime('%H:%M:%S') if exit_at else 'NEVER on the peer log'}; the guest on "
                                 f"{before[-1].ui_state if before else '?'} {before[-1].field_id if before else ''}; {lever_note}")
    if not i_ok:
        led.unreached([c for c in T2_ROWS if c != "S165-WK-I"], "the instrument is untrustworthy on this run (WK-I)")
        return
    # WK-WAIT: until the tape's host stands at the tile (the guest's host cache reading it, else the tape's clock)
    tile_first = (ctx.facts.get("tile") or {}).get("first")
    tile_wall = None if tile_first is None or ctx.t0 is None else start + _dt.timedelta(
        seconds=(float(tile_first) - float(ctx.t0)) / REPLAY_SPEED)
    deadline = (tile_wall or _dt.datetime.now()) + _dt.timedelta(seconds=TILE_SLACK_S)
    settled = {"t": None}

    def at_tile(s):
        hx, hz = _num(_h(s, "x")), _num(_h(s, "z"))
        here = _h(s, "b6") is True and hx is not None and torus((hx, hz), ICE_TILE) <= pb.WK_POSE_TOL
        if not here:
            settled["t"] = None
            return False
        settled["t"] = settled["t"] or _dt.datetime.now()
        return (_dt.datetime.now() - settled["t"]).total_seconds() >= HOLD_SETTLE_S
    if s165:
        cw._until(g, ctx, at_tile, max(1.0, (deadline - _dt.datetime.now()).total_seconds()))
    else:
        cw._until(g, ctx, lambda s: _dt.datetime.now() >= (tile_wall or deadline), max(1.0, (deadline - _dt.datetime.now())
                                                                                     .total_seconds()))
    since = cw._after(ctx, exit_at)
    st = since[-1] if since else g.state
    left = [(s.ui_state, s.field_id) for s in since if not (s.ui_state == "FieldHUD" and s.field_id == FARSHORE)]
    w_ok = (cb.has(st, PROBE) and not left and _o(st, "why") == "hold" and _o(st, "hold") is True and _h(st, "b6") is True
            and settled["t"] is not None)
    led.check("S165-WK-WAIT", w_ok, (f"absent: no `{PROBE}` -- " if not cb.has(st, PROBE) else "")
              + (f"LEFT 6603: {left[:3]}" if left else "on FieldHUD 6603 throughout")
              + f"; why {_o(st, 'why')!r} (want 'hold'), hold {_o(st, 'hold')!r}, host cache b6 {_h(st, 'b6')!r} at "
              f"({_h(st, 'x')}, {_h(st, 'z')}); the tile read {'settled' if settled['t'] else 'NEVER'}")
    # WK-LEAVE: release -> the world map
    base = g.state
    lever_out = ctx.lever == "out"
    t_rel = _dt.datetime.now()     # stamped BEFORE the release: the start can log in the very frame the release lands (whole-second
    if s165:                       # engine stamps -- a stamp taken after the round trip could fall in the next second)
        ok, why = _wf(g, "release")
        g.note(f"`worldfollow release`: {'ok' if ok else why[:160]}")
    leave_s = (REFUSE_S * 2) if (lever_out or not s165) else LEAVE_S
    cw._until(g, ctx, lambda s: first_judged([x for _t, x in ctx.samples if _t >= t_rel and x.ui_state == "WorldHUD"])
              is not None, leave_s)
    after = [(ts, s) for ts, s in ctx.samples if ts >= t_rel]
    samples = [s for _ts, s in after]
    led.check("S165-WK-LEAVE", *(judge_leave(base, samples, [m for _t, _l, m in ctx.eng.lines() if _t >= pb.floor_s(t_rel)])
                                 if cb.has(base, PROBE) else (False, f"absent: no `{PROBE}` -- the guest stays on 6603")))
    landed = first_judged([s for s in samples if s.ui_state == "WorldHUD"])
    # WK-POSE: the seam bracket on the tape clock
    l0 = _num(_o(base, "lands"))
    pre = [ts for ts, s in after if _num(_o(s, "lands")) == l0]
    post = [ts for ts, s in after if l0 is not None and (_num(_o(s, "lands")) or 0) > l0]
    bracket = None
    if pre and post and ctx.t0 is not None:
        bracket = (tape_t(pre[-1], start, ctx.t0), tape_t(post[0], start, ctx.t0))
    elif post and ctx.t0 is not None:
        bracket = (tape_t(t_rel, start, ctx.t0), tape_t(post[0], start, ctx.t0))
    led.check("S165-WK-POSE", *judge_tape_pose(landed, ctx.poses, bracket))
    # the world map for the rows below: the follow-out's landing, else (s165 only: the lever's calibration) the guest's own walk out
    if g.state.ui_state != "WorldHUD" and s165:
        okw, whyw, _st = cw.walk_out(g)
        g.note(f"the world map by the guest's OWN walk out (no follow-out landed): {okw} ({whyw[:120]})")
    st = g.state
    if st.ui_state != "WorldHUD":
        led.unreached(("S165-WK-FROZEN", "S165-WK-DOT", "S165-WK-REJOIN"), f"the guest never reached the world map (ui "
                      f"{st.ui_state!r} field {st.field_id})")
        _wait_rejoin_field(g, ctx)
        return
    moved, adv, st = cw.hold_walk(g, WALK_FRAMES)
    led.check("S165-WK-FROZEN", *cw.judge_frozen(st, moved, adv, base))
    # WK-DOT: Select once, then the dot against the tape's own pose at that moment
    g.press("select")
    g.wait_frames(20)

    def dot_ok(s):
        if _d(s, "shown") is not True:
            return False
        t = tape_t(_dt.datetime.now(), start, ctx.t0)
        return t is not None and judge_dot_track(dict(cb.path(s, "netsync.world.dot") or {}),
                                                 tape_poses_in(ctx.poses, t - 1.5, t + 1.5), None)[0]
    cw._until(g, ctx, dot_ok, DOT_S * 2)
    st = g.state
    t = tape_t(_dt.datetime.now(), start, ctx.t0)
    pts = tape_poses_in(ctx.poses, t - 1.5, t + 1.5) if t is not None else []
    led.check("S165-WK-DOT", *judge_dot_track(dict(cb.path(st, "netsync.world.dot") or {}), pts, _d(st, "mapno")))
    # WK-REJOIN: the tape's host enters 300
    rbase = g.state
    t_rj = _dt.datetime.now()
    enter = (ctx.facts.get("enter") or {}).get("t")
    wait_s = REJOIN_S + max(0.0, ((float(enter) - float(ctx.t0)) / REPLAY_SPEED - (t_rj - start).total_seconds())
                            if enter is not None and ctx.t0 is not None else 60.0)
    cw._until(g, ctx, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, wait_s)
    cb.hold_for(g, 1.0)
    cw._sample(g, ctx)
    rs = cw._after(ctx, t_rj)
    rlines = [m for _t, _l, m in ctx.eng.lines() if _t >= pb.floor_s(t_rj)]
    arrive = cw.judge_arrive_world(rs, rbase, rlines, field=ICE_CAVERN)
    led.check("S165-WK-REJOIN", *cw.with_arrive(cw.judge_rejoin_land(rs, rbase, rlines, field=ICE_CAVERN), arrive))


def _wait_rejoin_field(g, ctx) -> None:
    """(the OLD path) let the tape play out to its 300 entry, so the session is whole when the leg ends."""
    enter = (ctx.facts.get("enter") or {}).get("t")
    if enter is None or ctx.t0 is None:
        return
    due = ctx.anchors["start"] + _dt.timedelta(seconds=(float(enter) - float(ctx.t0)) / REPLAY_SPEED + 5.0)
    cw._until(g, ctx, lambda s: _dt.datetime.now() >= due, max(1.0, (due - _dt.datetime.now()).total_seconds() + 1.0))


# ---------------------------------------------------------------------------------------------- the duo
def run_duo(d) -> None:
    """The duo leg (duo.py pairs the two games on 6603 first: ``PAIR``). Every row recorded (strict off), each judged on the GUEST's
    samples beside its engine's keys and the HOST's own; COOP_CALIBRATE=1 judges D-CAL by the GUEST's stage."""
    calibrate = cb.CALIBRATE
    strict, d.strict = d.strict, False
    failed, done = [], set()
    marks = {}

    def check(cid, ok, detail):
        if cid in done:
            return
        done.add(cid)
        if not ok:
            failed.append(cid)
        d.check(bool(ok), f"{cid}: {DUO_CHECKS.get(cid, cid)}", str(detail)[:DETAIL_W], cid=cid)

    def rest(why):
        for cid in DUO_ORDER:
            if cid != "S165-D-SHARED" and cid not in done:
                check(cid, False, f"not reached: {why}"[:DETAIL_W])

    sent = []
    try:
        marks["host"], marks["guest"] = cb.mark(d.host), cb.mark(d.guest)
        _duo(d, check, rest, sent)
    except HarnessError as err:
        d.note(f"the duo raised: {str(err)[:400]}")
        rest(f"the duo raised ({str(err)[:200]})")
    finally:
        try:
            hl = cb.new(d.host, marks.get("host", 0))
            gl = cb.new(d.guest, marks.get("guest", 0))
        except HarnessError:
            hl, gl = [], []
        check("S165-D-SHARED", *judge_shared(hl, gl))
        rest("the duo ended before this row")
        if sent:
            ok, why = _wf(d.guest, "clear")
            d.note(f"`worldfollow clear` on the guest: {'ok' if ok else why[:160]}")
        if calibrate:
            try:
                stage = stage_of(d.guest.state)
            except HarnessError:
                stage = 0
            pred = set(DUO_OLD_PREDICTED) if stage < 165 else set()
            missing, extra = sorted(pred - set(failed)), sorted(set(failed) - pred)
            d.check(not missing and not extra, "S165-D-CAL: CALIBRATION -- exactly the predicted duo rows red for the GUEST's stage",
                    f"guest s{stage}: predicted reds that stayed GREEN {missing or 'none'}; unpredicted reds {extra or 'none'}",
                    cid="S165-D-CAL")
        d.strict = strict


def _both_home(host, guest) -> tuple:
    hs, gs = host.state, guest.state
    ok = (hs.ui_state == "FieldHUD" and hs.field_id == FARSHORE and gs.ui_state == "FieldHUD" and gs.field_id == FARSHORE
          and cw._s(gs, "mirroring") is True)
    return ok, f"host {hs.ui_state} {hs.field_id}; guest {gs.ui_state} {gs.field_id}, mirroring {cw._s(gs, 'mirroring')!r}"


def _duo(d, check, rest, sent: list) -> None:
    host, guest = d.host, d.guest
    gst = guest.state
    stage = stage_of(gst)
    d.note(f"s165 duo: the guest reads as s{stage}, the host as s{stage_of(host.state)}")
    ok, why = _both_home(host, guest)
    check("S165-D0", ok, why)
    if not ok:
        rest("the pair is not on 6603 (D0)")
        return
    s165 = cb.has(gst, PROBE)
    # D-FO1 (+ D-HOST): the host walks out, the guest tapped meanwhile
    gbase, hbase, hat = guest.state, host.state, cb.mark(host)
    tap = Tap(guest)
    tap.start()
    try:
        okw, whyw, hst = cw.walk_out(host)
    finally:
        t_host = _dt.datetime.now()
    if not okw:
        tap.stop()
        rest(f"the host's walk out failed ({whyw[:160]})")
        return

    def landed():
        return first_judged([s for _t, s in list(tap.samples) if s.ui_state == "WorldHUD"]) is not None
    deadline = time.time() + FO_S
    while time.time() < deadline and not landed():
        time.sleep(0.1)
    taps = tap.stop()
    gs = [s for _t, s in taps]
    hx = world_xz(host.state)
    st = first_judged([s for s in gs if s.ui_state == "WorldHUD"])
    t_commit = next((t for t, s in taps if (odelta(gbase, s, "commits") or 0) >= 1), None)
    _resumed, rwhy = hb_resumed_before(taps, t_commit)   # reported only (D-FO1)
    t_land = next((t for t, s in taps if s is st), None)
    gap = f"{(t_land - t_host).total_seconds():.1f} s after the host's walk out returned" if t_land else "never"
    if st is None:
        p_ok, p_why = False, "not judged: the guest never stood on a judged world sample"
    else:
        x, z = world_xz(st)
        dd = torus((x, z), hx) if x is not None and hx[0] is not None else None
        p_ok, p_why = dd is not None and dd <= POSE_TOL, f"landed at ({x}, {z}), {dd if dd is None else round(dd, 1)}u from the host's own {hx}"
    l_ok = st is not None and all(odelta(gbase, st, k) == 1 for k in ("starts", "commits", "lands")) if s165 else False
    # the heartbeat witness is REPORTED, never judged (the first s165 duos: the host's heartbeat ran ~1.2 s past b6 before its block
    # load on one run of two, so THE LIVE DEBOUNCE ended before the load and the guest committed inside it -- landing at the same
    # pose, height included, as the run that waited the load out: decision 4's "straddles the load" is not a property it has)
    check("S165-D-FO1", s165 and l_ok and p_ok,
          (f"absent: no `{PROBE}` on the guest -- " if not s165 else "") + f"starts/commits/lands "
          f"+{odelta(gbase, st, 'starts') if st else None}/+{odelta(gbase, st, 'commits') if st else None}/"
          f"+{odelta(gbase, st, 'lands') if st else None}; {p_why}; HEARTBEAT (reported) {rwhy}; the landing gap (noise, the s164 law): {gap}")
    hlines = cb.new(host, hat)
    hw = host.state.host_world_block or {}
    n_exit = cb.count(hlines, BW.log_host_world_exit(FARSHORE, WORLD))
    n_on = cb.count(hlines, f"host: on world map {WORLD} (b6) at world frame ")
    dw = (hw.get("wmapjumps") or 0) - ((hbase.host_world_block or {}).get("wmapjumps") or 0)
    check("S165-D-HOST", n_exit == 1 and n_on == 1 and hw.get("b6") is True and dw == 1,
          f"the exit line {n_exit}x, the b6 line {n_on}x (want 1 each); host.world {hw or 'ABSENT'}, wmapjumps +{dw}")
    if guest.state.ui_state != "WorldHUD":
        rest(f"the guest never reached the world map (ui {guest.state.ui_state!r}, field {guest.state.field_id})")
        return
    # D-DOT: Select once; the dot at the host's own pose here, then after its teleport onto ICE_TILE
    own0 = world_xz(guest.state)
    guest.press("select")
    guest.wait_frames(20)
    reads = []
    for spot in (None, ICE_TILE):
        if spot is not None:
            cw.teleport_settle(host, spot)
        hp = world_xz(host.state)
        hit = cb.poll(guest, lambda s: judge_dot_track(dict(cb.path(s, "netsync.world.dot") or {}), [hp], None)[0], DOT_S * 2,
                      "the dot at the host")
        reads.append(judge_dot_track(dict(cb.path(hit or guest.state, "netsync.world.dot") or {}), [hp], None))
    own1 = world_xz(guest.state)
    still = own0[0] is not None and own1[0] is not None and plain(own0, own1) < HELD_U
    check("S165-D-DOT", all(r[0] for r in reads) and still,
          " | ".join(f"{'landing' if i == 0 else 'ICE_TILE'}: {r[1]}" for i, r in enumerate(reads))
          + f"; the guest's own pose {'unmoved' if still else 'MOVED'} ({own0} -> {own1})")
    # D-REJOIN: the host Confirms on the tile into 300
    gbase2, gat2 = guest.state, cb.mark(guest)
    early = []
    take = cw._sampler(guest, early)
    host_on = {"t": None}
    try:
        host.wait_frames(cw.PROMPT_FRAMES)
        host.press("confirm")
        take()

        def host_in(s):
            take()
            if s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN:
                host_on["t"] = host_on["t"] or len(early)
                return True
            return False
        hin = cb.poll(host, host_in, cw.FIELD_S, "the host on 300")
    except HarnessError as err:
        hin = None
        d.note(f"the host's entry raised: {str(err)[:200]}")
    if hin is None:
        check("S165-D-REJOIN", False, f"not reached: the host never entered 300 (ui {host.state.ui_state!r})")
        rest("the host never entered 300")
        return
    samples, _hit = cb.watch(guest, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, REJOIN_S)
    samples += cb.hold_for(guest, 1.0)
    seen = {s.frame for s in samples}
    after_host = early[host_on["t"]:] if host_on["t"] is not None else []
    allg = [s for s in early if s.frame not in seen] + samples
    glines = cb.new(guest, gat2)
    # a frame first published BEFORE the host stood on 300 is not "after" it, however late it is re-read: the guest publishes
    # nothing during its own synchronous load, so watch's first read can be its last pre-load frame (the first s165 duo: the dot
    # on that one frame, 0.29 s before the host's first sample on 300, counted as shown "once the host stood on 300")
    before = {s.frame for s in early[:host_on["t"]]} if host_on["t"] is not None else set()
    shown = [cb.raw(s).get("frame") for s in after_host + [s for s in samples if s.frame not in before]
             if _d(s, "shown") is True]
    # ...and hidden BEFORE the guest's own fade: no sample inside the rejoin's armed window (THE BRACKET LAW: only where one was
    # sampled) or off the world map still showing it
    armed = [s for s in allg if cw.in_armed_window(s) or s.ui_state != "WorldHUD"]
    armed_shown = [cb.raw(s).get("frame") for s in armed if _d(s, "shown") is True]
    n_ok, n_why = cw.judge_rejoin_land(allg, gbase2, glines, field=ICE_CAVERN)
    arrive = cw.judge_arrive_world(allg, gbase2, glines, field=ICE_CAVERN)
    check("S165-D-REJOIN", *cw.with_arrive((n_ok and not shown and not armed_shown,
                                            f"LAND {n_why}; the dot shown on {len(shown)} sample(s) once the host stood on 300 and on "
                                            f"{len(armed_shown)} of {len(armed)} in the rejoin's own window (want none)"), arrive))
    # D-FO2: both back on 6603, `hold`, the host out and onto the tile, `release`
    if not s165:
        check("S165-D-FO2", False, f"not reached: no `{PROBE}` on the guest -- `worldfollow hold` is never sent there")
        return
    try:
        host.warp(FARSHORE)
    except HarnessError as err:
        check("S165-D-FO2", False, f"not reached: the host's warp to {FARSHORE} raised: {str(err)[:160]}")
        return
    if cb.poll(guest, lambda s: s.ui_state == "FieldHUD" and s.field_id == FARSHORE and cw._s(s, "mirroring") is True,
               DUO_HOME_S, "the guest back on 6603") is None:
        check("S165-D-FO2", False, f"not reached: the guest never followed the host back onto {FARSHORE} "
                                   f"(ui {guest.state.ui_state!r} field {guest.state.field_id})")
        return
    ok, why = _wf(guest, "hold")
    if ok:
        sent.append("hold")
    gbase3 = guest.state
    okw, whyw, _hs = cw.walk_out(host)
    if not (ok and okw):
        check("S165-D-FO2", False, f"not reached: `hold` {'ok' if ok else why[:80]}, the host's walk out {okw} ({whyw[:80]})")
        return
    cw.teleport_settle(host, ICE_TILE)
    hp = world_xz(host.state)
    cb.poll(guest, lambda s: _h(s, "x") is not None and torus((_h(s, "x"), _h(s, "z")), hp) <= pb.WK_POSE_TOL, DOT_S * 3,
            "the guest's host cache at the tile")
    held = guest.state
    _wf(guest, "release")
    samples = _land(guest, gbase3, FO_S)
    st = first_judged([s for s in samples if s.ui_state == "WorldHUD"])
    p_ok, p_why = judge_pose(st, hp, frame_words=("latest", "pin"))
    check("S165-D-FO2", _o(held, "why") == "hold" and p_ok, f"held: why {_o(held, 'why')!r} on 6603 (want 'hold'); {p_why}")
