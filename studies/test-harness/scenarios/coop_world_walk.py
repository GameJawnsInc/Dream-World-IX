"""s166 -- WORLD-MAP CO-OP RUNG 2, ROUND A (memoria-patch s166): the bench, run unattended. THIS STEP: PIECE A0 ONLY.
[ff9mapkit netsync s166] Round A's scenario (studies/world-coop/S166-DESIGN.md "The bench"); each later piece of the round adds its own
rows here, built and benched alone (one change per in-game test). On coop_world_follow.py's route and conventions (imported, never
copied: its route, judges and the s165 bench host): SOLO, one game on the forced selftest role, a FABRICATED host frame through the
engine's own encoders (`netsync worldfollow host <x> <z> ...`), 6603 -> 9011 by s165's own follow-out.

PIECE A0, DECISION 19 -- THE CONTROL-OFF KIT-CELL CLOSE (first and alone: it closes a live s165 hazard). The Southern Ring's kit adds six
cell functions to entry 0 of every deployed free-roam dispatcher (K1: WORLD00 / 02 / 03 / 05 / 07 / 08 / 09 / 10 / 11) and, on
WORLD11, the boardable boat (entry 15) and the ferryman (entry 16);
each reads a BARE KEYON(Confirm), no usercontrol term. The engine requests a cell's function every frame the walker stands on its
TRIGGER -- an event-id triangle (ff9.cs w_movementUpdate: `m_GetIDEvent(s_moveCHRStatus.id) != 0 && w_frameEventEnable` -> WorldEvent
-> Request(uid 0, level 1, the cell's tag)), never anywhere else in the 32-u cell -- whatever control says, and FilterScriptButtons'
control-OFF branch passes the guest's own keys -- so on s165 a Confirm in any control-off tick on a kit trigger takes the frozen guest
into 6601 / 6602 / 6603 ALONE (s42's no-recovery class), and beside the ferryman plays its scene on the guest's own copy. s166: on
gMode 3, under WorldFreezeNow, a control-OFF read loses HostOwnedKeys when its reader is
entry 0 or an entry past its world's stock dispatcher's last (e14 on WORLD02 / 11, e12 on WORLD10; K1 widened the design's walk-world
scope to every world map: battlewire.STOCK_LAST_ENTRY); every stock read passes as before. Its witness `netsync.world.kitcell` {lever, closed, last_sid, last_world}, netsync.world's LAST key (after `dot`); its line
'world kit-cell close: ' once per world load and reader entry (the engine re-arms it at every world load); its lever `netsync worldwalk kitcell old|act` (old = s165 exactly).

THE ROUTE: New Game -> 6603 FARSHORE (FF9CustomMap-world) -> world 9011 by s165's follow-out with the bench host AT FS_LANDING (68,
-444), the bench host off after the landing (s165's own way) -> each leg TELEPORTS the frozen guest onto its stand. THE PRE-INIT
SAMPLE: the landing is judged only on a sample with `world.block_ready` true and `world.ticks` advancing; A GAME PUBLISHES NOTHING
DURING ITS OWN SYNC LOAD, so every verdict reads frames first published after the edge it judges (the press); THE ORDER SKEW: a
`control` flip's own publish is dropped (the sample after the flip that first reads control off, plus two frames).

THE STAND POINT (the 2026-11-02 OLD run on s165: A-KITOFF pressed at FS_LANDING, 121 samples all WorldHUD 9011, no hazard). FS_LANDING
lies in cell (2, 13) but 12 u WEST of the 6603 TRIGGER: the kit wrote that entrance with `world-entrance --cell 2 13 --field-direct
6603 ... --trigger-at 80 -444 --trigger-radius 3.0 --no-tile-area` (the install's .ff9world.jsonl, read-only), so its event id sits
ONLY on the six terrain triangles whose centroids lie within 3 u of (80, -444) (the deployed mesh's census: battlewire.KIT_TRIGGER_TILES;
every kit cell is one such small patch), and nothing requests the cell's function anywhere else in the cell. A-KITOFF stands ON
KIT_6603_TRIGGER (80, -444), the patch's centre.

THE FREEZE (decision 19 closes only under WorldFreezeNow, so both legs' instruments require it: `netsync.world.freeze.on` true at the
stand, at the press and on every judged sample after it -- a sample where it lifted reads "not reached (the instrument): the freeze
lifted ...", never a pass and never a fail of the close, and an OLD / LEVER hazard measured unfrozen is not measured). On this bench
the freeze is SpectatorField's THIRD term, the selftest role under `netsync bench 1` (freeze.why 'bench'), NOT the bench host:
coop_world_follow's own FROZEN row judges it after `worldfollow host off`, and the 2026-11-02 runs read freeze.on true ('bench') on
every sample after both presses (121 and 128) -- the "world freeze lifted ... no spectator session" line those runs logged is the
`reset`'s (the role released, after the legs). So the bench host goes off after the landing, as s165's does; nothing here needs it on.

  setup  INI (READ-ONLY: [Netsync] Enabled 0 or absent, FollowHost 1 -- written BEFORE launch, solo_ini.py; a bench without them
         fails here, early, and sends nothing) -> OR (the offline oracle: s165's route oracle + the deployed WORLD11 read with the kit's
         pure reader -- entry 0's 6603 cell function 0x8D09 reads KEYON and enters 6603, the boat (e15) at BOAT_SPAWN and the ferryman
         (e16) at FERRY_AT, the stock dispatcher's last entry 14; and the deployed Block[1][6] Terrain's event tiles in cell (2, 13)
         exactly battlewire.KIT_TRIGGER_TILES[(2, 13)], KIT_STAND on them) -> S0 (newgame, the COOPPARTY seed, 6603, encounters off, the forced
         selftest role) -> P0 (`netsync.world` ends `dot`, `kitcell` -- the key at its sentinel's shape -- and the proof line 'world
         walk selftest: OK (N rows, M mutants)', none FAIL) -> P1 (`netsync bench 1`; `kitcell` at rest 'act' -- or, COOP_CALIBRATE=1
         with COOP_WW_LEVER=kitcell on s166, `worldwalk kitcell old` pulled here and held through the run).
  A-KITOFF   land at FS_LANDING (the route's instrument: WorldHUD 9011, judged, within POSE_TOL, on foot), then teleport ONTO the 6603
             trigger -- KIT_STAND, KIT_6603_TRIGGER (80, -444) -- control ON for the teleport (the overworld teleport sticks only
             then; a frozen guest's control-on reads are s144's mask, so standing there with control on presses nothing). The stand's
             instrument: WorldHUD 9011, within KIT_6603_TRIGGER_R (3 u, torus) of the trigger AND on its event tiles, on foot,
             FROZEN. Then `control 0` (the harness op: SetUserControl(false)), a Confirm press held PRESS_FRAMES frames, KITOFF_S
             watched: every sample WorldHUD 9011, never FieldHUD 6603, never `world.next_mode` 1 (the world's shutdown toward a
             field); `kitcell.closed` +2 (entry 0 and the boat's eager @00174 read, entry 15: BW.KIT_EAGER_READERS), last_sid
             0 or 15, last_world 9011, lever 'act'; one 'world kit-cell close: ' line naming entry 0 and 9011. The instruments
             in both legs: control off at the press and on every WorldHUD sample after it (a control-on
             read is s144's mask, never the close -- a window where something gave control back judges nothing), and THE FREEZE
             held (above).
  A-FERRYOFF teleport within 12 u of the ferryman (29, -1168) -- FERRY_STAND, never on a kit cell (cell (1, 36), x 32-64, is a 6601
             entrance; its trigger patch sits at x 44-52) -- control ON for the teleport, the stand's instrument (inside his box, off
             every kit cell, on foot, Map[50] / [51] 0, FROZEN), `control 0`, Confirm, FERRY_S watched: Map[50] stays 0 on every
             sample (the `world.mapvar` digest's byte 50), no scene fade (`fading` false), still WorldHUD 9011; `kitcell.closed` +2
             (16 and the boat's eager 15), last_sid 16 or 15, last_world 9011; one line naming entry 16.
  R      `kitcell old` pulled, then `reset`: the role released and 'worldwalk levers released (with the harness)' once; re-read
         WITH the role: `kitcell` 'act'.

THE ~ MENU'S "DISABLE CONTROL" HOLD (the design's A-KITOFF second clause): NOT DRIVABLE HERE -- the menu opens on a raw BackQuote key
read (UIKeyTrigger: UnityXInput.Input.GetKeyDown), which no harness verb injects. Its hold IS SetUserControl(false) (Ff9mkDebugMenu.
ApplyControlHold), the same call the harness's `control 0` makes, so A-KITOFF covers the engine's read; the stand-in models the hold
itself (tests/test_coop_world_walk.py: the close under it, and a close keyed on the harness op leaks there).

CALIBRATION -- a check that cannot fail is not a check. EACH DESTRUCTIVE LEG NEEDS ITS OWN LAUNCH: under COOP_CALIBRATE=1 the bench
refuses (S166-CAL red, nothing launched) unless COOP_WW_LEG names exactly one leg.
  * OLD_PREDICTED, on the deployed s165 (COOP_CALIBRATE=1): no `netsync.world.kitcell` -- the bench PROBES first and NEVER sends a
    `worldwalk` op there. P0, P1 and the leg red, and the leg MEASURES today's hazard ON ITS STAND, FROZEN (the CAL row also requires
    it: a hazard seen with the freeze lifted, or off the stand, is not measured): A-KITOFF -- the guest goes to FieldHUD 6603 alone (or
    at least the world's shutdown toward it: `next_mode` 1, then the load watched to the end); A-FERRYOFF -- the ferryman's scene
    plays on the guest's copy (Map[50] != 0).
  * LEVER_PREDICTED, on s166 (COOP_CALIBRATE=1, COOP_WW_LEVER=kitcell: `worldwalk kitcell old` held from P1): exactly OLD's leg row,
    the hazard measured the same way.
  * An s166+ engine without COOP_CALIBRATE: every row green, no hazard. An s165 engine without COOP_CALIBRATE: the legs are NOT run
    (nothing new to judge; run the OLD calibration to measure the hazard).
  * OFFLINE: the stand-in (tools/harness/fakegame.py, rung `worldwalk`, its WORLD_WALK_FAULTS, its kit content -- each kit cell
    requested only on its trigger tiles -- and both entry orders) and ff9mapkit/tests/test_coop_world_walk.py: each leg smoked
    through the real Session, each fault red in exactly its SOLO_FAULT_REDS rows, the s165 stand-in exactly OLD_PREDICTED, the lever
    exactly LEVER_PREDICTED, the pure judges red on each wrong shape; and each instrument can fail -- a stand at FS_LANDING (off the
    trigger: COOP_WW_KIT_AT) is "not reached" and measures no hazard, a freeze lifted before or after the press (the real
    `netsync bench worldfreeze off`) is "not reached: the freeze ...".

WHAT NO LEG HERE REACHES (named, not hidden): the ~ menu's hold in game (above); the boat (its board needs Map[24] 169 at its read,
which the entry order decides -- unsettled offline, K1: the stand-in pins the close under both orders, no round-A row boards in game);
a stock control-off wait (no drivable stock control-off Confirm read on the walk worlds: the proof's table and the stand-in pin that
every stock read passes); 9002 / 9010 (the same dispatcher cells; the bench lands only on 9011); the other five kit triggers (6601 x4,
6602: the same entry-0 read, the close keyed on the reader, never the cell -- the stand-in and the proof pin them); a FOLLOWED real
client's freeze ('live' / 'mirroring': the duo -- A0 changes nothing on the host, and the close keys on WorldFreezeNow whatever its term).

[ff9mapkit netsync s166] PIECE A0b, DECISION 26 -- THE PAIRING PULL (second and alone; its OLD is the A0 build af1f9e02). A following guest
that pairs ON ITS OWN FIELD while the host already stands on the world map waited there on s165 / A0 (WorldOutStep's term 3,
`not_mirroring`, THE PAIRING-WINDOW LAW) until the host's next stop -- the s165 two-PC session's finding 1, its line 'world follow-out:
waits: not mirroring the host's story yet (the pairing window: the s144 wait stands)' although the laptop wrote its pairing autosave the
moment it paired. A0b: term 3 holds such a guest only while its pairing autosave is PENDING (the window open, nothing written in it, no
durable decline: why `pairing_save`, "your pairing autosave is still pending"); a written autosave or a durable decline lets the follow-out
start, and its landing ARMS the mirror ("[NetSync] state-mirror ARMED at world map W's landing -- ..."). Its witness
`netsync.world.pairpull` {lever, pending, arms, last_world}, netsync.world's LAST key (after `kitcell`); its lever `netsync worldwalk
pairpull old|act` (old = s165's term 3 and no arm). The bench PROBES `netsync.world.pairpull` and never sends `pairpull` without it.

T2-A pair (COOP_WW_LEG=pair; the desktop is a REAL client, set up exactly as coop_world_follow.py's T2 `walk` leg: New Game -> 6603,
encounters off, the marker watched, the field entry's own autosave; Memoria.ini [Netsync] through _coop_peer_bench.IniGuard -- its
GUEST_VALUES (FollowHost 1, SessionGraceMs 30000), backed up first, restored byte-exact -- and the engine's own config line; then the
probe and (calibration only) the lever, BEFORE the replay; then tools/harness/coop_peer.py `replay-host <tape> --from PAIR_FROM_S
--at-end hold` on the private bench port of THE WORLD-WALK TAPE (COOP_TAPE_WORLD_WALK, recorded on s164: v14, no restamp while the
wire is v14). PAIR_FROM_S = 45.0 s is read off that tape with coop_peer's own `where --pose` (the evidence beside the constant): the host
on 9011 on foot at ICE_TILE from 40.99 s, live (its heartbeat moving) since 36.95 s, the stand lasting to 118.25 s, then 300 at
118.71 s. So the guest's very first host frame already says b6: it pairs on its own 6603 (no same-field kick: the host's lane reads
field 0), never mirrored.
  T2-TAPE  the tape's six facts (world_walk_tape_facts) AND pair_from_facts at PAIR_FROM_S (b6 on foot on [102] 11 at ICE_TILE, live
           >= the 1200 ms debounce, its heartbeat fresh, the stand >= PAIR_ROOM_S more, a field after it)
  T2-PEER  as coop_world_follow's (the bench port free, THE OWNER'S BRIDGE DOWN, the config line, listening / connected / the replay
           started) AND the replay's start line at tape PAIR_FROM_S
  PR-I     the instrument: from the replay's start to the host-cache b6 read, the guest on FieldHUD 6603, not mirroring, no kick or
           ARMED line; on A0b `pairpull.lever` read back
  PR-SAVE  'pairing autosave written on field 6603 (the pairing window): ...' after the replay's start and BEFORE the follow-out's start
           line (log order); no 'no pairing autosave this session' line
  PR-OUT   the pull: WorldHUD 9011, starts / commits / lands +1 and their lines (judge_leave: after block_ready + ticks, THE PRE-INIT
           SAMPLE), out.why never 'not_mirroring' on a sample published after the autosave line
  PR-POSE  the landing within POSE_TOL of the TAPE's own pose over the seam bracket, >= FAR_U plain from FS_LANDING (judge_tape_pose)
  PR-ARM   mirroring true on every judged world sample from the landing on; pairpull.arms +1, last_world 9011; the world-form ARMED line
           ONCE (naming 9011) and no field-form one
  PR-SAVEMENU on the world map, `worldfollow saveguard old` (R4's DRY lever) and Alt+F5 (`savemenu`): the arm's save-side witness. An
           ARMED guest's chord is refused AHEAD of the menu by s38's mirror gate (UIKeyTrigger.OnSaveLoadSceneCommandDetected:
           `!IsMenuControlEnable || IsMirroringStory`), so no save menu opens and R4's Save sites are never reached: refused +0 AND
           would_save +0, pinned to the mirror at the press (WorldHUD 9011, menu_refusal.now 'audible' = menu control on, mirroring,
           the DRY lever 'old') and the verb's own `savemenu` event (exactly one, from WorldHUD: HarnessSaveMenu always reaches the
           chord). An UNARMED guest's chord opens the menu and its DRY pick counts would_save +1 (s165's R4-DRY): red; the stand-in's
           `chord_gate_open` (the chord without the mirror term: R4 reached, refused +1) is red with every press term green -- the
           row's own calibration. No Confirm is pressed unless the menu opened; a late-opening menu still counts opened. The sandbox
           unchanged. (A0b's first in-game run read +0/+0 against a refused +1 that assumed the pick reaches SaveLoadUI: re-derived
           from the engine, not weakened.)
  PR-REJOIN the tape's host enters 300: the guest rejoins 300 from the world map (judge_rejoin_land + the arrival guard's world clause),
           mirroring true, the host's marker 0xA5 on 300, and NO ARMED line since the landing (armed once, there)
  T2-SAVE / T2-INI the finals.
D-PAIR (duo.py --no-pair: duo.py CAN start the guest's link late with its own ops -- run_duo applies the HOST's role (d.apply_role),
walks it out onto 9011 and onto ICE_TILE past the debounce, and only then applies the GUEST's role on its own 6603; no engine op): the
same judges on the duo (D-PAIR-I, D-PAIR-SAVE, D-PAIR-OUT at the host's own world x/z, D-PAIR-ARM, D-PAIR-SAVEMENU, D-PAIR-REJOIN by
the host's Confirm on the tile; D-PAIR-CAL).
THE PAIRING AUTOSAVE ON THE BENCH: the window's write is the STOCK autosave (FF9StateSystem.Serializer.Autosave, the very call
StartEvents makes at a field entry) -- and while the harness is armed HarnessAgent.RedirectSaves points SharedDataBytesStorage at its
SANDBOX, <game>/x64/ff9harness/save/ (the container and its Memoria sidecar), published as `save_path` / `save_sandboxed` and verified
at arm. The owner's own containers (%USERPROFILE%/AppData/LocalLow/SquareEnix/FINAL FANTASY IX/Steam/EncryptedSavedData) are never
written: the Session backs them up to the run dir before launch and flags any change at teardown. The s165 T2 walk legs already let
it write there (their guest paired free-standing on 6603: 'pairing autosave written on field 6603 (the pairing window)' in the
2026-11-01 runs, the sandbox path in the same log), as does this leg; nothing here overwrites more than those legs did.
CALIBRATION (COOP_CALIBRATE=1 COOP_WW_LEG=pair): by the GUEST's stage -- the A0 build (no netsync.world.pairpull; nothing new sent):
exactly T2_PAIR_OLD_PREDICTED red (OUT, POSE, ARM, SAVEMENU, REJOIN; I and SAVE green -- the s154 window writes on every engine) AND
THE OLD WAIT MEASURED (pair_old_wait: every sample from the b6 read to the tape's 300 on FieldHUD 6603, why 'not_mirroring', no start);
on A0b `worldwalk pairpull old` sent before the replay: exactly the same (LEVER_PREDICTED). The duo's D-PAIR-CAL: the A0 build exactly
DUO_PAIR_OLD_PREDICTED red. OFFLINE: tests/test_coop_world_walk.py drives the leg through a stub replay-host (it honours --from) on
the stand-in with THE PAIRING WINDOW modelled (FakeGame.pairing_window), the A0 build (FakeGame.world_walk_pieces), the lever, and the
faults pairpull_early (a BUSY guest at the pairing: the start before the write) and pairpull_unarmed, each red in exactly its
T2_PAIR_FAULT_REDS rows; and the duo on two stand-ins joined by a stub link that starts at the guest's apply_role.

PRECONDITIONS -- THE OPERATOR'S JOB: the DLL under test deployed (the bench deploys nothing); controllers OFF, nobody at the keyboard
(THE UNATTENDED LAW), FF9 unfocused; 6603 registered; [Netsync] Enabled 0 and FollowHost 1 written BEFORE launch (solo_ini.py);
close the game after a lab. [ff9mapkit netsync s166] T2-A pair: the world-walk tape, the bench port free, [SaveFile]
AutoSaveOnlyAtMoogle 0, THE OWNER'S OWN BRIDGE DOWN (127.0.0.1:49201: the guest launches on the owner's Memoria.ini, whose RelayUrl
dials it before the bench's edit -- the leg refuses, nothing edited); D-PAIR: duo.py's own preconditions.

    py <scratchpad>/solo_ini.py s166-a0 -- py tools/play.py studies/test-harness/scenarios/coop_world_walk.py --field 6603
    COOP_CALIBRATE=1 COOP_WW_LEG=kitoff   (the same command: one destructive leg per launch; on s165 = OLD, on s166 +
                                           COOP_WW_LEVER=kitcell = LEVER)
    COOP_WW_KIT_AT="x,z" / COOP_WW_FERRY_AT="x,z" move a stand (its instrument still judges it: off the trigger is "not reached")
    COOP_WW_LEG=pair py tools/play.py studies/test-harness/scenarios/coop_world_walk.py                     (T2-A pair; NEW on A0b)
    COOP_CALIBRATE=1 COOP_WW_LEG=pair py tools/play.py studies/test-harness/scenarios/coop_world_walk.py    (A0 build = OLD; A0b =
                                                                                     the lever `pairpull old`)
    py tools/harness/duo.py studies/test-harness/scenarios/coop_world_walk.py --no-pair                     (D-PAIR; COOP_CALIBRATE=1)
    COOP_WW_PAIR_FROM=<tape s> moves the --from second (T2-TAPE re-reads its facts there)
"""
from __future__ import annotations

