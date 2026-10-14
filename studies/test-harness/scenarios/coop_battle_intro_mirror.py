"""R3 #1 + #2 -- THE BATTLE INTRO MIRROR (memoria-patch s111) and THE DIORAMA SWIRL CLAMP (s112, leg S), the solo
bench, run unattended.

THE DEFECT (studies/battle-coop/R3-DESIGN.md 1.1 report 1, 3.1.2, 3.1.5). Sitting 2: the host skipped its battle intro
(its per-save cfg.skip_btl_camera, on a random encounter) and went straight into the fight, while the guest's diorama
played the GUEST's own choice -- the laptop arrived seconds late. And a guest whose [Graphics] BattleSwirlFrames is the
code default (115, ~3.8 s) swirled that long into a diorama of a host that swirls 0.

THE FIX.
  s111  The host latches its own intro at its battle's rising edge (`cfg.skip_btl_camera == 0 && isRandomEncounter`, the
        stock expression) and publishes it in type-1 header bits 2-3 (0x08 = "bit 2 is meaningful", 0x04 = "I skipped");
        a wire-booted diorama applies the HOST's choice at the two stock intro sites (one seam, SkipBattleIntro); LiveTick
        latches "reached its command phase N ms after the boot". Lever: `netsync bench intro 0` (both halves).
  s112  A swirl constructed while a diorama is booted plays min(own, [Netsync] DioramaSwirlFrames) frames (default 0);
        every real battle keeps its own. Levers: `bench swirl local <frames>` (the laptop stand-in: this process's OWN
        swirl length) and `bench swirl clamp <frames>|-1` (-1 = the pre-stage diorama). THE DESKTOP'S [Graphics] VALUE IS
        0, so the clamp can shorten nothing there: leg S runs under `bench swirl local 115` (the s112 capture's remark).

THE BENCH. Field 30602 (LOCKT2), `netsync selftest 1`, `stateevery 1`. Host legs are selftest OWN battles on scene 67
(`battle 67 -1 [rand]`, fought out, back to the field); guest legs boot `netsync dioboot 67 0 [wire] [skip|play] [rand]`
and leave (`dioleave`) each time.

WHAT IS PROVEN (design 6.2 + 6.13; each an OUTCOME -- published keys and the engine's own log lines, never an ack):
  P0/P1  the capability (`netsync.diorama.intro`) -- CAUTION: `bench intro` / `bench cfg` are NEVER sent without it (an engine
         before s111 reads them as `bench 1`, the FIELD-GATE bench ON); `bench cfg skipcam 0` -> host.cfg 0.
  I-A1   `battle 67 -1 rand`: host.caps has 0x0C (and 0x01, the random bit) WHILE the battle is up, host.intro.published
         1, own_skip 1, ONE "battle intro: SKIPPED (skip_btl_camera 0, random 1) -- published ..." line.
  I-A2   `battle 67` (rand 0): caps bit 3 set, bit 2 clear, published 0, own_skip 0, one "PLAYED (... random 0)" line.
  I-A3   A1's ENTER -> command-phase span is >= 1000 ms shorter than A2's (ENTER = the first publish of the new battle).
  I-B1/2 `dioboot 67 0 skip` / `play` (each a fresh boot): diorama.intro.wire 1 / 0, applied skip / play, calls > 0,
         normal_ms recorded.
  I-B3   T_play - T_skip >= 1500 ms (the engine's normal_ms when both boots publish it, else the harness's own
         dioboot-ack -> steady span for both -- one instrument per run).
  I-B4   `bench cfg skipcam 0` + `dioboot 67 0 play rand`: applied play, own skip -- the wire beats the guest's own.
  I-B5   each of B1/B2 logs ONE BOOT line naming `intro=` and `swirl=`, and ONE "reached its command phase" line.
  I-B6a  `dioboot 67 0 wire` (the ~ menu's wire bench, flags 0x01): the "wire bench (harness): parsed map=67 ... -> boot"
         line, the BOOT line reads `intro=own`, diorama.intro.wire -1 (review ctrl F9c: bit 3 clear -> WireIntro -1).
  I-B6b  `dioboot 67 0 wire play` (flags 0x09 through the REAL ParseView): "... -> boot flags=0x09 intro=0", BOOT
         `intro=play(host)`, diorama.intro.wire 0.
  I-SP   leg S's capability (`netsync.diorama.intro.swirl_clamp`) and its levers: `bench swirl local 115` + `bench swirl
         clamp 0` -> bench_local 115, clamp 0, src bench.
  I-SW1  `dioboot 67 0` under the clamp: swirl_clamp {diorama, own 115, used 0, clamped}, dwell < 500 ms, dioramas +1,
         clamps +1, "diorama swirl 0 frames (own 115, clamped by DioramaSwirlFrames 0 (bench))", BOOT `clamp=0(bench)`.
  I-SW2  `bench swirl clamp -1` + `dioboot 67 0`: used 115, not clamped, dwell 3000..6000 ms (115 frames at 30 Hz is
         3833 ms) -- the positive control that the dwell instrument CAN read a long swirl.
  I-SW3  `bench swirl clamp 0` + a REAL own battle: {diorama false, own 115, used 115}, dwell 3000..6000, dioramas and
         clamps unchanged, "battle swirl 115 frames (the bench stand-in ...; not a diorama, so no clamp)" -- real battles
         keep their own.
  I-R    `reset` with `bench intro 0` left pulled: "battle intro mirror back ON (released with the harness)", the skipcam
         override written back, both swirl levers back to the ini, host.intro.off false, the role released.
NOT PROVEN HERE (two-machine sitting A, boxes A1 + the optional s112 box): the real watcher's `WireIntro(hostFlags)`, the
laptop's own boot-to-live time and swirl, the felt timing.

PRECONDITION. Leg S needs the diorama to boot THROUGH the swirl ([Netsync] DioramaSwirl on: the BOOT line's `clamp=`
names a number or `off`, never `none(plain fade)`); without it SW1/SW2 read "not reached".

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s110): `netsync.diorama.intro` is absent, so `bench cfg` / `bench intro` / `bench swirl`
    are NEVER sent. The s110 agent IGNORES `battle`'s `rand` (it passes args 0-1 only: a NON-random battle) and every
    `dioboot` token (a plain manual boot) -- and the driver refuses to send either there -- so the scenario sends exactly
    what that engine would do with them (`battle 67 -1`, `dioboot 67 0`) and says so in the notes: the design's
    behavioural reds without a silently-ignored step. Expected RED: I-P0, I-P1 (not sent), I-A1 (caps 0x02, no intro
    keys, no line), I-A2 (bit 3 clear), I-A3 (rand ignored: both intros play, spans equal), I-B1, I-B2 (no intro keys),
    I-B3 (both boots play: difference < 1500 ms on the harness span), I-B4 (not reached: no skipcam), I-B5 (no `intro=`
    token, no "reached" line), I-B6a (no wire-bench line, no `intro=` token), I-B6b (not reached), I-SP + I-SW1-3 (not
    reached: no s112 key), I-R (the lever was never sent). GREEN there: I-S0 only.
  * s111 without s112 (if ever deployed alone): I-SP/I-SW* red "not reached", the rest green.
  * IN-RUN, on the new DLL: `COOP_CALIBRATE=1` pulls `bench intro 0` before leg A and runs leg S1 under `bench swirl
    clamp -1`. Predicted RED, exactly: I-A1, I-A2 (no intro bits), I-B1, I-B2 (calls 0; B1 applies its own play), I-B3
    (both boots play their own), I-B4 (applied skip -- the guest's own), I-B6b (BOOT reads `intro=own`), I-SW1 (115
    frames, ~3.8 s). Still GREEN under the levers: I-A3 (the HOST's own intro is the stock expression either way), I-B5,
    I-B6a, I-SW2, I-SW3.
  * I-CAL judges the set of the engine it FINDS (_predicted, by probe -- design 6.1's calibrate-first run is on the DLL
    BEFORE the patch): no `netsync.diorama.intro` -> the old-engine set above (every check but I-S0); s111 without
    s112 -> the lever set plus I-SP, I-SW2, I-SW3; s111+s112 -> the lever set. So `COOP_CALIBRATE=1` on s110 is green
    exactly when every old-engine red fired and nothing turned green (an I-A3 or I-B6a green there is a calibration red).
  * I-R re-reads the levers WITH the role after `reset` (_coop_battle.reread_with_role): every lever key reads its rest
    value while the role is off, so the plain post-reset read could not see a stranded bench field.

DRIVER NOTE. This file probes each key itself before `bench intro|cfg|swirl` (an older driver's NETSYNC_BENCH_OPS sends
any unknown `bench` op unprobed), so it never depends on the driver's tables. The `battle ... rand` step is sent raw (an
older driver's start_battle takes no `rand`); on an engine without s111 it is never sent with `rand` (see above).

    py tools/play.py studies/test-harness/scenarios/coop_battle_intro_mirror.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_battle_intro_mirror.py --field 30602
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

#: the capability probes (HarnessAgent's header comment, protocol 5 additive; one constant each, in _coop_battle)
P111 = cb.R3_PROBES[111]                 # netsync.diorama.intro
P112 = cb.R3_PROBES[112]                 # netsync.diorama.intro.swirl_clamp
CAP_RAND, CAP_GATED, FLAG_SKIPPED, CAP_INTRO = 0x01, 0x02, 0x04, 0x08   # type-1 header flags (R3-DESIGN section 2)

INTRO_S = 45.0                           # `battle` -> the command phase (the plunge camera plays in A2)
FIGHT_S = 300.0
SPAN_A_MS = 1000                         # I-A3: the skipped intro is at least this much shorter (design 6.2)
SPAN_B_MS = 1500                         # I-B3
SWIRL_LOCAL = 115                        # the code default [Graphics] BattleSwirlFrames: the laptop stand-in
SWIRL_SHORT_MS = 500                     # I-SW1: a clamped (0-frame) swirl is done within this
SWIRL_LONG_MS = (3000, 6000)             # I-SW2/SW3: 115 frames at 30 Hz = 3833 ms

INTRO_LINE = "[NetSync] battle intro: "
PUBLISHED = "-- published in the type-1 header (bit 2)"
SKIPPED_A1 = INTRO_LINE + "SKIPPED (skip_btl_camera 0, random 1) " + PUBLISHED
PLAYED_A2 = INTRO_LINE + "PLAYED (skip_btl_camera 0, random 0) " + PUBLISHED
REACHED = "diorama reached its command phase "
#: the BOOT line (NetSyncDiorama.Boot): `start=` prints the battle_start_type_tags NAME; s111 adds `intro= swirl=`, s112
#: `clamp=` ("N", "N(bench)", "off" or "none(plain fade)" -- the one value with a space)
BOOT_RX = re.compile(r"diorama BOOT scene=(\d+) pattern=(\d+) start=(\S+)( rand)?(?: intro=(\S+) swirl=(-?\d+))?"
                     r"(?: clamp=(none\(plain fade\)|\S+))?")
WIRE_LINE = "diorama wire bench (harness): parsed map=67 pat=0 start=FIRST rand=1 nonce=77 song=156 -> boot"
SW1_LINE = f"diorama swirl 0 frames (own {SWIRL_LOCAL}, clamped by DioramaSwirlFrames 0 (bench)) -- real battles keep their own"
SW2_LINE = f"diorama swirl {SWIRL_LOCAL} frames (own {SWIRL_LOCAL}; DioramaSwirlFrames -1 (bench) keeps it)"
SW3_LINE = (f"battle swirl {SWIRL_LOCAL} frames (the bench stand-in `bench swirl local {SWIRL_LOCAL}`; not a diorama, so "
            f"no clamp)")
LEVER_OFF = "battle intro mirror OFF -- CALIBRATION"
LEVER_REL = "battle intro mirror back ON (released with the harness)"
SKIPCAM_REL = "bench cfg skip_btl_camera back to "
SWIRL_LOCAL_REL = "bench swirl local back to [Graphics] BattleSwirlFrames (released with the harness)"
SWIRL_CLAMP_REL = "bench swirl clamp back to [Netsync] DioramaSwirlFrames "
RELEASED = "(released with the harness)"


def _catalog(calibrate: bool) -> dict:
    c = {
        "I-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "I-P0": f"the engine publishes `{P111}` (memoria-patch s111) -- else `bench intro|cfg` are NEVER sent",
        "I-P1": ("`bench cfg skipcam 0` -> host.cfg.skip_btl_camera 0, AND the lever PULLED for calibration: `bench intro "
                 "0` -> host.intro.off + diorama.intro.off true, 'battle intro mirror OFF -- CALIBRATION' logged"
                 if calibrate else
                 "`bench cfg skipcam 0` -> host.cfg.skip_btl_camera 0 and its 'bench cfg skip_btl_camera ... -> 0' line; the "
                 "lever at rest (host.intro.off false)"),
        "I-A1": "A1 (`battle 67 -1 rand`): while it is up host.caps & 0x0D == 0x0D (bits 3+2 and the random bit), "
                "host.intro.published 1, own_skip 1, ONE 'battle intro: SKIPPED (skip_btl_camera 0, random 1) -- published "
                "in the type-1 header (bit 2)' line",
        "I-A2": "A2 (`battle 67`, rand 0): host.caps bit 3 set, bits 2 and 0 clear, published 0, own_skip 0, ONE 'battle "
                "intro: PLAYED (skip_btl_camera 0, random 0) -- published ...' line",
        "I-A3": f"A1's ENTER -> command-phase span is >= {SPAN_A_MS} ms shorter than A2's (the skipped plunge camera)",
        "I-B1": "B1 (`dioboot 67 0 skip`): diorama.intro.wire 1, applied 'skip', calls > 0, normal_ms >= 0",
        "I-B2": "B2 (`dioboot 67 0 play`, a fresh boot): diorama.intro.wire 0, applied 'play', calls > 0, normal_ms >= 0",
        "I-B3": f"T_play - T_skip >= {SPAN_B_MS} ms (normal_ms when both boots publish it, else the harness span for both)",
        "I-B4": "B4 (`bench cfg skipcam 0` + `dioboot 67 0 play rand`): applied 'play', own 'skip', wire 0 -- the host's "
                "choice beats the guest's own",
        "I-B5": "B1 and B2 each log ONE 'diorama BOOT' line naming `intro=` and `swirl=`, and ONE 'diorama reached its "
                "command phase N ms after the boot' line",
        "I-B6a": "B6 (`dioboot 67 0 wire`, the wire bench, flags 0x01): '... wire bench (harness): parsed map=67 pat=0 "
                 "start=FIRST rand=1 nonce=77 song=156 -> boot', the BOOT line reads `intro=own`, diorama.intro.wire -1",
        "I-B6b": "B6 (`dioboot 67 0 wire play`, flags 0x09 through the REAL ParseView): '... -> boot flags=0x09 intro=0', "
                 "BOOT `intro=play(host)`, diorama.intro.wire 0",
        "I-SP": (f"leg S: the engine publishes `{P112}` (s112); `bench swirl local {SWIRL_LOCAL}` + `bench swirl clamp "
                 + ("-1` (CALIBRATION)" if calibrate else "0`") + f" -> bench_local {SWIRL_LOCAL}, clamp "
                 + ("-1" if calibrate else "0") + ", src 'bench'"),
        "I-SW1": f"S1 (`dioboot 67 0` under clamp 0): swirl_clamp diorama, own {SWIRL_LOCAL}, used 0, clamped; dwell_ms < "
                 f"{SWIRL_SHORT_MS}; dioramas +1, clamps +1; the 'diorama swirl 0 frames (own {SWIRL_LOCAL}, clamped by "
                 f"DioramaSwirlFrames 0 (bench))' line; BOOT `clamp=0(bench)`",
        "I-SW2": f"S2 (`bench swirl clamp -1` + `dioboot 67 0`): used {SWIRL_LOCAL}, not clamped, dwell_ms in "
                 f"{SWIRL_LONG_MS[0]}..{SWIRL_LONG_MS[1]}; clamps unchanged; '... DioramaSwirlFrames -1 (bench) keeps it'; "
                 f"BOOT `clamp=off`",
        "I-SW3": f"S3 (`bench swirl clamp 0` + a REAL own battle): swirl_clamp diorama false, own {SWIRL_LOCAL}, used "
                 f"{SWIRL_LOCAL}, dwell_ms in {SWIRL_LONG_MS[0]}..{SWIRL_LONG_MS[1]}; dioramas and clamps unchanged; the "
                 f"'battle swirl {SWIRL_LOCAL} frames (the bench stand-in ...; not a diorama, so no clamp)' line",
        "I-R": "`reset` with `bench intro 0` left pulled: 'battle intro mirror back ON (released with the harness)', the "
               "skipcam override written back (its value restored), both swirl levers back to the ini (their release "
               "lines), the role released; then RE-READ WITH THE ROLE (`netsync selftest 1`, which releases nothing -- "
               "every lever key reads its rest value while the role is off): host.intro.off and diorama.intro.off false, "
               "swirl bench_local -1 / src 'ini'",
    }
    if calibrate:
        c["I-CAL"] = ("CALIBRATION: exactly the predicted reds of the engine FOUND -- without s111 every check but I-S0; on "
                      "s111 without s112 the lever set plus I-SP, I-SW2, I-SW3; on s111+s112 (`bench intro 0` + S1 under "
                      "`bench swirl clamp -1`) I-A1, I-A2, I-B1, I-B2, I-B3, I-B4, I-B6b, I-SW1")
    return c


#: COOP_CALIBRATE=1 on the s111+s112 DLL: the levers' reds (`bench intro 0` before leg A, S1 under clamp -1).
LEVER_PREDICTED = ("I-A1", "I-A2", "I-B1", "I-B2", "I-B3", "I-B4", "I-B6b", "I-SW1")
#: ...on s111 without s112: leg S cannot run ("not reached"), so I-SP, I-SW2 and I-SW3 go red beside the lever's set.
S111_PREDICTED = LEVER_PREDICTED + ("I-SP", "I-SW2", "I-SW3")
#: ...on an engine without s111 (the deployed s110 at writing): every check but I-S0 (the module note's old-engine set).
OLD_PREDICTED = tuple(c for c in _catalog(True) if c not in ("I-S0", "I-CAL"))


def _predicted(ctx) -> tuple:
    """The calibration's red set for the engine this run FOUND (design 6.1: calibrate first on the DLL before the patch)."""
    if not ctx.p111:
        return OLD_PREDICTED
    return LEVER_PREDICTED if ctx.p112 else S111_PREDICTED


