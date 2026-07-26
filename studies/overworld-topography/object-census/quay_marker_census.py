"""READ-ONLY census: every disc-1 world block that carries an Object (baked structure) sub-mesh --
survey shape/size (footprint, height, tri count) + cross-reference with the entrance-area name table
(world/locate.py) and the coastal-donor table (list_coastal_donors) to flag small, coastal, low-tri
structures -- the candidates most likely to be a dock/pier/signpost/lantern-class marker rather than
a whole town/castle.

Reads ONLY the base game install's StreamingAssets bundles (never a mod folder). No writes to the repo
or the game install. Output -> scratchpad JSON + a printed ranked table.
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\gui-workspace-improvements-277c74")
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import locate as L           # noqa: E402

DISC = 1
OUT = Path(__file__).resolve().parent / "quay_marker_census.json"

print("Enumerating Object-mesh blocks (disc 1)...")
obj_blocks = X.list_object_blocks(disc=DISC)
print(f"{len(obj_blocks)} blocks carry an Object sub-mesh")

print("Building area->name / area->blocks table (world-locate)...")
try:
    rows = L.locate(disc=DISC)
    block_to_names = {}
    for r in rows:
        nm = sorted({d["name"] for d in r["destinations"] if d["name"]})
        if not nm:
            continue
        for b in r["blocks"]:
            block_to_names.setdefault(tuple(b), set()).update(nm)
except Exception as ex:
    print(f"  locate() failed ({ex}) -- continuing without name join")
    block_to_names = {}

print("Building coastal-donor table (beach/sea per land block)...")
try:
    coastal = X.list_coastal_donors(disc=DISC, beach_only=False)
except Exception as ex:
    print(f"  list_coastal_donors failed ({ex})")
    coastal = {}

results = []
for (bx, by) in obj_blocks:
    try:
        bm = X.read_block(bx, by, disc=DISC, part="object")
    except Exception as ex:
        results.append({"block": [bx, by], "error": str(ex)})
        continue
    verts = bm.verts
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    footprint_x = max(xs) - min(xs)
    footprint_z = max(zs) - min(zs)
    height = max(ys) - min(ys)
    names = sorted(block_to_names.get((bx, by), []))
    subs = coastal.get((bx, by), [])
    results.append({
        "block": [bx, by],
        "names": names,
        "coastal_subs": subs,
        "tris": len(bm.tris),
        "verts": bm.vcount,
        "footprint_x": round(footprint_x, 1),
        "footprint_z": round(footprint_z, 1),
        "footprint_max": round(max(footprint_x, footprint_z), 1),
        "height": round(height, 2),
        "y_min": round(min(ys), 2),
        "y_max": round(max(ys), 2),
    })

ok = [r for r in results if "error" not in r]
ok.sort(key=lambda r: r["tris"])

OUT.write_text(json.dumps({"disc": DISC, "n_object_blocks": len(obj_blocks), "blocks": results}, indent=1),
                encoding="utf-8")
print(f"\nwrote {OUT}\n")

print(f"{'block':<10}{'tris':>6}{'verts':>7}{'fpXZ':>14}{'height':>8}  {'coastal':<18}{'names'}")
for r in ok:
    fp = f"{r['footprint_x']:.0f}x{r['footprint_z']:.0f}"
    print(f"{str(r['block']):<10}{r['tris']:>6}{r['verts']:>7}{fp:>14}{r['height']:>8.1f}  "
          f"{','.join(r['coastal_subs']):<18}{','.join(r['names'])}")

print("\n--- smallest 20 (best marker candidates by tri count) ---")
for r in ok[:20]:
    fp = f"{r['footprint_x']:.0f}x{r['footprint_z']:.0f}"
    print(f"block {r['block']}: {r['tris']} tris, footprint {fp}, height {r['height']:.1f}, "
          f"coastal={r['coastal_subs']}, names={r['names']}")

print("\n--- COASTAL object blocks only (beach/sea neighbour -> plausible dock siting) ---")
coastal_obj = [r for r in ok if r["coastal_subs"]]
coastal_obj.sort(key=lambda r: r["tris"])
for r in coastal_obj:
    fp = f"{r['footprint_x']:.0f}x{r['footprint_z']:.0f}"
    print(f"block {r['block']}: {r['tris']} tris, footprint {fp}, height {r['height']:.1f}, "
          f"coastal={r['coastal_subs']}, names={r['names']}")

# Context: the quay's own block + immediate neighbours (does it already carry stock Object content?)
print("\n--- Block[0][18] (Lantern Quay) + neighbours: Object presence check ---")
for (bx, by) in [(0, 18), (0, 17), (0, 19), (1, 18), (1, 17), (1, 19)]:
    has_obj = (bx, by) in set(obj_blocks)
    has_terrain = (bx, by) in set(X.list_blocks(disc=DISC))
    cs = coastal.get((bx, by), [])
    nm = sorted(block_to_names.get((bx, by), []))
    print(f"  Block[{bx}][{by}]: terrain={has_terrain} object={has_obj} coastal={cs} names={nm}")
