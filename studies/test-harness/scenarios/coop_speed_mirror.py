"""s163 -- THE HOST'S SPEED ON A FOLLOWING GUEST (studies/field-coop/SPEED-MIRROR.md rev 3, memoria-patches s163), the SOLO bench.
[ff9mapkit netsync s163]

THE DEFECT (GUEST-TRAVERSAL-TWO-PC.md Finding 10, and the rate half of Finding 4). A host on the F1 booster plays a scene or an ATE
at 3x while its following guest's copy plays the same script at 1x: "Dagger Tries" (351 -> 450) was cut at line 162 of 175 when the
host's scripted Field() beat the guest's last lines and the tail hold let go on its 8 s progress clock.

THE FIX (s163). The host rides its booster SETTING and its FieldTPS in state section 10; a following guest's copy runs the host's
scene at its OWN SpeedFactor through a LATCH (NetSyncSpeed): START needs my control off, the host's setting > 1 from a fresh lane and
my copy playing the host's scene ((a) the host here with its control off, (b) the ATE episode here, (c) a relayed talk here); END on
my control back for StepInMs (500 ms), a field change or landing, leaving the field scene, a climb, a movie, the host's setting 1 from
a fresh frame, eligibility or the lever -- never on the host's control, position or link. The factor is APPLIED only while my control
is off (free roam stays at my own speed), through the FastForwardFactor getter and the SetFastForward mode seam; the raw flag stays
the player's own.

THE BENCH. One instance root, the selftest role, real field 352 at scenario 2600 (Dali/Inn, the morning: control on, the ATE gate
cleared by the load). The step-out's bench `eligible` holds on the selftest role, `netsync speed host 5` is the host's section 10
through the real codec (src "bench"; 5, ABOVE the desktop's own SpeedFactor G -- 3 by default -- so the ON line's factor tells my G
from the host's setting: FactorRule's law, the factor is MINE, never the host's -- at host 3 = G a host-rate engine read the same),
`netsync hostscene 1` is the host's control-off scene on my field (term (a)), and the harness's `control 0|1`
(EventEngine.SetUserControl: exactly the GetUserControl the mirror reads, and `player.control` publishes) is my control. A
diorama (`dioboot`, the cheap battle scene the battle benches boot) is the battle, the walk out of the kit's FARSHORE landing (6603,
coop_world_wait.walk_out) the world map.

  K0       provenance; a fresh process; newgame; warp 352 (entrance 0, scenario 2600) with control; noencounter; `netsync selftest 1`.
  K1       "speed mirror selftest: OK (N rows, M mutants caught, step-in 500 ms)" within 20 s (s163: 114 / 66 -- N and M are never
           judged against literals; the step-in is, the latch's debounce); `netsync.speed.selftest` "ok".
  K2       `netsync.speed` at rest: lever null, mirror / applied false, src "none", host_setting 1, raw false, own_factor 1, factor_now 1,
           the top-level `ff` 1, faults 0, why_not "I have control" (the selftest role is eligible: my control is the first refusal).
  S-HOST   `speed host 5`: its 'bench host -- section 10 = setting 5 x T TPS through the real codec' line once; host_setting 5, host_tps
           T > 0, src "bench", host_seen true, host_stale false; then `hostscene 1` with MY control on for 1.5 s: never mirror,
           factor_now / ff 1, why_not "I have control" (calibrating: the lever's words, its term comes first).
  S-ON     `control 0` (hostscene 1, host 5): within 2 s ONE 'speed mirror: ON on field 352 -- factor F (the host's booster 5 x T TPS
           covers my G x M; my own factor 1) -- the host plays its scene here (its control is off)' with F == G > 1, M == T, F the
           ini's [Cheats] SpeedFactor (3 when unset) -- never the host's 5 (a host-rate engine's factor 5 reds 'F = my G' and 'F = the
           ini's G'); from the first mirror sample on: applied true, factor_now F, ff F, raw false (the player's own flag untouched),
           own_factor 1, mode_wanted true, fast_mode true one Update later; edges_on +1.
  S-LATCH  `hostscene 0` with my control still off, 1.5 s: mirror, applied, factor_now F and ff F on every sample, no OFF line,
           edges_off +0 -- THE LATCH (never an end on the host's control: s158's law).
  S-BACK   `control 1`: applied false and factor_now / ff 1 within 0.25 s of control back and on every later sample (free roam at my
           own speed: rev 3), the mirror still standing through the debounce and ending 0.4-1.5 s after control (StepInMs 500,
           measured from the last control-off sample), end_why.control +1, last_end "control", one 'speed mirror: OFF on field 352 after
           N ms -- factor back to 1 (my own) -- my control is back (500 ms)'.
  S-BATTLE the mirror raised again (hostscene 1, control 0), then `dioboot 67 0` (BattleMapDebug): at least 3 diorama samples, each
           ff 1, factor_now 1, mirror false; no sampled frame off the field scene with the mirror or its factor applied; end_why.scene
           +1, last_end "scene", one OFF line on 352 '-- I left the field scene (...)'. `dioleave` back to 352. THE IN-DIORAMA READ
           ONLY: cb.boot blocks until BattleMapDebug is up, so the SwirlScene frames before it are never sampled -- an end that came
           late (the latch standing through the swirl, ended a frame before BattleMapDebug, still counted as `scene`) is green here;
           the getter's own scene test reads ff 1 in the swirl whatever the latch does, and NetSyncSpeed.SelfTest's EndRule rows
           carry the scene term.
  S-OFF    the mirror raised again, then `speed off`: it ends within 0.5 s (end_why.lever +1, last_end "lever", the OFF line '-- the
           speed lever is off', the harness's CALIBRATION line), factor_now / ff 1 and why_not "the speed lever is off" on every
           control-off sample after the end; `speed act` raises it again within 2 s (edges_on +1) -- my control still off.
  S-F1     `speed host 1` (the host's booster off), hostscene 1, control 0: never mirror, factor 1, why_not "the host's booster is
           off"; `speedmode 1` (the REAL F1 path): raw true, own_factor G, factor_now G, ff G, fast_mode true, still never mirror -- the
           guest's own F1 (the getter's max over stock); `speedmode 0`: raw false, factor 1 again.
  S-STALE  `speed clear` (the bench host forgotten: src "none"), `bench 1` + `lock 1` (the selftest bench lane: a fresh section-7
           frame every tick while the lock is on, no section 10), control 0: host_stale false, why_not "the host's booster is off";
           `stale 1` (a NULL state: no news) -> host_stale true, the cache unchanged (absent: setting 1, src "none"), why_not "the
           host's lane is stale" (StartRule's stale term before its host term: rev 3's CacheRule; rev 1 read a null state as setting
           1, not stale); `stale 0` -> stale false. The cache here IS the absent state already, so a null state that FORGOT it reads
           the same values: this row reds rev 1 through host_stale and why_not, never a forgetting CacheRule that still marks stale
           (the keep-on-null law is NetSyncSpeed.SelfTest's row cache.null_state_keeps_the_host).
  S-WORLD  6603's walk out onto the world map (WorldHUD), `speed host 5`, hostscene 1, control 0 for 2 s: every sample mirror false,
           ff 1, factor_now 1, why_not "not on a live field", edges_on +0, my control witnessed off -- every other START term holds, so
           the field term alone refuses (a getter or a StartRule without it would mirror here).
  K-R      `speedmode 1` then `reset`: re-read with the role, lever null, src "none" (the bench host forgotten), host_setting 1, raw
           false (the harness's booster released); the release line when a lever or a bench host was held into it. Of these only
           'release line iff held' and 'lever null' test HarnessRelease itself: the release (HarnessSelfTest(false)) drops the forced
           role BEFORE its reconfigure, whose NetSyncSpeed.Reset forgets a bench host off the role anyway: 'src none' holds either way.

THE STALE-LANE END (rev 3's headline: a null state never ENDS a standing latch) is NOT REACHABLE on the selftest role: the bench host
(`speed host <n>`, src "bench") owns the cache and NoteHostFrame returns early while it stands (never stale), and the bench lane's own
frames carry no section 10, so a stale cache there always holds setting 1 -- no latch can stand on it. S-STALE proves the cache step
and the START term; EndRule takes no stale input at all, and NetSyncSpeed.SelfTest's CacheRule / EndRule rows carry the end. Nor
reachable solo: the START terms (b) the ATE episode and (c) the relayed talk (S-ON starts by (a)), a climb or a movie end, the host's
section 10 on a real lane (the duo, coop_speed_mirror_duo.py, carries those), a SpeedFactor / FieldTPS mismatch between two machines
(the bench host is built with MY FieldTPS; NetSyncSpeed.SelfTest's FactorRule rows carry it).

THE CALIBRATION (COOP_CALIBRATE=1 or off): `speed off` (s162's rule, never mirror) is pulled right after K2 and HELD to the end
(S-STALE's `speed clear` resets the lever to act, so the bench re-takes `speed off` right after it). PREDICTED_OFF = S-ON, S-LATCH,
S-BACK, S-BATTLE, S-OFF red (each needs a standing mirror), each with OFF_MARKER: my control off with the bench host above 1, why_not
"the speed lever is off" on every such sample, never a mirror sample, no ON line. S-HOST, S-F1, S-STALE and S-WORLD stay green: their
why_not reads the lever's words (its term precedes theirs), the rest of each row is the cache, the getter or the F1 path. Any other
COOP_CALIBRATE word is REFUSED (the s162 lesson: never mapped to `speed off`) AT LOAD, as the duo does: tools/play.py imports the
scenario before its Session launches FF9, so a refused word never costs a boot.

    py tools/play.py studies/test-harness/scenarios/coop_speed_mirror.py --instance C:\\gd\\ff9-inst\\host
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_speed_mirror.py --instance C:\\gd\\ff9-inst\\host
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file

HarnessError = cb.HarnessError

KEY = "netsync.speed"
PROBE = KEY + ".edges_on"                # key PRESENCE is the capability (protocol 5, additive)

FIELD, ENTRANCE, SCENARIO = 352, 0, 2600 # Dali/Inn, the morning (the ATE relay bench's arrival: control on, the ATE gate cleared)
HOST = 5                                 # the bench host's booster setting: ABOVE the desktop's G (3, Finding 4) -- the factor is mine
DIO_SCENE, DIO_PATTERN = cb.SCENE, cb.PATTERN   # 67: BSC_EF_R007, one Goblin -- the battle benches' diorama
FIELD_SCENE = "FieldMap"                 # SceneDirector.FieldMapSceneName: the getter's / StartRule's field scene
DIO_SCENE_NAME = "BattleMapDebug"        # a booted diorama's scene
G_DEFAULT = 3                            # Memoria's [Cheats] SpeedFactor default (SettingsState.FastForwardGameSpeed)
STEP_IN_MS = 500                         # NetSyncStepOut.StepInMs: the latch's debounce (EndRule's control term)

SELFTEST_S = 20.0
ARRIVE_S = 25.0
REST_S = 1.5                             # S-HOST's my-control-on window
ON_S = 2.0                               # the mirror must stand this soon after my control goes off (a Tick a frame)
HOLD_ON_S = 1.0                          # samples after the start (FAST MODE follows an edge one Update later)
LATCH_S = 1.5                            # S-LATCH's hostscene-0 window (three times the debounce: an end on the host would show)
BACK_WATCH_S = 2.2                       # after control back: past IN_BY_S
APPLY_BACK_S = 0.25                      # the factor withheld this soon after control back (the Tick may run before the step's frame)
DEBOUNCE_MIN_S = 0.4                     # the latch ends no sooner than this after control (StepInMs 500, less a publish)
IN_BY_S = 1.5                            # ...and no later than this (StepInMs 500 + the publish cadence)
LAND_GAP_MAX_S = 0.3                     # a publish stall across the flip longer than this leaves the debounce unmeasurable (red)
DIO_HOLD_S = 1.5
DIO_MIN = 3                              # S-BATTLE needs this many diorama samples (else vacuous)
LEAVE_S = 45.0
OFF_END_S = 0.5                          # S-OFF: the lever ends a standing mirror at the next Tick
OFF_S = 1.0
F1_PRE_S, F1_HOLD_S, F1_POST_S = 0.8, 1.2, 0.6
STALE_S = 0.8
WORLD_HOLD_S = 2.0
WORLD_MIN = 5

PROOF_RX = re.compile(r"speed mirror selftest: OK \((\d+) rows, (\d+) mutants caught, step-in (\d+) ms\)")
ON_RX = re.compile(r"speed mirror: ON on field (-?\d+) -- factor (-?\d+) \(the host's booster (-?\d+) x (-?\d+) TPS covers my (-?\d+) x "
                   r"(-?\d+); my own factor (-?\d+)\) -- (.+?)\s*$")
OFF_RX = re.compile(r"speed mirror: OFF on field (-?\d+) after (-?\d+) ms -- factor back to (-?\d+) \(my own\) -- (.+?)\s*$")
BENCH_HOST_RX = re.compile(r"harness: speed mirror's bench host -- section 10 = setting (\d+) x (\d+) TPS through the real codec")
# NetSyncSpeed's words (StartRule's why_not, Tick's START reasons, EndWords, the harness lines)
WHY_LEVER = "the speed lever is off"
WHY_FIELD = "not on a live field"
WHY_CONTROL = "I have control"
WHY_STALE = "the host's lane is stale"
WHY_HOST = "the host's booster is off"
START_WHY_HOST = "the host plays its scene here (its control is off)"
END_CONTROL = f"my control is back ({STEP_IN_MS} ms)"
END_LEVER = "the speed lever is off"
END_SCENE = "I left the field scene ("
LOG_HARNESS_OFF = "[NetSync] harness: speed mirror OFF -- CALIBRATION: s162's rule, never mirror (released with the harness)"
LOG_RELEASE = "[NetSync] harness: speed mirror lever released (act; the bench host forgotten)"

CLAIMS = {
    "K0": "the forced selftest role on 352 (newgame, warp 352 at scenario 2600 with control, noencounter, `netsync selftest 1`); a "
          "fresh process",
    "K1": "the proof line 'speed mirror selftest: OK (N rows, M mutants caught, step-in 500 ms)' (s163: 114 rows, 66 mutants) within "
          "20 s, and `netsync.speed.selftest` 'ok'",
    "K2": "`netsync.speed` at rest: lever null, no mirror, src 'none', host_setting 1, raw false, own_factor / factor_now / ff 1, faults "
          "0, why_not 'I have control'",
    "S-HOST": f"`speed host {HOST}` reads back through the real codec (its line, host_setting {HOST}, host_tps > 0, src 'bench'); "
              "hostscene 1 with MY control on never mirrors (factor 1, why_not 'I have control' -- the lever's words when calibrating)",
    "S-ON": f"my control off under hostscene 1 + host {HOST}: one ON line on 352 (factor F = my own SpeedFactor G > 1, never the "
            f"host's {HOST}; the host's {HOST} x T covering my G x T, my own factor 1, 'the host plays its scene here'); applied, "
            "factor_now F, ff F, raw false, mode_wanted, FAST MODE; edges_on +1",
    "S-LATCH": "hostscene 0 with my control still off keeps the mirror (applied, factor F) for 1.5 s: no OFF line, edges_off +0",
    "S-BACK": "my control back: the factor withheld at once (applied false, factor / ff 1 within 0.25 s and after), the latch ending "
              "0.4-1.5 s later by `control` (end_why.control +1, the OFF line 'my control is back (500 ms)')",
    "S-BATTLE": "a standing mirror, then a diorama: every in-diorama sample ff 1, factor_now 1, no mirror (the swirl is not sampled); "
                "end_why.scene +1, the OFF line 'I left the field scene (...)'",
    "S-OFF": "a standing mirror, then `speed off`: it ends within 0.5 s by `lever` (its OFF line, the CALIBRATION line), factor 1 and "
             "why_not 'the speed lever is off' with my control still off; `speed act` raises it again (edges_on +1)",
    "S-F1": "host 1 with my control off never mirrors (factor 1, why_not 'the host's booster is off'); my own `speedmode 1` reads raw "
            "true, own_factor / factor_now / ff G, FAST MODE, still no mirror; `speedmode 0` back to 1",
    "S-STALE": "the bench lane with no bench host: a fresh frame reads host_stale false, why_not 'the host's booster is off'; `stale 1` "
               "reads host_stale true with the cache unchanged (absent: setting 1, src 'none'), why_not 'the host's lane is stale'; "
               "`stale 0` fresh again",
    "S-WORLD": f"on the world map with host {HOST}, hostscene 1 and my control off: never mirror, ff / factor_now 1, why_not 'not on a "
               "live "
               "field' on every sample, edges_on +0",
    "K-R": "`speedmode 1` then `reset`: re-read with the role, lever null, src 'none', host_setting 1, raw false; the release line when "
           "a lever or a bench host was held into it",
}
PREDICTED_OFF = ("S-ON", "S-LATCH", "S-BACK", "S-BATTLE", "S-OFF")
OFF_MARKER = ("my control off with the bench host above 1, why_not 'the speed lever is off' on every such sample, never a mirror "
              "sample, no ON line")
FINALS = ("K-R", "K-CAL-M", "K-CAL")


def calibration() -> str | None:
    v = os.environ.get("COOP_CALIBRATE", "").strip().lower()
    if v in ("", "0"):
        return None
    if v in ("1", "off", "true", "yes", "on"):
        return "off"
    # the s162 lesson: an unknown word is never mapped to `speed off` (the s162 DLL is a duo-side prediction, never a solo lever)
    raise SystemExit(f"coop_speed_mirror: COOP_CALIBRATE={v!r} is refused -- the solo bench takes 1 / off (`netsync speed off`, "
                     f"s162's rule) and nothing else; refused before the game boots.")


CAL_MODE = calibration()                 # at load: tools/play.py imports the scenario before its Session launches FF9


def catalog(cal: str | None) -> dict:
    cat = dict(CLAIMS)
    if cal is not None:
        cat["K-CAL-M"] = "the lever was taken and every predicted red carries its marker: " + OFF_MARKER
        cat["K-CAL"] = "the `speed off` calibration: exactly " + ", ".join(PREDICTED_OFF) + " red"
    return cat


# --------------------------------------------------------------------------------------------- reads (pure)
def sp(x) -> dict | None:
    b = cb.path(x, KEY)
    return b if isinstance(b, dict) else None


def sget(x, dotted: str, default=None):
    cur = sp(x)
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def ival(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def ffv(x) -> int | None:
    """The top-level `ff` (SettingsState.FastForwardFactor, the REAL getter); None = absent (an engine before s163)."""
    return ival(cb.raw(x).get("ff"))


def ctl(x) -> bool:
    return (cb.raw(x).get("player") or {}).get("control") is True


def settled(samples, on: bool) -> list:
    """The samples whose `player.control` is ``on``, minus each flip's own publish. THE ORDER SKEW (measured live on the first s163 solo
    run, at every harness flip, S-F1 and S-STALE red on it): the speed block is NetSyncSpeed's last Tick (why_not, mirror, applied, and
    factor_now / ff, which read NetSyncSpeedArmed.Applied), and HarnessAgent runs a `control` step and writes its ack (PublishState(true)
    inside DrainQueue) in the same Update, so no Tick runs between the two -- that publish shows the new control with the verdict made
    under the old one, whichever Update runs first; the next publish (2 frames on) follows a Tick and agrees. An engine-driven flip can
    lag too (085217 f1740 did, f1911 did not), when no Tick falls between the flip and the next publish. A window's first sample goes
    too: ``watch`` opens on the current publish, which IS the flip's own when the window opens on a `control` step. Two such publishes
    in a row stay red. Load-bearing for S-F1 and S-STALE only: S-HOST's window has no flip, and on S-WORLD (the field term) and under
    the calibration (the lever term) a term that StartRule checks before control already names the flip's own publish; they carry it
    so the five judges that can see a flip (S-HOST, S-F1, S-STALE, S-WORLD, the marker) read the same way. S-OFF does not: its
    control stays off and its window opens on the Block-2 lever ack."""
    return [s for i, s in enumerate(samples) if ctl(s) == on and i > 0 and ctl(samples[i - 1]) == on]


def field_of(x) -> int:
    return int((cb.raw(x).get("field") or {}).get("id", -1))


def scene_of(x):
    return cb.raw(x).get("scene")


def ui_of(x):
    return cb.raw(x).get("ui_state")


def counters(x) -> dict:
    """edges_on / edges_off and every end_why counter (None = absent)."""
    out = {"on": ival(sget(x, "edges_on")), "off": ival(sget(x, "edges_off"))}
    ew = sget(x, "end_why")
    for k, v in (ew.items() if isinstance(ew, dict) else ()):
        out[k] = ival(v)
    return out


def rose(b0: dict, b1: dict, key: str, by: int = 1) -> bool:
    """``key`` rose by exactly ``by`` from ``b0`` to ``b1`` -- an ABSENT counter is never a 0 that stayed."""
    a, b = b0.get(key), b1.get(key)
    return isinstance(a, int) and isinstance(b, int) and b - a == by


def mirror(x) -> bool:
    return sget(x, "mirror") is True


def applied(x) -> bool:
    return sget(x, "applied") is True


def at_one(x) -> bool:
    """The factor reads 1 on both reads: netsync.speed.factor_now and the top-level `ff`."""
    return ival(sget(x, "factor_now")) == 1 and ffv(x) == 1


def parse_on(lines) -> list:
    """Every ON line: {i, field, factor, s, t, g, m, own, why}."""
    out = []
    for i, ln in enumerate(lines):
        m = ON_RX.search(ln)
        if m:
            f, fac, s, t, g, mt, own = (int(m.group(k)) for k in range(1, 8))
            out.append({"i": i, "field": f, "factor": fac, "s": s, "t": t, "g": g, "m": mt, "own": own, "why": m.group(8)})
    return out


def parse_off(lines) -> list:
    """Every OFF line: {i, field, ms, own, why}."""
    out = []
    for i, ln in enumerate(lines):
        m = OFF_RX.search(ln)
        if m:
            out.append({"i": i, "field": int(m.group(1)), "ms": int(m.group(2)), "own": int(m.group(3)), "why": m.group(4)})
    return out


def g_oracle(ini_value) -> tuple:
    """(G, src): my own [Cheats] SpeedFactor as the mirror's factor must read -- the ini value clamped 1-255 (NetSyncSpeed's Clamp),
    or Memoria's default 3 when the key is unset or unreadable."""
    try:
        v = int(str(ini_value).strip())
    except (TypeError, ValueError):
        return G_DEFAULT, "default"
    return (1 if v < 1 else 255 if v > 255 else v), "ini"