# ------------------------------------------------------------------------------------------- reads
def _intro(x) -> dict:
    v = cb.path(x, P111)
    return v if isinstance(v, dict) else {}


def _sw(x) -> dict:
    v = cb.path(x, P112)
    return v if isinstance(v, dict) else {}


def _hintro(x) -> dict:
    v = cb.host(x).get("intro")
    return v if isinstance(v, dict) else {}


def _hcfg(x) -> dict:
    v = cb.host(x).get("cfg")
    return v if isinstance(v, dict) else {}


def _caps(x) -> int:
    return cb.mask_bits(cb.host(x).get("caps"))


def _boot_lines(lines) -> list:
    return [ln for ln in lines if "diorama BOOT scene=" in ln]


def _boot_fields(line: str) -> dict:
    m = BOOT_RX.search(line or "")
    if not m:
        return {}
    return {"scene": int(m.group(1)), "start": m.group(3), "rand": bool(m.group(4)), "intro": m.group(5),
            "swirl": None if m.group(6) is None else int(m.group(6)), "clamp": m.group(7)}


# ------------------------------------------------------------------------------------------- acting
def _bench(g, key: str, *args) -> tuple:
    """`netsync bench <args>` -- ONLY when ``key`` is published: an engine before the op reads `bench <op>` as `bench 1`
    and turns the FIELD-GATE bench ON (never sent there). (ok, why)."""
    if not cb.has(g.state, key):
        return False, f"never sent: the engine publishes no `{key}` (it would read `bench {args[0]}` as `bench 1`)"
    return cb.try_ns(g, "bench", *args)


