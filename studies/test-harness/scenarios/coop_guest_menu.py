"""s168 -- THE GUEST'S MAIN MENU, RUNG 0 (view only): THE SOLO (S) BENCH, run unattended, and the OFFLINE (O) rows' tables.
[ff9mapkit netsync s168] studies/field-coop/S168-DESIGN.md "The bench": every GM0 row the table marks S (the forced selftest role: THE
ACTION ONLY -- decision 35: it never mirrors, runs no DioramaTick and seats from a `guestmenu frame` built BEFORE the seat), one launch
per leg (COOP_GM_LEG), each row naming its OLD (the deployed s167 DLL), its NEW judge and its LEVER, so every row can fail. The O rows
(GM0-OFFLINE, GM0-REGISTRY, GM0-SAVEGATES, GM0-FRAME) are offline tests (ff9mapkit/tests/test_coop_guest_menu_bench.py).

THE STAGE, read off the probe: `netsync.guestmenu` published = s168 (NEW, LEVER); absent = OLD (s167: the `guestmenu` sub-verb unknown --
it fails closed -- and the key absent). On OLD NO `guestmenu` op is EVER sent (the driver sends it as a raw step through cb.ns_verb, so the
bench gates it on the probe itself), every leg row reads "not reached", and each leg MEASURES s167's shape: the selftest role's s121 reading
on the HUD (`menu_refusal.now` 'open'; decision 6: the bench is not mirroring), and a Menu press (noted: on s167 it opens the bench's OWN
menu; under `guestmenu old` on s168 that own, unseated open -- `open` true, `seated` false -- is required too).

THE ROUTE (the s121 bench's field conventions, cb.setup): New Game -> the COOPPARTY seeder -> (the refuse / deep legs: the GMBAG bag
seeder, BAG_FIELD 30816 -- Desert Boots, Gysahl Greens (no key item yet), granted on entry; the frame copies the guest's count>0 rows and rare
sets) -> GM_FIELD (30801, the journal dashboard: the scribe -- a plain window -- west at (-210, -837), the keeper east; COOP_GM_FIELD moves
it) -> encounters off -> the forced selftest role; P1 `netsync bench 1`. The `world` leg instead: 6603 FARSHORE -> world 9011 by s165's
follow-out (coop_world_walk._a_land, imported, never copied). Every seat is `guestmenu frame <marker>` (two markers: slot 0 the impostor "BENCH<marker>" lv99, every exp, the gil and one bag row
values the guest does not hold) then the REAL Menu key through the verdict (the bench is in `who`, decision 7).
THE LAWS: THE PRE-INIT SAMPLE (a press only from the HUD with control on, no fade, no window -- the field's init done; on the world after
`world.block_ready` and advancing ticks); THE ORDER SKEW (each op's own publish dropped: SKEW_FRAMES); LIVE VERDICT vs LAST DRAWN (`now` and
`session` are live reads, `why` the LAST refusal's book: every why row judges the press it made, its deltas from a base read right before);
NEVER JUDGED WHILE SEATED (fp.equal reads false while a record is held -- decision 33: every restore row reads after the close); THE DECLINE
LATCH (the refusal's log line is once per place per why class: a data_differs component is read on a FRESH place -- the witness variants
alternate GM_FIELD and ALT_FIELD).

  setup  S168-INI the ini, READ-ONLY ([Netsync] Enabled 0 or absent + FollowHost 1, written BEFORE launch by solo_ini.py: THE FORCED-ROLE
         PIN) -> S168-S0 (newgame, the seeder, the bench field, encounters off, `netsync selftest 1` forced) -> S168-P0 (`netsync.guestmenu`
         netsync's LAST key at BW.GUEST_MENU_SENTINELS' keys, every nested block's keys in order, the twelve levers at their defaults, my caps
         word 0x000B by stage) -> GM0-PROOF (the proof block's last three lines IN ORDER: 'world walk selftest: OK (534 rows, 198 mutants)',
         'seat bracket selftest: OK (19 rows, 7 mutants caught)', 'guest menu selftest: OK (420 rows, 249 mutants caught)' -- each want DERIVED
         from the s168 source ($FF9_S168_CLONE / an s168 patch; else the W1 fallbacks), none FAIL, and 'main menu refusal selftest: OK (14
         rows)' unmoved; the seat bracket line carries GM0-BRACKET-CLEAR's rows, `clear.*` and `cross.*`) -> S168-P1 (`netsync bench 1`; the levers at rest -- or the CALIBRATION lever pulled and read back, held through the
         run). Final: S168-R (`reset`: the role released; 'guestmenu levers released (with the harness)' ONCE; the twelve levers at their
         defaults, the bench frame dropped). Every launch: S168-CAL (THE CAL RULE: exactly the predicted reds, each MEASURED).

THE LEGS (OLD = the deployed s167; LEVER = what restores OLD or the row's mutant -- each pulled at P1 under COOP_CALIBRATE=1):
  proof   the setup alone (K1's launch: the proof lines and the probe).
  seat    GM0-SEAT the bench frame seated: `seated`, opens +1, seat.src 'bench', seat.marker the frame's, the frame line's BENCH<m> lv99 and
          gil G, the seat line 'from the bench frame (marker m) ... gil G', and seat_fp's players / party / gil components each differ from
          fp_before's (TWO MARKERS: the impostor drawn, not the guest's own). OLD not reached. LEVER `seat skip party` (players / party equal:
          the guest's own drawn, red), `old` (the own menu, unseated).
          GM0-CHIP the chip's words ("View only: your partner's game makes the changes.") on every sample while seated, null after the close.
          LEVER `chip off`: seated with no chip, red.
          GM0-FREEZE (S) `event_enable` false on every sample while seated, true after the close. LEVER `events on`: true while open, red.
          GM0-BROWSE Item, Ability, Equip and Status by label (Folklore / Journal when the root has it) each open its screen and Cancel back
          to the root; Order, Party, Card and Config (whichever the root draws) greyed: Confirm opens nothing, `refused` +0; no Save row;
          Alt+F5 (`savemenu`) never opens Serialize (TryShowSaveScene's state gate: nothing reaches R4); seated throughout, the frame's party
          drawn. One shot per screen (READ them). LEVER `seat skip party`: the guest's own party drawn, red.
          GM0-RESTORE two cycles -- the browse's close and a root-only open/Cancel (no sub-screen visited: the close's `prevState` reads
          FieldHUD) on `frame witness keyitem` (`frame <m>` copies the guest's own key items, so only that frame swaps the key-item family
          and lets `restore skip keyitems` redden the row): each fp_after == fp_before, `named` null, restore.doors +1, seated false, outside_equal. LEVER `restore skip <c>` (once
          per component, COOP_GM_LEVER=restore:<c>): red, `named` == c.
  refuse  GM0-REFUSE-I1 / -E1 / -A1 / -A2 one census confirm each (SITE_PLANS -- every bar is HORIZONTAL: Item opens ON its list, Potion
          > a target; Equip's bar > the accessory slot > the seeded Desert Boots; Ability's bar Equip > the support list, which opens ON the
          first lit SA: its Confirm, its Special), each list's group and label read before the press (the try's trail): `refused.count`
          +1, `captures` +1, `passes` +0, `last_site` the site, `last_screen` the screen, `impactful` 0, still seated, Cancel walks back to the root, ONE census line for the site, and at the close fp_after ==
          fp_before. LEVER `capture off`: refused +0, passes +1, impactful > 0 (the seated copy written; the restore still discards it).
          GM0-REFUSE-GREY Order / Party / Card / Config: grey (no screen opens), refused +0, captures +0. GM0-OUTSIDE across the sweep:
          fp.outside_equal true, outside_named null, outside_settled equal. LEVER `poke`: outside_named 'events', red.
  deep    (in-game paths; the stand-in models one confirm per screen) GM0-REFUSE-E2 (Equip's bar Off > a slot), -E3 (the bar's Optimize:
          its own Confirm), -A3 (Garnet -- member 2, the root's remembered character tracked -- Use > Cure > a target; a shot after the Use
          pick), -I2 (Item > the seeded Gysahl Greens), the same deltas; GM0-LOCAL Item's rail > Arrange > Auto, then Arrange > Manual: rows
          0 and 2 swap on the seated copy (MEASURED: row 2 reads row 0's label), the rail's Key > the seeded key item's description opened
          and closed, Folklore: refused +0, captures +0, seated, fp equal at the close. LEVER `capture off` on the four sites. E1, I2 and
          LOCAL's key read need GMBAG: unregistered, each reads "not reached: the bag seeder ... is not registered"; while GMBAG grants
          no key item (BAG_KEY_ITEM None: the toml's KNOWN GAP) the key read reads "not reached: ... grants no key item yet".
  why     each a Menu press after one bench op (decision 8's terms; every case but NODATA after a `frame`), refused AUDIBLY at the press:
          not seated, opens +0, `why` the case's, `menu_refusal.count` +1, the line's words (`line.text`: the selftest role's book), the HUD
          with control. NODATA (no frame: `no_data` -- or `older` if no bench host trailer reaches the receiver cache: K1 reports which),
          OLDER (`guestmenu caps off`: both words s167's 0x0003), ELSEWHERE (`guestmenu host elsewhere`: host_elsewhere), LEAVING
          (`guestmenu frame intent <field>`: leaving), LINK (`netsync stale 1`: link), BATTLE (`netsync lock 1` + `netsync host battle 1`:
          host_battle), SCENE (`netsync lock 1` + `netsync hostscene 1`: scene -- the scene inputs exist only while the bench dialogue
          session holds), HOSTCTL (`netsync lock 1` + `swap hostctl off`: scene, F4), BUSY (`swap intent ALT_FIELD`, a follow in flight:
          control -- StartFollowWarp turns control off as it arms, and term 9 precedes term 10; last: the follow lands on ALT_FIELD, the leg
          warps home). The line is read at the verdict (`verdict_line`: a field load ends the refusal line). LEVER `old`: the own menu
          opens, every case red.
  witness GM0-WITNESS-<c> `frame witness preset|pa|equip|sa|char|bag` (each on a fresh place): refused data_differs, the decline line
          naming 'component <c>', the line 'Your game data differs from your partner's (...)', not seated; -KEYITEM: SEATED, the 'key
          item(s) this install does not know' line; then the Cancel. GM0-SEATFAULT-<c> `seat fault players|party|bag|gil|keyitems`: refused
          `fault` (door_refused.fault +1), opens +0, the HUD with events and control on, the lever spent (one shot), the 'seat faulted at its
          <c> install' line -- and THE ROLLBACK: the next clean seat's fp.before equals the faulted seat's (nothing stayed installed).
  door    GM0-DOOR-FAULT-OPEN (after one clean open / close) `door fault open`: the DOOR refuses `fault` (door_refused.fault +1), FieldHUD,
          events and control on, nothing seated, the lever spent. GM0-DOOR-FAULT-RESTORE `door fault restore` + Cancel: the HUD with the
          record and the seat still held (restore.doors +0); the next press's door retries it first (doors +1) and seats again; its Cancel:
          fp equal, nothing held. GM0-DOOR-889 (the dialogue path) on STRIP_FIELD (30890: the roll-stream bench's persistent [NFOC] HUD
          strip, GM0-HUDSTRIP's -- a window up with control and events on), `frame` (re-arms the bench host there), `host elsewhere`, Menu:
          no press verdict, the DOOR refuses host_elsewhere (door_refused +1), the window gone (a Known limit: measured, never waited for),
          the HUD with events and control on, nothing seated. No `bench 0` / `bench 1`: BenchGates survives the warp.
  close   GM0-DEPTH-<d> `fireclose leave` at the root, Item, Equip, Ability and Status: closes.leave +1, last_close {cause leave, from <d>,
          end done, ms within DEPTH_MS (150 at FadeDuration 40)}, ONE forced-close line (no watchdog), close_line 'menu closed -- following
          your partner.', FieldHUD with events and control on, fp equal. GM0-DEPTH-FAULT `close fault sub` at Item and `close fault root` at
          the root: closes.faults +1, end 'fault', a live HUD with events on, one line each. GM0-CLOSE-IDS `fireclose` each of the eight ids
          (leave out rejoin world cut ending title scene -- the ACTION without its trigger, the S half of GM0-LEAVE, GM0-OUT, GM0-REJOIN,
          GM0-CUT, GM0-TITLE, GM0-SCENE, and `ending` that of GM0-RAMP-FIELD and GM0-RAMP-WORLD, whose ramp the selftest role never
          arms): closes.<id> +1, its words, end done. GM0-REOPEN every forced close reopens (opens +1 each); after a normal Cancel `seated` and `close_pending` clear
          and `fireclose leave` answers 'no seat' (closes +0, no forced-close line); under `guestmenu old` the own menu opens unseated
          (a shot: Order, Card and Config NOT grey -- READ it; FF9's Order acts in place, no screen to judge). LEVER `close old`: no
          close (DEPTH, DEPTH-FAULT, CLOSE-IDS red; the leg's own Cancel restores).
  quit    GM0-QUIT the quit prompt up (`endbench quit on`, the stock Alt+F4 path), `fireclose leave`: the close WAITS past CloseCapMs
          (close_pending, close_step 'quit', still seated, no watchdog line); Cancel by KEY: the close runs (end done), FieldHUD, events and
          control on. LEVER `close old`: never closes.
  quitexit GM0-QUIT-EXIT (DESTRUCTIVE: its own launch, last) seated, the quit prompt, a keyboard Confirm on Quit: the process exits, the
          sandbox's save files unchanged (no save written).
  held    GM0-HELDKEY beside the scribe (a local talk first: the stand's positive control): seated, Confirm HELD through `fireclose
          leave`: `held.bits` carries Confirm, `held.keyon` +0, no talk while held; released, `bench 0`, pressed again: the talk starts (a
          real re-press is a real edge).
  master  GM0-MASTER two sub-screen returns while seated: `master_skipped` +2 (SetMasterSkill never called on the guest's real benched
          characters); `ach_held` reported (which report the menu makes is K1's).
  diorama GM0-DIORAMA-BOOT `dioboot` while seated: REFUSED naming the guest menu, nothing booted. GM0-SILENT (S) inside a booted diorama:
          `menu_refusal.now` 'open' on BattleHUD (the bench keeps s121's step), a Menu press: still BattleHUD, opens +0, nothing open.
  release GM0-RELEASE all twelve levers off their defaults (BW.GUEST_MENU_RELEASE_SET) plus `host elsewhere` on a bench frame, then
          `reset`: every lever at its default, the bench frame and host field dropped, the release line ONCE; a second `reset` with nothing
          set says nothing; re-forced, a NEW `frame` seats ITS marker with the frame's party (`seat skip` released).
  softreset GM0-SOFTRESET (the combo is swallowed inside an open menu -- Session.soft_reset, measured: so the seat is held on a live HUD by
          `door fault restore`): the soft reset reaches the title, restore.backstops.replace +1, nothing seated, no 'should never happen'
          line, and the title takes input (New Game lands).
  cfg     GM0-RAMP-CFG (S) seated, a [Netsync] Role edit against the ini's own (Role = client on this HOST install; IniGuard: backed
          up, restored byte-exact) -- an edge only when the engine logs 'config change applied live' (LoadConfigIfChanged compares the ini
          with its own last read, never the forced role): ApplyConfigChange's own `ending` close -- closes.ending +1, 'menu closed -- the
          co-op session is ending.', the HUD with control on, fp equal; no ramp claim (the selftest role never mirrors). The restore is a
          second edge: after the close, `reset`, `selftest 1`, `bench 1` re-force the role. LEVER `close old`: the menu stays open, red.
  world   GM0-WORLDTAG4 (the S leg of a D row: CR-3's keys) on 9011: `uid0_vars` and `sysvar192` read on WorldHUD, then a seated open, one
          sub-screen round trip (Item), the close with no load: `outside_settled` {set, equal, named null}, fp equal, and `uid0_vars` /
          `sysvar192` read after the settle equal the ones before. LEVER `poke` (gEventGlobal[2047] bit 0 flipped after fp_before's outside
          stamp): outside_settled.equal false, named 'events' -- the judge sees runtime state.
  s       the chain: seat refuse why witness door close quit held master diorama release in ONE launch (never under a calibration).

WHAT NO SOLO LEG REACHES (named, not hidden): every D / T / H row (the key path on a mirroring guest, the real triggers, parity, the
ramps, the stall, the tape); GM0-LOAD (no harness verb injects Alt+F9: the load entry's backstop and the identity drop are the proof's
rows and the stand-in's gm_backstop / gm_load seams -- tests/test_coop_guest_menu.py); GM0-DEATH's kill and relaunch (NO runner or leg
launches it: an open item); GM0-BRACKET's "identical to s167" lines (the diorama legs on the pinned W1a/b DLL: Order step 2) -- its new
seat bracket line is GM0-PROOF's; GM0-DEPTH's character-pick / target-picker / candidate / control-panel depths and its fault leg with a
`swap intent` follow in flight; GM0-RAMP-CFG's Enabled=0 edit (solo_ini already wrote Enabled 0: not an edge on this bench); GM0-SILENT's
Pause read and the design's 'still buzzes and counts' (not judged: judge_silent reads now / ui / opens / open / seated only); GM0-DIORAMA's
open refused while ARMED or RETURNING (no harness verb holds the diorama in either state; the BOOTED half is GM0-SILENT's press).
IN-GAME UNKNOWNS each row reports rather than assumes: the menus' labels (the census plans name them; a wrong path reads "not reached",
never a pass; each try's trail records the group and label every list really opened on), whether the support list opens on a lit SA (A1
/ A2) and Garnet's Cure is lit on the seated copy (A3: the shot), the WHY-NODATA why (K1: the receiver cache on a field), which
achievement report the menu makes (MASTER), FadeDuration (read from [Interface]).
OFFLINE: tests/test_coop_guest_menu_bench.py runs every leg through the REAL Session on the stand-in (fakegame's opt-in `guestmenu` rung):
green where the stand-in models the engine, OLD on the deployed-s167 stand-in, each lever exactly LEVER_PREDICTED, each GUEST_MENU_FAULTS
fault exactly FAULT_REDS; the pure judges red on each wrong shape; and the O rows.

PRECONDITIONS (THE OPERATOR'S): the s168 DLL deployed (nothing here deploys); controllers OFF, nobody at the keyboard, FF9 unfocused;
GM_FIELD and ALT_FIELD (30602) registered; STRIP_FIELD (30890, `door`) registered; the GMBAG bag seeder (BAG_FIELD 30816,
studies/field-coop/s168/bench/gmbag.field.toml, `refuse` / `deep`) registered -- E1 needs a candidate the seated member can wear, I2 the
greens, LOCAL a key item; [Netsync] Enabled 0 + FollowHost 1 written BEFORE launch (solo_ini.py); [Control] SoftReset 1 and [Cheats]
Enabled 1 for `softreset`; never under a running test suite; close the game after a lab.

    py <scratchpad>/solo_ini.py s168-gm -- COOP_GM_LEG=seat py tools/play.py studies/test-harness/scenarios/coop_guest_menu.py --field 30801
    COOP_CALIBRATE=1 COOP_GM_LEG=<leg> [COOP_GM_LEVER=<lever>]   (the same command: OLD on s167, LEVER on s168)
    COOP_GM_LEG=world ... --field 6603                            (the world leg's route)
    COOP_GM_FIELD=<id> / COOP_GM_ALT_FIELD=<id> / COOP_GM_MARKER=<1-9999> move the bench field / the second place / the marker
"""
from __future__ import annotations

import copy
import hashlib
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError


def _bw():
    try:
        from harness import battlewire as bw                 # the driver puts tools/ on sys.path
    except ImportError:                                     # pragma: no cover - imported outside the driver
        sys.path.insert(0, str(cb.REPO / "tools"))
        from harness import battlewire as bw
    return bw


BW = _bw()


def _env_int(name: str, default: int, lo: int = 1, hi: int = 65535) -> int:
    raw = str(os.environ.get(name, "") or "").strip()
    return int(raw) if raw.isdigit() and lo <= int(raw) <= hi else default


