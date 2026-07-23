import sys,os; sys.path.insert(0,'.')
import ef_container as ec
SC="C:/gd/SCRATCH/summon-format"
CRE="ef038 ef177 ef179 ef184 ef186 ef210 ef211 ef225 ef226 ef227 ef251 ef261 ef276 ef381 ef431 ef432 ef435 ef438 ef439 ef447 ef493 ef494 ef495 ef498".split()
dist={}
for n in CRE:
    blob=open(os.path.join(SC,n+".bytes"),'rb').read()
    c=ec.parse_header(blob); found=[]
    for ch in c.chunks:
        for r in ch.resources:
            if r.id==5:
                try:
                    g=ec.parse_geom(blob,r.offset,block_end=r.offset+r.nbytes)
                    found.append((g.bone_count,g.mesh_count))
                except Exception as e: found.append(("ERR",str(e)[:30]))
    print(n,found)
    for f in found:
        if isinstance(f[1],int): dist[f[1]]=dist.get(f[1],0)+1
print("meshCount distribution:",dist)
