"""forms lane -- does any LIVE s34 loose-mesh override sit on a SWITCHABLE cell? (read-only listing of the install)

The s34 override key is "WorldMap/Disc{tag}/0_1/r{y}/Block[x][y] {transform.name}" (WMWorld.cs:823-825, s34+s74), and a
switchable block's form-2 children are NAMED "Terrain2"/"Object2"/"VolcanoLava2"/"Sea3_2".. (prefab_census.json).
So a kit edit written as "Block[x][y] Terrain.ff9mesh" on a switchable cell only replaces FORM 1: the day the cell's
place condition flips (UsePlaceAlternateForm), the stock form-2 mesh returns and the edit vanishes (render + walk).
This script lists, per mod folder, the override files on the 26 switchable cells and which form they reach.
Rerun:  py live_override_overlap.py
"""
import json, re, collections
from pathlib import Path

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
HERE = Path(__file__).parent
census = json.loads((HERE / "out" / "prefab_census.json").read_text())
SW = {d: {(r["x"], r["y"]): r for r in census[d] if r["IsSwitchable"]} for d in ("1", "4")}
F2_NAMES = {"Terrain2", "Object2", "VolcanoCrater2", "VolcanoLava2", "Sea3_2", "Sea4_2", "Sea5_2"}
pat = re.compile(r"Disc(\d+)[\\/]0_1[\\/]r(\d+)[\\/]Block\[(\d+)\]\[(\d+)\] (.+)\.ff9mesh$", re.I)
out = {}
for mod in sorted(p for p in GAME.iterdir() if p.is_dir()):
    files = [f for f in mod.rglob("*.ff9mesh")]
    if not files:
        continue
    hits = collections.defaultdict(list)
    tag_count = collections.Counter()
    for f in files:
        m = pat.search(str(f))
        if not m:
            continue
        disc, y, x, part = m.group(1), int(m.group(2)), int(m.group(3)), m.group(5)
        tag_count[disc] += 1
        sw = SW.get("1" if disc == "9" else disc, {})     # tag 9 = Path D sentinel; CLONE mode copies disc-1 flags (WorldDiscSpike.cs:187-193)
        if (x, y) in sw:
            hits[(disc, x, y)].append(part)
    print(f"{mod.name}: {len(files)} .ff9mesh (by disc tag {dict(tag_count)}); on switchable cells: {len(hits)}")
    for (disc, x, y), parts in sorted(hits.items()):
        num = y * 24 + x

        def reach(p):
            if p in F2_NAMES:
                return "FORM2"
            if p in ("Terrain", "Object", "VolcanoCrater1", "VolcanoLava1") or (num == 219 and p in ("Sea3", "Sea4", "Sea5")):
                return "FORM1-only"
            return "BOTH(shared part)"
        print(f"   disc-tag{disc} ({x},{y}) #{num}: " + ", ".join(f"{p}[{reach(p)}]" for p in sorted(parts)))
    out[mod.name] = {f"{d},{x},{y}": p for (d, x, y), p in hits.items()}
(HERE / "out" / "live_override_overlap.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
