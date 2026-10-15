"""R3 SITTING-A FIX #1 -- THE HAND-BACK NEEDS A LIVE GUEST (memoria-patch s118), the solo bench, run unattended.

THE GAP (studies/battle-coop/R3-SITTING-A-FIXES.md, s118; owner decision: "the host keeps it until a LIVE report returns,
then hands it back at the command root"). Before s118 ANY valid control frame stamped the guest's ownership stamp
(`_assistTick`), so G3 (s110) handed a held guest slot back to a guest whose s114 report read DECLINED -- sitting A, 10:37:27:
the laptop had left its diorama (the skip stamped) and reloaded its own autosave, and its only control was the legacy digit
panel on its field. s118, HOST only (NetSyncBattle.cs): the ownership stamp is earned through the pure GuestOwnsStep /
GuestOwnsFromReport -- a trailer-less frame owns (an s110-s113 guest, today's rule); a report owns on LIVE/BOOTING for THIS
battle, or on NONE while the per-battle latch `_rptDioramaSeen` is down (no diorama report on this battle yet = no diorama
path: a FollowHost=0 guest or one off a field, whose digit panel is its designed control -- review S118-NONE-PANEL, the
exception the fix pass KEPT). DECLINED, BUSY, an unknown state, NONE after the latch, or another battle's report keep the
slots with the host's ready loop (byte 1 reads shut); one line per own battle, one count per refusal episode at the open
command phase; G3 hands back, root-only and unchanged, on the tick a LIVE (or BOOTING) report returns.
No new verb or op: the bench drives s114's `netsync bench boot none|live|declined|busy|booting|stale` (the loopback
guest's report) and s110's `netsync bench lapse hold|end` (the loopback guest's STALL). `bench boot auto` -- every earlier
bench's default -- keeps its stand-in NONE owning as before s118 (ParseControl's loopbackAuto), which is why
coop_battle_handback.py (stage 11) needs no edit and this bench lives in its own file (stage 11's 21-check calibration
stays as measured).

THE BENCH. REAL selftest own battles (`battle 67`, one Goblin) on field 30602 with >= 2 members (COOPPARTY seeds +vivi
+garnet +steiner), `netsync guestslots 2` (slot 1 belongs to the loopback guest), `stateevery 1` (frame windows on the
doc's own counter, Time.frameCount -- the clock of `handback.last.frame` and `lapse.end_frame`). Every leg starts with slot
1 Ready (in turn.ready, not done, peer.ready_mask bit 1) and the host's window NOT on it, committing any other slot the
window opens with Defend; slot 1 is never commanded, so after its first fill it stays Ready across the legs (each hand-back
returns it Ready, not done). Battle 1 runs with `bench boot none` set BEFORE `battle` (the latch is per own battle):
N, D, L. Battle 2 with `bench boot live` set before it: B, T, S. The hand-back log budget is 8 lines per own battle; each
battle here spends at most 7 on the s118 DLL.

CAUTION: THE PROBE COMES FIRST. An engine before s110 reads `bench lapse` as `bench 1`, one before s114 reads `bench boot`
as `bench 1` -- the FIELD-GATE bench ON. :func:`_bench` refuses AT THE CALL SITE to send them without
`netsync.battle.host.handback` / `netsync.battle.host.start_hold` (P2), whatever the driver's NETSYNC_BENCH_OPS knows. The
s118 key (`netsync.battle.host.handback.refused_report`, P0) gates NOTHING that is sent: s117 runs every leg -- that is
its calibration red.

WHAT IS PROVEN (S18-*):
  PROOF  the selftest proof block's line reads exactly 'battle control selftest: OK (53 rows)' (ControlSelfTest 33 -> 53:
         the `own:` rows of GuestOwnsFromReport and the `step:` sequences of GuestOwnsStep) -- no FAIL line.
  N1  NONE FROM THE START (the panel-only exception, BOTH DLLs -- non-regression): `bench boot none` before battle 1 ->
      slot 1 stands guest-owned (the host's window never takes it without a lapse); `bench lapse hold` -> the capture
      (captures +1, owed false, '... silent N ms (a stall) ...'); `bench lapse end` at the root -> returns +1, last {slot 1,
      why 'handed back'}, last.frame - lapse.end_frame in 0..3, ONE 'handed BACK ... sat at the command root' line.
  N2  N's s118 keys: on every publish through N `handback.diorama_seen` is false and `refused_now` false; `refused_report`
      flat; no "its slots stay with the host's window" line -- a NONE before any diorama report OWNS.
  D1  DECLINED, the sitting-A shape: `bench boot live` (the latch rises), `bench lapse hold` -> capture; `bench boot
      declined`; `bench lapse end` at the root -> for >= 60 frames past lapse.end_frame turn.slot 1, handback.held 1,
      returns flat; owed false; no 'handed BACK' line.
  D2  D's refusal: refused_now true, refused_report +1 exactly, diorama_seen true, `host.wait.menu` 0, ONE 'hand-back: the
      guest's control lane is live but it reports declined for this battle -- its slots stay with the host's window ...'
      line. (`wait.menu` 0 discriminates nothing HERE: while the host's window holds slot 1, G6 withholds its Ready bit, so
      the loopback guest sends byte 1 = 0 under either rule -- L1 reads the shut byte where it does discriminate.)
  D3  then `bench boot live` -> ONE hand-back at the root: returns +1 within 1.5 s, last.why 'handed back' (frame after the
      lever), one 'handed BACK ... sat at the command root' line, turn.slot leaves 1, slot 1 still Ready (not done),
      held -1, refused_now false.
  L1  NONE AFTER THE LATCH (no lapse: the lane stays LIVE): `bench boot none` -> within 9 s the host's window captures slot
      1 (captures +1, held 1, owed false) and the capture line NAMES THE REPORT ('... the guest's control lane is live but
      it reports none for this battle after reporting a diorama of it ...'; no '(a stall)' capture line); refused_now
      true, refused_report +1, diorama_seen true; BYTE 1 READS SHUT: every publish from the first whose
      start_hold.guest.boot reads 0 (the NONE parsed) up to the capture reads `host.wait.menu` 0 -- slot 1 is Ready and not
      held there, so the loopback guest's own byte is 2 (the root) and only the refusal shuts it (no Wait freeze from a
      guest that commands nothing); no second 'its slots stay' line this battle (one per own battle -- D spent it; exactly
      one naming the NONE if D logged none).
  L2  then `bench boot live` -> one hand-back at the root (as D3).
  B1  BUSY (battle 2, `bench boot live` from its start): lapse hold -> capture; `bench boot busy`; `bench lapse end` at the
      root -> held >= 60 frames, returns flat, owed false, no 'handed BACK'; refused_now true, refused_report +1,
      diorama_seen true, ONE 'it reports busy for this battle -- its slots stay with the host's window' line (battle 2's).
  B2  then `bench boot live` -> one hand-back at the root (as D3).
  T1  BOOTING (BOTH DLLs -- non-regression: BOOTING still owns, so a normal start is unchanged): lapse hold -> capture;
      `bench boot booting`; `bench lapse end` at the root -> returns +1, why 'handed back', last.frame - lapse.end_frame in
      0..3, ONE 'handed BACK ... sat at the command root' line.
  S1  STALE (a LIVE naming the PREVIOUS battle nonce): lapse hold -> capture; `bench boot stale`; `bench lapse end` -> the
      stale LIVE on the wire and parsed (menu.ctl / start_hold.guest nonce == the battle's - 1, boot 2) yet held >= 60
      frames, returns flat, owed false; refused_now true, refused_report +1; no second 'its slots stay' line this battle (B
      spent it; exactly one naming "its report names another battle" if B logged none).
  S2  then `bench boot live` -> one hand-back at the root (as D3).
NOT PROVEN HERE (two-machine, the next sitting): a REAL guest's DECLINED from its watcher (a cut's watcher-leave, a ~ Leave,
the reload), its BUSY (the guest's main menu), the relay's timing, an s110-s113 guest's trailer-less frames (owns as
before -- ControlSelfTest's `own: no report` row only), the end-leave staying quiet (the refusal is counted only at the
open command phase), and the KNOWN follow-up: a refused guest's digit panel still shows Ready for the slots the host keeps
and its picks are refused host-side ("not a guest slot") without a word to it.

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s117) -- and any s114-s117 engine: `refused_report` is absent, so P0 is RED, yet every leg
    RUNS (`bench boot` and `bench lapse` are s114/s110 ops). RED, exactly: P0 (the key), PROOF ('OK (33 rows)'), N2 (no
    diorama_seen / refused_now / refused_report keys), D1 (the sitting-A defect reproduced: any valid frame owns, so the
    DECLINED guest is handed slot 1 back within ~3 frames of the lapse end -- returns +1, the 'handed BACK' line), D2 (keys
    absent, no 'its slots stay' line), D3 (not reached: slot 1 is no longer held, the hand-back already fired), L1 (no
    capture in 9 s: the live lane owns whatever it reports, and byte 1 reads the guest's 2), L2 (not reached: no capture),
    B1 + B2 and S1 + S2 (as D1 + D3). GREEN there, exactly: S0, P1, P2, PRE, N1, T1 -- 6 of 18 (the two non-regression
    legs green on both DLLs). COOP_CALIBRATE=1 on such an engine judges exactly that red set as S18-CAL.
    N1 and T1 are green on s117 by its own code, not by hope: its ParseControl stamps the ownership on ANY valid frame
    (`_assistTick = Environment.TickCount;   // any valid control frame ...`), so a NONE (N) or BOOTING (T) report owns,
    the lapse capture logs TrackHostHold's '... has been silent N ms (a stall)' and the lapse end HandBackGuestSlot's
    '... handed BACK to the guest -- ... sat at the command root (held N ms) ... returns=N' -- the matchers here read the
    deployed s117's own two lines in sitting A's host log (.harness-runs/sittingA-20261014/Memoria.log:72-73) as one stall
    capture and one root hand-back, and its zero 'its slots stay' / report-naming capture lines.
  * ON THE s118 DLL: no same-DLL lever exists (s118 ships no op -- `bench boot auto`'s loopbackAuto is a stand-in's
    exemption, not the old rule), so the behavioural red IS the s117 run above. COOP_CALIBRATE=1 there judges the EMPTY red
    set: it is the green run, and S18-CAL says so. The same holds on the stack through s121 (as captured): s119 acts only
    in a following guest's watcher (DioramaTick, which the selftest role never runs), s120's session clock only on a
    client (SessionTick returns for any other role), s121 only on a mirroring guest's Menu press -- none of them reaches
    a selftest host's own battle, so every verdict here is s118's.
    Log budget: each battle spends at most 7 of HandbackLog's 8 lines on s118 (battle 1: N capture + root, D capture + its
    'stay' + root, L capture + root; battle 2: B capture + 'stay' + root, T capture + root, S capture + root).
  * An engine before s114 (no `bench boot`) or s110 (no `bench lapse`): P2 RED and every leg RED "not reached" (nothing is
    sent) -- no calibration target.
  * THE STAND-IN (tools/harness/fakegame.py) models s110's capture/hand-back, s114's `bench boot` AND s118 (the
    "ownreport" cap: the lane and ownership stamps, the per-battle latch, the refusal episode's count and its one line per
    own battle, the shut byte), and writes the engine's own hand-back, refusal and proof lines into its Memoria.log
    (CRLF, Memoria's line shape; HandbackLog's 8-line budget). Its s117 is the stand-in with FG.NETSYNC_SITTING_A_CAPS
    removed. MEASURED [ff9mapkit netsync R3 fix round]: s121 caps -- all 18 green, COOP_CALIBRATE=1 S18-CAL PASS on the
    empty set; s117 caps -- red exactly P0, PROOF, N2, D1, D2, D3, L1, L2, B1, B2, S1, S2 (N1 and T1 green on the
    stand-in's own s117 hand-back lines), COOP_CALIBRATE=1 S18-CAL PASS with no unpredicted red. A seeded stand-in that
    keeps a refused frame's byte 1 turns L1 alone red. It is a calibration aid for THIS scenario's logic, never a proof
    of the engine: the first in-game run is the s117 calibration above.

    py tools/play.py studies/test-harness/scenarios/coop_handback_live.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_handback_live.py --field 30602
  PowerShell has no per-launch form: a `$env:` value PERSISTS in that shell, so the next "normal" run would read
  calibrated without a word. Clear it after the calibrated run [ff9mapkit netsync R3 resume]:
    $env:COOP_CALIBRATE='1'; py tools/play.py studies/test-harness/scenarios/coop_handback_live.py --field 30602
    Remove-Item Env:COOP_CALIBRATE -ErrorAction SilentlyContinue
BENCH ON A QUIET MACHINE [ff9mapkit netsync R3 fix round 2]: the capture legs wait CAPTURE_S (9 s) for a capture the
engine makes ~MenuStaleMs (2.5 s) after the guest stops owning (a lapse, or L's refused report). A saturated machine
(a build, pytest -n 6, a second game) was MEASURED to stretch that past the old 6 s on the stand-in (B1 + B2 red,
18/18 again on a quiet rerun) -- a false red costs a rerun, not a wrong verdict, but run nothing heavy beside it.
The longer window costs no discrimination: the red case (s117: a live lane owns whatever it reports) never captures.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

#: [ff9mapkit netsync R3 s118] the capability probe (defined here: _coop_battle.R3_PROBES stops at s117 and belongs to
#: another author this round) -- absent = a host that hands a guest slot back on any control frame
PROBE = "netsync.battle.host.handback.refused_report"
LAPSE_PROBE = cb.PROBES[11]               # s110: `bench lapse` (before it: read as `bench 1`)
BOOT_PROBE = cb.R3_PROBES[114]            # s114: `bench boot` (before it: read as `bench 1`)

GUEST = 1
GBIT = 1 << GUEST
READY_S = 90.0                            # slot 1's first ATB fill (Wait mode freezes the gauges while a window is open)
CAPTURE_S = 9.0                           # MenuStaleMs (2.5 s) + slack; [ff9mapkit netsync R3 fix round 2] 6 -> 9 s:
                                          # a loaded machine stretched the capture past 6 s (a false red, not a verdict)
INTRO_S = 40.0
FIGHT_S = 300.0
HOLD_FRAMES = 60                          # "the host keeps it": s117 hands back within ~3 frames of the lapse end
HANDBACK_S = 1.5                          # `bench boot live` -> the hand-back (the next pump tick on s118)
SELFTEST_ROWS = 53                        # NetSyncBattle.ControlSelfTest's rows on s118 (33 on s114-s117)
BOOT_NONE = 0                             # NetSyncBattle.BootNone (the report byte `start_hold.guest.boot` publishes)
BOOT_LIVE = 2

CAPTURE_ANY = "hand-back: the host's local window holds guest slot 1 -- "
CAPTURE_STALL = CAPTURE_ANY + "the guest's control lane has been silent "
CAPTURE_REPORT = CAPTURE_ANY + "the guest's control lane is live but "
HANDED = "hand-back: guest slot 1 handed BACK to the guest -- "
AT_ROOT = "sat at the command root (held "
#: NoteRefusedReport's line (once per own battle) -- "hand-back: the guest's ..." never matches the capture line, whose
#: same words follow "slot 1 -- "
STAY = "hand-back: the guest's control lane is live but "
STAY_TAIL = " -- its slots stay with the host's window"
PROOF = "battle control selftest:"
PROOF_OK = f"battle control selftest: OK ({SELFTEST_ROWS} rows)"
#: RefusedReportPhrase, per `bench boot` op
PHRASE = {"declined": "it reports declined for this battle",
          "busy": "it reports busy for this battle",
          "none": "it reports none for this battle after reporting a diorama of it",
          "stale": "its report names another battle (nonce "}


def _catalog(calibrate: bool) -> dict:
    c = {
        "S18-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S18-P0": f"the engine publishes `{PROBE}` (memoria-patch s118) -- absent = a host that hands a guest slot back on "
                  "any control frame (nothing is withheld on its absence: the legs run, that is the calibration)",
        "S18-P2": "the levers the bench drives are there: `netsync.battle.host.handback` (s110 `bench lapse`) and "
                  "`netsync.battle.host.start_hold` (s114 `bench boot`) -- else neither is sent (an older agent reads "
                  "them as `bench 1`)",
        "S18-P1": "`netsync guestslots 2` is accepted -- the loopback guest owns party slot 1",
        "S18-PROOF": f"the selftest proof block's line reads exactly '{PROOF_OK}' (the ownership rows) -- no FAIL line",
        "S18-PRE": "precondition: battle 1 seats a member in slot 1 (COOPPARTY)",
        "S18-N1": "N (both DLLs): `bench boot none` from the start -> slot 1 guest-owned until `bench lapse hold` captures "
                  "it ('... silent N ms (a stall)', captures +1, owed false); `bench lapse end` at the root -> returns +1, "
                  "last {slot 1, 'handed back'}, last.frame - lapse.end_frame in 0..3, ONE 'handed BACK ... sat at the "
                  "command root' line",
        "S18-N2": "N (s118): on every publish through N handback.diorama_seen false and refused_now false, refused_report "
                  "flat, no 'its slots stay with the host's window' line -- a NONE before any diorama report OWNS",
        "S18-D1": "D: `bench boot live`, lapse hold -> capture, `bench boot declined`, `bench lapse end` at the root -> for "
                  f">= {HOLD_FRAMES} frames past lapse.end_frame turn.slot 1, held 1, returns flat; owed false; no 'handed "
                  "BACK' line",
        "S18-D2": "D: refused_now true, refused_report +1, diorama_seen true, host.wait.menu 0, ONE '... it reports "
                  "declined for this battle -- its slots stay with the host's window ...' line",
        "S18-D3": "D: then `bench boot live` -> ONE hand-back at the root within 1.5 s (returns +1, last.why 'handed back' "
                  "after the lever, the 'sat at the command root' line), turn.slot leaves 1, slot 1 Ready not done, held "
                  "-1, refused_now false",
        "S18-L1": f"L: `bench boot none` after the latch, NO lapse -> within {CAPTURE_S:.0f} s the host's window captures "
                  "slot 1 (captures +1, held 1, owed false) and the capture line names the report ('... it reports none "
                  "for this battle after reporting a diorama of it ...', no '(a stall)' capture line); refused_now true, "
                  "refused_report +1, diorama_seen true; host.wait.menu 0 on every publish from the parsed NONE to the "
                  "capture (byte 1 shut); one 'its slots stay' line per own battle (none here if D logged it)",
        "S18-L2": "L: then `bench boot live` -> one hand-back at the root (as D3)",
        "S18-B1": f"B (battle 2): lapse hold -> capture, `bench boot busy`, `bench lapse end` at the root -> held >= "
                  f"{HOLD_FRAMES} frames, returns flat, owed false, no 'handed BACK'; refused_now true, refused_report +1, "
                  "diorama_seen true, ONE '... it reports busy for this battle -- its slots stay ...' line",
        "S18-B2": "B: then `bench boot live` -> one hand-back at the root (as D3)",
        "S18-T1": "T (both DLLs): lapse hold -> capture, `bench boot booting`, `bench lapse end` at the root -> returns +1, "
                  "'handed back', last.frame - lapse.end_frame in 0..3, ONE 'sat at the command root' line -- BOOTING owns",
        "S18-S1": f"S: lapse hold -> capture, `bench boot stale`, `bench lapse end` -> the stale LIVE on the wire and parsed "
                  f"(nonce == the battle's - 1, boot 2) yet held >= {HOLD_FRAMES} frames, returns flat, owed false; "
                  "refused_now true, refused_report +1; one 'its slots stay' line per own battle (none here if B logged it)",
        "S18-S2": "S: then `bench boot live` -> one hand-back at the root (as D3)",
    }
    if calibrate:
        c["S18-CAL"] = ("CALIBRATION: exactly the predicted checks are red -- on an engine without `refused_report` (s114-"
                        "s117) every check but S0/P1/P2/PRE/N1/T1; on the s118 DLL none (no same-DLL lever exists)")
    return c


BATTLE1 = ("S18-N1", "S18-N2", "S18-D1", "S18-D2", "S18-D3", "S18-L1", "S18-L2")
BATTLE2 = ("S18-B1", "S18-B2", "S18-T1", "S18-S1", "S18-S2")
#: COOP_CALIBRATE=1 on an engine without `refused_report` (the deployed s117, or s114-s116): all but the six green.
OLD_PREDICTED = tuple(k for k in _catalog(True)
                      if k not in ("S18-S0", "S18-P1", "S18-P2", "S18-PRE", "S18-N1", "S18-T1", "S18-CAL"))


# ------------------------------------------------------------------------------------------------- reads
def _num(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _sub(d, key: str) -> dict:
    v = d.get(key) if isinstance(d, dict) else None
    return v if isinstance(v, dict) else {}


def _hb(x) -> dict:
    return _sub(cb.host(x), "handback")


def _last(x) -> dict:
    return _sub(_hb(x), "last")


def _lapse(x) -> dict:
    return _sub(_hb(x), "lapse")


def _ctl(x) -> dict:
    return _sub(cb.bmenu(x), "ctl")


def _shg(x) -> dict:
    return _sub(_sub(cb.host(x), "start_hold"), "guest")


def _wait_menu(x):
    return _sub(cb.host(x), "wait").get("menu")


def _pbit(x) -> int:
    return cb.mask_bits(cb.peer(x).get("ready_mask")) & GBIT


def _held(x) -> bool:
    return x.turn_slot == GUEST and _hb(x).get("held") == GUEST


def _brief(x) -> str:
    t, h = cb.turn(x), _hb(x)
    return (f"turn.slot={t.get('slot')!r} ready={t.get('ready')} done={t.get('done')} group={cb.hud(x).get('group')!r} "
            f"panel={cb.hud(x).get('panel')!r} peer.ready={cb.peer(x).get('ready_mask')!r} wait.menu={_wait_menu(x)!r} "
            f"ctl={cb.pick(_ctl(x), 'nonce', 'boot')} handback="
            f"{cb.pick(h, 'held', 'owed', 'captures', 'returns', 'refused_report', 'refused_now', 'diorama_seen')}")


def _stays(lines) -> list:
    return [ln for ln in lines if STAY in ln and STAY_TAIL in ln]


def _handed(lines) -> list:
    return [ln for ln in lines if HANDED in ln]


# ------------------------------------------------------------------------------------------------- acting
def _bench_guard(st, args) -> str:
    """The call-site probe: why `bench <args>` must NOT be sent to this engine ('' = it may be)."""
    op = str(args[0]).strip().lower() if args else ""
    if op == "boot" and not cb.has(st, BOOT_PROBE):
        return (f"not sent: `bench boot` needs `{BOOT_PROBE}` (memoria-patch s114) -- an engine before it reads it as "
                f"`bench 1` (the field-gate bench ON)")
    if op in ("lapse", "handback") and not cb.has(st, LAPSE_PROBE):
        return (f"not sent: `bench {op}` needs `{LAPSE_PROBE}` (memoria-patch s110) -- an engine before it reads it as "
                f"`bench 1` (the field-gate bench ON)")
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


def _start(g, label: str) -> tuple:
    try:
        g.start_battle(cb.SCENE)
    except HarnessError as err:
        return None, f"`battle {cb.SCENE}` ({label}) did not start: {str(err)[:200]}"
    st = cb.poll(g, lambda s: s.commands_enabled, INTRO_S, f"{label}'s command phase")
    return st, ("" if st is not None else f"{label} never reached its command phase")


def _finish(g) -> None:
    """Fight the battle out and get back to the field (whatever leg ended where). The guest's slot is left owned (a lapse
    ended, `bench boot live`) so nothing the bench set holds a window open."""
    st = g.state
    if _lapse(st).get("active"):
        _bench(g, "lapse", "end")
    _bench(g, "boot", "live")
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


def _prep(g, timeout: float = READY_S) -> tuple:
    """Slot 1 Ready (in turn.ready, not done, peer bit 1) with the host's window NOT on it -- any other slot the window
    opens is committed with Defend. The window ON slot 1 here is no wait-it-out: no lapse runs, so the guest's report did
    not own it (or a leg left a hold) -- (None, why) and the leg records it. (state or None, why)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = g.state
        if not st.in_battle:
            return None, f"the battle is over (result {st.battle_result_name})"
        t = cb.turn(st)
        if st.turn_slot == GUEST:
            return None, (f"the host's window holds slot 1 with no lapse running -- the guest's report did not own it, or "
                          f"an earlier leg left the hold ({_brief(st)})")
        if st.turn_slot >= 0:
            try:
                g.act("Defend", slot=st.turn_slot)
            except HarnessError as err:
                g.note(f"prep: Defend for slot {st.turn_slot} refused ({str(err)[:120]})")
                g.wait_frames(10)
            continue
        if GUEST in (t.get("ready") or []) and GUEST not in (t.get("done") or []) and _pbit(st):
            return st, ""
        time.sleep(0.05)
    return None, f"slot 1 never stood ready with the window idle within {timeout:.0f}s ({_brief(g.state)})"


