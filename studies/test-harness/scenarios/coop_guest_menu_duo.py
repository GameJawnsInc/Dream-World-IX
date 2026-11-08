"""s168 -- THE GUEST'S MAIN MENU, RUNG 0 (view only): THE DUO (D) AND T2 (T) ROWS. [ff9mapkit netsync s168]
studies/field-coop/S168-DESIGN.md "The bench": every GM0 row the table marks D or T, beside coop_guest_menu.py's solo (S) rows -- its
readers, moves and judges IMPORTED, never copied (snap, press_menu, cancel_out, goto_screen, drive_site, the restore / chip / browse /
site / why / worldtag4 judges). Decision 35: the selftest role proves the ACTION only; THE DUO (tools/harness/duo.py: two real games, one
DLL through the instance junction) proves the key path for a MIRRORING guest, the real triggers and parity; T2 (tools/play.py, the desktop a
real client fed by coop_peer's replay-host) proves what a tape can: an unmirrored world-paired guest, an OLDER host, and -- once the
owner-gated b3 tape exists -- the key path, the freeze, the stall, the leave, the cut and the ramp against a recorded s168 host.

THE STAGE, read off EACH game's probe: `netsync.guestmenu` published = s168 (NEW, LEVER); absent = OLD (the deployed s167: the sub-verb
unknown, the key absent). On OLD no `guestmenu` op is EVER sent; every row reads "not reached" and the leg MEASURES s167's shape: a
MIRRORING guest's press refused as s121 ("audible", `menu_refusal.count` +1, the menu never opens) -- the measuring rows (GM0-STSCENE,
GM0-HUDSTRIP, GM0-DIALOG-PATH-A / -B) run on OLD and NEW alike. THE LAWS: THE PRE-INIT SAMPLE (a press only from the HUD with control, no
fade, no window, events on -- coop_guest_menu._ready); THE ORDER SKEW (each op's own publish dropped); LIVE VERDICT vs LAST DRAWN (`now` a
live read, `why` the last refusal's book: every judge reads deltas from a base taken right before); NEVER JUDGED WHILE SEATED (fp reads
after the close); THE DUO CANNOT PULL A SELFTEST-ROLE LEVER (every duo lever is an ANY-ROLE `guestmenu` op: `old`, `close old`, `caps
off`, `capture off`; the bench's `frame` / `fireclose` / faults are the solo's); THE EXCLUDED PORT RANGE (the runner's duo ports clear of
Parsec's 49211 and Windows' 49252-49351: duo.py --bridge-ports); THE CAL RULE (every launch: exactly the predicted reds, each MEASURED).

THE DUO LEGS (COOP_GMD_LEG, one per duo launch: `py tools/harness/duo.py studies/test-harness/scenarios/coop_guest_menu_duo.py`; PAIR is
the leg's -- 250 with the HOST's party seeded through COOPPARTY, so the seat is a SECOND MARKER the guest's own New-Game party is not):
  key      GM0-KEY (FieldHUD, a b3 host: `now` guest on the HUD, the press: MainMenu, menu_refusal.count +0, opens +1, seated, seat.src
           'wire', frame_age_ms -1), GM0-SEAT-D (for every wire-carried component seat_fp == the HOST's host_fp -- players, party, bag, gil;
           keyitems REPORTED: K1's HashSet order; TWO MARKERS: seat_fp's players / party differ from the guest's own fp_before), GM0-CHIP-D,
           GM0-BROWSE-D (the screens, the greyed rows, no Save row, Alt+F5 refused), GM0-REFUSE-I1-D (one census confirm, the S judge),
           GM0-LOCAL-D (a sort on the Item screen -- DESIGN D5: the bar's Arrange, Auto pressed and unmeasured, then Manual: rows 0 and 2
           swap on the seated copy, L0 read back at row 2 -- refused +0, captures +0, the HOST's host_fp bag unchanged, fp equal),
           GM0-FREEZE-D (event_enable false on every seated sample, true after the close: GM0-FREEZE's duo half until the b3 tape),
           GM0-GHOST (GhostAs=auto on both: each game's ghost of the other keeps its model and rig for the whole open), GM0-RESTORE-D
           (every cycle fp_after == fp_before), GM0-KEY-DOUBLE (FadeDuration >= 300 only: two presses 100 ms apart -- one open,
           menu_refusal.count +0, no line; else "not run (configuration)", out of the verdict). LEVERS `old` (the guest: exactly OLD),
           `capture` (`capture off` on the guest: REFUSE-I1-D passes +1).
  caps     GM0-CAPS-a (the HOST pulls `guestmenu caps off`: the guest's press is s121 exactly -- audible, count +1, lines +1, FieldHUD,
           why 'older' and its words, ONE caps line on the guest naming "guest menu"; `caps on` again: the press opens), GM0-PAIRED-LINE-F
           (that refusal: `session.overlay` 'guest_menu' while the line lives, the prior overlay after), GM0-BW (the HOST's frame book:
           with b3 `sec12_len` > 0; under `caps off` the type-5 frame shrinks by at least the block; `tx_bps` read >= 1 s apart, REPORTED).
           LEVER `old`.
  world    pair on 6603, the host walks out, the guest follows out to 9011: GM0-WORLD (walking, then frozen under `worldwalk walk off`:
           each press seated and restored; aboard -- the guest's own `vehicle 1` -- refused 'riding', audible), GM0-PAIRED-LINE-W (the
           riding refusal shows 'guest_menu' over the world chain's line, then that line returns), GM0-WORLDTAG4-D (coop_guest_menu's
           judge on a seated open with an Item round trip: outside_settled, uid0_vars and sysvar192), GM0-STSCENE (MEASURING: the host's own
           main menu 2 s -- the guest's view of the host trailer and its walk why, REPORTED; a rise is a Known limit), GM0-WALKGHOST
           (MEASURING: the HOST's ghost of the seated guest, sampled, and a shot), GM0-RAMP-WORLD-D (LAST: seated on WorldHUD, the
           duo's blackhole past the guest's SessionGraceMs -- 5000, PAIR's -- closes.ending, its door before the fire: end done, or
           clear_point at the exit ramp's fire; the restore line before 'reloading own autosave', no alarm line, fp equal:
           GM0-RAMP-WORLD's duo half until the b3 tape). LEVER `old`.
  leave    GM0-LEAVE (the guest in Equip's candidates, the host `warp`s 30602: closes.leave +1, end done, the guest lands, the pin
           under 2500 ms, a guest shot within 4 s of the close -- READ it for the close line), GM0-FADE (a second follow close at the ROOT
           as the host warps back: both closes land, both pins fresh), GM0-TIMING (MEASURING: close-to-HUD ms, the pin's age, FadeDuration).
           LEVERS `old`, `closeold` (`close old` on the guest + a Cancel 3.5 s after the warp: no close, the follow DEFERRED to the manual
           close -- DP-AGED's shape).
  door     GM0-DOOR-D alone, on its own launch (S168-DESIGN R5; FadeDuration >= 800 only, else "not run (configuration)"): a press,
           then the host's warp inside the guest's Hide fade: the DOOR refuses scene / control / busy / leaving -- a host's door turns
           its control off and fades for most of a second before its intent goes out, so the guest's door reads `scene` (F4), the
           likeliest; `control` once the follow has armed (DESIGN D1), `busy` / `leaving` before -- nothing seated, events on, the
           follow lands. The long fade puts the host's control-off well inside the Hide fade (at 300 it beat the door by ~33-96 ms, so a
           slower hop seats the menu), while the commit -- 0.9 s after the warp plus the ~450 ms follow fade -- still lands after the
           door. LEVER `old` (its press is refused at the press, so the row runs at any fade).
  out      pair on 6603: GM0-OUT (the guest seated, the host walks out: closes.out +1, the guest lands on 9011, at most one 'waits: the
           field HUD is not up' -- the request frame's, decision 18 keeps deferring -- logged before the close's end line, the start
           after the door, its 'live on the world map for N ms' >= 1200). LEVERS `old`, `closeold`.
  rejoin   pair on 6603, both out on 9011: GM0-REJOIN (the guest seated, the host Confirms into 300: closes.rejoin +1, then the rejoin
           lands; at most one 'waits: the world HUD is not up' -- the request frame's -- before the close's end line, the arm after the
           door). LEVERS `old`, `closeold`.
  cut      GM0-CUT (the guest in Item, the host's `battle 67 -1`: closes.cut +1 -- end done, or on a field clear_point at the boot's scene
           load with the door before 'diorama BOOT' -- the HOST's start-hold report 'booting', the guest's 'diorama LIVE' (counted after
           the fight: it lands at the command phase), fp equal after the return, a shot), GM0-SILENT-D (the guest's diorama: `now`
           'silent' on BattleHUD, a press keeps BattleHUD, `bmenu mainmenu` refused), GM0-CUT-QUIT (once the host's battle lane is stale
           on the guest -- term 6's PeerBattleLive holds StaleMs 2000 -- a second battle with the guest's quit prompt up: the close waits
           -- close_step 'quit' -- the report 'busy', never 'booting', over a window that opens at the guest's own close, closes.cut +1,
           never at the host's battle: S168-DESIGN R1; the prompt's Cancel lets the close end). LEVERS `old`, `closeold`.
           COOP_GMD_BATTLE=0: the cut rows "not run (configuration)" (the stand-in duo models no diorama). THE QUIT PROMPT ON A DUO:
           `endbench quit on` is a SELFTEST-ROLE lever (NetSyncEnd.HarnessEndBench), so on its refusal the leg posts a WM_CLOSE to the
           guest's window (instance.post_close: UIKeyTrigger.OnApplicationQuit cancels the quit and opens the stock prompt -- grounded in
           source, PROVEN in game by the 2026-11-08 reruns, rampquit and cut each raised it on a client; never Confirm under it); when
           that raises nothing GM0-CUT-QUIT and
           GM0-QUIT-D read "not run" (named, out of the calibration) -- an OPEN ITEM, not a pass; its two-PC route is B32.
  title    GM0-TITLE (the host soft-resets: closes.title +1 within CloseCapMs + two fades, its words). LEVERS `old`, `closeold` (MEASURED:
           closes.title +0, still seated for TITLE_HOLD_S, then the guest's own Cancel restores at the door: doors +1, fp equal).
  scene    pair on 30801: GM0-SCENE (the host talks to the scribe while the guest's menu is open: closes.scene +1, the talk plays on the
           guest, no 'expired before my copy was free'). LEVERS `old`, `closeold` (the expired line, no window).
  chest    pair on 200 (the chest relay's recipe): GM0-SCENE-CHEST (the host opens ChestA: closes.scene +1, the guest's 'opening chest'
           line). LEVERS `old`, `closeold`.
  ramp     GM0-RAMP-CFG-D (the guest seated at Item, its own [Netsync] Enabled=0 written live: closes.ending +1 -- end done, or
           clear_point at the exit ramp's fire, which the ramp block runs ahead of the close tick -- the door's restore line before
           'reloading own autosave', the close words, fp equal, input live after). LEVERS `old`, `closeold`. The Role edit is not a duo
           edit (duo.set_netsync owns Role): the S leg's.
  rampquit GM0-QUIT-D (the guest's quit prompt up over its seated menu -- `endbench quit on`, else the WM_CLOSE fallback -- then
           Enabled=0: the ramp's fire waits it out and restores quietly -- restore.backstops.ramp_quit +1, ramp +0, no 'should never
           happen' line, no prompt after the Autoload).
  stall    THE DUO'S BLACKHOLE (the host's bridge suspended: both directions silent, the TCP open): GM0-STALL-VIEW-D (seated through 3 s:
           still seated on every sample, closes +0), GM0-PAIRED-LINE-LOST (a press inside the blip hold: refused audibly, 'guest_menu' on
           the overlay), GM0-RAMP-FIELD-D (seated, a blackhole past SessionGraceMs: closes.ending at the ramp's arm -- end done, or
           clear_point at the exit ramp's fire -- the restore line before 'reloading own autosave', no alarm line, fp equal). LEVER `old`.
  dialog   pair on 30801: GM0-DIALOG-PATH-A (the host's line LOCKED on the guest: a press -- the window stays, `netsync.suppress` true,
           count +0, silent +0, opens +0), GM0-DIALOG-PATH-B (`netsync unlock` on the guest, the host's line again: `now` 'dialog', the
           window stays, count +0, opens +0). OLD and NEW alike (s121's own: measured on both). No lever (its mutant is the stand-in's).
  hudstrip GM0-HUDSTRIP (MEASURING, a Known limit: on COOP_GMD_STRIP_FIELD with a persistent kit strip -- `now` 'dialog', count and
           silent +0, opens +0, no line, the strip stays). OLD and NEW alike.

THE T LEGS (COOP_GMT_LEG, `py tools/play.py studies/test-harness/scenarios/coop_guest_menu_duo.py`; THE OWNER'S BRIDGE DOWN):
  hole      coop_world_walk_t2's stallhole route (the guest walks out ALONE, the ROAM host -- or its INSTRUMENT -- `--from` a world second
            pairs it ON THE WORLD MAP, unmirrored): GM0-HOLE-T (a press once the session itself holds -- session.state 'live', and
            guestmenu.session on s168: THE PRE-INIT SAMPLE at the pairing edge -- refused 'not_mirroring', audible, its words, never seated),
            GM0-STALL-WHO-T (a 3 s blackhole, the lane past StaleMs: still refused). OLD: its own menu opens (measured). LEVER `old`.
  older166  GM0-CAPS-b-166 / GM0-CAPS-b-167: an s166 (caps 0x0001) / s167 (0x0003) HOST replayed (the recorded tape named by
  older167  COOP_TAPE_GM_OLDER166 / 167, else THE INSTRUMENT of that caps word, named so): paired and mirroring on 6603, a press refused as
            s121 (audible, count +1, why 'older', its words) and the caps line naming "guest menu". OLD: refused as s121, the caps line
            naming "world fingerprint" (s166) or none (s167) -- measured. No lever.
  tape      COOP_TAPE_GUEST_MENU (OWNER-GATED: coop_tape_record.py's GUEST-MENU variant, an s168 host): S168-GMT-GATE red until it exists
            (never part of a calibration); with it GM0-KEY-T, GM0-FREEZE-T (event_enable false while seated, true after), GM0-STALL-VIEW-T
            (`--blackhole-at` 3 s, seated through), GM0-LEAVE-T (seated before the host's warp: closes.leave, the guest lands), GM0-CUT-T
            (seated before the battle: closes.cut, the diorama boots), GM0-RAMP-T (`--stop-at` then the grace: closes.ending at the arm,
            the restore line before 'reloading own autosave'; COOP_GMT_RAMP=field|world). LEVER `old`.
  GM0-CAPS-c is coop_cut_hold.py's s121 leg on its v14 tape, unchanged (the regression set's fallback row): not a leg here.

THE D HALVES CARRIED BY OTHER ROWS: GM0-WHY-x's -- the whys a duo reaches ride their own rows: older (GM0-CAPS-a), riding
(GM0-WORLD), link (GM0-PAIRED-LINE-LOST), scene / control / busy / leaving (GM0-DOOR-D); the rest are the S bench's bench ops.
GM0-REFUSE-x's D spot check is GM0-REFUSE-I1-D; GM0-RESTORE's is GM0-RESTORE-D plus every close row's fp_after == fp_before
(THE RESTORE FINGERPRINT AFTER EACH CLOSE); GM0-SEAT / GM0-CHIP / GM0-BROWSE / GM0-LOCAL / GM0-SILENT / GM0-RAMP-CFG / GM0-QUIT /
GM0-PAIRED-LINE / GM0-WORLDTAG4 /
GM0-STALL-VIEW / GM0-RAMP-FIELD / GM0-RAMP-WORLD / GM0-FREEZE carry a -D (or -F / -W / -LOST) row here; GM0-HOLE / GM0-STALL-WHO /
GM0-KEY / GM0-FREEZE / GM0-LEAVE / GM0-CUT / GM0-RAMP-WORLD a -T row (GM0-RAMP-T with COOP_GMT_RAMP=world). GM0-DOOR's long-fade
duo leg is GM0-DOOR-D (its own `door` launch). GM0-STALL-WHO has no duo half (the duo pairs a MIRRORING guest: an unmirrored one is
the T route's).
GM0-HOLE's D half likewise: a duo pairs a mirroring guest, so the unmirrored world-paired press is the T route's (GM0-HOLE-T).
GM0-DIALOG-PATH has no T half: the duo's -A / -B judge the same s121 dialog path on two real games; a T leg on the tape's recorded host
talk is an open item.
WHAT NO LEG HERE REACHES (named, not hidden): the `world` close (world-to-world: the trailer's world changes with no field between --
whether stock ever moves a host so is unverified, a Known limit; its ACTION is the S bench's GM0-CLOSE-IDS); GM0-BRACKET (the diorama legs
on the pinned W1a/b DLL: the regression runner's); GM0-CUT-NOBOOT (its field variant needs a battle scene missing on the guest -- one
install on one PC: the two-PC sheet; its world variant, a world visit the guest declines, has no harness route here -- the close itself is
the cut's own trigger, proven by `cut`); 9010 for GM0-REJOIN and GM0-WORLDTAG4-D (no harness route: the New-Game exit cascade lands on
9011 only, as coop_world_walk names 9002 / 9010; both run on 9011); GM0-REJOIN's FROZEN guest (the leg seats a walking guest only -- an
open item); GM0-PAIRED-LINE's past-grace press (the design's second peer-lost press: a `session` refusal between the blip hold's end and
the ramp's fire, under the session's own line -- OvlReconnecting while SessionGrace holds, not the connecting line the design row names;
the window is ~0 at this leg's SessionGraceMs 5000 against GhostGraceMs 5000; CR-2's precedence is proof-only, `line_over_connecting`,
its in-game half an open item); GM0-DEATH (a kill and a relaunch: NO runner or leg launches it -- an open item); GM0-RAMP-WORLD's and
GM0-RAMP-FIELD's D press legs (a FadeDuration above the 2 s config poll: no leg drives one yet -- an open item); the guest's quit
prompt on a duo past the WM_CLOSE fallback (GM0-CUT-QUIT, GM0-QUIT-D: no any-role verb -- an open item, two-PC B32); the s169 rows. The
FadeDuration-300 rows (GM0-KEY-DOUBLE, GM0-FADE's 300 half) run only on a launch whose games read FadeDuration >= 300 (duo.py
`--root-ini Interface.FadeDuration=300`, the runners' ROUND_GM_FADE=300: a hand edit of a root is regenerated away by Instance.ensure at
every duo start), GM0-DOOR-D only on its own `door` launch at FadeDuration >= 800 (ROUND_GM_FADE=800); every press waits out THE HUD-FADE
SETTLE first (coop_guest_menu._ready: one FadeDuration + 100 ms past the pre-init sample, whichever ends later of that many game frames
and that much wall time, S168-DESIGN R4); GM0-OVERLAY's shots are the close shots the leave and cut legs take (READ them).

THE STAND-IN (ff9mapkit/tests/test_coop_guest_menu_duo.py): two fakegame stand-ins (the opt-in `guestmenu` rung) under a stub link -- the
host's lane, flags, intent and caps word onto the guest, a stub blackhole -- run the legs it models: NEW green but STANDIN_UNMODELLED, OLD
on two s167 stand-ins exactly the predicted rows MEASURED, each lever exactly its prediction, each GUEST_MENU_FAULTS fault exactly its
FAULT_REDS rows; every pure judge red on each wrong shape; the T legs' tape facts on synthetic tapes; the recorder's owner gate.

    COOP_GMD_LEG=key py tools/harness/duo.py studies/test-harness/scenarios/coop_guest_menu_duo.py [--bridge-ports H,G]
    COOP_CALIBRATE=1 COOP_GMD_LEG=<leg> [COOP_GMD_LEVER=<lever>]   (OLD on s167; LEVER on s168)
    COOP_GMT_LEG=hole py tools/play.py studies/test-harness/scenarios/coop_guest_menu_duo.py
"""
from __future__ import annotations

import ctypes
import os
import re
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _coop_peer_bench as pb                              # noqa: E402 - the T2 two-role bench helpers
import coop_guest_menu as gm                               # noqa: E402 - the solo bench's readers, moves and judges (imported)

HarnessError = cb.HarnessError
BW = gm.BW


def _env_int(name: str, default: int, lo: int = 1, hi: int = 65535) -> int:
    raw = str(os.environ.get(name, "") or "").strip()
    return int(raw) if raw.isdigit() and lo <= int(raw) <= hi else default


