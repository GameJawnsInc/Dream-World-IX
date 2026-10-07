"""STEP 9 -- TOOLING INTERACTION: what the disc-1 vs disc-4 census means for world/discmirror.py.

Evidence only (no fix). Read-only on the install and the live mod folders.
 (1) THE GATE, MEASURED. discmirror.mirror() mirrors a cell to Disc4 only if the destination REAL cell is
     ocean or "byte-identical across discs" (discmirror.py `mirror`: _real_parts set equality +
     _parts_identical per part). Here we run the module's OWN predicates (_real_parts, _parts_identical) over
     all real cells and check the census predicts them cell-for-cell -- then count how much of the real map
     the gate refuses (an in-place edit there never reaches disc 4).
 (2) CHANGED BORDERS. Block edges whose terrain vertex profile differs between discs (land|land and
     land|non-terrain): an override welded against the disc-1 neighbour cracks against the disc-4 one, and
     the gate never looks at NEIGHBOURS.
 (3) THE LIVE STATE. Every deployed override (FF9CustomMap*/FF9_Data/WorldMap/Disc{1,4}/0_1): per (cell, part)
     -- is the real cell land, does the real part differ across discs, are the Disc1/Disc4 files identical,
     does the cell touch a changed border? A Disc4 override of a part whose REAL disc-4 bytes differ from
     disc 1 REPLACES a genuine disc-4 edit.
Writes out/mirror_risk.json. Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/mirror_risk.py
"""
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X                                  # noqa: E402
from ff9mapkit import config                         # noqa: E402
from ff9mapkit.world import discmirror as DM         # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
rows = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
ana = json.loads((OUT / "anatomy.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
res = {}

# ---------------- (1) the gate ----------------
r1, r4 = DM._real_parts(1), DM._real_parts(4)
cells = sorted(set(r1) | set(r4))
gate = {}
for c in cells:
    if not r4.get(c):
        gate[c] = "PASS(ocean)"
    elif r1.get(c, set()) != r4[c]:
        gate[c] = "SKIP(part sets)"
    else:
        diff = [p for p in sorted(r4[c]) if not DM._parts_identical(c, p, 1, 4)]
        gate[c] = "SKIP" if diff else "PASS(identical)"
pred = {}
for c in cells:
    rs = [r for r in rows if r["lod"] == "0_1" and (r["x"], r["y"]) == c]
    if any(r["cls"] in ("ADDED", "REMOVED") for r in rs):
        pred[c] = "SKIP(part sets)"
    elif any(r["cls"] != "IDENTICAL" for r in rs):
        pred[c] = "SKIP"
    else:
        pred[c] = "PASS(identical)"
agree = sum(1 for c in cells if gate[c] == pred[c])
gc = Counter(gate.values())
print(f"(1) discmirror gate over {len(cells)} real cells: {dict(gc)}")
print(f"    census predicts the gate on {agree}/{len(cells)} cells")
reorder_only = [c for c in cells if gate[c] == "SKIP" and all(
    r["cls"] in ("IDENTICAL", "REORDERED") for r in rows if r["lod"] == "0_1" and (r["x"], r["y"]) == c)]
print(f"    of the SKIPs, {len(reorder_only)} differ ONLY by triangle order (geometrically identical): {reorder_only}")
land = [c for c in cells if any(p == "terrain" for p in r1.get(c, ()))]
skip_land = [c for c in land if gate[c].startswith("SKIP")]
print(f"    real LAND cells (with a Terrain part): {len(land)}; gate refuses {len(skip_land)} "
      f"({100*len(skip_land)/len(land):.0f}%)")
res["gate"] = {str(c): v for c, v in gate.items()}
res["gate_agree"] = [agree, len(cells)]
res["reorder_only_skips"] = reorder_only

# ---------------- (2) changed borders ----------------
terr = {(d, x, y): o for (d, lod, x, y, p), o in objs.items() if lod == "0_1" and p == "terrain"}
prof = {}


def ep(d, x, y, s):
    k = (d, x, y)
    if k not in prof:
        bm = L.decode(terr[k], d, x, y, "0_1")
        prof[k] = {side: L.edge_profile(bm, side) for side in "EWNS"}
    return prof[k][s]


NB = {"E": (1, 0, "W"), "W": (-1, 0, "E"), "S": (0, 1, "N"), "N": (0, -1, "S")}
changed_edges = []
for (d, x, y) in sorted(terr):
    if d != 1 or (4, x, y) not in terr:
        continue
    for s, (dx, dy, _o) in NB.items():
        a1, a4 = ep(1, x, y, s), ep(4, x, y, s)
        if a1 != a4:
            nb = ((x + dx) % 24, y + dy)
            changed_edges.append({"cell": [x, y], "side": s, "neighbour": list(nb),
                                  "neighbour_is_terrain": (1, nb[0], nb[1]) in terr,
                                  "verts_d1": len(a1), "verts_d4": len(a4)})
nb_kind = Counter("land|land" if e["neighbour_is_terrain"] else "land|non-terrain" for e in changed_edges)
print(f"\n(2) terrain block SIDES whose border vertex profile differs disc1 vs disc4: {len(changed_edges)} {dict(nb_kind)}")
print("    land|non-terrain ones (an override in that ocean cell, welded to disc-1, would crack on disc 4):")
for e in changed_edges:
    if not e["neighbour_is_terrain"]:
        print("     ", e)
res["changed_edges"] = changed_edges

# ---------------- (3) live deployed state ----------------
gp = Path(config.find_game_path(None))
BR = re.compile(r"^Block\[(\d+)\]\[(\d+)\] (.+?)\.(ff9mesh|txt)$")
live = []
for mf in ("FF9CustomMap-world", "FF9CustomMap"):
    files = {}
    for d in (1, 4):
        root = gp / mf / "FF9_Data" / "WorldMap" / f"Disc{d}" / "0_1"
        if root.is_dir():
            for p in root.rglob("Block[[]*"):
                m = BR.match(p.name)
                if m:
                    files[(d, int(m.group(1)), int(m.group(2)), m.group(3))] = p
    keys = sorted({k[1:] for k in files})
    edge_cells = {tuple(e["neighbour"]) for e in changed_edges} | {tuple(e["cell"]) for e in changed_edges}
    for (x, y, part) in keys:
        p1, p4 = files.get((1, x, y, part)), files.get((4, x, y, part))
        h = lambda p: hashlib.md5(p.read_bytes()).hexdigest() if p else None
        pl = part.lower()
        row = next((r for r in rows if r["lod"] == "0_1" and (r["x"], r["y"]) == (x, y) and r["part"] == pl), None)
        live.append({"folder": mf, "cell": [x, y], "part": part,
                     "real_cell_parts": sorted(r4.get((x, y), set())),
                     "real_part_class": row["cls"] if row else ("(no real part)" if part != "Donor" else "sidecar"),
                     "on_disc1": p1 is not None, "on_disc4": p4 is not None,
                     "files_identical": (h(p1) == h(p4)) if (p1 and p4) else None,
                     "touches_changed_border": (x, y) in edge_cells})
lc = Counter()
for r in live:
    real = r["real_part_class"]
    tag = ("REPLACES a genuine disc-4 difference" if r["on_disc4"] and real not in
           ("IDENTICAL", "(no real part)", "sidecar") else "ok")
    r["verdict"] = tag
    lc[(r["folder"], tag)] += 1
print(f"\n(3) live deployed override files (per cell+part): {len(live)}")
print("    ", dict(lc))
for r in live:
    if r["verdict"] != "ok" or r["touches_changed_border"]:
        print("     ", r)
print("    Disc1-only (not mirrored) entries:", [(r["cell"], r["part"]) for r in live if r["on_disc1"] and not r["on_disc4"]])
print("    Disc4-only entries:", [(r["cell"], r["part"]) for r in live if r["on_disc4"] and not r["on_disc1"]])
print("    Disc1 vs Disc4 file mismatches:", [(r["cell"], r["part"]) for r in live if r["files_identical"] is False])
res["live"] = live
(OUT / "mirror_risk.json").write_text(json.dumps(res, indent=0, default=str), encoding="utf-8")
print("->", OUT / "mirror_risk.json")
