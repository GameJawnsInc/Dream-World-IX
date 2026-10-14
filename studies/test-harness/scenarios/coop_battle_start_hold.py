"""R3 s114 -- THE START HOLD (memoria-patch s114), the solo bench, run unattended.

THE GAP (studies/battle-coop/R3-DESIGN.md 1.1 report 1, 3.1.4). Sitting 2: the host's gauges ran from its first
command-phase frame while the laptop was still swirling into its diorama, so the guest arrived seconds into a fight
already moving. s114, both halves:
  GUEST  the type-3 control frame grows a trailer `[0][menu][fmt 1][host battle nonce][boot]` -- boot 0 NONE, 1 BOOTING,
         2 LIVE, 3 DECLINED, 4 BUSY: how far its diorama of THAT battle has got (LIVE is a per-boot latch: the boot's
         first steady frame with a host sample in hand);
  HOST   while the report reads BOOTING every gauge waits -- one gate in IsNativeEnableAtb after _commandEnable, so every
         ATB mode and every Speed -- decided ONCE at the command phase's opening (a BOOTING report within 1000 ms arms it
         late), never primed on silence, and every release FINAL: LIVE, NONE/DECLINED/BUSY ("declined"), the transport's
         null frame ("link"), a trailer-less frame ("old guest"), the cap ([Netsync] StartHoldMs, default 8000, clamped
         to 60000 at parse), the battle's end or the knob going off. Type-1 header flags bit 4 (0x10) while it holds.
Lever: `netsync bench starthold 1|0|cap <ms>|cap ini`. What the loopback / bench-feed guest reports: `netsync bench boot
auto|none|booting|live|declined|busy|stale|silent|late <ms>`. Both are set BEFORE `battle` (the hold primes in the intro).

THE BENCH. Host legs: REAL selftest own battles (`battle 67`, one Goblin) on field 30602 with `netsync guestslots 0`
(every party slot is the host's own; the loopback guest still reports every tick -- a GuestSlots=0 spectator holds too),
`stateevery 1`, the bench cap set explicitly before every battle (8000; 3000 for the cap legs A5/A6 -- the install's
StartHoldMs may be anything) and Active mode (`bench cfg atb active`; A3 runs Wait). ONE BATTLE PER LEG: the hold decides
once per battle. Guest legs: `dioboot 67 0 play` on 30602 plus the stage-8 bench feed (`bbench start 0x01`), whose diorama
reports as a wire boot of the feed's own battle nonce.

CAUTION: THE PROBE COMES FIRST. An engine before s114 parses `bench boot` / `bench starthold` as `bench 1` (the stock `Arg`
fallback) and turns the FIELD-GATE bench ON; an engine before s111 does the same with `bench cfg`, and one before s113
refuses `bench cfg atb` and a 4-argument lapse. :func:`_bench` refuses AT THE CALL SITE to send `boot`/`starthold` without
`netsync.battle.host.start_hold`, and `cfg` / `lapse ... reserve` without `netsync.battle.host.wait` -- whatever the
driver's NETSYNC_BENCH_OPS knows.

WHAT IS PROVEN (S14-*; the plan's 6.4 ids in brackets):
  A0  [H-A4's "green on both"] the CONTROL, both DLLs: an own battle with NO lever (auto: the selftest loopback has no
      diorama, so it reports NONE) -- some unit's atb moves within 0.5 s of the first turn.enabled publish, no ARMED
      line, header bit 4 never set. This is every other bench's default: s114 must not hold them.
  A1  [H-A1] `bench boot booting` + `battle 67`: from the first turn.enabled publish EVERY unit's atb is constant for
      >= 2.5 s; state "holding", why "booting", count +1; host.caps & 0x10; one ARMED line naming this battle's nonce and
      the cap.
  A2  [H-A2] then `bench boot live`: release "live" within 2 frames of the first loopback frame that carries LIVE
      (menu.ctl.boot 2 -- the lever on the wire); some atb moves within 0.5 s; released.live +1; bit 4 clear within 2
      frames; one RELEASED line whose N equals held_ms (>= 2500).
  A9  [H-A9] after that release: pause (an enemy gauge mid-fill), 1 s, resume -> count unchanged, no new ARMED line, state
      still "released" / "live", and an ENEMY's atb moves within 0.5 s of the resume (a release is final: ctrl F7).
  A3  [H-A3] A1 under `bench cfg atb wait` (host.cfg.atb 1): flat >= 2.5 s, holding, the ARMED line (mode independence).
  A4n/A4d/A4b/A4s  [H-A4] `bench boot none|declined|busy|silent`: one "not armed for battle nonce N -- <why>" line, why
      "none" | "declined" | "busy" | "no word yet", state "not_armed" once the 1000 ms late window has passed, count
      unchanged, no ARMED line, the lever's trailer on the wire (boot 0/3/4; silent: no frame at all), and some atb
      moves within 0.5 s of the first turn.enabled publish.
  A5  [H-A5] booting (cap 3000), then `bench boot stale` at held >= 1000 ms: the stale LIVE is on the wire (menu.ctl
      nonce == the battle's - 1, boot 2) and parsed by the host (start_hold.guest nonce/boot) yet releases NOTHING: the
      release is "cap" at held_ms 3000..3300.
  A6  [H-A6] booting + cap 3000: release "cap" at held_ms 3000..3300, the gauges flat until then (1 frame of slack), some
      atb moving within 0.5 s after it; released.cap +1.
  A7  [H-A7, ctrl F3] booting (cap 8000), `bench lapse 3000 reserve` at held >= 1000 ms (lapse.reserve true): release
      "link" at held_ms == (held at the lapse) + 2000 +/- 300 -- the null frame after the 2000 ms re-serve, before the
      cap; released.link +1.
  A8  [H-A8, ctrl F5] `bench boot late 300`: no control frame at the opening (menu.ctl.hex null), the "not armed -- no
      word yet" line, then "ARMED late +N ms" with N == late_ms in 300..400, why "late", state "holding", bit 4 set;
      then `bench boot live` releases it "live".
  L1  the stage's calibration lever, every run: `bench starthold 0` ('start hold OFF -- CALIBRATION') + booting -> no hold:
      some atb moves within 0.5 s, state "off", off true, count unchanged, no ARMED line, bit 4 never; `bench starthold 1`.
  B1  [H-B1] guest: `dioboot 67 0 play` + `bbench start 0x01` in BattleMapDebug -> menu.ctl.boot reads 1 through the
      intro (no 2 before the first PHASE_NORMAL publish), then 2 within 0.5 s of PHASE_NORMAL and from then on; every
      trailer nonce == the feed's nonce.
  B1L [H-B1] diorama.live: latched, ms ~ intro.normal_ms (|d| <= 100), nonce == the feed's; the 'diorama LIVE N ms after
      the boot (host battle nonce K' line and the guest's report lines '-> BOOTING' then '-> LIVE' for that nonce.
  B1b [H-B1b, ctrl F2] `dioleave`, a fresh `dioboot` + `bbench start`: live.latched false / ms -1 on the new boot's first
      publish, the feed nonce +1, and the report reads 1 (never 2, latched never true) until the NEW boot's PHASE_NORMAL,
      then 2.
  B2  [H-B2] the selftest proof block's line is exactly 'battle control selftest: OK (33 rows)' (ControlSelfTest: the
      codec + byte-1 nonce gate, GuestBootState's BUSY row, StartHoldStep's stale-nonce LIVE / 2-byte frame / unknown fmt
      / released-then-paused rows, HoldGate's spent cap) -- no FAIL line.
  C1  THE CLAMP (S114-LIVE-1): `bench starthold cap ini` -> cap_ms == the install's StartHoldMs as the engine parses it
      (quotes stripped; negative = 0 = off; absent / empty / malformed = 8000; past 60000 = 60000), off == (cap <= 0), the
      'cap back to [Netsync] StartHoldMs (N ms)' line -- and the '[NetSync] StartHoldMs N is past the ceiling -- clamped to
      60000 ms' line is in Memoria.log IF AND ONLY IF the ini value is past 60000 (read-only: Memoria.ini is never written).
  R   `reset` with `bench starthold cap 3000` and `bench boot booting` left set: 'start hold back to [Netsync] StartHoldMs
      (released with the harness)' + 'bench boot back to auto (released with the harness)'; then RE-READ WITH THE ROLE
      (_coop_battle.reread_with_role: `netsync selftest 1` releases nothing) -> cap_ms back to C1's ini cap, off == (cap <=
      0). The plain post-reset read cannot fail: StartHoldCapMs reads the bench fields only under IsSelfTestRole.
NOT PROVEN HERE (two-machine sitting A, boxes A2-A7, A10, A20): the laptop's real boot-to-live time, the watcher's own
NONE (a world-map battle) and BUSY (the guest's main menu), the transport's real null frame after a network cut, two
battles' nonces back to back on the wire, an old-DLL guest's 2-byte frames, Speed 2 / turn-based, the feel.

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s110) -- and any engine before s114 (s111-s113 read the same): `start_hold` is absent, so
    P0 is RED and `bench boot` / `bench starthold` are NEVER sent (nor `bench cfg` before s113). The control battle A0
    still runs and must stay GREEN (no hold on the old engine either). RED, exactly: P0, P2 (never sent), B2 (no
    ControlSelfTest line), A1 (not reached -- its detail carries A0's measurement: with no hold this engine's gauges ran
    within 0.5 s of turn.enabled, H-A1's "atb rises within 0.5 s"), A2, A9, A3, A4n, A4d, A4b, A4s, A5, A6, A7, A8, L1
    (not reached: ops withheld), B1 (no `menu.ctl.boot`: the feed's frames carry no trailer -- s110 has no `ctl` key,
    s113's has no `boot`), B1L and B1b (no `netsync.diorama.live`), C1 (not reached), R (no lever line). GREEN there,
    exactly: S0, P1, A0 -- 3 of 24. COOP_CALIBRATE=1 on such an engine judges exactly that red set as S14-CAL.
  * IN-RUN, on the s114+ DLL: leg L1 is the lever's red every run (judged as its own check). COOP_CALIBRATE=1 also pulls
    `bench starthold 0` for EVERY host leg (P2 then asserts the lever took); predicted reds, exactly: A1, A2, A9, A3, A4n,
    A4d, A4b, A4s, A5, A6, A7, A8 (state "off": nothing holds, nothing is decided, no line) -- A0, L1, the guest legs B1/
    B1L/B1b (the guest's report ignores the host's lever), B2, C1 (the lever goes back on first) and R stay green. S14-CAL
    judges that set (the run itself is red by design).
  * MEASURED ON THE STAND-IN, the old-engine path only (tools/harness/fakegame.py pinned to its s110 rung, atb_gain 400):
    S0, P1 and A0 green, the other 21 red -- the guest legs by their absent keys (no trailer, no `diorama.live`), the rest
    "not reached". The stand-in models no start hold at writing, and the scenario has NOT been run in game: the first
    live run is the calibration above.

RE-BASELINES this DLL brings to OTHER benches: none of their checks. Every selftest own battle now logs one "start hold not
armed ... -- the guest has no diorama of it" line, and `menu.ctl.hex` / the feed's `ctl` are 5 bytes (byte 1 unchanged).

    py tools/play.py studies/test-harness/scenarios/coop_battle_start_hold.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_battle_start_hold.py --field 30602
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

PROBE = cb.R3_PROBES[114]                 # s114 start_hold: `bench boot` / `bench starthold` (before it: read as `bench 1`)
WAIT_PROBE = cb.R3_PROBES[113]            # s113 host.wait: `bench cfg atb` and `bench lapse <ms> reserve` (s111 has `bench cfg`)
FEED_PROBE = cb.PROBES[8]                  # s107: the bench feed (`bbench start`)
INTRO_S = 40.0                             # scene 67's opening camera is a few seconds
FIGHT_S = 300.0
FLAT_S = 2.5                               # H-A1: every gauge flat at least this long
RISE_S = 0.5                               # "atb rising within 0.5 s"
CAP_MS = 8000                              # the bench cap of every non-cap leg
SHORT_CAP_MS = 3000                        # the cap legs (A5, A6)
CAP_SLACK_MS = 300                         # "+0..300"
HELD_AT_MS = 1000                          # A5 / A7: "at +1 s"
LATE_MS = 300                              # A8: `bench boot late 300`
LATE_SLACK_MS = 100
LATE_ARM_MS = 1000                         # NetSyncBattle.LateArmMs
LAPSE_MS = 3000
RESERVE_MS = 2000                          # NetSyncBattle.LapseReserveMs
LINK_TOL_MS = 300
CEILING_MS = 60000                         # NetSyncBattle.StartHoldMaxMs
INI_DEFAULT_MS = 8000                      # [Netsync] StartHoldMs's default (and what a malformed value keeps)
LIVE_TOL_MS = 100                          # B1L: diorama.live.ms ~ intro.normal_ms
SELFTEST_ROWS = 33                         # NetSyncBattle.ControlSelfTest's rows
FLAG_START_HOLD = 0x10                     # type-1 header flags bit 4
BOOT_LIVE = 2

ARMED_ANY = "start hold ARMED"
RX_ARMED = re.compile(r"start hold ARMED for battle nonce (\d+) -- the guest's diorama is BOOTING; every gauge waits "
                      r"\(cap (\d+) ms\)")
RX_LATE = re.compile(r"start hold ARMED late \+(\d+) ms for battle nonce (\d+) -- ")
RX_NOT = re.compile(r"start hold not armed for battle nonce (\d+) -- (.+) \(a BOOTING report within 1000 ms still arms it\)")
RX_REL = re.compile(r"start hold RELEASED after (\d+) ms: ([a-z ]+) -- (.+) \(battle nonce (\d+); final for this battle\)")
RX_CLAMP = re.compile(r"\[NetSync\] StartHoldMs (-?\d+) is past the ceiling -- clamped to (\d+) ms")
LEVER_OFF = "harness: start hold OFF -- CALIBRATION"
LEVER_ON = "harness: start hold ON (cap "
CAP_INI = "harness: start hold cap back to [Netsync] StartHoldMs ("
REL_HOLD = "harness: start hold back to [Netsync] StartHoldMs (released with the harness)"
REL_BOOT = "harness: bench boot back to auto (released with the harness)"
PROOF = "battle control selftest:"
PROOF_OK = f"battle control selftest: OK ({SELFTEST_ROWS} rows)"
LIVE_LINE = "diorama LIVE "
REPORT = "start hold report: host battle nonce "

#: A4: (bench boot op, check id, start_hold.why, the not-armed phrase, the trailer's boot byte -- None = no frame at all)
A4_MODES = (("none", "S14-A4n", "none", "the guest has no diorama of it", 0),
            ("declined", "S14-A4d", "declined", "the guest declined this battle", 3),
            ("busy", "S14-A4b", "busy", "the guest is busy", 4),
            ("silent", "S14-A4s", "no word yet", "no word yet from a guest", None))


def _catalog(calibrate: bool) -> dict:
    c = {
        "S14-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S14-P0": "the engine publishes `netsync.battle.host.start_hold` (memoria-patch s114) -- else `bench boot` / "
                  "`bench starthold` are NEVER sent (an engine before s114 reads them as `bench 1`)",
        "S14-P1": "`netsync guestslots 0` is accepted (host.guest_slots 0) -- every party slot is the host's own; the "
                  "loopback guest still reports every tick",
        "S14-P2": ("the lever is PULLED for calibration: `bench starthold 0` -> start_hold.off true, cap_ms 0, 'start hold "
                   "OFF -- CALIBRATION' logged once" if calibrate else
                   "`bench starthold cap 8000` -> start_hold.cap_ms 8000, off false, state 'idle' between battles, the "
                   "'start hold cap 8000 ms for this process' line"),
        "S14-B2": f"the selftest proof block's line reads exactly '{PROOF_OK}' -- no FAIL line",
        "S14-A0": "control (both DLLs): an own battle with NO lever (auto = NONE) -- some unit's atb moves within 0.5 s of "
                  "the first turn.enabled publish; no 'start hold ARMED' line; host.caps bit 4 never set",
        "S14-A1": "A1: `bench boot booting` + `battle 67` -> every unit's atb constant for >= 2.5 s from the first "
                  "turn.enabled publish; state 'holding', why 'booting', count +1; host.caps & 0x10; ONE 'start hold ARMED "
                  "for battle nonce N -- ... BOOTING ... (cap 8000 ms)' line naming start_hold.nonce",
        "S14-A2": "A2: then `bench boot live` -> release 'live' within 2 frames of the first loopback frame carrying LIVE "
                  "(menu.ctl.boot 2); some atb moves within 0.5 s; released.live +1; caps bit 4 clear within 2 frames; ONE "
                  "'start hold RELEASED after N ms: live' line, N == held_ms >= 2500",
        "S14-A9": "A9: after the live release, pause (an enemy gauge mid-fill), 1 s, resume -> count unchanged, no new "
                  "'start hold ARMED' line, state 'released' / release 'live', an enemy's atb moves within 0.5 s of the "
                  "resume",
        "S14-A3": "A3: A1 under `bench cfg atb wait` (host.cfg.atb 1) -> every atb constant for >= 2.5 s, state 'holding', "
                  "the ARMED line (mode independence)",
        "S14-A5": "A5: booting (cap 3000), `bench boot stale` at held >= 1000 ms -> the stale LIVE on the wire (menu.ctl "
                  "nonce == nonce - 1, boot 2) and parsed (start_hold.guest), yet released only by the cap: release 'cap' at "
                  "held_ms 3000..3300, the 'RELEASED ... cap' line",
        "S14-A6": "A6: booting + cap 3000 -> release 'cap' at held_ms 3000..3300; every atb flat until then (1 frame of "
                  "slack); some atb moves within 0.5 s after; released.cap +1; the 'RELEASED ... cap' line",
        "S14-A7": "A7: booting (cap 8000), `bench lapse 3000 reserve` at held >= 1000 ms (lapse.reserve) -> release 'link' "
                  "at held_ms == held-at-the-lapse + 2000 +/- 300, before the cap; released.link +1; the 'RELEASED ... "
                  "link' line",
        "S14-A8": "A8: `bench boot late 300` -> no control frame at the opening (menu.ctl.hex null), the 'not armed ... no "
                  "word yet' line, then ONE 'ARMED late +N ms' line with N == late_ms in 300..400, why 'late', state "
                  "'holding', caps bit 4; then `bench boot live` releases it 'live'",
        "S14-L1": "L1 (the lever): `bench starthold 0` ('start hold OFF -- CALIBRATION') + booting -> no hold: some atb "
                  "moves within 0.5 s, state 'off', off true, count unchanged, no ARMED line, caps bit 4 never; `bench "
                  "starthold 1` -> 'start hold ON (cap 8000 ms)'",
        "S14-B1": "B1 guest: `dioboot 67 0 play` + `bbench start 0x01` -> menu.ctl.boot 1 through the intro (never 2 before "
                  "the first PHASE_NORMAL publish), 2 within 0.5 s of PHASE_NORMAL and from then on; every trailer nonce "
                  "== the feed's nonce",
        "S14-B1L": "B1: diorama.live latched, |live.ms - intro.normal_ms| <= 100, live.nonce == the feed's nonce; the "
                   "'diorama LIVE N ms after the boot (host battle nonce K' line, and the report lines '-> BOOTING' then "
                   "'-> LIVE' for nonce K",
        "S14-B1b": "B1b: `dioleave`, a fresh `dioboot` + `bbench start` -> live.latched false and ms -1 on the new boot's "
                   "first publish, the feed nonce +1, menu.ctl.boot 1 (never 2, latched never true) until the NEW boot's "
                   "PHASE_NORMAL, then 2",
        "S14-C1": "C1 (the clamp): `bench starthold cap ini` -> cap_ms == the ini's StartHoldMs as the engine parses it "
                  "(past 60000 = 60000), off == (cap <= 0), the 'cap back to [Netsync] StartHoldMs (N ms)' line; the "
                  "'StartHoldMs N is past the ceiling -- clamped to 60000 ms' line logged iff the ini value is past 60000",
        "S14-R": "`reset` with `bench starthold cap 3000` + `bench boot booting` left set: 'start hold back to [Netsync] "
                 "StartHoldMs (released with the harness)' + 'bench boot back to auto (released with the harness)', the "
                 "role released; then RE-READ WITH THE ROLE (`netsync selftest 1`, which releases nothing -- cap_ms reads "
                 "the ini while the role is off): cap_ms back to the ini cap, off == (cap <= 0)",
    }
    for _op, cid, why, phrase, boot in A4_MODES:
        c[cid] = (f"A4 (`bench boot {_op}`): ONE 'not armed for battle nonce N -- {phrase} ...' line, why {why!r}, state "
                  f"'not_armed' past the 1000 ms late window, count unchanged, no ARMED line, "
                  + ("no control frame at all (menu.ctl.hex null)" if boot is None else f"menu.ctl.boot {boot}")
                  + ", some atb moves within 0.5 s of turn.enabled")
    if calibrate:
        c["S14-CAL"] = ("CALIBRATION: exactly the predicted checks are red -- on an engine without `start_hold` every check "
                        "but S0/P1/A0; on the s114 DLL under `bench starthold 0` exactly A1, A2, A9, A3, A4n/d/b/s, A5-A8")
    return c


HOST_LEGS = ("S14-A1", "S14-A2", "S14-A9", "S14-A3", "S14-A4n", "S14-A4d", "S14-A4b", "S14-A4s", "S14-A5", "S14-A6",
             "S14-A7", "S14-A8", "S14-L1")
GUEST_LEGS = ("S14-B1", "S14-B1L", "S14-B1b")
#: COOP_CALIBRATE=1 on the s114+ DLL: `bench starthold 0` for every host leg -- nothing holds, nothing is decided.
LEVER_PREDICTED = ("S14-A1", "S14-A2", "S14-A9", "S14-A3", "S14-A4n", "S14-A4d", "S14-A4b", "S14-A4s", "S14-A5", "S14-A6",
                   "S14-A7", "S14-A8")
#: COOP_CALIBRATE=1 on an engine without `start_hold` (the deployed s110, or s111-s113): all but S0, P1 and A0.
OLD_PREDICTED = tuple(c for c in _catalog(True) if c not in ("S14-S0", "S14-P1", "S14-A0", "S14-CAL"))


# ------------------------------------------------------------------------------------------------- reads
def _num(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _sub(d, key: str) -> dict:
    v = d.get(key) if isinstance(d, dict) else None
    return v if isinstance(v, dict) else {}


def _sh(x) -> dict:
    return _sub(cb.host(x), "start_hold")


def _shg(x) -> dict:
    return _sub(_sh(x), "guest")


def _rel(x) -> dict:
    return _sub(_sh(x), "released")


def _ctl(x) -> dict:
    return _sub(cb.bmenu(x), "ctl")


def _feed(x) -> dict:
    return _sub(cb.bmenu(x), "feed")


def _live(x) -> dict:
    return _sub(cb.dio(x), "live")


def _dintro(x) -> dict:
    return _sub(cb.dio(x), "intro")


def _caps4(x) -> bool:
    return bool(cb.mask_bits(cb.host(x).get("caps")) & FLAG_START_HOLD)


def _boot_of(x) -> int | None:
    v = _num(_ctl(x).get("boot"))
    return v if v is not None and v >= 0 else None


def _no_frame(x) -> bool:
    """The loopback sent no control frame this tick: `menu.ctl` is PUBLISHED (s113+) and its hex is null -- an engine
    without the key never reads as "no frame"."""
    return cb.has(x, "netsync.battle.menu.ctl.hex") and _ctl(x).get("hex") is None


def _brief(x) -> str:
    return (f"phase={cb.battle(x).get('phase')!r} enabled={bool(cb.turn(x).get('enabled'))} "
            f"caps={cb.host(x).get('caps')!r} start_hold="
            f"{cb.pick(_sh(x), 'off', 'cap_ms', 'state', 'nonce', 'why', 'release', 'held_ms', 'late_ms', 'count')} "
            f"guest={cb.pick(_shg(x), 'fmt', 'nonce', 'boot')} ctl={cb.pick(_ctl(x), 'nonce', 'boot', 'hex')}")


def _matches(rx, lines) -> list:
    return [m for m in (rx.search(ln) for ln in lines) if m]


def _atbs(x, *, enemies: bool = False) -> dict:
    """{btl id: atb} of the battle's units (living enemies only with ``enemies``); units with no readable atb left out."""
    out = {}
    for u in cb.units(x, player=False if enemies else None):
        if enemies and not u.get("alive"):
            continue
        a = _num(u.get("atb"))
        if a is not None and a >= 0:
            out[int(u.get("id", -1))] = a
    return out


