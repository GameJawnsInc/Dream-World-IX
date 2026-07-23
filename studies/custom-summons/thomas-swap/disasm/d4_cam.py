import sys; sys.path.insert(0,'.')
import ef_container as ec
blob=open("C:/gd/SCRATCH/summon-format/ef227.bytes",'rb').read()
c=ec.parse_header(blob)
ops=ec.parse_sequence(blob)
cur=None
print("tick  op  args")
tick=0
for o in ops:
    if o.code==0x05: cur=o.arg1
    if o.code in (0x23,0x29):
        print(f"  op {o.code:#04x} arg1={o.arg1} arg2={o.arg2} chunk={cur} at file {o.at:#x}")
# sub-file dirs
for ch in c.chunks:
    for r in ch.resources:
        if r.id==2:
            d=ec.parse_directory(blob, r.offset)
            print("chunk",ch.index,"id2 at",hex(r.offset),"entries",len(d))
            for i in (0,1,2,3,4,5):
                if i+1<len(d):
                    print("   sub",i,"off",hex(d[i]),"len",d[i+1]-d[i])