def why_want(cal: str | None, plain: str) -> str:
    """The why_not a lever-aware row expects: the lever's words while calibrating (its term precedes every other but eligibility)."""
    return WHY_LEVER if cal else plain


def _fmt(parts) -> str:
    return ", ".join(f"{k} {'ok' if v else 'NO'}" for k, v in parts)


def judge_proof(lines, verdict) -> tuple:
    """K1 (PURE): the proof line OK with step-in 500 (N and M not judged against literals), and the published verdict 'ok'."""
    m = next((PROOF_RX.search(ln) for ln in lines if PROOF_RX.search(ln)), None)
    fail = [ln for ln in lines if "speed mirror selftest: FAIL (" in ln]
    ok = m is not None and int(m.group(3)) == STEP_IN_MS and verdict == "ok" and not fail
    return ok, (f"{cb.grep(lines, 'speed mirror selftest')}; speed.selftest {verdict!r}"
                + (f"; rows {m.group(1)}, mutants {m.group(2)}, step-in {m.group(3)}" if m else "; no OK line"))


def judge_rest(st) -> tuple:
    """K2 (PURE): the block at rest on the selftest role with my control on."""
    parts = [("present", sp(st) is not None), ("lever null", sget(st, "lever", 0) is None), ("no mirror", sget(st, "mirror") is False),
             ("not applied", sget(st, "applied") is False), ("src none", sget(st, "src") == "none"),
             ("host_setting 1", ival(sget(st, "host_setting")) == 1), ("raw false", sget(st, "raw") is False),
             ("own_factor 1", ival(sget(st, "own_factor")) == 1), ("factor 1", at_one(st)), ("faults 0", ival(sget(st, "faults")) == 0),
             ("why_not " + WHY_CONTROL, sget(st, "why_not") == WHY_CONTROL)]
    return all(v for _, v in parts), _fmt(parts) + f"; why_not {sget(st, 'why_not')!r}, ff {ffv(st)!r}"


