"""Shared helpers for the B4/B5 battle co-op SOLO BENCHES (studies/battle-coop/B4-B5-DESIGN.md section 8.2).

NOT A SCENARIO (no ``run(g)``): the bench scenarios beside it import it --
    coop_battle_host_gates.py   stage 1  (s100)  host command-phase gates
    coop_battle_containment.py  stage 2  (s101)  the guest containment backstop (R9 + G2)
    coop_stock_menu.py          stage 3  (s102)  the stock menu first look + capture (the GO/NO-GO) -- "part 1"
    coop_battle_end_host.py     stage 4  (s103)  the host end block
    coop_battle_end_guest.py    stages 5-6 (s104, s105)  the guest victory presentation + exit with the host
    coop_stock_menu_content.py  stage 7  (s106)  the roster-fed menu content -- coop_stock_menu "part 2"
    coop_stock_menu_live.py     stage 8  (s107)  the production ready mirror + the bench feed -- coop_stock_menu "part 3"
    coop_battle_result_replay.py stages 9-10 (s108, s109)  the host result manifest + the guest's write-nothing replay
    coop_battle_handback.py     stage 11 (s110)  the guest-slot hand-back (G6 + G3)

What lives here, and why once:
  * THE LEDGER (:class:`Ledger`). Every scenario declares its checks up front as a catalog (id -> claim). A leg that
    cannot run records each of its checks FAILED with the reason ("not reached: ..."); the ledger's ``close`` does the
    same for anything never recorded. So the check count is stable on every engine, nothing is skipped silently, and
    nothing passes because it was never asked (the a-check-that-cannot-fail law). In CALIBRATION mode the ledger
    also judges the red set: the lever must turn exactly the predicted checks red (:meth:`Ledger.judge_calibration`).
  * THE DRIVER GAP. ``Session.netsync`` refuses a sub-verb missing from ``NETSYNC_SUBVERBS`` before sending, and the
    committed driver predates s100-s105's verbs (guestslots, bcmd, hostgates, containment, bctl, bmenu, endbench).
    :func:`ns_verb` sends an unknown sub-verb as a RAW ``netsync ...`` step (one note per sub-verb); the agent's own
    gates and refusals come back unchanged. On an engine without the verb the agent answers
    "netsync: unknown sub-verb '<sub>' (...)" -- read by :func:`absent` as "this engine cannot", never as a pass.
  * THE CAPABILITY PROBES. Each stage is told apart by a published KEY (HarnessAgent's header, protocol 5 additive):
    stage 1 ``netsync.battle``; 2 ``netsync.battle.menu.r9_refused``; 3 ``netsync.battle.menu.captures``; 4
    ``netsync.battle.host.end_trail``; 5 ``netsync.battle.end.r8_hits``; 6 ``netsync.battle.end.end_leave``; 7
    ``netsync.battle.menu.content_hits``; 8 ``netsync.battle.menu.stock_owns``; 9 ``netsync.battle.host.
    manifest_captures``; 10 ``netsync.battle.end.replay``; 11 ``netsync.battle.host.handback`` (:data:`PROBES`).
    CAUTION: Stage 11's ops ride the OLD `bench` sub-verb: an engine before s110 reads `bench lapse` / `bench handback` as
    `bench 1` and turns the FIELD-GATE bench ON -- probe first, never send them on an engine without the key. The R3
    patches (s111-s117) have their own ladder, keyed by patch number (:data:`R3_PROBES`, :func:`r3_stage_of`);
    :func:`stage_note` names both in a run's notes.
  * THE ROLE-GATED LEVERS. Every R3 selftest lever's getter (GuestMode, IntroMirrorOn, WaitParityOn, StartHoldCapMs, the
    swirl levers) answers its REST value whenever the selftest role is off -- so a read after `reset` (which releases
    the role) cannot see a bench field the release forgot. :func:`reread_with_role` re-forces the role (which releases
    nothing) and reads the levers WITH it, then resets again.
  * THE DRIVER'S OP TABLES. ``Session.netsync`` also refuses an ``endbench`` op its NETSYNC_ENDBENCH_OPS lacks (a
    driver that predates s109's ``replay`` / ``quit`` / ``fieldsong``); :func:`ns_verb` sends those as raw steps too, so
    the ENGINE's answer -- not a stale driver's -- decides (an engine without them answers "netsync endbench: unknown op
    ..."). A driver that knows them applies its own capability gate first ("publishes no `...`"): :func:`absent` reads
    both as "this engine cannot".
  * The v1 type-4 ROSTER codec in Python (:func:`roster_bytes` / :func:`roster_decode`) -- NetSyncBattle.EncodeRoster /
    ParseRoster byte for byte, for the stage-7 raw-hex bench (`bbench roster <hex>`).
  * The stock-menu driving helpers the stage 7/8/11 benches share (open/close a bench window, walk the cursor onto a
    command or a row by its drawn label, read the target under the cursor) and the frame-window reads ("within N
    frames" judged on the doc's own ``frame`` counter, Time.frameCount, never on wall time).
  * THE PARTY. ``newgame()`` + ``warp()`` leaves Zidane alone in slot 0 (the New-Game base; the sandbox autosave reads
    ``40000_Common/slot`` = [0, 255, 255, 255]). :func:`seed_party` warps through the COOPPARTY bench
    (studies/battle-coop/bench/coopparty.field.toml, id 30604: ``[party] add = vivi, garnet, steiner``) when it is
    registered; otherwise each scenario names the missing member as a precondition red.
  * THE INVARIANTS. Gil, the bag, every member's level/exp/AP, the kill counters and the card count are published by
    no harness key. :func:`fingerprint` forces an autosave (a field entry autosaves into the harness SANDBOX --
    ``save_path``; DisableAutoSave is 0 on this install) and decodes the Memoria extra file with the kit's own reader
    (``ff9mapkit.save.read_extra_tree``), imported from THIS worktree with its ``__file__`` asserted (study scripts
    otherwise pin the MAIN repo -- memory project-ff9-study-scripts-pin-main-repo).
  * The v1 command-frame codec in Python (:func:`cmd_hex` / :func:`decode_cmd`) -- the 9-byte
    ``[ver 1][slot][action][menu][idLo][idHi][maskLo][maskHi][cursor]`` of NetSyncBattle.EncodeCommand, so a captured
    frame is decoded HERE, independently of the engine's TryDecodeCommand.
  * Diorama boot/leave (the coop_diorama_return.py shapes), log reads, the log archive, and the frame tests: the
    whole-frame non-blank test (:func:`png_not_blank`) and the whole-frame LIGHT reading (:func:`frame_light` /
    :func:`settled_frame`: lit vs black over every pixel, shot only after a fade ramp has run out).
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import time
from pathlib import Path

try:                                     # play.py puts tools/ on sys.path before it loads a scenario
    from harness import HarnessError
except ImportError:                      # pragma: no cover - imported outside the driver (py_compile, a stub)
    HarnessError = RuntimeError          # HarnessError IS a RuntimeError

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                   # studies/test-harness/scenarios -> the worktree root

FIELD = 30602                            # LOCKT2 (FF9CustomMap-msgs): entry-0 tag-10 Main_Reinit + [encounter] -> WARM returns
PARTY_FIELD = 30604                      # COOPPARTY: [party] add = vivi, garnet, steiner (see the module note)
SCENE = 67                               # BSC_EF_R007, Evil Forest: one Goblin (33 HP) -- a registered BattleMapList id
PATTERN = 0
POTION = 236                             # RegularItem.Potion (the New-Game bag holds 7)
ATTACK_SUB = 176                         # BattleAbilityId.Attack
CMD_ATTACK = 1                           # BattleCommandId.Attack
BOOT_S = 30.0                            # the swirl into BattleMapDebug
STEADY_S = 45.0                          # boot -> PHASE_NORMAL + the command menu enabled
LEAVE_S = 45.0                           # the Replace back + StartEvents + Main_Reinit/Main_Init + control

# v1 action codes (NetSyncBattle.ActAttack ..)
ACT_ATTACK, ACT_DEFEND, ACT_ABILITY, ACT_ITEM, ACT_INSTANT = 0, 1, 2, 3, 4
# btl_phase (FF9StateBattleSystem)
PHASE_NORMAL, PHASE_MENU_OFF, PHASE_VICTORY, PHASE_DEFEAT, PHASE_CLOSE = 4, 5, 6, 7, 8

ABSENT_MARKERS = ("unknown sub-verb", "unknown op", "publishes no")

#: The capability probe of each B4/B5 stage: the published key whose PRESENCE says the deployed engine has it.
PROBES = {
    1: "netsync.battle",
    2: "netsync.battle.menu.r9_refused",
    3: "netsync.battle.menu.captures",
    4: "netsync.battle.host.end_trail",
    5: "netsync.battle.end.r8_hits",
    6: "netsync.battle.end.end_leave",
    7: "netsync.battle.menu.content_hits",
    8: "netsync.battle.menu.stock_owns",
    9: "netsync.battle.host.manifest_captures",
    10: "netsync.battle.end.replay",
    11: "netsync.battle.host.handback",
}


#: [R3] The capability probe of each battle co-op round-3 patch (studies/battle-coop/R3-DESIGN.md 5.2), keyed by its
#: PATCH number (a separate ladder: :func:`stage_of` stays on the B4/B5 stages 0-11). The R3 benches read their keys from
#: here, so one probe string is one constant. CAUTION as above: s111-s114's ops ride the OLD `bench` sub-verb.
R3_PROBES = {
    111: "netsync.diorama.intro",                   # the intro mirror (`bench intro|cfg`, `dioboot ... skip|play`)
    112: "netsync.diorama.intro.swirl_clamp",       # the diorama swirl clamp (`bench swirl`)
    113: "netsync.battle.host.wait",                # Wait parity (`bench waitparity|ctl`, `bench cfg atb`)
    114: "netsync.battle.host.start_hold",          # the start hold (`bench boot|starthold`)
    115: "netsync.battle.end.flee",                 # the guest's flee presentation (`endbench guest hold|nor9b`)
    116: "netsync.battle.end.flee.msg_gil",         # the host's "Dropped N Gil" relayed (`endbench fleegil`)
    117: "netsync.battle.end.follow_msg",           # the guest's defeat presentation (`endbench kill|phase-defeat`)
    # [ff9mapkit netsync s133] group 2 (renumbered s133-s141): the host action-start lane (`actbench`) -- keyed on
    # `act.host`, never the bare `act` block (s134 adds `act.guest`; audit amendment 13)
    133: "netsync.battle.act.host",
    # [ff9mapkit netsync s134] the guest action replay (the guest `actbench` ops: feed|feedat|tape play|replay|rework|
    # shortcircuit|knob|clear|teardown)
    134: "netsync.battle.act.guest",
    # [ff9mapkit netsync s135] the replay hit hold (the guest `actbench` ops: hold|lifeskip on|off, unit <slot> <state>) --
    # keyed on `act.guest.hold`, never a bare "hold" (s119's `netsync.diorama.hold`, s114's `host.start_hold`)
    135: "netsync.battle.act.guest.hold",
    # [ff9mapkit netsync s136] fallback A, one stock clip per uncovered action (the guest `actbench` op: fallback on|off) --
    # keyed on `act.guest.fallback`
    136: "netsync.battle.act.guest.fallback",
    # [ff9mapkit netsync s137] the trance burst timing (the guest `actbench` op: trancegrace on|off) -- keyed on
    # `act.guest.trance`, never a bare "trance" (`battle.units[].trance_model` is its unit witness, not its probe)
    137: "netsync.battle.act.guest.trance",
    # [ff9mapkit netsync s138] the dress instrument (no verb, op or lever: harness keys only) -- keyed on `netsync.dress.ghost`
    # (s138's own fixed sub-object; s139 adds `netsync.dress.codec`, s140 `netsync.dress.self`). Its OTHER half sits outside
    # netsync: `player.model` (the bench probes both, coop_self_dress.py)
    138: "netsync.dress.ghost",
    # [ff9mapkit netsync s139] the host dress rule and section 8 (the sub-verb `selfdress`) -- keyed on `netsync.dress.codec`
    # (appended after `party`; battlewire.DRESS_PROBES[139]). The driver's capability is `ghost.bench_mask` (s139's too)
    139: "netsync.dress.codec",
    # [ff9mapkit netsync s143] the leader guard (the `bench leaderguard` op -- the s110 hazard again: an older agent reads it
    # as `bench 1`) -- keyed on `netsync.battle.host.guard` (host's last key; s140 / s141 are told by battlewire.DRESS_PROBES)
    143: "netsync.battle.host.guard",
    # [ff9mapkit netsync s144] world-map co-op (the `bench worldfreeze` op -- the s110 hazard again: an s143 agent reads it as
    # `bench 1`) -- keyed on `netsync.world.freeze` (netsync's LAST key's first block; `rejoin` / `waitline` ride beside it)
    144: "netsync.world.freeze",
}


def stage_of(x) -> int:
    """The highest B4/B5 stage whose probe key this document carries (0 = none) -- for the notes only; every check
    reads its own key."""
    top = 0
    for n in sorted(PROBES):
        if has(x, PROBES[n]):
            top = n
    return top


def r3_stage_of(x) -> int:
    """The highest R3 patch whose probe key (:data:`R3_PROBES`) this document carries (0 = none: s110 or older) -- for the
    notes only; every check reads its own key."""
    top = 0
    for n in sorted(R3_PROBES):
        if has(x, R3_PROBES[n]):
            top = n
    return top


def stage_note(x) -> str:
    """Both ladders for a run's notes: "B4/B5 stage 11, R3 s117" (or "R3 none")."""
    r3 = r3_stage_of(x)
    return f"B4/B5 stage {stage_of(x)}, R3 {'s' + str(r3) if r3 else 'none'}"

