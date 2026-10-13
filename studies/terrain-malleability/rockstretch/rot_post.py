"""`world-mountain --rot` post-run: score the record and build the owner's blind panels.

Per view (west, east, north): the three stages' settled stills (the "-b" frame) side by side as X / Y / Z in a seeded
shuffled order (key in rot_key.json in the run dir), full frame and a 2x crop round the massif's foot (CROPS, set
by eye from the frames). The question for the owner is the FOOT: does the seam where grass meets rock read the
same at 45 and 30 deg as at 0 deg?

RUN:  py studies/terrain-malleability/rockstretch/rot_post.py <run dir>
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

STAGES = ("A", "B", "C")
VIEWS = ("west", "east", "north")
SEED = 20261013
# the massif and its foot in each view (x0, y0, x1, y1), by eye from the frames
CROPS = {"west": (360, 0, 920, 470), "east": (340, 0, 900, 460), "north": (330, 0, 890, 460)}


def label(im: Image.Image, text: str) -> Image.Image:
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("arial.ttf", max(18, im.width // 24))
    except OSError:
        f = ImageFont.load_default()
    d.rectangle((0, 0, f.size * len(text) * 0.75 + 16, f.size + 12), fill=(0, 0, 0))
    d.text((8, 4), text, fill=(255, 255, 255), font=f)
    return im


def row(ims: list) -> Image.Image:
    w, h = ims[0].size
    out = Image.new("RGB", (w * len(ims) + 8 * (len(ims) - 1), h), (40, 40, 40))
    for i, im in enumerate(ims):
        out.paste(im, (i * (w + 8), 0))
    return out


def main(run: Path):
    rec = json.loads((run / "rot_session.json").read_text(encoding="utf-8"))
    order = list(STAGES)
    random.Random(SEED).shuffle(order)
    key = {"XYZ"[i]: s for i, s in enumerate(order)}
    shots = run / "shots"
    out = {"settle": {}, "stages": {}}
    for s in rec["stages"]:
        out["stages"][s["stage"]] = {
            "error": s.get("error"),
            "summit": s.get("summit"),
            "ring_ok": sum(r["ok"] for r in s.get("ring", [])), "ring_n": len(s.get("ring", [])),
            "walks": {v: d.get("walk", {}).get("outcome") for v, d in s["views"].items() if d.get("walk")}}
    for view in VIEWS:
        frames = {}
        for st in STAGES:
            a, b = shots / f"{st}-{view}-a.png", shots / f"{st}-{view}-b.png"
            if a.is_file() and b.is_file():
                A = np.asarray(Image.open(a).convert("RGB"), dtype=np.int16)
                B = np.asarray(Image.open(b).convert("RGB"), dtype=np.int16)
                out["settle"][f"{st}-{view}"] = round(float((np.abs(A - B).max(-1) > 24).mean() * 100), 2)
                frames[st] = Image.open(b).convert("RGB")
        if len(frames) < 3:
            print(f"{view}: only {sorted(frames)} -- no panel")
            continue
        row([label(frames[key[k]].copy(), k) for k in "XYZ"]).save(run / f"rot_panel_{view}.png")
        x0, y0, x1, y1 = CROPS[view]
        row([label(frames[key[k]].crop((x0, y0, x1, y1)).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.LANCZOS), k)
             for k in "XYZ"]).save(run / f"rot_crops_{view}.png")
    (run / "rot_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    (run / "rot_post.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
