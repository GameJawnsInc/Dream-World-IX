import struct, sys, collections
import m5_motion_verify as V
b=open(sys.argv[1],'rb').read(); N=93
print(f"{'clip':>10} {'fr':>3} {'bytes':>6}  coarseTracks/279  fineTracks/279  sharedCoarseOffs  bytes/frame/bone")
for spec in sys.argv[2:]:
    m=int(spec,16); fc=V.u16(b,m+2); r0=V.u32(b,m+0xc); r1=V.u32(b,m+0x10)
    ct=ft=0; offs=set(); foffs=set()
    for k in range(N):
        a0,a1,a2,kf=struct.unpack_from('<HhHh',b,m+r0+8*k)
        for v,bit in ((a0,1),(a1&0xFFFF,2),(a2,4)):
            if not (kf&bit): ct+=1; offs.add(v)
        f0,f1,f2,ff=struct.unpack_from('<HhHh',b,m+r1+8*k)
        for v,bit in ((f0,1),(f1&0xFFFF,2),(f2,4)):
            if not (ff&bit): ft+=1; foffs.add(v)
    size=V.HDR+8*N*2 + len(offs)*fc + len(foffs)*((fc+1)//2)
    print(f"{m:#010x} {fc:3d} {size:6d}   {ct:3d} (uniq {len(offs):3d})   {ft:3d} (uniq {len(foffs):3d})   {size/(fc*N):.3f}")
