import refkit
pe = refkit.load(); base=refkit.image_base(pe)
print("=== 0x30c20..0x30d45  (camera init per M2 load chain)")
for i in refkit.disasm(pe, 0x30c20, 0x30d45): print(hex(i.address-base), i.mnemonic, i.op_str)
