"""DETERMINISTIC probe for the wrapper-ownership bug behind the Workspace GC crashes.

A QGraphicsItem created via scene.addRect() is C++-owned (the scene owns it). Retrieving it
later through scene.items() creates a temporary Python wrapper; when that wrapper dies, a
correct binding drops the wrapper and leaves the C++ item alone. Under the bug, the dying
TEMPORARY wrapper DESTROYS the C++-owned item — a read-only sweep empties the scene, and any
other reference (the scene's own child list mid-teardown, a retained sibling wrapper, a
parentItem() chain) becomes a dangling pointer -> double-free -> 0xC0000005 / 0xC0000374.

Exit 0 + "OK": binding healthy. Exit 1 + "BUG": items were destroyed by the sweep.
Same disease class as PYSIDE-3380 (QAction wrapper destroying the C++-owned QMenu).
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import __version__ as pyside_ver           # noqa: E402
from PySide6.QtCore import QRectF                       # noqa: E402
from PySide6.QtWidgets import QApplication, QGraphicsScene  # noqa: E402


def main():
    app = QApplication.instance() or QApplication([])
    scene = QGraphicsScene()
    for _ in range(10):
        scene.addRect(QRectF(0, 0, 10, 10)).setData(0, "tag")
    n0 = len(scene.items())
    for it in scene.items():         # a READ-ONLY sweep through temporary wrappers
        it.parentItem()
        it.data(0)
    del it
    n1 = len(scene.items())
    print(f"python {sys.version.split()[0]}  PySide6 {pyside_ver}  "
          f"items before sweep: {n0}  after: {n1}")
    if n1 != n0:
        print("BUG: temporary scene.items() wrappers destroyed C++-owned items")
        return 1
    print("OK: temporary wrappers left the scene alone")
    return 0


sys.exit(main())
