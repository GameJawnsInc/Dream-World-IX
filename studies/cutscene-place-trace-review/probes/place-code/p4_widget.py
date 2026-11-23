import sys, time, os, threading, tomllib
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
app = QApplication([])
from ff9mapkit.workspace import placedoc as P
from ff9mapkit.workspace.shell import pick_palette
pal = pick_palette("mist") if True else None
calls=[]
d = P.PlaceDoc(pal, on_edit=lambda m,l: calls.append((m,l)))
d.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
room = Path(r"<SCRATCH>/review/place-code/room/A/a.field.toml")
data = tomllib.loads(room.read_text(encoding="utf-8"))
def wait(pred, t=20):
    t0=time.time()
    while not pred() and time.time()-t0<t:
        app.processEvents(); time.sleep(0.02)
d.show_field("A", data, room)
d.on_load(); wait(lambda: d._bundle() is not None)
b1 = d._bundle(); xs=[v[0] for t in b1["tris"] for v in t]
print("loaded: tris", len(b1["tris"]), "x-extent", min(xs), max(xs), "tool armed place:", d.canvas._place_mode)
# --- (a) the walkmesh changes on disk (e.g. Trace/floorplan regenerate); Load again
wm = room.parent/"walkmesh.obj"; orig = wm.read_text()
lines=[]
for ln in orig.splitlines():
    if ln.startswith("v "):
        p=ln.split(); lines.append(f"v {float(p[1])*0.5} {p[2]} {p[3]}")
    else: lines.append(ln)
wm.write_text("\n".join(lines)+"\n")
d.on_load(); app.processEvents()
b2 = d._bundle(); xs2=[v[0] for t in b2["tris"] for v in t]
print("after disk change + Load: same bundle object?", b2 is b1, "x-extent", min(xs2), max(xs2))
fresh = P.build_surface_from_project(room); xs3=[v[0] for t in fresh["tris"] for v in t]
print("a fresh build would give x-extent", min(xs3), max(xs3))
wm.write_text(orig)
# --- (b) stale failure / loading-flag across a field switch
ev = threading.Event()
real = P.build_surface_from_project
def slow(path, ci=0):
    if "a.field" in str(path): ev.wait(5); raise RuntimeError("A blew up")
    time.sleep(0.5); return real(path, ci)
P.build_surface_from_project = slow
d._bundles.clear()
d.show_field("A", data, room); d.on_load()
roomB = room.parent.parent/"B"/"b.field.toml"; dataB = tomllib.loads(roomB.read_text(encoding="utf-8"))
d.show_field("B", dataB, roomB)
print("after switch to B: load_btn enabled", d.load_btn.isEnabled(), "_loading", d._loading)
d.on_load()   # B in flight
ev.set(); wait(lambda: "Could not" in d.status.text(), 3)
print("member", d._member, "status:", d.status.text()[:90], "| load_btn enabled while B in flight:", d.load_btn.isEnabled(), "_loading", d._loading)
wait(lambda: d._bundle() is not None, 10)
print("B applied:", d._bundle() is not None, "status:", d.status.text()[:80])
