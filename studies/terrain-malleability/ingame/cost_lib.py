"""Shared instruments for experiment rank 10 (THE IN-GAME COST BUDGET): the state POLLER, the per-window METRICS, the
circle fit, and the pure DECISION RULE. Imported by cost_session.py (in game), cost_post.py (re-score a run dir) and
cost_dryrun.py (synthetic tables + FakeGame). Nothing here touches the game, a mod folder or the memory store.

THE CLOCK. The engine publishes state.json every `stateevery` frames, written IN PLACE (memory project-ff9-test-harness:
THE CHANNEL MUST NOT USE File.Replace); it carries `frame` = Time.frameCount (HarnessAgent.cs:1509) and no realtime
clock, so a frame's time is the file's mtime -- the earliest mtime any read saw for that frame (a later read can only
stamp it LATER: tickrate.TickClock.observe). The poller here reads the file directly on its own thread at ~6 ms and
does NOT feed Channel.observer (TickClock is not thread-safe; the field verbs plan by it).

WHY SPAN FPS. Per-pair rates from 2-frame mtime pairs are noisy (archived world rings: p10 30 / p90 72 around a
median ~55); a window's span rate (frames / seconds between its first and last publish) carries only the two end
stamps' jitter, ~ms over ~20 s. Frame-duration quantiles come from consecutive frames (stateevery 1 on the world).
"""
from __future__ import annotations

import json
import math
import statistics
import threading
import time
from pathlib import Path

STEP = 0.4375                 # on-foot step a world tick (flat ground)
OMEGA_DEG = 2.8125            # PsxRot(32): L1/R1 camera turn a tick (ff9.cs:6140/6146)
RADIUS = STEP / math.radians(OMEGA_DEG)
LONG_REL = 1.5                # a frame is LONG when it lasts > 1.5x the load's idle median frame
T_MIN_FPS = 1.5               # the decision threshold never drops below this (fps)
T_MIN_FPS_AMP = 3.0           # ... nor this in the amplified (timescale) phase
T_MIN_LOAD_MS = 40.0          # ... nor this for the world-entry hitch
REGIME_SPLIT = 0.15           # idle fps differing by more than this fraction = a different regime


