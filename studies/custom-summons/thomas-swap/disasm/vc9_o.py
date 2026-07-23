import refkit,collections,struct
pe=refkit.load()
for s in pe.sections:
    print(s.Name.decode().rstrip('\x00'), hex(s.VirtualAddress), "vsz",hex(s.Misc_VirtualSize),"raw",hex(s.SizeOfRawData))
d=refkit.read_rva(pe,0x4f860,0x4200)
nz=[i for i,x in enumerate(d) if x]
print("first nonzero at +0x%x, last +0x%x"%(nz[0],nz[-1]))
print(d[nz[0]-16:nz[0]+64].hex())
# try the walker starting at the buffer start anyway, tolerate zero-count entries
o=0;ents=[]
while o+2<=len(d) and len(ents)<600:
    lo,dl=d[o],d[o+1]; n=dl&0x7f
    ents.append((lo+(0x100 if dl&0x80 else 0),n,o))
    o+=n*3+2
    if o>len(d): break
print("walk (tolerating zeros) reached 0x%x in %d entries"%(o,len(ents)))
print(ents[:8], ents[-4:])
