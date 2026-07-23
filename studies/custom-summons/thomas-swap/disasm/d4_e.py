import refkit
pe = refkit.load()
print("=== Register 0x15ee0..0x15f80")
for i in refkit.disasm(pe, 0x15ee0, 0x15f80): print(i)
print("=== 0xf8e0..0xf940 (DATA clear site)")
for i in refkit.disasm(pe, 0xf8e0, 0xf940): print(i)