def _moved(base: dict, x, *, enemies: bool = False) -> list:
    now = _atbs(x, enemies=enemies)
    return [(k, v, now[k]) for k, v in base.items() if k in now and now[k] != v]


def _rises(g, st0, *, enemies: bool = False) -> tuple:
    """How long after ``st0`` some gauge (an enemy's, with ``enemies``) first moved: (seconds or None, base, samples)."""
    base = _atbs(st0, enemies=enemies) if st0 is not None else {}
    if not base:
        return None, base, []
    samples, hit = cb.watch_from(g, st0, lambda s: bool(_moved(base, s, enemies=enemies)), RISE_S + 0.4)
    return (cb.elapsed(st0, hit) if hit is not None else None), base, samples


def _flat(g, st0, seconds: float = FLAT_S) -> tuple:
    """Every publish for ``seconds`` past ``st0``: (base, samples incl. st0, [(frame, id, was, now)] moved, span s)."""
    base = _atbs(st0)
    seq = [st0] + cb.hold_for(g, seconds + 0.15)
    moved = [(cb.frame_of(x), k, v, w) for x in seq for k, v, w in _moved(base, x)]
    return base, seq, moved, (cb.elapsed(st0, seq[-1]) if len(seq) > 1 else 0.0)


def _rise_txt(el, base) -> str:
    if not base:
        return "no unit with a readable atb"
    return f"first atb move {el:.3f} s after" if el is not None else f"no atb moved within {RISE_S + 0.4:.1f} s of"