#: COOP_CALIBRATE=1 runs a scenario's in-run calibration mode (each scenario's note says what it pulls).
CALIBRATE = os.environ.get("COOP_CALIBRATE", "").strip() not in ("", "0")


# ---------------------------------------------------------------------------------------- the ledger
class Ledger:
    """The run's checks, declared up front. ``check`` records one; ``unreached`` records the named ones FAILED with a
    reason; ``close`` fails whatever was never recorded. Ids are the stable handles the calibration judge reads."""

    def __init__(self, g, catalog: dict, *, finals=()):
        self.g = g
        self.catalog = dict(catalog)
        self.done: dict = {}
        #: checks judged in the scenario's `finally` (the release, a whole-run invariant): an early ``close`` leaves them
        #: for that judgement instead of failing them "not reached"
        self.finals = tuple(finals)

    def check(self, cid: str, ok, detail="") -> bool:
        if cid not in self.catalog:
            raise KeyError(f"check {cid!r} is not in this scenario's catalog")
        ok = bool(ok)
        if cid in self.done:
            # a re-record never upgrades a red (the first verdict stands unless both agree)
            ok = ok and self.done[cid]
            self.g.note(f"{cid} re-recorded ({'ok' if ok else 'FAIL'})")
        self.done[cid] = ok
        return self.g.check(ok, f"{cid}: {self.catalog[cid]}", str(detail)[:900])

    def unreached(self, cids, why: str) -> None:
        for cid in cids:
            if cid in self.catalog and cid not in self.done:
                self.check(cid, False, f"not reached: {why}"[:900])

    def pending(self, prefix: str = "") -> list:
        return [c for c in self.catalog if c.startswith(prefix) and c not in self.done]

    def close(self, why: str = "the run ended before this check was reached", *, final: bool = False) -> None:
        """Fail every pending check with ``why`` -- except the ``finals`` unless ``final`` (the scenario's last call)."""
        self.unreached([c for c in self.pending() if final or c not in self.finals], why)

    def failed(self) -> set:
        return {c for c, ok in self.done.items() if not ok}

    def judge_calibration(self, cid: str, predicted, maybe=()) -> bool:
        """The calibration verdict: every ``predicted`` check went red, and nothing else did except ``maybe`` (the
        probabilistic or lever-collateral ones). Recorded as ``cid`` (which must be in the catalog)."""
        predicted, maybe = set(predicted), set(maybe)
        failed = self.failed() - {cid}
        missing = sorted(predicted - failed)              # predicted red, stayed green: the lever did not bite there
        extra = sorted(failed - predicted - maybe)        # red that was not predicted: the lever (or the run) broke more
        return self.check(cid, not missing and not extra,
                          f"predicted reds that stayed GREEN: {missing or 'none'}; unpredicted reds: {extra or 'none'}; "
                          f"maybe-reds that fired: {sorted(failed & maybe) or 'none'}")


