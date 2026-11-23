"""Probe 2: real-event gestures + undo, then Generate / Regenerate x2 / reopen, with the real CLI."""
import json, shutil
from harness import *  # noqa

W = HERE / "p2"
shutil.rmtree(W, ignore_errors=True)
W.mkdir()
photo = room(W / "room.png")
sn = snip(W / "pillar_snip.png")
doc, run, handed = make_doc()
doc.load_image(photo)
app.processEvents(); doc.canvas._fit(); app.processEvents()

def H():
    return len(doc._history)

def sidecar():
    p = Path(doc._project["out"]) / "room.trace.json" if doc._project else None
    return json.loads(p.read_text()) if p and p.is_file() else None

log = []
def L(*a):
    s = " ".join(str(x) for x in a); log.append(s); print(s)

# ---- floor: 4 real clicks
for p in [(60, 430), (320, 430), (250, 220), (130, 220)]:
    click(doc, *p)
L("floor after 4 clicks", doc._floor, "hist", H())
# a click above the horizon is refused
h0 = H(); click(doc, 190, 40)
L("horizon", doc.pitch_label.text()); doc.on_undo()
L("above-horizon click: hist delta", H() - h0, "status:", doc.status.text()[:90])
# vertex drag
h0 = H(); drag(doc, doc._floor[2], (270, 240))
L("vertex drag ->", doc._floor[2], "hist delta", H() - h0)
doc.on_undo(); L("undo drag ->", doc._floor[2], "canvas", doc.canvas._trace[2])
# right-click delete vertex 3
h0 = H(); picked = context(doc, *doc._floor[3], "Delete vertex")
L("rclick delete:", picked, "floor len", len(doc._floor), "hist delta", H() - h0)
doc.on_undo(); L("undo delete -> len", len(doc._floor), "canvas len", len(doc.canvas._trace))

# ---- regions: gateway quad by 4 clicks
doc.tools.set_current("regions"); app.processEvents()
doc.gw_to.setValue(4005); doc.gw_ent.setValue(1)
h0 = H()
quad = [(100, 400), (180, 400), (180, 370), (100, 370)]
for p in quad[:2]:
    click(doc, *p)
doc.canvas.setFocus(); app.processEvents()
L("canvas hasFocus", doc.canvas.hasFocus(), "focusPolicy", doc.canvas.focusPolicy())
QTest.keyClick(doc.canvas, Qt.Key.Key_Escape); app.processEvents()
L("Esc mid-quad: pending", doc.canvas._pending_region, "hist delta", H() - h0)
QTest.keyClick(doc.canvas.viewport(), Qt.Key.Key_Escape); app.processEvents()
for p in quad:
    click(doc, *p)
L("gateway drawn: regions", len(doc._regions), doc._regions[0]["quad"] if doc._regions else None,
  "hist delta", H() - h0)
# event quad
doc.rkind_btns["event"].setChecked(True); doc.ev_msg.setText("Hello there")
for p in [(200, 400), (280, 400), (280, 370), (200, 370)]:
    click(doc, *p)
L("event drawn: regions", [(r["kind"], r["message"]) for r in doc._regions])
cent = lambda q: (sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4)
# retarget via the context menu
doc._ask_field_id = lambda cur: 4007
h0 = H(); picked = context(doc, *cent(doc._regions[0]["quad"]), "Set gateway target")
L("retarget:", picked, "to", doc._regions[0]["to"], "hist delta", H() - h0)
doc.on_undo(); L("undo retarget -> to", doc._regions[0]["to"])
doc._ask_message = lambda cur: "Reworded!"
h0 = H(); picked = context(doc, *cent(doc._regions[1]["quad"]), "Set message")
L("reword:", picked, doc._regions[1]["message"], "hist delta", H() - h0)
q_before = list(doc._regions[0]["quad"])
h0 = H(); picked = context(doc, *cent(doc._regions[0]["quad"]), "Walk-out edge")
L("rotate:", picked, "before", q_before, "after", doc._regions[0]["quad"], "hist delta", H() - h0)
doc.on_undo(); L("undo rotate ->", doc._regions[0]["quad"] == q_before)
# corner drag
h0 = H(); drag(doc, doc._regions[0]["quad"][1], (195, 405))
L("corner drag -> ", doc._regions[0]["quad"], "hist delta", H() - h0)
doc.on_undo()
h0 = H(); picked = context(doc, *cent(doc._regions[1]["quad"]), "Delete")
L("delete event:", picked, len(doc._regions), "hist delta", H() - h0)
doc.on_undo(); L("undo delete ->", [(r["kind"], r["message"]) for r in doc._regions])

