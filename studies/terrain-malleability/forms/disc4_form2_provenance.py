"""forms lane -- where did disc 4's FORM-2 meshes come from?  For each switchable cell and each of Terrain/Object,
classify disc-4 form 2 as
   COPY-OF-DISC1-F2  : full-record equal to disc 1's form 2 (a stale carry of the disc-1-era alternate form)
   SAME-AS-DISC4-F1  : full-record equal to disc 4's own form 1 (the switch is a no-op on disc 4)
   BOTH / NEITHER
and pair it with whether the cell's place is DISC-GATED (default condition requires w_frameDisc == 1).
Reads out/mesh_channel_diff.json + out/form_table.json.   Rerun:  py disc4_form2_provenance.py
"""
import json, collections
from pathlib import Path
HERE = Path(__file__).parent
ch = json.loads((HERE / "out" / "mesh_channel_diff.json").read_text())
ft = json.loads((HERE / "out" / "form_table.json").read_text())
tally = collections.Counter()
rows = []
for r in ft["rows"]:
    key = f"{r['cell'][0]},{r['cell'][1]}"
    gated = "w_frameDisc == 1" in (r["condition"] or "")
    out = {}
    for part in ("Terrain", "Object"):
        cd = ch["cross_disc"][key].get(f"{part}Form2")
        fm = ch["form"]["4"][key].get(f"{part}Form1|{part}Form2")
        if cd is None or fm is None or "present" in (fm or {}):
            out[part] = "n/a"
            continue
        a, b = cd["full_equal"], fm["full_equal"]
        out[part] = "BOTH" if a and b else "COPY-OF-DISC1-F2" if a else "SAME-AS-DISC4-F1" if b else "NEITHER"
        tally[(part, gated, out[part])] += 1
    rows.append((r["place"], tuple(r["cell"]), gated, out))
    print(f"{r['place']:<17} {str(tuple(r['cell'])):>8} disc-gated={gated!s:<5} Terrain2: {out['Terrain']:<17} Object2: {out['Object']}")
print()
for k, v in sorted(tally.items(), key=str):
    print("  ", k, v)
(HERE / "out" / "disc4_form2_provenance.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