# ================================================================================================ the places, the times
HOME, AWAY = pb.BENCH_FIELD, 30602                   # duo.py's pairing field / LOCKT2 (the -msgs folder)
FARSHORE, WORLD, ICE_CAVERN = 6603, 9011, 300
SCRIBE_FIELD, SCRIBE_AT = gm.GM_FIELD, gm.SCRIBE_AT  # 30801: the scribe (a plain window) west
STRIP_FIELD = _env_int("COOP_GMD_STRIP_FIELD", gm.GM_FIELD)
SCENE, GROUP = pb.BENCH_SCENE, -1
PIN_MAX_AGE_MS = BW.PIN_MAX_AGE_MS                   # 2500
HUDS = BW.GM_HUD_STATES
OPEN_S = gm.OPEN_S
CLOSE_S = gm.CLOSE_S
FOLLOW_S = 30.0          # a host's warp -> the guest landed on its field
WORLD_S = 90.0           # a walk out -> the world (the guest's follow-out included)
LINE_S = (BW.GM_GUEST_LINE_MS + 1500) / 1000.0       # the refusal line's life plus the publish skew
HOLD_S = 2.0             # samples read while seated (GHOST, STSCENE, WALKGHOST)
SHOT_S = 4.0             # a shot of the close line within this of the close (the design's)
STALL_S = 3.0            # the duo's blackhole (GM0-STALL-VIEW, the blip hold)
HOLE_BH_S = STALL_S + 1.5  # the T hole leg's blackhole (GM0-STALL-WHO-T: room past StaleMs + PRESS_PAST_MS for an in-stall press)
RAMP_OLD_AFTER_S = 2.5   # `close old` on the ramp leg: measured no sooner than this after the Enabled=0 write (past the 2 s ini poll)
GRACE_MS = 5000          # the stall leg's guest SessionGraceMs (its clamp floor: the past-grace blackhole stays short)
PAST_GRACE_S = GRACE_MS / 1000.0 + 4.0
RAMP_S = 40.0            # Enabled=0 / the grace -> 'reloading own autosave' and the Autoload's HUD
TITLE_HOLD_S = 4.0       # `close old`: the menu held this long after the host's title (THE CAL RULE's measured hold)
CLOSE_OLD_CANCEL_S = 3.5  # `close old` on the leave leg: the guest's own Cancel this long after the host's warp (DP-AGED)
DOUBLE_GAP_S = 0.1       # GM0-KEY-DOUBLE: the second press 100 ms after the first
FADE_LONG_MS = 300       # the FadeDuration the 300 rows need
#: GM0-DOOR-D's own launch (S168-DESIGN R5): at this FadeDuration the host's control-off lands well inside the guest's Hide fade (at 300 it
#: beat the door by only ~33-96 ms, so a slower relay hop seats the menu), and the follow's commit -- the debug warp's 0.9 s lead-in
#: (Ff9mkDebugMenu.cs:114), then the guest's ~450 ms follow fade -- still lands after the door (around 1.4 s of fade the door reaches it)
FADE_DOOR_MS = 800
STSCENE_S = 2.0          # GM0-STSCENE: the host's own main menu held this long
OUT_LIVE_MS = 1200       # GM0-OUT: the world-out starts at LiveMs >= this (the start line's host-alive ms)
#: GM0-DOOR-D's door verdicts: `scene` (F4) during a host door's control-off lead-in, the likeliest -- the host's control is off and its
#: fade runs for most of a second before the section-4 intent goes out (S168-DESIGN R5); `control` once the follow has armed (DESIGN D1:
#: term 9 precedes term 10 `busy`, a started follow turns control off as it arms); `busy` / `leaving` before it
DOOR_D_WHYS = (BW.GM_WHY_BUSY, BW.GM_WHY_LEAVING, BW.GM_WHY_CONTROL, BW.GM_WHY_SCENE)
SKEW_FRAMES = gm.SKEW_FRAMES
DETAIL_W = 1400
D_BATTLE = os.environ.get("COOP_GMD_BATTLE", "1").strip() != "0"   # 0: the stand-in duo (no diorama model): the cut rows not run
FIGHT_S, RETURN_S = 240.0, 60.0

# ================================================================================================ the legs and rows
DUO_LEGS = ("key", "caps", "world", "leave", "door", "out", "rejoin", "cut", "title", "scene", "chest", "ramp", "rampquit", "stall",
            "dialog", "hudstrip")
T_LEGS = ("hole", "older166", "older167", "tape")
_RAW_DUO = (os.environ.get("COOP_GMD_LEG") or "key").strip().lower()
DUO_LEG = _RAW_DUO if _RAW_DUO in DUO_LEGS else None
_RAW_T = (os.environ.get("COOP_GMT_LEG") or "").strip().lower()
T_LEG = _RAW_T if _RAW_T in T_LEGS else None
LEVER_RAW = (os.environ.get("COOP_GMD_LEVER") or os.environ.get("COOP_GMT_LEVER") or "").strip().lower() or None
T_RAMP = (os.environ.get("COOP_GMT_RAMP") or "field").strip().lower()

DUO_ROWS = {
    "key": ("GM0-KEY", "GM0-SEAT-D", "GM0-CHIP-D", "GM0-FREEZE-D", "GM0-BROWSE-D", "GM0-REFUSE-I1-D", "GM0-LOCAL-D", "GM0-GHOST",
            "GM0-RESTORE-D", "GM0-KEY-DOUBLE"),
    "caps": ("GM0-CAPS-a", "GM0-PAIRED-LINE-F", "GM0-BW"),
    "world": ("GM0-WORLD", "GM0-PAIRED-LINE-W", "GM0-WORLDTAG4-D", "GM0-STSCENE", "GM0-WALKGHOST", "GM0-RAMP-WORLD-D"),
    "leave": ("GM0-LEAVE", "GM0-FADE", "GM0-TIMING"),
    "door": ("GM0-DOOR-D",),
    "out": ("GM0-OUT",),
    "rejoin": ("GM0-REJOIN",),
    "cut": ("GM0-CUT", "GM0-SILENT-D", "GM0-CUT-QUIT"),
    "title": ("GM0-TITLE",),
    "scene": ("GM0-SCENE",),
    "chest": ("GM0-SCENE-CHEST",),
    "ramp": ("GM0-RAMP-CFG-D",),
    "rampquit": ("GM0-QUIT-D",),
    "stall": ("GM0-STALL-VIEW-D", "GM0-PAIRED-LINE-LOST", "GM0-RAMP-FIELD-D"),
    "dialog": ("GM0-DIALOG-PATH-A", "GM0-DIALOG-PATH-B"),
    "hudstrip": ("GM0-HUDSTRIP",),
}
T_ROWS = {
    "hole": ("GM0-HOLE-T", "GM0-STALL-WHO-T"),
    "older166": ("GM0-CAPS-b-166",),
    "older167": ("GM0-CAPS-b-167",),
    "tape": ("GM0-KEY-T", "GM0-FREEZE-T", "GM0-STALL-VIEW-T", "GM0-LEAVE-T", "GM0-CUT-T", "GM0-RAMP-T"),
}
#: the rows a leg reads on OLD and NEW alike (s121's own behaviour, or a MEASURING row): never in an OLD or `old` prediction
SAME_ON_OLD = frozenset(("GM0-STSCENE", "GM0-HUDSTRIP", "GM0-DIALOG-PATH-A", "GM0-DIALOG-PATH-B"))
#: the rows a launch's configuration can leave unrun (out of the verdict, named): FadeDuration >= 300 (GM0-KEY-DOUBLE) / >= FADE_DOOR_MS
#: (GM0-DOOR-D, its own door leg), a battle the stand-in duo cannot fight
FADE_ROWS = frozenset(("GM0-KEY-DOUBLE", "GM0-DOOR-D"))
BATTLE_ROWS = frozenset(("GM0-CUT", "GM0-SILENT-D", "GM0-CUT-QUIT"))

DUO_CHECKS = {
    "GMD-D0": "the pair: both games paired on the leg's field (the guest mirroring), each game's stage read off its probe (s168 both, or "
              "both s167 = OLD), coop_guest_menu.judge_probe green on each s168 game",
    "GM0-KEY": "FieldHUD with a b3 host: `now` guest on the HUD, the press -> MainMenu, menu_refusal.count +0, opens +1, seated, seat.src "
               "'wire', frame_age_ms -1",
    "GM0-SEAT-D": "seat_fp == the HOST's host_fp for players, party, bag and gil (keyitems REPORTED: K1); TWO MARKERS: seat_fp's players "
                  "and party differ from the guest's own fp_before",
    "GM0-CHIP-D": "the chip's words on every seated sample, null after the close",
    "GM0-FREEZE-D": "event_enable false on every seated sample, true after the close (the duo's GM0-FREEZE until the b3 tape exists)",
    "GM0-BROWSE-D": "Item / Ability / Equip / Status open and Cancel back; the greyed rows open nothing (refused +0); no Save row; Alt+F5 "
                    "never opens Serialize; the host's party drawn",
    "GM0-REFUSE-I1-D": "one Item > Use > target confirm: refused +1, captures +1, passes +0, last_site I1, impactful 0, seated, back to the "
                       "root, one census line; fp equal at the close",
    "GM0-LOCAL-D": "a sort on the Item screen (the bar's Arrange: Auto, then Manual -- rows 0 and 2 swap on the seated copy, L0 read back "
                   "at row 2): refused +0, captures +0, seated; the HOST's host_fp bag unchanged; fp equal at the close",
    "GM0-GHOST": "GhostAs=auto: each game's ghost of the other keeps its model and rig on every sample of the open (and as before it)",
    "GM0-RESTORE-D": "every open / close cycle of the leg: fp_after == fp_before, named null, doors +1, nothing seated, the HUD",
    "GM0-KEY-DOUBLE": "FadeDuration >= 300: two presses 100 ms apart -> one open, menu_refusal.count +0, no refusal line",
    "GM0-CAPS-a": "the HOST's `guestmenu caps off`: the guest's press is s121 exactly (audible, count +1, lines +1, FieldHUD, why older, its "
                  "words), ONE caps line on the guest naming 'guest menu'; after `caps on` the press opens",
    "GM0-PAIRED-LINE-F": "the refused press: `session.overlay` 'guest_menu' while the line lives, then the overlay before it",
    "GM0-BW": "the HOST's frame book: b3 -> sec12_len > 0 and type5_len; `caps off` -> the type-5 frame smaller by at least the block; "
              "tx_bps read >= 1 s apart (REPORTED)",
    "GM0-WORLD": "WorldHUD 9011: walking, then frozen (`worldwalk walk off`): each press seated, each close restored; aboard (`vehicle 1`): "
                 "refused 'riding', audible, count +1",
    "GM0-PAIRED-LINE-W": "the riding refusal: 'guest_menu' on the overlay while the line lives, the world chain's line after",
    "GM0-WORLDTAG4-D": "a seated open on 9011, Item and back, the close with no load: outside_settled set / equal / named null, uid0_vars "
                       "and sysvar192 after the settle equal the ones before",
    "GM0-STSCENE": "MEASURING: the host's own main menu 2 s on 9011 -- the guest's lane rx and walk why read on every sample (REPORTED)",
    "GM0-WALKGHOST": "MEASURING: the HOST's ghost of the seated guest sampled while the guest's world menu is open, and a host shot",
    "GM0-RAMP-WORLD-D": "seated on WorldHUD, the duo's blackhole past SessionGraceMs: closes.ending, its door before the fire (end done, or "
                        "clear_point at the exit ramp's fire), the restore line before 'reloading own autosave', no 'should never happen' "
                        "line, fp equal, the HUD with control after",
    "GM0-LEAVE": "the guest in Equip's candidates, the host `warp 30602`: closes.leave +1 (end done, from the sub-screen), the guest lands "
                 "on 30602 with the pin < 2500 ms, its close line, fp equal; a guest shot within 4 s",
    "GM0-FADE": "a second follow close at the ROOT (the host warps back to 250): it lands too, the pin < 2500 ms, fp equal",
    "GM0-TIMING": "MEASURING: close-to-HUD ms (last_close.ms), the pin ages, FadeDuration -- read on both closes",
    "GM0-DOOR-D": "FadeDuration >= 800 (its own launch): Menu, then the host's warp inside the Hide fade: the DOOR refuses scene / control "
                  "/ busy / leaving (`scene` in the host door's control-off lead-in, the likeliest; `control` once the follow has armed), "
                  "nothing seated, events on, the follow lands",
    "GM0-OUT": "the guest seated, the host walks out of 6603: closes.out +1 (end done), the guest lands on 9011, at most one 'waits: the "
               "field HUD is not up' (the request frame's), before the close's end line; the start after the door, its live ms >= 1200",
    "GM0-REJOIN": "both on 9011, the guest seated, the host Confirms into 300: closes.rejoin +1, the guest lands on 300; at most one 'waits: "
                  "the world HUD is not up' (the request frame's), before the close's end line; the arm after the door",
    "GM0-CUT": "the guest in Item, the host's `battle 67 -1`: closes.cut +1 (end done, or clear_point at the boot's scene load after the "
               "door), the host's start-hold report 'booting', the guest's 'diorama LIVE', back on 250 after the fight, fp equal; a guest "
               "shot within 4 s",
    "GM0-SILENT-D": "the guest's diorama: `now` 'silent' on BattleHUD, a press keeps BattleHUD (opens +0), `bmenu mainmenu` refused",
    "GM0-CUT-QUIT": "a second battle (once the host's battle lane is stale on the guest: term 6) with the guest's quit prompt over its "
                    "seated menu (`endbench quit on`, else a WM_CLOSE to the guest's window): the close waits (close_step 'quit'), the "
                    "host's report 'busy' (never 'booting'); the prompt's Cancel lets the close end (done, or clear_point at the boot's "
                    "scene load after the door)",
    "GM0-TITLE": "the guest seated, the host soft-resets: closes.title +1 within CloseCapMs + two fades, end done, its words",
    "GM0-SCENE": "the guest seated, the host talks to the scribe: closes.scene +1 (end done), its words, the talk opens on the guest, no "
                 "'expired before my copy was free'",
    "GM0-SCENE-CHEST": "the guest seated, the host opens ChestA: closes.scene +1 (end done), the guest's 'opening chest' line",
    "GM0-RAMP-CFG-D": "the guest seated at Item, its Enabled=0 written live: closes.ending +1 (end done, or clear_point at the exit ramp's "
                      "fire), the restore line before 'reloading own autosave', the close words, fp equal, the HUD with control after",
    "GM0-QUIT-D": "the guest's quit prompt over its seated menu (`endbench quit on`, else a WM_CLOSE to the guest's window), then "
                  "Enabled=0: the ramp's fire waits it out -- backstops.ramp_quit +1, ramp +0, no 'should never happen' line, no prompt "
                  "and control on after the Autoload",
    "GM0-STALL-VIEW-D": "seated through the duo's 3 s blackhole: seated on every sample, closes +0; Cancel after: fp equal",
    "GM0-PAIRED-LINE-LOST": "a press inside a blackhole's blip hold: refused audibly (count +1), 'guest_menu' on the overlay while it lives",
    "GM0-RAMP-FIELD-D": "seated, a blackhole past SessionGraceMs: closes.ending at the ramp's arm (end done, or clear_point at the exit "
                        "ramp's fire), the restore line before 'reloading own autosave', no 'should never happen' line, fp equal",
    "GM0-DIALOG-PATH-A": "the host's line LOCKED on the guest: a press -- the window stays, netsync.suppress true, count +0, silent +0, "
                         "opens +0",
    "GM0-DIALOG-PATH-B": "`netsync unlock` on the guest, the host's line again: `now` 'dialog', the press keeps the window, count +0, opens +0",
    "GM0-HUDSTRIP": "MEASURING (a Known limit): a persistent kit strip up -- `now` 'dialog', count +0, silent +0, opens +0, no line, the strip "
                    "stays",
}
T_CHECKS = {
    "GM0-HOLE-T": "a world-paired UNMIRRORED guest's press: refused 'not_mirroring' (audible, count +1, its words), never MainMenu",
    "GM0-STALL-WHO-T": "the same guest inside a 3 s blackhole, the lane past StaleMs: still refused, never MainMenu",
    "GM0-CAPS-b-166": "an s166 host (caps 0x0001): the press refused as s121 (audible, count +1, why older, its words), the caps line names "
                      "'guest menu'",
    "GM0-CAPS-b-167": "an s167 host (caps 0x0003): the press refused as s121 (audible, count +1, why older, its words), the caps line names "
                      "'guest menu'",
    "GM0-KEY-T": "the b3 tape's host on 250: the press seats the tape's section 12 (seat.src wire), menu_refusal.count +0",
    "GM0-FREEZE-T": "event_enable false on every seated sample, true after the close",
    "GM0-STALL-VIEW-T": "seated through `--blackhole-at` 3 s: seated on every sample, closes +0; fp equal after",
    "GM0-LEAVE-T": "seated before the tape host's warp to 30602: closes.leave +1, the guest lands on 30602, fp equal",
    "GM0-CUT-T": "seated before the tape's battle: closes.cut +1 (end done, or clear_point at the boot's scene load after the door), "
                 "the diorama boots, fp equal",
    "GM0-RAMP-T": "seated, `--stop-at` then the grace: closes.ending +1, the restore line before 'reloading own autosave', fp equal",
}
T_SETUP = {"T2-TAPE": "the leg's tape reads back and its facts hold (THE INSTRUMENT named when it stands in)",
           "T2-PEER": "the guest config written (its config line); replay-host listening, the guest connected, the replay started",
           "T2-SAVE": "no 'session ended, no autosave to resume -> title screen' line", "T2-INI": "Memoria.ini restored byte-exact"}
GATE = {"S168-GMT-GATE": "the OWNER-GATED COOP_TAPE_GUEST_MENU (coop_tape_record.py's GUEST-MENU variant on an s168 host) exists and its "
                         "eight facts hold -- RED until the owner's recording; never part of a calibration"}

#: the calibration levers per leg (COOP_GMD_LEVER / COOP_GMT_LEVER; unset = the leg's first): every one an ANY-ROLE `guestmenu` op, on the
#: role LEVER_ROLE names (THE DUO CANNOT PULL A SELFTEST-ROLE LEVER)
LEG_LEVERS = {"key": ("old", "capture"), "caps": ("old",), "world": ("old",), "leave": ("old", "closeold"), "door": ("old",),
              "out": ("old", "closeold"),
              "rejoin": ("old", "closeold"), "cut": ("old", "closeold"), "title": ("old", "closeold"), "scene": ("old", "closeold"),
              "chest": ("old", "closeold"), "ramp": ("old", "closeold"), "rampquit": ("old",), "stall": ("old",), "dialog": (),
              "hudstrip": (), "hole": ("old",), "older166": (), "older167": (), "tape": ("old",)}
LEVER_OPS = {"old": ("old",), "capture": ("capture", "off"), "closeold": ("close", "old"), "caps": ("caps", "off")}
LEVER_READ = {"old": ("menu", "old"), "capture": ("capture", "off"), "closeold": ("close", "old"), "caps": ("caps", "off")}
LEVER_ROLE = {"old": "guest", "capture": "guest", "closeold": "guest", "caps": "host"}
_CLOSE_ROWS = {"leave": ("GM0-LEAVE", "GM0-FADE"), "out": ("GM0-OUT",), "rejoin": ("GM0-REJOIN",),
               "cut": ("GM0-CUT", "GM0-CUT-QUIT"), "title": ("GM0-TITLE",), "scene": ("GM0-SCENE",), "chest": ("GM0-SCENE-CHEST",),
               "ramp": ("GM0-RAMP-CFG-D",)}


def leg_rows(leg: str) -> tuple:
    return DUO_ROWS.get(leg) or T_ROWS.get(leg) or ()


def old_predicted(leg: str) -> tuple:
    """OLD (PURE): every row of the leg but the ones s167 reads the same (SAME_ON_OLD)."""
    return tuple(r for r in leg_rows(leg) if r not in SAME_ON_OLD)


