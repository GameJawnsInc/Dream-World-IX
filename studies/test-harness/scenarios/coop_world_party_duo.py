"""s154 -- THE DIORAMA SEAT, the TWO-GAME bench (studies/coop-review/REVIEW.md 1.7, appendix findings 9 + 55; memoria-patches s154).

THE DEFECT. The diorama seated the host's party from the STORY mirror (NetSyncParty.MirrorActive / Slots), which arms only at a
FIELD load. A guest paired off-field -- it Continues a world-map save, or walks onto the world map before its partner is up
(S144 decision 9) -- is a live followed session that never mirrors, so the host's world battle booted on it with the guest's
OWN party seated (#9): the wire's player w drove the guest's own w-th character, and the stock menu refused ("the party mirror
is not active"). A guest that DID mirror but stays frozen on the world map seated its LAST FIELD LOAD's party (#55: levels,
equipment, SAs, statuses) in every world battle. s154: THE SEAT LAW -- a diorama seats the host's party from its boot's OWN
host state frame (NetSyncDiorama.SeatRule / NetSyncParty.TryParsePartyInto), never from the story mirror, and a seat never arms
the read wraps. (#34, a warm return ARMING the story mirror at its field load, is a different root and stays open.)

Two real FF9s on this desktop (tools/harness/duo.py, topology "bridge"), each from its own instance root. Two legs, one duo
process each (a duo New-Games both games, so a leg cannot follow another in one file):

LEG `unarmed` (the default; findings #9) -- the guest is BORN ON THE WORLD MAP while the host is already there, its story
mirror never armed (the ENSURE path: WMScriptDirector.HonoAwake creates the client, it dials on WorldHUD):
  W0  the host: New Game, seeded through COOPPARTY (+Vivi +Garnet +Steiner: [0,1,2,3]), its role (d.apply_role: the config line
      and one same-field warp on 6603), connected, then walked out to world 9011. The guest: New Game, UNSEEDED (Zidane alone),
      6603, encounters off; `netsync.instance` false asserted BEFORE its ini is written (its root boots co-op OFF: no client polls
      it), the ini written with NO reload (d.instances['guest'].netsync, its backup recorded in d.ini_backups['guest'] -- never
      d.apply_role, whose same-field warp is a field load, never d.pair), then walked out: the world load is its first read.
  WP-I    the instrument (green on BOTH engines, else nothing below is judged): the guest on WorldHUD 9011, its peer alive, frozen,
          NOT mirroring, `mirror_party` null, no ARMED line since the walk out, its own party [0,-1,-1,-1]; the host on WorldHUD
          9011 with [0,1,2,3]; the two parties differ (THE TWO-MARKER LAW: Vivi, Garnet, Steiner exist nowhere in the guest's).
  WP1-pre the guest booted a world diorama on the host's first world battle (s145's boot; green on both).
  WP1a    the seated party (`netsync.dress.party`, the live party.member inside the diorama) == the host's, on every SEATED sample
          (battle active + debug + a player unit). s153: [0,-1,-1,-1].
  WP1b    4 player units, named AND LEVELLED as the host's own units by name (level: the one per-unit value only the seat writes
          -- the reconciler repairs HP/MP/Death/Trance/ATB, never level). s153: 1 unit, Zidane.
  WP1c    BEHAVIOURAL: the guest's "stock menu: the ready mirror is SERVING" line, and the HOST's decode of the guest's real menu
          (host.wait.menu root/deep: judge_host_menu, coop_world_battle's DP). s153: the digit panel -- no line, no decode.
          (`menu.stock_owns` / `roster_src` are receipts only: they read the very predicate the patch rewrote.)
  WP1d    containment (green on BOTH): `mirror_party` null and `session.mirroring` false on EVERY sample (the seat never armed the
          story mirror); back on WorldHUD 9011, world returns +1, the own party [0,-1,-1,-1] again, still frozen.
  WP2-pre the guest booted a world diorama on the host's SECOND world battle (green on both): judged at battle 2 exactly as
          WP1-pre is, and never predicted -- a battle 2 that never boots (a declined boot, a start-hold timeout, a raise) is
          this unpredicted red, so WP2a / WP2b's 'not reached' can never pass for their predicted seat reds.
  WP2a/b  a SECOND host world battle with no field load between: WP1a / WP1b again -- a REPEAT of the seat on a battle after a
          battle (that boot seats from its own host frame too). Not a test of the per-boot resets (Boot's and ForceDisarm's
          `_seatSrc = SeatOwn`): every wire boot passes a fresh frame and MirrorHostParty rewrites the source on every seating
          boot, so deleting a reset leaves WP2a/b green.
LEG `mirror` (COOP_WP_LEG=mirror; finding #55) -- s145's shape: the duo paired on 6603 (the guest MIRRORING), both walk out, the
host fights world battles until its OWN levels change -- COOP_WP_FIGHTS battles at most, default AND floor MIN_FIGHTS = 5 (scene
67's one Goblin is 23 EXP, 5 each over four members, and level 2 is 16: the 5th fight is the first whose roster carries a
level-up; see WIN_EXP). THE PRE-PAIR FARM: the first PRE_WINS = 3 of those fights the host wins ALONE inside duo.pair's
host_setup, while the guest is still on its title (15 EXP: still level 1, so the guest's 6603 field load parses level 1), so
only ONE shared world return precedes the judged battle instead of four (THE SHARED-FILE RACE, at GUEST_RETURN_S):
  WP55-I     the instrument: the farm banked PRE_WINS wins, paired + ARMED on 6603, both frozen on 9011 (the guest), its party
             mirror landed.
  WP55-1     paired battle 1 (the 4th win, which levels the party at its result): the guest's seated levels by name == the
             host's (green on both: the 6603 parse is still current).
  WP55-GATE  the host's levels changed between battle 1 and a later battle k (read off the HOST's own samples) -- else WP55-2 is
             'not reached' and this row is red (a calibration can never pass on a fight that levelled nobody).
  WP55-2     battle k (by the arithmetic, paired battle 2): the guest's seated levels by name == the host's battle-k levels.
             s153: the 6603 field load's levels.
  Every battle starts only on a guest LIVE on the world map (judge_ready), and a booted battle's return must LAND (judge_return)
  before another is fought: a return that never lands stops the leg there, its rows 'not reached' -- an instrument red naming
  that battle and the guest's own engine-log errors, never a later battle's 'the guest never booted'.
Both legs: WP-SWIRL / WP55-SWIRL (the instrument: no swirl hang) and, under COOP_CALIBRATE=1, WP-CAL / WP55-CAL: by the GUEST's
stage (the s154 probe `netsync.diorama.boot_song`), exactly PREDICTED_S153 (resp. PREDICTED_S153_MIRROR) red before s154, nothing
after. WP-I, WP1-pre, WP2-pre and WP1d must be green on s153: a guest that never boots can never pass calibration as "the seat is
wrong" (the CAL equality compares sets only, so each battle's boot is its own row).

Prereqs as duo.py's (both roots built, no FF9 from either, no controller, nobody at the keyboard); COOPPARTY (30604) registered;
6603 FARSHORE and its walk-out as coop_world_wait's. Calibrate FIRST on the deployed s153 DLL (both roots run the install's DLL),
then deploy s154 and re-run; then re-run coop_world_battle.py's duo and the solo diorama benches as the regression set.

    py tools/harness/duo.py studies/test-harness/scenarios/coop_world_party_duo.py --no-pair
    COOP_WP_LEG=mirror py tools/harness/duo.py studies/test-harness/scenarios/coop_world_party_duo.py --no-pair
    COOP_CALIBRATE=1 py tools/harness/duo.py studies/test-harness/scenarios/coop_world_party_duo.py --no-pair
"""
from __future__ import annotations

