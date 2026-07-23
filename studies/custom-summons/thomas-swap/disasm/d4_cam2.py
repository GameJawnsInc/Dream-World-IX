import sys; sys.path.insert(0,'.')
import ef_container as ec
blob=open("C:/gd/SCRATCH/summon-format/ef227.bytes",'rb').read()
c=ec.parse_header(blob)
for k,ch in enumerate(c.chunks):
    for r in ch.resources:
        if r.id==2:
            d=ec.parse_directory(blob, r.offset)
            print("chunk ordinal",k,"id2 at",hex(r.offset),"entries",len(d))
            for i in (6,16,47):
                if i < len(d):
                    end = d[i+1] if i+1<len(d) else r.nbytes
                    print("   sub",i,"off",hex(d[i]),"len",end-d[i], "flags", hex(int.from_bytes(blob[r.offset+d[i]:r.offset+d[i]+2],'little')))