# --------------------------------------------------------------------------------------------------------- poller
class Poller:
    """Reads <game>/x64/ff9harness/state.json on a daemon thread; keeps one row per distinct frame (earliest mtime).
    Row = dict(t, frame, ui, scene, fading, field, x, z, y, ts)."""

    def __init__(self, path: Path, period: float = 0.006):
        self.path = Path(path)
        self.period = period
        self.rows: dict[int, dict] = {}
        self._latest: dict | None = None             # O(1) latest(): the circle loop asks every 50 ms
        self.reads = self.misses = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "Poller":
        self._thread = threading.Thread(target=self._loop, name="cost-poller", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                body = self.path.read_text(encoding="utf-8-sig")
                mt = self.path.stat().st_mtime
                d = json.loads(body)
            except (OSError, ValueError):
                self.misses += 1
                time.sleep(self.period)
                continue
            self.reads += 1
            f = int(d.get("frame", -1))
            if f >= 0:
                ui = d.get("ui_state")
                w = d.get("world") or {}
                p = d.get("player") or {}
                py = p.get("y")
                row = {"t": mt, "frame": f, "ui": ui, "scene": d.get("scene"), "fading": bool(d.get("fading")),
                       "field": (d.get("field") or {}).get("id"), "x": w.get("x"), "z": w.get("z"),
                       "y": (py / 256.0) if (ui == "WorldHUD" and isinstance(py, (int, float))) else None,
                       "ts": d.get("timescale")}
                with self._lock:
                    old = self.rows.get(f)
                    if old is None or mt < old["t"]:
                        self.rows[f] = row
                    if self._latest is None or f >= self._latest["frame"]:
                        self._latest = self.rows[f]
            time.sleep(self.period)

    def window(self, t0: float | None = None, t1: float | None = None) -> list[dict]:
        with self._lock:
            rows = list(self.rows.values())
        rows.sort(key=lambda r: r["frame"])
        return [r for r in rows if (t0 is None or r["t"] >= t0) and (t1 is None or r["t"] <= t1)]

    def latest(self) -> dict | None:
        with self._lock:
            return self._latest

    def dump(self, path: Path) -> None:
        with path.open("w", encoding="utf-8") as fh:
            for r in self.window():
                fh.write(json.dumps(r) + "\n")


# --------------------------------------------------------------------------------------------------------- metrics
def circle_fit(pts) -> tuple[float, float, float, float] | None:
    """Algebraic (Kasa) least-squares circle: (cx, cz, r, rms residual), None under 8 points."""
    if len(pts) < 8:
        return None
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    mz = sum(p[1] for p in pts) / n
    suu = svv = suv = suuu = svvv = suvv = svuu = 0.0
    for x, z in pts:
        u, v = x - mx, z - mz
        suu += u * u; svv += v * v; suv += u * v
        suuu += u * u * u; svvv += v * v * v; suvv += u * v * v; svuu += v * u * u
    det = suu * svv - suv * suv
    if abs(det) < 1e-9:
        return None
    a = 0.5 * (suuu + suvv)
    b = 0.5 * (svvv + svuu)
    uc = (a * svv - b * suv) / det
    vc = (b * suu - a * suv) / det
    r = math.sqrt(uc * uc + vc * vc + (suu + svv) / n)
    cx, cz = uc + mx, vc + mz
    rms = math.sqrt(sum((math.hypot(x - cx, z - cz) - r) ** 2 for x, z in pts) / n)
    return cx, cz, r, rms


def _q(vals, q):
    if not vals:
        return None
    s = sorted(vals)
    k = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[k]


def window_metrics(rows: list[dict], *, centre=None, idle_median_ms: float | None = None) -> dict:
    """Metrics of one measurement window (rows already sliced to it, sorted by frame)."""
    rows = [r for r in rows if r["ui"] == "WorldHUD"]
    out: dict = {"n": len(rows)}
    if len(rows) < 3:
        out["ok"] = False
        return out
    span = rows[-1]["t"] - rows[0]["t"]
    frames = rows[-1]["frame"] - rows[0]["frame"]
    out.update({"ok": span > 0.5, "span_s": round(span, 3), "frames": frames,
                "fps": round(frames / span, 3) if span > 0 else None})
    durs = []
    for a, b in zip(rows, rows[1:]):
        df = b["frame"] - a["frame"]
        if 0 < df <= 2:
            durs.append((b["t"] - a["t"]) / df * 1000.0)
    out["dur_n"] = len(durs)
    if durs:
        out.update({"p50_ms": round(_q(durs, 0.5), 2), "p90_ms": round(_q(durs, 0.9), 2),
                    "p99_ms": round(_q(durs, 0.99), 2), "max_ms": round(max(durs), 2),
                    "long25": round(sum(d > 25.0 for d in durs) / len(durs), 4),
                    "long45": round(sum(d > 45.0 for d in durs) / len(durs), 4)})
        if idle_median_ms:
            out["long_rel"] = round(sum(d > LONG_REL * idle_median_ms for d in durs) / len(durs), 4)
    if len(rows) >= 8:                               # a regime switch INSIDE the window: its two halves disagree
        mid = len(rows) // 2
        h = []
        for part in (rows[:mid + 1], rows[mid:]):
            sp = part[-1]["t"] - part[0]["t"]
            h.append(round((part[-1]["frame"] - part[0]["frame"]) / sp, 3) if sp > 0 else None)
        out["halves_fps"] = h
    pts = [(r["x"], r["z"]) for r in rows if r["x"] is not None and r["z"] is not None]
    path = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
    out["path"] = round(path, 3)
    out["ticks_est"] = round(path / STEP, 1)
    out["tick_rate"] = round(path / STEP / span, 3) if span > 0 else None
    ys = [r["y"] for r in rows if r["y"] is not None]
    if ys:
        out.update({"y_med": round(statistics.median(ys), 4), "y_min": round(min(ys), 4), "y_max": round(max(ys), 4)})
    if path > 4 * RADIUS:
        fit = circle_fit(pts)
        if fit:
            out["circle"] = {"cx": round(fit[0], 3), "cz": round(fit[1], 3), "r": round(fit[2], 3),
                             "rms": round(fit[3], 3)}
    if centre is not None and pts:
        out["max_from_centre"] = round(max(math.hypot(x - centre[0], z - centre[1]) for x, z in pts), 3)
    return out


def pooled_fps(*ws) -> float | None:
    fr = sum(w.get("frames", 0) for w in ws if w and w.get("ok"))
    sp = sum(w.get("span_s", 0.0) for w in ws if w and w.get("ok"))
    return round(fr / sp, 3) if sp > 0 else None


def entry_hitch(rows: list[dict]) -> dict:
    """World-entry frames from a reload's rows: every gap > 250 ms with its context; `scene_switch_ms` = the gap
    whose end row is the first WorldMap-scene row; `blocks_ms` = the largest gap between that row and the first
    WorldHUD row (the synchronous LoadBlocks frame, ff9.cs:3703 -- every override is parsed inside it)."""
    gaps = []
    for a, b in zip(rows, rows[1:]):
        g = b["t"] - a["t"]
        if g > 0.25:
            gaps.append({"from": a["frame"], "to": b["frame"], "ms": round(g * 1000.0, 1),
                         "ctx": f"{a['ui']}/{a['scene']} -> {b['ui']}/{b['scene']}"})
    out = {"gaps": gaps, "scene_switch_ms": None, "blocks_ms": None}
    i_world = next((i for i, r in enumerate(rows) if r["scene"] == "WorldMap"), None)
    if i_world is None:
        return out
    if i_world > 0:
        out["scene_switch_ms"] = round((rows[i_world]["t"] - rows[i_world - 1]["t"]) * 1000.0, 1)
    i_hud = next((i for i in range(i_world, len(rows)) if rows[i]["ui"] == "WorldHUD"), None)
    if i_hud is None or i_hud == i_world:
        return out
    seg = rows[i_world:i_hud + 1]
    out["blocks_ms"] = round(max(b["t"] - a["t"] for a, b in zip(seg, seg[1:])) * 1000.0, 1)
    return out


# --------------------------------------------------------------------------------------------------------- decision
def regime_of(fps: float | None) -> str:
    if fps is None:
        return "?"
    if fps >= 45.0:
        return "60"
    if 24.0 <= fps < 40.0:
        return "31"
    return "other"


def load_q(load: dict, phase: str) -> dict | None:
    """Per-load quantities for a phase ("walk" at timescale 1, "walk4" amplified): Q = walk fps - idle fps (the
    idle windows of the SAME load and timescale are the within-load control: idle probes are cache hits, so idle
    pays every arm-independent cost and the render of the extra tris, never the scan)."""
    w = load.get("windows", {})
    walk = w.get(phase)
    idle = [w.get(k) for k in (("idle_pre", "idle_post") if phase == "walk" else ("idle4",))]
    idle = [x for x in idle if x and x.get("ok")]
    if not walk or not walk.get("ok") or not idle:
        return None
    f_idle = pooled_fps(*idle)
    pre, post = w.get("idle_pre"), w.get("idle_post")
    switched = bool(phase == "walk" and pre and post and pre.get("ok") and post.get("ok")
                    and abs(pre["fps"] / post["fps"] - 1.0) > REGIME_SPLIT)
    hv = walk.get("halves_fps") or [None, None]
    if None not in hv and abs(hv[0] / hv[1] - 1.0) > REGIME_SPLIT:
        switched = True                              # the walk itself changed rate halfway: not a steady arm cost
    return {"q_fps": round(walk["fps"] - f_idle, 3), "walk_fps": walk["fps"], "idle_fps": f_idle,
            "q_long": (round(walk["long_rel"] - max(x.get("long_rel", 0.0) for x in idle), 4)
                       if "long_rel" in walk else None),
            "tick_rate": walk.get("tick_rate"), "regime": regime_of(f_idle), "switched": switched}


def load_idle(load: dict, phase: str = "walk") -> dict | None:
    """The IDLE LEVEL of a load (the render-only question): pooled idle fps of the phase's idle windows. Its regime
    is read from the same number, so the decision below never filters it by regime -- it flags instead."""
    w = load.get("windows", {})
    idle = [w.get(k) for k in (("idle_pre", "idle_post") if phase == "walk" else ("idle4",))]
    idle = [x for x in idle if x and x.get("ok")]
    if not idle:
        return None
    f = pooled_fps(*idle)
    return {"idle_level": f, "regime": regime_of(f), "switched": False}


def _sigma(diffs: list[float]) -> float | None:
    if len(diffs) < 2:
        return None
    return math.sqrt(sum(d * d for d in diffs) / len(diffs) / 2.0)    # SD of one Q, from A-A differences


def decide(loads: list[dict], *, phase: str = "walk", key: str = "q_fps", t_min: float = T_MIN_FPS,
           positive_control: bool | None = None) -> dict:
    """THE DECISION RULE (registered in cost_PLAN.md before the run).

    loads: in time order; each {"load", "arm", "role" ("warm"|"ref"|"test"), "arm_ok", "windows"}.
    For each TEST load: D = Q(test) - mean(Q(prev ref), Q(next ref)), the refs being the nearest x1 loads before and
    after it. VALID only if both refs exist, all three bound their arm (arm_ok), share one regime (idle fps) and none
    switched regime inside the load. Noise: sigma = SD of one Q from consecutive VALID ref pairs of one regime;
    T = max(t_min, 3 x 1.22 x sigma) (1.22 = sqrt(1 + 1/2): a test minus the mean of two refs).
    Per arm: COST if >= 2 valid and every D < -T; FREE if >= 2 valid and every |D| < T (FREE-UNPROVEN when the
    positive control did not fire); else INCONCLUSIVE.

    key "idle_level" asks the RENDER question (idle fps itself): its regime IS the measured value, so a test whose
    regime differs from both (agreeing) refs is not dropped as confounded -- it is a REGIME SHIFT, and an arm that
    shifts it in every occurrence is COST."""
    if key == "idle_level":
        q = [load_idle(ld, phase) if ld.get("role") != "warm" else None for ld in loads]
    else:
        q = [load_q(ld, phase) if ld.get("role") != "warm" else None for ld in loads]
    refs = [i for i, ld in enumerate(loads) if ld.get("role") == "ref" and ld.get("arm_ok") and q[i] is not None]
    aa = []
    for a, b in zip(refs, refs[1:]):
        qa, qb = q[a], q[b]
        if qa["regime"] == qb["regime"] and not qa["switched"] and not qb["switched"] and qa[key] is not None \
                and qb[key] is not None:
            aa.append(qb[key] - qa[key])
    sigma = _sigma(aa)
    thr = max(t_min, 3.0 * 1.22 * sigma) if sigma is not None else None
    occ: dict[str, list] = {}
    for i, ld in enumerate(loads):
        if ld.get("role") != "test":
            continue
        prev = max((j for j in refs if j < i), default=None)
        nxt = min((j for j in refs if j > i), default=None)
        row = {"load": ld.get("load"), "arm": ld["arm"], "valid": False, "why": None}
        if q[i] is None or not ld.get("arm_ok"):
            row["why"] = "no window / arm not bound"
        elif prev is None or nxt is None:
            row["why"] = "not bracketed by two x1 refs"
        else:
            trio = (q[prev], q[i], q[nxt])
            shift = (key == "idle_level" and trio[0]["regime"] == trio[2]["regime"] != trio[1]["regime"]
                     and None not in (trio[0][key], trio[1][key], trio[2][key]))
            if shift:
                row.update(shift=True, regime=q[i]["regime"],
                           d=round(q[i][key] - (q[prev][key] + q[nxt][key]) / 2.0, 3),
                           why="regime shift on the test load: " + "/".join(t["regime"] for t in trio))
            elif len({t["regime"] for t in trio}) != 1 or any(t["switched"] for t in trio):
                row["why"] = "regime-confounded: " + "/".join(t["regime"] + ("*" if t["switched"] else "")
                                                               for t in trio)
            elif any(t[key] is None for t in trio):
                row["why"] = f"no {key}"
            else:
                row.update(valid=True, regime=q[i]["regime"],
                           d=round(q[i][key] - (q[prev][key] + q[nxt][key]) / 2.0, 3),
                           refs=[loads[prev].get("load"), loads[nxt].get("load")])
        occ.setdefault(str(ld["arm"]), []).append(row)
    verdicts = {}
    for arm, rows in occ.items():
        ds = [r["d"] for r in rows if r["valid"]]
        shifts = [r["d"] for r in rows if r.get("shift")]
        if len(shifts) >= 2 and len(shifts) == len(rows) and (all(d < 0 for d in shifts) or all(d > 0 for d in shifts)):
            verdicts[arm] = {"verdict": "COST (regime shift in every occurrence)" if shifts[0] < 0
                             else "GAIN (regime shift in every occurrence)", "d": shifts,
                             "mean_d": round(sum(shifts) / len(shifts), 3), "occurrences": rows}
            continue
        if thr is None:
            v = "INCONCLUSIVE (no A-A noise floor: fewer than 2 valid consecutive x1 pairs)"
        elif len(ds) < 2:
            v = f"INCONCLUSIVE ({len(ds)} valid occurrence(s), 2 needed)"
        elif all(d < -thr for d in ds):
            v = "COST"
        elif all(abs(d) < thr for d in ds):
            v = "FREE" if positive_control else "FREE-UNPROVEN (the positive control did not fire)"
        else:
            v = "INCONCLUSIVE (mixed)"
        verdicts[arm] = {"verdict": v, "d": ds, "mean_d": round(sum(ds) / len(ds), 3) if ds else None,
                         "occurrences": rows}
    return {"phase": phase, "key": key, "sigma": None if sigma is None else round(sigma, 3), "aa_diffs": aa,
            "threshold": None if thr is None else round(thr, 3), "verdicts": verdicts,
            "regimes": [None if x is None else x["regime"] for x in q]}


def decide_load(loads: list[dict]) -> dict:
    """The world-entry hitch: D_E = blocks_ms(test) - mean(blocks_ms(prev ref), blocks_ms(next ref)); sigma from
    consecutive refs; T_E = max(40 ms, 3 x 1.22 x sigma). LOAD-COST if >= 2 valid and every D_E > T_E; BELOW-FLOOR if
    every |D_E| < T_E (the effect, if any, is under T_E); else INCONCLUSIVE. Regime is irrelevant here (one frame)."""
    e = [((ld.get("entry") or {}).get("blocks_ms") if ld.get("role") != "warm" else None) for ld in loads]
    refs = [i for i, ld in enumerate(loads) if ld.get("role") == "ref" and e[i] is not None]
    aa = [e[b] - e[a] for a, b in zip(refs, refs[1:])]
    sigma = _sigma(aa)
    thr = max(T_MIN_LOAD_MS, 3.0 * 1.22 * sigma) if sigma is not None else None
    occ: dict[str, list] = {}
    for i, ld in enumerate(loads):
        if ld.get("role") != "test" or e[i] is None:
            continue
        prev = max((j for j in refs if j < i), default=None)
        nxt = min((j for j in refs if j > i), default=None)
        if prev is None or nxt is None:
            continue
        occ.setdefault(str(ld["arm"]), []).append(round(e[i] - (e[prev] + e[nxt]) / 2.0, 1))
    verdicts = {}
    for arm, ds in occ.items():
        if thr is None or len(ds) < 2:
            v = "INCONCLUSIVE"
        elif all(d > thr for d in ds):
            v = "LOAD-COST"
        elif all(abs(d) < thr for d in ds):
            v = f"BELOW-FLOOR (< {thr:.0f} ms)"
        else:
            v = "INCONCLUSIVE (mixed)"
        verdicts[arm] = {"verdict": v, "d_ms": ds}
    return {"sigma_ms": None if sigma is None else round(sigma, 1), "threshold_ms": None if thr is None else round(thr, 1),
            "aa_diffs_ms": [round(x, 1) for x in aa], "verdicts": verdicts}


def score(loads: list[dict], *, amp_arm: str = "64") -> dict:
    """Everything the session reports: the amplified phase first (it decides whether FREE can be believed)."""
    amp = decide(loads, phase="walk4", t_min=T_MIN_FPS_AMP, positive_control=True)
    heavy = amp["verdicts"].get(amp_arm, {})
    fired = heavy.get("verdict") == "COST"
    walk = decide(loads, phase="walk", positive_control=fired)
    walk_long = decide(loads, phase="walk", key="q_long", t_min=0.03, positive_control=fired)
    idle = decide(loads, phase="walk", key="idle_level", positive_control=fired)
    return {"positive_control": {"arm": amp_arm, "fired": fired, "detail": heavy.get("verdict")},
            "walk": walk, "walk_long": walk_long, "idle_render": idle, "amplified": amp, "load": decide_load(loads)}
