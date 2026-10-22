"""s145 -- WORLD-MAP CO-OP, BATTLES FROM THE WORLD MAP (memoria-patch s145): the bench, run unattended. Three instruments in one
file, on coop_world_wait.py's route and judges (imported, never copied: that 2k-line file and its slow_leg registry stay put):
the SOLO leg (one game in the selftest role), three T2 legs (the desktop as a real GUEST, a recorded host replayed) and one DUO
leg (two real games). Every leg is judged on witnesses the engine does not compute -- world x/z against snapshot A, ui_state on
every sample, the world camera, the MAP-var digest, the encounter rate, the world tick (a reload restarts it), the peer's own
decode of the guest's control frames -- beside the engine's own claim (`netsync.world.dio`, `netsync.diorama`).

THE OWNER'S CALL (studies/world-coop/S145-DESIGN.md, decisions 1-12): a following guest frozen on the world map (s144) boots its
battle diorama there when the host fights -- the real menu -- and comes back to the world map WARM, where it stood (its camera, its
MAP vars, its control); it NEVER takes a cold world reload: a warm refusal is no boot (a decline keeps s144: frozen, the digit
panel, the report NONE). Vehicles decline. Calibration is the selftest-only lever `netsync bench worldwarm off|cold|on`.

THE ROUTE (coop_world_wait.py's, every leg): New Game -> 6603 FARSHORE (FF9CustomMap-world; RE-READ its registration first) ->
the proven walk out (walk_out: calibrate_axes with the door quad a hazard, walk_to inside it, wait_world) -> world 9011 (WORLD11,
the benign free-roam state) at the landing FS_LANDING (68, -444); encounters off. THE ACTOR-BRICK LAW: no world-map save.

THE OFFLINE ORACLE (S145-OR, read-only, never the engine's answer): coop_world_wait.read_oracle (the door, 6603's WorldMap(9011),
WORLD11's Field(300), block (18,12) stock, no fork of 300, the battle scene registered), the diorama's scene DIO_SCENE (359,
BSC_WM_0007: the Mist continent's own world formation) registered, and THE ENCOUNTER-RATE ORACLE (fix1): world.battle_prob
(w_frameEventBattleProb) is written ONLY by world script op 26, and WORLD11 writes it in Main_Init (entry 0, tag 0: 365) and
Main_Reinit (tag 10: 231) -- read off the world script 9011 loads (the highest stacked folder's override, else p0data's;
world_prob_oracle), so a return is judged BY VALUE: Main_Reinit's on a warm one, Main_Init's on a cold one (A itself follows a
Main_Init load). Every expected text the bench compares is the TWIN's (battlewire: world_warm_row, log_world_*), never read back
from the engine; tests/test_world_diorama.py pins each twin's literal pieces to the s145 patch.

SOLO (COOP_WB_LEG=solo, the default; the selftest role -- it never runs the watcher: it proves the boot and the return mechanics):
  setup  INI (read-only: [Netsync] Enabled 0 or absent; the runners' selftest_block.sh flips it, byte-exact restore) -> OR -> S0
         (newgame, the COOPPARTY seed, 6603, encounters off, the forced selftest role) -> P0 (the s145 keys and proof lines:
         `netsync.world.dio` in AppendWorldDio's order, `world` = freeze/rejoin/waitline/dio, `prev_mode`, the six world witness
         keys; 'world diorama selftest: OK (86 rows)', 'world watcher selftest: OK (59 rows)', 'world freeze selftest: OK (46
         rows)', 'diorama watcher selftest: OK (32 rows)'; none FAIL) -> P1 (`netsync bench 0` and the lever at rest: dio.lever
         'on'; COOP_CALIBRATE=1 on s145 pulls `bench worldwarm off` here, its OFF line once) -> ROUTE (the walk out) -> A.
  A      THE INSTRUMENT, snapshot A: unfrozen (`bench 0`) the walker walks OFF the landing (`hold up` WALK_OFF_FRAMES, at most
         WALK_OFF_TRIES holds, until >= A_AWAY_MIN from it: a warm return can then be told from the Main_Init spawn), the camera
         turns (`hold leftbumper` CAM_FRAMES: a prevMode-1 world load would reset it), `bench 1` freezes it ('bench') and a held
         `hold up` moves < HELD_U; on s145 the camera turned >= CAM_TURN_MIN from the arrival's and every world witness is live.
         The arrival's MAP digest beside A's is noted (whether the walk changed it: WC proves a cold return differs). A red A stops
         the leg (every world row 'not reached': the witnesses could not discriminate).
  BOOT   `netsync dioboot 359 0 wire` from WorldHUD boots WARM: dio.booted_world, boot_world 9011, boot 'warm'; prev_mode 3 and the
         LOOSE gMode 3 (gMode stays 3 through the boot); netsync.diorama boot 'warm' with boot_field -1 and boot_x / boot_z (PosObj:
         RealPosition x 256) within RETURN_TOL of A; 'diorama boot: WARM world return primed -- world 9011, player at (...)' once, no
         'REFUSED'; never FieldHUD on a sample since the verb.
  AUDIO  no 'diorama pre-swirl audio replicate failed' line and no 'diorama swirl centre (world) failed' line since the boot (the
         FIELD block's SFX_Rush.SetCenterPosition(0) throws on the world map; the world shape's SetCenterPosition(1) logs its own
         text) -- on a boot that happened.
  RET    `dioleave` (request-only, the swirl defers it: retried) lands on WorldHUD 9011 and the return is counted WARM ON ITS OWN
         LOAD: on the FIRST world sample after the leave dio.returns +1, last_return 'warm', last_world 9011, diorama.last_return
         'warm' with last_return_field -1; the world RELOADED (world.ticks restarted below the pre-boot read); never FieldHUD
         between the leave and the return; 'diorama LEAVE requested -> WorldMap (world 9011, mode 3)' once and the warm RETURN line
         of OUR prime once (through ': the guest stands where it stood at boot'; never the 'did NOT prime' Warning), no cold one.
  PLACE  the settled return stands within RETURN_TOL of A and >= LANDING_MIN from the landing (never the Main_Init spawn).
  CAM    world.cam_rot within CAM_TOL of A's and cam_upper A's (prevMode 3 kept the camera).
  MAP    the MAP-var digest (world.mapvar, 160 hex digits) A's exactly (the reinit branch restored ctx0) and world.battle_prob BY
         VALUE: Main_Reinit's own write, the oracle's (231 on WORLD11) -- never A's (A follows a Main_Init load: 365).
  MODE   the live travel mode (world.ctl) 0 -- on foot -- as at A.
  MUSIC  JUDGED ONLY WHEN DISCRIMINATING (A's song and the boot's battle song both read and different), on the SOUND INSTANCES the
         bookkeeping cannot overwrite (fix1): on the BOOTED sample the world song sits in the suspend slot (dio.suspend_song == A's
         song: a double suspend or none reads -1 there); at the settled return A's OWN instance plays again (dio.song_sid == A's: a
         restart from the top mints a new one), no instance latched at the Leave still plays over it (dio.boot_song_live false:
         decision 8's stop), and the bookkeeping reads A's (netsync.battle.end.music, suspend_song); otherwise green with 'not
         discriminating' named. (fix2/fix3) A settled read that still shows boot_song_live true is re-read on WorldHUD for up to
         SONG_FADE_S (song_quiet: a Leave-latched instance stops inside its own fade -- BeforeWorldEvents' STOPCURRENT, 500 ms --
         while a song LEFT playing never goes quiet); the held leg (HF-RET) reads its last RECORDED world sample, never re-read
         -- and (fix3-r2) its rejoin can leave the world map as soon as the return's own gates pass: FollowHostTick runs every
         Update, inside the diorama too, and stamps the host's field on first sight (NetSyncClient.cs:1824, 3714-3718), so
         FollowStableMs (1200 ms, :3720) is already spent at the return, and ServiceIntentFollow (:1820) has no debounce. So
         HF-RET judges boot_song_live only on a sample STOPCURRENT_FADE_MS (500 ms, on the wall: the state file's write time)
         past the first world sample; inside that fade it names the term 'not discriminating: the rejoin left the world map
         inside BeforeWorldEvents' 500 ms fade (N ms ...)' and still judges the instance, the slot and the bookkeeping.
  FROZEN still frozen after the round trip: `hold up` moves < HELD_U, freeze.on 'bench', edges A's +1 (re-frozen from the first
         world frame).
  SILENT the host-silent lane (fix1, audio-2): `netsync dioboot 359 0 wire silent` (the wire song 0xFFFE: the world shape's own
         suspend, the swirl's STOPCURRENT finding nothing) boots warm and returns to WorldHUD at A; MUSIC's judge in that lane --
         while booted the slot holds A's song and NOTHING is current (music -1); at the return A's own instance plays again.
  RESET  `reset` with a world diorama up: the deferred release waits for the teardown -- the return lands WARM (dio.returns +1,
         last_return 'warm') within RETURN_TOL of where it booted, the role released. (The role and `bench 1` re-forced after.)
  VEH    `vehicle 1` (chocobo) on 9011, then the boot DECLINES: `dioboot` refused, never booted, every sample WorldHUD, declines +1,
         decline_durable, decline_why the twin's ('aboard a vehicle (travel mode 1) ...'), NO world reload (world.ticks never
         restarted); `vehicle 0` -> back on foot (world.ctl 0).
  LEVER  `bench worldwarm off` (its OFF line) -> the boot declines: refused, never booted, declines +1, decline_durable, the twin's
         CALIBRATION why, no reload; `bench worldwarm on` after.
  WC     THE COLD REFERENCE, LAST (`bench worldwarm cold`): the boot reads 'cold' (its cold primed line), the return re-enters
         through Main_Init: last_return 'cold' and world.battle_prob Main_Init's value (the oracle's 365) -- and PLACE's and MAP's
         own judges read that return RED (Main_Init's placement, not A; its encounter rate, not Main_Reinit's): the rows that
         judge a warm return CAN fail. (Where Main_Init puts the walker is reported,
         never required -- the stand-in's spawn is the landing.)
  R      the lever pulled once more, then `reset`: the role released and 'world warm gate back ON (released with the harness)'
         once; re-read WITH the role: dio.lever 'on'. (Before s145: the role released.)
  SWIRL  the instrument (below): no leg start hung in the swirl.

T2 (COOP_WB_LEG=battle | held | decline; the desktop is a REAL client: Memoria.ini [Netsync] Enabled 1 / Role client / RelayUrl
ws://127.0.0.1:<COOP_PEER_PORT, never 49201> / SessionCode ff9-T2BENCH1 / FollowHost 1 / GuestSlots 0 / GuestStockMenu 1 /
SessionGraceMs 30000 / DioramaSwirlFrames 0 written through _coop_peer_bench.IniGuard -- backed up first, restored byte-exact --
and tools/harness/coop_peer.py `replay-host` replays the whole tape, holding at its end):
  battle THE COOP_TAPE_WORLD_BATTLE TAPE (coop_tape_record.py COOP_TAPE_WORLD_BATTLE=1, recorded on the live s144 host: PRE 25 s on
         6603, the walk out, a DWELL, `battle 67 0 rand` on WorldHUD fought and won, back where it fought, a STAY, then -- the
         default COOP_TAPE_WB_ENTER -- the host enters the Ice Cavern, 300; latest-world-battle.json in its own dir; COOP_TAPE names
         one). Its plan: _coop_peer_bench.plan_world_leg('world-battle') and the entry into 300 on it.
         WB-I    the instrument: 'paired on the host's field (6603)' and 'state-mirror ARMED' before the host's world exit; then the
                 guest walks out too, is FROZEN (`hold up` < HELD_U, freeze.on 'live' / 'mirroring'), teleports onto the Ice Cavern
                 tile ICE_TILE (far from the landing: discriminating) and takes snapshot A -- all before the host's battle reaches
                 the wire (the peer's 'tape T: host battle nonce N ...' line). The oracle's battle_prob is read first
                 (world_prob_oracle: the RET row judges by value).
         WB-BOOT from the battle's first frame: every guest sample on WorldHUD / the swirl / BattleHUD, NEVER FieldHUD; the diorama
                 booted from the world (dio.booted_world, boot_world 9011, boot 'warm'); THE REPORT on the wire, decoded by the
                 peer itself -- BOOTING then LIVE ('guest control: ... boot BOOTING' then '... boot LIVE', both naming THIS
                 battle's nonce) -- beside the guest's own 'diorama LIVE ... (host battle nonce N, booted from wire nonce N)' line.
         WB-PLAY its stock menu served: the peer reads the guest's control byte 2 (root) or 3 (deep) while LIVE on this battle,
                 and the guest logged 'stock menu: the ready mirror is SERVING' since the boot.
         WB-RET  it leaves on `terminal` (the end-leave) or `host_world` (b6, decision 9) -- never `stall_cap`; back on WorldHUD
                 9011 within RETURN_TOL of A, the return counted warm on its own load (dio.returns +1, last_return 'warm'), the world
                 reloaded, still frozen (`hold up` < HELD_U, freeze.on) -- and the witnesses the engine does not compute (fix1):
                 world.battle_prob Main_Reinit's (the oracle's: position-free), the MAP digest and the camera A's, and MUSIC's
                 judge over A, the booted sample and the return (a finished fight's settle, the host's own song on a real wire).
         WB-300  the host's entry: the guest rejoins 300 from the world map (FieldHUD 300 within REJOIN_S, rejoin.lands +1, 'world
                 rejoin landed on field 300') and NO SECOND RETURN is counted there: netsync.diorama.returns and dio.returns as they
                 were after the world return, last_return_field never 300 (s144's consume rule would count it at this field load).
  held   A HOST FIGHTING ON THE HELD FIELD (decision 1's source-field hold): a plain host tape recorded ON 6603 (coop_tape_record.py
         --field 6603 with COOP_TAPE_PRE_S=100 into its own COOP_TAPE_DIR, coop-tapes/held-6603: the host stays on 6603, fights
         `battle 67 -1 rand` there, back on 6603). Plan: plan_held_leg (the five facts on 6603, >= HELD_PRE_NEED_S before the
         battle). THE HOLD IS 15 s (battlewire.WORLD_HOLD_MS, s144 decision 4: a rejoin into the field the guest just left waits
         that long, or until the host leaves it), so the guest's walk out is TIMED against the tape: its axes calibrated on 6603
         right after the pairing, the walk itself started HELD_LEAD_S before the host's battle reaches the wire (the replay's
         start + the plan's battle time / REPLAY_SPEED) -- the battle then lands inside the hold, with the guest on the world map.
         HF-I    the instrument: paired + ARMED on 6603; the walk started on time; the guest on WorldHUD 9011, the source-field hold
                 latched (follow.hold 6603, its line once), freeze.on; and AT THE BATTLE's first frame on the wire the guest still
                 on the world map with the hold held (a walk that missed the window is the instrument's, never the engine's).
                 Snapshot A is the arrival at the landing (no teleport: the window is short).
         HF-BOOT the host's FIELD battle boots the guest's diorama from WorldHUD -- WB-BOOT's reads.
         HF-RET  it leaves on `terminal` or `host_field` (the host back on 6603) -- never `stall_cap` -- and returns warm at A,
                 counted on its own load, re-frozen; WB-RET's witnesses too (fix1) -- battle_prob Main_Reinit's is the one that
                 tells warm from cold HERE (A is the landing, which is also the Main_Init spawn), and MUSIC (the host's FIELD
                 battle song over the guest's suspended world song).
         HF-REJOIN decision 10: after the return the rejoin RESUMES -- the host back on 6603 past the hold, the guest rejoins 6603
                 from the world map (FieldHUD 6603 within REJOIN_S, lands +1, the landed line) and NO SECOND RETURN is counted there
                 (while the world diorama was up the follow compared against no field: the host's battle return was no arrival).
  decline THE WATCHER's DURABLE DECLINE on a real wire (fix1; decisions 3 + 4): the world-battle tape again; after WD-I (WB-I's
         instrument) the guest boards a chocobo (`vehicle 1`: its projection declines the world visit), then the host's battle:
         WD-DECL  the peer decodes NO BOOTING and NO DECLINED on its nonce (every report NONE: watching false, the digit panel's
                  slots kept); dio.visit_decline the twin's vehicle line; dio.declines +1 EXACTLY once, durable; nothing booted on
                  any sample, and (fix2, fix3) every sample ON THE WORLD MAP by witnesses the engine does not compute, beside its
                  `booted` claim: ui_state WorldHUD, the stage scene no swirl or battle (a world boot's swirl writes no UI state --
                  it reads WorldHUD on SwirlScene) and world.ticks live (-1: the WorldMap level gone); world.ticks monotonic (no
                  reload); 'diorama declined on world map 9011: ...' exactly once. THE WINDOW (decline_window): from the battle
                  on the wire to the host's entry into 300 on the wire, UNCUT -- the follow waits FollowStableMs past that entry
                  (fix3-r2: the host's intent fast path is the one unbenched caveat, see decline_window), so a FieldHUD inside it
                  is the guest LEAVING the world map (red, its field named); only with no entry anchor is
                  it cut at a FieldHUD on 300 (the rejoin: that load's own trailing samples spared). A game quiet on SwirlScene
                  there is SWIRL-HANG whatever the claim says. Then `vehicle 0`. (Before s145 the `vehicle` verb is never sent:
                  red, predicted.) A host battle that reached the wire before the guest was ABOARD -- anchored at or before the
                  state read once `vehicle 1` returned, or a `vehicle 1` refused with that boot on the next sample -- is the
                  instrument's: WD-I red, WD-DECL 'not reached: the instrument', never judged (the on-foot guest rightly boots
                  it; and no `vehicle 0` then -- a dismount mid-fight would boot it unwatched).
  COMMON T2-TAPE (the tape reads back and the plan fits), T2-PEER (port free, the owner's bridge DOWN, the config line, the guest
         connected, the replay started), T2-SAVE (final: AutoSaveOnlyAtMoogle off; no title fallback), T2-INI (final: Memoria.ini
         byte-exact). Never binds 49201.

DUO (`py tools/harness/duo.py studies/test-harness/scenarios/coop_world_battle.py`; PAIR on 6603, the host seeded through
COOPPARTY so its slot 1 is the guest's; keyed by the GUEST's stage -- both roots junction one Managed):
  D0-D2  coop_world_wait's: both on 6603, the guest mirroring; the host walks out -> the guest's line on 6603; the guest walks out
         -> frozen on 9011, the line there, the hold released by b6. The guest then teleports onto ICE_TILE (snapshot A).
  DB     the host's `battle 67 0 rand` on WorldHUD: the guest boots from WorldHUD (never FieldHUD; dio.booted_world, warm) and the
         HOST's start hold reads its report BOOTING, then LIVE, on its own nonce (host.start_hold.guest; no NONE / DECLINED / BUSY
         between) -- and (fix2, fix3) the hold's OWN verdict, read before the verb and after the fight. THE OPENING's decision is
         start_hold.why, kept with release and late_ms until the host's next own battle: 'booting', release 'live', late_ms -1 (a
         late arm, 'late', or a guest already LIVE at the opening, 'live', reads red); THE RELEASES are the counters, which see every
         release between the verb and the end of the fight but never how the hold armed: live +1 and every other reason +0, holds
         armed (start_hold.count) +1, and battle.epoch (party.battle_no, stock) +1 -- one own battle. (The host's samples start
         once its battle is up -- usually inside the intro, before the opening: the end state carries the opening's decision.)
  DP     the guest plays: its 'ready mirror is SERVING' line, and the host decodes the guest's control byte 2 / 3 on the battle
         (host.wait.menu) -- its stock menu is up.
  DR     the host wins; both back on the world map: the guest left on `terminal` / `host_world` (never `stall_cap`), WARM at A
         (counted on its own load), still frozen; WB-RET's witnesses too (fix1: battle_prob by value, the MAP digest, the camera,
         MUSIC).
  D3     coop_world_wait's D3 (the host enters the Ice Cavern -> the guest rejoins 300; THE BRACKET LAW) and no second return
         counted on 300.
  (The race -- the host entering the Ice Cavern within 2 s of its victory, the shared latch serializing the leave and the
  rejoin -- is NOT benched here: an owner duo check.)

SWIRL-HANG (decision 11): wherever a leg starts a battle or boots a diorama from the world map, a game that goes QUIET with its
last state on SwirlScene (no publish for QUIET_S) is an INSTRUMENT row (<PFX>-SWIRL, its detail 'SWIRL-HANG'): Memoria.log and
output_log.txt archived into the run dir, a frame grabbed (tools/game_snap.ps1 -Id <the game's pid>), the leg stopped (the rows
after it 'not reached: SWIRL-HANG'), the session left to kill the game -- never an engine verdict. The runners re-run that leg
ONCE when its output says SWIRL-HANG. Every boot and battle start writes the state every frame (`stateevery 1`).

CALIBRATION -- a check that cannot fail is not a check.
  * SOLO on the deployed s144 (be9abacbd7b11d64) with COOP_CALIBRATE=1: no `netsync.world.dio`, so the driver refuses `bench
    worldwarm`, `vehicle` and a world `dioboot` before the step (an s144 agent reads `bench worldwarm` as `bench 1`). Red, exactly
    (OLD_PREDICTED): P0, P1, BOOT, AUDIO, RET, PLACE, CAM, MAP, MODE, MUSIC, FROZEN, SILENT, RESET, VEH, LEVER, WC. GREEN:
    INI, OR, S0, ROUTE, A (the walk and s144's freeze), R (the role released), SWIRL.
  * SOLO on s145 with COOP_CALIBRATE=1: `bench worldwarm off` pulled at P1 and re-pulled after every harness release until LEVER:
    every world boot DECLINES -- never a cold return. Red, exactly (LEVER_PREDICTED): BOOT, AUDIO, RET, PLACE, CAM, MAP, MODE,
    MUSIC, FROZEN, SILENT, RESET, VEH (aboard, the lever's row outranks the vehicle's: the decline names the CALIBRATION). GREEN:
    P0, P1, A, LEVER (its own), WC (its own `cold` replaces `off`), R, SWIRL.
  * T2 on an s144 GUEST (COOP_CALIBRATE=1 adds <LEG>-CAL): battle -- exactly WB-BOOT, WB-PLAY, WB-RET (it stays WorldHUD, the peer
    reads its report NONE: the digit panel); held -- exactly HF-BOOT, HF-RET; decline -- exactly WD-DECL (no `vehicle` verb). The instrument rows and WB-300 / HF-REJOIN (s144's
    rejoin and hold) are never predicted red. T2 has no lever (the lever is the selftest role's).
  * DUO on s144 (COOP_CALIBRATE=1): exactly DB, DP, DR (D-CAL).
  * OFFLINE: the stand-in (tools/harness/fakegame.py, rung `worlddio`; its WORLD_DIO_FAULTS) and ff9mapkit/tests/
    test_coop_world_battle.py: every leg smoked against it, each fault red in exactly its *_FAULT_REDS rows, s144's stand-in
    exactly OLD_PREDICTED, the lever exactly LEVER_PREDICTED -- never read <LEG>-CAL offline: the engine is the calibration.
    (fix3) With the stand-in's sound instances on (FakeGame.world_music; fix3-r2: their fades on the wall, world_music_wall)
    MUSIC is judged through each leg's own call site, each WORLD_MUSIC_FAULTS lever red in exactly its MUSIC_FAULT_REDS rows (the
    held leg's boot_song_live named not discriminating inside the fade); the duo's host start hold is the engine's
    StartHoldStep (battlewire.start_hold_step) on the stand-in's opening, its guest's world boot swirling and loading first.

PRECONDITIONS -- THE OPERATOR'S JOB (the bench edits no ini but the T2 legs' guarded [Netsync] keys, deploys nothing): the DLL
under test deployed; controllers OFF and nobody at the keyboard (THE UNATTENDED LAW: every walk, Confirm, boot and battle is harness
input), FF9 unfocused; 6603 registered (FF9CustomMap-world); the T2 legs: the bench port free, [SaveFile] AutoSaveOnlyAtMoogle 0,
the tapes recorded (cal145.example.sh records the world-battle tape on s144 FIRST), AND THE OWNER's OWN BRIDGE DOWN
(127.0.0.1:49201) -- the legs refuse it (T2-PEER, nothing edited).

WHAT NO LEG HERE REACHES (named, not hidden): a real chocobo / airship round trip (decision 4: aboard declines -- the decline
itself IS benched, solo by VEH and on a real wire by T2 decline; a boot aboard is the owner's two-PC check), the event worlds (9001 / 9004 / 9006 / 9012: no tag 10 -- the runtime row covers them), the race above, the ~ menu's
"Release world freeze" surviving a world battle (no harness verb: the stand-in's rows and an owner check), the audio by ear.

    py tools/play.py studies/test-harness/scenarios/coop_world_battle.py --field 6603
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_world_battle.py --field 6603
    COOP_WB_LEG=battle py tools/play.py studies/test-harness/scenarios/coop_world_battle.py
    COOP_WB_LEG=held COOP_TAPE=<a 6603 field-battle tape> py tools/play.py studies/test-harness/scenarios/coop_world_battle.py
    COOP_WB_LEG=decline py tools/play.py studies/test-harness/scenarios/coop_world_battle.py
    py tools/harness/duo.py studies/test-harness/scenarios/coop_world_battle.py
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
import re
import shutil
import subprocess
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

PROBE = cb.R3_PROBES[145]                                  # netsync.world.dio: the s145 capability
LEGS = ("solo", "battle", "held", "decline")              # [fix1] + decline: the watcher's durable decline on a real wire


def _leg(raw) -> str | None:
    n = (raw or "solo").strip().lower()
    n = {"t2": "battle", "world-battle": "battle", "field": "held", "held-field": "held", "": "solo"}.get(n, n)
    return n if n in LEGS else None


_RAW_LEG = os.environ.get("COOP_WB_LEG", "solo")
LEG = _leg(_RAW_LEG)

# ------------------------------------------------------------------------------------------------ the route (coop_world_wait's)
FARSHORE, WORLD, ICE_CAVERN = cw.FARSHORE, cw.WORLD, cw.ICE_CAVERN
FS_LANDING, ICE_TILE = cw.FS_LANDING, cw.ICE_TILE
DIO_SCENE = 359                    # BSC_WM_0007, the Mist continent's own world formation: the selftest boot's scene
DIO_PATTERN = 0
SCENE, GROUP = cw.SCENE, cw.GROUP  # the battle verb's (67, one Goblin): the tapes and the duo
HELD_FIELD = FARSHORE              # the held leg's host fights on the field the guest walked out of

# ------------------------------------------------------------------------------------------------ the measures
HELD_U = cw.HELD_U                 # a hold that moves the walker less than this is HELD
WALK_FRAMES = cw.WALK_FRAMES       # the freeze witness' `hold up`
WALK_OFF_FRAMES = 45               # A: one `hold up` off the landing (~12-25u in game)
WALK_OFF_TRIES = 3
A_AWAY_MIN = 12.0                  # A stands at least this far from the landing (the Main_Init spawn)
LANDING_MIN = 8.0                  # ...and a warm return at least this far from it
RETURN_TOL = cw.RETURN_TOL         # a warm return stands within this of A (world units)
ROUTE_TOL = cw.ROUTE_TOL           # the cold reference lands within this of the landing
CAM_FRAMES = 20                    # A: `hold leftbumper` this long turns the world camera
CAM_TURN_MIN = 5.0                 # ...by at least this many degrees (the camera witness discriminates)
CAM_TOL = 1.0                      # a kept camera reads A's rotation within this
BOOT_S = 30.0                      # the boot verb -> the diorama up (BattleHUD, booted)
LEAVE_S = 45.0                     # `dioleave` -> the first world frame
SETTLE_S = 15.0                    # ...-> the walker settled with control
SONG_FADE_S = 2.5                  # fix2: MUSIC's settled read waits out the engine's stop fades (2 s StopCurrentSong(120); 0.5 s floor)
#: [fix3-r2] FF9SOUND_SONG_STOPCURRENT's floor (AllSoundDispatchPlayer.MINIMUM_SONG_FADE_MS): BeforeWorldEvents' stop of a battle
#: song still current over the suspend slot fades this long -- on the WALL (SaXAudio.Stop: a native real-time fade)
STOPCURRENT_FADE_MS = 500
DECLINE_S = 2.0                    # a refused boot's watch: no boot, no reload
QUIET_S = 5.0                      # a game silent this long on SwirlScene is SWIRL-HANG (the instrument)
POLL_S = 0.1

# ------------------------------------------------------------------------------------------------ T2 / duo
PORT = pb.env_int("COOP_PEER_PORT", pb.WORLD_PORT)        # a PRIVATE port: 49201 (the owner's bridge) is refused
CODE = pb.BENCH_CODE
GRACE_MS, GRACE_NOTE = pb.engine_grace(os.environ.get("COOP_GRACE_MS", str(pb.BENCH_GRACE_MS)))
GUEST_VALUES = {"Enabled": "1", "Role": "client", "RelayUrl": f"ws://127.0.0.1:{PORT}", "SessionCode": CODE,
                "FollowHost": "1", "TargetField": "0", "GuestSlots": "0", "GuestStockMenu": "1",
                "SessionGraceMs": str(GRACE_MS), "AutoTeleport": "0", "DioramaSwirlFrames": "0"}
#: the held leg's tape home (the plain recorder's COOP_TAPE_DIR there: its latest.json is THAT dir's, never coop_cut_hold's)
HELD_TAPE_SUBDIR = "held-6603"
HELD_PRE_NEED_S = 75.0             # the held tape's host on 6603 before its battle: the guest pairs and calibrates inside it
#: the held leg's walk out starts this long before the host's battle reaches the wire: the walk to the door, the world's load
#: (~4.4 s before its first WorldHUD frame) and the freeze fit before it, and the battle still lands inside the 15 s hold
HELD_LEAD_S = 12.0
REPLAY_SPEED = 1.0                 # replay-host replays in real time (a test seam: the stub replays faster)
FORCE = pb.env_flag("COOP_WB_FORCE")
DIAL_S = 25.0                      # the peer listening -> the guest connected
PAIR_S = 45.0                      # the replay's start -> paired + ARMED on 6603
EXIT_S = 60.0                      # ...the host's world exit
BATTLE_WAIT_S = 150.0              # A -> the host's battle on the wire (the rest of the tape's dwell)
BOOT_WAIT_S = 30.0                 # the battle on the wire -> the guest's diorama up
LIVE_WAIT_S = 30.0                 # ...-> its report LIVE
RET_WAIT_S = 120.0                 # ...-> back on the world map
ENTER_WAIT_S = 90.0                # the return -> the host's entry into 300 on the wire
REJOIN_S = 40.0                    # the host on 300 -> the guest on 300
HOLD_WAIT_S = 30.0                 # the duo: the host's battle up -> its start hold decided and the guest LIVE
BATTLE_S = cw.BATTLE_S
FIGHT_S = cw.FIGHT_S
RETURN_S = cw.RETURN_S

# ================================================================================================ the catalogs
SOLO_CHECKS = {
    "S145-INI": "precondition (Memoria.ini, READ-ONLY): [Netsync] Enabled 0 or absent (the selftest role)",
    "S145-OR": "the offline oracle: coop_world_wait.read_oracle (the door, 6603's WorldMap(9011), WORLD11's Field(300), block "
               "(18,12) stock, no fork of 300, the battle scene registered), the diorama scene DIO_SCENE (359) registered, and "
               "the encounter-rate oracle (WORLD11's op-26 writes: Main_Init's and Main_Reinit's battle_prob, read off the "
               "world script 9011 loads)",
    "S145-S0": "newgame -> (the COOPPARTY seed) -> 6603 -> encounters off -> the forced selftest role",
    "S145-P0": f"the engine publishes `{PROBE}` (AppendWorldDio's keys in order; `world` = freeze/rejoin/waitline/dio; `prev_mode`; "
               "the six world witness keys) and logged 'world diorama selftest: OK (86 rows)', 'world watcher selftest: OK (59 "
               "rows)', 'world freeze selftest: OK (46 rows)', 'diorama watcher selftest: OK (32 rows)' -- none FAIL",
    "S145-ROUTE": f"the walk out of {FARSHORE} lands on WorldHUD, world {WORLD}, within {cw.ROUTE_TOL:g}u of the landing "
                  f"{FS_LANDING} (the instrument)",
    "S145-A": f"THE INSTRUMENT, snapshot A: walked >= {A_AWAY_MIN:g}u off the landing unfrozen, the camera turned, then `bench 1` "
              f"freezes it (`hold up` < {HELD_U:g}u); on s145 the camera >= {CAM_TURN_MIN:g} deg from the arrival's and every "
              "world witness live",
    "S145-BOOT": f"`netsync dioboot {DIO_SCENE} {DIO_PATTERN} wire` from WorldHUD boots WARM: boot_world {WORLD}, boot 'warm', "
                 "booted_world; prev_mode 3, gMode stays 3; diorama boot 'warm', boot_field -1, boot_x/z at A; the warm primed "
                 "line once, no REFUSED; never FieldHUD",
    "S145-AUDIO": "no 'diorama pre-swirl audio replicate failed' line and no 'diorama swirl centre (world) failed' line since "
                  "the boot (on a boot that happened)",
    "S145-RET": f"`dioleave` lands on WorldHUD {WORLD}: the return counted WARM on its own load (the first world sample: returns "
                "+1, last_return 'warm', last_world 9011, diorama last_return 'warm' / field -1), the world reloaded (ticks "
                "restarted), never FieldHUD, the leave line and OUR prime's warm RETURN line once (never 'did NOT prime'), no "
                "cold one",
    "S145-PLACE": f"the settled return within {RETURN_TOL:g}u of A and >= {LANDING_MIN:g}u from the landing",
    "S145-CAM": f"world.cam_rot within {CAM_TOL:g} deg of A's and cam_upper A's (prevMode 3 kept the camera)",
    "S145-MAP": "the MAP-var digest (world.mapvar) A's exactly and world.battle_prob BY VALUE: Main_Reinit's own write (the "
                "oracle's: 231 on WORLD11) -- never A's (A follows a Main_Init load)",
    "S145-MODE": "the live travel mode (world.ctl) 0 -- on foot -- as at A",
    "S145-MUSIC": "judged only when discriminating (A's song and the boot's battle song read and different), on the sound "
                  "INSTANCES: booted, the slot holds A's song (dio.suspend_song); returned, A's own instance plays (dio.song_sid "
                  "A's), nothing latched at the Leave plays over it (dio.boot_song_live false), the bookkeeping A's; else green, "
                  "'not discriminating' named (a settled read still fading is re-read up to SONG_FADE_S: song_quiet; the held "
                  "leg's recorded tail is never re-read -- its boot_song_live is judged only 500 ms past the first world sample, "
                  "on the wall, else named not discriminating)",
    "S145-FROZEN": "still frozen after the round trip: `hold up` < HELD_U, freeze.on 'bench', edges A's +1",
    "S145-SILENT": "the host-silent lane (`dioboot 359 0 wire silent`): booted warm from the world, back on WorldHUD at A; while "
                   "booted the slot holds A's song and nothing is current, at the return A's own instance plays again (MUSIC's "
                   "judge, the 0xFFFE lane)",
    "S145-RESET": "`reset` with a world diorama up: the deferred release lands the return WARM (returns +1, last_return 'warm') "
                  "within RETURN_TOL of where it booted, the role released",
    "S145-VEH": "`vehicle 1` on 9011, then the boot DECLINES: refused, never booted, every sample WorldHUD, declines +1, durable, "
                "the twin's vehicle why, no world reload; `vehicle 0` -> back on foot",
    "S145-LEVER": "`bench worldwarm off` (its OFF line) -> the boot declines: refused, never booted, declines +1, durable, the "
                  "twin's CALIBRATION why, no reload",
    "S145-WC": "THE COLD REFERENCE, last (`bench worldwarm cold`): boot 'cold', the return 'cold', battle_prob Main_Init's (the "
               "oracle's) -- and PLACE's and MAP's own judges read that return RED: the warm rows CAN fail",
    "S145-R": "`reset` (the lever pulled just before it) releases the role and the lever ('world warm gate back ON (released "
              "with the harness)' once); re-read WITH the role: dio.lever 'on' (before s145: the role released)",
    "S145-SWIRL": "the instrument: no boot or battle start hung in the swirl (SWIRL-HANG: the logs archived, a frame grabbed, the "
                  "leg stopped -- never an engine verdict; the runner retries the leg once)",
}
SOLO_ORDER = ("S145-INI", "S145-OR", "S145-S0", "S145-P0", "S145-P1", "S145-ROUTE", "S145-A", "S145-BOOT", "S145-AUDIO",
              "S145-RET", "S145-PLACE", "S145-CAM", "S145-MAP", "S145-MODE", "S145-MUSIC", "S145-FROZEN", "S145-SILENT",
              "S145-RESET", "S145-VEH", "S145-LEVER", "S145-WC", "S145-R", "S145-SWIRL")


def solo_catalog(calibrate: bool) -> dict:
    c = dict(SOLO_CHECKS)
    c["S145-P1"] = ("the lever PULLED for calibration (s145): `netsync bench 0`, then `bench worldwarm off` -> dio.lever 'off' "
                    "and its OFF line once" if calibrate else
                    "`netsync bench 0` accepted (the walker free for A) and the lever at rest: dio.lever 'on'")
    out = {k: c[k] for k in SOLO_ORDER}
    if calibrate:
        out["S145-CAL"] = ("CALIBRATION: the engine's stage decides the set -- before s145 exactly OLD_PREDICTED red, on s145 "
                           "under `bench worldwarm off` exactly LEVER_PREDICTED red")
    return out


#: the world rows: a route (or an A) that cannot run records them "not reached"
WORLD_ROWS = ("S145-BOOT", "S145-AUDIO", "S145-RET", "S145-PLACE", "S145-CAM", "S145-MAP", "S145-MODE", "S145-MUSIC",
              "S145-FROZEN", "S145-SILENT", "S145-RESET", "S145-VEH", "S145-LEVER", "S145-WC")
#: the rows a world boot's RETURN feeds (judged on the settled return): no return -> "not reached"
RETURN_ROWS = ("S145-PLACE", "S145-CAM", "S145-MAP", "S145-MODE", "S145-MUSIC", "S145-FROZEN")
#: [calibration] an engine before s145 (the deployed s144): every key-judged row and every world-boot row
OLD_PREDICTED = ("S145-P0", "S145-P1", "S145-BOOT", "S145-AUDIO", "S145-RET", "S145-PLACE", "S145-CAM", "S145-MAP", "S145-MODE",
                 "S145-MUSIC", "S145-FROZEN", "S145-SILENT", "S145-RESET", "S145-VEH", "S145-LEVER", "S145-WC")
#: [calibration] s145 under `bench worldwarm off` (pulled at P1, re-pulled after every release until LEVER): every world boot
#: declines -- never a cold return
LEVER_PREDICTED = ("S145-BOOT", "S145-AUDIO", "S145-RET", "S145-PLACE", "S145-CAM", "S145-MAP", "S145-MODE", "S145-MUSIC",
                   "S145-FROZEN", "S145-SILENT", "S145-RESET", "S145-VEH")
#: the stand-in's FAULT LEVERS (fakegame.WORLD_DIO_FAULTS) -> exactly the SOLO rows each turns red (tests pin it); a fault that
#: breaks only the followed client (the watcher) reds no solo row
SOLO_FAULT_REDS = {
    "boot_cold": ("S145-BOOT", "S145-RET", "S145-PLACE", "S145-MAP", "S145-SILENT", "S145-RESET"),   # a cold reload: the spawn,
                                                                                                    # Main_Init's rate
    "leave_fieldmap": ("S145-RET", "S145-PLACE", "S145-CAM", "S145-MAP", "S145-MODE", "S145-MUSIC", "S145-FROZEN",
                       "S145-SILENT", "S145-RESET", "S145-WC"),                       # s144's Replace("FieldMap"): the field
    "prevmode_unset": ("S145-BOOT", "S145-CAM"),                                      # the return's camera reset (prevMode 1)
    "audio_field_block": ("S145-AUDIO",),                                             # the field block's cosmetic failure
    "vehicle_boots": ("S145-VEH",),                                                   # aboard, it boots
    "lever_ignored_warm": ("S145-LEVER", "S145-WC"),                                  # off and cold both boot warm
    "warm_lever_stuck": ("S145-R",),                                                  # the release leaves the lever
    "decline_reload": ("S145-VEH", "S145-LEVER"),                                     # a refusal reloads the world
    "return_uncounted": ("S145-RET", "S145-RESET", "S145-WC"),                       # s144's consume rule
    "refreeze_lost": ("S145-FROZEN",),                                                # free after the fight
    "proof_fail": ("S145-P0",),                                                       # the engine's own proof FAILs
}

# ---- T2
T2_COMMON = {
    "T2-TAPE": "the tape reads back and this leg's plan fits it (battle: plan_world_leg('world-battle') with the host's entry "
               "into 300; held: plan_held_leg)",
    "T2-PEER": f"port {PORT} free, the owner's bridge (49201) DOWN; the guest config written and the engine's own config line; "
               "the replay-host listening, the guest connected, the replay started",
    "T2-SAVE": "THE PRECHECK: [SaveFile] AutoSaveOnlyAtMoogle off before the run, and no 'session ended, no autosave to resume "
               "-> title screen' line in it",
    "T2-INI": "Memoria.ini restored byte-exact (sha256) after the run -- the install is shared",
}
T2_CHECKS = {
    "battle": {
        "S145-WB-I": "the instrument: paired on 6603 and ARMED before the host's world exit; the guest walks out, FROZEN, onto "
                     "the Ice Cavern tile, snapshot A -- before the host's battle reaches the wire",
        "S145-WB-BOOT": "from the battle's first frame never FieldHUD; the diorama booted from the world (booted_world, boot_world "
                        "9011, boot 'warm'); the peer decodes the guest's report BOOTING then LIVE on THIS battle; the guest's "
                        "'diorama LIVE' line",
        "S145-WB-PLAY": "its stock menu served: the peer reads control byte 2 / 3 while LIVE on this battle; 'ready mirror is "
                        "SERVING' logged since the boot",
        "S145-WB-RET": "the leave on `terminal` or `host_world` (never `stall_cap`); WorldHUD 9011 within RETURN_TOL of A, counted "
                       "warm on its own load, the world reloaded, still frozen; battle_prob Main_Reinit's (the oracle's), the MAP "
                       "digest and the camera A's, MUSIC on the sound instances",
        "S145-WB-300": "the host's entry: the guest rejoins 300 (FieldHUD 300, lands +1, the landed line) and no second return "
                       "is counted there (diorama / dio returns unmoved, last_return_field never 300)",
        "S145-WB-SWIRL": "the instrument: the guest's boot never hung in the swirl (SWIRL-HANG: logs, a frame, the leg stopped)",
    },
    "held": {
        "S145-HF-I": "the instrument: paired + ARMED on 6603; the walk out timed HELD_LEAD_S before the host's battle; on "
                     "WorldHUD 9011, follow.hold 6603 and its line once, freeze.on -- and at the battle's first frame still on "
                     "the world map inside the hold",
        "S145-HF-BOOT": "the host's FIELD battle boots the guest's diorama from WorldHUD: never FieldHUD; booted from the world, "
                        "warm; the peer decodes BOOTING then LIVE on THIS battle; the guest's 'diorama LIVE' line",
        "S145-HF-RET": "the leave on `terminal` or `host_field` (never `stall_cap`); back at A on WorldHUD, counted warm on its "
                       "own load, still frozen; battle_prob Main_Reinit's (the oracle's: the witness that tells warm from cold "
                       "here, A being the landing), the MAP digest and the camera A's, MUSIC on the sound instances",
        "S145-HF-REJOIN": "decision 10: after the return the rejoin RESUMES -- FieldHUD 6603 (lands +1, the landed line) and no "
                          "second return counted there (diorama / dio returns unmoved, last_return_field never 6603)",
        "S145-HF-SWIRL": "the instrument: the guest's boot never hung in the swirl",
    },
    "decline": {
        "S145-WD-I": "the instrument: WB-I's -- paired + ARMED on 6603 before the host's world exit; the guest walks out, FROZEN, "
                     "onto the Ice Cavern tile, snapshot A -- before the host's battle reaches the wire; and (fix3) the guest "
                     "ABOARD (`vehicle 1` read back) before it does",
        "S145-WD-DECL": "aboard (`vehicle 1` after WD-I) the host's battle DECLINES on the watcher: the peer decodes no BOOTING "
                        "and no DECLINED on its nonce (every report NONE); dio.visit_decline the twin's vehicle line; declines +1 "
                        "exactly once, durable; never booted, every sample on the world map (WorldHUD, no swirl / battle stage, "
                        "world.ticks live) up to the host's entry; world.ticks monotonic (no reload); the 'diorama declined on "
                        "world map 9011' line exactly once; then `vehicle 0` (a battle on the wire before the guest was aboard: "
                        "the instrument's)",
        "S145-WD-SWIRL": "the instrument: nothing hung in the swirl (no boot is expected)",
    },
}
T2_PFX = {"battle": "S145-WB", "held": "S145-HF", "decline": "S145-WD"}
#: [calibration] a GUEST before s145: it stays WorldHUD and reports NONE (the digit panel)
T2_PREDICTED = {"battle": ("S145-WB-BOOT", "S145-WB-PLAY", "S145-WB-RET"),
                "held": ("S145-HF-BOOT", "S145-HF-RET"),
                "decline": ("S145-WD-DECL",)}                      # (no `vehicle` verb before s145: never sent)
#: the stand-in faults -> exactly the T2 rows each turns red (the stub peer's smoke; tests pin it)
T2_FAULT_REDS = {
    "battle": {"boot_cold": ("S145-WB-BOOT", "S145-WB-RET"),                  # a cold boot, its return at the spawn
               "leave_fieldmap": ("S145-WB-RET", "S145-WB-300"),               # s144's Replace("FieldMap"): no world return
               "return_uncounted": ("S145-WB-RET", "S145-WB-300"),             # counted at the next FIELD load: 300's
               "refreeze_lost": ("S145-WB-RET",),                              # free after the fight
               "hostworld_blind": ("S145-WB-RET",)},                           # s144's watch step: it leaves at the stall cap
    "held": {"boot_cold": ("S145-HF-BOOT", "S145-HF-RET"),
             "leave_fieldmap": ("S145-HF-RET", "S145-HF-REJOIN"),
             "return_uncounted": ("S145-HF-RET", "S145-HF-REJOIN"),           # ...counted at 6603's load: a second return
             "refreeze_lost": ("S145-HF-RET",)},
    "decline": {"decline_unprojected": ("S145-WD-DECL",)},           # the projection skipped: aboard, it boots (BOOTING first)
    # (`follow_departed` reds nothing here: the host's return onto the departed field read "arrived" inside the diorama only
    # clears a candidate the world map re-reads after the return -- the stand-in's WC-FOLLOW, the intent path, is its pin)
}


def t2_catalog(leg: str, calibrate: bool) -> dict:
    p = T2_PFX[leg]
    cat = {"T2-TAPE": T2_COMMON["T2-TAPE"], "T2-PEER": T2_COMMON["T2-PEER"]}
    cat.update({k: v for k, v in T2_CHECKS[leg].items() if not k.endswith("-SWIRL")})
    cat[f"{p}-SWIRL"] = T2_CHECKS[leg][f"{p}-SWIRL"]
    if calibrate:
        cat[f"{p}-CAL"] = ("CALIBRATION: exactly the predicted rows are red for the GUEST's stage (before s145 T2_PREDICTED, on "
                           "s145 none)")
    cat["T2-SAVE"] = T2_COMMON["T2-SAVE"]
    cat["T2-INI"] = T2_COMMON["T2-INI"]
    return cat


# ---- the duo
DUO_CHECKS = {
    "S145-D0": "the instrument: both on FieldHUD 6603, the guest mirroring (duo's C2-C6 paired them)",
    "S145-D1": "coop_world_wait's D1: the host walks out of 6603 -> the guest LEFT on 6603 stays there and shows the line",
    "S145-D2": "coop_world_wait's D2: the guest walks out too -> FROZEN on 9011, the line there, the hold released by b6",
    "S145-DB": "the host's `battle 67 0 rand` on WorldHUD: the guest boots from WorldHUD (never FieldHUD; booted_world, warm) "
               "and the HOST's start hold reads its report BOOTING then LIVE on its own nonce (nothing between); the opening's "
               "decision why 'booting' (never late), release 'live', late_ms -1; released.live +1 and every other reason +0, "
               "holds armed +1, one own battle (battle.epoch +1)",
    "S145-DP": "the guest plays: its 'ready mirror is SERVING' line and the host decodes its control byte 2 / 3 on the battle",
    "S145-DR": "the host wins: the guest left on `terminal` / `host_world` (never `stall_cap`), WARM at A on 9011 (counted on its "
               "own load), still frozen; battle_prob Main_Reinit's, the MAP digest and the camera A's, MUSIC on the sound instances",
    "S145-D3": "coop_world_wait's D3: the host enters the Ice Cavern -> the guest rejoins 300 (THE BRACKET LAW) and no second "
               "return is counted there",
    "S145-D-SWIRL": "the instrument: neither game's battle start hung in the swirl",
}
DUO_ORDER = ("S145-D0", "S145-D1", "S145-D2", "S145-DB", "S145-DP", "S145-DR", "S145-D3", "S145-D-SWIRL")
DUO_PREDICTED = ("S145-DB", "S145-DP", "S145-DR")          # a GUEST before s145 (the duo cannot mix DLLs: both are)
#: the stand-in faults -> exactly the duo rows each turns red (the stub link's smoke; tests pin it)
DUO_FAULT_REDS = {"boot_cold": ("S145-DB", "S145-DR"), "leave_fieldmap": ("S145-DR", "S145-D3"),
                  "hostworld_blind": ("S145-DR",), "return_uncounted": ("S145-DR", "S145-D3"),
                  "refreeze_lost": ("S145-DR",)}
#: [fix3 -- v-raudio-1-1] the stand-in's SOUND faults (fakegame.WORLD_MUSIC_FAULTS, its sound instances on: FakeGame.world_music)
#: -> exactly the rows each turns red, by leg (tests pin each through that leg's OWN MUSIC call site, song_quiet's re-read
#: included): BeforeWorldEvents' stop removed leaves the Leave-latched battle song playing over the restored world song; the
#: pre-fix2 latch order reds nothing on the solo leg (a mid-fight `dioleave`: no settle shut the song -- its own lane, the finished
#: fight's, is test_world_diorama_harness.py's). [fix3-r2] The stand-in's fades run on the WALL (FakeGame.world_music_wall), as
#: SaXAudio's do. The held leg's rejoin leaves the world map inside BeforeWorldEvents' 500 ms fade, so its boot_song_live is not
#: discriminating there (named): the stop's removal reds nothing, and the instance / slot / bookkeeping terms stay judged.
MUSIC_FAULT_REDS = {"solo": {"bwe_stop_missing": ("S145-MUSIC",), "latch_before_settle": ()},
                    "battle": {"bwe_stop_missing": ("S145-WB-RET",)},
                    "held": {"bwe_stop_missing": ()},
                    "duo": {"bwe_stop_missing": ("S145-DR",)}}
#: duo.py's CLI calls ``d.pair(**PAIR)``: both games New Game onto 6603 (the host first, seeded through COOPPARTY so its slot 1
#: -- GuestSlots 2 -- holds a member the guest's stock menu can serve)


def _seed_host(g) -> str:
    return cb.seed_party(g, back_to=FARSHORE)


PAIR = {"field": FARSHORE, "host_setup": _seed_host}


# ================================================================================================ the offline oracle
def world_battle_probs(raw: bytes) -> dict:
    """(PURE over a world dispatcher's .eb bytes) THE ENCOUNTER-RATE ORACLE (fix1): ff9.w_frameEventBattleProb has ONE writer,
    world script op 26 (ff9.cs case 26), so entry 0's RunWorldCode(26, N) in Main_Init (tag 0) and Main_Reinit (tag 10) are the
    values a cold and a warm world load read -- ``{"init": N, "reinit": N, "why": None}``; ``why`` names what does not hold
    (entry 0 lacks the tag, a function writes op 26 other than exactly once with a literal, or the two values are equal: then
    battle_prob could not tell a warm return from a cold one)."""
    cw._kit()
    from ff9mapkit.eb import EbScript
    out = {"init": None, "reinit": None, "why": None}
    eb = EbScript.from_bytes(bytes(raw))
    e0 = next((e for e in eb.entries if e.index == 0 and not e.empty), None)
    if e0 is None:
        out["why"] = "the world script has no entry 0"
        return out
    for tag, key in ((0, "init"), (10, "reinit")):
        f = next((fn for fn in e0.funcs if fn.tag == tag), None)
        if f is None:
            out["why"] = f"entry 0 has no tag {tag} ({'Main_Init' if tag == 0 else 'Main_Reinit'})"
            return out
        writes = [s for s in (str(i) for i in eb.instrs(f)) if "RunWorldCode(26" in s]
        vals = [int(m.group(1)) for m in (re.search(r"RunWorldCode\(26,\s*(-?\d+)\)", s) for s in writes) if m]
        if len(writes) != 1 or len(vals) != 1:
            out["why"] = (f"entry 0 tag {tag} writes op 26 {len(writes)}x ({writes[:3]}) -- the oracle wants exactly one "
                          "literal write")
            return out
        out[key] = vals[0]
    if out["init"] == out["reinit"]:
        out["why"] = f"Main_Init and Main_Reinit both write {out['init']}: battle_prob cannot tell a warm return from a cold one"
    return out


def world_prob_oracle(game) -> tuple:
    """(probs | None, where) -- :func:`world_battle_probs` over the world dispatcher 9011 LOADS: the highest stacked folder's
    override (coop_world_wait.deployed_world_eb), else the stock one in p0data (the kit's load_all_dispatchers; read-only). None =
    unreadable or not discriminating (``where`` says why). A SEAM: the tests stub it (the stand-in has no world script)."""
    try:
        raw, where = cw.deployed_world_eb(Path(game))
        if raw is None:
            cw._kit()
            from ff9mapkit.world.entrance import load_all_dispatchers
            raw = (load_all_dispatchers(Path(game)).get(cw.WORLD_EB_NAME.split(".")[0].lower()) or {}).get(cw.EVT_LANG)
            where = "p0data (stock)"
        if raw is None:
            return None, f"the world dispatcher {cw.WORLD_EB_NAME} is unreadable (no override, none in p0data)"
        probs = world_battle_probs(raw)
    except Exception as err:                              # noqa: BLE001 - a parse fault is a named problem
        return None, f"the world script is unreadable: {type(err).__name__}: {str(err)[:200]}"
    if probs["why"] is not None:
        return None, f"{where}: {probs['why']}"
    return {"init": probs["init"], "reinit": probs["reinit"]}, f"{where}: Main_Init {probs['init']}, Main_Reinit {probs['reinit']}"


def read_oracle(game: Path) -> dict:
    """S145-OR (READ-ONLY): coop_world_wait's oracle (the route and its targets), the diorama scene DIO_SCENE registered in the
    kit's scene table, and the encounter-rate oracle (:func:`world_prob_oracle`: ``facts['battle_prob']`` -- {init, reinit} or
    None). ``problems`` names every fact that does not hold (empty = the bench's assumptions stand)."""
    out = cw.read_oracle(Path(game))
    try:
        if not cw.scene_registered(DIO_SCENE):
            out["problems"]["dio scene"] = f"the diorama scene {DIO_SCENE} is not in the kit's scene table"
    except Exception as err:                              # noqa: BLE001 - a parse fault is a named problem
        out["problems"]["dio scene"] = f"the scene table is unreadable: {type(err).__name__}: {err}"
    probs, where = world_prob_oracle(game)
    out["facts"]["battle_prob"] = probs
    out["facts"]["battle_prob_from"] = where
    if probs is None:
        out["problems"]["battle_prob"] = where
    return out


# ================================================================================================ pure readers / judges
def _dio(x, key, default=None):
    """A ``netsync.world.dio`` leaf (absent = ``default``: an engine before s145)."""
    return cb.path(x, "netsync.world.dio." + key, default)


def _d(x, key, default=None):
    """A ``netsync.diorama`` leaf."""
    return cb.path(x, "netsync.diorama." + key, default)


_w, _f, _s, _num = cw._w, cw._f, cw._s, cw._num
world_xz, dist = cw.world_xz, cw.dist


def _top(x, key, default=None):
    """A top-level ``world`` leaf (the s145 witnesses: cam_rot, cam_upper, ctl, battle_prob, ticks, mapvar)."""
    return cb.path(x, "world." + key, default)


def music(x):
    """FF9Snd.GetCurrentMusicId as the agent publishes it (``netsync.battle.end.music``; -1 = none / unreadable)."""
    return _num(cb.path(x, "netsync.battle.end.music"))


def stage_of(x) -> int:
    """145 when the engine publishes `netsync.world.dio`; else coop_world_wait's (144, or the R3 ladder's highest patch)."""
    return 145 if cb.has(x, PROBE) else cw.stage_of(x)


def booted_world(s) -> bool:
    """(PURE) a world-booted diorama is up on this sample: the engine's claim AND the battle HUD."""
    return s is not None and _dio(s, "booted_world") is True and _d(s, "booted") is True and s.ui_state == "BattleHUD"


def on_world_free(s) -> bool:
    """(PURE) back on the world map with no diorama: WorldHUD, its position read, the world tick live."""
    return (s is not None and s.ui_state == "WorldHUD" and not _d(s, "booted") and world_xz(s)[0] is not None
            and (_num(_top(s, "ticks")) is None or _num(_top(s, "ticks")) >= 0))


def is_swirl_hang(scene, age_s, quiet_s: float = QUIET_S) -> bool:
    """(PURE) THE SWIRL-HANG SIGNATURE (decision 11): the game's LAST published state is on SwirlScene and nothing newer came for
    ``quiet_s`` -- the 1-in-26 short-swirl stall (UnloadUnusedAssets never completing after LoadLevel("SwirlScene")). An
    INSTRUMENT row, never an engine verdict. A quiet game anywhere else is not this (its own row says what it waited for)."""
    return scene == "SwirlScene" and age_s is not None and float(age_s) >= float(quiet_s)


def judge_probe(st, lines) -> tuple:
    """P0 (PURE): `netsync.world.dio` in AppendWorldDio's key order, `world` = s144's three blocks + `dio`, `prev_mode` right
    after `gmode`, the top-level `world` block ending in the six witness keys, and the s145 proof lines OK -- none FAIL (the
    counts are each line's s145 stage: THE STAGE LAW)."""
    R = BW
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}` -- an engine before s145"
    world = cb.path(st, "netsync.world") or {}
    top = list(cb.raw(st))
    wkeys = list(cb.raw(st).get("world") or {})
    keys_ok = (list(world) == list(R.WORLD_SENTINELS) and list(world.get("dio") or {}) == list(R.WORLD_DIO_SENTINELS)
               and "gmode" in top and "prev_mode" in top and top.index("prev_mode") == top.index("gmode") + 1
               and wkeys[-len(R.WORLD_WITNESS_SENTINELS):] == list(R.WORLD_WITNESS_SENTINELS))
    proofs = [(R.PROOF_WORLD_DIORAMA, R.WORLD_DIORAMA_SELFTEST_ROWS), (R.PROOF_WORLD_WATCHER, R.WORLD_WATCHER_SELFTEST_ROWS),
              (R.PROOF_WORLD_FREEZE, R.world_freeze_selftest_rows(145)), (R.PROOF_WATCH, R.watch_selftest_rows(145))]
    seen = {head.split(":")[0]: cb.count(lines, R.proof_ok(head, n)) for head, n in proofs}
    fails = {head.split(":")[0]: cb.count(lines, head + "FAIL") for head, _n in proofs}
    ok = keys_ok and all(v >= 1 for v in seen.values()) and not any(fails.values())
    return ok, (f"world {list(world)}, dio {list(world.get('dio') or {})}; prev_mode after gmode "
                f"{'prev_mode' in top and 'gmode' in top and top.index('prev_mode') == top.index('gmode') + 1}; world keys "
                f"...{wkeys[-6:]}; proof lines OK {seen}, FAIL {fails}")


def judge_rest(st, *, pulled: bool, lines=()) -> tuple:
    """P1 (PURE): `netsync bench` 0 (the walker free for A) and dio.lever 'on' -- or, ``pulled``, 'off' and its OFF line once."""
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}` (the lever's key)"
    lever, bench = _dio(st, "lever"), cb.path(st, "netsync.bench")
    if pulled:
        n = cb.count(lines, BW.LOG_WORLD_WARM_OFF)
        return lever == "off" and bench is False and n == 1, f"dio.lever {lever!r} (want 'off'), netsync.bench {bench!r}; the OFF line {n}x"
    return lever == "on" and bench is False, f"dio.lever {lever!r} (want 'on'), netsync.bench {bench!r} (want False)"


def judge_a(arr, a, away, moved, advanced) -> tuple:
    """A (PURE, the instrument): ``away`` (A's distance from the landing) >= A_AWAY_MIN; the freeze held a `hold up` (``moved`` <
    HELD_U over ``advanced`` >= WALK_FRAMES frames) with freeze.on 'bench'; where the engine publishes the s145 witnesses, the
    camera turned >= CAM_TURN_MIN from the arrival's ``arr`` and every witness reads live (mapvar 160 hex digits, battle_prob,
    ticks >= 0, ctl 0). The arrival's MAP digest beside A's is reported (a walk that changed nothing leaves WC to show it)."""
    w_ok, w_why = cw.judge_walk(moved, advanced, WALK_FRAMES, held=True)
    if a is None or away is None:
        return False, f"not reached: no snapshot A ({w_why})"
    fz = _w(a, "freeze") or {}
    frz_ok = (fz.get("on") is True and fz.get("why") == "bench") if cb.has(a, cw.PROBE) else True
    ok = away >= A_AWAY_MIN and w_ok and frz_ok
    why = (f"A at ({world_xz(a)[0]}, {world_xz(a)[1]}), {away:.1f}u off the landing (want >= {A_AWAY_MIN:g}); FROZEN {w_why}; "
           f"freeze on {fz.get('on')!r} why {fz.get('why')!r}")
    if cb.has(a, PROBE):
        r0, r1 = a.world_cam_rot, (arr.world_cam_rot if arr is not None else None)
        turned = None if r0 is None or r1 is None else abs(((r0 - r1) + 180.0) % 360.0 - 180.0)
        mv = a.world_mapvar
        live = (isinstance(mv, str) and len(mv) == 2 * BW.MAPVAR_BYTES and (a.world_battle_prob or -1) >= 0
                and (a.world_ticks or -1) >= 0 and a.world_ctl == 0)
        ok = ok and turned is not None and turned >= CAM_TURN_MIN and live
        why += (f"; the camera turned {turned if turned is None else round(turned, 2)} deg (want >= {CAM_TURN_MIN:g}); "
                f"witnesses live {live} (ctl {a.world_ctl}, battle_prob {a.world_battle_prob}, ticks {a.world_ticks}); the "
                f"walk {'CHANGED' if arr is not None and arr.world_mapvar != mv else 'did NOT change'} the MAP digest")
    return ok, why


def judge_boot(st, samples, lines, a) -> tuple:
    """BOOT (PURE): the booted sample ``st`` -- dio.booted_world, boot_world WORLD, boot 'warm'; prev_mode 3, gMode 3; diorama boot
    'warm', boot_field -1, boot_x / boot_z (PosObj: x 256) within RETURN_TOL of A's world x / z; the warm primed line once and
    no REFUSED line in ``lines`` (since the verb); no sample in ``samples`` (verb -> up) on FieldHUD."""
    if st is None or not booted_world(st):
        return False, f"not booted from the world (ui {getattr(st, 'ui_state', None)!r}, dio {_dio(st, 'booted_world')!r})"
    ax, az = world_xz(a) if a is not None else (None, None)
    bx, bz = _num(_d(st, "boot_x")), _num(_d(st, "boot_z"))
    near = None not in (ax, az, bx, bz) and dist((bx / 256.0, bz / 256.0), (ax, az)) <= RETURN_TOL
    primed = cb.count(lines, BW.log_world_warm_primed(WORLD, 0, 0).split(" player at ")[0])   # the twin's head (fix1)
    refused = cb.count(lines, "diorama boot REFUSED")
    field = [(cb.raw(s).get("frame"), s.field_id) for s in samples if s.ui_state == "FieldHUD"]
    ok = (_dio(st, "boot_world") == WORLD and _dio(st, "boot") == "warm" and st.prev_mode == 3 and st.gmode == 3
          and _d(st, "boot") == "warm" and _d(st, "boot_field") == -1 and near and primed == 1 and refused == 0 and not field)
    return ok, (f"dio boot_world {_dio(st, 'boot_world')!r} boot {_dio(st, 'boot')!r}; prev_mode {st.prev_mode!r} (replaced "
                f"{_dio(st, 'prev_mode_at_boot')!r}) gmode {st.gmode!r}; diorama boot {_d(st, 'boot')!r} field "
                f"{_d(st, 'boot_field')!r} at ({bx}, {bz}) -- {'at A' if near else 'NOT at A'} {(ax, az)}; the primed line "
                f"{primed}x, REFUSED {refused}x; FieldHUD samples {field[:3] or 'none'}")


def judge_audio(booted: bool, lines) -> tuple:
    """AUDIO (PURE): a boot happened and no pre-swirl audio failure line since it -- nor the world shape's own swirl-centre failure
    (fix1, audio-4: SetCenterPosition(1) logs its own text: a wrong swirl centre)."""
    n = cb.count(lines, BW.LOG_PRESWIRL_AUDIO_FAILED)
    c = cb.count(lines, BW.LOG_SWIRL_CENTRE_WORLD_FAILED)
    if not booted:
        return False, "not reached: no world boot (BOOT)"
    return n == 0 and c == 0, (f"'{BW.LOG_PRESWIRL_AUDIO_FAILED}' {n}x, '{BW.LOG_SWIRL_CENTRE_WORLD_FAILED}' {c}x since the boot "
                               "(want 0 / 0)")


def judge_return(first, settled, pre_ticks, r0, d0, lines, samples) -> tuple:
    """RET (PURE): ``first`` -- the first world sample after the leave -- counts the return WARM on its own load (dio.returns ==
    ``r0`` + 1, last_return 'warm', last_world WORLD, diorama.returns ``d0`` + 1, last_return 'warm' / field -1) with the world
    tick restarted below ``pre_ticks`` (a reload: the witness the engine does not compute); ``settled`` on WorldHUD WORLD;
    ``samples`` (the leave -> ``first``) never FieldHUD; ``lines`` (since the leave) the leave line and the warm return line
    once, no cold return line."""
    if first is None or settled is None:
        return False, "not back on the world map after the leave"
    field = [(cb.raw(s).get("frame"), s.field_id) for s in samples if s.ui_state == "FieldHUD"]
    t1 = _num(_top(first, "ticks"))
    reloaded = t1 is not None and pre_ticks is not None and 0 <= t1 < pre_ticks
    leave = cb.count(lines, BW.log_world_leave(WORLD))
    warm = cb.count(lines, BW.log_world_return_warm_prefix(WORLD))          # OUR prime's line (fix1: through 'the guest stands')
    unprimed = cb.count(lines, BW.LOG_WORLD_RETURN_UNPRIMED)                # the engine's slot's warm line: never ours
    cold = cb.count(lines, BW.log_world_return_cold_calibration(WORLD).split(" -> ")[0])
    ok = (_dio(first, "returns") == (r0 or 0) + 1 and _dio(first, "last_return") == "warm" and _dio(first, "last_world") == WORLD
          and _d(first, "returns") == (d0 or 0) + 1 and _d(first, "last_return") == "warm"
          and _d(first, "last_return_field") == -1 and reloaded and settled.ui_state == "WorldHUD"
          and settled.world_id == WORLD and not field and leave == 1 and warm == 1 and unprimed == 0 and cold == 0)
    return ok, (f"first world sample: dio returns {r0}->{_dio(first, 'returns')!r} last {_dio(first, 'last_return')!r} on "
                f"{_dio(first, 'last_world')!r}; diorama returns {d0}->{_d(first, 'returns')!r} last {_d(first, 'last_return')!r}"
                f" field {_d(first, 'last_return_field')!r}; ticks {pre_ticks}->{t1} ({'reloaded' if reloaded else 'NO reload'});"
                f" settled {settled.ui_state} world {settled.world_id}; FieldHUD {field[:3] or 'never'}; leave line {leave}x, warm "
                f"return {warm}x, cold {cold}x, unprimed {unprimed}x")


def judge_place(st, a) -> tuple:
    """PLACE (PURE): within RETURN_TOL of A, >= LANDING_MIN from the landing."""
    p, pa = world_xz(st), world_xz(a)
    if None in (p[0], pa[0]):
        return False, "no world position read"
    da, dl = dist(p, pa), dist(p, FS_LANDING)
    return da <= RETURN_TOL and dl >= LANDING_MIN, (f"({p[0]:.2f}, {p[1]:.2f}): {da:.2f}u from A (want <= {RETURN_TOL:g}), "
                                                     f"{dl:.1f}u from the landing (want >= {LANDING_MIN:g})")


def judge_camera(st, a) -> tuple:
    """CAM (PURE): cam_rot within CAM_TOL of A's (the angle's shortest way) and cam_upper A's."""
    r, ra = st.world_cam_rot, a.world_cam_rot
    if r is None or ra is None:
        return False, f"absent: cam_rot {ra!r} -> {r!r}"
    d = abs(((r - ra) + 180.0) % 360.0 - 180.0)
    return d <= CAM_TOL and st.world_cam_upper == a.world_cam_upper, (f"cam_rot {ra} -> {r} ({d:.2f} deg), cam_upper "
                                                                       f"{a.world_cam_upper} -> {st.world_cam_upper}")


def judge_mapvar(st, a, probs=None) -> tuple:
    """MAP (PURE): the MAP digest exactly A's, and world.battle_prob BY VALUE (fix1): Main_Reinit's own op-26 write ``probs['reinit']``
    (the offline oracle's: 231 on WORLD11) -- the reinit branch ran -- never A's (A follows a Main_Init load: 365, which a cold
    return reads again). ``probs`` None = no oracle: red, named (never A's value as a stand-in)."""
    mv, ma = st.world_mapvar, a.world_mapvar
    if mv is None or ma is None:
        return False, "absent: no world.mapvar"
    if not probs or probs.get("reinit") is None:
        return False, "no encounter-rate oracle (S145-OR's battle_prob: the world script's op-26 writes) -- battle_prob unjudged"
    diff = [i // 2 for i in range(0, min(len(mv), len(ma)), 2) if mv[i:i + 2] != ma[i:i + 2]]
    ok = mv == ma and st.world_battle_prob == probs["reinit"]
    return ok, (f"MAP digest {'= A' if mv == ma else f'differs at Map{diff[:8]}'}; battle_prob {a.world_battle_prob} -> "
                f"{st.world_battle_prob} (want Main_Reinit's {probs['reinit']}; Main_Init writes {probs.get('init')})")


def judge_mode(st, a) -> tuple:
    """MODE (PURE): on foot (world.ctl 0), as A."""
    return st.world_ctl == 0 and a.world_ctl == 0, f"world.ctl {a.world_ctl} -> {st.world_ctl} (want 0: on foot)"


def judge_music(st, a, booted, *, silent: bool = False, live_unjudged: str | None = None) -> tuple:
    """MUSIC (PURE, fix1 -- audio-1): judged only when DISCRIMINATING -- A's song read and, in the battle-song lane, the BOOTED
    sample's song read and different from it (the silent lane, ``silent``: the boot plays none). On the sound INSTANCES the
    bookkeeping cannot overwrite (a missing BeforeWorldEvents stop and a double suspend both leave music / suspend_song at A's
    after the restore): the booted sample's dio.suspend_song == A's song (the world song in the slot through the fight: a double
    or a missing suspend reads -1 there; ``silent``: and NOTHING current, music -1); at the return dio.song_sid == A's (A's own
    instance resumed: a restart from the top mints a new one), dio.boot_song_live false (no instance latched at the Leave still
    plays over it), and the bookkeeping A's (music, suspend_song). Otherwise green, 'not discriminating' named.
    [fix3-r2] ``live_unjudged`` (why): the return was read INSIDE a stop fade that a correct return is still sounding, so
    boot_song_live cannot tell a correct return from a song left playing -- that term alone is 'not discriminating' (named, with
    the reading), every other term still judged."""
    ma, mr = music(a), music(st)
    mb = music(booted) if booted is not None else None
    if ma is None or ma < 0:
        return True, f"not discriminating: A plays no song ({ma!r}; the return plays {mr!r})"
    if not silent and (mb is None or mb < 0 or mb == ma):
        return True, f"not discriminating: A's song {ma!r}, the boot's {mb!r} (the return plays {mr!r})"
    sid_a, sid_r, live = _dio(a, "song_sid"), _dio(st, "song_sid"), _dio(st, "boot_song_live")
    slot_b = _dio(booted, "suspend_song") if booted is not None else None
    if sid_a is None or sid_r is None or live is None:
        return False, "absent: no dio.song_sid / boot_song_live (an engine before s145 fix1's music witnesses)"
    booted_ok = slot_b == ma and (mb == -1 if silent else True)
    live_ok = live is False if live_unjudged is None else isinstance(live, bool)
    ok = (booted_ok and isinstance(sid_a, int) and sid_a >= 0 and sid_r == sid_a and live_ok and mr == ma
          and _dio(st, "suspend_song") == _dio(a, "suspend_song"))
    live_txt = (f"{live!r} (want False)" if live_unjudged is None
                else f"{live!r} -- not discriminating: {live_unjudged}")
    return ok, (f"{'the silent lane: ' if silent else ''}song A {ma} / booted {mb} (its slot {slot_b!r}, want A's) / return {mr}; "
                f"instance A {sid_a!r} -> {sid_r!r} (want A's own); a Leave-latched instance still playing {live_txt}; "
                f"suspend_song {_dio(a, 'suspend_song')!r} -> {_dio(st, 'suspend_song')!r}")


def song_quiet(g, st, timeout: float | None = None):
    """(fix2 -- raudio-1's side note) the settled return read PAST the engine's stop fades: a correct return's Leave-latched instance
    stops within its own fade (BeforeWorldEvents' STOPCURRENT on a mid-fight leave: 500 ms; a song the settle shut is never latched
    since fix2), while a battle song LEFT PLAYING never stops -- so ``st`` reading dio.boot_song_live true is re-read on WorldHUD up
    to SONG_FADE_S for the first sample that reads it false (the last one read when it never does: MUSIC then judges the song still
    playing). ``st`` itself when it already reads false or absent, is off the world map, or is None."""
    if st is None or st.ui_state != "WorldHUD" or _dio(st, "boot_song_live") is not True:
        return st
    deadline = time.time() + (SONG_FADE_S if timeout is None else timeout)
    last = st
    while time.time() < deadline:
        s = g.state
        if s is None or s.ui_state != "WorldHUD":
            break
        last = s
        if _dio(s, "boot_song_live") is not True:
            return s
        time.sleep(POLL_S)
    return last


def judge_silent(booted, settled, a) -> tuple:
    """SILENT (PURE, fix1 -- audio-2): the host-silent lane's round trip (`dioboot 359 0 wire silent`): booted from the world WARM,
    back on WorldHUD within RETURN_TOL of A, and :func:`judge_music` in the silent lane."""
    if booted is None or not booted_world(booted):
        return False, "not booted from the world map (the silent boot)"
    if settled is None or settled.ui_state != "WorldHUD":
        return False, f"never back on the world map after the silent boot ({getattr(settled, 'ui_state', None)!r})"
    pa, p = world_xz(a), world_xz(settled)
    d = dist(p, pa) if None not in (p[0], pa[0]) else None
    m_ok, m_why = judge_music(settled, a, booted, silent=True)
    ok = _dio(booted, "boot") == "warm" and d is not None and d <= RETURN_TOL and m_ok
    return ok, (f"boot {_dio(booted, 'boot')!r}; back at {d if d is None else round(d, 2)}u from A; MUSIC {m_why}")


def judge_frozen_back(st, moved, advanced, a, *, whys=("bench",)) -> tuple:
    """FROZEN / the T2 legs' 'still frozen' (PURE): the walk held, freeze.on with a why in ``whys``, edges A's + 1 (the world load's
    rising edge: re-frozen from the first world frame)."""
    w_ok, w_why = cw.judge_walk(moved, advanced, WALK_FRAMES, held=True)
    fz = _w(st, "freeze") or {}
    de = cw._delta(a, st, "freeze.edges")
    ok = w_ok and fz.get("on") is True and fz.get("why") in whys and de == 1
    return ok, f"{w_why}; freeze on {fz.get('on')!r} why {fz.get('why')!r}; edges +{de} since A (want 1)"


def judge_reset(st, before, r0, ok_reset) -> tuple:
    """RESET (PURE): ``reset`` with a world diorama up -> the role released and the return WARM within RETURN_TOL of ``before``."""
    if st is None or not ok_reset:
        return False, "not reached: the boot or the reset failed"
    p, pb_ = world_xz(st), world_xz(before)
    d = dist(p, pb_) if None not in (p[0], pb_[0]) else None
    forced = (st.netsync or {}).get("forced")
    ok = (forced is False and st.ui_state == "WorldHUD" and _dio(st, "returns") == (r0 or 0) + 1
          and _dio(st, "last_return") == "warm" and d is not None and d <= RETURN_TOL)
    return ok, (f"forced {forced!r}; ui {st.ui_state}; dio returns {r0}->{_dio(st, 'returns')!r} last "
                f"{_dio(st, 'last_return')!r}; {d if d is None else round(d, 2)}u from where it booted")


def judge_decline(st0, st, samples, refusal, want_why) -> tuple:
    """VEH / LEVER (PURE): the boot REFUSED (``refusal`` the step's error), nothing booted on any sample, every sample WorldHUD,
    declines +1, durable, decline_why ``want_why`` (the twin's text), and NO reload: the world tick never fell across ``samples``
    from ``st0``."""
    if st is None or st0 is None:
        return False, "not reached: no state around the boot"
    ticks = [_num(_top(s, "ticks")) for s in [st0, *samples, st] if s is not None]
    ticks = [t for t in ticks if t is not None and t >= 0]
    monotonic = len(ticks) >= 2 and all(b >= a_ for a_, b in zip(ticks, ticks[1:])) and ticks[-1] > ticks[0]
    booted = [cb.raw(s).get("frame") for s in [*samples, st] if _d(s, "booted")]
    off = [s.ui_state for s in [*samples, st] if s.ui_state != "WorldHUD"]
    d0, d1 = _dio(st0, "declines"), _dio(st, "declines")
    ok = (refusal is not None and "refused" in refusal and not booted and not off and d0 is not None and d1 == d0 + 1
          and _dio(st, "decline_durable") is True and _dio(st, "decline_why") == want_why and monotonic)
    return ok, (f"refusal {(refusal or 'NONE: it booted')[:90]!r}; booted on {booted[:3] or 'no sample'}; off WorldHUD "
                f"{sorted(set(off)) or 'never'}; declines {d0}->{d1}; durable {_dio(st, 'decline_durable')!r}; why "
                f"{_dio(st, 'decline_why')!r} (want {want_why!r}); ticks {ticks[:1]}..{ticks[-1:]} "
                f"({'monotonic: no reload' if monotonic else 'a RELOAD (or unread)'})")


def judge_cold(booted_st, st, a, probs=None) -> tuple:
    """WC (PURE): THE WARM ROWS CAN FAIL -- the boot read 'cold', the return 'cold' (Main_Init) with world.battle_prob Main_Init's
    own value (fix1: ``probs['init']``, the oracle's -- the positive cold witness), and the warm rows' OWN judges read it RED:
    PLACE (:func:`judge_place`: the Main_Init placement, not A) and MAP (:func:`judge_mapvar`: Main_Init's encounter rate, not
    Main_Reinit's). Where Main_Init put the walker is reported (the stand-in's spawn is the landing), never required."""
    if booted_st is None or st is None:
        return False, "not reached: the cold boot or its return failed"
    p = world_xz(st)
    if p[0] is None:
        return False, f"no world position after the cold return (ui {st.ui_state})"
    if not probs or probs.get("init") is None:
        return False, "no encounter-rate oracle (S145-OR's battle_prob) -- the cold reference unjudged"
    pl_ok, pl_why = judge_place(st, a)
    mv_ok, mv_why = judge_mapvar(st, a, probs)
    ok = (_dio(booted_st, "boot") == "cold" and _dio(st, "last_return") == "cold" and not pl_ok and not mv_ok
          and st.world_mapvar is not None and st.world_battle_prob == probs["init"])
    return ok, (f"boot {_dio(booted_st, 'boot')!r}, last_return {_dio(st, 'last_return')!r}, battle_prob "
                f"{st.world_battle_prob} (want Main_Init's {probs['init']}); PLACE reads it "
                f"{'GREEN (cannot fail)' if pl_ok else 'red'} ({pl_why}); MAP reads it {'GREEN (cannot fail)' if mv_ok else 'red'} "
                f"({mv_why}); {dist(p, FS_LANDING):.1f}u from the landing")


# ---- T2 / duo: the peer's decode of the guest's control frames, the leave's why
#: replay-host's GuestWatch line (coop_peer.control_text + its nonce note): "guest control: menu 2 (root) | fmt-1 report: nonce 5
#: boot LIVE -- names THIS battle (host nonce 5)" -- logged on every CHANGE of the guest's frame
PEER_CTL = re.compile(r"^guest control: menu (\d+) \(([^)]*)\)(?: \| fmt-1 report: nonce (\d+) boot ([A-Z]+))?")
#: replay-host's own line when a tape battle reaches the wire: "tape T: host battle nonce N (map M, pattern P) on the wire"
PEER_NONCE = pb.PEER["tape_nonce"]


def peer_reports(lines, nonce, after=None) -> list:
    """(PURE) ``[(t, menu, boot)]`` of the peer's decoded guest control frames naming ``nonce`` (``lines``: [(t, msg)])."""
    out = []
    for t, msg in lines:
        if after is not None and t < after:
            continue
        m = PEER_CTL.search(msg)
        if m and m.group(3) is not None and int(m.group(3)) == int(nonce):
            out.append((t, int(m.group(1)), m.group(4)))
    return out


def judge_report(reports) -> tuple:
    """(PURE) the guest's report on THIS battle, as the peer decoded it: its FIRST word BOOTING (the LOOSE gMode 3 watches from
    WorldHUD: a guest that reads NONE first -- s144's field-only watching, the strict onWorld -- left the host's start hold
    unarmed at its opening), then LIVE later; never DECLINED (a world refusal reports NONE, never DECLINED: decision 3), and no
    NONE before the LIVE."""
    boots = [b for _t, _m, b in reports]
    live_at = boots.index("LIVE") if "LIVE" in boots else -1
    ok = (bool(boots) and boots[0] == "BOOTING" and live_at > 0 and "DECLINED" not in boots
          and "NONE" not in boots[:live_at])
    return ok, (f"the peer decoded {boots[:8] or 'NO report on this battle'} (want BOOTING first, then LIVE; never DECLINED, "
                "no NONE before the LIVE)")


def judge_play(reports, lines) -> tuple:
    """WB-PLAY / DP (PURE): a control byte 2 (root) or 3 (deep) while LIVE on this battle (``reports``), and the guest's 'ready
    mirror is SERVING' line in ``lines`` (since the boot)."""
    served = [(m, b) for _t, m, b in reports if b == "LIVE" and m in (BW.CTL_ROOT, BW.CTL_DEEP)]
    n = cb.count(lines, "stock menu: the ready mirror is SERVING")
    return bool(served) and n >= 1, (f"menu bytes while LIVE {sorted({m for _t, m, b in reports if b == 'LIVE'})} (want 2 or 3);"
                                     f" the SERVING line {n}x")


def leave_why(samples, lines) -> str | None:
    """(PURE) WHY the booted diorama left: a stall-cap verdict anywhere wins ('stall_cap': the red); else the last
    netsync.diorama.hold.why a sample published; else 'terminal' when the end-leave ran ('diorama END: end-leave attempt'); else
    the watcher line's text (host_world / host_field)."""
    whys = [_d(s, "hold.why") for s in samples if _d(s, "hold.why")]
    msgs = [ln.split("|", 2)[-1].strip() if "|" in ln else ln for ln in lines]
    if "stall_cap" in whys or any(pb.MATCHERS["hold_stall_cap"].search(m) for m in msgs):
        return "stall_cap"
    if whys:
        return whys[-1]
    if any(pb.MATCHERS["end_leave"].search(m) for m in msgs):
        return "terminal"
    for m in msgs:
        hit = pb.MATCHERS["watcher_why"].search(m)
        if hit:
            text = hit.group(1)
            return ("host_world" if text == BW.WATCH_WHY_TEXT_HOST_WORLD else
                    "host_field" if "back on field" in text else text)
    return None


def pre_boot_ticks(samples, a=None):
    """(PURE) the world tick the guest's world map had reached right before its boot: the largest live world.ticks on a sample
    before the first world-booted one (one world visit counts up), else A's -- what a reload's first frame must read below."""
    i0 = next((i for i, s in enumerate(samples) if booted_world(s)), len(samples))
    seen = [t for t in (_num(_top(s, "ticks")) for s in samples[:i0]) if t is not None and t >= 0]
    return max(seen) if seen else (_num(_top(a, "ticks")) if a is not None else None)


def wall_gap_ms(s0, s1) -> int | None:
    """(PURE, fix3-r2) the WALL time from sample ``s0`` to ``s1``, in ms: each one's write time (State.mtime -- the state file's, as
    the agent wrote it) when both are read, else both read times (read_at) -- the clock SaXAudio's fades run on, never a published
    `rt` (the stand-in's is its virtual clock, ~5x the wall). None when either sample is None."""
    if s0 is None or s1 is None:
        return None
    both = s0.mtime is not None and s1.mtime is not None
    t0, t1 = (s0.mtime, s1.mtime) if both else (s0.read_at, s1.read_at)
    return int(round((t1 - t0) * 1000))


def held_live_unjudged(first, settled) -> str | None:
    """(PURE, fix3-r2) THE HELD LEG's MUSIC GUARD: its return is judged on its last RECORDED world-free sample, never re-read (the
    rejoin follows) -- and the rejoin can leave the world map as soon as the return's own gates pass: FollowHostTick runs every
    Update, inside the diorama too (NetSyncClient.cs:1824), and stamps the host's field on first sight (:3714-3718), so
    FollowStableMs' 1200 ms debounce (:3720) is already spent when the guest is back; ServiceIntentFollow (:1820) has none. A
    correct return's Leave-latched battle song still sounds through BeforeWorldEvents' STOPCURRENT fade (STOPCURRENT_FADE_MS, on
    the wall, from before the first world sample): read inside it, dio.boot_song_live is True for a correct return and for a song
    LEFT playing alike. The reason that term is not discriminating, or None when the judged sample is that far past the first."""
    gap = wall_gap_ms(first, settled)
    if gap is not None and gap >= STOPCURRENT_FADE_MS:
        return None
    return (f"the rejoin left the world map inside BeforeWorldEvents' {STOPCURRENT_FADE_MS} ms fade "
            f"({'unread' if gap is None else f'{gap} ms'} past the first world sample)")


def judge_guest_return(first, settled, a, r0, d0, why, whys, moved, advanced, samples, *, keys_only: bool = False,
                       pre_ticks=None, probs=None, booted=None) -> tuple:
    """WB-RET / HF-RET / DR (PURE): the leave ``why`` in ``whys`` (never stall_cap); ``first`` (the first world sample after the
    boot) counts the return warm on its own load (dio.returns ``r0`` + 1, last_return 'warm', last_world WORLD, diorama.returns
    ``d0`` + 1) with the world tick restarted below ``pre_ticks`` (:func:`pre_boot_ticks`; None = A's); ``settled`` within
    RETURN_TOL of A; still frozen ('live' / 'mirroring': the walk witness -- or, ``keys_only`` (the held leg, whose rejoin follows:
    no walk there), freeze.on on ``settled``); never FieldHUD across ``samples``. [fix1] ...and the witnesses the engine does not
    compute, on ``settled``: world.battle_prob Main_Reinit's (``probs``, the oracle's: position-free -- on HF-RET, where A is the
    landing and the cold spawn alike, the one that tells warm from cold), the MAP digest A's and the camera A's
    (:func:`judge_camera`), and :func:`judge_music` over A, ``booted`` (the world-booted sample) and the return -- [fix3-r2]
    ``keys_only``: its boot_song_live term judged only when ``settled`` is STOPCURRENT_FADE_MS past ``first`` on the wall
    (:func:`held_live_unjudged`), else named not discriminating (the instance, the slot and the bookkeeping still judged)."""
    if first is None or settled is None:
        return False, f"never back on the world map after a boot (the leave why {why!r})"
    field = [(cb.raw(s).get("frame"), s.field_id) for s in samples if s.ui_state == "FieldHUD"]
    pa, p = world_xz(a), world_xz(settled)
    d = dist(p, pa) if None not in (p[0], pa[0]) else None
    t1 = _num(_top(first, "ticks"))
    ta = pre_ticks if pre_ticks is not None else _num(_top(a, "ticks"))
    reloaded = t1 is not None and ta is not None and 0 <= t1 < ta
    if keys_only:                                          # (no walk: the edge counter moves on a HELD dispatch -- a press)
        fz = _w(settled, "freeze") or {}
        f_ok = fz.get("on") is True and fz.get("why") in ("live", "mirroring")
        f_why = f"(the claim alone: the rejoin follows) freeze on {fz.get('on')!r} why {fz.get('why')!r}"
    else:
        f_ok, f_why = judge_frozen_back(settled, moved, advanced, a, whys=("live", "mirroring"))
    p_ok = bool(probs) and probs.get("reinit") is not None and settled.world_battle_prob == probs["reinit"]
    mv_ok = settled.world_mapvar is not None and settled.world_mapvar == a.world_mapvar
    c_ok, c_why = judge_camera(settled, a)
    m_ok, m_why = judge_music(settled, a, booted, live_unjudged=held_live_unjudged(first, settled) if keys_only else None)
    ok = (why in whys and _dio(first, "returns") == (r0 or 0) + 1 and _dio(first, "last_return") == "warm"
          and _dio(first, "last_world") == WORLD and _d(first, "returns") == (d0 or 0) + 1 and reloaded
          and d is not None and d <= RETURN_TOL and f_ok and not field and p_ok and mv_ok and c_ok and m_ok)
    want_p = (probs or {}).get("reinit")
    return ok, (f"left on {why!r} (want one of {list(whys)}); first world sample: dio returns {r0}->{_dio(first, 'returns')!r} "
                f"last {_dio(first, 'last_return')!r} on {_dio(first, 'last_world')!r}, diorama returns {d0}->"
                f"{_d(first, 'returns')!r}; ticks {ta}->{t1} ({'reloaded' if reloaded else 'NO reload'}); "
                f"{d if d is None else round(d, 2)}u from A; FieldHUD {field[:3] or 'never'}; STILL FROZEN {f_why}; battle_prob "
                f"{a.world_battle_prob}->{settled.world_battle_prob} (want Main_Reinit's {want_p if want_p is not None else '-- NO ORACLE'})"
                f"; MAP digest {'= A' if mv_ok else 'NOT A'}; CAM {c_why}; MUSIC {m_why}")


#: [fix3] the stage scenes a world-map sample never shows: a boot's swirl (SwirlScene) or its battle (BattleMap, BattleMapDebug) --
#: the published `scene` (HarnessAgent: SceneDirector's loaded level), a witness netsync does not compute
OFF_WORLD_SCENES = ("SwirlScene", "BattleMap", "BattleMapDebug")


def off_world(s) -> str | None:
    """(PURE, fix3) why the sample is NOT on the live world map, on witnesses the engine does not compute beside its `booted` claim
    (None when it is): ui_state not WorldHUD (UIManager.State); or the stage scene a swirl / battle -- a world boot's swirl writes
    no UIManager.State (SceneDirector._Swirl, UIManager's SwirlScene branch), so its samples read WorldHUD; or world.ticks -1 --
    HarnessAgent's live gate (WorldMap not the loaded level). An unread tick (None: an engine before the witnesses) is no verdict."""
    if s.ui_state != "WorldHUD":
        return f"FieldHUD {s.field_id}" if s.ui_state == "FieldHUD" else str(s.ui_state)
    if s.scene in OFF_WORLD_SCENES:
        return f"WorldHUD on {s.scene}"
    t = _num(_top(s, "ticks"))
    if t is not None and t < 0:
        return "WorldHUD, the WorldMap level gone (ticks -1)"
    return None


def rejoin_load(s) -> bool:
    """(PURE, fix3) a world -> field load's own sample: still WorldHUD (only the FieldMap level branch writes FieldHUD), the stage no
    swirl or battle, the WorldMap level gone (world.ticks -1), nothing booted."""
    t = _num(_top(s, "ticks"))
    return (s.ui_state == "WorldHUD" and s.scene not in OFF_WORLD_SCENES and t is not None and t < 0
            and not _d(s, "booted"))


def decline_window(stamped, bt, enter, now=None, *, field: int = ICE_CAVERN, not_before=None) -> tuple:
    """(PURE, fix3) WD-DECL's judged window, ``(samples, rejoined)``, over the guest's ``stamped`` [(ts, state)] from the host's
    battle on the wire (``bt``). With the host's entry into ``field`` ANCHORED (``enter``: the peer's own ms-stamped line) the
    window is [bt, enter] UNCUT -- the follow starts only once the host's field has held FollowStableMs (1200 ms) and faded, so no
    rejoin can land inside it: a FieldHUD there is the guest LEAVING the world map before the host's entry (decision 3: a declined
    guest stays frozen), judged red. With NO anchor (the instrument missed that line) the window runs to ``now`` and is cut at the
    first FieldHUD on ``field`` -- the follow's own target, the only FieldHUD that can be the rejoin (``rejoined``: the judge spares
    that load's own trailing samples); a FieldHUD on any other field stays in the judged window. [fix3-r2] ONE UNBENCHED CAVEAT: the
    serial follow waits FollowStableMs, but the host's gMode-3 MAPJUMP also emits a transition intent naming 300 before its own
    load (EventEngine.DoEventCode.cs:1040), and ServiceIntentFollow (NetSyncClient.cs:5351, no debounce) fires the world rejoin
    on it -- a guest that loads 300 faster than the host's field reaches the wire would read red here (never a false green;
    the peer logs no intent line to end the window on). [fix3b] ``not_before`` (the host's fight end on the wire): unanchored, a
    FieldHUD on ``field`` BEFORE it is no rejoin -- the host is still fighting -- and stays in the judged window (red)."""
    end = enter if enter is not None else now
    stamped = [(ts, s) for ts, s in stamped if ts >= bt and (end is None or ts <= end)]
    since = [s for _, s in stamped]
    if enter is not None:
        return since, False
    cut = next((i for i, (ts, s) in enumerate(stamped) if s.ui_state == "FieldHUD" and s.field_id == field
                and (not_before is None or ts >= not_before)), None)
    return (since, False) if cut is None else (since[:cut], True)


def boot_witnessed(s) -> bool:
    """(PURE, fix3) the sample shows a boot under way: netsync's claim (`netsync.diorama.booted`) or a witness it does not compute --
    the battle HUD, a swirl or battle stage (:data:`OFF_WORLD_SCENES`)."""
    return s is not None and (bool(_d(s, "booted")) or s.ui_state == "BattleHUD" or s.scene in OFF_WORLD_SCENES)


def aboard_refusal_instrument(anchored: bool, st) -> bool:
    """(PURE, fix3) a `vehicle 1` that RAISED is the instrument's -- the host's battle beat the boarding and the on-foot guest is
    booting it (Session.vehicle refuses off WorldHUD) -- only when that battle is anchored on the wire AND the state read right
    after the refusal shows the boot (:func:`boot_witnessed`); any other refusal (a read-back timeout, the engine's own) is the
    engine's row ('`vehicle 1` refused')."""
    return bool(anchored) and boot_witnessed(st)


def judge_watch_decline(st0, samples, reports, lines, nonce, want_why, *, rejoined: bool = False) -> tuple:
    """WD-DECL (PURE, fix1): THE WATCHER's DURABLE DECLINE on a real wire (decisions 3 + 4) -- over the guest's ``samples`` through
    the host's battle (``st0`` the state before it; :func:`decline_window` cuts them): the peer's ``reports`` on ``nonce`` all NONE
    (never BOOTING, never DECLINED: watching false keeps the digit panel's slots), dio.visit_decline ``want_why`` (the twin's vehicle
    line) on a sample, dio.declines +1 EXACTLY, durable, nothing booted on any sample, world.ticks monotonic (no reload), and
    ``lines`` (the guest's, since the battle) the 'diorama declined on world map' line for this nonce exactly once. fix2, fix3: and
    EVERY sample ON THE LIVE WORLD MAP (:func:`off_world`: ui_state, the stage scene, the world tick -- witnesses the engine does not
    compute, beside its `booted` claim; a boot still up at the window's end leaves only pre-boot world ticks, which read
    monotonic, and a boot still in its SWIRL reads WorldHUD with ticks -1). A FieldHUD inside the window is the guest LEAVING the
    world map (its field named). ``rejoined``: the window was cut at the rejoin's FieldHUD (no entry anchor), so a TRAILING run of
    that load's own samples (:func:`rejoin_load`) is spared -- never a swirl, a battle, a booted or a mid-window sample."""
    if st0 is None or not samples:
        return False, "not reached: no samples through the host's battle"
    last = samples[-1]
    judged = list(samples)
    if rejoined:
        while judged and rejoin_load(judged[-1]):
            judged.pop()
    off = [(cb.raw(s).get("frame"), w) for s in judged if (w := off_world(s)) is not None]
    left = sorted({s.field_id for s in judged if s.ui_state == "FieldHUD"})
    left_txt = f"; LEFT the world map before the host's entry: field {left}" if left else ""
    boots = [b for _t, _m, b in reports]
    visit = sorted({_dio(s, "visit_decline") for s in samples} - {None, ""})
    d0, d1 = _dio(st0, "declines"), _dio(last, "declines")
    booted = [cb.raw(s).get("frame") for s in samples if _d(s, "booted")]
    ticks = [t for t in (_num(_top(s, "ticks")) for s in [st0, *samples]) if t is not None and t >= 0]
    monotonic = len(ticks) >= 2 and all(b >= a_ for a_, b in zip(ticks, ticks[1:]))
    n = cb.count(lines, BW.log_world_declined(WORLD, want_why, nonce))
    ok = (bool(boots) and all(b == "NONE" for b in boots) and want_why in visit and d0 is not None and d1 == d0 + 1
          and _dio(last, "decline_durable") is True and not booted and not off and monotonic and n == 1)
    return ok, (f"the peer decoded {boots[:8] or 'NO report on this battle'} (want NONE only); visit_decline {visit[:2] or 'never'} "
                f"(want {want_why!r}); declines {d0}->{d1} (want +1), durable {_dio(last, 'decline_durable')!r}; booted on "
                f"{booted[:3] or 'no sample'}; off the world map on {off[:3] or 'no sample'}{left_txt}; ticks "
                f"{ticks[:1]}..{ticks[-1:]} ({'monotonic' if monotonic else 'a RELOAD'}); the declined line {n}x (want 1)")


def boot_window(samples) -> list:
    """(PURE) the samples of a BOOT's judgement: from the first up to the diorama's last booted one (its return is RET's: a return
    that lands on a field reds RET, never BOOT); every sample when nothing booted."""
    last = max((i for i, s in enumerate(samples) if _d(s, "booted")), default=None)
    return list(samples) if last is None else list(samples[:last + 1])


def judge_guest_boot(samples, booted_st, reports, lines, nonce) -> tuple:
    """WB-BOOT / HF-BOOT / DB's guest half (PURE): ``samples`` (from the battle on the wire to the diorama's end) never FieldHUD;
    ``booted_st`` the world diorama (booted_world, boot_world WORLD, boot 'warm'); the peer's ``reports`` BOOTING then LIVE; the
    guest's 'diorama LIVE ... (host battle nonce N, booted from wire nonce N)' line in ``lines``."""
    field = [(cb.raw(s).get("frame"), s.field_id) for s in samples if s.ui_state == "FieldHUD"]
    claim = (booted_st is not None and booted_world(booted_st) and _dio(booted_st, "boot_world") == WORLD
             and _dio(booted_st, "boot") == "warm")
    r_ok, r_why = judge_report(reports) if reports is not None else (True, "the report judged on the host (the duo)")
    live = [m for m in (ln.split("|", 2)[-1].strip() if "|" in ln else ln for ln in lines)
            if (h := pb.MATCHERS["live"].search(m)) and h.group(2) == h.group(3)
            and (nonce is None or h.group(2) == str(nonce))]
    uis = sorted({s.ui_state for s in samples})
    ok = not field and claim and r_ok and bool(live)
    return ok, (f"ui over {len(samples)} sample(s) {uis}; FieldHUD {field[:3] or 'never'}; the world diorama "
                f"{'booted warm on ' + str(_dio(booted_st, 'boot_world')) if claim else 'NEVER booted (it stayed on the world map)'};"
                f" {r_why}; 'diorama LIVE' on nonce {nonce} {len(live)}x")


def judge_rejoin_300(samples, after_ret, lines, *, field: int = ICE_CAVERN) -> tuple:
    """WB-300 / D3's tail (PURE): a FieldHUD ``field`` sample, rejoin.lands +1 since ``after_ret`` (the state after the world
    return) and the landed line; NO second return: netsync.diorama.returns and dio.returns as ``after_ret``, last_return_field
    never ``field``."""
    on = [s for s in samples if s.ui_state == "FieldHUD" and s.field_id == field]
    if not on:
        return False, f"never on FieldHUD {field} ({sorted({(s.ui_state, s.field_id) for s in samples})[:4]})"
    last = on[-1]
    dl = cw._delta(after_ret, last, "rejoin.lands")
    n = cb.count(lines, f"world rejoin landed on field {field}")
    r0, r1 = _d(after_ret, "returns"), _d(last, "returns")
    w0, w1 = _dio(after_ret, "returns"), _dio(last, "returns")
    lrf = [_d(s, "last_return_field") for s in on]
    ok = (dl or 0) >= 1 and n >= 1 and r1 == r0 and w1 == w0 and field not in lrf
    return ok, (f"FieldHUD {field} on {len(on)} sample(s); lands +{dl}; the landed line {n}x; diorama returns {r0}->{r1}, "
                f"dio returns {w0}->{w1} (want unmoved: no second return counted here); last_return_field {sorted(set(lrf))}")


#: the start hold's per-reason release counters (`netsync.battle.host.start_hold.released`, monotonic per process: read as DELTAS)
HOLD_RELEASE_KEYS = ("live", "declined", "link", "oldguest", "cap", "ended")
#: [fix3] the report words that release a held hold 'declined' (StartHoldStep: NONE / DECLINED / BUSY) -- between the first BOOTING
#: and the first LIVE they mean the hold let go, or (before the opening) unprimed it: the late arm's lane (judge_report's rule)
HOLD_BREAK_WORDS = ("none", "declined", "busy")


def _hold(x, key):
    """A ``netsync.battle.host.start_hold`` leaf (None on no sample)."""
    return cb.path(x, "netsync.battle.host.start_hold." + key) if x is not None else None


def _count(v):
    """An int counter as published (a bool, a missing key or a non-int is unread: None)."""
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def hold_released(x) -> dict | None:
    """(PURE) ``start_hold.released`` as ints, None when unread (no sample, no block, a non-int counter)."""
    r = cb.path(x, "netsync.battle.host.start_hold.released") if x is not None else None
    if not isinstance(r, dict) or not all(isinstance(r.get(k), int) and not isinstance(r.get(k), bool) for k in HOLD_RELEASE_KEYS):
        return None
    return {k: int(r[k]) for k in HOLD_RELEASE_KEYS}


def judge_host_hold(host_samples, nonce=None, *, before=None, after=None) -> tuple:
    """DB's host half (PURE): the host's start hold read the guest's report on ITS OWN battle (start_hold.guest.nonce ==
    start_hold.nonce) BOOTING FIRST, then LIVE on a later sample, with no NONE / DECLINED / BUSY between them (judge_report's rule,
    on the host's own decode) -- AND (fix2, fix3) the hold's OWN verdict, read on ``after`` (the host's state after the fight; the
    last sample when None) against ``before`` (read before its battle verb). Its two halves see different things:
      * THE OPENING's DECISION is start_hold.why -- 'booting' (armed at the command phase's opening), 'late' (not armed there: a
        BOOTING within LateArmMs armed it late, late_ms its offset) or the not-armed reason ('live': the guest was LIVE before the
        host's opening, 'none', 'declined', 'busy', ...) -- which the engine keeps, with release and late_ms, until its NEXT own
        battle starts (NetSyncBattle.NoteOwnBattleStart): required 'booting', release 'live', late_ms -1;
      * THE RELEASES are the per-reason counters (monotonic per process: DELTAS), which count every release between the verb and
        the end of the fight but never say how the hold was ARMED -- a late arm released by LIVE reads live +1 exactly as an
        on-time one: required live +1 and every other reason +0; with start_hold.count (holds armed) +1 and party.battle_no
        (``battle.epoch``, the stock counter netsync does not compute) +1 -- exactly ONE own battle in the window, since a second
        battle whose hold never armed adds no release at all.
    The host's samples start once its battle verb returns (the battle up, its units listed) -- usually INSIDE the intro, before
    the opening: the end-state read, not the samples, carries the opening's decision."""
    seq = []
    for s in host_samples:
        hn, gn = cb.path(s, "netsync.battle.host.start_hold.nonce"), cb.path(s, "netsync.battle.host.start_hold.guest.nonce")
        b = cb.path(s, "netsync.battle.host.start_hold.guest.boot_name")
        if isinstance(hn, int) and hn >= 0 and gn == hn and (nonce is None or hn == nonce) and b:
            if not seq or seq[-1] != b:
                seq.append(b)
    live_at = seq.index("live") if "live" in seq else -1
    broke = [b for b in seq[1:live_at] if b in HOLD_BREAK_WORDS] if live_at > 0 else []
    seq_ok = bool(seq) and seq[0] == "booting" and live_at > 0 and not broke
    end = after if after is not None else (host_samples[-1] if host_samples else None)
    why, release, late = _hold(end, "why"), _hold(end, "release"), _hold(end, "late_ms")
    dec_ok = why == "booting" and release == "live" and late == -1
    r0, r1 = hold_released(before), hold_released(end)
    delta = None if r0 is None or r1 is None else {k: r1[k] - r0[k] for k in HOLD_RELEASE_KEYS}
    rel_ok = delta is not None and delta["live"] == 1 and all(delta[k] == 0 for k in HOLD_RELEASE_KEYS if k != "live")
    c0, c1 = _count(_hold(before, "count")), _count(_hold(end, "count"))
    armed = None if c0 is None or c1 is None else c1 - c0
    e0, e1 = (_count(cb.path(x, "battle.epoch")) if x is not None else None for x in (before, end))
    battles = None if e0 is None or e1 is None or e0 < 0 or e1 < 0 else e1 - e0
    rel = (" ".join(f"{k} +{v}" for k, v in delta.items()) if delta is not None
           else "UNREAD (no start_hold.released before / after the battle)")
    note = (" -- the guest was LIVE before the host's opening: a timing red on hardware, the hold never armed" if why == "live"
            else f" -- armed LATE, +{late} ms after the opening" if why == "late" else "")
    ok = seq_ok and dec_ok and rel_ok and armed == 1 and battles == 1
    return ok, (f"the host's start hold read the guest {seq[:8] or 'NEVER on its own nonce'} (want booting first, then live, no "
                f"none / declined / busy between{'; broke on ' + str(broke) if broke else ''}); the opening's decision why {why!r} "
                f"release {release!r} late_ms {late!r} (want 'booting' / 'live' / -1{note}); released {rel} (want live +1, every "
                f"other +0); holds armed +{armed if armed is not None else ' UNREAD'} (want 1); own battles "
                f"+{battles if battles is not None else ' UNREAD'} (want 1)")


def judge_host_menu(host_samples) -> tuple:
    """DP's host half (PURE): the host decoded the guest's control byte 2 (root) or 3 (deep) on its own battle
    (``host.wait.menu``)."""
    seen = sorted({_num(cb.path(s, "netsync.battle.host.wait.menu")) for s in host_samples} - {None})
    return any(m in (BW.CTL_ROOT, BW.CTL_DEEP) for m in seen), f"host.wait.menu read {seen} (want 2 or 3)"


# ================================================================================================ the moves
class SwirlHang(HarnessError):
    """THE INSTRUMENT (decision 11): a game went quiet on SwirlScene -- the leg stops, its rows 'not reached', never a verdict."""


def _state_every(g, frames: int) -> None:
    """`stateevery N` (Session.state_every), best effort -- a refusal is a note, and NEVER a raise: a game already quiet on
    SwirlScene takes no step (the hang check that follows names it)."""
    try:
        g.state_every(frames)
    except (HarnessError, AttributeError) as err:
        _note(g, f"stateevery {frames} refused: {str(err)[:120]}")


def _note(g, text: str) -> None:
    """``g.note``, never raising: a hung game takes no `note` step (SWIRL-HANG) -- the run's own log keeps it then."""
    try:
        g.note(text)
    except HarnessError:
        try:
            g._log(f"note (the game took no step): {text[:600]}")
        except Exception:                                 # noqa: BLE001 - bookkeeping never breaks the run
            pass


def _run_dir(g) -> Path:
    return Path(getattr(g, "scenario_dir", None) or g.run_dir)


def grab_frame(g, path: Path) -> tuple:
    """tools/game_snap.ps1 on THIS session's game (``-Id`` its pid when known: with two FF9s up, never the first one found):
    (path | None, why). A SEAM -- the tests stub it (no window there)."""
    args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(cb.REPO / "tools" / "game_snap.ps1"),
            "-OutPath", str(path)]
    try:
        pid = getattr(g, "pid", None)
    except Exception:                                     # noqa: BLE001 - a pid probe never kills the archive
        pid = None
    if pid:
        args += ["-Id", str(int(pid))]
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=45)
    except (OSError, subprocess.TimeoutExpired) as err:
        return None, f"game_snap failed: {type(err).__name__}: {str(err)[:160]}"
    if out.returncode == 0 and Path(path).is_file():
        return Path(path), "grabbed"
    return None, f"game_snap exit {out.returncode}: {((out.stderr or '') + (out.stdout or ''))[-200:]}"


def archive_hang(g, tag: str) -> str:
    """THE SWIRL-HANG ARCHIVE, NOW (the install is shared; the session's teardown kills the game): Memoria.log and Unity's
    output_log.txt into the run dir, and one frame of the window."""
    notes = [f"Memoria.log -> {cb.archive_log(g, tag)}"]
    try:
        src = g.unity_log()
        if src is not None and Path(src).is_file():
            dest = _run_dir(g) / f"output_log-{tag}.txt"
            shutil.copy2(src, dest)
            notes.append(f"output_log.txt -> {dest}")
        else:
            notes.append("output_log.txt: none written")
    except (OSError, AttributeError) as err:
        notes.append(f"output_log.txt archive failed: {err}")
    shot, why = grab_frame(g, _run_dir(g) / f"{tag}.png")
    notes.append(f"frame -> {shot if shot is not None else why}")
    return "; ".join(notes)


def hang_check(g, where: str) -> None:
    """After a wait that did not see what it waited for (or raised): is the game QUIET ON SwirlScene? Then raise SwirlHang (the
    instrument), the archive's trail in its text; otherwise return (the caller's row says what it missed)."""
    try:
        st = g.state
    except HarnessError:
        return
    if is_swirl_hang(st.scene, st.age):
        raise SwirlHang(f"SWIRL-HANG at {where}: the game went quiet on SwirlScene (last frame {st.frame}, {st.age:.1f} s "
                        f"silent) -- {archive_hang(g, 'swirl-hang')}")


def world_boot(g, *, scene: int = DIO_SCENE, where: str = "the boot", silent: bool = False) -> tuple:
    """`netsync dioboot <scene> 0 wire` from WorldHUD, the state written every frame around it: ``(booted | None, samples,
    refusal | None, mark)`` -- ``booted`` the first world-booted sample (:func:`booted_world`), ``samples`` every publish from the
    verb, ``refusal`` the step's error (a driver that refuses before the step, or the engine's pre-Arm verdict). A boot that never
    comes up with the game quiet on SwirlScene raises SwirlHang. [fix1] ``silent`` adds the `silent` token: the wire bench's
    host-silent song (0xFFFE)."""
    at = cb.mark(g)
    _state_every(g, 1)
    hung = False
    try:
        try:
            g.netsync("dioboot", scene, DIO_PATTERN, "wire", *(("silent",) if silent else ()))
        except HarnessError as err:
            try:
                hang_check(g, where)
            except SwirlHang:
                hung = True
                raise
            return None, [], str(err)[:400], at
        samples, hit = cb.watch(g, booted_world, BOOT_S)
        if hit is None:
            try:
                hang_check(g, where)
            except SwirlHang:
                hung = True
                raise
        return hit, samples, None, at
    finally:
        if not hung:
            _state_every(g, 2)


def world_leave(g, *, where: str = "the leave") -> tuple:
    """`netsync dioleave` (request-only: the boot's swirl defers it -- retried) and every publish to the FIRST world frame, then
    the settle: ``(first | None, settled | None, samples, mark, why)``."""
    at = cb.mark(g)
    for attempt in range(8):
        ok, why = cb.try_ns(g, "dioleave")
        if ok or "no diorama is booted" in why:
            break
        if "deferred" not in why or attempt == 7:
            return None, None, [], at, f"dioleave refused: {why}"
        g.wait_frames(30)

    def first_world(s):
        t = _num(_top(s, "ticks"))
        return s.ui_state == "WorldHUD" and not _d(s, "booted") and world_xz(s)[0] is not None and (t is None or t >= 0)
    samples, first = cb.watch(g, first_world, LEAVE_S)
    if first is None:
        hang_check(g, where)
        return None, None, samples, at, f"never back on the world map ({g.state.ui_state!r}, field {g.state.field_id})"
    settled = cb.poll(g, lambda s: on_world_free(s) and s.control and not s.fading, SETTLE_S, "the walker after the return")
    if settled is not None:
        settled = song_quiet(g, g.world_settle())       # [fix2] MUSIC read past the stop fades
    return first, settled, samples, at, ""


# ================================================================================================ the run
def run(g, field: int | None = None):
    leg = LEG
    if leg is None:
        led = cb.Ledger(g, {"T2-TAPE": T2_COMMON["T2-TAPE"]})
        led.check("T2-TAPE", False, f"COOP_WB_LEG={_RAW_LEG!r} is no leg: one of {LEGS}")
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
    led = cb.Ledger(g, solo_catalog(calibrate), finals=("S145-R", "S145-SWIRL", "S145-CAL"))
    ctx = {"calibrate": calibrate, "stage": None, "a": None, "arr": None, "lever_row": False, "hung": None}
    try:
        _solo(g, led, ctx)
    except SwirlHang as err:
        ctx["hung"] = str(err)
        _note(g, str(err)[:600])
        led.close(f"SWIRL-HANG -- the instrument (the runner retries this leg once): {str(err)[:200]}")
    except HarnessError as err:
        _note(g, f"the solo leg raised: {str(err)[:400]}")
        led.close(f"the leg raised ({str(err)[:200]})")
    finally:
        _note(g, f"Memoria.log archived: {cb.archive_log(g, 'world-battle-solo')}")
        if ctx["hung"] is None:
            led.close()
            _release_solo(g, led, ctx)
        else:
            led.check("S145-R", False, "not reached: SWIRL-HANG (the game is hung: no `reset` is sent; the session kills it)")
        led.check("S145-SWIRL", ctx["hung"] is None, ctx["hung"] or "no boot or battle start hung in the swirl")
        if calibrate:
            stage = ctx.get("stage")
            if ctx["hung"] is not None:
                led.check("S145-CAL", False, "not reached: SWIRL-HANG -- the instrument; retry the leg")
            elif stage is None:
                led.check("S145-CAL", False, "no engine stage was read (the run died before P0)")
            else:
                led.judge_calibration("S145-CAL", OLD_PREDICTED if stage < 145 else LEVER_PREDICTED)
        led.close(final=True)


def _ini_ok(g) -> tuple:
    return cw._ini_ok(g)


def _solo(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why = _ini_ok(g)
    led.check("S145-INI", ok, why)
    if not ok:
        led.close("the install's ini refuses the bench (S145-INI)")
        return
    oracle = read_oracle(Path(g.game_path))
    ctx["probs"] = oracle["facts"].get("battle_prob")      # [fix1] the encounter-rate oracle: MAP / WC judge battle_prob by value
    led.check("S145-OR", not oracle["problems"], f"problems {oracle['problems'] or 'none'}; read {oracle['facts']}")
    ok, why = cb.setup(g, FARSHORE, label="s145: world-map co-op, battles from the world map -- the solo bench"
                                          + (" -- CALIBRATION" if ctx["calibrate"] else ""))
    led.check("S145-S0", ok and g.state.field_id == FARSHORE, why + f"; on field {g.state.field_id}")
    if not ok:
        led.close(f"the selftest role never came up -- {why}")
        return
    st = g.state
    ctx["stage"] = stage_of(st)
    g.note(f"engine stage: s{ctx['stage']} ({cb.stage_note(st)})")
    led.check("S145-P0", *judge_probe(st, cb.log_lines(g)))
    _p1(g, led, ctx)
    ok, why, arr = cw.walk_out(g)
    led.check("S145-ROUTE", ok, why)
    if not ok:
        led.unreached(("S145-A",) + WORLD_ROWS, f"the walk out never landed on world {WORLD} (ROUTE): {why[:160]}")
        return
    ctx["arr"] = arr
    if not _snapshot_a(g, led, ctx):
        led.unreached(WORLD_ROWS, "the instrument (S145-A) failed: the warm witnesses could not discriminate")
        return
    try:
        _leg_round_trip(g, led, ctx)
    except SwirlHang:
        raise
    except HarnessError as err:
        led.unreached(("S145-BOOT", "S145-AUDIO", "S145-RET") + RETURN_ROWS, f"the round trip raised: {str(err)[:200]}")
    for row, fn in (("S145-SILENT", _leg_silent), ("S145-RESET", _leg_reset), ("S145-VEH", _leg_vehicle),
                    ("S145-LEVER", _leg_lever), ("S145-WC", _leg_cold)):
        try:
            fn(g, led, ctx)
        except SwirlHang:
            raise
        except HarnessError as err:
            led.check(row, False, f"not reached: {str(err)[:300]}")


def _p1(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why = cb.try_ns(g, "bench", 0)
    st = cb.poll(g, lambda s: (s.netsync or {}).get("bench") is False, 3.0, "the field-gate bench off") or g.state
    if not ok:
        led.check("S145-P1", False, f"`netsync bench 0` refused: {why}")
        return
    if ctx["calibrate"] and (ctx["stage"] or 0) >= 145:
        at = cb.mark(g)
        okl, whyl = cb.try_ns(g, "bench", "worldwarm", "off")
        lines = cb.wait_log(g, at, BW.LOG_WORLD_WARM_OFF, 2.0)
        st = cb.poll(g, lambda s: _dio(s, "lever") == "off", 3.0, "the lever") or g.state
        r_ok, r_why = judge_rest(st, pulled=True, lines=lines)
        led.check("S145-P1", okl and r_ok, whyl or r_why)
        g.note("CALIBRATION: `bench worldwarm off` pulled -- every world boot declines; re-pulled after every release until LEVER")
        return
    if ctx["calibrate"]:
        g.note(f"CALIBRATION on s{ctx['stage']}: no `{PROBE}` -- `bench worldwarm`, `vehicle` and a world `dioboot` are NEVER "
               "sent (the driver refuses them: an s144 agent reads `bench worldwarm` as `bench 1`)")
    led.check("S145-P1", *judge_rest(st, pulled=False))


def _snapshot_a(g, led: cb.Ledger, ctx: dict) -> bool:
    """A: unfrozen, walk off the landing and turn the camera; then `bench 1` and the frozen witness; A = the settled state."""
    away = None
    try:
        st = g.world_settle()
        for _i in range(WALK_OFF_TRIES):
            _moved, _adv, st = cw.hold_walk(g, WALK_OFF_FRAMES)
            p = world_xz(st)
            away = dist(p, FS_LANDING) if p[0] is not None else None
            if away is not None and away >= A_AWAY_MIN:
                break
        g.send(f"hold leftbumper {CAM_FRAMES}", f"wait {CAM_FRAMES + 6}")
        g.wait_frames(10)
        ok, why = cb.try_ns(g, "bench", 1)
        if not ok:
            led.check("S145-A", False, f"`netsync bench 1` refused: {why}")
            return False
        cb.poll(g, lambda s: _w(s, "freeze.on") is True, 3.0, "the freeze")
        moved, adv, a = cw.hold_walk(g, WALK_FRAMES)
    except HarnessError as err:
        led.check("S145-A", False, f"not reached: {str(err)[:300]}")
        return False
    p = world_xz(a)
    away = dist(p, FS_LANDING) if p[0] is not None else away
    ok, why = judge_a(ctx["arr"], a, away, moved, adv)
    led.check("S145-A", ok, why)
    ctx["a"] = a
    return ok


def _leg_round_trip(g, led: cb.Ledger, ctx: dict) -> None:
    """BOOT -> AUDIO -> RET -> the return's witnesses (PLACE, CAM, MAP, MODE, MUSIC, FROZEN)."""
    a = ctx["a"]
    pre = g.state
    pre_ticks = _num(_top(pre, "ticks"))
    r0, d0 = _dio(pre, "returns"), _d(pre, "returns")
    booted, samples, refusal, at = world_boot(g, where="the BOOT row")
    if booted is None:
        led.check("S145-BOOT", False, (f"the boot was refused: {refusal}" if refusal else
                                       f"the diorama never came up from the world map within {BOOT_S:g} s (ui "
                                       f"{g.state.ui_state!r}, dio {_dio(g.state, 'booted_world')!r})"))
        led.check("S145-AUDIO", *judge_audio(False, ()))
        led.unreached(("S145-RET",) + RETURN_ROWS, "no world boot (BOOT)")
        if _d(g.state, "booted"):
            world_leave(g)
        return
    lines = cb.new(g, at)
    led.check("S145-BOOT", *judge_boot(booted, samples, lines, a))
    first, settled, lsamples, lat, why = world_leave(g, where="the RET leave")
    led.check("S145-AUDIO", *judge_audio(True, cb.new(g, at)))
    if first is None or settled is None:
        led.check("S145-RET", False, why or "never settled on the world map after the return")
        led.unreached(RETURN_ROWS, "no warm world return to judge (RET)")
        return
    led.check("S145-RET", *judge_return(first, settled, pre_ticks, r0, d0, cb.new(g, lat), lsamples))
    if settled.ui_state != "WorldHUD":
        led.unreached(RETURN_ROWS, f"the return landed on {settled.ui_state} (RET)")
        return
    led.check("S145-PLACE", *judge_place(settled, a))
    led.check("S145-CAM", *judge_camera(settled, a))
    led.check("S145-MAP", *judge_mapvar(settled, a, ctx.get("probs")))
    led.check("S145-MODE", *judge_mode(settled, a))
    led.check("S145-MUSIC", *judge_music(settled, a, booted))
    try:
        moved, adv, st = cw.hold_walk(g, WALK_FRAMES)
        led.check("S145-FROZEN", *judge_frozen_back(st, moved, adv, a))
    except HarnessError as err:
        led.check("S145-FROZEN", False, f"not reached: {str(err)[:240]}")


def _again(g, ctx: dict):
    """Each later row starts frozen on the world map at A under the role (a row a fault stranded elsewhere reds itself, not the
    rest): a diorama still up is left; off the world map, 6603 and the walk out again; the role and `bench 1` re-forced (and the
    calibration lever re-pulled until LEVER); back to A by teleport when the walker is away from it."""
    if _d(g.state, "booted"):
        world_leave(g)
    if g.state.ui_state != "WorldHUD":
        ok, why, _st = cw._reach_world_again(g)
        if not ok:
            raise HarnessError(f"the world map never came back: {why[:200]}")
    if not (g.state.netsync or {}).get("forced"):
        cb.try_ns(g, "selftest", 1)
        cb.poll(g, lambda s: bool((s.netsync or {}).get("forced")), 5.0, "the role again")
    cb.try_ns(g, "bench", 1)
    if ctx["calibrate"] and (ctx["stage"] or 0) >= 145 and not ctx["lever_row"]:
        cb.try_ns(g, "bench", "worldwarm", "off")
    a = ctx["a"]
    if a is not None and dist(world_xz(g.state), world_xz(a)) > RETURN_TOL:
        cw.teleport_settle(g, world_xz(a))
    cb.poll(g, lambda s: _w(s, "freeze.on") is True, 3.0, "the freeze again")
    return g.world_settle()


def _leg_silent(g, led: cb.Ledger, ctx: dict) -> None:
    """SILENT (fix1, audio-2): the host-silent lane's round trip -- `dioboot 359 0 wire silent`, then `dioleave`."""
    _again(g, ctx)
    booted, _samples, refusal, _at = world_boot(g, where="the SILENT boot", silent=True)
    if booted is None:
        led.check("S145-SILENT", False, f"the silent boot failed: {refusal or 'it never came up from the world map'}")
        if _d(g.state, "booted"):
            world_leave(g)
        return
    _first, settled, _ls, _lat, lwhy = world_leave(g, where="the SILENT leave")
    led.check("S145-SILENT", *(judge_silent(booted, settled, ctx["a"]) if settled is not None else
                               (False, f"not back on the world map: {lwhy or 'never settled after the silent return'}")))


def _leg_reset(g, led: cb.Ledger, ctx: dict) -> None:
    st0 = _again(g, ctx)
    r0 = _dio(st0, "returns")
    booted, _samples, refusal, _at = world_boot(g, where="the RESET boot")
    if booted is None:
        led.check("S145-RESET", False, f"not reached: the boot failed ({refusal or 'never came up'})")
        return
    g.send("reset")
    st = cb.poll(g, lambda s: s.netsync is not None and (s.netsync or {}).get("forced") is False and on_world_free(s),
                 LEAVE_S, "the deferred release") or g.state
    if st.ui_state == "WorldHUD":
        st = g.world_settle()
    led.check("S145-RESET", *judge_reset(st, st0, r0, True))


def _decline_row(g, ctx: dict, want_why: str, where: str) -> tuple:
    """A boot that must DECLINE: ``(ok, why)`` over the refused verb, the samples after it and the state before / after."""
    st0 = g.state
    booted, samples, refusal, _at = world_boot(g, where=where)
    samples = samples + cb.hold_for(g, DECLINE_S)
    st = g.state
    if booted is not None:
        world_leave(g)
    return judge_decline(st0, st, samples, refusal, want_why)


def _leg_vehicle(g, led: cb.Ledger, ctx: dict) -> None:
    _again(g, ctx)
    try:
        g.vehicle(1)
    except HarnessError as err:
        led.check("S145-VEH", False, f"`vehicle 1` refused: {str(err)[:240]}")
        return
    want = BW.world_warm_row(BW.world_warm_in(travel_mode=1, world=WORLD, ctx0_lastmap=WORLD))[0]
    ok, why = _decline_row(g, ctx, want, "the VEH boot")
    try:
        back = g.vehicle(0)
        foot = back.world_ctl == 0
    except HarnessError as err:
        foot, back = False, None
        why += f"; `vehicle 0` refused: {str(err)[:160]}"
    led.check("S145-VEH", ok and foot, f"{why}; back on foot (world.ctl {getattr(back, 'world_ctl', None)!r})")


def _leg_lever(g, led: cb.Ledger, ctx: dict) -> None:
    ctx["lever_row"] = True
    _again(g, ctx)
    if cb.has(g.state, PROBE):
        cb.try_ns(g, "bench", "worldwarm", "on")           # from 'on': the OFF line below is this row's own
    at = cb.mark(g)
    ok, why = cb.try_ns(g, "bench", "worldwarm", "off")
    if not ok:
        led.check("S145-LEVER", False, f"the lever cannot be sent: {why}")
        return
    cb.poll(g, lambda s: _dio(s, "lever") == "off", 3.0, "the lever off")
    want = BW.world_warm_row(BW.world_warm_in(lever=BW.WORLD_WARM_OFF))[0]
    d_ok, d_why = _decline_row(g, ctx, want, "the LEVER boot")
    n = cb.count(cb.new(g, at), BW.LOG_WORLD_WARM_OFF)
    cb.try_ns(g, "bench", "worldwarm", "on")
    led.check("S145-LEVER", d_ok and n == 1, f"{d_why}; the OFF line {n}x")


def _leg_cold(g, led: cb.Ledger, ctx: dict) -> None:
    _again(g, ctx)
    ok, why = cb.try_ns(g, "bench", "worldwarm", "cold")
    if not ok:
        led.check("S145-WC", False, f"the cold reference cannot be set: {why}")
        return
    cb.poll(g, lambda s: _dio(s, "lever") == "cold", 3.0, "the lever cold")
    booted, _samples, refusal, _at = world_boot(g, where="the WC boot")
    if booted is None:
        led.check("S145-WC", False, f"not reached: the cold boot failed ({refusal or 'never came up'})")
        cb.try_ns(g, "bench", "worldwarm", "on")
        return
    _first, settled, _ls, _lat, lwhy = world_leave(g, where="the WC leave")
    cb.try_ns(g, "bench", "worldwarm", "on")
    led.check("S145-WC", *(judge_cold(booted, settled, ctx["a"], ctx.get("probs")) if settled is not None else
                           (False, f"not reached: {lwhy or 'never settled after the cold return'}")))


def _release_solo(g, led: cb.Ledger, ctx: dict) -> None:
    """R: the lever pulled (s145), then `reset` (HarnessSelfTest(false) -> HarnessReleaseBench -> HarnessReleaseWorldWarm): the role
    released, the release line once; then the re-read WITH the role (WorldWarmLeverFor reads the bench only with it)."""
    stage = ctx.get("stage") or 0
    pulled = False
    if stage >= 145:
        pulled = cb.try_ns(g, "bench", "worldwarm", "off")[0]
    at = cb.mark(g)
    try:
        cb.release(g)
    except HarnessError as err:
        led.check("S145-R", False, f"`reset` failed: {str(err)[:300]}")
        return
    st = g.state
    ns = st.netsync or {}
    ok = ns.get("forced") is False and not cb.dio(st).get("booted")
    detail = f"forced={ns.get('forced')!r} booted={cb.dio(st).get('booted')!r}"
    if stage >= 145:
        n = cb.count(cb.wait_log(g, at, BW.LOG_WORLD_WARM_RELEASED, 2.0), BW.LOG_WORLD_WARM_RELEASED)
        st2, why = cb.reread_with_role(g)
        lever = _dio(st2, "lever") if st2 is not None else None
        ok = ok and pulled and st2 is not None and lever == "on" and n == 1
        detail += (f"; the lever pulled before the reset: {pulled}; the release line {n}x (want 1); " + (why or "")
                   + f"; re-read with the role: dio.lever {lever!r}")
    led.check("S145-R", ok, detail)


# ---------------------------------------------------------------------------------------------- T2
def held_tape_dir() -> Path:
    """The held leg's tape home: COOP_TAPE_DIR, else <the MAIN repo>/.harness-runs/coop-tapes/held-6603 (the plain recorder run
    with --field 6603 writes its latest.json THERE -- never coop_cut_hold's)."""
    env = os.environ.get("COOP_TAPE_DIR", "").strip()
    return Path(env).expanduser().resolve() if env else pb.main_repo() / ".harness-runs" / "coop-tapes" / HELD_TAPE_SUBDIR


def latest_held_tape() -> Path | None:
    """COOP_TAPE (absolute), else the held dir's latest.json, else its newest ``*-host6603-*.f9tape``."""
    env = os.environ.get("COOP_TAPE", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    d = held_tape_dir()
    try:
        p = Path(json.loads((d / "latest.json").read_text(encoding="utf-8"))["tape"])
        if p.exists():
            return p
    except (OSError, ValueError, KeyError, TypeError):
        pass
    tapes = sorted(d.glob(f"*-host{HELD_FIELD}-*.f9tape"), key=lambda p: p.stat().st_mtime) if d.is_dir() else []
    return tapes[-1] if tapes else None


def tape_ready_guest(records, cp, nonce) -> bool:
    """(PURE) the tape's battle ``nonce`` offers a READY member in one of its guest slots on some frame (a player unit whose btl
    index is in the head's guest slots, its Ready bit set) -- the slot a replayed guest's stock menu serves (WB-PLAY's premise:
    the recorder's COOPPARTY party puts a member in slot 1, GuestSlots 2)."""
    for _r, w, p in cp.host_frames(records):
        if w != cp.TYPE_BATTLE:
            continue
        d = pb.battle_detail(p, cp)
        if d is not None and d["nonce"] == nonce and any(
                u["player"] and u["ready"] and (d["guest_slots"] >> u["index"]) & 1 for u in d["unit_list"]):
            return True
    return False


def plan_battle_leg(facts: dict, ready_guest: bool = True) -> dict:
    """The battle leg's plan: _coop_peer_bench.plan_world_leg('world-battle') AND the host's entry into the Ice Cavern after its
    stay (expect.rejoin_field 300: WB-300's rejoin) AND a Ready guest slot on its battle (``ready_guest``: :func:`tape_ready_guest`,
    WB-PLAY's premise) -- a tape missing either cannot carry this leg."""
    plan = pb.plan_world_leg("world-battle", facts)
    if plan["ok"] and plan["expect"].get("rejoin_field") != ICE_CAVERN:
        plan.update(ok=False, why=(f"the tape carries no host entry into {ICE_CAVERN} after its stay (WB-300's rejoin): record "
                                   "with COOP_TAPE_WB_ENTER=1, the default"))
    elif plan["ok"] and not ready_guest:
        plan.update(ok=False, why=("the tape's battle never offers a Ready guest slot (GuestSlots 2 needs a member in slot 1: "
                                   "the recorder's COOPPARTY seed) -- no stock menu could be served (WB-PLAY)"))
    return plan


def plan_held_leg(facts: dict) -> dict:
    """The held leg's plan over _coop_peer_bench.tape_facts(field=6603): the five facts on 6603 (F5: the host back on it after its
    battle), the host on 6603 >= HELD_PRE_NEED_S before its battle (the guest pairs, walks out, freezes and sets up inside it);
    the whole tape (the replay holds at its end)."""
    bad = [f"{k} {(facts.get(k) or {}).get('why', 'missing')}" for k in ("f1", "f2", "f3", "f4", "f5")
           if not (facts.get(k) or {}).get("ok")]
    f1 = facts.get("f1") or {}
    pre = f1.get("pre_s")
    if f1.get("field") != HELD_FIELD:
        bad.append(f"the host's field is {f1.get('field')!r}, not {HELD_FIELD} (record with --field {HELD_FIELD})")
    elif pre is None or pre < HELD_PRE_NEED_S:
        bad.append(f"the host on {HELD_FIELD} only {pre if pre is None else round(pre, 1)} s before its battle (the guest's "
                   f"pairing, walk out and setup need >= {HELD_PRE_NEED_S:g}: COOP_TAPE_PRE_S=100)")
    b = facts.get("battle") or {}
    return {"ok": not bad, "why": "; ".join(bad), "field": HELD_FIELD, "stop_at": None,
            "expect": {"nonce": b.get("nonce"), "scene": b.get("map"), "battle_start": b.get("start"),
                       "battle_end": b.get("end"), "leave_whys": ("terminal", "host_field")}}


class _T2:
    def __init__(self):
        self.tape = None
        self.facts = None
        self.plan = None
        self.stage = 0
        self.guard = None
        self.peer = None
        self.eng = None
        self.samples: list = []
        self.anchors: dict = {}
        self.a = None
        self.after_ret = None
        self.marker_own = None
        self.hung = None
        self.probs = None                                  # [fix1] the encounter-rate oracle (world_prob_oracle)
        self.probs_from = None


def _run_t2(g, leg: str) -> None:
    calibrate = cb.CALIBRATE
    p = T2_PFX[leg]
    led = cb.Ledger(g, t2_catalog(leg, calibrate), finals=("T2-SAVE", "T2-INI", f"{p}-SWIRL", f"{p}-CAL"))
    ctx = _T2()
    try:
        _t2(g, led, ctx, leg)
    except SwirlHang as err:
        ctx.hung = str(err)
        _note(g, str(err)[:600])
        led.close(f"SWIRL-HANG -- the instrument (the runner retries this leg once): {str(err)[:200]}")
    except HarnessError as err:
        _note(g, f"the {leg} leg raised: {str(err)[:400]}")
        led.close(f"the leg raised ({str(err)[:200]})")
    finally:
        _t2_teardown(g, led, ctx, leg)
        led.check(f"{p}-SWIRL", ctx.hung is None, ctx.hung or "the guest's boot never hung in the swirl")
        if calibrate:
            try:
                ctx.stage = max(ctx.stage, stage_of(g.state))
            except HarnessError:
                pass
            pred = T2_PREDICTED[leg] if ctx.stage < 145 else ()
            _note(g, f"{p}-CAL: the guest reads as s{ctx.stage or '<117'}; predicted reds {sorted(pred)}")
            led.close("not reached: the leg ended before this check")
            if ctx.hung is not None:
                led.check(f"{p}-CAL", False, "not reached: SWIRL-HANG -- the instrument; retry the leg")
            else:
                led.judge_calibration(f"{p}-CAL", pred)
        led.close(final=True)


def _t2_teardown(g, led: cb.Ledger, ctx: _T2, leg: str) -> None:
    if ctx.peer is not None and ctx.peer.how_ended is None:
        _note(g, f"coop_peer replay-host: {ctx.peer.stop()}")
    if "T2-SAVE" not in led.done:
        fell = pb.hits(ctx.eng.lines(), "ramp_failed") if ctx.eng is not None else []
        led.check("T2-SAVE", not fell, f"the exit ramp fell back to the TITLE: {pb.show(fell, 1)}" if fell else
                  "no title fallback" + ("" if ctx.eng is not None else " (the guest never ran a session)"))
    if ctx.guard is not None:
        ok, why = ctx.guard.restore()
        led.check("T2-INI", ok, why)
    else:
        led.check("T2-INI", True, "Memoria.ini was never edited (the leg stopped before the edit)")
    _note(g, f"Memoria.log archived: {cb.archive_log(g, f'world-battle-{leg}')}")


def _sample(g, ctx: _T2):
    st = g.state
    ctx.samples.append((_dt.datetime.now(), st))
    if ctx.eng is not None:
        ctx.eng.lines()
    if ctx.peer is not None:
        for key in ("guest_connected", "replay_start"):
            if key not in ctx.anchors:
                hit = ctx.peer.first(pb.PEER[key])
                if hit is not None:
                    ctx.anchors[key] = hit[0]
        for t, _msg, m in ctx.peer.find(pb.PEER["tape_field"]):
            if "exit" not in ctx.anchors and m.group(3) == "0" and str(HELD_FIELD) in m.group(2):
                ctx.anchors["exit"] = t
            if "enter" not in ctx.anchors and m.group(3) == str(ICE_CAVERN):
                ctx.anchors["enter"] = t
        if "battle" not in ctx.anchors:
            hit = ctx.peer.first(PEER_NONCE)
            if hit is not None:
                ctx.anchors["battle"], ctx.anchors["nonce"] = hit[0], int(hit[2].group(2))
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


def _msgs(ctx: _T2, after=None) -> list:
    """The engine's messages (Memoria.log, the stamp stripped) since ``after`` (whole-second stamps: floored)."""
    cut = pb.floor_s(after) if after is not None else None
    return [m for t, _l, m in ctx.eng.lines() if cut is None or t >= cut]


def _config_hits(ctx: _T2, code: str = CODE) -> list:
    return pb.hits(ctx.eng.lines(), "config", pred=lambda m: m.group(1) == "True" and m.group(2) == "client"
                   and m.group(5) == f"ws://127.0.0.1:{PORT}" and m.group(6) == code)


def _wait_config(g, ctx: _T2) -> list:
    """The engine's own config line for the bench code -- a 6603 reload after 6 s if none (Ensure reads the ini at a field load)."""
    for wait_s, reload_ in ((6.0, True), (10.0, False)):
        deadline = time.time() + wait_s
        while time.time() < deadline:
            if _config_hits(ctx):
                return _config_hits(ctx)
            time.sleep(0.25)
        if reload_:
            g.note("no config line within the poll window -- reloading 6603 (Ensure reads the ini at a field load)")
            try:
                g.warp(FARSHORE)
            except HarnessError as err:
                g.note(f"the reload warp failed: {str(err)[:200]}")
    return _config_hits(ctx)


def _t2(g, led: cb.Ledger, ctx: _T2, leg: str) -> None:
    p = T2_PFX[leg]
    rows = [c for c in led.catalog if c.startswith(p + "-") and not c.endswith(("-CAL", "-SWIRL"))]
    # A. the tape and its plan
    worldtape = leg in ("battle", "decline")                # [fix1] the decline leg replays the world-battle tape too
    ctx.tape = pb.latest_world_battle_tape() if worldtape else latest_held_tape()
    if ctx.tape is None or not Path(ctx.tape).exists():
        led.check("T2-TAPE", False, f"no tape ({ctx.tape or (pb.world_battle_tape_dir() if worldtape else held_tape_dir())})"
                                    + (": record one -- COOP_TAPE_WORLD_BATTLE=1 coop_tape_record.py" if worldtape else
                                       f": record one -- COOP_TAPE_PRE_S=100 COOP_TAPE_DIR=<{HELD_TAPE_SUBDIR}> "
                                       f"coop_tape_record.py --field {HELD_FIELD}"))
        led.close("not reached: no tape")
        return
    try:
        cp = pb.coop_peer_module()
        _h, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                              # noqa: BLE001
        led.check("T2-TAPE", False, f"{ctx.tape} does not read back: {err}")
        led.close("not reached: the tape does not read back")
        return
    if worldtape:
        ctx.facts = pb.world_battle_tape_facts(records, cp)
        b = ctx.facts.get("battle") or {}
        ctx.plan = plan_battle_leg(ctx.facts, tape_ready_guest(records, cp, b.get("nonce")) if b else False)
    else:
        ctx.facts = pb.tape_facts(records, cp, field=HELD_FIELD)
        ctx.plan = plan_held_leg(ctx.facts)
    exp = ctx.plan.get("expect") or {}
    led.check("T2-TAPE", ctx.plan["ok"], f"{Path(ctx.tape).name} ({len(records)} records{f', torn {torn} B' if torn else ''}): "
                                         + ("ok" if ctx.plan["ok"] else "CANNOT -- " + ctx.plan["why"])
                                         + f"; battle nonce {exp.get('nonce')} scene {exp.get('scene')} from tape "
                                         f"{exp.get('battle_start')}" + (f"; the entry into {exp.get('rejoin_field')} at "
                                                                         f"{exp.get('enter_t')}" if worldtape else ""))
    if not ctx.plan["ok"]:
        led.close(f"this tape cannot carry the {leg} leg ({ctx.plan['why'][:200]})")
        return
    # B. the port, the owner's bridge, the guest's own autosave
    free, why = (False, f"COOP_PEER_PORT={PORT} is the owner's bridge port: the s145 legs never bind it (they write their own "
                        f"RelayUrl -- pick a private port; default {pb.WORLD_PORT})") if PORT == pb.OWNER_PORT \
        else pb.port_free(PORT)
    if not free:
        led.check("T2-PEER", False, why)
        led.close("not reached: the bench port is taken (nothing was edited)")
        return
    owner_free, _owhy = pb.port_free(pb.OWNER_PORT)
    if not owner_free:
        led.check("T2-PEER", False, f"the owner's bridge is UP on 127.0.0.1:{pb.OWNER_PORT}: this guest game launched on the "
                                    "owner's Memoria.ini dials it before any edit and joins the owner's LIVE session -- stop "
                                    "the bridge first")
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
    # [fix1] the encounter-rate oracle, READ-ONLY, before the run (the RET rows judge world.battle_prob by its value)
    ctx.probs, ctx.probs_from = world_prob_oracle(g.game_path)
    g.note(f"the encounter-rate oracle: {ctx.probs_from}")
    # C. the guest's own game on 6603
    cb.provenance(g)
    g.note(f"s145 T2 {leg} leg: the guest on {FARSHORE}, then the world map")
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
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", GUEST_VALUES, label=f"coop-world-battle-{leg}",
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
    # E. the replay-host: the whole tape, holding at its end
    rd = _run_dir(g)
    args = [ctx.tape, "--port", str(PORT), "--code", CODE, "--at-end", "hold"]
    ctx.peer = pb.PeerProc("replay-host", args, log_path=rd / f"coop_peer-replay-world-battle-{leg}.log",
                           out_path=rd / f"coop_peer-replay-world-battle-{leg}.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0, tick=lambda: _sample(g, ctx))
    conn = ctx.peer.wait_for(pb.PEER["guest_connected"], DIAL_S, tick=lambda: _sample(g, ctx)) if up else None
    start = ctx.peer.wait_for(pb.PEER["replay_start"], 10.0, tick=lambda: _sample(g, ctx)) if conn else None
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "guest" and m.group(2) == CODE)
    ok = up is not None and conn is not None and start is not None and bool(relay)
    led.check("T2-PEER", ok, f"config: {pb.show(cfg, 1)}; peer: {up[1] if up else 'never listened'} / "
                             f"{conn[1] if conn else 'no guest'} / {start[1] if start else 'no replay start'}; engine: "
                             f"{pb.show(relay, 1)}")
    if not ok:
        led.unreached(rows, "the instrument never started (T2-PEER)")
        return
    ctx.anchors["start"] = start[0]
    if not _t2_setup(g, led, ctx, leg, p):
        return
    if leg == "decline":
        _t2_decline(g, led, ctx, p)
        return
    _t2_battle(g, led, ctx, leg, p)


def _paired_armed(ctx: _T2):
    lines = ctx.eng.lines()
    start = ctx.anchors["start"]
    return (pb.hits(lines, "paired", after=start, pred=lambda m: int(m.group(1)) == FARSHORE),
            pb.hits(lines, "armed", after=start))


def battle_wall(ctx: _T2):
    """When the host's battle reaches the wire, wall time: the replay's start + (the plan's battle time - the tape's first host
    frame) / REPLAY_SPEED (replay-host's clock starts at the guest's first frame, at its first host frame's tape time)."""
    exp = ctx.plan.get("expect") or {}
    t0 = ctx.facts.get("start")
    if exp.get("battle_start") is None or t0 is None or "start" not in ctx.anchors:
        return None
    return ctx.anchors["start"] + _dt.timedelta(seconds=(float(exp["battle_start"]) - float(t0)) / REPLAY_SPEED)


def _t2_setup(g, led: cb.Ledger, ctx: _T2, leg: str, p: str) -> bool:
    """<P>-I, the instrument (False = the leg stops, its rows recorded). battle: paired + ARMED on 6603 before the host's world
    exit, which the guest waits for; its own walk out, FROZEN, onto ICE_TILE, snapshot A -- all before the host's battle reaches
    the wire. held: paired + ARMED (the host stays), the axes calibrated on 6603, the walk started HELD_LEAD_S before the battle
    (THE 15 s HOLD), A the arrival -- judged once the battle is on the wire (:func:`_held_window`)."""
    rows = [c for c in led.catalog if c.startswith(p + "-") and not c.endswith(("-CAL", "-SWIRL", "-I"))]
    if leg != "held":                                      # battle / decline: the host's world exit first
        _until(g, ctx, lambda s: "exit" in ctx.anchors, PAIR_S + EXIT_S)
        gate = ctx.anchors.get("exit")
    else:
        _until(g, ctx, lambda s: all(_paired_armed(ctx)) and s.ui_state == "FieldHUD" and s.field_id == FARSHORE, PAIR_S)
        cb.hold_for(g, 1.5)
        gate = _dt.datetime.now()
    paired, armed = _paired_armed(ctx)
    paired = [h for h in paired if gate is None or h[0] <= gate + _dt.timedelta(seconds=1)]
    before = [s for ts, s in ctx.samples if gate is not None and ts <= gate]
    on6603 = bool(before) and before[-1].ui_state == "FieldHUD" and before[-1].field_id == FARSHORE
    why = (f"paired {pb.show(paired, 1)}; armed {pb.show(armed, 1)}; "
           + (f"the host's world exit {'at ' + gate.strftime('%H:%M:%S') if gate else 'NEVER on the peer log'}; "
              if leg != "held" else "the host stays on 6603; ")
           + f"the guest on {before[-1].ui_state if before else '?'} {before[-1].field_id if before else ''}")
    if not (gate is not None and paired and armed and on6603):
        led.check(f"{p}-I", False, why)
        led.unreached(rows, f"the instrument is untrustworthy on this run ({p}-I)")
        return False
    if leg == "held":
        return _held_walk(g, led, ctx, p, rows, why)
    base = g.state
    ok, wwhy, _st = cw.walk_out(g)
    if not ok:
        led.check(f"{p}-I", False, f"{why}; the guest's walk out failed: {wwhy[:200]}")
        led.unreached(rows, "the guest never reached the world map")
        return False
    moved, adv, st = cw.hold_walk(g, WALK_FRAMES)
    f_ok, f_why = cw.judge_frozen(st, moved, adv, base)
    try:
        cw.teleport_settle(g, ICE_TILE)
        g.wait_frames(10)
        ctx.a = g.world_settle()
    except HarnessError as err:
        ctx.a = None
        f_why += f"; the tile teleport raised: {str(err)[:160]}"
    _sample(g, ctx)
    early = ctx.anchors.get("battle")
    a_ok = ctx.a is not None and dist(world_xz(ctx.a), ICE_TILE) <= RETURN_TOL and ctx.a.ui_state == "WorldHUD"
    ok = f_ok and a_ok and early is None
    led.check(f"{p}-I", ok, f"{why}; FROZEN {f_why}; A on the Ice Cavern tile {a_ok} "
                            f"({world_xz(ctx.a) if ctx.a is not None else None}); the host's battle on the wire "
                            + ("BEFORE A (the tape's dwell is too short for this run)" if early is not None else "not yet"))
    if not ok:
        led.unreached(rows, f"the instrument is untrustworthy on this run ({p}-I)")
        return False
    return True


def _held_walk(g, led: cb.Ledger, ctx: _T2, p: str, rows, why: str) -> bool:
    """The held leg's timed walk out: the axes calibrated now (on 6603), then -- at the battle's wall time less HELD_LEAD_S -- the
    walk to the door, the world's load, A (the arrival, frozen, the hold latched). HF-I itself is judged at the battle's first
    frame on the wire (:func:`_held_window`)."""
    at_ = battle_wall(ctx)
    try:
        g.calibrate_axes(hazards=[cw.FS_DOOR])
    except HarnessError as err:
        led.check(f"{p}-I", False, f"{why}; calibrate_axes on {FARSHORE} failed: {str(err)[:200]}")
        led.unreached(rows, "the instrument never walked out")
        return False
    go = at_ - _dt.timedelta(seconds=HELD_LEAD_S) if at_ is not None else None
    now = _dt.datetime.now()
    late = go is None or now > go
    if not late:
        _until(g, ctx, lambda s: _dt.datetime.now() >= go, (go - now).total_seconds() + 1.0)
    ctx.anchors["walk"] = _dt.datetime.now()
    at = cb.mark(g)
    try:
        g.walk_to(*cw.FS_EXIT, strict=False, halt_on_transition=True)
        # sampled, never a blocking wait_world: the host's battle may reach the guest right as the world comes up (its boot is
        # this leg's subject -- a wait for WorldHUD would sit through the whole diorama)
        _until(g, ctx, lambda s: s.ui_state == "WorldHUD" or booted_world(s), cw.WORLD_S)
        st = g.state
        if st.ui_state == "WorldHUD":
            st = g.world_settle()                         # (returns at once if a boot takes the world map away)
    except HarnessError as err:
        led.check(f"{p}-I", False, f"{why}; the timed walk out never reached the world map: {str(err)[:200]}")
        led.unreached(rows, "the guest never reached the world map")
        return False
    _sample(g, ctx)
    if st.ui_state == "WorldHUD":
        try:
            g.no_encounters(True)
        except (HarnessError, AttributeError):
            pass
    ctx.a = next((s for _ts, s in reversed(ctx.samples) if s.ui_state == "WorldHUD" and world_xz(s)[0] is not None
                  and not _d(s, "booted")), None)
    walk_note = "LATE (after the lead time)" if late else "on time"
    battle_note = at_.strftime("%H:%M:%S") if at_ is not None else "?"
    ctx.anchors["held_why"] = f"{why}; the walk started {walk_note} {HELD_LEAD_S:g} s before the battle's wall time {battle_note}"
    ctx.anchors["held_lines"] = cb.new(g, at)
    return True


def _held_window(ctx: _T2, bt) -> tuple:
    """HF-I (PURE over the run's samples): the walk started before the host's battle reached the wire (``bt``); A -- the arrival --
    on WorldHUD 9011 near the landing, the hold latched (follow.hold 6603, its line once since the walk), freeze.on; and the FIRST
    sample at or after ``bt`` on the world map with the hold still held (the guest may still be loading the world when the battle
    arrives -- the watcher waits for WorldHUD; a hold that expired first sent it back to 6603: the walk missed the window, the
    instrument's red, never the engine's)."""
    a = ctx.a
    if a is not None:
        hold_ok, hold_why = cw.judge_hold(a, ctx.anchors.get("held_lines") or [], src=HELD_FIELD, wld=WORLD)
    else:
        hold_ok, hold_why = False, "no arrival state"
    walk = ctx.anchors.get("walk")
    on_time = walk is not None and bt is not None and walk <= bt
    at_bt = next((s for ts, s in ctx.samples if bt is not None and ts >= bt), None)
    in_window = (at_bt is not None and (at_bt.ui_state == "WorldHUD" or booted_world(at_bt))
                 and _f(at_bt, "hold") == HELD_FIELD)
    frozen = a is not None and _w(a, "freeze.on") is True
    near = a is not None and world_xz(a)[0] is not None and dist(world_xz(a), FS_LANDING) <= ROUTE_TOL
    ok = a is not None and hold_ok and frozen and near and on_time and in_window
    where = f"on WorldHUD at {world_xz(a)}" if a is not None else "NEVER on the world map"
    first = (at_bt.ui_state, _f(at_bt, "hold")) if at_bt is not None else "no sample"
    missed = "" if in_window and on_time else " -- the walk MISSED the hold window: the instrument"
    return ok, (("the walk MISSED the hold window (the instrument, never the engine): " if missed else "")
                + f"{ctx.anchors.get('held_why', '')}; walked before the battle {on_time}; A {where}; HOLD {hold_why}; freeze.on "
                f"{_w(a, 'freeze.on') if a is not None else None!r}; the first sample after the battle reached the wire: {first} "
                f"(want WorldHUD -- or its world diorama already up -- and the hold {HELD_FIELD}{missed})")


def _t2_battle(g, led: cb.Ledger, ctx: _T2, leg: str, p: str) -> None:
    """BOOT, PLAY (battle), RET, then the rejoin (battle: into 300 after the host's entry; held: into 6603 after the hold) -- every
    sample the guest published from the battle's first frame on the wire, the peer's decode of the guest's control frames, the
    guest's own lines."""
    exp = ctx.plan["expect"]
    later = [f"{p}-BOOT", f"{p}-PLAY", f"{p}-RET", f"{p}-300", f"{p}-REJOIN"]
    if not _until(g, ctx, lambda s: "battle" in ctx.anchors, BATTLE_WAIT_S):
        if leg == "held":
            led.check(f"{p}-I", False, f"{ctx.anchors.get('held_why', '')}; the host's battle never reached the wire")
        led.unreached(later, f"the host's battle never reached the wire within {BATTLE_WAIT_S:g} s")
        return
    bt, nonce = ctx.anchors["battle"], ctx.anchors["nonce"]
    if leg == "held":
        ok, why = _held_window(ctx, bt)
        led.check(f"{p}-I", ok, why)
        if not ok:
            led.unreached(later, f"the instrument is untrustworthy on this run ({p}-I)")
            return
    a = ctx.a
    r0, d0 = _dio(a, "returns"), _d(a, "returns")
    _state_every(g, 1)                                    # the guest's swirl: every frame written (SWIRL-HANG's last state)
    booted = _until(g, ctx, booted_world, BOOT_WAIT_S)
    if not booted:
        hang_check(g, "the guest's boot")
    _state_every(g, 2)
    booted_st = next((s for s in _after(ctx, bt) if booted_world(s)), None)
    fight_s = max(0.0, float((exp.get("battle_end") or 0.0) - (exp.get("battle_start") or 0.0))) / REPLAY_SPEED
    if booted_st is not None:
        _until(g, ctx, lambda s: any(b == "LIVE" for _t, _m, b in peer_reports(ctx.peer.lines(), nonce, bt))
               and any(pb.MATCHERS["live"].search(m) for m in _msgs(ctx, bt)), LIVE_WAIT_S)
        _until(g, ctx, lambda s: on_world_free(s), RET_WAIT_S)
    else:                                                 # the host's whole fight on the wire: the guest stays and reports, up
        _until(g, ctx, lambda s: "enter" in ctx.anchors or s.ui_state == "FieldHUD", fight_s + 8.0)   # to the next field
    end = ctx.anchors.get("enter") or _dt.datetime.now()
    since = [s for ts, s in ctx.samples if bt <= ts <= end]
    if booted_st is None:                                 # the rejoin's own field load is the next field, not the battle's
        cut = next((i for i, s in enumerate(since) if s.ui_state == "FieldHUD"), len(since))
        since = since[:cut]
    lines = _msgs(ctx, bt)
    reports = peer_reports(ctx.peer.lines(), nonce, bt)
    led.check(f"{p}-BOOT", *judge_guest_boot(boot_window(since), booted_st, reports, lines, nonce))
    if leg == "battle":
        led.check(f"{p}-PLAY", *(judge_play(reports, lines) if booted_st is not None else
                                 (False, f"not reached: no world diorama ({judge_report(reports)[1]})")))
    after = None
    if booted_st is None:
        led.check(f"{p}-RET", False, f"not reached: no world diorama -- it stayed on {sorted({s.ui_state for s in since})} "
                                     f"(the digit panel; {judge_report(reports)[1]})")
    else:
        i0 = next((i for i, s in enumerate(since) if booted_world(s)), None)
        tail = since[i0:] if i0 is not None else []
        first_i = next((i for i, s in enumerate(tail) if on_world_free(s)), None)
        if leg == "held" and first_i is not None:         # the rejoin into 6603 follows the return: its field is no return
            k = next((i for i in range(first_i, len(tail)) if tail[i].ui_state == "FieldHUD"), len(tail))
            tail = tail[:k]
            since = since[:(i0 or 0) + k]
        first = tail[first_i] if first_i is not None else None
        why = leave_why(tail, lines)
        if leg == "held":                                 # the rejoin follows: the return's own samples (its last), the keys
            settled = next((s for s in reversed(tail) if on_world_free(s)), first)
            moved = adv = None
            after = settled
        else:
            settled = song_quiet(g, g.world_settle()) if g.state.ui_state == "WorldHUD" else None   # [fix2] past the fades
            try:
                moved, adv, after = cw.hold_walk(g, WALK_FRAMES) if settled is not None else (None, None, None)
            except HarnessError as err:
                moved, adv, after = None, None, None
                _note(g, f"the frozen witness raised: {str(err)[:200]}")
        _sample(g, ctx)
        pre = pre_boot_ticks([s for _ts, s in ctx.samples], a)
        led.check(f"{p}-RET", *judge_guest_return(first, settled, a, r0, d0, why, exp["leave_whys"], moved, adv, since,
                                                    keys_only=leg == "held", pre_ticks=pre, probs=ctx.probs,
                                                    booted=booted_st))
    ctx.after_ret = after if after is not None else (since[-1] if since else g.state)
    _t2_rejoin(g, led, ctx, p, leg)


def _t2_decline(g, led: cb.Ledger, ctx: _T2, p: str) -> None:
    """WD-DECL (fix1): aboard a chocobo the followed guest's WATCHER declines the host's battle for the world visit -- `vehicle 1`
    after WD-I, then every sample through the host's whole fight on the wire (to its entry into 300, or the fight's end + 8 s),
    the peer's decode of the guest's report, the guest's own lines; then `vehicle 0`."""
    row = f"{p}-DECL"
    exp = ctx.plan["expect"]

    def instrument(why: str) -> None:
        # [fix2, fix3] THE ABOARD GUARD: the host's battle beat the boarding -- the on-foot guest rightly boots it. The instrument's,
        # never judged: WD-I red (its own catalog: the guest aboard before the battle) and WD-DECL 'not reached: the instrument',
        # as the held leg reads a missed window (HF-I red, its rows not reached)
        text = f"the host's battle reached the wire before the guest was aboard: {why}"
        led.check(f"{p}-I", False, text)
        led.check(row, False, f"not reached: the instrument ({text})")

    try:
        g.vehicle(1)
    except HarnessError as err:
        st = _sample(g, ctx)
        if aboard_refusal_instrument("battle" in ctx.anchors, st):     # [fix3] the refusal coincides with the boot it predicts
            instrument(f"`vehicle 1` {str(err)[:200]}")
            return
        led.check(row, False, f"`vehicle 1` refused: {str(err)[:240]}")
        return
    st0 = _sample(g, ctx)
    # [fix3] the guest ABOARD by st0's own read (`vehicle 1` returned on world.ctl 1 read back) -- and st0 is the judge's declines /
    # visit baseline, so a battle anchored at or before THAT read is the instrument's (bench clock: the peer's line stamps share it)
    t_aboard = ctx.samples[-1][0]
    want = BW.world_warm_row(BW.world_warm_in(travel_mode=1, world=WORLD, ctx0_lastmap=WORLD))[0]
    if not _until(g, ctx, lambda s: "battle" in ctx.anchors, BATTLE_WAIT_S):
        led.check(row, False, f"not reached: the host's battle never reached the wire within {BATTLE_WAIT_S:g} s")
        return
    bt, nonce = ctx.anchors["battle"], ctx.anchors["nonce"]
    if bt <= t_aboard:
        instrument(f"battle {bt:%H:%M:%S.%f}, aboard {t_aboard:%H:%M:%S.%f}")
        # (no `vehicle 0` here: the world decline is re-read every frame, so a dismount mid-fight boots the on-foot guest with
        # nobody watching -- the leg ends now and play.py closes the game; the next leg starts with newgame)
        return
    _state_every(g, 1)                                    # (a boot -- the red -- would write every swirl frame)
    fight_s = max(0.0, float((exp.get("battle_end") or 0.0) - (exp.get("battle_start") or 0.0))) / REPLAY_SPEED
    # [fix3b] watch until the host's ENTRY reaches the wire -- never stop at the guest's own first FieldHUD: a guest that leaves
    # the world map mid-fight (decision 3 forbids it) lands long before that entry, so stopping on it left the window unanchored
    # and the 300 cut forgave it (green). Anchored, the FieldHUD sits inside [bt, enter] and is judged.
    _until(g, ctx, lambda s: "enter" in ctx.anchors, fight_s + ENTER_WAIT_S)
    hang_check(g, "the decline's watch")                  # [fix3] whatever the claim says: a swirl stall with `booted` unset
    _state_every(g, 2)                                    # reads WorldHUD on SwirlScene (it does nothing unless quiet there)
    since, rejoined = decline_window(ctx.samples, bt, ctx.anchors.get("enter"), _dt.datetime.now(),
                                     not_before=bt + _dt.timedelta(seconds=fight_s))
    led.check(row, *judge_watch_decline(st0, since, peer_reports(ctx.peer.lines(), nonce, bt), _msgs(ctx, bt), nonce, want,
                                        rejoined=rejoined))
    try:
        g.vehicle(0)
    except HarnessError as err:
        _note(g, f"`vehicle 0` refused after the decline: {str(err)[:200]}")


def _t2_rejoin(g, led: cb.Ledger, ctx: _T2, p: str, leg: str) -> None:
    """WB-300 / HF-REJOIN: the guest rejoins the host's next field from the world map -- the Ice Cavern after the host's entry on
    the wire (battle), 6603 once the host is back on it past the hold (held) -- and no second return is counted there."""
    base = ctx.after_ret
    if leg == "battle":
        if not _until(g, ctx, lambda s: "enter" in ctx.anchors, ENTER_WAIT_S):
            led.check(f"{p}-300", False, f"not reached: the host's entry into {ICE_CAVERN} never reached the wire within "
                                         f"{ENTER_WAIT_S:g} s")
            return
        t0, field, cid = ctx.anchors["enter"], ICE_CAVERN, f"{p}-300"
    else:
        t0, field, cid = ctx.anchors["battle"], FARSHORE, f"{p}-REJOIN"
    _until(g, ctx, lambda s: s.ui_state == "FieldHUD" and s.field_id == field, REJOIN_S)
    cb.hold_for(g, 1.5)
    _sample(g, ctx)
    led.check(cid, *judge_rejoin_300([s for ts, s in ctx.samples if ts >= t0], base, _msgs(ctx, t0), field=field))


# ---------------------------------------------------------------------------------------------- the duo
class GuestTap(threading.Thread):
    """The GUEST's publishes on a thread while the main thread drives the HOST (its fight blocks): distinct frames; a read that
    fails is skipped. Nothing else reads the guest while it runs."""

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
                self.samples.append(st)
            time.sleep(self.period)

    def wait_for(self, pred, timeout: float):
        """The first tapped sample satisfying ``pred`` (waiting up to ``timeout``), or None."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            hit = next((s for s in list(self.samples) if pred(s)), None)
            if hit is not None:
                return hit
            time.sleep(0.05)
        return next((s for s in list(self.samples) if pred(s)), None)

    def wait_return(self, timeout: float):
        """The first tapped world-free sample AFTER a world-booted one (the return), waiting up to ``timeout``; None = none."""
        deadline = time.time() + timeout
        while True:
            snap = list(self.samples)
            i0 = next((i for i, s in enumerate(snap) if booted_world(s)), None)
            hit = next((s for s in snap[i0:] if on_world_free(s)), None) if i0 is not None else None
            if hit is not None or time.time() >= deadline:
                return hit
            time.sleep(0.05)

    def stop(self) -> list:
        self.halt.set()
        self.join(5.0)
        return list(self.samples)


def _host_nonce(samples):
    """The host's own battle nonce off its start hold (the first >= 0), or None."""
    return next((n for n in (cb.path(s, "netsync.battle.host.start_hold.nonce") for s in samples)
                 if isinstance(n, int) and not isinstance(n, bool) and n >= 0), None)


def run_duo(d) -> None:
    """The duo leg (duo.py pairs the two games on 6603 first: ``PAIR``, the host seeded through COOPPARTY). Every row recorded
    (strict off), each judged on the GUEST's samples beside its engine's keys -- and DB / DP on the HOST's decode of the guest's
    report; COOP_CALIBRATE=1 judges D-CAL by the GUEST's stage."""
    calibrate = cb.CALIBRATE
    strict, d.strict = d.strict, False
    failed, done, hung = [], set(), [None]

    def check(cid, ok, detail):
        if cid in done:
            return
        done.add(cid)
        if not ok:
            failed.append(cid)
        d.check(bool(ok), f"{cid}: {DUO_CHECKS.get(cid, cid)}", str(detail)[:900], cid=cid)

    def rest(why):
        for cid in DUO_ORDER:
            if cid != "S145-D-SWIRL" and cid not in done:
                check(cid, False, f"not reached: {why}"[:900])

    try:
        _duo(d, check, rest)
    except SwirlHang as err:
        hung[0] = str(err)
        d.note(str(err)[:600])
        rest(f"SWIRL-HANG -- the instrument (the runner retries the duo once): {str(err)[:200]}")
    except HarnessError as err:
        d.note(f"the duo raised: {str(err)[:400]}")
        rest(f"the duo raised ({str(err)[:200]})")
    finally:
        check("S145-D-SWIRL", hung[0] is None, hung[0] or "neither game's battle start hung in the swirl")
        if calibrate:
            try:
                stage = stage_of(d.guest.state)
            except HarnessError:
                stage = 0
            pred = set(DUO_PREDICTED) if stage < 145 else set()
            missing, extra = sorted(pred - set(failed)), sorted(set(failed) - pred)
            d.check(not missing and not extra and hung[0] is None, "S145-D-CAL: CALIBRATION -- exactly the predicted duo rows "
                                                                   "red for the GUEST's stage",
                    f"guest s{stage}: predicted reds that stayed GREEN {missing or 'none'}; unpredicted reds {extra or 'none'}"
                    + ("; SWIRL-HANG: the instrument" if hung[0] else ""), cid="S145-D-CAL")
        d.strict = strict


def _duo(d, check, rest) -> None:
    host, guest = d.host, d.guest
    gst = guest.state
    d.note(f"s145 duo: the guest reads as s{stage_of(gst)}, the host as s{stage_of(host.state)}")
    probs, probs_from = world_prob_oracle(guest.game_path)     # [fix1] DR judges world.battle_prob by value
    d.note(f"the encounter-rate oracle (the guest's install): {probs_from}")
    both = (host.state.ui_state == "FieldHUD" and host.state.field_id == FARSHORE and gst.ui_state == "FieldHUD"
            and gst.field_id == FARSHORE and _s(gst, "mirroring") is True)
    check("S145-D0", both, f"host {host.state.ui_state} {host.state.field_id}; guest {gst.ui_state} {gst.field_id}, "
                           f"mirroring {_s(gst, 'mirroring')!r}")
    if not both:
        rest("the pair is not on 6603 (D0)")
        return
    # D1 / D2: coop_world_wait's
    ok, why, _hs = cw.walk_out(host)
    if not ok:
        rest(f"the host's walk out failed ({why[:160]})")
        return
    samples, hit = cb.watch(guest, lambda s: cw.judge_line(s, b6=True, field=FARSHORE)[0], cw.DUO_LINE_S)
    left = [(s.ui_state, s.field_id) for s in samples if not (s.ui_state == "FieldHUD" and s.field_id == FARSHORE)]
    l_ok, l_why = cw.judge_line(hit if hit is not None else guest.state, b6=True, field=FARSHORE)
    check("S145-D1", l_ok and not left, l_why + (f"; the guest LEFT 6603: {left[:3]}" if left else ""))
    base = guest.state
    at = cb.mark(guest)
    ok, why, _gs = cw.walk_out(guest)
    if not ok:
        rest(f"the guest's walk out failed ({why[:160]})")
        return
    moved, adv, gst = cw.hold_walk(guest, WALK_FRAMES)
    f_ok, f_why = cw.judge_frozen(gst, moved, adv, base)
    cb.hold_for(guest, 1.0)
    gst = guest.state
    l_ok, l_why = cw.judge_line(gst, b6=True)
    n = cb.count(cb.new(guest, at), BW.log_world_hold_released(FARSHORE, False))
    check("S145-D2", f_ok and l_ok and n == 1, f"FROZEN {f_why}; LINE {l_why}; the hold released by b6 {n}x")
    # A: the guest onto the Ice Cavern tile (far from the landing: discriminating)
    cw.teleport_settle(guest, ICE_TILE)
    guest.wait_frames(10)
    a = guest.world_settle()
    if dist(world_xz(a), ICE_TILE) > RETURN_TOL:
        rest(f"the guest never stood on the Ice Cavern tile (A at {world_xz(a)})")
        return
    r0, d0 = _dio(a, "returns"), _d(a, "returns")
    # DB: the host's world battle, the guest tapped from the verb on
    gat = cb.mark(guest)
    _state_every(guest, 1)
    _state_every(host, 1)
    tap = GuestTap(guest)
    tap.start()
    h0 = host.state                                       # [fix2] the start hold's release counters BEFORE the verb (DB's host half)
    try:
        host.world_battle(SCENE, group=GROUP, rand=True, timeout=BATTLE_S)
    except HarnessError as err:
        tap.stop()
        hang_check(host, "the host's world battle")
        rest(f"the host's world battle never came up ({str(err)[:200]})")
        return
    _state_every(host, 2)
    hsamples, _hit = cb.watch(host, lambda s: cb.path(s, "netsync.battle.host.start_hold.guest.boot_name") == "live",
                              HOLD_WAIT_S)
    booted_st = tap.wait_for(booted_world, 1.0)
    gsamples = []
    if booted_st is None:
        gsamples = tap.stop()                             # (it stayed on the world map: those samples judge DB)
        hang_check(guest, "the guest's boot")
        tap = None
    nonce = _host_nonce(hsamples)
    hrec = list(hsamples)

    def policy(s, slot):
        try:
            hrec.append(host.state)                       # the host's decode of the guest's control frame, each prompt
        except HarnessError:
            pass
        return {"command": "Attack"}
    try:
        host.fight(policy=policy, timeout=FIGHT_S, finish=True)
        host.wait_world(timeout=RETURN_S)
    except HarnessError as err:
        d.note(f"the host's fight / return raised: {str(err)[:200]}")
    if tap is not None:
        tap.wait_return(RET_WAIT_S)
        cb.hold_for(host, 0.5)                            # (a few more of the guest's frames after its return)
        gsamples = tap.stop()
    _state_every(guest, 2)
    glines = cb.new(guest, gat)
    try:
        h_end = host.state                                # [fix2] ...and after the fight (the hold decided at the battle's opening)
    except HarnessError:
        h_end = None
    hb_ok, hb_why = judge_host_hold(hrec, nonce, before=h0, after=h_end)
    gb_ok, gb_why = judge_guest_boot(boot_window(gsamples), booted_st, None, glines, nonce)
    check("S145-DB", gb_ok and hb_ok, f"GUEST {gb_why}; HOST {hb_why}")
    if booted_st is None:
        why = "no world diorama on the guest (DB): it stayed on the world map -- the digit panel"
        check("S145-DP", False, f"not reached: {why}; {judge_host_menu(hrec)[1]}")
        check("S145-DR", False, f"not reached: {why}")
        after = guest.state
    else:
        sv = cb.count(glines, "stock menu: the ready mirror is SERVING")
        hm_ok, hm_why = judge_host_menu(hrec)
        check("S145-DP", sv >= 1 and hm_ok, f"the guest's SERVING line {sv}x; {hm_why}")
        i0 = next((i for i, s in enumerate(gsamples) if booted_world(s)), 0)
        tail = gsamples[i0:]
        first = next((s for s in tail if on_world_free(s)), None)
        why = leave_why(tail, glines)
        settled = song_quiet(guest, guest.world_settle()) if guest.state.ui_state == "WorldHUD" else None   # [fix2] past the fades
        moved, adv, after = cw.hold_walk(guest, WALK_FRAMES) if settled is not None else (None, None, guest.state)
        check("S145-DR", *judge_guest_return(first, settled, a, r0, d0, why, pb.WB_LEAVE_WHYS, moved, adv, gsamples,
                                             pre_ticks=pre_boot_ticks(gsamples, a), probs=probs, booted=booted_st))
    # D3: coop_world_wait's (THE BRACKET LAW), then no second return counted on 300
    gbase = guest.state
    gat3 = cb.mark(guest)
    early = []
    take = cw._sampler(guest, early)
    try:
        cw.teleport_settle(host, ICE_TILE)
        host.wait_frames(cw.PROMPT_FRAMES)
        host.press("confirm")
        take()
        hst = cw._poll(host, lambda s: (take(), s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN)[1], cw.FIELD_S,
                       "the host on 300")
    except HarnessError as err:
        hst = None
        d.note(f"the host's entry raised: {str(err)[:200]}")
    if hst is None:
        check("S145-D3", False, f"not reached: the host never entered 300 (ui {host.state.ui_state!r}, field "
                                f"{host.state.field_id})")
        return
    samples, _hit = cb.watch(guest, lambda s: s.ui_state == "FieldHUD" and s.field_id == ICE_CAVERN, REJOIN_S)
    samples += cb.hold_for(guest, 1.5)
    seen = {s.frame for s in samples}
    samples = [s for s in early if s.frame not in seen] + samples
    lines3 = cb.new(guest, gat3)
    a_ok, a_why = cw.judge_rejoin_arm(samples, gbase, lines3, field=ICE_CAVERN, bracket=True)
    n_ok, n_why = cw.judge_rejoin_land(samples, gbase, lines3, field=ICE_CAVERN)
    r_ok, r_why = judge_rejoin_300(samples, after if after is not None else gbase, lines3)
    mir = _s(samples[-1], "mirroring") if samples else None
    check("S145-D3", a_ok and n_ok and r_ok and mir is True, f"ARM {a_why}; LAND {n_why}; NO SECOND RETURN {r_why}; "
                                                              f"mirroring {mir!r}")