# ------------------------------------------------------------------------------------------------- acting
def _bench_guard(st, args) -> str:
    """The call-site probe: why `bench <args>` must NOT be sent to this engine ('' = it may be)."""
    op = str(args[0]).strip().lower() if args else ""
    if op in ("boot", "starthold") and not cb.has(st, PROBE):
        return (f"not sent: `bench {op}` needs `{PROBE}` (memoria-patch s114) -- an engine before it reads `bench {op}` as "
                f"`bench 1` (the field-gate bench ON)")
    if op == "cfg" and not cb.has(st, WAIT_PROBE):
        return (f"not sent: `bench cfg atb` needs `{WAIT_PROBE}` (memoria-patch s113) -- an engine before s111 reads "
                f"`bench cfg` as `bench 1`")
    if op == "lapse" and "reserve" in [str(a).lower() for a in args] and not cb.has(st, WAIT_PROBE):
        return f"not sent: `bench lapse <ms> reserve` needs `{WAIT_PROBE}` (memoria-patch s113)"
    return ""


def _bench_st(g, *args) -> tuple:
    """`netsync bench <args>` behind the call-site probe. (the state after it or None, why-not)."""
    try:
        why = _bench_guard(g.state, args)
        if why:
            return None, why
        return cb.ns_verb(g, "bench", *args), ""
    except (HarnessError, AttributeError) as err:          # AttributeError: a driver table naming an accessor not there
        return None, str(err)[:300]


