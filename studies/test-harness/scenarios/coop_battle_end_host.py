"""B4/B5 STAGE 4 -- THE HOST END BLOCK (memoria-patch s103), the solo bench, run unattended.

THE GAP (studies/battle-coop/B4-B5-DESIGN.md 3.6, 5.2, 6.2). At the host's win the guest's diorama kept showing a live
fight until the stale-lane leave, because nothing on the wire said how the host's battle was ENDING or where its
stock result screen stood. s103 appends an additive trailer to every co-op host type-1 frame (magic 0xB5, fmt 1, the
8-byte END BLOCK: kind / phase / seq / result / ui / resState (+Loading bit 7) / flags / winPoseMask), sampled at once
on every end-state change; `ParseView` reads it in its own try (a bad trailer nulls only the end, never the view).
ClassifyEnd: MENU_OFF + a victory seq = victory-pending; PHASE_VICTORY = victory; CLOSE + VICTORY/NO_POSE =
victory-no-pose; CLOSE + DEFEAT/GAMEOVER = defeat; var 32's MENU_OFF/EVENT = event (NOT an end).

THE BENCH. `netsync selftest 1` on field 30602; `netsync endbench <op>` FABRICATES an end block through the real
codec and the REAL ParseView and serves it as the BENCH end (`netsync.battle.peer.end`, bench true); a REAL own battle
(`battle 67`) ships its genuine block on the selftest loopback, so `host.end_trail` (what the host shipped) and
`peer.end_trail` (what ParseView read back) can be compared after the field load.

WHAT IS PROVEN (outcomes: the parsed blocks, the trails, the live result screen, the engine's log lines):
  A  codec + classifier, no battle: SelfTest OK (classify 23, chase 162 + pins, codec 46 -- later stages append
     their sections), both the verb's line and the session's own proof line; `endbench victory` round-trips every
     field (and logs its 24 B frame, trailer at +12); each fabricate advances wire_seq by 1 (ui/state/loading/flags
     each carried); every classification through the real ClassifyEnd (incl. CLOSE + DEFEAT = defeat and var 32's
     event); the out-of-range / stage-9 ops are refused; `clear` empties peer.end.
  B  a real own battle through the loopback: peer.end is never the bench seam; while the result screen is up its
     live state/Loading equals host.end's within a tick; after the field load host.end_trail == peer.end_trail,
     shaped 0/0/- .. 2/0/- .. 2/1/<state>.. 2/1/7 with a Loading entry at the EXP/AP fade; every settled press steps
     the state; end_edges > 0, <= end_changes, and end_changes >= trail - 1 (the pumps do not count an edge that
     lands on a cadence tick or a phase edge, so `edges >= trail - 1` would be probabilistic); peer.live falls only
     with the battle scene; host.end/peer.end go null and the trails stay; the host/peer log lines name the walk.
  C  the victory-edge one-shot (`endbench cmd`, guestslots 2): at the first end-kind sample the frame is queued and
     drained in the same tick and REFUSED "the battle is ending (menu off)" -- cmd_refused +1 exactly, end_cmd
     "fired victory-pending".
  D  SAME-DLL CALIBRATION, the lever: `endbench host off` (the pre-stage host) -> host.end/peer.end null and both
     trails [] for a whole battle, trailer_bad unchanged; `endbench host cadence` -> the trail ships but end_edges ==
     0 with end_changes > 0 (the change trigger is the stage's effect). Short entries missing under cadence are
     probabilistic and only NOTED (judge them over several openings, never one).
  R  `reset` with the lever left at cadence restores it ('end-block host back ON (released with the harness)').
  E  co-op OFF (after the reset: Enabled 0): a battle publishes host.end null throughout and logs no end-block line.
  G  (COOP_END_GAMEOVER=1, LAST, a throwaway save) a deliberate loss (guestslots 15: nobody commands): the host trail
     reports ui 2 (Game Over); whether it reaches ui 3 (the title) and whether peer.live stays up there is NOTED --
     that settles design risk 4.
NOT PROVEN HERE (stage 5-6 + two-machine): a guest acting on the block; the live-lane nonce gate on a real relay.

CALIBRATION.
  * PRE-STAGE DLL (s102): the probe fails closed -- `netsync endbench` answers "netsync: unknown sub-verb 'endbench'
    (...|bmenu)" and `netsync.battle.host.end_trail` is absent: P0 and every A/C/D check RED (A/C/D "not reached"
    with that refusal); leg B's battle still runs and its trail/end checks are RED on the absent keys; E is RED (no
    `host.end` key to read null -- an absent key is not a null); R RED. GREEN there: S0 and B7 (peer.live staying up
    through the result screen is the stage-1 lane the block RIDES, not this stage's change). Stand-in at s102 caps:
    the same two.
  * The DEPLOYED DLL at writing (s99): `netsync.battle` is absent entirely, so B7 goes red too -- S0 is the one green
    (stand-in at s99 caps: 1 green / 22 red).
  * In-run, on the stage DLL: leg D is the lever's red, judged as its own checks (D1/D2 pass when the lever reverts
    exactly the stage's paths).
  * R3 RE-BASELINE (s115-s117, studies/battle-coop/R3-DESIGN.md 3.2.4): the only change s115-s117 make on THIS bench's wire is s116's
    additive fmt-2 FLEE record after the 0xB5 fmt-1 block -- written only once the host's stock escape tail has dropped
    gil (Zidane's Flee), so every victory frame stays byte-identical to s115. S4-B3 now also wants
    `peer.trailer_skipped` UNCHANGED across leg B's real battle -- an s103-s115 guest skips an unknown record by its len
    and an s116+ guest skips a SHORT fmt-2 body (both count trailer_skipped), so a malformed record turns it red -- AND,
    on an engine that publishes the key (s116+), `host.end.flee_gil` and `peer.end.flee_gil` reading -1 on every
    battle publish: an s116+ guest PARSES a whole fmt-2 record and never counts it (NetSyncEnd.ReadTrailer), so only
    the parsed figure can catch a host that wrongly shipped a well-formed record on a victory (review R3H-4). Green on
    every engine from s103 on (no record; before s116 the flee_gil keys are absent and that half reads nothing).
    Unchanged and still green: S4-A1/A2's head ("codec 46": s116 moved its unknown-fmt rows from 0x02 to 0x7F
    and kept the count), S4-A3's line (EndBlock.ToString adds ", flee 0x.. N gil" only when a record is present -- the
    template carries none without `endbench fleegil`), S4-A5's kinds (escape 5, defeat 4: ClassifyEnd untouched), S4-B9's
    lines (the record's own line is "battle flee record (peer, ...", never "battle end block").

    py tools/play.py studies/test-harness/scenarios/coop_battle_end_host.py --field 30602
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

GAMEOVER_LEG = os.environ.get("COOP_END_GAMEOVER", "").strip() not in ("", "0")
BENCH_NONCE = 0xB5                       # NetSyncEnd.BenchNonce (181)
SELFTEST_HEAD = "classify 23, chase 162 + pins, codec 46"
FIGHT_S = 300.0
TRAIL_RX = re.compile(r"^(\d+)/(\d+)/(-|\d+)(L?)$")

CATALOG = {
    "S4-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
    "S4-P0": "the engine publishes `netsync.battle.host.end_trail` (memoria-patch s103, stage 4)",
    "S4-A1": "`endbench selftest` succeeds and logs 'harness: battle end-block selftest OK (classify 23, chase 162 + "
             "pins, codec 46'",
    "S4-A2": "the selftest session's own proof line 'battle end-block selftest: OK (classify 23, chase 162 + pins, "
             "codec 46' is in the log",
    "S4-A3": "`endbench victory` round-trips through the real ParseView: peer.end == {kind 2 'victory', phase 6, seq 0, "
             "result 1, ui 0, res_state -1, loading false, flags 0, win_pose 15, manifest_len 0, rows 0, bench true, "
             "nonce 181}, and its line names a 24 B frame with the trailer at +12",
    "S4-A4": "each fabricate advances wire_seq by 1 and carries its field: ui 1 -> res 0; state 2 loading -> 2 + "
             "loading; state 7 -> 7; afterevent 1 -> flags 1; overflow 1 -> flags 5",
    "S4-A5": "ClassifyEnd through the real ParseView: pending 1, nopose 3, defeat 4, escape 5, other 5 -> 6, other 3 "
             "-> 4 (CLOSE + DEFEAT), event 7 (var 32: not an end), fight 0",
    "S4-A6": "the out-of-range and stage-9 ops are refused: manifest, state 9, ui 4, host x",
    "S4-A7": "`endbench clear` -> peer.end reads null on the field",
    "S4-B1": "B (a real own battle): peer.end is NEVER the bench seam on any loopback read (bench false)",
    "S4-B2": "B: while ui is 1, host.end.res_state/loading equal battle.result_ui.state/loading, or trail it by exactly "
             "one publish (the previous local value, or agreeing on the next)",
    "S4-B3": "B: after the field load host.end_trail == peer.end_trail (the loopback round trip), non-empty, and "
             "peer.trailer_skipped unchanged across the battle (no trailer record skipped), and where the engine "
             "publishes them (s116+) host.end.flee_gil and peer.end.flee_gil -1 on every battle publish (a victory "
             "ships no s116 flee record: a whole one is PARSED, never counted)",
    "S4-B4": "B: the trail's shape -- starts 0/0/-, kind walks 0 -> (1) -> 2 never back, ui 0 -> 1, the result state "
             "never decreases and reaches 7 (the Hide, '2/1/7' or '2/1/7L'), after which only the close '2/0/-' (the "
             "result-hide edge) or None states follow, with an L entry at state 2 or 3 (the EXP/AP fade)",
    "S4-B5": "B: every press on a SETTLED result screen (not Loading, state < 7) is followed by a higher state within 2 s",
    "S4-B6": "B: the change trigger fired and the tracker saw every step -- end_edges > 0, end_edges <= end_changes, "
             "end_changes >= len(trail) - 1 (an edge on a cadence/phase-edge tick is not counted, so edges vs trail "
             "is reported, not judged)",
    "S4-B7": "B: peer.live falls only with the battle scene (never false on a battle publish once it rose)",
    "S4-B8": "B: after the battle host.end and peer.end read null and both trails remain",
    "S4-B9": "B: the log names the walk -- 'battle end block (host): ... -> victory (phase 6', 'victory ui 0 -> "
             "victory (... ui 1, res 0', each '-- shipped on the type-1 lane', and matching '(peer, nonce N)' lines",
    "S4-C1": "C: `endbench cmd` (guestslots 2) fires at the first end-kind sample: 'harness: endbench cmd -- the host's "
             "end edge (victory-pending ...) queued the frame on the loopback (drained this tick)', then 'peer command "
             "for slot 1 (Attack) refused -- not in the command phase: the battle is ending (menu off)'; cmd_refused +1 "
             "exactly; end_cmd 'fired victory-pending'",
    "S4-D1": "D (lever OFF = the pre-stage host): for a whole battle host.end and peer.end null, both trails [], "
             "trailer_bad unchanged, end_mode 'off'",
    "S4-D2": "D (lever CADENCE): the trail still ships but end_edges == 0 while end_changes > 0, end_mode 'cadence'",
    "S4-R": "`reset` with the lever left at cadence: 'end-block host back ON (released with the harness)', end_mode 'on'",
    "S4-E1": "E (co-op OFF after the reset): a battle publishes netsync.battle.host.end null throughout and logs no "
             "'battle end block' line",
}
if GAMEOVER_LEG:
    CATALOG["S4-G1"] = "G (a deliberate loss): the host trail reports ui 2 (Game Over) -- x/2/-"


# ------------------------------------------------------------------------------------------- helpers
def _trail(entries) -> list:
    out = []
    for e in entries or []:
        m = TRAIL_RX.match(str(e))
        if m:
            out.append((int(m.group(1)), int(m.group(2)), None if m.group(3) == "-" else int(m.group(3)), bool(m.group(4))))
    return out


def _peer_end(st) -> dict | None:
    e = cb.peer(st).get("end")
    return e if isinstance(e, dict) else None


def _host_end(st) -> dict | None:
    e = cb.host(st).get("end")
    return e if isinstance(e, dict) else None


def _endbench(g, *args) -> tuple:
    return cb.try_ns(g, "endbench", *args)


def _fabricate(g, *args) -> tuple:
    """(ok, why, peer.end after, wire_seq before)."""
    seq0 = (_peer_end(g.state) or {}).get("wire_seq")
    ok, why = _endbench(g, *args)
    st = g.state
    return ok, why, _peer_end(st), seq0


def _battle(g, *, epoch_tag: str, on_sample=None) -> tuple:
    """A real own battle on scene 67, fought to its result and confirmed out, reading every publish. Returns
    (result or None, why, samples, presses) where presses carry the settled state they were made on."""
    st0 = g.state
    try:
        g.start_battle(cb.SCENE)
    except HarnessError as err:
        return None, f"`battle {cb.SCENE}` ({epoch_tag}) did not start: {str(err)[:200]}", [], []
    frame0 = st0.frame
    try:
        result = g.fight(timeout=FIGHT_S, finish=False)
    except HarnessError as err:
        return None, f"{epoch_tag} did not reach a result: {str(err)[:200]}", [cb.raw(x) for x in g.states_since(frame0)], []
    samples = [cb.raw(x) for x in g.states_since(frame0)]
    if on_sample is not None:
        for x in samples:
            on_sample(x)
    presses = []
    for _ in range(40):
        st = g.state
        if not st.in_battle and st.ui_state not in ("BattleHUD", "BattleResult"):
            break
        ru = cb.battle(st).get("result_ui")
        presses.append({"frame": st.frame, "state": (ru or {}).get("state"), "loading": (ru or {}).get("loading"),
                        "after": []})
        g.press("confirm", 4)
        got = cb.hold_for(g, 0.4)
        for x in got:
            r = cb.raw(x)
            samples.append(r)
            presses[-1]["after"].append(r)
            if on_sample is not None:
                on_sample(r)
    tail = cb.hold_for(g, 1.0)                          # the field's first publishes (peer.live's fall, the nulls)
    for x in tail:
        r = cb.raw(x)
        samples.append(r)
        if on_sample is not None:
            on_sample(r)
    cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD", 30.0, "the field after the result screen")
    return result, "", samples, presses


def _on_battle(x) -> bool:
    return bool(cb.battle(x).get("active")) and not cb.battle(x).get("debug")


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    led = cb.Ledger(g, CATALOG)
    try:
        _run(g, led, field)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'end-host')}")
        cb.release(g)
        led.close(final=True)


def _run(g, led: cb.Ledger, field: int) -> None:
    ok, why = cb.setup(g, field, label="B4/B5 stage 4: the host end block (s103), solo")
    led.check("S4-S0", ok, why)
    st = g.state
    led.check("S4-P0", cb.has(st, "netsync.battle.host.end_trail"),
              f"netsync.battle.host keys: {sorted(cb.host(st))}" if cb.has(st, "netsync.battle") else
              "no `netsync.battle` at all (a pre-s100 engine)")
    bench = _leg_a(g, led)
    _leg_b(g, led)
    if bench:
        _leg_c(g, led)
        _leg_d(g, led)
    else:
        led.unreached(("S4-C1", "S4-D1", "S4-D2"), "`netsync endbench` does not exist on this engine (leg A)")
    _leg_r(g, led, bench)
    _leg_e(g, led)
    if GAMEOVER_LEG:
        _leg_g(g, led)


def _leg_a(g, led: cb.Ledger) -> bool:
    g.note("A: the codec and the classifier through the real ParseView (no battle)")
    at = cb.mark(g)
    ok, why = _endbench(g, "selftest")
    lines = cb.wait_log(g, at, "harness: battle end-block selftest", 2.0)
    led.check("S4-A1", ok and cb.count(lines, "harness: battle end-block selftest OK (" + SELFTEST_HEAD) == 1,
              why or cb.grep(lines, "end-block selftest"))
    if not ok and cb.absent(why):
        led.check("S4-A2", any("battle end-block selftest: OK (" + SELFTEST_HEAD in ln for ln in cb.log_lines(g)),
                  "no session proof line (and no `endbench` verb)")
        led.unreached(("S4-A3", "S4-A4", "S4-A5", "S4-A6", "S4-A7"), f"`netsync endbench` refused -- {why}")
        return False
    proof = [ln for ln in cb.log_lines(g) if "battle end-block selftest: " in ln]
    led.check("S4-A2", bool(proof) and ("battle end-block selftest: OK (" + SELFTEST_HEAD) in proof[-1],
              (proof[-1][-260:] if proof else "no session proof line"))
    # A3
    at = cb.mark(g)
    ok, why, e, _ = _fabricate(g, "victory")
    lines = cb.wait_log(g, at, "endbench victory -- fabricated", 2.0)
    want = {"kind": 2, "kind_name": "victory", "phase": 6, "seq": 0, "result": 1, "ui": 0, "res_state": -1,
            "loading": False, "flags": 0, "win_pose": 15, "manifest_len": 0, "rows": 0, "bench": True,
            "nonce": BENCH_NONCE}
    got = {k: (e or {}).get(k) for k in want}
    line = [ln for ln in lines if "endbench victory -- fabricated victory (phase 6 seq 0 result 1; ui 0, res -, flags "
            "0x00, pose 0x0F) through the real ParseView (24 B frame, trailer at +12, wire seq " in ln
            and "served as the BENCH end" in ln]
    led.check("S4-A3", ok and got == want and len(line) == 1, why or f"peer.end {got}; want {want}; "
                                                                     f"{cb.grep(lines, 'endbench')}")
    # A4: one field per fabricate, wire_seq +1 each
    steps = (("ui", "1"), ("state", "2", "loading"), ("state", "7"), ("afterevent", "1"), ("overflow", "1"))
    expect = ({"ui": 1, "res_state": 0, "loading": False}, {"res_state": 2, "loading": True},
              {"res_state": 7, "loading": False}, {"flags": 1}, {"flags": 5})
    bad = []
    for args, exp in zip(steps, expect):
        ok, why, e, seq0 = _fabricate(g, *args)
        e = e or {}
        sub = {k: e.get(k) for k in exp}
        if not ok or sub != exp or not isinstance(seq0, int) or e.get("wire_seq") != seq0 + 1:
            bad.append(f"{' '.join(args)}: ok={ok} {why[:80]} got {sub} wire_seq {seq0!r}->{e.get('wire_seq')!r}")
    led.check("S4-A4", not bad, "; ".join(bad) or "every field carried, wire_seq +1 each")
    # A5: the classifier
    cases = ((("pending",), 1), (("nopose",), 3), (("defeat",), 4), (("escape",), 5), (("other", "5"), 6),
             (("other", "3"), 4), (("event",), 7), (("fight",), 0))
    bad = []
    for args, kind in cases:
        ok, why, e, _ = _fabricate(g, *args)
        if not ok or (e or {}).get("kind") != kind:
            bad.append(f"{' '.join(args)} -> {(e or {}).get('kind')!r} (want {kind}){'' if ok else ' ' + why[:80]}")
    led.check("S4-A5", not bad, "; ".join(bad) or "all eight kinds")
    # A6: refusals
    bad = []
    for args in (("manifest",), ("state", "9"), ("ui", "4"), ("host", "x")):
        ok, why = _endbench(g, *args)
        if ok:
            bad.append(" ".join(args) + " was ACCEPTED")
    led.check("S4-A6", not bad, "; ".join(bad) or "all four refused")
    # A7
    ok, why = _endbench(g, "clear")
    st = cb.poll(g, lambda s: _peer_end(s) is None, 2.0, "peer.end to read null")
    led.check("S4-A7", ok and st is not None, why or f"peer.end={_peer_end(g.state)!r}")
    return True


def _leg_b(g, led: cb.Ledger) -> None:
    g.note("B: a real own battle through the loopback -- the trail")
    _endbench(g, "clear")
    tb0 = cb.peer(g.state).get("trailer_bad")
    # [R3 re-baseline, s116] the trailer's skip counter, read around the same battle (S4-B3; the module note)
    ts0 = cb.peer(g.state).get("trailer_skipped")
    at = cb.mark(g)
    result, why, samples, presses = _battle(g, epoch_tag="B")
    if result is None:
        led.unreached([c for c in led.pending("S4-B")], why)
        return
    st = g.state
    battle_samples = [x for x in samples if _on_battle(x)]
    # B1: never the bench seam on the loopback
    benchy = [x.get("frame") for x in battle_samples if isinstance(cb.peer(x).get("end"), dict) and cb.peer(x)["end"].get("bench")]
    seen = [x for x in battle_samples if isinstance(cb.peer(x).get("end"), dict)]
    led.check("S4-B1", seen and not benchy, f"{len(seen)} publish(es) with a peer.end; bench on frames {benchy[:6]}")
    # B2: live cross-check while ui 1
    pairs = []
    for x in samples:
        ru, he = cb.battle(x).get("result_ui"), cb.host(x).get("end")
        if isinstance(ru, dict) and isinstance(he, dict) and he.get("ui") == 1:
            pairs.append(((ru.get("state"), bool(ru.get("loading"))), (he.get("res_state"), bool(he.get("loading")))))
    # A mismatch is fine when it is the end block ONE PUBLISH BEHIND: it carries the previous publish's local state (the
    # host's pump samples before the result screen's own Update in the frame, so two local steps in a row -- 2L -> 3L ->
    # 3 -- leave the block a step behind for two publishes) or the very next publish agrees. Anything else -- a value the
    # local screen never showed, or a lag of two steps -- is a real miss.
    unresolved = [i for i, (a, b) in enumerate(pairs) if a != b
                  and not (i + 1 < len(pairs) and pairs[i + 1][0] == pairs[i + 1][1])
                  and not (i > 0 and b == pairs[i - 1][0])]
    led.check("S4-B2", len(pairs) >= 3 and not unresolved,
              f"{len(pairs)} paired publish(es); mismatches not resolved by the next: {[pairs[i] for i in unresolved][:5]}")
    # B3/B4/B6: the trails
    ht, pt = cb.host(st).get("end_trail"), cb.peer(st).get("end_trail")
    ts1 = cb.peer(st).get("trailer_skipped")
    # [R3 re-baseline, s116; review R3H-4] an s116+ guest PARSES a whole fmt-2 record (trailer_skipped stays put), so a
    # stray record on this victory shows only as a parsed figure: every battle publish's flee_gil must read -1 (no record)
    stray = [(x.get("frame"), side, e.get("flee_gil")) for x in battle_samples
             for side, e in (("host", cb.host(x).get("end")), ("peer", cb.peer(x).get("end")))
             if isinstance(e, dict) and "flee_gil" in e and e.get("flee_gil") != -1]
    keyed = sum(1 for x in battle_samples for e in (cb.host(x).get("end"), cb.peer(x).get("end"))
                if isinstance(e, dict) and "flee_gil" in e)
    led.check("S4-B3", isinstance(ht, list) and ht and ht == pt and ts1 == ts0 and not stray,
              f"host {ht}; peer {pt}; trailer_skipped {ts0!r}->{ts1!r} ({cb.peer(st).get('trailer_why')!r}); flee_gil "
              f"read on {keyed} end block(s), != -1 on {stray[:4]}")
    tr = _trail(ht)
    kinds = [k for k, _, _, _ in tr]
    uis = [u for _, u, _, _ in tr]
    states = [s for _, u, s, _ in tr if u == 1 and s is not None and s != 8]   # None (8) sorts after Hide: not a step
    loading = [(s, ld) for _, u, s, ld in tr if ld]
    hide = next((i for i, (_, u, s, _) in enumerate(tr) if u == 1 and s == 7), None)
    # After the Hide state the host's result screen is GONE: its ui flag falls back to 0 ("2/0/-") -- the very edge the
    # guest's stage-6 exit keys on (result-hide). So the tail may hold only that close and None (8) states; ui is
    # monotone up to the Hide. (The first draft required ui to stay 1 and an exact "2/1/7": the engine's Hide entry is
    # "2/1/7L" -- the closing fade -- and the close follows it.)
    after_hide = [] if hide is None else [e for e in tr[hide + 1:]
                                          if not ((e[1] == 1 and e[2] == 8) or (e[0] == 2 and e[1] == 0 and e[2] is None))]
    uis_to_hide = uis if hide is None else uis[:hide + 1]
    shape_ok = (bool(tr) and ht[0] == "0/0/-" and "2/0/-" in ht and hide is not None and not after_hide
                and all(a <= b for a, b in zip(kinds, kinds[1:])) and set(kinds) <= {0, 1, 2}
                and all(a <= b for a, b in zip(uis_to_hide, uis_to_hide[1:]))
                and all(a <= b for a, b in zip(states, states[1:]))
                and any(s in (2, 3) for s, _ in loading))
    led.check("S4-B4", shape_ok, f"trail {ht}; victory-pending (1/0/-) {'seen' if '1/0/-' in (ht or []) else 'NOT seen'}; "
                                 f"Loading entries {loading}")
    # B6 -- only the deterministic part. The pumps count an edge sample (NoteEdgeSample) only when NEITHER a command-phase
    # edge NOR the SampleMs (150) cadence is due that tick, so a change landing on a cadence tick (~1 in 5 at 30 fps) or
    # on the opening/closing phase edge ships its trail entry without counting: `edges >= trail - 1` is a coin toss on a
    # correct engine. What cannot vary: the tracker counts EVERY end-key change (end_changes >= trail - 1: each new
    # (kind, ui, resState) entry is one), edges never exceed changes, and the change trigger fired at least once
    # (edges > 0 -- leg D2's cadence lever is the red that pins edges to this stage's effect).
    edges, changes = cb.host(st).get("end_edges"), cb.host(st).get("end_changes")
    led.check("S4-B6", isinstance(edges, int) and isinstance(changes, int) and bool(tr) and edges > 0
              and edges <= changes and changes >= len(ht) - 1,
              f"end_edges={edges!r} end_changes={changes!r} trail length {len(ht or [])} "
              f"(edge share of the steps: {edges}/{max(len(ht or []) - 1, 0)} -- reported, not judged)")
    # B5: settled presses step the state
    judged, stuck = 0, []
    for p in presses:
        s0, ld = p.get("state"), p.get("loading")
        if not isinstance(s0, int) or ld or s0 >= 7:
            continue
        judged += 1
        rose = False
        later = p["after"]
        for x in later:
            ru = cb.battle(x).get("result_ui")
            if not isinstance(ru, dict) or (isinstance(ru.get("state"), int) and ru["state"] > s0):
                rose = True
                break
        if not rose:
            nxt = presses[presses.index(p) + 1:presses.index(p) + 6]
            rose = any(isinstance(q.get("state"), int) and q["state"] > s0 for q in nxt)
        if not rose:
            stuck.append((p.get("frame"), s0))
    led.check("S4-B5", judged >= 2 and not stuck, f"{judged} settled press(es) judged; not followed by a higher state: {stuck}")
    # B7: peer.live
    risen, bad = False, []
    for x in samples:
        live = cb.peer(x).get("live")
        if live:
            risen = True
        elif risen and _on_battle(x):
            bad.append(x.get("frame"))
    led.check("S4-B7", risen and not bad, f"peer.live rose: {risen}; false on battle publishes {bad[:6]}")
    # B8
    st = cb.poll(g, lambda s: _host_end(s) is None and _peer_end(s) is None, 3.0, "host.end/peer.end to read null") or g.state
    led.check("S4-B8", _host_end(st) is None and _peer_end(st) is None and cb.host(st).get("end_trail") == ht
              and cb.peer(st).get("end_trail") == pt and bool(ht),
              f"host.end={_host_end(st)!r} peer.end={_peer_end(st)!r} trails kept: {cb.host(st).get('end_trail') == ht}")
    # B9: the log walk
    lines = cb.new(g, at)
    hl = [ln for ln in lines if "battle end block (host): " in ln]
    pl = [ln for ln in lines if "battle end block (peer, nonce " in ln]
    led.check("S4-B9", any("-> victory (phase 6" in ln for ln in hl)
              and any("victory ui 0 -> victory (" in ln and "ui 1, res 0" in ln for ln in hl)
              and hl and all(ln.rstrip().endswith("-- shipped on the type-1 lane") for ln in hl)
              and len(pl) == len(hl),
              cb.grep(lines, "battle end block", limit=900))
    if cb.peer(g.state).get("trailer_bad") != tb0:
        g.note(f"trailer_bad moved {tb0!r} -> {cb.peer(g.state).get('trailer_bad')!r} during B ({cb.peer(g.state).get('trailer_why')!r})")


def _leg_c(g, led: cb.Ledger) -> None:
    g.note("C: the victory-edge one-shot (`endbench cmd`)")
    okg, whyg = cb.try_ns(g, "guestslots", 2)
    _endbench(g, "clear")
    ok, why = _endbench(g, "cmd")
    r0 = cb.host(g.state).get("cmd_refused")
    at = cb.mark(g)
    if not (okg and ok):
        led.check("S4-C1", False, f"not reached: guestslots {whyg or 'ok'}; endbench cmd {why or 'ok'}")
        return
    result, bwhy, _, _ = _battle(g, epoch_tag="C")
    st = g.state
    lines = cb.new(g, at)
    fired = [i for i, ln in enumerate(lines) if "harness: endbench cmd -- the host's end edge (victory-pending" in ln
             and "queued the frame on the loopback (drained this tick)" in ln]
    refused = [i for i, ln in enumerate(lines)
               if "peer command for slot 1 (Attack) refused -- not in the command phase: the battle is ending (menu off)" in ln]
    led.check("S4-C1", result is not None and fired and refused and fired[0] < refused[0]
              and isinstance(r0, int) and cb.host(st).get("cmd_refused") == r0 + 1
              and cb.host(st).get("end_cmd") == "fired victory-pending",
              bwhy or f"cmd_refused {r0!r}->{cb.host(st).get('cmd_refused')!r} end_cmd={cb.host(st).get('end_cmd')!r}; "
                      f"{cb.grep(lines, 'endbench cmd', 'peer command')}")
    cb.try_ns(g, "guestslots", 0)


def _leg_d(g, led: cb.Ledger) -> None:
    g.note("D: the calibration lever -- `endbench host off`, then `cadence`")
    ok, why = _endbench(g, "host", "off")
    tb0 = cb.peer(g.state).get("trailer_bad")
    if not ok:
        led.check("S4-D1", False, f"`endbench host off` refused -- {why}")
    else:
        result, bwhy, samples, _ = _battle(g, epoch_tag="D-off")
        st = g.state
        leaks = [x.get("frame") for x in samples if _on_battle(x)
                 and (isinstance(cb.host(x).get("end"), dict) or isinstance(cb.peer(x).get("end"), dict))]
        led.check("S4-D1", result is not None and not leaks and cb.host(st).get("end_trail") == []
                  and cb.peer(st).get("end_trail") == [] and cb.peer(st).get("trailer_bad") == tb0
                  and cb.host(st).get("end_mode") == "off",
                  bwhy or f"end blocks on frames {leaks[:6]}; trails {cb.host(st).get('end_trail')} / "
                          f"{cb.peer(st).get('end_trail')}; trailer_bad {tb0!r}->{cb.peer(st).get('trailer_bad')!r} "
                          f"end_mode={cb.host(st).get('end_mode')!r}")
    ok, why = _endbench(g, "host", "cadence")
    if not ok:
        led.check("S4-D2", False, f"`endbench host cadence` refused -- {why}")
    else:
        result, bwhy, _, _ = _battle(g, epoch_tag="D-cadence")
        st = g.state
        h = cb.host(st)
        tr = h.get("end_trail") or []
        led.check("S4-D2", result is not None and bool(tr) and h.get("end_edges") == 0
                  and isinstance(h.get("end_changes"), int) and h["end_changes"] > 0 and h.get("end_mode") == "cadence",
                  bwhy or f"trail {tr}; end_edges={h.get('end_edges')!r} end_changes={h.get('end_changes')!r} "
                          f"end_mode={h.get('end_mode')!r}")
        missed = [e for e in ("1/0/-",) if e not in tr] + (["an L entry"] if not any(str(e).endswith("L") for e in tr) else [])
        g.note(f"D-cadence: short entries missing this opening: {missed or 'none'} (probabilistic -- judge over several)")
    _endbench(g, "host", "on")


def _leg_r(g, led: cb.Ledger, bench: bool) -> None:
    ok, why = _endbench(g, "host", "cadence") if bench else (False, "no `endbench` on this engine")
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    lines = cb.new(g, at)
    led.check("S4-R", ok and cb.count(lines, "end-block host back ON (released with the harness)") == 1
              and cb.host(st).get("end_mode") == "on" and (st.netsync or {}).get("forced") is False,
              why or f"end_mode={cb.host(st).get('end_mode')!r}; {cb.grep(lines, 'released with the harness')}")


def _leg_e(g, led: cb.Ledger) -> None:
    g.note("E: co-op OFF -- the host ships no end block")
    st = g.state
    if (st.netsync or {}).get("enabled"):
        led.check("S4-E1", False, "not reached: co-op still enabled after the reset")
        return
    at = cb.mark(g)
    result, why, samples, _ = _battle(g, epoch_tag="E")
    lines = cb.new(g, at)
    present = all(cb.has(x, "netsync.battle.host.end") for x in samples if _on_battle(x))
    blocks = [x.get("frame") for x in samples if isinstance(cb.host(x).get("end"), dict)]
    led.check("S4-E1", result is not None and present and not blocks and cb.count(lines, "battle end block") == 0,
              why or f"host.end key present on every battle publish: {present}; non-null on {blocks[:6]}; "
                     f"{cb.grep(lines, 'battle end block')}")


def _leg_g(g, led: cb.Ledger) -> None:
    """LAST and THROWAWAY: nobody commands (guestslots 15), the party falls, Game Over -> the title."""
    g.note("G: a deliberate loss -- the Game Over trail (throwaway save)")
    ok, why = cb.try_ns(g, "selftest", 1)
    ok2, why2 = cb.try_ns(g, "guestslots", 15) if ok else (False, why)
    if not ok2:
        led.check("S4-G1", False, f"not reached: {why2}")
        return
    try:
        g.start_battle(cb.SCENE)
    except HarnessError as err:
        led.check("S4-G1", False, f"`battle {cb.SCENE}` did not start: {str(err)[:200]}")
        return
    samples, end = cb.watch(g, lambda s: (cb.host(s).get("end_trail") or []) and any(
        str(e).split("/")[1:2] == ["3"] for e in cb.host(s).get("end_trail") or []) or s.ui_state == "Title", 900.0)
    st = g.state
    tr = cb.host(st).get("end_trail") or []
    lived = sorted({str(cb.peer(x).get("live")) for x in samples if x.ui_state == "Title"})
    game_over = any(re.match(r"^\d+/2/-", str(e)) for e in tr)
    title = any(re.match(r"^\d+/3/-", str(e)) for e in tr)
    led.check("S4-G1", game_over, f"host trail {tr}")
    g.note(f"G: reached the title: {st.ui_state == 'Title'}; trail has ui 3: {title}; peer.live at the title: {lived}")
