"""Measure how the character actually moves, so scenarios can target POSITIONS instead of guessing frames.

`walk("up", 120)` is a bad primitive. It encodes a distance nobody measured, it silently saturates when
the character reaches a walkmesh edge, and every scenario that uses it hard-codes a constant that is
wrong on the next field. Before building `walk_to`, measure the thing it depends on.

This holds a direction while sampling every published frame, so one run yields the ramp, the
steady-state speed and the saturation point together -- rather than four separate before/after
measurements that cannot tell a slow start from a short run.

Measures, on the flat 30801 bench:
  * walk speed in world units per frame, and whether it is linear (it should be: the harness pushes a
    full unit vector, so there is no analog ramp -- worth CONFIRMING rather than assuming)
  * run speed, and which of walk/run is the unmodified default (Cancel XOR cfg.move decides it)
  * the diagonal, which is where a normalised vector could bite

    py tools/play.py studies/test-harness/scenarios/calibrate_movement.py --field 30801
"""
import json
import time
from pathlib import Path

FIELD = 30801
HOLD = 75          # long enough to reach steady state, short enough not to cross the whole bench


def _trace(g, steps, frames):
    """Fire `steps` and sample position every newly-published frame until the hold has elapsed."""
    g.send(*steps, wait=False)
    rows, deadline = [], time.time() + frames / 60.0 + 1.5
    while time.time() < deadline:
        st = g.channel.state()
        if st is not None and st.player_x is not None and (not rows or st.frame != rows[-1][0]):
            rows.append((st.frame, st.player_x, st.player_z))
        time.sleep(0.008)
    return rows


def _measure(g, label, steps, frames):
    start = g.state
    rows = _trace(g, steps, frames)
    g.wait_frames(20)
    end = g.state

    # Per-frame speed across the middle of the hold, avoiding the first/last samples where the hold
    # is starting or has already ended.
    speeds = []
    for (f0, x0, z0), (f1, x1, z1) in zip(rows, rows[1:]):
        df = f1 - f0
        if df <= 0:
            continue
        d = ((x1 - x0) ** 2 + (z1 - z0) ** 2) ** 0.5
        speeds.append(d / df)
    moving = [s for s in speeds if s > 0.01]
    steady = sorted(moving)[len(moving) // 4:] if moving else []      # drop the ramp-in quartile

    total = ((end.player_x - start.player_x) ** 2 + (end.player_z - start.player_z) ** 2) ** 0.5
    per_frame = sum(steady) / len(steady) if steady else 0.0
    row = {
        "label": label,
        "frames": frames,
        "samples": len(rows),
        "moving_samples": len(moving),
        "total_displacement": round(total, 2),
        "units_per_frame": round(per_frame, 3),
        "implied_total": round(per_frame * frames, 1),
        "from": [round(start.player_x, 1), round(start.player_z, 1)],
        "to": [round(end.player_x, 1), round(end.player_z, 1)],
    }
    print(f"[cal] {label:14} {total:8.1f}u over {frames} frames  ->  {per_frame:6.3f} u/frame")
    return row


def run(g, field: int = FIELD):
    g.note("calibrate_movement")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.timescale(1.0)          # calibration must not run under a distorted clock

    out = []
    # Alternate the axis each time so the character oscillates around the bench centre instead of
    # marching into an edge, where displacement would saturate and read as a slower speed.
    out.append(_measure(g, "walk-up", [f"hold up {HOLD}"], HOLD))
    out.append(_measure(g, "walk-down", [f"hold down {HOLD}"], HOLD))
    out.append(_measure(g, "run-up", [f"hold cancel {HOLD}", f"hold up {HOLD}"], HOLD))
    out.append(_measure(g, "run-down", [f"hold cancel {HOLD}", f"hold down {HOLD}"], HOLD))
    out.append(_measure(g, "diag-up-right", [f"hold up {HOLD}", f"hold right {HOLD}"], HOLD))
    out.append(_measure(g, "diag-down-left", [f"hold down {HOLD}", f"hold left {HOLD}"], HOLD))

    dest = Path(g.run_dir) / "movement-calibration.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")

    walk = next((r["units_per_frame"] for r in out if r["label"] == "walk-up"), 0)
    run_ = next((r["units_per_frame"] for r in out if r["label"] == "run-up"), 0)
    diag = next((r["units_per_frame"] for r in out if r["label"] == "diag-up-right"), 0)

    g.check(walk > 0.5, "the plain direction hold moves the character", f"{walk} u/frame")
    g.check(abs(run_ - walk) > 0.05, "the Cancel modifier changes speed",
            f"plain {walk} vs modified {run_} u/frame")
    g.check(diag > 0.5, "a diagonal hold moves the character", f"{diag} u/frame")
    print(f"\n[cal] plain={walk} u/frame  modified={run_} u/frame  diagonal={diag} u/frame")
    print(f"[cal] wrote {dest}")
