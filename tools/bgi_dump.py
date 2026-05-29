import struct, sys

def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def i16(b,o): return struct.unpack_from('<h',b,o)[0]
def i32(b,o): return struct.unpack_from('<i',b,o)[0]

def dump(path):
    b=open(path,'rb').read()
    print(f"\n===== {path}  ({len(b)} bytes) =====")
    dataSize=u16(b,4)
    # header table starts at 6: 5 vecs(6 each)=30 ->offset 36; then activeFloor,activeTri (i16 x2)=40
    base=6+5*6  # 36
    activeFloor=i16(b,base); activeTri=i16(b,base+2)
    p=base+4  # 40
    triCount=u16(b,p);   triOffset=u16(b,p+2)
    edgeCount=u16(b,p+4);edgeOffset=u16(b,p+6)
    anmCount=u16(b,p+8); anmOffset=u16(b,p+10)
    floorCount=u16(b,p+12);floorOffset=u16(b,p+14)
    normalCount=u16(b,p+16);normalOffset=u16(b,p+18)
    vertexCount=u16(b,p+20);vertexOffset=u16(b,p+22)
    print(f"dataSize={dataSize} activeFloor={activeFloor} activeTri={activeTri}")
    print(f"tri:cnt={triCount}@{triOffset} edge:cnt={edgeCount}@{edgeOffset} floor:cnt={floorCount}@{floorOffset} norm:cnt={normalCount}@{normalOffset} vert:cnt={vertexCount}@{vertexOffset}")
    # vertices
    vo=4+vertexOffset
    verts=[(i16(b,vo+i*6),i16(b,vo+i*6+2),i16(b,vo+i*6+4)) for i in range(vertexCount)]
    print("verts:",verts)
    # triangles (40 bytes each)
    to=4+triOffset
    for t in range(triCount):
        o=to+t*40
        vtx=(i16(b,o+12),i16(b,o+14),i16(b,o+16))
        edg=(i16(b,o+18),i16(b,o+20),i16(b,o+22))
        nbr=(i16(b,o+24),i16(b,o+26),i16(b,o+28))
        print(f"  tri{t}: vtx={vtx} edgeNdx={edg} neighborNdx={nbr} flags={u16(b,o)}")
    # edges (4 bytes)
    eo=4+edgeOffset
    for e in range(edgeCount):
        o=eo+e*4
        print(f"  edge{e}: flags={u16(b,o)} edgeClone={i16(b,o+2)}")

for path in sys.argv[1:]:
    try: dump(path)
    except Exception as ex: print(path,"ERR",ex)
