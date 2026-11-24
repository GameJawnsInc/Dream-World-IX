import sys, math
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QSizePolicy
from PySide6.QtGui import QFontMetricsF
from PySide6.QtCore import Qt
app = QApplication(sys.argv)
from ff9mapkit.workspace import widgets, style
from ff9mapkit.editor.theme import pick_palette
app.setStyleSheet(style.qss(pick_palette("dark")))
host = QWidget(); host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
h = QHBoxLayout(host); ls=[]
for t in ("＋ Step", "⧉ Scene", "plays at beat 100 · cast: Cid, Mira", "scene #0"):
    l = widgets.ElideLabel(t); l.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed); h.addWidget(l); ls.append(l)
h.addStretch(1); host.resize(1400,60); host.show(); app.processEvents()
for l in ls: print(repr(l.fullText()), "->", repr(l.text()), l.width(), l.sizeHint().width())
# patched ElideButton test: ceil
from PySide6.QtCore import QSize
class Fixed(widgets.ElideButton):
    def sizeHint(self):
        sh = super(widgets.ElideButton, self).sizeHint()
        return QSize(math.ceil(QFontMetricsF(self.font()).horizontalAdvance(self._full)) + 1 + self._pad(), sh.height())
host2 = QWidget(); host2.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True); h2=QHBoxLayout(host2); bs=[]
for t in ("＋ Step", "⧉ Scene", "− Scene"):
    b=Fixed(t); b.setProperty("role","quiet"); h2.addWidget(b); bs.append(b)
h2.addStretch(1); host2.resize(1400,60); host2.show(); app.processEvents()
print("fixed:", [(b.text(), b.width()) for b in bs])
