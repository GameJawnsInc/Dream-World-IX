import sys, math
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from PySide6.QtGui import QFontMetricsF, QFont
from PySide6.QtCore import Qt
app = QApplication(sys.argv)
from ff9mapkit.workspace import widgets, style
from ff9mapkit.editor.theme import pick_palette
pal = pick_palette("dark")
try: app.setStyleSheet(style.qss(pal))
except Exception as e: print("qss", e)
for pt in (9, 10, 11, 12, 13):
    f = app.font(); f.setPointSizeF(pt); app.setFont(f)
    host = QWidget(); host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    h = QHBoxLayout(host); bs = []
    for t in ("＋ Step", "Settings", "⧉ Scene", "− Scene", "▶ Storyboard"):
        b = widgets.ElideButton(t); b.setProperty("role", "quiet"); h.addWidget(b); bs.append(b)
    h.addStretch(1); host.resize(1400, 60); host.show(); app.processEvents()
    out=[]
    for b in bs:
        fmf = QFontMetricsF(b.font())
        out.append(f"{b.accessibleName()!r}->{b.text()!r} w{b.width()} hint{b.sizeHint().width()} f{fmf.horizontalAdvance(b.accessibleName()):.2f}")
    print(pt, out)
    host.hide(); host.deleteLater()
