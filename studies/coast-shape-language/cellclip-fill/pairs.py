"""Side-by-side pairs of the two runs' stills: BEFORE (pre-fix fill) | AFTER (cell-clipped fill).

Per station and shot (a = the 12u view, near = 3u short of the OLD streak tri, on = standing on it):
<st>-<shot>-pair.png (whole frames) and <st>-<shot>-ahead.png (the frame's centre band at 2x, where the tri lands).
The two runs face the same heading from the same points (face_targets.json), so the frames line up -- but only to
sub-pixel camera jitter, so a pixel diff lights every textured surface and proves nothing: judge by eye.
RUN:  py studies/coast-shape-language/cellclip-fill/pairs.py <old run dir> <new run dir>   -> out/pairs/
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
AHEAD = (400, 160, 880, 560)                    # the centre band: the player and the ground in front of him


def find(run: Path, name: str) -> Path | None:
    hits = sorted(run.rglob(f"{name}.png"))
    return hits[0] if hits else None


def side(a: Image.Image, b: Image.Image, title: str) -> Image.Image:
    w, h = a.size
    out = Image.new("RGB", (w * 2 + 10, h + 30), (20, 20, 20))
    out.paste(a, (0, 30))
    out.paste(b, (w + 10, 30))
    d = ImageDraw.Draw(out)
    d.text((8, 8), f"{title}  BEFORE (pre-fix fill)", fill=(255, 210, 120))
    d.text((w + 18, 8), f"{title}  AFTER (cell-clipped fill)", fill=(140, 230, 140))
    return out


def main(old: Path, new: Path) -> None:
    dst = HERE / "out" / "pairs"
    dst.mkdir(parents=True, exist_ok=True)
    for st in "ABCD":
        for shot in ("a", "near", "on"):
            pa, pb = find(old, f"{st}-old-{shot}"), find(new, f"{st}-new-{shot}")
            if pa is None or pb is None:
                continue
            a, b = Image.open(pa).convert("RGB"), Image.open(pb).convert("RGB")
            side(a, b, f"{st} {shot}").save(dst / f"{st}-{shot}-pair.png")
            ca, cb = a.crop(AHEAD), b.crop(AHEAD)
            w, h = ca.size
            side(ca.resize((w * 2, h * 2), Image.LANCZOS), cb.resize((w * 2, h * 2), Image.LANCZOS),
                 f"{st} {shot} x2").save(dst / f"{st}-{shot}-ahead.png")
            print(dst / f"{st}-{shot}-ahead.png")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