import datetime as _dt
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import coop_world_wait as cw                               # noqa: E402 - the s144 route (imported, never copied)
import coop_world_battle as wb                             # noqa: E402 - the s145 duo's tap, fight policy and judges

HarnessError = cb.HarnessError
BW = cw._bw()

PROBE = "netsync.diorama.boot_song"                        # the s154 capability (AppendDioramaReturnSong; the same patch)
FARSHORE, WORLD, ICE_TILE = cw.FARSHORE, cw.WORLD, cw.ICE_TILE
HOST_PARTY = [0, 1, 2, 3]                                  # COOPPARTY: Zidane + Vivi + Garnet + Steiner (CharacterId)
GUEST_PARTY = [0, -1, -1, -1]                              # the New-Game party: Zidane alone
LINK_S = 30.0                                              # the guest's walk out -> its config line and relay leg
BOOT_WAIT_S = 30.0                                         # the host's battle up -> the guest's world diorama up
#: THE SHARED-FILE RACE (the cal153 run .harness-runs/20261026-121811-duo-s154-wpm-cal153). The guest follows the host out of
#: every world battle at the host's result-hide, so BOTH games construct the world map in the same second -- and both instance
#: roots junction FF9CustomMap-world to the one install folder (tools/harness/instance.py), where stock Memoria's
#: FbxIO.ReadFlexible opens a custom FBX READ-WRITE (`new FileStream(path, FileMode.Open)`: share Read only). At the 4th return
#: the guest lost: "Sharing violation" on Models/5/6321/6321.fbx (GEO_SUB_W0_DWX, its Memoria.log 12:22:14), the import gave
#: null, and WMScriptDirector.HonoAwake -> w_frameMapConstructor threw (its output_log): a world map that never constructed
#: (ui BattleResult on scene WorldMap, world ticks 0, never a WorldHUD frame) and so could never boot battle 5 -- whose late
#: join it then CORRECTLY declined. The bench had waited RET_WAIT_S for that return, dropped the None and fought on.
GUEST_RETURN_S = 60.0                                      # the host back on its world map -> the guest's own WorldHUD (~6 s)
READY_S = 20.0                                             # before a host battle: the guest live on the world map
DETAIL_W = 1600
LEGS = ("unarmed", "mirror")


def _leg(raw) -> str | None:
    n = (raw or "unarmed").strip().lower()
    n = {"": "unarmed", "9": "unarmed", "55": "mirror", "mirroring": "mirror"}.get(n, n)
    return n if n in LEGS else None