def _await_window(g, until, timeout: float) -> tuple:
    """Read every publish until ``until`` holds, committing (Defend) any OTHER slot the host's window opens meanwhile.
    (samples, the state that ended it or None)."""
    out = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        samples, hit = cb.watch(g, lambda s: until(s) or (s.turn_slot >= 0 and s.turn_slot != GUEST),
                                max(0.1, deadline - time.time()))
        out += samples
        if hit is None:
            return out, None
        if until(hit):
            return out, hit
        try:
            g.act("Defend", slot=hit.turn_slot)
        except HarnessError as err:
            g.note(f"Defend for slot {hit.turn_slot} refused ({str(err)[:120]})")
            g.wait_frames(10)
    return out, None


def _restore(g) -> None:
    """Between legs: no lapse, the guest's report LIVE, and any hold an earlier (failed) leg left handed back -- or, if it
    will not go, committed with Defend (slot 1 refills; :func:`_prep` waits for it)."""
    st = g.state
    if _lapse(st).get("active"):
        _bench(g, "lapse", "end")
    _bench(g, "boot", "live")
    if not _held(g.state):
        return
    cb.to_root(g)
    if cb.poll(g, lambda s: not _held(s), 1.5, "a left-over hold of slot 1 to be handed back") is not None:
        return
    g.note(f"restore: the host's window still holds slot 1 -- committed with Defend ({_brief(g.state)})")
    try:
        g.act("Defend", slot=GUEST)
    except HarnessError as err:
        g.note(f"restore: Defend for slot 1 refused ({str(err)[:120]})")


