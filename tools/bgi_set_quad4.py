# Set 4 arbitrary walkmesh corners (y=0) + recompute tri centers. Keeps neighbor links.
# Vert order around the quad: v0,v1,v2,v3 (tri0=v0v1v2, tri1=v0v2v3, diagonal v0-v2).
# Usage: bgi_set_quad4.py file x0 z0 x1 z1 x2 z2 x3 z3
import struct, sys
def w16(b,o,v): struct.pack_into('<h',b,o,int(round(v)))
def i16(b,o): return struct.unpack_from('<h',b,o)[0]
path=sys.argv[1]; nums=list(map(float,sys.argv[2:10]))
verts=[(nums[2*i],0,nums[2*i+1]) for i in range(4)]
b=bytearray(open(path,'rb').read()); VO=200
for i,(x,y,z) in enumerate(verts):
    w16(b,VO+i*6,x); w16(b,VO+i*6+2,y); w16(b,VO+i*6+4,z)
for tri_off,idxs in ((94,(0,1,2)),(134,(0,2,3))):
    cx=sum(verts[i][0] for i in idxs)/3.0; cz=sum(verts[i][2] for i in idxs)/3.0
    w16(b,tri_off,cx); w16(b,tri_off+2,0); w16(b,tri_off+4,cz)
open(path,'wb').write(b)
print("verts:",[(i16(b,VO+i*6),i16(b,VO+i*6+4)) for i in range(4)])
