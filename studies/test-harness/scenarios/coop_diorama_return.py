"""F3.3 DIO-1 THE DIORAMA WARM RETURN -- the solo bench (s97), run unattended.

THE DEFECT (`studies/field-coop/F3.2-DESIGN.md` suggestions DIO-1; F1-BUILD.md "the next warp"). A stock battle saves
the field in two halves: `BackupPosObjData` on the field side, then the battle's own `StartEvents` copies
`sEventContext0` into `sEventContext1`. The guest's battle DIORAMA did neither: `isDebug` skips the battle's
`StartEvents`, and every field load zeroes `sEventContext1.inited`. So every return cold-started the guest's field
through Main_Init. The guest was moved to the arrival point, MAP variables were zeroed and NPCs reset, while the host
came back in place.

THE FIX (memoria-patch s97, `NetSyncDiorama.PrimeWarmReturn`). Right before the boot's Replace, the pure `WarmVerdict`
runs. Only when the guest is FREE-STANDING does it do the stock field half itself. Free-standing means: on a field,
the event context is this field's, the engine's own slot is empty, entry 0 has a tag-10 Main_Reinit, random encounters
are armed (`encratio > 0`), entry 0 is above level 0, no battle-return bracket is open, control is on, FieldHUD, no
dialogue window, and a controlled actor exists. Anything else keeps today's cold return and logs one reason line.
`EventEngine.StartEvents` then reports which branch it actually took (`NoteFieldEventsStart`): `warm` (Main_Reinit
called), `cold` (Main_Init), or `reinit-missing`. The harness reads the same facts in `netsync.diorama`.

THE BENCH (s97's harness verbs; the ~ menu's IMGUI "Boot" / "Leave diorama" buttons cannot be pressed by injected
input). `netsync selftest 1` forces the selftest role, which is the diorama's sanctioned solo bench.
`netsync dioboot <scene> [pattern]` boots BattleMapDebug from a live field (selftest role only; the scene id must be
registered in `FF9StateSystem.Battle.mapName`). `netsync dioleave` asks for the return; the teardown lands on arrival.
A `reset` Leaves a diorama the harness booted and holds the role until it has torn down.

THE FIELD. The warm gate needs a field with BOTH an entry-0 tag-10 Main_Reinit and armed random encounters, so the
journal bench 30801 CANNOT host the warm leg. Its `.eb` entry 0 has tags 0 and 1 only, and it has no [encounter], so
its boot is correctly COLD ("field 30801 has no Main_Reinit ..."). That is the same case as Dali 350, which
s97 also returns cold. The default is 30602 (LOCKT2, `studies/movement/bench/lockt2.field.toml`, deployed in
FF9CustomMap-msgs). Its entry 0 carries tags 0, 1 and 10; its [encounter] arms Evil Forest battles at the default
freq 255; the spawn is (0, -1900); and a plain held talker ("control", vivi) stands at (0, -350). The scenario
suppresses random battles with `noencounter 1` (s94, the F4 booster). That flag is read only by the step roll, so
it leaves `encratio`, which the warm gate reads, untouched. 30801 is used instead for leg G, the gate's own negative.
Pass `--field N` to run the warm/cold legs on another field. The engine's `boot_why` names it if N cannot take a warm
return.

WHAT IS PROVEN -- every check an OUTCOME (the published position, the engine's own branch report, its log lines):
  DIO-0  the engine publishes `netsync.diorama`, and the selftest proof line `diorama containment selftest: OK (...
         warm[gate=ok return=ok])` (WarmVerdict's truth table + ReturnIsOurs, offline) -- once per process.
  W  THE WARM RETURN, from a free-standing stand ~530 units from the spawn (so a cold return would be visible):
     W0 (precondition) the stand is >= AWAY_MIN from the Main_Init placement sampled at arrival;
     W1 boot == "warm", no cold reason, `primed`, `boot_field` == this field;
     W2 `boot_x`/`boot_z` == the player's position at the boot (within BOOT_TOL);
     W3 one "diorama boot: WARM return primed -- field N, player at (x, z)" line;
     W4 the return: `returns` +1, `last_return` "warm" on this field (StartEvents' REINIT branch with Main_Reinit
        CALLED -- the engine's own report, not a replica of its test), `primed` consumed;
     W5 one "diorama RETURN (warm) -> field N resumed through Main_Reinit: every actor restores ..." line, and no
        cold, reinit-missing or "did NOT prime" return line;
     W6 the player is back where he stood (|pos - P0| <= KEEP_TOL), compared only once control is back (the
        actors are placed after StartEvents);
     W7 the field is LIVE: `resuming` false (no battle-return bracket left open) and a short walk moves him -- a
        frozen field cannot pass on position alone. (A liveness guard, not a warm/cold discriminator: a cold return
        passes it too. Its teeth are a reinit that ran with no Main_Reinit and left every object suspended.)
  C  THE COLD CONTROL, on the same DLL and field: the player talks to the "control" NPC (a window open, control
     off) and boots from there.
     C0 (precondition) the talker's window opened;
     C1 boot == "cold" with the reason "player control is off ..." or "a dialogue window is open";
     C2 one "diorama boot: COLD return (...)" line;
     C3 `returns` +1, `last_return` "cold";
     C4 one "diorama RETURN (cold) -> field N re-entered through Main_Init (...)" line, no warm return line;
     C5 THE INSTRUMENT CAN FAIL: the SAME position test W6 passed (`_kept`) reads NOT kept here -- the player is at
        the Main_Init placement (the arrival sample), not where the boot found him.
  G  THE GATE'S NEGATIVE: a FREE-STANDING boot on 30801, which has no Main_Reinit, is refused warm with that reason
     (G1) and returns cold to the arrival placement (G2) -- the warm path is never taken where a reinit would leave
     every object suspended. When 30801 is not registered, the registrations cannot be read, or 30801 IS the warm
     field (`--field 30801`), G1/G2 are recorded FAILED "not reached" with that reason -- never a note-only skip.
  RESET  `reset` releases the forced role and leaves no diorama booted.
NOT PROVEN HERE (two-machine boxes): a HOST random encounter pulling a guest who stands mid-screen; the guest's NPCs
and doors keeping their pre-battle state; Main_Reinit reading `GetBattleResult` 0 (s97 known gap).

CALIBRATION -- a check that cannot fail is not a check. Run this once against the currently deployed s96 engine
(no `netsync.diorama`, no `dioboot`/`dioleave`) BEFORE trusting a green run of s97. Expected there:
  * RED, key-absent: DIO-0 (no `diorama` block) and the proof-line check (the s96 diorama selftest line carries no
    `warm[...]`).
  * RED, not reached: W1-W7, C1-C5 and G1-G2. The boot is refused, so each is recorded FAILED with the refusal as
    its detail -- the agent's "unknown sub-verb 'dioboot'" (raw step), or a driver that knows the verb refusing it
    up front ("publishes no `netsync.diorama`"). Never skipped silently, never passed. Legs C and G do not run at
    all once the verb is missing (their checks are recorded failed with the same refusal).
  * GREEN there: the forced role, the encounter booster, W0 (the stand-away precondition), and RESET.
  In all, 16 red and 5 green on s96.
  The behavioural calibration of the position check lives in THIS run: C5 applies W6's exact test to the cold
  return and must read "not kept". A run where W6 and C5 both pass proves the warm return; a W6 that passed with
  C5 also reading "kept" would mean the position check cannot tell the branches apart.

DRIVER NOTE. `Session.netsync` refuses a sub-verb its NETSYNC_SUBVERBS lacks BEFORE sending; the committed driver
predates `dioboot`/`dioleave` (the F3.3 driver stage adds them, gated on `netsync.diorama`). `_ns_verb` sends a
sub-verb the driver does not know as a raw `netsync ...` step instead (one note per sub-verb); the AGENT's own gates
and refusals apply unchanged. With a driver that knows the verb, `_ns_verb` is plain `g.netsync` -- and on s96 its
up-front capability refusal ("publishes no `netsync.diorama`") is read exactly like the agent's "unknown sub-verb".

    py tools/play.py studies/test-harness/scenarios/coop_diorama_return.py --field 30602
"""
from __future__ import annotations

