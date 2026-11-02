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

PRECONDITIONS -- THE OPERATOR'S JOB: the DLL under test deployed (the bench deploys nothing); controllers OFF, nobody at the keyboard
(THE UNATTENDED LAW), FF9 unfocused; 6603 registered; [Netsync] Enabled 0 and FollowHost 1 written BEFORE launch (solo_ini.py);
close the game after a lab.

    py <scratchpad>/solo_ini.py s166-a0 -- py tools/play.py studies/test-harness/scenarios/coop_world_walk.py --field 6603
    COOP_CALIBRATE=1 COOP_WW_LEG=kitoff   (the same command: one destructive leg per launch; on s165 = OLD, on s166 +
                                           COOP_WW_LEVER=kitcell = LEVER)
    COOP_WW_KIT_AT="x,z" / COOP_WW_FERRY_AT="x,z" move a stand (its instrument still judges it: off the trigger is "not reached")
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import coop_world_wait as cw                               # noqa: E402 - the s144 route and judges (imported, never copied)
import coop_world_follow as wf                             # noqa: E402 - the s165 route, bench host and judges (imported, never copied)

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
