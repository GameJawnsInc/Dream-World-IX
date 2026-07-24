"""final_checks.py -- close two fairness questions:
 (A) body-FT3 overshoot restricted to the TIGHT-BOX fly-in frames (fair reproduction of the 0.055 calib,
     removing the climax whole-screen contamination that inflated my earlier 0.76).
 (B) LOCALITY-constrained straddle for P8->P9: require a front prim and a behind prim within the SAME
     ~80px neighborhood (not just the same screen-sized box) -- tests whether the 28% straddle is real
     per-location interleave or bounding-box aggregation of spatially-separate near/far effects.
"""
from __future__ import annotations
import statistics
from collections import defaultdict
import numpy as np

LOG=r"C:\gd\SCRATCH\summon-transplant\logs\sfxmeshprobe.20260724-012109.log"
EFF=227; STALE_TOL=5000; AABB_PAD=8.0; NDC_MARGIN=1.50; MIN_SIDE=3; FT3=36
def sat16(v): return -32768 if v<-32768 else (32767 if v>32767 else v)
def project(R,T,H,v):
    vx,vy,vz=int(v[0]),int(v[1]),int(v[2])
    px=((R[0]*vx+R[1]*vy+R[2]*vz)>>12)+T[0]; py=((R[3]*vx+R[4]*vy+R[5]*vz)>>12)+T[1]
    pz=((R[6]*vx+R[7]*vy+R[8]*vz)>>12)+T[2]
    if pz<=0 or H==0: return None
    sz=min(65535,pz); q=(H<<16)//sz
    return (float(160+((sat16(int(px))*q)>>16)),float(120+((sat16(int(py))*q)>>16)),float(pz))
psxcam,bones,smodel={},{},{}
for line in open(LOG,encoding="utf-8",errors="replace"):
    if not line or line[0]=="#": continue
    p=line.rstrip("\n").split(",")
    t=p[0]
    try:
        if t=="PSXCAM" and int(p[1])==EFF:
            f=int(p[2]); psxcam[f]=([int(x) for x in p[3:12]],[int(x) for x in p[12:15]],int(p[17]))
        elif t=="BONES" and int(p[1])==EFF:
            f=int(p[2]); bones[f]=dict(cx=float(p[4]),cy=float(p[5]),cz=float(p[6]),mnx=float(p[7]),mny=float(p[8]),
                mnz=float(p[9]),mxx=float(p[10]),mxy=float(p[11]),mxz=float(p[12]))
        elif t=="MODEL" and len(p)>26 and p[3]=="S" and int(p[1])==EFF:
            f=int(p[2]); smodel[f]=(p[26],int(p[14]),int(p[15]),int(p[16]),int(p[11]),int(p[12]),int(p[13]))
    except (ValueError,IndexError): continue
reliable=set()
for f,(b32,wx,wy,wz,ax,ay,az) in smodel.items():
    if b32=="00000000": continue
    if abs(wx-ax)>STALE_TOL or abs(wy-ay)>STALE_TOL or abs(wz-az)>STALE_TOL: continue
    reliable.add(f)
class CF: __slots__=("aabb","zmin","zmax","depth","framed","csx","csy","boxw")
creature={}
for f in reliable:
    cam=psxcam.get(f); b=bones.get(f)
    if cam is None or b is None: continue
    R,T,H=cam
    corners=[(x,y,z) for x in (b["mnx"],b["mxx"]) for y in (b["mny"],b["mxy"]) for z in (b["mnz"],b["mxz"])]
    sxs,sys_,pzs=[],[],[]
    for c in corners:
        pr=project(R,T,H,c)
        if pr: sxs.append(pr[0]); sys_.append(pr[1]); pzs.append(pr[2])
    if not sxs: continue
    cen=project(R,T,H,(b["cx"],b["cy"],b["cz"]))
    if cen is None: continue
    cf=CF(); cf.aabb=(min(sxs)-AABB_PAD,max(sxs)+AABB_PAD,min(sys_)-AABB_PAD,max(sys_)+AABB_PAD)
    cf.zmin,cf.zmax,cf.depth=min(pzs),max(pzs),cen[2]; cf.boxw=cf.aabb[1]-cf.aabb[0]
    nx=(cen[0]-160)/160; ny=(120-cen[1])/120; cf.framed=abs(nx)<=NDC_MARGIN and abs(ny)<=NDC_MARGIN
    cf.csx,cf.csy=cen[0],cen[1]; creature[f]=cf
