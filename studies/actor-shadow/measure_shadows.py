"""Measure the blob shadows in a rung frame against its CONTROL frame (same bench, the actors under test at
shadow = false).

    py studies/actor-shadow/measure_shadows.py <shadows-on run dir> <control run dir> [--bench rung0|set_pieces] [--shot 1-spawn] [--out PNG]

Per actor, a box around its feet (this bench's fixed camera + spawn positions -- read off the frames, below):
only pixels that are FLOOR in both frames are scored (the actor's own model is excluded, so an idle-animation
frame that differs between the runs is not counted as shadow). The score is the mean luminance ratio
on/control over those floor pixels, and the fraction darkened by >= 5%. A shadow reads as a ratio well under 1;
`none` (shadow = false in BOTH builds) is the negative control and must stay ~1.0. Also writes a side-by-side
of every box, control above shadows-on, for the eye.

The set-pieces bench (bench/set_pieces.field.toml): `cactus` is stock-dark (no ops in EITHER build) and `player` / `holder`
keep their rung-0 shadows in BOTH builds -- all three are in-pair "unchanged" controls that must read ~1.0.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

# feet boxes (x0, y0, x1, y1) in the 1280x720 frame -- the actors stand still until `walk` is raised
BOXES = {"player": (380, 400, 540, 480), "stock": (700, 350, 880, 420), "none": (460, 570, 640, 650),
         "rover": (180, 570, 360, 650), "big": (880, 520, 1110, 640)}
# the set-pieces bench's spawn frame (bench/set_pieces.field.toml, player at (900, -600) -- the field camera follows it, so only the spawn
# frame is pixel-comparable between runs)
BOXES_SET_PIECES = {"cask": (170, 330, 390, 400), "cactus": (380, 300, 520, 365), "cactus_on": (550, 300, 690, 365),
           "chest": (725, 315, 855, 375), "moogle": (215, 510, 350, 570), "holder": (405, 545, 580, 615),
           "barrel": (895, 540, 1115, 630), "player": (915, 415, 1050, 465)}
BOXES_BY_BENCH = {"rung0": BOXES, "set_pieces": BOXES_SET_PIECES}


def _lum(p) -> float:
    r, g, b = p[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b


def _is_floor(p) -> bool:
    """The checkerboard's warm browns (either tile, lit or shaded): red > green > blue, clearly saturated.
    The CSO NPCs' white/blue/gold and Zidane's blue/white/grey fail it; their gold trim is excluded by the
    both-frames test (it differs between the frames only where the model is)."""
    r, g, b = p[:3]
    return r > g > b and (r - b) > 25


def measure(on: Image.Image, off: Image.Image, boxes: dict = BOXES) -> dict:
    out = {}
    for name, (x0, y0, x1, y1) in boxes.items():
        n = dark = 0
        s_on = s_off = 0.0
        for y in range(y0, y1):
            for x in range(x0, x1):
                a, b = on.getpixel((x, y)), off.getpixel((x, y))
                if not (_is_floor(a) and _is_floor(b)):
                    continue
                la, lb = _lum(a), _lum(b)
                n += 1
                s_on += la
                s_off += lb
                if la <= 0.95 * lb:
                    dark += 1
        out[name] = {"floor_px": n, "ratio": (s_on / s_off) if s_off else None,
                     "darkened": dark / n if n else None}
    return out


def sheet(on: Image.Image, off: Image.Image, path: Path, scale: int = 2, boxes: dict = BOXES,
          label: str = "control (top) / shadows on (bottom)") -> None:
    rows = [(f"{n}: {label}", b) for n, b in boxes.items()]
    w = max(b[2] - b[0] for _, b in rows) * scale
    h = sum(2 * (b[3] - b[1]) * scale + 22 for _, b in rows)
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    y = 0
    for label, b in rows:
        d.text((4, y + 4), label, fill="black")
        y += 22
        for src in (off, on):
            c = src.crop(b)
            img.paste(c.resize((c.width * scale, c.height * scale), Image.NEAREST), (0, y))
            y += c.height * scale
    img.save(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("on", type=Path)
    ap.add_argument("control", type=Path)
    ap.add_argument("--bench", default="rung0", choices=sorted(BOXES_BY_BENCH))
    ap.add_argument("--shot", default="1-spawn")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    on = Image.open(a.on / "shots" / f"{a.shot}.png").convert("RGB")
    off = Image.open(a.control / "shots" / f"{a.shot}.png").convert("RGB")
    boxes = BOXES_BY_BENCH[a.bench]
    for name, m in measure(on, off, boxes).items():
        r = "n/a" if m["ratio"] is None else f"{m['ratio']:.3f}"
        dk = "n/a" if m["darkened"] is None else f"{100 * m['darkened']:.1f}%"
        print(f"{name:9s} floor px {m['floor_px']:6d}   luminance on/control {r}   darkened >=5%: {dk}")
    if a.out:
        sheet(on, off, a.out, boxes=boxes)
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
