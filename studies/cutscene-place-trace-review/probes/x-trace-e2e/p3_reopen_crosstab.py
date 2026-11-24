"""Probe 3: reopen numerics, the Place cross-tab round trip, the cp1252 child crash, same-stem
collision, history cap."""
import json, shutil, tomllib
from harness import *  # noqa
from ff9mapkit.workspace import placedoc
from ff9mapkit.editor import model as M

W = HERE / "p3"
shutil.rmtree(W, ignore_errors=True)
W.mkdir()
def L(*a):
    print(" ".join(str(x) for x in a), flush=True)

def traced(doc, photo, pitch=None):
    doc.load_image(photo); app.processEvents(); doc.canvas._fit(); app.processEvents()
    if pitch:
        doc.pitch.setValue(pitch)
    for p in [(60, 430), (320, 430), (250, 240), (130, 240)]:
        click(doc, *p)

# ================= A. reopen numerics (pitch 31, snip, gateway + event)
photo = room(W / "room.png")
sn = snip(W / "snip.png")
doc, run, handed = make_doc()
traced(doc, photo, pitch=31)
doc.tools.set_current("regions"); app.processEvents()
doc.gw_to.setValue(4005); doc.gw_ent.setValue(2)
for p in [(100, 400), (180, 400), (180, 370), (100, 370)]:
    click(doc, *p)
doc.rkind_btns["event"].setChecked(True); doc.ev_msg.setText('Say "hi" \\ back')
for p in [(200, 400), (280, 400), (280, 370), (200, 370)]:
    click(doc, *p)
doc.tools.set_current("cutout"); app.processEvents()
doc._ask_cutout = lambda: str(sn)
click(doc, 220, 380)
f = doc._fg[0]; k = doc._canvas_scale(); sw, sh = f["size"]
mid = (f["offset"][0] + sw * k / 2, f["offset"][1] + sh * k / 3)
drag(doc, mid, (mid[0] + 33, mid[1] + 7))
doc.name_box.setText("REOPEN"); doc.id_box.setText("30111")
doc._ask_out = lambda: str(W)
doc.on_generate(); run.flush()
L("A gen exit", run.calls[-1]["code"])
out = Path(doc._project["out"]); toml = out / "REOPEN.field.toml"
ref = {"floor": list(doc._floor), "pitch": doc.pitch.value(),
       "fg": [(f["contact"], f.get("offset"), f.get("kind")) for f in doc._fg],
       "regions": [(r["kind"], r["to"], r["entrance"], r["message"], r["quad"]) for r in doc._regions],
       "name": doc.name_box.text(), "id": doc.id_box.text()}
L("ref", ref)

def state(d):
    return {"floor": list(d._floor), "pitch": d.pitch.value(),
            "fg": [(f["contact"], f.get("offset"), f.get("kind")) for f in d._fg],
            "regions": [(r["kind"], r["to"], r["entrance"], r["message"], r["quad"]) for r in d._regions],
            "name": d.name_box.text(), "id": d.id_box.text()}

def maxdiff(a, b):
    import itertools
    m = 0.0
    def walk(x, y):
        nonlocal m
        if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)):
            if len(x) != len(y):
                m = float("inf"); return
            for u, v in zip(x, y):
                walk(u, v)
        elif isinstance(x, (int, float)) and isinstance(y, (int, float)):
            m = max(m, abs(x - y))
        elif x != y:
            m = float("inf")
    walk(a, b)
    return m

for how in ("trace.json", "field.toml (sidecar)"):
    d2, r2, _ = make_doc()
    (d2.load_trace(out / "room.trace.json") if how == "trace.json" else d2.load_project(toml))
    s = state(d2)
    L(f"A reopen via {how}:", {k: maxdiff(ref[k], s[k]) if k in ("floor", "fg", "regions", "pitch") else (ref[k] == s[k])
                               for k in ref}, "status:", d2.status.text()[:70])
# pre-sidecar: copy project without the sidecar
pre = W / "pre"; shutil.copytree(out, pre); (pre / "room.trace.json").unlink()
d3, r3, _ = make_doc()
d3.load_project(pre / "REOPEN.field.toml")
s = state(d3)
L("A reopen pre-sidecar:", {k: maxdiff(ref[k], s[k]) if k in ("floor", "fg", "regions", "pitch") else (ref[k] == s[k]) for k in ref})
L("   pre-sidecar fg:", s["fg"], " regions msgs:", [r[3] for r in s["regions"]])
L("   pre-sidecar floor:", s["floor"]); L("   ref floor:        ", ref["floor"])
# regenerate pre-sidecar unchanged -> what changes on disk?
before = files_snapshot(pre)
d3.on_generate(); r3.flush()
L("A pre-sidecar regen exit", r3.calls[-1]["code"], "changed:", {k for k in set(before) | set(files_snapshot(pre)) if before.get(k) != files_snapshot(pre).get(k)})
L("   argv:", r3.calls[-1]["argv"][3:])

