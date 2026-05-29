import struct, sys, shutil
def i16(b,o): return struct.unpack_from('<h',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def w16(b,o,v): struct.pack_into('<h',b,o,v)

SLOT_PAIRS = [(0,2),(0,1),(1,2)]  # slot0=(v0,v2), slot1=(v0,v1), slot2=(v1,v2)

def fix(path):
    b=bytearray(open(path,'rb').read())
    base=6+5*6
    p=base+4
    triCount=u16(b,p); triOffset=u16(b,p+2)
    edgeCount=u16(b,p+4); edgeOffset=u16(b,p+6)
    to=4+triOffset; eo=4+edgeOffset
    tris=[]
    for t in range(triCount):
        o=to+t*40
        vtx=[i16(b,o+12+2*k) for k in range(3)]
        edg=[i16(b,o+18+2*k) for k in range(3)]
        nbr=[i16(b,o+24+2*k) for k in range(3)]
        tris.append({'o':o,'vtx':vtx,'edg':edg,'nbr':nbr})
    # reset ALL neighbor links + edgeClones, then rebuild from shared-vertex analysis
    for t in tris:
        for k in range(3): w16(b,t['o']+24+2*k,-1)
    for e in range(edgeCount): w16(b,eo+e*4+2,-1)
    # find shared edges between triangle pairs
    def slot_of(tri,a,c):
        s=set((a,c))
        for k,(i,j) in enumerate(SLOT_PAIRS):
            if set((tri['vtx'][i],tri['vtx'][j]))==s: return k
        return None
    links=0
    for ia in range(triCount):
        for ib in range(ia+1,triCount):
            shared=set(tris[ia]['vtx'])&set(tris[ib]['vtx'])
            if len(shared)==2:
                a,c=tuple(shared)
                sa=slot_of(tris[ia],a,c); sb=slot_of(tris[ib],a,c)
                if sa is None or sb is None:
                    print(f"  !! tri{ia}/tri{ib} share {shared} but slot map failed"); continue
                w16(b,tris[ia]['o']+24+2*sa, ib)
                w16(b,tris[ib]['o']+24+2*sb, ia)
                # edgeClone = the neighbor's slot
                w16(b, eo+tris[ia]['edg'][sa]*4+2, sb)
                w16(b, eo+tris[ib]['edg'][sb]*4+2, sa)
                links+=1
                print(f"  linked tri{ia}[slot{sa},edge{tris[ia]['edg'][sa]}] <-> tri{ib}[slot{sb},edge{tris[ib]['edg'][sb]}] (shared {shared})")
    print(f"  total internal edges linked: {links}")
    return bytes(b)

path=sys.argv[1]
shutil.copy(path, path+".prefix.bak")
out=fix(path)
open(path,'wb').write(out)
print("WROTE",path)