# ------------------------------------------------------------------------------------------------ the bench's facts
PROBE = "netsync.guestmenu"
GM_FIELD = _env_int("COOP_GM_FIELD", 30801)          # the journal dashboard (the scribe west, the keeper east)
ALT_FIELD = _env_int("COOP_GM_ALT_FIELD", cb.FIELD)  # 30602 LOCKT2: THE DECLINE LATCH's second place, WHY-BUSY's follow target
FARSHORE, WORLD = 6603, 9011
SCRIBE_AT = (-210.0, -837.0)                         # beside the scribe (a plain window): coop_talk_relay.py's WEST
#: GM0-DOOR-889's field: the roll-stream bench's persistent [NFOC] [[behavior.hud]] strip (GM0-HUDSTRIP's; round_gm_lib.sh exports it)
STRIP_FIELD = _env_int("COOP_GMD_STRIP_FIELD", 30890)
#: GMBAG, the bench bag seeder (D6): Desert Boots (192) first, then Gysahl Greens (251) (a stock key item: BAG_KEY_ITEM), on entry -- the
#: frame copies the guest's count>0 rows and rare sets, so E1 has a candidate every member can wear, I2 the greens, LOCAL a key item
BAG_FIELD = _env_int("COOP_GM_BAG_FIELD", 30816)
BAG_TOML = "studies/field-coop/s168/bench/gmbag.field.toml"
BAG_SITES = ("E1", "I2")                             # the census sites that need the seeded bag (and LOCAL's key read)
BAG_LEGS = ("refuse", "deep")                        # the legs the seeder runs for (the other legs keep the New-Game bag)
BAG_FRAMES = 45                                      # BAG_FIELD's entry grants run (cb.seed_party's COOPPARTY wait)
#: the stock key item GMBAG grants (its key-item id), None while it grants none: gmbag.field.toml's KNOWN GAP -- the kit has no field.toml
#: lane for a stock key item yet (give_item / [[on_entry]] items take 0-255, give_folklore 80-254), and the New-Game bag holds none. While
#: None, LOCAL's key read is not driven: its why names the gap (set it -- Mini-Burmecia, 35, is the toml's pick -- once GMBAG grants one)
BAG_KEY_ITEM = None
MARKER = _env_int("COOP_GM_MARKER", 7, 1, 9998)
MARKER2 = MARKER + 1                                 # GM0-RELEASE's next seat
HUDS = BW.GM_HUD_STATES
OPEN_S = 3.0              # a Menu press -> MainMenu (one HUD fade, the door, the seat, MainMenu's Show) or its refusal
CLOSE_S = 5.0             # a Cancel / a forced close -> the HUD with events back on and the settle stamped
SEL_S = 1.5               # a pick / a Cancel -> its next state
STEP_S = 1.0              # a census plan's step -> its refusal counted
HOLD_S = 0.6              # samples read while seated (CHIP, FREEZE)
SAVE_S = 2.0              # `savemenu` -> a Serialize sample if the chord opened it
QUIT_WAIT_S = (BW.GM_CLOSE_CAP_MS + 1000) / 1000.0   # past CloseCapMs: the quit prompt still holds the close (no watchdog)
EXIT_S = 10.0
CFG_S = 6.0               # an ini edit -> the 2 s config poll + the close
TALK_S = 4.0
HELD_FRAMES = 240         # GM0-HELDKEY: Confirm held this long (through the fireclose and the samples)
SKEW_FRAMES = 2           # THE ORDER SKEW
SETTLE_FRAMES = 20
TWEEN_FRAMES = 30        # an NGUI sub-menu tween holds UIScene.Loading: a key pressed inside it is swallowed
DEPTH_MS_AT_40 = 150      # GM0-DEPTH: FieldHUD within 150 ms at 40 ms fades (the design's)
CONFIRM_MASK = 0x20000 | 0x4000   # EventInput.GetKeyMaskFromControl(Confirm) under New Game's identity mapping (logical | physical)
DETAIL_W = 1400
SUB_SCREENS = ("Item", "Ability", "Equip", "Status")
OPTIONAL_SCREENS = ("Folklore", "Journal")
SERIALIZE = "Serialize"
QUIT_LABELS = ("Quit", "Yes", "OK")

# ------------------------------------------------------------------------------------------------ the legs and rows
LEGS = ("proof", "seat", "refuse", "deep", "why", "witness", "door", "close", "quit", "held", "master", "diorama", "release", "softreset",
        "cfg", "quitexit", "world")
CHAIN = "s"
CHAIN_LEGS = ("seat", "refuse", "why", "witness", "door", "close", "quit", "held", "master", "diorama", "release")
WITNESS_COMPS = (BW.GM_COMP_PRESET, BW.GM_COMP_PA, BW.GM_COMP_EQUIP, BW.GM_COMP_SA, BW.GM_COMP_CHAR, BW.GM_COMP_BAG)
FP_COMPS = tuple(BW.GM_FP_COMP_NAMES)
DEPTHS = ("root",) + SUB_SCREENS
REFUSE_SITES = ("I1", "E1", "A1", "A2")
DEEP_SITES = ("E2", "E3", "A3", "I2")
#: the why cases: (row, the whys the row accepts, the setup ops, the undo ops); each op a (sub, args...) of `netsync`
WHY_CASES = (
    ("GM0-WHY-NODATA", (BW.GM_WHY_NO_DATA, BW.GM_WHY_OLDER), (), ()),
    ("GM0-WHY-OLDER", (BW.GM_WHY_OLDER,), (("guestmenu", "caps", "off"),), (("guestmenu", "caps", "on"),)),
    ("GM0-WHY-ELSEWHERE", (BW.GM_WHY_HOST_ELSEWHERE,), (("guestmenu", "host", "elsewhere"),), (("guestmenu", "host", "here"),)),
    ("GM0-WHY-LEAVING", (BW.GM_WHY_LEAVING,), (("guestmenu", "frame", "intent", "<alt>"),), (("guestmenu", "frame", "<marker>"),)),
    ("GM0-WHY-LINK", (BW.GM_WHY_LINK,), (("stale", 1),), (("stale", 0),)),
    ("GM0-WHY-BATTLE", (BW.GM_WHY_HOST_BATTLE,), (("lock", 1), ("host", "battle", 1)), (("host", "battle", 0), ("lock", 0))),
    # SCENE / HOSTCTL under `netsync lock 1`: _glSceneHere / _glHostHoldsInput are written, and BenchHostTick builds the bench host's
    # state, only while the bench dialogue session holds (NetSyncClient.cs:13146, :13178-13179, :13387-13389) -- unlocked, the press opens
    ("GM0-WHY-SCENE", (BW.GM_WHY_SCENE,), (("lock", 1), ("hostscene", 1)), (("hostscene", 0), ("lock", 0))),
    ("GM0-WHY-HOSTCTL", (BW.GM_WHY_SCENE,), (("lock", 1), ("swap", "hostctl", "off")), (("swap", "hostctl", "on"), ("lock", 0))),
    # a follow in flight: StartFollowWarp turns my control off in the same call that arms it (NetSyncClient.cs:6670 / :6674), and term 9
    # (control) precedes term 10 (busy) -- so the press reads `control`, the follow landing on ALT_FIELD (DESIGN D1)
    ("GM0-WHY-BUSY", (BW.GM_WHY_CONTROL,), (("swap", "intent", "<alt>"),), ()),
)
LEG_ROWS = {
    "proof": (),
    "seat": ("GM0-SEAT", "GM0-CHIP", "GM0-FREEZE", "GM0-BROWSE", "GM0-RESTORE"),
    "refuse": tuple(f"GM0-REFUSE-{s}" for s in REFUSE_SITES) + ("GM0-REFUSE-GREY", "GM0-OUTSIDE"),
    "deep": tuple(f"GM0-REFUSE-{s}" for s in DEEP_SITES) + ("GM0-LOCAL",),
    "why": tuple(c[0] for c in WHY_CASES),
    "witness": tuple(f"GM0-WITNESS-{c.upper()}" for c in WITNESS_COMPS) + ("GM0-WITNESS-KEYITEM",)
               + tuple(f"GM0-SEATFAULT-{c.upper()}" for c in FP_COMPS),
    "door": ("GM0-DOOR-FAULT-OPEN", "GM0-DOOR-FAULT-RESTORE", "GM0-DOOR-889"),
    "close": tuple(f"GM0-DEPTH-{d.upper()}" for d in DEPTHS) + ("GM0-DEPTH-FAULT", "GM0-CLOSE-IDS", "GM0-REOPEN"),
    "quit": ("GM0-QUIT",),
    "quitexit": ("GM0-QUIT-EXIT",),
    "held": ("GM0-HELDKEY",),
    "master": ("GM0-MASTER",),
    "diorama": ("GM0-SILENT", "GM0-DIORAMA-BOOT"),
    "release": ("GM0-RELEASE",),
    "softreset": ("GM0-SOFTRESET",),
    "cfg": ("GM0-RAMP-CFG",),
    "world": ("GM0-WORLDTAG4",),
}
SETUP = {
    "S168-INI": "the install's Memoria.ini, READ-ONLY: [Netsync] Enabled 0 or absent and FollowHost 1 (solo_ini.py, written BEFORE launch: "
                "THE FORCED-ROLE PIN)",
    "S168-S0": "newgame, the COOPPARTY seeder (then the GMBAG bag seeder for the refuse / deep legs), the bench field, encounters off, "
               "`netsync selftest 1` forced",
    "S168-P0": "`netsync.guestmenu` is netsync's LAST key, at BW.GUEST_MENU_SENTINELS' keys in order (every nested block too), the twelve "
               "levers at their defaults, caps.own the stage's word (0x000B)",
    "GM0-PROOF": "the proof block's last three lines in order -- world walk (534 / 198), seat bracket (19 / 7), guest menu (420 / 249), each "
                 "the s168 source's -- none FAIL, and 'main menu refusal selftest: OK (14 rows)' unmoved",
}
P1_TEXT = "`netsync bench 1` accepted, the twelve guestmenu levers at their defaults"
ROWS = {
    "GM0-SEAT": "the bench frame seated: seated, opens +1, seat {src bench, marker m, frame_age_ms >= 0}, the frame line's BENCH<m> lv99 and "
                "gil G, the seat line's marker and gil G, seat_fp's players / party / gil each differ from fp_before's (TWO MARKERS)",
    "GM0-CHIP": "the chip's words on every sample while seated, null after the close",
    "GM0-FREEZE": "event_enable false on every sample while seated, true after the close",
    "GM0-BROWSE": "Item / Ability / Equip / Status (Folklore / Journal if drawn) open their screens and Cancel back; Order / Party / Card / "
                  "Config greyed (nothing opens, refused +0); no Save row; Alt+F5 never opens Serialize; seated throughout, the frame's party",
    "GM0-RESTORE": "two cycles (the browse, a root-only open): fp_after == fp_before, named null, restore.doors +1, outside_equal, seated false",
    "GM0-REFUSE-GREY": "Order / Party / Card / Config greyed while seated: no screen opens, refused +0, captures +0",
    "GM0-OUTSIDE": "across the refusal sweep: fp.outside_equal true, outside_named null, outside_settled equal",
    "GM0-LOCAL": "Auto and manual sort (judged on a measured order change: Arrange, Manual -- rows 0 and 2 swap on the seated copy), the "
                 "key-item read on a seeded key item (its description opened and closed), Folklore: refused +0, captures +0, seated; fp "
                 "equal at the close",
    "GM0-WITNESS-KEYITEM": "`frame witness keyitem`: seated anyway, the 'key item(s) this install does not know' line; the Cancel restores",
    "GM0-DOOR-FAULT-OPEN": "after one clean open / close, `door fault open`: the DOOR refuses `fault` (door_refused.fault +1), the HUD with "
                           "events and control on, nothing seated, the lever spent",
    "GM0-DOOR-FAULT-RESTORE": "`door fault restore` + Cancel: the HUD with the record held (doors +0); the next door retries (doors +1) and "
                              "seats; its Cancel: fp equal, nothing held",
    "GM0-DOOR-889": "on the strip field (a persistent [NFOC] strip up with control and events on), `frame`, `host elsewhere`, Menu: the "
                    "dialogue path (no press verdict), the DOOR refuses host_elsewhere (door_refused +1), the window gone, the HUD with "
                    "events and control on, nothing seated",
    "GM0-DEPTH-FAULT": "`close fault sub` at Item and `close fault root` at the root: closes.faults +1, end fault, a live HUD with events on, "
                       "one line each",
    "GM0-CLOSE-IDS": "`fireclose` each of the eight ids: closes.<id> +1, its words on close_line, end done",
    "GM0-REOPEN": "every forced close reopens (opens +1 each); after a Cancel nothing held and `fireclose leave` answers 'no seat' (closes +0, "
                  "no line); under `guestmenu old` the own menu opens unseated (a shot: Order not grey)",
    "GM0-QUIT": "the quit prompt holds a `fireclose leave` past CloseCapMs (pending, step quit, seated, no watchdog line); Cancel by key: the "
                "close ends done, the HUD with events and control on",
    "GM0-QUIT-EXIT": "seated, the quit prompt, a keyboard Confirm on Quit: the process exits; the sandbox saves unchanged",
    "GM0-HELDKEY": "Confirm held through `fireclose leave`: held.bits carries Confirm, held.keyon +0, no talk; released and pressed again "
                   "(bench 0): the talk starts",
    "GM0-MASTER": "two sub-screen returns while seated: master_skipped +2 (ach_held reported)",
    "GM0-DIORAMA-BOOT": "`dioboot` while seated: REFUSED naming the guest menu, nothing booted, still seated",
    "GM0-SILENT": "inside a booted diorama: menu_refusal.now 'open' on BattleHUD; a Menu press: still BattleHUD, opens +0, nothing open",
    "GM0-RELEASE": "the twelve levers + `host elsewhere` + a frame set, `reset`: every lever at its default, the bench frame dropped, ONE "
                   "release line; a bare `reset` says nothing; a NEW frame seats its marker with the frame's party",
    "GM0-SOFTRESET": "the seat held on a live HUD (`door fault restore`), the soft reset: the title, backstops.replace +1, nothing seated, no "
                     "'should never happen' line, New Game lands",
    "GM0-RAMP-CFG": "seated, a [Netsync] Role edit against the ini's own (Role = client on this HOST install), heard live ('config change "
                    "applied live'): closes.ending +1, its words, the HUD with control on, fp equal",
    "GM0-WORLDTAG4": "on 9011: a seated open, Item and back, the close with no load: outside_settled {set, equal, named null}, fp equal, "
                     "uid0_vars and sysvar192 after the settle equal the ones before",
}
for _s in REFUSE_SITES + DEEP_SITES:
    ROWS[f"GM0-REFUSE-{_s}"] = (f"the {_s} confirm while seated: refused +1, captures +1, passes +0, last_site {_s}, the screen, impactful 0, "
                                "seated, Cancel back to the root, one census line; fp equal at the close")
for _row, _whys, _ops, _undo in WHY_CASES:
    ROWS[_row] = (f"a Menu press after {' + '.join(' '.join(map(str, o)) for o in _ops) or 'no frame'}: refused audibly at the press "
                  f"(why {' or '.join(_whys)}), opens +0, not seated, menu_refusal.count +1, the line's words, the HUD with control")
ROWS["GM0-WHY-BUSY"] += " (a follow in flight: the follow lands on ALT_FIELD)"
for _c in WITNESS_COMPS:
    ROWS[f"GM0-WITNESS-{_c.upper()}"] = (f"`frame witness {_c}` on a fresh place: refused data_differs, the decline line naming 'component "
                                         f"{_c}', the line's words, not seated, opens +0")
for _c in FP_COMPS:
    ROWS[f"GM0-SEATFAULT-{_c.upper()}"] = (f"`seat fault {_c}`: refused fault (door_refused.fault +1), opens +0, the HUD with events and "
                                           f"control on, the lever spent, the 'faulted at its {_c} install' line; the next seat's fp.before "
                                           "equals the faulted seat's")
for _d in DEPTHS:
    ROWS[f"GM0-DEPTH-{_d.upper()}"] = (f"`fireclose leave` at {_d}: closes.leave +1, last_close {{leave, from {_d}, end done, within "
                                       "DEPTH_MS}, one line, its words, the HUD with events and control on, fp equal")
FINAL = {"S168-R": "`reset` releases the role and every guestmenu lever ('guestmenu levers released (with the harness)' once); the twelve "
                   "levers at their defaults, the bench frame dropped"}
CAL_TEXT = ("THE CAL RULE: exactly the predicted reds (OLD on s167: the setup's and every leg row; a lever on s168: LEVER_PREDICTED; NEW: "
            "none), each predicted row MEASURING its shape")
#: [calibration] the levers per leg (COOP_GM_LEVER; unset = the leg's first), their ops, and what each predicts red -- each predicted row
#: MEASURING its shape (MEASURE)
LEG_LEVERS = {"proof": (), "seat": ("old", "skip", "chip", "events") + tuple(f"restore:{c}" for c in FP_COMPS),
              "refuse": ("old", "capture", "poke"), "deep": ("old", "capture"), "why": ("old",), "witness": ("old",), "door": ("old",),
              "close": ("old", "closeold"), "quit": ("old", "closeold"), "held": ("old",), "master": ("old",), "diorama": ("old",),
              "release": (), "softreset": ("old",), "cfg": ("old", "closeold"), "quitexit": (), "world": ("old", "poke")}
LEVER_OPS = {"old": ("old",), "skip": ("seat", "skip", "party"), "chip": ("chip", "off"), "events": ("events", "on"),
             "capture": ("capture", "off"), "poke": ("poke",), "closeold": ("close", "old"),
             **{f"restore:{c}": ("restore", "skip", c) for c in FP_COMPS}}
#: each lever read back on `netsync.guestmenu.lever` (field, word)
LEVER_READ = {"old": ("menu", "old"), "skip": ("seat_skip", "party"), "chip": ("chip", "off"), "events": ("events", "on"),
              "capture": ("capture", "off"), "poke": ("poke", "armed"), "closeold": ("close", "old"),
              **{f"restore:{c}": ("restore_skip", c) for c in FP_COMPS}}
LEVER_PREDICTED = {
    **{(leg, "old"): tuple(r for r in LEG_ROWS[leg] if r != "GM0-SILENT") for leg in LEG_ROWS if "old" in LEG_LEVERS[leg]},
    ("seat", "skip"): ("GM0-SEAT", "GM0-BROWSE"), ("seat", "chip"): ("GM0-CHIP",), ("seat", "events"): ("GM0-FREEZE",),
    **{("seat", f"restore:{c}"): ("GM0-RESTORE",) for c in FP_COMPS},
    ("refuse", "capture"): tuple(f"GM0-REFUSE-{s}" for s in REFUSE_SITES), ("refuse", "poke"): ("GM0-OUTSIDE",),
    ("deep", "capture"): tuple(f"GM0-REFUSE-{s}" for s in DEEP_SITES),
    ("close", "closeold"): tuple(f"GM0-DEPTH-{d.upper()}" for d in DEPTHS) + ("GM0-DEPTH-FAULT", "GM0-CLOSE-IDS"),
    ("quit", "closeold"): ("GM0-QUIT",), ("cfg", "closeold"): ("GM0-RAMP-CFG",), ("world", "poke"): ("GM0-WORLDTAG4",),
}
#: [calibration] OLD on s167: the setup rows that read red there (the key and the proof lines absent), then every leg row
OLD_SETUP_RED = ("S168-P0", "GM0-PROOF", "S168-P1")
#: the shape each predicted row MEASURES (OLD's / the lever's) -- a row merely red is not the shape (a failed landing is red too)
MEASURE = {
    "old": "s121's bench reading: menu_refusal.now 'open' on the HUD and a Menu press opening the OWN menu unseated (`open` true, `seated` "
           "false; on s167 MainMenu with no `guestmenu` key)",
    "skip": "seated with seat_fp's players and party EQUAL to fp_before's (the guest's own party drawn)",
    "chip": "seated with no chip",
    "events": "event_enable true while seated",
    "capture": "the census passed: refused +0, passes +1, impactful > 0",
    "poke": "outside named 'events' at the close",
    "closeold": "no forced close: the fireclose answered `close old`, the menu still seated, closes +0",
    **{f"restore:{c}": f"fp named '{c}' at the close" for c in FP_COMPS},
}
#: the stand-in's GUEST_MENU_FAULTS -> exactly the S rows each turns red, by leg, each leg launched as these keys group them (tests pin it:
#: the field legs of one fault in ONE launch, the world leg alone). The client-only faults (the real triggers, an unmirrored / stalled guest,
#: the dialogue path's mirroring drop, Pause) and slot_keyed (the bench frame's members sit in the guest's own slots) redden no S row: the
#: selftest role proves the ACTION only. restore_skip is pinned on the legs where its restore is the FIRST over the guest's own state (a later
#: seat over a copy the skip left installed folds the same content again -- the chain reddens more rows, in its own order); settle_same_frame
#: reddens nothing until a tag-4 write is modelled (the tests' gm_tag4_event: then the miss reads GREEN, the row's own falsifier)
FAULT_REDS = {
    "capture_leak": {"refuse": tuple(f"GM0-REFUSE-{s}" for s in REFUSE_SITES)},
    "restore_skip": {"seat": ("GM0-RESTORE",), "world": ("GM0-WORLDTAG4",)},
    "cut_ignored": {}, "leave_ignored": {}, "scene_ignored": {}, "title_ignored": {}, "pause_closed": {}, "unmirrored_open": {},
    "stall_open": {}, "dialog_drop_lifted": {},
    "caps_ignored": {"why": ("GM0-WHY-NODATA", "GM0-WHY-OLDER")},         # no caps term: NODATA reads host_busy, OLDER opens
    "seat_at_press": {"door": ("GM0-DOOR-FAULT-OPEN", "GM0-DOOR-FAULT-RESTORE")},   # no door: neither the fault nor the retry runs there
    "quit_under_close": {"quit": ("GM0-QUIT",)},
    "slot_keyed": {},
    "own_values": {"seat": ("GM0-SEAT", "GM0-BROWSE"), "release": ("GM0-RELEASE",)},
    "release_skip": {"release": ("GM0-RELEASE", "S168-R")},               # the final reset keeps `seat skip` too
    "settle_same_frame": {},
    "guest_menu_proof_fail": {leg: ("GM0-PROOF",) for leg in LEGS},
}


