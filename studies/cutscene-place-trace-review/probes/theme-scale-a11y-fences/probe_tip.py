import os; os.environ["QT_QPA_PLATFORM"]="offscreen"
from pathlib import Path
from PySide6.QtWidgets import QApplication
app=QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace.placedoc import PlaceDoc
d=PlaceDoc(pick_palette("dark"),on_edit=lambda *a:None)
d.show_field("V",{"field":{"source_field":351},"verbatim_eb":{"donor":351}},Path("C:/nowhere/V.field.toml"))
print("verbatim: spawn enabled",d.mode_btns["spawn"].isEnabled(),"tip",d.mode_btns["spawn"].toolTip()[:40])
d.show_field("N",{"field":{"source_field":351}},Path("C:/nowhere/N.field.toml"))
print("novel: spawn enabled",d.mode_btns["spawn"].isEnabled(),"tip",repr(d.mode_btns["spawn"].toolTip()[:60]))
