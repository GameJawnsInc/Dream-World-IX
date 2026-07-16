"""SHOT: tracking, rendered before it is built -- PUNCH P1's own condition.

PUNCH's honest note: "Nobody has rendered a tracked caption beside an untracked one and looked. Do that
before P1 ships, not after." This study's FORM LESSON says why that is not ceremony: statistics reproduce
a thing's measured properties and never its look. The optical axis is MEASURED (and real -- Segoe is flat
at 0.500, the six Sitka cuts step 0.503 -> 0.430). Whether tracking HELPS is not a measurement.

The claim under test: "the 26px nameplate tracks at 0 and the 12px caption tracks at 0; both are wrong,
in opposite directions" -- display type wants tightening, small text wants opening.

Two things the numbers already settled and this shot does not re-litigate:
  * P2 (a small optical cut for captions) is DEAD: Sitka Small buys +0.5% x-height for +17.9% width.
    Segoe UI is already a UI face drawn for small sizes and sits at 0.500 vs Sitka Small's 0.503.
  * The app already spends the family correctly at the top: 40px wordmark = Sitka Banner (0.430), 26px
    nameplate = Sitka Display (0.439). The display end is done; only tracking is unspent.

NATIVE ONLY -- offscreen stubs the font DB. Fusion, because the app forces Fusion.

Run:  py studies/gui-aesthetics/evidence/shot_punch.py
Out:  evidence/punch_{palette}.png
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtGui import QColor, QFont, QImage, QPainter                    # noqa: E402
from PySide6.QtWidgets import QApplication                                   # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"
app.setStyle("fusion")

from ff9mapkit.editor import theme                                           # noqa: E402

NAME = "Build & Deploy"
CAP = "Quick and reversible. Your field's own id is overridden — play it with F6 → Warp."
W, ROW = 980, 52


def draw(mode):
    pal = theme.derive(dict(theme.THEMES[mode]))
    tracks_name = (0.0, -0.25, -0.5, -0.75)
    tracks_cap = (0.0, 0.15, 0.3, 0.5)
    h = ROW * (len(tracks_name) + len(tracks_cap)) + 90
    img = QImage(W, h, QImage.Format.Format_RGB32)
    img.fill(QColor(pal["surface_2"]))                  # a card ground: where both of these actually live
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    hd = QFont("Segoe UI"); hd.setPixelSize(12); hd.setWeight(QFont.Weight.DemiBold)
    p.setFont(hd); p.setPen(QColor(pal["muted"]))
    p.drawText(16, 22, "THE CROWN — 26px Sitka Display. A display cut is already drawn tight; does it want MORE?")
    y = 44
    for t in tracks_name:
        f = QFont("Sitka Display"); f.setPixelSize(26); f.setWeight(QFont.Weight(400))
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, t)
        p.setFont(f); p.setPen(QColor(pal["text"]))
        p.drawText(150, y + 26, NAME)
        p.setFont(hd); p.setPen(QColor(pal["muted"]))
        p.drawText(16, y + 24, f"track {t:+.2f}" + ("   (ships)" if t == 0 else ""))
        y += ROW

    y += 18
    p.setFont(hd); p.setPen(QColor(pal["muted"]))
    p.drawText(16, y, "THE HINT — 12px Segoe, $muted. Small text on a card: does opening it help or just stretch it?")
    y += 22
    for t in tracks_cap:
        f = QFont("Segoe UI"); f.setPixelSize(12)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, t)
        p.setFont(f); p.setPen(QColor(pal["muted"]))
        p.drawText(150, y + 16, CAP)
        p.setFont(hd); p.setPen(QColor(pal["muted"]))
        p.drawText(16, y + 16, f"track {t:+.2f}" + ("   (ships)" if t == 0 else ""))
        y += ROW - 12
    p.end()
    dst = HERE / f"punch_{mode}.png"
    img.save(str(dst))
    return dst


for mode in ("mist", "light"):
    print(f"  {draw(mode).name}")
print("\nJudge the CROWN first: it is the one rung where a display face plausibly wants tightening, and it")
print("is the app's identity surface. Judge the HINT second and be sceptical -- Segoe at 12px is already")
print("drawn open for exactly this size, so tracking it may only cost measure.")
