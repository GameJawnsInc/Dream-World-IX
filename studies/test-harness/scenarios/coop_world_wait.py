"""s144 -- WORLD-MAP CO-OP, WAIT THEN REJOIN (memoria-patch s144): the bench, run unattended. Three instruments in one file:
the SOLO leg (one game in the selftest role), two T2 legs (the desktop as a real GUEST, a recorded host replayed) and one
DUO leg (two real games). Every leg is judged on witnesses the engine does not compute -- world x/z displacement over
advancing frames, ui_state, the field id, the published words, the story byte the tape carries -- beside the engine's own
claim (`netsync.world.*`, `netsync.session.follow.*`).

THE OWNER'S CALL (studies/world-coop/S144-DESIGN.md, decisions 1-11): on the world map the HOST drives. A following guest
may reach the world map, and there it is FROZEN (no walk, no vehicle, no location, no full map); it rejoins the host's next
field through the world's own field entry; a guest left on a field when the host walks out waits there; both kinds of
waiting show one line (section 7's b6 HfWorld / b7 HfTitle; an old host's debounced field-0 fallback). Battles from the
world map are s145: this bench only proves the harness's world battle verb (a real own battle from WorldHUD and back).

THE ROUTE (every leg): New Game -> warp 6603 FARSHORE (the kit's FF9CustomMap-world landing: registered as FieldScene 6603
31 on 2026-10-20 -- RE-READ before each run, other sessions edit that folder) -> calibrate_axes with its door quad FS_DOOR
as a hazard -> walk_to FS_EXIT (strict=False, halt_on_transition) -> wait_world: world 9011 (WORLD11, the benign free-roam
state the 6603 exit cascade picks at the New-Game scenario), the landing FS_LANDING (68, -444). Proven by the terrain study
(r3 / r8 / veh_session1-4, rimwalk 20/20). Encounters off (noencounter, the s94 booster) at every arrival: round 8's first
launch died in a random battle at level 1. THE TELEPORT SPOTS are only ones proven inside a tri: the landing lawn (68,
-444) -- world_face probes walk ~30u there, so every unfrozen walk here stays inside WALK_FRAMES' reach -- and the stock
Ice Cavern entrance tile on block (18,12) at ICE_TILE (1197.37, -796.7): r8_build's walk lane crosses it at x 1197.37 for z
-795.2..-798.3 (every point on the tile), dispatch case 4 -> field 300 in every free-roam world script, round 8 10/10 (its
prompt, and Confirm entering 300). THE ACTOR-BRICK LAW: a world map never autosaves; the bench's only saves are the sandbox
autosaves of a FIELD entry (6603, 300), never parked on an edited cell.

THE OFFLINE ORACLE (S144-OR, read-only, before anything is launched -- never the engine's answer): the landing toml's
[[gateway]] (zone == FS_DOOR, to "worldmap", arrive == FS_LANDING); the DEPLOYED 6603 `.eb` (the highest-priority stacked
folder that registers it) exits to the world map with 9011 among its WorldMap() operands (eventscan.scan_all_warps); the
deployed WORLD11 dispatcher (a stacked folder's EVT_WORLD_WORLD11, else the stock one) carries a Field(300); no stacked
folder overrides the Ice Cavern's block (18,12) (its tile is the stock one round 8 entered); no stacked ForkDonorPatch.txt
forks field 300 unambiguously (ForkSiblingField would land every world entry into 300 -- F5, the rejoin rows -- on the
fork); the bench's world battle scene SCENE is a registered battle scene (the kit's scene table).

SOLO (COOP_WORLD_LEG=solo, the default; the selftest role, `netsync bench 1`):
  setup  INI (read-only: [Netsync] Enabled 0 or absent -- the runners' selftest_block.sh flips it, byte-exact restore) ->
         OR -> S0 (newgame, the COOPPARTY seed when registered, 6603, encounters off, the forced selftest role) -> P0 (the
         s144 keys and the three proof lines: 'world freeze selftest: OK (42 rows)', 'world rejoin selftest: OK (70
         rows)', 'overlay text selftest: OK (50 rows)') -> P1 (`netsync bench 1`; the lever at rest -- or pulled) -> ROUTE
  F0     THE SOURCE-FIELD HOLD: the spectator's own WorldMap() exit latched it -- `follow.hold` 6603 and its line once.
  F1     THE FREEZE, judged on the witness: `hold up` WALK_FRAMES at the landing moves world x/z < HELD_U over advancing
         frames (the world tick runs: world.phase 2).
  F1K    ...beside the engine's claim: freeze.on true, why 'bench', skips +SKIPS_MIN or more, edges exactly +1 since the
         walk out, the ON line once.
  F2     Confirm on the Ice Cavern tile (teleported onto it; the prompt's frames waited) stays WorldHUD for STAY_S, never
         field 300; freeze.keys +1 or more; the world-poll decline line once.
  F3     THE FULL MAP: Select is refused -- freeze.map +1, 'full map suppressed (following guest) on world map 9011' once,
         and the dispatcher is still asked after it (skips advance across MAP_S: w_naviMode 2 would stop it); then Cancel
         does nothing (still WorldHUD, the walker where it stood). Triangle is NOT pressed: on foot it reaches no world
         poll, and the selftest role's main menu is s121's refusal (keyed on IsMirroringStory, which the bench is not) --
         it would open (piece B's open issue). A map that DID open (no `map` count, or the dispatcher stopped being asked:
         s143, the lever, a fault) is closed after the judged window by a second Select -- stock WorldHUD never closes the
         full map on Cancel (OnKeyCancel's only branch needs currentState != FullMap; held, Cancel only hides its content)
         -- and the bench waits for the dispatcher to be asked again before F6.
  F6     THE EDGE: world_warp 6603 (a field load) and the walk out again -> edges +1 and the walker held again.
  F4     THE LEVER: `bench worldfreeze off` -> the walk moves > HELD_U, freeze.on false / off true; Confirm on the tile
         still stays WorldHUD and freeze.keys does not move (F1's spectator mask takes Confirm either way -- piece C's
         finding: a spectator cannot enter a location even unfrozen; decision 4's "walks and enters" is F5's). The lever is
         the pre-s144 world map, never the ~ menu's release (which DOES hand Confirm back: a live followed session only --
         the stand-in's rows and an owner check, below).
  F5     THE CONTROL: `bench worldfreeze on` (only where the probe allows it), `bench 0` -> the walk moves > HELD_U and
         Confirm on the tile enters field 300 (FieldHUD, field 300). Green on every engine. It is also F2's PREMISE's
         control: the same teleport onto the tile and Confirm ENTER 300 unfrozen (round 8 WALKED onto it; a teleport
         arming the tile's prompt is this bench's own assumption) -- a red F2 beside a red F5 is the instrument, never
         the freeze.
  B1     THE WORLD BATTLE VERB: from 300, warp 6603 and the walk out (no spectator: no hold), then `battle SCENE 0 rand`
         on WorldHUD (Session.world_battle): a new battle epoch on BattleHUD, `debug_status` the engine's started text,
         its line once. On s143 the driver refuses it (no `world.next_mode`) and the raw step answers 'battle: field
         only' (recorded in the detail).
  B2     THE SWIRL: a publish between the verb and the battle reads world.next_mode 2 with the shared latch busy
         (`rejoin.latch` true). The agent writes state every frame around the verb (`stateevery 1`, restored after): the
         readable window is the few frames before _Swirl's LoadLevel("SwirlScene"); no publish on the live WorldMap scene
         in it is the instrument's ("not reached"), never the engine's red.
  B3     THE RETURN: the fight won (or fled) -> WorldHUD, world 9011, x/z within RETURN_TOL of where it started (the warm
         return by prevMode 3), next_mode 3.
  R      the lever pulled once more, then `reset`: the role released and 'world freeze back ON (released with the
         harness)' once; RE-READ WITH THE ROLE (`netsync selftest 1` releases nothing): off false.
  THE BATTLE SCENE: 67 (BSC_EF_R007, one Goblin, 33 HP: a level-1 New-Game party wins it; registered in Battle.mapName;
  the scene every co-op bench fights; the world return and prevMode do not depend on it). COOP_WORLD_SCENE=359
  (BSC_WM_0007, the Mist continent's own world formation, in game 2026-07-02) is the fidelity knob -- off by default: its
  group can kill a lone level-1 Zidane, and a lost fight ends at Game Over, never the world return.

T2 (COOP_WORLD_LEG=rejoin | wait; the desktop is a REAL client: Memoria.ini [Netsync] Enabled 1 / Role client / RelayUrl
ws://127.0.0.1:<COOP_PEER_PORT, never 49201> / SessionCode ff9-T2BENCH1 / FollowHost 1 / SessionGraceMs 30000 written
through _coop_peer_bench.IniGuard -- backed up first, restored byte-exact, the engine hot-reloads it -- and
tools/harness/coop_peer.py `replay-host` stands in for the bridge):
  rejoin  THE EXISTING FIELD-250 TAPE (latest.json; its coop_cut_hold CAL verdict required -- T2-CAL), the replay stopped
          REJOIN_SPAN_S in (before its battle). THE CLIENT IS BORN -- OR DIALS -- ON THE WORLD MAP (decision 9; review: a
          transport created on 6603 survives the walk out and retries from any scene, so a guest configured on the field
          connects from the world HUD on s143 too). Two paths, by the guest's state before any edit:
            ENSURE  no client instance (`netsync.instance` false: [Netsync] off at launch): the FULL config is written on 6603
                    with no reload -- nothing reads it there (no instance polls; HonoluluFieldMain's Ensure runs at a field
                    LOAD); the walk out's world load runs WMScriptDirector.HonoAwake's Ensure (s144 only), which reads it and
                    the client dials on WorldHUD. On s143 nothing reads it at all (no config line, no dial).
            POLL    an instance exists (its 2 s poll would read a code on the field): the PARK config (SessionCode "") on 6603
                    -- a client never dials an empty code (OvlNoCode) -- then the walk out, then the code alone written on
                    the world HUD (IniGuard.update): the poll reads it there (every engine), and only s144's dial gate
                    accepts WorldHUD.
          Only then does the peer start.
          RJ-PARK the instrument: nothing dialled on the field -- ENSURE: no config or relay line before the walk began;
                  POLL: the park config line (code empty), the overlay 'no_code', no relay line before the walk began.
                  A relay line counts only when it is THE BENCH's own dial (its port, or its code: bench_dial): the guest
                  launched on the owner's ini, whose transport keeps retrying ITS endpoint (127.0.0.1:49201, the owner's
                  code) every ~2 s until the park's config change stops it -- and an attempt already in flight still logs
                  its failure after that (NetSyncRelay.Stop only clears _running). Those lines say nothing about the bench.
          RJ-I    the instrument: the guest on WorldHUD 9011 with its OWN story (the marker byte 0x00, the watch READ) when
                  the peer starts.
          RJ-DIAL the guest dials the replay-host FROM THE WORLD HUD: the engine's config line with the code and its first
                  'relay connected ...?role=guest' both stamped after the walk began, every sample since the world arrival
                  on WorldHUD, 'GUEST game connected' and 'REPLAY start' within DIAL_S (decision 9).
          RJ-ARM  the world arm: rejoin.arms +1 with last F (the tape's field), the overlay 'rejoining' (detail F) with
                  decision 7's words on a sample, 'rejoining the peer at field F from world map 9011' logged.
          RJ-LAND the witness: FieldHUD on F within LAND_S of the replay's start; rejoin.lands +1, follow.world_armed -1 at
                  the end, 'world rejoin landed on field F' logged.
          RJ-MIRROR the arrival is a field follow's: 'state-mirror ARMED' after the landing, session.mirroring true, and the
                  story marker reads the HOST's 0xA5 on F (the byte the tape carries, never the guest's own 0x00).
  wait    A HOST-ON-WORLD TAPE (coop_tape_record.py COOP_TAPE_WORLD=1: the host on 6603, then out on the world map >=
          WAIT_NEED_S; its own COOP_TAPE_DIR, pointer latest-world.json; COOP_TAPE names one). Its b6 is read OFFLINE
          (coop_peer.tape_where): an s144 host's tape says 'host_world', an s143 host's (no b6) is the old-host fallback
          'host_away' -- the oracle for the guest's line. The guest pairs on 6603 (a field: every engine dials there).
          WT-I    the instrument: 'paired on the host's field (6603)' and 'state-mirror ARMED' before the host's world exit
                  (the peer's 'tape T: host field 6603 -> 0' line), the guest on FieldHUD 6603.
          WT-FIELD decision 5: within LINE_S + LINE_GRACE_S of the exit the guest shows the waiting line -- polled, bounded
                  (an s144 host's b6 rises only once its WorldMap scene runs) -- and is STILL on FieldHUD 6603 on every
                  sample since the exit: overlay 'host_world', overlay_text "FF9 co-op: Your partner is on the world
                  map.\\nYou'll rejoin them at their next stop.", waitline 'host_world', follow.host_world true (an s143
                  tape: 'host_away', "FF9 co-op: Your partner is away.", waitline.fallback true).
          WT-FROZEN the guest walks out too (a mirroring guest may reach the world map) and is frozen there: `hold up`
                  moves < HELD_U, freeze.on true (why 'live' or 'mirroring'), skips advancing.
          WT-WORLD the same line on the world map (waitline the same), and -- an s144 tape -- the source-field hold on 6603
                  released by the host's b6 ('world rejoin hold on field 6603 released: the host left it'), follow.hold -1.
  COMMON  T2-TAPE (the tape reads back and the leg's plan fits it: _coop_peer_bench.plan_world_leg), T2-CAL (rejoin only),
          T2-PEER (the port free, the guest config written, the peer listening; the wait leg: the engine's own config line,
          the guest connected and the replay started too -- the rejoin leg's config line is RJ-DIAL's: only an s144 engine
          reads it on the world map), T2-SAVE (in these legs the precheck only: [SaveFile] AutoSaveOnlyAtMoogle off and no
          title fallback logged -- no leg ends a session inside the run, so the exit ramp itself is never exercised here),
          T2-INI (final, as coop_cut_hold's).

DUO (`py tools/harness/duo.py studies/test-harness/scenarios/coop_world_wait.py`; PAIR on 6603; keyed by the GUEST's
stage -- both roots junction one Managed, so the duo cannot mix DLLs):
  D0  the instrument: both on FieldHUD 6603, the guest mirroring (duo's own C2-C6 paired them).
  D1  the host walks out of 6603 -> the guest LEFT on 6603 stays there (every sample) and shows the waiting line
      ('host_world', the words, follow.host_world).
  D2  the guest walks out too -> frozen on world 9011 (`hold up` < HELD_U; freeze.on, why live / mirroring), the line on
      the world map, the hold released by the host's b6.
  D3  the host enters the Ice Cavern (the tile, Confirm) -> the guest rejoins from the world map: FieldHUD 300 within
      REJOIN_S, rejoin.arms / lands +1, 'rejoining the peer at field 300 from world map 9011' and 'world rejoin landed on
      field 300' logged, mirroring.

CALIBRATION -- a check that cannot fail is not a check.
  * SOLO on s143 (the live DLL at writing, Assembly-CSharp be01339d49f6a87b) with COOP_CALIBRATE=1: no `netsync.world`, so
    the lever is never sent (the driver's NETSYNC_BENCH_OPS gate: an s143 agent reads `bench worldfreeze` as `bench 1`).
    Red, exactly (OLD_PREDICTED): P0, P1 (the lever's keys absent), F0 (no hold), F1 (the walker WALKS), F1K, F2 (no
    keys count), F3 (the full map opens), F6, F4 (the lever cannot be sent), B1 (the driver refuses; 'battle: field
    only'), B2, B3. GREEN: INI, OR, S0, ROUTE (the route is the instrument), F5 (the control), R.
  * SOLO on s144 with COOP_CALIBRATE=1: `bench worldfreeze off` pulled at P1 and held through F6. Red, exactly
    (LEVER_PREDICTED), each the pre-s144 world map: F1 (the walker walks), F1K, F2 (Confirm still stays -- F1's mask --
    but keys never counts), F3 (the full map opens; the bench closes it), F6. GREEN: F0 (the hold keys on
    SpectatorField, not the lever), F4, F5, B1-B3 (the verb is not co-op gated), R.
  * T2 on an s143 GUEST (COOP_CALIBRATE=1 adds <LEG>-CAL): rejoin -- exactly RJ-DIAL, RJ-ARM, RJ-LAND, RJ-MIRROR (the
    guest never dials off a field: its client is never Ensured on the world map, or its code is read there with no dial
    gate to take it -- it stays on the world map); wait -- exactly WT-FIELD (s143's bare 'waiting'), WT-FROZEN (it
    walks), WT-WORLD (no line). The instrument rows (T2-*, RJ-PARK, RJ-I, WT-I) are never predicted red. The rejoin has
    no lever: its calibration is the s143 DLL alone.
  * DUO on s143 (COOP_CALIBRATE=1): exactly D1, D2, D3 (D-CAL).
  * OFFLINE: the stand-in (tools/harness/fakegame.py, rung `worldwait`) models the freeze, the rejoin and the line, and
    its FAULT LEVERS (FakeGame.world_faults); ff9mapkit/tests/test_coop_world_wait.py smokes every leg against it (the T2
    legs through a stub peer that connects whenever the stand-in's TRANSPORT exists -- FakeGame.dial_socket, born where its
    dial gate FakeGame.dial_ready held and kept in every scene; a stub ini that only a client's poll or the next Ensure
    reads) and turns each fault red in exactly its *_FAULT_REDS rows -- never read <LEG>-CAL offline: the engine is the
    calibration.

PRECONDITIONS -- THE OPERATOR'S JOB (the bench edits no ini but the T2 legs' guarded [Netsync] keys, deploys nothing,
launches nothing it was not asked to): the DLL under test deployed, controllers OFF and nobody at the keyboard (THE
UNATTENDED LAW: every walk, Confirm and battle is harness input), FF9 unfocused; 6603 registered (FF9CustomMap-world);
the T2 legs: the production bridge NOT on the bench port, [SaveFile] AutoSaveOnlyAtMoogle 0, the tape recorded, AND THE
OWNER's OWN BRIDGE DOWN (127.0.0.1:49201): the guest game launches on the owner's Memoria.ini (its Role, its SessionCode) and
its transport dials that endpoint before IniGuard edits anything -- with the bridge up it joins the owner's LIVE session, and
since s144 it re-dials from the world HUD after T2-INI's restore. The legs refuse it (T2-PEER, nothing edited).

WHAT NO LEG HERE REACHES (named, not hidden): raw XInput (the right stick, the vehicle throttle) and raw WASD -- the gate's
code read and an owner pad / keyboard check; a guest frozen ABOARD a vehicle (no proven vehicle route on this bench: the
OWED OWNER LEG -- set a chocobo from the ~ World tab's vehicle control, freeze with `bench 1`, press Cancel: the published
`world.vehicle` (gEventGlobal[190]) must stay nonzero; the stand-in pins the counted-but-unmasked shape); F11 / held L3
and the ~ menu's "Release world freeze" (no harness verb: the stand-in's rows and an owner check -- released, Confirm on
a location tile enters it); the overlay box's placement over the world HUD (tools/game_snap.ps1 on a T2 / duo run: the
bench shoots `world-line-*` frames for the owner); the host-side line (decision 7 has none, but a world-map HOST with no
guest reads its connecting line).

    py tools/play.py studies/test-harness/scenarios/coop_world_wait.py --field 6603
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_world_wait.py --field 6603
    COOP_WORLD_LEG=rejoin py tools/play.py studies/test-harness/scenarios/coop_world_wait.py
    COOP_WORLD_LEG=wait COOP_TAPE=<world tape> py tools/play.py studies/test-harness/scenarios/coop_world_wait.py
    py tools/harness/duo.py studies/test-harness/scenarios/coop_world_wait.py
"""
from __future__ import annotations

