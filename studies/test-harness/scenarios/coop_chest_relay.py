"""s160 -- THE CHEST RELAY (studies/field-coop/CHEST-RELAY.md, memoria-patches s160), the SOLO bench: the guest half.
[ff9mapkit netsync s160]

THE DEFECT. A stock chest opens in its tag-2 `_Range` body, which polls Confirm|Special with control on. That press never reached the
talk relay or the key relay, so a following guest's copy never opened the chest: no lid, no "Received Item!" box (two-PC 2026-10-28,
301 and 352).

THE FIX (s160). The host stamps a chest start at its chest's own read and rides it in state-lane section 9. The guest's copy arms a
ONE-SHOT serve for that chest, Requests its tag-2 body (or finds it already queued by the stock range request, standing in push range),
and NetSyncField.FilterScriptButtons hands the host's press to that chest's next control-on read. The chest's own script then turns and
kneels the guest's character, opens the lid, grants the item and opens window 7.

THE BENCH. One instance root, the selftest role, the field-gate bench on. `netsync chest <uid>` fabricates a section-9 start through
the real codec onto the accept path (the host's stamp is the duo's: coop_chest_relay_duo.py). Field 200 (Prima Vista/Hallway,
test2_57.txt), ChestA = entry 9 = uid 9: model 75 at (576, 80), push radius 346, the opened flag VARL_GenBool_7244, item 112 (the
Leather Hat), window 7 text 70; the player's function 19 turns and kneels (2606 Hiza_1, stand 2605), 20 stands (2590 Hiza_3, then 200).
Arrival (the research recipe, CHEST-RELAY.md "Bench plan"): scenario 2000, entrance 0, flag 2471 = 1 (no Nero walking through), the
env-sound bytes 13/14 zeroed (THE ENV-SLOT LAW), flag 7244 cleared before every opening leg (ChestA_Init reads it for its pose).

  K0      provenance; newgame; noencounter; the arrival; the preflight (uid 9 is a model-75 chest at its spot, no Nero/Blank uids 4/6/17);
          `netsync selftest 1`; `netsync bench 1`; `netsync.chest` present (key PRESENCE is the capability).
  K1      "chest relay selftest: OK (N rows, M mutants caught)" within 20 s and `netsync.chest.selftest` "ok".
  C5      `chest 10` (Zidane, model 98) and `chest 99` (no object): declined +2, each with its line, nothing opens.
  C1      FAR (the spawn, 672 u away): `chest 9` -> accepted +1, served +1 (one "served" line), my control falls, my face turns to the
          chest (within FACE_TOL of the computed byte), my position holds (MOVE_EPS), flag 7244 rises, a window opens naming the item.
          The accept-to-window time is logged (the press-to-window path the design measured as 1.3-1.9 s).
  C3      ...then my Confirm closes it: control back within LAND_S, the stand clip seen (2590 or idle 200), my face held.
  C6      `chest 9` on an OPEN chest (posed open by flag 7244 at its own arrival, so no lever can couple it to C1): accepted +1, then
          expired +1 with the "not served" line inside ChestServeMs + slack; nothing opens, 7244 stays set.
  C7      FAR, chest closed again, MY CONTROL OFF (`control 0`): one "deferred" line, nothing accepted; control back inside the 4 s TTL ->
          the C1 outcomes (accepted, served, a window).
  C4      NEAR (290, 80; inside the push radius, outside the walking stop), chest closed, NO start: my own Confirm opens nothing (no
          window, 7244 clear, control on) -- F1's free-walk mask still holds.
  C2      NEAR, `chest 9`: the "already queued by the stock range request" accept line (I stand in push range), served +1, a window,
          7244 set, my face turned from where I left it toward the chest.
  K-R     `reset` releases the levers (their line when the calibration held one); re-read with the role: serve_off / request_off false.

THE CALIBRATION (COOP_CALIBRATE=serve | request; `1` = serve). The lever is pulled right after K1 and HELD:
  serve    `netsync chest serve off` -- the body runs, its read stays masked: C1, C2, C3, C7 red (no serve, no window); every other row
           green (C6's expiry names the lever).
  request  `netsync chest request off` -- no forced Request: C1, C3, C7 red (FAR: nothing queues the body); C2 GREEN (NEAR: the stock
           range request queues it). That split is the proof the in-range path and the forced Request are each load-bearing.
K-CAL (judged last) is green only when exactly the predicted rows went red.

NOT PROVEN HERE (the duo, coop_chest_relay_duo.py, and the two-PC session): the host's stamp at its press, section 9 on a real lane,
the same-nonce dedup (the verb mints a fresh nonce each call), the version gate against an s159 guest, the dialogue lock's catch-up of
a live host's close, option C, the step-out claim, the mirror gate (the bench path is exempt by design), a JP-language pair.

    py tools/play.py studies/test-harness/scenarios/coop_chest_relay.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=serve py tools/play.py studies/test-harness/scenarios/coop_chest_relay.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=request py tools/play.py studies/test-harness/scenarios/coop_chest_relay.py --instance C:\\gd\\ff9-inst\\host
"""
from __future__ import annotations

