"""R3 STAGE 12 -- THE GUEST'S FLEE PRESENTATION (memoria-patch s115, part a), THE HOST'S "DROPPED N GIL" RELAYED (s116,
part c) AND THE GUEST'S DEFEAT PRESENTATION (s117, part b), the solo bench, run unattended.

THE GAP (studies/battle-coop/R3-DESIGN.md 3.2, 6.5, 6.6, 6.13). Through s114 the guest's diorama HELD the host's escape
and defeat -- the HUD hidden, the party frozen mid-fight until the exit pulled it out -- although every s103+ host already
ships both outcomes (kind 5 / kind 4, with the raw phase) on the 0xB5 end block.
  s115 (12a): a host still in PHASE_MENU_OFF (its run-away) is shown as the STOCK run-away -- cmd_status bit 0 +
    SetDefaultIdle (MP_ESCAPE, mot 17) on every living escapable player, MENU_OFF + SEQ_MENU_OFF_ESCAPE; the stock
    escape tail then runs (z falls, the escape fade, disappear 5, ESCAPE, PHASE_CLOSE) and R9b skips its STATE half (a
    mod's OnFlee, the gil penalty, "Dropped N Gil"); a CLOSE+ESCAPE (var 33 / a late join) is the CLOSE fade; W2 is
    kind-aware; THE NO-LEAK RULE reverts a local DEFEAT/GAMEOVER (or anything, once the host's kind is Defeat) when
    nothing is stamped; ArmVerdict ignores AfterEvent for an ESCAPE. Levers: `endbench guest hold|nor9b`.
  s116 (12c): the host's "Dropped N Gil" (Zidane's Flee) rides the end block as an additive fmt-2 record; the guest's
    run-away shows the HOST's figure through the stock follow message between its R9b and R8, its own gil untouched.
    Bench op: `endbench fleegil <n>|none`.
  s117 (12b): the host's MENU_OFF defeat (or PHASE_DEFEAT with the local party down, or any PHASE_DEFEAT not after the
    host's event phase -- the fix pass) is the STOCK annihilation ("Annihilated" before the menu hide, then the stock
    settle -- or, with a local player standing, the tail's own writes at once), var 34 (PHASE_DEFEAT after the host's
    event phase, the party standing) its own writes, any other phase the CLOSE fade; song 6 only in a Game-Over scene;
    W2's defeat rows; Game Over still sends the guest to ITS OWN field; a NoGameOver defeat is stamped and replayed.
    Bench ops: `endbench kill [mask]`, `endbench phase-defeat`. W1 now counts battle time (a pause is not counted).

THE BENCH. Field 30602, `netsync selftest 1` (saves sandboxed), the party seeded through COOPPARTY (30604); every leg
its own fresh `dioboot 67 0` (Runaway true, NoGameOver false) after `endbench clear` (a fabricated end stays armed
across a dioboot). `endbench <op>` fabricates the HOST's end block through the real codec and ParseView. Invariants:
the sandbox autosave's fingerprint (_coop_battle.fingerprint: gil, bag, levels/exp/AP, kill counters, cards) around
each part, and `netsync.battle.end.flee.gil_now` read WHILE booted (the teardown's Restore puts gil back, so only the
in-diorama read can catch a leak).

PARTS (COOP_S12_PART, any of "a", "c", "b"; unset = all three, in the build order a, c, b):
  a (s115, design 6.5)
    P0/P1  `netsync.battle.end.flee` published; `endbench guest hold` accepted.
    A      `escape` -> injected, action "flee", inject 5/3, the menu closed (A1); every living player mot 17 within
           500 ms of the injection (A2); each runner's z falls, then disappear 5 within 3 s (A3); phase 8, result 4,
           btl_flag & 64, flee.r9b 1 + its line, ability_flag false, gil_now unchanged (A4); R8 rising "(phase 8 seq
           1" (A5); a PNG shot MID-RUN, s12a-runaway (A6 -- READ it: backs turned, mid-run); `other 4` + `ui 1` +
           `state 7 loading` -> result-hide, a warm return reading 4, wipe_lifted, invariants identical (A7).
    B      escape with gil: `manifest 2` + `escape`, R8, `other 4`, `ui 1` + `state 2` -> the replay opens, verdict 0
           (B1); the gil page reads +321 (B2, PNG s12a-B-escape-gil); `state 5/6/7` -> it closes, and the field reads
           4 from the STAMP (B3). BAE: the same with `afterevent 1` still opens (ArmVerdict's ESCAPE row).
    C      `other 4` straight (CLOSE + ESCAPE) -> the CLOSE fade: action "close", inject 8/0, never mot 17, r9b 0, R8.
    NL     escape, the tail's local ESCAPE, then `defeat` + `ui 2` -> stamp -1, end_leave.reverted 4, field result 0.
    L1/L2  the in-DLL levers: `guest hold` -> HELD (the pre-s115 guest); `guest nor9b` (precondition flee.penalty > 0)
           -> ability_flag, bypassed 1, gil_now == boot gil - penalty WHILE booted, the gil back after the return.
    S1     SelfTest -> "..., replay N, flee M" (M > 0).            INV  part a's invariants, start to end.
  c (s116, design 6.13)
    P0/P1  `netsync.battle.end.flee.msg_gil` published; `endbench fleegil none` accepted.
    G      `fleegil 77` round-trips (peer.end.flee_gil 77, G1); `escape` -> after R9b msg_gil 77, the "shown with the
           HOST's figure" line before the first R8, follow_msg "dropped-gil" where the engine publishes it (G2); the
           guest's gil untouched while booted and after the return (G3); `fleegil none` -> -1 and a run-away shows
           nothing (G4).
    K1     SelfTest -> "..., fleegil K" (K > 0: a SHORT fmt-2 record skipped with the block kept, among its rows).
    INV    part c's diorama legs change nothing.
    H1     a REAL own battle (`battle 67`), Zidane's Flee: host.flee_gil == the gil the autosave lost, the host tap's
           line, host.end AND the loopback's peer.end carry the figure, trailer_skipped unchanged (an s116 guest PARSES
           the record). Runs AFTER part c's INV: a real flee really costs gil.
  b (s117, design 6.6 + the s117 README's re-baseline)
    P0/P1  `netsync.battle.end.follow_msg` published; `endbench kill` exists (on the field it answers "needs a booted
           battle diorama", not "unknown op").
    A      `kill 15`, every player at mot 4 (MP_DISABLE), then `defeat` -> "annihilate" 5/1, follow_msg "annihilated"
           (A1); MENU_OFF < 1.5 s, no watchdog, phase 7, result 3, btl_flag & 32 (song 6 in this Game-Over scene),
           R8 "(phase 7 seq 1" (A2); `ui 2` -> game-over, back on 30602, no Title, stamp -1, reverted 3, field 0,
           music_shut, invariants (members' HP included) identical (A3).
    B0     `defeat` with NO kill and no lever -> "annihilate" at 7/0 at once (the settle skipped: a standing party),
           follow_msg "annihilated", no W2 for 9 s.
    B      `guest settle` + `defeat`, no kill -> MENU_OFF > 8 s, W2 naming "player(s) not down" and the annihilate row
           (B1); forced phase 7 / result 3, never 6 / 1, R8 (B2).
    C      a NoGameOver scene (12, 336, 339 -- the booted scene's own flag judges): kill + defeat -> annihilate, phase
           7, btl_flag & 32 never set (C1); `phase-defeat` + `manifest 1` + `ui 1` -> the replay opens (C2); `state
           1..7` -> it closes, the field reads 3 (C3).
    D      `phase-defeat`, the party up, no event -> "annihilate" 7/0 (D0: the s117-1 fix -- var 34 needs the host's
           event phase); `event` first -> "defeat" 7/0, no message, never MENU_OFF (D1); `kill` + `phase-defeat` ->
           "annihilate" (D2).
    E1     the s117-2 song rule: `fieldsong 1` (the host's b4) + a Game-Over annihilation that played song 6 -> the
           end-leave still shuts the song, its line "over the host's b4".
    E2/E3  design 6.6 row E, CLOSE + DEFEAT straight (`other 3`: var 33 / a late join) -> the CLOSE fade (close, 8/0,
           local 3, no message): in scene 67 `ui 2` -> game-over, stamp -1, reverted 3, field 0 (E2); in a NoGameOver
           scene `ui 1` + `state 7` -> result-hide, stamp 3, reverted -1, field 3 (E3). The only bench of this row
           PRESENTED: coop_battle_end_guest's S6-C1/C2 run it under `guest hold` from s115 on.
    W      W1 counts battle time: a victory paused at SEQ_VICTORY_CAMERA_MOVE with `ui 1` sent -> no W1 for >= 5.5 s
           of pause (W1); after the resume seq 2 with no W1, or a W1 whose line says >= 5000 ms "paused, not counted" (W2).
    L1     `guest hold` + `defeat` -> HELD (the pre-s117 guest inside the s117 DLL).
    S1     SelfTest -> "..., defeat D" (D > 0).                   INV  part b's invariants, start to end.
  common   S0 (the forced selftest role), PRE (the invariant instrument), R (`reset` with `guest nor9b` pulled restores
           the lever: its line, and guest_mode "on" RE-READ WITH THE ROLE -- GuestMode answers "on" whenever the role is
           off, so only _coop_battle.reread_with_role can see a stranded lever).
NOT PROVEN HERE (two-machine, R3-DESIGN 7 sitting A boxes 11-17): the live lane's nonce gate on a real relay; the
host's bumper flee and the guest's run-away side by side; the real Game Over and title on the host; a guest paused as
the host flees (A14).

CALIBRATION (design 6.1; COOP_CALIBRATE=1 adds S12-CAL, which judges the run against the predicted red set of the
engine it FINDS -- see _predicted). The deployed DLL at writing is s110; s111-s114 publish none of these keys either.
  * s110-s114 (no `netsync.battle.end.flee`): EVERY check RED except S12-S0, S12-PRE and the three INVs (nothing a
    pre-stage guest does writes the save). Why each red: `endbench guest hold|nor9b` is refused -- by the engine
    ("netsync endbench guest: needs on|off|settle") or, first, by a driver that gates those values on
    `netsync.battle.end.flee` ("publishes no ...") -- (S12a-P1, L1, L2, S12-R); `escape` / `defeat` HELD -- nothing
    injected (a: A1-A6, B1-B3, BAE, C1, NL; b: B0, B1-B2, E2-E3), A7 returns 4 but wipe_lifted false (nothing injected to
    lift); `fleegil`, `kill`, `phase-defeat` -> "unknown op" or the driver's "publishes no ..." (c: P1, G1-G4; b: P1,
    A1-A3, C1-C3, D0-D2, E1 "not reached"); the keys are absent (P0s, c-H1 host.flee_gil); the SelfTest detail stops
    at "replay N" (a-S1, c-K1, b-S1); W1 counts wall time, so it FIRES during the 6 s pause (b-W1, b-W2).
  * Measured on the protocol stand-in (tools/harness/fakegame at its committed s110 rungs; a Python-path smoke, not an
    oracle): 1/54 green (S12-S0) in 263 s, every leg ran to its verdict, and S12-CAL named exactly the stand-in's own
    gap as unpredicted -- S12-PRE and the three INVs (the stand-in writes no autosave).
  * s115 (part c's predecessor): part a GREEN (bar the maybes below); part c RED except S12c-INV; part b RED except
    S12b-INV and S12b-L1 (s115's hold lever holds a defeat too -- every pre-s117 guest does); S12-R GREEN.
  * s116 (part b's predecessor): parts a and c GREEN; part b RED except S12b-INV and S12b-L1.
  * s117 (the new DLL): every check GREEN, except the MAYBE set below.
  * In-run, on the stage DLLs: a-L1 / a-L2 / b-B / b-L1 are the levers' reds inside the stage DLL (the house pattern),
    judged as their own checks.
  * MAYBE (environmental, excused by S12-CAL either way): S12a-L2 -- its precondition `flee.penalty > 0` needs the
    party's gil above zero (a New-Game party may hold none: then "not reached"); S12b-W1/W2 -- the stock pause opens
    only at btl_seq 0 (BattleHUD.OnKeyPause), so a victory camera that has already moved on leaves them "not reached";
    S12c-H1 -- Zidane's Flee must be on his menu (the New-Game Dagger teaches it) and the roll must succeed within 8
    turns.

    py tools/play.py studies/test-harness/scenarios/coop_battle_flee_defeat.py --field 30602
    COOP_S12_PART=a py tools/play.py studies/test-harness/scenarios/coop_battle_flee_defeat.py --field 30602
    COOP_CALIBRATE=1 COOP_S12_PART=b py tools/play.py studies/test-harness/scenarios/coop_battle_flee_defeat.py --field 30602
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError


def _parts(raw: str) -> tuple:
    """COOP_S12_PART -> the parts to run, in the build order a, c, b (unset or unknown letters = all three)."""
    want = {ch for ch in (raw or "").lower() if ch in "acb"}
    return tuple(p for p in ("a", "c", "b") if not want or p in want)


PARTS = _parts(os.environ.get("COOP_S12_PART", ""))

# ---- the capability keys (HarnessAgent's header: protocol 5, additive) and the patch each part needs
KEY_FLEE = cb.R3_PROBES[115]                             # s115: netsync.battle.end.flee
KEY_MSG_GIL = cb.R3_PROBES[116]                          # s116: netsync.battle.end.flee.msg_gil
KEY_FOLLOW = cb.R3_PROBES[117]                           # s117: netsync.battle.end.follow_msg
KEY_HOST_FLEE_GIL = "netsync.battle.host.flee_gil"       # s116 (the host tap's receipt)
PART_PATCH = {"a": 115, "c": 116, "b": 117}

# ---- engine values (FF9StateBattleSystem / FF9StateGlobal / battle.cs / BattlePlayerCharacter.PlayerMotionIndex)
PHASE_NORMAL, PHASE_MENU_OFF, PHASE_VICTORY, PHASE_DEFEAT, PHASE_CLOSE = 4, 5, 6, 7, 8
SEQ_FADEOUT, SEQ_MENU_OFF_DEFEAT, SEQ_MENU_OFF_ESCAPE = 0, 1, 3
SEQ_VICTORY_CAMERA_MOVE, SEQ_VICTORY_WAIT = 0, 2
RES_VICTORY, RES_DEFEAT, RES_ESCAPE, RES_GAMEOVER = 1, 3, 4, 6
BTL_SONG_FADEOUT, BTL_PLAY_END_SONG, BTL_END_LOAD = 16, 32, 64
MP_DISABLE, MP_ESCAPE = 4, 17
ALL_PLAYERS = 15                                         # `endbench kill` mask: a bit per player btl_id

SCENE = cb.SCENE                                         # 67: a Game-Over scene (NoGameOver false), Runaway true
NOGO_SCENES = (12, 336, 339)                             # NoGameOver scenes (coop_battle_end_guest.NOGO_SCENES)
ESC_GIL = 321                                            # `endbench manifest 2`'s escape gil (BenchManifest)
FLEE_GIL_MARK, FLEE_GIL_ALT = 77, 7713                   # the bench host's "Dropped N Gil" (design 6.13: 77)

# ---- the engine's words (each one C# literal of the s115-s117 stack)
INJ_FLEE = "diorama END: injected PHASE_MENU_OFF + SEQ_MENU_OFF_ESCAPE (the stock run-away"
R9B_LINE = "diorama R9b: the stock escape tail reached its STATE half"
R9B_BYPASS = "diorama R9b BYPASSED -- CALIBRATION (`endbench guest nor9b`)"
R8_LINE = "diorama R8: ManageBattleEnd refused (phase "
R8_DONE = "the guest's own end presentation is DONE"
HELD = " HELD -- the stock menu closed"
HELD_ESCAPE = "diorama END: the host's escape"
HELD_DEFEAT = "diorama END: the host's defeat"
HOLD_LEVER = "the `endbench guest hold` lever"
INJ_ANNIHILATE = 'diorama END: injected PHASE_MENU_OFF + SEQ_MENU_OFF_DEFEAT after the stock "Annihilated"'
INJ_ANNIHILATE_TAIL = 'diorama END: injected PHASE_DEFEAT + SEQ_DEFEATCLOSE_FADEOUT with result 3 after the stock "Annihilated"'
SETTLE_SKIPPED = "its per-unit settle skipped"
INJ_VAR34 = "diorama END: injected PHASE_DEFEAT + SEQ_DEFEATCLOSE_FADEOUT with result 3 (var 34's scripted end"
SONG_GO = "song 6 in this Game-Over scene"
SONG_NOGO = "song 6 NOT played: a NoGameOver scene"
W1_LINE = "diorama END watchdog W1: still PHASE_VICTORY + SEQ_VICTORY_CAMERA_MOVE"
W1_PAUSED_RX = re.compile(r"\((\d+) ms of it paused, not counted\)")
W2_LINE = "diorama END watchdog W2: still PHASE_MENU_OFF"
W2_ANNIHILATE_ROW = "[the annihilate row: phase 7 seq 0 result 3]"
NOT_DOWN = "player(s) not down"
SHOWN = "diorama flee: \"Dropped {n} Gil\" shown with the HOST's figure ("
SHOWN_ANY = "\" shown with the HOST's figure ("
HOST_FLEE = "battle flee (host): the stock escape tail dropped "
LEAVING = "diorama END: leaving a finished fight ("
OVER_B4 = "over the host's b4"
KILL_LINE = "harness: endbench kill -- the reconciler's KillUnit on "
NEEDS_BOOT = "needs a booted battle diorama"
SELFTEST_OK = "harness: battle end-block selftest OK ("
REL_GUEST = "end presentation guest back ON (released with the harness)"

FIGHT_S = 300.0


# ------------------------------------------------------------------------------------------- the catalog
def _catalog(parts, calibrate: bool) -> dict:
    c = {
        "S12-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S12-PRE": "the invariant instrument reads the sandbox autosave (gil, bag, levels/exp/AP, kill counters, cards)",
    }
    if "a" in parts:
        c.update({
            "S12a-P0": "the engine publishes `netsync.battle.end.flee` (memoria-patch s115)",
            "S12a-P1": "`netsync endbench guest hold` is accepted (the s115 lever exists)",
            "S12a-A1": "A: `endbench escape` -> injected, action 'flee', inject_phase 5, inject_seq 3, the menu closed "
                       "(turn.slot -1, hud.shown false), one 'injected PHASE_MENU_OFF + SEQ_MENU_OFF_ESCAPE (the stock "
                       "run-away' line",
            "S12a-A2": "A: every living player reads mot 17 (MP_ESCAPE) within 500 ms of the injection (inject_ms)",
            "S12a-A3": "A: each runner's z falls by more than 100, then every runner reads disappear 5 within 3000 ms of "
                       "the injection",
            "S12a-A4": "A: phase 8, result 4, btl_flag & 64; flee.r9b 1 with ONE R9b line, ability_flag false, gil_now "
                       "== the boot's gil on every booted publish",
            "S12a-A5": "A: R8 holds -- r8_hits rising, one 'diorama R8: ManageBattleEnd refused (phase 8 seq 1' DONE line",
            "S12a-A6": "A: a PNG shot MID-RUN (a runner at mot 17 with its z fallen, not yet vanished): s12a-runaway, not "
                       "blank -- READ it (backs turned, mid-run)",
            "S12a-A7": "A: `other 4` + `ui 1` + `state 7 loading` -> trigger 'result-hide', a warm return (returns +1), "
                       "field battle.result 4 (stamped 4), wipe_lifted; every invariant byte-identical across the leg",
            "S12a-B1": "B (escape with gil): `manifest 2` + `escape`, R8, `other 4`, `ui 1` + `state 2` -> the replay "
                       "opens: replay.opened, verdict 0",
            "S12a-B2": "B: the gil page (screen state 3 after `state 2 loading`) reads the host's +321 "
                       "(result_ui.labels.gil_receive) -- PNG s12a-B-escape-gil",
            "S12a-B3": "B: `state 5` / `6` / `7` -> replay.closed, trigger 'result-hide', the field reads 4 from the "
                       "STAMP (end_leave.stamp 4, stamped 4)",
            "S12a-BAE": "BAE: the same with `afterevent 1` still OPENS (verdict 0) -- an ESCAPE ignores AfterEvent "
                        "(review end F3)",
            "S12a-C1": "C: `other 4` straight (CLOSE + ESCAPE: var 33 / a late join) -> action 'close', inject 8/0, no "
                       "player ever at mot 17, flee.r9b 0, R8 rising",
            "S12a-NL": "NL: `escape`, the tail's local ESCAPE (battle.result 4), then `defeat` + `ui 2` -> trigger "
                       "'game-over', stamp -1, end_leave.reverted 4, field battle.result 0 (review end F4)",
            "S12a-L1": "L1 (`endbench guest hold` -- the pre-s115 guest): `escape` is HELD -- held, not injected, action "
                       "'hold', phase 4 for 1.5 s, guest_mode 'hold', the HELD line naming the lever",
            "S12a-L2": "L2 (`endbench guest nor9b`; precondition flee.penalty > 0): ability_flag true, bypassed 1, r9b 0, "
                       "the BYPASSED line, gil_now == the boot's gil - penalty WHILE booted; after the return the "
                       "autosave's gil equals the leg's start",
            "S12a-S1": "`endbench selftest` -> 'battle end-block selftest OK (... replay N, flee M' with M > 0",
            "S12a-INV": "part a's invariants byte-identical, its start to its end",
        })
    if "c" in parts:
        c.update({
            "S12c-P0": "the engine publishes `netsync.battle.end.flee.msg_gil` (memoria-patch s116)",
            "S12c-P1": "`netsync endbench fleegil none` is accepted on the field (the s116 op exists)",
            "S12c-G1": "G: `endbench fleegil <mark>` round-trips -- peer.end.flee_gil == mark (bench true), the "
                       "fabricated line names 'flee 0x01 <mark> gil'",
            "S12c-G2": "G: `escape` -> after R9b (flee.r9b 1) flee.msg_gil == mark, ONE '\"Dropped <mark> Gil\" shown "
                       "with the HOST's figure (at R9b' line BEFORE the first R8 line, follow_msg 'dropped-gil' where "
                       "the engine publishes follow_msg",
            "S12c-G3": "G: the guest's gil is untouched -- gil_now == the boot's gil on every booted publish, and the "
                       "leg's invariants byte-identical after the return",
            "S12c-G4": "G4: `fleegil none` -> peer.end.flee_gil -1; a run-away then shows nothing: msg_gil -1 for 3 s past "
                       "R9b, no 'shown with the HOST's figure' line",
            "S12c-K1": "`endbench selftest` -> 'battle end-block selftest OK (... fleegil K' with K > 0",
            "S12c-INV": "part c's diorama legs leave every invariant byte-identical (before H1's real battle)",
            "S12c-H1": "H (a REAL own battle, Zidane's Flee): host.flee_gil == the gil the autosave lost, ONE 'battle flee "
                       "(host): the stock escape tail dropped N gil' line, host.end.flee_gil and the loopback's "
                       "peer.end.flee_gil == N on a battle publish, peer.trailer_skipped unchanged",
        })
    if "b" in parts:
        c.update({
            "S12b-P0": "the engine publishes `netsync.battle.end.follow_msg` (memoria-patch s117)",
            "S12b-P1": "`netsync endbench kill` exists: on the field it answers 'needs a booted battle diorama' (never "
                       "'unknown op')",
            "S12b-A1": "A: `kill 15` (every player at mot 4) then `defeat` -> action 'annihilate', inject 5/1, follow_msg "
                       "'annihilated', one 'injected PHASE_MENU_OFF + SEQ_MENU_OFF_DEFEAT after the stock "
                       "\"Annihilated\"' line naming song 6 in this Game-Over scene",
            "S12b-A2": "A: MENU_OFF < 1.5 s with no watchdog, then phase 7, result 3, btl_flag & 32 (song 6); R8 rising "
                       "with one '(phase 7 seq 1' DONE line",
            "S12b-A3": "A: `ui 2` -> trigger 'game-over', back on the bench field, the Title never shown, stamp -1, "
                       "end_leave.reverted 3, field battle.result 0, music_shut; the invariants (members' HP included) "
                       "byte-identical across the leg",
            "S12b-B0": "B0: `defeat` with NO kill (a standing party) -> action 'annihilate', inject 7/0 at once, follow_msg "
                       "'annihilated', the 'its per-unit settle skipped' line, no watchdog for 9 s",
            "S12b-B1": "B (`endbench guest settle`): `defeat` with no kill -> inject 5/1, PHASE_MENU_OFF held > 8 s, then "
                       "W2: blocker names 'player(s) not down', the W2 line names the annihilate row (phase 7 seq 0 "
                       "result 3)",
            "S12b-B2": "B: after W2 phase 7 and result 3, never phase 6 nor result 1 on any publish; R8 rising",
            "S12b-C1": "C (a NoGameOver scene, its own scene_info.no_gameover true): kill + `defeat` -> 'annihilate', phase "
                       "7, btl_flag & 32 never set from the injection to R8, the line says song 6 NOT played",
            "S12b-C2": "C: `phase-defeat` + `manifest 1` + `ui 1` -> the replay opens (opened, verdict 0)",
            "S12b-C3": "C: `state 1..7` -> replay.closed, trigger 'result-hide', the field reads 3 (stamp 3)",
            "S12b-D0": "D0: `phase-defeat` with the party up and NO event (the s117-1 fix) -> 'annihilate' at 7/0, "
                       "follow_msg 'annihilated', the settle-skipped line",
            "S12b-D1": "D1: `event` (nothing presented) then `phase-defeat`, the party up -> 'defeat' (var 34) at 7/0, "
                       "follow_msg null, PHASE_MENU_OFF never seen, the var-34 line",
            "S12b-D2": "D2: `kill 15` + `phase-defeat` -> 'annihilate', follow_msg 'annihilated'",
            "S12b-E1": "E (the s117-2 song rule): `fieldsong 1` + a Game-Over annihilation that played song 6 (btl_flag & "
                       "16) + `ui 2` -> end_leave.music_shut true, the leaving line says 'over the host's b4'",
            "S12b-E2": "E2 (design 6.6 row E, scene 67 -- a Game-Over scene): `other 3` (CLOSE + DEFEAT: var 33 / a late "
                       "join) -> the CLOSE fade -- action 'close', inject 8/0, local battle.result 3, follow_msg null; then "
                       "`ui 2` -> trigger 'game-over', the Title never shown, stamp -1, end_leave.reverted 3, field "
                       "battle.result 0",
            "S12b-E3": "E3 (row E, a NoGameOver scene -- its own scene_info.no_gameover true): `other 3` -> 'close', inject "
                       "8/0, local result 3; then `ui 1` + `state 7` -> trigger 'result-hide', stamp 3, "
                       "end_leave.reverted -1, field battle.result 3",
            "S12b-W1": "W: a victory paused at SEQ_VICTORY_CAMERA_MOVE, `ui 1` sent -> w1_armed, and for >= 5.5 s of pause "
                       "no watchdog and (phase 6, seq 0) on every publish",
            "S12b-W2": "W: after the resume, seq 2 with no W1 -- or a W1 whose line says >= 5000 ms 'paused, not counted'",
            "S12b-L1": "L1 (`endbench guest hold` -- the pre-s117 guest): `defeat` is HELD -- held, not injected, action "
                       "'hold', phase 4, the HELD line naming the lever",
            "S12b-S1": "`endbench selftest` -> 'battle end-block selftest OK (... defeat D' with D > 0",
            "S12b-INV": "part b's invariants byte-identical, its start to its end",
        })
    c["S12-R"] = (f"`reset` with `endbench guest nor9b` left pulled: one '{REL_GUEST}' line, the forced role released; "
                  f"then RE-READ WITH THE ROLE (`netsync selftest 1`, which releases nothing -- GuestMode reads 'on' while "
                  f"the role is off): guest_mode 'on'")
    if calibrate:
        c["S12-CAL"] = "COOP_CALIBRATE: the reds are exactly the predicted set for the engine found (MAYBE excused)"
    return c


#: The environmental reds S12-CAL excuses (see the module note).
MAYBE = {"a": ("S12a-L2",), "c": ("S12c-H1",), "b": ("S12b-W1", "S12b-W2")}


def _stage(st) -> int:
    """The end lane's patch level, by its keys' PRESENCE (114 = none of s115-s117)."""
    if cb.has(st, KEY_FOLLOW):
        return 117
    if cb.has(st, KEY_MSG_GIL):
        return 116
    if cb.has(st, KEY_FLEE):
        return 115
    return 114


def _predicted(catalog: dict, parts, stage: int) -> tuple:
    """(predicted reds, maybe) for an engine at ``stage``: a part whose patch the engine lacks is RED except its INV
    (nothing a pre-stage guest does writes the save) -- and S12b-L1 on s115/s116 (their hold lever holds a defeat as
    every pre-s117 guest does); S12-R is red before s115 (no `guest nor9b`)."""
    reds, maybe = set(), set()
    for p in parts:
        maybe |= set(MAYBE[p])
        if stage >= PART_PATCH[p]:
            continue
        greens = {f"S12{p}-INV"}
        if p == "b" and stage >= 115:
            greens.add("S12b-L1")
        reds |= {cid for cid in catalog if cid.startswith(f"S12{p}-")} - greens
    if stage < 115:
        reds.add("S12-R")
    return reds, maybe


# ------------------------------------------------------------------------------------------- reads
def _end(x) -> dict:
    return cb.bend(x)


def _flee(x) -> dict:
    v = _end(x).get("flee")
    return v if isinstance(v, dict) else {}


def _el(x) -> dict:
    v = _end(x).get("end_leave")
    return v if isinstance(v, dict) else {}


def _rep(x) -> dict:
    r = _end(x).get("replay")
    return r if isinstance(r, dict) else {}


def _scr(x) -> dict:
    s = _rep(x).get("screen")
    return s if isinstance(s, dict) else {}


def _ru(x) -> dict:
    r = cb.battle(x).get("result_ui")
    return r if isinstance(r, dict) else {}


def _peer_end(x) -> dict:
    e = cb.peer(x).get("end")
    return e if isinstance(e, dict) else {}


def _host_end(x) -> dict:
    e = cb.host(x).get("end")
    return e if isinstance(e, dict) else {}


def _phase(x):
    return cb.battle(x).get("phase")


def _seq(x):
    return cb.battle(x).get("seq")


def _result(x):
    return cb.battle(x).get("result")


def _shown(x):
    return cb.hud(x).get("shown")


def _flag(x) -> int:
    f = _end(x).get("btl_flag")
    return f if isinstance(f, int) and not isinstance(f, bool) else 0


def _ms(x):
    v = _end(x).get("inject_ms")
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _num(v):
    """A published number as float, or None (bool, null, NaN or a string)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    return None if f != f else f