#: each (leg, lever) -> the rows it turns red, each MEASURING its shape (MEASURE)
LEVER_PREDICTED = {
    **{(leg, "old"): old_predicted(leg) for leg in LEG_LEVERS if "old" in LEG_LEVERS[leg]},
    ("key", "capture"): ("GM0-REFUSE-I1-D",),
    **{(leg, "closeold"): rows for leg, rows in _CLOSE_ROWS.items()},
}
MEASURE = {
    "old": "a MIRRORING guest's press refused as s121: `now` audible on the HUD, menu_refusal.count +1, the menu never opens (on the T legs "
           "the unmirrored guest's OWN menu opens)",
    "capture": "the census passed the confirm: refused +0, passes +1",
    "closeold": "no forced close: the trigger came and the menu stayed seated (closes +0)",
}
#: the stand-in's faults (fakegame.GUEST_MENU_FAULTS) -> the duo / T rows each turns red, by leg (pinned by the tests on the stand-in)
FAULT_REDS = {
    "key": {"capture_leak": ("GM0-REFUSE-I1-D",), "own_values": ("GM0-SEAT-D", "GM0-BROWSE-D"), "restore_skip": ("GM0-RESTORE-D",)},
    # without term 3 an older host still refuses -- term 7 (no_data: the host sends no section 12) -- never the older words or caps line
    "caps": {"caps_ignored": ("GM0-CAPS-a",)},
    "leave": {"leave_ignored": ("GM0-LEAVE", "GM0-FADE")},
    "title": {"title_ignored": ("GM0-TITLE",)},
}


def lever_of(leg: str, raw):
    """The calibration lever for ``leg``: ``raw`` when it is one of the leg's, the leg's first when ``raw`` is None; else None."""
    levers = LEG_LEVERS.get(leg, ())
    if raw is None:
        return levers[0] if levers else None
    return raw if raw in levers else None


def duo_catalog(leg: str, calibrate: bool = False) -> dict:
    c = {"GMD-D0": DUO_CHECKS["GMD-D0"]}
    c.update({r: DUO_CHECKS[r] for r in DUO_ROWS[leg]})
    if calibrate:
        c["S168D-CAL"] = gm.CAL_TEXT
    return c


def t_catalog(leg: str, calibrate: bool = False) -> dict:
    c = dict(T_SETUP)
    c.update({r: T_CHECKS[r] for r in T_ROWS[leg]})
    if leg == "tape":
        c.update(GATE)
    if calibrate:
        c["S168T-CAL"] = gm.CAL_TEXT
    return c


# ================================================================================================ the pure readers
_gm, _mr, _n, _d, snap, HUD_OF = gm._gm, gm._mr, gm._n, gm._d, gm.snap, gm._hud


def stage_new(st) -> bool:
    return cb.has(st, gm.PROBE)


def overlay(st):
    return cb.path(st, "netsync.session.overlay")


def suppress(st):
    return cb.path(st, "netsync.suppress")


def swap_pin_age(st):
    v = cb.path(st, "netsync.swap.pin.last_use_age_ms")
    return int(v) if isinstance(v, (int, float)) else None


def host_fp_comps(st) -> dict:
    return dict(((_gm(st).get("host_fp") or {}).get("components")) or {})


def ghost_rig(st):
    """A game's ghost of the other: (model, rig) off `netsync.dress.ghost` (None when unpublished)."""
    gh = cb.path(st, "netsync.dress.ghost")
    return (gh.get("model"), gh.get("rig")) if isinstance(gh, dict) else None


def boot_name(st):
    return cb.path(st, "netsync.battle.host.start_hold.guest.boot_name")


def frame_book(st) -> dict:
    return dict(_gm(st).get("frame") or {})


#: the world-out start line's live ms: the engine's '; live on the world map for N ms)' (NetSyncClient.cs:9068-9070), or the kit twin's
#: older ', N ms host-alive)' (battlewire.log_world_out_start)
_RX_HOST_ALIVE = re.compile(r"world follow-out: start .*?(?:, (\d+) ms host-alive\)|; live on the world map for (\d+) ms\))")


# ================================================================================================ the pure judges
def judge_d0(hs, gs, field: int) -> tuple:
    """GMD-D0 (PURE): both on ``field`` (FieldHUD), the guest mirroring, the stages read (both s168, or both s167 = OLD), each s168 probe
    green."""
    both = hs is not None and gs is not None and hs.field_id == field and gs.field_id == field and hs.ui_state == "FieldHUD" \
        and gs.ui_state == "FieldHUD" and cb.path(gs, "netsync.session.mirroring") is True
    nh, ng = stage_new(hs) if hs is not None else False, stage_new(gs) if gs is not None else False
    probes = [gm.judge_probe(x) for x in (hs, gs)] if nh and ng else []
    ok = both and nh == ng and all(p[0] for p in probes)
    return ok, (f"host {getattr(hs, 'ui_state', None)} {getattr(hs, 'field_id', None)} (s{168 if nh else 167}); guest "
                f"{getattr(gs, 'ui_state', None)} {getattr(gs, 'field_id', None)} (s{168 if ng else 167}), mirroring "
                f"{cb.path(gs, 'netsync.session.mirroring') if gs is not None else None!r}; probes "
                f"{[p[1][:160] for p in probes] or 'OLD (no guestmenu key)'}")


def judge_key(pre: dict, s: dict) -> tuple:
    """GM0-KEY (PURE): ``pre`` the HUD sample before the press, ``s`` after it."""
    now = pre.get("mr", {}).get("now")
    seat = _n(s, "seat", default={}) or {}
    count = int(s.get("mr", {}).get("count", 0) or 0) - int(pre.get("mr", {}).get("count", 0) or 0)
    ok = (now == "guest" and s.get("ui") == "MainMenu" and count == 0 and _d(pre, s, "opens") == 1 and bool(_n(s, "seated", default=False))
          and seat.get("src") == BW.GM_SEAT_SRC_WIRE and int(seat.get("frame_age_ms", 0)) == -1)
    return ok, (f"now {now!r} on the HUD; after the press ui {s.get('ui')!r}, menu_refusal.count +{count}, opens +{_d(pre, s, 'opens')}, "
                f"seated {_n(s, 'seated', default=None)!r}, seat {seat}")


def key_old_measured(pre: dict, s: dict) -> bool:
    """OLD's / `old`'s shape on a MIRRORING guest (PURE): s121's audible refusal -- `now` audible, count +1, the menu never opened."""
    count = int(s.get("mr", {}).get("count", 0) or 0) - int(pre.get("mr", {}).get("count", 0) or 0)
    return pre.get("mr", {}).get("now") == "audible" and count == 1 and s.get("ui") in HUDS and not _n(s, "seated", default=False)


def judge_seat_d(s: dict, host_comps: dict) -> tuple:
    """GM0-SEAT-D (PURE): ``s`` seated, ``host_comps`` the HOST's host_fp components."""
    seat = dict(_n(s, "seat_fp", "components", default=None) or {})
    wire = ("players", "party", "bag", "gil")
    diff = [c for c in wire if seat.get(c) is None or seat.get(c) != host_comps.get(c)]
    drawn = gm.seat_drawn(s)
    ok = bool(_n(s, "seated", default=False)) and bool(host_comps) and not diff and drawn
    return ok, (f"seat_fp vs the host's host_fp: differ on {diff or 'none'} (seat {seat or None}, host {host_comps or None}); keyitems "
                f"{'equal' if seat.get('keyitems') == host_comps.get('keyitems') else 'DIFFER'} (REPORTED: K1); TWO MARKERS (the host's "
                f"players / party drawn, not the guest's own) {drawn}")


def swap_measured_d(rec: dict) -> bool:
    """(PURE) GM0-LOCAL-D's measured order change -- coop_guest_menu._manual_swap's record: two different labels read (l0 under the
    cursor, l2 two rows on) and, after the swap, the cursor's row (JumpToIndex) reads l0 (``swapped``). The solo bench's own rule
    (coop_guest_menu.swap_measured) when it has one, so S and D judge one shape."""
    rule = getattr(gm, "swap_measured", None)
    if callable(rule):
        return bool(rule(rec))
    l0, l2 = rec.get("l0"), rec.get("l2")
    r0, r2 = rec.get("row0"), rec.get("row2")
    return (bool(l0) and bool(l2) and l0 != l2 and rec.get("swapped") == l0
            and bool(r0) and bool(r2) and r0 != r2 and rec.get("swapped_row") == r2)


def judge_local_d(rec: dict, host_bag0, host_bag1, closed: dict) -> tuple:
    """GM0-LOCAL-D (PURE): ``rec`` {reached, why, what, before, after, manual_label, l0, l2, swapped, trail} -- DESIGN D5: the GUEST's
    MEASURED manual swap (rows 0 and 2 swap on the seated copy: swap_measured_d), refused +0, captures +0, still seated -- and the HOST's
    host_fp bag before / after unchanged (the sort never forwarded), fp equal at the close."""
    trail = f" [trail: {str(rec.get('trail'))[:400]}]" if rec.get("trail") else ""
    if not rec.get("reached"):
        return False, f"not reached: {rec.get('why')}{trail}"
    a, b = rec["before"], rec["after"]
    swapped = swap_measured_d(rec)
    fp_ok = bool((_n(closed, "fp", default={}) or {}).get("equal"))
    ok = (_d(a, b, "refused", "count") == 0 and _d(a, b, "captures") == 0 and bool(_n(b, "seated", default=False))
          and host_bag0 is not None and host_bag0 == host_bag1 and fp_ok and swapped)
    return ok, (f"{rec.get('what')}: the manual swap {rec.get('l0')!r} <-> {rec.get('l2')!r} (Manual row {rec.get('manual_label')!r}), "
                f"the cursor's row after it {rec.get('swapped')!r}: measured {swapped}; refused +{_d(a, b, 'refused', 'count')} captures "
                f"+{_d(a, b, 'captures')}, seated {_n(b, 'seated', default=None)!r}; the HOST's bag {host_bag0} -> {host_bag1}; at the "
                f"close fp equal {fp_ok}{trail}")


def judge_ghost(before, samples) -> tuple:
    """GM0-GHOST (PURE): ``before`` (host's, guest's) ghost before the open, ``samples`` [(host's, guest's)] while seated."""
    shown = before is not None and all(x is not None and x[0] is not None and int(x[0]) >= 0 for x in before)
    if not samples or not shown:
        return False, f"not reached: no ghost on both games (before {before}, {len(samples or [])} samples: GhostAs=auto on both roots?)"
    flips = [s for s in samples if s != before]
    return not flips, f"before {before}; {len(samples)} seated samples, changed on {flips[:3] or 'none'}"


def judge_key_double(pre: dict, s: dict, lines) -> tuple:
    """GM0-KEY-DOUBLE (PURE): two presses inside one FadeDuration-300 fade."""
    count = int(s.get("mr", {}).get("count", 0) or 0) - int(pre.get("mr", {}).get("count", 0) or 0)
    line = (_n(s, "line", default={}) or {}).get("text")
    ok = _d(pre, s, "opens") == 1 and count == 0 and line is None and bool(_n(s, "seated", default=False))
    return ok, f"opens +{_d(pre, s, 'opens')}, menu_refusal.count +{count}, line {line!r}, seated {_n(s, 'seated', default=None)!r}"


def judge_caps_a(pre: dict, s: dict, lines, after_on: dict, own: int, peer: int) -> tuple:
    """GM0-CAPS-a (PURE): ``pre`` / ``s`` around the press under the host's `caps off`, ``lines`` the guest's since the lever, ``after_on``
    the press after `caps on` (seated)."""
    mr0, mr1 = pre.get("mr", {}), s.get("mr", {})
    count = int(mr1.get("count", 0) or 0) - int(mr0.get("count", 0) or 0)
    nlines = int(mr1.get("lines", 0) or 0) - int(mr0.get("lines", 0) or 0)
    words = (_n(s, "line", default={}) or {}).get("text")
    want_caps = BW.ww_caps_line_text(own, peer)
    caps_lines = sum(1 for ln in lines if want_caps in ln and "guest menu" in ln)
    ok = (count == 1 and nlines == 1 and s.get("ui") in HUDS and _n(s, "why", default=None) == BW.GM_WHY_OLDER
          and words == BW.gm_refusal_line_rule(BW.GM_WHY_OLDER) and caps_lines == 1 and not _n(s, "seated", default=True)
          and bool(_n(after_on, "seated", default=False)))
    return ok, (f"under caps off: count +{count}, lines +{nlines}, ui {s.get('ui')!r}, why {_n(s, 'why', default=None)!r}, words {words!r}, "
                f"caps lines naming 'guest menu' {caps_lines} (want 1: {want_caps!r}); after `caps on` seated "
                f"{_n(after_on, 'seated', default=None)!r}")


PAIRED_LINE_NEED = 3     # GM0-PAIRED-LINE-F / -W: at least this many line-live samples past the first (SKEW), every one 'guest_menu'


def line_live(line) -> bool:
    """(PURE) The guest's refusal line LIVE on a sample: its words set and 0 <= age < GM_GUEST_LINE_MS (`netsync.guestmenu.line`)."""
    if not isinstance(line, dict) or not line.get("text"):
        return False
    age = line.get("age")
    return isinstance(age, (int, float)) and 0 <= age < BW.GM_GUEST_LINE_MS


def judge_paired_line(prior, live: list, after) -> tuple:
    """GM0-PAIRED-LINE-x (PURE): ``prior`` the overlay before the press, ``live`` one (overlay, `netsync.guestmenu.line`) per sample from the
    press on, ``after`` the overlay once the line is gone. Judged on the samples where the line LIVES (line_live), the first of them dropped
    (THE ORDER SKEW: the overlay is set on the next Update): at least PAIRED_LINE_NEED of them, EVERY one 'guest_menu' -- a state-29 line
    that flickers or falls back to OvlOff early is red, not only one never shown -- and the prior overlay after."""
    lived = [o for o, ln in live if line_live(ln)][1:]
    on = [o for o in lived if o == BW.OVERLAY_NAME_GUEST_MENU]
    ok = (len(lived) >= PAIRED_LINE_NEED and len(on) == len(lived) and after != BW.OVERLAY_NAME_GUEST_MENU and after == prior)
    return ok, (f"prior {prior!r}; while the line lived {len(on)} of {len(lived)} samples 'guest_menu' ({sorted(set(map(str, lived)))}; "
                f"want every one, >= {PAIRED_LINE_NEED}, the first line-live sample dropped: SKEW; {len(live)} sampled); after {after!r}")


def judge_bw(on: dict, off: dict, bps_on, bps_off) -> tuple:
    """GM0-BW (PURE): the HOST's frame book with b3 (``on``) and under `caps off` (``off``)."""
    s12, t5, t5_off = int(on.get("sec12_len", -1)), int(on.get("type5_len", -1)), int(off.get("type5_len", -1))
    shrink = t5 - t5_off if t5 > 0 and t5_off > 0 else None
    ok = s12 > 0 and t5 > 0 and shrink is not None and shrink >= s12 and int(off.get("sec12_len", -1)) <= 0
    return ok, (f"b3: type5_len {t5}, sec12_len {s12}, tx_bps {bps_on}; caps off: type5_len {t5_off}, sec12_len {off.get('sec12_len')}, "
                f"tx_bps {bps_off}; the frame shrank {shrink} B (want >= the block's {s12} B)")


def judge_world(walk: tuple, frozen: tuple, ride: tuple, *, frozen_why=None) -> tuple:
    """GM0-WORLD (PURE): (seated snap, closed snap) for the walking and the frozen open, (pre, s) for the riding refusal. ``frozen_why``
    set = the guest was never shown FROZEN (`worldwalk walk off` refused, or walk.lever never read 'off' with walk.free false): the frozen
    half 'not reached' -- never a second walking cycle passing as the frozen one."""
    why = []
    if frozen_why is not None:
        why.append(f"frozen: not reached ({frozen_why})")
    for name, (s, closed) in (("walking", walk), ("frozen", frozen)):
        if name == "frozen" and frozen_why is not None:
            continue
        ok_r = gm.restore_ok(s, closed)[0] if s is not None and closed is not None else False
        if s is None or not _n(s, "seated", default=False) or s.get("ui") != "MainMenu" or not ok_r:
            why.append(f"{name}: seated {_n(s or {}, 'seated', default=None)!r}, restored {ok_r}")
    pre, s = ride
    if pre is None or s is None:
        why.append("aboard: not reached")
    else:
        count = int(s.get("mr", {}).get("count", 0) or 0) - int(pre.get("mr", {}).get("count", 0) or 0)
        if not (_n(s, "why", default=None) == BW.GM_WHY_RIDING and count == 1 and not _n(s, "seated", default=True) and s.get("ui") == "WorldHUD"):
            why.append(f"aboard: why {_n(s, 'why', default=None)!r}, count +{count}, ui {s.get('ui')!r}")
    return not why, "; ".join(why) or "walking and frozen seated and restored; aboard refused 'riding' audibly"


def judge_measuring(samples: list, what: str, need: int = 3) -> tuple:
    """A MEASURING row (PURE): green once measured (at least ``need`` samples); the reading is the detail."""
    return len(samples) >= need, f"{len(samples)} sample(s) {what}" + ("" if len(samples) >= need else " -- NOT measured")


def close_words_want(cause: str):
    """(PURE) The forced close's words for ``cause`` (the twins: CloseLineRule over the cause's index)."""
    return BW.gm_close_line_rule(BW.gm_cause_index_rule(cause))


def judge_close(cause: str, base: dict, s: dict, *, words=None, want_from=None, landed: bool = True, extra_ok: bool = True,
                extra: str = "", ends=("done",)) -> tuple:
    """A real trigger's forced close (PURE): closes.<cause> +1, last_close {cause, end in ``ends`` (done; a judge whose close can end at
    a decision-16 clear point -- the boot's scene load, the exit ramp's fire -- also passes 'clear_point' and pins its form itself)[,
    from]}, the close WORDS (``words``: the close_line text stamped AT the close -- _CloseWatch; it lives GM_GUEST_LINE_MS, gone long
    before a follow lands -- equal to the cause's CloseLineRule line), fp equal, nothing seated, the follow / the scene ``landed``."""
    lc = _n(s, "last_close", default={}) or {}
    fp = _n(s, "fp", default={}) or {}
    want = close_words_want(cause)
    ok = (_d(base, s, "closes", cause) == 1 and lc.get("cause") == cause and lc.get("end") in tuple(ends)
          and (want_from is None or lc.get("from") == want_from) and bool(fp.get("equal")) and not _n(s, "seated", default=True)
          and words is not None and words == want and landed and extra_ok)
    return ok, (f"closes.{cause} +{_d(base, s, 'closes', cause)}, last_close {lc} (from want {want_from or 'any'}), close words {words!r} "
                f"at the close (want {want!r}), fp equal {fp.get('equal')!r} named {fp.get('named')!r}, seated "
                f"{_n(s, 'seated', default=None)!r}, landed {landed}" + (f"; {extra}" if extra else ""))


def close_old_measured(cause: str, base: dict, s: dict) -> bool:
    """`close old`'s shape (PURE): the trigger came, no close counted, still seated."""
    return _d(base, s, "closes", cause) == 0 and bool(_n(s, "seated", default=False))


def ramp_old_measured(base: dict, last, elapsed: float) -> bool:
    """`close old` on the ramp leg (PURE): ``last`` the last sample before the ramp's reload line, ``elapsed`` its seconds after the
    Enabled=0 write -- the shape counts only past the 2 s ini poll (RAMP_OLD_AFTER_S), when ApplyConfigChange has run: no ending close,
    still seated. A sample at the write's own instant reads the same on ANY build."""
    return last is not None and elapsed >= RAMP_OLD_AFTER_S and close_old_measured("ending", base, last)


def judge_leave(base: dict, s: dict, pin, landed: bool, shot, words=None) -> tuple:
    ok, why = judge_close("leave", base, s, words=words, want_from=base.get("ui"), landed=landed,
                          extra_ok=pin is not None and 0 <= pin <= PIN_MAX_AGE_MS,
                          extra=f"pin age {pin} ms (want <= {PIN_MAX_AGE_MS}: PinUseRule ages a pin only OVER it); shot {shot}")
    return ok, why


def judge_fade(cycles: list) -> tuple:
    """GM0-FADE (PURE): ``cycles`` [(depth, base, s, pin, landed)]: every follow close counted, landed, with a fresh pin."""
    rows = [(d, _d(b, s, "closes", "leave"), pin, landed) for d, b, s, pin, landed in cycles]
    bad = [d for d, n, pin, landed in rows if not (n == 1 and landed and pin is not None and 0 <= pin <= PIN_MAX_AGE_MS)]
    shown = [f"{d}: closes.leave +{n}, pin {pin}, landed {landed}" for d, n, pin, landed in rows]
    return (len(cycles) >= 2 and not bad), f"{shown}; failed at {bad or 'none'}"


def _at(lines, needle: str) -> list:
    """(PURE) The indices of ``lines`` holding ``needle``."""
    return [i for i, ln in enumerate(lines) if needle in ln]


