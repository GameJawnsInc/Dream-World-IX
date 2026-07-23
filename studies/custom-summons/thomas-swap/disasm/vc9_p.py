import struct,glob,os,collections
import refkit
pe=refkit.load()
tabA=struct.unpack_from("<16Q",refkit.read_rva(pe,0x4aff0,16*8),0)
tabB=struct.unpack_from("<48Q",refkit.read_rva(pe,0x4ab80+0x30*8,48*8),0)
jt=struct.unpack_from("<21I",refkit.read_rva(pe,0x31f58,21*4),0)
def verdict(c):
    if c<=0x14: return "ASSERT" if jt[c]==0x316da else "VALID"
    if c<0x20: return "ASSERT"
    if c<0x30: return "VALID" if tabA[c-0x20] else "NULL"
    if c<0x50: return "ILLEGAL"
    if c<0x80: return "VALID" if tabB[c-0x50] else "NULL"
    return "VALID"
def resources(b):
    o=2; pos=0x800; out=[]
    cc=struct.unpack_from("<h",b,0)[0]
    for ci in range(cc):
        c_i,rc=struct.unpack_from("<hh",b,o); o+=4
        for _ in range(rc):
            rid,info=struct.unpack_from("<bb",b,o); n=struct.unpack_from("<h",b,o+2)[0]<<11; o+=4
            start=pos; pos+=n
            if rid==2 and info!=0:
                pos+=struct.unpack_from("<h",b,o)[0]<<11; o+=2
            out.append((ci,rid,info,start,pos-start))
    return out
def walk_seqtable(payload,limit=0x200):
    o=0; ents=[]; codes=collections.Counter(); bad=0
    for _ in range(limit):
        if o+2>len(payload): return None
        lo,dl=payload[o],payload[o+1]
        n=dl&0x7f
        if o+2+3*n>len(payload): return None
        for k in range(n):
            c=payload[o+2+3*k]; codes[c]+=1
            if verdict(c)!="VALID": bad+=1
        ents.append((lo+(0x100 if dl&0x80 else 0),n))
        o+=n*3+2
        if lo==0 and dl==0: break
    return ents,codes,bad,o
for name in ("ef227","ef038","ef000"):
    b=open("C:/gd/SCRATCH/summon-format/%s.bytes"%name,'rb').read()
    rs=resources(b)
    print("==",name,"resources:",[(r[1],hex(r[3]),hex(r[4])) for r in rs])
    for ci,rid,info,st,ln in rs:
        if rid!=3: continue
        pay=b[st:st+ln]
        print("   id3 chunk%d @0x%x len0x%x first16=%s"%(ci,st,ln,pay[:16].hex()))
        r=walk_seqtable(pay)
        print("   walker:",("None" if r is None else "ents=%d bad=%d consumed=0x%x firstents=%s"%(len(r[0]),r[2],r[3],r[0][:6])))
