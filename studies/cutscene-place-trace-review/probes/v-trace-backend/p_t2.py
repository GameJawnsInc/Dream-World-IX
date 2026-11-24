import shutil, tomllib
from pathlib import Path
from PIL import Image
from ff9mapkit import imagefield as I
from ff9mapkit.editor.model import FieldDoc
S = Path(r"<SCRATCH>/review/v-trace-backend/t2")
shutil.rmtree(S, ignore_errors=True); S.mkdir(parents=True)
img = S / "p.png"; Image.new("RGB", (800, 600), (90, 80, 70)).save(img)
FLOOR = [(60, 420), (330, 420), (300, 250), (90, 250)]
I.build_image_field(img, FLOOR, S / "o", name="M", field_id=30500)
t = S / "o" / "M.field.toml"
doc = FieldDoc.load(t)                       # what the Editor's FIELD_SPEC form edits
doc.data["field"]["location"] = "Mog's Hut"; doc.data["field"]["title"] = "my notes"
doc.save()
print("before:", tomllib.loads(t.read_text(encoding="utf-8"))["field"])
m = I.build_image_field(img, FLOOR, S / "o", name="M", field_id=30500)
print("after :", tomllib.loads(t.read_text(encoding="utf-8"))["field"], "| retaken", m["retaken"], "kept", m["kept"])
