#!/usr/bin/env python3
"""The deciding A/B for the harness's one open question: does the character translate?

The harness can press a button and the engine agrees it received it -- `key_up` (what UIKeyTrigger
sees) and `move_key` (what FieldMapActorController decided) are both true for the whole hold -- yet
`player.pos` never changes on 4010-4013 / 30416 / 30801. Two very different worlds explain that, and
they need opposite fixes:

  A. a REAL keyboard press walks him on the same field  -> real and virtual input diverge downstream
     of the movement decision, and the harness has a genuine bug.
  B. a real keyboard press does NOT walk him either     -> the harness is correct and these benches
     simply are not walkable right now (no mesh under the arrival, or a script that never finishes
     handing control over). Movement would then be proven-by-absence and the bug is elsewhere.

Running both phases in ONE attached session against ONE field is what makes the comparison mean
anything -- a human test on Monday and a harness test on Tuesday, on whatever field each happened to
pick, is how this project has previously talked itself into false conclusions.

Usage (the game must already be running; this attaches and never closes it):

    py studies/test-harness/movement_ab.py human    --seconds 40
    py studies/test-harness/movement_ab.py harness

Both write a per-sample JSONL trace next to the run so the raw evidence outlives the summary.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from harness import HarnessError, Session          # noqa: E402


def sample(g: Session, seconds: float, trace: Path, label: str) -> dict:
    """Poll state as fast as it publishes, recording every position and input reading."""
    rows: list[dict] = []
    start = time.time()
    first = None
    while time.time() - start < seconds:
        st = g.channel.state()
        if st is not None and (not rows or st.frame != rows[-1]["frame"]):
            inp = st.raw.get("input", {})
            row = {
                "t": round(time.time() - start, 3),
                "frame": st.frame,
                "x": st.player_x, "y": st.player_y, "z": st.player_z,
                "control": st.control,
                "field": st.field_id,
                "key_up": inp.get("key_up"),
                "move_key": inp.get("move_key"),
                "dash_inh": inp.get("dash_inh"),
                "axis_x": inp.get("axis_x"), "axis_y": inp.get("axis_y"),
                "held": st.held,
            }
            rows.append(row)
            if first is None and row["x"] is not None:
                first = row
        time.sleep(0.01)

    with trace.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({"phase": label, **r}) + "\n")

    moved = 0.0
    if first is not None:
        for r in rows:
            if r["x"] is None:
                continue
            d = max(abs(r["x"] - first["x"]), abs(r["z"] - first["z"]))
            moved = max(moved, d)

    return {
        "phase": label,
        "samples": len(rows),
        "field": first["field"] if first else None,
        "start_pos": (first["x"], first["z"]) if first else None,
        "max_displacement": round(moved, 3),
        "control_ever": any(r["control"] for r in rows),
        "key_up_ever": any(r["key_up"] for r in rows),
        "move_key_ever": any(r["move_key"] for r in rows),
        "dash_inh": sorted({r["dash_inh"] for r in rows if r["dash_inh"] is not None}),
        "axis_nonzero": any((r["axis_x"] or 0) or (r["axis_y"] or 0) for r in rows),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["human", "harness"])
    ap.add_argument("--seconds", type=float, default=40.0,
                    help="how long to watch during the human phase")
    ap.add_argument("--frames", type=int, default=150,
                    help="how long to inject Up during the harness phase")
    args = ap.parse_args(argv)

    out = Path(__file__).resolve().parent / "movement-ab"
    out.mkdir(exist_ok=True)
    trace = out / "trace.jsonl"

    with Session(label=f"movement-ab-{args.phase}", attach=True, run_dir=out / args.phase) as g:
        st = g.state
        print(f"[ab] attached: {st!r}")
        if st.field_id <= 0:
            print("[ab] !! not on a field -- walk onto one first, then re-run")
            return 2

        if args.phase == "human":
            print(f"[ab] watching for {args.seconds:.0f}s -- HOLD A DIRECTION ON THE KEYBOARD NOW")
            summary = sample(g, args.seconds, trace, "human")
        else:
            print(f"[ab] injecting Up for {args.frames} frames")
            g.send(f"hold up {args.frames}", wait=False)
            summary = sample(g, args.frames / 60.0 + 1.0, trace, "harness")

    print("\n[ab] " + json.dumps(summary, indent=2))
    verdict = ("MOVED" if summary["max_displacement"] > 0.5 else "DID NOT MOVE")
    print(f"\n[ab] VERDICT ({args.phase}): {verdict} "
          f"(max displacement {summary['max_displacement']})")
    print(f"[ab] trace: {trace}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except HarnessError as err:
        print(f"[ab] harness error: {err}")
        sys.exit(1)