def _lapse_capture(g, label: str) -> tuple:
    """`_prep`, then `bench lapse hold` and the host's window capturing slot 1. (ctx or None, why)."""
    st, why = _prep(g)
    if st is None:
        return None, why
    c0 = _num(_hb(st).get("captures"))
    at = cb.mark(g)
    ok, why = _bench(g, "lapse", "hold")
    if not ok:
        return None, f"`bench lapse hold` refused: {why}"
    samples, cap = _await_window(g, _held, CAPTURE_S)
    if cap is None:
        _bench(g, "lapse", "end")
        return None, f"{label}: no capture within {CAPTURE_S:.0f} s of `bench lapse hold` ({_brief(g.state)})"
    lines = cb.wait_log(g, at, CAPTURE_STALL, 1.0)
    return {"pre": st, "c0": c0, "samples": [st] + samples, "cap": cap, "lines": lines}, ""


def _end_lapse(g, *, hold: bool) -> dict:
    """`bench lapse end` with the host's window at the command root. ``hold``: every publish for HOLD_FRAMES frames past
    lapse.end_frame (the refusal: nothing may move); else until the hand-back (<= 2 s)."""
    cb.to_root(g)
    s = g.state
    e = {"r0": _num(_hb(s).get("returns")), "rr0": _num(_hb(s).get("refused_report")), "at": cb.mark(g)}
    st0, why = _bench_st(g, "lapse", "end")
    end_f = _num(_lapse(st0 or g.state).get("end_frame"))
    f0 = end_f if end_f is not None and end_f >= 0 else cb.frame_of(st0 or g.state)
    r0 = e["r0"] if e["r0"] is not None else -10
    if st0 is None:
        samples, hit = [], None
    elif hold:
        samples, hit = cb.watch_from(g, st0, lambda x: cb.frame_of(x) >= f0 + HOLD_FRAMES, 4.0)
    else:
        samples, hit = cb.watch_from(g, st0, lambda x: _hb(x).get("returns") == r0 + 1, 2.0)
    e.update(st0=st0, why=why, f0=f0, end_f=end_f, samples=samples, hit=hit)
    return e


