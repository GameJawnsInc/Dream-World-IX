import sys, io, contextlib
from collections import defaultdict, Counter
sys.path.insert(0,'../../ff9mapkit'); sys.path.insert(0,'.')
import contract_mass_gates as G
import seam_null_recon as SNR
core=[(x,y) for x in (13,14,15) for y in (11,12)]
with contextlib.redirect_stdout(io.StringIO()):
    cand=G.load_candidate('stock',None,core_blocks=core)
DROP={49,50,58,7,62,45,46,36,37,27,28,48,51,10,59}
core_tris=cand['core_tris']
def pct(vals,p):
    if not vals: return None
    s=sorted(vals); i=min(len(s)-1,int(p/100*len(s)))
    return s[i]
# tri height = mean y of its 3 verts (w[j][1])
def triy(t): return sum(p[1] for p in t['w'])/3.0
kept=[t for t in core_tris if t['topo'] not in DROP]
dropped=[t for t in core_tris if t['topo'] in DROP]
print("=== KEPT tris (topo not in DROP):", len(kept), "===")
ky=[triy(t) for t in kept]
print(f"  height  min {min(ky):.1f}  p50 {pct(ky,50):.1f}  p90 {pct(ky,90):.1f}  p99 {pct(ky,99):.1f}  max {max(ky):.1f}")
# per kept-topo height
print("--- per kept topo: count / p50 / p90 / max height ---")
byt=defaultdict(list)
for t in kept: byt[t['topo']].append(triy(t))
for tp in sorted(byt, key=lambda k:-len(byt[k])):
    v=byt[tp]; fam=SNR.FAM_OF.get(tp)
    print(f"  topo {tp:>3} fam={str(fam):>7} n={len(v):>4}  p50 {pct(v,50):5.1f}  p90 {pct(v,90):5.1f}  max {max(v):5.1f}")
# the CRITICAL set: the ecotone/backing kept tris that define the OUTER boundary + how many kept tris are "elevated" (>6u, >10u, >15u)
for thr in (6,10,15,20):
    hi=[t for t in kept if triy(t)>thr]
    print(f"  kept tris with height > {thr}u: {len(hi)}  ({100*len(hi)/len(kept):.1f}%)  topos={dict(Counter(t['topo'] for t in hi))}")
# specifically the ecotone-family kept tris (16/17/19/20/41) height
eco=[t for t in kept if t['topo'] in (16,17,19,20,41)]
ey=[triy(t) for t in eco]
print(f"=== ECOTONE-FAMILY kept (16/17/19/20/41) n={len(eco)}  p50 {pct(ey,50):.1f} p90 {pct(ey,90):.1f} p99 {pct(ey,99):.1f} max {max(ey):.1f} ===")
hi_eco=[t for t in eco if triy(t)>10]
print(f"  ecotone-family kept tris >10u: {len(hi_eco)}  topos={dict(Counter(t['topo'] for t in hi_eco))}")
hi_eco6=[t for t in eco if triy(t)>6]
print(f"  ecotone-family kept tris >6u: {len(hi_eco6)}  topos={dict(Counter(t['topo'] for t in hi_eco6))}")