import math
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import coop_guest_traversal as gt                          # noqa: E402 - pos / control / field_of / dist_xz

HarnessError = cb.HarnessError

KEY = "netsync.chest"
PROBE = KEY + ".served"                  # key PRESENCE is the capability (protocol 5, additive)

FIELD = 200
SCENARIO = 2000
ENTRANCE = 0
CHEST_UID = 9
CHEST_MODEL = 75
CHEST_XZ = (576.0, 80.0)
NOT_CHEST_UID = 10                       # the player (Zidane, model 98)
NO_SUCH_UID = 99
FLAG_OPENED = 7244
FLAG_NO_NERO = 2471
SPAWN = (-90.0, 171.0)
NEAR = (290.0, 80.0)
RANGE_R = 346.0                          # 4*40 + 4*24 + 30 + 60 (WalkMesh.Collision push mode)
STOP_R = 256.0                           # the walking collision stop
ITEM_WORDS = ("Leather Hat",)
STAND_CLIPS = (2590, 200)
FORBIDDEN_UIDS = (4, 6, 17)              # the scenario-2260 Blanks and Nero (flag 2471 = 0)

SELFTEST_S = 20.0
OPEN_S = 8.0                             # accept -> window (1.3-1.9 s measured on paper; generous)
LAND_S = 6.0
SERVE_MS = 2000                          # NetSyncClient.ChestServeMs
EXPIRE_S = SERVE_MS / 1000.0 + 1.5
TTL_S = 4.0                              # NetSyncClient.TalkRelayTtlMs
FACE_TOL = 6                             # face bytes (256 to a turn)
MOVE_EPS = 2.0
NEAR_TOL = 20.0

SELFTEST_RX = re.compile(r"chest relay selftest: OK \((\d+) rows, (\d+) mutants caught\)")
LINE_ACCEPT = "[NetSync] chest relay: opening chest {u} on my copy of field {f}"
LINE_QUEUED = "its body is already queued by the stock range request"
LINE_SERVED = "[NetSync] chest relay: served the host's press to chest {u} on my copy"
LINE_NOT_SERVED = "[NetSync] chest relay: chest start uid {u} not served ("
LINE_DEFERRED = "[NetSync] chest relay: start {n} (chest {u}) deferred -- my copy of a talk/scene still holds control"
LINE_NOT_CHEST = "[NetSync] chest relay: obj {u} is not a stock chest on my copy"
LINE_NO_OBJ = "[NetSync] chest relay: no object with uid {u} on this field -- ignored"
LINE_LEVER_SERVE = "[NetSync] harness: chest serve OFF -- CALIBRATION"
LINE_LEVER_REQUEST = "[NetSync] harness: chest request OFF -- CALIBRATION"
LINE_RELEASED = "[NetSync] harness: chest levers released (serve + request on)"