import datetime as _dt                                     # [ff9mapkit netsync s166] A0b's T2 leg
import os
import re
import sys
import time                                                # [ff9mapkit netsync s166] A0b's duo leg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import coop_world_wait as cw                               # noqa: E402 - the s144 route and judges (imported, never copied)
import coop_world_follow as wf                             # noqa: E402 - the s165 route, bench host and judges (imported, never copied)
import _coop_peer_bench as pb                              # noqa: E402 - [ff9mapkit netsync s166] A0b: the T2 two-role bench helpers

HarnessError = cb.HarnessError
BW = cw._bw()                                              # battlewire (the driver puts tools/ on sys.path)

#: the s166 capability: key PRESENCE (State.coop_world_walk). An engine without it fails `netsync worldwalk` closed.
PROBE = "netsync.world.kitcell"
#: the s165 route's own capability (the bench host and the follow-out): an engine without it cannot land this bench at all
ROUTE_PROBE = wf.PROBE
LEGS = ("kitoff", "ferryoff")
LEVERS = ("kitcell",)


def _legs(raw) -> tuple | None:
    n = (raw or "all").strip().lower()
    if n in ("", "all"):
        return LEGS
    picked = tuple(x for x in LEGS if x in {p.strip() for p in n.split(",")})
    return picked or None


_RAW_LEG = os.environ.get("COOP_WW_LEG", "all")
SOLO_LEGS = _legs(_RAW_LEG)
_RAW_LEVER = os.environ.get("COOP_WW_LEVER", "kitcell").strip().lower() or "kitcell"
LEVER = _RAW_LEVER if _RAW_LEVER in LEVERS else None

# ------------------------------------------------------------------------------------------------ the route (coop_world_follow's)
FARSHORE, FS_LANDING, WORLD = wf.FARSHORE, wf.FS_LANDING, wf.WORLD
#: THE STAND POINT (battlewire's census facts): the 6603 entrance's TRIGGER -- the ledger's `--trigger-at 80 -444 --trigger-radius 3.0
#: --no-tile-area`, its six event-id triangles BW.KIT_TRIGGER_TILES[(2, 13)] -- not its cell: FS_LANDING is in the cell, 12 u west of it
KIT_TRIGGER, KIT_TRIGGER_R = BW.KIT_6603_TRIGGER, BW.KIT_6603_TRIGGER_R
KIT_CELL = BW.world_cell(*KIT_TRIGGER)
KIT_FIELD = BW.KIT_CELLS.get(KIT_CELL)
FERRY_AT = BW.KIT_FERRY_AT


def _stand(raw, default) -> tuple:
    """A stand's "x,z" override (COOP_WW_KIT_AT / COOP_WW_FERRY_AT), else ``default``. The stand's instrument judges wherever it is."""
    try:
        x, z = (float(v) for v in str(raw).split(","))
        return x, z
    except (TypeError, ValueError):
        return default


#: A-KITOFF: ON the 6603 trigger (its centre, the vertex all six event triangles share)
KIT_STAND = _stand(os.environ.get("COOP_WW_KIT_AT"), KIT_TRIGGER)
#: A-FERRYOFF: 3 u west and 8 u north of the ferryman -- inside its +-12 u box, on cell (0, 36), never on the 6601 kit cell (1, 36) east
FERRY_STAND = _stand(os.environ.get("COOP_WW_FERRY_AT"), (FERRY_AT[0] - 3.0, FERRY_AT[1] + 8.0))

# ------------------------------------------------------------------------------------------------ the measures
POSE_TOL = wf.POSE_TOL     # the landing within this (torus) of FS_LANDING
PRESS_FRAMES = 4           # the Confirm held this long ("a few frames": its KeyOn edge is read once per reader)
KITOFF_S = 4.0             # the press -> the window every sample must stay on WorldHUD 9011 (s165's fade + Field() land inside it)
FERRY_S = 4.0              # the press -> the window Map[50] must stay 0 (s165's scene sets 1 ~25 world ticks after the press)
HAZARD_S = 30.0            # OLD: a hazard seen -> watched on until FieldHUD 6603 (the load measured to its end)
LEAVE_S = 60.0             # the follow-out's start -> its first judged world sample
CONTROL_S = 3.0            # a `control` flip -> the first sample reading it
SKEW_FRAMES = 2            # THE ORDER SKEW: the flip's own publish dropped
SETTLE_FRAMES = 20
POLL_S = 0.1
DETAIL_W = 1400
FORCE = os.environ.get("COOP_WW_FORCE", "").strip() not in ("", "0")

# ================================================================================================ the catalogs
SOLO_SETUP = {
    "S166-INI": "precondition (Memoria.ini, READ-ONLY): [Netsync] Enabled 0 or absent and FollowHost 1, written before launch (the "
                "selftest role with the fabricated host's gate) -- else the bench stops here and sends nothing",
    "S166-OR": "the offline oracle: s165's route (coop_world_wait.read_oracle) and the deployed WORLD11 -- entry 0's 6603 cell "
               "function (0x8D09) reads KEYON and enters 6603, the boat (e15) at BOAT_SPAWN and the ferryman (e16) at FERRY_AT -- and "
               "the deployed terrain's 6603 trigger tiles exactly the census's, the stand on them",
    "S166-S0": "newgame -> (the COOPPARTY seed) -> 6603 -> encounters off -> the forced selftest role",
    "S166-P0": "`netsync.world` ends `dot`, `kitcell` (its keys the contract's, in order) and the proof line 'world walk selftest: "
               "OK (N rows, M mutants)', none FAIL",
}
SOLO_LEGS_ROWS = {
    "kitoff": {"S166-A-KITOFF": "ON the 6603 trigger (80, -444), frozen, `control 0`, Confirm: every sample WorldHUD 9011, never "
                                "FieldHUD 6603 nor next_mode 1; kitcell.closed +2 (entries 0 and 15), last_sid 0 or 15, last_world 9011; one close line naming "
                                "entry 0"},
    "ferryoff": {"S166-A-FERRYOFF": "within 12 u of the ferryman, frozen, `control 0`, Confirm: Map[50] stays 0, no scene fade, "
                                    "WorldHUD 9011; kitcell.closed +2 (entries 16 and 15), last_sid 16 or 15, last_world 9011; one close line naming entry 16"},
}
SOLO_FINAL = {
    "S166-R": "`reset` (the lever pulled just before it) releases the role and every worldwalk lever ('worldwalk levers released "
              "(with the harness)' once); re-read WITH the role: kitcell 'act'",
}
LEG_ROW = {leg: next(iter(rows)) for leg, rows in SOLO_LEGS_ROWS.items()}
SOLO_ALL = tuple(SOLO_SETUP) + ("S166-P1",) + tuple(LEG_ROW.values()) + tuple(SOLO_FINAL)


def solo_catalog(calibrate: bool, legs=LEGS, lever=None) -> dict:
    c = dict(SOLO_SETUP)
    c["S166-P1"] = (f"`netsync bench 1` accepted and the CALIBRATION lever `worldwalk {lever} old` pulled and read back (held "
                    "through the run)" if calibrate and lever else
                    "`netsync bench 1` accepted (the field-gate bench on) and kitcell at rest: lever 'act'")
    for leg in LEGS:
        if leg in legs:
            c.update(SOLO_LEGS_ROWS[leg])
    c.update(SOLO_FINAL)
    if calibrate:
        c["S166-CAL"] = ("CALIBRATION (one destructive leg per launch): the engine's stage decides the set -- before s166 exactly "
                         "OLD_PREDICTED red, on s166 under the pulled lever exactly LEVER_PREDICTED[lever] red -- and the leg "
                         "MEASURED its hazard (FieldHUD 6603 / Map[50]) on its stand, frozen")
    return c


