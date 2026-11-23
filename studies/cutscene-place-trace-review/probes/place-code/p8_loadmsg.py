import sys
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
from PySide6.QtWidgets import QApplication
app = QApplication([])
from ff9mapkit.workspace import placedoc as P
from ff9mapkit.workspace.shell import pick_palette
d = P.PlaceDoc(pick_palette("mist"), on_edit=None)
d._loader.start = lambda *a: None
d.show_field("F", {"field":{"source_field":351}}, Path("C:/x/F.field.toml")); d.on_load(); print(d.status.text())
d.show_field("N", {"field":{"id":30001}}, Path("C:/proj/rooms/N.field.toml")); d.on_load(); print(d.status.text())
