import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
app = QApplication([])
from ff9mapkit.workspace import placedoc as P
from ff9mapkit.workspace.shell import pick_palette
from ff9mapkit.scene import guide
cam = guide.make_camera(26.0, 3000.0, fov_x_deg=42.0)
tris = [((-900, 0, 600), (900, 0, 600), (900, 0, 2400)), ((-900, 0, 600), (900, 0, 2400), (-900, 0, 2400))]
NC = {"n": 2}
def fake(path, ci=0):
    ci = max(0, min(int(ci), NC["n"] - 1))
    return {"donor": None, "source": ("project", str(path)), "cam_index": ci, "n_cams": NC["n"],
            "cam": cam, "png": None, "tris": tris, "floors": [0, 0]}
P.build_surface_from_project = fake
d = P.PlaceDoc(pick_palette("mist"), on_edit=lambda m, l: None)
d.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
def wait(pred, t=5):
    t0 = time.time()
    while not pred() and time.time() - t0 < t:
        app.processEvents(); time.sleep(0.02)
    app.processEvents()
# project 1: room A with two cameras; user picks camera 1 via the combo
d.show_field("A", {"field": {"id": 30001}}, Path("C:/p1/A.field.toml"))
d.on_load(); wait(lambda: d._bundle() is not None)
d.cam_box.setCurrentIndex(1); wait(lambda: d._bundle() is not None)
print("p1 cam pick:", d._cam_index(), "applied cam:", d._bundle()["cam_index"])
# project 2: another room named A, single camera
NC["n"] = 1
d.show_field("A", {"field": {"id": 30002}}, Path("C:/p2/A.field.toml"))
for k in range(2):
    d.on_load(); wait(lambda: d._loading is None)
    print(f"Load #{k+1}: applied={d._bundle() is not None} bundles keys cams={[c for (s,c) in d._bundles if s[1].startswith('C:'+chr(92)+'p2')]}"
          f" status={d.status.text()[:60]!r} cam_box visible={d.cam_box.isVisible()}")
