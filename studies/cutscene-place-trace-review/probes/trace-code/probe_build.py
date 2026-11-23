"""build_image_field end-to-end in a scratch dir: bowtie, names, merge across regenerates."""
import shutil, tomllib, traceback
from pathlib import Path
from PIL import Image
from ff9mapkit import imagefield as I

S = Path(r"<SCRATCH>/review/trace-code/build")
shutil.rmtree(S, ignore_errors=True)
S.mkdir(parents=True)
img = S / "photo.png"
Image.new("RGB", (800, 600), (90, 80, 70)).save(img)
FLOOR = [(60, 420), (330, 420), (300, 250), (90, 250)]

print("== bowtie floor builds silently? ==")
bow = [(60, 420), (300, 250), (330, 420), (90, 250)]
try:
    m = I.build_image_field(img, bow, S / "bow", name="BOW", field_id=30500)
    print("built:", m["verts"], "verts", m["faces"], "faces (no refusal)")
except Exception as e:
    print("refused:", e)

for nm in ['A"B', "sub/dir", "Q?X"]:
    out = S / ("name_" + str(abs(hash(nm)) % 1000))
    print(f"== name {nm!r} ==")
    try:
        I.build_image_field(img, FLOOR, out, name=nm, field_id=30500)
        t = next(out.glob("*.field.toml"), None)
        print("  wrote", t)
        try:
            tomllib.loads(t.read_text(encoding="utf-8")); print("  toml parses")
        except Exception as e:
            print("  TOML BROKEN:", e)
    except Exception as e:
        print("  raised", type(e).__name__, e)
    print("  left on disk:", sorted(str(p.relative_to(out)) for p in out.rglob("*")) if out.exists() else None)

print("== merge: Place door0 on a no-regions project, then Trace adds an event zone ==")
P = S / "merge"
I.build_image_field(img, FLOOR, P, name="M", field_id=30500)
t = P / "M.field.toml"
t.write_text(t.read_text(encoding="utf-8") + '''
[[gateway]]
name = "door0"
to = 100
zone = [[0, 0], [100, 0], [100, 100], [0, 100]]

[[event]]
name = "zone0"
message = "hand"
zone = [[0, 0], [10, 0], [10, 10], [0, 10]]

[[npc]]
name = "bob"
model = "x"
''', encoding="utf-8")
# regenerate #1 with no regions -> keeps
m = I.build_image_field(img, FLOOR, P, name="M", field_id=30500)
print(" regen no-regions: removed", m["removed"], "kept", m["kept"])
ev = "hello@150,400;250,400;250,350;150,350"
m = I.build_image_field(img, FLOOR, P, name="M", field_id=30500, events=[ev])
print(" regen +event: removed", m["removed"])
d = tomllib.loads(t.read_text(encoding="utf-8"))
print(" gateways now:", [g["name"] for g in d.get("gateway", [])], "events:", [e["name"] for e in d.get("event", [])])
for k in range(2):
    m = I.build_image_field(img, FLOOR, P, name="M", field_id=30500, events=[ev])
d = tomllib.loads(t.read_text(encoding="utf-8"))
print(" after 2 more regens: npc", len(d.get("npc", [])), "events", [e["name"] for e in d.get("event", [])])

print("== name change on an in-place regenerate ==")
m = I.build_image_field(img, FLOOR, P, name="RENAMED", field_id=30500)
print(" kept on rename:", m["kept"], "; tomls in folder:", sorted(p.name for p in P.glob("*.field.toml")))

print("== a hand [field] key and [camera] key ==")
t.write_text(t.read_text(encoding="utf-8").replace("[field]\n", '[field]\ntext_block = 30500\nbgm = 5\n', 1), encoding="utf-8")
m = I.build_image_field(img, FLOOR, P, name="M", field_id=30500, events=[ev])
print(" retaken", m["retaken"], "; text_block survives:", "text_block" in t.read_text(encoding="utf-8"))

print("== gateway zone near the horizon: Int16? ==")
gw = "100@150,0;250,0;250,30;150,30"
try:
    m = I.build_image_field(img, FLOOR, S / "gwh", name="G", field_id=30500, gateways=[gw])
    print(" built; zone:", tomllib.loads((S / "gwh" / "G.field.toml").read_text())["gateway"][0]["zone"])
except Exception as e:
    print(" refused", e)