import math

try:                                     # play.py puts tools/ on sys.path before it loads a scenario
    from harness import HarnessError
except ImportError:                      # pragma: no cover - imported outside the driver (py_compile, a stub)
    HarnessError = RuntimeError          # HarnessError IS a RuntimeError

FIELD = 30602                   # LOCKT2: entry-0 tag-10 Main_Reinit + [encounter] (freq 255) -- see the module note
SPOT = (-520.0, -1520.0)        # the free-standing stand: ~530 units from the spawn, clear of every book zone
TALKER_PATH = ((-250.0, -760.0), (0.0, -760.0), (0.0, -545.0))   # due north onto the "control" talker at (0, -350)
GATE_FIELD = 30801              # no Main_Reinit, no [encounter]: the warm gate must refuse it (leg G)
GATE_SPOT = (0.0, -330.0)       # ~500 units north of 30801's spawn (0, -837)
DIO_SCENE = 67                  # Evil Forest / Trail -- a BattleMapList id every bench here boots (diorama-lane.md)
DIO_PATTERN = 0

BOOT_TOL = 1.0                  # boot_x/z vs the player sampled at rest just before the boot (one PosObj source)
KEEP_TOL = 4.0                  # "back where he stood" -- the bench note says about a unit; a few units of slack
SPAWN_TOL = 40.0                # the Main_Init placement vs the arrival sample (entry settle included)
AWAY_MIN = 250.0                # the stand must be this far from the Main_Init placement, or a cold return hides
WALK_MIN = 60.0                 # W7: a short walk must move him at least this far
BOOT_S = 30.0                   # the swirl into BattleMapDebug
LEAVE_S = 45.0                  # the Replace back + StartEvents + Main_Reinit/Main_Init + control

