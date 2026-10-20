"""`world-mountain --spread` post-run: score the record and build the owner's panels.

Per view (west, east, north, south): the four stages' settled stills (the "-b" frame) side by side, LABELLED (the
size shows from one camera, so a shuffle could not blind it: round 17's lesson). The question for the owner: does a
widened Uaho read as a stock FF9 mountain, its rock not visibly stretched, at x1.25, x1.5 and scaled whole?

RUN:  py studies/terrain-malleability/mountainspread/lab_post.py <run dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

STAGES = ("A", "B", "C", "D")
NAMES = {"A": "A  rigid", "B": "B  x1.25 wide", "C": "C  x1.5 wide", "D": "D  x1.5 wide + x1.5 tall"}
VIEWS = ("west", "east", "north", "south")


def label(im: Image.Image, text: str) -> Image.Image:
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("arial.ttf", max(18, im.width // 24))
    except OSError:
        f = ImageFont.load_default()
    d.rectangle((0, 0, f.size * len(text) * 0.62 + 16, f.size + 12), fill=(0, 0, 0))
    d.text((8, 4), text, fill=(255, 255, 255), font=f)
    return im


def grid(ims: list) -> Image.Image:
    """Two by two: A B / C D."""
    w, h = ims[0].size
    out = Image.new("RGB", (2 * w + 8, 2 * h + 8), (40, 40, 40))
    for i, im in enumerate(ims):
        out.paste(im, ((i % 2) * (w + 8), (i // 2) * (h + 8)))
    return out


def main(run: Path):
    rec = json.loads((run / "mountain_session.json").read_text(encoding="utf-8"))
    shots = run / "shots"
    out = {"settle": {}, "stages": {}}
    for s in rec["stages"]:
        out["stages"][s["stage"]] = {
            "error": s.get("error"),
            "summit": s.get("summit"),
            "ring_ok": sum(r["ok"] for r in s.get("ring", [])), "ring_n": len(s.get("ring", [])),
            "walks": {v: (d["walk"]["outcome"], len(d["walk"]["off_surface"])) for v, d in s["views"].items()
                      if d.get("walk")}}
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
        grid([label(frames[st].copy(), NAMES[st]) for st in STAGES]).save(run / f"mountain_panel_{view}.png")
    (run / "mountain_post.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
