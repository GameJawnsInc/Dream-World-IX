"""Measure rung 1 (see rung1_editable_mcf.py) from the harness frames.

    py studies/actor-shadow/measure_rung1.py objects <on run> <control run> <empty run> [--out SHEET.png]
    py studies/actor-shadow/measure_rung1.py keying  <probe run> <reshape run> <reshape-nokey run> <empty run>

OBJECTS -- the carried donor objects, with vs without the donor MCF. The model mask is where CONTROL differs
from EMPTY (the grafted models; the player spawns off-screen in these three). Reported:
  tint    mean RGB on/control over pixels that are model in every frame (the MCF's (clr + light) << 3)
  shadow  background pixels (outside the dilated model mask) that ON darkens by >= 10% against EMPTY while
          CONTROL does not; its CALIBRATION is the same count with CONTROL in ON's place (must be ~0: before
          the fix no grafted object cast anything)
KEYING -- the player at the probe spot on donor floor 0: mean RGB of his model pixels in each reshape frame
over the probe (verbatim .bgi) frame, next to the MCF's prediction for floor 3's light landing on him instead.
The probe's own second shot is the noise floor.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

LUMA = np.array([0.299, 0.587, 0.114])
DIFF = 60                          # summed |dRGB| above which a pixel belongs to a model (not jpeg-ish noise)
ZIDANE_BOX = (250, 420, 520, 620)  # y0, y1, x0, x1 at the probe spot, 1280x720
# Zidane's MCF row clr (15, 15, 13); floor 0's light clr -1, floor 3's -3 -> the mis-key's tint ratio
NOKEY_PREDICTED = tuple(round(v, 3) for v in ((15 - 3) / (15 - 1), (15 - 3) / (15 - 1), (13 - 3) / (13 - 1)))


def _frame(run: Path, shot: str = "1-spawn") -> np.ndarray:
    return np.asarray(Image.open(run / "shots" / f"{shot}.png").convert("RGB")).astype(float)


def _dilate(m: np.ndarray, r: int) -> np.ndarray:
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def objects(on_run: Path, control_run: Path, empty_run: Path, out: Path | None = None) -> dict:
    on, ct, em = _frame(on_run), _frame(control_run), _frame(empty_run)
    model = np.abs(ct - em).sum(-1) > DIFF
    both = model & (np.abs(on - em).sum(-1) > DIFF)
    tint = on[both].mean(0) / ct[both].mean(0)
    bg = ~_dilate(model | (np.abs(on - em).sum(-1) > DIFF) & ~_darkening(on, em), 4)
    lon, lct, lem = on @ LUMA, ct @ LUMA, em @ LUMA
    shadow = bg & (lon < 0.90 * lem) & (lct >= 0.97 * lem)
    calib = bg & (lct < 0.90 * lem)
    res = {"model_px": int(model.sum()), "tint": tuple(round(float(v), 3) for v in tint),
           "shadow_px": int(shadow.sum()),
           "shadow_darkening": round(float((lon[shadow] / lem[shadow]).mean()), 3) if shadow.any() else None,
           "calibration_px": int(calib.sum())}
    if out:
        _sheet(out, on, ct, em, shadow)
    return res


def _darkening(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pixels where ``a`` is ``b`` uniformly scaled down (a shadow on the art), not a different colour
    (a model): channel ratios agree within 0.08 and the luminance drops."""
    r = (a + 1) / (b + 1)
    return (r.max(-1) - r.min(-1) < 0.08) & ((a @ LUMA) < 0.97 * (b @ LUMA))


def _sheet(path: Path, on, ct, em, shadow) -> None:
    """EMPTY | CONTROL | ON, with ON's shadow pixels outlined red in a fourth panel."""
    mark = on.copy()
    mark[shadow] = [255, 0, 0]
    panels = [em, ct, on, mark]
    labels = ["EMPTY (background)", "CONTROL (no MCF)", "ON (donor MCF)", "ON shadow pixels"]
    h, w = on.shape[:2]
    img = Image.new("RGB", (w * 2, h * 2 + 40), "white")
    d = ImageDraw.Draw(img)
    for k, (p, lab) in enumerate(zip(panels, labels)):
        x, y = (k % 2) * w, (k // 2) * (h + 20)
        img.paste(Image.fromarray(p.astype(np.uint8)), (x, y + 20))
        d.text((x + 6, y + 4), lab, fill="black")
    img.save(path)


def keying(probe_run: Path, reshape_run: Path, nokey_run: Path, empty_run: Path) -> dict:
    y0, y1, x0, x1 = ZIDANE_BOX
    em = _frame(empty_run)[y0:y1, x0:x1]
    frames = {"probe": _frame(probe_run), "probe_repeat": _frame(probe_run, "2-spawn-later"),
              "reshape": _frame(reshape_run), "reshape_nokey": _frame(nokey_run)}
    crops = {k: v[y0:y1, x0:x1] for k, v in frames.items()}
    mask = np.logical_and.reduce([np.abs(c - em).sum(-1) > DIFF for c in crops.values()])
    base = crops["probe"][mask].mean(0)
    res = {"player_px": int(mask.sum()), "nokey_predicted": NOKEY_PREDICTED}
    for k in ("probe_repeat", "reshape", "reshape_nokey"):
        res[k] = tuple(round(float(v), 3) for v in crops[k][mask].mean(0) / base)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("objects")
    o.add_argument("on", type=Path)
    o.add_argument("control", type=Path)
    o.add_argument("empty", type=Path)
    o.add_argument("--out", type=Path, default=None)
    k = sub.add_parser("keying")
    for n in ("probe", "reshape", "nokey", "empty"):
        k.add_argument(n, type=Path)
    a = ap.parse_args(argv)
    res = (objects(a.on, a.control, a.empty, a.out) if a.cmd == "objects"
           else keying(a.probe, a.reshape, a.nokey, a.empty))
    for key, v in res.items():
        print(f"{key:18s} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
