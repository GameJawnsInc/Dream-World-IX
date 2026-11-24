"""Lead re-verification of T1: does a Trace regenerate delete a Place-minted door0?"""
import importlib.util, sys, tempfile, tomllib
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from ff9mapkit import imagefield as IF
from ff9mapkit.workspace import placedoc

assert "inspiring-wing" in IF.__file__, IF.__file__
spec = importlib.util.spec_from_file_location("_fx", Path.cwd() / "tests" / "test_imagefield.py")
fx = importlib.util.module_from_spec(spec); spec.loader.exec_module(fx)

root = Path(tempfile.mkdtemp(prefix="lead_t1_"))
photo, floor = fx._paint_room(root)
out = root / "proj"
IF.build_image_field(photo, floor, out, name="PICTURE", field_id=30058)
toml = out / "PICTURE.field.toml"
data = tomllib.loads(toml.read_text(encoding="utf-8"))
print("after first generate: gateways", [g.get("name") for g in data.get("gateway", [])])

# what the Place tab does: its own pure op, then the shell's save (model.dumps of the doc dict)
from ff9mapkit.editor import model
doc = model.FieldDoc.load(toml)
name = placedoc.place_gateway(doc.data, [(0, 0), (100, 0), (100, 100), (0, 100)], 4005)
print("Place minted:", name if isinstance(name, str) else doc.data["gateway"][-1].get("name"))
doc.save()
print("on disk after Place save: gateways", [g.get("name") for g in tomllib.loads(toml.read_text(encoding="utf-8")).get("gateway", [])])

# back in Trace: add ONE event zone and regenerate
ev = IF.parse_event_spec("hello@40,400;150,400;150,430;40,430")
man = IF.build_image_field(photo, floor, out, name="PICTURE", field_id=30058, events=[ev])
after = tomllib.loads(toml.read_text(encoding="utf-8"))
print("regenerate removed:", man.get("removed"))
print("on disk after regenerate: gateways", [g.get("name") for g in after.get("gateway", [])],
      "events", [e.get("name") for e in after.get("event", [])])