def _finish(g) -> None:
    """Fight a real battle out and get back to the field (whatever leg ended where)."""
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
    cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD" and cb.free(s), 30.0, "the field after the battle")
    g.wait_frames(20)


def _own_battle(g, *, rand: bool) -> dict:
    """`battle 67 -1 [rand]` sent RAW (the driver's start_battle takes no `rand`), every publish read from the send to the
    command phase. Returns {ok, why, at, enter, normal, span (s), up (a state while the battle is up and sampled)}."""
    r = {"ok": False, "why": "", "at": cb.mark(g), "enter": None, "normal": None, "span": None, "up": None}
    if cb.poll(g, lambda s: s.ui_state == "FieldHUD" and cb.free(s), 15.0, "a playable field to leave from") is None:
        r["why"] = f"no playable field to start a battle from (ui {g.state.ui_state!r})"
        return r
    base = g.state.battle_epoch
    # an engine before s111 IGNORES `rand` (its agent passes args 0-1 only) and the driver refuses to send it there: send
    # the NON-random battle that engine would boot instead -- the calibration's behavioural red, said in the notes
    plain = rand and not cb.has(g.state, P111)
    if plain:
        g.note(f"`battle {cb.SCENE} -1 rand`: no `{P111}` -- an engine before s111 ignores `rand`; sent the non-random "
               f"battle it would boot instead")
    step = f"battle {cb.SCENE} -1" + (" rand" if rand and not plain else "")
    ok, why = cb.try_send(g, step)
    if not ok:
        r["why"] = f"`{step}` refused: {why}"
        return r
    samples, hit = cb.watch(g, lambda s: s.in_battle and s.battle_epoch > base and s.commands_enabled, INTRO_S)
    enter = next((x for x in samples if x.in_battle and x.battle_epoch > base), None)
    r["enter"], r["normal"] = enter, hit
    if hit is None:
        r["why"] = (f"`{step}`: no command phase within {INTRO_S:.0f}s (in_battle={g.state.in_battle} "
                    f"phase {g.state.battle_phase})")
        return r
    r["span"] = cb.elapsed(enter, hit) if enter is not None else None
    # the host's sample carries the intro bits only while the battle is up (NoteOwnBattleEnd resets them to -1)
    r["up"] = cb.poll(g, lambda s: s.in_battle and _caps(s) & CAP_GATED, 3.0, "a host sample of the battle") or g.state
    r["ok"] = True
    return r


