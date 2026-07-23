import refkit
pe = refkit.load(); base=refkit.image_base(pe)
for i in refkit.disasm(pe, 0x1e80, 0x1f10): print(hex(i.address-base), i.mnemonic, i.op_str)
print("=== 0x1d10..0x1d40 (other stepper caller)")
for i in refkit.disasm(pe, 0x1d00, 0x1d40): print(hex(i.address-base), i.mnemonic, i.op_str)
