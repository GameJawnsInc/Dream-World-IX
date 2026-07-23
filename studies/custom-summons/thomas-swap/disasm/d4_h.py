import refkit, struct
pe = refkit.load(); base=refkit.image_base(pe)
print("=== alloc site 0x30c90..0x30ce0")
for i in refkit.disasm(pe, 0x30c90, 0x30ce0): print(hex(i.address-base), i.mnemonic, i.op_str)
print("=== 0x47400..0x47460")
for i in refkit.disasm(pe, 0x47400, 0x47470): print(hex(i.address-base), i.mnemonic, i.op_str)
print("=== which opcode handler contains 0xf906")
jt = struct.unpack('<216I', refkit.read_rva(pe, 0x12358, 216*4))
cand = [(op,h) for op,h in enumerate(jt) if h <= 0xf906]
cand.sort(key=lambda t:-t[1])
print(cand[:4])