# ---------------------------------------------------------------------------------------- observing
def raw(x) -> dict:
    """A State or a ring sample (raw dict) -> the raw document."""
    return x.raw if hasattr(x, "raw") else (x or {})


def path(x, dotted: str, default=None):
    """``path(st, "netsync.battle.menu.r9_refused")`` -- None-safe walk of the raw document."""
    cur = raw(x)
    for key in dotted.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def has(x, dotted: str) -> bool:
    sentinel = object()
    return path(x, dotted, sentinel) is not sentinel


def guard_leader(x) -> int:
    """[ff9mapkit netsync s143] The leader the engine's leader guard takes NOW (NetSyncBattle.LeaderForGuard) off the
    published `netsync.battle.host.guard`: its `leader`, or -1 under the `bench leaderguard off` lever; -1 on an engine
    before s143 (no guard: the positional rule). The s139-s141 dress benches thread it into their twins' expectations
    (review s143 field-3: a bench mask that seats the leader is predicted as the guard moves it, never positionally)."""
    g = path(x, "netsync.battle.host.guard")
    if not isinstance(g, dict) or g.get("off") is True:
        return -1
    v = g.get("leader")
    return int(v) if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else -1


def nsb(x) -> dict:
    b = path(x, "netsync.battle")
    return b if isinstance(b, dict) else {}


def host(x) -> dict:
    return nsb(x).get("host") or {}


def peer(x) -> dict:
    return nsb(x).get("peer") or {}


def bmenu(x) -> dict:
    return nsb(x).get("menu") or {}


def bend(x) -> dict:
    return nsb(x).get("end") or {}


def dio(x) -> dict:
    d = path(x, "netsync.diorama")
    return d if isinstance(d, dict) else {}


def battle(x) -> dict:
    return raw(x).get("battle") or {}


def turn(x) -> dict:
    return battle(x).get("turn") or {}


def hud(x) -> dict:
    h = battle(x).get("hud")
    return h if isinstance(h, dict) else {}


def units(x, player=None) -> list:
    out = list(battle(x).get("units") or [])
    if player is not None:
        out = [u for u in out if bool(u.get("player")) is player]
    return out


def unit(x, slot: int) -> dict | None:
    return next((u for u in units(x) if int(u.get("slot", -1)) == slot), None)


def first_enemy(x) -> dict | None:
    foes = [u for u in units(x, player=False) if u.get("alive") and u.get("targetable", True)]
    return foes[0] if foes else None


def player_slots(x) -> list:
    return sorted(int(u.get("slot", -1)) for u in units(x, player=True))


def mask_bits(m) -> int:
    """A published mask: -1 (no lane) reads as no bits."""
    try:
        m = int(m)
    except (TypeError, ValueError):
        return 0
    return m if m >= 0 else 0


def in_diorama(s) -> bool:
    return s.scene == "BattleMapDebug" and bool(battle(s).get("debug"))


def free(s) -> bool:
    return (s.on_field and s.control and not s.dialog_open and not s.fading
            and s.player_x is not None and s.player_z is not None)


def steady(s) -> bool:
    """A live selftest diorama in its command phase: contained, PHASE_NORMAL, the menu enabled."""
    return (in_diorama(s) and battle(s).get("phase") == PHASE_NORMAL and bool(turn(s).get("enabled"))
            and bmenu(s).get("contained") is not False)


def poll(g, predicate, timeout: float, what: str):
    """``g.wait_for`` that answers None on a timeout: the check that follows carries the verdict. A dead game still
    raises -- every send asserts the process is alive."""
    try:
        return g.wait_for(predicate, timeout=timeout, what=what)
    except HarnessError:
        return None


def watch(g, until, timeout: float, *, on_sample=None):
    """Read every published state (distinct frames) until ``until(state)`` holds or ``timeout`` runs out. Returns
    (samples, the state that ended it or None). For the "every publish from A until B" claims."""
    out, seen = [], None
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = g.state
        if st.frame != seen:
            seen = st.frame
            out.append(st)
            if on_sample is not None:
                on_sample(st)
            try:
                if until(st):
                    return out, st
            except (TypeError, KeyError, AttributeError, IndexError, ValueError):
                pass
        time.sleep(0.004)
    return out, None


def hold_for(g, seconds: float, *, on_sample=None) -> list:
    """Every published state for ``seconds`` (nothing ends it early)."""
    samples, _ = watch(g, lambda s: False, seconds, on_sample=on_sample)
    return samples


# ------------------------------------------------------------------------------------------- the log
def log_lines(g) -> list:
    p = g.engine_log()
    if p is None:
        return []
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def mark(g) -> int:
    return len(log_lines(g))


def new(g, at: int) -> list:
    return log_lines(g)[at:]


def count(lines, needle: str) -> int:
    return sum(1 for ln in lines if needle in ln)


def grep(lines, *needles, limit: int = 600) -> str:
    return " || ".join(ln.split("|", 2)[-1].strip() if "|" in ln else ln
                       for ln in lines if any(n in ln for n in needles))[:limit]


def matching(lines, pattern) -> list:
    rx = re.compile(pattern) if isinstance(pattern, str) else pattern
    return [ln for ln in lines if rx.search(ln)]


def wait_log(g, at: int, needle: str, timeout: float = 3.0) -> list:
    """Wait (bounded) until a line with ``needle`` lands after ``at``; return the new lines either way."""
    deadline = time.time() + timeout
    lines = new(g, at)
    while count(lines, needle) == 0 and time.time() < deadline:
        time.sleep(0.15)
        lines = new(g, at)
    return lines


def archive_log(g, tag: str) -> str:
    """Snapshot Memoria.log into the run's artifact dir NOW (the install is shared: memory
    feedback-archive-capture-logs-immediately). The session archives it again at teardown."""
    try:
        src = g.engine_log()
        dest_dir = getattr(g, "scenario_dir", None) or g.run_dir
        if src is None or dest_dir is None:
            return "no Memoria.log to archive"
        dest = Path(dest_dir) / f"Memoria-{re.sub(r'[^A-Za-z0-9_.-]', '_', tag)}.log"
        shutil.copy2(src, dest)
        return str(dest)
    except (OSError, AttributeError) as err:
        return f"archive failed: {err}"


def ini_value(g, section: str, key: str) -> str | None:
    """The ``[section] key`` value the engine obeys from the install's Memoria.ini, READ-ONLY (harness.artifacts' last-
    wins reader -- the file is never written), or None when absent/unreadable. For a check that is falsifiable only
    under one configuration (it decides whether that check is asked at all)."""
    try:
        from harness.artifacts import read_memoria_ini
        gp = getattr(g, "game_path", None)
        if gp is None:
            return None
        doc = read_memoria_ini(Path(gp) / "Memoria.ini", {section: (key,)}) or {}
    except Exception:                    # noqa: BLE001 - a config read never kills the run
        return None
    hit = {k.lower(): v for k, v in (doc.get(section) or {}).items()}
    return hit.get(key.lower())


# ---------------------------------------------------------------------------------------- acting
_RAW_NOTED: set = set()


def absent(why: str) -> bool:
    """A refusal that says the ENGINE (or this driver) has no such verb/op -- never a behavioural refusal."""
    return any(m in (why or "") for m in ABSENT_MARKERS)