_CAL = os.environ.get("COOP_CALIBRATE", "").strip().lower()
CAL_MODE = None if _CAL in ("", "0") else ("request" if _CAL == "request" else "serve")
PREDICTED = {"serve": ("C1", "C2", "C3", "C7"), "request": ("C1", "C3", "C7")}

CATALOG = {
    "K0": "arrival on 200 at scenario 2000 (control, at the spawn), the chest preflight, the selftest role + field-gate bench, "
          "`netsync.chest` present",
    "K1": "the proof line 'chest relay selftest: OK (N rows, M mutants caught)' and netsync.chest.selftest 'ok'",
    "C5": "`chest 10` / `chest 99` declined (+2, each its own line), nothing opens",
    "C1": "FAR: accepted, served, control falls, face turns to the chest, position held, 7244 set, a window names the item",
    "C3": "the window closed by my Confirm: control back, the stand clip, face held",
    "C6": "a start on the OPEN chest: accepted, then expired with 'not served', nothing opens",
    "C7": "FAR with my control off: one 'deferred' line, then (control back inside the TTL) accepted, served, a window",
    "C4": "NEAR, no start: my own Confirm opens nothing (F1's mask)",
    "C2": "NEAR: accepted on the stock range request's queued body, served, a window, 7244 set, face turned to the chest",
    "K-R": "`reset` releases the chest levers; re-read with the role: serve_off / request_off false",
}
FINALS = ("K-R",)


def catalog(mode: str | None) -> dict:
    cat = dict(CATALOG)
    if mode:
        cat["K-CAL"] = f"the {mode} lever calibration: exactly " + ", ".join(PREDICTED[mode]) + " red"
    return cat


# ================================================================================================ pure reads (fixtures in the
# engine's types: the published document as a dict, or a State whose .raw is one)
def chest(x) -> dict:
    return cb.path(x, KEY) or {}


def flag(x, bit: int):
    return (cb.raw(x).get("flags") or {}).get(str(bit))


def face(x):
    v = (cb.raw(x).get("player") or {}).get("face")
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def anim(x):
    v = (cb.raw(x).get("player") or {}).get("anim")
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def dialog_open(x) -> bool:
    return bool((cb.raw(x).get("dialog") or {}).get("open", False))


def dialog_text(x) -> str:
    return " ".join(t for t in ((cb.raw(x).get("dialog") or {}).get("texts") or []) if isinstance(t, str))


def counters(x) -> dict:
    c = chest(x)
    return {k: int(c.get(k, 0) or 0) for k in ("accepted", "served", "expired", "declined")}


def delta(a: dict, b: dict) -> dict:
    return {k: b.get(k, 0) - a.get(k, 0) for k in ("accepted", "served", "expired", "declined")}


def face_toward(player_xz, target_xz) -> int:
    """The face byte a TimedTurn toward the target lands on (the research's formula: 256 to a turn, measured from -z)."""
    dx = target_xz[0] - player_xz[0]
    dz = target_xz[1] - player_xz[1]
    return int(round((math.degrees(math.atan2(-dx, -dz)) % 360.0) * 256.0 / 360.0)) % 256


def face_diff(a: int, b: int) -> int:
    d = abs(int(a) - int(b)) % 256
    return min(d, 256 - d)


def selftest_verdict(lines, x) -> tuple:
    hits = [ln for ln in lines if "chest relay selftest:" in ln]
    m = next((SELFTEST_RX.search(ln) for ln in hits if SELFTEST_RX.search(ln)), None)
    pub = chest(x).get("selftest")
    ok = m is not None and int(m.group(1)) > 0 and int(m.group(2)) > 0 and pub == "ok"
    return ok, f"line {cb.grep(hits, 'chest relay selftest') or 'none'}; netsync.chest.selftest {pub!r}"