import datetime as _dt
import math
import os
import re
import sys
import time
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _coop_peer_bench as pb                              # noqa: E402 - the T2 two-role bench helpers

HarnessError = cb.HarnessError
BW = None                                                  # battlewire, bound by _bw() (the driver puts tools/ on sys.path)


def _bw():
    global BW
    if BW is None:
        try:
            from harness import battlewire
        except ImportError:                                # pragma: no cover - imported outside the driver
            sys.path.insert(0, str(cb.REPO / "tools"))
            from harness import battlewire
        BW = battlewire
    return BW


_bw()

PROBE = cb.R3_PROBES[144]                                  # netsync.world.freeze: the s144 capability
LEGS = ("solo", "rejoin", "wait")


def _leg(raw) -> str | None:
    n = (raw or "solo").strip().lower()
    n = {"t2": "rejoin", "world-rejoin": "rejoin", "world-wait": "wait", "": "solo"}.get(n, n)
    return n if n in LEGS else None


_RAW_LEG = os.environ.get("COOP_WORLD_LEG", "solo")
LEG = _leg(_RAW_LEG)

# ------------------------------------------------------------------------------------------------ the route
FARSHORE = 6603                                            # the kit's FARSHORE landing (FF9CustomMap-world)
FS_DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]   # its walk-off quad (landing.field.toml [[gateway]])
FS_EXIT = (400.0, -1400.0)                                 # a point inside it (r3_session's FS_EXIT)
FS_LANDING = (68.0, -444.0)                                # where the door sets the party down on world 9011
WORLD = 9011                                               # WORLD11, the exit cascade's pick at the New-Game scenario
ICE_CAVERN = 300                                           # the stock Ice Cavern entrance (field 300)
ICE_TILE = (1197.37, -796.7)                               # its walk-on entrance tile on block (18,12) (r8_build's lane)
ICE_BLOCK = (18, 12)
LANDING_TOML = cb.REPO / "studies" / "overworld-topography" / "west-seam-continent" / "landing.field.toml"
WORLD_EB_NAME = "EVT_WORLD_WORLD11.eb.bytes"
EVT_DIR = ("StreamingAssets", "assets", "resources", "commonasset", "eventengine", "eventbinary")
EVT_LANG = "us"

# ------------------------------------------------------------------------------------------------ the measures
ROUTE_TOL = 8.0          # the walk out lands within this of the landing
HELD_U = 2.0             # a hold that moves the walker less than this is HELD; more is a walk (Session.WORLD_PROBE_MIN)
WALK_FRAMES = 30         # `hold up` this long: ~0.5 s -- a free walk covers ~8-15u in game (inside the landing lawn's 30u)
EDGE_FRAMES = 15         # F6's shorter hold
SKIPS_MIN = 8            # world ticks (~28 a second) the freeze must count over a WALK_FRAMES hold
STAY_S = 3.0             # a refused Confirm must leave the game on WorldHUD this long
PROMPT_FRAMES = 30       # on the tile, before the Confirm (the prompt's own frames: r8 waited 20)
MAP_S = 2.0              # after Select: the window the dispatcher must still be asked in
FIELD_S = 20.0           # Confirm on the tile -> field 300
WORLD_S = 90.0           # a walk out -> the world map (the first WorldHUD frame precedes the all-block load by ~4.4 s)
BATTLE_S = 60.0          # the verb -> BattleHUD
FIGHT_S = 240.0
RETURN_S = 60.0          # the battle's end -> WorldHUD
RETURN_TOL = 4.0         # the warm return puts the walker back within this of where the battle started
SCENE = pb.env_int("COOP_WORLD_SCENE", 67)                 # one Goblin (see THE BATTLE SCENE); 359 the fidelity knob
GROUP = 0
POLL_S = 0.1

# ------------------------------------------------------------------------------------------------ T2 / duo
PORT = pb.env_int("COOP_PEER_PORT", pb.WORLD_PORT)        # a PRIVATE port: 49201 (the owner's bridge) is refused
CODE = pb.BENCH_CODE
GRACE_MS, GRACE_NOTE = pb.engine_grace(os.environ.get("COOP_GRACE_MS", str(pb.BENCH_GRACE_MS)))
GUEST_VALUES = {"Enabled": "1", "Role": "client", "RelayUrl": f"ws://127.0.0.1:{PORT}", "SessionCode": CODE,
                "FollowHost": "1", "TargetField": "0", "GuestSlots": "0", "GuestStockMenu": "1",
                "SessionGraceMs": str(GRACE_MS), "AutoTeleport": "0", "DioramaSwirlFrames": "0"}
#: the rejoin leg's POLL path: the guest's config with NO code on the field -- a client never dials an empty code (OvlNoCode)
PARK_VALUES = dict(GUEST_VALUES, SessionCode="")
#: F3's map close (a test seam: False leaves an opened map open -- the bench's own close is what keeps F4 / F5 honest)
CLOSE_MAP = True
FORCE = pb.env_flag("COOP_WORLD_FORCE")    # run the rejoin leg past an untrusted instrument (T2-CAL red stays red)
DIAL_S = 25.0            # the peer listening -> the guest connected
LAND_S = 30.0            # the replay's start -> the guest on the host's field
MIRROR_S = 6.0           # the landing -> 'state-mirror ARMED' and the host's story byte
PAIR_S = 45.0            # the wait leg: the replay's start -> paired + ARMED on 6603
EXIT_S = 60.0            # ...the host's world exit (after the tape's own exit_t)
LINE_S = _bw().WAIT_AWAY_MS / 1000.0 + 3.0   # the host's exit -> the line judged (the old-host debounce, + 3 s)
LINE_GRACE_S = 10.0      # ...polled up to this much longer (an s144 host's b6 rises only once its WorldMap scene runs)
PARK_S = 3.0             # the rejoin leg's ENSURE path: the ini sits on 6603 this long (past the 2 s poll) with nothing reading it
CONFIG_S = 12.0          # the code written on the world map -> the engine's config line (the 2 s poll, or the world load's Ensure)
STAMP_S = 1.05           # [review 2] the POLL path's park line -> the walk: past the engine's whole-second stamps (RJ-PARK's cut)
REJOIN_S = 40.0          # the duo: the host on 300 -> the guest on 300
DUO_LINE_S = 20.0        # the duo: the host's walk out -> the guest's line

# ================================================================================================ the catalogs
SOLO_CHECKS = {
    "S144-INI": "precondition (Memoria.ini, READ-ONLY): [Netsync] Enabled 0 or absent (the selftest role)",
    "S144-OR": "the offline oracle: the landing toml's door (FS_DOOR -> worldmap at FS_LANDING), the DEPLOYED 6603 .eb's "
               "WorldMap() operands holding 9011, the deployed WORLD11 dispatcher's Field(300), no stacked override of "
               "block (18,12), no unambiguous fork of field 300 (ForkDonorPatch.txt), the battle scene registered",
    "S144-S0": "newgame -> (the COOPPARTY seed) -> 6603 -> encounters off -> the forced selftest role",
    "S144-P0": f"the engine publishes `{PROBE}` and the s144 blocks (netsync.world freeze / rejoin / waitline and "
               "session.follow in the agent's key order, session.overlay_text) and logged the three proof lines OK -- "
               "'world freeze selftest' (42 rows), 'world rejoin selftest' (70), 'overlay text selftest' (50) -- none FAIL",
    "S144-ROUTE": f"the walk out of {FARSHORE} lands on WorldHUD, world {WORLD}, within {ROUTE_TOL:g}u of the landing "
                  f"{FS_LANDING} (the instrument)",
    "S144-F0": f"THE SOURCE-FIELD HOLD: the spectator's own WorldMap() exit latched it -- follow.hold {FARSHORE} and "
               "'world-map exit from field 6603 to world map 9011 (following guest): ...' once",
    "S144-F1": f"THE FREEZE (the witness): `hold up` {WALK_FRAMES} frames at the landing moves world x/z < {HELD_U:g}u "
               "over advancing frames",
    "S144-F1K": f"...the engine's claim beside it: freeze.on true, why 'bench', skips +{SKIPS_MIN} or more, edges exactly "
                "+1 since the walk out, the ON line once",
    "S144-F2": "Confirm on the Ice Cavern tile stays WorldHUD (never field 300) for STAY_S; freeze.keys +1 or more; the "
               "world-poll decline line once",
    "S144-F3": "THE FULL MAP: Select refused -- freeze.map +1, 'full map suppressed (following guest) on world map 9011' "
               "once, the dispatcher still asked after it (skips advance); Cancel then does nothing (WorldHUD, the walker "
               "where it stood); a map that opened is closed after the window by a second Select (never Cancel)",
    "S144-F6": "THE EDGE: world_warp 6603 (a field load) and the walk out again -> edges +1 and the walker held again",
    "S144-F4": "THE LEVER: `bench worldfreeze off` -> the walk moves > HELD_U, freeze.on false / off true; Confirm on the "
               "tile still stays WorldHUD (F1's spectator mask) and freeze.keys does not move",
    "S144-F5": "THE CONTROL: `bench worldfreeze on` (where the probe allows), `bench 0` -> the walk moves > HELD_U and "
               "Confirm on the tile ENTERS field 300",
    "S144-B1": f"THE WORLD BATTLE VERB: `battle {SCENE} {GROUP} rand` on WorldHUD -> a new battle epoch on BattleHUD, "
               "debug_status the engine's started text, its line once",
    "S144-B2": "THE SWIRL: a publish between the verb and the battle reads world.next_mode 2 with the shared latch busy "
               "(rejoin.latch true); no publish on the live WorldMap scene in the window is 'not reached' (the instrument)",
    "S144-B3": f"THE RETURN: the fight over -> WorldHUD, world {WORLD}, x/z within {RETURN_TOL:g}u of where it started (the "
               "warm return), next_mode 3",
    "S144-R": "`reset` (the lever pulled just before it) releases the role and the lever ('world freeze back ON (released "
              "with the harness)' once); re-read WITH the role: freeze.off false",
}


