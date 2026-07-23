import sys; sys.path.insert(0,'.')
import ef_container as ec
blob=open("C:/gd/SCRATCH/summon-format/ef227.bytes",'rb').read()
c=ec.parse_header(blob)
for ch in c.chunks:
    for r in ch.resources:
        if r.id==5:
            print("id5 res at", hex(r.offset), "size", hex(r.nbytes))
            try:
                g=ec.parse_geom(blob, r.offset, block_end=r.offset+r.nbytes)
                print("  flags",hex(g.flags),"bones",g.bone_count,"meshes",g.mesh_count)
                for m in g.meshes:
                    print("   mesh",m.index,"prims",dict(zip([p[0] for p in ec.PRIM_TYPES],m.counts)),"nvert",m.n_vert)
                print("  checks", ec.geom_checks(blob,g,limit=r.offset+r.nbytes))
            except Exception as e:
                print("  ERR",e)