COLD_WHYS = ("player control is off", "a dialogue window is open")
NO_REINIT = "has no Main_Reinit"
BOOT_REFUSED = "diorama boot REFUSED:"   # NetSyncDiorama.Boot's log line; the agent's own refusal text never says why
FADE_REFUSAL = "diorama boot REFUSED: a scene fade is in flight"

WARM_CHECKS = (
    "W1: the boot primed the WARM return (boot 'warm', no cold reason, primed, boot_field == this field)",
    "W2: the boot recorded the player where he stood (boot_x/boot_z == P0)",
    "W3: one 'diorama boot: WARM return primed -- field N, player at (x, z)' line",
    "W4: the return took the REINIT branch with Main_Reinit called (returns +1, last_return 'warm', primed consumed)",
    "W5: one 'RETURN (warm) -> field N resumed through Main_Reinit' line, no cold / reinit-missing / unprimed line",
    "W6: the player came back WHERE HE STOOD (not the Main_Init placement)",
    "W7: the field is live after the return (no battle-return bracket open; a short walk moves him)",
)
COLD_CHECKS = (
    "C1: a boot with a talk window open primed NO warm return (boot 'cold', reason control-off / window-open)",
    "C2: one 'diorama boot: COLD return (...)' line",
    "C3: the return took the COLD branch (returns +1, last_return 'cold')",
    "C4: one 'RETURN (cold) -> field N re-entered through Main_Init (...)' line, no warm return line",
    "C5: W6's position test reads NOT KEPT on the cold return (the player is at the Main_Init placement)",
)
GATE_CHECKS = (
    "G1: a FREE-STANDING boot on a field with no Main_Reinit is refused warm, with that reason",
    "G2: ...and returns cold through Main_Init, to the arrival placement",
)


# ---------------------------------------------------------------------------------------- observing
def _log_lines(g) -> list:
    p = g.engine_log()
    if p is None:
        return []
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _mark(g) -> int:
    return len(_log_lines(g))


def _new(g, mark: int) -> list:
    return _log_lines(g)[mark:]


def _count(lines, needle: str) -> int:
    return sum(1 for ln in lines if needle in ln)


