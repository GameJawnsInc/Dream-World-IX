import refkit,struct
pe=refkit.load('x86'); IB=refkit.image_base(pe)
text=[s for s in pe.sections if s.Name.startswith(b'.text')][0]
tlo,thi=text.VirtualAddress,text.VirtualAddress+text.Misc_VirtualSize
want=set([0x52,0x53,0x54,0x58,0x59,0x5d,0x60,0x66,0x67,0x68,0x74,0x75,0x76,0x77,0x78,0x7d,0x7e])
wantrel=set(c-0x50 for c in want)
rd=[s for s in pe.sections if s.Name.startswith(b'.rdata')][0]
base=rd.VirtualAddress; size=rd.Misc_VirtualSize
d=refkit.read_rva(pe,base,size)
hits=[]
for off in range(0,size-48*4,4):
    vals=struct.unpack_from("<48I",d,off)
    nulls=set(i for i,v in enumerate(vals) if v==0)
    if nulls!=wantrel: continue
    if all((tlo<=v-IB<thi) for i,v in enumerate(vals) if i not in nulls):
        hits.append(base+off)
print("x86 candidate tableB rvas (exact NULL-pattern + all-.text):",[hex(h) for h in hits])
for h in hits:
    vals=struct.unpack_from("<48I",refkit.read_rva(pe,h,48*4),0)
    print("  first 8:",[hex(v) for v in vals[:8]])