def _driver_lacks_op(g, sub: str, args) -> bool:
    """[ff9mapkit netsync B5] the driver knows the sub-verb but refuses this OP before sending (its op table predates
    the engine's): an ``endbench`` op missing from NETSYNC_ENDBENCH_OPS + NETSYNC_ENDBENCH_UNLISTED (s109's ``replay``
    / ``quit`` / ``fieldsong``)."""
    if sub != "endbench" or not args:
        return False
    ops = getattr(g, "NETSYNC_ENDBENCH_OPS", None)
    if ops is None:
        return False
    op = str(args[0]).strip().lower()
    return op not in tuple(ops) + tuple(getattr(g, "NETSYNC_ENDBENCH_UNLISTED", ()) or ())


def ns_verb(g, sub: str, *args, timeout: float = 20.0):
    """`netsync <sub> [args]` -- through the driver when it knows the sub-verb (and the op), else as a raw step. Raises
    the agent's refusal (a HarnessError/StepRefused) either way."""
    known = getattr(g, "NETSYNC_SUBVERBS", None)
    lacks_op = _driver_lacks_op(g, sub, args)
    if (known is None or sub in known) and not lacks_op:
        return g.netsync(sub, *args, timeout=timeout)
    key = f"{sub} {str(args[0]).lower()}" if lacks_op else sub
    if key not in _RAW_NOTED:
        _RAW_NOTED.add(key)
        g.note(f"driver predates `netsync {key}` (not in Session's "
               f"{'NETSYNC_ENDBENCH_OPS' if lacks_op else 'NETSYNC_SUBVERBS'}) -- sent as a raw step; the agent's own "
               f"gates and refusals still apply")
    g.send("netsync " + " ".join([sub, *(str(a) for a in args)]), timeout=timeout)
    return g.state


def try_ns(g, sub: str, *args, timeout: float = 20.0) -> tuple:
    """(ok, why): the verb's verdict, never raised."""
    try:
        ns_verb(g, sub, *args, timeout=timeout)
        return True, ""
    except HarnessError as err:
        return False, str(err)[:400]


def try_send(g, step: str, timeout: float = 20.0) -> tuple:
    try:
        g.send(step, timeout=timeout)
        return True, ""
    except HarnessError as err:
        return False, str(err)[:400]


# ------------------------------------------------------------------------------------- v1 command frames
def cmd_bytes(slot: int, action: int, menu: int = 0, ident: int = 0, mask: int = 0, cursor: int = 0,
              ver: int = 1) -> bytes:
    """NetSyncBattle.EncodeCommand, byte for byte."""
    return bytes([ver & 0xFF, slot & 0xFF, action & 0xFF, menu & 0xFF, ident & 0xFF, (ident >> 8) & 0xFF,
                  mask & 0xFF, (mask >> 8) & 0xFF, cursor & 0xFF])


def hexstr(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def cmd_hex(*a, **k) -> str:
    return hexstr(cmd_bytes(*a, **k))


def decode_cmd(text) -> dict | None:
    """The host's TryDecodeCommand, re-implemented: a ``"01 01 00 ..."`` (or ``01-01-..``) string -> the fields, or
    None (malformed: short or not ver 1)."""
    try:
        b = bytes(int(t, 16) for t in re.split(r"[\s\-]+", str(text).strip()) if t)
    except ValueError:
        return None
    if len(b) < 9 or b[0] != 1:
        return None
    return {"slot": b[1], "action": b[2], "menu": b[3], "id": b[4] | (b[5] << 8), "mask": b[6] | (b[7] << 8),
            "cursor": b[8]}


# -------------------------------------------------------------------------------------- setup + party
def provenance(g) -> None:
    """Note where the driver package came from (play.py run from THIS worktree puts its own tools/ first)."""
    mod = sys.modules.get("harness")
    where = getattr(mod, "__file__", None)
    mine = where is not None and Path(where).resolve().is_relative_to(REPO)
    g.note(f"harness package: {where} ({'this worktree' if mine else 'NOT this worktree: ' + str(REPO)})")


def seed_party(g, *, back_to: int) -> str:
    """Warp through COOPPARTY when it is registered (its Main_Init adds vivi/garnet/steiner), then to ``back_to``.
    Returns a one-line account for the notes; the scenarios judge the party they actually got."""
    try:
        regs = g.registered_fields()[0]
    except (HarnessError, AttributeError, OSError) as err:
        return f"party seeder: could not read the registrations ({str(err)[:120]})"
    if PARTY_FIELD not in regs:
        return (f"party seeder: {PARTY_FIELD} (COOPPARTY) is not registered -- the New-Game party stands (deploy: "
                f"py tools/deploy_field.py studies/battle-coop/bench/coopparty.field.toml --id {PARTY_FIELD} "
                f"--mod-folder FF9CustomMap-msgs, then relaunch)")
    g.warp(PARTY_FIELD)
    g.wait_frames(45)                    # Main_Init's B_PARTYADD ops run on entry
    g.warp(back_to)
    return f"party seeder: warped through {PARTY_FIELD} (COOPPARTY: +vivi +garnet +steiner)"


def setup(g, field: int, *, label: str) -> tuple:
    """newgame -> (party seeder) -> the bench field -> encounters off -> the forced selftest role. Returns
    (selftest_ok, detail)."""
    provenance(g)
    g.note(label)
    g.newgame()
    g.note(seed_party(g, back_to=field))
    if g.state.field_id != field:
        g.warp(field)
    try:
        g.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        g.note(f"noencounter refused ({str(err)[:120]}) -- a random battle may interrupt a leg")
    g.wait_frames(45)
    ok, why = try_ns(g, "selftest", 1)
    st = g.state
    ns = st.netsync or {}
    good = ok and bool(ns.get("selftest")) and bool(ns.get("forced"))
    return good, (why or f"selftest={ns.get('selftest')!r} forced={ns.get('forced')!r} role={ns.get('role')!r}")


def release(g, ledger: Ledger | None = None, cid: str | None = None, *, expect_lines=(), at: int | None = None,
            extra=None) -> None:
    """`reset`: every lever, the forced role, parked frames, a harness diorama. Optionally judged as ``cid``: the role
    is released, no diorama is left booted, each ``expect_lines`` needle logged after ``at``, and -- [ff9mapkit netsync
    s139] -- ``extra(state)`` -> (ok, detail) on the post-reset state, when given (a lever the bench HELD into the reset
    read back released)."""
    try:
        g.send("reset")
        st = poll(g, lambda s: s.netsync is not None and not (s.netsync or {}).get("forced") and not dio(s).get("booted"),
                  LEAVE_S, "`reset` to release the forced selftest (and any diorama the harness booted)") or g.state
    except HarnessError as err:
        if ledger is not None and cid is not None:
            ledger.check(cid, False, f"`reset` failed: {str(err)[:300]}")
        return
    if ledger is None or cid is None:
        return
    lines = new(g, at) if at is not None else []
    missing = [n for n in expect_lines if count(lines, n) == 0]
    ns = st.netsync or {}
    x_ok, x_why = extra(st) if extra is not None else (True, "")
    ledger.check(cid, ns.get("forced") is False and not dio(st).get("booted") and not missing and x_ok,
                 f"forced={ns.get('forced')!r} booted={dio(st).get('booted')!r} missing lines={missing}; "
                 + (f"{x_why}; " if x_why else "")
                 + f"{grep(lines, 'released with the harness', 'override released')}")


def reread_with_role(g) -> tuple:
    """[R3] AFTER a :func:`release`: force the selftest role AGAIN, read one state WITH it, then `reset` once more.
    Every R3 lever's getter answers its rest value while the role is off (GuestMode, IntroMirrorOn, WaitParityOn,
    StartHoldCapMs, the swirl levers: `bench field && IsSelfTestRole`), so the read straight after `reset` is green
    whatever the bench field holds; `netsync selftest 1` re-forces the role and releases NOTHING
    (NetSyncClient.HarnessSelfTest), so this read shows the bench fields themselves. (state or None, why)."""
    ok, why = try_ns(g, "selftest", 1)
    if not ok:
        return None, f"the re-read's `netsync selftest 1` was refused: {why}"
    st = poll(g, lambda s: bool((s.netsync or {}).get("forced")) and bool((s.netsync or {}).get("selftest")), 5.0,
              "the re-forced selftest role")
    release(g)
    if st is None:
        return None, "the selftest role never came back for the re-read"
    return st, ""


# ------------------------------------------------------------------------------------------ the diorama
BOOT_REFUSED = "diorama boot REFUSED:"
FADE_REFUSAL = "diorama boot REFUSED: a scene fade is in flight"


def boot(g, scene: int = SCENE, pattern: int = PATTERN) -> tuple:
    """`netsync dioboot` and wait for BattleMapDebug. (booted, why-not). A boot refused because a scene fade was in
    flight is retried once (Boot names its reason only in Memoria.log)."""
    why = ""
    for attempt in range(2):
        at = mark(g)
        try:
            ns_verb(g, "dioboot", scene, pattern)
            why = ""
            break
        except HarnessError as err:
            why = str(err)[:300]
            if "diorama boot REFUSED" in why:
                lines = wait_log(g, at, BOOT_REFUSED, 2.0)
                logged = grep(lines, BOOT_REFUSED, limit=240)
                if logged:
                    why = f"{why} -- log: {logged}"
            if FADE_REFUSAL not in why or attempt:
                return False, f"dioboot refused: {why}"
            g.wait_frames(30)
    st = poll(g, in_diorama, BOOT_S, "the diorama (BattleMapDebug, battle.debug) to come up")
    if st is None:
        s = g.state
        return False, f"the diorama never came up (scene={s.scene!r} battle={battle(s)!r})"[:300]
    return True, ""


def wait_steady(g, timeout: float = STEADY_S):
    """The diorama in its command phase (units final, PHASE_NORMAL, the menu enabled)."""
    return poll(g, steady, timeout, "the diorama's command phase (PHASE_NORMAL + turn.enabled)")


def leave(g, field: int, *, timeout: float = LEAVE_S) -> tuple:
    """`netsync dioleave` (request-only; a fade defers it -- retried) and wait for the field, playable. (ok, why)."""
    for attempt in range(4):
        ok, why = try_ns(g, "dioleave")
        if ok:
            break
        if "no diorama is booted" in why:
            break                         # it left on its own (an end-leave): wait for the field below
        if "deferred" not in why or attempt == 3:
            return False, f"dioleave refused: {why}"
        g.wait_frames(30)
    return arrive(g, field, timeout=timeout)


def arrive(g, field: int, *, timeout: float = LEAVE_S) -> tuple:
    st = poll(g, lambda s: s.field_id == field and free(s), timeout, f"field {field} to be playable after the return")
    if st is None:
        s = g.state
        return False, (f"no playable return to field {field} (field={s.field_id} ui={s.ui_state!r} control={s.control} "
                       f"scene={s.scene!r} booted={dio(s).get('booted')!r})")
    g.wait_frames(10)
    return True, ""


def back_to_field(g, field: int) -> None:
    """After a failed leg: never leave a diorama up or a window open."""
    try:
        if dio(g.state).get("booted"):
            try_ns(g, "dioleave")
            poll(g, lambda s: s.field_id == field and s.on_field and not dio(s).get("booted"), LEAVE_S,
                 "the field after a failed leg")
        for _ in range(12):
            if not g.state.dialog_open:
                break
            g.press("confirm", 4)
            g.wait_frames(12)
    except HarnessError as err:
        g.note(f"cleanup after a failed leg: {str(err)[:200]}")


# ------------------------------------------------------------------------------------- the battle HUD
def strip_tags(text) -> str:
    out, depth = [], 0
    for ch in str(text or ""):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out).strip()


