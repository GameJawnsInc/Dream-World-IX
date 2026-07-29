"""The smallest shape found that still corrupts the heap (Python 3.14.4 + PySide6 6.11.1,
offscreen): a bare QGraphicsScene, plain rect items, and repeated fresh scene.items()
retrieval sweeps interleaved with scene.clear() rebuilds. No QGraphicsView, no cursors, no
child items, no pixmaps, no text, no forced gc.collect — delta-debugged down from the full
Workspace mirror (repro_scene_items_cursor_gc.py; the bisect axes are repro_bisect.py).

Crashes either mid-run (0xC0000005 access violation) or at interpreter shutdown
(0xC0000374 heap corruption) depending on allocation pattern.

Knobs: ROUNDS (20) · NITEMS (16) · CYCLES sweeps-per-round (3; 1 = no crash observed) ·
TOUCH "pd" = parentItem()+data() reads per fresh wrapper · PARK 1 keep each round's scene
alive (0 = drop to GC).
"""

import faulthandler
import gc
import os

faulthandler.enable()
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF                       # noqa: E402
from PySide6.QtWidgets import QApplication, QGraphicsScene  # noqa: E402

ROUNDS = int(os.environ.get("ROUNDS", "20"))
NITEMS = int(os.environ.get("NITEMS", "16"))
CYCLES = int(os.environ.get("CYCLES", "3"))
TOUCH = os.environ.get("TOUCH", "pd")
PARK = os.environ.get("PARK", "1") == "1"
PARKED = []


def build(scene, retained):
    for i in range(NITEMS):
        it = scene.addRect(QRectF(0, 0, 10, 10))
        it.setData(0, "tag")
        if i % 2:                    # half retained, half left wrapper-less (the app's mix)
            retained.append(it)


def sweep(scene):
    for it in scene.items():         # FRESH shiboken wrappers for the unretained half
        if "p" in TOUCH:
            it.parentItem()
        if "d" in TOUCH:
            it.data(0)


def main():
    app = QApplication.instance() or QApplication([])
    for n in range(ROUNDS):
        scene = QGraphicsScene()
        retained = []
        for _ in range(CYCLES):
            build(scene, retained)
            sweep(scene)
            retained = []            # refs dropped BEFORE the clear (the app's rebuild order)
            scene.clear()
        build(scene, retained)
        sweep(scene)
        if PARK:
            PARKED.append((scene, retained))
        print(f"round {n + 1}/{ROUNDS} ok", flush=True)
    print("ALL ROUNDS DONE", flush=True)


main()
