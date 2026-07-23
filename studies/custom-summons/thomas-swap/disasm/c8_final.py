import struct, glob, os, refkit
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
tw=to=0; imgs=[]; nimg100=0; badhdr=0; prol=0; nprog=0
for f in sorted(glob.glob(r"C:/gd/SCRATCH/summon-format/ef*.bytes")):
    b,endp,id3=walk(f)
    if endp!=len(b): continue
    for ordn,off,sz in id3:
        pay=b[off:off+sz]
        psx=0x801E7700+(ordn&1)*0x5000
        hdr=(struct.unpack_from("<I",pay,0)[0]&0xfffffff)-(psx&0xfffffff)
        if not (0<hdr<=sz): badhdr+=1; continue
        ok=bad=0
        for o2 in range(4,hdr-3,4):
            if dec(struct.unpack_from("<I",pay,o2)[0]) is None: bad+=1
            else: ok+=1
        tw+=ok+bad; to+=ok; imgs.append((ok/max(1,ok+bad),os.path.basename(f),ordn))
        if bad==0: nimg100+=1
        # program entry prologue test: first word must be addiu sp,sp,-N
        for k,v in enumerate(struct.unpack_from("<16I",pay,hdr+8)):
            if not v: continue
            po=(v&0xfffffff)-(psx&0xfffffff)
            if not (0<po<hdr): continue
            nprog+=1
            w=struct.unpack_from("<I",pay,po)[0]
            if (w>>16)==0x27bd and (w&0x8000): prol+=1
imgs.sort()
print("id-3 images: %d  headerRel-out-of-range: %d"%(len(imgs),badhdr))
print("code words %d, decode as MIPS %d = %.4f%%"%(tw,to,100*to/tw))
print("images 100%%: %d/%d (%.1f%%)"%(nimg100,len(imgs),100*nimg100/len(imgs)))
print("worst5:", [(round(r,3),n,o) for r,n,o in imgs[:5]])
print("program entry points: %d ; starting with 'addiu sp,sp,-N': %d (%.2f%%)"%(nprog,prol,100*prol/nprog))