def cursor_label(st) -> str:
    c = st.battle_cursor
    return strip_tags(c.get("label") or "")


def cursor_group(st) -> str:
    return st.battle_cursor.get("group") or ""


def walk_to_label(g, want: str, *, group: str, max_steps: int = 24) -> tuple:
    """Move the cursor of ``group`` onto ``want`` (tag-stripped, case-insensitive) WITHOUT confirming. Searches like
    Session.battle_pick: down to the edge, up to the edge, then the neighbouring columns. (found, seen-labels)."""
    want_l = strip_tags(want).lower()
    seen: list = []
    steps = 0

    def here():
        st = g.state
        return cursor_group(st), cursor_label(st)

    def nudge(button) -> bool:
        nonlocal steps
        _, before = here()
        g.press(button, 4)
        g.wait_frames(10)
        steps += 1
        return here()[1] != before

    def run(button) -> bool:
        stalls = 0
        while steps < max_steps:
            grp, cur = here()
            if grp != group:
                return False
            if cur.lower() == want_l:
                return True
            if cur and cur not in seen:
                seen.append(cur)
            if nudge(button):
                stalls = 0
            else:
                stalls += 1
                if stalls >= 2:
                    return False
        return False

    for column in (None, "right", "left"):
        if steps >= max_steps:
            break
        if column is not None and not nudge(column):
            continue
        if run("down") or run("up"):
            return True, seen
    grp, cur = here()
    return (grp == group and cur.lower() == want_l), seen


def wait_panel(g, panel: str, timeout: float = 4.0):
    return poll(g, lambda s: hud(s).get("panel") == panel, timeout, f"battle.hud.panel == {panel!r}")


# --------------------------------------------------------------------------------------------- frames
#: frame_light: a pixel is LIT when its luma (Pillow's "L": ITU-R 601-2) exceeds LIT_LUMA. A black-faded field is 0
#: everywhere a fade covers; only the UI layer (the booster icon setup() turns on) draws over it.
LIT_LUMA = 24
#: ...a frame reads "lit" when at least LIT_FRAC of ALL its pixels are lit, "black" when at most BLACK_FRAC are (room for
#: the small UI overlays), "dim" in between -- neither verdict, so a lit check and a black check both go red on it.
#: Calibrated on the ARTLESS bench field 30602 (black background; only actors and props draw): its lit return reads
#: ~3.5% lit pixels, so a 10% bar called it "dim". A fade-covered frame keeps only the booster icon (~0.2%).
LIT_FRAC, BLACK_FRAC = 0.01, 0.005
#: FF9Wipe_FadeInEx(256) -- the stock result-hide tail the stage-6 return lift runs -- ramps over 256 SceneDirector
#: ServiceFade steps, and the field calls ServiceFade once per FIELD LOGIC tick (HonoluluFieldMain, 30 Hz), not once
#: per render frame: so the ramp is waited out on the wall clock, never in harness `wait` frames (~31 or ~60 a second).
FADE_IN_256_S = 256 / 30.0


def frame_light(p) -> dict | None:
    """The WHOLE frame's light: ``{"w", "h", "mean" (luma 0-255), "lit" (the fraction of pixels over LIT_LUMA)}`` over
    every row and column, PNG filters undone (Pillow -- the kit's one hard runtime dependency). None when unreadable."""
    try:
        from PIL import Image
        with Image.open(p) as im:
            im.load()
            lum = im.convert("L")
        w, h = lum.size
        hist = lum.histogram()
    except Exception:                    # noqa: BLE001 - a frame reading never kills the run
        return None
    n = sum(hist)
    if n <= 0:
        return None
    mean = sum(i * c for i, c in enumerate(hist)) / n
    return {"w": w, "h": h, "mean": round(mean, 2), "lit": round(sum(hist[LIT_LUMA + 1:]) / n, 4)}


def frame_reads(light: dict | None) -> str | None:
    """'lit' / 'black' / 'dim' for a :func:`frame_light` reading (None when there is none)."""
    if not light:
        return None
    if light["lit"] >= LIT_FRAC:
        return "lit"
    return "black" if light["lit"] <= BLACK_FRAC else "dim"


