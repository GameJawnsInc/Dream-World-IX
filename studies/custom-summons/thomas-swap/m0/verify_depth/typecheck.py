"""typecheck.py -- are the FRONT prims (nearer than the body band) genuine effect types (FT4/BLUR/SPRT)
or body-type (FT3)? A FRONT population dominated by FT3 would be body-skin-forward leakage (weakens the
verdict); dominated by FT4/BLUR/effect types = a real foreground effect layer (supports it).

Also: the FT4_BLUR foreground burst DEPTH-GATE sec 2.1 places at otz~=30 -- does it show up in P8->P9?
"""
from __future__ import annotations
import statistics
from collections import defaultdict, Counter

LOG=r"C:\gd\SCRATCH\summon-transplant\logs\sfxmeshprobe.20260724-012109.log"
EFF=227; STALE_TOL=5000; AABB_PAD=8.0; NDC_MARGIN=1.50
LABELS={32:"F3",36:"FT3",40:"F4",44:"FT4",48:"G3",52:"GT3",56:"G4",60:"GT4",64:"LINE_F2",
        68:"FT4_BLUR",72:"GT4_BLUR",76:"FT4_POINT",80:"LINE_G2",96:"TILE",100:"SPRT",
        104:"TILE_1",112:"TILE_8",116:"SPRT_8",120:"TILE_16",124:"SPRT_16"}
PHASES=[(82,144,"P1->P2"),(250,414,"P8->P9")]
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
class CF: __slots__=("aabb","zmin","zmax","depth","framed","csx","csy")
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
    cf.zmin,cf.zmax,cf.depth=min(pzs),max(pzs),cen[2]
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

frac=0.055
front_types=defaultdict(Counter); behind_types=defaultdict(Counter); inband_types=defaultdict(Counter)
front_otz=defaultdict(list)
for line in open(LOG,encoding="utf-8",errors="replace"):
    if not line.startswith("PRIM,"): continue
    p=line.rstrip("\n").split(",")
    try:
        if int(p[1])!=EFF: continue
        f=int(p[2]); code=int(p[4]); raw=-float(p[6]); x=float(p[7])-OFFSET; y=float(p[8])
    except (ValueError,IndexError): continue
    cf=creature.get(f)
    if cf is None or not cf.framed: continue
    lab=None
    for lo,hi,l in PHASES:
        if lo<=f<hi: lab=l; break
    if lab is None: continue
    xmin,xmax,ymin,ymax=cf.aabb
    if not (xmin<=x<=xmax and ymin<=y<=ymax): continue
    m=max(64.0,frac*cf.depth)
    tl=LABELS.get(code&252,f"c{code}")
    if raw<cf.zmin-m:
        front_types[lab][tl]+=1; front_otz[lab].append(raw)
    elif raw>cf.zmax+m:
        behind_types[lab][tl]+=1
    else:
        inband_types[lab][tl]+=1

for lab in ("P1->P2","P8->P9"):
    print(f"\n=== {lab} inside-silhouette prim type composition (nominal frac 0.055) ===")
    for name,c in (("FRONT (nearer than body)",front_types[lab]),
                   ("IN-BAND (body depth)",inband_types[lab]),
                   ("BEHIND (farther than body)",behind_types[lab])):
        tot=sum(c.values())
        top=", ".join(f"{k}={v}({v*100//max(1,tot)}%)" for k,v in c.most_common(5))
        print(f"  {name:30s} n={tot:7d}  {top}")
    fo=front_otz[lab]
    if fo:
        fo.sort()
        print(f"  FRONT raw-otz: min={fo[0]:.0f} p10={fo[len(fo)//10]:.0f} p50={fo[len(fo)//2]:.0f} "
              f"(smaller=nearer; the FT4_BLUR foreground burst DEPTH-GATE places at ~30)")
