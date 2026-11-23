import sys, os, tempfile
from pathlib import Path
os.environ["FF9MAPKIT_NO_THUMBS"]="1"
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
SCR = Path(r"<SCRATCH>/review/place-code")
tmp = Path(tempfile.mkdtemp(dir=SCR))
from ff9mapkit import prefs, provision
prefs._path = lambda: tmp/"prefs.json"
_real = provision._user_dir
provision._user_dir = lambda sub: (tmp/"cfg") if sub=="config" else _real(sub)
from PySide6.QtWidgets import QApplication
app = QApplication([])
from ff9mapkit.workspace import shell
from ff9mapkit.workspace.shell import pick_palette
win = shell.Workspace(pick_palette("dark"))
p = tmp/"X.field.toml"
z = lambda x: f"[[{x},0],[{x+100},0],[{x+100},100],[{x},100]]"
p.write_text('[field]\nid = 30999\nname = "X"\narea = 11\nsource_field = 351\n'
  f'[[gateway]]\nname="g0"\nto=100\nzone={z(0)}\n'
  f'[[gateway]]\nname="g1"\nto=101\nzone={z(200)}\n'
  f'[[gateway]]\nname="g2"\nto=102\nzone={z(400)}\n', encoding="utf-8")
assert win.open_field(p)
win._open_editor("X", "object", "gateway:1")
ctx = win._save_ctx; print("mounted form:", ctx["key"], "idx", ctx["idx"])
# the author edits the g1 form's 'to' (simulated through its getter) and does NOT navigate
g = dict(ctx["getters"]); g["to"] = (lambda: 555) if not isinstance(ctx["mounted"]["to"], str) else (lambda: "555")
ctx["getters"] = g
win.tabs.setCurrentWidget(win.place_doc)        # tab change: no commit
pd = win.place_doc
from ff9mapkit.scene import guide
q=[((-1000.0,0.0,500.0),(1000.0,0.0,500.0),(1000.0,0.0,2500.0)),((-1000.0,0.0,500.0),(1000.0,0.0,2500.0),(-1000.0,0.0,2500.0))]
pd._bundles[(("real",351),0)]={"donor":351,"source":("real",351),"cam_index":0,"n_cams":1,"cam":guide.make_camera(26.0,3000.0,fov_x_deg=42.0),"png":None,"tris":q,"floors":[0,0]}
pd._apply_bundle(pd._bundles[(("real",351),0)], refit=True)
i0 = [r["i"] for r in pd._region_rows_cache if r["index"]==0][0]
pd._on_region_deleted(i0)                        # delete g0 on the Place tab
print("after Place delete:", [(gw["name"], gw["to"]) for gw in win._doc("X").data["gateway"]])
win.tabs.setCurrentWidget(win.doc_scroll)
win._commit_active_ck()                          # the author's next navigation folds the form
print("after the Editor fold:", [(gw["name"], gw["to"], gw["zone"][0]) for gw in win._doc("X").data["gateway"]])
win.hide()