def _kept(g, e: dict) -> tuple:
    """The refusal's shape after `bench lapse end`: the host's window held slot 1 for HOLD_FRAMES frames, returns flat,
    owed false, no hand-back line. (ok, detail)."""
    samples, r0, f0 = e["samples"], e["r0"], e["f0"]
    moved = [(cb.frame_of(x), x.turn_slot, _hb(x).get("held"), _hb(x).get("returns")) for x in samples
             if x.turn_slot != GUEST or _hb(x).get("held") != GUEST or _hb(x).get("returns") != r0]
    span = (cb.frame_of(samples[-1]) - f0) if samples else 0
    s = g.state
    lines = cb.new(g, e["at"])
    handed = _handed(lines)
    last = _last(s)
    ok = (bool(samples) and r0 is not None and not moved and span >= HOLD_FRAMES and _hb(s).get("owed") is False
          and not handed)
    return ok, (e["why"] or f"over {span} frames from the lapse end (frame {f0}): off-hold (frame, turn.slot, held, returns) "
                            f"{moved[:4]}; owed={_hb(s).get('owed')!r}; returns {r0!r}->{_hb(s).get('returns')!r}, last="
                            f"{last}; {cb.grep(handed, 'handed BACK', limit=240)}; {_brief(s)}")


def _refused(g, e: dict, op: str, *, line_due: bool) -> tuple:
    """The refusal's s118 observables: refused_now, refused_report +1, diorama_seen, and the once-per-own-battle line --
    ONE naming the report when ``line_due`` (this battle's first refusal), none otherwise. (ok, detail, state)."""
    lines = cb.wait_log(g, e["at"], STAY, 1.0) if line_due else cb.new(g, e["at"])
    stays = _stays(lines)
    s = g.state
    h = _hb(s)
    rr0 = e["rr0"]
    line_ok = (len(stays) == 1 and PHRASE[op] in stays[0]) if line_due else not stays
    ok = (h.get("refused_now") is True and rr0 is not None and h.get("refused_report") == rr0 + 1
          and h.get("diorama_seen") is True and line_ok)
    return ok, (f"refused_now={h.get('refused_now', 'ABSENT')!r} refused_report {rr0!r}->"
                f"{h.get('refused_report', 'ABSENT')!r} diorama_seen={h.get('diorama_seen', 'ABSENT')!r}; 'its slots stay' "
                f"lines {len(stays)} (due {1 if line_due else 0}): {cb.grep(stays, STAY, limit=260)}"), s