def solo_catalog(calibrate: bool) -> dict:
    c = dict(SOLO_CHECKS)
    c["S144-P1"] = ("the lever PULLED for calibration: `netsync bench 1` then `bench worldfreeze off` -> freeze.off true "
                    "and its OFF line once" if calibrate else
                    "`netsync bench 1` accepted (the field-gate bench on: SpectatorField) and the lever at rest: "
                    "freeze.off false")
    order = ["S144-INI", "S144-OR", "S144-S0", "S144-P0", "S144-P1", "S144-ROUTE", "S144-F0", "S144-F1", "S144-F1K",
             "S144-F2", "S144-F3", "S144-F6", "S144-F4", "S144-F5", "S144-B1", "S144-B2", "S144-B3", "S144-R"]
    out = {k: c[k] for k in order}
    if calibrate:
        out["S144-CAL"] = ("CALIBRATION: the engine's stage decides the set -- before s144 exactly OLD_PREDICTED red, on "
                           "s144 under `bench worldfreeze off` exactly LEVER_PREDICTED red")
    return out


#: the world rows: a route that cannot run records them "not reached"
WORLD_ROWS = ("S144-F0", "S144-F1", "S144-F1K", "S144-F2", "S144-F3", "S144-F6", "S144-F4", "S144-F5", "S144-B1",
              "S144-B2", "S144-B3")
#: [calibration] an engine before s144 (the deployed s143): every key-judged row, and the behavioural F1 / F2 / F3 / F6
OLD_PREDICTED = ("S144-P0", "S144-P1", "S144-F0", "S144-F1", "S144-F1K", "S144-F2", "S144-F3", "S144-F6", "S144-F4",
                 "S144-B1", "S144-B2", "S144-B3")
#: [calibration] s144 under `bench worldfreeze off` (pulled at P1, held through F6): the pre-s144 world map at every freeze
#: seam -- the walker walks, nothing counts, the full map opens
LEVER_PREDICTED = ("S144-F1", "S144-F1K", "S144-F2", "S144-F3", "S144-F6")
#: the stand-in's FAULT LEVERS (fakegame.WORLD_FAULTS) -> exactly the SOLO rows each turns red (tests pin it); a fault that
#: breaks only the followed client reds no solo row
SOLO_FAULT_REDS = {
    "dispatch_ungated": ("S144-F1", "S144-F6"),        # counted and claimed, but the walker walks: the x / z witness
    "keys_unmasked": ("S144-F2",),                     # Confirm still stays (s143's F1 mask), `keys` never counts
    "fullmap_open": ("S144-F3",),                      # the map opens: `map` never counts, the dispatcher stops being asked
    "lever_ignored": ("S144-F4",),
    "lever_stuck": ("S144-R",),
    "bench0_stuck": ("S144-F5",),
    "edge_once": ("S144-F6",),
    "hold_unlatched": ("S144-F0",),
    "battle_nextmode": ("S144-B1", "S144-B3"),         # the world strands in nextMode 2 (the swirl's latch still busy)
    "battle_field_return": ("S144-B3",),
    "counters_dark": ("S144-F1K", "S144-F3", "S144-F6"),   # held, but the counts lie (F3's dispatcher read is `skips`)
    # the shared latch reads free: the swirl's busy latch is the real B2 red. (Its nextMode term ALONE has no in-game red --
    # the consuming tick writes mode 2 and attr 0x1000 with nextMode 2, and the mode term comes first -- so no fault models
    # it: the engine selftest's mutant row is its only pin.)
    "latch_free": ("S144-B2",),
}

# ---- T2
T2_COMMON = {
    "T2-TAPE": "the tape reads back and this leg's plan fits it (_coop_peer_bench.plan_world_leg off its facts)",
    "T2-CAL": "the CAL leg passed on THIS tape (<tape>.cal.json, sha256-keyed) -- the instrument is trusted",
    "T2-PEER": f"port {PORT} free; the guest config written; the replay-host listening",
    "T2-SAVE": "THE PRECHECK (these legs end no session inside the run, so no exit ramp runs here): [SaveFile] "
               "AutoSaveOnlyAtMoogle off before the run (the guest had its OWN autosave to end a session on), and no "
               "'session ended, no autosave to resume -> title screen' line in it",
    "T2-INI": "Memoria.ini restored byte-exact (sha256) after the run -- the install is shared",
}
T2_CHECKS = {
    "rejoin": {
        "S144-RJ-PARK": "the instrument: nothing dialled on the field -- ENSURE (no client before the edit): no config or relay "
                        "line before the walk began; POLL (a client exists): the park config line (code empty), the overlay "
                        "'no_code', no relay line before the walk began -- the BENCH's own dial only (its port or its code): "
                        "the owner's transport retrying ITS endpoint until the park is no bench line",
        "S144-RJ-I": f"the instrument: the guest on WorldHUD {WORLD} with its OWN story (the marker 0x00, the watch read) when "
                     "the peer starts",
        "S144-RJ-DIAL": "the guest dials the replay-host FROM THE WORLD HUD: the engine's config line with the code and its "
                        "first 'relay connected ...?role=guest' both stamped after the walk began, every sample since the "
                        "world arrival on WorldHUD, 'GUEST game connected' and 'REPLAY start' within DIAL_S (decision 9)",
        "S144-RJ-ARM": "the world arm: rejoin.arms +1 with last F (the tape's field), the overlay 'rejoining' (detail F) "
                       "with decision 7's words on a sample, 'rejoining the peer at field F from world map 9011' logged",
        "S144-RJ-LAND": "the witness: FieldHUD on F within LAND_S of the replay's start; rejoin.lands +1, "
                        "follow.world_armed -1 at the end, 'world rejoin landed on field F' logged",
        "S144-RJ-MIRROR": "the arrival is a field follow's: 'state-mirror ARMED' after the landing, session.mirroring true, "
                          "the story marker reads the HOST's 0xA5 on F (the tape's byte, never the guest's own)",
    },
    "wait": {
        "S144-WT-I": "the instrument: 'paired on the host's field (6603)' and 'state-mirror ARMED' before the host's world "
                     "exit, the guest on FieldHUD 6603",
        "S144-WT-FIELD": "decision 5: within LINE_S (+ LINE_GRACE_S) of the host's exit the guest shows the waiting line "
                         "-- s144 tape: 'host_world' + its words + waitline 'host_world' + follow.host_world; s143 tape: "
                         "'host_away' + its words + waitline.fallback -- and is STILL on FieldHUD 6603 on every sample since",
        "S144-WT-FROZEN": "the guest walks out too and is FROZEN on the world map: `hold up` moves < HELD_U, freeze.on true "
                          "(why live / mirroring), skips advancing",
        "S144-WT-WORLD": "the same line on the world map (waitline the same) and -- an s144 tape -- the source-field hold "
                         "on 6603 released by the host's b6 ('... released: the host left it'), follow.hold -1",
    },
}
T2_PFX = {"rejoin": "S144-RJ", "wait": "S144-WT"}
#: [calibration] a GUEST before s144: the rows its stage cannot satisfy (the instrument rows never: a red there is the
#: instrument's)
T2_PREDICTED = {"rejoin": ("S144-RJ-DIAL", "S144-RJ-ARM", "S144-RJ-LAND", "S144-RJ-MIRROR"),
                "wait": ("S144-WT-FIELD", "S144-WT-FROZEN", "S144-WT-WORLD")}
#: the stand-in faults -> exactly the T2 rows each turns red (the stub peer's smoke; tests pin it)
T2_FAULT_REDS = {
    "rejoin": {"rejoin_field_recipe": ("S144-RJ-LAND", "S144-RJ-MIRROR"),   # armed (counted, the line), never lands
               "arm_uncounted": ("S144-RJ-ARM",),
               "line_s143": ("S144-RJ-ARM",)},                              # the world guest's chain absent: no line
    "wait": {"tail_s143": ("S144-WT-FIELD",),
             "line_s143": ("S144-WT-WORLD",),
             "dispatch_ungated": ("S144-WT-FROZEN",),
             "counters_dark": ("S144-WT-FROZEN",),
             "hold_unlatched": ("S144-WT-WORLD",)},                         # no hold: none for the host's b6 to release
}


def t2_catalog(leg: str, calibrate: bool) -> dict:
    cat = {"T2-TAPE": T2_COMMON["T2-TAPE"]}
    if leg == "rejoin":
        cat["T2-CAL"] = T2_COMMON["T2-CAL"]
    cat["T2-PEER"] = T2_COMMON["T2-PEER"] + (" (the rejoin leg's engine config line is RJ-DIAL's)" if leg == "rejoin" else
                                             f"; the engine's 'config enabled=True role=client ... code={CODE}'; the guest "
                                             "connected on 6603 and the replay started")
    cat.update(T2_CHECKS[leg])
    if calibrate:
        cat[f"{T2_PFX[leg]}-CAL"] = ("CALIBRATION: exactly the predicted rows are red for the GUEST's stage (before s144 "
                                     "T2_PREDICTED, on s144 none)")
    cat["T2-SAVE"] = T2_COMMON["T2-SAVE"]
    cat["T2-INI"] = T2_COMMON["T2-INI"]
    return cat


# ---- the duo
DUO_CHECKS = {
    "S144-D0": "the instrument: both on FieldHUD 6603, the guest mirroring (duo's C2-C6 paired them)",
    "S144-D1": "the host walks out of 6603 -> the guest LEFT on 6603 stays there and shows the waiting line ('host_world', "
               "its words, follow.host_world true)",
    "S144-D2": "the guest walks out too -> FROZEN on world 9011 (`hold up` < HELD_U; freeze.on, why live / mirroring), the "
               "line on the world map, the hold released by the host's b6",
    "S144-D3": "the host enters the Ice Cavern (the tile, Confirm) -> the guest REJOINS from the world map: FieldHUD 300 "
               "within REJOIN_S, rejoin.arms and lands +1, the rejoining and landed lines, mirroring",
}
DUO_PREDICTED = ("S144-D1", "S144-D2", "S144-D3")          # a GUEST before s144 (the duo cannot mix DLLs: both are)
DUO_FAULT_REDS = {"tail_s143": ("S144-D1",), "dispatch_ungated": ("S144-D2",), "line_s143": ("S144-D2", "S144-D3"),
                  "hold_unlatched": ("S144-D2",), "counters_dark": ("S144-D2",),
                  "rejoin_field_recipe": ("S144-D3",), "arm_uncounted": ("S144-D3",)}
#: duo.py's CLI calls ``d.pair(**PAIR)``: both games New Game onto 6603 (the host first), the roles from their own inis
PAIR = {"field": FARSHORE}


# ================================================================================================ the offline oracle
def _kit():
    pkg_root = cb.REPO / "ff9mapkit"
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    import ff9mapkit                                       # noqa: E402 - path pinned above
    where = Path(getattr(ff9mapkit, "__file__", "") or ".").resolve()
    if not where.is_relative_to(pkg_root):
        raise RuntimeError(f"ff9mapkit resolved to {where}, not this worktree's {pkg_root}")
    return ff9mapkit