def _players(x) -> list:
    return cb.units(x, player=True)


def _living(x) -> list:
    """Slots of the players alive and above 0 HP (a bench party carries no escape-blocking status at its boot)."""
    return [int(u.get("slot", -1)) for u in _players(x) if u.get("alive") and (u.get("hp_raw") or 0) > 0]


def _by_slot(x) -> dict:
    return {int(u.get("slot", -1)): u for u in _players(x)}


def _all_down(x) -> bool:
    ps = _players(x)
    return bool(ps) and all(u.get("mot") == MP_DISABLE for u in ps)


def _mots(x) -> list:
    return [(u.get("slot"), u.get("mot"), u.get("alive")) for u in _players(x)]


def _eb(g, *args) -> tuple:
    return cb.try_ns(g, "endbench", *args)


def _r8_rising(g, seconds: float = 3.5, first_s: float = 12.0) -> tuple:
    """R8 holding: the first refusal lands, then r8_hits RISES over ``seconds`` (non-decreasing; the Byte
    btl_fade_time wraps, so never judged between two polls) -- coop_battle_end_guest's reading."""
    first = cb.poll(g, lambda x: isinstance(_end(x).get("r8_hits"), int) and _end(x)["r8_hits"] > 0, first_s,
                    "the first R8 refusal")
    samples = cb.hold_for(g, seconds)
    vals = [_end(x).get("r8_hits") for x in samples if isinstance(_end(x).get("r8_hits"), int)]
    ok = (first is not None and len(vals) >= 2 and vals[0] > 0 and vals[-1] > vals[0]
          and all(a <= b for a, b in zip(vals, vals[1:])))
    return ok, (f"r8_hits {vals[:1]}..{vals[-1:]} over {seconds:.1f}s ({len(vals)} publish(es))"
                + ("" if first is not None else f"; no R8 refusal within {first_s:.0f}s"))