def judge_bench_host(st, lines, rest, cal) -> tuple:
    """S-HOST (PURE): ``st`` read after `speed host HOST`, ``lines`` its log, ``rest`` the hostscene-1 samples with MY control on."""
    hits = [BENCH_HOST_RX.search(ln) for ln in lines]
    hits = [m for m in hits if m]
    t = int(hits[0].group(2)) if hits else None
    want = why_want(cal, WHY_CONTROL)
    on = settled(rest, True)
    parts = [("one bench-host line", len(hits) == 1), (f"its setting {HOST}", bool(hits) and int(hits[0].group(1)) == HOST),
             (f"host_setting {HOST}", ival(sget(st, "host_setting")) == HOST),
             ("host_tps = the line's", t is not None and t > 0 and ival(sget(st, "host_tps")) == t),
             ("src bench", sget(st, "src") == "bench"), ("host_seen", sget(st, "host_seen") is True),
             ("not stale", sget(st, "host_stale") is False),
             ("control-on samples", len(on) >= 3), ("never mirror", not any(mirror(s) for s in rest)),
             ("factor 1", bool(rest) and all(at_one(s) for s in rest)),
             ("why_not " + want, bool(on) and all(sget(s, "why_not") == want for s in on))]
    return all(v for _, v in parts), (_fmt(parts) + f"; host_tps {sget(st, 'host_tps')!r}; why_not "
                                      f"{sorted({str(sget(s, 'why_not')) for s in rest})}; {cb.grep(lines, 'bench host')}")