def _bench(g, *args) -> tuple:
    st, why = _bench_st(g, *args)
    return st is not None, why


def _field_ready(g, label: str):
    return cb.poll(g, lambda s: cb.free(s) and s.ui_state == "FieldHUD" and not s.in_battle, 30.0,
                   f"a playable field before {label}")


def _open(g, label: str, *, boot: str | None, cap: int | None) -> tuple:
    """A leg's battle: its levers set BEFORE `battle` (the hold primes in the intro), the log mark and the counters before
    it, then every publish up to the first turn.enabled one. (ctx or None, why)."""
    if _field_ready(g, label) is None:
        return None, f"not on a playable field before {label} (ui {g.state.ui_state!r}, field {g.state.field_id})"
    steps = []
    if boot is not None:
        steps.append(("boot", *boot.split()))
    if cap is not None:
        steps.append(("starthold", "cap", cap))
    for args in steps:
        ok, why = _bench(g, *args)
        if not ok:
            return None, f"`bench {' '.join(str(a) for a in args)}` refused: {why}"
    st = g.state
    ctx = {"label": label, "at": cb.mark(g), "count": _num(_sh(st).get("count")), "released": dict(_rel(st))}
    try:
        st = g.start_battle(cb.SCENE)
    except HarnessError as err:
        return None, f"`battle {cb.SCENE}` ({label}) did not start: {str(err)[:200]}"
    intro, en = cb.watch_from(g, st, lambda s: s.commands_enabled, INTRO_S)
    if en is None:
        return None, f"{label} never reached its command phase (turn.enabled) -- {_brief(g.state)}"
    ctx["intro"], ctx["en"] = intro, en
    return ctx, ""


def _finish(g) -> None:
    """Fight the battle out and get back to the field (whatever leg ended where)."""
    try:
        if g.state.in_battle:
            g.fight(timeout=FIGHT_S, finish=False)
    except HarnessError as err:
        g.note(f"the battle did not finish cleanly: {str(err)[:160]}")
    for _ in range(40):
        st = g.state
        if not st.in_battle and st.ui_state not in ("BattleHUD", "BattleResult"):
            break
        g.press("confirm", 4)
        g.wait_frames(20)
    cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD", 30.0, "the field after the battle")


def _wait_held(g, ms: int, timeout: float = 4.0):
    return cb.poll(g, lambda s: (_num(_sh(s).get("held_ms")) or -1) >= ms and _sh(s).get("state") == "holding", timeout,
                   f"start_hold.held_ms >= {ms} while holding")


# ------------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _catalog(calibrate), finals=("S14-R", "S14-CAL"))
    ctx = {"probe": False, "ini_cap": None}
    try:
        _run(g, led, field, calibrate, ctx)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'start-hold')}")
        led.close()                                        # every leg check is recorded before the judge reads them
        _release(g, led, ctx)
        if calibrate:
            led.judge_calibration("S14-CAL", LEVER_PREDICTED if ctx["probe"] else OLD_PREDICTED)
        led.close(final=True)


def _run(g, led: cb.Ledger, field: int, calibrate: bool, ctx: dict) -> None:
    ok, why = cb.setup(g, field, label="R3 s114: the start hold, solo"
                                       + (" -- CALIBRATION (bench starthold 0)" if calibrate else ""))
    led.check("S14-S0", ok, why)
    st = g.state
    have = ctx["probe"] = cb.has(st, PROBE)
    led.check("S14-P0", have, f"netsync.battle.host keys: {sorted(cb.host(st))}" if cb.has(st, "netsync.battle") else
              "no `netsync.battle` at all (a pre-s100 engine)")
    g.note(f"probe stage: {cb.stage_note(st)}; start_hold {'present' if have else 'ABSENT'}; host.wait "
           f"{'present' if cb.has(st, WAIT_PROBE) else 'absent'}" + ("" if have else
           " -- `bench boot` / `bench starthold` will NOT be sent (a pre-s114 agent reads them as `bench 1`)"))
    _leg_b2(g, led)
    ok, why = cb.try_ns(g, "guestslots", 0)
    st = cb.poll(g, lambda s: cb.host(s).get("guest_slots") == 0, 1.5, "host.guest_slots to read 0") if ok else None
    led.check("S14-P1", ok and st is not None, why or f"guest_slots={cb.host(g.state).get('guest_slots')!r}")
    if not ok:
        led.close(f"`netsync guestslots 0` refused -- {why}")
        return
    try:
        g.state_every(1)
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]}) -- frame windows read at the default cadence")
    if have:
        _leg_p2(g, led, calibrate)
    else:
        led.unreached(("S14-P2",), f"`{PROBE}` is absent: the lever and the bench cap were never sent")
    if cb.has(g.state, WAIT_PROBE):
        ok, why = _bench(g, "cfg", "atb", "active")
        if not ok:
            g.note(f"`bench cfg atb active` refused ({why}) -- the save's own ATB mode stands")
    measure = _leg_a0(g, led, have)
    if not have:
        led.check("S14-A1", False, f"not reached: `{PROBE}` is absent, so `bench boot booting` was never sent; with no "
                                   f"hold this engine's gauges ran from the first command-phase frame ({measure})")
        led.unreached(HOST_LEGS, f"`{PROBE}` is absent: an engine before s114 (the probe fails closed; `bench boot` / "
                                 f"`bench starthold` were never sent)")
    else:
        _battle_1(g, led)
        _leg_a3(g, led)
        for mode in A4_MODES:
            _leg_a4(g, led, mode)
        _leg_a5(g, led)
        _leg_a6(g, led)
        _leg_a7(g, led)
        _leg_a8(g, led)
        _leg_l1(g, led, calibrate)
        if cb.has(g.state, WAIT_PROBE):
            _bench(g, "cfg", "atb", "restore")
    _guest_legs(g, led, field, have)
    if have:
        _leg_c1(g, led, ctx)
    else:
        led.unreached(("S14-C1",), f"`{PROBE}` is absent: `bench starthold cap ini` was never sent")


# ------------------------------------------------------------------------------------------------- P2 / B2 / A0
def _leg_p2(g, led: cb.Ledger, calibrate: bool) -> None:
    at = cb.mark(g)
    if calibrate:
        ok, why = _bench(g, "starthold", 0)
        lines = cb.wait_log(g, at, LEVER_OFF, 1.5)
        st = cb.poll(g, lambda s: _sh(s).get("off") is True, 1.5, "start_hold.off to read true") or g.state
        sh = _sh(st)
        led.check("S14-P2", ok and sh.get("off") is True and sh.get("cap_ms") == 0 and cb.count(lines, LEVER_OFF) == 1,
                  why or f"{cb.pick(sh, 'off', 'cap_ms', 'state')}; {cb.grep(lines, 'start hold')}")
        return
    ok, why = _bench(g, "starthold", "cap", CAP_MS)
    want = f"harness: start hold cap {CAP_MS} ms for this process (Memoria.ini untouched)"
    lines = cb.wait_log(g, at, want, 1.5)
    st = cb.poll(g, lambda s: _sh(s).get("cap_ms") == CAP_MS, 1.5, f"start_hold.cap_ms to read {CAP_MS}") or g.state
    sh = _sh(st)
    led.check("S14-P2", ok and sh.get("cap_ms") == CAP_MS and sh.get("off") is False and sh.get("state") == "idle"
              and cb.count(lines, want) == 1, why or f"{cb.pick(sh, 'off', 'cap_ms', 'state')}; {cb.grep(lines, 'start hold')}")