def _r8_line(lines, phase: int) -> int:
    return len([ln for ln in lines if f"{R8_LINE}{phase} seq 1" in ln and R8_DONE in ln])


def _selftest_count(lines, section: str):
    """The OK line's ``<section> N`` count (None when absent or not OK)."""
    hit = next((ln for ln in lines if SELFTEST_OK in ln), "")
    m = re.search(rf"[ (,]{re.escape(section)} (\d+)[,)]", hit)
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------------------------------- legs' plumbing
class _Ctx:
    def __init__(self, field: int):
        self.field = field
        self.stage = 114


def _fresh(g, field: int, scene: int = SCENE) -> tuple:
    """`endbench clear`, a fresh `dioboot <scene> 0`, the steady command phase. (state or None, why)."""
    _eb(g, "clear")
    ok, why = cb.boot(g, scene)
    if not ok:
        cb.back_to_field(g, field)
        return None, why
    st = cb.wait_steady(g)
    if st is None:
        cb.leave(g, field)
        return None, "the diorama never reached its command phase"
    return st, ""


def _out(g, field: int) -> tuple:
    """Back on the field, playable (Leave if still booted, else wait for the end-leave's return), the bench cleared."""
    if cb.dio(g.state).get("booted"):
        ok, why = cb.leave(g, field)
    else:
        ok, why = cb.arrive(g, field)
    _eb(g, "clear")
    return ok, why


def _arrive_after_exit(g, field: int, timeout: float = 20.0) -> tuple:
    """The end-leave should take the guest out on its own; if not (an older engine), say so and leave by hand."""
    st = cb.poll(g, lambda s: not cb.dio(s).get("booted") and s.field_id == field and cb.free(s), timeout,
                 "the end-leave's return")
    if st is not None:
        cb.arrive(g, field)
        return True, ""
    cb.leave(g, field)
    return False, f"no end-leave within {timeout:.0f}s (left by hand)"


def _fp(g, field: int):
    fp, why = cb.fingerprint(g, field=field)
    if fp is None:
        g.note(f"invariants unreadable: {why}")
    return fp, why


def _fp_hp(g, field: int) -> tuple:
    """The invariants PLUS every member's current HP (`players[].cur.hp` of the sandbox autosave -- JsonParser writes
    it as a string): the defeat legs kill the seated party's BTL_DATA, which must never reach the save. (fp or None,
    why)."""
    tree, why = cb.extra_tree(g, field=field)
    if tree is None:
        return None, why
    fp = cb._fp_from_tree(tree)          # the same fingerprint cb.fingerprint decodes
    hp = []
    for p in (tree.get("40000_Common") or {}).get("players") or []:
        cur = p.get("cur") if isinstance(p, dict) else None
        v = cur.get("hp") if isinstance(cur, dict) else None
        try:
            hp.append(int(str(v)))
        except (TypeError, ValueError):
            hp.append(None)
    if not any(isinstance(h, int) for h in hp):
        return None, "no member HP readable in the autosave (players[].cur.hp)"
    fp["hp"] = hp
    return fp, ""


def _inv_check(led: cb.Ledger, cid: str, before, after, why_b: str = "", why_a: str = "") -> bool:
    if before is None or after is None:
        return led.check(cid, False, f"not reached: the invariant snapshot failed ({why_b or why_a})")
    diff = cb.fp_diff(before, after)
    return led.check(cid, not diff,
                     ("changed: " + "; ".join(f"{k}: {before.get(k)!r} -> {after.get(k)!r}" for k in diff))[:600]
                     if diff else f"identical (gil {before.get('gil')}, {len(before.get('items') or [])} bag rows, "
                                  f"{len(before.get('players') or [])} players)")


def _recover(g, field: int) -> None:
    """After a leg raised: resume a pause, put the lever back, never leave a diorama up."""
    try:
        if g.state.ui_state == "Pause":
            g.press("start", 4)
            g.wait_frames(20)
    except HarnessError:
        pass
    for args in (("guest", "on"), ("clear",)):
        try:
            _eb(g, *args)
        except HarnessError:
            pass
    try:
        cb.back_to_field(g, field)
    except HarnessError:
        pass


