"""forms lane SYNTHESIS -- join the stock trigger table to the census.

1. Parse ff9.w_worldChangeBlockSet (ff9.cs) into {WorldPlace: [(x, z)]} and WorldConfiguration.UsePlaceAlternateForm
   (WorldConfiguration.cs) into {WorldPlace: default condition text} straight from the Memoria SOURCE (no hand copy).
2. CHECK THAT CAN FAIL: the union of the code's block lists must equal the census IsSwitchable set (prefab tier and
   scene tier), with no block driven by two places.
3. Per place / per block: effect class on each disc from mesh_channel_diff.json (NO-OP = every form-specific part
   full-record identical; RENDER-ONLY = geometry identical but UV/IDALL differ; GEO = positions differ), walk-surface
   numbers from form_diff.json, walk-list length parity, and the nearest engine navipos landmark to the changed
   region (ff9mapkit.world.locate.nearest_landmark -- a label with its distance, not identity).
Output: out/form_table.json + a printed table.   Rerun:  py label_forms.py   (needs the three out/*.json first)
"""
import sys, json, re
from pathlib import Path
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import locate as L

HERE = Path(__file__).parent
SRC = Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp")
FF9 = (SRC / "Global" / "ff9" / "ff9.cs").read_text(encoding="utf-8-sig")
WC = (SRC / "Memoria" / "World" / "WorldConfiguration.cs").read_text(encoding="utf-8-sig")
census = json.loads((HERE / "out" / "prefab_census.json").read_text())
walk = json.loads((HERE / "out" / "form_diff.json").read_text())
chan = json.loads((HERE / "out" / "mesh_channel_diff.json").read_text())
scene = json.loads((HERE / "out" / "scene_worlddisc.json").read_text())

# --- 1. parse the trigger table from source ---
m = re.search(r"public static void w_worldChangeBlockSet\(\)\s*\{(.*?)\n    \}\n", FF9, re.S)
body = m.group(1)
start_line = FF9[:m.start()].count("\n") + 1
place_blocks = {}
for pm in re.finditer(r"UsePlaceAlternateForm\(WorldPlace\.(\w+)\)\)[^\n]*\n\s*\{(.*?)\}", body, re.S):
    place_blocks[pm.group(1)] = [(int(a), int(b)) for a, b in re.findall(r"mw_worldSetFormBit\((\d+), (\d+)\)", pm.group(2))]
cm = re.search(r"public static Boolean UsePlaceAlternateForm\(WorldPlace place\)(.*?)\n        \}\n", WC, re.S)
conds = {k: v.strip() for k, v in re.findall(r"case WorldPlace\.(\w+):[^\n]*\n\s*return (.*?);", cm.group(1))}
print(f"w_worldChangeBlockSet @ ff9.cs:{start_line}: {len(place_blocks)} places, "
      f"{sum(len(v) for v in place_blocks.values())} SetFormBit calls")

# --- 2. the check that can fail ---
code_cells = [c for v in place_blocks.values() for c in v]
dup = {c for c in code_cells if code_cells.count(c) > 1}
for d in ("1", "4"):
    sw = {(r["x"], r["y"]) for r in census[d] if r["IsSwitchable"]}
    assert set(code_cells) == sw, (d, set(code_cells) ^ sw)
sc_sw = {(r["x"], r["y"]) for r in scene["level7"] if r["IsSwitchable"]}
assert set(code_cells) == sc_sw
assert not dup, dup
print(f"CHECK OK: code block set == prefab IsSwitchable (disc1, disc4) == scene WMBlock IsSwitchable ({len(sc_sw)}); "
      f"no block driven by two places")


def eff_class(rec):
    if not rec:
        return "?"
    kinds = []
    for k, v in rec.items():
        if "present" in v:
            kinds.append("GEO")      # a part exists in only one form (added/removed)
        elif not v["geo_equal"]:
            kinds.append("GEO")
        elif not v["full_equal"]:
            kinds.append("RENDER")
        else:
            kinds.append("SAME")
    if "GEO" in kinds:
        return "GEO"
    if "RENDER" in kinds:
        return "RENDER-ONLY"
    return "NO-OP"


rows = []
for place, cells in place_blocks.items():
    print(f"\n{place:<17} default: {conds.get(place, '?')}")
    for (x, y) in cells:
        key = f"{x},{y}"
        line = f"   ({x:>2},{y:>2}) #{y * 24 + x:<3}"
        rec = {"place": place, "cell": [x, y], "number": y * 24 + x, "condition": conds.get(place)}
        for d in ("1", "4"):
            w = walk[d][key]
            ec = eff_class(chan["form"][d][key])
            rec[f"disc{d}"] = {"class": ec, "walk_changed": w["any_changed"], "dy": [w["dy_min"], w["dy_max"]],
                               "topo_changed": w["topo_changed"], "topo_top": w["topo_transitions_top"][:3],
                               "list_len": w["walk_list_len"], "walk_lists": w["walk_list"],
                               "terrain_tris": w["terrain_tris"], "object_tris": w["object_tris"],
                               "bbox_local": w.get("bbox_local")}
            line += f" | d{d} {ec:<11} walk {w['any_changed']:>4}/4096 dy[{w['dy_min']:+.2f},{w['dy_max']:+.2f}] topo {w['topo_changed']:>3}"
        bb = walk["1"][key].get("bbox_local")
        if bb:
            cx, cz = x * 64 + (bb[0] + bb[1]) / 2, -y * 64 + (bb[2] + bb[3]) / 2
        else:
            cx, cz = x * 64 + 32, -y * 64 - 32
        lm = L.nearest_landmark(cx, cz)
        rec["nearest_landmark"] = {"name": lm["name"], "dist": round(lm["dist"], 1)}
        line += f" | near {lm['name']} ({lm['dist']:.0f}u)"
        parity = rec["disc1"]["list_len"][0] == rec["disc1"]["list_len"][1]
        same_head = rec["disc1"]["walk_lists"][0][:1] == [s.replace("Form2", "Form1") for s in rec["disc1"]["walk_lists"][1][:1]]
        rec["list_parity_d1"] = parity
        rec["list_index0_same_role_d1"] = same_head
        print(line)
        rows.append(rec)

(HERE / "out" / "form_table.json").write_text(json.dumps({"ff9_line": start_line, "places": place_blocks,
                                                           "conditions": conds, "rows": rows}, indent=1), encoding="utf-8")
n1 = {c: sum(1 for r in rows if r["disc1"]["class"] == c) for c in ("NO-OP", "RENDER-ONLY", "GEO")}
n4 = {c: sum(1 for r in rows if r["disc4"]["class"] == c) for c in ("NO-OP", "RENDER-ONLY", "GEO")}
print(f"\nclass tally disc1 {n1}  disc4 {n4}")
print("walk-list length mismatch (disc1):", [tuple(r["cell"]) for r in rows if not r["list_parity_d1"]])
print("walk-list index0 role differs (disc1):", [tuple(r["cell"]) for r in rows if not r["list_index0_same_role_d1"]])