def first_mirror(samples) -> int | None:
    return next((i for i, s in enumerate(samples) if mirror(s)), None)


def judge_on(samples, lines, b0, g_want: int, field: int) -> tuple:
    """S-ON (PURE): ``samples`` stamped (``_t``) from my control going off, ``lines`` the log since then, ``b0`` the counters before.
    -> (ok, detail, F): F the ON line's factor (None without one). With the bench host at HOST (5) above G, 'F = my G' and 'F = the
    ini's G' red an engine that applies the HOST's setting (SelfTest's factor_host_rate mutant: factor 5, the line's G 3)."""
    ons = [o for o in parse_on(lines) if o["field"] == field]
    o = ons[0] if ons else {}
    fac = o.get("factor")
    k = first_mirror(samples)
    t_off = next((s["_t"] for s in samples if not ctl(s)), None)
    live = samples[k:] if k is not None else []
    live_off = [s for s in live if not ctl(s)]
    b1 = counters(samples[-1]) if samples else {}
    parts = [("one ON line", len(ons) == 1 and len(parse_on(lines)) == 1), ("F > 1", isinstance(fac, int) and fac > 1),
             ("F = my G", fac is not None and fac == o.get("g")), ("F = the ini's G", fac == g_want),
             (f"the host's {HOST}", o.get("s") == HOST),
             ("its TPS = mine", o.get("t") is not None and o.get("t") == o.get("m") and o["t"] > 0),
             ("my own factor 1", o.get("own") == 1), ("the host's scene", o.get("why") == START_WHY_HOST),
             ("started within ON_S", k is not None and t_off is not None and samples[k]["_t"] - t_off <= ON_S),
             ("applied", bool(live_off) and all(applied(s) for s in live_off)),
             ("factor_now F", bool(live_off) and all(ival(sget(s, "factor_now")) == fac for s in live_off)),
             ("ff F", bool(live_off) and all(ffv(s) == fac for s in live_off)),
             ("raw false", bool(live) and all(sget(s, "raw") is False for s in live)),
             ("own_factor 1", bool(live) and all(ival(sget(s, "own_factor")) == 1 for s in live)),
             ("mode_wanted", bool(live_off) and all(sget(s, "mode_wanted") is True for s in live_off)),
             ("FAST MODE", any(sget(s, "fast_mode") is True for s in live_off[1:])),
             ("edges_on +1", rose(b0, b1, "on"))]
    return all(v for _, v in parts), (_fmt(parts) + f"; G wanted {g_want}; {len(live_off)} live control-off samples of "
                                      f"{len(samples)}; why_not {sorted({str(sget(s, 'why_not')) for s in samples})}; "
                                      f"{cb.grep(lines, 'speed mirror')}"), fac


def judge_latch(samples, lines, b0, fac) -> tuple:
    """S-LATCH (PURE): the hostscene-0 window with my control still off."""
    off = [s for s in samples if not ctl(s)]
    b1 = counters(samples[-1]) if samples else {}
    parts = [("samples", len(off) >= 3 and len(off) == len(samples)), ("factor known", isinstance(fac, int) and fac > 1),
             ("mirror kept", bool(off) and all(mirror(s) for s in off)), ("applied", bool(off) and all(applied(s) for s in off)),
             ("factor F", bool(off) and all(ival(sget(s, "factor_now")) == fac and ffv(s) == fac for s in off)),
             ("no OFF line", not parse_off(lines)), ("edges_off +0", rose(b0, b1, "off", 0))]
    return all(v for _, v in parts), (_fmt(parts) + f"; {len(off)} control-off samples of {len(samples)}; "
                                      f"{cb.grep(lines, 'speed mirror')}")