def _leg_b2(g, led: cb.Ledger) -> None:
    """The selftest proof block logs once per process, on the first selftest tick on a field (setup gives it one)."""
    proof = cb.poll(g, lambda s: cb.count(cb.log_lines(g), PROOF) >= 1, 8.0, "the selftest proof block's control line")
    lines = [ln for ln in cb.log_lines(g) if PROOF in ln]
    last = lines[-1] if lines else ""
    failed = [ln for ln in lines if "battle control selftest: FAIL" in ln]
    led.check("S14-B2", proof is not None and PROOF_OK in last and not failed,
              (last.split("|", 2)[-1].strip()[-300:] if last else
               "no 'battle control selftest' line (an engine before s114 has no ControlSelfTest)")
              + (f"; FAIL lines: {len(failed)}" if failed else ""))


def _leg_a0(g, led: cb.Ledger, have: bool) -> str:
    g.note("A0: the control -- an own battle with no bench lever (auto: the loopback reports NONE); every gauge runs")
    if have:
        _bench(g, "boot", "auto")
    ctx, why = _open(g, "A0", boot=None, cap=None)
    if ctx is None:
        led.check("S14-A0", False, f"not reached: {why}")
        return f"A0 never reached: {why}"
    try:
        en = ctx["en"]
        el, base, rs = _rises(g, en)
        tail = cb.hold_for(g, 0.3)
        lines = cb.new(g, ctx["at"])
        caps4 = [cb.frame_of(x) for x in ctx["intro"] + rs + tail if _caps4(x)]
        measure = f"{_rise_txt(el, base)} turn.enabled (units {sorted(base)})"
        led.check("S14-A0", bool(base) and el is not None and el <= RISE_S and cb.count(lines, ARMED_ANY) == 0
                  and not caps4,
                  f"{measure}; ARMED lines {cb.count(lines, ARMED_ANY)}; caps bit 4 at frames {caps4[:4]}; "
                  f"{cb.grep(lines, 'start hold')}; {_brief(tail[-1] if tail else en)}")
        return measure
    finally:
        _finish(g)


# ------------------------------------------------------------------------------------------------- A1 + A2 + A9
def _judge_held(g, led: cb.Ledger, cid: str, ctx: dict, *, wait_mode: bool = False) -> bool:
    """A1 / A3: from the first turn.enabled publish every gauge flat >= 2.5 s, holding, bit 4, one ARMED line."""
    en = ctx["en"]
    base, seq, moved, span = _flat(g, en)
    last = seq[-1]
    sh = _sh(last)
    lines = cb.new(g, ctx["at"])
    armed = _matches(RX_ARMED, lines)
    c0 = ctx["count"]
    nonce = _num(sh.get("nonce"))
    caps_on = [cb.frame_of(x) for x in seq if _caps4(x)]
    atb_mode = _sub(cb.host(en), "cfg").get("atb")
    mode_ok = (not wait_mode) or atb_mode == 1
    ok = (bool(base) and not moved and span >= FLAT_S and sh.get("state") == "holding" and sh.get("why") == "booting"
          and c0 is not None and sh.get("count") == c0 + 1 and bool(caps_on) and _caps4(last)
          and len(armed) == 1 and nonce is not None and int(armed[0].group(1)) == nonce
          and int(armed[0].group(2)) == CAP_MS and mode_ok)
    led.check(cid, ok, f"units {sorted(base)} over {span:.2f} s from turn.enabled (frame {cb.frame_of(en)}): moved "
                       f"(frame, id, was, now) {moved[:4]}; count {c0!r}->{sh.get('count')!r}; caps bit 4 on "
                       f"{len(caps_on)}/{len(seq)} publish(es); cfg.atb {atb_mode!r}; ARMED lines "
                       f"{[m.group(0) for m in armed][:2]}; {_brief(last)}")
    return sh.get("state") == "holding"


def _battle_1(g, led: cb.Ledger) -> None:
    g.note("A1/A2/A9: a BOOTING guest holds every gauge; its LIVE releases them, once and for good")
    ctx, why = _open(g, "A1", boot="booting", cap=CAP_MS)
    if ctx is None:
        led.unreached(("S14-A1", "S14-A2", "S14-A9"), why)
        return
    try:
        holding = _judge_held(g, led, "S14-A1", ctx)
        if not holding:
            led.unreached(("S14-A2", "S14-A9"), f"the hold is not holding ({_brief(g.state)})")
            return
        released = _leg_a2(g, led, ctx)
        _leg_a9(g, led, released)
    finally:
        _finish(g)


def _leg_a2(g, led: cb.Ledger, ctx: dict) -> bool:
    rel0 = _num(_sub(ctx, "released").get("live"))
    at = cb.mark(g)
    st0, why = _bench_st(g, "boot", "live")
    samples, hit = cb.watch_from(g, st0, lambda s: _sh(s).get("release") is not None, 1.5) if st0 is not None \
        else ([], None)
    el, base, rs = _rises(g, hit) if hit is not None else (None, {}, [])
    tail = cb.hold_for(g, 0.2)
    f_ctl = cb.first_frame(samples, lambda x: _boot_of(x) == BOOT_LIVE)
    f_rel = cb.frame_of(hit) if hit is not None else None
    after = [x for x in samples + rs + tail if f_rel is not None and cb.frame_of(x) >= f_rel]
    f_clear = cb.first_frame(after, lambda x: not _caps4(x))
    s = g.state
    sh = _sh(s)
    held = _num(sh.get("held_ms"))
    lines = cb.new(g, at)
    rels = _matches(RX_REL, lines)
    ok = (hit is not None and _sh(hit).get("release") == "live" and f_ctl is not None and 0 <= f_rel - f_ctl <= 2
          and el is not None and el <= RISE_S and sh.get("state") == "released" and rel0 is not None
          and _rel(s).get("live") == rel0 + 1 and f_clear is not None and f_clear - f_rel <= 2
          and len(rels) == 1 and rels[0].group(2) == "live" and held is not None and int(rels[0].group(1)) == held
          and held >= int(FLAT_S * 1000))
    led.check("S14-A2", ok, why or f"LIVE on the wire at frame {f_ctl!r}, released at {f_rel!r} "
                                   f"({_sh(hit).get('release') if hit is not None else None!r}); bit 4 clear at "
                                   f"{f_clear!r}; {_rise_txt(el, base)} the release; released.live {rel0!r}->"
                                   f"{_rel(s).get('live')!r}; lines {[m.group(0)[:90] for m in rels][:2]}; {_brief(s)}")
    return hit is not None and _sh(hit).get("release") == "live"


def _enemy_filling(g, timeout: float = 8.0):
    """A publish where a living enemy's gauge is mid-fill and RISING (so a resume can only move it, not an action)."""
    prev: dict = {}

    def until(s) -> bool:
        hit = False
        for u in cb.units(s, player=False):
            a, m = _num(u.get("atb")), _num(u.get("atb_max"))
            if not u.get("alive") or a is None or m is None or m <= 0:
                continue
            k = int(u.get("id", -1))
            p = prev.get(k)
            if p is not None and p < a < 0.6 * m:
                hit = True
            prev[k] = a
        return hit

    _, hit = cb.watch(g, until, timeout)
    return hit


def _leg_a9(g, led: cb.Ledger, released: bool) -> None:
    g.note("A9: pause and resume after the release -- nothing re-arms, the gauges run")
    if not released:
        led.check("S14-A9", False, f"not reached: no 'live' release preceded it ({_brief(g.state)})")
        return
    filling = _enemy_filling(g)
    c0 = _num(_sh(g.state).get("count"))
    at = cb.mark(g)
    g.press("start", 4)
    paused = cb.poll(g, lambda s: s.ui_state == "Pause" or not s.commands_enabled, 3.0, "the pause")
    if paused is None:
        led.check("S14-A9", False, f"not reached: the pause never engaged (ui {g.state.ui_state!r}, enabled "
                                   f"{g.state.commands_enabled})")
        return
    during = cb.hold_for(g, 1.0)
    g.press("start", 4)
    resumed = cb.poll(g, lambda s: s.ui_state == "BattleHUD" and s.commands_enabled, 3.0, "the resume")
    el, base, _ = _rises(g, resumed, enemies=True) if resumed is not None else (None, {}, [])
    s = g.state
    sh = _sh(s)
    lines = cb.new(g, at)
    ok = (resumed is not None and el is not None and el <= RISE_S and c0 is not None and sh.get("count") == c0
          and cb.count(lines, ARMED_ANY) == 0 and sh.get("state") == "released" and sh.get("release") == "live")
    led.check("S14-A9", ok, f"enemy mid-fill before the pause: {filling is not None}; paused {len(during)} publish(es); "
                            f"resumed: {resumed is not None}; {_rise_txt(el, base)} the resume (enemies {sorted(base)}); "
                            f"count {c0!r}->{sh.get('count')!r}; ARMED lines since the pause {cb.count(lines, ARMED_ANY)}; "
                            f"{_brief(s)}")