def _boot(g, *tokens) -> tuple:
    """`netsync dioboot 67 0 [tokens]` (a fade refusal retried once, as _coop_battle.boot) and wait for BattleMapDebug.
    (booted, why, the verb's ack state). On an engine before s111 the agent IGNORES the tokens (a plain manual boot with
    the guest's own intro) and the driver refuses to send them: the plain boot that engine would run is sent instead --
    the calibration's behavioural red (I-B3's equal spans, I-B5/I-B6a's missing tokens), said in the notes."""
    if tokens and not cb.has(g.state, P111):
        g.note(f"`dioboot {cb.SCENE} {cb.PATTERN} {' '.join(str(t) for t in tokens)}`: no `{P111}` -- an engine before s111 "
               f"ignores the tokens; sent the plain boot it would run instead")
        tokens = ()
    why, ack = "", None
    for attempt in range(2):
        at = cb.mark(g)
        try:
            ack = cb.ns_verb(g, "dioboot", cb.SCENE, cb.PATTERN, *tokens)
            why = ""
            break
        except HarnessError as err:
            why = str(err)[:300]
            if "diorama boot REFUSED" in why:
                logged = cb.grep(cb.wait_log(g, at, cb.BOOT_REFUSED, 2.0), cb.BOOT_REFUSED, limit=240)
                if logged:
                    why = f"{why} -- log: {logged}"
            if cb.FADE_REFUSAL not in why or attempt:
                return False, f"dioboot {' '.join(str(t) for t in tokens)} refused: {why}", None
            g.wait_frames(30)
    st = cb.poll(g, cb.in_diorama, cb.BOOT_S, "the diorama (BattleMapDebug, battle.debug) to come up")
    if st is None:
        s = g.state
        return False, f"the diorama never came up (scene={s.scene!r} battle={cb.battle(s)!r})"[:300], ack
    return True, "", ack