def judge_back(samples, lines, b0, field: int) -> tuple:
    """S-BACK (PURE): ``samples`` stamped from the moment `control 1` was SENT (a pre-send sample at 0, control off), ``lines`` the
    log since. The debounce's floor is measured from the last control-off sample (the step-out's s159 lesson: a publish stall across the
    flip); a stall over LAND_GAP_MAX_S leaves it unmeasurable (red, never a silent green)."""
    k = next((i for i, s in enumerate(samples) if ctl(s)), None)
    if k is None:
        return False, f"control never came back over {len(samples)} samples"
    t_land = samples[k]["_t"]
    offs = [s["_t"] for s in samples[:k] if not ctl(s)]
    gap = (t_land - offs[-1]) if offs else t_land
    after = samples[k:]
    w = next((s for s in after if not applied(s)), None)
    t_w = (w["_t"] - t_land) if w is not None else None
    late = [s for s in after if s["_t"] - t_land >= APPLY_BACK_S]
    e = next((s for s in after if not mirror(s)), None)
    dt = (e["_t"] - t_land) if e is not None else None
    b1 = counters(samples[-1])
    offl = [o for o in parse_off(lines) if o["field"] == field]
    parts = [("withheld within 0.25 s", t_w is not None and t_w <= APPLY_BACK_S),
             ("never re-applied", bool(late) and not any(applied(s) for s in late)),
             ("factor 1 once withheld", bool(late) and all(at_one(s) for s in late)),
             ("still standing at the flip", mirror(samples[k])),
             ("debounce", dt is not None and gap <= LAND_GAP_MAX_S and DEBOUNCE_MIN_S <= dt + gap and dt <= IN_BY_S),
             ("end_why.control +1", rose(b0, b1, "control")), ("last_end control", sget(samples[-1], "last_end") == "control"),
             ("edges_off +1", rose(b0, b1, "off")),
             ("one OFF line by control", len(offl) == 1 and offl[0]["why"] == END_CONTROL and offl[0]["own"] == 1)]
    return all(v for _, v in parts), (_fmt(parts) + f"; withheld {t_w if t_w is None else round(t_w, 3)} s, ended "
                                      f"{dt if dt is None else round(dt, 3)} s after control (gap {gap:.3f} s); "
                                      f"{cb.grep(lines, 'speed mirror')}")


def judge_battle(raised: bool, samples, b0, lines, field: int) -> tuple:
    """S-BATTLE (PURE): ``raised`` (the mirror stood before the boot), ``samples`` from the boot on, ``b0`` the counters before it.
    The run's samples begin once the diorama is up (cb.boot blocks until BattleMapDebug): 'no mirror off the field scene' reads the
    in-diorama frames, never the swirl's (see the module note)."""
    dio = [s for s in samples if scene_of(s) == DIO_SCENE_NAME]
    off_scene = [s for s in samples if scene_of(s) != FIELD_SCENE]
    b1 = counters(samples[-1]) if samples else {}
    offl = [o for o in parse_off(lines) if o["field"] == field]
    parts = [("raised before the boot", raised), ("diorama samples", len(dio) >= DIO_MIN),
             ("factor 1 in battle", bool(dio) and all(at_one(s) for s in dio)),
             ("no mirror off the field scene", not any(mirror(s) or applied(s) for s in off_scene)),
             ("end_why.scene +1", rose(b0, b1, "scene")), ("last_end scene", sget(samples[-1] if samples else {}, "last_end") == "scene"),
             ("one OFF line by the scene", len(offl) == 1 and offl[0]["why"].startswith(END_SCENE))]
    return all(v for _, v in parts), (_fmt(parts) + f"; {len(dio)} diorama samples of {len(samples)}; ff "
                                      f"{sorted({str(ffv(s)) for s in dio})}; {cb.grep(lines, 'speed mirror', 'diorama boot')}")


def judge_off(raised: bool, after, b0, lines, again, b_mid, field: int) -> tuple:
    """S-OFF (PURE): ``after`` stamped from the `speed off` step, ``again`` the samples after `speed act` (``b_mid`` the counters before
    it)."""
    # Safe because `netsync speed off` Blocks 2 frames: the window opens after the next Tick. The ending Tick clears why_not before
    # Stop, so a publish between it and the next Tick reads mirror false with why_not None -- a non-blocking end step would need
    # `e` taken from the first non-mirror sample whose why_not is set.
    e = next((s for s in after if not mirror(s)), None)
    ended = [s for s in after if e is not None and s["_t"] >= e["_t"]]
    ended_off = [s for s in ended if not ctl(s)]
    b1 = counters(after[-1]) if after else {}
    b2 = counters(again[-1]) if again else {}
    offl = [o for o in parse_off(lines) if o["field"] == field]
    parts = [("raised", raised), ("ended within 0.5 s", e is not None and e["_t"] <= OFF_END_S),
             ("factor 1, control still off", len(ended_off) >= 2 and all(at_one(s) for s in ended_off)),
             ("why_not the lever", bool(ended_off) and all(sget(s, "why_not") == WHY_LEVER for s in ended_off)),
             ("end_why.lever +1", rose(b0, b1, "lever")), ("last_end lever", sget(after[-1] if after else {}, "last_end") == "lever"),
             ("one OFF line by the lever", len(offl) == 1 and offl[0]["why"] == END_LEVER),
             ("the CALIBRATION line", cb.count(lines, LOG_HARNESS_OFF) == 1),
             ("act raises it again", any(mirror(s) for s in again) and rose(b_mid, b2, "on"))]
    return all(v for _, v in parts), (_fmt(parts) + f"; ended at {e['_t'] if e else None!r} s; {cb.grep(lines, 'speed mirror')}")


def judge_f1(pre, f1, post, cal, g_want: int) -> tuple:
    """S-F1 (PURE): host 1 with my control off (``pre``), then my own `speedmode 1` (``f1``), then `speedmode 0` (``post``)."""
    want = why_want(cal, WHY_HOST)
    pre_off = settled(pre, False)
    k = next((i for i, s in enumerate(f1) if sget(s, "raw") is True), None)
    on = f1[k:] if k is not None else []
    tail = post[-3:]
    parts = [("pre: control off", len(pre_off) >= 3), ("pre: host 1", all(ival(sget(s, "host_setting")) == 1 for s in pre_off)),
             ("pre: factor 1", bool(pre_off) and all(at_one(s) for s in pre_off)),
             ("pre: why_not " + want, bool(pre_off) and all(sget(s, "why_not") == want for s in pre_off)),
             ("F1: raw true", len(on) >= 3), ("F1: own_factor G", bool(on) and all(ival(sget(s, "own_factor")) == g_want for s in on)),
             ("F1: factor_now G", bool(on) and all(ival(sget(s, "factor_now")) == g_want for s in on)),
             ("F1: ff G", bool(on) and all(ffv(s) == g_want for s in on)),
             ("F1: FAST MODE", any(sget(s, "fast_mode") is True for s in on)),
             ("F1: why_not " + want, bool(on) and all(sget(s, "why_not") == want for s in on)),
             ("never mirror", not any(mirror(s) for s in pre + f1 + post)),
             ("after: raw false, factor 1", bool(tail) and all(sget(s, "raw") is False and at_one(s) for s in tail))]
    return all(v for _, v in parts), (_fmt(parts) + f"; G wanted {g_want}; F1 own {sorted({str(sget(s, 'own_factor')) for s in on})} ff "
                                      f"{sorted({str(ffv(s)) for s in on})}; why_not {sorted({str(sget(s, 'why_not')) for s in pre + f1})}")