def _leg(g, led: cb.Ledger, ctx: _Ctx, cids, fn, *args) -> None:
    """Run one leg; a HarnessError (a refused wait, a dead verb) fails its pending checks "not reached" and recovers,
    so the next leg starts on the field. A dead game still ends the run (the recover raises again, uncaught)."""
    try:
        fn(g, led, ctx, *args)
    except HarnessError as err:
        led.unreached(cids, f"the leg raised: {str(err)[:300]}")
        _recover(g, ctx.field)


def _hold_lever_needles(lines, which: str) -> bool:
    return any(which in ln and HELD in ln and HOLD_LEVER in ln for ln in lines)


def _kill_all(g, timeout: float = 8.0) -> tuple:
    """`endbench kill 15` and every seated player down (mot 4, MP_DISABLE) -- design 6.6's review end F6: the
    annihilation's settle is judged only once the party HAS settled. (ok, why)."""
    ok, why = _eb(g, "kill", ALL_PLAYERS)
    if not ok:
        return False, f"`endbench kill {ALL_PLAYERS}` refused -- {why}"
    st = cb.poll(g, _all_down, timeout, "every seated player at MP_DISABLE")
    if st is None:
        return False, f"the party never settled down within {timeout:.0f}s: {_mots(g.state)}"
    return True, ""


def _injected(g, timeout: float = 3.0):
    return cb.poll(g, lambda x: _end(x).get("injected") is True, timeout, "the end injection")


def _replay_walk(g, steps, *, close_s: float = 10.0) -> tuple:
    """Step an OPEN replay by the bench host's state only: each (args, target) sends `endbench <args>` and waits for the
    screen state to reach ``target`` (for 3: off the Loading fade too); then `state 7` and the replay CLOSED through its
    own hide tail. (closed, trail)."""
    trail = []
    for args, target, timeout in steps:
        ok, why = _eb(g, *args)
        st = cb.poll(g, lambda s: isinstance(_scr(s).get("state"), int) and _scr(s)["state"] >= target
                     and not (target == 3 and _ru(s).get("loading")), timeout, f"the replay at state {target}")
        trail.append(f"{' '.join(args)}->{_scr(st or g.state).get('state')!r}{'' if ok else ' REFUSED ' + why[:60]}")
    _eb(g, "state", "7")
    st = cb.poll(g, lambda s: _rep(s).get("closed") is True or _el(s).get("trigger") == "result-hide", close_s,
                 "the replay to close")
    st2 = cb.poll(g, lambda s: _rep(s).get("closed") is True, 3.0, "replay.closed") if st is not None else None
    trail.append(f"state 7->closed={_rep(st2 or st or g.state).get('closed')!r}")
    return st2 is not None, trail


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    calibrate = cb.CALIBRATE
    catalog = _catalog(PARTS, calibrate)
    led = cb.Ledger(g, catalog, finals=("S12-R", "S12-CAL"))
    ctx = _Ctx(field)
    try:
        _run(g, led, ctx)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'flee-defeat')}")
        led.close()
        _release(g, led)
        if calibrate:
            reds, maybe = _predicted(catalog, PARTS, ctx.stage)
            g.note(f"S12-CAL: the engine reads as s{ctx.stage}; predicted reds {sorted(reds)}; maybe {sorted(maybe)}")
            led.judge_calibration("S12-CAL", reds, maybe)
        led.close(final=True)