def _dio_leg(g, field: int, *tokens) -> dict:
    """One diorama boot -> its steady command phase -> a leave. Everything a check reads is snapshotted WHILE booted
    (the intro keys read their sentinels between boots). Returns {booted, why, intro, sw, span (s), lines, left}."""
    r = {"booted": False, "why": "", "intro": {}, "sw": {}, "span": None, "lines": [], "left": False, "steady": False}
    at = cb.mark(g)
    booted, why, ack = _boot(g, *tokens)
    if not booted:
        r["why"] = why
        r["lines"] = cb.new(g, at)
        cb.back_to_field(g, field)
        return r
    r["booted"] = True
    st = cb.wait_steady(g)
    r["steady"] = st is not None
    if st is not None and ack is not None:
        r["span"] = cb.elapsed(ack, st)
    snap = st or g.state
    if cb.has(snap, P111):
        # normal_ms latches on the boot's first steady frame (LiveTick, after the client tick): read it while booted
        snap = cb.poll(g, lambda s: isinstance(_intro(s).get("normal_ms"), int) and _intro(s)["normal_ms"] >= 0, 3.0,
                       "diorama.intro.normal_ms") or g.state
        cb.wait_log(g, at, REACHED, 2.0)
    r["intro"], r["sw"] = dict(_intro(snap)), dict(_sw(snap))
    left, lwhy = cb.leave(g, field)
    r["left"] = left
    if not left:
        r["why"] = lwhy
        cb.back_to_field(g, field)
    r["lines"] = cb.new(g, at)
    return r


def _brief(r: dict) -> str:
    i = r.get("intro") or {}
    boots = _boot_lines(r.get("lines") or [])
    boot = (boots[0].split("|")[-1].strip() if boots else "none")[:200]
    span = None if r.get("span") is None else round(r["span"], 2)
    return f"intro={cb.pick(i, 'wire', 'applied', 'own', 'off', 'calls', 'normal_ms', 'swirl_frames')} span={span}s; BOOT: {boot}"


class _Ctx:
    p111 = False
    p112 = False
    skipcam0 = None          # the save's skip_btl_camera before the bench override (the release must restore it)
    skipcam_set = False
    swirl_set = False
    intro_lever_sent = False


# ------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _catalog(calibrate), finals=("I-R", "I-CAL"))
    ctx = _Ctx()
    try:
        _run(g, led, ctx, field, calibrate)
    finally:
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'intro-mirror')}")
        led.close()
        try:
            if cb.dio(g.state).get("booted"):
                cb.leave(g, field)
            if g.state.in_battle:
                _finish(g)
        except HarnessError as err:
            g.note(f"could not get back to the field before the release: {str(err)[:160]}")
        _release(g, led, ctx)
        if calibrate:
            pred = _predicted(ctx)
            g.note(f"I-CAL: s111 {'present' if ctx.p111 else 'ABSENT'}, s112 {'present' if ctx.p112 else 'ABSENT'} -- "
                   f"predicted reds {sorted(pred)}")
            led.judge_calibration("I-CAL", pred)
        led.close(final=True)


def _run(g, led: cb.Ledger, ctx: _Ctx, field: int, calibrate: bool) -> None:
    ok, why = cb.setup(g, field, label="R3 #1/#2: the battle intro mirror (s111) + the diorama swirl clamp (s112), solo"
                                       + (" -- CALIBRATION (bench intro 0, swirl clamp -1)" if calibrate else ""))
    led.check("I-S0", ok, why)
    st = g.state
    ctx.p111, ctx.p112 = cb.has(st, P111), cb.has(st, P112)
    led.check("I-P0", ctx.p111, f"netsync.diorama keys: {sorted(cb.dio(st))}" if cb.dio(st) else "no `netsync.diorama`")
    g.note(f"probe stage: {cb.stage_note(st)}; s111 {'present' if ctx.p111 else 'ABSENT'}, s112 "
           f"{'present' if ctx.p112 else 'ABSENT'} -- " + ("" if ctx.p111 else "`bench intro|cfg|swirl` will NOT be sent; ")
           + f"[Netsync] DioramaSwirl={cb.ini_value(g, 'Netsync', 'DioramaSwirl')!r} DioramaSwirlFrames="
           f"{cb.ini_value(g, 'Netsync', 'DioramaSwirlFrames')!r} [Graphics] BattleSwirlFrames="
           f"{cb.ini_value(g, 'Graphics', 'BattleSwirlFrames')!r} (read-only)")
    try:
        g.state_every(1)
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]}) -- spans read at the default cadence")
    _levers(g, led, ctx, calibrate)
    spans = _leg_a(g, led, ctx)
    led.check("I-A3", spans[0] is not None and spans[1] is not None and (spans[1] - spans[0]) * 1000.0 >= SPAN_A_MS,
              f"A1 (skip) {_ms(spans[0])} ms, A2 (play) {_ms(spans[1])} ms: difference "
              f"{_ms(None if None in spans else spans[1] - spans[0])} ms (want >= {SPAN_A_MS})")
    _leg_b(g, led, ctx, field)
    _leg_b4(g, led, ctx, field)
    _leg_b6(g, led, ctx, field)
    _leg_s(g, led, ctx, field, calibrate)


def _ms(seconds) -> int | None:
    return None if seconds is None else int(round(float(seconds) * 1000.0))