def folder_order(game: Path) -> list:
    """Memoria.ini [Mod] FolderNames, highest priority first (READ-ONLY); the mod folders on disk when unreadable."""
    try:
        text = (Path(game) / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
        m = re.search(r'(?mi)^\s*FolderNames\s*=\s*(.+?)\s*$', text)
        if m:
            return re.findall(r'"([^"]+)"', m.group(1))
    except OSError:
        pass
    try:
        return sorted(p.name for p in Path(game).iterdir() if (p / "DictionaryPatch.txt").is_file())
    except OSError:
        return []


def deployed_field_eb(game: Path, field: int) -> tuple:
    """(bytes | None, where): the field's `.eb` (language us) from the highest-priority stacked folder whose
    DictionaryPatch registers it AND ships its EVT_<name>.eb.bytes. The line is ``FieldScene <id> <area> <map> <event>
    [<mes>]``: a BG-borrowing field's <map> is the BORROWED scene (6603's IFTR_MAP559_IF_CST_0), its <event> its own
    script (FARSHORE) -- the event name is read, the map name only when no event name follows. READ-ONLY."""
    for name in folder_order(game):
        d = Path(game) / name
        try:
            text = (d / "DictionaryPatch.txt").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.search(rf"(?m)^\s*FieldScene\s+{int(field)}\s+\d+\s+(\S+)(?:[ \t]+(\S+))?", text)
        if not m:
            continue
        evt = m.group(2) or m.group(1)
        p = d.joinpath(*EVT_DIR, "field", EVT_LANG, f"EVT_{evt}.eb.bytes")
        if p.is_file():
            return p.read_bytes(), str(p)
    return None, f"field {field}: no stacked mod folder registers it with an EVT_*.eb.bytes"


def deployed_world_eb(game: Path, name: str = WORLD_EB_NAME) -> tuple:
    """(bytes | None, where): the world dispatcher's `.eb` (us) from the highest-priority stacked folder shipping it; None
    with "stock" when none does (the dispatcher is then the game's own, in p0data -- not read here)."""
    for folder in folder_order(game):
        p = (Path(game) / folder).joinpath(*EVT_DIR, "world", EVT_LANG, name)
        if p.is_file():
            return p.read_bytes(), str(p)
    return None, "stock"


def block_overrides(game: Path, block=ICE_BLOCK) -> list:
    """Every stacked folder's override of world ``block`` (its Terrain / Terrain2 / Object meshes), READ-ONLY."""
    x, y = block
    hits = []
    for folder in folder_order(game):
        root = Path(game) / folder / "FF9_Data" / "WorldMap"
        if root.is_dir():
            hits += [str(p) for p in root.rglob(f"Block[[]{x}][[]{y}]*")]
    return hits


def toml_door(path: Path = LANDING_TOML) -> dict | None:
    """The landing toml's first worldmap [[gateway]]: {zone, to, arrive} (None when it has none)."""
    doc = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    for gw in doc.get("gateway") or []:
        if gw.get("to") == "worldmap":
            return {"zone": [list(map(float, q)) for q in gw.get("zone") or []], "to": gw.get("to"),
                    "arrive": tuple(float(v) for v in gw.get("arrive") or ())}
    return None


def forks_of(game: Path, donor: int = ICE_CAVERN) -> list:
    """Every stacked folder's ForkDonorPatch.txt mapping ``<fork> <donor>`` (DataPatchers.PatchForkDonors' format: one per line,
    # / ; comments), READ-ONLY -- the distinct fork ids, in folder order. Exactly one = ForkSiblingField(donor) lands every
    world entry into ``donor`` on that fork; two or more = ambiguous (the engine disables the remap: identity)."""
    out = []
    for folder in folder_order(game):
        try:
            text = (Path(game) / folder / "ForkDonorPatch.txt").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            s = line.strip()
            if not s or s[0] in "#;":
                continue
            parts = s.split()
            if len(parts) >= 2 and parts[0].lstrip("-").isdigit() and parts[1].lstrip("-").isdigit() and int(parts[1]) == donor:
                if int(parts[0]) not in out:
                    out.append(int(parts[0]))
    return out


def scene_registered(scene: int) -> bool:
    """The kit's battle scene table (ff9mapkit._scenedb.SCENES: Memoria's open-source SceneData name -> id, the ids the
    engine's Battle.mapName registers) has ``scene``."""
    _kit()
    from ff9mapkit._scenedb import SCENES
    return int(scene) in set(SCENES.values())


def read_oracle(game: Path) -> dict:
    """The offline oracle (S144-OR): ``problems`` names every fact that does not hold (empty = the route and its targets
    are what the bench assumes); ``facts`` what was read."""
    out = {"problems": {}, "facts": {}}
    try:
        door = toml_door()
    except (OSError, ValueError) as err:
        door = None
        out["problems"]["toml"] = f"{LANDING_TOML.name}: {type(err).__name__}: {str(err)[:160]}"
    if door is not None:
        out["facts"]["door"] = door
        if door["zone"] != [list(map(float, q)) for q in FS_DOOR] or tuple(door["arrive"]) != FS_LANDING:
            out["problems"]["door"] = f"the landing toml's door {door} is not FS_DOOR -> {FS_LANDING}"
    elif "toml" not in out["problems"]:
        out["problems"]["door"] = f"{LANDING_TOML.name} has no worldmap [[gateway]]"
    eb, where = deployed_field_eb(Path(game), FARSHORE)
    if eb is None:
        out["problems"]["eb 6603"] = where
    else:
        try:
            _kit()
            from ff9mapkit import eventscan
            exits = list(eventscan.scan_all_warps(eb)["overworld_exits"])
        except Exception as err:                          # noqa: BLE001 - a parse fault is a named problem
            exits = []
            out["problems"]["eb 6603"] = f"{where}: {type(err).__name__}: {str(err)[:160]}"
        out["facts"]["exits"] = exits
        if WORLD not in exits and "eb 6603" not in out["problems"]:
            out["problems"]["eb 6603"] = f"{where}: its WorldMap() operands {exits} do not hold {WORLD}"
    web, wwhere = deployed_world_eb(Path(game))
    out["facts"]["world_eb"] = wwhere
    if web is not None:
        try:
            _kit()
            from ff9mapkit import eventscan
            w = eventscan.scan_all_warps(web)
            tos = {x["to"] for x in w["scripted"]} | {x["to"] for x in w["walk_in"]}
        except Exception as err:                          # noqa: BLE001
            tos = set()
            out["problems"]["world eb"] = f"{wwhere}: {type(err).__name__}: {str(err)[:160]}"
        if ICE_CAVERN not in tos and "world eb" not in out["problems"]:
            out["problems"]["world eb"] = f"{wwhere}: no Field({ICE_CAVERN}) -- the Ice Cavern's dispatch is gone"
    over = block_overrides(Path(game))
    if over:
        out["problems"]["block"] = f"block {ICE_BLOCK} is overridden: {over[:3]} -- the tile round 8 entered is not there"
    forks = forks_of(Path(game))
    out["facts"]["forks_300"] = forks
    if len(forks) == 1:
        out["problems"]["fork"] = (f"field {ICE_CAVERN} is forked by {forks[0]} (ForkDonorPatch.txt): every world entry into it "
                                   f"lands on the fork (ForkSiblingField) -- F5 and the rejoin rows judge FieldHUD {ICE_CAVERN}")
    try:
        if not scene_registered(SCENE):
            out["problems"]["scene"] = f"battle scene {SCENE} is not in the kit's scene table"
    except Exception as err:                              # noqa: BLE001
        out["problems"]["scene"] = f"the scene table is unreadable: {type(err).__name__}: {err}"
    return out


# ================================================================================================ pure readers / judges
def _w(x, key, default=None):
    """A ``netsync.world`` leaf (absent = ``default``: an engine without the block)."""
    return cb.path(x, "netsync.world." + key, default)


def _f(x, key, default=None):
    """A ``netsync.session.follow`` leaf."""
    return cb.path(x, "netsync.session.follow." + key, default)


def _s(x, key, default=None):
    """A ``netsync.session`` leaf."""
    return cb.path(x, "netsync.session." + key, default)


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _delta(a, b, key):
    """b's ``netsync.world.<key>`` - a's; None when either is absent (never a zero)."""
    va, vb = _num(_w(a, key)), _num(_w(b, key))
    return None if va is None or vb is None else vb - va


def world_xz(x) -> tuple:
    w = cb.raw(x).get("world") or {}
    return w.get("x"), w.get("z")


def dist(a, b) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def stage_of(x) -> int:
    """144 when the engine publishes `netsync.world.freeze`; else the R3 ladder's highest patch (cb.r3_stage_of)."""
    return 144 if cb.has(x, PROBE) else cb.r3_stage_of(x)


def judge_probe(st, lines) -> tuple:
    """P0 (PURE): the s144 blocks in the agent's key order and the three proof lines OK, none FAIL."""
    R = _bw()
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}` -- an engine before s144"
    world = cb.path(st, "netsync.world") or {}
    follow = cb.path(st, "netsync.session.follow")
    keys_ok = (list(world) == list(R.WORLD_SENTINELS)
               and all(list(world.get(k) or {}) == list(R.WORLD_SENTINELS[k]) for k in R.WORLD_SENTINELS)
               and isinstance(follow, dict) and list(follow) == list(R.SESSION_FOLLOW_SENTINELS)
               and cb.has(st, "netsync.session.overlay_text"))
    proofs = [(R.PROOF_WORLD_FREEZE, R.WORLD_FREEZE_SELFTEST_ROWS), (R.PROOF_WORLD_REJOIN, R.WORLD_REJOIN_SELFTEST_ROWS),
              (R.PROOF_OVERLAY_TEXT, R.OVERLAY_TEXT_SELFTEST_ROWS)]
    seen = {head: cb.count(lines, f"{head}OK ({n} rows)") for head, n in proofs}
    fails = {head: cb.count(lines, head + "FAIL") for head, _n in proofs}
    ok = keys_ok and all(v >= 1 for v in seen.values()) and not any(fails.values())
    return ok, (f"world {list(world)} ({ {k: list(world.get(k) or {}) for k in world} }); follow "
                f"{list(follow or {})}; overlay_text {'present' if cb.has(st, 'netsync.session.overlay_text') else 'ABSENT'};"
                f" proof lines OK {seen}, FAIL {fails}")


def judge_rest(st, *, lever: bool) -> tuple:
    """P1's lever (PURE): `netsync.world.freeze.off` as set, the field-gate bench on."""
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}` (the lever's keys)"
    off, bench = _w(st, "freeze.off"), cb.path(st, "netsync.bench")
    return off is bool(lever) and bench is True, f"freeze.off {off!r} (want {lever}), netsync.bench {bench!r}"


def judge_route(st) -> tuple:
    """ROUTE (PURE): WorldHUD, world 9011, within ROUTE_TOL of the landing."""
    x, z = world_xz(st)
    if not (st is not None and st.ui_state == "WorldHUD" and x is not None):
        return False, f"not on the world map (ui {getattr(st, 'ui_state', None)!r}, field {getattr(st, 'field_id', None)})"
    d = dist((x, z), FS_LANDING)
    return st.world_id == WORLD and d <= ROUTE_TOL, f"world {st.world_id} at ({x:.2f}, {z:.2f}), {d:.1f}u from {FS_LANDING}"


def judge_hold(st, lines, *, src: int = FARSHORE, wld: int = WORLD) -> tuple:
    """F0 (PURE): follow.hold == src and the hold line once."""
    if not cb.has(st, "netsync.session.follow.hold"):
        return False, "absent: no `netsync.session.follow.hold`"
    hold = _f(st, "hold")
    n = cb.count(lines, _bw().log_world_hold_latched(src, wld))
    return hold == src and n == 1, f"follow.hold {hold!r} (want {src}); the hold line logged {n}x"


def judge_walk(moved, advanced, frames: int, *, held: bool) -> tuple:
    """F1 / F4 / F5 / F6 / WT-FROZEN / D2's witness (PURE): the hold ran (frames advanced >= its length) and the walker
    moved < HELD_U (``held``) or > HELD_U."""
    if moved is None or advanced is None:
        return False, "not reached: no world position read around the hold"
    ran = advanced >= frames
    ok = ran and (moved < HELD_U if held else moved > HELD_U)
    return ok, (f"`hold up` {frames} frames: moved {moved:.2f}u over {advanced} advancing frames (want "
                f"{'< ' if held else '> '}{HELD_U:g}u{'' if ran else '; the hold never ran its frames'})")


def judge_freeze_keys(st, base, lines, *, why: str = "bench", wld: int = WORLD) -> tuple:
    """F1K (PURE): on, why, skips +SKIPS_MIN, edges exactly +1 since ``base``, the ON line once."""
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}`"
    fz = _w(st, "freeze") or {}
    ds, de = _delta(base, st, "freeze.skips"), _delta(base, st, "freeze.edges")
    n = cb.count(lines, _bw().log_world_freeze_on(why, wld))
    ok = fz.get("on") is True and fz.get("why") == why and (ds or 0) >= SKIPS_MIN and de == 1 and n == 1
    return ok, f"freeze on {fz.get('on')!r} why {fz.get('why')!r}; skips +{ds} edges +{de}; the ON line {n}x"


def judge_stay(samples, *, field: int = ICE_CAVERN) -> tuple:
    """A refused entry (PURE): every sample on WorldHUD, none on ``field``."""
    if not samples:
        return False, "not reached: no sample read after the press"
    off = [(cb.raw(s).get("frame"), s.ui_state, s.field_id) for s in samples
           if s.ui_state != "WorldHUD" or (s.on_field and s.field_id == field)]
    return not off, f"{len(samples)} sample(s) over the window: " + (f"LEFT the world map {off[:3]}" if off else
                                                                     "all WorldHUD")


def judge_confirm(samples, k0, k1, lines, *, wld: int = WORLD, want_keys: bool = True) -> tuple:
    """F2 / F4's Confirm (PURE): stayed; keys +1 or more (``want_keys``) or unchanged; F2: the world-poll line once in
    ``lines`` -- the PROCESS's log: DeclineOnceHere latches one line per class per world map per process."""
    s_ok, s_why = judge_stay(samples)
    if k0 is None or k1 is None:
        return False, f"{s_why}; absent: no `netsync.world.freeze.keys`"
    dk = k1 - k0
    if not want_keys:
        return s_ok and dk == 0, f"{s_why}; keys {k0} -> {k1} (want unchanged)"
    n = cb.count(lines, _bw().decline_line(_bw().WORLD_POLL_DECLINE, f"world map {wld}"))
    return s_ok and dk >= 1 and n == 1, f"{s_why}; keys {k0} -> {k1} (want +1 or more); the poll line {n}x"


def judge_map(st0, window, after, lines, *, wld: int = WORLD) -> tuple:
    """F3 (PURE): over ``window`` (Select's MAP_S, before the Cancel): map +1 or more, its line once (``lines``: the process's
    log -- RefuseWorldUi's line latches per world map per process), the dispatcher still
    asked (skips advance >= SKIPS_MIN / 2 there: an open full map's w_naviMode 2 stops it -- the one read of the map's
    state the agent publishes); over ``after`` (the Cancel's): still WorldHUD; across both the walker where it stood."""
    if not window or not cb.has(st0, PROBE):
        return False, "not reached: no sample" if not window else f"absent: no `{PROBE}`"
    last = window[-1]
    dm, ds = _delta(st0, last, "freeze.map"), _delta(st0, last, "freeze.skips")
    n = cb.count(lines, _bw().decline_line(_bw().WORLD_UI_DECLINE_MAP, f"world map {wld}"))
    x0 = world_xz(st0)
    both = list(window) + list(after)
    moved = max((dist(world_xz(s), x0) for s in both if world_xz(s)[0] is not None and x0[0] is not None), default=None)
    s_ok = all(s.ui_state == "WorldHUD" for s in both)
    asked = (ds or 0) >= SKIPS_MIN // 2
    ok = (dm or 0) >= 1 and n == 1 and asked and s_ok and moved is not None and moved < HELD_U
    return ok, (f"map +{dm}; the full-map line {n}x; skips +{ds} over Select's {len(window)} sample(s) ("
                + ("the dispatcher still asked: the map shut" if asked else
                   "the dispatcher NOT asked under a holding freeze: the map opened, or the freeze lifted")
                + f"); all WorldHUD through the Cancel {s_ok}; moved {moved}")


def judge_edge(base, st, moved, advanced) -> tuple:
    """F6 (PURE): edges +1 since ``base`` (the second world load) and the walker held."""
    w_ok, w_why = judge_walk(moved, advanced, EDGE_FRAMES, held=True)
    de = _delta(base, st, "freeze.edges")
    return w_ok and de == 1, f"edges +{de} (want exactly 1: the field load reset the edge); {w_why}"


def judge_lever(st) -> tuple:
    """F4's keys (PURE): on false, off true."""
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}`"
    fz = _w(st, "freeze") or {}
    return fz.get("on") is False and fz.get("off") is True, f"freeze on {fz.get('on')!r} off {fz.get('off')!r}"