def judge_stale(fresh, stale, back, cal) -> tuple:
    """S-STALE (PURE): the bench lane, no bench host, my control off -- ``fresh`` (stale 0), ``stale`` (stale 1), ``back`` (stale 0);
    each window judged on its control-off samples only."""
    w_host, w_stale = why_want(cal, WHY_HOST), why_want(cal, WHY_STALE)
    fresh, stale, back = (settled(w, False) for w in (fresh, stale, back))   # THE ORDER SKEW: each flip's own publish dropped
    k = next((i for i, s in enumerate(stale) if sget(s, "host_stale") is True), None)
    st_on = stale[k:] if k is not None else []
    tail = back[-3:]
    cache = lambda s: ival(sget(s, "host_setting")) == 1 and sget(s, "src") == "none" and sget(s, "host_seen") is False   # noqa: E731
    parts = [("fresh: not stale", len(fresh) >= 3 and all(sget(s, "host_stale") is False for s in fresh)),
             ("fresh: no host (setting 1, src none)", bool(fresh) and all(cache(s) for s in fresh)),
             ("fresh: why_not " + w_host, bool(fresh) and all(sget(s, "why_not") == w_host for s in fresh)),
             ("stale 1: stale", len(st_on) >= 2 and all(sget(s, "host_stale") is True for s in st_on)),
             ("stale 1: the cache unchanged (absent)", bool(st_on) and all(cache(s) for s in st_on)),
             ("stale 1: why_not " + w_stale, bool(st_on) and all(sget(s, "why_not") == w_stale for s in st_on)),
             ("stale 0: fresh again", bool(tail) and all(sget(s, "host_stale") is False for s in tail)),
             ("never mirror", not any(mirror(s) for s in fresh + stale + back))]
    return all(v for _, v in parts), (_fmt(parts) + f"; why_not fresh {sorted({str(sget(s, 'why_not')) for s in fresh})} stale "
                                      f"{sorted({str(sget(s, 'why_not')) for s in stale})}")


def judge_world(samples, cal) -> tuple:
    """S-WORLD (PURE): the world-map window -- host HOST, hostscene 1, my control off: only the field term refuses."""
    want = why_want(cal, WHY_FIELD)
    world = [s for s in samples if ui_of(s) == "WorldHUD"]
    off = settled(world, False)
    b0, b1 = (counters(samples[0]), counters(samples[-1])) if samples else ({}, {})
    parts = [("WorldHUD samples", len(world) >= WORLD_MIN), ("my control off witnessed", len(off) >= 2),
             (f"the bench host {HOST}", bool(world) and all(ival(sget(s, "host_setting")) == HOST for s in world)),
             ("never mirror", not any(mirror(s) or applied(s) for s in samples)),
             ("factor 1", bool(world) and all(at_one(s) for s in world)),
             ("why_not " + want, bool(off) and all(sget(s, "why_not") == want for s in off)),
             ("edges_on +0", rose(b0, b1, "on", 0))]
    return all(v for _, v in parts), (_fmt(parts) + f"; {len(off)} control-off of {len(world)} WorldHUD samples ({len(samples)}); "
                                      f"why_not {sorted({str(sget(s, 'why_not')) for s in samples})}")


def off_marker(samples, lines) -> tuple:
    """The calibration's marker on a predicted red: the mirror's every other term held (my control off, the bench host above 1) and
    the lever refused it -- never a mirror, never an ON line."""
    armed = [s for s in settled(samples, False) if (ival(sget(s, "host_setting")) or 0) > 1]
    parts = [("control off with the host above 1", bool(armed)),
             ("why_not the lever", bool(armed) and all(sget(s, "why_not") == WHY_LEVER for s in armed)),
             ("never mirror", not any(mirror(s) for s in samples)), ("no ON line", not parse_on(lines))]
    return all(v for _, v in parts), _fmt(parts)


# --------------------------------------------------------------------------------------------- the run
class Ctx:
    def __init__(self, cal: str | None):
        self.cal = cal
        self.k0_ok = False
        self.lever_held = False
        self.bench_host = False          # a bench host stood at the last `speed` op (the release line names it)
        self.field = FIELD
        self.g_want = G_DEFAULT
        self.factor = None               # S-ON's factor (S-LATCH reads it)
        self.marks: dict = {}            # leg -> (samples, lines): the calibration marker reads them


def _ns(g, sub: str, *args) -> tuple:
    return cb.try_ns(g, sub, *args)


def _must(g, sub: str, *args) -> None:
    ok, why = _ns(g, sub, *args)
    if not ok:
        raise HarnessError(f"netsync {sub} {' '.join(str(a) for a in args)} refused: {why}")


def _speed(g, ctx: Ctx, op: str, n: int | None = None) -> None:
    """`netsync speed <op> [n]`, refused loud; tracks what the release must name (a lever, a bench host)."""
    _must(g, "speed", *((op,) if n is None else (op, n)))
    if op == "host":
        ctx.bench_host = True
    elif op == "clear":
        ctx.bench_host = False
    if op == "off":
        ctx.lever_held = True
    elif op in ("act", "clear"):
        ctx.lever_held = False


def _control(g, on: bool) -> None:
    try:
        g.control(on)
    except HarnessError as err:
        raise HarnessError(f"`control {int(on)}` refused: {str(err)[:200]}")


def watch(g, seconds: float, until=None, t0: float | None = None) -> tuple:
    """Every distinct publish for ``seconds`` (or until ``until(sample)``), each a raw dict stamped ``_t`` = seconds since ``t0``
    (default: now). -> (samples, the sample that ended it or None)."""
    t0 = time.time() if t0 is None else t0
    out, seen, hit = [], None, None
    deadline = time.time() + seconds
    while time.time() < deadline:
        st = g.state
        if st.frame != seen:
            seen = st.frame
            d = dict(cb.raw(st))
            d["_t"] = time.time() - t0
            out.append(d)
            try:
                if until is not None and until(d):
                    hit = d
                    break
            except (TypeError, KeyError, AttributeError, IndexError, ValueError):
                pass
        time.sleep(0.004)
    return out, hit


def _arrive(g, ctx: Ctx) -> tuple:
    """Warp to 352 (entrance 0, scenario 2600) and wait for control there, paging any line that opens on the way in."""
    try:
        g.warp(FIELD, entrance=ENTRANCE, scenario=SCENARIO)
    except HarnessError as err:
        return False, f"warp {FIELD} failed: {str(err)[:200]}"
    return _free_on(g, FIELD, ARRIVE_S)


def _free_on(g, fid: int, timeout: float) -> tuple:
    deadline = time.time() + timeout
    st = g.state
    while time.time() < deadline:
        st = g.state
        if st.field_id == fid and st.control and not st.dialog_open:
            return True, ""
        if st.dialog_open:
            g.press("confirm", 2)
        g.wait_frames(6)
    return False, f"no control on {fid}: field {st.field_id} control {st.control} dialog {st.dialog_open}"


def _raise(g, ctx: Ctx) -> tuple:
    """hostscene 1, then my control off: (raised, samples stamped from the control-off, the log mark before it, that stamp's t0)."""
    _must(g, "hostscene", 1)
    at = cb.mark(g)
    t0 = time.time()
    _control(g, False)
    samples, hit = watch(g, ON_S, until=mirror, t0=t0)
    return hit is not None, samples, at, t0


def _settle_mirror_off(g) -> None:
    """Between legs: my control on, hostscene 0, and the latch spent (it ends StepInMs after my control)."""
    for step in (lambda: _control(g, True), lambda: _ns(g, "hostscene", 0)):
        try:
            step()
        except HarnessError:
            pass
    cb.poll(g, lambda s: not mirror(s), IN_BY_S + 1.0, "the speed mirror to end")