def judge_out(base: dict, s: dict, landed: bool, lines, words=None) -> tuple:
    """GM0-OUT (PURE), decision 18: WorldOutTick REQUESTS the `out` close, then WorldOutStep refuses at its FieldHud term in the same call
    -- one 'the field HUD is not up' wait (latched once per host b6 visit and reason; two-PC B10), logged before the close's end line. The
    start after the door's restore (no move lane passes its HUD term before it), its 'live on the world map for N ms' >= OUT_LIVE_MS."""
    hud = _at(lines, BW.log_world_out_waits("the field HUD is not up"))
    end = _at(lines, BW.LOG_GM_FORCED_CLOSE + "out)")
    door = _at(lines, BW.LOG_GM_RESTORED + "the door")
    starts = [(i, int(m.group(1) or m.group(2))) for i, m in ((i, _RX_HOST_ALIVE.search(ln)) for i, ln in enumerate(lines)) if m]
    alive = starts[0][1] if starts else None
    order = (bool(end) and bool(door) and bool(starts) and starts[0][0] > door[0] and len(hud) <= 1 and all(i < end[0] for i in hud))
    return judge_close("out", base, s, words=words, landed=landed, extra_ok=order and alive is not None and alive >= OUT_LIVE_MS,
                       extra=f"'the field HUD is not up' waits {len(hud)} at {hud[:2]} (want <= 1, before the close's end at {end[:1]}); "
                             f"the start at {[i for i, _a in starts][:1]} (want after the door at {door[:1]}), host-alive ms "
                             f"{alive if alive is not None else 'no start line'} (want >= {OUT_LIVE_MS})")


def judge_rejoin(base: dict, s: dict, landed: bool, lines, words=None) -> tuple:
    """GM0-REJOIN (PURE), decision 18: WorldFollowFire requests the close, then WorldArmWhy refuses that call at its first gate (the world
    HUD) -- one wait, logged before the close's end line (two-PC B11); the arm ('rejoining the peer at field') after the door's restore."""
    hud = _at(lines, "waits: the world HUD is not up")
    end = _at(lines, BW.LOG_GM_FORCED_CLOSE + "rejoin)")
    door = _at(lines, BW.LOG_GM_RESTORED + "the door")
    arm = _at(lines, "rejoining the peer at field")
    order = bool(end) and bool(door) and bool(arm) and arm[0] > door[0] and len(hud) <= 1 and all(i < end[0] for i in hud)
    return judge_close("rejoin", base, s, words=words, landed=landed, extra_ok=order,
                       extra=f"'the world HUD is not up' waits {len(hud)} at {hud[:2]} (want <= 1, before the close's end at {end[:1]}); "
                             f"the arm at {arm[:1]} (want after the door at {door[:1]})")


def cut_end_ok(lc_end, lines) -> bool:
    """(PURE) A cut close's end: `done`, or a `clear_point` whose end line says '(a scene load)' with the door's restore before 'diorama
    BOOT' (the boot's scene load ends the record first: UIManager.OnLevelWasLoaded, before CeScene could)."""
    endl = [ln for ln in lines if BW.LOG_GM_FORCED_CLOSE + "cut)" in ln]
    door = _at(lines, BW.LOG_GM_RESTORED + "the door")
    boot = _at(lines, "diorama BOOT")
    return lc_end == "done" or (lc_end == "clear_point" and any("(a scene load)" in ln for ln in endl) and bool(door) and bool(boot)
                                and door[0] < boot[0])


def judge_cut(base: dict, s: dict, report, live_lines: int, landed: bool, words=None, lines=()) -> tuple:
    """GM0-CUT (PURE), decision 18: the boot fires on its first HUD frame (DioramaTick's UI gate reads the state only), so a FIELD cut's
    record ends at the boot's scene load (decision 16: `clear_point`, '(a scene load)' -- OnLevelWasLoaded ends it first, so CeScene can
    never win at a load), with the door's restore BEFORE 'diorama BOOT'; a WORLD cut ends `done` (WorldHUD.Show turns events on at once)."""
    lc_end = (_n(s, "last_close", default={}) or {}).get("end")
    end_ok = cut_end_ok(lc_end, lines)
    return judge_close("cut", base, s, words=words, landed=landed, ends=("done", "clear_point"),
                       extra_ok=end_ok and report == BW.BOOT_NAMES[BW.BOOT_BOOTING] and live_lines >= 1,
                       extra=f"end {lc_end!r} (done, or the boot's scene load after the door: {end_ok}); the host's start-hold report "
                             f"{report!r} (want 'booting'), 'diorama LIVE' lines {live_lines}")


def judge_silent(now, ui_after, opens_delta: int, bmenu_ok: bool, booted: bool) -> tuple:
    if not booted:
        return False, "not reached: the guest's diorama never booted"
    ok = now == "silent" and ui_after == "BattleHUD" and opens_delta == 0 and not bmenu_ok
    return ok, f"now {now!r} on BattleHUD; after the press ui {ui_after!r}, opens +{opens_delta}; `bmenu mainmenu` accepted {bmenu_ok}"


def judge_cut_quit(waiting: list, report, s_after: dict, base: dict, lines=()) -> tuple:
    """GM0-CUT-QUIT (PURE): the prompt held the cut close (close_step 'quit', seated, the host's report 'busy' and never 'booting'), then
    the prompt's Cancel let it end -- `done`, or on this FIELD the boot's scene load (cut_end_ok, as GM0-CUT). ``report`` is every report
    the window saw, in order (a lone name reads as one): 'busy' seen and 'booting' never (S168-DESIGN R1)."""
    held = bool(waiting) and all(_n(w, "close_step", default=None) == "quit" and _n(w, "seated", default=False) for w in waiting)
    lc = _n(s_after, "last_close", default={}) or {}
    end_ok = cut_end_ok(lc.get("end"), lines)
    seen = [] if report is None else [report] if isinstance(report, str) else [r for r in report if r is not None]
    rep_ok = BW.BOOT_NAMES[BW.BOOT_BUSY] in seen and BW.BOOT_NAMES[BW.BOOT_BOOTING] not in seen
    ok = held and rep_ok and _d(base, s_after, "closes", "cut") == 1 and end_ok
    names = sorted(set(seen), key=seen.index)
    return ok, (f"{len(waiting)} samples under the prompt, close_step quit and seated on all {held}; the host's reports {names} (want "
                f"'busy', never 'booting'); after the prompt's Cancel closes.cut +{_d(base, s_after, 'closes', 'cut')}, end "
                f"{lc.get('end')!r} (done, or the boot's scene load after the door: {end_ok})")


def judge_title(base: dict, s: dict, fade_ms, words=None) -> tuple:
    lc = _n(s, "last_close", default={}) or {}
    budget = BW.GM_CLOSE_CAP_MS + 2 * int(fade_ms or 40)
    return judge_close("title", base, s, words=words, extra_ok=0 <= int(lc.get("ms", -1)) <= budget, extra=f"ms {lc.get('ms')} (budget {budget})")


def title_old_measured(base: dict, held: list, s: dict) -> bool:
    """`close old` on the title leg (PURE): closes.title +0, seated on every held sample, then the own Cancel restored at the door."""
    return (bool(held) and all(_n(h, "seated", default=False) for h in held) and _d(base, s, "closes", "title") == 0
            and _d(base, s, "restore", "doors") == 1 and bool((_n(s, "fp", default={}) or {}).get("equal")))


def judge_scene(base: dict, s: dict, played: bool, lines, *, chest: bool = False, words=None) -> tuple:
    expired = sum(1 for ln in lines if "expired before my copy was free" in ln)
    chest_line = sum(1 for ln in lines if "chest relay: opening chest" in ln)
    extra_ok = (chest_line >= 1) if chest else (played and expired == 0)
    return judge_close("scene", base, s, words=words, extra_ok=extra_ok, extra=(f"'opening chest' lines {chest_line}" if chest else
                                                                     f"the talk opened on the guest {played}; expired lines {expired}"))


def judge_ramp(cause_base: dict, s: dict, lines, *, ui_ok: bool, words=None) -> tuple:
    """GM0-RAMP-CFG-D / GM0-RAMP-FIELD-D / GM0-RAMP-WORLD-D / GM0-RAMP-T (PURE): the ending close, the restore line before the ramp's, no
    alarm. Decision 16: the record ends `clear_point` at the ramp's fire -- the ramp block runs before the close tick (NetSyncClient.cs
    :3421 before :3528), so the fire beats step 5 (the HUD's events) on a field and on the world map alike -- its end line 'ended at a
    clear point ... (the exit ramp's fire)'; `done` passes too (B16)."""
    restored = [i for i, ln in enumerate(lines) if BW.LOG_GM_RESTORED in ln]
    ramp = [i for i, ln in enumerate(lines) if "session ended -> reloading own autosave" in ln]
    alarm = sum(1 for ln in lines if "(should never happen)" in ln and "guest menu" in ln)
    order = bool(restored) and bool(ramp) and restored[0] < ramp[0]
    lc_end = (_n(s, "last_close", default={}) or {}).get("end")
    fire = [ln for ln in lines if BW.LOG_GM_FORCED_CLOSE + "ending)" in ln]
    end_ok = lc_end == "done" or (lc_end == "clear_point" and any("ended at a clear point" in ln and "the exit ramp's fire" in ln
                                                                  for ln in fire))
    return judge_close("ending", cause_base, s, words=words, ends=("done", "clear_point"), extra_ok=order and alarm == 0 and ui_ok and end_ok,
                       extra=f"the restore line before the ramp's {order} (restore at {restored[:1]}, ramp at {ramp[:1]}), alarm lines {alarm}, "
                             f"the HUD with control after {ui_ok}, end {lc_end!r} (done, or a clear point at the exit ramp's fire: {end_ok})")


def judge_quit_d(base: dict, s: dict, lines, prompt_after: bool) -> tuple:
    bs0 = _n(base, "restore", "backstops", default={}) or {}
    bs1 = _n(s, "restore", "backstops", default={}) or {}
    rq = int(bs1.get("ramp_quit", 0)) - int(bs0.get("ramp_quit", 0))
    rp = int(bs1.get("ramp", 0)) - int(bs0.get("ramp", 0))
    alarm = sum(1 for ln in lines if "(should never happen)" in ln)
    ok = rq == 1 and rp == 0 and alarm == 0 and not prompt_after and s.get("ui") in HUDS and s.get("control")
    return ok, (f"backstops.ramp_quit +{rq} ramp +{rp}, alarm lines {alarm}; after the Autoload the prompt {prompt_after}, ui "
                f"{s.get('ui')!r}, control {s.get('control')}")


def stale_read(st) -> bool:
    """(PURE) The link read STALE on a raw state: `netsync.session.peer_alive` false (HarnessAgent: IsConnected && GetRemote().Valid --
    the lane past StaleMs)."""
    return cb.path(st, "netsync.session.peer_alive") is False


def judge_stall_view(base: dict, during: list, after: dict, closed: dict, stale: int) -> tuple:
    """GM0-STALL-VIEW-D / -T (PURE): ``during`` the snaps sampled while the blackhole held, ``stale`` how many of those samples' RAW states
    read the link stale (stale_read). THE STALL WITNESS: at least one -- a blackhole that buffered instead of stalling (or a window that
    missed it) exercised nothing, and the row's mutant (close on peer death) fires only on a stale peer."""
    if stale < 1:
        return False, (f"not reached: the blackhole never staled the link (peer_alive never false on {len(during)} stall samples)")
    seated = [d for d in during if _n(d, "seated", default=False)]
    closes = sum(_d(base, after, "closes", c) for c in BW.GM_CLOSE_IDS)
    ok = bool(during) and len(seated) == len(during) and closes == 0 and bool(_n(after, "seated", default=False)) \
        and gm.restore_ok(after, closed)[0]
    return ok, (f"{len(seated)} of {len(during)} stall samples seated ({stale} read the link stale), closes +{closes}, seated after "
                f"{_n(after, 'seated', default=None)!r}; the Cancel: {gm.restore_ok(after, closed)[2]}")


def judge_lost_line(pre: dict, s: dict, live: list) -> tuple:
    """GM0-PAIRED-LINE-LOST (PURE): ``live`` one (overlay, held) per sample, ``held`` = the blackhole had not ended when the read returned.
    The row is the HOLD's (NetSyncClient's blip-grace branch, SetOverlayOffOrGuestLine: state 29 in place of OvlOff), so only a held
    sample counts -- once the link is back the live paired branch draws 29 for the line's rest, and a hold left at OvlOff would pass there."""
    count = int(s.get("mr", {}).get("count", 0) or 0) - int(pre.get("mr", {}).get("count", 0) or 0)
    held = [o for o, h in live if h]
    on = [o for o in held if o == BW.OVERLAY_NAME_GUEST_MENU]
    later = [o for o, h in live if not h and o == BW.OVERLAY_NAME_GUEST_MENU]
    ok = count == 1 and not _n(s, "seated", default=True) and len(on) >= 1
    return ok, (f"count +{count}, why {_n(s, 'why', default=None)!r}, seated {_n(s, 'seated', default=None)!r}, 'guest_menu' on {len(on)} "
                f"of {len(held)} held samples ({sorted(set(map(str, held)))}; +{len(later)} once the link was back, not judged)")


def judge_dialog_a(pre: dict, s: dict, sup_after, window_before: bool) -> tuple:
    if not window_before:
        return False, "not reached: no host line on the guest at the press"
    mr0, mr1 = pre.get("mr", {}), s.get("mr", {})
    dc = int(mr1.get("count", 0) or 0) - int(mr0.get("count", 0) or 0)
    ds = int(mr1.get("silent", 0) or 0) - int(mr0.get("silent", 0) or 0)
    ok = bool(s.get("dialog")) and sup_after is True and dc == 0 and ds == 0 and _d(pre, s, "opens") == 0 and s.get("ui") not in BW.GM_MENU_STATES
    return ok, f"the window {s.get('dialog')}, suppress {sup_after!r}, count +{dc}, silent +{ds}, opens +{_d(pre, s, 'opens')}, ui {s.get('ui')!r}"


def judge_dialog_b(pre: dict, s: dict, sup_before, window_before: bool) -> tuple:
    if not window_before:
        return False, "not reached: no host line on the guest at the press"
    now = pre.get("mr", {}).get("now")
    dc = int(s.get("mr", {}).get("count", 0) or 0) - int(pre.get("mr", {}).get("count", 0) or 0)
    ok = now == "dialog" and sup_before is not True and bool(s.get("dialog")) and dc == 0 and _d(pre, s, "opens") == 0 \
        and s.get("ui") not in BW.GM_MENU_STATES
    return ok, f"now {now!r}, suppress before {sup_before!r}; the window after {s.get('dialog')}, count +{dc}, opens +{_d(pre, s, 'opens')}"


def judge_hudstrip(pre: dict, s: dict, window_before: bool) -> tuple:
    if not window_before:
        return False, "not reached: no strip window up on the field (dialog_open false)"
    mr0, mr1 = pre.get("mr", {}), s.get("mr", {})
    dc = int(mr1.get("count", 0) or 0) - int(mr0.get("count", 0) or 0)
    ds = int(mr1.get("silent", 0) or 0) - int(mr0.get("silent", 0) or 0)
    line = (_n(s, "line", default={}) or {}).get("text")
    ok = mr0.get("now") == "dialog" and dc == 0 and ds == 0 and _d(pre, s, "opens") == 0 and line is None and bool(s.get("dialog"))
    return ok, f"now {mr0.get('now')!r}, count +{dc}, silent +{ds}, opens +{_d(pre, s, 'opens')}, line {line!r}, the strip after {s.get('dialog')}"


def judge_refused(want_whys, pre: dict, s: dict, *, world: bool = False) -> tuple:
    """A T leg's refused press (PURE): one of ``want_whys``, audible (count +1), its words, never MainMenu."""
    count = int(s.get("mr", {}).get("count", 0) or 0) - int(pre.get("mr", {}).get("count", 0) or 0)
    why = _n(s, "why", default=None)
    words = (_n(s, "line", default={}) or {}).get("text")
    ok = (pre.get("mr", {}).get("now") == "audible" and why in want_whys and count == 1 and words in {BW.gm_refusal_line_rule(w) for w in want_whys}
          and not _n(s, "seated", default=True) and s.get("ui") != "MainMenu")
    return ok, (f"now {pre.get('mr', {}).get('now')!r}, why {why!r} (want {list(want_whys)}), count +{count}, words {words!r}, ui "
                f"{s.get('ui')!r}, seated {_n(s, 'seated', default=None)!r}")


def judge_stall_who(want_whys, pre: dict, s: dict, stalled: bool, age) -> tuple:
    """GM0-STALL-WHO-T (PURE): the refused press is the row only when the press landed INSIDE the stall (``stalled``: the pre-press raw
    state's lane past StaleMs + PRESS_PAST_MS, ``age`` its arrival_age_ms) -- outside a stall the stall_open mutant refuses
    `not_mirroring` exactly as NEW does, so a press that missed the stall cannot tell them apart."""
    if not stalled:
        return False, f"not reached: the press missed the stall (lane age {age} ms)"
    ok, why = judge_refused(want_whys, pre, s, world=True)
    return ok, f"inside the stall (lane age {age} ms): {why}"


def own_menu_measured(s: dict) -> bool:
    """OLD's shape on an UNMIRRORED guest (PURE): its own menu opened (MainMenu, unseated)."""
    return s.get("ui") == "MainMenu" and not _n(s, "seated", default=False)


def judge_caps_b(pre: dict, s: dict, lines, own: int, peer: int) -> tuple:
    count = int(s.get("mr", {}).get("count", 0) or 0) - int(pre.get("mr", {}).get("count", 0) or 0)
    want = BW.ww_caps_line_text(own, peer)
    caps = sum(1 for ln in lines if want in ln and "guest menu" in ln)
    ok = (count == 1 and pre.get("mr", {}).get("now") == "audible" and _n(s, "why", default=None) == BW.GM_WHY_OLDER
          and (_n(s, "line", default={}) or {}).get("text") == BW.gm_refusal_line_rule(BW.GM_WHY_OLDER) and caps >= 1
          and s.get("ui") in HUDS)
    return ok, (f"now {pre.get('mr', {}).get('now')!r}, count +{count}, why {_n(s, 'why', default=None)!r}, ui {s.get('ui')!r}; caps lines "
                f"naming 'guest menu' {caps} ({want!r})")


def caps_b_old_measured(pre: dict, s: dict, lines, peer: int) -> bool:
    """OLD (s167 guest, PURE): refused as s121 and the s167 caps line -- naming 'world fingerprint' against an s166 host, none against s167."""
    count = int(s.get("mr", {}).get("count", 0) or 0) - int(pre.get("mr", {}).get("count", 0) or 0)
    fp = sum(1 for ln in lines if "lacks my world fingerprint" in ln)
    return count == 1 and s.get("ui") in HUDS and ((fp >= 1) if peer == BW.CAPS_S166 else (fp == 0))


def judge_freeze_t(seated: list, closed: dict) -> tuple:
    return gm.judge_freeze(seated, closed)


def judge_cal(failed, predicted, measured: dict, needs) -> tuple:
    return gm.judge_cal(failed, predicted, measured, needs)


def cal_verdict(new: bool, lever, pulled, failed, pred, measured: dict, needs, skip=()) -> tuple:
    """S168D-CAL / S168T-CAL (PURE): judge_cal -- but never green on an s168 launch whose requested lever was NOT pulled (refused, or never
    read back: nothing calibrated, and LEVER_PREDICTED of None is empty), nor on one whose lever's every predicted row a configuration left
    unrun. Gated on ``new``: on OLD the leg's default lever is never sent (s167 has no `guestmenu`), so its absence is no red."""
    if new and lever in LEVER_OPS and pulled is None:
        return False, (f"the calibration lever `guestmenu {' '.join(LEVER_OPS[lever])}` was not pulled (refused or never read back) -- "
                       f"nothing calibrated")
    if new and pulled and not pred:
        return False, f"nothing calibrated: every predicted row unrun (configuration: {sorted(skip) or 'none'})"
    return judge_cal(failed, pred, measured, needs)


# ================================================================================================ the duo's moves
def _gmop(g, ctx: dict, *args) -> tuple:
    """`netsync guestmenu <args>` on ``g`` -- never to a game without `netsync.guestmenu` (OLD): (ok, why)."""
    if not stage_new(g.state):
        return False, f"`guestmenu {' '.join(map(str, args))}` not sent (no `netsync.guestmenu`: an engine before s168)"
    ok, why = cb.try_ns(g, "guestmenu", *[str(a) for a in args])
    g.wait_frames(SKEW_FRAMES)
    if ok:
        ctx.setdefault("sent", set()).add(id(g))
    return ok, why


