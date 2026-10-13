"""X1 post-run: score the summit probes, check the stills settled, and build the owner's panels.

Per viewpoint, one panel of the four stages' settled stills (the "-b" frame) and one of crops round the rock
(CROPS, shown at 2x). The panels are BLIND: the stages are
shown as A-D in a shuffled order (seeded, the same order in every panel) and the key is written to x1_key.json in
the run dir, so the owner judges the texture without the registered prediction beside it.

RUN:  py studies/terrain-malleability/rockstretch/x1_post.py <run dir> [<rerun dir> ...]
      (a stage present in several runs is taken from the LAST run that completed it; the outputs go to the first)
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

STAGES = ("rigid", "s125", "s150", "s200")
VIEWS = ("east", "west")
SEED = 20261012
# The rock's box in each view, set by eye from the tallest (s200) and the rigid frames: a pixel-difference box
# covers the whole frame (the sea animates, and the stages' headings differ by up to 3 deg).
CROPS = {"east": (330, 10, 870, 360), "west": (400, 0, 860, 390)}


def load(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.int16)


def label(im: Image.Image, text: str) -> Image.Image:
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("arial.ttf", max(18, im.width // 24))
    except OSError:
        f = ImageFont.load_default()
    d.rectangle((0, 0, f.size * len(text) * 0.75 + 16, f.size + 12), fill=(0, 0, 0))
    d.text((8, 4), text, fill=(255, 255, 255), font=f)
    return im


def grid(ims: list, cols: int = 2) -> Image.Image:
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    out = Image.new("RGB", (w * cols + 8 * (cols - 1), h * rows + 8 * (rows - 1)), (40, 40, 40))
    for i, im in enumerate(ims):
        out.paste(im, ((i % cols) * (w + 8), (i // cols) * (h + 8)))
    return out


def main(runs: list):
    run = runs[0]
    done, where = {}, {}
    for r in runs:
        for s in json.loads((r / "x1_session.json").read_text(encoding="utf-8"))["stages"]:
            if "error" not in s:
                done[s["stage"]], where[s["stage"]] = s, r
    rec = {"stages": [done[s] for s in STAGES if s in done]}

    def find(name):
        st = name.split("-")[0]
        r = where.get(st)
        return next(iter(sorted(r.rglob(f"*{name}.png"))), None) if r else None
    order = list(STAGES)
    random.Random(SEED).shuffle(order)
    key = {chr(65 + i): s for i, s in enumerate(order)}
    out = {"runs": {k: str(v) for k, v in where.items()}, "probe": {}, "settle": {}, "key_file": "x1_key.json"}
    for s in rec["stages"]:
        p = s.get("probe") or {}
        out["probe"][s["stage"]] = {"want": p.get("want"), "got": p.get("got"),
                                    "ok": p.get("got") is not None and abs(p["got"] - p["want"]) <= 0.15}
    for view in VIEWS:
        frames = {}
        for st in STAGES:
            a, b = find(f"{st}-{view}-a"), find(f"{st}-{view}-b")
            if a is None or b is None:
                continue
            A, B = load(a), load(b)
            out["settle"][f"{st}-{view}"] = round(float(np.abs(A - B).max(-1).__gt__(24).mean() * 100), 2)
            frames[st] = B
        if len(frames) < 4:
            print(f"{view}: only {sorted(frames)} -- no panel")
            continue
        box = CROPS[view]
        out[f"crop_{view}"] = box
        full = [label(Image.fromarray(frames[key[k]].astype(np.uint8)), k) for k in sorted(key)]
        grid(full).save(run / f"x1_panel_{view}.png")
        bw, bh = box[2] - box[0], box[3] - box[1]
        crops = [label(Image.fromarray(frames[key[k]].astype(np.uint8)).crop(box).resize((bw * 2, bh * 2),
                                                                                         Image.LANCZOS), k)
                 for k in sorted(key)]
        grid(crops).save(run / f"x1_crops_{view}.png")
    (run / "x1_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    (run / "x1_post.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    main([Path(a) for a in sys.argv[1:]])