def _handed_at(g, e: dict) -> tuple:
    """A hand-back right at the lapse end (N, T): returns +1, why 'handed back', slot 1, last.frame - lapse.end_frame in
    0..3, ONE 'sat at the command root' line. (ok, detail)."""
    s = e["hit"] or g.state
    last, lapse, r0 = _last(s), _lapse(s), e["r0"]
    lines = cb.wait_log(g, e["at"], HANDED, 1.0)
    roots = [ln for ln in _handed(lines) if AT_ROOT in ln and "returns=" in ln]
    lf, ef = _num(last.get("frame")), _num(lapse.get("end_frame"))
    ok = (e["hit"] is not None and r0 is not None and _hb(s).get("returns") == r0 + 1 and last.get("why") == "handed back"
          and last.get("slot") == GUEST and lf is not None and ef is not None and 0 <= lf - ef <= 3 and len(roots) == 1)
    return ok, (e["why"] or f"returns {r0!r}->{_hb(s).get('returns')!r} last={last} lapse.end_frame={ef!r}; root lines "
                            f"{len(roots)}: {cb.grep(_handed(lines), 'handed BACK', limit=240)}; {_brief(s)}")


def _live_back(g, led: cb.Ledger, cid: str) -> None:
    """`bench boot live` with the host's window holding slot 1 at the root -> ONE hand-back at the root, judged as ``cid``.
    Not reached (red) when the window no longer holds slot 1 -- on s117 the hand-back already fired at the lapse end."""
    st = g.state
    if not _held(st):
        led.check(cid, False, f"not reached: the host's window does not hold slot 1 (a pre-s118 host hands it back on "
                              f"any frame, so it is gone before the lever) -- {_brief(st)}")
        _bench(g, "boot", "live")
        return
    cb.to_root(g)
    r0 = _num(_hb(g.state).get("returns"))
    at = cb.mark(g)
    f_pre = cb.frame_of(g.state)
    st0, why = _bench_st(g, "boot", "live")
    want = (r0 if r0 is not None else -10) + 1
    samples, hit = cb.watch_from(g, st0, lambda x: _hb(x).get("returns") == want and x.turn_slot != GUEST,
                                 HANDBACK_S) if st0 is not None else ([], None)
    s = hit or g.state
    last = _last(s)
    lines = cb.wait_log(g, at, HANDED, 1.0)
    roots = [ln for ln in _handed(lines) if AT_ROOT in ln]
    t = cb.turn(s)
    lf = _num(last.get("frame"))
    ok = (hit is not None and last.get("why") == "handed back" and last.get("slot") == GUEST and lf is not None
          and lf >= f_pre and len(_handed(lines)) == 1 and len(roots) == 1 and GUEST in (t.get("ready") or [])
          and GUEST not in (t.get("done") or []) and _hb(s).get("held") == -1 and _hb(s).get("refused_now") is False)
    led.check(cid, ok, why or f"returns {r0!r}->{_hb(s).get('returns')!r}; last={last} (lever at frame >= {f_pre}); "
                              f"'handed BACK' lines {len(_handed(lines))}, at the root {len(roots)}; {_brief(s)}")


