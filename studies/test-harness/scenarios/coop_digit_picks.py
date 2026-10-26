"""s154 -- THE DIGIT-PICK LAW (studies/coop-review/REVIEW.md 1.6 / appendix #33, memoria-patches s154), the SOLO bench.

THE DEFECT. The guest's digit panel (the fallback command surface: a stranded slot, GuestStockMenu=0, a guest who left its
diorama, FollowHost=0 panel-only co-op, a faulted mirror, the s145 world-map declines) drew its target pick and its item page
from the LIVE peer view / roster, and RE-DERIVED both at the keypress. A death between the draw and the press compacted every
later position, so [2] on "Goblin B" landed on the host's Zidane (friendly fire); a used-up or a stolen item slid the item page,
so [2] on "Ether" spent the host's Elixir. The host cannot catch it: a shifted mask still names a real, valid unit.

THE FIX (s154). A digit, once drawn, keeps its unit (its item) for the life of the pick: the target pick and the item page
draw and press a SNAPSHOT taken when they open; a drawn entry that is no longer valid -- KO, gone, up again on a revive pick,
used up -- is REFUSED (stock's disabled button: the buzzer, a panel note, the pick stays open, one log line per pick / digit /
verdict -- PickLogFresh), never retargeted. Two pure rules decide (NetSyncBattle.DigitTargetRule / DigitItemRule); the proof
block's "digit picks selftest: OK (22 rows)" pins them, the resolvers (each resolver row against s153's position press) and
the refusal log (the review's [2] [3] [2] [3] alternation logs twice, against the LAST-key compare that logged four times).

THE BENCH. One instance root, harness-driven, unattended. The selftest diorama (`dioboot 67 0`, Evil Forest, one Goblin) and
its BENCH FEED (`bbench start 8`: the host's lane built from the diorama's own units, guest wire slot 3 -- Steiner -- offered;
a bench host answers every forwarded frame) with `bbench knob 0` (GuestStockMenu off: the production fallback, the digit panel
serves the ready slot). The press is `bbench digit <0-9>` -- ONE keypress, taken by the panel's own read on its next serving
tick (never by the UIKeyTrigger swallow: the game sees nothing). Every leg reads what the guest COMMITTED: the bench host's
`feed.last` (its hex re-decoded here, independently of the engine's decoder), `feed.taken`, the PRE-EXISTING s113
`feed.ctl_menu` (3 = the panel below its root) and the s154 digit keys (`digit_taken`: a missing frame is never a missing
press; `digit_cands` / `digit_items`: the lists AS DRAWN; `digit_refused` / `digit_refused_why`). Items first, kills last
(KillUnit sticks: the selftest branch never reconciles), never the guest slot, never the last player (THE BENCH ORDERING LAW).

  K0      the forced selftest role.   K1  "digit picks selftest: OK (22 rows)".
  K2-pre  the panel serves wire 3 (assist_slot 3, stock_owns false, the feed live, its digit keys published) and the
          INSTRUMENT is calibrated: [1] moves the pre-existing ctl_menu 2 -> 3, [0] takes it back (digit_taken +2).
  I1      the slid item: page drawn [Potion 236 x1, Ether 238 x2, Elixir 239 x3], the host's last Potion used (`bbench roster`
          R2) with the page open -> [2] commits the drawn Ether (id 238, Self 0x08). RED marker: id 239.
  I2      the used-up item: the page drawn again, the Potion used up again -> [1] is REFUSED: taken +1, no frame for 1.5 s, the
          page open (ctl_menu 3), digit_refused +1 naming "(item 236)". RED marker: a frame (id 238).
  T1-pre  Attack (SingleAny) drew [Goblin, Zidane 0, Vivi 1, Garnet 2, Steiner 3].
  T1      the shifted target: Zidane KO'd (`endbench kill 1`) after the draw -> the drawn Vivi commits (mask 0x02). RED: 0x04.
  T2-pre  the next Attack drew [Goblin, Vivi 1, Garnet 2, Steiner 3] (the KO Zidane is not drawn).
  T2a     the fallen target: Vivi KO'd (`endbench kill 2`) after the draw -> her digit is REFUSED (no frame for 1.5 s, the
          pick open, digit_refused +1 naming "(unit 1)"). RED marker: a frame for Garnet (0x04).
  T2b     after a refusal the pick still commits: [1] -> the drawn Goblin (mask 0x10). An s154-only green leg (below).
  K-INV   the guest's own save untouched (the autosave fingerprint before == after: gil, bag, party, levels).
  K-R     `reset` releases the role, the diorama, the feed, the lever and a waiting bench digit.

THE CALIBRATION IS BY LEVER, and the README says so: NO harness input reaches the s153 binary's digit panel -- ReadDigit reads
UnityEngine.Input.GetKeyDown, and HarnessAgent hooks only HonoInputManager and the UnityXInput axes -- so on the s153 DLL every
digit leg is honestly ABSENT (`bbench digit` answers "unknown op 'digit'", the feed carries no digit keys: K2-pre and every
digit leg red "not reached: this engine has no digit input"), which is NOT a calibration. The behavioural red is s153's own
CODE: `bbench digitsnap off` (selftest only, released with the harness) runs s153's draw and press VERBATIM at the four sites
(the item page and the target pick, each drawn live and re-derived at the keypress). COOP_CALIBRATE=1 pulls it right after
K2-pre and judges K-CAL: exactly PREDICTED_S153 = {I1, I2, T1, T2a} red, each BEHAVIOURALLY. A red alone is not the
behaviour (a press never taken, a frame that never reached the bench host, an unreached leg all read red too), so each
predicted leg keeps the frame it read and K-CAL-M (the calibration catalog only, judged before K-CAL) is green only when every
one is s153's marker -- I1 a frame for the Elixir (id 239), I2 a frame for the Ether (id 238), T1 and T2a an Attack frame for
Garnet (mask 0x04); a K-CAL-M red is an unpredicted red, so K-CAL cannot pass on a red s153's code did not produce. T2b is
NOT predicted: under the lever T2a's frame was ACCEPTED and the slot's Ready bit fell, so [1] is never read -- unreached
under the lever, a consequence of T2a and no witness of the bug -- so the calibration catalog drops it (noted in the run)
and it stays an s154-only green leg. K0, K1, K2-pre, T1-pre, T2-pre, K-INV and K-R stay green under the lever.

THE PREREQS: the instance root (py tools/harness/instance.py ensure C:\\gd\\ff9-inst\\host), COOPPARTY (30604) and LOCKT2
(30602) registered (the -msgs folder), no other FF9 from that root, no controller, nobody at the keyboard (THE UNATTENDED LAW:
the press is injected inside the engine; no OS keystroke, no focus).

    py tools/play.py studies/test-harness/scenarios/coop_digit_picks.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_digit_picks.py --instance C:\\gd\\ff9-inst\\host

On the s154 DLL the plain run reads 12/12 and the calibration run reads 9/13 with K-CAL-M and K-CAL green (its four reds
predicted, each s153's marker).
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

GUEST_WIRE = 3                    # the bench feed offers wire slot 3 (Steiner, seated through COOPPARTY)
GUEST_MASK = 1 << GUEST_WIRE
POTION, ETHER, ELIXIR = 236, 238, 239
SELF = 13                         # TargetType.Self: an item pick commits in one press
TAKE_S = 4.0                      # a bench press is taken on the panel's next serving tick (past the 700 ms send cooldown)
HOLD_S = 1.5                      # a "no frame" leg holds past the cooldown and ten feed frames
KILL_FRAMES = 2                   # feed samples after a kill before the press (the lane must carry the KO; SampleMs 150)
PROBE = "netsync.battle.menu.feed.digit_taken"
LEVER_BACK = "digit-panel snapshot back ON (released with the harness)"
DISCARDED = "a waiting bench digit ["
USED_UP = "is used up since the page was drawn"
FALLEN = "is KO since the list was drawn"

#: the roster the feed's panel serves: wire slot 3's Attack (SingleAny) and a bag whose every item is a Self pick
R_ATTACK = {GUEST_WIRE: [{"menu": 0, "cmd": cb.CMD_ATTACK, "type": 0, "tinfo": 0, "abils": []}]}
R1 = cb.roster_bytes(R_ATTACK, [{"id": POTION, "count": 1, "tinfo": SELF}, {"id": ETHER, "count": 2, "tinfo": SELF},
                                {"id": ELIXIR, "count": 3, "tinfo": SELF}])
R2 = cb.roster_bytes(R_ATTACK, [{"id": ETHER, "count": 2, "tinfo": SELF}, {"id": ELIXIR, "count": 3, "tinfo": SELF}])

#: the checks that must be red on s153's CODE (under `bbench digitsnap off`), each behaviourally
PREDICTED_S153 = ("I1", "I2", "T1", "T2a")
LEGS = ("K2-pre", "I1", "I2", "T1-pre", "T1", "T2-pre", "T2a", "T2b")
GARNET = 2                        # party slot 2: where s153's re-derived list slides T1's and T2a's digit
#: s153's BEHAVIOURAL red per predicted leg (review L14): what K-CAL-M requires of the frame each leg read under the lever
S153_MARKERS = {"I1": f"a slot-3 Item frame for the Elixir (id {ELIXIR})",
                "I2": f"a slot-3 Item frame for the Ether (id {ETHER})",
                "T1": f"a slot-3 Attack frame for Garnet (mask 0x{1 << GARNET:02X})",
                "T2a": f"a slot-3 Attack frame for Garnet (mask 0x{1 << GARNET:02X})"}


def s153_marker(cid: str, c) -> bool:
    """The frame ``c`` (re-decoded, or None) is s153's behavioural red for ``cid`` -- never just "red" (no frame, a press
    never taken and an unreached leg are red too, and none of them is the slid item or the friendly fire)."""
    if not isinstance(c, dict) or c.get("slot") != GUEST_WIRE:
        return False
    if cid in ("I1", "I2"):
        return (c.get("action") == cb.ACT_ITEM and c.get("id") == (ELIXIR if cid == "I1" else ETHER)
                and c.get("mask") == GUEST_MASK)
    return cid in ("T1", "T2a") and c.get("action") == cb.ACT_ATTACK and c.get("mask") == 1 << GARNET


def _catalog(calibrate: bool) -> dict:
    c = {
        "K0": "the forced selftest role on the bench field",
        "K1": "digit picks selftest: OK (22 rows)",
        "K2-pre": "the digit panel serves wire slot 3 (assist_slot 3, stock_owns false, the feed live, its digit keys "
                  "published) and a bench press reaches the panel's own read: [1] moves the pre-existing s113 "
                  "feed.ctl_menu 2 -> 3, [0] takes it back (digit_taken +2)",
        "I1": "the slid item: the page drawn [Potion, Ether, Elixir], the host's last Potion used with the page open -> [2] "
              "commits the drawn Ether (slot 3 Item id 238 mask 0x08), never the Elixir (239)",
        "I2": "the used-up item: [1] (the drawn Potion, gone from the host's bag) is REFUSED -- digit_taken +1, no frame for "
              "1.5 s, the page open (ctl_menu 3), digit_refused +1 naming item 236 -- never a frame for the Ether (238)",
        "T1-pre": "the Attack pick drew [Goblin, Zidane 0, Vivi 1, Garnet 2, Steiner 3] (digit_cands; ctl_menu 3)",
        "T1": "the shifted target: Zidane KO after the draw -> the drawn Vivi commits (slot 3 Attack mask 0x02), never "
              "Garnet (0x04)",
        "T2-pre": "the next Attack pick drew [Goblin, Vivi 1, Garnet 2, Steiner 3] -- the KO Zidane is not drawn",
        "T2a": "the fallen target: Vivi KO after the draw -> her digit is REFUSED -- digit_taken +1, no frame for 1.5 s, the "
               "pick open (ctl_menu 3), digit_refused +1 naming unit 1 -- never a frame for Garnet (0x04)",
        "T2b": "after the refusal the pick still commits: [1] -> the drawn Goblin (mask 1 << its btl index)",
        "K-INV": "the guest's own save untouched: the autosave fingerprint (gil, bag, party, levels) before == after",
        "K-R": "`reset` releases the role, the diorama, the feed, the digit-pick lever and a waiting bench digit",
    }
    if calibrate:
        del c["T2b"]                  # unreached under the lever (T2a's frame closed the pick): no witness, out of the set
        c["K-CAL-M"] = ("CALIBRATION: every predicted red is s153's BEHAVIOUR, seen in the frame its leg read -- I1 the "
                        f"Elixir ({ELIXIR}), I2 the Ether ({ETHER}), T1 and T2a Garnet (0x{1 << GARNET:02X}); a red for any "
                        "other reason is no calibration (K-CAL reads this row red as unpredicted)")
        c["K-CAL"] = ("CALIBRATION (`bbench digitsnap off`): exactly I1, I2, T1, T2a red, each behaviourally (K-CAL-M green; "
                      "T2b dropped: unreached under the lever)")
    return c


#: the plain run's checks (COOP_CALIBRATE=1 runs _catalog(True): T2b out, K-CAL-M and K-CAL in)
CATALOG = _catalog(False)


# ------------------------------------------------------------------------------------------- observing
def feed(x) -> dict:
    f = cb.path(x, "netsync.battle.menu.feed")
    return f if isinstance(f, dict) else {}


def _int(v, default: int = -1) -> int:
    return v if isinstance(v, int) and not isinstance(v, bool) else default


def last_frame(x) -> dict | None:
    """The frame the bench host took last (`feed.last`, "digit panel [01 03 ...] slot ..."), RE-DECODED here."""
    m = re.search(r"\[([0-9A-Fa-f ]+)\]", str(feed(x).get("last") or ""))
    return cb.decode_cmd(m.group(1)) if m else None


def brief(x) -> str:
    f = feed(x)
    return (f"mode {f.get('digit_mode')!r} snap {f.get('digit_snap')!r} waiting {f.get('digit_waiting')!r} taken "
            f"{f.get('digit_taken')!r} cands {f.get('digit_cands')!r} items {f.get('digit_items')!r} refused "
            f"{f.get('digit_refused')!r} ctl_menu {f.get('ctl_menu')!r} feed.taken {f.get('taken')!r} ready "
            f"{f.get('ready')!r} last {str(f.get('last'))[:160]!r}")


# ------------------------------------------------------------------------------------------- acting
def press(g, d: int, *, timeout: float = TAKE_S) -> tuple:
    """ONE bench press, proven to reach the panel's own read: (ok, why, the state after it was taken). Waits for no digit
    to be waiting first, then for `digit_taken` to advance (a check that cannot fail otherwise)."""
    st = cb.poll(g, lambda s: _int(feed(s).get("digit_waiting")) == -1, timeout, "no bench digit waiting")
    if st is None:
        return False, f"a bench digit still waits before [{d}] ({brief(g.state)})", None
    taken0 = _int(feed(st).get("digit_taken"), 0)
    ok, why = cb.try_ns(g, "bbench", "digit", d)
    if not ok:
        return False, f"`bbench digit {d}` refused: {why}", None
    st = cb.poll(g, lambda s: _int(feed(s).get("digit_taken"), 0) > taken0, timeout, f"the panel to take [{d}]")
    if st is None:
        return False, f"[{d}] was never taken ({brief(g.state)})", None
    return True, "", st


def queue(g, d: int) -> tuple:
    """A bench press that need not be taken now (a slot that is not Ready leaves it waiting)."""
    return cb.try_ns(g, "bbench", "digit", d)


def frame_after(g, taken0: int, timeout: float = TAKE_S):
    """The next frame the bench host takes after `feed.taken` == taken0: (decoded or None, the state)."""
    st = cb.poll(g, lambda s: _int(feed(s).get("taken"), 0) > taken0, timeout, "the bench host to take a frame")
    if st is None:
        return None, g.state
    return last_frame(st), st


def no_frame(g, taken0: int, mode: str) -> tuple:
    """HOLD_S of publishes: no frame taken and the panel still below its root at ``mode``. (ok, detail)."""
    samples = cb.hold_for(g, HOLD_S)
    sent = [s for s in samples if _int(feed(s).get("taken"), 0) != taken0]
    closed = [s for s in samples if feed(s).get("digit_mode") != mode or _int(feed(s).get("ctl_menu")) != 3]
    detail = f"{len(samples)} publishes; frames taken {len(sent)}; off the {mode} page {len(closed)}"
    if sent:
        detail += f"; first frame {last_frame(sent[0])!r}"
    return not sent and not closed and len(samples) > 0, detail


def ready(g) -> tuple:
    """`bbench ready 8` and the panel serving wire 3 at its root again."""
    ok, why = cb.try_ns(g, "bbench", "ready", GUEST_MASK)
    if not ok:
        return False, f"`bbench ready {GUEST_MASK}` refused: {why}", None
    st = cb.poll(g, lambda s: _int(cb.bmenu(s).get("assist_slot")) == GUEST_WIRE and feed(s).get("digit_mode") == "root"
                 and _int(feed(s).get("ctl_menu")) == 2, TAKE_S, "the panel serving wire 3 at its root")
    if st is None:
        return False, f"the panel never served wire 3 at its root ({brief(g.state)})", None
    return True, "", st


def roster(g, data: bytes) -> tuple:
    return cb.try_ns(g, "bbench", "roster", *cb.hexstr(data).split())


def kill(g, slot: int) -> tuple:
    """`endbench kill <btl_id>` on party slot ``slot``, then the feed carries it (KILL_FRAMES more samples)."""
    f0 = _int(feed(g.state).get("frames"), 0)
    ok, why = cb.try_ns(g, "endbench", "kill", 1 << slot)
    if not ok:
        return False, f"`endbench kill {1 << slot}` refused: {why}"
    st = cb.poll(g, lambda s: (cb.unit(s, slot) or {}).get("hp") == 0 and _int(feed(s).get("frames"), 0) >= f0 + KILL_FRAMES,
                 6.0, f"slot {slot} KO on the feed's lane")
    if st is None:
        return False, f"slot {slot} never read KO on the lane (unit {cb.unit(g.state, slot)!r}; {brief(g.state)})"
    return True, ""


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _catalog(calibrate), finals=("K-INV", "K-R", "K-CAL-M", "K-CAL"))
    fp0, fp_why = None, ""
    pulled = {"lever": False}                              # the lever actually taken (K-R then expects its release line)
    frames = {}                                            # PREDICTED_S153 leg -> the frame it read (K-CAL-M's markers)
    try:
        at0 = cb.mark(g)
        ok, why = cb.setup(g, field, label="s154 digit picks, solo" + (" -- CALIBRATION (`bbench digitsnap off`)"
                                                                         if calibrate else ""))
        led.check("K0", ok, why)
        if not ok:
            led.close("the forced selftest role did not arm")
            return
        lines = cb.wait_log(g, at0, "digit picks selftest:", timeout=20.0)
        proof = [ln for ln in lines if "digit picks selftest:" in ln]
        led.check("K1", bool(proof) and "OK (22 rows)" in proof[-1], cb.grep(lines, "digit picks selftest:") or "no line")
        fp0, fp_why = cb.fingerprint(g, field=field)
        _legs(g, led, calibrate, pulled, frames)
    finally:
        at = cb.mark(g)
        cb.release(g, led, "K-R", at=at, expect_lines=(LEVER_BACK,) if pulled["lever"] else (),
                   extra=lambda st: (not feed(st), f"feed after the reset {feed(st)!r}"))
        lines = cb.new(g, at)
        g.note("release lines: " + (cb.grep(lines, "digit-panel snapshot", DISCARDED, "bench feed stopped") or "none"))
        fp1, why1 = cb.fingerprint(g, field=field) if fp0 is not None else (None, "")
        if fp0 is None:
            led.check("K-INV", False, f"not reached: the BEFORE fingerprint failed: {fp_why}")
        elif fp1 is None:
            led.check("K-INV", False, f"the AFTER fingerprint failed: {why1}")
        else:
            diff = cb.fp_diff(fp0, fp1)
            led.check("K-INV", not diff, f"changed: {diff or 'nothing'}"
                      + (f" -- before {[fp0.get(k) for k in diff]} after {[fp1.get(k) for k in diff]}" if diff else ""))
        if calibrate:
            # K-CAL-M first: its red is an UNPREDICTED red to K-CAL, so a red s153's code did not produce cannot pass it
            seen = {c: s153_marker(c, frames.get(c)) for c in PREDICTED_S153}
            led.check("K-CAL-M", all(seen.values()),
                      "; ".join(f"{c} {'SEEN' if seen[c] else 'NOT seen'} (want {S153_MARKERS[c]}; read "
                                f"{frames.get(c, 'no frame: the leg never read one')!r})" for c in PREDICTED_S153))
            led.judge_calibration("K-CAL", PREDICTED_S153)
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'digit-picks' + ('-cal' if calibrate else ''))}")
        led.close(final=True)


def _legs(g, led, calibrate, pulled, frames):
    """The diorama, the feed and the legs. The harness `reset` (run's finally) releases the diorama it booted. Each
    PREDICTED_S153 leg leaves the frame it read in ``frames`` (None = none taken) for K-CAL-M."""
    legs = [c for c in LEGS if c in led.catalog]
    ok, why = cb.boot(g)
    if not ok:
        led.unreached(legs, f"the diorama did not boot: {why}")
        return
    st = cb.wait_steady(g)
    if st is None:
        led.unreached(legs, "the diorama never reached its command phase")
        return
    _feed_legs(g, led, legs, st, calibrate, pulled, frames)


def _feed_legs(g, led, legs, st, calibrate, pulled, frames):
    seated = cb.player_slots(st)
    enemies = sorted(int(u.get("slot", -1)) for u in cb.units(st, player=False) if u.get("alive"))
    if seated[:4] != [0, 1, 2, 3] or not enemies:
        led.unreached(legs, f"the diorama seats party slots {seated} and enemies {enemies} -- the bench needs the four of "
                            f"COOPPARTY (30604 registered?) and a living enemy")
        return
    for step, args in (("knob", ("knob", 0)), ("roster R1", ("roster", *cb.hexstr(R1).split())),
                       ("start", ("start", GUEST_MASK))):
        ok, why = cb.try_ns(g, "bbench", *args)
        if not ok:
            led.unreached(legs, f"`bbench {step}` refused: {why}")
            return
    ok, why, st = ready(g)
    f = feed(st or g.state)
    menu = cb.bmenu(st or g.state)
    have = cb.has(st or g.state, PROBE)                    # (inside the feed: readable only while it runs -- it runs here)
    if not have:
        led.check("K2-pre", False, f"absent: the feed publishes no `{PROBE}` -- this engine has no digit input (an "
                                   f"s107-s153 engine: no harness input reaches its digit panel); {brief(st or g.state)}")
        led.unreached([c for c in legs if c != "K2-pre"], "this engine has no digit input (absent, not a calibration)")
        return
    if not ok:
        led.unreached(legs, why)
        return
    # K2-pre: the panel serves wire 3, and the instrument -- a bench press moves the PRE-EXISTING s113 ctl_menu 2 -> 3 -> 2
    taken0 = _int(f.get("digit_taken"), 0)
    pre = (menu.get("assist_slot") == GUEST_WIRE and menu.get("stock_owns") is False and f.get("live") is True
           and _int(f.get("ctl_menu")) == 2)
    ok1, why1, st1 = press(g, 1)
    st1 = cb.poll(g, lambda s: _int(feed(s).get("ctl_menu")) == 3 and feed(s).get("digit_mode") == "target", TAKE_S,
                  "ctl_menu 3 after [1]") if ok1 else None
    ok0, why0, st0 = press(g, 0) if st1 is not None else (False, "skipped: [1] never moved ctl_menu", None)
    st0 = cb.poll(g, lambda s: _int(feed(s).get("ctl_menu")) == 2 and feed(s).get("digit_mode") == "root", TAKE_S,
                  "ctl_menu 2 after [0]") if ok0 else None
    good = pre and st1 is not None and st0 is not None and _int(feed(st0).get("digit_taken"), 0) == taken0 + 2
    led.check("K2-pre", good, f"assist_slot {menu.get('assist_slot')!r} stock_owns {menu.get('stock_owns')!r} live "
                              f"{f.get('live')!r} ctl_menu {f.get('ctl_menu')!r}; [1] {why1 or 'taken'} [0] {why0 or 'taken'}; "
                              f"{brief(st0 or g.state)}")
    if not good:
        led.unreached([c for c in legs if c != "K2-pre"], "the instrument did not calibrate (K2-pre)")
        return
    if calibrate:
        ok, why = cb.try_ns(g, "bbench", "digitsnap", "off")
        pulled["lever"] = ok
        snap = feed(cb.poll(g, lambda s: feed(s).get("digit_snap") is False, 3.0, "the lever read back") or g.state)
        g.note(f"CALIBRATION: `bbench digitsnap off` {'taken' if ok else 'REFUSED: ' + why}; digit_snap "
               f"{snap.get('digit_snap')!r} -- s153's draw and press at the four sites from here")
        g.note("T2b: N/A under the lever -- T2a's frame is ACCEPTED and the slot's Ready bit falls, so [1] is never read "
               "(unreached under the lever); it stays an s154-only green leg, out of PREDICTED_S153")
    _item_legs(g, led, frames)
    _target_legs(g, led, enemies, calibrate, frames)


def _item_legs(g, led, frames):
    # I1 -- the slid item: [5] draws R1's page; the host's last Potion goes (R2) with the page open; [2]
    ok, why, st = press(g, 5)
    st = cb.poll(g, lambda s: feed(s).get("digit_mode") == "item" and _int(feed(s).get("ctl_menu")) == 3, TAKE_S,
                 "the item page") if ok else None
    if st is None:
        led.unreached(["I1", "I2"], f"[5] did not open the item page: {why or brief(g.state)}")
        return
    drawn = feed(st).get("digit_items")
    ok, why = roster(g, R2)
    if not ok:
        led.unreached(["I1", "I2"], f"`bbench roster R2` refused: {why}")
        return
    taken0 = _int(feed(g.state).get("taken"), 0)
    ok, why, _st = press(g, 2)
    c, st = frame_after(g, taken0) if ok else (None, g.state)
    frames["I1"] = c
    led.check("I1", drawn == [POTION, ETHER, ELIXIR] and c is not None and c["slot"] == GUEST_WIRE
              and c["action"] == cb.ACT_ITEM and c["id"] == ETHER and c["mask"] == GUEST_MASK,
              f"drawn {drawn!r}; [2] {why or 'taken'}; frame {c!r} (green: id {ETHER} mask 0x{GUEST_MASK:02X}; red: id "
              f"{ELIXIR}); {brief(st)}")
    # I2 -- the used-up item: the page drawn again with the Potion, the Potion used up again (R2), [1]
    ok, why, st = ready(g)
    if ok:
        ok, why = roster(g, R1)
    if ok:
        ok, why, st = press(g, 5)
        st = cb.poll(g, lambda s: feed(s).get("digit_mode") == "item" and _int(feed(s).get("ctl_menu")) == 3, TAKE_S,
                     "the item page again") if ok else None
        ok = st is not None
    if ok:
        ok, why = roster(g, R2)
    if not ok:
        led.unreached(["I2"], f"the I2 page did not open: {why or brief(g.state)}")
        return
    f0 = feed(g.state)
    taken0, refused0 = _int(f0.get("taken"), 0), _int(f0.get("digit_refused"), 0)
    ok, why, _st = press(g, 1)
    held, hold_why = no_frame(g, taken0, "item") if ok else (False, "the press was not taken")
    st = g.state
    f1 = feed(st)
    c = last_frame(st) if _int(f1.get("taken"), 0) != taken0 else None
    frames["I2"] = c
    rwhy = str(f1.get("digit_refused_why") or "")
    led.check("I2", ok and held and _int(f1.get("digit_refused"), 0) == refused0 + 1 and f"(item {POTION})" in rwhy
              and USED_UP in rwhy,
              f"[1] {why or 'taken'}; {hold_why}; refused {refused0}->{f1.get('digit_refused')!r} why {rwhy!r}; frame "
              f"{c!r} (red: id {ETHER}); note {f1.get('digit_note')!r}")
    if feed(g.state).get("digit_mode") == "item":
        press(g, 0)                                        # back to the root (the law: the page is still open)


def _target_legs(g, led, enemies, calibrate, frames):
    e = len(enemies)
    # T1 -- the shifted target: Attack draws [enemies, 0, 1, 2, 3]; Zidane KO; the drawn Vivi's digit
    ok, why, st = ready(g)
    if ok:
        ok, why, st = press(g, 1)
    st = cb.poll(g, lambda s: feed(s).get("digit_mode") == "target" and _int(feed(s).get("ctl_menu")) == 3, TAKE_S,
                 "the Attack pick") if ok else None
    want = enemies + [0, 1, 2, 3]
    cands = feed(st).get("digit_cands") if st is not None else None
    led.check("T1-pre", st is not None and cands == want, f"drawn {cands!r} (want {want}); {why or brief(st or g.state)}")
    if st is None or cands != want:
        led.unreached(["T1", "T2-pre", "T2a", "T2b"], "the Attack pick did not draw the expected list (T1-pre)")
        return
    ok, why = kill(g, 0)
    if not ok:
        led.unreached(["T1", "T2-pre", "T2a", "T2b"], why)
        return
    taken0 = _int(feed(g.state).get("taken"), 0)
    ok, why, _st = press(g, e + 2)                          # the drawn Vivi (unit 1)
    c, st = frame_after(g, taken0) if ok else (None, g.state)
    frames["T1"] = c
    led.check("T1", c is not None and c["slot"] == GUEST_WIRE and c["action"] == cb.ACT_ATTACK and c["mask"] == 1 << 1,
              f"[{e + 2}] {why or 'taken'}; frame {c!r} (green: mask 0x02 Vivi; red: 0x04 Garnet); {brief(st)}")
    # T2 -- the fallen target: Attack draws [enemies, 1, 2, 3]; Vivi KO; her digit
    ok, why, st = ready(g)
    if ok:
        ok, why, st = press(g, 1)
    st = cb.poll(g, lambda s: feed(s).get("digit_mode") == "target" and _int(feed(s).get("ctl_menu")) == 3, TAKE_S,
                 "the second Attack pick") if ok else None
    want = enemies + [1, 2, 3]
    cands = feed(st).get("digit_cands") if st is not None else None
    led.check("T2-pre", st is not None and cands == want, f"drawn {cands!r} (want {want}); {why or brief(st or g.state)}")
    if st is None or cands != want:
        led.unreached(["T2a", "T2b"], "the second Attack pick did not draw the expected list (T2-pre)")
        return
    ok, why = kill(g, 1)
    if not ok:
        led.unreached(["T2a", "T2b"], why)
        return
    f0 = feed(g.state)
    taken0, refused0 = _int(f0.get("taken"), 0), _int(f0.get("digit_refused"), 0)
    ok, why, _st = press(g, e + 1)                          # the drawn Vivi, KO since the draw
    held, hold_why = no_frame(g, taken0, "target") if ok else (False, "the press was not taken")
    st = g.state
    f1 = feed(st)
    c = last_frame(st) if _int(f1.get("taken"), 0) != taken0 else None
    frames["T2a"] = c
    rwhy = str(f1.get("digit_refused_why") or "")
    led.check("T2a", ok and held and _int(f1.get("digit_refused"), 0) == refused0 + 1 and "(unit 1)" in rwhy
              and FALLEN in rwhy,
              f"[{e + 1}] {why or 'taken'}; {hold_why}; refused {refused0}->{f1.get('digit_refused')!r} why {rwhy!r}; frame "
              f"{c!r} (red: mask 0x04 Garnet); note {f1.get('digit_note')!r}")
    if "T2b" not in led.catalog:                            # the calibration: unreached under the lever (noted above)
        ok, why = queue(g, 1)
        time.sleep(1.0)
        g.note(f"T2b (N/A under the lever): [1] {'queued' if ok else 'refused: ' + why}; after 1 s {brief(g.state)}")
        return
    taken0 = _int(feed(g.state).get("taken"), 0)
    ok, why, _st = press(g, 1)                              # the drawn Goblin: the pick still commits after a refusal
    c, st = frame_after(g, taken0) if ok else (None, g.state)
    led.check("T2b", c is not None and c["slot"] == GUEST_WIRE and c["action"] == cb.ACT_ATTACK
              and c["mask"] == 1 << enemies[0],
              f"[1] {why or 'taken'}; frame {c!r} (green: mask 0x{1 << enemies[0]:02X}, the drawn enemy); {brief(st)}")
