"""Probe 4: odd images through the tab's own ingest, keyboard reachability, id band edges."""
import shutil
import numpy as np
from harness import *  # noqa
from PIL import Image, ImageStat

W = HERE / "p4"
shutil.rmtree(W, ignore_errors=True)
W.mkdir()
def L(*a):
    print(" ".join(str(x) for x in a), flush=True)

# 16-bit greyscale PNG with full-range values (what GIMP/Photoshop/raw converters export)
arr = (np.linspace(0, 1, 800)[None, :].repeat(600, 0) * 65535 * 0.5 + 8000).astype(np.uint16)
im16 = Image.fromarray(arr)
im16.save(W / "grey16.png")
L("16-bit source mode", Image.open(W / "grey16.png").mode, "8-bit-equivalent mean", round(float(arr.mean()) / 257, 1))
L("tab/build ingest convert('RGB') mean", [round(v, 1) for v in ImageStat.Stat(Image.open(W / "grey16.png").convert("RGB")).mean])
doc, run, _ = make_doc()
doc.load_image(W / "grey16.png")
img = doc._pixmap.toImage()
px = [img.pixelColor(x, 400).red() for x in (10, 200, 400, 700)]
L("tab canvas pixels across the 16-bit gradient", px)
r = subprocess.run([sys.executable, "-m", "ff9mapkit", "image-field", str(W / "grey16.png"), "--floor",
                    "60,440 324,440 260,200 124,200", "--out", str(W / "o16"), "--id", "30058"], cwd=KIT,
                   capture_output=True, env=CHILD_ENV)
L("CLI on 16-bit exit", r.returncode, "base mean",
  [round(v, 1) for v in ImageStat.Stat(Image.open(W / "o16" / "art" / "base.png")).mean])

# keyboard: the focus chain of the tab with an image loaded and a traced floor
for p in [(60, 430), (320, 430), (250, 240), (130, 240)]:
    click(doc, *p)
seen = []
doc.open_btn.setFocus(); app.processEvents()
w = app.focusWidget()
for _ in range(40):
    nm = (w.accessibleName() or getattr(w, "text", lambda: "")() or type(w).__name__) if w else None
    seen.append(f"{type(w).__name__}:{nm}")
    w.focusNextChild() if False else QTest.keyClick(w, Qt.Key.Key_Tab)
    app.processEvents()
    w = app.focusWidget()
    if w is doc.open_btn:
        break
L("focus chain:", seen)
# keyboard on the canvas: arrows / Delete / Menu key with a vertex 'selected'?
doc.canvas.setFocus(); n0 = list(doc._floor)
for key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace, Qt.Key.Key_Right, Qt.Key.Key_Return, Qt.Key.Key_Space):
    QTest.keyClick(doc.canvas, key); app.processEvents()
L("canvas keys changed the floor?", doc._floor != n0)
QTest.keyClick(doc.canvas, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier); app.processEvents()
L("Ctrl+Z on the canvas (no shell) changed the floor?", doc._floor != n0)

from ff9mapkit import pack
for v in ["3999", "4000", "9000", "9012", "9013", "9899", "9900", "29999", "30000", "32767", "32768", " 30058 ", "3e4"]:
    try:
        L("check_custom_id", repr(v), "->", pack.check_custom_id(v))
    except Exception as e:
        L("check_custom_id", repr(v), "-> refused:", str(e)[:70])
d = doc
L("gw_to range", d.gw_to.minimum(), d.gw_to.maximum())