def _legs(raw) -> tuple | None:
    """COOP_GM_LEG: `s` = the chain; else the named legs (comma-separated); None when it names none."""
    names = [p.strip() for p in str(raw or "").lower().split(",") if p.strip()]
    if CHAIN in names:
        return CHAIN_LEGS
    picked = tuple(x for x in LEGS if x in names)
    return picked or None


_RAW_LEG = os.environ.get("COOP_GM_LEG", "seat")
SOLO_LEGS = _legs(_RAW_LEG)
LEVER_RAW = (os.environ.get("COOP_GM_LEVER") or "").strip().lower() or None


def lever_of(leg: str, raw):
    """The calibration lever for ``leg``: ``raw`` when it is one of the leg's, the leg's first when ``raw`` is None; else None."""
    levers = LEG_LEVERS.get(leg, ())
    if raw is None:
        return levers[0] if levers else None
    return raw if raw in levers else None


def leg_rows(legs) -> tuple:
    return tuple(r for leg in LEGS if leg in legs for r in LEG_ROWS[leg])


def catalog(legs, lever=None, *, calibrate: bool = False) -> dict:
    c = dict(SETUP)
    c["S168-P1"] = P1_TEXT + (f" -- and the CALIBRATION lever `guestmenu {' '.join(LEVER_OPS[lever])}` pulled and read back (held through "
                              "the run)" if calibrate and lever in LEVER_OPS else "")
    c.update({r: ROWS[r] for r in leg_rows(legs)})
    if "quitexit" not in legs:
        c.update(FINAL)
    c["S168-CAL"] = CAL_TEXT
    return c


def old_predicted(legs) -> tuple:
    """OLD (PURE): s167 -- the setup's three and every leg row."""
    return OLD_SETUP_RED + leg_rows(legs)


def lever_predicted(leg: str, lever) -> tuple:
    return tuple(LEVER_PREDICTED.get((leg, lever), ())) if lever else ()


# ------------------------------------------------------------------------------------------------ the pure readers
def _gm(x) -> dict:
    v = cb.path(x, PROBE) if x is not None else None
    return v if isinstance(v, dict) else {}


def _mr(x) -> dict:
    v = cb.path(x, "netsync.menu_refusal") if x is not None else None
    return v if isinstance(v, dict) else {}


def snap(st) -> dict:
    """The bench's view of one state: what every judge reads (the state's own objects copied: a later publish never edits it)."""
    if st is None:
        return {"frame": None, "ui": None, "field": None, "control": False, "dialog": False, "gm": {}, "mr": {}, "world": None,
                "label": None, "group": None, "booted": False, "fading": False, "save": None}
    return {"frame": getattr(st, "frame", None), "ui": getattr(st, "ui_state", None), "field": getattr(st, "field_id", None),
            "control": bool(getattr(st, "control", False)), "dialog": bool(getattr(st, "dialog_open", False)),
            "gm": copy.deepcopy(_gm(st)), "mr": dict(_mr(st)), "world": getattr(st, "world_id", None),
            "label": getattr(st, "menu_label", None), "group": getattr(st, "menu_group", None),
            "booted": bool(cb.dio(st).get("booted")), "fading": bool(getattr(st, "fading", False)), "save": cb.raw(st).get("save_path")}


def _n(s: dict, *path, default=0):
    cur = s.get("gm", {})
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _d(a: dict, b: dict, *path) -> int:
    """b - a of a numeric guestmenu field (0 when either is missing)."""
    try:
        return int(_n(b, *path)) - int(_n(a, *path))
    except (TypeError, ValueError):
        return 0


def _door_total(s: dict) -> int:
    dr = _n(s, "door_refused", default={}) or {}
    return sum(int(v) for v in dr.values() if isinstance(v, int))


def _comps_before(s: dict) -> dict:
    comps = _n(s, "fp", "components", default=None) or {}
    return {k: (v or {}).get("before") for k, v in comps.items()}


def _comps_seat(s: dict) -> dict:
    return dict(_n(s, "seat_fp", "components", default=None) or {})


def _lines(lines, needle: str) -> list:
    return [ln for ln in lines if needle in ln]


_RX_FRAME = re.compile(r"guestmenu frame (\d+) -- a two-marker bench host frame .*? as (BENCH\d+) lv99, .*?gil (\d+)")
_RX_SEATED = re.compile(r"seated the host's party from the bench frame \(marker (\d+)\) -- (\d+) member\(s\), (\d+) bag row\(s\), "
                        r"(\d+) key item\(s\), gil (\d+)")
_RX_ALARM = "(should never happen)"


def frame_line(lines, marker: int):
    """The last `guestmenu frame <marker>` ack in ``lines``: (name, gil) or None."""
    hit = None
    for ln in lines:
        m = _RX_FRAME.search(ln)
        if m and int(m.group(1)) == int(marker):
            hit = (m.group(2), int(m.group(3)))
    return hit


def seat_line(lines, marker: int):
    hit = None
    for ln in lines:
        m = _RX_SEATED.search(ln)
        if m and int(m.group(1)) == int(marker):
            hit = int(m.group(5))
    return hit


# ------------------------------------------------------------------------------------------------ the pure judges
def judge_probe(st) -> tuple:
    """S168-P0 (PURE)."""
    ns = cb.path(st, "netsync") or {}
    if not isinstance(ns, dict) or "guestmenu" not in ns:
        return False, "absent: no `netsync.guestmenu` -- an engine before s168 (the `guestmenu` verb unknown: nothing sent)"
    gm = ns["guestmenu"]
    why = []
    if list(ns)[-1] != "guestmenu":
        why.append(f"netsync's last key {list(ns)[-1]!r} (want guestmenu)")
    if list(gm) != list(BW.GUEST_MENU_KEYS):
        why.append(f"keys {list(gm)} (want {list(BW.GUEST_MENU_KEYS)})")
    for k, v in BW.GUEST_MENU_SENTINELS.items():
        if isinstance(v, dict) and list(gm.get(k) or {}) != list(v):
            why.append(f"{k} {list(gm.get(k) or {})} (want {list(v)})")
    if list((gm.get("restore") or {}).get("backstops") or {}) != list(BW.GUEST_MENU_SENTINELS["restore"]["backstops"]):
        why.append("restore.backstops' keys")
    if (gm.get("lever") or {}) != BW.GUEST_MENU_LEVER_DEFAULTS:
        why.append(f"lever {gm.get('lever')} (want the defaults {BW.GUEST_MENU_LEVER_DEFAULTS})")
    own, want = (gm.get("caps") or {}).get("own"), BW.ww_own_caps_want(ns)
    if own != want:
        why.append(f"caps.own {own!r} (want {want})")
    return not why, ("; ".join(why) or f"guestmenu last, {len(gm)} keys at the sentinels', the levers at rest, caps.own {own}")


def _proof_hits(lines, rx: str) -> list:
    r = re.compile(rx)
    return [(i, int(m.group(1)), int(m.group(2))) for i, m in ((i, r.search(ln)) for i, ln in enumerate(lines)) if m]


def judge_proof(lines, want_ww, want_sb, want_gm) -> tuple:
    """GM0-PROOF (PURE): the three lines present with their wants, in the block's order (world walk < seat bracket < guest menu), none FAIL,
    and s121's menu refusal line at its 14 rows."""
    ww = _proof_hits(lines, BW.WORLD_WALK_PROOF_RE)
    sb = _proof_hits(lines, BW.SEAT_BRACKET_PROOF_RE)
    gm = _proof_hits(lines, BW.GUEST_MENU_PROOF_RE)
    fails = sum(cb.count(lines, h + "FAIL") for h in BW.PROOF_ORDER_S168)
    menu14 = cb.count(lines, BW.proof_ok(BW.PROOF_MENU, BW.MENU_SELFTEST_ROWS)) > 0
    got = {"ww": [(n, m) for _i, n, m in ww], "sb": [(n, m) for _i, n, m in sb], "gm": [(n, m) for _i, n, m in gm]}
    have = (tuple(want_ww) in got["ww"]) and (tuple(want_sb) in got["sb"]) and (tuple(want_gm) in got["gm"])
    order = bool(ww and sb and gm) and ww[-1][0] < sb[-1][0] < gm[-1][0]
    ok = have and order and not fails and menu14
    return ok, (f"world walk {got['ww'] or 'NONE'} (want {tuple(want_ww)}), seat bracket {got['sb'] or 'NONE'} (want {tuple(want_sb)}), "
                f"guest menu {got['gm'] or 'NONE'} (want {tuple(want_gm)}); in order {order}; FAIL lines {fails}; menu refusal 14 rows {menu14}")


def judge_rest(st, want: dict) -> tuple:
    """S168-P1 (PURE): the bench on and each lever in ``want`` (the defaults, or with the calibration lever) read back."""
    gm = _gm(st)
    if not gm:
        return False, "absent: no `netsync.guestmenu` (OLD): no guestmenu lever readable, none sent"
    lever = gm.get("lever") or {}
    bad = {k: (lever.get(k), v) for k, v in want.items() if lever.get(k) != v}
    bench = cb.path(st, "netsync.bench")
    return (not bad and bench is True), f"levers {lever}; off their want {bad or 'none'}; netsync.bench {bench!r}"


def judge_seat(base: dict, s: dict, lines, marker: int) -> tuple:
    """GM0-SEAT (PURE)."""
    if not _n(s, "seated", default=False):
        return False, f"not seated (ui {s.get('ui')!r}, open {_n(s, 'open', default=None)!r}, why {_n(s, 'why', default=None)!r})"
    seat = _n(s, "seat", default={}) or {}
    fl, sg = frame_line(lines, marker), seat_line(lines, marker)
    before, seated = _comps_before(s), _comps_seat(s)
    drawn = {c: seated.get(c) is not None and seated.get(c) != before.get(c) for c in ("players", "party", "gil")}
    ok = (_d(base, s, "opens") == 1 and seat.get("src") == BW.GM_SEAT_SRC_BENCH and seat.get("marker") == marker
          and int(seat.get("frame_age_ms", -1)) >= 0 and fl is not None and fl[0] == BW.gm_bench_name(marker) and sg is not None
          and sg == fl[1] and all(drawn.values()) and s.get("ui") == "MainMenu")
    return ok, (f"opens +{_d(base, s, 'opens')}, seat {seat}, frame line {fl}, seat line gil {sg}, seat_fp differs from fp_before "
                f"{drawn} (TWO MARKERS: the frame's party drawn), ui {s.get('ui')!r}")


def seat_skip_measured(s: dict) -> bool:
    """LEVER `seat skip party` (PURE): seated with seat_fp's players and party EQUAL to fp_before's (the guest's own party drawn)."""
    before, seated = _comps_before(s), _comps_seat(s)
    return bool(_n(s, "seated", default=False)) and all(seated.get(c) is not None and seated.get(c) == before.get(c)
                                                      for c in ("players", "party"))


def judge_chip(open_samples, closed: dict) -> tuple:
    """GM0-CHIP (PURE)."""
    seated = [s for s in open_samples if _n(s, "seated", default=False)]
    chips = sorted({str(_n(s, "chip", default=None)) for s in seated})
    ok = bool(seated) and all(_n(s, "chip", default=None) == BW.GM_CHIP_VIEW_ONLY for s in seated) and _n(closed, "chip", default=0) is None \
        and not _n(closed, "seated", default=True)
    return ok, f"{len(seated)} seated samples, chips {chips}; after the close chip {_n(closed, 'chip', default=None)!r}"


def chip_off_measured(open_samples) -> bool:
    seated = [s for s in open_samples if _n(s, "seated", default=False)]
    return bool(seated) and all(_n(s, "chip", default=0) is None for s in seated)


def judge_freeze(open_samples, closed: dict) -> tuple:
    """GM0-FREEZE's S half (PURE)."""
    seated = [s for s in open_samples if _n(s, "seated", default=False)]
    on = [s.get("frame") for s in seated if _n(s, "event_enable", default=None) is not False]
    ok = bool(seated) and not on and _n(closed, "event_enable", default=None) is True and not _n(closed, "seated", default=True)
    return ok, (f"{len(seated)} seated samples, event_enable true on {on or 'none'}; after the close event_enable "
                f"{_n(closed, 'event_enable', default=None)!r}, seated {_n(closed, 'seated', default=None)!r}")


def events_on_measured(open_samples) -> bool:
    seated = [s for s in open_samples if _n(s, "seated", default=False)]
    return bool(seated) and all(_n(s, "event_enable", default=None) is True for s in seated)


def judge_browse(visits: list, greys: list, labels: list, save: dict, open_snap: dict) -> tuple:
    """GM0-BROWSE (PURE). ``visits`` [{label, found, state, back, seated}], ``greys`` [{label, state, refused_delta, seated}], ``save``
    {serialize, seated}."""
    why = []
    req = {v["label"]: v for v in visits}
    for lbl in SUB_SCREENS:
        v = req.get(lbl)
        if v is None or not v.get("found") or v.get("state") in (None, "MainMenu") or not v.get("back") or not v.get("seated"):
            why.append(f"{lbl}: {v}")
    for v in visits:
        if v["label"] in OPTIONAL_SCREENS and v.get("found") and (v.get("state") in (None, "MainMenu") or not v.get("back")):
            why.append(f"{v['label']}: {v}")
    if not greys:
        why.append("no greyed row drawn (Order / Party / Card / Config)")
    for gr in greys:
        if not gr.get("picked") or gr.get("state") != "MainMenu" or gr.get("refused_delta") != 0 or not gr.get("seated"):
            why.append(f"grey {gr}")
    if any(str(lb).strip().lower() == "save" for lb in labels):
        why.append(f"a Save row on the root {labels}")
    if save.get("serialize") or not save.get("seated"):
        why.append(f"Alt+F5 {save}")
    if not seat_drawn(open_snap):
        why.append("the seated party is the guest's own (seat_fp's players / party equal fp_before's)")
    return not why, ("; ".join(why) or f"screens {[(v['label'], v.get('state')) for v in visits]}, greyed {[g['label'] for g in greys]} "
                                       f"(nothing opened, refused +0), root {labels}, Alt+F5 refused")


def seat_drawn(s: dict) -> bool:
    before, seated = _comps_before(s), _comps_seat(s)
    return all(seated.get(c) is not None and seated.get(c) != before.get(c) for c in ("players", "party"))


def restore_ok(base: dict, closed: dict) -> tuple:
    """One open / close cycle's restore (PURE): (ok, named, detail)."""
    fp = _n(closed, "fp", default={}) or {}
    ok = (bool(fp.get("equal")) and fp.get("named") is None and fp.get("before") is not None and fp.get("before") == fp.get("after")
          and bool(fp.get("outside_equal")) and _d(base, closed, "restore", "doors") == 1 and not _n(closed, "seated", default=True)
          and closed.get("ui") in HUDS)
    return ok, fp.get("named"), (f"fp equal {fp.get('equal')!r} named {fp.get('named')!r} ({fp.get('before')} -> {fp.get('after')}), "
                                 f"outside_equal {fp.get('outside_equal')!r}, doors +{_d(base, closed, 'restore', 'doors')}, seated "
                                 f"{_n(closed, 'seated', default=None)!r}, ui {closed.get('ui')!r}")


def judge_restore(cycles: list) -> tuple:
    """GM0-RESTORE (PURE): every cycle ((base, closed)) restores; at least two (the browse, the root-only)."""
    res = [restore_ok(b, c) for b, c in cycles]
    ok = len(res) >= 2 and all(r[0] for r in res)
    return ok, " | ".join(f"cycle {i + 1}: {r[2]}" for i, r in enumerate(res)) or "no cycle ran"


def restore_skip_measured(cycles: list, comp: str) -> bool:
    """LEVER `restore skip <comp>` (PURE): a cycle's fp names ``comp`` (a skipped family whose seated copy differs from the guest's own:
    a later cycle over a copy the first left installed can read equal, and `keyitems` differs only on the witness-keyitem cycle)."""
    return any(restore_ok(b, c)[1] == comp for b, c in cycles)


def judge_site(site: str, rec: dict, closed: dict, lines) -> tuple:
    """GM0-REFUSE-<site> (PURE). ``rec`` {reached, why, before, after, back, screen}."""
    if not rec.get("reached"):
        return False, f"not reached: {rec.get('why')}"
    a, b = rec["before"], rec["after"]
    ref = _n(b, "refused", default={}) or {}
    census = cb.count(lines, BW.log_gm_census(BW.GM_CENSUS_NAMES.index(site), str(ref.get("last_screen")))) if site in BW.GM_CENSUS_NAMES \
        else 0
    fp_ok = bool((_n(closed, "fp", default={}) or {}).get("equal"))
    ok = (_d(a, b, "refused", "count") == 1 and _d(a, b, "captures") == 1 and _d(a, b, "passes") == 0 and ref.get("last_site") == site
          and ref.get("last_screen") not in (None, "MainMenu") and _n(b, "impactful", default=-1) == 0 and _n(b, "seated", default=False)
          and rec.get("back") and census == 1 and fp_ok)
    return ok, (f"refused +{_d(a, b, 'refused', 'count')} captures +{_d(a, b, 'captures')} passes +{_d(a, b, 'passes')}, last "
                f"{ref.get('last_site')!r} on {ref.get('last_screen')!r}, impactful {_n(b, 'impactful', default=None)!r}, seated "
                f"{_n(b, 'seated', default=None)!r}, back to the root {rec.get('back')}, census lines {census}; at the close fp equal {fp_ok}")


def capture_off_measured(rec: dict) -> bool:
    a, b = rec.get("before") or {}, rec.get("after") or {}
    return bool(rec.get("reached_pass")) and _d(a, b, "refused", "count") == 0 and _d(a, b, "passes") >= 1 and \
        int(_n(b, "impactful", default=0) or 0) > 0


def judge_grey(greys: list) -> tuple:
    if not greys:
        return False, "not reached: no greyed row drawn on the root (Order / Party / Card / Config)"
    bad = [gr for gr in greys if not gr.get("picked") or gr.get("state") != "MainMenu" or gr.get("refused_delta") != 0
           or gr.get("captures_delta") != 0
           or not gr.get("seated")]
    return not bad, f"greyed {[gr['label'] for gr in greys]}: {bad or 'none opened, refused +0, captures +0'}"


def judge_outside(closed: dict) -> tuple:
    fp, se = _n(closed, "fp", default={}) or {}, _n(closed, "outside_settled", default={}) or {}
    ok = bool(fp.get("outside_equal")) and fp.get("outside_named") is None and bool(se.get("set")) and bool(se.get("equal")) \
        and se.get("named") is None and not _n(closed, "seated", default=True)
    return ok, (f"outside_equal {fp.get('outside_equal')!r} named {fp.get('outside_named')!r}; outside_settled {se}; seated "
                f"{_n(closed, 'seated', default=None)!r}")