#: [calibration] an engine before s166 (the deployed s165): the key and the proof line absent, the leg's hazard live
OLD_PREDICTED = ("S166-P0", "S166-P1") + tuple(LEG_ROW.values())
#: [calibration] s166 under the lever pulled at P1 and held: exactly the legs (s165's hazard back)
LEVER_PREDICTED = {"kitcell": tuple(LEG_ROW.values())}
#: the stand-in's FAULT LEVERS (fakegame.WORLD_WALK_FAULTS) -> exactly the SOLO rows each turns red under the stand-in's DEFAULT entry
#: order (e0 before e1); tests pin it, and ORDER_FAULT_REDS the ones the other order turns red
SOLO_FAULT_REDS = {
    "walk_proof_fail": ("S166-P0",),
    "kitcell_leak": ("S166-A-KITOFF", "S166-A-FERRYOFF"),
    "kitcell_sid0_only": ("S166-A-KITOFF", "S166-A-FERRYOFF"),   # the ferryman leaks, and the boat's eager read in both legs
    "kitcell_first_read": ("S166-A-KITOFF", "S166-A-FERRYOFF"),  # the boat's eager read is never a pass's first: it leaks
    "kitcell_uncounted": ("S166-A-KITOFF", "S166-A-FERRYOFF"),
    "kitcell_last_stale": ("S166-A-KITOFF", "S166-A-FERRYOFF"),
    "kitcell_silent": ("S166-A-KITOFF", "S166-A-FERRYOFF"),
    "kitcell_stock": ("S166-A-KITOFF",),                   # entry 1's stock read closed too: closed +3 (0, 1 and 15)
    "kitcell_menu_leak": (),                               # the ~ menu's hold: no harness verb drives it (the stand-in's own row)
    "kitcell_lever_ignored": (),                           # the lever's own effect: the calibration's (S166-CAL) -- tests pin it
    "kitcell_lever_stuck": ("S166-R",),
    # [ff9mapkit netsync s166] A0b's: the solo bench is exempt from term 3 and never arms (it never mirrors) -- byte-identical to A0
    "pairpull_early": (),
    "pairpull_unarmed": (),
    "pairpull_lever_ignored": (),
    "chord_gate_open": (),                                 # the solo bench never mirrors and never presses the chord
}
#: ...and under the entry order with entry 1 FIRST (fakegame.FAKE_WORLD_KIT_ORDER_E1_FIRST): what changes there
ORDER_FAULT_REDS = {"kitcell_first_read": ("S166-A-KITOFF", "S166-A-FERRYOFF"),
                    "kitcell_stock": ("S166-A-KITOFF",)}


# ================================================================================================ pure readers / judges
def _k(x, key, default=None):
    """A ``netsync.world.kitcell`` leaf (absent = ``default``: an engine before s166)."""
    return cb.path(x, "netsync.world.kitcell." + key, default)


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def kdelta(a, b, key="closed"):
    """b's ``netsync.world.kitcell.<key>`` - a's; None when either is unread (never a zero)."""
    va, vb = _num(_k(a, key)), _num(_k(b, key))
    return None if va is None or vb is None else vb - va


def stage_of(x) -> int:
    """166 when the engine publishes `netsync.world.kitcell`; else coop_world_follow's reading (165 with `netsync.world.out`)."""
    return 166 if cb.has(x, PROBE) else wf.stage_of(x)


def map_byte(x, i: int):
    """Byte ``i`` of the live event context's MAP vars (the top-level `world.mapvar` digest: 160 hex digits), None off the world."""
    hx = cb.path(x, "world.mapvar")
    if not isinstance(hx, str) or len(hx) < 2 * (int(i) + 1):
        return None
    try:
        return int(hx[2 * int(i):2 * int(i) + 2], 16)
    except ValueError:
        return None


def next_mode(x):
    return _num(cb.path(x, "world.next_mode"))


def kit_hazard(samples) -> tuple:
    """(PURE) Today's hazard over the samples after the press: (seen, reached 6603, why) -- a FieldHUD sample on the kit cell's field
    (the guest went in alone) or the world's shutdown armed toward a field (`world.next_mode` 1)."""
    field = [s for s in samples if s.ui_state == "FieldHUD"]
    shut = [s for s in samples if s.ui_state == "WorldHUD" and next_mode(s) == 1]
    reached = any(s.field_id == KIT_FIELD for s in field)
    seen = bool(field or shut)
    why = ("FieldHUD " + "/".join(str(f) for f in sorted({s.field_id for s in field})) + " reached" if field else
           ("the world's shutdown armed toward a field (next_mode 1)" if shut else "no hazard"))
    return seen, reached, why


def ferry_hazard(samples) -> tuple:
    """(PURE) The ferryman's scene over the samples after the press: (seen, why) -- Map[50] nonzero on any sample."""
    vals = sorted({v for v in (map_byte(s, BW.KIT_MAP_FERRY) for s in samples) if v})
    return bool(vals), (f"Map[50] read {vals} (the scene played)" if vals else "Map[50] 0 throughout")