# ------------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _catalog(calibrate), finals=("S18-CAL",))
    ctx = {"probe": False}
    try:
        _run(g, led, field, ctx)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'handback-live')}")
        led.close()                                        # every leg check is recorded before the judge reads them
        cb.release(g)                                      # `reset`: the role, `bench boot`, a lapse, the latch
        if calibrate:
            led.judge_calibration("S18-CAL", () if ctx["probe"] else OLD_PREDICTED)
        led.close(final=True)


def _run(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    ok, why = cb.setup(g, field, label="R3 s118: the hand-back needs a live guest, solo"
                                       + (" -- CALIBRATION" if cb.CALIBRATE else ""))
    led.check("S18-S0", ok, why)
    st = g.state
    have = ctx["probe"] = cb.has(st, PROBE)
    led.check("S18-P0", have, f"netsync.battle.host.handback keys: {sorted(_hb(st))}" if cb.has(st, LAPSE_PROBE) else
              "no `netsync.battle.host.handback` at all (a pre-s110 engine)")
    levers = cb.has(st, LAPSE_PROBE) and cb.has(st, BOOT_PROBE)
    led.check("S18-P2", levers, f"handback {'present' if cb.has(st, LAPSE_PROBE) else 'ABSENT'}, start_hold "
                                f"{'present' if cb.has(st, BOOT_PROBE) else 'ABSENT'}")
    g.note(f"probe stage: {cb.stage_note(st)}; s118 `refused_report` {'present' if have else 'ABSENT'}"
           + ("" if have else " -- every leg still runs: this engine's hand-back on any frame is the calibration red"))
    _leg_proof(g, led)
    ok, why = cb.try_ns(g, "guestslots", 2)
    led.check("S18-P1", ok, why or "accepted")
    if not ok:
        led.close(f"`netsync guestslots` refused -- {why}")
        return
    try:
        g.state_every(1)
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]}) -- frame windows read at the default cadence")
    if not levers:
        led.close(f"`{LAPSE_PROBE}` or `{BOOT_PROBE}` is absent: an engine before s110/s114 (the probe fails closed; "
                  f"`bench lapse` / `bench boot` were never sent)")
        return
    # ---- battle 1: NONE from the start (the latch down), then DECLINED, then NONE after the latch
    ok, why = _bench(g, "boot", "none")
    if not ok:
        led.close(f"`bench boot none` refused: {why}")
        return
    at1 = cb.mark(g)
    st, why = _start(g, "battle 1")
    if st is None:
        led.close(why)
        return
    slots = cb.player_slots(st)
    led.check("S18-PRE", GUEST in slots, f"party slots {slots}")
    if GUEST not in slots:
        led.close("no party member in slot 1 (S18-PRE)")
        _finish(g)
        return
    _leg_n(g, led, at1)
    _restore(g)
    _leg_d(g, led)
    _restore(g)
    _leg_l(g, led, at1)
    _finish(g)
    # ---- battle 2: LIVE from the start; BUSY, BOOTING, STALE
    ok, why = _bench(g, "boot", "live")
    at2 = cb.mark(g)
    st, why = _start(g, "battle 2") if ok else (None, f"`bench boot live` refused: {why}")
    if st is None:
        led.unreached(BATTLE2, why)
        _finish(g)
        return
    _leg_b(g, led, at2)
    _restore(g)
    _leg_t(g, led)
    _restore(g)
    _leg_s(g, led, at2)
    _finish(g)


