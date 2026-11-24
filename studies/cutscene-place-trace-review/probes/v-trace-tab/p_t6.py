import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from PIL import Image
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.workspace.shell import pick_palette
from ff9mapkit.workspace.tracedoc import TraceDoc
from ff9mapkit import imagefield as I
from ff9mapkit.scene import cam as C
S = Path(r"<SCRATCH>/review/v-trace-tab/doc")
photo=S/"photo.png"
d=TraceDoc(pick_palette("dark"),Path("."),run=lambda *a,**k: True); d.load_image(photo)
d.canvas._commit_floor([(60,420),(330,420),(300,250),(90,250)])
print("h26", C.horizon_canvas_y(d.canvas.camera()))
d.tools.set_current("regions"); d.rkind_btns["event"].setChecked(True)
cam=d.canvas.camera(); quad=[I.click_to_world(cam,p) for p in [(150,140),(250,140),(250,100),(150,100)]]
d._on_region_drawn(quad)
print("26 fed", len(d._region_rows_cache), "canvas", len(d.canvas._regions))
d.pitch.setValue(10)
print("10 h", round(C.horizon_canvas_y(d.canvas.camera()),1), "fed", len(d._region_rows_cache), "canvas", len(d.canvas._regions), "gen", d.gen_btn.isEnabled())
print("status", d.status.text())
# vertices above horizon: do they stay in canvas?
d2=TraceDoc(pick_palette("dark"),Path("."),run=lambda *a,**k: True); d2.load_image(photo)
d2.canvas._commit_floor([(60,420),(330,420),(300,120),(90,120)]); d2.pitch.setValue(10)
print("floor verts canvas:", len(d2.canvas._floor) if hasattr(d2.canvas,"_floor") else "?", d2.status.text())
