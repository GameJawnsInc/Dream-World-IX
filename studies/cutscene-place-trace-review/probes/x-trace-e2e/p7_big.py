import time, tracemalloc
from harness import *  # noqa
W = HERE / "p1"
doc, run, _ = make_doc()
for n in ("huge.png", "pano.png", "tiny.png", "rgba.png"):
    t = time.time(); doc.load_image(W / n); dt = time.time() - t
    print(n, "load_image s", round(dt, 2), "pixmap", doc._pixmap.width(), doc._pixmap.height(), "status", doc.status.text()[:50])
doc.load_image(W / "huge.png")
for p in [(60, 430), (320, 430), (250, 240), (130, 240)]:
    click(doc, *p)
tracemalloc.start()
for i in range(120):
    doc._on_floor(list(doc._floor))
print("120 snapshots python-heap KB", round(tracemalloc.get_traced_memory()[1] / 1024), "history", len(doc._history))