# ------------------------------------------------------------------------------------------------- PROOF
def _leg_proof(g, led: cb.Ledger) -> None:
    """The selftest proof block logs once per process, on the first selftest tick on a field (setup gives it one)."""
    proof = cb.poll(g, lambda s: cb.count(cb.log_lines(g), PROOF) >= 1, 8.0, "the selftest proof block's control line")
    lines = [ln for ln in cb.log_lines(g) if PROOF in ln]
    last = lines[-1] if lines else ""
    failed = [ln for ln in lines if "battle control selftest: FAIL" in ln]
    led.check("S18-PROOF", proof is not None and PROOF_OK in last and not failed,
              (last.split("|", 2)[-1].strip()[-300:] if last else
               "no 'battle control selftest' line (an engine before s114 has no ControlSelfTest)")
              + (f"; FAIL lines: {len(failed)}" if failed else ""))


# ------------------------------------------------------------------------------------------------- battle 1
def _leg_n(g, led: cb.Ledger, at_battle: int) -> None:
    g.note("N: `bench boot none` from the start -- a guest with no diorama path keeps its slot (the panel-only exception)")
    c, why = _lapse_capture(g, "N")
    if c is None:
        led.unreached(("S18-N1", "S18-N2"), why)
        return
    cap, c0 = c["cap"], c["c0"]
    rr0 = _num(_hb(c["pre"]).get("refused_report"))
    e = _end_lapse(g, hold=False)
    ok_h, det_h = _handed_at(g, e)
    stall = [ln for ln in c["lines"] if CAPTURE_STALL in ln and "ms (a stall)" in ln]
    led.check("S18-N1", ok_h and c0 is not None and _hb(cap).get("captures") == c0 + 1 and _hb(cap).get("owed") is False
              and len(stall) == 1,
              f"capture {c0!r}->{_hb(cap).get('captures')!r} owed={_hb(cap).get('owed')!r}, stall lines {len(stall)}; "
              f"{det_h}")
    seq = c["samples"] + e["samples"] + [g.state]
    bad = [(cb.frame_of(x), _hb(x).get("diorama_seen", "ABSENT"), _hb(x).get("refused_now", "ABSENT")) for x in seq
           if _hb(x).get("diorama_seen") is not False or _hb(x).get("refused_now") is not False]
    s = g.state
    stays = _stays(cb.new(g, at_battle))
    led.check("S18-N2", not bad and rr0 is not None and _hb(s).get("refused_report") == rr0 and not stays,
              f"{len(seq)} publish(es); off (frame, diorama_seen, refused_now) {bad[:4]}; refused_report "
              f"{rr0!r}->{_hb(s).get('refused_report', 'ABSENT')!r}; 'its slots stay' lines {len(stays)}")


def _leg_d(g, led: cb.Ledger) -> None:
    g.note("D: the sitting-A shape -- the guest's diorama was LIVE, a stall, then it comes back reporting DECLINED: the "
           "host keeps slot 1 until a LIVE report returns")
    c, why = _lapse_capture(g, "D")
    if c is None:
        led.unreached(("S18-D1", "S18-D2", "S18-D3"), why)
        return
    ok, why = _bench(g, "boot", "declined")
    if not ok:
        led.unreached(("S18-D1", "S18-D2", "S18-D3"), f"`bench boot declined` refused: {why}")
        _bench(g, "lapse", "end")
        return
    e = _end_lapse(g, hold=True)
    ok, det = _kept(g, e)
    led.check("S18-D1", ok, det)
    ok, det, s = _refused(g, e, "declined", line_due=True)
    led.check("S18-D2", ok and _wait_menu(s) == 0, f"{det}; host.wait.menu={_wait_menu(s)!r} (0 here under either rule: G6 "
                                                   f"withholds the held slot's Ready bit -- L1 reads the refusal's shut byte)")
    _live_back(g, led, "S18-D3")


