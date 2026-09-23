"""Measure rung 4 (see rung4_shadow_off.py) from the harness frames.

    py studies/actor-shadow/measure_rung4.py <on run> <init-only run> <control run> [--out DIR]

SPAWN (1-spawn): measure_shadows.py's set-pieces boxes, luminance ON / CONTROL and ON / INIT-ONLY. The off
actors (player, chest, moogle, holder) read above 1 against CONTROL (its MCF blob) and ~1 against INIT-ONLY;
the untouched ones (cask, cactus_on, barrel) ~1 against both.
LANDED (2-landed, 3-landed-later): the player stands at the jump's `to` with the camera settled on it, the same
frame in all three runs. LANDED_BOX is his feet (read off these frames); luminance ON / INIT-ONLY and
ON / CONTROL there read above 1 where the variant's blob came back, and ON's own repeat shot is the noise floor.
A whole-frame darkened count is printed too, but it is blunt: HUD icons differ between runs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

import measure_shadows as M


LANDED_BOX = {"player_landed": (820, 410, 920, 475)}      # the landed player's feet, 1280x720


def _img(run: Path, shot: str) -> Image.Image:
    return Image.open(run / "shots" / f"{shot}.png").convert("RGB")


def darkened(other: Image.Image, on: Image.Image) -> dict:
    """Floor pixels ``other`` darkens by >= 10% against ``on`` (both floor in each frame)."""
    n, box = 0, [10 ** 9, 10 ** 9, -1, -1]
    w, h = on.size
    for y in range(h):
        for x in range(w):
            a, b = other.getpixel((x, y)), on.getpixel((x, y))
            if M._is_floor(a) and M._is_floor(b) and M._lum(a) <= 0.90 * M._lum(b):
                n += 1
                box = [min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y)]
    return {"px": n, "box": tuple(box) if n else None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for k in ("on", "init_only", "control"):
        ap.add_argument(k, type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    on, io, ct = (_img(r, "1-spawn") for r in (a.on, a.init_only, a.control))
    print("SPAWN  box        on/control  on/init-only")
    mc, mi = M.measure(on, ct, M.BOXES_SET_PIECES), M.measure(on, io, M.BOXES_SET_PIECES)
    for name in M.BOXES_SET_PIECES:
        print(f"       {name:10s} {mc[name]['ratio']:.3f}       {mi[name]['ratio']:.3f}")
    for shot in ("2-landed", "3-landed-later"):
        on_l = _img(a.on, shot)
        for lab, run in (("init-only", a.init_only), ("control", a.control)):
            m = M.measure(on_l, _img(run, shot), LANDED_BOX)["player_landed"]
            print(f"{shot}: player_landed on/{lab} {m['ratio']:.3f} over {m['floor_px']} floor px")
        print(f"{shot}: darkened vs ON -- init-only {darkened(_img(a.init_only, shot), on_l)}, "
              f"control {darkened(_img(a.control, shot), on_l)}")
    nf = M.measure(_img(a.on, "3-landed-later"), _img(a.on, "2-landed"), LANDED_BOX)["player_landed"]
    print(f"noise floor: player_landed ON 3-landed-later / ON 2-landed {nf['ratio']:.3f}; whole frame "
          f"{darkened(_img(a.on, '3-landed-later'), _img(a.on, '2-landed'))}")
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        for shot in ("1-spawn", "2-landed"):
            imgs = [_img(r, shot) for r in (a.control, a.init_only, a.on)]
            sheet = Image.new("RGB", (imgs[0].width * 3, imgs[0].height), "white")
            for k, im in enumerate(imgs):
                sheet.paste(im, (k * im.width, 0))
            sheet.save(a.out / f"{shot}_control_initonly_on.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
