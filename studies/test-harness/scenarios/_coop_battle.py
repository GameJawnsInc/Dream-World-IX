"""Shared helpers for the B4/B5 battle co-op SOLO BENCHES (studies/battle-coop/B4-B5-DESIGN.md section 8.2).

NOT A SCENARIO (no ``run(g)``): the five bench scenarios beside it import it --
    coop_battle_host_gates.py   stage 1  (s100)  host command-phase gates
    coop_battle_containment.py  stage 2  (s101)  the guest containment backstop (R9 + G2)
    coop_stock_menu.py          stage 3  (s102)  the stock menu first look + capture (the GO/NO-GO)
    coop_battle_end_host.py     stage 4  (s103)  the host end block
    coop_battle_end_guest.py    stages 5-6 (s104, s105)  the guest victory presentation + exit with the host

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
    ``netsync.battle.host.end_trail``; 5 ``netsync.battle.end.r8_hits``; 6 ``netsync.battle.end.end_leave``.
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


def ns_verb(g, sub: str, *args, timeout: float = 20.0):
    """`netsync <sub> [args]` -- through the driver when it knows the sub-verb, else as a raw step. Raises the agent's
    refusal (a HarnessError/StepRefused) either way."""
    known = getattr(g, "NETSYNC_SUBVERBS", None)
    if known is None or sub in known:
        return g.netsync(sub, *args, timeout=timeout)
    if sub not in _RAW_NOTED:
        _RAW_NOTED.add(sub)
        g.note(f"driver predates `netsync {sub}` (not in Session.NETSYNC_SUBVERBS) -- sent as a raw step; the "
               f"agent's own gates still apply")
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


def release(g, ledger: Ledger | None = None, cid: str | None = None, *, expect_lines=(), at: int | None = None) -> None:
    """`reset`: every lever, the forced role, parked frames, a harness diorama. Optionally judged as ``cid``: the role
    is released, no diorama is left booted, and each ``expect_lines`` needle logged after ``at``."""
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
    ledger.check(cid, ns.get("forced") is False and not dio(st).get("booted") and not missing,
                 f"forced={ns.get('forced')!r} booted={dio(st).get('booted')!r} missing lines={missing}; "
                 f"{grep(lines, 'released with the harness', 'override released')}")


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