def _levers(g, led: cb.Ledger, ctx: _Ctx, calibrate: bool) -> None:
    st = g.state
    ctx.skipcam0 = _hcfg(st).get("skip_btl_camera")
    at = cb.mark(g)
    ok, why = _bench(g, P111, "cfg", "skipcam", 0)
    ctx.skipcam_set = ok
    okl, whyl = (True, "")
    if calibrate:
        okl, whyl = _bench(g, P111, "intro", 0)
        ctx.intro_lever_sent = okl
    st = cb.poll(g, lambda s: _hcfg(s).get("skip_btl_camera") == 0, 1.5, "host.cfg.skip_btl_camera 0") or g.state
    lines = cb.new(g, at)
    cfg_line = cb.count(lines, "bench cfg skip_btl_camera ") == 1 and cb.count(lines, "-> 0 for this process") == 1
    off = _hintro(st).get("off")
    if calibrate:
        good = (ok and okl and _hcfg(st).get("skip_btl_camera") == 0 and off is True and _intro(st).get("off") is True
                and cb.count(lines, LEVER_OFF) == 1)
    else:
        good = ok and _hcfg(st).get("skip_btl_camera") == 0 and cfg_line and off is False
    led.check("I-P1", good, (why or whyl) or f"host.cfg={_hcfg(st)} host.intro={_hintro(st)} (save's skipcam "
                                              f"{ctx.skipcam0!r}); {cb.grep(lines, 'bench cfg', 'intro mirror')}")


# ------------------------------------------------------------------------------------------- leg A (host)
def _leg_a(g, led: cb.Ledger, ctx: _Ctx) -> tuple:
    g.note("A1: an own battle as a RANDOM encounter with skip_btl_camera 0 -- the host skips its intro and says so")
    a1 = _own_battle(g, rand=True)
    if a1["ok"]:
        up = a1["up"]
        lines = cb.wait_log(g, a1["at"], INTRO_LINE, 2.0)
        caps, hi = _caps(up), _hintro(up)
        led.check("I-A1", (caps & (CAP_INTRO | FLAG_SKIPPED | CAP_RAND)) == (CAP_INTRO | FLAG_SKIPPED | CAP_RAND)
                  and hi.get("published") == 1 and hi.get("own_skip") == 1 and cb.count(lines, SKIPPED_A1) == 1,
                  f"host.caps=0x{caps:02X} host.intro={hi} span {_ms(a1['span'])} ms; {cb.grep(lines, INTRO_LINE)}")
    else:
        led.check("I-A1", False, f"not reached: {a1['why']}")
    _finish(g)
    g.note("A2: the same own battle, NOT random -- the host plays its intro and publishes that")
    a2 = _own_battle(g, rand=False)
    if a2["ok"]:
        up = a2["up"]
        lines = cb.wait_log(g, a2["at"], INTRO_LINE, 2.0)
        caps, hi = _caps(up), _hintro(up)
        led.check("I-A2", bool(caps & CAP_INTRO) and not (caps & (FLAG_SKIPPED | CAP_RAND)) and hi.get("published") == 0
                  and hi.get("own_skip") == 0 and cb.count(lines, PLAYED_A2) == 1,
                  f"host.caps=0x{caps:02X} host.intro={hi} span {_ms(a2['span'])} ms; {cb.grep(lines, INTRO_LINE)}")
    else:
        led.check("I-A2", False, f"not reached: {a2['why']}")
    _finish(g)
    return a1["span"], a2["span"]


# ------------------------------------------------------------------------------------------- leg B (guest)
def _leg_b(g, led: cb.Ledger, ctx: _Ctx, field: int) -> None:
    g.note("B1/B2: a diorama booted with the host's SKIP, then with its PLAY")
    b1 = _dio_leg(g, field, "skip")
    b2 = _dio_leg(g, field, "play")
    for cid, r, wire, applied in (("I-B1", b1, 1, "skip"), ("I-B2", b2, 0, "play")):
        i = r["intro"]
        if not r["booted"]:
            led.check(cid, False, f"not reached: {r['why']}")
            continue
        led.check(cid, r["steady"] and i.get("wire") == wire and i.get("applied") == applied
                  and isinstance(i.get("calls"), int) and i["calls"] > 0
                  and isinstance(i.get("normal_ms"), int) and i["normal_ms"] >= 0,
                  f"steady={r['steady']}; {_brief(r)}")
    # I-B3: one instrument for both boots
    n1, n2 = b1["intro"].get("normal_ms"), b2["intro"].get("normal_ms")
    if isinstance(n1, int) and isinstance(n2, int) and n1 >= 0 and n2 >= 0:
        t_skip, t_play, inst = n1, n2, "the engine's normal_ms"
    elif b1["span"] is not None and b2["span"] is not None:
        t_skip, t_play, inst = _ms(b1["span"]), _ms(b2["span"]), "the harness's dioboot-ack -> steady span"
    else:
        t_skip = t_play = None
        inst = "neither boot reached a measurable command phase"
    led.check("I-B3", t_skip is not None and t_play is not None and t_play - t_skip >= SPAN_B_MS,
              f"{inst}: T_skip {t_skip!r} ms, T_play {t_play!r} ms (want a difference >= {SPAN_B_MS}); harness spans "
              f"{_ms(b1['span'])}/{_ms(b2['span'])} ms")
    bad = []
    for name, r in (("B1", b1), ("B2", b2)):
        boots = _boot_lines(r["lines"])
        f = _boot_fields(boots[0]) if len(boots) == 1 else {}
        reached = cb.count(r["lines"], REACHED)
        if not (r["booted"] and len(boots) == 1 and f.get("intro") is not None and f.get("swirl") is not None and reached == 1):
            bad.append(f"{name}: {len(boots)} BOOT line(s) {f or '(no intro=/swirl= token)'}, {reached} 'reached' line(s)")
    led.check("I-B5", not bad, "; ".join(bad) or ("BOOT + reached lines: " + cb.grep(b1["lines"] + b2["lines"],
                                                                                     "diorama BOOT", REACHED)))


