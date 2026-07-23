import sys, glob, os
sys.path.insert(0,'.')
import ef_container as ec
SC = "C:/gd/SCRATCH/summon-format"
CREATURE = "ef038 ef177 ef179 ef184 ef186 ef210 ef211 ef225 ef226 ef227 ef251 ef261 ef276 ef381 ef431 ef432 ef435 ef438 ef439 ef447 ef493 ef494 ef495 ef498".split()
for name in CREATURE:
    p = os.path.join(SC, name+".bytes")
    if not os.path.exists(p): print(name,"MISSING"); continue
    blob = open(p,'rb').read()
    try:
        c = ec.parse_header(blob)
    except Exception as e:
        print(name,"hdr err",e); continue
    got=False
    for ch in c.chunks:
        try:
            mp = ec.parse_model_package(blob, ch)
        except Exception as e:
            mp=None
        if mp is None: continue
        for res in ch.resources:
            if res.id==5:
                try:
                    g = ec.find_geom(blob, res)
                except Exception as e:
                    g=None
                if g: print(f"{name}: meshCount={g.mesh_count} boneCount={g.bone_count}"); got=True
    if not got: print(name, "no geom")