def _leg_l(g, led: cb.Ledger, at_battle: int) -> None:
    g.note("L: NONE after the latch -- the guest reported a diorama of this battle, now NONE: the host takes slot 1 with "
           "the lane still live, the capture naming the report")
    st, why = _prep(g)
    if st is None:
        led.unreached(("S18-L1", "S18-L2"), why)
        return
    h0 = _hb(st)
    c0, rr0 = _num(h0.get("captures")), _num(h0.get("refused_report"))
    spent = bool(_stays(cb.new(g, at_battle)))
    at = cb.mark(g)
    ok, why = _bench(g, "boot", "none")
    if not ok:
        led.unreached(("S18-L1", "S18-L2"), f"`bench boot none` refused: {why}")
        return
    samples, cap = _await_window(g, _held, CAPTURE_S)
    lines = cb.wait_log(g, at, CAPTURE_REPORT, 1.0)
    named = [ln for ln in lines if CAPTURE_REPORT in ln and PHRASE["none"] in ln]
    stalls = [ln for ln in lines if CAPTURE_STALL in ln]
    stays = _stays(lines)
    # [ff9mapkit netsync R3 s118] byte 1 reads shut from the first publish that shows the NONE parsed (start_hold.guest.boot
    # 0 -- ParseControl stores the report and the shut byte in the one call) up to the capture: slot 1 stands Ready and
    # unheld there, so the loopback guest's own byte is 2 (the root) and only the refusal shuts it (D2's window cannot
    # tell the rules apart: G6 already zeroes the guest's byte while the host's window holds the slot)
    parsed = [x for x in samples if _shg(x).get("boot") == BOOT_NONE and not _held(x)]
    opened = [(cb.frame_of(x), _wait_menu(x)) for x in parsed if _wait_menu(x) != 0]
    s = cap or g.state
    h = _hb(s)
    # the refusal's own keys read after the capture line landed: the episode is counted on its first refused frame with the
    # command phase open, which may be any tick up to the capture
    r = _hb(g.state)
    line_ok = not stays if spent else (len(stays) == 1 and PHRASE["none"] in stays[0])
    led.check("S18-L1", cap is not None and c0 is not None and h.get("captures") == c0 + 1 and h.get("owed") is False
              and r.get("refused_now") is True and rr0 is not None and r.get("refused_report") == rr0 + 1
              and r.get("diorama_seen") is True and len(named) == 1 and not stalls and line_ok and parsed and not opened,
              (f"captured: {cap is not None} within {CAPTURE_S:.0f} s of `bench boot none`; captures {c0!r}->"
               f"{h.get('captures')!r}; refused_report {rr0!r}->{r.get('refused_report', 'ABSENT')!r} refused_now="
               f"{r.get('refused_now', 'ABSENT')!r} diorama_seen={r.get('diorama_seen', 'ABSENT')!r}; byte 1 over "
               f"{len(parsed)} publish(es) from the parsed NONE to the capture, not shut (frame, wait.menu) {opened[:4]}; "
               f"capture lines naming the NONE {len(named)}, stall capture lines {len(stalls)}; 'its slots stay' lines "
               f"{len(stays)} (due {0 if spent else 1}); {cb.grep(lines, 'hand-back', limit=300)}; {_brief(s)}"))
    _live_back(g, led, "S18-L2")


# ------------------------------------------------------------------------------------------------- battle 2
def _leg_keep(g, led: cb.Ledger, op: str, cids: tuple, at_battle: int) -> None:
    """B / S: lapse hold -> capture, `bench boot <op>`, `bench lapse end` -> the host keeps slot 1 (cids[0]), then `bench
    boot live` hands it back at the root (cids[1])."""
    c, why = _lapse_capture(g, op)
    if c is None:
        led.unreached(cids, why)
        return
    spent = bool(_stays(cb.new(g, at_battle)))
    ok, why = _bench(g, "boot", op)
    if not ok:
        led.unreached(cids, f"`bench boot {op}` refused: {why}")
        _bench(g, "lapse", "end")
        return
    e = _end_lapse(g, hold=True)
    ok_k, det_k = _kept(g, e)
    ok_r, det_r, s = _refused(g, e, op, line_due=not spent)
    wire_ok, wire = True, ""
    if op == "stale":
        nonce = _num(_sub(cb.host(s), "start_hold").get("nonce"))
        want = (nonce - 1) & 0xFF if nonce is not None and nonce >= 0 else None
        wire_ok = (want is not None and _ctl(s).get("nonce") == want and _ctl(s).get("boot") == BOOT_LIVE
                   and _shg(s).get("nonce") == want and _shg(s).get("boot") == BOOT_LIVE)
        wire = (f"; the stale LIVE (want nonce {want!r}, boot 2): ctl {cb.pick(_ctl(s), 'nonce', 'boot')} parsed "
                f"{cb.pick(_shg(s), 'nonce', 'boot')}")
    led.check(cids[0], ok_k and ok_r and wire_ok, f"{det_k} || {det_r}{wire}")
    _live_back(g, led, cids[1])


def _leg_b(g, led: cb.Ledger, at_battle: int) -> None:
    g.note("B: the guest comes back from a stall reporting BUSY (its main menu) -- the host keeps slot 1")
    _leg_keep(g, led, "busy", ("S18-B1", "S18-B2"), at_battle)


def _leg_t(g, led: cb.Ledger) -> None:
    g.note("T: the guest comes back reporting BOOTING -- it still owns (a normal start is unchanged): handed back at once")
    c, why = _lapse_capture(g, "T")
    if c is None:
        led.unreached(("S18-T1",), why)
        return
    ok, why = _bench(g, "boot", "booting")
    if not ok:
        led.unreached(("S18-T1",), f"`bench boot booting` refused: {why}")
        _bench(g, "lapse", "end")
        return
    e = _end_lapse(g, hold=False)
    ok, det = _handed_at(g, e)
    led.check("S18-T1", ok, det)


def _leg_s(g, led: cb.Ledger, at_battle: int) -> None:
    g.note("S: the guest comes back with a LIVE naming the PREVIOUS battle -- another battle's word owns nothing here")
    _leg_keep(g, led, "stale", ("S18-S1", "S18-S2"), at_battle)
