import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from PySide6.QtCore import Qt
app = QApplication(sys.argv)
from ff9mapkit.workspace import widgets
host = QWidget(); host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
h = QHBoxLayout(host); h.setSpacing(10); h.setContentsMargins(0,0,0,0)
labels = ["＋ Step", "Settings", "⧉ Scene", "− Scene", "▶ Storyboard"]
bs = [widgets.ElideButton(t) for t in labels]
for b in bs: h.addWidget(b)
host.show()
for W in (700, 520, 480, 520, 700):
    host.resize(W, 40); app.processEvents(); app.processEvents()
    print(W, [(b.text(), b.width(), b.sizeHint().width(), b.minimumSizeHint().width()) for b in bs])
