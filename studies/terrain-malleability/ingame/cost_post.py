"""RE-SCORE a cost_session.py run OFFLINE from its own dumped samples: rebuild every window from the recorded marks and
the raw per-frame rows (cost_samples.jsonl), recompute the metrics with cost_lib, and apply the registered decision
rule -- so the verdict is reproducible from the run dir alone, and the rule can be re-run if it is ever corrected.

Also prints the per-load timeline (arm, regime, idle / walk fps, ticks a second, LoadBlocks ms) -- the place a
regime flip shows up -- and, when the unlocked (VSync 0) launch is scored (--unlocked), the per-tick cost in ms:
    tick_cost(arm) = (1 - f_walk / f_idle) / ticks_per_second      (no vsync quantisation: every frame's time is work)
and c = (tick_cost(x64) - tick_cost(x1)) / (tests(x64) - tests(x1)) with the tests from out/cost_predict.json.

Rerun:  py studies/terrain-malleability/ingame/cost_post.py <.harness-runs/<stamp>-cost-session> [--unlocked]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cost_lib as L                                               # noqa: E402

CENTRE = (1376.37, -96.61)


class Rows:
    def __init__(self, rows):
        self.rows = sorted(rows, key=lambda r: r["frame"])

    def window(self, t0=None, t1=None):
        return [r for r in self.rows if (t0 is None or r["t"] >= t0) and (t1 is None or r["t"] <= t1)]


def rescore(run_dir: Path) -> dict:
    rec = json.loads((run_dir / "cost_session.json").read_text(encoding="utf-8"))
    rows = [json.loads(x) for x in (run_dir / "cost_samples.jsonl").read_text(encoding="utf-8").splitlines() if x]
    P = Rows(rows)
    man_tags = {"1": 6.0, "4": 6.125, "16": 6.25, "64": 6.375}
    for ld in rec["loads"]:
        marks = ld.get("marks") or {}
        W = ld["windows"] = {}
        for k in ("idle_pre", "idle_post", "idle4"):
            if k in marks:
                W[k] = L.window_metrics(P.window(*marks[k]), centre=CENTRE)
        for walk, idle_k in (("walk", "idle_pre"), ("walk4", "idle4")):
            if walk in marks:
                med = (W.get(idle_k) or {}).get("p50_ms")
                if med:
                    W[idle_k] = L.window_metrics(P.window(*marks[idle_k]), centre=CENTRE, idle_median_ms=med)
                    if idle_k == "idle_pre" and "idle_post" in marks:
                        W["idle_post"] = L.window_metrics(P.window(*marks["idle_post"]), centre=CENTRE,
                                                          idle_median_ms=med)
                W[walk] = L.window_metrics(P.window(*marks[walk]), centre=CENTRE, idle_median_ms=med)
        y = (W.get("walk") or {}).get("y_med")
        ld["arm_y"] = y
        ld["arm_ok"] = y is not None and abs(y - man_tags[str(ld["arm"])]) <= 0.03
        if ld.get("t_walkout") and ld.get("t_arrived"):
            ld["entry"] = L.entry_hitch(P.window(ld["t_walkout"], ld["t_arrived"]))
    rec["score"] = L.score(rec["loads"])
    return rec


def unlocked_costs(rec: dict) -> dict:
    pred = json.loads((HERE / "out" / "cost_predict.json").read_text(encoding="utf-8"))
    tests = {a: v["by_D"][1]["tests_per_tick"] for a, v in pred["arms"].items()}
    by_arm: dict[str, list] = {}
    for ld in rec["loads"]:
        if ld["role"] == "warm":
            continue
        q = L.load_q(ld, "walk")
        if not q or not q["idle_fps"] or not q["tick_rate"]:
            continue
        by_arm.setdefault(str(ld["arm"]), []).append((1.0 - q["walk_fps"] / q["idle_fps"]) / q["tick_rate"] * 1000.0)
    ms = {a: round(sum(v) / len(v), 3) for a, v in by_arm.items()}
    out = {"ms_per_tick": ms}
    if "1" in ms and "64" in ms:
        out["c_us_per_test"] = round((ms["64"] - ms["1"]) * 1000.0 / (tests["64"] - tests["1"]), 4)
    return out


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    run_dir = Path(argv[0])
    rec = rescore(run_dir)
    S = rec["score"]
    print(f"{'W':>3} {'arm':>4} {'role':<5} {'y':>7} {'regime':>6} {'idle':>7} {'walk':>7} {'t/s':>6} "
          f"{'idle4':>7} {'walk4':>7} {'t/s4':>6} {'blocks ms':>9}")
    for ld, reg in zip(rec["loads"], S["walk"]["regimes"]):
        W = ld.get("windows") or {}
        q = L.load_q(ld, "walk") or {}
        f = lambda k, m: (W.get(k) or {}).get(m)                   # noqa: E731
        print(f"{ld['load']:>3} x{ld['arm']:<3} {ld['role']:<5} {str(ld.get('arm_y')):>7} {str(reg):>6} "
              f"{str(q.get('idle_fps')):>7} {str(f('walk', 'fps')):>7} {str(f('walk', 'tick_rate')):>6} "
              f"{str(f('idle4', 'fps')):>7} {str(f('walk4', 'fps')):>7} {str(f('walk4', 'tick_rate')):>6} "
              f"{str((ld.get('entry') or {}).get('blocks_ms')):>9}")
    print(f"\npositive control: {S['positive_control']}")
    for name in ("walk", "walk_long", "idle_render", "amplified"):
        d = S[name]
        print(f"{name:<12} sigma {d['sigma']} threshold {d['threshold']} :: "
              + "; ".join(f"x{a} {v['verdict']} {v['d']}" for a, v in sorted(d["verdicts"].items(), key=lambda kv: int(kv[0]))))
    ld = S["load"]
    print(f"load         sigma {ld['sigma_ms']} ms threshold {ld['threshold_ms']} ms :: "
          + "; ".join(f"x{a} {v['verdict']} {v['d_ms']}" for a, v in sorted(ld["verdicts"].items(), key=lambda kv: int(kv[0]))))
    if "--unlocked" in argv:
        print(f"\nunlocked: {unlocked_costs(rec)}")
    (run_dir / "cost_post.json").write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