# ================= B. cross-tab: Place edits on the project, then Trace regenerate
data = tomllib.loads(toml.read_text(encoding="utf-8"))
L("B place_npc", placedoc.place_npc(data, 50, -900))
L("B place_prop", placedoc.place_prop(data, -60, -1000))
L("B set_spawn", placedoc.set_spawn(data, 10, -1100))
L("B set_arrival", placedoc.set_arrival(data, 1, 20, -1000))
L("B place_gateway", placedoc.place_gateway(data, [(-100, -800), (0, -800), (0, -700), (-100, -700)], 4008))
L("B place_event", placedoc.place_event(data, [(100, -800), (200, -800), (200, -700), (100, -700)]))
toml.write_text(M.dumps(data), encoding="utf-8")
placed = tomllib.loads(toml.read_text(encoding="utf-8"))
L("B after Place save: gateways", [g["name"] for g in placed.get("gateway", [])], "events", [e["name"] for e in placed.get("event", [])],
  "npc", [n.get("name") for n in placed.get("npc", [])], "spawn", placed["player"].get("spawn"))
# back to Trace: the original session doc regenerates in place after an edit
drag(doc, doc._floor[1], (325, 428)) if doc.tools.set_current("floor") is None else None
doc.on_generate(); r = run; r.flush()
L("B regen exit", r.calls[-1]["code"]); L(r.calls[-1]["out"][-1200:])
after = tomllib.loads(toml.read_text(encoding="utf-8"))
L("B survived: gateways", [g["name"] for g in after.get("gateway", [])], "events", [e["name"] for e in after.get("event", [])],
  "npc", [n.get("name") for n in after.get("npc", [])], "props", [p.get("name") for p in after.get("prop", [])],
  "spawn", after["player"].get("spawn"), "arrival", after["player"].get("arrival"))
L("B trace status:", doc.status.text()[-140:])

# ================= C. cp1252 child: an event message with an arrow
d4, r4, h4 = make_doc()
traced(d4, photo)
d4.tools.set_current("regions"); app.processEvents()
d4.rkind_btns["event"].setChecked(True); d4.ev_msg.setText("Go → north")
for p in [(200, 400), (280, 400), (280, 370), (200, 370)]:
    click(d4, *p)
(W / "c").mkdir(); d4._ask_out = lambda: str(W / "c")
d4.name_box.setText("ARROW"); d4.id_box.setText("30112")
d4.on_generate(); r4.flush()
c = r4.calls[-1]
L("C exit", c["code"], "handed", h4, "files:", sorted(files_snapshot(W / "c" / "room-field")))
L("C tail:", c["out"][-400:])

# ================= D. same-stem collision: two different photos both called IMG_0001.jpg
(W / "phoneA").mkdir(); (W / "phoneB").mkdir(); (W / "projects").mkdir()
from PIL import Image
a = room(W / "phoneA" / "tmpa.png"); Image.open(a).convert("RGB").save(W / "phoneA" / "IMG_0001.jpg")
b = room(W / "phoneB" / "tmpb.png", size=(600, 800)); Image.open(b).convert("RGB").save(W / "phoneB" / "IMG_0001.jpg")
da, ra, _ = make_doc(); traced(da, W / "phoneA" / "IMG_0001.jpg")
da.name_box.setText("CELLAR"); da.id_box.setText("30120"); da._ask_out = lambda: str(W / "projects")
da.on_generate(); ra.flush()
proj = W / "projects" / "IMG_0001-field"
# the author adds hand content to CELLAR
t = proj / "CELLAR.field.toml"; t.write_text(t.read_text(encoding="utf-8") + '\n[[npc]]\nname = "Bob"\npos = [0, -900]\n', encoding="utf-8")
snapA = files_snapshot(proj)
db, rb, _ = make_doc(); traced(db, W / "phoneB" / "IMG_0001.jpg")
db.name_box.setText("ATTIC"); db.id_box.setText("30121"); db._ask_out = lambda: str(W / "projects")
db.on_generate(); rb.flush()
snapB = files_snapshot(proj)
L("D second project exit", rb.calls[-1]["code"], "out", db._project["out"])
L("D files:", sorted(snapB)); L("D CELLAR files overwritten:", [k for k in snapA if snapA[k] != snapB.get(k)])
side = json.loads((proj / "IMG_0001.trace.json").read_text())
L("D sidecar now names:", side["name"], side["image"])
dr, _, _ = make_doc(); dr.load_project(t)
L("D reopen CELLAR.field.toml in Trace -> name box", dr.name_box.text(), "id", dr.id_box.text(), "image", dr._image)

# ================= E. history cap
de, _, _ = make_doc(); traced(de, photo)
for i in range(150):
    drag(de, de._floor[0], (60 + (i % 2) * 3, 430))
L("E history len after 154 gestures", len(de._history))
n = 0
while de._history:
    de.on_undo(); n += 1
L("E undo steps available", n, "floor after undoing all", de._floor)
