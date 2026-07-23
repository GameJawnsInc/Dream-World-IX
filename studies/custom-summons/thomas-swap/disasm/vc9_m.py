import refkit,struct,collections
pe=refkit.load()
s=refkit._section_for_rva(pe,0x4f860); print("0x4f860 section",s.Name.decode().rstrip('\x00'),"inRaw",0x4f860-s.VirtualAddress< s.SizeOfRawData)
d=refkit.read_rva(pe,0x4f860,0x4200)
print("first 48 bytes:",d[:48].hex())
# walk per fn 0x31470: entry = u8 idLow, u8 dl ; id = idLow + (0x100 if dl&0x80) ; stride = (dl&0x7f)*3 + 2
o=0; ents=[]; codes=collections.Counter(); bad=[]
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
while o+2<=len(d) and len(ents)<0x200:
    lo=d[o]; dl=d[o+1]
    eid=lo+(0x100 if dl&0x80 else 0)
    n=dl&0x7f
    if lo==0 and dl==0: break
    recs=[(d[o+2+3*k],d[o+3+3*k],d[o+4+3*k]) for k in range(n) if o+5+3*k<=len(d)]
    for c,a,b in recs:
        codes[c]+=1
        v=verdict(c)
        if v!="VALID": bad.append((eid,"%02x"%c,v))
    ents.append((eid,n,o))
    o += n*3+2
print("entries walked:",len(ents),"bytes consumed 0x%x of 0x4200"%o)
print("first 12 entries (id,count,off):",ents[:12])
print("last 3:",ents[-3:])
print("opcodes in built-in table:",sum(codes.values()),"distinct",len(codes))
print("NON-VALID:",len(bad),bad[:20])
print("distinct codes:"," ".join("%02x"%c for c in sorted(codes)))
