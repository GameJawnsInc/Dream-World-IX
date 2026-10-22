"""comp9 IN GAME (round 21) post-run: score the record and build the owner's panels.

Per view (west, east, north, south, inlet): the three stages' settled stills (the "-b" frame) side by side, LABELLED
by angle. Rotation, not size, is the variable, so the panels do not need size-matched framing (round 17's lesson
is about a size variant). The question for the owner: does comp9 read as a stock FF9 snow mountain at each angle,
and does its inlet floor read as the massif's own snow, not a patch?

RUN:  py studies/terrain-malleability/snowmassif/lab_post.py <run dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

VIEWS = ("west", "east", "north", "south", "inlet")


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
    """Two by two: A B / C (blank)."""
    w, h = ims[0].size
    out = Image.new("RGB", (2 * w + 8, 2 * h + 8), (40, 40, 40))
    for i, im in enumerate(ims):
        out.paste(im, ((i % 2) * (w + 8), (i // 2) * (h + 8)))
    return out


def main(run: Path):
    rec = json.loads((run / "mountain_session.json").read_text(encoding="utf-8"))
    stages = [(s["stage"], s["rot"]) for s in rec["stages"]]
    shots = run / "shots"
    out = {"settle": {}, "stages": {}}
    for s in rec["stages"]:
        il = s.get("inlet") or {}
        out["stages"][s["stage"]] = {
            "rot": s["rot"], "error": s.get("error"), "summit": s.get("summit"),
            "ring_ok": sum(r["ok"] for r in s.get("ring", [])), "ring_n": len(s.get("ring", [])),
            "inlet_probe": il.get("probe_at"), "inlet_walk": (il.get("walk") or {}).get("progress"),
            "walks": {v: (d["walk"]["outcome"], len(d["walk"]["off_surface"])) for v, d in s["views"].items()
                      if d.get("walk")}}
    for view in VIEWS:
        frames = {}
        for st, rot in stages:
            a, b = shots / f"{st}-{view}-a.png", shots / f"{st}-{view}-b.png"
            if a.is_file() and b.is_file():
                A = np.asarray(Image.open(a).convert("RGB"), dtype=np.int16)
                B = np.asarray(Image.open(b).convert("RGB"), dtype=np.int16)
                out["settle"][f"{st}-{view}"] = round(float((np.abs(A - B).max(-1) > 24).mean() * 100), 2)
                frames[st] = label(Image.open(b).convert("RGB"), f"{st}  rot {rot}")
        if len(frames) < len(stages):
            print(f"{view}: only {sorted(frames)} -- no panel")
            continue
        grid([frames[st] for st, _ in stages]).save(run / f"mountain_panel_{view}.png")
    (run / "mountain_post.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
