"""INDEPENDENT re-derivation of the C9 validity map + corpus scan.
Does NOT import ef_container.py. Reads only from C:/gd/SCRATCH/summon-format/.
"""
import os,struct,glob,collections
import refkit
pe=refkit.load(); IB=refkit.image_base(pe)

# --- build the validity map straight from the DLL's own tables ---
tabA=struct.unpack_from("<16Q", refkit.read_rva(pe,0x4aff0,16*8),0)          # codes 0x20..0x2F
tabB_raw=refkit.read_rva(pe,0x4ab80+0x30*8,0x30*8)                            # codes 0x50..0x7F
tabB=struct.unpack_from("<48Q", tabB_raw,0)
jt=struct.unpack_from("<21I", refkit.read_rva(pe,0x31f58,21*4),0)             # codes 0x00..0x14
ASSERT=0x316da

def verdict(c):
    if c<=0x14:
        return "ASSERT" if jt[c]==ASSERT else "VALID"
    if c<0x20: return "ASSERT"           # ja 0x14 -> 0x316da
    if c<0x30: return "VALID" if tabA[c-0x20] else "NULLPTR"
    if c<0x50: return "ILLEGAL"          # index past tabA into .rdata strings
    if c<0x80: return "VALID" if tabB[c-0x50] else "NULLPTR"
    return "VALID"                        # fn 0x49170 (program N)

print("validity map (from tables):")
for band,rng in [("0x00-0x14",range(0,0x15)),("0x15-0x1F",range(0x15,0x20)),("0x20-0x2F",range(0x20,0x30)),
                 ("0x30-0x4F",range(0x30,0x50)),("0x50-0x7F",range(0x50,0x80)),(">=0x80",range(0x80,0x100))]:
    cnt=collections.Counter(verdict(c) for c in rng)
    print("  %-10s %s"%(band,dict(cnt)))
print("  ASSERT codes in 0..0x14:", ["%02x"%c for c in range(0x15) if jt[c]==ASSERT])
print("  NULL codes 0x50-0x7F:", ["%02x"%(0x50+i) for i in range(0x30) if tabB[i]==0])

# --- corpus ---
SC="C:/gd/SCRATCH/summon-format"
files=sorted(glob.glob(os.path.join(SC,"ef*.bytes")))
print("\ncorpus: %d files"%len(files))
tot=0; bad=[]; codes=collections.Counter(); term=collections.Counter(); maxops=0
tablends=[]
for p in files:
    b=open(p,'rb').read()
    # independent table walk (fn 0xd390) to find where the table ends + cursor invariant
    o=0; chunkCount=struct.unpack_from("<h",b,0)[0]; o=2; pos=0x800; ok=True
    try:
        for _ in range(chunkCount):
            ci,rc=struct.unpack_from("<hh",b,o); o+=4
            for _ in range(rc):
                rid=struct.unpack_from("<b",b,o)[0]; info=struct.unpack_from("<b",b,o+1)[0]
                n=struct.unpack_from("<h",b,o+2)[0]<<11; o+=4; pos+=n
                if rid==2 and info!=0:
                    pos+=struct.unpack_from("<h",b,o)[0]<<11; o+=2
    except Exception as e:
        ok=False
    tablends.append((os.path.basename(p),o,pos==len(b),ok))
    # sequence
    q=0x400; nops=0
    while q+3<=0x800:
        c,a1,a2=b[q],b[q+1],b[q+2]; q+=3; nops+=1; tot+=1
        codes[c]+=1
        v=verdict(c)
        if v!="VALID": bad.append((os.path.basename(p),hex(q-3),"%02x"%c,v))
        if c==0x00: term["END"]+=1; break
    else:
        term["RAN-OFF-SECTOR"]+=1
        bad.append((os.path.basename(p),"0x800","--","NO-END"))
    maxops=max(maxops,nops)
print("total opcodes: %d   distinct: %d   max ops/file: %d"%(tot,len(codes),maxops))
print("termination:",dict(term))
print("NON-VALID occurrences: %d"%len(bad))
for r in bad[:40]: print("   ",r)
print("distinct codes:", " ".join("%02x"%c for c in sorted(codes)))
tbad=[t for t in tablends if t[1]>0x400 or not t[2] or not t[3]]
print("\nfiles whose resource table ends past 0x400 OR cursor!=len: %d"%len(tbad))
for t in tbad[:10]: print("   ",t)
print("max table end offset: 0x%x"%max(t[1] for t in tablends))