def judge_probe(st, lines) -> tuple:
    """P0 (PURE): `netsync.world` = s165's eight then `kitcell` (the prefix law: s165's keys unmoved, kitcell right after `dot`), its
    keys the contract's in order, and the proof line OK -- none FAIL."""
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}` -- an engine before s166"
    world = cb.path(st, "netsync.world") or {}
    want = list(BW.WORLD_SENTINELS_S166)
    got = list(world)
    keys_ok = got[:len(want)] == want and list(world.get("kitcell") or {}) == list(BW.WORLD_KITCELL_SENTINELS)
    rx = re.compile(BW.WORLD_WALK_PROOF_RE)
    oks = [m.group(0) for m in (rx.search(ln) for ln in lines) if m]
    fails = cb.count(lines, BW.PROOF_WORLD_WALK + "FAIL")
    ok = keys_ok and bool(oks) and not fails
    return ok, (f"world {got} (want the prefix {want}); kitcell {list(world.get('kitcell') or {})}; proof {oks[:1] or 'NONE'}; "
                f"FAIL lines {fails}")


def judge_rest(st, *, lever_old: bool = False) -> tuple:
    """P1 (PURE): the bench on and `kitcell` at rest ('act'), or (``lever_old``) the calibration lever read back ('old')."""
    if not cb.has(st, PROBE):
        return False, f"absent: no `{PROBE}` (the lever's key)"
    want = "old" if lever_old else "act"
    got, bench = _k(st, "lever"), cb.path(st, "netsync.bench")
    return got == want and bench is True, f"kitcell.lever {got!r} (want {want!r}); netsync.bench {bench!r}"


def frozen(x) -> bool:
    """`netsync.world.freeze.on` (HarnessWorldFreezeOn: the WorldMap scene AND WorldFreezeNow) reads true -- the only input decision 19
    keys its close on besides the read itself."""
    return x is not None and cb.path(x, BW.WORLD_FREEZE_ON_KEY) is True


def _freeze_word(x) -> str:
    if x is None:
        return "no state"
    return f"freeze.on {cb.path(x, BW.WORLD_FREEZE_ON_KEY)!r}, why {cb.path(x, BW.WORLD_FREEZE_WHY_KEY)!r}"


def freeze_held(base, samples) -> tuple:
    """THE FREEZE INSTRUMENT (PURE): decision 19 closes only under WorldFreezeNow, so the hazard it closes is a FROZEN guest's -- the
    press made frozen (``base``) and the freeze still on at every judged sample after it: each WorldHUD sample on WORLD until today's
    hazard first shows (the world's shutdown toward a field, `next_mode` 1, or another scene: from there the world's own exit owns the
    samples). (held, why); a lift names its frame and the term."""
    if not frozen(base):
        return False, f"the freeze lifted before the press -- OFF at it ({_freeze_word(base)})"
    n = 0
    for s in samples:
        if s.ui_state != "WorldHUD" or s.world_id != WORLD or next_mode(s) == 1:
            break
        if not frozen(s):
            return False, f"the freeze lifted at frame {s.frame} ({_freeze_word(s)}), {n} judged sample(s) after the press"
        n += 1
    return True, f"frozen at the press ({_freeze_word(base)}) and on all {n} judged sample(s) after it"


def judge_landing(st) -> tuple:
    """The route's instrument (PURE): the first judged world sample on WorldHUD 9011, within POSE_TOL (torus) of FS_LANDING, on foot.
    (FS_LANDING is in the 6603 cell but OFF its trigger: no leg presses here.)"""
    if st is None:
        return False, "not judged: no sample with the blocks in and the world ticking (THE PRE-INIT SAMPLE)"
    x, z = wf.world_xz(st)
    if st.ui_state != "WorldHUD" or st.world_id != WORLD or x is None:
        return False, f"not on world {WORLD} (ui {st.ui_state!r}, world {st.world_id})"
    d, v = wf.torus((x, z), FS_LANDING), st.vehicle
    ok = d <= POSE_TOL and v == 0
    return ok, f"landed at ({x:.1f}, {z:.1f}): {d:.1f}u from {FS_LANDING} (want <= {POSE_TOL:g}), [190] {v}"


def judge_kit_stand(st) -> tuple:
    """A-KITOFF's instrument (PURE): on WorldHUD 9011, within KIT_TRIGGER_R (torus) of the 6603 trigger AND on its event tiles (the
    census: BW.KIT_TRIGGER_TILES -- where the engine requests the cell's function), on foot, FROZEN."""
    if st is None:
        return False, "no state"
    x, z = wf.world_xz(st)
    if st.ui_state != "WorldHUD" or st.world_id != WORLD or x is None:
        return False, f"not on world {WORLD} (ui {st.ui_state!r}, world {st.world_id})"
    d = wf.torus((x, z), KIT_TRIGGER)
    on = BW.kit_trigger_field(WORLD, x, z)
    fz = frozen(st)
    ok = d <= KIT_TRIGGER_R and on == KIT_FIELD and st.vehicle == 0 and fz
    return ok, (f"at ({x:.1f}, {z:.1f}): {d:.1f}u from the {KIT_FIELD} trigger {KIT_TRIGGER} (want <= {KIT_TRIGGER_R:g}), on its "
                f"event tiles: {'yes' if on == KIT_FIELD else 'NO'} (cell {BW.world_cell(x, z)}); [190] {st.vehicle}; "
                f"{'FROZEN' if fz else 'NOT FROZEN'} ({_freeze_word(st)})")


def judge_ferry_stand(st) -> tuple:
    """A-FERRYOFF's instrument (PURE): on WorldHUD 9011, inside the ferryman's +-12 u box, NOT on a kit cell, on foot, Map[50] and
    Map[51] 0 (no scene, not its arrival branch), FROZEN."""
    if st is None:
        return False, "no state"
    x, z = wf.world_xz(st)
    if st.ui_state != "WorldHUD" or st.world_id != WORLD or x is None:
        return False, f"not on world {WORLD} (ui {st.ui_state!r}, world {st.world_id})"
    inside = BW.in_kit_box(FERRY_AT, BW.KIT_FERRY_RANGE, x, z)
    on_cell = BW.kit_cell_field(WORLD, x, z)
    m50, m51 = map_byte(st, BW.KIT_MAP_FERRY), map_byte(st, BW.KIT_MAP_FERRY_ARRIVAL)
    fz = frozen(st)
    ok = inside and on_cell is None and st.vehicle == 0 and m50 == 0 and m51 == 0 and fz
    return ok, (f"at ({x:.1f}, {z:.1f}): {'inside' if inside else 'OUTSIDE'} the ferryman's +-{BW.KIT_FERRY_RANGE:g} u box round "
                f"{FERRY_AT}; kit cell {on_cell}; [190] {st.vehicle}; Map[50] {m50}, Map[51] {m51}; "
                f"{'FROZEN' if fz else 'NOT FROZEN'} ({_freeze_word(st)})")


def _close_lines(lines, sid: int) -> list:
    return [ln for ln in lines if BW.kitcell_line_names(ln, sid, WORLD)]


def witness_readers(sid: int) -> tuple:
    """The entries that read one press on the leg's stand (PURE): the leg's own reader, then every reader that reads each Confirm on
    WORLD wherever the walker stands (BW.KIT_EAGER_READERS: 9011's boat, entry 15, through @00174's eager KEYON)."""
    return (sid,) + tuple(e for e in BW.KIT_EAGER_READERS.get(WORLD, ()) if e != sid)


def judge_witness(base, last, lines, sid: int) -> tuple:
    """The close's witness (PURE): `closed` up since ``base`` by exactly one per reader of the press (witness_readers: on 9011 the
    leg's entry AND the boat's eager read, so +2), last_sid one of them (their order in a frame is the engine's), last_world 9011,
    the lever 'act', and one close line naming entry ``sid`` and the world."""
    if not cb.has(last, PROBE):
        return False, f"absent: no `{PROBE}`"
    readers = witness_readers(sid)
    dc = kdelta(base, last)
    ls, lw, lev = _k(last, "last_sid"), _k(last, "last_world"), _k(last, "lever")
    n = len(_close_lines(lines, sid))
    ok = dc == len(readers) and ls in readers and lw == WORLD and lev == "act" and n == 1
    return ok, f"kitcell closed +{dc} (want {len(readers)}: entries {list(readers)}), last_sid {ls} (want one of {list(readers)}), " \
               f"last_world {lw} (want {WORLD}), lever {lev!r}; the close line naming entry {sid} {n}x (want 1)"


def control_held_off(base, samples) -> tuple:
    """The legs' instrument (PURE): the press was made control-OFF (``base``) and control stayed off on every WorldHUD sample after it
    -- a control-on read is s144's mask, never decision 19's close, so a window where something gave control back judges nothing."""
    on = sum(1 for s in samples if s.ui_state == "WorldHUD" and s.control)
    ok = base is not None and base.control is False and on == 0
    return ok, f"control {'OFF' if base is not None and base.control is False else 'ON'} at the press, on {on} WorldHUD sample(s) after"


def judge_kitoff(base, samples, lines) -> tuple:
    """A-KITOFF (PURE over the samples first published after the press): THE FREEZE INSTRUMENT first (a lift judges nothing: "not
    reached"); then every sample WorldHUD 9011, never FieldHUD (6603), never `next_mode` 1, control off throughout -- and the close's
    witness for entry 0."""
    if not samples:
        return False, "not reached: no sample after the press"
    off = [(s.ui_state, s.field_id if s.ui_state == "FieldHUD" else s.world_id) for s in samples
           if not (s.ui_state == "WorldHUD" and s.world_id == WORLD)]
    seen, _reached, hz = kit_hazard(samples)
    f_ok, f_why = freeze_held(base, samples)
    c_ok, c_why = control_held_off(base, samples)
    w_ok, w_why = judge_witness(base, samples[-1], lines, BW.KIT_CELL_SID)
    detail = (f"{len(samples)} sample(s): " + (f"LEFT WorldHUD {WORLD}: {sorted(set(off))[:4]}" if off else f"all WorldHUD {WORLD}")
              + f"; {hz}; {c_why}; {w_why}")
    if not f_ok:
        return False, f"not reached (the instrument): {f_why} -- the close keys on the freeze, so this window judges nothing; {detail}"
    ok = not off and not seen and c_ok and w_ok
    return ok, f"{f_why}; {detail}"


def judge_ferryoff(base, samples, lines) -> tuple:
    """A-FERRYOFF (PURE over the samples first published after the press): THE FREEZE INSTRUMENT first (a lift judges nothing: "not
    reached"); then Map[50] 0 on every sample (each sample's digest read), no scene fade (`fading` false), every sample WorldHUD 9011,
    control off throughout -- and the close's witness for entry 16."""
    if not samples:
        return False, "not reached: no sample after the press"
    unread = sum(1 for s in samples if map_byte(s, BW.KIT_MAP_FERRY) is None)
    seen, hz = ferry_hazard(samples)
    fades = sum(1 for s in samples if s.fading)
    off = [(s.ui_state, s.world_id) for s in samples if not (s.ui_state == "WorldHUD" and s.world_id == WORLD)]
    f_ok, f_why = freeze_held(base, samples)
    c_ok, c_why = control_held_off(base, samples)
    w_ok, w_why = judge_witness(base, samples[-1], lines, BW.KIT_FERRY_SID)
    detail = (f"{len(samples)} sample(s): {hz}" + (f" ({unread} sample(s) with no MAP digest)" if unread else "")
              + f"; fading on {fades} sample(s); " + (f"LEFT WorldHUD {WORLD}: {off[:3]}" if off else f"all WorldHUD {WORLD}")
              + f"; {c_why}; {w_why}")
    if not f_ok:
        return False, f"not reached (the instrument): {f_why} -- the close keys on the freeze, so this window judges nothing; {detail}"
    ok = not seen and not unread and not fades and not off and c_ok and w_ok
    return ok, f"{f_why}; {detail}"


def judge_release(pulled: bool, n_lines: int, st2, forced) -> tuple:
    """R (PURE): the role released, a lever was pulled before the reset, the release line once, and the re-read with the role reads
    `kitcell` 'act'."""
    lev = _k(st2, "lever") if st2 is not None else None
    ok = forced is False and pulled and n_lines == 1 and lev == "act"
    return ok, (f"forced={forced!r}; a lever pulled before the reset: {pulled}; the release line {n_lines}x (want 1); re-read with "
                f"the role: kitcell.lever {lev!r} (want 'act')")


def judge_cal(failed, predicted, measured: dict, legs_run) -> tuple:
    """S166-CAL (PURE): every ``predicted`` row red and nothing else (``failed``: the ledger's reds, the CAL row excepted), AND every
    selected leg row (``legs_run``) RAN and MEASURED its hazard -- OLD (and the lever) are today's hazard, never a row merely red (a
    leg whose landing failed is red too, and would otherwise pass the prediction)."""
    failed, predicted = set(failed), set(predicted)
    missing, extra = sorted(predicted - failed), sorted(failed - predicted)
    unmeasured = sorted(r for r in legs_run if not measured.get(r))
    ok = not missing and not extra and not unmeasured
    return ok, (f"predicted reds that stayed GREEN: {missing or 'none'}; unpredicted reds: {extra or 'none'}; leg rows whose hazard "
                f"was NOT measured: {unmeasured or 'none'} (measured: {measured or 'none'})")


# ================================================================================================ the offline oracle
def read_kit_oracle(game: Path) -> dict:
    """S166-OR's kit half (READ-ONLY): the deployed WORLD11 (the highest-priority folder shipping it) read with the kit's pure reader --
    entry 0's (2, 13) cell function (tag 0x8D09) reads KEYON and names Field(6603); entries 15 and 16 exist and stand at BOAT_SPAWN and
    FERRY_AT (their func0 MoveInstantXZY, fixed-point / 256); the stock dispatcher's last entry is 14 (so 15 and 16 are the kit's)."""
    out = {"problems": {}, "facts": {}}
    web, where = cw.deployed_world_eb(Path(game))
    out["facts"]["world_eb"] = where
    if web is None:
        out["problems"]["world eb"] = f"no stacked folder ships {cw.WORLD_EB_NAME} (the kit's WORLD11 is not deployed)"
        return out
    try:
        cw._kit()
        from ff9mapkit.eb.model import EbScript
        from ff9mapkit.eb import cmdasm
        from ff9mapkit.world import entrance as WE
        eb = EbScript.from_bytes(web)

        def text(e, f) -> str:
            return "\n".join(t for _o, t in cmdasm.disassemble_items(web, f.abs_start, f.abs_end)) if f.length else ""

        entries = {e.index: e for e in eb.entries if not e.empty}
        tag = WE.pack_cell_tag(*KIT_CELL, 1)
        cellf = [f for f in entries[0].funcs if f.tag == tag] if 0 in entries else []
        body = text(entries[0], cellf[0]) if cellf else ""
        out["facts"]["cell"] = f"0x{tag:04X}: {'present' if cellf else 'ABSENT'}"
        if not cellf:
            out["problems"]["cell"] = f"entry 0 has no cell function 0x{tag:04X} (cell {KIT_CELL})"
        elif "B_KEYON" not in body or str(KIT_FIELD) not in body:
            out["problems"]["cell"] = f"entry 0's 0x{tag:04X} does not read KEYON and enter {KIT_FIELD}"
        mv = re.compile(r"MoveInstantXZY\(\{const4?\((-?\d+)\) B_EXPR_END\}, \{const4?\((-?\d+)\) B_EXPR_END\}, "
                        r"\{const4?\((-?\d+)\) B_EXPR_END\}\)")
        for sid, at, name in ((BW.KIT_BOAT_SID, BW.KIT_BOAT_AT, "boat"), (BW.KIT_FERRY_SID, BW.KIT_FERRY_AT, "ferryman")):
            e = entries.get(sid)
            f0 = [f for f in e.funcs if f.tag == 0] if e is not None else []
            m = mv.search(text(e, f0[0])) if f0 else None
            pos = (int(m.group(1)) / 256.0, int(m.group(3)) / 256.0) if m else None
            out["facts"][name] = pos
            if pos is None or abs(pos[0] - at[0]) > 1.0 or abs(pos[1] - at[1]) > 1.0:
                out["problems"][name] = f"entry {sid}'s func0 places it at {pos}, not {at}"
        out["facts"]["entries"] = sorted(entries)
    except Exception as err:                              # noqa: BLE001 - a parse fault is a named problem
        out["problems"]["world eb"] = f"{where}: {type(err).__name__}: {str(err)[:200]}"
    trig = read_trigger_oracle(Path(game))
    out["facts"]["trigger"] = trig["fact"]
    if trig["problem"]:
        out["problems"]["trigger"] = trig["problem"]
    return out


def _tri_key(pts) -> frozenset:
    return frozenset((round(float(a), 2), round(float(b), 2)) for a, b in pts)


def read_trigger_oracle(game: Path, cell=None) -> dict:
    """S166-OR's trigger half (READ-ONLY): the walkable Terrain of KIT_STAND's block from the highest-priority stacked folder that
    overrides it (Disc1/0_1), read with the kit's own reader -- its event-id triangles in the 6603 cell exactly
    BW.KIT_TRIGGER_TILES[cell] (the census the stand-in and the stand judge read), and KIT_STAND on one of them. {fact, problem}."""
    cell = tuple(cell or KIT_CELL)
    bx, by = int(KIT_STAND[0] // 64), int((-KIT_STAND[1]) // 64)
    name = f"Block[{bx}][{by}] Terrain.ff9mesh"
    path, src = None, None
    for folder in cw.folder_order(Path(game)):
        p = Path(game) / folder / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / f"r{by}" / name
        if p.is_file():
            path, src = p, folder
            break
    if path is None:
        return {"fact": f"{name}: no override", "problem": f"no stacked folder overrides {name} (the {KIT_FIELD} trigger is the kit's)"}
    try:
        cw._kit()
        from ff9mapkit.world import mesh as WM
        from ff9mapkit.world import extract as WX
        bm = WM.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by)
        ox, oz = WX.block_world_origin(bx, by)
        got = set()
        for t in bm.tris:
            if not WX.decode_id(int(round(bm.tangents[t[0]][0])))["event"]:
                continue
            pts = [(bm.verts[i][0] + ox, bm.verts[i][2] + oz) for i in t]
            cx, cz = sum(p[0] for p in pts) / 3.0, sum(p[1] for p in pts) / 3.0
            if BW.world_cell(cx, cz) == cell:
                got.add(_tri_key(pts))
    except Exception as err:                              # noqa: BLE001 - a parse fault is a named problem
        return {"fact": f"{path}", "problem": f"{path}: {type(err).__name__}: {str(err)[:200]}"}
    want = {_tri_key(t) for t in BW.KIT_TRIGGER_TILES.get(cell, ())}
    on = BW.kit_trigger_field(WORLD, *KIT_STAND)
    fact = f"{src}/{name}: {len(got)} event tile(s) in cell {cell}"
    problem = None
    if got != want:
        problem = (f"{name}'s event tiles in cell {cell} are not the census's ({len(got)} read, {len(want)} in "
                   f"battlewire.KIT_TRIGGER_TILES; {len(got - want)} new, {len(want - got)} gone): re-census before the bench")
    elif on != KIT_FIELD:
        problem = f"KIT_STAND {KIT_STAND} is not on the {KIT_FIELD} trigger's tiles"
    return {"fact": fact, "problem": problem}


# ================================================================================================ the moves
def _ww(g, *args) -> tuple:
    """`netsync worldwalk <args>` (ok, why) -- callers PROBE first: never sent to an engine without `netsync.world.kitcell`."""
    return cb.try_ns(g, "worldwalk", *args)


def _control(g, on: bool):
    """`control 0|1`, then THE ORDER SKEW: the first sample reading it, plus SKEW_FRAMES (the flip's own publish dropped)."""
    g.control(on)
    st = cb.poll(g, lambda s: bool(s.control) is bool(on), CONTROL_S, f"control {'on' if on else 'off'}")
    g.wait_frames(SKEW_FRAMES)
    return st


def _land(g, ctx: dict) -> tuple:
    """6603 -> 9011 by s165's follow-out with the bench host AT FS_LANDING: (instrument ok, why). The bench host is off after it, as
    s165's own FROZEN row has it: the freeze here is `bench 1` on the selftest role (freeze.why 'bench'), not the bench host."""
    if not wf._home(g, ctx):
        return False, f"not on FieldHUD {FARSHORE} before the follow-out"
    base = g.state
    ok, why = wf._frame(g, *FS_LANDING)
    if not ok:
        return False, f"`worldfollow host {FS_LANDING[0]:g} {FS_LANDING[1]:g}` refused: {why}"
    samples = wf._land(g, base, LEAVE_S)
    st = wf.first_judged([s for s in samples if s.ui_state == "WorldHUD"])
    wf._host_off(g)
    g.wait_frames(SETTLE_FRAMES)
    return judge_landing(st)


def _watch_press(g, seconds: float, hazard, *, settle=None) -> list:
    """A Confirm press (PRESS_FRAMES), then every sample first published after it for ``seconds``; once ``hazard(samples)`` sees today's
    hazard, watched on up to HAZARD_S until ``settle`` holds (OLD: the kit cell's load measured to its end, FieldHUD settled) -- or,
    with no ``settle``, half a second more."""
    g.press("confirm", PRESS_FRAMES)
    samples, _ = cb.watch(g, lambda s: False, seconds)
    if hazard(samples):
        if settle is not None:
            more, _ = cb.watch(g, settle, HAZARD_S)
            samples += more
        samples += cb.hold_for(g, 0.5)
    return samples


# ================================================================================================ the run
def run(g, field: int | None = None):
    if field is not None and field != FARSHORE:
        g.note(f"--field {field} is ignored: the bench runs on {FARSHORE} and the world map")
    if _RAW_LEG.strip().lower() == PAIR_LEG:              # [ff9mapkit netsync s166] A0b's T2 leg: its own launch, its own rows
        _run_pair(g)
        return
    calibrate = cb.CALIBRATE
    legs = SOLO_LEGS or LEGS
    led = cb.Ledger(g, solo_catalog(calibrate, legs, LEVER), finals=("S166-R", "S166-CAL"), width=DETAIL_W)
    ctx = {"calibrate": calibrate, "stage": None, "pulled": None, "legs": legs, "measured": {}}
    if SOLO_LEGS is None:
        led.check("S166-INI", False, f"COOP_WW_LEG={_RAW_LEG!r} names no leg: one of {LEGS} (or 'all')")
        led.close("no leg selected", final=True)
        return
    if calibrate and len(legs) != 1:
        led.check("S166-CAL", False, f"EACH DESTRUCTIVE LEG NEEDS ITS OWN LAUNCH: COOP_CALIBRATE=1 needs COOP_WW_LEG naming exactly "
                                     f"one of {LEGS} (got {_RAW_LEG!r}) -- nothing was launched")
        led.close("not launched: a calibration names exactly one leg", final=True)
        return
    try:
        _solo(g, led, ctx)
    except HarnessError as err:
        g.note(f"the solo leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'world-walk-solo')}")
        led.close()
        _release_solo(g, led, ctx)
        if calibrate:
            stage = ctx.get("stage")
            if stage is None:
                led.check("S166-CAL", False, "no engine stage was read (the run died before P0)")
            else:
                pred = OLD_PREDICTED if stage < 166 else LEVER_PREDICTED.get(LEVER or "", ())
                pred = [c for c in pred if c in led.catalog]
                g.note(f"S166-CAL: s{stage}, lever {LEVER!r}: predicted reds {sorted(pred)}")
                legs_run = [LEG_ROW[leg] for leg in ctx["legs"]]      # every selected leg must have RUN and measured its hazard
                led.check("S166-CAL", *judge_cal(led.failed() - {"S166-CAL"}, pred, ctx["measured"], legs_run))
        led.close(final=True)


def _solo(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why = wf._ini_ok(g)
    led.check("S166-INI", ok, why)
    if not ok:
        led.close("the install's ini refuses the bench (S166-INI): write [Netsync] Enabled 0 + FollowHost 1 BEFORE launch "
                  "(solo_ini.py) -- nothing was sent")
        return
    oracle = cw.read_oracle(Path(g.game_path))
    kit = read_kit_oracle(Path(g.game_path))
    problems = {**oracle["problems"], **kit["problems"]}
    led.check("S166-OR", not problems, f"problems {problems or 'none'}; read {kit['facts']}")
    ok, why = cb.setup(g, FARSHORE, label="s166 A0: world-map co-op, the control-off kit-cell close -- the solo bench"
                                          + (" -- CALIBRATION" if ctx["calibrate"] else ""))
    led.check("S166-S0", ok and g.state.field_id == FARSHORE, why + f"; on field {g.state.field_id}")
    if not ok:
        led.close(f"the selftest role never came up -- {why}")
        return
    st = g.state
    ctx["stage"] = stage_of(st)
    g.note(f"engine stage: s{ctx['stage']} ({cb.stage_note(st)})")
    led.check("S166-P0", *judge_probe(st, cb.log_lines(g)))
    _p1(g, led, ctx)
    if not cb.has(g.state, ROUTE_PROBE):
        led.close(f"not reached: no `{ROUTE_PROBE}` -- an engine before s165 has no follow-out to land this bench")
        return
    if ctx["stage"] < 166 and not ctx["calibrate"]:
        led.close(f"not reached: an engine before s166 (no `{PROBE}`) -- nothing new to judge; COOP_CALIBRATE=1 with one leg "
                  "(COOP_WW_LEG) measures its hazard (OLD)")
        return
    if ctx["stage"] < 166:
        g.note(f"s{ctx['stage']}: no `{PROBE}` -- no `worldwalk` op is EVER sent; the leg MEASURES today's hazard (OLD)")
    for leg in LEGS:
        if leg in ctx["legs"]:
            (_leg_kitoff if leg == "kitoff" else _leg_ferryoff)(g, led, ctx)


def _p1(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why = cb.try_ns(g, "bench", 1)
    st = cb.poll(g, lambda s: (s.netsync or {}).get("bench") is True, 3.0, "the field-gate bench") or g.state
    if not ok:
        led.check("S166-P1", False, f"`netsync bench 1` refused: {why}")
        return
    if ctx["stage"] >= 166 and ctx["calibrate"] and LEVER:
        okl, whyl = _ww(g, LEVER, "old")
        st = cb.poll(g, lambda s: _k(s, "lever") == "old", 3.0, f"the calibration lever {LEVER}") or g.state
        ctx["pulled"] = LEVER if okl else None
        led.check("S166-P1", okl and _k(st, "lever") == "old", whyl or f"`worldwalk {LEVER} old` pulled: " + judge_rest(
            st, lever_old=True)[1])
        g.note(f"CALIBRATION: `worldwalk {LEVER} old` pulled -- held through the run")
        return
    led.check("S166-P1", *judge_rest(st))


def _stand(g, led: cb.Ledger, ctx: dict, cid: str, xz, judge) -> bool:
    """The leg's stand: on the world map (else the route's landing), control ON for the teleport (the overworld teleport sticks only
    with control live; a frozen guest's control-on reads are s144's mask, so it presses nothing there), the teleport onto ``xz`` and
    its instrument ``judge`` (the stand, on foot, FROZEN). False (the row written "not reached") when any of it fails."""
    if g.state.ui_state != "WorldHUD" or g.state.world_id != WORLD:
        ok, why = _land(g, ctx)
        if not ok:
            led.check(cid, False, f"not reached (the instrument): {why}")
            return False
    _control(g, True)
    try:
        st = cw.teleport_settle(g, xz)
    except HarnessError as err:
        led.check(cid, False, f"not reached: the teleport onto {xz} raised: {str(err)[:200]}")
        return False
    ok, why = judge(st)
    if not ok:
        led.check(cid, False, f"not reached (the instrument): {why}")
        return False
    return True


def _press_leg(g, led: cb.Ledger, ctx: dict, cid: str, seconds: float, hazard, judge, *, settle=None) -> None:
    """`control 0`, the press and its window, the row; the hazard counts as MEASURED only with the freeze held through the window (the
    hazard decision 19 closes is a frozen guest's). Control back on after, while still on the world map."""
    try:
        if _control(g, False) is None:
            led.check(cid, False, "not reached: `control 0` never read back")
            return
        base, at = g.state, cb.mark(g)
        samples = _watch_press(g, seconds, lambda ss: hazard(ss)[0], settle=settle)
        seen, hz = hazard(samples)
        held, f_why = freeze_held(base, samples)
        ctx["measured"][cid] = seen and held
        led.check(cid, *judge(base, samples, cb.new(g, at)))
        if seen:
            g.note(f"{cid}: TODAY'S HAZARD " + (f"measured, frozen -- {hz}" if held else f"seen but NOT measured ({f_why}) -- {hz}"))
    finally:
        if g.state.ui_state == "WorldHUD":
            _control(g, True)


def _kit_seen(samples) -> tuple:
    seen, reached, hz = kit_hazard(samples)
    return seen, hz + ("" if reached or not seen else f" (FieldHUD {KIT_FIELD} not seen)")


def _leg_kitoff(g, led: cb.Ledger, ctx: dict) -> None:
    """A-KITOFF: the route's landing (FS_LANDING, off the trigger), the stand ON the 6603 trigger, then the press."""
    cid = LEG_ROW["kitoff"]
    ok, why = _land(g, ctx)
    if not ok:
        led.check(cid, False, f"not reached (the instrument): {why}")
        return
    if not _stand(g, led, ctx, cid, KIT_STAND, judge_kit_stand):
        return
    _press_leg(g, led, ctx, cid, KITOFF_S, _kit_seen, judge_kitoff, settle=lambda s: s.ui_state == "FieldHUD" and s.control)


def _leg_ferryoff(g, led: cb.Ledger, ctx: dict) -> None:
    """A-FERRYOFF: the stand inside the ferryman's box (off every kit cell), then the press."""
    cid = LEG_ROW["ferryoff"]
    if not _stand(g, led, ctx, cid, FERRY_STAND, judge_ferry_stand):
        return
    _press_leg(g, led, ctx, cid, FERRY_S, ferry_hazard, judge_ferryoff)


def _release_solo(g, led: cb.Ledger, ctx: dict) -> None:
    """A lever pulled (stage >= 166), then `reset` (HarnessSelfTest(false) -> HarnessReleaseBench -> the worldwalk release): the role
    released, the release line once; then the re-read WITH the role. One verdict after both reads."""
    stage = ctx.get("stage") or 0
    pulled = _ww(g, "kitcell", "old")[0] if stage >= 166 else False
    at = cb.mark(g)
    try:
        cb.release(g)
    except HarnessError as err:
        led.check("S166-R", False, f"`reset` failed: {str(err)[:300]}")
        return
    forced = (g.state.netsync or {}).get("forced")
    if stage < 166:
        led.check("S166-R", forced is False, f"forced={forced!r} (an engine before s166: no worldwalk lever to release)")
        return
    n = cb.count(cb.wait_log(g, at, BW.LOG_WORLDWALK_RELEASED, 2.0), BW.LOG_WORLDWALK_RELEASED)
    st2, why = cb.reread_with_role(g)
    ok, detail = judge_release(pulled, n, st2, forced)
    led.check("S166-R", ok, detail + (f"; {why}" if why else ""))


# ================================================================================================ [ff9mapkit netsync s166] PIECE A0b
# DECISION 26, THE PAIRING PULL (second and alone: its OLD is the A0 build). T2-A pair (COOP_WW_LEG=pair) and D-PAIR (duo.py --no-pair):
# the guest pairs ON ITS OWN FIELD while the host already stands on 9011, and is pulled out once its pairing autosave has resolved.
PAIR_LEG = "pair"
#: the capability: key PRESENCE (State.coop_world_pairpull) -- the A0 build has `kitcell` and no `pairpull`, and the bench never sends
#: `worldwalk pairpull` there
PAIR_PROBE = "netsync.world.pairpull"
_RAW_PAIR_FROM = os.environ.get("COOP_WW_PAIR_FROM", "").strip()
#: THE --from SECOND on COOP_TAPE_WORLD_WALK (20261101-230914-host6603-world-walk-s164.f9tape, recorded on s164, v14), read off the tape
#: with coop_peer's own pose tooling (`py tools/harness/coop_peer.py where <tape> --pose --every 1`, read-only, 2026-11-02): the host left
#: 6603 at 29.88 s (b6 from that frame, [102] 11, on foot, entrance 35), its heartbeat FROZE 30.89-35.94 s (its own all-block load), moved
#: again from 36.95 s, the host stood at ICE_TILE (1197.37, -796.7) from 40.99 s to 118.25 s on foot, and entered 300 at 118.71 s. At
#: 45.0 s the host has been live on the world map ~8 s (past THE LIVE DEBOUNCE's 1200 ms), stands at the tile -- 538 u (torus) from
#: FS_LANDING, so the landing can only be a follow-out's -- and the stand lasts 73 s more (the pull, the rows) before the tape's 300 (the
#: rejoin). COOP_WW_PAIR_FROM overrides it; T2-TAPE re-reads every one of those facts at the second used (pair_from_facts).
PAIR_FROM_S = float(_RAW_PAIR_FROM) if _RAW_PAIR_FROM.replace(".", "", 1).isdigit() else 45.0
PAIR_LIVE_S = BW.WORLD_OUT_DEBOUNCE_MS / 1000.0   # the host live on the world map at least this long before --from
PAIR_HB_FRESH_S = BW.WORLD_OUT_ALIVE_MS / 1000.0  # ...its heartbeat moved within this of --from
PAIR_ROOM_S = 40.0        # ...and the tile stand lasts at least this long after it (the dial, the autosave, the pull, the rows)
PAIR_S = 30.0             # the replay's start -> the guest's host cache reading the host's b6 (the dial is already up)
PAIR_OUT_S = 60.0         # the host's b6 read -> the guest's first judged world sample (the debounce, the fade, the ~4.4 s load)
PAIR_TOWER_S = 15.0       # the 300 entry anchor's slack (OLD: the wait is measured up to it)
SAVEMENU_OPEN_S = 2.0     # `savemenu` -> a 'Serialize' sample if the chord opens the menu (s165's solo save leg: 2-32 frames)
#: the leg's own lever (the calibration on A0b): `worldwalk pairpull old` sent BEFORE the replay, held through the leg
PAIR_LEVER = "pairpull"

T2_PAIR_CHECKS = {
    "S166-PR-I": "the instrument: from the replay's start until the guest's host cache reads the host's b6 -- the guest on FieldHUD 6603, "
                 "NOT mirroring, no 'paired on the host's field' kick, no ARMED line (paired on its own field, never mirrored); on A0b "
                 "`pairpull` read back at its lever word",
    "S166-PR-SAVE": "THE PAIRING AUTOSAVE: 'pairing autosave written on field 6603 (the pairing window)' after the replay's start and "
                    "BEFORE the follow-out's start line; no 'no pairing autosave this session' line",
    "S166-PR-OUT": "the pull: WorldHUD 9011 within PAIR_OUT_S of the host's b6 read, starts / commits / lands +1 and their lines (after "
                   "block_ready + ticks), out.why never 'not_mirroring' after the autosave",
    "S166-PR-POSE": "the landing within POSE_TOL of the TAPE's own section-0 pose over the seam bracket, >= FAR_U (plain) from "
                    "FS_LANDING; out.last.frame latest / pin",
    "S166-PR-ARM": "the arm at the landing: mirroring true from the first judged world sample on, pairpull.arms +1 with last_world 9011, "
                   "'state-mirror ARMED at world map 9011's landing' ONCE and no field-form ARMED line",
    "S166-PR-SAVEMENU": "on the world map, `worldfollow saveguard old` (DRY) and Alt+F5: the CHORD refuses (s38's mirror gate, ahead of "
                        "the menu) -- no save menu, refused +0 / would_save +0; at the press WorldHUD 9011, menu_refusal.now 'audible', "
                        "mirroring, the lever 'old', one `savemenu` event from WorldHUD (an unarmed guest opens it: would_save +1), the "
                        "sandbox's files unchanged",
    "S166-PR-REJOIN": "the tape's host enters 300: the guest rejoins 300 from the world map (lands +1, the landed line, the arrival "
                      "guard's world clause), mirroring true, the host's marker 0xA5 on 300, and NO ARMED line since the landing",
}
T2_PAIR_ROWS = tuple(T2_PAIR_CHECKS)
#: [calibration] the A0 build (no `netsync.world.pairpull`): the guest waits on 6603 (`not_mirroring`) until the tape's 300 -- every row
#: after the autosave red, the wait MEASURED (pair_old_wait); LEVER_PREDICTED (`pairpull old` on A0b): exactly the same
T2_PAIR_OLD_PREDICTED = ("S166-PR-OUT", "S166-PR-POSE", "S166-PR-ARM", "S166-PR-SAVEMENU", "S166-PR-REJOIN")
T2_PAIR_LEVER_PREDICTED = {PAIR_LEVER: T2_PAIR_OLD_PREDICTED}
#: the stand-in's faults -> exactly the T2 rows each turns red (tests/test_coop_world_walk.py's stub-replay smoke). pairpull_early needs
#: a BUSY guest at the pairing (the smoke's `busy` knob: menu control off at the rise) -- a free-standing one writes before any start
T2_PAIR_FAULT_REDS = {"pairpull_early": ("S166-PR-SAVE",),
                      # the unarmed landing arms at 300's field load instead: REJOIN's "no re-arm since the landing" clause sees it
                      "pairpull_unarmed": ("S166-PR-ARM", "S166-PR-SAVEMENU", "S166-PR-REJOIN"),
                      "pairpull_lever_ignored": (),          # the lever's own effect: the calibration's (S166-PR-CAL) -- tests pin it
                      # the chord without s38's mirror term: the armed press reaches R4 (refused +1) -- SAVEMENU's after-the-press
                      # clause red ALONE, with every press-state term green (the row's own calibration)
                      "chord_gate_open": ("S166-PR-SAVEMENU",)}


def t2_pair_catalog(calibrate: bool) -> dict:
    cat = {"T2-TAPE": wf.T2_COMMON["T2-TAPE"] + f"; at --from {PAIR_FROM_S:g} s the host stands on 9011 on foot past the debounce "
                                                "(pair_from_facts)",
           "T2-PEER": wf.T2_COMMON["T2-PEER"] + f"; the replay started at tape {PAIR_FROM_S:g} s"}
    cat.update(T2_PAIR_CHECKS)
    if calibrate:
        cat["S166-PR-CAL"] = ("CALIBRATION: by the GUEST's stage -- the A0 build (no netsync.world.pairpull) exactly T2_PAIR_OLD_PREDICTED "
                              "red, on A0b under `pairpull old` exactly the same -- AND the OLD wait MEASURED: on FieldHUD 6603, "
                              "why 'not_mirroring', no follow-out, until the tape's 300")
    cat["T2-SAVE"] = wf.T2_COMMON["T2-SAVE"]
    cat["T2-INI"] = wf.T2_COMMON["T2-INI"]
    return cat


# ------------------------------------------------------------------------------------------------ A0b's pure readers / judges
_ENGINE_HEAD = re.compile(r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2} \|\w\| ")
_RX_ARMED_FIELD = re.compile(BW.MIRROR_ARMED_FIELD_RE)
_RX_ARMED_WORLD = re.compile(BW.MIRROR_ARMED_WORLD_RE)
_RX_WRITTEN = re.compile(BW.PAIRING_WRITTEN_RE)
_RX_NO_PAIRING = re.compile(BW.NO_PAIRING_RE)


def _msg(line) -> str:
    """An engine line's message (the `dd.MM.yyyy HH:mm:ss |L| ` head stripped; a bare message passes through)."""
    return _ENGINE_HEAD.sub("", str(line).rstrip("\r\n"))


def _p(x, key, default=None):
    """A ``netsync.world.pairpull`` leaf (absent = ``default``: an engine before A0b)."""
    return cb.path(x, PAIR_PROBE + "." + key, default)


def pdelta(a, b, key="arms"):
    """b's ``netsync.world.pairpull.<key>`` - a's; None when either is unread (never a zero)."""
    va, vb = _num(_p(a, key)), _num(_p(b, key))
    return None if va is None or vb is None else vb - va


def pair_stage(x) -> str:
    """'a0b' with `netsync.world.pairpull`; 'a0' with A0's `kitcell` alone (A0b's OLD); else 's165' (or older): both OLD here."""
    return "a0b" if cb.has(x, PAIR_PROBE) else ("a0" if cb.has(x, PROBE) else "s165")


def armed_lines(lines) -> dict:
    """(PURE) The ARMED lines in ``lines``, in log order, by form: {"field": [index], "world": [(index, world map)]}."""
    out = {"field": [], "world": []}
    for i, ln in enumerate(lines):
        m = _msg(ln)
        if _RX_ARMED_FIELD.match(m):
            out["field"].append(i)
        else:
            w = _RX_ARMED_WORLD.match(m)
            if w:
                out["world"].append((i, int(w.group(1))))
    return out


def pairing_lines(lines) -> dict:
    """(PURE) The pairing window's lines in ``lines`` (log order): the writes [(index, kind, place, site)], the no-autosave lines
    [(index, field, world, note)], the follow-out's start lines [index]."""
    out = {"written": [], "none": [], "start": []}
    for i, ln in enumerate(lines):
        m = _msg(ln)
        w = _RX_WRITTEN.match(m)
        if w:
            out["written"].append((i, w.group(1), int(w.group(2)), w.group(3)))
            continue
        n = _RX_NO_PAIRING.match(m)
        if n:
            out["none"].append((i, n.group(1), n.group(2), n.group(3)))
            continue
        if BW.LOG_WORLD_OUT_START in m:
            out["start"].append(i)
    return out


def pair_from_facts(rows, t: float, *, tile=None, room: float = PAIR_ROOM_S) -> dict:
    """(PURE over coop_peer.tape_poses' rows) THE --from FACTS at tape second ``t``: {ok, why, first, live_s, room_s, enter_t}. The
    first host state frame at or after ``t`` is b6 with a whole pose on [102] WK_WORLD_IDX, on foot ([190] 0, [181] 0), within
    WK_POSE_TOL (torus) of ``tile`` (default the tape's WK_TILE); the host has been LIVE on the world map at least PAIR_LIVE_S before
    ``t`` (the b6 run's frames whose heartbeat moved, from the first move after the last freeze of PAIR_HB_FRESH_S or more) and its
    heartbeat moved within PAIR_HB_FRESH_S of ``t``; the same stand lasts at least ``room`` seconds after ``t``; a real field follows it."""
    tile = tuple(tile or pb.WK_TILE)
    after = [r for r in rows if r["t"] >= float(t)]
    out = {"ok": False, "why": "", "first": None, "live_s": None, "room_s": None, "enter_t": None}
    if not after:
        out["why"] = f"no host state frame at or after tape {t:g} s"
        return out
    f0 = after[0]
    out["first"] = round(f0["t"], 3)
    p = f0.get("pose")
    if not f0.get("b6") or p is None:
        out["why"] = f"the frame at tape {f0['t']:.2f} s is not on the world map (b6 {f0.get('b6')}, pose {'yes' if p else 'none'})"
        return out
    if p["idx"] != pb.WK_WORLD_IDX or p["mode"] != 0 or p["choco"] != 0:
        out["why"] = f"at tape {f0['t']:.2f} s: [102] {p['idx']}, [190] {p['mode']}, [181] {p['choco']} (want 11, 0, 0: on foot on 9011)"
        return out
    d = BW.world_torus_distance((p["x"], p["z"]), tile)
    if d > pb.WK_POSE_TOL:
        out["why"] = f"at tape {f0['t']:.2f} s the host stands {d:.1f} u from {tile} (want <= {pb.WK_POSE_TOL:g})"
        return out
    # THE LIVE RUN before it (THE LIVE DEBOUNCE's own clock): the heartbeat's moves on the b6 frames, back from the last one while each
    # follows the one before within PAIR_HB_FRESH_S -- the host's synchronous all-block load (a frozen heartbeat) ends the run
    b6 = sorted((r for r in rows if r.get("b6") and r["t"] <= f0["t"]), key=lambda r: r["t"])
    moves = [b["t"] for a, b in zip(b6, b6[1:]) if a["hb"] != b["hb"]]
    if not moves or f0["t"] - moves[-1] > PAIR_HB_FRESH_S:
        out["live_s"] = 0.0
        out["why"] = f"the host's heartbeat is frozen at tape {f0['t']:.2f} s (last moved {moves[-1] if moves else None})"
        return out
    live_from = moves[-1]
    for m in reversed(moves[:-1]):
        if live_from - m > PAIR_HB_FRESH_S:
            break
        live_from = m
    out["live_s"] = round(f0["t"] - live_from, 2)
    if out["live_s"] < PAIR_LIVE_S:
        out["why"] = f"the host has been live on the world map {out['live_s']:.2f} s before tape {f0['t']:.2f} s (want >= {PAIR_LIVE_S:g})"
        return out
    stand = []
    for r in after:
        q = r.get("pose")
        if not (r.get("b6") and q is not None and BW.world_torus_distance((q["x"], q["z"]), tile) <= pb.WK_POSE_TOL):
            break
        stand.append(r)
    out["room_s"] = round(stand[-1]["t"] - f0["t"], 2) if stand else 0.0
    nxt = next((r for r in after[len(stand):] if r.get("field") and 0 < r["field"] < 65535), None)   # the stand's end, then a field
    out["enter_t"] = round(nxt["t"], 3) if nxt is not None else None
    if out["room_s"] < room:
        out["why"] = f"the tile stand lasts {out['room_s']:.1f} s after tape {t:g} s (want >= {room:g})"
        return out
    if out["enter_t"] is None:
        out["why"] = "no real field follows the tile stand (the tape's rejoin)"
        return out
    out["ok"] = True
    out["why"] = (f"at tape {f0['t']:.2f} s the host stands at {tile} on foot on 9011, live {out['live_s']:.1f} s (>= {PAIR_LIVE_S:g}), "
                  f"the stand lasting {out['room_s']:.1f} s more, a field at {out['enter_t']:.2f} s")
    return out


def judge_pair_instrument(samples, lines, *, lever_word=None, lever_read=None) -> tuple:
    """S166-PR-I (PURE over the samples and engine lines from the replay's start to the host-b6 read): every sample on FieldHUD 6603,
    none mirroring, the last one's host cache reading b6; no same-field kick ('paired on the host's field') and no ARMED line; on A0b
    (``lever_word``) `pairpull.lever` read back as it."""
    if not samples:
        return False, "not reached: no sample after the replay's start"
    off = sorted({(s.ui_state, s.field_id if s.on_field else s.world_id) for s in samples
                  if not (s.ui_state == "FieldHUD" and s.field_id == FARSHORE)})
    mir = sum(1 for s in samples if cb.path(s, "netsync.session.mirroring") is True)
    b6 = wf._h(samples[-1], "b6") is True
    kick = sum(1 for ln in lines if "paired on the host's field (" in ln)
    arm = armed_lines(lines)
    n_arm = len(arm["field"]) + len(arm["world"])
    lev_ok = lever_word is None or lever_read == lever_word
    ok = not off and not mir and b6 and not kick and not n_arm and lev_ok
    return ok, (f"{len(samples)} sample(s): " + (f"OFF 6603: {off[:3]}" if off else "all FieldHUD 6603")
                + f"; mirroring on {mir}; the host cache b6 {'read' if b6 else 'NOT read'}; the kick line {kick}x, ARMED {n_arm}x "
                f"(want 0 each)" + (f"; pairpull.lever {lever_read!r} (want {lever_word!r})" if lever_word is not None else ""))


def judge_pair_autosave(lines, *, field: int = FARSHORE) -> tuple:
    """S166-PR-SAVE (PURE over the engine lines since the replay's start, log order): one 'pairing autosave written on field <field>
    (the pairing window)' line, BEFORE the follow-out's first start line (if any), and no 'no pairing autosave this session' line."""
    pl = pairing_lines(lines)
    mine = [w for w in pl["written"] if w[1] == "field" and w[2] == int(field)]
    first_start = pl["start"][0] if pl["start"] else None
    before = bool(mine) and (first_start is None or mine[0][0] < first_start)
    ok = len(mine) == 1 and before and not pl["none"]
    return ok, (f"written on field {field} {len(mine)}x (site {mine[0][3]!r})" if mine else f"NO write on field {field}") + (
        f"; {'before' if before else 'AFTER'} the follow-out's start line" if mine and first_start is not None else
        "; no follow-out start line" if mine else "") + (f"; the no-autosave line {len(pl['none'])}x: {pl['none'][0][3]!r}"
                                                          if pl["none"] else "; no no-autosave line")


def judge_pair_out(base, samples, lines, *, after_autosave=None) -> tuple:
    """S166-PR-OUT (PURE): coop_world_follow.judge_leave (WorldHUD 9011, starts / commits / lands +1, the three lines) and no sample
    (``after_autosave``: those published after the autosave line) reading out.why 'not_mirroring'."""
    ok, why = wf.judge_leave(base, samples, lines)
    later = after_autosave if after_autosave is not None else samples
    nm = sum(1 for s in later if wf._o(s, "why") == "not_mirroring")
    whys = sorted({str(wf._o(s, "why")) for s in later})[:6]
    return ok and not nm, f"{why}; out.why 'not_mirroring' on {nm} sample(s) after the autosave (want 0; seen {whys})"


def judge_pair_arm(base, world_samples, lines, *, world: int = WORLD) -> tuple:
    """S166-PR-ARM (PURE): mirroring true on every judged world sample from the landing's first on (wf.first_judged), pairpull.arms +1
    and last_world ``world`` since ``base``, the world-form ARMED line exactly once naming ``world``, no field-form ARMED line
    (``lines``: the engine's since the replay's start). The no-autosave line is S166-PR-SAVE's, never this row's."""
    st = wf.first_judged(world_samples)
    if st is None:
        return False, "not judged: no world sample with the blocks in and the world ticking (THE PRE-INIT SAMPLE)"
    later = world_samples[world_samples.index(st):]
    unmir = sum(1 for s in later if cb.path(s, "netsync.session.mirroring") is not True)
    da, lw = pdelta(base, later[-1]), _p(later[-1], "last_world")
    arm = armed_lines(lines)
    named = [w for _i, w in arm["world"]]
    ok = unmir == 0 and da == 1 and lw == world and named == [world] and not arm["field"]
    return ok, (f"mirroring false on {unmir} of {len(later)} judged world sample(s); pairpull.arms +{da} (want 1), last_world {lw!r} "
                f"(want {world}); ARMED at a world landing {named or 'NEVER'} (want [{world}]), field-form ARMED {len(arm['field'])}x "
                "(want 0)")


def judge_pair_savemenu(sg0: dict, sg1: dict, files0, files1, hud_back: bool, *, press: dict, opened: bool, froms: list,
                        world: int = WORLD) -> tuple:
    """S166-PR-SAVEMENU (PURE): the armed guest's Alt+F5 is refused AT THE CHORD by the mirror -- s38's spectator gate in
    UIKeyTrigger.OnSaveLoadSceneCommandDetected (`!IsMenuControlEnable || IsMirroringStory`, BW.save_chord_refused), ahead of the save
    menu -- so the menu never opens (``opened`` False: no 'Serialize' sample, nothing off the HUD to Cancel) and R4's Save sites are never
    reached: `refused` +0 AND `would_save` +0. The chord's buzz is counted nowhere, so the press is pinned three ways. ``press`` (read just
    before the verb): ui WorldHUD on ``world``, `menu_refusal.now` 'audible' (= menu control on and mirroring, NetSyncField.MenuKeyStep --
    not stock's own 'off'), `mirroring` True and the DRY lever 'old'. ``froms``: the agent's `savemenu` events since the press, exactly
    one, from 'WorldHUD' (the verb RAN: HarnessSaveMenu always reaches the chord). An UNARMED guest's chord opens the menu and its DRY pick
    counts would_save +1 (s165's R4-DRY); a chord without the mirror term reaches R4 (refused +1): both red. The sandbox unchanged, the
    HUD back. (Derived from the engine after A0b's NEW T2 pair read +0/+0: its refused +1 assumed the pick reaches SaveLoadUI.)"""
    if not sg1:
        return False, "absent: no `netsync.saveguard`"
    dr = (sg1.get("refused") or 0) - (sg0.get("refused") or 0)
    dw = (sg1.get("would_save") or 0) - (sg0.get("would_save") or 0)
    same = files0 is not None and files0 == files1
    at = (press.get("ui") == "WorldHUD" and press.get("world") == world and press.get("now") == "audible"
          and press.get("mirroring") is True and press.get("lever") == "old")
    ran = list(froms) == ["WorldHUD"]
    ok = at and ran and not opened and dr == 0 and dw == 0 and same and hud_back
    return ok, (f"at the press ui {press.get('ui')!r} world {press.get('world')} (want WorldHUD {world}), menu_refusal.now "
                f"{press.get('now')!r} (want 'audible': menu control on, the mirror refuses), mirroring {press.get('mirroring')!r}, lever "
                f"{press.get('lever')!r} (want 'old'); `savemenu` events {list(froms)} (want ['WorldHUD']); the save menu opened {opened} "
                f"(want False); refused +{dr} / would_save +{dw} (want +0 / +0: R4 never reached), last_why {sg1.get('last_why')!r}; the "
                "sandbox's files " + ("UNCHANGED" if same else ("UNREAD" if files0 is None else "CHANGED")) + f"; back on the HUD {hud_back}")


def judge_pair_rejoin(samples, base, lines, *, field: int = wf.ICE_CAVERN) -> tuple:
    """S166-PR-REJOIN (PURE): coop_world_wait.judge_rejoin_land and its arrival-guard clause, from the world map (``base`` on WorldHUD),
    mirroring true at the end, the host's marker (0xA5) on a FieldHUD ``field`` sample, and NO ARMED line in ``lines`` (since the
    landing: the mirror armed there; the field load stages the host's story without re-arming)."""
    if base is None or base.ui_state != "WorldHUD":
        return False, f"not reached: the guest never followed out (it stood on {getattr(base, 'ui_state', None)!r})"
    land = cw.judge_rejoin_land(samples, base, lines, field=field)
    arrive = cw.judge_arrive_world(samples, base, lines, field=field)
    on = [s for s in samples if s.ui_state == "FieldHUD" and s.field_id == field]
    marks = sorted({pb.marker_value(s) for s in on}, key=lambda v: -1 if v is None else v)
    mir = cb.path(samples[-1], "netsync.session.mirroring") if samples else None
    arm = armed_lines(lines)
    rearm = len(arm["field"]) + len(arm["world"])
    extra = (pb.MARKER_VALUE in marks and mir is True and not rearm,
             f"mirroring {mir!r} at the end; the marker on {field} read {[hex(m) if isinstance(m, int) else m for m in marks]} (want "
             f"0x{pb.MARKER_VALUE:02X}, the host's); ARMED lines since the landing {rearm} (want 0: armed once, at the landing)")
    (lk, lw), (ek, ew) = cw.with_arrive(land, arrive), extra
    return lk and ek, f"{lw}; {ew}"


def pair_old_wait(samples, lines) -> tuple:
    """THE OLD MEASUREMENT (PURE): the A0 build's (and `pairpull old`'s) wait -- every sample (from the host-b6 read to the tape's 300)
    on FieldHUD 6603, out.why 'not_mirroring' on at least one and nothing else blocking a start (no follow-out start line, starts +0)."""
    if not samples:
        return False, "no sample to measure"
    off = sorted({(s.ui_state, s.field_id if s.on_field else s.world_id) for s in samples
                  if not (s.ui_state == "FieldHUD" and s.field_id == FARSHORE)})
    nm = sum(1 for s in samples if wf._o(s, "why") == "not_mirroring")
    starts = pairing_lines(lines)["start"]
    ok = not off and nm >= 1 and not starts
    return ok, (f"{len(samples)} sample(s) " + (f"OFF 6603 {off[:3]}" if off else "all on FieldHUD 6603") + f"; why 'not_mirroring' on "
                f"{nm}; follow-out start lines {len(starts)}")


# ------------------------------------------------------------------------------------------------ A0b's T2 leg (COOP_WW_LEG=pair)
def _run_pair(g) -> None:
    """T2-A pair: the real guest on its own 6603, the COOP_TAPE_WORLD_WALK host replayed from PAIR_FROM_S (on 9011 already)."""
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, t2_pair_catalog(calibrate), finals=("T2-SAVE", "T2-INI", "S166-PR-CAL"), width=DETAIL_W)
    ctx = cw._T2()
    ctx.field = FARSHORE
    ctx.sent, ctx.poses, ctx.t0, ctx.lever = [], [], None, (PAIR_LEVER if calibrate else None)
    ctx.pstage, ctx.measured, ctx.from_facts = None, None, None
    try:
        _pair(g, led, ctx)
    except HarnessError as err:
        g.note(f"the pair leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        _pair_teardown(g, led, ctx)
        if calibrate:
            stage = ctx.pstage
            try:
                stage = stage or pair_stage(g.state)
            except HarnessError:
                pass
            pred = T2_PAIR_OLD_PREDICTED if stage != "a0b" else T2_PAIR_LEVER_PREDICTED[PAIR_LEVER]
            g.note(f"S166-PR-CAL: the guest reads as {stage}; predicted reds {sorted(pred)}; the OLD wait: {ctx.measured}")
            led.close("not reached: the leg ended before this check")
            failed = led.failed() - {"S166-PR-CAL"}
            missing, extra = sorted(set(pred) - failed), sorted(failed - set(pred))
            m_ok, m_why = ctx.measured if ctx.measured else (False, "never measured")
            led.check("S166-PR-CAL", not missing and not extra and m_ok,
                      f"predicted reds that stayed GREEN: {missing or 'none'}; unpredicted reds: {extra or 'none'}; the OLD wait "
                      f"{'MEASURED' if m_ok else 'NOT measured'}: {m_why}")
        led.close(final=True)


def _pair_teardown(g, led: cb.Ledger, ctx) -> None:
    if ctx.sent:
        ok, why = _ww(g, "clear")
        g.note(f"`worldwalk clear` (the levers this leg sent: {ctx.sent}): {'ok' if ok else why[:160]}")
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
    g.note(f"Memoria.log archived: {cb.archive_log(g, 'world-walk-pair')}")


def _pair(g, led: cb.Ledger, ctx) -> None:
    rows = list(T2_PAIR_ROWS)
    ctx.tape = pb.latest_world_walk_tape()
    if ctx.tape is None or not Path(ctx.tape).exists():
        led.check("T2-TAPE", False, f"no tape ({ctx.tape or pb.world_walk_tape_dir()}): record one -- COOP_TAPE_WORLD_WALK=1 "
                                    "coop_tape_record.py on a host (s164+; v14)")
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
    ctx.from_facts = pair_from_facts(ctx.poses, PAIR_FROM_S)
    facts_ok = all(ctx.facts[f"wk{i}"]["ok"] for i in range(1, 7)) and ctx.from_facts["ok"]
    bad = [f"wk{i}: {ctx.facts[f'wk{i}']['why']}" for i in range(1, 7) if not ctx.facts[f"wk{i}"]["ok"]]
    led.check("T2-TAPE", facts_ok, f"{Path(ctx.tape).name} ({len(records)} records{f', torn {torn} B' if torn else ''}): "
                                   + ("the six facts hold" if not bad else "CANNOT -- " + "; ".join(bad))
                                   + f"; --from {PAIR_FROM_S:g} s: {ctx.from_facts['why']}")
    if not facts_ok and not FORCE:
        led.close("not reached: this tape cannot carry the pair leg at that --from second")
        return
    if not wf._walk_preflight(g, led):
        return
    # the guest's own game on 6603 -- never paired there with the host (the host is on the world map from the tape's first frame)
    cb.provenance(g)
    g.note(f"s166 A0b T2 pair leg: the guest on its own {FARSHORE}, the world-walk host replayed from tape {PAIR_FROM_S:g} s (on 9011)")
    g.newgame()
    g.warp(FARSHORE)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.watch(*(pb.MARKER_BYTE * 8 + b for b in range(8)))
    g.wait_frames(45)                                     # the field entry's autosave: the exit ramp's own Continue
    ctx.stage = wf.stage_of(g.state)
    ctx.pstage = pair_stage(g.state)
    g.note(f"the guest engine reads as {ctx.pstage} (s{ctx.stage or '<117'})")
    ctx.eng = pb.EngineLog(g.engine_log())
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", wf.GUEST_VALUES, label="coop-world-walk-pair", run_dir=cw._run_dir(g))
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
    # the probe, then the calibration lever -- BEFORE the replay (the pairing happens at the replay's first frame); never on an engine
    # without `netsync.world.pairpull` (the A0 build answers the op with its usage line only after the step)
    st = g.state
    ctx.pstage = pair_stage(st)
    lever_note = f"{ctx.pstage}: no `{PAIR_PROBE}` -- nothing sent (the A0 build: the OLD calibration)"
    ctx.lever_word = None
    if ctx.pstage == "a0b":
        ctx.lever_word = "act"
        if ctx.lever == PAIR_LEVER:
            ok, why = _ww(g, PAIR_LEVER, "old")
            if ok:
                ctx.sent.append(PAIR_LEVER)
                ctx.lever_word = "old"
            lever_note = f"`worldwalk {PAIR_LEVER} old` {'sent' if ok else 'REFUSED: ' + why[:100]} (the CALIBRATION: held through the leg)"
        else:
            lever_note = f"a0b: `{PAIR_PROBE}` published -- the pull acts (no lever sent)"
        cb.poll(g, lambda s: _p(s, "lever") == ctx.lever_word, 3.0, "the pairpull lever read back")
    g.note(lever_note)
    ctx.base = g.state
    # the replay-host: the tape from PAIR_FROM_S, holding at its end
    rd = cw._run_dir(g)
    ctx.peer = pb.PeerProc("replay-host", [ctx.tape, "--port", str(wf.PORT), "--code", wf.CODE, "--from", f"{PAIR_FROM_S:g}",
                                           "--at-end", "hold"],
                           log_path=rd / "coop_peer-replay-world-walk-pair.log", out_path=rd / "coop_peer-replay-world-walk-pair.out")
    g.note(f"starting: {ctx.peer.command_text()}")
    ctx.log_at = cb.mark(g)                               # every engine line the rows judge is written after this mark (log order)
    ctx.peer.start()
    up = ctx.peer.wait_for(pb.PEER["listening"], 15.0, tick=lambda: cw._sample(g, ctx))
    conn = ctx.peer.wait_for(pb.PEER["guest_connected"], wf.DIAL_S, tick=lambda: cw._sample(g, ctx)) if up else None
    start = ctx.peer.wait_for(pb.PEER["replay_start"], 10.0, tick=lambda: cw._sample(g, ctx)) if conn else None
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "guest" and m.group(2) == wf.CODE)
    m = pb.PEER["replay_start"].search(start[1]) if start else None
    ctx.t0 = float(m.group(1)) if m else None
    at_from = ctx.t0 is not None and abs(ctx.t0 - PAIR_FROM_S) <= 0.5
    ok = up is not None and conn is not None and start is not None and bool(relay) and at_from
    led.check("T2-PEER", ok, f"config: {pb.show(cfg, 1)}; peer: {up[1] if up else 'never listened'} / "
                             f"{conn[1] if conn else 'no guest'} / {start[1] if start else 'no replay start'} (want tape "
                             f"{PAIR_FROM_S:g} s); engine: {pb.show(relay, 1)}; {lever_note}")
    if not ok:
        led.unreached(rows, "the instrument never started (T2-PEER)")
        return
    ctx.anchors["start"] = start[0]
    _pair_rows(g, led, ctx)


def _tape_wall(ctx, tape_s):
    """The wall moment the replay reaches tape second ``tape_s`` (its own anchor), None when unread."""
    if tape_s is None or ctx.t0 is None or "start" not in ctx.anchors:
        return None
    return ctx.anchors["start"] + _dt.timedelta(seconds=(float(tape_s) - float(ctx.t0)) / float(wf.REPLAY_SPEED))


def _pair_rows(g, led: cb.Ledger, ctx) -> None:
    """The rows, on the guest's own publishes and its engine lines since the replay started (``ctx.log_at``, a log MARK: order exact)."""
    start = ctx.anchors["start"]
    # I: until the guest's host cache reads the host's b6 (the host on the world map from the tape's first frame)
    cw._until(g, ctx, lambda s: wf._h(s, "b6") is True, PAIR_S)
    b6_mark = cb.mark(g)
    since = [(ts, s) for ts, s in ctx.samples if ts >= start]
    b6_at = next((i for i, (_ts, s) in enumerate(since) if wf._h(s, "b6") is True), None)
    upto = [s for _ts, s in (since[:b6_at + 1] if b6_at is not None else since)]
    lines_i = cb.log_lines(g)[ctx.log_at:b6_mark]
    led.check("S166-PR-I", *judge_pair_instrument(upto, lines_i, lever_word=ctx.lever_word, lever_read=_p(ctx.base, "lever")))
    if b6_at is None:
        led.unreached([c for c in T2_PAIR_ROWS if c != "S166-PR-I"], "the guest's host cache never read the host's b6")
        _pair_wait_tower(g, ctx)
        return
    t_b6 = since[b6_at][0]
    # SAVE + OUT: the autosave and the pull -- OLD (the A0 build, `pairpull old`): the wait, measured until the tape's 300
    pull_on = ctx.pstage == "a0b" and ctx.lever_word == "act"
    if pull_on:
        cw._until(g, ctx, lambda s: wf.first_judged([x for _t, x in ctx.samples if _t >= t_b6 and x.ui_state == "WorldHUD"])
                  is not None, PAIR_OUT_S)
    else:
        _pair_wait_tower(g, ctx)
    lines = cb.new(g, ctx.log_at)
    led.check("S166-PR-SAVE", *judge_pair_autosave(lines))
    due300 = _tape_wall(ctx, (ctx.facts.get("enter") or {}).get("t"))
    after = [(ts, s) for ts, s in ctx.samples if ts >= t_b6 and (pull_on or due300 is None or ts < due300)]
    samples = [s for _ts, s in after]
    w_idx = next((i for i, ln in enumerate(lines) if _RX_WRITTEN.match(_msg(ln))), None)
    t_written = _wall_of(lines[w_idx]) if w_idx is not None else None
    after_save = [s for ts, s in after if t_written is None or ts >= t_written + _dt.timedelta(seconds=1)]
    if cb.has(ctx.base, wf.PROBE):
        led.check("S166-PR-OUT", *judge_pair_out(ctx.base, samples, lines, after_autosave=after_save))
    else:
        led.check("S166-PR-OUT", False, f"absent: no `{wf.PROBE}` -- the guest stays on {FARSHORE}")
    if not pull_on:
        ctx.measured = pair_old_wait(samples, lines)
        g.note(f"THE OLD WAIT ({ctx.pstage}{', pairpull old' if ctx.lever_word == 'old' else ''}): {ctx.measured[1]}")
    world = [s for s in samples if s.ui_state == "WorldHUD"]
    landed = wf.first_judged(world)
    # POSE: the seam bracket on the tape clock (coop_world_follow's)
    l0 = _num(wf._o(ctx.base, "lands"))
    pre_l = [ts for ts, s in after if _num(wf._o(s, "lands")) == l0]
    post_l = [ts for ts, s in after if l0 is not None and (_num(wf._o(s, "lands")) or 0) > l0]
    bracket = None
    if pre_l and post_l and ctx.t0 is not None:
        bracket = (wf.tape_t(pre_l[-1], start, ctx.t0), wf.tape_t(post_l[0], start, ctx.t0))
    led.check("S166-PR-POSE", *wf.judge_tape_pose(landed, ctx.poses, bracket))
    if world:
        led.check("S166-PR-ARM", *judge_pair_arm(ctx.base, world, lines))
    else:
        led.check("S166-PR-ARM", False, f"not reached: the guest never followed out (it stood on {g.state.ui_state!r} "
                                        f"{g.state.field_id})")
    if g.state.ui_state != "WorldHUD":
        led.unreached(("S166-PR-SAVEMENU", "S166-PR-REJOIN"), f"the guest never reached the world map (ui {g.state.ui_state!r} "
                                                              f"field {g.state.field_id})")
        return
    # SAVEMENU: the DRY pick on the world map
    _pair_savemenu(g, lambda ok, why: led.check("S166-PR-SAVEMENU", ok, why))
    # REJOIN: the tape's host enters 300
    rbase, t_rj, r_at = g.state, _dt.datetime.now(), cb.mark(g)
    wait_s = wf.REJOIN_S + max(0.0, (due300 - _dt.datetime.now()).total_seconds() if due300 is not None else 60.0)
    cw._until(g, ctx, lambda s: s.ui_state == "FieldHUD" and s.field_id == wf.ICE_CAVERN, wait_s)
    cb.hold_for(g, 1.0)
    cw._sample(g, ctx)
    led.check("S166-PR-REJOIN", *judge_pair_rejoin(cw._after(ctx, t_rj), rbase, cb.new(g, r_at)))


def _pair_pick(g) -> tuple:
    """`savemenu` on the paired guest, then -- only if the save menu OPENS (a 'Serialize' sample within SAVEMENU_OPEN_S: an unarmed
    guest, the chord let through) -- coop_world_follow's Confirm pick until R4 answers, and Cancel back. On an ARMED guest the chord
    buzzes and nothing opens, so NO Confirm is pressed (on WorldHUD it would be the world script's button); a menu that opens LATE is
    still counted opened (the Cancel loop finds it), never closed quietly. (state at the press, state after, back on the HUD, opened,
    the `from` of every `savemenu` event since the press)."""
    hud = ("WorldHUD", "FieldHUD")
    st0 = g.state
    n0 = wf._sg_answers(st0.saveguard_block)
    ev0 = len(g.channel.events())
    g.savemenu()
    hit = cb.poll(g, lambda s: s.ui_state == "Serialize" or wf._sg_answers(s.saveguard_block) > n0, SAVEMENU_OPEN_S, "the save menu")
    opened = hit is not None and hit.ui_state == "Serialize"
    if opened:
        for _ in range(wf.PICK_PRESSES):
            st = g.state
            if wf._sg_answers(st.saveguard_block) > n0 or st.ui_state in hud:
                break                                        # answered, or the menu shut: never a Confirm on the HUD
            g.press("confirm")
            g.wait_frames(int(wf.PICK_S * 30))
    for _ in range(wf.CLOSE_PRESSES):
        if g.state.ui_state in hud:
            break
        opened = True                                        # off the HUD after the press: the menu opened (late or not)
        g.press("cancel")
        g.wait_frames(20)
    st1 = g.state
    froms = [e.get("from") for e in g.channel.events()[ev0:] if e.get("kind") == "savemenu"]
    return st0, st1, st1.ui_state in hud, opened, froms


def _pair_savemenu(g, record) -> None:
    """The DRY save pick on the world map (`worldfollow saveguard old`, _pair_pick, then `saveguard act`): ``record(ok, why)`` with
    judge_pair_savemenu's verdict -- never on an engine with no sandboxed save path (R4 never opens the owner's slots). The lever stays
    DRY so an unarmed guest's opened menu writes no slot."""
    files0 = wf.save_files(g.state)
    if files0 is None:
        record(False, "not reached: no SANDBOXED save path published (R4 never opens a save on the owner's slots)")
        return
    try:
        ok, why = wf._wf(g, "saveguard", "old")
        if not ok:
            record(False, f"`worldfollow saveguard old` refused: {why[:160]}")
            return
        st0, st1, back, opened, froms = _pair_pick(g)
        press = {"ui": st0.ui_state, "world": st0.world_id, "now": cb.path(st0, "netsync.menu_refusal.now"),
                 "mirroring": cb.path(st0, "netsync.session.mirroring"), "lever": (st0.saveguard_block or {}).get("lever")}
        record(*judge_pair_savemenu(dict(st0.saveguard_block or {}), dict(st1.saveguard_block or {}), files0,
                                    wf.save_files(g.state), back, press=press, opened=opened, froms=froms))
    except HarnessError as err:
        record(False, f"`savemenu` raised: {str(err)[:240]}")
    finally:
        wf._wf(g, "saveguard", "act")


def _since_wall(lines, wall) -> list:
    """The raw engine lines stamped at or after ``wall`` (floored to the second, as the engine stamps), in log order."""
    lo = pb.floor_s(wall) if wall is not None else None
    out = []
    for ln in lines:
        t = _wall_of(ln)
        if lo is None or (t is not None and t >= lo):
            out.append(ln)
    return out


def _wall_of(line):
    got = pb.parse_engine_line(str(line))
    return got[0] if got else None


def _pair_wait_tower(g, ctx) -> None:
    """Sample on until the tape's 300 entry (plus two seconds): the OLD wait is measured up to it, and the session is whole when the leg
    ends (the guest's own field follow into 300 then comes after the measured window)."""
    due = _tape_wall(ctx, (ctx.facts.get("enter") or {}).get("t"))
    if due is None:
        return
    due = due + _dt.timedelta(seconds=2.0)
    cw._until(g, ctx, lambda s: _dt.datetime.now() >= due, max(1.0, (due - _dt.datetime.now()).total_seconds() + 1.0))


# ------------------------------------------------------------------------------------------------ A0b's duo leg (D-PAIR)
DUO_PAIR_CHECKS = {
    "S166-D-PAIR-I": "the instrument: the host on WorldHUD 9011 at ICE_TILE (its own walk out and teleport, past the debounce) BEFORE "
                     "the guest's role is applied; the guest on FieldHUD 6603, not mirroring, never kicked or armed until its host "
                     "cache reads the host's b6",
    "S166-D-PAIR-SAVE": "the guest's pairing autosave on field 6603 (the pairing window) before its follow-out's start; no no-autosave "
                        "line",
    "S166-D-PAIR-OUT": "the pull: the guest on WorldHUD 9011, starts / commits / lands +1, landed within POSE_TOL of the host's OWN "
                       "world x/z (after block_ready + ticks)",
    "S166-D-PAIR-ARM": "mirroring true from the landing on, pairpull.arms +1 / last_world 9011, the world-form ARMED line once, no "
                       "field-form one",
    "S166-D-PAIR-SAVEMENU": "Alt+F5 under the DRY lever refused at the chord by the mirror (no save menu, refused +0 / would_save +0, "
                            "menu_refusal.now 'audible' at the press), the sandbox unchanged",
    "S166-D-PAIR-REJOIN": "the host Confirms on the tile into 300: the guest rejoins 300 from the world map, mirroring, the host's "
                          "marker on 300, no re-arm",
}
DUO_PAIR_ORDER = tuple(DUO_PAIR_CHECKS)
DUO_PAIR_OLD_PREDICTED = ("S166-D-PAIR-OUT", "S166-D-PAIR-ARM", "S166-D-PAIR-SAVEMENU", "S166-D-PAIR-REJOIN")
DUO_PAIR_SETTLE_FRAMES = 60    # the host stands this long on the tile before the guest's role is applied (past THE LIVE DEBOUNCE)


def run_duo(d) -> None:
    """D-PAIR (``py tools/harness/duo.py studies/test-harness/scenarios/coop_world_walk.py --no-pair``): a STAGGERED pairing through
    duo.py's own ops -- the host's role first (d.apply_role), its walk out onto 9011 and onto ICE_TILE, and only then the guest's role
    (d.apply_role on its own 6603): the guest's link comes up while its host already stands on the world map. Keyed by the GUEST's
    stage; COOP_CALIBRATE=1 judges S166-D-PAIR-CAL (the A0 build: exactly DUO_PAIR_OLD_PREDICTED red)."""
    calibrate = cb.CALIBRATE
    strict, d.strict = d.strict, False
    failed, done = [], set()

    def check(cid, ok, detail):
        if cid in done:
            return
        done.add(cid)
        if not ok:
            failed.append(cid)
        d.check(bool(ok), f"{cid}: {DUO_PAIR_CHECKS.get(cid, cid)}", str(detail)[:DETAIL_W], cid=cid)

    def rest(why):
        for cid in DUO_PAIR_ORDER:
            if cid not in done:
                check(cid, False, f"not reached: {why}"[:DETAIL_W])

    try:
        if getattr(d, "paired", False):
            rest("D-PAIR needs `duo.py ... --no-pair`: the duo paired both games on one field first, so the guest's link was already up "
                 "before its host stood on the world map")
        else:
            _duo_pair(d, check, rest)
    except HarnessError as err:
        d.note(f"the duo raised: {str(err)[:400]}")
        rest(f"the duo raised ({str(err)[:200]})")
    finally:
        rest("the duo ended before this row")
        if calibrate:
            try:
                stage = pair_stage(d.guest.state)
            except HarnessError:
                stage = "?"
            pred = set(DUO_PAIR_OLD_PREDICTED) if stage != "a0b" else set()
            missing, extra = sorted(pred - set(failed)), sorted(set(failed) - pred)
            d.check(not missing and not extra, "S166-D-PAIR-CAL: CALIBRATION -- exactly the predicted rows red for the GUEST's stage",
                    f"guest {stage}: predicted reds that stayed GREEN {missing or 'none'}; unpredicted reds {extra or 'none'}",
                    cid="S166-D-PAIR-CAL")
        d.strict = strict


def _duo_pair(d, check, rest) -> None:
    host, guest = d.host, d.guest
    for r, g_ in (("host", host), ("guest", guest)):
        g_.newgame()
        g_.warp(FARSHORE)
        try:
            g_.no_encounters(True)
        except HarnessError as err:
            g_.note(f"noencounter refused ({str(err)[:120]})")
        if r == "host":
            g_.poke(pb.MARKER_BYTE, pb.MARKER_VALUE)
        else:
            g_.watch(*(pb.MARKER_BYTE * 8 + b for b in range(8)))
            g_.wait_frames(45)                            # the guest's own field-entry autosave (its exit ramp's Continue)
    d.apply_role("host", cid="S166-D-PAIR-C2-host")
    okw, whyw, _hs = cw.walk_out(host)
    if not okw:
        rest(f"the host's walk out failed ({whyw[:160]})")
        return
    cw.teleport_settle(host, cw.ICE_TILE)
    host.wait_frames(DUO_PAIR_SETTLE_FRAMES)
    hp = wf.world_xz(host.state)
    hs = host.state
    gs0 = guest.state
    stage = pair_stage(gs0)
    d.note(f"D-PAIR: the guest reads as {stage}; the host stands on {hs.ui_state} {hs.world_id} at {hp}")
    h_ok = hs.ui_state == "WorldHUD" and hs.world_id == WORLD and hp[0] is not None and wf.torus(hp, cw.ICE_TILE) <= wf.POSE_TOL
    # the guest's link comes up NOW (its own 6603, before any partner frame): its base, then its role
    base, g_at = guest.state, cb.mark(guest)
    d.apply_role("guest", cid="S166-D-PAIR-C2-guest")
    taps = []
    take = cw._sampler(guest, taps)
    cb.poll(guest, lambda s: (take() or True) and wf._h(s, "b6") is True, PAIR_S, "the guest's host cache reading b6")
    upto = list(taps)
    glines = cb.new(guest, g_at)
    i_ok, i_why = judge_pair_instrument(upto, glines, lever_word="act" if stage == "a0b" else None,
                                        lever_read=_p(base, "lever"))
    check("S166-D-PAIR-I", h_ok and i_ok, f"host on {hs.ui_state} {hs.world_id} at {hp} (want WorldHUD {WORLD} at {cw.ICE_TILE}); "
                                          f"{i_why}")
    if not (h_ok and i_ok):
        rest("the instrument is untrustworthy on this run (D-PAIR-I)")
        return
    deadline = time.time() + PAIR_OUT_S
    while time.time() < deadline:
        take()
        if wf.first_judged([s for s in taps if s.ui_state == "WorldHUD"]) is not None:
            break
        time.sleep(0.1)
    lines = cb.new(guest, g_at)
    check("S166-D-PAIR-SAVE", *judge_pair_autosave(lines))
    world = [s for s in taps if s.ui_state == "WorldHUD"]
    st = wf.first_judged(world)
    if st is None:
        p_ok, p_why = False, "not judged: the guest never stood on a judged world sample"
    else:
        x, z = wf.world_xz(st)
        dd = wf.torus((x, z), hp) if x is not None else None
        p_ok, p_why = dd is not None and dd <= wf.POSE_TOL, f"landed at ({x}, {z}), {dd if dd is None else round(dd, 1)}u from the host's own {hp}"
    l_ok, l_why = wf.judge_leave(base, taps, lines) if cb.has(base, wf.PROBE) else (False, f"absent: no `{wf.PROBE}`")
    check("S166-D-PAIR-OUT", l_ok and p_ok, f"{l_why}; {p_why}")
    check("S166-D-PAIR-ARM", *judge_pair_arm(base, world, lines))
    if guest.state.ui_state != "WorldHUD":
        rest(f"the guest never reached the world map (ui {guest.state.ui_state!r}, field {guest.state.field_id})")
        return
    _pair_savemenu(guest, lambda ok, why: check("S166-D-PAIR-SAVEMENU", ok, why))
    # REJOIN: the host Confirms on the tile into 300
    rbase, r_at = guest.state, cb.mark(guest)
    early = []
    take2 = cw._sampler(guest, early)
    try:
        host.wait_frames(cw.PROMPT_FRAMES)
        host.press("confirm")
        take2()
        hin = cb.poll(host, lambda s: (take2() or True) and s.ui_state == "FieldHUD" and s.field_id == wf.ICE_CAVERN, cw.FIELD_S,
                      "the host on 300")
    except HarnessError as err:
        hin = None
        d.note(f"the host's entry raised: {str(err)[:200]}")
    if hin is None:
        check("S166-D-PAIR-REJOIN", False, f"not reached: the host never entered 300 (ui {host.state.ui_state!r})")
        return
    samples, _hit = cb.watch(guest, lambda s: s.ui_state == "FieldHUD" and s.field_id == wf.ICE_CAVERN, wf.REJOIN_S)
    samples += cb.hold_for(guest, 1.0)
    seen = {s.frame for s in samples}
    allg = [s for s in early if s.frame not in seen] + samples
    check("S166-D-PAIR-REJOIN", *judge_pair_rejoin(allg, rbase, cb.new(guest, r_at)))
