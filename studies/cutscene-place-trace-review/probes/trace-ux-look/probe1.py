"""Trace-tab geometry + flow probe (native Qt, WA_DontShowOnScreen via gui_snap's builders)."""
import sys, importlib.util
from pathlib import Path
REPO = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9")
OUT = Path(r"<SCRATCH>/review/trace-ux-look")
spec = importlib.util.spec_from_file_location("gui_snap", REPO / "tools" / "gui_snap.py")
gs = importlib.util.module_from_spec(spec); sys.modules["gui_snap"] = gs; spec.loader.exec_module(gs)
from PySide6.QtCore import QRectF, QPointF
from ff9mapkit import imagefield as IF
from ff9mapkit.scene import cam as _cam

spec2 = importlib.util.spec_from_file_location("_tf", REPO / "ff9mapkit" / "tests" / "test_imagefield.py")
tf = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(tf)
root = OUT / "room"; root.mkdir(parents=True, exist_ok=True)
photo, floor = tf._paint_room(root)
from PIL import Image
cut = root / "pillar_snip.png"; Image.new("RGBA", (40, 180), (68, 60, 82, 255)).save(cut)

class A: pass

def geom(td, tag):
    c = td.canvas
    vp = c.viewport()
    img = c.mapFromScene(QRectF(0, 0, 384, 448)).boundingRect()
    hint = c._hint.geometry()
    full = img.top() >= 0 and img.bottom() <= vp.height() and img.left() >= 0 and img.right() <= vp.width()
    print(f"  [{tag}] canvas {c.width()}x{c.height()} viewport {vp.width()}x{vp.height()} zoom {c._zoom:.3f} "
          f"vbar {c.verticalScrollBar().isVisible()} img-in-vp {img.left()},{img.top()},{img.right()},{img.bottom()} "
          f"fully-visible {full} hint {hint.x()},{hint.y()} {hint.width()}x{hint.height()}")
    # which traced vertices lie under the hint pill (viewport coords)?
    under = []
    for i, p in enumerate(td._floor):
        q = c.mapFromScene(QPointF(*p))
        if hint.adjusted(-5, -5, 5, 5).contains(q):
            under.append(i)
    print(f"      vertices under the hint pill: {under}; status={td.status.text()!r}")

for scale, w, h in ((100, 1280, 850), (150, 1280, 850), (125, 1024, 720), (100, 1024, 720)):
    a = A(); a.theme = "mist"; a.scale = scale; a.guided = "guided"; a.width = w; a.height = h; a.out = str(OUT / "snaps")
    ctx = gs._Ctx(a)
    win = gs._make_win(ctx)
    win.tabs.setCurrentWidget(win.trace_doc); gs._settle(4)
    td = win.trace_doc
    print(f"== scale {scale} window {w}x{h}")
    geom(td, "bare")
    td.load_image(photo)
    td.canvas._commit_floor([(float(x), float(y)) for x, y in floor]); gs._settle(6)
    geom(td, "traced")
    td._ask_cutout = lambda: str(cut)
    td.tools.set_current("cutout")
    td._on_contact(230.0, 320.0); gs._settle(6)
    geom(td, "contact added")
    td.canvas._fit(); gs._settle(3)
    geom(td, "after Ctrl+0 fit")
    td.tools.set_current("regions"); gs._settle(4)
    geom(td, "regions tool")
    print("      ev_msg width", td.ev_msg.width(), "gw_to visible", td.gw_to.isVisible(), td.gw_to.width())
    print("      status label width", td.status.width(), "sizeHint", td.status.sizeHint().width(), "wordWrap", td.status.wordWrap())
    gs._close(win)

# the horizon across the pitch band
from ff9mapkit.scene import guide
vis = []
for p in range(6, 49):
    hy = _cam.horizon_canvas_y(guide.make_camera(float(p), IF.DEFAULT_DISTANCE, fov_x_deg=IF.DEFAULT_FOV))
    vis.append((p, round(hy)))
print("pitch -> horizon y:", vis)
print("DEFAULT_PITCH", IF.DEFAULT_PITCH)
