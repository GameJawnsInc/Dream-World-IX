"""`world-forest --spread / --rot` post-run: score the record and build the owner's shuffled panels.

Per view (west, east, north): the four stages' settled stills (the "-b" frame) side by side as W / X / Y / Z in a
seeded shuffled order (key in forest_key.json in the run dir). The question for the owner: does any canopy look
stretched, or turned wrong, next to the verbatim carry -- and from which spread on? NOT BLIND: one camera per view,
so each canopy's size names it (round 17's owner saw it at a glance); a blind texture judgement needs each variant
framed at a distance scaled by its spread (RESULTS.md, instrument lessons).

RUN:  py studies/terrain-malleability/canopyspread/lab_post.py <run dir>
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

STAGES = ("A", "B", "C", "D")
VIEWS = ("west", "east", "north")
SEED = 20261013 + 37
LABELS = "WXYZ"


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
    """2 x 2."""
    w, h = ims[0].size
    out = Image.new("RGB", (w * 2 + 8, h * 2 + 8), (40, 40, 40))
    for i, im in enumerate(ims):
        out.paste(im, ((i % 2) * (w + 8), (i // 2) * (h + 8)))
    return out


def main(run: Path):
    rec = json.loads((run / "forest_session.json").read_text(encoding="utf-8"))
    order = list(STAGES)
    random.Random(SEED).shuffle(order)
    key = {LABELS[i]: s for i, s in enumerate(order)}
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
        grid([label(frames[key[k]].copy(), k) for k in LABELS]).save(run / f"forest_panel_{view}.png")
    (run / "forest_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    (run / "forest_post.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