deltas=[]
for line in open(LOG,encoding="utf-8",errors="replace"):
    if not line.startswith("PRIM,"): continue
    p=line.rstrip("\n").split(",")
    try:
        if int(p[1])!=EFF: continue
        f=int(p[2]); raw=-float(p[6]); x=float(p[7]); y=float(p[8])
    except (ValueError,IndexError): continue
    cf=creature.get(f)
    if cf is None or not cf.framed: continue
    if abs(y-cf.csy)>8.0: continue
    if abs(raw-cf.depth)>0.10*max(1.0,cf.depth): continue
    deltas.append(x-cf.csx)
OFFSET=statistics.median(deltas) if len(deltas)>=8 else 0.0

allp=defaultdict(list)
for line in open(LOG,encoding="utf-8",errors="replace"):
    if not line.startswith("PRIM,"): continue
    p=line.rstrip("\n").split(",")
    try:
        if int(p[1])!=EFF: continue
        f=int(p[2]); code=int(p[4]); raw=-float(p[6]); x=float(p[7])-OFFSET; y=float(p[8])
    except (ValueError,IndexError): continue
    cf=creature.get(f)
    if cf is None or not cf.framed: continue
    allp[f].append((raw,code,x,y))

# (A) fly-in-only body-FT3 overshoot (tight-box frames: boxw<=320)
print("=== (A) body-FT3 overshoot beyond band, restricted to TIGHT-box fly-in frames (fair 0.055 check) ===")
for name,cond in [("P1->P2 fly-in tight-box (boxw<=320)", lambda f:82<=f<144 and creature[f].boxw<=320),
                  ("P1->P2 fly-in ALL",                   lambda f:82<=f<144),
                  ("whole cast tight-box (boxw<=320)",    lambda f:creature[f].boxw<=320)]:
    ov=[]
    for f in creature:
        cf=creature[f]
        if not cf.framed or not cond(f): continue
        xmin,xmax,ymin,ymax=cf.aabb
        for raw,code,x,y in allp.get(f,[]):
            if (code&252)!=FT3: continue
            if not (xmin<=x<=xmax and ymin<=y<=ymax): continue
            if raw<cf.zmin: ov.append((cf.zmin-raw)/max(1.0,cf.depth))
            elif raw>cf.zmax: ov.append((raw-cf.zmax)/max(1.0,cf.depth))
    if ov:
        a=np.array(ov)
        nf=sum(1 for f in creature if creature[f].framed and cond(f))
        print(f"  {name:42s}: frames={nf:3d} n={len(a):6d}  p50={np.percentile(a,50):.3f} "
              f"p90={np.percentile(a,90):.3f} p99={np.percentile(a,99):.3f}")

# (B) locality-constrained straddle for P8->P9 and P1->P2
print("\n=== (B) locality-constrained straddle (front & behind prim within R px of EACH OTHER) ===")
def straddle_rate(lo,hi,R,frac=0.055):
    frmd=box_strad=loc_strad=0
    for f in creature:
        cf=creature[f]
        if not (lo<=f<hi and cf.framed): continue
        frmd+=1
        m=max(64.0,frac*cf.depth); xmin,xmax,ymin,ymax=cf.aabb
        fronts=[]; behinds=[]
        for raw,code,x,y in allp.get(f,[]):
            if not (xmin<=x<=xmax and ymin<=y<=ymax): continue
            if raw<cf.zmin-m: fronts.append((x,y))
            elif raw>cf.zmax+m: behinds.append((x,y))
        if len(fronts)>=MIN_SIDE and len(behinds)>=MIN_SIDE:
            box_strad+=1
            # locality: does some front prim have >=MIN_SIDE-1 behind prims within R, and vice versa?
            # cheap: is there ANY front-behind pair within R?
            found=False
            fb=np.array(fronts); bb=np.array(behinds)
            for fx,fy in fb:
                if np.any((np.abs(bb[:,0]-fx)<=R)&(np.abs(bb[:,1]-fy)<=R)):
                    found=True; break
            if found: loc_strad+=1
    return frmd,box_strad,loc_strad
for lab,lo,hi in [("P1->P2",82,144),("P8->P9",250,414)]:
    for R in (240,120,60,30):
        frmd,bx,lc=straddle_rate(lo,hi,R)
        print(f"  {lab} R={R:3d}px: frmd={frmd:3d}  box-straddle={bx/frmd:5.0%}  locality-straddle={lc/frmd:5.0%}")
    print()
