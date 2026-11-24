"""Drive the real TraceDoc (offscreen; logic only, no widths judged)."""
import os, json, shutil
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from PIL import Image
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.workspace.shell import pick_palette
from ff9mapkit.workspace.tracedoc import TraceDoc
from ff9mapkit import imagefield as I

KIT = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
S = Path(r"<SCRATCH>/review/v-trace-backend/rc_doc")
shutil.rmtree(S, ignore_errors=True); S.mkdir(parents=True)

class Run:
    def __init__(self): self.calls = []
    def __call__(self, argv, **kw):
        self.calls.append((argv, kw)); return True

def doc():
    r = Run(); d = TraceDoc(pick_palette("dark"), KIT, run=r); return d, r

photo = S / "photo.png"; Image.new("RGB", (800, 600), (90, 80, 70)).save(photo)
FLOOR = [(60, 420), (330, 420), (300, 250), (90, 250)]

print("== 1. failed first Generate leaves the project armed + stamped ==")
d, r = doc(); d.load_image(photo); d.canvas._commit_floor(FLOOR)
d._ask_out = lambda: str(S / "out1")
d.on_generate()
argv, kw = r.calls[-1]
kw["on_finished"](2)            # the CLI refused
print(" project:", d._project, "| stamped:", d._stamped)
print(" button:", d.gen_btn.text(), "| status:", d.status.text())
print(" sidecar exists though build failed:", list((S / "out1").glob("*")))

print("== 2. Clear keeps regions/cut-outs; Clear disabled with regions only ==")
d, r = doc(); d.load_image(photo); d.canvas._commit_floor(FLOOR)
d._regions.append({"kind": "event", "to": 0, "entrance": 0, "message": "m",
                   "quad": [(150, 400), (250, 400), (250, 350), (150, 350)]})
d._fg.append({"contact": (200, 400), "image": None})
d.on_clear()
print(" after Clear: floor", d._floor, "regions", len(d._regions), "fg", len(d._fg),
      "| clear enabled:", d.clear_btn.isEnabled())

print("== 3. pitch change is not undoable ==")
d, r = doc(); d.load_image(photo); d.canvas._commit_floor(FLOOR)
p0 = d.pitch.value(); d.pitch.setValue(40); d.on_undo()
print(" pitch before", p0, "after set 40 + Undo:", d.pitch.value(), "floor", d._floor)

print("== 4. new photo inherits previous project's name + id ==")
d, r = doc(); d.load_image(photo); d.canvas._commit_floor(FLOOR)
d.name_box.setText("ROOMA"); d.id_box.setText("30500")
d._ask_out = lambda: str(S / "out4"); d.on_generate()
photo2 = S / "other.png"; Image.new("RGB", (800, 600), (10, 80, 70)).save(photo2)
d.load_image(photo2); d.canvas._commit_floor(FLOOR); d._ask_out = lambda: str(S / "out4")
d.on_generate()
print(" second project argv id/name:", [a for a in r.calls[-1][0] if a in ("30500", "ROOMA")],
      "out", r.calls[-1][0][r.calls[-1][0].index("--out") + 1])

print("== 5. cut-out classification ==")
big = S / "big.jpg"; Image.new("RGB", (1200, 1600), (1, 2, 3)).save(big)
d, r = doc(); d.load_image(big)
snip = S / "snip_same_aspect.png"; Image.new("RGBA", (120, 160), (255, 0, 0, 255)).save(snip)
d._fg.append({"contact": (200, 400), "image": None}); t = d._attach_cutout(0, snip)
print(" 120x160 snip on a 1200x1600 photo ->", d._fg[0]["kind"], "(teach:", t, ")")
land = S / "land.jpg"; Image.new("RGB", (4000, 3000), (1, 2, 3)).save(land)
d, r = doc(); d.load_image(land)
canv = S / "canvas_frame_cutout.png"; Image.new("RGBA", (1536, 1792), (0, 0, 0, 0)).save(canv)
d._fg.append({"contact": (200, 400), "image": None}); t = d._attach_cutout(0, canv)
f = d._fg[0]; k = d._canvas_scale()
print(" 1536x1792 canvas-frame cut-out on a 4000x3000 photo ->", f["kind"],
      "preview size", round(1536 * k), "x", round(1792 * k), "canvas px")

print("== 6. sidecar project whose photo moved: unopenable despite art/base.png ==")
P = S / "moved"
pp = S / "tmp_photo.png"; Image.new("RGB", (800, 600), (90, 80, 70)).save(pp)
I.build_image_field(pp, FLOOR, P, name="MV", field_id=30500)
(P / "tmp_photo.trace.json").write_text(json.dumps({"image": str(pp), "pitch": 26, "floor": FLOOR,
                                                    "fg": [], "regions": [], "name": "MV", "id": "30500"}))
pp.unlink()
d, r = doc()
d.offer_project(str(P / "MV.field.toml"))
print(" pristine auto-load: image", d._image, "project", d._project, "rejected", d._offer_rejected is not None)
d, r = doc(); d._ask_image = lambda: str(P / "MV.field.toml"); d.on_open()
print(" Open: status:", d.status.text()[:160])

print("== 7. offer: half-loaded tab when walkmesh.obj is missing ==")
P2 = S / "noobj"
I.build_image_field(photo, FLOOR, P2, name="NO", field_id=30500)
(P2 / "walkmesh.obj").unlink()
d, r = doc(); d.offer_project(str(P2 / "NO.field.toml"))
print(" image:", d._image, "| project:", d._project, "| status:", d.status.text()[:90])

print("== 8. EXIF-rotated photo ==")
ex = S / "exif.jpg"
im = Image.new("RGB", (800, 400), (200, 0, 0)); im.paste((0, 0, 255), (0, 0, 400, 400))
exif = im.getexif(); exif[0x0112] = 6; im.save(ex, exif=exif)
d, r = doc(); d.load_image(ex)
print(" img_size", d._img_size, "(viewer would show 400x800 portrait)")

print("== 9. 16-bit greyscale PNG ==")
import numpy as np
arr = (np.ones((600, 800), dtype=np.uint16) * 30000)
g16 = S / "g16.png"; Image.fromarray(arr, mode="I;16").save(g16)
src = Image.open(g16); print(" mode", src.mode, "-> RGB pixel", src.convert("RGB").getpixel((5, 5)),
                             "(true value 30000/65535 = 117/255)")
