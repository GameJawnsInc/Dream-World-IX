import os, sys, json, shutil
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from PIL import Image
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.workspace.shell import pick_palette
from ff9mapkit.workspace.tracedoc import TraceDoc
from ff9mapkit import imagefield as I
KIT = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
S = Path(r"<SCRATCH>/review/v-trace-tab/doc")
shutil.rmtree(S, ignore_errors=True); S.mkdir(parents=True)
class Run:
    def __init__(s, ret=True): s.calls=[]; s.ret=ret
    def __call__(s, argv, **kw): s.calls.append((argv, kw)); return s.ret
photo = S/"photo.png"; Image.new("RGB",(800,600),(90,80,70)).save(photo)
FLOOR=[(60,420),(330,420),(300,250),(90,250)]

print("== T8 retry after a failed first Generate ==")
opened=[]; r=Run(); d=TraceDoc(pick_palette("dark"),KIT,run=r,on_generated=opened.append)
d.load_image(photo); d.canvas._commit_floor(FLOOR); d.id_box.setText("30785")
asked=[]; d._ask_out=lambda: (asked.append(1), str(S/"o"))[1]
d.on_generate(); r.calls[-1][1]["on_finished"](2)
print(" after fail: btn=",d.gen_btn.text()," stamped=",d._stamped," status=",d.status.text()[:40])
d.on_generate()   # user retries
toml=S/"o"/"photo-field"/"PICTURE.field.toml"; toml.write_text('[field]\nid=30785\nname="PICTURE"\n',encoding="utf-8")
r.calls[-1][1]["on_finished"](0)
print(" retry OK: out dialog asked",len(asked),"times | opened:",opened," | status:",d.status.text()[:40])
print("== T8 status after a SUCCESSFUL regenerate ==")
d.on_generate(); r.calls[-1][1]["on_finished"](0); print(" status:", d.status.text()[:40])

print("== T30 busy ==")
r2=Run(ret=False); d=TraceDoc(pick_palette("dark"),KIT,run=r2); d.load_image(photo); d.canvas._commit_floor(FLOOR)
d._ask_out=lambda: str(S/"o2"); before=d.status.text(); d.on_generate()
print(" status changed:", before!=d.status.text(), "| project:", d._project)

print("== T6 drawn region via canvas signal at pitch 26, then pitch 12 ==")
d=TraceDoc(pick_palette("dark"),KIT,run=Run()); d.load_image(photo); d.canvas._commit_floor(FLOOR)
d.tools.set_current("regions"); d.rkind_btns["event"].setChecked(True)
cam=d.canvas.camera(); quad=[I.click_to_world(cam,p) for p in [(150,160),(250,160),(250,130),(150,130)]]
d._on_region_drawn(quad)
print(" pitch26 canvas regions:", len(d._region_rows_cache))
d.pitch.setValue(12); print(" pitch12 canvas regions:", len(d._region_rows_cache), "session", len(d._regions), "gen", d.gen_btn.isEnabled())
cr = getattr(d.canvas, "_regions", None); print(" canvas._regions attr:", None if cr is None else len(cr))
d.pitch.setValue(26); print(" back to 26:", len(d._region_rows_cache))

print("== T12 Clear in regions mode ==")
d.tools.set_current("regions"); print(" clear enabled:", d.clear_btn.isEnabled(), "label:", d.clear_btn.text())
d.on_clear(); print(" floor", len(d._floor), "regions", len(d._regions))

print("== T25 open other image mid-session ==")
d.canvas._commit_floor(FLOOR); print(" before: floor",len(d._floor),"regions",len(d._regions),"hist",len(d._history))
p2=S/"b.png"; Image.new("RGB",(800,600),(9,9,9)).save(p2); d._ask_image=lambda: str(p2); d.on_open()
print(" after Open: floor",len(d._floor),"regions",len(d._regions),"hist",len(d._history),"undo",d.undo_btn.isEnabled())

print("== T13 name/id after new photo ==")
d.name_box.setText("ROOMA"); d.id_box.setText("30500"); d.load_image(photo); print(" ", d.name_box.text(), d.id_box.text())
