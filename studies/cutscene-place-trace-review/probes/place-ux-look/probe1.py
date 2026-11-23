import os, sys, tempfile, tomllib
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
import ff9mapkit
print("pkg:", ff9mapkit.__file__)
from ff9mapkit.workspace import placedoc as P
from ff9mapkit.workspace.shell import pick_palette
from ff9mapkit import build

pal = pick_palette("mist") if callable(pick_palette) else None
edits = []
doc = P.PlaceDoc(pal, on_edit=lambda m, l: edits.append(l))
doc._loader.start = lambda *a, **k: print("  (loader.start suppressed:", a, ")")

tmp = Path(tempfile.mkdtemp(prefix="placeprobe_"))
fpath = tmp / "demo.field.toml"
fpath.write_text("[field]\nname='demo'\nid=30999\n", encoding="utf-8")

# 1. loading message
data = {"field": {"name": "demo", "id": 30999, "source_field": 351}}
doc.show_field("demo", data, str(fpath))
print("donor resolved:", doc._donor, "source:", doc._source)
doc.on_load()
print("1. status while loading:", repr(doc.status.text()))
doc._loading = None
data2 = {"field": {"name": "novel", "id": 30998}}
doc.show_field("novel", data2, str(fpath))
doc.on_load()
print("1b. novel status while loading:", repr(doc.status.text()))
doc._loading = None

# 2. prop name collision after delete
d = {}
P.place_prop(d, 0, 0); P.place_prop(d, 10, 10)
del d["prop"][0]
P.place_prop(d, 20, 20)
print("2. prop names after delete+place:", [p["name"] for p in d["prop"]])

# 3. verbatim tooltip stale
v = {"field": {"name": "v", "id": 30997}, "verbatim_eb": {"donor": 351}}
doc.show_field("v", v, str(fpath))
print("3a. verbatim spawn enabled/tooltip:", doc.mode_btns["spawn"].isEnabled(), repr(doc.mode_btns["spawn"].toolTip()[:60]))
nv = {"field": {"name": "nv", "id": 30996, "source_field": 351}}
doc.show_field("nv", nv, str(fpath))
print("3b. non-verbatim spawn enabled/tooltip:", doc.mode_btns["spawn"].isEnabled(), repr(doc.mode_btns["spawn"].toolTip()[:60]))

# 4. scene.toml override of a Place spawn/arrival
base = {"player": {"spawn": [0, 0]}}
P.set_spawn(base, 400, 900)
P.set_arrival(base, 1, 50, 60)
scene = {"player": {"spawn": [-100, -100], "arrival": [{"entrance": 1, "pos": [7, 7]}]}}
merged = build._merge_scene(base, scene)
print("4. field.toml spawn after Place:", base["player"]["spawn"], "-> build sees:", merged["player"]["spawn"])
print("4. arrival after Place:", base["player"]["arrival"], "-> build sees:", merged["player"]["arrival"])
print("4. markers Place draws:", [(m["label"], m["xz"]) for m in P.content_markers(base)])

# 5. hint pill text in regions mode / blocked
print("5. hint text:", repr(doc.canvas._hint.text()))
blocked = {"field": {"name": "b", "id": 1, "source_field": 351}}
doc._blocked = None
print("6. bare/no-field note:")
doc.show_none(); print("   ", repr(doc.status.text()))
print("7. load_btn tooltip:", repr(doc.load_btn.toolTip()))
