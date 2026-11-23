import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontMetrics, QFontMetricsF
from PySide6.QtCore import Qt
app = QApplication(sys.argv)
labels = ["＋ Step", "Settings", "⧉ Scene", "− Scene", "▶ Storyboard", "＋ Add scene…"]
for fam in ("Segoe UI", "Segoe UI Variable Text", "Inter"):
  for px in (13, 14, 15, 16, 17, 18, 20, 21):
    f = QFont(fam); f.setPixelSize(px)
    fm = QFontMetrics(f); fmf = QFontMetricsF(f)
    out = []
    for t in labels:
        w = fm.horizontalAdvance(t)
        e = fm.elidedText(t, Qt.TextElideMode.ElideRight, w)
        if e != t: out.append(f"{t!r} adv={w} f={fmf.horizontalAdvance(t):.2f} -> {e!r}")
    print(fam, px, out)
