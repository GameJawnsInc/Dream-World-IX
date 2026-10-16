"""R3 GROUP 2, s133 -- THE HOST ACTION-START LANE (memoria-patch s133), the solo bench, run unattended.

THE GAP (studies/battle-coop/R3-DESIGN.md 3.3.1-3.3.2 as amended by R3-ACTION-REPLAY-AUDIT.md 2.1; the design's "s122":
group 2 was renumbered s133-s141). A guest's diorama sees every hit's NUMBERS (type-6 impacts) but no action: nothing
tells it an action began, who acts, what it plays, or when it ended. s133 is the HOST half, no visible change: every action
an own battle runs ships a START record (76 B: actor, flags, cmd/sub, tar, cursor, the host's own vfx description) BEFORE
its first impact, an END (52 B) after its last, and every impact the action's id (+6 B: the 0xA6 extension); type-1 header
flags bit 5 (0x20) says so. All additive behind the 46-byte layout (wire v14): an s110-s132 guest parses a START/END as an
impact with slots 0xFF/0xFF and returns. The guest that replays them is s134.
Lever: `netsync actbench hoststarts off|on` (off = the pre-s133 host: no START/END, no impact ids, no caps bit 5). Tape:
`netsync actbench tape rec|stop|clear|info` (the selftest loopback's type-6 frames, up to 1024) and `actbench tape dump
<from> <count>` (count 1-16: the page `netsync.battle.act.host.tape.page`, compact hex -- the tape's ONLY way out of the
engine, audit amendment 14). Read back: `netsync.battle.act.host` (published in every role; `loop` / `tape` fed by the
selftest loopback only).

PRECONDITIONS -- THE OPERATOR'S JOB (this bench writes NOTHING; it checks and refuses):
  * Memoria.ini [Netsync] Enabled = 0 (or absent). The selftest role this bench needs is refused on a live-configured
    install ("co-op is configured live (role=host)"; the shared install read Enabled = 1, Role = host at writing -- audit
    4.8). Set it by hand and relaunch; the bench never edits Memoria.ini (an ini edit mid-run re-commits the role and
    stops the bench). S133-INI reads it READ-ONLY and, when it reads 1, records itself red and runs NOTHING -- every other
    check "not reached" (a refusal, never a verdict on the engine).
  * The DLL under test deployed and the game launched on it (the orchestrator's: this bench deploys nothing).
  * COOPPARTY (studies/battle-coop/bench/coopparty.field.toml, id 30604, FF9CustomMap-msgs) registered, so the party is
    Zidane / Vivi / Garnet / Steiner (S133-PRE names what it got). Scene 306 (BSC_EF_R004) registered (stock).
  * A Vivi who knows a MANY-TARGET black magic: Fira preferred, else the first castable Blk Mag ability whose target type
    is ManyAny / ManyEnemy / AllEnemy. Whether a COOPPARTY-seeded Vivi knows one is UNVERIFIED (audit 2.1 amendment 15):
    with none, S133-MT reads red naming her abilities -- a precondition gap to report, not a verdict on s133.

THE BENCH. Field 30602 (cb.FIELD), the forced selftest role, `stateevery 1`. Battle 1 (the GREEN battle): `actbench tape
rec`, then `battle 306 <COOP_ACT_GROUP, default 4>` -- group 4 is Fang x2 (136 HP), group 2 Goblin + Fang: multi-enemy
(audit amendment 15: battle 67 is ONE enemy, so a multi-target `tar` can never span two). The command plan, by the turns
the game asks (wait_turn): Zidane Attack x2 -- the first on the first enemy, the second on ANOTHER standing enemy (the
damage spread, so no enemy falls to him alone before Vivi casts); Vivi the many-target spell on ALL enemies (cursor group
2) at her FIRST prompt while two enemies stand (a split cast cannot one-shot a 68 HP Fang), then Fire on one; Garnet a
Potion on herself; then a Defend from whoever is asked next (Steiner, or anyone); every other prompt Defends (so the
enemies act) until the plan is done; then `fight` to the victory. `actbench tape stop`, the tape paged out (`tape dump <i>
16`) and judged OFFLINE through tools/harness/battlewire.py. Battle 2 (the lever, L1): `hoststarts off` + a new tape,
Attack to the victory, the tape paged out; `hoststarts on`.
A SHORT FIGHT (the dice; there is no HP lever -- audit amendment 15) can leave a planned action's check red with no engine
verdict in it: MT (fewer than two enemies standing at Vivi's first prompt), AT (Zidane asked fewer than twice), POT (Garnet
never asked), EN (no enemy acted before the end). Each names the plan's progress in its detail; B0 stays green.

WHAT IS PROVEN (S133-*):
  INI   precondition: [Netsync] Enabled reads 0 / absent (READ-ONLY) -- else NOTHING runs.
  S0    the harness forced the selftest role (Memoria.ini untouched).
  P0    the probe: `netsync.battle.act.host` is published -- else `actbench` is NEVER sent (fails closed).
  PROOF the selftest proof block's line reads exactly 'action lane selftest: OK (30 rows)' -- no FAIL line.
  P1    `actbench tape rec` -> tape.state 'rec', 0 frames, the RECORDING line (COOP_CALIBRATE=1: `hoststarts off` first ->
        lever_off true, on false, the 'OFF -- CALIBRATION' line).
  PRE   precondition: battle 1 seats Zidane, Vivi and Garnet and 2+ enemies.
  B0    THE CONTROL (both DLLs): battle 1 ended in a victory, back on the field, no 'action frame failed to parse
        (codec drift)' line -- the s110-s132 loopback reads every type-6 frame either way -- and, over battle 1's window, no
        'pump failed' line and no exception line (s133's loopback work runs inside SelfTestPump's catch-all: a throw there
        would leave only that line). (How far the plan got is in its detail; each planned action is judged by its own check
        -- a plan cut short by the dice is never B0's red.)
  ON    every own-battle publish with a lane read during battle 1: act.host.on true, lever_off false, host.caps & 0x20 and
        peer.caps & 0x20, act.host.nonce == peer.nonce.
  AT    Zidane's two Attack STARTs (his slot, the cmd/sub the driver resolved and sent -- stock: cmd 1, sub 176) are both
        kind 3 (special) with the same num.
  EN    at least one enemy START (no player bit) of kind 2 (enemy) whose num == its sub.
  MT    the many-target cast's START (Vivi's slot, its sub) has a `tar` spanning 2+ enemy bits.
  POT   Garnet's Potion START (the cmd/sub sent -- stock: cmd 14, sub 236) is kind 3.
  VFX   the describe check (audit D2): vfx.checked + vfx.unchecked == starts - scripted > 0, drift 0, why null, the kinds
        sum to starts, and no 'describe drift' line.
  PAIR  starts == loop.starts > 0, ends == loop.ends > 0, loop.paired == ends, orphans 0, caster_mismatch 0, loop.ext_bad 0,
        noid_impacts 0, dropped 0 and wire_dropped 0 (the two 64-frame budgets: `dropped` is the per-tick buffer's,
        `wire_dropped` the transport's -- it reads 0 under the selftest loopback, which has no transport, so neither is
        evidence that a real link's FIFO arrived whole), open 0, no_end 0 and cut 0 (both books), no 'never ENDed' line, and
        the 'own battle (nonce N) closed -- S START(s) ...' summary naming the same STARTs and ENDs.
  TAPE  offline over the dumped tape: every frame decodes; every START is 76 bytes and every END 52, and what an s110-s132
        guest reads of either is INERT byte for byte -- slots 0xFF/0xFF, every figure and raw 0 (a resolvable slot's zero
        raws would read as lethal there), flags 0x04 / 0x08 alone; every non-stat impact 52 bytes, ext kind 1; stat ticks 46
        bytes; every impact's legacy head is an impact's (each slot < 8 or 0xFF, one < 8), names an id a START on the tape
        carries, repeats that START's cmd/sub and is cast by its actor or 0xFF, and every END repeats its START's cmd/sub
        (battlewire.act_identity_violations); the seqs keep the STATE-WRITE<=>HORIZON law -- impacts and stat ticks consume
        the clock strictly upward, a START/END stamps it unconsumed: after the last consumed seq, at or before the next
        (battlewire.act_horizon_violations); every frame's nonce byte == act.host.nonce (MARKER 1: this battle's own frames,
        nothing older); the STARTs counted == tape.starts == act.host.starts; overflow 0.
  ORDER the FIFO promise over the tape: every impact naming id k lies between START k and END k, every END after its START.
  DUMP  the egress: pages of 16 tile the tape exactly (from / count / total / i), `tape dump <total> 1` is refused in the
        engine's words, and `tape info`'s summary line counts what battlewire counts over the dumped bytes.
  STOP  `actbench tape stop` -> state 'stopped', the frames kept, the 'stopped -- N frame(s), S START(s)' line.
  L1    THE LEVER (every run): `hoststarts off` (the CALIBRATION line) + a new tape + battle 2 to the victory -> starts 0,
        ends 0, ext_impacts 0, every kind 0, on false, lever_off true, caps bit 5 on no publish read, loop.impacts > 0 and
        every taped impact 46 bytes with battle 2's nonce (MARKER 2, != MARKER 1), no 'pump failed' or exception line over
        battle 2's window; `hoststarts on` -> on true and the 'action STARTs ON' line.
  R     `reset` with `hoststarts off` + `tape rec` left set: 'action STARTs back ON (released with the harness)' + 'action
        tape cleared (N frame(s); released with the harness)'; then RE-READ WITH THE ROLE (cb.reread_with_role): lever_off
        false, tape 'off', 0 frames, no page.
NOT PROVEN HERE: a scripted sequence (StartBtlSeq: `scripted`, the takeover / re-entry -- no stock scene 306 script runs
one), a mid-action teardown (`cut`), the 64-frame budgets under a burst or a stalled link (`dropped`; `wire_dropped` needs
a real transport), a stat tick (no Poison here), an unresolvable actor, the old engine (`vfx.unchecked`), a real guest's
reading of any of it (s134; the tape bench), and every s110-s132 GUEST's non-reaction to START/END frames (a mixed-DLL box
of the next two-machine sitting).

CALIBRATION -- a check that cannot fail is not a check.
  * THE DEPLOYED DLL AT WRITING (s132) -- and any engine before s133: `act.host` is absent, so P0 is RED and `actbench` is
    NEVER sent (the act probe fails closed). Battle 1 still runs its plan as the control. RED, exactly: P0, PROOF (no
    'action lane' line), P1 (never sent), ON (no key; caps bit 5 never set), AT, EN, MT, POT, VFX, PAIR, TAPE, ORDER, DUMP,
    STOP, L1, R (not reached). GREEN there, exactly: INI, S0, PRE, B0 -- 4 of 20. COOP_CALIBRATE=1 on such an engine
    judges exactly that red set as S133-CAL.
  * IN-RUN, on the s133 DLL: L1 is the lever's red every run (judged as its own check). COOP_CALIBRATE=1 also pulls
    `hoststarts off` BEFORE battle 1 (P1 then asserts the lever took); predicted reds, exactly: ON, AT, EN, MT, POT, VFX,
    PAIR, TAPE, ORDER (no START, no END, no id: every impact 46 bytes, nothing to pair or order, nothing described) --
    INI, S0, P0, PROOF, P1, PRE, B0, DUMP, STOP, L1 and R stay green. S133-CAL judges that set (the run is red by design).
  * THE STAND-IN (tools/harness/fakegame.py, cap `actstart`) models the lane through battlewire.ActHostLane but cannot run
    this plan (its battles ignore the scene and group -- one enemy, no Vivi / Garnet, its own command ids): never read
    S133-CAL offline. Its tests (ff9mapkit/tests/test_harness_netsync.py) pin the codec, the books, the verb and the keys;
    the engine is the calibration.

RE-BASELINES this DLL brings to OTHER benches: none of their checks (design 6.1: "own battles emit more type-6 frames;
nothing else changes"). Every caps reader masks (`& 2`, `& ~0x3C`); the 'own battle (nonce N) closed' summary line is new
in every selftest own battle's log. Regression set after the deploy (design 6.1 + audit amendment 1): the battle set,
every earlier R3 scenario, coop_handback_live and coop_cut_hold.

    py tools/play.py studies/test-harness/scenarios/coop_action_host.py --field 30602
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_action_host.py --field 30602
    COOP_ACT_GROUP=2 py tools/play.py studies/test-harness/scenarios/coop_action_host.py --field 30602
  PowerShell has no per-launch form: a `$env:` value PERSISTS in that shell, so clear it after the calibrated run:
    $env:COOP_CALIBRATE='1'; py tools/play.py studies/test-harness/scenarios/coop_action_host.py --field 30602
    Remove-Item Env:COOP_CALIBRATE -ErrorAction SilentlyContinue
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

try:                                                       # play.py puts tools/ on sys.path before it loads a scenario
    from harness import battlewire as BW                   # noqa: E402
except ImportError:                                        # pragma: no cover - imported outside the driver
    sys.path.insert(0, str(cb.REPO / "tools"))
    from harness import battlewire as BW                   # noqa: E402

HarnessError = cb.HarnessError

PROBE = cb.R3_PROBES[133]                  # netsync.battle.act.host: `actbench`; absent = a host that ships no STARTs
SCENE = 306                                # BSC_EF_R004: multi-enemy groups (audit amendment 15)
GROUP = int(os.environ.get("COOP_ACT_GROUP", "4") or 4)   # 4 = Fang x2 (136 HP), 2 = Goblin + Fang
FIGHT_S = 300.0
TURN_S = 90.0
INTRO_S = 40.0
PAGE = BW.ACT_TAPE_PAGE_MAX                # 16 frames a `tape dump` page
CMD_ATTACK, ATTACK_SUB = BW.CMD_ATTACK_ID, BW.ABILITY_ATTACK_ID   # BattleCommandId.Attack, BattleAbilityId.Attack (the
CMD_ITEM, POTION = BW.CMD_ITEM_ID, BW.ITEM_POTION_ID               # fallbacks: AT / POT filter by what `act` sent)
MANY_TARGET_TYPES = (3, 5, 8)              # TargetType ManyAny / ManyEnemy / AllEnemy: a cast that can take the enemy group
CURSOR_ALL_ENEMIES = 2                     # the HUD's CursorGroup for the whole enemy side (session._GROUP_TARGETS)
PROOF = "action lane selftest:"
PROOF_OK = BW.proof_ok(BW.PROOF_ACTION, BW.ACTION_SELFTEST_ROWS).rstrip()
LEVER_OFF_LINE = BW.LOG_ACT_LEVER_OFF.split("] ", 1)[1]
LEVER_ON_LINE = BW.LOG_ACT_LEVER_ON.split("] ", 1)[1]
RECORDING = BW.LOG_ACT_TAPE_REC.split("] ", 1)[1]
STOPPED = BW.LOG_ACT_TAPE_STOPPED.split("] ", 1)[1]
REL_LEVER = BW.LOG_ACT_LEVER_RELEASED.split("] ", 1)[1]
REL_TAPE = "frame(s); released with the harness)"
CLOSED = BW.LOG_ACT_CLOSED.split("] ", 1)[1]
CODEC_DRIFT = "an action frame failed to parse (codec drift)"
PUMP_FAILED = "pump failed"                # '[NetSync] battle (selftest) pump failed': a throw in a pump's catch-all


def _catalog(calibrate: bool) -> dict:
    c = {
        "S133-INI": "precondition: Memoria.ini [Netsync] Enabled reads 0 (or absent), READ-ONLY -- the operator's job; "
                    "with Enabled = 1 the selftest role is refused and this bench runs NOTHING",
        "S133-S0": "the harness forced the selftest role for this process (Memoria.ini untouched)",
        "S133-P0": f"the engine publishes `{PROBE}` (memoria-patch s133) -- else `actbench` is never sent (fails closed)",
        "S133-PROOF": f"the selftest proof block's line reads exactly '{PROOF_OK}' -- no FAIL line",
        "S133-P1": ("the lever is PULLED for calibration: `actbench hoststarts off` -> lever_off true, on false, the 'OFF -- "
                    "CALIBRATION' line; then `actbench tape rec` -> state 'rec', 0 frames, the RECORDING line" if calibrate
                    else "`actbench tape rec` -> tape.state 'rec', 0 frames, page null, the RECORDING line"),
        "S133-PRE": f"precondition: battle 1 (`battle {SCENE} {GROUP}`) seats Zidane, Vivi and Garnet and 2+ enemies",
        "S133-B0": "control (both DLLs): battle 1 ended in a victory, back on the field, no 'codec drift', 'pump failed' "
                   "or exception line in its window",
        "S133-ON": "every own-battle publish read in battle 1: act.host.on true, lever_off false, host.caps & 0x20 and "
                   "peer.caps & 0x20, act.host.nonce == peer.nonce",
        "S133-AT": "Zidane's two Attack STARTs (the cmd/sub sent; stock 1/176) are both kind 3 (special) with the same num "
                   "(a short fight can leave it red: Zidane asked fewer than twice)",
        "S133-EN": "an enemy START (no player bit) of kind 2 (enemy) whose num == its sub (a short fight can leave it red: "
                   "no enemy acted)",
        "S133-MT": "the many-target cast's START (Vivi, its sub) has a tar spanning 2+ enemy bits (a short fight can leave "
                   "it red: fewer than two enemies at her first prompt)",
        "S133-POT": "Garnet's Potion START (the cmd/sub sent; stock 14/236) is kind 3 (special) (a short fight can leave it "
                    "red: Garnet never asked)",
        "S133-VFX": "the describe check: vfx.checked + unchecked == starts - scripted > 0, drift 0, why null, kinds sum to "
                    "starts, no 'describe drift' line",
        "S133-PAIR": "starts == loop.starts > 0, ends == loop.ends > 0, paired == ends, orphans 0, caster_mismatch 0, ext_bad "
                     "0, noid_impacts 0, dropped 0 and wire_dropped 0 (budgets only: no transport under selftest), open 0, "
                     "no_end 0, cut 0, no 'never ENDed' line, the 'own battle (nonce N) closed' summary naming the same "
                     "STARTs and ENDs",
        "S133-TAPE": "the dumped tape offline: every START 76 B / END 52 B with an INERT head to an s110-s132 reader (slots "
                     "0xFF/0xFF, figures and raws 0, flags 0x04 / 0x08); every non-stat impact 52 B (ext kind 1), its head "
                     "an impact's, its id a taped START's, that START's cmd/sub and actor; every END its START's cmd/sub; the "
                     "seqs keep the HORIZON law; stat ticks 46 B; every frame's nonce == act.host.nonce; STARTs == "
                     "tape.starts == act.host.starts; overflow 0",
        "S133-ORDER": "the FIFO promise: every impact naming id k lies between START k and END k, every END after its START",
        "S133-DUMP": "the egress: pages of 16 tile the tape exactly; `tape dump <total> 1` refused in the engine's words; "
                     "`tape info`'s line counts what battlewire counts over the dumped bytes",
        "S133-STOP": "`actbench tape stop` -> state 'stopped', the frames kept, the 'stopped -- N frame(s), S START(s)' line",
        "S133-L1": "the lever (every run): `hoststarts off` + a new tape + battle 2 -> starts 0, ends 0, ext_impacts 0, kinds "
                   "0, on false, caps bit 5 never, every taped impact 46 B with battle 2's nonce, no 'pump failed' or "
                   "exception line; `hoststarts on` -> on true and the 'action STARTs ON' line",
        "S133-R": "`reset` with `hoststarts off` + `tape rec` left set: the two 'released with the harness' lines; RE-READ "
                  "WITH THE ROLE: lever_off false, tape 'off', 0 frames, no page",
    }
    if calibrate:
        c["S133-CAL"] = ("CALIBRATION: exactly the predicted checks are red -- on an engine without `act.host` every check "
                         "but INI/S0/PRE/B0; on the s133 DLL under `hoststarts off` exactly ON, AT, EN, MT, POT, VFX, PAIR, "
                         "TAPE, ORDER")
    return c


#: the checks battle 1's tape and keys decide (not reached together when the probe fails closed or battle 1 never ran)
LANE_CHECKS = ("S133-ON", "S133-AT", "S133-EN", "S133-MT", "S133-POT", "S133-VFX", "S133-PAIR", "S133-TAPE", "S133-ORDER",
               "S133-DUMP", "S133-STOP")
#: COOP_CALIBRATE=1 on the s133 DLL: `hoststarts off` before battle 1 -- nothing STARTs, nothing ENDs, no id.
LEVER_PREDICTED = ("S133-ON", "S133-AT", "S133-EN", "S133-MT", "S133-POT", "S133-VFX", "S133-PAIR", "S133-TAPE",
                   "S133-ORDER")
#: COOP_CALIBRATE=1 on an engine without `act.host` (the deployed s132, or older): all but INI, S0, PRE and B0.
OLD_PREDICTED = tuple(c for c in _catalog(True) if c not in ("S133-INI", "S133-S0", "S133-PRE", "S133-B0", "S133-CAL"))


# ------------------------------------------------------------------------------------------------- reads
def _num(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _sub(d, key: str) -> dict:
    v = d.get(key) if isinstance(d, dict) else None
    return v if isinstance(v, dict) else {}


def _act(x) -> dict:
    return _sub(_sub(cb.nsb(x), "act"), "host")


def _loop(x) -> dict:
    return _sub(_act(x), "loop")


def _tape(x) -> dict:
    return _sub(_act(x), "tape")


def _brief(x) -> str:
    a = _act(x)
    keys = ('on', 'lever_off', 'nonce', 'starts', 'ends', 'ext_impacts', 'noid_impacts', 'open', 'dropped', 'wire_dropped')
    return (f"act.host={cb.pick(a, *keys)}"
            f" loop={cb.pick(_loop(x), 'starts', 'ends', 'paired', 'orphans', 'caster_mismatch', 'ext_bad')}"
            f" tape={cb.pick(_tape(x), 'state', 'frames', 'starts', 'overflow')} host.caps={cb.host(x).get('caps')!r}")


#: the party members the plan names, by their published names (Garnet answers to her later name too)
NAMES = {"zidane": ("zidane",), "vivi": ("vivi",), "garnet": ("garnet", "dagger")}


def _unit_named(x, name: str) -> dict | None:
    want = NAMES.get(name, (name,))
    return next((u for u in cb.units(x, player=True) if str(u.get("name") or "").strip().lower() in want), None)


def _enemy_mask(x) -> int:
    m = 0
    for u in cb.units(x, player=False):
        m |= int(u.get("id") or 0)
    return m


def _living_enemies(x) -> list:
    return [u for u in cb.units(x, player=False) if u.get("alive") and u.get("targetable", True)]


# ------------------------------------------------------------------------------------------------- acting
def _act_verb(g, *args) -> tuple:
    """`netsync actbench <args>` -- (the state after it or None, why-not). The caller probes `act.host` first."""
    try:
        return cb.ns_verb(g, "actbench", *args), ""
    except (HarnessError, AttributeError) as err:
        return None, str(err)[:400]


def _dump_all(g, total: int) -> tuple:
    """The whole tape, paged out (`tape dump <i> 16`): ([(i, ms, bytes)], [page dicts], why-not)."""
    frames, pages = [], []
    while len(frames) < total:
        start = len(frames)
        st, why = _act_verb(g, "tape", "dump", start, PAGE)
        if st is None:
            return frames, pages, f"`tape dump {start} {PAGE}` refused: {why}"
        hit = cb.poll(g, lambda s: _num(_sub(_tape(s), "page").get("from")) == start, 5.0, f"the tape page from {start}")
        page = _sub(_tape(hit), "page") if hit is not None else {}
        got = BW.act_tape_page_frames(page)
        if not got:
            return frames, pages, f"the page from {start} never landed ({_brief(g.state)})"
        pages.append(page)
        frames.extend(got)
    return frames, pages, ""


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


def _many_target(menu: dict) -> dict | None:
    """Vivi's many-target black magic: Fira when it is castable, else the first castable ability whose TargetType can take
    the enemy group -> {cmd, sub, name, target}; None = none offered."""
    commands = {c.get("menu"): c for c in menu.get("commands") or []}
    castable = [a for a in menu.get("abilities") or [] if a.get("enabled", True)
                and int(a.get("target", -1)) in MANY_TARGET_TYPES and a.get("menu") in commands]
    pick = next((a for a in castable if str(a.get("name") or "").strip().lower() == "fira"), None) or \
        (castable[0] if castable else None)
    if pick is None:
        return None
    return {"cmd": int(commands[pick["menu"]]["id"]), "sub": int(pick["sub"]), "name": pick.get("name"),
            "target": int(pick.get("target", -1))}


def _single_fire(menu: dict) -> dict | None:
    commands = {c.get("menu"): c for c in menu.get("commands") or []}
    a = next((a for a in menu.get("abilities") or [] if str(a.get("name") or "").strip().lower() == "fire"
              and a.get("enabled", True) and a.get("menu") in commands), None)
    return None if a is None else {"cmd": int(commands[a["menu"]]["id"]), "sub": int(a["sub"]), "name": a.get("name")}


def _commit(g, slot: int, cmd: int, sub: int, tar: int, cursor: int) -> None:
    """A raw `battlecmd` and the closed loop on its outcome (the slot stops being asked), as Session.act does."""
    g.battle_command(slot, cmd, sub=sub, target=tar, cursor=cursor)
    cb.poll(g, lambda s: s.turn_slot != slot or s.battle_result != 0 or not s.in_battle, 20.0,
            f"slot {slot} to stop being asked")


def _plan(g, ctx: dict, samples: list) -> str:
    """Battle 1's command plan, turn by turn (the game's own asks): Zidane Attack x2 (the first on the first enemy, the
    second on ANOTHER standing one -- the damage spread), Vivi's many-target spell on every enemy at her first prompt while
    two stand, then Fire; Garnet a Potion on herself; then one Defend; every other prompt Defends. Each prompt's state is
    sampled for ON; each `act` records the cmd/sub it sent (AT / POT filter by them). Returns why it stopped early ('' = the
    plan ran)."""
    st = g.state
    z, v, gar = (_unit_named(st, n) for n in ("zidane", "vivi", "garnet"))
    done = {"attacks": 0, "many": False, "fire": False, "potion": False, "defend": False}
    ctx["plan"] = done
    first = cb.first_enemy(st)
    target_slot = int(first.get("slot")) if first else -1
    for _turn in range(80):
        if all((done["attacks"] >= 2, done["many"] or ctx.get("no_many"), done["fire"] or ctx.get("no_fire"),
                done["potion"], done["defend"])):
            return ""
        try:
            slot = g.wait_turn(timeout=TURN_S)
        except HarnessError as err:
            return f"the battle stopped asking ({str(err)[:160]})"
        s = g.state
        samples.append(s)
        live = _living_enemies(s)
        if not any(int(u.get("slot", -1)) == target_slot for u in live) and live:
            target_slot = int(live[0].get("slot"))
        try:
            if z is not None and slot == int(z["slot"]) and done["attacks"] < 2:
                aim = target_slot
                if done["attacks"] == 1:                  # the second on ANOTHER standing enemy: the damage spread
                    other = [u for u in live if int(u.get("slot", -1)) != ctx.get("attack_target")]
                    aim = int(other[0]["slot"]) if other else target_slot
                sent = g.act("Attack", slot=slot, target=aim)
                done["attacks"] += 1
                ctx.setdefault("attack_target", aim)
                ctx.setdefault("attack_sent", (int(sent["id"]), int(sent["sub"])))
            elif v is not None and slot == int(v["slot"]) and not done["many"] and not ctx.get("no_many"):
                menu = g.menus(slot)
                spell = _many_target(menu)
                if spell is None or len(live) < 2:
                    ctx["no_many"] = ("Vivi offers no castable many-target black magic (abilities "
                                      f"{[a.get('name') for a in menu.get('abilities') or []]}) -- a PRECONDITION gap"
                                      if spell is None else f"only {len(live)} enemy standing when Vivi was asked")
                    g.act("Defend", slot=slot)
                else:
                    mask = 0
                    for u in live:
                        mask |= int(u["id"])
                    _commit(g, slot, spell["cmd"], spell["sub"], mask, CURSOR_ALL_ENEMIES)
                    done["many"] = True
                    ctx["many"] = dict(spell, mask=mask)
            elif (v is not None and slot == int(v["slot"]) and (done["many"] or ctx.get("no_many"))
                  and not done["fire"] and not ctx.get("no_fire") and live):
                spell = _single_fire(g.menus(slot))
                if spell is None:
                    ctx["no_fire"] = True
                    g.act("Defend", slot=slot)
                else:
                    _commit(g, slot, spell["cmd"], spell["sub"], int(live[0]["id"]), 0)
                    done["fire"] = True
                    ctx["fire"] = spell
            elif gar is not None and slot == int(gar["slot"]) and not done["potion"]:
                sent = g.act("Potion", slot=slot, target=slot)
                done["potion"] = True
                ctx["potion_sent"] = (int(sent["id"]), int(sent["sub"]))
            elif done["potion"] and done["attacks"] >= 2 and not done["defend"]:
                g.act("Defend", slot=slot)
                done["defend"] = True
                ctx["defend_slot"] = slot
            else:
                g.act("Defend", slot=slot)
        except HarnessError as err:
            if not g.state.in_battle:
                return f"the battle ended mid-plan ({str(err)[:120]})"
            g.note(f"plan step refused on slot {slot}: {str(err)[:200]}")
    return "the plan did not finish in 80 prompts"


# ------------------------------------------------------------------------------------------------- the run
def run(g, field: int = cb.FIELD):
    calibrate = cb.CALIBRATE
    led = cb.Ledger(g, _catalog(calibrate), finals=("S133-R", "S133-CAL"))
    ctx = {"probe": False, "ini_ok": False}
    try:
        _run(g, led, field, calibrate, ctx)
    finally:
        g.note(f"logs archived: {_archive_logs(g, 'action-host')}")
        led.close()                                        # every leg check is recorded before the judge reads them
        if ctx["ini_ok"]:
            _release(g, led, ctx)
        else:
            led.unreached(("S133-R",), "the precondition refused the run (S133-INI): nothing was set, nothing to release")
        if calibrate:
            led.judge_calibration("S133-CAL", LEVER_PREDICTED if ctx["probe"] else OLD_PREDICTED)
        led.close(final=True)


def _archive_logs(g, tag: str) -> str:
    """BOTH logs into the run's artifact dir NOW (design 6.1): Memoria.log (cb.archive_log) and Unity's output_log.txt."""
    out = [cb.archive_log(g, tag)]
    try:
        src = g.unity_log()
        dest_dir = getattr(g, "scenario_dir", None) or g.run_dir
        if src is not None and dest_dir is not None:
            dest = Path(dest_dir) / f"output_log-{tag}.txt"
            shutil.copy2(src, dest)
            out.append(str(dest))
        else:
            out.append("no output_log.txt to archive")
    except (OSError, AttributeError) as err:
        out.append(f"output_log archive failed: {err}")
    return "; ".join(out)


def _ini_guard(g) -> tuple:
    """S133-INI: [Netsync] Enabled as the engine reads it (``.Trim() == "1"``), READ-ONLY. (ok, detail)."""
    raw = cb.ini_value(g, "Netsync", "Enabled")
    role = cb.ini_value(g, "Netsync", "Role")
    if raw is not None and raw.strip() == "1":
        return False, (f"Memoria.ini [Netsync] Enabled = 1 (Role = {role!r}): the selftest role is refused on a "
                       f"live-configured install -- set Enabled = 0 BY HAND (the operator's job: this bench never writes "
                       f"Memoria.ini) and relaunch, then run again")
    return True, (f"[Netsync] Enabled = {raw!r} (absent = the engine's default 0)" if raw is not None else
                  "[Netsync] Enabled absent or unreadable: the engine's default (0) -- the selftest role decides at S0")


def _run(g, led: cb.Ledger, field: int, calibrate: bool, ctx: dict) -> None:
    ok, why = _ini_guard(g)
    led.check("S133-INI", ok, why)
    if not ok:
        led.close(f"refused to run: {why}")
        return
    ctx["ini_ok"] = True
    if Path(BW.__file__).resolve().is_relative_to(cb.REPO):
        g.note(f"battlewire: {BW.__file__} (this worktree)")
    else:
        g.note(f"battlewire: {BW.__file__} -- NOT this worktree ({cb.REPO}): the offline judges run someone else's codec")
    ok, why = cb.setup(g, field, label=f"R3 s133: the host action-start lane, solo (scene {SCENE} group {GROUP})"
                                       + (" -- CALIBRATION (actbench hoststarts off)" if calibrate else ""))
    led.check("S133-S0", ok, why)
    if not ok:
        led.close(f"the selftest role was refused -- {why}")
        return
    st = g.state
    have = ctx["probe"] = cb.has(st, PROBE)
    led.check("S133-P0", have, f"act.host keys: {sorted(_act(st))}" if have else
              f"no `{PROBE}` (an engine before s133: `actbench` will NOT be sent)")
    g.note(f"probe stage: {cb.stage_note(st)}; act.host {'present' if have else 'ABSENT'}")
    _leg_proof(g, led)
    try:
        g.state_every(1)
    except (HarnessError, AttributeError) as err:
        g.note(f"stateevery 1 refused ({str(err)[:120]}) -- every publish read at the default cadence")
    if have:
        _leg_p1(g, led, calibrate)
    else:
        led.unreached(("S133-P1",), f"`{PROBE}` is absent: `actbench` was never sent")
    _battle_1(g, led, field, ctx)
    if have:
        _leg_l1(g, led, ctx)
    else:
        led.unreached(LANE_CHECKS + ("S133-L1",), f"`{PROBE}` is absent: an engine before s133 (the act probe fails "
                                                  f"closed; `actbench` was never sent)")


def _leg_proof(g, led: cb.Ledger) -> None:
    """The selftest proof block logs once per process, on the first selftest tick on a field (setup gives it one)."""
    proof = cb.poll(g, lambda s: cb.count(cb.log_lines(g), PROOF) >= 1, 8.0, "the proof block's action-lane line")
    lines = [ln for ln in cb.log_lines(g) if PROOF in ln]
    last = lines[-1] if lines else ""
    failed = [ln for ln in lines if "action lane selftest: FAIL" in ln]
    led.check("S133-PROOF", proof is not None and PROOF_OK in last and not failed,
              (last.split("|", 2)[-1].strip()[-300:] if last else
               "no 'action lane selftest' line (an engine before s133 has no ActionSelfTest)")
              + (f"; FAIL lines: {len(failed)}" if failed else "") + f"; want '{PROOF_OK}'")


def _leg_p1(g, led: cb.Ledger, calibrate: bool) -> None:
    at = cb.mark(g)
    parts, ok = [], True
    if calibrate:
        st, why = _act_verb(g, "hoststarts", "off")
        lines = cb.wait_log(g, at, LEVER_OFF_LINE, 1.5)
        st = cb.poll(g, lambda s: _act(s).get("lever_off") is True, 1.5, "act.host.lever_off") or g.state
        a = _act(st)
        ok = not why and a.get("lever_off") is True and a.get("on") is False and cb.count(lines, LEVER_OFF_LINE) == 1
        parts.append(why or f"lever {cb.pick(a, 'lever_off', 'on')}; {cb.grep(lines, 'action STARTs')}")
    at = cb.mark(g)
    st, why = _act_verb(g, "tape", "rec")
    lines = cb.wait_log(g, at, RECORDING, 1.5)
    st = cb.poll(g, lambda s: _tape(s).get("state") == "rec", 1.5, "act.host.tape.state 'rec'") or g.state
    t = _tape(st)
    ok = ok and not why and t.get("state") == "rec" and t.get("frames") == 0 and t.get("page") is None \
        and cb.count(lines, RECORDING) == 1
    parts.append(why or f"tape {cb.pick(t, 'state', 'frames', 'page')}; {cb.grep(lines, 'action tape')}")
    led.check("S133-P1", ok, "; ".join(parts))


# ------------------------------------------------------------------------------------------------- battle 1
def _battle_1(g, led: cb.Ledger, field: int, ctx: dict) -> None:
    have = ctx["probe"]
    g.note(f"battle 1: `battle {SCENE} {GROUP}` with the tape recording -- the GREEN plan")
    if cb.poll(g, lambda s: cb.free(s) and s.ui_state == "FieldHUD" and not s.in_battle, 30.0, "a playable field") is None:
        led.close(f"not on a playable field before battle 1 (ui {g.state.ui_state!r})")
        return
    at = cb.mark(g)
    try:
        st = g.start_battle(SCENE, group=GROUP)
    except HarnessError as err:
        led.unreached(("S133-PRE", "S133-B0") + LANE_CHECKS, f"`battle {SCENE} {GROUP}` did not start: {str(err)[:200]}")
        return
    intro, en = cb.watch_from(g, st, lambda s: s.commands_enabled, INTRO_S)
    st = en or g.state
    names = {k: _unit_named(st, k) for k in ("zidane", "vivi", "garnet")}
    foes = cb.units(st, player=False)
    pre = all(names.values()) and len(foes) >= 2
    led.check("S133-PRE", pre, f"party {[(u.get('slot'), u.get('name')) for u in cb.units(st, player=True)]}; enemies "
                               f"{[(u.get('slot'), u.get('name'), u.get('id')) for u in foes]}")
    ctx["slots"] = {k: (int(u["slot"]) if u else None) for k, u in names.items()}
    ctx["enemy_mask"] = _enemy_mask(st)
    samples = list(intro)
    stop = _plan(g, ctx, samples) if pre else "the precondition failed (S133-PRE)"
    if stop:
        g.note(f"the plan stopped early: {stop}")
    result = None
    try:
        if g.state.in_battle:
            result = g.fight(timeout=FIGHT_S, finish=False)
        else:
            result = g.state.battle_result
    except HarnessError as err:
        g.note(f"battle 1's fight did not finish: {str(err)[:200]}")
    end_state = g.state
    _finish(g)
    back = cb.poll(g, lambda s: s.on_field and s.ui_state == "FieldHUD", 30.0, f"field {field} after battle 1")
    lines = cb.new(g, at)
    failed, thrown = cb.count(lines, PUMP_FAILED), cb.exception_lines(lines)
    led.check("S133-B0", result in (1, 2) and back is not None and cb.count(lines, CODEC_DRIFT) == 0 and failed == 0
              and not thrown,
              f"plan {'ran' if not stop else 'stopped: ' + stop} ({ctx.get('plan')}); result {result!r}; back on the "
              f"field {back is not None}; codec-drift lines {cb.count(lines, CODEC_DRIFT)}; 'pump failed' lines {failed}; "
              f"exception lines {len(thrown)}{': ' + thrown[0].split('|', 2)[-1].strip()[:160] if thrown else ''}")
    ctx["b1_lines"] = lines
    ctx["b1_samples"] = samples + [end_state]
    if have:
        _judge_battle_1(g, led, ctx)


def _start_of(starts: list, actor: int | None, cmd: int | None = None, sub: int | None = None) -> list:
    return [s for s in starts if (actor is None or s["actor_slot"] == actor) and (cmd is None or s["act_cmd_no"] == cmd)
            and (sub is None or s["act_sub_no"] == sub)]


def _judge_battle_1(g, led: cb.Ledger, ctx: dict) -> None:
    """ON from the samples; STOP; the tape paged out (DUMP); TAPE / ORDER offline; AT / EN / MT / POT off its STARTs; VFX /
    PAIR off the keys and the log."""
    samples = [s for s in ctx["b1_samples"] if (_num(cb.host(s).get("caps")) if _num(cb.host(s).get("caps")) is not None
                                                  else -1) >= 0]
    bad_on = [cb.frame_of(s) for s in samples if not (_act(s).get("on") is True and _act(s).get("lever_off") is False
              and cb.mask_bits(cb.host(s).get("caps")) & BW.CAP_ACTION_STARTS
              and cb.mask_bits(cb.peer(s).get("caps")) & BW.CAP_ACTION_STARTS
              and _act(s).get("nonce") == cb.peer(s).get("nonce"))]
    led.check("S133-ON", bool(samples) and not bad_on,
              f"{len(samples)} own-battle publish(es) read, off at frames {bad_on[:6]}; "
              f"{_brief(samples[-1]) if samples else 'no publish with a lane'}")
    at = cb.mark(g)
    st, why = _act_verb(g, "tape", "stop")
    lines = cb.wait_log(g, at, STOPPED, 1.5)
    st = cb.poll(g, lambda s: _tape(s).get("state") == "stopped", 1.5, "the tape stopped") or g.state
    a, t = _act(st), _tape(st)
    ctx["b1_nonce"] = a.get("nonce")
    total = _num(t.get("frames")) or 0
    stop_line = [ln for ln in lines if STOPPED in ln]
    led.check("S133-STOP", not why and t.get("state") == "stopped" and total > 0 and len(stop_line) == 1
              and f"-- {total} frame(s), {t.get('starts')} START(s)," in stop_line[0],
              why or f"tape {cb.pick(t, 'state', 'frames', 'starts', 'ms', 'overflow')}; {cb.grep(lines, 'action tape')}")
    frames, pages, dwhy = _dump_all(g, total)
    tape = [b for _i, _ms, b in frames]
    decoded = [BW.decode_action(b) for b in tape]
    kinds = [BW.classify_action(d) for d in decoded]
    starts = [d for d, k in zip(decoded, kinds) if k == "start"]
    # ---- DUMP
    tiled = [i for i, _ms, _b in frames] == list(range(total)) and all(
        p.get("total") == total and p.get("count") == min(PAGE, total - p.get("from", 0)) for p in pages)
    refused_ok, rwhy = True, ""
    if total:
        st2, rwhy = _act_verb(g, "tape", "dump", total, 1)
        refused_ok = st2 is None and f"from {total} is past the tape's last frame ({total} frame(s))" in rwhy
    at = cb.mark(g)
    _act_verb(g, "tape", "info")
    ilines = cb.wait_log(g, at, BW.LOG_ACT_TAPE_INFO.split("] ", 1)[1] + "stopped", 1.5)
    s = BW.act_tape_summary(tape)
    want = (f"{s['frames']} frame(s) -- {s['starts']} START(s), {s['ends']} END(s), {s['impacts']} impact(s) ({s['ext']} "
            f"with the id extension), {s['stat']} stat tick(s), {s['bad']} bad;")
    info_ok = any(want in ln for ln in ilines)
    led.check("S133-DUMP", not dwhy and tiled and refused_ok and info_ok,
              dwhy or f"{len(pages)} page(s), {len(frames)} of {total} frame(s), tiled {tiled}; past-the-end refusal "
                      f"{'ok' if refused_ok else repr(rwhy)}; info wants '{want}': {cb.grep(ilines, 'action tape:')}")
    if dwhy or not frames:
        led.unreached(("S133-TAPE", "S133-ORDER", "S133-AT", "S133-EN", "S133-MT", "S133-POT"),
                      f"no tape to judge: {dwhy or 'the tape is empty'}")
    else:
        _judge_tape(led, ctx, a, t, tape, decoded, kinds, starts)
    _judge_books(led, ctx, st, a)


def _judge_tape(led: cb.Ledger, ctx: dict, a: dict, t: dict, tape: list, decoded: list, kinds: list, starts: list) -> None:
    nonce = a.get("nonce")
    bad = []
    for i, (b, d, k) in enumerate(zip(tape, decoded, kinds)):
        legacy = BW.decode_action_legacy(b)
        if d is None or legacy is None:
            bad.append(f"{i}: unparsed ({len(b)} B)")
        elif k == "start" and not (len(b) == BW.ACT_START_RECORD_LEN and BW.act_inert_head(legacy)
                                   and legacy["flags"] == BW.ACT_FLAG_START):
            bad.append(f"{i}: START {len(b)} B legacy c/t {legacy['caster_slot']}/{legacy['target_slot']} inert "
                       f"{BW.act_inert_head(legacy)} flags 0x{legacy['flags']:02X}")
        elif k == "end" and not (len(b) == BW.ACT_ID_RECORD_LEN and BW.act_inert_head(legacy)
                                 and legacy["flags"] == BW.ACT_FLAG_END):
            bad.append(f"{i}: END {len(b)} B legacy c/t {legacy['caster_slot']}/{legacy['target_slot']} inert "
                       f"{BW.act_inert_head(legacy)} flags 0x{legacy['flags']:02X}")
        elif k == "impact" and not (len(b) == BW.ACT_ID_RECORD_LEN and d["has_ext"] and d["ext_kind"] == BW.ACT_EXT_IMPACT):
            bad.append(f"{i}: impact {len(b)} B ext {d['has_ext']}")
        elif k == "stat" and len(b) != BW.ACT_LEGACY_LEN:
            bad.append(f"{i}: stat tick {len(b)} B")
        elif k == "bad":
            bad.append(f"{i}: a START/END flag with no good extension ({len(b)} B)")
        if legacy is not None and legacy["nonce"] != nonce:
            bad.append(f"{i}: nonce {legacy['nonce']} != act.host.nonce {nonce} (MARKER 1)")
    bad += [f"identity: {v}" for v in BW.act_identity_violations(tape)]
    bad += [f"horizon: {v}" for v in BW.act_horizon_violations(tape)]
    counts = (len(starts), t.get("starts"), a.get("starts"))
    led.check("S133-TAPE", not bad and len(set(counts)) == 1 and counts[0] > 0 and t.get("overflow") == 0,
              f"{len(tape)} frame(s): {dict((k, kinds.count(k)) for k in sorted(set(kinds)))}; STARTs taped/tape/act "
              f"{counts}; overflow {t.get('overflow')!r}; bad {bad[:5]}")
    viol = BW.act_order_violations(tape)
    led.check("S133-ORDER", bool(starts) and not viol, f"{len(starts)} START(s); violations {viol[:5]}")
    slots, plan = ctx.get("slots") or {}, ctx.get("plan") or {}
    acmd, asub = ctx.get("attack_sent") or (CMD_ATTACK, ATTACK_SUB)
    zat = _start_of(starts, slots.get("zidane"), acmd, asub)
    led.check("S133-AT", len(zat) >= 2 and all(s["vfx_kind"] == BW.VFX_KIND_SPECIAL for s in zat[:2])
              and zat[0]["vfx_num"] == zat[1]["vfx_num"],
              f"Zidane (slot {slots.get('zidane')}) Attack (cmd {acmd} sub {asub}) STARTs "
              f"{[(s['act_id'], s['vfx_kind'], s['vfx_num']) for s in zat]}; the plan's attacks {plan.get('attacks')}")
    foes = [s for s in starts if not s["actor_flags"] & BW.ACTOR_IS_PLAYER]
    good = [s for s in foes if s["vfx_kind"] == BW.VFX_KIND_ENEMY and s["vfx_num"] == s["act_sub_no"]]
    led.check("S133-EN", bool(good), f"enemy STARTs (id, actor, cmd, sub, kind, num) "
                                     f"{[(s['act_id'], s['actor_slot'], s['act_cmd_no'], s['act_sub_no'], s['vfx_kind'], s['vfx_num']) for s in foes][:6]}")
    many = ctx.get("many")
    mt = _start_of(starts, slots.get("vivi"), many["cmd"], many["sub"]) if many else []
    spans = [bin(s["act_tar_id"] & ctx.get("enemy_mask", 0)).count("1") for s in mt]
    led.check("S133-MT", bool(mt) and max(spans) >= 2,
              (f"{many['name']} (cmd {many['cmd']} sub {many['sub']}, sent tar 0x{many['mask']:X}): STARTs tar "
               f"{[hex(s['act_tar_id']) for s in mt]}, enemy bits {spans} (enemy mask 0x{ctx.get('enemy_mask', 0):X})")
              if many else f"no many-target cast was made: {ctx.get('no_many') or f'the plan never reached it ({plan})'}")
    pcmd, psub = ctx.get("potion_sent") or (CMD_ITEM, POTION)
    pot = _start_of(starts, slots.get("garnet"), pcmd, psub)
    led.check("S133-POT", bool(pot) and all(s["vfx_kind"] == BW.VFX_KIND_SPECIAL for s in pot),
              f"Garnet (slot {slots.get('garnet')}) Potion (cmd {pcmd} sub {psub}) STARTs "
              f"{[(s['act_id'], s['vfx_kind'], s['vfx_num']) for s in pot]}; the plan's potion {plan.get('potion')}")


def _judge_books(led: cb.Ledger, ctx: dict, st, a: dict) -> None:
    lp, vfx, kinds = _loop(st), _sub(a, "vfx"), _sub(a, "kinds")
    lines = ctx.get("b1_lines") or []
    starts, scripted = _num(a.get("starts")) or 0, _num(a.get("scripted")) or 0
    checked = (_num(vfx.get("checked")) or 0) + (_num(vfx.get("unchecked")) or 0)
    led.check("S133-VFX", starts > 0 and checked == starts - scripted and vfx.get("drift") == 0 and vfx.get("why") is None
              and sum(_num(v) or 0 for v in kinds.values()) == starts and cb.count(lines, "describe drift --") == 0,
              f"vfx {cb.pick(vfx, 'checked', 'drift', 'unchecked', 'why')}; kinds {dict(kinds)}; starts {starts} "
              f"(scripted {scripted}); drift lines {cb.count(lines, 'describe drift --')}")
    nonce = a.get("nonce")
    closed = [ln for ln in lines if f"{CLOSED}{nonce}) closed -- {starts} START(s)" in ln
              and f", {a.get('ends')} END(s), " in ln]
    ok = (starts > 0 and starts == lp.get("starts") and (_num(a.get("ends")) or 0) > 0 and a.get("ends") == lp.get("ends")
          and lp.get("paired") == a.get("ends") and lp.get("orphans") == 0 and lp.get("caster_mismatch") == 0
          and lp.get("ext_bad") == 0 and a.get("noid_impacts") == 0 and a.get("dropped") == 0
          and a.get("wire_dropped") == 0 and a.get("open") == 0
          and a.get("no_end") == 0 and a.get("cut") == 0 and lp.get("no_end") == 0 and lp.get("cut") == 0
          and cb.count(lines, BW.LOG_ACT_NEVER_ENDED) == 0 and len(closed) == 1)
    led.check("S133-PAIR", ok, f"{_brief(st)} loop {dict(lp)}; no_end/cut {a.get('no_end')!r}/{a.get('cut')!r}; "
                               f"'never ENDed' lines {cb.count(lines, BW.LOG_ACT_NEVER_ENDED)}; summary "
                               f"{cb.grep(lines, CLOSED, limit=400)}")


# ------------------------------------------------------------------------------------------------- L1 (the lever)
def _leg_l1(g, led: cb.Ledger, ctx: dict) -> None:
    g.note("L1: `actbench hoststarts off` -- the pre-s133 host on the s133 DLL; battle 2 to the victory")
    at = cb.mark(g)
    st1, w1 = _act_verb(g, "hoststarts", "off")
    st2, w2 = _act_verb(g, "tape", "rec")
    if st1 is None or st2 is None:
        led.check("S133-L1", False, f"not reached: {w1 or w2}")
        return
    if cb.poll(g, lambda s: cb.free(s) and s.ui_state == "FieldHUD" and not s.in_battle, 30.0, "a playable field") is None:
        led.check("S133-L1", False, f"not reached: no playable field before battle 2 (ui {g.state.ui_state!r})")
        _act_verb(g, "hoststarts", "on")
        return
    seen = []
    try:
        g.start_battle(SCENE, group=GROUP)

        def policy(s, _slot):
            seen.append(s)
            return {"command": "Attack"}
        g.fight(policy=policy, timeout=FIGHT_S, finish=False)
    except HarnessError as err:
        g.note(f"battle 2 did not finish cleanly: {str(err)[:200]}")
    st = g.state
    _finish(g)
    a, lp = _act(st), _loop(st)
    _act_verb(g, "tape", "stop")
    t = _tape(cb.poll(g, lambda s: _tape(s).get("state") == "stopped", 1.5, "the tape stopped") or g.state)
    frames, _pages, dwhy = _dump_all(g, _num(t.get("frames")) or 0)
    impacts = [b for _i, _ms, b in frames if BW.classify_action(BW.decode_action(b)) == "impact"]
    nonces = {BW.decode_action_legacy(b)["nonce"] for _i, _ms, b in frames}
    caps5 = [cb.frame_of(s) for s in seen if cb.mask_bits(cb.host(s).get("caps")) & BW.CAP_ACTION_STARTS]
    off_ok = (a.get("starts") == 0 and a.get("ends") == 0 and a.get("ext_impacts") == 0 and a.get("on") is False
              and a.get("lever_off") is True and all(v == 0 for v in _sub(a, "kinds").values()) and not caps5
              and (_num(lp.get("impacts")) or 0) > 0 and impacts and all(len(b) == BW.ACT_LEGACY_LEN for b in impacts)
              and nonces == {a.get("nonce")} and a.get("nonce") != ctx.get("b1_nonce"))
    lines = cb.new(g, at)
    failed, thrown = cb.count(lines, PUMP_FAILED), cb.exception_lines(lines)
    at2 = cb.mark(g)
    st3, w3 = _act_verb(g, "hoststarts", "on")
    lines2 = cb.wait_log(g, at2, LEVER_ON_LINE, 1.5)
    st3 = cb.poll(g, lambda s: _act(s).get("on") is True, 1.5, "act.host.on back") or g.state
    on_ok = st3 is not None and _act(st3).get("on") is True and _act(st3).get("lever_off") is False \
        and any(ln.rstrip().endswith(LEVER_ON_LINE) for ln in lines2)
    led.check("S133-L1", off_ok and on_ok and cb.count(lines, LEVER_OFF_LINE) == 1 and not dwhy and failed == 0
              and not thrown,
              f"battle 2: {_brief(st)}; caps bit 5 at frames {caps5[:4]}; {len(impacts)} taped impact(s), lengths "
              f"{sorted({len(b) for b in impacts})}, nonces {sorted(nonces)} (MARKER 2); {dwhy or 'dump ok'}; "
              f"'pump failed' lines {failed}, exception lines {len(thrown)}; "
              f"after `hoststarts on`: {cb.pick(_act(st3), 'on', 'lever_off')} {w3}; "
              f"{cb.grep(lines + lines2, 'action STARTs', limit=300)}")


# ------------------------------------------------------------------------------------------------- R (the release)
def _release(g, led: cb.Ledger, ctx: dict) -> None:
    """The lever and a recording tape left SET on purpose (only on an engine that has them), then `reset`: both must come
    back, logged -- read again WITH the role (the plain post-reset read sees the role released)."""
    have = ctx["probe"]
    if have:
        _act_verb(g, "hoststarts", "off")
        _act_verb(g, "tape", "rec")
    at = cb.mark(g)
    cb.release(g)
    lines = cb.new(g, at)
    rr, rwhy = cb.reread_with_role(g) if have else (None, "")
    a, t = (_act(rr), _tape(rr)) if rr is not None else ({}, {})
    led.check("S133-R", have and rr is not None and cb.count(lines, REL_LEVER) == 1 and cb.count(lines, REL_TAPE) == 1
              and a.get("lever_off") is False and t.get("state") == "off" and t.get("frames") == 0
              and t.get("page") is None,
              (f"`{PROBE}` absent: nothing was set" if not have else
               f"re-read WITH the role: {cb.pick(a, 'lever_off', 'on')} tape {cb.pick(t, 'state', 'frames', 'page')}"
               if rr is not None else f"no re-read with the role ({rwhy})")
              + f"; {cb.grep(lines, 'released with the harness')}")