def settled_frame(g, name: str, *, after_s: float = FADE_IN_256_S + 0.5, every_s: float = 1.0, tries: int = 4) -> tuple:
    """Wait ``after_s`` on the wall clock (a whole FF9Wipe_FadeInEx(256) ramp by default), then shoot ``<name>-<i>``
    (a distinct file per shot: a re-used name is found on disk before the new frame lands) until two shots in a row
    agree -- the same :func:`frame_reads` verdict and a mean within 2 luma levels -- up to ``tries`` shots.
    (path or None, light or None, settled, trail of readings)."""
    hold_for(g, after_s)
    trail: list = []
    prev = None
    last_path, last_light = None, None
    for i in range(tries):
        p, why = shot(g, f"{name}-{i + 1}")
        light = frame_light(p) if p is not None else None
        trail.append(light if light is not None else (why or "undecodable"))
        if light is not None:
            if prev is not None and frame_reads(prev) == frame_reads(light) and abs(prev["mean"] - light["mean"]) <= 2.0:
                return p, light, True, trail
            prev, last_path, last_light = light, p, light
        if i + 1 < tries:
            hold_for(g, every_s)
    return last_path, last_light, False, trail


def png_not_blank(p, *, min_distinct: int = 8) -> bool:
    """play.py's test, over the WHOLE frame: at least ``min_distinct`` distinct channel values across every pixel (PNG
    filter bytes excluded) -- a solid frame fails. Falls back to play.py's IDAT read when Pillow cannot decode it."""
    try:
        from PIL import Image
        with Image.open(p) as im:
            im.load()
            hist = im.convert("RGB").histogram()           # 3 bands x 256 bins
        return sum(1 for v in range(256) if hist[v] or hist[256 + v] or hist[512 + v]) >= min_distinct
    except Exception:                    # noqa: BLE001 - fall through to the byte read
        pass
    try:
        import zlib
        data = Path(p).read_bytes()
        idat, i = b"", 8
        while i + 8 <= len(data):
            length = int.from_bytes(data[i:i + 4], "big")
            if data[i + 4:i + 8] == b"IDAT":
                idat += data[i + 8:i + 8 + length]
            i += 12 + length
        if not idat:
            return Path(p).stat().st_size > 1000
        return len(set(zlib.decompress(idat)[:200000])) >= min_distinct
    except Exception:                    # noqa: BLE001 - a frame test never kills the run
        try:
            return Path(p).stat().st_size > 1000
        except OSError:
            return False


def shot(g, name: str):
    """g.shot that answers (path or None, why)."""
    try:
        return g.shot(name), ""
    except HarnessError as err:
        return None, str(err)[:200]


# ------------------------------------------------------------------------------------- the invariants
_KIT = None


def kit_save():
    """``ff9mapkit.save`` from THIS worktree, or raise naming where it resolved instead."""
    global _KIT
    if _KIT is not None:
        return _KIT
    pkg_root = REPO / "ff9mapkit"
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    import ff9mapkit                                       # noqa: E402 - path pinned above
    where = Path(getattr(ff9mapkit, "__file__", "") or ".").resolve()
    if not where.is_relative_to(pkg_root):
        raise RuntimeError(f"ff9mapkit resolved to {where}, not this worktree's {pkg_root} (an editable install of "
                           f"another tree was imported first)")
    from ff9mapkit import save as kit                     # noqa: E402
    _KIT = kit
    return kit


def autosave_extra(st) -> Path | None:
    sp = raw(st).get("save_path")
    if not sp or not str(sp).endswith(".dat"):
        return None
    return Path(str(sp)[:-4] + "_Memoria_Autosave.dat")


_COUNTERS = ("escape_no", "steal_no", "frog_no", "humanoid_no", "beast_no", "devil_no", "dragon_no", "undead_no",
             "stone_no", "soul_no", "flight_no", "summon_flag")


def _fp_from_tree(t: dict) -> dict:
    c = t.get("40000_Common") or {}
    players = []
    for p in c.get("players") or []:
        info = p.get("info") or {}
        players.append((p.get("name"), info.get("slot_no"), p.get("level"), p.get("exp"),
                        repr(p.get("pa_extended"))))
    mg = t.get("30000_MiniGame") or {}
    return {
        "gil": c.get("gil"),
        "items": sorted((i.get("id"), i.get("count")) for i in (c.get("items") or []) if isinstance(i, dict)),
        "rare": repr(c.get("rareItemsEx")),
        "players": players,
        "counters": {k: c.get(k) for k in _COUNTERS},
        "kills": repr(c.get("kills_per_model")),
        "cards": len(mg.get("MiniGameCard") or []),
        "card_record": (mg.get("sWin"), mg.get("sLose"), mg.get("sDraw")),
        "slot": repr(c.get("slot")),
    }


def fingerprint(g, *, field: int, timeout: float = 8.0) -> tuple:
    """Force an autosave (a warp into ``field`` is a field entry), wait for the sandbox extra file to be rewritten,
    and decode the invariants. (fp or None, why). ``battle_no`` is reported apart (a diorama's InitBattle bumps it)."""
    try:
        kit = kit_save()
    except Exception as err:                               # noqa: BLE001 - the instrument, not the game
        return None, f"the kit's save reader is unavailable: {str(err)[:200]}"
    st = g.state
    extra = autosave_extra(st)
    if extra is None:
        return None, f"no sandbox save_path published ({raw(st).get('save_path')!r})"
    if raw(st).get("save_sandboxed") is not True:
        return None, "the saves are not sandboxed -- never read (or write) the owner's autosave"
    before = extra.stat().st_mtime if extra.exists() else 0.0
    try:
        g.warp(field)
    except HarnessError as err:
        return None, f"the autosave warp to {field} failed: {str(err)[:200]}"
    deadline = time.time() + timeout
    fp = None
    while time.time() < deadline and fp is None:
        if extra.exists() and extra.stat().st_mtime > before:
            time.sleep(0.4)                                # let the writer finish (File.OpenWrite, no truncate)
            try:
                tree = kit.read_extra_tree(str(extra))
                if isinstance(tree, dict) and "40000_Common" in tree:
                    fp = _fp_from_tree(tree)
                    fp["_battle_no"] = (tree.get("40000_Common") or {}).get("battle_no")
                    continue
            except Exception:                              # noqa: BLE001 - a torn read: retry
                pass
        time.sleep(0.25)
    # the warp's own fade must be over before the caller boots anything (a dioboot refuses mid-fade)
    poll(g, lambda s: s.field_id == field and free(s), 15.0, f"field {field} playable after the autosave warp")
    g.wait_frames(20)
    if fp is None:
        return None, f"the warp into {field} wrote no fresh autosave within {timeout:.0f}s ({extra.name})"
    return fp, ""


def fp_diff(a: dict, b: dict) -> list:
    return [k for k in a if not k.startswith("_") and a.get(k) != b.get(k)]


def seated_party(t_or_fp) -> list:
    """The seated party's character ids (slot_no) in RAW party-slot order, None for an empty seat -- from an extra tree
    (``40000_Common.slot``) or a :func:`fingerprint` (its ``slot`` repr). [] when unreadable."""
    try:
        if isinstance(t_or_fp, dict) and "40000_Common" in t_or_fp:
            raw_slots = (t_or_fp.get("40000_Common") or {}).get("slot")
        else:
            import ast
            raw_slots = ast.literal_eval(str((t_or_fp or {}).get("slot")))
        return [None if (s is None or int(s) >= 255) else int(s) for s in list(raw_slots)[:4]]
    except Exception:                    # noqa: BLE001 - an instrument read never kills the run
        return []


def extra_tree(g, *, field: int, timeout: float = 8.0) -> tuple:
    """Like :func:`fingerprint`, but returns the WHOLE decoded extra tree (the members' levels/exp, the card list, the
    bag) for benches that need more than the invariants. (tree or None, why). Forces an autosave by warping."""
    try:
        kit = kit_save()
    except Exception as err:                               # noqa: BLE001 - the instrument, not the game
        return None, f"the kit's save reader is unavailable: {str(err)[:200]}"
    st = g.state
    extra = autosave_extra(st)
    if extra is None:
        return None, f"no sandbox save_path published ({raw(st).get('save_path')!r})"
    if raw(st).get("save_sandboxed") is not True:
        return None, "the saves are not sandboxed -- never read (or write) the owner's autosave"
    before = extra.stat().st_mtime if extra.exists() else 0.0
    try:
        g.warp(field)
    except HarnessError as err:
        return None, f"the autosave warp to {field} failed: {str(err)[:200]}"
    deadline = time.time() + timeout
    tree = None
    while time.time() < deadline and tree is None:
        if extra.exists() and extra.stat().st_mtime > before:
            time.sleep(0.4)
            try:
                t = kit.read_extra_tree(str(extra))
                if isinstance(t, dict) and "40000_Common" in t:
                    tree = t
                    continue
            except Exception:                              # noqa: BLE001 - a torn read: retry
                pass
        time.sleep(0.25)
    poll(g, lambda s: s.field_id == field and free(s), 15.0, f"field {field} playable after the autosave warp")
    g.wait_frames(20)
    if tree is None:
        return None, f"the warp into {field} wrote no fresh autosave within {timeout:.0f}s ({extra.name})"
    return tree, ""


