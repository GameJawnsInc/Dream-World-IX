"""Measure the npc_default bench (30925) against its control: measure_shadows.py's rung-0 feet boxes, relabelled.

    py studies/actor-shadow/measure_npc_default.py <shadows-on run dir> <control run dir> [--out PNG]

bench/npc_default.field.toml puts its actors on rung 0's exact slots and spawn, so the rung-0 boxes frame them
unchanged: player -> the Black Waltz 3 player, stock -> frog, rover -> bird, big -> ramuh, none -> frog_off
(shadow = false in BOTH builds: the in-frame negative control, which must read ~1.0).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_shadows as MS  # noqa: E402

LABELS = {"player": "player (Black Waltz 3)", "stock": "frog", "rover": "bird", "big": "ramuh",
          "none": "frog_off (shadow = false)"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("on", type=Path)
    ap.add_argument("control", type=Path)
    ap.add_argument("--shot", default="1-spawn")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    on = Image.open(a.on / "shots" / f"{a.shot}.png").convert("RGB")
    off = Image.open(a.control / "shots" / f"{a.shot}.png").convert("RGB")
    for slot, m in MS.measure(on, off).items():                 # the rung-0 boxes (the default)
        r = "n/a" if m["ratio"] is None else f"{m['ratio']:.3f}"
        dk = "n/a" if m["darkened"] is None else f"{100 * m['darkened']:.1f}%"
        print(f"{LABELS[slot]:26s} floor px {m['floor_px']:6d}   luminance on/control {r}   darkened >=5%: {dk}")
    if a.out:
        MS.sheet(on, off, a.out)
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
