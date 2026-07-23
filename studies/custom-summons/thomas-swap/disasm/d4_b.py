import refkit, struct
pe = refkit.load()
print("=== handler 157/158 region 0x117c2..0x11830")
for i in refkit.disasm(pe, 0x117c2, 0x11830):
    print(i)
print()
print("=== .data op->fn table entries 157,158")
ft = struct.unpack('<216Q', refkit.read_rva(pe, 0x68780, 216*8))
b = refkit.image_base(pe)
for op in (157,158,25,23):
    print(op, hex(ft[op]-b))