# ------------------------------------------------------------------------------- the v1 type-4 roster codec
def roster_bytes(slots: dict, items: list) -> bytes:
    """NetSyncBattle.EncodeRoster / BuildRoster's v1 layout, byte for byte:
    ``[01][slotCount]`` then per slot ``[wire][cmdCount]`` per command ``[menu][cmdId u16][type][tinfo][abilCount]`` per
    ability ``[id u16][mp][flags b0 enabled b1 forDead][tinfo]``, then ``[itemCount u16]`` per item ``[id u16][count]
    [tinfo][forDead]`` (little-endian). ``slots`` = {wire: [{menu, cmd, type, tinfo, abils: [{id, mp, on, dead,
    tinfo}]}]}; ``items`` = [{id, count, tinfo, dead}]."""
    out = bytearray([1, len(slots) & 0xFF])
    for w in sorted(slots):
        cmds = slots[w] or []
        out += bytes([int(w) & 0xFF, len(cmds) & 0xFF])
        for c in cmds:
            out += bytes([int(c["menu"]) & 0xFF]) + (int(c["cmd"]) & 0xFFFF).to_bytes(2, "little")
            out += bytes([int(c.get("type", 0)) & 0xFF, int(c.get("tinfo", 0)) & 0xFF])
            abils = list(c.get("abils") or [])[:255]
            out.append(len(abils))
            for a in abils:
                out += (int(a["id"]) & 0xFFFF).to_bytes(2, "little")
                out += bytes([min(max(int(a.get("mp", 0)), 0), 255),
                              (1 if a.get("on") else 0) | (2 if a.get("dead") else 0), int(a.get("tinfo", 0)) & 0xFF])
    out += (len(items) & 0xFFFF).to_bytes(2, "little")
    for it in items:
        out += (int(it["id"]) & 0xFFFF).to_bytes(2, "little")
        out += bytes([min(max(int(it.get("count", 0)), 0), 255), int(it.get("tinfo", 0)) & 0xFF, 1 if it.get("dead") else 0])
    return bytes(out)


def roster_decode(data: bytes) -> dict | None:
    """NetSyncBattle.ParseRoster, re-implemented: the bytes -> {"slots": {wire: [cmd...]}, "items": [...]} in
    :func:`roster_bytes`' shape, or None (not ver 1, or truncated -- ParseRoster's catch). Trailing bytes are ignored,
    as ParseRoster ignores them."""
    b = bytes(data or b"")
    pos = 0

    def take(n: int) -> bytes:
        nonlocal pos
        if pos + n > len(b):
            raise ValueError("truncated")
        chunk = b[pos:pos + n]
        pos += n
        return chunk

    try:
        if take(1)[0] != 1:
            return None
        slots = {}
        for _ in range(take(1)[0]):
            w, n = take(2)
            cmds = []
            for _ in range(n):
                menu = take(1)[0]
                cmd = int.from_bytes(take(2), "little")
                typ, tinfo, na = take(3)
                abils = []
                for _ in range(na):
                    aid = int.from_bytes(take(2), "little")
                    mp, flags, at = take(3)
                    abils.append({"id": aid, "mp": mp, "on": bool(flags & 1), "dead": bool(flags & 2), "tinfo": at})
                cmds.append({"menu": menu, "cmd": cmd, "type": typ, "tinfo": tinfo, "abils": abils})
            slots[w] = cmds
        items = []
        for _ in range(int.from_bytes(take(2), "little")):
            iid = int.from_bytes(take(2), "little")
            cnt, tinfo, dead = take(3)
            items.append({"id": iid, "count": cnt, "tinfo": tinfo, "dead": bool(dead)})
        return {"slots": slots, "items": items}
    except ValueError:
        return None


def roster_published(decoded: dict) -> dict:
    """A decoded roster in the shape `netsync.battle.menu.roster` publishes it (AppendStockContent): {slots: [{wire,
    cmds: [{menu, cmd, type, abils (count), on (enabled count)}]}], items: [{id, count}]} -- for comparing the engine's
    parse with this module's."""
    return {"slots": [{"wire": w, "cmds": [{"menu": c["menu"], "cmd": c["cmd"], "type": c["type"], "abils": len(c["abils"]),
                                            "on": sum(1 for a in c["abils"] if a["on"])} for c in decoded["slots"][w]]}
                      for w in sorted(decoded["slots"])],
            "items": [{"id": i["id"], "count": i["count"]} for i in decoded["items"]]}


# ----------------------------------------------------------------------------- driving the stock menu
CMD_GROUP, TARGET_GROUP, ABILITY_GROUP, ITEM_GROUP = "Battle.Command", "Battle.Target", "Battle.Ability", "Battle.Item"
#: BattleCommandMenu (Memoria/Data/Battle/BattleCommandMenu.cs)
MENU_ATTACK, MENU_DEFEND, MENU_ABILITY1, MENU_ABILITY2, MENU_ITEM, MENU_CHANGE, MENU_ACCESS = 0, 1, 2, 3, 4, 5, 7
MENU_NAMES = {0: "Attack", 1: "Defend", 2: "Ability1", 3: "Ability2", 4: "Item", 5: "Change", 7: "AccessMenu"}


def digits(text) -> str:
    """The digits of a label as drawn (tags stripped): '1,234,567' -> '1234567'. '' for none."""
    return re.sub(r"[^0-9]", "", strip_tags(text))


def menus_of(g, slot: int) -> dict:
    """`menus <slot>` as a RAW step (Session.menus refuses a diorama) -> battle.menu stamped for that slot, or {}. Its
    items are the guest's REAL bag (CollectNetMenus reads FF9.item; only battle-usable items are listed)."""
    ok, why = try_send(g, f"menus {int(slot)}")
    if not ok:
        g.note(f"menus {slot} refused: {why[:160]}")
        return {}
    st = poll(g, lambda s: int(battle(s).get("menu", {}).get("slot", -1)) == int(slot), 3.0, f"the menu for slot {slot}")
    return battle(st).get("menu", {}) if st is not None else {}


def bag_count(menu: dict, item_id) -> int | None:
    """The bag count of ``item_id`` in a :func:`menus_of` read: 0 when absent, None when the read failed."""
    if not menu:
        return None
    it = next((i for i in menu.get("items", []) if int(i.get("sub", -1)) == int(item_id)), None)
    return 0 if it is None else int(it.get("count", -1))


def hud_cmd(st, menu: int) -> dict | None:
    return next((r for r in hud(st).get("commands") or [] if int(r.get("menu", -9)) == int(menu)), None)


def hud_row(st, ident) -> dict | None:
    return next((r for r in hud(st).get("rows") or [] if int(r.get("id", -9)) == int(ident)), None)


def hud_brief(st) -> str:
    h = hud(st)
    return (f"panel={h.get('panel')!r} group={h.get('group')!r} slot={h.get('slot')!r} mirrored={h.get('mirrored')!r} "
            f"cursor={cursor_label(st)!r}")


def captured(st) -> dict:
    c = bmenu(st).get("captured")
    return c if isinstance(c, dict) else {}


def to_root(g) -> bool:
    """Cancel back to the command root (a target cursor or a list left open). False when no window is open."""
    for _ in range(4):
        st = g.state
        if hud(st).get("panel") == "command" and cursor_group(st) == CMD_GROUP:
            return True
        if hud(st).get("panel") in ("none", None) or st.turn_slot < 0:
            return False
        g.press("cancel", 4)
        g.wait_frames(14)
    st = g.state
    return hud(st).get("panel") == "command" and cursor_group(st) == CMD_GROUP


