"""forms lane -- one overview PNG per disc: the 24x20 block grid (sea blue, land grey), the 26 switchable cells
outlined in yellow, and each cell's form1->form2 WALK-surface change mask (form_diff.json, 32x32 downsample) in red.
Cells whose switch is render-only (UV/IDALL) get a magenta outline; NO-OP cells stay plain yellow.
Output out/form_map_disc{1,4}.png (derived render, no game bytes).  Rerun:  py render_form_map.py
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
census = json.loads((HERE / "out" / "prefab_census.json").read_text())
walk = json.loads((HERE / "out" / "form_diff.json").read_text())
table = json.loads((HERE / "out" / "form_table.json").read_text())
S = 32
for d in ("1", "4"):
    img = Image.new("RGB", (24 * S, 20 * S), (20, 20, 20))
    dr = ImageDraw.Draw(img)
    cls = {tuple(r["cell"]): r[f"disc{d}"]["class"] for r in table["rows"]}
    for r in census[d]:
        x, y = r["x"], r["y"]
        dr.rectangle([x * S, y * S, x * S + S - 1, y * S + S - 1], fill=(40, 70, 140) if r["IsSea"] else (110, 110, 100))
    for key, w in walk[d].items():
        x, y = (int(v) for v in key.split(","))
        for j, row in enumerate(w["mask_rows"]):
            for i, ch in enumerate(row):
                if ch == "#":
                    img.putpixel((x * S + i, y * S + j), (230, 40, 40))
        col = {"NO-OP": (240, 220, 40), "RENDER-ONLY": (230, 60, 230), "GEO": (255, 140, 0)}[cls[(x, y)]]
        dr.rectangle([x * S, y * S, x * S + S - 1, y * S + S - 1], outline=col, width=2)
    img = img.resize((24 * S * 2, 20 * S * 2), Image.NEAREST)
    p = HERE / "out" / f"form_map_disc{d}.png"
    img.save(p)
    print("wrote", p)
