"""s154 -- THE FOLLOW RACE, the TWO-GAME bench (tools/harness/duo.py; studies/coop-review/REVIEW.md 1.7 / appendix #5).
[ff9mapkit netsync s154]

Two real FF9s on this desktop, paired on 250 by duo.py (the guest FOLLOWING and its state mirror ARMED, so the same-field
kick never fires mid-race). The defect: a guest's field follow-warp is two-phase -- StartFollowWarp fades and stamps the
latch, ServiceFollowWarp writes SetNextMap + attr|=8 blind 0.9 s of GAME time later -- and nothing ties that commit to the
field instance it faded. Two arms, each provoked with the guest's OWN transition (the harness `warp`: the ~ menu's faded
warp, whose commit uses a gateway's own levers) racing the host's follow intent:

  FE1 / FE2  AN ORDINARY FOLLOW (250 -> 30602, then 30602 -> 250; the regression legs, GREEN on both DLLs): the host warps,
             the guest lands on the host's field by ONE load (one 'ghost spawned ... on field N' line, no second fade-out
             there) and no s154 drop / cancel / never-landed line is logged. Each also MEASURES the guest's load window of
             that field (shutdown -> landing, game seconds) -- the races below are aimed off it.
  FS         THE STRAND. The host warps 250 -> 30602 and the guest warps 250 -> 250 (its own reload), the two sends a SEND
             OFFSET apart (the host first by ~0.25 s: aimed so the follow's commit lands FS_TARGET_G of GAME time after the
             guest's own commit -- a few frames, inside its reload as the ENGINE counts it: THE CLOCK LAW below). The
             intent starts the follow while the guest's own warp is still fading; both timers run, a known game-time apart.
             FS-pre (REACHED): the follow is in flight across the guest's own reload of 250 and its commit falls INSIDE it,
             before 250's init (the observed order below). FS-a: the guest reaches 30602 (the host's field) within 10 s of
             that landing. FS-b: no stale latch -- from the landing + 5 s no sample reads pending -1 with warped_to 30602
             while the guest is off 30602. s153: the commit is wiped by 250's init (HonoluluFieldMain ff9InitStateFieldMap:
             attr &= ~0x30F, nextMapNo = fldMapNo) and FollowHostTick returns at `rs.Field == _followWarpedTo` forever --
             the guest sits on 250, 'following them there...' (both red).
  FD         THE DOUBLE LOAD. Both on 250: the guest warps 250 -> 30602 itself, the host warps there too ~7 s later (aimed
             at dgame FD_TARGET_G, as late as the guest's own timer allows: the commit then falls ~0.75 game s past the
             guest's landing, and the conservative clock still proves it past the init on a load stall up to ~0.6 s).
             FD-pre (REACHED): the follow's commit falls AFTER the guest's own landing on 30602, past its init grace
             (INIT_GRACE_G + TOL_G) on the conservative clock, and the own load is witnessed by the per-load dress counter
             (so a second load can be seen). FD-a: ONE load of 30602 -- no second fade-out rising edge while field.id ==
             30602, exactly one 'ghost spawned ... on field 30602' line, the per-load dress counter advanced once and at
             most one 'self-dress: field 30602' line. FD-b: the pending never survives the landing -- no FieldHUD sample
             on 30602 past the landing's init grace reads pending 30602.
             s153: the commit runs on the live 30602 and reloads it (Main_Init twice; both red).

THE ORDER, OBSERVED (the critique's law: dgame alone cannot make s153 red -- a short load turns FS green on s153, a long
one FD). Each race runs on the guest's own state stream at `stateevery 1`, every publish pulled from the Session's ring
with its WRITE time (read_at - age), and is judged only on the observed order of its edges:
  * the guest's own warp start: the first sample after its send with player.control false (Warp's SetUserControl);
  * the follow's start: netsync.session.follow.pending rising to 30602; its COMMIT is that start + FollowFadeWait (0.9 s)
    of GAME time, on the game clock integrated off the stream itself (game_bounds: THE CLOCK LAW);
  * the guest's own shutdown: the first sample with fading true, ui_state off FieldHUD or field.id off the start field
    (the scene change's _Fade: IsFading -- the debug warp's FF9Wipe never sets it) -- OR THE LOAD'S STALL: the first
    published gap past the guest's own commit that the game, not the sampler, spent (>= STALL_S and >= STALL_FRAME_S a
    frame). [ff9mapkit netsync s154] A same-field reload (FS: 250 -> 250) moves no field id and its IsFading pulse is
    two or three frames inside a burst right after the load: the s153 calibration's sampler (a read every ~2nd frame)
    missed it on every attempt, took the follow's later departure to 30602 for the reload ('never landed on 250 after
    its shutdown') or saw no shutdown at all on the attempt that DID strand. The stall is never missed;
  * its landing: the first sample at or after that shutdown with field.id the warp's target, FieldHUD, fading false;
  * [ff9mapkit netsync s154] the init's POST-witness (FS): the first sample from that shutdown on with the per-load dress
    counter (netsync.dress.self.attach_cold: Main_Init's SetModel, after the init's wipe) past its pre-shutdown value, or
    control back on the landed field -- both engines publish both. The follow's commit falls BEFORE the init when the
    pending is already down on a sample before that witness.
  THE CLOCK LAW [ff9mapkit netsync s154]: a level load's wall stall is NOT game time. Unity spends one nominal frame on
  the frame after Application.LoadLevel (its post-load delta reset), so both 0.9 s timers count a 0.4-0.6 s load as a
  frame or two -- while the old single clock counted the stall in full (capped at 1/3 s a frame). On s153 every FD
  attempt's pending fell 0.35-0.5 s of that clock after the modeled commit ('mismatch'), and FS's aim (mid-WALL-window,
  0.138 game s past the guest's own commit) landed the commit AFTER 250's init on two attempts (a hard cut to 30602, s153
  green) and before it on one (the strand). game_bounds gives each sample an INTERVAL [lo, hi]: hi is that old clock (a
  stall counted in full: an upper bound on what any engine timer spent), lo counts a stalled gap as its frames x
  DT_FLOOR (a lower bound: no frame spends less). Every verdict on the model is taken where the interval decides it: FD's
  order (the commit past the landing's init) on hi, the fall's agreement with the timer on the interval, FS's order on
  the observed edges alone.
  THE INIT LAG [ff9mapkit netsync s154]: that landed sample is NOT the field's init. s154's landing step (NoteFieldLanding,
  in ApplyStoryBeforeEvents) runs inside the new field's first HonoUpdate, which waits for IsFading to fall
  (HonoluluFieldMain.cs:203) and for a frame with a logic tick (30 Hz field logic under a faster render), and the harness's
  publish is not ordered against it -- so one or two published samples read landed with the pending still set, on BOTH
  DLLs. The bench grants INIT_GRACE_G (0.1 game s: a logic tick plus a frame, well under FD_MARGIN_G) after the landing:
  FD-b ignores the samples inside it, the 'landing' fall is bounded on the LAST sample still reading the pending (the
  first one after the fall is written only after the init frame's synchronous field load), and FD is REACHED only when its
  commit falls past the landing + INIT_GRACE_G + TOL_G on hi (inside it the order reads "in-init": never judged).
  Every edge is a BRACKET (the last sample before it, the first after it -- THE WITNESS LAW). FS is REACHED ("in-load")
  only when the pending was still set on the last sample before the reload's shutdown, the guest re-landed on 250 (a
  landing on 30602 instead is the commit OVERWRITING the guest's own warp: "overwrite"), and the pending was already down
  on a sample BEFORE the init's post-witness -- the fall on that witness's sample is "ambiguous", after it "after-init"
  (s153 hard-cuts there: green, never judged). FD is REACHED only when the commit's bracket lies past the landing's init
  grace on hi. Anything else is UNREACHED with the measured order, and the leg retries (TRIES) with its send offset
  corrected by the latency the measured dgame implies and its aim stepped by the order (FS: a frame or so earlier after
  the init, later before the shutdown; FD: later by the lead it lacked). The observed pending FALL cross-checks the model:
  it must be possible on the scheduled commit's interval (the timer -- s153, and s154's commit guard) or, for FD only,
  certainly EARLIER, between the guest's own shutdown and its landing's init (s154's landing step cancelling it -- the
  fix, not another race); any other fall is an instrument mismatch and the attempt reads UNREACHED.
  The new s154 lines (dropped / cancelled / never landed / waits) are corroboration only: no leg is judged on them.
  Every attempt's stream is saved beside the guest's report (follow-<leg>-<n>.jsonl, the rows the judges read), so the
  next diagnosis reads the race itself and not the ring's last 300 samples.

THE DETERMINISM LEVER is the existing `timescale` verb: on the guest at 0.1 both 0.9 s timers (ServiceFollowWarp and
Ff9mkDebugMenu.ServicePendingWarp) spend Time.deltaTime, while every netsync clock runs on render frames -- so the game-time
gap between them is 0.1 x the real gap (cross-process jitter of ~50 ms becomes ~5 ms). `timescale 1` goes back before
either timer runs out, which keeps the gap. timescale 1 and stateevery 2 are restored in a finally.

CALIBRATION (COOP_CALIBRATE=1, ON THE s153 DLL FIRST): FR-CAL judges exactly PREDICTED_S153 red over the legs whose
precondition was REACHED (an unreached leg is NOT calibrated and named; none reached = red), and reads red outright when
the log holds an s154 follow line (this is not the s153 DLL). FE1 / FE2 and every *-pre row are never predicted red: a red
there is the instrument, and the run's verdict is void.

    py tools/harness/duo.py studies/test-harness/scenarios/coop_follow_race_duo.py --keep-going
    COOP_CALIBRATE=1 py tools/harness/duo.py studies/test-harness/scenarios/coop_follow_race_duo.py --keep-going   (s153)

Prereqs as duo.py's (both roots built, no FF9 from either, no controller connected, nobody at the keyboard -- THE
UNATTENDED LAW), LOCKT2 (30602) registered on both roots (the -msgs folder). --keep-going is not required (the bench turns
strict off for its own rows) but keeps duo.py's own C* rows recorded too.
NOT PROVEN HERE: the 1-frame script-overwrite arm (a door's MAPJUMP one frame after the commit) and a gateway MAPJUMP as the
own transition -- the selftest's landing rows (L3) carry those; feel.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from harness.duo import MATCHERS as DUO_MATCHERS                    # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                          # noqa: E402 - Ledger, path, CALIBRATE

HarnessError = cb.HarnessError
CALIBRATE = cb.CALIBRATE

HOME = 250                     # duo.py's BENCH_FIELD: Evil Forest/Trail, the pairing field
AWAY = 30602                   # LOCKT2 in the -msgs folder: registered on both roots, walkable

# The engine's clocks, each by its C# name.
FOLLOW_FADE_S = 0.9            # NetSyncClient.FollowFadeWait: the follow's commit, in GAME seconds after its start
WARP_FADE_S = 0.9              # Ff9mkDebugMenu.WarpFadeWait: the harness `warp`'s commit (the host's, and the guest's own)
MAX_DT = 1.0 / 3.0             # Unity Time.maximumDeltaTime (default): no frame spends more than this (the clock's hi)
FRAME_G = 1.0 / 60.0           # one render frame of game time at timescale 1 (the margin unit)
# [ff9mapkit netsync s154] THE CLOCK LAW's terms (game_bounds). Unity's frame after Application.LoadLevel spends one nominal
# frame (1/targetFrameRate; FieldFPS -1 here: its startup 0.02 s), never the load's 0.4-0.6 s stall -- the clock's lo.
DT_FLOOR = 1.0 / 90.0          # the least game time any frame spends at timescale 1 (a 90 fps frame; the post-load one: 1/60-0.02)
STALL_S = 0.12                 # a published gap this long ...
STALL_FRAME_S = 0.05           # ... averaging this much wall a frame is the GAME stalling (a level load, a long init frame),
                               # never the sampler (a sampler hiccup spans as many frames as its wall time holds)

SLOW = 0.1                     # the guest's timescale for a race's start phase
TOL_G = 0.05                   # the timer model's slack, game seconds (the timescale switch's frame + a publish)
TRIES = 3                      # attempts per race before it reads UNREACHED
LAT0 = 0.05                    # the first guess of the host-warp -> guest-follow-start latency (s, real), corrected per try
INIT_GRACE_G = 0.1             # [ff9mapkit netsync s154] THE INIT LAG: the landed sample(s) before the new field's first
                               # HonoUpdate (the landing step) -- one 30 Hz tick plus a frame; well under FD_MARGIN_G
# [ff9mapkit netsync s154] THE AIMS, in GAME seconds between the two starts (dgame) -- i.e. how long after the guest's own
# commit the follow's commit falls, as the ENGINE counts it (both timers are 0.9 s of the same deltaTime).
FS_TARGET_G = 0.07             # FS: ~4 frames past the guest's own commit -- after its consumption (the next 30 Hz tick, <= 2
                               # frames: earlier, the commit OVERWRITES the own warp) and the load's own frame, inside 250's
                               # post-load frames before its init (6-12 frames on the s153 calibration's machine: its strand/
                               # hard-cut split fell at dgame ~0.13)
FS_STEP_G = 0.02               # FS: one correction step (about a frame) per unreached attempt
FS_MIN_G, FS_MAX_G = 0.035, 0.12
FD_TARGET_G = 0.82             # FD: as late as the guest's own timer allows -- the commit ~0.75 game s past the landing
FD_STEP_G = 0.02               # FD: the least correction step
FD_MARGIN_G = 0.3              # FD: the floor of its aim -- even then s153's pending survives this long past the landing
FD_MAX_G = 0.86                # ...and the cap: the follow must start (and the switch to timescale 1 land) before the guest's
                               # own 0.9 s timer runs out (0.04 game s = 0.4 s real at SLOW)

FOLLOW_S = 15.0                # FE: the host's warp -> the guest's landing on the host's field
SETTLE_S = 3.0                 # FE: samples after that landing (a second load would show here)
RISE_S = 8.0                   # a race: the follow's start after the later send
LAND_S = 12.0                  # a race: the timescale switch -> the guest's own landing
JUDGE_S = 10.0                 # a race: the judge window after that landing
LATCH_FROM_S = 5.0             # FS-b: the stale-latch window opens this long after the landing
SEAT_S = 30.0

#: Each race's REACHED order.
REACH = {"FS": "in-load", "FD": "after-landing"}
#: COOP_CALIBRATE=1 on the s153 DLL: exactly these red, per REACHED leg (FE and every *-pre are the instrument).
PREDICTED_S153 = {"FS": ("FS-a", "FS-b"), "FD": ("FD-a", "FD-b")}
PREDICTED_S153_LEGS = tuple(PREDICTED_S153)

CATALOG = {
    "FR-PRE": "the pair is ready: both games on 250, the guest on FieldHUD and MIRRORING (the armed mirror keeps the same-field "
              "kick out of every leg), 30602 registered on both roots, netsync.session.follow published",
    "FE1": "an ordinary follow 250 -> 30602: the guest lands on the host's field by ONE load (one 'ghost spawned ... on field "
           "30602' line, no second fade-out there) and logs no s154 drop / cancel / never-landed line",
    "FE2": "an ordinary follow 30602 -> 250: one load, one ghost line on 250, no s154 drop / cancel / never-landed line",
    "FS-pre": "THE STRAND's race REACHED: the follow is in flight across the guest's own reload of 250 and its commit falls "
              "inside it -- the pending still set on the last sample before the reload's shutdown (its fade, or the load's "
              "stall), the guest re-landed on 250, and the pending down on a sample before 250's init post-witness (the "
              "per-load dress counter, or control back); the fall agrees with the timer's interval",
    "FS-a": "the guest reaches the host's field 30602 (FieldHUD) within 10 s of its own reload's landing -- never stranded on 250",
    "FS-b": "no stale latch: from that landing + 5 s no sample reads follow.pending -1 with warped_to 30602 while the guest is "
            "off 30602",
    "FD-pre": "THE DOUBLE LOAD's race REACHED: the follow's commit falls after the guest's own landing on 30602, past its init "
              "grace (0.1 game s + the timer slack) on the conservative clock (a load's stall counted in full); the pending's "
              "observed fall agrees (the timer's interval, or s154's landing step at that load's init); the own load is "
              "witnessed by the per-load dress counter",
    "FD-a": "ONE load of 30602: after the guest's own landing no second fade-out rising edge while field.id == 30602, exactly "
            "one 'ghost spawned ... on field 30602' line, the per-load dress counter advanced once and at most one "
            "'self-dress: field 30602' line",
    "FD-b": "the follow never survives the landing: no FieldHUD sample on 30602 (fading false) past the landing's init grace "
            "(0.1 game s: the samples before the new field's first logic tick) reads follow.pending 30602",
}
CAL_ID = "FR-CAL"
CAL_CLAIM = ("CALIBRATION (COOP_CALIBRATE=1, the s153 DLL): exactly PREDICTED_S153 red over the REACHED legs, nothing else red "
             "but an unreached leg's own rows, and no s154 follow line in the log")


def catalog(calibrate: bool = CALIBRATE) -> dict:
    cat = dict(CATALOG)
    if calibrate:
        cat[CAL_ID] = CAL_CLAIM
    return cat


#: The guest's lines this bench reads. The s154 ones are corroboration only (written from design-follow-race.json's logging
#: section; a reworded line only drops a note). `ghost` is duo.py's own matcher, verbatim.
MINE = {
    "ghost": DUO_MATCHERS["ghost"],
    "intent": re.compile(r"^\[NetSync\] intent: following the peer to field (\d+) \(parallel\)$"),
    "drop_world": re.compile(r"^\[NetSync\] follow-warp to field (\d+) dropped: the field left for the world map inside its "
                             r"fade"),
    # [ff9mapkit netsync s154] the commit guard, the landing step, the start defer (the follow's and the same-field kick's
    # forms both: NoteFieldLanding prints "<what> cancelled / never landed" with what = "follow-warp to field N" or "the
    # same-field kick on field N"; NoteFollowWaits "the follow to field N waits" or "the same-field kick on field N waits")
    "drop_inflight": re.compile(r"^\[NetSync\] follow-warp to field (\d+) dropped: (?!the field left for the world map)(.+)$"),
    "cancel": re.compile(r"^\[NetSync\] (?:follow-warp to field|the same-field kick on field) (\d+) cancelled: (.+)$"),
    "never_landed": re.compile(r"^\[NetSync\] (?:follow-warp to field|the follow to field|the same-field kick on field) (\d+) "
                               r"never landed"),
    "waits": re.compile(r"^\[NetSync\] (?:the follow to field|the same-field kick on field) (\d+) waits: (.+)$"),
    "selftest": re.compile(r"^\[NetSync\] follow race selftest: (OK|FAIL) \((.*)\)$"),
    # [ff9mapkit netsync s154] the s140 self-dress line, one per field load of the guest's own body (DoEventCode SetModel):
    # both DLLs print it -- a load witness that no sampling gap can miss (FD-a)
    "dress": re.compile(r"^\[NetSync\] self-dress: field (\d+) uid (-?\d+) sid (-?\d+): "),
}
S154_LINES = ("drop_inflight", "cancel", "never_landed", "waits")


# ================================================================================================ the pure judges
def _int(v, default=-1) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def row_of(st) -> dict:
    """One guest publish as the judges read it: its WRITE time (``mtime``, else the read time), frame, the timescale it
    published, fading / ui_state / field.id / player.control, netsync.session.follow's pending / warped_to, and
    [ff9mapkit netsync s154] ``dress`` = netsync.dress.self.attach_cold (the per-load counter of the guest's own body:
    Main_Init's SetModel, one per field load while the self-dress is armed; None when not published)."""
    raw = st.raw if hasattr(st, "raw") else (st or {})
    fol = cb.path(raw, "netsync.session.follow") or {}
    t = getattr(st, "mtime", None) or getattr(st, "read_at", None) or time.time()
    ts = raw.get("timescale")
    dress = cb.path(raw, "netsync.dress.self.attach_cold")
    return {"t": float(t), "frame": _int(raw.get("frame"), -1),
            "ts": float(ts) if isinstance(ts, (int, float)) and not isinstance(ts, bool) and ts > 0 else 1.0,
            "fading": bool(raw.get("fading", False)), "ui": raw.get("ui_state"),
            "field": _int((raw.get("field") or {}).get("id"), -1),
            "control": bool((raw.get("player") or {}).get("control", False)),
            "pending": _int(fol.get("pending"), -1), "warped_to": _int(fol.get("warped_to"), -1),
            "dress": _int(dress, None) if isinstance(dress, (int, float)) and not isinstance(dress, bool) else None,
            "overlay": cb.path(raw, "netsync.session.overlay"), "mirroring": cb.path(raw, "netsync.session.mirroring")}


def _gap(a: dict, b: dict) -> tuple:
    """(wall seconds, frames >= 1) between two consecutive samples."""
    return max(0.0, float(b["t"]) - float(a["t"])), max(1, int(b["frame"]) - int(a["frame"]))


def stalled(rows, j: int) -> bool:
    """[ff9mapkit netsync s154] The gap before sample ``j`` is the GAME stalling (a level load, a long init frame): at least
    STALL_S of wall time and STALL_FRAME_S a frame -- never the sampler, whose hiccup spans as many frames as it lasts."""
    if j <= 0 or j >= len(rows):
        return False
    dt, n = _gap(rows[j - 1], rows[j])
    return dt >= STALL_S and dt >= n * STALL_FRAME_S


def game_bounds(rows, max_dt: float = MAX_DT, floor: float = DT_FLOOR) -> tuple:
    """[ff9mapkit netsync s154] THE CLOCK LAW: the engine's GAME clock at each sample as an interval (lo, hi), seconds from the
    first sample. A one-frame gap spends the EARLIER sample's timescale (a frame's deltaTime is fixed at its start); a longer
    one could hold the switch, so hi spends the larger and lo the smaller of the two. ``hi`` spends the write-time gap capped
    at ``max_dt`` a frame -- an upper bound on any engine timer (the old single clock, a level load's stall counted in
    full). ``lo`` spends the same on an ordinary gap, but a STALLED gap (:func:`stalled`) only its frames x ``floor``: Unity
    spends one nominal frame on the frame after Application.LoadLevel, so a load's 0.4-0.6 s of wall is a frame or two of
    game time to both 0.9 s timers -- lo is a lower bound either way (a stalled init frame, which IS counted, only
    makes it looser)."""
    lo, hi = [0.0], [0.0]
    for j in range(1, len(rows or [])):
        a, b = rows[j - 1], rows[j]
        dt, n = _gap(a, b)
        ta, tb = float(a["ts"]), float(b["ts"])
        ts_lo, ts_hi = (ta, ta) if n == 1 else (min(ta, tb), max(ta, tb))
        spent = min(dt, n * max_dt)
        hi.append(hi[-1] + ts_hi * spent)
        lo.append(lo[-1] + ts_lo * (min(spent, n * floor) if stalled(rows, j) else spent))
    return lo, hi


def game_clock(rows, max_dt: float = MAX_DT) -> list:
    """The conservative GAME clock (game_bounds' ``hi``): a level load's stall counted in full, capped at ``max_dt`` a frame
    -- an upper bound on what any engine timer spent between two samples. The judges' grace windows run on it."""
    return game_bounds(rows, max_dt)[1]


def shut_evidence(r: dict, origin: int) -> bool:
    """The guest's own scene change is under way: the scene fade (IsFading), off FieldHUD, or field.id moved off ``origin``
    (fldMapNo takes nextMapNo at the shutdown)."""
    return bool(r["fading"]) or r["ui"] != "FieldHUD" or r["field"] != origin


def landed(r: dict, target: int) -> bool:
    return r["field"] == target and r["ui"] == "FieldHUD" and not r["fading"]


def _first(rows, pred, start: int = 0):
    for i in range(max(0, start), len(rows)):
        if pred(rows[i]):
            return i
    return None


def _br(G, i):
    """An edge's bracket on the game clock: (the sample before it, its first sample)."""
    return (G[i - 1] if i > 0 else G[i], G[i])


def _r3(x):
    return None if x is None else round(float(x), 3)


def dress_loads(rows, start: int = 0):
    """[ff9mapkit netsync s154] How many field loads of the guest's own body the per-load dress counter saw from sample
    ``start`` on (its last value minus its value there) -- None when the counter is not published, 0 when it never moved
    (the self-dress not armed: no witness)."""
    vals = [r.get("dress") for r in (rows or [])[max(0, start):] if r.get("dress") is not None]
    return (vals[-1] - vals[0]) if vals else None


def own_edges(rows, *, origin: int, own_target: int, t_own_send: float, bounds=None, tol: float = TOL_G) -> dict:
    """[ff9mapkit netsync s154] The guest's own warp on its stream -> {i_w, i_s, shut_by, i_l, landed_on}: its start (the first
    sample after its send with control off), its shutdown (the first later sample with explicit evidence -- fading, ui off
    FieldHUD, field.id off ``origin`` -- or, once its own 0.9 s timer can have run out, the post sample of a GAME STALL: a
    same-field reload shows no persistent field change and its fade pulse is easily missed), and its landing (the first
    sample from that shutdown on that is FieldHUD, not fading, on a field: ``landed_on`` names it -- ``i_l`` is set only
    when it is ``own_target``)."""
    out = {"i_w": None, "i_s": None, "shut_by": None, "i_l": None, "landed_on": None}
    if not rows:
        return out
    lo, hi = bounds or game_bounds(rows)
    i_w = _first(rows, lambda r: r["t"] >= t_own_send and r["control"] is False)
    out["i_w"] = i_w
    if i_w is None:
        return out
    base = hi[max(0, i_w - 1)]
    for j in range(i_w + 1, len(rows)):
        r = rows[j]
        if shut_evidence(r, origin):
            out["i_s"] = j
            out["shut_by"] = "fade" if r["fading"] else ("ui" if r["ui"] != "FieldHUD" else "field")
            break
        if stalled(rows, j) and hi[j - 1] - base >= WARP_FADE_S - 2.0 * tol:   # the last pre-stall sample: <= 2 frames early
            out["i_s"], out["shut_by"] = j, "stall"
            break
    if out["i_s"] is None:
        return out
    k = _first(rows, lambda r: r["ui"] == "FieldHUD" and not r["fading"] and r["field"] > 0, out["i_s"])
    if k is not None:
        out["landed_on"] = rows[k]["field"]
        out["i_l"] = k if rows[k]["field"] == own_target else None
    return out


def race_order(rows, *, dest: int, own_target: int, t_own_send: float, follow_s: float = FOLLOW_FADE_S,
               tol: float = TOL_G, init_grace: float = INIT_GRACE_G) -> dict:
    """THE OBSERVED ORDER of one race on the guest's stream -> {order, consistent, fall, why, dgame, window, ...}.

    Common edges (own_edges): the guest's own warp start i_w, the follow's start i_r (pending rising to ``dest``), the own
    shutdown i_s (``shut_by``: fade / ui / field / stall), its landing i_l, the pending's first fall i_f. Unreached shapes:
    "no-own-warp", "no-follow", "follow-first" (the follow before the own warp), "no-shutdown", "follow-late" (the follow
    started after the own shutdown began), "no-landing".

    THE RELOAD (FS: ``own_target`` is the start field) -- judged on the observed edges alone [ff9mapkit netsync s154]:
    "overwrite" (the own warp landed on another field right at its own commit: the follow's commit overwrote it before its
    consumption -- a later departure to another field is the reload unseen, "no-shutdown"),
    "before-shutdown" (the pending fell on or before the last pre-shutdown sample), "in-load" (REACHED: fallen on a sample
    before the init's post-witness i_post -- the per-load dress counter past its pre-shutdown value, or control back on the
    landed field), "ambiguous" (fallen first on i_post's own sample), "after-init" (still set past it: s153 hard-cuts
    there), "no-init-witness", "no-fall".
    THE DOUBLE LOAD (FD) -- the commit against the edges on THE CLOCK LAW's interval (``rel_*`` = how long after a sample
    the commit falls, [lo, hi] game s): "after-landing" (REACHED: the commit's lo past the landing + ``init_grace`` +
    ``tol``), "in-init" (certainly past the landed sample but inside that grace: the init may not have run -- never judged),
    "in-load", "before-shutdown", "ambiguous". ``witness``: the own load moved the per-load dress counter (FD-a can see a
    second load).
    ``fall``: "timer" (possible on the scheduled commit's interval), "landing" (certainly earlier, on the LAST sample still
    reading the pending at or after the last pre-shutdown sample and no later than the landing + ``init_grace``: s154's
    landing step -- FD only), "mismatch" or "never". ``consistent`` = FS: "timer"; FD: "timer" or "landing".
    ``init_lag`` = the landed samples still reading the pending (count, frames, game s to the fall)."""
    out = {"order": "no-samples", "consistent": False, "fall": None, "why": "", "dgame": None, "dgame_lo": None,
           "dgame_hi": None, "window": None, "fc": None, "fc_lo": None, "shut": None, "land": None, "shut_by": None,
           "landed_on": None, "rel_shut": None, "rel_land": None, "fall_at": None, "fall_rel": None, "witness": None,
           "loads": None, "i_w": None, "i_r": None, "i_s": None, "i_l": None, "i_f": None, "i_post": None,
           "post_by": None, "init_lag": None, "reload": None, "samples": len(rows or [])}
    if not rows or len(rows) < 3:
        out["why"] = f"{len(rows or [])} sample(s)"
        return out
    L, H = game_bounds(rows)
    i_w = _first(rows, lambda r: r["t"] >= t_own_send and r["control"] is False)
    out["i_w"] = i_w
    if i_w is None:
        out.update(order="no-own-warp", why="the guest's own warp never took control off (refused? not on FieldHUD?)")
        return out
    origin = rows[i_w]["field"]
    reload = own_target == origin
    out["reload"] = reload
    i_r = _first(rows, lambda r: r["pending"] == dest)
    out["i_r"] = i_r
    if i_r is None:
        out.update(order="no-follow", why=f"follow.pending never read {dest} (the intent never started the follow)")
        return out
    if i_r <= i_w:
        out.update(order="follow-first", why="the follow started before (or with) the guest's own warp: dgame <= 0")
        return out
    pw = max(0, i_w - 1)
    dlo, dhi = L[i_r - 1] - L[i_w], H[i_r] - H[pw]
    out.update(dgame_lo=_r3(dlo), dgame_hi=_r3(dhi), dgame=_r3((dlo + dhi) / 2.0),
               fc_lo=_r3(H[i_r - 1] + follow_s), fc=_r3((H[i_r - 1] + H[i_r]) / 2.0 + follow_s))
    e = own_edges(rows, origin=origin, own_target=own_target, t_own_send=t_own_send, bounds=(L, H), tol=tol)
    i_s, i_l = e["i_s"], e["i_l"]
    out.update(i_s=i_s, i_l=i_l, shut_by=e["shut_by"], landed_on=e["landed_on"])
    loads = dress_loads(rows, i_w)
    out.update(loads=loads, witness=bool(loads))
    if i_s is None:
        out.update(order="no-shutdown", why=f"dgame {out['dgame']} s; no sample showed the guest's own shutdown (no fade, ui, "
                                            f"field change or load stall after its own commit)")
        return out
    if i_r >= i_s:
        out.update(order="follow-late", why=f"dgame {out['dgame']} s; the follow started after the guest's own shutdown began "
                                            f"(by {e['shut_by']}) -- not in flight across it")
        return out
    gs = (H[i_s - 1], H[i_s])
    out["shut"] = [_r3(gs[0]), _r3(gs[1])]
    if i_l is None:
        late = H[i_s - 1] - H[pw] - WARP_FADE_S        # how long past the guest's own commit that shutdown began (hi)
        if reload and e["landed_on"] is not None and e["landed_on"] != own_target and late <= 4.0 * FRAME_G + tol:
            out.update(order="overwrite", why=f"dgame {out['dgame']} s; the guest's own warp landed on {e['landed_on']}, not "
                                              f"{own_target}: the follow's commit overwrote it before its consumption")
        elif reload and e["landed_on"] is not None and e["landed_on"] != own_target:
            out.update(order="no-shutdown", why=f"dgame {out['dgame']} s; the first shutdown evidence (by {e['shut_by']}) is "
                                                f"a departure to {e['landed_on']} {_r3(late)} s past the guest's own commit "
                                                f"-- the reload of {own_target} itself went unseen (no fade, no stall)")
        else:
            out.update(order="no-landing", why=f"dgame {out['dgame']} s; the guest never landed on {own_target} after its "
                                               f"shutdown (by {e['shut_by']})")
        return out
    gl = (H[i_l - 1], H[i_l])
    out.update(land=[_r3(gl[0]), _r3(gl[1])], window=_r3(((gl[0] - gs[1]) + (gl[1] - gs[0])) / 2.0))
    pr = max(0, i_r - 1)

    def rel(x):                              # how long after sample x the commit falls: [lo, hi] game s
        return follow_s - (H[x] - H[pr]), follow_s - (L[x] - L[i_r])

    rs, rl = rel(i_s - 1), rel(i_l)
    out.update(rel_shut=[_r3(rs[0]), _r3(rs[1])], rel_land=[_r3(rl[0]), _r3(rl[1])])
    i_f = _first(rows, lambda r: r["pending"] != dest, i_r + 1)
    out["i_f"] = i_f
    lag = ""
    if i_f is None:
        fall = "never"
    else:
        f_lo, f_hi = L[i_f - 1] - L[i_r], H[i_f] - H[pr]
        out.update(fall_at=[_r3(H[i_f - 1]), _r3(H[i_f])], fall_rel=[_r3(f_lo), _r3(f_hi)])
        if f_lo < follow_s + tol and f_hi >= follow_s - tol:
            fall = "timer"
        elif f_hi < follow_s - tol and i_f - 1 >= i_s - 1 and H[i_f - 1] <= H[i_l] + init_grace:
            fall = "landing"                   # [ff9mapkit netsync s154] bounded on the LAST pending sample: the first
        else:                                  # sample after the fall is written only after the init frame's field load
            fall = "mismatch"
        if i_f > i_l:
            out["init_lag"] = {"samples": i_f - i_l, "frames": int(rows[i_f]["frame"]) - int(rows[i_l]["frame"]),
                               "last_g": _r3(H[i_f - 1] - H[i_l]), "fall_g": _r3(H[i_f] - H[i_l])}
            lag = (f"; {i_f - i_l} landed sample(s) still read the pending ({out['init_lag']['frames']} frame(s): the last "
                   f"+{out['init_lag']['last_g']} s, the fall +{out['init_lag']['fall_g']} s after the landing)")
        else:
            lag = "; the pending fell before the landing"
    head = (f"dgame {out['dgame']} [{out['dgame_lo']}, {out['dgame_hi']}] s; own shutdown by {e['shut_by']} {out['shut']}, "
            f"landing {out['land']} on {own_target}; pending fell {out['fall_at']} -> {fall} (rise -> fall "
            f"{out['fall_rel']} game s, the timer {follow_s:g}){lag}")
    if reload:
        pre = rows[i_s - 1].get("dress")
        i_post = _first(rows, lambda r: (pre is not None and r.get("dress") is not None and r["dress"] > pre)
                        or (r["control"] and landed(r, own_target)), i_s)
        out["i_post"] = i_post
        if i_post is not None:
            rp = rows[i_post]
            out["post_by"] = "dress" if (pre is not None and rp.get("dress") is not None and rp["dress"] > pre) else "control"
        if i_f is None:
            order = "no-fall"
        elif i_f < i_s:
            order = "before-shutdown"
        elif i_post is None:
            order = "no-init-witness"
        elif i_f < i_post:
            order = "in-load"
        elif i_f == i_post:
            order = "ambiguous"
        else:
            order = "after-init"
        post = (f"; the init's post-witness ({out['post_by']}) at sample +{i_post - i_s} from the shutdown"
                if i_post is not None else "; no init post-witness (dress counter flat, control never back)")
        out.update(order=order, fall=fall, consistent=fall == "timer")
        out["why"] = f"{head}{post}; order {order}"
        return out
    if rs[1] <= 0:
        order = "before-shutdown"
    elif rs[0] > 0 and rl[1] < 0:
        order = "in-load"
    elif rl[0] > init_grace + tol:            # [ff9mapkit netsync s154] past the init lag on hi: 'landing' and 'timer' apart
        order = "after-landing"
    elif rl[0] > 0:
        order = "in-init"
    else:
        order = "ambiguous"
    out.update(order=order, fall=fall, consistent=fall in ("timer", "landing"))
    out["why"] = (f"{head}; the commit {out['rel_land']} game s after the landing (past the init grace {init_grace:g} + "
                  f"{tol:g} needed); the own load witnessed by the dress counter: "
                  f"{'yes' if out['witness'] else 'NO'} ({loads} load(s)); order {order}")
    return out


def reached(leg: str, order: dict) -> bool:
    """The leg's order was observed and the fall agreed. FD's "after-landing" already requires the commit past the
    landing's init grace (race_order): an "in-init" commit is never judged as FD; FD also needs its load WITNESSED (the
    per-load dress counter moved), or FD-a could not see a second load."""
    ok = order.get("order") == REACH[leg] and bool(order.get("consistent"))
    return ok and (leg != "FD" or bool(order.get("witness")))


#: [ff9mapkit netsync s154] How each unreached order moves the next attempt's aim (a sign: +1 later, -1 earlier).
FS_STEER = {"before-shutdown": 1, "overwrite": 1, "after-init": -1, "ambiguous": -1, "no-landing": -1}
FD_STEER = {"in-init": 1, "ambiguous": 1, "in-load": 1, "before-shutdown": 1, "follow-late": -1}


def next_dgame(leg: str, order: dict, target: float) -> float:
    """The next attempt's dgame aim, off THIS attempt's observed order: FS steps FS_STEP_G (about a frame) later when the
    commit fell before the guest's own shutdown (or overwrote its warp), earlier when it fell at or after 250's init;
    FD aims later by the lead it lacked on hi (at least FD_STEP_G), earlier when the follow started too late. The old aim
    when the order says nothing about it."""
    o = order.get("order")
    if leg == "FS":
        step = FS_STEER.get(o, 0)
        return max(FS_MIN_G, min(FS_MAX_G, float(target) + step * FS_STEP_G))
    step = FD_STEER.get(o, 0)
    if step < 0:
        return max(FD_MARGIN_G, float(target) - 1.5 * FD_STEP_G)
    if step > 0:
        try:
            lack = INIT_GRACE_G + TOL_G - float(order["rel_land"][0])
        except (TypeError, KeyError, ValueError, IndexError):
            lack = 0.0
        return max(FD_MARGIN_G, min(FD_MAX_G, float(target) + max(FD_STEP_G, lack + FD_STEP_G)))
    return max(FD_MARGIN_G, min(FD_MAX_G, float(target)))


OFFSET_RANGE = (-(WARP_FADE_S - 0.05), 8.0)   # never a follow start before the guest's own warp; never past its timer


def offset_for(dgame: float, lat: float) -> float:
    """The SEND OFFSET (the host's warp send minus the guest's own, real seconds; negative = the host first) that puts the
    follow's start ``dgame`` of game time after the guest's own warp start: the follow starts when the host's warp commits
    (WARP_FADE_S at the host's timescale 1) plus ``lat`` (the intent's trip), while the guest runs at SLOW -- so
    dgame = SLOW (offset + WARP_FADE_S + lat). Clamped to :data:`OFFSET_RANGE`."""
    return max(OFFSET_RANGE[0], min(OFFSET_RANGE[1], dgame / SLOW - WARP_FADE_S - lat))


def implied_lat(offset: float, dgame: float) -> float:
    """offset_for's inverse: the latency a measured ``dgame`` at ``offset`` implies (fed to the next attempt's offset)."""
    return dgame / SLOW - WARP_FADE_S - offset


def first_target(leg: str, window=None) -> float:
    """The first attempt's dgame aim: FS_TARGET_G / FD_TARGET_G. [ff9mapkit netsync s154] NOT off FE's measured load window
    (kept in the notes): that is the load's WALL stall, which both 0.9 s timers count as a frame or two (THE CLOCK LAW) --
    aiming FS mid-window put its commit past 250's init on two of the s153 calibration's three attempts."""
    return FS_TARGET_G if leg == "FS" else FD_TARGET_G


def _hits(msgs, name: str, pred=None) -> list:
    rx = MINE[name]
    out = []
    for m in msgs:
        hit = rx.search(m)
        if hit and (pred is None or pred(hit)):
            out.append(m)
    return out


def s154_lines(msgs) -> list:
    return [m for m in msgs if any(MINE[k].search(m) for k in S154_LINES)]


def ghosts_on(msgs, field: int) -> int:
    return len(_hits(msgs, "ghost", lambda h: int(h.group(2)) == field))


def dress_lines_on(msgs, field: int) -> int:
    """[ff9mapkit netsync s154] 'self-dress: field N ...' lines for ``field``: one per load of the guest's own body there."""
    return len(_hits(msgs, "dress", lambda h: int(h.group(1)) == field))


def _rising(rows, start: int, end: int, field: int) -> list:
    """Indexes in (start, end) where fading rises while field.id == ``field`` (a scene change there)."""
    return [j for j in range(max(start + 1, 1), min(end, len(rows))) if rows[j]["fading"] and not rows[j - 1]["fading"]
            and rows[j]["field"] == field]


def judge_follow(rows, msgs, *, dest: int, origin: int, t_send: float) -> dict:
    """FE: an ordinary follow off ``origin`` to the host's ``dest``. {ok, why, window}: the pending rose, the guest shut down
    and landed on ``dest`` by ONE load (no fading rising edge on ``dest`` after the landing), ONE ghost line on ``dest``, no
    s154 line; ``window`` = that load's WALL stall on the conservative clock (a record: the races are not aimed off it).
    [ff9mapkit netsync s154] ``timer`` = the follow's 0.9 s timer as the bench's clock measures it with no load inside
    (rise -> fall, [lo, hi] game s: it must straddle 0.9 -- the clock's own calibration, noted, never judged here) and
    ``loads`` = the per-load dress counter's count (noted)."""
    out = {"ok": False, "why": "", "window": None, "timer": None, "loads": None}
    L, G = game_bounds(rows) if rows else ([], [])
    i_r = _first(rows, lambda r: r["t"] >= t_send and r["pending"] == dest) if rows else None
    i_s = _first(rows, lambda r: shut_evidence(r, origin), i_r or 0) if rows else None
    i_l = _first(rows, lambda r: landed(r, dest), (i_s or 0) + 1) if i_s is not None else None
    ghosts = ghosts_on(msgs, dest)
    news = s154_lines(msgs)
    second = _rising(rows, i_l, len(rows), dest) if i_l is not None else []
    if i_s is not None and i_l is not None:
        gs, gl = _br(G, i_s), _br(G, i_l)
        out["window"] = _r3(((gl[0] - gs[1]) + (gl[1] - gs[0])) / 2.0)
    if i_r is not None:
        i_f = _first(rows, lambda r: r["pending"] != dest, i_r + 1)
        if i_f is not None:
            out["timer"] = [_r3(L[i_f - 1] - L[i_r]), _r3(G[i_f] - G[max(0, i_r - 1)])]
        out["loads"] = dress_loads(rows, i_r)
    out["ok"] = i_r is not None and i_l is not None and not second and ghosts == 1 and not news
    out["why"] = (f"{len(rows or [])} sample(s); pending rose {'yes' if i_r is not None else 'NEVER'}; shutdown "
                  f"{'seen' if i_s is not None else 'UNSEEN'}; landed on {dest} {'yes' if i_l is not None else 'NO'}; load "
                  f"stall {out['window']} s (wall); second fade-outs on {dest}: {len(second)}; ghost lines on {dest}: {ghosts} "
                  f"(want 1); s154 lines: {news[:2] or 'none'}; the follow's timer rise -> fall {out['timer']} game s (want "
                  f"{FOLLOW_FADE_S:g} inside); dress loads {out['loads']}")
    return out


def judge_strand(rows, order: dict, *, dest: int, host_field: int) -> dict:
    """FS-a / FS-b off a REACHED strand race: {"a": (ok, why), "b": (ok, why)}."""
    i_l = order.get("i_l")
    if i_l is None:
        return {"a": (False, "no landing"), "b": (False, "no landing")}
    t_land = rows[i_l]["t"]
    after = [r for r in rows[i_l:] if r["t"] <= t_land + JUDGE_S]
    on_dest = [r for r in after if landed(r, dest)]
    join = _r3(on_dest[0]["t"] - t_land) if on_dest else None
    a_ok = bool(on_dest) and host_field == dest
    win = [r for r in after if r["t"] >= t_land + LATCH_FROM_S]
    stale = [r for r in win if r["field"] != dest and r["pending"] == -1 and r["warped_to"] == dest]
    elsewhere = sorted({str(r["overlay"]) for r in win if r["field"] != dest})
    b_ok = len(win) >= 10 and not stale
    last = after[-1] if after else {}
    return {"a": (a_ok, f"the guest on {dest} {join} s after its own landing on {rows[i_l]['field']} (window {JUDGE_S:g} s); "
                        f"the host on {host_field}; last sample field {last.get('field')} pending {last.get('pending')} "
                        f"warped_to {last.get('warped_to')} overlay {last.get('overlay')!r}"),
            "b": (b_ok, f"{len(stale)} of {len(win)} sample(s) from the landing + {LATCH_FROM_S:g} s read pending -1 with "
                        f"warped_to {dest} off {dest}; overlay off {dest}: {elsewhere or 'none'}")}


def judge_double(rows, order: dict, msgs, *, dest: int, init_grace: float = INIT_GRACE_G) -> dict:
    """FD-a / FD-b off a REACHED double-load race: {"a": (ok, why), "b": (ok, why)}. FD-b judges only the samples PAST the
    landing's init grace (game clock): the landed samples before the new field's first logic tick read the pending on both
    DLLs (THE INIT LAG), while s153's surviving pending reads it until the timer, past the grace by construction (FD is
    REACHED only with its commit past the landing + ``init_grace`` + TOL_G) -- and a re-rise after the fall still counts.
    [ff9mapkit netsync s154] FD-a counts the loads three ways and takes the most: the fading rises (a scene change's
    two-or-three-frame pulse, easily missed by the sampler), the per-load dress counter over the whole attempt (a counter:
    no gap misses it) and the 'self-dress: field N' lines -- s153's double load showed ONE ghost line (the ghost spawns
    after the second load, once the host is there), so the ghost count alone never saw it."""
    i_l = order.get("i_l")
    if i_l is None:
        return {"a": (False, "no landing"), "b": (False, "no landing")}
    t_land = rows[i_l]["t"]
    end = next((j for j in range(i_l, len(rows)) if rows[j]["t"] > t_land + JUDGE_S), len(rows))
    G = game_clock(rows)
    g_init = G[i_l] + init_grace
    second = _rising(rows, i_l, end, dest)
    ghosts = ghosts_on(msgs, dest)
    loads = dress_loads(rows, order.get("i_w") or 0)
    lines = dress_lines_on(msgs, dest)
    judged = [j for j in range(i_l, end) if G[j] > g_init]
    survive = [j for j in judged if landed(rows[j], dest) and rows[j]["pending"] == dest]
    early = [j for j in range(i_l, end) if G[j] <= g_init and landed(rows[j], dest) and rows[j]["pending"] == dest]
    n_loads = max(1 + len(second), loads or 0, lines)
    a_ok = n_loads == 1 and ghosts == 1
    b_ok = len(judged) >= 10 and not survive
    return {"a": (a_ok, f"loads of {dest}: {n_loads} (want 1) -- second fade-outs after the landing: {len(second)}"
                        + (f" (+{_r3(rows[second[0]]['t'] - t_land)} s)" if second else "")
                        + f", the per-load dress counter: {loads}, 'self-dress: field {dest}' lines: {lines}"
                        + f"; ghost lines on {dest}: {ghosts} (want 1)"),
            "b": (b_ok, f"{len(survive)} of {len(judged)} FieldHUD sample(s) on {dest} past the landing's init grace "
                        f"(+{init_grace:g} game s) read pending {dest}"
                        + (f" (first +{_r3(G[survive[0]] - G[i_l])} s)" if survive else "")
                        + f"; inside the grace {len(early)} landed sample(s) still read it (the init lag, not judged)")}


def cal_sets(done: dict) -> tuple:
    """(predicted, maybe, reached legs, unreached legs) off the recorded rows: a leg counts only when its *-pre is green;
    an unreached leg's rows (and its *-pre) are its own instrument reds, not judged."""
    predicted, maybe, got, missed = set(), set(), [], []
    for leg, cids in PREDICTED_S153.items():
        if done.get(f"{leg}-pre") is True:
            got.append(leg)
            predicted |= set(cids)
        else:
            missed.append(leg)
            maybe |= set(cids) | {f"{leg}-pre"}
    return predicted, maybe, got, missed


def cal_judgement(done: dict, predicted, maybe=(), s154=()) -> tuple:
    """Ledger.judge_calibration's verdict as a pure step (the CAL row itself excluded): every predicted row red, nothing
    else red but ``maybe``, at least one predicted row, and no s154 line seen."""
    if s154:
        return False, (f"this engine logged s154 follow lines ({list(s154)[:2]}) -- COOP_CALIBRATE=1 judges the s153 DLL")
    predicted, maybe = set(predicted), set(maybe)
    if not predicted:
        return False, "not reached: no leg reached its race order -- nothing was calibrated (re-run)"
    failed = {c for c, ok in done.items() if not ok and c != CAL_ID}
    missing = sorted(predicted - failed)
    extra = sorted(failed - predicted - maybe)
    return (not missing and not extra,
            f"predicted reds that stayed GREEN: {missing or 'none'}; unpredicted reds: {extra or 'none'}; maybe-reds that "
            f"fired: {sorted(failed & maybe) or 'none'}")


# ================================================================================================ the stream
def _reads(g, frame: int) -> list:
    """Every publish the Session's ring kept after ``frame``, with its write time (Session._reads_since); a driver
    without it gives the raw states (read time only)."""
    fn = getattr(g, "_reads_since", None)
    if fn is not None:
        return list(fn(frame))
    from harness.channel import State
    return [State(raw) for raw in (g.states_since(frame) or [])]


class _Stream:
    """The guest's publishes, every distinct frame the reads saw (pulled off the ring each pump: it holds ~5 s at
    stateevery 1), plus the host's field every 0.2 s."""

    def __init__(self, g, host=None):
        self.g, self.h = g, host
        self.rows: list = []
        self.host_rows: list = []
        self.last = g.state.frame
        self._hnext = 0.0

    def pump(self) -> None:
        self.g.state                                    # one read: into the Session's ring
        for st in _reads(self.g, self.last):
            if st.frame > self.last:
                self.rows.append(row_of(st))
                self.last = st.frame
        if self.h is not None and time.time() >= self._hnext:
            self._hnext = time.time() + 0.2
            try:
                hs = self.h.state
                self.host_rows.append({"t": time.time(), "field": hs.field_id, "ui": hs.ui_state})
            except HarnessError:
                pass

    def until(self, cond, timeout: float, poll: float = 0.003) -> bool:
        deadline = time.time() + timeout
        while True:
            self.pump()
            try:
                if cond():
                    return True
            except (TypeError, KeyError, AttributeError, IndexError, ValueError):
                pass
            if time.time() >= deadline:
                return False
            time.sleep(poll)

    def hold(self, seconds: float) -> None:
        self.until(lambda: False, seconds)

    def host_field(self) -> int:
        return self.host_rows[-1]["field"] if self.host_rows else -1


def _msgs(d, at: int) -> list:
    return [m for _t, _l, m in d.lines("guest")[at:]]


class _DuoG:
    """cb.Ledger's ``g``: each row recorded on the duo (and the guest's report), its id the catalog's."""

    def __init__(self, d):
        self.d = d

    def check(self, ok, what, detail=""):
        return self.d.check(bool(ok), str(what), str(detail), role="guest", cid=str(what).split(":", 1)[0])

    def note(self, msg):
        self.d.note(str(msg))


class _Ctx:
    def __init__(self):
        self.window: dict = {}
        self.notes: list = []


# ================================================================================================ the run
def run_duo(d) -> None:
    led = cb.Ledger(_DuoG(d), catalog(CALIBRATE), finals=(CAL_ID,) if CALIBRATE else (), width=1400)
    strict, d.strict = d.strict, False
    ctx = _Ctx()
    try:
        _run(d, led, ctx)
    except HarnessError as err:
        d.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    finally:
        _restore(d)
        try:
            d.note(f"logs archived: {d.archive('follow-race')}")
        except Exception as err:                            # noqa: BLE001 - teardown must not mask the verdicts
            d.note(f"archive failed: {err}")
        try:
            news = s154_lines(_msgs(d, 0))
            tests = _hits(_msgs(d, 0), "selftest")
        except Exception:                                   # noqa: BLE001
            news, tests = [], []
        d.note(f"s154 follow lines (corroboration only): {len(news)} -- {news[:4] or 'none'}; selftest {tests[-1:] or 'none'}")
        if CALIBRATE:
            led.close("not reached: the run ended before this check")
            predicted, maybe, got, missed = cal_sets(led.done)
            ok, why = cal_judgement(led.done, predicted, maybe, news)
            led.check(CAL_ID, ok, f"{why}; REACHED {got or 'none'}; NOT calibrated (unreached) {missed or 'none'}")
        led.close(final=True)
        d.strict = strict


def _restore(d) -> None:
    for step in ((lambda: d.guest.timescale(1.0)), (lambda: d.guest.state_every(2))):
        try:
            step()
        except Exception as err:                            # noqa: BLE001 - a dead game says so in its own rows
            d.note(f"restore: {str(err)[:160]}")


def _run(d, led, ctx) -> None:
    g, h = d.guest, d.host
    cb.provenance(g)
    try:
        regs_g, regs_h = g.registered_fields()[0], h.registered_fields()[0]
    except (HarnessError, OSError) as err:
        regs_g, regs_h = {}, {}
        d.note(f"registrations unreadable: {err}")
    _settle(d, HOME)                                        # past the pairing kick's fade-in (never judged)
    gst, hst = g.state, h.state
    ok = (AWAY in regs_g and AWAY in regs_h and gst.field_id == HOME and hst.field_id == HOME and gst.ui_state == "FieldHUD"
          and cb.path(gst, "netsync.session.mirroring") is True and cb.has(gst, "netsync.session.follow.pending"))
    led.check("FR-PRE", ok, f"guest {gst.ui_state} {gst.field_id} mirroring {cb.path(gst, 'netsync.session.mirroring')!r}; "
                            f"host {hst.ui_state} {hst.field_id}; {AWAY} registered guest {AWAY in regs_g} host "
                            f"{AWAY in regs_h}; follow published {cb.has(gst, 'netsync.session.follow.pending')}")
    if not ok:
        led.close("not reached: the pair is not ready (FR-PRE)")
        return
    try:
        g.state_every(1)
        ctx.window[AWAY] = _leg_follow(d, led, "FE1", AWAY)
        _settle(d, AWAY)
        ctx.window[HOME] = _leg_follow(d, led, "FE2", HOME)
        d.note(f"measured load stalls (wall, the conservative clock -- a record: the races are aimed in GAME time, THE "
               f"CLOCK LAW): {ctx.window}")
        _seat(d, HOME)
        _leg_race(d, led, ctx, "FS")
        _seat(d, HOME)
        _leg_race(d, led, ctx, "FD")
    finally:
        _restore(d)


def _settle(d, field: int) -> None:
    """Both on ``field`` and the guest free-standing with no follow in flight (a short wait, never judged)."""
    def ok():
        s = d.guest.state
        return (s.field_id == field and s.ui_state == "FieldHUD" and s.control and not s.fading
                and cb.path(s, "netsync.session.follow.pending", -1) == -1 and d.host.state.field_id == field)
    deadline = time.time() + SEAT_S
    while time.time() < deadline and not ok():
        time.sleep(0.2)
    time.sleep(1.5)


def _seat(d, field: int) -> None:
    """Re-seat the pair on ``field``: the host warps there (an s153 strand clears its latch by co-location) and the guest
    follows; a guest left elsewhere after SEAT_S is warped there itself (noted)."""
    g, h = d.guest, d.host
    try:
        if h.state.field_id != field:
            h.warp(field)
    except HarnessError as err:
        d.note(f"re-seat: the host's warp to {field}: {str(err)[:200]}")
    _settle(d, field)
    try:
        if g.state.field_id != field:
            d.note(f"re-seat: the guest is on {g.state.field_id}, not {field}, after {SEAT_S:g} s -- warping it there")
            g.warp(field)
            _settle(d, field)
    except HarnessError as err:
        d.note(f"re-seat: the guest's warp to {field}: {str(err)[:200]}")


def _ready(d) -> tuple:
    g, h = d.guest, d.host
    s, hs = g.state, h.state
    ok = (s.field_id == HOME and hs.field_id == HOME and s.ui_state == "FieldHUD" and s.control and not s.fading
          and cb.path(s, "netsync.session.follow.pending", -1) == -1 and cb.path(s, "netsync.session.mirroring") is True)
    return ok, (f"guest {s.ui_state} {s.field_id} control {s.control} pending "
                f"{cb.path(s, 'netsync.session.follow.pending')} mirroring {cb.path(s, 'netsync.session.mirroring')!r}; "
                f"host {hs.field_id}")


def _follow_landed(rows, dest, origin, t_send) -> bool:
    i_s = _first(rows, lambda r: r["t"] >= t_send and shut_evidence(r, origin))
    return i_s is not None and _first(rows, lambda r: landed(r, dest), i_s + 1) is not None


def _save_rows(d, name: str, rows) -> None:
    """[ff9mapkit netsync s154] One leg's stream beside the guest's report (follow-<name>.jsonl, the rows the judges read):
    the Session's ring keeps only the last 300 samples, so without this a red race leaves nothing to diagnose it by."""
    try:
        import json
        path = Path(d.guest.run_dir) / f"follow-{name}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for r in rows or []:
                fh.write(json.dumps(r, default=str) + "\n")
    except Exception as err:                                # noqa: BLE001 - a record, never a verdict
        d.note(f"could not save the {name} stream: {str(err)[:160]}")


def _leg_follow(d, led, cid: str, dest: int):
    g, h = d.guest, d.host
    origin = g.state.field_id
    s = _Stream(g, h)
    at = len(d.lines("guest"))
    s.hold(0.3)
    t_send = time.time()
    try:
        h.send(f"warp {dest} -1 -1", wait=False)
    except HarnessError as err:
        led.check(cid, False, f"not reached: the host's warp to {dest} was refused ({str(err)[:200]})")
        return None
    s.until(lambda: _follow_landed(s.rows, dest, origin, t_send), FOLLOW_S)
    s.hold(SETTLE_S)
    _save_rows(d, cid, s.rows)
    res = judge_follow(s.rows, _msgs(d, at), dest=dest, origin=origin, t_send=t_send)
    hf = s.host_field()
    led.check(cid, res["ok"] and hf == dest, res["why"] + f"; the host on {hf}")
    return res["window"]


def _attempt(d, leg: str, offset: float) -> dict:
    """One race: the two sends ``offset`` apart (the host's minus the guest's own; negative = the host first) with the
    guest at timescale 0.1, the follow's start, the switch back to 1, the guest's own landing, then the judge window --
    every guest publish on the stream."""
    g, h = d.guest, d.host
    own_target = HOME if leg == "FS" else AWAY
    out = {"rows": [], "msgs": [], "t_own": None, "host_field": -1, "why": ""}
    at = len(d.lines("guest"))
    s = _Stream(g, h)
    gap = abs(float(offset))
    try:
        g.timescale(SLOW)
        s.hold(0.25)
        if offset < 0:                                      # the host first, the guest's own warp -offset later
            h.send(f"warp {AWAY} -1 -1", wait=False)
            t_h = time.time()
            s.until(lambda: time.time() >= t_h + gap, gap + 1.0)
            out["t_own"] = time.time()
            g.send(f"warp {own_target} -1 -1", wait=False)
        else:                                               # the guest's own warp first, the host offset later
            out["t_own"] = time.time()
            g.send(f"warp {own_target} -1 -1", wait=False)
            t_g = out["t_own"]
            s.until(lambda: time.time() >= t_g + gap, gap + 1.0)
            h.send(f"warp {AWAY} -1 -1", wait=False)
        rose = s.until(lambda: bool(s.rows) and s.rows[-1]["pending"] == AWAY, RISE_S)
        g.send("timescale 1", wait=False)                   # both timers keep their gap: they spend the same deltaTime
        if not rose:
            out["why"] = f"the follow never started within {RISE_S:g} s"
        origin = HOME
        t_own = out["t_own"]
        seen = {"n": -1, "next": 0.0}

        def own_landed():                                   # [ff9mapkit netsync s154] the judges' own edges (a reload's
            if len(s.rows) == seen["n"] or time.time() < seen["next"]:   # shutdown may be only its load's stall),
                return False                                # re-read at most every 50 ms: never a drag on the sampling
            seen["n"], seen["next"] = len(s.rows), time.time() + 0.05
            e = own_edges(s.rows, origin=origin, own_target=own_target, t_own_send=t_own)
            return e["i_s"] is not None and e["landed_on"] is not None
        s.until(own_landed, LAND_S)
        s.hold(JUDGE_S + 0.5)
    except HarnessError as err:
        out["why"] = f"the race raised: {str(err)[:200]}"
    finally:
        try:
            g.timescale(1.0)
        except HarnessError as err:
            out["why"] += f"; timescale 1 refused ({str(err)[:120]})"
    out["rows"], out["msgs"], out["host_field"] = s.rows, _msgs(d, at), s.host_field()
    try:
        out["debug_status"] = g.state.debug_status
    except HarnessError:
        out["debug_status"] = None
    return out


def _leg_race(d, led, ctx, leg: str) -> None:
    own_target = HOME if leg == "FS" else AWAY
    target = first_target(leg)                              # [ff9mapkit netsync s154] never off FE's wall stall (ctx.window)
    lat = LAT0
    offset = offset_for(target, lat)
    last = "never attempted"
    for attempt in range(1, TRIES + 1):
        if attempt > 1:
            _seat(d, HOME)
        ok, why = _ready(d)
        if not ok:
            last = f"attempt {attempt}: the pair was not ready ({why})"
            d.note(f"{leg} {last}")
            continue
        res = _attempt(d, leg, offset)
        _save_rows(d, f"{leg}-{attempt}", res["rows"])
        order = race_order(res["rows"], dest=AWAY, own_target=own_target, t_own_send=res["t_own"] or 0.0)
        line = (f"{leg} attempt {attempt}: send offset {offset:+.3f} s (aim dgame {target:.3f}) -> "
                f"{order['why'] or order['order']}" + (f"; {res['why']}" if res["why"] else "")
                + (f"; debug_status {res.get('debug_status')!r}" if order["order"] == "no-own-warp" else ""))
        d.note(line)
        if reached(leg, order):
            led.check(f"{leg}-pre", True, line + f"; s154 lines: {s154_lines(res['msgs'])[:2] or 'none'}")
            if leg == "FS":
                j = judge_strand(res["rows"], order, dest=AWAY, host_field=res["host_field"])
            else:
                j = judge_double(res["rows"], order, res["msgs"], dest=AWAY)
            led.check(f"{leg}-a", *j["a"])
            led.check(f"{leg}-b", *j["b"])
            return
        last = line
        if order.get("dgame") is not None:
            lat = implied_lat(offset, float(order["dgame"]))
            target = next_dgame(leg, order, target)
            offset = offset_for(target, lat)
    led.check(f"{leg}-pre", False, f"not reached after {TRIES} attempt(s): {last}"[:1400])
    led.unreached([f"{leg}-a", f"{leg}-b"], f"the {leg} race never reached its order ({REACH[leg]}) -- see {leg}-pre")
