"""In-game experiment rank 10 -- THE IN-GAME COST BUDGET of refined walkable terrain (capacity CAP-10/CAP-12).

DEPLOYS into the scratch folder FF9CustomMap-lab ONLY, and SWAPS ONE FILE there between world loads (owner-approved
lab protocol of sessions 4-7; the orchestrator creates the folder first in FolderNames and removes it after):
    <game>/FF9CustomMap-lab/FF9_Data/WorldMap/Disc1/0_1/r1/Block[21][1] Terrain.ff9mesh
The four arms come from cost_build.py ($COST_SCRATCH/arms): the SAME flat 64u plane on the isolated ocean cell
(21,1) at x1 / x4 / x16 / x64 triangles (338 / 1,352 / 5,408 / 21,632), area 14 / topograph 0 (an encounter hole),
each at its own height TAG (6.000 / 6.125 / 6.250 / 6.375) so the walked height names the arm the engine loaded.
The swap happens only while the game stands on field 6603 (the file is read only inside the world's LoadBlocks
frame, ff9.cs:3703 -> WMWorld.RegisterBlockComponent -> WorldMeshOverride.TryLoad, which re-opens it every load).

ONE LAUNCH, A/B ALTERNATION. World loads W0..Wn follow $COST_SCHEDULE; every test arm is BRACKETED by x1 loads
(x1, x64, x1, x16, x1, x4, x1, ...), each reload a field round trip (world_warp 6603 -> swap -> walk out).
W0 (the launch's first, cold world entry) is a warm-up: it calibrates the circle and is never scored.
Per load, on the cell (all at the cell centre C = (1376.37, -96.61), all on the plane):
    probe    world_probe("up") -> the heading h; teleport to S = C - r u(h + s 90deg) so the circle is centred on C
    idle_pre 4 s standing (ts 1)        -- the WITHIN-LOAD CONTROL: every probe a cache hit (cost_predict: 6 tests
                                           a tick in every arm), so idle pays the regime, the render, everything but
                                           the scan
    walk     "up" + L1 held: a circle of radius 8.91u (0.4375u a tick, 2.8125deg a tick), 600 ticks after a 1.5 s
             lead-in -- the walker's 2 cached probes and the camera's 4 fuzzy sky probes all on the refined cell
    idle_post 3 s standing
    [amplified, $COST_AMP = 4; 0 disables] re-probe, teleport, timescale 4: idle4 2 s, walk4 600 ticks, timescale 1
                                        -- the POSITIVE CONTROL: x4 the ticks a frame, so x64 must show
A background poller (cost_lib.Poller, ~6 ms) records every published frame's mtime; stateevery 1 on the world.

REGISTERED PREDICTIONS (cost_predict.py -> out/cost_predict.json; c = seconds per triangle test, central 0.25 us):
  tests a tick (walker + camera):  x1 389 / x4 2,435 (6.3x) / x16 12,808 (32.9x) / x64 55,552 (142.7x); idle 6 in all
  P1 binding    every load's walked y = its arm tag +-0.03; one lab Block[21][1] Terrain log line per world load
  P2 circle     fitted radius 8.91 +-0.6u, centre within 1.5u of C; y constant; WorldHUD throughout (no battle)
  P3 clock      every walk at ts 1 runs 28 +-1.5 ticks a second -- in EVERY arm (x64 at 0.25 us is 0.39 s of CPU a
                second: the frame rate pays, the world clock does not)
  P4 idle       refinement is invisible at idle: |D_idle| below the A-A floor for every arm (GPU cost of 21k tris ~0)
  P5 x4         FREE (0.6 ms a tick-frame)
  P6 x16        60-fps regime: COST, D(walk-idle) in [-10, -2] fps (3.2 ms a tick-frame); a FREE verdict bounds
                c < ~0.12 us.  31-fps regime: FREE.
  P7 x64        COST in either regime: 60-fps regime D in [-30, -8] fps (walk ~30-45 fps); 31-fps regime [-12, -3]
  P8 amplified  x64 at ts 4 cannot hold its clock: walk4 < 15 fps and < 80 ticks/s (x1 at ts 4: ~112 ticks/s);
                x16 at ts 4 COST. (P8 is the POSITIVE CONTROL: if x64 does not show here, FREE verdicts prove nothing)
  P9 load       the LoadBlocks frame (the gap before the first WorldHUD frame, ~1.2-1.5 s on this install) grows by
                +20..+120 ms at x64 (mean of its occurrences <= 120 ms -- likely BELOW-FLOOR: archived same-launch
                loads differ by ~75 ms); x16 and x4 never LOAD-COST
  Parked actors: NOT RUN (no harness verb can make a non-player world actor present on the cell; see cost_PLAN.md).

DECISION RULE: cost_lib.decide / decide_load (bracketed differences, regime-matched, A-A noise floor; see the PLAN).

Env: COST_SCRATCH, COST_LAB, COST_SCHEDULE (full|short|"1,1,64,1,..."), COST_TICKS (600), COST_AMP (4),
     COST_AMP_TICKS (600), COST_IDLE_S (4).
Rerun:  py tools/play.py studies/terrain-malleability/ingame/cost_session.py --label cost-session
Score:  py studies/terrain-malleability/ingame/cost_post.py <.harness-runs/... run dir>
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cost_lib as L                                               # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
SCRATCH = Path(os.environ.get("COST_SCRATCH", r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                                              r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\cost"))
ARMS_DIR = SCRATCH / "arms"
LAB_NAME = "FF9CustomMap-lab"
LAB = Path(os.environ.get("COST_LAB", str(GAME / LAB_NAME)))
DRYRUN = os.environ.get("COST_DRYRUN") == "1"

SCHEDULES = {
    "full": [1, 1, 64, 1, 16, 1, 4, 1, 64, 1, 16, 1, 4, 1, 64, 1, 16, 1],
    "short": [1, 1, 64, 1, 16, 1, 64, 1, 16, 1, 4, 1, 4, 1],
}
_sch = os.environ.get("COST_SCHEDULE", "full")
SCHEDULE = SCHEDULES[_sch] if _sch in SCHEDULES else [int(a) for a in _sch.split(",")]
TICKS = int(os.environ.get("COST_TICKS", "600"))
AMP = float(os.environ.get("COST_AMP", "4"))
AMP_TICKS = int(os.environ.get("COST_AMP_TICKS", "600"))
IDLE_S = float(os.environ.get("COST_IDLE_S", "4"))
TPS = 28.0                                   # Memoria.ini [Graphics] WorldTPS (read at start; this is the default)

LANDING_FIELD = 6603
EXIT_AT = (400.0, -1400.0)
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
CENTRE = (1376.37, -96.61)                   # block (21,1) centre, off the 0.615u x64 lattice
SETTLE_S = 3.0                               # camera ease after a teleport (RESULTS: > 90 frames from high view)
LEAD_S = 1.5                                 # circle lead-in, discarded (the camera's eye height re-converges)
DRIFT_MAX = 22.0                             # walker farther than this from C = the circle is not a circle: stop
HOLD_FRAMES = 20000
OVERRIDE_LINE = re.compile(r"\[WorldMeshOverride\] loaded 'WorldMap/Disc1/0_1/r1/Block\[21\]\[1\] Terrain' from (.+)")

_RECORD: dict = {"schedule": SCHEDULE, "ticks": TICKS, "amp": AMP, "amp_ticks": AMP_TICKS, "loads": [], "notes": []}


# ------------------------------------------------------------------------------------------------ the lab and swap
def manifest() -> dict:
    return json.loads((ARMS_DIR / "cost_manifest.json").read_text(encoding="utf-8"))


def guard_lab() -> Path:
    """Refuse unless the lab is set up exactly as the orchestrator promised: the folder exists and is FIRST in
    Memoria.ini FolderNames (read-only parse). Returns the swap target, resolved INSIDE the lab folder."""
    man = manifest()
    target = (LAB / man["rel_path"]).resolve()
    if LAB.resolve() not in target.parents:
        raise RuntimeError(f"swap target {target} is not inside {LAB}")
    if not LAB.is_dir():
        raise RuntimeError(f"{LAB} does not exist -- the orchestrator creates the lab folder before the launch")
    if not DRYRUN:
        ini = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
        m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', ini, re.M)
        folders = re.findall(r'"([^"]*)"', m.group(1)) if m else []
        if not folders or folders[0] != LAB_NAME:
            raise RuntimeError(f"{LAB_NAME} must be FIRST in Memoria.ini FolderNames (read: {folders})")
        g = re.search(r'^\s*WorldTPS\s*=\s*(\d+)', ini, re.M)
        if g:
            global TPS
            TPS = float(g.group(1))
    for arm in {str(a) for a in SCHEDULE}:
        row = man["arms"][arm]
        data = (ARMS_DIR / row["file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise RuntimeError(f"arm x{arm} on disk does not match the manifest -- rerun cost_build.py")
    return target


def swap(target: Path, arm: int) -> dict:
    """Atomically put arm `arm` in place (only ever called with the game standing on a FIELD), and read it back."""
    row = manifest()["arms"][str(arm)]
    data = (ARMS_DIR / row["file"]).read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, target)
    back = hashlib.sha256(target.read_bytes()).hexdigest()
    if back != row["sha256"]:
        raise RuntimeError(f"swap to x{arm}: the file read back differs from the manifest")
    return {"arm": arm, "sha256": back[:16], "bytes": len(data), "tag": row["height_tag"], "t": time.time()}


# ------------------------------------------------------------------------------------------------ reaching the world
def _log_tail_mark(g) -> tuple[Path, int] | None:
    for _name, (path, off) in (g.log_mark() or {}).items():
        if Path(path).name.lower() == "memoria.log":
            return Path(path), int(off)
    return None


def _override_lines(mark) -> list[str]:
    if mark is None:
        return []
    path, off = mark
    try:
        with open(path, "rb") as fh:
            fh.seek(off)
            text = fh.read().decode("utf-8", "replace")
    except OSError:
        return []
    return [m.group(1).strip() for m in OVERRIDE_LINE.finditer(text)]


def walk_out(g) -> None:
    g.wait_frames(45)
    g.calibrate_axes(hazards=[DOOR])
    g.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    g.world_settle()


def reach_world(g, target, arm, rec) -> None:
    g.newgame()
    g.warp(LANDING_FIELD)
    rec["swap"] = swap(target, arm)
    rec["t_walkout"] = time.time()
    rec["_mark"] = _log_tail_mark(g)
    walk_out(g)


def reload_world(g, target, arm, rec) -> None:
    g.state_every(2)
    g.world_warp(LANDING_FIELD)
    rec["swap"] = swap(target, arm)
    rec["t_walkout"] = time.time()
    rec["_mark"] = _log_tail_mark(g)
    walk_out(g)


HOOKS = {"reach": reach_world, "reload": reload_world}


# ------------------------------------------------------------------------------------------------ on the cell
def _u(deg: float) -> tuple[float, float]:
    return math.cos(math.radians(deg)), math.sin(math.radians(deg))


def heading_at_centre(g) -> dict:
    g.teleport(*CENTRE)
    g.world_settle()
    p = g.world_probe("up", home=CENTRE)
    if p.get("left_world") or p.get("heading") is None:
        raise RuntimeError(f"the heading probe on the plane failed: {p}")
    return {"heading": p["heading"], "speed": p.get("speed"), "unsettled": bool(p.get("unsettled"))}


def circle_start(h: float, cal: dict) -> tuple[float, float]:
    ux, uz = _u(h + cal["sign"] * 90.0)
    return CENTRE[0] - cal["radius"] * ux, CENTRE[1] - cal["radius"] * uz


def idle(g, seconds: float) -> tuple[float, float]:
    t0 = time.time()
    time.sleep(seconds)
    return t0, time.time()


def circle(g, P: L.Poller, *, ticks: int, ts: float, lead_s: float) -> dict:
    """Hold up + L1 together; measure `ticks` ticks of path after the lead-in. Returns the window and how it ended."""
    expect = ticks / (TPS * ts)
    cap = 2.5 * expect + 5.0
    g.send(f"hold up {HOLD_FRAMES}", f"hold leftbumper {HOLD_FRAMES}")
    end = "ticks"
    try:
        time.sleep(max(0.5, lead_s / ts))           # about the same number of TICKS of lead-in at any timescale
        t0 = time.time()
        path, last = 0.0, None
        while True:
            time.sleep(0.05)
            r = P.latest()
            if r is None:
                continue
            if r["ui"] != "WorldHUD":
                end = f"left_world:{r['ui']}"
                break
            if r["x"] is not None:
                if last is not None:
                    path += math.hypot(r["x"] - last[0], r["z"] - last[1])
                last = (r["x"], r["z"])
                if math.hypot(r["x"] - CENTRE[0], r["z"] - CENTRE[1]) > DRIFT_MAX:
                    end = "drift"
                    break
            if path >= ticks * L.STEP:
                break
            if time.time() - t0 > cap:
                end = "cap"
                break
        t1 = time.time()
    finally:
        g.send("release up", "release leftbumper")
    return {"t": [t0, t1], "end": end, "path_live": round(path, 2), "expect_s": round(expect, 2)}


def calibrate_turn(g, P: L.Poller) -> dict:
    """W0 only: one circle from the centre -> the turn SIGN (which side of the heading the centre lies) and the
    measured radius (registered 8.91 +-0.6)."""
    h = heading_at_centre(g)
    g.teleport(*CENTRE)
    g.world_settle()
    c = circle(g, P, ticks=160, ts=1.0, lead_s=0.5)
    rows = P.window(*c["t"])
    fit = L.circle_fit([(r["x"], r["z"]) for r in rows if r["x"] is not None])
    if fit is None:
        raise RuntimeError(f"calibration circle: no fit ({len(rows)} rows, end {c['end']})")
    ux, uz = _u(h["heading"])
    dx, dz = fit[0] - CENTRE[0], fit[1] - CENTRE[1]
    sign = 1 if ux * dz - uz * dx > 0 else -1
    out = {"heading": h["heading"], "fit": [round(v, 3) for v in fit], "sign": sign, "radius": round(fit[2], 3),
           "end": c["end"]}
    g.world_settle()
    return out


def measure_cell(g, P: L.Poller, rec: dict, cal: dict, tags: dict) -> None:
    W = rec["windows"] = {}
    marks = rec["marks"] = {}
    h = heading_at_centre(g)
    rec["probe"] = h
    S = circle_start(h["heading"], cal)
    rec["S"] = [round(S[0], 3), round(S[1], 3)]
    g.teleport(*S)
    g.world_settle()
    time.sleep(SETTLE_S)
    marks["idle_pre"] = idle(g, IDLE_S)
    c = circle(g, P, ticks=TICKS, ts=1.0, lead_s=LEAD_S)
    marks["walk"] = c["t"]
    rec["walk_end"] = c["end"]
    g.world_settle()
    time.sleep(1.0)
    marks["idle_post"] = idle(g, max(2.0, IDLE_S - 1.0))
    if AMP > 0 and c["end"] == "ticks":
        h4 = heading_at_centre(g)
        S4 = circle_start(h4["heading"], cal)
        g.teleport(*S4)
        g.world_settle()
        g.timescale(AMP)
        try:
            time.sleep(SETTLE_S / AMP + 0.5)
            marks["idle4"] = idle(g, 2.0)
            c4 = circle(g, P, ticks=AMP_TICKS, ts=AMP, lead_s=LEAD_S)
            marks["walk4"] = c4["t"]
            rec["walk4_end"] = c4["end"]
        finally:
            g.timescale(1.0)
    score_windows(P, rec, tags)


def score_windows(P: L.Poller, rec: dict, tags: dict) -> None:
    """Window metrics from the poller rows (cost_post.py redoes exactly this from the dumped samples)."""
    marks, W = rec["marks"], rec.setdefault("windows", {})
    for k in ("idle_pre", "idle_post", "idle4"):
        if k in marks:
            W[k] = L.window_metrics(P.window(*marks[k]), centre=CENTRE)
    for walk, idle_k in (("walk", "idle_pre"), ("walk4", "idle4")):
        if walk in marks:
            med = (W.get(idle_k) or {}).get("p50_ms")
            if med:
                W[idle_k] = L.window_metrics(P.window(*marks[idle_k]), centre=CENTRE, idle_median_ms=med)
                if idle_k == "idle_pre" and "idle_post" in marks:
                    W["idle_post"] = L.window_metrics(P.window(*marks["idle_post"]), centre=CENTRE, idle_median_ms=med)
            W[walk] = L.window_metrics(P.window(*marks[walk]), centre=CENTRE, idle_median_ms=med)
    y = (W.get("walk") or {}).get("y_med")
    rec["arm_y"] = y
    rec["arm_ok"] = y is not None and abs(y - tags[str(rec["arm"])]) <= 0.03
    if rec.get("t_walkout") and rec.get("t_arrived"):
        rec["entry"] = L.entry_hitch(P.window(rec["t_walkout"], rec["t_arrived"]))


# ------------------------------------------------------------------------------------------------ the run
def run(g):
    target = guard_lab()
    tags = {k: v["height_tag"] for k, v in manifest()["arms"].items()}
    g.note(f"cost_session: refinement cost budget on (21,1); schedule {SCHEDULE}; ticks {TICKS}; amp {AMP}")
    P = L.Poller(g.channel.dir / "state.json").start()
    cal = None
    try:
        for i, arm in enumerate(SCHEDULE):
            role = "warm" if i == 0 else ("ref" if arm == 1 else "test")
            rec = {"load": i, "arm": arm, "role": role}
            _RECORD["loads"].append(rec)
            try:
                (HOOKS["reach"] if i == 0 else HOOKS["reload"])(g, target, arm, rec)
                rec["t_arrived"] = time.time() + 0.5
                g.state_every(1)
                time.sleep(0.5)
                rec["log"] = _override_lines(rec.pop("_mark", None))
                if cal is None:
                    cal = _RECORD["calibration"] = calibrate_turn(g, P)
                    g.note(f"cost_session: circle sign {cal['sign']} radius {cal['radius']}")
                measure_cell(g, P, rec, cal, tags)
            except Exception as err:                               # noqa: BLE001 -- recorded, then scored as-is
                rec.pop("_mark", None)
                rec["error"] = f"{type(err).__name__}: {err}"
                _RECORD["notes"].append(f"W{i} x{arm}: {rec['error']}")
                print(f"[cost] W{i} x{arm} FAILED: {rec['error']}")
                break
            w = rec["windows"]
            print(f"[cost] W{i:<2} x{arm:<2} {role:<4} y {rec.get('arm_y')} ok {rec.get('arm_ok')} | idle "
                  f"{(w.get('idle_pre') or {}).get('fps')} walk {(w.get('walk') or {}).get('fps')} "
                  f"({(w.get('walk') or {}).get('tick_rate')} t/s) | idle4 {(w.get('idle4') or {}).get('fps')} walk4 "
                  f"{(w.get('walk4') or {}).get('fps')} ({(w.get('walk4') or {}).get('tick_rate')} t/s) | blocks "
                  f"{(rec.get('entry') or {}).get('blocks_ms')} ms | end {rec.get('walk_end')}/{rec.get('walk4_end')}")
            _write(g, P)
            if rec.get("walk_end", "").startswith("left_world") or rec.get("walk4_end", "").startswith("left_world"):
                _RECORD["notes"].append(f"W{i}: left the world mid-walk -- stopping")
                break
        else:
            _RECORD["completed"] = True
    finally:
        try:
            g.state_every(2)
        except Exception:                                          # noqa: BLE001
            pass
        P.stop()
        _write(g, P)
    _checks(g, cal, tags)


def _write(g, P) -> None:
    try:
        rd = Path(g.run_dir)
        (rd / "cost_session.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
        P.dump(rd / "cost_samples.jsonl")
    except Exception as err:                                       # noqa: BLE001
        print(f"[cost] could not write the record: {err}")


def _checks(g, cal, tags) -> None:
    loads = [ld for ld in _RECORD["loads"] if ld.get("windows")]
    scored = [ld for ld in loads if ld["role"] != "warm"]
    lab_lines = [ld.get("log") or [] for ld in scored]
    g.check(bool(scored) and all(ld.get("arm_ok") for ld in scored),
            "P1 binding: every load's walked y equals its arm tag (+-0.03)",
            "; ".join(f"W{ld['load']} x{ld['arm']} y {ld.get('arm_y')}" for ld in scored))
    g.check(bool(scored) and all(len(x) == 1 and LAB_NAME in x[0] for x in lab_lines),
            "P1 log: exactly one FF9CustomMap-lab Block[21][1] Terrain load line per world load",
            "; ".join(str(len(x)) for x in lab_lines))
    circ = [(ld["load"], (ld["windows"].get("walk") or {}).get("circle")) for ld in scored]
    ok_c = all(c and abs(c["r"] - L.RADIUS) <= 0.6 and math.hypot(c["cx"] - CENTRE[0], c["cz"] - CENTRE[1]) <= 1.5
               for _i, c in circ)
    g.check(bool(circ) and ok_c, "P2 circle: radius 8.91 +-0.6, centre within 1.5u of C, every load",
            f"calibration {cal}; " + "; ".join(f"W{i} {c}" for i, c in circ))
    tr = [((ld["windows"].get("walk") or {}).get("tick_rate"), ld["arm"]) for ld in scored]
    g.check(bool(tr) and all(t is not None and abs(t - TPS) <= 1.5 for t, _a in tr),
            "P3 clock: every ts-1 walk runs 28 +-1.5 ticks a second, in every arm",
            "; ".join(f"x{a} {t}" for t, a in tr))
    S = L.score(_RECORD["loads"])
    _RECORD["score"] = S
    idle_dec = S["idle_render"]
    g.check(bool(idle_dec["verdicts"]) and all(not v["verdict"].startswith("COST")
                                               for v in idle_dec["verdicts"].values()),
            "P4 idle: no arm lowers the idle frame rate beyond the A-A floor (render cost of the extra tris ~0)",
            json.dumps({k: (v["verdict"], v["d"]) for k, v in idle_dec["verdicts"].items()}))
    pc = S["positive_control"]
    g.check(bool(pc["fired"]), f"P8 positive control: x{pc['arm']} at timescale {AMP:g} costs frames (COST)",
            f"{pc['detail']}; amplified {json.dumps({k: v['verdict'] for k, v in S['amplified']['verdicts'].items()})}")
    v = {k: x["verdict"] for k, x in S["walk"]["verdicts"].items()}
    regimes = [r for r in S["walk"]["regimes"] if r]
    regime = max(set(regimes), key=regimes.count) if regimes else "?"
    g.check(v.get("4", "").startswith("FREE"), "P5 x4: FREE", f"{S['walk']['verdicts'].get('4')}")
    want16 = "COST" if regime == "60" else "FREE"
    g.check(v.get("16", "").startswith(want16), f"P6 x16: {want16} in the observed {regime}-fps regime",
            f"{S['walk']['verdicts'].get('16')}; threshold {S['walk']['threshold']} fps")
    g.check(v.get("64") == "COST", "P7 x64: COST", f"{S['walk']['verdicts'].get('64')}")
    lv = S["load"]["verdicts"]
    d64 = lv.get("64", {}).get("d_ms") or []
    g.check(len(d64) >= 2 and sum(d64) / len(d64) <= 120.0
            and not any(lv.get(a, {}).get("verdict", "").startswith("LOAD-COST") for a in ("4", "16")),
            "P9 load: x64 adds at most 120 ms to the LoadBlocks frame (mean of its occurrences); "
            "x16 and x4 never LOAD-COST", json.dumps(S["load"]))
    g.check(_RECORD.get("completed", False), "the schedule completed (every planned world load measured)",
            "; ".join(_RECORD["notes"]) or f"{len(scored) + 1} of {len(SCHEDULE)} loads")
    try:
        (Path(g.run_dir) / "cost_session.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception:                                              # noqa: BLE001
        pass