def _grep(lines, *needles, limit: int = 400) -> str:
    return "; ".join(ln for ln in lines if any(n in ln for n in needles))[:limit]


def _ns(st) -> dict:
    return st.netsync or {}


def _dio(st) -> dict:
    d = _ns(st).get("diorama")
    return d if isinstance(d, dict) else {}


def _xz(st) -> tuple:
    return (st.player_x, st.player_z)


def _dist(a, b) -> float:
    if a is None or b is None or None in a or None in b:
        return float("inf")
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _kept(after, before) -> bool:
    """W6's position test -- and C5 applies the SAME function to the cold return, where it must read False."""
    return _dist(after, before) <= KEEP_TOL


def _fmt(p) -> str:
    return "None" if p is None or None in p else f"({p[0]:.1f}, {p[1]:.1f})"


def _poll(g, predicate, timeout: float, what: str):
    """``g.wait_for`` that answers None on a timeout: the check that follows carries the verdict. A dead game
    still raises -- the next send asserts the process is alive."""
    try:
        return g.wait_for(predicate, timeout=timeout, what=what)
    except HarnessError:
        return None


def _free(s) -> bool:
    """Free-standing as the harness can see it: on a field, control on, no window, not mid-fade."""
    return s.on_field and s.control and not s.dialog_open and not s.fading


def _in_diorama(s) -> bool:
    return s.scene == "BattleMapDebug" and bool(s.battle.get("debug"))


# ------------------------------------------------------------------------------------------- acting
_RAW_NOTED: set = set()


def _ns_verb(g, sub: str, *args):
    """`netsync <sub> [args]` -- through the driver when it knows the sub-verb, else as a raw step (module note:
    today's driver predates s97's `dioboot`/`dioleave`). The agent's refusals come back either way."""
    known = getattr(g, "NETSYNC_SUBVERBS", None)
    if known is None or sub in known:
        return g.netsync(sub, *args)
    if sub not in _RAW_NOTED:
        _RAW_NOTED.add(sub)
        g.note(f"driver predates `netsync {sub}` (not in Session.NETSYNC_SUBVERBS) -- sent as a raw step; the "
               f"agent's own gates still apply")
    g.send("netsync " + " ".join([sub, *(str(a) for a in args)]), timeout=20.0)
    return g.state


def _boot(g) -> tuple:
    """`netsync dioboot` and wait for BattleMapDebug. (booted, why-not). When NetSyncDiorama.Boot itself refuses, the
    agent answers ONE fixed text ("refused (Memoria.log names why: ...)") -- the reason is written to Memoria.log only.
    So the log after the attempt is read: its REFUSED line rides on the refusal's detail, and a boot refused because a
    scene fade was in flight is retried once."""
    why = ""
    for attempt in range(2):
        mark = _mark(g)
        try:
            _ns_verb(g, "dioboot", DIO_SCENE, DIO_PATTERN)
            why = ""
            break
        except HarnessError as err:
            why = str(err)[:300]
            if "diorama boot REFUSED" in why:          # [ff9mapkit netsync F3.3] Boot's own refusal: read its reason
                _poll(g, lambda s: _count(_new(g, mark), BOOT_REFUSED) >= 1, 2.0, "Boot's REFUSED line in the log")
                logged = _grep(_new(g, mark), BOOT_REFUSED, limit=240)
                if logged:
                    why = f"{why} -- log: {logged}"
            if FADE_REFUSAL not in why or attempt:
                return False, f"dioboot refused: {why}"
            g.wait_frames(30)
    st = _poll(g, _in_diorama, BOOT_S, "the diorama (BattleMapDebug, battle.debug) to come up")
    if st is None:
        s = g.state
        return False, f"the diorama never came up (scene={s.scene!r} battle={s.battle!r})"[:300]
    return True, ""