def judge_battle_start(st, epoch0, statuses, lines, *, scene: int = SCENE, group: int = GROUP, wld: int = WORLD) -> tuple:
    """B1 (PURE): BattleHUD on a new epoch, the started status among ``statuses`` (every debug_status read), its line once."""
    R = _bw()
    want = R.world_battle_started(scene, group, True, wld)
    n = cb.count(lines, want)
    ok = (st is not None and st.ui_state == "BattleHUD" and st.battle_epoch > (epoch0 or 0) and want in statuses and n == 1)
    return ok, (f"ui {getattr(st, 'ui_state', None)!r}, epoch {epoch0} -> {getattr(st, 'battle_epoch', None)}; status "
                f"{want!r} {'read' if want in statuses else 'NOT read'} (read {sorted({s for s in statuses if s})[:3]}); "
                f"its line {n}x")


def judge_swirl(samples) -> tuple:
    """B2 (PURE): a publish with world.next_mode 2 and the shared latch busy. No publish at all on the live WorldMap scene
    after the verb (world.next_mode -1 / absent on every one: the window is a few frames) is 'not reached' -- the
    instrument's, never the engine's red."""
    hits = [s for s in samples if cb.path(s, "world.next_mode") == 2]
    busy = [s for s in hits if _w(s, "rejoin.latch") is True]
    live = [s for s in samples if isinstance(cb.path(s, "world.next_mode"), int) and cb.path(s, "world.next_mode") >= 0]
    if not busy and not hits and not any(cb.path(s, "world.next_mode") != 3 for s in live):
        return False, (f"not reached: {len(samples)} publish(es) from the verb to the battle, none on the live WorldMap scene "
                       f"after the one-shot fired ({len(live)} on it, all next_mode 3) -- the swirl's window fell between "
                       f"two writes (the instrument)")
    return bool(busy), (f"{len(samples)} publish(es) from the verb to the battle: next_mode 2 on {len(hits)}, with the "
                        f"latch busy on {len(busy)}")


def judge_return(st, before, *, wld: int = WORLD) -> tuple:
    """B3 (PURE): WorldHUD on ``wld``, within RETURN_TOL of ``before`` (x, z), next_mode 3."""
    x, z = world_xz(st) if st is not None else (None, None)
    if st is None or st.ui_state != "WorldHUD" or x is None or before[0] is None:
        return False, (f"not back on the world map: ui {getattr(st, 'ui_state', None)!r}, field "
                       f"{getattr(st, 'field_id', None)}")
    d = dist((x, z), before)
    nm = cb.path(st, "world.next_mode")
    return st.world_id == wld and d <= RETURN_TOL and nm == 3, (f"world {st.world_id} at ({x:.2f}, {z:.2f}), {d:.2f}u from "
                                                                f"the battle's start {before}; next_mode {nm!r}")


def judge_line(st, *, b6: bool, field: int | None = None) -> tuple:
    """WT-FIELD / WT-WORLD / D1 / D2's line (PURE): an s144 host's b6 -> 'host_world' with its words, waitline 'host_world'
    and follow.host_world; no b6 (an old host) -> 'host_away' with its words and waitline.fallback."""
    R = _bw()
    ovl, text = _s(st, "overlay"), _s(st, "overlay_text")
    line, fb = _w(st, "waitline.line"), _w(st, "waitline.fallback")
    if b6:
        ok = (ovl == "host_world" and text == R.WAIT_TEXT_HOST_WORLD and line == "host_world"
              and _f(st, "host_world") is True)
    else:
        ok = ovl == "host_away" and text == R.WAIT_TEXT_HOST_AWAY and line == "away" and fb is True
    where = (f"ui {st.ui_state!r} field {st.field_id}" if field is None else
             f"ui {st.ui_state!r} field {st.field_id} (want FieldHUD {field})")
    return ok, (f"{where}; overlay {ovl!r}, text {text!r}, waitline {line!r} fallback {fb!r}, follow.host_world "
                f"{_f(st, 'host_world')!r} (want {'host_world' if b6 else 'host_away'})")


def judge_frozen(st, moved, advanced, base) -> tuple:
    """WT-FROZEN / D2's freeze (PURE): the walk held, freeze.on true, why live / mirroring, skips advancing."""
    w_ok, w_why = judge_walk(moved, advanced, WALK_FRAMES, held=True)
    if not cb.has(st, PROBE):
        return False, f"{w_why}; absent: no `{PROBE}`"
    fz = _w(st, "freeze") or {}
    ds = _delta(base, st, "freeze.skips")
    ok = w_ok and fz.get("on") is True and fz.get("why") in ("live", "mirroring") and (ds or 0) >= SKIPS_MIN
    return ok, f"{w_why}; freeze on {fz.get('on')!r} why {fz.get('why')!r}; skips +{ds}"


def judge_rejoin_arm(samples, base, lines, *, field: int, wld: int = WORLD) -> tuple:
    """RJ-ARM / D3's arm (PURE): arms +1 or more and last ``field`` (on the last sample), a sample with overlay 'rejoining'
    detail ``field`` and the words, the rejoining line logged."""
    R = _bw()
    if not samples or not cb.has(samples[-1], "netsync.world.rejoin"):
        return False, "absent: no `netsync.world.rejoin`" if samples else "not reached: no sample"
    last = samples[-1]
    da = _delta(base, last, "rejoin.arms")
    words = R.wait_line_text(R.OVL_REJOINING, field)
    shown = any(_s(s, "overlay") == "rejoining" and _s(s, "overlay_detail") == field and _s(s, "overlay_text") == words
                for s in samples)
    n = cb.count(lines, f"rejoining the peer at field {field} from world map {wld}")
    ok = (da or 0) >= 1 and _w(last, "rejoin.last") == field and shown and n >= 1
    return ok, (f"arms +{da}, last {_w(last, 'rejoin.last')!r} (want {field}); the overlay 'rejoining' {field} with "
                f"{words!r} {'shown' if shown else 'NOT shown'}; the rejoining line {n}x")


def judge_rejoin_land(samples, base, lines, *, field: int) -> tuple:
    """RJ-LAND / D3's landing (PURE): a sample FieldHUD on ``field``, lands +1 or more, world_armed -1 at the end, the
    landed line logged."""
    if not samples:
        return False, "not reached: no sample"
    on = [s for s in samples if s.ui_state == "FieldHUD" and s.field_id == field]
    last = samples[-1]
    dl = _delta(base, last, "rejoin.lands")
    armed = _f(last, "world_armed")
    n = cb.count(lines, f"world rejoin landed on field {field}")
    where = sorted({(s.ui_state, s.field_id if s.on_field else s.world_id) for s in samples})[:4]
    ok = bool(on) and (dl or 0) >= 1 and armed == -1 and n >= 1
    return ok, (f"FieldHUD {field} on {len(on)} of {len(samples)} sample(s) (seen {where}); lands +{dl}, world_armed "
                f"{armed!r} at the end; the landed line {n}x")


def judge_mirror(before, after, lines, *, field: int) -> tuple:
    """RJ-MIRROR (PURE): the mirror armed AT the landing -- no sample ``before`` it mirroring (the guest walked out alone:
    no session, no mirror), 'state-mirror ARMED' in ``lines`` (logged since the replay started: the engine's whole-second
    stamp may precede the first FieldHUD read), mirroring true on the last sample ``after`` it, and the host's marker
    (0xA5) on a FieldHUD sample on ``field``."""
    armed = cb.count(lines, "state-mirror ARMED -- this guest's fields now stage the HOST's story")
    early = [cb.raw(s).get("frame") for s in before if _s(s, "mirroring") is True]
    on = [s for s in after if s.ui_state == "FieldHUD" and s.field_id == field]
    marks = sorted({pb.marker_value(s) for s in on}, key=lambda v: -1 if v is None else v)
    mir = _s(after[-1], "mirroring") if after else None
    ok = bool(after) and armed >= 1 and not early and mir is True and pb.MARKER_VALUE in marks
    return ok, (f"'state-mirror ARMED' {armed}x since the replay started; mirroring before the landing on "
                f"{len(early)} sample(s) (want none), at the end {mir!r}; the marker on field {field} read "
                f"{[hex(m) if isinstance(m, int) else m for m in marks]} (want 0x{pb.MARKER_VALUE:02X}, the host's)")


# ================================================================================================ the moves
def _poll(g, pred, timeout: float, what: str):
    return cb.poll(g, pred, timeout, what)


def walk_out(g, *, tries: int = 3, before_walk=None) -> tuple:
    """6603's door, the proven way: calibrate_axes with the door quad as a hazard (a probe never walks into it), walk_to
    a point inside it (strict=False, halt_on_transition), wait_world, world_settle, encounters off. (ok, why, state).
    ``before_walk``: called once right before the walk itself (after calibrate_axes -- the T2 rejoin leg stamps the moment
    the guest began to leave the field there)."""
    for attempt in range(tries):
        try:
            g.calibrate_axes(hazards=[FS_DOOR], recalibrate=attempt > 0)
            break
        except HarnessError as err:
            if attempt == tries - 1:
                return False, f"calibrate_axes on {FARSHORE} failed {tries}x: {str(err)[:200]}", g.state
            g.note(f"calibrate_axes retry {attempt + 1}: {str(err)[:160]}")
            try:
                g.warp(FARSHORE)
                g.wait_frames(90)
            except HarnessError as err2:
                return False, f"the re-warp to {FARSHORE} failed: {str(err2)[:200]}", g.state
    if before_walk is not None:
        before_walk()
    try:
        g.walk_to(*FS_EXIT, strict=False, halt_on_transition=True)
        g.wait_world(timeout=WORLD_S)
        g.wait_frames(30)                                  # the all-block load: frames advance past it
        st = g.world_settle()
    except HarnessError as err:
        return False, f"the walk out never reached the world map: {str(err)[:240]}", g.state
    try:
        g.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        g.note(f"noencounter refused on the world map ({str(err)[:120]})")
    ok, why = judge_route(st)
    return ok, why, st


def hold_walk(g, frames: int = WALK_FRAMES, button: str = "up") -> tuple:
    """`hold <button> <frames>` on the world map, every publish read meanwhile -> (moved, advanced, final state): the
    largest x/z displacement from the settled start over the samples, and the frames that advanced."""
    st0 = g.world_settle()
    x0 = world_xz(st0)
    f0 = cb.raw(st0).get("frame", 0)
    try:
        g.send(f"hold {button} {int(frames)}", f"wait {int(frames) + 6}")
    except HarnessError as err:
        g.note(f"hold {button} refused: {str(err)[:160]}")
        return None, None, g.state
    samples = cb.hold_for(g, 0.3)
    st1 = g.world_settle()
    pts = [s for s in [st0, *samples, st1] if s is not None and s.on_world and world_xz(s)[0] is not None]
    if x0[0] is None or not pts:
        return None, None, st1
    moved = max(dist(world_xz(s), x0) for s in pts)
    return moved, int(cb.raw(st1).get("frame", 0)) - int(f0), st1


def teleport_settle(g, xz) -> object:
    g.teleport(*xz)
    st = g.world_settle()
    return st


def press_confirm_watch(g, seconds: float = STAY_S) -> list:
    g.press("confirm")
    samples, _ = cb.watch(g, lambda s: False, seconds)
    return samples


def _reach_world_again(g) -> tuple:
    """From a field (300 or anything): warp 6603 and walk out again. (ok, why, state)."""
    try:
        if g.state.ui_state == "WorldHUD":
            g.world_warp(FARSHORE)
        else:
            g.warp(FARSHORE)
        g.wait_frames(45)
    except HarnessError as err:
        return False, f"the way back to {FARSHORE} failed: {str(err)[:200]}", g.state
    return walk_out(g)


# ================================================================================================ the run
def run(g, field: int | None = None):
    leg = LEG
    if leg is None:
        led = cb.Ledger(g, {"T2-TAPE": T2_COMMON["T2-TAPE"]})
        led.check("T2-TAPE", False, f"COOP_WORLD_LEG={_RAW_LEG!r} is no leg: one of {LEGS}")
        return
    if field is not None and field != FARSHORE:
        g.note(f"--field {field} is ignored: the bench runs on {FARSHORE} and the world map")
    if leg == "solo":
        _run_solo(g)
    else:
        _run_t2(g, leg)


# ---------------------------------------------------------------------------------------------- SOLO
def _run_solo(g) -> None:
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, solo_catalog(calibrate), finals=("S144-R", "S144-CAL"))
    ctx = {"calibrate": calibrate, "lever": False, "stage": None, "mark0": 0}
    try:
        _solo(g, led, ctx)
    except HarnessError as err:
        g.note(f"the solo leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'world-wait-solo')}")
        led.close()
        _release_solo(g, led, ctx)
        if calibrate:
            stage = ctx.get("stage")
            if stage is None:
                led.check("S144-CAL", False, "no engine stage was read (the run died before P0)")
            else:
                led.judge_calibration("S144-CAL", OLD_PREDICTED if stage < 144 else LEVER_PREDICTED)
        led.close(final=True)


def _ini_ok(g) -> tuple:
    en = cb.ini_value(g, "Netsync", "Enabled")
    ok = en is None or str(en).strip() in ("0", "")
    return ok, f"[Netsync] Enabled {en!r}" + ("" if ok else " -- the selftest role needs it off (selftest_block.sh)")


def _solo(g, led: cb.Ledger, ctx: dict) -> None:
    ctx["mark0"] = cb.mark(g)
    ok, why = _ini_ok(g)
    led.check("S144-INI", ok, why)
    if not ok:
        led.close("the install's ini refuses the bench (S144-INI)")
        return
    oracle = read_oracle(Path(g.game_path))
    ctx["oracle"] = oracle
    led.check("S144-OR", not oracle["problems"], f"problems {oracle['problems'] or 'none'}; read {oracle['facts']}")
    ok, why = cb.setup(g, FARSHORE, label="s144: world-map co-op, wait then rejoin -- the solo bench"
                                          + (" -- CALIBRATION" if ctx["calibrate"] else ""))
    led.check("S144-S0", ok and g.state.field_id == FARSHORE, why + f"; on field {g.state.field_id}")
    if not ok:
        led.close(f"the selftest role never came up -- {why}")
        return
    st = g.state
    ctx["stage"] = stage_of(st)
    g.note(f"engine stage: s{ctx['stage']} ({cb.stage_note(st)})")
    led.check("S144-P0", *judge_probe(st, cb.log_lines(g)))
    _p1(g, led, ctx)
    base = g.state
    at = cb.mark(g)
    ok, why, st = walk_out(g)
    led.check("S144-ROUTE", ok, why)
    if not ok:
        led.unreached(WORLD_ROWS, f"the walk out never landed on world {WORLD} (ROUTE): {why[:160]}")
        return
    st = _poll(g, lambda s: _f(s, "hold") == FARSHORE, 3.0, "the source-field hold") or g.state
    led.check("S144-F0", *judge_hold(st, cb.new(g, at)))
    _leg_freeze(g, led, ctx, base, at)
    _leg_battle(g, led, ctx)