def run(g, field: int | None = None):
    cal = CAL_MODE                                       # read at load: an unknown word never reached a booted game
    st0 = cb.poll(g, lambda s: s.netsync is not None, 15.0, "the netsync block (protocol 5)") or g.state
    ctx = Ctx(cal)
    led = cb.Ledger(g, catalog(cal), finals=FINALS, width=1400)
    if field is not None:
        g.note(f"--field {field} is ignored: the bench uses 352 (and the world map out of 6603)")
    if not cb.has(st0, PROBE):
        g.note("this engine publishes no `netsync.speed` (s162 or older): every leg is red by absence")
    try:
        ctx.k0_ok = _k0(g, ctx, led)
        if not ctx.k0_ok:
            led.close("not reached: K0 (the setup) refused")
            return
        _k1_k2(g, led)
        if cal is not None:
            ok, why = _ns(g, "speed", "off")
            st = cb.poll(g, lambda s: sget(s, "lever") == "off", 3.0, "the off lever read back")
            ctx.lever_held = ok and st is not None
            g.note(f"CALIBRATION: `speed off` {'taken' if ok else 'REFUSED: ' + why}, held to the end (after K2); predicted red "
                   f"{', '.join(PREDICTED_OFF)}")
        _guard(g, ctx, led, ("S-HOST",), lambda: _s_host(g, ctx, led))
        _guard(g, ctx, led, ("S-ON", "S-LATCH", "S-BACK"), lambda: _episode(g, ctx, led))
        _guard(g, ctx, led, ("S-BATTLE",), lambda: _s_battle(g, ctx, led))
        _guard(g, ctx, led, ("S-OFF",), lambda: _s_off(g, ctx, led))
        _guard(g, ctx, led, ("S-F1",), lambda: _s_f1(g, ctx, led))
        _guard(g, ctx, led, ("S-STALE",), lambda: _s_stale(g, ctx, led))
        _guard(g, ctx, led, ("S-WORLD",), lambda: _s_world(g, ctx, led))
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    finally:
        for step in (lambda: g.control(True), lambda: _ns(g, "hostscene", 0), lambda: _ns(g, "stale", 0), lambda: _ns(g, "lock", 0)):
            try:
                step()
            except (HarnessError, AttributeError):
                pass
        if ctx.k0_ok:
            _k_r(g, ctx, led)
        else:
            led.unreached(["K-R"], "K0 refused")
        g.note(f"Memoria.log archived: {cb.archive_log(g, 'speed-mirror-' + (cal or 'plain'))}")
        if cal is not None:
            led.close("not reached: the run ended before this check")
            marks_ok = ctx.lever_held and all(leg in ctx.marks and off_marker(*ctx.marks[leg])[0] for leg in PREDICTED_OFF)
            led.check("K-CAL-M", marks_ok, f"lever {'taken' if ctx.lever_held else 'NOT TAKEN'}; " + "; ".join(
                f"{leg}: {off_marker(*ctx.marks[leg])[1] if leg in ctx.marks else 'NO RUN'}" for leg in PREDICTED_OFF))
            led.judge_calibration("K-CAL", PREDICTED_OFF)
        led.close(final=True)


def _guard(g, ctx: Ctx, led: cb.Ledger, legs: tuple, fn) -> None:
    todo = [leg for leg in legs if leg in led.catalog and leg not in led.done]
    if not todo:
        return
    try:
        fn()
    except HarnessError as err:
        led.unreached(todo, f"the leg raised: {str(err)[:300]}")
    except Exception as err:                             # noqa: BLE001 - a BENCH bug: red and loud, the run goes on
        g.note(f"{'/'.join(todo)} FAULTED (a bench bug, not a verdict): {err!r}"[:400])
        led.unreached(todo, f"the leg FAULTED (a bench bug): {err!r}"[:300])
    finally:
        if ui_of(g.state) == "FieldHUD":
            _settle_mirror_off(g)
    led.unreached(todo, "the leg recorded nothing")


def _k0(g, ctx: Ctx, led: cb.Ledger) -> bool:
    cb.provenance(g)
    if getattr(g, "attach", False):
        led.check("K0", False, "refused: --attach (a reused process carries earlier counters and episodes)")
        return False
    try:
        g.newgame()
    except HarnessError as err:
        led.check("K0", False, f"newgame failed: {str(err)[:300]}")
        return False
    ok, why = _arrive(g, ctx)
    if not ok:
        led.check("K0", False, why)
        return False
    try:
        g.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        g.note(f"noencounter refused ({str(err)[:120]})")
    ok1, why1 = _ns(g, "selftest", 1)
    st = cb.poll(g, lambda s: bool((s.netsync or {}).get("forced")) and bool((s.netsync or {}).get("selftest")), 5.0,
                 "the forced selftest role") or g.state
    ns = st.netsync or {}
    ctx.g_want, src = g_oracle(cb.ini_value(g, "Cheats", "SpeedFactor"))
    g.note(f"my own [Cheats] SpeedFactor G = {ctx.g_want} ({src}); the bench host's {HOST} covers it only when G <= {HOST}, and "
           f"S-ON tells my factor from the host's only when G != {HOST}")
    good = ok1 and bool(ns.get("forced")) and bool(ns.get("selftest")) and st.field_id == FIELD
    led.check("K0", good, f"selftest={ns.get('selftest')!r} forced={ns.get('forced')!r} field={st.field_id}" + (f"; {why1}" if why1 else ""))
    return good


def _k1_k2(g, led: cb.Ledger) -> None:
    lines = cb.wait_log(g, 0, "speed mirror selftest:", timeout=SELFTEST_S)
    st = cb.poll(g, lambda s: sget(s, "selftest") is not None, SELFTEST_S, "netsync.speed.selftest") or g.state
    ok, why = judge_proof(lines, sget(st, "selftest"))
    led.check("K1", ok, why)
    st, _ = watch(g, 0.5)
    ok, why = judge_rest(st[-1] if st else g.state)
    led.check("K2", ok, why)


def _s_host(g, ctx: Ctx, led: cb.Ledger) -> None:
    at = cb.mark(g)
    _speed(g, ctx, "host", HOST)
    st = cb.poll(g, lambda s: ival(sget(s, "host_setting")) == HOST, 3.0, "the bench host read back") or g.state
    _must(g, "hostscene", 1)
    rest, _ = watch(g, REST_S)
    lines = cb.new(g, at)
    ok, why = judge_bench_host(cb.raw(st), lines, rest, ctx.cal)
    led.check("S-HOST", ok, why)


def _episode(g, ctx: Ctx, led: cb.Ledger) -> None:
    """S-ON -> S-LATCH -> S-BACK: one latch, raised by my control off under hostscene 1 (S-HOST left it up)."""
    b0 = counters(g.state)
    raised, samples, at, t0 = _raise(g, ctx)
    more, _ = watch(g, HOLD_ON_S, t0=t0)
    samples += more
    lines = cb.new(g, at)
    ctx.marks["S-ON"] = (samples, lines)
    ok, why, ctx.factor = judge_on(samples, lines, b0, ctx.g_want, ctx.field)
    led.check("S-ON", ok, why)
    # S-LATCH: the host's control back (hostscene 0), mine still off
    b1 = counters(g.state)
    at2 = cb.mark(g)
    _must(g, "hostscene", 0)
    latch, _ = watch(g, LATCH_S)
    lines2 = cb.new(g, at2)
    ctx.marks["S-LATCH"] = (samples + latch, lines + lines2)
    ok, why = judge_latch(latch, lines2, b1, ctx.factor)
    led.check("S-LATCH", ok, why)
    # S-BACK: my control back -- a pre-send sample (control off) stamps 0, every publish after it
    pre = dict(cb.raw(g.state))
    b2 = counters(pre)
    at3 = cb.mark(g)
    t0 = time.time()
    pre["_t"] = 0.0
    _control(g, True)
    back, _ = watch(g, BACK_WATCH_S, t0=t0)
    lines3 = cb.new(g, at3)
    ctx.marks["S-BACK"] = (samples + latch + back, lines + lines2 + lines3)
    ok, why = judge_back([pre] + back, lines3, b2, ctx.field)
    led.check("S-BACK", ok, why)