def _run(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    ok, why = cb.setup(g, field, label=f"R3 stage 12: flee / gil relay / defeat (s115-s117), parts {''.join(PARTS)}")
    led.check("S12-S0", ok, why)
    ctx.stage = _stage(g.state)
    g.note(f"probe stage: {cb.stage_note(g.state)}; the end lane reads as s{ctx.stage} (follow_msg "
           f"{cb.has(g.state, KEY_FOLLOW)}, msg_gil "
           f"{cb.has(g.state, KEY_MSG_GIL)}, flee {cb.has(g.state, KEY_FLEE)})")
    fp, fwhy = _fp(g, field)
    led.check("S12-PRE", fp is not None, fwhy or f"gil {fp.get('gil')}, slot {fp.get('slot')}")
    okc, whyc = _eb(g, "clear")
    if not okc:
        led.close(f"`netsync endbench` does not exist on this engine -- {whyc}")
        return
    for p in PARTS:
        {"a": _part_a, "c": _part_c, "b": _part_b}[p](g, led, ctx)


def _release(g, led: cb.Ledger) -> None:
    """Leave `guest nor9b` pulled ON PURPOSE, then `reset`: the release must restore it and say so."""
    if "S12-R" in led.done:
        return
    try:
        ok, why = _eb(g, "guest", "nor9b")
        at = cb.mark(g)
        cb.release(g)
        st = g.state
        lines = cb.new(g, at)
        forced = (st.netsync or {}).get("forced")
        # GuestMode answers "on" whenever the role is off, and `reset` released the role: re-read it WITH the role
        # (re-forced, which releases nothing) -- the release line and this re-read are the real check (review R3H-3)
        rr, rwhy = cb.reread_with_role(g) if ok else (None, "")
        mode = _end(rr).get("guest_mode") if rr is not None else None
        led.check("S12-R", ok and cb.count(lines, REL_GUEST) == 1 and mode == "on" and forced is False,
                  why or (f"re-read WITH the role: guest_mode={mode!r}" if rr is not None else
                          f"no re-read with the role ({rwhy})")
                  + f"; forced after reset={forced!r}; {cb.grep(lines, 'released with the harness')}")
    except HarnessError as err:
        led.check("S12-R", False, f"the release raised: {str(err)[:300]}")


# =========================================================================================== PART A (s115)
def _part_a(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("PART A (s115): the guest's flee presentation")
    st = g.state
    led.check("S12a-P0", cb.has(st, KEY_FLEE), f"netsync.battle.end keys: {sorted(_end(st))}")
    ok, why = _eb(g, "guest", "hold")
    if ok:
        _eb(g, "guest", "on")
    led.check("S12a-P1", ok, why or "accepted (and put back on)")
    fp0, w0 = _fp(g, field)
    a_ids = [c for c in led.catalog if c.startswith("S12a-A")]
    _leg(g, led, ctx, a_ids, _a_runaway)
    _leg(g, led, ctx, ("S12a-B1", "S12a-B2", "S12a-B3"), _a_replay)
    _leg(g, led, ctx, ("S12a-BAE",), _a_afterevent)
    _leg(g, led, ctx, ("S12a-C1",), _a_close)
    _leg(g, led, ctx, ("S12a-NL",), _a_noleak)
    _leg(g, led, ctx, ("S12a-L1",), _a_hold)
    _leg(g, led, ctx, ("S12a-L2",), _a_nor9b)
    _selftest(g, led, "S12a-S1", "flee")
    fp1, w1 = _fp(g, field)
    _inv_check(led, "S12a-INV", fp0, fp1, w0, w1)


def _a_runaway(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12a-A: `escape` -- the stock run-away, R9b, the CLOSE fade, R8, then the exit")
    cids = [c for c in led.catalog if c.startswith("S12a-A")]
    before, bwhy = _fp(g, field)
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(cids, why)
        return
    gil0 = _flee(st).get("gil_now")
    r0 = cb.dio(st).get("returns")
    at = cb.mark(g)
    ok, why = _eb(g, "escape")
    inj = _injected(g)
    s = inj or g.state
    e, t = _end(s), cb.turn(s)
    runners = _living(s)
    z0 = {k: _num(u.get("z")) for k, u in _by_slot(s).items() if k in runners}
    lines = cb.wait_log(g, at, INJ_FLEE, 1.5)
    led.check("S12a-A1", ok and inj is not None and e.get("action") == "flee" and e.get("inject_phase") == PHASE_MENU_OFF
              and e.get("inject_seq") == SEQ_MENU_OFF_ESCAPE and t.get("slot") == -1 and _shown(s) is False
              and cb.count(lines, INJ_FLEE) == 1,
              why or f"end={cb.pick(e, 'injected', 'held', 'action', 'inject_phase', 'inject_seq', 'why')} "
                     f"turn.slot={t.get('slot')!r} hud.shown={_shown(s)!r} phase={_phase(s)!r}; {cb.grep(lines, 'diorama END')}")

    # A2/A3/A6: read every publish until a runner is mid-run (its z fallen > 200), photograph, then until all vanish
    def fell(x, k, by):
        z = _num(_by_slot(x).get(k, {}).get("z"))
        return z is not None and z0.get(k) is not None and z < z0[k] - by

    pre, mid = cb.watch(g, lambda x: any(fell(x, k, 200) and _by_slot(x).get(k, {}).get("mot") == MP_ESCAPE
                                         and _by_slot(x).get(k, {}).get("disappear") != 5 for k in runners), 2.5)
    shot, swhy = (cb.shot(g, "s12a-runaway") if mid is not None else (None, "never mid-run"))
    post, _ = cb.watch(g, lambda x: bool(runners) and all(_by_slot(x).get(k, {}).get("disappear") == 5 for k in runners)
                       and _phase(x) == PHASE_CLOSE, 4.0)
    samples = ([inj] if inj is not None else []) + pre + post
    first17 = next((x for x in samples if runners and all(_by_slot(x).get(k, {}).get("mot") == MP_ESCAPE
                                                           for k in runners)), None)
    ms17 = _ms(first17) if first17 is not None else None
    led.check("S12a-A2", inj is not None and bool(runners) and isinstance(ms17, int) and ms17 <= 500,
              f"runners {runners}; all at mot 17 first at inject_ms {ms17!r} (want <= 500); "
              f"mots at the injection {_mots(s)}")
    zmin = {k: min((z for z in (_num(_by_slot(x).get(k, {}).get("z")) for x in samples) if z is not None), default=None)
            for k in runners}
    gone = next((x for x in samples if runners and all(_by_slot(x).get(k, {}).get("disappear") == 5 for k in runners)),
                None)
    gone_ms = _ms(gone) if gone is not None else None
    falls = bool(runners) and all(zmin.get(k) is not None and z0.get(k) is not None and zmin[k] < z0[k] - 100
                                  for k in runners)
    led.check("S12a-A3", inj is not None and falls and isinstance(gone_ms, int) and gone_ms <= 3000,
              f"z at the injection {z0} -> lowest {zmin}; every runner at disappear 5 at inject_ms {gone_ms!r} "
              f"(want <= 3000)")
    led.check("S12a-A6", shot is not None and mid is not None and cb.png_not_blank(shot),
              f"{shot or swhy} -- READ it: backs turned, mid-run (shot at inject_ms {_ms(mid) if mid else None!r})")
    # A4
    sc = cb.poll(g, lambda x: _phase(x) == PHASE_CLOSE and _result(x) == RES_ESCAPE and _flag(x) & BTL_END_LOAD
                 and (_flee(x).get("r9b") or 0) >= 1, 4.0, "PHASE_CLOSE, ESCAPE, END_LOAD and R9b")
    s = sc or g.state
    fl = _flee(s)
    gils = sorted({_flee(x).get("gil_now") for x in samples + [s] if cb.dio(x).get("booted")}, key=repr)
    lines = cb.new(g, at)
    led.check("S12a-A4", sc is not None and fl.get("r9b") == 1 and cb.count(lines, R9B_LINE) == 1
              and fl.get("ability_flag") is False and isinstance(gil0, int) and gil0 >= 0 and gils == [gil0],
              f"phase={_phase(s)!r} result={_result(s)!r} btl_flag={_flag(s)!r} flee={fl} boot gil {gil0!r}, booted "
              f"gil_now {gils}; {cb.grep(lines, 'R9b')}")
    # A5
    rising, detail = _r8_rising(g)
    lines = cb.new(g, at)
    led.check("S12a-A5", rising and _r8_line(lines, PHASE_CLOSE) == 1,
              f"{detail}; {cb.grep(lines, 'diorama R8')}")
    # A7: the host's tail end (CLOSE + ESCAPE), its result screen, its Hide -> the guest follows it out
    oks = [_eb(g, *a) for a in (("other", "4"), ("ui", "1"), ("state", "7", "loading"))]
    back, bwhy2 = _arrive_after_exit(g, field)
    s = g.state
    el = _el(s)
    after, awhy = _fp(g, field)
    diff = cb.fp_diff(before, after) if before is not None and after is not None else ["unread"]
    led.check("S12a-A7", all(o for o, _ in oks) and back and el.get("trigger") == "result-hide"
              and cb.dio(s).get("last_return") == "warm" and isinstance(r0, int) and cb.dio(s).get("returns") == r0 + 1
              and _result(s) == RES_ESCAPE and el.get("stamped") == RES_ESCAPE and el.get("wipe_lifted") is True
              and not diff,
              "; ".join(w for _, w in oks if w) or bwhy2 or
              f"trigger={el.get('trigger')!r} last_return={cb.dio(s).get('last_return')!r} returns {r0!r}->"
              f"{cb.dio(s).get('returns')!r} field result={_result(s)!r} stamped={el.get('stamped')!r} "
              f"wipe_lifted={el.get('wipe_lifted')!r}; invariants changed {diff} ({bwhy or awhy})")
    _eb(g, "clear")


def _a_replay(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12a-B: escape with gil -- the write-nothing replay follows the host's ESCAPE result screen")
    cids = ("S12a-B1", "S12a-B2", "S12a-B3")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(cids, why)
        return
    oks = [_eb(g, "manifest", "2"), _eb(g, "escape")]
    inj = _injected(g)
    r8 = cb.poll(g, lambda x: (_end(x).get("r8_hits") or 0) > 0, 12.0, "the run-away's R8") if inj else None
    oks += [_eb(g, *a) for a in (("other", "4"), ("ui", "1"), ("state", "2"))]
    op = cb.poll(g, lambda x: _rep(x).get("opened") is True, 4.0, "the replay to open") if r8 is not None else None
    rp = _rep(op or g.state)
    refused = "; ".join(w for _, w in oks if w)
    led.check("S12a-B1", all(o for o, _ in oks) and inj is not None and r8 is not None and op is not None
              and rp.get("verdict") == 0,
              refused or f"injected={inj is not None} r8={r8 is not None} replay="
                         f"{cb.pick(rp, 'armed', 'opened', 'verdict', 'why')}")
    if op is None:
        led.unreached(("S12a-B2", "S12a-B3"), "the replay never opened")
        _eb(g, "state", "7")
        _arrive_after_exit(g, field)
        _eb(g, "clear")
        return
    cb.poll(g, lambda s: _scr(s).get("state") == 2, 30.0, "the tick pages' natural end (state 2)")
    _eb(g, "state", "2", "loading")
    s3 = cb.poll(g, lambda s: isinstance(_scr(s).get("state"), int) and _scr(s)["state"] >= 3 and not _ru(s).get("loading"),
                 10.0, "the gil page (state 3)")
    g.wait_frames(10)
    lab = _ru(g.state).get("labels") or {}
    p, pw = cb.shot(g, "s12a-B-escape-gil")
    led.check("S12a-B2", s3 is not None and cb.digits(lab.get("gil_receive")) == str(ESC_GIL)
              and p is not None and cb.png_not_blank(p),
              f"screen state={_scr(s3 or g.state).get('state')!r} labels={lab} (want gil_receive {ESC_GIL}); {p or pw}")
    closed, trail = _replay_walk(g, ((("state", "5"), 5, 8.0), (("state", "6"), 6, 8.0)))
    r_closed = _rep(g.state).get("closed")
    back, bwhy = _arrive_after_exit(g, field)
    s = g.state
    el = _el(s)
    led.check("S12a-B3", closed and back and el.get("trigger") == "result-hide" and el.get("stamp") == RES_ESCAPE
              and el.get("stamped") == RES_ESCAPE and _result(s) == RES_ESCAPE,
              bwhy or f"walk {trail}; closed={r_closed!r}; trigger={el.get('trigger')!r} stamp={el.get('stamp')!r} "
                      f"stamped={el.get('stamped')!r} field result={_result(s)!r}")
    _eb(g, "clear")


def _a_afterevent(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12a-BAE: escape with gil in an AfterEvent battle still opens (the host's Show never reads Event on ESCAPE)")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S12a-BAE",), why)
        return
    oks = [_eb(g, *a) for a in (("manifest", "2"), ("afterevent", "1"), ("escape",))]
    inj = _injected(g)
    r8 = cb.poll(g, lambda x: (_end(x).get("r8_hits") or 0) > 0, 12.0, "the run-away's R8") if inj else None
    oks += [_eb(g, *a) for a in (("other", "4"), ("ui", "1"))]
    op = cb.poll(g, lambda x: _rep(x).get("opened") is True, 4.0, "the replay to open") if r8 is not None else None
    rp = _rep(op or g.state)
    flags = _peer_end(op or g.state).get("flags")
    led.check("S12a-BAE", all(o for o, _ in oks) and op is not None and rp.get("verdict") == 0
              and isinstance(flags, int) and flags & 1,
              "; ".join(w for _, w in oks if w) or f"injected={inj is not None} r8={r8 is not None} replay="
                                                    f"{cb.pick(rp, 'armed', 'opened', 'verdict', 'why')} peer.end.flags="
                                                    f"{flags!r} (b0 = AfterEvent)")
    _out(g, field)


def _a_close(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12a-C: CLOSE + ESCAPE straight (var 33 / a late join) -- the CLOSE fade, no run-away")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S12a-C1",), why)
        return
    ok, why = _eb(g, "other", "4")
    inj = _injected(g)
    samples, _ = cb.watch(g, lambda x: (_end(x).get("r8_hits") or 0) > 0, 10.0)
    ran = [cb.frame_of(x) for x in samples if any(u.get("mot") == MP_ESCAPE for u in _players(x))]
    rising, detail = _r8_rising(g, first_s=4.0)
    e = _end(inj or g.state)
    led.check("S12a-C1", ok and inj is not None and e.get("action") == "close" and e.get("inject_phase") == PHASE_CLOSE
              and e.get("inject_seq") == SEQ_FADEOUT and not ran and _flee(g.state).get("r9b") == 0 and rising,
              why or f"end={cb.pick(e, 'injected', 'held', 'action', 'inject_phase', 'inject_seq')} mot 17 on frames "
                     f"{ran[:5]} r9b={_flee(g.state).get('r9b')!r}; {detail}")
    _out(g, field)


def _a_noleak(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12a-NL: a flee that ends in the host's annihilation -- the no-leak rule reverts the local ESCAPE")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S12a-NL",), why)
        return
    ok, why = _eb(g, "escape")
    inj = _injected(g)
    esc = cb.poll(g, lambda x: _result(x) == RES_ESCAPE, 5.0, "the escape tail's local ESCAPE") if inj else None
    ok2, why2 = _eb(g, "defeat")
    ok3, why3 = _eb(g, "ui", "2")
    back, bwhy = _arrive_after_exit(g, field)
    s = g.state
    el = _el(s)
    led.check("S12a-NL", ok and ok2 and ok3 and inj is not None and esc is not None and back
              and el.get("trigger") == "game-over" and el.get("stamp") == -1 and el.get("reverted") == RES_ESCAPE
              and _result(s) == 0,
              (why or why2 or why3) or bwhy or
              f"injected={inj is not None} local ESCAPE seen={esc is not None}; trigger={el.get('trigger')!r} "
              f"stamp={el.get('stamp')!r} reverted={el.get('reverted', 'ABSENT')!r} field result={_result(s)!r}")
    _eb(g, "clear")


def _a_hold(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12a-L1: the lever `endbench guest hold` -- the pre-s115 guest holds the escape")
    ok, why = _eb(g, "guest", "hold")
    if not ok:
        led.check("S12a-L1", False, f"not reached: `endbench guest hold` refused -- {why}")
        return
    try:
        st, swhy = _fresh(g, field)
        if st is None:
            led.unreached(("S12a-L1",), swhy)
            return
        at = cb.mark(g)
        ok2, why2 = _eb(g, "escape")
        held = cb.poll(g, lambda x: _end(x).get("held") is True, 2.0, "the escape to be HELD")
        samples = cb.hold_for(g, 1.5)
        bad = [cb.frame_of(x) for x in samples if not (_end(x).get("held") is True and _end(x).get("injected") is False
                                                       and _phase(x) == PHASE_NORMAL)]
        e = _end(g.state)
        lines = cb.new(g, at)
        led.check("S12a-L1", ok2 and held is not None and samples and not bad and e.get("action") == "hold"
                  and e.get("guest_mode") == "hold" and _hold_lever_needles(lines, HELD_ESCAPE),
                  why2 or f"end={cb.pick(e, 'held', 'injected', 'action', 'guest_mode')} off-hold frames {bad[:5]}; "
                          f"{cb.grep(lines, 'diorama END')}")
        _out(g, field)
    finally:
        _eb(g, "guest", "on")


def _a_nor9b(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12a-L2: the lever `endbench guest nor9b` -- R9b bypassed, the stock penalty runs WHILE booted")
    before, bwhy = _fp(g, field)
    ok, why = _eb(g, "guest", "nor9b")
    if not ok:
        led.check("S12a-L2", False, f"not reached: `endbench guest nor9b` refused -- {why}")
        return
    try:
        st, swhy = _fresh(g, field)
        if st is None:
            led.unreached(("S12a-L2",), swhy)
            return
        fl = _flee(st)
        pen, gil0 = fl.get("penalty"), fl.get("gil_now")
        if not (isinstance(pen, int) and pen > 0 and isinstance(gil0, int)):
            led.check("S12a-L2", False, f"not reached: precondition flee.penalty > 0 failed (penalty {pen!r}, the party's "
                                        f"gil {gil0!r} -- a party with no gil pays nothing)")
            _out(g, field)
            return
        at = cb.mark(g)
        ok2, why2 = _eb(g, "escape")
        paid = cb.poll(g, lambda x: (_flee(x).get("bypassed") or 0) >= 1 and _flee(x).get("gil_now") == gil0 - pen, 6.0,
                       "the bypassed tail's gil penalty")
        s = paid or g.state
        fl = _flee(s)
        lines = cb.new(g, at)
        live_ok = (paid is not None and fl.get("ability_flag") is True and fl.get("bypassed") == 1 and fl.get("r9b") == 0
                   and cb.count(lines, R9B_BYPASS) == 1)
        oks = [_eb(g, *a) for a in (("other", "4"), ("ui", "1"), ("state", "7"))]
        back, rwhy = _arrive_after_exit(g, field)
        after, awhy = _fp(g, field)
        led.check("S12a-L2", ok2 and live_ok and back and before is not None and after is not None
                  and after.get("gil") == before.get("gil"),
                  why2 or rwhy or f"flee={fl} (boot gil {gil0}, penalty {pen}); autosave gil {(before or {}).get('gil')!r} "
                                  f"-> {(after or {}).get('gil')!r} ({bwhy or awhy}); {cb.grep(lines, 'R9b')}"
                                  f"{'; ' + '; '.join(w for _, w in oks if w) if any(not o for o, _ in oks) else ''}")
        _eb(g, "clear")
    finally:
        _eb(g, "guest", "on")


# =========================================================================================== PART C (s116)
def _part_c(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("PART C (s116): the host's \"Dropped N Gil\" relayed to the guest's run-away")
    st = g.state
    led.check("S12c-P0", cb.has(st, KEY_MSG_GIL), f"netsync.battle.end.flee = {_flee(st) or 'ABSENT'}")
    ok, why = _eb(g, "fleegil", "none")
    led.check("S12c-P1", ok, why or "accepted")
    fp0, w0 = _fp(g, field)
    _leg(g, led, ctx, ("S12c-G1", "S12c-G2", "S12c-G3"), _c_relay)
    _leg(g, led, ctx, ("S12c-G4",), _c_none)
    _selftest(g, led, "S12c-K1", "fleegil")
    fp1, w1 = _fp(g, field)
    _inv_check(led, "S12c-INV", fp0, fp1, w0, w1)
    _leg(g, led, ctx, ("S12c-H1",), _c_host)


def _c_relay(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12c-G: the bench host's flee record, then the run-away shows ITS figure at R9b")
    cids = ("S12c-G1", "S12c-G2", "S12c-G3")
    before, bwhy = _fp(g, field)
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(cids, why)
        return
    fl = _flee(st)
    gil0 = fl.get("gil_now")
    # TWO-MARKER: the figure must be one no other source in the process says (the stock penalty, the party's gil)
    mark = FLEE_GIL_ALT if FLEE_GIL_MARK in (fl.get("penalty"), gil0) else FLEE_GIL_MARK
    at = cb.mark(g)
    ok, why = _eb(g, "fleegil", mark)
    pe = _peer_end(g.state)
    lines = cb.wait_log(g, at, f"flee 0x01 {mark} gil", 1.5)
    led.check("S12c-G1", ok and pe.get("flee_gil") == mark and pe.get("bench") is True
              and any("endbench fleegil -- fabricated" in ln and f"flee 0x01 {mark} gil" in ln for ln in lines),
              why or f"peer.end={cb.pick(pe, 'kind', 'flee_gil', 'bench')}; {cb.grep(lines, 'endbench fleegil')}")
    if not ok:
        led.unreached(("S12c-G2", "S12c-G3"), f"`endbench fleegil {mark}` refused -- {why}")
        _out(g, field)
        return
    at = cb.mark(g)
    ok2, why2 = _eb(g, "escape")
    samples, r9 = cb.watch(g, lambda x: (_flee(x).get("r9b") or 0) >= 1, 6.0)
    more, shown = cb.watch(g, lambda x: _flee(x).get("msg_gil") == mark, 2.5)
    samples += more
    s = shown or g.state
    lines = cb.wait_log(g, at, R8_LINE, 12.0)
    i_shown = next((i for i, ln in enumerate(lines) if SHOWN.format(n=mark) in ln and "at R9b: the record was in hand" in ln),
                   None)
    i_r8 = next((i for i, ln in enumerate(lines) if R8_LINE in ln), None)
    fm_ok = (_end(s).get("follow_msg") == "dropped-gil") if cb.has(s, KEY_FOLLOW) else True
    led.check("S12c-G2", ok2 and r9 is not None and shown is not None and cb.count(lines, SHOWN_ANY) == 1
              and i_shown is not None and (i_r8 is None or i_shown < i_r8) and fm_ok,
              why2 or f"r9b reached={r9 is not None} msg_gil={_flee(s).get('msg_gil')!r} (want {mark}) follow_msg="
                      f"{_end(s).get('follow_msg', 'ABSENT')!r}; shown line #{i_shown} first R8 #{i_r8}; "
                      f"{cb.grep(lines, 'diorama flee', 'R9b')}")
    oks = [_eb(g, *a) for a in (("other", "4"), ("ui", "1"), ("state", "7"))]
    gils = sorted({_flee(x).get("gil_now") for x in samples if cb.dio(x).get("booted")}, key=repr)
    back, rwhy = _arrive_after_exit(g, field)
    after, awhy = _fp(g, field)
    diff = cb.fp_diff(before, after) if before is not None and after is not None else ["unread"]
    led.check("S12c-G3", isinstance(gil0, int) and gils == [gil0] and back and not diff,
              rwhy or f"boot gil {gil0!r}; booted gil_now {gils}; invariants changed {diff} ({bwhy or awhy})"
                      f"{'; ' + '; '.join(w for _, w in oks if w) if any(not o for o, _ in oks) else ''}")
    _eb(g, "clear")


def _c_none(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12c-G4: `fleegil none` -- no record, nothing shown")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S12c-G4",), why)
        return
    oks = [_eb(g, "fleegil", FLEE_GIL_MARK), _eb(g, "fleegil", "none")]
    pe = _peer_end(g.state)
    at = cb.mark(g)
    oks.append(_eb(g, "escape"))
    r9 = cb.poll(g, lambda x: (_flee(x).get("r9b") or 0) >= 1, 6.0, "R9b")
    samples = cb.hold_for(g, 3.0)
    lines = cb.new(g, at)
    shown = [cb.frame_of(x) for x in samples if _flee(x).get("msg_gil") != -1 or _end(x).get("follow_msg") == "dropped-gil"]
    led.check("S12c-G4", all(o for o, _ in oks) and pe.get("flee_gil") == -1 and r9 is not None and samples and not shown
              and cb.count(lines, SHOWN_ANY) == 0,
              "; ".join(w for _, w in oks if w) or f"peer.end.flee_gil={pe.get('flee_gil', 'ABSENT')!r} r9b reached="
                                                    f"{r9 is not None}; shown on frames {shown[:5]}; "
                                                    f"{cb.grep(lines, 'diorama flee')}")
    _out(g, field)


def _c_host(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """A REAL own battle (selftest loopback, no guest slots): Zidane's Flee runs the stock default method's gil drop,
    and the host tap ships the figure. Run after part c's INV -- the gil is really lost."""
    field = ctx.field
    g.note("S12c-H: a real own battle -- Zidane's Flee drops gil and the host ships the figure")
    if not cb.has(g.state, KEY_HOST_FLEE_GIL):
        led.check("S12c-H1", False, f"not reached: no `{KEY_HOST_FLEE_GIL}` (an engine before s116 has no host tap)")
        return
    cb.try_ns(g, "guestslots", 0)
    _eb(g, "clear")
    fp0, w0 = _fp(g, field)
    tb0 = cb.peer(g.state).get("trailer_skipped")
    at = cb.mark(g)
    frame0 = cb.frame_of(g.state)
    try:
        g.start_battle(SCENE)
    except HarnessError as err:
        led.check("S12c-H1", False, f"not reached: `battle {SCENE}` did not start -- {str(err)[:200]}")
        return
    # Every prompt is answered (nobody may sit idle in Active ATB): Zidane's slot Flees, any other slot Defends, until
    # the escape is under way (SysEscape queued) or the battle is over. A Flee that fails its roll just comes round.
    fled, tried, idle = False, [], 0
    for _ in range(12):
        st = g.state
        if st.escaping or st.battle_result == RES_ESCAPE:
            fled = True
            break
        if not st.in_battle or idle >= 2:
            break
        try:
            slot = g.wait_turn(timeout=60.0)
            idle = 0
        except HarnessError as err:
            # the battle ended (or the escape is playing): judged at the top; two silent minutes in a row end the loop
            idle += 1
            tried.append(f"no turn ({str(err)[:80]})")
            continue
        try:
            g.act("Flee", slot=slot)
            tried.append(f"slot {slot}: Flee")
        except HarnessError as err:
            tried.append(f"slot {slot}: no Flee ({str(err)[:60]}) -> Defend")
            try:
                g.act("Defend", slot=slot)
            except HarnessError as err2:
                tried.append(f"Defend refused ({str(err2)[:60]})")
    fled = fled or g.state.escaping
    back = cb.poll(g, lambda s: s.on_field and not s.in_battle and cb.free(s),
                   60.0 if fled or not g.state.in_battle else 1.0, "the field after the flee")
    if back is None and g.state.in_battle:
        # no escape seen (no Flee on the menu, or every roll lost): end the fight the ordinary way -- never leave it
        # running; an escape that was under way after all still ends it (fight() returns on any result)
        tried.append("no escape seen: fought to the end")
        try:
            g.fight(timeout=FIGHT_S)
        except HarnessError as err:
            tried.append(f"fight: {str(err)[:80]}")
        back = cb.poll(g, lambda s: s.on_field and not s.in_battle and cb.free(s), 60.0, "the field after the fight")
    # every publish since the battle began, read off the driver's ring BEFORE the autosave warp pushes newer ones: the
    # record rides the end block from the drop to the battle's end
    samples = g.states_since(frame0)
    fled = fled or any(bool(cb.battle(x).get("escaping")) or (cb.battle(x).get("active") and not cb.battle(x).get("debug")
                                                             and cb.battle(x).get("result") == RES_ESCAPE) for x in samples)
    g.wait_frames(20)
    st = g.state
    hf = cb.host(st).get("flee_gil")
    tb1 = cb.peer(st).get("trailer_skipped")
    lines = cb.new(g, at)
    fp1, w1 = _fp(g, field)
    lost = (fp0.get("gil") - fp1.get("gil")) if fp0 is not None and fp1 is not None else None
    host_seen = sorted({_host_end(x).get("flee_gil") for x in samples if _host_end(x)}, key=repr)
    peer_seen = sorted({_peer_end(x).get("flee_gil") for x in samples if _peer_end(x)}, key=repr)
    led.check("S12c-H1", fled and back is not None and isinstance(lost, int) and lost >= 0 and hf == lost
              and cb.count(lines, HOST_FLEE) == 1 and any(f"{HOST_FLEE}{lost} gil" in ln for ln in lines)
              and lost in host_seen and lost in peer_seen and tb1 == tb0,
              f"turns {tried}; autosave gil {(fp0 or {}).get('gil')!r} -> {(fp1 or {}).get('gil')!r} (lost {lost!r}; "
              f"{w0 or w1 or 'read'}); host.flee_gil={hf!r}; host.end.flee_gil seen {host_seen}; peer.end.flee_gil seen "
              f"{peer_seen}; trailer_skipped {tb0!r}->{tb1!r}; {cb.grep(lines, 'battle flee')}")


# =========================================================================================== PART B (s117)
def _part_b(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("PART B (s117): the guest's defeat presentation")
    st = g.state
    led.check("S12b-P0", cb.has(st, KEY_FOLLOW), f"netsync.battle.end keys: {sorted(_end(st))}")
    ok, why = _eb(g, "kill")
    led.check("S12b-P1", not ok and NEEDS_BOOT in why and not cb.absent(why),
              "ACCEPTED on the field (it must need a booted diorama)" if ok else why)
    fp0, w0 = _fp(g, field)
    _leg(g, led, ctx, ("S12b-A1", "S12b-A2", "S12b-A3"), _b_annihilate)
    _leg(g, led, ctx, ("S12b-B0",), _b_standing)
    _leg(g, led, ctx, ("S12b-B1", "S12b-B2"), _b_settle_w2)
    _leg(g, led, ctx, ("S12b-C1", "S12b-C2", "S12b-C3"), _b_nogo)
    _leg(g, led, ctx, ("S12b-D0",), _b_phase_defeat_no_event)
    _leg(g, led, ctx, ("S12b-D1",), _b_var34)
    _leg(g, led, ctx, ("S12b-D2",), _b_phase_defeat_down)
    _leg(g, led, ctx, ("S12b-E1",), _b_song_over_b4)
    _leg(g, led, ctx, ("S12b-E2", "S12b-E3"), _b_close_defeat)
    _leg(g, led, ctx, ("S12b-W1", "S12b-W2"), _b_w1_pause)
    _leg(g, led, ctx, ("S12b-L1",), _b_hold)
    _selftest(g, led, "S12b-S1", "defeat")
    fp1, w1 = _fp(g, field)
    _inv_check(led, "S12b-INV", fp0, fp1, w0, w1)


def _b_annihilate(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12b-A: the party down, then the host's annihilation -- 'Annihilated', the stock settle, song 6, Game Over")
    cids = ("S12b-A1", "S12b-A2", "S12b-A3")
    before, bwhy = _fp_hp(g, field)
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(cids, why)
        return
    down, dwhy = _kill_all(g)
    if not down:
        led.unreached(cids, dwhy)
        _out(g, field)
        return
    at = cb.mark(g)
    ok, why = _eb(g, "defeat")
    inj = _injected(g)
    s = inj or g.state
    e = _end(s)
    lines = cb.wait_log(g, at, "diorama END: injected", 1.5)
    inj_line = [ln for ln in lines if INJ_ANNIHILATE in ln]
    led.check("S12b-A1", ok and inj is not None and e.get("action") == "annihilate"
              and e.get("inject_phase") == PHASE_MENU_OFF and e.get("inject_seq") == SEQ_MENU_OFF_DEFEAT
              and e.get("follow_msg") == "annihilated" and len(inj_line) == 1 and SONG_GO in inj_line[0],
              why or f"end={cb.pick(e, 'injected', 'held', 'action', 'inject_phase', 'inject_seq', 'follow_msg', 'why')} "
                     f"phase={_phase(s)!r}; {cb.grep(lines, 'diorama END')}")
    samples, sv = cb.watch(g, lambda x: _phase(x) == PHASE_DEFEAT, 3.0)
    menu_off_ms = _ms(sv) if sv is not None else None
    sf = cb.poll(g, lambda x: _result(x) == RES_DEFEAT and _flag(x) & BTL_PLAY_END_SONG, 4.0,
                 "result 3 + song 6's flag") if sv is not None else None
    rising, detail = _r8_rising(g)
    s = sf or g.state
    lines = cb.new(g, at)
    led.check("S12b-A2", sv is not None and isinstance(menu_off_ms, int) and menu_off_ms < 1500 and sf is not None
              and _end(s).get("watchdog") is None and rising and _r8_line(lines, PHASE_DEFEAT) == 1,
              f"PHASE_DEFEAT at inject_ms {menu_off_ms!r} (want < 1500); result={_result(s)!r} btl_flag={_flag(s)!r} "
              f"watchdog={_end(s).get('watchdog')!r} music={_end(s).get('music')!r}; {detail}; "
              f"{cb.grep(lines, 'diorama R8')}")
    titles = []
    ok2, why2 = _eb(g, "ui", "2")
    _, back = cb.watch(g, lambda x: not cb.dio(x).get("booted") and x.field_id == field and cb.free(x), 20.0,
                       on_sample=lambda x: titles.append(x.frame) if x.ui_state == "Title" else None)
    if back is None:
        cb.leave(g, field)
    else:
        cb.arrive(g, field)
    s = g.state
    el = _el(s)
    after, awhy = _fp_hp(g, field)
    diff = cb.fp_diff(before, after) if before is not None and after is not None else ["unread"]
    led.check("S12b-A3", ok2 and back is not None and not titles and el.get("trigger") == "game-over"
              and el.get("stamp") == -1 and el.get("reverted") == RES_DEFEAT and _result(s) == 0
              and el.get("music_shut") is True and cb.dio(s).get("last_return_field") == field and not diff,
              why2 or f"returned={back is not None} Title frames {titles[:3]}; end_leave="
                      f"{cb.pick(el, 'trigger', 'settled', 'stamp', 'reverted', 'music_shut', 'music_why')} field "
                      f"result={_result(s)!r}; invariants changed {diff} ({bwhy or awhy}; HP {(before or {}).get('hp')} -> "
                      f"{(after or {}).get('hp')})")
    _eb(g, "clear")


def _b_standing(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12b-B0: the host's annihilation over a STANDING local party -- the tail's writes at once, no W2")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S12b-B0",), why)
        return
    at = cb.mark(g)
    ok, why = _eb(g, "defeat")
    inj = _injected(g)
    samples = cb.hold_for(g, 9.0)
    e = _end(inj or g.state)
    wd = [cb.frame_of(x) for x in samples if _end(x).get("watchdog") is not None]
    lines = cb.new(g, at)
    tail = [ln for ln in lines if INJ_ANNIHILATE_TAIL in ln]
    led.check("S12b-B0", ok and inj is not None and e.get("action") == "annihilate" and e.get("inject_phase") == PHASE_DEFEAT
              and e.get("inject_seq") == SEQ_FADEOUT and e.get("follow_msg") == "annihilated" and len(tail) == 1
              and SETTLE_SKIPPED in tail[0] and samples and not wd,
              why or f"end={cb.pick(e, 'injected', 'held', 'action', 'inject_phase', 'inject_seq', 'follow_msg')} "
                     f"watchdog on frames {wd[:5]}; {cb.grep(lines, 'diorama END')}")
    _out(g, field)


def _b_settle_w2(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12b-B: `guest settle` keeps the per-unit settle over a standing party -- W2's defeat row")
    ok, why = _eb(g, "guest", "settle")
    if not ok:
        led.unreached(("S12b-B1", "S12b-B2"), f"`endbench guest settle` refused -- {why}")
        return
    try:
        st, swhy = _fresh(g, field)
        if st is None:
            led.unreached(("S12b-B1", "S12b-B2"), swhy)
            return
        at = cb.mark(g)
        ok2, why2 = _eb(g, "defeat")
        inj = _injected(g)
        held, moved = cb.watch(g, lambda x: _phase(x) != PHASE_MENU_OFF and _end(x).get("injected") is True, 14.0)
        pre = [x for x in (held[:-1] if moved is not None else held) if _end(x).get("injected") is True]
        flip_ms = _ms(moved) if moved is not None else None
        w2 = cb.poll(g, lambda x: "W2" in str(_end(x).get("watchdog") or ""), 4.0, "W2 to fire")
        e = _end(w2 or g.state)
        lines = cb.new(g, at)
        e_inj = _end(inj or g.state)
        led.check("S12b-B1", ok2 and inj is not None and e_inj.get("inject_phase") == PHASE_MENU_OFF
                  and e_inj.get("inject_seq") == SEQ_MENU_OFF_DEFEAT and pre
                  and all(_phase(x) == PHASE_MENU_OFF for x in pre) and isinstance(flip_ms, int) and flip_ms > 8000
                  and w2 is not None and NOT_DOWN in str(e.get("blocker") or "")
                  and any(W2_LINE in ln and W2_ANNIHILATE_ROW in ln for ln in lines),
                  why2 or f"inject={cb.pick(e_inj, 'action', 'inject_phase', 'inject_seq')}; MENU_OFF on {len(pre)} "
                          f"publish(es), left it at inject_ms={flip_ms!r}; watchdog={e.get('watchdog')!r} blocker="
                          f"{e.get('blocker')!r}; {cb.grep(lines, 'watchdog W2')}")
        after, _ = cb.watch(g, lambda x: (_end(x).get("r8_hits") or 0) > 0, 10.0)
        tail = [x for x in ([moved] if moved is not None else []) + after]
        wrong = [(cb.frame_of(x), _phase(x), _result(x)) for x in tail if _phase(x) == PHASE_VICTORY
                 or _result(x) == RES_VICTORY]
        rising, detail = _r8_rising(g, first_s=4.0)
        s = g.state
        led.check("S12b-B2", moved is not None and tail and not wrong and any(_phase(x) == PHASE_DEFEAT for x in tail)
                  and _result(s) == RES_DEFEAT and rising,
                  f"after W2: phase/result {[(_phase(x), _result(x)) for x in tail[:3]]}..; VICTORY/1 on {wrong[:5]}; "
                  f"result now {_result(s)!r}; {detail}")
        _out(g, field)
    finally:
        _eb(g, "guest", "on")


def _no_gameover(st):
    v = (cb.battle(st).get("scene_info") or {}).get("no_gameover")
    return v if isinstance(v, bool) else None


def _b_nogo(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12b-C: a NoGameOver annihilation -- no song, then the result-screen replay and the DEFEAT stamp")
    cids = ("S12b-C1", "S12b-C2", "S12b-C3")
    tried = []
    for scene in NOGO_SCENES:
        st, why = _fresh(g, field, scene)
        if st is None:
            tried.append(f"scene {scene}: {why}")
            continue
        nogo = _no_gameover(st)
        if nogo is not True:
            tried.append(f"scene {scene} booted but reads scene_info.no_gameover={nogo!r}")
            _out(g, field)
            continue
        break
    else:
        led.unreached(cids, "no NoGameOver scene booted as one -- " + "; ".join(tried))
        return
    note = f"scene {scene} (NoGameOver)" + (f"; skipped first: {'; '.join(tried)}" if tried else "")
    down, dwhy = _kill_all(g)
    if not down:
        led.unreached(cids, f"{note}: {dwhy}")
        _out(g, field)
        return
    at = cb.mark(g)
    r0 = cb.dio(g.state).get("returns")
    ok, why = _eb(g, "defeat")
    inj = _injected(g)
    samples, r8 = cb.watch(g, lambda x: (_end(x).get("r8_hits") or 0) > 0, 12.0)
    e = _end(inj or g.state)
    song = [cb.frame_of(x) for x in samples if _flag(x) & BTL_PLAY_END_SONG]
    lines = cb.new(g, at)
    inj_line = [ln for ln in lines if INJ_ANNIHILATE in ln or INJ_ANNIHILATE_TAIL in ln]
    led.check("S12b-C1", ok and inj is not None and e.get("action") == "annihilate"
              and any(_phase(x) == PHASE_DEFEAT for x in samples) and r8 is not None and not song
              and len(inj_line) == 1 and SONG_NOGO in inj_line[0],
              why or f"{note}: end={cb.pick(e, 'action', 'inject_phase', 'inject_seq', 'follow_msg')} R8 "
                     f"{r8 is not None}; btl_flag & 32 on frames {song[:5]}; {cb.grep(lines, 'diorama END')}")
    oks = [_eb(g, *a) for a in (("phase-defeat",), ("manifest", "1"), ("ui", "1"))]
    op = cb.poll(g, lambda x: _rep(x).get("opened") is True, 4.0, "the replay to open") if r8 is not None else None
    rp = _rep(op or g.state)
    led.check("S12b-C2", all(o for o, _ in oks) and op is not None and rp.get("verdict") == 0,
              "; ".join(w for _, w in oks if w) or f"{note}: replay={cb.pick(rp, 'armed', 'opened', 'verdict', 'why')}")
    if op is None:
        led.unreached(("S12b-C3",), "the replay never opened")
        _eb(g, "state", "7")
        _arrive_after_exit(g, field)
        _eb(g, "clear")
        return
    closed, trail = _replay_walk(g, ((("state", "1"), 1, 30.0), (("state", "2"), 2, 30.0),
                                     (("state", "2", "loading"), 3, 10.0), (("state", "5"), 5, 8.0),
                                     (("state", "6"), 6, 8.0)))
    back, bwhy = _arrive_after_exit(g, field)
    s = g.state
    el = _el(s)
    led.check("S12b-C3", closed and back and el.get("trigger") == "result-hide" and el.get("stamp") == RES_DEFEAT
              and _result(s) == RES_DEFEAT and isinstance(r0, int) and cb.dio(s).get("returns") == r0 + 1,
              bwhy or f"{note}: walk {trail}; trigger={el.get('trigger')!r} stamp={el.get('stamp')!r} "
                      f"stamped={el.get('stamped')!r} field result={_result(s)!r}")
    _eb(g, "clear")


def _b_phase_defeat_no_event(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12b-D0: PHASE_DEFEAT with the party up and no event phase -- an annihilation the diorama cannot mirror")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S12b-D0",), why)
        return
    at = cb.mark(g)
    ok, why = _eb(g, "phase-defeat")
    inj = _injected(g)
    e = _end(inj or g.state)
    lines = cb.wait_log(g, at, "diorama END: injected", 1.5)
    tail = [ln for ln in lines if INJ_ANNIHILATE_TAIL in ln]
    led.check("S12b-D0", ok and inj is not None and e.get("action") == "annihilate" and e.get("inject_phase") == PHASE_DEFEAT
              and e.get("inject_seq") == SEQ_FADEOUT and e.get("follow_msg") == "annihilated" and len(tail) == 1
              and SETTLE_SKIPPED in tail[0],
              why or f"end={cb.pick(e, 'injected', 'held', 'action', 'inject_phase', 'inject_seq', 'follow_msg')}; "
                     f"{cb.grep(lines, 'diorama END')}")
    _out(g, field)


def _b_var34(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12b-D1: the host's event phase, then PHASE_DEFEAT with the party up -- var 34's scripted end")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S12b-D1",), why)
        return
    at = cb.mark(g)
    ok, why = _eb(g, "event")
    quiet = cb.hold_for(g, 0.8)                           # EndTick latches the host's event block; nothing presented
    ok2, why2 = _eb(g, "phase-defeat")
    inj = _injected(g)
    after = cb.hold_for(g, 2.0)
    e = _end(inj or g.state)
    menu_off = [cb.frame_of(x) for x in quiet + after if _phase(x) == PHASE_MENU_OFF]
    early = [cb.frame_of(x) for x in quiet if _end(x).get("injected")]
    lines = cb.new(g, at)
    led.check("S12b-D1", ok and ok2 and inj is not None and not early and e.get("action") == "defeat"
              and e.get("inject_phase") == PHASE_DEFEAT and e.get("inject_seq") == SEQ_FADEOUT
              and e.get("follow_msg") is None and not menu_off and cb.count(lines, INJ_VAR34) == 1,
              (why or why2) or f"end={cb.pick(e, 'injected', 'action', 'inject_phase', 'inject_seq', 'follow_msg')} "
                                f"injected during the event on {early[:3]}; MENU_OFF on {menu_off[:5]}; "
                                f"{cb.grep(lines, 'diorama END')}")
    _out(g, field)


def _b_phase_defeat_down(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12b-D2: the party down, then PHASE_DEFEAT -- the settled annihilation")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S12b-D2",), why)
        return
    down, dwhy = _kill_all(g)
    if not down:
        led.unreached(("S12b-D2",), dwhy)
        _out(g, field)
        return
    ok, why = _eb(g, "phase-defeat")
    inj = _injected(g)
    e = _end(inj or g.state)
    led.check("S12b-D2", ok and inj is not None and e.get("action") == "annihilate" and e.get("follow_msg") == "annihilated",
              why or f"end={cb.pick(e, 'injected', 'held', 'action', 'inject_phase', 'inject_seq', 'follow_msg')}")
    _out(g, field)


def _b_song_over_b4(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12b-E: the host keeps its field song (b4), but this guest's Game-Over defeat played song 6 -- shut anyway")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S12b-E1",), why)
        return
    down, dwhy = _kill_all(g)
    if not down:
        led.unreached(("S12b-E1",), dwhy)
        _out(g, field)
        return
    oks = [_eb(g, "fieldsong", "1"), _eb(g, "defeat")]
    inj = _injected(g)
    sang = cb.poll(g, lambda x: _phase(x) == PHASE_DEFEAT and _flag(x) & BTL_SONG_FADEOUT, 6.0,
                   "PHASE_DEFEAT and song 6's fade-out flag") if inj is not None else None
    at = cb.mark(g)
    oks.append(_eb(g, "ui", "2"))
    back, bwhy = _arrive_after_exit(g, field)
    s = g.state
    el = _el(s)
    lines = cb.new(g, at)
    leaving = [ln for ln in lines if LEAVING in ln]
    led.check("S12b-E1", all(o for o, _ in oks) and inj is not None and sang is not None and back
              and el.get("music_shut") is True and len(leaving) == 1 and OVER_B4 in leaving[0],
              "; ".join(w for _, w in oks if w) or bwhy or
              f"injected={inj is not None} song 6 flags seen={sang is not None} (btl_flag {_flag(sang or s)!r}); "
              f"music_shut={el.get('music_shut')!r} music_why={el.get('music_why')!r}; {cb.grep(lines, 'leaving a finished')}")
    _eb(g, "clear")


def _present_close_defeat(g) -> tuple:
    """`endbench other 3` (the host's CLOSE + DEFEAT) and poll the PRESENTED CLOSE fade: injected, action 'close', inject
    8/0 and the local battle.result 3 (CloseResult keeps the host's DEFEAT). (presented state or None, detail)."""
    ok, why = _eb(g, "other", str(RES_DEFEAT))
    if not ok:
        return None, f"`endbench other {RES_DEFEAT}` refused -- {why}"
    pres = cb.poll(g, lambda x: _end(x).get("injected") is True and _end(x).get("action") == "close"
                   and _end(x).get("inject_phase") == PHASE_CLOSE and _end(x).get("inject_seq") == SEQ_FADEOUT
                   and _result(x) == RES_DEFEAT, 3.0, "the CLOSE fade of the host's DEFEAT (local result 3)")
    e = _end(pres or g.state)
    return pres, (f"end={cb.pick(e, 'injected', 'held', 'action', 'inject_phase', 'inject_seq', 'follow_msg')} local "
                  f"result={_result(pres or g.state)!r}")


def _b_close_defeat(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """Design 6.6 row E (review R3H-2): the host's CLOSE + DEFEAT -- var 33's scripted end, or a late join -- is the
    CLOSE fade on an s117 guest (PresentFor's last defeat row). In a Game-Over scene the defeat is never stamped and the
    no-leak rule reverts the local 3 (E2); in a NoGameOver scene it is stamped 3 and nothing is reverted (E3). Before
    s117 (and under `guest hold`) the same block is HELD: nothing injected, so both read red there."""
    field = ctx.field
    g.note("S12b-E2: CLOSE + DEFEAT in scene 67 (a Game-Over scene) -- the CLOSE fade, then the host's Game Over")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S12b-E2",), why)
    else:
        nogo = _no_gameover(st)
        pres, pdetail = _present_close_defeat(g)
        titles = []
        ok2, why2, back = False, "", None
        if pres is not None:
            ok2, why2 = _eb(g, "ui", "2")
            _, back = cb.watch(g, lambda x: not cb.dio(x).get("booted") and x.field_id == field and cb.free(x), 20.0,
                               on_sample=lambda x: titles.append(x.frame) if x.ui_state == "Title" else None)
        if back is None:
            cb.leave(g, field)
        else:
            cb.arrive(g, field)
        s = g.state
        el = _el(s)
        led.check("S12b-E2", nogo is False and pres is not None and _end(pres).get("follow_msg") is None and ok2
                  and back is not None and not titles and el.get("trigger") == "game-over" and el.get("stamp") == -1
                  and el.get("reverted") == RES_DEFEAT and _result(s) == 0,
                  why2 or f"scene {SCENE} no_gameover={nogo!r}; presented={pres is not None}: {pdetail}; returned="
                          f"{back is not None} Title frames {titles[:3]}; end_leave="
                          f"{cb.pick(el, 'trigger', 'stamp', 'stamped', 'reverted')} field result={_result(s)!r}")
        _eb(g, "clear")
    g.note("S12b-E3: CLOSE + DEFEAT in a NoGameOver scene -- the CLOSE fade, then the result-hide's DEFEAT stamp")
    tried = []
    for scene in NOGO_SCENES:
        st, why = _fresh(g, field, scene)
        if st is None:
            tried.append(f"scene {scene}: {why}")
            continue
        nogo = _no_gameover(st)
        if nogo is not True:
            tried.append(f"scene {scene} booted but reads scene_info.no_gameover={nogo!r}")
            _out(g, field)
            continue
        break
    else:
        led.unreached(("S12b-E3",), "no NoGameOver scene booted as one -- " + "; ".join(tried))
        return
    note = f"scene {scene} (NoGameOver)" + (f"; skipped first: {'; '.join(tried)}" if tried else "")
    pres, pdetail = _present_close_defeat(g)
    oks = [_eb(g, *a) for a in (("ui", "1"), ("state", "7"))] if pres is not None else []
    if pres is not None:
        back, bwhy = _arrive_after_exit(g, field)
    else:
        back, bwhy = False, ""
        cb.leave(g, field)
    s = g.state
    el = _el(s)
    led.check("S12b-E3", pres is not None and all(o for o, _ in oks) and back and el.get("trigger") == "result-hide"
              and el.get("stamp") == RES_DEFEAT and el.get("reverted") == -1 and _result(s) == RES_DEFEAT,
              "; ".join(w for _, w in oks if w) or bwhy or
              f"{note}: presented={pres is not None}: {pdetail}; end_leave="
              f"{cb.pick(el, 'trigger', 'stamp', 'stamped', 'reverted')} field result={_result(s)!r}")
    _eb(g, "clear")


def _b_w1_pause(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """W1 counts BATTLE time (the s117 bundle, the s115 review's W1 twin): the guest pauses at the victory camera and
    the host reaches its result screen meanwhile -- a wall-clock W1 fires during the pause and forces the FADEOUT."""
    field = ctx.field
    g.note("S12b-W: a victory paused at the camera move while the host reaches its result screen")
    st, why = _fresh(g, field)
    if st is None:
        led.unreached(("S12b-W1", "S12b-W2"), why)
        return
    paused_by_us = False
    try:
        ok, why = _eb(g, "victory")
        cam = cb.poll(g, lambda x: _phase(x) == PHASE_VICTORY and _seq(x) == SEQ_VICTORY_CAMERA_MOVE, 4.0,
                      "PHASE_VICTORY at the camera move")
        if not ok or cam is None:
            led.unreached(("S12b-W1", "S12b-W2"), why or f"no PHASE_VICTORY + seq 0 to pause at (phase {_phase(g.state)!r} "
                                                         f"seq {_seq(g.state)!r})")
            return
        g.press("start", 4)
        paused = cb.poll(g, lambda x: x.ui_state == "Pause", 3.0, "the pause")
        if paused is None:
            led.unreached(("S12b-W1", "S12b-W2"), f"the pause never engaged (ui {g.state.ui_state!r}, phase "
                                                  f"{_phase(g.state)!r} seq {_seq(g.state)!r}: OnKeyPause refuses seq 1/2)")
            return
        paused_by_us = True
        at = cb.mark(g)
        t_pause = time.time()
        ok2, why2 = _eb(g, "ui", "1")
        armed = cb.poll(g, lambda x: _end(x).get("w1_armed") is True, 2.0, "W1 armed")
        samples = cb.hold_for(g, 6.0)
        held_s = time.time() - t_pause
        moved = [(cb.frame_of(x), _phase(x), _seq(x), _end(x).get("watchdog")) for x in samples
                 if _end(x).get("watchdog") is not None or _phase(x) != PHASE_VICTORY or _seq(x) != SEQ_VICTORY_CAMERA_MOVE]
        led.check("S12b-W1", ok2 and armed is not None and samples and held_s >= 5.5 and not moved,
                  why2 or f"w1_armed={_end(g.state).get('w1_armed')!r}; paused {held_s:.1f}s; moved/fired on "
                          f"{moved[:4]}; {cb.grep(cb.new(g, at), 'watchdog')}")
        g.press("start", 4)
        paused_by_us = False
        cb.poll(g, lambda x: x.ui_state == "BattleHUD", 4.0, "the resume")
        _, s2 = cb.watch(g, lambda x: _phase(x) == PHASE_VICTORY and _seq(x) == SEQ_VICTORY_WAIT, 14.0)
        s = s2 or g.state
        wd = str(_end(s).get("watchdog") or "")
        lines = cb.new(g, at)
        w1 = [ln for ln in lines if W1_LINE in ln]
        if "W1" in wd:
            m = W1_PAUSED_RX.search(w1[0]) if len(w1) == 1 else None
            w2ok = s2 is not None and m is not None and int(m.group(1)) >= 5000
        else:
            w2ok = s2 is not None and not w1
        led.check("S12b-W2", w2ok,
                  f"seq 2 {'reached' if s2 is not None else 'NOT reached'}; watchdog={wd or None!r}; "
                  f"{cb.grep(lines, 'watchdog W1')}")
    finally:
        if paused_by_us or g.state.ui_state == "Pause":
            g.press("start", 4)
            cb.poll(g, lambda x: x.ui_state != "Pause", 4.0, "the resume (cleanup)")
        _out(g, field)


def _b_hold(g, led: cb.Ledger, ctx: _Ctx) -> None:
    field = ctx.field
    g.note("S12b-L1: the lever `endbench guest hold` -- the pre-s117 guest holds the defeat")
    ok, why = _eb(g, "guest", "hold")
    if not ok:
        led.check("S12b-L1", False, f"not reached: `endbench guest hold` refused -- {why}")
        return
    try:
        st, swhy = _fresh(g, field)
        if st is None:
            led.unreached(("S12b-L1",), swhy)
            return
        at = cb.mark(g)
        ok2, why2 = _eb(g, "defeat")
        held = cb.poll(g, lambda x: _end(x).get("held") is True, 2.0, "the defeat to be HELD")
        samples = cb.hold_for(g, 1.5)
        bad = [cb.frame_of(x) for x in samples if not (_end(x).get("held") is True and _end(x).get("injected") is False
                                                       and _phase(x) == PHASE_NORMAL)]
        e = _end(g.state)
        lines = cb.new(g, at)
        led.check("S12b-L1", ok2 and held is not None and samples and not bad and e.get("action") == "hold"
                  and _hold_lever_needles(lines, HELD_DEFEAT),
                  why2 or f"end={cb.pick(e, 'held', 'injected', 'action', 'guest_mode', 'follow_msg')} off-hold frames "
                          f"{bad[:5]}; {cb.grep(lines, 'diorama END')}")
        _out(g, field)
    finally:
        _eb(g, "guest", "on")


# ------------------------------------------------------------------------------------------- shared
def _selftest(g, led: cb.Ledger, cid: str, section: str) -> None:
    """`endbench selftest` -> OK, and the named section's count > 0 (its rows exist on this engine)."""
    at = cb.mark(g)
    ok, why = _eb(g, "selftest")
    lines = cb.wait_log(g, at, "harness: battle end-block selftest", 2.0)
    n = _selftest_count(lines, section)
    led.check(cid, ok and isinstance(n, int) and n > 0,
              why or f"{section} {n!r}; {cb.grep(lines, 'end-block selftest')}")