def judge_open(samples, before: dict, *, start_xz, want_face: int, queued: bool, lines) -> tuple:
    """C1 / C2 / C7's open: every claim is an OUTCOME read off the published samples from the inject on."""
    if not samples:
        return False, "no samples"
    last = samples[-1]
    d = delta(before, counters(last))
    ctl_fell = any(not gt.control(s) for s in samples)
    opened = next((s for s in samples if dialog_open(s)), None)
    faces = [face(s) for s in samples if face(s) is not None]
    turned = any(face_diff(f, want_face) <= FACE_TOL for f in faces)
    ps = [gt.pos(s) for s in samples if gt.pos(s) is not None]
    moved = max((gt.dist_xz(p, start_xz) for p in ps), default=math.inf)
    flagged = any(flag(s, FLAG_OPENED) is True for s in samples)
    named = opened is not None and any(w in dialog_text(opened) for w in ITEM_WORDS)
    queued_ok = (cb.count(lines, LINE_QUEUED) >= 1) if queued else True
    ok = (d["accepted"] == 1 and d["served"] == 1 and ctl_fell and turned and moved <= MOVE_EPS and flagged and opened is not None
          and named and queued_ok)
    return ok, (f"deltas {d}; control fell {ctl_fell}; faces seen {sorted(set(faces))[:12]} (want {want_face} +-{FACE_TOL}); moved "
                f"{moved:.1f} u; 7244 {flagged}; window {'open: ' + dialog_text(opened)[:80] if opened else 'NEVER'}; "
                f"queued line {queued_ok if queued else 'n/a'}")


def judge_close(samples, *, want_face: int) -> tuple:
    if not samples:
        return False, "no samples"
    back = next((i for i, s in enumerate(samples) if gt.control(s) and not dialog_open(s)), None)
    clips = {anim(s) for s in samples if anim(s) is not None}
    stood = bool(clips & set(STAND_CLIPS))
    held = back is not None and face(samples[back]) is not None and face_diff(face(samples[back]), want_face) <= FACE_TOL
    ok = back is not None and stood and held
    return ok, (f"control back {'at sample ' + str(back) if back is not None else 'NEVER'}; clips {sorted(clips)[:10]} (want one of "
                f"{STAND_CLIPS}); face held {held}")


def judge_nothing_opens(samples, before: dict, *, want: dict, flag_was) -> tuple:
    if not samples:
        return False, "no samples"
    d = delta(before, counters(samples[-1]))
    opened = any(dialog_open(s) for s in samples)
    flag_now = flag(samples[-1], FLAG_OPENED)
    ok = all(d[k] == v for k, v in want.items()) and not opened and flag_now == flag_was
    return ok, f"deltas {d} (want {want}); a window opened {opened}; 7244 {flag_was!r} -> {flag_now!r}"


# ================================================================================================ the run
class Ctx:
    def __init__(self, mode):
        self.mode = mode
        self.accept_to_window: list = []


def _ns(g, *args) -> tuple:
    return cb.try_ns(g, "chest", *args)


def _arrive(g, *, opened: bool = False) -> tuple:
    """warp 200 (scenario 2000, entrance 0) with the chest's opened flag set as asked BEFORE the load (ChestA_Init poses from it)."""
    try:
        g.poke(13, 0)
        g.poke(14, 0)
        g.flag(FLAG_NO_NERO, True)
        g.flag(FLAG_OPENED, opened)
    except (HarnessError, AttributeError) as err:
        return False, f"the arrival pokes were refused: {str(err)[:160]}"
    ok, why = cb.try_ns(g, "bench", 0)
    try:
        g.warp(FIELD, entrance=ENTRANCE, scenario=SCENARIO)
    except HarnessError as err:
        return False, f"warp {FIELD} failed: {str(err)[:200]}"
    st = cb.poll(g, lambda s: gt.field_of(s) == FIELD and gt.control(s)
                 and gt.dist_xz(gt.pos(s), (SPAWN[0], 0.0, SPAWN[1])) <= 40.0, 15.0, "the field-200 spawn with control")
    ok2, why2 = cb.try_ns(g, "bench", 1)
    if st is None:
        st = g.state
        return False, f"no arrival: field {gt.field_of(st)} control {gt.control(st)} at {gt.pos(st)}"
    if not ok2:
        return False, f"`netsync bench 1` refused: {why2}"
    return True, f"at {gt.pos(st)}"