#: this launch's FadeDuration (the guest's ini, read once in _d0): THE HUD-FADE SETTLE's length for every press (S168-DESIGN R4)
LAUNCH_FADE = {"ms": None}


def _gctx(g) -> dict:
    """coop_guest_menu's ctx shape for its moves (THE PRE-INIT SAMPLE reads `new`; its HUD-FADE SETTLE reads `fade_ms`)."""
    return {"new": stage_new(g.state), "measured": {}, "fade_ms": LAUNCH_FADE["ms"]}


def ready(g, *, world: bool = False, timeout: float = CLOSE_S):
    return gm._ready(g, _gctx(g), world=world, timeout=timeout)


def open_seated(g, *, world: bool = False) -> tuple:
    """THE PRE-INIT SAMPLE, then a Menu press: (outcome, pre snap, after snap)."""
    st = ready(g, world=world)
    if st is None and world:
        # a FROZEN world guest (`worldwalk walk off`) may read no control: the HUD with no fade is its pre-init sample
        st = poll(g, lambda s: s.ui_state == "WorldHUD" and not getattr(s, "fading", False), 3.0, "WorldHUD, no fade (a frozen guest)")
    pre = snap(st or g.state)
    if st is None:
        return "not_ready", pre, pre
    out, s = gm.press_menu(g, _gctx(g), world=world)
    return out, pre, s


def close_out(g, *, world: bool = False) -> dict:
    return gm.cancel_out(g, _gctx(g), world=world)


def poll(g, pred, timeout: float, what: str):
    return cb.poll(g, pred, timeout, what)


def watch_snaps(g, seconds: float) -> list:
    return [snap(st) for st in cb.hold_for(g, seconds)]


def wait_field(g, field: int, timeout: float = FOLLOW_S):
    return poll(g, lambda s: s.ui_state == "FieldHUD" and s.field_id == field and s.control, timeout, f"FieldHUD {field} with control")


def wait_settled(g, timeout: float = CLOSE_S) -> dict:
    """After a forced close: the HUD with events back on (or the deadline): the snap."""
    st = poll(g, lambda s: s.ui_state in HUDS and not _gm(s).get("seated") and not _gm(s).get("close_pending"), timeout,
              "the forced close ended") or g.state
    return snap(st)


def shot_note(d, g, name: str):
    path, why = cb.shot(g, name)
    d.note(f"{name}: {path or 'no shot (' + why + ')'} -- READ it")
    return path


class _CloseWatch(threading.Thread):
    """THE CLOSE WORDS, stamped AT the close: samples ``g`` (state reads only -- the main thread may drive the OTHER game's blocking trigger,
    a walk out, meanwhile) every 50 ms from the trigger on, and keeps the close line's text at the first sample where closes.<cause>
    reads +1 over ``base`` with the line live. The line lives GM_GUEST_LINE_MS (4 s): read after a follow lands it is long gone, so a
    judge reading the words off the settled snap would see none. ``stop()`` -> the words (None: never seen)."""

    def __init__(self, g, base: dict, cause: str, seconds: float):
        super().__init__(daemon=True)
        self.g, self.base, self.cause, self.until = g, base, cause, time.time() + float(seconds)
        self.words, self.halt, self.found = None, threading.Event(), threading.Event()

    def run(self) -> None:
        while not self.halt.is_set() and time.time() < self.until and self.words is None:
            try:
                x = self.g.state
            except Exception:                              # noqa: BLE001 - a dead channel: the main thread reports it
                return
            if _d(self.base, snap(x), "closes", self.cause) >= 1:
                self.words = (_gm(x).get("close_line") or {}).get("text") or None
                if self.words is not None:
                    self.found.set()
            time.sleep(0.05)

    def stop(self, grace: float = 0.5):
        """The words; ``grace`` lets a sample already in flight land (the main thread's own wait may have seen the close first)."""
        if self.is_alive():
            self.found.wait(grace)
        self.halt.set()
        self.join(2.0)
        return self.words


def close_watch(g, base: dict, cause: str, seconds: float) -> _CloseWatch:
    w = _CloseWatch(g, base, cause, seconds)
    w.start()
    return w


class _Blackhole(threading.Thread):
    """THE DUO'S BLACKHOLE: the HOST's netsync_bridge process SUSPENDED for ``seconds`` (NtSuspendProcess / NtResumeProcess: both directions
    go silent, the TCP connections stay open) and ALWAYS resumed (the finally). Our own child process only; topology `bridge` only."""

    def __init__(self, pid: int, seconds: float):
        super().__init__(daemon=False)
        self.pid, self.seconds, self.error, self.done = int(pid), float(seconds), None, threading.Event()

    def run(self) -> None:
        k32, nt = ctypes.windll.kernel32, ctypes.windll.ntdll       # noqa: F821 -- Windows-only, as duo.py is
        h = k32.OpenProcess(0x0800, False, self.pid)                  # PROCESS_SUSPEND_RESUME
        if not h:
            self.error = f"OpenProcess({self.pid}) failed"
            self.done.set()
            return
        try:
            nt.NtSuspendProcess(h)
            time.sleep(self.seconds)
        finally:
            nt.NtResumeProcess(h)
            k32.CloseHandle(h)
            self.done.set()


def blackhole(d, seconds: float):
    """Start the duo's blackhole: the stub duo's own seam (``d.blackhole``) or the host bridge's suspension. -> (handle, why); the handle's
    ``done`` Event is set when the link is back."""
    seam = getattr(d, "blackhole", None)
    if callable(seam):
        return seam(seconds), "the stub duo's blackhole"
    b = (getattr(d, "bridges", None) or {}).get("host")
    pid = getattr(getattr(b, "proc", None), "pid", None)
    if pid is None or os.name != "nt":
        return None, "no host bridge process to suspend (topology relay, or not Windows): the duo's blackhole needs `--topology bridge`"
    bh = _Blackhole(pid, seconds)
    bh.start()
    return bh, f"the host's bridge (pid {pid}) suspended {seconds:g} s"


# ================================================================================================ the duo
def _seed_host_to(field: int):
    """PAIR's host_setup for a leg paired on ``field``: the HOST's party seeded through COOPPARTY, so the seat is a SECOND MARKER the
    guest's own party is not. duo.py runs host_setup RIGHT AFTER the host's New Game, while the game stands on field 70 (the New-Game
    override, no player control), so the seeder must warp on to the LEG's field, never to ``g.state.field_id``: the OLD run of
    2026-11-07 lost nine duo legs at setup to exactly that (the warp back to 70 waited 60 s for control that never comes)."""
    def seed(g) -> str:
        return cb.seed_party(g, back_to=field)
    seed.field = field
    return seed


def _chest_setup(g) -> str:
    import coop_chest_relay_duo as crd                      # beside this file: the chest relay duo's recipe
    return crd._setup(g)


def _pair_of(leg) -> dict:
    """The leg's PAIR (duo.py calls d.pair(**PAIR))."""
    extra_host = {"GhostAs": "auto"} if leg == "key" else {}
    extra_guest = {"GhostAs": "auto"} if leg == "key" else {"SessionGraceMs": str(GRACE_MS)} if leg in ("stall", "world") else {}
    if leg == "world":
        return {"field": FARSHORE, "host_setup": _seed_host_to(FARSHORE), "role_extra": {"host": {}, "guest": extra_guest}}
    if leg in ("out", "rejoin"):
        return {"field": FARSHORE, "host_setup": _seed_host_to(FARSHORE)}
    if leg in ("scene", "dialog"):
        return {"field": SCRIBE_FIELD, "host_setup": _seed_host_to(SCRIBE_FIELD)}
    if leg == "hudstrip":
        return {"field": STRIP_FIELD}
    if leg == "chest":
        import coop_chest_relay as cr
        return {"field": cr.FIELD, "host_setup": _chest_setup, "guest_setup": _chest_setup}
    pair = {"field": HOME, "host_setup": _seed_host_to(HOME)}
    if extra_host or extra_guest:
        pair["role_extra"] = {"host": extra_host, "guest": extra_guest}
    return pair


PAIR = _pair_of(DUO_LEG) if DUO_LEG else {"field": HOME}


def run_duo(d) -> None:
    """One duo leg (COOP_GMD_LEG): every row recorded (strict off); COOP_CALIBRATE=1 judges S168D-CAL by the GUEST's stage (OLD) or the
    lever."""
    leg = DUO_LEG
    calibrate = cb.CALIBRATE
    strict, d.strict = d.strict, False
    if leg is None:
        d.check(False, f"S168D-LEG: COOP_GMD_LEG={_RAW_DUO!r} names one of {DUO_LEGS}", "nothing was run past the pairing", cid="S168D-LEG")
        d.strict = strict
        return
    lever = lever_of(leg, LEVER_RAW) if calibrate else None
    if calibrate and LEVER_RAW is not None and lever is None:
        d.check(False, f"S168D-CAL: COOP_GMD_LEVER={LEVER_RAW!r} is not leg {leg!r}'s ({LEG_LEVERS[leg] or 'none'})", "nothing was edited",
                cid="S168D-CAL")
        d.strict = strict
        return
    cat = duo_catalog(leg, calibrate)
    failed, done = [], set()
    ctx = {"leg": leg, "lever": lever, "pulled": None, "measured": {}, "new": False, "fade_ms": None, "config_skip": set(), "sent": set()}

    def check(cid, ok, detail):
        if cid in done:
            return
        done.add(cid)
        if not ok:
            failed.append(cid)
        d.check(bool(ok), f"{cid}: {cat.get(cid, cid)}", str(detail)[:DETAIL_W], cid=cid)

    def rest(why):
        for cid in DUO_ROWS[leg]:
            if cid not in done:
                check(cid, False, f"not reached: {why}"[:DETAIL_W])

    try:
        if _d0(d, check, ctx):
            FNS[leg](d, check, rest, ctx)
    except HarnessError as err:
        d.note(f"the {leg} leg raised: {str(err)[:400]}")
        rest(f"the leg raised ({str(err)[:200]})")
    finally:
        rest("the leg ended before this row")
        for who, g in (("host", d.host), ("guest", d.guest)):
            if id(g) in ctx["sent"]:
                try:
                    ok, why = cb.try_ns(g, "guestmenu", "clear")
                    d.note(f"`guestmenu clear` on the {who}: {'ok' if ok else why[:120]}")
                except HarnessError:
                    pass
        if calibrate:
            skip = set(ctx["config_skip"])
            pred = old_predicted(leg) if not ctx["new"] else LEVER_PREDICTED.get((leg, ctx["pulled"]), ())
            pred = tuple(r for r in pred if r not in skip)
            needs = pred                                  # THE CAL RULE on OLD too: each predicted red MEASURED (OLD is unrepeatable)
            ok, why = cal_verdict(ctx["new"], ctx["lever"], ctx["pulled"], set(failed) - skip, pred, ctx["measured"], needs, skip)
            d.check(ok, "S168D-CAL: CALIBRATION -- exactly the predicted duo rows red (OLD by the guest's stage, else the lever's)",
                    f"{'s168' if ctx['new'] else 'OLD (s167)'}, lever {ctx['pulled']!r}: {why}; not run (configuration): "
                    f"{sorted(skip) or 'none'}", cid="S168D-CAL")
        d.strict = strict


def _not_run(check, ctx: dict, rows, why: str) -> None:
    """Rows a launch's configuration leaves unrun: recorded red with the reason, out of the calibration (named)."""
    for r in rows:
        ctx["config_skip"].add(r)
        check(r, False, f"not run (configuration): {why}")


def _quit_unreachable(check, ctx: dict, rows, why: str) -> None:
    """The guest's quit prompt is raised by `endbench quit on`, a SELFTEST-ROLE lever (NetSyncEnd.HarnessEndBench refuses any other role):
    THE DUO CANNOT PULL A SELFTEST-ROLE LEVER. Its fallback, a WM_CLOSE posted to the guest's window (_raise_quit_prompt), keeps the
    'needs the selftest role' words when it too raised nothing -- the rows are then recorded unrun, out of the calibration, until an
    any-role quit-prompt drive is proven (an open item; its two-PC route is B32); any OTHER refusal is a plain red."""
    if "needs the selftest role" in str(why):
        _not_run(check, ctx, rows, f"no any-role quit-prompt verb: `endbench quit on` is the selftest role's ({str(why)[:120]})")
        return
    for r in rows:
        check(r, False, f"not reached: `endbench quit on` refused ({str(why)[:160]})")


def _harness_instance():
    """tools/harness/instance.py (the driver puts tools/ on sys.path; a direct import adds it)."""
    try:
        from harness import instance as hinst
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
        from harness import instance as hinst
    return hinst


def _post_close(d, role: str = "guest") -> tuple:
    """WM_CLOSE (0x0010) posted to ``role``'s game windows -- instance.post_close over the duo's own pid (no focus, no keys: THE UNATTENDED
    LAW): -> (windows posted, how). 0 when the duo carries no pid for the role (the stub duo) or no post_close exists."""
    pid = (getattr(d, "pids", None) or {}).get(role)
    if not pid:
        return 0, f"no {role} pid on this duo"
    fn = getattr((getattr(d, "instances", None) or {}).get(role), "post_close", None)   # Instance.post_close: a method or a static
    if fn is None:
        try:
            hinst = _harness_instance()
        except ImportError as err:
            return 0, f"no tools/harness/instance.py ({err})"
        fn = getattr(hinst, "post_close", None) or getattr(getattr(hinst, "Instance", None), "post_close", None)
    if fn is None:
        return 0, "no instance.post_close (tools/harness/instance.py)"
    try:
        n = int(fn(int(pid)) or 0)
    except (OSError, AttributeError, TypeError, ValueError) as err:
        return 0, f"post_close({pid}) raised: {err}"
    return n, f"WM_CLOSE posted to {n} window(s) of the {role}'s pid {pid}"


def _raise_quit_prompt(d, g) -> tuple:
    """The guest's stock quit prompt over its seated menu: `endbench quit on` (the selftest role's) -- else, on its 'needs the selftest
    role' refusal (a duo guest is role client), a WM_CLOSE posted to the guest's own window: UIKeyTrigger.OnApplicationQuit cancels the
    quit and opens the same stock prompt BenchQuitPrompt does (UIKeyTrigger.cs:412-418; Unity 5.2.3 honours CancelQuit). Grounded in
    source and PROVEN in game (the 2026-11-08 reruns: rampquit and cut each raised it on a client). -> (ok, why, how): how 'endbench' |
    'wm_close' | None. NEVER Confirm while the prompt is up -- its Yes quits the game."""
    okq, whyq = cb.try_ns(g, "endbench", "quit", "on")
    if okq:
        return True, "", "endbench"
    if "needs the selftest role" not in str(whyq):
        return False, whyq, None
    n, how = _post_close(d, "guest")
    if not n:
        return False, whyq, None                          # the refusal's own words: the named 'not run' (no fallback on this duo)
    up = poll(g, lambda s: cb.quit_prompt_up(s), 3.0, "the quit prompt (WM_CLOSE)") is not None
    if up:
        return True, how, "wm_close"
    return False, (f"neither `endbench quit on` (needs the selftest role) nor a window close request ({how}) raised the prompt"), None


def _lower_quit_prompt(g, how) -> None:
    """Take the prompt down the way it went up: `endbench quit off`, or -- the WM_CLOSE prompt is the stock QuitUI -- a Cancel (never
    Confirm). A no-op when the prompt is already gone."""
    if how == "endbench":
        cb.try_ns(g, "endbench", "quit", "off")
    elif how == "wm_close" and cb.quit_prompt_up(g.state):
        g.press("cancel")
        g.wait_frames(SKEW_FRAMES)


def _measure(ctx: dict, rows, shape: bool) -> None:
    for r in rows if isinstance(rows, (tuple, list)) else (rows,):
        ctx["measured"][r] = ctx["measured"].get(r, False) or bool(shape)


def _d0(d, check, ctx: dict) -> bool:
    host, guest = d.host, d.guest
    field = PAIR.get("field", HOME)
    gs = poll(guest, lambda s: s.ui_state == "FieldHUD" and s.field_id == field and cb.path(s, "netsync.session.mirroring") is True,
              20.0, "the guest mirroring on the pairing field") or guest.state
    hs = host.state
    ok, why = judge_d0(hs, gs, field)
    check("GMD-D0", ok, why)
    ctx["new"] = stage_new(gs)
    fade = cb.ini_value(guest, "Interface", "FadeDuration")
    ctx["fade_ms"] = int(fade) if fade is not None and str(fade).strip().isdigit() else None
    LAUNCH_FADE["ms"] = ctx["fade_ms"]
    d.note(f"the guest reads s{168 if ctx['new'] else 167}; FadeDuration {ctx['fade_ms']!r} ms (each press settles "
           f"{gm.settle_frames(ctx['fade_ms'])} frames and at least {gm.settle_ms(ctx['fade_ms'])} ms past the pre-init sample)")
    paired = gs.field_id == field and gs.ui_state == "FieldHUD" and cb.path(gs, "netsync.session.mirroring") is True
    if not paired or stage_new(hs) != stage_new(gs):
        return False                                     # (a probe-shape red alone still runs the leg: its own row is red)
    if ctx["new"] and ctx["lever"] in LEVER_OPS:
        role = LEVER_ROLE[ctx["lever"]]
        g = host if role == "host" else guest
        okl, whyl = _gmop(g, ctx, *LEVER_OPS[ctx["lever"]])
        field_name, word = LEVER_READ[ctx["lever"]]
        st = poll(g, lambda s: (_gm(s).get("lever") or {}).get(field_name) == word, 3.0, "the lever read back") or g.state
        ctx["pulled"] = ctx["lever"] if okl and (_gm(st).get("lever") or {}).get(field_name) == word else None
        d.note(f"CALIBRATION `guestmenu {' '.join(LEVER_OPS[ctx['lever']])}` on the {role}: "
               f"{'pulled (held through the leg)' if ctx['pulled'] else 'REFUSED: ' + whyl}")
    return True


def _old_gate(d, check, rest, ctx: dict, *, world: bool = False) -> bool:
    """OLD (s167) or `old`: MEASURE the mirroring guest's s121 refusal once, then every non-SAME row reads 'not reached' (OLD) -- or, under
    `old`, the leg's rows still run (each red by its judge) and the shape is the measure. True = run the leg's rows."""
    if ctx["new"] and ctx["pulled"] != "old":
        return True
    out, pre, s = open_seated(d.guest, world=world)
    shape = key_old_measured(pre, s)
    if s.get("ui") in BW.GM_MENU_STATES:
        close_out(d.guest, world=world)
    _measure(ctx, old_predicted(ctx["leg"]), shape)
    d.note(f"s121's shape on the mirroring guest: now {pre.get('mr', {}).get('now')!r}, the press {out} (ui {s.get('ui')!r}): "
           f"{'MEASURED' if shape else 'NOT measured'}")
    if not ctx["new"]:
        rest(f"OLD: no `netsync.guestmenu` -- an engine before s168 (nothing sent); s121's refusal {'measured' if shape else 'NOT measured'}")
        return False
    return True


# ---- key
TWEEN_FRAMES = 30        # an NGUI sub-menu tween holds UIScene.Loading: a key pressed inside it is swallowed (the solo bench's)


def _where(g) -> tuple:
    """(menu_group, menu_label) right now: one entry of the sort's trail."""
    st = g.state
    return getattr(st, "menu_group", None), getattr(st, "menu_label", None)