def _leg_b4(g, led: cb.Ledger, ctx: _Ctx, field: int) -> None:
    g.note("B4: the guest's own setting would SKIP (skipcam 0 + random), the host's wire says PLAY")
    if not ctx.p111 or not ctx.skipcam_set:
        led.check("I-B4", False, "not reached: no `bench cfg skipcam 0` (needs s111's `netsync.diorama.intro`)")
        return
    if _hcfg(g.state).get("skip_btl_camera") != 0:
        _bench(g, P111, "cfg", "skipcam", 0)
    r = _dio_leg(g, field, "play", "rand")
    i = r["intro"]
    led.check("I-B4", r["booted"] and r["steady"] and i.get("applied") == "play" and i.get("own") == "skip"
              and i.get("wire") == 0 and isinstance(i.get("calls"), int) and i["calls"] > 0,
              (r["why"] if not r["booted"] else "") or f"steady={r['steady']}; {_brief(r)}")


def _leg_b6(g, led: cb.Ledger, ctx: _Ctx, field: int) -> None:
    g.note("B6: the ~ menu's wire bench -- its 0x01 header keeps its own intro; a 0x09 header plays the host's")
    r = _dio_leg(g, field, "wire")
    boots = _boot_lines(r["lines"])
    f = _boot_fields(boots[0]) if len(boots) == 1 else {}
    wire_lines = [ln for ln in r["lines"] if WIRE_LINE in ln]
    led.check("I-B6a", r["booted"] and len(wire_lines) == 1 and wire_lines[0].rstrip().endswith("-> boot")
              and f.get("intro") == "own" and r["intro"].get("wire") == -1,
              (r["why"] if not r["booted"] else "") or f"wire-bench lines {len(wire_lines)}; BOOT fields {f}; "
                                                        f"{_brief(r)}; {cb.grep(r['lines'], 'wire bench')}")
    if not ctx.p111:
        led.check("I-B6b", False, "not reached: `dioboot ... wire play` needs s111 (an older agent ignores both tokens -- "
                                  "a plain manual boot)")
        return
    r = _dio_leg(g, field, "wire", "play")
    boots = _boot_lines(r["lines"])
    f = _boot_fields(boots[0]) if len(boots) == 1 else {}
    wire_lines = [ln for ln in r["lines"] if WIRE_LINE in ln]
    led.check("I-B6b", r["booted"] and len(wire_lines) == 1 and wire_lines[0].rstrip().endswith("-> boot flags=0x09 intro=0")
              and f.get("intro") == "play(host)" and r["intro"].get("wire") == 0,
              (r["why"] if not r["booted"] else "") or f"wire-bench lines {len(wire_lines)}; BOOT fields {f}; "
                                                        f"{_brief(r)}; {cb.grep(r['lines'], 'wire bench')}")


# ------------------------------------------------------------------------------------------- leg S (s112)
def _sw_brief(sw: dict) -> str:
    return str(cb.pick(sw, "clamp", "src", "bench_local", "diorama", "own", "used", "clamped", "dwell_ms", "swirls",
                       "dioramas", "clamps"))


