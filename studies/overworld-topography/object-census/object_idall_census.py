"""READ-ONLY: map-wide census of stock world OBJECT-mesh IDALL values (disc 1).
Answers: what idall do stock landmarks carry, and do the engine SKIP ids {4078,4088,2040} appear?"""
import sys, collections, json
sys.path.insert(0, r"C:\gd\Dream-World-IX\.claude\worktrees\gui-workspace-improvements-277c74\ff9mapkit")
from ff9mapkit.world import transplant as T

SKIP = {4078, 4088, 2040}
hist_obj = collections.Counter()
hist_ter_skip = collections.Counter()
blocks_with_obj = []
for by in range(20):
    for bx in range(24):
        try:
            tris = T.world_tris(bx, by, "object", disc=1, lod="0_1", game=None) or []
        except Exception:
            tris = []
        if not tris:
            continue
        h = collections.Counter()
        for t in tris:
            i = int(round(t[0][3][0]))
            h[i] += 1
            hist_obj[i] += 1
        blocks_with_obj.append({"block": [bx, by], "tris": len(tris),
                                "idall": {str(k): v for k, v in sorted(h.items())}})
        # does this block's TERRAIN use any skip id?
        try:
            tt = T.world_tris(bx, by, "terrain", disc=1, lod="0_1", game=None) or []
        except Exception:
            tt = []
        for t in tt:
            i = int(round(t[0][3][0]))
            if i in SKIP:
                hist_ter_skip[i] += 1

print("blocks WITH a stock Object mesh: %d" % len(blocks_with_obj))
tot = sum(hist_obj.values())
print("total stock Object tris: %d" % tot)
print("\n=== OBJECT idall histogram (all blocks, disc 1) ===")
for k, v in sorted(hist_obj.items(), key=lambda kv: -kv[1]):
    print("  idall=%-6d (0x%04X) ev=%d area=%-3d topo=%-3d flags=%d  tris=%-6d %s"
          % (k, k, (k & 0xC000) >> 14, (k & 0x3F00) >> 8, (k & 0xFC) >> 2, k & 3, v,
             "<-- ENGINE SKIP ID" if k in SKIP else ""))
print("\nSKIP ids present in OBJECT meshes:", {k: v for k, v in hist_obj.items() if k in SKIP} or "NONE")
print("SKIP ids present in TERRAIN of object-bearing blocks:", dict(hist_ter_skip) or "NONE")

print("\n=== SMALLEST stock Object meshes (candidate small-structure donors) ===")
for e in sorted(blocks_with_obj, key=lambda e: e["tris"])[:14]:
    bx, by = e["block"]
    print("  block(%2d,%2d)  %4d tris   world x[%d..%d] z[%d..%d]  idall=%s"
          % (bx, by, e["tris"], bx * 64, bx * 64 + 64, -(by * 64 + 64), -(by * 64), e["idall"]))

out = r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX--claude-worktrees-gui-workspace-improvements-277c74\73e87cb6-c7f0-4578-9bec-fbe36ba8421f\scratchpad\object_census.json"
json.dump({"blocks": blocks_with_obj, "idall_hist": {str(k): v for k, v in hist_obj.items()}},
          open(out, "w"), indent=1)
print("\nfull census ->", out)