def _local_sort_d(g) -> dict:
    """GM0-LOCAL-D's drive, from the Item screen (DESIGN D5: judged by the MANUAL swap -- Auto stays pressed and unmeasured, a no-op on a
    bag already in order -- so no host-side seeder): Item opens ON its list (Item.Item), so one Cancel puts the group on the rail
    (Item.SubMenu; any other group is named, never Cancelled blind: a Cancel on the rail leaves the screen); the rail's Arrange (every
    s168 bar is HORIZONTAL: right, then down) into Item.ArrangeMenu, Auto; Arrange again, the dialog's SECOND row (Manual: ItemUI.cs
    :299-306, mode 2 = sibling index 1; its label recorded), Confirm -- then coop_guest_menu._manual_swap, the solo bench's measured
    sort: l0 and l2 read, rows 0 and 2 swapped on the seated copy, the cursor's row read back (``swapped``). -> the rec judge_local_d
    reads; ``why`` names the first step that did not run (with every pick's `seen` list)."""
    whys = []
    rec = {"reached": False, "why": "", "what": "sort (Arrange: Auto, then Manual)", "before": snap(g.state), "trail": [_where(g)]}

    def stop(why: str) -> dict:
        rec["why"] = why + (f" ({'; '.join(whys)})" if whys else "")
        rec["after"] = snap(g.state)
        rec["trail"].append(_where(g))
        return rec

    def arrange(what: str) -> bool:
        if not gm._pick(g, "Arrange", directions=("right", "down"), why=whys):
            return False
        if gm._group(g, "Item.ArrangeMenu", what) is None:
            return False
        g.wait_frames(TWEEN_FRAMES)
        rec["trail"].append(_where(g))
        return True
    if gm._group(g, "Item.Item", "the Item screen's list (Item opens ON it)") is not None:
        g.press("cancel")
    if gm._group(g, "Item.SubMenu", "the Item rail (a Cancel off the list)") is None:
        return stop(f"no Item.SubMenu (the rail) after the Item screen opened (read {_where(g)})")
    rec["trail"].append(_where(g))
    if not arrange("the arrange dialog"):
        return stop(f"no Item.ArrangeMenu by the rail's Arrange (read {_where(g)})")
    if not gm._pick(g, "Auto", directions=("down", "right"), why=whys):      # pressed, never measured: no census, still seated
        return stop(f"no 'Auto' in the arrange dialog (read {_where(g)})")
    rec["auto_rail"] = gm._group(g, "Item.SubMenu", "the rail after Auto (ItemUI.cs:289-296)") is not None
    g.wait_frames(TWEEN_FRAMES)
    rec["auto_seated"] = bool(_gm(g.state).get("seated"))
    rec["trail"].append(_where(g))
    if not arrange("the arrange dialog, again"):
        return stop(f"no Item.ArrangeMenu by the rail's Arrange after Auto (read {_where(g)})")
    if not gm._pick(g, "Auto", confirm=False, directions=("down", "up"), why=whys):   # the first row, wherever the dialog opened
        return stop(f"no 'Auto' row to start the second-row walk from (read {_where(g)})")
    g.press("down")
    st = cb.poll(g, lambda s: getattr(s, "menu_label", None) not in (None, "", "Auto"), gm.SEL_S, "the arrange dialog's second row")
    rec["manual_label"] = getattr(g.state, "menu_label", None)
    if st is None:
        return stop(f"the arrange dialog's second row never read (label {rec['manual_label']!r})")
    g.press("confirm")
    swap = getattr(gm, "_manual_swap", None)
    if not callable(swap):
        return stop("no coop_guest_menu._manual_swap (the solo bench's measured sort) to spend")
    swap(g, rec)
    g.wait_frames(SKEW_FRAMES)
    rec["after"] = snap(g.state)
    rec["reached"] = not rec.get("swap_why")
    rec["why"] = rec.get("swap_why") or ""
    return rec


def _leg_key(d, check, rest, ctx: dict) -> None:
    host, guest = d.host, d.guest
    if not _old_gate(d, check, rest, ctx):
        return
    cycles = []
    gh0 = (ghost_rig(host.state), ghost_rig(guest.state))
    at = cb.mark(guest)
    out, pre, s = open_seated(guest)
    check("GM0-KEY", *judge_key(pre, s))
    if out != "seated":
        rest(f"the press did not seat ({out}: ui {s.get('ui')!r}, why {_n(s, 'why', default=None)!r})")
        return
    held = []
    for _ in range(int(HOLD_S / 0.2)):
        held.append((ghost_rig(host.state), ghost_rig(guest.state)))
        time.sleep(0.2)
    check("GM0-SEAT-D", *judge_seat_d(snap(guest.state), host_fp_comps(host.state)))
    check("GM0-GHOST", *judge_ghost(gh0, held))
    open_samples = [s] + watch_snaps(guest, gm.HOLD_S)
    labels = gm.root_labels(guest)
    visits = []
    for label in gm.SUB_SCREENS:
        gm._back_to_root(guest)
        state, why = gm.goto_screen(guest, label)
        seated = bool(_gm(guest.state).get("seated"))
        back = gm._back_to_root(guest) if state else False
        visits.append({"label": label, "found": state is not None, "state": state, "back": back, "seated": seated, "why": why})
    greys = [gm._grey(guest, lb) for lb in BW.GM_GREYED_SUB_MENUS if lb in labels]
    save = gm._savemenu_try(guest)
    closed = close_out(guest)
    cycles.append((pre, closed))
    check("GM0-CHIP-D", *gm.judge_chip(open_samples, closed))
    check("GM0-FREEZE-D", *gm.judge_freeze(open_samples, closed))
    check("GM0-BROWSE-D", *gm.judge_browse(visits, greys, labels, save, s))
    # the census spot check (I1) and the local sort, one more open
    out2, pre2, s2 = open_seated(guest)
    if out2 == "seated":
        rec = gm.drive_site(guest, _gctx(guest), "I1")
        hb0 = host_fp_comps(host.state).get("bag")
        gm._back_to_root(guest)
        state, _why = gm.goto_screen(guest, "Item")
        lrec = {"reached": False, "why": f"no Item screen ({_why})", "what": "sort"}
        if state is not None:
            lrec = _local_sort_d(guest)
        hb1 = host_fp_comps(host.state).get("bag")
        closed2 = close_out(guest)
        cycles.append((pre2, closed2))
        check("GM0-REFUSE-I1-D", *gm.judge_site("I1", rec, closed2, cb.new(guest, at)))
        if ctx["pulled"] == "capture":
            _measure(ctx, "GM0-REFUSE-I1-D", gm.capture_off_measured(rec))
        check("GM0-LOCAL-D", *judge_local_d(lrec, hb0, hb1, closed2))
    else:
        check("GM0-REFUSE-I1-D", False, f"not reached: the second press did not seat ({out2})")
        check("GM0-LOCAL-D", False, f"not reached: the second press did not seat ({out2})")
    check("GM0-RESTORE-D", *gm.judge_restore(cycles))
    if (ctx["fade_ms"] or 40) < FADE_LONG_MS:
        _not_run(check, ctx, ("GM0-KEY-DOUBLE",), f"FadeDuration {ctx['fade_ms']!r} < {FADE_LONG_MS} (this launch's)")
        return
    st = ready(guest)
    pre3 = snap(st or guest.state)
    guest.press("menu")
    time.sleep(DOUBLE_GAP_S)
    guest.press("menu")
    s3 = snap(poll(guest, lambda x: x.ui_state == "MainMenu", OPEN_S, "MainMenu") or guest.state)
    gm._skew(guest)
    s3 = snap(guest.state)
    check("GM0-KEY-DOUBLE", *judge_key_double(pre3, s3, cb.new(guest, at)))
    if s3.get("ui") in BW.GM_MENU_STATES:
        close_out(guest)


# ---- caps
def _leg_caps(d, check, rest, ctx: dict) -> None:
    host, guest = d.host, d.guest
    if not _old_gate(d, check, rest, ctx):
        return
    on = frame_book(poll(host, lambda s: int(frame_book(s).get("sec12_len", -1)) > 0, 5.0, "the host's section 12 built") or host.state)
    time.sleep(1.1)                                                   # tx_bps: windows of at least 1000 ms between reads
    bps_on = frame_book(host.state).get("tx_bps")
    at = cb.mark(guest)
    _gmop(host, ctx, "caps", "off")
    guest_caps = poll(guest, lambda s: int((_gm(s).get("caps") or {}).get("peer", -1)) == BW.CAPS_S167, 5.0, "the guest reads 0x0003")
    off = frame_book(poll(host, lambda s: int(frame_book(s).get("sec12_len", 0)) <= 0, 5.0, "section 12 dropped") or host.state)
    time.sleep(1.1)
    bps_off = frame_book(host.state).get("tx_bps")
    check("GM0-BW", *judge_bw(on, off, bps_on, bps_off))
    st = ready(guest)
    prior = overlay(st or guest.state)
    pre = snap(st or guest.state)
    guest.press("menu")
    live = []
    end = time.time() + LINE_S
    s = None
    while time.time() < end:
        x = guest.state
        live.append((overlay(x), dict(_gm(x).get("line") or {})))
        if s is None and int(_mr(x).get("count", 0) or 0) > int(pre["mr"].get("count", 0) or 0):
            gm._skew(guest)
            s = snap(guest.state)
        time.sleep(0.2)
    s = s or snap(guest.state)
    after = overlay(poll(guest, lambda x: overlay(x) != BW.OVERLAY_NAME_GUEST_MENU, 3.0, "the line gone") or guest.state)
    lines = cb.new(guest, at)
    _gmop(host, ctx, "caps", "on")
    poll(guest, lambda x: int((_gm(x).get("caps") or {}).get("peer", -1)) == BW.CAPS_S168, 5.0, "the guest reads 0x000B again")
    out2, _pre2, s2 = open_seated(guest)
    if s2.get("ui") in BW.GM_MENU_STATES:
        close_out(guest)
    own = int((_gm(guest_caps or guest.state).get("caps") or {}).get("own", BW.CAPS_S168))
    check("GM0-CAPS-a", *judge_caps_a(pre, s, lines, s2, own, BW.CAPS_S167))
    check("GM0-PAIRED-LINE-F", *judge_paired_line(prior, live, after))


# ---- world
def _walk_out_both(d) -> tuple:
    """The host walks out of 6603 (coop_world_wait.walk_out, the proven route); the guest follows out: (ok, why)."""
    import coop_world_wait as cw
    host, guest = d.host, d.guest
    try:
        host.no_encounters(True)
    except (HarnessError, AttributeError):
        pass
    ok, why, _st = cw.walk_out(host)
    if not ok:
        return False, f"the host's walk out failed: {why[:200]}"
    st = poll(guest, lambda s: s.ui_state == "WorldHUD" and s.world_id == WORLD and cb.path(s, "world.block_ready") is True, WORLD_S,
              "the guest on the world map")
    return st is not None, ("both on 9011" if st is not None else f"the guest never followed out (ui {guest.state.ui_state!r})")


def _leg_world(d, check, rest, ctx: dict) -> None:
    host, guest = d.host, d.guest
    ok, why = _walk_out_both(d)
    if not ok:
        rest(why)
        return
    # GM0-STSCENE (MEASURING: OLD and NEW): the host's own main menu, the guest's view of the host trailer
    rows = []
    try:
        host.press("menu")
        if poll(host, lambda s: s.ui_state == "MainMenu", OPEN_S, "the host's own main menu"):
            end = time.time() + STSCENE_S
            while time.time() < end:
                x = guest.state
                rows.append((cb.path(x, "netsync.world.lane.rx"), cb.path(x, "netsync.world.walk.why")))
                time.sleep(0.2)
        gm.cancel_out(host, _gctx(host), world=True)
    except HarnessError as err:
        d.note(f"GM0-STSCENE: {str(err)[:160]}")
    whys = sorted({str(w) for _rx, w in rows})
    check("GM0-STSCENE", *judge_measuring(rows, f"while the host's own main menu was up: the guest's walk whys {whys}; the lane rx (last) "
                                                f"{rows[-1][0] if rows else None} -- a scene why here is the Known limit"))
    if not _old_gate(d, check, rest, ctx, world=True):
        return
    # GM0-WORLD: walking
    out, pre, s = open_seated(guest, world=True)
    walk = (s if out == "seated" else None, close_out(guest, world=True) if out == "seated" else None)
    # GM0-WALKGHOST (MEASURING) + GM0-WORLDTAG4-D on the next seated open
    before = snap(ready(guest, world=True) or guest.state)
    out3, _pre3, s3 = open_seated(guest, world=True)
    gsamp = []
    sub_ok = False
    if out3 == "seated":
        for _ in range(int(HOLD_S / 0.2)):
            gsamp.append(cb.path(host.state, "netsync.world.ghost"))
            time.sleep(0.2)
        shot_note(d, host, "s168-walkghost-host")
        state, _why = gm.goto_screen(guest, "Item")
        sub_ok = state is not None and gm._back_to_root(guest)
        closed3 = close_out(guest, world=True)
        closed3 = snap(poll(guest, lambda x: (_gm(x).get("outside_settled") or {}).get("set") is True, 2.0, "the settle") or guest.state)
        check("GM0-WORLDTAG4-D", *gm.judge_worldtag4(before, closed3, sub_ok, WORLD))
    else:
        check("GM0-WORLDTAG4-D", False, f"not reached: the press did not seat ({out3})")
    check("GM0-WALKGHOST", *judge_measuring([x for x in gsamp if x is not None], f"of the host's ghost of the seated guest: "
                                            f"{gsamp[-1] if gsamp else None} (REPORTED: a Known limit -- frozen mid-stride)"))
    # frozen (`worldwalk walk off` on the guest: any-role) -- SHOWN frozen first (walk.lever 'off', walk.free false), never a second walk
    okw, _w = cb.try_ns(guest, "worldwalk", "walk", "off")
    guest.wait_frames(SKEW_FRAMES)
    stf = poll(guest, lambda x: cb.path(x, "netsync.world.walk.lever") == "off" and cb.path(x, "netsync.world.walk.free") is False, 3.0,
               "the guest frozen") if okw else None
    frozen, frozen_why = (None, None), None
    if not okw or stf is None:
        frozen_why = (f"`worldwalk walk off` refused ({_w[:120]})" if not okw else
                      f"walk.lever {cb.path(guest.state, 'netsync.world.walk.lever')!r}, walk.free "
                      f"{cb.path(guest.state, 'netsync.world.walk.free')!r} -- never read frozen")
    else:
        outf, _pref, sf = open_seated(guest, world=True)
        frozen = (sf if outf == "seated" else None, close_out(guest, world=True) if outf == "seated" else None)
    if okw:
        cb.try_ns(guest, "worldwalk", "walk", "on")
    # aboard: the guest's own vehicle, a press refused 'riding'
    ride = (None, None)
    live, prior, after = [], None, None
    try:
        guest.vehicle(1)
        guest.wait_frames(20)
        st = poll(guest, lambda x: x.ui_state == "WorldHUD" and not getattr(x, "fading", False), 3.0, "aboard on WorldHUD") or guest.state
        prior = overlay(st)
        pre_r = snap(st)
        guest.press("menu")
        s_r = None
        end = time.time() + LINE_S
        while time.time() < end:
            x = guest.state
            live.append((overlay(x), dict(_gm(x).get("line") or {})))
            if s_r is None and int(_mr(x).get("count", 0) or 0) > int(pre_r["mr"].get("count", 0) or 0):
                gm._skew(guest)
                s_r = snap(guest.state)
            time.sleep(0.2)
        after = overlay(poll(guest, lambda x: overlay(x) != BW.OVERLAY_NAME_GUEST_MENU, 3.0, "the line gone") or guest.state)
        ride = (pre_r, s_r or snap(guest.state))
        guest.vehicle(0)
        guest.wait_frames(20)
    except HarnessError as err:
        d.note(f"aboard: `vehicle 1` refused on the guest ({str(err)[:160]})")
    check("GM0-WORLD", *judge_world(walk, frozen, ride, frozen_why=frozen_why))
    check("GM0-PAIRED-LINE-W", *judge_paired_line(prior, live, after)
          if ride[0] is not None else (False, "not reached: no aboard press"))
    # GM0-RAMP-WORLD-D (LAST: the ramp ends the session) -- the duo's blackhole past the grace while seated on the world map, ON FOOT
    if getattr(guest.state, "world_ctl", 0) not in (0, None):
        try:
            guest.vehicle(0)
        except HarnessError as err:
            d.note(f"GM0-RAMP-WORLD-D: `vehicle 0` refused on the guest ({str(err)[:160]})")
    ok, base, why = _seat_at(guest, None, world=True)
    if not ok:
        check("GM0-RAMP-WORLD-D", False, f"not reached: {why}")
        return
    at = cb.mark(guest)
    bh, how = blackhole(d, PAST_GRACE_S)
    d.note(f"GM0-RAMP-WORLD-D: {how}")
    if bh is None:
        check("GM0-RAMP-WORLD-D", False, f"not reached: {how}")
        close_out(guest, world=True)
        return
    wch = close_watch(guest, base, "ending", PAST_GRACE_S + RAMP_S)
    poll(guest, lambda s: cb.count(cb.new(guest, at), "session ended -> reloading own autosave") > 0, PAST_GRACE_S + RAMP_S, "the ramp")
    st = poll(guest, lambda s: s.ui_state in HUDS and s.control, RAMP_S, "the HUD after the Autoload")
    bh.done.wait(PAST_GRACE_S + 5.0)
    check("GM0-RAMP-WORLD-D", *judge_ramp(base, snap(st or guest.state), cb.new(guest, at), ui_ok=st is not None, words=wch.stop()))


# ---- the close legs
def _seat_at(g, screen, *, world: bool = False) -> tuple:
    """Seated, then at ``screen`` (None: the root): (ok, the snap there, why)."""
    out, _pre, s = open_seated(g, world=world)
    if out != "seated":
        return False, s, f"the press did not seat ({out}: ui {s.get('ui')!r}, why {_n(s, 'why', default=None)!r})"
    if screen is None:
        return True, snap(g.state), ""
    state, why = gm.goto_screen(g, screen)
    if state is None:
        return False, snap(g.state), why
    if screen == "Equip":                                 # Equip's candidates: a slot's list (the design's depth)
        gm._pick(g, "Equip")
        g.press("confirm")
        g.wait_frames(10)
    return True, snap(g.state), ""


def _leg_leave(d, check, rest, ctx: dict) -> None:
    host, guest = d.host, d.guest
    if not _old_gate(d, check, rest, ctx):
        return
    cycles = []
    timing = []
    for n, (dest, screen) in enumerate(((AWAY, "Equip"), (HOME, None))):
        ok, base, why = _seat_at(guest, screen)
        if not ok:
            check("GM0-LEAVE" if n == 0 else "GM0-FADE", False, f"not reached: {why}")
            break
        at = cb.mark(guest)
        t0 = time.time()
        host.send(f"warp {int(dest)} -1 -1", wait=False)     # unawaited: the close and its shot window start at the send
        wch = close_watch(guest, base, "leave", FOLLOW_S)
        if ctx["pulled"] == "closeold":
            time.sleep(CLOSE_OLD_CANCEL_S)
            held = snap(guest.state)
            _measure(ctx, _CLOSE_ROWS["leave"], close_old_measured("leave", base, held))
            close_out(guest)
        shot = None
        s = None
        while time.time() < t0 + SHOT_S:
            x = guest.state
            if _d(base, snap(x), "closes", "leave") >= 1 and shot is None:
                shot = shot_note(d, guest, f"s168-leave-close-{n}")
            time.sleep(0.1)
        landed = wait_field(guest, dest) is not None
        wait_field(host, dest)
        s = wait_settled(guest)
        words = wch.stop()
        pin = swap_pin_age(guest.state)
        cycles.append((screen or "root", base, s, pin, landed))
        timing.append({"depth": screen or "root", "close_ms": (_n(s, "last_close", default={}) or {}).get("ms"), "pin_ms": pin,
                       "landed": landed, "lines": len(cb.new(guest, at))})
        if n == 0:
            check("GM0-LEAVE", *judge_leave(base, s, pin, landed, shot, words=words))
        if guest.state.ui_state in BW.GM_MENU_STATES:     # a cycle that never closed: the guest's own Cancel, so the next cycle starts clean
            close_out(guest)
            wait_field(guest, dest)
    check("GM0-FADE", *judge_fade(cycles))
    check("GM0-TIMING", *judge_measuring(timing, f"(FadeDuration {ctx['fade_ms']!r} ms): {timing}", need=2))


def judge_door_d(pre: dict, s: dict, landed: bool) -> tuple:
    """GM0-DOOR-D (PURE): exactly one door refusal of DOOR_D_WHYS, nothing seated, events on, the follow landed."""
    per = {w: _d(pre, s, "door_refused", w) for w in DOOR_D_WHYS}
    dr = sum(per.values())
    hits = {w: n for w, n in per.items() if n}
    ok = dr == 1 and not _n(s, "seated", default=True) and landed and _n(s, "event_enable", default=None) is True
    return ok, (f"door_refused {'+'.join(DOOR_D_WHYS)} +{dr} ({hits}), why "
                f"{_n(s, 'why', default=None)!r}, seated {_n(s, 'seated', default=None)!r}, the follow landed {landed}, event_enable "
                f"{_n(s, 'event_enable', default=None)!r}")