def _leg_s(g, led: cb.Ledger, ctx: _Ctx, field: int, calibrate: bool) -> None:
    g.note(f"S: the diorama swirl clamp under the laptop stand-in (`bench swirl local {SWIRL_LOCAL}`: the desktop's own "
           f"[Graphics] value is 0, so nothing could be clamped there)")
    if not ctx.p112:
        led.unreached(("I-SP", "I-SW1", "I-SW2", "I-SW3"),
                      f"the engine publishes no `{P112}` (s112) -- `bench swirl` NEVER sent (an older agent reads it as "
                      f"`bench 1`)")
        return
    clamp1 = -1 if calibrate else 0
    ok1, why1 = _bench(g, P112, "swirl", "local", SWIRL_LOCAL)
    ok2, why2 = _bench(g, P112, "swirl", "clamp", clamp1) if ok1 else (False, why1)
    ctx.swirl_set = ok1 or ok2
    st = cb.poll(g, lambda s: _sw(s).get("bench_local") == SWIRL_LOCAL and _sw(s).get("clamp") == clamp1, 1.5,
                 "the swirl levers") or g.state
    sw = _sw(st)
    led.check("I-SP", ok1 and ok2 and sw.get("bench_local") == SWIRL_LOCAL and sw.get("clamp") == clamp1
              and sw.get("src") == "bench", (why1 or why2) or _sw_brief(sw))
    if not (ok1 and ok2):
        led.unreached(("I-SW1", "I-SW2", "I-SW3"), f"the swirl levers were refused -- {why1 or why2}")
        return
    # S1: the clamp shortens the stand-in's 115 frames to 0
    n0, c0 = sw.get("dioramas"), sw.get("clamps")
    r = _dio_leg(g, field)
    boots = _boot_lines(r["lines"])
    f = _boot_fields(boots[0]) if len(boots) == 1 else {}
    s1 = r["sw"]
    if r["booted"] and f.get("clamp") == "none(plain fade)":
        led.unreached(("I-SW1", "I-SW2"), "the diorama boots through the PLAIN FADE here ([Netsync] DioramaSwirl 0): no "
                                          "swirl is constructed to clamp")
    else:
        dwell = s1.get("dwell_ms")
        led.check("I-SW1", r["booted"] and s1.get("diorama") is True and s1.get("own") == SWIRL_LOCAL and s1.get("used") == 0
                  and s1.get("clamped") is True and isinstance(dwell, int) and 0 <= dwell < SWIRL_SHORT_MS
                  and isinstance(n0, int) and s1.get("dioramas") == n0 + 1 and isinstance(c0, int)
                  and s1.get("clamps") == c0 + 1 and cb.count(r["lines"], SW1_LINE) == 1 and f.get("clamp") == "0(bench)",
                  (r["why"] if not r["booted"] else "") or f"swirl_clamp {_sw_brief(s1)} (dioramas {n0!r}, clamps "
                                                            f"{c0!r} before); BOOT clamp={f.get('clamp')!r}; "
                                                            f"{cb.grep(r['lines'], 'swirl')}")
        # S2: clamp -1 = the pre-stage diorama: the stand-in's own 115 frames play (the dwell instrument's positive control)
        ok, why = _bench(g, P112, "swirl", "clamp", -1)
        sw = _sw(g.state)
        n0, c0 = sw.get("dioramas"), sw.get("clamps")
        r = _dio_leg(g, field) if ok else {"booted": False, "why": why, "sw": {}, "lines": []}
        boots = _boot_lines(r["lines"])
        f = _boot_fields(boots[0]) if len(boots) == 1 else {}
        s2 = r["sw"]
        dwell = s2.get("dwell_ms")
        led.check("I-SW2", r["booted"] and s2.get("diorama") is True and s2.get("own") == SWIRL_LOCAL
                  and s2.get("used") == SWIRL_LOCAL and s2.get("clamped") is False and isinstance(dwell, int)
                  and SWIRL_LONG_MS[0] <= dwell <= SWIRL_LONG_MS[1] and isinstance(n0, int) and s2.get("dioramas") == n0 + 1
                  and s2.get("clamps") == c0 and cb.count(r["lines"], SW2_LINE) == 1 and f.get("clamp") == "off",
                  (r["why"] if not r["booted"] else "") or f"swirl_clamp {_sw_brief(s2)} (dioramas {n0!r}, clamps {c0!r} "
                                                            f"before); BOOT clamp={f.get('clamp')!r}; "
                                                            f"{cb.grep(r['lines'], 'swirl')}")
    # S3: a REAL battle keeps its own swirl even with a clamp in force
    ok, why = _bench(g, P112, "swirl", "clamp", 0)
    sw = _sw(g.state)
    n0, c0, s0 = sw.get("dioramas"), sw.get("clamps"), sw.get("swirls")
    g.note("S3: a REAL own battle under the clamp -- it plays the stand-in's own length")
    b = _own_battle(g, rand=False) if ok else {"ok": False, "why": why, "at": cb.mark(g), "up": None}
    if b["ok"]:
        st = cb.poll(g, lambda s: isinstance(_sw(s).get("dwell_ms"), int) and _sw(s)["dwell_ms"] >= 0, 3.0,
                     "the real battle's swirl dwell") or g.state
        s3 = _sw(st)
        lines = cb.wait_log(g, b["at"], "swirl done after", 1.0)
        dwell = s3.get("dwell_ms")
        led.check("I-SW3", s3.get("diorama") is False and s3.get("own") == SWIRL_LOCAL and s3.get("used") == SWIRL_LOCAL
                  and s3.get("clamped") is False and isinstance(dwell, int) and SWIRL_LONG_MS[0] <= dwell <= SWIRL_LONG_MS[1]
                  and isinstance(s0, int) and isinstance(s3.get("swirls"), int) and s3["swirls"] > s0
                  and s3.get("dioramas") == n0 and s3.get("clamps") == c0 and cb.count(lines, SW3_LINE) == 1,
                  f"swirl_clamp {_sw_brief(s3)} (swirls {s0!r}, dioramas {n0!r}, clamps {c0!r} before); "
                  f"{cb.grep(lines, 'swirl')}")
    else:
        led.check("I-SW3", False, f"not reached: {b['why']}")
    _finish(g)


# ------------------------------------------------------------------------------------------- the release
def _release(g, led: cb.Ledger, ctx: _Ctx) -> None:
    """The intro lever left PULLED on purpose (only on an engine that has it), then `reset`: it must come back ON, logged,
    with the skipcam override written back and both swirl levers released."""
    ok, why = _bench(g, P111, "intro", 0) if ctx.p111 else (False, f"never sent: no `{P111}`")
    at = cb.mark(g)
    cb.release(g)
    st = g.state
    lines = cb.new(g, at)
    want = [LEVER_REL]
    if ctx.skipcam_set:
        want.append(SKIPCAM_REL)
    missing = [n for n in want if not any(n in ln and RELEASED in ln for ln in lines)]
    if ctx.swirl_set:
        if cb.count(lines, SWIRL_LOCAL_REL) != 1:
            missing.append(SWIRL_LOCAL_REL)
        if not any(SWIRL_CLAMP_REL in ln and RELEASED in ln for ln in lines):
            missing.append(SWIRL_CLAMP_REL)
    forced = (st.netsync or {}).get("forced")
    # the lever keys read their REST value whenever the role is off (IntroMirrorOn, BenchSwirlLocal, SwirlClampFromBench
    # are `bench field && IsSelfTestRole`): `reset` released the role, so the state above cannot see a bench field the
    # release forgot. Re-read them WITH the role (re-forced, which releases nothing) -- the release lines and this re-read
    # are the real check (review R3H-3).
    rr, rwhy = cb.reread_with_role(g) if ok else (None, "")
    rsw = _sw(rr) if rr is not None else {}
    reread_ok = (rr is not None and _hintro(rr).get("off") is False and _intro(rr).get("off") is False
                 and (not ctx.skipcam_set or _hcfg(rr).get("skip_btl_camera") == ctx.skipcam0)
                 and (not ctx.swirl_set or (rsw.get("bench_local") == -1 and rsw.get("src") == "ini")))
    good = (ok and not missing and cb.count(lines, LEVER_REL) == 1 and reread_ok and forced is False)
    led.check("I-R", good, why or f"missing lines {missing}; forced after reset={forced!r}; re-read WITH the role: "
                                  + (f"host.intro={_hintro(rr)} diorama.intro.off={_intro(rr).get('off')!r} "
                                     f"host.cfg.skip_btl_camera={_hcfg(rr).get('skip_btl_camera')!r} (want "
                                     f"{ctx.skipcam0!r}); swirl {cb.pick(rsw, 'bench_local', 'clamp', 'src')}"
                                     if rr is not None else f"none ({rwhy})")
                                  + f"; {cb.grep(lines, RELEASED)}")
