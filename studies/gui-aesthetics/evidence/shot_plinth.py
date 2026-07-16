"""SHOT: PLINTH -- the front door learns to measure itself.

Two questions, and they are different:

  1. THE RAMP-JOIN (a change at 100%, so it needs an eye). The band kept private 11px and 13px faces. After
     QUARTO P1 raised the caption floor to 12, the hero was the ONLY surface in the app still shipping 11px
     text -- the front door wearing exactly the small type the user asked us to fix everywhere else. They
     now spend `type_caption` / `type_body` like everything else: 11 -> 12 and 13 -> 14.

     The band's GEOMETRY does not move for this: band_metrics(d, 100) returns the shipped tuple identically
     (asserted). Only the two faces change. So this strip is the honest delta and nothing else.

  2. THE SCALE (the defect CALIBRE created). The band paints via QPainter, so no stylesheet reaches it: at
     150% every tab grew and the front door sat at exactly 156px. `shell._apply_text_scale` was ALREADY
     calling the hero on every scale change -- the scale just never arrived.

The 100% tuples are the DESIGN, not a derivation: 106.5 and 94.5 are half-pixel rule positions chosen by
eye against a 40px serif. band_metrics SCALES that composition rather than recomputing it from metrics,
which is why 100% is identity by construction rather than by arithmetic luck.

NATIVE ONLY -- offscreen stubs the font DB. Fusion, because the app forces Fusion (shell.py:129).

Run:  py studies/gui-aesthetics/evidence/shot_plinth.py
Out:  evidence/plinth_ramp_{palette}.png   -- the 100% delta (the eye's call)
      evidence/plinth_scale_{palette}.png  -- 100 / 125 / 150, the defect fixed
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
from ff9mapkit.workspace import hero as H                                    # noqa: E402
from ff9mapkit.workspace import style                                        # noqa: E402

W = 1000


def band(pal, scale, faces=None):
    """Grab the real HeroBand. `faces` overrides band_type -- used ONLY to reconstruct the old 11/13."""
    real = H.band_type
    if faces is not None:
        H.band_type = lambda _s=100: faces
    try:
        b = H.HeroBand(pal, scale=scale)
        b.setStyleSheet(style.qss(pal, "comfortable", scale))
        b.resize(W, b.height())
        b._draw = 1.0                                  # at rest -- not mid-signature
        img = b.grab().toImage()
        b.deleteLater()
        app.processEvents()
        return img
    finally:
        H.band_type = real


def strip(pal, rows, dst):
    lab = 30
    h = sum(i.height() + lab for _, i in rows)
    out = QImage(W, h, QImage.Format.Format_RGB32)
    out.fill(QColor(pal["bg"]))
    p = QPainter(out)
    y = 0
    for tag, img in rows:
        f = QFont("Segoe UI"); f.setPixelSize(12); f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f); p.setPen(QColor(pal["muted"]))
        p.drawText(10, y + 19, tag)
        p.drawImage(0, y + lab, img)
        y += img.height() + lab
    p.end()
    out.save(str(dst))
    return dst


for mode in ("mist", "light"):
    pal = theme.derive(dict(theme.THEMES[mode]))

    # 1. the ramp-join, at 100%, geometry frozen -- the ONLY delta is the two faces
    rows = [
        ("BEFORE — overline 11px, status 13px (the app's last 11px text)", band(pal, 100, faces=(11, 40, 13))),
        ("AFTER  — overline 12px, status 14px (the ramp: type_caption / type_body)", band(pal, 100)),
    ]
    print(f"  {strip(pal, rows, HERE / f'plinth_ramp_{mode}.png').name}")

    # 2. the scale -- what the dial could not reach until now
    rows = []
    for pct in (100, 125, 150):
        m = H.band_metrics("comfortable", pct)
        rows.append((f"text size {pct}%  —  band {int(m[0])}px, wordmark {H.band_type(pct)[1]}px"
                     + ("   (was 156px / 40px at EVERY scale)" if pct != 100 else ""),
                     band(pal, pct)))
    print(f"  {strip(pal, rows, HERE / f'plinth_scale_{mode}.png').name}")

print("\n1) plinth_ramp: judge whether +1px on the two small rows is right. Geometry is frozen; if this")
print("   looks like nothing, that is the correct outcome -- it means the front door quietly joined the")
print("   ramp without disturbing a composition someone chose by eye.")
print("2) plinth_scale: the band, the wordmark, the mark and the mist all grow as ONE thing.")