# ------------------------------------------------------------------------------------------------- A3 / A4
def _leg_a3(g, led: cb.Ledger) -> None:
    g.note("A3: the same hold under Wait (mode independence)")
    ok, why = _bench(g, "cfg", "atb", "wait")
    if not ok:
        led.check("S14-A3", False, f"not reached: `bench cfg atb wait` refused: {why}")
        return
    try:
        ctx, why = _open(g, "A3", boot="booting", cap=CAP_MS)
        if ctx is None:
            led.check("S14-A3", False, f"not reached: {why}")
            return
        try:
            _judge_held(g, led, "S14-A3", ctx, wait_mode=True)
            _bench(g, "boot", "live")                       # let it go now: the fight needs no 8 s cap
        finally:
            _finish(g)
    finally:
        _bench(g, "cfg", "atb", "active")


def _leg_a4(g, led: cb.Ledger, mode: tuple) -> None:
    op, cid, want_why, phrase, boot = mode
    g.note(f"A4 ({op}): the guest reports {op.upper()} -- the hold is never armed, the gauges run")
    ctx, why = _open(g, f"A4 {op}", boot=op, cap=CAP_MS)
    if ctx is None:
        led.check(cid, False, f"not reached: {why}")
        return
    try:
        en = ctx["en"]
        el, base, rs = _rises(g, en)
        cb.hold_for(g, (LATE_ARM_MS + 300) / 1000.0)       # past the late window: "not_armed"
        s = g.state
        sh = _sh(s)
        lines = cb.new(g, ctx["at"])
        nots = _matches(RX_NOT, lines)
        nonce = _num(sh.get("nonce"))
        wire = _no_frame(s) if boot is None else _boot_of(s) == boot
        ok = (bool(base) and el is not None and el <= RISE_S and sh.get("why") == want_why
              and sh.get("state") == "not_armed" and ctx["count"] is not None and sh.get("count") == ctx["count"]
              and cb.count(lines, ARMED_ANY) == 0 and len(nots) == 1 and nonce is not None
              and int(nots[0].group(1)) == nonce and phrase in nots[0].group(2) and wire)
        led.check(cid, ok, f"{_rise_txt(el, base)} turn.enabled; not-armed lines {[m.group(0)[:110] for m in nots][:2]}; "
                           f"ARMED lines {cb.count(lines, ARMED_ANY)}; the lever on the wire: {wire}; {_brief(s)}")
    finally:
        _finish(g)


# ------------------------------------------------------------------------------------------------- A5 / A6 / A7 / A8
def _cap_release_ok(sh: dict, cap: int) -> bool:
    held = _num(sh.get("held_ms"))
    return sh.get("release") == "cap" and held is not None and cap <= held <= cap + CAP_SLACK_MS


def _leg_a5(g, led: cb.Ledger) -> None:
    g.note("A5: a stale LIVE (naming the previous battle) releases nothing -- the cap does")
    ctx, why = _open(g, "A5", boot="booting", cap=SHORT_CAP_MS)
    if ctx is None:
        led.check("S14-A5", False, f"not reached: {why}")
        return
    try:
        if _wait_held(g, HELD_AT_MS) is None:
            led.check("S14-A5", False, f"not reached: the hold never held {HELD_AT_MS} ms ({_brief(g.state)})")
            return
        st0, why = _bench_st(g, "boot", "stale")
        nonce = _num(_sh(st0 or g.state).get("nonce"))
        want = (nonce - 1) & 0xFF if nonce is not None else None
        wire = cb.poll(g, lambda s: _ctl(s).get("nonce") == want and _boot_of(s) == BOOT_LIVE
                       and _shg(s).get("nonce") == want and _shg(s).get("boot") == BOOT_LIVE, 1.0,
                       "the stale LIVE on the wire and parsed") if st0 is not None and want is not None else None
        samples, hit = cb.watch_from(g, st0, lambda s: _sh(s).get("release") is not None, 4.0) if st0 is not None \
            else ([], None)
        s = hit or g.state
        sh = _sh(s)
        lines = cb.new(g, ctx["at"])
        rels = _matches(RX_REL, lines)
        rel0 = _num(_sub(ctx, "released").get("cap"))
        ok = (wire is not None and hit is not None and _cap_release_ok(sh, SHORT_CAP_MS) and rel0 is not None
              and _rel(s).get("cap") == rel0 + 1 and len(rels) == 1 and rels[0].group(2) == "cap"
              and f"the cap ({SHORT_CAP_MS} ms)" in rels[0].group(3))
        led.check("S14-A5", ok, why or f"stale nonce {want!r} on the wire+parsed: {wire is not None}; release "
                                       f"{sh.get('release')!r} at held_ms {sh.get('held_ms')!r}; released.cap {rel0!r}->"
                                       f"{_rel(s).get('cap')!r}; lines {[m.group(0)[:100] for m in rels][:2]}; {_brief(s)}")
    finally:
        _finish(g)


def _leg_a6(g, led: cb.Ledger) -> None:
    g.note("A6: the cap releases a hold whose release never comes")
    ctx, why = _open(g, "A6", boot="booting", cap=SHORT_CAP_MS)
    if ctx is None:
        led.check("S14-A6", False, f"not reached: {why}")
        return
    try:
        en = ctx["en"]
        base = _atbs(en)
        samples, hit = cb.watch_from(g, en, lambda s: _sh(s).get("release") is not None, SHORT_CAP_MS / 1000.0 + 2.0)
        f_rel = cb.frame_of(hit) if hit is not None else None
        early = [(cb.frame_of(x), k, v, w) for x in samples if f_rel is not None and cb.frame_of(x) < f_rel - 1
                 for k, v, w in _moved(base, x)]
        el, rb, _ = _rises(g, hit) if hit is not None else (None, {}, [])
        s = g.state
        sh = _sh(hit or s)
        lines = cb.new(g, ctx["at"])
        rels = _matches(RX_REL, lines)
        rel0 = _num(_sub(ctx, "released").get("cap"))
        ok = (bool(base) and hit is not None and _cap_release_ok(sh, SHORT_CAP_MS) and not early and el is not None
              and el <= RISE_S and rel0 is not None and _rel(s).get("cap") == rel0 + 1 and len(rels) == 1
              and rels[0].group(2) == "cap")
        led.check("S14-A6", ok, f"release {sh.get('release')!r} at held_ms {sh.get('held_ms')!r} (frame {f_rel!r}); "
                                f"moved before it {early[:4]}; {_rise_txt(el, rb)} the release; released.cap {rel0!r}->"
                                f"{_rel(s).get('cap')!r}; lines {[m.group(0)[:100] for m in rels][:2]}; {_brief(s)}")
    finally:
        _finish(g)


def _leg_a7(g, led: cb.Ledger) -> None:
    g.note("A7: a link cut -- the transport's null frame (after the 2 s re-serve) releases 'link', before the cap")
    ctx, why = _open(g, "A7", boot="booting", cap=CAP_MS)
    if ctx is None:
        led.check("S14-A7", False, f"not reached: {why}")
        return
    try:
        pre_st = _wait_held(g, HELD_AT_MS)
        if pre_st is None:
            led.check("S14-A7", False, f"not reached: the hold never held {HELD_AT_MS} ms ({_brief(g.state)})")
            return
        pre = _num(_sh(g.state).get("held_ms"))
        st0, why = _bench_st(g, "lapse", LAPSE_MS, "reserve")
        post = _num(_sh(st0).get("held_ms")) if st0 is not None else None
        reserve = _sub(_sub(cb.host(st0), "handback"), "lapse").get("reserve") if st0 is not None else None
        samples, hit = cb.watch_from(g, st0, lambda s: _sh(s).get("release") is not None, 4.0) if st0 is not None \
            else ([], None)
        s = g.state
        sh = _sh(hit or s)
        held = _num(sh.get("held_ms"))
        lines = cb.new(g, ctx["at"])
        rels = _matches(RX_REL, lines)
        rel0 = _num(_sub(ctx, "released").get("link"))
        lo = (pre or 0) + RESERVE_MS - LINK_TOL_MS
        hi = (post if post is not None else pre or 0) + RESERVE_MS + LINK_TOL_MS
        ok = (hit is not None and sh.get("release") == "link" and held is not None and pre is not None and lo <= held <= hi
              and held < CAP_MS and reserve is True and rel0 is not None and _rel(s).get("link") == rel0 + 1
              and len(rels) == 1 and rels[0].group(2) == "link")
        led.check("S14-A7", ok, why or f"lapse armed at held {pre!r}..{post!r} ms (reserve {reserve!r}); release "
                                       f"{sh.get('release')!r} at held_ms {held!r} (window {lo}..{hi}); released.link "
                                       f"{rel0!r}->{_rel(s).get('link')!r}; lines {[m.group(0)[:100] for m in rels][:2]}; "
                                       f"{_brief(s)}")
        _bench(g, "lapse", "end")
    finally:
        _finish(g)