def _leave(g, field: int) -> tuple:
    """`netsync dioleave` (request-only; a fade in flight defers it -- retried) and wait until the field is
    playable again. (returned, why-not)."""
    for attempt in range(4):
        try:
            _ns_verb(g, "dioleave")
            break
        except HarnessError as err:
            why = str(err)[:300]
            if "deferred" not in why or attempt == 3:
                return False, f"dioleave refused: {why}"
            g.wait_frames(30)
    st = _poll(g, lambda s: s.field_id == field and _free(s), LEAVE_S,
               f"field {field} to be playable after the return")
    if st is None:
        s = g.state
        return False, f"no playable return to field {field} (field={s.field_id} ui={s.ui_state!r} " \
                      f"control={s.control} scene={s.scene!r})"
    g.wait_frames(10)                    # the returned field's first ticks: position published, not mid-placement
    return True, ""


def _unreached(g, names, why: str) -> None:
    """A leg that could not run: every check it owns is recorded FAILED with the reason -- never skipped silently,
    never passed (the calibration contract)."""
    for name in names:
        g.check(False, name, f"not reached: {why}"[:400])


def _stand(g, spot, what: str):
    """Walk to `spot` and come to rest free-standing. Returns the rested state, or None."""
    g.walk_to(*spot, tolerance=30, strict=False)
    st = _poll(g, _free, 6.0, f"control back at {what}")
    if st is None:
        return None
    g.wait_frames(20)                    # at rest: the boot reads PosObj.pos, the same source as player.x/z
    st = g.state
    return st if _free(st) else None


# ------------------------------------------------------------------------------------------ the run
def run(g, field: int = FIELD):
    g.note(f"F3.3 DIO-1: the diorama WARM return, solo (warm + cold control on {field}, the gate on {GATE_FIELD})")
    g.newgame()
    g.warp(field)
    enc = _encounters_off(g)
    g.wait_frames(60)
    arrival = g.state
    s0 = _xz(arrival)                    # the Main_Init placement: where a COLD return puts him
    g.note(f"arrival (the Main_Init placement) on {field}: {_fmt(s0)}")
    if enc:                              # calibrating WALKS: never on an armed encounter field without the booster
        g.calibrate_axes()

    st = _ns_verb(g, "selftest", 1)
    ns = _ns(st)
    g.check(st.netsync is not None and ns.get("selftest") and ns.get("instance") and ns.get("forced"),
            "the harness forced the selftest role for this process (Memoria.ini untouched)", repr(st.netsync)[:300])
    have = isinstance(ns.get("diorama"), dict)
    g.check(have, "DIO-0: the engine publishes `netsync.diorama` (memoria-patch s97)",
            "" if have else f"absent -- a pre-s97 engine (netsync keys: {sorted(ns)[:40]})")
    proof = _poll(g, lambda s: _count(_log_lines(g), "diorama containment selftest:") >= 1, 8.0,
                  "the selftest proof block to log the diorama containment self-test")
    lines = [ln for ln in _log_lines(g) if "diorama containment selftest:" in ln]
    last = lines[-1] if lines else ""
    g.check(proof is not None and "selftest: OK (" in last and "warm[gate=ok return=ok]" in last,
            "DIO-0: the diorama selftest logged OK with the warm-return truth table (warm[gate=ok return=ok])",
            last[-300:] or "no proof line")

    if not enc:
        _unreached(g, WARM_CHECKS + COLD_CHECKS + GATE_CHECKS,
                   "random encounters could not be suppressed -- a walk on this field would end in a real battle")
        _release(g)
        return

    absent = _leg_warm(g, field, s0)
    if absent:
        g.note(f"the boot verb itself is missing on this engine -- legs C and G cannot run either ({absent[:160]})")
        _unreached(g, COLD_CHECKS + GATE_CHECKS, absent)
    else:
        _leg_cold(g, field, s0)
        _leg_gate(g, field)
    _release(g)


def _encounters_off(g) -> bool:
    """`noencounter 1` (s94): the step roll only -- `encratio`, which the warm gate reads, is untouched."""
    try:
        g.no_encounters(True)
        ok, why = True, ""
    except (HarnessError, AttributeError) as err:
        ok, why = False, str(err)[:300]
    g.check(ok, "random encounters are suppressed for the walks (noencounter 1, s94; encratio untouched)", why)
    return ok


