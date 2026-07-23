"""M5 -- validate the decoded MOTION layout against a real stock clip (STRUCTURE ONLY).

Reads a locally-extracted stock ef###.bytes from C:/gd/SCRATCH (never the repo), derives each
clip's node count from the key-table fixpoint, checks that the clip's regions TILE without
overlap, and reports statistical smoothness of the decoded tracks. Prints structure + statistics
only -- no animation payload is echoed or written.
"""
import struct, sys, os

HDR = 0x14

def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def s16(b,o): return struct.unpack_from('<h',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

def keytable_fixpoint(b, m, off, fc, span, maxn=512):
    """Largest N s.t. entries 0..N-1 are well-formed and every track offset >= off+8N."""
    best = 0
    n = 1
    while n <= maxn and m+off+8*n <= len(b):
        e = m+off+8*(n-1)
        a0,a1,a2,kf = struct.unpack_from('<HhHh', b, e)
        if kf & ~0x7: break
        ok = True
        for v,bit in ((a0,1),(a1 & 0xFFFF,2),(a2,4)):
            if not (kf & bit):
                if v < off+8*n or m+v+span > len(b): ok=False
        if not ok: break
        best = n; n += 1
    return best

def analyse(path, m, fc, fl, r0, r1):
    b = open(path,'rb').read()
    n_c = keytable_fixpoint(b, m, r0, fc, fc)
    n_f = keytable_fixpoint(b, m, r1, fc, (fc+1)//2) if r1 else None
    # region coverage
    regions = [("header", 0, HDR)]
    for i,bit in enumerate((1,2,4)):
        if not (fl & bit):
            o = u16(b, m+4+2*i); regions.append((f"trans{'XYZ'[i]}", o, o+2*fc))
    regions.append(("rotKeyTable", r0, r0+8*n_c))
    seen=set()
    for k in range(n_c):
        a0,a1,a2,kf = struct.unpack_from('<HhHh', b, m+r0+8*k)
        for v,bit,ax in ((a0,1,'X'),(a1 & 0xFFFF,2,'Y'),(a2,4,'Z')):
            if not (kf & bit) and v not in seen:
                seen.add(v); regions.append((f"coarse[{k}]{ax}", v, v+fc))
    if r1:
        regions.append(("fineKeyTable", r1, r1+8*n_f))
        seen2=set()
        for k in range(n_f):
            a0,a1,a2,kf = struct.unpack_from('<HhHh', b, m+r1+8*k)
            for v,bit,ax in ((a0,1,'X'),(a1 & 0xFFFF,2,'Y'),(a2,4,'Z')):
                if not (kf & bit) and v not in seen2:
                    seen2.add(v); regions.append((f"fine[{k}]{ax}", v, v+(fc+1)//2))
    regions.sort(key=lambda r:r[1])
    gaps=[]; overlaps=[]
    cur=0
    for name,a,z in regions:
        if a > cur: gaps.append((cur,a))
        if a < cur: overlaps.append((name,a,cur))
        cur=max(cur,z)
    # root-translation smoothness (structure metric only)
    smooth={}
    for i,bit in enumerate((1,2,4)):
        if fl & bit: smooth['XYZ'[i]]='const'; continue
        o=u16(b,m+4+2*i)
        vals=[s16(b,m+o+2*t) for t in range(fc)]
        d=[abs(vals[t+1]-vals[t]) for t in range(fc-1)]
        rng=max(vals)-min(vals)
        smooth['XYZ'[i]]=f"range={rng} maxStep={max(d) if d else 0} medStep={sorted(d)[len(d)//2] if d else 0}"
    # angle-track smoothness for node 0 (12-bit reconstruction, circular delta)
    ang={}
    for j,(ax,bit) in enumerate((('a0',1),('a1',2),('a2',4))):
        a0,a1,a2,kf = struct.unpack_from('<HhHh', b, m+r0+0)
        f0,f1,f2,ff = struct.unpack_from('<HhHh', b, m+r1+0) if r1 else (0,0,0,7)
        coarse=(a0,a1 & 0xFFFF,a2)[j]; fine=(f0,f1 & 0xFFFF,f2)[j]
        if kf & bit: ang[ax]='const'; continue
        seq=[]
        for t in range(fc):
            c=b[m+coarse+t]
            v=(c<<4)
            if r1 and not (ff & bit):
                by=b[m+fine+(t>>1)]
                v |= ((by>>4) if (t&1) else by) & 0xF
            seq.append(v)
        d=[min((seq[t+1]-seq[t])%4096,(seq[t]-seq[t+1])%4096) for t in range(fc-1)]
        ang[ax]=f"maxStep={max(d)} medStep={sorted(d)[len(d)//2]} (of 4096)"
    return dict(motion=m, frames=fc, flags=fl, nodes_coarse=n_c, nodes_fine=n_f,
                span=cur, gaps=gaps, overlaps=overlaps, trans=smooth, node0_angles=ang)

if __name__=='__main__':
    path=sys.argv[1]
    for spec in sys.argv[2:]:
        m=int(spec,16)
        b=open(path,'rb').read()
        fc=u16(b,m+2); fl=b[m+0xa]; r0=u32(b,m+0xc); r1=u32(b,m+0x10)
        r=analyse(path,m,fc,fl,r0,r1)
        print(f"--- motion @{m:#08x}")
        for k,v in r.items(): print(f"    {k}: {v}")