def _leg_a8(g, led: cb.Ledger) -> None:
    g.note("A8: no word at the opening, BOOTING 300 ms later -- the hold arms late")
    ctx, why = _open(g, "A8", boot=f"late {LATE_MS}", cap=CAP_MS)
    if ctx is None:
        led.check("S14-A8", False, f"not reached: {why}")
        return
    try:
        en = ctx["en"]
        silent_open = _no_frame(en)
        samples, hit = cb.watch_from(g, en, lambda s: _sh(s).get("state") == "holding", 2.0)
        tail = cb.hold_for(g, 0.3)
        s = hit or g.state
        sh = _sh(s)
        late = _num(sh.get("late_ms"))
        lines = cb.new(g, ctx["at"])
        nots = [i for i, ln in enumerate(lines) if RX_NOT.search(ln) and "no word yet from a guest" in ln]
        lates = [(i, m) for i, m in ((i, RX_LATE.search(ln)) for i, ln in enumerate(lines)) if m]
        nonce = _num(sh.get("nonce"))
        armed_ok = (hit is not None and silent_open and sh.get("why") == "late" and late is not None
                    and LATE_MS <= late <= LATE_MS + LATE_SLACK_MS and ctx["count"] is not None
                    and sh.get("count") == ctx["count"] + 1 and len(nots) == 1 and len(lates) == 1
                    and nots[0] < lates[0][0] and int(lates[0][1].group(1)) == late
                    and nonce is not None and int(lates[0][1].group(2)) == nonce and any(_caps4(x) for x in tail))
        rel_ok, rwhy = False, "not tried: the late arm did not hold"
        if hit is not None:
            st0, rwhy = _bench_st(g, "boot", "live")
            _, rh = cb.watch_from(g, st0, lambda x: _sh(x).get("release") is not None, 1.5) if st0 is not None \
                else ([], None)
            rel_ok = rh is not None and _sh(rh).get("release") == "live"
            rwhy = rwhy or f"release {_sh(rh or g.state).get('release')!r}"
        led.check("S14-A8", armed_ok and rel_ok,
                  f"no frame at the opening: {silent_open}; why {sh.get('why')!r} late_ms {late!r} count "
                  f"{ctx['count']!r}->{sh.get('count')!r}; line order (not-armed, ARMED late) "
                  f"{(nots[:1], [i for i, _ in lates][:1])}; bit 4 after the arm: {any(_caps4(x) for x in tail)}; then "
                  f"`bench boot live`: {rwhy}; {_brief(s)}")
    finally:
        _finish(g)


# ------------------------------------------------------------------------------------------------- L1 (the lever)
def _leg_l1(g, led: cb.Ledger, calibrate: bool) -> None:
    g.note("L1: the calibration lever `bench starthold 0` -- the pre-stage host: a BOOTING guest holds nothing")
    at = cb.mark(g)
    ok, why = (True, "") if calibrate else _bench(g, "starthold", 0)
    lever_lines = cb.count(cb.log_lines(g), LEVER_OFF) if calibrate else cb.count(cb.wait_log(g, at, LEVER_OFF, 1.5),
                                                                                    LEVER_OFF)
    if not ok:
        led.check("S14-L1", False, f"not reached: `bench starthold 0` refused: {why}")
        return
    try:
        ctx, why = _open(g, "L1", boot="booting", cap=CAP_MS)
        if ctx is None:
            led.check("S14-L1", False, f"not reached: {why}")
            return
        try:
            en = ctx["en"]
            el, base, rs = _rises(g, en)
            tail = cb.hold_for(g, 1.2)
            s = g.state
            sh = _sh(s)
            lines = cb.new(g, ctx["at"])
            caps4 = [cb.frame_of(x) for x in ctx["intro"] + rs + tail if _caps4(x)]
            ok = (bool(base) and el is not None and el <= RISE_S and sh.get("state") == "off" and sh.get("off") is True
                  and ctx["count"] is not None and sh.get("count") == ctx["count"] and cb.count(lines, ARMED_ANY) == 0
                  and not caps4 and lever_lines >= 1)
            led.check("S14-L1", ok, f"{_rise_txt(el, base)} turn.enabled; caps bit 4 at {caps4[:4]}; ARMED lines "
                                    f"{cb.count(lines, ARMED_ANY)}; lever lines {lever_lines}; {_brief(s)}")
        finally:
            _finish(g)
    finally:
        if not calibrate:
            at = cb.mark(g)
            ok, why = _bench(g, "starthold", 1)
            lines = cb.wait_log(g, at, LEVER_ON, 1.5)
            if not ok or not any(LEVER_ON + f"{CAP_MS} ms)" in ln for ln in lines):
                g.note(f"L1: `bench starthold 1` did not read back ON at cap {CAP_MS} ({why or cb.grep(lines, 'start hold')})")


# ------------------------------------------------------------------------------------------------- B (the guest)
def _gboot(g) -> tuple:
    """`dioboot 67 0 play` (the s111 token: a bench host's choice 'play') and wait for BattleMapDebug. An engine without
    `netsync.diorama.intro` gets the plain `dioboot 67 0` (the driver refuses the token there: such an engine ignores it,
    and a non-random manual boot plays its intro anyway), so the guest legs still MEASURE its red (no trailer). A boot
    refused for a scene fade in flight is retried once (Boot names why only in the log)."""
    tokens = ("play",) if cb.has(g.state, "netsync.diorama.intro") else ()
    why = ""
    for attempt in range(2):
        at = cb.mark(g)
        ok, why = cb.try_ns(g, "dioboot", cb.SCENE, cb.PATTERN, *tokens)
        if ok:
            why = ""
            break
        if "diorama boot REFUSED" in why:
            logged = cb.grep(cb.wait_log(g, at, cb.BOOT_REFUSED, 2.0), cb.BOOT_REFUSED, limit=240)
            if logged:
                why = f"{why} -- log: {logged}"
        if cb.FADE_REFUSAL not in why or attempt:
            return None, f"dioboot refused: {why}"
        g.wait_frames(30)
    st = cb.poll(g, cb.in_diorama, cb.BOOT_S, "the diorama (BattleMapDebug, battle.debug) to come up")
    if st is None:
        s = g.state
        return None, f"the diorama never came up (scene={s.scene!r} booted={cb.dio(s).get('booted')!r})"
    return st, ""


def _feed_run(g) -> tuple:
    """`bbench start 0x01` in the booted diorama, then every publish until its command phase and 1 s past it."""
    try:
        st0 = cb.ns_verb(g, "bbench", "start", "0x01")
    except (HarnessError, AttributeError) as err:
        return None, f"`bbench start 0x01` refused: {str(err)[:200]}"
    samples, hit = cb.watch_from(g, st0, cb.steady, cb.STEADY_S)
    if hit is None:
        return None, f"the diorama never reached its command phase ({_brief(g.state)})"
    return samples + cb.hold_for(g, 1.0), ""


