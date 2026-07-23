import collections, math, itertools
LOG=r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/sfxmeshprobe.log"
BODY={'0033B990','0033B9D0','0035BA90','0034BA50','0034BA10','0035BAD0','0097BD02'}
view={};proj={};root={};mesh=collections.defaultdict(list)
for ln in open(LOG,'r',errors='ignore'):
    p=ln.rstrip('\n').split(',')
    if p[0]=='VIEW': view[int(p[1])]=[float(x) for x in p[2:18]]
    elif p[0]=='PROJ': proj[int(p[1])]=[float(x) for x in p[2:18]]
    elif p[0]=='ROOT': root[int(p[2])]=[int(x) for x in p[3:]]
    elif p[0]=='MESH': mesh[int(p[2])].append((p[4],int(p[6]),float(p[7]),float(p[8])))
def mul(m,v): return [sum(m[r*4+c]*v[c] for c in range(4)) for r in range(4)]
def body_centroid(f):
    rows=[(tc,cx,cy) for (k,tc,cx,cy) in mesh.get(f,[]) if k in BODY and tc>0]
    if not rows: return None
    W=sum(r[0] for r in rows)
    return (sum(r[0]*r[1] for r in rows)/W, sum(r[0]*r[2] for r in rows)/W)
def pearson(a,b):
    n=len(a); ma=sum(a)/n; mb=sum(b)/n
    va=sum((x-ma)**2 for x in a); vb=sum((y-mb)**2 for y in b)
    if va==0 or vb==0: return 0.0
    return sum((a[i]-ma)*(b[i]-mb) for i in range(n))/math.sqrt(va*vb)
frames=[f for f in sorted(root) if f in view and body_centroid(f) and any(v!=0 for v in root[f][1:])]
print("frames with body meshes + nonzero root:", len(frames))
best=[]
for sx,sy,sz in itertools.product((1,-1),repeat=3):
    px=[];py=[];bx=[];by=[]
    for f in frames:
        V=view[f];P=proj[f];R=root[f]
        c=mul(P,mul(V,[R[10]*sx,R[11]*sy,R[12]*sz,1.0]))
        if abs(c[3])<1e-6: continue
        px.append(c[0]/c[3]); py.append(c[1]/c[3])
        b=body_centroid(f); bx.append(b[0]); by.append(b[1])
    best.append((pearson(px,bx),pearson(py,by),(sx,sy,sz)))
best.sort(key=lambda r:-(abs(r[0])+abs(r[1])))
for r in best: print(f"  signs {r[2]}  corr(ndcX,bodyCx)={r[0]:+.3f}  corr(ndcY,bodyCy)={r[1]:+.3f}")
# control: does the body centroid move at all?
bs=[body_centroid(f) for f in frames]
print(f"body centroid X range {min(b[0] for b in bs):.1f}..{max(b[0] for b in bs):.1f}  Y {min(b[1] for b in bs):.1f}..{max(b[1] for b in bs):.1f}")
