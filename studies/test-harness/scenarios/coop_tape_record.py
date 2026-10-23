"""R3 T2 -- THE HOST TAPE, the recording half of the solo two-role bench (studies/battle-coop/R3-SITTING-A-FIXES.md "T2"),
run unattended. [ff9mapkit netsync R3 T2]

THE GAP. No guest-side watcher, exit-ramp or mirror-gated behaviour can be benched in the selftest role: it returns
before the transport and DioramaTick exist, and IsMirroringStory needs a real socket. s119 (the diorama hold keyed on the
peer), s120 (the session grace) and s121 (the audible menu refusal) are all guest-side, so they are judged by REPLAYING a
recorded host into the desktop running as the guest (coop_cut_hold.py). This scenario makes that recording: the desktop as
the co-op HOST, tools/harness/coop_peer.py `serve-guest` standing in for the bridge on the game's RelayUrl port as its
fake guest, taping every frame the host sends.

THE BENCH.
  1. New Game, the party seeded through COOPPARTY (30604: +vivi +garnet +steiner -- a guest slot needs a member in slot
     1), field 250 (Evil Forest/Trail, sitting A's meeting field, warm), random encounters off (the free roam must stay
     free roam), and the STORY MARKER: gEventGlobal byte 1121 (bits 8968-8975, the campaign lane) poked to 0xA5 -- a
     value no New-Game save holds, so a guest reading it is reading the HOST's story (the roam leg's story-byte check).
  2. Memoria.ini [Netsync] (BACKED UP FIRST -- the MAIN repo's backups/ and the run dir; restored byte-exact in the
     `finally`): Enabled 1, Role host, RelayUrl ws://127.0.0.1:<COOP_PEER_PORT, 49201>, SessionCode ff9-T2BENCH1,
     GuestSlots 2, FollowHost 0, TargetField 0, StartHoldMs 8000. The engine hot-reloads it (mtime-gated, polled every
     2 s; a field load when no NetSyncClient exists yet), so the RUNNING game turns host; its config line is the proof.
  3. `py tools/harness/coop_peer.py serve-guest --port <port> --report live --tap <tape>` as a subprocess (stopped with
     CTRL_BREAK -> its own KeyboardInterrupt path, so the tape closes whole). Its fake guest answers at 30 Hz on the
     host's field and reports its diorama LIVE on every battle nonce: the s114 start hold releases at once, and slot 1
     stays GUEST-OWNED (the host's HUD skips it, G2) -- so on the replay the guest's ready mirror has a slot to serve, as
     in sitting A (the laptop's slot-1 window was up at the cut).
  4. COOP_TAPE_PRE_S (70) s of free roam -- the replay's pairing, mirror arm, S121 presses and the two roam cuts (20 s and
     40 s) all live here -- then `battle 67 -1 rand` from the field, fought COOP_TAPE_FIGHT_S (40) s with Defend (slots 0,
     2, 3; slot 1 is the guest's), then Attack to the win; the result screen confirmed through (its Hide is the end-leave's
     trigger); COOP_TAPE_POST_S (30) s back on 250 (the "still mirrored after the victory" window); the peer stopped.

WHY THIS BATTLE PATH (the publication gate). NetSyncBattle.Pump publishes the type-1 lane only for an OWN battle:
InOwnBattle needs EventEngine.gMode 2 or 4, which only EventEngine.StartEvents writes -- and HonoluluBattleMain skips
StartEvents under isDebug. So NetSyncDiorama.Boot / `netsync dioboot` (isDebug set) and any ~ menu debug fight never
reach NoteOwnBattleStart (no "battle intro:" line, no nonce, nothing on the wire). The harness `battle <scene> <group>
[rand]` verb (Ff9mkDebugMenu.HarnessBattle -> StartBattle) is NOT a debug fight: it performs exactly ENCOUNT2's writes
(btlSubMapNo, SetNextMap, isRandomEncounter, `isDebug = false`, nextMode 2, BackupPosObjData, attr |= 8) -- the field's
own encounter transition through the swirl, StartEvents, gMode 2 -- which is the publishing path every selftest own
battle in coop_battle_*.py already rides (there SelfTestPump is the publisher; here the real Pump is). `rand` (s111+)
makes it a random encounter, as sitting A's were; REC-B proves the publication rather than assuming it: the host's
NoteOwnBattleStart line ("battle intro: ...") AND the peer's decoded "host battle lane UP: nonce N map 67". Walking 250
until a random encounter would also publish, but at an unbounded time -- the tape's phases must land where the legs'
cuts are planned.

WHERE THE TAPE GOES. <the MAIN repo>/.harness-runs/coop-tapes/<stamp>-host<field>-s<stage>.f9tape (COOP_TAPE_DIR
overrides), plus latest.json there (written only when all five facts are on the tape: coop_cut_hold.py's default). Not
studies/test-harness/tapes/: the type-5 story snapshot (~2 KB) rides EVERY 33 ms write tick, so a ~3 min tape is 10-20
MB of binary; a tape replays exactly one engine build's wire; it is a run artifact, not source. .harness-runs/ is
gitignored, and the MAIN repo's copy outlives the worktree that recorded it (the worktree-parked-backups lesson).

THE FIVE CALIBRATION FACTS (REC-F1..F5, printed as notes): read back off the closed tape with coop_peer's codec -- the
five things a replay must find before coop_cut_hold's CAL leg can see its five lines:
  F1 PAIR    the host on field 250 >= 10 s before its battle          -> 'paired on the host's field (250)'
  F2 MIRROR  type-5 story frames from the first second, the marker    -> 'state-mirror ARMED'
  F3 BOOT    a type-1 run on one nonce, scene 67, command-gated caps  -> 'diorama BOOT scene=67'
  F4 LIVE    >= 20 s of live fight, the seq advancing, a player Ready -> 'diorama LIVE'
  F5 END     the end block terminal, the result screen at Hide, the host back on 250 -> the end-leave
Each leg's cut on THIS tape (or why the tape cannot carry it) is printed after them.

CHECKS (REC-*): SEAT (a seat run only) the party seat seated its party; P0 the port free and the peer listening; P1 the
host config applied live (the engine's own config line naming role=host and the bench code); P2 the host dialled the peer
(both sides' lines); M the marker reads 0xA5 on the host before the tape starts; B a REAL own battle PUBLISHED (above); W the fight ran >= FIGHT_S s, was won, and the host is
back on 250 with control; T the tape closed cleanly and reads back with no torn tail; F1-F5 the five facts; INI (final)
Memoria.ini restored byte-exact.

CALIBRATION. The recording is the INSTRUMENT, not a bench of s118-s121: the host side of the wire is v14 on every DLL from
s110 on, and the fake guest's LIVE report keeps every s114/s118 host rule out of the way. Expected red set on the deployed
s117 DLL: NONE. Each check fails when its fact is missing (REC-B on a debug-fight path, F4 on a short fight, F2 when the
mirror lane is off, P2 when a production bridge holds the port -- P0 then refuses before any edit). A tape recorded on
s117 replays into s117 and s121 guests alike (the wire is unchanged), which is what lets one tape calibrate red on s117
and judge green on s118-s121.

THE SEAT VARIANT ([ff9mapkit netsync s143] COOP_TAPE_SEAT=30607 or 30608): after the COOPPARTY seed the host warps to that
PARTY SEAT (studies/battle-coop/bench/plantbrain.field.toml -- field 257's [Blank, Zidane, Vivi, Steiner] -- or
forestexit.field.toml -- field 261's [Garnet, Zidane, Vivi, Steiner]; its Main_Init rebuilds the party), then to field 250
as always: GuestSlots 2 now lands on the host's LEADER (Zidane, party slot 1), so the tape is a REAL host's wire where the
s143 leader guard moves something -- its section 8 must read Vivi (`coop_peer.py dress --ghost-as auto --guest-slots 2
--leader 0`: 08 00 01; an s141 host ships Zidane, 62 00 00) and its type-1 header must offer Vivi's btl index (`coop_peer.py
offer --want 4`; an s141 host offers 2). The seat tape is named `-seat<id>` and NEVER moves latest.json (the cut legs keep
the COOPPARTY tape). The seats are NEW ids (their first deploy needs a relaunch -- cal143.example.sh). REC-SEAT FAILS CLOSED
(review s143 rharness-1), before any Memoria.ini edit and before a tape exists: the warp refused (unregistered), never on
the seat, or the RAW party (`netsync.dress.party`) not the seat's toml [party] folded over the party before it
(coop_leader_guard.toml_party + battlewire.seat_after, read_oracle's arithmetic) -- a stale or wrong seat would otherwise
record a `-seat` tape whose `offer --want 4` red looks exactly like the predicted s141 calibration red. Every run, seat or
not, then warps to field 250 if it is not there (COOPPARTY unregistered leaves the host on the New-Game field: review s143
rfield-1).

THE WORLD VARIANT ([ff9mapkit netsync s144] COOP_TAPE_WORLD=1): a HOST-ON-WORLD tape for coop_world_wait.py's T2 world-wait
leg. The host stands on 6603 FARSHORE (the kit's FF9CustomMap-world landing: re-read its registration first) instead of 250
for COOP_TAPE_PRE_S (25 here) s -- the replay's pairing and the mirror's arm --, walks out of its door the proven way
(coop_world_wait.walk_out: calibrate_axes with the door quad a hazard, walk_to inside it, wait_world: world 9011 at the
landing (68, -444)) and STAYS on the world map COOP_TAPE_WORLD_S (90) s, encounters off, no battle -- then the peer is
stopped. Its checks: REC-P0 / P1 / P2 / M as ever, REC-WX the walk out landed on 9011, REC-WS the host stayed on the world
map (WorldHUD on every read, the battle epoch unmoved), REC-T, and the world facts REC-WF1 (the host on 6603 >= 10 s before
its exit), REC-WF2 (the story lane with the marker), REC-WF3 (off-field >= 60 s with section 7 riding) --
_coop_peer_bench.world_tape_facts --, REC-INI. The tape is named `-world-`, lands in its OWN dir (COOP_TAPE_DIR; default
<main repo>/.harness-runs/coop-tapes/world) and moves only that dir's latest-world.json, NEVER latest.json. The recorder is
the instrument: its b6 is not one of its checks -- `py tools/harness/coop_peer.py where <tape> --want world` (an s144 host)
or `--want none` (an s143 host: the calibration) is the tape's verdict, run by cal144 / full144.

THE WORLD-BATTLE VARIANT ([ff9mapkit netsync s145] COOP_TAPE_WORLD_BATTLE=1): the T2 tape for coop_world_battle.py's world-battle
leg (studies/world-coop/S145-DESIGN.md "The bench"), recorded on the LIVE s144 host -- it needs only s144 features (the world battle
verb, b6). The host stands on 6603 COOP_TAPE_PRE_S (25) s -- the guest pairs there --, walks out the proven way (coop_world_wait.
walk_out), then DWELLS on the world map COOP_TAPE_WB_DWELL_S (90) s -- PLANNED for the guest: its waiting line on 6603 (+ the
old-host debounce), its own walk out (calibrate + walk_to + the world's load), the freeze and the bench's setup on the world map
(the tile teleport, the camera turn, snapshot A) all fit, with room (_coop_peer_bench.WB_DWELL_NEED_S = 75: the leg's plan refuses
a shorter dwell) --, then `battle 67 0 rand` on WorldHUD (Session.world_battle: the native world encounter start, a random
encounter), fought COOP_TAPE_WB_FIGHT_S (25) s with Defend (the guest's boot, its LIVE latch and a served stock menu inside it;
_coop_peer_bench.WB_LIVE_NEED_S = 15) then Attack to the win, the result screen confirmed through, back on the world map where it
fought (the stock world battle's warm return), and STAYS there COOP_TAPE_WB_POST_S (30) s (the guest's leave, warm return and
post-return witnesses; WB_AFTER_NEED_S = 25) -- [ff9mapkit netsync s145 bench] then, COOP_TAPE_WB_ENTER=1 (the default), ENTERS
the stock Ice Cavern (coop_world_wait's ICE_TILE teleport, its prompt's frames, Confirm -> field 300: round 8's lane) and stands on
300 COOP_TAPE_WB_ENTER_S (15) s (the replayed guest rejoins 300 from the world map after its warm return: coop_world_battle.py's
WB-300; _coop_peer_bench.WB_ENTER_NEED_S = 8) -- then the peer is stopped. Its checks: REC-P0 / P1 / P2 / M as ever, REC-WX the walk
out, REC-WD the dwell (WorldHUD on every read, the battle epoch unmoved), REC-WB the world battle PUBLISHED (the peer's 'host
battle lane UP: nonce N map 67' and the host's intro line), REC-WW won and back on WorldHUD within ROUTE_TOL of where it fought,
REC-WP the stay (WorldHUD on every read, no second battle, no field), REC-WE the entry (FieldHUD 300, held ENTER_S; only with
COOP_TAPE_WB_ENTER), REC-T, the five facts REC-WBF1..5
(_coop_peer_bench.world_battle_tape_facts: the pairing, the story, the dwell, a world-map battle -- b6 before and after it, its
live stretch --, the stay after it), REC-INI. The tape is named `-world-battle-`, lands in its OWN dir (COOP_TAPE_DIR; default
<main repo>/.harness-runs/coop-tapes/world-battle) and moves only that dir's latest-world-battle.json -- never latest.json or
latest-world.json. Its verdict beside the recorder's: `py tools/harness/coop_peer.py where <tape> --want world-battle`.

THE HAND RECORDING (a world-map victory for coop_cut_hold's s120-world leg, which a field-250 tape cannot carry): with the
desktop's [Netsync] set to the host values above by hand, run
    py tools/harness/coop_peer.py serve-guest --report live --tap <tape>.f9tape
play to a WORLD-MAP fight, win it, stay on the world map >= 20 s, Ctrl+C; then, in ONE launch (a world tape has no field
for its CAL leg to pair on, so the leg runs forced -- coop_cut_hold.py's RUN notes):
    COOP_CUT_FORCE=1 COOP_TAPE=<tape> COOP_CUT_LEG=s120-world py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py

RUN (the game must be closed; play.py launches it; the production bridge must NOT be running on 49201):
    py tools/play.py studies/test-harness/scenarios/coop_tape_record.py
    COOP_TAPE_FIGHT_S=45 py tools/play.py studies/test-harness/scenarios/coop_tape_record.py      (a longer fight)
  PowerShell (a `$env:` value persists in that shell -- clear it, or every later launch inherits it):
    $env:COOP_TAPE_FIGHT_S='45'; py tools/play.py studies/test-harness/scenarios/coop_tape_record.py
    Remove-Item Env:COOP_TAPE_FIGHT_S -ErrorAction SilentlyContinue
then the guest legs, in order (coop_cut_hold.py): COOP_CUT_LEG=cal first -- nothing else judges until it passes.
AFTER AN ABORTED RUN (anything that skips the `finally`): the install's Memoria.ini may still say Role host /
SessionCode ff9-T2BENCH1. Compare it with the newest <main repo>/backups/Memoria.ini.pre-coop-tape-record.<stamp> and copy
that back if they differ (the run dir keeps a second copy). [ff9mapkit netsync R3 resume]
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _coop_peer_bench as pb                              # noqa: E402 - the T2 two-role bench helpers

HarnessError = cb.HarnessError

FIELD = pb.BENCH_FIELD
SCENE = pb.BENCH_SCENE
#: [ff9mapkit netsync s144] THE WORLD VARIANT (see its paragraph): the host on 6603, then out on the world map -- on a
#: PRIVATE port (pb.WORLD_PORT: the s144 legs never bind the owner's 49201; this run writes its own RelayUrl)
WORLD_TAPE = pb.env_flag("COOP_TAPE_WORLD")
#: [ff9mapkit netsync s145] THE WORLD-BATTLE VARIANT (see its paragraph): out on the world map, a planned dwell, a world battle
#: won, a stay -- on the same private port as the world variant
WORLD_BATTLE_TAPE = pb.env_flag("COOP_TAPE_WORLD_BATTLE")
ANY_WORLD = WORLD_TAPE or WORLD_BATTLE_TAPE
PORT = pb.env_int("COOP_PEER_PORT", pb.WORLD_PORT if ANY_WORLD else pb.DEFAULT_PORT)
CODE = pb.BENCH_CODE
WORLD_FIELD = pb.WORLD_TAPE_FIELD
WORLD_S = pb.env_float("COOP_TAPE_WORLD_S", 90.0)
PRE_S = pb.env_float("COOP_TAPE_PRE_S", 25.0 if ANY_WORLD else 70.0)
#: [ff9mapkit netsync s145] the world-battle variant's dwell, fight and stay (s); its battle (`battle 67 0 rand` on WorldHUD)
WB_DWELL_S = pb.env_float("COOP_TAPE_WB_DWELL_S", 90.0)
WB_FIGHT_S = pb.env_float("COOP_TAPE_WB_FIGHT_S", 25.0)
WB_POST_S = pb.env_float("COOP_TAPE_WB_POST_S", 30.0)
WB_SCENE, WB_GROUP = 67, 0
#: ...and the stock world battle's warm return: back on WorldHUD within this of where it fought (world units)
WB_RETURN_TOL = 4.0
#: [ff9mapkit netsync s145 bench] ...then the host's entry into the Ice Cavern after the stay (the replayed guest's rejoin: WB-300),
#: and how long it stands on 300 before the peer stops
WB_ENTER = pb.env_int("COOP_TAPE_WB_ENTER", 1) != 0
WB_ENTER_S = pb.env_float("COOP_TAPE_WB_ENTER_S", 15.0)
ENTER_FIELD_S = 20.0                     # the Confirm on the tile -> FieldHUD 300 (coop_world_wait.FIELD_S)
FIGHT_S = pb.env_float("COOP_TAPE_FIGHT_S", 40.0)
POST_S = pb.env_float("COOP_TAPE_POST_S", 30.0)
GUEST_SLOTS = pb.env_int("COOP_TAPE_GUEST_SLOTS", 2)
#: [ff9mapkit netsync s143] the party seat warped to after the COOPPARTY seed (0 = none; see THE SEAT VARIANT)
SEAT = pb.env_int("COOP_TAPE_SEAT", 0)
SEATS = {0: "COOPPARTY", 30607: "COOPPBRAIN [Blank, Zidane, Vivi, Steiner]", 30608: "COOPFOREST [Garnet, Zidane, Vivi, Steiner]"}

CATALOG = {
    "REC-P0": f"the bench port {PORT} is free and `coop_peer serve-guest` listens on it (no production bridge there)",
    "REC-P1": f"the HOST config applied live: the engine's own line 'config enabled=True role=host ... relay=ws://127.0.0.1:"
              f"{PORT} code={CODE}'",
    "REC-P2": f"the HOST game dialled the peer: coop-peer 'HOST game connected (session {CODE})' and the engine's 'relay "
              f"connected ...?role=host'",
    "REC-M": f"the story marker: gEventGlobal byte {pb.MARKER_BYTE} reads 0x{pb.MARKER_VALUE:02X} on the host (its watched "
             "bits) before the tape starts",
    "REC-B": f"a REAL own battle on field {FIELD} (`battle {SCENE} -1 rand`: ENCOUNT2's writes, isDebug cleared) is "
             "PUBLISHED: the host's 'battle intro:' line (NoteOwnBattleStart) and the peer's 'host battle lane UP: nonce N "
             f"map {SCENE}'",
    "REC-W": f"the fight ran >= COOP_TAPE_FIGHT_S ({FIGHT_S:g}) s, was WON, and the host is back on field {FIELD} with "
             "control (the warm return)",
    "REC-T": "the tape closed cleanly (the peer's own KeyboardInterrupt path wrote its 'tape ...: N record(s)' line) and "
             "reads back with no torn tail",
    "REC-F1": "F1 PAIR: the host on field 250 >= 10 s before its battle (the replay's 'paired on the host's field')",
    "REC-F2": "F2 MIRROR: type-5 story frames from the first second, carrying the marker (the replay's 'state-mirror ARMED')",
    "REC-F3": "F3 BOOT: a type-1 run on one nonce, scene 67, command-phase-gated caps (the replay's 'diorama BOOT')",
    "REC-F4": "F4 LIVE: >= 20 s of live fight, the seq advancing, a player Ready (the replay's 'diorama LIVE')",
    "REC-F5": "F5 END: the end block terminal, the result screen at Hide, the host back on 250 (the replay's end-leave)",
    "REC-INI": "Memoria.ini restored byte-exact (sha256) after the run -- the install is shared",
}
#: [ff9mapkit netsync s143] a SEAT run's own check (review s143 rharness-1) -- in the ledger only when COOP_TAPE_SEAT is set
SEAT_CATALOG = {
    "REC-SEAT": "the party seat SEATED its party before any edit: the warp landed on the seat and the RAW party "
                "(`netsync.dress.party`) == the seat toml's [party] over the party before it (coop_leader_guard.toml_party "
                "+ battlewire.seat_after), a change -- else nothing is edited and no `-seat` tape is made",
}


#: [ff9mapkit netsync s144] the WORLD variant's checks (COOP_TAPE_WORLD=1): the battle facts give way to the world's
WORLD_CATALOG = {
    **{k: CATALOG[k] for k in ("REC-P0", "REC-P1", "REC-P2", "REC-M")},
    "REC-WX": f"the host walked out of {WORLD_FIELD} onto world 9011 at the landing (coop_world_wait.walk_out: the proven "
              "route)",
    "REC-WS": f"the host stayed on the world map COOP_TAPE_WORLD_S ({WORLD_S:g}) s: WorldHUD on every read, the battle epoch "
              "unmoved (encounters off)",
    "REC-T": CATALOG["REC-T"],
    "REC-WF1": f"WF1 PAIR: the host on {WORLD_FIELD} >= 10 s before its world exit, no battle there (the replay's pairing)",
    "REC-WF2": "WF2 STORY: type-5 story frames from the first seconds, carrying the marker",
    "REC-WF3": "WF3 WORLD: the host off-field >= 60 s after its exit, section 7 riding its state frames (the waiting line's "
               "input; its b6 is `coop_peer.py where`'s verdict, not the recorder's)",
    "REC-INI": CATALOG["REC-INI"],
}


#: [ff9mapkit netsync s145] the WORLD-BATTLE variant's checks (COOP_TAPE_WORLD_BATTLE=1)
WORLD_BATTLE_CATALOG = {
    **{k: CATALOG[k] for k in ("REC-P0", "REC-P1", "REC-P2", "REC-M")},
    "REC-WX": WORLD_CATALOG["REC-WX"],
    "REC-WD": f"the DWELL: the host on the world map COOP_TAPE_WB_DWELL_S ({WB_DWELL_S:g}) s before its battle -- WorldHUD on every "
              "read, the battle epoch unmoved (the guest pairs, walks out and settles inside it)",
    "REC-WB": f"a REAL own WORLD battle (`battle {WB_SCENE} {WB_GROUP} rand` on WorldHUD: Session.world_battle) is PUBLISHED: the "
              f"host's 'battle intro:' line and the peer's 'host battle lane UP: nonce N map {WB_SCENE}'",
    "REC-WW": f"the fight ran >= COOP_TAPE_WB_FIGHT_S ({WB_FIGHT_S:g}) s, was WON, and the host is back on WorldHUD within "
              f"{WB_RETURN_TOL:g}u of where it fought (the stock world battle's warm return)",
    "REC-WP": f"the STAY: the host on the world map COOP_TAPE_WB_POST_S ({WB_POST_S:g}) s after the battle -- WorldHUD on every "
              "read, no second battle, no field",
    # [ff9mapkit netsync s145 bench] the entry after the stay (only with COOP_TAPE_WB_ENTER, the default)
    **({"REC-WE": f"THE ENTRY: the host on the Ice Cavern's world tile, Confirm -> FieldHUD {pb.WB_ENTER_FIELD} within "
                  f"{ENTER_FIELD_S:g} s, then on it COOP_TAPE_WB_ENTER_S ({WB_ENTER_S:g}) s (the replayed guest's rejoin)"}
       if WB_ENTER else {}),
    "REC-T": CATALOG["REC-T"],
    "REC-WBF1": "WB1 PAIR: the host on 6603 >= 10 s before its world exit, no battle there",
    "REC-WBF2": "WB2 STORY: type-5 story frames from the first seconds, carrying the marker",
    "REC-WBF3": "WB3 DWELL: the host off-field >= 75 s from its exit to its world battle, b6 riding",
    "REC-WBF4": "WB4 BATTLE: a WORLD-MAP battle (b6 before and after it) published with command-gated caps, >= 15 s live, the "
                "seq advancing, a player Ready",
    "REC-WBF5": "WB5 AFTER: its end terminal, the result screen at Hide, then the host on the world map (b6) >= 25 s before any "
                "field -- a field after that stay only the Ice Cavern (300), held >= 8 s ([s145 bench] the rejoin)",
    "REC-INI": CATALOG["REC-INI"],
}


def _catalog(seat: int, world: bool | None = None, world_battle: bool | None = None) -> dict:
    """The run's checks: CATALOG, plus REC-SEAT on a seat run; [s144] WORLD_CATALOG on a world run; [s145]
    WORLD_BATTLE_CATALOG on a world-battle run."""
    if WORLD_BATTLE_TAPE if world_battle is None else world_battle:
        return dict(WORLD_BATTLE_CATALOG)
    if WORLD_TAPE if world is None else world:
        return dict(WORLD_CATALOG)
    return {**CATALOG, **SEAT_CATALOG} if seat else dict(CATALOG)

HOST_VALUES = {"Enabled": "1", "Role": "host", "RelayUrl": f"ws://127.0.0.1:{PORT}", "SessionCode": CODE,
               "GuestSlots": str(GUEST_SLOTS), "FollowHost": "0", "TargetField": "0", "StartHoldMs": "8000"}


class _Ctx:
    def __init__(self, field: int):
        self.field = field
        self.guard = None
        self.peer = None
        self.tape = None
        self.eng = None
        self.stage = 0
        self.host_s118 = False


def _run_dir(g) -> Path:
    return Path(getattr(g, "scenario_dir", None) or g.run_dir)


def _host_setup(g, led: cb.Ledger, ctx: _Ctx) -> bool:
    """New Game, the COOPPARTY seed, [the party seat], then field ``ctx.field`` -- ALWAYS: seed_party returns WITHOUT a warp
    when COOPPARTY is unregistered or the registrations cannot be read, and a tape recorded off the bench field is unusable
    (review s143 rfield-1). [ff9mapkit netsync s143] A seat that did not seat its party fails closed HERE (REC-SEAT), before
    any Memoria.ini edit and before a tape exists (review s143 rharness-1). False = the run stops."""
    g.newgame()
    g.note(cb.seed_party(g, back_to=ctx.field))
    if SEAT:
        ok, why = _seat(g, SEAT)
        led.check("REC-SEAT", ok, why)
        if not ok:
            led.close(f"the party seat {SEAT} did not seat its party -- nothing was edited, no `-seat` tape was made")
            return False
    if g.state.field_id != ctx.field:
        g.warp(ctx.field)
    return True


def seat_party(seat: int, base) -> tuple:
    """[ff9mapkit netsync s143] (the toml read only) The RAW party the seat's Main_Init leaves over ``base`` (the RAW party
    before the warp): its [party] block through coop_leader_guard.toml_party (the kit's own content.party) folded by
    battlewire.seat_after -- read_oracle's arithmetic. (party | None, how)."""
    import coop_leader_guard as lg                     # beside this file (the scenario dir is on sys.path)
    toml = lg.TOMLS.get(seat)
    if toml is None:
        return None, f"no seat toml for {seat}"
    try:
        (rm, add), _old = lg.toml_party(toml)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, ImportError) as err:
        return None, f"{toml.name}: {type(err).__name__}: {str(err)[:160]}"
    want = lg._bw().seat_after(base, rm, add)
    if want is None:
        return None, f"the RAW party before the seat (netsync.dress.party) is unreadable: {base!r}"
    return want, f"{toml.name}: remove {list(rm)}, add {list(add)} over {list(base)}"