def poke_measured(closed: dict) -> bool:
    return (_n(closed, "fp", default={}) or {}).get("outside_named") == "events" or \
        (_n(closed, "outside_settled", default={}) or {}).get("named") == "events"


def swap_measured(rec: dict) -> bool:
    """(PURE) a manual swap MEASURED (_manual_swap's record): two different labels read -- l0 under the cursor on row0, l2 two rows on, on
    row2 -- and, after the swap, the cursor sits on row2 (JumpToIndex: the move's target) and that row reads l0. The ROW is judged as well
    as the label: a move whose down never registered swaps row 0 with itself and lands the cursor back on row 0, which also reads l0
    (ItemUI.cs:468-474). Rows are the pool objects' names, `menu_selected` ('Item 0' / 'Item 2', RecycleListPopulator.cs:308)."""
    l0, l2 = rec.get("l0"), rec.get("l2")
    r0, r2 = rec.get("row0"), rec.get("row2")
    return (bool(l0) and bool(l2) and l0 != l2 and rec.get("swapped") == l0
            and bool(r0) and bool(r2) and r0 != r2 and rec.get("swapped_row") == r2)


def judge_local(recs: list, closed: dict) -> tuple:
    """GM0-LOCAL (PURE): every read reached, none refused / captured / unseated; the sort MEASURED (the `sort` rec's swap_measured); the
    `key items` rec's description opened and closed; fp equal at the close. Every rec's trail rides the detail."""
    trails = "; ".join(f"{r.get('what')} {r.get('trail')}" for r in recs if r.get("trail"))
    tail = f" [trail: {trails[:500]}]" if trails else ""
    sort = [r for r in recs if r.get("what") == "sort"]
    swapped = bool(sort) and all(swap_measured(r) for r in sort)
    s0 = (sort or [{}])[0]
    swap_txt = (f"the manual swap {s0.get('l0')!r} <-> {s0.get('l2')!r} (rows {s0.get('row0')!r} / {s0.get('row2')!r}), the cursor "
                f"after it {s0.get('swapped')!r} on {s0.get('swapped_row')!r}: measured {swapped}")
    if not recs or not all(r.get("reached") for r in recs):
        return False, (f"not reached: {[(r.get('what'), r.get('why')) for r in recs if not r.get('reached')] or 'no step'}; "
                       f"{swap_txt}{tail}")
    bad = [r["what"] for r in recs if _d(r["before"], r["after"], "refused", "count") or _d(r["before"], r["after"], "captures")
           or not _n(r["after"], "seated", default=False)]
    keys = [r for r in recs if r.get("what") == "key items"]
    described = bool(keys) and all(bool(r.get("opened")) and bool(r.get("closed")) for r in keys)
    fp_ok = bool((_n(closed, "fp", default={}) or {}).get("equal"))
    k0 = (keys or [{}])[0]
    return (not bad and swapped and described and fp_ok), (
        f"{[r['what'] for r in recs]}: refused / captured / unseated on {bad or 'none'}; {swap_txt} (Manual row "
        f"{s0.get('manual_label')!r}); "
        f"the key item {k0.get('key_label')!r}: description opened {k0.get('opened')!r}, closed {k0.get('closed')!r}; at the close fp "
        f"equal {fp_ok}{tail}")


def judge_why(whys: tuple, base: dict, s: dict) -> tuple:
    """GM0-WHY-x (PURE): the press refused audibly with one of ``whys``. The line is the settled sample's, else the one read AT the verdict
    (press_menu's `verdict_line`: a field load ends the refusal line before the HUD settles). A count +0 marks the `why` stale: `why` is
    the LAST refusal's book (NoteRefusal its only writer), so with no refusal this press it is an earlier press's."""
    line = (_n(s, "line", default={}) or {}).get("text") or s.get("verdict_line")
    why = _n(s, "why", default=None)
    want_line = {BW.gm_refusal_line_rule(w) for w in whys}
    count = int(s.get("mr", {}).get("count", 0) or 0) - int(base.get("mr", {}).get("count", 0) or 0)
    ok = (why in whys and not _n(s, "seated", default=True) and _d(base, s, "opens") == 0 and count == 1 and line in want_line
          and s.get("ui") in HUDS and s.get("control"))
    stale = " (stale: no refusal this press)" if count == 0 else ""
    return ok, (f"why {why!r}{stale} (want {' or '.join(whys)}), seated {_n(s, 'seated', default=None)!r}, opens +{_d(base, s, 'opens')}, "
                f"menu_refusal.count +{count}, line {line!r}, ui {s.get('ui')!r}, control {s.get('control')}")


def judge_witness(comp: str, base: dict, s: dict, lines) -> tuple:
    """GM0-WITNESS-<comp> (PURE)."""
    named = cb.count(lines, f"component {comp}")
    line = (_n(s, "line", default={}) or {}).get("text") or ""
    ok = (_n(s, "why", default=None) == BW.GM_WHY_DATA_DIFFERS and not _n(s, "seated", default=True) and _d(base, s, "opens") == 0
          and named >= 1 and line.startswith(BW.GM_LINE_PREFIX + "Your game data differs from your partner's") and s.get("ui") in HUDS)
    return ok, (f"why {_n(s, 'why', default=None)!r}, seated {_n(s, 'seated', default=None)!r}, opens +{_d(base, s, 'opens')}, "
                f"'component {comp}' lines {named}, line {line!r}")


def judge_keyitem(open_snap: dict, closed: dict, lines) -> tuple:
    unknown = cb.count(lines, "key item(s) this install does not know")
    ok, _named, detail = restore_ok(open_snap, closed) if closed else (False, None, "no close")
    seated = bool(_n(open_snap, "seated", default=False))
    return (seated and unknown >= 1 and ok), f"seated {seated}, unknown-key lines {unknown}; the close: {detail}"


def judge_seatfault(comp: str, base: dict, s: dict, lines, fp_before_next) -> tuple:
    """GM0-SEATFAULT-<comp> (PURE): ``fp_before_next`` the NEXT clean seat's fp.before (THE ROLLBACK)."""
    faulted = cb.count(lines, f"the seat faulted at its {comp} install")
    lever = (_n(s, "lever", default={}) or {}).get("seat_fault")
    fpb = (_n(s, "fp", default={}) or {}).get("before")
    ok = (_n(s, "why", default=None) == BW.GM_WHY_FAULT and _d(base, s, "door_refused", "fault") == 1 and _d(base, s, "opens") == 0
          and not _n(s, "seated", default=True) and s.get("ui") in HUDS and s.get("control") and _n(s, "event_enable", default=None) is True
          and lever == "off" and faulted >= 1 and fpb is not None and fp_before_next == fpb)
    return ok, (f"why {_n(s, 'why', default=None)!r}, door_refused.fault +{_d(base, s, 'door_refused', 'fault')}, opens "
                f"+{_d(base, s, 'opens')}, seated {_n(s, 'seated', default=None)!r}, ui {s.get('ui')!r}, control {s.get('control')}, "
                f"event_enable {_n(s, 'event_enable', default=None)!r}, lever {lever!r}, faulted lines {faulted}; THE ROLLBACK: fp.before "
                f"{fpb} then the next seat's {fp_before_next}")


def judge_door_open(base: dict, s: dict) -> tuple:
    lever = (_n(s, "lever", default={}) or {}).get("door_fault")
    ok = (_d(base, s, "door_refused", "fault") == 1 and _n(s, "why", default=None) == BW.GM_WHY_FAULT and not _n(s, "seated", default=True)
          and _d(base, s, "opens") == 0 and s.get("ui") in HUDS and s.get("control") and _n(s, "event_enable", default=None) is True
          and lever == "off")
    return ok, (f"door_refused.fault +{_d(base, s, 'door_refused', 'fault')}, why {_n(s, 'why', default=None)!r}, seated "
                f"{_n(s, 'seated', default=None)!r}, opens +{_d(base, s, 'opens')}, ui {s.get('ui')!r}, control {s.get('control')}, "
                f"event_enable {_n(s, 'event_enable', default=None)!r}, lever {lever!r}")


def judge_door_restore(base: dict, held: dict, reseat: dict, closed: dict) -> tuple:
    ok_close, _named, detail = restore_ok(reseat, closed)
    ok = (held.get("ui") in HUDS and bool(_n(held, "seated", default=False)) and _d(base, held, "restore", "doors") == 0
          and _d(held, reseat, "restore", "doors") == 1 and bool(_n(reseat, "seated", default=False)) and _d(held, reseat, "opens") == 1
          and ok_close)
    return ok, (f"after the faulted Cancel: ui {held.get('ui')!r}, seated {_n(held, 'seated', default=None)!r}, doors "
                f"+{_d(base, held, 'restore', 'doors')}; the next door: doors +{_d(held, reseat, 'restore', 'doors')}, opens "
                f"+{_d(held, reseat, 'opens')}, seated {_n(reseat, 'seated', default=None)!r}; its close: {detail}")


def judge_door_889(base: dict, s: dict, window_before: bool) -> tuple:
    if not window_before:
        return False, "not reached: no window up at the press (no persistent strip on the strip field: the dialogue path untested)"
    ok = (_d(base, s, "door_refused", "host_elsewhere") == 1 and _n(s, "why", default=None) == BW.GM_WHY_HOST_ELSEWHERE
          and not _n(s, "seated", default=True) and _d(base, s, "opens") == 0 and not s.get("dialog") and s.get("ui") in HUDS
          and s.get("control") and _n(s, "event_enable", default=None) is True)
    return ok, (f"door_refused.host_elsewhere +{_d(base, s, 'door_refused', 'host_elsewhere')}, why {_n(s, 'why', default=None)!r}, "
                f"seated {_n(s, 'seated', default=None)!r}, opens +{_d(base, s, 'opens')}, window {s.get('dialog')}, ui {s.get('ui')!r}, "
                f"control {s.get('control')}, event_enable {_n(s, 'event_enable', default=None)!r}")


def depth_ms(fade_ms) -> int:
    """GM0-DEPTH's bound: 150 ms at the design's 40 ms fades; at a longer FadeDuration the two fades it spends plus the same slack."""
    f = int(fade_ms) if fade_ms is not None else 40
    return DEPTH_MS_AT_40 if f <= 40 else DEPTH_MS_AT_40 + 3 * (f - 40)


def judge_depth(where: str, base: dict, s: dict, lines, bound_ms: int, cause: str = "leave") -> tuple:
    """GM0-DEPTH-<where> / one GM0-CLOSE-IDS cycle (PURE): ``base`` seated at ``where``'s state, ``s`` after the close."""
    lc = _n(s, "last_close", default={}) or {}
    cl = (_n(s, "close_line", default={}) or {}).get("text")
    forced = _lines(lines, BW.LOG_GM_FORCED_CLOSE)
    watchdog = [ln for ln in forced if "WATCHDOG" in ln]
    from_ok = lc.get("from") == base.get("ui")
    fp = _n(s, "fp", default={}) or {}
    ok = (_d(base, s, "closes", cause) == 1 and lc.get("cause") == cause and from_ok and lc.get("end") == "done"
          and 0 <= int(lc.get("ms", -1)) <= int(bound_ms) and len(forced) == 1 and not watchdog
          and cl == BW.gm_close_line_rule(BW.gm_cause_index_rule(cause)) and s.get("ui") in HUDS and s.get("control")
          and _n(s, "event_enable", default=None) is True and not _n(s, "seated", default=True) and bool(fp.get("equal")))
    return ok, (f"{where}: closes.{cause} +{_d(base, s, 'closes', cause)}, last_close {lc} (from want {base.get('ui')!r}, ms <= {bound_ms}), "
                f"forced-close lines {len(forced)} (watchdog {len(watchdog)}), close_line {cl!r}, ui {s.get('ui')!r}, control "
                f"{s.get('control')}, event_enable {_n(s, 'event_enable', default=None)!r}, seated {_n(s, 'seated', default=None)!r}, "
                f"fp equal {fp.get('equal')!r}")


def close_old_measured(base: dict, s: dict, lines, cause: str = "leave") -> bool:
    return (_d(base, s, "closes", cause) == 0 and bool(_n(s, "seated", default=False))
            and cb.count(lines, BW.log_guestmenu_fireclose(BW.gm_cause_index_rule(cause), "old")) >= 1)


def judge_depth_fault(results: list) -> tuple:
    """GM0-DEPTH-FAULT (PURE): ``results`` [(step, base, after, lines)]."""
    out = []
    ok = bool(results)
    for step, base, s, lines in results:
        lc = _n(s, "last_close", default={}) or {}
        one = (_d(base, s, "closes", "faults") == 1 and lc.get("end") == "fault" and s.get("ui") in HUDS
               and _n(s, "event_enable", default=None) is True and len(_lines(lines, BW.LOG_GM_FORCED_CLOSE)) == 1)
        ok = ok and one
        out.append(f"{step}: faults +{_d(base, s, 'closes', 'faults')}, end {lc.get('end')!r}, ui {s.get('ui')!r}, event_enable "
                   f"{_n(s, 'event_enable', default=None)!r}, lines {len(_lines(lines, BW.LOG_GM_FORCED_CLOSE))}")
    return ok, " | ".join(out) or "not reached: no fault leg ran"


def judge_close_ids(results: list, bound_ms: int) -> tuple:
    """GM0-CLOSE-IDS (PURE): ``results`` [(cause, base, after, lines)] -- every id once."""
    done = {c for c, *_rest in results}
    missing = [c for c in BW.GM_CLOSE_IDS if c not in done]
    verdicts = [(c,) + judge_depth("root", b, s, ln, bound_ms, cause=c) for c, b, s, ln in results]
    bad = [f"{c}: {d}" for c, ok, d in verdicts if not ok]
    return (not missing and not bad), (f"ids missing {missing or 'none'}; " + (" | ".join(bad) if bad else
                                       f"each of {list(BW.GM_CLOSE_IDS)} closed with its words, end done"))


def judge_reopen(reopens: list, cancel_base: dict, after_fire: dict, fire_lines, own: dict) -> tuple:
    """GM0-REOPEN (PURE): ``reopens`` the seats taken after each forced close (each True), ``after_fire`` after a `fireclose leave` with
    no seat, ``own`` {opened, state} -- the own menu's Order under `guestmenu old`."""
    nos = cb.count(fire_lines, BW.log_guestmenu_fireclose(BW.GM_CAUSE_LEAVE, "no_seat"))
    forced = len(_lines(fire_lines, BW.LOG_GM_FORCED_CLOSE))
    ok = (bool(reopens) and all(reopens) and not _n(cancel_base, "seated", default=True) and not _n(cancel_base, "close_pending", default=True)
          and nos == 1 and forced == 0 and _d(cancel_base, after_fire, "closes", "leave") == 0 and bool(own.get("opened"))
          and own.get("open") is True and own.get("seated") is False)
    return ok, (f"reopens {reopens}; after a Cancel seated {_n(cancel_base, 'seated', default=None)!r} pending "
                f"{_n(cancel_base, 'close_pending', default=None)!r}; `fireclose leave` 'no seat' acks {nos}, forced lines {forced}, closes "
                f"+{_d(cancel_base, after_fire, 'closes', 'leave')}; the own menu (`old`) {own}")


def judge_quit(base: dict, waiting: list, wait_lines, s: dict, lines) -> tuple:
    """GM0-QUIT (PURE): ``waiting`` the samples after the fireclose (past CloseCapMs), ``s`` after the Cancel."""
    held = bool(waiting) and all(_n(w, "seated", default=False) and _n(w, "close_pending", default=False)
                                 and _n(w, "close_step", default=None) == "quit" for w in waiting)
    wd = [ln for ln in wait_lines if "WATCHDOG" in ln]
    lc = _n(s, "last_close", default={}) or {}
    ok = (held and not wd and _d(base, s, "closes", "leave") == 1 and lc.get("end") == "done" and s.get("ui") in HUDS and s.get("control")
          and _n(s, "event_enable", default=None) is True and not _n(s, "seated", default=True))
    return ok, (f"{len(waiting)} samples while the prompt held it (pending / step quit / seated on all: {held}), watchdog lines {len(wd)}; "
                f"after the Cancel: closes.leave +{_d(base, s, 'closes', 'leave')}, end {lc.get('end')!r}, ui {s.get('ui')!r}, control "
                f"{s.get('control')}, event_enable {_n(s, 'event_enable', default=None)!r}")


def judge_quit_exit(seated: bool, prompt: bool, exited: bool, saves_before, saves_after) -> tuple:
    ok = seated and prompt and exited and saves_before is not None and saves_before == saves_after
    return ok, (f"seated {seated}, the quit prompt up {prompt}, the process exited {exited}, sandbox saves unchanged "
                f"{saves_before is not None and saves_before == saves_after} ({len(saves_before or {})} files)")


def judge_held(stand_ok: bool, base: dict, held: list, s_back: dict, talk: bool) -> tuple:
    """GM0-HELDKEY (PURE): ``held`` the samples on the HUD while Confirm stayed held, ``talk`` the re-press opened the scribe's window."""
    if not stand_ok:
        return False, "not reached: the stand's positive control (a local talk with the scribe) never opened a window"
    on_hud = [h for h in held if h.get("ui") in HUDS]
    bits = [int((_n(h, "held", default={}) or {}).get("bits", 0) or 0) for h in on_hud]
    keyon = [int((_n(h, "held", default={}) or {}).get("keyon", 0) or 0) - int((_n(base, "held", default={}) or {}).get("keyon", 0) or 0)
             for h in on_hud]
    ok = (bool(on_hud) and all(b & CONFIRM_MASK for b in bits) and all(k == 0 for k in keyon) and not any(h.get("dialog") for h in on_hud)
          and not _n(s_back, "seated", default=True) and talk)
    return ok, (f"{len(on_hud)} HUD samples while held: bits {sorted(set(hex(b) for b in bits)) or 'none'}, keyon +{sorted(set(keyon)) or '?'}, "
                f"a window {any(h.get('dialog') for h in on_hud)}; the real re-press opened the talk {talk}")


def judge_master(m0: dict, m1: dict, returns: int) -> tuple:
    skipped = _d(m0, m1, "master_skipped")
    ok = returns == 2 and skipped == 2 and bool(_n(m1, "seated", default=False))
    return ok, (f"{returns} sub-screen returns, master_skipped +{skipped} (want +2), seated {_n(m1, 'seated', default=None)!r}; ach_held "
                f"{_n(m0, 'ach_held', default=None)!r} -> {_n(m1, 'ach_held', default=None)!r} (reported: which report the menu makes is K1's)")


def judge_dio_boot(seated: bool, why: str, s: dict) -> tuple:
    named = "guest menu" in (why or "")
    ok = seated and named and not s.get("booted") and bool(_n(s, "seated", default=False))
    return ok, (f"seated at the boot {seated}; the boot's refusal {why[:300]!r}; booted {s.get('booted')}, still seated "
                f"{_n(s, 'seated', default=None)!r}")


def judge_silent(booted: bool, now, base: dict, s: dict) -> tuple:
    if not booted:
        return False, "not reached: the diorama never booted"
    ok = now == "open" and s.get("ui") == "BattleHUD" and _d(base, s, "opens") == 0 and not _n(s, "open", default=True) \
        and not _n(s, "seated", default=True)
    return ok, (f"menu_refusal.now {now!r} on BattleHUD; after the press ui {s.get('ui')!r}, opens +{_d(base, s, 'opens')}, open "
                f"{_n(s, 'open', default=None)!r}, seated {_n(s, 'seated', default=None)!r}")


def judge_release(set_snap: dict, after: dict, lines_reset, lines_bare, seat2: dict, lines2, marker2: int) -> tuple:
    lever_set = _n(set_snap, "lever", default={}) or {}
    off = [k for k, v in BW.GUEST_MENU_LEVER_DEFAULTS.items() if lever_set.get(k) == v]
    rel = cb.count(lines_reset, BW.LOG_GUESTMENU_RELEASED)
    bare = cb.count(lines_bare, BW.LOG_GUESTMENU_RELEASED)
    bench = _n(after, "bench", default={}) or {}
    seat = _n(seat2, "seat", default={}) or {}
    ok = (not off and (_n(after, "lever", default={}) or {}) == BW.GUEST_MENU_LEVER_DEFAULTS and bench.get("marker") == -1
          and bench.get("host_field") == -1 and rel == 1 and bare == 0 and bool(_n(seat2, "seated", default=False))
          and seat.get("marker") == marker2 and seat_drawn(seat2) and frame_line(lines2, marker2) is not None)
    return ok, (f"levers left at their default when set: {off or 'none'}; after `reset` {_n(after, 'lever', default=None)}, bench {bench}, "
                f"release lines {rel} (a bare reset: {bare}); the next seat: marker {seat.get('marker')!r} (want {marker2}), the frame's "
                f"party drawn {seat_drawn(seat2)}")


