"""Donor spec sheet for the shortlisted small coastal structures."""
import sys, json, math
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")
from ff9mapkit.world import extract as X

CAND = {
 "Alexandria Harbour": [(21,10)],
 "Lindblum Harbour":   [(13,17)],
 "Lindblum Dragon Gate":[(14,15)],
 "unnamed gatehouse":  [(22,14)],
 "Chocobo Lagoon":     [(9,17)],
 "Quan Dwelling cave": [(21,14)],
 "Fossil Roo portal":  [(14,6)],
 "Black Mage Village": [(14,6)],
 "Madain Sari":        [(14,2),(14,3)],
 "Water Shrine spires":[(3,9)],
 "Wind Shrine":        [(7,13),(7,14),(8,13),(8,14)],
 "Desert Palace mound":[(18,4)],
 "Earth Shrine trio":  [(18,5)],
 "CP Mountain bridge": [(13,4)],
 "Mognet Central quad":[(16,1)],
}
for name, blks in CAND.items():
    print("="*100)
    print(f"{name}   blocks {blks}")
    for (bx,by) in blks:
        bm = X.read_block(bx,by,disc=1,part="object")
        tan=bm.tangents
        ids=[int(round(tan[bm.flat_index[t*3]][0])) for t in range(len(bm.tris))]
        cnt=Counter(ids)
        V=bm.verts
        print(f"  Block[{bx}][{by}] Object: {len(bm.tris)} tri / {bm.vcount} v / stride {bm.stride} / "
              f"16-bit idx={not bm.use32} / submeshes={bm.submeshes} / roundtrip={X.roundtrip_ok(bm)}")
        print(f"    LOCAL bbox  x[{min(v[0] for v in V):7.3f},{max(v[0] for v in V):7.3f}] "
              f"y[{min(v[1] for v in V):7.3f},{max(v[1] for v in V):7.3f}] "
              f"z[{min(v[2] for v in V):7.3f},{max(v[2] for v in V):7.3f}]")
        print(f"    WORLD bbox  x[{min(v[0] for v in V)+bx*64:8.2f},{max(v[0] for v in V)+bx*64:8.2f}] "
              f"z[{min(v[2] for v in V)-by*64:9.2f},{max(v[2] for v in V)-by*64:9.2f}]")
        for k in sorted(cnt):
            d=X.decode_id(k)
            runs=[]; start=None
            for t in range(len(ids)+1):
                cur = t<len(ids) and ids[t]==k
                if cur and start is None: start=t
                if not cur and start is not None: runs.append((start,t-1)); start=None
            print(f"    idall {k:6d} 0x{k:04X} event={d['event']} area={d['area']:2d} topo={d['topograph']:2d} "
                  f"flags={d['flags']}  tris={cnt[k]:4d}  tri-index runs={runs if len(runs)<=6 else str(runs[:6])+'...'}")
        U=bm.uvs
        print(f"    UV span u[{min(u[0] for u in U):.4f},{max(u[0] for u in U):.4f}] "
              f"v[{min(u[1] for u in U):.4f},{max(u[1] for u in U):.4f}]  (object atlas res(1_24)_objects 1024^2)")