def _seat(g, seat: int) -> tuple:
    """[ff9mapkit netsync s143] Warp to the party seat (its Main_Init rebuilds the party: every RemoveParty, then the adds in
    order) and judge it SEATED: (ok, detail). Red when the seat's party cannot be computed, the warp is refused (an
    unregistered seat: a NEW id needs a relaunch after its first deploy), the host never stands on it, or the RAW party is
    not the toml's (a stale deploy) or is unchanged by it."""
    base = cb.path(g.state, "netsync.dress.party")
    want, how = seat_party(seat, base)
    if want is None:
        return False, f"the seat's party cannot be computed ({how}) -- the seat was not entered"
    try:
        g.warp(seat)
    except HarnessError as err:
        return False, f"the warp to the party seat {seat} was refused ({str(err)[:240]})"
    st = cb.poll(g, lambda s: s.field_id == seat and s.on_field, 30.0, f"the party seat {seat}")
    if st is None:
        return False, f"never on the party seat {seat} (field {g.state.field_id})"
    st = cb.poll(g, lambda s: cb.path(s, "netsync.dress.party") == want, 5.0, f"the seat's party {want}")
    g.wait_frames(45)                                  # the rest of the seat's Main_Init
    got = cb.path(st or g.state, "netsync.dress.party")
    changed = want != list(base)
    ok = got == want and changed
    return ok, (f"party seat {seat}: netsync.dress.party {got!r}, the seat's toml says {want} ({how})"
                + ("" if changed else " -- the SAME as before the seat: nothing proves its Main_Init ran")
                + (f" -- GuestSlots {GUEST_SLOTS} lands on the leader there" if ok else " -- STALE or wrong seat"))