def _preflight(st) -> tuple:
    objs = cb.raw(st).get("objects") or []
    ch = next((o for o in objs if o.get("uid") == CHEST_UID), None)
    bad = [o.get("uid") for o in objs if o.get("uid") in FORBIDDEN_UIDS]
    ok = (ch is not None and ch.get("model") == CHEST_MODEL and gt.dist_xz((ch.get("x"), ch.get("z")), CHEST_XZ) <= 5.0
          and not bad and flag(st, FLAG_OPENED) is False and flag(st, FLAG_NO_NERO) is True)
    return ok, (f"uid {CHEST_UID}: {({k: ch.get(k) for k in ('model', 'x', 'z', 'range_r', 'r')} if ch else 'ABSENT')}; forbidden "
                f"present {bad}; 7244 {flag(st, FLAG_OPENED)!r} 2471 {flag(st, FLAG_NO_NERO)!r}")


def _inject_and_watch(g, args, until, timeout: float):
    at = cb.mark(g)
    before = counters(g.state)
    ok, why = _ns(g, *args)
    if not ok:
        return None, before, [], at, why
    samples, _ = cb.watch(g, until, timeout)
    return samples, before, cb.new(g, at), at, ""


def _close_window(g, timeout: float):
    samples = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = g.state
        if dialog_open(st):
            g.press("confirm", 2)
        s, _ = cb.watch(g, lambda s: gt.control(s) and not dialog_open(s), 0.6)
        samples += s
        if samples and gt.control(samples[-1]) and not dialog_open(samples[-1]):
            samples += cb.hold_for(g, 0.6)
            break
    return samples


def run(g, field: int | None = None):
    mode = CAL_MODE
    ctx = Ctx(mode)
    led = cb.Ledger(g, catalog(mode), finals=FINALS, width=1400)
    at0 = cb.mark(g)
    try:
        if not _k0(g, led):
            led.close("K0 failed: no bench")
            return
        _k1(g, led, at0)
        if mode:
            ok, why = _ns(g, mode, "off")
            g.note(f"CALIBRATION: `netsync chest {mode} off` {'held' if ok else 'REFUSED: ' + why}")
        _c5(g, led)
        _c1_c3(g, ctx, led)
        _c6(g, led)
        _c7(g, ctx, led)
        _c4_c2(g, ctx, led)
    finally:
        _k_r(g, led, mode)
        if ctx.accept_to_window:
            g.note("accept -> window (s): " + ", ".join(f"{t:.2f}" for t in ctx.accept_to_window))
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'chest-relay-' + (mode or 'plain'))}")
        if mode:
            led.judge_calibration("K-CAL", PREDICTED[mode])
        led.close("the run ended before this check was reached", final=True)


def _k0(g, led) -> bool:
    cb.provenance(g)
    g.newgame()
    try:
        g.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        g.note(f"noencounter refused ({str(err)[:120]})")
    ok, why = cb.try_ns(g, "selftest", 1)
    st = cb.poll(g, lambda s: bool((s.netsync or {}).get("selftest")), 5.0, "the forced selftest role") or g.state
    if not ok or not (st.netsync or {}).get("selftest"):
        led.check("K0", False, f"`netsync selftest 1`: {why or 'role not set'}")
        return False
    try:
        g.watch(FLAG_OPENED, FLAG_NO_NERO)
    except (HarnessError, AttributeError) as err:
        g.note(f"watch refused ({str(err)[:120]}) -- the flag rows will read None")
    ok, why = _arrive(g)
    st = g.state
    pf_ok, pf_why = _preflight(st)
    has = cb.has(st, PROBE)
    led.check("K0", ok and pf_ok and has, f"{why}; preflight {pf_why}; {KEY} present {has}")
    return ok and has


