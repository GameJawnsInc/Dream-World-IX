import refkit, struct
pe=refkit.load()
d=refkit.read_rva(pe,0x31f58,4*40)
for i in range(40):
    v=struct.unpack_from("<I",d,i*4)[0]
    print("idx %02x -> rva %06x %s"%(i,v,"ASSERT@0x316da" if v==0x316da else ""))
