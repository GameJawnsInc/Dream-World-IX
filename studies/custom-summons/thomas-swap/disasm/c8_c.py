import refkit, struct
pe=refkit.load()
data=pe.get_data(0xed18, 0x168+0x40)
vals=struct.unpack_from("<%dI"%(0x168//4), data, 0)
print("n=",len(vals))
for i,v in enumerate(vals):
    print("%02x: %08x"%(i,v), end="   ")
    if i%4==3: print()
print()
print("tail after table:", data[0x168:0x188].hex())