def bmenu_open(g, slot: int, timeout: float = 3.0) -> tuple:
    """`bmenu open <slot>` (the stage-3 bench opener) and wait for its command root. (ok, why, state)."""
    ok, why = try_ns(g, "bmenu", "open", slot)
    if not ok:
        return False, why, g.state
    st = poll(g, lambda s: s.turn_slot == slot and hud(s).get("panel") == "command" and cursor_group(s) == CMD_GROUP,
              timeout, f"slot {slot}'s command root")
    return (st is not None, "" if st else f"the command root never opened for slot {slot} (turn.slot={g.state.turn_slot} "
                                          f"{hud_brief(g.state)})", st or g.state)


def bmenu_close(g, slot: int) -> None:
    try_ns(g, "bmenu", "close", slot)
    poll(g, lambda s: s.turn_slot != slot, 2.0, f"slot {slot}'s panel to close")


#: The command panel's cursor layout: a TWO-COLUMN grid that does NOT wrap vertically (measured live 2026-09-04 -- from
#: Steal, `down` reaches Item and then moves nothing; the stand-in models the same): row = menu // 2, column = menu % 2
#: (Attack Defend / Ability1 Ability2 / Item Change).
def walk_to_menu(g, menu: int) -> bool:
    """Cursor onto command ``menu`` by its GRID POSITION (no label read): to the top-left corner, then down / right.
    Only a fallback for :func:`pick_command` -- whatever opens is still judged by the panel and the rows it draws."""
    if not 0 <= int(menu) <= 5:
        return False
    for button, n in (("up", 3), ("left", 1)):
        for _ in range(n):
            g.press(button, 4)
            g.wait_frames(8)
    for _ in range(int(menu) // 2):
        g.press("down", 4)
        g.wait_frames(8)
    if int(menu) % 2:
        g.press("right", 4)
        g.wait_frames(8)
    return cursor_group(g.state) == CMD_GROUP


def pick_command(g, menu: int, *, expect_panel: str) -> tuple:
    """Cursor onto the command of ``menu`` (by its DRAWN label; by its grid position when the cursor never shows that
    label), Confirm, wait for ``expect_panel``. (ok, why, st). A panel that did not open is cancelled back to the root so
    the next leg is not stranded."""
    st = g.state
    row = hud_cmd(st, menu)
    if row is None or not row.get("label"):
        return False, f"no drawn command for menu {menu} ({hud(st).get('commands')})", st
    if not to_root(g):
        return False, f"not at the command root ({hud_brief(g.state)})", g.state
    found, seen = walk_to_label(g, row["label"], group=CMD_GROUP)
    if not found:
        if not walk_to_menu(g, menu):
            return False, f"the cursor never reached {row['label']!r} (saw {seen}), nor its grid position", g.state
        g.note(f"pick_command: the cursor never showed the drawn label {row['label']!r} (saw {seen}) -- walked to menu "
               f"{menu} by its grid position (cursor now {cursor_label(g.state)!r})")
    g.press("confirm", 4)
    st = wait_panel(g, expect_panel)
    if st is None:
        why = f"Confirm on {row['label']!r} opened no {expect_panel!r} panel ({hud_brief(g.state)})"
        to_root(g)
        return False, why, g.state
    return True, "", st


def pick_row(g, ident, *, group: str) -> tuple:
    """Cursor onto the VISIBLE row whose id is ``ident`` (by its drawn label), no Confirm. (ok, why)."""
    st = g.state
    row = hud_row(st, ident)
    if row is None or not row.get("label"):
        return False, (f"row id {ident} is not among the visible rows "
                       f"{[(r.get('id'), r.get('label'), r.get('state')) for r in hud(st).get('rows') or []][:10]}")
    found, seen = walk_to_label(g, row["label"], group=group)
    return found, ("" if found else f"the cursor never reached {row['label']!r} (saw {seen})")


def back_to_root(g) -> bool:
    g.press("cancel", 4)
    return poll(g, lambda s: hud(s).get("panel") == "command" and cursor_group(s) == CMD_GROUP, 3.0,
                "Cancel back to the command root") is not None


def target_mask(st) -> tuple:
    """The target bit of the unit under the target cursor (by its drawn name) and that name. A PARTY row's label is a
    name TOKEN ([FRYA]) that strip_tags empties -- its NGUI button names it instead ("Character k" = slot k-1)."""
    name = cursor_label(st)
    hits = [u for u in units(st) if name and strip_tags(u.get("name") or u.get("name_raw") or "") == name]
    if len(hits) == 1:
        return int(hits[0]["id"]), name
    button = str(st.battle_cursor.get("button") or "")
    if cursor_group(st) == TARGET_GROUP and button.startswith("Character "):
        try:
            k = int(button.split()[1])
        except ValueError:
            return None, name
        return (1 << (k - 1) if 1 <= k <= 4 else None), name or button
    return None, name


def pick(d, *keys) -> dict:
    """{k: d[k]} for the named keys (None when absent) -- the detail lines' compact view of a published block."""
    d = d if isinstance(d, dict) else {}
    return {k: d.get(k) for k in keys}


# ----------------------------------------------------------------------------- frame windows
def elapsed(st0, st1) -> float:
    """Seconds between two published states on the GAME's clock when the document carries one (the stand-in's virtual
    ``rt``), else between their reads (``State.read_at`` -- the live engine runs on the wall clock). For "after >= N s"
    claims a stand-in running faster than real time would otherwise fail by construction."""
    a, b = raw(st0).get("rt"), raw(st1).get("rt")
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return float(b) - float(a)
    return float(getattr(st1, "read_at", 0.0) or 0.0) - float(getattr(st0, "read_at", 0.0) or 0.0)


def frame_of(x) -> int:
    try:
        return int(raw(x).get("frame", -1))
    except (TypeError, ValueError):
        return -1


def first_frame(samples, pred) -> int | None:
    """The doc frame (Time.frameCount) of the first sample satisfying ``pred``, or None."""
    for x in samples:
        try:
            if pred(x):
                return frame_of(x)
        except (TypeError, KeyError, AttributeError, IndexError, ValueError):
            continue
    return None


def watch_from(g, st0, until, timeout: float) -> tuple:
    """:func:`watch` with the state a verb returned prepended (so an edge that already landed by the ack is seen at the
    ack's frame). (samples, the state that ended it or None)."""
    if st0 is not None:
        try:
            if until(st0):
                return [st0], st0
        except (TypeError, KeyError, AttributeError, IndexError, ValueError):
            pass
    samples, hit = watch(g, until, timeout)
    return ([st0] if st0 is not None else []) + samples, hit


QUIT_GROUP = "Quit.Warning"            # QuitUI.WarningMenuGroupButton: QuitUI.Show makes it the active button group


def quit_prompt_up(st) -> bool:
    """The game's own QUIT prompt is showing. QuitUI.Show does NOT change UIManager.State (`ui_state` stays BattleHUD /
    BattleResult); it makes "Quit.Warning" the ACTIVE BUTTON GROUP -- the published cursor group, the live tell. Also
    read: a `Quit` ui_state, and -- over the result screen -- ``battle.result_ui.paused`` with the state not a plain
    Pause (what the stand-in publishes). CAUTION: Never press Confirm while this is True: its Yes quits the game."""
    if cursor_group(st) == QUIT_GROUP or st.ui_state == "Quit":
        return True
    ru = battle(st).get("result_ui")
    return isinstance(ru, dict) and ru.get("paused") is True and st.ui_state != "Pause"


def exception_lines(lines) -> list:
    """Exception lines in Memoria.log (an unhandled throw into the HUD -- e.g. a Confirm into GetCommandFromCommandIndex
    on a stale command group -- or a hook's swallowed FAULT): the "nothing threw" checks read these, after a mark."""
    return [ln for ln in lines if "Exception" in ln or "GetCommandFromCommandIndex" in ln or " FAULTED" in ln]
