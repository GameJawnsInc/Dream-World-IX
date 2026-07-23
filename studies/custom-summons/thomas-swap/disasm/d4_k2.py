import refkit, struct
pe=refkit.load()
for rva in (0x4B690,0x4B6A8,0x4B6C0,0x4b6a0,0x4b6c8,0x4b6e8):
    d=struct.unpack('<d', refkit.read_rva(pe,rva,8))[0]
    print(hex(rva), d)
