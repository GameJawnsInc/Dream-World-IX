"""`world-forest --donor` post-run: score the record and build the owner's panels.

Per view (west, east, north): the five stages' settled stills (the "-b" frame), LABELLED by donor -- the shapes
differ, so a shuffle could not blind them (round 17's lesson); the question is whether each reads as a stock
forest.

RUN:  py studies/terrain-malleability/forestdonors/lab_post.py <run dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

STAGES = ("A", "B", "C", "D", "E")
NAMES = {"A": "A 15,15 (control)", "B": "B 3,12 long", "C": "C 19,8 round",
         "D": "D 18,15 small", "E": "E 13,15 grove"}
VIEWS = ("west", "east", "north")


def label(im: Image.Image, text: str) -> Image.Image:
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("arial.ttf", max(18, im.width // 24))
    except OSError:
        f = ImageFont.load_default()
    d.rectangle((0, 0, f.size * len(text) * 0.75 + 16, f.size + 12), fill=(0, 0, 0))
    d.text((8, 4), text, fill=(255, 255, 255), font=f)
    return im


def grid(ims: list) -> Image.Image:
    """3 across."""
    w, h = ims[0].size
    rows = (len(ims) + 2) // 3
    out = Image.new("RGB", (w * 3 + 16, h * rows + 8 * (rows - 1)), (40, 40, 40))
    for i, im in enumerate(ims):
        out.paste(im, ((i % 3) * (w + 8), (i // 3) * (h + 8)))
    return out


def main(run: Path):
    rec = json.loads((run / "forest_session.json").read_text(encoding="utf-8"))
    shots = run / "shots"
    out = {"settle": {}, "stages": {}}
    for s in rec["stages"]:
        out["stages"][s["stage"]] = {
            "error": s.get("error"),
            "canopy_ok": sum(r["ok"] for r in s.get("canopy", [])), "canopy_n": len(s.get("canopy", [])),
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
        if len(frames) < len(STAGES):
            print(f"{view}: only {sorted(frames)} -- no panel")
            continue
        grid([label(frames[st].resize((frames[st].width // 2, frames[st].height // 2)), NAMES[st])
              for st in STAGES]).save(run / f"donors_panel_{view}.png")
    (run / "donors_post.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
