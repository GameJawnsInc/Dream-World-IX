import struct, random, refkit, glob, os
pe=refkit.load(); TB=0x66c70
ent=[]; i=0
while True:
    m,mt=struct.unpack_from("<II", pe.get_data(TB+i*0x38,8),0)
    if m==0: break
    ent.append((m,mt)); i+=1
def dec(w):
    for idx,(m,mt) in enumerate(ent):
        if (w&m)==mt: return idx
    return None
random.seed(1)
N=200000
ok=sum(1 for _ in range(N) if dec(random.getrandbits(32)) is not None)
print("CONTROL random-uniform 32-bit words accepted: %d/%d = %.4f%%"%(ok,N,100*ok/N))
# control 2: other sections of the same files (id-0 VRAM pixel data)
def walk(path):
    b=open(path,'rb').read(); n=struct.unpack_from("<h",b,0)[0]; p=2; pos=0x800; out=[]
    for c in range(n):
        ci,rc=struct.unpack_from("<hh",b,p); p+=4
        for j in range(rc):
            rid=struct.unpack_from("<b",b,p)[0]; info=struct.unpack_from("<b",b,p+1)[0]
            sz=struct.unpack_from("<h",b,p+2)[0]<<11; p+=4
            out.append((rid,pos,sz)); pos+=sz
            if rid==2 and info!=0: pos+=struct.unpack_from("<h",b,p)[0]<<11; p+=2
    return b,pos,out
tot=okc=0
for f in sorted(glob.glob(r"C:/gd/SCRATCH/summon-format/ef*.bytes"))[:60]:
    b,endp,res=walk(f)
    if endp!=len(b): continue
    for rid,off,sz in res:
        if rid!=0: continue
        pay=b[off:off+min(sz,0x4000)]
        for o in range(0,len(pay)-3,4):
            w=struct.unpack_from("<I",pay,o)[0]
            tot+=1; okc+= dec(w) is not None
        break
print("CONTROL id-0 (VRAM pixel) words accepted: %d/%d = %.4f%%"%(okc,tot,100*okc/max(1,tot)))