LEG = _leg(os.environ.get("COOP_WP_LEG", "unarmed"))
#: THE MIRROR GATE's ARITHMETIC (the s154 pre-build review): the leg fights wb.SCENE / wb.GROUP = scene 67 (EF_R007), one Goblin,
#: whichever pattern `rand` picks: WinExp 23. BattleResultUI splits btl_bonus.exp over the members alive and not capped, as an
#: integer (23 // 4 = 5 each); a New-Game party is level 1 at 0 EXP, and Leveling.csv's level 2 is 16. Fight k's host roster
#: (the farm's fights counted) carries the EXP of k - 1 wins, so the first fight whose levels differ from the first's is the one
#: after ceil(16 / 5) = 4 wins: fight 5. A KO only raises the survivors' share (23 // 3 = 7): it can only bring the change
#: earlier (inside the farm: before the guest's field load, which then parses it -- WP55-GATE says so, never a pass). Four
#: fights could NEVER reach WP55-GATE with the whole party standing.
WIN_EXP, LV2_EXP = 23, 16                                   # scene 67's WinExp (EF_R007, both patterns); Leveling.csv's level 2
MIN_FIGHTS = -(-LV2_EXP // (WIN_EXP // len(HOST_PARTY))) + 1   # = 5: fight k's roster carries k - 1 wins
#: THE PRE-PAIR FARM: the most wins whose EXP still reads level 1 (15 // 5 = 3; 3 x 5 = 15 < 16), banked by the host ALONE before
#: the guest's New Game. Paired battle 1 is then the 4th win (its result levels the party) and paired battle 2 the first roster
#: with the level-up: PRE_WINS + 2 == MIN_FIGHTS (an identity: ceil(a / b) == (a - 1) // b + 1), the total unchanged.
PRE_WINS = (LV2_EXP - 1) // (WIN_EXP // len(HOST_PARTY))   # = 3
WIN_RESULTS = (1, 2)                                        # channel.State.BATTLE_RESULTS: victory, victory-no-pose
try:                                                        # COOP_WP_FIGHTS can raise the cap, never take it below MIN_FIGHTS
    MIRROR_FIGHTS = max(MIN_FIGHTS, int(os.environ.get("COOP_WP_FIGHTS", "") or MIN_FIGHTS))
except ValueError:
    MIRROR_FIGHTS = MIN_FIGHTS
#: the farm's own record (_farm writes it inside duo.pair's host_setup; WP55-I judges it): reset by every mirror leg
FARM = {"wins": 0, "fights": 0, "results": [], "why": "the farm never ran"}

CHECKS_UNARMED = {
    "WP-I": "the instrument: the guest born on WorldHUD 9011 -- peer alive, frozen, NOT mirroring, mirror_party null, no ARMED line, "
            "its own party [0,-1,-1,-1]; the host on 9011 with [0,1,2,3]; the parties differ",
    "WP1-pre": "the guest boots a world diorama on the host's world battle",
    "WP1a": "the seated party == the host's [0,1,2,3] on every seated sample",
    "WP1b": "4 player units, named and levelled as the host's own by name",
    "WP1c": "the guest's stock menu SERVES (its line) and the host decodes the guest's menu (root / deep)",
    "WP1d": "containment: mirror_party null + not mirroring throughout; back on 9011, world returns +1, own party again, frozen",
    "WP2-pre": "the guest boots a world diorama on the host's SECOND world battle (a battle 2 that never seats is this red, "
               "never WP2a / WP2b's predicted one)",
    "WP2a": "a second world battle (no field load between): the seated party == the host's again",
    "WP2b": "...4 player units named and levelled as the host's again",
    "WP-SWIRL": "the instrument: neither game's battle start hung in the swirl",
    "WP-CAL": "CALIBRATION: exactly the predicted rows red for the GUEST's stage",
}
#: the calibration ledger (unarmed): exactly these red on an s153 guest -- wrong outcomes the harness reads, never a missing line;
#: each battle's own boot instrument (WP1-pre, WP2-pre) stays OUT, so a battle that never seats is an unpredicted red
PREDICTED_S153 = ("WP1a", "WP1b", "WP1c", "WP2a", "WP2b")
#: the boot instrument of battle n (judged at that n, never predicted)
PRE_IDS = {1: "WP1-pre", 2: "WP2-pre"}
CHECKS_MIRROR = {
    "WP55-I": "the instrument: the host's pre-pair farm banked its wins, paired + ARMED on 6603, both walked out, the guest "
              "frozen on 9011",
    "WP55-1": "battle 1: the guest's seated levels by name == the host's",
    "WP55-GATE": "the host's own levels changed between battle 1 and a later battle (else WP55-2 is not reached)",
    "WP55-2": "that battle: the guest's seated levels by name == the host's (s153: the 6603 field load's)",
    "WP55-SWIRL": "the instrument: neither game's battle start hung in the swirl",
    "WP55-CAL": "CALIBRATION: exactly the predicted rows red for the GUEST's stage",
}
PREDICTED_S153_MIRROR = ("WP55-2",)


# ================================================================================================ pure readers / judges
def party(x):
    """`netsync.dress.party` (the live FF9.party.member[i] CharacterIds; -1 empty, -2 unreadable) as a list, or None."""
    v = cb.path(x, "netsync.dress.party")
    return list(v) if isinstance(v, list) else None


def world_id(x):
    w = cb.raw(x).get("world")
    return w.get("id") if isinstance(w, dict) else None


def seated(s) -> bool:
    """(PURE) a diorama sample past InitBattleScene: the battle active, a debug battle, at least one player unit."""
    b = cb.battle(s)
    return bool(b.get("active")) and bool(b.get("debug")) and bool(cb.units(s, player=True))


def players(s) -> dict:
    """(PURE) the player units by name -> level (the HUD name: tags stripped)."""
    return {u.get("name"): u.get("level") for u in cb.units(s, player=True)}


def roster_sample(samples):
    """(PURE) the sample carrying the most player units (the settled roster: InitPlayerData lands N frames after the boot) --
    the LAST such one; None when no sample has a player unit."""
    best, n = None, 0
    for s in samples:
        k = len(cb.units(s, player=True))
        if k and k >= n:
            best, n = s, k
    return best


def host_players(hsamples) -> dict:
    """(PURE) the HOST's own battle roster (by name -> level) off its in-battle samples (not a debug battle)."""
    real = [s for s in hsamples if cb.battle(s).get("active") and not cb.battle(s).get("debug")]
    s = roster_sample(real)
    return players(s) if s is not None else {}


def judge_instrument(gst, hst, armed_lines: int, *, mirroring_expected: bool = False) -> tuple:
    """(PURE) WP-I: the guest on WorldHUD 9011, peer alive, frozen, mirroring as expected (the unarmed leg: NOT), no ARMED line,
    its own party; the host on WorldHUD 9011 with its seeded party; the two parties differ (the two-marker law)."""
    g_party, h_party = party(gst), party(hst)
    terms = {
        "guest WorldHUD 9011": gst is not None and gst.ui_state == "WorldHUD" and world_id(gst) == WORLD,
        "peer alive": cb.path(gst, "netsync.session.peer_alive") is True,
        "frozen": cb.path(gst, "netsync.world.freeze.on") is True,
        "mirroring": cb.path(gst, "netsync.session.mirroring") is mirroring_expected,
        "mirror_party": (cb.path(gst, "netsync.dress.mirror_party") is None) != mirroring_expected,
        "no ARMED line": armed_lines == 0 if not mirroring_expected else True,
        "guest party": g_party == GUEST_PARTY,
        "host WorldHUD 9011": hst is not None and hst.ui_state == "WorldHUD" and world_id(hst) == WORLD,
        "host party": h_party == HOST_PARTY,
        "two markers": bool(set(h_party or []) - set(g_party or []) - {-1, -2}),
    }
    bad = [k for k, ok in terms.items() if not ok]
    return not bad, (f"guest ui {getattr(gst, 'ui_state', None)!r} world {world_id(gst)!r} peer_alive "
                     f"{cb.path(gst, 'netsync.session.peer_alive')!r} freeze {cb.path(gst, 'netsync.world.freeze.on')!r} mirroring "
                     f"{cb.path(gst, 'netsync.session.mirroring')!r} mirror_party {cb.path(gst, 'netsync.dress.mirror_party')!r} "
                     f"ARMED lines {armed_lines} party {g_party}; host ui {getattr(hst, 'ui_state', None)!r} world {world_id(hst)!r} "
                     f"party {h_party}" + (f"; FAILED {bad}" if bad else ""))


def judge_seat_party(gsamples, want) -> tuple:
    """(PURE) WP1a / WP2a: every SEATED sample's party == ``want`` (the host's); at least one seated sample."""
    seats = [s for s in gsamples if seated(s)]
    seen = sorted({tuple(party(s) or ()) for s in seats})
    ok = bool(seats) and all(party(s) == list(want) for s in seats)
    return ok, f"{len(seats)} seated sample(s); seated parties {[list(p) for p in seen]} (want only {list(want)})"


def judge_seat_units(gsamples, host_roster: dict) -> tuple:
    """(PURE) WP1b / WP2b / WP55: the guest's settled seated roster has the host's player count, names, and each name's level."""
    if not host_roster:
        return False, "the host's own battle roster was never read (no host in-battle sample with player units)"
    s = roster_sample([x for x in gsamples if seated(x)])
    if s is None:
        return False, f"no seated guest sample with a player unit (host roster {host_roster})"
    mine = players(s)
    lv_bad = {n: (mine.get(n), lv) for n, lv in host_roster.items() if mine.get(n) != lv}
    ok = len(mine) == len(host_roster) and set(mine) == set(host_roster) and not lv_bad
    return ok, (f"guest seated {len(mine)} unit(s) {mine}; host {len(host_roster)} {host_roster}"
                + (f"; level / name mismatches {lv_bad}" if lv_bad else ""))


def judge_levels(gsamples, host_roster: dict) -> tuple:
    """(PURE) WP55-1 / WP55-2: by name, the guest's seated level == the host's (names present on both); the host's names all
    seated."""
    if not host_roster:
        return False, "the host's own battle roster was never read"
    s = roster_sample([x for x in gsamples if seated(x)])
    if s is None:
        return False, f"no seated guest sample (host roster {host_roster})"
    mine = players(s)
    bad = {n: (mine.get(n), lv) for n, lv in host_roster.items() if mine.get(n) != lv}
    return not bad, f"guest seated {mine}; host {host_roster}" + (f"; mismatches (guest, host) {bad}" if bad else "")


def levels_changed(first: dict, now: dict) -> bool:
    """(PURE) WP55-GATE: some name both rosters share reads a different level."""
    return any(n in now and now[n] != lv for n, lv in first.items()) if first and now else False


def judge_menu(glines, hsamples) -> tuple:
    """(PURE) WP1c: the guest's SERVING line (coop_world_battle's DP count) and the host's decode of the guest's control byte
    root / deep (wb.judge_host_menu). The guest's stock_owns / roster_src ride along as receipts (never the verdict)."""
    serving = cb.count(glines, "stock menu: the ready mirror is SERVING")
    hm_ok, hm_why = wb.judge_host_menu(hsamples)
    return serving >= 1 and hm_ok, f"the guest's SERVING line {serving}x; {hm_why}"


def menu_receipts(gsamples) -> str:
    owns = sorted({cb.path(s, "netsync.battle.menu.stock_owns") for s in gsamples}, key=str)
    src = sorted({cb.path(s, "netsync.battle.menu.roster_src") for s in gsamples}, key=str)
    why = sorted({cb.path(s, "netsync.battle.menu.why") for s in gsamples if cb.path(s, "netsync.battle.menu.why")}, key=str)
    return f"receipts: stock_owns {owns}, roster_src {src}, why {why[:2]}"


def judge_containment(gsamples, after, returns0) -> tuple:
    """(PURE) WP1d: `mirror_party` null and `session.mirroring` false on EVERY guest sample (the seat never armed the story
    mirror); after the return: WorldHUD 9011, world returns +1, the guest's own party again, still frozen."""
    armed = [s for s in gsamples if cb.path(s, "netsync.dress.mirror_party") is not None]
    mirroring = [s for s in gsamples if cb.path(s, "netsync.session.mirroring") is not False]
    r1 = cb.path(after, "netsync.world.dio.returns")
    counted = isinstance(r1, int) and isinstance(returns0, int) and r1 == returns0 + 1
    back = after is not None and after.ui_state == "WorldHUD" and world_id(after) == WORLD
    own = party(after) == GUEST_PARTY
    frozen = cb.path(after, "netsync.world.freeze.on") is True
    ok = bool(gsamples) and not armed and not mirroring and counted and back and own and frozen
    return ok, (f"{len(gsamples)} sample(s): mirror_party set on {len(armed)}, mirroring on {len(mirroring)}; after: ui "
                f"{getattr(after, 'ui_state', None)!r} world {world_id(after)!r}, world returns {returns0}->{r1} (want +1), party "
                f"{party(after)} (want {GUEST_PARTY}), frozen {cb.path(after, 'netsync.world.freeze.on')!r}")


def calibration(stage_s154: bool, leg: str) -> tuple:
    """(PURE) the predicted red set for the GUEST's stage: s153 -> the leg's PREDICTED_S153*, s154 -> none."""
    if stage_s154:
        return ()
    return PREDICTED_S153 if leg == "unarmed" else PREDICTED_S153_MIRROR


def engine_errors(lines, limit: int = 3) -> list:
    """(PURE) the engine log's ERROR lines (`|E|`), each trimmed to its message, the first ``limit`` -- a failed return's
    evidence (the cal153 run: "When importing FBX '.../6321.fbx':" then "System.IO.IOException: Sharing violation ...")."""
    out = [ln.split("|E|", 1)[-1].strip() for ln in (lines or ()) if "|E|" in ln]
    return [x[:220] for x in out[:limit]]


def ready_detail(st) -> str:
    return (f"guest ui {getattr(st, 'ui_state', None)!r} scene {cb.raw(st).get('scene')!r} world "
            f"{world_id(st)!r} ticks {cb.path(st, 'world.ticks')!r} diorama booted {cb.path(st, 'netsync.diorama.booted')!r} "
            f"returns {cb.path(st, 'netsync.world.dio.returns')!r} frozen {cb.path(st, 'netsync.world.freeze.on')!r}")


def judge_ready(st) -> tuple:
    """(PURE) the guest LIVE on the world map before a host battle: WorldHUD with no diorama up and a world position
    (wb.on_world_free), on world 9011. The cal153 run's dead world -- ui BattleResult on scene WorldMap, world ticks 0, the
    constructor thrown -- is red here (it can boot nothing). The freeze rides along in the detail only: WP55-I / WP-I own it,
    and it re-arms seconds after a healthy return's first WorldHUD frame."""
    ok = st is not None and wb.on_world_free(st) and world_id(st) == WORLD
    return ok, ready_detail(st)


def judge_return(out) -> tuple:
    """(PURE) a booted battle's return LANDED: host_world_battle's ``returned`` (the first world-free guest sample after the
    boot). None -- or no such key -- is a guest that never came back to a live world map: every later battle would be fought
    against a guest that cannot boot, so the caller stops there ('not reached': an instrument red at THIS battle, never the
    next one's 'the guest never booted'), naming the guest's last sample and its own engine-log errors."""
    r = out.get("returned")
    if r is not None:
        return True, f"the guest back on WorldHUD (frame {cb.raw(r).get('frame')})"
    tail = (out.get("gsamples") or [None])[-1]
    errs = engine_errors(out.get("glines"))
    return False, (f"the guest's return never landed (no world-free sample within {GUEST_RETURN_S:.0f} s of the host's own "
                   f"return; its last tapped sample: {ready_detail(tail) if tail is not None else 'none'})"
                   + (f"; its engine log: {' | '.join(errs)}" if errs else "; no error line in its engine log")
                   + (f"; the host's fight / return raised: {out['host_err']}" if out.get("host_err") else ""))


def judge_farm(farm) -> tuple:
    """(PURE) WP55-I's farm term: the pre-pair farm banked exactly PRE_WINS victories (so the guest's 6603 field load still
    parses level 1 and paired battle 2 is the first levelled roster) and named no failure."""
    wins, why = farm.get("wins"), farm.get("why")
    ok = wins == PRE_WINS and not why
    return ok, (f"pre-pair farm: {wins} of {PRE_WINS} win(s) banked over {farm.get('fights')} fight(s), results "
                f"{farm.get('results')}" + (f"; {why}" if why else ""))


# ================================================================================================ the moves
def host_world_battle(d, where: str) -> dict:
    """The host's world battle (s145's DB-DR moves): the guest tapped from the verb on, the host's fight Defending until it decodes
    the guest's menu (wb.dp_command, its DP_WAIT_S cap), then the host's world return and the guest's. -> {booted, returned,
    gsamples, hsamples, glines, why, host_err}; ``returned`` is the guest's first world-free sample after its boot (None: it
    never came back to a live world map -- judge_return); raises wb.SwirlHang (the instrument)."""
    host, guest = d.host, d.guest
    gat = cb.mark(guest)
    wb._state_every(guest, 1)
    wb._state_every(host, 1)
    tap = wb.GuestTap(guest)
    tap.start()
    out = {"booted": None, "returned": None, "gsamples": [], "hsamples": [], "glines": [], "why": None, "host_err": None}
    try:
        host.world_battle(wb.SCENE, group=wb.GROUP, rand=True, timeout=wb.BATTLE_S)
    except HarnessError as err:
        out["gsamples"] = tap.stop()
        wb.hang_check(host, f"the host's world battle ({where})")
        out["why"] = f"the host's world battle never came up ({str(err)[:200]})"
        return out
    wb._state_every(host, 2)
    hsamples, _hit = cb.watch(host, lambda s: cb.path(s, "netsync.battle.host.start_hold.guest.boot_name") == "live",
                              wb.HOLD_WAIT_S)
    booted = tap.wait_for(wb.booted_world, BOOT_WAIT_S if not hsamples else 5.0)
    hrec = list(hsamples)
    t_fight = time.time()

    def policy(_s, _slot):
        try:
            hrec.append(host.state)
        except HarnessError:
            pass
        seen = any(cw._num(cb.path(x, "netsync.battle.host.wait.menu")) in (BW.CTL_ROOT, BW.CTL_DEEP) for x in hrec)
        return {"command": wb.dp_command(seen, time.time() - t_fight)}
    host_err = None
    try:
        host.fight(policy=policy, timeout=wb.FIGHT_S, finish=True, max_turns=1_000_000)
        host.wait_world(timeout=wb.RETURN_S)
    except HarnessError as err:
        host_err = str(err)[:200]
        d.note(f"{where}: the host's fight / return raised: {host_err}")
    returned = None
    if booted is not None:
        # KEPT, never dropped (the cal153 run waited RET_WAIT_S here for a world that never constructed, then fought battle 5
        # against it): the host is already back, so a healthy guest lands within seconds -- GUEST_RETURN_S bounds the dead one
        returned = tap.wait_return(GUEST_RETURN_S)
        cb.hold_for(host, 0.5)
    out.update(booted=booted, returned=returned, host_err=host_err, gsamples=tap.stop(), hsamples=hrec,
               glines=cb.new(guest, gat))
    if booted is None:
        wb.hang_check(guest, f"the guest's boot ({where})")   # the tap is stopped first: a SwirlHang leaves no thread behind
    wb._state_every(guest, 2)
    return out


def _guest_link(d, at, timeout: float = LINK_S) -> tuple:
    """The guest's own config line (enabled, Role=client, this duo's relay + code) and its relay leg as role=guest, both logged
    after ``at``. (ok, detail)."""
    url = d.role_values("guest")["RelayUrl"]

    def want(m):
        return m.group(1) == "True" and m.group(2) == "client" and m.group(5) == url and m.group(6) == d.code
    cfg = d.wait_line("guest", "config", timeout, pred=want, after=at)
    up = d.wait_line("guest", "relay_up", timeout, pred=lambda m: m.group(3) == "guest" and m.group(2) == d.code, after=at)
    return bool(cfg) and bool(up), f"the guest's config line {'seen' if cfg else 'MISSING'}, relay role=guest {'up' if up else 'MISSING'}"


def _guest_ready(guest, timeout: float | None = None) -> tuple:
    """Before a host battle: the guest LIVE on the world map (judge_ready), its world_settle first and then its publishes
    polled up to ``timeout`` (READY_S). world_settle alone cannot tell: it returns at once off a non-WorldHUD sample -- the
    cal153 run's dead world sailed through it into battle 5. (ok, why, state)."""
    st = guest.world_settle()
    ok, why = judge_ready(st)
    deadline = time.time() + (READY_S if timeout is None else timeout)
    while not ok and time.time() < deadline:
        time.sleep(0.25)
        st = guest.state
        ok, why = judge_ready(st)
    return ok, why, st


def run_duo(d) -> None:
    """One leg per duo process (COOP_WP_LEG): every row recorded (strict off), judged on the GUEST's samples beside the HOST's;
    COOP_CALIBRATE=1 judges the CAL row by the GUEST's stage."""
    checks = CHECKS_UNARMED if LEG == "unarmed" else CHECKS_MIRROR
    cal_id = "WP-CAL" if LEG == "unarmed" else "WP55-CAL"
    swirl_id = "WP-SWIRL" if LEG == "unarmed" else "WP55-SWIRL"
    strict, d.strict = d.strict, False
    failed, done, hung = [], set(), [None]

    def check(cid, ok, detail):
        if cid in done:
            return
        done.add(cid)
        if not ok:
            failed.append(cid)
        d.check(bool(ok), f"{cid}: {checks.get(cid, cid)}", str(detail)[:DETAIL_W], cid=cid)

    def rest(why):
        for cid in checks:
            if cid not in (cal_id, swirl_id) and cid not in done:
                check(cid, False, f"not reached: {why}"[:DETAIL_W])

    try:
        if LEG is None:
            rest(f"COOP_WP_LEG={os.environ.get('COOP_WP_LEG')!r} is not one of {LEGS}")
        elif d.paired:
            rest("the duo was paired before the scenario (run it with --no-pair: the unarmed leg's guest must be born on the world "
                 "map, and the mirror leg pairs itself)")
        elif LEG == "unarmed":
            _unarmed(d, check, rest)
        else:
            _mirror(d, check, rest)
    except wb.SwirlHang as err:
        hung[0] = str(err)
        d.note(str(err)[:600])
        rest(f"SWIRL-HANG -- the instrument: {str(err)[:200]}")
    except HarnessError as err:
        d.note(f"the duo raised: {str(err)[:400]}")
        rest(f"the duo raised ({str(err)[:200]})")
    finally:
        check(swirl_id, hung[0] is None, hung[0] or "neither game's battle start hung in the swirl")
        if cb.CALIBRATE:
            try:
                s154 = cb.has(d.guest.state, PROBE)
            except HarnessError:
                s154 = False
            pred = set(calibration(s154, LEG))
            missing, extra = sorted(pred - set(failed)), sorted(set(failed) - pred)
            d.check(not missing and not extra and hung[0] is None, f"{cal_id}: {checks[cal_id]}",
                    f"guest {'s154' if s154 else 'pre-s154'}: predicted reds that stayed GREEN {missing or 'none'}; unpredicted "
                    f"reds {extra or 'none'}" + ("; SWIRL-HANG: the instrument" if hung[0] else ""), cid=cal_id)
        d.strict = strict


def _unarmed(d, check, rest) -> None:
    host, guest = d.host, d.guest
    # W0 host: seeded, its role, connected, walked out
    host.newgame()
    host.note(cb.seed_party(host, back_to=FARSHORE))
    if host.state.field_id != FARSHORE:
        host.warp(FARSHORE)
    host.no_encounters(True)
    d.apply_role("host", cid="WP0-host")
    up = d.wait_line("host", "relay_up", 30.0, pred=lambda m: m.group(3) == "host" and m.group(2) == d.code)
    if not up:
        rest("the host never connected to the relay as role=host")
        return
    ok, why, _hs = cw.walk_out(host)
    if not ok:
        rest(f"the host's walk out failed ({why[:160]})")
        return
    # W0 guest: unseeded, 6603, co-op OFF until its ini is written with no reload, then the walk out (the ENSURE path)
    guest.newgame()
    if guest.state.field_id != FARSHORE:
        guest.warp(FARSHORE)
    guest.no_encounters(True)
    pre = guest.state
    off = cb.path(pre, "netsync.instance") is False
    if not off:
        rest(f"the guest already has a NetSyncClient before its ini is written (netsync.instance "
             f"{cb.path(pre, 'netsync.instance')!r}): its root must boot co-op off")
        return
    bak = d.instances["guest"].netsync(d.role_values("guest"), backup_to=d.run_dir / "ini")
    d.ini_backups["guest"] = str(bak) if bak else None
    at = _dt.datetime.now() - _dt.timedelta(seconds=1)
    ok, why, _gs = cw.walk_out(guest)
    if not ok:
        rest(f"the guest's walk out failed ({why[:160]})")
        return
    l_ok, l_why = _guest_link(d, at)
    gst = cb.poll(guest, lambda s: cb.path(s, "netsync.session.peer_alive") is True
                  and cb.path(s, "netsync.world.freeze.on") is True, 20.0, "the guest alive and frozen") or guest.state
    armed = len(d.wait_line("guest", "armed", 0.1, after=at))
    i_ok, i_why = judge_instrument(gst, host.state, armed)
    check("WP-I", l_ok and i_ok, f"{l_why}; {i_why}")
    if not (l_ok and i_ok):
        rest("the instrument (WP-I) is red: an armed or unborn guest proves nothing about the seat")
        return
    cw.teleport_settle(guest, ICE_TILE)                        # s145's proven boot spot
    guest.wait_frames(10)
    _seat_battles(d, check, rest)


def _seat_battles(d, check, rest) -> None:
    """The unarmed leg's two host world battles, guest frozen on 9011 (run_duo's own check / rest; the tests drive it with
    host_world_battle stubbed). Battle n's boot is judged as its OWN row (PRE_IDS[n]) before anything it seats: a battle that never
    boots is an unpredicted red, so its 'not reached' rows can never pass for the predicted seat reds. Battle n starts only on a
    guest live on the world map (judge_ready), and battle 1's return must land (judge_return) before battle 2 is fought."""
    guest = d.guest
    for n, (a_id, b_id) in enumerate((("WP1a", "WP1b"), ("WP2a", "WP2b")), start=1):
        r_ok, r_why, before = _guest_ready(guest)
        if not r_ok:
            rest(f"battle {n} not started: the guest is not live on the world map ({r_why})")
            return
        r0 = cb.path(before, "netsync.world.dio.returns")
        out = host_world_battle(d, f"battle {n}")
        check(PRE_IDS[n], out["booted"] is not None, out["why"] or (
            "booted_world on a guest sample" if out["booted"] is not None else "no world diorama on the guest"))
        if out["booted"] is None:
            rest(f"battle {n}: {out['why'] or 'the guest never booted its world diorama'}")
            return
        hroster = host_players(out["hsamples"])
        check(a_id, *judge_seat_party(out["gsamples"], HOST_PARTY))
        check(b_id, *judge_seat_units(out["gsamples"], hroster))
        if n == 1:
            m_ok, m_why = judge_menu(out["glines"], out["hsamples"])
            check("WP1c", m_ok, f"{m_why}; {menu_receipts(out['gsamples'])}")
            after = guest.state
            check("WP1d", *judge_containment(out["gsamples"], after, r0))
            ret_ok, ret_why = judge_return(out)
            if not ret_ok:
                rest(f"battle 1: {ret_why} -- an INSTRUMENT stop: battle 2 would be fought against a guest that cannot boot")
                return


def _farm(g) -> str:
    """THE PRE-PAIR FARM (inside duo.pair's host_setup: the host New-Gamed and seeded, its role NOT yet written, the guest
    still on its title -- no second game loads anything, so no shared-file race): encounters off, the 6603 walk out, PRE_WINS
    world battles at scene 67 fought the stock way (fight()'s Attack policy: no guest exists to wait for), each back on the
    world map, then into 6603 from the world map (coop_world_wait._reach_world_again's way) for the pairing. Records into
    FARM; WP55-I judges it (judge_farm). Returns the one-line account for the notes."""
    FARM.update(wins=0, fights=0, results=[], why=None)
    try:
        g.no_encounters(True)
    except HarnessError as err:
        g.note(f"farm: noencounter refused on {FARSHORE} ({str(err)[:120]})")
    ok, why, _st = cw.walk_out(g)
    if not ok:
        FARM["why"] = f"the farm's walk out failed ({why[:160]})"
    else:
        for n in range(1, PRE_WINS + 1):
            try:
                g.world_settle()
                g.world_battle(wb.SCENE, group=wb.GROUP, rand=True, timeout=wb.BATTLE_S)
                res = g.fight(timeout=wb.FIGHT_S, finish=True)
                g.wait_world(timeout=wb.RETURN_S)
            except HarnessError as err:
                FARM["why"] = f"farm fight {n} raised: {str(err)[:200]}"
                break
            FARM["fights"] = n
            FARM["results"].append(res)
            if res not in WIN_RESULTS:
                FARM["why"] = f"farm fight {n} ended with result {res!r}, not a victory"
                break
            FARM["wins"] += 1
    try:
        if g.state.ui_state == "WorldHUD":
            g.world_warp(FARSHORE)
            g.wait_frames(45)
    except HarnessError as err:
        FARM["why"] = FARM["why"] or f"the way back into {FARSHORE} failed: {str(err)[:200]}"
    return judge_farm(FARM)[1]


def _seed_host(g) -> str:
    """The mirror leg's host_setup: COOPPARTY's seed, then THE PRE-PAIR FARM."""
    return f"{cb.seed_party(g, back_to=FARSHORE)}; {_farm(g)}"


def _mirror(d, check, rest) -> None:
    host, guest = d.host, d.guest
    FARM.update(wins=0, fights=0, results=[], why="the farm never ran (duo.pair never called host_setup)")
    # s145's shape: both New Game onto 6603, the guest ARMED there -- the host's setup banks PRE_WINS wins first (_farm)
    d.pair(field=FARSHORE, host_setup=_seed_host)
    ok, why, _hs = cw.walk_out(host)
    if not ok:
        rest(f"the host's walk out failed ({why[:160]})")
        return
    ok, why, _gs = cw.walk_out(guest)
    if not ok:
        rest(f"the guest's walk out failed ({why[:160]})")
        return
    gst = cb.poll(guest, lambda s: cb.path(s, "netsync.world.freeze.on") is True, 20.0, "the guest frozen on 9011") or guest.state
    i_ok, i_why = judge_instrument(gst, host.state, 0, mirroring_expected=True)
    f_ok, f_why = judge_farm(FARM)
    check("WP55-I", d.paired and i_ok and f_ok, f"{f_why}; paired {d.paired}; {i_why}")
    if not (d.paired and i_ok and f_ok):
        rest("the instrument (WP55-I) is red")
        return
    cw.teleport_settle(guest, ICE_TILE)
    guest.wait_frames(10)
    _mirror_battles(d, check, rest)


def _mirror_battles(d, check, rest) -> None:
    """The mirror leg's PAIRED host world battles, guest frozen on 9011 (run_duo's own check / rest; the tests drive it with
    host_world_battle stubbed over the EXP arithmetic): battle 1 judged, then battles 2..(MIRROR_FIGHTS - PRE_WINS) until the
    host's own levels change (WP55-GATE), that battle judged as WP55-2. Each battle starts only on a guest live on the world map
    (judge_ready), and each unjudged battle's return must land (judge_return) before the next: THE SHARED-FILE RACE's dead world
    stops the leg at the battle whose return died, 'not reached', never a later battle's 'the guest never booted'."""
    guest = d.guest
    first = None
    paired = MIRROR_FIGHTS - PRE_WINS
    for k in range(1, paired + 1):
        r_ok, r_why, _st = _guest_ready(guest)
        if not r_ok:
            rest(f"battle {k} not started: the guest is not live on the world map ({r_why})")
            return
        out = host_world_battle(d, f"battle {k}")
        if out["booted"] is None:
            rest(f"battle {k}: {out['why'] or 'the guest never booted its world diorama'}")
            return
        hroster = host_players(out["hsamples"])
        ret_ok, ret_why = judge_return(out)
        if k == 1:
            first = hroster
            check("WP55-1", *judge_levels(out["gsamples"], hroster))
        elif levels_changed(first, hroster):
            check("WP55-GATE", True, f"battle {k}: host levels {hroster} (battle 1: {first})")
            check("WP55-2", *judge_levels(out["gsamples"], hroster))
            if not ret_ok:
                d.note(f"battle {k} (judged; its own return judges nothing): {ret_why}"[:DETAIL_W])
            return
        else:
            d.note(f"battle {k}: the host's levels did not change ({hroster}) -- another fight")
        if not ret_ok:
            rest(f"battle {k}: {ret_why} -- an INSTRUMENT stop: no later battle can boot on a world map that never came back")
            return
    check("WP55-GATE", False, f"the host's levels never changed over {paired} paired battle(s) after the farm's {PRE_WINS} "
                              f"win(s) (battle 1: {first}) -- by the arithmetic (WIN_EXP {WIN_EXP} // {len(HOST_PARTY)} a "
                              f"win, level 2 at {LV2_EXP}) paired battle 2 (fight {MIN_FIGHTS}) was due to carry one: a lost "
                              f"or fled fight, a KO in the farm, or a scene other than 67's Goblin (fought: scene {wb.SCENE} "
                              f"group {wb.GROUP})")
    rest(f"not reached: no host level changed in {paired} paired battle(s) -- the stale-mirror witness needs a level the "
         "field load did not see")
