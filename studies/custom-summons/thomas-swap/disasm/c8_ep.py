import struct, glob, os, refkit
def walk(path):
    b=open(path,'rb').read(); n=struct.unpack_from("<h",b,0)[0]; p=2; pos=0x800; out=[]; o=0
    for c in range(n):
        ci,rc=struct.unpack_from("<hh",b,p); p+=4
        for j in range(rc):
            rid=struct.unpack_from("<b",b,p)[0]; info=struct.unpack_from("<b",b,p+1)[0]
            sz=struct.unpack_from("<h",b,p+2)[0]<<11; p+=4
            if rid==3: out.append((o,pos,sz))
            pos+=sz
            if rid==2 and info!=0: pos+=struct.unpack_from("<h",b,p)[0]<<11; p+=2
        o+=1
    return b,pos,out
odd=[]
for f in sorted(glob.glob(r"C:/gd/SCRATCH/summon-format/ef*.bytes")):
    b,endp,id3=walk(f)
    if endp!=len(b): continue
    for ordn,off,sz in id3:
        pay=b[off:off+sz]; psx=0x801E7700+(ordn&1)*0x5000
        hdr=(struct.unpack_from("<I",pay,0)[0]&0xfffffff)-(psx&0xfffffff)
        for k,v in enumerate(struct.unpack_from("<16I",pay,hdr+8)):
            if not v: continue
            po=(v&0xfffffff)-(psx&0xfffffff)
            if not (0<po<hdr): continue
            w=struct.unpack_from("<I",pay,po)[0]
            if not ((w>>16)==0x27bd and (w&0x8000)):
                odd.append((os.path.basename(f),ordn,k,hex(po),"%08x"%w))
for o in odd: print(o)