def judge_softreset(held: dict, title: bool, base: dict, s: dict, lines, newgame_ok: bool) -> tuple:
    alarm = [ln for ln in _lines(lines, BW.LOG_GM_RESTORED) if _RX_ALARM in ln]
    ok = (held.get("ui") in HUDS and bool(_n(held, "seated", default=False)) and title and _d(base, s, "restore", "backstops", "replace") == 1
          and not _n(s, "seated", default=True) and not alarm and newgame_ok)
    return ok, (f"the seat held on the HUD {held.get('ui')!r}/{_n(held, 'seated', default=None)!r}; the title {title}; backstops.replace "
                f"+{_d(base, s, 'restore', 'backstops', 'replace')}, seated {_n(s, 'seated', default=None)!r}, alarm lines {len(alarm)}; "
                f"New Game landed {newgame_ok}")


def judge_cfg(base: dict, s: dict, heard: bool) -> tuple:
    """GM0-RAMP-CFG (PURE): ``heard`` the ini edit was an EDGE (the engine logged 'config change applied live' after it)."""
    if not heard:
        return False, "not reached: the ini edit was not an edge (no 'config change applied live')"
    cl = (_n(s, "close_line", default={}) or {}).get("text")
    fp = _n(s, "fp", default={}) or {}
    ok = (_d(base, s, "closes", "ending") == 1 and cl == BW.gm_close_line_rule(BW.GM_CAUSE_ENDING) and s.get("ui") in HUDS
          and s.get("control") and not _n(s, "seated", default=True) and bool(fp.get("equal")))
    return ok, (f"closes.ending +{_d(base, s, 'closes', 'ending')}, close_line {cl!r}, ui {s.get('ui')!r}, control {s.get('control')}, "
                f"seated {_n(s, 'seated', default=None)!r}, fp equal {fp.get('equal')!r}")


def judge_worldtag4(before: dict, s: dict, sub_ok: bool, world: int) -> tuple:
    se = _n(s, "outside_settled", default={}) or {}
    fp = _n(s, "fp", default={}) or {}
    u0, u1 = _n(before, "uid0_vars", default=None), _n(s, "uid0_vars", default=None)
    v0, v1 = _n(before, "sysvar192", default=-1), _n(s, "sysvar192", default=-1)
    ok = (sub_ok and bool(se.get("set")) and bool(se.get("equal")) and se.get("named") is None and bool(fp.get("equal"))
          and u0 is not None and u0 == u1 and v0 != -1 and v0 == v1 and s.get("ui") == "WorldHUD" and s.get("world") == world)
    return ok, (f"the Item round trip {sub_ok}; outside_settled {se}; fp equal {fp.get('equal')!r}; uid0_vars {u0!r} -> {u1!r}; sysvar192 "
                f"{v0!r} -> {v1!r}; ui {s.get('ui')!r} on {s.get('world')!r} (no load)")


def judge_cal(failed, predicted, measured: dict, needs) -> tuple:
    """S168-CAL (PURE): every predicted row red and nothing else, and every row in ``needs`` MEASURED its shape."""
    failed, predicted = set(failed), set(predicted)
    missing, extra = sorted(predicted - failed), sorted(failed - predicted)
    unmeasured = sorted(r for r in needs if not measured.get(r))
    ok = not missing and not extra and not unmeasured
    return ok, (f"predicted reds that stayed GREEN: {missing or 'none'}; unpredicted reds: {extra or 'none'}; rows whose shape was NOT "
                f"measured: {unmeasured or 'none'}")


# ------------------------------------------------------------------------------------------------ the proof's wants
def proof_wants() -> tuple:
    """(world walk, seat bracket, guest menu) tallies DERIVED from the s168 source (fakegame's readers: $FF9_S168_CLONE carrying the s168 tag,
    else an s168 patch), else the W1 fallbacks; and where they came from."""
    try:
        from harness import fakegame as FG
        src = FG.s168_engine_source("NetSyncWorldWalk.cs")
        ww = BW.world_walk_proof_counts(src) if src else None
        sb, gm = FG.seat_bracket_proof_tallies(), FG.guest_menu_proof_tallies()
        where = "the s168 source" if src else "the W1 fallbacks (no s168 source reachable)"
    except Exception as err:                                 # noqa: BLE001 - an unreadable source is a named fallback
        ww, sb, gm, where = None, BW.SEAT_BRACKET_PROOF_S168, BW.GUEST_MENU_PROOF_S168, f"the W1 fallbacks ({type(err).__name__})"
    return tuple(ww or BW.WORLD_WALK_PROOF_S168), tuple(sb), tuple(gm), where


# ------------------------------------------------------------------------------------------------ the moves
def _skew(g) -> None:
    g.wait_frames(SKEW_FRAMES)


def _gmop(g, ctx: dict, *args) -> tuple:
    """`netsync guestmenu <args>` -- NEVER sent to an engine without `netsync.guestmenu` (s167 answers "unknown sub-verb" only after the
    step; the driver has no `guestmenu` in its list, so cb.ns_verb sends it raw): (ok, why)."""
    if not ctx.get("new"):
        return False, f"`guestmenu {' '.join(map(str, args))}` not sent (no `netsync.guestmenu`: an engine before s168)"
    ok, why = cb.try_ns(g, "guestmenu", *[str(a) for a in args])
    _skew(g)
    return ok, why


def _ns(g, *args) -> tuple:
    ok, why = cb.try_ns(g, *[str(a) for a in args])
    _skew(g)
    return ok, why


def _hud(world: bool) -> str:
    return "WorldHUD" if world else "FieldHUD"


def _ready(g, ctx: dict, *, world: bool = False, timeout: float = CLOSE_S):
    """THE PRE-INIT SAMPLE: the HUD with control, no fade, no window (and, on s168, events on). The state or None."""
    hud = _hud(world)

    def ok(s):
        if s.ui_state != hud or not s.control or getattr(s, "fading", False) or getattr(s, "dialog_open", False):
            return False
        return not ctx.get("new") or _gm(s).get("event_enable") is True
    return cb.poll(g, ok, timeout, f"{hud} with control (the pre-init sample)")


def _frame(g, ctx: dict, marker: int) -> tuple:
    ok, why = _gmop(g, ctx, "frame", marker)
    if ok:
        cb.poll(g, lambda s: (_gm(s).get("bench") or {}).get("marker") == marker, 2.0, "the bench frame read back")
    return ok, why


def press_menu(g, ctx: dict, *, world: bool = False) -> tuple:
    """One Menu press on the HUD: (outcome, the settled snap). outcome 'seated' | 'own' (MainMenu, unseated) | 'refused' | 'none'."""
    base = snap(g.state)
    mr0, dr0 = int(base["mr"].get("count", 0) or 0), _door_total(base)
    g.press("menu")
    st = cb.poll(g, lambda s: s.ui_state == "MainMenu" or int(_mr(s).get("count", 0) or 0) > mr0 or _door_total(snap(s)) > dr0,
                 OPEN_S, "the press's outcome (MainMenu or a refusal)")
    if st is None:
        return "none", snap(g.state)
    if st.ui_state == "MainMenu":
        _skew(g)
        s = snap(g.state)
        _CHAR_AT[id(g)] = 0                                  # a fresh root has no remembered character (MainMenuUI.cs:130-138)
        return ("seated" if _n(s, "seated", default=False) else "own"), s
    # the refusal's line is read AT the verdict: a field load ends it (RefusalLineLiveRule + ClearGuestMenuLine, NetSyncGuestMenu.cs:1982-
    # 1987), so a press whose follow lands before the HUD settles (WHY-BUSY) would read line None at the settled sample
    at = snap(st)
    st = _ready(g, ctx, world=world, timeout=CLOSE_S) or g.state
    s = snap(st)
    s["verdict_line"] = (_n(at, "line", default={}) or {}).get("text")
    return "refused", s


def cancel_out(g, ctx: dict, *, world: bool = False, presses: int = 8) -> dict:
    """Cancel back up to the HUD (the restore door), then the HUD's Show (events back on) and the settle: the settled snap."""
    hud = _hud(world)
    for _ in range(presses):
        st = g.state
        if st.ui_state == hud:
            break
        if st.ui_state not in BW.GM_MENU_STATES:
            g.wait_frames(6)
            continue
        g.press("cancel")
        cb.poll(g, lambda s, u=st.ui_state: s.ui_state != u, SEL_S, "the Cancel's next state")
    st = _ready(g, ctx, world=world, timeout=CLOSE_S) or g.state
    if ctx.get("new") and not _gm(st).get("seated"):
        st = cb.poll(g, lambda s: (_gm(s).get("outside_settled") or {}).get("set") is True, 1.0, "the settle stamped") or g.state
    return snap(st)


#: MainMenuUI's two root groups (MainMenuUI.cs:903-904): the sub-menu rows and the character pick
ROOT_GROUP, CHAR_GROUP = "MainMenu.SubMenu", "MainMenu.Character"


def _on_root(st) -> bool:
    """(PURE) on the root, not in its character pick: ui MainMenu with any group but CHAR_GROUP. The character pick is ui MainMenu too
    (MainMenuUI.cs:171-181 sets CharacterGroupButton; ui_state never moves for it, HarnessAgent.cs:3790-3794) but is NOT the root. Keyed on
    the one exception, so a publisher that names the root otherwise (the stand-in's "MainMenu") still reads as the root."""
    return st.ui_state == "MainMenu" and getattr(st, "menu_group", None) != CHAR_GROUP


def _back_to_root(g, presses: int = 5) -> bool:
    for _ in range(presses):
        st = g.state
        if _on_root(st):
            return True
        if st.ui_state == "MainMenu":                        # stranded in the character pick: Cancel goes back to SubMenu (:351-359)
            g.press("cancel")
            cb.poll(g, _on_root, SEL_S, "the root's sub-menu after the character pick's Cancel")
            continue
        if st.ui_state not in BW.GM_MENU_STATES:
            return False
        g.press("cancel")
        cb.poll(g, lambda s, u=st.ui_state: s.ui_state != u, SEL_S, "the Cancel's next state")
    return _on_root(g.state)


def _pick(g, label: str, *, confirm: bool = True, max_steps: int = 14, directions=("down",), why: list | None = None) -> bool:
    """Move the highlight onto ``label`` along each of ``directions`` in turn (every s168 bar is HORIZONTAL: ('right', 'down')) and
    (``confirm``) press Confirm; False (nothing confirmed) when none reaches it, each direction's menu_pick error (its `seen` list)
    appended to ``why``."""
    for d in directions:
        try:
            g.menu_pick(label, direction=d, max_steps=max_steps, confirm=confirm)
            return True
        except HarnessError as err:
            if why is not None:
                why.append(f"{label!r} by {d}: {str(err)[:200]}")
    return False


def _group(g, group: str, what: str, timeout: float | None = None):
    """Poll until NGUI's active button group (`menu_group`) is ``group``: the state, or None."""
    return cb.poll(g, lambda s: getattr(s, "menu_group", None) == group, SEL_S if timeout is None else timeout, what)


def _label(g):
    return getattr(g.state, "menu_label", None)


def _where(g) -> tuple:
    """(menu_group, menu_label) right now: one entry of a try's trail."""
    st = g.state
    return getattr(st, "menu_group", None), getattr(st, "menu_label", None)


def _trail_text(trail, limit: int = 600) -> str:
    return f"; trail {trail}"[:limit] if trail else ""


#: the root's remembered character, per session: MainMenuUI remembers the last character picked (:176-179, set at :259 / :270 / :281)
#: and its list wraps (:681-692) -- cleared only at the root's final close (:339, :95-98 -> RemoveCursorMemorize :130-138)
_CHAR_AT: dict = {}


def _char_downs(prev, want) -> int:
    """(PURE) the downs from the remembered character ``prev`` to party slot ``want`` on a four-row wrapping list."""
    return (int(want) - int(prev)) % 4


def root_labels(g) -> list:
    try:
        return list(g.menu_labels(max_steps=16))
    except HarnessError:
        return []


def goto_screen(g, label: str, *, char: int = 0) -> tuple:
    """From the root: ``label`` picked, then (when the root moved to the character pick: still MainMenu) party slot ``char`` confirmed --
    walked from the root's REMEMBERED character (_CHAR_AT), never from the top: (the screen's state or None, why). On a screen, the poll
    waits for its own group (`<label>.`) and a non-empty label, so the first read after the pick is never the root's stale one."""
    if g.state.ui_state != "MainMenu":
        return None, f"not on the root ({g.state.ui_state!r})"
    whys = []
    if not _pick(g, label, why=whys):
        return None, f"no {label!r} row on the root (read {_where(g)}; {'; '.join(whys)})"
    st = cb.poll(g, lambda s: s.ui_state != "MainMenu", SEL_S, f"{label}'s screen")
    picked = False
    if st is None and g.state.ui_state == "MainMenu":
        if getattr(g.state, "menu_group", None) == ROOT_GROUP:
            # the root's Confirm was swallowed (a UIScene Loading frame): blind downs + Confirm here would land on the SUB-MENU
            return None, f"{label}'s root confirm opened neither a screen nor the character pick (read {_where(g)})"
        for _ in range(_char_downs(_CHAR_AT.get(id(g), 0), char)):
            g.press("down")
            g.wait_frames(6)
        g.press("confirm")
        picked = True
        st = cb.poll(g, lambda s: s.ui_state != "MainMenu", SEL_S, f"{label}'s screen (after the character pick)")
    s = g.state.ui_state
    if s in ("MainMenu", None) or s in HUDS:
        return None, f"{label} opened no screen (ui {s!r}; read {_where(g)})"
    if picked:
        _CHAR_AT[id(g)] = int(char)                          # remembered only once the pick OPENED its screen (MainMenuUI.cs:259/:270/:281)
    cb.poll(g, lambda x: str(getattr(x, "menu_group", None) or "").startswith(f"{label}.") and bool(getattr(x, "menu_label", None)),
            SEL_S, f"{label}'s own group and a fresh label")
    return s, ""


#: THE CENSUS PLANS (the second in-game round's: the first run measured the screens -- every bar HORIZONTAL, Item opening ON its list, the
#: Ability lists opening on their first lit row): site -> tries, each (screen, char, steps); char a PARTY SLOT (goto_screen walks it from
#: the root's remembered character). A step is ("bar", (labels...)) a horizontal bar's pick (its Confirm); ("expect", group, (labels...))
#: the list's group polled and its opening label read -- a seek only when it is none of ``labels``; ("group", group) a poll; ("key",
#: button) one press; ("shot", name) a screenshot. The census is polled after each step that presses (bar, pick, key).
#: each tried member's OWN lit support abilities (never one list shared by all: a NoDraw row's NameLabel is never rewritten, AbilityUI.cs:1140-
#: 1145, so a reused cell can publish another member's lit name): slot 0 (the impostor drawn on Freya: Dragon Killer from the Javelin first),
#: slot 3 (Steiner)
_LIT_SAS = ((0, ("Dragon Killer", "Cover", "Antibody")), (3, ("Bird Killer", "Bug Killer", "Beast Killer")))
SITE_PLANS = {
    # Item opens ON its list, the cursor on row 0 (Potion, usable): Confirm opens Item.Target, whose Confirm is I1 (ItemUI.cs:415)
    "I1": [("Item", 0, (("expect", "Item.Item", ("Potion",)), ("key", "confirm"), ("group", "Item.Target"), ("key", "confirm")))],
    # the bar's Equip, slot 4 (accessory), Confirm, the seeded Desert Boots (the only candidate: the list opens on row 0): E1 (EquipUI.cs:183)
    "E1": [("Equip", 0, (("bar", ("Equip",)), ("key", "down"), ("key", "down"), ("key", "down"), ("key", "down"), ("key", "confirm"),
                         ("expect", "Equip.Inventory", ("Desert Boots",)), ("key", "confirm")))],
    # the bar's Equip opens the support list ON the first lit SA (AbilityUI.cs:1102-1124): Confirm there is A1 (:419)
    "A1": [("Ability", c, (("bar", ("Equip",)), ("expect", "Ability.SupportAbility", lit), ("key", "confirm"))) for c, lit in _LIT_SAS],
    # Special ON a lit SA row is A2 (:638); Special on Ability.SubMenu is stock's fast switch to the Equip SCREEN (:606-618), never a write
    "A2": [("Ability", c, (("bar", ("Equip",)), ("expect", "Ability.SupportAbility", lit), ("key", "special"))) for c, lit in _LIT_SAS],
    "E2": [("Equip", 0, (("bar", ("Off", "Remove")),) + tuple(("key", k) for k in ["down"] * n + ["confirm"])) for n in range(1, 5)],
    "E3": [("Equip", 0, (("bar", ("Optimize", "Ability")),))],          # the bar pick's own Confirm is E3 (EquipUI.cs:329)
    # char 2 IS Garnet only with the remembered character tracked: Cure is her first Enable AA by source; the expect records what the list
    # really opens on, and the shot right after the Use pick shows whether Cure is lit on the seated copy (DESIGN D10)
    "A3": [("Ability", 2, (("bar", ("Use",)), ("shot", "s168-a3-garnet-use"), ("expect", "Ability.ActionAbility", ("Cure", "Panacea")),
                           ("key", "confirm"), ("group", "Ability.Target"), ("key", "confirm")))],
    "I2": [("Item", 0, (("expect", "Item.Item", ("Gysahl Greens",)), ("key", "confirm")))],
}
_MOVES = ("up", "down", "left", "right")


def drive_site(g, ctx: dict, site: str) -> dict:
    """Each of the site's tries from the root until a census confirm is counted: {reached, why, before, after, back, reached_pass, trail}.
    No blind Confirm: a label not found ends the try with a why. After every Confirm (and Special) the (menu_group, menu_label) joins
    ``trail``, and every not-reached why carries it. A site that needs the seeded bag (BAG_SITES) on a run whose seeder did not run
    (ctx['bag_why']) is not driven: its why names the seeder."""
    rec = {"reached": False, "why": "no try ran", "before": None, "after": None, "back": False, "reached_pass": False, "trail": []}
    trail = rec["trail"]
    if site in BAG_SITES and ctx.get("bag_why"):
        rec["why"] = ctx["bag_why"]
        rec["back"] = _back_to_root(g)
        return rec
    for screen, char, steps in SITE_PLANS[site]:
        if not _back_to_root(g):
            rec["why"] = f"not on the root ({g.state.ui_state!r})" + _trail_text(trail)
            return rec
        before = snap(g.state)
        trail.append(f"{screen} c{char}")
        state, why = goto_screen(g, screen, char=char)
        if state is None:
            rec["why"] = why + _trail_text(trail)
            continue
        trail.append(_where(g))
        r0, p0 = int(_n(before, "refused", "count")), int(_n(before, "passes"))

        def census(s, r0=r0, p0=p0):
            return int((_gm(s).get("refused") or {}).get("count", 0)) > r0 or int(_gm(s).get("passes", 0)) > p0
        hit, stop, whys = None, None, []
        for step in steps:
            kind = step[0]
            if kind == "shot":
                path, swhy = cb.shot(g, step[1])
                trail.append(f"shot {path or 'FAILED: ' + swhy}")
                if path:
                    g.note(f"GM0-REFUSE-{site}: {path} (READ it: is the row under the cursor lit on the seated copy?)")
                continue
            if kind == "group":
                if _group(g, step[1], f"{site}: {step[1]}") is None:
                    stop = f"{screen}: never reached {step[1]} (read {_where(g)})"
                    break
                continue
            if kind == "expect":
                group, labels = step[1], tuple(step[2])
                ok_group = _group(g, group, f"{site}: {group}") is not None
                where = _where(g)
                trail.append(where)
                if not ok_group:
                    stop = f"{screen}: never reached {group} (read {where})"
                    break
                if where[1] not in labels and not any(_pick(g, lb, confirm=False, directions=("down", "right"), why=whys) for lb in labels):
                    stop = f"{screen}: {group} opened on {where[1]!r}, none of {labels} found ({'; '.join(whys)})"
                    break
                continue
            if kind == "bar":
                if not any(_pick(g, lb, directions=("right", "down"), why=whys) for lb in step[1]):
                    stop = f"{screen}: no {step[1]} on the bar ({'; '.join(whys)})"
                    break
                confirmed = True
            elif kind == "pick":                             # no blind fallback Confirm: a missing label ends the try
                if not any(_pick(g, lb, why=whys) for lb in step[1]):
                    stop = f"{screen}: no {step[1]} row ({'; '.join(whys)})"
                    break
                confirmed = True
            else:
                g.press(step[1])
                confirmed = step[1] not in _MOVES
            hit = cb.poll(g, census, STEP_S, f"{site}'s census")
            if confirmed:
                trail.append(_where(g))
            if hit is not None:
                break
        if hit is None:
            rec["why"] = (stop or f"{screen}: no census confirm counted (refused +0, passes +0)") + _trail_text(trail)
            continue
        _skew(g)
        after = snap(g.state)
        last = (_n(after, "refused", default={}) or {}).get("last_site")
        passed = int(_n(after, "passes")) > p0
        if not passed and last != site:
            rec.update(why=f"the path landed on {last!r}, not {site}" + _trail_text(trail), before=before, after=after)
            continue
        rec.update(reached=not passed, reached_pass=passed, why=f"the census PASSED the {site} confirm (`capture off`: passes +1)" if passed
                   else "", before=before, after=after, screen=state)
        break
    rec["back"] = _back_to_root(g)
    return rec


