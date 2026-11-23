"""A region whose corner goes above the horizon after a pitch change: still on the canvas?"""
import os; os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from PIL import Image
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.workspace.shell import pick_palette
from ff9mapkit.workspace.tracedoc import TraceDoc
from ff9mapkit.scene import cam as C
S = Path(r"<SCRATCH>/review/trace-code/rp"); S.mkdir(parents=True, exist_ok=True)
ph = S / "p.png"; Image.new("RGB", (800, 600), (9, 9, 9)).save(ph)
d = TraceDoc(pick_palette("dark"), Path("."), run=lambda *a, **k: True)
d.load_image(ph)
d.canvas._commit_floor([(60, 420), (330, 420), (300, 250), (90, 250)])
d.rkind_btns["event"].setChecked(True)
d._regions.append({"kind": "event", "to": 0, "entrance": 0, "message": "m",
                   "quad": [(150, 160), (250, 160), (250, 120), (150, 120)]})
d._refresh_regions(); d._refresh()
print("pitch", d.pitch.value(), "regions fed to canvas:", len(d.canvas._regions if hasattr(d.canvas, "_regions") else d._region_rows_cache))
for p in (12, 8, 6):
    d.pitch.setValue(p)
    print("pitch", p, "horizon y", round(C.horizon_canvas_y(d.canvas.camera()), 1),
          "| rows fed:", len(d._region_rows_cache), "| session regions:", len(d._regions),
          "| gen enabled:", d.gen_btn.isEnabled())
print("status:", d.status.text())
print("tooltip:", d.gen_btn.toolTip())