def _leg_warm(g, field: int, s0) -> str:
    """Leg W. Returns the refusal text when the boot VERB does not exist on this engine (legs C/G are then
    unreachable too), else ''."""
    g.note("W: the warm return -- boot from a free-standing stand, then leave")
    st = _stand(g, SPOT, "the free-standing stand")
    if st is None:
        _unreached(g, WARM_CHECKS, f"could not come to rest free-standing at {SPOT} ({g.state!r})"[:300])
        return ""
    p0 = _xz(st)
    away = _dist(p0, s0)
    g.check(away >= AWAY_MIN,
            f"W0: the player stands {away:.0f} units from the Main_Init placement (>= {AWAY_MIN:.0f}: a cold return "
            f"would be visible)", f"P0={_fmt(p0)} spawn={_fmt(s0)}")
    r0 = _dio(st).get("returns")
    mark = _mark(g)
    booted, why = _boot(g)
    if not booted:
        _unreached(g, WARM_CHECKS, why)
        _back_to_field(g, field)
        # the bench itself is missing (no `diorama` block: the agent's "unknown sub-verb", or a driver that refuses
        # the verb up front on the absent capability) -- not a refusal a later leg could get past
        absent = not _dio(g.state) or any(m in why for m in ("unknown sub-verb", "unknown op", "publishes no"))
        return why if absent else ""

    d = _dio(g.state)
    reason = d.get("boot_why")
    unfit = isinstance(reason, str) and (NO_REINIT in reason or "no random encounters" in reason)
    g.check(d.get("boot") == "warm" and reason is None and d.get("primed") is True and d.get("boot_field") == field,
            WARM_CHECKS[0],
            (f"FIELD {field} CANNOT TAKE A WARM RETURN -- the engine says: {reason!r}. Run the warm leg on a field "
             f"with an entry-0 tag-10 Main_Reinit AND armed random encounters (module note). " if unfit else "")
            + f"boot={d.get('boot')!r} why={reason!r} primed={d.get('primed')!r} boot_field={d.get('boot_field')!r}")
    bx, bz = d.get("boot_x"), d.get("boot_z")
    g.check(isinstance(bx, (int, float)) and isinstance(bz, (int, float)) and _dist((bx, bz), p0) <= BOOT_TOL,
            WARM_CHECKS[1], f"boot=({bx!r}, {bz!r}) P0={_fmt(p0)}")
    fresh = _new(g, mark)
    g.check(_count(fresh, f"diorama boot: WARM return primed -- field {field}, player at (") == 1
            and _count(fresh, "diorama boot: COLD return") == 0,
            WARM_CHECKS[2], _grep(fresh, "diorama boot", "diorama warm return DISCARDED"))
    g.shot("dio-W-booted")

    left, why = _leave(g, field)
    if not left:
        _unreached(g, WARM_CHECKS[3:], why)
        _back_to_field(g, field)
        return ""
    st = g.state
    d = _dio(st)
    fresh = _new(g, mark)
    g.check(isinstance(r0, int) and d.get("returns") == r0 + 1 and d.get("last_return") == "warm"
            and d.get("last_return_field") == field and d.get("primed") is False and d.get("booted") is False,
            WARM_CHECKS[3],
            f"returns {r0!r}->{d.get('returns')!r} last={d.get('last_return')!r} field={d.get('last_return_field')!r} "
            f"primed={d.get('primed')!r} booted={d.get('booted')!r}")
    g.check(_count(fresh, f"diorama RETURN (warm) -> field {field} resumed through Main_Reinit: every actor restores") == 1
            and _count(fresh, "diorama RETURN (cold)") == 0 and _count(fresh, "diorama RETURN (reinit-missing)") == 0
            and _count(fresh, "did NOT prime") == 0,
            WARM_CHECKS[4], _grep(fresh, "diorama RETURN"))
    p1 = _xz(st)
    g.check(_kept(p1, p0), WARM_CHECKS[5],
            f"back at {_fmt(p1)}, stood at {_fmt(p0)} (moved {_dist(p1, p0):.1f}; the Main_Init placement is "
            f"{_dist(p1, s0):.0f} away)")
    g.shot("dio-W-returned")
    resuming = d.get("resuming")
    moved = 0.0
    if None not in p1:
        g.walk_to(p1[0] + 150.0, p1[1], tolerance=40, strict=False)
        moved = _dist(_xz(g.state), p1)
    g.check(resuming is False and moved >= WALK_MIN, WARM_CHECKS[6],
            f"resuming={resuming!r}; a 150-unit walk moved him {moved:.0f}")
    return ""


