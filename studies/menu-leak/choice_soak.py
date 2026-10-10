"""Choice-menu memory soak: does each dialogue CHOICE grow FF9.exe's private memory, and by what?

    py studies/sims/sims_bench2.py deploy        # bench 30431 (once; it is usually already live)
    py tools/play.py studies/menu-leak/choice_soak.py
    SOAK_ARMS=quick,held,idle SOAK_QUICK=30 SOAK_HELD=10 SOAK_HOLD_S=10 py tools/play.py ...

Arms (one launch, in order; each samples FF9's PrivateUsage straight from Win32, no PowerShell):
  idle   stand still -- the floor the other arms are judged against
  quick  open the pot menu and decline it at once, N times
  held   open it, leave it up SOAK_HOLD_S seconds, then decline, N times
A per-OPEN leak grows quick and held by the same MB per menu; a per-FRAME-while-open leak grows held far more.
Writes soak.jsonl (every sample) next to the scenario's run artifacts and prints a per-arm MB/menu slope.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "studies" / "sims"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

import sims_bench2 as B                                  # noqa: E402

B.configure("priority")                                  # bench 30431
import rung2_day as R                                    # noqa: E402
from harness.session import ff9_pids                     # noqa: E402
from memprobe import private_mb, _slope                  # noqa: E402


ROWS: list[dict] = []


def _sample(pid: int, arm: str, n: int) -> dict:
    priv, ws = private_mb(pid)
    row = {"t": round(time.time(), 2), "arm": arm, "n": n, "private_mb": round(priv, 1), "ws_mb": round(ws, 1)}
    ROWS.append(row)
    print(f"  [{arm:>5} {n:3}] private {priv:7.1f} MB  ws {ws:7.1f} MB", flush=True)
    return row


def _menu(g, hold_s: float) -> bool:
    got = R._open_menu(g)
    if got is None:
        return False
    if hold_s > 0:
        time.sleep(hold_s)
    g.choose_landed(g.option_index("Never mind."))
    g.wait_for(lambda s: s.choice is None and s.control, timeout=10, what="control back after the menu")
    return True


def run(g) -> None:
    arms = os.environ.get("SOAK_ARMS", "idle,quick,held,idle").split(",")
    n_quick = int(os.environ.get("SOAK_QUICK", "30"))
    n_held = int(os.environ.get("SOAK_HELD", "10"))
    hold_s = float(os.environ.get("SOAK_HOLD_S", "10"))
    every = int(os.environ.get("SOAK_EVERY", "5"))
    pids = ff9_pids()
    assert len(pids) == 1, pids
    pid = pids[0]

    g.newgame()
    g.warp(R.FID)
    g.wait_for(lambda s: s.field_id == R.FID and s.control, timeout=30, what="the bench")
    R._go(g, "hunger")
    time.sleep(20)                                       # settle the field load before the floor
    summary = {}
    for k, arm in enumerate(arms):
        tag = f"{arm}{k}"
        rows0 = len(ROWS)
        g.note(f"soak arm {tag}")
        if arm == "idle":
            for i in range(7):
                _sample(pid, tag, i)
                time.sleep(5)
        else:
            count, hold = (n_quick, 0.0) if arm == "quick" else (n_held, hold_s)
            step = every if arm == "quick" else 1
            _sample(pid, tag, 0)
            done = 0
            for i in range(1, count + 1):
                if not _menu(g, hold):
                    g.check(False, f"{tag}: menu {i} opened")
                    break
                done = i
                if i % step == 0:
                    _sample(pid, tag, i)
            time.sleep(5)
            _sample(pid, tag, done)                      # a settled read at the same n
        arm_rows = ROWS[rows0:]
        s = _slope(arm_rows)
        delta = arm_rows[-1]["private_mb"] - arm_rows[0]["private_mb"]
        summary[tag] = {"slope_mb_per_menu_or_sample": None if s is None else round(s, 3),
                        "delta_mb": round(delta, 1), "samples": len(arm_rows)}
        print(f"== {tag}: delta {delta:+.1f} MB, slope {s if s is None else round(s, 3)}", flush=True)
    out = Path(g.run_dir) / "soak.jsonl" if getattr(g, "run_dir", None) else HERE / "soak-last.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in ROWS) + json.dumps({"summary": summary}) + "\n")
    print(json.dumps(summary, indent=1))
    g.check(True, "soak finished", json.dumps(summary))