def _k1(g, led, at0) -> None:
    st = cb.poll(g, lambda s: chest(s).get("selftest") is not None, SELFTEST_S, "netsync.chest.selftest") or g.state
    ok, why = selftest_verdict(cb.new(g, at0), st)
    led.check("K1", ok, why)


def _c5(g, led) -> None:
    lines_all, opened, before = [], False, counters(g.state)
    for uid in (NOT_CHEST_UID, NO_SUCH_UID):
        samples, _, lines, _, why = _inject_and_watch(g, (uid,), lambda s: False, 1.5)
        if samples is None:
            led.check("C5", False, f"`chest {uid}` refused: {why}")
            return
        lines_all += lines
        opened = opened or any(dialog_open(s) for s in samples)
    d = delta(before, counters(g.state))
    found = (cb.count(lines_all, LINE_NOT_CHEST.format(u=NOT_CHEST_UID)) == 1 and cb.count(lines_all, LINE_NO_OBJ.format(u=NO_SUCH_UID)) == 1)
    led.check("C5", d["declined"] == 2 and d["accepted"] == 0 and found and not opened,
              f"deltas {d}; lines {cb.grep(lines_all, 'chest relay:')}; a window opened {opened}")


def _c1_c3(g, ctx, led) -> None:
    st = g.state
    start = gt.pos(st)
    want = face_toward((start[0], start[2]), CHEST_XZ)
    t0 = time.time()
    samples, before, lines, _, why = _inject_and_watch(g, (CHEST_UID,), lambda s: dialog_open(s), OPEN_S)
    if samples is None:
        led.unreached(("C1", "C3"), f"`chest {CHEST_UID}` refused: {why}")
        return
    opened_at = time.time() if samples and dialog_open(samples[-1]) else None
    samples += cb.hold_for(g, 0.5)
    ok, detail = judge_open(samples, before, start_xz=start, want_face=want, queued=False, lines=lines)
    if opened_at:
        ctx.accept_to_window.append(opened_at - t0)
    led.check("C1", ok, detail + "; " + cb.grep(lines, "chest relay:"))
    after = _close_window(g, LAND_S)
    ok, detail = judge_close(after, want_face=want)
    led.check("C3", ok and not dialog_open(g.state), detail)


def _c6(g, led) -> None:
    ok, why = _arrive(g, opened=True)           # independent of C1 (which a calibration lever keeps shut)
    if not ok:
        led.check("C6", False, f"re-arrival (chest open): {why}")
        return
    st = g.state
    flag_was = flag(st, FLAG_OPENED)
    samples, before, lines, _, why = _inject_and_watch(g, (CHEST_UID,), lambda s: False, EXPIRE_S)
    if samples is None:
        led.check("C6", False, f"`chest {CHEST_UID}` refused: {why}")
        return
    ok, detail = judge_nothing_opens(samples, before, want={"accepted": 1, "served": 0, "expired": 1}, flag_was=flag_was)
    found = cb.count(lines, LINE_NOT_SERVED.format(u=CHEST_UID)) == 1
    led.check("C6", ok and found and flag_was is True, detail + f"; 'not served' line {found}: {cb.grep(lines, 'not served')}")


