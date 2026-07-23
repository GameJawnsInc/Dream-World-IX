import struct, sys
import m5_motion_verify as V
path=sys.argv[1]; b=open(path,'rb').read()
N=93
starts=[int(x,16) for x in sys.argv[2:]]
for m in starts:
    fc=V.u16(b,m+2); fl=b[m+0xa]; r0=V.u32(b,m+0xc); r1=V.u32(b,m+0x10)
    regs=[(0,V.HDR)]
    for i,bit in enumerate((1,2,4)):
        if not (fl&bit):
            o=V.u16(b,m+4+2*i); regs.append((o,o+2*fc))
    regs.append((r0,r0+8*N)); regs.append((r1,r1+8*N))
    for tbl,span in ((r0,fc),(r1,(fc+1)//2)):
        for k in range(N):
            a0,a1,a2,kf=struct.unpack_from('<HhHh',b,m+tbl+8*k)
            for v,bit in ((a0,1),(a1&0xFFFF,2),(a2,4)):
                if not (kf&bit): regs.append((v,v+span))
    regs=sorted(set(regs)); cur=0; gap=0; ovl=0
    for a,z in regs:
        if a>cur: gap+=a-cur
        if a<cur: ovl+=min(z,cur)-a
        cur=max(cur,z)
    print(f"@{m:#08x} frames={fc:3d} flags={fl} N=93 end=+{cur:#07x} -> next@{m+cur:#08x}  gapBytes={gap} overlapBytes={ovl}")
