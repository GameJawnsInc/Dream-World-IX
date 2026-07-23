import collections, math, itertools
LOG=r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/sfxmeshprobe.log"
view={};proj={};root={};mesh=collections.defaultdict(list)
for ln in open(LOG,'r',errors='ignore'):
    p=ln.rstrip('\n').split(',')
    if p[0]=='VIEW': view[int(p[1])]=tuple(float(x) for x in p[2:18])
    elif p[0]=='PROJ': proj[int(p[1])]=tuple(float(x) for x in p[2:18])
    elif p[0]=='ROOT': root[int(p[2])]=tuple(int(x) for x in p[3:])
    elif p[0]=='MESH': mesh[int(p[2])].append((p[4],int(p[6]),float(p[7]),float(p[8])))
def mul(m,v): return [sum(m[r*4+c]*v[c] for c in range(4)) for r in range(4)]
def pearson(a,b):
    n=len(a); ma=sum(a)/n; mb=sum(b)/n
    va=sum((x-ma)**2 for x in a); vb=sum((y-mb)**2 for y in b)
    return 0.0 if va==0 or vb==0 else sum((a[i]-ma)*(b[i]-mb) for i in range(n))/math.sqrt(va*vb)
# per-key centroid series; use only keys present in >=200 frames
keyframes=collections.defaultdict(dict)
for f,rows in mesh.items():
    for (k,tc,cx,cy) in rows:
        if tc>0: keyframes[k][f]=(cx,cy)
cand=[k for k,d in keyframes.items() if len(d)>=200]
print("candidate keys:",len(cand))
# static-camera consecutive pairs where ROOT changed
pairs=[]
for f in sorted(root):
    g=f+1
    if g in root and f in view and g in view and view[f]==view[g] and proj[f]==proj[g] and root[f]!=root[g]:
        pairs.append((f,g))
print("static-camera pairs with a ROOT change:",len(pairs))
for sx,sy,sz in [(1,-1,-1),(1,1,1),(1,-1,1),(1,1,-1)]:
    dpx=[];dpy=[];rows=[]
    for f,g in pairs:
        V=view[f];P=proj[f]
        a=mul(P,mul(V,[root[f][10]*sx,root[f][11]*sy,root[f][12]*sz,1.0]))
        b=mul(P,mul(V,[root[g][10]*sx,root[g][11]*sy,root[g][12]*sz,1.0]))
        if abs(a[3])<1e-6 or abs(b[3])<1e-6: continue
        dpx.append(b[0]/b[3]-a[0]/a[3]); dpy.append(b[1]/b[3]-a[1]/a[3]); rows.append((f,g))
    out=[]
    for k in cand:
        d=keyframes[k]
        ax=[];ay=[];bx=[];by=[]
        for i,(f,g) in enumerate(rows):
            if f in d and g in d:
                ax.append(dpx[i]); ay.append(dpy[i]); bx.append(d[g][0]-d[f][0]); by.append(d[g][1]-d[f][1])
        if len(ax)>=50: out.append((abs(pearson(ax,bx))+abs(pearson(ay,by)), k, pearson(ax,bx), pearson(ay,by), len(ax)))
    out.sort(reverse=True)
    print(f"signs {(sx,sy,sz)}: best keys ->", [(k,f"{cx:+.2f}/{cy:+.2f}",n) for _,k,cx,cy,n in out[:4]])