def _c7(g, ctx, led) -> None:
    ok, why = _arrive(g)
    if not ok:
        led.check("C7", False, f"re-arrival: {why}")
        return
    st = g.state
    start = gt.pos(st)
    want = face_toward((start[0], start[2]), CHEST_XZ)
    try:
        g.control(False)
    except (HarnessError, AttributeError) as err:
        led.check("C7", False, f"`control 0` refused: {str(err)[:200]}")
        return
    at = cb.mark(g)
    before = counters(g.state)
    okv, whyv = _ns(g, CHEST_UID)
    held = cb.hold_for(g, 1.0)
    lines_held = cb.new(g, at)
    g.control(True)
    samples, _ = cb.watch(g, lambda s: dialog_open(s), OPEN_S)
    samples += cb.hold_for(g, 0.5)
    lines = cb.new(g, at)
    deferred = sum(1 for ln in lines_held if "chest relay: start" in ln and "deferred" in ln)
    none_held = delta(before, counters(held[-1] if held else g.state))["accepted"] == 0
    ok_open, detail = judge_open(samples, before, start_xz=start, want_face=want, queued=False, lines=lines)
    led.check("C7", okv and deferred == 1 and none_held and ok_open,
              f"inject {'ok' if okv else whyv}; deferred lines while held {deferred}; nothing accepted while held {none_held}; " + detail)
    _close_window(g, LAND_S)


def _c4_c2(g, ctx, led) -> None:
    ok, why = _arrive(g)
    if not ok:
        led.unreached(("C4", "C2"), f"re-arrival: {why}")
        return
    try:
        arrived = g.walk_to(NEAR[0], NEAR[1], tolerance=NEAR_TOL, strict=False)
    except HarnessError as err:
        led.unreached(("C4", "C2"), f"walk to NEAR refused: {str(err)[:200]}")
        return
    st = g.state
    d = gt.dist_xz(gt.pos(st), (CHEST_XZ[0], 0.0, CHEST_XZ[1]))
    if not (STOP_R - 5 < d < RANGE_R):
        led.unreached(("C4", "C2"), f"NEAR not reached inside the push radius: {d:.0f} u from the chest (walk_to {arrived})")
        return
    # C4: my own Confirm, no start
    before = counters(st)
    samples = []
    for _ in range(2):
        g.press("confirm", 4)
        samples += cb.hold_for(g, 0.8)
    ok4, d4 = judge_nothing_opens(samples, before, want={"accepted": 0, "served": 0}, flag_was=False)
    led.check("C4", ok4 and all(gt.control(s) for s in samples[-3:]), d4 + f"; at {d:.0f} u")
    # C2: turn away first, so the chest's own turn is visible
    try:
        g.turn_in_place(("up",), 8)
    except (HarnessError, AttributeError, TypeError) as err:
        g.note(f"C2: the turn-away refused ({str(err)[:120]}) -- the face row still reads the turn")
    st = g.state
    start = gt.pos(st)
    want = face_toward((start[0], start[2]), CHEST_XZ)
    if face(st) is not None and face_diff(face(st), want) < 32:
        g.note(f"C2: the turn-away left the face {face(st)} within 32 of the chest's {want} -- the turn row is weak here")
    samples, before, lines, _, why = _inject_and_watch(g, (CHEST_UID,), lambda s: dialog_open(s), OPEN_S)
    if samples is None:
        led.check("C2", False, f"`chest {CHEST_UID}` refused: {why}")
        return
    samples += cb.hold_for(g, 0.5)
    ok2, detail = judge_open(samples, before, start_xz=start, want_face=want, queued=True, lines=lines)
    led.check("C2", ok2, detail + "; " + cb.grep(lines, "chest relay:"))
    _close_window(g, LAND_S)


def _k_r(g, led, mode) -> None:
    at = cb.mark(g)
    expect = (LINE_RELEASED,) if mode else ()

    def extra(st):
        c = chest(st)
        return c.get("serve_off") is False and c.get("request_off") is False, f"serve_off {c.get('serve_off')!r} request_off {c.get('request_off')!r}"

    cb.release(g, led, "K-R", expect_lines=expect, at=at, extra=extra)
