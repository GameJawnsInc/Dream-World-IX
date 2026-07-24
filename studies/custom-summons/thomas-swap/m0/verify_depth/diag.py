"""diag.py -- pin down the two soft spots: margin robustness + the climax box geometry.

Depends on independent_gate.py's parsed structures by re-importing its top half. To stay simple, re-parse.
"""
from __future__ import annotations
import statistics
from collections import defaultdict
import numpy as np

LOG = r"C:\gd\SCRATCH\summon-transplant\logs\sfxmeshprobe.20260724-012109.log"
EFF = 227
STALE_TOL = 5000
AABB_PAD = 8.0
NDC_MARGIN = 1.50
MIN_SIDE = 3

PHASES = [(82,144,"P1->P2"),(144,157,"P2->P3"),(157,172,"P3->P4"),(172,179,"P4->P5"),
          (179,204,"P5->P6"),(204,207,"P6->P7"),(207,250,"P7->P8"),(250,414,"P8->P9"),(414,417,"P9->P10")]
def phase_for(f):
    for lo,hi,l in PHASES:
        if lo<=f<hi: return l
    return "OUT"
def sat16(v): return -32768 if v<-32768 else (32767 if v>32767 else v)
def project(R,T,H,v):
    vx,vy,vz=int(v[0]),int(v[1]),int(v[2])
    px=((R[0]*vx+R[1]*vy+R[2]*vz)>>12)+T[0]; py=((R[3]*vx+R[4]*vy+R[5]*vz)>>12)+T[1]
    pz=((R[6]*vx+R[7]*vy+R[8]*vz)>>12)+T[2]
    if pz<=0 or H==0: return None
    sz=min(65535,pz); q=(H<<16)//sz
    return (float(160+((sat16(int(px))*q)>>16)), float(120+((sat16(int(py))*q)>>16)), float(pz))

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

class CF: __slots__=("aabb","zmin","zmax","depth","framed","csx","csy","boxw","boxh","cornpz")
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
    cf=CF()
    cf.aabb=(min(sxs)-AABB_PAD,max(sxs)+AABB_PAD,min(sys_)-AABB_PAD,max(sys_)+AABB_PAD)
    cf.zmin,cf.zmax,cf.depth=min(pzs),max(pzs),cen[2]
    cf.boxw=cf.aabb[1]-cf.aabb[0]; cf.boxh=cf.aabb[3]-cf.aabb[2]
    cf.cornpz=min(pzs)
    ndc_x=(cen[0]-160.0)/160.0; ndc_y=(120.0-cen[1])/120.0
    cf.framed=abs(ndc_x)<=NDC_MARGIN and abs(ndc_y)<=NDC_MARGIN
    cf.csx,cf.csy=cen[0],cen[1]
    creature[f]=cf

# widescreen offset (recompute)
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

# collect prims on framed frames
allp=defaultdict(list)
for line in open(LOG,encoding="utf-8",errors="replace"):
    if not line.startswith("PRIM,"): continue
    p=line.rstrip("\n").split(",")
    try:
        if int(p[1])!=EFF: continue
        f=int(p[2]); code=int(p[4]); raw=-float(p[6]); x=float(p[7]); y=float(p[8])
    except (ValueError,IndexError): continue
    cf=creature.get(f)
    if cf is None or not cf.framed: continue
    allp[f].append((raw,code,x-OFFSET,y))

# ---------- (1) per-phase box geometry ----------
print("=== per-phase creature box geometry (framed frames) ===")
print(f"  screen is 320x240. box = reprojected bone-AABB corners (+8px pad).")
print(f"  {'phase':8s} {'n':>3} {'medW':>6} {'medH':>6} {'boxes>screen':>12} {'medDepth':>9} {'medZmin':>8} {'medZmax':>8}")
for lo,hi,lab in PHASES:
    fs=[f for f in creature if lo<=f<hi and creature[f].framed]
    if not fs: continue
    ws=[creature[f].boxw for f in fs]; hs=[creature[f].boxh for f in fs]
    over=sum(1 for f in fs if creature[f].boxw>320 or creature[f].boxh>240)
    dep=[creature[f].depth for f in fs]; zmn=[creature[f].zmin for f in fs]; zmx=[creature[f].zmax for f in fs]
    print(f"  {lab:8s} {len(fs):3d} {statistics.median(ws):6.0f} {statistics.median(hs):6.0f} "
          f"{over:5d}/{len(fs):<6d} {statistics.median(dep):9.0f} {statistics.median(zmn):8.0f} {statistics.median(zmx):8.0f}")