def _leg_door(d, check, rest, ctx: dict) -> None:
    """GM0-DOOR-D on its own launch (S168-DESIGN R5): the guest's Menu press, then the host's warp right behind it, so the host's door --
    its control off, its lead-in -- lands inside the guest's Hide fade and the guest's DOOR refuses (`scene` the likeliest). Below
    FADE_DOOR_MS the door can run before the host's control-off has crossed the relay (the margin was ~33-96 ms at 300), and it then
    passes and seats the menu: not run (configuration). The commit cannot beat the door below ~1.4 s of fade: it comes 0.9 s after the
    warp (the debug warp's lead-in) plus the guest's ~450 ms follow fade."""
    host, guest = d.host, d.guest
    if not _old_gate(d, check, rest, ctx):
        return
    # under `old` the press is refused AT the press (s121's audible refusal): no door at any fade, the row red by its judge and its shape
    # already measured by _old_gate -- so the gate is the NEW run's only (a gate here would leave the lever's CAL nothing to calibrate)
    if ctx["pulled"] != "old" and (ctx["fade_ms"] or 40) < FADE_DOOR_MS:
        _not_run(check, ctx, ("GM0-DOOR-D",), f"FadeDuration {ctx['fade_ms']!r} < {FADE_DOOR_MS} (this launch's)")
        return
    st = ready(guest)
    if st is None:
        check("GM0-DOOR-D", False, f"not reached: no FieldHUD with control before the press (ui {guest.state.ui_state!r})")
        return
    pre = snap(st)
    guest.press("menu")
    host.send(f"warp {AWAY} -1 -1", wait=False)
    landed = wait_field(guest, AWAY) is not None
    check("GM0-DOOR-D", *judge_door_d(pre, snap(guest.state), landed))


def _leg_out(d, check, rest, ctx: dict) -> None:
    import coop_world_wait as cw
    host, guest = d.host, d.guest
    if not _old_gate(d, check, rest, ctx):
        return
    ok, base, why = _seat_at(guest, None)
    if not ok:
        rest(why)
        return
    at = cb.mark(guest)
    wch = close_watch(guest, base, "out", 2 * WORLD_S)
    okw, whyw, _st = cw.walk_out(host)
    landed = poll(guest, lambda s: s.ui_state == "WorldHUD" and s.world_id == WORLD, WORLD_S, "the guest on 9011") is not None
    s = wait_settled(guest)
    words = wch.stop()
    if ctx["pulled"] == "closeold":
        _measure(ctx, _CLOSE_ROWS["out"], close_old_measured("out", base, s))
    check("GM0-OUT", *judge_out(base, s, landed and okw, cb.new(guest, at), words=words))


def _leg_rejoin(d, check, rest, ctx: dict) -> None:
    import coop_world_wait as cw
    host, guest = d.host, d.guest
    ok, why = _walk_out_both(d)
    if not ok:
        rest(why)
        return
    if not _old_gate(d, check, rest, ctx, world=True):
        return
    ok, base, why = _seat_at(guest, None, world=True)
    if not ok:
        rest(why)
        return
    at = cb.mark(guest)
    wch = close_watch(guest, base, "rejoin", 2 * WORLD_S)
    try:
        cw.teleport_settle(host, cw.ICE_TILE)
        host.wait_frames(cw.PROMPT_FRAMES)
        host.press("confirm")
    except HarnessError as err:
        d.note(f"the host's entry raised: {str(err)[:200]}")
    landed = wait_field(guest, ICE_CAVERN, WORLD_S) is not None
    s = wait_settled(guest)
    words = wch.stop()
    if ctx["pulled"] == "closeold":
        _measure(ctx, _CLOSE_ROWS["rejoin"], close_old_measured("rejoin", base, s))
    check("GM0-REJOIN", *judge_rejoin(base, s, landed, cb.new(guest, at), words=words))


def _fight_out(host) -> None:
    try:
        host.fight(policy=lambda s, slot: {"command": "Attack"}, timeout=FIGHT_S, max_turns=240)
    except HarnessError:
        pass


def _leg_cut(d, check, rest, ctx: dict) -> None:
    host, guest = d.host, d.guest
    if not D_BATTLE:
        _not_run(check, ctx, DUO_ROWS["cut"], "COOP_GMD_BATTLE=0 (the stand-in duo has no diorama model)")
        return
    if not _old_gate(d, check, rest, ctx):
        return
    ok, base, why = _seat_at(guest, "Item")
    if not ok:
        rest(why)
        return
    at = cb.mark(guest)
    t0 = time.time()
    try:
        host.send(f"battle {SCENE} {GROUP}", wait=False)     # unawaited: the cut and its shot window start at the send
    except HarnessError as err:
        rest(f"the host's battle never started ({str(err)[:160]})")
        return
    wch = close_watch(guest, base, "cut", 30.0)
    report, shot = None, None
    while time.time() < t0 + SHOT_S:
        report = boot_name(host.state) or report
        if shot is None and _d(base, snap(guest.state), "closes", "cut") >= 1:
            shot = shot_note(d, guest, "s168-cut-close")
        time.sleep(0.1)
    s_close = snap(guest.state)
    if ctx["pulled"] == "closeold":
        _measure(ctx, _CLOSE_ROWS["cut"], close_old_measured("cut", base, s_close))
    booted = poll(guest, lambda s: s.ui_state == "BattleHUD" and bool(cb.dio(s).get("booted")), 30.0, "the guest's diorama") is not None
    words = wch.stop()
    now = _mr(guest.state).get("now") if booted else None
    pre = snap(guest.state)
    if booted:
        guest.press("menu")
        guest.wait_frames(30)
    after = snap(guest.state)
    bm_ok = cb.try_ns(guest, "bmenu", "mainmenu")[0] if booted else True
    check("GM0-SILENT-D", *judge_silent(now, after.get("ui"), _d(pre, after, "opens"), bm_ok, booted))
    _fight_out(host)
    landed = wait_field(guest, HOME, RETURN_S) is not None
    s = snap(guest.state)
    # 'diorama LIVE' is logged at the command phase (~8 s after the boot), so it is counted only after the fight, never at the boot poll
    lines = cb.new(guest, at)
    live = cb.count(lines, "diorama LIVE")
    check("GM0-CUT", *judge_cut(base, s, report, live, landed, words=words, lines=lines))
    # the quit-prompt leg: a second battle with the guest's prompt over its seated menu
    wait_field(host, HOME, RETURN_S)
    # term 6 reads NetSyncBattle.PeerBattleLive, which holds StaleMs 2000 past the host's last battle view: a press inside it is refused
    # 'host_battle' by design (decision 8), so the seat waits for the guest's battle lane to go stale first
    poll(guest, lambda x: cb.path(x, "netsync.battle.peer.live") is False, 6.0,
         "the host's battle lane stale on the guest (StaleMs 2000: term 6)")
    ok2, base2, why2 = _seat_at(guest, "Item")
    if not ok2:
        check("GM0-CUT-QUIT", False, f"not reached: {why2}")
        return
    okq, whyq, how = _raise_quit_prompt(d, guest)
    if not okq:
        _quit_unreachable(check, ctx, ("GM0-CUT-QUIT",), whyq)
        close_out(guest)                                  # never end the leg seated (as _leg_rampquit)
        return
    d.note(f"GM0-CUT-QUIT: the quit prompt up by {how}{(' (' + whyq + ')') if whyq else ''}")
    at2 = cb.mark(guest)
    try:
        host.start_battle(SCENE, group=GROUP)
    except HarnessError as err:
        check("GM0-CUT-QUIT", False, f"not reached: the second battle never started ({str(err)[:160]})")
        _lower_quit_prompt(guest, how)
        close_out(guest)
        return
    # THE WINDOW OPENS AT THE GUEST'S CLOSE (S168-DESIGN R1): start_battle returns once the battle is up on the HOST, one relay hop before
    # the guest's cut close begins -- a window from there samples the guest before its close (close_step None) and reds a correct hold.
    # closes.cut goes up at the close's REQUEST, one service tick before its first step is judged (the request frame's publish reads
    # close_step None, close_pending true), so the window opens at the first JUDGED step -- or at a close already ended, which the
    # strict judge then reds with its true step. From there it covers the held close past the CloseCapMs it would otherwise end at.
    began = poll(guest, lambda x: _d(base2, snap(x), "closes", "cut") >= 1 and (_gm(x).get("close_step") is not None
                                                                                  or not _gm(x).get("close_pending")),
                 CLOSE_S, "the cut close began on the guest")
    if began is None:
        check("GM0-CUT-QUIT", False, "not reached: the host's battle never closed the guest's menu (closes.cut +0)")
        _lower_quit_prompt(guest, how)
        close_out(guest)
        _fight_out(host)
        wait_field(guest, HOME, RETURN_S)
        return
    waiting, reports = [], []
    end = time.time() + (BW.GM_CLOSE_CAP_MS + 1000) / 1000.0
    while time.time() < end:
        waiting.append(snap(guest.state))
        reports.append(boot_name(host.state))
        time.sleep(0.2)
    _lower_quit_prompt(guest, how)
    s2 = snap(poll(guest, lambda x: (_gm(x).get("last_close") or {}).get("cause") == "cut" and not _gm(x).get("close_pending"), CLOSE_S,
                   "the close ended") or guest.state)
    check("GM0-CUT-QUIT", *judge_cut_quit(waiting, reports, s2, base2, lines=cb.new(guest, at2)))
    _fight_out(host)
    wait_field(guest, HOME, RETURN_S)


def _leg_title(d, check, rest, ctx: dict) -> None:
    host, guest = d.host, d.guest
    if not _old_gate(d, check, rest, ctx):
        return
    ok, base, why = _seat_at(guest, None)
    if not ok:
        rest(why)
        return
    wch = close_watch(guest, base, "title", 2 * CLOSE_S + TITLE_HOLD_S)
    try:
        host.soft_reset()
    except HarnessError as err:
        wch.stop()
        rest(f"the host's soft reset was refused ({str(err)[:160]}: [Control] SoftReset 1 on the host's root?)")
        return
    if ctx["pulled"] == "closeold":
        held = watch_snaps(guest, TITLE_HOLD_S)
        s = close_out(guest)
        _measure(ctx, _CLOSE_ROWS["title"], title_old_measured(base, held, s))
    s = wait_settled(guest)
    check("GM0-TITLE", *judge_title(base, s, ctx["fade_ms"], words=wch.stop()))


def _leg_scene(d, check, rest, ctx: dict, *, chest: bool = False) -> None:
    host, guest = d.host, d.guest
    if not _old_gate(d, check, rest, ctx):
        return
    ok, base, why = _seat_at(guest, None)
    if not ok:
        rest(why)
        return
    at = cb.mark(guest)
    wch = close_watch(guest, base, "scene", 30.0)
    try:
        if chest:
            import coop_chest_relay as cr
            host.walk_to(cr.NEAR[0], cr.NEAR[1], tolerance=cr.NEAR_TOL, strict=False)
            host.press("confirm", 4)
        else:
            host.walk_to(*SCRIBE_AT, tolerance=45, strict=False)
            host.interact(timeout=6.0)
    except HarnessError as err:
        d.note(f"the host's {'chest' if chest else 'talk'} raised: {str(err)[:200]}")
    s = wait_settled(guest)
    words = wch.stop()
    played = poll(guest, lambda x: x.dialog_open, 6.0, "the talk on the guest") is not None
    if ctx["pulled"] == "closeold":
        _measure(ctx, _CLOSE_ROWS["chest" if chest else "scene"], close_old_measured("scene", base, snap(guest.state)))
    row = "GM0-SCENE-CHEST" if chest else "GM0-SCENE"
    check(row, *judge_scene(base, s, played, cb.new(guest, at), chest=chest, words=words))
    try:
        host.advance(max_pages=24)
    except (HarnessError, AttributeError):
        pass


def _leg_ramp(d, check, rest, ctx: dict) -> None:
    guest = d.guest
    if not _old_gate(d, check, rest, ctx):
        return
    ok, base, why = _seat_at(guest, "Item")
    if not ok:
        rest(why)
        return
    at = cb.mark(guest)
    wch = close_watch(guest, base, "ending", 2 * RAMP_S)
    t_w = time.time()
    d.set_netsync("guest", {"Enabled": "0"}, timeout=1.0)   # (its echo wants enabled=True: never for an Enabled=0 edit -- do not wait 15 s)
    if ctx["pulled"] == "closeold":
        # MEASURED past the trigger: the ini lands on the Update's 2 s poll (duo.set_netsync), so a sample read at once precedes
        # ApplyConfigChange and reads as `close old` on ANY build. The last sample BEFORE the ramp's reload line, >= 2.5 s after the write.
        last, last_t = None, None
        end = time.time() + RAMP_S
        while time.time() < end:
            x = guest.state
            if cb.count(cb.new(guest, at), "session ended -> reloading own autosave") > 0:
                break
            last, last_t = snap(x), time.time()
            time.sleep(0.2)
        elapsed = (last_t - t_w) if last_t is not None else 0.0
        _measure(ctx, _CLOSE_ROWS["ramp"], ramp_old_measured(base, last, elapsed))
        d.note(f"`close old` on the ramp: the last pre-ramp sample {elapsed:.1f} s after the write: "
               f"{'MEASURED' if ramp_old_measured(base, last, elapsed) else 'NOT measured'}")
    poll(guest, lambda s: cb.count(cb.new(guest, at), "session ended -> reloading own autosave") > 0, RAMP_S, "the ramp's reload")
    st = poll(guest, lambda s: s.ui_state in HUDS and s.control, RAMP_S, "the HUD with control after the Autoload")
    s = snap(st or guest.state)
    check("GM0-RAMP-CFG-D", *judge_ramp(base, s, cb.new(guest, at), ui_ok=st is not None, words=wch.stop()))


def _leg_rampquit(d, check, rest, ctx: dict) -> None:
    guest = d.guest
    if not _old_gate(d, check, rest, ctx):
        return
    ok, base, why = _seat_at(guest, None)
    if not ok:
        rest(why)
        return
    okq, whyq, how = _raise_quit_prompt(d, guest)         # `endbench quit on`, else (the selftest role's) a WM_CLOSE to the guest
    if not okq:
        _quit_unreachable(check, ctx, ("GM0-QUIT-D",), whyq)
        close_out(guest)
        return
    d.note(f"GM0-QUIT-D: the quit prompt up by {how}{(' (' + whyq + ')') if whyq else ''}")
    at = cb.mark(guest)
    d.set_netsync("guest", {"Enabled": "0"}, timeout=1.0)   # (its echo wants enabled=True: never for an Enabled=0 edit -- do not wait 15 s)
    poll(guest, lambda s: cb.count(cb.new(guest, at), "session ended -> reloading own autosave") > 0, RAMP_S, "the ramp's reload")
    st = poll(guest, lambda s: s.ui_state in HUDS and s.control, RAMP_S, "the HUD with control after the Autoload")
    s = snap(st or guest.state)
    prompt = cb.quit_prompt_up(guest.state)                 # the stock QuitUI's tell (no engine publishes a quit_open key)
    check("GM0-QUIT-D", *judge_quit_d(base, s, cb.new(guest, at), prompt))
    if prompt:
        _lower_quit_prompt(guest, how)                    # a prompt that survived the Autoload: down by Cancel / `quit off`, never Confirm


def _leg_stall(d, check, rest, ctx: dict) -> None:
    guest = d.guest
    if not _old_gate(d, check, rest, ctx):
        return
    # GM0-STALL-VIEW-D
    ok, base, why = _seat_at(guest, None)
    if not ok:
        rest(why)
        return
    bh, how = blackhole(d, STALL_S)
    d.note(f"GM0-STALL-VIEW-D: {how}")
    if bh is None:
        rest(how)
        close_out(guest)
        return
    during, stale = [], 0
    while not bh.done.is_set():
        x = guest.state
        during.append(snap(x))
        stale += stale_read(x)                            # THE STALL WITNESS: the raw read, snap() drops peer_alive
        time.sleep(0.2)
    time.sleep(1.0)
    after = snap(guest.state)
    closed = close_out(guest)
    check("GM0-STALL-VIEW-D", *judge_stall_view(base, during, after, closed, stale))
    # GM0-PAIRED-LINE-LOST: a press inside the blip hold -- past StaleMs (the lane stale: IsLiveFollowedSession false), before the grace
    st = ready(guest)
    pre = snap(st or guest.state)
    bh, how = blackhole(d, STALL_S + 1.5)
    time.sleep((BW.STALE_MS + 500) / 1000.0)
    guest.press("menu")
    live, s = [], None
    end = time.time() + LINE_S
    while time.time() < end:
        x = guest.state
        live.append((overlay(x), bh is not None and not bh.done.is_set()))   # held: `done` read AFTER the state, so the read was inside
        if s is None and int(_mr(x).get("count", 0) or 0) > int(pre["mr"].get("count", 0) or 0):
            s = snap(x)
        time.sleep(0.2)
    if bh is not None:
        bh.done.wait(STALL_S + 6.5)
    check("GM0-PAIRED-LINE-LOST", *judge_lost_line(pre, s or snap(guest.state), live))
    # GM0-RAMP-FIELD-D (last: the ramp ends the session)
    ready(guest, timeout=10.0)
    ok, base, why = _seat_at(guest, None)
    if not ok:
        check("GM0-RAMP-FIELD-D", False, f"not reached: {why}")
        return
    at = cb.mark(guest)
    bh, how = blackhole(d, PAST_GRACE_S)
    wch = close_watch(guest, base, "ending", PAST_GRACE_S + RAMP_S)
    poll(guest, lambda s: cb.count(cb.new(guest, at), "session ended -> reloading own autosave") > 0, PAST_GRACE_S + RAMP_S, "the ramp")
    st = poll(guest, lambda s: s.ui_state in HUDS and s.control, RAMP_S, "the HUD after the Autoload")
    if bh is not None:
        bh.done.wait(PAST_GRACE_S + 5.0)
    check("GM0-RAMP-FIELD-D", *judge_ramp(base, snap(st or guest.state), cb.new(guest, at), ui_ok=st is not None, words=wch.stop()))


def _leg_dialog(d, check, rest, ctx: dict) -> None:
    host, guest = d.host, d.guest
    for row, unlock in (("GM0-DIALOG-PATH-A", False), ("GM0-DIALOG-PATH-B", True)):
        if unlock:
            oku, whyu = cb.try_ns(guest, "unlock")
            d.note(f"`netsync unlock` on the guest: {'ok' if oku else whyu[:160]}")
        try:
            host.walk_to(*SCRIBE_AT, tolerance=45, strict=False)
            host.interact(timeout=6.0)
        except HarnessError as err:
            d.note(f"the host's talk raised: {str(err)[:160]}")
        st = poll(guest, lambda x: x.dialog_open, 6.0, "the host's line on the guest")
        pre = snap(st or guest.state)
        sup0 = suppress(st or guest.state)
        guest.press("menu")
        guest.wait_frames(30)
        s = snap(guest.state)
        sup1 = suppress(guest.state)
        if unlock:
            check(row, *judge_dialog_b(pre, s, sup0, st is not None))
        else:
            check(row, *judge_dialog_a(pre, s, sup1, st is not None))
        try:
            host.advance(max_pages=24)
            host.wait_for(lambda x: x.control, timeout=8.0, what="the host's control back")
        except (HarnessError, AttributeError):
            pass
        poll(guest, lambda x: not x.dialog_open, 8.0, "the guest's window closed")


def _leg_hudstrip(d, check, rest, ctx: dict) -> None:
    guest = d.guest
    st = poll(guest, lambda x: x.dialog_open, 5.0, "the field's strip window")
    pre = snap(st or guest.state)
    guest.press("menu")
    guest.wait_frames(30)
    check("GM0-HUDSTRIP", *judge_hudstrip(pre, snap(guest.state), st is not None))


FNS = {"key": _leg_key, "caps": _leg_caps, "world": _leg_world, "leave": _leg_leave, "door": _leg_door, "out": _leg_out,
       "rejoin": _leg_rejoin,
       "cut": _leg_cut, "title": _leg_title, "scene": _leg_scene, "chest": lambda d, c, r, x: _leg_scene(d, c, r, x, chest=True),
       "ramp": _leg_ramp, "rampquit": _leg_rampquit, "stall": _leg_stall, "dialog": _leg_dialog, "hudstrip": _leg_hudstrip}


