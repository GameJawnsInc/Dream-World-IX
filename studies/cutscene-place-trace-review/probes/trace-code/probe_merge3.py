"""Three regenerates over hand content: arrivals, a scalar, a hand layer, a hand subtable."""
import shutil, tomllib
from pathlib import Path
from PIL import Image
from ff9mapkit import imagefield as I
S = Path(r"<SCRATCH>/review/trace-code/merge3")
shutil.rmtree(S, ignore_errors=True); S.mkdir(parents=True)
img = S / "p.png"; Image.new("RGB", (800, 600), (9, 9, 9)).save(img)
F = [(60, 420), (330, 420), (300, 250), (90, 250)]
ev = "hi@150,400;250,400;250,350;150,350"
I.build_image_field(img, F, S / "o", name="M", field_id=30500, events=[ev])
t = S / "o" / "M.field.toml"
txt = t.read_text(encoding="utf-8")
txt = txt.replace("[player]\n", "[player]\nface = 3\n", 1)
txt += '''
[[player.arrival]]
entrance = 1
pos = [0, 0]

[[layers]]
image = "art/sign.png"
z = 100

[music]
song = 12
[music.extra]
a = 1
'''
t.write_text(txt, encoding="utf-8")
try:
    tomllib.loads(txt); print("hand toml parses")
except Exception as e:
    print("hand toml bad", e)
for k in range(3):
    m = I.build_image_field(img, F, S / "o", name="M", field_id=30500, events=[ev])
    d = tomllib.loads(t.read_text(encoding="utf-8"))
    print(k, "arrivals", len(d["player"].get("arrival", [])), "face", d["player"].get("face"),
          "layers", [l["image"] for l in d["layers"]], "music", d.get("music"), "events", [e["name"] for e in d["event"]])
print(t.read_text(encoding="utf-8"))