# ---------- (2) fine margin sweep: where does P8->P9 lose NATIVE? ----------
def gate_phase(frac, lab_target, floor=64.0):
    lo,hi = next((l,h) for l,h,x in PHASES if x==lab_target)
    frmd=front=behind=strad=0
    for f in creature:
        cf=creature[f]
        if not (lo<=f<hi and cf.framed): continue
        frmd+=1
        m=max(floor,frac*cf.depth)
        nf=nb=0
        xmin,xmax,ymin,ymax=cf.aabb
        for raw,code,x,y in allp.get(f,[]):
            if not (xmin<=x<=xmax and ymin<=y<=ymax): continue
            if raw<cf.zmin-m: nf+=1
            elif raw>cf.zmax+m: nb+=1
        fr=nf>=MIN_SIDE; bh=nb>=MIN_SIDE
        if fr: front+=1
        if bh: behind+=1
        if fr and bh: strad+=1
    st=strad/frmd if frmd else 0; frr=front/frmd if frmd else 0
    v="NATIVE" if (st>0.15 or frr>0.33) else ("BORDER" if (frr>0.05 or st>0) else "HYBRID")
    return frmd,frr,st,behind/frmd if frmd else 0,v

print("\n=== fine margin sweep on P8->P9 (climax) and P1->P2 (fly-in) ===")
print(f"  {'frac':>6} | {'P8->P9 front/strad/verdict':32s} | {'P1->P2 front/strad/verdict':32s}")
for frac in [0.055,0.11,0.22,0.3,0.4,0.55,0.76,1.0,1.5,2.0]:
    a=gate_phase(frac,"P8->P9"); b=gate_phase(frac,"P1->P2")
    print(f"  {frac:6.3f} | {a[1]:5.0%} {a[2]:5.0%} {a[4]:8s}{'':11s} | {b[1]:5.0%} {b[2]:5.0%} {b[4]:8s}")

# ---------- (3) proper spatial control: small box at centroid vs small box elsewhere ----------
# 40x40 box. At the creature centroid (csx-OFFSET? no -- centroid is in creature screen space, prims are
# offset-corrected already). Compare depth-straddle rate inside a small centroid box vs small boxes at 4
# screen quadrant anchors well away from centroid.
def small_box_gate(lab_target, anchor, half=40, frac=0.055):
    """anchor: 'centroid' or (sx,sy) fixed screen point. Count front/straddle over the phase."""
    lo,hi=next((l,h) for l,h,x in PHASES if x==lab_target)
    frmd=front=strad=0
    for f in creature:
        cf=creature[f]
        if not (lo<=f<hi and cf.framed): continue
        if anchor=="centroid":
            ax,ay=cf.csx,cf.csy
        else:
            ax,ay=anchor
        frmd+=1
        m=max(64.0,frac*cf.depth)
        nf=nb=0
        for raw,code,x,y in allp.get(f,[]):
            if abs(x-ax)<=half and abs(y-ay)<=half:
                if raw<cf.zmin-m: nf+=1
                elif raw>cf.zmax+m: nb+=1
        fr=nf>=MIN_SIDE; bh=nb>=MIN_SIDE
        if fr: front+=1
        if fr and bh: strad+=1
    return frmd,(front/frmd if frmd else 0),(strad/frmd if frmd else 0)

print("\n=== spatial control: 40x40 box AT centroid vs at fixed screen anchors ===")
print("  (if straddle at an off-centroid anchor ~= at centroid, the effect depth-field is screen-wide;")
print("   if it drops, the interleave is specific to the creature's screen region)")
for lab in ("P1->P2","P8->P9"):
    c=small_box_gate(lab,"centroid")
    print(f"  {lab}: centroid  frmd={c[0]:3d} front={c[1]:5.0%} strad={c[2]:5.0%}")
    for name,anc in [("TL",(40,40)),("TR",(280,40)),("BL",(40,200)),("BR",(280,200)),("C",(160,120))]:
        r=small_box_gate(lab,anc)
        print(f"        anchor {name:2s} ({anc[0]:3d},{anc[1]:3d}): front={r[1]:5.0%} strad={r[2]:5.0%}")