def _config_applied(lines, role: str) -> list:
    return pb.hits(lines, "config", pred=lambda m: m.group(1) == "True" and m.group(2) == role
                   and m.group(5) == f"ws://127.0.0.1:{PORT}" and m.group(6) == CODE)


def run(g, field: int = FIELD):
    led = cb.Ledger(g, _catalog(SEAT), finals=("REC-INI",))
    ctx = _Ctx(WORLD_FIELD if ANY_WORLD else field)        # [ff9mapkit netsync s144/s145] a world tape's host stands on 6603
    try:
        _run(g, led, ctx)
    except HarnessError as err:
        g.note(f"the recording raised: {str(err)[:400]}")
        led.close(f"the recording raised before this check: {str(err)[:200]}")
    finally:
        _teardown(g, led, ctx)
        led.close(final=True)


def _teardown(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """The peer FIRST (the tape closes; and a restored owner config that dials the same port must find nobody), then the
    ini, then the logs."""
    if ctx.peer is not None and ctx.peer.how_ended is None:
        g.note(f"coop_peer serve-guest: {ctx.peer.stop()}")
    if ctx.guard is not None:
        ok, why = ctx.guard.restore()
        led.check("REC-INI", ok, why)
    else:
        led.check("REC-INI", True, "Memoria.ini was never edited (the run stopped before the edit)")
    g.note(f"Memoria.log archived: {cb.archive_log(g, 'coop-tape-record')}")


def _run(g, led: cb.Ledger, ctx: _Ctx) -> None:
    cb.provenance(g)
    g.note(f"R3 T2 tape record: host on field {ctx.field}, peer port {PORT}, pre {PRE_S:g} s / fight {FIGHT_S:g} s / "
           f"post {POST_S:g} s, GuestSlots {GUEST_SLOTS}, party seat {SEATS.get(SEAT, SEAT)}")
    if SEAT not in SEATS:
        led.close(f"COOP_TAPE_SEAT={SEAT} is not a party seat ({sorted(k for k in SEATS if k)}) -- nothing was edited")
        return
    if SEAT and ANY_WORLD:
        led.close("COOP_TAPE_SEAT and COOP_TAPE_WORLD / COOP_TAPE_WORLD_BATTLE are separate variants -- nothing was edited")
        return
    if WORLD_TAPE and WORLD_BATTLE_TAPE:                     # [ff9mapkit netsync s145]
        led.close("COOP_TAPE_WORLD and COOP_TAPE_WORLD_BATTLE are separate variants -- nothing was edited")
        return
    if ANY_WORLD and PORT == pb.OWNER_PORT:
        led.check("REC-P0", False, f"COOP_PEER_PORT={PORT} is the owner's bridge port: the world variant never binds it")
        led.close("the bench port is the owner's -- nothing was edited")
        return
    free, why = pb.port_free(PORT)
    if not free:
        led.check("REC-P0", False, why)
        led.close(f"the bench port is taken -- nothing was edited ({why[:160]})")
        return
    # 1. the host's game
    if not _host_setup(g, led, ctx):
        return
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]}) -- a random battle may interrupt the free roam")
    g.poke(pb.MARKER_BYTE, pb.MARKER_VALUE)
    g.watch(*(pb.MARKER_BYTE * 8 + b for b in range(8)))
    st = cb.poll(g, lambda s: pb.marker_value(s) == pb.MARKER_VALUE, 5.0, "the story marker on the watched bits")
    st = st or g.state
    led.check("REC-M", pb.marker_value(st) == pb.MARKER_VALUE,
              f"byte {pb.MARKER_BYTE} reads {pb.marker_value(st)!r} on field {st.field_id}")
    ctx.stage = pb.engine_stage(st)
    if ANY_WORLD and cb.has(st, cb.R3_PROBES[144]):
        ctx.stage = 144                     # [ff9mapkit netsync s144] a world tape is named by the host's s144 (b6) stage
    if ANY_WORLD and cb.has(st, cb.R3_PROBES[145]):
        ctx.stage = 145                     # [ff9mapkit netsync s145] ...or s145's (the host side of the wire is s144's either way)
    ctx.host_s118 = pb.has(st, "netsync.battle.host.handback.refused_report")
    g.note(f"the engine reads as s{ctx.stage or '<117'} (guest ladder){'; s118 host keys present' if ctx.host_s118 else ''}"
           f"; {cb.stage_note(st)}")
    # 2. the ini, then wait for the engine's own config line
    ctx.eng = pb.EngineLog(g.engine_log())
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", HOST_VALUES, label="coop-tape-record",
                            run_dir=_run_dir(g))
    try:
        g.note(ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("REC-P1", False, f"the edit failed: {err}")
        led.close(f"Memoria.ini could not be edited ({str(err)[:160]})")
        return
    applied = _wait_config(g, ctx, "host")
    led.check("REC-P1", bool(applied), pb.show(applied) if applied else
              f"no matching config line in Memoria.log after the edit (and a field reload); config lines seen: "
              f"{pb.show(pb.hits(ctx.eng.lines(), 'config'))}")
    if not applied:
        led.close("the engine never took the host config -- is this the Memoria.ini the game reads (cwd = the game root)?")
        return
    # 3. the peer
    stamp = time.strftime("%Y%m%d-%H%M%S")
    tdir = (pb.world_battle_tape_dir() if WORLD_BATTLE_TAPE else      # [ff9mapkit netsync s145] a world-battle tape's own home
            pb.world_tape_dir() if WORLD_TAPE else pb.tape_dir())        # [ff9mapkit netsync s144] a world tape's own home
    tdir.mkdir(parents=True, exist_ok=True)
    ctx.tape = tdir / (f"{stamp}-host{ctx.field}{f'-seat{SEAT}' if SEAT else ''}{'-world' if WORLD_TAPE else ''}"
                       f"{'-world-battle' if WORLD_BATTLE_TAPE else ''}-s{ctx.stage or 0}.f9tape")
    rd = _run_dir(g)
    ctx.peer = pb.PeerProc("serve-guest", ["--port", PORT, "--report", "live", "--tap", ctx.tape, "--status", "5"],
                           log_path=rd / "coop_peer-serve-guest.log", out_path=rd / "coop_peer-serve-guest.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0)
    err = ctx.peer.first(pb.PEER["error"])
    led.check("REC-P0", up is not None and err is None,
              (up[1] if up else f"no listening line; tail: {ctx.peer.tail()}") + (f"; {err[1]}" if err else ""))
    if up is None:
        led.close("coop_peer serve-guest never listened")
        return
    conn = ctx.peer.wait_for(pb.PEER["host_connected"], 20.0)
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "host" and m.group(2) == CODE)
    led.check("REC-P2", conn is not None and conn[2].group(1) == CODE and bool(relay),
              f"peer: {conn[1] if conn else 'no HOST connection'}; engine: {pb.show(relay)}")
    if conn is None:
        led.close("the host game never dialled the peer")
        return
    if WORLD_TAPE:                          # [ff9mapkit netsync s144] the world variant: out on the world map, no battle
        _world(g, led, ctx, conn)
        return
    if WORLD_BATTLE_TAPE:                   # [ff9mapkit netsync s145] the world-battle variant: out, a dwell, a world battle
        _world_battle(g, led, ctx, conn)
        return
    # 4. the free roam, the battle, the post-battle roam
    _hold_until(ctx, conn[0], PRE_S)
    _note_host_ghost(g)                     # [ff9mapkit netsync s139] the transport site's tuple: a NOTE, no check
    _battle(g, led, ctx)
    g.note(f"post-battle free roam: {POST_S:g} s on field {g.state.field_id}")
    time.sleep(POST_S)
    g.note(f"coop_peer serve-guest: {ctx.peer.stop()}")
    _facts(g, led, ctx)


def _note_host_ghost(g) -> None:
    """[ff9mapkit netsync s139] A NOTE (never a check: the recorder's calibration is unchanged) of the HOST's own ghost of the
    fake guest while it roams -- the transport site (HostDress behind GhostGuard on the fake guest's wire body, which
    mirrors the host's model: 98) -- for a reader to judge against battlewire's host rule and the install oracle
    (coop_dress_wire.py's G9d-f are that judge on a real guest, at three GuestSlots). An engine before s138 publishes no
    `netsync.dress`."""
    gh = cb.path(g.state, "netsync.dress.ghost")
    if not isinstance(gh, dict):
        g.note("s139 transport site: the host publishes no `netsync.dress.ghost` (an engine before s138)")
        return
    g.note("s139 transport site -- the host's ghost of the fake guest: "
           + ", ".join(f"{k}={gh.get(k)!r}" for k in ("model", "rig", "geo", "body", "clip", "playing", "mode")
                       if k in gh))


def _note_section8(g, ctx: _Ctx, cp) -> None:
    """[ff9mapkit netsync s139] NOTES (never a check) of the tape's section 8 -- coop_peer's `dress` report with each host
    frame's own party (its section 1) and the host's [Netsync] GhostAs read READ-ONLY: what `py tools/harness/coop_peer.py
    dress <tape> --ghost-as <it> --guest-slots 2` prints. An s138-or-older host's tape reads "none"."""
    ghost_as = (cb.ini_value(g, "Netsync", "GhostAs") or "").strip()
    lead = cb.guard_leader(g.state)                    # [ff9mapkit netsync s143] an s143 host's leader guard (-1 before)
    try:
        ok, lines = cp.tape_dress_lines(ctx.tape, cp.frame_expect(ghost_as, GUEST_SLOTS, leader=lead))
    except Exception as err:                 # noqa: BLE001 -- a note only
        g.note(f"section 8: the tape's dress read raised {type(err).__name__}: {err}")
        return
    g.note(f"SECTION 8 on {ctx.tape.name} (GhostAs {ghost_as!r}, GuestSlots {GUEST_SLOTS}, leader {lead}): "
           f"{'held' if ok else 'NOT held'}")
    for line in lines[1:]:
        g.note("  " + line)


def _wait_config(g, ctx: _Ctx, role: str, first: float = 6.0, second: float = 10.0) -> list:
    """The engine's config line for ``role`` + the bench relay/code. A running NetSyncClient polls Memoria.ini every 2 s;
    with none yet (the owner's Enabled=0), only a field load's Ensure() reads it -- so one same-field warp, then wait."""
    deadline = time.time() + first
    while time.time() < deadline:
        found = _config_applied(ctx.eng.lines(), role)
        if found:
            return found
        time.sleep(0.25)
    g.note("no config line within the poll window -- reloading the field (Ensure reads the ini at a field load)")
    try:
        g.warp(ctx.field)
    except HarnessError as err:
        g.note(f"the reload warp failed: {str(err)[:200]}")
    deadline = time.time() + second
    while time.time() < deadline:
        found = _config_applied(ctx.eng.lines(), role)
        if found:
            return found
        time.sleep(0.25)
    return []


def _hold_until(ctx: _Ctx, base, seconds: float) -> None:
    """Idle until ``seconds`` after ``base`` (the peer's HOST-connected stamp), reading the peer's log as it grows."""
    end = base + _dt.timedelta(seconds=seconds)
    while _dt.datetime.now() < end and ctx.peer.alive():
        ctx.peer.lines()
        time.sleep(0.5)


def _battle(g, led: cb.Ledger, ctx: _Ctx) -> None:
    st = g.state
    rand = bool(getattr(st, "coop_intro_mirror", False))
    if not rand:
        g.note("the engine publishes no `netsync.diorama.intro` (pre-s111): the battle boots NON-random")
    at = _dt.datetime.now()
    try:
        g.start_battle(SCENE, group=-1, rand=rand)
    except HarnessError as err:
        led.check("REC-B", False, f"`battle {SCENE} -1{' rand' if rand else ''}` failed: {str(err)[:300]}")
        led.unreached(("REC-W",), "no battle")
        return
    lane = ctx.peer.wait_for(pb.PEER["host_lane_up"], 15.0, after=at)
    intro = pb.hits(ctx.eng.lines(), "intro", after=at)
    ok = lane is not None and int(lane[2].group(2)) == SCENE and bool(intro)
    led.check("REC-B", ok, f"peer: {lane[1] if lane else 'no host battle lane'}; host: {pb.show(intro)}")
    st = g.state
    g.note(f"battle up: party slots {cb.player_slots(st)}, enemies "
           f"{[u.get('name') for u in cb.units(st, player=False)]}; slot 1 is the fake guest's (GuestSlots {GUEST_SLOTS}, "
           "reported LIVE): the host's HUD skips it")
    t0 = time.time()

    def policy(s, slot):
        # Defend until FIGHT_S has run (the tape needs a LONG live fight: the s119 / s120 cuts land inside it), healing a
        # member under 45% with a Potion (a New-Game party at level 1 must outlast ~45 s of Goblin hits), then Attack
        if time.time() - t0 >= FIGHT_S:
            return {"command": "Attack"}
        try:
            menu = g.menus(slot)
        except HarnessError:
            return None
        names = {c.get("name") for c in (menu.get("commands") or []) if c.get("offered", True)}
        items = {i.get("name") for i in (menu.get("items") or [])}
        hurt = [u for u in cb.units(s, player=True) if u.get("alive") and int(u.get("hp_max") or 0) > 0
                and int(u.get("hp") or 0) * 100 < int(u.get("hp_max")) * 45]
        if hurt and "Potion" in items:
            return {"command": "Potion"}
        return {"command": "Defend"} if "Defend" in names else None

    try:
        result = g.fight(policy=policy, timeout=FIGHT_S + 180.0, max_turns=240)
    except HarnessError as err:
        led.check("REC-W", False, f"the fight raised: {str(err)[:300]}")
        return
    lf = getattr(g, "last_fight", {}) or {}
    back, why = cb.arrive(g, ctx.field, timeout=90.0)
    won = result in (1, 2)
    long_enough = float(lf.get("seconds", 0.0)) >= FIGHT_S - 1.0
    led.check("REC-W", won and long_enough and back,
              f"result {result} ({lf.get('name')}), {lf.get('seconds')} s, {lf.get('turns')} turn(s); "
              f"{'back on ' + str(ctx.field) if back else why}")


def _facts(g, led: cb.Ledger, ctx: _Ctx) -> None:
    summary = ctx.peer.first(pb.PEER["tape_summary"])
    try:
        cp = pb.coop_peer_module()
        header, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                 # noqa: BLE001 -- the reason goes into the checks
        led.check("REC-T", False, f"the tape does not read back: {err}")
        led.unreached(("REC-F1", "REC-F2", "REC-F3", "REC-F4", "REC-F5"), "the tape does not read back")
        return
    size = ctx.tape.stat().st_size
    led.check("REC-T", summary is not None and not torn and "stopped cleanly" in (ctx.peer.how_ended or ""),
              f"{summary[1] if summary else 'no tape line (the peer did not close it itself)'}; {ctx.peer.how_ended}; "
              f"{len(records)} record(s), {size / 1e6:.1f} MB, torn tail {torn} B")
    facts = pb.tape_facts(records, cp, field=ctx.field)
    g.note(f"THE FIVE CALIBRATION FACTS of {ctx.tape.name}:")
    for line in pb.facts_lines(facts):
        g.note("  " + line)
    for k in ("f1", "f2", "f3", "f4", "f5"):
        led.check(f"REC-{k.upper()}", facts[k]["ok"], facts[k]["why"])
    _note_section8(g, ctx, cp)              # [ff9mapkit netsync s139] the tape's section 8: NOTES, no check
    plans = {leg: pb.plan_leg(leg, facts) for leg in pb.LEGS}
    plans["s120-world"] = pb.plan_leg("span", facts, world=True)
    for leg, p in plans.items():
        how = (f"cut at tape {p['bh'][0]:.2f} s for {p['bh'][1]:g} s" if p.get("bh") else
               f"no cut, the replay stops at tape {p['stop_at']:.2f} s" if p.get("stop_at") else "no cut (the whole tape)")
        g.note(f"  leg {leg}: " + (how if p["ok"] else "CANNOT -- " + p["why"]))
    try:
        (_run_dir(g) / "tape-info.txt").write_text("\n".join(cp.tape_info(ctx.tape)) + "\n", encoding="utf-8")
    except Exception as err:                 # noqa: BLE001 -- a convenience copy only
        g.note(f"tape-info.txt not written: {err}")
    all_ok = all(facts[k]["ok"] for k in ("f1", "f2", "f3", "f4", "f5"))
    if all_ok and SEAT:
        g.note(f"tape: {ctx.tape} ({size / 1e6:.1f} MB) -- a SEAT tape ({SEAT}): latest.json NOT moved (the cut legs keep "
               f"the COOPPARTY tape)")
    elif all_ok:
        ptr = ctx.tape.parent / "latest.json"
        ptr.write_text(json.dumps({"tape": str(ctx.tape), "stage": ctx.stage, "host_s118": ctx.host_s118,
                                   "recorded": header.get("started"), "field": ctx.field, "scene": SCENE,
                                   "facts": {k: facts[k]["why"] for k in ("f1", "f2", "f3", "f4", "f5")}},
                                  indent=1), encoding="utf-8")
        g.note(f"tape: {ctx.tape} ({size / 1e6:.1f} MB) -- latest.json points at it (coop_cut_hold.py's default)")
    else:
        g.note(f"tape: {ctx.tape} -- a fact is MISSING, so latest.json was NOT moved to it")


# ---------------------------------------------------------------------------------------- [ff9mapkit netsync s144] the world
def _world(g, led: cb.Ledger, ctx: _Ctx, conn) -> None:
    """THE WORLD VARIANT's middle: PRE_S on 6603, the proven walk out (coop_world_wait.walk_out), WORLD_S on the world map
    -- every read on WorldHUD, the battle epoch unmoved --, the peer stopped, then the world facts."""
    import coop_world_wait as cw                       # beside this file (the scenario dir is on sys.path)
    _hold_until(ctx, conn[0], PRE_S)
    ok, why, st = cw.walk_out(g)
    led.check("REC-WX", ok, why)
    if ok:
        epoch0 = st.battle_epoch
        end = time.time() + WORLD_S
        reads, off = 0, []
        while time.time() < end and ctx.peer.alive():
            s = g.state
            reads += 1
            if s.ui_state != "WorldHUD" or s.battle_epoch != epoch0:
                off.append((s.ui_state, s.field_id, s.battle_epoch))
            ctx.peer.lines()
            time.sleep(0.5)
        led.check("REC-WS", reads > 0 and not off, f"{reads} read(s) over {WORLD_S:g} s on world {st.world_id}: "
                  + (f"LEFT the world map {off[:3]}" if off else "WorldHUD throughout, no battle"))
    else:
        led.unreached(("REC-WS",), f"the host never reached the world map (REC-WX): {why[:160]}")
    g.note(f"coop_peer serve-guest: {ctx.peer.stop()}")
    _world_facts(g, led, ctx)


def _world_facts(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """REC-T and the world facts (REC-WF1-3) off the closed tape; latest-world.json in the world dir when all three hold
    (NEVER latest.json); the tape's b6 noted (its verdict is `coop_peer.py where`'s)."""
    summary = ctx.peer.first(pb.PEER["tape_summary"])
    try:
        cp = pb.coop_peer_module()
        header, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                 # noqa: BLE001 -- the reason goes into the checks
        led.check("REC-T", False, f"the tape does not read back: {err}")
        led.unreached(("REC-WF1", "REC-WF2", "REC-WF3"), "the tape does not read back")
        return
    size = ctx.tape.stat().st_size
    led.check("REC-T", summary is not None and not torn and "stopped cleanly" in (ctx.peer.how_ended or ""),
              f"{summary[1] if summary else 'no tape line (the peer did not close it itself)'}; {ctx.peer.how_ended}; "
              f"{len(records)} record(s), {size / 1e6:.1f} MB, torn tail {torn} B")
    facts = pb.world_tape_facts(records, cp, field=ctx.field)
    for k in ("w1", "w2", "w3"):
        led.check(f"REC-WF{k[1]}", facts[k]["ok"], facts[k]["why"])
    g.note(f"THE WORLD FACTS of {ctx.tape.name}: exit at tape {facts['exit_t']}, {facts['world_s']} s off-field; the host's "
           f"b6: {facts['b6']} (where: {facts['where']})")
    plan = pb.plan_world_leg("world-wait", facts)
    g.note("  leg world-wait: " + ("the whole tape" if plan["ok"] else "CANNOT -- " + plan["why"]))
    try:
        (_run_dir(g) / "tape-info.txt").write_text("\n".join(cp.tape_info(ctx.tape)) + "\n", encoding="utf-8")
    except Exception as err:                 # noqa: BLE001 -- a convenience copy only
        g.note(f"tape-info.txt not written: {err}")
    if all(facts[k]["ok"] for k in ("w1", "w2", "w3")):
        ptr = ctx.tape.parent / pb.WORLD_POINTER
        ptr.write_text(json.dumps({"tape": str(ctx.tape), "stage": ctx.stage, "recorded": header.get("started"),
                                   "field": ctx.field, "b6": facts["b6"], "world_s": facts["world_s"],
                                   "facts": {k: facts[k]["why"] for k in ("w1", "w2", "w3")}}, indent=1),
                       encoding="utf-8")
        g.note(f"tape: {ctx.tape} ({size / 1e6:.1f} MB) -- {pb.WORLD_POINTER} points at it (latest.json untouched)")
    else:
        g.note(f"tape: {ctx.tape} -- a world fact is MISSING, so {pb.WORLD_POINTER} was NOT moved to it")


# ---------------------------------------------------------------------------------------- [ff9mapkit netsync s145] the world battle
def _stay(g, ctx: _Ctx, seconds: float, epoch0) -> tuple:
    """Idle on the world map ``seconds`` reading the state every 0.5 s: (reads, [(ui, field, epoch) off WorldHUD or a new
    battle])."""
    end = time.time() + seconds
    reads, off = 0, []
    while time.time() < end and ctx.peer.alive():
        s = g.state
        reads += 1
        if s.ui_state != "WorldHUD" or s.battle_epoch != epoch0:
            off.append((s.ui_state, s.field_id, s.battle_epoch))
        ctx.peer.lines()
        time.sleep(0.5)
    return reads, off


def _world_battle(g, led: cb.Ledger, ctx: _Ctx, conn) -> None:
    """THE WORLD-BATTLE VARIANT's middle: PRE_S on 6603, the proven walk out, the planned DWELL on the world map, `battle 67 0
    rand` on WorldHUD (Session.world_battle), the fight won, back on the world map where it fought, the STAY, the peer stopped,
    then the five facts."""
    import coop_world_wait as cw                       # beside this file (the scenario dir is on sys.path)
    _hold_until(ctx, conn[0], PRE_S)
    ok, why, st = cw.walk_out(g)
    led.check("REC-WX", ok, why)
    if not ok:
        led.unreached(("REC-WD", "REC-WB", "REC-WW", "REC-WP"), f"the host never reached the world map (REC-WX): {why[:160]}")
        g.note(f"coop_peer serve-guest: {ctx.peer.stop()}")
        _world_battle_facts(g, led, ctx)
        return
    reads, off = _stay(g, ctx, WB_DWELL_S, st.battle_epoch)
    led.check("REC-WD", reads > 0 and not off, f"{reads} read(s) over {WB_DWELL_S:g} s on world {st.world_id}: "
              + (f"LEFT the world map {off[:3]}" if off else "WorldHUD throughout, no battle"))
    at = _dt.datetime.now()
    here = g.state
    x0, z0 = here.world_x, here.world_z
    import coop_world_battle as wbm                    # [s145 fix1] decision 11's SWIRL-HANG instrument (beside this file)
    wbm._state_every(g, 1)                             # the swirl written every frame: a hang's LAST state is SwirlScene
    try:
        g.world_battle(WB_SCENE, group=WB_GROUP, rand=True)
    except HarnessError as err:
        hung = None
        try:
            wbm.hang_check(g, "the recorder's world battle")
        except wbm.SwirlHang as hang:
            hung = str(hang)
        led.check("REC-WB", False, (f"SWIRL-HANG -- the instrument, never a host verdict (the runner re-records ONCE): {hung[:300]}"
                                    if hung is not None else
                                    f"`battle {WB_SCENE} {WB_GROUP} rand` on WorldHUD failed: {str(err)[:300]}"))
        led.unreached(("REC-WW", "REC-WP"), "no world battle" + (" (SWIRL-HANG)" if hung is not None else ""))
        wbm._note(g, f"coop_peer serve-guest: {ctx.peer.stop()}")
        _world_battle_facts(g, led, ctx)
        return
    wbm._state_every(g, 2)
    lane = ctx.peer.wait_for(pb.PEER["host_lane_up"], 15.0, after=at)
    intro = pb.hits(ctx.eng.lines(), "intro", after=at)
    led.check("REC-WB", lane is not None and int(lane[2].group(2)) == WB_SCENE and bool(intro),
              f"peer: {lane[1] if lane else 'no host battle lane'}; host: {pb.show(intro)}; status {g.state.debug_status!r}")
    t0 = time.time()

    def policy(s, slot):
        # Defend until WB_FIGHT_S has run (the guest's boot, LIVE and served menu land inside the live fight), healing a member
        # under 45% with a Potion, then Attack
        if time.time() - t0 >= WB_FIGHT_S:
            return {"command": "Attack"}
        try:
            menu = g.menus(slot)
        except HarnessError:
            return None
        names = {c.get("name") for c in (menu.get("commands") or []) if c.get("offered", True)}
        items = {i.get("name") for i in (menu.get("items") or [])}
        hurt = [u for u in cb.units(s, player=True) if u.get("alive") and int(u.get("hp_max") or 0) > 0
                and int(u.get("hp") or 0) * 100 < int(u.get("hp_max")) * 45]
        if hurt and "Potion" in items:
            return {"command": "Potion"}
        return {"command": "Defend"} if "Defend" in names else None

    try:
        result = g.fight(policy=policy, timeout=WB_FIGHT_S + 180.0, max_turns=240)
        back = g.wait_world(timeout=90.0)
    except HarnessError as err:
        led.check("REC-WW", False, f"the fight (or its return) raised: {str(err)[:300]}")
        led.unreached(("REC-WP",), "no return to the world map")
        g.note(f"coop_peer serve-guest: {ctx.peer.stop()}")
        _world_battle_facts(g, led, ctx)
        return
    lf = getattr(g, "last_fight", {}) or {}
    won = result in (1, 2)
    long_enough = float(lf.get("seconds", 0.0)) >= WB_FIGHT_S - 1.0
    dist = (abs((back.world_x or 0.0) - (x0 or 0.0)) + abs((back.world_z or 0.0) - (z0 or 0.0))
            if None not in (back.world_x, x0) else None)
    near = dist is not None and dist <= WB_RETURN_TOL
    led.check("REC-WW", won and long_enough and back.ui_state == "WorldHUD" and near,
              f"result {result} ({lf.get('name')}), {lf.get('seconds')} s, {lf.get('turns')} turn(s); back on "
              f"{back.ui_state} world {back.world_id} at ({back.world_x}, {back.world_z}) -- "
              f"{'%.2f' % dist if dist is not None else '?'}u from where it fought ({x0}, {z0})")
    reads, off = _stay(g, ctx, WB_POST_S, back.battle_epoch)
    led.check("REC-WP", reads > 0 and not off, f"{reads} read(s) over {WB_POST_S:g} s after the battle: "
              + (f"LEFT the world map {off[:3]}" if off else "WorldHUD throughout, no second battle"))
    if WB_ENTER:
        _world_battle_enter(g, led, ctx, cw)
    g.note(f"coop_peer serve-guest: {ctx.peer.stop()}")
    _world_battle_facts(g, led, ctx)


def _world_battle_enter(g, led: cb.Ledger, ctx: _Ctx, cw) -> None:
    """[ff9mapkit netsync s145 bench] THE ENTRY after the stay (REC-WE): the Ice Cavern's world tile (coop_world_wait.ICE_TILE, round
    8's lane), its prompt's frames, Confirm -> FieldHUD 300 (the host is unfrozen: its own game), then WB_ENTER_S on 300 -- what the
    replayed guest's rejoin (coop_world_battle.py's WB-300) follows from the world map after its warm return."""
    try:
        cw.teleport_settle(g, cw.ICE_TILE)
        g.wait_frames(cw.PROMPT_FRAMES)
        g.press("confirm")
        st = cb.poll(g, lambda s: s.ui_state == "FieldHUD" and s.field_id == pb.WB_ENTER_FIELD, ENTER_FIELD_S,
                     f"field {pb.WB_ENTER_FIELD}")
    except HarnessError as err:
        led.check("REC-WE", False, f"the entry raised: {str(err)[:300]}")
        return
    if st is None:
        led.check("REC-WE", False, f"never entered {pb.WB_ENTER_FIELD} within {ENTER_FIELD_S:g} s (ui {g.state.ui_state!r}, "
                                   f"field {g.state.field_id}, world {g.state.world_id})")
        return
    end = time.time() + WB_ENTER_S
    off = []
    while time.time() < end and ctx.peer.alive():
        s = g.state
        if not (s.ui_state in ("FieldHUD", "FieldMenu") or s.fading) or s.field_id != pb.WB_ENTER_FIELD:
            off.append((s.ui_state, s.field_id))
        ctx.peer.lines()
        time.sleep(0.5)
    led.check("REC-WE", not off, f"FieldHUD {pb.WB_ENTER_FIELD} after the Confirm; {WB_ENTER_S:g} s on it"
              + (f" -- LEFT it {off[:3]}" if off else ""))


def _world_battle_facts(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """REC-T and the five facts (REC-WBF1-5) off the closed tape; latest-world-battle.json in the world-battle dir when all five
    hold (NEVER latest.json / latest-world.json); the tape's battle segments noted (`coop_peer.py where --want world-battle`)."""
    summary = ctx.peer.first(pb.PEER["tape_summary"])
    try:
        cp = pb.coop_peer_module()
        header, records, torn = cp.read_tape(ctx.tape)
    except Exception as err:                 # noqa: BLE001 -- the reason goes into the checks
        led.check("REC-T", False, f"the tape does not read back: {err}")
        led.unreached(tuple(f"REC-WBF{i}" for i in range(1, 6)), "the tape does not read back")
        return
    size = ctx.tape.stat().st_size
    led.check("REC-T", summary is not None and not torn and "stopped cleanly" in (ctx.peer.how_ended or ""),
              f"{summary[1] if summary else 'no tape line (the peer did not close it itself)'}; {ctx.peer.how_ended}; "
              f"{len(records)} record(s), {size / 1e6:.1f} MB, torn tail {torn} B")
    facts = pb.world_battle_tape_facts(records, cp, field=ctx.field)
    keys = ("wb1", "wb2", "wb3", "wb4", "wb5")
    for k in keys:
        led.check(f"REC-WBF{k[2]}", facts[k]["ok"], facts[k]["why"])
    g.note(f"THE WORLD-BATTLE FACTS of {ctx.tape.name}: exit at tape {facts['exit_t']}, dwell {facts['dwell_s']} s, battle "
           f"{facts['battle']}, terminal at {facts['t_term']}, {facts['after_s']} s after")
    plan = pb.plan_world_leg("world-battle", facts)
    g.note("  leg world-battle: " + ("the whole tape" if plan["ok"] else "CANNOT -- " + plan["why"]))
    try:
        (_run_dir(g) / "tape-info.txt").write_text("\n".join(cp.tape_info(ctx.tape)) + "\n", encoding="utf-8")
    except Exception as err:                 # noqa: BLE001 -- a convenience copy only
        g.note(f"tape-info.txt not written: {err}")
    if all(facts[k]["ok"] for k in keys):
        ptr = ctx.tape.parent / pb.WORLD_BATTLE_POINTER
        ptr.write_text(json.dumps({"tape": str(ctx.tape), "stage": ctx.stage, "recorded": header.get("started"),
                                   "field": ctx.field, "scene": WB_SCENE, "b6": facts["b6"], "dwell_s": facts["dwell_s"],
                                   "battle": facts["battle"], "after_s": facts["after_s"], "enter": facts.get("enter"),
                                   "facts": {k: facts[k]["why"] for k in keys}}, indent=1), encoding="utf-8")
        g.note(f"tape: {ctx.tape} ({size / 1e6:.1f} MB) -- {pb.WORLD_BATTLE_POINTER} points at it (latest.json and "
               f"{pb.WORLD_POINTER} untouched)")
    else:
        g.note(f"tape: {ctx.tape} -- a world-battle fact is MISSING, so {pb.WORLD_BATTLE_POINTER} was NOT moved to it")
