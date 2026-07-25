"""Calibrate FIND_TINT_FLOOR by RENDER -- the quiet find tier, swept, cropped to the log, upscaled 4x.

WHY A SWEEP AND NOT A NUMBER. `_find_token` inherited `_selection_token`'s 20/255 floor, and 20 was
calibrated against a different GROUND (a fill vs hover on a mid-grey surface). At 20 the mist render painted
the quiet match -- 339 measured px of the `find_bg` token, so the mechanism was correct -- and it still did
not read as a match on a near-black well. So the floor is re-calibrated here, the same way EDGE_T was: by
looking, at a magnification where a 13px mono glyph's background is actually judgeable.

THE UPSCALE IS NEAREST-NEIGHBOUR. A smooth upscale invents intermediate colours, which is precisely what a
"can you see this fill" judgement must not have -- and downscaled review is how this study missed a 1.215
delta it could measure exactly (`shot_ladder`'s note: sample the button, don't squint at the screenshot).

Run:  py studies/gui-aesthetics/evidence/shot_find_tier.py [--themes mist,solarized-light,light]
Writes shot_find-<theme>-floor<N>.png into tools/scroll_out/gui_snaps/.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(REPO / "tools"))

os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    del os.environ["QT_QPA_PLATFORM"]          # native only: offscreen's stub font DB lies about every width

import gui_snap as G                                                   # noqa: E402  (owns the prefs pin + Qt app)
from PySide6.QtCore import Qt                                          # noqa: E402
from ff9mapkit.editor import theme                                     # noqa: E402


def shoot(theme_key: str, floor: int, out: Path) -> Path:
    """One render of the console at ``floor``, cropped to the Output log, 4x nearest-neighbour."""
    theme.FIND_TINT_FLOOR = floor          # the constant IS the lever; nothing else in the app moves
    args = argparse.Namespace(theme=theme_key, scale=100, guided="guided", width=1280, height=850,
                              out=str(out), campaign=None, thumb_source=None)
    ctx = G._Ctx(args)
    win = G._make_win(ctx)
    G._seed_console(win)
    win._raise_console()
    win._open_find("wrote")
    G._settle(8)
    # Crop to the LOG WIDGET, not the panel: the subject is a fill under mono glyphs, and the surrounding
    # chrome only invites the eye to judge the wrong thing.
    img = win.output.grab().toImage()
    big = img.scaled(img.width() * 4, img.height() * 4, Qt.AspectRatioMode.IgnoreAspectRatio,
                     Qt.TransformationMode.FastTransformation)
    path = out / f"shot_find-{theme_key}-floor{floor}.png"
    big.save(str(path))
    d = theme.derive(dict(theme.THEMES[theme_key]))
    rgb = [int(d["find_bg"][i:i + 2], 16) for i in (1, 3, 5)]
    well = [int(d["log_bg"][i:i + 2], 16) for i in (1, 3, 5)]
    print(f"  {theme_key:16} floor {floor:3d} -> find_bg {d['find_bg']}  "
          f"d(well)={max(abs(a - b) for a, b in zip(rgb, well)):3d}  {path.name}")
    G._close(win)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # The three that matter: mist is the DEFAULT theme and the deepest well; solarized-light is where the
    # quiet tier's INK was sub-AA (4.42) and its well is cream, the opposite direction; light is the flattest.
    ap.add_argument("--themes", default="mist,solarized-light,light")
    ap.add_argument("--floors", default="20,32,44,56")
    ap.add_argument("--out", default=str(REPO / "tools" / "scroll_out" / "gui_snaps"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    orig = theme.FIND_TINT_FLOOR
    try:
        for t in a.themes.split(","):
            for f in (int(x) for x in a.floors.split(",")):
                shoot(t.strip(), f, out)
    finally:
        theme.FIND_TINT_FLOOR = orig
    print("\nJudge the 4x crops: the CURRENT match is the loud accent; every OTHER match must read as")
    print("marked without competing with it. Too low = invisible; too high = a second current match.")


if __name__ == "__main__":
    main()
