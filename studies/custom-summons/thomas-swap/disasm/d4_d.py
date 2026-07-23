import refkit
pe = refkit.load()
print("=== Draw mesh loop 0x178a0..0x17960")
for i in refkit.disasm(pe, 0x178a0, 0x17960):
    print(i)