def _story(samples) -> dict:
    """The report's walk over one boot: the trailers before the first PHASE_NORMAL publish (after the feed's first frame),
    the first LIVE, and every publish after it."""
    i_norm = next((i for i, x in enumerate(samples) if cb.battle(x).get("phase") == cb.PHASE_NORMAL), None)
    pre = samples[:i_norm] if i_norm is not None else list(samples)
    i_first = next((i for i, x in enumerate(pre) if _boot_of(x) is not None), None)
    pre_boots = [(cb.frame_of(x), _boot_of(x)) for x in pre[i_first:]] if i_first is not None else []
    i2 = next((i for i, x in enumerate(samples) if _boot_of(x) == BOOT_LIVE), None)
    after2 = [(cb.frame_of(x), _boot_of(x)) for x in samples[i2:]] if i2 is not None else []
    last = samples[-1] if samples else None
    fn = _num(_feed(last).get("nonce")) if last is not None else None
    nonces = sorted({_num(_ctl(x).get("nonce")) for x in samples if _boot_of(x) is not None} - {None, -1})
    lag = cb.elapsed(samples[i_norm], samples[i2]) if i_norm is not None and i2 is not None else None
    ok = (bool(pre_boots) and all(b == 1 for _, b in pre_boots) and i_norm is not None and i2 is not None
          and i2 >= i_norm and lag is not None and lag <= RISE_S and all(b == BOOT_LIVE for _, b in after2)
          and fn is not None and nonces == [fn])
    return {"ok": ok, "pre": pre_boots, "i_norm": i_norm, "i2": i2, "lag": lag, "after_bad": [p for p in after2 if
            p[1] != BOOT_LIVE][:4], "feed_nonce": fn, "nonces": nonces, "pre_latched": [cb.frame_of(x) for x in pre
            if _live(x).get("latched") is True]}


def _story_txt(sty: dict) -> str:
    return (f"trailers before PHASE_NORMAL (frame, boot) {sty['pre'][:3]}..{sty['pre'][-2:]} ({len(sty['pre'])}); "
            f"PHASE_NORMAL at sample {sty['i_norm']!r}, first LIVE at {sty['i2']!r} ({sty['lag']!r} s later); not-LIVE "
            f"after it {sty['after_bad']}; feed nonce {sty['feed_nonce']!r}, trailer nonces {sty['nonces']}")


def _guest_legs(g, led: cb.Ledger, field: int, have: bool) -> None:
    g.note("B: the guest's report -- a bench-feed diorama reads BOOTING through its intro, LIVE from its command phase")
    if not cb.has(g.state, FEED_PROBE):
        led.unreached(GUEST_LEGS, f"`{FEED_PROBE}` is absent: no stage-8 bench feed to stand in for the host's lane")
        return
    if have:
        _bench(g, "boot", "auto")                           # the feed reports its OWN diorama state
    if _field_ready(g, "the guest legs") is None:
        led.unreached(GUEST_LEGS, f"not on a playable field ({g.state.ui_state!r})")
        return
    at = cb.mark(g)
    st, why = _gboot(g)
    samples, fwhy = _feed_run(g) if st is not None else (None, why)
    if samples is None:
        led.unreached(GUEST_LEGS, fwhy)
        cb.back_to_field(g, field)
        return
    sty = _story(samples)
    led.check("S14-B1", sty["ok"], _story_txt(sty))
    s = samples[-1]
    lv, fn = _live(s), sty["feed_nonce"]
    ms, nms = _num(lv.get("ms")), _num(_dintro(s).get("normal_ms"))
    lines = cb.new(g, at)
    live_lines = [ln for ln in lines if LIVE_LINE in ln and f"ms after the boot (host battle nonce {fn}," in ln]
    ib = next((i for i, ln in enumerate(lines) if f"{REPORT}{fn} -> BOOTING" in ln), None)
    il = next((i for i, ln in enumerate(lines) if f"{REPORT}{fn} -> LIVE" in ln), None)
    led.check("S14-B1L", lv.get("latched") is True and ms is not None and ms >= 0 and nms is not None and nms >= 0
              and abs(ms - nms) <= LIVE_TOL_MS and fn is not None and lv.get("nonce") == fn and len(live_lines) == 1
              and ib is not None and il is not None and ib < il,
              f"live={lv or 'ABSENT'} intro.normal_ms={nms!r} feed nonce {fn!r}; LIVE lines {len(live_lines)}; report "
              f"lines BOOTING@{ib!r} LIVE@{il!r}; {cb.grep(lines, 'start hold report', LIVE_LINE, limit=300)}")
    ok, why = cb.leave(g, field)
    if not ok:
        led.unreached(("S14-B1b",), f"the first diorama never left: {why}")
        cb.back_to_field(g, field)
        return
    g.note("B1b: a fresh boot reports BOOTING until ITS OWN command phase (no carried latch)")
    st, why = _gboot(g)
    first_live = _live(st) if st is not None else {}
    samples, fwhy = _feed_run(g) if st is not None else (None, why)
    if samples is None:
        led.unreached(("S14-B1b",), fwhy)
        cb.back_to_field(g, field)
        return
    sty2 = _story(samples)
    fn2 = sty2["feed_nonce"]
    led.check("S14-B1b", sty2["ok"] and first_live.get("latched") is False and first_live.get("ms") == -1
              and not sty2["pre_latched"] and fn is not None and fn2 == (fn + 1) & 0xFF,
              f"the new boot's first publish live={first_live or 'ABSENT'}; latched before PHASE_NORMAL at "
              f"{sty2['pre_latched'][:4]}; feed nonce {fn!r}->{fn2!r}; {_story_txt(sty2)}")
    ok, why = cb.leave(g, field)
    if not ok:
        g.note(f"B1b: the second diorama never left: {why}")
        cb.back_to_field(g, field)


# ------------------------------------------------------------------------------------------------- C1 / R
def _ini_cap(g) -> tuple:
    """[Netsync] StartHoldMs as NetSyncClient parses it, from Memoria.ini READ-ONLY: (cap, clamp line expected, raw)."""
    raw = cb.ini_value(g, "Netsync", "StartHoldMs")
    if raw is None:
        return INI_DEFAULT_MS, False, None
    s = str(raw).strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1].strip()
    if not re.fullmatch(r"[+-]?\d+", s) or not -2 ** 31 <= int(s) < 2 ** 31:
        return INI_DEFAULT_MS, False, raw                   # malformed (or empty): 8000 kept
    n = int(s)
    cap = 0 if n < 0 else n
    return (CEILING_MS, True, raw) if cap > CEILING_MS else (cap, False, raw)


def _leg_c1(g, led: cb.Ledger, ctx: dict) -> None:
    g.note("C1: the cap back to the ini value -- and the 60000 ms ceiling's clamp line only when the ini is past it")
    _bench(g, "starthold", 1)                               # (calibration left the lever off)
    at = cb.mark(g)
    st, why = _bench_st(g, "starthold", "cap", "ini")
    exp, clamp, raw = _ini_cap(g)
    ctx["ini_cap"] = exp
    lines = cb.wait_log(g, at, CAP_INI, 1.5)
    clamps = _matches(RX_CLAMP, cb.log_lines(g))
    sh = _sh(st or g.state)
    clamp_ok = (bool(clamps) and all(int(m.group(2)) == CEILING_MS for m in clamps)) if clamp else not clamps
    led.check("S14-C1", st is not None and sh.get("cap_ms") == exp and sh.get("off") is (exp <= 0)
              and any(f"{CAP_INI}{exp} ms)" in ln for ln in lines) and clamp_ok,
              why or f"ini StartHoldMs {raw!r} -> expected cap {exp} (clamp line expected: {clamp}); "
                     f"{cb.pick(sh, 'off', 'cap_ms', 'state')}; clamp lines {[m.group(0) for m in clamps][:2]}; "
                     f"{cb.grep(lines, 'start hold cap')}")


def _release(g, led: cb.Ledger, ctx: dict) -> None:
    """The levers left SET on purpose (only on an engine that has them), then `reset`: both must come back, logged."""
    have = ctx["probe"]
    if have:
        ok1, w1 = _bench(g, "starthold", "cap", SHORT_CAP_MS)
        ok2, w2 = _bench(g, "boot", "booting")
    else:
        ok1, ok2, w1, w2 = False, False, f"`{PROBE}` absent: never sent", ""
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    lines = cb.new(g, at)
    forced = (st.netsync or {}).get("forced")
    exp = ctx["ini_cap"] if ctx["ini_cap"] is not None else _ini_cap(g)[0]
    # cap_ms reads the ini whenever the role is off (StartHoldCapMs reads the bench fields only under IsSelfTestRole), and
    # `reset` released the role: re-read it WITH the role (re-forced, which releases nothing) -- the release lines and this
    # re-read are the real check (review R3H-3)
    rr, rwhy = cb.reread_with_role(g) if have else (None, "")
    sh = _sh(rr) if rr is not None else {}
    led.check("S14-R", have and ok1 and ok2 and cb.count(lines, REL_HOLD) == 1 and cb.count(lines, REL_BOOT) == 1
              and rr is not None and sh.get("cap_ms") == exp and sh.get("off") is (exp <= 0) and forced is False,
              (w1 or w2) or (f"re-read WITH the role: cap_ms {sh.get('cap_ms')!r} off {sh.get('off')!r} (ini {exp})"
                             if rr is not None else f"no re-read with the role ({rwhy})")
                            + f"; forced after reset={forced!r}; {cb.grep(lines, 'released with the harness')}")