def _p1(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why = cb.try_ns(g, "bench", 1)
    st = _poll(g, lambda s: (s.netsync or {}).get("bench") is True, 3.0, "the field-gate bench") or g.state
    if not ok:
        led.check("S144-P1", False, f"`netsync bench 1` refused: {why}")
        return
    if ctx["calibrate"] and (ctx["stage"] or 0) >= 144:
        at = cb.mark(g)
        okl, whyl = cb.try_ns(g, "bench", "worldfreeze", "off")
        ctx["lever"] = okl
        lines = cb.wait_log(g, at, _bw().LOG_WORLD_FREEZE_OFF, 2.0)
        st = _poll(g, lambda s: _w(s, "freeze.off") is True, 3.0, "the lever") or g.state
        r_ok, r_why = judge_rest(st, lever=True)
        n = cb.count(lines, _bw().LOG_WORLD_FREEZE_OFF)
        led.check("S144-P1", okl and r_ok and n == 1, whyl or f"{r_why}; the OFF line {n}x")
        g.note("CALIBRATION: `bench worldfreeze off` pulled -- the pre-s144 world map at every freeze seam, through F6")
        return
    if ctx["calibrate"]:
        g.note(f"CALIBRATION on s{ctx['stage']}: no `{PROBE}` -- `bench worldfreeze` is NEVER sent (an s143 agent reads "
               "it as `bench 1`)")
    led.check("S144-P1", *judge_rest(st, lever=False))


def _leg_freeze(g, led: cb.Ledger, ctx: dict, base, at: int) -> None:
    # F1 / F1K at the landing
    moved, adv, st = hold_walk(g, WALK_FRAMES)
    led.check("S144-F1", *judge_walk(moved, adv, WALK_FRAMES, held=True))
    led.check("S144-F1K", *judge_freeze_keys(st, base, cb.new(g, at)))
    # F2 the Ice Cavern tile
    try:
        st = teleport_settle(g, ICE_TILE)
        g.wait_frames(PROMPT_FRAMES)
        k0 = _num(_w(g.state, "freeze.keys"))
        samples = press_confirm_watch(g)
        k1 = _num(_w(g.state, "freeze.keys"))
        led.check("S144-F2", *judge_confirm(samples, k0, k1, cb.log_lines(g)))      # the latch: once a process
    except HarnessError as err:
        led.check("S144-F2", False, f"not reached: {str(err)[:240]}")
    if g.state.ui_state != "WorldHUD":
        led.unreached(("S144-F3", "S144-F6", "S144-F4", "S144-F5"), f"the Confirm left the world map "
                      f"(ui {g.state.ui_state!r}, field {g.state.field_id}) -- the freeze did not hold the entry")
        _back_to_world_after_entry(g)
    else:
        # F3 the full map
        try:
            st0 = teleport_settle(g, FS_LANDING)
            g.press("select")
            samples, _ = cb.watch(g, lambda s: False, MAP_S)
            g.press("cancel")                              # stock: Cancel closes no full map (frozen: nothing at all)
            after, _ = cb.watch(g, lambda s: False, 1.0)
            led.check("S144-F3", *judge_map(st0, samples, after, cb.log_lines(g)))  # the latch: once a process
            if CLOSE_MAP:
                close_opened_map(g, st0, samples)
        except HarnessError as err:
            led.check("S144-F3", False, f"not reached: {str(err)[:240]}")
        # F6 a second world load
        st_b = g.state
        ok, why, _st = _reach_world_again(g)
        if not ok:
            led.check("S144-F6", False, f"not reached: {why}")
        else:
            moved, adv, st = hold_walk(g, EDGE_FRAMES)
            led.check("S144-F6", *judge_edge(st_b, st, moved, adv))
    if g.state.ui_state != "WorldHUD":
        led.unreached(("S144-F4", "S144-F5"), f"not on the world map (ui {g.state.ui_state!r})")
        return
    _leg_lever(g, led, ctx)
    _leg_control(g, led, ctx)


def _leg_lever(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why = cb.try_ns(g, "bench", "worldfreeze", "off")
    if not ok:
        led.check("S144-F4", False, f"the lever cannot be sent: {why}")
        return
    ctx["lever"] = True
    try:
        teleport_settle(g, FS_LANDING)
        st = _poll(g, lambda s: _w(s, "freeze.off") is True, 3.0, "the lever") or g.state
        moved, adv, st = hold_walk(g, WALK_FRAMES)
        w_ok, w_why = judge_walk(moved, adv, WALK_FRAMES, held=False)
        l_ok, l_why = judge_lever(st)
        teleport_settle(g, ICE_TILE)
        g.wait_frames(PROMPT_FRAMES)
        k0 = _num(_w(g.state, "freeze.keys"))
        samples = press_confirm_watch(g)
        k1 = _num(_w(g.state, "freeze.keys"))
        c_ok, c_why = judge_confirm(samples, k0, k1, (), want_keys=False)
        led.check("S144-F4", w_ok and l_ok and c_ok, f"WALK {w_why}; KEYS {l_why}; CONFIRM {c_why}")
    except HarnessError as err:
        led.check("S144-F4", False, f"not reached: {str(err)[:240]}")
    if g.state.ui_state != "WorldHUD":
        _back_to_world_after_entry(g)


def _leg_control(g, led: cb.Ledger, ctx: dict) -> None:
    if cb.has(g.state, PROBE):
        cb.try_ns(g, "bench", "worldfreeze", "on")         # the lever back ON first: `bench 0` must be the only release
    ok, why = cb.try_ns(g, "bench", 0)
    if not ok:
        led.check("S144-F5", False, f"`netsync bench 0` refused: {why}")
        return
    try:
        if g.state.ui_state != "WorldHUD":
            okw, whyw, _st = _reach_world_again(g)
            if not okw:
                led.check("S144-F5", False, f"not reached: {whyw}")
                return
        teleport_settle(g, FS_LANDING)
        moved, adv, _st = hold_walk(g, WALK_FRAMES)
        w_ok, w_why = judge_walk(moved, adv, WALK_FRAMES, held=False)
        teleport_settle(g, ICE_TILE)
        g.wait_frames(PROMPT_FRAMES)
        g.press("confirm")
        st = _poll(g, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, FIELD_S, "field 300")
        e_ok = st is not None
        led.check("S144-F5", w_ok and e_ok, f"WALK {w_why}; ENTRY " + ("FieldHUD 300" if e_ok else
                                                                     f"never entered 300 (ui {g.state.ui_state!r}, "
                                                                     f"field {g.state.field_id})"))
    except HarnessError as err:
        led.check("S144-F5", False, f"not reached: {str(err)[:240]}")


def map_opened(st0, window) -> bool:
    """(PURE) Did F3's Select OPEN the full map? An engine without the keys (s143): it does (no refusal there); else when
    `map` never counted over the window, or the dispatcher stopped being asked (skips stalled: w_naviMode 2)."""
    if not window or not cb.has(st0, PROBE):
        return True
    last = window[-1]
    dm, ds = _delta(st0, last, "freeze.map"), _delta(st0, last, "freeze.skips")
    return (dm or 0) < 1 or (ds or 0) < SKIPS_MIN // 2


def close_opened_map(g, st0, window) -> None:
    """After F3's judged window: a full map that opened (map_opened) is closed by a SECOND Select -- the only stock close
    (WorldHUD.OnKeySelect's FullMap branch; Cancel never closes it) -- then the dispatcher is confirmed asked again (skips
    advancing) before F6. A map the freeze kept shut is left alone: another Select would only be refused (and counted)."""
    if not map_opened(st0, window):
        return
    g.press("select")
    g.wait_frames(20)
    a = g.state
    if not cb.has(a, PROBE):
        g.note("F3: the opened full map closed with a second Select (no keys to confirm it on this engine)")
        return
    if _w(a, "freeze.on") is not True:
        g.note("F3: the opened full map closed with a second Select (unfrozen: no `skips` count can confirm it)")
        return
    st = _poll(g, lambda s: (_delta(a, s, "freeze.skips") or 0) >= 4, 3.0, "the dispatcher asked again")
    g.note("F3: the opened full map closed with a second Select -- " + ("the dispatcher is asked again" if st is not None
                                                                         else "the dispatcher still NOT asked"))


def _back_to_world_after_entry(g) -> None:
    """A Confirm that ENTERED the location (a fault, an engine without the freeze): back to 6603 and out again."""
    ok, why, _st = _reach_world_again(g)
    g.note(f"back on the world map after an entry: {ok} ({why[:160]})")


def _leg_battle(g, led: cb.Ledger, ctx: dict) -> None:
    rows = ("S144-B1", "S144-B2", "S144-B3")
    ok, why, st = _reach_world_again(g)
    if not ok:
        led.unreached(rows, f"the world map never came back for the battle leg: {why[:160]}")
        return
    before = world_xz(st)
    epoch0 = st.battle_epoch
    f0 = int(cb.raw(st).get("frame", 0))
    at = cb.mark(g)
    if st.world_next_mode is None:
        okr, whyr = cb.try_send(g, f"battle {SCENE} {GROUP} rand")
        led.check("S144-B1", False, f"the driver refuses world_battle (no `world.next_mode`: an engine before s144); the raw "
                                    f"`battle {SCENE} {GROUP} rand` on WorldHUD answered "
                                    f"{'ACCEPTED' if okr else repr(whyr[:120])}")
        led.unreached(rows[1:], "no world battle on this engine (B1)")
        return
    _state_every(g, 1)                                     # the swirl's readable window is a few frames: every frame written
    try:
        bst = g.world_battle(SCENE, group=GROUP, rand=True, timeout=BATTLE_S)
    except HarnessError as err:
        _state_every(g, 2)
        led.check("S144-B1", False, f"the verb did not start a battle: {str(err)[:200]}; debug_status "
                                    f"{g.state.debug_status!r}")
        led.check("S144-B2", *judge_swirl(_ring(g, f0)))
        led.unreached(("S144-B3",), "no battle (B1)")
        _recover_world(g)
        return
    _state_every(g, 2)                                     # the agent's default back
    reads = _ring(g, f0)
    statuses = [cb.raw(x).get("debug_status") for x in reads] + [bst.debug_status, g.state.debug_status]
    led.check("S144-B1", *judge_battle_start(bst, epoch0, statuses, cb.new(g, at)))
    led.check("S144-B2", *judge_swirl(reads))
    try:
        g.fight(timeout=FIGHT_S, finish=True)
    except HarnessError as err:
        g.note(f"the fight did not finish: {str(err)[:200]}")
    st = _poll(g, lambda s: s.ui_state == "WorldHUD" and world_xz(s)[0] is not None and not s.fading, RETURN_S,
               "the world map after the battle")
    led.check("S144-B3", *judge_return(st if st is not None else g.state, before))


def _state_every(g, frames: int) -> None:
    """`stateevery N` (Session.state_every), best effort: a refusal is a note (B2 then reads what the default cadence caught)."""
    try:
        g.state_every(frames)
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery {frames} refused: {str(err)[:120]}")


def _ring(g, frame0: int) -> list:
    """Every state the driver READ since ``frame0`` (the session's ring: each wait's reads, ~20 ms apart) as States -- the
    swirl lasts about a second, so one read per poll would miss it."""
    from harness.channel import State
    return [State(x) for x in (g.states_since(int(frame0)) or []) if isinstance(x, dict)]


def _recover_world(g) -> None:
    try:
        if g.state.in_battle:
            g.fight(timeout=FIGHT_S, finish=True)
    except HarnessError as err:
        g.note(f"recovery: {str(err)[:160]}")


def _release_solo(g, led: cb.Ledger, ctx: dict) -> None:
    """The lever pulled (stage >= 144), then `reset` (HarnessSelfTest(false) -> HarnessReleaseBench -> HarnessReleaseWorld
    Freeze): the role released, the release line once; then the re-read WITH the role (WorldFreezeRule reads the lever
    only with it: `benchOff && selfTestRole`). One verdict after both reads."""
    stage = ctx.get("stage") or 0
    pulled = False
    if stage >= 144:
        pulled = cb.try_ns(g, "bench", "worldfreeze", "off")[0]
    at = cb.mark(g)
    try:
        cb.release(g)
    except HarnessError as err:
        led.check("S144-R", False, f"`reset` failed: {str(err)[:300]}")
        return
    st = g.state
    ns = st.netsync or {}
    ok = ns.get("forced") is False and not cb.dio(st).get("booted")
    detail = f"forced={ns.get('forced')!r} booted={cb.dio(st).get('booted')!r}"
    if stage >= 144:
        n = cb.count(cb.wait_log(g, at, _bw().LOG_WORLD_FREEZE_RELEASED, 2.0), _bw().LOG_WORLD_FREEZE_RELEASED)
        st2, why = cb.reread_with_role(g)
        off = _w(st2, "freeze.off") if st2 is not None else None
        ok = ok and pulled and st2 is not None and off is False and n == 1
        detail += (f"; the lever pulled before the reset: {pulled}; the release line {n}x (want 1); " + (why or "")
                   + f"; re-read with the role: freeze.off {off!r}")
    led.check("S144-R", ok, detail)


# ---------------------------------------------------------------------------------------------- T2
class _T2:
    def __init__(self):
        self.path = None                 # the rejoin leg's park path: "ensure" (no client before the edit) | "poll"
        self.cfg = []
        self.tape = None
        self.facts = None
        self.plan = None
        self.field = None
        self.stage = 0
        self.guard = None
        self.peer = None
        self.eng = None
        self.samples: list = []
        self.anchors: dict = {}
        self.base = None
        self.marker_own = None


def _run_dir(g) -> Path:
    return Path(getattr(g, "scenario_dir", None) or g.run_dir)


def _run_t2(g, leg: str) -> None:
    calibrate = cb.CALIBRATE
    p = T2_PFX[leg]
    led = cb.Ledger(g, t2_catalog(leg, calibrate), finals=("T2-SAVE", "T2-INI", f"{p}-CAL"))
    ctx = _T2()
    try:
        _t2(g, led, ctx, leg)
    except HarnessError as err:
        g.note(f"the {leg} leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        _t2_teardown(g, led, ctx, leg)
        if calibrate:
            try:
                ctx.stage = max(ctx.stage, stage_of(g.state))
            except HarnessError:
                pass
            pred = T2_PREDICTED[leg] if ctx.stage < 144 else ()
            g.note(f"{p}-CAL: the guest reads as s{ctx.stage or '<117'}; predicted reds {sorted(pred)}")
            led.close("not reached: the leg ended before this check")
            led.judge_calibration(f"{p}-CAL", pred)
        led.close(final=True)


def _t2_teardown(g, led: cb.Ledger, ctx: _T2, leg: str) -> None:
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
    g.note(f"Memoria.log archived: {cb.archive_log(g, f'world-wait-{leg}')}")


def _sample(g, ctx: _T2):
    st = g.state
    ctx.samples.append((_dt.datetime.now(), st))
    if ctx.eng is not None:
        ctx.eng.lines()
    if ctx.peer is not None:
        for key in ("guest_connected", "replay_start", "stop_at"):
            if key not in ctx.anchors:
                hit = ctx.peer.first(pb.PEER[key])
                if hit is not None:
                    ctx.anchors[key] = hit[0]
        if "exit" not in ctx.anchors and ctx.field is not None:
            for t, msg, m in ctx.peer.find(pb.PEER["tape_field"]):
                if m.group(3) == "0" and str(ctx.field) in m.group(2):
                    ctx.anchors["exit"] = t
                    break
    return st


def _until(g, ctx: _T2, cond, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = _sample(g, ctx)
        try:
            if cond(st):
                return True
        except (TypeError, KeyError, AttributeError, IndexError, ValueError):
            pass
        time.sleep(POLL_S)
    _sample(g, ctx)
    return False


def _after(ctx: _T2, t) -> list:
    return [s for ts, s in ctx.samples if t is None or ts >= t]


def _config_hits(ctx: _T2, code: str) -> list:
    return pb.hits(ctx.eng.lines(), "config", pred=lambda m: m.group(1) == "True" and m.group(2) == "client"
                   and m.group(5) == f"ws://127.0.0.1:{PORT}" and m.group(6) == code)


def _wait_config(g, ctx: _T2, code: str = CODE, *, reload: bool = True, wait: float = 10.0) -> list:
    """The engine's own config line for ``code``; with ``reload`` (on 6603 only) a field reload after 6 s (Ensure reads the
    ini at a field load) -- never on the world map, where a reload would be a field load (and its own dial)."""
    def found():
        return _config_hits(ctx, code)
    steps = ((6.0, True), (10.0, False)) if reload else ((wait, False),)
    for wait_s, reload_ in steps:
        deadline = time.time() + wait_s
        while time.time() < deadline:
            if found():
                return found()
            time.sleep(0.25)
        if reload_:
            g.note("no config line within the poll window -- reloading 6603 (Ensure reads the ini at a field load)")
            try:
                g.warp(FARSHORE)
            except HarnessError as err:
                g.note(f"the reload warp failed: {str(err)[:200]}")
    return found()


_RELAY_DIAL = re.compile(r"^\[NetSync\] relay connect(?:ed| to) .*")
#: NetSyncRelay's two dial lines, their endpoint parsed: "relay connect to <host>:<port> failed (...)" (every refused attempt)
#: and "relay connected ws[s]://<host>:<port>/sess/<code>?role=<role>" (the hop up)
_RELAY_TO = re.compile(r"^\[NetSync\] relay connect to [^\s:]+:(\d+) ")
_RELAY_UP = re.compile(r"^\[NetSync\] relay connected wss?://[^\s/]+?:(\d+)/sess/(\S+?)\?role=")


def bench_dial(msg: str, port=None, code=None) -> bool:
    """[review 2] (PURE) a relay line of THE BENCH's own dial: an attempt on its port, or the hop up on its port or with its code.
    The guest game launched on the OWNER's Memoria.ini, so its transport -- born at its first field, before any edit -- keeps
    retrying the owner's endpoint (127.0.0.1:49201, the owner's code) every ~2 s until the park's config change stops it, and
    the attempt in flight then still logs its failure (NetSyncRelay.Stop only clears _running): those lines say nothing about
    the bench, and counting them reds RJ-PARK at random."""
    port = PORT if port is None else int(port)
    code = CODE if code is None else code
    m = _RELAY_TO.search(msg)
    if m:
        return int(m.group(1)) == port
    m = _RELAY_UP.search(msg)
    if m:
        return int(m.group(1)) == port or m.group(2) == code
    return False


def judge_park(path: str, lines, *, before, overlay) -> tuple:
    """RJ-PARK (PURE): nothing dialled on the field before ``before`` (the moment the walk began; engine lines are
    whole-second stamps -- (t, level, msg)) -- ENSURE: no config line and no relay line of the bench's own dial; POLL: the park
    config line (an empty code), the overlay ``overlay`` 'no_code' on a field sample, no relay line of the bench's own dial
    (:func:`bench_dial` -- the owner's transport retrying its own endpoint is counted apart, never red)."""
    cut = pb.floor_s(before)
    early = [(t, m) for t, _l, m in lines if t < cut]
    cfg = [m for _t, m in early if pb.MATCHERS["config"].search(m)]
    relay = [m for _t, m in early if bench_dial(m)]
    other = [m for _t, m in early if _RELAY_DIAL.search(m) and not bench_dial(m)]
    others = f" ({len(other)} of another endpoint's transport ignored)" if other else ""
    if path == "ensure":
        return not cfg and not relay, (f"ENSURE (no client before the edit): config lines before the walk {cfg[:1] or 'none'}; "
                                       f"the bench's relay lines {relay[:1] or 'none'}{others}")
    parked = [m for m in cfg if pb.MATCHERS["config"].search(m).group(6) == ""]
    coded = [m for m in cfg if pb.MATCHERS["config"].search(m).group(6) == CODE]
    ok = bool(parked) and not coded and not relay and overlay == "no_code"
    return ok, (f"POLL (a client existed): the park config line {'seen' if parked else 'NOT seen'}, a coded one before the "
                f"walk {coded[:1] or 'none'}; the bench's relay lines {relay[:1] or 'none'}{others}; the field overlay "
                f"{overlay!r} (want 'no_code')")


def judge_dial(conn, start, cfg, relay, at_dial, *, began) -> tuple:
    """RJ-DIAL (PURE): the engine's config line with the code and its first relay-up line both stamped at or after the walk
    began (``began``; whole-second stamps), every sample from the world arrival to the dial on WorldHUD (``at_dial``), the
    peer's 'GUEST game connected' and 'REPLAY start'."""
    cut = pb.floor_s(began) if began is not None else None
    c_ok = bool(cfg) and cut is not None and min(t for t, _m, _x in cfg) >= cut
    r_ok = bool(relay) and cut is not None and min(t for t, _m, _x in relay) >= cut
    off = [s.ui_state for s in at_dial if s.ui_state != "WorldHUD"]
    w_ok = bool(at_dial) and not off
    ok = conn is not None and start is not None and c_ok and r_ok and w_ok
    return ok, (f"peer: {'GUEST connected' if conn else 'no guest connection'} / {'REPLAY start' if start else 'no replay'}; "
                f"engine: the config line {'after the walk' if c_ok else ('BEFORE the walk' if cfg else 'never')} "
                f"({pb.show(cfg, 1)}), the relay {'up after the walk' if r_ok else ('up BEFORE the walk' if relay else 'never up')}"
                f" ({pb.show(relay, 1)}); the guest on {at_dial[-1].ui_state if at_dial else '?'} at the dial"
                + (f" (left the world HUD on {sorted(set(off))})" if off else ""))


def _t2(g, led: cb.Ledger, ctx: _T2, leg: str) -> None:
    p = T2_PFX[leg]
    rows = [c for c in led.catalog if c.startswith(p + "-") and c != f"{p}-CAL"]
    # A. the tape and its plan
    ctx.tape = pb.latest_tape() if leg == "rejoin" else pb.latest_world_tape()
    if ctx.tape is None or not Path(ctx.tape).exists():
        led.check("T2-TAPE", False, f"no tape ({ctx.tape or (pb.tape_dir() if leg == 'rejoin' else pb.world_tape_dir())})"
                                    + (": record one -- coop_tape_record.py" if leg == "rejoin" else
                                       ": record one -- COOP_TAPE_WORLD=1 coop_tape_record.py"))
        led.close("not reached: no tape")
        return
    try:
        cp = pb.coop_peer_module()
        _h, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                              # noqa: BLE001
        led.check("T2-TAPE", False, f"{ctx.tape} does not read back: {err}")
        led.close("not reached: the tape does not read back")
        return
    if leg == "rejoin":
        ctx.facts = pb.tape_facts(records, cp, field=None)
        ctx.plan = pb.plan_world_leg("world-rejoin", ctx.facts)
    else:
        ctx.facts = pb.world_tape_facts(records, cp)
        ctx.plan = pb.plan_world_leg("world-wait", ctx.facts)
    ctx.field = ctx.plan.get("field")
    led.check("T2-TAPE", ctx.plan["ok"], f"{Path(ctx.tape).name} ({len(records)} records{f', torn {torn} B' if torn else ''})"
                                         f": field {ctx.field}; " + ("ok" if ctx.plan["ok"] else "CANNOT -- "
                                                                     + ctx.plan["why"])
                                         + (f"; stop at tape {ctx.plan['stop_at']:.2f} s" if ctx.plan.get("stop_at")
                                            else "") + (f"; the host's b6: {ctx.plan['expect'].get('b6')}"
                                                        if leg == "wait" else ""))
    if not ctx.plan["ok"]:
        led.close(f"not reached: this tape cannot carry the {leg} leg ({ctx.plan['why'][:200]})")
        return
    if leg == "rejoin":
        okc, whyc = pb.read_cal(Path(ctx.tape))
        led.check("T2-CAL", okc, whyc + (" -- COOP_WORLD_FORCE=1: running anyway" if not okc and FORCE else ""))
        if not okc and not FORCE:
            led.close(f"not reached: the instrument is untrustworthy -- {whyc[:200]}")
            return
    # B. the port and the guest's own autosave
    free, why = (False, f"COOP_PEER_PORT={PORT} is the owner's bridge port: the s144 legs never bind it (they write "
                        f"their own RelayUrl -- pick a private port; default {pb.WORLD_PORT})") if PORT == pb.OWNER_PORT \
        else pb.port_free(PORT)
    if not free:
        led.check("T2-PEER", False, why)
        led.close("not reached: the bench port is taken (nothing was edited)")
        return
    owner_free, _owhy = pb.port_free(pb.OWNER_PORT)       # [review 2] THE PRECONDITION enforced: the owner's own bridge DOWN
    if not owner_free:
        led.check("T2-PEER", False, f"the owner's bridge is UP on 127.0.0.1:{pb.OWNER_PORT}: this guest game launched on the "
                                    "owner's Memoria.ini (its Role, its SessionCode) dials it before any edit and joins the "
                                    "owner's LIVE session (and re-dials from the world HUD after T2-INI's restore) -- stop the "
                                    "bridge first")
        led.close("not reached: the owner's bridge is up (nothing was edited)")
        return
    try:
        moogle = pb.ini_autosave_moogle_only((Path(g.game_path) / "Memoria.ini").read_text(encoding="utf-8",
                                                                                           errors="replace"))
    except OSError:
        moogle = False
    if moogle:
        led.check("T2-SAVE", False, "[SaveFile] AutoSaveOnlyAtMoogle = 1: no own autosave on 6603 for the exit ramp "
                                    "(nothing was edited)")
        led.close("the guest can have no own autosave on the bench field (T2-SAVE)")
        return
    # C. the guest's own game on 6603
    cb.provenance(g)
    g.note(f"s144 T2 {leg} leg: the guest on {FARSHORE}" + (" then the world map" if leg == "rejoin" else ""))
    g.newgame()
    g.warp(FARSHORE)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.watch(*(pb.MARKER_BYTE * 8 + b for b in range(8)))
    g.wait_frames(45)                                     # the field entry's autosave: the exit ramp's own Continue
    st = g.state
    ctx.stage = stage_of(st)
    ctx.marker_own = pb.marker_value(st)
    g.note(f"the guest engine reads as s{ctx.stage or '<117'}; its own story marker {ctx.marker_own!r}")
    # D. the ini, the engine's own config line
    ctx.eng = pb.EngineLog(g.engine_log())
    if leg == "rejoin":
        if not _rejoin_park_and_walk(g, led, ctx, p, rows):
            return
        cfg = ctx.cfg
    else:
        ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", GUEST_VALUES, label=f"coop-world-{leg}",
                                run_dir=_run_dir(g))
        try:
            g.note(ctx.guard.apply())
        except (OSError, RuntimeError) as err:
            led.check("T2-PEER", False, f"the Memoria.ini edit failed: {err}")
            led.close("not reached: Memoria.ini could not be edited")
            return
        cfg = _wait_config(g, ctx)
        if not cfg:
            led.check("T2-PEER", False, f"the engine never logged the guest config (seen: "
                                        f"{pb.show(pb.hits(ctx.eng.lines(), 'config'))})")
            led.close("not reached: the guest config never applied")
            return
    # E. the replay-host
    rd = _run_dir(g)
    args = [ctx.tape, "--port", str(PORT), "--code", CODE, "--at-end", "hold"]
    if ctx.plan.get("stop_at") is not None:
        args += ["--stop-at", f"{ctx.plan['stop_at']:.3f}"]
    ctx.peer = pb.PeerProc("replay-host", args, log_path=rd / f"coop_peer-replay-world-{leg}.log",
                           out_path=rd / f"coop_peer-replay-world-{leg}.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    ctx.peer.start()
    ctx.anchors["peer"] = _dt.datetime.now()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0, tick=lambda: _sample(g, ctx))
    if leg == "rejoin":
        led.check("T2-PEER", up is not None, f"the guest config written ({ctx.path}; the engine's line so far: "
                                             f"{pb.show(cfg, 1) if cfg else 'none -- RJ-DIAL judges it'}); peer: "
                                             f"{up[1] if up else 'never listened'}; tail: {ctx.peer.tail(3)}")
        if up is None:
            led.unreached(rows, "the instrument never started (T2-PEER)")
            return
        _leg_rejoin(g, led, ctx, p)
    else:
        conn = ctx.peer.wait_for(pb.PEER["guest_connected"], DIAL_S, tick=lambda: _sample(g, ctx)) if up else None
        start = ctx.peer.wait_for(pb.PEER["replay_start"], 10.0, tick=lambda: _sample(g, ctx)) if conn else None
        relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "guest" and m.group(2) == CODE)
        ok = up is not None and conn is not None and start is not None and bool(relay)
        led.check("T2-PEER", ok, f"config: {pb.show(cfg, 1)}; peer: {up[1] if up else 'never listened'} / "
                                 f"{conn[1] if conn else 'no guest'} / {start[1] if start else 'no replay start'}; "
                                 f"engine: {pb.show(relay, 1)}")
        if not ok:
            led.unreached(rows, "the instrument never started (T2-PEER)")
            return
        ctx.anchors["start"] = start[0]
        _leg_wait(g, led, ctx, p)


def _rejoin_park_and_walk(g, led: cb.Ledger, ctx: _T2, p: str, rows) -> bool:
    """The rejoin leg's D: THE PARK (by the guest's state before any edit -- see the docstring's ENSURE / POLL), the walk out
    (RJ-PARK, RJ-I), then -- POLL -- the code alone on the world HUD, and the engine's config line awaited there (never a
    reload). False = the leg stops (its rows recorded)."""
    inst = bool((g.state.netsync or {}).get("instance"))
    ctx.path = "poll" if inst else "ensure"
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", PARK_VALUES if inst else GUEST_VALUES,
                            label="coop-world-rejoin", run_dir=_run_dir(g))
    try:
        g.note(f"rejoin leg, path {ctx.path.upper()}: " + ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("T2-PEER", False, f"the Memoria.ini edit failed: {err}")
        led.close("not reached: Memoria.ini could not be edited")
        return False
    overlay = None
    if inst:
        if not _wait_config(g, ctx, ""):
            led.check("T2-PEER", False, f"the engine never logged the PARK config (seen: "
                                        f"{pb.show(pb.hits(ctx.eng.lines(), 'config'))})")
            led.close("not reached: the park config never applied")
            return False
        st = _poll(g, lambda s: _s(s, "overlay") == "no_code", 4.0, "the park overlay") or g.state
        overlay = _s(st, "overlay")
        # [review 2] the engine stamps whole seconds and RJ-PARK reads "before the walk" as a strictly EARLIER second: a park line
        # logged in the walk's own second read 'NOT seen' (the stand-in's flake; a real game spends seconds in calibrate_axes)
        cb.hold_for(g, STAMP_S)
    else:
        cb.hold_for(g, PARK_S)                             # past the 2 s poll: nothing may read the ini on the field
    g.wait_playable(timeout=60)
    began = {}
    ok, why, st = walk_out(g, before_walk=lambda: began.setdefault("t", _dt.datetime.now()))
    ctx.anchors["began"] = began.get("t")
    pk_ok, pk_why = judge_park(ctx.path, ctx.eng.lines(), before=began.get("t") or _dt.datetime.now(), overlay=overlay)
    led.check(f"{p}-PARK", pk_ok, pk_why)
    st = _sample(g, ctx)
    ctx.anchors["world"] = _dt.datetime.now()
    own = pb.marker_value(st)
    i_ok = ok and own is not None and ctx.marker_own is not None and own == ctx.marker_own and own != pb.MARKER_VALUE
    led.check(f"{p}-I", i_ok, f"{why}; the guest's own marker {own!r} (want its own {ctx.marker_own!r}, never the host's "
                              f"0x{pb.MARKER_VALUE:02X})" + ("; the marker watch never read (the instrument)"
                                                             if own is None or ctx.marker_own is None else ""))
    if not (pk_ok and i_ok):
        led.check("T2-PEER", True, f"the guest config written ({ctx.path}); the peer was never started: RJ-PARK / RJ-I")
        led.unreached([c for c in rows if c not in (f"{p}-PARK", f"{p}-I")],
                      f"the instrument is untrustworthy on this run -- {(why if not i_ok else pk_why)[:160]}")
        return False
    if inst:
        try:
            g.note("on the world HUD: " + ctx.guard.update({"SessionCode": CODE}))
        except (OSError, RuntimeError) as err:
            led.check("T2-PEER", False, f"the code's Memoria.ini edit failed on the world map: {err}")
            led.unreached([c for c in rows if c not in (f"{p}-PARK", f"{p}-I")], "the code never reached the ini")
            return False
    ctx.cfg = _wait_config(g, ctx, CODE, reload=False, wait=CONFIG_S if inst else 2.0)
    ctx.base = g.state
    return True


def _leg_rejoin(g, led: cb.Ledger, ctx: _T2, p: str) -> None:
    F = int(ctx.field)
    _until(g, ctx, lambda s: "guest_connected" in ctx.anchors and "replay_start" in ctx.anchors, DIAL_S)
    conn, start = ctx.anchors.get("guest_connected"), ctx.anchors.get("replay_start")
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "guest" and m.group(2) == CODE)
    world_at = ctx.anchors.get("world")
    at_dial = [s for ts, s in ctx.samples if world_at is not None and ts >= world_at
               and (conn is None or ts <= conn + _dt.timedelta(seconds=0.5))]
    led.check(f"{p}-DIAL", *judge_dial(conn, start, _config_hits(ctx, CODE), relay, at_dial, began=ctx.anchors.get("began")))
    t0 = start or ctx.anchors.get("peer")
    _until(g, ctx, lambda s: s.ui_state == "FieldHUD" and s.field_id == F, LAND_S)
    landed = next((ts for ts, s in ctx.samples if s.ui_state == "FieldHUD" and s.field_id == F and ts >= t0), None)
    if landed is not None:
        _until(g, ctx, lambda s: pb.marker_value(s) == pb.MARKER_VALUE and _s(s, "mirroring") is True, MIRROR_S)
        cb.hold_for(g, 1.0)
        _sample(g, ctx)
    samples = _after(ctx, t0)
    lines = [m for _t, _l, m in ctx.eng.lines()]
    led.check(f"{p}-ARM", *judge_rejoin_arm(samples, ctx.base, lines, field=F))
    led.check(f"{p}-LAND", *judge_rejoin_land(samples, ctx.base, lines, field=F))
    before = [s for ts, s in ctx.samples if landed is None or ts < landed]
    since = [m for t, _l, m in ctx.eng.lines() if t >= pb.floor_s(t0)]
    led.check(f"{p}-MIRROR", *judge_mirror(before, _after(ctx, landed) if landed else [], since, field=F))
    if landed is None:
        g.note(f"RJ: the guest never reached field {F} (last: {g.state.ui_state}, world {g.state.world_id})")


def _leg_wait(g, led: cb.Ledger, ctx: _T2, p: str) -> None:
    b6 = bool(ctx.plan["expect"].get("b6"))
    start = ctx.anchors["start"]
    _until(g, ctx, lambda s: "exit" in ctx.anchors, PAIR_S + EXIT_S)
    exit_at = ctx.anchors.get("exit")
    lines = ctx.eng.lines()
    paired = pb.hits(lines, "paired", after=start, before=exit_at, pred=lambda m: int(m.group(1)) == FARSHORE)
    armed = pb.hits(lines, "armed", after=start, before=exit_at)
    before = [s for ts, s in ctx.samples if exit_at is not None and ts <= exit_at]
    on6603 = bool(before) and before[-1].ui_state == "FieldHUD" and before[-1].field_id == FARSHORE
    i_ok = exit_at is not None and bool(paired) and bool(armed) and on6603
    led.check(f"{p}-I", i_ok, f"paired {pb.show(paired, 1)}; armed {pb.show(armed, 1)}; the host's exit "
                              f"{'at ' + exit_at.strftime('%H:%M:%S') if exit_at else 'NEVER on the peer log'}; the guest "
                              f"on {before[-1].ui_state if before else '?'} {before[-1].field_id if before else ''}")
    if not i_ok:
        led.unreached([c for c in led.catalog if c.startswith(p + "-") and c not in (f"{p}-I", f"{p}-CAL")],
                      "the instrument is untrustworthy on this run (WT-I)")
        return
    # WT-FIELD: within LINE_S (+ LINE_GRACE_S, polled) of the exit the line; still on 6603 on every sample since
    _until(g, ctx, lambda s: _dt.datetime.now() >= exit_at + _dt.timedelta(seconds=LINE_S) and judge_line(s, b6=b6)[0],
           LINE_S + LINE_GRACE_S + 5.0)
    since = _after(ctx, exit_at)
    left = [(s.ui_state, s.field_id) for s in since if not (s.ui_state == "FieldHUD" and s.field_id == FARSHORE)]
    st = since[-1] if since else g.state
    l_ok, l_why = judge_line(st, b6=b6, field=FARSHORE)
    led.check(f"{p}-FIELD", l_ok and not left, l_why + (f"; LEFT 6603: {left[:3]}" if left else "; on 6603 throughout"))
    cb.shot(g, "world-line-field")
    # WT-FROZEN: the guest's own walk out
    base = g.state
    at = cb.mark(g)
    ok, why, _st = walk_out(g)
    if not ok:
        led.unreached((f"{p}-FROZEN", f"{p}-WORLD"), f"the guest's walk out failed: {why[:160]}")
        return
    moved, adv, st = hold_walk(g, WALK_FRAMES)
    led.check(f"{p}-FROZEN", *judge_frozen(st, moved, adv, base))
    cb.hold_for(g, 1.0)
    st = g.state
    l_ok, l_why = judge_line(st, b6=b6)
    if b6:
        n = cb.count(cb.new(g, at), _bw().log_world_hold_released(FARSHORE, False))
        h_ok = n == 1 and _f(st, "hold") == -1
        l_why += f"; the hold released by b6 {n}x, follow.hold {_f(st, 'hold')!r}"
    else:
        h_ok = True
    led.check(f"{p}-WORLD", l_ok and h_ok and st.ui_state == "WorldHUD", l_why)
    cb.shot(g, "world-line-world")


# ---------------------------------------------------------------------------------------------- the duo
def run_duo(d) -> None:
    """The duo leg (duo.py pairs the two games on 6603 first: ``PAIR``). Every row recorded (strict off), each judged on
    the GUEST's samples beside its engine's keys; COOP_CALIBRATE=1 judges D-CAL by the GUEST's stage."""
    calibrate = cb.CALIBRATE
    strict, d.strict = d.strict, False
    failed = []

    def check(cid, ok, detail):
        if not ok:
            failed.append(cid)
        d.check(bool(ok), f"{cid}: {DUO_CHECKS.get(cid, cid)}", str(detail)[:900], cid=cid)

    try:
        host, guest = d.host, d.guest
        gst = guest.state
        stage = stage_of(gst)
        d.note(f"s144 duo: the guest reads as s{stage}, the host as s{stage_of(host.state)}")
        both = (host.state.ui_state == "FieldHUD" and host.state.field_id == FARSHORE and gst.ui_state == "FieldHUD"
                and gst.field_id == FARSHORE and _s(gst, "mirroring") is True)
        check("S144-D0", both, f"host {host.state.ui_state} {host.state.field_id}; guest {gst.ui_state} {gst.field_id}, "
                               f"mirroring {_s(gst, 'mirroring')!r}")
        if not both:
            for cid in DUO_PREDICTED:
                check(cid, False, "not reached: the pair is not on 6603 (D0)")
            return
        # D1: the host walks out; the guest left on 6603 shows the line
        ok, why, _hs = walk_out(host)
        if not ok:
            for cid in DUO_PREDICTED:
                check(cid, False, f"not reached: the host's walk out failed ({why[:160]})")
            return
        samples, hit = cb.watch(guest, lambda s: judge_line(s, b6=True, field=FARSHORE)[0], DUO_LINE_S)
        left = [(s.ui_state, s.field_id) for s in samples if not (s.ui_state == "FieldHUD" and s.field_id == FARSHORE)]
        l_ok, l_why = judge_line(hit if hit is not None else guest.state, b6=True, field=FARSHORE)
        check("S144-D1", l_ok and not left, l_why + (f"; the guest LEFT 6603: {left[:3]}" if left else ""))
        cb.shot(guest, "world-line-duo-field")
        # D2: the guest walks out too -> frozen, the line
        base = guest.state
        at = cb.mark(guest)
        ok, why, _gs = walk_out(guest)
        if not ok:
            check("S144-D2", False, f"not reached: the guest's walk out failed ({why[:160]})")
            check("S144-D3", False, "not reached: the guest never reached the world map (D2)")
            return
        moved, adv, gst = hold_walk(guest, WALK_FRAMES)
        f_ok, f_why = judge_frozen(gst, moved, adv, base)
        cb.hold_for(guest, 1.0)
        gst = guest.state
        l_ok, l_why = judge_line(gst, b6=True)
        n = cb.count(cb.new(guest, at), _bw().log_world_hold_released(FARSHORE, False))
        check("S144-D2", f_ok and l_ok and n == 1, f"FROZEN {f_why}; LINE {l_why}; the hold released by b6 {n}x")
        cb.shot(guest, "world-line-duo-world")
        # D3: the host enters the Ice Cavern; the guest rejoins from the world map
        gbase = guest.state
        gat = cb.mark(guest)
        try:
            teleport_settle(host, ICE_TILE)
            host.wait_frames(PROMPT_FRAMES)
            host.press("confirm")
            hst = _poll(host, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, FIELD_S, "the host on 300")
        except HarnessError as err:
            hst = None
            d.note(f"the host's entry raised: {str(err)[:200]}")
        if hst is None:
            check("S144-D3", False, f"not reached: the host never entered 300 (ui {host.state.ui_state!r}, field "
                                    f"{host.state.field_id})")
            return
        samples, _hit = cb.watch(guest, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, REJOIN_S)
        samples += cb.hold_for(guest, 1.5)
        glines = cb.new(guest, gat)
        a_ok, a_why = judge_rejoin_arm(samples, gbase, glines, field=ICE_CAVERN)
        n_ok, n_why = judge_rejoin_land(samples, gbase, glines, field=ICE_CAVERN)
        mir = _s(samples[-1], "mirroring") if samples else None
        check("S144-D3", a_ok and n_ok and mir is True, f"ARM {a_why}; LAND {n_why}; mirroring {mir!r}")
    finally:
        if calibrate:
            try:
                stage = stage_of(d.guest.state)
            except HarnessError:
                stage = 0
            pred = set(DUO_PREDICTED) if stage < 144 else set()
            missing, extra = sorted(pred - set(failed)), sorted(set(failed) - pred)
            d.check(not missing and not extra, "S144-D-CAL: CALIBRATION -- exactly the predicted duo rows red for the "
                                               "GUEST's stage",
                    f"guest s{stage}: predicted reds that stayed GREEN {missing or 'none'}; unpredicted reds "
                    f"{extra or 'none'}", cid="S144-D-CAL")
        d.strict = strict