# ---- cut-out: contact click + snip attach + snip drag + contact drag
doc.tools.set_current("cutout"); app.processEvents()
doc._ask_cutout = lambda: str(sn)
h0 = H(); click(doc, 220, 380)
L("contact:", doc._fg[0]["contact"] if doc._fg else None, doc._fg[0].get("kind") if doc._fg else None,
  "offset", doc._fg[0].get("offset") if doc._fg else None, "hist delta", H() - h0, "tool now", doc.tools.current())
f = doc._fg[0]; k = doc._canvas_scale(); sw, sh = f["size"]
mid = (f["offset"][0] + sw * k / 2, f["offset"][1] + sh * k / 3)
h0 = H(); drag(doc, mid, (mid[0] + 30, mid[1] + 10))
L("snip drag: offset", doc._fg[0]["offset"], "contact", doc._fg[0]["contact"], "hist delta", H() - h0)
h0 = H(); drag(doc, doc._fg[0]["contact"], (doc._fg[0]["contact"][0], doc._fg[0]["contact"][1] + 12))
L("contact drag: contact", doc._fg[0]["contact"], "offset", doc._fg[0]["offset"], "hist delta", H() - h0)
doc.on_undo(); L("undo contact drag ->", doc._fg[0]["contact"])

# ---- Generate for real
doc.name_box.setText("ROOMX"); doc.id_box.setText("30058")
doc._ask_out = lambda: str(W)
L("gen enabled", doc.gen_btn.isEnabled(), doc.gen_btn.toolTip()[:80])
doc.on_generate(); run.flush()
c = run.calls[-1]; L("GEN1 exit", c["code"]); L(c["out"][-900:])
out = Path(doc._project["out"])
snap1 = files_snapshot(out); L("files after gen1:", snap1)
L("handed to shell:", handed)
side = sidecar(); L("sidecar fg:", side["fg"]); L("sidecar regions:", [(r["kind"], r["to"], r["message"]) for r in side["regions"]])
toml1 = (out / "ROOMX.field.toml").read_text(); L(toml1)
# ---- edit 1: move a vertex, regenerate
drag(doc, doc._floor[0], (70, 425)) if doc.tools.current() == "floor" else None
L("stamped?", doc._stamped, doc.status.text()[-90:])
doc.on_generate(); run.flush(); L("GEN2 exit", run.calls[-1]["code"])
snap2 = files_snapshot(out); L("changed by gen2:", {k for k in set(snap1) | set(snap2) if snap1.get(k) != snap2.get(k)})
# ---- edit 2: remove the cut-out + delete the event zone, regenerate
doc.on_fg_remove()
doc.tools.set_current("regions"); app.processEvents()
ev_i = next(i for i, r in enumerate(doc._region_rows_cache) if r["kind"] == "event")
doc._on_region_deleted(ev_i)
doc.on_generate(); run.flush(); L("GEN3 exit", run.calls[-1]["code"]); L(run.calls[-1]["out"][-600:])
snap3 = files_snapshot(out); L("changed by gen3:", {k for k in set(snap2) | set(snap3) if snap2.get(k) != snap3.get(k)})
L("files after gen3:", sorted(snap3))
L((out / "ROOMX.field.toml").read_text())
(W / "log.txt").write_text("\n".join(log), encoding="utf-8")