def _leg_cold(g, field: int, s0) -> None:
    """Leg C -- the same-run control: a boot with a talk window open must stay cold, and W6's test must read
    NOT kept on its return."""
    g.note("C: the cold control -- boot with the control NPC's window open")
    for p in TALKER_PATH:
        g.walk_to(*p, tolerance=30, strict=False)
    if _poll(g, _free, 6.0, "control back beside the talker") is None:
        _unreached(g, COLD_CHECKS, f"could not reach the talker ({g.state!r})"[:300])
        return
    try:
        g.turn_in_place("up", 10)        # face the talker due north
    except HarnessError as err:
        g.note(f"turn_in_place refused ({str(err)[:120]}) -- interacting as faced")
    opened = g.interact(timeout=6.0)
    g.check(opened is not None and opened.dialog_open,
            "C0: the control NPC's window opened (a non-free-standing state: control off, a window up)",
            repr(opened)[:200])
    if opened is None:
        _unreached(g, COLD_CHECKS, "the talker's window never opened")
        return
    g.wait_frames(15)
    st = g.state
    pc = _xz(st)
    r0 = _dio(st).get("returns")
    mark = _mark(g)
    booted, why = _boot(g)
    if not booted:
        _unreached(g, COLD_CHECKS, why)
        _back_to_field(g, field)
        return
    d = _dio(g.state)
    reason = d.get("boot_why")
    g.check(d.get("boot") == "cold" and isinstance(reason, str) and reason.startswith(COLD_WHYS)
            and d.get("primed") is False,
            COLD_CHECKS[0], f"boot={d.get('boot')!r} why={reason!r} primed={d.get('primed')!r}")
    fresh = _new(g, mark)
    g.check(_count(fresh, "diorama boot: COLD return (") == 1
            and _count(fresh, "diorama boot: WARM return primed") == 0,
            COLD_CHECKS[1], _grep(fresh, "diorama boot"))
    left, why = _leave(g, field)
    if not left:
        _unreached(g, COLD_CHECKS[2:], why)
        _back_to_field(g, field)
        return
    st = g.state
    d = _dio(st)
    fresh = _new(g, mark)
    g.check(isinstance(r0, int) and d.get("returns") == r0 + 1 and d.get("last_return") == "cold"
            and d.get("last_return_field") == field,
            COLD_CHECKS[2], f"returns {r0!r}->{d.get('returns')!r} last={d.get('last_return')!r}")
    g.check(_count(fresh, f"diorama RETURN (cold) -> field {field} re-entered through Main_Init (") == 1
            and _count(fresh, "diorama RETURN (warm)") == 0,
            COLD_CHECKS[3], _grep(fresh, "diorama RETURN"))
    p1 = _xz(st)
    g.check(not _kept(p1, pc) and _dist(p1, s0) <= SPAWN_TOL, COLD_CHECKS[4],
            f"back at {_fmt(p1)}: {_dist(p1, pc):.0f} from where the boot found him {_fmt(pc)}, "
            f"{_dist(p1, s0):.1f} from the Main_Init placement {_fmt(s0)}")
    g.shot("dio-C-returned")