def _measure(ctx: dict, rows, shape: bool) -> None:
    for r in rows if isinstance(rows, (tuple, list)) else (rows,):
        ctx["measured"][r] = ctx["measured"].get(r, False) or bool(shape)


def _seat(g, ctx: dict, *, marker: int | None = None, world: bool = False) -> tuple:
    """A frame (``marker``: the leg's own unless None = keep the current one) and a Menu press: (ok, why, the snap). An own menu (`old`)
    is MEASURED (OLD's shape) and closed again."""
    if _ready(g, ctx, world=world) is None:
        return False, f"no {_hud(world)} with control (the pre-init sample: ui {g.state.ui_state!r})", snap(g.state)
    if marker is not None:
        ok, why = _frame(g, ctx, marker)
        if not ok:
            return False, f"`guestmenu frame {marker}` refused: {why}", snap(g.state)
    out, s = press_menu(g, ctx, world=world)
    if out == "seated":
        return True, "", s
    if out == "own":
        ctx["own_seen"] = True
        cancel_out(g, ctx, world=world)
        return False, "the press opened the OWN menu unseated (s121's Open: `guestmenu old`)", s
    if out == "refused":
        return False, f"the press was refused (why {_n(s, 'why', default=None)!r})", s
    return False, f"nothing happened on the press (ui {s.get('ui')!r})", s


def hold_samples(g, seconds: float = HOLD_S) -> list:
    return [snap(st) for st in cb.hold_for(g, seconds)]


def old_shape(g, ctx: dict, *, world: bool = False) -> bool:
    """OLD's shape (s167) and `guestmenu old`'s: s121's bench reading `open` on the HUD and a press opening the OWN menu unseated."""
    st = _ready(g, ctx, world=world) or g.state
    now = _mr(st).get("now")
    out, s = press_menu(g, ctx, world=world)
    if s.get("ui") == "MainMenu":
        cancel_out(g, ctx, world=world)
    g.note(f"OLD's shape: menu_refusal.now {now!r} on the HUD; the press: {out} (ui {s.get('ui')!r}, open {_n(s, 'open', default=None)!r}, "
           f"seated {_n(s, 'seated', default=None)!r})")
    return now == "open" and (not ctx.get("new") or (out == "own" and _n(s, "open", default=False) is True))


# ------------------------------------------------------------------------------------------------ the bag seeder (GMBAG, DESIGN D6)
_BAG_SEEDED = "bag seeder: warped"


def bag_unregistered_why() -> str:
    """The named precondition red when GMBAG is not registered (E1, I2 and LOCAL's key read carry it as their not-reached why)."""
    return (f"the bag seeder {BAG_FIELD} is not registered (GMBAG -- deploy: py tools/deploy_field.py {BAG_TOML} --id {BAG_FIELD} "
            "--mod-folder FF9CustomMap, then relaunch)")


def _bag_registered(g):
    """True / False from the live DictionaryPatch registrations (cb.seed_party's read), None when they could not be read."""
    try:
        return BAG_FIELD in g.registered_fields()[0]
    except (HarnessError, AttributeError, OSError):
        return None


def seed_bag(g, *, back_to: int | None = None) -> str:
    """Through GMBAG (BAG_FIELD) when it is registered -- its entry grants Desert Boots, Gysahl Greens (a key item only once BAG_KEY_ITEM
    is set: the toml's KNOWN GAP) into the guest's
    OWN bag, which the bench frame copies at the seat (count>0 rows and rare sets, NetSyncClient.cs:2688-2709) -- then to ``back_to`` (the
    field the call began on by default). cb.seed_party's shape: a one-line note for the notes, starting "bag seeder: warped" only when the
    seeder ran (a grant that speaks has its window closed with Confirm)."""
    reg = _bag_registered(g)
    if reg is None:
        return "bag seeder: the registrations could not be read -- the New-Game bag stands"
    if not reg:
        return f"bag seeder: {bag_unregistered_why()}"
    home = g.state.field_id if back_to is None else back_to
    try:
        if g.state.field_id != BAG_FIELD:
            g.warp(BAG_FIELD)
        g.wait_frames(BAG_FRAMES)                            # the entry grants run
        window = bool(getattr(g.state, "dialog_open", False))
        _close_window(g)
        if home is not None and home != BAG_FIELD:
            g.warp(home)
    except HarnessError as err:
        return f"bag seeder: the warp through {BAG_FIELD} failed ({str(err)[:160]}) -- the bag is not known seeded"
    return (f"{_BAG_SEEDED} through {BAG_FIELD} (GMBAG: +Desert Boots +Gysahl Greens "
            + (f"+key item {BAG_KEY_ITEM})" if BAG_KEY_ITEM is not None else "-- no key item: GMBAG's KNOWN GAP)")
            + ("; its window closed with Confirm" if window else ""))


def bag_key_why() -> str:
    """LOCAL's key read, not driven while GMBAG grants no key item (BAG_KEY_ITEM None): the named reason."""
    return (f"the bag seeder {BAG_FIELD} grants no key item yet (GMBAG's KNOWN GAP: the kit has no field.toml lane for a stock key item; "
            "the New-Game bag holds none) -- the key-item read is untested")


def _setup(g, field: int, *, label: str, bag: bool) -> tuple:
    """cb.setup's own steps with the bag seeder between the party seeder and the bench field when ``bag``: newgame -> COOPPARTY -> GMBAG
    -> ``field`` -> encounters off -> the forced selftest role. (selftest_ok, detail, bag_why: None when the bag was seeded or not asked
    for, else the named reason E1 / I2 / LOCAL's key read carry)."""
    if not bag:
        ok, why = cb.setup(g, field, label=label)
        return ok, why, None
    cb.provenance(g)
    g.note(label)
    g.newgame()
    g.note(cb.seed_party(g, back_to=BAG_FIELD if _bag_registered(g) else field))
    note = seed_bag(g, back_to=field)
    g.note(note)
    if g.state.field_id != field:
        g.warp(field)
    try:
        g.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        g.note(f"noencounter refused ({str(err)[:120]}) -- a random battle may interrupt a leg")
    g.wait_frames(45)
    ok, why = cb.try_ns(g, "selftest", 1)
    ns = g.state.netsync or {}
    good = ok and bool(ns.get("selftest")) and bool(ns.get("forced"))
    bag_why = None if note.startswith(_BAG_SEEDED) else note.split("bag seeder: ", 1)[-1]
    return good, (why or f"selftest={ns.get('selftest')!r} forced={ns.get('forced')!r} role={ns.get('role')!r}"), bag_why


# ------------------------------------------------------------------------------------------------ the legs
def _leg_seat(g, led: cb.Ledger, ctx: dict) -> None:
    rows = LEG_ROWS["seat"]
    cycles = []
    at = cb.mark(g)
    base = snap(_ready(g, ctx) or g.state)
    ok, why, s = _seat(g, ctx, marker=ctx["marker"])
    if not ok:
        led.unreached(rows, why)
        return
    open_samples = [s] + hold_samples(g)
    led.check("GM0-SEAT", *judge_seat(base, s, cb.new(g, at), ctx["marker"]))
    _measure(ctx, ("GM0-SEAT", "GM0-BROWSE"), ctx["pulled"] == "skip" and seat_skip_measured(s))
    _measure(ctx, "GM0-CHIP", ctx["pulled"] == "chip" and chip_off_measured(open_samples))
    _measure(ctx, "GM0-FREEZE", ctx["pulled"] == "events" and events_on_measured(open_samples))
    labels = root_labels(g)
    visits = []
    for label in SUB_SCREENS + tuple(lb for lb in OPTIONAL_SCREENS if lb in labels):
        _back_to_root(g)
        state, why = goto_screen(g, label)
        shot = cb.shot(g, f"s168-browse-{label.lower()}")[0] if state else None
        seated = bool(_gm(g.state).get("seated"))
        back = _back_to_root(g) if state else False
        visits.append({"label": label, "found": state is not None, "state": state, "back": back, "seated": seated, "why": why})
        if shot:
            g.note(f"GM0-BROWSE {label}: {shot} (READ it: the BENCH{ctx['marker']} impostor at lv99, the frame's values)")
    greys = [_grey(g, lb) for lb in BW.GM_GREYED_SUB_MENUS if lb in labels]
    save = _savemenu_try(g)
    closed = cancel_out(g, ctx)
    cycles.append((base, closed))
    led.check("GM0-CHIP", *judge_chip(open_samples, closed))
    led.check("GM0-FREEZE", *judge_freeze(open_samples, closed))
    led.check("GM0-BROWSE", *judge_browse(visits, greys, labels, save, s))
    # the root-only cycle: open and Cancel at the root, no sub-screen visited -- on `frame witness keyitem` (the two-marker frame plus one
    # key item this install lacks), so the KEY ITEMS family is swapped too (`frame <m>` copies the guest's own: `restore skip keyitems`
    # over it would read equal, and that lever could not redden this row)
    base2 = snap(_ready(g, ctx) or g.state)
    okw, whyw = _gmop(g, ctx, "frame", "witness", BW.GM_COMP_KEY_ITEM)
    if not okw:
        g.note(f"GM0-RESTORE's root-only cycle: `frame witness keyitem` refused ({whyw}) -- the marker frame kept")
    ok2, why2, _s2 = _seat(g, ctx)
    if ok2:
        cycles.append((base2, cancel_out(g, ctx)))
    else:
        g.note(f"GM0-RESTORE's root-only cycle not seated: {why2}")
    led.check("GM0-RESTORE", *judge_restore(cycles))
    if ctx["pulled"] and ctx["pulled"].startswith("restore:"):
        _measure(ctx, "GM0-RESTORE", restore_skip_measured(cycles, ctx["pulled"].split(":", 1)[1]))


def _grey(g, label: str) -> dict:
    """A greyed row's Confirm while seated: {label, state, refused_delta, captures_delta, seated}."""
    _back_to_root(g)
    s0 = snap(g.state)
    picked = _pick(g, label)
    st = cb.poll(g, lambda s: s.ui_state != "MainMenu", SEL_S, f"{label} to open (it must not)")
    s1 = snap(g.state)
    if st is not None:
        _back_to_root(g)
    return {"label": label, "picked": picked, "state": s1.get("ui"), "refused_delta": _d(s0, s1, "refused", "count"),
            "captures_delta": _d(s0, s1, "captures"), "seated": bool(_n(s1, "seated", default=False))}


def _savemenu_try(g) -> dict:
    """Alt+F5 while seated: {serialize (a Serialize sample), raised, seated}."""
    _back_to_root(g)
    raised = None
    try:
        g.savemenu()
    except HarnessError as err:
        raised = str(err)[:160]
    seen = cb.poll(g, lambda s: s.ui_state == SERIALIZE, SAVE_S, "a Serialize screen (it must not open)")
    if seen is not None:
        _back_to_root(g)
    return {"serialize": seen is not None, "raised": raised, "seated": bool(_gm(g.state).get("seated"))}


def _leg_refuse(g, led: cb.Ledger, ctx: dict, sites=REFUSE_SITES, *, deep: bool = False) -> None:
    rows = LEG_ROWS["deep" if deep else "refuse"]
    at = cb.mark(g)
    ok, why, _s = _seat(g, ctx, marker=ctx["marker"])
    if not ok:
        led.unreached(rows, why)
        return
    recs = {site: drive_site(g, ctx, site) for site in sites}
    local = _local_steps(g, ctx) if deep else []
    greys = [] if deep else [_grey(g, lb) for lb in BW.GM_GREYED_SUB_MENUS if lb in root_labels(g)]
    closed = cancel_out(g, ctx)
    lines = cb.new(g, at)
    for site in sites:
        led.check(f"GM0-REFUSE-{site}", *judge_site(site, recs[site], closed, lines))
        _measure(ctx, f"GM0-REFUSE-{site}", ctx["pulled"] == "capture" and capture_off_measured(recs[site]))
    if deep:
        led.check("GM0-LOCAL", *judge_local(local, closed))
        return
    led.check("GM0-REFUSE-GREY", *judge_grey(greys))
    led.check("GM0-OUTSIDE", *judge_outside(closed))
    _measure(ctx, "GM0-OUTSIDE", ctx["pulled"] == "poke" and poke_measured(closed))


def _item_rail(g, rec: dict) -> bool:
    """Item > the rail (Item.SubMenu, 'Use | Arrange | Key'): Item opens ON its list (ItemUI.cs:192-198), so one Cancel off Item.Item puts
    the group on the rail; any other opening group is named, never Cancelled blind (a Cancel on the rail leaves the screen)."""
    trail = rec.setdefault("trail", [])
    state, why = goto_screen(g, "Item")
    if state is None:
        rec["why"] = why
        return False
    trail.append(_where(g))
    if getattr(g.state, "menu_group", None) == "Item.Item":
        g.press("cancel")
    if _group(g, "Item.SubMenu", "the Item rail (a Cancel off the list)") is None:
        rec["why"] = f"no Item.SubMenu (the rail) after the Item screen opened (read {_where(g)})"
        return False
    trail.append(_where(g))
    return True


def _arrange(g, rec: dict, whys: list) -> bool:
    """The rail's Arrange (a HORIZONTAL bar): the arrange dialog (Item.ArrangeMenu) open and its TweenIn run out."""
    if not _pick(g, "Arrange", directions=("right", "down"), why=whys):
        rec["why"] = f"no 'Arrange' on the Item rail ({'; '.join(whys)})"
        return False
    if _group(g, "Item.ArrangeMenu", "the arrange dialog") is None:
        rec["why"] = f"no Item.ArrangeMenu after the rail's Arrange (read {_where(g)})"
        return False
    g.wait_frames(TWEEN_FRAMES)                              # the dialog's tween holds Loading: a press inside it is swallowed (UIScene)
    rec.setdefault("trail", []).append(_where(g))
    return True


def _sort_steps(g, rec: dict) -> bool:
    """GM0-LOCAL's sort (D5): the rail's Arrange > Auto (pressed, never measured: a no-op on a bag already in Order; nothing asserted but
    the seat), then Arrange > the SECOND row, Manual (ItemUI.cs:299-306: mode 2 = sibling index 1; its label recorded as manual_label),
    then the MEASURED swap (_manual_swap). True when every step ran (``rec['why']`` names the first that did not)."""
    whys = []
    if not _item_rail(g, rec) or not _arrange(g, rec, whys):
        return False
    if not _pick(g, "Auto", directions=("down", "right"), why=whys):
        rec["why"] = f"no 'Auto' in the arrange dialog ({'; '.join(whys)})"
        return False
    rec["auto_rail"] = _group(g, "Item.SubMenu", "the rail after Auto (ItemUI.cs:289-296)") is not None
    g.wait_frames(TWEEN_FRAMES)
    rec["auto_seated"] = bool(_gm(g.state).get("seated"))
    rec["trail"].append(_where(g))
    if not _arrange(g, rec, whys):
        return False
    if not _pick(g, "Auto", confirm=False, directions=("down", "up"), why=whys):   # the first row, wherever the dialog opened
        rec["why"] = f"no 'Auto' row to start the second-row walk from ({'; '.join(whys)})"
        return False
    g.press("down")
    st = cb.poll(g, lambda s: getattr(s, "menu_label", None) not in (None, "", "Auto"), SEL_S, "the arrange dialog's second row")
    rec["manual_label"] = _label(g)
    if st is None:
        rec["why"] = f"the arrange dialog's second row never read (label {_label(g)!r})"
        return False
    g.press("confirm")
    if not _manual_swap(g, rec):
        rec["why"] = rec.get("swap_why") or (
            f"the manual swap did not measure: l0 {rec.get('l0')!r} on {rec.get('row0')!r}, l2 {rec.get('l2')!r} on {rec.get('row2')!r}, "
            f"the cursor after it {rec.get('swapped')!r} on {rec.get('swapped_row')!r}")
        return False
    return True


def _manual_swap(g, rec: dict) -> bool:
    """THE MEASURED SORT (GM0-LOCAL; the duo's GM0-LOCAL-D spends it too), called right after Arrange > Manual's Confirm: on Item.Item the
    label under the cursor (l0) and the one two rows on (l2: the list has two columns -- read here, where labels publish, then back up),
    then l0 Confirmed (Item.Arrange), one down, that row Confirmed: the two swap (ItemUI.cs:463-474) and the cursor stays on the second
    row (JumpToIndex), which must now read l0 (``swapped``). Records l0 / l2 / l2_arrange (the Arrange group's own read) / swapped /
    swap_why (empty when every step ran) and the trail in ``rec``; True when the swap is MEASURED (swap_measured)."""
    rec.update(l0=None, l2=None, l2_arrange=None, swapped=None, swap_why="", row0=None, row2=None, swapped_row=None)
    trail = rec.setdefault("trail", [])
    skip = (None, "", "Auto", "Manual", rec.get("manual_label"))

    def on_list(s, want=None):
        lb = getattr(s, "menu_label", None)
        return getattr(s, "menu_group", None) == "Item.Item" and (lb == want if want is not None else lb not in skip)
    st = cb.poll(g, on_list, SEL_S, "the item list in Manual")
    trail.append(_where(g))
    if st is None:
        rec["swap_why"] = f"no item list (Item.Item) after Manual (read {_where(g)})"
        return False
    g.wait_frames(TWEEN_FRAMES)                              # the arrange dialog's TweenOut holds Loading: a press inside it is swallowed
    rec["l0"] = l0 = _label(g)
    rec["row0"] = getattr(g.state, "menu_selected", None)
    g.press("down")
    cb.poll(g, lambda s: on_list(s) and getattr(s, "menu_label", None) != l0, SEL_S, "the row two on")
    rec["l2"] = l2 = _label(g)
    rec["row2"] = getattr(g.state, "menu_selected", None)
    g.press("up")
    back = cb.poll(g, lambda s: on_list(s, l0), SEL_S, "back on the first row") is not None
    trail.append((l0, l2))
    if not back or not l2 or l2 == l0:
        rec["swap_why"] = f"no second row read two on from {l0!r} (read {l2!r}, back on {l0!r} {back})"
        return False
    g.press("confirm")
    if _group(g, "Item.Arrange", "the manual move's first pick") is None:
        trail.append(_where(g))
        rec["swap_why"] = f"no Item.Arrange after Confirm on {l0!r} (read {_where(g)})"
        return False
    trail.append(_where(g))
    g.press("down")
    cb.poll(g, lambda s: getattr(s, "menu_label", None) not in (None, "", l0), SEL_S, "the move's target row")
    rec["l2_arrange"] = _label(g)
    g.press("confirm")
    cb.poll(g, lambda s: on_list(s, l0), SEL_S, "the swap: the cursor's row reads l0")
    rec["swapped"] = _label(g)
    rec["swapped_row"] = getattr(g.state, "menu_selected", None)
    trail.append(_where(g))
    if getattr(g.state, "menu_group", None) != "Item.Item":
        rec["swap_why"] = f"no item list (Item.Item) after the move's second Confirm (read {_where(g)})"
    return swap_measured(rec)


