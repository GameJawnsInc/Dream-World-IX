"""M5 -- falsifiable test: does the logged ROOT (SummonData+0x40) project onto the creature's
on-screen silhouette? Uses only the probe's OWN log (decoded runtime state, no asset bytes)."""
import sys, collections, itertools, math
LOG=r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/sfxmeshprobe.log"
view={}; proj={}; root={}; mesh=collections.defaultdict(list)
for ln in open(LOG,'r',errors='ignore'):
    p=ln.rstrip('\n').split(',')
    if p[0]=='VIEW': view[int(p[1])]=[float(x) for x in p[2:18]]
    elif p[0]=='PROJ': proj[int(p[1])]=[float(x) for x in p[2:18]]
    elif p[0]=='ROOT': root[int(p[2])]=[int(x) for x in p[3:]]
    elif p[0]=='MESH':
        f=int(p[2]); mesh[f].append((p[4], int(p[5]), int(p[6]), float(p[7]), float(p[8]), float(p[10]), float(p[11])))
print(f"frames: VIEW {len(view)} ROOT {len(root)} MESH {len(mesh)}")
keys=collections.Counter(k for f in mesh for (k,vc,tc,cx,cy,ex,ey) in mesh[f])
print("mesh keys by row count:", keys.most_common(12))
cxs=[cx for f in mesh for (k,vc,tc,cx,cy,ex,ey) in mesh[f]]
cys=[cy for f in mesh for (k,vc,tc,cx,cy,ex,ey) in mesh[f]]
print(f"MESH centroid ranges: cx {min(cxs):.1f}..{max(cxs):.1f}  cy {min(cys):.1f}..{max(cys):.1f}")

def mul(m, v):
    return [sum(m[r*4+c]*v[c] for c in range(4)) for r in range(4)]

def project(f, sx, sy, sz, scale, W, H):
    V=view[f]; P=proj[f]; R=root[f]
    t=[R[10]*sx*scale, R[11]*sy*scale, R[12]*sz*scale, 1.0]
    c=mul(P, mul(V, t))
    if abs(c[3])<1e-9: return None
    x=(c[0]/c[3]*0.5+0.5)*W; y=(1-(c[1]/c[3]*0.5+0.5))*H
    return x,y

frames=[f for f in sorted(root) if f in view and f in mesh and any(v!=0 for v in root[f][1:])]
print(f"testable frames: {len(frames)}")
best=None
for sx,sy,sz in itertools.product((1,-1),repeat=3):
    for scale in (1.0, 1/1.0):
        for (W,H) in ((320,240),(640,480),(400,300)):
            errs=[]
            for f in frames:
                pr=project(f,sx,sy,sz,scale,W,H)
                if pr is None: continue
                # nearest mesh centroid this frame
                d=min(math.hypot(pr[0]-cx, pr[1]-cy) for (k,vc,tc,cx,cy,ex,ey) in mesh[f])
                errs.append(d)
            if not errs: continue
            errs.sort(); med=errs[len(errs)//2]
            if best is None or med<best[0]: best=(med,sx,sy,sz,scale,W,H)
print("best sign/viewport combo (median px error to nearest mesh centroid):", best)
