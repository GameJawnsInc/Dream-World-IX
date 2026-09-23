"""Measure the intensity-wrap bench (intensity_wrap.py): runs A and B swap the intensities between the four slots,
the CONTROL run casts nothing.

    py studies/actor-shadow/measure_intensity_wrap.py <run a dir> <run b dir> <control run dir> [--shot 1-spawn] [--out PNG]

The slots stand where the rung-0 bench's actors stood, so measure_shadows.py's feet boxes apply
(s1 = its `stock` box, s2 = `big`, s3 = `none`, s4 = `rover`, and the player's own). Pixels are scored only where
the CONTROL frame is floor: a mask taken from both frames (measure_shadows.py's) would drop exactly the pixels a
strong blob darkens out of the floor test.

Two measurements per slot:
  vs CONTROL   mean luminance run/control, and the fraction darkened by >= 5%. A drawn blob reads well under 1.
  A vs B       the same slot across the two runs: mean |dRGB| and the fraction of pixels with any channel off by
               more than 8. The prediction is a MATCH in every slot (15 vs 31 both colour 240; 16 vs 0 both
               colour 0). The player's box (nothing in either run) and each run's own repeat shot give the noise.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_shadows import BOXES, _is_floor, _lum, sheet  # noqa: E402

SLOTS = {"player": BOXES["player"], "s1": BOXES["stock"], "s2": BOXES["big"], "s3": BOXES["none"],
         "s4": BOXES["rover"]}
INTENSITY = {"a": {"player": None, "s1": 15, "s2": 16, "s3": 31, "s4": 0},
             "b": {"player": None, "s1": 31, "s2": 0, "s3": 15, "s4": 16}}


def _mask(control: Image.Image, box) -> list:
    x0, y0, x1, y1 = box
    return [(x, y) for y in range(y0, y1) for x in range(x0, x1) if _is_floor(control.getpixel((x, y)))]


def vs_control(run: Image.Image, control: Image.Image, px: list) -> tuple:
    s_on = s_off = 0.0
    dark = 0
    for p in px:
        la, lb = _lum(run.getpixel(p)), _lum(control.getpixel(p))
        s_on += la
        s_off += lb
        dark += la <= 0.95 * lb
    return (s_on / s_off if s_off else None), (dark / len(px) if px else None)


def match(a: Image.Image, b: Image.Image, px: list) -> tuple:
    tot = 0.0
    off = 0
    for p in px:
        d = [abs(u - v) for u, v in zip(a.getpixel(p)[:3], b.getpixel(p)[:3])]
        tot += sum(d) / 3
        off += max(d) > 8
    return (tot / len(px) if px else None), (off / len(px) if px else None)


def _load(run: Path, shot: str) -> Image.Image:
    return Image.open(run / "shots" / f"{shot}.png").convert("RGB")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("control", type=Path)
    ap.add_argument("--shot", default="1-spawn")
    ap.add_argument("--repeat", default="2-spawn-later", help="each run's own repeat shot (the noise floor)")
    ap.add_argument("--out", type=Path, default=None, help="a side-by-side sheet: run A (top) / run B (bottom)")
    a = ap.parse_args(argv)
    fa, fb, fc = _load(a.a, a.shot), _load(a.b, a.shot), _load(a.control, a.shot)
    ra, rb, rc = _load(a.a, a.repeat), _load(a.b, a.repeat), _load(a.control, a.repeat)
    print(f"{'slot':6s} {'A':>4s} {'B':>4s} {'floor px':>8s} | {'A/ctl':>6s} {'dark':>6s} | {'B/ctl':>6s} {'dark':>6s} |"
          f" {'A~B |d|':>8s} {'off>8':>6s} | {'repeat |d| A/B/ctl':>20s}")
    for slot, box in SLOTS.items():
        px = _mask(fc, box)
        (ca, da), (cb, db) = vs_control(fa, fc, px), vs_control(fb, fc, px)
        mab, oab = match(fa, fb, px)
        noise = [match(f, r, px)[0] for f, r in ((fa, ra), (fb, rb), (fc, rc))]
        ia, ib = INTENSITY["a"][slot], INTENSITY["b"][slot]
        print(f"{slot:6s} {str(ia):>4s} {str(ib):>4s} {len(px):8d} | {ca:6.3f} {100 * da:5.1f}% | {cb:6.3f} {100 * db:5.1f}% |"
              f" {mab:8.2f} {100 * oab:5.1f}% | " + " / ".join(f"{n:.2f}" for n in noise))
    if a.out:
        sheet(fb, fa, a.out, boxes=SLOTS, label="run A (top) / run B (bottom)")   # the 2nd argument is on top
        print(f"wrote {a.out}  (per slot: run A on top, run B below)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
