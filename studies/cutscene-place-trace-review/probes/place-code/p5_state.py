import sys, os
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtTest import QTest
app = QApplication([])
from ff9mapkit.workspace import placedoc as P
from ff9mapkit.workspace.shell import pick_palette
from ff9mapkit.scene import guide
calls=[]
d = P.PlaceDoc(pick_palette("mist"), on_edit=lambda m,l: calls.append((m,l)))
d.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True); d.resize(900,700); d.show(); app.processEvents()
def quad(y, z0=600, z1=2400, x=900):
    a,b,c,e=(-x,y,z0),(x,y,z0),(x,y,z1),(-x,y,z1); return [(a,b,c),(a,c,e)]
cam = guide.make_camera(26.0, 3000.0, fov_x_deg=42.0)
# ---- 1) stacked floors: the chosen floor is not recorded
tris = quad(0.0) + quad(-300.0)          # render frame: floor1 is 300 above floor0
B = {"donor":351,"source":("real",351),"cam_index":0,"n_cams":1,"cam":cam,"png":None,"tris":tris,"floors":[0,0,1,1]}
data={"field":{"source_field":351}}
d.show_field("FORK", data, Path("C:/x/FORK.field.toml")); d._bundles[(("real",351),0)]=B; d._apply_bundle(B, refit=True); app.processEvents()
from ff9mapkit import imagefield as IF
from ff9mapkit.scene import cam as _C
px = _C.to_canvas((0.0, -300.0, 1500.0), cam); print("px", px)
hit = IF.click_to_surface(cam, tris, px)
rows=[{"pos":p,"xz":(p[0],p[2]),"floor":B["floors"][ti],"tri":ti,"s":s} for s,ti,p in hit["hits"]]
print("stacked rows:", [(r["floor"], round(r["pos"][1]), [round(v) for v in r["xz"]]) for r in rows])
d._choose_hit = lambda rr: rr[1]          # author picks the BEHIND floor
pay=dict(rows[0]); pay["stacked"]=rows
d._on_surface_clicked(pay)
print("written npc:", data["npc"][-1], "| status:", d.status.text()[:70])
d.show_field("FORK", data, Path("C:/x/FORK.field.toml"))
print("marker y:", [m["pos"][1] for m in d.canvas._markers], "(chosen floor y was", rows[1]["pos"][1], ")")
# ---- 2) same member NAME, different project/path: stale surface stays armed
calls.clear()
data2={"field":{"id":30701}}
d.show_field("FORK", data2, Path("C:/other/FORK.field.toml"))
print("after re-feed w/ other path: source", d._source, "bundle", d._bundle() is not None,
      "| canvas place_mode", d.canvas._place_mode, "| surface tris", len(d.canvas._surface_tris))
wpt = d.canvas.world_to_click((0.0, 1500.0))
QTest.mouseClick(d.canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(round(wpt.x()), round(wpt.y())))
print("click on the stale surface ->", calls, data2.get("npc"))
# ---- 3) verbatim tooltip leaks to a non-verbatim field
d.show_field("V", {"verbatim_eb":{"donor":351}}, Path("C:/x/V.field.toml"))
d.show_field("N", {"field":{"source_field":351}}, Path("C:/x/N.field.toml"))
print("non-verbatim spawn enabled:", d.mode_btns["spawn"].isEnabled(), "tooltip:", d.mode_btns["spawn"].toolTip()[:60])
# ---- 4) a blocked field after a loaded one keeps place mode?
d.show_field("FORK", data, Path("C:/x/FORK.field.toml")); d._apply_bundle(B, refit=True)
ex = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/examples/vivi-hut/hut_int.field.toml")
d.show_field("FORK", {"field":{"source_field":351}}, ex)
print("same member now blocked:", bool(d._blocked), "| canvas place_mode still:", d.canvas._place_mode, "| tris", len(d.canvas._surface_tris))
