# Set the 4 corners of the single-quad walkmesh + recompute tri centers.
# Vert order: v0=front-left, v1=front-right, v2=back-right, v3=back-left.
# front = +Z (toward camera / screen-bottom). Usage: bgi_set_quad.py file xL xR zBack zFront
import struct, sys
def w16(b,o,v): struct.pack_into('<h',b,o,int(round(v)))
def i16(b,o): return struct.unpack_from('<h',b,o)[0]
path,xL,xR,zBack,zFront=sys.argv[1],*map(int,sys.argv[2:6])
b=bytearray(open(path,'rb').read())
VO=200
verts=[(xL,0,zFront),(xR,0,zFront),(xR,0,zBack),(xL,0,zBack)]
for i,(x,y,z) in enumerate(verts):
    w16(b,VO+i*6,x); w16(b,VO+i*6+2,y); w16(b,VO+i*6+4,z)
for tri_off,idxs in ((94,(0,1,2)),(134,(0,2,3))):
    cx=sum(verts[i][0] for i in idxs)/3.0; cz=sum(verts[i][2] for i in idxs)/3.0
    w16(b,tri_off,cx); w16(b,tri_off+2,0); w16(b,tri_off+4,cz)
open(path,'wb').write(b)
print("verts:",[(i16(b,VO+i*6),i16(b,VO+i*6+2),i16(b,VO+i*6+4)) for i in range(4)])