# ================================================================================================ the T legs (tools/play.py)
def _t2():
    import coop_world_walk_t2 as t2                     # beside this file: the T2 route (the stallhole route, the instrument, the replay)
    return t2


def run(g, field: int | None = None):
    """One T leg (COOP_GMT_LEG): the desktop a real client fed by replay-host."""
    if T_LEG is None:
        led = cb.Ledger(g, {"S168T-LEG": "COOP_GMT_LEG names one T leg"})
        led.check("S168T-LEG", False, f"COOP_GMT_LEG={_RAW_T!r} is not one of {T_LEGS} -- nothing was run past the boot")
        return
    calibrate = cb.CALIBRATE
    lever = lever_of(T_LEG, LEVER_RAW) if calibrate else None
    cat = t_catalog(T_LEG, calibrate)
    led = cb.Ledger(g, cat, finals=("T2-SAVE", "T2-INI", "S168T-CAL", "S168-GMT-GATE"), width=DETAIL_W)
    if calibrate and LEVER_RAW is not None and lever is None:
        led.check("S168T-CAL", False, f"COOP_GMT_LEVER={LEVER_RAW!r} is not leg {T_LEG!r}'s ({LEG_LEVERS[T_LEG] or 'none'}) -- nothing edited")
        led.close("not launched: the lever is not this leg's", final=True)
        return
    t2 = _t2()
    ctx = t2._Ctx()
    ctx.field, ctx.lever = FARSHORE, lever
    ctx.gm = {"new": False, "pulled": None, "measured": {}, "tape_ok": None}
    try:
        {"hole": _t_hole, "older166": _t_older, "older167": _t_older, "tape": _t_tape}[T_LEG](g, led, ctx)
    except HarnessError as err:
        g.note(f"the {T_LEG} leg raised: {str(err)[:400]}")
        led.close(f"not reached: the leg raised ({str(err)[:200]})")
    finally:
        if ctx.gm.get("sent"):
            cb.try_ns(g, "guestmenu", "clear")
        t2._t2_teardown(g, led, ctx)
        if "S168-GMT-GATE" in led.catalog and "S168-GMT-GATE" not in led.done:
            led.check("S168-GMT-GATE", bool(ctx.gm.get("tape_ok")), ctx.gm.get("gate_why") or "no COOP_TAPE_GUEST_MENU (owner-gated: "
                      "record it with coop_tape_record.py's GUEST-MENU variant on an s168 host)")
        if calibrate:
            led.close("not reached: the leg ended before this check")
            new = ctx.gm["new"]
            pred = old_predicted(T_LEG) if not new else LEVER_PREDICTED.get((T_LEG, ctx.gm["pulled"]), ())
            needs = pred                                  # THE CAL RULE on OLD too: each predicted red MEASURED (OLD is unrepeatable)
            failed = led.failed() - {"S168T-CAL", "S168-GMT-GATE"}
            if T_LEG == "tape" and not ctx.gm.get("tape_ok"):
                pred, needs = T_ROWS["tape"] + ("T2-TAPE", "T2-PEER"), ()   # no b3 tape (owner-gated): every row unrun and predicted
                led.check("S168T-CAL", *judge_cal(failed, pred, ctx.gm["measured"], needs))
            else:
                led.check("S168T-CAL", *cal_verdict(new, ctx.lever, ctx.gm["pulled"], failed, pred, ctx.gm["measured"], needs))
        led.close(final=True)


def _t_pull(g, ctx) -> None:
    gmx = ctx.gm
    gmx["new"] = stage_new(g.state)
    if gmx["new"] and ctx.lever in LEVER_OPS:
        ok, why = cb.try_ns(g, "guestmenu", *LEVER_OPS[ctx.lever])
        g.wait_frames(SKEW_FRAMES)
        field, word = LEVER_READ[ctx.lever]
        st = poll(g, lambda s: (_gm(s).get("lever") or {}).get(field) == word, 3.0, "the lever read back") or g.state
        gmx["pulled"] = ctx.lever if ok and (_gm(st).get("lever") or {}).get(field) == word else None
        gmx["sent"] = gmx.get("sent") or ok
        g.note(f"CALIBRATION `guestmenu {' '.join(LEVER_OPS[ctx.lever])}`: "
               f"{'pulled (read back)' if gmx['pulled'] else 'NOT pulled: ' + (why[:160] or 'never read back')}")


def _t_press(g, *, world: bool = False, timeout: float = OPEN_S, wait_s: float = 10.0) -> tuple:
    """A T guest's press from its HUD (control NOT required: a frozen world-paired guest): (pre, after, the RAW state read right before
    the press -- GM0-STALL-WHO-T asks it whether the press landed inside the stall). ``wait_s`` bounds the wait for the HUD with no fade."""
    hud = HUD_OF(world)
    st = poll(g, lambda s: s.ui_state == hud and not getattr(s, "fading", False), wait_s, f"{hud} (no fade)")
    raw = st if st is not None else g.state
    pre = snap(raw)
    c0 = int(pre["mr"].get("count", 0) or 0)
    g.press("menu")
    poll(g, lambda s: s.ui_state == "MainMenu" or int(_mr(s).get("count", 0) or 0) > c0, timeout, "the press's outcome")
    g.wait_frames(SKEW_FRAMES)
    s = snap(g.state)
    if s.get("ui") in BW.GM_MENU_STATES and not _n(s, "seated", default=False):
        gm.cancel_out(g, _gctx(g), world=world)
    return pre, s, raw


def _t_hole(g, led, ctx) -> None:
    """GM0-HOLE-T + GM0-STALL-WHO-T on coop_world_walk_t2's stallhole route."""
    t2 = _t2()
    import coop_world_wait as cw
    rows = list(T_ROWS["hole"])
    if not t2._guest_setup(g, led, ctx):
        return
    _t_pull(g, ctx)
    if t2._b_tape(g, led, ctx) is None:
        return
    w = t2.stall_windows(ctx.rows)
    w_ok = None not in (w["from"], w["gap"])
    led.check("T2-TAPE", ctx.tape_ok and w_ok, ctx.tape_detail + f"; the stall window {w}")
    if not (ctx.tape_ok and w_ok):
        led.unreached(rows, "this tape cannot carry the leg (T2-TAPE)")
        return
    ok, why, _st = cw.walk_out(g)
    if not ok:
        led.unreached(rows, f"the guest's own walk out failed: {why[:200]}")
        return
    ctx.base = g.state
    # the hole's blackhole widened as PAIRED-LINE-LOST's (STALL_S + 1.5: ~2.2 s past StaleMs + PRESS_PAST_MS for the press); the window
    # pick_window chose holds it (2.3 s + RECOVER_S 3.0 of jump-free rows from `gap`)
    args = ["--from", f"{w['from']:g}", "--blackhole-at", f"{w['gap']:g}", "--blackhole-for", f"{HOLE_BH_S:g}", "--at-end", "hold"]
    if not t2._replay(g, led, ctx, args, want_send=None, tag="gm-hole"):
        led.unreached(rows, "the replay never started (T2-PEER)")
        return
    # THE PRE-INIT SAMPLE at the pairing edge: `world.freeze.on` is a LIVE read (SpectatorField -> IsLiveFollowedSession) while decision
    # 7's guestSession (WorldSessionHeld) is SessionTick's once-per-Update latch -- a sample between them reads `now` 'open' (s121's read)
    # and the press one frame on is refused. Press only once the session itself holds (session.state on OLD too; guestmenu.session on s168).
    t2._wait(g, ctx, lambda s: s.ui_state == "WorldHUD" and t2.judged(s) and cb.path(s, "netsync.session.mirroring") is not True
             and cb.path(s, "netsync.world.freeze.on") is True and cb.path(s, "netsync.session.state") == "live"
             and (not ctx.gm["new"] or cb.path(s, "netsync.guestmenu.session") is True), t2.STALL_PAIR_S, kinds="bh")
    pre, s, _raw = _t_press(g, world=True)
    led.check("GM0-HOLE-T", *judge_refused((BW.GM_WHY_NOT_MIRRORING,), pre, s, world=True))
    _measure(ctx.gm, "GM0-HOLE-T", own_menu_measured(s))
    if not t2._wait(g, ctx, lambda st: "bh1" in ctx.events, t2.EVENT_S, kinds="bh"):
        led.check("GM0-STALL-WHO-T", False, f"not reached: the blackhole never opened (peer edges {sorted(ctx.events)})")
        return
    t2._wait(g, ctx, lambda st: t2._stalled(st, t2.PRESS_PAST_MS) or "bh1_end" in ctx.events, HOLE_BH_S + 2.0, kinds="bh")
    pre2, s2, raw2 = _t_press(g, world=True, timeout=1.5, wait_s=1.0)   # never wait for 'no fade' past the stall's end
    stalled = t2._stalled(raw2, t2.PRESS_PAST_MS)
    led.check("GM0-STALL-WHO-T", *judge_stall_who((BW.GM_WHY_NOT_MIRRORING,), pre2, s2, stalled,
                                                   cb.path(raw2, "netsync.world.lane.arrival_age_ms")))
    _measure(ctx.gm, "GM0-STALL-WHO-T", stalled and own_menu_measured(s2))   # measured only on an in-stall press


def _t_older(g, led, ctx) -> None:
    """GM0-CAPS-b-<stage>: an older HOST (the recorded tape, else its INSTRUMENT) replayed into the guest on 6603."""
    t2 = _t2()
    stage = 166 if T_LEG == "older166" else 167
    peer = BW.CAPS_S166 if stage == 166 else BW.CAPS_S167
    row = f"GM0-CAPS-b-{stage}"
    if not t2._guest_setup(g, led, ctx):
        return
    _t_pull(g, ctx)
    cp = pb.coop_peer_module()
    env = (os.environ.get(f"COOP_TAPE_GM_OLDER{stage}") or "").strip()
    if env:
        ctx.tape, how = Path(env), f"the recorded s{stage} tape"
    else:
        ctx.tape = t2.write_instrument(t2.cw._run_dir(g) / f"gm-older{stage}-INSTRUMENT.f9tape", cp, caps=peer)
        ctx.instrument, how = True, f"THE INSTRUMENT (a synthetic s{stage} host, caps 0x{peer:04X})"
    try:
        _h, records, _torn = cp.read_tape(ctx.tape)
        f_ok, bad = t2.facts_ok(t2.roam_tape_facts(records, cp))
    except Exception as err:                              # noqa: BLE001
        f_ok, bad = False, [f"the tape does not read back: {err}"]
    led.check("T2-TAPE", f_ok, f"{how}: {Path(ctx.tape).name}: " + ("the facts hold" if f_ok else "; ".join(bad)))
    if not f_ok:
        led.unreached((row,), "this tape cannot carry the leg (T2-TAPE)")
        return
    at = cb.mark(g)
    if not t2._replay(g, led, ctx, ["--at-end", "hold"], want_send=None, tag=f"gm-older{stage}"):
        led.unreached((row,), "the replay never started (T2-PEER)")
        return
    t2._wait(g, ctx, lambda s: s.ui_state == "FieldHUD" and s.field_id == FARSHORE and cb.path(s, "netsync.session.mirroring") is True
             and s.control, 20.0)
    pre, s, _raw = _t_press(g)
    lines = cb.new(g, at)
    own = int((_gm(g.state).get("caps") or {}).get("own", BW.CAPS_S168)) if ctx.gm["new"] else BW.CAPS_S167
    led.check(row, *judge_caps_b(pre, s, lines, own, peer))
    _measure(ctx.gm, row, caps_b_old_measured(pre, s, lines, peer))


def t_tape_windows(facts: dict) -> dict:
    """(PURE) The `tape` leg's plan off pb.gm_tape_facts' anchors (tape seconds): the key press, the stall's blackhole, the press before the
    leave and the battle, and the ramp's `--stop-at` (field: 10 s after the battle's end; world: 15 s after the world exit)."""
    if facts is None or facts.get("start") is None:
        return {}
    st = facts["start"]
    out = {"key": st + 14.0, "stall": st + 26.0, "leave": (facts.get("away") or 0) - 6.0 if facts.get("away") else None,
           "cut": ((facts.get("battle") or {}).get("start") or 0) - 6.0 if facts.get("battle") else None}
    if T_RAMP == "world":
        out["stop_at"] = (facts["exit"] + 15.0) if facts.get("exit") is not None else None
    else:
        out["stop_at"] = ((facts.get("battle") or {}).get("end") + 10.0) if facts.get("battle") else None
    return out


def _t_tape(g, led, ctx) -> None:
    """The b3 tape rows (OWNER-GATED tape): until COOP_TAPE_GUEST_MENU exists, every row 'not reached' and the gate red."""
    t2 = _t2()
    rows = list(T_ROWS["tape"])
    tape = pb.latest_guest_menu_tape()
    cp = pb.coop_peer_module()
    if tape is None or not Path(tape).exists():
        ctx.gm["gate_why"] = ("no COOP_TAPE_GUEST_MENU: the owner-gated recording (coop_tape_record.py's GUEST-MENU variant on an s168 "
                              "host) has not been made -- the rows' duo twins run them (GM0-KEY, GM0-STALL-VIEW-D, GM0-LEAVE, GM0-CUT, "
                              "GM0-RAMP-FIELD-D)")
        led.check("T2-TAPE", False, ctx.gm["gate_why"])
        led.unreached(rows + ["T2-PEER"], "no b3 tape (owner-gated): the duo twins run these rows")
        return
    try:
        _h, records, torn = cp.read_tape(tape)
        facts = pb.gm_tape_facts(records, cp)
        ok, bad = pb.gm_tape_ok(facts)
    except Exception as err:                              # noqa: BLE001
        facts, ok, bad = None, False, [f"the tape does not read back: {err}"]
    ctx.gm["tape_ok"] = ok
    ctx.gm["gate_why"] = f"{Path(tape).name}: " + ("the eight facts hold" if ok else "; ".join(bad))
    led.check("T2-TAPE", ok, ctx.gm["gate_why"])
    if not ok:
        led.unreached(rows, "this tape cannot carry the leg (T2-TAPE)")
        return
    w = t_tape_windows(facts)
    ctx.tape = Path(tape)
    if not _t_guest_setup_on(g, led, ctx, pb.GM_TAPE_FIELD):
        return
    _t_pull(g, ctx)
    args = ["--blackhole-at", f"{w['stall']:g}", "--blackhole-for", f"{STALL_S:g}"]
    if w.get("stop_at") is not None:
        args += ["--stop-at", f"{w['stop_at']:g}"]
    args += ["--at-end", "hold"]
    if not t2._replay(g, led, ctx, args, want_send=None, tag="gm-tape"):
        led.unreached(rows, "the replay never started (T2-PEER)")
        return
    t0 = time.time() - 0.5
    rel = lambda tape_t: t0 + (tape_t - facts["start"])                                    # noqa: E731

    def until(tape_t):
        while time.time() < rel(tape_t):
            t2._sample(g, ctx)
            t2._peer_events(ctx, "bh")
            time.sleep(0.1)
    t2._wait(g, ctx, lambda s: s.ui_state == "FieldHUD" and cb.path(s, "netsync.session.mirroring") is True and s.control, 30.0)
    # KEY + FREEZE
    out, pre, s = open_seated(g)
    seated = [s] + watch_snaps(g, 1.0) if out == "seated" else []
    closed = close_out(g) if out == "seated" else snap(g.state)
    ok_k = out == "seated" and (_n(s, "seat", default={}) or {}).get("src") == BW.GM_SEAT_SRC_WIRE and \
        int(s.get("mr", {}).get("count", 0) or 0) == int(pre.get("mr", {}).get("count", 0) or 0)
    led.check("GM0-KEY-T", ok_k, f"the press {out}, seat {_n(s, 'seat', default=None)}, count {s.get('mr', {}).get('count')}")
    _measure(ctx.gm, "GM0-KEY-T", key_old_measured(pre, s))
    led.check("GM0-FREEZE-T", *judge_freeze_t(seated, closed))
    _measure(ctx.gm, "GM0-FREEZE-T", key_old_measured(pre, s))
    # STALL-VIEW
    until(w["stall"] - 3.0)
    out2, pre2, s2 = open_seated(g)
    during = []
    if out2 == "seated":
        until(w["stall"] + STALL_S + 0.5)
        win = [x for _t, x in ctx.samples[-int((STALL_S + 0.5) / 0.1):]]
        during = [snap(x) for x in win]
        stale = sum(1 for x in win if stale_read(x))      # THE STALL WITNESS over the window's raw states
        after = snap(g.state)
        closed2 = close_out(g)
        led.check("GM0-STALL-VIEW-T", *judge_stall_view(s2, during, after, closed2, stale))
    else:
        led.check("GM0-STALL-VIEW-T", False, f"not reached: the press {out2}")
    _measure(ctx.gm, "GM0-STALL-VIEW-T", key_old_measured(pre2, s2))
    # LEAVE
    for row, at_t, cause, dest in (("GM0-LEAVE-T", w.get("leave"), "leave", pb.GM_TAPE_AWAY), ("GM0-CUT-T", w.get("cut"), "cut", None)):
        if at_t is None:
            led.check(row, False, "not reached: no anchor on the tape")
            continue
        until(at_t)
        if cause == "cut":
            wait_field(g, pb.GM_TAPE_FIELD, 30.0)
        outx, prex, sx = open_seated(g)
        if outx != "seated":
            led.check(row, False, f"not reached: the press {outx}")
            _measure(ctx.gm, row, key_old_measured(prex, sx))
            continue
        at = cb.mark(g) if cause == "cut" else None
        wch = close_watch(g, sx, cause, 40.0)
        if cause == "leave":
            landed = wait_field(g, dest, 30.0) is not None
            sl = wait_settled(g)
            led.check(row, *judge_close("leave", sx, sl, words=wch.stop(), landed=landed))
        else:
            booted = poll(g, lambda x: bool(cb.dio(x).get("booted")), 30.0, "the diorama") is not None
            st = poll(g, lambda x: (_gm(x).get("last_close") or {}).get("cause") == "cut" and not _gm(x).get("close_pending"),
                      CLOSE_S, "the cut's close record ended")
            sl = snap(st or g.state)
            lc_end = (_n(sl, "last_close", default={}) or {}).get("end")
            end_ok = cut_end_ok(lc_end, cb.new(g, at))
            led.check(row, *judge_close("cut", sx, sl, words=wch.stop(), landed=booted, ends=("done", "clear_point"), extra_ok=end_ok,
                                        extra=f"the diorama booted {booted}; end {lc_end!r} (done, or the boot's scene load after the "
                                              f"door: {end_ok})"))
    # RAMP
    if w.get("stop_at") is None:
        led.check("GM0-RAMP-T", False, "not reached: no --stop-at anchor")
        return
    until(w["stop_at"] - 4.0)
    outr, prer, sr = open_seated(g, world=T_RAMP == "world")
    if outr != "seated":
        led.check("GM0-RAMP-T", False, f"not reached: the press {outr}")
        _measure(ctx.gm, "GM0-RAMP-T", key_old_measured(prer, sr))
        return
    at = cb.mark(g)
    wch = close_watch(g, sr, "ending", 60.0 + RAMP_S)
    poll(g, lambda x: cb.count(cb.new(g, at), "session ended -> reloading own autosave") > 0, 60.0, "the ramp")
    st = poll(g, lambda x: x.ui_state in HUDS and x.control, RAMP_S, "the HUD after the Autoload")
    led.check("GM0-RAMP-T", *judge_ramp(sr, snap(st or g.state), cb.new(g, at), ui_ok=st is not None, words=wch.stop()))


def _t_guest_setup_on(g, led, ctx, field: int) -> bool:
    """coop_world_walk_t2._guest_setup's guest, on ``field`` (the b3 tape's host starts on 250, not 6603)."""
    t2 = _t2()
    if not t2.wf._walk_preflight(g, led):
        return False
    cb.provenance(g)
    g.newgame()
    g.warp(field)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"noencounter refused ({str(err)[:160]})")
    g.wait_frames(45)
    ctx.eng = pb.EngineLog(g.engine_log())
    ctx.guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", t2.GUEST_VALUES, label="coop-guest-menu-t-tape", run_dir=t2.cw._run_dir(g))
    try:
        g.note(ctx.guard.apply())
    except (OSError, RuntimeError) as err:
        led.check("T2-PEER", False, f"the Memoria.ini edit failed: {err}")
        return False
    ctx.field = field
    cfg = t2.cw._wait_config(g, ctx)
    if not cfg:
        led.check("T2-PEER", False, "the engine never logged the guest config")
        return False
    ctx.cfg = cfg
    return True