def _key_steps(g, rec: dict) -> bool:
    """GM0-LOCAL's key-item read: the rail's Key (the rail label is 'Key'), Item.KeyItem, Confirm on the seeded key item -- its description
    opens (DisplayKeyItemSkin: DisableAllGroup empties the group) -- then Cancel: it closes back onto Item.KeyItem, the local write (the
    read marker, FF9Item_UseImportant, ItemUI.cs:865 via :492-496). Records key_label / opened / closed; True when every press ran."""
    whys = []
    if not _item_rail(g, rec):
        return False
    if not _pick(g, "Key", directions=("right", "down"), why=whys):
        rec["why"] = f"no 'Key' on the Item rail ({'; '.join(whys)})"
        return False
    if _group(g, "Item.KeyItem", "the key-item list") is None:
        rec["why"] = f"no Item.KeyItem after the rail's Key (read {_where(g)})"
        return False
    rec["key_label"] = _label(g)
    rec["trail"].append(_where(g))
    ui = g.state.ui_state
    g.press("confirm")
    rec["opened"] = cb.poll(g, lambda s: s.ui_state == ui and getattr(s, "menu_group", None) != "Item.KeyItem", SEL_S,
                            "the key item's description (the group emptied)") is not None
    rec["trail"].append(_where(g))
    g.wait_frames(TWEEN_FRAMES)                              # the description's TweenIn holds Loading: a Cancel inside it is swallowed
    g.press("cancel")
    rec["closed"] = bool(rec["opened"]) and cb.poll(g, lambda s: getattr(s, "menu_group", None) == "Item.KeyItem", SEL_S,
                                                    "the description closed (back on the key list)") is not None
    rec["trail"].append(_where(g))
    return True


def _local_steps(g, ctx: dict | None = None) -> list:
    """GM0-LOCAL's reads (no census hook): the sort (Arrange > Auto, Arrange > Manual: the MEASURED swap), the key-item read (needs GMBAG's
    key item: ctx['bag_why'] names the seeder otherwise), the root's Folklore / Journal."""
    out = []
    for what in ("sort", "key items", "folklore"):
        _back_to_root(g)
        rec = {"what": what, "reached": False, "why": "", "before": snap(g.state), "trail": []}
        if what == "sort":
            rec["reached"] = _sort_steps(g, rec)
        elif what == "key items":
            if (ctx or {}).get("bag_why"):
                rec["why"] = ctx["bag_why"]
            elif BAG_KEY_ITEM is None:
                rec["why"] = bag_key_why()
            else:
                rec["reached"] = _key_steps(g, rec)
        else:
            rec["reached"] = any(goto_screen(g, lb)[0] is not None for lb in OPTIONAL_SCREENS)
            rec["why"] = "" if rec["reached"] else f"no {OPTIONAL_SCREENS} on the root"
        g.wait_frames(SETTLE_FRAMES)
        rec["after"] = snap(g.state)
        out.append(rec)
        _back_to_root(g)
    return out


def _why_args(args, ctx) -> list:
    return [str(ALT_FIELD) if a == "<alt>" else str(ctx["marker"]) if a == "<marker>" else str(a) for a in args]


def _leg_why(g, led: cb.Ledger, ctx: dict) -> None:
    for row, whys, ops, undo in WHY_CASES:
        if _ready(g, ctx) is None:
            led.check(row, False, f"not reached: no FieldHUD with control (ui {g.state.ui_state!r})")
            continue
        if row == "GM0-WHY-NODATA" and not ctx["pulled"]:
            _gmop(g, ctx, "clear")                           # no bench frame (one left by an earlier leg of the chain dropped)
        elif row != "GM0-WHY-NODATA":
            _frame(g, ctx, ctx["marker"])
        sent = []
        for op in ops:
            args = _why_args(op, ctx)
            ok, why = (_gmop(g, ctx, *args[1:]) if args[0] == "guestmenu" else _ns(g, *args))
            sent.append(f"`{' '.join(args)}` {'ok' if ok else 'REFUSED: ' + why}")
        base = snap(g.state)
        out, s = press_menu(g, ctx)
        if out in ("seated", "own"):
            cancel_out(g, ctx)
        ok, detail = judge_why(whys, base, s)
        if row == "GM0-WHY-BUSY":                            # the follow in flight is real: it lands on ALT_FIELD (DESIGN D1)
            landed = s.get("field") == ALT_FIELD
            ok, detail = ok and landed, f"{detail}; the follow landed on {s.get('field')!r} (want {ALT_FIELD}) {landed}"
        led.check(row, ok, f"{'; '.join(sent) or 'no op'}; the press: {out}; {detail}")
        for op in undo:
            args = _why_args(op, ctx)
            if args[0] == "guestmenu":
                _gmop(g, ctx, *args[1:])
            else:
                _ns(g, *args)
    # WHY-BUSY's follow lands on ALT_FIELD: home again
    _home(g, ctx)


def _home(g, ctx: dict, field: int | None = None) -> bool:
    """Back on FieldHUD ``field`` (the bench field by default) with nothing open and NOTHING SEATED -- a record a leg left held on the HUD
    (a faulted restore door, a boot over a seat) is retried at the next door and Cancelled, so no leg inherits another's seat."""
    field = field or ctx.get("field") or GM_FIELD
    st = g.state
    if st.ui_state in BW.GM_MENU_STATES:
        cancel_out(g, ctx)
    cb.poll(g, lambda s: s.ui_state == "FieldHUD" and not getattr(s, "fading", False), CLOSE_S, "a field")
    if ctx.get("new") and _gm(g.state).get("seated") and g.state.ui_state in HUDS and g.state.control:
        g.note("a seat left held on the HUD: the next door retries its restore")
        out, _s = press_menu(g, ctx)
        if out in ("seated", "own"):
            cancel_out(g, ctx)
    if g.state.field_id != field:
        try:
            g.warp(field)
        except HarnessError as err:
            g.note(f"the way home to {field} failed: {str(err)[:160]}")
        cb.poll(g, lambda s: s.ui_state == "FieldHUD" and s.field_id == field and s.control, CLOSE_S, f"home on {field}")
        g.wait_frames(SETTLE_FRAMES)
    return g.state.field_id == field


def _leg_witness(g, led: cb.Ledger, ctx: dict) -> None:
    places = (ctx["field"], ALT_FIELD)
    for i, comp in enumerate(WITNESS_COMPS):
        row = f"GM0-WITNESS-{comp.upper()}"
        _home(g, ctx, places[i % 2])                         # THE DECLINE LATCH: each variant's line on a fresh place
        if _ready(g, ctx) is None:
            led.check(row, False, f"not reached: no FieldHUD with control on {places[i % 2]}")
            continue
        at = cb.mark(g)
        okf, whyf = _gmop(g, ctx, "frame", "witness", comp)
        if not okf:
            led.check(row, False, f"`frame witness {comp}` refused: {whyf}")
            continue
        base = snap(g.state)
        out, s = press_menu(g, ctx)
        if out in ("seated", "own"):
            cancel_out(g, ctx)
        led.check(row, *judge_witness(comp, base, s, cb.new(g, at)))
    _home(g, ctx)
    at = cb.mark(g)
    okf, whyf = _gmop(g, ctx, "frame", "witness", BW.GM_COMP_KEY_ITEM)
    out, s = press_menu(g, ctx) if okf else ("none", snap(g.state))
    closed = cancel_out(g, ctx) if out in ("seated", "own") else None
    led.check("GM0-WITNESS-KEYITEM", *(judge_keyitem(s, closed, cb.new(g, at)) if okf else (False, f"refused: {whyf}")))
    for comp in FP_COMPS:
        row = f"GM0-SEATFAULT-{comp.upper()}"
        if _ready(g, ctx) is None:
            led.check(row, False, "not reached: no FieldHUD with control")
            continue
        _frame(g, ctx, ctx["marker"])
        at = cb.mark(g)
        okf, whyf = _gmop(g, ctx, "seat", "fault", comp)
        if not okf:
            led.check(row, False, f"`seat fault {comp}` refused: {whyf}")
            continue
        base = snap(g.state)
        out, s = press_menu(g, ctx)
        if out in ("seated", "own"):
            cancel_out(g, ctx)
        lines = cb.new(g, at)
        ok2, _w2, s2 = _seat(g, ctx)
        nxt = (_n(s2, "fp", default={}) or {}).get("before") if ok2 else None
        if ok2:
            cancel_out(g, ctx)
        led.check(row, *judge_seatfault(comp, base, s, lines, nxt))


def _leg_door(g, led: cb.Ledger, ctx: dict) -> None:
    # FAULT-OPEN: one clean cycle first (the HUD's Show after a normal close), then the faulted door
    ok, why, _s = _seat(g, ctx, marker=ctx["marker"])
    if ok:
        cancel_out(g, ctx)
        okf, whyf = _gmop(g, ctx, "door", "fault", "open")
        base = snap(_ready(g, ctx) or g.state)
        out, s = press_menu(g, ctx)
        if out in ("seated", "own"):
            cancel_out(g, ctx)
        v = judge_door_open(base, s)
        led.check("GM0-DOOR-FAULT-OPEN", v[0] and okf, (f"`door fault open` {'ok' if okf else 'REFUSED: ' + whyf}; the press: {out}; "
                                                       + v[1]))
    else:
        led.check("GM0-DOOR-FAULT-OPEN", False, f"not reached: the clean cycle never seated ({why})")
    # FAULT-RESTORE
    base = snap(_ready(g, ctx) or g.state)
    ok, why, _s = _seat(g, ctx)
    if not ok:
        led.check("GM0-DOOR-FAULT-RESTORE", False, f"not reached: never seated ({why})")
    else:
        _gmop(g, ctx, "door", "fault", "restore")
        _back_to_root(g)
        g.press("cancel")
        held = snap(cb.poll(g, lambda s: s.ui_state == "FieldHUD", CLOSE_S, "the HUD after the faulted restore door") or g.state)
        g.wait_frames(SETTLE_FRAMES)
        held = snap(g.state) if held.get("ui") == "FieldHUD" else held
        out, reseat = press_menu(g, ctx)
        closed = cancel_out(g, ctx) if out in ("seated", "own") else snap(g.state)
        led.check("GM0-DOOR-FAULT-RESTORE", *judge_door_restore(base, held, reseat, closed))
    # 889: the dialogue path, on STRIP_FIELD -- its persistent [NFOC] strip is the window up at the press (an NPC talk's UCOFF would clear
    # menu control, and the press would take UIKeyTrigger.cs:896's return before OnKeyMenu: no door at all). [NFOC] sets FlagButtonInh, so
    # term 12 (AnyEtbLine(false)) skips the strip and cannot refuse `ui` ahead of F1. No `bench 0` / `bench 1`: BenchGates survives the
    # warp (NetSyncClient.cs:14997), and no _close_window: whether the strip stays closed is the Known limit the row MEASURES
    _home(g, ctx, STRIP_FIELD)
    st0 = cb.poll(g, lambda s: s.ui_state == "FieldHUD" and s.control and getattr(s, "dialog_open", False)
                  and _gm(s).get("event_enable") is True, 5.0, "the strip up on FieldHUD with control and events on")
    if st0 is None:
        led.check("GM0-DOOR-889", *judge_door_889({}, {}, False))
        g.note(f"GM0-DOOR-889: no strip up on {STRIP_FIELD} (field {g.state.field_id}, ui {g.state.ui_state!r}, window "
               f"{getattr(g.state, 'dialog_open', None)!r}, control {g.state.control})")
        _home(g, ctx)
        return
    _frame(g, ctx, ctx["marker"])                            # re-arms the bench host on STRIP_FIELD, then `host elsewhere` moves it off
    _gmop(g, ctx, "host", "elsewhere")
    still = bool(getattr(g.state, "dialog_open", False))
    base = snap(g.state)
    g.press("menu")
    st = cb.poll(g, lambda s: _door_total(snap(s)) > _door_total(base) or s.ui_state == "MainMenu", OPEN_S, "the door's verdict")
    back = (cb.poll(g, lambda x: x.ui_state == "FieldHUD" and x.control and _gm(x).get("event_enable") is True, CLOSE_S,
                    "the HUD back after the door (control and events on; a window NOT waited for)") or g.state) if st is not None else g.state
    s = snap(back)
    if s.get("ui") == "MainMenu":
        s = cancel_out(g, ctx)
    _gmop(g, ctx, "host", "here")
    led.check("GM0-DOOR-889", *judge_door_889(base, s, still))
    _home(g, ctx)


def _talk_open(g, ctx: dict) -> tuple:
    """The scribe's window up (a LOCAL talk, `bench 0`: the F1 field gate never lets a spectator's own talk start): (open, why)."""
    _ns(g, "bench", 0)
    _home(g, ctx)
    try:
        g.walk_to(*SCRIBE_AT, tolerance=45, strict=False)
    except (HarnessError, TypeError) as err:
        return False, f"the walk to the scribe failed: {str(err)[:160]}"
    try:
        st = g.interact(timeout=TALK_S)
    except HarnessError as err:
        return False, f"the talk raised: {str(err)[:160]}"
    if st is None or not getattr(st, "dialog_open", False):
        return False, "no window opened beside the scribe"
    return True, ""


def _close_window(g) -> None:
    for _ in range(12):
        if not getattr(g.state, "dialog_open", False):
            return
        g.press("confirm")
        g.wait_frames(12)


def _leg_close(g, led: cb.Ledger, ctx: dict) -> None:
    bound = depth_ms(ctx.get("fade_ms"))
    reopens = []
    for d in DEPTHS:
        row = f"GM0-DEPTH-{d.upper()}"
        ok, why, _s = _seat(g, ctx, marker=ctx["marker"] if d == "root" else None)
        reopens.append(ok)
        if not ok:
            led.check(row, False, f"not reached: {why}")
            continue
        if d != "root" and goto_screen(g, d)[0] is None:
            led.check(row, False, f"not reached: {d} never opened")
            cancel_out(g, ctx)
            continue
        base = snap(g.state)
        at = cb.mark(g)
        okf, whyf = _gmop(g, ctx, "fireclose", "leave")
        st = cb.poll(g, lambda s: s.ui_state == "FieldHUD" and _gm(s).get("close_pending") is False and not _gm(s).get("seated"),
                     CLOSE_S, "the forced close's end")
        s = snap(_ready(g, ctx) or g.state)
        lines = cb.new(g, at)
        if ctx["pulled"] == "closeold":
            _measure(ctx, row, close_old_measured(base, s, lines))
        if st is None and _n(s, "seated", default=False):
            s = cancel_out(g, ctx)
        led.check(row, *judge_depth(d, base, s, lines, bound))
    # DEPTH-FAULT: `close fault sub` at Item, `close fault root` at the root
    faults = []
    for step, where in (("sub", "Item"), ("root", "root")):
        ok, why, _s = _seat(g, ctx)
        reopens.append(ok)
        if not ok or (where != "root" and goto_screen(g, where)[0] is None):
            if ok:
                cancel_out(g, ctx)
            continue
        _gmop(g, ctx, "close", "fault", step)
        base = snap(g.state)
        at = cb.mark(g)
        _gmop(g, ctx, "fireclose", "leave")
        cb.poll(g, lambda s: s.ui_state == "FieldHUD" and not _gm(s).get("close_pending"), CLOSE_S, "the faulted close's end")
        s = snap(_ready(g, ctx) or g.state)
        faults.append((step, base, s, cb.new(g, at)))
        if ctx["pulled"] == "closeold":
            _measure(ctx, "GM0-DEPTH-FAULT", close_old_measured(base, s, cb.new(g, at)))
        if _n(s, "seated", default=False) or s.get("ui") in BW.GM_MENU_STATES:
            cancel_out(g, ctx)
    led.check("GM0-DEPTH-FAULT", *judge_depth_fault(faults))
    # CLOSE-IDS: each of the eight ids from the root
    ids = []
    for cause in BW.GM_CLOSE_IDS:
        ok, why, _s = _seat(g, ctx)
        reopens.append(ok)
        if not ok:
            continue
        base = snap(g.state)
        at = cb.mark(g)
        _gmop(g, ctx, "fireclose", cause)
        cb.poll(g, lambda s: s.ui_state == "FieldHUD" and _gm(s).get("close_pending") is False and not _gm(s).get("seated"), CLOSE_S,
                f"the {cause} close's end")
        s = snap(_ready(g, ctx) or g.state)
        lines = cb.new(g, at)
        if ctx["pulled"] == "closeold":
            _measure(ctx, "GM0-CLOSE-IDS", close_old_measured(base, s, lines, cause))
        if _n(s, "seated", default=False):
            s = cancel_out(g, ctx)
        ids.append((cause, base, s, lines))
    led.check("GM0-CLOSE-IDS", *judge_close_ids(ids, bound))
    # REOPEN: a normal Cancel, then a fireclose with no seat; then the own menu under `guestmenu old`
    ok, why, _s = _seat(g, ctx)
    cancel_base = cancel_out(g, ctx) if ok else snap(g.state)
    at = cb.mark(g)
    _gmop(g, ctx, "fireclose", "leave")
    g.wait_frames(SETTLE_FRAMES)
    after_fire = snap(g.state)
    fire_lines = cb.new(g, at)
    own = {"opened": False, "open": None, "seated": None}
    pulled_old = ctx["pulled"] == "old"
    if pulled_old or _gmop(g, ctx, "old")[0]:
        out, so = press_menu(g, ctx)
        own.update(opened=out == "own", open=_n(so, "open", default=None), seated=_n(so, "seated", default=None))
        if so.get("ui") == "MainMenu":
            shot = cb.shot(g, "s168-reopen-own-menu")[0]
            if shot:
                g.note(f"GM0-REOPEN: the own menu after the session: {shot} (READ it: Order, Card and Config NOT grey)")
        cancel_out(g, ctx)
        if not pulled_old:
            _gmop(g, ctx, "act")
    led.check("GM0-REOPEN", *judge_reopen(reopens, cancel_base, after_fire, fire_lines, own))


def _leg_quit(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why, _s = _seat(g, ctx, marker=ctx["marker"])
    if not ok:
        led.check("GM0-QUIT", False, f"not reached: {why}")
        return
    okq, whyq = _ns(g, "endbench", "quit", "on")
    if not okq:
        led.check("GM0-QUIT", False, f"not reached: `endbench quit on` refused: {whyq}")
        cancel_out(g, ctx)
        return
    base = snap(g.state)
    at = cb.mark(g)
    _gmop(g, ctx, "fireclose", "leave")
    waiting = [snap(st) for st in cb.hold_for(g, QUIT_WAIT_S)]
    wait_lines = cb.new(g, at)
    g.press("cancel")                                        # the prompt's Cancel by KEY (NEVER Confirm: its Yes quits)
    cb.poll(g, lambda s: s.ui_state == "FieldHUD" and _gm(s).get("close_pending") is False and not _gm(s).get("seated"), CLOSE_S,
            "the close's end after the prompt's Cancel (last_close.end is stamped one service tick after the HUD's Show)")
    s = snap(_ready(g, ctx) or g.state)
    if ctx["pulled"] == "closeold":
        _measure(ctx, "GM0-QUIT", close_old_measured(base, s, cb.new(g, at)))
    if s.get("ui") != "FieldHUD":
        _ns(g, "endbench", "quit", "off")
        s = cancel_out(g, ctx)
    led.check("GM0-QUIT", *judge_quit(base, waiting, wait_lines, s, cb.new(g, at)))


def _save_files(save_path) -> dict | None:
    if not save_path:
        return None
    root = Path(str(save_path))
    root = root if root.is_dir() else root.parent
    try:
        return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}
    except OSError:
        return None


def _exited(g) -> bool:
    proc = getattr(g, "proc", None)
    try:
        return proc is not None and proc.poll() is not None
    except Exception:                                        # noqa: BLE001 - a dead handle reads as exited
        return True


