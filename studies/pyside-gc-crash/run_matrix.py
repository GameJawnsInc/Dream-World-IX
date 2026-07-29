"""Drive repro_scene_items_cursor_gc.py across a variant matrix in fresh subprocesses.

An access violation kills a process (Windows 0xC0000005 -> unsigned 3221225477), so each
(variant x N) cell counts crashed processes. Usage:

    py run_matrix.py [procs-per-variant] [rounds-per-proc]

Results print as a table and append as JSON lines to results.jsonl beside this file.
"""

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPRO = os.path.join(HERE, "repro_scene_items_cursor_gc.py")

VARIANTS = [
    # (label, env-overrides) — SWEEP is the suspect axis, PARK the teardown axis
    ("fresh+park",        {"SWEEP": "fresh",    "PARK": "1", "AGGRO": "0"}),
    ("fresh+drop",        {"SWEEP": "fresh",    "PARK": "0", "AGGRO": "0"}),
    ("fresh+park+aggro",  {"SWEEP": "fresh",    "PARK": "1", "AGGRO": "1"}),
    ("fresh+drop+aggro",  {"SWEEP": "fresh",    "PARK": "0", "AGGRO": "1"}),
    ("retained+park",     {"SWEEP": "retained", "PARK": "1", "AGGRO": "0"}),
    ("retained+drop",     {"SWEEP": "retained", "PARK": "0", "AGGRO": "0"}),
]


def run_one(env_over, rounds, timeout=300):
    env = dict(os.environ)
    env.update(env_over)
    env["ROUNDS"] = str(rounds)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, REPRO], env=env, capture_output=True,
                           text=True, timeout=timeout)
        code, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        code, out, err = "TIMEOUT", (e.stdout or ""), (e.stderr or "")
    done = isinstance(out, str) and "ALL ROUNDS DONE" in out
    last = ""
    for line in (out or "").splitlines():
        if line.strip():
            last = line.strip()
    return {"code": code, "reached_done": done, "last_line": last,
            "stderr_tail": (err or "")[-400:], "secs": round(time.time() - t0, 1)}


def main():
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    results_path = os.path.join(HERE, "results.jsonl")
    summary = {}
    for label, env_over in VARIANTS:
        crashes = 0
        codes = []
        for n in range(procs):
            r = run_one(env_over, rounds)
            codes.append(r["code"])
            crashed = r["code"] not in (0,)
            if crashed:
                crashes += 1
            with open(results_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"variant": label, "rounds": rounds, **r}) + "\n")
            print(f"[{label}] proc {n + 1}/{procs}: code={r['code']}"
                  f"{'' if r['reached_done'] else '  DIED AT: ' + r['last_line']}",
                  flush=True)
        summary[label] = (crashes, procs, codes)
    print("\n=== SUMMARY ===")
    for label, (crashes, total, codes) in summary.items():
        uniq = sorted({str(c) for c in codes if c != 0})
        print(f"{label:22s} {crashes}/{total} crashed"
              + (f"  (codes: {', '.join(uniq)})" if uniq else ""))


if __name__ == "__main__":
    main()
