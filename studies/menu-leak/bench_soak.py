"""The crossed soak on LEAKBENCH (bench/leakbench.field.toml, slot 30487): which window leaks -- any window, a choice,
or the "!" bubble?

    py tools/deploy_field.py studies/menu-leak/bench/leakbench.field.toml --id 30487   # first deploy = relaunch
    py tools/play.py studies/menu-leak/bench_soak.py
    SOAK_SPOTS=cursor SOAK_N=60   # one choice held open, the cursor moved N times
    SOAK_SPOTS=choice,plain SOAK_N=30 py tools/play.py studies/menu-leak/bench_soak.py

For each spot: walk there, a short idle floor, then open/close its window N times, sampling FF9's private bytes
(memprobe.private_mb) every SOAK_EVERY windows. Prints and writes per-spot MB/window.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE))

from harness.session import ff9_pids                     # noqa: E402
from memprobe import private_mb, _slope                  # noqa: E402

FID = 30487
STAND = {"plain": (-750, -1450), "choice": (750, -1450),
         "plain_bubble": (-750, -550), "choice_bubble": (750, -550), "cursor": (750, -1450)}
ROWS: list[dict] = []


def _sample(pid: int, spot: str, n: int) -> None:
    priv, ws = private_mb(pid)
    ROWS.append({"t": round(time.time(), 2), "spot": spot, "n": n, "private_mb": round(priv, 1), "ws_mb": round(ws, 1)})
    print(f"  [{spot:>13} {n:3}] private {priv:7.1f} MB  ws {ws:7.1f} MB", flush=True)


def _open(g, is_choice: bool) -> bool:
    for _ in range(3):
        g.press("confirm", 4)
        try:
            if is_choice:
                g.wait_for(lambda s: s.choice is not None and s.menu_group == g.CHOICE_GROUP, timeout=3.0,
                           what="the choice ready")
            else:
                g.wait_for(lambda s: s.dialog_open, timeout=3.0, what="the window")
            return True
        except Exception:                                # noqa: BLE001
            continue
    return False


def _close(g, is_choice: bool) -> None:
    if is_choice:
        g.choose_landed(g.option_index("Never mind."))
    else:
        time.sleep(0.3)
        for _ in range(6):
            if not g.state.dialog_open:
                break
            g.press("confirm", 4)
            time.sleep(0.4)
    g.wait_for(lambda s: not s.dialog_open and s.control, timeout=10, what="control back")


def run(g) -> None:
    spots = os.environ.get("SOAK_SPOTS", "plain,choice,plain_bubble,choice_bubble").split(",")
    n = int(os.environ.get("SOAK_N", "30"))
    every = int(os.environ.get("SOAK_EVERY", "5"))
    pid = ff9_pids()[0]
    g.newgame()
    g.warp(FID)
    g.wait_for(lambda s: s.field_id == FID and s.control, timeout=30, what="the bench")
    time.sleep(15)
    summary = {}
    for spot in spots:
        x, z = STAND[spot]
        st = g.state
        g.walk_to(st.player_x, z, tolerance=40, strict=False)
        g.walk_to(x, z, tolerance=40, strict=False)
        time.sleep(3)
        r0 = len(ROWS)
        _sample(pid, spot, 0)
        is_choice = spot.startswith("choice") or spot == "cursor"
        done = 0
        if spot == "cursor":                             # ONE window held open; only the cursor moves (each = SE 103)
            if not _open(g, True):
                g.check(False, "cursor: the choice opened")
            else:
                for i in range(1, n + 1):
                    g.press("down", 4)
                    time.sleep(0.35)
                    done = i
                    if i % every == 0:
                        _sample(pid, spot, i)
                _close(g, True)
        for i in range(1, n + 1 if spot != "cursor" else 1):
            if not _open(g, is_choice):
                g.check(False, f"{spot}: window {i} opened", f"at ({g.state.player_x},{g.state.player_z})")
                break
            _close(g, is_choice)
            done = i
            if i % every == 0:
                _sample(pid, spot, i)
        time.sleep(5)
        _sample(pid, spot, done)
        rows = ROWS[r0:]
        s = _slope(rows)
        summary[spot] = {"windows": done, "delta_mb": round(rows[-1]["private_mb"] - rows[0]["private_mb"], 1),
                         "mb_per_window": None if s is None else round(s, 3)}
        print(f"== {spot}: {summary[spot]}", flush=True)
        g.check(done == n, f"{spot}: {n} windows opened and closed", json.dumps(summary[spot]))
    (Path(g.run_dir) / "soak.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ROWS)
                                                + json.dumps({"summary": summary}) + "\n")
    print(json.dumps(summary, indent=1))