def _dioleave(g, ctx: Ctx) -> None:
    for attempt in range(4):
        ok, why = _ns(g, "dioleave")
        if ok or "no diorama is booted" in why:
            break
        if "deferred" not in why or attempt == 3:
            raise HarnessError(f"dioleave refused: {why}")
        g.wait_frames(30)
    st = cb.poll(g, lambda s: s.field_id == ctx.field and s.on_field and not cb.dio(s).get("booted"), LEAVE_S, "352 after the diorama")
    if st is None:
        raise HarnessError(f"no return to {ctx.field} after the diorama (field {g.state.field_id}, ui {g.state.ui_state!r})")
    _control(g, True)                                    # the cold return re-runs Main_Init; the harness's `control 0` never outlives it
    ok, why = _free_on(g, ctx.field, ARRIVE_S)
    if not ok:
        raise HarnessError(why)


def _s_battle(g, ctx: Ctx, led: cb.Ledger) -> None:
    raised, rsamples, at, _t0 = _raise(g, ctx)
    ctx.marks["S-BATTLE"] = (rsamples, cb.new(g, at))
    b0 = counters(rsamples[-1] if rsamples else g.state)
    t0 = time.time()
    booted, why = cb.boot(g, DIO_SCENE, DIO_PATTERN)
    if not booted:
        led.check("S-BATTLE", False, f"raised {raised}; the diorama never came up: {why}")
        _control(g, True)
        return
    try:
        samples, _ = watch(g, DIO_HOLD_S, t0=t0)
        lines = cb.new(g, at)
        _ns(g, "hostscene", 0)                           # before the return: the field comes back with no host scene to raise on
        ok, detail = judge_battle(raised, samples, b0, lines, ctx.field)
        led.check("S-BATTLE", ok, detail)
    finally:
        _dioleave(g, ctx)                                # never leave a diorama up for the next leg


def _s_off(g, ctx: Ctx, led: cb.Ledger) -> None:
    raised, rsamples, at, _t0 = _raise(g, ctx)
    ctx.marks["S-OFF"] = (rsamples, cb.new(g, at))
    b0 = counters(rsamples[-1] if rsamples else g.state)
    after, again, b_mid = [], [], {}
    if ctx.cal is None:                                  # calibrating: the lever is already held, and `act` would release it
        t0 = time.time()
        _speed(g, ctx, "off")
        after, _ = watch(g, OFF_S, t0=t0)
        b_mid = counters(after[-1] if after else g.state)
        _speed(g, ctx, "act")
        again, _ = watch(g, ON_S, until=mirror)
    lines = cb.new(g, at)
    ok, why = judge_off(raised, after, b0, lines, again, b_mid, ctx.field)
    led.check("S-OFF", ok, why)


def _s_f1(g, ctx: Ctx, led: cb.Ledger) -> None:
    _speed(g, ctx, "host", 1)
    _must(g, "hostscene", 1)
    _control(g, False)
    pre, _ = watch(g, F1_PRE_S)
    try:
        g.speedmode(True)
        f1, _ = watch(g, F1_HOLD_S)
    finally:
        g.speedmode(False)
    post, _ = watch(g, F1_POST_S)
    ok, why = judge_f1(pre, f1, post, ctx.cal, ctx.g_want)
    led.check("S-F1", ok, why)


def _s_stale(g, ctx: Ctx, led: cb.Ledger) -> None:
    _speed(g, ctx, "clear")                              # the bench host forgotten: src none (clear also sets the lever to act...)
    if ctx.cal is not None:
        _speed(g, ctx, "off")                            # ...so a calibration re-takes it at once
    _must(g, "hostscene", 0)
    _must(g, "bench", 1)
    _must(g, "lock", 1)
    cb.poll(g, lambda s: (s.netsync or {}).get("lock_engaged") is True, 3.0, "the bench lock to engage")
    try:
        _control(g, False)
        fresh, _ = watch(g, STALE_S)
        _must(g, "stale", 1)
        stale, _ = watch(g, STALE_S)
        _must(g, "stale", 0)
        back, _ = watch(g, STALE_S)
    finally:
        for step in (lambda: _ns(g, "stale", 0), lambda: _control(g, True), lambda: _ns(g, "lock", 0), lambda: _ns(g, "bench", 0)):
            try:
                step()
            except HarnessError:
                pass
    ok, why = judge_stale(fresh, stale, back, ctx.cal)
    led.check("S-STALE", ok, why)


def _s_world(g, ctx: Ctx, led: cb.Ledger) -> None:
    try:
        import coop_world_wait as ww                     # the s144 bench's proven walk out of 6603 (FF9CustomMap-world)
    except Exception as err:                             # noqa: BLE001 - its import never kills the run
        raise HarnessError(f"coop_world_wait would not import: {err!r}"[:300])
    try:
        g.warp(ww.FARSHORE)
        g.wait_frames(45)
    except HarnessError as err:
        raise HarnessError(f"warp {ww.FARSHORE} (FARSHORE, FF9CustomMap-world) failed: {str(err)[:200]}")
    ok, why, st = ww.walk_out(g)
    if st is None or st.ui_state != "WorldHUD":
        raise HarnessError(f"the walk out of {ww.FARSHORE} never reached the world map: {why}")
    if not ok:
        g.note(f"S-WORLD: on the world map, off the route's landing ({why}) -- the leg needs WorldHUD only")
    _speed(g, ctx, "host", HOST)
    _must(g, "hostscene", 1)
    try:
        _control(g, False)
        samples, _ = watch(g, WORLD_HOLD_S)
    finally:
        for step in (lambda: _control(g, True), lambda: _ns(g, "hostscene", 0)):
            try:
                step()
            except HarnessError:
                pass
    ok, detail = judge_world(samples, ctx.cal)
    led.check("S-WORLD", ok, detail)


def _k_r(g, ctx: Ctx, led: cb.Ledger) -> None:
    try:
        g.speedmode(True)                                # from off: the harness owns it, so the reset must switch it off
    except HarnessError as err:
        g.note(f"K-R: `speedmode 1` refused ({str(err)[:160]}) -- the release of the booster is not judged")
    at = cb.mark(g)
    held = ctx.lever_held or ctx.bench_host
    try:
        cb.release(g)
    except HarnessError as err:
        led.check("K-R", False, f"the release raised: {str(err)[:200]}")
        return
    lines = cb.new(g, at)
    try:
        _ns(g, "selftest", 1)
        st = cb.poll(g, lambda s: bool((s.netsync or {}).get("selftest")), 5.0, "the role again") or g.state
        _ns(g, "selftest", 0)
    except HarnessError as err:
        led.check("K-R", False, f"the re-read raised: {str(err)[:200]}")
        return
    line = cb.count(lines, LOG_RELEASE) > 0
    parts = [("lever null", sget(st, "lever", 0) is None), ("src none", sget(st, "src") == "none"),
             ("host_setting 1", ival(sget(st, "host_setting")) == 1), ("raw false", sget(st, "raw") is False),
             ("release line iff held", line == held)]
    led.check("K-R", all(v for _, v in parts), _fmt(parts) + f"; held into the reset: lever {ctx.lever_held}, bench host "
                                                             f"{ctx.bench_host}; {cb.grep(lines, 'speed mirror')}")