def _leg_quitexit(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why, s = _seat(g, ctx, marker=ctx["marker"])
    saves0 = _save_files(s.get("save"))
    okq, whyq = _ns(g, "endbench", "quit", "on") if ok else (False, why)
    if ok and okq:
        if not any(_pick(g, lbl, confirm=False, max_steps=4) for lbl in QUIT_LABELS):
            g.note(f"GM0-QUIT-EXIT: no {QUIT_LABELS} label published on the prompt -- the highlighted row is confirmed")
        try:
            g.press("confirm")                               # DESTRUCTIVE: the prompt's Quit
        except HarnessError:
            pass
    exited = False
    if ok and okq:
        import time as _time
        deadline = _time.time() + EXIT_S
        while _time.time() < deadline and not exited:
            exited = _exited(g)
            _time.sleep(0.2)
    ctx["exited"] = exited
    led.check("GM0-QUIT-EXIT", *judge_quit_exit(ok, okq, exited, saves0, _save_files(s.get("save"))))


def _leg_held(g, led: cb.Ledger, ctx: dict) -> None:
    stand, why = _talk_open(g, ctx)
    _close_window(g)
    _ns(g, "bench", 1)
    if not stand:
        led.check("GM0-HELDKEY", *judge_held(False, {}, [], {}, False))
        g.note(f"GM0-HELDKEY: {why}")
        return
    ok, why, _s = _seat(g, ctx, marker=ctx["marker"])
    if not ok:
        led.check("GM0-HELDKEY", False, f"not reached: {why}")
        return
    base = snap(g.state)
    try:
        g.hold("confirm", HELD_FRAMES)
    except HarnessError as err:
        led.check("GM0-HELDKEY", False, f"`hold confirm` refused: {str(err)[:160]}")
        cancel_out(g, ctx)
        return
    g.wait_frames(10)
    _gmop(g, ctx, "fireclose", "leave")
    cb.poll(g, lambda s: s.ui_state == "FieldHUD" and not _gm(s).get("seated"), CLOSE_S, "the close under the held Confirm")
    held = hold_samples(g, 0.8)
    try:
        g.release("confirm")
    except HarnessError:
        pass
    g.wait_frames(SETTLE_FRAMES)
    s_back = snap(_ready(g, ctx) or g.state)
    _ns(g, "bench", 0)
    g.press("confirm")
    talk = cb.poll(g, lambda s: getattr(s, "dialog_open", False), TALK_S, "the talk on the real re-press") is not None
    _close_window(g)
    _ns(g, "bench", 1)
    led.check("GM0-HELDKEY", *judge_held(True, base, held, s_back, talk))


def _leg_master(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why, s = _seat(g, ctx, marker=ctx["marker"])
    if not ok:
        led.check("GM0-MASTER", False, f"not reached: {why}")
        return
    m0 = snap(g.state)
    returns = 0
    for label in ("Item", "Status"):
        if goto_screen(g, label)[0] is not None and _back_to_root(g):
            returns += 1
            g.wait_frames(SETTLE_FRAMES)
    m1 = snap(g.state)
    cancel_out(g, ctx)
    led.check("GM0-MASTER", *judge_master(m0, m1, returns))


def _leg_diorama(g, led: cb.Ledger, ctx: dict) -> None:
    # GM0-SILENT first, from a clean field (no seat anywhere): the bench's own step inside a booted diorama
    _ready(g, ctx)
    booted, bwhy = cb.boot(g)
    if not booted:
        led.check("GM0-SILENT", *judge_silent(False, None, {}, {}))
        g.note(f"GM0-SILENT: {bwhy}")
    else:
        cb.wait_steady(g)
        st = g.state
        now = _mr(st).get("now")
        base = snap(st)
        g.press("menu")
        g.wait_frames(30)
        s = snap(g.state)
        if s.get("ui") in BW.GM_MENU_STATES:
            cancel_out(g, ctx)
        led.check("GM0-SILENT", *judge_silent(True, now, base, s))
        cb.leave(g, ctx["field"])
    # GM0-DIORAMA-BOOT: a boot asked while seated
    _home(g, ctx)
    ok, why, _s = _seat(g, ctx, marker=ctx["marker"])
    if not ok:
        led.check("GM0-DIORAMA-BOOT", False, f"not reached: {why}")
        return
    booted, bwhy = cb.boot(g)
    s = snap(g.state)
    if booted:
        cb.leave(g, ctx["field"])
    led.check("GM0-DIORAMA-BOOT", *judge_dio_boot(True, bwhy if not booted else "BOOTED over the seat", s))
    if g.state.ui_state in BW.GM_MENU_STATES:
        cancel_out(g, ctx)


def _leg_release(g, led: cb.Ledger, ctx: dict) -> None:
    _frame(g, ctx, ctx["marker"])
    _gmop(g, ctx, "host", "elsewhere")
    for op in BW.GUEST_MENU_RELEASE_SET.values():
        _gmop(g, ctx, *op)
    set_snap = snap(g.state)
    at = cb.mark(g)
    cb.release(g)
    after = snap(g.state)
    lines_reset = cb.new(g, at)
    at2 = cb.mark(g)
    cb.release(g)
    lines_bare = cb.new(g, at2)
    okr, whyr = cb.try_ns(g, "selftest", 1)
    _ns(g, "bench", 1)
    at3 = cb.mark(g)
    ok, why, seat2 = _seat(g, ctx, marker=MARKER2)
    if ok:
        cancel_out(g, ctx)
    led.check("GM0-RELEASE", *judge_release(set_snap, after, lines_reset, lines_bare, seat2, cb.new(g, at3), MARKER2))


def _leg_softreset(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why, _s = _seat(g, ctx, marker=ctx["marker"])
    if not ok:
        led.check("GM0-SOFTRESET", False, f"not reached: {why}")
        return
    base = snap(g.state)
    _gmop(g, ctx, "door", "fault", "restore")
    _back_to_root(g)
    g.press("cancel")
    cb.poll(g, lambda s: s.ui_state == "FieldHUD" and s.control, CLOSE_S, "the HUD with the seat held")
    g.wait_frames(SETTLE_FRAMES)
    held = snap(g.state)
    at = cb.mark(g)
    title = False
    try:
        g.soft_reset(timeout=20.0)
        title = g.state.ui_state == "Title"
    except HarnessError as err:
        g.note(f"GM0-SOFTRESET: {str(err)[:200]}")
    s = snap(g.state)
    lines = cb.new(g, at)
    newgame_ok = False
    if title:
        try:
            g.newgame()
            newgame_ok = g.state.ui_state == "FieldHUD"
        except HarnessError as err:
            g.note(f"GM0-SOFTRESET: New Game after the title failed: {str(err)[:200]}")
    led.check("GM0-SOFTRESET", *judge_softreset(held, title, base, s, lines, newgame_ok))


def _leg_cfg(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why, _s = _seat(g, ctx, marker=ctx["marker"])
    if not ok:
        led.check("GM0-RAMP-CFG", False, f"not reached: {why}")
        return
    base = snap(g.state)
    import _coop_peer_bench as pb
    # a TRANSPORT-signature edge against the ini's OWN Role: LoadConfigIfChanged compares the ini with its own last committed read, never
    # the forced role (NetSyncClient.cs:3154-3170), so neither Enabled=0 (solo_ini's) nor the install's own Role is an edge on this bench
    cur = str(cb.ini_value(g, "Netsync", "Role") or "selftest").strip().lower()
    role = "host" if cur == "client" else "client"
    guard = pb.IniGuard(Path(g.game_path) / "Memoria.ini", {"Role": role}, label="s168-gm-cfg", run_dir=getattr(g, "run_dir", None))
    edited = heard = False
    at = cb.mark(g)
    try:
        g.note(f"GM0-RAMP-CFG: the ini's own Role {cur!r} -> {role!r}: {guard.apply()}")
        edited = bool(guard.changes)
        if edited:
            cb.poll(g, lambda s: _gm(s).get("seated") is False and s.ui_state == "FieldHUD", CFG_S, "the `ending` close")
        s = snap((_ready(g, ctx) if edited else None) or g.state)
        heard = edited and cb.count(cb.new(g, at), "[NetSync] config change applied live") >= 1
    except (OSError, RuntimeError) as err:
        g.note(f"GM0-RAMP-CFG: the ini edit failed: {err}")
        s = snap(g.state)
    finally:
        okr, detail = guard.restore()
        g.note(f"GM0-RAMP-CFG: the ini restore {'OK' if okr else 'FAILED'}: {detail}")
    if ctx["pulled"] == "closeold":
        _measure(ctx, "GM0-RAMP-CFG", heard and _n(s, "seated", default=False) and _d(base, s, "closes", "ending") == 0)
    if _n(s, "seated", default=False) or s.get("ui") in BW.GM_MENU_STATES:
        cancel_out(g, ctx)
    if heard:   # the restore is an edge too: it commits the ini's own Enabled 0 / Role over the forced role (bench refused after it)
        cb.poll(g, lambda st: cb.path(st, "netsync.role") == cur, CFG_S, "the restore re-read")
        cb.release(g)                                        # reset FIRST: `selftest 1` is a no-op while the old override flag holds
        cb.try_ns(g, "selftest", 1)
        _ns(g, "bench", 1)
    led.check("GM0-RAMP-CFG", *judge_cfg(base, s, heard))


def _leg_world(g, led: cb.Ledger, ctx: dict) -> None:
    import coop_world_walk as ww                             # the s165 route through round A's landing (imported, never copied)
    ok, why, _ss, _b = ww._a_land(g, {"calibrate": False})
    if not ok:
        led.check("GM0-WORLDTAG4", False, f"not reached: the landing on {WORLD}: {why}")
        return
    st = cb.poll(g, lambda s: s.ui_state == "WorldHUD" and cb.path(s, "world.block_ready") is True and s.control
                 and _gm(s).get("uid0_vars") is not None, CLOSE_S, "WorldHUD with the blocks in (THE PRE-INIT SAMPLE)")
    before = snap(st or g.state)
    okw, whyw, _s = _seat(g, ctx, marker=ctx["marker"], world=True)
    if not okw:
        led.check("GM0-WORLDTAG4", False, f"not reached: {whyw}")
        return
    sub_ok = goto_screen(g, "Item")[0] is not None and _back_to_root(g)
    s = cancel_out(g, ctx, world=True)
    st2 = cb.poll(g, lambda x: (_gm(x).get("outside_settled") or {}).get("set") is True, CLOSE_S, "the settle stamped")
    s = snap(st2) if st2 is not None else s
    if ctx["pulled"] == "poke":
        _measure(ctx, "GM0-WORLDTAG4", (_n(s, "outside_settled", default={}) or {}).get("named") == "events")
    led.check("GM0-WORLDTAG4", *judge_worldtag4(before, s, sub_ok, WORLD))


FNS = {"seat": _leg_seat, "refuse": _leg_refuse, "deep": lambda g, led, ctx: _leg_refuse(g, led, ctx, DEEP_SITES, deep=True),
       "why": _leg_why, "witness": _leg_witness, "door": _leg_door, "close": _leg_close, "quit": _leg_quit, "quitexit": _leg_quitexit,
       "held": _leg_held, "master": _leg_master, "diorama": _leg_diorama, "release": _leg_release, "softreset": _leg_softreset,
       "cfg": _leg_cfg, "world": _leg_world}


# ------------------------------------------------------------------------------------------------ the run
def run(g, field: int | None = None):
    calibrate = cb.CALIBRATE
    legs = SOLO_LEGS or ()
    lever = lever_of(legs[0], LEVER_RAW) if calibrate and len(legs) == 1 else None
    led = cb.Ledger(g, catalog(legs, lever, calibrate=calibrate), finals=("S168-R", "S168-CAL"), width=DETAIL_W)
    world = "world" in legs
    ctx = {"calibrate": calibrate, "legs": legs, "lever": lever, "pulled": None, "new": False, "measured": {}, "marker": MARKER,
           "field": FARSHORE if world else GM_FIELD, "fade_ms": None, "stage": None, "own_seen": False, "exited": False, "bag_why": None}
    if not legs:
        led.check("S168-INI", False, f"COOP_GM_LEG={_RAW_LEG!r} names no leg: one of {LEGS} (or {CHAIN!r})")
        led.close("not launched: no leg named", final=True)
        return
    if world and len(legs) > 1:
        led.check("S168-INI", False, f"COOP_GM_LEG={_RAW_LEG!r} mixes the world leg with field legs: one route per launch")
        led.close("not launched: one route per launch", final=True)
        return
    if calibrate and len(legs) != 1:
        led.check("S168-CAL", False, f"EACH LEG NEEDS ITS OWN LAUNCH: COOP_CALIBRATE=1 needs COOP_GM_LEG naming exactly one of {LEGS} "
                                     f"(got {_RAW_LEG!r}) -- nothing was launched")
        led.close("not launched: a calibration names exactly one leg", final=True)
        return
    if calibrate and LEVER_RAW is not None and lever is None:
        led.check("S168-CAL", False, f"COOP_GM_LEVER={LEVER_RAW!r} is not leg {legs[0]!r}'s: one of {LEG_LEVERS[legs[0]] or '(none)'} -- "
                                     "nothing was launched")
        led.close("not launched: the lever is not this leg's", final=True)
        return
    try:
        _round(g, led, ctx)
    except HarnessError as err:
        _note(g, ctx, f"the leg raised: {str(err)[:400]}")
        led.close(f"the leg raised ({str(err)[:200]})")
    finally:
        try:
            _finish(g, led, ctx, legs)
        except HarnessError as err:                          # GM0-QUIT-EXIT: the game is gone -- the ledger still closes
            print(f"[coop_guest_menu] the finish raised: {str(err)[:300]}")
        led.close(final=True)


def _note(g, ctx: dict, text: str) -> None:
    """g.note, never to a game that exited (GM0-QUIT-EXIT)."""
    if ctx.get("exited"):
        print(f"[coop_guest_menu] {text}")
    else:
        g.note(text)


def _finish(g, led: cb.Ledger, ctx: dict, legs) -> None:
    _note(g, ctx, f"Memoria.log archived: {cb.archive_log(g, 'guest-menu')}")
    led.close()
    if not ctx.get("exited"):
        _release(g, led, ctx)
    if ctx.get("stage") is None:
        led.check("S168-CAL", False, "no engine stage was read (the run died before P0)")
        return
    pred = (old_predicted(legs) if not ctx["new"] else lever_predicted(legs[0], ctx["pulled"]) if ctx["pulled"] else ())
    pred = tuple(r for r in pred if r in led.catalog)
    needs = tuple(r for r in pred if r not in SETUP and r != "S168-P1")
    if ctx["new"] and BAG_KEY_ITEM is None and "GM0-LOCAL" in led.catalog and "GM0-LOCAL" not in pred:
        pred += ("GM0-LOCAL",)                               # GMBAG's KNOWN GAP: no key item, so the key read can never run (not in needs)
    _note(g, ctx, f"S168-CAL: {'s168' if ctx['new'] else 'OLD (s167)'}, legs {list(legs)}, lever {ctx['pulled']!r}: predicted reds "
                  f"{sorted(pred)}")
    led.check("S168-CAL", *judge_cal(led.failed() - {"S168-CAL"}, pred, ctx["measured"], needs))


def _round(g, led: cb.Ledger, ctx: dict) -> None:
    en, fh = cb.ini_value(g, "Netsync", "Enabled"), cb.ini_value(g, "Netsync", "FollowHost")
    ini_ok = (en is None or str(en).strip() in ("0", "")) and fh is not None and str(fh).strip() == "1"
    led.check("S168-INI", ini_ok, f"[Netsync] Enabled {en!r}, FollowHost {fh!r}" + ("" if ini_ok else " -- write them BEFORE launch "
                                                                                      "(solo_ini.py): nothing was sent"))
    if not ini_ok:
        led.close("the install's ini refuses the bench (S168-INI)")
        return
    fade = cb.ini_value(g, "Interface", "FadeDuration")
    ctx["fade_ms"] = int(fade) if fade is not None and str(fade).strip().isdigit() else None
    bag = any(leg in BAG_LEGS for leg in ctx["legs"])
    ok, why, ctx["bag_why"] = _setup(g, ctx["field"], label="s168: the guest's main menu, rung 0 (view only) -- the solo bench"
                                     + (" -- CALIBRATION" if ctx["calibrate"] else ""), bag=bag)
    led.check("S168-S0", ok and g.state.field_id == ctx["field"], why + f"; on field {g.state.field_id}"
              + (f"; the bag seeder: {'seeded' if ctx['bag_why'] is None else ctx['bag_why']}" if bag else ""))
    if not ok:
        led.close(f"the selftest role never came up -- {why}")
        return
    st = g.state
    ctx["new"] = cb.has(st, PROBE)
    ctx["stage"] = 168 if ctx["new"] else 167
    g.note(f"engine stage: s{ctx['stage']} ({cb.stage_note(st)}); FadeDuration {ctx['fade_ms']!r} ms; marker {ctx['marker']}")
    led.check("S168-P0", *judge_probe(st))
    ww_want, sb_want, gm_want, where = proof_wants()
    g.note(f"GM0-PROOF's wants: world walk {ww_want}, seat bracket {sb_want}, guest menu {gm_want} ({where})")
    led.check("GM0-PROOF", *judge_proof(cb.log_lines(g), ww_want, sb_want, gm_want))
    _p1(g, led, ctx)
    legs = ctx["legs"]
    if not ctx["new"]:
        shape = old_shape(g, ctx)
        rows = leg_rows(legs)
        _measure(ctx, rows, shape)
        led.unreached(rows, "OLD: no `netsync.guestmenu` -- an engine before s168 (the `guestmenu` verb unknown: it fails closed; nothing "
                            f"sent); s121's bench reading `open` {'measured' if shape else 'NOT measured'}")
        return
    if ctx["pulled"] == "old":
        _measure(ctx, leg_rows(legs), old_shape(g, ctx))
    for leg in LEGS:
        if leg in legs and leg in FNS:
            g.note(f"== leg {leg}")
            FNS[leg](g, led, ctx)
            if leg not in ("quitexit", "softreset", "world") and not ctx.get("exited"):
                _home(g, ctx)
                _ns(g, "bench", 1)


def _p1(g, led: cb.Ledger, ctx: dict) -> None:
    ok, why = cb.try_ns(g, "bench", 1)
    st = cb.poll(g, lambda s: (s.netsync or {}).get("bench") is True, 3.0, "the field-gate bench") or g.state
    if not ok:
        led.check("S168-P1", False, f"`netsync bench 1` refused: {why}")
        return
    if not ctx["new"]:
        led.check("S168-P1", *judge_rest(st, {}))
        return
    want = dict(BW.GUEST_MENU_LEVER_DEFAULTS)
    note = ""
    lever = ctx["lever"]
    if ctx["calibrate"] and lever in LEVER_OPS:
        okl, whyl = _gmop(g, ctx, *LEVER_OPS[lever])
        field, word = LEVER_READ[lever]
        want[field] = word
        ctx["pulled"] = lever if okl else None
        note = f"; CALIBRATION `guestmenu {' '.join(LEVER_OPS[lever])}` {'pulled (held through the run)' if okl else 'REFUSED: ' + whyl}"
    st = cb.poll(g, lambda s: judge_rest(s, want)[0], 3.0, "the guestmenu levers read back") or g.state
    ok, why = judge_rest(st, want)
    led.check("S168-P1", ok, why + note)


def _release(g, led: cb.Ledger, ctx: dict) -> None:
    """S168-R: a lever pulled just before `reset` (so the release line is owed), the role released, the levers at their defaults."""
    if "S168-R" not in led.catalog:
        return
    if ctx.get("new"):
        _ns(g, "bench", 1)                                   # the bench lever a title or a leg may have dropped
        _gmop(g, ctx, "chip", "off")
    at = cb.mark(g)

    def extra(st):
        if not ctx.get("new"):
            return True, "OLD: no guestmenu lever to read"
        gm = _gm(st)
        ok = (gm.get("lever") or {}) == BW.GUEST_MENU_LEVER_DEFAULTS and (gm.get("bench") or {}).get("marker") == -1
        return ok, f"levers {gm.get('lever')}, bench {gm.get('bench')}"
    cb.release(g, led, "S168-R", expect_lines=(BW.LOG_GUESTMENU_RELEASED,) if ctx.get("new") else (), at=at, extra=extra)
    if ctx.get("new"):
        n = cb.count(cb.new(g, at), BW.LOG_GUESTMENU_RELEASED)
        if n != 1:
            led.check("S168-R", False, f"the release line {n} times (want once)")