def _leg_gate(g, field: int) -> None:
    """Leg G -- the warm gate's hasReinit row in game: free-standing on a field with no Main_Reinit stays cold.
    [ff9mapkit netsync F3.3] Every way out before the boot records G1/G2 FAILED with the reason (`_unreached`), so a
    missing gate field is a visible red and the check count stays stable -- never a note-only skip."""
    if field == GATE_FIELD:
        _unreached(g, GATE_CHECKS, f"the warm field IS {GATE_FIELD}, so there is no separate gate field to boot on "
                                   f"(its W1 already reports the gate's verdict -- run with the default field for G)")
        return
    try:
        registered = GATE_FIELD in g.registered_fields()[0]
    except (HarnessError, AttributeError, OSError) as err:
        _unreached(g, GATE_CHECKS, f"could not read the field registrations ({str(err)[:160]})")
        return
    if not registered:
        _unreached(g, GATE_CHECKS, f"{GATE_FIELD} is not registered on this install (its DictionaryPatch line is "
                                   f"gone -- another session's deploy can change it)")
        return
    g.note(f"G: the gate's negative -- a free-standing boot on {GATE_FIELD} (no Main_Reinit)")
    g.warp(GATE_FIELD)
    g.wait_frames(45)
    s1 = _xz(g.state)
    st = _stand(g, GATE_SPOT, f"the stand on {GATE_FIELD}")
    if st is None or _dist(_xz(st), s1) < AWAY_MIN:
        _unreached(g, GATE_CHECKS, f"could not stand free {AWAY_MIN:.0f}+ units from {GATE_FIELD}'s arrival "
                                   f"({_fmt(s1)} -> {None if st is None else _fmt(_xz(st))})")
        return
    mark = _mark(g)
    booted, why = _boot(g)
    if not booted:
        _unreached(g, GATE_CHECKS, why)
        _back_to_field(g, GATE_FIELD)
        return
    d = _dio(g.state)
    reason = d.get("boot_why")
    g.check(d.get("boot") == "cold" and isinstance(reason, str) and NO_REINIT in reason and d.get("primed") is False,
            GATE_CHECKS[0], f"boot={d.get('boot')!r} why={reason!r} primed={d.get('primed')!r}")
    left, why = _leave(g, GATE_FIELD)
    if not left:
        _unreached(g, GATE_CHECKS[1:], why)
        _back_to_field(g, GATE_FIELD)
        return
    st = g.state
    d = _dio(st)
    fresh = _new(g, mark)
    p1 = _xz(st)
    g.check(d.get("last_return") == "cold" and _dist(p1, s1) <= SPAWN_TOL
            and _count(fresh, f"diorama RETURN (cold) -> field {GATE_FIELD} re-entered through Main_Init (") == 1,
            GATE_CHECKS[1],
            f"last={d.get('last_return')!r} back at {_fmt(p1)} (arrival {_fmt(s1)}); {_grep(fresh, 'diorama RETURN')}")


def _back_to_field(g, field: int) -> None:
    """After a failed leg: never leave a diorama up (a booted one is asked to leave) or a window open."""
    try:
        if _dio(g.state).get("booted"):
            _ns_verb(g, "dioleave")
            _poll(g, lambda s: s.field_id == field and s.on_field, LEAVE_S, "the field after a failed leg")
        for _ in range(12):
            if not g.state.dialog_open:
                break
            g.press("confirm", 4)
            g.wait_frames(12)
    except HarnessError as err:
        g.note(f"cleanup after a failed leg: {str(err)[:200]}")


def _release(g) -> None:
    """`reset`: the forced role and the encounter booster go; a harness-booted diorama is Left first."""
    try:
        g.send("reset")
        st = _poll(g, lambda s: s.netsync is not None and not _ns(s).get("forced") and not _dio(s).get("booted"),
                   LEAVE_S, "`reset` to release the forced selftest (and any diorama the harness booted)") or g.state
    except HarnessError as err:
        g.check(False, "RESET: `reset` was sent and acknowledged", str(err)[:300])
        return
    ns = _ns(st)
    g.check(ns.get("forced") is False and ns.get("enabled") is False and not _dio(st).get("booted"),
            "RESET: `reset` released the selftest override and left no diorama booted", repr(ns)[:300])
    st = _poll(g, lambda s: s.control, 10.0, "control on after the reset") or g.state
    g.check(st.control, "RESET: the character is not left frozen by a released run", repr(_ns(st))[:200])
